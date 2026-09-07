"""Declarative rules engine. Reads config/rules.yaml, evaluates against a Snapshot."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)

SEVERITY_ORDER = {"info": 0, "watch": 1, "action": 2, "critical": 3}
SEVERITY_ICON = {"info": "·", "watch": "◎", "action": "▲", "critical": "✕"}


@dataclass
class Fire:
    rule_id: str
    group: str
    title: str
    severity: str
    text: str
    value: float | None


def _cmp(op: str, cur: float, prev: float | None, target: Any) -> bool:
    if op == "lt":
        return cur < target
    if op == "gt":
        return cur > target
    if op == "abs_gt":
        return abs(cur) > target
    if op == "between":
        lo, hi = target
        return lo <= cur <= hi
    if op == "outside":
        lo, hi = target
        return cur < lo or cur > hi
    if op == "crosses_down":
        return prev is not None and prev > target >= cur
    if op == "crosses_up":
        return prev is not None and prev < target <= cur
    raise ValueError(f"unknown op {op!r}")


class SafeDict(dict):
    def __missing__(self, key):
        return "n/a"


def _format(template: str, values: dict) -> str:
    """Formats without exploding when a metric is missing."""
    try:
        return template.format_map(SafeDict(values)).strip()
    except (ValueError, TypeError):
        # a missing numeric with a format spec ("{x:.1f}" on "n/a")
        safe = {k: (v if isinstance(v, (int, float)) else 0) for k, v in values.items()}
        try:
            return template.format_map(SafeDict(safe)).strip()
        except Exception:                       # noqa: BLE001
            return template


class RulesEngine:
    def __init__(self, cfg: dict):
        self.reload(cfg)

    def reload(self, cfg: dict) -> None:
        self.meta = cfg.get("meta", {})
        self.rules = [r for r in cfg.get("rules", []) if r.get("enabled", True)]
        self.overrides: dict[str, Any] = {}

    def set_threshold(self, rule_id: str, value: Any) -> bool:
        for r in self.rules:
            if r["id"] == rule_id:
                self.overrides[rule_id] = value
                return True
        return False

    def target_for(self, rule: dict) -> Any:
        return self.overrides.get(rule["id"], rule["value"])

    def evaluate(self, values: dict, prev: dict | None) -> list[Fire]:
        fires: list[Fire] = []
        prev = prev or {}
        for r in self.rules:
            metric = r["metric"]
            cur = values.get(metric)
            if cur is None or not isinstance(cur, (int, float)):
                continue
            try:
                hit = _cmp(r["op"], float(cur), prev.get(metric), self.target_for(r))
            except Exception as e:                # noqa: BLE001
                log.warning("rule %s failed: %s", r["id"], e)
                continue
            if hit:
                fires.append(Fire(
                    rule_id=r["id"], group=r.get("group", "misc"),
                    title=r.get("title", r["id"]), severity=r.get("severity", "info"),
                    text=_format(r.get("message", r.get("title", "")), values),
                    value=float(cur),
                ))
        fires.sort(key=lambda f: -SEVERITY_ORDER.get(f.severity, 0))
        return fires

    def cooldown_for(self, rule_id: str) -> int:
        for r in self.rules:
            if r["id"] == rule_id:
                return int(r.get("cooldown", 3600))
        return 3600

    def status_table(self, values: dict) -> list[tuple[str, str, str, bool]]:
        """(group, title, 'current vs target', armed?) for /rules."""
        rows = []
        for r in self.rules:
            cur = values.get(r["metric"])
            tgt = self.target_for(r)
            tgt_s = f"{tgt[0]}–{tgt[1]}" if isinstance(tgt, list) else f"{tgt}"
            cur_s = f"{cur:,.2f}" if isinstance(cur, (int, float)) else "n/a"
            armed = isinstance(cur, (int, float))
            rows.append((r.get("group", "misc"), r.get("title", r["id"]),
                         f"{cur_s}  |  {r['op']} {tgt_s}", armed))
        return rows
