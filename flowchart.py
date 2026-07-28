import csv, math, statistics as st
QG=2.032*0.900; MG=4.6083*0.705
Q=list(csv.DictReader(open('data/qm_full.csv')))
U={r['date']:float(r['usd']) for r in csv.DictReader(open('data/usd_irr.csv'))}
rows=[(r['date'],float(r['quarter']),float(r['mesghal']),U[r['date']]) for r in Q if r['date'] in U]
dt=[r[0] for r in rows]; q=[r[1] for r in rows]; m=[r[2] for r in rows]; u=[r[3] for r in rows]
n=len(rows)
RP=[(q[i]/QG)/(m[i]/MG)-1 for i in range(n)]
def vol(s,i,w):
    a=max(1,i-w+1); rs=[s[j]/s[j-1]-1 for j in range(a,i+1)]
    return st.pstdev(rs) if len(rs)>2 else 0.0
GV=[vol(m,i,45) for i in range(n)]
C=1e9; hold_m=C/m[0]*m[-1]; hold_q=C/q[0]*q[-1]; hold_u=C/u[0]*u[-1]

def flow(volhi=0.033, vollo=0.020, A=0.60, B=0.31,
         cost=0.02, mh1=10, mh2=5, start='M', log=False):
    """
    EXACT FLOW CHART:
      Layer1: vol45 >= volhi -> USD ; while USD, stay until vol45 <= vollo
      Layer2: only while in GOLD, pick Q or M from RP
    """
    val=C; cur=start; l1=-999; l2=-999; pref='M'; tr=0; L=[]
    for i in range(n):
        # layer2 preference (always computed)
        if RP[i]<=B: pref='Q'
        elif RP[i]>=A: pref='M'
        # layer1 gate
        if cur=='U':
            want = 'U' if GV[i]>vollo else pref
        else:
            want = 'U' if GV[i]>=volhi else pref
        if want!=cur:
            isL1 = (want=='U') or (cur=='U')
            ok = (i-l1>=mh1) if isL1 else (i-l2>=mh2)
            if ok:
                val*=(1-cost)**2
                L.append((dt[i], f'{cur}->{want}', f'RP={RP[i]*100:.0f}% vol={GV[i]*100:.1f}%',
                          'LAYER1' if isL1 else 'LAYER2'))
                cur=want; tr+=1
                if isL1: l1=i
                else: l2=i
        if i<n-1:
            val*={'Q':q[i+1]/q[i],'M':m[i+1]/m[i],'U':u[i+1]/u[i]}[cur]
    return (val,tr,cur,L) if log else (val,tr,cur)

print("="*86)
print("FULL FLOW CHART BACKTEST — 1 bn rial, 2%/leg, 375 sessions")
print("="*86)
print(f"  hold rial   {C/1e9:6.3f} bn   {C/hold_m:.3f}x gold")
print(f"  hold USD    {hold_u/1e9:6.3f} bn   {hold_u/hold_m:.3f}x gold")
print(f"  hold ربع    {hold_q/1e9:6.3f} bn   {hold_q/hold_m:.3f}x gold")
print(f"  hold مثقال  {hold_m/1e9:6.3f} bn   1.000x  <-- benchmark")
print(f"  TRUE optimum (3-asset hindsight) computed below\n")
v,t,c,L=flow(log=True)
print(f"  FLOW CHART  {v/1e9:6.3f} bn   {v/hold_m:.3f}x gold   ({t} trades, now in {c})\n")
print("  TRADE LOG:")
for x in L: print("     ",*x)
