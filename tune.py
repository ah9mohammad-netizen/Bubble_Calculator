"""Parameter search with honest in-sample / out-of-sample separation."""
import csv,sys,statistics as st
sys.path.insert(0,'bot'); import strategy as S
rows=list(csv.DictReader(open('data/master.csv')))
D=[r['date'] for r in rows];Q=[float(r['quarter']) for r in rows]
M=[float(r['mesghal']) for r in rows];U=[float(r['usd']) for r in rows]
N=len(D)
RP=[S.relative_premium(Q[i],M[i]) for i in range(N)]
VOLC={}
def vol(i,w):
    k=(i,w)
    if k not in VOLC: VOLC[k]=S.vol45(M[max(0,i-w):i+1],w)
    return VOLC[k]
def px(a,i): return {'Q':Q[i]/S.QUARTER_G,'M':M[i]/S.MESGHAL_G,'U':U[i]}[a]
WARM=46

def run(A,B,VH=None,VL=None,mh2=5,mh1=10,w=45,lo=WARM,hi=None,cost=0.02):
    hi = hi or N
    two = VH is not None
    cur='Q' if RP[lo]<=B else 'M'
    units=1e9*(1-cost)/px(cur,lo); l1=l2=-10**9; n=0
    for i in range(lo,hi):
        t=cur
        v=vol(i,w) if two else None
        if two and v is not None:
            if cur=='U': t='U' if v>VL else ('Q' if RP[i]<=B else 'M')
            elif v>=VH: t='U'
            else: t='Q' if RP[i]<=B else ('M' if RP[i]>=A else cur)
        else:
            c2='M' if cur=='U' else cur
            t='Q' if RP[i]<=B else ('M' if RP[i]>=A else c2)
        if t!=cur:
            isl1='U' in (cur,t)
            if isl1 and i-l1<mh1: t=cur
            elif not isl1 and i-l2<mh2: t=cur
        if t!=cur:
            val=units*px(cur,i)*(1-cost); units=val*(1-cost)/px(t,i)
            if 'U' in (cur,t): l1=i
            else: l2=i
            cur=t; n+=1
    return units*px(cur,hi-1), n

def bench(lo,hi,cost=0.02):
    return 1e9*(1-cost)/px('Q',lo)*px('Q',hi-1)

MID=WARM+(N-WARM)//2
def score(A,B,VH=None,VL=None,mh2=5,w=45):
    full,n=run(A,B,VH,VL,mh2,w=w)
    h1,_=run(A,B,VH,VL,mh2,w=w,lo=WARM,hi=MID)
    h2,_=run(A,B,VH,VL,mh2,w=w,lo=MID,hi=N)
    return (full/bench(WARM,N), h1/bench(WARM,MID), h2/bench(MID,N), n)

print('='*76)
print('SEARCH 1 — Layer 2 only: A x B grid (full / H1 / H2, xhold-quarter)')
print('='*76)
best=[]
for A in [0.45,0.50,0.55,0.60,0.65,0.70,0.75,0.80,0.85]:
    for B in [0.15,0.18,0.20,0.22,0.25,0.28,0.31,0.34,0.37,0.40]:
        if B>=A: continue
        f,h1,h2,n=score(A,B)
        best.append((f,h1,h2,n,A,B))
best.sort(reverse=True)
print('%-6s %-6s %7s %7s %7s %4s'%('A','B','FULL','H1','H2','tr'))
for f,h1,h2,n,A,B in best[:12]:
    print('%-6.2f %-6.2f %7.2f %7.2f %7.2f %4d'%(A,B,f,h1,h2,n))
print('  ... current (0.60,0.31):', '%.2f / %.2f / %.2f'%score(0.60,0.31)[:3])
tot=len(best); beat=sum(1 for b in best if b[0]>1)
beat_both=sum(1 for b in best if b[1]>1 and b[2]>1)
print('\n%d/%d combos beat hold-quarter overall; only %d/%d beat it in BOTH halves'%(beat,tot,beat_both,tot))

print()
print('='*76)
print('SEARCH 2 — min-hold, vol window, Layer-1 thresholds')
print('='*76)
print('\n(a) Layer-2 min-hold (A=.60 B=.31):')
for mh in [0,3,5,10,20,40]:
    f,h1,h2,n=score(0.60,0.31,mh2=mh)
    print('   mh2=%-3d full %.2f  H1 %.2f  H2 %.2f  trades %d'%(mh,f,h1,h2,n))

print('\n(b) Layer-1 grid (A=.60 B=.31), vol window 45:')
rowsb=[]
for VH in [0.028,0.030,0.033,0.036,0.040,0.045]:
    for VL in [0.016,0.018,0.020,0.022,0.025]:
        if VL>=VH: continue
        f,h1,h2,n=score(0.60,0.31,VH,VL)
        rowsb.append((f,h1,h2,n,VH,VL))
rowsb.sort(reverse=True)
print('   %-7s %-7s %7s %7s %7s %4s'%('VH','VL','FULL','H1','H2','tr'))
for f,h1,h2,n,VH,VL in rowsb[:8]:
    print('   %-7.3f %-7.3f %7.2f %7.2f %7.2f %4d'%(VH,VL,f,h1,h2,n))
print('   L2-only baseline                 %7.2f %7.2f %7.2f %4d'%score(0.60,0.31))
nb=sum(1 for r in rowsb if r[0]>1.47)
print('   %d/%d Layer-1 settings beat Layer-2-only overall'%(nb,len(rowsb)))
nb2=sum(1 for r in rowsb if r[1]>0.92)
print('   %d/%d improve the weak first half'%(nb2,len(rowsb)))

print('\n(c) vol window (VH=.033 VL=.020):')
for w in [20,30,45,60,90]:
    f,h1,h2,n=score(0.60,0.31,0.033,0.020,w=w)
    print('   w=%-3d full %.2f  H1 %.2f  H2 %.2f  trades %d'%(w,f,h1,h2,n))
