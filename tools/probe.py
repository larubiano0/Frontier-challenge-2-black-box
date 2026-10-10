"""Research tool: ad-hoc probes against the ORIGINAL (token via env only, never printed).
Logs to experimentos.jsonl / experimentos_trace.jsonl in the same format as replay_original."""
import json, os, sys, time, datetime as dt
from pathlib import Path
import httpx
from tools.replay_original import (ORIGINAL_BASE_URL, ExperimentLog, TokenBudget, DEFAULT_LOG,
                                   DEFAULT_TRACE, DEFAULT_COUNTER, TOKEN_ENV, _parse_x_req)
TOKEN = os.environ[TOKEN_ENV]
log = ExperimentLog(DEFAULT_LOG, DEFAULT_TRACE)
budget = TokenBudget(DEFAULT_COUNTER, TOKEN_ENV, run_cap=10**6)
client = httpx.Client(base_url=ORIGINAL_BASE_URL, timeout=5.0, trust_env=False)

def send(seq, hip, method="POST", path="/msg", body=None, raw=None, auth="ok", ctype="json", note=None, quiet=False):
    budget.before_request(); time.sleep(0.15)
    h = {}
    if auth == "ok": h["Authorization"] = f"Bearer {TOKEN}"
    elif auth == "bad": h["Authorization"] = "Bearer invalid-probe-token"
    content = None
    if raw is not None: content = raw.encode(); req = {"raw": raw}
    elif body is not None: content = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode(); req = body
    else: req = {"method": method, "path": path}
    if content is not None and ctype: h["Content-Type"] = "application/json" if ctype == "json" else ctype
    if auth != "ok": req = {"method": method, "path": path, "auth": auth, **({"body": req} if content is not None else {})}
    elif method != "POST" or path != "/msg":
        if content is not None: req = {"method": method, "path": path, "body": req}
    i = log.take_id()
    r = client.request(method, path, headers=h, content=content)
    raw_t = r.content.decode("utf-8", "backslashreplace").replace(TOKEN, "[REDACTED]")
    try: parsed = json.loads(raw_t) if raw_t.strip() else raw_t
    except ValueError: parsed = raw_t
    xr = r.headers.get("x-req"); infra = r.headers.get("x-frontier-infra")
    e = {"id": i, "seq": seq, "x_req": _parse_x_req(xr), "hipotesis": hip, "request": req,
         "status": r.status_code, "response": parsed}
    if note: e["conclusion"] = note
    tr = {"id": i, "version": 2, "provenance": "original v2 via tools/probe.py", "ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
          "method": method, "path": path, "x_req_raw": xr, "x_frontier_infra": infra, "content_type": r.headers.get("content-type"),
          "response_raw": raw_t, "eligible_for_golden": (infra or "") != "rate-limit"}
    log.append(e, tr)
    if infra == "rate-limit": print("RATE LIMIT"); sys.exit(2)
    if not quiet: print(f"{i:4d} {method} {path} {json.dumps(req if 'auth' not in req else req, ensure_ascii=False)[:90]:90s} -> {r.status_code} {raw_t[:110]!r} ct={r.headers.get('content-type')}")
    return r.status_code, parsed

def msg(seq, hip, m, **k): return send(seq, hip, body={"m": m}, **k)
def reset(seq, hip): return send(seq, hip, path="/__reset")

def scan(seq, hip, prefix, keep_going=False):
    """Find a valid control for `prefix` (no trailing ;). Sends prefix;0..99 until response is not E202. Returns (control,status,body)."""
    for c in range(100):
        st, b = msg(seq, hip, f"{prefix};{c}", quiet=True)
        if not (st == 400 and isinstance(b, dict) and b.get("error") == "E202"):
            print(f"  SCAN {prefix!r} control={c} -> {st} {json.dumps(b, ensure_ascii=False)}")
            return c, st, b
    print(f"  SCAN {prefix!r}: no valid control 0..99"); return None, None, None
