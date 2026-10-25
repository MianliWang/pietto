from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

import pytest

import _pietto_project_completion_ledger as slice7
from pietto._project import project_completion as completion
from pietto._project import project_joined_aggregation as aggregation
from pietto._project import project_joined_row_filter as row_filter
from pietto._project import project_multifact as multifact
from pietto._project import project_ir_relational_properties as relational
from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto.ast_nodes import DottedNameExpr, QueryDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import EffectiveNullability


PROJECT_SOURCE = """shape AccountRow:
    id: Int
    dimension_id: Int
    metric: Int
    label: Text
    account_key = unique(id)
    account_dimension_key = unique(dimension_id)
shape DimensionRow:
    id: Int
    dimension_key = unique(id)
shape EventRow:
    id: Int
    account_id: Int
    dimension_id: Int
    parent_id: Int
    metric: Int | None
    label: Text
    event_key = unique(id)
shape SignalRow:
    id: Int
    dimension_id: Int
    metric: Int | None
    label: Text
    signal_key = unique(id)
source accounts: AccountRow = postgres.table("accounts")
source dimensions: DimensionRow = postgres.table("dimensions")
source events: EventRow = postgres.table("events")
source signals: SignalRow = postgres.table("signals")
relationship account_dimension(account: AccountRow, dimension: DimensionRow):
    account.dimension_id == dimension.id
relationship account_events(account: AccountRow, event: EventRow):
    account.id == event.account_id
relationship dimension_signals(dimension: DimensionRow, signal: SignalRow):
    dimension.id == signal.dimension_id
relationship event_parent(child: EventRow, parent: EventRow):
    child.parent_id == parent.id
query absent_stage:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        account_id = accounts.id
query grouped_safe:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    where event.metric is not None
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
    let event = events
    inner join event on account_events(accounts, event)
    select:
        total = sum(event.metric)
        average = avg(event.metric)
        counted = count()
query grouped_let:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let key = event.id
    let amount = event.metric
    group by:
        key
    select:
        event_id = event.id
        total = sum(amount)
query multi_field_argument:
    from accounts
    let dimension = dimensions
    inner join dimension on account_dimension(accounts, dimension)
    let event = events
    inner join event on account_events(accounts, event)
    let signal = signals
    inner join signal on dimension_signals(dimension, signal)
    select:
        total = sum(event.metric + signal.metric)
query duplicate_group_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        account_id
        event.account_id
    select:
        account_id = event.account_id
        total = count()
query distinct_same_spelling_keys:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        accounts.id
        event.id
    select:
        account_id = accounts.id
        event_id = event.id
        total = count()
query unknown_group_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        missing
    select:
        total = count()
query ambiguous_group_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        id
    select:
        total = count()
query computed_alias_group_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let computed = event.metric + 1
    let alias = computed
    group by:
        alias
    select:
        total = count()
query computed_both_sides_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let band = accounts.metric > event.metric
    group by:
        band
        accounts.id
    select:
        high = band
        account_id = accounts.id
        total = sum(event.metric)
query computed_fanout_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let same_event = event.id + 0
    group by:
        same_event
    select:
        event_id = same_event
        total = sum(accounts.metric)
query computed_self_key:
    from events
    let parent = events
    inner join parent on event_parent(events, parent)
    let older = events.id > parent.id
    group by:
        older
    select:
        older
        total = count()
query computed_duplicate_key:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let band = accounts.metric > event.metric
    group by:
        band
        band
    select:
        total = count()
query computed_extrema:
    from events
    let parent = events
    inner join parent on event_parent(events, parent)
    let gap = parent.id + events.id * 0
    group by:
        events.id
    select:
        event_id = events.id
        low = min(gap)
        high = max(gap)
query computed_extrema_blocked:
    from events
    let parent = events
    inner join parent on event_parent(events, parent)
    let fixed = 3
    let tag = parent.label
    group by:
        events.id
    select:
        event_id = events.id
        top = max(fixed)
        name = min(tag)
query extremum_fanout_let:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let same_event = event.id + 0
    let measured = accounts.metric + 0
    group by:
        same_event
    select:
        event_id = same_event
        top = max(measured)
query extremum_fanout_field:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let same_event = event.id + 0
    group by:
        same_event
    select:
        event_id = same_event
        top = max(accounts.metric)
query extremum_fanout_constant:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let same_event = event.id + 0
    let constant = 7
    group by:
        same_event
    select:
        event_id = same_event
        top = max(constant)
query pure_grouping:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        event_id = event.id
query non_grouped_projection:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        accounts.id
    select:
        account_id = accounts.id
        event_metric = event.metric
        total = count()
query aggregate_errors:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let amount = event.metric
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
        unapproved_let = min(amount + 1)
query wrong_type_only:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.label)
query fanout_risk:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        total = sum(accounts.metric)
query fanout_absorbed:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(accounts.metric)
query fanout_unrelated_group:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.account_id
    select:
        account_id = event.account_id
        total = sum(accounts.metric)
query repeated_self:
    from events
    let parent = events
    inner join parent on event_parent(events, parent)
    group by:
        events.id
    select:
        event_id = events.id
        child_total = sum(events.metric)
        parent_total = sum(parent.metric)
query ambiguous_chasm:
    from accounts
    let dimension = dimensions
    inner join dimension on account_dimension(accounts, dimension)
    let event = events
    inner join event on account_events(accounts, event)
    let signal = signals
    inner join signal on dimension_signals(dimension, signal)
    select:
        event_total = sum(event.metric)
        signal_total = sum(signal.metric)
query satisfying_outputs:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        key > 0 and total > 0
query satisfying_aggregate_let:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    let amount = accounts.metric
    group by:
        event.id
    select:
        key = event.id
        total = sum(amount)
    having:
        sum(amount) > 0
query satisfying_input_field:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        account_id > 0
query satisfying_unknown_output:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        missing > 0
query satisfying_non_bool:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
        event.label
    select:
        key = event.id
        label = event.label
        total = sum(accounts.metric)
    having:
        label
query satisfying_invalid_bool_operands:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        key and total
query satisfying_cross_family_comparison:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        total > "0"
query satisfying_unsupported_output:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        unsupported = event.metric
        total = sum(accounts.metric)
    having:
        unsupported > 0
query satisfying_unmatched_aggregate:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    group by:
        event.id
    select:
        key = event.id
        total = sum(accounts.metric)
    having:
        sum(event.metric) > 0
query global_satisfying:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    select:
        total = sum(event.metric)
    having:
        total > 0
query upstream_filter_blocked:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)
    where missing > 0
    group by:
        event.id
    select:
        event_id = event.id
        total = count()
"""

SINGLE_INPUT_PREFIX = """shape Row:
    id: Int
    account_id: Int
    metric: Int | None
    label: Text
source rows: Row = postgres.table("rows")
"""


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: ProjectSemanticResult
    completion: completion.ProjectCompletion
    filters: tuple[row_filter.ProjectJoinedRowFilterSet, ...]
    aggregations: tuple[aggregation.ProjectJoinedAggregationSet, ...]


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic = slice7._semantic_project(
        tmp_path_factory.mktemp("joined-grouping") / "project",
        {"main.pietto": PROJECT_SOURCE},
        reverse_creation=False,
    )
    completed = build_project_completed_semantic_result(semantic)
    assert type(completed) is ProjectConcreteCompletedSemanticResult
    aggregations = tuple(
        tail.window_set.aggregation_set
        for tail in completed.effective_outputs.current_tails
    )
    assert aggregations
    expected = tuple(
        owner
        for owner in completed.completion.schedule
        if type(owner.definition) is QueryDef and owner.definition.join_clauses
    )
    actual = tuple(
        result.input_filter.entry.owner
        for values in aggregations
        for result in values.results
    )
    assert len(actual) == len(expected) and expected
    assert all(
        owner is retained for owner, retained in zip(actual, expected, strict=True)
    )
    return _Built(
        semantic=completed.semantic_result,
        completion=completed.completion,
        filters=tuple(values.filter_set for values in aggregations),
        aggregations=aggregations,
    )


