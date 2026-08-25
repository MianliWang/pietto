from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts" / "package_smoke.py"

_RELATION_SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
    "table active_users:\n"
    "    from users\n"
    "    where active == true\n"
    "    select:\n"
    "        id\n"
    "        email\n"
)


def test_project_check_text_and_json_success_remain_compatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root_with_source(tmp_path)
    _forbid_project_compiler_pipeline(monkeypatch)

    assert cli.main(["check", "--project", str(root)]) == 0
    text_result = capsys.readouterr()
    assert text_result.out == "Project check OK: .\nFiles checked: 1\n"
    assert text_result.err == ""
    assert str(root) not in text_result.out

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 0
    document = _read_json_document(capsys)
    assert tuple(document) == (
        "schema_version",
        "command",
        "mode",
        "ok",
        "project",
        "inputs",
        "diagnostics",
        "cli_errors",
        "result",
    )
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
            }
        ],
        "diagnostics": [],
        "cli_errors": [],
        "result": {
            "check": {
                "files_total": 1,
                "files_ok": 1,
                "files_with_errors": 0,
            }
        },
    }
    assert str(root) not in json.dumps(document)


def test_project_check_json_parser_diagnostics_do_not_enter_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(
        tmp_path / "project",
        include=("*.pietto", "models/*.pietto"),
    )
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _write(root, "models/good.pietto", "shape Good:\n    id: Int\n")
    _forbid_project_compiler_pipeline(monkeypatch)

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
    assert diagnostics[0]["related_locations"] == []
    location = cast(dict[str, object], diagnostics[0]["location"])
    assert location["path"] == "bad.pietto"
    assert str(root) not in json.dumps(document)


def test_project_check_json_source_read_and_config_errors_stay_cli_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path / "read-error", include=("*.pietto",))
    _write_bytes(root, "bad.pietto", b"\xff")
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")
    _forbid_project_compiler_pipeline(monkeypatch)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    read_error_document = _read_json_document(capsys)
    assert read_error_document["inputs"] == [
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
    assert read_error_document["diagnostics"] == []
    assert read_error_document["cli_errors"] == [
        {
            "kind": "source_read",
            "message": "Project source file must be valid UTF-8.",
            "path": "bad.pietto",
        }
    ]
    assert read_error_document["result"] == {
        "check": {
            "files_total": 2,
            "files_ok": 1,
            "files_with_errors": 1,
        }
    }

    schema_root = _project_root(
        tmp_path / "schema-error",
        config_text="schema_version = 1\n\n[sources]\ninclude = []\n",
    )
    assert cli.main(["check", "--project", str(schema_root), "--format", "json"]) == 2

    schema_error_document = _read_json_document(capsys)
    assert schema_error_document["project"] == {
        "root": ".",
        "config_path": "pietto.toml",
    }
    assert schema_error_document["inputs"] == []
    assert schema_error_document["diagnostics"] == []
    assert schema_error_document["result"] == {
        "check": {
            "files_total": 0,
            "files_ok": 0,
            "files_with_errors": 0,
        }
    }
    cli_errors = cast(list[dict[str, object]], schema_error_document["cli_errors"])
    assert len(cli_errors) == 1
    assert cli_errors[0]["kind"] == "config_schema"
    assert cli_errors[0]["path"] == "pietto.toml"
    assert str(tmp_path) not in json.dumps(schema_error_document)


def test_single_file_json_v1_and_artifact_v1_surfaces_remain_separate(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    check_source = _write(
        tmp_path,
        "valid.pietto",
        "shape User:\n    email: Text not null\n",
    )
    relation_source = _write(tmp_path, "active_users.pietto", _RELATION_SOURCE)

    assert cli.main(["check", str(check_source), "--format", "json"]) == 0
    check_document = _read_json_document(capsys)
    assert check_document["schema_version"] == 1
    assert check_document["command"] == "check"
    assert "mode" not in check_document

    assert (
        cli.main(
            [
                "emit-sql",
                str(relation_source),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )
    emit_document = _read_json_document(capsys)
    assert emit_document["schema_version"] == 1
    assert emit_document["command"] == "emit-sql"
    assert "mode" not in emit_document

    assert cli.main(["explain", str(relation_source), "--format", "json"]) == 0
    explain_document = _read_json_document(capsys)
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert explain_document["command"] == "explain"
    assert "mode" not in explain_document


def test_project_flag_remains_rejected_by_emit_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path / "project")

    assert cli.main(["emit-sql", "--project", str(root)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: pietto" in captured.err


def test_installed_package_smoke_locks_project_text_and_json_success() -> None:
    source = PACKAGE_SMOKE_PATH.read_text(encoding="utf-8")

    for required in (
        '"installed CLI project check text"',
        '"installed CLI project check JSON v2"',
        '("check", "--project", project_root.as_posix())',
        '("check", "--project", project_root.as_posix(), "--format", "json")',
        "Project check OK: .",
        "Files checked: 1",
        '"schema_version": 2',
        '"mode": "project"',
        '"path": "models/user.pietto"',
        '"kind": "source"',
        '"status": "parsed"',
        '"files_total": 1',
        '"files_ok": 1',
        '"files_with_errors": 0',
        "installed CLI project check text wrote unexpected stderr",
        "installed CLI project check JSON v2 wrote unexpected stderr",
    ):
        assert required in source, required


def _forbid_project_compiler_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project check must not enter compiler output pipelines")

    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
    monkeypatch.setattr(cli.mysql_backend, "emit_mysql_sql", unexpected_call)
    monkeypatch.setattr(cli, "build_semantic_metadata_artifact", unexpected_call)
    monkeypatch.setattr(cli, "semantic_metadata_artifact_to_json_dict", unexpected_call)
    monkeypatch.setattr(cli, "render_semantic_metadata_text", unexpected_call)


def _read_json_document(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _project_root(
    path: Path,
    *,
    include: tuple[str, ...] = ("models/*.pietto",),
    config_text: str | None = None,
) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if config_text is None:
        config_text = (
            f"schema_version = 1\n\n[sources]\ninclude = {_toml_array(include)}\n"
        )
    (path / "pietto.toml").write_text(config_text, encoding="utf-8")
    return path


def _project_root_with_source(path: Path) -> Path:
    root = _project_root(path / "project")
    _write(root, "models/user.pietto", "shape User:\n    id: Int\n")
    return root


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _write_bytes(root: Path, relative_path: str, source: bytes) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(source)
    return path


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"
