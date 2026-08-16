from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.modules.audit.service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit(
    action: str | None = None,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    items = await AuditService(db).list_logs(action=action)
    return {
        "items": [
            {
                "id": row.id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "actor": row.actor,
                "linux_user": row.linux_user,
                "action": row.action,
                "target": row.target,
                "detail": row.detail,
                "ok": row.ok,
            }
            for row in items
        ]
    }
