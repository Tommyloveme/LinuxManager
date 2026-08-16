from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.core.security import decode_token
from app.db.models import AppUser, LinuxIdentity
from app.db.session import get_db
from app.modules.auth.service import AuthService

bearer = HTTPBearer(auto_error=False)


async def db_session(db: AsyncSession = Depends(get_db)) -> AsyncSession:
    return db


async def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> AppUser:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")
    payload = decode_token(creds.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效")
    user = await AuthService(db).get_by_username(payload["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


async def current_identity(
    user: AppUser = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    x_linux_user: str | None = Header(default=None, alias="X-Linux-User"),
    x_cwd: str | None = Header(default=None, alias="X-Cwd"),
) -> LinuxIdentity:
    identity = await AuthService(db).identity_for(user)
    if x_linux_user is not None:
        identity.linux_user = x_linux_user
    if x_cwd is not None:
        identity.cwd = x_cwd
    await db.commit()
    await db.refresh(identity)
    return identity


def linux_user_of(identity: LinuxIdentity) -> str | None:
    return identity.linux_user or None


def cwd_of(identity: LinuxIdentity) -> str | None:
    return identity.cwd or None


def raise_cedar(exc: Exception) -> None:
    if isinstance(exc, AuthError):
        raise exc.as_http() from exc
    from app.core.exceptions import CedarError

    if isinstance(exc, CedarError):
        raise exc.as_http() from exc
    raise HTTPException(status_code=400, detail=str(exc)) from exc
