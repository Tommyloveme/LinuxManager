from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import current_user
from app.modules.system.service import SystemService

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/overview")
async def overview(_: object = Depends(current_user)) -> dict:
    return SystemService().overview()


@router.get("/os")
async def os_info(_: object = Depends(current_user)) -> dict:
    from app.modules.system.service import ServiceManager

    return ServiceManager().os_release()
