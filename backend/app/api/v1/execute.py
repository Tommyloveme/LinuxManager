from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.executor import LinuxExecutor
from app.api.deps import current_identity, current_user, cwd_of, db_session, linux_user_of
from app.api.schemas import CommandIn
from app.core.exceptions import CedarError
from app.db.models import AppUser, LinuxIdentity
from app.modules.audit.service import AuditService

router = APIRouter(prefix="/exec", tags=["exec"])


@router.post("")
async def exec_command(
    body: CommandIn,
    user: AppUser = Depends(current_user),
    identity: LinuxIdentity = Depends(current_identity),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        result = await LinuxExecutor().run(
            body.command,
            linux_user=linux_user_of(identity),
            cwd=body.cwd or cwd_of(identity),
            timeout=body.timeout,
        )
        await AuditService(db).record(
            actor=user.username,
            linux_user=result.linux_user,
            action="exec.command",
            target=body.command[:200],
            ok=result.exit_code == 0,
        )
        return {
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cwd": result.cwd,
            "linux_user": result.linux_user,
        }
    except CedarError as exc:
        raise exc.as_http() from exc