def _result(
    built: _Built,
    name: str,
) -> aggregation.ProjectJoinedAggregationResult:
    matches = tuple(
        result
        for values in built.aggregations
        for result in values.results
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
    grouped_key = _field_key(grouped.group_keys[0])
    assert type(grouped_key.item.key) is DottedNameExpr
    assert grouped_key.item.key.parts == ("accounts", "id")
    assert grouped_key.value_type is (
        grouped_key.field_semantics.scalar_field.value_type
    )

    let_key = _field_key(grouped_let.group_keys[0])
    first, second = (_field_key(key) for key in distinct.group_keys)
    assert tuple(type(item) for item in let_key.resolutions) == (
        aggregation.ProjectJoinedLetReferenceResolution,
        aggregation.ProjectScalarReferenceResolution,
    )
    assert let_key.effective_expression is let_key.resolutions[-1].reference.expression
    assert let_key.field_semantics.joined_field.evidence.name == "id"
    assert (first.field_semantics, second.field_semantics) == tuple(
        _field_key(output.group_key).field_semantics
        for output in distinct.stage_outputs
        if output.role is aggregation.ProjectJoinedStageOutputRole.GROUP_KEY
    )
    assert first.field_semantics is not second.field_semantics
    assert (
        first.field_semantics.joined_field.evidence.name
        == second.field_semantics.joined_field.evidence.name
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
            "computed_alias_group_key",
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
    if name == "computed_alias_group_key":
        # S05j admits a key naming its computed LET; an alias of one stays refused.
        assert [
            (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
        ] == [("PIE-S2102", "Unknown field: alias")]


def _field_key(key: object) -> aggregation.ProjectJoinedGroupKeyOccurrence:
    assert type(key) is aggregation.ProjectJoinedGroupKeyOccurrence
    return key


def _protection_root(
    protection: aggregation.ProjectJoinedGroupProtection,
) -> tuple[object, object]:
    return protection.input_properties, protection.introduction_use


def test_computed_key_records_both_join_sides_and_seeds_no_protection(
    built: _Built,
) -> None:
    result = _result(built, "computed_both_sides_key")
    assert type(result) is aggregation.ProjectConcreteJoinedAggregation
    band, account_id = result.group_keys
    assert type(band) is aggregation.ProjectJoinedComputedGroupKeyOccurrence
    assert type(account_id) is aggregation.ProjectJoinedGroupKeyOccurrence
    assert band.let_value.occurrence.binding.name == "band"
    assert band.value_type is band.let_value.value_type
    # The exact JOIN-side occurrences the value reads, in source leaf order.
    accounts_metric, event_metric = band.field_dependencies
    assert accounts_metric.joined_field.evidence.name == "metric"
    assert event_metric.joined_field.evidence.name == "metric"
    assert accounts_metric.introduction_use is (
        account_id.field_semantics.introduction_use
    )
    assert event_metric.introduction_use is not accounts_metric.introduction_use
    # Protection: the accounts side is proven by its direct STRICT key only; the
    # events side is recorded for the computed key and seeds no class at all.
    accounts_side, events_side = result.group_protections
    assert _protection_root(accounts_side) == (
        accounts_metric.input_properties,
        accounts_metric.introduction_use,
    )
    assert _protection_root(events_side) == (
        event_metric.input_properties,
        event_metric.introduction_use,
    )
    assert accounts_side.group_keys == (account_id,)
    assert accounts_side.computed_keys == events_side.computed_keys == (band,)
    assert events_side.group_keys == () and events_side.seed.classes == ()
    assert accounts_side.protected_factors and not events_side.protected_factors
    assert all(
        determination.status is relational.ProjectIROutputDeterminationStatus.NOT_PROVEN
        for determination in events_side.determinations
    )
    # Grain linkage records both computed sides; only proven factors are seeded.
    (linkage,) = result.grain_linkages
    assert set(linkage.computed_key_factors) == {
        *multifact._localized_input_factors(
            grain=accounts_metric.input_properties.grain,
            introduction_use=accounts_metric.introduction_use,
            final_grain=linkage.final_grain,
        ),
        *multifact._localized_input_factors(
            grain=event_metric.input_properties.grain,
            introduction_use=event_metric.introduction_use,
            final_grain=linkage.final_grain,
        ),
    }
    assert set(linkage.group_protection_factors) == set(accounts_side.protected_factors)
    assert linkage.requirements == ()
    (high, account_output, _) = result.stage_outputs
    assert high.role is aggregation.ProjectJoinedStageOutputRole.GROUP_KEY
    assert high.group_key is band and high.output_name == "high"
    assert account_output.group_key is account_id


def test_computed_key_never_protects_against_fanout(built: _Built) -> None:
    """`event.id + 0` is not assumed injective, so the accounts sum fans out."""
    absorbed = _result(built, "fanout_absorbed")
    computed = _result(built, "computed_fanout_key")
    assert type(absorbed) is aggregation.ProjectConcreteJoinedAggregation
    assert type(computed) is aggregation.ProjectNonConcreteJoinedAggregation
    assert computed.reason is (
        aggregation.ProjectJoinedAggregationNonConcreteReason.AGGREGATE_ALGEBRA_REQUIRED
    )
    (key,) = (
        item
        for item in computed.group_key_results
        if type(item) is aggregation.ProjectJoinedComputedGroupKeyOccurrence
    )
    (protection,) = computed.group_protections
    assert protection.computed_keys == (key,) and protection.group_keys == ()
    assert protection.protected_factors == ()
    (linkage,) = computed.grain_linkages
    (events_side,) = key.field_dependencies
    assert set(linkage.computed_key_factors) == set(
        multifact._localized_input_factors(
            grain=events_side.input_properties.grain,
            introduction_use=events_side.introduction_use,
            final_grain=linkage.final_grain,
        )
    )
    assert linkage.computed_key_factors
    assert linkage.group_protection_factors == ()
    assert not set(linkage.computed_key_factors) & set(linkage.combined_seed.factors)
    assert linkage.requirements == (
        multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,
    )
    assert absorbed.grain_linkages[0].requirements == ()
    assert computed.diagnostics == ()


def test_computed_key_keeps_self_join_occurrences_distinct(built: _Built) -> None:
    result = _result(built, "computed_self_key")
    assert type(result) is aggregation.ProjectConcreteJoinedAggregation
    (key,) = result.group_keys
    assert type(key) is aggregation.ProjectJoinedComputedGroupKeyOccurrence
    child, parent = key.field_dependencies
    assert child.joined_field.evidence.name == parent.joined_field.evidence.name
    assert child is not parent
    assert child.introduction_use is not parent.introduction_use
    assert tuple(_protection_root(p) for p in result.group_protections) == (
        (child.input_properties, child.introduction_use),
        (parent.input_properties, parent.introduction_use),
    )
    assert all(
        protection.computed_keys == (key,) and not protection.protected_factors
        for protection in result.group_protections
    )
    (output, _) = result.stage_outputs
    assert output.group_key is key and output.output_name == "older"


def test_repeated_computed_key_is_one_duplicate_without_a_winner(
    built: _Built,
) -> None:
    result = _result(built, "computed_duplicate_key")
    assert type(result) is aggregation.ProjectNonConcreteJoinedAggregation
    first, second = result.group_key_results
    assert type(first) is aggregation.ProjectJoinedComputedGroupKeyOccurrence
    assert type(second) is aggregation.ProjectJoinedGroupKeyIssue
    assert second.kind is (
        aggregation.ProjectJoinedGroupKeyIssueKind.DUPLICATE_EFFECTIVE_FIELD
    )
    assert second.duplicate_of is first
    assert [(d.code, d.message) for d in result.diagnostics] == [
        ("PIE-S2317", "Duplicate GROUP BY key: band")
    ]


def test_computed_key_evidence_rejects_forged_sides(built: _Built) -> None:
    result = _result(built, "computed_both_sides_key")
    assert type(result) is aggregation.ProjectConcreteJoinedAggregation
    band = result.group_keys[0]
    assert type(band) is aggregation.ProjectJoinedComputedGroupKeyOccurrence
    with pytest.raises(ValueError, match="exact LET authority"):
        replace(band, field_dependencies=band.field_dependencies[:1])
    with pytest.raises(ValueError, match="complete exact key evidence"):
        replace(result.group_protections[1], computed_keys=())
    (linkage,) = result.grain_linkages
    with pytest.raises(ValueError, match="exact source order"):
        replace(result, grain_linkages=(replace(linkage, computed_key_factors=()),))
    # The concrete stage re-derives every side's record from the keys: a
    # dropped, reordered or re-membered record is refused, and so is a dropped
    # proving record whose factors the linkage still seeds.
    accounts_side, events_side = result.group_protections
    for forged in (
        (accounts_side,),
        (events_side, accounts_side),
        (replace(accounts_side, computed_keys=()), events_side),
    ):
        with pytest.raises(ValueError, match="cover every group key"):
            replace(result, group_protections=forged)
    with pytest.raises(ValueError, match="exact source order"):
        replace(result, group_protections=(events_side,))


def test_extrema_over_a_joined_let_value_read_its_exact_join_sides(
    built: _Built,
) -> None:
    """A12: MIN/MAX accept one row LET name with JOIN inputs; the argument
    reaches every field occurrence the value reads and the result admits NULL."""
    result = _result(built, "computed_extrema")
    assert type(result) is aggregation.ProjectConcreteJoinedAggregation
    (key,) = result.group_keys
    child_key = _field_key(key)
    low, high = result.aggregates
    assert (low.function_name, high.function_name) == ("min", "max")
    for aggregate in (low, high):
        assert aggregate.argument_analysis is not None
        argument_type = aggregate.argument_analysis.value_type
        assert aggregate.result_value_type.resolved_type == argument_type.resolved_type
        assert aggregate.result_value_type.nullability is EffectiveNullability.NULLABLE
        parent_id, child_id = aggregate.field_dependencies
        path = tuple(value.occurrence.binding.name for value in parent_id.let_path)
        assert path == ("gap",)
        assert child_id.field_semantics.introduction_use is (
            child_key.field_semantics.introduction_use
        )
        assert parent_id.field_semantics.introduction_use is not (
            child_id.field_semantics.introduction_use
        )
        assert parent_id.field_semantics.joined_field.evidence.name == "id"
    assert all(linkage.argument_factors for linkage in result.grain_linkages)


def test_extrema_over_a_joined_let_value_keep_the_field_fanout_law(
    built: _Built,
) -> None:
    """The LET argument links the sides it reads exactly like the field; a
    field-free value links none, so the fan-out is not absorbed either."""
    through_let = _result(built, "extremum_fanout_let")
    direct = _result(built, "extremum_fanout_field")
    constant = _result(built, "extremum_fanout_constant")
    for result in (through_let, direct, constant):
        assert type(result) is aggregation.ProjectNonConcreteJoinedAggregation
        assert result.reason is (
            aggregation.ProjectJoinedAggregationNonConcreteReason.AGGREGATE_ALGEBRA_REQUIRED
        )
        assert result.diagnostics == ()
    (let_linkage,), (field_linkage,) = through_let.grain_linkages, direct.grain_linkages
    assert let_linkage.requirements == field_linkage.requirements != ()
    assert tuple(f.kind for f in let_linkage.argument_factors) == tuple(
        f.kind for f in field_linkage.argument_factors
    )
    (constant_linkage,) = constant.grain_linkages
    assert constant_linkage.argument_factors == ()
    assert constant_linkage.requirements == field_linkage.requirements


def _source_position(text: str) -> tuple[int, int]:
    (line,) = (
        number
        for number, value in enumerate(PROJECT_SOURCE.splitlines(), start=1)
        if text in value
    )
    return line, PROJECT_SOURCE.splitlines()[line - 1].index(text) + 1


def test_extrema_over_a_field_free_joined_let_value_link_no_side(
    built: _Built,
) -> None:
    """A12: `fixed = 3` reads no joined field, so MIN/MAX over it is admitted as
    without JOIN and its argument links no JOIN side; only the Text value keeps
    its type refusal."""
    result = _result(built, "computed_extrema_blocked")
    assert type(result) is aggregation.ProjectNonConcreteJoinedAggregation
    assert result.reason is (
        aggregation.ProjectJoinedAggregationNonConcreteReason.AGGREGATE_NON_CONCRETE
    )
    top, name = result.aggregate_results
    assert type(top) is aggregation.ProjectJoinedAggregateOccurrence
    assert top.field_dependencies == ()
    assert top.result_value_type.nullability is EffectiveNullability.NULLABLE
    assert type(name) is aggregation.ProjectJoinedAggregateIssue
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [
        (
            "PIE-S2314",
            "Aggregate function min expects Int, Float, Decimal, Date, or "
            "Timestamp field argument, got Text",
            *_source_position("min(tag)"),
        ),
    ]


_JOINED_KEY_QUERY = """query computed_key_tail:
    from accounts
    let event = events
    inner join event on account_events(accounts, event)

    let band = accounts.metric > event.metric
    group by:
        band
    select:
        high = band
        total = count()
"""


@pytest.mark.parametrize(
    ("tail", "expected"),
    (
        (
            "        position = row_number() window(\n"
            "            order by\n"
            "                high)\n",
            [("PIE-S2102", "Unknown field: high", 14, 17)],
        ),
        (
            "        position = row_number() window(\n"
            "            partition by\n                high)\n",
            [("PIE-S2102", "Unknown field: high", 14, 17)],
        ),
        (
            "        position = row_number() window(\n"
            "            order by\n"
            "                total)\n"
            "    qualify:\n"
            "        high\n",
            [("PIE-S2332", "Unknown QUALIFY reference: high", 16, 9)],
        ),
        (
            "        position = row_number() window(\n"
            "            order by\n"
            "                total)\n"
            "    qualify:\n"
            "        row_number() window(\n"
            "            order by\n"
            "                high) <= 1\n",
            [("PIE-S2102", "Unknown field: high", 18, 17)],
        ),
        ("    having:\n        high\n    order by:\n        high desc\n", []),
    ),
    ids=("window_order", "window_partition", "qualify", "hidden_window", "ordered"),
)
def test_a_joined_computed_key_output_orders_but_stays_outside_windows(
    tmp_path: Path, tail: str, expected: list[tuple[str, str, int, int]]
) -> None:
    """Grouped ORDER BY and satisfying name the selected key; windows and
    QUALIFY keep their unknown-name refusals with every diagnostic."""
    header = PROJECT_SOURCE.split("query absent_stage:")[0]
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        header + _JOINED_KEY_QUERY + tail, encoding="utf-8"
    )
    parsed = check_project_parse_only(tmp_path)
    assert parsed.ok, parsed.diagnostics
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    offset = header.count("\n")
    assert completed.ok is not expected
    assert [
        (d.code, d.message, d.location.line - offset, d.location.column)
        for d in completed.diagnostics
    ] == expected


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
        _field_key(grouped_let.group_keys[0]).field_semantics.introduction_use
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
        _field_key(absorbed.group_keys[0]).field_semantics.input_properties
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


_UNAVAILABLE = "Project relation semantic completion is unavailable: "


def test_fanout_refusal_names_the_repeating_joins_only_for_its_own_relation(
    tmp_path: Path,
) -> None:
    """Current JOIN refusals name their own repeating inputs; upstream readers stay bare."""

    def query(name: str) -> str:
        start = PROJECT_SOURCE.index(f"query {name}:")
        return PROJECT_SOURCE[start : PROJECT_SOURCE.index("\nquery ", start) + 1]

    header = PROJECT_SOURCE.split("query absent_stage:")[0]
    source = (
        header
        + query("fanout_risk")
        + query("ambiguous_chasm")
        + "query reader:\n    from fanout_risk\n    select:\n        total\n"
        + "query qualified_risk:\n    from accounts\n    let event = events\n"
        "    inner join event on account_events(accounts, event)\n"
        "    let weight = accounts.metric\n    group by:\n        accounts.label\n"
        "    select:\n        label = accounts.label\n        top = max(weight)\n"
        "        rk = rank() window(order by top desc)\n    qualify:\n        rk <= 3\n"
        + query("fanout_risk")
        .replace("fanout_risk", "on_risk")
        .replace("account_events(accounts, event)", "accounts.id == event.account_id")
    )
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(source, encoding="utf-8")
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    )
    assert not completed.ok

    def at(name: str) -> int:
        return source[: source.index(f"query {name}:")].count("\n") + 1

    event = " (an aggregate may read rows repeated by JOIN event; match a unique key of event whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)"
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in completed.diagnostics
    ] == [
        ("PIE-S2333", f"{_UNAVAILABLE}fanout_risk{event}", at("fanout_risk"), 1),
        (
            "PIE-S2333",
            f"{_UNAVAILABLE}ambiguous_chasm (an aggregate may read rows repeated by JOIN event and JOIN signal; match unique keys of event and signal whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
            at("ambiguous_chasm"),
            1,
        ),
        ("PIE-S2333", f"{_UNAVAILABLE}reader", at("reader"), 1),
        ("PIE-S2333", f"{_UNAVAILABLE}qualified_risk{event}", at("qualified_risk"), 1),
        ("PIE-S2333", f"{_UNAVAILABLE}on_risk{event}", at("on_risk"), 1),
    ]


