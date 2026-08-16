from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Playbook, PlaybookStep, Script


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
    scripts: list[Script] = []
    for item in SAMPLE_SCRIPTS:
        script = Script(**item, timeout_sec=60)
        db.add(script)
        scripts.append(script)
    await db.flush()
    playbook = Playbook(
        name="日常巡检",
        description="依次采集系统摘要与进程 Top，适合作为批处理模板",
        tags="inspect",
        stop_on_error=False,
    )
    db.add(playbook)
    await db.flush()
    # 通过 playbook_id 直接建行，避免在 async 会话里触发关系懒加载（MissingGreenlet）
    db.add(
        PlaybookStep(
            playbook_id=playbook.id,
            ord=0,
            name="采集系统摘要",
            kind="script",
            payload=f'{{"script_id": {scripts[0].id}}}',
            on_error="continue",
        )
    )
    db.add(
        PlaybookStep(
            playbook_id=playbook.id,
            ord=1,
            name="采集进程 Top",
            kind="script",
            payload=f'{{"script_id": {scripts[2].id}}}',
            on_error="continue",
        )
    )
    await db.commit()
