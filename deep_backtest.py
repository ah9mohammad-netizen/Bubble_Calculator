"""Deep backtest on 750 sessions (2023-07-15 -> 2026-07-27), close prices, consistent convention."""
import csv, statistics as st, sys
sys.path.insert(0,'bot')
import strategy as S

rows=list(csv.DictReader(open('data/master.csv')))
D=[r['date'] for r in rows]
Q=[float(r['quarter']) for r in rows]
M=[float(r['mesghal']) for r in rows]
U=[float(r['usd']) for r in rows]
N=len(D)
C=S.COST_PER_LEG

RP=[S.relative_premium(Q[i],M[i]) for i in range(N)]
VOL=[None]*N
for i in range(N):
    if i>=46: VOL[i]=S.vol45(M[max(0,i-45):i+1])

def gq(i): return 1.0/ (Q[i]/S.QUARTER_G)   # fine grams per rial
def gm(i): return 1.0/ (M[i]/S.MESGHAL_G)

def price(a,i):
    return {'QUARTER':Q[i]/S.QUARTER_G,'MESGHAL':M[i]/S.MESGHAL_G,'USD':U[i]}[a]

def run(strategy_name, decide_fn, start=46):
    """Track wealth in rials, 1bn start. decide_fn(i, cur) -> target."""
    cash=1_000_000_000.0
    cur='QUARTER'
    units=cash/price(cur,start)
    trades=[]
    last_l1=last_l2=-999
    for i in range(start,N):
        tgt=decide_fn(i,cur,last_l1,last_l2)
        if tgt!=cur:
            isl1 = 'USD' in (cur,tgt)
            if isl1 and i-last_l1 < S.MINHOLD_L1: tgt=cur
            elif (not isl1) and i-last_l2 < S.MINHOLD_L2: tgt=cur
        if tgt!=cur:
            val=units*price(cur,i)*(1-C)
            units=val*(1-C)/price(tgt,i)
            trades.append((D[i],cur,tgt,RP[i],VOL[i]))
            if 'USD' in (cur,tgt): last_l1=i
            else: last_l2=i
            cur=tgt
    final=units*price(cur,N-1)
    return final,trades,cur

def hold(asset):
    return lambda i,cur,a,b: asset

def l2_only(i,cur,a,b):
    if cur=='USD': cur='MESGHAL'
    if RP[i]<=S.B_BUY_QUARTER: return 'QUARTER'
    if RP[i]>=S.A_SELL_QUARTER: return 'MESGHAL'
    return cur

def two_layer(i,cur,a,b):
    v=VOL[i]
    if v is None: return cur
    if cur=='USD':
        if v>S.VOL_LO: return 'USD'
        pref='QUARTER' if RP[i]<=S.B_BUY_QUARTER else ('MESGHAL' if RP[i]>=S.A_SELL_QUARTER else 'MESGHAL')
        return pref
    if v>=S.VOL_HI: return 'USD'
    return l2_only(i,cur,a,b)

print('='*78)
print('DEEP BACKTEST  %s -> %s   (%d sessions, %d yrs)'%(D[46],D[-1],N-46,(N-46)/250))
print('start 1,000,000,000 rial held as QUARTER   cost %.1f%%/leg'%(C*100))
print('='*78)
res={}
for name,fn in [('1 Hold USD',hold('USD')),('2 Hold ربع سکه',hold('QUARTER')),
                ('3 Hold مثقال',hold('MESGHAL')),('4 Q<->M switching',l2_only),
                ('5 Two-layer',two_layer)]:
    f,t,c=run(name,fn)
    res[name]=(f,t)
    print('%-20s final %8.3f bn  %+9.1f%%  trades %2d  end=%s'%(name,f/1e9,(f/1e9-1)*100,len(t),c))

print()
print('--- gold-denominated (grams of fine gold, start = 1bn in ربع) ---')
g0=1e9/(Q[46]/S.QUARTER_G)
for name,(f,t) in res.items():
    # convert final rials to grams at mesghal rate
    gend=f/(M[N-1]/S.MESGHAL_G)
    print('%-20s %9.2f g  (%.3fx start %.2f g)'%(name,gend,gend/g0,g0))

print()
print('--- trades of the two-layer strategy ---')
for d,a,b,rp,v in res['5 Two-layer'][1]:
    print('  %s  %-8s -> %-8s  RP=%5.1f%%  vol=%s'%(d,a,b,rp*100,('%.2f%%'%(v*100)) if v else 'n/a'))
