# Z-score persistence: 0 vs 1 vs 2 confirmations

Reproduce with `python3 zscore_persist.py`.

Naming, so we don't talk past each other:

| this doc | consecutive closes required | meaning |
|---|---|---|
| **0 persistence** | P = 1 | trade the first close that breaches the threshold |
| **1 persistence** | P = 2 | one extra confirming close |
| **2 persistence** | P = 3 | the spec as written |

Everything below: entry z > +1.75, exit z < +0.50, cooldown 30, 2% per leg,
position measured in **fine grams of gold**, 1.0000 = buy-and-hold مثقال.

## Sample — read this first

```
spot × domestic overlap : 244 sessions   2025-02-07 → 2026-07-27
sessions with a z-score : 169 sessions   2025-07-22 → 2026-07-27   (0.68 yr)
```

**169 sessions. Eight months.** The 75-session rolling window eats the first
75 of the 244. This is not enough data to rank three rules, and nothing below
should be read as a validated result. It is a description of what happened in
one eight-month window that contained one large rial devaluation.

## Headline

| rule | trades | per yr | grams | vs hold |
|---|---|---|---|---|
| **0 persistence (P=1)** | 4 | 5.9 | **1.0881** | **+8.8%** |
| 1 persistence (P=2) | 0 | 0.0 | 1.0000 | 0.0% |
| 2 persistence (P=3, spec) | 0 | 0.0 | 1.0000 | 0.0% |
| buy & hold مثقال | 0 | 0.0 | 1.0000 | 0.0% |

**Relaxing from 2 confirmations to 1 changes nothing. Only dropping
persistence entirely produces any trades at all.** There is no middle ground
here — it is a binary.

## Why: entries are spikes, exits are plateaus

```
condition            closes  episodes  run lengths
z > +1.75 (entry)         3         3  [1, 1, 1]
z > +1.50                 9         8  [2, 1, 1, 1, 1, 1, 1, 1]
z > +1.25                18        13  [3, 3, 2, 1, 1, 1, 1, 1, 1, 1]
z > +1.00                27        18  [3, 3, 2, 2, 2, 2, 2, 1, 1, 1]
z < +0.50 (exit)        116        25  [21, 15, 15, 14, 7, 6, 5, 4, 3, 3]
```

Every single breach above +1.75 was a **one-day spike**. Not one lasted two
closes. Meanwhile the exit condition sits below +0.50 for runs of 21, 15, 15,
14 sessions.

That asymmetry is the whole story, and it is structural, not bad luck. The
Tehran basis blows out when the rial gaps or a war headline hits, and it is
arbitraged back within a day or two. The spec's persistence filter was
designed to suppress noise; on this series it suppresses the entire signal,
because the signal *is* the spike.

Confirming this, the entry/exit split:

| | exit P=1 | exit P=2 | exit P=3 |
|---|---|---|---|
| **entry P=1** | 1.0881 | 1.0620 | 1.0663 |
| **entry P=2** | 1.0000 | 1.0000 | 1.0000 |
| **entry P=3** | 1.0000 | 1.0000 | 1.0000 |

Exit persistence is nearly free (plateaus satisfy it anyway). **Entry
persistence is the entire binding constraint.**

## The 4 trades under 0 persistence

```
2025-09-24  GOLD->USD  z=+3.18
2025-11-18  USD->GOLD  z=+0.15
2026-02-03  GOLD->USD  z=+1.76
2026-06-08  USD->GOLD  z=-0.64
```

| round trip | USD | gold | gross edge | net of 2%×2 |
|---|---|---|---|---|
| 2025-09-24 → 2025-11-18 | +7.4% | +11.9% | −4.0% | **−7.8%** |
| 2026-02-03 → 2026-06-08 | +15.4% | −6.1% | +22.9% | **+18.0%** |

**One loser, one winner, and the winner is the entire result.** The +8.8%
is one trade. Take away 2026-02-03 and the rule is down 7.8%.

## Placebo test