_FANOUT_SHAPES = {
    "orders": ("Order", ("customer_id: Int", "amount: Int")),
    "customers": ("Customer", ("name: Text", "region_id: Int")),
    "regions": ("Region", ("name: Text",)),
    "emps": ("Emp", ("manager_id: Int", "name: Text")),
}
_FANOUT_RELATIONSHIPS = (
    ("order_customer", "order", "orders", "customer", "customers"),
    ("customer_region", "customer", "customers", "region", "regions"),
    ("report_manager", "report", "emps", "manager", "emps"),
    ("order_customer_dup", "order", "orders", "customer", "customers"),
    ("order_customer_twice", "order", "orders", "customer", "customers"),
)
_FANOUT_REPEATED = frozenset({"order_customer_dup", "order_customer_twice"})
_FANOUT_CONDITIONS = {
    "order_customer": "order.customer_id == customer.id",
    "customer_region": "customer.region_id == region.id",
    "report_manager": "report.manager_id == manager.id",
    # An ON that repeats an operand: one equality twice, one field twice.
    "order_customer_dup": (
        "order.customer_id == customer.id and order.customer_id == customer.id"
    ),
    "order_customer_twice": (
        "order.customer_id == customer.id and order.amount == customer.id"
    ),
}
_FANOUT_BINDINGS = {
    "orders": "orders",
    "cust": "customers",
    "reg": "regions",
    "emps": "emps",
    "boss": "emps",
    "c1": "customers",
    "c2": "customers",
}
_CUST = "    let cust = customers\n    {} join cust on "
_VIA_CUST = "order_customer(orders, cust)\n"
_REG = "    let reg = regions\n    inner join reg on "
_VIA_REG = "customer_region(cust, reg)\n"
_SELF = "    let boss = emps\n    inner join boss on report_manager(emps, boss)\n"
_FROM_SIDE = (("cust.name",), ("cname = cust.name", "top = max(orders.amount)"))
_TARGET_SIDE = (("orders.amount",), ("amt = orders.amount", "top = max(cust.id)"))
_FANOUT_CASES: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...], str]] = {
    **{
        f"{kind}_{match}_{side}": (
            "orders",
            (_CUST.format(kind) + text)
            if kind != "cross"
            else "    let cust = customers\n    cross join cust\n",
            groups,
            outputs,
            "",
        )
        for kind, match, text in (
            ("inner", "typed", _VIA_CUST),
            ("left", "typed", _VIA_CUST),
            ("right", "typed", _VIA_CUST),
            ("full", "typed", _VIA_CUST),
            (
                "inner",
                "typed_refinement",
                'order_customer(orders, cust) and cust.name != "x"\n',
            ),
            ("inner", "on", "orders.customer_id == cust.id\n"),
            ("left", "on", "orders.customer_id == cust.id\n"),
            ("cross", "cross", ""),
        )
        for side, (groups, outputs) in (("from", _FROM_SIDE), ("target", _TARGET_SIDE))
    },
    "chain_last": (
        "orders",
        _CUST.format("inner") + _VIA_CUST + _REG + _VIA_REG,
        ("orders.amount",),
        ("amt = orders.amount", "top = max(reg.id)"),
        "",
    ),
    "chain_first": (
        "orders",
        _CUST.format("inner") + _VIA_CUST + _REG + _VIA_REG,
        ("reg.name",),
        ("rname = reg.name", "top = max(orders.amount)"),
        "",
    ),
    "chain_middle": (
        "orders",
        _CUST.format("inner") + _VIA_CUST + _REG + _VIA_REG,
        ("orders.amount",),
        ("amt = orders.amount", "top = max(cust.id)"),
        "",
    ),
    "chain_on_last": (
        "orders",
        _CUST.format("inner") + _VIA_CUST + _REG + "cust.region_id == reg.id\n",
        ("orders.amount",),
        ("amt = orders.amount", "top = max(reg.id)"),
        "",
    ),
    "chain_partly_proven_last": (
        "orders",
        _CUST.format("inner") + _VIA_CUST + _REG + _VIA_REG,
        ("orders.amount",),
        ("amt = orders.amount", "n = count(reg.id)"),
        "orders:proven = unique(customer_id)",
    ),
    "chain_partly_proven_first": (
        "orders",
        _CUST.format("inner") + _VIA_CUST + _REG + _VIA_REG,
        ("reg.name",),
        ("rname = reg.name", "top = max(orders.amount)"),
        "customers:proven = unique(id)",
    ),
    "chain_left_first": (
        "orders",
        _CUST.format("left") + _VIA_CUST + _REG + _VIA_REG,
        ("reg.name",),
        ("rname = reg.name", "top = max(orders.amount)"),
        "",
    ),
    "self_from": (
        "emps",
        _SELF,
        ("boss.name",),
        ("bname = boss.name", "top = max(emps.id)"),
        "",
    ),
    "self_target": (
        "emps",
        _SELF,
        ("emps.name",),
        ("ename = emps.name", "top = max(boss.id)"),
        "",
    ),
    "two_aggregates": (
        "orders",
        _CUST.format("inner") + _VIA_CUST,
        ("cust.name",),
        ("cname = cust.name", "top = max(orders.amount)", "most = max(cust.id)"),
        "",
    ),
    # An `any` filter repeats nothing and its binder is never named.
    "semi_then_via": (
        "orders",
        "    let sr = regions\n"
        "    where any(orders.amount == sr.id for sr in sr)\n"
        + _CUST.format("inner")
        + _VIA_CUST,
        ("cust.name",),
        ("cname = cust.name", "top = max(orders.amount)"),
        "",
    ),
    **{
        f"{name}_{side}": (
            "orders",
            _CUST.format("inner") + f"{relationship}(orders, cust)\n",
            groups,
            outputs,
            "",
        )
        for name, relationship in (
            ("repeated_equality", "order_customer_dup"),
            ("repeated_field", "order_customer_twice"),
        )
        for side, (groups, outputs) in (("from", _FROM_SIDE), ("target", _TARGET_SIDE))
    },
    # Both aliases retain independent occurrences of the same producer.
    "two_joins_same_producer": (
        "orders",
        "".join(
            f"    let {name} = customers\n    inner join {name} on order_customer(orders, {name})\n"
            for name in ("c1", "c2")
        ),
        ("orders.amount",),
        ("amt = orders.amount", "top = max(orders.amount)"),
        "",
    ),
}


