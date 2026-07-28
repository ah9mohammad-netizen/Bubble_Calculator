import csv, statistics as st
QG=2.032*0.900; MG=4.6083*0.705
QM=list(csv.DictReader(open('data/qm_ext.csv')))
U={r['date']:float(r['usd']) for r in csv.DictReader(open('data/usd_irr.csv'))}
# ---- window A: quarter+mesghal only (longer) ----
dA=[r['date'] for r in QM]; qA=[float(r['quarter']) for r in QM]; mA=[float(r['mesghal']) for r in QM]
# ---- window B: all three ----
B=[(r['date'],float(r['quarter']),float(r['mesghal']),U[r['date']]) for r in QM if r['date'] in U]
dB=[x[0] for x in B]; qB=[x[1] for x in B]; mB=[x[2] for x in B]; uB=[x[3] for x in B]
C=1e9; COST=0.02
def vol(s,i,w):
    a=max(1,i-w+1); rs=[s[j]/s[j-1]-1 for j in range(a,i+1)]
    return st.pstdev(rs) if len(rs)>2 else 0.0

def strat4(d,q,m,A=0.60,Bb=0.31,cost=COST,minhold=5):
    """quarter<->mesghal only. start in mesghal."""
    n=len(d); RP=[(q[i]/QG)/(m[i]/MG)-1 for i in range(n)]
    val=C; cur='M'; last=-999; tr=0; L=[]
    for i in range(n):
        tgt = 'Q' if RP[i]<=Bb else ('M' if RP[i]>=A else cur)
        if tgt!=cur and i-last>=minhold:
            val*=(1-cost)**2; L.append((d[i],f'{cur}->{tgt}',f'RP={RP[i]*100:.0f}%')); cur=tgt; last=i; tr+=1
        if i<n-1: val*= (q[i+1]/q[i]) if cur=='Q' else (m[i+1]/m[i])
    return val,tr,cur,L

def strat5(d,q,m,u,A=0.60,Bb=0.31,vhi=0.033,vlo=0.020,cost=COST,mh1=10,mh2=5):
    n=len(d); RP=[(q[i]/QG)/(m[i]/MG)-1 for i in range(n)]
    GV=[vol(m,i,45) for i in range(n)]
    val=C; cur='M'; l1=-999; l2=-999; pref='M'; tr=0; L=[]
    for i in range(n):
        if RP[i]<=Bb: pref='Q'
        elif RP[i]>=A: pref='M'
        want = ('U' if GV[i]>vlo else pref) if cur=='U' else ('U' if GV[i]>=vhi else pref)
        if want!=cur:
            isL1=(want=='U') or (cur=='U')
            if (i-l1>=mh1) if isL1 else (i-l2>=mh2):
                val*=(1-cost)**2
                L.append((d[i],f'{cur}->{want}',f'RP={RP[i]*100:.0f}% V={GV[i]*100:.1f}%','L1' if isL1 else 'L2'))
                cur=want; tr+=1
                if isL1: l1=i
                else: l2=i
        if i<n-1: val*={'Q':q[i+1]/q[i],'M':m[i+1]/m[i],'U':u[i+1]/u[i]}[cur]
    return val,tr,cur,L

print("="*88)
print("WINDOW A — quarter & mesghal only:", dA[0], "->", dA[-1], f"({len(dA)} sessions)")
print("="*88)
hq=C/qA[0]*qA[-1]; hm=C/mA[0]*mA[-1]
v4,t4,c4,L4=strat4(dA,qA,mA)
print(f"  2. hold ربع سکه       {hq/1e9:7.3f} bn   {(hq/C-1)*100:+7.1f}%    0 trades")
print(f"  3. hold مثقال         {hm/1e9:7.3f} bn   {(hm/C-1)*100:+7.1f}%    0 trades")
print(f"  4. Q<->M switching    {v4/1e9:7.3f} bn   {(v4/C-1)*100:+7.1f}%    {t4} trades")
print(f"     vs hold مثقال: {v4/hm:.3f}x     vs hold ربع: {v4/hq:.3f}x")
print("\n   trades:")
for x in L4: print("      ",*x)
print()
print("="*88)
print("WINDOW B — all three assets:", dB[0], "->", dB[-1], f"({len(dB)} sessions)")
print("="*88)
hu=C/uB[0]*uB[-1]; hq2=C/qB[0]*qB[-1]; hm2=C/mB[0]*mB[-1]
v4b,t4b,_,_=strat4(dB,qB,mB)
v5,t5,c5,L5=strat5(dB,qB,mB,uB)
print(f"  1. hold USD           {hu/1e9:7.3f} bn   {(hu/C-1)*100:+7.1f}%    0 trades")
print(f"  2. hold ربع سکه       {hq2/1e9:7.3f} bn   {(hq2/C-1)*100:+7.1f}%    0 trades")
print(f"  3. hold مثقال         {hm2/1e9:7.3f} bn   {(hm2/C-1)*100:+7.1f}%    0 trades")
print(f"  4. Q<->M switching    {v4b/1e9:7.3f} bn   {(v4b/C-1)*100:+7.1f}%    {t4b} trades")
print(f"  5. TWO-LAYER          {v5/1e9:7.3f} bn   {(v5/C-1)*100:+7.1f}%    {t5} trades   (now in {c5})")
print("\n   two-layer trades:")
for x in L5: print("      ",*x)
