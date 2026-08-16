"""Module registry — the extension point for new capabilities.

To add a feature:
1. Implement a service under app/modules/<name>/
2. Expose HTTP routes under app/api/v1/
3. Append a ModuleSpec here so the UI and docs can discover it
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleSpec:
    key: str
    title: str
    description: str
    api_prefix: str
    nav_group: str
    icon: str


MODULES: tuple[ModuleSpec, ...] = (
    ModuleSpec("overview", "总览", "主机资源与健康摘要", "/system", "observe", "grid"),
    ModuleSpec("identity", "Linux 用户", "查看系统用户并切换执行身份", "/users", "operate", "user"),
    ModuleSpec("scripts", "脚本", "脚本库、单次与批量执行", "/scripts", "operate", "code"),
    ModuleSpec("playbooks", "批处理", "把多步操作打包成可复用流程", "/playbooks", "operate", "layers"),
    ModuleSpec("files", "文件", "浏览、正则打包、目录同步", "/files", "operate", "folder"),
    ModuleSpec("process", "进程", "进程查看、终止与资源排序", "/process", "operate", "activity"),
    ModuleSpec("services", "服务", "systemd 单元启停与状态", "/services", "operate", "cpu"),
    ModuleSpec("terminal", "终端", "浏览器内 PTY，显示当前目录", "/terminal", "operate", "terminal"),
    ModuleSpec("jobs", "作业", "后台长任务进度与产物", "/jobs", "observe", "clock"),
    ModuleSpec("audit", "审计", "敏感操作留痕", "/audit", "observe", "shield"),
)


def list_modules() -> list[dict[str, str]]:
    return [
        {
            "key": m.key,
            "title": m.title,
            "description": m.description,
            "api_prefix": m.api_prefix,
            "nav_group": m.nav_group,
            "icon": m.icon,
        }
        for m in MODULES
    ]