def _fanout_source(
    case: tuple[str, str, tuple[str, ...], tuple[str, ...], str],
    declarations: tuple[str, ...] = (),
    groups: tuple[str, ...] = (),
) -> str:
    base, joins, case_groups, outputs, extra = case
    declared = tuple(filter(None, (extra, *declarations)))
    shapes = "".join(
        f"shape {shape}:\n    id: Int\n    uid: Int\n"
        + "".join(f"    {item}\n" for item in fields)
        + "".join(
            f"    {line.split(':', 1)[1]}\n"
            for line in dict.fromkeys(declared)
            if line.split(":", 1)[0] == relation
        )
        + f'source {relation}: {shape} = postgres.table("{relation}")\n'
        for relation, (shape, fields) in _FANOUT_SHAPES.items()
    )
    relationships = "".join(
        f"relationship {name}({left}: {_FANOUT_SHAPES[left_relation][0]}, {right}: {_FANOUT_SHAPES[right_relation][0]}):\n"
        f"    {_FANOUT_CONDITIONS[name]}\n"
        for name, left, left_relation, right, right_relation in _FANOUT_RELATIONSHIPS
        if name not in _FANOUT_REPEATED or f"{name}(" in joins
    )
    return (
        shapes
        + relationships
        + f"query q:\n    from {base}\n{joins}    group by:\n"
        + "".join(f"        {group}\n" for group in (*case_groups, *groups))
        + "    select:\n"
        + "".join(f"        {output}\n" for output in outputs)
    )


def _fanout_check(
    tmp_path: Path, name: str, source: str | dict[str, str]
) -> list[tuple[str, str]]:
    root = tmp_path / name
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    for path, text in (
        {"main.pietto": source} if isinstance(source, str) else source
    ).items():
        (root / path).write_text(text, encoding="utf-8")
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(root))
    )
    return [(d.code, d.message) for d in completed.diagnostics]


@pytest.mark.parametrize("name", _FANOUT_CASES)
def test_every_current_fanout_group_remedy_applied_alone_clears_the_refusal(
    tmp_path: Path, name: str
) -> None:
    """Current typed/ordinary ON, CROSS, chains and repeated uses retain real remedies."""
    case = _FANOUT_CASES[name]
    ((code, message),) = _fanout_check(tmp_path, "refused", _fanout_source(case))
    assert code == "PIE-S2333"
    assert message.startswith(
        f"{_UNAVAILABLE}q (an aggregate may read rows repeated by JOIN "
    )
    assert "declare a unique key" not in message
    # The remedy names the inputs whose unique keys close the refusal; grouping
    # by those keys proves the names here without changing the ON.
    grouped = re.search(
        r"match (?:a unique key|unique keys) of (.+) whose fields are never None in",
        message,
    )
    assert grouped is not None
    names = re.split(r", | and ", grouped.group(1))
    assert names and len(names) == len(set(names))
    declarations = tuple(
        f"{_FANOUT_BINDINGS[item]}:group_key = unique(uid)" for item in names
    )
    groups = tuple(f"{item}.uid" for item in names)
    assert (
        _fanout_check(tmp_path, "group", _fanout_source(case, declarations, groups))
        == []
    )


_DECLARABLE_HEADER = (
    "shape Customer:\n"
    "    id: Int\n"
    "    uid: Int\n"
    "    code: Int\n"
    "    name: Text\n"
    "shape Order:\n"
    "    id: Int\n"
    "    uid: Int\n"
    "    customer_id: Int\n"
    "    amount: Int\n"
    'source customers: Customer = postgres.table("customers")\n'
    'source customers_b: Customer = postgres.table("customers_b")\n'
    'source orders: Order = postgres.table("orders")\n'
)


def _endpoint(kind: str, groups: str, aggregate: str) -> str:
    return (
        f"{kind} bc:\n    from customers\n    select:\n        id = code\n        name\n"
        "query q:\n    from orders\n    let j0 = bc\n"
        "    inner join j0 on orders.customer_id == j0.id\n"
        f"    group by:\n        {groups}\n    select:\n        g = {groups}\n        top = max({aggregate})\n"
    )


def test_fanout_remedies_never_name_an_undeclarable_input(tmp_path: Path) -> None:
    """A UNION input, a query or table relationship endpoint, and an import
    alias: the clause never asks for a key that cannot be declared or for a
    group key that cannot exist, and each remedy it does offer clears it."""

    union = (
        "query su:\n"
        "    union all:\n"
        "        from customers\n"
        "        from customers_b\n"
        "query q:\n"
        "    from orders\n"
        "    let s = su\n"
        "    inner join s on orders.customer_id == s.id\n"
        "    group by:\n"
        "        s.name\n"
        "    select:\n"
        "        n = s.name\n"
        "        top = max(orders.amount)\n"
    )
    bare = f"{_UNAVAILABLE}q (an aggregate may read rows repeated by JOIN "
    for name, body, message in (
        ("union", union, f"{bare}s)"),
        ("query", _endpoint("query", "j0.name", "orders.amount"), f"{bare}j0)"),
        ("table", _endpoint("table", "j0.name", "orders.amount"), f"{bare}j0)"),
    ):
        assert _fanout_check(tmp_path, name, _DECLARABLE_HEADER + body) == [
            ("PIE-S2333", message)
        ]

    target = _endpoint("query", "orders.amount", "j0.id")
    assert _fanout_check(tmp_path, "target", _DECLARABLE_HEADER + target) == [
        (
            "PIE-S2333",
            f"{bare}j0; match a unique key of orders whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
        )
    ]
    with_order = _DECLARABLE_HEADER.replace(
        "    amount: Int\n",
        "    amount: Int\n    group_key = unique(uid)\n",
        1,
    )
    fixed = with_order + target.replace(
        "        orders.amount\n    select",
        "        orders.amount\n        orders.uid\n    select",
    )
    assert _fanout_check(tmp_path, "target_group", fixed) == []

    module = (
        "shape Customer:\n    id: Int\n    uid: Int\n    name: Text\n{}"
        'source customers: Customer = postgres.table("customers")\nexport source customers\n'
    )
    main = (
        'from "a.pietto" import source customers as cs\n'
        "shape Order:\n    id: Int\n    customer_id: Int\n    amount: Int\n"
        'source orders: Order = postgres.table("orders")\n'
        "query q:\n    from orders\n    let cust = cs\n"
        "    inner join cust on orders.customer_id == cust.id\n"
        "    group by:\n        cust.name\n{}    select:\n        n = cust.name\n        top = max(orders.amount)\n"
    )
    assert _fanout_check(
        tmp_path,
        "import",
        {"a.pietto": module.format(""), "main.pietto": main.format("")},
    ) == [
        (
            "PIE-S2333",
            f"{bare}cust; match a unique key of cust whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
        )
    ]
    files = {
        "a.pietto": module.format("    group_key = unique(uid)\n"),
        "main.pietto": main.format("        cust.uid\n"),
    }
    assert _fanout_check(tmp_path, "import_group", files) == []


_NULLING_HEADER = """shape Order:
    id: Int
    customer_id: Int | None
    amount: Int
    rush: Bool
    order_key = unique(id)
shape Customer:
    id: Int
    region_id: Int | None
    vip: Bool
    customer_key = unique(id)
shape Region:
    id: Int
    region_key = unique(id)
shape Payment:
    id: Int
    order_id: Int
    payment_key = unique(id)
source orders: Order = postgres.table("orders")
source customers: Customer = postgres.table("customers")
source regions: Region = postgres.table("regions")
source payments: Payment = postgres.table("payments")
relationship order_customer(orders: Order, customers: Customer):
    orders.customer_id == customers.id
relationship customer_region(customers: Customer, regions: Region):
    customers.region_id == regions.id
relationship payment_order(payments: Payment, orders: Order):
    payments.order_id == orders.id
"""
_RIGHT_C = "    from orders\n    let c = customers\n    right join c on order_customer(orders, c)\n"
_CROSS_R = "    let r = regions\n    cross join r\n"
_BY_ORDER = "    group by orders.id\n    select:\n        oid = orders.id\n"
_BY_PAYMENT = "    group by payments.id\n    select:\n        pid = payments.id\n"
_RIGHT_O = "    from payments\n    let o = orders\n    right join o on payment_order(payments, o)\n"


