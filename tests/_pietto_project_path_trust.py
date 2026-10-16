"""Shared fakes for the private trusted-read primitives in pietto._project.path_trust.

They let Linux CI drive the path-based open fallback that native Windows always
uses, report Windows reparse points to os.lstat, and give os.fstat the Windows
CPython descriptor ctime meaning.  Every fake is installed through the caller's
monkeypatch and wraps the os function captured when this module was imported.
"""

from __future__ import annotations

import os
from pathlib import Path
import stat
import time
from types import SimpleNamespace
from typing import Any

import pytest

import pietto._project.path_trust as path_trust

JUNCTION_TAG = 0xA000_0003
LX_SYMLINK_TAG = 0xA000_001D
CLOUD_FILE_TAG = 0x9000_601A

_os_open = os.open
_os_lstat = os.lstat
_os_fstat = os.fstat


def report_reparse_point(
    monkeypatch: pytest.MonkeyPatch,
    path: Path,
    reparse_tag: int = JUNCTION_TAG,
) -> None:
    """Make os.lstat report ``path`` with a Windows reparse tag, as Windows does."""

    reported = os.fspath(path)

    def lstat(target: Any, *args: Any, **kwargs: Any) -> Any:
        result = _os_lstat(target, *args, **kwargs)
        if os.fspath(target) != reported:
            return result
        facts = {
            name: getattr(result, name)
            for name in dir(result)
            if name.startswith("st_")
        }
        return SimpleNamespace(**{**facts, "st_reparse_tag": reparse_tag})

    monkeypatch.setattr(os, "lstat", lstat)


def mutate_before_fallback_open(
    monkeypatch: pytest.MonkeyPatch,
    target: Path,
    mutation: str,
) -> list[bool]:
    """Pin the path-based open fallback and mutate ``target`` just before it opens.

    The parent mutations expect ``target`` two levels below the project root and
    move its parent directory beside the root, outside it.
    """

    canonical = os.fspath(target.resolve())
    fired: list[bool] = []

    def racing_open(
        path: str | os.PathLike[str],
        flags: int,
        mode: int = 0o777,
        *,
        dir_fd: int | None = None,
    ) -> int:
        if not fired and dir_fd is None and os.fspath(path) == canonical:
            fired.append(True)
            _mutate(target, mutation)
        return _os_open(path, flags, mode, dir_fd=dir_fd)

    monkeypatch.setattr(path_trust, "_supports_directory_relative_open", lambda: False)
    monkeypatch.setattr(os, "open", racing_open)
    return fired


def later_descriptor_ctime(
    monkeypatch: pytest.MonkeyPatch,
    only: tuple[int, int] | None = None,
) -> None:
    """Report os.fstat st_ctime 1 ms later than the path-based stat, as on Windows.

    ``only`` restricts the skew to one (st_dev, st_ino) file.
    """

    def later_ctime(file_descriptor: int) -> os.stat_result:
        result = _os_fstat(file_descriptor)
        if only is not None and (result.st_dev, result.st_ino) != only:
            return result
        hidden = {
            name: getattr(result, name)
            for name in dir(result)
            if name.startswith("st_") and name not in os.stat_result.__match_args__
        }
        hidden["st_ctime_ns"] += 1_000_000
        return os.stat_result(tuple(result), hidden)

    monkeypatch.setattr(os, "fstat", later_ctime)


def _mutate(target: Path, mutation: str) -> None:
    if mutation == "replace":
        staged = target.with_name(target.name + ".new")
        staged.write_bytes(target.read_bytes())
        os.replace(staged, target)
    elif mutation == "size":
        with target.open("ab") as handle:
            handle.write(b"\n")
    elif mutation == "mtime":
        before = target.stat()
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
    elif mutation == "chmod":
        # Only st_ctime changes; retry until the coarse kernel clock has ticked.
        before = target.stat()
        mode = stat.S_IMODE(before.st_mode)
        deadline = time.monotonic() + 5
        while target.stat().st_ctime_ns == before.st_ctime_ns:
            assert time.monotonic() < deadline, "st_ctime did not change"
            mode ^= stat.S_IXUSR
            os.chmod(target, mode)
    elif mutation == "parent-link":
        parent = target.parent
        moved = parent.parent.parent / (parent.name + "-moved")
        os.rename(parent, moved)
        os.symlink(moved, parent, target_is_directory=True)
    elif mutation == "parent-dir":
        parent = target.parent
        moved = parent.parent.parent / (parent.name + "-moved")
        os.rename(parent, moved)
        parent.mkdir()
        os.link(moved / target.name, target)
    elif mutation != "none":
        raise ValueError(f"unknown mutation {mutation!r}")
