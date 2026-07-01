from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

import _static_audit_helpers as helpers
from _static_audit_helpers import (
    git_diff_name_only,
    normalized_text,
    read_text,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_read_text_reads_utf8_text_exactly(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    text = "alpha\n  beta café\n"
    path.write_text(text, encoding="utf-8")

    assert read_text(path) == text


def test_normalized_text_matches_split_join_semantics(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    text = " alpha\n\tbeta   gamma \n"
    path.write_text(text, encoding="utf-8")

    assert normalized_text(path) == " ".join(text.split())


def test_git_diff_name_only_returns_empty_output_for_clean_surface() -> None:
    assert git_diff_name_only(REPO_ROOT, ("grammar/Pietto.g4",)) in {
        "",
        "grammar/Pietto.g4",
    }


def test_git_diff_name_only_asserts_empty_stderr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["git", "diff"],
            returncode=0,
            stdout="",
            stderr="unexpected stderr",
        )

    monkeypatch.setattr(helpers.subprocess, "run", fake_run)

    with pytest.raises(AssertionError):
        git_diff_name_only(REPO_ROOT, ("grammar/Pietto.g4",))


def test_git_diff_name_only_uses_only_requested_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[tuple[object, ...], dict[str, Any]]] = []

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(
            args=["git", "diff"],
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(helpers.subprocess, "run", fake_run)

    assert git_diff_name_only(REPO_ROOT, ("README.md", "AGENTS.md")) == ""

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args == (
        [
            "git",
            "diff",
            "--name-only",
            "--",
            "README.md",
            "AGENTS.md",
        ],
    )
    assert kwargs["cwd"] == REPO_ROOT
    assert kwargs["check"] is True
    assert kwargs["text"] is True
    assert kwargs["stdout"] is subprocess.PIPE
    assert kwargs["stderr"] is subprocess.PIPE
