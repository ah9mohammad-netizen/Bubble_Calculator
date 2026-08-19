"""Persistence sensitivity for the basis z-score gate.

Question: the spec requires z > +1.75 for 3 consecutive closes and that fired
ZERO times.  What happens if we relax the confirmation requirement?

Naming used here (P = number of consecutive closes required):
    P=1  "0 persistence"   -> trade the first close above the threshold
    P=2  "1 persistence"   -> one extra confirming close
    P=3  "2 persistence"   -> the spec as written

Position semantics: GOLD = hold مثقال, USD = hold dollars.
Every transition pays COST per leg.  Reported in FINE GRAMS OF GOLD, which is
the unit that matters for this strategy, against 1.0 = buy-and-hold مثقال.
"""
import csv, glob, sys, statistics as st

sys.path.insert(0, 'bot')
import strategy as S

COST = 0.02
Z_HI, Z_LO = S.Z_ENTER_USD, S.Z_EXIT_USD
W = S.Z_WINDOW

# ------------------------------------------------------------------ data
spot = {}
for f in glob.glob('data/raw/ons_*.csv'):
    for r in csv.reader(open(f)):
        if r and r[0].startswith('20'):
            spot[r[0]] = float(r[1])
dom = {r['date']: r for r in csv.DictReader(open('data/master.csv'))}
dates = sorted(set(spot) & set(dom))

rows = []
for d in dates:
    xau, usd, mes = spot[d], float(dom[d]['usd']), float(dom[d]['mesghal'])
    fair = xau / S.OZ_G * usd * S.MESGHAL_G
    rows.append({'d': d, 'basis': mes / fair - 1, 'mes': mes, 'usd': usd})

Z = [None] * len(rows)
for i in range(len(rows)):
    if i < W:
        continue
    win = [r['basis'] for r in rows[i - W:i]]
    m = sum(win) / len(win)
    s = st.pstdev(win)
    if s > 0:
        Z[i] = (rows[i]['basis'] - m) / s

live = [i for i, z in enumerate(Z) if z is not None]
YEARS = len(live) / 250


def runs(pred):
    out, c = [], 0
    for i in live:
        if pred(Z[i]):
            c += 1
        elif c:
            out.append(c); c = 0
    if c:
        out.append(c)
    return out


def bt(p_in, p_out, z_hi=Z_HI, z_lo=Z_LO, cooldown=S.Z_COOLDOWN, cost=COST):
    """Backtest.  p_in/p_out = consecutive closes required to enter/exit USD."""
    state, last, run_hi, run_lo = 'GOLD', -10**9, 0, 0
    trades, grams, usd_held = [], 1.0, 0.0
    for i, z in enumerate(Z):
        if z is None:
            continue
        run_hi = run_hi + 1 if z > z_hi else 0
        run_lo = run_lo + 1 if z < z_lo else 0
        r = rows[i]
        gp = r['mes'] / S.MESGHAL_G            # rial per fine gram
        if state == 'GOLD' and run_hi >= p_in and i - last >= cooldown:
            usd_held = grams * gp / r['usd'] * (1 - cost)
            grams = 0.0
            state, last, run_hi = 'USD', i, 0
            trades.append((r['d'], 'GOLD->USD', z))
        elif state == 'USD' and run_lo >= p_out and i - last >= cooldown:
            grams = usd_held * r['usd'] / gp * (1 - cost)
            usd_held = 0.0
            state, last, run_lo = 'GOLD', i, 0
            trades.append((r['d'], 'USD->GOLD', z))
    lr = rows[live[-1]]
    if state == 'USD':                          # mark back to gold at the end
        grams = usd_held * lr['usd'] / (lr['mes'] / S.MESGHAL_G)
    return trades, grams, state


LAB = {1: '0 persistence  (P=1, fire on 1st close)',
       2: '1 persistence  (P=2, one confirmation)',
       3: '2 persistence  (P=3, the spec)'}

