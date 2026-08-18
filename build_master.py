import csv,glob
def load(pat):
    d={}
    for f in glob.glob(pat):
        for r in csv.reader(open(f)):
            if not r or not r[0].startswith('20'): continue
            try: d[r[0]]=float(r[1])
            except: pass
    return d
q={};m={}
for r in csv.DictReader(open('data/qm_ext.csv')):
    if r['quarter']: q[r['date']]=float(r['quarter'])
    if r['mesghal']: m[r['date']]=float(r['mesghal'])
q.update(load('data/raw/rob_*.csv')); m.update(load('data/raw/mesghal_*.csv'))
u=load('data/raw/usd_close_*.csv')
for r in csv.DictReader(open('data/usd_irr.csv')):
    if r.get('usd') and r['date'] not in u: u[r['date']]=float(r['usd'])
# ---- manual exclusions only --------------------------------------------
# I tried an automatic one-day-spike filter at 4% and it removed REAL events
# (2024-05-18 Raisi helicopter crash, 2026-02-02 war spike, 2022-06-11).
# Iranian gold genuinely moves 8-14% in a day on news, so no purely
# statistical rule can separate signal from placeholder.
# Only rows VERIFIED as tgju placeholders are dropped: identical OHLC
# (open=low=high=close) AND ~10% off both neighbours AND a non-trading day.
BAD_USD = {'2021-12-02','2021-12-09','2021-12-16','2021-12-30','2022-01-13'}
for k in BAD_USD: u.pop(k, None)
print('  dropped %d verified-placeholder USD rows' % len(BAD_USD))

d=sorted(set(q)&set(m)&set(u))
with open('data/master.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['date','quarter','mesghal','usd'])
    for x in d: w.writerow([x,int(q[x]),int(m[x]),int(u[x])])
print('master.csv %d rows  %s -> %s'%(len(d),d[0],d[-1]))
bad=0
for name,s in (('quarter',q),('mesghal',m),('usd',u)):
    for i in range(1,len(d)):
        r=s[d[i]]/s[d[i-1]]-1
        if abs(r)>0.15: print('  !! %s %s %+.1f%%'%(name,d[i],r*100)); bad+=1
print('extreme moves flagged:',bad)
