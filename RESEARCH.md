# Market Research — Iran Gold/FX Arbitrage

Research conducted 2026-07-28. Purpose: ground the strategy in verified market
structure, real cost numbers, and usable data sources.

---

## 0. 🔴 Read this first: your workbook is 5 months stale, and the regime changed

`Strategy.xlsb` ends **2026-02-19**. Since then Iran has entered an **active
military conflict with the United States** — strikes on Tehran, closure of the
Strait of Hormuz, Iranian retaliation against installations in the UAE, Kuwait
and Bahrain, with a fragile pause as of late July 2026 [1](https://www.business-standard.com/amp/markets/commodities/gold-silver-may-stay-volatile-amid-us-iran-tensions-inflation-data-126071200309_1.html)[2](https://www.cnbc.com/amp/2026/07/27/gold-wavers-as-investors-weigh-us-strikes-on-iran-await-fed-minutes.html).

This matters enormously and in a **counter-intuitive** direction:

> Escalation between the US and Iran drives the **global dollar up** and
> **XAU/USD down**, because oil spikes → inflation fears → higher-rate
> expectations → stronger DXY → weaker gold [3](https://www.reuters.com/world/india/gold-falls-stronger-dollar-amid-renewed-us-iran-tensions-2026-04-20/).

Meanwhile *inside* Iran the same news drives the **rial down** and domestic gold
**up**. So during a conflict shock your two intrinsic-value inputs move in
opposite directions and partially cancel. Any model that treats `WorldSpot` and
`USD_IRR` as independent noise will misprice the bubble exactly when it matters
most. **Conflict state must be an explicit regime variable, not a residual.**

Second implication: the §2.7 "no state memory" problem in the audit becomes
critical. In a war regime, a 250-day trailing window is meaningless.

---

## 1. Verified instrument specifications

Cross-checked against multiple Iranian sources. **Two corrections to your
`FACTORS` sheet.**

| Instrument | Weight (g) | Fineness | Fine gold (g) |
|---|---|---|---|
| سکه امامی / تمام | 8.133 | 0.900 (عیار ۲۱.۶) | 7.3197 |
| نیم سکه | 4.066 | 0.900 | 3.6594 |
| **ربع سکه** | **2.032–2.033** | 0.900 | **1.8288–1.8297** |
| مثقال آب‌شده | 4.6083 | **0.705 (عیار ۷۰۵)** | **3.2489** |
| گرم ۱۸ عیار | 1.000 | 0.750 | 0.7500 |

Sources: [4](https://zcoinn.com/coin/), [5](https://alanchand.com/en/how_to_calculate_gold_bubble)

### Correction A — your Mesghal constant is ~0.47% too high

`FACTORS` uses `Mesghal_24k_g = 3.264213`, derived from `4.6083 × 17/24`
(= 0.70833 fineness). The market convention for آب‌شده is **عیار ۷۰۵**, i.e.
0.705, giving **3.2489 g**. AlanChand's published bubble table uses 0.705 [5](https://alanchand.com/en/how_to_calculate_gold_bubble).

This is a **permanent +0.47% bias in `Q/M_Ratio`**, sitting inside a band that is
only ~11% wide (`R_Low` 1.24 → `R_High` 1.38). It systematically biases you
toward "Quarter."

> ⚠️ But note: آب‌شده fineness is **not fixed** — it is whatever the assayed
> piece is (عیار ۷۴۰, ۷۰۵, etc. all trade). The correct treatment is to carry
> fineness as a per-trade input, not a global constant. The tgju `mesghal`
> index is a 705 benchmark; your actual dealer piece may differ, and you must
> reprice off its ری‌گیری certificate.

### Correction B — ربع سکه weight

You use 2.03399 g. Iranian trade sources give **2.032** or **2.033** [4](https://zcoinn.com/coin/)[5](https://alanchand.com/en/how_to_calculate_gold_bubble).
Small (~0.05%) but free to fix.

---

## 2. 🔴 The Quarter/Mesghal decline you found is NOT mean reversion

The audit found `Q/M_Ratio` monthly means falling 1.589 → 1.186 over 16 months.
Research explains **why**, and it is structural, not cyclical:

**Driver 1 — CBI auctions.** The Central Bank began coin auctions (حراج سکه) at
مرکز مبادله on **1402-12-13 (Mar 2024)**. By **1403-11-01 (Jan 2025)** over **63
auctions** had been held [6](https://fararu.com/fa/news/823623/). By late 2025 they ran **three
days a week** [7](https://donya-e-eqtesad.com/4117175). Bubbles fell across almost all
denominations; **ربع سکه had the second-largest bubble decline** of any piece [6](https://fararu.com/fa/news/823623/).

**Driver 2 — new mint years destroyed the ۸۶ scarcity premium.** Before Nov 2024,
essentially all circulating coins were ضرب ۱۳۸۶, and ربع سکه ۸۶ carried a large
scarcity bubble. On **1403-08-19 (Nov 9, 2024)** the CBI auctioned the first
**ربع سکه ضرب ۱۴۰۳**. Merely *announcing* it knocked ربع سکه طرح قدیم from
18.5m to ~15m tomans within days [8](https://snn.ir/fa/news/1192000/). The CBI then committed
to minting **each year with its own date**, explicitly to kill the vintage
premium [9](https://www.tabnak.ir/fa/news/1270153/).

**This is a one-way structural repricing, not a cycle.** Your `Q/M_Ratio` will
not revert to 1.59. A mean-reversion model calibrated on 2024 data is fitting a
policy-driven regime break as if it were noise.

> **Design consequence:** the Layer-A z-score baseline must use a **short,
> adaptive window** (60–120 sessions) or an explicit structural-break test.
> A 250-day window straddles the break and produces garbage.

### 🔴 And a data-integrity landmine: "ربع سکه" is not one asset

Coins now trade as **distinct lines by mint year**: ۱۳۸۶, ۱۴۰۳, ۱۴۰۴. The ۱۴۰۳
issue trades **500k–1m tomans BELOW** ۱۳۸۶/۱۴۰۴ because of differences in colour
and strike quality, and remains incompletely accepted by the trade [10](https://www.hamshahrionline.ir/news/1003325/).

So a single "Quarter" price is an **ambiguous blend**. If your dealer quotes ۱۴۰۳
and tgju indexes ۱۳۸۶, your measured bubble is wrong by more than your entire
trading band. **You must record mint year on every quote and every trade.**

Same applies to سکه پلمب (sealed) vs باز, and بانکی vs غیربانکی.

---

## 3. Real transaction costs — the strategy's make-or-break

This is the number the workbook has no model for. Verified ranges:

| Leg | Buy | Sell | Round trip |
|---|---|---|---|
| **آب‌شده, online platform** (گلدیکا/زرمینکس/طلاسی) | 0.5–1.0% | 1.0% | **~1.5–2.0%** |
| **آب‌شده, traditional dealer** | +2–3% seller margin | 1.5–3.0% | **~3.5–6.0%** |
| **سکه** | dealer spread | dealer spread | **~1.5–3.0%** |
| **Gold ETF (بورس)** | ~0.1–0.2% | ~0.1–0.2% | **~0.3–0.5%** |

Sources: [11](https://zarminex.ir/blog/melted-gold-fee/), [12](https://blog.goldika.ir/molten-gold-authenticity), [13](https://www.etemadonline.com/752095), [14](https://faraz.io/blog/financial-markets/gold-and-currency/gold-price-calculation-formula/)

**Tax:** آب‌شده and raw gold are **VAT-exempt** under Article 26 of the 1400 VAT
law — only اجرت ساخت, seller profit and حق‌العمل are taxable (10% in 1405) [15](https://taline.ir/pricing-melted-gold-iran/)[14](https://faraz.io/blog/financial-markets/gold-and-currency/gold-price-calculation-formula/).
If you request a رسمی invoice, 9–10% VAT applies to fee+margin — normally not
issued for آب‌شده resale [11](https://zarminex.ir/blog/melted-gold-fee/). **Never trade مصنوعات or سکه پارسیان
for this strategy**: 7% اجرت + 9% VAT + margin ≈ 20% round trip [12](https://blog.goldika.ir/molten-gold-authenticity).

### Why this is decisive

Recall the audit backtest: your rules produced **+7.6% gross, 3 trades**, vs
**+16.4% for simply holding ربع سکه**. Now layer on a realistic **1.5–2.0%
round trip** for physical legs. Every rotation must clear ~2% *in grams* just to
break even. Over 16 months and a handful of trades, that is most of the edge.

> **The single highest-leverage change available to you: move the execution
> venue, not the signal.** Same strategy on gold ETFs (~0.4% round trip) instead
> of physical (~2%) is worth several percent a year in grams — likely more than
> any refinement of `R_Low`/`R_High` will ever produce.

---

## 4. Data sources — verified working

### ✅ tgju undocumented JSON API (recommended)

```
https://api.tgju.org/v1/market/indicator/summary-table-data/{symbol}
```

Returns `[open, low, high, close, change, change%, gregorian, jalali]`,
newest-first, **full history in one call**. Verified live:

| Symbol | Series | Records |
|---|---|---|
| `price_dollar_rl` | USD/IRR free market | deep |
| `sekeb` | سکه امامی | **3,446** |
| `nim` | نیم سکه | ~3,400 |
| `rob` | ربع سکه | ~3,400 |
| `mesghal` | مثقال آب‌شده | **3,467** |
| `geram18` | طلای ۱۸ عیار | deep |
| `geram24` | طلای ۲۴ عیار | deep |
| `ons` | XAU/USD | deep |

**≈13 years of daily OHLC** — vs the 365 rows you have. This alone fixes the
audit's "one regime only" problem and makes half-life estimation possible.

### ⛔ Do NOT use tgju's bubble indices

`coin_blubber` (1,943 recs) and `rob_blubber` (1,913 recs) look perfect for this
project. **They are unusable.** I pulled them: `coin_blubber` contains daily
"changes" of **5718%**, **25228%**, **30571%**, and repeated placeholder values
of exactly 10,000 / 100,000 / 9,990,000. The series is corrupted with sentinel
values and division artifacts.

**Compute your own bubble from raw prices.** Your `Premium` formula is correct —
keep it.

### Other

- Python wrappers exist (`tgju-crawl`, `tgju_api`, `oxtapus`) but are 2023-era;
  hitting the JSON endpoint directly is cleaner.
- **Cross-check USD against a second source** (alanchand, bonbast, or Nobitex
  USDT/IRT). tgju is indicative, not executable.
- **Auction calendar**: مرکز مبادله announcements, mirrored by tgju news and
  nabzebourse. No API — needs scraping or manual entry.

---

## 5. Auction mechanics — a tradeable edge you are not using

Auctions are not merely a risk to dodge. Published data on the pattern of
auction discounts vs the free market [16](https://nabzebourse.com/fa/news/118660/):

| Piece | Typical auction discount to market |
|---|---|
| تمام سکه | 4.0–5.5% |
| نیم سکه | 5.0–6.5% |
| **ربع سکه** | **6–10%**, occasionally >3.5m toman gap |

Two direct consequences:

1. **A recurring, quantified discount** — the auction *is* the arbitrage. Buying
   ربع at auction 6–10% under market beats anything the rotation signal has
   produced. Allocation is by price-time priority and is not guaranteed, but
   average auction clearing price is consistently below market [17](https://nabzebourse.com/fa/news/86159/).
2. **Announcement effect on the free market.** Auction news compresses bubbles;
   the ۱۴۰۳ ربع announcement alone cut prices several million toman [8](https://snn.ir/fa/news/1192000/).

Also note: **demand at auctions has been persistently weaker than supply** —
settled volume consistently below orders placed, which the CBI reads as low
inflationary expectations [17](https://nabzebourse.com/fa/news/86159/). Auction bid/cover is therefore a
**free sentiment indicator** for the coin bubble.

**Recommendation: add auction date, floor price, average clearing price, volume
offered and bid/cover to the data model.** This is likely a bigger edge than
Layers A–C combined, and it is a scheduled, calendar-known event.

---

## 6. Gold ETFs — the friction fix, with a caveat

15+ صندوق طلا trade on the Tehran exchange. Their bubbles (market price vs NAV)
are published and, critically, **have compressed to near zero**: a 3-month study
to 1405-03-23 found an average **−0.5% price bubble / −1.7% total bubble**, with
most funds trading at a small discount [18](https://learning.charisma.ir/funds/).

That is a big change from 2024, when gold funds averaged **+12%** bubbles [19](https://ecoiran.com/62937).

Implications:
- ETFs are now a **cheap, clean gold proxy** (~0.4% round trip vs ~2% physical).
- Fund bubble vs physical coin bubble is **itself a spread** — a new Layer-A pair
  with far lower friction.
- Caveat: funds hold a **mix** of shemsh and coins, so a fund's "intrinsic bubble"
  (حباب ذاتی) inherits coin bubbles. Decompose: `total = nominal + intrinsic` [18](https://learning.charisma.ir/funds/).

---

## 7. Revised priorities

Ordered by expected value, highest first:

1. **Pull 13 years of history from the tgju API.** Everything downstream depends
   on it. Recompute bubbles yourself; ignore tgju's bubble indices.
2. **Add the auction calendar + clearing prices.** Probably the largest single
   edge, and it is scheduled and public.
3. **Move execution to ETFs where possible.** ~1.6pp saved per round trip in
   grams beats any parameter tuning.
4. **Fix Mesghal fineness to 0.705** and treat fineness as a per-trade input.
5. **Record mint year on every coin quote.** Otherwise your bubble series is a
   blend of three different assets.
6. **Add a conflict/regime state variable.** In a war regime, XAU and USD/IRR
   move in opposing directions and the 250-day window is meaningless.
7. Only then revisit `R_Low`/`R_High`, Delta, and the z-score windows from the
   audit.

Note the shape of this list: **items 1–6 are data and execution, not signal
logic.** That ordering is deliberate. The audit showed the current signal
underperforming buy-and-hold ربع سکه; research suggests the fix is better data,
cheaper venues, and the auction calendar — not a better indicator.
