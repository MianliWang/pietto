"""Write a schema_version 2 project and read its `check --project` JSON diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import pietto.cli as cli


def _check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], files: dict[str, str]
) -> list[tuple[str, str, int, int, str]]:
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
    )
    for name, text in files.items():
        (root / name).write_text(text)
    code = cli.main(["check", "--project", str(root), "--format", "json"])
    diagnostics = json.loads(capsys.readouterr().out)["diagnostics"]
    assert code == (1 if diagnostics else 0)
    return [
        (
            item["code"],
            item["location"]["path"],
            item["location"]["line"],
            item["location"]["column"],
            item["message"],
        )
        for item in diagnostics
    ]
