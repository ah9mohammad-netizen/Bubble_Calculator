"""Telegram message builders (HTML parse mode)."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import strategy as S

FA = {"QUARTER": "ربع سکه", "MESGHAL": "مثقال آب‌شده", "USD": "دلار"}
EN = {"QUARTER": "Quarter Coin", "MESGHAL": "Melted Gold", "USD": "USD"}
EMO = {"QUARTER": "🪙", "MESGHAL": "🥇", "USD": "💵"}


def rial(v) -> str:
    if v is None:
        return "—"
    return f"{v:,.0f}"


def toman(v) -> str:
    if v is None:
        return "—"
    return f"{v/10:,.0f}"


def tehran_now() -> str:
    t = datetime.now(timezone.utc) + timedelta(hours=3, minutes=30)
    return t.strftime("%Y-%m-%d %H:%M")


def _bar(x, lo, hi, n=20) -> str:
    if x is None:
        return "—"
    pos = max(0, min(n - 1, int((x - lo) / (hi - lo) * n)))
    return "─" * pos + "◆" + "─" * (n - 1 - pos)


def daily_report(snap, dec, state, bq=None, bm=None) -> str:
    pos = state.get("position", "MESGHAL")
    rp, vol = dec.rp, dec.vol
    L = []
    L.append("📊 <b>Iran Gold / FX Monitor</b>")
    L.append(f"<i>{tehran_now()} Tehran</i>")
    L.append("")
    L.append("<b>━━ PRICES ━━</b>")
    L.append(f"💵 USD        <code>{rial(snap.get('usd'))}</code> rial")
    L.append(f"🥇 مثقال      <code>{rial(snap.get('mesghal'))}</code> rial")
    L.append(f"🪙 ربع سکه    <code>{rial(snap.get('quarter'))}</code> rial")
    sp = snap.get("spot")
    L.append(f"🌍 Gold spot  <code>{sp:,.2f}</code> $/oz" if sp else "🌍 Gold spot  —")
    L.append("")

    L.append("<b>━━ LAYER 1 · USD vs GOLD ━━</b>")
    vtxt = f"{vol*100:.2f}%" if vol is not None else "n/a"
    L.append(f"vol90 = <b>{vtxt}</b>   (USD ≥ {S.VOL_HI*100:.1f}% · gold ≤ {S.VOL_LO*100:.1f}%)")
    if vol is not None:
        L.append(f"<code>{_bar(vol*100, 1.0, 4.5)}</code>")
        L.append("<code>1.0%            4.5%</code>")
    pref1 = "💵 USD" if dec.layer1 == "USD" else "🥇 GOLD"
    L.append(f"→ prefers <b>{pref1}</b>")
    L.append("")

    L.append("<b>━━ LAYER 2 · ربع vs مثقال ━━</b>")
    L.append(f"RP = <b>{rp*100:.1f}%</b>   (buy ربع ≤ {S.B_BUY_QUARTER*100:.0f}% · "
             f"sell ≥ {S.A_SELL_QUARTER*100:.0f}%)")
    L.append(f"<code>{_bar(rp*100, 10, 80)}</code>")
    L.append("<code>10%              80%</code>")
    L.append(f"→ prefers <b>{EMO[dec.layer2_pref]} {FA[dec.layer2_pref]}</b>")
    if bq is not None and bm is not None:
        L.append(f"<i>abs. bubble — ربع {bq*100:+.1f}% · مثقال {bm*100:+.1f}%</i>")
    L.append("")

    L.append("<b>━━ POSITION ━━</b>")
    L.append(f"Holding: <b>{EMO[pos]} {FA[pos]}</b>")
    if state.get("since"):
        L.append(f"<i>since {state['since']}</i>")
    L.append("")
    if dec.action:
        L.append("🚨 <b>ACTION REQUIRED — see signal</b>")
    elif dec.blocked_by_gate:
        L.append("⏳ Signal fired but min-hold gate is active")
    else:
        L.append("✅ <b>NO ACTION</b> — hold current position")
    L.append(f"<i>{dec.reason}</i>")
    return "\n".join(L)


def signal_alert(from_pos, to_pos, dec, snap) -> str:
    layer = "LAYER 1 (USD ↔ GOLD)" if "USD" in (from_pos, to_pos) else "LAYER 2 (ربع ↔ مثقال)"
    L = []
    L.append("🚨🚨 <b>TRADE SIGNAL</b> 🚨🚨")
    L.append(f"<i>{tehran_now()} Tehran · {layer}</i>")
    L.append("")
    L.append(f"<b>SELL</b>  {EMO[from_pos]} {FA[from_pos]}")
    L.append(f"<b>BUY</b>   {EMO[to_pos]} {FA[to_pos]}")
    L.append("")
    L.append(f"RP    <b>{dec.rp*100:.1f}%</b>")
    if dec.vol is not None:
        L.append(f"vol90 <b>{dec.vol*100:.2f}%</b>")
    L.append("")
    L.append(f"<b>Why:</b> {dec.reason}")
    L.append("")
    L.append("<b>Prices now</b>")
    L.append(f"💵 {rial(snap.get('usd'))}  🥇 {rial(snap.get('mesghal'))}  "
             f"🪙 {rial(snap.get('quarter'))}")
    L.append("")
    if to_pos == "QUARTER":
        tgt = S.A_SELL_QUARTER
        gain = S.round_trip_gain(dec.rp, tgt)
        L.append(f"🎯 Exit target RP ≥ {tgt*100:.0f}% → ≈ <b>{(gain-1)*100:+.1f}%</b> "
                 f"in gold after costs")
    elif from_pos == "QUARTER" and to_pos == "MESGHAL":
        L.append("🎯 Bubble harvested — wait for RP ≤ "
                 f"{S.B_BUY_QUARTER*100:.0f}% to re-enter ربع")
    elif to_pos == "USD":
        L.append(f"🛡 Risk-off. Return to gold when vol90 ≤ {S.VOL_LO*100:.1f}%")
    L.append("")
    L.append("⚠️ <i>Confirm mint year (۱۳۸۶/۱۴۰۳/۱۴۰۴) and dealer spread before trading.</i>")
    return "\n".join(L)


HELP = f"""📖 <b>Iran Gold Arbitrage Bot</b>

