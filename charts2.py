"""Final charts: 1,000,000 toman start, indexed growth, full history."""
import csv,sys,statistics as st,datetime
sys.path.insert(0,'bot')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import strategy as S
from cpi import CPI

rows=list(csv.DictReader(open('data/master.csv')))
D=[r['date'] for r in rows]
Q=[float(r['quarter']) for r in rows]      # rial
M=[float(r['mesghal']) for r in rows]      # rial
U=[float(r['usd']) for r in rows]          # rial
N=len(D); C=0.02; W=46
START_TOMAN=1_000_000
START_RIAL=START_TOMAN*10                  # 1 toman = 10 rial

RP=[S.relative_premium(Q[i],M[i]) for i in range(N)]
def sd(x): return st.pstdev(x) if len(x)>1 else 0.0
def rets(s,i,w):
    a=s[max(0,i-w):i+1]; return [a[k]/a[k-1]-1 for k in range(1,len(a))]
V90=[None]*N
for i in range(91,N): V90[i]=sd(rets(M,i,90))
def px(a,i): return {'Q':Q[i]/S.QUARTER_G,'M':M[i]/S.MESGHAL_G,'U':U[i]}[a]

A,B = S.A_SELL_QUARTER, S.B_BUY_QUARTER   # 0.60 / 0.31
VH,VL = 0.030, 0.022                      # vol90 (validated this session)

def run(mode):
    if mode=='hold_u': cur='U'
    elif mode=='hold_m': cur='M'
    elif mode=='hold_q': cur='Q'
    else: cur='Q' if RP[W]<=B else 'M'
    units=START_RIAL*(1-C)/px(cur,W)
    a1=a2=-10**9; tr=[]; curve=[]; on=False
    for i in range(W,N):
        t=cur
        if mode in ('hold_u','hold_m','hold_q'): pass
        elif mode=='l2':
            t='Q' if RP[i]<=B else ('M' if RP[i]>=A else cur)
        elif mode=='two':
            v=V90[i]
            if v is not None:
                if on and v<=VL: on=False
                elif not on and v>=VH: on=True
            if on: t='U'
            else:
                c2='M' if cur=='U' else cur
                t='Q' if RP[i]<=B else ('M' if RP[i]>=A else c2)
        if t!=cur:
            isl1='U' in (cur,t)
            if isl1 and i-a1<10: t=cur
            elif not isl1 and i-a2<5: t=cur
        if t!=cur:
            val=units*px(cur,i)*(1-C); units=val*(1-C)/px(t,i)
            tr.append((i,cur,t))
            if 'U' in (cur,t): a1=i
            else: a2=i
            cur=t
        curve.append(units*px(cur,i))
    return curve,tr

MODES=[('hold_u','Hold USD','#8c8c8c'),
       ('hold_q','Hold QUARTER COIN (ربع سکه)','#c0392b'),
       ('hold_m','Hold MESGHAL (مثقال)','#e67e22'),
       ('l2','LAYER 2 ONLY — switch quarter <-> mesghal','#2471a3'),
       ('two','TWO-LAYER — Layer 2 + vol90 USD gate','#148f77')]
res={m:run(m) for m,_,_ in MODES}
dates=D[W:]
X=[datetime.date(*map(int,d.split('-'))) for d in dates]

def cpi_at(d):
    m=d[:7]; ks=sorted(CPI)
    return CPI.get(m, CPI[ks[-1]] if m>ks[-1] else CPI[ks[0]])
c0=cpi_at(dates[0])
cpi_curve=[START_RIAL*cpi_at(d)/c0 for d in dates]

# ---------- indexed growth (start = 100) ----------
def idx(c): return [v/START_RIAL*100 for v in c]

plt.rcParams['font.family']='DejaVu Sans'
fig,(ax,ax2)=plt.subplots(2,1,figsize=(16,12),gridspec_kw={'height_ratios':[3.1,1]})

for m,lbl,col in MODES:
    lw=3.2 if m in ('l2','two') else 1.8
    ax.plot(X,idx(res[m][0]),label=lbl,color=col,lw=lw,zorder=6 if m in ('l2','two') else 2)
ax.plot(X,idx(cpi_curve),label='Iran CPI (inflation) — break-even',color='#555',lw=2.2,ls=':',zorder=3)

lab={'Q':'QUARTER','M':'MESGHAL','U':'USD'}
for k,(i,a,b) in enumerate(res['two'][1]):
    xi=X[i-W]; yi=idx(res['two'][0])[i-W]
    ax.plot([xi],[yi],'o',color='#148f77',ms=8,mec='white',mew=1.5,zorder=9)
