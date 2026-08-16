"""Structurally different Layer-2 variants, not just threshold tweaks."""
import csv,sys,statistics as st
sys.path.insert(0,'bot'); import strategy as S
rows=list(csv.DictReader(open('data/master.csv')))
D=[r['date'] for r in rows];Q=[float(r['quarter']) for r in rows]
M=[float(r['mesghal']) for r in rows];U=[float(r['usd']) for r in rows]
N=len(D);W=46
RP=[S.relative_premium(Q[i],M[i]) for i in range(N)]
def px(a,i): return {'Q':Q[i]/S.QUARTER_G,'M':M[i]/S.MESGHAL_G,'U':U[i]}[a]
def bench(lo,hi,c=0.02): return 1e9*(1-c)/px('Q',lo)*px('Q',hi-1)

def engine(target_fn,lo,hi,cost=0.02,mh=5):
    cur=target_fn(lo,'M') or 'M'
    units=1e9*(1-cost)/px(cur,lo); last=-10**9; n=0
    for i in range(lo,hi):
        t=target_fn(i,cur) or cur
        if t!=cur and i-last<mh: t=cur
        if t!=cur:
            val=units*px(cur,i)*(1-cost); units=val*(1-cost)/px(t,i)
            last=i; cur=t; n+=1
    return units*px(cur,hi-1),n

MID=W+(N-W)//2
def report(name,fn,mh=5):
    f,n=engine(fn,W,N,mh=mh); a,_=engine(fn,W,MID,mh=mh); b,_=engine(fn,MID,N,mh=mh)
    print('%-42s %6.2f %6.2f %6.2f %4d'%(name,f/bench(W,N),a/bench(W,MID),b/bench(MID,N),n))
    return f/bench(W,N)

print('%-42s %6s %6s %6s %4s'%('variant','FULL','H1','H2','tr'))
print('-'*70)
report('baseline fixed bands A=.60 B=.31',
       lambda i,c:'Q' if RP[i]<=0.31 else ('M' if RP[i]>=0.60 else c))

# 1. rolling-quantile bands
for win,qlo,qhi in [(120,0.25,0.75),(250,0.25,0.75),(250,0.20,0.80),(500,0.25,0.75)]:
    def mk(win=win,qlo=qlo,qhi=qhi):
        def f(i,c):
            if i<win: return c
            h=sorted(RP[i-win:i]); lo=h[int(qlo*len(h))]; hi=h[int(qhi*len(h))]
            return 'Q' if RP[i]<=lo else ('M' if RP[i]>=hi else c)
        return f
    report('rolling quantile w=%d [%.2f,%.2f]'%(win,qlo,qhi),mk())

# 2. z-score of RP
for win,z in [(250,1.0),(250,1.5),(500,1.0)]:
    def mk(win=win,z=z):
        def f(i,c):
            if i<win: return c
            h=RP[i-win:i]; m=sum(h)/len(h); s=st.pstdev(h)
            if s==0: return c
            zz=(RP[i]-m)/s
            return 'Q' if zz<=-z else ('M' if zz>=z else c)
        return f
    report('RP z-score w=%d |z|>%.1f'%(win,z),mk())

# 3. RP momentum / trend-following instead of mean-reversion
for k in [20,60]:
    def mk(k=k):
        def f(i,c):
            if i<k: return c
            return 'M' if RP[i]>RP[i-k] else 'Q'
        return f
    report('RP momentum %d-session'%k,mk())

# 4. asymmetric min-hold
for mh in [5,20,60]:
    report('fixed bands, min-hold=%d'%mh,
           lambda i,c:'Q' if RP[i]<=0.31 else ('M' if RP[i]>=0.60 else c),mh=mh)
print('-'*70)
print('hold-quarter benchmark = 1.00 by construction')
