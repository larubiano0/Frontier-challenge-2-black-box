"""LOCALLY GENERATED rule tests (NOT confirmed by the original service).

They pin the behavior of the three approved `supuesto` rules (S-1, S-2, S-3) and
the v1-derived scaffolding around them. The authoritative evidence is the golden
suite (tests/golden/v2, recorded from the original). Each test names the evidence
it relies on; anything beyond that is a default and says so.
"""
import pytest

from app.domain import rules
from tools import golden_lib as gl

AUTH = {"Authorization": f"Bearer {gl.LOCAL_TEST_TOKEN}"}


@pytest.fixture()
def msg():
    client = gl.make_local_client()
    client.post("/__reset", headers=AUTH)

    def send(m):
        r = client.post("/msg", content=gl.encode_body({"m": m}), headers={**AUTH, "Content-Type": "application/json"})
        return r.status_code, r.json()
    return send


def open_accounts(msg):
    assert msg("ALTA;Ana;1") == (201, {"cuentaId": "AC-0001"})
    assert msg("ALTA;Beto;1") == (201, {"cuentaId": "AC-0002"})


# ---- S-1: saldo as "X.YY" string (v2 ids 6, 9, 12, 20) ----------------------------
@pytest.mark.parametrize("units,text", [(0, "0.00"), (5, "0.05"), (100, "1.00"), (40000, "400.00"),
                                         (40700, "407.00"), (210000, "2100.00"), (-150, "-1.50")])
def test_s1_format_saldo(units, text):
    assert rules.format_saldo(units) == text


def test_s1_consulta_returns_string_two_decimals(msg):
    open_accounts(msg)
    assert msg("CONSULTA;AC-0001;1") == (200, {"cuenta_id": "AC-0001", "saldo": "0.00"})
    assert msg("DEPOSITO;AC-0001;250000;1")[0] == 200
    assert msg("CONSULTA;AC-0001;1") == (200, {"cuenta_id": "AC-0001", "saldo": "2500.00"})
    assert msg("DEPOSITO;AC-0001;1;1")[0] == 200
    assert msg("CONSULTA;AC-0001;1")[1]["saldo"] == "2500.01"


# ---- S-2: TRANSFER >= 100000 -> E506 (v2 ids 10, 11); DEPOSITO unlimited (id 7) ----
def test_s2_transfer_100000_and_120000_rejected_even_with_funds(msg):
    open_accounts(msg)
    msg("DEPOSITO;AC-0001;250000;1")
    for amount in ("100000", "120000"):
        assert msg(f"TRANSFER;AC-0001;AC-0002;{amount};1") == (422, {"error": "E506", "mensaje": "límite excedido"})
    assert msg("CONSULTA;AC-0001;1")[1]["saldo"] == "2500.00"       # nothing moved
    assert msg("CONSULTA;AC-0002;1")[1]["saldo"] == "0.00"


def test_s2_rejected_transfer_does_not_consume_operation_id(msg):   # v2 id 19: next success is OP-0003
    open_accounts(msg)
    assert msg("DEPOSITO;AC-0001;250000;1")[1]["operacionId"] == "OP-0001"
    assert msg("TRANSFER;AC-0001;AC-0002;40000;1")[1]["operacionId"] == "OP-0002"
    assert msg("TRANSFER;AC-0001;AC-0002;100000;1")[0] == 422
    assert msg("DEPOSITO;AC-0002;700;1")[1]["operacionId"] == "OP-0003"


def test_s2_deposito_is_not_limited(msg):
    open_accounts(msg)
    assert msg("DEPOSITO;AC-0001;250000;1") == (200, {"status": "recieved", "operacionId": "OP-0001"})


def test_s2_limit_checked_before_balance_is_a_DEFAULT_not_evidence(msg):
    open_accounts(msg)   # AC-0001 has 0: both E506 and E507 apply; real precedence is UNKNOWN
    assert msg("TRANSFER;AC-0001;AC-0002;100000;1")[1]["error"] == "E506"


