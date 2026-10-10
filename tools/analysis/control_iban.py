"""Offline: test ISO7064 mod 97-10 / IBAN-style encodings against recorded rows."""
import sys; sys.path.insert(0,'tools/analysis')
from control_fit import ROWS
def enc_map(s, kind):
    out=""
    for ch in s:
        if kind=="iban":      # digits kept, letters A=10.., other dropped
            if ch.isdigit(): out+=ch
            elif ch.isalpha(): out+=str(ord(ch.upper())-55)
        elif kind=="iban_case": # case-sensitive: a=36..
            if ch.isdigit(): out+=ch
            elif ch.isupper(): out+=str(ord(ch)-55)
            elif ch.islower(): out+=str(ord(ch)-61)
        elif kind=="ord": out+=str(ord(ch))
        elif kind=="ord_nosemi":
            if ch!=";": out+=str(ord(ch))
        elif kind=="digits":
            if ch.isdigit(): out+=ch
        elif kind=="iban_semi0":
            out+= ch if ch.isdigit() else (str(ord(ch.upper())-55) if ch.isalpha() else "")
    return out
hits=[]
for kind in ["iban","iban_case","ord","ord_nosemi","digits"]:
  for pre in ["","  "]:
    for tail in ["","00","0","000","0000"]:
      for post in ["n","98-n","97-n","n+1","96-n"]:
        for up in (False,True):
          ok=True
          for s,c,_ in ROWS:
              t=s.upper() if up else s
              e=enc_map(t,kind)+tail
              if not e: ok=False;break
              n=int(e)%97
              v={"n":n,"98-n":98-n,"97-n":97-n,"n+1":n+1,"96-n":96-n}[post]
              if v!=c: ok=False;break
          if ok: hits.append((kind,tail,post,up))
print(hits)
# per-row diagnostics for 'digits' + '00'
for kind in ["iban","digits"]:
    print(kind,[ (s,c,(int(enc_map(s,kind)+"00")%97) if enc_map(s,kind) else None) for s,c,_ in ROWS])
