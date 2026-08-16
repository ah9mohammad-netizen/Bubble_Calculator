# Iran Gold/FX Bubble Arbitrage — Strategy Presentation

**Backtest window:** 2023-09-20 → 2026-07-27 · 704 trading sessions (~2.8 years)
**Starting capital:** 1,000,000,000 rial (1 bn), held as cash on day 1
**Transaction cost:** 2.0% per leg (conservative — traditional dealer spread)

---

## 1. The idea in one paragraph

In Iran you cannot measure profit in rials — the rial loses value faster than
most assets gain it. **Profit means ending up with more grams of gold.**

The ربع سکه (quarter coin) does not trade at its metal value. It carries a
*bubble* — a premium over the gold actually inside it — and that premium
swings violently, from under 20% to over 75%. مثقال آب‌شده (melted gold) has
almost no bubble; it is close to pure metal.

So: **sell the coin when its bubble is fat, buy it back when the bubble is
thin.** Each completed round trip leaves you holding more gold than you
started with, regardless of what the gold price itself did.

On top of that sits a second question — is it even a good time to hold gold
at all, or should you be in dollars? That is Layer 1.

---

## 2. The two signals

Everything is computed from **two numbers off the dealer board**.

### RP — the relative premium (Layer 2)

```
RP = (price of ربع / 1.8288 g) / (price of مثقال / 3.24885 g) − 1
```

The premium the coin charges *per gram of fine gold* versus melted gold.

> **Why this is robust:** world gold price and the USD rate cancel out of this
> formula algebraically. RP is immune to what XAU or the dollar are doing —
> it measures only the coin's bubble.

### vol45 — the volatility regime (Layer 1)

```
vol45 = standard deviation of daily مثقال returns, trailing 45 sessions
```

Measures *how violently* the market is moving, ignoring direction.

---

## 3. The decision rules

```
LAYER 1 — should I be in gold at all?
    holding gold :  vol45 ≥ 3.3%  →  sell everything, go to USD
    holding USD  :  vol45 ≤ 2.0%  →  come back to gold
    in between   :  do nothing

LAYER 2 — which gold? (only runs while in gold)
    RP ≤ 31%  →  hold ربع سکه   (coin is cheap)
    RP ≥ 60%  →  hold مثقال     (coin's bubble is fat)
    in between →  keep what you have

MINIMUM HOLD: 10 sessions between Layer 1 flips, 5 between Layer 2 flips
```

The two different Layer 1 thresholds (3.3% out, 2.0% back) are deliberate —
that gap stops the strategy flip-flopping when volatility hovers near a
single line.

### Why volatility predicts gold vs USD

674 observations, measuring the **next 30 days** of gold return minus USD return:

| vol45 | n | gold − USD over next 30d | gold wins |
|---|---|---|---|
| 1.0–1.5% | 151 | +5.0pp | 75% |
| **1.5–2.0%** | 212 | **+6.6pp** | **90%** |
| 2.0–2.5% | 116 | +4.7pp | 81% |
| 2.5–3.0% | 57 | +2.6pp | 68% |
| 3.0–3.5% | 58 | −2.0pp | 36% |
| 3.5–4.0% | 18 | **−12.8pp** | **0%** |

correlation = **−0.317**. When domestic gold goes wild, it has usually run
ahead of the dollar on panic — and it gives that excess back.

---

## 4. Results — five ways to hold 1 billion rial

![growth](charts/growth.png)

| Plan | Final value | Return | vs inflation | Gold owned | Trades |
|---|---|---|---|---|---|
| Hold USD | 3.70 bn | +269.8% | 1.10× | 15.2 g | 0 |
| Hold ربع سکه | 5.32 bn | +432.4% | 1.59× | 21.9 g | 0 |
| Hold مثقال | 7.68 bn | +667.6% | 2.29× | 31.6 g | 0 |
| Switch ربع↔مثقال | 8.70 bn | +769.7% | 2.59× | 35.8 g | 3 |
| **Two-layer strategy** | **9.45 bn** | **+844.7%** | **2.82×** | **38.9 g** | **4** |

Iran CPI over the same window rose **236%** (3.36×). That is the dotted line
on the chart — the true break-even.

### The headline

![summary](charts/summary.png)

**Holding USD returned +270% in rials and still lost more than half your
gold** — 32.3 g at the start, 15.2 g at the end. It barely beat inflation
(1.10×). This is the single most important slide: in Iran, a number that looks
like a profit can be a large real loss.

