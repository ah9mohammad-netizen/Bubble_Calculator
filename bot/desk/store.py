"""SQLite history + signal dedupe + persisted manual overrides.

One change from the upstream desk: every method holds a lock. Upstream ran
single-threaded on an event loop; here the poll thread writes snapshots while
the command thread services /set, /thresh and /mute. A sqlite3 connection
opened with check_same_thread=False is not safe against concurrent use, and
the failure mode is an interleaved cursor rather than a clean exception.
"""
from __future__ import annotations
import json, sqlite3, threading, time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
  ts        INTEGER PRIMARY KEY,
  payload   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS fires (
  id        INTEGER PRIMARY KEY AUTOINCREMENT,
  ts        INTEGER NOT NULL,
  rule_id   TEXT NOT NULL,
  severity  TEXT NOT NULL,
  value     REAL,
  text      TEXT
);
CREATE INDEX IF NOT EXISTS idx_fires_rule ON fires(rule_id, ts DESC);
CREATE TABLE IF NOT EXISTS kv (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, timeout=15)
        self.lock = threading.RLock()
        self.db.executescript(SCHEMA)
        self.db.commit()

    # ---- snapshots ----
    def save_snapshot(self, values: dict) -> None:
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO snapshots(ts,payload) VALUES(?,?)",
                            (int(time.time()), json.dumps(values, default=str)))
            self.db.execute("DELETE FROM snapshots WHERE ts < ?",
                            (int(time.time()) - 90 * 86400,))
            self.db.commit()

    def last_values(self, skip: int = 0) -> dict | None:
        with self.lock:
            row = self.db.execute(
                "SELECT payload FROM snapshots ORDER BY ts DESC LIMIT 1 OFFSET ?", (skip,)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def series(self, metric: str, hours: int = 48) -> list[tuple[int, float]]:
        cutoff = int(time.time()) - hours * 3600
        with self.lock:
            rows = self.db.execute(
                "SELECT ts,payload FROM snapshots WHERE ts>=? ORDER BY ts",
                (cutoff,)).fetchall()
        out = []
        for ts, payload in rows:
            v = json.loads(payload).get(metric)
            if isinstance(v, (int, float)):
                out.append((ts, float(v)))
        return out

    # ---- fires / cooldown ----
    def last_fire_ts(self, rule_id: str) -> int | None:
        with self.lock:
            row = self.db.execute(
                "SELECT ts FROM fires WHERE rule_id=? ORDER BY ts DESC LIMIT 1", (rule_id,)
            ).fetchone()
        return row[0] if row else None

    def record_fire(self, rule_id: str, severity: str, value, text: str) -> None:
        with self.lock:
            self.db.execute(
                "INSERT INTO fires(ts,rule_id,severity,value,text) VALUES(?,?,?,?,?)",
                (int(time.time()), rule_id, severity, value, text))
            self.db.commit()

    def recent_fires(self, limit: int = 15) -> list[tuple]:
        with self.lock:
            return self.db.execute(
                "SELECT ts,rule_id,severity,text FROM fires ORDER BY ts DESC LIMIT ?",
                (limit,)).fetchall()

    # ---- kv ----
    def set(self, k: str, v) -> None:
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO kv(k,v) VALUES(?,?)",
                            (k, json.dumps(v)))
            self.db.commit()

    def get(self, k: str, default=None):
        with self.lock:
            row = self.db.execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
        return json.loads(row[0]) if row else default

    def all_manual(self) -> dict:
        return {k[7:]: json.loads(v) for k, v in self.kv_prefix("manual.")}

    def kv_prefix(self, prefix: str) -> list[tuple[str, str]]:
        with self.lock:
            return self.db.execute("SELECT k,v FROM kv WHERE k LIKE ?",
                                   (prefix + "%",)).fetchall()
