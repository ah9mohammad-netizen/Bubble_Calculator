# Finding A and B — ربع سکه ↔ مثقال

**Your question:** you hold 1 quarter coin. Sell it for mesghal when the quarter
bubble is above **A**, buy it back when the bubble falls to **B**. Find A and B.

**You were right and my previous benchmark was wrong.** I had been measuring
against "hold مثقال." Your starting asset is a **quarter coin**, so the bar is
holding that coin. Measured correctly, the strategy wins — decisively.

---

## The answer

| | A (sell ربع) | B (buy ربع) |
|---|---|---|
| **Recommended** | **65%** | **20%** |
| Highest raw return | 60% | 30% |
| Most stable plateau | 70% | 15% |

**Recommended pair: A = 65%, B = 20%.**

Result on 430 sessions (2024-10-30 → 2026-07-27), 0.75%/leg costs:

```
Start:   1 quarter coin        = 1.8288 g pure gold
Finish:  1.4811 quarter coins  = 2.7087 g pure gold
         +48.1% more gold, in 2 completed trades
```

C and D — the bounds you asked about, as observed:
**C (floor) = 13.0%**, **D (ceiling) = 76.0%**.

---

## Step 1 — Crossing counts (your method)

How often the line actually crosses each candidate level:

| A (sell) | upward crossings | | B (buy) | downward crossings |
|---|---|---|---|---|
| 40% | 4 | | 13% | **0** |
| 45% | 8 | | 15% | 3 |
| 50% | 8 | | 16% | 4 |
| 55% | 4 | | 18% | 8 |
| 60% | 4 | | 20% | **9** |
| 65% | 4 | | 22% | 4 |
| 70% | 2 | | 25% | 3 |
| 75% | **1** | | 28% | **9** |

This is exactly the right way to pick the levels. It rules out the extremes
immediately: **A = 75% fires once** (not a strategy, a single event) and
**B = 13% never fires** (it is the floor itself — you can't buy at the absolute
minimum). The levels that fire often enough to be tradeable are
**A ∈ [45%, 65%]** and **B ∈ [18%, 30%]**.

---

## Step 2 — The full grid, measured in quarter coins

Wealth after the period, starting from 1 quarter coin. **Benchmark = 1.000.**

| A\B | 15% | 16% | 18% | 20% | 22% | 25% | 28% | 30% |
|---|---|---|---|---|---|---|---|---|
| 40% | 1.349 | 1.333 | 1.333 | 1.333 | 1.491 | 1.369 | 1.281 | 1.329 |
| 45% | 1.349 | 1.333 | 1.333 | 1.333 | 1.261 | 1.234 | 1.204 | 1.310 |
| 50% | 1.349 | 1.333 | 1.333 | 1.333 | 1.261 | 1.234 | 1.204 | 1.342 |
| 55% | 1.349 | 1.333 | 1.333 | 1.333 | 1.261 | 1.234 | 1.204 | 1.389 |
| 60% | 1.387 | 1.371 | 1.371 | 1.371 | 1.297 | 1.269 | 1.238 | **1.612** |
| 65% | **1.499** | 1.481 | 1.481 | 1.481 | 1.402 | 1.371 | 1.338 | 1.324 |
| 70% | **1.499** | 1.481 | 1.481 | 1.481 | 1.402 | 1.371 | 1.338 | 1.324 |

**All 56 cells beat holding the coin.** Worst cell = **1.204** (+20.4%).
Median = 1.333 (+33%). Best = 1.612 (+61%).

This is the key result, and it is what I got wrong before. There is no
parameter choice in this range that loses to holding the coin — the entire
question is *how much* you gain, not *whether*.

---

## Step 3 — Why 65/20 and not 60/30

60/30 scores highest (1.612) but sits on a spike:

```
        B=28%   B=30%   B=32%
A=55%   1.204   1.389   1.389
A=60%   1.238   1.612   1.612     ← 1.612 only when B ≥ 30
A=65%   1.338   1.324   1.324
```

Moving B from 30% → 28% drops it 1.612 → 1.238. That is a **cliff**.

Ranking every pair by its **worst neighbour** instead of its own score:

