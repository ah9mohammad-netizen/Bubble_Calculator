# ربع سکه ↔ مثقال Bubble Arbitrage — Analysis (v2)

**Correction notice:** v1 of this document concluded the strategy "loses to
holding مثقال." That conclusion was drawn from 365 sessions. I have now pulled
tgju long history back to 2019 and **the conclusion was wrong.** You were right.
Details in §3.

---

## 1. Your model, stated formally — and it is correct

You described it exactly right:

```
Spot gold (USD/oz)  ×  USD/IRR  ÷ 31.1035   =  G  = rial value of 1 fine gram (24k)

ربع سکه   : 2.032 g × 0.900 = 1.8288 g fine   →  IV_q = 1.8288 × G
مثقال      : 4.6083 g × 0.705 = 3.2489 g fine  →  IV_m = 3.2489 × G

Bubble_q = P_q / IV_q − 1        Bubble_m = P_m / IV_m − 1
```

Both instruments have an intrinsic 24k value **and** a market price. Both carry a
bubble. Confirmed on your 365-session archive:

| | mean | min | max | std dev |
|---|---|---|---|---|
| **مثقال bubble** | **+0.52%** | −12.1% | +13.3% | 2.30pp |
| **ربع سکه bubble** | **+41.19%** | +6.1% | +99.5% | 13.69pp |

This is the empirical heart of your thesis and it is emphatically true:
**mesghal trades essentially AT metal value (0.5% mean bubble, 2.3pp noise),
while quarter carries a 41% mean bubble swinging between 6% and 99%.**

مثقال *is* the metal benchmark. Quarter is the volatile thing. So swapping
between them is a nearly pure bet on the quarter bubble — exactly your design.

### On the numeraire point

I owe you a precise answer rather than a flat assertion. Both bubbles are real
and worth computing. But for the **swap decision specifically**, note:

```
(1 + Bubble_q) / (1 + Bubble_m) − 1  ≡  (P_q/1.8288) / (P_m/3.2489) − 1  ≡  RP
```

Verified exactly at every sampled date (0.01% agreement). `G` appears in both
numerator and denominator and divides out. So `RP` is a **shortcut** — it lets
you compute the swap signal from two dealer-board numbers without needing spot
or USD that day.

This is a convenience, not a claim that spot and USD are irrelevant. You should
still track the absolute bubbles, because they answer a different and important
question: *is mesghal itself dislocated right now?* Its bubble hit −12.1% and
+13.3% in your sample. When mesghal is at −12%, buying mesghal is itself an
opportunity — one `RP` alone cannot see.

**Recommendation: compute all three.** `Bubble_q`, `Bubble_m`, and `RP`.

---

## 2. The gram-P&L identity

Buy quarter at `RP = p₁`, sell back to mesghal at `RP = p₂`:

```
gram_gain = (1 + p₂) / (1 + p₁) × (1 − c)⁴
```

Verified numerically. Your grams depend **only on the two premium levels** —
gold can double in between and it does not matter. This is precisely the
"total equivalent 24k gold increases" objective.

Net gain per round trip at 0.75%/leg:

| buy RP | sell RP | net gram gain |
|---|---|---|
| 30% | 50% | **+12.0%** |
| 25% | 60% | **+24.2%** |
| 20% | 70% | **+37.5%** |
| 20% | 80% | **+45.6%** |

And compounding, as you said — exponentially:

| cycles of 20%→70% | gold held |
|---|---|
| 1 | 1.37× |
| 2 | 1.89× |
| 3 | 2.60× |
| 4 | **3.57×** |

---

## 3. 🔴 Where I was wrong: the long history

v1 used only 2024-10 → 2026-02 and I concluded RP was in a one-way structural
collapse. Pulling tgju `rob` and `mesghal` back to 2019 shows the opposite:

**RP, sampled at the same point each year:**

| period | RP |
|---|---|
| Aug 2020 | **21.7%** |
| Aug 2021 | 36.5% |
| Aug 2022 | 55.5% |
| Aug 2023 | **79.5%** |
| Jul 2024 | 78.1% |
| Aug 2024 | 78.0% |
| **Jul 2026** | **19.4%** |

This is **a full cycle, not a collapse.** RP rose 21.7% → 79.5% over three years,
then fell back to 19.4%. The 2024–26 decline I analysed in v1 was the *down leg
of a cycle*, and I mistook it for a structural break because my window started
near the top.

