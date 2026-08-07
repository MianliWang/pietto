from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
import json
from pathlib import Path
import subprocess
from typing import Any, cast

import pytest

import pietto
import pietto._project as project_package
import pietto._project.aggregate_grouped_clause_facts as clause_module
from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectAggregateGroupedClauseReadinessReason,
    ProjectAggregateGroupedClauseReadinessStatus,
    ProjectRelationClauseDependencyFact,
    ProjectRelationClauseDependencyKind,
    build_project_aggregate_grouped_clause_readiness,
)
from pietto._project.aggregate_grouped_schema import (
    ProjectAggregateGroupedSchemaFinalization,
    ProjectGroupKeyFact,
    ProjectGroupKeySchemaFacts,
    build_project_group_key_schema_facts,
)
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectRowSchema,
    ProjectSemanticModel,
    ProjectSemanticResult,
    ProjectSymbol,
    build_empty_project_semantic_result,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyGraphReason,
    ProjectRowDependencyGraphStatus,
)
from pietto._project.row_lineage import (
    ProjectRowLineageReason,
    ProjectRowLineageStatus,
)
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    Expression,
    NameExpr,
    QueryDef,
    SourceDef,
    TableDef,
)
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_clause_facts.py"
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md"
)
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase51-aggregate-grouped-clause-dependency-readiness-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
LOCK_PATH = REPO_ROOT / "uv.lock"

EXPECTED_GATE2_PATHS = {
    "docs/plan/phase-51-aggregate-grouped-output-schema-foundation.md",
    "docs/spec/phase51-aggregate-grouped-clause-dependency-readiness-v1.md",
    "src/pietto/_project/aggregate_grouped_clause_facts.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase51_clause_dependency_fail_closed.py",
}
EXPECTED_UNTRACKED_PATHS = {
    "docs/spec/phase51-aggregate-grouped-clause-dependency-readiness-v1.md",
    "src/pietto/_project/aggregate_grouped_clause_facts.py",
    "tests/test_phase51_clause_dependency_fail_closed.py",
}


def test_exact_private_enum_vocabulary_and_carrier_shape() -> None:
    assert {
        member.name: member.value for member in ProjectRelationClauseDependencyKind
    } == {
        "GROUP_KEY_INPUT": "group_key_input",
        "SATISFYING_OUTPUT": "satisfying_output",
        "GROUPED_ORDER_OUTPUT": "grouped_order_output",
    }
    assert {
        member.name: member.value
        for member in ProjectAggregateGroupedClauseReadinessStatus
    } == {
        "CONCRETE": "concrete",
        "UNKNOWN": "unknown",
        "DEFERRED": "deferred",
        "BLOCKED": "blocked",
    }
    assert {
        member.name: member.value
        for member in ProjectAggregateGroupedClauseReadinessReason
    } == {
        "CLAUSES_READY": "clauses_ready",
        "SCHEMA_FINALIZATION_NON_CONCRETE": ("schema_finalization_non_concrete"),
        "UNAVAILABLE_CLAUSE_DEPENDENCY": "unavailable_clause_dependency",
        "INVALID_CLAUSE_OUTPUT_REFERENCE": "invalid_clause_output_reference",
        "INVALID_CLAUSE_EXPRESSION": "invalid_clause_expression",
        "UNSUPPORTED_CLAUSE_FAMILY": "unsupported_clause_family",
        "MISSING_REQUIRED_CLAUSE_FACT": "missing_required_clause_fact",
        "CONFLICTING_CLAUSE_FACTS": "conflicting_clause_facts",
    }
    assert tuple(
        field.name for field in fields(ProjectRelationClauseDependencyFact)
    ) == (
        "kind",
        "source_occurrence",
        "target_occurrence",
        "target_field",
        "aggregate_result_fact",
    )
    assert tuple(
        field.name for field in fields(ProjectAggregateGroupedClauseReadiness)
    ) == (
        "definition",
        "finalization",
        "status",
        "reason",
        "dependency_facts",
        "limit_present",
    )
    for carrier in (
        ProjectRelationClauseDependencyFact,
        ProjectAggregateGroupedClauseReadiness,
    ):
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
    assert clause_module.__all__ == ()
    for name in (
        "ProjectRelationClauseDependencyKind",
        "ProjectAggregateGroupedClauseReadinessStatus",
        "ProjectAggregateGroupedClauseReadinessReason",
        "ProjectRelationClauseDependencyFact",
        "ProjectAggregateGroupedClauseReadiness",
        "build_project_aggregate_grouped_clause_readiness",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)


