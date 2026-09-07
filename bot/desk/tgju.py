"""tgju.org — the one Iranian source proven to answer from this deployment.

`bot/datafeed.py` has been pulling this exact endpoint from this exact Railway
service since the bot went live, which makes it the only Iranian feed here with
production evidence behind it rather than a hopeful URL. When brsapi and
TSETMC stopped answering, this is what the desk falls back to.

Shape (same as datafeed.py reads):

    GET /v1/market/indicator/summary-table-data/<symbol>?start=0&length=5
    {"data": [[open, low, high, close, change, change%, "YYYY/MM/DD", jalali], ...]}

One request per symbol, so the symbol map lives in config/sources.yaml under
`fields:` and each entry names its own tgju slug. Columns are config too
(`close_index`, `date_index`), because tgju has reordered them before.

**Units.** tgju quotes Iranian instruments in RIAL. The desk works in TOMAN.
Every Iranian field therefore carries `scale: 0.1`. Getting this wrong is a
clean factor of ten, which is exactly what `derive.sanity_warnings()` catches
against parity — but catching it is a worse outcome than setting it right.
"""
from __future__ import annotations
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from .http_source import get_json, num, relay_wrap

log = logging.getLogger("desk.tgju")

_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="desk-tgju")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _latest(rows: list, close_ix: int, date_ix: int):
    """Newest (close, date) from a summary-table payload, oldest-first sort.

    tgju returns newest-first today, but has served the other order before,
    so sort rather than trusting the position.
    """
    parsed = []
    for row in rows:
        if not isinstance(row, (list, tuple)) or len(row) <= max(close_ix, date_ix):
            continue
        close = num(row[close_ix])
        date = str(row[date_ix]).replace("/", "-").strip()
        if close and _DATE.match(date):
            parsed.append((date, close))
    if not parsed:
        return None, None
    parsed.sort()
    return parsed[-1][1], parsed[-1][0]


def _one(spec: dict, sym: str, via_relay: bool):
    url = spec["url"].format(symbol=sym)
    headers = {}
    if via_relay:
        url, headers = relay_wrap(url)
    data, raw = get_json(url, params={"start": 0, "length": spec.get("rows", 5)},
                         timeout=spec.get("timeout", 15), headers=headers)
    close, date = _latest(data.get("data") or [],
                          spec.get("close_index", 3), spec.get("date_index", 6))
    return close, date, raw


def _spread_days(dates: list[str]) -> float | None:
    """Widest gap between the session dates behind the quotes we just paired.

    The bot learned this the hard way once already: pairing a stale ربع سکه
    against a fresh مثقال silently produced a fake relative premium. Parity
    has the same exposure — a two-day-old 18k print against today's dollar is
    not a discount, it is a stale quote. Measure it so a rule can see it.
    """
    ds = sorted({d for d in dates if d})
    if len(ds) < 2:
        return 0.0 if ds else None
    try:
        a = datetime.strptime(ds[0], "%Y-%m-%d")
        b = datetime.strptime(ds[-1], "%Y-%m-%d")
    except ValueError:
        return None
    return (b - a).days


# Candidate slugs to scan with /tgju. tgju is the only Iranian host that
# answers this deployment, so before hunting a new provider it is worth
# finding out what tgju itself will serve. These are guesses in tgju's own
# naming style, not documented endpoints — the scan reports which ones
# actually return rows, which is the only thing that settles it.
SCAN_CANDIDATES = [
    # the funds we are missing
    "tala", "sandogh_tala", "fund_tala", "etf_tala", "gold_fund", "lotus_tala",
    "plata", "sandogh_noghre", "silver_fund",
    "ahrom", "sandogh_ahrom", "leverage_fund",
    # already in sources.yaml but unconfirmed — the scan settles these too
    "geram18", "silver", "sekee", "bourse",
    # known-good controls: if these come back empty the scan itself is broken
    "price_dollar_rl", "mesghal", "ons",
]


def probe_symbol(spec: dict, sym: str, via_relay: bool = False) -> tuple:
    """(close, date, error) for one slug. Never raises."""
    try:
        close, date, _ = _one(spec, sym, via_relay)
    except Exception as e:                                 # noqa: BLE001
        return None, None, f"{type(e).__name__}: {str(e)[:80]}"
    if close is None:
        return None, None, "200 but no usable row"
    return close, date, None


def scan(spec: dict, symbols: list[str], via_relay: bool = False) -> list[tuple]:
    """Try many slugs at once. Returns [(sym, close, date, error)]."""
    futures = {s: _POOL.submit(probe_symbol, spec, s, via_relay) for s in symbols}
    out = []
    for sym, fut in futures.items():
        try:
            close, date, err = fut.result(timeout=spec.get("timeout", 15) + 10)
        except Exception as e:                             # noqa: BLE001
            close, date, err = None, None, f"{type(e).__name__}"
        out.append((sym, close, date, err))
    return out


def fetch_tgju(spec: dict, store=None, via_relay: bool = False) -> tuple[dict, str]:
    out: dict[str, float] = {}
    raw_bits: list[str] = []
    dates: list[str] = []
    errors: list[str] = []

    fields = spec.get("fields") or {}
    futures = {name: _POOL.submit(_one, spec, fs["symbol"], via_relay)
               for name, fs in fields.items() if fs.get("symbol")}

    for name, fut in futures.items():
        fs = fields[name]
        try:
            close, date, raw = fut.result(timeout=spec.get("timeout", 15) + 10)
        except Exception as e:                             # noqa: BLE001
            errors.append(f"{name}({fs['symbol']}): {type(e).__name__}: {e}")
            continue
        raw_bits.append(f"{name} <- {fs['symbol']} = {close} @ {date}\n{raw[:300]}")
        if close is None:
            errors.append(f"{name}({fs['symbol']}): no usable row — check "
                          f"close_index/date_index")
            continue
        out[name] = close * float(fs.get("scale", 1))
        # Only quotes that feed parity need to be same-session with each other.
        if fs.get("dated", True):
            dates.append(date)

    spread = _spread_days(dates)
    if spread is not None:
        out["tgju_quote_spread_days"] = float(spread)

    if errors:
        raw_bits.append("ERRORS\n" + "\n".join(errors))
    if not out or set(out) == {"tgju_quote_spread_days"}:
        raise RuntimeError(errors[0] if errors else "no fields mapped")
    return out, "\n\n".join(raw_bits)[:4000]
