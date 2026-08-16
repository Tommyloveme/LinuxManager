from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import AppUser, LinuxIdentity


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def ensure_admin(self, username: str, password: str) -> None:
        existing = await self.db.scalar(select(AppUser).where(AppUser.username == username))
        if existing:
            return
        user = AppUser(
            username=username,
            password_hash=hash_password(password),
            display_name="管理员",
            is_admin=True,
            must_change_password=True,
        )
        self.db.add(user)
        await self.db.commit()

    async def authenticate(self, username: str, password: str) -> tuple[AppUser, str]:
        user = await self.db.scalar(select(AppUser).where(AppUser.username == username))
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("用户名或密码错误")
        token = create_access_token(user.username, {"uid": user.id, "admin": user.is_admin})
        return user, token

    async def get_by_username(self, username: str) -> AppUser | None:
        return await self.db.scalar(select(AppUser).where(AppUser.username == username))

    async def change_password(self, user: AppUser, old: str, new: str) -> None:
        if not verify_password(old, user.password_hash):
            raise AuthError("原密码不正确")
        if len(new) < 8:
            raise AuthError("新密码至少 8 位")
        user.password_hash = hash_password(new)
        user.must_change_password = False
        await self.db.commit()

    async def identity_for(self, user: AppUser) -> LinuxIdentity:
        row = await self.db.scalar(select(LinuxIdentity).where(LinuxIdentity.app_user_id == user.id))
        if row:
            return row
        row = LinuxIdentity(app_user_id=user.id, linux_user="", cwd="")
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row
