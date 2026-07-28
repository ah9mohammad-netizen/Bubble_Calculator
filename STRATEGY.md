# Iran Gold/FX Bubble Arbitrage — Strategy Framework v0.2

> Status: **draft for discussion.** No code yet. Goal is a decision system robust enough
> to be worth automating.

## Locked design decisions

| Decision | Choice | Consequence |
|---|---|---|
| Execution | **Advisory** — bot signals, human trades with dealers | Human is the final risk gate; signals must carry limit prices, not just direction |
| Universe | **Core four**: آب‌شده, امامی, ربع, USD | 3 Layer-A spread pairs + 1 regime ratio. Tight enough to validate honestly |
| Action cadence | **Weekly / on-signal** | Matches physical friction. But see §4.0 — compute daily, act weekly |
| Numeraire | **Grams of pure gold** | Non-negotiable, applies to the objective function too |

Advisory mode changes two things in the bot's favour: the cost model can use
*actual* dealer quotes at decision time rather than scraped indicative prices,
and the §5 vetoes get a human backstop. It also caps realistic turnover — which
is why weekly is the right cadence, not a compromise.

---

## 0. The one rule that shapes everything: the numeraire

Profit is **not** growth in rials. Profit is **growth in grams of pure gold held.**

Define the account unit:

```
NAV_g = Σ_i  (units_i × liquidation_price_i(rial)) / P_pure_gram(rial)
```

Everything — P&L, drawdown, Sharpe, the backtest objective — is denominated in
`NAV_g` (grams of 24k gold).

Two useful consequences:

1. **Buy-and-hold melted gold becomes the zero line.** A strategy that returns
   +0.0% in grams did nothing. This kills the illusion of "we made 40% this year"
   in a 40% inflation year.
2. **USD is a risk position, not cash.** Holding USD is an active bet that
   `XAU/USD` falls or that the rial devalues faster than gold rises. There is no
   risk-free asset in this system. Every sleeve is a bet.

A secondary reporting numeraire (USD) should be tracked but never optimized against.

---

## 1. Instrument universe

| Sleeve | Instrument | Nominal wt (g) | Fineness | Pure gold (g) | Notes |
|---|---|---|---|---|---|
| A | آب‌شده / مثقال | 4.6083 | 0.705 (17c) | 3.2489 | The metal benchmark. Lowest friction. |
| B | سکه امامی (طرح جدید) | 8.13598 | 0.900 | 7.3224 | Deepest coin liquidity. |
| C | ربع سکه | 2.03399 | 0.900 | 1.8306 | Structurally largest bubble. |
| D | USD (free market) | — | — | — | Proxy: cash نقدی, or USDT on Nobitex/Wallex. |

Out of scope for v1 (revisit after Layer A validates): نیم سکه, گرمی,
طرح قدیم, 18k gram (طلای ۱۸ عیار), gold ETFs (صندوق طلا), سکه آتی futures on IME.

> Note on the deferred futures leg: سکه آتی term structure is a direct read on
> the market's *expected* future bubble and would be the single strongest
> addition to Layer A. Worth revisiting the moment the core four are working.

> ⚠️ Coin specs must live in a config file, not hardcoded. Old-design (طرح قدیم)
> Bahar Azadi trades as a separate line with its own bubble and must not be
> pooled with طرح جدید.

---

## 2. Intrinsic value engine

Global anchor:

```
P_pure_gram_intrinsic = (XAU_USD / 31.1035) × USD_IRR_free
```

Per-instrument intrinsic value:

```
IV_i = pure_gold_g_i × P_pure_gram_intrinsic
```

Bubble, three ways — all three are needed:

```
Bubble_abs_i  = P_market_i − IV_i                      # rials, for headlines only
Bubble_pct_i  = P_market_i / IV_i − 1                  # the working number
Bubble_z_i    = (Bubble_pct_i − μ_i) / σ_i             # the tradeable number
```

`μ_i, σ_i` = EWMA mean/std of `Bubble_pct_i` over ~90 sessions, with a slow
2-year baseline for structural drift.

