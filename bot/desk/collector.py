"""Runs every source, merges into one Snapshot, records health.

Upstream ran the sources as asyncio tasks. Here they run on a small thread
pool instead, because the host bot is a threaded `requests` program and
introducing an event loop next to its poller would be a second concurrency
model to reason about for no gain — the work is four blocking GETs.
"""
from __future__ import annotations
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from .config import load_yaml
from .models import Snapshot
from .derive import derive, sanity_warnings
from .http_source import fetch_http_source
from .tse import fetch_tse
from .tgju import fetch_tgju

log = logging.getLogger("desk.collector")
LAST_RAW: dict[str, str] = {}          # for /probe

# Iranian fields that are allowed to go missing for a poll or two. They are
# carried forward from the last good snapshot rather than dropped, because a
# hole in NAV reads downstream as "no premium" instead of "unknown premium".
CARRY_FORWARD = ("usd_havaleh", "tala_nav", "plata_nav", "ahrom_nav", "tedpix",
                 "tala_price", "plata_price", "ahrom_price")


class Collector:
    def __init__(self, store):
        self.store = store
        self.pool = ThreadPoolExecutor(max_workers=4,
                                       thread_name_prefix="desk-src")
        self.reload()

    def reload(self) -> None:
        cfg = load_yaml("sources.yaml")
        self.sources = cfg["sources"]
        self.relay_targets = (cfg.get("relay") or {}).get("applies_to", [])

    def _run(self, name: str, spec: dict):
        if name == "tgju":
            return fetch_tgju(spec, self.store, name in self.relay_targets)
        if name == "tse":
            return fetch_tse(spec, self.store, name in self.relay_targets)
        return fetch_http_source(name, spec, self.relay_targets)

    def collect(self) -> Snapshot:
        snap = Snapshot()
        futures = {}
        started: dict[str, float] = {}

        for name, spec in self.sources.items():
            if name == "manual" or not spec.get("enabled", True):
                continue
            started[name] = time.monotonic()
            futures[name] = self.pool.submit(self._run, name, spec)

        for name, fut in futures.items():
            try:
                values, raw = fut.result(timeout=90)
                LAST_RAW[name] = raw
                if not values:
                    snap.health[name] = (False, "connected but no fields mapped — run /probe",
                                         time.monotonic() - started[name])
                else:
                    snap.values.update(values)
                    snap.health[name] = (True, f"{len(values)} fields",
                                         time.monotonic() - started[name])
            except Exception as e:                       # noqa: BLE001
                snap.health[name] = (False, f"{type(e).__name__}: {e}",
                                     time.monotonic() - started[name])
                log.warning("source %s failed: %s", name, e)

        # manual values: yaml defaults, then DB overrides
        for k, v in (self.sources.get("manual") or {}).items():
            snap.values.setdefault(k, v)
        for k, v in self.store.all_manual().items():
            snap.values[k] = v

        prev = self.store.last_values() or {}
        for k in CARRY_FORWARD:
            if snap.values.get(k) is None and prev.get(k) is not None:
                snap.values[k] = prev[k]
                snap.notes.append(f"{k} carried forward from last snapshot")

        snap.values = derive(snap.values)
        snap.notes.extend(sanity_warnings(snap.values))
        return snap

    def close(self) -> None:
        self.pool.shutdown(wait=False)