# Refused shapes (0.1.4 accepted them) with the JOINs and the group-key binding
# their clause names, then admitted shapes whose aggregate never reads a row
# that matches no order, or reads only such rows that a later JOIN's row pins.
_NULLING_CASES = {
    "right_then_left": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    left join r on customer_region(c, r)\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c and JOIN r", "c"),
    ),
    "right_then_cross": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "full_then_cross": (
        "    from orders\n"
        "    let c = customers\n"
        "    full join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "or_reads_both_sides": (
        "    from customers\n"
        "    let r = regions\n"
        "    right join r on customer_region(customers, r)\n"
        "    let w = orders\n"
        "    cross join w\n"
        "    select:\n"
        "        n = count(customers.vip or w.rush)\n",
        ("JOIN r", "r"),
    ),
    "or_true": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    select:\n"
        "        n = count(orders.rush or True)\n",
        ("JOIN c", "c"),
    ),
    "where_or": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where orders.amount > 0 or c.vip\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "where_not_not": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where not (not (orders.id is None))\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "where_not_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where orders.id not in ()\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "where_not_of_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where not (orders.id in ())\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "where_in_empty_is_false": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where (orders.id in ()) == False\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "where_not_in_empty_and": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where orders.id not in () and r.id > 0\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "on_not_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    inner join r on orders.id not in ()\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "let_not_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "\n"
        "    let keep = orders.id not in ()\n"
        "    where keep\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "full_where_not_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    full join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where orders.amount not in ()\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "anti_keeps_unmatched": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let p = payments\n"
        "    where not any(p.order_id == orders.id for p in p)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        ("JOIN c", "c"),
    ),
    "conditional_else_literal": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "\n"
        "    let v = orders.amount if orders.rush else 0\n"
        "    select:\n"
        "        top = max(v)\n",
        ("JOIN c", "c"),
    ),
    "conditional_on_not_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "\n"
        "    let v = 0 if orders.id not in () else orders.amount\n"
        "    select:\n"
        "        top = max(v)\n",
        ("JOIN c", "c"),
    ),
    "many_to_one_from_the_right": (
        "    from payments\n"
        "    let o = orders\n"
        "    right join o on payment_order(payments, o)\n"
        "    let c2 = customers\n"
        "    left join c2 on order_customer(o, c2)\n"
        "    group by payments.id\n"
        "    select:\n"
        "        pid = payments.id\n"
        "        n = count(c2.id)\n",
        ("JOIN o and JOIN c2", "o"),
    ),
    "on_or_from_the_right": (
        "    from payments\n"
        "    let o = orders\n"
        "    right join o on payment_order(payments, o)\n"
        "    let p2 = payments\n"
        "    left join p2 on p2.order_id == o.id or p2.id > 0\n"
        "    group by payments.id\n"
        "    select:\n"
        "        pid = payments.id\n"
        "        n = count(p2.id)\n",
        ("JOIN o and JOIN p2", "o"),
    ),
    "same_source_semi_removes_orphans": (
        "    from payments\n"
        "    let o = orders\n"
        "    right join o on payment_order(payments, o)\n"
        "    let p2 = payments\n"
        "    where any(payment_order(p2, o) for p2 in p2)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by payments.id\n"
        "    select:\n"
        "        pid = payments.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "same_source_full_semi_removes_orphans": (
        "    from payments\n"
        "    let o = orders\n"
        "    full join o on payment_order(payments, o)\n"
        "    let p2 = payments\n"
        "    where any(payment_order(p2, o) for p2 in p2)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by payments.id\n"
        "    select:\n"
        "        pid = payments.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "same_source_later_on_still_removes_orphans": (
        "    from payments\n"
        "    let o = orders\n"
        "    right join o on payment_order(payments, o)\n"
        "    let p2 = payments\n"
        "    where any(payment_order(p2, o) and p2.id > 0 for p2 in p2)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by payments.id\n"
        "    select:\n"
        "        pid = payments.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "same_source_anti_keeps_orphans": (
        "    from payments\n"
        "    let o = orders\n"
        "    right join o on payment_order(payments, o)\n"
        "    let p2 = payments\n"
        "    where not any(payment_order(p2, o) for p2 in p2)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by payments.id\n"
        "    select:\n"
        "        pid = payments.id\n"
        "        n = count(r.id)\n",
        ("JOIN o", "o"),
    ),
    "same_source_extra_on_keeps_orphans": (
        "    from payments\n"
        "    let o = orders\n"
        "    right join o on payment_order(payments, o) and o.rush\n"
        "    let p2 = payments\n"
        "    where any(payment_order(p2, o) for p2 in p2)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by payments.id\n"
        "    select:\n"
        "        pid = payments.id\n"
        "        n = count(r.id)\n",
        ("JOIN o", "o"),
    ),
    "strict_argument": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    select:\n"
        "        n = count(orders.id)\n",
        None,
    ),
    "full_strict_argument": (
        "    from orders\n"
        "    let c = customers\n"
        "    full join c on order_customer(orders, c)\n"
        "    select:\n"
        "        n = count(orders.amount)\n",
        None,
    ),
    "grouped_by_the_null_extended_key": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(c.id)\n",
        None,
    ),
    "or_of_one_side": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    select:\n"
        "        n = count(orders.rush or orders.rush)\n",
        None,
    ),
    "coalesce_of_two_left_inputs": (
        "    from orders\n"
        "    let p = payments\n"
        "    inner join p on payment_order(p, orders)\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "\n"
        "    let v = coalesce(p.id, orders.amount)\n"
        "    select:\n"
        "        top = max(v)\n",
        None,
    ),
    "let_extremum": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "\n"
        "    let amt = orders.amount * 2\n"
        "    select:\n"
        "        top = max(amt)\n",
        None,
    ),
    "conditional_of_null_branches": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "\n"
        "    let v = orders.amount if orders.rush else orders.amount + 1\n"
        "    select:\n"
        "        top = max(v)\n",
        None,
    ),
    "conditional_else_unmatched": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let p = payments\n"
        "    left join p on payment_order(p, orders)\n"
        "\n"
        "    let v = 1 if orders.rush else p.id\n"
        "    select:\n"
        "        top = max(v)\n",
        None,
    ),
    "conditional_on_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "\n"
        "    let v = 0 if orders.id in () else orders.amount\n"
        "    select:\n"
        "        top = max(v)\n",
        None,
    ),
    "inner_from_the_left": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let p = payments\n"
        "    inner join p on payment_order(p, orders)\n"
        "    select:\n"
        "        n = count(p.id)\n",
        None,
    ),
    "left_from_the_left": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let p = payments\n"
        "    left join p on payment_order(p, orders)\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(p.id)\n",
        None,
    ),
    "full_from_the_left": (
        "    from orders\n"
        "    let c = customers\n"
        "    full join c on order_customer(orders, c)\n"
        "    let p = payments\n"
        "    full join p on payment_order(p, orders)\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(p.id)\n",
        None,
    ),
    "inner_on_from_the_left": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let p = payments\n"
        "    inner join p on p.order_id == orders.id\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(p.id)\n",
        None,
    ),
    "right_on_the_left": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let p = payments\n"
        "    right join p on p.order_id == orders.id\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by orders.id, p.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        pid = p.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "semi_removes_unmatched": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let p = payments\n"
        "    where any(payment_order(p, orders) for p in p)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "where_removes_unmatched": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where orders.id is not None\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "where_not_is_null": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where not (orders.id is None)\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "where_not_or": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where not (orders.id is None or c.region_id is None)\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "where_in": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where orders.id in (1, 2)\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "where_between": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where 1 <= orders.amount <= 10\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "where_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where orders.id in ()\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "where_not_of_not_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "    where not (orders.id not in ())\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "on_in_empty": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    inner join r on orders.id in ()\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "where_let_condition": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let r = regions\n"
        "    cross join r\n"
        "\n"
        "    let known = orders.id is not None\n"
        "    where known\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(r.id)\n",
        None,
    ),
    "left_from_the_right": (
        "    from orders\n"
        "    let c = customers\n"
        "    right join c on order_customer(orders, c)\n"
        "    let o2 = orders\n"
        "    left join o2 on order_customer(o2, c)\n"
        "    group by orders.id\n"
        "    select:\n"
        "        oid = orders.id\n"
        "        n = count(o2.id)\n",
        None,
    ),
    "on_key_from_the_right": (
        "    from payments\n"
        "    let o = orders\n"
        "    right join o on payment_order(payments, o)\n"
        "    let p2 = payments\n"
        "    left join p2 on p2.order_id == o.id\n"
        "    group by payments.id\n"
        "    select:\n"
        "        pid = payments.id\n"
        "        n = count(p2.id)\n",
        None,
    ),
}


def test_a_null_extended_join_side_proves_nothing_the_aggregate_may_read(
    tmp_path: Path,
) -> None:
    """A RIGHT or FULL JOIN keeps each right row that matches no left row beside
    a left side NULL-extended in every input, so with NULL as a value its
    at-most-one match proves nothing there: a group key of the NULL-extended
    side or an argument that is not NULL on such a row (`or` over both sides or
    with a literal, a conditional whose else branch is a literal, WHERE with
    `or` or `not (not ...)`, `not any`, a later JOIN that may match such a row
    more than once) no longer hides a repeated row; nor does an empty list, which
    is never NULL: `not in ()` is TRUE there in a WHERE or ON (also through
    `not`, `and`, `== False` or a LET) and as a condition. The match still
    proves an aggregate that never reads such a row: its argument is NULL when
    the left side is (`or` of one side, `coalesce` of two left inputs, a LET,
    a conditional with NULL branches or whose condition, such as `in ()`, is
    never TRUE), WHERE is never TRUE there (`is not None`, `not (... is None)`,
    `in`, `between`, `in ()`, a LET condition), or a later JOIN or `any` drops
    it (INNER, `any`, RIGHT) or NULL-extends what it reads (LEFT, FULL). It also
    proves one that reads only such rows holding a row of a later JOIN whose
    relationship or `on` equality matches a key of the right input."""

    source = _NULLING_HEADER + "".join(
        f"query {name}:\n{body}" for name, (body, _) in _NULLING_CASES.items()
    )
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(source, encoding="utf-8")
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    )
    lines = source.splitlines()
    actual = [
        (d.code, d.message, d.location.line, d.location.column)
        for d in completed.diagnostics
    ]
    expected = [
        (
            "PIE-S2333",
            f"{_UNAVAILABLE}{name} (an aggregate may read rows repeated by "
            f"{refusal[0]}; match a unique key of {refusal[1]} whose fields are "
            "never None in `on` with a relationship call, use `any(...)` for an "
            "input that only filters rows, or aggregate in a separate query first)",
            lines.index(f"query {name}:") + 1,
            1,
        )
        for name, (_, refusal) in _NULLING_CASES.items()
        if refusal is not None
    ]

    if actual != expected:
        pytest.fail(
            "Complete null-extension diagnostic vectors:\n"
            + json.dumps({"expected": expected, "actual": actual}, indent=2),
            pytrace=False,
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
        ("satisfying_cross_family_comparison", "PIE-S2105"),
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
    elif name == "satisfying_cross_family_comparison":
        line = PROJECT_SOURCE.splitlines().index('        total > "0"') + 1
        assert [
            (
                diagnostic.code,
                diagnostic.message,
                diagnostic.location.line,
                diagnostic.location.column,
            )
            for diagnostic in result.diagnostics
            if diagnostic.severity is Severity.ERROR
        ] == [
            (
                "PIE-S2105",
                "Invalid operands for operator >: expected comparable operands",
                line,
                9,
            )
        ]


def test_satisfying_reports_a_def_argument_that_does_not_fit_once(
    tmp_path: Path,
) -> None:
    """A `satisfying:` predicate that is a not-null def call whose argument
    does not fit is PIE-S2395 at the call; an output whose def argument does
    not fit is PIE-S2395 alone, also where the predicate reads it, as without
    JOIN inputs."""
    header = PROJECT_SOURCE.split("query absent_stage:")[0]
    queries = "".join(
        f"query {name}:\n    from accounts\n    let event = events\n"
        "    inner join event on event.account_id == accounts.id\n"
        f"    group by:\n        {key}\n    select:\n        key = {item}\n"
        f"        top = {top}\n        total = count(event.id)\n"
        f"    having:\n        {predicate}\n"
        for name, key, item, top, predicate in (
            (
                "null_predicate",
                "accounts.id",
                "accounts.id",
                "max(event.metric)",
                "nb(None)",
            ),
            (
                "comparison_predicate",
                "accounts.id",
                "accounts.id",
                "max(event.metric)",
                "nb(total > 0)",
            ),
            (
                "unfit_aggregate",
                "accounts.id",
                "accounts.id",
                "nn(max(event.metric))",
                "total > 0 and top > 0",
            ),
            (
                "unfit_key",
                "event.metric",
                "nn(event.metric)",
                "max(event.id)",
                "total > 0 and key > 0",
            ),
        )
    )
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        header
        + "def nb(x: Bool) -> Bool: return x\n"
        + "def nn(x: Int) -> Int: return x\n"
        + queries,
        encoding="utf-8",
    )
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    )
    offset = header.count("\n")
    assert [
        (d.code, d.message, d.location.line - offset, d.location.column)
        for d in completed.diagnostics
    ] == [
        (
            "PIE-S2395",
            f"Invalid argument for def {name} at position 1 (x): "
            f"expected {expected}, got {actual}",
            line,
            column,
        )
        for name, expected, actual, line, column in (
            ("nb", "Bool", "null", 14, 9),
            ("nb", "Bool", "Bool of unknown nullability", 26, 9),
            ("nn", "Int", "Int | None", 35, 15),
            ("nn", "Int", "Int | None", 46, 15),
        )
    ]


