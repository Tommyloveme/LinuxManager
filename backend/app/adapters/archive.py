from __future__ import annotations

import asyncio
import os
import re
import shutil
import tarfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import CedarError


@dataclass
class ArchiveResult:
    archive_path: str
    file_count: int
    total_bytes: int


class ArchiveAdapter:
    def __init__(self) -> None:
        self.settings = get_settings()

    def collect_files(
        self,
        sources: list[str],
        include: str | None,
        exclude: str | None,
    ) -> list[Path]:
        include_re = re.compile(include) if include else None
        exclude_re = re.compile(exclude) if exclude else None
        collected: list[Path] = []
        for raw in sources:
            root = Path(raw).expanduser().resolve()
            if not root.exists():
                raise CedarError(f"路径不存在: {root}")
            if root.is_file():
                rel = str(root)
                if self._match(rel, include_re, exclude_re):
                    collected.append(root)
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                rel = str(path.relative_to(root))
                if self._match(rel, include_re, exclude_re) or self._match(str(path), include_re, exclude_re):
                    collected.append(path)
        return collected

    async def create_archive(
        self,
        sources: list[str],
        *,
        include: str | None,
        exclude: str | None,
        fmt: str,
        output_name: str,
    ) -> ArchiveResult:
        files = await asyncio.to_thread(self.collect_files, sources, include, exclude)
        if not files:
            raise CedarError("没有匹配到任何文件，请检查路径与正则")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", output_name).strip("_") or "archive"
        dest_dir = self.settings.archive_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        def _pack() -> ArchiveResult:
            total = 0
            if fmt == "zip":
                dest = dest_dir / f"{safe_name}.zip"
                with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for file in files:
                        zf.write(file, arcname=self._arcname(file, sources))
                        total += file.stat().st_size
            else:
                dest = dest_dir / f"{safe_name}.tar.gz"
                with tarfile.open(dest, "w:gz") as tf:
                    for file in files:
                        tf.add(file, arcname=self._arcname(file, sources))
                        total += file.stat().st_size
            return ArchiveResult(str(dest), len(files), total)

        return await asyncio.to_thread(_pack)

    async def sync_dirs(
        self,
        mappings: list[dict[str, str]],
        *,
        include: str | None,
        exclude: str | None,
        delete_extra: bool = False,
    ) -> dict:
        include_re = re.compile(include) if include else None
        exclude_re = re.compile(exclude) if exclude else None
        copied = 0
        skipped = 0
        deleted = 0

        def _sync() -> dict:
            nonlocal copied, skipped, deleted
            for item in mappings:
                src = Path(item["src"]).expanduser().resolve()
                dst = Path(item["dst"]).expanduser().resolve()
                if not src.exists():
                    raise CedarError(f"源路径不存在: {src}")
                dst.mkdir(parents=True, exist_ok=True)
                if src.is_file():
                    if self._match(src.name, include_re, exclude_re):
                        shutil.copy2(src, dst / src.name)
                        copied += 1
                    else:
                        skipped += 1
                    continue
                seen: set[Path] = set()
                for file in src.rglob("*"):
                    if not file.is_file():
                        continue
                    rel = file.relative_to(src)
                    if not self._match(str(rel).replace("\\", "/"), include_re, exclude_re):
                        skipped += 1
                        continue
                    target = dst / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, target)
                    seen.add(target)
                    copied += 1
                if delete_extra:
                    for existing in dst.rglob("*"):
                        if existing.is_file() and existing not in seen:
                            existing.unlink()
                            deleted += 1
            return {"copied": copied, "skipped": skipped, "deleted": deleted}

        return await asyncio.to_thread(_sync)

    def _match(self, rel: str, include_re: re.Pattern[str] | None, exclude_re: re.Pattern[str] | None) -> bool:
        normalized = rel.replace("\\", "/")
        if exclude_re and exclude_re.search(normalized):
            return False
        if include_re:
            return bool(include_re.search(normalized))
        return True

    def _arcname(self, file: Path, sources: list[str]) -> str:
        for raw in sources:
            root = Path(raw).expanduser().resolve()
            try:
                rel = file.relative_to(root if root.is_dir() else root.parent)
                return str(Path(root.name if root.is_dir() else root.parent.name) / rel).replace("\\", "/")
            except ValueError:
                continue
        return file.name
