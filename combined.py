import csv, math, statistics as st
QG=2.032*0.900; MG=4.6083*0.705
Q=list(csv.DictReader(open('data/qm_full.csv')))
U={r['date']:float(r['usd']) for r in csv.DictReader(open('data/usd_irr.csv'))}
rows=[(r['date'],float(r['quarter']),float(r['mesghal']),U[r['date']]) for r in Q if r['date'] in U]
dt=[r[0] for r in rows]; q=[r[1] for r in rows]; m=[r[2] for r in rows]; u=[r[3] for r in rows]
n=len(rows)
RP=[(q[i]/QG)/(m[i]/MG)-1 for i in range(n)]          # layer-2 signal
def vol(s,i,w):
    a=max(1,i-w+1); rs=[s[j]/s[j-1]-1 for j in range(a,i+1)]
    return st.pstdev(rs) if len(rs)>2 else 0
GV=[vol(m,i,30) for i in range(n)]                     # layer-1 signal
C=1e9

# ---- benchmarks (rial) ----
hold_q = C/q[0]*q[-1]
hold_m = C/m[0]*m[-1]
hold_u = C/u[0]*u[-1]

def run(A,B,vol_hi=None,vol_lo=None,cost=0.02,minhold_L2=5,minhold_L1=10,log=False):
    """
    Two-layer. Asset states: 'Q' quarter, 'M' mesghal, 'U' usd.
    LAYER 1 (macro): if vol_hi set and GV>=vol_hi -> go USD. return to gold when GV<=vol_lo.
    LAYER 2 (relative value, only while in gold): Q when RP<=B, M when RP>=A.
    """
    val=C; cur='M'          # start in mesghal
    lastL1=-999; lastL2=-999; tr=0; L=[]
    gold_pref='M'           # which gold instrument layer2 wants
    for i in range(n):
        px={'Q':q[i],'M':m[i],'U':u[i]}
        # ---- LAYER 2 decides preferred gold instrument ----
        if RP[i]<=B: gold_pref='Q'
        elif RP[i]>=A: gold_pref='M'
        # ---- LAYER 1 decides gold vs usd ----
        want_usd = (vol_hi is not None) and (
            (cur=='U' and GV[i]>vol_lo) or (cur!='U' and GV[i]>=vol_hi))
        if want_usd: target='U'
        else: target=gold_pref
        # ---- execute ----
        if target!=cur:
            isL1 = (target=='U') or (cur=='U')
            gate = (i-lastL1>=minhold_L1) if isL1 else (i-lastL2>=minhold_L2)
            if gate:
                val*= (1-cost)**2
                L.append((dt[i],f'{cur}->{target}', f'RP{RP[i]*100:.0f}% V{GV[i]*100:.1f}%'))
                cur=target; tr+=1
                if isL1: lastL1=i
                else: lastL2=i
        if i<n-1:
            val *= px if False else ({'Q':q[i+1]/q[i],'M':m[i+1]/m[i],'U':u[i+1]/u[i]}[cur])
    return (val,tr,cur,L) if log else (val,tr,cur)

print("="*82)
print("COMBINED TWO-LAYER SYSTEM — rial wealth, start 1.000 bn, 2%/leg")
print("="*82)
print(f"  period {dt[0]} -> {dt[-1]}  ({n} sessions)\n")
print("  BENCHMARKS")
print(f"    hold rial cash    {C/1e9:7.3f} bn   1.000x")
print(f"    hold USD          {hold_u/1e9:7.3f} bn   {hold_u/hold_m:.3f}x gold")
print(f"    hold مثقال        {hold_m/1e9:7.3f} bn   1.000x  <-- main benchmark")
print(f"    hold ربع سکه      {hold_q/1e9:7.3f} bn   {hold_q/hold_m:.3f}x gold")
print()
# Layer 2 alone
v2,t2,c2=run(0.60,0.31,vol_hi=None)
print(f"  LAYER 2 ONLY (A=60,B=31)          {v2/1e9:7.3f} bn   {v2/hold_m:.3f}x gold  ({t2} trades)")
# Layer 1 alone (gold=mesghal only)
def run_L1(vh,vl,cost=0.02,minhold=10):
    val=C; cur='M'; last=-999; tr=0
    for i in range(n):
        want = 'U' if ((cur=='U' and GV[i]>vl) or (cur!='U' and GV[i]>=vh)) else 'M'
        if want!=cur and i-last>=minhold:
            val*=(1-cost)**2; cur=want; last=i; tr+=1
        if i<n-1: val*= (m[i+1]/m[i]) if cur=='M' else (u[i+1]/u[i])
    return val,tr
for vh,vl in [(0.030,0.020),(0.035,0.025),(0.040,0.030)]:
    v1,t1=run_L1(vh,vl)
    print(f"  LAYER 1 ONLY (vol {vh*100:.1f}/{vl*100:.1f})       {v1/1e9:7.3f} bn   {v1/hold_m:.3f}x gold  ({t1} trades)")

print()
print("="*82); print("COMBINED: Layer1 (vol) + Layer2 (A/B)")
print("="*82)
print("   volHi/volLo " + "".join(f"  A{a*100:.0f}/B{b*100:.0f}" for a,b in [(0.60,0.31),(0.65,0.20),(0.60,0.30),(0.55,0.25)]))
best=None
for vh,vl in [(None,None),(0.030,0.020),(0.030,0.025),(0.035,0.025),(0.040,0.030),(0.040,0.015)]:
    lbl = "  OFF      " if vh is None else f"  {vh*100:.1f}/{vl*100:.1f}    "
    row=lbl
    for a,b in [(0.60,0.31),(0.65,0.20),(0.60,0.30),(0.55,0.25)]:
        v,t,c=run(a,b,vh,vl)
        row+=f"  {v/hold_m:6.3f}x"
        if best is None or v>best[0]: best=(v,a,b,vh,vl,t)
    print(row)
v,a,b,vh,vl,t=best
print()
print(f"  BEST COMBINED: A={a*100:.0f}% B={b*100:.0f}%  vol {vh if vh is None else f'{vh*100:.1f}/{vl*100:.1f}'}")
print(f"    {v/1e9:.3f} bn = {v/hold_m:.3f}x gold  ({t} trades)")
vv,tt,cc,L=run(a,b,vh,vl,log=True)
print("\n  TRADE LOG:")
for x in L: print("     ",*x)
print(f"    ending in {cc}")
