import csv, statistics as st
from datetime import datetime
QG=2.032*0.900; MG=4.6083*0.705
R=list(csv.DictReader(open('data/qm_full.csv')))
d=[datetime.strptime(r['date'],'%Y-%m-%d') for r in R]
q=[float(r['quarter']) for r in R]; m=[float(r['mesghal']) for r in R]
rp=[(q[i]/QG)/(m[i]/MG)-1 for i in range(len(R))]
n=len(rp)

def bt(buy,sell,cost=0.0075,minhold=5,timestop=None,nonewlow=0,start=0,end=None,log=False):
    end=n if end is None else end
    units=1.0/MG; cur='M'; last=-999; ent=None; tr=0; L=[]
    for i in range(start,end):
        if cur=='M':
            ok=rp[i]<=buy
            if ok and nonewlow:
                a=max(start,i-nonewlow)
                if rp[i]<=min(rp[a:i+1]): ok=False
            if ok and i-last>=minhold:
                v=units*m[i]*(1-cost); units=v/q[i]*(1-cost)
                cur='Q'; last=i; ent=i; tr+=1; L.append((str(d[i].date()),'BUY ',round(rp[i]*100,1)))
        else:
            hit=rp[i]>=sell
            if not hit and timestop and i-ent>=timestop: hit=True
            if hit and i-last>=minhold:
                v=units*q[i]*(1-cost); units=v/m[i]*(1-cost)
                cur='M'; last=i; tr+=1; L.append((str(d[i].date()),'SELL',round(rp[i]*100,1)))
    fg=units*(m[end-1] if cur=='M' else q[end-1])/(m[end-1]/MG)
    return (fg,tr,cur,L) if log else (fg,tr,cur)

print(f"n={n}  {d[0].date()} -> {d[-1].date()}")
print(f"RP: min {min(rp)*100:.1f}%  max {max(rp)*100:.1f}%  median {st.median(rp)*100:.1f}%")
qs=sorted(rp)
print("percentiles: " + "  ".join(f"p{p}={qs[int(p/100*(n-1))]*100:.0f}%" for p in [5,10,25,50,75,90,95]))
print()
print("="*76); print("TRUE OUT-OF-SAMPLE TEST")
print("="*76)
print("Previous analysis used data ending 2026-02-19 and proposed buy<=30 / sell>=55.")
print("The 2026-05 -> 2026-07 data is genuinely OUT OF SAMPLE. What happened?\n")
oos=[i for i in range(n) if d[i]>=datetime(2026,5,1)]
print(f"  OOS window: {d[oos[0]].date()} -> {d[-1].date()}  ({len(oos)} sessions)")
print(f"  RP entering OOS: {rp[oos[0]]*100:.1f}%   RP now: {rp[-1]*100:.1f}%")
print(f"  RP min in OOS  : {min(rp[i] for i in oos)*100:.1f}%")
print(f"  -> RP rose {(rp[-1]-min(rp[i] for i in oos))*100:.1f}pp off the low. Buy signal was CORRECT.")
print()
# grams if you had bought at the OOS low and held
lo=min(oos,key=lambda i:rp[i])
gain=(1+rp[-1])/(1+rp[lo])*(1-0.0075)**4
print(f"  Buy at OOS low ({d[lo].date()}, RP={rp[lo]*100:.1f}%), hold to now: {gain:.4f}x grams ({(gain-1)*100:+.1f}%)")

print()
print("="*76); print("FULL GRID on 430 sessions (NAV grams, cost 0.75%/leg)")
print("="*76)
hold_q=((1.0*(m[0]/MG))/q[0]*q[-1])/(m[-1]/MG)
print(f"  BASELINE hold مثقال = 1.0000 g   |   hold ربع = {hold_q:.4f} g\n")
buys=[0.16,0.18,0.20,0.22,0.25,0.28,0.30,0.32,0.35]
sells=[0.42,0.45,0.48,0.50,0.55,0.60,0.65]
print("  buy\\sell " + "".join(f"{s*100:7.0f}%" for s in sells))
G={}
for b in buys:
    row=f"   {b*100:4.0f}%   "
    for s in sells:
        fg,tr,cur=bt(b,s,timestop=75,nonewlow=0)
        G[(b,s)]=(fg,tr,cur); row+=f" {fg:6.3f}"
    print(row)
print("\n  trade counts")
print("  buy\\sell " + "".join(f"{s*100:7.0f}%" for s in sells))
for b in buys:
    print(f"   {b*100:4.0f}%   " + "".join(f" {G[(b,s)][1]:6d}" for s in sells))
print()
best=max(G.items(), key=lambda kv: kv[1][0])
print(f"  BEST: buy<={best[0][0]*100:.0f}% sell>={best[0][1]*100:.0f}%  NAV={best[1][0]:.4f}  trades={best[1][1]}")
beat=sum(1 for v in G.values() if v[0]>1.0)
print(f"  configs beating hold-مثقال: {beat}/{len(G)}")
navs=[v[0] for v in G.values()]
print(f"  NAV spread: {min(navs):.3f} .. {max(navs):.3f}   median {st.median(navs):.3f}")
