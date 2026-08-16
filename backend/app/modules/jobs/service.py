from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job


class JobService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, kind: str, title: str, payload: dict) -> Job:
        job = Job(kind=kind, title=title, payload=json.dumps(payload, ensure_ascii=False), status="queued")
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def finish(self, job: Job, *, status: str, result: str = "", error: str = "", artifact_path: str = "") -> Job:
        job.status = status
        job.result = result
        job.error = error
        job.artifact_path = artifact_path
        job.progress = 100 if status == "ok" else job.progress
        job.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def list_jobs(self, limit: int = 80) -> list[Job]:
        result = await self.db.scalars(select(Job).order_by(Job.id.desc()).limit(limit))
        return list(result)

    async def get(self, job_id: int) -> Job | None:
        return await self.db.get(Job, job_id)