**Why the z-score is non-negotiable:** ربع سکه carries a permanent structural
premium (minting cost per gram + retail lot-size demand) that has historically
run far above امامی's. Comparing raw bubble percentages between them produces a
permanent, wrong "sell ربع" signal. Only the *deviation from each coin's own
normal* is tradeable.

---

## 3. Signal layers

The framework is deliberately split into three orthogonal decisions.

### Layer A — Coin vs metal (intra-gold relative value)

Trades: B↔A, C↔A, C↔B. Pure grams-of-gold arbitrage, zero directional exposure.

```
S_CB = Bubble_z(ربع) − Bubble_z(امامی)
S_BA = Bubble_z(امامی) − Bubble_z(آبشده)
```

Mean-reverting by construction. Enter when `|S| > entry_band`, exit toward 0.
This is the **highest-conviction, lowest-risk** part of the book — it is a spread
trade inside a single asset class and it compounds grams directly.

Half-life of coin-bubble mean reversion needs measuring; my prior is 2–6 weeks
absent policy shocks.

### Layer B — Gold vs USD (the regime decision)

Invert the intrinsic formula to back out the dollar the *gold market* is pricing:

```
USD_implied = P_pure_gram_market × 31.1035 / XAU_USD
R = USD_implied / USD_free
```

- `R > 1` → domestic gold is rich against the dollar → rotate toward **D (USD)**
- `R < 1` → domestic gold is cheap → rotate toward **A (metal)**

This single ratio is the cleanest expression of "sometimes USD is better than
gold." It already nets out global gold moves, so it isolates the purely domestic
premium. Trade `Z(R)`, not `R`, for the same structural-drift reason as §2.

### Layer C — Momentum / lead-lag overlay

Rial devaluation shocks hit USD first; domestic gold catches up with a lag of
days. So `R` is not purely mean-reverting — it trends during shocks.

Overlay rule: **suppress the Layer-B mean-reversion signal when USD momentum is
in the top decile.** Concretely, if 5-day USD return z-score is extreme and `R`
is *falling* (gold lagging), do not sell gold to buy USD — the catch-up trade is
about to fire. Mean reversion and momentum must be gated against each other or
they will cancel out and pay the spread both ways.

---

## 4. From signals to positions

### 4.0 Daily signal, weekly action

Compute every signal **daily**; permit trades **weekly** (fixed session, e.g.
Saturday open) plus an **on-signal override** when `|z|` breaches a wide
emergency band or a §5 veto fires.

Rationale: weekly *sampling* would alias out the 2–6 week mean-reversion cycle
we are trying to harvest and would miss auction announcements entirely. Weekly
*acting* respects physical friction. These are different things and conflating
them is a common way to destroy a real edge.

**No binary flips.** Binary rotation across four sleeves with 0.5–1.5% round-trip
costs is a guaranteed slow bleed. Use continuous target weights:

```
w_target = softmax( λ_A · s_A + λ_B · s_B + λ_C · s_C )   subject to constraints
```

Execution gates, all mandatory:

1. **Cost gate.** Only rebalance the portion of the trade whose expected edge
   exceeds `k × round_trip_cost`, with `k ≈ 2`.
2. **Hysteresis.** Entry band strictly wider than exit band. Never rebalance on
   a signal that just crossed zero.
3. **Minimum holding period** per sleeve (candidate: 3 sessions) to stop churn.
4. **No-trade zone** around every current weight (±5–8pp).

Realistic cost stack per leg (to be calibrated from actual dealer quotes):

| Leg | Bid/ask + fee |
|---|---|
| آب‌شده | ~0.3–0.7% |
| سکه (امامی/ربع) | ~0.5–1.5%, worse for ربع |
| USD cash | ~0.3–0.8% |
| USDT proxy | ~0.2–0.5% + on/off-ramp |

Costs are *asymmetric and state-dependent* — spreads blow out exactly when
signals are strongest. Model cost as a function of realized volatility, not a
constant.

---

## 5. Risk & regime overrides

These are hard vetoes that sit above the signal engine:

