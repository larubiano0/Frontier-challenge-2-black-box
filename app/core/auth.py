"""Bearer-token handling.

Only the README contract is established: `Authorization: Bearer <token>`,
with the token compared to FRONTIER_TOKEN. The exact original response for
a missing/wrong token is UNKNOWN; `unauthorized_response` is the single place
to replace it once evidenced. Current body is a PLACEHOLDER (supuesto).
"""
from fastapi import Request
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings


def is_authorized(request: Request) -> bool:
    expected = get_settings().token
    if not expected:
        return False  # no token configured -> nothing is authorized
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    return scheme.lower() == "bearer" and value == expected


def unauthorized_response() -> Response:
    # TODO(evidence): status/body of the original for bad/missing token.
    return JSONResponse({"error": "unauthorized"}, status_code=401)
