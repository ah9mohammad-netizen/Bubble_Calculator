# Audit — `Strategy.xlsb` (your existing framework)

Decoded from the binary workbook on `main`. Author: AmirHossein Mohammad.
Created 2025-11-09, last modified 2026-02-21. 3 sheets + a VBA project.

---

## 1. What the workbook actually is

| Sheet | Role |
|---|---|
| `DATA ENTRY` | Live scratchpad. You type 5 inputs; it computes 6 derived metrics and 2 decisions. |
| `FACTORS` | 12 tunable parameters. |
| `DATA SET` | Append-only archive, **365 sessions, 2024-10-30 → 2026-02-19**. |

`Module1.Macro1` is **not** strategy logic — it is an archiver. It inserts a row
at the top of `DATA SET`, transpose-pastes `DATA ENTRY!B1:B12` into it as values,
and returns. All the intelligence is in the `DATA ENTRY` formulas.

### Inputs you type daily
`DATE`, `USD` (IRR), `WorldSpot` (USD/oz), `24K` (IRR/gram), `Quarter` (IRR), `Mesghal` (IRR)

### Decoded formulas (verified numerically to 1e-15 against stored values)

```
USD_MOM  = USD / 'DATA SET'!$B$252 − 1          ← 250 rows back
24K_MOM  = 24K / 'DATA SET'!$D$252 − 1          ← 250 rows back
Delta    = 24K_MOM − USD_MOM
Q/M_Ratio= (Quarter/1.8306) / (Mesghal/3.264213)   ← price per fine gram, ratio
Premium  = 24K / ((WorldSpot/31.1035) × USD) − 1    ← domestic gold premium
Z-Score  = (Premium − AVERAGE('DATA SET'!$K$2:$K$252)) / STDEV('DATA SET'!$K$2:$K$252)
```

### Decoded decision tree

```
DECISION_USD/GOLD =
    IF(Delta > 1.0, "GOLD",
    IF(Z > 0.008, "EMERGENCY GOLD EXIT",      ← see §2.2
    IF(Delta < -0.8, "GOLD",
    IF(Delta >  1.2, "GOLD", ...
    IF(Z > 0.008, "USD", "HOLD")))))

DECISION_Q/M =
    IF(Q/M_Ratio > 1.38, "Mesghal",
    IF(Q/M_Ratio < 1.24, "Quarter", "HOLD"))
```

The `Q/M` rule is clean. The `USD/GOLD` rule is where the problems are.

---

## 2. Findings, worst first

### 2.1 🔴 `Delta` is structurally incapable of ever saying "USD"

`Delta` compares **250-session trailing returns** of gold vs USD. Over the 115
sessions where it is computable:

| stat | value |
|---|---|
| min | **+0.641** (+64%) |
| median | +0.868 |
| max | +1.397 |
| fraction `Delta ≥ +0.008` | **100.0%** |
| fraction `Delta ≤ −0.008` | **0.0%** |

The threshold is **0.8%**. The actual signal never goes below **+64%**. Gold has
outrun USD by 64–140 percentage points on every single trailing-year window in
your data. `Delta > Delta_Threshold` is therefore a constant `TRUE`, and the
`USD/GOLD` decision is a hardcoded `"GOLD"`.

The parameter `Delta_Threshold = 0.008` is calibrated for a **daily or weekly**
momentum difference. It is being applied to an **annual** one. The lookback and
the threshold are off by roughly two orders of magnitude relative to each other.

**This is the single most important bug.** Your stated goal — "sometimes keeping
USD is better than gold" — is currently unreachable by the model.

**Fix:** `Delta` must be a short-horizon momentum spread (5–20 sessions), and the
threshold must be re-derived from that series' own dispersion, not chosen a
priori. Better still, use the §3 `R` ratio, which is scale-free.

### 2.2 🔴 The `Z > 0.008` comparison mixes units

