# Basis Z-score — world-parity gate

Added to the bot as an **indicator paragraph**, not (yet) an executing rule.
Reason is in "Validation" below.

## Definition

```
FairValue = XAU/USD ÷ 31.1035 × USD/IRR × 3.24885
Basis     = Mesghal_market / FairValue − 1
Z         = (Basis − mean(Basis, 75)) / stdev(Basis, 75)
```

`FairValue` is what one مثقال *should* cost if Iranian gold tracked the world
price and the free-market dollar exactly. **Basis** is the gap.

- **Positive basis** — local mesghal is expensive vs global gold + USD
- **Negative basis** — local mesghal is at a discount

## State machine (as specified)

```
default state       : GOLD
GOLD -> USD  when   : z > +1.75 for 3 consecutive closes, and
                      >= 30 observations since the last transition
USD  -> GOLD when   : z < +0.50 for 3 consecutive closes, and cooldown met
+0.50 <= z <= +1.75 : no new trade, keep prior state
```

## Measured behaviour, 2025-02-07 → 2026-07-27 (244 sessions)

| metric | value |
|---|---|
| basis range | −8.8% … +15.1% |
| basis median | +0.3% |
| z range | −4.04 … +3.18 |
| z median | +0.01 |
| sessions with z > +1.75 | **3** |
| longest consecutive run above +1.75 | **1** |
| transitions fired | **0** |

## ⚠️ Validation — read before trusting it

**The rule never fired once in 244 sessions.** Not because the threshold is
never reached — z hit +3.18, +2.99 and +1.76 — but because it never stayed
above +1.75 for **three consecutive closes**. Every breach was a single day.

That is the persistence filter doing exactly what it was designed to do. But
it means:

1. **Zero trades = zero evidence.** I cannot tell you this rule makes or loses
   money, because on the data I have it has never traded. The spec's "2–4
   switches per year" was not reproduced.
2. **The sample is short.** 244 sessions of overlap, of which only 169 have a
   z-score at all (the first 75 are consumed by the rolling window).
3. **Spot history is the binding constraint.** `master.csv` had no XAU column;
   I pulled 420 records of tgju `ons` to build this. Extending to the full
   6.4-year window needs ~25 more paged fetches.

**Therefore the bot displays z but does not act on it.** Layer 1 (vol90) and
Layer 2 (RP) still drive the position. The z paragraph is decision *support*.

If you want it to execute, say so — but I'd want either more history or a
relaxed persistence requirement (e.g. 2 closes) first, and I'd want to see it
produce a non-zero number of trades before wiring it to real money.

## Where it appears

`/status` and the daily digest gain:

```
  basis  -0.7%      vs world parity
  z     +0.27      NORMAL
  ········◆|·······|········
         0.50    1.75
  cheap vs world   rich vs world
  gate: GOLD
```

## Code

`bot/strategy.py`: `fair_value_mesghal()`, `basis()`, `basis_z()`, `z_zone()`,
`z_decide()`. Constants `Z_WINDOW=75`, `Z_ENTER_USD=1.75`, `Z_EXIT_USD=0.50`,
`Z_PERSIST=3`, `Z_COOLDOWN=30`.

Gate state persists in the volume as `z_state` / `last_z_date`, so persistence
and cooldown survive restarts.

`bot/seed_history.csv` now carries a `spot` column (244 of 495 rows), so the
z-score is live from first boot instead of needing a 75-day warm-up.
