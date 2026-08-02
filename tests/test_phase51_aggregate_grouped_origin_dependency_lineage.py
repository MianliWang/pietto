from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import hashlib
import inspect
import json
from pathlib import Path
import re
import subprocess
from typing import cast

from _phase54_active_gate2_manifest import (
    PHASE54_ACTIVE_GATE2_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE,
    PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto
import pietto._project as project_package
import pietto._project.aggregate_grouped_dependency_lineage as dependency_lineage_module
from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectRelationClauseDependencyKind,
)
from pietto._project.aggregate_grouped_dependency_lineage import (
    ProjectAggregateGroupedDependencyLineageReadiness,
    build_project_aggregate_grouped_dependency_lineage_readiness,
)
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticResult,
    ProjectSymbol,
    build_empty_project_semantic_result,
)
from pietto._project.row_dependency_graph import (
    ProjectRelationRowDependencyGraph,
    ProjectRowDependencyEdgeKind,
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
    ProjectRowDependencyNodeKind,
)
from pietto._project.row_lineage import (
    ProjectRelationRowLineage,
    ProjectRowLineageFactKind,
    ProjectRowLineageReason,
    ProjectRowLineageSegmentKind,
    ProjectRowLineageStatus,
)
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    NameExpr,
    QueryDef,
    SourceDef,
    TableDef,
)
from pietto.errors import SourceLocation
from pietto.semantic.aggregates import child_expressions

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_dependency_lineage.py"
GRAPH_PATH = REPO_ROOT / "src/pietto/_project/row_dependency_graph.py"
LINEAGE_PATH = REPO_ROOT / "src/pietto/_project/row_lineage.py"
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PERSISTENCE_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_persistence.py"
PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md"
)
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase51-origin-provenance-dependency-lineage-integration-v1.md"
)

