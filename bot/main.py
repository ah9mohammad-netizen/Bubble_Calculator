"""
Iran Gold / FX signalling bot — Telegram + Railway.

Env:
  TELEGRAM_BOT_TOKEN  (required)
  TELEGRAM_CHAT_ID    (required — default broadcast target)
  DATA_DIR            (default /data)
  CHECK_INTERVAL_MIN  (default 60)
  REPORT_HOUR_TEHRAN  (default 12)
  PORT                (Railway healthcheck)

Optional Metals Desk feature (see bot/desk/README.md). Off unless switched on;
when off, not one line of the code below behaves differently:
  ENABLE_DESK         (default 0 — set 1 to run the desk)
  DESK_POLL_SECONDS   (default 900)
  DESK_ALERTS         (default 1 — 0 = commands only, no pushes)
  DESK_QUIET_HOURS    (default 01:00-07:00 Tehran; critical rules ignore it)
"""
from __future__ import annotations
import logging, os, sys, threading, time, json
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests
import strategy as S
import datafeed
import store
import messages as M

# The desk is an optional add-on. A missing dependency or a broken config
# must cost us the desk, never the strategy loop, so the import itself is
# guarded and the object stays None until main() decides to build it.
try:
    import desk as desk_mod
except Exception as _desk_import_error:          # noqa: BLE001
    desk_mod, DESK_IMPORT_ERROR = None, _desk_import_error
else:
    DESK_IMPORT_ERROR = None
DESK = None

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("bot")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
INTERVAL_MIN = int(os.getenv("CHECK_INTERVAL_MIN", "60"))
REPORT_HOUR = int(os.getenv("REPORT_HOUR_TEHRAN", "12"))
API = f"https://api.telegram.org/bot{TOKEN}"
SEED = Path(__file__).parent / "seed_history.csv"


# ───────────────────────── telegram ─────────────────────────
def send(text: str, chat_id: str | None = None, parse_mode: str = "HTML") -> bool:
    cid = chat_id or CHAT_ID
    if not (TOKEN and cid):
        log.error("missing token/chat id")
        return False
    for attempt in range(3):
        try:
            payload = {"chat_id": cid, "text": text[:4096],
                       "disable_web_page_preview": True}
            if parse_mode:
                # Omitted entirely rather than sent empty: that is how a
                # message is sent with no formatting at all, which is the
                # fallback when Markdown from the desk fails to parse.
                payload["parse_mode"] = parse_mode
            r = requests.post(f"{API}/sendMessage", timeout=25, json=payload)
            if r.status_code == 200:
                return True
            log.warning("sendMessage %s: %s", r.status_code, r.text[:200])
            if r.status_code == 429:
                time.sleep(int(r.json().get("parameters", {}).get("retry_after", 5)))
                continue
            return False
        except Exception as e:
            log.warning("send failed (%s/3): %s", attempt + 1, e)
            time.sleep(2 * (attempt + 1))
    return False


def broadcast(text: str) -> None:
    targets = {CHAT_ID} | set(store.load_state().get("subscribers", []))
    for t in filter(None, targets):
        send(text, t)


# ───────────────────────── core evaluation ─────────────────────────
def bars_since(date_str: str | None, prices: list[dict]) -> int:
    if not date_str:
        return 999
    dates = [r["date"] for r in prices]
    try:
        return max(0, len(dates) - 1 - dates.index(date_str))
    except ValueError:
        return 999


