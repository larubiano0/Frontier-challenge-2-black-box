"""HTTP routing. Body is read raw (no pydantic models) so exact original
HTTP behavior can be reproduced later."""
from fastapi import APIRouter, Request

from app.core.auth import is_authorized, unauthorized_response
from app.services.dispatcher import handle_msg
from app.storage.memory import store

router = APIRouter()


@router.get("/health")
async def health(request: Request):
    # Auth requirement on /health is unconfirmed; README says all calls carry the token.
    if not is_authorized(request):
        return unauthorized_response()
    return {"status": "ok"}  # body is a placeholder (supuesto)


@router.post("/__reset")
async def reset(request: Request):
    if not is_authorized(request):
        return unauthorized_response()
    store.reset()
    return {"ok": True}  # body is a placeholder (supuesto)


@router.post("/msg")
async def msg(request: Request):
    if not is_authorized(request):
        return unauthorized_response()
    return await handle_msg(await request.body(), store)
