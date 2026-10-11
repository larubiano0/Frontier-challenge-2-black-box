"""Golden-regression library: fixtures, README comparison rules, local replay.

OFFLINE ONLY. Replays recorded evidence against the LOCAL FastAPI app through
Starlette's in-process TestClient (no sockets). It never references or calls the
original service. Production code (`app/`) must not import anything from here.

Comparison rules (README, "Cómo se evalúa"):
  * status must be identical;
  * if both bodies are JSON: object keys in any order, arrays in the same order,
    scalars identical in value AND type (1 != 1.0 != true != "1");
  * otherwise the raw text must be identical character by character.
"""
from __future__ import annotations

import json
import re
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLDEN_DIR = REPO_ROOT / "tests" / "golden"
SUITES = {"v2": GOLDEN_DIR / "v2", "v1_historical": GOLDEN_DIR / "v1_historical"}
SUITE_VERSION = {"v2": "v2", "v1_historical": "v1"}
LOCAL_TEST_TOKEN = "local-golden-runner-token"  # dummy, for the LOCAL app only
STEP_TIME_LIMIT_S = 5.0


# --------------------------------------------------------------------------- #
# Offline guard
# --------------------------------------------------------------------------- #
class NetworkBlocked(RuntimeError):
    pass


def block_network() -> None:
    """Make any real socket connection raise (in-process ASGI needs none)."""
    def _blocked(*_a: Any, **_k: Any):
        raise NetworkBlocked("network access is blocked in golden regression runs")
    socket.socket.connect = _blocked          # type: ignore[assignment]
    socket.socket.connect_ex = _blocked       # type: ignore[assignment]
    socket.create_connection = _blocked       # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Comparison
# --------------------------------------------------------------------------- #
def json_type_name(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def strict_json_equal(a: Any, b: Any) -> bool:
    ta, tb = json_type_name(a), json_type_name(b)
    if ta != tb:
        return False
    if ta == "object":
        return a.keys() == b.keys() and all(strict_json_equal(a[k], b[k]) for k in a)
    if ta == "array":
        return len(a) == len(b) and all(strict_json_equal(x, y) for x, y in zip(a, b))
    return a == b


def json_diff_paths(a: Any, b: Any, path: str = "$") -> list[str]:
    """Descriptive, factual list of where two JSON values differ."""
    ta, tb = json_type_name(a), json_type_name(b)
    if ta != tb:
        return [f"{path}: {json.dumps(a, ensure_ascii=False)} ({ta}) → {json.dumps(b, ensure_ascii=False)} ({tb})"]
    if ta == "object":
        out: list[str] = []
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append(f"{path}.{k}: (ausente) → {json.dumps(b[k], ensure_ascii=False)}")
            elif k not in b:
                out.append(f"{path}.{k}: {json.dumps(a[k], ensure_ascii=False)} → (ausente)")
            else:
                out += json_diff_paths(a[k], b[k], f"{path}.{k}")
        return out
    if ta == "array":
        if len(a) != len(b):
            return [f"{path}: array de {len(a)} elementos → {len(b)}"]
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out += json_diff_paths(x, y, f"{path}[{i}]")
        return out
    return [] if a == b else [f"{path}: {json.dumps(a, ensure_ascii=False)} → {json.dumps(b, ensure_ascii=False)}"]


def parse_json(raw: str) -> tuple[bool, Any]:
    if not raw.strip():
        return False, raw
    try:
        return True, json.loads(raw)
    except ValueError:
        return False, raw


def compare_response(expected: dict, actual_status: int, actual_raw: str) -> tuple[bool, str]:
    """expected = {"status", "body_kind": "json"|"text", "body", "raw"}"""
    if expected["status"] != actual_status:
        return False, f"status: esperado {expected['status']} ≠ real {actual_status}"
    act_is_json, act_val = parse_json(actual_raw)
    if expected["body_kind"] == "json" and act_is_json:
        if strict_json_equal(expected["body"], act_val):
            return True, "ok"
        return False, "cuerpo JSON distinto: " + "; ".join(json_diff_paths(expected["body"], act_val)) 
    exp_raw = expected["body"] if expected["body_kind"] == "text" else expected.get("raw", "")
    if exp_raw == actual_raw:
        return True, "ok"
    return False, "texto distinto (carácter a carácter)"


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
def load_sequences(suite: str) -> list[dict]:
    d = SUITES[suite]
    seqs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(d.glob("*.json"))]
    for s in seqs:
        if s.get("version") != SUITE_VERSION[suite]:
            raise ValueError(f"fixture {s.get('sequence_id')} has version {s.get('version')!r} "
                             f"but lives in suite {suite!r} — suites must never be mixed")
    return seqs


