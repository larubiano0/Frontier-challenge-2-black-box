"""Offline brute force of the control (E202) algorithm over recorded rows. No network."""
import itertools, zlib, json
# (message without control, control, valid?)  valid=True => control accepted (response reached a later stage or succeeded)
ROWS = [
 ("ALTA;Lucia",82,True),("ALTA;Mateo",3,True),("CONSULTA;AC-0001",14,True),
 ("DEPOSITO;AC-0001;250000",86,True),("TRANSFER;AC-0001;AC-0002;40000",86,True),
 ("CONSULTA;AC-0002",11,True),("TRANSFER;AC-0001;AC-0002;120000",55,True),
 ("TRANSFER;AC-0001;AC-0002;100000",12,True),("CONSULTa;AC-0001",14,True),
 ("ANULA;OP-0003",66,True),("CONSULTA;AC-0009",87,True),
 ("TRANSFER;AC-0002;AC-0001;50000",23,True),("DEPOSITO;AC-0002;700",35,True),
]
BAD = [("ALTA;Lucia",83)]
def variants(s):
    yield "raw", s
    yield "upper", s.upper()
    yield "lower", s.lower()
    yield "nosemi", s.replace(";","")
    yield "upper_nosemi", s.upper().replace(";","")
    yield "withsemi", s+";"
    yield "args", s.split(";",1)[1]
    yield "args_nosemi", s.split(";",1)[1].replace(";","")
    yield "digits", "".join(c for c in s if c.isdigit())
    yield "rev", s[::-1]
def fns():
    yield "sum", lambda b,M: sum(b)%M
    yield "xor", lambda b,M: (lambda x: x%M)(__import__("functools").reduce(lambda a,c:a^c,b,0))
    yield "len", lambda b,M: len(b)%M
    yield "crc32", lambda b,M: zlib.crc32(bytes(b))%M
    yield "adler", lambda b,M: zlib.adler32(bytes(b))%M
    for B in range(2,260):
        yield f"poly_fwd_B{B}", (lambda B: lambda b,M: __import__("functools").reduce(lambda a,c:(a*B+c)%M,b,0))(B)
        yield f"poly_rev_B{B}", (lambda B: lambda b,M: __import__("functools").reduce(lambda a,c:(a*B+c)%M,reversed(b),0))(B)
        yield f"posw_B{B}", (lambda B: lambda b,M: sum((i+1)*c for i,c in enumerate(b))%M if B==2 else sum(c*pow(B,i,M) for i,c in enumerate(b))%M)(B)
    yield "idxw", lambda b,M: sum((i+1)*c for i,c in enumerate(b))%M
    yield "idxw0", lambda b,M: sum((i)*c for i,c in enumerate(b))%M
    yield "alt", lambda b,M: sum(c*(1 if i%2==0 else -1) for i,c in enumerate(b))%M
def search():
    hits=[]
    for vn in [v for v,_ in variants("A;B")]:
        for fname,f in fns():
            for M in list(range(90,130))+[256,255,251,127,128,1000]:
                for post in ("id","neg","plus1"):
                    ok=True
                    for s,c,_ in ROWS:
                        b=list(dict(variants(s))[vn].encode())
                        v=f(b,M)
                        v={"id":v,"neg":(-v)%M,"plus1":(v+1)%M}[post]
                        if v!=c: ok=False;break
                    if ok: hits.append((vn,fname,M,post))
    return hits
if __name__=="__main__":
    h=search(); print(len(h),"hits"); print(h[:20])
