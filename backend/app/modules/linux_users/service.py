from __future__ import annotations

import os
from pathlib import Path

from app.adapters.executor import LinuxExecutor
from app.core.exceptions import CedarError


class LinuxUserService:
    SYSTEM_UID_MAX = 999

    def __init__(self) -> None:
        self.executor = LinuxExecutor()

    def list_users(self) -> list[dict]:
        users: list[dict] = []
        passwd = Path("/etc/passwd")
        if not passwd.exists():
            name = self.executor.current_user()
            return [
                {
                    "name": name,
                    "uid": 0,
                    "gid": 0,
                    "gecos": "current",
                    "home": str(Path.home()),
                    "shell": os.environ.get("SHELL") or os.environ.get("COMSPEC") or "",
                    "is_system": False,
                }
            ]
        for line in passwd.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line or line.startswith("#"):
                continue
            parts = line.split(":")
            if len(parts) < 7:
                continue
            name, _pw, uid_s, gid_s, gecos, home, shell = parts[:7]
            uid = int(uid_s)
            users.append(
                {
                    "name": name,
                    "uid": uid,
                    "gid": int(gid_s),
                    "gecos": gecos,
                    "home": home,
                    "shell": shell,
                    "is_system": uid < self.SYSTEM_UID_MAX,
                }
            )
        users.sort(key=lambda item: (item["is_system"], item["uid"]))
        return users

    def get_user(self, name: str) -> dict:
        for user in self.list_users():
            if user["name"] == name:
                return user
        raise CedarError(f"Linux 用户不存在: {name}", 404)

    async def whoami(self, linux_user: str | None) -> dict:
        result = await self.executor.run("id", linux_user=linux_user)
        user = linux_user or self.executor.current_user()
        info = self.get_user(user) if any(u["name"] == user for u in self.list_users()) else {
            "name": user,
            "home": self.executor.home_for(user),
            "shell": "",
            "uid": None,
            "gid": None,
            "gecos": "",
            "is_system": False,
        }
        info["id_output"] = result.stdout.strip()
        info["id_ok"] = result.exit_code == 0
        info["id_error"] = result.stderr.strip()
        return info
