from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.adapters.archive import ArchiveAdapter
from app.adapters.executor import LinuxExecutor
from app.core.exceptions import CedarError, NotFoundError
from app.db.models import Playbook, PlaybookRun, PlaybookStep, Script
from app.modules.audit.service import AuditService
from app.modules.process.service import ProcessService
from app.modules.system.service import ServiceManager


class PlaybookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.executor = LinuxExecutor()
        self.archive = ArchiveAdapter()

    async def list_playbooks(self) -> list[Playbook]:
        result = await self.db.scalars(
            select(Playbook).options(selectinload(Playbook.steps)).order_by(Playbook.updated_at.desc())
        )
        return list(result)

    async def get(self, playbook_id: int) -> Playbook:
        playbook = await self.db.scalar(
            select(Playbook).options(selectinload(Playbook.steps)).where(Playbook.id == playbook_id)
        )
        if not playbook:
            raise NotFoundError("批处理不存在")
        return playbook

    async def create(self, data: dict, steps: list[dict]) -> Playbook:
        playbook = Playbook(
            name=data["name"],
            description=data.get("description") or "",
            tags=data.get("tags") or "",
            stop_on_error=data.get("stop_on_error", True),
        )
        self.db.add(playbook)
        await self.db.flush()
        self._replace_steps(playbook, steps)
        await self.db.commit()
        return await self.get(playbook.id)

    async def update(self, playbook_id: int, data: dict, steps: list[dict] | None) -> Playbook:
        playbook = await self.get(playbook_id)
        for key in ("name", "description", "tags", "stop_on_error"):
            if key in data and data[key] is not None:
                setattr(playbook, key, data[key])
        if steps is not None:
            for step in list(playbook.steps):
                await self.db.delete(step)
            await self.db.flush()
            self._replace_steps(playbook, steps)
        await self.db.commit()
        return await self.get(playbook_id)

    async def delete(self, playbook_id: int) -> None:
        playbook = await self.get(playbook_id)
        await self.db.delete(playbook)
        await self.db.commit()

    def _replace_steps(self, playbook: Playbook, steps: list[dict]) -> None:
        # 通过 playbook_id 直接建行，避免在 async 会话里触发关系懒加载（MissingGreenlet）
        for index, item in enumerate(steps):
            payload = item.get("payload") or {}
            if not isinstance(payload, str):
                payload = json.dumps(payload, ensure_ascii=False)
            self.db.add(
                PlaybookStep(
                    playbook_id=playbook.id,
                    ord=item.get("ord", index),
                    name=item.get("name") or f"步骤 {index + 1}",
                    kind=item["kind"],
                    payload=payload,
                    on_error=item.get("on_error") or "stop",
                )
            )

    async def run(self, playbook_id: int, *, linux_user: str | None, cwd: str | None, actor: str) -> PlaybookRun:
        playbook = await self.get(playbook_id)
        run = PlaybookRun(
            playbook_id=playbook.id,
            linux_user=linux_user or "",
            status="running",
            started_at=datetime.now(timezone.utc),
            log="",
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)
        lines: list[str] = [f"开始执行「{playbook.name}」"]
        ok = True
        for step in sorted(playbook.steps, key=lambda s: s.ord):
            run.current_step = step.ord
            lines.append(f"→ [{step.kind}] {step.name}")
            try:
                output = await self._execute_step(step, linux_user=linux_user, cwd=cwd)
                lines.append(output or "(完成)")
            except Exception as exc:  # noqa: BLE001
                ok = False
                lines.append(f"失败: {exc}")
                if (step.on_error or "stop") == "stop" or playbook.stop_on_error:
                    run.status = "failed"
                    break
            run.log = "\n".join(lines)
            await self.db.commit()
        else:
            run.status = "ok" if ok else "failed"
        if run.status == "running":
            run.status = "ok" if ok else "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.log = "\n".join(lines)
        await self.db.commit()
        await AuditService(self.db).record(
            actor=actor,
            linux_user=linux_user or "",
            action="playbook.run",
            target=playbook.name,
            detail=json.dumps({"run_id": run.id, "status": run.status}),
            ok=run.status == "ok",
        )
        await self.db.refresh(run)
        return run

    async def _execute_step(self, step: PlaybookStep, *, linux_user: str | None, cwd: str | None) -> str:
        payload = json.loads(step.payload or "{}")
        kind = step.kind
        if kind == "command":
            result = await self.executor.run(
                payload.get("command") or "",
                linux_user=linux_user,
                cwd=payload.get("cwd") or cwd,
                timeout=payload.get("timeout") or 120,
            )
            if result.exit_code != 0:
                raise CedarError(result.stderr or f"exit {result.exit_code}")
            return (result.stdout or result.stderr)[-4000:]
        if kind == "script":
            script = await self.db.get(Script, int(payload["script_id"]))
            if not script:
                raise NotFoundError("步骤引用的脚本不存在")
            result = await self.executor.run_script_content(
                script.content,
                interpreter=script.interpreter,
                linux_user=linux_user,
                cwd=payload.get("cwd") or cwd,
                timeout=script.timeout_sec,
            )
            if result.exit_code != 0:
                raise CedarError(result.stderr or f"exit {result.exit_code}")
            return (result.stdout or "")[-4000:]
        if kind == "archive":
            result = await self.archive.create_archive(
                payload.get("sources") or [],
                include=payload.get("include"),
                exclude=payload.get("exclude"),
                fmt=payload.get("format") or "tar.gz",
                output_name=payload.get("output_name") or step.name,
            )
            return f"打包 {result.file_count} 个文件 → {result.archive_path}"
        if kind == "sync":
            stats = await self.archive.sync_dirs(
                payload.get("mappings") or [],
                include=payload.get("include"),
                exclude=payload.get("exclude"),
                delete_extra=bool(payload.get("delete_extra")),
            )
            return f"同步 copied={stats['copied']} skipped={stats['skipped']}"
        if kind == "process":
            svc = ProcessService()
            action = payload.get("action") or "kill"
            pid = int(payload["pid"])
            if action == "kill":
                svc.kill(pid, payload.get("signal") or "TERM")
                return f"已向 pid {pid} 发送信号"
            raise CedarError(f"未知进程动作: {action}")
        if kind == "service":
            mgr = ServiceManager()
            name = payload["unit"]
            action = payload.get("action") or "status"
            return await mgr.control(name, action)
        if kind == "wait":
            seconds = float(payload.get("seconds") or 1)
            await asyncio.sleep(min(seconds, 300))
            return f"等待 {seconds}s"
        raise CedarError(f"未知步骤类型: {kind}")

    async def list_runs(self, playbook_id: int | None = None, limit: int = 40) -> list[PlaybookRun]:
        stmt = select(PlaybookRun).options(selectinload(PlaybookRun.playbook)).order_by(PlaybookRun.id.desc()).limit(limit)
        if playbook_id:
            stmt = stmt.where(PlaybookRun.playbook_id == playbook_id)
        return list(await self.db.scalars(stmt))
