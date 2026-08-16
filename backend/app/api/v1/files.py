from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_user, db_session
from app.api.schemas import ArchiveIn, FileWriteIn, MkdirIn, SyncIn
from app.core.exceptions import CedarError
from app.core.security import decode_token
from app.db.models import AppUser
from app.modules.audit.service import AuditService
from app.modules.files.service import FileService
from app.modules.jobs.service import JobService

router = APIRouter(prefix="/files", tags=["files"])
svc = FileService()
optional_bearer = HTTPBearer(auto_error=False)


@router.get("/ls")
async def list_dir(path: str = Query(default=""), _: object = Depends(current_user)) -> dict:
    try:
        return svc.list_dir(path)
    except CedarError as exc:
        raise exc.as_http() from exc


@router.get("/read")
async def read_file(path: str, _: object = Depends(current_user)) -> dict:
    try:
        return svc.read_text(path)
    except CedarError as exc:
        raise exc.as_http() from exc


@router.post("/write")
async def write_file(
    body: FileWriteIn,
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        result = svc.write_text(body.path, body.content)
        await AuditService(db).record(actor=user.username, action="file.write", target=body.path)
        return result
    except CedarError as exc:
        raise exc.as_http() from exc


@router.post("/mkdir")
async def mkdir(body: MkdirIn, _: object = Depends(current_user)) -> dict:
    try:
        return svc.mkdir(body.path)
    except CedarError as exc:
        raise exc.as_http() from exc


@router.delete("")
async def remove(path: str, user: AppUser = Depends(current_user), db: AsyncSession = Depends(db_session)) -> dict:
    try:
        svc.remove(path)
        await AuditService(db).record(actor=user.username, action="file.delete", target=path)
        return {"ok": True}
    except CedarError as exc:
        raise exc.as_http() from exc


@router.post("/archive")
async def archive(
    body: ArchiveIn,
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        result = await svc.archive(body.model_dump())
        job = await JobService(db).create("archive", f"打包 {body.output_name}", body.model_dump())
        await JobService(db).finish(
            job, status="ok", result=json.dumps(result, ensure_ascii=False), artifact_path=result["archive_path"]
        )
        await AuditService(db).record(
            actor=user.username,
            action="file.archive",
            target=body.output_name,
            detail=json.dumps(result, ensure_ascii=False),
        )
        return result
    except CedarError as exc:
        raise exc.as_http() from exc


@router.post("/sync")
async def sync(
    body: SyncIn,
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        stats = await svc.sync(body.model_dump())
        await AuditService(db).record(
            actor=user.username, action="file.sync", target=str(len(body.mappings)), detail=json.dumps(stats)
        )
        return stats
    except CedarError as exc:
        raise exc.as_http() from exc


@router.get("/download")
async def download(
    path: str,
    token: str | None = None,
    creds: HTTPAuthorizationCredentials | None = Depends(optional_bearer),
) -> FileResponse:
    raw = token or (creds.credentials if creds else "")
    if not decode_token(raw):
        raise HTTPException(status_code=401, detail="未登录")
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise CedarError("文件不存在", 404).as_http()
    return FileResponse(target, filename=target.name)


@router.post("/upload")
async def upload(
    path: str,
    file: UploadFile = File(...),
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    dest_dir = Path(path).expanduser().resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / (file.filename or "upload.bin")
    content = await file.read()
    dest.write_bytes(content)
    await AuditService(db).record(actor=user.username, action="file.upload", target=str(dest))
    return {"path": str(dest), "size": len(content)}
