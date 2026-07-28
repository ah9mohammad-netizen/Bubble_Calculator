# Is USD↔Gold Switching Profitable in Rials?

**Your question:** I said the USD rotation doesn't work. But I measured in gold
units. In *rials*, isn't it profitable?

**Short answer: yes, both assets make huge rial profits — but switching between
them does not. And this time the reason is not the numeraire.**

---

## 1. In rials, everything looks profitable

Start 1,000,000,000 rial, 375 sessions (2025-01-04 → 2026-07-27):

| | end value | return |
|---|---|---|
| Hold rial cash | 1.000 bn | **+0%** (destroyed by inflation) |
| Hold USD | 2.331 bn | **+133%** |
| **Hold مثقال** | **3.556 bn** | **+256%** |

You are right that in rial terms both are big winners. Gold simply beat USD by
53 points. So the honest question is not "is USD profitable" — it is
**"does switching beat just holding the better one?"**

---

## 2. The opportunity is real and enormous

Perfect daily foresight (always in tomorrow's winner, no costs):

```
120.4 bn  =  +11,944%   →  33.9× more than holding gold
```

So the raw opportunity absolutely exists. **This was worth checking and I should
have shown it before.** The question is how much survives friction.

---

## 3. 🔴 The killer: even PERFECT foresight loses at 2%

Perfect foresight, restricted to switching only every N sessions:

| block | cost 0% | cost 1% | **cost 2%** | switches | verdict @2% |
|---|---|---|---|---|---|
| 1d | 120.44 bn | 1.57 bn | **0.02 bn** | 216 | loses |
| 5d | 8.13 bn | 3.86 bn | **1.82 bn** | 37 | loses |
| 10d | 6.57 bn | 3.98 bn | **2.39 bn** | 25 | loses |
| **20d** | 4.91 bn | 4.35 bn | **3.85 bn** | 6 | **beats gold** |
| **30d** | 4.51 bn | 4.16 bn | **3.83 bn** | 4 | **beats gold** |
| **60d** | 4.51 bn | 4.16 bn | **3.83 bn** | 4 | **beats gold** |
| 90d | 3.75 bn | 3.60 bn | **3.46 bn** | 2 | loses |

Hold gold = 3.556 bn.

**At its very best, a God-mode oracle beats holding gold by 1.08×.** That is the
theoretical ceiling. A real rule — one that cannot see the future — has to
capture 100% of a 8% edge while making zero mistakes. There is no margin.

Note also the collapse at 2% for frequent switching: daily perfect foresight
goes from 120 bn to **0.02 bn**. At 2%/leg, 216 switches cost you 98.5% of
capital even when every single call is correct.

---

## 4. Why a real rule cannot find the window

There *was* one genuinely big USD period:

```
2026-02-08 → 2026-07-11:   gold −6.9%,  USD +17.4%   → USD edge 24.4pp
```

That is a huge, tradeable window. So why doesn't a momentum rule catch it?

**Because at the ideal entry date, gold momentum was still strongly positive:**

| lookback at 2026-02-08 | rel momentum (gold − USD) |
|---|---|
| 30d | **+21.9pp** |
| 45d | **+18.8pp** |
| 60d | **+28.7pp** |

A "switch to USD when gold underperforms" rule needs a *negative* reading. It
only turned negative in mid-June — **four months late, near the end of the move.**

Watch the signal fight the outcome all the way through:

| date | trailing 45d | next 45d USD edge |
|---|---|---|
| 2026-02-08 | **+18.8pp** | **+18.1pp** |
| 2026-05-05 | −0.7pp | +3.5pp |
| 2026-06-14 | **−13.9pp** | +3.3pp |
| 2026-07-11 | −11.4pp | **−2.1pp** |

### The statistical verdict

```
Correlation( trailing 45d rel-momentum , forward 45d rel-momentum ) = −0.325
```

**Negative.** Gold-vs-USD relative performance **mean-reverts**; it does not
trend. Every trend-following crossover is therefore built on the wrong sign —
which is exactly why all 48 configurations I tested lost:

| best causal trend rule | result |
|---|---|
| k=45, out ≤ −6pp | 2.969 bn = **0.835× gold** |

---

## 5. So I tested the contrarian version too

If the correlation is −0.325, the fix should be to invert: buy USD when gold has
run *too far ahead*.

| best contrarian rule | result |
|---|---|
| k=30, out ≥ +25pp, in ≤ −5pp | 3.228 bn = **0.908× gold** |

**Better than trend-following (0.908 vs 0.835), but still below 1.0.** And it
fails the split-sample test:

| rule | 1st half | 2nd half |
|---|---|---|
| hold gold | 1.803× | 1.882× |
| k=30 out≥25 in≤−5 | 1.446× ❌ | 2.131× ✅ |
| k=45 out≥15 in≤0 | 1.201× ❌ | 1.606× ❌ |
| k=30 out≥20 in≤0 | 1.390× ❌ | 1.766× ❌ |

Only one config wins one half. That is noise, not signal.

---

## 6. The answer to your question

**Yes — holding USD is very profitable in rials (+133%).**
**No — switching between USD and gold is not, at 2% cost.**

Three independent reasons, none of which is about the numeraire:

1. **The ceiling is 1.08×.** Perfect foresight at the optimal frequency barely
   beats holding gold. There is no room for an imperfect rule.
2. **The correlation is −0.325.** Relative performance mean-reverts, so
   trend-following has the wrong sign — and the contrarian version doesn't
   survive a split-sample test either.
3. **2% is brutal on a 2-asset switch.** Each round trip costs 4pp. The average
   USD-winning 60-day window offers 9.9pp, but you cannot identify it in
   advance; the ones you *can* identify are already over.

### What would change this

- **Costs at 0.5%/leg.** The oracle table shows 13.8 bn at 0.5% vs 0.02 bn at 2%.
  If you can move USD↔gold at 0.5% (USDT on an exchange, or a gold ETF), the
  economics transform completely. **This is the single highest-value change
  available** — far more than any signal work.
- **A leading indicator instead of a lagging one.** Trailing momentum arrives 4
  months late. Something forward-looking — auction announcements, the
  USD_implied/USD_free gap from `STRATEGY.md` §3B, or news-driven regime flags —
  could plausibly work where momentum cannot.
- **A different regime.** This sample is 18 months of extreme domestic gold
  strength under war. In a classic rial-devaluation shock with flat world gold,
  USD leads and persists. The detector is built; leave it off until then.

---

## 7. What to actually do

```
DEFAULT: hold gold (مثقال or ربع per the A/B rule), not USD.
         Gold beat USD 68% of 20-day windows and +53% overall.

The USD sleeve stays OFF unless one of these becomes true:
  1. your round-trip cost drops below ~1%/leg, or
  2. 45-day rel-momentum < −8pp AND persists 30+ sessions
     (a real regime, not a 2-day blip), or
  3. world gold is falling while the rial is devaluing — the one
     configuration where USD structurally leads domestic gold.
```

Your A/B quarter↔mesghal strategy (A=60%, B=31%) remains the primary engine.
It works because the quarter bubble genuinely oscillates 13%→76% with a ~29pp
tradeable gap — roughly 7× the 4pp cost hurdle. The USD spread simply is not
that wide.

Data: `data/usd_irr.csv` (441 sessions), `data/qm_full.csv` (430 sessions).
