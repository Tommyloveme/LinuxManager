from __future__ import annotations

import inspect
from pathlib import Path

from app.adapters.archive import ArchiveAdapter
from app.modules.files.service import FileService


def test_archive_method_not_shadowed() -> None:
    """回归：实例属性不得遮蔽 FileService.archive 方法。"""
    svc = FileService()
    assert inspect.iscoroutinefunction(svc.archive)
    assert inspect.iscoroutinefunction(svc.sync)


def test_regex_include_exclude(tmp_path: Path) -> None:
    (tmp_path / "a.log").write_text("1")
    (tmp_path / "b.txt").write_text("2")
    (tmp_path / "c.log.gz").write_text("3")
    files = ArchiveAdapter().collect_files([str(tmp_path)], r".*\.log$", r".*\.gz$")
    names = {p.name for p in files}
    assert names == {"a.log"}


def test_path_rejects_dotdot() -> None:
    svc = FileService()
    try:
        svc._safe("../etc/passwd")  # noqa: SLF001
        raise AssertionError("should reject")
    except Exception as exc:
        assert ".." in str(exc) or "不允许" in str(exc)
