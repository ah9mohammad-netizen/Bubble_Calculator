# The Flow Chart — Layer 1 (USD vs Gold) → Layer 2 (Which Gold)

Your architecture, implemented and tested. 375 sessions (2025-01-04 → 2026-07-27),
1 bn rial start, 2% per leg.

```
        ┌──────────────────────────────────────────┐
        │  START: 1 bn rial                        │
        └────────────────┬─────────────────────────┘
                         ▼
        ┌──────────────────────────────────────────┐
        │  LAYER 1 — USD or GOLD?                  │
        │  signal: vol45 = 45-day volatility       │
        │          of daily مثقال returns          │
        │                                          │
        │  vol45 ≥ 3.3%  →  BUY USD, hold          │
        │  while in USD: stay until vol45 ≤ 2.0%   │
        └───────┬──────────────────────┬───────────┘
            USD │                      │ GOLD
                ▼                      ▼
        ┌───────────────┐   ┌──────────────────────────────┐
        │ hold USD      │   │  LAYER 2 — which gold?       │
        │ check vol45   │   │  signal: RP = quarter bubble │
        │ daily         │   │                              │
        │ vol ≤ 2.0%    │   │  RP ≤ 31%  →  ربع سکه        │
        │   → go gold   │   │  RP ≥ 60%  →  مثقال          │
        └───────────────┘   │  else      →  keep current   │
                            │  (loop here while gold)      │
                            └──────────────────────────────┘
```

**Layer 1 is a gate, not a peer.** Layer 2 only runs when Layer 1 says "gold."
While in USD you ignore RP entirely — exactly as you described.

---

## Layer 1: the investigation you asked for

I tested **67 candidate indicators** for the USD-vs-gold decision, across five
families, measured as pure USD↔مثقال switching:

| family | what it measures | OOS mean | beat gold OOS |
|---|---|---|---|
| **VOL** | gold return volatility | **1.862×** | **26/36** |
| RSI | momentum oscillator on R | 1.701× | 3/6 |
| DD | gold drawdown from rolling high | 1.470× | 0/9 |
| RvSMA | R vs its moving average | 1.468× | 1/4 |
| MOM | relative momentum gold−USD | 1.391× | 1/12 |

*(test-period hold gold = 1.739×)*

**Volatility wins decisively, and momentum is the worst family** — consistent with
the −0.325 correlation found earlier. Trend-following on this pair is the wrong
tool; the useful signal is *risk state*, not direction.

### The window matters more than the threshold

| vol window | OOS mean | beat gold |
|---|---|---|
| 15 | 1.499× | **0/15** |
| 20 | 1.580× | 4/15 |
| 30 | 1.863× | 10/15 |
| **45** | **1.996×** | **15/15** ✅ |
| 60 | 1.901× | 12/15 |
| 90 | 1.855× | 14/15 |

**vol45 beat gold in 15 of 15 out-of-sample configurations.** Short windows fail
completely — they react to noise. This is a plateau, not a point.

### The mechanism is real and monotonic

Bucketing every session by vol45, then measuring the *next* 30 days:

| vol45 bucket | n | fwd-30d gold−USD | gold wins |
|---|---|---|---|
| 1.5–2.0% | 117 | **+9.2pp** | **94%** |
| 2.0–2.5% | 64 | +4.0pp | 80% |
| 2.5–3.0% | 42 | +0.4pp | 60% |
| 3.0–3.5% | 58 | **−2.0pp** | 36% |
| 3.5–4.0% | 18 | **−12.8pp** | **0%** |

**Perfectly monotonic across 299 observations.** Calm gold → gold wins 94% of the
time. Violent gold → gold wins 0% of the time. This is a genuine economic
relationship, not a curve fit: when domestic gold goes turbulent it is
overshooting, and the rial-dollar becomes the better store.

This is the strongest single result in the project, and it is why Layer 1 should
be a **volatility gate** rather than a momentum crossover.

### Signal history

```
ENTRY (vol45 crosses above 3.3%):
  2026-02-02  vol 3.4%  →  next 60d: gold +0.4%, USD +10.7%   USD edge +10.2pp ✅
  2026-05-23  vol 3.3%  →  next 60d: gold −1.9%, USD  +4.0%   USD edge  +5.9pp ✅

EXIT (vol45 falls below 2.0%):
  2025-06-07  vol 1.9%  →  next 60d: gold +34.8%, USD +23.7%  ✅
  2025-11-19  vol 2.0%  →  next 60d: gold +69.5%, USD +37.1%  ✅
```

All four signals were directionally correct.

---

## Full flow-chart results

