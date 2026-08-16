from __future__ import annotations

import os
import signal
from datetime import datetime

import psutil

from app.core.exceptions import CedarError, NotFoundError


class ProcessService:
    def list_processes(self, query: str = "", limit: int = 400) -> list[dict]:
        items: list[dict] = []
        q = (query or "").lower()
        for proc in psutil.process_iter(["pid", "name", "username", "cpu_percent", "memory_info", "status", "cmdline", "create_time"]):
            try:
                info = proc.info
                name = info.get("name") or ""
                cmdline = " ".join(info.get("cmdline") or [])[:400]
                if q and q not in name.lower() and q not in cmdline.lower() and q not in str(info.get("username") or "").lower():
                    continue
                mem = info.get("memory_info")
                items.append(
                    {
                        "pid": info["pid"],
                        "name": name,
                        "user": info.get("username") or "",
                        "cpu": info.get("cpu_percent") or 0.0,
                        "rss": mem.rss if mem else 0,
                        "status": info.get("status") or "",
                        "cmdline": cmdline,
                        "started": datetime.fromtimestamp(info.get("create_time") or 0).isoformat(),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if len(items) >= limit:
                break
        items.sort(key=lambda row: row["cpu"], reverse=True)
        return items

    def get(self, pid: int) -> dict:
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess as exc:
            raise NotFoundError(f"进程不存在: {pid}") from exc
        with proc.oneshot():
            mem = proc.memory_info()
            return {
                "pid": proc.pid,
                "name": proc.name(),
                "user": proc.username(),
                "cpu": proc.cpu_percent(interval=0.05),
                "rss": mem.rss,
                "vms": mem.vms,
                "status": proc.status(),
                "cmdline": " ".join(proc.cmdline())[:800],
                "cwd": _safe_cwd(proc),
                "exe": _safe_exe(proc),
                "num_threads": proc.num_threads(),
                "started": datetime.fromtimestamp(proc.create_time()).isoformat(),
            }

    def kill(self, pid: int, sig: str = "TERM") -> None:
        mapping = {
            "TERM": signal.SIGTERM,
            "KILL": signal.SIGKILL if hasattr(signal, "SIGKILL") else signal.SIGTERM,
            "INT": signal.SIGINT,
            "HUP": signal.SIGHUP if hasattr(signal, "SIGHUP") else signal.SIGTERM,
        }
        signum = mapping.get(sig.upper())
        if signum is None:
            raise CedarError(f"不支持的信号: {sig}")
        if pid == os.getpid():
            raise CedarError("拒绝终止 Cedar 自身进程")
        try:
            proc = psutil.Process(pid)
            proc.send_signal(signum)
        except psutil.NoSuchProcess as exc:
            raise NotFoundError(f"进程不存在: {pid}") from exc
        except psutil.AccessDenied as exc:
            raise CedarError("权限不足，无法向该进程发信号") from exc

    def top_summary(self) -> dict:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.15),
            "cpu_count": psutil.cpu_count() or 1,
            "loadavg": _loadavg(),
            "memory": {"total": vm.total, "used": vm.used, "percent": vm.percent, "available": vm.available},
            "swap": {"total": swap.total, "used": swap.used, "percent": swap.percent},
            "disk": {"total": disk.total, "used": disk.used, "percent": disk.percent, "free": disk.free},
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            "process_count": len(psutil.pids()),
        }


def _safe_cwd(proc: psutil.Process) -> str:
    try:
        return proc.cwd()
    except (psutil.AccessDenied, psutil.Error):
        return ""


def _safe_exe(proc: psutil.Process) -> str:
    try:
        return proc.exe()
    except (psutil.AccessDenied, psutil.Error):
        return ""


def _loadavg() -> list[float]:
    try:
        return [round(x, 2) for x in os.getloadavg()]
    except (AttributeError, OSError):
        return [0.0, 0.0, 0.0]
