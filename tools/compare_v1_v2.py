#!/usr/bin/env python3
"""Step-by-step v1 (historical) vs v2 (observed) comparison. OFFLINE; descriptive only.

Reads the two golden fixtures (tests/golden/v1_historical/ejemplos.json and
tests/golden/v2/<seq>.json) and prints a Markdown table: n, request, v1
response, v2 response, equal?, and a factual list of differing JSON paths.
It does NOT decide which differences are independent changes; differing rows
are only *candidates* (a difference may be a consequence of an earlier one).

    python -m tools.compare_v1_v2 [--v2-seq v2-s1] [--out reports/v1_vs_v2.md]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tools import golden_lib as gl


def fmt(exp: dict) -> str:
    body = json.dumps(exp["body"], ensure_ascii=False, separators=(",", ":")) if exp["body_kind"] == "json" else repr(exp["body"])
    return f"{exp['status']} `{body}`".replace("|", "\\|")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--v2-seq", default="v2-s1")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    v1 = next(s for s in gl.load_sequences("v1_historical") if s["sequence_id"] == "ejemplos")
    v2 = next(s for s in gl.load_sequences("v2") if s["sequence_id"] == args.v2_seq)
    a = [s for s in v1["steps"] if s["kind"] == "msg"]
    b = [s for s in v2["steps"] if s["kind"] == "msg"]
    assert len(a) == len(b), "sequences have different lengths"
    lines = ["| n | request | respuesta v1 (histórica) | respuesta v2 (observada) | ¿igual? | diferencias (descriptivo) |",
             "|---|---|---|---|---|---|"]
    diffs = 0
    for s1, s2 in zip(a, b):
        assert s1["request"] == s2["request"], f"request mismatch at n={s1['source_example_n']}"
        same, why = gl.compare_response(s1["expected"], s2["expected"]["status"], s2["expected"]["raw"])
        if not same:
            diffs += 1
            parts = []
            if s1["expected"]["status"] != s2["expected"]["status"]:
                parts.append(f"status {s1['expected']['status']} → {s2['expected']['status']}")
            if s1["expected"]["body_kind"] == s2["expected"]["body_kind"] == "json":
                parts += gl.json_diff_paths(s1["expected"]["body"], s2["expected"]["body"])
            why = "; ".join(parts) or why
        req = json.dumps(s1["request"], ensure_ascii=False, separators=(",", ":")).replace("|", "\\|")
        lines.append(f"| {s1['source_example_n']} | `{req}` | {fmt(s1['expected'])} | {fmt(s2['expected'])} | "
                     f"{'sí' if same else '**NO** (candidata)'} | {'' if same else why.replace('|', '\\|')} |")
    lines.append("")
    lines.append(f"Pasos: {len(a)}; iguales: {len(a) - diffs}; distintos (candidatas): {diffs}. "
                 f"Fuentes v2: ids {v2['provenance']['experiment_ids'][1]}–{v2['provenance']['experiment_ids'][-1]} de experimentos.jsonl; "
                 f"v1: pruebas/ejemplos.jsonl (no está en el log).")
    text = "\n".join(lines)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
