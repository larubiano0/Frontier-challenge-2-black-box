"""Offline tests of tools/replay_original.py using httpx.MockTransport (NO network)."""
import json

import httpx
import pytest

from tools import replay_original as ro

TOKEN = "unit-test-fake-token-not-real"


def _mk(tmp_path, handler, budget_cap=25):
    log = ro.ExperimentLog(tmp_path / "exp.jsonl", tmp_path / "trace.jsonl")
    budget = ro.TokenBudget(tmp_path / "counter.json", ro.TOKEN_ENV, run_cap=budget_cap)
    limiter = ro.RateLimiter(clock=lambda: 0.0, sleep=lambda s: None)
    client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(handler))
    return log, budget, limiter, client


def _plan(n_msgs=3):
    return [ro.PlanItem("POST", "/__reset", None)] + [
        ro.PlanItem("POST", "/msg", {"m": f"PING;{i}"}) for i in range(n_msgs)]


def _lines(p):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]


def test_happy_path_logs_every_request_with_exact_keys(tmp_path):
    def handler(req):
        assert req.headers["authorization"] == f"Bearer {TOKEN}"
        if req.url.path == "/__reset":
            return httpx.Response(200, json={"ok": True}, headers={"X-Req": "1"})
        return httpx.Response(200, text="not json", headers={"X-Req": "2"})
    log, budget, limiter, client = _mk(tmp_path, handler)
    s = ro.run_plan(client, TOKEN, _plan(), log, budget, limiter, "t-s1", "H-000: t", echo=lambda *_: None)
    assert s.sent == 4 and s.stop_reason is None
    rows = _lines(tmp_path / "exp.jsonl")
    assert [r["id"] for r in rows] == [1, 2, 3, 4]
    for r in rows:
        assert set(r) == {"id", "seq", "x_req", "hipotesis", "request", "status", "response"}
    assert rows[0]["request"] == {"method": "POST", "path": "/__reset"}
    assert rows[1]["request"] == {"m": "PING;0"} and rows[1]["response"] == "not json"
    assert rows[1]["x_req"] == 2
    assert budget.run_used == 4 and budget.day_count == 4


def test_missing_x_req_is_null_and_flagged(tmp_path):
    log, budget, limiter, client = _mk(tmp_path, lambda r: httpx.Response(200, json={"ok": True}))
    ro.run_plan(client, TOKEN, _plan(0), log, budget, limiter, "t", "H-000", echo=lambda *_: None)
    row = _lines(tmp_path / "exp.jsonl")[0]
    assert row["x_req"] is None and "X-Req ausente" in row["conclusion"]
    assert _lines(tmp_path / "trace.jsonl")[0]["x_req_missing"] is True


@pytest.mark.parametrize("status", [401, 403])
def test_stops_on_auth_failure(tmp_path, status):
    log, budget, limiter, client = _mk(tmp_path, lambda r: httpx.Response(status, text="no"))
    s = ro.run_plan(client, TOKEN, _plan(), log, budget, limiter, "t", "H-000", echo=lambda *_: None)
    assert s.sent == 1 and "auth failure" in s.stop_reason


def test_stops_on_infra_rate_limit_and_marks_ineligible(tmp_path):
    log, budget, limiter, client = _mk(
        tmp_path, lambda r: httpx.Response(429, text="slow", headers={"X-Frontier-Infra": "rate-limit"}))
    s = ro.run_plan(client, TOKEN, _plan(), log, budget, limiter, "t", "H-000", echo=lambda *_: None)
    assert s.sent == 1 and "rate-limit" in s.stop_reason
    assert _lines(tmp_path / "trace.jsonl")[0]["eligible_for_golden"] is False


def test_stops_on_connectivity_error_without_leaking_token(tmp_path):
    def handler(req):
        raise httpx.ConnectTimeout(f"boom {TOKEN}")
    log, budget, limiter, client = _mk(tmp_path, handler)
    s = ro.run_plan(client, TOKEN, _plan(), log, budget, limiter, "t", "H-000", echo=lambda *_: None)
    assert s.sent == 1 and "connectivity" in s.stop_reason
    row = _lines(tmp_path / "exp.jsonl")[0]
    assert row["status"] is None and row["x_req"] is None
    for p in ("exp.jsonl", "trace.jsonl", "counter.json"):
        assert TOKEN not in (tmp_path / p).read_text(encoding="utf-8")


