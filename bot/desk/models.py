"""Typed snapshot of the market at one instant."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class Snapshot:
    ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    values: dict[str, float] = field(default_factory=dict)
    # per-source health: name -> (ok, detail, age_seconds)
    health: dict[str, tuple[bool, str, float]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def get(self, k: str, default: Any = None) -> Any:
        v = self.values.get(k)
        return default if v is None else v

    def has(self, *keys: str) -> bool:
        return all(self.values.get(k) is not None for k in keys)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ts"] = self.ts.isoformat()
        return d

    @property
    def degraded(self) -> list[str]:
        return [n for n, (ok, _, _) in self.health.items() if not ok]
