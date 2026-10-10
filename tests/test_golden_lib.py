"""Unit tests of the comparison rules (README) and of fixture hygiene. These
test the HARNESS, not the business logic."""
import ast
import json
from pathlib import Path

import pytest

from tools import golden_lib as gl

ROOT = Path(__file__).resolve().parent.parent


def J(body, status=200):
    return {"status": status, "body_kind": "json", "body": body, "raw": json.dumps(body)}


# ---- README comparison rules -------------------------------------------------
def test_object_key_order_is_ignored():
    assert gl.compare_response(J({"a": 1, "b": [1, 2]}), 200, '{"b":[1,2],"a":1}')[0]


def test_array_order_matters():
    assert not gl.compare_response(J({"a": [1, 2]}), 200, '{"a":[2,1]}')[0]


@pytest.mark.parametrize("exp,act", [
    (1, "1.0"), (1, "true"), (1, '"1"'), (True, "1"), (0, '"0.00"'), (None, "0"), ("a", '"a "'),
])
def test_scalar_values_and_types_are_exact(exp, act):
    assert not gl.compare_response(J({"v": exp}), 200, '{"v":' + act + "}")[0]


def test_status_must_match():
    ok, why = gl.compare_response(J({"a": 1}), 201, '{"a":1}')
    assert not ok and "status" in why


def test_extra_or_missing_keys_fail():
    assert not gl.compare_response(J({"a": 1}), 200, '{"a":1,"b":2}')[0]
    assert not gl.compare_response(J({"a": 1, "b": 2}), 200, '{"a":1}')[0]


def test_non_json_is_compared_char_by_char():
    exp = {"status": 400, "body_kind": "text", "body": "comando desconocido ", "raw": "comando desconocido "}
    assert gl.compare_response(exp, 400, "comando desconocido ")[0]
    assert not gl.compare_response(exp, 400, "comando desconocido")[0]      # trailing space matters
    assert not gl.compare_response(exp, 400, "Comando desconocido ")[0]     # case matters


def test_expected_json_vs_actual_non_json_fails():
    assert not gl.compare_response(J({"a": 1}), 200, "not json")[0]


def test_trailing_space_inside_json_string_is_preserved():
    assert not gl.compare_response(J({"mensaje": "comando desconocido "}), 400,
                                   '{"mensaje":"comando desconocido"}')[0]


# ---- fixture hygiene / guarantees -------------------------------------------
def test_suites_are_separated_by_version():
    v2, v1 = gl.load_sequences("v2"), gl.load_sequences("v1_historical")
    assert v2 and v1
    assert {s["version"] for s in v2} == {"v2"} and {s["version"] for s in v1} == {"v1"}


def test_every_v2_fixture_starts_with_explicit_reset_and_cites_sources():
    from tools.build_golden import STATELESS_SEQUENCES
    for s in gl.load_sequences("v2"):
        if s["sequence_id"] in STATELESS_SEQUENCES:
            # explicitly allow-listed, state-independent probes (justified in build_golden.py)
            assert s["provenance"].get("stateless_without_reset")
        else:
            assert s["steps"][0]["kind"] == "reset" and s["steps"][0]["path"] == "/__reset"
        for st in s["steps"]:
            assert isinstance(st["source_experiment_id"], int) and st["expected"] is not None


