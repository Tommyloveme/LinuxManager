from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.api.schemas import ServiceActionIn
from app.core.exceptions import CedarError
from app.db.models import AppUser
from app.modules.audit.service import AuditService
from app.modules.system.service import ServiceManager

router = APIRouter(prefix="/services", tags=["services"])


@router.get("")
async def list_services(q: str = "", _: object = Depends(current_user)) -> dict:
    items = await ServiceManager().list_units(q)
    return {"items": items}


@router.post("/{unit}/action")
async def action(
    unit: str,
    body: ServiceActionIn,
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        output = await ServiceManager().control(unit, body.action)
        await AuditService(db).record(
            actor=user.username, action=f"service.{body.action}", target=unit, detail=output[-500:]
        )
        return {"output": output}
    except (ValueError, RuntimeError) as exc:
        raise CedarError(str(exc)).as_http() from exc