EXPECTED_GATE2_PATHS = {
    "src/pietto/_project/aggregate_grouped_dependency_lineage.py",
    "src/pietto/_project/row_dependency_graph.py",
    "src/pietto/_project/row_lineage.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md",
    "docs/spec/phase51-origin-provenance-dependency-lineage-integration-v1.md",
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
EXPECTED_UNTRACKED_PATHS = {
    "src/pietto/_project/aggregate_grouped_dependency_lineage.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    "docs/spec/phase51-origin-provenance-dependency-lineage-integration-v1.md",
}
CI_REPAIR_BASE_HEAD_SHA = "321ec6f80737015648bc1f81b0561fdd34610e92"
CI_REPAIR_MODIFIED_PATHS = {
    "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
    "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
}
PHASE54_BASE_HEAD_SHA = "d8a5e9ab3de70ce30575513c73560c86430eca63"
PHASE54_SLICE4_BASE_HEAD_SHA = "15bae172ee151e370fe59d3bf909d735aee6aa90"
PHASE54_SLICE4_PATH_COUNTS = (138, 2, 140)
PHASE54_SLICE5_BASE_HEAD_SHA = "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
PHASE54_SLICE5_PATH_COUNTS = (164, 3, 167)
PHASE54_SLICE6_BASE_HEAD_SHA = "c44a4271d9592cb393d2232f127a59d8466cc60a"
PHASE54_SLICE6_PATH_COUNTS = (57, 4, 61)
PHASE54_SLICE7_BASE_HEAD_SHA = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
PHASE54_SLICE7_PATH_COUNTS = (59, 3, 62)
PHASE54_SLICE8_BASE_HEAD_SHA = "027b33cafcfd58916a89e299487dad38d24ade6c"
PHASE54_SLICE8_PATH_COUNTS = (66, 3, 69)
PHASE54_SLICE9_BASE_HEAD_SHA = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
PHASE54_SLICE9_PATH_COUNTS = (68, 3, 71)
PHASE54_STATE_REL = "tests/_phase54_active_gate2_manifest.py"


def _literal_set(relative: str, name: str) -> set[str]:
    path = REPO_ROOT / relative
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            return value
    raise AssertionError(name)


def _phase53_gate2_paths(name: str) -> set[str]:
    return _literal_set(
        "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
        name,
    )


def _phase54_gate2_paths() -> tuple[set[str], set[str]]:
    added = _literal_set(PHASE54_STATE_REL, "ADDED_PATHS")
    modified = _literal_set(
        PHASE54_STATE_REL,
        "NON_READER_MODIFIED_PATHS",
    ) | _literal_set(PHASE54_STATE_REL, "MECHANICAL_READER_PATHS")
    return modified, added


BOUNDARY_PATHS = (
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
)

type _CandidateInputs = tuple[
    ProjectParseCheckResult,
    ProjectSemanticResult,
    TableDef | QueryDef,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectRelationRowLineage | None,
]


def test_exact_private_enum_extensions_and_composed_carrier_shape(
    tmp_path: Path,
) -> None:
    assert tuple(
        (member.name, member.value) for member in ProjectRowDependencyNodeKind
    ) == (
        ("OUTPUT_FIELD", "output_field"),
        ("UPSTREAM_FIELD", "upstream_field"),
        ("LET_BINDING", "let_binding"),
        ("RELATION_INPUT", "relation_input"),
    )
    assert tuple(
        (member.name, member.value) for member in ProjectRowDependencyEdgeKind
    ) == (
        ("DIRECT_PROJECTION", "direct_projection"),
        ("RENAMED_PROJECTION", "renamed_projection"),
        ("COMPUTED_EXPRESSION", "computed_expression"),
        ("LET_OUTPUT", "let_output"),
        ("LET_EXPRESSION", "let_expression"),
        ("AGGREGATE_ARGUMENT", "aggregate_argument"),
        ("AGGREGATE_RELATION_INPUT", "aggregate_relation_input"),
        ("WINDOW_RELATION_INPUT", "window_relation_input"),
        ("WINDOW_ARGUMENT", "window_argument"),
        ("WINDOW_DEFAULT", "window_default"),
        ("WINDOW_PARTITION", "window_partition"),
        ("WINDOW_ORDER", "window_order"),
    )
    assert tuple(
        (member.name, member.value) for member in ProjectRowLineageSegmentKind
    ) == (
        ("SOURCE_FIELD", "source_field"),
        ("UPSTREAM_FIELD", "upstream_field"),
        ("OUTPUT_FIELD", "output_field"),
        ("LET_BINDING", "let_binding"),
        ("RELATION_INPUT", "relation_input"),
    )
    assert tuple(
        (member.name, member.value) for member in ProjectRowLineageFactKind
    ) == (
        ("DIRECT_PROJECTION", "direct_projection"),
        ("RENAMED_PROJECTION", "renamed_projection"),
        ("COMPUTED_EXPRESSION", "computed_expression"),
        ("LET_OUTPUT", "let_output"),
        ("LET_EXPRESSION", "let_expression"),
        ("TRANSITIVE_DEPENDENCY", "transitive_dependency"),
        ("AGGREGATE_ARGUMENT", "aggregate_argument"),
        ("AGGREGATE_RELATION_INPUT", "aggregate_relation_input"),
        ("WINDOW_RELATION_INPUT", "window_relation_input"),
        ("WINDOW_ARGUMENT", "window_argument"),
        ("WINDOW_DEFAULT", "window_default"),
        ("WINDOW_PARTITION", "window_partition"),
        ("WINDOW_ORDER", "window_order"),
    )
    assert tuple(member.value for member in ProjectRowDependencyGraphStatus) == (
        "concrete",
        "unknown",
        "deferred",
        "blocked",
    )
    assert tuple(member.value for member in ProjectRowLineageStatus) == (
        "concrete",
        "unknown",
        "deferred",
        "blocked",
    )
    assert tuple(
        field.name
        for field in fields(ProjectAggregateGroupedDependencyLineageReadiness)
    ) == ("definition", "clause_readiness", "dependency_graph", "lineage")
    assert is_dataclass(ProjectAggregateGroupedDependencyLineageReadiness)
    assert hasattr(ProjectAggregateGroupedDependencyLineageReadiness, "__slots__")

    signature = inspect.signature(
        build_project_aggregate_grouped_dependency_lineage_readiness
    )
    assert tuple(signature.parameters) == (
        "definition",
        "input_schema",
        "upstream_symbol",
        "upstream_lineage",
        "fallback_path",
        "let_scope_facts",
    )
    assert all(
        parameter.kind is inspect.Parameter.KEYWORD_ONLY
        for parameter in signature.parameters.values()
    )
    assert signature.parameters["upstream_lineage"].default is inspect.Parameter.empty
    assert signature.parameters["let_scope_facts"].default is None

    _, _, definition, input_schema, symbol, upstream_lineage = _candidate_inputs(
        tmp_path,
        _aggregate_body("total = count()"),
    )
    result = _readiness(definition, input_schema, symbol, upstream_lineage)
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(result, "lineage", None)
    with pytest.raises(ValueError, match="definition identity"):
        replace(result, definition=replace(definition, name="other"))
    with pytest.raises(ValueError, match="outcome mismatch"):
        replace(
            result,
            lineage=ProjectRelationRowLineage(
                status=ProjectRowLineageStatus.UNKNOWN,
                reason=ProjectRowLineageReason.UNKNOWN_SCHEMA,
            ),
        )
    with pytest.raises(ValueError, match="retain every immediate"):
        replace(result, lineage=replace(result.lineage, facts=()))
    with pytest.raises(ValueError, match="must be empty"):
        ProjectAggregateGroupedDependencyLineageReadiness(
            definition=definition,
            clause_readiness=result.clause_readiness,
            dependency_graph=ProjectRelationRowDependencyGraph(
                status=ProjectRowDependencyGraphStatus.UNKNOWN,
                reason=ProjectRowDependencyGraphReason.UNKNOWN_SCHEMA,
                nodes=(result.dependency_graph.nodes[0],),
            ),
            lineage=ProjectRelationRowLineage(
                status=ProjectRowLineageStatus.UNKNOWN,
                reason=ProjectRowLineageReason.UNKNOWN_SCHEMA,
            ),
        )


def test_composed_builder_calls_slice8_readiness_exactly_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, definition, input_schema, symbol, upstream_lineage = _candidate_inputs(
        tmp_path,
        _aggregate_body("total = sum(amount)"),
    )
    original = (
        dependency_lineage_module.build_project_aggregate_grouped_clause_readiness
    )
    captured: list[ProjectAggregateGroupedClauseReadiness] = []

    def spy(
        *,
        definition: TableDef | QueryDef,
        input_schema: ProjectRowSchema,
        upstream_symbol: ProjectSymbol,
        fallback_path: str,
        let_scope_facts: ProjectRelationLetScopeFacts | None = None,
    ) -> ProjectAggregateGroupedClauseReadiness:
        readiness = original(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path=fallback_path,
            let_scope_facts=let_scope_facts,
        )
        captured.append(readiness)
        return readiness

    monkeypatch.setattr(
        dependency_lineage_module,
        "build_project_aggregate_grouped_clause_readiness",
        spy,
    )
    result = _readiness(definition, input_schema, symbol, upstream_lineage)
    assert len(captured) == 1
    assert result.clause_readiness is captured[0]
    source = inspect.getsource(
        dependency_lineage_module.build_project_aggregate_grouped_dependency_lineage_readiness
    )
    assert source.count("build_project_aggregate_grouped_clause_readiness(") == 1
    assert "build_project_aggregate_grouped_schema_finalization" not in (
        HELPER_PATH.read_text(encoding="utf-8")
    )


def test_non_concrete_clause_readiness_mirrors_without_dependency_or_lineage_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden_traversal(*_args: object, **_kwargs: object) -> Expression:
        raise AssertionError("non-concrete result traversed")

    monkeypatch.setattr(
        dependency_lineage_module,
        "effective_semantic_aggregate_argument_expression",
        forbidden_traversal,
    )
    cases = (
        (
            "duplicate",
            _aggregate_body("duplicate = sum(amount)\n        duplicate = avg(score)"),
            ProjectRowDependencyGraphStatus.UNKNOWN,
            ProjectRowDependencyGraphReason.DUPLICATE_OUTPUT_NAME,
        ),
        (
            "pure",
            "query candidate:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n",
            ProjectRowDependencyGraphStatus.DEFERRED,
            ProjectRowDependencyGraphReason.AGGREGATE_OR_GROUPED_DEFERRED,
        ),
    )
    for name, body, status, reason in cases:
        _, _, definition, input_schema, symbol, upstream_lineage = _candidate_inputs(
            tmp_path / name,
            body,
        )
        result = _readiness(definition, input_schema, symbol, upstream_lineage)
        _assert_atomic_empty(result, status=status, reason=reason)
        assert result.clause_readiness.definition is definition

    _, _, grouped, grouped_schema, grouped_symbol, grouped_lineage = _candidate_inputs(
        tmp_path / "blocked",
        _grouped_body(),
    )
    aggregate_item = grouped.select_items[-1]
    conflicting = replace(
        grouped,
        select_items=(aggregate_item, aggregate_item),
    )
    blocked = _readiness(
        conflicting,
        grouped_schema,
        grouped_symbol,
        grouped_lineage,
    )
    _assert_atomic_empty(
        blocked,
        status=ProjectRowDependencyGraphStatus.BLOCKED,
        reason=ProjectRowDependencyGraphReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
    )


def test_selected_group_key_output_dependency_and_unselected_clause_only_boundary(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, symbol, upstream_lineage = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        region\n"
        "        created_at\n"
        "    select:\n"
        "        status\n"
        "        area = region\n"
        "        total = count()\n",
    )
    result = _readiness(definition, input_schema, symbol, upstream_lineage)
    assert result.dependency_graph.status is ProjectRowDependencyGraphStatus.CONCRETE
    group_facts = tuple(
        fact
        for fact in result.clause_readiness.dependency_facts
        if fact.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT
    )
    assert tuple(fact.target_field.name for fact in group_facts) == (
        "status",
        "region",
        "created_at",
    )
    output_nodes = tuple(
        node.name
        for node in result.dependency_graph.nodes
        if node.kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD
    )
    assert output_nodes == ("status", "area", "total")
    assert _edge_names(result.dependency_graph)[:2] == (
        (ProjectRowDependencyEdgeKind.DIRECT_PROJECTION, "status", "users.status"),
        (ProjectRowDependencyEdgeKind.RENAMED_PROJECTION, "area", "users.region"),
    )
    assert "created_at" not in output_nodes
    assert all(
        edge.kind.value
        not in {"group_key_input", "satisfying_output", "grouped_order_output"}
        for edge in result.dependency_graph.edges
    )
    finalized_schema = result.clause_readiness.finalization.state.schema
    assert finalized_schema is not None
    assert tuple(finalized_schema.fields) == (
        "status",
        "area",
        "total",
    )
    assert finalized_schema.fields["area"].result_role is ProjectRowResultRole.GROUP_KEY
    assert tuple(fact.upstream_segment.kind for fact in result.lineage.facts[:2]) == (
        ProjectRowLineageSegmentKind.SOURCE_FIELD,
        ProjectRowLineageSegmentKind.SOURCE_FIELD,
    )


def test_aggregate_argument_edges_preserve_select_ast_order_and_first_target_dedupe(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, symbol, upstream_lineage = _candidate_inputs(
        tmp_path,
        _aggregate_body(
            "counted = count(users.amount)\n"
            "        distinct = count_distinct(lower(trim(status)))\n"
            "        summed = sum(amount + tax + amount + 1)\n"
            "        average = avg(score * weight)\n"
            "        earliest = min(created_at)\n"
            "        largest = max(price)"
        ),
    )
    result = _readiness(definition, input_schema, symbol, upstream_lineage)
    argument_edges = tuple(
        edge
        for edge in result.dependency_graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT
    )
    assert tuple(
        (edge.from_node.name, edge.to_node.name) for edge in argument_edges
    ) == (
        ("counted", "users.amount"),
        ("distinct", "users.status"),
        ("summed", "users.amount"),
        ("summed", "users.tax"),
        ("average", "users.score"),
        ("average", "users.weight"),
        ("earliest", "users.created_at"),
        ("largest", "users.price"),
    )
    assert tuple(
        edge.to_node.name for edge in argument_edges if edge.from_node.name == "summed"
    ) == ("users.amount", "users.tax")
    names = {node.name for node in result.dependency_graph.nodes}
    assert names.isdisjoint({"lower", "trim", "sum", "avg", "1"})
    summed_call = cast(CallExpr, definition.select_items[2].expression)
    amount_occurrences = tuple(
        occurrence
        for occurrence in _name_occurrences(summed_call.arguments[0])
        if occurrence.name == "amount"
    )
    summed_amount_edge = next(
        edge
        for edge in argument_edges
        if edge.from_node.name == "summed" and edge.to_node.field_name == "amount"
    )
    assert summed_amount_edge.location == _location(amount_occurrences[0])
    assert all(
        fact.kind is ProjectRowLineageFactKind.AGGREGATE_ARGUMENT
        for fact in result.lineage.facts
    )


def test_count_relation_input_dependency_has_no_field_leaf(tmp_path: Path) -> None:
    _, _, definition, _, symbol, _ = _candidate_inputs(
        tmp_path / "empty",
        _aggregate_body("total = count()"),
    )
    empty = _readiness(definition, ProjectRowSchema(), symbol, None)
    _assert_count_relation_input(empty, immediate_name="users")

    _, _, relation_definition, input_schema, relation_symbol, upstream_lineage = (
        _candidate_inputs(
            tmp_path / "relation",
            "query middle:\n"
            "    from users\n"
            "    select:\n"
            "        amount\n"
            "query candidate:\n"
            "    from middle\n"
            "    select:\n"
            "        total = count()\n",
        )
    )
    relation = _readiness(
        relation_definition,
        input_schema,
        relation_symbol,
        upstream_lineage,
    )
    _assert_count_relation_input(relation, immediate_name="middle")
    total_facts = tuple(
        fact for fact in relation.lineage.facts if fact.output_segment.name == "total"
    )
    assert len(total_facts) == 1
    assert total_facts[0].upstream_segment.kind is (
        ProjectRowLineageSegmentKind.RELATION_INPUT
    )


@pytest.mark.parametrize(
    ("bindings", "expected_let_edges", "expected_source_fields"),
    (
        (
            "        selected = amount\n",
            (("selected", "users.amount"),),
            {"amount"},
        ),
        (
            "        base = amount\n        selected = base\n",
            (("base", "users.amount"), ("selected", "base")),
            {"amount"},
        ),
        (
            "        base = amount + tax\n        selected = base + amount\n",
            (
                ("base", "users.amount"),
                ("base", "users.tax"),
                ("selected", "base"),
                ("selected", "users.amount"),
            ),
            {"amount", "tax"},
        ),
    ),
)
def test_direct_chained_and_computed_let_ancestry_is_immediate_then_transitive(
    tmp_path: Path,
    bindings: str,
    expected_let_edges: tuple[tuple[str, str], ...],
    expected_source_fields: set[str],
) -> None:
    _, _, definition, input_schema, symbol, upstream_lineage = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        f"{bindings}"
        "    select:\n"
        "        total = sum(selected)\n",
    )
    result = _readiness(definition, input_schema, symbol, upstream_lineage)
    aggregate_edge = next(
        edge
        for edge in result.dependency_graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.AGGREGATE_ARGUMENT
    )
    assert aggregate_edge.from_node.name == "total"
    assert aggregate_edge.to_node.kind is ProjectRowDependencyNodeKind.LET_BINDING
    assert aggregate_edge.to_node.name == "selected"
    let_edges = tuple(
        (edge.from_node.name, edge.to_node.name)
        for edge in result.dependency_graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.LET_EXPRESSION
    )
    assert let_edges == expected_let_edges
    assert result.lineage.facts[0].kind is ProjectRowLineageFactKind.AGGREGATE_ARGUMENT
    assert result.lineage.facts[0].upstream_segment.kind is (
        ProjectRowLineageSegmentKind.LET_BINDING
    )
    source_fields = {
        fact.upstream_segment.field_name
        for fact in result.lineage.facts
        if fact.upstream_segment.kind is ProjectRowLineageSegmentKind.SOURCE_FIELD
    }
    assert source_fields == expected_source_fields


def test_table_query_source_relation_and_multi_hop_upstream_parity(
    tmp_path: Path,
) -> None:
    for relation_kind in ("table", "query"):
        _, _, definition, input_schema, symbol, upstream_lineage = _candidate_inputs(
            tmp_path / relation_kind,
            f"{relation_kind} candidate:\n"
            "    from users\n"
            "    select:\n"
            "        total = sum(amount)\n",
        )
        result = _readiness(definition, input_schema, symbol, upstream_lineage)
        assert result.dependency_graph.reason is (
            ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE
        )
        assert result.lineage.facts[0].upstream_segment.kind is (
            ProjectRowLineageSegmentKind.SOURCE_FIELD
        )

    _, _, candidate, input_schema, symbol, upstream_lineage = _candidate_inputs(
        tmp_path / "multi-hop",
        "query seed:\n"
        "    from users\n"
        "    select:\n"
        "        amount\n"
        "table middle:\n"
        "    from seed\n"
        "    select:\n"
        "        amount\n"
        "query candidate:\n"
        "    from middle\n"
        "    select:\n"
        "        total = sum(amount)\n",
    )
    result = _readiness(candidate, input_schema, symbol, upstream_lineage)
    assert result.dependency_graph.reason is (
        ProjectRowDependencyGraphReason.RELATION_UPSTREAM_CONCRETE
    )
    assert _edge_names(result.dependency_graph)[0][2] == "middle.amount"
    lineage_names = {fact.upstream_segment.name for fact in result.lineage.facts}
    assert {"middle.amount", "seed.amount", "users.amount"} <= lineage_names
    assert all("users.amount" != node.name for node in result.dependency_graph.nodes)

    missing = _readiness(candidate, input_schema, symbol, None)
    _assert_atomic_empty(
        missing,
        status=ProjectRowDependencyGraphStatus.BLOCKED,
        reason=ProjectRowDependencyGraphReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
    )
    unavailable = _readiness(
        candidate,
        input_schema,
        symbol,
        ProjectRelationRowLineage(
            status=ProjectRowLineageStatus.UNKNOWN,
            reason=ProjectRowLineageReason.UNKNOWN_SCHEMA,
        ),
    )
    _assert_atomic_empty(
        unavailable,
        status=ProjectRowDependencyGraphStatus.BLOCKED,
        reason=ProjectRowDependencyGraphReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
    )


def test_duplicate_invalid_clause_and_pure_grouping_outcomes_are_atomic(
    tmp_path: Path,
) -> None:
    cases = (
        _aggregate_body("duplicate = sum(amount)\n        duplicate = avg(score)"),
        _aggregate_body("literal = sum(1)"),
        _aggregate_body("missing = sum(does_not_exist)"),
        _aggregate_body("nested = sum(max(amount))"),
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n",
        "query candidate:\n"
        "    from users\n"
        "    select:\n"
        "        total = count()\n"
        "    order by:\n"
        "        amount asc\n",
    )
    for index, body in enumerate(cases):
        _, _, definition, input_schema, symbol, upstream_lineage = _candidate_inputs(
            tmp_path / str(index),
            body,
        )
        result = _readiness(definition, input_schema, symbol, upstream_lineage)
        assert result.dependency_graph.status is not (
            ProjectRowDependencyGraphStatus.CONCRETE
        )
        assert result.dependency_graph.nodes == ()
        assert result.dependency_graph.edges == ()
        assert result.lineage.facts == ()
        assert result.dependency_graph.status.value == result.lineage.status.value
        assert result.dependency_graph.reason.value == result.lineage.reason.value
    literal = _candidate_inputs(
        tmp_path / "literal-lock",
        _aggregate_body("literal = sum(1)"),
    )
    literal_result = _readiness(literal[2], literal[3], literal[4], literal[5])
    assert literal_result.dependency_graph.reason is (
        ProjectRowDependencyGraphReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    )


def test_origin_dependency_lineage_production_is_persisted_and_downstream_active(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query aggregate_only:\n"
            "    from users\n"
            "    select:\n"
            "        total = count()\n"
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount)\n"
            "query pure_grouping:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "query downstream:\n"
            "    from aggregate_only\n"
            "    select:\n"
            "        total\n",
        )
    )
    assert semantic_result.model is not None
    model = semantic_result.model
    for name in ("aggregate_only", "grouped"):
        definition = _derived_definition(parse_result, name)
        symbol = model.relation_resolutions[definition.from_clause]
        assert isinstance(symbol.definition, SourceDef)
        _readiness(
            definition,
            model.source_row_schemas[symbol.definition],
            symbol,
            None,
        )

    aggregate_only = _derived_definition(parse_result, "aggregate_only")
    grouped = _derived_definition(parse_result, "grouped")
    pure_grouping = _derived_definition(parse_result, "pure_grouping")
    assert tuple(model.relation_aggregate_result_facts) == (
        aggregate_only,
        grouped,
    )
    for definition, expected_fields in (
        (aggregate_only, ("total",)),
        (grouped, ("status", "total")),
    ):
        state = model.relation_row_schema_states[definition]
        assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
        assert state.reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
        schema = state.schema
        assert schema is not None
        assert schema is model.relation_row_schemas[definition]
        assert tuple(schema.fields) == expected_fields
        assert tuple(model.relation_aggregate_result_facts[definition]) == ("total",)
        graph = model.relation_row_dependency_graphs[definition]
        lineage = model.relation_row_lineages[definition]
        assert graph.status is ProjectRowDependencyGraphStatus.CONCRETE
        assert graph.reason is ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE
        assert graph.edges
        assert lineage.status is ProjectRowLineageStatus.CONCRETE
        assert lineage.reason is ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE
        assert lineage.facts

    pure_state = model.relation_row_schema_states[pure_grouping]
    assert pure_state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert pure_state.reason is (
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert pure_state.schema is None
    assert pure_grouping not in model.relation_aggregate_result_facts
    pure_graph = model.relation_row_dependency_graphs[pure_grouping]
    pure_lineage = model.relation_row_lineages[pure_grouping]
    assert pure_graph.status is ProjectRowDependencyGraphStatus.DEFERRED
    assert pure_graph.reason is (
        ProjectRowDependencyGraphReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert pure_graph.edges == ()
    assert pure_lineage.status is ProjectRowLineageStatus.DEFERRED
    assert pure_lineage.reason is (
        ProjectRowLineageReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert pure_lineage.facts == ()

    downstream = _derived_definition(parse_result, "downstream")
    assert model.relation_row_schema_states[downstream].status is (
        ProjectRelationRowSchemaStatus.CONCRETE
    )
    assert tuple(model.relation_row_schemas[downstream].fields) == ("total",)
    assert model.relation_row_dependency_graphs[downstream].edges
    assert model.relation_row_lineages[downstream].facts


def test_private_helper_is_not_exported_or_serialized(tmp_path: Path) -> None:
    assert dependency_lineage_module.__all__ == ()
    for name in (
        "ProjectAggregateGroupedDependencyLineageReadiness",
        "build_project_aggregate_grouped_dependency_lineage_readiness",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
    model_source = MODEL_PATH.read_text(encoding="utf-8")
    helper_source = HELPER_PATH.read_text(encoding="utf-8")
    persistence_source = PERSISTENCE_PATH.read_text(encoding="utf-8")
    assert "aggregate_grouped_persistence" in model_source
    assert "build_project_aggregate_grouped_persistence(" in model_source
    assert "aggregate_grouped_dependency_lineage" in persistence_source
    assert (
        persistence_source.count(
            "build_project_aggregate_grouped_dependency_lineage_readiness("
        )
        == 1
    )
    assert "ProjectSemanticModel" not in helper_source
    assert "Diagnostic(" not in helper_source
    assert "semantic_api.analyze" not in helper_source
    assert "from pietto.semantic import analyze" not in helper_source

    parse_result, semantic_result = _project_semantic_result(
        _project(tmp_path, _aggregate_body("total = count()"))
    )
    serialized = json.dumps(
        project_check_result_to_json_dict(
            parse_result,
            semantic_diagnostics=semantic_result.diagnostics,
        )
    )
    for value in (
        "ProjectAggregateGroupedDependencyLineageReadiness",
        "relation_input",
        "aggregate_argument",
        "aggregate_relation_input",
    ):
        assert value not in serialized


def test_slice9_documentation_allowlist_hash_and_protected_boundaries() -> None:
    plan_lines = PLAN_PATH.read_text(encoding="utf-8").splitlines()
    heading = "### Slice 9 Gate 2 Bounded Implementation Status"
    assert plan_lines.count(heading) == 1
    assert "## Slice 9 Gate 2 Bounded Implementation Status" not in plan_lines
    spec_lines = SPEC_PATH.read_text(encoding="utf-8").splitlines()
    assert spec_lines[0] == (
        "# Phase 51 Origin Provenance Dependency And Lineage Integration v1"
    )
    assert tuple(line for line in spec_lines if line.startswith("## ")) == (
        "## Status And Authority",
        "## Controlling Architecture",
        "## Exact Carrier And Builder",
        "## Exact Graph Vocabulary",
        "## Exact Lineage Vocabulary",
        "## Status Reason Mapping And Atomicity",
        "## Selected Group-key Output Dependency And Lineage",
        "## Aggregate Argument Leaf Extraction",
        "## No-argument Count Relation-input Dependency",
        "## Selected-let Dependency And Ancestry",
        "## Deterministic Ordering And Dedupe",
        "## Slice 8 Clause-fact Separation",
        "## Table Query And Upstream Parity",
        "## Pure-grouping Boundary",
        "## Production Non-persistence And Slice 10 Ownership",
        "## Privacy Public Compiler And Diagnostic Boundary",
        "## Exact Gate 2 Allowlist",
        "## Format Hash And Environment Procedure",
        "## Exact Validation Matrix",
        "## Evidence And Stop Rules",
    )
    spec_text = "\n".join(spec_lines)
    for path in EXPECTED_GATE2_PATHS:
        assert f"`{path}`" in spec_text

    dirty = _git_paths(["status", "--short", "--untracked-files=all"])
    slice14_modified = _phase53_gate2_paths("MODIFIED_PATHS")
    slice14_added = _phase53_gate2_paths("ADDED_PATHS")
    phase54_modified, phase54_added = _phase54_gate2_paths()
    assert dirty in (
        set(),
        EXPECTED_GATE2_PATHS,
        CI_REPAIR_MODIFIED_PATHS,
        slice14_modified | slice14_added,
        phase54_modified | phase54_added,
    )
    untracked = _git_paths(["ls-files", "--others", "--exclude-standard"])
    assert untracked in (
        set(),
        EXPECTED_UNTRACKED_PATHS,
        slice14_added,
        phase54_added,
    )
    if dirty == CI_REPAIR_MODIFIED_PATHS:
        assert untracked == set()
        assert _git_output(["branch", "--show-current"]).strip() == "main"
        assert (
            tuple(
                _git_output(["rev-parse", ref]).strip()
                for ref in ("HEAD", "main", "origin/main")
            )
            == (CI_REPAIR_BASE_HEAD_SHA,) * 3
        )
    elif dirty == phase54_modified | phase54_added:
        assert untracked == phase54_added
        assert set(_git_output(["diff", "--name-only"]).splitlines()) == (
            phase54_modified
        )
        path_counts = (
            len(phase54_modified),
            len(phase54_added),
            len(phase54_modified | phase54_added),
        )
        expected_head = PHASE54_BASE_HEAD_SHA
        if path_counts == PHASE54_SLICE4_PATH_COUNTS:
            expected_head = PHASE54_SLICE4_BASE_HEAD_SHA
        elif path_counts == PHASE54_SLICE5_PATH_COUNTS:
            expected_head = PHASE54_SLICE5_BASE_HEAD_SHA
        elif path_counts == PHASE54_SLICE6_PATH_COUNTS:
            expected_head = PHASE54_SLICE6_BASE_HEAD_SHA
        elif path_counts == PHASE54_SLICE7_PATH_COUNTS:
            expected_head = PHASE54_SLICE7_BASE_HEAD_SHA
        elif path_counts == PHASE54_SLICE8_PATH_COUNTS:
            expected_head = PHASE54_SLICE8_BASE_HEAD_SHA
        elif path_counts == PHASE54_SLICE9_PATH_COUNTS:
            expected_head = PHASE54_SLICE9_BASE_HEAD_SHA
        if _phase54_active_gate2_is_active():
            active_head = _git_output(["rev-parse", "HEAD"]).strip()
            assert active_head in {
                PHASE54_ACTIVE_GATE2_BASE,
                PHASE54_POST_REVIEW_PRODUCT_REPAIR1_BASE,
                PHASE54_POST_REVIEW_PRODUCT_REPAIR2_BASE,
            }
            expected_head = active_head
        assert _git_output(["rev-parse", "HEAD"]).strip() == expected_head
    assert _git_output(["diff", "--cached", "--name-status"]) == ""

    compiler_digest = _compiler_digest()
    for relative_path in BOUNDARY_PATHS:
        match = re.search(
            r'^BOUNDARY_HASH = "([0-9a-f]{64})"$',
            (REPO_ROOT / relative_path).read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        )
        assert match is not None
        assert match.group(1) == compiler_digest
    project_paths = _project_private_paths()
    project_digest = _digest(project_paths)
    assert len(project_paths) == 28
    phase33 = (REPO_ROOT / "tests/test_phase33_completion_audit.py").read_text(
        encoding="utf-8"
    )
    assert (
        f'"project_private": (\n        "src/pietto/_project",\n'
        f'        28,\n        "{project_digest}",\n    ),'
    ) in phase33

    protected = (
        "src/pietto/_project/model.py",
        "src/pietto/_project/aggregate_grouped_schema.py",
        "src/pietto/_project/aggregate_grouped_clause_facts.py",
        "src/pietto/_project/let_scope_facts.py",
        "src/pietto/_project/row_expression_schema.py",
        "src/pietto/_project/row_expression_type_facts.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/check.py",
        "src/pietto/_project/__init__.py",
        "src/pietto/semantic",
        "src/pietto/ir.py",
        "src/pietto/sql.py",
        "src/pietto/cli.py",
        "grammar/Pietto.g4",
        "pyproject.toml",
        "uv.lock",
        "docs/spec/pietto-roadmap-phase45-60-v1.md",
        ".github/workflows",
        "scripts",
        "tests/fixtures",
        "tests/goldens",
        "examples",
    )
    if dirty == phase54_modified | phase54_added:
        protected = tuple(path for path in protected if path not in phase54_modified)
    assert _git_output(["diff", "--", *protected]) == ""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.1.0"' in pyproject
    assert '"ruff>=0.16.0"' in pyproject
    assert '"mypy>=2.3.0"' in pyproject


def _readiness(
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
    upstream_lineage: ProjectRelationRowLineage | None,
) -> ProjectAggregateGroupedDependencyLineageReadiness:
    return build_project_aggregate_grouped_dependency_lineage_readiness(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        upstream_lineage=upstream_lineage,
        fallback_path="models.pietto",
    )


def _candidate_inputs(
    root: Path,
    relations: str,
    *,
    definition_name: str = "candidate",
) -> _CandidateInputs:
    parse_result, semantic_result = _project_semantic_result(_project(root, relations))
    assert semantic_result.model is not None
    definition = _derived_definition(parse_result, definition_name)
    model = semantic_result.model
    upstream_symbol = model.relation_resolutions[definition.from_clause]
    upstream_definition = upstream_symbol.definition
    if isinstance(upstream_definition, SourceDef):
        input_schema = model.source_row_schemas[upstream_definition]
        upstream_lineage = None
    else:
        assert isinstance(upstream_definition, (TableDef, QueryDef))
        input_schema = model.relation_row_schemas[upstream_definition]
        upstream_lineage = model.relation_row_lineages[upstream_definition]
    return (
        parse_result,
        semantic_result,
        definition,
        input_schema,
        upstream_symbol,
        upstream_lineage,
    )


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    semantic_result = build_empty_project_semantic_result(parse_result)
    return parse_result, semantic_result


def _project(root: Path, relations: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 1\n\n[sources]\ninclude = ["models.pietto"]\n',
        encoding="utf-8",
    )
    (root / "models.pietto").write_text(
        "shape User:\n"
        "    active: Bool not null\n"
        "    amount: Int not null\n"
        "    tax: Int nullable\n"
        "    score: Float not null\n"
        "    weight: Float nullable\n"
        "    price: Decimal(12, 2) not null\n"
        "    status: Text not null\n"
        "    region: Text nullable\n"
        "    created_at: Timestamp not null\n"
        'source users: User is postgres.table("users")\n'
        f"{relations}",
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
    raise AssertionError(f"Derived definition not found: {name}")


def _aggregate_body(select_items: str) -> str:
    return f"query candidate:\n    from users\n    select:\n        {select_items}\n"


def _grouped_body() -> str:
    return (
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
    )


def _assert_atomic_empty(
    result: ProjectAggregateGroupedDependencyLineageReadiness,
    *,
    status: ProjectRowDependencyGraphStatus,
    reason: ProjectRowDependencyGraphReason,
) -> None:
    assert result.dependency_graph.status is status
    assert result.dependency_graph.reason is reason
    assert result.lineage.status.value == status.value
    assert result.lineage.reason.value == reason.value
    assert result.dependency_graph.nodes == ()
    assert result.dependency_graph.edges == ()
    assert result.lineage.facts == ()


def _assert_count_relation_input(
    result: ProjectAggregateGroupedDependencyLineageReadiness,
    *,
    immediate_name: str,
) -> None:
    relation_nodes = tuple(
        node
        for node in result.dependency_graph.nodes
        if node.kind is ProjectRowDependencyNodeKind.RELATION_INPUT
    )
    assert len(relation_nodes) == 1
    assert relation_nodes[0].name == immediate_name
    assert relation_nodes[0].field_name is None
    assert not any(
        node.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
        for node in result.dependency_graph.nodes
    )
    relation_edges = tuple(
        edge
        for edge in result.dependency_graph.edges
        if edge.kind is ProjectRowDependencyEdgeKind.AGGREGATE_RELATION_INPUT
    )
    assert len(relation_edges) == 1
    assert relation_edges[0].to_node is relation_nodes[0]
    relation_facts = tuple(
        fact
        for fact in result.lineage.facts
        if fact.kind is ProjectRowLineageFactKind.AGGREGATE_RELATION_INPUT
    )
    assert len(relation_facts) == 1
    assert relation_facts[0].upstream_segment.kind is (
        ProjectRowLineageSegmentKind.RELATION_INPUT
    )


def _edge_names(
    graph: ProjectRelationRowDependencyGraph,
) -> tuple[tuple[ProjectRowDependencyEdgeKind, str, str], ...]:
    return tuple(
        (edge.kind, edge.from_node.name, edge.to_node.name) for edge in graph.edges
    )


def _name_occurrences(expression: Expression) -> tuple[NameExpr, ...]:
    if isinstance(expression, NameExpr):
        return (expression,)
    if isinstance(expression, DottedNameExpr):
        return ()
    return tuple(
        occurrence
        for child in child_expressions(expression)
        for occurrence in _name_occurrences(child)
    )


def _location(expression: Expression) -> SourceLocation:
    span = expression.span
    return SourceLocation(
        path=span.path or "models.pietto",
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _git_paths(args: list[str]) -> set[str]:
    output = _git_output(args)
    if args[:2] == ["status", "--short"]:
        return {line[3:] for line in output.splitlines() if line}
    return {line for line in output.splitlines() if line}


def _compiler_digest() -> str:
    paths = [REPO_ROOT / "Makefile", REPO_ROOT / "grammar/Pietto.g4"]
    paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    return _digest(
        tuple(sorted(paths, key=lambda path: path.relative_to(REPO_ROOT).as_posix()))
    )


def _project_private_paths() -> tuple[Path, ...]:
    return tuple(
        sorted(
            (
                path
                for path in (REPO_ROOT / "src/pietto/_project").rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix != ".pyc"
            ),
            key=lambda path: path.relative_to(REPO_ROOT).as_posix(),
        )
    )


def _digest(paths: tuple[Path, ...] | list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
