from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from pathlib import Path
import re
from typing import cast

import pytest

import test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation as slice7
from pietto._project import project_completion as completion
from pietto._project import project_joined_aggregation as aggregation
from pietto._project import project_joined_row_filter as row_filter
from pietto._project import project_multifact as multifact
from pietto._project import project_ir_relational_properties as relational
from pietto._project.model import ProjectSemanticResult
from pietto.ast_nodes import DottedNameExpr, QueryDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import EffectiveNullability


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_aggregation.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice9-joined-grouping-aggregate-global-satisfying-risk-linkage-v1.md"
)
SPEC_HEADINGS = (
    "Decision And Live Authority",
    "Admission And Closed Modes",
    "Occurrence-Safe Group Keys",
    "Aggregate Occurrences And Dependencies",
    "Plan-Independent Stage Outputs",
    "Group Protection And Contextual Grain",
    "Fanout And Pairwise Chasm Linkage",
    "Risk Closure Without Repair",
    "Satisfying Namespace And SQL Truth",
    "Historical And Later-Stage Boundary",
    "Differential Compatibility",
    "Exact Changed-Path Closure",
    "Assurance And Publication",
    "Slice 10 Handoff",
)

PROJECT_SOURCE = """shape AccountRow:
    id: Int not null
    dimension_id: Int not null
    metric: Int not null
    label: Text not null
    unique account_key on id
    unique account_dimension_key on dimension_id
shape DimensionRow:
    id: Int not null
    unique dimension_key on id
shape EventRow:
    id: Int not null
    account_id: Int not null
    dimension_id: Int not null
    parent_id: Int not null
    metric: Int nullable
    label: Text not null
    unique event_key on id
shape SignalRow:
    id: Int not null
    dimension_id: Int not null
    metric: Int nullable
    label: Text not null
    unique signal_key on id
source accounts: AccountRow is postgres.table("accounts")
source dimensions: DimensionRow is postgres.table("dimensions")
source events: EventRow is postgres.table("events")
source signals: SignalRow is postgres.table("signals")
relationship account_dimension:
    endpoint account: accounts
    endpoint dimension: dimensions
    on account.dimension_id == dimension.id
relationship account_events:
    endpoint account: accounts
    endpoint event: events
    on account.id == event.account_id
relationship dimension_signals:
    endpoint dimension: dimensions
    endpoint signal: signals
    on dimension.id == signal.dimension_id
relationship event_parent:
    endpoint child: events
    endpoint parent: events
    on child.parent_id == parent.id
query absent_stage:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = accounts.id
query grouped_safe:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where event.metric is not null
    group by:
        accounts.id
    select:
        account_id = accounts.id
        total = sum(event.metric)
        average = avg(event.metric)
        counted = count()
        distinct_labels = count_distinct(event.label)
        minimum = min(event.metric)
        maximum = max(event.metric)
query global_safe:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
        average = avg(event.metric)
        counted = count()
query grouped_let:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.id
        amount = event.metric
    group by:
        key
    select:
        event_id = event.id
        total = sum(amount)
query multi_field_argument:
    from accounts
    inner join dimensions as dimension:
        from accounts
        via account_dimension: account -> dimension
    inner join events as event:
        from accounts
        via account_events: account -> event
    inner join signals as signal:
        from dimension
        via dimension_signals: dimension -> signal
    select:
        total = sum(event.metric + signal.metric)
query duplicate_group_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        account_id
        event.account_id
    select:
        account_id = event.account_id
        total = count()
query distinct_same_spelling_keys:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        accounts.id
        event.id
    select:
        account_id = accounts.id
        event_id = event.id
        total = count()
query unknown_group_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        missing
    select:
        total = count()
query ambiguous_group_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        id
    select:
        total = count()
query computed_let_group_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        computed = event.metric + 1
    group by:
        computed
    select:
        total = count()
query pure_grouping:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
query non_grouped_projection:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        accounts.id
    select:
        account_id = accounts.id
        event_metric = event.metric
        total = count()
query aggregate_errors:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        amount = event.metric
    group by:
        event.id
    select:
        event_id = event.id
        nested = sum(count())
        composed = sum(event.metric) + 1
        wrong_type = sum(event.label)
        wrong_arity = sum(event.metric, accounts.metric)
        sum(event.metric)
        unsupported = min(event.metric + accounts.metric)
        unapproved_let = min(amount)
query wrong_type_only:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.label)
query fanout_risk:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(accounts.metric)
query fanout_absorbed:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(accounts.metric)
query fanout_unrelated_group:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.account_id
    select:
        account_id = event.account_id
        total = sum(accounts.metric)
query repeated_self:
    from events
    inner join events as parent:
        from events
        via event_parent: child -> parent
    group by:
        events.id
    select:
        event_id = events.id
        child_total = sum(events.metric)
        parent_total = sum(parent.metric)
query ambiguous_chasm:
    from accounts
    inner join dimensions as dimension:
        from accounts
        via account_dimension: account -> dimension
    inner join events as event:
        from accounts
        via account_events: account -> event
    inner join signals as signal:
        from dimension
        via dimension_signals: dimension -> signal
    select:
        event_total = sum(event.metric)
        signal_total = sum(signal.metric)
query satisfying_outputs:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        key > 0 and total > 0
query satisfying_aggregate_let:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        amount = accounts.metric
    group by:
        event.id
    select:
        key = event.id
        total = sum(amount)
    satisfying:
        sum(amount) > 0
query satisfying_input_field:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        account_id > 0
query satisfying_unknown_output:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        missing > 0
query satisfying_non_bool:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
        event.label
    select:
        key = event.id
        label = event.label
        total = sum(accounts.metric)
    satisfying:
        label
query satisfying_invalid_bool_operands:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        key and total
query satisfying_unsupported_output:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        unsupported = event.metric
        total = sum(accounts.metric)
    satisfying:
        unsupported > 0
query satisfying_unmatched_aggregate:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    satisfying:
        sum(event.metric) > 0
query global_satisfying:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
    satisfying:
        total > 0
query upstream_filter_blocked:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where missing > 0
    group by:
        event.id
    select:
        event_id = event.id
        total = count()
"""

