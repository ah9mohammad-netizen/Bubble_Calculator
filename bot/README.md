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

## Troubleshooting a failed deploy

Build config now exists at **both** the repo root and in `bot/`, so the deploy
works whether **Root Directory** is left blank or set to `bot`.

| Symptom in Railway logs | Cause | Fix |
|---|---|---|
| `Nixpacks build failed` / `no start command could be found` | Railway found no `requirements.txt` at the directory it was pointed at | Now fixed — root `requirements.txt` + `Procfile` are committed. Redeploy. |
| `ModuleNotFoundError: No module named 'requests'` | Install phase never ran | Confirm `requirements.txt` is in the directory Railway builds from |
| `MISSING REQUIRED RAILWAY VARIABLES: …` then exit | Env vars unset | Service → **Variables** → add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` → redeploy |
| Healthcheck failed / service marked unhealthy | Port not bound in time | Fixed — the health server binds `0.0.0.0:$PORT` *before* any other startup work |
| Deploys but forgets position after redeploy | No volume attached | Add a volume mounted at `/data` and set `DATA_DIR=/data` |
| `cannot create /data … falling back to ./data_local` | Volume missing or wrong mount path | Mount path must be exactly `/data` |

**Verify a good boot** — the logs should show, in order:

```
INFO [bot] health server listening on 0.0.0.0:8080
INFO [store] seeded prices.csv from .../seed_history.csv
INFO [bot] storage ready: {'prices': 495, ...}
INFO [bot] polling started
```

…and a **"Bot online"** message arrives in Telegram.

You can also hit the service's public URL — it returns JSON:

```json
{"status":"ok","position":"MESGHAL","prices":495,"first":"2024-08-03","last":"2026-07-27","signals":0,"dir":"/data"}
```

After the first successful boot, run **`/setpos`** to sync the bot to what
you actually hold.

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

Plus the optional **Metals Desk** commands (`/now`, `/parity`, `/gates`,
`/ladder`, `/funds`, `/rules`, `/fires`, `/health`, …) when it is switched on.
See [`desk/README.md`](desk/README.md).

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

---

## Optional: the Metals Desk

A second, independent engine lives in [`bot/desk/`](desk/README.md): import
parity for 18k gold, the طلا / پلاتا / اهرم wrappers against their NAV, world
spot, and 33 declarative handbook rules with cooldowns and quiet hours.

**It is off unless you set `ENABLE_DESK=1`.** With the variable unset the bot
above registers no extra commands, starts no extra thread and opens no extra
connection — the only difference is one line in `/stats` saying `desk off`.

When on, it runs on its own thread and its own 15-minute clock, deliberately
separate from the strategy `monitor()` loop, so a slow or blocked Iranian feed
can never delay a trade signal. It stores to `desk.db` on the same volume.

Read `desk/README.md` before enabling — in particular the *Blocked IPs*
section, because Railway's US/EU address is often refused by Iranian hosts.

---

## Railway cost control

Railway bills **RAM-hours + CPU-hours**, not repository size. A always-on
worker is the cost, not the files. Three knobs, all env vars:

| variable | default | effect |
|---|---|---|
| `CHECK_INTERVAL_MIN` | 60 | Minutes between price checks. Set `120` to halve them. |
| `LONGPOLL_SEC` | 50 | Telegram long-poll seconds. Higher = fewer reconnects = less CPU. |
| `ENABLE_COMMANDS` | 1 | Set `0` to drop the command listener and receive only the daily digest. Removes one always-on thread. |
| `ENABLE_DESK` | 0 | Set `1` to add the Metals Desk. Costs one more thread and ~4 HTTP calls per `DESK_POLL_SECONDS`. |
| `DESK_POLL_SECONDS` | 900 | Only read when the desk is on. Raise it to cut the desk's share of CPU. |

The monitor now also **sleeps 4× longer outside 08:00–20:00 Tehran**, since the
dealer board does not move overnight.

**If you want the cheapest possible setup:** `CHECK_INTERVAL_MIN=240`,
`ENABLE_COMMANDS=0`. The strategy trades about **6 times in 6.4 years** — it
does not need minute-level monitoring.

**Cheaper still:** the bot does not have to run 24/7 at all. Railway
[cron schedules](https://docs.railway.com/reference/cron-jobs) can run it once
a day; the process would live for seconds instead of hours. That needs a small
refactor (run one cycle, then exit) — ask if you want it.
