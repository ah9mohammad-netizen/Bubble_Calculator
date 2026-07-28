import csv, math, statistics as st
Q=list(csv.DictReader(open('data/qm_full.csv')))
U={r['date']:float(r['usd']) for r in csv.DictReader(open('data/usd_irr.csv'))}
rows=[(r['date'],float(r['mesghal']),U[r['date']]) for r in Q if r['date'] in U]
dt=[r[0] for r in rows]; m=[r[1] for r in rows]; u=[r[2] for r in rows]
n=len(rows); C=1e9
R=[m[i]/u[i] for i in range(n)]          # mesghal priced in USD. up = gold winning
hm=C/m[0]*m[-1]

def sma(s,i,w):
    a=max(0,i-w+1); return sum(s[a:i+1])/(i-a+1)
def ema_series(s,span):
    a=2/(span+1); out=[s[0]]
    for x in s[1:]: out.append(a*x+(1-a)*out[-1])
    return out
def rsi_series(s,p=14):
    out=[50.0]*len(s); g=[0]*len(s); l=[0]*len(s)
    for i in range(1,len(s)):
        d=s[i]-s[i-1]; g[i]=max(d,0); l[i]=max(-d,0)
    ag=sum(g[1:p+1])/p; al=sum(l[1:p+1])/p
    for i in range(p+1,len(s)):
        ag=(ag*(p-1)+g[i])/p; al=(al*(p-1)+l[i])/p
        out[i]=100 if al==0 else 100-100/(1+ag/al)
    return out

def backtest(sig,cost=0.02,minhold=1):
    """sig[i] in {0:gold,1:usd,None:hold prev}. RIAL wealth."""
    val=C; cur=0; last=-999; tr=0; L=[]
    for i in range(n):
        s=sig[i]
        if s is not None and s!=cur and i-last>=minhold:
            val*=(1-cost)**2; cur=s; last=i; tr+=1
            L.append((dt[i],'USD' if s==1 else 'GOLD'))
        if i<n-1: val*= (m[i+1]/m[i]) if cur==0 else (u[i+1]/u[i])
    return val,tr,L

print("="*80); print("INDICATOR SUITE on R = mesghal/USD   (R up = gold winning)")
print("="*80)
print(f"  benchmark hold gold = {hm/1e9:.3f} bn | TRUE optimum @2% = 5.831 bn (1.64x)\n")
res=[]

# 1 EMA crossover
for f in [5,8,10,12,15,20,25]:
    for s in [20,26,30,40,50,60,80]:
        if f>=s: continue
        ef=ema_series(R,f); es=ema_series(R,s)
        sig=[0 if ef[i]>es[i] else 1 for i in range(n)]
        v,tr,_=backtest(sig); res.append(('EMA%d/%d'%(f,s),v,tr))
# 2 MACD
for f,s,sg in [(12,26,9),(8,21,5),(5,35,5),(10,30,9)]:
    ef=ema_series(R,f); es=ema_series(R,s)
    macd=[ef[i]-es[i] for i in range(n)]; sl=ema_series(macd,sg)
    sig=[0 if macd[i]>sl[i] else 1 for i in range(n)]
    v,tr,_=backtest(sig); res.append(('MACD%d/%d/%d'%(f,s,sg),v,tr))
# 3 RSI
for p in [14,21,30]:
    r=rsi_series(R,p)
    for lo,hi in [(30,70),(40,60),(35,65),(45,55)]:
        sig=[None]*n
        for i in range(n):
            if r[i]>=hi: sig[i]=0
            elif r[i]<=lo: sig[i]=1
        v,tr,_=backtest(sig); res.append(('RSI%d_%d/%d'%(p,lo,hi),v,tr))
# 4 price vs SMA
for w in [20,30,50,80,100,120]:
    sig=[0 if R[i]>sma(R,i,w) else 1 for i in range(n)]
    v,tr,_=backtest(sig); res.append(('R>SMA%d'%w,v,tr))
# 5 Rate of change
for k in [10,20,30,45,60,90]:
    sig=[None]*n
    for i in range(k,n):
        sig[i]= 0 if R[i]>R[i-k] else 1
    v,tr,_=backtest(sig); res.append(('ROC%d'%k,v,tr))
# 6 Bollinger on R
for w in [20,30,50]:
    for k in [1.0,1.5,2.0]:
        sig=[None]*n
        for i in range(w,n):
            mu=sma(R,i,w); sd=st.pstdev(R[max(0,i-w+1):i+1])
            if sd==0: continue
            z=(R[i]-mu)/sd
            if z>k: sig[i]=0
            elif z<-k: sig[i]=1
        v,tr,_=backtest(sig); res.append(('BB%d_%.1f'%(w,k),v,tr))
res.sort(key=lambda x:-x[1])
print("  TOP 20 INDICATORS (in-sample, full period):")
print("   indicator          wealth(bn)  trades   x gold")
for nm,v,tr in res[:20]:
    print(f"   {nm:18s} {v/1e9:8.3f}   {tr:4d}   {v/hm:6.3f}x")
print(f"\n  configs beating hold-gold: {sum(1 for _,v,_ in res if v>hm)}/{len(res)}")
