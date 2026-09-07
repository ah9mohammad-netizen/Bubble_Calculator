"""Derived metrics. This is where the handbook's arithmetic lives.

Everything a rule can reference must be produced here.
"""
from __future__ import annotations
import logging

log = logging.getLogger(__name__)

TROY_OZ_G = 31.1035
K18 = 0.750           # 18 karat purity
TOZ_PER_LB = 14.5833333     # troy ounces in one pound
# مثقال آب‌شده: 4.6083 g at عیار ۷۰۵ = 3.2489 g of fine gold. Same constant the
# strategy engine uses (strategy.MESGHAL_G) — the two must not drift apart.
MESGHAL_FINE_G = 4.6083 * 0.705


def _pct(a: float, b: float) -> float:
    return (a / b - 1.0) * 100.0


def derive(v: dict) -> dict:
    """Mutates and returns the value dict with derived metrics added."""
    out = dict(v)

    # --- copper: metals.dev quotes per troy oz; the handbook works in $/lb ---
    # 1 lb = 453.59237 g = 14.58333 troy oz  ->  $/lb = $/toz * 14.58333
    if out.get("copper_usd_lb") is None and out.get("copper_usd_toz") is not None:
        out["copper_usd_lb"] = out["copper_usd_toz"] * TOZ_PER_LB

    # --- 18k per gram, derived from مثقال when no direct 18k feed answers ---
    # Engine 1 is built on the 18k gram price: parity, the gap, grams per
    # billion and every ladder rung reference it. brsapi served it directly;
    # when it is unreachable the melted-gold quote carries the same
    # information, because مثقال is just 3.2489 g of the same fine gold.
    #   toman/g 24k = mesghal / 3.2489   ->   18k = x 0.750
    if out.get("gold18k_toman") is None and out.get("mesghal_toman"):
        out["gold18k_toman"] = out["mesghal_toman"] / MESGHAL_FINE_G * K18
        out["gold18k_is_derived"] = 1.0

    # --- import parity for 18k gold, in toman per gram ---
    if out.get("xau_usd") and out.get("usd_free"):
        parity = out["xau_usd"] / TROY_OZ_G * K18 * out["usd_free"]
        out["gold_parity_toman"] = parity
        if out.get("gold18k_toman"):
            out["gold_parity_gap_pct"] = _pct(out["gold18k_toman"], parity)

    # --- the two-dollar spread ---
    if out.get("usd_free") and out.get("usd_havaleh"):
        out["fx_spread_pct"] = _pct(out["usd_free"], out["usd_havaleh"])

    # --- how much metal a billion toman buys (the real unit of account) ---
    if out.get("gold18k_toman"):
        out["grams_per_billion"] = 1e9 / out["gold18k_toman"]

    # --- gold / silver ratio ---
    if out.get("xau_usd") and out.get("xag_usd"):
        out["gold_silver_ratio"] = out["xau_usd"] / out["xag_usd"]

    # --- fund premium / discount vs NAV ---
    for key, label in (("tala", "tala"), ("plata", "plata"), ("ahrom", "ahrom")):
        p, n = out.get(f"{key}_price"), out.get(f"{key}_nav")
        if p and n:
            gap = _pct(p, n)
            if key == "ahrom":
                out["ahrom_discount_pct"] = gap        # negative = discount
            elif key == "plata":
                out["plata_premium_pct"] = gap
            else:
                out["tala_bubble_pct"] = gap

    # --- limit-day detection (Iranian commodity funds cap at +/-10%) ---
    at_limit: list[str] = []
    for key, fa in (("tala", "طلا"), ("plata", "پلاتا"), ("ahrom", "اهرم")):
        p, prev = out.get(f"{key}_price"), out.get(f"{key}_prev_close")
        if p and prev:
            move = _pct(p, prev)
            out[f"{key}_day_pct"] = move
            if abs(move) >= 9.5:
                at_limit.append(f"{fa} {move:+.1f}%")
    out["any_fund_at_limit"] = len(at_limit)
    out["limit_fund_names"] = ", ".join(at_limit) if at_limit else "-"

    # --- ladder state ---
    rungs = [(22_200_000, 0.30), (20_800_000, 0.25), (19_500_000, 0.25), (18_000_000, 0.20)]
    g = out.get("gold18k_toman")
    if g:
        live = [i + 1 for i, (lvl, _) in enumerate(rungs) if g <= lvl]
        out["ladder_rungs_live"] = len(live)
        out["ladder_next_level"] = next((lvl for lvl, _ in rungs if g > lvl), rungs[-1][0])

    return out


def sanity_warnings(v: dict) -> list[str]:
    """Catches unit errors, which are the most likely failure with Iranian feeds."""
    w: list[str] = []
    usd = v.get("usd_free")
    if usd and not (50_000 <= usd <= 2_000_000):
        w.append(f"usd_free={usd:,.0f} outside plausible toman range - check `scale` in sources.yaml")
    g, par = v.get("gold18k_toman"), v.get("gold_parity_toman")
    # A rial/toman mix-up is exactly a factor of 10. Detect it against parity,
    # which is self-calibrating, rather than a hardcoded band that goes stale.
    if g and par:
        ratio = g / par
        if 9.0 <= ratio <= 11.0:
            w.append(f"gold18k_toman={g:,.0f} is ~10x parity - feed is in RIAL. "
                     f"Set scale: 0.1 for gold18k_toman in sources.yaml")
        elif 0.09 <= ratio <= 0.11:
            w.append(f"gold18k_toman={g:,.0f} is ~1/10 of parity - scale error, "
                     f"set scale: 10 in sources.yaml")
    if g and not (100_000 <= g <= 5_000_000_000):
        w.append(f"gold18k_toman={g:,.0f} implausible on any scale")
    gap = v.get("gold_parity_gap_pct")
    if gap is not None and 35 < abs(gap) < 800:
        w.append(f"parity gap {gap:+.1f}% is extreme - verify the dollar feed before trading it")
    xau = v.get("xau_usd")
    if xau and not (500 <= xau <= 20_000):
        w.append(f"xau_usd={xau} implausible")
    # Parity pairs a gold quote against a dollar quote. If they are from
    # different sessions the gap is an artefact of the calendar, not an edge —
    # this bot has already been burned once by pairing mismatched dates.
    spread = v.get("tgju_quote_spread_days")
    if spread:
        w.append(f"tgju quotes span {spread:.0f} days — the parity gap pairs "
                 f"prints from different sessions, treat it as indicative")
    if v.get("gold18k_is_derived"):
        w.append("gold18k_toman derived from مثقال (no direct 18k feed) — "
                 "it carries the melted-gold spread, not a dealer 18k print")
    return w