def command_of(step: dict) -> str:
    if step["kind"] == "reset":
        return "__reset"
    if step["kind"] == "http":
        return f"{step.get('method')} {step.get('path')}"
    req = step.get("request") or {}
    m = req.get("m") if isinstance(req, dict) else None
    if not isinstance(m, str):
        return "<sin m>"
    return m.split(";", 1)[0].upper()


# --------------------------------------------------------------------------- #
# Local replay
# --------------------------------------------------------------------------- #
@dataclass
class StepResult:
    step: int
    kind: str
    command: str
    request: Any
    compared: bool
    ok: bool
    reason: str
    expected: Any
    actual_status: int | None
    actual_body: str | None
    source_id: Any
    elapsed_s: float


@dataclass
class SequenceResult:
    sequence_id: str
    version: str
    steps: list[StepResult] = field(default_factory=list)

    @property
    def compared_steps(self) -> list[StepResult]:
        return [s for s in self.steps if s.compared]

    @property
    def passed(self) -> bool:
        return all(s.ok for s in self.compared_steps)

    @property
    def first_failure(self) -> StepResult | None:
        return next((s for s in self.compared_steps if not s.ok), None)


def make_local_client():
    """In-process client for the LOCAL app. Uses a dummy token, never a real one."""
    import os
    os.environ["FRONTIER_TOKEN"] = LOCAL_TEST_TOKEN
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


def encode_body(body: dict) -> bytes:
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


BAD_LOCAL_TOKEN = "invalid-probe-token"  # mirrors tools/probe.py auth="bad"


_TRUNC = re.compile(r"\.\.\.<(\d+) chars>$")


def _raw_bytes(raw: str) -> bytes:
    """Exact raw body. Truncated log records ('...<N chars>') are the padded PING bodies of the
    body-size probes: '{"m":"PING;64","p":"' + 'a'*(N-22) + '"}' (ids 3015, 3745-3747)."""
    m = _TRUNC.search(raw)
    if m:
        return ('{"m":"PING;64","p":"' + "a" * (int(m.group(1)) - 22) + '"}').encode("utf-8")
    return raw.encode("utf-8")


def _body_bytes(body: Any) -> bytes | None:
    if body is None:
        return None
    if isinstance(body, dict) and set(body) == {"raw"} and isinstance(body["raw"], str):
        return _raw_bytes(body["raw"])              # exact raw text that was sent
    return encode_body(body)


def http_of_step(st: dict) -> tuple[str, str, str, bytes | None, dict]:
    """(method, path, auth, body, extra_headers) to replay a recorded step.

    Request-record conventions (tools/replay_original.py, tools/probe.py, tools/diffprobe.py):
      * reset with request None                   -> authorized POST /__reset, no body
      * {"method","path",["auth"],["body"|"raw"],["headers"]}: explicit HTTP request;
        auth "ok" (default) | "none" | "bad" | "custom" (exactly `headers`, "<token>" -> local token)
      * POST /msg: {"raw": text} = raw body text; anything else = the JSON body itself
    """
    method = st.get("method", "POST")
    path = st.get("path", "/__reset" if st["kind"] == "reset" else "/msg")
    req = st.get("request")
    if req is None:
        return method, path, "ok", None, {}
    if isinstance(req, dict) and "method" in req and "path" in req:
        body = _raw_bytes(req["raw"]) if isinstance(req.get("raw"), str) else _body_bytes(req.get("body"))
        hdrs = {k: v.replace("<token>", LOCAL_TEST_TOKEN) for k, v in (req.get("headers") or {}).items()}
        return req["method"], req["path"], req.get("auth", "ok"), body, hdrs
    return method, path, "ok", _body_bytes(req), {}