SINGLE_INPUT_PREFIX = """shape Row:
    id: Int not null
    account_id: Int not null
    metric: Int nullable
    label: Text not null
source rows: Row is postgres.table("rows")
"""


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: ProjectSemanticResult
    completion: completion.ProjectCompletion
    filters: row_filter.ProjectJoinedRowFilterSet
    aggregations: aggregation.ProjectJoinedAggregationSet


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic = slice7._semantic_project(
        tmp_path_factory.mktemp("p63s9") / "project",
        {"main.pietto": PROJECT_SOURCE},
        reverse_creation=False,
    )
    completed = completion.build_project_completion(slice7._phase62(semantic))
    filters = row_filter.build_project_joined_row_filters(completed)
    return _Built(
        semantic=semantic,
        completion=completed,
        filters=filters,
        aggregations=aggregation.build_project_joined_aggregations(filters),
    )


def _result(
    built: _Built,
    name: str,
) -> aggregation.ProjectJoinedAggregationResult:
    matches = tuple(
        result
        for result in built.aggregations.results
        if result.input_filter.entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _error_codes(
    result: aggregation.ProjectJoinedAggregationResult,
) -> tuple[str, ...]:
    return tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )


def test_real_join_fixture_builds_closed_absent_grouped_global_and_upstream_modes(
    built: _Built,
) -> None:
    absent = _result(built, "absent_stage")
    grouped = _result(built, "grouped_safe")
    global_ = _result(built, "global_safe")
    upstream = _result(built, "upstream_filter_blocked")
    assert type(absent) is aggregation.ProjectConcreteJoinedAggregation
    assert type(grouped) is aggregation.ProjectConcreteJoinedAggregation
    assert type(global_) is aggregation.ProjectConcreteJoinedAggregation
    assert type(upstream) is aggregation.ProjectNonConcreteJoinedAggregation
    assert absent.mode is aggregation.ProjectJoinedAggregationMode.ABSENT
    assert grouped.mode is aggregation.ProjectJoinedAggregationMode.GROUPED
    assert global_.mode is aggregation.ProjectJoinedAggregationMode.GLOBAL
    assert upstream.reason is (
        aggregation.ProjectJoinedAggregationNonConcreteReason.UPSTREAM_FILTER_NON_CONCRETE
    )
    assert absent.post_aggregate.input_namespace is absent.input_filter.namespace
    assert upstream.post_aggregate is None


