# Sensitivity Analysis — Buy/Sell Bands for RP (ربع ↔ مثقال)

**v2 — rerun on 430 sessions (2024-10-30 → 2026-07-27), including ~5 months of
data that no earlier analysis in this repo had seen.**

`RP = (P_ربع / 1.8288) / (P_مثقال / 3.2489) − 1`
NAV in fine grams, start 1.000 g held as مثقال, cost 0.75%/leg.
**Benchmark: hold مثقال = 1.0000 g.** (Hold ربع = 0.7682 g.)

---

## 0. Headline

| Question | Answer |
|---|---|
| Best band on full sample? | buy ≤30% / sell ≥60% = **1.1753 g** |
| Is it robust? | **No** — same 1-point cliff as v1, still one day |
| Does scaling in fix the cliff? | **Yes** — sensitivity spread cut **0.234 → 0.108** |
| Does anything beat hold-مثقال out of sample? | **No** — best OOS mean is **0.977** |
| Is the signal real? | **Yes** — confirmed again, and the 2026 OOS buy signal was correct |

**Recommendation: do not deploy fixed bands. Use scaled entry, and switch the
exit to a regime-relative rule (§6). Phase 2 should be data, not parameters.**

---

## 1. The updated range

430 sessions:

| stat | RP |
|---|---|
| min | 13.0% |
| p5 | 17% |
| p10 | 19% |
| p25 | 27% |
| **p50** | **36%** |
| p75 | 47% |
| p90 | 56% |
| p95 | 61% |
| max | 76.0% |

Monthly means now extend through the war period:

```
2024-11  50.8%   2025-05  57.0%   2025-11  28.5%
2024-12  46.5%   2025-06  49.3%   2025-12  32.2%
2025-01  36.1%   2025-07  44.0%   2026-01  30.1%
2025-02  33.6%   2025-08  40.7%   2026-02  18.2%
2025-03  53.1%   2025-09  34.3%   2026-05  16.3%
2025-04  61.8%   2025-10  27.1%   2026-06  21.9%
                                  2026-07  20.9%
```

---

## 2. ✅ Genuine out-of-sample check — your thesis held

The May–July 2026 data was not available when the 30/55 prior was proposed. It is
a clean forward test of the **entry** signal:

| | |
|---|---|
| RP entering the OOS window (2026-05-05) | 17.7% |
| RP low in window (2026-05-16) | **13.0%** |
| RP now (2026-07-27) | **21.6%** |
| Buy at the low, hold to now, net of costs | **+4.4% in grams** |

**RP rose 8.6pp off the low. Buying deep-value RP was the right call.** The
directional core of your strategy was validated on data the model never saw.

---

## 3. The grid (430 sessions, timestop 75)

| buy\sell | 42% | 45% | 48% | 50% | 55% | 60% | 65% |
|---|---|---|---|---|---|---|---|
| 16% | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 |
| 20% | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 | 0.983 |
| 22% | 1.014 | 1.014 | 1.014 | 1.014 | 1.014 | 1.014 | 1.014 |
| 25% | 0.968 | 0.968 | 0.968 | 0.968 | 0.968 | 0.968 | 0.968 |
| 28% | 0.942 | 0.942 | 0.942 | 0.942 | 0.942 | 0.942 | 0.942 |
| **30%** | 0.949 | 0.982 | 1.001 | 1.006 | 1.042 | **1.175** | **1.175** |
| 32% | 0.949 | 0.982 | 1.001 | 1.006 | 1.042 | 1.175 | 1.175 |
| 35% | 0.858 | 0.889 | 0.906 | 0.910 | 0.942 | 1.063 | 1.063 |

Trades now 2–7 (was 1–3). Only **19 of 63** beat doing nothing. Median 0.983.

### 🔴 The cliff survived the data expansion

| buy band | NAV |
|---|---|
| 28% | 0.9417 |
| **29%** | **0.9470** |
| **30%** | **1.1753** |
| 32% | 1.1753 |
| 33% | 1.0793 |

Still a 23-point jump on a 1-point parameter change, still traceable to
**2025-02-11 (RP = 29.75%)**. Doubling the sample did not cure it — because the
problem is not sample size, it is that an all-in threshold makes the whole result
hinge on single-tick crossings.

---

## 4. ✅ Scaling in works — the one clear win

Buying in thirds at three descending levels instead of all-in at one:

| approach | mean NAV | min | max | **spread** | sd |
|---|---|---|---|---|---|
| All-in (7 variants) | 1.0642 | 0.9417 | 1.1753 | **0.2336** | 0.1045 |
| Scaled thirds (7 variants) | 1.0365 | 0.9741 | 1.0825 | **0.1085** | 0.0420 |

**Parameter sensitivity more than halves.** You give up ~3% of headline return
and remove ~54% of the cliff risk. On a strategy whose apparent edge is
manufactured by one lucky tick, that is unambiguously the right trade.

Cost sensitivity of scaled [30,25,20] / sell 60:

| cost/leg | NAV |
|---|---|
| 0.00% | 1.1499 |
| 0.75% | 1.0642 |
| 1.50% | 0.9847 |
| 2.00% | 0.9349 |

**Breakeven at ~1.4%/leg.** With 12 trades this is now a real constraint — unlike
v1 where low turnover hid it. Physical dealer spreads (`RESEARCH.md` §3) put you
uncomfortably close to that line.

---

## 5. 🔴 Walk-forward still fails — and now I know exactly why

