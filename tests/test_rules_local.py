"""LOCALLY GENERATED rule tests (NOT themselves observations of the original).

They pin the v2 rules from reports/handoff_implementation.md. The authoritative
evidence is the golden suite (tests/golden/v2, recorded from the original); each
test names the log ids it relies on, and `supuesto` marks unprobed defaults.

History: this file previously encoded assumptions that the H-001…H-008/E510
experiments disproved (501 placeholders, limit >= 100000, `{"status":"ok"}`,
no E202). Those tests were rewritten, not silenced.
"""
import json

import pytest

from app.domain import rules
from app.domain.control import control_matches, expected_control
from tools import golden_lib as gl

AUTH = {"Authorization": f"Bearer {gl.LOCAL_TEST_TOKEN}"}
ROOT_ROWS = "reports/control_rows.json"


def signed(body: str) -> str:
    """Append the valid control to a message body (uses the implemented E202 model)."""
    return f"{body};{expected_control(body)}"


@pytest.fixture()
def client():
    c = gl.make_local_client()
    c.post("/__reset", headers=AUTH)
    return c


@pytest.fixture()
def raw(client):
    def send(m):
        r = client.post("/msg", content=gl.encode_body({"m": m}), headers={**AUTH, "Content-Type": "application/json"})
        return r.status_code, r.json()
    return send


@pytest.fixture()
def msg(raw):
    return lambda body: raw(signed(body))


def err(code, mensaje, **extra):
    return {"error": code, "mensaje": mensaje, **extra}


def open_accounts(msg, n=2):
    for i in range(1, n + 1):
        assert msg(f"ALTA;U{i}") == (201, {"cuentaId": f"AC-{i:04d}"})


# ---- E202 control model ------------------------------------------------------------
def test_control_model_reproduces_every_recorded_valid_pair():
    rows = json.load(open(ROOT_ROWS, encoding="utf-8"))["rows"]
    bad = [r for r in rows if not r["message_without_control"].strip().upper().startswith("PING")
           and expected_control(r["message_without_control"]) != r["control"]]
    assert not bad


@pytest.mark.parametrize("body,ctl", [("ALTA;Lucia", 82), ("ALTA;Mateo", 3), ("CONSULTA;AC-0001", 14),
                                      ("CONSULTA;AC-0009", 87), ("PONG", 98), ("DEPOSITOX", 98)])
def test_control_known_values(body, ctl):     # ids 4, 5, 6, 16; 98 values from the h007 scans
    assert expected_control(body) == ctl


def test_control_ignores_case_and_punctuation():   # ids 94-159
    for v in ("ALTA;Lu cia", "alta;LUCIA", "ALTA;Lucia "):
        assert expected_control(v) == 82
    assert control_matches("CONSULTA;AC-0001", "14") and not control_matches("ALTA;Mateo", "03")  # ids 62, 122


# ---- entrada -------------------------------------------------------------------------
def test_routes_auth_and_health(client):
    assert (client.get("/health", headers=AUTH).status_code, client.get("/health", headers=AUTH).json()) == (200, {"ok": True})
    for method, path in [("GET", "/msg"), ("PUT", "/msg"), ("GET", "/__reset"), ("POST", "/health"),
                         ("GET", "/"), ("POST", "/msg/"), ("POST", "/MSG"), ("DELETE", "/x")]:
        r = client.request(method, path)                       # no auth: route check first (id 77)
        assert (r.status_code, r.json()) == (404, err("E404", "ruta desconocida"))
    for method, path in [("GET", "/health"), ("POST", "/msg"), ("POST", "/__reset")]:
        for h in ({}, {"Authorization": "Bearer wrong"}):
            r = client.request(method, path, headers=h, content=b'{"m":"PING;64"}')
            assert (r.status_code, r.json()) == (401, err("E001", "no autorizado"))


@pytest.mark.parametrize("body,expected", [
    (b"not json", (400, err("E100", "json inválido"))),
    (b"", (400, err("E100", "json inválido"))),
    (b"[1,2]", (400, err("E102", "falta m"))),
    (b"{}", (400, err("E102", "falta m"))),
    (b'{"m":5}', (400, err("E102", "falta m"))),
    (b'{"m":null}', (400, err("E102", "falta m"))),
    (b'{"M":"PING;64"}', (400, err("E102", "falta m"))),
    (b'{"m":""}', (400, err("E103", "falta control"))),
    (b'{"m":"PING"}', (400, err("E103", "falta control"))),
    (b'{"m":"PING;"}', (400, err("E104", "segmento vacío"))),
    (b'{"m":";64"}', (400, err("E104", "segmento vacío"))),
    (b'{"m":"PING;;64"}', (400, err("E104", "segmento vacío"))),
    (b'{"m":"PING;64","x":1}', (200, {"pong": True})),
])
def test_body_parsing(client, body, expected):
    r = client.post("/msg", content=body, headers=AUTH)
    assert (r.status_code, r.json()) == expected


