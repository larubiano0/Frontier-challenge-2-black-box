from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import e404, error_response, handle

ALL_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD", "TRACE", "CONNECT"]

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False)
app.add_route("/{path:path}", handle, methods=ALL_METHODS, include_in_schema=False)


@app.exception_handler(StarletteHTTPException)
async def _any_http_error(request, exc):
    # Methods outside ALL_METHODS (405) or anything Starlette rejects -> original's E404.
    return error_response(e404())