def test_an_aggregate_reports_its_unfit_def_argument_alone(tmp_path: Path) -> None:
    """A field or `let:` name passed to a def it does not fit is PIE-S2395
    alone as an aggregate argument, grouped or not, as in a single file: it is
    no expression argument (PIE-S2315), as one that fits shows. An expression
    argument written by hand keeps PIE-S2315."""
    header = PROJECT_SOURCE.split("query absent_stage:")[0]
    joined = (
        "    from accounts\n"
        "    let event = events\n"
        "    inner join event on event.account_id == accounts.id\n"
    )
    grouped = "    group by accounts.id\n    select:\n        key = accounts.id\n"
    queries = (
        f"query field:\n{joined}{grouped}        top = max(nn(event.metric))\n"
        f"query global:\n{joined}    select:\n"
        "        total = count(nn(event.metric))\n"
        f"query let_name:\n{joined}    let j = event.metric\n{grouped}"
        "        top = max(nn(j))\n"
        f"query wrong_type:\n{joined}{grouped}        top = max(tn(event.metric))\n"
        f"query fits:\n{joined}{grouped}        top = max(ni(event.metric))\n"
        f"query expression:\n{joined}{grouped}"
        "        top = max(lower(event.metric))\n"
    )
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        header
        + "def nn(x: Int) -> Int: return x\n"
        + "def ni(x: Int | None) -> Int | None: return x\n"
        + "def tn(x: Text) -> Text: return x\n"
        + queries,
        encoding="utf-8",
    )
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    )
    offset = header.count("\n") + 3
    assert [
        (d.code, d.message, d.location.line - offset, d.location.column)
        for d in completed.diagnostics
    ] == [
        *(
            (
                "PIE-S2395",
                f"Invalid argument for def {name} at position 1 (x): "
                f"expected {expected}, got Int | None",
                line,
                column,
            )
            for name, expected, line, column in (
                ("nn", "Int", 8, 19),
                ("nn", "Int", 14, 23),
                ("nn", "Int", 23, 19),
                ("tn", "Text", 31, 19),
            )
        ),
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Int",
            47,
            19,
        ),
        (
            "PIE-S2315",
            "Aggregate function max requires a direct field argument; "
            "expression arguments are not supported yet",
            47,
            15,
        ),
    ]


def test_an_aggregate_keeps_the_s2315_of_an_unfit_def_argument_form(
    tmp_path: Path,
) -> None:
    """An aggregate argument passed to a def it does not fit adds PIE-S2315
    beside its PIE-S2395 only in a form the aggregate accepts for no
    argument type, as in a single file: not for `event.metric + 1` in
    `count` (before: PIE-S2315 too), but for a `let:` value the aggregate
    reads as `upper(event.label)` or a constant (before: PIE-S2395 alone),
    as the same forms are without the def, and for an expression that
    reads a `let:` name."""
    header = PROJECT_SOURCE.split("query absent_stage:")[0]
    joined = (
        "    from accounts\n"
        "    let event = events\n"
        "    inner join event on event.account_id == accounts.id\n"
    )
    grouped = "    group by accounts.id\n    select:\n        key = accounts.id\n"
    queries = (
        f"query plus:\n{joined}{grouped}        c = count(nn(event.metric + 1))\n"
        f"query let_upper:\n{joined}    let j = upper(event.label)\n"
        f"{grouped}        c = count(nn(j))\n"
        f"query let_constant:\n{joined}    let j = 1.5\n{grouped}"
        "        s = sum(nn(j))\n"
        f"query let_read:\n{joined}    let j = event.metric\n{grouped}"
        "        c = count(nn(j + 1))\n"
    )
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        header + "def nn(x: Int) -> Int: return x\n" + queries,
        encoding="utf-8",
    )
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    )
    offset = header.count("\n") + 1

    def mismatch(line: int, column: int, actual: str) -> tuple[str, str, int, int]:
        return (
            "PIE-S2395",
            "Invalid argument for def nn at position 1 (x): "
            f"expected Int, got {actual}",
            line,
            column,
        )

    def expression_argument(name: str, line: int) -> tuple[str, str, int, int]:
        return (
            "PIE-S2315",
            f"Aggregate function {name} requires a direct field argument; "
            "expression arguments are not supported yet",
            line,
            13,
        )

    assert [
        (d.code, d.message, d.location.line - offset, d.location.column)
        for d in completed.diagnostics
    ] == [
        mismatch(8, 19, "Int of unknown nullability"),
        mismatch(17, 19, "Text"),
        expression_argument("count", 17),
        mismatch(26, 17, "Float"),
        expression_argument("sum", 26),
        mismatch(35, 19, "Int of unknown nullability"),
        expression_argument("count", 35),
    ]


def test_an_aggregate_argument_part_that_does_not_fit_its_def_is_unknown(
    tmp_path: Path,
) -> None:
    """A def argument that does not fit and is only a part of an aggregate's
    argument is unknown to the aggregate as a whole one is, as in a single
    file: PIE-S2395 alone where the aggregate accepts the argument's form
    (`count(nn(event.metric) + 1)`; before: PIE-S2315 too), and both where it
    accepts the form for no argument type (`max(nn(event.metric) + 1)`)."""
    header = PROJECT_SOURCE.split("query absent_stage:")[0]
    joined = (
        "    from accounts\n"
        "    let event = events\n"
        "    inner join event on event.account_id == accounts.id\n"
    )
    grouped = "    group by accounts.id\n    select:\n        key = accounts.id\n"
    queries = (
        f"query part:\n{joined}{grouped}        c = count(nn(event.metric) + 1)\n"
        f"query extremum:\n{joined}{grouped}        m = max(nn(event.metric) + 1)\n"
    )
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        header + "def nn(x: Int) -> Int: return x\n" + queries,
        encoding="utf-8",
    )
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    )
    offset = header.count("\n") + 1
    mismatch = (
        "Invalid argument for def nn at position 1 (x): expected Int, got Int | None"
    )
    assert [
        (d.code, d.message, d.location.line - offset, d.location.column)
        for d in completed.diagnostics
    ] == [
        ("PIE-S2395", mismatch, 8, 19),
        ("PIE-S2395", mismatch, 16, 17),
        (
            "PIE-S2315",
            "Aggregate function max requires a direct field argument; "
            "expression arguments are not supported yet",
            16,
            13,
        ),
    ]


_JOINED_STAGE_SOURCE = """shape Point:
    code: Text
shape T:
    id: Int
    n: Int | None
    home: Point
    t_key = unique(id)
shape O:
    oid: Int
    tid: Int
    o_key = unique(oid)
source src: T = postgres.table("src")
source oth: O = postgres.table("oth")
def bl(x: Bool | None) -> Bool | None: return x
def ni(x: Int | None) -> Int | None: return x
def nn(x: Int) -> Int: return x
"""
_JOINED_STAGE_INPUT = (
    "    from oth\n    let r = src\n    inner join r on r.id == oth.tid\n"
)


def _joined_stage_diagnostics(
    root: Path, queries: str
) -> list[tuple[str, str, int, int]]:
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(_JOINED_STAGE_SOURCE + queries, encoding="utf-8")
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(root))
    )
    offset = _JOINED_STAGE_SOURCE.count("\n")
    return [
        (d.code, d.message, d.location.line - offset, d.location.column)
        for d in completed.diagnostics
    ]


def test_satisfying_null_literal_is_pie_s2327_and_an_unknown_predicate_fails_closed(
    tmp_path: Path,
) -> None:
    """A null literal compared or combined in a joined `satisfying:` predicate,
    also the argument of a nullable def, is PIE-S2327 at the literal, as in a
    single file; any other predicate of unknown type, here a comparison of a
    shape-typed output, leaves the relation to PIE-S2333. Before, both raised
    ValueError."""
    predicates = (
        "a > 0",
        "None",
        "a == None",
        "None and a > 0",
        "bl(None)",
        "bl(a == None)",
        "ni(None) > 0",
    )
    queries = "".join(
        f"query q{ordinal}:\n{_JOINED_STAGE_INPUT}    group by:\n        oth.oid\n"
        "    select:\n        key = oth.oid\n        a = count(r.n)\n"
        f"    having:\n        {predicate}\n"
        for ordinal, predicate in enumerate(predicates)
    )
    shape_line = len(predicates) * 11 + 1
    queries += (
        f"query shaped:\n{_JOINED_STAGE_INPUT}    group by:\n        oth.oid\n"
        "        r.home\n    select:\n        key = oth.oid\n        h = r.home\n"
        "        a = count(r.n)\n    having:\n        h == h\n"
    )
    assert _joined_stage_diagnostics(tmp_path, queries) == [
        *(
            (
                "PIE-S2327",
                "Unsupported having expression form: null literal",
                ordinal * 11 + 11,
                column,
            )
            for ordinal, column in ((1, 9), (2, 14), (3, 9), (4, 12), (5, 17), (6, 12))
        ),
        (
            "PIE-S2333",
            "Project relation semantic completion is unavailable: shaped",
            shape_line,
            1,
        ),
    ]


