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
