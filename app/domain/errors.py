"""Application-level errors with the exact status/code/message observed.

Evidence is cited by experiment id (`experimentos.jsonl`, v2) or by example
number (`EX-n`, `pruebas/ejemplos.jsonl`, historical v1). Messages are
byte-exact: note the trailing space in E301.
"""


class ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message

    def body(self) -> dict:
        return {"error": self.code, "mensaje": self.message}


def e201() -> ServiceError:  # v2 id 18 (DEPOSITO ...;5X); v1 EX-17
    return ServiceError(400, "E201", "control mal formado")


def e301() -> ServiceError:  # v2 id 13 (SALDOS); v1 EX-12 — TRAILING SPACE is intentional
    return ServiceError(400, "E301", "comando desconocido ")


def e302() -> ServiceError:  # v2 id 21 (ALTA with 4 fields); v1 EX-20
    return ServiceError(400, "E302", "aridad inválida")


def e401() -> ServiceError:  # v2 id 16 (CONSULTA AC-0009); v1 EX-15
    return ServiceError(404, "E401", "cuenta inexistente")


def e402() -> ServiceError:  # v2 ids 14, 15 (ANULA OP-0003 when it does not exist). Rule S-3.
    return ServiceError(404, "E402", "operación inexistente")


def e506() -> ServiceError:  # v2 ids 10, 11 (TRANSFER 120000 / 100000); v1 EX-9
    return ServiceError(422, "E506", "límite excedido")


def e507() -> ServiceError:  # v2 id 17 (TRANSFER 50000 from a 40000 balance); v1 EX-16
    return ServiceError(422, "E507", "saldo insuficiente")


class Unevidenced(Exception):
    """Input/path for which NO evidence and NO reasonable default exists.

    The dispatcher answers with the skeleton's explicit placeholder
    (501 {"error":"not_implemented"}), which is NOT the original's behavior.
    Each raise site names the open question so a future experiment can close it.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