- **CBI / مرکز مبادله coin auctions (حراج سکه).** Announced auctions
  systematically crush coin bubbles. An auction calendar is a *first-class data
  input*, not a footnote. Any long-coin-bubble position must be flat or reduced
  into an announced auction.
- **Market closure.** Fridays, public holidays, and discretionary shutdowns of
  the gold market during extreme volatility. The bot must never assume it can
  exit.
- **Stale/wide quotes.** If dealer spread > threshold or the last tick is older
  than N minutes, freeze all trading. In Iran the "price" during a panic is
  frequently not a real executable price.
- **Policy/news shocks** — negotiations, sanctions, budget/FX-rate announcements.
  At minimum a manual kill switch; ideally a volatility-triggered de-risk.
- **Physical risks that don't exist in normal markets:** counterfeit coins,
  unsealed coins (سکه پلمپ vs باز) trading at a discount, physical custody,
  dealer counterparty risk. These cap position size per sleeve regardless of what
  the signal says.
- **Seasonality.** Coin bubbles inflate into Nowruz and wedding season, deflate
  after. Include a seasonal term or at minimum size down against it.

---

## 6. What the backtest must prove

Objective: **CAGR in grams**, not rials.

Mandatory reporting:
- Grams CAGR, max drawdown in grams, worst 3-month grams drawdown
- Same metrics vs three baselines: 100% آب‌شده, 100% امامی, 50/50 gold/USD
- Turnover, total cost paid in grams, and **net-of-cost vs gross-of-cost gap**
  (if that gap is more than ~40% of gross edge, the strategy is not real)
- Performance split by regime: rial-stable vs rial-crisis periods

Protocol discipline:
- Walk-forward only. Parameters fitted on a trailing window, tested forward.
- Model execution at the *far* side of the spread, always.
- Test robustness to ±50% cost assumptions — if it dies, it was never alive.

---

## 7. Data layer (before anything else works)

Nothing in §2–§4 is computable without a clean series. Required daily (ideally
intraday):

- `XAU/USD` — global, easy
- `USD/IRR` free market — tgju, alanchand, bonbast; and/or USDT/IRT from Nobitex
- `مثقال آب‌شده` bid/ask
- `سکه امامی` / `ربع سکه` bid/ask
- Auction calendar + announcements

Hard problems to solve early: these sources publish *indicative* prices, not
executable ones, and they disagree. The gap between the screen price and the
price a dealer actually fills is where this strategy lives or dies. Any backtest
built on mid-quotes from a scraping site will be optimistic.

---

## 8. Open design questions

**Resolved:** execution = advisory; universe = core four; cadence = daily
signal / weekly action.

**Still open:**

1. **Cash leg.** Is rial ever an allowed holding, or is the book always 100%
   invested across A–D? (Recommendation: always invested. Rial is a guaranteed
   loss in the numeraire.)
2. **Capital scale.** Determines whether ربع سکه is even liquid enough, and
   whether physical custody is viable. Also sets the minimum tradeable lot —
   with the core-four universe, one امامی is a large indivisible ticket for a
   small book, and lot granularity may dominate the optimizer.
3. **History depth available.** Half-life estimation and z-score baselines need
   3+ years; ideally through a full devaluation cycle.
4. **Which USD, exactly?** اسکناس نقدی, حواله, and USDT trade at meaningfully
   different prices. The series used for `USD_free` in §2 defines the entire
   bubble calculation — it must be the one you can actually transact in.
5. **سکه پلمپ vs باز** — do we track them as one line or two?

---

## 9. Build order

```
1. Data layer + storage          ← nothing works without this
2. Intrinsic value + bubble engine, validated against known historical episodes
3. Bubble statistics: half-life, structural means, correlation matrix
4. Layer A backtest alone (lowest risk, most likely to be real)
5. Layer B, then Layer C overlay
6. Cost model calibrated from real quotes
7. Portfolio construction + gates
8. Paper trading / advisory mode
9. Automation only where legs are genuinely automatable
```

Steps 1–4 are where the truth is. If Layer A doesn't survive an honest
cost model, nothing downstream will.
