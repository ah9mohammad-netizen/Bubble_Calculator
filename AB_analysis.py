import csv, statistics as st
from datetime import datetime
QG=2.032*0.900; MG=4.6083*0.705
R=list(csv.DictReader(open('data/qm_full.csv')))
d=[datetime.strptime(r['date'],'%Y-%m-%d') for r in R]
q=[float(r['quarter']) for r in R]; m=[float(r['mesghal']) for r in R]
rp=[(q[i]/QG)/(m[i]/MG)-1 for i in range(len(R))]
n=len(rp)

def run(A,B,cost=0.0075,minhold=5,log=False):
    uq=1.0; um=0.0; cur='Q'; last=-999; tr=0; L=[]
    for i in range(n):
        if cur=='Q' and rp[i]>=A and i-last>=minhold:
            v=uq*q[i]*(1-cost); um=v/m[i]*(1-cost); uq=0.0
            cur='M'; last=i; tr+=1; L.append((str(d[i].date()),'SELL Q @',f"{rp[i]*100:.1f}%"))
        elif cur=='M' and rp[i]<=B and i-last>=minhold:
            v=um*m[i]*(1-cost); uq=v/q[i]*(1-cost); um=0.0
            cur='Q'; last=i; tr+=1; L.append((str(d[i].date()),'BUY  Q @',f"{rp[i]*100:.1f}%"))
    coins = uq + um*m[-1]/q[-1]
    return (coins,tr,cur,L) if log else (coins,tr,cur)

print("="*78)
print("STEP 1 — HOW OFTEN DOES THE LINE CROSS EACH LEVEL?  (your method)")
print("="*78)
print("  A candidates (sell high):")
for A in [0.40,0.45,0.50,0.55,0.60,0.65,0.70,0.75]:
    up=sum(1 for i in range(1,n) if rp[i]>=A and rp[i-1]<A)
    print(f"    A={A*100:3.0f}%  upward crossings = {up}")
print("  B candidates (buy low):")
for B in [0.13,0.15,0.16,0.18,0.20,0.22,0.25,0.28,0.30]:
    dn=sum(1 for i in range(1,n) if rp[i]<=B and rp[i-1]>B)
    print(f"    B={B*100:3.0f}%  downward crossings = {dn}")
print()
print("  -> usable pairs need BOTH to fire repeatedly.")

print("="*78)
print("STEP 2 — FULL A/B GRID, wealth in QUARTER COINS (start = 1 coin)")
print("="*78)
print("  BENCHMARK: hold your 1 quarter coin = 1.0000\n")
As=[0.40,0.45,0.50,0.55,0.60,0.65,0.70]
Bs=[0.15,0.16,0.18,0.20,0.22,0.25,0.28,0.30]
print("   A\\B  " + "".join(f"{b*100:8.0f}%" for b in Bs))
G={}
for A in As:
    row=f"  {A*100:3.0f}%  "
    for B in Bs:
        c,tr,cur=run(A,B); G[(A,B)]=(c,tr,cur); row+=f" {c:7.3f}"
    print(row)
print("\n   trades")
print("   A\\B  " + "".join(f"{b*100:8.0f}%" for b in Bs))
for A in As:
    print(f"  {A*100:3.0f}%  " + "".join(f" {G[(A,b)][1]:7d}" for b in Bs))
navs=[v[0] for v in G.values()]
print(f"\n  ALL {len(navs)} cells: min={min(navs):.3f} max={max(navs):.3f} median={st.median(navs):.3f}")
print(f"  cells beating 1.000 (hold coin): {sum(1 for x in navs if x>1.0)}/{len(navs)}")
print(f"  WORST cell still = {min(navs):.3f} coins ({(min(navs)-1)*100:+.1f}%)")

print()
print("="*78)
print("STEP 3 — ROBUSTNESS: is the best cell a plateau or a spike?")
print("="*78)
best=max(G.items(), key=lambda kv: kv[1][0])
A0,B0=best[0]
print(f"  best = A={A0*100:.0f}% B={B0*100:.0f}%  -> {best[1][0]:.3f}")
print("\n  neighbourhood of best:")
for A in [A0-0.05,A0,A0+0.05]:
    r=f"    A={A*100:3.0f}%  "
    for B in [B0-0.02,B0,B0+0.02]:
        c,_,_=run(A,B); r+=f" B={B*100:2.0f}%:{c:6.3f}"
    print(r)
print()
print("="*78)
print("STEP 4 — COST SENSITIVITY of a few good pairs")
print("="*78)
for (A,B) in [(0.60,0.30),(0.65,0.20),(0.55,0.20),(0.50,0.20),(0.45,0.22)]:
    line=f"  A={A*100:.0f}% B={B*100:.0f}%  "
    for c in [0.0,0.0075,0.015,0.02]:
        v,_,_=run(A,B,cost=c); line+=f" c={c*100:4.1f}%:{v:6.3f}"
    print(line)
