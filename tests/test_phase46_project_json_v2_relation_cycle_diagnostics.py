from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

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


def test_project_json_v2_cycle_diagnostic_envelope_and_counters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "cycle_json.pietto",
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
    )

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
        {
            "path": "cycle_json.pietto",
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
    assert len(diagnostics) == 1
    _assert_cycle_diagnostic_json(
        diagnostics[0],
        path="cycle_json.pietto",
        line=6,
        column=5,
        end_line=6,
        end_column=15,
    )
    assert str(root) not in serialized
    _assert_private_cycle_facts_absent(serialized)


def test_project_json_v2_unresolved_relation_and_cycle_diagnostics_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "a_broken.pietto",
        "query broken:\n    from missing_relation\n    select:\n        id\n",
    )
    _write(
        root,
        "b_first.pietto",
        "table first:\n    from second\n    select:\n        id\n",
    )
    _write(
        root,
        "c_second.pietto",
        "table second:\n    from first\n    select:\n        id\n",
    )

    assert cli.main(["check", "--project", root.as_posix(), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is False
    assert document["inputs"] == [
        {"path": "a_broken.pietto", "kind": "source", "status": "parsed"},
        {"path": "b_first.pietto", "kind": "source", "status": "parsed"},
        {"path": "c_second.pietto", "kind": "source", "status": "parsed"},
    ]
    assert document["result"] == {
        "check": {
            "files_total": 3,
            "files_ok": 3,
            "files_with_errors": 0,
        }
    }
    assert document["cli_errors"] == []
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2301", "Unknown relation: missing_relation"),
        ("PIE-S2302", "Relation cycle detected: first -> second -> first"),
    ]
    assert cast(dict[str, object], diagnostics[0]["location"])["path"] == (
        "a_broken.pietto"
    )
    _assert_cycle_diagnostic_json(
        diagnostics[1],
        path="c_second.pietto",
        line=2,
        column=5,
        end_line=2,
        end_column=15,
    )


def test_project_text_and_json_cycle_diagnostics_align(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    message = "Relation cycle detected: first -> second -> first"
    text_root = _cycle_project(tmp_path / "text", source_name="cycle_text.pietto")
    json_root = _cycle_project(tmp_path / "json", source_name="cycle_json.pietto")

    assert cli.main(["check", "--project", text_root.as_posix()]) == 1

    text_result = capsys.readouterr()
    assert text_result.out == ""
    assert "cycle_text.pietto:6:5 PIE-S2302 error" in text_result.err
    assert message in text_result.err

    assert (
        cli.main(["check", "--project", json_root.as_posix(), "--format", "json"]) == 1
    )

    document = _read_json_document(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [
        (diagnostic["code"], diagnostic["message"]) for diagnostic in diagnostics
    ] == [("PIE-S2302", message)]


def test_package_version_is_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject


def _assert_cycle_diagnostic_json(
    diagnostic: dict[str, object],
    *,
    path: str,
    line: int,
    column: int,
    end_line: int,
    end_column: int,
) -> None:
    assert diagnostic["code"] == "PIE-S2302"
    assert diagnostic["severity"] == "error"
    assert diagnostic["message"] == "Relation cycle detected: first -> second -> first"
    assert diagnostic["location"] == {
        "path": path,
        "line": line,
        "column": column,
        "end_line": end_line,
        "end_column": end_column,
    }
    assert diagnostic["suggestion"] is None
    assert diagnostic["related_locations"] == []


def _assert_private_cycle_facts_absent(serialized: str) -> None:
    for private_fact in (
        "ProjectRelationDependencyGraph",
        "ProjectRelationDependencyNode",
        "ProjectRelationDependencyEdge",
        "ProjectRelationDependencySource",
        "ProjectRelationDependencyCycle",
        "relation_dependency_graph",
        "cycles",
        "nodes",
        "edges",
        "origin",
        "target",
        "dependency_source",
    ):
        assert private_fact not in serialized


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
