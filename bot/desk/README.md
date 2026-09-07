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
| Wrappers | طلا price + NAV + bubble · پلاتا price + NAV + premium · اهرم price + NAV + discount · TEDPIX — *needs TSETMC, currently dark; see Data sources* |
| Macro | Iran CPI y/y, oil exports (manual, set via `/set`) |
| Derived | ladder state, limit-day detection, sanity/unit checks |

The **parity gap** is the one most people never compute. On 9 Shahrivar it
read −18.3% and the next session gold moved +20.5%.
`test_the_9_shahrivar_discount_would_have_fired` pins that behaviour.

---

## Turning it on

1. Railway → the bot service → **Variables** → add `ENABLE_DESK=1`.
2. Add `METALS_DEV_KEY` (free tier). `BRSAPI_KEY` is not needed while brsapi
   is disabled. tgju and coingecko need no key at all.
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
/parity   parity, step by step   /probe X  raw JSON from a wired source
/funds    fund premiums          /set k v [k v ...]  manual values
/probeurl <url> [filter]  fetch ANY url from this box, list its numbers
/tgju [slug ...]          ask tgju which slugs it will actually serve
/mute /unmute                    /thresh id v   override a threshold
/reload   re-read config from disk
/desk     this command list
```

`/fires` is the desk's signal log. The strategy bot's own `/history` and
`/signal` are untouched and still mean position changes.

---

## Data sources

**brsapi and TSETMC do not answer from Railway.** Both are disabled in
`config/sources.yaml` — kept, not deleted, so re-enabling is a one-word edit
if you stand up the relay. tgju carries Engine 1 in their place.

| Source | What | Status |
|---|---|---|
| `api.tgju.org` | USD free, مثقال, ربع سکه, XAU — plus 18k, سکه امامی, XAG to confirm | **working** — `bot/datafeed.py` has read this same endpoint from this same service since launch |
| `api.gold-api.com` | XAU, XAG | keyless fallback — same host `datafeed.py` already falls back to |
| `metals.dev` | XAU, XAG, copper | needs `METALS_DEV_KEY`; **401 without it**, which looks identical to a block |
| `coingecko` | BTC | works; no key |
| `brsapi.ir` | USD حواله, direct 18k | **disabled** — not answering |
| `cdn.tsetmc.com` | fund price + **NAV**, TEDPIX | **disabled** — not answering |

### Why tgju is enough for Engine 1

The handbook is built on the 18k gram price: parity, the gap, grams per
billion and every ladder rung reference it. brsapi served that directly. tgju
may serve it as `geram18` — unconfirmed from this deployment — but it does not
have to, because **مثقال is the same gold**: 4.6083 g at عیار ۷۰۵ = 3.2489 g
fine, the same constant `strategy.py` uses.

```
toman/g 24k = mesghal / 3.2489        18k = × 0.750
```

`derive.py` applies that whenever no direct 18k feed answers, and
`/health` says the value is derived rather than passing it off as a dealer
print. Fed the handbook's own مثقال quote it reproduces brsapi's answer
exactly — 22,170,000 toman/g, parity 22,549,866, gap −1.68%, 45.1 g per
billion. `test_engine_one_survives_on_tgju_alone` pins that.

So on tgju alone you keep: parity and the gap, the FX side of Engine 1, grams
per billion, the full ladder, and world spot.

### Still no طلا / پلاتا / اهرم? Work it in this order

**1. Ask tgju first.** It is the only Iranian host answering this deployment,
so before hunting a new provider, find out what tgju itself carries:

```
/tgju
```

That scans a list of candidate slugs — fund names in tgju's own naming style,
the unconfirmed ones already wired into `sources.yaml` (`geram18`, `silver`,
`sekee`, `bourse`), and three known-good controls. It reports which slugs
returned rows and which returned nothing.

**Read the controls first.** `price_dollar_rl`, `mesghal` and `ons` must
appear under SERVES DATA. If they do not, tgju is down and the rest of the
scan means nothing. Try your own guesses with `/tgju slug1 slug2`. Anything
that serves data goes straight into the `tgju` fields block, then `/reload`.

**2. Then probe the other sites.** See below.

### Probing a candidate host: `/probeurl`



TSETMC was the only source of طلا / پلاتا / اهرم price and NAV, and it does not
answer this deployment. The question for any replacement is not "what shape is
the JSON" — it is **"will this host talk to Railway at all"**, and only the
Railway box can answer that. So ask it directly:

```
/probeurl https://fund.fipiran.ir/api/v1/fund/fundcompare
/probeurl https://some-host/api/funds nav        ← filter a long response
```

It fetches from the deployment's own IP and prints the status, the size, and
every numeric field with the exact dot/bracket path `sources.yaml` wants —
flagging the ones whose key looks like a price or a NAV. Paste a path into
`funds_a`, `/reload`, done. No redeploy, no code change.

**A timeout or a connection reset is the answer**, not a failure: that host is
blocked the same way brsapi and TSETMC are, so move to the next candidate.

**Try the page URL first — it may just work.** rahavard365, chartix and
alandinvest are Next.js/Nuxt sites, and those bake their data into a JSON blob
inside the HTML (`__NEXT_DATA__`, `window.__NUXT__`). `/probeurl` digs that out
and scans it like any other JSON, so pasting the page address is worth one try:

```
/probeurl https://rahavard365.com/fund
/probeurl https://chartix.ir/market/saham-fund
/probeurl https://alandinvest.com/markets/bourse/68
```

If the reply says it found no JSON inside the page, the numbers arrive by XHR
after load. Then open the site in a *desktop* browser → DevTools → Network →
Fetch/XHR → reload → copy the request that returns them, and probe that URL
instead.

Candidates worth probing, in the order I would try them:

| Host | Why | Status |
|---|---|---|
| `fund.fipiran.ir` | the canonical NAV publisher, and a *different host* from tsetmc — which matters, since tgju answers and tsetmc does not | URL above is a **candidate, unverified from here** |
| rahavard365 / chartix / alandinvest | all three show the funds, so all three fetch the data from somewhere | find their XHR, then probe |

`/probeurl` is **owner-only** — it makes the bot fetch a URL the caller chose,
and it refuses anything but a public `https` host (no loopback, no private
range, no cloud-metadata endpoint).

### What is dark until a source comes back

| Missing | Costs you |
|---|---|
| `usd_havaleh` (was brsapi) | `fx_spread_pct` → the spread rules, **including the `fx_spread_converging` KILL criterion** |
| fund NAV + price (was TSETMC) | طلا bubble, پلاتا premium, اهرم discount → the whole `funds` group and the wrapper gates in `/gates` |
| TEDPIX (was TSETMC) | the index rules |

`/health` reports these as absent rather than reporting a premium of zero.

**The stopgap is `/set`.** Manual values feed the snapshot exactly like a
scraped field, persist in `desk.db`, and are carried forward between updates:

```
/set usd_havaleh 157480
/set tala_price 1556199 tala_nav 1578000 plata_price 12150 plata_nav 11667
/set ahrom_price 57106 ahrom_nav 73496
```

`/set` takes as many key/value pairs as you like in one message, because six
values in six separate messages is how people stop bothering.

That is about a minute a day and it re-arms the kill criterion, which is the
one rule you least want dark.

### Adding a source you have verified — tradersarena, iranjib, anything else

`custom_a` and `custom_b` are empty slots in `sources.yaml`, disabled and
ready. **No code change is needed** — any JSON endpoint can be mapped there.

I could not confirm a public JSON API for tradersarena or iranjib from this
deployment, and a guessed URL fails silently rather than loudly, so the slots
are left for you to point at something you have actually seen respond:

1. Open the site, watch the network tab, find the request that returns the
   numbers as JSON. Copy its URL into `url:`.
2. `/reload`, then `/probe custom_a` to dump the raw response.
3. Read the dump, set `path:` for each field (dot/bracket notation), add
   `scale: 0.1` if the site quotes rial, `/reload` again.

Field names must be ones `derive.py` knows: `usd_free`, `usd_havaleh`,
`gold18k_toman`, `mesghal_toman`, `xau_usd`, `xag_usd`, `tala_price`,
`tala_nav`, `plata_price`, `plata_nav`, `ahrom_price`, `ahrom_nav`, `tedpix`.

### Source order

The collector merges in file order, and a later source overwrites an earlier
one **only for fields it actually returned**. So the proven-but-coarse feed
goes first and the better-but-flakier one after: when `metals.dev` answers it
wins on spot, and when it does not, tgju's `ons` is already in place.

### Units — the one that bites

tgju quotes Iranian instruments in **rial**; the desk works in **toman**.
Every Iranian tgju field carries `scale: 0.1`. Get it wrong and you have a
clean factor of ten, which `derive.sanity_warnings()` catches against parity
on the first poll and names the line to fix — but catching it is a worse
outcome than setting it right.

### Same-session pairing

Parity pairs a gold quote against a dollar quote. tgju updates its indicators
at different times, so the naive "latest row of each" can pair a two-day-old
18k print against today's dollar and call the calendar a discount. This bot
has already been burned by exactly that once, with ربع سکه against مثقال. The
tgju source now measures the spread between the session dates behind the
quotes it paired and warns when they disagree.

### When a feed changes shape

Iranian APIs change their JSON without notice. Field mapping lives in
`config/sources.yaml`, not in code:

```
/probe tgju            # dump the raw response
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

Twelve are the upstream handbook tests, unchanged. Nine cover the tgju
fallback — rial scaling, newest-row selection whichever order tgju serves,
mismatched-session detection, and the promise that Engine 1 reproduces
brsapi's parity answer from مثقال alone. Ten more cover what the port
changed: the Jalali clock that replaced `jdatetime`, the `requests`
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
