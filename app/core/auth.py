"""Bearer-token handling.

`Authorization: Bearer <token>` compared to FRONTIER_TOKEN (README contract).
Missing or wrong token on a KNOWN route -> 401 E001 (ids 65-69). Unknown routes
answer E404 before auth is checked (id 77). Scheme matched case-insensitively
and token compared exactly [supuesto: variants not probed].
"""
from starlette.requests import Request

from app.core.config import get_settings


def is_authorized(request: Request) -> bool:
    expected = get_settings().token
    if not expected:
        return False  # no token configured -> nothing is authorized
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    return scheme.lower() == "bearer" and value == expected
