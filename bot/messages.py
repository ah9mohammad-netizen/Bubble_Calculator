"""Telegram message builders (HTML parse mode).

Layout rules learned the hard way:
  * Persian is RTL. Putting Persian in the MIDDLE of a line that also has
    digits makes Telegram reorder the line and the numbers jump around.
    => Persian only ever appears at the END of a line, or alone on a line.
  * Alignment only survives inside <pre>. Everything columnar goes in <pre>,
    and <pre> content is ASCII-only so nothing shifts.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import strategy as S

FA = {"QUARTER": "ربع سکه", "MESGHAL": "مثقال آب‌شده", "USD": "دلار"}
EN = {"QUARTER": "QUARTER COIN", "MESGHAL": "MESGHAL", "USD": "USD"}
EMO = {"QUARTER": "🪙", "MESGHAL": "🥇", "USD": "💵"}


# ───────────────────────── formatting helpers ─────────────────────────
def rial(v) -> str:
    return "—" if v is None else f"{v:,.0f}"


def toman(v) -> str:
    """Iranians quote toman = rial / 10."""
    return "—" if v is None else f"{v/10:,.0f}"


def tehran_now() -> str:
    t = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
    return t.strftime("%Y-%m-%d %H:%M")


def _gauge(val, lo, hi, t1, t2, w=26, fmt=lambda v: f"{v:g}"):
    """Return (bar, ticks) — two strings of identical width, so they line up
    under each other inside <pre>. t1/t2 are the two thresholds."""
    if val is None:
        return "—", ""
    span = hi - lo

    def pos(x):
        return max(0, min(w - 1, int(round((x - lo) / span * (w - 1)))))

    bar = ["·"] * w
    bar[pos(t1)] = "|"
    bar[pos(t2)] = "|"
    bar[pos(val)] = "◆"

    ticks = [" "] * w
    for value in (t1, t2):
        s = fmt(value)
        start = max(0, min(w - len(s), pos(value) - len(s) // 2))
        for k, ch in enumerate(s):
            ticks[start + k] = ch
    return "".join(bar), "".join(ticks)


def _zone_z(z):
    if z is None:
        return "n/a"
    if z > S.Z_ENTER_USD:
        return "STRETCHED"
    if z < S.Z_EXIT_USD:
        return "NORMAL"
    return "ELEVATED"


def _zone_rp(rp):
    if rp <= S.B_BUY_QUARTER:
        return "BUY QUARTER", "QUARTER"
    if rp >= S.A_SELL_QUARTER:
        return "BUY MESGHAL", "MESGHAL"
    return "HOLD (no edge)", None


def _zone_vol(v):
    if v is None:
        return "n/a", None
    if v >= S.VOL_HI:
        return "RISK-OFF → USD", "USD"
    if v <= S.VOL_LO:
        return "CALM → GOLD", "GOLD"
    return "NEUTRAL", None


# ───────────────────────── daily report ─────────────────────────
def daily_report(snap, dec, state, bq=None, bm=None, dec_extra=None) -> str:
    """Deliberately minimal: prices, the two signals with their ranges,
    and one decision. Nothing else."""
    rp, vol = dec.rp, dec.vol
    sp = snap.get("spot")

    rp_zone, _ = _zone_rp(rp)
    v_zone, _ = _zone_vol(vol)
    rp_bar, rp_tick = _gauge(rp * 100, 0, 90, S.B_BUY_QUARTER * 100, S.A_SELL_QUARTER * 100)
    v_bar, v_tick = _gauge(None if vol is None else vol * 100, 0.5, 4.5,
                           S.VOL_LO * 100, S.VOL_HI * 100,
                           fmt=lambda v: f"{v:.1f}")

    body = []
    body.append("  PRICES                 toman")
    body.append("  " + "-" * 29)
    body.append(f"  USD           {toman(snap.get('usd')):>15}")
    body.append(f"  Mesghal       {toman(snap.get('mesghal')):>15}")
    body.append(f"  Quarter coin  {toman(snap.get('quarter')):>15}")
    body.append(f"  Gold spot     {('%s $/oz' % f'{sp:,.2f}') if sp else '—':>15}")
    if snap.get("stale_quarter"):
        body.append(f"  coin quote is from {snap.get('quarter_lag_from')}")
    body.append("")
    body.append(f"  RP     {rp*100:5.1f}%      {rp_zone}")
    body.append(f"  {rp_bar}")
    body.append(f"  {rp_tick}")
    body.append("  cheap coin      rich bubble")
    body.append("")
    vtxt = f"{vol*100:5.2f}%" if vol is not None else "  n/a"
    body.append(f"  vol90  {vtxt}      {v_zone}")
    if vol is not None:
        body.append(f"  {v_bar}")
        body.append(f"  {v_tick}")
        body.append("  calm=gold        wild=USD")

    # ---- world-parity basis z-score ----
    ex = dec_extra or {}
    z = ex.get("z")
    bas = ex.get("basis")
    zgate = ex.get("z_state", "GOLD")
    body.append("")
    if bas is None:
        # No spot or no USD today -> can't even compute the basis.
        body.append("  basis   n/a      no spot/USD quote")
    else:
        body.append(f"  basis {bas*100:+5.1f}%      vs world parity")

    if z is not None:
        z_bar, z_tick = _gauge(z, -1.0, 3.0, S.Z_EXIT_USD, S.Z_ENTER_USD,
                               fmt=lambda v: f"{v:.2f}")
        body.append(f"  z     {z:+5.2f}      {_zone_z(z)}")
        body.append(f"  {z_bar}")
        body.append(f"  {z_tick}")
        body.append("  cheap vs world   rich vs world")
        body.append(f"  gate: {zgate}")
    else:
        # Say WHY instead of silently dropping the section.
        have = ex.get("basis_obs")
        need = S.Z_WINDOW + 1
        if have is None:
            body.append("  z       n/a      warming up")
        else:
            body.append(f"  z       n/a      warming up {have}/{need}")
        body.append("  needs 76 days of spot+USD+mesghal")

    L = []
    L.append("📊 <b>IRAN GOLD MONITOR</b>")
    L.append(f"<i>{tehran_now()} Tehran</i>")
    L.append(f"<pre>{chr(10).join(body)}</pre>")
    L.append(f"<b>TODAY →</b> {EMO[dec.target]} <b>{EN[dec.target]}</b>")
    L.append(f"<b>امروز →</b> {FA[dec.target]}")
    return "\n".join(L)


# ───────────────────────── trade signal ─────────────────────────
def signal_alert(from_pos, to_pos, dec, snap) -> str:
    layer = "LAYER 1" if "USD" in (from_pos, to_pos) else "LAYER 2"
    body = []
    body.append(f"  SELL   {EN[from_pos]}")
    body.append(f"  BUY    {EN[to_pos]}")
    body.append("")
    body.append(f"  RP     {dec.rp*100:5.1f}%")
    if dec.vol is not None:
        body.append(f"  vol90  {dec.vol*100:5.2f}%")
    body.append("")
    body.append("  prices now             toman")
    body.append(f"  USD           {toman(snap.get('usd')):>15}")
    body.append(f"  Mesghal       {toman(snap.get('mesghal')):>15}")
    body.append(f"  Quarter coin  {toman(snap.get('quarter')):>15}")

    L = []
    L.append("🚨 <b>TRADE SIGNAL</b>")
    L.append(f"<i>{tehran_now()} Tehran · {layer}</i>")
    L.append(f"<pre>{chr(10).join(body)}</pre>")
    L.append(f"<b>SELL</b> {EMO[from_pos]} {FA[from_pos]}")
    L.append(f"<b>BUY</b> {EMO[to_pos]} {FA[to_pos]}")
    L.append("")

    if to_pos == "QUARTER":
        gain = S.round_trip_gain(dec.rp, S.A_SELL_QUARTER)
        L.append(f"🎯 Exit when RP ≥ {S.A_SELL_QUARTER*100:.0f}% "
                 f"→ ≈ <b>{(gain-1)*100:+.1f}%</b> more gold after costs")
    elif from_pos == "QUARTER" and to_pos == "MESGHAL":
        L.append(f"🎯 Bubble harvested. Re-enter when RP ≤ {S.B_BUY_QUARTER*100:.0f}%")
    elif to_pos == "USD":
        L.append(f"🛡 Risk-off. Back to gold when vol90 ≤ {S.VOL_LO*100:.1f}%")
    L.append("")
    L.append("⚠️ <i>Check the mint year and the dealer spread before trading.</i>")
    return "\n".join(L)


# ───────────────────────── help ─────────────────────────
HELP = f"""📖 <b>Iran Gold Arbitrage Bot</b>