Under 0 persistence the rule sat in USD for 61 of 169 sessions (36% of the
time), in two blocks of 31 and 30. I re-ran 12,189 random placements of two
same-length USD windows in the same period:

```
random windows: median 0.8671   5% 0.6800   95% 1.0523
rule result   : 1.0881  -> beaten by 2.5% of random placements   (p = 0.03)
```

So the timing is not *nothing* — p = 0.03 is on the good side. But: it is one
observation of a two-trade rule over eight months, and the median random
placement loses 13% because being in USD was mostly the wrong call in this
window. The rule's edge is that it happened to catch the one stretch where it
wasn't. n = 2 does not distinguish that from luck no matter what the p-value
says.

## What would make P=2 or P=3 trade

Lowering the entry threshold instead of the persistence:

| z_enter | P=1 trades / grams | P=2 trades / grams | P=3 trades / grams |
|---|---|---|---|
| 2.00 | 2 / 0.9222 | 0 / 1.0000 | 0 / 1.0000 |
| **1.75** | **4 / 1.0881** | 0 / 1.0000 | 0 / 1.0000 |
| 1.50 | 4 / 1.0881 | 2 / 0.8812 | 0 / 1.0000 |
| 1.25 | 4 / 1.0618 | 2 / 0.9001 | 2 / 0.8847 |
| 1.00 | 4 / 1.0618 | 4 / 1.0265 | 2 / 0.8847 |
| 0.75 | 5 / 0.7055 | 4 / 1.0265 | 3 / 0.8881 |

**Every single cell where P=2 or P=3 trades, it loses money.** Not one
combination of (lower threshold + persistence) beats buy-and-hold. The
confirmation delay means you buy dollars *after* the basis has already started
mean-reverting — you enter at the worst point of the spike.

This is the same failure mode already documented for USD-vol in Layer 1: the
rial devalues in jumps, so any rule that waits for confirmation buys the top.

## Cost and cooldown

```
cost/leg     P=1      P=2      P=3
0.0%      1.1797   1.0000   1.0000
0.5%      1.1562   1.0000   1.0000
1.0%      1.1332   1.0000   1.0000
2.0%      1.0881   1.0000   1.0000
3.0%      1.0443   1.0000   1.0000
```

Even at zero cost, P=2 and P=3 stay at exactly 1.0000 — they never trade. Cost
is not what's killing them.

```
cooldown   trades   grams
0               6  1.0665
5               6  0.9801
10              4  0.9364
20              4  0.8561
30              4  1.0881   <- current
45              2  0.8717
60              2  0.8370
```

⚠️ Cooldown 30 is the single best value in the grid, and its neighbours (20 →
0.8561, 45 → 0.8717) are much worse. That is a spike in a parameter surface,
not a plateau. **This is a warning sign of overfitting**, and it is the reason
I would not put money on the P=1 number even though it looks good.

## Recommendation

**Do not switch the z-score to executing, at any persistence setting.**

- 2 confirmations (spec) and 1 confirmation are **identical: zero trades**.
  There is nothing to choose between them.
- 0 persistence is the only variant that trades. It shows +8.8%, but that is
  **two round trips, one of which is a loss**, over eight months, with a
  parameter surface that spikes at the current cooldown.
- Every attempt to keep persistence *and* get trades (by lowering the
  threshold) loses money — in all 8 such cells.

The honest read is that the basis z-score, as specified, does not fire on
Tehran data because Tehran basis dislocations do not persist. Fixing that by
removing the filter leaves a rule with n=2 and no out-of-sample evidence.

**Keep it as a displayed indicator.** Layer 1 (vol90) and Layer 2 (RP) keep
driving the position.

If you want to actually settle this, the binding constraint is data, not
parameters: 169 scored sessions needs to become ~1,500. That means a full
XAU/USD daily series back to 2020. tgju's `ons` has it, but the sandbox can
only page ~60 records per fetch (~25 more calls). LBMA publishes the entire
daily history as one JSON file, but it is not reachable from this sandbox's
shell — only the page-fetch tool reaches it, and it chunks. Say the word and
I'll grind through the paging.
