from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    import pwd
except ImportError:  # Windows
    pwd = None  # type: ignore[assignment]

from app.core.config import get_settings
from app.core.exceptions import CedarError
from app.core.logging import get_logger

logger = get_logger()


@dataclass
class ExecResult:
    command: str
    cwd: str
    linux_user: str
    exit_code: int
    stdout: str
    stderr: str


class LinuxExecutor:
    """Run commands on the host, optionally as another Linux user."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def current_user(self) -> str:
        try:
            return pwd.getpwuid(os.geteuid()).pw_name
        except (AttributeError, KeyError, ImportError):
            return os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"

    def home_for(self, user: str | None) -> str:
        if not user:
            return str(Path.home())
        try:
            return pwd.getpwnam(user).pw_dir
        except (KeyError, AttributeError, ImportError):
            return str(Path.home())

    async def run(
        self,
        command: str | list[str],
        *,
        linux_user: str | None = None,
        cwd: str | None = None,
        timeout: int | None = None,
        env: dict[str, str] | None = None,
        input_text: str | None = None,
    ) -> ExecResult:
        timeout = timeout or self.settings.command_timeout
        cwd = cwd or self.home_for(linux_user)
        argv = self._build_argv(command, linux_user)
        display = command if isinstance(command, str) else " ".join(command)
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        logger.info("exec user=%s cwd=%s cmd=%s", linux_user or self.current_user(), cwd, display[:200])

        def _run() -> subprocess.CompletedProcess[str]:
            Path(cwd).mkdir(parents=True, exist_ok=True)
            return subprocess.run(
                argv,
                cwd=cwd,
                env=merged_env,
                input=input_text,
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=False,
            )

        try:
            completed = await asyncio.to_thread(_run)
        except subprocess.TimeoutExpired as exc:
            raise CedarError(f"命令超时（{timeout}s）: {display[:120]}", 408) from exc
        except FileNotFoundError as exc:
            raise CedarError(f"工作目录或可执行文件不存在: {cwd}") from exc

        stdout = self._clip(completed.stdout or "")
        stderr = self._clip(completed.stderr or "")
        return ExecResult(
            command=display,
            cwd=cwd,
            linux_user=linux_user or self.current_user(),
            exit_code=completed.returncode,
            stdout=stdout,
            stderr=stderr,
        )

    async def run_script_content(
        self,
        content: str,
        *,
        interpreter: str = "/bin/bash",
        linux_user: str | None = None,
        cwd: str | None = None,
        timeout: int | None = None,
    ) -> ExecResult:
        suffix = ".sh"
        if "python" in interpreter:
            suffix = ".py"
        elif "pwsh" in interpreter or "powershell" in interpreter:
            suffix = ".ps1"

        def _write() -> str:
            handle = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=suffix,
                prefix="cedar-",
                dir=str(self.settings.script_dir),
                delete=False,
                encoding="utf-8",
                newline="\n",
            )
            handle.write(content)
            if not content.endswith("\n"):
                handle.write("\n")
            handle.close()
            os.chmod(handle.name, 0o700)
            return handle.name

        path = await asyncio.to_thread(_write)
        try:
            exe = interpreter if Path(interpreter).exists() or shutil.which(interpreter) else interpreter
            return await self.run(
                [exe, path],
                linux_user=linux_user,
                cwd=cwd,
                timeout=timeout,
            )
        finally:
            Path(path).unlink(missing_ok=True)

    def _build_argv(self, command: str | list[str], linux_user: str | None) -> list[str]:
        if isinstance(command, str):
            inner = ["/bin/bash", "-lc", command] if os.name != "nt" else ["cmd", "/c", command]
        else:
            inner = list(command)

        if not linux_user or linux_user == self.current_user() or not self.settings.allow_user_switch:
            return inner
        if os.name == "nt":
            return inner
        sudo = shutil.which("sudo") or "/usr/bin/sudo"
        return [sudo, "-u", linux_user, "-H", "--"] + inner

    def _clip(self, text: str) -> str:
        limit = self.settings.max_output_bytes
        encoded = text.encode("utf-8", errors="replace")
        if len(encoded) <= limit:
            return text
        return encoded[:limit].decode("utf-8", errors="replace") + "\n…(输出已截断)"
