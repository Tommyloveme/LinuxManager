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
    ModuleSpec("overview", "运行概览", "主机资源、负载与网络实时摘要", "/system", "monitor", "grid"),
    ModuleSpec("monitor", "进程与服务", "进程资源排序、systemd 单元治理，支持实时刷新", "/process", "monitor", "activity"),
    ModuleSpec("identity", "执行身份", "选择并验证 Linux 用户，作为后续操作的执行者", "/users", "operate", "user"),
    ModuleSpec("scripts", "脚本中心", "脚本编辑、保存与单次/批量执行", "/scripts", "operate", "code"),
    ModuleSpec("files", "文件管理", "浏览、过滤、预览、上传与批量下载/打包", "/files", "operate", "folder"),
    ModuleSpec("terminal", "远程终端", "浏览器内交互式终端，实时显示当前目录", "/terminal", "operate", "terminal"),
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
