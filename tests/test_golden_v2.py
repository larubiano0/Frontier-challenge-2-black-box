"""Current golden suite (VERSION 2). One test per recorded reset-started sequence.

Replays recorded v2 evidence against the LOCAL app only. Expectations are never
adjusted to make a test pass: while business logic is missing, red is expected
and honest. Failure classification vs. baseline: `python -m tools.run_golden`.
"""
import pytest

from tools import golden_lib as gl

SEQUENCES = gl.load_sequences("v2")


@pytest.fixture(scope="module")
def client():
    return gl.make_local_client()


@pytest.mark.parametrize("seq", SEQUENCES, ids=[s["sequence_id"] for s in SEQUENCES])
def test_v2_sequence(client, seq):
    res = gl.run_sequence(client, seq)
    ff = res.first_failure
    if ff is not None:
        failing = [s.step for s in res.compared_steps if not s.ok]
        pytest.fail(
            f"{res.sequence_id}: first failing step {ff.step} ({ff.command}, source id {ff.source_id}); "
            f"expected status={ff.expected['status']} body={ff.expected['body']!r}; "
            f"actual status={ff.actual_status} body={ff.actual_body!r}; "
            f"reason={ff.reason}; all failing steps={failing}", pytrace=False)
