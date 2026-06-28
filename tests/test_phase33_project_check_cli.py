from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

import pietto.cli as cli


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


def test_project_check_json_is_deferred_and_not_json_v1(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path)

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "project JSON output is deferred" in captured.err
    assert "JSON v2 Serializer MVP" in captured.err
    with pytest.raises(json.JSONDecodeError):
        json.loads(captured.err)


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