def run_sequence(client, seq: dict) -> SequenceResult:
    auth = {"Authorization": f"Bearer {LOCAL_TEST_TOKEN}"}
    result = SequenceResult(seq["sequence_id"], seq["version"])
    # Every sequence starts from a clean local state, even if its own first step
    # is not a recorded reset.
    client.post("/__reset", headers=auth)
    for st in seq["steps"]:
        method, path, auth_kind, content, extra = http_of_step(st)
        headers = ({} if auth_kind in ("none", "custom") else
                   {"Authorization": f"Bearer {BAD_LOCAL_TOKEN}"} if auth_kind == "bad" else dict(auth))
        if content is not None:
            headers["Content-Type"] = "application/json"
        headers.update(extra)
        t0 = time.monotonic()
        resp = client.request(method, path, content=content, headers=headers)
        elapsed = time.monotonic() - t0
        raw = resp.content.decode("utf-8", errors="backslashreplace")
        expected = st.get("expected")
        if expected is None:   # e.g. v1 reset: response was never recorded
            ok, reason, compared = True, "no comparado (respuesta no registrada)", False
        else:
            ok, reason = compare_response(expected, resp.status_code, raw)
            compared = True
            if elapsed > STEP_TIME_LIMIT_S:
                ok, reason = False, f"{reason}; excede {STEP_TIME_LIMIT_S}s ({elapsed:.2f}s)"
        result.steps.append(StepResult(
            step=st["step"], kind=st["kind"], command=command_of(st), request=st.get("request"),
            compared=compared, ok=ok, reason=reason, expected=expected,
            actual_status=resp.status_code, actual_body=raw,
            source_id=st.get("source_experiment_id", st.get("source_example_n")), elapsed_s=elapsed))
    return result


# --------------------------------------------------------------------------- #
# Metrics / baseline classification
# --------------------------------------------------------------------------- #
def load_baseline(suite: str) -> dict | None:
    p = GOLDEN_DIR / f"baseline_{suite}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def classify(results: list[SequenceResult], baseline: dict | None) -> dict[tuple[str, int], str]:
    """For each FAILING compared step: regression | known_mismatch | new_mismatch."""
    out: dict[tuple[str, int], str] = {}
    for r in results:
        for s in r.compared_steps:
            if s.ok:
                continue
            prev = None if baseline is None else baseline["steps"].get(r.sequence_id, {}).get(str(s.step))
            out[(r.sequence_id, s.step)] = ("regression" if prev == "PASS"
                                            else "known_mismatch" if prev == "FAIL"
                                            else "new_mismatch")
    return out


def newly_passing(results: list[SequenceResult], baseline: dict | None) -> list[tuple[str, int]]:
    """Steps recorded as FAIL in the baseline that PASS now (progress, not a rewrite of expectations)."""
    if baseline is None:
        return []
    return [(r.sequence_id, s.step) for r in results for s in r.compared_steps
            if s.ok and baseline["steps"].get(r.sequence_id, {}).get(str(s.step)) == "FAIL"]


def metrics(results: list[SequenceResult]) -> dict:
    steps = [s for r in results for s in r.compared_steps]
    msg = [s for s in steps if s.kind == "msg"]
    seq_total = len(results)
    seq_pass = sum(1 for r in results if r.passed)
    seq_pass_msg = sum(1 for r in results if all(s.ok for s in r.compared_steps if s.kind == "msg"))
    per_cmd: dict[str, list[int]] = {}
    for s in steps:
        per_cmd.setdefault(s.command, [0, 0])
        per_cmd[s.command][1] += 1
        per_cmd[s.command][0] += 1 if s.ok else 0
    return {
        "sequences_total": seq_total, "sequences_passing": seq_pass, "sequences_failing": seq_total - seq_pass,
        "requests_total": len(steps), "requests_passing": sum(1 for s in steps if s.ok),
        "request_agreement_rate": (sum(1 for s in steps if s.ok) / len(steps)) if steps else None,
        "sequence_agreement_rate": (seq_pass / seq_total) if seq_total else None,
        "msg_requests_total": len(msg), "msg_requests_passing": sum(1 for s in msg if s.ok),
        "msg_request_agreement_rate": (sum(1 for s in msg if s.ok) / len(msg)) if msg else None,
        "sequence_agreement_rate_msg_only": (seq_pass_msg / seq_total) if seq_total else None,
        "per_command": {k: {"passing": v[0], "total": v[1]} for k, v in sorted(per_cmd.items())},
        "max_step_latency_s": max((s.elapsed_s for s in steps), default=0.0),
    }
