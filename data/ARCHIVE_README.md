# Iran Gold / FX daily archive, 2020-2026

**File:** `ARCHIVE_iran_gold_fx_2020_2026.csv`
**Rows:** 1,655 trading sessions · **2020-02-05 → 2026-07-27** (~6.5 years)
**Source:** tgju.org daily **close** (`rob`, `mesghal`, `price_dollar_rl`)

Only dates where **all three** instruments have a close are included, so every
row is directly comparable.

## Columns

| column | meaning |
|---|---|
| `date` | Gregorian, YYYY-MM-DD |
| `quarter_rial` | ربع سکه close, rial |
| `mesghal_rial` | مثقال آب‌شده close, rial |
| `usd_rial` | USD/IRR close, rial |
| `quarter_toman` `mesghal_toman` `usd_toman` | same ÷ 10 |
| `quarter_rial_per_g` | `quarter_rial / 1.8288` — rial per gram of **fine** gold |
| `mesghal_rial_per_g` | `mesghal_rial / 3.24885` — same basis |
| `RP` | relative premium, decimal (0.216 = 21.6%) |
| `vol45` | 45-session stdev of daily مثقال returns |
| `vol90` | 90-session stdev of daily مثقال returns ← **the one in use** |
| `pos_layer2` | position held that day, Layer-2-only strategy |
| `pos_twolayer` | position held that day, two-layer strategy |

Blank `vol*` / `pos_*` cells are the warm-up window (first 46–91 rows).

## Formulas

```
QUARTER_G = 2.032  × 0.900 = 1.8288  g fine   (ربع سکه)
MESGHAL_G = 4.6083 × 0.705 = 3.24885 g fine   (مثقال, عیار ۷۰۵)

RP    = (quarter_rial / 1.8288) / (mesghal_rial / 3.24885) − 1
vol90 = population stdev of the last 90 daily مثقال returns
```

RP needs only the two dealer-board prices — the world gold price and the
dollar rate cancel out algebraically.

## Strategy parameters used for the position columns

```
A_SELL_QUARTER = 0.60     RP ≥ 60% → hold مثقال
B_BUY_QUARTER  = 0.31     RP ≤ 31% → hold ربع سکه
VOL_HI / VOL_LO = 0.030 / 0.022   on vol90 (two-layer only)
MINHOLD  10 sessions (L1) · 5 sessions (L2)
COST     2% per leg
```

Layer-2-only makes **6** trades; two-layer makes **11**.

## Data-quality notes — read before using

**Range observed:** RP 12.1% – 120.8% · vol90 0.82% – 3.25%

**Rows deliberately excluded** (verified tgju placeholders, not real prices):

- USD `2021-12-02`, `12-09`, `12-16`, `12-30`, `2022-01-13` — identical
  OHLC and a fake ~10% dip vs both neighbours, every one a Thursday.
- USD `2020-03-18 → 2020-04-02` — frozen at ~149,000 through the Nowruz +
  COVID closure.

**Large moves that are REAL and were kept:**

- USD `2022-05-14` **+19.4%** — the جراحی اقتصادی subsidy reform.
- ربع `2025-03-17` **+17.2%** — corroborated by مثقال moving the same way.
- مثقال `2024-05-18` — Raisi helicopter crash.
- مثقال `2026-02-02` — war-period spike.

> An automatic one-day-spike filter was tried at a 4% threshold and
> **rejected**: it deleted the Raisi crash and the 2026 war spike. Iranian
> gold genuinely moves 8–14% in a day on news, so no purely statistical rule
> separates a real event from a stale placeholder. Only manually verified
> placeholders were removed.

**⚠️ The `rob` index blends mint years.** tgju's quarter-coin series mixes
۱۳۸۶ / ۱۴۰۳ / ۱۴۰۴, which have traded up to 1m toman apart. Treat
`quarter_*` as an index, not a quote for one specific coin.

Screen closes are not dealer fills.

## Provenance

Collected by paging tgju's undocumented JSON endpoint ~60 records at a time:

```
https://api.tgju.org/v1/market/indicator/summary-table-data/{symbol}?start=N&length=60
```

Per-batch raw pulls are kept in `data/raw/` if you want to re-verify any
segment. `make_archive.py` regenerates this file from `data/master.csv`.

tgju's history reaches back to **2013-07** for all three series, so this
archive can be extended a further ~6.5 years with more paging.
