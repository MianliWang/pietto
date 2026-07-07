from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
import json
from pathlib import Path
import subprocess

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectParseCheckResult,
    ProjectRelationDependencyEdge,
    ProjectRelationDependencyGraph,
    ProjectRelationDependencyNode,
    ProjectRelationDependencySource,
    ProjectRoot,
    ProjectSemanticCatalog,
    ProjectSemanticModel,
    ProjectSemanticResult,
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, TableDef
from pietto.errors import Severity

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE5_GATE2_PATHS = {
    "src/pietto/_project/model.py",
    "tests/test_phase45_project_relation_namespace_semantics.py",
    "tests/test_phase46_project_relation_dependency_graph_scaffold.py",
    "tests/test_phase46_project_relation_dependency_edge_collection.py",
    "tests/test_phase46_project_relation_cycle_detection.py",
    "tests/test_phase46_project_relation_cycle_diagnostics.py",
}


def test_project_relation_dependency_carriers_are_frozen_slots_dataclasses() -> None:
    for model_type in (
        ProjectRelationDependencyNode,
        ProjectRelationDependencySource,
        ProjectRelationDependencyEdge,
        ProjectRelationDependencyGraph,
    ):
        assert is_dataclass(model_type)
        assert hasattr(model_type, "__slots__")

    graph = ProjectRelationDependencyGraph()
    assert not hasattr(graph, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(graph, "edges", ())


def test_project_semantic_model_defaults_to_empty_dependency_graph() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )

    assert model.relation_dependency_graph == ProjectRelationDependencyGraph()
    assert model.relation_dependency_graph.nodes == ()
    assert model.relation_dependency_graph.edges == ()
    assert model.relation_dependency_graph.cycles == ()


def test_relation_dependency_graph_nodes_are_table_query_only_and_ordered(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(root, "models/a_shape.pietto", "shape Row:\n    id: Int\n")
    _write(
        root,
        "models/b_source.pietto",
        'source rows: Row is postgres.table("rows")\n',
    )
    _write(
        root,
        "models/c_table.pietto",
        "table projected:\n    from rows\n    select:\n        id\n",
    )
    _write(
        root,
        "models/d_query.pietto",
        "query exported:\n    from projected\n    select:\n        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    graph = semantic_result.model.relation_dependency_graph
    assert tuple(node.symbol.name for node in graph.nodes) == ("projected", "exported")
    assert tuple(node.symbol.kind for node in graph.nodes) == (
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    )
    assert "rows" not in {node.symbol.name for node in graph.nodes}
    assert "rows" not in {edge.target.symbol.name for edge in graph.edges}

    projected = _derived_definition(parse_result, "projected")
    exported = _derived_definition(parse_result, "exported")
    assert semantic_result.model.relation_resolutions[projected.from_clause].name == (
        "rows"
    )
    assert semantic_result.model.relation_resolutions[exported.from_clause].name == (
        "projected"
    )


def test_cycle_project_emits_relation_cycle_diagnostic(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "cycle_deferred.pietto",
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    node_names = tuple(
        node.symbol.name
        for node in semantic_result.model.relation_dependency_graph.nodes
    )
    assert node_names == ("first", "second")
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [
        (
            "PIE-S2302",
            Severity.ERROR,
            "Relation cycle detected: first -> second -> first",
        ),
    ]


def test_project_json_v2_does_not_expose_relation_dependency_graph(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "good.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source rows: Row is postgres.table("rows")\n'
        "table projected:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)
    document = project_check_result_to_json_dict(parse_result)
    serialized = json.dumps(document)

    assert semantic_result.model is not None
    assert semantic_result.model.relation_dependency_graph.nodes
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
    assert document["ok"] is True
    for private_fact in (
        "ProjectRelationDependencyGraph",
        "ProjectRelationDependencyNode",
        "relation_dependency_graph",
        "nodes",
        "edges",
        "ProjectSymbol",
        "catalog",
    ):
        assert private_fact not in serialized


def test_phase46_slice5_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_status_paths().issubset(ALLOWED_SLICE5_GATE2_PATHS)


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _derived_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (TableDef, QueryDef)) and definition.name == name:
                return definition
    raise AssertionError(f"Derived relation not found: {name}")


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
