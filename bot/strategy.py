"""
Two-layer strategy engine.

LAYER 1 (macro gate):  vol90 >= VOL_HI  -> USD ;  while USD, exit when vol90 <= VOL_LO
LAYER 2 (rel. value):  RP <= B -> ربع سکه ;  RP >= A -> مثقال   (only while in gold)

RP = (P_quarter / 1.8288) / (P_mesghal / 3.2489) - 1
vol90 = stdev of daily mesghal returns over trailing 90 sessions
"""
from __future__ import annotations
import statistics as st
from dataclasses import dataclass, asdict
from typing import Optional

# ---- fine-gold content (grams) --------------------------------------------
QUARTER_G = 2.032 * 0.900      # 1.8288  ربع سکه   (2.032 g @ 900)
MESGHAL_G = 4.6083 * 0.705     # 3.24885 مثقال آب‌شده (عیار ۷۰۵)
OZ_G = 31.1035

# ---- calibrated parameters (see FLOWCHART.md) ------------------------------
A_SELL_QUARTER = 0.60   # RP >= 60%  -> hold مثقال
B_BUY_QUARTER  = 0.31   # RP <= 31%  -> hold ربع سکه
VOL_HI         = 0.030  # vol90 >= 3.0% -> USD
VOL_LO         = 0.022  # vol90 <= 2.2% -> release back to gold
VOL_WINDOW     = 90     # 90 beat 45 out-of-sample on all 4 walk-forward splits
MINHOLD_L1     = 10     # sessions
MINHOLD_L2     = 5      # sessions
COST_PER_LEG   = 0.02   # 2% fee + slippage

GOLD = ("QUARTER", "MESGHAL")


def relative_premium(quarter: float, mesghal: float) -> float:
    """RP — quarter's premium over melted gold, per fine gram."""
    return (quarter / QUARTER_G) / (mesghal / MESGHAL_G) - 1.0


def vol90(mesghal_series: list[float], window: int = VOL_WINDOW) -> Optional[float]:
    """Stdev of daily mesghal returns over the trailing window (default 90)."""
    s = [x for x in mesghal_series if x and x > 0]
    if len(s) < 5:
        return None
    s = s[-(window + 1):]
    rets = [s[i] / s[i - 1] - 1.0 for i in range(1, len(s))]
    if len(rets) < 4:
        return None
    return st.pstdev(rets)


def intrinsic_bubbles(quarter, mesghal, usd, spot_usd_oz):
    """Absolute bubbles vs world spot. Returns (bubble_q, bubble_m) or (None, None)."""
    if not (usd and spot_usd_oz):
        return None, None
    g = (spot_usd_oz / OZ_G) * usd          # rial per fine gram
    if g <= 0:
        return None, None
    return (quarter / QUARTER_G) / g - 1.0, (mesghal / MESGHAL_G) / g - 1.0


@dataclass
class Decision:
    target: str            # QUARTER | MESGHAL | USD
    layer1: str            # USD | GOLD
    layer2_pref: str       # QUARTER | MESGHAL
    rp: float
    vol: Optional[float]
    reason: str
    action: bool           # True if target != current position
    blocked_by_gate: bool  # signal fired but min-hold blocked it

    def to_dict(self):
        return asdict(self)


def decide(rp: float,
           vol: Optional[float],
           current: str,
           prev_pref: str = "MESGHAL",
           bars_since_l1: int = 999,
           bars_since_l2: int = 999) -> Decision:
    """Core decision. `current` is the position actually held."""
    # ---- Layer 2 preference (always computed) ----
    if rp <= B_BUY_QUARTER:
        pref = "QUARTER"
    elif rp >= A_SELL_QUARTER:
        pref = "MESGHAL"
    else:
        pref = prev_pref if prev_pref in GOLD else "MESGHAL"

    # ---- Layer 1 gate ----
    if vol is None:
        l1 = "USD" if current == "USD" else "GOLD"
    elif current == "USD":
        l1 = "USD" if vol > VOL_LO else "GOLD"
    else:
        l1 = "USD" if vol >= VOL_HI else "GOLD"

    target = "USD" if l1 == "USD" else pref

    # ---- min-hold gates ----
    blocked = False
    if target != current:
        is_l1 = (target == "USD") or (current == "USD")
        if is_l1 and bars_since_l1 < MINHOLD_L1:
            blocked, target = True, current
        elif (not is_l1) and bars_since_l2 < MINHOLD_L2:
            blocked, target = True, current

    # ---- human-readable reason ----
    v = f"{vol*100:.2f}%" if vol is not None else "n/a"
    if l1 == "USD" and current != "USD":
        reason = f"vol45 {v} ≥ {VOL_HI*100:.1f}% → risk-off to USD"
    elif l1 == "USD":
        reason = f"vol45 {v} still > {VOL_LO*100:.1f}% → stay in USD"
    elif current == "USD" and l1 == "GOLD":
        reason = f"vol45 {v} ≤ {VOL_LO*100:.1f}% → back to gold, Layer 2 picks {pref}"
    elif rp <= B_BUY_QUARTER:
        reason = f"RP {rp*100:.1f}% ≤ {B_BUY_QUARTER*100:.0f}% → ربع سکه is cheap"
    elif rp >= A_SELL_QUARTER:
        reason = f"RP {rp*100:.1f}% ≥ {A_SELL_QUARTER*100:.0f}% → quarter bubble rich, hold مثقال"
    else:
        reason = (f"RP {rp*100:.1f}% inside [{B_BUY_QUARTER*100:.0f}%,"
                  f"{A_SELL_QUARTER*100:.0f}%] → no edge, hold")
    if blocked:
        reason += "  ⏳ min-hold gate active"

    return Decision(target=target, layer1=l1, layer2_pref=pref, rp=rp, vol=vol,
                    reason=reason, action=(target != current), blocked_by_gate=blocked)


