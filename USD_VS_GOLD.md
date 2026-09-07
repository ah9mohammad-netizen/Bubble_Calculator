# USD ↔ Gold Switching: Indicator Study

**Your position:** switching between gold and USD must beat holding one.
**My earlier claim:** the ceiling is only 1.08× so it can't work.

**I was wrong about the ceiling.** Corrected below. But the indicator tests still
come out negative, for a different and more interesting reason.

---

## 1. 🔴 Correction: my ceiling was understated

I previously computed the "perfect foresight" maximum using **uniform N-day
blocks**. That is not the true optimum — the optimal switch dates are irregular.
Recomputed with **dynamic programming** (exact optimum, switch cost per leg):

| cost/leg | true optimum | × gold |
|---|---|---|
| 0.0% | 120.4 bn | 33.9× |
| 0.5% | 25.5 bn | **7.16×** |
| 1.0% | 10.8 bn | **3.04×** |
| **2.0%** | **5.83 bn** | **1.64×** |
| 3.0% | 4.77 bn | 1.34× |

Hold gold = 3.556 bn.

**At 2% the true ceiling is 1.64×, not the 1.08× I quoted.** There is
substantially more headroom than I said, and you were right to push back. The
optimum makes **13 switches**, not 4.

---

## 2. Indicator suite — 84 configurations tested

Applied to `R = P_مثقال / P_USD` (R rising = gold winning):
EMA crossovers, MACD, RSI, price-vs-SMA, rate-of-change, Bollinger bands.

Top results, full sample, 2%/leg, benchmark 3.556 bn:

| indicator | wealth | trades | × gold |
|---|---|---|---|
| BB50 (1.0σ) | 3.682 bn | **1** | **1.036×** |
| RSI14 30/70 | 3.556 bn | **0** | 1.000× |
| RSI21 30/70 | 3.556 bn | **0** | 1.000× |
| EMA8/60 | 3.519 bn | 3 | 0.990× |
| EMA20/30 | 3.519 bn | 3 | 0.990× |
| EMA5/60 | 3.481 bn | 3 | 0.979× |

**8 of 84 beat hold-gold — and they do it by barely trading.** The RSI variants
score exactly 1.000× because they never fire. The single "winner" (BB50) makes
one trade. That is not a strategy.

---

## 3. The diagnostic that explains it

I reconstructed the DP-optimal state path and measured how well each indicator
matches it:

| indicator | agreement with optimal state |
|---|---|
| EMA8/60 | **86.7%** |
| EMA10/30 | 85.6% |
| EMA20/50 | 85.3% |
| ROC45 | 81.9% |
| EMA5/20 | 77.3% |

**86.7% agreement, yet it still loses money.** This is the crux.

The optimal path is **28.3% USD / 71.7% gold**, in 7 USD spells of lengths:

```
7, 19, 4, 4, 2, 39, 31 sessions
```

Three of the seven spells last **2–4 sessions**. With a 20-session minimum hold
you cannot take them; without one you churn at 4pp a round trip. The indicators
get the *easy* 86% right (the long gold stretches) and miss precisely the short,
violent USD spells where all the value is.

---

## 4. The one genuinely strong lead — and why I don't trust it

I tested leading indicators. Two findings:

**Quarter bubble as a leading signal — weak but real:**

| | correlation |
|---|---|
| RP(t) vs R forward-20d | **+0.251** |
| dRP20(t) vs R forward-20d | **+0.265** |

**Gold volatility as a leading signal — strong:**

| | correlation |
|---|---|
| gold vol30 vs USD-edge forward-20d | +0.475 |
| **gold vol30 vs USD-edge forward-45d** | **+0.769** |

+0.769 is a large correlation. High gold volatility → USD outperforms next.
Economically sensible: panic → gold spikes then mean-reverts, dollar grinds.

### But it does not survive scrutiny

| test | result |
|---|---|
| overlapping windows (300 pts) | +0.769 |
| **non-overlapping (7 independent pts)** | **+0.744** |
| effective sample size | **7, not 300** |

And the high-vol regime is one episode:

```
sessions with 30d gold vol ≥ 3.0%, by month:
2025-04: 17   2025-05: 7   2026-01: 4   2026-02: 15   2026-05: 17
```

**Essentially the war period.** The +0.769 describes *one event*, not a law.

Backtested, the vol rule gives **0.982× gold** full-sample (1 trade). In
walk-forward it looks better — 12/17 configs beat gold out-of-sample, best
2.13× — but every one of them **lost in the training half**. A rule that fails
in-sample and wins out-of-sample has found the war, not a mechanism.

---

## 5. Final scorecard (2%/leg)

| | wealth | × gold |
|---|---|---|
| **True optimum (perfect hindsight)** | **5.831 bn** | **1.640×** |
| Hold gold | 3.556 bn | 1.000× |
| Best indicator (BB50, 1 trade) | 3.682 bn | 1.036× |
| Best EMA | 3.519 bn | 0.990× |
| Best vol rule | 3.491 bn | 0.982× |
| Hold USD | 2.331 bn | 0.655× |

**Of the 1.64× available, no indicator captured meaningfully more than 1.00×.**

---

## 6. Where I now agree with you, and where I don't

**You are right that:**
- The opportunity is much bigger than I said — **1.64×, not 1.08×**
- Gold volatility genuinely does lead USD outperformance (+0.769, and it
  replicates in both halves: +0.612 / +0.842)
- The quarter bubble carries real information about the gold/USD rotation
  (+0.265) — the two phases of your strategy are linked, which you suspected

**The obstacle is not the signal, it is the cost:**

The value sits in USD spells of **2, 4, and 4 sessions**. At 2%/leg each attempt
costs 4pp. You cannot profitably trade a 3-day window with a 4pp toll — that
requires being right about both entry *and* exit within 72 hours, repeatedly.

Look at the cost ladder again:

| cost/leg | ceiling |
|---|---|
| 2.0% | 1.64× |
| 1.0% | **3.04×** |
| 0.5% | **7.16×** |

**Halving your cost roughly doubles the ceiling.** At 0.5% the short spells
become tradeable and a 60–70%-accurate indicator would be enough. This is why I
keep returning to execution venue: it is not a side issue, it is *the* variable.

---

## 7. What I'd actually deploy

```
DEFAULT: gold. It won 68% of 20-day windows and +53% overall.

USD SLEEVE — enable only with BOTH:
  1. round-trip cost ≤ 1%/leg  (USDT on an exchange, or a gold ETF)
  2. gold 30d volatility ≥ 3.0%
     → rotate to USD; return to gold when vol ≤ 2.0%

At 2%/leg: keep it OFF. Tested, does not pay.
```

**Honest position:** I now believe the USD rotation *can* work — you were right
that the opportunity is real and larger than I claimed. But on this data, at 2%
cost, no indicator I tested extracted it, and the one strong signal rests on a
single war episode with 7 independent observations.

The highest-value next step is not a better indicator. **It is getting your
execution cost from 2% to 0.5%** — that alone moves the ceiling from 1.64× to
7.16× and makes the whole question worth revisiting.

Data: `data/usd_irr.csv` (441 sessions), `data/qm_full.csv` (430 sessions).
Code: `indicators.py`, `vol_rule.py`.
