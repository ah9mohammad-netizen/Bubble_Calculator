"""The desk as a self-contained service the signalling bot can hold.

Everything the upstream metals-desk did in its own process happens here
instead, with two deliberate constraints:

  * **It never raises into the host.** Every public method is wrapped, so a
    broken feed, a bad rule, or a TSETMC schema change can degrade the desk
    and nothing else. The gold/FX strategy loop must not notice.
  * **It owns no I/O to Telegram.** `tick()` returns the messages it wants
    sent and the host sends them with its own retrying `send()`. That keeps
    one Telegram client, one long-poll, one token.
"""
from __future__ import annotations
import json
import logging
import threading
import time
from pathlib import Path

from .collector import Collector, LAST_RAW
from .config import load_yaml, settings
from .format import esc, gates_block, ladder_block, snapshot_block, stamp
from .notify import gate
from .probe import ProbeRefused, probe_url
from .tgju import SCAN_CANDIDATES, scan as tgju_scan
from .rules import SEVERITY_ICON, RulesEngine
from .store import Store

log = logging.getLogger("desk")

HELP = """*Metals Desk*

`/now`      full snapshot
`/gates`    handbook entry gates
`/ladder`   ladder status
`/parity`   parity arithmetic, shown step by step
`/funds`    طلا · پلاتا · اهرم premiums
`/rules`    every rule, current value vs threshold
`/fires`    recent desk signals
`/health`   source status and staleness
`/probe X`  raw response from source X (schema mapping)
`/probeurl <url> [filter]`  fetch any URL from this box and list its
            numeric paths — use it to test a data source before wiring it
`/tgju [slug ...]`  ask tgju which indicator slugs it will actually serve
            (no args = scan the candidates for the missing funds)
`/set k v [k v ...]`  set manual values (e.g. `/set iran_cpi_yoy 84.2`)
`/thresh id v`  override a rule threshold
`/mute` `/unmute`
`/reload`   re-read config from disk
"""