def test_stops_when_reset_is_not_2xx(tmp_path):
    log, budget, limiter, client = _mk(tmp_path, lambda r: httpx.Response(500, text="x"))
    s = ro.run_plan(client, TOKEN, _plan(), log, budget, limiter, "t", "H-000", echo=lambda *_: None)
    assert s.sent == 1 and "reset failed" in s.stop_reason


def test_budget_cap_is_enforced(tmp_path):
    log, budget, limiter, client = _mk(tmp_path, lambda r: httpx.Response(200, json={}), budget_cap=2)
    s = ro.run_plan(client, TOKEN, _plan(5), log, budget, limiter, "t", "H-000", echo=lambda *_: None)
    assert s.sent == 2 and s.stop_reason.startswith("budget")


def test_token_echoed_in_body_is_redacted(tmp_path):
    log, budget, limiter, client = _mk(tmp_path, lambda r: httpx.Response(200, json={"echo": TOKEN}))
    ro.run_plan(client, TOKEN, _plan(0), log, budget, limiter, "t", "H-000", echo=lambda *_: None)
    for p in ("exp.jsonl", "trace.jsonl"):
        assert TOKEN not in (tmp_path / p).read_text(encoding="utf-8")


def test_ids_continue_from_existing_log_and_are_append_only(tmp_path):
    (tmp_path / "exp.jsonl").write_text('{"id": 7, "seq": "old"}\n', encoding="utf-8")
    log, budget, limiter, client = _mk(tmp_path, lambda r: httpx.Response(200, json={}))
    ro.run_plan(client, TOKEN, _plan(1), log, budget, limiter, "new", "H-000", echo=lambda *_: None)
    rows = _lines(tmp_path / "exp.jsonl")
    assert rows[0] == {"id": 7, "seq": "old"} and [r["id"] for r in rows[1:]] == [8, 9]


def test_rate_limiter_spaces_requests_at_target():
    t = [0.0]
    slept = []
    lim = ro.RateLimiter(target_rps=4, clock=lambda: t[0], sleep=lambda s: (slept.append(s), t.__setitem__(0, t[0] + s)))
    for _ in range(5):
        lim.wait()
    assert t[0] == pytest.approx(1.0)  # 5 requests at 4 req/s => 4 gaps of 0.25 s
    assert all(s <= 0.25 + 1e-9 for s in slept)


def test_rate_limiter_hard_ceiling():
    t = [0.0]
    slept = []
    lim = ro.RateLimiter(target_rps=1000, hard_rps=10,
                         clock=lambda: t[0], sleep=lambda s: (slept.append(s), t.__setitem__(0, t[0] + s)))
    stamps = []
    for _ in range(25):
        lim.wait()
        stamps.append(t[0])
    for i in range(len(stamps)):  # never more than 10 in any 1 s window
        assert sum(1 for s in stamps if stamps[i] <= s < stamps[i] + 1.0) <= 10


def test_counter_persists_across_instances(tmp_path):
    b1 = ro.TokenBudget(tmp_path / "c.json", "ALIAS", run_cap=5)
    b1.before_request(); b1.before_request()
    b2 = ro.TokenBudget(tmp_path / "c.json", "ALIAS", run_cap=5)
    assert b2.day_count == 2 and b2.lifetime_count == 2
    data = json.loads((tmp_path / "c.json").read_text())
    assert set(data) == {"ALIAS"}


def test_dry_run_sends_nothing(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv(ro.TOKEN_ENV, raising=False)
    rc = ro.main(["--hypothesis", "H-000: x", "--seq", "dry", "--budget", "25",
                  "--log", str(tmp_path / "e.jsonl"), "--trace", str(tmp_path / "t.jsonl"),
                  "--counter", str(tmp_path / "c.json")])
    assert rc == 0 and "dry run" in capsys.readouterr().out
    assert not (tmp_path / "e.jsonl").exists() and not (tmp_path / "c.json").exists()


def test_refuses_plan_larger_than_budget(tmp_path):
    rc = ro.main(["--hypothesis", "H-000: x", "--seq", "dry", "--budget", "5",
                  "--log", str(tmp_path / "e.jsonl"), "--trace", str(tmp_path / "t.jsonl"),
                  "--counter", str(tmp_path / "c.json")])
    assert rc == 2
