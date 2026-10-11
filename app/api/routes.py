"""HTTP layer: one catch-all handler so FastAPI/Starlette defaults (404/405/422,
trailing-slash redirects) never leak.

Order (reports/handoff_implementation.md §1):
  1. route + method: only GET /health, POST /__reset, POST /msg exist; anything
     else (other method, other path, '/msg/', '/MSG') -> 404 E404, before auth
     (ids 70-77, 91, 92).
  2. auth on known routes -> 401 E001 (ids 65-69).
  3. route handler.
"""
import json
from itertools import count

from starlette.requests import Request
from starlette.responses import Response

from app.core.auth import is_authorized
from app.domain.errors import ServiceError, e001, e404, e599
from app.services.dispatcher import process
from app.storage.memory import store

_KNOWN = {("GET", "/health"), ("POST", "/__reset"), ("POST", "/msg")}

# X-Req: +1 per authorized POST /msg, NOT reset by /__reset (log ids 21-23). Headers are not
# scored; kept for fidelity only [probable].
_x_req = count(1)


def json_response(status: int, body: dict, headers: dict | None = None) -> Response:
    content = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(content, status_code=status, headers=headers,
                    media_type="application/json; charset=utf-8")


def error_response(err: ServiceError) -> Response:
    return json_response(err.status, err.body())


async def handle(request: Request) -> Response:
    # Raw, undecoded path without query string: '/m%73g' is NOT '/msg' (id 3725).
    raw_path = (request.scope.get("raw_path") or request.url.path.encode()).split(b"?", 1)[0].decode("latin-1")
    key = (request.method.upper(), raw_path)
    if key not in _KNOWN:
        return error_response(e404())
    if not is_authorized(request):
        return error_response(e001())
    if key == ("GET", "/health"):
        return json_response(200, {"ok": True})                    # id 64
    if key == ("POST", "/__reset"):
        store.reset()                                              # clears accounts, ops, counters, blocks
        return json_response(200, {"ok": True})                    # id 1
    if store.get_state().halted:               # after HALT;1: every /msg -> 503, before size/JSON checks (ids 3003-3015)
        return error_response(e599())
    raw = await request.body()
    status, body = process(raw, store)                             # synchronous -> atomic per request
    return json_response(status, body, {"X-Req": str(next(_x_req))})
