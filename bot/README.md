# Iran Gold / FX Signalling Bot

Telegram bot implementing the two-layer strategy from `FLOWCHART.md`.
Runs 24/7 on Railway, persists to a `/data` volume.

```
LAYER 1  vol45 ≥ 3.3% → USD  ·  while USD, exit when vol45 ≤ 2.0%
LAYER 2  RP ≤ 31% → ربع سکه  ·  RP ≥ 60% → مثقال      (only while in gold)
```

---

## Deploy on Railway — 5 steps

**1 · Push this folder to GitHub**

**2 · New Railway project** → *Deploy from GitHub repo* → pick the repo.
If the bot is in a subfolder, set **Root Directory** = `bot`.

**3 · Add the volume** (this is the important one)

> Service → **Variables** tab → **+ Volume**
> **Mount path:** `/data`

**4 · Set environment variables**

| Variable | Value | Notes |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | `123456:ABC…` | from @BotFather |
| `TELEGRAM_CHAT_ID` | `123456789` | from @userinfobot |
| `DATA_DIR` | `/data` | must match the volume mount |
| `CHECK_INTERVAL_MIN` | `60` | optional |
| `REPORT_HOUR_TEHRAN` | `12` | optional, daily digest hour |

**5 · Deploy.** You should get a "Bot online" message within a minute.
Send `/help` to confirm.

> **If you skip the volume**, the bot still runs but writes to `./data_local`,
> which Railway wipes on every redeploy — you'd lose signal history and
> position state. The volume is what makes it stateful.

---

## Commands

| Command | Does |
|---|---|
| `/status` | Full dashboard — prices, both layers, position, action |
| `/price` | Prices only (fast) |
| `/signal` | What the model says right now |
| `/position` | Current holding + since when |
| `/setpos quarter\|mesghal\|usd` | Sync bot to what you actually hold |
| `/history` | Last 10 signals |
| `/backfill` | Repair/extend price history from tgju |
| `/stats` | Rows stored, volume path |
| `/help` | Strategy, evidence, backtest numbers |

**`/setpos` matters.** The bot starts assuming you hold مثقال. Set it to your
real position on day one or the first signal will be wrong.

---

## What it does automatically

- **Every 60 min** — fetch prices, store them, evaluate both layers.
- **On a position change** — immediate 🚨 alert with reason, prices, and target.
- **Once daily at 12:00 Tehran** — digest, if no signal already fired.

Signals fire once per change, never repeat, and respect the min-hold gates
(10 sessions Layer 1, 5 sessions Layer 2) that stop cost-destroying churn.

---

## Files on the volume

```
/data/prices.csv    date,quarter,mesghal,usd,spot   (seeded with 495 sessions)
/data/signals.csv   every trade signal, with reason
/data/state.json    position, since, min-hold dates, subscribers
```

`prices.csv` ships pre-seeded from `seed_history.csv` (2024-08-03 → 2026-07-27)
so **vol45 is live from the first run** — no 45-day warm-up.

---

## Verification done

The engine was replayed over the seed history and reproduces the backtest in
`FLOWCHART.md` exactly:

```
2025-02-11  MESGHAL→QUARTER [L2]  RP=29.8%  vol=1.58%
2025-03-17  QUARTER→MESGHAL [L2]  RP=76.0%  vol=2.22%
2025-09-13  MESGHAL→QUARTER [L2]  RP=28.9%  vol=1.59%
2026-02-02  QUARTER→USD     [L1]  RP=20.7%  vol=3.36%
```

Also tested: tgju JSON parsing against real payloads, number cleaning
(commas / `</span>` / dashes), upsert-without-clobber, state round-trip,
min-hold gating, USD hysteresis, and cold start with no volatility data.

---

## Current reading (2026-07-27)

```
RP    = 21.6%   ≤ 31%  → Layer 2 wants ربع سکه
vol45 = 2.32%   between 2.0 and 3.3 → no Layer 1 action
```

Backtest state is **in USD since 2026-02-02**; vol45 is drifting toward the 2.0%
release. When it crosses, the bot signals USD → ربع سکه.

---

## Limitations — read before trading

- Only **4 trades** in the tested window. Small sample.
- Layer 1 rests on **2 episodes**, both inside the 2026 war period.
- tgju's `rob` index **blends mint years** ۱۳۸۶/۱۴۰۳/۱۴۰۴ which trade up to
  1m toman apart. Confirm which coin your dealer is quoting.
- Screen prices are indicative, not executable. Costs assume **2%/leg**.
- The bot **signals; it does not trade**. You execute.
