"""Tehran Stock Exchange: fund price + NAV, straight off TSETMC's JSON API.

Why not `pytse-client` (what the upstream desk used)? It pulls in pandas, and
the signalling bot this desk lives inside installs exactly one dependency
today. A hundred megabytes of build for three numbers would slow every deploy
and enlarge the container the bot has to keep resident. So the same three
numbers are fetched directly.

NAV is the point of this source: without it there is no premium/discount, and
premium/discount is what the handbook's wrapper gates are written against.
Every URL and every field path lives in config/sources.yaml, so when TSETMC
changes shape you fix it with `/probe tse` -> edit -> `/reload`, no redeploy.

Instrument codes are resolved by symbol search once and then cached in the
desk's own kv store, so the normal path is two requests per fund.
"""
from __future__ import annotations
import logging

from .http_source import dig, get_json, num, relay_wrap

log = logging.getLogger("desk.tse")


def _headers(spec: dict) -> dict:
    # TSETMC's CDN rejects requests without a browser-ish Referer.
    return {"Referer": spec.get("referer", "https://www.tsetmc.com/")}


def _fetch(url: str, spec: dict, via_relay: bool):
    """One TSETMC GET, optionally through the in-Iran relay."""
    headers = _headers(spec)
    if via_relay:
        url, extra = relay_wrap(url)
        headers.update(extra)
    return get_json(url, timeout=spec.get("timeout"), headers=headers)


def _resolve_code(key: str, sym: str, spec: dict, store, notes: list[str],
                  via_relay: bool = False):
    """Config-pinned code wins; otherwise search once and cache the result."""
    pinned = (spec.get("codes") or {}).get(key)
    if pinned:
        return str(pinned)
    cached = store.get(f"tse.code.{key}") if store else None
    if cached:
        return str(cached)

    url = spec.get("search_url", "").format(symbol=sym)
    if not url:
        return None
    data, _ = _fetch(url, spec, via_relay)
    items = dig(data, spec.get("search_path", "instrumentSearch")) or []
    code_key = spec.get("search_code_key", "insCode")
    sym_key = spec.get("search_symbol_key", "lVal18AFC")
    want = sym.strip()
    # Prefer an exact symbol match; TSETMC's search is fuzzy and returns
    # delisted look-alikes, which is how you end up quoting the wrong fund.
    for it in items:
        if isinstance(it, dict) and str(it.get(sym_key, "")).strip() == want:
            code = str(it.get(code_key) or "").strip()
            if code:
                if store:
                    store.set(f"tse.code.{key}", code)
                notes.append(f"resolved {sym} -> insCode {code}")
                return code
    return None


def _one(key: str, sym: str, spec: dict, store, raw_bits: list[str],
         notes: list[str], via_relay: bool = False) -> dict:
    out: dict[str, float] = {}
    code = _resolve_code(key, sym, spec, store, notes, via_relay)
    if not code:
        raw_bits.append(f"{key}({sym}) -> no insCode; pin one under `codes:` in sources.yaml")
        return out

    price_url = spec.get("price_url", "").format(code=code)
    if price_url:
        data, raw = _fetch(price_url, spec, via_relay)
        raw_bits.append(f"{key} price {raw[:600]}")
        p = num(dig(data, spec.get("price_path", "closingPriceInfo.pDrCotVal")))
        if p:
            out[f"{key}_price"] = p
        prev = num(dig(data, spec.get("prev_path", "closingPriceInfo.priceYesterday")))
        if prev:
            out[f"{key}_prev_close"] = prev

    nav_url = spec.get("nav_url", "").format(code=code)
    if nav_url:
        try:
            data, raw = _fetch(nav_url, spec, via_relay)
            raw_bits.append(f"{key} nav {raw[:600]}")
            n = num(dig(data, spec.get("nav_path", "etf.estimatedNAV")))
            if n:
                out[f"{key}_nav"] = n
        except Exception as e:                          # noqa: BLE001
            # A missing NAV must never cost us the price. The collector
            # carries the last NAV forward and /health says it did.
            raw_bits.append(f"{key} nav ERROR {type(e).__name__}: {e}")
    return out


def fetch_tse(spec: dict, store=None, via_relay: bool = False) -> tuple[dict, str]:
    out: dict[str, float] = {}
    raw_bits: list[str] = []
    notes: list[str] = []

    for key, sym in (spec.get("symbols") or {}).items():
        try:
            out.update(_one(key, sym, spec, store, raw_bits, notes, via_relay))
        except Exception as e:                          # noqa: BLE001
            raw_bits.append(f"{key}({sym}) ERROR {type(e).__name__}: {e}")
            log.warning("tse %s failed: %s", key, e)

    index_url = spec.get("index_url")
    if index_url:
        try:
            data, raw = _fetch(index_url, spec, via_relay)
            raw_bits.append(f"tedpix {raw[:400]}")
            v = num(dig(data, spec.get("index_path", "")))
            if v:
                out["tedpix"] = v
        except Exception as e:                          # noqa: BLE001
            raw_bits.append(f"tedpix ERROR {type(e).__name__}: {e}")

    if not out:
        # Distinguish "reached TSETMC, mapped nothing" from a transport
        # failure — the collector reports the two differently.
        raise RuntimeError(raw_bits[0] if raw_bits else "no fields mapped")
    return out, "\n".join(raw_bits)[:4000]
