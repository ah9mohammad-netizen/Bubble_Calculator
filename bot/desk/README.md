# Metals Desk

The **Two Engines Handbook** as a set of rules, running inside the existing
gold/FX signalling bot. It polls Iranian and world market data, computes the
handbook's arithmetic, evaluates 33 declarative rules, and pushes what fires
to the same Telegram chat.

It does not trade. It watches, computes, and tells you when a handbook
condition is met. Every threshold lives in `config/rules.yaml` — tune it
without touching code.

---

## It is off by default. That is deliberate.

The strategy bot in `bot/main.py` is a live deployment. Nothing in this
folder runs, opens a socket, or writes to the volume until you set one
Railway variable:

```
ENABLE_DESK=1
```

With it unset, `main.py` registers no extra commands, starts no extra thread,
and builds no desk object. The only visible traces are one extra line in
`/stats` (`desk off`) and one extra key in the health JSON
(`"desk": {"enabled": false}`).

---

## What it tracks

| Group | Metrics |
|---|---|
| Engine 1 — toman | USD free, USD حواله, spread, 18k gold, **import parity + gap**, grams per billion |
| Engine 2 — spot | XAU, XAG, copper $/lb, BTC, gold/silver ratio |
| Wrappers | طلا price + NAV + bubble · پلاتا price + NAV + premium · اهرم price + NAV + discount · TEDPIX |
| Macro | Iran CPI y/y, oil exports (manual, set via `/set`) |
| Derived | ladder state, limit-day detection, sanity/unit checks |

The **parity gap** is the one most people never compute. On 9 Shahrivar it
read −18.3% and the next session gold moved +20.5%.
`test_the_9_shahrivar_discount_would_have_fired` pins that behaviour.

---

## Turning it on

1. Railway → the bot service → **Variables** → add `ENABLE_DESK=1`.
2. Add `BRSAPI_KEY` and `METALS_DEV_KEY` (both free tiers; without them
   those two sources return errors and `/health` shows them red).
3. Redeploy, then run **`/health`** in Telegram. That is the whole checklist:
   green sources are working, red ones need `/probe`.

| variable | default | effect |
|---|---|---|
| `ENABLE_DESK` | `0` | master switch |
| `DESK_POLL_SECONDS` | `900` | seconds between desk polls (min 60) |
| `DESK_ALERTS` | `1` | `0` = commands only, never pushes |
| `DESK_QUIET_HOURS` | `01:00-07:00` | Tehran; `critical` rules ignore it |
| `DESK_HTTP_TIMEOUT` | `20` | per-request seconds |
| `BRSAPI_KEY` | — | brsapi.ir |
| `METALS_DEV_KEY` | — | metals.dev |
| `IRAN_RELAY_URL` / `IRAN_RELAY_TOKEN` | — | see *Blocked IPs* below |

The desk stores its history in `desk.db` **on the same volume** as
`prices.csv`, so cooldowns, manual values and threshold overrides survive a
redeploy exactly like the strategy bot's state does.

---

## Commands

None of these collide with the strategy bot's own commands, and if one ever
did, the existing command wins and the desk logs that it was skipped.

```
/now      full snapshot          /rules    every rule vs its threshold
/gates    handbook entry gates   /fires    recent desk signals
/ladder   ladder rung status     /health   source status + staleness
/parity   parity, step by step   /probe X  raw JSON from source X
/funds    fund premiums          /set k v  manual value (CPI, oil exports)
/mute /unmute                    /thresh id v   override a threshold
/reload   re-read config from disk
/desk     this command list
```

`/fires` is the desk's signal log. The strategy bot's own `/history` and
`/signal` are untouched and still mean position changes.

---

## Data sources

| Source | What | Key | Notes |
|---|---|---|---|
| `brsapi.ir` | USD toman, 18k gold, coins | free, key on request | Iranian host |
| `metals.dev` | XAU, XAG, copper | free tier | |
| `coingecko` | BTC | none | |
| `cdn.tsetmc.com` | طلا / پلاتا / اهرم price **and NAV**, TEDPIX | none | Iranian host |

NAV is what makes premium/discount computable, and premium/discount is what
the wrapper gates are written against. If NAV goes missing the desk carries
the last value forward and says so in `/health` rather than silently
reporting a wrong premium.

**Verify `tse` first.** Its instrument codes are resolved by symbol search on
first use and cached; TSETMC lists delisted look-alikes, so once `/probe tse`
shows you the real codes, pin them under `codes:` in `sources.yaml`. TSETMC
is also the source whose response shape changes most often.

### ⚠️ Blocked IPs — read this before enabling