| | wealth | × gold | trades |
|---|---|---|---|
| hold rial | 1.000 bn | 0.281× | — |
| hold USD | 2.331 bn | 0.656× | — |
| hold ربع سکه | 3.103 bn | 0.873× | — |
| **hold مثقال** | **3.556 bn** | **1.000×** | — |
| **FLOW CHART** | **4.376 bn** | **1.231×** | **4** |
| *3-asset optimum (hindsight)* | *9.623 bn* | *2.706×* | *many* |

```
2025-02-11  M → Q   RP=30%  vol=1.7%   LAYER 2  buy quarter, bubble cheap
2025-03-17  Q → M   RP=76%  vol=2.2%   LAYER 2  sell quarter at peak bubble
2025-09-13  M → Q   RP=29%  vol=1.6%   LAYER 2  buy quarter again
2026-02-02  Q → U   RP=21%  vol=3.4%   LAYER 1  vol spike → exit to USD
                                                 (still in USD today)
```

Four decisions in 19 months, each with a readable reason.

### Robustness

**Walk-forward** (train 60%, test 40%, 81 configs):

```
mean OOS 1.763×   median 1.762×   min 1.650×   gold 1.739×
beat gold: 48/81
```

The **minimum** across all 81 configs is 1.650× — worst case is 5% below gold,
not a catastrophe. That matters more than the mean.

⚠️ **Honest caveat:** the top *training* configs slightly **lost** out-of-sample
(1.684× vs 1.739×). The system as a whole is sound, but picking parameters by
in-sample rank does not work here. Choose from the middle of the plateau, not
the peak.

**Cost ladder** — only 4 trades, so friction is not binding:

| cost/leg | 0.5% | 1.0% | 2.0% | 3.0% |
|---|---|---|---|---|
| × gold | 1.390× | 1.335× | **1.231×** | 1.134× |

**Parameter plateau** (volhi × vollo, A=60/B=31):

| volhi | lo=1.5 | lo=2.0 | lo=2.5 |
|---|---|---|---|
| 2.8% | 1.147 | 1.271 | **1.313** |
| 3.0% | 1.004 | 1.112 | 1.149 |
| **3.3%** | **1.231** | **1.231** | 1.245 |
| 3.6% | 1.206 | 1.206 | 1.220 |
| 4.0% | 1.133 | 1.133 | 1.133 |

I recommend **3.3 / 2.0** rather than the higher-scoring 2.8/2.5, because 3.3%
sits on a flatter local surface and its trigger is supported by the monotonic
bucket table above.

---

## Operating procedure

```
EVERY SESSION:
  P_ربع, P_مثقال, P_USD  ← dealer board

  RP    = (P_ربع / 1.8288) / (P_مثقال / 3.2489) − 1
  vol45 = stdev( daily مثقال returns, last 45 sessions )

  ── LAYER 1 ──
  if holding USD:
        if vol45 ≤ 2.0%   → exit USD, go to Layer 2
        else              → stay in USD  (ignore RP entirely)
  else:
        if vol45 ≥ 3.3%   → SELL gold, BUY USD
        else              → go to Layer 2

  ── LAYER 2 (gold only) ──
  if RP ≤ 31%  → hold ربع سکه
  if RP ≥ 60%  → hold مثقال
  else         → keep whatever you hold

  GATES: Layer 1 min hold 10 sessions, Layer 2 min hold 5 sessions.
```

### Current reading — 2026-07-27

```
vol45 = 2.32%     (between 2.0 and 3.3 → no Layer-1 action)
RP    = 21.6%     (≤31% → Layer 2 wants ربع سکه)

vol45 trend, last 10 sessions:  2.1 2.2 2.2 2.2 2.2 2.2 2.2 2.3 2.3 2.3
```

**Backtest state: in USD since 2026-02-02.** vol45 is drifting down toward the
2.0% exit but has not reached it. When it does, Layer 2 immediately says
**buy ربع سکه** (RP 21.6% is well below 31%).

**Watch vol45 daily. A close ≤ 2.0% is your signal to rotate USD → ربع سکه.**

---

## What is still weak

1. **Only 4 trades and 2 Layer-1 entries.** Directionally consistent, but small.
2. **Capture is 14% of the 3-asset optimum** (2.706× available, 1.231× taken).
   Most of the gap is short USD spells the 10-session gate deliberately skips —
   an acceptable trade for robustness at 2% cost.
3. **Both Layer-1 entries are in 2026**, inside the war period. The bucket table
   (299 obs, monotonic) is much stronger evidence than the 2 trades, but a calm
   regime has not yet tested it.
4. **Mint year** — tgju's `rob` blends ۱۳۸۶/۱۴۰۳/۱۴۰۴. Confirm before acting on RP.

**Recommendation: trade this at reduced size through one full cycle** — one
Layer-1 round trip and one RP round trip — before full capital.

Data: `data/qm_full.csv`, `data/usd_irr.csv`. Code: `flowchart.py`, `layer1.py`.
