from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Script


SAMPLE_SCRIPTS = [
    {
        "name": "系统摘要",
        "description": "输出主机名、内核、磁盘与内存摘要",
        "interpreter": "/bin/bash",
        "tags": "inspect,system",
        "content": """#!/bin/bash
set -euo pipefail
echo "=== host ==="
hostnamectl 2>/dev/null || uname -a
echo
echo "=== disk ==="
df -hT | head -n 20
echo
echo "=== memory ==="
free -h
echo
echo "=== load ==="
uptime
""",
    },
    {
        "name": "清理过期日志预览",
        "description": "列出 /var/log 下超过 14 天的日志，不删除",
        "interpreter": "/bin/bash",
        "tags": "log,preview",
        "content": """#!/bin/bash
set -euo pipefail
find /var/log -type f -mtime +14 2>/dev/null | head -n 80
""",
    },
    {
        "name": "活跃进程 Top",
        "description": "按 CPU 列出前 20 个进程",
        "interpreter": "/bin/bash",
        "tags": "process",
        "content": """#!/bin/bash
set -euo pipefail
ps -eo pid,user,pcpu,pmem,comm --sort=-pcpu | head -n 21
""",
    },
]


async def seed_if_empty(db: AsyncSession) -> None:
    exists = await db.scalar(select(Script.id).limit(1))
    if exists:
        return
    for item in SAMPLE_SCRIPTS:
        db.add(Script(**item, timeout_sec=60))
    await db.commit()
