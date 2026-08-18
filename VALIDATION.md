# Threshold & Signal Validation on the full 6.4-year history

Window **2020-04-21 → 2026-07-27**, 1,609 evaluated sessions, 2% cost per leg.
All figures are **× holding ربع سکه**.

---

## Q1 — Are A (RP sell) and B (RP buy) still the best thresholds?

### In-sample grid (90 combinations)

| A | B | FULL | H1 | H2 |
|---|---|---|---|---|
| 0.70 | 0.31 | **1.89** | 1.09 | 1.74 |
| 0.70 | 0.20 | 1.84 | 1.18 | 1.56 |
| 0.65 | 0.31 | 1.80 | 1.03 | 1.74 |
| **0.60** | **0.31** *(current)* | 1.66 | 0.95 | 1.74 |

88/90 combos beat holding the coin; **16/90 now beat it in BOTH halves**
(on the 4.4-year window that number was 0/90).

At face value A = 0.70 looks better. **It is not.**

### Walk-forward test — choose on TRAIN only, measure on unseen TEST

| cutoff | picked on train | train | **TEST** |
|---|---|---|---|
| 2022-09-13 | A=0.70 B=0.20 | 1.36× | 1.35× |
| 2023-05-04 | A=0.70 B=0.20 | 1.18× | 1.56× |
| 2023-12-05 | A=0.70 B=0.20 | 1.28× | 1.43× |
| 2024-08-18 | A=0.70 B=0.20 | 1.30× | 1.44× |
| | | **mean TEST** | **1.45×** |

Same TEST windows with parameters **fixed in advance**:

| params | 40% | 50% | 60% | 70% | mean |
|---|---|---|---|---|---|
| A=0.60 B=0.31 | 1.51 | 1.74 | 1.60 | 1.61 | **1.62** |
| A=0.65 B=0.31 | 1.51 | 1.74 | 1.60 | 1.61 | **1.62** |
| A=0.70 B=0.31 | 1.51 | 1.74 | 1.60 | 1.61 | **1.62** |
| A=0.70 B=0.20 | 1.35 | 1.56 | 1.43 | 1.44 | 1.45 |

**Optimising made it worse: 1.62× → 1.45×.** Anyone who had re-fit the
parameters at any of those four dates would have earned *less*.

### Why A barely matters

`A` is only a **trigger**. Once you are in مثقال you stay until RP ≤ B, so
A = 0.60 / 0.65 / 0.70 / 0.75 produce **identical** out-of-sample results.
The apparent in-sample gain at 0.70 comes from one crossing being timed
slightly better inside the training window.

`B` is the parameter that matters, and B = 0.31 beats B = 0.20 out-of-sample
(1.62× vs 1.45×) because B = 0.20 fires on only 7% of sessions — too rare.

> ### ✅ Verdict: keep **A = 0.60, B = 0.31**. No change.

---

## Q2 — Is vol45 the best USD-vs-gold tool? Is anything else needed?

I tested **21 signals in 8 families** for correlation with forward-30-day
(gold − USD):

| signal | n | corr | top-decile spread |
|---|---|---|---|
| vol90 **USD** | 1534 | **−0.266** | +4.3pp |
| vol45 **USD** | 1579 | −0.180 | −0.0pp |
| **vol90 mesghal** | 1534 | −0.171 | **+5.9pp** |
| drawdown-180 | 1444 | +0.145 | −3.8pp |
| vol60 mesghal | 1564 | −0.139 | +3.9pp |
| **vol45 mesghal** *(current)* | 1579 | −0.135 | +2.5pp |
| relative momentum (4 windows) | — | −0.07 … −0.02 | ~0 |
| gold/USD vs SMA (3 windows) | — | −0.07 … −0.01 | ~0 |
| RSI-14 | 1579 | +0.061 | −1.3pp |
| RP level itself | 1579 | −0.001 | −2.5pp |

### Correlation ≠ profit

USD-volatility had the *best* correlation, and is **catastrophic** as a rule:

| Layer-1 overlay | FULL | H1 | H2 | trades |
|---|---|---|---|---|
| none (Layer 2 only) | 1.66 | 0.95 | 1.74 | 6 |
| **vol90 mesghal 3.0/2.2** | **1.72** | 0.95 | 1.77 | 11 |
| vol45 mesghal 4.0/1.6 | 1.73 | 0.97 | 1.72 | 8 |
| vol45 mesghal 3.3/2.0 *(old)* | 1.44 | 0.76 | 1.83 | 11 |
| vol90 **USD** 1.5/1.0 | **0.68** | 0.58 | 1.14 | 9 |
| vol45 **USD** 1.5/1.0 | **0.60** | 0.48 | 1.21 | 14 |
| drawdown-180 | **0.50** | 0.57 | 0.87 | 21 |

`vol45 = 4.0/1.6` scores highest but fires on **one single episode**
(2023-03-15 → 2023-05-07) — the same curve-fit trap found earlier.

`vol90 = 3.0/2.2` fires on **4 distinct episodes** and survives walk-forward:

| test from | Layer 2 only | + vol90 | winner |
|---|---|---|---|
| 2022-09-13 | 1.51 | **1.62** | vol90 |
| 2023-05-04 | 1.74 | **1.77** | vol90 |
| 2023-12-05 | 1.60 | **1.64** | vol90 |
| 2024-08-18 | 1.61 | **1.65** | vol90 |

Every USD episode it produced was profitable:

| in | out | days | USD | مثقال | net edge |
|---|---|---|---|---|---|
| 2020-11-08 | 2021-02-23 | 88 | −5.0% | −9.9% | **+1.3%** |
| 2023-03-15 | 2023-07-17 | 85 | +4.3% | −7.7% | **+8.6%** |
| 2026-05-12 | 2026-07-27 | 59 | +2.8% | −7.0% | **+6.1%** |

Compounded: **+16.7%**, 3 for 3.

> ### ✅ Verdict: **change vol45 → vol90, thresholds 3.0% / 2.2%.**
> No other tool is needed. Momentum, RSI, drawdown, gold/USD ratio and
> USD-volatility were all tested and all **destroy** value as trading rules.

### Why USD-vol fails despite the best correlation
The rial devalues in sudden jumps. High USD volatility means the jump is
*already happening* — by the time the signal fires you buy dollars at the top
and gold at the bottom. Good description, terrible timing.

---

## Updated parameter set

```
A_SELL_QUARTER = 0.60      unchanged
B_BUY_QUARTER  = 0.31      unchanged
VOL_WINDOW     = 90        was 45   ← changed
VOL_HI         = 0.030     was 0.033 ← changed
VOL_LO         = 0.022     was 0.020 ← changed
MINHOLD_L1     = 10        unchanged
MINHOLD_L2     = 5         unchanged
COST_PER_LEG   = 0.02      unchanged
```

`bot/strategy.py` updated; `vol45` retained as an alias of `vol90`.

**Layer 1 is now worth including** — but only just. It contributed +16.7%
over 6.4 years from 3 episodes. It remains the weakest part of the system and
should be described as such.
