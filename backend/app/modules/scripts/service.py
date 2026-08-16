from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.executor import LinuxExecutor
from app.core.exceptions import NotFoundError
from app.db.models import Script, ScriptRun
from app.modules.audit.service import AuditService


class ScriptService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.executor = LinuxExecutor()

    async def list_scripts(self) -> list[Script]:
        result = await self.db.scalars(select(Script).order_by(Script.ord, Script.id))
        return list(result)

    async def reorder(self, ordered_ids: list[int]) -> None:
        for index, script_id in enumerate(ordered_ids):
            script = await self.db.get(Script, script_id)
            if script:
                script.ord = index
        await self.db.commit()

    async def create(self, data: dict) -> Script:
        # 新脚本排到末尾
        max_ord = await self.db.scalar(select(func.max(Script.ord)))
        script = Script(**data, ord=(max_ord or 0) + 1)
        self.db.add(script)
        await self.db.commit()
        await self.db.refresh(script)
        return script

    async def get(self, script_id: int) -> Script:
        script = await self.db.get(Script, script_id)
        if not script:
            raise NotFoundError("脚本不存在")
        return script

    async def update(self, script_id: int, data: dict) -> Script:
        script = await self.get(script_id)
        for key, value in data.items():
            if value is not None:
                setattr(script, key, value)
        await self.db.commit()
        await self.db.refresh(script)
        return script

    async def delete(self, script_id: int) -> None:
        script = await self.get(script_id)
        await self.db.delete(script)
        await self.db.commit()

    async def run_one(
        self,
        script: Script,
        *,
        linux_user: str | None,
        cwd: str | None,
        actor: str,
        batch_id: str = "",
    ) -> ScriptRun:
        run = ScriptRun(
            script_id=script.id,
            batch_id=batch_id,
            linux_user=linux_user or "",
            cwd=cwd or "",
            command=f"{script.interpreter} <{script.name}>",
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        try:
            result = await self.executor.run_script_content(
                script.content,
                interpreter=script.interpreter,
                linux_user=linux_user,
                cwd=cwd,
                timeout=script.timeout_sec,
            )
            run.exit_code = result.exit_code
            run.stdout = result.stdout
            run.stderr = result.stderr
            run.cwd = result.cwd
            run.status = "ok" if result.exit_code == 0 else "failed"
        except Exception as exc:  # noqa: BLE001 — persist failure
            run.status = "failed"
            run.stderr = str(exc)
            run.exit_code = -1
        run.finished_at = datetime.now(timezone.utc)
        await self.db.commit()
        await AuditService(self.db).record(
            actor=actor,
            linux_user=linux_user or "",
            action="script.run",
            target=script.name,
            detail=json.dumps({"run_id": run.id, "status": run.status, "exit": run.exit_code}),
            ok=run.status == "ok",
        )
        await self.db.refresh(run)
        # 直接绑定已加载的 script，避免 _run_out 在异步会话里触发关系懒加载（MissingGreenlet）
        run.script = script
        return run

    async def run_batch(
        self,
        script_ids: list[int],
        *,
        linux_user: str | None,
        cwd: str | None,
        actor: str,
        stop_on_error: bool = True,
    ) -> list[ScriptRun]:
        batch_id = str(uuid.uuid4())
        runs: list[ScriptRun] = []
        for script_id in script_ids:
            script = await self.get(script_id)
            run = await self.run_one(script, linux_user=linux_user, cwd=cwd, actor=actor, batch_id=batch_id)
            runs.append(run)
            if stop_on_error and run.status != "ok":
                break
        return runs

    async def list_runs(self, script_id: int | None = None, limit: int = 50) -> list[ScriptRun]:
        stmt = select(ScriptRun).options(selectinload(ScriptRun.script)).order_by(ScriptRun.id.desc()).limit(limit)
        if script_id:
            stmt = stmt.where(ScriptRun.script_id == script_id)
        result = await self.db.scalars(stmt)
        return list(result)
