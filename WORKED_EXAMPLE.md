# How RP and vol45 are calculated — a fully worked example

Using a **real trade day from the backtest: 2025-09-13**, when the model
switched مثقال → ربع سکه (trade #3).

Board prices that day (tgju close):

```
ربع سکه   P_q = 266,000,000 rial
مثقال     P_m = 366,470,000 rial
```

---

## Part 1 — RP (the relative premium)

### The constants

You are not comparing prices. You are comparing **the cost of one gram of
pure gold** bought two different ways.

| instrument | gross weight | purity (عیار) | fine gold |
|---|---|---|---|
| ربع سکه | 2.032 g | 0.900 | **1.8288 g** |
| مثقال آب‌شده | 4.6083 g | 0.705 | **3.24885 g** |

### Step 1 — convert both to rial per gram of fine gold

```
quarter:  266,000,000 / 1.8288  = 145,450,569 rial per gram
mesghal:  366,470,000 / 3.24885 = 112,799,862 rial per gram
```

### Step 2 — take the ratio, subtract 1

```
RP = 145,450,569 / 112,799,862 − 1
   = 1.2895 − 1
   = 0.2895  →  28.9%
```

**Interpretation:** a gram of gold *inside the coin* costs **28.9% more** than
the identical gram as melted gold. You are paying a 28.9% premium for the
coin's form.

Since 28.9% ≤ 31%, the coin is historically cheap → **buy the coin**.

### The whole formula

```
RP = (P_quarter / 1.8288) / (P_mesghal / 3.24885) − 1
```

### Why RP is robust: XAU and USD cancel out

Suppose you instead measured each instrument's bubble against the world gold
price. Using USD = 992,000 rial that day:

| assumed world spot | quarter bubble | mesghal bubble | (1+Bq)/(1+Bm) − 1 |
|---|---|---|---|
| $3,300/oz | +38.2% | +7.2% | **0.2895** |
| $4,500/oz | +1.3% | −21.4% | **0.2895** |

The individual bubbles swing wildly with the assumed spot price — but their
**ratio is identical**, and exactly equals RP.

The reason is algebraic. Let `g` = rial per gram of pure gold from the world
market (`spot / 31.1035 × USD`). Then:

```
1 + B_q = (P_q / 1.8288) / g
1 + B_m = (P_m / 3.24885) / g

(1 + B_q)     (P_q / 1.8288) / g     (P_q / 1.8288)
─────────  =  ──────────────────  =  ──────────────     ← g cancels
(1 + B_m)     (P_m / 3.24885) / g    (P_m / 3.24885)
```

**Practical consequence:** you need only **two numbers off the dealer board.**
No world gold price, no dollar rate, no exchange feed. RP is unaffected by
what XAU or the rial are doing — it measures the coin's bubble and nothing else.

---

## Part 2 — vol45 (the volatility regime)

### Step 1 — take the last 46 مثقال closes

Sessions 2025-07-16 through 2025-09-13. 46 prices → **45 daily returns**.

### Step 2 — convert to daily returns

```
r = today's close / yesterday's close − 1
```

First few:

```
2025-07-16 → 07-18 : 302,520,000 / 306,690,000 − 1 = −1.36%
2025-07-18 → 07-19 : 300,730,000 / 302,520,000 − 1 = −0.59%
2025-07-19 → 07-20 : 306,770,000 / 300,730,000 − 1 = +2.01%
2025-07-20 → 07-21 : 311,040,000 / 306,770,000 − 1 = +1.39%
... 45 returns in total
```

### Step 3 — standard deviation of those 45 returns

```
mean     = +0.409%
variance = Σ(r − mean)² / 45 = 0.00025321
vol45    = √0.00025321 = 0.01591  →  1.59%
```

> Note: this is the **population** standard deviation (divide by 45, not 44).

Over that window: biggest up day **+4.14%**, biggest down day **−2.92%**.

### What it means

vol45 = 1.59% says: *on a typical day over the last ~2 months, مثقال moved
about 1.6%.* It deliberately ignores **direction** — a 45-day stretch that
rose steadily and one that crashed steadily can have the same vol45. It
measures only how violent the market is.

Roughly: 1.59% daily ≈ 25% annualised (× √252).

---

## Part 3 — the decision on that day

```
vol45 = 1.59%   → below 3.3%, so Layer 1 says STAY IN GOLD
RP    = 28.9%   → at or below 31%, so Layer 2 says HOLD ربع سکه

Position was مثقال  →  ACTION: switch to ربع سکه
```

That is trade #3 in the backtest.

---

## Part 4 — what the round trip actually earns

Say you hold مثقال containing **100.00 g** of fine gold.

**Leg 1 — buy the coin at RP = 28.9%**

```
sell مثقال  −2%
buy ربع     −2%
→ 100.00 × 0.98 × 0.98 = 96.04 g now held as coins
```

**Leg 2 — later the bubble fattens to RP = 60%. Reverse the trade.**

```
gold multiplies by (1 + 0.60) / (1 + 0.2895) = 1.2408
sell ربع    −2%
buy مثقال   −2%
→ 96.04 × 1.2408 × 0.98 × 0.98 = 114.45 g
```

**Result: 100.00 g → 114.45 g = +14.5% more gold.**

### The general formula

```
gram_gain = (1 + RP_sell) / (1 + RP_buy) × (1 − cost)⁴
```

Four cost legs because a full cycle is four transactions.

**The critical point:** this profit does **not** depend on the gold price. Gold
could have risen 50% or fallen 30% in between — you still end with 14.5% more
metal, because you sold a form of gold that was expensive and bought it back
when it was cheap.

That is the entire strategy in one equation.

---

## Reproduce it yourself

```python
QUARTER_G = 2.032  * 0.900   # 1.8288
MESGHAL_G = 4.6083 * 0.705   # 3.24885

def relative_premium(quarter, mesghal):
    return (quarter / QUARTER_G) / (mesghal / MESGHAL_G) - 1

def vol45(mesghal_closes, window=45):
    s = mesghal_closes[-(window + 1):]
    rets = [s[i] / s[i-1] - 1 for i in range(1, len(s))]
    mean = sum(rets) / len(rets)
    return (sum((r - mean) ** 2 for r in rets) / len(rets)) ** 0.5
```

Both are in `bot/strategy.py`; the numbers above were verified against it.
