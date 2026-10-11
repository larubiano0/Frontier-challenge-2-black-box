"""Local-only robustness probe of the replacement (TestClient, dummy token). No network."""
import os, json, time
os.environ["FRONTIER_TOKEN"]="dummy-local"
from fastapi.testclient import TestClient
from app.main import app
from app.domain.control import expected_control
c=TestClient(app, raise_server_exceptions=False)
H={"Authorization":"Bearer dummy-local"}
def msg(m): 
    body=m.rsplit(";",1)[0]; return f"{m}"
def withctl(body): return f"{body};{expected_control(body)}"
cases=[]
def add(name,method,path,content=None,headers=H,**kw): cases.append((name,method,path,content,headers))
add("invalid utf8","POST","/msg",b'{"m":"ALTA;\xff;1"}')
add("lone surrogate","POST","/msg",b'{"m":"ALTA;\\ud800;1"}')
add("bom","POST","/msg",b'\xef\xbb\xbf{"m":"PING;64"}')
add("utf16","POST","/msg",'{"m":"PING;64"}'.encode('utf-16'))
add("deep nest","POST","/msg",b'['*5000+b']'*5000)
add("huge int","POST","/msg",b'{"m":"PING;64","x":'+b'9'*5000+b'}')
add("accent name","POST","/msg",json.dumps({"m":withctl("ALTA;José")},ensure_ascii=False).encode())
add("accent name esc","POST","/msg",json.dumps({"m":withctl("ALTA;José")}).encode())
add("emoji name","POST","/msg",json.dumps({"m":withctl("ALTA;😀")},ensure_ascii=False).encode())
add("HEAD /health","HEAD","/health")
add("OPTIONS /msg","OPTIONS","/msg")
add("PATCH /msg","PATCH","/msg",b'{}')
add("DELETE /__reset","DELETE","/__reset")
add("query /msg?x=1","POST","/msg?x=1",b'{"m":"PING;64"}')
add("query /health?x=1","GET","/health?x=1")
add("pct /m%73g","POST","/m%73g",b'{"m":"PING;64"}')
add("// path","POST","//msg",b'{"m":"PING;64"}')
add("lowercase bearer","POST","/msg",b'{"m":"PING;64"}',{"Authorization":"bearer dummy-local"})
add("no scheme","POST","/msg",b'{"m":"PING;64"}',{"Authorization":"dummy-local"})
add("double space","POST","/msg",b'{"m":"PING;64"}',{"Authorization":"Bearer  dummy-local"})
add("trailing space tok","POST","/msg",b'{"m":"PING;64"}',{"Authorization":"Bearer dummy-local "})
add("Basic","POST","/msg",b'{"m":"PING;64"}',{"Authorization":"Basic dummy-local"})
add("ctrl chars name","POST","/msg",json.dumps({"m":withctl("ALTA;a\u0000b")}).encode())
add("json str body","POST","/msg",b'"PING;64"')
add("number body","POST","/msg",b'5')
add("m with newline","POST","/msg",json.dumps({"m":"PING;64\n"}).encode())
add("dup key","POST","/msg",b'{"m":"x","m":"PING;64"}')
add("NaN","POST","/msg",b'{"m":"PING;64","x":NaN}')
add("trailing garbage","POST","/msg",b'{"m":"PING;64"} x')
add("whitespace body","POST","/msg",b'  {"m":"PING;64"}  \n')
add("GET /msg + body","GET","/msg",b'{"m":"PING;64"}')
for n,me,p,body,h in cases:
    t=time.time()
    r=c.request(me,p,content=body,headers=h)
    print(f"{n:22s} {r.status_code} {r.text[:90]!r} {(time.time()-t)*1000:.0f}ms")