def round_trip_gain(rp_buy: float, rp_sell: float, cost: float = COST_PER_LEG) -> float:
    """Gram gain of a full ربع→مثقال→ربع cycle: (1+p2)/(1+p1) x (1-c)^4."""
    return (1 + rp_sell) / (1 + rp_buy) * (1 - cost) ** 4


# backwards-compatible alias
vol45 = vol90

# ─────────────── basis z-score (world-parity gate) ───────────────
# FairValue = XAU/USD ÷ 31.1035 × USDIRR × grams  -> rial value of one mesghal
# implied by the world gold price and the dollar. Basis is how far the local
# mesghal trades from that. Positive = local gold expensive vs world parity.
Z_WINDOW    = 75     # rolling observations for mean/stdev
Z_ENTER_USD = 1.75   # basis z above this -> local premium stretched -> USD
Z_EXIT_USD  = 0.50   # basis z below this -> premium gone -> back to GOLD
Z_PERSIST   = 3      # consecutive observed closes required
Z_COOLDOWN  = 30     # observations since the last z-transition


def fair_value_mesghal(spot_usd_oz, usd_irr):
    """Rial value of one مثقال implied by world gold + USD. None if inputs missing."""
    if not spot_usd_oz or not usd_irr:
        return None
    return spot_usd_oz / OZ_G * usd_irr * MESGHAL_G


def basis(mesghal, spot_usd_oz, usd_irr):
    """Local premium/discount of مثقال vs world parity. Positive = expensive."""
    fv = fair_value_mesghal(spot_usd_oz, usd_irr)
    if not fv or not mesghal:
        return None
    return mesghal / fv - 1.0


def basis_z(basis_series, window: int = Z_WINDOW):
    """Rolling z-score of the latest basis. Needs `window` prior observations."""
    s = [b for b in basis_series if b is not None]
    if len(s) < window + 1:
        return None
    hist = s[-(window + 1):-1]          # prior window, excludes today
    mean = sum(hist) / len(hist)
    sd = st.pstdev(hist)
    if sd == 0:
        return None
    return (s[-1] - mean) / sd


def z_zone(z):
    """Human label for where the z-score sits."""
    if z is None:
        return "n/a"
    if z > Z_ENTER_USD:
        return "STRETCHED"
    if z < Z_EXIT_USD:
        return "NORMAL"
    return "ELEVATED"


def z_decide(z_series, state="GOLD", bars_since_z=999):
    """Apply the persistence + cooldown state machine.

    Returns (new_state, run_hi, run_lo, fired). `state` is the caller's
    previous z-gate state, NOT the portfolio position.
    """
    zs = [z for z in z_series if z is not None]
    if not zs:
        return state, 0, 0, False

    run_hi = 0
    for z in reversed(zs):
        if z > Z_ENTER_USD:
            run_hi += 1
        else:
            break
    run_lo = 0
    for z in reversed(zs):
        if z < Z_EXIT_USD:
            run_lo += 1
        else:
            break

    fired = False
    if state == "GOLD" and run_hi >= Z_PERSIST and bars_since_z >= Z_COOLDOWN:
        state, fired = "USD", True
    elif state == "USD" and run_lo >= Z_PERSIST and bars_since_z >= Z_COOLDOWN:
        state, fired = "GOLD", True
    return state, run_hi, run_lo, fired

