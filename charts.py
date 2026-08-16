import csv,sys
sys.path.insert(0,'bot')
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import strategy as S
from cpi import CPI

rows=list(csv.DictReader(open('data/master.csv')))
D=[r['date'] for r in rows];Q=[float(r['quarter']) for r in rows]
M=[float(r['mesghal']) for r in rows];U=[float(r['usd']) for r in rows]
N=len(D);C=S.COST_PER_LEG
RP=[S.relative_premium(Q[i],M[i]) for i in range(N)]
VOL=[None]*N
for i in range(46,N): VOL[i]=S.vol45(M[max(0,i-45):i+1])
def px(a,i): return {'Q':Q[i]/S.QUARTER_G,'M':M[i]/S.MESGHAL_G,'U':U[i]}[a]
START=46; BUD=1_000_000_000.0

def first_target(mode):
    if mode=='hold_u': return 'U'
    if mode=='hold_m': return 'M'
    if mode=='hold_q': return 'Q'
    i=START
    if mode=='qm':
        return 'Q' if RP[i]<=S.B_BUY_QUARTER else ('M' if RP[i]>=S.A_SELL_QUARTER else 'M')
    v=VOL[i]
    if v is not None and v>=S.VOL_HI: return 'U'
    return 'Q' if RP[i]<=S.B_BUY_QUARTER else 'M'

def run(mode):
    # everyone starts in CASH and pays exactly one entry cost -> fair comparison
    cur=first_target(mode); units=BUD*(1-C)/px(cur,START); l1=l2=-999; tr=[]; curve=[]
    for i in range(START,N):
        v=VOL[i]; t=cur
        if mode=='hold_u': t='U'
        elif mode=='hold_q': t='Q'
        elif mode=='hold_m': t='M'
        elif mode=='qm':
            c2='M' if cur=='U' else cur
            t='Q' if RP[i]<=S.B_BUY_QUARTER else ('M' if RP[i]>=S.A_SELL_QUARTER else c2)
        elif mode=='two':
            if v is None: t=cur
            elif cur=='U': t='U' if v>S.VOL_LO else ('Q' if RP[i]<=S.B_BUY_QUARTER else 'M')
            elif v>=S.VOL_HI: t='U'
            else:
                t='Q' if RP[i]<=S.B_BUY_QUARTER else ('M' if RP[i]>=S.A_SELL_QUARTER else cur)
        if t!=cur:
            isl1='U' in (cur,t)
            if isl1 and i-l1<S.MINHOLD_L1: t=cur
            elif not isl1 and i-l2<S.MINHOLD_L2: t=cur
        if t!=cur:
            val=units*px(cur,i)*(1-C); units=val*(1-C)/px(t,i)
            tr.append((i,cur,t)); 
            if 'U' in (cur,t): l1=i
            else: l2=i
            cur=t
        curve.append(units*px(cur,i))
    return curve,tr

modes=[('hold_u','Hold USD','#888888','-'),
       ('hold_q','Hold QUARTER COIN (rob-e sekkeh)','#c0392b','-'),
       ('hold_m','Hold MESGHAL (melted gold)','#e67e22','-'),
       ('qm','SWITCH: quarter <-> mesghal (Layer 2)','#2980b9','-'),
       ('two','TWO-LAYER STRATEGY (Layer 1 + 2)','#16a085','-')]
res={m:run(m) for m,_,_,_ in modes}
dates=D[START:]
# CPI curve on same dates
def cpi_at(d):
    m=d[:7]
    return CPI.get(m, CPI[max(CPI)] if m>max(CPI) else CPI[min(CPI)])
c0=cpi_at(dates[0])
cpi_curve=[BUD*cpi_at(d)/c0 for d in dates]

import datetime
X=[datetime.date(int(d[:4]),int(d[5:7]),int(d[8:])) for d in dates]

plt.rcParams['font.family']='DejaVu Sans'
fig,(ax,ax2)=plt.subplots(2,1,figsize=(15,11.5),gridspec_kw={'height_ratios':[3,1.15]})

for m,lbl,col,ls in modes:
    cur=res[m][0]
    lw=3.2 if m=='two' else 1.9
    z=5 if m=='two' else 2
    ax.plot(X,[v/1e9 for v in cur],label=lbl,color=col,lw=lw,ls=ls,zorder=z)
