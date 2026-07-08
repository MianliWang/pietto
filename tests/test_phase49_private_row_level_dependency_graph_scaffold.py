from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass
import json
from pathlib import Path
import subprocess
import tomllib

import pytest

from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRowFieldProvenanceKind,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.row_dependency_graph import (
    ProjectRelationRowDependencyGraph,
    ProjectRowDependencyEdge,
    ProjectRowDependencyEdgeKind,
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
)
from pietto.ast_nodes import QueryDef, TableDef

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE9_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-private-row-level-dependency-graph-scaffold-v1.md",
    "src/pietto/_project/model.py",
    "src/pietto/_project/row_dependency_graph.py",
    "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
}

ALLOWED_SLICE10_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-minimal-private-lineage-carrier-source-direct-rename-v1.md",
    "src/pietto/_project/model.py",
    "src/pietto/_project/row_lineage.py",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
}

ALLOWED_SLICE11_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-computed-let-multi-hop-row-lineage-v1.md",
    "src/pietto/_project/row_lineage.py",
    "tests/test_phase49_computed_let_multi_hop_row_lineage.py",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase49_private_row_level_dependency_graph_scaffold.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
}

FORBIDDEN_FILES = (
    "src/pietto/_project/json_v2.py",
    "src/pietto/_project/check.py",
    "src/pietto/_project/let_scope_facts.py",
    "src/pietto/_project/row_expression_schema.py",
    "src/pietto/_project/row_expression_type_facts.py",
    "src/pietto/semantic/let_bindings.py",
)

PRIVATE_JSON_FACTS = (
    "relation_row_dependency_graphs",
    "ProjectRelationRowDependencyGraph",
    "ProjectRowDependencyGraphStatus",
    "ProjectRowDependencyGraphReason",
    "ProjectRowDependencyNode",
    "ProjectRowDependencyEdge",
    "output_field",
    "upstream_field",
    "let_binding",
    "computed_expression",
    "let_output",
    "let_expression",
    "dependency",
    "lineage",
    "relation_row_schemas",
    "relation_let_scope_facts",
    "ProjectRowSchema",
    "ProjectRowField",
    "provenance",
)


def test_row_dependency_graph_carriers_are_private_frozen_dataclasses() -> None:
    for model_type in (
        ProjectRowDependencyNode,
        ProjectRowDependencyEdge,
        ProjectRelationRowDependencyGraph,
    ):
        assert is_dataclass(model_type)
        assert hasattr(model_type, "__slots__")

    node = ProjectRowDependencyNode(
        kind=ProjectRowDependencyNodeKind.OUTPUT_FIELD,
        name="id",
        relation_name="projected",
        output_name="id",
    )
    graph = ProjectRelationRowDependencyGraph(
        status=ProjectRowDependencyGraphStatus.CONCRETE,
        reason=ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE,
        nodes=(node,),
    )

    assert graph.nodes == (node,)
    assert not hasattr(graph, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(graph, "nodes", ())


def test_direct_renamed_and_computed_output_dependencies_are_recorded(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "        user_email = email\n"
            "        normalized = lower(status)\n"
            "        total = score + bonus\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    graph = semantic_result.model.relation_row_dependency_graphs[projected]
    projected_schema = semantic_result.model.relation_row_schemas[projected]

    assert graph.status is ProjectRowDependencyGraphStatus.CONCRETE
    assert graph.reason is ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE
    assert (
        projected_schema.fields["total"].provenance is not None
        and projected_schema.fields["total"].provenance.kind
        is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    )
    assert _edge_values(graph, ProjectRowDependencyEdgeKind.DIRECT_PROJECTION) == (
        ("id", "users.id"),
    )
    assert _edge_values(graph, ProjectRowDependencyEdgeKind.RENAMED_PROJECTION) == (
        ("user_email", "users.email"),
    )
    assert _edge_values(graph, ProjectRowDependencyEdgeKind.COMPUTED_EXPRESSION) == (
        ("normalized", "users.status"),
        ("total", "users.score"),
        ("total", "users.bonus"),
    )
    assert "lower" not in {node.name for node in graph.nodes}


def test_selected_let_outputs_and_let_expression_dependencies_are_recorded(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "        label = lower(status)\n"
            "        adjusted = total + score\n"
            "    select:\n"
            "        total\n"
            "        exported = adjusted\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    projected = _derived_definition(parse_result, "projected")
    graph = semantic_result.model.relation_row_dependency_graphs[projected]
    projected_schema = semantic_result.model.relation_row_schemas[projected]

    for output_name in ("total", "exported"):
        field = projected_schema.fields[output_name]
        assert field.field_def is None
        assert field.provenance is not None
        assert field.provenance.kind is ProjectRowFieldProvenanceKind.LET_DERIVED

    assert _edge_values(graph, ProjectRowDependencyEdgeKind.LET_OUTPUT) == (
        ("total", "total"),
        ("exported", "adjusted"),
    )
    assert _edge_values(graph, ProjectRowDependencyEdgeKind.LET_EXPRESSION) == (
        ("total", "users.score"),
        ("total", "users.bonus"),
        ("label", "users.status"),
        ("adjusted", "total"),
        ("adjusted", "users.score"),
    )
    assert "lower" not in {node.name for node in graph.nodes}


def test_multi_hop_dependency_remains_immediate_upstream_only(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query seed:\n"
            "    from users\n"
            "    select:\n"
            "        total = score + bonus\n"
            "query exported:\n"
            "    from seed\n"
            "    select:\n"
            "        total\n",
        )
    )

    assert semantic_result.ok
    assert semantic_result.model is not None
    exported = _derived_definition(parse_result, "exported")
    graph = semantic_result.model.relation_row_dependency_graphs[exported]

    assert _edge_values(graph, ProjectRowDependencyEdgeKind.DIRECT_PROJECTION) == (
        ("total", "seed.total"),
    )
    assert "users.score" not in {node.name for node in graph.nodes}
    assert "users.bonus" not in {node.name for node in graph.nodes}


def test_non_concrete_row_schema_states_produce_non_concrete_graphs(
    tmp_path: Path,
) -> None:
    unknown_parse, unknown_semantic = _project_semantic_result(
        _project(
            tmp_path / "unknown",
            "query broken:\n    from users\n    select:\n        missing\n",
        )
    )
    grouped_parse, grouped_semantic = _project_semantic_result(
        _project(
            tmp_path / "grouped",
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(score)\n",
        )
    )
    cycle_parse, cycle_semantic = _project_semantic_result(
        _project(
            tmp_path / "cycle",
            "query first:\n"
            "    from second\n"
            "    select:\n"
            "        id\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        id\n",
            include_source=False,
        )
    )

    assert unknown_semantic.model is not None
    broken = _derived_definition(unknown_parse, "broken")
    broken_graph = unknown_semantic.model.relation_row_dependency_graphs[broken]
    assert broken_graph.status is ProjectRowDependencyGraphStatus.UNKNOWN
    assert broken_graph.reason is ProjectRowDependencyGraphReason.UNKNOWN_SCHEMA
    assert broken_graph.nodes == ()
    assert broken_graph.edges == ()

    assert grouped_semantic.model is not None
    grouped = _derived_definition(grouped_parse, "grouped")
    grouped_graph = grouped_semantic.model.relation_row_dependency_graphs[grouped]
    assert grouped_graph.status is ProjectRowDependencyGraphStatus.DEFERRED
    assert (
        grouped_graph.reason
        is ProjectRowDependencyGraphReason.DEFERRED_PHASE48_BEHAVIOR
    )

    assert cycle_semantic.model is not None
    first = _derived_definition(cycle_parse, "first")
    first_graph = cycle_semantic.model.relation_row_dependency_graphs[first]
    assert first_graph.status is ProjectRowDependencyGraphStatus.BLOCKED
    assert first_graph.reason is ProjectRowDependencyGraphReason.CYCLE_BLOCKED


def test_project_json_v2_keeps_row_dependency_graph_private(tmp_path: Path) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query projected:\n"
            "    from users\n"
            "    let:\n"
            "        total = score + bonus\n"
            "    select:\n"
            "        id\n"
            "        total\n",
        )
    )
    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)

    assert semantic_result.ok
    assert semantic_result.model is not None
    assert semantic_result.model.relation_row_dependency_graphs
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
    for private_fact in PRIVATE_JSON_FACTS:
        assert private_fact not in serialized