def test_group_keys_preserve_direct_let_duplicate_and_occurrence_identity(
    built: _Built,
) -> None:
    grouped = _result(built, "grouped_safe")
    grouped_let = _result(built, "grouped_let")
    distinct = _result(built, "distinct_same_spelling_keys")
    assert type(grouped) is aggregation.ProjectConcreteJoinedAggregation
    assert type(grouped_let) is aggregation.ProjectConcreteJoinedAggregation
    assert type(distinct) is aggregation.ProjectConcreteJoinedAggregation
    assert len(grouped.group_keys) == 1
    assert type(grouped.group_keys[0].item.key) is DottedNameExpr
    assert grouped.group_keys[0].item.key.parts == ("accounts", "id")
    assert grouped.group_keys[0].value_type is (
        grouped.group_keys[0].field_semantics.scalar_field.value_type
    )

    let_key = grouped_let.group_keys[0]
    assert tuple(type(item) for item in let_key.resolutions) == (
        aggregation.ProjectJoinedLetReferenceResolution,
        aggregation.ProjectScalarReferenceResolution,
    )
    assert let_key.effective_expression is let_key.resolutions[-1].reference.expression
    assert let_key.field_semantics.joined_field.evidence.name == "id"
    assert tuple(key.field_semantics for key in distinct.group_keys) == tuple(
        output.group_key.field_semantics
        for output in distinct.stage_outputs
        if output.role is aggregation.ProjectJoinedStageOutputRole.GROUP_KEY
        and output.group_key is not None
    )
    assert distinct.group_keys[0].field_semantics is not (
        distinct.group_keys[1].field_semantics
    )
    assert (
        distinct.group_keys[0].field_semantics.joined_field.evidence.name
        == distinct.group_keys[1].field_semantics.joined_field.evidence.name
        == "id"
    )

    duplicate = _result(built, "duplicate_group_key")
    assert type(duplicate) is aggregation.ProjectNonConcreteJoinedAggregation
    assert duplicate.reason is (
        aggregation.ProjectJoinedAggregationNonConcreteReason.GROUP_KEY_NON_CONCRETE
    )
    assert tuple(type(item) for item in duplicate.group_key_results) == (
        aggregation.ProjectJoinedGroupKeyOccurrence,
        aggregation.ProjectJoinedGroupKeyIssue,
    )
    issue = duplicate.group_key_results[1]
    assert type(issue) is aggregation.ProjectJoinedGroupKeyIssue
    assert issue.kind is (
        aggregation.ProjectJoinedGroupKeyIssueKind.DUPLICATE_EFFECTIVE_FIELD
    )
    assert issue.duplicate_of is duplicate.group_key_results[0]
    assert _error_codes(duplicate) == ("PIE-S2317",)


@pytest.mark.parametrize(
    ("name", "kind"),
    (
        (
            "unknown_group_key",
            aggregation.ProjectJoinedGroupKeyIssueKind.REFERENCE_NON_CONCRETE,
        ),
        (
            "ambiguous_group_key",
            aggregation.ProjectJoinedGroupKeyIssueKind.REFERENCE_NON_CONCRETE,
        ),
        (
            "computed_let_group_key",
            aggregation.ProjectJoinedGroupKeyIssueKind.COMPUTED_LET_EXPRESSION,
        ),
    ),
)
def test_unknown_ambiguous_and_computed_group_keys_fail_closed(
    built: _Built,
    name: str,
    kind: aggregation.ProjectJoinedGroupKeyIssueKind,
) -> None:
    result = _result(built, name)
    assert type(result) is aggregation.ProjectNonConcreteJoinedAggregation
    assert result.post_aggregate is None
    issue = next(
        item
        for item in result.group_key_results
        if type(item) is aggregation.ProjectJoinedGroupKeyIssue
    )
    assert issue.kind is kind
    assert _error_codes(result)[0] == "PIE-S2102"


