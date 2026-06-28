from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli

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


def test_project_check_valid_root_config_is_text_only_and_pipeline_free(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, config_text="not valid = [")
    _forbid_project_pipeline(monkeypatch)

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 0\n"
    assert captured.err == ""
    assert str(root) not in captured.out


def test_project_check_explicit_text_format_matches_default(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path)

    assert cli.main(["check", "--project", str(root), "--format", "text"]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 0\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("root_name", "make_root", "expected_kind"),
    [
        ("missing", lambda path: path / "missing", "project_root"),
        ("file-root", lambda path: _write(path, "file-root", ""), "project_root"),
        ("missing-config", lambda path: path, "config_read"),
        (
            "directory-config",
            lambda path: _root_with_config_directory(path),
            "config_read",
        ),
    ],
)
def test_project_check_root_and_config_errors_are_project_relative(
    root_name: str,
    make_root: Callable[[Path], Path],
    expected_kind: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del root_name
    root = make_root(tmp_path)
    _forbid_project_pipeline(monkeypatch)

    assert cli.main(["check", "--project", str(root)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"project error: {expected_kind}:" in captured.err
    assert str(tmp_path) not in captured.err
    if expected_kind == "config_read":
        assert "(path: pietto.toml)" in captured.err


@pytest.mark.parametrize(
    "format_args",
    [
        ["--format", "json"],
        ["--format=json"],
    ],
)
def test_project_check_json_success_emits_json_v2_stdout_only(
    format_args: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, config_text="not valid = [")
    _forbid_project_pipeline(monkeypatch)

    assert cli.main(["check", "--project", str(root), *format_args]) == 0

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
        "inputs": [],
        "diagnostics": [],
        "cli_errors": [],
        "result": {
            "check": {
                "files_total": 0,
                "files_ok": 0,
                "files_with_errors": 0,
            }
        },
    }
    assert str(root) not in json.dumps(document)


@pytest.mark.parametrize(
    ("root_name", "make_root", "expected_kind", "expected_path", "expected_project"),
    [
        (
            "missing",
            lambda path: path / "missing",
            "project_root",
            None,
            {"root": None, "config_path": None},
        ),
        (
            "file-root",
            lambda path: _write(path, "file-root", ""),
            "project_root",
            None,
            {"root": None, "config_path": None},
        ),
        (
            "missing-config",
            lambda path: path,
            "config_read",
            "pietto.toml",
            {"root": ".", "config_path": "pietto.toml"},
        ),
        (
            "directory-config",
            lambda path: _root_with_config_directory(path),
            "config_read",
            "pietto.toml",
            {"root": ".", "config_path": "pietto.toml"},
        ),
    ],
)
def test_project_check_json_root_and_config_errors_are_json_v2(
    root_name: str,
    make_root: Callable[[Path], Path],
    expected_kind: str,
    expected_path: str | None,
    expected_project: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del root_name
    root = make_root(tmp_path)
    _forbid_project_pipeline(monkeypatch)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    document = _read_json_document(capsys)
    assert document["schema_version"] == 2
    assert document["command"] == "check"
    assert document["mode"] == "project"
    assert document["ok"] is False
    assert document["project"] == expected_project
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
    assert cli_errors[0]["kind"] == expected_kind
    assert isinstance(cli_errors[0]["message"], str)
    assert cli_errors[0]["message"]
    assert cli_errors[0]["path"] == expected_path
    assert str(tmp_path) not in json.dumps(document)


def test_project_check_rejects_path_and_project_together(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write(tmp_path, "input.pietto", "")
    root = _project_root(tmp_path / "project")

    assert cli.main(["check", str(source_path), "--project", str(root)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "path and --project are mutually exclusive" in captured.err


def test_project_check_still_requires_single_file_or_project(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["check"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "the following arguments are required: path" in captured.err


@pytest.mark.parametrize("command", ["emit-sql", "explain"])
def test_project_flag_is_not_accepted_by_emit_sql_or_explain(
    command: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path)

    assert cli.main([command, "--project", str(root)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: pietto" in captured.err


def test_single_file_check_text_and_json_v1_remain_available(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write(
        tmp_path,
        "valid.pietto",
        "shape User:\n    email: Text not null\n",
    )

    assert cli.main(["check", str(source_path)]) == 0
    text_result = capsys.readouterr()
    assert text_result.out == f"OK: {source_path}\n"
    assert text_result.err == ""

    assert cli.main(["check", str(source_path), "--format", "json"]) == 0
    json_result = capsys.readouterr()
    document = json.loads(json_result.out)
    assert json_result.err == ""
    assert document["schema_version"] == 1
    assert document["command"] == "check"
    assert document["path"] == str(source_path)
    assert "mode" not in document


def test_single_file_emit_sql_json_v1_and_explain_artifact_v1_remain_available(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write(tmp_path, "active_users.pietto", _RELATION_SOURCE)

    assert (
        cli.main(
            [
                "emit-sql",
                str(source_path),
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
    assert "artifacts" in emit_document
    assert "mode" not in emit_document

    assert cli.main(["explain", str(source_path), "--format", "json"]) == 0
    explain_document = _read_json_document(capsys)
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert explain_document["command"] == "explain"
    assert "metadata" in explain_document
    assert "mode" not in explain_document


def _forbid_project_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project check must not enter the compiler pipeline")

    monkeypatch.setattr(cli.parser_api, "parse_file", unexpected_call)
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


def _project_root(path: Path, *, config_text: str = "") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "pietto.toml").write_text(config_text, encoding="utf-8")
    return path


def _root_with_config_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "pietto.toml").mkdir()
    return path


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