| A | B | self | neighbourhood worst |
|---|---|---|---|
| 70% | 15% | 1.499 | **1.481** |
| 70% | 16% | 1.481 | **1.481** |
| 70% | 18% | 1.481 | **1.481** |
| 65% | 15% | 1.499 | 1.371 |
| 65% | 18% | 1.481 | 1.371 |

The **A ∈ [65,70], B ∈ [15,20]** block is a genuine plateau — every pair in it
returns 1.37–1.50 regardless of where exactly you put the line.

I recommend **A=65%, B=20%** rather than 70/15 because A=70% crossed only **twice**
and B=15% only **three times**. 65/20 sits on the same plateau but with levels the
market actually reaches often enough to trade. It gives up ~1% of return for
materially more opportunities.

---

## Step 4 — Cost robustness

| pair | 0% | 0.75% | 1.5% | 2.0% |
|---|---|---|---|---|
| A=60 B=30 | 1.713 | 1.612 | 1.518 | 1.457 |
| **A=65 B=20** | 1.526 | **1.481** | 1.437 | 1.408 |
| A=55 B=20 | 1.373 | 1.333 | 1.293 | 1.267 |
| A=45 B=22 | 1.300 | 1.261 | 1.224 | 1.199 |

**Even at 2% per leg — worse than any real dealer — every pair still beats
holding the coin by 20–46%.** Because the trade only fires 2–4 times, costs
barely matter. This is the opposite of the high-turnover versions I tested
earlier, where costs were binding.

---

## The trades it would have made (A=65, B=20)

```
2025-03-17   SELL quarter @ RP = 76.0%    →  into mesghal
2026-05-12   BUY  quarter @ RP = 19.0%    →  back into quarter
```

Two decisions in 21 months. You sold the coin when its premium over melted gold
was 76%, sat in mesghal while that premium collapsed, and bought back ~1.48
coins with the proceeds of 1.

That is precisely the mechanism you described, and the arithmetic is simply:

```
gram_gain = (1 + A) / (1 + B) × (1 − c)⁴
          = 1.65 / 1.20 × 0.970  =  1.334  per completed cycle
```

Each full A→B round trip compounds ~33% more gold at these levels.

---

## Important caveats

1. **Only 2–4 completed trades in this window.** The direction is unambiguous
   (56/56 cells profitable) but the *magnitude* rests on few events. Expect
   ~+30% per cycle, not +61%.
2. **The window contains one big down-leg** (76% → 13%), which flatters any
   sell-high-buy-low rule. A period where RP grinds sideways at 40% would
   produce no trades at all — that is fine (you just hold the coin), but it
   means returns arrive in lumps, not steadily.
3. **RP today is 21.6%** — just above B=20%. You are near the buy zone. The
   floor of 13.0% was touched in May 2026.
4. **Mint year matters** (`RESEARCH.md` §2): ۱۳۸۶ / ۱۴۰۳ / ۱۴۰۴ trade up to 1m
   toman apart, and tgju's `rob` index blends them. Confirm which coin you are
   quoted — on a 33%-per-cycle edge this is a detail, but on entry timing it
   shifts RP by a few points.
5. **C is not a hard floor.** 13.0% is the observed minimum in this data, not a
   law. Coins cannot trade below melt indefinitely, so the true floor is
   somewhere near 0–10%, but do not assume 13% holds.

---

## Rule to follow

```
IF holding ربع سکه  AND  RP ≥ 65%   →  SELL all ربع, buy مثقال
IF holding مثقال    AND  RP ≤ 20%   →  SELL all مثقال, buy ربع
OTHERWISE                            →  do nothing

RP = (P_ربع / 1.8288) / (P_مثقال / 3.2489) − 1

where 1.8288 = 2.032 g × 0.900   (fine gold in a quarter coin)
      3.2489 = 4.6083 g × 0.705  (fine gold in a mesghal of آب‌شده)
```

You need only two numbers off the dealer board. No dollar, no world spot — they
cancel out of the ratio.

**Current reading (2026-07-27): RP = 21.6% → HOLD, close to the buy trigger.**
