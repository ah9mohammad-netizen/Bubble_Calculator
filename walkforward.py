"""Rigorous validation: is A=0.70 a real improvement or curve-fit?
Rule: choose parameters ONLY on data before a cutoff, then measure after it."""
import csv,sys,statistics as st
sys.path.insert(0,'bot'); import strategy as S
rows=list(csv.DictReader(open('data/master.csv')))
D=[r['date'] for r in rows];Q=[float(r['quarter']) for r in rows]
M=[float(r['mesghal']) for r in rows];U=[float(r['usd']) for r in rows]
N=len(D);W=46
RP=[S.relative_premium(Q[i],M[i]) for i in range(N)]
def px(a,i): return {'Q':Q[i]/S.QUARTER_G,'M':M[i]/S.MESGHAL_G}[a]
def run(A,B,lo,hi,c=0.02,mh=5):
    cur='Q' if RP[lo]<=B else 'M'
    u=1e9*(1-c)/px(cur,lo); last=-10**9; n=0
    for i in range(lo,hi):
        t='Q' if RP[i]<=B else ('M' if RP[i]>=A else cur)
        if t!=cur and i-last<mh: t=cur
        if t!=cur:
            v=u*px(cur,i)*(1-c); u=v*(1-c)/px(t,i); last=i; cur=t; n+=1
    return u*px(cur,hi-1), n
def bench(lo,hi,c=0.02): return 1e9*(1-c)/px('Q',lo)*px('Q',hi-1)

GRID=[(A,B) for A in [0.50,0.55,0.60,0.65,0.70,0.75,0.80]
            for B in [0.15,0.18,0.20,0.22,0.25,0.28,0.31,0.34,0.37,0.40] if B<A]

print('='*78)
print('WALK-FORWARD: pick best (A,B) on TRAIN only, then measure on unseen TEST')
print('='*78)
print('%-12s %-22s %-13s %8s %8s'%('cutoff','train window','picked','train','TEST'))
res=[]
for frac in [0.40,0.50,0.60,0.70]:
    cut=W+int((N-W)*frac)
    best=max(GRID,key=lambda ab: run(ab[0],ab[1],W,cut)[0]/bench(W,cut))
    tr=run(best[0],best[1],W,cut)[0]/bench(W,cut)
    te=run(best[0],best[1],cut,N)[0]/bench(cut,N)
    res.append((best,tr,te))
    print('%-12s %s..%s  A=%.2f B=%.2f %8.2fx %8.2fx'%(
        D[cut],D[W],D[cut-1],best[0],best[1],tr,te))
print()
print('mean TEST multiple of the walk-forward picks: %.2fx'%(sum(r[2] for r in res)/len(res)))
print()
# how would fixed choices have done on the same TEST windows?
print('Same TEST windows, but with a FIXED parameter set chosen in advance:')
print('%-14s %8s %8s %8s %8s %8s'%('params','t=40%','t=50%','t=60%','t=70%','mean'))
for A,B in [(0.60,0.31),(0.65,0.31),(0.70,0.31),(0.70,0.20),(0.75,0.31)]:
    outs=[]
    for frac in [0.40,0.50,0.60,0.70]:
        cut=W+int((N-W)*frac)
        outs.append(run(A,B,cut,N)[0]/bench(cut,N))
    print('A=%.2f B=%.2f  '%(A,B)+' '.join('%8.2f'%o for o in outs)+' %8.2f'%(sum(outs)/len(outs)))
