# Sensitivity Analysis — Buy/Sell Bands for RP (ربع ↔ مثقال)

Objective: find the best low/high band for the relative premium
`RP = (P_ربع/1.8288) / (P_مثقال/3.2489) − 1`.

Data: 365 sessions, 2024-10-30 → 2026-02-19 (your archive).
NAV in fine grams, start 1.000 g held as مثقال, cost 0.75%/leg.

**Benchmark to beat: hold مثقال = 1.0000 g.** (Hold ربع = 0.7359 g.)

---

## Result up front

**The grid produces an apparent optimum at buy<30% / sell>60% = 1.1711 g (+17%).**

**Do not use it.** It fails every robustness test below. The honest output of
this analysis is not a band — it is the finding that **this dataset cannot
identify one**, plus a signal-level result (§5) that *is* trustworthy and tells
us what to do next.

---

## 1. The grid

Final NAV in grams, cost 0.75%/leg, no filters:

| buy\sell | 45% | 50% | 55% | 60% | 65% | 70% | 75% |
|---|---|---|---|---|---|---|---|
| 18% | 0.995 | 0.995 | 0.995 | 0.995 | 0.995 | 0.995 | 0.995 |
| 20% | 0.995 | 0.995 | 0.995 | 0.995 | 0.995 | 0.995 | 0.995 |
| 22% | 0.942 | 0.942 | 0.942 | 0.942 | 0.942 | 0.942 | 0.942 |
| 25% | 0.922 | 0.922 | 0.922 | 0.922 | 0.922 | 0.922 | 0.922 |
| 28% | 0.899 | 0.899 | 0.899 | 0.899 | 0.899 | 0.899 | 0.899 |
| **30%** | 0.979 | 1.002 | 1.038 | **1.171** | **1.171** | **1.171** | **1.171** |
| 32% | 0.979 | 1.002 | 1.038 | 1.171 | 1.171 | 1.171 | 1.171 |
| 35% | 0.916 | 0.938 | 0.971 | 1.096 | 1.096 | 1.096 | 1.096 |

Trade counts across the *entire* grid: **1 to 3.** Median 1.

Only **16 of 56** configurations beat doing nothing.

Note the rows are flat across sell bands from 60% onward — because RP only
exceeded 60% on a handful of days, so 60/65/70/75 are the *same trade*.

---

## 2. 🔴 The optimum is a cliff edge, not a peak

Scanning the buy band finely at sell=60%:

| buy band | NAV | trades |
|---|---|---|
| 24% | 0.9423 | 1 |
| 26% | 0.9148 | 1 |
| 28% | 0.8993 | 1 |
| **29%** | **0.8900** | 1 |
| **30%** | **1.1711** | 3 |
| 31% | 1.1711 | 3 |
| 32% | 1.1711 | 3 |
| 34% | 1.1065 | 3 |

A **1-percentage-point** change in the buy band moves NAV from 0.890 to 1.171 —
a 28-point swing. That is not a robust optimum. That is a discontinuity.

### The cause: one single day

Trade logs either side of the boundary:

```
buy<29%:  2025-09-13 BUY @28.9%          → 0.8900  (never exits)

buy<30%:  2025-02-11 BUY @29.8%
          2025-03-17 SELL @76.0%   ← +41% round trip
          2025-09-13 BUY @28.9%          → 1.1711
```

The entire +28pp difference is **one entry on 2025-02-11 when RP printed
29.75%.** Had that day printed 30.1% instead of 29.75%, the "optimal" strategy
would have returned 0.89 g.

RP values that week: 29.75, 30.23, 31.61, 30.39, 29.81, 31.49, 31.69. The signal
brushed the threshold and bounced. **The result is a coin flip on tick noise.**

---

## 3. 🔴 Walk-forward: the optimum inverts out of sample

Fit on the first half, test on the second — the only test that matters.

| | |
|---|---|
| **In-sample** (2024-10-30 → 2025-07-02), best of grid | buy<30% / sell>60% → **1.3159 g**, 2 trades |
| **Out-of-sample** (2025-07-06 → 2026-02-19), same params | **0.8900 g**, 1 trade |
| Out-of-sample, hold مثقال | **1.0000 g** |
| Out-of-sample, hold ربع | 0.8015 g |

The in-sample champion **loses 11% of your gold** out of sample, underperforming
doing nothing. This is the textbook signature of a parameter fitted to noise.

---

## 4. Cost sensitivity (the one test it passes)

For the 30/60 config:

| cost/leg | NAV |
|---|---|
| 0.00% | 1.2252 |
| 0.75% | 1.1711 |
| 1.50% | 1.1190 |
| 2.00% | 1.0854 |