for k,(i,a,b) in enumerate(res['l2'][1]):
    xi=X[i-W]; yi=idx(res['l2'][0])[i-W]
    ax.plot([xi],[yi],'s',color='#2471a3',ms=7,mec='white',mew=1.5,zorder=9)

ax.set_yscale('log')
ticks=[100,200,400,800,1600,3200,6400]
ax.set_yticks(ticks); ax.set_yticklabels([f'{t:,}' for t in ticks])
ax.set_ylabel('INDEXED GROWTH  (start = 100)',fontsize=12,fontweight='bold')
ax.set_title('Iran Gold/FX Bubble Arbitrage — 1,000,000 toman invested %s\n'
             'indexed growth to %s   ·   %d sessions (~%.1f years)   ·   2%% cost per leg'
             %(dates[0],dates[-1],len(dates),len(dates)/250),
             fontsize=15,fontweight='bold',pad=14)
ax.legend(loc='upper left',fontsize=11,framealpha=.95)
ax.grid(alpha=.25,which='both')
ax.text(.995,.02,'log scale · ● two-layer trade  ■ layer-2 trade',transform=ax.transAxes,
        ha='right',fontsize=9,color='#555')
ends=[(idx(res[m][0])[-1],col) for m,_,col in MODES]+[(idx(cpi_curve)[-1],'#555')]
ends.sort()
prev=None
for v,col in ends:
    y=v
    if prev is not None and y/prev<1.13: y=prev*1.13   # de-overlap on log axis
    ax.annotate('  %s'%f'{v:,.0f}',(X[-1],y),color=col,fontsize=11,
                fontweight='bold',va='center',annotation_clip=False)
    prev=y

# inflation panel
mk=sorted(CPI); mx=[datetime.date(int(k[:4]),int(k[5:]),15) for k in mk]
p2p=[]
for k in mk:
    py='%04d-%02d'%(int(k[:4])-1,int(k[5:]))
    p2p.append((CPI[k]/CPI[py]-1)*100 if py in CPI else None)
mm=[(a,b) for a,b in zip(mx,p2p) if b is not None and a>=X[0]]
ax2.bar([a for a,b in mm],[b for a,b in mm],width=22,color='#c0392b',alpha=.85)
ax2.set_title('Iran CPI point-to-point inflation (Statistical Center of Iran)',fontsize=11,fontweight='bold')
ax2.set_ylabel('% vs same month\nprevious year',fontsize=10)
ax2.grid(alpha=.25,axis='y')
for a,b in mm[::6]: ax2.annotate('%.0f%%'%b,(a,b),ha='center',va='bottom',fontsize=8.5)
fig.autofmt_xdate()
plt.tight_layout(rect=[0,0,0.955,1])
plt.savefig('charts/indexed_growth.png',dpi=150,facecolor='white')
print('saved charts/indexed_growth.png')

# ---------- summary table ----------
print()
print('%-46s %14s %10s %9s %7s'%('plan','final toman','index','vs CPI','trades'))
cpi_mult=cpi_curve[-1]/START_RIAL
for m,lbl,col in MODES:
    f=res[m][0][-1]; tom=f/10
    print('%-46s %14s %10.0f %8.2fx %7d'%(lbl,f'{tom:,.0f}',f/START_RIAL*100,(f/START_RIAL)/cpi_mult,len(res[m][1])))
print('%-46s %14s %10.0f %8.2fx'%('Iran CPI (inflation)',f'{cpi_curve[-1]/10:,.0f}',cpi_mult*100,1.0))

# ---------- trade history ----------
FA={'Q':'ربع سکه','M':'مثقال','U':'USD'}
EN={'Q':'QUARTER','M':'MESGHAL','U':'USD'}
for mode,title in (('l2','LAYER 2 ONLY'),('two','TWO-LAYER')):
    print()
    print('%s — transition / exchange history'%title)
    print('  %-4s %-12s %-9s %-9s %8s %9s'%('#','date','from','to','RP','vol90'))
    for k,(i,a,b) in enumerate(res[mode][1],1):
        v='%.2f%%'%(V90[i]*100) if V90[i] else '   n/a'
        print('  %-4d %-12s %-9s %-9s %7.1f%% %9s'%(k,D[i],EN[a],EN[b],RP[i]*100,v))
    print('  total: %d trades over %.1f years = one every %.0f months'%(
        len(res[mode][1]),len(dates)/250,len(dates)/250*12/max(len(res[mode][1]),1)))
