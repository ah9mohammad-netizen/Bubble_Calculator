"""Q2: is vol45 the best USD-vs-GOLD signal? Test 8 families of alternatives.
Metric: correlation with FORWARD 30-day (gold - USD), plus a decile monotonicity
check. A signal is only useful if it separates future outcomes."""
import csv,sys,statistics as st
sys.path.insert(0,'bot'); import strategy as S
rows=list(csv.DictReader(open('data/master.csv')))
D=[r['date'] for r in rows];Q=[float(r['quarter']) for r in rows]
M=[float(r['mesghal']) for r in rows];U=[float(r['usd']) for r in rows]
N=len(D);H=30
RP=[S.relative_premium(Q[i],M[i]) for i in range(N)]

def sd(xs):
    return st.pstdev(xs) if len(xs)>1 else 0.0
def rets(s,i,w):
    a=s[max(0,i-w):i+1]
    return [a[k]/a[k-1]-1 for k in range(1,len(a))]

SIG={}
# 1. volatility of mesghal, several windows
for w in (15,30,45,60,90):
    SIG['vol%d_mesghal'%w]=lambda i,w=w: sd(rets(M,i,w)) if i>w else None
# 2. volatility of USD
for w in (45,90):
    SIG['vol%d_usd'%w]=lambda i,w=w: sd(rets(U,i,w)) if i>w else None
# 3. RELATIVE vol: gold vol / usd vol
SIG['volratio45']=lambda i: (sd(rets(M,i,45))/sd(rets(U,i,45))) if i>45 and sd(rets(U,i,45))>0 else None
# 4. momentum of gold vs usd
for w in (30,60,90,120):
    SIG['relmom%d'%w]=lambda i,w=w: (M[i]/M[i-w]-U[i]/U[i-w]) if i>w else None
# 5. gold priced in USD (domestic gold / dollar) - is gold rich vs the dollar?
GU=[M[i]/U[i] for i in range(N)]
for w in (60,120,250):
    SIG['gu_vs_sma%d'%w]=lambda i,w=w: (GU[i]/(sum(GU[i-w:i])/w)-1) if i>w else None
# 6. drawdown of mesghal from trailing peak
for w in (90,180):
    SIG['dd%d'%w]=lambda i,w=w: (M[i]/max(M[max(0,i-w):i+1])-1) if i>w else None
# 7. RSI of mesghal
def rsi(i,w=14):
    if i<=w: return None
    r=rets(M,i,w); g=[x for x in r if x>0]; l=[-x for x in r if x<0]
    ag=sum(g)/w; al=sum(l)/w
    return 100.0 if al==0 else 100-100/(1+ag/al)
SIG['rsi14']=rsi
# 8. the RP level itself (does a fat coin bubble predict gold weakness?)
SIG['RP_level']=lambda i: RP[i]
# 9. USD momentum alone
for w in (60,120):
    SIG['usdmom%d'%w]=lambda i,w=w: (U[i]/U[i-w]-1) if i>w else None

def corr(pairs):
    xs=[p[0] for p in pairs]; ys=[p[1] for p in pairs]
    mx=sum(xs)/len(xs); my=sum(ys)/len(ys)
    cov=sum((a-mx)*(b-my) for a,b in pairs)/len(pairs)
    sx,sy=sd(xs),sd(ys)
    return cov/(sx*sy) if sx>0 and sy>0 else 0.0

print('='*84)
print('Q2 — WHICH SIGNAL PREDICTS FORWARD 30-DAY (gold - USD)?  n=obs, |r| bigger=better')
print('='*84)
print('%-18s %5s %7s %11s %11s %s'%('signal','n','corr','bottom-dec','top-dec','spread'))
out=[]
for name,f in SIG.items():
    obs=[]
    for i in range(46,N-H):
        v=f(i)
        if v is None: continue
        fwd=(M[i+H]/M[i]-1)-(U[i+H]/U[i]-1)
        obs.append((v,fwd))
    if len(obs)<200: continue
    obs.sort()
    k=max(1,len(obs)//10)
    bot=sum(o[1] for o in obs[:k])/k*100
    top=sum(o[1] for o in obs[-k:])/k*100
    out.append((abs(corr(obs)),name,len(obs),corr(obs),bot,top,bot-top))
out.sort(reverse=True)
for a,name,n,r,bot,top,spr in out:
    print('%-18s %5d %+7.3f %+10.1fpp %+10.1fpp %+7.1fpp'%(name,n,r,bot,top,spr))
