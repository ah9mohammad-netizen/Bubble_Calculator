"""Build the archive CSV: raw closes + every derived signal, self-contained."""
import csv, sys, statistics as st
sys.path.insert(0, 'bot')
import strategy as S

rows = list(csv.DictReader(open('data/master.csv')))
D = [r['date'] for r in rows]
Q = [float(r['quarter']) for r in rows]
M = [float(r['mesghal']) for r in rows]
U = [float(r['usd']) for r in rows]
N = len(D)

def sd(x): return st.pstdev(x) if len(x) > 1 else 0.0
def rets(s, i, w):
    a = s[max(0, i-w):i+1]
    return [a[k]/a[k-1]-1 for k in range(1, len(a))]

RP  = [S.relative_premium(Q[i], M[i]) for i in range(N)]
V45 = [sd(rets(M, i, 45)) if i > 45 else None for i in range(N)]
V90 = [sd(rets(M, i, 90)) if i > 90 else None for i in range(N)]

# replay both strategies to record the position held each day
def replay(two):
    A, B = S.A_SELL_QUARTER, S.B_BUY_QUARTER
    VH, VL = 0.030, 0.022
    cur = 'QUARTER' if RP[46] <= B else 'MESGHAL'
    a1 = a2 = -10**9; on = False
    out = [''] * N
    for i in range(46, N):
        t = cur
        if two:
            v = V90[i]
            if v is not None:
                if on and v <= VL: on = False
                elif not on and v >= VH: on = True
            if on: t = 'USD'
            else:
                c2 = 'MESGHAL' if cur == 'USD' else cur
                t = 'QUARTER' if RP[i] <= B else ('MESGHAL' if RP[i] >= A else c2)
        else:
            t = 'QUARTER' if RP[i] <= B else ('MESGHAL' if RP[i] >= A else cur)
        if t != cur:
            isl1 = 'USD' in (cur, t)
            if isl1 and i - a1 < 10: t = cur
            elif not isl1 and i - a2 < 5: t = cur
        if t != cur:
            if 'USD' in (cur, t): a1 = i
            else: a2 = i
            cur = t
        out[i] = cur
    return out

POS2 = replay(False)
POST = replay(True)

hdr = ['date',
       'quarter_rial', 'mesghal_rial', 'usd_rial',
       'quarter_toman', 'mesghal_toman', 'usd_toman',
       'quarter_rial_per_g', 'mesghal_rial_per_g',
       'RP', 'vol45', 'vol90',
       'pos_layer2', 'pos_twolayer']
with open('data/ARCHIVE_iran_gold_fx_2020_2026.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(hdr)
    for i in range(N):
        w.writerow([
            D[i],
            int(Q[i]), int(M[i]), int(U[i]),
            round(Q[i]/10, 1), round(M[i]/10, 1), round(U[i]/10, 1),
            round(Q[i]/S.QUARTER_G, 2), round(M[i]/S.MESGHAL_G, 2),
            round(RP[i], 6),
            '' if V45[i] is None else round(V45[i], 6),
            '' if V90[i] is None else round(V90[i], 6),
            POS2[i], POST[i],
        ])
print('wrote data/ARCHIVE_iran_gold_fx_2020_2026.csv')
print('rows %d   %s -> %s' % (N, D[0], D[-1]))
print()
print('sanity:')
print('  RP    min %.1f%%  max %.1f%%' % (min(RP)*100, max(RP)*100))
v9 = [v for v in V90 if v]
print('  vol90 min %.2f%% max %.2f%%' % (min(v9)*100, max(v9)*100))
print('  trades layer2   :', sum(1 for i in range(47,N) if POS2[i]!=POS2[i-1]))
print('  trades two-layer:', sum(1 for i in range(47,N) if POST[i]!=POST[i-1]))
