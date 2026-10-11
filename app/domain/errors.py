"""Application-level errors with the exact status/code/message observed (v2).

Evidence is cited by experiment id in `experimentos.jsonl` (all version 2).
Messages are byte-exact: note the trailing space in E301 and the accents.
Catalogue: reports/handoff_implementation.md §7.
"""


class ServiceError(Exception):
    def __init__(self, status: int, code: str, message: str, extra: dict | None = None) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message
        self.extra = extra or {}

    def body(self) -> dict:
        return {"error": self.code, "mensaje": self.message, **self.extra}


# --- entrada / transporte -------------------------------------------------------
def e001() -> ServiceError:  # missing/wrong token on a known route: ids 65-69
    return ServiceError(401, "E001", "no autorizado")


def e404() -> ServiceError:  # unknown route or method (checked before auth): ids 70-77, 91, 92
    return ServiceError(404, "E404", "ruta desconocida")


def e100() -> ServiceError:  # body is not valid JSON (garbage or empty): ids 78, 85
    return ServiceError(400, "E100", "json inválido")


def e101() -> ServiceError:  # body > 8192 bytes: ids 2800-2802, 2807 (8192 ok), 2821 (8193)
    return ServiceError(413, "E101", "cuerpo demasiado grande")


def e102() -> ServiceError:  # not an object / no string `m`: ids 79, 80, 83, 84, 89, 90
    return ServiceError(400, "E102", "falta m")


def e103() -> ServiceError:  # `m` has no ';': ids 81, 82, 2794, 2795
    return ServiceError(400, "E103", "falta control")


def e104() -> ServiceError:  # some ';'-segment is empty: ids 99-103, 145-147
    return ServiceError(400, "E104", "segmento vacío")


# --- integridad -------------------------------------------------------------------
def e201() -> ServiceError:  # control not ^[0-9]{1,2}$: ids 18, 55, 57, 63, 112, 113, 2798
    return ServiceError(400, "E201", "control mal formado")


def e202() -> ServiceError:  # control value wrong: ids 3, 54, 56, 58, 62, 117, 119
    return ServiceError(400, "E202", "control inválido")


# --- comandos ---------------------------------------------------------------------
def e301(sugerencia: str | None = None) -> ServiceError:
    # ids 13, 54 (no suggestion); ids 97, 220, 303, 365, 445, 602, 696, 795, 800 (suggestion).
    # TRAILING SPACE in the message is intentional (original).
    return ServiceError(400, "E301", "comando desconocido ",
                        {"sugerencia": sugerencia} if sugerencia else None)


def e302() -> ServiceError:  # wrong field count: ids 21, 56, 100, 121, 2771
    return ServiceError(400, "E302", "aridad inválida")


def e303() -> ServiceError:  # bad amount: ids 983, 1000, 1063, 1134, 1148, 2776
    return ServiceError(400, "E303", "monto inválido")


def e304() -> ServiceError:  # TRANSFER src == dst: ids 1200, 1550, 1804
    return ServiceError(400, "E304", "origen y destino iguales")


def e401() -> ServiceError:  # unknown account: ids 16, 59, 60, 111, 114
    return ServiceError(404, "E401", "cuenta inexistente")


def e402() -> ServiceError:  # unknown operation: ids 14, 15, 2547, 2592, 2652, 2725
    return ServiceError(404, "E402", "operación inexistente")


def e506() -> ServiceError:  # TRANSFER amount > 50000: ids 10, 11, 37, 49, 50, 2786
    return ServiceError(422, "E506", "límite excedido")


def e507() -> ServiceError:  # amount > balance: ids 17, 2013-2017
    return ServiceError(422, "E507", "saldo insuficiente")


def e510(intentos: int) -> ServiceError:  # blocked source account: ids 1998-2004, 2877-2880
    return ServiceError(423, "E510", "cuenta bloqueada", {"intentos": intentos})


def e520() -> ServiceError:  # HALT with argument != "1": ids 2965, 2966, 2973-2980, 2989-2999
    return ServiceError(409, "E520", "operación destructiva: detiene el servicio; reenvía con confirmación")


def e599() -> ServiceError:  # service halted (HALT;1 itself and every later /msg): ids 2981, 3003-3015
    return ServiceError(503, "E599", "service halted")
