from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.api.schemas import KillIn
from app.core.exceptions import CedarError
from app.db.models import AppUser
from app.modules.audit.service import AuditService
from app.modules.process.service import ProcessService

router = APIRouter(prefix="/process", tags=["process"])
svc = ProcessService()


@router.get("")
async def list_processes(q: str = "", _: object = Depends(current_user)) -> dict:
    return {"items": svc.list_processes(q), "summary": svc.top_summary()}


@router.get("/{pid}")
async def get_process(pid: int, _: object = Depends(current_user)) -> dict:
    try:
        return svc.get(pid)
    except CedarError as exc:
        raise exc.as_http() from exc


@router.post("/kill")
async def kill(
    body: KillIn,
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        svc.kill(body.pid, body.signal)
        await AuditService(db).record(
            actor=user.username, action="process.kill", target=str(body.pid), detail=body.signal
        )
        return {"ok": True}
    except CedarError as exc:
        raise exc.as_http() from exc
