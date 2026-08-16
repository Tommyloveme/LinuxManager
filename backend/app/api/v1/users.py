from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import current_identity, current_user
from app.core.exceptions import CedarError
from app.db.models import LinuxIdentity
from app.modules.linux_users.service import LinuxUserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(_: object = Depends(current_user)) -> dict:
    return {"items": LinuxUserService().list_users()}


@router.get("/whoami")
async def whoami(identity: LinuxIdentity = Depends(current_identity)) -> dict:
    try:
        return await LinuxUserService().whoami(identity.linux_user or None)
    except CedarError as exc:
        raise exc.as_http() from exc
