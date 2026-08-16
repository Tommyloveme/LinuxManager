from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.executor import LinuxExecutor
from app.api.deps import current_identity, current_user, db_session
from app.api.schemas import IdentityIn, LoginIn, PasswordIn
from app.core.exceptions import CedarError
from app.core.module_registry import list_modules
from app.db.models import AppUser, LinuxIdentity
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(body: LoginIn, db: AsyncSession = Depends(db_session)) -> dict:
    try:
        user, token = await AuthService(db).authenticate(body.username, body.password)
    except CedarError as exc:
        raise exc.as_http() from exc
    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "must_change_password": user.must_change_password,
        },
        "modules": list_modules(),
    }


@router.get("/me")
async def me(
    user: AppUser = Depends(current_user),
    identity: LinuxIdentity = Depends(current_identity),
) -> dict:
    executor = LinuxExecutor()
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "must_change_password": user.must_change_password,
        },
        "identity": {
            "linux_user": identity.linux_user or executor.current_user(),
            "cwd": identity.cwd or executor.home_for(identity.linux_user or None),
            "host_user": executor.current_user(),
        },
        "modules": list_modules(),
    }


@router.post("/password")
async def password(
    body: PasswordIn,
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    try:
        await AuthService(db).change_password(user, body.old_password, body.new_password)
    except CedarError as exc:
        raise exc.as_http() from exc
    return {"ok": True}


@router.put("/identity")
async def set_identity(
    body: IdentityIn,
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    identity = await AuthService(db).identity_for(user)
    identity.linux_user = body.linux_user
    identity.cwd = body.cwd
    await db.commit()
    return {"linux_user": identity.linux_user, "cwd": identity.cwd}