Profit is counted in <b>grams of gold</b>, not rials.

<b>LAYER 2 — which gold?</b>
<code>RP = (P_quarter/1.8288) / (P_mesghal/3.2489) − 1</code>
The quarter coin's premium per gram of fine gold.
• RP ≤ <b>{S.B_BUY_QUARTER*100:.0f}%</b> → buy the quarter coin
• RP ≥ <b>{S.A_SELL_QUARTER*100:.0f}%</b> → switch to mesghal
• between → hold, no edge

<b>BASIS Z — is local gold rich vs the world?</b>
<code>FairValue = XAU/USD ÷ 31.1035 × USDIRR × 3.2489</code>
<code>Basis     = Mesghal / FairValue − 1</code>
The z-score is Basis standardised over a rolling <b>75</b> observations.
• z &gt; <b>+1.75</b> for <b>3</b> closes → local premium stretched → USD
• z &lt; <b>+0.50</b> for <b>3</b> closes → premium gone → back to gold
• between → no new trade, keep the prior state
Cooldown of <b>30</b> observations between switches. Default state is GOLD.

<b>LAYER 1 — gold or dollars?</b>
<code>vol90</code> = 90-day volatility of mesghal returns.
• vol90 ≥ <b>{S.VOL_HI*100:.1f}%</b> → risk-off to USD
• vol90 ≤ <b>{S.VOL_LO*100:.1f}%</b> → back to gold

