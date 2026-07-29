# 2020 Backtest — Data Collection Status

## Verified: tgju paged JSON API reaches back well past 2020

| symbol | series | recordsTotal | index of 2020-01-01 | earliest confirmed |
|---|---|---|---|---|
| `rob` | ربع سکه | 3,375 | ~1798 | 2019-08-28 seen at idx 1882 |
| `mesghal` | مثقال | 3,468 | ~1859 | 2019-12-02 seen at idx 1882 |
| `price_dollar_rl` | USD/IRR | 3,914 | ~1845 | 2019-11-19 seen at idx 1882 |

Confirmed index anchors (for resuming):

```
rob      idx 1797 = 2020-01-05 , idx 1798 = 2020-01-04
mesghal  idx 1858 = 2020-01-05 , idx 1859 = 2020-01-04
usd      idx 1845 = 2020-01-01
rob      idx 487  = 2024-10-05
mesghal  idx 497  = 2024-11-05
usd      idx 430  = 2025-01-21
```

## 🔴 Data bug found in `data/usd_irr.csv`

`usd_irr.csv` was built from **column 0 (open)**, but `qm_ext.csv` /
`qm_full.csv` / `seed_history.csv` were built from **column 3 (close)**.
The two gold series and the USD series are on *different price conventions*.

Verified on 120 overlapping days (2024-08-28 → 2025-01-21):

```
mean |open − close| divergence : 0.73%
max                            : 2.18%
USD daily-return vol, open     : 0.985%
USD daily-return vol, close    : 0.978%
cumulative over window, open   : +39.16%
cumulative over window, close  : +39.02%
```

**Impact: small but non-zero.** Cumulative USD return over 120 days shifts
by 0.14pp, so the headline "hold USD" benchmark is barely affected. But
Layer 1 compares gold vs USD on *forward 30-day* windows, and a 0.73%
mean divergence is material at that horizon. Any rebuild must use
**close (column 3) for all three series** for internal consistency.

## Constraint that shaped collection

The sandbox has **no outbound network from bash** (DNS resolves,
all TCP returns `000`). Only the `fetch_page` tool has egress, and it
chunks responses at ~60-70 records per call. There is **no bulk/chart
endpoint** — probed and 404:

```
/v1/market/indicator/history/{sym}
/v1/market/indicator/chart-data/{sym}
/v1/market/indicator/summary/{sym}
/v1/chart/linechart/{sym}
/v1/chart/data?symbol=
```

So a full 3-series rebuild to 2020 = ~4,000 records ≈ 67 paged fetches.
Not completable in a single session.

## Collected this session (raw, close prices)

- `rob_530_650.csv` — 120 sessions ربع سکه, 2024-03-05 → 2024-08-09 (close)
- `usd_close_2024-08-28_2025-01-21.csv` — 120 sessions USD, both open and
  close, used to diagnose the column bug above

## Resume plan (user chose: all three series, ~2022 start)

Page backwards with `length=60`, saving after each batch:

```
rob      idx 650 → 1100   (2022-01 .. 2024-03)
mesghal  idx 610 → 1100
usd      idx 550 → 1100
```

Then rebuild all three from column 3 and re-run the five-approach
comparison on the common date intersection.