def test_pure_grouping_and_non_grouped_projection_keep_current_diagnostics(
    built: _Built,
) -> None:
    pure = _result(built, "pure_grouping")
    non_grouped = _result(built, "non_grouped_projection")
    assert type(pure) is aggregation.ProjectNonConcreteJoinedAggregation
    assert type(non_grouped) is aggregation.ProjectNonConcreteJoinedAggregation
    assert pure.mode is aggregation.ProjectJoinedAggregationMode.GROUPED
    assert _error_codes(pure) == ("PIE-S2320",)
    assert "PIE-S2318" in _error_codes(non_grouped)
    assert pure.post_aggregate is non_grouped.post_aggregate is None


def test_grouped_and_global_aggregate_inventory_types_and_stage_outputs_are_exact(
    built: _Built,
) -> None:
    grouped = _result(built, "grouped_safe")
    global_ = _result(built, "global_safe")
    assert type(grouped) is aggregation.ProjectConcreteJoinedAggregation
    assert type(global_) is aggregation.ProjectConcreteJoinedAggregation
    assert tuple(item.function_name for item in grouped.aggregates) == (
        "sum",
        "avg",
        "count",
        "count_distinct",
        "min",
        "max",
    )
    assert tuple(item.item.alias for item in grouped.aggregates) == (
        "total",
        "average",
        "counted",
        "distinct_labels",
        "minimum",
        "maximum",
    )
    nullability = {
        item.item.alias: item.result_value_type.nullability
        for item in grouped.aggregates
    }
    assert nullability == {
        "total": EffectiveNullability.NULLABLE,
        "average": EffectiveNullability.NULLABLE,
        "counted": EffectiveNullability.NON_NULL,
        "distinct_labels": EffectiveNullability.NON_NULL,
        "minimum": EffectiveNullability.NULLABLE,
        "maximum": EffectiveNullability.NULLABLE,
    }
    assert tuple(
        output.selected_output_ordinal for output in grouped.stage_outputs
    ) == (
        0,
        1,
        2,
        3,
        4,
        5,
        6,
    )
    assert tuple(output.output_name for output in grouped.stage_outputs) == (
        "account_id",
        "total",
        "average",
        "counted",
        "distinct_labels",
        "minimum",
        "maximum",
    )
    assert all(
        grouped.post_aggregate.find_output(output.output_name) == (output,)
        for output in grouped.stage_outputs
    )
    assert grouped.post_aggregate.input_namespace is None

    assert global_.mode is aggregation.ProjectJoinedAggregationMode.GLOBAL
    assert tuple(item.function_name for item in global_.aggregates) == (
        "sum",
        "avg",
        "count",
    )
    assert global_.group_keys == global_.group_protections == ()
    assert global_.post_aggregate.input_namespace is None
    assert all(item.call.arguments for item in global_.aggregates[:2])
    assert global_.aggregates[2].call.arguments == ()
    assert global_.aggregates[2].field_dependencies == ()


def test_approved_let_and_multi_field_aggregate_dependencies_are_complete(
    built: _Built,
) -> None:
    grouped_let = _result(built, "grouped_let")
    multi = _result(built, "multi_field_argument")
    assert type(grouped_let) is aggregation.ProjectConcreteJoinedAggregation
    assert type(multi) is aggregation.ProjectConcreteJoinedAggregation
    let_aggregate = grouped_let.aggregates[0]
    assert let_aggregate.function_name == "sum"
    assert len(let_aggregate.field_dependencies) == 1
    dependency = let_aggregate.field_dependencies[0]
    assert tuple(value.occurrence.binding.name for value in dependency.let_path) == (
        "amount",
    )
    assert dependency.field_semantics.joined_field.evidence.name == "metric"
    assert dependency.field_semantics.introduction_use is (
        grouped_let.group_keys[0].field_semantics.introduction_use
    )

    aggregate = multi.aggregates[0]
    assert tuple(
        dependency.field_semantics.joined_field.evidence.name
        for dependency in aggregate.field_dependencies
    ) == ("metric", "metric")
    assert aggregate.field_dependencies[0].field_semantics is not (
        aggregate.field_dependencies[1].field_semantics
    )
    assert aggregate.field_dependencies[0].reference.expression is not (
        aggregate.field_dependencies[1].reference.expression
    )
    linkage = multi.grain_linkages[0]
    assert len(linkage.argument_factors) == 2
    assert linkage.requirements == ()
    assert linkage.closure.factors == linkage.final_grain.active