<b>━━ BACKTEST ━━</b>
1,000,000 toman · 2020-04-21 → 2026-07-27 · 6.4 years · 2% per leg
<pre>plan            final toman  index  trades
Hold USD         11,200,773   1120     0
Hold mesghal     27,267,852   2727     0
Hold quarter     28,299,465   2830     0
Layer 2 only     46,971,072   4697     6
Two-layer        48,758,579   4876    11
Inflation (CPI)  11,567,489   1157     -</pre>
Holding dollars returned +1020% and still <b>lost</b> to inflation.

<b>━━ COMMANDS ━━</b>
/status — prices, both signals, today's decision
/price — prices only
/signal — what the model says now
/position — what the bot thinks you hold
/setpos quarter|mesghal|usd — sync it to reality
/history — last 10 signals
/backfill — repair price history
/repair — restore spot history (fixes a missing z)
/stats — storage info
/help — this message

<b>━━ METALS DESK ━━</b>
Optional add-on, off unless <code>ENABLE_DESK=1</code>. Watches the other
engine — import parity, the fund wrappers, world spot — against 33 rules.
/now — full desk snapshot   /parity — parity, step by step
/gates — handbook entry gates   /ladder — ladder rungs
/funds — طلا · پلاتا · اهرم premium vs NAV
/rules — every rule vs its threshold   /fires — recent desk signals
/health — data-source status   /desk — the desk's own help

<b>━━ REALITY CHECKS ━━</b>
• 6 trades in 6.4 years. It is a patient strategy.
• Layer 1 fired 3 times only. It is the weakest part.
• tgju's quarter index blends mint years ۱۳۸۶/۱۴۰۳/۱۴۰۴ that trade up to
  1m toman apart. Confirm which coin you are quoted.
• Screen prices are not dealer fills. Budget 2% per leg.
"""