Inside the decision tree, the Z-score branch tests `Z > 0.008` — but `0.008` is
`Delta_Threshold`, a **percentage**. `Z` is a **standard-deviation score** ranging
−4.88 to +6.19 in your data. The literal is also hardcoded in the formula rather
than referencing `FACTORS`, so `Z_High (1.2)`, `Z_Low (−0.8)` and `Z_Exit (1.5)`
are **defined but never used** by the live decision.

Consequence: the "EMERGENCY GOLD EXIT" branch fires whenever `Z > 0.008`, i.e.
roughly **half the time**, instead of the ~6% of the time `Z_Exit = 1.5` intends.
It is masked today only because branch 1 (`Delta > 1.0`) short-circuits to
`"GOLD"` first. **Fix §2.1 without fixing this and the model will start emitting
emergency exits on half of all sessions.** These two bugs are currently hiding
each other.

### 2.3 🟠 Z-score look-ahead / fixed-window bias

`Z` reads `$K$2:$K$252` — an **absolute** reference. Because new rows are
inserted at row 2, this window slides correctly in real time. But every
historical `Z` stored in `DATA SET` was computed against *whatever window existed
on that date*, so the archived `Z` column is not a consistent time series and
must not be used for backtesting. I recomputed `Z` on a clean trailing window for
all analysis below.

Also: with only 365 archived rows, a 251-row window means `μ` and `σ` are
estimated from a period that includes the extreme regime shift of early 2025.
`σ` is inflated, so `|Z|` is compressed toward zero.

### 2.4 🟠 `R_Low`/`R_High` are stale relative to the current regime

`Q/M_Ratio` monthly means show a strong secular decline:

```
2024-10  1.589      2025-04  1.624      2025-10  1.276
2024-11  1.514      2025-05  1.576      2025-11  1.290
2024-12  1.471      2025-06  1.499      2025-12  1.327
2025-01  1.366      2025-07  1.446      2026-01  1.306
2025-02  1.341      2025-08  1.412      2026-02  1.186
2025-03  1.537      2025-09  1.348
```

The quarter-coin premium over mesghal has compressed from ~1.59 to ~1.19 over 16
months. Fixed bands `[1.24, 1.38]` were reasonable mid-sample; today the ratio
sits **below** `R_Low`, so the model is pinned to `"Quarter"`. 54% of all
sessions are above `R_High` and only 6% below `R_Low` — the bands are not
centred on the distribution.

This is exactly the structural-drift problem: a **fixed** band on a **trending**
ratio degenerates into a permanent one-sided signal. The bands need to be
z-scores or rolling quantiles of `Q/M_Ratio`, not constants.

### 2.5 🟡 Mesghal fine-gold constant is inconsistent

`FACTORS` says `Mesghal_24k_g = 3.264213` ("4.6083g @ 17K"). But
`4.6083 × 17/24 = 3.26421`. ✅ consistent. However `Quarter_24k_g = 1.8306`
implies `2.0340 × 0.900`. ✅ also fine. **No error** — but note the mesghal figure
assumes exactly 17/24 = 0.70833 fineness, whereas آب‌شده commonly trades at
**0.705** measured (عیار ۷۰۵), which is 0.47% lower. That 0.47% is a permanent
bias in `Q/M_Ratio` — small, but it sits directly inside your arbitrage
threshold, which is only ~11% wide.

### 2.6 🟡 No cost model anywhere

There is no bid/ask, no dealer spread, no fee. Every decision is evaluated at
mid. With `MinHold` of 8–15 days the turnover is low enough that this is
survivable, but it means the backtest below is an upper bound.

### 2.7 🟡 `Confirm_Days_USDGold = 2` is not implemented

The parameter exists in `FACTORS`. Nothing in the formulas references it — there
is no state memory in a single-row scratchpad. Same for `MinHold_USDGold (15)`
and `MinHold_GoldTypes (8)`. **Three of your twelve parameters are documentation,
not logic.** A spreadsheet with one live row structurally cannot enforce a
minimum holding period; that requires the archive to be read back.

---

## 3. Backtest of your logic, in grams

Rules as written (with `MinHold`/`Confirm` implemented as intended, and `Z_Exit`
used correctly), start = 1 gram, window 2025-09-30 → 2026-02-19 (the period where
`Delta` is computable):

