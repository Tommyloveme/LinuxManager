from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import current_identity, current_user, cwd_of, db_session, linux_user_of
from app.api.schemas import PlaybookIn, PlaybookPatch
from app.core.exceptions import CedarError
from app.db.models import AppUser, LinuxIdentity, Playbook, PlaybookRun
from app.modules.playbooks.service import PlaybookService

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


def _playbook_out(pb: Playbook) -> dict:
    return {
        "id": pb.id,
        "name": pb.name,
        "description": pb.description,
        "tags": pb.tags,
        "stop_on_error": pb.stop_on_error,
        "updated_at": pb.updated_at.isoformat() if pb.updated_at else None,
        "steps": [
            {
                "id": s.id,
                "ord": s.ord,
                "name": s.name,
                "kind": s.kind,
                "payload": json.loads(s.payload or "{}"),
                "on_error": s.on_error,
            }
            for s in sorted(pb.steps, key=lambda x: x.ord)
        ],
    }


def _run_out(run: PlaybookRun) -> dict:
    return {
        "id": run.id,
        "playbook_id": run.playbook_id,
        "playbook_name": run.playbook.name if run.playbook else "",
        "linux_user": run.linux_user,
        "status": run.status,
        "log": run.log,
        "current_step": run.current_step,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
    }


@router.get("")
async def list_playbooks(_: object = Depends(current_user), db: AsyncSession = Depends(db_session)) -> dict:
    items = await PlaybookService(db).list_playbooks()
    return {"items": [_playbook_out(p) for p in items]}


@router.post("")
async def create_playbook(
    body: PlaybookIn,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    pb = await PlaybookService(db).create(body.model_dump(), [s.model_dump() for s in body.steps])
    return _playbook_out(pb)


@router.get("/runs")
async def list_runs(
    playbook_id: int | None = None,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    items = await PlaybookService(db).list_runs(playbook_id)
    return {"items": [_run_out(r) for r in items]}


@router.get("/{playbook_id}")
async def get_playbook(playbook_id: int, _: object = Depends(current_user), db: AsyncSession = Depends(db_session)) -> dict:
    try:
        return _playbook_out(await PlaybookService(db).get(playbook_id))
    except CedarError as exc:
        raise exc.as_http() from exc


@router.patch("/{playbook_id}")
async def patch_playbook(
    playbook_id: int,
    body: PlaybookPatch,
    _: object = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        steps = [s.model_dump() for s in body.steps] if body.steps is not None else None
        pb = await PlaybookService(db).update(playbook_id, body.model_dump(exclude={"steps"}), steps)
        return _playbook_out(pb)
    except CedarError as exc:
        raise exc.as_http() from exc


@router.delete("/{playbook_id}")
async def delete_playbook(
    playbook_id: int, _: object = Depends(current_user), db: AsyncSession = Depends(db_session)
) -> dict:
    try:
        await PlaybookService(db).delete(playbook_id)
        return {"ok": True}
    except CedarError as exc:
        raise exc.as_http() from exc


@router.post("/{playbook_id}/run")
async def run_playbook(
    playbook_id: int,
    user: AppUser = Depends(current_user),
    identity: LinuxIdentity = Depends(current_identity),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        run = await PlaybookService(db).run(
            playbook_id,
            linux_user=linux_user_of(identity),
            cwd=cwd_of(identity),
            actor=user.username,
        )
        return _run_out(run)
    except CedarError as exc:
        raise exc.as_http() from exc
