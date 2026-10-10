M=97
def h(s,B,val): 
    n=len(s); return sum(val(c)*pow(B,n-1-i,M) for i,c in enumerate(s))%M
for nm,val in [("ord",ord),("digit",lambda c:int(c))]:
  for B in range(2,M):
    d1=(h("120000",B,val)-h("100000",B,val))%M
    d2=(h("40000",B,val)-h("100000",B,val))%M
    # need alpha with alpha*d1=43, alpha*d2=74
    for a in range(1,M):
        if a*d1%M==43 and a*d2%M==74: print(nm,"B",B,"alpha",a)
print("done")
