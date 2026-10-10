"""Offline: control = (b + a * sum(f(c_i) * w_i)) mod M for weight families; a,b free."""
import sys; sys.path.insert(0,'tools/analysis')
from control_fit import ROWS, variants
def charval(kind,ch):
    if kind=="ord": return ord(ch)
    if kind=="ordU": return ord(ch.upper())
    if kind=="alnum36":
        if ch.isdigit(): return int(ch)
        if ch.isalpha(): return ord(ch.upper())-55
        return 0
    if kind=="digitonly": return int(ch) if ch.isdigit() else 0
hits=[]
for M in [97,100,101,89,83,103,107,113,127,128,256,251,89,91,93,95,99]:
  for vn in [v for v,_ in variants("A;B")]:
    for kind in ["ord","ordU","alnum36","digitonly"]:
      for fam in ["pow_end","pow_start","lin_end","lin_start","flat"]:
        for B in (range(0,M) if fam.startswith("pow") else [1]):
          feats=[]
          for s,c,_ in ROWS:
            t=dict(variants(s))[vn]; n=len(t); tot=0
            for i,ch in enumerate(t):
              v=charval(kind,ch)
              if fam=="pow_end": w=pow(B,n-1-i,M)
              elif fam=="pow_start": w=pow(B,i,M)
              elif fam=="lin_end": w=n-i
              elif fam=="lin_start": w=i+1
              else: w=1
              tot+=v*w
            feats.append(tot%M)
          # solve a,b using first two rows
          for a in range(1,M):
            b=(ROWS[0][1]-a*feats[0])%M
            if all((b+a*f)%M==r[1] for f,r in zip(feats,ROWS)):
              hits.append((M,vn,kind,fam,B,a,b))
print(len(hits)); print(hits[:20])
