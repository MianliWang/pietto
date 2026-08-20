from __future__ import annotations

import json
from pathlib import Path

import pytest

import pietto.cli as cli
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectDiscoveryErrorKind,
    ProjectInput,
    ProjectParseCheckResult,
    ProjectRoot,
)
from pietto.ast_nodes import Script

REPO_ROOT = Path(__file__).resolve().parents[1]

_TOP_LEVEL_KEYS = (
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


def test_project_parse_check_result_parsed_inputs_defaults_empty() -> None:
    result = ProjectParseCheckResult(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        errors=(),
        diagnostics=(),
    )

    assert result.parsed_inputs == ()


def test_project_check_retains_parsed_inputs_in_selected_order(
    tmp_path: Path,
) -> None:
    root = _project_root(
        tmp_path,
        include=("models/*.pietto", "*.pietto"),
        exclude=("models/tmp/*.pietto",),
    )
    _write(root, "root.pietto", "shape Root:\n    id: Int\n")
    _write(root, "models/z.pietto", "shape Zed:\n    id: Int\n")
    _write(root, "models/a.pietto", "shape Alpha:\n    id: Int\n")
    _write(root, "models/tmp/skip.pietto", "not parsed\n")

    result = check_project_parse_only(root)

    expected_inputs = (
        ProjectInput(path="models/a.pietto", status="parsed"),
        ProjectInput(path="models/z.pietto", status="parsed"),
        ProjectInput(path="root.pietto", status="parsed"),
    )
    assert result.ok
    assert result.errors == ()
    assert result.diagnostics == ()
    assert result.inputs == expected_inputs
    assert tuple(parsed.path for parsed in result.parsed_inputs) == tuple(
        item.path for item in expected_inputs
    )
    for parsed_input in result.parsed_inputs:
        assert not Path(parsed_input.path).is_absolute()
        assert isinstance(parsed_input.script, Script)
        assert parsed_input.script.span.path == parsed_input.path
        assert parsed_input.script.definitions
        assert parsed_input.script.definitions[0].span.path == parsed_input.path
        assert str(root) not in repr(parsed_input.script.span)


def test_parser_errors_are_project_relative_and_excluded_from_parsed_inputs(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto", "models/*.pietto"))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _write(root, "models/good.pietto", "shape Good:\n    id: Int\n")

    result = check_project_parse_only(root)

    assert not result.ok
    assert result.errors == ()
    assert result.inputs == (
        ProjectInput(path="bad.pietto", status="error"),
        ProjectInput(path="models/good.pietto", status="parsed"),
    )
    assert tuple(parsed.path for parsed in result.parsed_inputs) == (
        "models/good.pietto",
    )
    assert result.parsed_inputs[0].script.span.path == "models/good.pietto"
    assert result.diagnostics
    assert {diagnostic.location.path for diagnostic in result.diagnostics} == {
        "bad.pietto"
    }
    assert str(root) not in " ".join(str(item) for item in result.diagnostics)


def test_source_read_failures_are_excluded_from_parsed_inputs(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write_bytes(root, "bad.pietto", b"\xff")
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")

    result = check_project_parse_only(root)

    assert not result.ok
    assert result.inputs == (
        ProjectInput(path="bad.pietto", status="error"),
        ProjectInput(path="good.pietto", status="parsed"),
    )
    assert [(error.kind, error.path) for error in result.errors] == [
        (ProjectDiscoveryErrorKind.SOURCE_READ, "bad.pietto")
    ]
    assert tuple(parsed.path for parsed in result.parsed_inputs) == ("good.pietto",)
    assert result.parsed_inputs[0].script.span.path == "good.pietto"
    assert result.diagnostics == ()


def test_project_json_v2_does_not_expose_private_parsed_inputs(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto", "*.pietto"))
    _write(root, "root.pietto", "shape Root:\n    id: Int\n")
    _write(root, "models/user.pietto", "shape User:\n    id: Int\n")

    result = check_project_parse_only(root)
    assert len(result.parsed_inputs) == 2

    document = project_check_result_to_json_dict(result)
    assert tuple(document) == _TOP_LEVEL_KEYS
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
    serialized = json.dumps(document)
    assert "parsed_inputs" not in serialized
    assert "script" not in serialized
    assert str(root) not in serialized


def test_project_text_output_remains_unchanged_and_stops_before_compiler(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_compiler_pipeline(monkeypatch)
    root = _project_root(tmp_path / "success", include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""

    error_root = _project_root(tmp_path / "parser-error", include=("*.pietto",))
    _write(error_root, "bad.pietto", "shape Broken\n    id: Int\n")

    assert cli.main(["check", "--project", str(error_root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "bad.pietto:" in captured.err
    assert str(error_root) not in captured.err


@pytest.mark.parametrize("command", ["emit-sql", "explain"])
def test_project_emit_sql_and_explain_paths_remain_rejected(
    command: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))

    assert cli.main([command, "--project", str(root)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: pietto" in captured.err


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
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


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
