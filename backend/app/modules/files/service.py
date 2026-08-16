from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from app.adapters.archive import ArchiveAdapter
from app.core.exceptions import CedarError, ForbiddenError


class FileService:
    def __init__(self) -> None:
        # 命名为 archiver，避免实例属性遮蔽下方的 archive 方法
        self.archiver = ArchiveAdapter()

    def _safe(self, raw: str) -> Path:
        path = Path(raw).expanduser()
        resolved = path.resolve()
        # Reject obvious traversal when the client sent relative junk
        if ".." in Path(raw).parts:
            raise ForbiddenError("不允许使用 .. 访问上级目录")
        return resolved

    def list_dir(self, path: str) -> dict:
        target = self._safe(path or str(Path.home()))
        if not target.exists():
            raise CedarError(f"路径不存在: {target}", 404)
        if target.is_file():
            stat = target.stat()
            return {
                "path": str(target),
                "is_dir": False,
                "entries": [],
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        entries = []
        try:
            children = list(target.iterdir())
        except PermissionError as exc:
            raise ForbiddenError(f"没有权限读取: {target}") from exc
        for child in sorted(children, key=lambda p: (not p.is_dir(), p.name.lower())):
            try:
                stat = child.stat()
                entries.append(
                    {
                        "name": child.name,
                        "path": str(child),
                        "is_dir": child.is_dir(),
                        "size": 0 if child.is_dir() else stat.st_size,
                        "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "mode": oct(stat.st_mode & 0o777),
                    }
                )
            except OSError:
                continue
        return {
            "path": str(target),
            "is_dir": True,
            "parent": str(target.parent),
            "entries": entries,
        }

    def read_text(self, path: str, max_bytes: int = 256_000) -> dict:
        target = self._safe(path)
        if not target.is_file():
            raise CedarError("不是文件")
        data = target.read_bytes()[:max_bytes]
        return {
            "path": str(target),
            "truncated": target.stat().st_size > max_bytes,
            "content": data.decode("utf-8", errors="replace"),
        }

    def write_text(self, path: str, content: str) -> dict:
        target = self._safe(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": str(target), "size": target.stat().st_size}

    def mkdir(self, path: str) -> dict:
        target = self._safe(path)
        target.mkdir(parents=True, exist_ok=True)
        return {"path": str(target)}

    def remove(self, path: str) -> None:
        target = self._safe(path)
        if target.is_dir():
            try:
                target.rmdir()
            except OSError as exc:
                raise CedarError("目录非空，拒绝删除") from exc
        else:
            target.unlink()

    async def archive(self, body: dict) -> dict:
        result = await self.archiver.create_archive(
            body.get("sources") or [],
            include=body.get("include"),
            exclude=body.get("exclude"),
            fmt=body.get("format") or "tar.gz",
            output_name=body.get("output_name") or "bundle",
        )
        return {
            "archive_path": result.archive_path,
            "file_count": result.file_count,
            "total_bytes": result.total_bytes,
            "filename": os.path.basename(result.archive_path),
        }

    async def sync(self, body: dict) -> dict:
        return await self.archiver.sync_dirs(
            body.get("mappings") or [],
            include=body.get("include"),
            exclude=body.get("exclude"),
            delete_extra=bool(body.get("delete_extra")),
        )
