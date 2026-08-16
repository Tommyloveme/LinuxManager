from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.executor import LinuxExecutor
from app.api.deps import current_identity, current_user, db_session
from app.api.schemas import UserSwitchIn
from app.core import credentials
from app.core.exceptions import CedarError
from app.db.models import AppUser, LinuxIdentity
from app.modules.auth.service import AuthService
from app.modules.linux_users.service import LinuxUserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users(_: object = Depends(current_user)) -> dict:
    return {"items": LinuxUserService().list_users()}


@router.get("/whoami")
async def whoami(identity: LinuxIdentity = Depends(current_identity)) -> dict:
    executor = LinuxExecutor()
    target = identity.linux_user or ""
    svc = LinuxUserService()
    verified = credentials.has(target) if target else True
    # 需要 su 但尚未验证（例如服务重启后凭据丢失）：不实际执行 id，避免报错
    if target and executor.needs_su(target) and not verified:
        base = svc.get_user(target) if any(u["name"] == target for u in svc.list_users()) else {
            "name": target, "home": executor.home_for(target), "shell": "", "uid": None,
            "gid": None, "gecos": "", "is_system": False,
        }
        base.update({"id_output": "", "id_ok": False, "id_error": "身份未验证，请重新输入密码切换", "verified": False})
        return base
    try:
        info = await svc.whoami(target or None)
        info["verified"] = verified
        return info
    except CedarError as exc:
        raise exc.as_http() from exc


@router.post("/switch")
async def switch_user(
    body: UserSwitchIn,
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """校验目标 Linux 用户密码并切换执行身份。

    - 切回当前进程用户或 root 进程下切换：无需密码。
    - 非 root 切换到其它用户：用 su 校验密码，通过后把密码缓存在服务内存。
    """
    executor = LinuxExecutor()
    target = body.linux_user.strip()
    svc = LinuxUserService()

    if not target or target == executor.current_user():
        credentials.forget(target)
        home = executor.home_for(target or None)
        await _persist_identity(db, user, target, home)
        return {"ok": True, "linux_user": target, "cwd": home, "verified": True, "message": "已切换"}

    is_root = False
    try:
        is_root = os.geteuid() == 0
    except AttributeError:
        is_root = False

    if is_root:
        home = executor.home_for(target)
        await _persist_identity(db, user, target, home)
        return {"ok": True, "linux_user": target, "cwd": home, "verified": True, "message": "root 直接切换"}

    if not body.password:
        raise CedarError("请输入该用户的登录密码", 400).as_http()

    ok, output = await _verify(executor, target, body.password)
    if not ok:
        raise CedarError(f"密码校验失败：{output or '认证不通过'}", 401).as_http()

    credentials.remember(target, body.password)
    home = executor.home_for(target)
    await _persist_identity(db, user, target, home)
    return {"ok": True, "linux_user": target, "cwd": home, "verified": True, "id_output": output}


async def _verify(executor: LinuxExecutor, user: str, password: str) -> tuple[bool, str]:
    import asyncio

    return await asyncio.to_thread(executor.verify_password, user, password)


async def _persist_identity(db: AsyncSession, app_user: AppUser, linux_user: str, cwd: str) -> None:
    identity = await AuthService(db).identity_for(app_user)
    identity.linux_user = linux_user
    identity.cwd = cwd
    await db.commit()
