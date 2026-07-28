# A/B at 2% Cost + Phase 2 (USD vs Gold Momentum)

Cost assumption updated to **2% per leg** (fee + slippage), as you specified.
A full cycle ربع→مثقال→ربع pays **4 legs = 0.98⁴ = 0.9224**, so every round trip
starts **7.8% in the hole.**

---

## PART 1 — Best A/B at 2% cost

### The hard constraint you correctly anticipated

```
Break-even:  (1 + A) / (1 + B)  >  1.0842
```

| B (buy) | A must exceed | minimum gap |
|---|---|---|
| 15% | 24.7% | **9.7pp** |
| 20% | 30.1% | **10.1pp** |
| 25% | 35.5% | **10.5pp** |
| 30% | 40.9% | **10.9pp** |

**You need a ~10pp minimum gap just to break even.** This is exactly the tension
you identified — and it resolves *against* frequent trading. See §1.3.

### 1.1 The grid at 2%/leg

Wealth in quarter coins, start = 1 coin. **Benchmark = 1.000.**

| A\B | 15% | 18% | 20% | 22% | 25% | 28% | 30% | 32% |
|---|---|---|---|---|---|---|---|---|
| 40% | 1.282 | 1.267 | 1.267 | 1.347 | 1.237 | 1.158 | 1.142 | 1.108 |
| 45% | 1.282 | 1.267 | 1.267 | 1.199 | 1.173 | 1.144 | 1.184 | 1.184 |
| 50% | 1.282 | 1.267 | 1.267 | 1.199 | 1.173 | 1.144 | 1.212 | 1.212 |
| 55% | 1.282 | 1.267 | 1.267 | 1.199 | 1.173 | 1.144 | 1.255 | 1.255 |
| **60%** | 1.319 | 1.303 | 1.303 | 1.233 | 1.206 | 1.177 | **1.457** | **1.457** |
| 65% | 1.425 | 1.408 | 1.408 | 1.333 | 1.303 | 1.272 | 1.259 | 1.259 |
| 70% | 1.425 | 1.408 | 1.408 | 1.333 | 1.303 | 1.272 | 1.259 | 1.259 |

**All 56 cells still beat holding the coin**, even at 2%. Worst = 1.108 (+11%).

### 1.2 🔴 More trades actively destroys value

I searched all 1,360 (A,B) combinations and grouped by trade count:

| trades | best result | A | B | gap |
|---|---|---|---|---|
| 1 | 1.390 | 63% | 10% | 53pp |
| 2 | 1.425 | 63% | 14% | 49pp |
| **4** | **1.457** | **59%** | **30%** | **29pp** |
| 6 | 1.167 | 41% | 30% | 11pp |
| 8 | 1.103 | 38% | 30% | 8pp |

**This directly answers your concern.** You wanted more trades to convert more
bubble into gold. But at 2%/leg the relationship **inverts above 4 trades**:
going from 4 → 8 trades cuts your result from 1.457 to 1.103. The extra
round trips are narrow-gap trades that barely clear the 7.8% hurdle, and the
friction eats the rest.

**4 trades is the optimum — not a compromise, an actual peak.**

### 1.3 Recommended: A = 60%, B = 31%

Ranked by *worst neighbour* (robustness, not peak):

| A | B | self | worst neighbour |
|---|---|---|---|
| **60%** | **31%** | **1.457** | **1.274** |
| 68% | 26% | 1.294 | 1.272 |
| 62% | 31% | 1.457 | 1.259 |

The A∈[58,62], B∈[30,32] block is a genuine plateau at 1.27–1.46.

```
A = 60%   (sell ربع → buy مثقال)
B = 31%   (sell مثقال → buy ربع)
gap = 29pp — nearly 3× the 10.1pp break-even
```

Result: **1.4570 coins** = 2.664 g fine gold, from 1.8288 g start → **+45.7%**

Trades:
```
2024-11-01  SELL ربع @ 62.8%
2025-02-11  BUY  ربع @ 29.8%
2025-03-17  SELL ربع @ 76.0%
2025-09-13  BUY  ربع @ 28.9%
```

Cost ladder (note how flat it is — the wide gap absorbs friction):

| cost/leg | 0% | 1% | 1.5% | **2%** | 2.5% | 3% |
|---|---|---|---|---|---|---|
| coins | 1.713 | 1.580 | 1.518 | **1.457** | 1.399 | 1.342 |

**Even at 3%/leg you keep +34%.** Note B moved up from 20% → 31% versus the
0.75% case: higher costs push you to trade *sooner* on the buy side, because
waiting for a deeper discount that may not arrive costs more than it saves.

---

## PART 2 — USD vs Mesghal momentum

