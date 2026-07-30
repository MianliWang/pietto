from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import cast

import pytest

import pietto.cli as cli
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto.errors import Diagnostic, Severity
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

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

ALLOWED_SLICE5_GATE2_PATHS = {
    "src/pietto/_project/model.py",
    "tests/test_phase45_project_relation_namespace_semantics.py",
    "tests/test_phase46_project_relation_dependency_graph_scaffold.py",
    "tests/test_phase46_project_relation_dependency_edge_collection.py",
    "tests/test_phase46_project_relation_cycle_detection.py",
    "tests/test_phase46_project_relation_cycle_diagnostics.py",
}


def test_acyclic_project_emits_no_relation_cycle_diagnostic(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/a_source.pietto",
        'shape Row:\n    id: Int\nsource raw: Row is postgres.table("raw")\n',
    )
    _write(
        root,
        "models/b_table.pietto",
        "table staged:\n    from raw\n    select:\n        id\n",
    )
    _write(
        root,
        "models/c_query.pietto",
        "query exported:\n    from staged\n    select:\n        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert _cycle_diagnostics(semantic_result) == ()


def test_self_cycle_emits_one_deterministic_diagnostic(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "self_cycle.pietto",
        "table loop:\n    from loop\n    select:\n        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in _cycle_diagnostics(semantic_result)
    ] == [
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: loop -> loop",
        )
    ]


def test_two_node_cycle_uses_closing_edge_location(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "two_node_cycle.pietto",
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    diagnostics = _cycle_diagnostics(semantic_result)
    assert not semantic_result.ok
    assert [(diagnostic.code, diagnostic.message) for diagnostic in diagnostics] == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]
    assert diagnostics[0].location.path == "two_node_cycle.pietto"
    assert diagnostics[0].location.line == 6
    assert diagnostics[0].location.column == 5


def test_three_node_cycle_emits_canonical_path(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "three_node_cycle.pietto",
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "query second:\n"
        "    from third\n"
        "    select:\n"
        "        id\n"
        "table third:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in _cycle_diagnostics(semantic_result)
    ] == [
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: first -> second -> third -> first",
        )
    ]


def test_source_target_and_unresolved_only_projects_emit_no_cycle_diagnostic(
    tmp_path: Path,
) -> None:
    source_root = _project_root(tmp_path / "source_target", include=("*.pietto",))
    _write(
        source_root,
        "source_target.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source raw: Row is postgres.table("raw")\n'
        "table staged:\n"
        "    from raw\n"
        "    select:\n"
        "        id\n",
    )

    _, source_semantic_result = _project_semantic_result(source_root)
    assert source_semantic_result.ok
    assert _cycle_diagnostics(source_semantic_result) == ()

    unresolved_root = _project_root(tmp_path / "unresolved", include=("*.pietto",))
    _write(
        unresolved_root,
        "unresolved.pietto",
        "table broken:\n    from missing_relation\n    select:\n        id\n",
    )

    _, unresolved_semantic_result = _project_semantic_result(unresolved_root)
    assert not unresolved_semantic_result.ok
    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in unresolved_semantic_result.diagnostics
    ] == [("PIE-S2301", "Unknown relation: missing_relation")]
    assert _cycle_diagnostics(unresolved_semantic_result) == ()


def test_unresolved_relation_diagnostic_precedes_separate_cycle(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "mixed_diagnostics.pietto",
        "query broken:\n"
        "    from missing_relation\n"
        "    select:\n"
        "        id\n"
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("PIE-S2301", "Unknown relation: missing_relation"),
        ("PIE-S2302", "Relation cycle detected: first -> second -> first"),
    ]


def test_project_text_check_reports_relation_cycle_diagnostic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_output_pipelines(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "cycle_text.pietto",
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
    )

    assert cli.main(["check", "--project", str(root)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "cycle_text.pietto:6:5 PIE-S2302 error" in captured.err
    assert "Relation cycle detected: first -> second -> first" in captured.err


def test_project_json_v2_reports_cycle_diagnostic_without_private_facts(
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

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1

    document = _read_json_document(capsys)
    serialized = json.dumps(document)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is False
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2302", "Relation cycle detected: first -> second -> first")
    ]
    assert diagnostics[0]["location"] == {
        "path": "cycle_json.pietto",
        "line": 6,
        "column": 5,
        "end_line": 6,
        "end_column": 15,
    }
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


def test_project_json_v2_top_level_shape_remains_unchanged(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "cycle_shape.pietto",
        "table first:\n"
        "    from second\n"
        "    select:\n"
        "        id\n"
        "table second:\n"
        "    from first\n"
        "    select:\n"
        "        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )

    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is False


def test_phase46_slice5_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert (_git_status_paths().issubset(ALLOWED_SLICE5_GATE2_PATHS)) or _slice5_gate2()


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _cycle_diagnostics(
    semantic_result: ProjectSemanticResult,
) -> tuple[Diagnostic, ...]:
    return tuple(
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.code == "PIE-S2302"
    )


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