def evaluate(persist: bool = True):
    """Fetch → store → decide. Returns (snap, decision, state, bq, bm)."""
    snap = datafeed.fetch_latest()
    if not snap.get("ok"):
        log.warning("incomplete snapshot: %s", snap.get("errors"))
        return snap, None, store.load_state(), None, None, {}

    if persist:
        store.upsert_price(snap["date"], snap.get("quarter"), snap.get("mesghal"),
                           snap.get("usd"), snap.get("spot"))

    prices = store.load_prices()
    state = store.load_state()
    rp = S.relative_premium(snap["quarter"], snap["mesghal"])
    vol = S.vol90(store.mesghal_series())
    bq, bm = S.intrinsic_bubbles(snap["quarter"], snap["mesghal"],
                                 snap.get("usd"), snap.get("spot"))

    # ---- world-parity basis z-score ----
    bas_series = []
    for r in prices:
        try:
            sp = float(r["spot"]) if r.get("spot") else None
            ur = float(r["usd"]) if r.get("usd") else None
            mm = float(r["mesghal"]) if r.get("mesghal") else None
        except (ValueError, TypeError):
            sp = ur = mm = None
        bas_series.append(S.basis(mm, sp, ur))
    bas_today = S.basis(snap.get("mesghal"), snap.get("spot"), snap.get("usd"))
    zval = S.basis_z(bas_series)
    zstate, run_hi, run_lo, _ = S.z_decide(
        [S.basis_z(bas_series[: i + 1]) for i in range(max(0, len(bas_series) - S.Z_PERSIST), len(bas_series))],
        state=state.get("z_state", "GOLD"),
        bars_since_z=bars_since(state.get("last_z_date"), prices),
    )
    extra = {"basis": bas_today, "z": zval, "z_state": zstate,
             "run_hi": run_hi, "run_lo": run_lo,
             "basis_obs": sum(1 for b in bas_series if b is not None)}

    dec = S.decide(rp=rp, vol=vol,
                   current=state.get("position", "MESGHAL"),
                   prev_pref=state.get("last_pref", "MESGHAL"),
                   bars_since_l1=bars_since(state.get("last_l1_date"), prices),
                   bars_since_l2=bars_since(state.get("last_l2_date"), prices))
    return snap, dec, state, bq, bm, extra


def apply_signal(snap, dec, state) -> bool:
    """Persist a position change and alert. Returns True if a trade fired."""
    if not dec or not dec.action:
        if dec and dec.layer2_pref != state.get("last_pref"):
            state["last_pref"] = dec.layer2_pref
            store.save_state(state)
        return False

    frm, to = state.get("position", "MESGHAL"), dec.target
    is_l1 = "USD" in (frm, to)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    store.append_signal(snap["date"], ts, frm, to,
                        "L1" if is_l1 else "L2", dec.rp, dec.vol, dec.reason)
    state["position"] = to
    state["since"] = snap["date"]
    state["last_pref"] = dec.layer2_pref
    if is_l1:
        state["last_l1_date"] = snap["date"]
    else:
        state["last_l2_date"] = snap["date"]
    store.save_state(state)

    broadcast(M.signal_alert(frm, to, dec, snap))
    log.info("SIGNAL %s -> %s", frm, to)
    return True


# ───────────────────────── commands ─────────────────────────
def cmd_status(chat):
    snap, dec, state, bq, bm, extra = evaluate()
    if not dec:
        send("⚠️ Could not fetch prices right now.\n"
             f"<code>{', '.join(snap.get('errors') or ['unknown'])}</code>", chat)
        return
    send(M.daily_report(snap, dec, state, bq, bm, extra), chat)


def cmd_price(chat):
    snap = datafeed.fetch_latest()
    if not snap.get("ok"):
        send("⚠️ Price feed unavailable.", chat)
        return
    sp = snap.get("spot")
    send("\n".join([
        f"💵 USD       <code>{M.rial(snap.get('usd'))}</code> rial",
        f"🥇 مثقال     <code>{M.rial(snap.get('mesghal'))}</code> rial",
        f"🪙 ربع سکه   <code>{M.rial(snap.get('quarter'))}</code> rial",
        f"🌍 spot      <code>{sp:,.2f}</code> $/oz" if sp else "🌍 spot      —",
        f"<i>{M.tehran_now()} Tehran</i>"]), chat)