print('=' * 74)
print('SAMPLE')
print('=' * 74)
print('spot x domestic overlap : %d sessions  %s -> %s'
      % (len(dates), dates[0], dates[-1]))
print('sessions with a z-score : %d  %s -> %s  (%.2f yr; first %d eaten by the window)'
      % (len(live), rows[live[0]]['d'], rows[live[-1]]['d'], YEARS, W))
zz = [Z[i] for i in live]
print('z range                 : %+.2f .. %+.2f   median %+.2f'
      % (min(zz), max(zz), st.median(zz)))

print()
print('=' * 74)
print('WHY PERSISTENCE BITES — run lengths, not levels')
print('=' * 74)
print('%-22s %8s %8s   %s' % ('condition', 'closes', 'episodes', 'run lengths'))
for lbl, pred in [('z > +1.75 (entry)', lambda z: z > 1.75),
                  ('z > +1.50', lambda z: z > 1.50),
                  ('z > +1.25', lambda z: z > 1.25),
                  ('z > +1.00', lambda z: z > 1.00),
                  ('z < +0.50 (exit)', lambda z: z < 0.50)]:
    rl = runs(pred)
    print('%-22s %8d %8d   %s' % (lbl, sum(rl), len(rl),
          sorted(rl, reverse=True)[:10]))
print()
print('Entry breaches are SPIKES (single closes); exits are PLATEAUS (long runs).')
print('So entry persistence is the whole game and exit persistence is free.')

print()
print('=' * 74)
print('HEAD-TO-HEAD  (entry AND exit persistence both = P, as in the spec)')
print('=' * 74)
hdr = '%-42s %7s %7s %9s %8s' % ('rule', 'trades', 'per yr', 'grams', 'vs hold')
print(hdr); print('-' * len(hdr))
res = {}
for p in (1, 2, 3):
    tr, g, stt = bt(p, p)
    res[p] = (tr, g, stt)
    print('%-42s %7d %7.1f %9.4f %7.1f%%'
          % (LAB[p], len(tr), len(tr) / YEARS, g, (g - 1) * 100))
print('%-42s %7d %7.1f %9.4f %7.1f%%' % ('buy & hold مثقال', 0, 0, 1.0, 0.0))

print()
print('=' * 74)
print('SPLIT: entry persistence vs exit persistence (grams)')
print('=' * 74)
print('%-14s %10s %10s %10s' % ('entry \\ exit', 'exit P=1', 'exit P=2', 'exit P=3'))
for pi in (1, 2, 3):
    print('%-14s %10.4f %10.4f %10.4f'
          % ('entry P=%d' % pi, bt(pi, 1)[1], bt(pi, 2)[1], bt(pi, 3)[1]))

print()
print('=' * 74)
print('TRADE LOG')
print('=' * 74)
idx = {r['d']: i for i, r in enumerate(rows)}
for p in (1, 2, 3):
    tr, g, stt = res[p]
    print('%s  ->  %d trades, %.4f g' % (LAB[p], len(tr), g))
    if not tr:
        print('    (never fired)')
    for d, k, z in tr:
        print('    %s  %-10s z=%+.2f' % (d, k, z))
    if tr:
        print('    round-trips:')
        for a, b in zip(tr[::2], tr[1::2] + [None]):
            i0 = idx[a[0]]
            i1 = idx[b[0]] if b else live[-1]
            r0, r1 = rows[i0], rows[i1]
            u = r1['usd'] / r0['usd'] - 1
            au = (r1['mes'] / S.MESGHAL_G) / (r0['mes'] / S.MESGHAL_G) - 1
            print('      %s -> %-11s USD %+6.1f%%  gold %+6.1f%%  gross %+6.1f%%  net(2%%x2) %+6.1f%%'
                  % (a[0], b[0] if b else '(still open)', u * 100, au * 100,
                     ((1 + u) / (1 + au) - 1) * 100,
                     ((1 + u) / (1 + au) * (1 - COST) ** 2 - 1) * 100))
    print()

