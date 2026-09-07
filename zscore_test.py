"""Implement + validate the basis z-score spec before wiring it into the bot."""
import csv, sys, statistics as st
sys.path.insert(0,'bot')
import strategy as S

# spot
import glob
spot={}
for f in glob.glob('data/raw/ons_*.csv'):
    for r in csv.reader(open(f)):
        if r and r[0].startswith('20'): spot[r[0]]=float(r[1])
# domestic
dom={r['date']:r for r in csv.DictReader(open('data/master.csv'))}
dates=sorted(set(spot)&set(dom))
print('overlap: %d sessions  %s -> %s'%(len(dates),dates[0],dates[-1]))

OZ=S.OZ_G; MG=S.MESGHAL_G
rows=[]
for d in dates:
    xau=spot[d]; usd=float(dom[d]['usd']); mes=float(dom[d]['mesghal'])
    fair = xau/OZ*usd*MG          # rial per mesghal implied by world gold + USD
    basis = mes/fair - 1
    rows.append((d,basis,mes,usd,xau))

print()
print('basis stats: min %+.1f%%  median %+.1f%%  max %+.1f%%'%(
    min(r[1] for r in rows)*100,
    st.median([r[1] for r in rows])*100,
    max(r[1] for r in rows)*100))

# rolling 75 z-score
W=75
Z=[None]*len(rows)
for i in range(len(rows)):
    if i<W: continue
    win=[r[1] for r in rows[i-W:i]]
    m=sum(win)/len(win); s=st.pstdev(win)
    if s>0: Z[i]=(rows[i][1]-m)/s

zz=[z for z in Z if z is not None]
print('z-score  : min %+.2f  median %+.2f  max %+.2f   (n=%d)'%(
    min(zz),st.median(zz),max(zz),len(zz)))

# state machine exactly as specified
Z_HI, Z_LO, PERSIST, COOLDOWN = 1.75, 0.50, 3, 30
state='GOLD'; last=-10**9; run_hi=0; run_lo=0; trades=[]
for i,z in enumerate(Z):
    if z is None: continue
    run_hi = run_hi+1 if z > Z_HI else 0
    run_lo = run_lo+1 if z < Z_LO else 0
    if state=='GOLD' and run_hi>=PERSIST and i-last>=COOLDOWN:
        state='USD'; last=i; trades.append((rows[i][0],'GOLD->USD',z)); run_hi=0
    elif state=='USD' and run_lo>=PERSIST and i-last>=COOLDOWN:
        state='GOLD'; last=i; trades.append((rows[i][0],'USD->GOLD',z)); run_lo=0

print()
print('transitions with z>%.2f / z<%.2f, persist %d, cooldown %d:'%(Z_HI,Z_LO,PERSIST,COOLDOWN))
for d,k,z in trades: print('   %s  %-10s z=%+.2f'%(d,k,z))
print('   total %d over %.1f years = %.1f/yr'%(len(trades),len(dates)/250,len(trades)/(len(dates)/250)))
print()
print('current: z=%+.2f  state=%s'%(Z[-1] if Z[-1] is not None else float('nan'), state))