def test_nested_composed_arity_type_alias_shape_and_unapproved_let_fail_closed(
    built: _Built,
) -> None:
    result = _result(built, "aggregate_errors")
    assert type(result) is aggregation.ProjectNonConcreteJoinedAggregation
    assert result.reason is (
        aggregation.ProjectJoinedAggregationNonConcreteReason.AGGREGATE_NON_CONCRETE
    )
    issues = tuple(
        item
        for item in result.aggregate_results
        if type(item) is aggregation.ProjectJoinedAggregateIssue
    )
    assert tuple(item.kind for item in issues) == (
        aggregation.ProjectJoinedAggregateIssueKind.NESTED,
        aggregation.ProjectJoinedAggregateIssueKind.COMPOSED,
        aggregation.ProjectJoinedAggregateIssueKind.WRONG_ARGUMENT_TYPE,
        aggregation.ProjectJoinedAggregateIssueKind.WRONG_ARITY,
        aggregation.ProjectJoinedAggregateIssueKind.ALIAS_REQUIRED,
        aggregation.ProjectJoinedAggregateIssueKind.ARGUMENT_EXPRESSION_UNSUPPORTED,
        aggregation.ProjectJoinedAggregateIssueKind.ARGUMENT_EXPRESSION_UNSUPPORTED,
    )
    assert _error_codes(result) == (
        "PIE-S2311",
        "PIE-S2310",
        "PIE-S2314",
        "PIE-S2309",
        "PIE-S2313",
        "PIE-S2315",
        "PIE-S2315",
    )
    assert result.post_aggregate is None


def test_fanout_risk_and_group_key_protection_use_exact_phase62_proofs(
    built: _Built,
) -> None:
    risky = _result(built, "fanout_risk")
    absorbed = _result(built, "fanout_absorbed")
    unrelated = _result(built, "fanout_unrelated_group")
    assert type(risky) is aggregation.ProjectNonConcreteJoinedAggregation
    assert type(absorbed) is aggregation.ProjectConcreteJoinedAggregation
    assert type(unrelated) is aggregation.ProjectNonConcreteJoinedAggregation
    assert risky.reason is (
        aggregation.ProjectJoinedAggregationNonConcreteReason.AGGREGATE_ALGEBRA_REQUIRED
    )
    risk = risky.grain_linkages[0]
    assert risk.final_comparison.status is (
        relational.ProjectIRGrainComparisonStatus.RIGHT_FINER
    )
    assert risk.multiplicity_risks == (
        multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,
    )
    assert risk.requirements == (
        multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,
    )
    assert risk.multiplicity_exposures
    assert all(
        exposure.join in risk.multifact_region.region.joins
        for exposure in risk.multiplicity_exposures
    )
    assert risky.post_aggregate is None

    assert len(absorbed.group_protections) == 1
    protection = absorbed.group_protections[0]
    assert protection.input_properties is (
        absorbed.group_keys[0].field_semantics.input_properties
    )
    assert protection.protected_factors
    assert all(
        determination.status is relational.ProjectIROutputDeterminationStatus.PROVEN
        for determination in protection.determinations
    )
    assert absorbed.grain_linkages[0].combined_seed.factors == (
        absorbed.grain_linkages[0].final_grain.active
    )
    assert absorbed.grain_linkages[0].requirements == ()

    unrelated_protection = unrelated.group_protections[0]
    assert unrelated_protection.protected_factors == ()
    assert all(
        determination.status is relational.ProjectIROutputDeterminationStatus.NOT_PROVEN
        for determination in unrelated_protection.determinations
    )
    assert unrelated.grain_linkages[0].requirements == (
        multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,
    )


def test_repeated_self_bindings_keep_argument_occurrences_and_factors_distinct(
    built: _Built,
) -> None:
    result = _result(built, "repeated_self")
    assert type(result) is aggregation.ProjectConcreteJoinedAggregation
    child, parent = result.aggregates
    assert child.field_dependencies[0].field_semantics is not (
        parent.field_dependencies[0].field_semantics
    )
    assert child.field_dependencies[0].field_semantics.introduction_use is not (
        parent.field_dependencies[0].field_semantics.introduction_use
    )
    child_link, parent_link = result.grain_linkages
    assert child_link.argument_factors != parent_link.argument_factors
    assert child_link.group_protection_factors == (parent_link.group_protection_factors)
    assert (
        child_link.closure.factors
        == parent_link.closure.factors
        == (child_link.final_grain.active)
    )
    assert result.pair_linkages[0].structural is (
        multifact.ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED
    )


