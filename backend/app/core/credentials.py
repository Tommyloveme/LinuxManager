"""进程内的 Linux 用户凭据缓存。

用于在 Web 会话里"切换执行身份"：管理员在界面输入目标 Linux 用户的密码并通过校验后，
密码仅保存在服务进程内存中（不落库、不写日志），供 su 执行命令时使用。
服务重启后需要重新验证，避免明文密码持久化带来的风险。
"""

from __future__ import annotations

import threading

_lock = threading.Lock()
_cache: dict[str, str] = {}


def remember(user: str, password: str) -> None:
    with _lock:
        _cache[user] = password


def get(user: str) -> str | None:
    with _lock:
        return _cache.get(user)


def has(user: str) -> bool:
    with _lock:
        return user in _cache


def forget(user: str) -> None:
    with _lock:
        _cache.pop(user, None)
