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
`/set k v`  set a manual value (e.g. `/set iran_cpi_yoy 84.2`)
`/thresh id v`  override a rule threshold
`/mute` `/unmute`
`/reload`   re-read config from disk
"""


class Desk:
    """Owns the desk's store, rules engine and collector."""

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
        parts = (arg or "").split()
        if len(parts) < 2:
            return "Usage: `/set iran_cpi_yoy 84.2`"
        k, raw = parts[0], parts[1]
        try:
            val = float(raw.replace(",", ""))
        except ValueError:
            return "Value must be numeric."
        self.store.set(f"manual.{k}", val)
        return f"Set `{k}` = `{val:,.4g}` (persisted, applied on the next poll)."

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
            "/set": self.cmd_set,
            "/thresh": self.cmd_thresh,
            "/mute": self.cmd_mute,
            "/unmute": self.cmd_unmute,
            "/reload": self.cmd_reload,
            "/desk": self.cmd_help,
        }