def test_independent_fact_branches_retain_ambiguous_winner_free_chasm_evidence(
    built: _Built,
) -> None:
    result = _result(built, "ambiguous_chasm")
    assert type(result) is aggregation.ProjectNonConcreteJoinedAggregation
    assert result.reason is (
        aggregation.ProjectJoinedAggregationNonConcreteReason.AGGREGATE_ALGEBRA_REQUIRED
    )
    assert len(result.grain_linkages) == 2
    assert all(
        linkage.final_comparison.status
        is relational.ProjectIRGrainComparisonStatus.RIGHT_FINER
        for linkage in result.grain_linkages
    )
    pair = result.pair_linkages[0]
    assert pair.grain_comparison.status is (
        relational.ProjectIRGrainComparisonStatus.INCOMPARABLE
    )
    assert pair.common_grain.status is multifact.ProjectCommonGrainStatus.AMBIGUOUS
    assert len(pair.common_grain.common_candidates) >= len(pair.chasm_candidates) >= 2
    assert pair.chasm_candidates == pair.common_grain.candidates
    assert pair.structural is (
        multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
    )
    assert pair.multiplicity_risks == (
        multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,
        multifact.ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION,
    )
    assert pair.requirements == (
        multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,
    )
    assert result.post_aggregate is None
    assert all(
        linkage.aggregate.call is linkage.aggregate.item.expression
        for linkage in result.grain_linkages
    )


def test_satisfying_resolves_exact_group_and_aggregate_outputs_with_sql_truth_law(
    built: _Built,
) -> None:
    result = _result(built, "satisfying_outputs")
    assert type(result) is aggregation.ProjectConcreteJoinedAggregation
    satisfying = result.satisfying
    assert type(satisfying) is aggregation.ProjectJoinedSatisfyingAnalysis
    assert satisfying.status is aggregation.ProjectJoinedSatisfyingStatus.CONCRETE
    assert tuple(
        reference.output.output_name
        for reference in satisfying.references
        if type(reference) is aggregation.ProjectJoinedSatisfyingOutputReference
    ) == ("key", "total")
    assert all(
        any(reference.output is output for output in result.stage_outputs)
        for reference in satisfying.references
        if type(reference) is aggregation.ProjectJoinedSatisfyingOutputReference
    )
    assert tuple(
        (effect.truth, effect.retain_row) for effect in satisfying.retention_effects
    ) == (
        (row_filter.ProjectSQLPredicateTruth.TRUE, True),
        (row_filter.ProjectSQLPredicateTruth.FALSE, False),
        (row_filter.ProjectSQLPredicateTruth.UNKNOWN, False),
    )
    assert row_filter.ProjectSQLPredicateTruth.UNKNOWN != (EffectiveNullability.UNKNOWN)


def test_satisfying_approved_aggregate_let_call_reuses_one_retained_occurrence(
    built: _Built,
) -> None:
    result = _result(built, "satisfying_aggregate_let")
    assert type(result) is aggregation.ProjectConcreteJoinedAggregation
    satisfying = result.satisfying
    assert type(satisfying) is aggregation.ProjectJoinedSatisfyingAnalysis
    aggregate_references = tuple(
        reference
        for reference in satisfying.references
        if type(reference) is aggregation.ProjectJoinedSatisfyingAggregateReference
    )
    assert len(aggregate_references) == 1
    assert aggregate_references[0].aggregate is result.aggregates[0]
    assert aggregate_references[0].expression is not result.aggregates[0].call
    assert aggregate_references[0].aggregate.call is (
        aggregate_references[0].aggregate.item.expression
    )