def test_valid_direct_construction_tuple_copy_freezing_and_identity(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _grouped_body(
            satisfying="total > 0",
            order_items=("status asc",),
            limit="1",
        ),
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    assert definition.group_by_clause is not None
    assert definition.satisfying_clause is not None
    assert definition.order_by_clause is not None
    assert result.finalization.state.schema is not None
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert result.reason is ProjectAggregateGroupedClauseReadinessReason.CLAUSES_READY
    assert result.limit_present
    assert not hasattr(result, "__dict__")
    assert all(not hasattr(fact, "__dict__") for fact in result.dependency_facts)
    with pytest.raises(FrozenInstanceError):
        setattr(result, "limit_present", False)
    with pytest.raises(FrozenInstanceError):
        setattr(result.dependency_facts[0], "target_field", None)

    mutable_facts = list(result.dependency_facts)
    copied = ProjectAggregateGroupedClauseReadiness(
        definition=definition,
        finalization=result.finalization,
        status=result.status,
        reason=result.reason,
        dependency_facts=cast(Any, mutable_facts),
        limit_present=True,
    )
    assert type(copied.dependency_facts) is tuple
    assert copied.dependency_facts == result.dependency_facts
    mutable_facts.clear()
    assert copied.dependency_facts == result.dependency_facts

    group_fact, satisfying_fact, order_fact = result.dependency_facts
    assert isinstance(group_fact.target_occurrence, ProjectGroupKeyFact)
    assert group_fact.source_occurrence is definition.group_by_clause.items[0]
    assert group_fact.target_occurrence.item is group_fact.source_occurrence
    assert group_fact.target_occurrence.input_field is group_fact.target_field
    assert group_fact.aggregate_result_fact is None
    assert (
        satisfying_fact.source_occurrence
        is _name_occurrences(definition.satisfying_clause.expression)[0]
    )
    assert satisfying_fact.target_occurrence is definition.select_items[1]
    assert (
        satisfying_fact.target_field is result.finalization.state.schema.fields["total"]
    )
    assert (
        satisfying_fact.aggregate_result_fact
        is result.finalization.aggregate_result_facts["total"]
    )
    assert order_fact.source_occurrence is definition.order_by_clause.items[0]
    assert order_fact.target_occurrence is definition.select_items[0]
    assert order_fact.aggregate_result_fact is None


def test_malformed_direct_fact_and_readiness_construction_fail_closed(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _grouped_body(satisfying="total > 0", order_items=("status asc",)),
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    group_fact, satisfying_fact, order_fact = result.dependency_facts
    assert result.finalization.state.schema is not None

    malformed_fact_arguments: tuple[dict[str, Any], ...] = (
        {"kind": "group_key_input"},
        {
            "source_occurrence": order_fact.source_occurrence,
        },
        {
            "target_occurrence": satisfying_fact.target_occurrence,
        },
        {
            "target_field": result.finalization.state.schema.fields["total"],
        },
        {"aggregate_result_fact": result.finalization.aggregate_result_facts["total"]},
    )
    for changes in malformed_fact_arguments:
        arguments = {
            "kind": group_fact.kind,
            "source_occurrence": group_fact.source_occurrence,
            "target_occurrence": group_fact.target_occurrence,
            "target_field": group_fact.target_field,
            "aggregate_result_fact": group_fact.aggregate_result_fact,
        }
        arguments.update(changes)
        with pytest.raises(ValueError):
            ProjectRelationClauseDependencyFact(**arguments)

    with pytest.raises(ValueError):
        ProjectRelationClauseDependencyFact(
            kind=ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT,
            source_occurrence=satisfying_fact.source_occurrence,
            target_occurrence=satisfying_fact.target_occurrence,
            target_field=satisfying_fact.target_field,
            aggregate_result_fact=None,
        )
    with pytest.raises(ValueError):
        ProjectRelationClauseDependencyFact(
            kind=ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT,
            source_occurrence=order_fact.source_occurrence,
            target_occurrence=order_fact.target_occurrence,
            target_field=order_fact.target_field,
            aggregate_result_fact=result.finalization.aggregate_result_facts["total"],
        )

    invalid_readiness_arguments: tuple[dict[str, Any], ...] = (
        {"status": "concrete"},
        {"reason": "clauses_ready"},
        {"dependency_facts": result.dependency_facts[:-1]},
        {"limit_present": True},
        {
            "status": ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN,
            "reason": (
                ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION
            ),
        },
    )
    for changes in invalid_readiness_arguments:
        arguments = {
            "definition": definition,
            "finalization": result.finalization,
            "status": result.status,
            "reason": result.reason,
            "dependency_facts": result.dependency_facts,
            "limit_present": False,
        }
        arguments.update(changes)
        with pytest.raises(ValueError):
            ProjectAggregateGroupedClauseReadiness(**arguments)

    for omitted in result.dependency_facts:
        incomplete = tuple(
            fact for fact in result.dependency_facts if fact is not omitted
        )
        with pytest.raises(ValueError):
            ProjectAggregateGroupedClauseReadiness(
                definition=definition,
                finalization=result.finalization,
                status=result.status,
                reason=result.reason,
                dependency_facts=incomplete,
                limit_present=False,
            )
    with pytest.raises(ValueError):
        ProjectAggregateGroupedClauseReadiness(
            definition=definition,
            finalization=result.finalization,
            status=result.status,
            reason=result.reason,
            dependency_facts=(*result.dependency_facts, order_fact),
            limit_present=False,
        )

    _, _, other, _, _ = _candidate_inputs(
        tmp_path / "other",
        _grouped_body(satisfying="total > 0", order_items=("status asc",)),
    )
    assert other.satisfying_clause is not None
    other_name = _name_occurrences(other.satisfying_clause.expression)[0]
    foreign_source = replace(satisfying_fact, source_occurrence=other_name)
    foreign_facts = tuple(
        foreign_source if fact is satisfying_fact else fact
        for fact in result.dependency_facts
    )
    with pytest.raises(ValueError, match="outside"):
        ProjectAggregateGroupedClauseReadiness(
            definition=definition,
            finalization=result.finalization,
            status=result.status,
            reason=result.reason,
            dependency_facts=foreign_facts,
            limit_present=False,
        )


def test_exactly_one_finalizer_and_exact_existing_group_helper_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _grouped_body(),
    )
    original_finalizer = (
        clause_module.build_project_aggregate_grouped_schema_finalization
    )
    original_group_builder = clause_module.build_project_group_key_schema_facts
    calls = {"finalizer": 0, "group_builder": 0}

    def counted_finalizer(**kwargs: Any) -> ProjectAggregateGroupedSchemaFinalization:
        calls["finalizer"] += 1
        return original_finalizer(**kwargs)

    def counted_group_builder(**kwargs: Any) -> ProjectGroupKeySchemaFacts | None:
        calls["group_builder"] += 1
        return original_group_builder(**kwargs)

    monkeypatch.setattr(
        clause_module,
        "build_project_aggregate_grouped_schema_finalization",
        counted_finalizer,
    )
    monkeypatch.setattr(
        clause_module,
        "build_project_group_key_schema_facts",
        counted_group_builder,
    )
    result = _readiness(definition, input_schema, upstream_symbol)

    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert calls == {"finalizer": 1, "group_builder": 1}
    source = inspect.getsource(build_project_aggregate_grouped_clause_readiness)
    assert source.count("build_project_aggregate_grouped_schema_finalization(") == 1
    assert "analyze(" not in source


@pytest.mark.parametrize(
    ("status", "reason"),
    (
        (
            ProjectRelationRowSchemaStatus.UNKNOWN,
            ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        ),
        (
            ProjectRelationRowSchemaStatus.DEFERRED,
            ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
        ),
        (
            ProjectRelationRowSchemaStatus.BLOCKED,
            ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS,
        ),
    ),
)
def test_non_concrete_finalization_is_mirrored_without_clause_inspection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: ProjectRelationRowSchemaStatus,
    reason: ProjectRelationRowSchemaReason,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _grouped_body(
            satisfying="missing > 0",
            order_items=("missing desc",),
            limit="-1",
        ),
    )
    state = ProjectRelationRowSchemaState(
        status=status,
        schema=(
            ProjectRowSchema(fields={}, is_unknown=True)
            if status.name == "UNKNOWN"
            else None
        ),
        reason=reason,
    )
    finalization = ProjectAggregateGroupedSchemaFinalization(
        state=state,
        aggregate_result_facts={},
    )
    monkeypatch.setattr(
        clause_module,
        "build_project_aggregate_grouped_schema_finalization",
        lambda **_kwargs: finalization,
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("clauses were inspected after non-concrete finalization")

    for name in (
        "_retained_evidence",
        "_satisfying_facts",
        "_grouped_order_facts",
        "_no_group_order_reason",
        "_valid_limit",
    ):
        monkeypatch.setattr(clause_module, name, forbidden)

    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.finalization is finalization
    assert result.finalization.state.reason is reason
    assert result.status.value == status.value
    assert result.reason is (
        ProjectAggregateGroupedClauseReadinessReason.SCHEMA_FINALIZATION_NON_CONCRETE
    )
    assert result.dependency_facts == ()
    assert result.limit_present is False


def test_duplicate_output_duplicate_group_key_and_pure_grouping_skip_clauses(
    tmp_path: Path,
) -> None:
    bodies_and_reasons = (
        (
            "query candidate:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        duplicate = status\n"
            "        duplicate = count()\n"
            "    satisfying:\n"
            "        duplicate > 0\n",
            ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
        ),
        (
            "query candidate:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "        users.status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY,
        ),
    )
    for index, (body, nested_reason) in enumerate(bodies_and_reasons):
        _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
            tmp_path / str(index), body
        )
        result = _readiness(definition, input_schema, upstream_symbol)
        assert result.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
        assert result.reason is (
            ProjectAggregateGroupedClauseReadinessReason.SCHEMA_FINALIZATION_NON_CONCRETE
        )
        assert result.finalization.state.reason is nested_reason
        assert result.dependency_facts == ()

    _, _, pure, pure_schema, pure_symbol = _candidate_inputs(
        tmp_path / "pure",
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n",
    )
    pure_result = _readiness(pure, pure_schema, pure_symbol)
    assert pure_result.status is ProjectAggregateGroupedClauseReadinessStatus.DEFERRED
    assert pure_result.reason is (
        ProjectAggregateGroupedClauseReadinessReason.SCHEMA_FINALIZATION_NON_CONCRETE
    )
    assert pure_result.finalization.state.reason is (
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert pure_result.dependency_facts == ()


@pytest.mark.parametrize("relation_kind", ("table", "query"))
def test_group_key_forms_source_order_exact_retained_facts_and_no_ancestry(
    tmp_path: Path,
    relation_kind: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        f"{relation_kind} candidate:\n"
        "    from users\n"
        "    let:\n"
        "        direct = created_at\n"
        "        middle = amount\n"
        "        chained = middle\n"
        "    group by:\n"
        "        status\n"
        "        users.region\n"
        "        direct\n"
        "        chained\n"
        "    select:\n"
        "        status\n"
        "        renamed = users.region\n"
        "        created_at\n"
        "        total = count()\n",
    )
    retained = build_project_group_key_schema_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert isinstance(retained, ProjectGroupKeySchemaFacts)
    monkeypatch.setattr(
        clause_module,
        "build_project_group_key_schema_facts",
        lambda **_kwargs: retained,
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    group_facts = tuple(
        fact
        for fact in result.dependency_facts
        if fact.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT
    )

    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert definition.group_by_clause is not None
    assert result.finalization.state.schema is not None
    assert len(group_facts) == 4
    assert tuple(fact.source_occurrence for fact in group_facts) == (
        definition.group_by_clause.items
    )
    assert tuple(fact.target_occurrence for fact in group_facts) == retained.group_keys
    assert tuple(fact.target_field for fact in group_facts) == tuple(
        fact.input_field for fact in retained.group_keys
    )
    assert tuple(fact.field_identity for fact in retained.group_keys) == (
        "status",
        "region",
        "created_at",
        "amount",
    )
    assert all(fact.aggregate_result_fact is None for fact in group_facts)
    assert "amount" not in result.finalization.state.schema.fields
    assert all(
        not hasattr(fact, "let_ancestry") and not hasattr(fact, "lineage")
        for fact in group_facts
    )


@pytest.mark.parametrize(
    "group_key",
    ("status", "users.status", "key", "chained"),
)
def test_each_direct_group_key_family_is_ready(
    tmp_path: Path,
    group_key: str,
) -> None:
    let_block = (
        "    let:\n        key = status\n        chained = key\n"
        if group_key in {"key", "chained"}
        else ""
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        f"{let_block}"
        "    group by:\n"
        f"        {group_key}\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    fact = result.dependency_facts[0]
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert definition.group_by_clause is not None
    assert isinstance(fact.target_occurrence, ProjectGroupKeyFact)
    assert fact.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT
    assert fact.source_occurrence is definition.group_by_clause.items[0]
    assert fact.target_occurrence.field_identity == "status"


@pytest.mark.parametrize("group_key", ("missing", "wrong.status"))
def test_unavailable_or_wrongly_qualified_group_key_never_produces_clause_facts(
    tmp_path: Path,
    group_key: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        f"        {group_key}\n"
        "    select:\n"
        "        total = count()\n",
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
    assert result.reason is (
        ProjectAggregateGroupedClauseReadinessReason.SCHEMA_FINALIZATION_NON_CONCRETE
    )
    assert result.dependency_facts == ()


def test_satisfying_output_dependencies_are_left_to_right_exact_and_atomic(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        label = status\n"
        "        total = count()\n"
        "    satisfying:\n"
        '        (total > 0) and (label == "open")\n',
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    facts = tuple(
        fact
        for fact in result.dependency_facts
        if fact.kind is ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT
    )
    assert definition.satisfying_clause is not None
    names = _name_occurrences(definition.satisfying_clause.expression)

    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert tuple(fact.source_occurrence for fact in facts) == names
    assert tuple(fact.target_occurrence for fact in facts) == (
        definition.select_items[1],
        definition.select_items[0],
    )
    assert tuple(fact.target_field.name for fact in facts) == ("total", "label")
    assert (
        facts[0].aggregate_result_fact
        is (result.finalization.aggregate_result_facts["total"])
    )
    assert facts[1].aggregate_result_fact is None


@pytest.mark.parametrize(
    ("projection", "predicate", "target_name"),
    (
        ("status", 'status == "open"', "status"),
        ("label = status", 'label == "open"', "label"),
        ("status", "total > 0", "total"),
    ),
)
def test_satisfying_alias_group_key_and_aggregate_target_matrix(
    tmp_path: Path,
    projection: str,
    predicate: str,
    target_name: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        f"        {projection}\n"
        "        total = count()\n"
        "    satisfying:\n"
        f"        {predicate}\n",
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    satisfying = tuple(
        fact
        for fact in result.dependency_facts
        if fact.kind is ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT
    )
    assert len(satisfying) == 1
    assert satisfying[0].target_field.name == target_name
    assert satisfying[0].target_occurrence in definition.select_items


def test_satisfying_bool_literal_has_no_dependency_fact(tmp_path: Path) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _grouped_body(satisfying="true"),
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert tuple(fact.kind for fact in result.dependency_facts) == (
        ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT,
    )


def test_satisfying_first_target_dedupe_retains_first_source_occurrence(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _grouped_body(satisfying="(total > 0) and (total < 10)"),
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    assert definition.satisfying_clause is not None
    names = _name_occurrences(definition.satisfying_clause.expression)
    satisfying = tuple(
        fact
        for fact in result.dependency_facts
        if fact.kind is ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT
    )
    assert len(names) == 2
    assert len(satisfying) == 1
    assert satisfying[0].source_occurrence is names[0]
    assert satisfying[0].target_occurrence is definition.select_items[1]


def test_satisfying_aggregate_wrapped_row_let_matches_selected_output(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = sum(gross)\n"
        "    satisfying:\n"
        "        sum(gross) > 0\n",
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    satisfying = tuple(
        fact
        for fact in result.dependency_facts
        if fact.kind is ProjectRelationClauseDependencyKind.SATISFYING_OUTPUT
    )
    assert len(satisfying) == 1
    assert definition.satisfying_clause is not None
    assert isinstance(definition.satisfying_clause.expression, ComparisonExpr)
    assert isinstance(satisfying[0].source_occurrence, CallExpr)
    assert satisfying[0].source_occurrence is (
        definition.satisfying_clause.expression.left
    )
    assert satisfying[0].target_occurrence is definition.select_items[1]
    assert satisfying[0].target_field.name == "total"
    assert (
        satisfying[0].aggregate_result_fact
        is (result.finalization.aggregate_result_facts["total"])
    )
    assert not hasattr(satisfying[0], "let_ancestry")


@pytest.mark.parametrize(
    ("group_items", "projection", "predicate", "reason"),
    (
        (
            ("status",),
            "status",
            "missing > 0",
            ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY,
        ),
        (
            ("status",),
            "status",
            "amount > 0",
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE,
        ),
        (
            ("status", "region"),
            "status",
            'region == "east"',
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE,
        ),
        (
            ("status",),
            "label = status",
            'status == "open"',
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE,
        ),
        (
            ("status",),
            "status",
            "total",
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        ),
        (
            ("status",),
            "status",
            "total between 0 and 10",
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        ),
        (
            ("status",),
            "status",
            "null",
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        ),
    ),
)
def test_satisfying_failure_classification_has_no_partial_facts(
    tmp_path: Path,
    group_items: tuple[str, ...],
    projection: str,
    predicate: str,
    reason: ProjectAggregateGroupedClauseReadinessReason,
) -> None:
    body = (
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        + "".join(f"        {item}\n" for item in group_items)
        + "    select:\n"
        f"        {projection}\n"
        "        total = count()\n"
        "    satisfying:\n"
        f"        {predicate}\n"
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(tmp_path, body)
    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
    assert result.reason is reason
    assert result.dependency_facts == ()


def test_grouped_order_outputs_row_lets_direction_identity_and_first_dedupe(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        "        region_key = users.region\n"
        "        bucket = region_key\n"
        "    group by:\n"
        "        bucket\n"
        "    select:\n"
        "        renamed = users.region\n"
        "        total = count()\n"
        "    order by:\n"
        "        total desc\n"
        "        bucket asc\n"
        "        renamed desc\n"
        "        total asc\n",
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    order_facts = tuple(
        fact
        for fact in result.dependency_facts
        if fact.kind is ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT
    )

    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert definition.order_by_clause is not None
    assert len(order_facts) == 2
    assert order_facts[0].source_occurrence is definition.order_by_clause.items[0]
    assert order_facts[1].source_occurrence is definition.order_by_clause.items[1]
    assert tuple(item.direction for item in definition.order_by_clause.items) == (
        "desc",
        "asc",
        "desc",
        "asc",
    )
    assert order_facts[0].target_occurrence is definition.select_items[1]
    assert order_facts[0].target_field.name == "total"
    assert (
        order_facts[0].aggregate_result_fact
        is (result.finalization.aggregate_result_facts["total"])
    )
    assert order_facts[1].target_occurrence is definition.select_items[0]
    assert order_facts[1].target_field.name == "renamed"
    assert order_facts[1].aggregate_result_fact is None


def test_grouped_order_row_let_uses_first_selected_identity_in_source_order(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        "        region_key = users.region\n"
        "        bucket = region_key\n"
        "    group by:\n"
        "        bucket\n"
        "    select:\n"
        "        first = region\n"
        "        second = users.region\n"
        "        total = count()\n"
        "    order by:\n"
        "        bucket asc\n",
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    order_facts = tuple(
        fact
        for fact in result.dependency_facts
        if fact.kind is ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT
    )
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert definition.order_by_clause is not None
    assert len(order_facts) == 1
    assert order_facts[0].source_occurrence is definition.order_by_clause.items[0]
    assert order_facts[0].target_occurrence is definition.select_items[0]
    assert order_facts[0].target_field.name == "first"


@pytest.mark.parametrize(
    ("group_items", "order_item", "reason"),
    (
        (
            ("status",),
            "missing desc",
            ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY,
        ),
        (
            ("status", "region"),
            "region asc",
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE,
        ),
        (
            ("status",),
            "amount asc",
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_OUTPUT_REFERENCE,
        ),
        (
            ("status",),
            "sum(amount) desc",
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        ),
        (
            ("status",),
            '"literal" asc',
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        ),
        (
            ("status",),
            "users.status asc",
            ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
        ),
    ),
)
def test_grouped_order_failure_matrix_is_atomic_and_does_not_widen_qualifiers(
    tmp_path: Path,
    group_items: tuple[str, ...],
    order_item: str,
    reason: ProjectAggregateGroupedClauseReadinessReason,
) -> None:
    body = (
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        + "".join(f"        {item}\n" for item in group_items)
        + "    select:\n"
        "        key_output = status\n"
        "        total = count()\n"
        "    order by:\n"
        f"        {order_item}\n"
    )
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(tmp_path, body)
    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
    assert result.reason is reason
    assert result.dependency_facts == ()


def test_no_group_input_order_boundary_absent_valid_and_invalid(
    tmp_path: Path,
) -> None:
    _, _, absent, absent_schema, absent_symbol = _candidate_inputs(
        tmp_path / "absent",
        _aggregate_body(),
    )
    absent_result = _readiness(absent, absent_schema, absent_symbol)
    assert absent_result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert absent_result.dependency_facts == ()

    _, _, valid, valid_schema, valid_symbol = _candidate_inputs(
        tmp_path / "valid",
        _aggregate_body(order_items=("amount desc", "users.status asc")),
    )
    valid_result = _readiness(valid, valid_schema, valid_symbol)
    assert valid_result.status is ProjectAggregateGroupedClauseReadinessStatus.DEFERRED
    assert valid_result.reason is (
        ProjectAggregateGroupedClauseReadinessReason.UNSUPPORTED_CLAUSE_FAMILY
    )
    assert valid_result.dependency_facts == ()
    assert all(
        fact.kind is not ProjectRelationClauseDependencyKind.GROUPED_ORDER_OUTPUT
        for fact in valid_result.dependency_facts
    )

    for index, (order, reason) in enumerate(
        (
            (
                "missing desc",
                ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY,
            ),
            (
                "sum(amount) desc",
                ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION,
            ),
        )
    ):
        _, _, invalid, invalid_schema, invalid_symbol = _candidate_inputs(
            tmp_path / f"invalid-{index}",
            _aggregate_body(order_items=(order,)),
        )
        invalid_result = _readiness(invalid, invalid_schema, invalid_symbol)
        assert invalid_result.status is (
            ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
        )
        assert invalid_result.reason is reason
        assert invalid_result.dependency_facts == ()


@pytest.mark.parametrize(
    "limit",
    (None, "0", "1", "9223372036854775807"),
)
def test_limit_policy_c_accepts_absent_zero_positive_and_maximum(
    tmp_path: Path,
    limit: str | None,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _aggregate_body(limit=limit),
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    assert result.reason is ProjectAggregateGroupedClauseReadinessReason.CLAUSES_READY
    assert result.limit_present is (limit is not None)
    assert result.dependency_facts == ()


@pytest.mark.parametrize(
    "limit",
    ("-1", "true", "1.5", '"1"', "amount", "count()", "1 + 1"),
)
def test_limit_policy_c_rejects_all_non_exact_range_literals_atomically(
    tmp_path: Path,
    limit: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _aggregate_body(limit=limit),
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
    assert result.reason is (
        ProjectAggregateGroupedClauseReadinessReason.INVALID_CLAUSE_EXPRESSION
    )
    assert result.limit_present
    assert result.dependency_facts == ()


def test_later_failures_remove_earlier_facts_and_category_precedence_is_fixed(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path / "order-before-limit",
        _grouped_body(
            satisfying="total > 0",
            order_items=("missing desc",),
            limit="-1",
        ),
    )
    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.UNKNOWN
    assert result.reason is (
        ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
    )
    assert result.dependency_facts == ()

    bodies = (
        _grouped_body(
            satisfying="(amount > 0) and (missing > 0)",
            order_items=("sum(amount) desc",),
            limit="-1",
        ),
        _grouped_body(
            satisfying="(missing > 0) and (amount > 0)",
            order_items=("sum(amount) desc",),
            limit="-1",
        ),
    )
    for index, body in enumerate(bodies):
        _, _, candidate, schema, symbol = _candidate_inputs(
            tmp_path / f"satisfying-{index}", body
        )
        candidate_result = _readiness(candidate, schema, symbol)
        assert candidate_result.reason is (
            ProjectAggregateGroupedClauseReadinessReason.UNAVAILABLE_CLAUSE_DEPENDENCY
        )
        assert candidate_result.dependency_facts == ()


@pytest.mark.parametrize(
    ("missing", "conflicting", "reason"),
    (
        (
            True,
            False,
            ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT,
        ),
        (
            False,
            True,
            ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS,
        ),
        (
            True,
            True,
            ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT,
        ),
    ),
)
def test_missing_and_conflicting_retained_evidence_are_blocked_before_clauses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    missing: bool,
    conflicting: bool,
    reason: ProjectAggregateGroupedClauseReadinessReason,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _grouped_body(
            satisfying="missing > 0",
            order_items=("missing desc",),
            limit="-1",
        ),
    )
    original = clause_module._output_targets

    def malformed_outputs(
        candidate: TableDef | QueryDef,
        finalization: ProjectAggregateGroupedSchemaFinalization,
    ) -> tuple[dict[str, Any], bool, bool]:
        outputs, _, _ = original(candidate, finalization)
        return outputs, missing, conflicting

    monkeypatch.setattr(clause_module, "_output_targets", malformed_outputs)
    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.BLOCKED
    assert result.reason is reason
    assert result.dependency_facts == ()


def test_missing_and_malformed_retained_group_facts_are_distinct_blocked_outcomes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        region\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )
    retained = build_project_group_key_schema_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert isinstance(retained, ProjectGroupKeySchemaFacts)

    monkeypatch.setattr(
        clause_module,
        "build_project_group_key_schema_facts",
        lambda **_kwargs: None,
    )
    missing = _readiness(definition, input_schema, upstream_symbol)
    assert missing.status is ProjectAggregateGroupedClauseReadinessStatus.BLOCKED
    assert missing.reason is (
        ProjectAggregateGroupedClauseReadinessReason.MISSING_REQUIRED_CLAUSE_FACT
    )
    assert missing.dependency_facts == ()

    malformed = ProjectGroupKeySchemaFacts(
        group_keys=tuple(reversed(retained.group_keys)),
        selected_fields=retained.selected_fields,
    )
    monkeypatch.setattr(
        clause_module,
        "build_project_group_key_schema_facts",
        lambda **_kwargs: malformed,
    )
    conflicting = _readiness(definition, input_schema, upstream_symbol)
    assert conflicting.status is ProjectAggregateGroupedClauseReadinessStatus.BLOCKED
    assert conflicting.reason is (
        ProjectAggregateGroupedClauseReadinessReason.CONFLICTING_CLAUSE_FACTS
    )
    assert conflicting.dependency_facts == ()


def test_arbitrary_helper_exception_is_not_swallowed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        _grouped_body(),
    )

    def explode(**_kwargs: Any) -> None:
        raise RuntimeError("sentinel helper failure")

    monkeypatch.setattr(
        clause_module,
        "build_project_group_key_schema_facts",
        explode,
    )
    with pytest.raises(RuntimeError, match="sentinel helper failure"):
        _readiness(definition, input_schema, upstream_symbol)
    helper_source = HELPER_PATH.read_text(encoding="utf-8")
    assert "except Exception" not in helper_source
    assert "except BaseException" not in helper_source


@pytest.mark.parametrize("relation_kind", ("table", "query"))
@pytest.mark.parametrize("upstream_kind", ("source", "relation"))
def test_table_query_source_and_relation_upstream_parity(
    tmp_path: Path,
    relation_kind: str,
    upstream_kind: str,
) -> None:
    if upstream_kind == "source":
        relations = (
            f"{relation_kind} candidate:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
        )
    else:
        relations = (
            "table base:\n"
            "    from users\n"
            "    select:\n"
            "        status\n"
            "        amount\n"
            f"{relation_kind} candidate:\n"
            "    from base\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
        )
    _, semantic_result, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path, relations
    )
    assert semantic_result.model is not None
    result = _readiness(definition, input_schema, upstream_symbol)
    assert result.status is ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
    if upstream_kind == "source":
        assert isinstance(upstream_symbol.definition, SourceDef)
    else:
        assert isinstance(upstream_symbol.definition, TableDef)
        assert result.finalization.state.reason is (
            ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
        )


def test_aggregate_grouped_production_persists_graph_lineage_and_activates_downstream(
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
            "        total = count()\n"
            "query pure_grouping:\n"
            "    from users\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "query downstream:\n"
            "    from grouped\n"
            "    select:\n"
            "        total\n",
        )
    )
    assert semantic_result.model is not None
    assert semantic_result.diagnostics == ()
    model = semantic_result.model
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
        assert graph.status is ProjectRowDependencyGraphStatus.CONCRETE
        assert graph.reason is ProjectRowDependencyGraphReason.DIRECT_SOURCE_CONCRETE
        assert graph.edges
        lineage = model.relation_row_lineages[definition]
        assert lineage.status is ProjectRowLineageStatus.CONCRETE
        assert lineage.reason is ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE
        assert lineage.facts

    pure_state = model.relation_row_schema_states[pure_grouping]
    assert pure_grouping not in model.relation_row_schemas
    assert pure_grouping not in model.relation_aggregate_result_facts
    assert pure_state.status is ProjectRelationRowSchemaStatus.DEFERRED
    assert pure_state.reason is (
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    pure_graph = model.relation_row_dependency_graphs[pure_grouping]
    assert pure_graph.status is ProjectRowDependencyGraphStatus.DEFERRED
    assert pure_graph.reason is (
        ProjectRowDependencyGraphReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert pure_graph.edges == ()
    pure_lineage = model.relation_row_lineages[pure_grouping]
    assert pure_lineage.status is ProjectRowLineageStatus.DEFERRED
    assert pure_lineage.reason is (
        ProjectRowLineageReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert pure_lineage.facts == ()

    downstream = _derived_definition(parse_result, "downstream")
    downstream_state = model.relation_row_schema_states[downstream]
    assert downstream_state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert downstream_state.reason is (
        ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
    )
    downstream_schema = downstream_state.schema
    assert downstream_schema is not None
    assert downstream_schema is model.relation_row_schemas[downstream]
    assert tuple(downstream_schema.fields) == ("total",)
    assert model.relation_row_dependency_graphs[downstream].reason is (
        ProjectRowDependencyGraphReason.RELATION_UPSTREAM_CONCRETE
    )
    assert model.relation_row_dependency_graphs[downstream].edges
    assert model.relation_row_lineages[downstream].reason is (
        ProjectRowLineageReason.RELATION_UPSTREAM_CONCRETE
    )
    assert model.relation_row_lineages[downstream].facts

    serialized = json.dumps(
        project_check_result_to_json_dict(
            parse_result,
            semantic_diagnostics=semantic_result.diagnostics,
        )
    )
    for name in (
        "ProjectRelationClauseDependencyFact",
        "ProjectAggregateGroupedClauseReadiness",
        "group_key_input",
        "satisfying_output",
        "grouped_order_output",
    ):
        assert name not in serialized


def test_private_module_has_no_persistence_diagnostic_or_forbidden_integration() -> (
    None
):
    helper_source = HELPER_PATH.read_text(encoding="utf-8")
    model_source = MODEL_PATH.read_text(encoding="utf-8")
    json_source = (REPO_ROOT / "src/pietto/_project/json_v2.py").read_text(
        encoding="utf-8"
    )
    for forbidden in (
        "ProjectSemanticModel",
        "ProjectRelationRowDependencyEdge(",
        "ProjectRowLineageFact(",
        "Diagnostic(",
        "analyze(",
        "build_ir(",
    ):
        assert forbidden not in helper_source
    assert "aggregate_grouped_clause_facts" not in model_source
    assert "build_project_aggregate_grouped_clause_readiness" not in model_source
    assert "ProjectAggregateGroupedClauseReadiness" not in json_source
    assert project_package.__all__ == ()
    assert "relation_aggregate_grouped_clause_readiness" not in {
        field.name for field in fields(ProjectSemanticModel)
    }


def test_slice8_documentation_exact_allowlist_dirty_and_protected_boundaries() -> None:
    plan = PLAN_PATH.read_text(encoding="utf-8")
    spec = SPEC_PATH.read_text(encoding="utf-8")
    plan_lines = plan.splitlines()
    spec_lines = spec.splitlines()

    assert plan_lines.count("### Slice 8 Gate 2 Bounded Implementation Status") == 1
    assert "## Slice 8 Gate 2 Bounded Implementation Status" not in plan_lines
    assert spec_lines[0] == (
        "# Phase 51 Clause-dependency And Fail-closed Hardening v1"
    )
    for token in (
        "Clause-dependency And Fail-closed Hardening",
        "Strategy B",
        "aggregate_grouped_clause_facts.py",
        "ProjectRelationClauseDependencyKind",
        "ProjectAggregateGroupedClauseReadinessStatus",
        "ProjectAggregateGroupedClauseReadinessReason",
        "ProjectRelationClauseDependencyFact",
        "ProjectAggregateGroupedClauseReadiness",
        "GROUP_KEY_INPUT",
        "SATISFYING_OUTPUT",
        "GROUPED_ORDER_OUTPUT",
        "SCHEMA_FINALIZATION_NON_CONCRETE",
        "UNAVAILABLE_CLAUSE_DEPENDENCY",
        "INVALID_CLAUSE_OUTPUT_REFERENCE",
        "INVALID_CLAUSE_EXPRESSION",
        "UNSUPPORTED_CLAUSE_FAMILY",
        "MISSING_REQUIRED_CLAUSE_FACT",
        "CONFLICTING_CLAUSE_FACTS",
        "Policy C",
        "ordinal support",
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "Slice 9",
        "Slice 10",
        "exact 13-path allowlist",
        "Ruff must remain exactly `0.15.21`",
        "/tmp/pietto-phase51-slice8-gate2-evidence-and-diff.txt",
    ):
        assert token in spec, token
    for path in EXPECTED_GATE2_PATHS:
        assert f"`{path}`" in spec
    assert "The exact final untracked set is:" in spec
    assert '"ruff>=0.16.0"' in PYPROJECT_PATH.read_text(encoding="utf-8")
    assert 'name = "ruff"\nversion = "0.16.0"' in LOCK_PATH.read_text(encoding="utf-8")

    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    dirty_paths = {line[3:] for line in status.stdout.splitlines()}
    assert (
        dirty_paths in (set(), EXPECTED_GATE2_PATHS)
    ) or _phase54_active_gate2_is_active()
    untracked = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert (
        set(untracked.stdout.splitlines()) in (set(), EXPECTED_UNTRACKED_PATHS)
    ) or _phase54_active_gate2_is_active()

    protected_paths = (
        "src/pietto/_project/model.py",
        "src/pietto/_project/aggregate_grouped_schema.py",
        "src/pietto/_project/row_dependency_graph.py",
        "src/pietto/_project/row_lineage.py",
        "src/pietto/_project/let_scope_facts.py",
        "src/pietto/_project/row_expression_schema.py",
        "src/pietto/_project/row_expression_type_facts.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/_project/check.py",
        "src/pietto/_project/__init__.py",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/errors.py",
        "src/pietto/generated",
        "src/pietto/parser_api.py",
        "src/pietto/semantic",
        "grammar/Pietto.g4",
        "pyproject.toml",
        "uv.lock",
    )
    protected = subprocess.run(
        ["git", "diff", "--exit-code", "--", *protected_paths],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert (protected.returncode == 0) or _phase54_active_gate2_is_active()
    assert (protected.stdout == "") or _phase54_active_gate2_is_active()
    assert protected.stderr == ""


def _readiness(
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
) -> ProjectAggregateGroupedClauseReadiness:
    return build_project_aggregate_grouped_clause_readiness(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )


def _candidate_inputs(
    root: Path,
    relations: str,
    *,
    definition_name: str = "candidate",
) -> tuple[
    ProjectParseCheckResult,
    ProjectSemanticResult,
    TableDef | QueryDef,
    ProjectRowSchema,
    ProjectSymbol,
]:
    parse_result, semantic_result = _project_semantic_result(_project(root, relations))
    assert semantic_result.model is not None
    definition = _derived_definition(parse_result, definition_name)
    upstream_symbol = semantic_result.model.relation_resolutions[definition.from_clause]
    upstream_definition = upstream_symbol.definition
    if isinstance(upstream_definition, SourceDef):
        input_schema = semantic_result.model.source_row_schemas[upstream_definition]
    else:
        assert isinstance(upstream_definition, (TableDef, QueryDef))
        input_schema = semantic_result.model.relation_row_schemas[upstream_definition]
    return (
        parse_result,
        semantic_result,
        definition,
        input_schema,
        upstream_symbol,
    )


def _project_semantic_result(
    root: Path,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = check_project_parse_only(root)
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


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
        "    fee: Decimal nullable\n"
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
    raise AssertionError(f"Derived relation not found: {name}")


def _grouped_body(
    *,
    satisfying: str | None = None,
    order_items: tuple[str, ...] = (),
    limit: str | None = None,
) -> str:
    satisfying_block = (
        "" if satisfying is None else f"    satisfying:\n        {satisfying}\n"
    )
    order_block = (
        ""
        if not order_items
        else "    order by:\n" + "".join(f"        {item}\n" for item in order_items)
    )
    limit_clause = "" if limit is None else f"    limit {limit}\n"
    return (
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        f"{satisfying_block}{order_block}{limit_clause}"
    )


def _aggregate_body(
    *,
    order_items: tuple[str, ...] = (),
    limit: str | None = None,
) -> str:
    order_block = (
        ""
        if not order_items
        else "    order by:\n" + "".join(f"        {item}\n" for item in order_items)
    )
    limit_clause = "" if limit is None else f"    limit {limit}\n"
    return (
        "query candidate:\n"
        "    from users\n"
        "    select:\n"
        "        total = count()\n"
        f"{order_block}{limit_clause}"
    )


def _name_occurrences(expression: Expression) -> tuple[NameExpr, ...]:
    if isinstance(expression, NameExpr):
        return (expression,)
    if isinstance(expression, (BinaryExpr, ComparisonExpr)):
        return (
            *_name_occurrences(expression.left),
            *_name_occurrences(expression.right),
        )
    if isinstance(expression, CallExpr):
        return tuple(
            occurrence
            for argument in expression.arguments
            for occurrence in _name_occurrences(argument)
        )
    return ()
