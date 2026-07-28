# Five Approaches Compared — 1 bn Rial

**⚠️ Important: I could not run this from 2020-01-01.** See §4 for why and what
it would take. Results below cover **2024-08-03 → 2026-07-27** (495 sessions,
~2 years), which is the deepest window where I have all series aligned.

All figures in rials, **2% per leg** fee + slippage.

---

## 1. Head-to-head — all three assets

Window: **2025-01-04 → 2026-07-27** (375 sessions, 18.7 months)

| # | Approach | Final | Return | Trades |
|---|---|---|---|---|
| 1 | Hold USD | 2.331 bn | **+133.1%** | 0 |
| 2 | Hold ربع سکه | 3.103 bn | **+210.3%** | 0 |
| 3 | Hold مثقال | 3.556 bn | **+255.6%** | 0 |
| 4 | Quarter ↔ Mesghal switching | 4.029 bn | **+302.9%** | **3** |
| 5 | **Two-layer strategy** | **4.376 bn** | **+337.6%** | **4** |

**Ranking: 5 > 4 > 3 > 2 > 1.** The layered system wins, and every gold approach
beats USD by a wide margin.

### Trade log — strategy 5

```
2025-02-11   M → Q    RP=30%  vol=1.7%   LAYER 2   quarter cheap, buy it
2025-03-17   Q → M    RP=76%  vol=2.2%   LAYER 2   bubble peaked, sell
2025-09-13   M → Q    RP=29%  vol=1.6%   LAYER 2   quarter cheap again
2026-02-02   Q → U    RP=21%  vol=3.4%   LAYER 1   vol spike, exit to USD
                                                    → currently in USD
```

Four decisions in 19 months.

---

## 2. Longer window — gold only

Window: **2024-08-03 → 2026-07-27** (495 sessions, ~24 months). USD not aligned
this far back, so strategies 1 and 5 are excluded.

| # | Approach | Final | Return | Trades |
|---|---|---|---|---|
| 2 | Hold ربع سکه | 3.484 bn | **+248.4%** | 0 |
| 3 | Hold مثقال | 5.058 bn | **+405.8%** | 0 |
| 4 | **Quarter ↔ Mesghal** | **5.731 bn** | **+473.1%** | **3** |

```
Strategy 4  vs  hold مثقال : 1.133×
Strategy 4  vs  hold ربع   : 1.645×
```

Note how much the answer depends on the window: over 2 years hold-مثقال returns
+406%, over 18.7 months +256%. **Start date matters enormously in a market
compounding at this rate** — which is exactly why the 2020 start you asked for
is not a cosmetic detail.

---

## 3. What the numbers say

**Trade counts are low by design.** 3–4 trades over ~2 years. At 2%/leg each
round trip costs ~4pp, so the system only acts on large, well-separated signals.
This is a feature — §1.2 of `A_AND_B.md` showed that forcing more trades
*reduces* returns at this cost level (8 trades → 1.103× vs 4 trades → 1.457×).

**Layer 2 does most of the work.** Three of four trades are quarter↔mesghal.
It contributed +47pp over hold-مثقال (302.9% vs 255.6%).

**Layer 1 fired once and added +35pp** (337.6% vs 302.9%) by exiting to USD on
the February 2026 volatility spike.

**Holding rial cash returns 0% nominal** — against gold up 256–406%, that is the
real baseline being escaped.

---

## 4. 🔴 Why not from 2020-01-01

Your question needs **~1,320 sessions × 3 series ≈ 4,000 data points**. The tgju
API returns them ~65 rows per request, so this is **60+ sequential fetches**.
I completed roughly a third before hitting practical limits in this session.

**What I have:**

| series | coverage |
|---|---|
| ربع سکه | 2021-12 → 2026-07 (partial, gaps) |
| مثقال | 2023-07 → 2026-07 (continuous) |
| USD/IRR | 2025-01 → 2026-07 (continuous) |

**The binding constraint is USD**, which only goes back to 2025-01 in my
assembled file — so the two-layer strategy cannot be tested before then no
matter how much coin data I add.

### What a 2020 start would likely show

Directionally, from `QUARTER_MESGHAL.md` §3, RP ran **21.7% (2020) → 79.5%
(2023) → 19.4% (2026)** — a full cycle. A 2020 start would therefore:

- **begin near an RP low**, so strategy 4 would buy ربع early and ride the rise
  to 79.5% — probably **2–3 extra round trips** and a materially better result
  than the 1.13× seen here
- include the **2020 COVID gold spike** and the **2022 rial collapse**, both
  high-volatility episodes that would have triggered Layer 1
- give **8–12 trades** rather than 4

But I want to be explicit: **that is reasoning from annual snapshots, not a
backtest.** I am not going to hand you a number I did not compute.

### To do it properly

The clean path is a script that pages the API directly rather than manual
fetches:

```
for start in range(0, 1400, 100):
    GET api.tgju.org/v1/market/indicator/summary-table-data/{rob|mesghal|price_dollar_rl}
        ?start={start}&length=100
```

~42 calls total, a few minutes from any machine with internet. The sandbox here
has no outbound network, which is what forced the manual approach.

---

## 5. Bottom line

On the ~2 years I can verify:

```
1 bn rial, 2025-01-04 → 2026-07-27

  hold USD          →  2.331 bn   (+133%)    0 trades
  hold ربع سکه      →  3.103 bn   (+210%)    0 trades
  hold مثقال        →  3.556 bn   (+256%)    0 trades
  Q↔M switching     →  4.029 bn   (+303%)    3 trades
  TWO-LAYER         →  4.376 bn   (+338%)    4 trades   ← best
```

The ordering is consistent with everything built so far, and the walk-forward in
`FLOWCHART.md` (48/81 configs beat gold out-of-sample, worst case 1.650× vs gold
1.739×) supports it not being a fluke.

**Caveat I keep repeating because it matters: 4 trades is a small sample.** The
mechanism behind Layer 1 is well-evidenced (299-observation monotonic
volatility→outperformance table), but the *strategy* has only fired a handful of
times. Trade at reduced size until you have seen a full cycle live.

Data: `data/qm_ext.csv` (495 sessions), `data/usd_irr.csv` (441 sessions).
Code: `compare5.py`.