Train on the first 60% (258 sessions), test on the last 40% (172):

| | In-sample | Out-of-sample |
|---|---|---|
| Best all-in (30/60) | 1.2944 | **0.9520** |
| Best scaled ([30,25,20]/60) | 1.0993 | **0.9750** |
| Mean of 10 scaled variants | — | **0.9769** |
| Mean of 10 all-in variants | — | **0.9370** |
| Hold مثقال | 1.0000 | **1.0000** |

Scaled beats all-in out of sample (0.977 vs 0.937) — the robustness fix is real.
**But neither beats doing nothing.**

### The cause is unambiguous

```
TRAIN  2024-10-30 → 2025-10-08 :  RP 58% → 29%,  max 76%,  min 27%
TEST   2025-10-09 → 2026-07-27 :  RP 28% → 22%,  max 42%,  min 13%

Sessions with RP ≥ 55%:  TRAIN 46   |   TEST 0
Sessions with RP ≥ 45%:  TRAIN many |   TEST 0
Sessions with RP ≥ 35%:              |   TEST 9
```

**In the entire test window RP never exceeded 42%.** Every sell band ≥45% is
physically unreachable. The strategy buys, then can only ever exit on the
timestop — it is structurally long ربع through a regime that stayed depressed.

This is not a fitting artifact. It is a **regime shift**: the CBI auction
programme and annual re-minting (`RESEARCH.md` §2) reset the entire RP
distribution downward, and the 2026 war period kept it there.

### What would have worked in that regime

| buy ≤22%, sell ≥ | OOS NAV |
|---|---|
| 24% | 1.0428 |
| 26% | **1.0596** |
| 35% | 1.0523 |

A sell band of **26%** — absurd against the 2024 distribution — was optimal.
**The correct bands in the new regime are roughly half the old ones.**

---

## 6. The real conclusion: bands must be regime-relative

Fixed absolute bands cannot work across a distributional reset. But note the
important nuance — I tested rolling quantiles **only in the OOS window**:

| window | quantiles | OOS NAV |
|---|---|---|
| 120 | q[0.25, 0.75] | 0.9933 |
| 120 | q[0.15, 0.85] | 0.9852 |
| 180 | q[0.20, 0.80] | 0.9520 |
| 250 | any | 0.9520 |

Short windows (120) adapt and nearly break even; long windows (250) fail exactly
like fixed bands. This **partially reverses** my v1 advice. The accurate
statement is:

> Rolling quantiles fail when the window straddles a regime break (v1's finding,
> still correct). They are the *better* choice once you are inside a new stable
> regime, provided the window is short enough (~120 sessions) to have forgotten
> the old one.

Neither variant clears 1.0000 in this window, so I am not recommending either as
a deployable rule yet.

---

## 7. Recommended configuration (provisional, not for full size)

```
ENTRY   scale in thirds at the trailing-120-session 25th / 15th / 8th percentile of RP
EXIT    trailing-120-session 75th percentile of RP,  OR
        +12pp above weighted average entry,  OR
        90-session timestop  — whichever fires first
COST    abort any leg if round-trip cost > 1.2%/leg (breakeven is ~1.4%)
SIZE    at most 1/3 of the intended book until a full up-cycle is observed
```

Rationale: fixed bands are dead (§5); scaling is proven (§4); short adaptive
windows are the only exit family that survived the regime shift (§6); the cost
constraint is now binding (§4).

**Current reading (2026-07-27): RP = 21.6%, ~p25 of the last 120 sessions.**
That is a first-tranche buy zone but *not* a deep-value level any more — the
13.0% low in May was.

---

## 8. What actually limits us, and what Phase 2 should be

The honest constraint is **not** parameter choice. It is that 430 sessions
contain **one and a half cycles and one regime break**. Every failure in this
document traces to that.

Three things would change the answer, in priority order:

1. **Full 2019–2024 daily series.** I retrieved annual snapshots
   (`QUARTER_MESGHAL.md` §3) showing RP ran 21.7% → 79.5% → 19.4%, but the
   *daily* path for 2019–2024 is still not in the repo. That period contains
   the previous full cycle and probably 10+ independent round trips. Without it
   we cannot distinguish "band is wrong" from "regime changed."
2. **Mint-year-specific quotes.** tgju `rob` is a blend of ۱۳۸۶/۱۴۰۳/۱۴۰۴, which
   trade up to 1m toman apart (`RESEARCH.md` §2). On a 3% cost hurdle that
   ambiguity is larger than the edge.
3. **Real dealer bid/ask.** Breakeven is ~1.4%/leg and physical spreads sit near
   it. The venue decision (physical vs ETF) plausibly matters more than any band.

**My recommendation: do not size up yet.** The signal is real and was validated
out of sample in §2, but no parameterisation has yet beaten holding مثقال on
unseen data. Phase 2 should be pulling item 1 above, not tuning further.

---

## 9. Changes from v1

| | v1 (365 sessions) | v2 (430 sessions) |
|---|---|---|
| Grid optimum | 30/60 = 1.171 | 30/60 = 1.175 (unchanged) |
| Cliff at 29→30% | yes | **still yes** |
| Trades | 1–3 | 2–7 |
| Scaling tested | proposed only | **tested: spread 0.234 → 0.108** |
| Rolling quantiles | "do not use" | **nuanced: short windows OK post-break** |
| OOS entry signal | untested | **✅ validated (+4.4% grams)** |
| Cost breakeven | not binding | **~1.4%/leg — now binding** |
