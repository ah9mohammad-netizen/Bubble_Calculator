# Would changing the parameters improve anything?

**Short answer: no.** The current settings are already the global optimum on
this data, and every attempt to improve them either fails out-of-sample or is
fitted to a single episode.

Search performed on the full 945-session window (2022-10-13 → 2026-07-27),
always reported as **× holding ربع سکه**, and always split into two halves so
that a number that only works in one regime is visible.

---

## 1. Layer 2 bands (A, B) — 90 combinations

| A | B | FULL | H1 | H2 | trades |
|---|---|---|---|---|---|
| **0.60** | **0.31** | **1.47** | 0.92 | 1.60 | 3 |
| 0.65/0.70/0.75 | 0.31 | 1.47 | 0.92 | 1.60 | 3 |
| 0.60 | 0.34 | 1.39 | 0.92 | 1.51 | 3 |
| 0.70 | 0.15 | 1.33 | 0.92 | 1.45 | 1 |

**The current (0.60, 0.31) is already the joint best of all 90.** There is
nothing to gain by retuning.

Two things worth noting:

- **90/90 combinations beat holding the coin overall** — the edge is not
  sensitive to the exact numbers, which is a good sign.
- **0/90 beat it in *both* halves.** Every single setting loses in
  2022–2024. That is not a tuning problem (see §5).

`A` is flat from 0.60 to 0.85 — a plateau, not a spike. Good.

## 2. Minimum hold — no effect

0, 3, 5, 10, 20 sessions all give **identical** results (1.47). Only at 40+
does it start to hurt (1.40). The rule fires so rarely that the gate is
almost never binding.

## 3. Layer 1 volatility thresholds — 30 combinations

| VH | VL | FULL | H1 | H2 | trades |
|---|---|---|---|---|---|
| 0.040 | 0.016 | 1.54 | 0.96 | 1.60 | 5 |
| 0.033 | 0.020 (current) | 1.40 | 0.80 | 1.74 | 6 |
| — | Layer-2 only | 1.47 | 0.92 | 1.60 | 3 |

`VH = 4.0%` appears to be an improvement (1.54 vs 1.47). **It is not.**

```
VH=4.0% fires on 31 sessions = ONE episode, 2023-03-15 → 2023-07-03
```

Raising the threshold to 4.0% and dropping the exit to 1.6% simply moves the
2023 exit date from May to July, dodging part of the loss that the 3.3%
setting incurred. It is **fitting a single trade's exit date.** At `VH = 4.5%`
the rule never fires at all.

> Only **10/30** Layer-1 settings beat doing nothing, and the ones that "win"
> do so on a one-episode sample. This reinforces the earlier conclusion:
> **Layer 1 should not be presented as part of the strategy.**

## 4. Volatility window

| window | FULL | H1 | H2 |
|---|---|---|---|
| 20 | 1.11 | 0.88 | 1.26 |
| 45 (current) | 1.40 | 0.80 | 1.74 |
| 90 | 1.47 | 0.92 | 1.60 |

Window 90 scores best only because it makes Layer 1 stop trading — it
converges to the Layer-2-only result. Another way of saying Layer 1 adds nothing.

## 5. Structurally different rules — all worse

Not just retuned thresholds, genuinely different logic:

| Variant | FULL | H1 | H2 | trades |
|---|---|---|---|---|
| **Fixed bands (current)** | **1.47** | 0.92 | 1.60 | 3 |
| Rolling quantile, w=250 [.25,.75] | 0.91 | 0.85 | 1.04 | 7 |
| Rolling quantile, w=120 [.25,.75] | 0.87 | 0.89 | 0.93 | 17 |
| RP z-score, w=250, \|z\|>1.5 | 1.00 | 0.95 | 1.04 | 3 |
| RP momentum, 20-session | **0.07** | 0.18 | 0.37 | 72 |
| RP momentum, 60-session | 0.30 | 0.44 | 0.71 | 38 |

- **Adaptive bands (quantile / z-score) fail** for the reason found earlier:
  in a downtrend they keep re-labelling ever-lower premiums as "normal", so
  they buy the coin too early and sell too late.
- **Momentum is catastrophic** (0.07× = you lose 93%). This confirms the
  bubble is *mean-reverting*, not trending — trading it the other way round
  destroys capital. Useful as a sanity check that the core thesis is right.

## 6. Why the first half fails — and why no parameter can fix it

```
H1 (2022-10 → 2024-08):  RP ranged 54.7% – 120.8%   → never below 31%
H2 (2024-08 → 2026-07):  RP ranged 13.0% –  84.2%   → 3 trades
```

**In H1 the buy signal never fired.** The coin's bubble stayed permanently
elevated between 55% and 121% and never mean-reverted. The strategy simply sat
in مثقال the whole time, and مثقال lagged the coin by 23.8pp in that period
(+166.7% vs +190.5%).

That is not a parameter failure. **No band setting can harvest a reversion
that does not occur.** You could only "fix" H1 by choosing bands that fit that
specific regime — which would then break H2.

This is the honest characterisation of the strategy:

> It is a **conditional** edge. It pays when the coin's bubble actually
> oscillates. In a regime where the bubble stays permanently rich, it
> underperforms simply holding the coin.

## 7. The one lever that does work: execution cost

| cost/leg | FULL | H2 |
|---|---|---|
| 0.5% | **1.62** | 1.75 |
| 1.0% | 1.57 | 1.70 |
| 2.0% (assumed) | 1.47 | 1.60 |
| 3.0% | 1.39 | 1.51 |

Cutting the round-trip cost from 2% to 0.5% adds **+0.15×** — more than any
parameter change on this list, and it does not rely on fitting anything.

**Recommendation: stop tuning parameters. Go find cheaper execution.**
Gold ETFs (صندوق طلا) at 0.3–0.5% and online آب‌شده platforms at 1.5–2.0%
round trip are the highest-value unexplored lever in this whole project.
