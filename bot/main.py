"""
Iran Gold / FX signalling bot — Telegram + Railway.

Env:
  TELEGRAM_BOT_TOKEN  (required)
  TELEGRAM_CHAT_ID    (required — default broadcast target)
  DATA_DIR            (default /data)
  CHECK_INTERVAL_MIN  (default 60)
  REPORT_HOUR_TEHRAN  (default 12)
  PORT                (Railway healthcheck)
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
def send(text: str, chat_id: str | None = None) -> bool:
    cid = chat_id or CHAT_ID
    if not (TOKEN and cid):
        log.error("missing token/chat id")
        return False
    for attempt in range(3):
        try:
            r = requests.post(f"{API}/sendMessage", timeout=25, json={
                "chat_id": cid, "text": text[:4096],
                "parse_mode": "HTML", "disable_web_page_preview": True})
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
        return snap, None, store.load_state(), None, None

    if persist:
        store.upsert_price(snap["date"], snap.get("quarter"), snap.get("mesghal"),
                           snap.get("usd"), snap.get("spot"))

    prices = store.load_prices()
    state = store.load_state()
    rp = S.relative_premium(snap["quarter"], snap["mesghal"])
    vol = S.vol45(store.mesghal_series())
    bq, bm = S.intrinsic_bubbles(snap["quarter"], snap["mesghal"],
                                 snap.get("usd"), snap.get("spot"))

    dec = S.decide(rp=rp, vol=vol,
                   current=state.get("position", "MESGHAL"),
                   prev_pref=state.get("last_pref", "MESGHAL"),
                   bars_since_l1=bars_since(state.get("last_l1_date"), prices),
                   bars_since_l2=bars_since(state.get("last_l2_date"), prices))
    return snap, dec, state, bq, bm


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
    snap, dec, state, bq, bm = evaluate()
    if not dec:
        send("⚠️ Could not fetch prices right now.\n"
             f"<code>{', '.join(snap.get('errors') or ['unknown'])}</code>", chat)
        return
    send(M.daily_report(snap, dec, state, bq, bm), chat)


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
    snap, dec, state, *_ = evaluate()
    if not dec:
        send("⚠️ Feed unavailable.", chat)
        return
    if dec.action:
        send(M.signal_alert(state.get("position"), dec.target, dec, snap), chat)
    else:
        send(f"✅ <b>NO TRADE</b>\nHold {M.EMO[state['position']]} "
             f"<b>{M.FA[state['position']]}</b>\n\n"
             f"RP <b>{dec.rp*100:.1f}%</b>"
             + (f" · vol45 <b>{dec.vol*100:.2f}%</b>" if dec.vol else "")
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
        f"position <b>{store.load_state().get('position')}</b>"]), chat)


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
}


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
    log.info("polling started")
    while True:
        try:
            r = requests.get(f"{API}/getUpdates", timeout=40,
                             params={"timeout": 30, "offset": offset})
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
            snap, dec, state, bq, bm = evaluate()
            if dec:
                fired = apply_signal(snap, dec, state)
                tehran = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
                today = tehran.strftime("%Y-%m-%d")
                st = store.load_state()
                if (not fired and tehran.hour >= REPORT_HOUR
                        and st.get("last_daily_report") != today):
                    broadcast(M.daily_report(snap, dec, st, bq, bm))
                    st["last_daily_report"] = today
                    store.save_state(st)
        except Exception:
            log.exception("monitor cycle failed")
        time.sleep(INTERVAL_MIN * 60)


class Health(BaseHTTPRequestHandler):
    def do_GET(self):
        s = store.stats()
        body = json.dumps({"status": "ok", "position": store.load_state().get("position"),
                           **s}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def main():
    if not TOKEN or not CHAT_ID:
        log.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
        sys.exit(1)

    store.init(seed_csv=SEED)
    log.info("storage ready: %s", store.stats())

    port = int(os.getenv("PORT", "8080"))
    threading.Thread(target=lambda: HTTPServer(("0.0.0.0", port), Health).serve_forever(),
                     daemon=True).start()
    threading.Thread(target=poller, daemon=True).start()

    s = store.stats()
    send("🤖 <b>Bot online</b>\n"
         f"<i>{M.tehran_now()} Tehran</i>\n"
         f"history <b>{s['prices']}</b> rows · position "
         f"<b>{store.load_state().get('position')}</b>\n\n/help for the strategy")
    monitor()


if __name__ == "__main__":
    main()
