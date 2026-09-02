"""Telegram message rendering. Markdown-safe, tabular-ish.

Unchanged from the upstream desk except for the clock: `stamp()` now comes
from tehran.py, so neither pytz nor jdatetime is needed.
"""
from __future__ import annotations
from .tehran import stamp                      # noqa: F401  (re-exported)

_MD = str.maketrans({"_": r"\_", "*": r"\*", "[": r"\[", "`": r"\`"})


def esc(s: str) -> str:
    return str(s).translate(_MD)



def _n(v, fmt=",.0f", dash="—"):
    return format(v, fmt) if isinstance(v, (int, float)) else dash


def snapshot_block(v: dict) -> str:
    L = []
    L.append("*ENGINE 1 — the toman*")
    L.append(f"`USD free      {_n(v.get('usd_free')):>12}`")
    L.append(f"`USD havaleh   {_n(v.get('usd_havaleh')):>12}`   spread `{_n(v.get('fx_spread_pct'),'+.1f')}%`")
    L.append(f"`18k gold      {_n(v.get('gold18k_toman')):>12}` toman/g")
    L.append(f"`parity        {_n(v.get('gold_parity_toman')):>12}`   gap `{_n(v.get('gold_parity_gap_pct'),'+.2f')}%`")
    L.append(f"`g per 1B      {_n(v.get('grams_per_billion'),'.1f'):>12}`")
    L.append("")
    L.append("*ENGINE 2 — world spot*")
    L.append(f"`XAU  ${_n(v.get('xau_usd'),',.2f'):>10}`   `XAG  ${_n(v.get('xag_usd'),',.2f'):>8}`")
    L.append(f"`G/S ratio {_n(v.get('gold_silver_ratio'),'.1f'):>6}`   `Cu  ${_n(v.get('copper_usd_lb'),'.3f'):>8}`/lb")
    L.append(f"`BTC  ${_n(v.get('btc_usd')):>10}`")
    L.append("")
    L.append("*WRAPPERS*")
    L.append(f"`طلا    {_n(v.get('tala_price')):>10}`  bubble `{_n(v.get('tala_bubble_pct'),'+.2f')}%`")
    L.append(f"`پلاتا  {_n(v.get('plata_price')):>10}`  prem   `{_n(v.get('plata_premium_pct'),'+.2f')}%`")
    L.append(f"`اهرم   {_n(v.get('ahrom_price')):>10}`  disc   `{_n(v.get('ahrom_discount_pct'),'+.2f')}%`")
    L.append(f"`TEDPIX {_n(v.get('tedpix')):>10}`")
    L.append("")
    L.append("*MACRO*")
    L.append(f"`CPI y/y {_n(v.get('iran_cpi_yoy'),'.1f'):>6}%`   `oil {_n(v.get('iran_oil_exports_bpd')):>9}` bpd")
    if v.get("any_fund_at_limit"):
        L.append(f"\n⚠️ *LIMIT DAY* — {esc(v.get('limit_fund_names',''))}")
    return "\n".join(L)


def gates_block(v: dict) -> str:
    def gate(ok: bool | None, yes: str, no: str) -> str:
        if ok is None:
            return "· unknown"
        return ("🟢 " + yes) if ok else ("🔴 " + no)

    tb = v.get("tala_bubble_pct")
    pp = v.get("plata_premium_pct")
    xag = v.get("xag_usd")
    L = ["*HANDBOOK GATES*"]
    L.append("gold wrapper  " + gate(None if tb is None else tb <= 3.0,
                                     f"open ({tb:+.2f}%)" if tb is not None else "",
                                     f"shut ({tb:+.2f}%>3%)" if tb is not None else ""))
    L.append("silver wrap   " + gate(None if pp is None else pp <= 6.0,
                                     f"open ({pp:+.2f}%)" if pp is not None else "",
                                     f"shut ({pp:+.2f}%>6%)" if pp is not None else ""))
    both = None if (pp is None or xag is None) else (pp < 5.0 and 58 <= xag <= 60)
    L.append("silver entry  " + gate(both, "BOTH conditions met", "waiting"))
    return "\n".join(L)


def ladder_block(v: dict) -> str:
    g = v.get("gold18k_toman")
    rungs = [(22_200_000, "30%"), (20_800_000, "25%"), (19_500_000, "25%"), (18_000_000, "20%")]
    L = ["*LADDER* — trigger on the toman gold price, never on the dollar"]
    for i, (lvl, share) in enumerate(rungs, 1):
        if not isinstance(g, (int, float)):
            mark, note = "·", ""
        elif g <= lvl:
            mark, note = "🟢", "LIVE"
        else:
            mark, note = "○", f"{(g/lvl-1)*100:+.1f}% away"
        L.append(f"{mark} `{i}  {lvl/1e6:>4.1f}M  {share:>4}`  {note}   `{1e9/lvl:>5.1f} g/B`")
    if isinstance(g, (int, float)):
        L.append(f"\nnow `{g/1e6:.2f}M` → `{1e9/g:.1f} g` per billion toman")
    return "\n".join(L)