def test_transfer_under_limit_and_insufficient_balance(msg):        # v2 id 17: E507
    open_accounts(msg)
    msg("DEPOSITO;AC-0001;40000;1")
    assert msg("TRANSFER;AC-0001;AC-0002;50000;1") == (422, {"error": "E507", "mensaje": "saldo insuficiente"})
    assert msg("TRANSFER;AC-0001;AC-0002;40000;1")[0] == 200


# ---- S-3: ANULA of a non-existent operation -> E402 (v2 ids 14, 15) -----------------
def test_s3_anula_nonexistent_operation(msg):
    for _ in range(2):  # repeated, as observed
        assert msg("ANULA;OP-0003;66") == (404, {"error": "E402", "mensaje": "operación inexistente"})


def test_anula_existing_is_v1_derived_scaffolding(msg):             # v1 EX-13/14/16/19, UNVERIFIED in v2
    open_accounts(msg)
    msg("DEPOSITO;AC-0001;250000;1")
    msg("TRANSFER;AC-0001;AC-0002;40000;1")                          # OP-0002
    assert msg("ANULA;OP-0002;1") == (200, {"ok": True, "anulada": "OP-0002"})
    assert msg("ANULA;OP-0002;1") == (200, {"ok": False, "motivo": "ya anulada"})
    assert msg("CONSULTA;AC-0001;1")[1]["saldo"] == "2500.00"       # transfer reversed
    assert msg("CONSULTA;AC-0002;1")[1]["saldo"] == "0.00"


# ---- pipeline (v2 ids 2-21; order of checks is a DEFAULT) ----------------------------
def test_ping_and_case_insensitive_command(msg):
    assert msg("PING;64") == (200, {"pong": True})
    open_accounts(msg)
    assert msg("CONSULTa;AC-0001;14")[0] == 200                      # v2 id 12


def test_error_bodies_are_byte_exact(msg):
    assert msg("SALDOS;AC-0001;38") == (400, {"error": "E301", "mensaje": "comando desconocido "})   # trailing space
    assert msg("DEPOSITO;AC-0002;700;5X") == (400, {"error": "E201", "mensaje": "control mal formado"})
    assert msg("ALTA;Lucia;Gomez;11") == (400, {"error": "E302", "mensaje": "aridad inválida"})
    assert msg("CONSULTA;AC-0009;87") == (404, {"error": "E401", "mensaje": "cuenta inexistente"})


def test_failed_alta_does_not_consume_account_id(msg):
    assert msg("ALTA;Lucia;Gomez;11")[0] == 400
    assert msg("ALTA;Lucia;5X")[0] == 400
    assert msg("ALTA;Lucia;1") == (201, {"cuentaId": "AC-0001"})


def test_reset_clears_state(msg):
    open_accounts(msg)
    msg("DEPOSITO;AC-0001;5;1")
    client = gl.make_local_client()
    client.post("/__reset", headers=AUTH)
    assert msg("CONSULTA;AC-0001;1")[0] == 404 and msg("ALTA;X;1")[1] == {"cuentaId": "AC-0001"}


# ---- KNOWN GAP, documented as a test of the placeholder (not an expectation of the original) --
def test_unevidenced_paths_return_explicit_501_placeholder(msg):
    open_accounts(msg)   # accounts must exist, otherwise E401 (default order) is evaluated first
    for m in ("PING", "DEPOSITO;AC-0001;-5;1", "ALTA;;1"):
        status, body = msg(m)
        assert status == 501 and body == {"error": "not_implemented"}


def test_e202_is_not_implemented_yet_KNOWN_GAP(msg):
    """v2 id 3 expects E202 for `ALTA;Lucia;83`; the control algorithm is unknown, so any
    well-formed control is accepted. This test documents the gap; it is NOT the original's rule."""
    assert msg("ALTA;Lucia;83") == (201, {"cuentaId": "AC-0001"})
