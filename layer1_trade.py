"""Do the best-correlating signals actually EARN anything as a trading rule?
Layer 2 (A=.60 B=.31) always on; Layer 1 overlay varies. Reported x hold-quarter."""
import csv,sys,statistics as st
sys.path.insert(0,'bot'); import strategy as S
rows=list(csv.DictReader(open('data/master.csv')))
D=[r['date'] for r in rows];Q=[float(r['quarter']) for r in rows]
M=[float(r['mesghal']) for r in rows];U=[float(r['usd']) for r in rows]
N=len(D);W=46;A,B=0.60,0.31
RP=[S.relative_premium(Q[i],M[i]) for i in range(N)]
def sd(xs): return st.pstdev(xs) if len(xs)>1 else 0.0
def rets(s,i,w):
    a=s[max(0,i-w):i+1]; return [a[k]/a[k-1]-1 for k in range(1,len(a))]
def px(a,i): return {'Q':Q[i]/S.QUARTER_G,'M':M[i]/S.MESGHAL_G,'U':U[i]}[a]
def bench(lo,hi,c=0.02): return 1e9*(1-c)/px('Q',lo)*px('Q',hi-1)

def engine(l1,lo,hi,c=0.02,mh1=10,mh2=5):
    cur='Q' if RP[lo]<=B else 'M'
    u=1e9*(1-c)/px(cur,lo); a1=a2=-10**9; n=0
    for i in range(lo,hi):
        risk=l1(i) if l1 else False   # True => be in USD
        if risk is None: t=cur
        elif risk: t='U'
        else:
            c2='M' if cur=='U' else cur
            t='Q' if RP[i]<=B else ('M' if RP[i]>=A else c2)
        if t!=cur:
            isl1='U' in (cur,t)
            if isl1 and i-a1<mh1: t=cur
            elif not isl1 and i-a2<mh2: t=cur
        if t!=cur:
            v=u*px(cur,i)*(1-c); u=v*(1-c)/px(t,i)
            if 'U' in (cur,t): a1=i
            else: a2=i
            cur=t; n+=1
    return u*px(cur,hi-1),n

def hyst(valf,hi_th,lo_th):
    state={'on':False}
    def f(i):
        v=valf(i)
        if v is None: return None
        if state['on']:
            if v<=lo_th: state['on']=False
        else:
            if v>=hi_th: state['on']=True
        return state['on']
    return f

MID=W+(N-W)//2
def show(name,mk):
    state_full=mk(); f,n=engine(state_full,W,N)
    a,_=engine(mk(),W,MID); b,_=engine(mk(),MID,N)
    print('%-30s %7.2f %7.2f %7.2f %4d'%(name,f/bench(W,N),a/bench(W,MID),b/bench(MID,N),n))

print('%-30s %7s %7s %7s %4s'%('Layer-1 overlay','FULL','H1','H2','tr'))
print('-'*62)
show('none (Layer 2 only)',lambda: None)
show('vol45 mesghal 3.3/2.0',lambda: hyst(lambda i: sd(rets(M,i,45)) if i>45 else None,0.033,0.020))
show('vol45 mesghal 4.0/1.6',lambda: hyst(lambda i: sd(rets(M,i,45)) if i>45 else None,0.040,0.016))
show('vol90 mesghal 2.8/2.0',lambda: hyst(lambda i: sd(rets(M,i,90)) if i>90 else None,0.028,0.020))
show('vol90 mesghal 3.0/2.2',lambda: hyst(lambda i: sd(rets(M,i,90)) if i>90 else None,0.030,0.022))
show('vol90 USD 1.5/1.0',lambda: hyst(lambda i: sd(rets(U,i,90)) if i>90 else None,0.015,0.010))
show('vol90 USD 2.0/1.2',lambda: hyst(lambda i: sd(rets(U,i,90)) if i>90 else None,0.020,0.012))
show('vol45 USD 1.5/1.0',lambda: hyst(lambda i: sd(rets(U,i,45)) if i>45 else None,0.015,0.010))
show('dd180 < -12% -> USD',lambda: hyst(lambda i: -(M[i]/max(M[max(0,i-180):i+1])-1) if i>180 else None,0.12,0.05))