![grams](charts/grams.png)

Measured in gold, only three plans finished above where they started.
The two-layer strategy turned **32.3 g into 38.9 g — a 21% gain in metal**,
on top of riding the gold price itself.

---

## 5. How often does it trade?

**4 trades in 2.8 years — roughly one every 8 months.**

| # | Date | Move | Trigger |
|---|---|---|---|
| 1 | 2025-02-11 | مثقال → ربع | RP fell to 29.8% (coin cheap) |
| 2 | 2025-03-17 | ربع → مثقال | RP spiked to 76.0% (bubble fat) |
| 3 | 2025-09-13 | مثقال → ربع | RP back to 28.9% |
| 4 | 2026-02-02 | ربع → USD | vol45 hit 3.36% (risk-off) |

This is a **patient** strategy. It is not day trading. Long stretches — 121
sessions, 116 sessions — pass with no action at all. That matters at 2% cost:
we tested every possible threshold pair, and pushing the trade count to 6 or 8
*destroyed* value.

Current state: still in USD since 2026-02-02, waiting for vol45 to fall to
2.0%. At today's RP of 21.6% the next move would be **USD → ربع سکه**.

---

## 6. Is it robust, or curve-fitted?

| Test | Result |
|---|---|
| A/B threshold grid (36 combinations) | **36/36 beat holding the coin** |
| Volatility threshold grid (15 combinations) | **15/15 beat holding the coin** |
| First half alone (2023-09 → 2025-02) | 1.26× vs holding the coin |
| Second half alone (2025-02 → 2026-07) | 1.37× vs holding the coin |
| Worst drawdown | −24.9% (same as holding مثقال, better than the coin's −33.5%) |

The chosen parameters sit on a **flat plateau**, not a lone spike —
A = 0.60, 0.65, 0.70 and 0.75 all give identical results. That is the
signature of a real effect rather than a fitted one.

### Year by year

| Year | USD | ربع | مثقال | Switch | Two-layer |
|---|---|---|---|---|---|
| 2024 | +60.6% | +63.9% | +105.1% | +105.1% | +105.1% |
| 2025 | +71.9% | +174.9% | +171.3% | **+258.1%** | **+258.1%** |
| 2026 (part) | +37.9% | +11.5% | +28.2% | +11.5% | +21.1% |

---

## 7. What could go wrong — say this out loud

1. **Only 4 trades.** The entire edge rests on a handful of decisions.
   Doubling the data added exactly one trade.
2. **Layer 1 has fired in essentially one episode** (Feb 2026 and a May 2026
   re-entry), during the war. The 3.5–4.0% volatility bucket is 18
   observations from a single window. Layer 2 is far better evidenced.
3. **Screen prices ≠ your fill.** tgju's ربع index blends mint years
   ۱۳۸۶/۱۴۰۳/۱۴۰۴, which trade up to 1m toman apart. Real spreads may be worse
   than the 2% assumed.
4. **Costs dominate everything.** At 2%/leg the theoretical maximum from
   perfect foresight is 1.64×. At 0.5%/leg it becomes 7.16×. Finding cheaper
   execution (gold ETFs at 0.3–0.5%, online آب‌شده platforms at 1.5–2%) is
   worth more than any parameter tuning.
5. **Backtest ≠ future.** 2023–2026 contained a currency collapse and a war.
   A calm decade would produce far fewer signals.

---

## 8. Sources

- Prices: tgju.org daily **close** for `rob` (ربع سکه), `mesghal` (مثقال),
  `price_dollar_rl` (USD/IRR). 750 sessions where all three exist.
- Inflation: Statistical Center of Iran CPI releases. Verified anchors —
  Dec-2023 = 217.0, Jan-2024 = 222.7, Jan-2026 = 469.4 (p2p 60.0%),
  Feb-2026 = 513.6 (p2p 68.1%), Jul-2026 = 676.9 (p2p 87.9% urban).
  Months between anchors are geometrically interpolated.
  Cross-check: 469.4/222.7 = 2.108 vs (1.325)×(1.600) = 2.120 → consistent.
- Coin content: ربع سکه 2.032 g × 0.900 = 1.8288 g fine.
  مثقال 4.6083 g × 0.705 = 3.24885 g fine (عیار ۷۰۵).
