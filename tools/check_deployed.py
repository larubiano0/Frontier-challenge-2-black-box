"""H-017: replay recorded sequences from experimentos.jsonl against OUR deployed replacement and compare
status + body with what the original answered (README rules: JSON compared structurally, else exact text).

Usage:
    FRONTIER_TOKEN=<team token> python -m tools.check_deployed --url https://<our-app>.up.railway.app \
        [--seq-prefix r2-] [--repeat 3] [--limit-seqs 50]

Never sends anything to the original (refuses its host). Steps that cannot be reproduced exactly are
skipped: truncated raw bodies ("...<N chars>"), and the HALT/E599 steps are kept (they are deterministic).
Exit code 1 if any difference is found. Repeating (--repeat) detects multi-process / multi-instance state
splits (random later-step failures).
"""
import argparse
import json
import os
import sys
from collections import OrderedDict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL_HOST = "caja-negra-production-c64f.up.railway.app"


def load_sequences(prefix: str | None):
    raw_by_id = {}
    for line in (ROOT / "experimentos_trace.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            t = json.loads(line)
            raw_by_id[t["id"]] = t.get("response_raw")
    seqs: "OrderedDict[str, list]" = OrderedDict()
    for line in (ROOT / "experimentos.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if prefix and not r["seq"].startswith(prefix):
            continue
        if r.get("status") is None:
            continue
        r["_raw"] = raw_by_id.get(r["id"])
        seqs.setdefault(r["seq"], []).append(r)
    return seqs


def build(req, token):
    """-> (method, path, headers, content) or None if not reproducible."""
    if "m" in req and len(req) == 1:
        return "POST", "/msg", {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, \
            json.dumps(req, ensure_ascii=False, separators=(",", ":")).encode()
    method, path = req.get("method", "POST"), req.get("path", "/msg")
    h = {}
    auth = req.get("auth", "ok")
    if auth == "ok":
        h["Authorization"] = f"Bearer {token}"
    elif auth == "bad":
        h["Authorization"] = "Bearer invalid-probe-token"
    for k, v in (req.get("headers") or {}).items():
        h[k] = v.replace("<token>", token)
    content = None
    if "raw" in req:
        if "...<" in req["raw"]:
            return None
        content = req["raw"].encode()
        h.setdefault("Content-Type", "application/json")
    elif "body" in req:
        content = json.dumps(req["body"], ensure_ascii=False, separators=(",", ":")).encode()
        h.setdefault("Content-Type", "application/json")
    elif "m" in req:
        content = json.dumps({k: v for k, v in req.items()}, ensure_ascii=False).encode()
    elif not ("method" in req and "path" in req):
        content = json.dumps(req, ensure_ascii=False, separators=(",", ":")).encode()
        h.setdefault("Content-Type", "application/json")
    return method, path, h, content


def same(st, text, exp_st, exp_raw):
    if st != exp_st:
        return False
    try:
        return json.loads(text) == json.loads(exp_raw)
    except (ValueError, TypeError):
        return text == (exp_raw or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--seq-prefix", default=None)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--limit-seqs", type=int, default=0)
    a = ap.parse_args()
    if ORIGINAL_HOST in a.url:
        sys.exit("refusing: that is the ORIGINAL service")
    token = os.environ.get("FRONTIER_TOKEN")
    if not token:
        sys.exit("set FRONTIER_TOKEN")
    seqs = load_sequences(a.seq_prefix)
    names = list(seqs)[: a.limit_seqs or None]
    cli = httpx.Client(base_url=a.url.rstrip("/"), timeout=10, trust_env=False)
    diffs = steps = skipped = 0
    for rep in range(a.repeat):
        for name in names:
            for r in seqs[name]:
                b = build(r["request"], token)
                if b is None:
                    skipped += 1
                    continue
                method, path, h, content = b
                resp = cli.request(method, path, headers=h, content=content)
                steps += 1
                if not same(resp.status_code, resp.text, r["status"], r["_raw"]):
                    diffs += 1
                    print(f"DIFF rep={rep} seq={name} id={r['id']} {method} {path} "
                          f"{json.dumps(r['request'], ensure_ascii=False)[:100]}\n   expected {r['status']} "
                          f"{(r['_raw'] or '')[:160]}\n   got      {resp.status_code} {resp.text[:160]}")
    print(f"steps={steps} skipped={skipped} diffs={diffs} sequences={len(names)} repeat={a.repeat}")
    sys.exit(1 if diffs else 0)


if __name__ == "__main__":
    main()
