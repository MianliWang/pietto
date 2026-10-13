from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli


def test_project_json_v2_reports_parsed_inputs_and_counters(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto", "*.pietto"))
    _write(root, "root.pietto", "shape Root:\n    id: Int\n")
    _write(root, "models/user.pietto", "shape User:\n    id: Int\n")

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 0

    document = _read_json_document(capsys)
    assert document == {
        "schema_version": 2,
        "command": "check",
        "mode": "project",
        "ok": True,
        "project": {
            "root": ".",
            "config_path": "pietto.toml",
        },
        "inputs": [
            {
                "path": "models/user.pietto",
                "kind": "source",
                "status": "parsed",
            },
            {
                "path": "root.pietto",
                "kind": "source",
                "status": "parsed",
            },
        ],
        "diagnostics": [],
        "cli_errors": [],
        "result": {
            "check": {
                "files_total": 2,
                "files_ok": 2,
                "files_with_errors": 0,
            }
        },
    }
    assert str(root) not in json.dumps(document)


def test_project_json_v2_reports_parser_diagnostics_and_error_counter(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto", "models/*.pietto"))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _write(root, "models/good.pietto", "shape Good:\n    id: Int\n")

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert document["inputs"] == [
        {
            "path": "bad.pietto",
            "kind": "source",
            "status": "error",
        },
        {
            "path": "models/good.pietto",
            "kind": "source",
            "status": "parsed",
        },
    ]
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 2,
            "files_ok": 1,
            "files_with_errors": 1,
        }
    }
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert diagnostics
    assert diagnostics[0]["code"] == "PIE-P1000"
    assert diagnostics[0]["severity"] == "error"
    assert diagnostics[0]["related_locations"] == []
    location = cast(dict[str, object], diagnostics[0]["location"])
    assert location["path"] == "bad.pietto"
    assert str(tmp_path) not in json.dumps(document)


def test_project_json_v2_keeps_read_parse_counters_for_semantic_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "semantic_error.pietto",
        "table projected:\n    from missing_relation\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert document["inputs"] == [
        {
            "path": "semantic_error.pietto",
            "kind": "source",
            "status": "parsed",
        }
    ]
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 1,
            "files_with_errors": 0,
        }
    }
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2301", "Unknown relation: missing_relation")
    ]


def test_project_json_v2_reports_source_read_errors_as_cli_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write_bytes(root, "bad.pietto", b"\xff")
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert document["inputs"] == [
        {
            "path": "bad.pietto",
            "kind": "source",
            "status": "error",
        },
        {
            "path": "good.pietto",
            "kind": "source",
            "status": "parsed",
        },
    ]
    assert document["diagnostics"] == []
    assert document["cli_errors"] == [
        {
            "kind": "source_read",
            "message": "Project source file must be valid UTF-8.",
            "path": "bad.pietto",
        }
    ]
    assert document["result"] == {
        "check": {
            "files_total": 2,
            "files_ok": 1,
            "files_with_errors": 1,
        }
    }
    assert str(tmp_path) not in json.dumps(document)


def test_project_json_v2_keeps_pre_selection_failures_empty(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "missing-config"
    root.mkdir()

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    document = _read_json_document(capsys)
    assert document["ok"] is False
    assert document["project"] == {"root": ".", "config_path": "pietto.toml"}
    assert document["inputs"] == []
    assert document["diagnostics"] == []
    assert document["result"] == {
        "check": {
            "files_total": 0,
            "files_ok": 0,
            "files_with_errors": 0,
        }
    }
    cli_errors = cast(list[dict[str, object]], document["cli_errors"])
    assert len(cli_errors) == 1
    assert cli_errors[0]["kind"] == "config_read"
    assert cli_errors[0]["path"] == "pietto.toml"


def _read_json_document(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    config_text = (
        "schema_version = 1\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(f'"{value}"' for value in values) + "]"


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _write_bytes(root: Path, relative_path: str, content: bytes) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path
