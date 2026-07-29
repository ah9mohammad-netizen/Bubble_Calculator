# Deep Backtest — 750 sessions (2023-07-15 → 2026-07-27)

Roughly **double** the previous testable window (was 375 sessions from
2025-01-04). All three series rebuilt from **column 3 (close)** so gold and
USD are finally on the same price convention.

## Data

`data/master.csv` — 750 sessions where ربع سکه, مثقال and USD/IRR all exist.

| series | sessions | range |
|---|---|---|
| ربع سکه (`rob`) | 789 | 2023-07-15 → 2026-07-27 |
| مثقال (`mesghal`) | 795 | 2023-05-30 → 2026-07-27 |
| USD/IRR (`price_dollar_rl`) | 906 | 2023-05-27 → 2026-07-27 |
| **intersection** | **750** | **2023-07-15 → 2026-07-27** |

🔴 **Fixed a real bug.** `data/usd_irr.csv` had been built from column 0
(**open**) while every gold series used column 3 (**close**). Measured on 120
overlapping days: 0.73% mean divergence, 2.18% max. Everything below uses
close throughout.

Integrity check: only 2 daily moves >13% in any series, both in ربع
(2025-03-17 +17.2%, 2025-09-20 +14.3%). Both are corroborated by مثقال moving
the same direction on the same day — real market events, not sentinel
corruption.

## Results — 1 bn rial, starting held as ربع سکه, 2% per leg

704 evaluated sessions (46 burned for the vol45 warm-up).

| # | Approach | Final | Return | Trades |
|---|---|---|---|---|
| 1 | Hold USD | 3.624 bn | +262.4% | 0 |
| 2 | Hold ربع سکه | 5.433 bn | +443.3% | 0 |
| 3 | Hold مثقال | 7.522 bn | +652.2% | 0 |
| 4 | Q↔M switching | 8.523 bn | +752.3% | 4 |
| 5 | **Two-layer** | **9.258 bn** | **+825.8%** | **5** |

**In grams of fine gold** (the metric that matters), starting 18.40 g:

| Approach | End grams | × start |
|---|---|---|
| Hold USD | 14.93 g | **0.811×** ← *lost gold* |
| Hold ربع سکه | 22.37 g | 1.216× |
| Hold مثقال | 30.98 g | 1.684× |
| Q↔M switching | 35.10 g | 1.908× |
| **Two-layer** | **38.13 g** | **2.073×** |

The ordering is unchanged from the 375-session test, and the margins widened.

### The 5 trades

```
2023-09-20  QUARTER → MESGHAL  [L2]  RP=75.3%  vol=0.80%
2025-02-11  MESGHAL → QUARTER  [L2]  RP=29.8%  vol=1.58%
2025-03-17  QUARTER → MESGHAL  [L2]  RP=76.0%  vol=2.22%
2025-09-13  MESGHAL → QUARTER  [L2]  RP=28.9%  vol=1.59%
2026-02-02  QUARTER → USD      [L1]  vol=3.36%
```

The new window adds one trade at the very start (Sep 2023, RP 75.3%) — the
tail of the high-bubble regime the old window couldn't see.

## Robustness

**A/B grid — 36/36 cells beat holding ربع.** Range 1.25× to 1.70×, chosen
(A=0.60, B=0.31) sits at 1.70×, the joint maximum but on a **flat plateau**
(A=0.60/0.65/0.70/0.75 all identical at 1.70×) rather than a lone spike.

```
      B=  0.20   0.25   0.28   0.31   0.34   0.40
A=0.50   1.52x  1.41x  1.38x  1.46x  1.38x  1.25x
A=0.60   1.52x  1.41x  1.38x  1.70x  1.61x  1.46x
A=0.75   1.52x  1.41x  1.38x  1.70x  1.61x  1.46x
```

**Vol thresholds — all 15 combos beat holding ربع** (1.41×–1.76×). Chosen
3.3/2.0 gives 1.70×. Note 2.8/2.0 scores higher (1.76×) — see caveats.

**Split-sample — wins in both halves independently:**

| half | window | hold ربع | two-layer | ratio |
|---|---|---|---|---|
| H1 | 2023-09-20 → 2025-02-02 | 1.861 bn | 2.339 bn | **1.26×** |
| H2 | 2025-02-02 → 2026-07-27 | 2.919 bn | 3.991 bn | **1.37×** |

This is the first time the strategy has been validated on two independent
sub-periods. It was not possible with the old 375-session window.

## ⚠️ Layer 1 correction — the vol table is NOT monotonic

Previously I reported a "perfectly monotonic" vol45 table from 345
observations. With **674 observations** on corrected close prices, the low
end reverses. The true shape is a **hump**:

| vol45 bucket | n | fwd-30d gold−USD | gold wins |
|---|---|---|---|
| 0.5–1.0% | 62 | +1.6pp | 65% |
| 1.0–1.5% | 151 | +5.0pp | 75% |
| **1.5–2.0%** | 212 | **+6.6pp** | **90%** |
| 2.0–2.5% | 116 | +4.7pp | 81% |
| 2.5–3.0% | 57 | +2.6pp | 68% |
| 3.0–3.5% | 58 | −2.0pp | 36% |
| 3.5–4.0% | 18 | **−12.8pp** | **0%** |

correlation(vol45, fwd-30d gold−USD) = **−0.317**

**What survives:** the high-vol signal, which is what Layer 1 actually trades.
Above 3.0% gold reliably loses to USD; above 3.5% it lost in 18/18 cases.

**What does not:** *very* calm markets (<1.5%) are NOT the best time to hold
gold — the sweet spot is 1.5–2.0%. My earlier "calmer is always better"
description was an artefact of the shorter, convention-mismatched sample.
This does not change the rule (VOL_LO = 2.0% sits right at the peak) but it
does change the explanation.

## Still-standing caveats

1. **Only 5 trades.** Doubling the data added exactly one trade. The result
   rests on a handful of decisions.
2. **Layer 1 still fires on essentially one episode** (Feb 2026, plus a
   re-entry May 2026). The 3.5–4.0% bucket is 18 observations from a single
   war-driven window.
3. **2.8% threshold beats 3.3%** (1.76× vs 1.70×) but fires more often.
   I kept 3.3% because it is inside a flat region; this is a judgement call,
   not a result.
4. **Still not 2020.** The binding constraint is now ربع سکه, whose usable
   history in this collection starts 2023-07-15. Reaching 2020 needs ~25
   more paged fetches.
5. tgju's `rob` blends mint years ۱۳۸۶/۱۴۰۳/۱۴۰۴ that trade up to 1m toman
   apart; screen prices ≠ dealer fills.
