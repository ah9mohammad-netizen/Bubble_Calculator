"""Show the full daily calculation, step by step, with every number visible.

Uses the SAME functions the bot uses (bot/strategy.py), so if the arithmetic
below is right, the bot is right.

    python3 daily_calc.py                 # latest stored session
    python3 daily_calc.py --date 2026-08-18
    python3 daily_calc.py --quarter 535000000 --mesghal 836220000 \
                          --usd 1870100 --spot 4337.21

Prices are entered in RIAL (as tgju publishes them) and displayed in TOMAN.
"""
import argparse, csv, glob, sys, statistics as st

sys.path.insert(0, 'bot')
import strategy as S


def tm(rial):
    return f"{rial/10:,.0f}"


def load():
    rows = list(csv.DictReader(open('data/master.csv')))
    d = {}
    for r in rows:
        try:
            d[r['date']] = {'quarter': float(r['quarter']),
                            'mesghal': float(r['mesghal']),
                            'usd': float(r['usd'])}
        except (ValueError, TypeError, KeyError):
            pass
    for f in glob.glob('data/raw/ons_*.csv'):
        for r in csv.reader(open(f)):
            if r and r[0].startswith('20') and r[0] in d:
                d[r[0]]['spot'] = float(r[1])
    return d


ap = argparse.ArgumentParser()
ap.add_argument('--date')
ap.add_argument('--quarter', type=float)
ap.add_argument('--mesghal', type=float)
ap.add_argument('--usd', type=float)
ap.add_argument('--spot', type=float)
a = ap.parse_args()

data = load()
dates = sorted(data)
date = a.date or dates[-1]
row = dict(data.get(date, {}))
for k in ('quarter', 'mesghal', 'usd', 'spot'):
    if getattr(a, k) is not None:
        row[k] = getattr(a, k)

Q, M, U = row.get('quarter'), row.get('mesghal'), row.get('usd')
SP = row.get('spot')

W = 62
print('=' * W)
print(f'DAILY CALCULATION   {date}')
print('=' * W)

# ---------------------------------------------------------------- 0. inputs
print('\n[0] INPUTS  (tgju closes)')
print(f'    quarter coin  {tm(Q):>18} toman   ({Q:,.0f} rial)')
print(f'    mesghal       {tm(M):>18} toman   ({M:,.0f} rial)')
print(f'    USD           {tm(U):>18} toman   ({U:,.0f} rial)')
print(f'    gold spot     {SP:>18,.2f} $/oz' if SP else '    gold spot                     n/a')

print('\n    constants')
print(f'    quarter fine gold = 2.032 g x 0.900 = {S.QUARTER_G} g')
print(f'    mesghal fine gold = 4.6083 g x 0.705 = {S.MESGHAL_G} g')
print(f'    troy ounce        = {S.OZ_G} g')

# ---------------------------------------------------------------- 1. RP
print('\n' + '-' * W)
print('[1] RP  — is the quarter coin cheap or rich vs mesghal?')
print('-' * W)
qg = Q / S.QUARTER_G
mg = M / S.MESGHAL_G
print(f'    quarter per fine gram = {tm(Q)} / {S.QUARTER_G}')
print(f'                          = {tm(qg):>16} toman/g')
print(f'    mesghal per fine gram = {tm(M)} / {S.MESGHAL_G}')
print(f'                          = {tm(mg):>16} toman/g')
rp = qg / mg - 1
print(f'\n    RP = {qg/10:,.0f} / {mg/10:,.0f} - 1')
print(f'       = {qg/mg:.6f} - 1')
print(f'       = {rp*100:+.2f}%')
print(f'    check strategy.relative_premium() = {S.relative_premium(Q, M)*100:+.2f}%'
      f'   {"MATCH" if abs(S.relative_premium(Q,M)-rp) < 1e-12 else "MISMATCH"}')
print(f'\n    thresholds: buy quarter <= {S.B_BUY_QUARTER*100:.0f}%'
      f' | hold | switch to mesghal >= {S.A_SELL_QUARTER*100:.0f}%')
verdict = ('BUY QUARTER' if rp <= S.B_BUY_QUARTER else
           'BUY MESGHAL' if rp >= S.A_SELL_QUARTER else 'HOLD (no edge)')
print(f'    -> {verdict}')
print(f'\n    meaning: per gram of fine gold, the coin costs {abs(rp)*100:.1f}% '
      f'{"less" if rp < 0 else "more"} than mesghal.')
print(f'    historically RP has a median of ~51% and a low of ~12%,')
print(f'    so {rp*100:.1f}% is an unusually collapsed coin premium.')

# ---------------------------------------------------------------- 2. vol90
print('\n' + '-' * W)
print('[2] vol90 — how violent is the market? (drives gold vs USD)')
print('-' * W)
hist = [data[d]['mesghal'] for d in dates if d <= date]
rets = [hist[i] / hist[i - 1] - 1 for i in range(1, len(hist))]
w = rets[-S.VOL_WINDOW:]
vol = st.pstdev(w)
print(f'    mesghal sessions available : {len(hist)}')
print(f'    daily returns used         : last {len(w)} of {len(rets)}')
print(f'    mean daily return          : {sum(w)/len(w)*100:+.3f}%')
print(f'    population stdev           : {vol*100:.2f}%')
print(f'    check strategy.vol90()     = {S.vol90(hist)*100:.2f}%'
      f'   {"MATCH" if abs(S.vol90(hist)-vol) < 1e-12 else "MISMATCH"}')