<b>━━ THE IDEA ━━</b>
Profit is measured in <b>grams of gold</b>, not rials. Two independent layers
decide where 100% of the book sits.

<b>LAYER 1 — USD or GOLD?</b>
Signal: <code>vol90</code> = 45-day volatility of مثقال returns.
• vol90 ≥ <b>{S.VOL_HI*100:.1f}%</b> → risk-off to <b>USD</b>
• while in USD, return to gold when vol90 ≤ <b>{S.VOL_LO*100:.1f}%</b>
Evidence: bucketing 299 observations, when vol90 was 1.5–2.0% gold beat USD over
the next 30 days <b>94%</b> of the time; at 3.5–4.0% it beat USD <b>0%</b> of
the time. Monotonic across all buckets.

<b>LAYER 2 — ربع سکه or مثقال?</b>
Signal: <code>RP</code> = quarter's premium over melted gold per fine gram.
<code>RP = (P_ربع/1.8288) / (P_مثقال/3.2489) − 1</code>
• RP ≤ <b>{S.B_BUY_QUARTER*100:.0f}%</b> → buy <b>ربع سکه</b> (bubble cheap)
• RP ≥ <b>{S.A_SELL_QUARTER*100:.0f}%</b> → switch to <b>مثقال</b> (bubble rich)
• in between → hold, no edge
RP has ranged <b>13% – 76%</b>. Each full cycle compounds
<code>(1+A)/(1+B)×(1−2%)⁴ ≈ 1.13×</code> more gold.

<b>━━ BACKTEST (1 bn rial, 2% per leg) ━━</b>
2025-01-04 → 2026-07-27, 375 sessions:
<code>hold USD       2.331 bn   +133%   0 trades
hold ربع سکه   3.103 bn   +210%   0 trades
hold مثقال     3.556 bn   +256%   0 trades
ربع↔مثقال      4.029 bn   +303%   3 trades
TWO-LAYER      4.376 bn   +338%   4 trades ★</code>

Longer gold-only window (2024-08 → 2026-07, 495 sessions):
<code>hold ربع       3.484 bn   +248%
hold مثقال     5.058 bn   +406%
ربع↔مثقال      5.731 bn   +473%  = 1.65× holding ربع</code>

<b>━━ COMMANDS ━━</b>
/status  — full dashboard: prices, both layers, position
/price   — prices only (quick)
/signal  — what the model says right now
/position — current holding + how long
/history — last 10 signals
/setpos &lt;quarter|mesghal|usd&gt; — sync bot to your real holding
/backfill — repair price history from tgju
/stats   — stored rows, volume path
/help    — this message

<b>━━ REALITY CHECKS ━━</b>
• Only <b>4 trades</b> in the tested window. Small sample.
• Layer 1 rests on 2 episodes, both in the 2026 war period.
• tgju's <code>rob</code> blends mint years ۱۳۸۶/۱۴۰۳/۱۴۰۴ which trade up to
  1m toman apart — <b>confirm which coin you are quoted</b>.
• Screen prices ≠ dealer fills. Budget 2%/leg.
• Trade reduced size until you've seen one full cycle live.
"""