def test_a_let_renaming_a_field_selects_that_field_group_key(tmp_path: Path) -> None:
    """A `let:` name that renames a field is that field's group key where it is
    selected, as a computed one is, and a def it is passed to must fit it
    (PIE-S2395); a `let:` name that selects no group key is no unknown field
    (PIE-S2102), and the relation fails closed with PIE-S2333."""
    queries = "".join(
        f"query {name}:\n{_JOINED_STAGE_INPUT}    let g1 = r.n\n"
        f"    let g2 = r.id\n    group by:\n        g1\n    select:\n"
        f"        k = {item}\n        c = count()\n"
        for name, item in (("alias", "g1"), ("unfit", "nn(g1)"), ("other", "g2"))
    )
    assert _joined_stage_diagnostics(tmp_path, queries) == [
        (
            "PIE-S2395",
            "Invalid argument for def nn at position 1 (x): "
            "expected Int, got Int | None",
            21,
            13,
        ),
        (
            "PIE-S2333",
            "Project relation semantic completion is unavailable: other",
            23,
            1,
        ),
    ]


def test_collection_preserves_exact_current_tail_order_and_base_ledger(
    built: _Built,
) -> None:
    entries_before = built.completion.entries
    assert len(built.aggregations) == len(built.filters) and built.aggregations
    for aggregations, filters in zip(built.aggregations, built.filters, strict=True):
        assert aggregations.filter_set is filters
        assert filters.completion is built.completion
        current = filters.current_semantics
        assert current is not None
        owner = current.namespaces.binding_environment.ledger.owner
        expected = tuple(entry for entry in entries_before if entry.owner is owner)
        assert len(expected) == 1
        assert tuple(result.entry for result in filters.results) == expected
        assert len(aggregations.results) == len(filters.results) and filters.results
        assert all(
            result.input_filter is input_filter
            for result, input_filter in zip(
                aggregations.results, filters.results, strict=True
            )
        )
        assert all(
            input_filter.current_semantics is current
            and input_filter.joined_semantics is current
            for input_filter in filters.results
        )
        with pytest.raises(ValueError, match="exact Slice-8 membership"):
            aggregation.build_project_joined_aggregation(
                filters, replace(filters.results[0])
            )
    assert built.completion.entries is entries_before


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
            "    having:\n"
            "        account_id > 0\n",
            ("PIE-S2325",),
        ),
        (
            "global_satisfying",
            "    from rows\n"
            "    select:\n"
            "        total = sum(metric)\n"
            "    having:\n"
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


def test_unknown_join_grain_with_an_aggregate_issue_reports_the_issue(
    tmp_path: Path,
) -> None:
    from _pietto_project_join import _completed

    result = _completed(
        tmp_path,
        "shape Customer:\n"
        "    id: Int\n"
        "    score: Int\n"
        'source customers: Customer = postgres.table("customers")\n'
        "query scores:\n"
        "    from customers\n"
        "    select:\n"
        "        score\n"
        "query q:\n"
        "    from generate_series(1, 5, 1) as gs\n"
        "    let j0 = scores\n"
        "    cross join j0\n"
        "    group by:\n"
        "        j0.score\n"
        "    select:\n"
        "        a1 = min(j0.score)\n"
        "        a2 = max(j0.id)\n",
    )

    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in result.diagnostics
    ] == [("PIE-S2102", "Unknown field: j0.id", 17, 18)]


@pytest.mark.parametrize("compound", (False, True))
@pytest.mark.parametrize("extra_on", (False, True))
def test_equality_non_null_unique_group_key_protects_its_final_join_rows(
    tmp_path: Path, compound: bool, extra_on: bool
) -> None:
    header = _NULLING_HEADER.replace(
        "    order_key = unique(id)\n",
        "    order_key = unique(id)\n    match_key = unique(customer_id"
        + (", amount" if compound else "")
        + ")\n",
    )
    if compound:
        header = header.replace("amount: Int", "amount: Int | None").replace(
            "orders.customer_id == customers.id\n",
            "orders.customer_id == customers.id and orders.amount == customers.region_id\n",
        )
    body = _RIGHT_C
    if extra_on:
        body = body.replace(
            "on order_customer(orders, c)\n",
            "on order_customer(orders, c) and c.vip\n",
        )
    body += (
        "    let o2 = orders\n    inner join o2 on order_customer(o2, c)\n" + _CROSS_R
    )
    groups = "orders.id"
    if extra_on:
        groups += ", o2.customer_id" + (", o2.amount" if compound else "")
    body += f"    group by {groups}\n    select:\n        n = count(r.id)\n"
    assert _fanout_check(tmp_path, "nonnull", header + "query result:\n" + body) == []
    if extra_on:
        # One unproved component cannot make a nullable composite key strict.
        incomplete = (
            header.replace(
                "orders.customer_id == customers.id and orders.amount == customers.region_id",
                "orders.customer_id == customers.id",
            )
            if compound
            else header.replace(
                "match_key = unique(customer_id)",
                "match_key = unique(customer_id, region)",
            )
        )
        if not compound:
            incomplete = incomplete.replace(
                "    rush: Bool",
                "    region: Int | None\n    rush: Bool",
            )
            body = body.replace("o2.customer_id\n", "o2.customer_id, o2.region\n")
        assert _fanout_check(
            tmp_path, "incomplete", incomplete + "query result:\n" + body
        ) == [
            (
                "PIE-S2333",
                _UNAVAILABLE
                + "result (an aggregate may read rows repeated by JOIN c; match a unique key of o2 whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
            )
        ]


@pytest.mark.parametrize("where_first", (False, True))
def test_composed_where_and_let_depth_does_not_stack(
    tmp_path: Path, where_first: bool
) -> None:
    repeated = " and ".join(["orders.amount > 0"] * 300)
    declarations = [
        f"    let w = (orders.id is not None) and {repeated}\n",
        "    let v = r.id\n",
    ]
    if not where_first:
        declarations.reverse()
    body = _RIGHT_C + _CROSS_R + "".join(declarations)
    body += f"    where w and {repeated}\n" + _BY_ORDER + "        n = count(v)\n"
    assert (
        _fanout_check(tmp_path, "depth", _NULLING_HEADER + "query result:\n" + body)
        == []
    )


def test_null_proof_visits_only_demanded_operands_in_order() -> None:
    source = "query q:\n    from input\n    where (a is None) and (b in ()) and (c or c)\n    select x\n"
    program = parse_source(source)
    assert program.ast is not None and not program.diagnostics
    query = next(item for item in program.ast.definitions if isinstance(item, QueryDef))
    assert query.where_clause is not None
    visits = []

    def leaf(expression, nulls, truth):
        visits.append((expression.name, truth))
        return True

    assert aggregation._never(query.where_clause.expression, True, frozenset(), leaf)
    assert visits == [("c", True), ("c", True)]


@pytest.mark.parametrize("filtered", (False, True))
def test_inverse_relationship_requires_the_same_unfiltered_source_domain(
    tmp_path: Path, filtered: bool
) -> None:
    header = _NULLING_HEADER
    if filtered:
        header += "query other:\n    from payments\n    where payments.id > 0\n    select id, order_id\n"
    else:
        header += 'source other: Payment = postgres.table("payments")\n'
    body = (
        "query result:\n"
        "    from other\n"
        "    let o = orders\n"
        "    right join o on other.order_id == o.id\n"
        "    let p = payments\n    where any(payment_order(p, o) for p in p)\n"
        "    let r = regions\n    cross join r\n"
        "    group by other.id\n"
        "    select:\n"
        "        n = count(r.id)\n"
    )
    assert _fanout_check(tmp_path, "domains", header + body) == [
        (
            "PIE-S2333",
            _UNAVAILABLE
            + "result (an aggregate may read rows repeated by JOIN o; match a unique key of o whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
        )
    ]


def test_later_outer_join_invalidates_equality_non_null_group_key(
    tmp_path: Path,
) -> None:
    header = _NULLING_HEADER.replace(
        "    order_key = unique(id)\n",
        "    order_key = unique(id)\n    match_key = unique(customer_id)\n",
    )
    body = (
        "query result:\n    from orders\n    let c = customers\n"
        "    right join c on order_customer(orders, c) and c.vip\n"
        "    let o2 = orders\n    inner join o2 on order_customer(o2, c)\n"
        "    let c3 = customers\n    right join c3 on order_customer(o2, c3)\n"
        + _CROSS_R
        + "    group by orders.id, o2.customer_id\n    select:\n        n = count(r.id)\n"
    )
    assert _fanout_check(tmp_path, "outer", header + body) == [
        (
            "PIE-S2333",
            _UNAVAILABLE
            + "result (an aggregate may read rows repeated by JOIN c; match a unique key of c3 whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
        )
    ]