@pytest.mark.parametrize(
    ("name", "expected_code"),
    (
        ("satisfying_input_field", "PIE-S2325"),
        ("satisfying_unknown_output", "PIE-S2324"),
        ("satisfying_non_bool", "PIE-S2202"),
        ("satisfying_invalid_bool_operands", "PIE-S2105"),
        ("satisfying_unsupported_output", "PIE-S2326"),
        ("satisfying_unmatched_aggregate", "PIE-S2308"),
        ("global_satisfying", "PIE-S2323"),
    ),
)
def test_satisfying_failures_keep_existing_diagnostics_and_no_namespace(
    built: _Built,
    name: str,
    expected_code: str,
) -> None:
    result = _result(built, name)
    assert type(result) is aggregation.ProjectNonConcreteJoinedAggregation
    assert result.post_aggregate is None
    assert type(result.satisfying) is aggregation.ProjectJoinedSatisfyingAnalysis
    assert result.satisfying.status is (
        aggregation.ProjectJoinedSatisfyingStatus.NON_CONCRETE
    )
    assert expected_code in _error_codes(result)
    assert result.satisfying.retention_effects == ()
    if name == "satisfying_unsupported_output":
        assert "PIE-S2318" in _error_codes(result)
        assert result.reason is (
            aggregation.ProjectJoinedAggregationNonConcreteReason.SELECTED_OUTPUT_NON_CONCRETE
        )
    elif name == "global_satisfying":
        assert result.mode is aggregation.ProjectJoinedAggregationMode.GLOBAL
        assert result.reason is (
            aggregation.ProjectJoinedAggregationNonConcreteReason.SATISFYING_NON_CONCRETE
        )


def test_collection_preserves_exact_slice8_order_membership_and_slice7_ledger(
    built: _Built,
) -> None:
    entries_before = built.completion.entries
    assert len(built.aggregations.results) == len(built.filters.results)
    assert all(
        result.input_filter is input_filter
        for result, input_filter in zip(
            built.aggregations.results,
            built.filters.results,
            strict=True,
        )
    )
    assert built.aggregations.filter_set is built.filters
    assert built.filters.completion is built.completion
    assert built.completion.entries is entries_before
    assert all(
        entry.reason
        is completion.ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
        for entry in entries_before
        if type(entry) is completion.ProjectEffectiveOutputTerminal
        and any(result.entry is entry for result in built.filters.results)
    )
    input_filter = built.filters.results[0]
    with pytest.raises(ValueError, match="exact Slice-8 membership"):
        aggregation.build_project_joined_aggregation(
            built.filters,
            replace(input_filter),
        )


def test_evidence_carriers_reject_forged_protection_grain_pair_and_output(
    built: _Built,
) -> None:
    absorbed = _result(built, "fanout_absorbed")
    chasm = _result(built, "ambiguous_chasm")
    assert type(absorbed) is aggregation.ProjectConcreteJoinedAggregation
    assert type(chasm) is aggregation.ProjectNonConcreteJoinedAggregation
    with pytest.raises(ValueError, match="proven STRICT key"):
        replace(absorbed.group_protections[0], protected_factors=())
    with pytest.raises(ValueError, match="exact Phase-62 roots"):
        replace(absorbed.grain_linkages[0], argument_factors=())
    with pytest.raises(ValueError, match="replay exact grain evidence"):
        replace(chasm.pair_linkages[0], chasm_candidates=())
    with pytest.raises(ValueError, match="selected occurrence"):
        replace(absorbed.stage_outputs[0], output_name="forged")


def _single_input_errors(body: str) -> tuple[str, ...]:
    parsed = parse_source(
        SINGLE_INPUT_PREFIX + "query comparison:\n" + body,
        path="single-input-aggregation.pietto",
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    result = analyze(parsed.ast)
    definition = cast(QueryDef, result.model.relation_symbols["comparison"])
    assert definition.name == "comparison"
    return tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )


