#!/usr/bin/env python3
"""OFFLINE research tool: replay an approved request sequence against the ORIGINAL.

This is experimental tooling. It is NOT part of the deployed replacement and
must never be imported from `app/`.

Safety properties
-----------------
* Token: read ONLY from the env var ORIGINAL_BEARER_TOKEN via os.environ. It is
  never printed, logged, or written. Any occurrence in a response body is
  redacted before persisting. FRONTIER_TOKEN is never used here.
* Host: fixed constant (the token can only be sent to the original host).
* Per-token counter (persisted, keyed by env-var alias, never by token value):
  per-run cap (the approved budget), daily cap (8000) and a rate limiter
  (target ~4 req/s, hard ceiling 10 req/s). The counter is incremented BEFORE
  each send, so resets and failed sends count.
* Timeout 5 s. No automatic retries (so no hidden extra requests).
* Stops after logging the offending request on: `X-Frontier-Infra: rate-limit`,
  HTTP 401/403, HTTP 429 (extra conservative), connectivity error/timeout, or a
  non-2xx reset (the sequence would not start from a clean state).
* After EVERY request one line is appended (append-only + fsync) to
  experimentos.jsonl with exactly: id, seq, x_req, hipotesis, request, status,
  response (+ `conclusion` only when justified). Supplementary provenance
  (version, raw body, headers of interest, latency, eligibility) goes to
  experimentos_trace.jsonl, keyed by the same id.
* Default is a dry run. Real traffic needs `--execute`.

Usage
-----
    python -m tools.replay_original --hypothesis "H-000: ..." --seq v2-s1 \
        --budget 25 --source pruebas/ejemplos.jsonl            # dry run
    python -m tools.replay_original ... --execute               # real run
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import httpx

ORIGINAL_BASE_URL = "https://caja-negra-production-c64f.up.railway.app"
TOKEN_ENV = "ORIGINAL_BEARER_TOKEN"  # alias used as counter key (never the value)
HARD_MAX_RPS = 10
TARGET_RPS = 4
DAILY_LIMIT = 8000
TIMEOUT_S = 5.0
VERSION = 2

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG = REPO_ROOT / "experimentos.jsonl"
DEFAULT_TRACE = REPO_ROOT / "experimentos_trace.jsonl"
DEFAULT_COUNTER = REPO_ROOT / "tools" / "original_request_counter.json"
DEFAULT_SOURCE = REPO_ROOT / "pruebas" / "ejemplos.jsonl"


# --------------------------------------------------------------------------- #
# Budget / rate limiting
# --------------------------------------------------------------------------- #
class BudgetExceeded(Exception):
    pass


class TokenBudget:
    """Persistent per-token (alias) request counter with per-run and daily caps."""

    def __init__(self, path: Path, alias: str, run_cap: int,
                 daily_limit: int = DAILY_LIMIT,
                 today: Callable[[], str] | None = None) -> None:
        self.path = Path(path)
        self.alias = alias
        self.run_cap = run_cap
        self.daily_limit = daily_limit
        self._today = today or (lambda: dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d"))
        self.run_used = 0
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text(encoding="utf-8"))
        return {}

    def _entry(self) -> dict:
        e = self._data.setdefault(self.alias, {"date_utc": self._today(), "day_count": 0,
                                               "lifetime_count": 0})
        if e["date_utc"] != self._today():
            e["date_utc"] = self._today()
            e["day_count"] = 0
        return e

    @property
    def day_count(self) -> int:
        return self._entry()["day_count"]

    @property
    def lifetime_count(self) -> int:
        return self._entry()["lifetime_count"]

    def before_request(self) -> None:
        e = self._entry()
        if self.run_used >= self.run_cap:
            raise BudgetExceeded(f"run cap {self.run_cap} reached")
        if e["day_count"] >= self.daily_limit:
            raise BudgetExceeded(f"daily limit {self.daily_limit} reached")
        self.run_used += 1
        e["day_count"] += 1
        e["lifetime_count"] += 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)


class RateLimiter:
    """Spaces requests to ~TARGET_RPS and enforces a hard sliding-window ceiling."""

    def __init__(self, target_rps: float = TARGET_RPS, hard_rps: int = HARD_MAX_RPS,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.min_interval = 1.0 / target_rps
        self.hard_rps = hard_rps
        self.clock = clock
        self.sleep = sleep
        self._stamps: collections.deque[float] = collections.deque()

    def wait(self) -> None:
        now = self.clock()
        if self._stamps:
            gap = now - self._stamps[-1]
            if gap < self.min_interval:
                self.sleep(self.min_interval - gap)
                now = self.clock()
        while self._stamps and now - self._stamps[0] >= 1.0:
            self._stamps.popleft()
        if len(self._stamps) >= self.hard_rps:
            self.sleep(max(0.0, 1.0 - (now - self._stamps[0])) + 0.01)
            now = self.clock()
            while self._stamps and now - self._stamps[0] >= 1.0:
                self._stamps.popleft()
        self._stamps.append(now)


# --------------------------------------------------------------------------- #
# Append-only experiment log
# --------------------------------------------------------------------------- #
class ExperimentLog:
    def __init__(self, log_path: Path, trace_path: Path) -> None:
        self.log_path = Path(log_path)
        self.trace_path = Path(trace_path)
        self._next_id = self._scan_next_id()

    def _scan_next_id(self) -> int:
        if not self.log_path.exists():
            return 1
        last = 0
        with self.log_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    last = max(last, int(json.loads(line)["id"]))
        return last + 1

    def seq_exists(self, seq: str) -> bool:
        if not self.log_path.exists():
            return False
        with self.log_path.open(encoding="utf-8") as fh:
            return any(line.strip() and json.loads(line).get("seq") == seq for line in fh)

    def take_id(self) -> int:
        i = self._next_id
        self._next_id += 1
        return i

    @staticmethod
    def _append(path: Path, obj: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:  # append-only
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def append(self, entry: dict, trace: dict) -> None:
        self._append(self.log_path, entry)
        self._append(self.trace_path, trace)


# --------------------------------------------------------------------------- #
# Plan and execution
# --------------------------------------------------------------------------- #
@dataclass
class PlanItem:
    method: str
    path: str
    body: dict | None  # None => no body


def load_plan(source: Path) -> list[PlanItem]:
    """1 reset + the requests of the source file, in order (n ascending)."""
    rows = [json.loads(l) for l in Path(source).read_text(encoding="utf-8").splitlines() if l.strip()]
    rows.sort(key=lambda r: r["n"])
    plan = [PlanItem("POST", "/__reset", None)]
    plan += [PlanItem("POST", "/msg", r["request"]) for r in rows]
    return plan


@dataclass
class RunSummary:
    sent: int = 0
    stop_reason: str | None = None
    entry_ids: list[int] = field(default_factory=list)


def _redact(text: str, token: str) -> tuple[str, bool]:
    if token and token in text:
        return text.replace(token, "[REDACTED]"), True
    return text, False


def _parse_x_req(raw: str | None) -> Any:
    if raw is None:
        return None
    raw = raw.strip()
    return int(raw) if raw.isdigit() else raw


def run_plan(client: httpx.Client, token: str, plan: list[PlanItem], log: ExperimentLog,
             budget: TokenBudget, limiter: RateLimiter, seq: str, hipotesis: str,
             echo: Callable[[str], None] = print) -> RunSummary:
    summary = RunSummary()
    for item in plan:
        try:
            budget.before_request()
        except BudgetExceeded as exc:
            summary.stop_reason = f"budget: {exc}"
            break
        limiter.wait()

        headers = {"Authorization": f"Bearer {token}"}
        content = None
        if item.body is not None:
            headers["Content-Type"] = "application/json"
            content = json.dumps(item.body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        is_reset = item.path == "/__reset"
        request_field = ({"method": item.method, "path": item.path} if item.body is None
                         else item.body)
        entry_id = log.take_id()
        t0 = time.monotonic()
        error_name = None
        resp = None
        try:
            resp = client.request(item.method, item.path, headers=headers, content=content)
        except httpx.HTTPError as exc:       # connectivity / timeout
            error_name = type(exc).__name__  # class name only: never str(exc)
        except Exception as exc:             # defensive: still log what we sent
            error_name = "Unexpected:" + type(exc).__name__
        latency_ms = round((time.monotonic() - t0) * 1000, 1)

        trace: dict[str, Any] = {
            "id": entry_id, "version": VERSION,
            "provenance": "original service v2 (observed) via tools/replay_original.py",
            "ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds"),
            "method": item.method, "path": item.path, "latency_ms": latency_ms,
        }
        conclusion = None
        stop = None
        if resp is None:
            entry = {"id": entry_id, "seq": seq, "x_req": None, "hipotesis": hipotesis,
                     "request": request_field, "status": None, "response": None}
            trace.update({"x_req_missing": True, "error": error_name, "eligible_for_golden": False,
                          "ineligible_reason": "no response (connectivity error)"})
            conclusion = (f"Sin respuesta ({error_name}); x_req=null. Request contado en el presupuesto. "
                          "No es comportamiento del servicio.")
            stop = f"connectivity: {error_name}"
        else:
            raw_bytes = resp.content
            try:
                raw = raw_bytes.decode("utf-8")
                not_utf8 = False
            except UnicodeDecodeError:
                raw = raw_bytes.decode("utf-8", errors="backslashreplace")
                not_utf8 = True
            raw, redacted = _redact(raw, token)
            try:
                parsed: Any = json.loads(raw) if raw.strip() else raw
                is_json = bool(raw.strip())
            except ValueError:
                parsed, is_json = raw, False
            x_req_raw = resp.headers.get("x-req")
            infra = resp.headers.get("x-frontier-infra")
            is_infra = (infra or "").strip().lower() == "rate-limit"
            entry = {"id": entry_id, "seq": seq, "x_req": _parse_x_req(x_req_raw),
                     "hipotesis": hipotesis, "request": request_field,
                     "status": resp.status_code, "response": parsed}
            trace.update({
                "x_req_raw": x_req_raw, "x_req_missing": x_req_raw is None,
                "x_frontier_infra": infra, "infra_response": is_infra,
                "content_type": resp.headers.get("content-type"),
                "response_raw": raw, "response_is_json": is_json,
                "response_not_utf8": not_utf8, "token_redacted_in_body": redacted,
                "eligible_for_golden": not is_infra,
            })
            notes = []
            if x_req_raw is None:
                notes.append("X-Req ausente en la respuesta (x_req=null)")
            if is_infra:
                trace["ineligible_reason"] = "infrastructure rate-limit response"
                notes.append("Respuesta de infraestructura (X-Frontier-Infra: rate-limit); "
                             "no es comportamiento del servicio y no se aprende de ella")
                stop = "rate-limit (X-Frontier-Infra)"
            elif resp.status_code in (401, 403):
                stop = f"auth failure HTTP {resp.status_code}"
                notes.append(f"HTTP {resp.status_code}: parada por autenticación; no se reintenta")
            elif resp.status_code == 429:
                stop = "HTTP 429"
                notes.append("HTTP 429 sin cabecera de infraestructura: parada conservadora")
            elif is_reset and not (200 <= resp.status_code < 300):
                stop = f"reset failed HTTP {resp.status_code}"
                notes.append("El reset no devolvió 2xx: la secuencia no parte de estado limpio")
            if notes:
                conclusion = "; ".join(notes) + "."

        if conclusion:
            entry["conclusion"] = conclusion
        log.append(entry, trace)          # immediately after the request
        summary.sent += 1
        summary.entry_ids.append(entry_id)
        echo(f"[{summary.sent}/{len(plan)}] id={entry_id} {item.method} {item.path} "
             f"-> status={entry['status']} x_req={entry['x_req']}")
        if stop:
            summary.stop_reason = stop
            break
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hypothesis", required=True, help='e.g. "H-000: ..."')
    ap.add_argument("--seq", required=True, help="sequence id, e.g. v2-s1")
    ap.add_argument("--budget", type=int, required=True, help="max original requests for this run (resets count)")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    ap.add_argument("--trace", default=str(DEFAULT_TRACE))
    ap.add_argument("--counter", default=str(DEFAULT_COUNTER))
    ap.add_argument("--execute", action="store_true", help="actually send requests (default: dry run)")
    args = ap.parse_args(argv)

    if not args.hypothesis.startswith("H-"):
        print("refusing: --hypothesis must start with an approved id like 'H-000'", file=sys.stderr)
        return 2
    plan = load_plan(Path(args.source))
    if len(plan) > args.budget:
        print(f"refusing: plan needs {len(plan)} requests > budget {args.budget}", file=sys.stderr)
        return 2
    log = ExperimentLog(Path(args.log), Path(args.trace))
    if log.seq_exists(args.seq):
        print(f"refusing: seq {args.seq!r} already present in the log (no duplicate runs)", file=sys.stderr)
        return 2

    print(f"plan: {len(plan)} requests (1 reset + {len(plan) - 1} /msg), budget {args.budget}, "
          f"first id {log._next_id}, seq {args.seq}")
    if not args.execute:
        print("dry run: no requests sent (use --execute)")
        return 0

    token = os.environ.get(TOKEN_ENV)
    if not token:
        print(f"refusing: env var {TOKEN_ENV} is not set", file=sys.stderr)
        return 2

    budget = TokenBudget(Path(args.counter), TOKEN_ENV, run_cap=args.budget)
    print(f"counter before: day_count={budget.day_count} lifetime={budget.lifetime_count} "
          f"(tool-observed only; true consumption of the token is unknown)")
    with httpx.Client(base_url=ORIGINAL_BASE_URL, timeout=TIMEOUT_S,
                      follow_redirects=False, trust_env=False) as client:
        summary = run_plan(client, token, plan, log, budget, RateLimiter(), args.seq, args.hypothesis)
    print(f"done: sent={summary.sent} stop_reason={summary.stop_reason} ids={summary.entry_ids[:1]}..{summary.entry_ids[-1:]}")
    print(f"counter after: day_count={budget.day_count} lifetime={budget.lifetime_count}")
    return 0 if summary.stop_reason is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
