# Combined Two-Layer Strategy

Three assets: **USD**, **مثقال آب‌شده**, **ربع سکه**.
Two independent decision layers. 375 aligned sessions (2025-01-04 → 2026-07-27).
All results in **rials**, start 1.000 bn, **2% per leg** fee+slippage.

---

## Architecture

```
                    ┌─────────────────────────────┐
   LAYER 1          │  gold 30-day volatility     │
   macro / risk     │  GV ≥ 3.3%  →  hold USD     │
                    │  GV ≤ 1.5%  →  back to gold │
                    └──────────────┬──────────────┘
                                   │ if "gold"
                    ┌──────────────▼──────────────┐
   LAYER 2          │  RP = quarter bubble vs     │
   relative value   │       mesghal, per fine gram│
                    │  RP ≤ 31%  →  hold ربع سکه  │
                    │  RP ≥ 60%  →  hold مثقال    │
                    └─────────────────────────────┘
```

**Layer 1 has priority.** Layer 2 only chooses *which gold instrument* to hold;
it never overrides a USD signal. Separate minimum-hold gates: 10 sessions for
Layer 1, 5 for Layer 2, so the layers cannot fight each other.

### Signals

```
RP = (P_ربع / 1.8288) / (P_مثقال / 3.2489) − 1
GV = stdev of daily مثقال returns over trailing 30 sessions
```

`1.8288 = 2.032 g × 0.900` (fine gold in ربع سکه)
`3.2489 = 4.6083 g × 0.705` (fine gold in one مثقال آب‌شده)

---

## Results

| strategy | wealth | × gold | trades |
|---|---|---|---|
| hold rial cash | 1.000 bn | 0.281× | — |
| hold USD | 2.331 bn | 0.656× | — |
| hold ربع سکه | 3.103 bn | 0.873× | — |
| **hold مثقال** (benchmark) | **3.556 bn** | **1.000×** | — |
| Layer 2 only (A=60, B=31) | 4.029 bn | 1.133× | 3 |
| Layer 1 only (vol 4.0/3.0) | 3.883 bn | 1.092× | 2 |
| **COMBINED (vol 3.3/1.5)** | **4.366 bn** | **1.228×** | **6** |
| COMBINED (vol 3.8/1.5) | 4.873 bn | 1.370× | 4 |
| *true optimum (hindsight)* | *5.831 bn* | *1.640×* | *13* |

**The combined system captures ~1.23× of the 1.64× theoretical maximum — about
36% of the available edge, versus 20% for Layer 2 alone.**

### Trade log (vol 3.3/1.5)

```
2025-02-11  M → Q    RP 30%   V 1.7%     buy quarter, bubble cheap
2025-03-17  Q → M    RP 76%   V 2.3%     sell quarter at peak bubble
2025-04-12  M → U    RP 67%   V 3.5%     vol spike → risk off to USD
2025-08-06  U → M    RP 43%   V 1.5%     vol normalised → back to gold
2025-09-13  M → Q    RP 29%   V 1.7%     buy quarter again
2026-01-28  Q → U    RP 23%   V 3.5%     vol spike → USD
                                          (currently in USD)
```

Six trades in 19 months. Every trade has a clear, readable reason.

---

## Robustness

### Walk-forward — this is the important test

Train on first 60%, test on last 40%, 100 configurations:

| | mean OOS | beat gold OOS |
|---|---|---|
| **Layer 2 only** (20 cfg) | 1.621× | **4 / 20** |
| **With Layer 1** (80 cfg) | **1.898×** | **56 / 80** |
| hold gold | 1.739× | — |

**Adding Layer 1 improves mean out-of-sample result by +0.276×.** This is the
strongest evidence in the whole project: the layers are genuinely complementary,
not two fits to the same noise.

Note the top train configs: every `volOFF` variant that won in training **lost**
in testing (1.550× vs gold 1.739×), while the same A/B pair with Layer 1 enabled
**won** (1.875×). Layer 2 alone overfits; Layer 1 rescues it.

### Cost sensitivity

