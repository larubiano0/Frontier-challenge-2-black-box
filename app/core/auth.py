"""Bearer-token handling.

`Authorization: Bearer <token>` compared to FRONTIER_TOKEN (README contract).
Missing or wrong token on a KNOWN route -> 401 E001 (ids 65-69). Unknown routes
answer E404 before auth is checked (id 77). The header value must equal exactly
"Bearer <token>" (ids 3734-3749).
"""
from starlette.requests import Request

from app.core.config import get_settings


def is_authorized(request: Request) -> bool:
    expected = get_settings().token
    if not expected:
        return False  # no token configured -> nothing is authorized
    # Exact match only: lowercase "bearer", two spaces, tab, other schemes -> 401 (ids 3734-3749).
    return request.headers.get("authorization", "") == f"Bearer {expected}"