print(f'\n    last 5 daily returns: ' + '  '.join(f'{r*100:+.2f}%' for r in w[-5:]))
print(f'\n    thresholds: calm <= {S.VOL_LO*100:.1f}% -> GOLD'
      f' | neutral | wild >= {S.VOL_HI*100:.1f}% -> USD')
vv = ('CALM -> GOLD' if vol <= S.VOL_LO else
      'RISK-OFF -> USD' if vol >= S.VOL_HI else 'NEUTRAL')
print(f'    -> {vv}')

# ---------------------------------------------------------------- 3. basis
print('\n' + '-' * W)
print('[3] BASIS — is Tehran gold rich or cheap vs the world?')
print('-' * W)
if not SP:
    print('    no spot price -> basis and z cannot be computed')
    bas = None
else:
    pg = SP / S.OZ_G
    print(f'    world gold per gram = {SP:,.2f} / {S.OZ_G} = ${pg:,.2f}/g')
    print(f'    in rial             = ${pg:,.2f} x {U:,.0f} = {pg*U:,.0f} rial/g')
    fv = pg * U * S.MESGHAL_G
    print(f'    fair mesghal        = {pg*U:,.0f} x {S.MESGHAL_G}')
    print(f'                        = {tm(fv):>16} toman')
    print(f'    actual mesghal      = {tm(M):>16} toman')
    bas = M / fv - 1
    print(f'\n    basis = {tm(M)} / {tm(fv)} - 1 = {bas*100:+.2f}%')
    print(f'    check strategy.basis() = {S.basis(M, SP, U)*100:+.2f}%'
          f'   {"MATCH" if abs(S.basis(M,SP,U)-bas) < 1e-12 else "MISMATCH"}')
    print(f'\n    -> Tehran gold trades {abs(bas)*100:.1f}% '
          f'{"BELOW" if bas < 0 else "ABOVE"} world parity')

# ---------------------------------------------------------------- 4. z
print('\n' + '-' * W)
print('[4] Z-SCORE — how unusual is that basis? (display only)')
print('-' * W)
series, sdates = [], []
for d in dates:
    if d > date:
        break
    r = data[d]
    b = S.basis(r.get('mesghal'), r.get('spot'), r.get('usd'))
    if b is not None:
        series.append(b); sdates.append(d)
if len(series) < S.Z_WINDOW + 1:
    print(f'    only {len(series)} basis observations, need {S.Z_WINDOW+1}')
    print('    -> z = n/a (warming up)')
else:
    hist_b = series[-(S.Z_WINDOW + 1):-1]
    mu = sum(hist_b) / len(hist_b)
    sd = st.pstdev(hist_b)
    z = (series[-1] - mu) / sd
    print(f'    window            : {S.Z_WINDOW} prior sessions '
          f'({sdates[-(S.Z_WINDOW+1)]} .. {sdates[-2]})')
    print(f'    mean basis        : {mu*100:+.2f}%')
    print(f'    stdev basis       : {sd*100:.2f}%')
    print(f'    today basis       : {series[-1]*100:+.2f}%')
    print(f'\n    z = ({series[-1]*100:+.2f}% - ({mu*100:+.2f}%)) / {sd*100:.2f}%')
    print(f'      = {(series[-1]-mu)*100:+.2f} / {sd*100:.2f}')
    print(f'      = {z:+.2f}')
    zc = S.basis_z(series)
    print(f'    check strategy.basis_z() = {zc:+.2f}'
          f'   {"MATCH" if abs(zc-z) < 1e-9 else "MISMATCH"}')
    print(f'\n    thresholds: normal < {S.Z_EXIT_USD:+.2f}'
          f' | elevated | stretched > {S.Z_ENTER_USD:+.2f}')
    zz = ('STRETCHED' if z > S.Z_ENTER_USD else
          'NORMAL' if z < S.Z_EXIT_USD else 'ELEVATED')
    print(f'    -> {zz}   (display only, does not trade)')

# ---------------------------------------------------------------- 5. decision
print('\n' + '=' * W)
print('[5] DECISION')
print('=' * W)
print(f'    Layer 1  vol90 {vol*100:.2f}%  -> {vv}')
print(f'    Layer 2  RP    {rp*100:.1f}%   -> {verdict}')
if vol >= S.VOL_HI:
    tgt = 'USD'
elif rp <= S.B_BUY_QUARTER:
    tgt = 'QUARTER COIN'
elif rp >= S.A_SELL_QUARTER:
    tgt = 'MESGHAL'
else:
    tgt = 'MESGHAL (default)'
print(f'\n    TODAY -> {tgt}')
