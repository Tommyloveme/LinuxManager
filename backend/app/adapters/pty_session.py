from __future__ import annotations

import asyncio
import os
import struct
from typing import Callable

from app.core.logging import get_logger

logger = get_logger()

# 每次出提示符前通过 OSC 0 上报 “user@host:cwd”，前端据此实时显示当前目录
PROMPT_REPORT = 'printf "\\033]0;%s@%s:%s\\007" "$USER" "${HOSTNAME%%.*}" "$PWD"'


class PtySession:
    """Linux PTY session. Windows falls back to a piped shell."""

    def __init__(self, *, linux_user: str | None, cwd: str, cols: int = 120, rows: int = 32) -> None:
        self.linux_user = linux_user
        self.cwd = cwd
        self.cols = cols
        self.rows = rows
        self.pid: int | None = None
        self.fd: int | None = None
        self.process: asyncio.subprocess.Process | None = None
        self._reader: asyncio.Task | None = None
        self.on_data: Callable[[bytes], None] | None = None
        self.alive = False

    async def start(self) -> None:
        os.makedirs(self.cwd, exist_ok=True)
        if os.name == "posix":
            await self._start_pty()
        else:
            await self._start_pipe()
        self.alive = True

    async def _start_pty(self) -> None:
        import fcntl
        import pty
        import termios

        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(self.cwd)
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["PS1"] = "\\u@\\h:\\w\\$ "
            env["PROMPT_COMMAND"] = PROMPT_REPORT
            shell = env.get("SHELL", "/bin/bash")
            switch_user = bool(self.linux_user and self.linux_user != env.get("USER"))
            if switch_user:
                os.execvpe("sudo", ["sudo", "-u", self.linux_user, "-H", "-i", shell], env)
            os.execvpe(shell, [shell, "-i"], env)
        self.pid = pid
        self.fd = fd
        # sudo -i 会重置环境变量；root 部署下 sudo 不会询问密码，可安全注入 PROMPT_COMMAND
        if self.linux_user and os.geteuid() == 0:
            injection = f" export PROMPT_COMMAND='{PROMPT_REPORT}'\n".encode()
            asyncio.get_running_loop().call_later(0.8, self._inject, injection)
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        self._set_winsize(self.cols, self.rows)
        loop = asyncio.get_running_loop()
        loop.add_reader(fd, self._on_fd_readable)
        # keep termios imported for platforms that need it later
        _ = termios

    def _inject(self, data: bytes) -> None:
        if self.fd is None or not self.alive:
            return
        try:
            os.write(self.fd, data)
        except OSError:
            pass

    def _on_fd_readable(self) -> None:
        if self.fd is None:
            return
        try:
            data = os.read(self.fd, 4096)
        except OSError:
            data = b""
        if not data:
            self.alive = False
            return
        if self.on_data:
            self.on_data(data)

    async def _start_pipe(self) -> None:
        shell = os.environ.get("COMSPEC", "cmd.exe")
        self.process = await asyncio.create_subprocess_exec(
            shell,
            cwd=self.cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        self._reader = asyncio.create_task(self._pump_pipe())

    async def _pump_pipe(self) -> None:
        assert self.process and self.process.stdout
        while True:
            chunk = await self.process.stdout.read(4096)
            if not chunk:
                self.alive = False
                break
            if self.on_data:
                self.on_data(chunk)

    async def write(self, data: bytes) -> None:
        if self.fd is not None:
            await asyncio.to_thread(os.write, self.fd, data)
            return
        if self.process and self.process.stdin:
            self.process.stdin.write(data)
            await self.process.stdin.drain()

    def resize(self, cols: int, rows: int) -> None:
        self.cols, self.rows = cols, rows
        self._set_winsize(cols, rows)

    def _set_winsize(self, cols: int, rows: int) -> None:
        if self.fd is None:
            return
        try:
            import fcntl
            import termios

            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.fd, termios.TIOCSWINSZ, winsize)
        except Exception:
            logger.debug("winsize not applied", exc_info=True)

    async def close(self) -> None:
        self.alive = False
        loop = asyncio.get_running_loop()
        if self.fd is not None:
            try:
                loop.remove_reader(self.fd)
            except Exception:
                pass
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
        if self.pid:
            try:
                os.kill(self.pid, 15)
            except OSError:
                pass
            self.pid = None
        if self.process:
            self.process.kill()
            await self.process.wait()
            self.process = None
        if self._reader:
            self._reader.cancel()