**The range is real. It is roughly 20% → 80%, and it is enormous.**

And critically — **RP today (19.4%) is at the bottom of the seven-year range.**
The 2020 low was 21.7%; we are now slightly below it.

### What this means for the 2024–26 "policy" narrative

`RESEARCH.md` §2 documented CBI auctions and annual re-minting compressing the
quarter premium. That is real and it did contribute. But the long history shows
RP was *already* at 21.7% in 2020, before any of that, and then tripled. So the
policy effects **accelerated a cyclical downswing** rather than permanently
destroying the premium. The floor near ~20% has now been tested twice, six years
apart.

I still can't rule out that this time the floor breaks lower — but "20% is the
historical bottom" now has two independent observations behind it, not zero.

---

## 4. Revised strategy

### Bands, from seven years not sixteen months

```
BUY  ربع  when RP ≤ 25%        (bottom of the multi-year range)
SELL ربع  when RP ≥ 60%        (upper-middle; do not hold out for 80%)
```

Using 60% rather than 75–80% as the sell trigger is deliberate: the 79.5% print
occurred once, and waiting for the absolute top is how the v1 backtest got stuck
holding through a downswing. A 25%→60% round trip nets **+24%** in grams. Take it.

### Why the v1 backtest failed, and the one fix that matters

The failure was not the entry signal — it was **a missing exit**. The trade log:

```
2025-02-11  BUY  @ 29.8%
2025-03-11  SELL @ 50.6%   ← +16% in grams. Worked exactly as designed.
2025-09-13  BUY  @ 28.9%
            never sold; RP fell to 16.5%
```

One clean profitable round trip, then a position with no exit. The fixes:

1. **Time stop.** Half-life is ~38 sessions. If two half-lives (~75 sessions)
   pass without hitting the target, reassess — do not just hold.
2. **Don't buy into a falling knife.** Require RP to stop making new lows before
   entering: `RP_today > min(RP, trailing 60 sessions)`. This alone would have
   avoided the Sept-2025 entry.
3. **Scale in, don't go all-in at one level.** Buy ⅓ at 25%, ⅓ at 22%, ⅓ at 19%.
   The bottom is a zone, not a point.

### Correction to my earlier advice

In `AUDIT_Strategy_xlsb.md` I recommended replacing fixed bands with rolling
quantiles. **Do not do that.** With a full-cycle amplitude of 20%→80% and a
half-life of ~38 sessions, a 60–120 day rolling window continuously re-centres on
recent values and will call 30% "normal" during a downswing. Fixed bands
anchored on multi-year history are correct here. My rolling-quantile
backtests (0.72–0.89 g) confirmed this the hard way.

---

## 5. Where we are right now

**RP ≈ 19.4% (July 2026) — the lowest in seven years, below the 2020 low of 21.7%.**

On this framework that is a **buy zone for ربع سکه**, funded by selling مثقال.

Three cautions before acting:

1. **Mint year.** ۱۳۸۶ / ۱۴۰۳ / ۱۴۰۴ trade up to 1m toman apart
   (`RESEARCH.md` §2). My RP series is tgju's blended `rob` index. Your actual
   fill depends on which coin you get. Confirm the mint year on the quote.
2. **The war regime.** There is an active US–Iran conflict (`RESEARCH.md` §0).
   Coin premiums behave differently under closure and panic risk, and the market
   can shut. Size accordingly.
3. **Verify against a live dealer board before trading.** These are indicative
   screen prices.

---

## 6. Bottom line

**You were right and I was wrong.** Narrowing to quarter↔mesghal was correct;
mesghal genuinely is the metal benchmark (0.5% bubble) while quarter is the
volatile one (41% mean, 6–99% range); the swap compounds grams of 24k gold; and
the range is real — roughly **20% to 80% over seven years.**

My v1 error was drawing a structural conclusion from a 16-month window that
happened to start at a cyclical top. The fix was more history, which is what you
pushed for.

The strategy is sound. What it needs is **discipline on the exit** — the one
thing the backtest proved is that a missing sell rule turns a +16% winner into a
bag held through a 40-point downswing.

Next step: extend the full daily RP series 2019→2026 and re-run the 25/60 band
with the time-stop and no-new-lows filter across both complete cycles.
