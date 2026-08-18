# 10-Year Backtest — Data Collection Status

## ✅ tgju HAS the full history — 13 years, back to 2013-07

Verified by probing the end of each series:

| symbol | series | recordsTotal | oldest record |
|---|---|---|---|
| `rob` | ربع سکه | 3,389 | **2013-07-24** |
| `mesghal` | مثقال | 3,482 | **2013-07-24** |
| `price_dollar_rl` | USD/IRR | 3,928 | earlier still |

So a 10-year (or even 13-year) backtest is possible. The limit is purely
mechanical, not availability.

## The bottleneck

- **bash has no outbound network** in this sandbox (DNS resolves, every TCP
  connection returns `000`). Only the `fetch_page` tool reaches the internet,
  so the paging loop cannot be scripted.
- `fetch_page` returns **~60 records per call**.
- No bulk/CSV endpoint exists. Probed and 404:
  `/v1/market/indicator/history/{sym}`, `/chart-data/{sym}`, `/summary/{sym}`,
  `/v1/chart/linechart/{sym}`, `/v1/chart/data?symbol=`

## Alternative sources evaluated (user-suggested)

| source | verdict |
|---|---|
| servatmandi.com/Entities/2 | Gold **ETFs** (صندوق طلا) on بورس کالا — not ربع/مثقال spot. **Valuable for the execution-cost problem** (0.3–0.5% round trip), not for history. |
| navasan.net/dayRates.php | `?item=abshodeh` returns HTTP 500; root page is live prices only, no bulk archive. |
| chartix.ir/market/tala/Abshode_Etehadiye | Live price + rendered chart. Has ربع سکه and دلار pages too, but history sits behind a paid "نمودار پیشرفته" (max.chartix.ir) and is not exposed as data. |

**Conclusion: tgju remains the best source.** It has the depth; it just has to
be paged.

## Index anchors (for resuming)

```
rob      idx 1106 = 2022-07-20   idx 1798 = 2020-01-04   idx 2600 = 2016-09-25
mesghal  idx 1138 = 2022-08-14   idx 1859 = 2020-01-04   idx 2680 = 2016-10-05
usd      idx 1137 = 2022-08-03   idx 1845 = 2020-01-01   idx 3050 = 2015-05-09
```

## Effort remaining

| target | records to fetch | ≈ paged calls |
|---|---|---|
| 2020-01 start (6.5 yr) | 2,121 | **~35** |
| 2016-09 start (10 yr) | 4,949 | **~82** |

## Current coverage

`data/master.csv` — **1,035 sessions, 2022-05-30 → 2026-07-27** (~4.2 years),
all three assets, all **close** prices.

## Data-quality notes

- Only 1 daily move >15% in the whole file: ربع +17.2% on 2025-03-17,
  corroborated by مثقال moving the same direction. Real.
- USD **2022-05-14 +19.45%** was investigated and **kept**: it is the
  real "جراحی اقتصادی" subsidy-reform devaluation of May 2022, confirmed
  against external reporting. Rows 2022-05-07..05-12 retained.
