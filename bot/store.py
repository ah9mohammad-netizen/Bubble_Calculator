"""Persistence on the Railway volume (default /data)."""
from __future__ import annotations
import csv, json, os, shutil, logging
from pathlib import Path
from typing import Optional

log = logging.getLogger("store")

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
PRICES_CSV = DATA_DIR / "prices.csv"
SIGNALS_CSV = DATA_DIR / "signals.csv"
STATE_JSON = DATA_DIR / "state.json"

PRICE_COLS = ["date", "quarter", "mesghal", "usd", "spot"]
SIGNAL_COLS = ["date", "ts", "from_pos", "to_pos", "layer", "rp", "vol", "reason"]

DEFAULT_STATE = {
    "position": "MESGHAL",   # QUARTER | MESGHAL | USD
    "since": None,
    "last_pref": "MESGHAL",
    "last_l1_date": None,
    "last_l2_date": None,
    "last_daily_report": None,
    "subscribers": [],
}


def init(seed_csv: Optional[Path] = None) -> None:
    """Create the volume layout; seed price history on first boot."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.error("cannot create %s (%s) — falling back to ./data_local", DATA_DIR, e)
        _fallback()
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    if not PRICES_CSV.exists():
        if seed_csv and Path(seed_csv).exists():
            shutil.copy(seed_csv, PRICES_CSV)
            log.info("seeded prices.csv from %s", seed_csv)
        else:
            _write_header(PRICES_CSV, PRICE_COLS)
    if not SIGNALS_CSV.exists():
        _write_header(SIGNALS_CSV, SIGNAL_COLS)
    if not STATE_JSON.exists():
        save_state(DEFAULT_STATE.copy())


def _fallback():
    global DATA_DIR, PRICES_CSV, SIGNALS_CSV, STATE_JSON
    DATA_DIR = Path("./data_local")
    PRICES_CSV = DATA_DIR / "prices.csv"
    SIGNALS_CSV = DATA_DIR / "signals.csv"
    STATE_JSON = DATA_DIR / "state.json"


def _write_header(p: Path, cols: list[str]):
    with p.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(cols)


# ---------------- prices ----------------
def load_prices() -> list[dict]:
    if not PRICES_CSV.exists():
        return []
    with PRICES_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        rec = {"date": (r.get("date") or "").strip()}
        if not rec["date"]:
            continue
        for k in ("quarter", "mesghal", "usd", "spot"):
            v = (r.get(k) or "").strip()
            try:
                rec[k] = float(v) if v else None
            except ValueError:
                rec[k] = None
        out.append(rec)
    out.sort(key=lambda r: r["date"])
    return out


def upsert_price(date: str, quarter=None, mesghal=None, usd=None, spot=None) -> None:
    """Insert or merge one day (never overwrites a value with None)."""
    rows = load_prices()
    idx = {r["date"]: r for r in rows}
    rec = idx.get(date) or {"date": date, "quarter": None, "mesghal": None,
                            "usd": None, "spot": None}
    for k, v in (("quarter", quarter), ("mesghal", mesghal),
                 ("usd", usd), ("spot", spot)):
        if v is not None:
            rec[k] = v
    idx[date] = rec
    with PRICES_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PRICE_COLS)
        w.writeheader()
        for d in sorted(idx):
            w.writerow({c: (idx[d].get(c) if idx[d].get(c) is not None else "")
                        for c in PRICE_COLS})


def mesghal_series() -> list[float]:
    return [r["mesghal"] for r in load_prices() if r.get("mesghal")]


# ---------------- signals ----------------
def append_signal(date, ts, from_pos, to_pos, layer, rp, vol, reason) -> None:
    with SIGNALS_CSV.open("a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([date, ts, from_pos, to_pos, layer,
                                f"{rp:.6f}" if rp is not None else "",
                                f"{vol:.6f}" if vol is not None else "", reason])


def load_signals(limit: int = 20) -> list[dict]:
    if not SIGNALS_CSV.exists():
        return []
    with SIGNALS_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-limit:]


# ---------------- state ----------------
def load_state() -> dict:
    try:
        s = json.loads(STATE_JSON.read_text(encoding="utf-8"))
    except Exception:
        s = {}
    merged = DEFAULT_STATE.copy()
    merged.update(s or {})
    return merged


def save_state(state: dict) -> None:
    tmp = STATE_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_JSON)


def stats() -> dict:
    rows = load_prices()
    return {
        "prices": len(rows),
        "first": rows[0]["date"] if rows else None,
        "last": rows[-1]["date"] if rows else None,
        "signals": max(0, len(load_signals(10 ** 6))),
        "dir": str(DATA_DIR),
    }
