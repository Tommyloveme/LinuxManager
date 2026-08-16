from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def record(
        self,
        *,
        actor: str,
        action: str,
        target: str = "",
        detail: str = "",
        linux_user: str = "",
        ok: bool = True,
    ) -> None:
        self.db.add(
            AuditLog(
                actor=actor,
                linux_user=linux_user,
                action=action,
                target=target[:255],
                detail=detail[:8000],
                ok=ok,
            )
        )
        await self.db.commit()

    async def list_logs(self, limit: int = 200, action: str | None = None) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        return list(await self.db.scalars(stmt))
