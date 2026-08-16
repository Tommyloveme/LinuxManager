from __future__ import annotations

import os
import platform
import socket
from datetime import datetime, timezone
from pathlib import Path

import psutil

from app.adapters.executor import LinuxExecutor
from app.core.config import get_settings
from app.core.module_registry import list_modules
from app.modules.process.service import ProcessService


class SystemService:
    def __init__(self) -> None:
        self.executor = LinuxExecutor()
        self.processes = ProcessService()

    def overview(self) -> dict:
        info = self.processes.top_summary()
        uname = platform.uname()
        nets = []
        for name, addrs in psutil.net_if_addrs().items():
            ipv4 = [a.address for a in addrs if a.family == socket.AF_INET]
            if ipv4:
                nets.append({"iface": name, "ipv4": ipv4})
        return {
            "host": uname.node,
            "os": f"{uname.system} {uname.release}",
            "kernel": uname.version,
            "arch": uname.machine,
            "python": platform.python_version(),
            "now": datetime.now(timezone.utc).isoformat(),
            "resources": info,
            "networks": nets[:12],
            "app": {
                "name": get_settings().app_name,
                "version": get_settings().app_version,
                "modules": list_modules(),
            },
        }

    async def hostnamectl(self) -> str:
        if Path("/usr/bin/hostnamectl").exists():
            result = await self.executor.run(["hostnamectl"])
            return result.stdout
        return platform.platform()


class ServiceManager:
    """systemd unit helper with graceful fallback."""

    def __init__(self) -> None:
        self.executor = LinuxExecutor()

    async def list_units(self, query: str = "") -> list[dict]:
        if not Path("/usr/bin/systemctl").exists():
            return []
        result = await self.executor.run(
            ["systemctl", "list-units", "--type=service", "--all", "--no-pager", "--no-legend"],
            timeout=30,
        )
        units = []
        q = query.lower()
        for line in result.stdout.splitlines():
            parts = line.split(None, 4)
            if len(parts) < 4:
                continue
            name, load, active, sub = parts[0], parts[1], parts[2], parts[3]
            desc = parts[4] if len(parts) > 4 else ""
            if q and q not in name.lower() and q not in desc.lower():
                continue
            units.append({"name": name, "load": load, "active": active, "sub": sub, "description": desc})
        return units[:300]

    async def control(self, unit: str, action: str) -> str:
        if action not in {"start", "stop", "restart", "reload", "status", "enable", "disable"}:
            raise ValueError(f"不支持的动作: {action}")
        if not Path("/usr/bin/systemctl").exists():
            return "当前系统没有 systemctl"
        argv = ["systemctl", action, "--no-pager", unit]
        result = await self.executor.run(argv, timeout=60)
        text = (result.stdout or "") + (result.stderr or "")
        if result.exit_code != 0 and action != "status":
            raise RuntimeError(text.strip() or f"systemctl {action} 失败")
        return text[-6000:]

    def os_release(self) -> dict:
        data: dict[str, str] = {}
        path = Path("/etc/os-release")
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    data[key] = value.strip().strip('"')
        data.setdefault("PRETTY_NAME", platform.platform())
        data["SUSE"] = "suse" in data.get("ID", "").lower() or "suse" in data.get("PRETTY_NAME", "").lower()
        data["cwd"] = os.getcwd()
        return data
