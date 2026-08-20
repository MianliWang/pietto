from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

import pytest

import pietto
import pietto._project as project_package
import pietto._project.aggregate_grouped_schema as aggregate_module
from pietto._project.aggregate_grouped_schema import (
    ProjectAggregateGroupedCandidateAttempt,
    ProjectAggregateGroupedSchemaFinalization,
    ProjectAggregateSchemaFacts,
    ProjectGroupedSchemaFacts,
    build_project_aggregate_grouped_schema_finalization,
    build_project_aggregate_schema_facts,
    build_project_grouped_schema_facts,
)
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectAggregateResultFact,
    ProjectParseCheckResult,
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowFieldNullability,
    ProjectRowResultRole,
    ProjectRowSchema,
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
from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
HELPER_PATH = REPO_ROOT / "src/pietto/_project/aggregate_grouped_schema.py"
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"

NEW_REASONS = {
    "DUPLICATE_GROUP_KEY": "duplicate_group_key",
    "UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT": ("unavailable_aggregate_or_grouped_fact"),
    "INVALID_AGGREGATE_OR_GROUPED_OUTPUT": "invalid_aggregate_or_grouped_output",
    "AGGREGATE_OR_GROUPED_DEFERRED": "aggregate_grouped_deferred",
    "CONFLICTING_AGGREGATE_OR_GROUPED_FACTS": (
        "conflicting_aggregate_or_grouped_facts"
    ),
}

WINDOW_REASONS = {
    "UNAVAILABLE_WINDOW_RESULT_FACT": "unavailable_window_result_fact",
    "INVALID_WINDOW_OUTPUT": "invalid_window_output",
    "WINDOW_RESULT_DEFERRED": "window_result_deferred",
    "CONFLICTING_WINDOW_RESULT_FACTS": "conflicting_window_result_facts",
}

OLD_SCHEMA_REASONS = {
    "DIRECT_SOURCE_CONCRETE": "direct_source_concrete",
    "TABLE_UPSTREAM_CONCRETE": "table_upstream_concrete",
    "RELATION_UPSTREAM_CONCRETE": "relation_upstream_concrete",
    "UNKNOWN_SCHEMA": "unknown_schema",
    "DUPLICATE_OUTPUT_NAME": "duplicate_output_name",
    "DEFERRED_PHASE48_BEHAVIOR": "deferred_phase48_behavior",
    "UNRESOLVED_RELATION_BLOCKED": "unresolved_relation_blocked",
    "CYCLE_BLOCKED": "cycle_blocked",
    "UPSTREAM_UNKNOWN": "upstream_unknown",
    "UPSTREAM_DEFERRED": "upstream_deferred",
    "UPSTREAM_BLOCKED": "upstream_blocked",
}

OLD_DEPENDENCY_ONLY_REASONS = {
    "MISSING_ROW_SCHEMA_STATE": "missing_row_schema_state",
    "MISSING_ROW_SCHEMA": "missing_row_schema",
    "MISSING_UPSTREAM_SCHEMA": "missing_upstream_schema",
}

OLD_LINEAGE_ONLY_REASONS = OLD_DEPENDENCY_ONLY_REASONS | {
    "MISSING_DEPENDENCY_GRAPH": "missing_dependency_graph",
}


