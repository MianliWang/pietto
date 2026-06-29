from __future__ import annotations

import subprocess
from pathlib import Path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalized_text(path: Path) -> str:
    return " ".join(read_text(path).split())


def git_diff_name_only(repo_root: Path, paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", *paths],
        cwd=repo_root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()