def test_body_size_limit(client):                              # ids 2807 (8192 ok), 2821 (8193)
    def body(n):
        b = b'{"m":"PING;64","p":"' + b"a" * (n - 22) + b'"}'
        assert len(b) == n
        return b
    assert client.post("/msg", content=body(8192), headers=AUTH).status_code == 200
    r = client.post("/msg", content=body(8193), headers=AUTH)
    assert (r.status_code, r.json()) == (413, err("E101", "cuerpo demasiado grande"))


# ---- integridad / precedence -----------------------------------------------------------
def test_ping_exempt_from_control_but_not_arity(raw):          # ids 52, 53, 95, 100
    for m in ("PING;65", "PING;5X", "ping;-1", "PING;64 ", "PING;１２"):
        assert raw(m) == (200, {"pong": True})
    assert raw("PING;x;64") == (400, err("E302", "aridad inválida"))


def test_control_format_then_value_then_command_then_arity(raw):
    assert raw("ALTA;Mateo;100") == (400, err("E201", "control mal formado"))     # id 63
    assert raw("ALTA;Mateo;3 ") == (400, err("E201", "control mal formado"))
    assert raw("ALTA;Mateo;03") == (400, err("E202", "control inválido"))         # id 62
    assert raw("SALDOS;AC-0001;39") == (400, err("E202", "control inválido"))     # id 54: E202 before E301
    assert raw("ALTA;Lucia;Gomez;12") == (400, err("E202", "control inválido"))   # id 56: E202 before E302
    assert raw("SALDOS;AC-0001;38") == (400, err("E301", "comando desconocido "))  # trailing space
    assert raw("ALTA;Lucia;Gomez;11") == (400, err("E302", "aridad inválida"))


@pytest.mark.parametrize("cmd,sug", [(" PING", "PING"), ("PNG", "PING"), ("PONG", "PING"), ("CONSULTAS", "CONSULTA"),
                                     ("TRANSFERIR", "TRANSFER"), ("ALTAXY", "ALTA"), ("ANUL", "ANULA"),
                                     ("DEPOSITOX", "DEPOSITO"), ("TRANSF", "TRANSFER"), ("CON SULTA", "CONSULTA"),
                                     ("SALDOS", None), ("XYZ", None), ("ALTAXYZ", None), ("PINGPONG", None)])
def test_e301_suggestion(msg, cmd, sug):
    expected = err("E301", "comando desconocido ", **({"sugerencia": sug} if sug else {}))
    assert msg(cmd) == (400, expected)


# ---- comandos ------------------------------------------------------------------------------
def test_saldo_format():
    for cents, text in [(0, "0.00"), (5, "0.05"), (40000, "400.00"), (-40000, "-400.00"), (11000249998, "110002499.98")]:
        assert rules.format_saldo(cents) == text


def test_amount_rules_e303_and_cents(msg):
    open_accounts(msg, 1)
    for bad in ("0", "-5", "1.5", "007", "abc", "12345678901", "+5"):
        assert msg(f"DEPOSITO;AC-0001;{bad}") == (400, err("E303", "monto inválido"))
    assert msg("DEPOSITO;AC-0009;0") == (400, err("E303", "monto inválido"))      # E303 before E401
    assert msg("DEPOSITO;AC-0009;5") == (404, err("E401", "cuenta inexistente"))
    assert msg("DEPOSITO;AC-0001;9999999999")[0] == 200
    assert msg("DEPOSITO;AC-0001;1") == (200, {"status": "recieved", "operacionId": "OP-0002"})
    assert msg("CONSULTA;AC-0001") == (200, {"cuenta_id": "AC-0001", "saldo": "100000000.00"})


def test_transfer_precedence(msg):
    open_accounts(msg)
    assert msg("TRANSFER;AC-0008;AC-0009;abc")[1]["error"] == "E303"
    assert msg("TRANSFER;AC-0009;AC-0009;100")[1]["error"] == "E304"
    assert msg("TRANSFER;AC-0001;AC-0009;100")[1]["error"] == "E401"
    assert msg("TRANSFER;AC-0001;AC-0002;100000") == (422, err("E506", "límite excedido"))   # limit before balance
    assert msg("TRANSFER;AC-0001;AC-0002;100") == (422, err("E507", "saldo insuficiente"))


def test_transfer_limit_is_50000_per_operation(msg):            # ids 2786, 2792, 42-45
    open_accounts(msg)
    msg("DEPOSITO;AC-0001;250000")
    assert msg("TRANSFER;AC-0001;AC-0002;50001")[1]["error"] == "E506"
    for _ in range(3):
        assert msg("TRANSFER;AC-0001;AC-0002;50000")[0] == 200
    assert msg("CONSULTA;AC-0002")[1]["saldo"] == "1500.00"


