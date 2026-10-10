#!/usr/bin/env python3
"""Replay golden sequences against the LOCAL app and report regression metrics.

OFFLINE: uses recorded fixtures and the in-process local FastAPI app. It NEVER
calls the original service (sockets are blocked while it runs).

    python -m tools.run_golden                     # current suite (v2)
    python -m tools.run_golden --suite v1_historical   # informational only
    python -m tools.run_golden --update-baseline   # record PASS/FAIL state (refuses on regressions)

Failure classes (per failing step, relative to tests/golden/baseline_<suite>.json):
  regression      step PASSED in the baseline, FAILS now          -> must be fixed in code
  known_mismatch  step already FAILED in the baseline             -> tracked, not new
  new_mismatch    step has no baseline entry (new evidence)       -> not yet implemented
Expected outputs are never edited to make a run pass.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from tools import golden_lib as gl


def short(v, n=220) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[:n] + "…"


def render(results, mets, cls, suite, baseline) -> str:
    out: list[str] = []
    P = out.append
    P(f"== Golden regression — suite {suite} (local app, offline) ==")
    P(f"baseline: {'present' if baseline else 'ABSENT (every failure is reported as new_mismatch)'}")
    P(f"sequences: total={mets['sequences_total']} passing={mets['sequences_passing']} failing={mets['sequences_failing']}")
    P(f"requests (compared steps, incl. reset): total={mets['requests_total']} passing={mets['requests_passing']}")
    fmt = lambda x: "n/a" if x is None else f"{x:.1%}"
    P(f"Request Agreement Rate : {fmt(mets['request_agreement_rate'])} (all compared steps)"
      f" | {fmt(mets['msg_request_agreement_rate'])} ({mets['msg_requests_passing']}/{mets['msg_requests_total']} /msg only)")
    P(f"Sequence Agreement Rate: {fmt(mets['sequence_agreement_rate'])} (strict: every compared step incl. reset)"
      f" | {fmt(mets['sequence_agreement_rate_msg_only'])} (/msg steps only)")
    P(f"max step latency: {mets['max_step_latency_s'] * 1000:.1f} ms (limit 5000 ms)")
    n_reg = sum(1 for v in cls.values() if v == "regression")
    n_known = sum(1 for v in cls.values() if v == "known_mismatch")
    n_new = sum(1 for v in cls.values() if v == "new_mismatch")
    P(f"failing steps: {len(cls)} → new regressions={n_reg}, known mismatches={n_known}, new (unbaselined) mismatches={n_new}")
    fixed = gl.newly_passing(results, baseline)
    P(f"steps that failed in the baseline and pass now: {len(fixed)}")
    P("per command (passing/total): " + ", ".join(f"{k} {v['passing']}/{v['total']}" for k, v in mets["per_command"].items()))
    for r in results:
        ff = r.first_failure
        P("")
        P(f"[{'PASS' if r.passed else 'FAIL'}] {r.sequence_id} ({r.version}) — "
          f"{sum(1 for s in r.compared_steps if s.ok)}/{len(r.compared_steps)} steps")
        if ff:
            P(f"  first failing step {ff.step} ({ff.command}) [src id {ff.source_id}] class={cls[(r.sequence_id, ff.step)]}")
            P(f"    request : {short(ff.request) if ff.request is not None else 'POST /__reset'}")
            P(f"    expected: status={ff.expected['status']} body={short(ff.expected['body'])}")
            P(f"    actual  : status={ff.actual_status} body={short(ff.actual_body)}")
            P(f"    reason  : {ff.reason[:300]}")
            failing = [s.step for s in r.compared_steps if not s.ok]
            P(f"  all failing steps: {failing}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--suite", choices=sorted(gl.SUITES), default="v2")
    ap.add_argument("--update-baseline", action="store_true")
    ap.add_argument("--force", action="store_true", help="allow --update-baseline despite regressions")
    ap.add_argument("--fail-on", choices=["any", "regression"], default="any")
    ap.add_argument("--json-out", help="write the full result as JSON to this path")
    args = ap.parse_args(argv)

    gl.block_network()
    sequences = gl.load_sequences(args.suite)
    if not sequences:
        print(f"no fixtures in suite {args.suite}", file=sys.stderr)
        return 2
    client = gl.make_local_client()
    results = [gl.run_sequence(client, s) for s in sequences]
    baseline = gl.load_baseline(args.suite)
    cls = gl.classify(results, baseline)
    mets = gl.metrics(results)
    print(render(results, mets, cls, args.suite, baseline))

    if args.json_out:
        payload = {
            "suite": args.suite, "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "metrics": mets,
            "failures": [{"sequence": k[0], "step": k[1], "class": v} for k, v in sorted(cls.items())],
        }
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")

    if args.update_baseline:
        if any(v == "regression" for v in cls.values()) and not args.force:
            print("\nREFUSING --update-baseline: regressions present (fix code, not the baseline).", file=sys.stderr)
            return 1
        data = {"suite": args.suite, "note": "PASS/FAIL state per compared step at the last accepted run. "
                "Used only to classify failures; expectations live in the fixtures and are never edited.",
                "recorded_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "steps": {r.sequence_id: {str(s.step): ("PASS" if s.ok else "FAIL") for s in r.compared_steps}
                          for r in results}}
        (gl.GOLDEN_DIR / f"baseline_{args.suite}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"\nbaseline_{args.suite}.json updated")

    n_reg = sum(1 for v in cls.values() if v == "regression")
    if args.fail_on == "regression":
        return 1 if n_reg else 0
    return 1 if cls else 0


if __name__ == "__main__":
    sys.exit(main())
