import csv, statistics as st, math
from datetime import datetime
MG=4.6083*0.705
Q=list(csv.DictReader(open('data/qm_full.csv')))
U={r['date']:float(r['usd']) for r in csv.DictReader(open('data/usd_irr.csv'))}
rows=[(r['date'],float(r['quarter']),float(r['mesghal']),U[r['date']]) for r in Q if r['date'] in U]
d=[datetime.strptime(r[0],'%Y-%m-%d') for r in rows]
q=[r[1] for r in rows]; m=[r[2] for r in rows]; u=[r[3] for r in rows]
n=len(rows)
print(f"Aligned USD+gold: {n} sessions  {rows[0][0]} -> {rows[-1][0]}")
print(f"  USD    {u[0]:,.0f} -> {u[-1]:,.0f}   ({(u[-1]/u[0]-1)*100:+.0f}%)")
print(f"  Mesghal{m[0]:,.0f} -> {m[-1]:,.0f}   ({(m[-1]/m[0]-1)*100:+.0f}%)")
print(f"  -> mesghal outpaced USD by {((m[-1]/m[0])/(u[-1]/u[0])-1)*100:+.0f}% over the period\n")

# RATIO: mesghal per dollar  = how much gold one dollar buys (inverse)
# We want: when does USD outrun gold, and vice versa
ratio=[m[i]/u[i] for i in range(n)]   # mesghal price in DOLLARS
print("KEY SERIES: R = Mesghal_rial / USD_rial  = price of mesghal IN DOLLARS")
print(f"  R start {ratio[0]:,.1f}  end {ratio[-1]:,.1f}   ({(ratio[-1]/ratio[0]-1)*100:+.0f}%)")
print("  R rising  => gold outrunning USD  => HOLD GOLD")
print("  R falling => USD outrunning gold  => HOLD USD\n")

def sma(s,i,w): 
    a=max(0,i-w+1); return sum(s[a:i+1])/(i-a+1)

print("="*78)
print("MOMENTUM CROSSOVER SYSTEM: fast SMA vs slow SMA of R")
print("="*78)
def bt_cross(fast,slow,cost=0.02,minhold=5):
    """Hold mesghal when fast>slow, hold USD when fast<slow. Start in mesghal.
       Wealth measured in MESGHAL units."""
    um=1.0; uu=0.0; cur='M'; last=-999; tr=0; L=[]
    for i in range(n):
        if i<slow: continue
        f=sma(ratio,i,fast); s=sma(ratio,i,slow)
        if cur=='M' and f<s and i-last>=minhold:
            v=um*m[i]*(1-cost); uu=v/u[i]*(1-cost); um=0.0; cur='U'; last=i; tr+=1
            L.append((rows[i][0],'->USD'))
        elif cur=='U' and f>s and i-last>=minhold:
            v=uu*u[i]*(1-cost); um=v/m[i]*(1-cost); uu=0.0; cur='M'; last=i; tr+=1
            L.append((rows[i][0],'->GOLD'))
    final = um + uu*u[-1]/m[-1]
    return final,tr,cur,L
print("  benchmark: hold mesghal = 1.0000 |  hold USD =", round((1.0*m[0]/u[0])*u[-1]/m[-1],4))
print()
print("   fast\\slow " + "".join(f"{s:8d}" for s in [20,30,50,80,120]))
best=None
for f in [5,10,15,20,30]:
    row=f"     {f:3d}     "
    for s in [20,30,50,80,120]:
        if f>=s: row+="       -"; continue
        v,tr,cur,_=bt_cross(f,s)
        row+=f" {v:7.3f}"
        if best is None or v>best[0]: best=(v,f,s,tr)
    print(row)
print(f"\n  BEST: fast={best[1]} slow={best[2]} -> {best[0]:.4f} mesghal ({best[3]} trades)")