def test_exact_four_statuses_and_five_reason_values_are_mirrored() -> None:
    assert {member.name: member.value for member in ProjectRelationRowSchemaStatus} == {
        "CONCRETE": "concrete",
        "UNKNOWN": "unknown",
        "DEFERRED": "deferred",
        "BLOCKED": "blocked",
    }
    assert {
        member.name: member.value for member in ProjectRowDependencyGraphStatus
    } == {
        "CONCRETE": "concrete",
        "UNKNOWN": "unknown",
        "DEFERRED": "deferred",
        "BLOCKED": "blocked",
    }
    assert {member.name: member.value for member in ProjectRowLineageStatus} == {
        "CONCRETE": "concrete",
        "UNKNOWN": "unknown",
        "DEFERRED": "deferred",
        "BLOCKED": "blocked",
    }

    schema_reasons = {
        member.name: member.value for member in ProjectRelationRowSchemaReason
    }
    dependency_reasons = {
        member.name: member.value for member in ProjectRowDependencyGraphReason
    }
    lineage_reasons = {member.name: member.value for member in ProjectRowLineageReason}
    assert schema_reasons == OLD_SCHEMA_REASONS | NEW_REASONS | WINDOW_REASONS
    assert dependency_reasons == (
        OLD_SCHEMA_REASONS | NEW_REASONS | WINDOW_REASONS | OLD_DEPENDENCY_ONLY_REASONS
    )
    assert lineage_reasons == (
        OLD_SCHEMA_REASONS | NEW_REASONS | WINDOW_REASONS | OLD_LINEAGE_ONLY_REASONS
    )
    aligned_reasons = NEW_REASONS | WINDOW_REASONS
    assert {
        name: dependency_reasons[name] for name in aligned_reasons
    } == aligned_reasons
    assert {name: lineage_reasons[name] for name in aligned_reasons} == aligned_reasons
    assert set(schema_reasons.values()) <= set(dependency_reasons.values())
    assert set(schema_reasons.values()) <= set(lineage_reasons.values())

    for reason in ProjectRelationRowSchemaReason:
        assert ProjectRowDependencyGraphReason(reason.value).value == reason.value
        assert ProjectRowLineageReason(reason.value).value == reason.value


def test_structured_attempt_is_frozen_slots_exactly_one_and_preserves_facts(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n    from users\n    select:\n        total = count()\n",
    )
    facts = build_project_aggregate_schema_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert isinstance(facts, ProjectAggregateSchemaFacts)

    success = ProjectAggregateGroupedCandidateAttempt(
        facts=facts,
        failure_reason=None,
    )
    failure = ProjectAggregateGroupedCandidateAttempt(
        facts=None,
        failure_reason=(
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
        ),
    )

    assert tuple(field.name for field in fields(success)) == (
        "facts",
        "failure_reason",
    )
    assert is_dataclass(ProjectAggregateGroupedCandidateAttempt)
    assert hasattr(ProjectAggregateGroupedCandidateAttempt, "__slots__")
    assert not hasattr(success, "__dict__")
    assert success.facts is facts
    assert success.failure_reason is None
    assert failure.facts is None
    with pytest.raises(FrozenInstanceError):
        setattr(success, "facts", None)
    with pytest.raises(ValueError, match="exactly one"):
        ProjectAggregateGroupedCandidateAttempt(facts=None, failure_reason=None)
    with pytest.raises(ValueError, match="exactly one"):
        ProjectAggregateGroupedCandidateAttempt(
            facts=facts,
            failure_reason=(
                ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
            ),
        )
    with pytest.raises(ValueError, match="failure reason"):
        ProjectAggregateGroupedCandidateAttempt(
            facts=None,
            failure_reason=cast(Any, "invalid"),
        )
    for finalization_only_reason in (
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
    ):
        with pytest.raises(ValueError, match="invalid failure reason"):
            ProjectAggregateGroupedCandidateAttempt(
                facts=None,
                failure_reason=finalization_only_reason,
            )

    assert (
        build_project_aggregate_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        == facts
    )

    attempt = aggregate_module._build_project_aggregate_schema_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert attempt.facts is facts or attempt.facts == facts
    assert attempt.failure_reason is None