ax.plot(X,[v/1e9 for v in cpi_curve],label='Inflation (Iran CPI) — break-even',
        color='#7f8c8d',lw=2.2,ls=':',zorder=3)

# mark trades of two-layer
tr=res['two'][1]
lab={'Q':'QUARTER','M':'MESGHAL','U':'USD'}
offs=[(-10,-38),(8,-34),(-18,26),(10,-36),(6,22)]
for k,(i,a,b) in enumerate(tr):
    xi=X[i-START]; yi=res['two'][0][i-START]/1e9
    ax.plot([xi],[yi],'o',color='#16a085',ms=10,mec='white',mew=1.8,zorder=7)
    dx,dy=offs[k] if k<len(offs) else (6,14)
    ax.annotate('%d. %s\u2192%s\n%s'%(k+1,lab[a],lab[b],D[i]),(xi,yi),
                textcoords='offset points',xytext=(dx,dy),fontsize=8.2,
                color='white',fontweight='bold',ha='center',zorder=8,
                bbox=dict(boxstyle='round,pad=0.35',fc='#16a085',ec='white',lw=1.2,alpha=0.96),
                arrowprops=dict(arrowstyle='-',color='#16a085',lw=1.4))

ax.set_title('Iran Gold/FX Bubble-Arbitrage — growth of 1 billion rial\n'
             '%s to %s  (%d sessions, ~%.1f years, 2%% cost per leg)'%(
             dates[0],dates[-1],len(dates),len(dates)/250),
             fontsize=14,fontweight='bold',pad=14)
ax.set_ylabel('Portfolio value (billion rial)',fontsize=11)
ax.legend(loc='upper left',fontsize=10.5,framealpha=0.95)
ax.grid(alpha=0.25)
ax.set_yscale('log')
ax.set_yticks([1,1.5,2,3,4,5,6,7,8,9,10])
ax.get_yaxis().set_major_formatter(FuncFormatter(lambda v,p:'%g'%v))
ax.text(0.995,0.03,'log scale',transform=ax.transAxes,ha='right',fontsize=9,color='#555')

# final labels
for m,lbl,col,ls in modes:
    v=res[m][0][-1]/1e9
    ax.annotate('  %.2f bn'%v,(X[-1],v),color=col,fontsize=10.5,fontweight='bold',va='center',annotation_clip=False)

# panel 2 : CPI p2p inflation
mk=sorted(CPI); 
mx=[datetime.date(int(k[:4]),int(k[5:]),15) for k in mk]
p2p=[]
for k in mk:
    py='%04d-%02d'%(int(k[:4])-1,int(k[5:]))
    p2p.append((CPI[k]/CPI[py]-1)*100 if py in CPI else None)
mm=[(a,b) for a,b in zip(mx,p2p) if b is not None]
ax2.bar([a for a,b in mm],[b for a,b in mm],width=22,color='#c0392b',alpha=0.8)
ax2.set_title('Iran CPI point-to-point inflation (Statistical Center of Iran)',fontsize=11,fontweight='bold')
ax2.set_ylabel('% vs same month\nprevious year',fontsize=10)
ax2.grid(alpha=0.25,axis='y')
ax2.axhline(0,color='k',lw=0.8)
for a,b in mm[::4]:
    ax2.annotate('%.0f%%'%b,(a,b),ha='center',va='bottom',fontsize=8.5)
fig.autofmt_xdate()
plt.subplots_adjust(right=0.90)
plt.tight_layout(rect=[0,0,0.945,1])
plt.savefig('charts/growth.png',dpi=155,facecolor='white')
print('saved charts/growth.png')

# ---- chart 2: grams of gold ----
fig2,ax3=plt.subplots(figsize=(14,7))
g0=BUD/(M[START]/S.MESGHAL_G)   # melted-gold-equivalent at t0 (same for all plans)
for m,lbl,col,ls in modes:
    cur=res[m][0]
    grams=[cur[j]/(M[START+j]/S.MESGHAL_G) for j in range(len(cur))]
    lw=3.2 if m=='two' else 1.9
    ax3.plot(X,grams,label='%s  → %.1f g'%(lbl,grams[-1]),color=col,lw=lw,zorder=5 if m=='two' else 2)