print('=' * 74)
print('WHAT WOULD MAKE P=2 / P=3 TRADE AT ALL — entry threshold grid')
print('=' * 74)
print('%-10s %-22s %-22s %-22s' % ('z_enter', 'P=1  trades / grams',
                                   'P=2  trades / grams', 'P=3  trades / grams'))
for zh in (2.00, 1.75, 1.50, 1.25, 1.00, 0.75):
    cells = []
    for p in (1, 2, 3):
        tr, g, _ = bt(p, p, z_hi=zh)
        cells.append('%2d / %.4f' % (len(tr), g))
    print('%-10.2f %-22s %-22s %-22s' % (zh, *cells))

print()
print('=' * 74)
print('COST SENSITIVITY (grams)')
print('=' * 74)
print('%-12s %10s %10s %10s' % ('cost/leg', 'P=1', 'P=2', 'P=3'))
for c in (0.000, 0.005, 0.010, 0.020, 0.030):
    print('%-12s %10.4f %10.4f %10.4f' % ('%.1f%%' % (c * 100),
          bt(1, 1, cost=c)[1], bt(2, 2, cost=c)[1], bt(3, 3, cost=c)[1]))

print()
print('=' * 74)
print('COOLDOWN SENSITIVITY, P=1 only (the other two never trade)')
print('=' * 74)
print('%-12s %8s %10s' % ('cooldown', 'trades', 'grams'))
for cd in (0, 5, 10, 20, 30, 45, 60):
    tr, g, _ = bt(1, 1, cooldown=cd)
    print('%-12s %8d %10.4f' % (cd, len(tr), g))

print()
print('=' * 74)
print('PLACEBO — is P=1 skill, or did it just hold USD during one lucky window?')
print('=' * 74)
import random
random.seed(7)
tr, g_real, _ = bt(1, 1)
# P=1 spent this many sessions in USD; sample random windows of the same length
in_usd = 0
state, last, rh, rl = 'GOLD', -10**9, 0, 0
occ = []
for i, z in enumerate(Z):
    if z is None:
        continue
    rh = rh + 1 if z > Z_HI else 0
    rl = rl + 1 if z < Z_LO else 0
    if state == 'GOLD' and rh >= 1 and i - last >= S.Z_COOLDOWN:
        state, last, rh = 'USD', i, 0; start = i
    elif state == 'USD' and rl >= 1 and i - last >= S.Z_COOLDOWN:
        state, last, rl = 'GOLD', i, 0; occ.append((start, i))
lens = [b - a for a, b in occ]
print('P=1 held USD for %d + %d = %d of %d scored sessions (%.0f%% of the time)'
      % (*lens, sum(lens), len(live), 100 * sum(lens) / len(live)))

wins = 0; N = 20000; samples = []
lo, hi = live[0], live[-1]
for _ in range(N):
    grams = 1.0
    ok = True
    starts = []
    for L in lens:
        s0 = random.randint(lo, hi - L)
        starts.append((s0, s0 + L))
    starts.sort()
    if any(starts[k][1] > starts[k + 1][0] for k in range(len(starts) - 1)):
        continue
    for a, b in starts:
        r0, r1 = rows[a], rows[b]
        u = r1['usd'] / r0['usd']
        au = (r1['mes'] / S.MESGHAL_G) / (r0['mes'] / S.MESGHAL_G)
        grams *= u / au * (1 - COST) ** 2
    samples.append(grams)
    if grams >= g_real:
        wins += 1
samples.sort()
print('random same-length USD windows (n=%d): median %.4f  5%% %.4f  95%% %.4f'
      % (len(samples), samples[len(samples)//2],
         samples[int(.05*len(samples))], samples[int(.95*len(samples))]))
print('P=1 result %.4f  ->  beaten by %.1f%% of random windows  (p = %.2f)'
      % (g_real, 100*wins/len(samples), wins/len(samples)))
print()
print('A p-value anywhere near 0.5 means the timing carried no information;')
print('the gain came from being in USD at all during a rial-devaluation stretch.')