def test_finalization_carrier_is_frozen_defensive_and_schema_fact_atomic(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    select:\n"
        "        total = sum(amount)\n"
        "        rows = count()\n",
    )
    finalization = _finalize(definition, input_schema, upstream_symbol)
    assert finalization.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert finalization.state.schema is not None
    assert tuple(finalization.state.schema.fields) == ("total", "rows")
    assert tuple(finalization.aggregate_result_facts) == ("total", "rows")
    assert isinstance(finalization.aggregate_result_facts, MappingProxyType)
    assert tuple(field.name for field in fields(finalization)) == (
        "state",
        "aggregate_result_facts",
    )
    assert is_dataclass(ProjectAggregateGroupedSchemaFinalization)
    assert hasattr(ProjectAggregateGroupedSchemaFinalization, "__slots__")
    assert not hasattr(finalization, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(finalization, "aggregate_result_facts", {})
    with pytest.raises(TypeError):
        cast(
            MutableMapping[str, ProjectAggregateResultFact],
            finalization.aggregate_result_facts,
        )["other"] = next(iter(finalization.aggregate_result_facts.values()))

    caller_facts = dict(finalization.aggregate_result_facts)
    copied = ProjectAggregateGroupedSchemaFinalization(
        state=finalization.state,
        aggregate_result_facts=caller_facts,
    )
    caller_facts.clear()
    assert tuple(copied.aggregate_result_facts) == ("total", "rows")

    unknown = _unknown_state(
        ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
    )
    deferred = ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        schema=None,
        reason=ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )
    blocked = ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.BLOCKED,
        schema=None,
        reason=(ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS),
    )
    assert (
        ProjectAggregateGroupedSchemaFinalization(
            state=unknown,
            aggregate_result_facts={},
        ).aggregate_result_facts
        == {}
    )
    assert (
        ProjectAggregateGroupedSchemaFinalization(
            state=deferred,
            aggregate_result_facts={},
        ).aggregate_result_facts
        == {}
    )
    assert (
        ProjectAggregateGroupedSchemaFinalization(
            state=blocked,
            aggregate_result_facts={},
        ).aggregate_result_facts
        == {}
    )

    one_fact = {
        "total": finalization.aggregate_result_facts["total"],
    }
    with pytest.raises(ValueError):
        ProjectAggregateGroupedSchemaFinalization(
            state=finalization.state,
            aggregate_result_facts=one_fact,
        )
    with pytest.raises(ValueError):
        ProjectAggregateGroupedSchemaFinalization(
            state=unknown,
            aggregate_result_facts=finalization.aggregate_result_facts,
        )
    with pytest.raises(ValueError):
        ProjectAggregateGroupedSchemaFinalization(
            state=deferred,
            aggregate_result_facts=finalization.aggregate_result_facts,
        )
    with pytest.raises(ValueError):
        ProjectAggregateGroupedSchemaFinalization(
            state=finalization.state,
            aggregate_result_facts={
                "wrong": finalization.aggregate_result_facts["total"]
            },
        )

    _, _, grouped_definition, grouped_schema, grouped_symbol = _candidate_inputs(
        tmp_path / "grouped",
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )
    grouped = _finalize(grouped_definition, grouped_schema, grouped_symbol)
    assert grouped.state.schema is not None
    key_field = grouped.state.schema.fields["status"]
    key_only_schema = ProjectRowSchema(fields={"status": key_field})
    with pytest.raises(ValueError):
        ProjectAggregateGroupedSchemaFinalization(
            state=ProjectRelationRowSchemaState(
                status=ProjectRelationRowSchemaStatus.CONCRETE,
                schema=key_only_schema,
                reason=ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
            ),
            aggregate_result_facts={},
        )


@pytest.mark.parametrize("relation_kind", ("table", "query"))
def test_unique_direct_expression_let_decimal_and_count_finalize_in_order(
    tmp_path: Path,
    relation_kind: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        f"{relation_kind} candidate:\n"
        "    from users\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        rows = count()\n"
        "        direct = sum(amount)\n"
        "        expression = avg(score * weight)\n"
        "        selected_let = sum(gross)\n"
        "        decimal_total = sum(price + fee)\n",
    )

    attempt = aggregate_module._build_project_aggregate_schema_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert isinstance(attempt.facts, ProjectAggregateSchemaFacts)
    finalization = aggregate_module._finalize_project_aggregate_grouped_candidate(
        definition=definition,
        upstream_symbol=upstream_symbol,
        attempt=attempt,
    )
    assert finalization == _finalize(definition, input_schema, upstream_symbol)
    state = finalization.state
    assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert state.reason is ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
    assert state.schema is not None
    assert not state.schema.is_unknown
    assert tuple(state.schema.fields) == (
        "rows",
        "direct",
        "expression",
        "selected_let",
        "decimal_total",
    )
    assert tuple(finalization.aggregate_result_facts) == tuple(state.schema.fields)
    assert state.schema.fields["rows"].resolved_type == ProjectResolvedType(
        name="Int",
        kind=ProjectResolvedTypeKind.BUILTIN,
    )
    assert state.schema.fields["rows"].nullability is (
        ProjectRowFieldNullability.NON_NULL
    )
    assert state.schema.fields["expression"].resolved_type.name == "Float"
    assert state.schema.fields["decimal_total"].resolved_type == ProjectResolvedType(
        name="Decimal",
        kind=ProjectResolvedTypeKind.BUILTIN,
    )
    for name, field in state.schema.fields.items():
        assert field.result_role is ProjectRowResultRole.AGGREGATE_RESULT
        fact = finalization.aggregate_result_facts[name]
        assert fact.output_name == name
        assert fact.grouped is False
    for selected_result in attempt.facts.selected_results.values():
        output_name = selected_result.field.name
        assert state.schema.fields[output_name] is selected_result.field
        assert finalization.aggregate_result_facts[output_name] is selected_result.fact


