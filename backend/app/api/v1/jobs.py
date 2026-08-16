from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.db.models import Job
from app.modules.jobs.service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_out(job: Job) -> dict:
    return {
        "id": job.id,
        "kind": job.kind,
        "title": job.title,
        "status": job.status,
        "progress": job.progress,
        "result": job.result,
        "error": job.error,
        "artifact_path": job.artifact_path,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.get("")
async def list_jobs(_: object = Depends(current_user), db: AsyncSession = Depends(db_session)) -> dict:
    items = await JobService(db).list_jobs()
    return {"items": [_job_out(j) for j in items]}