| cost/leg | final NAV (g) | trades |
|---|---|---|
| 0.0% | 1.0760 | 3 |
| 0.5% | 1.0441 | 3 |
| 1.0% | 1.0130 | 3 |

Baselines over the identical window:

| strategy | final NAV (g) |
|---|---|
| hold Quarter | **1.1639** |
| hold 24K (numeraire) | 1.0000 |
| hold Mesghal | 0.9954 |
| hold USD | 0.7697 |

**The strategy underperforms simply holding quarter coins**, at every cost level.
It made 3 trades and captured about half of the quarter-coin move.

Two honest caveats: the evaluable window is only ~4.7 months because `Delta`
needs 250 sessions of warm-up, and that window happens to be one where quarter
coins ran hard. This is not enough data to condemn the approach — but it is
enough to say **the current parameterisation has not demonstrated an edge.**

The USD baseline result is the important one: **0.77 grams.** Holding dollars for
16 months cost you 23% of your gold. Over this sample the "hold USD sometimes"
thesis has been expensive; USD returned +140% while 24k gold returned +331% in
rial terms. Whatever USD rule replaces §2.1 must clear a high bar.

---

## 4. What is genuinely good here

Worth keeping, and I'd build v2 on top of it rather than starting over:

1. **Per-fine-gram normalisation in `Q/M_Ratio`.** Dividing each coin by its own
   fine-gold content before comparing is exactly right, and it is the thing most
   retail approaches get wrong.
2. **The `Premium` definition.** `24K / ((spot/31.1035) × USD) − 1` is the correct
   domestic-premium construction and matches §2 of `STRATEGY.md`.
3. **Z-scoring the premium** rather than trading its raw level — right instinct,
   just not yet wired into the decision.
4. **Separating the macro decision (USD vs gold) from the relative-value decision
   (Quarter vs Mesghal).** This is the correct architecture and maps directly
   onto Layer A / Layer B in `STRATEGY.md`.
5. **The append-only archive.** 365 clean sessions of aligned data is a real
   asset and the hardest part to reconstruct.

---

## 5. Reconciliation with `STRATEGY.md`

| `STRATEGY.md` | `Strategy.xlsb` | Status |
|---|---|---|
| Layer A: coin-vs-metal spread | `Q/M_Ratio` rule | ✅ present, bands need to float |
| Layer B: gold-vs-USD regime | `Delta` rule | 🔴 broken (§2.1) |
| Layer C: momentum gate | — | ❌ absent |
| Grams numeraire | — | ❌ absent (works in rials) |
| Bubble z-score per instrument | `Z` on 24K only | 🟠 partial — no per-coin z |
| Cost model | — | ❌ absent |
| Auction-calendar veto | — | ❌ absent |
| Hysteresis / min-hold | in `FACTORS`, unused | 🟠 declared not implemented |

The workbook is a solid **Layer A** engine with a **non-functional Layer B**.

---

## 6. Recommended next steps, in order

1. **Replace `Delta` with the scale-free regime ratio** from `STRATEGY.md` §3B:
   `R = USD_implied / USD_free`, traded on its own z-score. This cannot suffer
   the units mismatch of §2.1 because it is dimensionless by construction.
2. **Wire `Z_Low` / `Z_High` / `Z_Exit` into the decision** and delete the
   hardcoded `0.008` from the Z branch.
3. **Float the `Q/M` bands** — replace `[1.24, 1.38]` with rolling quantiles or a
   z-score of `Q/M_Ratio` on a 90–120 session window.
4. **Add a `Quarter` premium and `Mesghal` premium column** so each coin gets its
   own bubble z-score, per `STRATEGY.md` §2. Right now only 24k has one.
5. **Add a cost column** and re-run. If the edge does not survive 0.5%/leg, it is
   not an edge.
6. **Extend the archive backwards** if you can source it — 365 sessions is one
   regime. Half-life estimation needs 3+ years.

The fastest high-value change is #3 plus #1. Those two touch the two decisions
that are currently pinned to constants.
