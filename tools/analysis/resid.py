import sys; sys.path.insert(0,'tools/analysis')
from control_fit import ROWS
M=97
def H(t,B=10,val=ord):
    n=len(t); return sum(val(ch)*pow(B,n-1-i,M) for i,ch in enumerate(t))%M
for name,val in [("ord",ord),("digitsonly",lambda c:int(c) if c.isdigit() else 0)]:
  print(name)
  for s,c,_ in ROWS:
    h=H(s,10,val); print(f"{s:42s} c={c:3d} H={h:3d} resid(c+3H)={(c+3*h)%M}")