@pytest.mark.parametrize(
    ("joined_name", "body", "expected"),
    (
        (
            "grouped_safe",
            "    from rows\n"
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        id\n"
            "        total = sum(metric)\n",
            (),
        ),
        (
            "global_safe",
            "    from rows\n    select:\n        total = sum(metric)\n",
            (),
        ),
        (
            "duplicate_group_key",
            "    from rows\n"
            "    group by:\n"
            "        account_id\n"
            "        rows.account_id\n"
            "    select:\n"
            "        account_id\n"
            "        total = count()\n",
            ("PIE-S2317",),
        ),
        (
            "non_grouped_projection",
            "    from rows\n"
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        id\n"
            "        metric\n"
            "        total = count()\n",
            ("PIE-S2318",),
        ),
        (
            "pure_grouping",
            "    from rows\n    group by:\n        id\n    select:\n        id\n",
            ("PIE-S2320",),
        ),
        (
            "wrong_type_only",
            "    from rows\n"
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        id\n"
            "        total = sum(label)\n",
            ("PIE-S2314",),
        ),
        (
            "satisfying_input_field",
            "    from rows\n"
            "    group by:\n"
            "        id\n"
            "    select:\n"
            "        key = id\n"
            "        total = count()\n"
            "    satisfying:\n"
            "        account_id > 0\n",
            ("PIE-S2325",),
        ),
        (
            "global_satisfying",
            "    from rows\n"
            "    select:\n"
            "        total = sum(metric)\n"
            "    satisfying:\n"
            "        total > 0\n",
            ("PIE-S2323",),
        ),
    ),
)
def test_join_free_semantic_decisions_and_diagnostics_remain_compatible(
    built: _Built,
    joined_name: str,
    body: str,
    expected: tuple[str, ...],
) -> None:
    public_errors = _single_input_errors(body)
    joined = _result(built, joined_name)
    assert public_errors == expected
    assert tuple(code for code in _error_codes(joined) if code in expected) == expected
    assert (type(joined) is aggregation.ProjectConcreteJoinedAggregation) is (
        not expected
    )


def test_scope_boundary_has_no_old_fact_forgery_ir_allocation_or_later_stage() -> None:
    source = PRODUCTION.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = tuple(
        alias.name
        for node in ast.walk(tree)
        if type(node) is ast.Import
        for alias in node.names
    ) + tuple(
        node.module or "" for node in ast.walk(tree) if type(node) is ast.ImportFrom
    )
    assert not any(
        name.startswith(("pietto.sql", "pietto.cli", "pyarrow")) for name in imports
    )
    for forbidden in (
        "ProjectAggregateFactJoinLocality(",
        "ProjectMultiFactAlignment(",
        "ProjectModuleRowFieldIdentity(",
        "ProjectGroupedGrainFactorIdentity(",
        "ProjectIRSnapshotScope(",
        "ProjectIROutputValueOccurrence(",
        "build_project_completion(",
        "build_project_joined_row_filters(",
        "WINDOW_EVALUATION",
        "QUALIFY",
        "FINAL_PROJECTION",
        "emit_sql",
        "reaggregate",
        "preaggregate",
        "symmetric_aggregate",
    ):
        assert forbidden not in source
    assert source.count("analyze_project_joined_namespace_expression(") == 1
    assert "ProjectCompletion.entries" not in source
    document = SPEC.read_text(encoding="utf-8")
    assert tuple(re.findall(r"^## (.+)$", document, re.MULTILINE)) == SPEC_HEADINGS
    changed_paths = tuple(
        re.findall(r"^\| `([AM])` \| `([^`]+)` \|$", document, re.MULTILINE)
    )
    assert len(changed_paths) == len(set(changed_paths)) == 8
    assert sum(status == "A" for status, _ in changed_paths) == 3
    assert sum(status == "M" for status, _ in changed_paths) == 5
    assert ("M", "tests/test_phase63_slice8_joined_row_filtering.py") in changed_paths
    normalized = " ".join(document.split()).replace("`", "")
    for evidence in (
        "GLOBAL != empty key",
        "Names are lookup surfaces, not identity",
        "count() has no field dependency and explicitly observes the complete final joined grain",
        "stage output occurrence != final semantic field identity",
        "all determinations are retained and none is selected as a winner",
        "GLOBAL contributes zero group-protection factors",
        "RIGHT_FINER retains every unresolved final factor",
        "CROSS_FACT_MULTIPLICATION",
        "publishes post_aggregate = None",
        "never preaggregates, reaggregates, installs a symmetric aggregate",
        "TRUE -> retain grouped row",
        "Slice-7 ledger entries remain object-identical and JOINED_TAIL_PENDING",
        "production 170 -> 171 and tests 413 -> 414",
        "Slice 10 becomes NEXT / NOT IMPLEMENTED",
        "Slice 10 is not begun here",
    ):
        assert evidence in normalized
