from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_identity, current_user, cwd_of, db_session, linux_user_of
from app.api.schemas import (
    ScriptBatchDeleteIn,
    ScriptIn,
    ScriptPatch,
    ScriptReorderIn,
    ScriptRunIn,
    ScriptRunOneIn,
)
from app.core.exceptions import CedarError
from app.db.models import AppUser, LinuxIdentity, Script, ScriptRun
from app.modules.scripts.service import ScriptService

router = APIRouter(prefix="/scripts", tags=["scripts"])


def _script_out(script: Script) -> dict:
    return {
        "id": script.id,
        "name": script.name,
        "description": script.description,
        "interpreter": script.interpreter,
        "content": script.content,
        "tags": script.tags,
        "timeout_sec": script.timeout_sec,
        "ord": script.ord,
        "default_args": script.default_args,
        "updated_at": script.updated_at.isoformat() if script.updated_at else None,
    }


def _run_out(run: ScriptRun) -> dict:
    return {
        "id": run.id,
        "script_id": run.script_id,
        "script_name": run.script.name if run.script else "",
        "batch_id": run.batch_id,
        "linux_user": run.linux_user,
        "cwd": run.cwd,
        "command": run.command,
        "status": run.status,
        "exit_code": run.exit_code,
        "stdout": run.stdout,
        "stderr": run.stderr,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@router.get("")
async def list_scripts(
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    items = await ScriptService(db).list_scripts()
    return {"items": [_script_out(s) for s in items]}


@router.post("")
async def create_script(
    body: ScriptIn,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    script = await ScriptService(db).create(body.model_dump())
    return _script_out(script)


@router.post("/reorder")
async def reorder_scripts(
    body: ScriptReorderIn,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    svc = ScriptService(db)
    await svc.reorder(body.ids)
    items = await svc.list_scripts()
    return {"items": [_script_out(s) for s in items]}


@router.post("/batch-delete")
async def batch_delete_scripts(
    body: ScriptBatchDeleteIn,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    deleted = await ScriptService(db).delete_many(body.ids)
    return {"deleted": deleted}


@router.get("/runs")
async def list_runs(
    script_id: int | None = None,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    items = await ScriptService(db).list_runs(script_id)
    return {"items": [_run_out(r) for r in items]}


@router.get("/{script_id}")
async def get_script(
    script_id: int,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        return _script_out(await ScriptService(db).get(script_id))
    except CedarError as exc:
        raise exc.as_http() from exc


@router.patch("/{script_id}")
async def patch_script(
    script_id: int,
    body: ScriptPatch,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        script = await ScriptService(db).update(script_id, body.model_dump())
        return _script_out(script)
    except CedarError as exc:
        raise exc.as_http() from exc


@router.delete("/{script_id}")
async def delete_script(
    script_id: int,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        await ScriptService(db).delete(script_id)
        return {"ok": True}
    except CedarError as exc:
        raise exc.as_http() from exc


@router.post("/{script_id}/run")
async def run_script(
    script_id: int,
    body: ScriptRunOneIn | None = None,
    user: AppUser = Depends(current_user),
    identity: LinuxIdentity = Depends(current_identity),
    db: AsyncSession = Depends(db_session),
) -> dict:
    svc = ScriptService(db)
    try:
        script = await svc.get(script_id)
        run = await svc.run_one(
            script,
            linux_user=linux_user_of(identity),
            cwd=cwd_of(identity),
            actor=user.username,
            args=body.args if body else None,
        )
        return _run_out(run)
    except CedarError as exc:
        raise exc.as_http() from exc


@router.post("/batch")
async def run_batch(
    body: ScriptRunIn,
    user: AppUser = Depends(current_user),
    identity: LinuxIdentity = Depends(current_identity),
    db: AsyncSession = Depends(db_session),
) -> dict:
    svc = ScriptService(db)
    try:
        runs = await svc.run_batch(
            body.script_ids,
            linux_user=linux_user_of(identity),
            cwd=body.cwd or cwd_of(identity),
            actor=user.username,
            stop_on_error=body.stop_on_error,
        )
        return {"items": [_run_out(r) for r in runs]}
    except CedarError as exc:
        raise exc.as_http() from exc
