"""Command dispatch skeleton.

Future agents implement: PING, ALTA, CONSULTA, DEPOSITO, TRANSFER, ANULA.
Parsing, integrity (control field), arity and error precedence are NOT
implemented: none are evidenced yet.
"""
from fastapi.responses import JSONResponse, Response

from app.storage.base import Store

COMMANDS: dict[str, object] = {}  # name -> handler(store, args); empty for now


async def handle_msg(raw_body: bytes, store: Store) -> Response:
    # PLACEHOLDER: does NOT reproduce the original service.
    return JSONResponse({"error": "not_implemented"}, status_code=501)