ax3.axhline(g0,color='k',ls='--',lw=1.6,label='START = %.1f g  (break-even: keeping your gold)'%g0)
ax3.fill_between(X,g0,[max(g0,1) for _ in X],color='none')
ax3.set_title('The real scoreboard — GOLD you end up owning (melted-gold equivalent)\n'
              'same 1 bn rial start, %s to %s   |  above the dashed line = you GAINED gold'%(dates[0],dates[-1]),
              fontsize=13.5,fontweight='bold',pad=12)
ax3.set_ylabel('grams of fine gold (melted equivalent)',fontsize=11)
ax3.axhspan(0,g0,color='#c0392b',alpha=0.055,zorder=0)
ax3.legend(loc='upper left',fontsize=10.5)
ax3.grid(alpha=0.25)
fig2.autofmt_xdate()
plt.tight_layout(); plt.savefig('charts/grams.png',dpi=155,facecolor='white')
print('saved charts/grams.png')

# ---- summary numbers ----
print()
print('%-26s %10s %10s %9s %8s %8s'%('approach','final bn','vs start','vs CPI','grams','trades'))
cpi_mult=cpi_curve[-1]/BUD
for m,lbl,col,ls in modes:
    cur,t=res[m]
    f=cur[-1]; gr=f/(M[N-1]/S.MESGHAL_G)
    print('%-26s %10.3f %9.1f%% %8.2fx %8.1f %8d'%(lbl,f/1e9,(f/BUD-1)*100,(f/BUD)/cpi_mult,gr,len(t)))
print()
print('CPI multiple over window: %.2fx  (inflation %.0f%%)'%(cpi_mult,(cpi_mult-1)*100))
print('start grams: %.2f g'%g0)

# ---- chart 3: summary bars ----
fig3,(bx,bx2)=plt.subplots(1,2,figsize=(15,6.4))
names=[l for _,l,_,_ in modes]; cols=[c for _,_,c,_ in modes]
short=['Hold\nUSD','Hold\nQUARTER','Hold\nMESGHAL','SWITCH\nQ<->M','TWO-LAYER\nSTRATEGY']
finals=[res[m][0][-1]/1e9 for m,_,_,_ in modes]
b=bx.bar(short,finals,color=cols,edgecolor='white',lw=2)
bx.axhline(cpi_curve[-1]/1e9,color='#7f8c8d',ls=':',lw=2.4)
bx.annotate('inflation break-even  %.2f bn'%(cpi_curve[-1]/1e9),
            (4.45,cpi_curve[-1]/1e9),ha='right',va='bottom',fontsize=9.5,color='#555',fontweight='bold')
for r,v in zip(b,finals):
    bx.annotate('%.2f bn'%v,(r.get_x()+r.get_width()/2,v),ha='center',va='bottom',
                fontsize=11,fontweight='bold')
bx.set_title('Final value of 1 bn rial after ~2.8 years',fontsize=12.5,fontweight='bold')
bx.set_ylabel('billion rial',fontsize=11); bx.grid(alpha=0.25,axis='y'); bx.set_ylim(0,11)

grams=[res[m][0][-1]/(M[N-1]/S.MESGHAL_G) for m,_,_,_ in modes]
b2=bx2.bar(short,grams,color=cols,edgecolor='white',lw=2)
bx2.axhline(g0,color='k',ls='--',lw=2)
bx2.annotate('START %.1f g — below this line you LOST gold'%g0,(0.02,g0),
             xycoords=('axes fraction','data'),ha='left',va='top',fontsize=9.5,
             fontweight='bold',xytext=(0,-4),textcoords='offset points')
for r,v in zip(b2,grams):
    bx2.annotate('%.1f g'%v,(r.get_x()+r.get_width()/2,v),ha='center',va='bottom',
                 fontsize=11,fontweight='bold')
bx2.set_title('Gold actually owned at the end (melted-gold equivalent)',fontsize=12.5,fontweight='bold')
bx2.set_ylabel('grams of fine gold',fontsize=11); bx2.grid(alpha=0.25,axis='y'); bx2.set_ylim(0,45)
plt.tight_layout(); plt.savefig('charts/summary.png',dpi=155,facecolor='white')
print('saved charts/summary.png')
