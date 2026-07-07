from __future__ import annotations

import json
from pathlib import Path
import subprocess

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationDependencyEdge,
    ProjectRelationDependencyCycle,
    ProjectRelationDependencyNode,
    ProjectRelationDependencySource,
    ProjectSemanticResult,
    ProjectSymbolKind,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import QueryDef, TableDef
from pietto.errors import Severity

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


def test_table_query_dependencies_get_deterministic_private_edges(
    tmp_path: Path,
) -> None:
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
    _write(
        root,
        "models/d_from_query.pietto",
        "table table_from_query:\n"
        "    from exported\n"
        "    select:\n"
        "        id\n"
        "query query_from_query:\n"
        "    from exported\n"
        "    select:\n"
        "        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    graph = semantic_result.model.relation_dependency_graph
    assert tuple(node.symbol.name for node in graph.nodes) == (
        "staged",
        "exported",
        "table_from_query",
        "query_from_query",
    )
    assert _edge_names(graph.edges) == (
        ("exported", "staged"),
        ("table_from_query", "exported"),
        ("query_from_query", "exported"),
    )

    staged = _derived_definition(parse_result, "staged")
    exported = _derived_definition(parse_result, "exported")
    table_from_query = _derived_definition(parse_result, "table_from_query")
    query_from_query = _derived_definition(parse_result, "query_from_query")

    assert (
        semantic_result.model.relation_resolutions[staged.from_clause].kind
        is ProjectSymbolKind.SOURCE
    )
    expected_from_clauses = {
        "exported": exported.from_clause,
        "table_from_query": table_from_query.from_clause,
        "query_from_query": query_from_query.from_clause,
    }
    for edge in graph.edges:
        assert isinstance(edge.origin, ProjectRelationDependencyNode)
        assert isinstance(edge.target, ProjectRelationDependencyNode)
        assert isinstance(edge.dependency_source, ProjectRelationDependencySource)
        assert (
            edge.dependency_source.from_clause
            is expected_from_clauses[edge.origin.symbol.name]
        )


def test_table_query_to_source_references_resolve_without_edges(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "source_target.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source raw: Row is postgres.table("raw")\n'
        "table staged:\n"
        "    from raw\n"
        "    select:\n"
        "        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert semantic_result.ok
    assert semantic_result.model is not None
    staged = _derived_definition(parse_result, "staged")
    assert (
        semantic_result.model.relation_resolutions[staged.from_clause].kind
        is ProjectSymbolKind.SOURCE
    )
    graph = semantic_result.model.relation_dependency_graph
    assert tuple(node.symbol.name for node in graph.nodes) == ("staged",)
    assert graph.edges == ()


def test_unresolved_relation_diagnostics_do_not_create_edges(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "mixed_relations.pietto",
        "shape Row:\n"
        "    id: Int\n"
        'source raw: Row is postgres.table("raw")\n'
        "table staged:\n"
        "    from raw\n"
        "    select:\n"
        "        id\n"
        "query exported:\n"
        "    from staged\n"
        "    select:\n"
        "        id\n"
        "query broken:\n"
        "    from missing_relation\n"
        "    select:\n"
        "        id\n",
    )

    parse_result, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("PIE-S2301", Severity.ERROR, "Unknown relation: missing_relation"),
    ]
    broken = _derived_definition(parse_result, "broken")
    assert broken.from_clause not in semantic_result.model.relation_resolutions
    assert _edge_names(semantic_result.model.relation_dependency_graph.edges) == (
        ("exported", "staged"),
    )


def test_cycle_shaped_dependencies_collect_edges_and_cycle_diagnostic(
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
    graph = semantic_result.model.relation_dependency_graph
    assert _edge_names(graph.edges) == (
        ("first", "second"),
        ("second", "first"),
    )
    assert len(graph.cycles) == 1
    assert isinstance(graph.cycles[0], ProjectRelationDependencyCycle)
    assert _cycle_node_names(graph.cycles[0]) == ("first", "second")
    assert _cycle_edge_names(graph.cycles[0]) == (
        ("first", "second"),
        ("second", "first"),
    )
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
    for cycle_fact in ("cycle_candidates", "cyclic_relations", "traversal_state"):
        assert not hasattr(graph, cycle_fact)


def test_project_json_v2_does_not_expose_relation_dependency_edges(
    tmp_path: Path,
) -> None:
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

    parse_result, semantic_result = _project_semantic_result(root)
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.model is not None
    assert semantic_result.model.relation_dependency_graph.edges
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is True
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


def _edge_names(
    edges: tuple[ProjectRelationDependencyEdge, ...],
) -> tuple[tuple[str, str], ...]:
    return tuple((edge.origin.symbol.name, edge.target.symbol.name) for edge in edges)


def _cycle_node_names(
    cycle: ProjectRelationDependencyCycle,
) -> tuple[str, ...]:
    return tuple(node.symbol.name for node in cycle.nodes)


def _cycle_edge_names(
    cycle: ProjectRelationDependencyCycle,
) -> tuple[tuple[str, str], ...]:
    return _edge_names(cycle.edges)


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