Fetched **441 sessions of USD/IRR** (`data/usd_irr.csv`), aligned to 375 sessions
with the gold data. Removed 3 corrupted Nowruz-window rows (13% single-day
"moves" that were tgju artifacts).

### 2.1 The core series

```
R = Mesghal_rial / USD_rial   = price of a mesghal in dollars

R rising  → gold outrunning USD → hold GOLD
R falling → USD outrunning gold → hold USD
```

Over the period: USD **+133%**, mesghal **+256%** → R **+53%**.

### 2.2 🔴 The finding that kills the naive version

Relative momentum (gold return − USD return):

| horizon | mean | median | **gold wins** |
|---|---|---|---|
| 10d | +1.2pp | +1.3pp | **63%** |
| 20d | +2.7pp | +2.7pp | **68%** |
| 30d | +4.1pp | +4.2pp | **73%** |
| 60d | +9.3pp | +10.3pp | **80%** |

**Gold beats USD 63–80% of the time, and the edge grows with horizon.** This is
not a symmetric two-sided market. A symmetric crossover rule flips into USD
constantly and pays 4% round-trip to sit in the losing asset.

SMA crossover results (2%/leg), benchmark hold-mesghal = 1.0000:

| fast\slow | 20 | 30 | 50 | 80 | 120 |
|---|---|---|---|---|---|
| 5 | 0.357 | 0.414 | 0.858 | **1.079** | 1.046 |
| 10 | 0.489 | 0.618 | 0.836 | 1.053 | 0.998 |
| 15 | 0.373 | 0.638 | 0.955 | 1.059 | 1.033 |

Only the slowest settings survive, and the best (1.079) fires **once**.

### 2.3 The USD-winning episodes are too short to trade

Using 20-day relative momentum:

- **30 USD-winning episodes** in 375 sessions
- lengths: min 1, **median 2**, max 20 sessions
- only **2 episodes lasted ≥15 sessions**

The two big ones:

| period | length | gold | USD | USD edge |
|---|---|---|---|---|
| 2025-05-13 → 2025-06-01 | 17d | +2.3% | −1.7% | **−4.0pp** |
| 2026-05-05 → 2026-05-31 | 20d | −5.4% | −6.0% | **−0.6pp** |

**Even the best USD windows produced only a 4.0pp and 0.6pp edge — against a
7.8% round-trip cost.** The episodes are real but they are too short and too
shallow to pay for the switch.

### 2.4 Asymmetric threshold — best possible attempt

Only rotate to USD on *strong* USD momentum, requiring a big trigger:

| k | switch-out | wealth | trades |
|---|---|---|---|
| 30 | ≤ −8pp | **0.9857** | 2 |
| 20 | ≤ −10pp | 0.7881 | 4 |
| 10 | ≤ −10pp | 0.7113 | 6 |
| 20 | ≤ −3pp | 0.2309 | 23 |

**Best achievable: 0.9857 — still below 1.0000 for simply holding gold.**

### 2.5 Verdict on Phase 2

**Do not add the USD leg at 2% cost.** On this data it cannot pay for itself:

1. Gold structurally beats USD (68% of 20-day windows) — the rial devalues
   against gold faster than against the dollar, because domestic gold carries
   both the FX move *and* the world gold move.
2. USD-winning episodes have a **median length of 2 sessions**.
3. The best two episodes offered 4.0pp and 0.6pp — under a 7.8% hurdle.

This matches the earlier `AUDIT` finding: your original workbook's Delta signal
never once said "USD" in 365 sessions. Now we know that wasn't only a units bug —
**it was also directionally correct.**

**One caveat:** this sample is a period of extreme domestic gold strength (+256%)
under war conditions. In a classic rial-devaluation shock with flat world gold,
USD *can* lead. The tool to detect it is built and in the repo — but it should
stay switched off until a regime appears where USD momentum persists for 30+
sessions.

---

## Combined recommendation

```
PRIMARY (active):
  A = 60%  →  sell ربع سکه, buy مثقال
  B = 31%  →  sell مثقال, buy ربع سکه
  RP = (P_ربع / 1.8288) / (P_مثقال / 3.2489) − 1
  Expect ~4 trades per 18 months. Do NOT force more.

SECONDARY (built, disabled):
  Track R = P_مثقال / P_USD and 30-day relative momentum.
  Activate USD rotation ONLY if rel-momentum < −8pp persists 30+ sessions.
  Currently: gold favoured.
```

**Current reading (2026-07-27): RP = 21.6%** — below B=31%, so the model says
hold ربع سکه. 30-day gold-vs-USD momentum favours gold.

Data files: `data/qm_full.csv` (430 sessions), `data/usd_irr.csv` (441 sessions).