def test_anula_flow_and_unconditional_reversal(msg):           # ids 29, 31, 2410-2411
    open_accounts(msg)
    msg("DEPOSITO;AC-0001;250000")                                # OP-0001
    msg("TRANSFER;AC-0001;AC-0002;40000")                         # OP-0002
    assert msg("ANULA;OP-0001") == (200, {"ok": True, "anulada": "OP-0001"})
    assert msg("CONSULTA;AC-0001")[1]["saldo"] == "-400.00"
    assert msg("ANULA;OP-0001") == (200, {"ok": False, "motivo": "ya anulada"})
    assert msg("ANULA;OP-0002") == (200, {"ok": True, "anulada": "OP-0002"})
    assert msg("CONSULTA;AC-0001")[1]["saldo"] == "0.00"
    assert msg("CONSULTA;AC-0002")[1]["saldo"] == "0.00"
    for bad in ("OP-9999", "op-0001", "AC-0001", "XYZ"):
        assert msg(f"ANULA;{bad}") == (404, err("E402", "operación inexistente"))


def test_ids_only_consumed_on_success(msg, raw):
    assert raw("ALTA;Lucia;83")[1]["error"] == "E202"            # ids 3, 4
    assert msg("ALTA;Lucia") == (201, {"cuentaId": "AC-0001"})
    assert msg("ALTA;Lucia") == (201, {"cuentaId": "AC-0002"})   # duplicates allowed (ids 943-945)
    msg("DEPOSITO;AC-0001;100")
    assert msg("TRANSFER;AC-0001;AC-0002;500")[1]["error"] == "E507"
    assert msg("DEPOSITO;AC-0001;100")[1]["operacionId"] == "OP-0002"


# ---- E510 blocking -----------------------------------------------------------------------
def blocked(n):
    return (423, err("E510", "cuenta bloqueada", intentos=n))


def test_three_failures_block_source_and_count_intentos(msg):   # ids 1998-2004, 2877-2880
    open_accounts(msg)
    msg("DEPOSITO;AC-0001;1000")
    assert msg("TRANSFER;AC-0001;AC-0002;60000")[1]["error"] == "E506"
    assert msg("TRANSFER;AC-0001;AC-0002;5000")[1]["error"] == "E507"
    assert msg("TRANSFER;AC-0001;AC-0002;5000")[1]["error"] == "E507"
    assert msg("TRANSFER;AC-0001;AC-0002;10") == blocked(1)      # would succeed, still blocked
    assert msg("TRANSFER;AC-0001;AC-0002;10") == blocked(2)
    # still precedes: E303, E304, E401
    assert msg("TRANSFER;AC-0001;AC-0002;0")[1]["error"] == "E303"
    assert msg("TRANSFER;AC-0001;AC-0001;10")[1]["error"] == "E304"
    assert msg("TRANSFER;AC-0001;AC-0009;10")[1]["error"] == "E401"
    # blocked account can still receive, consult, cancel
    msg("DEPOSITO;AC-0002;1000")
    assert msg("TRANSFER;AC-0002;AC-0001;10")[0] == 200
    assert msg("CONSULTA;AC-0001")[0] == 200
    assert msg("TRANSFER;AC-0001;AC-0002;10") == blocked(3)
    # deposit into it unblocks, intentos restarts
    assert msg("DEPOSITO;AC-0001;1")[0] == 200
    assert msg("TRANSFER;AC-0001;AC-0002;10")[0] == 200


def test_success_resets_streak_and_other_errors_do_not_count(msg):   # ids 2025-2031, 2057-2066
    open_accounts(msg)
    msg("DEPOSITO;AC-0001;1000")
    for _ in range(2):
        msg("TRANSFER;AC-0001;AC-0002;60000")
    assert msg("TRANSFER;AC-0001;AC-0002;10")[0] == 200
    for _ in range(2):
        msg("TRANSFER;AC-0001;AC-0002;60000")
    for m in ("TRANSFER;AC-0001;AC-0002;0", "TRANSFER;AC-0001;AC-0001;5", "TRANSFER;AC-0001;AC-0009;5",
              "CONSULTA;AC-0001", "DEPOSITO;AC-0002;5", "ANULA;OP-0099", "PONG"):
        msg(m)
    assert msg("TRANSFER;AC-0001;AC-0002;60000")[1]["error"] == "E506"   # 3rd failure
    assert msg("TRANSFER;AC-0001;AC-0002;10") == blocked(1)


def test_reset_clears_everything(client, msg):
    open_accounts(msg)
    for _ in range(3):
        msg("TRANSFER;AC-0001;AC-0002;5")
    assert msg("TRANSFER;AC-0001;AC-0002;5") == blocked(1)
    assert client.post("/__reset", headers=AUTH).json() == {"ok": True}
    assert msg("CONSULTA;AC-0001")[0] == 404
    assert msg("ALTA;X") == (201, {"cuentaId": "AC-0001"})
