# ربع سکه ↔ مثقال Bubble Arbitrage — Analysis

Scope narrowed per your instruction: **only ربع سکه and مثقال آب‌شده.** No Imami,
no USD, no XAU.

---

## 1. The simplification you just unlocked

Dropping USD and Imami removes the two hardest inputs. Here is why.

The conventional bubble needs a global anchor:

```
IV_quarter = 1.8288 g × (XAU_USD / 31.1035) × USD_IRR
Bubble      = P_quarter / IV_quarter − 1
```

That formula needs `XAU_USD` and `USD_IRR` — the two noisiest, least reliable
series in the whole system, and the ones that fight each other during a conflict
shock.

But for a **quarter↔mesghal** trade you never need the absolute bubble. You only
need the **relative** one:

```
gram_price_quarter = P_quarter / 1.8288      (rial per fine gram)
gram_price_mesghal = P_mesghal / 3.24885     (rial per fine gram)

RP = gram_price_quarter / gram_price_mesghal − 1     ← "relative premium"
```

**`XAU` and `USD` cancel out completely.** Both instruments are priced off the
same domestic gold market, so the common factor divides away. `RP` needs only two
numbers you can read off any dealer's board.

### And the P&L identity is exact

I verified this numerically. If you buy quarter when `RP = p₁` and sell back to
mesghal when `RP = p₂`, your holding in **fine grams** changes by exactly:

```
gram_gain = (1 + p₂) / (1 + p₁) × (1 − c)⁴
```

(four cost legs: sell mesghal, buy quarter, sell quarter, buy mesghal).

This is the whole strategy in one line. It says something important: **your
profit depends only on the two premium levels, not on the gold price at all.**
Gold can triple or halve in between; irrelevant. That is exactly the
"grams-of-gold" objective you wanted.

**The cost hurdle is therefore explicit.** At 0.75%/leg you need
`(1+p₂)/(1+p₁) > 1.0306`, i.e. **a ~3.1% relative move minimum**. Buying at
RP=25% means you must sell above **RP=28.8%** just to break even.

---

## 2. What the history actually shows

365 sessions, 2024-10-30 → 2026-02-19, from your archive (corrected constants:
ربع = 2.032 g × 0.900 = 1.8288 g; مثقال = 4.6083 × 0.705 = 3.24885 g).

### The range you asked for

| percentile | RP |
|---|---|
| min | 15.3% |
| p5 | 22.1% |
| p10 | 26.2% |
| p25 | 31.5% |
| **p50** | **39.1%** |
| p75 | 49.5% |
| p90 | 56.6% |
| p95 | 62.8% |
| max | 76.0% |

So the naive reading is: **buy below ~26%, sell above ~57%.** A 15%→76% range on
a quantity where you only need 3% to cover costs. That looks like an enormous
opportunity.

### The signal genuinely predicts

I checked forward outcomes conditional on the entry level, and **your thesis is
correct**:

| entry condition | 20d later | 40d later | 60d later |
|---|---|---|---|
| buy when RP ≤ 30% | **+4.7pp** (76% win) | **+4.5pp** (84% win) | +1.7pp (50% win) |
| sell when RP ≥ 50% | **−5.9pp** | **−12.0pp** | **−17.0pp** |
| sell when RP ≥ 55% | **−7.7pp** | **−13.6pp** | **−18.8pp** |

Low premium → premium rises. High premium → premium falls, hard. Mean reversion
is real. AR(1) β = 0.982, **half-life ≈ 38 sessions** (~7–8 weeks).

**Your intuition about the mechanism is right.** Now the problem.

---

## 3. 🔴 Why it still loses money — and it does

Full backtest, NAV in fine grams, start = 1.0 g, cost 0.75%/leg:

| Strategy | Final (g) | Trades |
|---|---|---|
| **Hold مثقال (the benchmark)** | **1.0000** | 0 |
| Fixed buy<30% / sell>50% | 1.0024 | 3 |
| Fixed buy<25% / sell>50% | 0.9216 | 1 |
| Fixed buy<20% / sell>45% | 0.9955 | 1 |
| Rolling quantile, 120d, q[0.20,0.80] | 0.8793 | 5 |
| Rolling quantile, 90d, q[0.25,0.75] | 0.7998 | 5 |
| Rolling quantile, 60d, q[0.20,0.80] | 0.7248 | 5 |
| z-score vs rolling median, 120d, ±1.0 | 0.8852 | 5 |
| **Hold ربع سکه** | **0.7359** | 0 |

**Every configuration except one loses to doing nothing.** And the one that
"wins" (+0.24%) made **3 trades in 16 months** — that is not a strategy, it is
noise.

### The cause: RP is not stationary, it is collapsing

```
2024-11  50.8%     2025-04  61.8%     2025-10  27.1%
2024-12  46.5%     2025-05  57.0%     2025-11  28.5%
2025-01  36.1%     2025-06  49.3%     2025-12  32.2%
2025-02  33.6%     2025-07  44.0%     2026-01  30.1%
2025-03  53.1%     2025-08  40.7%     2026-02  18.2%
```

First-half mean **48.5%** → second-half mean **32.3%**. Start 58.3% → end 16.5%,
a **−41.8pp** structural decline.