def test_every_eligible_log_entry_is_in_a_v2_fixture():
    """VERIFY duty: fixture completeness against the experiment log."""
    log = [json.loads(l) for l in (ROOT / "experimentos.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    trace = {t["id"]: t for t in (json.loads(l) for l in (ROOT / "experimentos_trace.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    eligible = {r["id"] for r in log if trace.get(r["id"], {}).get("version") == 2
                and trace[r["id"]].get("eligible_for_golden")}
    in_fixtures = {st["source_experiment_id"] for s in gl.load_sequences("v2") for st in s["steps"]}
    assert eligible <= in_fixtures, f"missing from golden: {sorted(eligible - in_fixtures)}"


def test_fixture_expectations_match_the_log_exactly():
    """The fixtures must be a faithful copy of the recorded evidence."""
    log = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "experimentos.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    for s in gl.load_sequences("v2"):
        for st in s["steps"]:
            r = log[st["source_experiment_id"]]
            assert st["expected"]["status"] == r["status"] and st["expected"]["body"] == r["response"]


def test_log_schema_and_no_secrets():
    rows = [json.loads(l) for l in (ROOT / "experimentos.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = [r["id"] for r in rows]
    assert ids == sorted(set(ids)), "ids must be unique and increasing"
    required = {"id", "seq", "x_req", "hipotesis", "request", "status", "response"}
    for r in rows:
        assert required <= set(r) <= required | {"conclusion"}
    import os
    tok = os.environ.get("ORIGINAL_BEARER_TOKEN")
    if tok:
        for f in ("experimentos.jsonl", "experimentos_trace.jsonl", "tools/original_request_counter.json"):
            assert tok not in (ROOT / f).read_text(encoding="utf-8")


def test_production_code_cannot_reach_the_original():
    banned_imports = {"httpx", "requests", "urllib", "urllib3", "aiohttp", "socket", "http", "tools"}
    for p in (ROOT / "app").rglob("*.py"):
        src = p.read_text(encoding="utf-8")
        assert "railway.app" not in src and "ORIGINAL_BEARER_TOKEN" not in src, p
        for node in ast.walk(ast.parse(src)):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""] if isinstance(node, ast.ImportFrom) else [])
            for n in names:
                assert n.split(".")[0] not in banned_imports, f"{p}: imports {n}"


def test_regression_tooling_has_no_reference_to_the_original():
    for f in ("tools/golden_lib.py", "tools/run_golden.py", "tools/build_golden.py",
              "tests/test_golden_v2.py", "tests/conftest.py"):
        src = (ROOT / f).read_text(encoding="utf-8")
        assert "railway.app" not in src and "ORIGINAL_BEARER_TOKEN" not in src, f


def test_network_is_blocked_in_tests():
    import socket
    with pytest.raises(gl.NetworkBlocked):
        socket.create_connection(("example.com", 80), timeout=0.1)


# ---- regression classification & fixture immutability -------------------------
def _res(seq, oks):
    r = gl.SequenceResult(seq, "v2")
    for i, ok in enumerate(oks):
        r.steps.append(gl.StepResult(i, "msg", "PING", {}, True, ok, "x", None, 200, "", i, 0.0))
    return r


def test_classify_regression_known_and_new():
    baseline = {"steps": {"s": {"0": "PASS", "1": "FAIL"}}}
    cls = gl.classify([_res("s", [False, False, False])], baseline)
    assert cls == {("s", 0): "regression", ("s", 1): "known_mismatch", ("s", 2): "new_mismatch"}
    assert gl.classify([_res("s", [True, True])], baseline) == {}


def test_metrics_rates():
    m = gl.metrics([_res("a", [True, True]), _res("b", [True, False])])
    assert m["sequences_total"] == 2 and m["sequences_passing"] == 1
    assert m["requests_total"] == 4 and m["requests_passing"] == 3
    assert m["request_agreement_rate"] == 0.75 and m["sequence_agreement_rate"] == 0.5


def test_build_golden_refuses_to_alter_recorded_expectations(tmp_path, monkeypatch):
    from tools import build_golden as bg
    monkeypatch.setitem(bg.SUITES, "v2", tmp_path)
    rows = [{"id": 1, "seq": "s", "x_req": None, "hipotesis": "H-0", "request": {"method": "POST", "path": "/__reset"},
             "status": 200, "response": {"ok": True}},
            {"id": 2, "seq": "s", "x_req": 1, "hipotesis": "H-0", "request": {"m": "PING;1"},
             "status": 200, "response": {"pong": True}}]
    trace = [{"id": 1, "version": 2, "method": "POST", "path": "/__reset", "eligible_for_golden": True,
              "response_raw": '{"ok":true}', "response_is_json": True},
             {"id": 2, "version": 2, "method": "POST", "path": "/msg", "eligible_for_golden": True,
              "response_raw": '{"pong":true}', "response_is_json": True}]
    fx, rep = bg.build_v2(rows, trace)
    assert rep["entries_in_fixtures"] == 2 and fx["s"]["steps"][0]["kind"] == "reset"
    bg.write_fixtures("v2", fx, False)
    rows[1]["response"] = {"pong": False}          # tampered evidence
    fx2, _ = bg.build_v2(rows, trace)
    with pytest.raises(SystemExit):
        bg.write_fixtures("v2", fx2, False)


def test_build_golden_excludes_infra_and_untraced_entries():
    from tools import build_golden as bg
    rows = [{"id": 1, "seq": "s", "x_req": None, "hipotesis": "H", "request": {}, "status": 200, "response": {}},
            {"id": 2, "seq": "s", "x_req": 1, "hipotesis": "H", "request": {"m": "PING;1"}, "status": 429, "response": "slow"},
            {"id": 3, "seq": "s", "x_req": 2, "hipotesis": "H", "request": {"m": "PING;1"}, "status": 200, "response": {}}]
    trace = [{"id": 1, "version": 2, "method": "POST", "path": "/__reset", "eligible_for_golden": True},
             {"id": 2, "version": 2, "method": "POST", "path": "/msg", "eligible_for_golden": False,
              "ineligible_reason": "infrastructure rate-limit response"}]
    fx, rep = bg.build_v2(rows, trace)
    assert [s["source_experiment_id"] for s in fx["s"]["steps"]] == [1]
    assert fx["s"]["provenance"]["excluded"][0]["id"] == 2