| cost/leg | wealth | × gold |
|---|---|---|
| 0.5% | 5.239 bn | 1.473× |
| 1.0% | 4.932 bn | 1.387× |
| 2.0% | 4.366 bn | **1.228×** |
| 3.0% | 3.860 bn | 1.086× |

**Survives to 3%/leg.** Only 6 trades, so friction is not the binding constraint.

### Volatility threshold — plateau check

| volHi | 1.5 | 2.0 | 2.5 | 3.0 |
|---|---|---|---|---|
| 3.0% | 1.173 | 1.128 | 1.146 | 1.101 |
| **3.3%** | **1.228** | 1.181 | 1.200 | 1.153 |
| 3.5% | 1.080 | 1.039 | 1.056 | 1.014 |
| 3.8% | 1.370 | 1.234 | 1.254 | 1.252 |
| 4.2%+ | 1.133 | 1.133 | 1.133 | 1.133 |

⚠️ **Use 3.3%, not 3.8%.** The 3.8–4.0% band scores higher (1.370×) but
`vol ≥ 4.0%` fires on **exactly 1 session in 375** — that is a single-point fit,
not a rule. At 3.3% the trigger fires across **two independent episodes**
(Apr–May 2025 and Jan–May 2026), which is a real signal with weak but genuine
support.

I am deliberately recommending the **lower-scoring, better-supported** threshold.

---

## Why the layers combine well

They are **economically orthogonal**:

- **Layer 2** harvests a *mean-reverting spread* — the ربع bubble oscillates
  13%→76% and always comes back. It is a relative-value trade inside gold, and
  it is indifferent to the gold price level.
- **Layer 1** responds to a *directional regime* — when domestic gold turns
  violent, the rial-denominated dollar is the safer store. It is indifferent to
  which coin is cheap.

Their trade dates barely overlap, and Layer 1 supplies the exit Layer 2
structurally lacks. Recall the recurring failure in earlier work: Layer 2 alone
ends up "stuck holding quarter with no exit." Layer 1 provides one that does not
depend on the bubble ever recovering.

---

## Operating rules

```
DAILY:
  1. read P_ربع, P_مثقال, P_USD from the dealer board
  2. RP = (P_ربع/1.8288)/(P_مثقال/3.2489) − 1
  3. GV = 30-day stdev of daily مثقال returns

  LAYER 1:
     if GV ≥ 3.3%          → target = USD
     elif holding USD and GV ≤ 1.5% → release to Layer 2
     else                  → Layer 2 decides

  LAYER 2 (only when Layer 1 says "gold"):
     if RP ≤ 31%  → ربع سکه
     if RP ≥ 60%  → مثقال
     else         → hold current

  GATES: Layer 1 min hold 10 sessions; Layer 2 min hold 5 sessions.
```

### Current reading (2026-07-27)

```
RP = 21.6%   (≤31 → Layer 2 wants ربع سکه)
GV = 2.6%    (<3.3 → Layer 1 says gold, no USD)
Backtest state: in USD since 2026-01-28, vol has not yet fallen to 1.5%
```

→ **Layer 1 is close to releasing.** When GV drops below 1.5%, rotate USD → ربع سکه.

---

## Honest limitations

1. **Six trades.** The direction is consistent and walk-forward is positive, but
   the sample is small. Treat 1.23× as an estimate, not a promise.
2. **Layer 1 rests on two episodes** (2025-04, 2026-02/05), both in an unusually
   volatile period including the war. The underlying correlation (gold vol →
   USD outperformance, +0.769) has only ~7 independent observations.
3. **Mint year.** tgju's `rob` blends ۱۳۸۶/۱۴۰۳/۱۴۰۴, which trade up to 1m toman
   apart. Confirm which coin you are quoted before acting on RP.
4. **The war regime is live.** Both layers were calibrated partly inside it.

**Recommendation: run at reduced size for one full RP cycle** (RP back above
60%, then below 31%) before committing full capital. That is roughly 6–12 months
and would give two more independent observations of each layer.

Data: `data/qm_full.csv`, `data/usd_irr.csv`. Code: `combined.py`.
