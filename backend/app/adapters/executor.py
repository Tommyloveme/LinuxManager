from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import pwd
except ImportError:  # Windows
    pwd = None  # type: ignore[assignment]

from app.core import credentials
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

    def needs_su(self, linux_user: str | None) -> bool:
        """是否需要通过 su 切换到目标用户（当前进程既非该用户、也非 root）。"""
        if not linux_user or not self.settings.allow_user_switch or os.name == "nt":
            return False
        if linux_user == self.current_user():
            return False
        try:
            return os.geteuid() != 0  # root 可直接 sudo -u，无需密码
        except AttributeError:
            return False

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
        display = command if isinstance(command, str) else " ".join(command)

        # 非 root 进程切换到其它用户：走 su + 缓存密码（用 PTY 喂密码）
        if self.needs_su(linux_user):
            password = credentials.get(linux_user or "")
            if password is None:
                raise CedarError(
                    f"尚未验证用户 {linux_user} 的密码，请先到「执行身份」页面完成切换", 403
                )
            inner = command if isinstance(command, str) else " ".join(shlex.quote(c) for c in command)
            logger.info("exec(su) user=%s cwd=%s cmd=%s", linux_user, cwd, display[:200])
            exit_code, output = await asyncio.to_thread(
                self._su_run, linux_user or "", password, inner, cwd, timeout
            )
            return ExecResult(
                command=display,
                cwd=cwd,
                linux_user=linux_user or self.current_user(),
                exit_code=exit_code,
                stdout=self._clip(output),
                stderr="",
            )

        argv = self._build_argv(command, linux_user)
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

    def verify_password(self, user: str, password: str) -> tuple[bool, str]:
        """用 su 校验目标用户密码，返回 (是否通过, id 命令输出/错误)。"""
        if os.name == "nt":
            return False, "当前系统不支持 su 切换"
        exit_code, output = self._su_run(user, password, "id", self.home_for(user), 20)
        ok = exit_code == 0
        return ok, output.strip()

    def _su_run(self, user: str, password: str, inner_cmd: str, cwd: str, timeout: int) -> tuple[int, str]:
        """通过 PTY 运行 `su - user -c`，在密码提示处喂入密码，返回 (exit_code, 合并输出)。"""
        import pty
        import select

        safe_cwd = shlex.quote(cwd)
        full = f"cd {safe_cwd} 2>/dev/null; {inner_cmd}"
        argv = ["su", "-", user, "-c", full]

        pid, fd = pty.fork()
        if pid == 0:  # 子进程
            try:
                os.execvp("su", argv)
            except Exception:
                os._exit(127)

        deadline = time.time() + timeout
        buf = bytearray()
        password_sent = False
        try:
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    try:
                        os.kill(pid, 9)
                    except OSError:
                        pass
                    return 124, self._strip_prompt(bytes(buf)) + "\n…(执行超时)"
                rlist, _, _ = select.select([fd], [], [], min(remaining, 0.5))
                if fd in rlist:
                    try:
                        chunk = os.read(fd, 4096)
                    except OSError:
                        break
                    if not chunk:
                        break
                    buf.extend(chunk)
                    if not password_sent and b"assword" in bytes(buf).lower():
                        # 见到 Password: 提示后送入密码
                        try:
                            os.write(fd, (password + "\n").encode())
                        except OSError:
                            pass
                        password_sent = True
                elif not password_sent and buf:
                    # 有些系统提示不含换行，select 静默时也尝试送一次密码
                    try:
                        os.write(fd, (password + "\n").encode())
                    except OSError:
                        pass
                    password_sent = True
        finally:
            _, status = os.waitpid(pid, 0)
            try:
                os.close(fd)
            except OSError:
                pass
        exit_code = os.waitstatus_to_exitcode(status)
        return exit_code, self._strip_prompt(bytes(buf))

    @staticmethod
    def _strip_prompt(raw: bytes) -> str:
        text = raw.decode("utf-8", errors="replace")
        # 去掉回显的 "Password:" 提示行
        lines = text.splitlines()
        cleaned = [ln for ln in lines if ln.strip().lower() not in {"password:", "password："}]
        if cleaned and "assword" in cleaned[0].lower():
            cleaned = cleaned[1:]
        return "\n".join(cleaned).strip("\r\n")

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
