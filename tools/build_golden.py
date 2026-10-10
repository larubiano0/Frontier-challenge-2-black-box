#!/usr/bin/env python3
"""Build golden fixtures from recorded evidence. OFFLINE; never calls any service.

* v2 suite  : experimentos.jsonl (+ experimentos_trace.jsonl) -> tests/golden/v2/<seq>.json
              One fixture per `seq`, explicit reset step, steps in original order,
              each step carrying its source experiment id. Only entries whose trace
              says version 2 and eligible_for_golden=true are used. Ineligible
              entries (infra rate-limit, no response) are listed under
              provenance.excluded — never deleted from the log.
* v1 suite  : pruebas/ejemplos.jsonl -> tests/golden/v1_historical/ejemplos.json
              Historical v1 evidence (organizer-provided, morning version). Kept
              apart from v2 and never mixed into the current suite.

Immutability: an existing fixture is never rewritten with different expectations.
It may only be EXTENDED (new steps appended after an identical prefix); anything
else aborts with an error.

Usage: python -m tools.build_golden [--log ...] [--trace ...] [--check]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools.golden_lib import GOLDEN_DIR, REPO_ROOT, SUITES

DEFAULT_LOG = REPO_ROOT / "experimentos.jsonl"
DEFAULT_TRACE = REPO_ROOT / "experimentos_trace.jsonl"
DEFAULT_EXAMPLES = REPO_ROOT / "pruebas" / "ejemplos.jsonl"
SCHEMA = "golden-sequence/1"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def expected_from(status: int, response, raw: str | None, is_json: bool | None) -> dict:
    if is_json is None:                      # no trace flag: fall back to the stored type
        is_json = not isinstance(response, str)
    if is_json:
        return {"status": status, "body_kind": "json", "body": response,
                "raw": raw if raw is not None else json.dumps(response, ensure_ascii=False)}
    return {"status": status, "body_kind": "text", "body": response if isinstance(response, str) else raw,
            "raw": raw}


def build_v2(log_rows: list[dict], trace_rows: list[dict]) -> tuple[dict[str, dict], dict]:
    trace = {t["id"]: t for t in trace_rows}
    by_seq: dict[str, list[dict]] = {}
    for r in log_rows:
        by_seq.setdefault(r["seq"], []).append(r)
    fixtures: dict[str, dict] = {}
    report = {"entries_total": len(log_rows), "entries_in_fixtures": 0, "skipped": []}
    for seq, rows in by_seq.items():
        rows.sort(key=lambda r: r["id"])
        steps: list[dict] = []
        excluded: list[dict] = []
        hyps: list[str] = []
        stopped = False
        for r in rows:
            t = trace.get(r["id"])
            if t is None:
                excluded.append({"id": r["id"], "reason": "no trace record: version/provenance unknown"})
                stopped = True
            elif t.get("version") != 2:
                excluded.append({"id": r["id"], "reason": f"trace version {t.get('version')!r} is not 2"})
                stopped = True
            elif not t.get("eligible_for_golden", False):
                excluded.append({"id": r["id"], "reason": t.get("ineligible_reason", "ineligible")})
                stopped = True
            if stopped:
                break   # later steps would depend on a request that is not usable
            is_reset = t["path"] == "/__reset"
            if not steps and not is_reset:
                report["skipped"].append({"seq": seq, "reason": "sequence does not start with a reset"})
                steps = []
                break
            if r["hipotesis"] not in hyps:
                hyps.append(r["hipotesis"])
            steps.append({
                "step": len(steps),
                "kind": "reset" if is_reset else "msg",
                "method": t["method"], "path": t["path"],
                "request": None if is_reset else r["request"],
                "expected": expected_from(r["status"], r["response"], t.get("response_raw"),
                                          t.get("response_is_json")),
                "source_experiment_id": r["id"],
                "x_req": r["x_req"],
            })
        if not steps:
            continue
        report["entries_in_fixtures"] += len(steps)
        fixtures[seq] = {
            "schema": SCHEMA, "version": "v2", "sequence_id": seq,
            "provenance": {
                "origin": "original service, VERSION 2 (observed via authorized experiment)",
                "source": "experimentos.jsonl", "trace": "experimentos_trace.jsonl",
                "built_by": "tools/build_golden.py",
                "hipotesis": hyps,
                "experiment_ids": [s["source_experiment_id"] for s in steps],
                "excluded": excluded,
            },
            "steps": steps,
        }
    return fixtures, report


def build_v1(examples: list[dict]) -> dict[str, dict]:
    examples = sorted(examples, key=lambda r: r["n"])
    steps = [{"step": 0, "kind": "reset", "method": "POST", "path": "/__reset", "request": None,
              "expected": None, "source_example_n": None,
              "note": "reset implied by the examples' README; its response was not recorded"}]
    for r in examples:
        steps.append({
            "step": len(steps), "kind": "msg", "method": "POST", "path": "/msg",
            "request": r["request"],
            "expected": expected_from(r["status"], r["response"], None, None),
            "source_example_n": r["n"],
        })
    return {"ejemplos": {
        "schema": SCHEMA, "version": "v1", "sequence_id": "ejemplos",
        "provenance": {
            "origin": "HISTORICAL v1 (morning version), supplied by the organizers",
            "source": "pruebas/ejemplos.jsonl",
            "note": "Not an entry of experimentos.jsonl. Not a current expectation: v2 differs "
                    "in exactly three behaviors (FR-0153). Never mix into the v2 suite.",
            "built_by": "tools/build_golden.py",
            "example_ns": [r["n"] for r in examples],
        },
        "steps": steps,
    }}


def write_fixtures(suite: str, fixtures: dict[str, dict], check_only: bool) -> list[str]:
    outdir = SUITES[suite]
    outdir.mkdir(parents=True, exist_ok=True)
    msgs: list[str] = []
    for seq, fx in fixtures.items():
        path = outdir / f"{seq}.json"
        new_text = json.dumps(fx, indent=2, ensure_ascii=False) + "\n"
        if path.exists():
            old = json.loads(path.read_text(encoding="utf-8"))
            n = len(old["steps"])
            if old["steps"] == fx["steps"][:n]:
                if old == fx:
                    msgs.append(f"{suite}/{seq}: unchanged")
                    continue
                msgs.append(f"{suite}/{seq}: extended ({n} -> {len(fx['steps'])} steps)" if len(fx["steps"]) > n
                            else f"{suite}/{seq}: metadata refreshed")
            else:
                raise SystemExit(f"REFUSING to alter recorded expectations of {suite}/{seq}: existing "
                                 f"steps differ from the log. Annotate instead of rewriting.")
        else:
            msgs.append(f"{suite}/{seq}: created ({len(fx['steps'])} steps)")
        if not check_only:
            path.write_text(new_text, encoding="utf-8")
    return msgs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", default=str(DEFAULT_LOG))
    ap.add_argument("--trace", default=str(DEFAULT_TRACE))
    ap.add_argument("--examples", default=str(DEFAULT_EXAMPLES))
    ap.add_argument("--check", action="store_true", help="report only; write nothing")
    args = ap.parse_args(argv)

    v2, rep = build_v2(read_jsonl(Path(args.log)), read_jsonl(Path(args.trace)))
    for m in write_fixtures("v2", v2, args.check):
        print(m)
    print(f"v2 coverage: {rep['entries_in_fixtures']}/{rep['entries_total']} log entries represented; "
          f"skipped sequences: {rep['skipped'] or 'none'}")
    for seq, fx in v2.items():
        if fx["provenance"]["excluded"]:
            print(f"  excluded in {seq}: {fx['provenance']['excluded']}")
    for m in write_fixtures("v1_historical", build_v1(read_jsonl(Path(args.examples))), args.check):
        print(m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
