"""Round-2 probe plan (OFFLINE). Builds literal request bodies with controls from the local E202 model and
shows what the CURRENT replacement answers. No network. Run: PYTHONPATH=. python tools/analysis/r2_plan.py"""
import os, json, unicodedata, difflib, itertools
os.environ["FRONTIER_TOKEN"]="dummy-local"
from fastapi.testclient import TestClient
from app.main import app
from app.domain.control import expected_control
from app.domain.rules import levenshtein
cli=TestClient(app); H={"Authorization":"Bearer dummy-local"}
def ctl(body): return f"{body};{expected_control(body)}"
def run(seq):
    cli.post("/__reset",headers=H); out=[]
    for m in seq:
        r=cli.post("/msg",content=json.dumps({"m":m},ensure_ascii=False).encode(),headers=H); out.append((m,r.status_code,r.text))
    return out
def show(title,seq):
    print("##",title)
    for i,(m,s,t) in enumerate(run(seq),2): print(f"  S{i} {m!r:52} -> {s} {t}")
# H-011 control coverage
print("## H-011 stateless (ANULA;<x> -> E402 404 if control accepted)")
for name in ["HJKQVW","José","Ñandú","Straße","😀"]:
    b=f"ANULA;{name}"; print(f"  {b!r:22} ctl(ascii-ignore)={expected_control(b)}", end="")
    nf=unicodedata.normalize("NFD",name); nf=''.join(c for c in nf if not unicodedata.combining(c)); b2=f"ANULA;{nf}"
    print(f"  ctl(NFD-strip)={expected_control(b2)}  ctl(ß->SS)={expected_control('ANULA;'+name.replace('ß','SS'))}")
# H-012 E301
print("## H-012 E301 probes")
K=["PING","ALTA","CONSULTA","DEPOSITO","TRANSFER","ANULA"]
def lev_m(c): 
    b=min(K,key=lambda n:levenshtein(c,n)); return b if levenshtein(c,b)<=2 else None
def ratio_m(c,t=0.75):
    b=max(K,key=lambda n:difflib.SequenceMatcher(None,c,n).ratio()); return b if difflib.SequenceMatcher(None,c,b).ratio()>=t else None
def rel_m(c):
    b=min(K,key=lambda n:levenshtein(c,n)); return b if levenshtein(c,b)/max(len(c),len(b))<=0.34 else None
for c in ["AL","PI","TRANS","TRANSFERENCIA","ANU","DEPOSITAR","HOLA","CONSULTAR"]:
    print(f"  {('%s;ctl'%c)!r:24} m='{c};{expected_control(c)}'  lev<=2:{lev_m(c)}  ratio>=.75:{ratio_m(c)}  rel<=.34:{rel_m(c)}")
# ties
ties=set()
import string
for n in K:
    for i in range(len(n)+1):
        for ch in string.ascii_uppercase:
            for s in (n[:i]+ch+n[i:], n[:i]+ch+n[i+1:] if i<len(n) else None):
                if s and s not in K:
                    ds=sorted((levenshtein(s,k),k) for k in K)
                    if ds[0][0]<=2 and ds[1][0]==ds[0][0]: ties.add((s,ds[0],ds[1]))
print("  tie examples (<=1-edit neighbours):",sorted(ties)[:6])
# H-013 ANULA x E510
seqA=[ctl("ALTA;Lucia"),ctl("ALTA;Mateo"),ctl("DEPOSITO;AC-0001;250000"),ctl("TRANSFER;AC-0001;AC-0002;40000"),
 ctl("TRANSFER;AC-0001;AC-0002;100000")]*0
A=[ctl("ALTA;Lucia"),ctl("ALTA;Mateo"),ctl("DEPOSITO;AC-0001;250000"),ctl("TRANSFER;AC-0001;AC-0002;40000")]+[ctl("TRANSFER;AC-0001;AC-0002;100000")]*3+[ctl("ANULA;OP-0002"),ctl("TRANSFER;AC-0001;AC-0002;40000")]
show("H-013 seqA (ANULA of a TRANSFER credits blocked src)",A)
B=[ctl("ALTA;Lucia"),ctl("ALTA;Mateo"),ctl("DEPOSITO;AC-0001;250000")]+[ctl("TRANSFER;AC-0001;AC-0002;100000")]*3+[ctl("ANULA;OP-0001"),ctl("TRANSFER;AC-0001;AC-0002;40000")]
show("H-013 seqB (ANULA of the DEPOSITO debits blocked src)",B)
# H-014 saldo
C=[ctl("ALTA;Lucia"),ctl("ALTA;Mateo"),ctl("DEPOSITO;AC-0001;50"),ctl("TRANSFER;AC-0001;AC-0002;50"),ctl("ANULA;OP-0001"),ctl("CONSULTA;AC-0001"),ctl("CONSULTA;AC-0002")]
show("H-014 saldo small/negative",C)