def cmd_signal(chat):
    snap, dec, state, bq, bm, extra = evaluate()
    if not dec:
        send("⚠️ Feed unavailable.", chat)
        return
    if dec.action:
        send(M.signal_alert(state.get("position"), dec.target, dec, snap), chat)
    else:
        send(f"✅ <b>NO TRADE</b>\nHold {M.EMO[state['position']]} "
             f"<b>{M.FA[state['position']]}</b>\n\n"
             f"RP <b>{dec.rp*100:.1f}%</b>"
             + (f" · vol90 <b>{dec.vol*100:.2f}%</b>" if dec.vol else "")
             + f"\n<i>{dec.reason}</i>", chat)


def cmd_position(chat):
    st = store.load_state()
    p = st.get("position", "MESGHAL")
    txt = [f"{M.EMO[p]} Holding <b>{M.FA[p]}</b> ({M.EN[p]})"]
    if st.get("since"):
        txt.append(f"<i>since {st['since']}</i>")
    txt.append("\nChange with <code>/setpos quarter|mesghal|usd</code>")
    send("\n".join(txt), chat)


def cmd_setpos(chat, arg):
    m = {"quarter": "QUARTER", "ربع": "QUARTER", "mesghal": "MESGHAL",
         "مثقال": "MESGHAL", "gold": "MESGHAL", "usd": "USD", "dollar": "USD"}
    key = m.get((arg or "").strip().lower())
    if not key:
        send("Usage: <code>/setpos quarter</code> | <code>mesghal</code> | <code>usd</code>", chat)
        return
    st = store.load_state()
    st["position"] = key
    st["since"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if key in ("QUARTER", "MESGHAL"):
        st["last_pref"] = key
    store.save_state(st)
    send(f"✅ Position set to {M.EMO[key]} <b>{M.FA[key]}</b>", chat)


def cmd_history(chat):
    sigs = store.load_signals(10)
    if not sigs:
        send("No signals recorded yet.", chat)
        return
    out = ["📜 <b>Recent signals</b>", ""]
    for s in sigs:
        try:
            rp = float(s.get("rp") or 0) * 100
        except ValueError:
            rp = 0.0
        out.append(f"<code>{s.get('date','')}</code> {s.get('from_pos')}→"
                   f"<b>{s.get('to_pos')}</b> [{s.get('layer')}] RP {rp:.0f}%")
    send("\n".join(out), chat)


def cmd_stats(chat):
    s = store.stats()
    send("\n".join([
        "🗄 <b>Storage</b>",
        f"path <code>{s['dir']}</code>",
        f"price rows <b>{s['prices']}</b>",
        f"range <code>{s['first']} → {s['last']}</code>",
        f"signals <b>{s['signals']}</b>",
        f"position <b>{store.load_state().get('position')}</b>",
        f"vol obs <b>{store.vol_obs_count()}</b>/{S.VOL_WINDOW + 1} (for vol90)",
        f"basis obs <b>{store.basis_obs_count()}</b>/{S.Z_WINDOW + 1} (for z)",
        f"gap since last <b>{store.gap_days()}</b> days",
        ("✅ history is on a persistent volume"
         if "data_local" not in str(store.DATA_DIR)
         else "⚠️ NO VOLUME — history resets on redeploy"),
        _desk_stats_line()]), chat)


def _desk_stats_line() -> str:
    if DESK is None:
        return "desk <b>off</b> (set <code>ENABLE_DESK=1</code>)"
    st = DESK.status()
    age = st["last_poll_age_s"]
    return (f"desk <b>on</b> · {st['rules']} rules · sources "
            f"<b>{st['sources_ok']}/{st['sources_total']}</b> ok · last poll "
            + (f"<b>{age}</b>s ago" if age is not None else "<b>pending</b>"))


def cmd_repair(chat):
    """Merge missing spot history from the bundled seed into the volume."""
    n = store.merge_seed_spot(SEED)
    have = store.basis_obs_count()
    need = S.Z_WINDOW + 1
    msg = [f"🔧 Repaired <b>{n}</b> rows of spot history.",
           f"basis observations now <b>{have}</b>/{need}"]
    msg.append("✅ z-score is live." if have >= need
               else "⏳ Still warming up — run /backfill too.")
    send("\n".join(msg), chat)


def cmd_backfill(chat):
    send("⏳ Backfilling from tgju…", chat)
    try:
        merged = datafeed.backfill(rows=400)
        n = 0
        for d, vals in sorted(merged.items()):
            if vals.get("quarter") or vals.get("mesghal"):
                store.upsert_price(d, vals.get("quarter"), vals.get("mesghal"),
                                   vals.get("usd"), vals.get("spot"))
                n += 1
        s = store.stats()
        send(f"✅ Merged <b>{n}</b> days.\nNow <b>{s['prices']}</b> rows "
             f"(<code>{s['first']} → {s['last']}</code>)", chat)
    except Exception as e:
        send(f"❌ Backfill failed: <code>{e}</code>", chat)


# ───────────────────────── metals desk bridge ─────────────────────────
def send_md(text: str, chat: str | None = None) -> None:
    """Send desk output, which is Markdown rather than the HTML the rest of
    the bot uses.

    Telegram rejects the whole message when Markdown is unbalanced, and desk
    text is partly user-authored (rule messages live in rules.yaml). A 400
    must not swallow a kill-criterion alert, so fall back to plain text.
    Long output (/rules) is chunked; Telegram's limit is 4096.
    """
    text = text or "(no output)"
    for i in range(0, len(text), 3800):
        part = text[i:i + 3800]
        if not send(part, chat, parse_mode="Markdown"):
            send(part, chat, parse_mode="")


def _desk_cmd(fn):
    """Adapt a Desk method (arg) -> text to the bot's (chat, arg) handler."""
    def handler(chat, arg):
        if DESK is None:
            send("Metals Desk is off. Set <code>ENABLE_DESK=1</code> in Railway "
                 "variables to switch it on.", chat)
            return
        try:
            send_md(fn(arg), chat)
        except Exception as e:                        # noqa: BLE001
            log.exception("desk command failed")
            send(f"❌ Desk error: <code>{type(e).__name__}: {e}</code>", chat)
    return handler


COMMANDS = {
    "/start": lambda c, a: (send(M.HELP, c), _subscribe(c)),
    "/help": lambda c, a: send(M.HELP, c),
    "/status": lambda c, a: cmd_status(c),
    "/price": lambda c, a: cmd_price(c),
    "/prices": lambda c, a: cmd_price(c),
    "/signal": lambda c, a: cmd_signal(c),
    "/position": lambda c, a: cmd_position(c),
    "/setpos": cmd_setpos,
    "/history": lambda c, a: cmd_history(c),
    "/stats": lambda c, a: cmd_stats(c),
    "/backfill": lambda c, a: cmd_backfill(c),
    "/repair": lambda c, a: cmd_repair(c),
}


def _owner_only(fn):
    """Restrict a handler to the configured owner chat.

    The strategy bot has never authenticated its commands, and that is fine
    for /price. It is not fine for /probeurl, which makes this process fetch
    a URL the caller chose. Gate it here, where CHAT_ID lives.
    """
    inner = _desk_cmd(fn)

    def handler(chat, arg):
        if str(chat) != str(CHAT_ID):
            send("That command is limited to the bot owner.", chat)
            return
        inner(chat, arg)
    return handler


def register_desk_commands(d) -> None:
    """Merge the desk's commands in. An existing command always wins — the
    strategy bot's UI is the one people already use, and silently shadowing
    /status or /signal would be exactly the kind of regression this feature
    is not allowed to cause."""
    for name, fn in d.commands().items():
        if name in COMMANDS:
            log.warning("desk command %s collides with an existing one — skipped", name)
            continue
        COMMANDS[name] = (_owner_only(fn) if name in d.OWNER_ONLY
                          else _desk_cmd(fn))


def _subscribe(chat):
    st = store.load_state()
    subs = set(st.get("subscribers", []))
    if str(chat) not in subs:
        subs.add(str(chat))
        st["subscribers"] = sorted(subs)
        store.save_state(st)


def handle(update: dict) -> None:
    msg = update.get("message") or update.get("channel_post") or {}
    text = (msg.get("text") or "").strip()
    chat = str((msg.get("chat") or {}).get("id") or "")
    if not text.startswith("/") or not chat:
        return
    parts = text.split(maxsplit=1)
    cmd = parts[0].split("@")[0].lower()
    arg = parts[1] if len(parts) > 1 else ""
    fn = COMMANDS.get(cmd)
    if not fn:
        send("Unknown command. Try /help", chat)
        return
    try:
        fn(chat, arg)
    except Exception as e:
        log.exception("command %s failed", cmd)
        send(f"❌ Error: <code>{type(e).__name__}</code>", chat)


# ───────────────────────── loops ─────────────────────────
def poller():
    offset = None
    if os.getenv("ENABLE_COMMANDS", "1") not in ("1", "true", "True"):
        log.info("command polling DISABLED (ENABLE_COMMANDS=0) - digest only")
        return
    log.info("polling started")
    while True:
        try:
            lp = int(os.getenv("LONGPOLL_SEC", "50"))
            r = requests.get(f"{API}/getUpdates", timeout=lp + 10,
                             params={"timeout": lp, "offset": offset})
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                handle(upd)
        except Exception as e:
            log.warning("poll: %s", e)
            time.sleep(5)


def monitor():
    log.info("monitor started (every %s min, report %02d:00 Tehran)",
             INTERVAL_MIN, REPORT_HOUR)
    while True:
        try:
            snap, dec, state, bq, bm, extra = evaluate()
            if dec:
                fired = apply_signal(snap, dec, state)
                tehran = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
                today = tehran.strftime("%Y-%m-%d")
                st = store.load_state()
                if (not fired and tehran.hour >= REPORT_HOUR
                        and st.get("last_daily_report") != today):
                    broadcast(M.daily_report(snap, dec, st, bq, bm, extra))
                    st["last_daily_report"] = today
                    store.save_state(st)
        except Exception:
            log.exception("monitor cycle failed")

        # Sleep longer outside Tehran market hours - the board does not move
        # overnight, so polling then just burns CPU-hours.
        th = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
        quiet = th.hour >= 20 or th.hour < 8
        time.sleep(INTERVAL_MIN * 60 * (4 if quiet else 1))


def desk_loop():
    """The desk polls on its own thread and its own clock.

    Deliberately NOT folded into monitor(): the strategy loop's cadence, its
    night-time 4x slowdown and its daily-digest bookkeeping are tuned for a
    market that prints once a session, and the desk wants 15-minute intraday
    resolution. Sharing a thread would mean one of them compromising. Sharing
    nothing means a hung desk fetch can never delay a trade signal.
    """
    log.info("desk started (every %ss, %d rules)",
             desk_mod.settings.poll_seconds, len(DESK.engine.rules))
    time.sleep(5)                       # let the strategy boot ping land first
    while True:
        try:
            for text, rule_id in DESK.tick():
                for t in filter(None, {CHAT_ID} | set(
                        store.load_state().get("subscribers", []))):
                    send_md(text, t)
                log.info("DESK FIRE %s", rule_id)
            warn = DESK.degraded_warning()
            if warn:
                send_md(warn)
        except Exception:
            log.exception("desk cycle failed")
        time.sleep(desk_mod.settings.poll_seconds)


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        s = store.stats()
        payload = {"status": "ok", "position": store.load_state().get("position"), **s}
        if DESK is not None:
            try:
                payload["desk"] = DESK.status()
            except Exception as e:                     # noqa: BLE001
                payload["desk"] = {"enabled": True, "error": f"{type(e).__name__}: {e}"}
        else:
            payload["desk"] = {"enabled": False}
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def start_desk() -> None:
    """Bring the desk up if it is switched on. Never raises."""
    global DESK
    if desk_mod is None:
        if os.getenv("ENABLE_DESK", "0").strip().lower() in ("1", "true", "yes", "on"):
            log.error("ENABLE_DESK is set but the desk failed to import: %s",
                      DESK_IMPORT_ERROR)
        return
    if not desk_mod.settings.enabled:
        log.info("metals desk disabled (set ENABLE_DESK=1 to enable)")
        return
    try:
        DESK = desk_mod.Desk(store.DATA_DIR)
        register_desk_commands(DESK)
        threading.Thread(target=desk_loop, daemon=True, name="desk").start()
        log.info("metals desk ready: %d rules, db %s",
                 len(DESK.engine.rules), DESK.db_path)
    except Exception:
        log.exception("metals desk failed to start — continuing without it")
        DESK = None


def main():
    # 1. Bind the health port FIRST so Railway's healthcheck can never race the
    #    data seeding or a Telegram outage.
    port = int(os.getenv("PORT", "8080"))
    try:
        srv = HTTPServer(("0.0.0.0", port), Health)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        log.info("health server listening on 0.0.0.0:%s", port)
    except Exception:
        log.exception("could not bind health port %s", port)

    # 2. Fail loudly and readably if the deploy is missing its variables.
    if not TOKEN or not CHAT_ID:
        missing = [n for n, v in (("TELEGRAM_BOT_TOKEN", TOKEN),
                                  ("TELEGRAM_CHAT_ID", CHAT_ID)) if not v]
        log.error("=" * 62)
        log.error("MISSING REQUIRED RAILWAY VARIABLES: %s", ", ".join(missing))
        log.error("Set them under Service -> Variables, then redeploy.")
        log.error("=" * 62)
        sys.exit(1)

    store.init(seed_csv=SEED)
    log.info("storage ready: %s", store.stats())

    # 3. Warn loudly if history is NOT on a persistent volume. Without one,
    #    every redeploy resets to the seed and vol90/z silently drift.
    if "data_local" in str(store.DATA_DIR):
        log.error("=" * 62)
        log.error("NO PERSISTENT VOLUME: history lives in the container and")
        log.error("will be LOST on every redeploy. Mount a volume at /data")
        log.error("and set DATA_DIR=/data.")
        log.error("=" * 62)

    # 4. If the bot was down, prices are missing. A hole turns two prices
    #    weeks apart into one giant 'daily' return and inflates vol90 —
    #    enough to fake a RISK-OFF signal. Self-heal before deciding anything.
    gap = store.gap_days()
    if gap >= 2:
        log.warning("history gap of %d days — backfilling to repair vol90", gap)
        try:
            merged = datafeed.backfill(rows=400)
            n = 0
            for d, vals in sorted(merged.items()):
                if vals.get("quarter") or vals.get("mesghal"):
                    store.upsert_price(d, vals.get("quarter"), vals.get("mesghal"),
                                       vals.get("usd"), vals.get("spot"))
                    n += 1
            log.info("gap backfill merged %d days; now %s", n, store.stats())
        except Exception:
            log.exception("gap backfill failed — vol90 may be distorted")

    # 5. Optional Metals Desk. Built last, after everything the strategy bot
    #    needs is already up, and behind three separate guards: the env flag,
    #    a guarded import, and a guarded construction. Any failure logs and
    #    leaves DESK as None; the bot below runs exactly as it did before.
    start_desk()

    threading.Thread(target=poller, daemon=True).start()

    s = store.stats()
    send("🤖 <b>Bot online</b>\n"
         f"<i>{M.tehran_now()} Tehran</i>\n"
         f"history <b>{s['prices']}</b> rows · position "
         f"<b>{store.load_state().get('position')}</b>\n\n/help for the strategy")
    monitor()


if __name__ == "__main__":
    main()