def test_row_dependency_graph_module_does_not_call_full_semantic_analyze() -> None:
    module = (REPO_ROOT / "src/pietto/_project/row_dependency_graph.py").read_text(
        encoding="utf-8"
    )

    assert "semantic_api.analyze" not in module
    assert "from pietto.semantic import analyze" not in module
    assert "import pietto.semantic as semantic_api" not in module


def test_slice9_forbidden_files_have_no_diff() -> None:
    for relative_path in FORBIDDEN_FILES:
        assert _git_diff(relative_path) == ""


def test_slice9_package_version_and_dirty_paths_are_locked() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]

    assert project["version"] == "0.1.0"
    assert _git_status_paths() in (
        set(),
        ALLOWED_SLICE9_GATE2_PATHS,
        ALLOWED_SLICE10_GATE2_PATHS,
        ALLOWED_SLICE11_GATE2_PATHS,
    )


def _edge_values(
    graph: ProjectRelationRowDependencyGraph,
    kind: ProjectRowDependencyEdgeKind,
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (edge.from_node.name, edge.to_node.name)
        for edge in graph.edges
        if edge.kind is kind
    )


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _project(
    root: Path,
    relation_source: str,
    *,
    include_source: bool = True,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    source_prefix = (
        "shape User:\n"
        "    id: Int not null\n"
        "    email: Text nullable\n"
        "    score: Int not null\n"
        "    bonus: Int nullable\n"
        "    status: Text not null\n"
    )
    if include_source:
        source_prefix += 'source users: User is postgres.table("users")\n'
    (root / "models.pietto").write_text(
        source_prefix + relation_source,
        encoding="utf-8",
    )
    return root


def _derived_definition(
    parse_result: ProjectParseCheckResult,
    name: str,
) -> TableDef | QueryDef:
    for parsed_input in parse_result.parsed_inputs:
        for definition in parsed_input.script.definitions:
            if isinstance(definition, (TableDef, QueryDef)) and definition.name == name:
                return definition
    raise AssertionError(f"Missing derived definition: {name}")


def _git_diff(relative_path: str) -> str:
    return _git_output(["diff", "--", relative_path])


def _git_status_paths() -> set[str]:
    output = _git_output(["status", "--short", "--untracked-files=all"])
    return {line[3:] for line in output.splitlines() if line}


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout.rstrip()
