"""Price feed: tgju.org (Iran) + world gold spot, with fallbacks."""
from __future__ import annotations
import logging, re, json
from datetime import datetime, timezone, timedelta
from typing import Optional
import requests

log = logging.getLogger("datafeed")

TGJU = "https://api.tgju.org/v1/market/indicator/summary-table-data/{sym}"
HEAD = {"User-Agent": "Mozilla/5.0 (compatible; GoldBot/1.0)", "Accept": "application/json"}
TIMEOUT = 25

SYMBOLS = {
    "quarter": "rob",              # ربع سکه
    "mesghal": "mesghal",          # مثقال آب‌شده
    "usd":     "price_dollar_rl",  # USD/IRR free market
    "spot":    "ons",              # XAU/USD
}


def _num(s) -> Optional[float]:
    if s is None:
        return None
    t = re.sub(r"[^\d.\-]", "", str(s))
    if not t or t in {"-", "."}:
        return None
    try:
        return float(t)
    except ValueError:
        return None


def fetch_series(sym: str, rows: int = 80) -> list[tuple[str, float]]:
    """Return [(YYYY-MM-DD, close)] oldest-first."""
    r = requests.get(TGJU.format(sym=sym), headers=HEAD, timeout=TIMEOUT,
                     params={"start": 0, "length": rows})
    r.raise_for_status()
    data = r.json().get("data", [])
    out = []
    for row in data:
        if len(row) < 8:
            continue
        close = _num(row[3])
        greg = str(row[6]).replace("/", "-").strip()
        if close and re.match(r"^\d{4}-\d{2}-\d{2}$", greg):
            out.append((greg, close))
    out.sort(key=lambda x: x[0])
    return out


def _spot_fallback() -> Optional[float]:
    """Backup XAU/USD if tgju's `ons` is unavailable."""
    for url, pick in (
        ("https://api.gold-api.com/price/XAU", lambda j: j.get("price")),
        ("https://api.coingecko.com/api/v3/simple/price?ids=gold&vs_currencies=usd",
         lambda j: j.get("gold", {}).get("usd")),
    ):
        try:
            j = requests.get(url, headers=HEAD, timeout=15).json()
            v = _num(pick(j))
            if v and v > 100:
                return v
        except Exception as e:
            log.warning("spot fallback %s failed: %s", url, e)
    return None


def fetch_latest() -> dict:
    """Latest snapshot of all four instruments. Missing keys => None."""
    snap: dict = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    errors = []
    for key, sym in SYMBOLS.items():
        try:
            s = fetch_series(sym, rows=5)
            if s:
                snap[key] = s[-1][1]
                snap[f"{key}_date"] = s[-1][0]
            else:
                errors.append(f"{key}: empty")
        except Exception as e:
            errors.append(f"{key}: {type(e).__name__}")
            log.warning("fetch %s failed: %s", sym, e)

    if not snap.get("spot"):
        fb = _spot_fallback()
        if fb:
            snap["spot"], snap["spot_src"] = fb, "fallback"

    # Tehran business date
    tehran = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
    snap["date"] = snap.get("mesghal_date") or tehran.strftime("%Y-%m-%d")

    # RP compares two instruments, so it is only meaningful if BOTH quotes are
    # from the same session. tgju updates `rob` less often than `mesghal`
    # (the quarter coin is quoted in coarse 5m-toman steps and often does not
    # print at all), so the naive "latest row of each" pairing silently
    # compares a stale coin against a fresh mesghal. Flag it.
    qd, md = snap.get("quarter_date"), snap.get("mesghal_date")
    snap["stale_quarter"] = bool(qd and md and qd != md)
    snap["quarter_lag_from"] = qd if snap["stale_quarter"] else None

    snap["errors"] = errors
    snap["ok"] = bool(snap.get("quarter") and snap.get("mesghal"))
    return snap


def backfill(rows: int = 400) -> dict[str, dict[str, float]]:
    """{date: {quarter,mesghal,usd,spot}} for seeding/repair."""
    merged: dict[str, dict[str, float]] = {}
    for key, sym in SYMBOLS.items():
        try:
            for d, v in fetch_series(sym, rows=rows):
                merged.setdefault(d, {})[key] = v
        except Exception as e:
            log.warning("backfill %s failed: %s", sym, e)
    return merged
