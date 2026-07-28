import csv, statistics as st
from datetime import datetime

QG=2.032*0.900; MG=4.6083*0.705

def load():
    R=list(csv.DictReader(open('data/qm_workbook.csv')))
    d=[datetime.strptime(r['date'],'%Y-%m-%d') for r in R]
    q=[float(r['quarter']) for r in R]; m=[float(r['mesghal']) for r in R]
    rp=[(q[i]/QG)/(m[i]/MG)-1 for i in range(len(R))]
    return d,q,m,rp

d,q,m,rp=load(); n=len(rp)

def bt(buy,sell,cost=0.0075,minhold=5,timestop=None,nonewlow=0,
       start=0,end=None,ret_log=False):
    """NAV in fine grams. Start holding mesghal = 1.0 fine gram."""
    end = n if end is None else end
    units=1.0/MG; cur='M'; last=-999; entry_i=None; tr=0; log=[]
    for i in range(start,end):
        if cur=='M':
            ok = rp[i]<=buy
            if ok and nonewlow:
                a=max(start,i-nonewlow)
                if rp[i] <= min(rp[a:i+1]): ok=False   # still making new lows
            if ok and i-last>=minhold:
                v=units*m[i]*(1-cost); units=v/q[i]*(1-cost)
                cur='Q'; last=i; entry_i=i; tr+=1
                log.append((str(d[i].date()),'BUY ',round(rp[i]*100,1)))
        else:
            hit = rp[i]>=sell
            if not hit and timestop and i-entry_i>=timestop: hit=True
            if hit and i-last>=minhold:
                v=units*q[i]*(1-cost); units=v/m[i]*(1-cost)
                cur='M'; last=i; tr+=1
                log.append((str(d[i].date()),'SELL',round(rp[i]*100,1)))
    fg=units*(m[end-1] if cur=='M' else q[end-1])/(m[end-1]/MG)
    return (fg,tr,cur,log) if ret_log else (fg,tr,cur)

# ---------- baselines ----------
hold_m = 1.0
hold_q = ((1.0*(m[0]/MG))/q[0]*q[-1])/(m[-1]/MG)
print("="*78)
print("BASELINES (NAV in fine grams, start 1.000g, full window)")
print("="*78)
print(f"  hold مثقال  : {hold_m:.4f} g   <-- the benchmark to beat")
print(f"  hold ربع    : {hold_q:.4f} g")
print()

# ---------- 1. COARSE GRID ----------
print("="*78)
print("1. COARSE GRID — final NAV in grams (cost 0.75%/leg, no filters)")
print("="*78)
buys=[0.18,0.20,0.22,0.25,0.28,0.30,0.32,0.35]
sells=[0.45,0.50,0.55,0.60,0.65,0.70,0.75]
print("  buy\\sell " + "".join(f"{s*100:7.0f}%" for s in sells))
grid={}
for b in buys:
    row=f"   {b*100:4.0f}%   "
    for s in sells:
        fg,tr,cur=bt(b,s)
        grid[(b,s)]=(fg,tr,cur)
        row+=f" {fg:6.3f}"
    print(row)
print()
print("  same grid, TRADE COUNT")
print("  buy\\sell " + "".join(f"{s*100:7.0f}%" for s in sells))
for b in buys:
    row=f"   {b*100:4.0f}%   "
    for s in sells:
        row+=f" {grid[(b,s)][1]:6d}"
    print(row)

# ---------- 2. WITH TIME STOP + NO-NEW-LOW FILTER ----------
print()
print("="*78)
print("2. WITH FILTERS: timestop=75 sessions, no-new-low=60")
print("="*78)
print("  buy\\sell " + "".join(f"{s*100:7.0f}%" for s in sells))
g2={}
for b in buys:
    row=f"   {b*100:4.0f}%   "
    for s in sells:
        fg,tr,cur=bt(b,s,timestop=75,nonewlow=60)
        g2[(b,s)]=(fg,tr)
        row+=f" {fg:6.3f}"
    print(row)
print("  trade counts")
print("  buy\\sell " + "".join(f"{s*100:7.0f}%" for s in sells))
for b in buys:
    print(f"   {b*100:4.0f}%   " + "".join(f" {g2[(b,s)][1]:6d}" for s in sells))

# ---------- 3. TRADE-LEVEL STATS (the honest view) ----------
print()
print("="*78)
print("3. HOW MANY INDEPENDENT SIGNALS DOES THE DATA EVEN CONTAIN?")
print("="*78)
for b in [0.20,0.25,0.30]:
    cross=[i for i in range(1,n) if rp[i]<=b and rp[i-1]>b]
    print(f"  RP crosses BELOW {b*100:.0f}%: {len(cross)} times -> {[str(d[i].date()) for i in cross]}")
for s in [0.50,0.60,0.70]:
    cross=[i for i in range(1,n) if rp[i]>=s and rp[i-1]<s]
    print(f"  RP crosses ABOVE {s*100:.0f}%: {len(cross)} times -> {[str(d[i].date()) for i in cross]}")