class Desk:
    """Owns the desk's store, rules engine and collector."""

    # Commands only the configured owner chat may run. /probeurl makes this
    # process fetch a URL of the caller's choosing, which is not something to
    # hand to whoever finds the bot.
    OWNER_ONLY = frozenset({"/probeurl"})

    def __init__(self, data_dir: Path | str):
        self.db_path = Path(data_dir) / "desk.db"
        self.store = Store(self.db_path)
        self.engine = RulesEngine(load_yaml("rules.yaml"))
        self._restore_thresholds()
        self.collector = Collector(self.store)
        self.last_snapshot = None
        self.last_poll = 0.0
        self.last_error: str | None = None
        self._lock = threading.Lock()

    # ───────────────────────── lifecycle ─────────────────────────
    def _restore_thresholds(self) -> None:
        """Thresholds set with /thresh outlive a redeploy."""
        for k, v in self.store.kv_prefix("thresh."):
            try:
                self.engine.set_threshold(k[7:], json.loads(v))
            except Exception:                            # noqa: BLE001
                log.warning("could not restore threshold %s", k)

    def tick(self) -> list[tuple[str, str]]:
        """One poll. Returns [(text, rule_id)] for the host to send.

        Never raises: a failure here must cost the desk one cycle, not the
        process the strategy bot is running in.
        """
        try:
            with self._lock:
                return self._tick()
        except Exception as e:                           # noqa: BLE001
            self.last_error = f"{type(e).__name__}: {e}"
            log.exception("desk tick failed")
            return []

    def _tick(self) -> list[tuple[str, str]]:
        prev = self.store.last_values()
        snap = self.collector.collect()
        self.last_snapshot = snap
        self.last_poll = time.time()
        self.last_error = None
        self.store.save_snapshot(snap.values)

        if not settings.alerts:
            return []

        fires = self.engine.evaluate(snap.values, prev)
        send, dropped = gate(fires, self.store, self.engine,
                             settings.quiet_window(),
                             bool(self.store.get("muted", False)))
        if dropped:
            log.info("suppressed: %s", dropped)

        out = []
        for f in send:
            self.store.record_fire(f.rule_id, f.severity, f.value, f.text)
            icon = SEVERITY_ICON.get(f.severity, "·")
            out.append((f"{icon} *{esc(f.title)}*\n"
                        f"_{f.severity.upper()} · {f.group} · {stamp()}_\n\n{f.text}",
                        f.rule_id))
        return out

    def degraded_warning(self) -> str | None:
        """Iranian sources down: worth saying once an hour, not every poll."""
        snap = self.last_snapshot
        if not snap:
            return None
        down = [n for n in snap.degraded if n in ("brsapi_gold", "brsapi_havaleh", "tse")]
        if not down:
            return None
        if time.time() - float(self.store.get("last_down_warn", 0) or 0) < 3600:
            return None
        self.store.set("last_down_warn", time.time())
        return (f"⚠️ Iranian data sources down: `{', '.join(down)}`\n"
                f"Desk rules that need them are not being evaluated. "
                f"`/health` for detail.")

    def status(self) -> dict:
        """Compact dict for the bot's /stats and its health endpoint."""
        snap = self.last_snapshot
        return {
            "enabled": True,
            "rules": len(self.engine.rules),
            "poll_seconds": settings.poll_seconds,
            "last_poll_age_s": int(time.time() - self.last_poll) if self.last_poll else None,
            "sources_ok": sum(1 for ok, _, _ in (snap.health.values() if snap else []) if ok),
            "sources_total": len(snap.health) if snap else 0,
            "degraded": snap.degraded if snap else [],
            "last_error": self.last_error,
        }

    # ───────────────────────── commands ─────────────────────────
    # Each returns the text to send. `None` is never returned.
    def _values(self) -> dict:
        return self.last_snapshot.values if self.last_snapshot else {}

    def cmd_now(self, arg: str = "") -> str:
        snap = self.last_snapshot
        if not snap:
            return "No desk snapshot yet — first poll pending."
        msg = f"*MARKET* · {stamp()}\n\n{snapshot_block(snap.values)}"
        if snap.degraded:
            msg += f"\n\n⚠️ degraded: `{', '.join(snap.degraded)}`"
        for n in snap.notes[:3]:
            msg += f"\n_{esc(n)}_"
        return msg

    def cmd_gates(self, arg: str = "") -> str:
        return gates_block(self._values()) if self.last_snapshot else "No desk snapshot yet."

    def cmd_ladder(self, arg: str = "") -> str:
        return ladder_block(self._values()) if self.last_snapshot else "No desk snapshot yet."

    def cmd_parity(self, arg: str = "") -> str:
        v = self._values()
        oz, usd = v.get("xau_usd"), v.get("usd_free")
        mkt = v.get("gold18k_toman")
        par, gap = v.get("gold_parity_toman"), v.get("gold_parity_gap_pct")
        if None in (oz, usd, par, mkt, gap):
            return "Missing inputs for parity — check `/health`."
        txt = (f"*PARITY*\n\n"
               f"`({oz:,.2f} / 31.1035) x 0.75 x {usd:,.0f}`\n"
               f"`= {par:,.0f}` toman/g fair value\n"
               f"`market  {mkt:,.0f}`\n"
               f"`gap     {gap:+.2f}%`\n\n")
        if gap <= -15:
            txt += "🟢 *Deep discount.* This is the setup that paid +20.5% on 10 Shahrivar."
        elif gap <= -5:
            txt += "🟢 Discount — worth a tranche."
        elif gap >= 5:
            txt += "🔴 Premium — you are paying over the metal. Do not add."
        else:
            txt += "· At parity. No edge from the gap; decide on the ladder instead."
        return txt

    def cmd_funds(self, arg: str = "") -> str:
        v = self._values()
        rows = [("طلا", "tala_price", "tala_nav", "tala_bubble_pct", "bubble"),
                ("پلاتا", "plata_price", "plata_nav", "plata_premium_pct", "premium"),
                ("اهرم", "ahrom_price", "ahrom_nav", "ahrom_discount_pct", "discount")]
        L = ["*FUNDS*"]
        for fa, pk, nk, gk, lab in rows:
            p, n, g = v.get(pk), v.get(nk), v.get(gk)
            if p is None:
                L.append(f"`— no data`  {fa}")
                continue
            d = v.get(pk.replace("_price", "_day_pct"))
            dd = f"  day `{d:+.1f}%`" if isinstance(d, (int, float)) else ""
            if n and g is not None:
                L.append(f"`{p:,.0f}` / NAV `{n:,.0f}`  {lab} `{g:+.2f}%`{dd}  {fa}")
            else:
                L.append(f"`{p:,.0f}`  NAV unavailable  {fa}")
        if v.get("any_fund_at_limit"):
            L.append(f"\n⚠️ limit: {esc(v.get('limit_fund_names'))}")
        return "\n".join(L)

    def cmd_rules(self, arg: str = "") -> str:
        rows = self.engine.status_table(self._values())
        by_group: dict[str, list] = {}
        for g, t, s, armed in rows:
            by_group.setdefault(g, []).append(("✓" if armed else "·", t, s))
        out = ["*RULES*"]
        for g, items in by_group.items():
            out.append(f"\n*{g.upper()}*")
            for mark, t, s in items:
                out.append(f"{mark} {esc(t)}\n   `{s}`")
        return "\n".join(out)

    def cmd_fires(self, arg: str = "") -> str:
        rows = self.store.recent_fires(12)
        if not rows:
            return "No desk signals recorded yet."
        L = ["*RECENT DESK SIGNALS*"]
        for ts, rid, sev, text in rows:
            ago = int((time.time() - ts) / 60)
            head = (text or "").strip().split("\n")[0][:80]
            L.append(f"{SEVERITY_ICON.get(sev,'·')} `{rid}` · {ago}m ago\n   {esc(head)}")
        return "\n".join(L)

    def cmd_health(self, arg: str = "") -> str:
        snap = self.last_snapshot
        if not snap:
            err = f"\nlast error: `{esc(self.last_error)}`" if self.last_error else ""
            return f"No desk poll has completed yet.{err}"
        L = [f"*DESK HEALTH* · {stamp()}",
             f"last poll `{int(time.time()-self.last_poll)}s` ago · "
             f"every `{settings.poll_seconds}s`", ""]
        for name, (ok, detail, secs) in snap.health.items():
            L.append(f"{'🟢' if ok else '🔴'} `{name}` — {esc(detail)} ({secs:.1f}s)")
        if snap.notes:
            L.append("\n*NOTES*")
            L += [f"· {esc(n)}" for n in snap.notes]
        if self.store.get("muted", False):
            L.append("\n🔇 muted — only `critical` rules are being sent.")
        L.append("\n_Iranian feeds may block non-Iranian IPs. If they stay red, "
                 "see bot/desk/README.md > Blocked IPs._")
        return "\n".join(L)

    def cmd_probe(self, arg: str = "") -> str:
        name = (arg or "").split()[0] if arg.strip() else ""
        if not name:
            return f"Sources: `{', '.join(LAST_RAW) or 'none captured yet'}`"
        raw = LAST_RAW.get(name)
        if not raw:
            return f"No raw capture for `{name}`. Known: `{', '.join(LAST_RAW) or 'none'}`"
        return f"`{name}` raw:\n```\n{raw[:3500]}\n```"

    def cmd_set(self, arg: str = "") -> str:
        """Accepts several key/value pairs at once.

        Supplying fund price and NAV by hand is six values; making that six
        separate messages is how people stop doing it.
        """
        parts = (arg or "").replace("=", " ").split()
        if len(parts) < 2 or len(parts) % 2:
            return ("Usage: `/set iran_cpi_yoy 84.2`\n"
                    "Several at once: `/set tala_price 1556199 tala_nav 1578000`")
        done, bad = [], []
        for k, raw in zip(parts[::2], parts[1::2]):
            try:
                val = float(raw.replace(",", "").replace("٬", ""))
            except ValueError:
                bad.append(k)
                continue
            self.store.set(f"manual.{k}", val)
            done.append(f"`{k}` = `{val:,.4g}`")
        out = []
        if done:
            out.append("Set " + ", ".join(done) + " (persisted, applied on the "
                       "next poll).")
        if bad:
            out.append("Not numeric, skipped: " + ", ".join(f"`{k}`" for k in bad))
        return "\n".join(out)

    def cmd_thresh(self, arg: str = "") -> str:
        parts = (arg or "").split()
        if len(parts) < 2:
            return "Usage: `/thresh ladder_rung_2 20800000`"
        rid = parts[0]
        try:
            nums = [float(x.replace(",", "")) for x in parts[1:]]
        except ValueError:
            return "Thresholds must be numeric."
        val = nums[0] if len(nums) == 1 else nums
        if not self.engine.set_threshold(rid, val):
            return f"Unknown rule id `{rid}`. `/rules` lists them."
        self.store.set(f"thresh.{rid}", val)
        return f"Override set: `{rid}` -> `{val}`."

    def cmd_probeurl(self, arg: str = "") -> str:
        """Test a candidate data source from the deployment's own IP.

        The blocker with Iranian hosts is reachability, not schema, and only
        this box can answer whether a host replies to it. Owner-gated in
        main.py; see probe.py for the SSRF guard.
        """
        parts = (arg or "").split(maxsplit=1)
        if not parts:
            return ("Usage: `/probeurl https://host/path` — fetches it from this "
                    "server and lists the numeric fields it found.\n"
                    "Add a filter to narrow a long list: "
                    "`/probeurl https://host/path nav`\n\n"
                    "Find the URL: open the site in a desktop browser, "
                    "DevTools → Network → Fetch/XHR, and copy the request that "
                    "returns the numbers (not the page itself).")
        url, needle = parts[0], (parts[1].strip() if len(parts) > 1 else "")
        try:
            return probe_url(url, needle)
        except ProbeRefused as e:
            return f"Refused: {e}"
        except Exception as e:                            # noqa: BLE001
            # The failure IS the answer here — a timeout or a reset is how you
            # learn this host does not serve Railway.
            return (f"`{type(e).__name__}` — {str(e)[:400]}\n\n"
                    f"_If this is a timeout or a connection reset, that host "
                    f"does not answer this deployment. Same situation as brsapi "
                    f"and TSETMC; see README > Blocked IPs._")

    def cmd_tgju(self, arg: str = "") -> str:
        """Ask tgju what it will actually serve, one slug at a time.

        tgju is the only Iranian host answering this deployment, so before
        hunting a new provider for the fund quotes it is worth finding out
        whether tgju itself carries them. Slug names are not documented
        anywhere, and guessing is free if checking is one message.
        """
        spec = dict(self.collector.sources.get("tgju") or {})
        if not spec.get("url"):
            return "No `tgju` source in sources.yaml."
        syms = [w.strip(" ,") for w in (arg or "").split() if w.strip(" ,")]
        scanning_defaults = not syms
        syms = syms[:24] or SCAN_CANDIDATES
        spec["timeout"] = min(int(spec.get("timeout", 15)), 12)

        rows = tgju_scan(spec, syms, "tgju" in self.collector.relay_targets)
        live = [(s_, c, d) for s_, c, d, e in rows if e is None]
        dead = [(s_, e) for s_, c, d, e in rows if e is not None]

        out = [f"*tgju slug scan* — {len(live)}/{len(rows)} answered"]
        if live:
            out.append("\n*SERVES DATA*")
            for sym, close, date in sorted(live):
                out.append(f"`{sym}` = `{close:,.0f}`  _{date}_")
        if dead:
            out.append("\n*NOTHING*")
            out.append("`" + "` `".join(sym for sym, _ in sorted(dead)) + "`")
        if scanning_defaults:
            out.append("\n_Controls `price_dollar_rl`, `mesghal` and `ons` must "
                       "be in the SERVES list — if they are not, tgju itself is "
                       "down and this scan says nothing._")
        out.append("\nA slug that serves data goes straight into the `tgju` "
                   "fields block in `sources.yaml`, then `/reload`. "
                   "Try more with `/tgju slug1 slug2`.")
        return "\n".join(out)

    def cmd_mute(self, arg: str = "") -> str:
        self.store.set("muted", True)
        return "Desk muted. `critical` rules still come through. `/unmute` to restore."

    def cmd_unmute(self, arg: str = "") -> str:
        self.store.set("muted", False)
        return "Desk unmuted."

    def cmd_reload(self, arg: str = "") -> str:
        self.engine.reload(load_yaml("rules.yaml"))
        self._restore_thresholds()
        self.collector.reload()
        return (f"Desk config reloaded: {len(self.engine.rules)} rules, "
                f"{len(self.collector.sources)} source blocks.")

    def cmd_help(self, arg: str = "") -> str:
        return HELP

    def commands(self) -> dict:
        return {
            "/now": self.cmd_now,
            "/gates": self.cmd_gates,
            "/ladder": self.cmd_ladder,
            "/parity": self.cmd_parity,
            "/funds": self.cmd_funds,
            "/rules": self.cmd_rules,
            "/fires": self.cmd_fires,
            "/health": self.cmd_health,
            "/probe": self.cmd_probe,
            "/probeurl": self.cmd_probeurl,
            "/tgju": self.cmd_tgju,
            "/set": self.cmd_set,
            "/thresh": self.cmd_thresh,
            "/mute": self.cmd_mute,
            "/unmute": self.cmd_unmute,
            "/reload": self.cmd_reload,
            "/desk": self.cmd_help,
        }