@pytest.mark.parametrize("relation_kind", ("table", "query"))
def test_grouped_expression_let_unknown_key_nullability_and_relation_upstream(
    tmp_path: Path,
    relation_kind: str,
) -> None:
    parse_result, semantic_result, definition, input_schema, upstream_symbol = (
        _candidate_inputs(
            tmp_path,
            "table base:\n"
            "    from users\n"
            "    select:\n"
            "        status\n"
            "        region\n"
            "        amount\n"
            "        tax\n"
            f"{relation_kind} candidate:\n"
            "    from base\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        region\n"
            "    select:\n"
            "        region\n"
            "        expression = sum(amount + tax)\n"
            "        selected_let = sum(gross)\n",
        )
    )
    assert semantic_result.model is not None
    base = _derived_definition(parse_result, "base")
    assert input_schema is semantic_result.model.relation_row_schemas[base]
    fields_with_unknown_key = dict(input_schema.fields)
    fields_with_unknown_key["region"] = replace(
        fields_with_unknown_key["region"],
        nullability=ProjectRowFieldNullability.UNKNOWN,
    )

    finalization = _finalize(
        definition,
        ProjectRowSchema(fields=fields_with_unknown_key),
        upstream_symbol,
    )
    group_key_attempt = aggregate_module._build_project_group_key_schema_attempt(
        definition=definition,
        input_schema=ProjectRowSchema(fields=fields_with_unknown_key),
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    grouped_attempt = aggregate_module._build_project_grouped_schema_attempt(
        definition=definition,
        input_schema=ProjectRowSchema(fields=fields_with_unknown_key),
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert group_key_attempt.facts is not None
    assert group_key_attempt.failure_reason is None
    assert grouped_attempt.facts is not None
    assert grouped_attempt.failure_reason is None
    wrapper_facts = build_project_grouped_schema_facts(
        definition=definition,
        input_schema=ProjectRowSchema(fields=fields_with_unknown_key),
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert isinstance(wrapper_facts, ProjectGroupedSchemaFacts)
    assert wrapper_facts == grouped_attempt.facts
    state = finalization.state
    assert state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert state.reason is ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
    assert state.schema is not None
    assert tuple(state.schema.fields) == ("region", "expression", "selected_let")
    assert state.schema.fields["region"].nullability is (
        ProjectRowFieldNullability.UNKNOWN
    )
    assert state.schema.fields["region"].result_role is ProjectRowResultRole.GROUP_KEY
    assert tuple(finalization.aggregate_result_facts) == (
        "expression",
        "selected_let",
    )
    assert all(fact.grouped for fact in finalization.aggregate_result_facts.values())


@pytest.mark.parametrize(
    "relation_body",
    (
        "query candidate:\n"
        "    from users\n"
        "    select:\n"
        "        duplicate = sum(amount)\n"
        "        duplicate = sum(amount)\n",
        "query candidate:\n"
        "    from users\n"
        "    select:\n"
        "        duplicate = sum(amount)\n"
        "        duplicate = avg(score * weight)\n",
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        duplicate = status\n"
        "        duplicate = users.status\n"
        "        total = count()\n",
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        status = count()\n",
    ),
)
def test_all_duplicate_output_families_are_unknown_with_no_winner(
    tmp_path: Path,
    relation_body: str,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        relation_body,
    )
    finalization = _finalize(definition, input_schema, upstream_symbol)

    if definition.group_by_clause is None:
        attempt = aggregate_module._build_project_aggregate_schema_attempt(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
    else:
        attempt = aggregate_module._build_project_grouped_schema_attempt(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
    assert attempt.facts is not None
    assert attempt.failure_reason is None

    _assert_unknown_empty(
        finalization,
        ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME,
    )


def test_duplicate_names_are_case_sensitive_and_do_not_collapse(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    select:\n"
        "        total = count()\n"
        "        Total = count()\n",
    )
    finalization = _finalize(definition, input_schema, upstream_symbol)

    assert finalization.state.status is ProjectRelationRowSchemaStatus.CONCRETE
    assert finalization.state.schema is not None
    assert tuple(finalization.state.schema.fields) == ("total", "Total")
    assert tuple(finalization.aggregate_result_facts) == ("total", "Total")


def test_duplicate_group_key_identity_retains_exact_private_reason(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        users.status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )
    assert (
        build_project_grouped_schema_facts(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        is None
    )

    attempt = aggregate_module._build_project_group_key_schema_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert attempt.facts is None
    assert attempt.failure_reason is ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY

    finalization = _finalize(definition, input_schema, upstream_symbol)
    _assert_unknown_empty(
        finalization,
        ProjectRelationRowSchemaReason.DUPLICATE_GROUP_KEY,
    )


def test_unavailable_and_invalid_failures_are_not_inferred_from_wrapper_none(
    tmp_path: Path,
) -> None:
    _, _, unavailable_definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path / "unavailable",
        "query candidate:\n    from users\n    select:\n        total = sum(amount)\n",
    )
    unknown_fields = dict(input_schema.fields)
    unknown_fields["amount"] = replace(
        unknown_fields["amount"],
        resolved_type=ProjectResolvedType(
            name="<unknown>",
            kind=ProjectResolvedTypeKind.UNKNOWN,
        ),
        nullability=ProjectRowFieldNullability.UNKNOWN,
    )
    unavailable = _finalize(
        unavailable_definition,
        ProjectRowSchema(fields=unknown_fields),
        upstream_symbol,
    )
    unavailable_attempt = aggregate_module._build_project_aggregate_schema_attempt(
        definition=unavailable_definition,
        input_schema=ProjectRowSchema(fields=unknown_fields),
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert unavailable_attempt.facts is None
    assert unavailable_attempt.failure_reason is (
        ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
    )
    _assert_unknown_empty(
        unavailable,
        ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
    )

    _, _, invalid_definition, invalid_schema, invalid_symbol = _candidate_inputs(
        tmp_path / "invalid",
        "query candidate:\n    from users\n    select:\n        count()\n",
    )
    assert (
        build_project_aggregate_schema_facts(
            definition=invalid_definition,
            input_schema=invalid_schema,
            upstream_symbol=invalid_symbol,
            fallback_path="models.pietto",
        )
        is None
    )
    invalid = _finalize(invalid_definition, invalid_schema, invalid_symbol)
    invalid_attempt = aggregate_module._build_project_aggregate_schema_attempt(
        definition=invalid_definition,
        input_schema=invalid_schema,
        upstream_symbol=invalid_symbol,
        fallback_path="models.pietto",
    )
    assert invalid_attempt.facts is None
    assert invalid_attempt.failure_reason is (
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    )
    _assert_unknown_empty(
        invalid,
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
    )

    _, _, invalid_let_definition, invalid_let_schema, invalid_let_symbol = (
        _candidate_inputs(
            tmp_path / "invalid_let",
            "query candidate:\n"
            "    from users\n"
            "    let:\n"
            "        gross = sum(amount)\n"
            "    select:\n"
            "        total = count()\n",
        )
    )
    invalid_let_attempt = aggregate_module._build_project_aggregate_schema_attempt(
        definition=invalid_let_definition,
        input_schema=invalid_let_schema,
        upstream_symbol=invalid_let_symbol,
        fallback_path="models.pietto",
    )
    assert invalid_let_attempt.facts is None
    assert invalid_let_attempt.failure_reason is (
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    )
    assert (
        build_project_aggregate_schema_facts(
            definition=invalid_let_definition,
            input_schema=invalid_let_schema,
            upstream_symbol=invalid_let_symbol,
            fallback_path="models.pietto",
        )
        is None
    )
    _assert_unknown_empty(
        _finalize(invalid_let_definition, invalid_let_schema, invalid_let_symbol),
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
    )

    finalizer_source = inspect.getsource(
        build_project_aggregate_grouped_schema_finalization
    )
    assert "build_project_aggregate_schema_facts(" not in finalizer_source
    assert "build_project_grouped_schema_facts(" not in finalizer_source
    assert "except ValueError" not in finalizer_source


def test_unknown_aggregate_result_nullability_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n    from users\n    select:\n        total = sum(amount)\n",
    )

    monkeypatch.setattr(
        aggregate_module,
        "semantic_projection_aggregate_result_value_type",
        lambda *_: ValueType(
            resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
            nullability=EffectiveNullability.UNKNOWN,
        ),
    )
    attempt = aggregate_module._build_project_aggregate_schema_attempt(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert attempt.facts is None
    assert attempt.failure_reason is (
        ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT
    )
    _assert_unknown_empty(
        _finalize(definition, input_schema, upstream_symbol),
        ProjectRelationRowSchemaReason.UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT,
    )


@pytest.mark.parametrize("grouped", (False, True))
def test_unknown_input_schema_retains_upstream_unknown(
    tmp_path: Path,
    grouped: bool,
) -> None:
    group_clause = "    group by:\n        status\n" if grouped else ""
    key_output = "        status\n" if grouped else ""
    _, _, definition, _, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        f"{group_clause}"
        "    select:\n"
        f"{key_output}"
        "        total = count()\n",
    )
    unknown_schema = ProjectRowSchema(fields={}, is_unknown=True)
    if grouped:
        attempt = aggregate_module._build_project_grouped_schema_attempt(
            definition=definition,
            input_schema=unknown_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        wrapper = build_project_grouped_schema_facts(
            definition=definition,
            input_schema=unknown_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
    else:
        attempt = aggregate_module._build_project_aggregate_schema_attempt(
            definition=definition,
            input_schema=unknown_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        wrapper = build_project_aggregate_schema_facts(
            definition=definition,
            input_schema=unknown_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
    assert attempt.facts is None
    assert attempt.failure_reason is ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
    assert wrapper is None
    _assert_unknown_empty(
        _finalize(definition, unknown_schema, upstream_symbol),
        ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
    )


def test_explicit_future_family_and_controlled_conflict_keep_distinct_reasons(
    tmp_path: Path,
) -> None:
    _, _, deferred_definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path / "deferred",
        "query candidate:\n"
        "    from users\n"
        "    select:\n"
        "        future = min(amount + tax)\n",
    )
    deferred_attempt = aggregate_module._build_project_aggregate_schema_attempt(
        definition=deferred_definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )
    assert deferred_attempt.facts is None
    assert deferred_attempt.failure_reason is (
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    deferred = _finalize(deferred_definition, input_schema, upstream_symbol)
    assert deferred.state == ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        schema=None,
        reason=ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )
    assert deferred.aggregate_result_facts == {}

    _, _, deferred_let_definition, let_schema, let_symbol = _candidate_inputs(
        tmp_path / "deferred_let",
        "query candidate:\n"
        "    from users\n"
        "    let:\n"
        "        chosen = amount\n"
        "    select:\n"
        "        future = min(chosen)\n",
    )
    deferred_let_attempt = aggregate_module._build_project_aggregate_schema_attempt(
        definition=deferred_let_definition,
        input_schema=let_schema,
        upstream_symbol=let_symbol,
        fallback_path="models.pietto",
    )
    assert deferred_let_attempt.facts is None
    assert deferred_let_attempt.failure_reason is (
        ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    deferred_let = _finalize(deferred_let_definition, let_schema, let_symbol)
    assert deferred_let.state == ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        schema=None,
        reason=ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )
    assert deferred_let.aggregate_result_facts == {}

    _, _, grouped_definition, grouped_schema, grouped_symbol = _candidate_inputs(
        tmp_path / "conflict",
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )
    aggregate_item = grouped_definition.select_items[1]
    conflicting_definition = replace(
        grouped_definition,
        select_items=(aggregate_item, aggregate_item),
    )
    conflicting_attempt = aggregate_module._build_project_grouped_schema_attempt(
        definition=conflicting_definition,
        input_schema=grouped_schema,
        upstream_symbol=grouped_symbol,
        fallback_path="models.pietto",
    )
    assert conflicting_attempt.facts is None
    assert conflicting_attempt.failure_reason is (
        ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS
    )
    conflicting = _finalize(
        conflicting_definition,
        grouped_schema,
        grouped_symbol,
    )
    assert conflicting.state == ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.BLOCKED,
        schema=None,
        reason=(ProjectRelationRowSchemaReason.CONFLICTING_AGGREGATE_OR_GROUPED_FACTS),
    )
    assert conflicting.aggregate_result_facts == {}


def test_attempt_reason_precedence_is_independent_of_selected_source_order(
    tmp_path: Path,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path / "aggregate",
        "query candidate:\n"
        "    from users\n"
        "    select:\n"
        "        count()\n"
        "        total = sum(amount)\n",
    )
    unknown_fields = dict(input_schema.fields)
    unknown_fields["amount"] = replace(
        unknown_fields["amount"],
        resolved_type=ProjectResolvedType(
            name="<unknown>",
            kind=ProjectResolvedTypeKind.UNKNOWN,
        ),
    )
    unavailable_schema = ProjectRowSchema(fields=unknown_fields)

    for selected_items in (
        definition.select_items,
        tuple(reversed(definition.select_items)),
    ):
        reordered = replace(definition, select_items=selected_items)
        attempt = aggregate_module._build_project_aggregate_schema_attempt(
            definition=reordered,
            input_schema=unavailable_schema,
            upstream_symbol=upstream_symbol,
            fallback_path="models.pietto",
        )
        assert attempt.facts is None
        assert attempt.failure_reason is (
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
        )
        _assert_unknown_empty(
            _finalize(reordered, unavailable_schema, upstream_symbol),
            ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
        )

    _, _, grouped, grouped_schema, grouped_symbol = _candidate_inputs(
        tmp_path / "grouped",
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "        users.status\n"
        "    select:\n"
        "        status\n"
        "        count()\n",
    )
    grouped_attempt = aggregate_module._build_project_grouped_schema_attempt(
        definition=grouped,
        input_schema=grouped_schema,
        upstream_symbol=grouped_symbol,
        fallback_path="models.pietto",
    )
    assert grouped_attempt.facts is None
    assert grouped_attempt.failure_reason is (
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT
    )
    _assert_unknown_empty(
        _finalize(grouped, grouped_schema, grouped_symbol),
        ProjectRelationRowSchemaReason.INVALID_AGGREGATE_OR_GROUPED_OUTPUT,
    )


def test_finalization_does_not_swallow_arbitrary_value_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n    from users\n    select:\n        total = count()\n",
    )

    def raise_sentinel(**_: object) -> ProjectAggregateGroupedCandidateAttempt:
        raise ValueError("sentinel arbitrary failure")

    monkeypatch.setattr(
        aggregate_module,
        "_build_project_aggregate_schema_attempt",
        raise_sentinel,
    )
    with pytest.raises(ValueError, match="sentinel arbitrary failure"):
        _finalize(definition, input_schema, upstream_symbol)


def test_pure_grouping_is_explicitly_deferred_without_schema_or_facts(
    tmp_path: Path,
) -> None:
    _, semantic_result, definition, input_schema, upstream_symbol = _candidate_inputs(
        tmp_path,
        "query candidate:\n"
        "    from users\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n",
    )
    finalization = _finalize(definition, input_schema, upstream_symbol)

    assert finalization.state == ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        schema=None,
        reason=ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )
    assert finalization.aggregate_result_facts == {}
    assert semantic_result.model is not None
    production_state = semantic_result.model.relation_row_schema_states[definition]
    assert production_state == ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.DEFERRED,
        schema=None,
        reason=ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
    )


def test_aggregate_grouped_production_is_persisted_private_and_downstream_active(
    tmp_path: Path,
) -> None:
    parse_result, semantic_result = _project_semantic_result(
        _project(
            tmp_path,
            "query aggregate_only:\n"
            "    from users\n"
            "    select:\n"
            "        total = sum(amount + tax)\n"
            "query grouped:\n"
            "    from users\n"
            "    group by:\n"
            "        region\n"
            "    select:\n"
            "        region\n"
            "        total = count()\n"
            "query pure_grouping:\n"
            "    from users\n"
            "    group by:\n"
            "        region\n"
            "    select:\n"
            "        region\n"
            "query downstream:\n"
            "    from aggregate_only\n"
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
        (grouped, ("region", "total")),
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
        assert graph.nodes
        assert graph.edges
        lineage = model.relation_row_lineages[definition]
        assert lineage.status is ProjectRowLineageStatus.CONCRETE
        assert lineage.reason is ProjectRowLineageReason.DIRECT_SOURCE_CONCRETE
        assert lineage.facts

    assert pure_grouping not in model.relation_row_schemas
    assert pure_grouping not in model.relation_aggregate_result_facts
    assert model.relation_row_schema_states[pure_grouping] == (
        ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
        )
    )
    pure_graph = model.relation_row_dependency_graphs[pure_grouping]
    assert pure_graph.status is ProjectRowDependencyGraphStatus.DEFERRED
    assert pure_graph.reason is (
        ProjectRowDependencyGraphReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert pure_graph.nodes == ()
    assert pure_graph.edges == ()
    pure_lineage = model.relation_row_lineages[pure_grouping]
    assert pure_lineage.status is ProjectRowLineageStatus.DEFERRED
    assert pure_lineage.reason is ProjectRowLineageReason.AGGREGATE_OR_GROUPED_DEFERRED
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
    assert downstream_schema.fields["total"].result_role is (
        ProjectRowResultRole.ORDINARY_ROW_VALUE
    )
    downstream_graph = model.relation_row_dependency_graphs[downstream]
    assert downstream_graph.status is ProjectRowDependencyGraphStatus.CONCRETE
    assert downstream_graph.reason is (
        ProjectRowDependencyGraphReason.RELATION_UPSTREAM_CONCRETE
    )
    assert downstream_graph.edges
    downstream_lineage = model.relation_row_lineages[downstream]
    assert downstream_lineage.status is ProjectRowLineageStatus.CONCRETE
    assert downstream_lineage.reason is (
        ProjectRowLineageReason.RELATION_UPSTREAM_CONCRETE
    )
    assert downstream_lineage.facts

    document = project_check_result_to_json_dict(
        parse_result,
        semantic_diagnostics=semantic_result.diagnostics,
    )
    serialized = json.dumps(document)
    model_source = MODEL_PATH.read_text(encoding="utf-8")
    module_source = HELPER_PATH.read_text(encoding="utf-8")
    assert "aggregate_grouped_persistence" in model_source
    assert "build_project_aggregate_grouped_persistence(" in model_source
    assert "build_project_aggregate_grouped_schema_finalization" not in model_source
    assert "ProjectSemanticModel" not in module_source
    assert project_package.__all__ == ()
    for name in (
        "ProjectAggregateGroupedCandidateAttempt",
        "ProjectAggregateGroupedSchemaFinalization",
        "build_project_aggregate_grouped_schema_finalization",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
        assert name not in serialized


def _finalize(
    definition: TableDef | QueryDef,
    input_schema: ProjectRowSchema,
    upstream_symbol: ProjectSymbol,
) -> ProjectAggregateGroupedSchemaFinalization:
    return build_project_aggregate_grouped_schema_finalization(
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        fallback_path="models.pietto",
    )


def _unknown_state(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectRelationRowSchemaState:
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        schema=ProjectRowSchema(fields={}, is_unknown=True),
        reason=reason,
    )


def _assert_unknown_empty(
    finalization: ProjectAggregateGroupedSchemaFinalization,
    reason: ProjectRelationRowSchemaReason,
) -> None:
    assert finalization.state == _unknown_state(reason)
    assert finalization.state.schema is not None
    assert finalization.state.schema.is_unknown
    assert finalization.state.schema.fields == {}
    assert finalization.aggregate_result_facts == {}


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
