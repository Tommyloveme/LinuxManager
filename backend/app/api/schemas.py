from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordIn(BaseModel):
    old_password: str
    new_password: str


class IdentityIn(BaseModel):
    linux_user: str = ""
    cwd: str = ""


class UserSwitchIn(BaseModel):
    linux_user: str
    password: str = ""


class ScriptIn(BaseModel):
    name: str
    description: str = ""
    interpreter: str = "/bin/bash"
    content: str = "#!/bin/bash\nset -euo pipefail\necho hello\n"
    tags: str = ""
    timeout_sec: int = 120


class ScriptPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    interpreter: str | None = None
    content: str | None = None
    tags: str | None = None
    timeout_sec: int | None = None


class ScriptRunIn(BaseModel):
    script_ids: list[int]
    stop_on_error: bool = True
    cwd: str | None = None


class PlaybookStepIn(BaseModel):
    name: str = ""
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)
    on_error: str = "stop"
    ord: int | None = None


class PlaybookIn(BaseModel):
    name: str
    description: str = ""
    tags: str = ""
    stop_on_error: bool = True
    steps: list[PlaybookStepIn] = Field(default_factory=list)


class PlaybookPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: str | None = None
    stop_on_error: bool | None = None
    steps: list[PlaybookStepIn] | None = None


class ArchiveIn(BaseModel):
    sources: list[str]
    include: str | None = None
    exclude: str | None = None
    format: str = "tar.gz"
    output_name: str = "bundle"


class SyncMapping(BaseModel):
    src: str
    dst: str


class SyncIn(BaseModel):
    mappings: list[SyncMapping]
    include: str | None = None
    exclude: str | None = None
    delete_extra: bool = False


class FileWriteIn(BaseModel):
    path: str
    content: str


class MkdirIn(BaseModel):
    path: str


class KillIn(BaseModel):
    pid: int
    signal: str = "TERM"


class ServiceActionIn(BaseModel):
    action: str


class CommandIn(BaseModel):
    command: str
    cwd: str | None = None
    timeout: int | None = None


def model_dump_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