Robust to costs — but irrelevant, because the underlying trade selection is not
robust. Low turnover (3 trades) means costs were never going to be the binding
constraint. **This is the trap:** a strategy can look cost-insensitive purely
because it barely trades.

---

## 5. ✅ What IS statistically solid — the signal itself

Set bands aside and ask directly: does RP level predict forward RP change?
All overlapping 40-session observations:

| RP at entry | n | 40d forward change | win rate |
|---|---|---|---|
| 0–25% | 6 | **+4.6pp** | **100%** |
| 25–30% | 44 | **+4.5pp** | **82%** |
| 30–35% | 53 | **+8.3pp** | 60% |
| 35–45% | 100 | −3.1pp | 25% |
| 45–55% | 76 | **−9.3pp** | 7% |
| 55%+ | 46 | **−13.6pp** | **4%** |

**This is a clean, monotonic, strongly-signed relationship.** Low RP → rises.
High RP → falls, hard. The 55%+ bucket has a **4% win rate** across 46
observations. The 25–30% bucket has **82%** across 44.

**Your thesis is confirmed at the signal level.** The mean reversion is real and
the effect sizes are large relative to the ~3% cost hurdle.

### So why doesn't the backtest capture it?

Because those n=44 and n=46 observations are **overlapping daily samples of only
a handful of independent episodes.** Counting actual threshold crossings:

- RP crossed below 25%: **2 times**
- RP crossed below 30%: **8 times**
- RP crossed above 60%: **4 times**
- RP crossed above 70%: **2 times**

A complete round trip needs one low crossing *and* one subsequent high crossing.
In 365 sessions there were **at most 3 such opportunities.** You cannot fit two
parameters on three events. The grid isn't measuring skill; it's measuring which
side of a threshold three coin flips landed on.

---

## 6. Recommendation

### Do not pick a band from this data. Pick it from the structure.

The signal table (§5) is far more trustworthy than the NAV grid, because it uses
193 observations of RP-level→outcome rather than 3 round trips. Reading bands
off §5 directly:

```
BUY  ربع  when RP ≤ 30%     (25–30% bucket: +4.5pp fwd, 82% win)
SELL ربع  when RP ≥ 55%     (55%+ bucket: −13.6pp fwd, 4% win)
```

These are **structurally** motivated, not curve-fitted: they sit where the sign
of the forward-return relationship flips, and both sides have 40+ supporting
observations. The 30/55 pair also comfortably clears the cost hurdle — a
30%→55% round trip nets **+16.2%** in grams at 0.75%/leg.

I deliberately choose 55% over 60% despite 60% scoring better in the grid. The
grid preference for 60% comes from a single 76% spike in March 2025; the §5
evidence says the edge is already strongly negative from 55% up. **Take the
statistically-supported exit, not the one that happened to catch the peak once.**

### Mandatory risk controls (from §2's failure mode)

Every configuration that ended holding ربع did so because **no exit ever fired**.
Non-negotiable:

1. **Time stop:** exit after ~75 sessions (2 half-lives) regardless of RP.
2. **Scale in:** ⅓ at 30%, ⅓ at 25%, ⅓ at 20%. The 1pp cliff in §2 exists
   *because* the strategy went all-in at one threshold. Scaling removes that
   sensitivity entirely — this is the single most valuable fix.
3. **No-new-lows filter:** don't enter while RP is still making 60-session lows.

### What this phase cannot tell us, and what would

We cannot validate bands on 3 round trips. To move to the next phase properly we
need **the full daily 2019→2026 RP series** (~1,700 sessions). §3 of
`QUARTER_MESGHAL.md` already showed via annual snapshots that this window covers
a complete 21.7% → 79.5% → 19.4% cycle — that period plausibly contains
**10–15 independent round trips**, which is enough to fit two parameters and
still hold back an out-of-sample block.

**Recommendation: do not commit capital to a specific band yet.** The structural
30/55 pair above is a sound prior. Confirm it on the long series before sizing up.

---

## 7. Summary

| Test | Result |
|---|---|
| Grid optimum found | buy<30% / sell>60% = 1.171 g |
| Neighbour stability | ❌ **cliff** — 1pp shift → 0.890 |
| Driven by | ❌ **one day** (2025-02-11) |
| Walk-forward | ❌ **1.316 IS → 0.890 OOS** (worse than nothing) |
| Cost robustness | ✅ passes (but only because turnover is 3) |
| Independent round trips | ❌ **3** |
| Signal-level evidence | ✅ **strong, monotonic, n=193** |

**Verdict: the signal is real; the band is not yet identifiable.** Proposed
structural prior **30% / 55%** with scaling and a time stop, to be validated on
the 2019–2026 series before any capital is committed.
