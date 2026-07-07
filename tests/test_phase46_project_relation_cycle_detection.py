from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
import json
from pathlib import Path
import subprocess
from typing import cast

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationDependencyCycle,
    ProjectRelationDependencyEdge,
    ProjectRelationDependencyGraph,
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


def test_project_relation_dependency_cycle_carrier_and_default_graph() -> None:
    assert is_dataclass(ProjectRelationDependencyCycle)
    assert hasattr(ProjectRelationDependencyCycle, "__slots__")

    cycle = ProjectRelationDependencyCycle(nodes=(), edges=())
    assert not hasattr(cycle, "__dict__")
    assert cycle.nodes == ()
    assert cycle.edges == ()
    with pytest.raises(FrozenInstanceError):
        setattr(cycle, "nodes", ())

    graph = ProjectRelationDependencyGraph()
    assert graph.nodes == ()
    assert graph.edges == ()
    assert graph.cycles == ()


def test_acyclic_project_has_no_private_cycles(tmp_path: Path) -> None:
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
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    graph = semantic_result.model.relation_dependency_graph
    assert _edge_names(graph.edges) == (("exported", "staged"),)
    assert graph.cycles == ()


def test_self_cycle_creates_one_private_cycle_fact(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "self_cycle.pietto",
        "table loop:\n    from loop\n    select:\n        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    graph = semantic_result.model.relation_dependency_graph
    assert _edge_names(graph.edges) == (("loop", "loop"),)
    assert _cycle_node_names(graph.cycles) == (("loop",),)
    assert _cycle_edge_names(graph.cycles) == ((("loop", "loop"),),)
    assert _cycle_diagnostic_messages(semantic_result) == (
        "Relation cycle detected: loop -> loop",
    )


def test_two_node_cycle_creates_canonical_private_cycle_fact(
    tmp_path: Path,
) -> None:
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    graph = semantic_result.model.relation_dependency_graph
    assert _cycle_node_names(graph.cycles) == (("first", "second"),)
    assert _cycle_edge_names(graph.cycles) == (
        (("first", "second"), ("second", "first")),
    )
    assert _cycle_diagnostic_messages(semantic_result) == (
        "Relation cycle detected: first -> second -> first",
    )


def test_three_node_cycle_keeps_edges_in_forward_cycle_order(
    tmp_path: Path,
) -> None:
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

    assert not semantic_result.ok
    assert semantic_result.model is not None
    graph = semantic_result.model.relation_dependency_graph
    assert _cycle_node_names(graph.cycles) == (("first", "second", "third"),)
    assert _cycle_edge_names(graph.cycles) == (
        (("first", "second"), ("second", "third"), ("third", "first")),
    )
    assert _cycle_diagnostic_messages(semantic_result) == (
        "Relation cycle detected: first -> second -> third -> first",
    )


def test_disjoint_cycles_are_ordered_by_canonical_node_order(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "disjoint_cycles.pietto",
        "table alpha:\n"
        "    from beta\n"
        "    select:\n"
        "        id\n"
        "table beta:\n"
        "    from alpha\n"
        "    select:\n"
        "        id\n"
        "table gamma:\n"
        "    from delta\n"
        "    select:\n"
        "        id\n"
        "table delta:\n"
        "    from gamma\n"
        "    select:\n"
        "        id\n",
    )

    _, semantic_result = _project_semantic_result(root)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    graph = semantic_result.model.relation_dependency_graph
    assert _cycle_node_names(graph.cycles) == (
        ("alpha", "beta"),
        ("gamma", "delta"),
    )
    assert _cycle_edge_names(graph.cycles) == (
        (("alpha", "beta"), ("beta", "alpha")),
        (("gamma", "delta"), ("delta", "gamma")),
    )
    assert _cycle_diagnostic_messages(semantic_result) == (
        "Relation cycle detected: alpha -> beta -> alpha",
        "Relation cycle detected: gamma -> delta -> gamma",
    )


def test_source_targets_and_unresolved_targets_do_not_create_cycles(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "mixed_targets.pietto",
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
    staged = _derived_definition(parse_result, "staged")
    broken = _derived_definition(parse_result, "broken")
    assert (
        semantic_result.model.relation_resolutions[staged.from_clause].kind
        is ProjectSymbolKind.SOURCE
    )
    assert broken.from_clause not in semantic_result.model.relation_resolutions
    graph = semantic_result.model.relation_dependency_graph
    assert _edge_names(graph.edges) == (("exported", "staged"),)
    assert graph.cycles == ()


def test_project_json_v2_does_not_expose_relation_cycle_facts(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "cycle_private.pietto",
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
    serialized = json.dumps(document)

    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_dependency_graph.cycles
    assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS
    assert document["ok"] is False
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2302"]
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
    cycles: tuple[ProjectRelationDependencyCycle, ...],
) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(node.symbol.name for node in cycle.nodes) for cycle in cycles)


def _cycle_edge_names(
    cycles: tuple[ProjectRelationDependencyCycle, ...],
) -> tuple[tuple[tuple[str, str], ...], ...]:
    return tuple(_edge_names(cycle.edges) for cycle in cycles)


def _cycle_diagnostic_messages(
    semantic_result: ProjectSemanticResult,
) -> tuple[str, ...]:
    return tuple(
        diagnostic.message
        for diagnostic in semantic_result.diagnostics
        if diagnostic.code == "PIE-S2302"
    )


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