This is the CBI auction programme and the annual re-minting destroying the ربع
scarcity premium (documented in `RESEARCH.md` §2). **It is a policy-driven
one-way repricing, not a cycle.**

The consequence is brutal and specific:

> **What looks "cheap" on the historical range keeps getting cheaper.**
> A buy signal at RP=25% was in the bottom 10% of the 2024–25 distribution.
> By Feb 2026 RP was 16.5% — the "cheap" level became the new normal, then
> kept falling.

And the exit never fires. Trace the buy<30/sell>50 run:

```
2025-02-11  BUY  Q @ 29.8%
2025-03-11  SELL Q @ 50.6%     ← +16% in grams, the trade works
2025-09-13  BUY  Q @ 28.9%
            ...never sells. RP ends at 16.5%.
```

The strategy **ends stuck holding quarter through the entire collapse.** One good
round trip, then a permanent bag. That is the whole story of the backtest.

### The adaptive bands fail *worse*, and the reason matters

Rolling-quantile bands (0.72–0.89 g) underperform fixed bands. This is
counter-intuitive but logical: in a downtrend, a rolling window keeps
**re-labelling ever-lower premiums as "normal,"** so it issues buy signals all the
way down. Adaptivity accelerates the bleed. I recommended rolling quantiles in
the audit — **on this data that recommendation is wrong**, and the reason is the
structural break.

---

## 4. What would have to be true for this to work

The trade is sound *conditional on RP being range-bound*. So the real question is
not "what bands?" but **"is the decline over?"**

Three regimes and what each implies:

| Regime | RP behaviour | Correct action |
|---|---|---|
| **Range-bound** (pre-2024) | oscillates around a stable mean | your strategy works; trade the range |
| **Structural decline** (2024→2026) | new lows keep printing | **do nothing** — hold مثقال, quarter bleeds |
| **Floor reached** | RP stabilises at a new, lower mean | re-estimate the range, resume trading |

There *is* a floor in principle: ربع سکه cannot trade below its melt value plus
minting cost, so RP has a hard lower bound near 0% and a practical one somewhat
above. At 16.5% and falling, we are far closer to that floor than to the old 40%
mean — but "closer" is not "there."

**The honest position: we cannot tell from 365 sessions.** This sample contains
exactly one regime — the collapse. Fitting bands to it is fitting a trend as if
it were a cycle.

---

## 5. What I recommend, concretely

### 5.1 Get the long history first — it is free and it decides everything

`RESEARCH.md` §4 verified the tgju endpoints work and are deep:

```
https://api.tgju.org/v1/market/indicator/summary-table-data/rob       → 3,374 rows
https://api.tgju.org/v1/market/indicator/summary-table-data/mesghal   → 3,467 rows
```

**~13 years of daily OHLC on both legs.** That is the single most valuable thing
available, and it directly answers the only question that matters:

- What did RP do in **2013–2023**? Was it range-bound, and around what mean?
- How did it behave in previous CBI intervention episodes (there were coin
  pre-sales in 2018 and earlier auction programmes)?
- Is 15–20% a historically normal floor, or genuinely unprecedented?

Until that is answered, any band you pick is a guess dressed as analysis.

### 5.2 Add a trend filter — do not trade the range in a downtrend

The single change that would have saved this backtest:

```
Only take a BUY signal if RP is not making new lows.
e.g.  require  RP_today > min(RP over trailing 60 sessions)
      or       RP's 20d slope ≥ 0
```

This keeps you out of the entire 2025-09 → 2026-02 collapse. It costs you a bit
of upside at true bottoms and saves you from the bag.

### 5.3 Always define the exit before entry

The failure mode was a missing exit. Every position needs three:

- **Target:** RP reaches the sell band
- **Time stop:** ~2 half-lives ≈ 75 sessions, then reassess regardless
- **Structural stop:** if RP breaks below entry by >8pp, the regime assumption
  was wrong — exit, do not average down

I tested TP/SL/time-stop variants (§ backtest): they cap the damage (0.85–1.02 g)
but still do not beat holding مثقال on this sample. They are damage control, not
alpha.

### 5.4 Respect the cost hurdle explicitly

`gram_gain = (1+p₂)/(1+p₁) × (1−c)⁴`. Print this before every trade. At 0.75%/leg
the minimum viable round trip is a **3.1% relative move**; at 1.5%/leg it is
**6.2%**. Narrow bands are mathematically incapable of paying.

### 5.5 Mint-year discipline is non-negotiable here

`RESEARCH.md` §2 found ربع سکه ۱۳۸۶ / ۱۴۰۳ / ۱۴۰۴ trade as separate lines, up to
1m toman apart. On a quantity where 3% is your hurdle, a mint-year mismatch
between your dealer quote and your reference series is larger than your entire
edge. **Record mint year on every quote.**

---

## 6. Bottom line

Your framework is **analytically correct** — I verified the P&L identity, and the
mean-reversion signal genuinely predicts in the right direction with good hit
rates.

But on the only data we have, **it loses to holding مثقال**, because 2024–2026 was
not a range — it was a one-way, policy-driven collapse in the quarter-coin
premium, and a range-trading system in a downtrend just buys all the way down.

The next step is not a better band. It is **the 13-year history**, to find out
whether the range you want to trade actually exists outside this window.

Say the word and I'll pull both full series and re-run everything on ~3,400
sessions across multiple regimes.
