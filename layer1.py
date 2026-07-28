import csv, math, statistics as st
QG=2.032*0.900; MG=4.6083*0.705
Q=list(csv.DictReader(open('data/qm_full.csv')))
U={r['date']:float(r['usd']) for r in csv.DictReader(open('data/usd_irr.csv'))}
rows=[(r['date'],float(r['quarter']),float(r['mesghal']),U[r['date']]) for r in Q if r['date'] in U]
dt=[r[0] for r in rows]; q=[r[1] for r in rows]; m=[r[2] for r in rows]; u=[r[3] for r in rows]
n=len(rows)
RP=[(q[i]/QG)/(m[i]/MG)-1 for i in range(n)]
R=[m[i]/u[i] for i in range(n)]     # gold priced in USD; rising = gold winning
C=1e9
hold_m=C/m[0]*m[-1]

def sma(s,i,w):
    a=max(0,i-w+1); return sum(s[a:i+1])/(i-a+1)
def vol(s,i,w):
    a=max(1,i-w+1); rs=[s[j]/s[j-1]-1 for j in range(a,i+1)]
    return st.pstdev(rs) if len(rs)>2 else 0.0
def ema(s,span):
    a=2/(span+1); o=[s[0]]
    for x in s[1:]: o.append(a*x+(1-a)*o[-1])
    return o
def rsi(s,p=14):
    o=[50.0]*len(s); g=[0]*len(s); l=[0]*len(s)
    for i in range(1,len(s)):
        d=s[i]-s[i-1]; g[i]=max(d,0); l[i]=max(-d,0)
    ag=sum(g[1:p+1])/p; al=sum(l[1:p+1])/p
    for i in range(p+1,len(s)):
        ag=(ag*(p-1)+g[i])/p; al=(al*(p-1)+l[i])/p
        o[i]=100 if al==0 else 100-100/(1+ag/al)
    return o

# LAYER 1 EVALUATION: pure USD-vs-MESGHAL switching (no layer 2)
def eval_L1(state, cost=0.02, minhold=10):
    """state[i] = 1 for USD, 0 for gold, None = keep. Returns rial wealth using MESGHAL as the gold leg."""
    val=C; cur=0; last=-999; tr=0
    for i in range(n):
        s=state[i]
        if s is not None and s!=cur and i-last>=minhold:
            val*=(1-cost)**2; cur=s; last=i; tr+=1
        if i<n-1: val*= (m[i+1]/m[i]) if cur==0 else (u[i+1]/u[i])
    return val,tr

print("="*84)
print("LAYER 1 INVESTIGATION — decide USD vs GOLD")
print("="*84)
print(f"  benchmark hold مثقال = {hold_m/1e9:.3f} bn | hold USD = {C/u[0]*u[-1]/1e9:.3f} bn")
print(f"  true optimum (hindsight, USD/mesghal only) = 5.831 bn = 1.640x\n")

cands={}
# A. gold volatility
for w in [20,30,45]:
    GV=[vol(m,i,w) for i in range(n)]
    for hi in [0.028,0.030,0.033,0.036]:
        for lo in [0.015,0.020,0.025]:
            if lo>=hi: continue
            s=[None]*n; cur=0
            for i in range(w,n):
                if cur==0 and GV[i]>=hi: cur=1
                elif cur==1 and GV[i]<=lo: cur=0
                s[i]=cur
            cands[f'VOL{w}_{hi*100:.1f}/{lo*100:.1f}']=s
# B. relative momentum (trend)
for k in [20,30,45,60]:
    for th in [0.0,-0.03,-0.06]:
        s=[None]*n
        for i in range(k,n):
            rel=(m[i]/m[i-k]-1)-(u[i]/u[i-k]-1)
            s[i]= 1 if rel<th else 0
        cands[f'MOM{k}_{th*100:.0f}']=s
# C. R vs its SMA
for w in [30,50,80,120]:
    s=[None]*n
    for i in range(w,n): s[i]= 0 if R[i]>sma(R,i,w) else 1
    cands[f'RvSMA{w}']=s
# D. RSI on R
for p in [14,21]:
    rr=rsi(R,p)
    for lo,hi in [(35,65),(40,60),(30,70)]:
        s=[None]*n
        for i in range(p+1,n):
            if rr[i]>=hi: s[i]=0
            elif rr[i]<=lo: s[i]=1
        cands[f'RSI{p}_{lo}/{hi}']=s
# E. gold drawdown from rolling high
for w in [30,60,90]:
    for dd in [0.05,0.08,0.12]:
        s=[None]*n; cur=0
        for i in range(w,n):
            pk=max(m[max(0,i-w):i+1]); d=m[i]/pk-1
            if cur==0 and d<=-dd: cur=1
            elif cur==1 and d>=-dd/3: cur=0
            s[i]=cur
        cands[f'DD{w}_{dd*100:.0f}']=s
res=[]
for k,v in cands.items():
    w_,t=eval_L1(v); res.append((k,w_,t))
res.sort(key=lambda x:-x[1])
print("  TOP 18 LAYER-1 INDICATORS (full sample):")
print("   indicator             wealth(bn) trades   x gold")
for k,w_,t in res[:18]:
    print(f"   {k:22s} {w_/1e9:7.3f}   {t:4d}   {w_/hold_m:6.3f}x")
print(f"\n  beating hold-gold: {sum(1 for _,w_,_ in res if w_>hold_m)}/{len(res)}")
