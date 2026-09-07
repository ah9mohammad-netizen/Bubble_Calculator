"""Cooldown + quiet-hours gating for outbound desk signals.

Identical logic to the upstream desk; `pytz` is replaced by the bot's own
fixed Tehran offset (see tehran.py).
"""
from __future__ import annotations
import time

from .tehran import minutes_of_day


def in_quiet_hours(window) -> bool:
    if not window:
        return False
    (sh, sm), (eh, em) = window
    start_m, end_m = sh * 60 + sm, eh * 60 + em
    cur = minutes_of_day()
    return start_m <= cur < end_m if start_m < end_m else (cur >= start_m or cur < end_m)


def gate(fires, store, engine, quiet_window, muted: bool):
    """Returns (to_send, suppressed_reasons)."""
    send, dropped = [], []
    now = int(time.time())
    quiet = in_quiet_hours(quiet_window)
    for f in fires:
        last = store.last_fire_ts(f.rule_id)
        cd = engine.cooldown_for(f.rule_id)
        if last and now - last < cd:
            dropped.append((f.rule_id, f"cooldown {int((cd-(now-last))/60)}m left"))
            continue
        if f.severity != "critical":
            if muted:
                dropped.append((f.rule_id, "muted"))
                store.record_fire(f.rule_id, f.severity, f.value, f.text)
                continue
            if quiet:
                dropped.append((f.rule_id, "quiet hours"))
                continue
        send.append(f)
    return send, dropped