def test_null_argument_does_not_visit_a_where_let(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = aggregation._namespace_leaf
    visits = []

    def namespace(*args, **kwargs):
        answer = original(*args, **kwargs)

        def leaf(expression, nulls, truth):
            if getattr(expression, "name", None) == "w":
                visits.append(truth)
            return answer(expression, nulls, truth)

        return leaf

    monkeypatch.setattr(aggregation, "_namespace_leaf", namespace)
    repeated = " and ".join(["orders.amount > 0"] * 300)
    source = _NULLING_HEADER + "query result:\n" + _RIGHT_C
    source += f"    let w = {repeated}\n    where w\n"
    source += "    select:\n        n = count(orders.id)\n"
    assert _fanout_check(tmp_path, "skipped", source) == []
    assert visits == []


_COMPOSITE_REVERSE_SOURCE = """shape Payment:
    id: Int
    x: Int
    y: Int
    payment_key = unique(id)
shape Order:
    x: Int
    y: Int
    order_key = unique(x, y)
shape Region:
    id: Int
    region_key = unique(id)
source payments: Payment = postgres.table("payments")
source orders: Order = postgres.table("orders")
source regions: Region = postgres.table("regions")
relationship forward_match(payments: Payment, orders: Order):
    payments.x == orders.x and payments.y == orders.y
relationship reverse_match(orders: Order, payments: Payment):
    orders.y == payments.y and orders.x == payments.x
query reordered_reverse:
    from payments
    let o = orders
    right join o on forward_match(payments, o)
    let p2 = payments
    where any(reverse_match(o, p2) for p2 in p2)
    let r = regions
    cross join r
    group by payments.id
    select:
        n = count(r.id)
"""


@pytest.mark.parametrize(
    "variant", ("reordered", "wrong_pairs", "duplicates", "missing_duplicate")
)
def test_inverse_match_compares_complete_paired_equality_multisets(
    tmp_path: Path, variant: str
) -> None:
    source = _COMPOSITE_REVERSE_SOURCE
    if variant == "wrong_pairs":
        source = source.replace(
            "orders.y == payments.y and orders.x == payments.x",
            "orders.y == payments.x and orders.x == payments.y",
        )
    if variant in {"duplicates", "missing_duplicate"}:
        source = source.replace(
            "payments.x == orders.x and payments.y == orders.y",
            "payments.x == orders.x and payments.y == orders.y and payments.x == orders.x",
        )
    if variant == "duplicates":
        source = source.replace(
            "orders.y == payments.y and orders.x == payments.x",
            "orders.x == payments.x and orders.y == payments.y and orders.x == payments.x",
        )
    assert _fanout_check(tmp_path, variant, source) == (
        []
        if variant in {"reordered", "duplicates"}
        else [
            (
                "PIE-S2333",
                _UNAVAILABLE
                + "reordered_reverse (an aggregate may read rows repeated by JOIN o; match a unique key of o whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
            )
        ]
    )


_UNBOUNDED_NULLABLE_SOURCE = """shape Order:
    id: Int
    order_key = unique(id)
shape Payment:
    id: Int
    order_id: Int
    customer_id: Int | None
    payment_key = unique(id)
    payment_customer = unique(customer_id)
shape Customer:
    id: Int
    customer_key = unique(id)
shape Region:
    id: Int
    region_key = unique(id)
source orders: Order = postgres.table("orders")
source payments: Payment = postgres.table("payments")
source customers: Customer = postgres.table("customers")
source regions: Region = postgres.table("regions")
relationship payment_order(payments: Payment, orders: Order):
    payments.order_id == orders.id
relationship payment_customer(payments: Payment, customers: Customer):
    payments.customer_id == customers.id
query scope_unbounded_right:
    from orders
    let p = payments
    right join p on payment_order(p, orders)
    let c = customers
    inner join c on payment_customer(p, c)
    let r = regions
    cross join r
    group by orders.id, p.customer_id
    select:
        n = count(r.id)
"""


@pytest.mark.parametrize("unrelated_bounded", (False, True))
def test_nullable_holder_key_never_seeds_an_unrelated_unbounded_join(
    tmp_path: Path, unrelated_bounded: bool
) -> None:
    source = _UNBOUNDED_NULLABLE_SOURCE
    if unrelated_bounded:
        source = source.replace(
            "query scope_unbounded_right:",
            "relationship order_region(orders: Order, regions: Region):\n    orders.id == regions.id\nquery scope_unbounded_right:",
        ).replace(
            "    from orders\n    let p = payments\n",
            "    from orders\n    let bounded = regions\n    right join bounded on order_region(orders, bounded)\n    let p = payments\n",
        )
    assert _fanout_check(tmp_path, "scope", source) == [
        (
            "PIE-S2333",
            _UNAVAILABLE
            + "scope_unbounded_right (an aggregate may read rows repeated by JOIN p; match a unique key of c whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
        )
    ]


def test_modern_predicate_reverse_proof_uses_whole_accumulated_left_key(
    tmp_path: Path,
) -> None:
    from _pietto_project_join import _completed
    from pietto._project.project_current_joins import (
        ProjectCurrentBinaryJoin,
        current_forward_at_most_one,
    )

    source = """shape Row:
    id: Int
    tenant: Int
    row_key = unique(id, tenant)
shape Many:
    id: Int
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
source events: Many = postgres.table("events")
relationship SameId(a: Row, b: Row):
    a.id == b.id
relationship SameTenant(a: Row, b: Row):
    a.tenant == b.tenant
query result:
    from lhs
    let e = events
    left join e on lhs.id == e.id
    let r = rhs
    left join r on SameId(lhs, r) and SameTenant(lhs, r)
    select:
        id = lhs.id
        matched = r.id
"""
    completed = _completed(tmp_path, source)
    assert completed.ok, completed.diagnostics
    regions = tuple(
        region
        for region in completed.effective_outputs.current_regions
        if region.ledger.owner.identity.declared_name == "result"
    )
    assert len(regions) == 1
    first, second = regions[0].joins
    assert isinstance(first, ProjectCurrentBinaryJoin)
    assert isinstance(second, ProjectCurrentBinaryJoin)
    assert current_forward_at_most_one(second.condition)
    assert any(
        match.binding is second.condition.ledger.bindings[0]
        for match in second.condition.key_matches
    )
    assert first.properties.relational.keys == ()
    assert second.properties.relational.keys == ()


@pytest.mark.parametrize("prior_join", (False, True))
@pytest.mark.parametrize(
    "join", ("cross join r", "inner join r on True", "inner join r on r.id > 0")
)
def test_disconnected_join_fanout_names_the_factor_introduction(
    tmp_path: Path, prior_join: bool, join: str
) -> None:
    body = _RIGHT_C if prior_join else "    from orders\n"
    body += f"    let r = regions\n    {join}\n"
    if prior_join:
        body += "    group by orders.id\n"
    body += "    select:\n        n = count(r.id)\n"
    repeated, grouped = ("c", "c") if prior_join else ("r", "orders")
    assert _fanout_check(
        tmp_path, "disconnected", _NULLING_HEADER + "query result:\n" + body
    ) == [
        (
            "PIE-S2333",
            _UNAVAILABLE
            + f"result (an aggregate may read rows repeated by JOIN {repeated}; match a unique key of {grouped} whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
        )
    ]


@pytest.mark.parametrize(
    "predicate",
    ("orders.id == r.id or c.id == r.id", "c.id == r.id or orders.id == r.id"),
)
def test_join_fanout_retains_every_prior_predicate_binding(
    tmp_path: Path, predicate: str
) -> None:
    body = _RIGHT_C + f"    let r = regions\n    inner join r on {predicate}\n"
    body += "    group by orders.id\n    select:\n        n = count(r.id)\n"
    assert _fanout_check(
        tmp_path, "all_bindings", _NULLING_HEADER + "query result:\n" + body
    ) == [
        (
            "PIE-S2333",
            _UNAVAILABLE
            + "result (an aggregate may read rows repeated by JOIN c and JOIN r; match a unique key of c whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
        )
    ]


@pytest.mark.parametrize(
    "predicate,joins",
    (
        pytest.param(
            "any(candidate.id == c.id and candidate.id == r.id for candidate in regions) or orders.id == r.id",
            "JOIN c and JOIN r",
            id="any_then_direct",
        ),
        pytest.param(
            "orders.id == r.id or any(candidate.id == c.id and candidate.id == r.id for candidate in regions)",
            "JOIN c and JOIN r",
            id="direct_then_any",
        ),
        pytest.param(
            "any(candidate.id == c.id and candidate.id == r.id for candidate in regions)",
            "JOIN c and JOIN r",
            id="only_any",
        ),
        pytest.param(
            "any(any(inner.id == c.id and inner.id == r.id and inner.id == candidate.id for inner in regions) for candidate in regions) or orders.id == r.id",
            "JOIN c and JOIN r",
            id="nested_outer_capture",
        ),
        pytest.param(
            "any(candidate.id == c.id and candidate.id == r.id for candidate in regions) or any(candidate.id == c.id and candidate.id == r.id for candidate in regions) or orders.id == r.id",
            "JOIN c and JOIN r",
            id="overlapping_captures",
        ),
        pytest.param(
            "any(candidate.id == r.id for candidate in regions) or orders.id == r.id",
            "JOIN c",
            id="target_capture_only",
        ),
        pytest.param(
            "any(c.id == r.id for c in regions) or orders.id == r.id",
            "JOIN c",
            id="local_shadow",
        ),
        pytest.param(
            "any(any(inner.id == c.id and inner.id == r.id for inner in regions) for c in regions) or orders.id == r.id",
            "JOIN c",
            id="nested_local_capture",
        ),
    ),
)
def test_join_fanout_reads_exact_any_outer_captures(
    tmp_path: Path, predicate: str, joins: str
) -> None:
    body = _RIGHT_C + f"    let r = regions\n    inner join r on {predicate}\n"
    body += "    group by orders.id\n    select:\n        n = count(r.id)\n"
    assert _fanout_check(
        tmp_path, "any_capture", _NULLING_HEADER + "query result:\n" + body
    ) == [
        (
            "PIE-S2333",
            _UNAVAILABLE
            + f"result (an aggregate may read rows repeated by {joins}; match a unique key of c whose fields are never None in `on` with a relationship call, use `any(...)` for an input that only filters rows, or aggregate in a separate query first)",
        )
    ]


_REGION_REVENUE = """shape Customer:
    id: Int
    region: Text
    customer_key = unique(id)
shape Order:
    id: Int
    customer_id: Int
    amount: Int
    order_key = unique(id)
source customers: Customer = postgres.table("customers")
source orders: Order = postgres.table("orders")
relationship OrderCustomer(order: Order, customer: Customer):
    order.customer_id == customer.id
query revenue_by_region:
    from orders
    inner join customers on orders.customer_id == customers.id
    group by customers.region
    select region = customers.region, n = count(orders.id), total = sum(orders.amount)
"""


def test_single_file_fanout_remedy_keeps_the_grouping_the_query_asks_for() -> None:
    """Grouping by a customer key would pass but change the result's grain;
    the remedy matches the key in `on` instead, which this release proves
    for a relationship call."""

    def check(source: str) -> list[tuple[str, str, int, int]]:
        parsed = parse_source(source)
        assert parsed.ast is not None and parsed.diagnostics == ()
        return [
            (d.code, d.message, d.location.line, d.location.column)
            for d in analyze(parsed.ast).diagnostics
        ]

    remedy = (
        "An aggregate may read rows that a JOIN repeats; match a declared unique "
        "key of customers whose fields are never None in `on` with a relationship "
        "call, use `any(...)` for an input that only filters rows, or aggregate in "
        "a separate query first"
    )
    assert check(_REGION_REVENUE) == [
        ("PIE-S2381", remedy, 18, 43),
        ("PIE-S2381", remedy, 18, 69),
    ]
    assert (
        check(
            _REGION_REVENUE.replace(
                "on orders.customer_id == customers.id",
                "on OrderCustomer(orders, customers)",
            )
        )
        == []
    )
