"""Iran CPI monthly index, SCI base 1400=100.
VERIFIED ANCHORS (published figures, sourced in PRESENTATION.md):
  2023-06 189.3 | 2023-07 193.0 | 2023-08 197.7 | 2023-09 201.7
  2023-10 206.5 | 2023-11 210.9 | 2023-12 217.0 | 2024-01 222.7   (SCI monthly series)
  2026-01 469.4 | 2026-02 513.6 | 2026-07 676.9                   (SCI releases)
  2025-01 = 469.4/1.600 = 293.4   (SCI p2p Jan-2026 = 60.0%)
  2025-02 = 513.6/1.681 = 305.5   (SCI p2p Feb-2026 = 68.1%)
Between anchors: geometric interpolation. Cross-check: 469.4/222.7 = 2.108
vs (1+.32)x(1+.60) = 2.112  -> anchors are mutually consistent (0.2%).
"""
ANCHORS = {
 '2023-06':189.3,'2023-07':193.0,'2023-08':197.7,'2023-09':201.7,
 '2023-10':206.5,'2023-11':210.9,'2023-12':217.0,'2024-01':222.7,
 '2025-01':293.4,'2025-02':305.5,
 '2026-01':469.4,'2026-02':513.6,'2026-07':676.9,
}
def months(a,b):
    ya,ma=int(a[:4]),int(a[5:]); yb,mb=int(b[:4]),int(b[5:])
    out=[]
    while (ya,ma)<=(yb,mb):
        out.append('%04d-%02d'%(ya,ma)); ma+=1
        if ma==13: ma=1; ya+=1
    return out
def build():
    ks=sorted(ANCHORS); allm=months(ks[0],ks[-1]); cpi={}
    for i in range(len(ks)-1):
        a,b=ks[i],ks[i+1]; seg=months(a,b); n=len(seg)-1
        r=(ANCHORS[b]/ANCHORS[a])**(1.0/n)
        for j,m in enumerate(seg): cpi[m]=ANCHORS[a]*(r**j)
    cpi[ks[-1]]=ANCHORS[ks[-1]]
    return cpi
CPI=build()
if __name__=='__main__':
    ks=sorted(CPI)
    print('months',len(ks),ks[0],'->',ks[-1])
    for m in ks:
        p=None
        py='%04d-%02d'%(int(m[:4])-1,int(m[5:]))
        if py in CPI: p=(CPI[m]/CPI[py]-1)*100
        print('  %s  %7.1f  %s'%(m,CPI[m],('p2p %+5.1f%%'%p) if p else ''))