**Railway runs in the US/EU. Iranian hosts frequently block or rate-limit
foreign IPs, and TSETMC is the most likely to fail.** Three ways to handle
it, in order:

1. **Try direct first.** Enable, then run `/health`. If `brsapi_gold` and
   `tse` are green, you are done.
2. **Relay.** `relay.py` is a small FastAPI proxy. Run it on any always-on
   box inside Iran, set `IRAN_RELAY_URL` and `IRAN_RELAY_TOKEN` on Railway.
   Only the sources listed under `relay.applies_to` in `config/sources.yaml`
   route through it. It exposes `/proxy?name=` for single-URL sources and
   `/get?url=` for TSETMC, which needs three; `/get` refuses any host that
   does not appear in `sources.yaml`, so it cannot be used as an open proxy.
   `relay.py` is never imported by the bot and its dependencies (fastapi,
   uvicorn) are not in `requirements.txt` — it runs on your machine.
3. **Degrade.** With Iranian sources down, world-spot rules still fire and
   Iranian ones simply do not evaluate. `/health` tells you which. The desk
   warns once an hour rather than pretending the data is fresh.

### When a feed changes shape

Iranian APIs change their JSON without notice. Field mapping lives in
`config/sources.yaml`, not in code:

```
/probe brsapi_gold     # dump the raw response
# edit the path in config/sources.yaml
/reload                # re-read, no redeploy
```

The `scale:` field handles rial-vs-toman. `derive.sanity_warnings()` detects
a factor-of-10 error against parity and tells you exactly which line to fix —
this is the single most likely bug with Iranian feeds, so it is checked on
every poll.

---

## Adding a rule

Append to `config/rules.yaml`, then `/reload`:

```yaml
  - id: my_rule
    group: spot
    title: "Silver reclaims the 200-day"
    metric: xag_usd            # must exist in derive.py
    op: crosses_up             # lt gt between outside crosses_up crosses_down abs_gt
    value: 71.5
    severity: action           # info watch action critical
    cooldown: 43200
    message: "*XAG ${xag_usd:.2f}* reclaimed 71.5."
```

`test_every_rule_metric_is_producible` fails the build if a rule references a
metric `derive()` never emits — so a typo cannot become a silently dead rule.

`crosses_down` / `crosses_up` need a previous snapshot and fire **once** per
crossing. Use them for the ladder. Use `lt`/`gt` for states you want
re-reminding about, and let `cooldown` control the nagging.

---

## Tests

```
python -m pytest bot/desk/tests -q      # 22 tests, no network needed
```

Twelve are the upstream handbook tests, unchanged. Ten more cover what this
port changed: the Jalali clock that replaced `jdatetime`, the `requests`
field extraction that replaced `httpx`, Persian-digit parsing, and the
promise that every renderer survives a completely empty snapshot — because a
blocked Iranian IP is the expected case, not the exceptional one.

---

## Design notes

- **Its own thread, its own clock.** The desk does not run inside
  `monitor()`. The strategy loop's cadence, its night-time 4× slowdown and
  its daily-digest bookkeeping are tuned for a market that prints once a
  session; the desk wants 15-minute resolution. Sharing a thread would mean
  one of them compromising — and a hung desk fetch could delay a trade
  signal.
- **It never raises into the host.** `Desk.tick()` and every command handler
  are wrapped. A broken feed costs the desk one cycle and nothing else.
- **One Telegram client.** The desk returns the text it wants sent; the bot
  sends it with its own retrying `send()`. Two processes long-polling the
  same token would 409 each other and take the strategy bot down with it.
- **No heavy dependencies.** Upstream used python-telegram-bot, APScheduler,
  httpx, pytz, jdatetime and pytse-client. All are gone. The desk adds
  exactly one line to `requirements.txt` (`PyYAML`), and even that is
  imported defensively: if it were missing the desk reports itself
  unavailable instead of killing the process at boot.
- **Rules are data.** Changing a level is a YAML edit and a `/reload`, not a
  deploy.
- **Cooldown + quiet hours** live in `notify.py`. `critical` ignores both — a
  kill criterion should wake you.
- **Carry-forward, loudly.** Missing Iranian fields reuse the last snapshot
  and add a note. Stale data that announces itself beats a gap that looks
  like a signal.
- **Sanity before signal.** Unit checks run before rules, because a
  rial/toman mix-up would otherwise fire a spectacular fake parity discount.

## Not financial advice

The thresholds encode one specific reading of one market on 10 Shahrivar
1405. They expire. Re-run the scenario matrix quarterly and update
`config/rules.yaml`.
