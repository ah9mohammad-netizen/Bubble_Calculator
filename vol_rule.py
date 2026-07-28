exec(open('indicators.py').read().split('print("="*80)')[0])
import statistics as st
def vol(s,i,w):
    a=max(1,i-w+1); rs=[s[j]/s[j-1]-1 for j in range(a,i+1)]
    return st.pstdev(rs) if len(rs)>2 else 0
GV=[vol(m,i,30) for i in range(n)]
print("="*80); print("VOLATILITY-REGIME RULE: hold USD when gold vol is HIGH")
print("="*80)
print(f"  gold 30d vol: min {min(GV[30:])*100:.2f}%  median {st.median(GV[30:])*100:.2f}%  max {max(GV[30:])*100:.2f}%\n")
hm_=C/m[0]*m[-1]
def bt_vol(thr_hi,thr_lo,cost=0.02,minhold=10,w=30,log=False):
    val=C; cur=0; last=-999; tr=0; L=[]
    for i in range(w,n):
        v=GV[i]
        s=None
        if cur==0 and v>=thr_hi: s=1
        elif cur==1 and v<=thr_lo: s=0
        if s is not None and i-last>=minhold:
            val*=(1-cost)**2; cur=s; last=i; tr+=1
            L.append((dt[i],'USD' if s==1 else 'GOLD',round(v*100,2)))
        if i<n-1: val*= (m[i+1]/m[i]) if cur==0 else (u[i+1]/u[i])
    return (val,tr,L) if log else (val,tr)
print("  thr_hi  thr_lo   wealth(bn) trades  x gold")
best=None
for hi in [0.020,0.025,0.030,0.035,0.040]:
    for lo in [0.015,0.020,0.025,0.030]:
        if lo>hi: continue
        v,tr=bt_vol(hi,lo)
        if best is None or v>best[0]: best=(v,hi,lo,tr)
        print(f"   {hi*100:4.1f}%  {lo*100:4.1f}%   {v/1e9:8.3f}   {tr:3d}   {v/hm_:6.3f}x")
v,hi,lo,tr=best
print(f"\n  BEST: hi={hi*100:.1f}% lo={lo*100:.1f}% -> {v/1e9:.3f} bn = {v/hm_:.3f}x gold ({tr} trades)")
vv,tt,L=bt_vol(hi,lo,log=True)
for x in L: print("      ",*x)
print()
print("="*80); print("WALK-FORWARD on the vol rule")
print("="*80)
h=int(n*0.6)
def bt_win(hi,lo,s,e,cost=0.02,minhold=10,w=30):
    val=1.0; cur=0; last=-999
    for i in range(max(w,s),e):
        vx=GV[i]; sg=None
        if cur==0 and vx>=hi: sg=1
        elif cur==1 and vx<=lo: sg=0
        if sg is not None and i-last>=minhold: val*=(1-cost)**2; cur=sg; last=i
        if i<e-1: val*= (m[i+1]/m[i]) if cur==0 else (u[i+1]/u[i])
    return val
g1=m[h-1]/m[0]; g2=m[-1]/m[h]
print(f"  hold gold: train {g1:.3f}x  test {g2:.3f}x\n")
cands=[(hi_,lo_) for hi_ in [0.020,0.025,0.030,0.035,0.040] for lo_ in [0.015,0.020,0.025,0.030] if lo_<=hi_]
sc=sorted(((bt_win(a,b,0,h),a,b) for a,b in cands), reverse=True)
print("  top-5 in TRAIN -> TEST:")
for tr_,a,b in sc[:5]:
    te=bt_win(a,b,h,n)
    print(f"    hi={a*100:.1f} lo={b*100:.1f}  train {tr_:.3f}x ({'W' if tr_>g1 else 'L'})  test {te:.3f}x ({'W' if te>g2 else 'L'})")
allte=[bt_win(a,b,h,n) for a,b in cands]
print(f"\n  ALL {len(allte)} vol-configs in TEST: mean {st.mean(allte):.3f}x  best {max(allte):.3f}x  gold {g2:.3f}x")
print(f"  beating gold OOS: {sum(1 for x in allte if x>g2)}/{len(allte)}")
