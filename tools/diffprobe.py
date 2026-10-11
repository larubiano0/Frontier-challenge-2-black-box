"""Research tool (round 2): send each request to the ORIGINAL (logged to experimentos.jsonl) AND to the
local replacement (in-process TestClient), and report differences (README comparison rules).

Token: read only from ORIGINAL_BEARER_TOKEN; never printed; redacted from bodies. The local app runs with a
dummy token, and any header containing the real token is rewritten to the dummy token for the local call.
Never imported from app/.
"""
import datetime as dt
import json
import os
import sys
import time

import httpx

from tools.replay_original import (ORIGINAL_BASE_URL, DEFAULT_COUNTER, DEFAULT_LOG, DEFAULT_TRACE,
                                   TOKEN_ENV, ExperimentLog, TokenBudget, _parse_x_req)

TOKEN = os.environ[TOKEN_ENV]
LOCAL_TOKEN = "dummy-local-token"
os.environ["FRONTIER_TOKEN"] = LOCAL_TOKEN          # local app only (process env, not persisted)
from fastapi.testclient import TestClient            # noqa: E402
from app.main import app                             # noqa: E402
from app.domain.control import expected_control      # noqa: E402

local = TestClient(app)
log = ExperimentLog(DEFAULT_LOG, DEFAULT_TRACE)
budget = TokenBudget(DEFAULT_COUNTER, TOKEN_ENV, run_cap=10 ** 6)
client = httpx.Client(timeout=10.0, trust_env=False)
DIFFS: list[dict] = []
MIN_GAP = 0.13
_last = [0.0]


def ctl(body: str) -> str:
    """Message with the locally-modelled control appended."""
    return f"{body};{expected_control(body)}"


def _parse(text: str):
    try:
        return json.loads(text) if text.strip() else text
    except ValueError:
        return text


def _same(a_status, a_text, b_status, b_text) -> bool:
    if a_status != b_status:
        return False
    try:
        return json.loads(a_text) == json.loads(b_text)
    except ValueError:
        return a_text == b_text


def send(seq, hip, method="POST", path="/msg", body=None, raw=None, auth="ok", headers=None,
         ctype="application/json", note=None, quiet=False, compare=True):
    """auth: ok | none | bad | custom (headers given explicitly; use {TOKEN} placeholder)."""
    budget.before_request()
    gap = time.monotonic() - _last[0]
    if gap < MIN_GAP:
        time.sleep(MIN_GAP - gap)
    _last[0] = time.monotonic()
    h = {}
    if auth == "ok":
        h["Authorization"] = "Bearer {TOKEN}"
    elif auth == "bad":
        h["Authorization"] = "Bearer invalid-probe-token"
    if headers:
        h.update(headers)
    content = None
    if raw is not None:
        content = raw.encode("utf-8") if isinstance(raw, str) else raw
    elif body is not None:
        content = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if content is not None and ctype:
        h.setdefault("Content-Type", ctype)
    orig_h = {k: v.replace("{TOKEN}", TOKEN) for k, v in h.items()}
    loc_h = {k: v.replace("{TOKEN}", LOCAL_TOKEN) for k, v in h.items()}
    # request field for the log (no token)
    if method == "POST" and path == "/msg" and auth == "ok" and not headers and raw is None and body is not None:
        req = body
    else:
        req = {"method": method, "path": path}
        if auth != "ok":
            req["auth"] = auth
        if headers:
            req["headers"] = {k: v.replace("{TOKEN}", "<token>") for k, v in headers.items()}
        if raw is not None:
            req["raw"] = raw if isinstance(raw, str) else raw.decode("utf-8", "backslashreplace")
            if len(req["raw"]) > 300:
                req["raw"] = req["raw"][:120] + f"...<{len(req['raw'])} chars>"
        elif body is not None:
            req["body"] = body
    try:
        r = client.request(method, ORIGINAL_BASE_URL + path, headers=orig_h, content=content)
    except Exception as exc:  # never let a traceback echo the Authorization header
        raise SystemExit(f"request failed ({type(exc).__name__}); headers not shown") from None
    i = log.take_id()
    text = r.content.decode("utf-8", "backslashreplace").replace(TOKEN, "[REDACTED]")
    xr = r.headers.get("x-req")
    infra = r.headers.get("x-frontier-infra")
    entry = {"id": i, "seq": seq, "x_req": _parse_x_req(xr), "hipotesis": hip, "request": req,
             "status": r.status_code, "response": _parse(text)}
    lr = None
    if compare:
        lr = local.request(method, path, headers=loc_h, content=content)
        ltext = lr.content.decode("utf-8", "backslashreplace")
        same = _same(r.status_code, text, lr.status_code, ltext)
        if not same:
            entry["conclusion"] = (note + " | " if note else "") + \
                f"DIFERENCIA con el reemplazo local: local={lr.status_code} {ltext[:200]}"
            DIFFS.append({"id": i, "seq": seq, "req": req, "orig": (r.status_code, text),
                          "local": (lr.status_code, ltext)})
        elif note:
            entry["conclusion"] = note
    elif note:
        entry["conclusion"] = note
    trace = {"id": i, "version": 2, "provenance": "original v2 via tools/diffprobe.py",
             "ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
             "method": method, "path": path, "x_req_raw": xr, "x_frontier_infra": infra,
             "content_type": r.headers.get("content-type"), "response_raw": text,
             "allow": r.headers.get("allow"), "eligible_for_golden": (infra or "") != "rate-limit"}
    log.append(entry, trace)
    if infra == "rate-limit":
        print("RATE LIMIT at id", i)
        sys.exit(2)
    flag = "" if (lr is None or "DIFERENCIA" not in entry.get("conclusion", "")) else \
        f"   <<< DIFF local={lr.status_code} {lr.text[:120]!r}"
    if not quiet or flag:
        shown = json.dumps(req, ensure_ascii=False)
        print(f"{i:5d} {shown[:95]:95s} -> {r.status_code} {text[:120]!r}{flag}")
    return r.status_code, _parse(text)


def msg(seq, hip, m, **k):
    return send(seq, hip, body={"m": m}, **k)


def cmsg(seq, hip, body, **k):
    """Message with the modelled control."""
    return msg(seq, hip, ctl(body), **k)


def reset(seq, hip, quiet=True):
    return send(seq, hip, path="/__reset", quiet=quiet)


def summary():
    print(f"\n=== {len(DIFFS)} differences ===")
    for d in DIFFS:
        print(d["id"], d["seq"], json.dumps(d["req"], ensure_ascii=False)[:120])
        print("    orig :", d["orig"][0], d["orig"][1][:200])
        print("    local:", d["local"][0], d["local"][1][:200])
