"""Command dispatch and validation precedence.

Precedence implemented (ONLY partially evidenced -> `supuesto`):
  1. body/`m` shape                       [?]  -> Unevidenced (501 placeholder)
  2. control format (digits only)         [v2] id 18 (E201); order vs. 3-5 is [default]
  3. control VALUE (E202)                 NOT IMPLEMENTED: the algorithm is unknown
                                          (v2 id 3 `ALTA;Lucia;83` -> E202 cannot be reproduced)
  4. command known (case-insensitive)     [v2] id 13 (E301), id 12 (`CONSULTa` accepted)
  5. arity                                [v2] id 21 (E302)
  6. handler (accounts, limit, balance...)
"""
from fastapi.responses import JSONResponse, Response

from app.domain.errors import ServiceError, Unevidenced, e201, e301, e302
from app.protocol.parser import parse_message
from app.services.commands import COMMANDS
from app.storage.base import Store

NOT_IMPLEMENTED = {"error": "not_implemented"}  # skeleton placeholder, NOT the original's behavior


def _control_is_well_formed(control: str) -> bool:
    return control.isascii() and control.isdigit()  # [v2] id 18: "5X" malformed; "3" (unpadded) accepted [v1] EX-4


async def handle_msg(raw_body: bytes, store: Store) -> Response:
    try:
        msg = parse_message(raw_body)
        if not _control_is_well_formed(msg.control):
            raise e201()
        # TODO(evidence): control VALUE check (E202) once the algorithm is known.
        entry = COMMANDS.get(msg.command.upper())
        if entry is None:
            raise e301()
        arity, handler = entry
        if len(msg.args) != arity:
            raise e302()
        reply = handler(store.get_state(), msg.args)
        return JSONResponse(reply.body, status_code=reply.status)
    except ServiceError as err:
        return JSONResponse(err.body(), status_code=err.status)
    except Unevidenced:
        return JSONResponse(NOT_IMPLEMENTED, status_code=501)
