import csv,sys,statistics as st
sys.path.insert(0,'bot'); import strategy as S
rows=list(csv.DictReader(open('data/master.csv')))
D=[r['date'] for r in rows];Q=[float(r['quarter']) for r in rows]
M=[float(r['mesghal']) for r in rows];U=[float(r['usd']) for r in rows]
N=len(D);C=0.02
RP=[S.relative_premium(Q[i],M[i]) for i in range(N)]
VOL=[None]*N
for i in range(46,N): VOL[i]=S.vol45(M[max(0,i-45):i+1])
def price(a,i): return {'Q':Q[i]/S.QUARTER_G,'M':M[i]/S.MESGHAL_G,'U':U[i]}[a]
def run(A,B,VH,VL,lo=46,hi=None,two=True):
    hi=hi or N; cur='Q'; units=1e9/price(cur,lo); l1=l2=-999; n=0
    for i in range(lo,hi):
        v=VOL[i]; t=cur
        if two and v is not None:
            if cur=='U': t='U' if v>VL else ('Q' if RP[i]<=B else 'M')
            elif v>=VH: t='U'
            else: t='Q' if RP[i]<=B else ('M' if RP[i]>=A else cur)
        else:
            c2='M' if cur=='U' else cur
            t='Q' if RP[i]<=B else ('M' if RP[i]>=A else c2)
        if t!=cur:
            isl1='U' in (cur,t)
            if isl1 and i-l1<S.MINHOLD_L1: t=cur
            elif not isl1 and i-l2<S.MINHOLD_L2: t=cur
        if t!=cur:
            val=units*price(cur,i)*(1-C); units=val*(1-C)/price(t,i)
            if 'U' in (cur,t): l1=i
            else: l2=i
            cur=t; n+=1
    return units*price(cur,hi-1),n
base_q,_=run(0,9,9,9,two=False)  # never trades -> hold quarter
holdq=1e9/price('Q',46)*price('Q',N-1)
print('benchmark hold ربع = %.3f bn'%(holdq/1e9))
print()
print('A/B grid (two-layer), multiple of holding ربع:')
print('      B=  0.20   0.25   0.28   0.31   0.34   0.40')
beat=0;tot=0
for A in [0.50,0.55,0.60,0.65,0.70,0.75]:
    line='A=%.2f '%A
    for B in [0.20,0.25,0.28,0.31,0.34,0.40]:
        f,n=run(A,B,0.033,0.020)
        r=f/holdq; tot+=1; beat+= r>1
        line+=' %5.2fx'%r
    print(line)
print('\n%d/%d grid cells beat holding ربع'%(beat,tot))
print()
print('vol threshold sweep (A=0.60,B=0.31):')
for VH in [0.028,0.030,0.033,0.036,0.040]:
    for VL in [0.018,0.020,0.022]:
        f,n=run(0.60,0.31,VH,VL)
        print('   VH=%.3f VL=%.3f -> %.2fx  trades %d'%(VH,VL,f/holdq,n))
print()
print('split-sample (out-of-sample check):')
mid=46+(N-46)//2
print('  first half %s -> %s'%(D[46],D[mid]))
print('  second half %s -> %s'%(D[mid],D[-1]))
for lbl,lo,hi in [('H1',46,mid),('H2',mid,N)]:
    hq=1e9/price('Q',lo)*price('Q',hi-1)
    f2,n2=run(0.60,0.31,0.033,0.020,lo,hi)
    f4,n4=run(0.60,0.31,9,9,lo,hi,two=False)
    print('  %s hold-ربع %.3f bn | two-layer %.3f bn (%.2fx, %d tr) | L2only %.3f bn (%.2fx)'%(
        lbl,hq/1e9,f2/1e9,f2/hq,n2,f4/1e9,f4/hq))
