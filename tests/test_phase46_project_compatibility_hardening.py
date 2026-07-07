from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import cast

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PROJECT_JSON_V2_PATH = REPO_ROOT / "src/pietto/_project/json_v2.py"
PROJECT_CHECK_PATH = REPO_ROOT / "src/pietto/_project/check.py"
CLI_PATH = REPO_ROOT / "src/pietto/cli.py"

PROJECT_JSON_TOP_LEVEL_KEYS = (
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

ALLOWED_SLICE7_GATE2_PATHS = {
    "tests/test_phase46_project_compatibility_hardening.py",
}

VALID_RELATION_SOURCE = (
    "shape User:\n"
    "    id: Int not null\n"
    "    email: Text not null\n"
    'source users: User is postgres.table("users")\n'
    "table active_users:\n"
    "    from users\n"
    "    select:\n"
    "        id\n"
)


@pytest.mark.parametrize("json_mode", (False, True))
def test_project_cycle_check_does_not_enter_single_file_output_pipelines(
    json_mode: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _cycle_project(tmp_path, source_name="cycle_project.pietto")
    arguments = ["check", "--project", root.as_posix()]
    if json_mode:
        arguments.extend(("--format", "json"))

    assert cli.main(arguments) == 1

    if json_mode:
        document = _read_json_document(capsys)
        diagnostics = cast(list[dict[str, object]], document["diagnostics"])
        assert [(item["code"], item["message"]) for item in diagnostics] == [
            ("PIE-S2302", "Relation cycle detected: first -> second -> first")
        ]
        return

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "cycle_project.pietto:6:5 PIE-S2302 error" in captured.err
    assert "Relation cycle detected: first -> second -> first" in captured.err
    assert "Project check OK" not in captured.out
    assert "Files checked" not in captured.out


def test_single_file_surfaces_remain_separate_from_project_cycle_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_semantic_builder(monkeypatch)
    check_source = _write(
        tmp_path,
        "shape_only.pietto",
        "shape Row:\n    id: Int not null\n",
    )
    relation_source = _write(tmp_path, "relation.pietto", VALID_RELATION_SOURCE)

    assert cli.main(["check", check_source.as_posix()]) == 0
    text_check = capsys.readouterr()
    assert text_check.out == f"OK: {check_source}\n"
    assert text_check.err == ""

    assert cli.main(["check", check_source.as_posix(), "--format", "json"]) == 0
    check_document = _read_json_document(capsys)
    assert check_document["schema_version"] == 1
    assert check_document["command"] == "check"
    assert "mode" not in check_document

    assert (
        cli.main(["emit-sql", relation_source.as_posix(), "--dialect", "postgres"]) == 0
    )
    emit_result = capsys.readouterr()
    assert "SELECT" in emit_result.out
    assert "PIE-S2302" not in emit_result.out
    assert emit_result.err == ""

    assert cli.main(["explain", relation_source.as_posix(), "--format", "json"]) == 0
    explain_document = _read_json_document(capsys)
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert explain_document["command"] == "explain"
    assert "mode" not in explain_document


@pytest.mark.parametrize("command", ("emit-sql", "explain"))
def test_project_emit_sql_and_explain_remain_rejected_without_cycle_leakage(
    command: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _cycle_project(tmp_path, source_name="cycle_project.pietto")

    assert cli.main([command, "--project", root.as_posix()]) != 0

    captured = capsys.readouterr()
    combined_output = f"{captured.out}\n{captured.err}"
    assert "SELECT" not in captured.out
    assert "Semantic Metadata Artifact" not in captured.out
    assert "Project check OK" not in captured.out
    assert "PIE-S2302" not in combined_output
    _assert_private_cycle_facts_absent(combined_output)


def test_project_json_v2_cycle_output_shape_and_private_facts_are_locked(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _cycle_project(tmp_path, source_name="cycle_json.pietto")

    assert cli.main(["check", "--project", root.as_posix(), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    serialized = json.dumps(document)

    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["schema_version"] == 2
    assert document["command"] == "check"
    assert document["mode"] == "project"
    assert document["ok"] is False
    assert document["inputs"] == [
        {"path": "cycle_json.pietto", "kind": "source", "status": "parsed"}
    ]
    assert document["cli_errors"] == []
    assert document["result"] == {
        "check": {
            "files_total": 1,
            "files_ok": 1,
            "files_with_errors": 0,
        }
    }
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]
    assert diagnostics[0]["severity"] == "error"
    assert diagnostics[0]["suggestion"] is None
    assert diagnostics[0]["related_locations"] == []
    assert cast(dict[str, object], diagnostics[0]["location"]) == {
        "path": "cycle_json.pietto",
        "line": 6,
        "column": 5,
        "end_line": 6,
        "end_column": 15,
    }
    assert str(root) not in serialized
    _assert_private_cycle_facts_absent(serialized)


def test_public_project_paths_do_not_serialize_private_cycle_internals() -> None:
    public_surface_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PROJECT_JSON_V2_PATH, PROJECT_CHECK_PATH, CLI_PATH)
    )

    _assert_private_cycle_facts_absent(public_surface_source)


def test_phase46_slice7_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_status_paths().issubset(ALLOWED_SLICE7_GATE2_PATHS)


def _forbid_project_output_pipelines(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _forbid_project_semantic_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_builder(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("single-file surfaces must not build project semantics")

    monkeypatch.setattr(cli, "build_empty_project_semantic_result", unexpected_builder)


def _read_json_document(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _cycle_project(path: Path, *, source_name: str) -> Path:
    root = _project_root(path, include=("*.pietto",))
    _write(
        root,
        source_name,
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
    )
    return root


def _project_root(
    path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = path / "project"
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


def _assert_private_cycle_facts_absent(text: str) -> None:
    for private_fact in (
        "relation_dependency_graph",
        "ProjectRelationDependencyGraph",
        "ProjectRelationDependencyCycle",
        "cycles",
        "nodes",
        "edges",
        "origin",
        "target",
        "dependency_source",
    ):
        assert private_fact not in text


def _git_status_paths() -> set[str]:
    result = subprocess.run(
        ["git", "status", "--short"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return paths
