from __future__ import annotations

import ast
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
    build_project_completed_semantic_result,
)
from pietto.ast_nodes import DottedNameExpr, QueryDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import EffectiveNullability


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_aggregation.py"
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
query computed_alias_group_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        computed = event.metric + 1
        alias = computed
    group by:
        alias
    select:
        total = count()
query computed_both_sides_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        band = accounts.metric > event.metric
    group by:
        band
        accounts.id
    select:
        high = band
        account_id = accounts.id
        total = sum(event.metric)
query computed_fanout_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        same_event = event.id + 0
    group by:
        same_event
    select:
        event_id = same_event
        total = sum(accounts.metric)
query computed_self_key:
    from events
    inner join events as parent:
        from events
        via event_parent: child -> parent
    let:
        older = events.id > parent.id
    group by:
        older
    select:
        older
        total = count()
query computed_duplicate_key:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        band = accounts.metric > event.metric
    group by:
        band
        band
    select:
        total = count()
query computed_extrema:
    from events
    inner join events as parent:
        from events
        via event_parent: child -> parent
    let:
        gap = parent.id + events.id * 0
    group by:
        events.id
    select:
        event_id = events.id
        low = min(gap)
        high = max(gap)
query computed_extrema_blocked:
    from events
    inner join events as parent:
        from events
        via event_parent: child -> parent
    let:
        fixed = 3
        tag = parent.label
    group by:
        events.id
    select:
        event_id = events.id
        top = max(fixed)
        name = min(tag)
query extremum_fanout_let:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        same_event = event.id + 0
        measured = accounts.metric + 0
    group by:
        same_event
    select:
        event_id = same_event
        top = max(measured)
query extremum_fanout_field:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        same_event = event.id + 0
    group by:
        same_event
    select:
        event_id = same_event
        top = max(accounts.metric)
query extremum_fanout_constant:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        same_event = event.id + 0
        constant = 7
    group by:
        same_event
    select:
        event_id = same_event
        top = max(constant)
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
        unapproved_let = min(amount + 1)
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
query satisfying_cross_family_comparison:
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
        total > "0"
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
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        band = accounts.metric > event.metric
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
            "        position = row_number() window:\n"
            "            order by:\n                high\n",
            [("PIE-S2102", "Unknown field: high", 15, 17)],
        ),
        (
            "        position = row_number() window:\n"
            "            partition by:\n                high\n",
            [("PIE-S2102", "Unknown field: high", 15, 17)],
        ),
        (
            "        position = row_number() window:\n"
            "            order by:\n                total\n"
            "    qualify:\n        high\n",
            [("PIE-S2332", "Unknown QUALIFY reference: high", 17, 9)],
        ),
        (
            "        position = row_number() window:\n"
            "            order by:\n                total\n"
            "    qualify:\n        row_number() window:\n"
            "            order by:\n                high\n        <= 1\n",
            [("PIE-S2102", "Unknown field: high", 19, 17)],
        ),
        ("    satisfying:\n        high\n    order by:\n        high desc\n", []),
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
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(tmp_path))
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
    """PIE-S2333 keeps its code and span; the relation whose own aggregate is
    refused for fan-out names the repeating JOINs and remedies, also beneath a
    row let, a window and QUALIFY, and offers no declared key for an ON
    condition; a reader of it stays bare."""

    def query(name: str) -> str:
        start = PROJECT_SOURCE.index(f"query {name}:")
        return PROJECT_SOURCE[start : PROJECT_SOURCE.index("\nquery ", start) + 1]

    header = PROJECT_SOURCE.split("query absent_stage:")[0]
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        header
        + query("fanout_risk")
        + query("ambiguous_chasm")
        + "query reader:\n    from fanout_risk\n    select:\n        total\n"
        + "query qualified_risk:\n    from accounts\n"
        "    inner join events as event:\n        from accounts\n"
        "        via account_events: account -> event\n"
        "    let:\n        weight = accounts.metric\n"
        "    group by:\n        accounts.label\n"
        "    select:\n        label = accounts.label\n        top = max(weight)\n"
        "        rk = rank() window:\n            order by:\n                top desc\n"
        "    qualify:\n        rk <= 3\n"
        + query("fanout_risk")
        .replace("fanout_risk", "on_risk")
        .replace(
            "via account_events: account -> event", "on accounts.id == event.account_id"
        ),
        encoding="utf-8",
    )
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    )
    offset = header.count("\n")
    event = (
        " (an aggregate may read rows repeated by JOIN event; declare a unique key "
        "on events.account_id (matched by JOIN event), or group by a unique key of "
        "event whose fields are all not null)"
    )
    assert not completed.ok
    assert [
        (d.code, d.message, d.location.line - offset, d.location.column)
        for d in completed.diagnostics
    ] == [
        ("PIE-S2333", f"{_UNAVAILABLE}fanout_risk{event}", 1, 1),
        (
            "PIE-S2333",
            f"{_UNAVAILABLE}ambiguous_chasm (an aggregate may read rows repeated by "
            "JOIN event and JOIN signal; declare a unique key on events.account_id "
            "(matched by JOIN event) and a unique key on signals.dimension_id (matched "
            "by JOIN signal), or group by unique keys of event and signal whose "
            "fields are all not null)",
            8,
            1,
        ),
        ("PIE-S2333", f"{_UNAVAILABLE}reader", 22, 1),
        ("PIE-S2333", f"{_UNAVAILABLE}qualified_risk{event}", 26, 1),
        (
            "PIE-S2333",
            f"{_UNAVAILABLE}on_risk (an aggregate may read rows repeated by JOIN "
            "event; group by a unique key of event whose fields are all not null)",
            43,
            1,
        ),
    ]


_FANOUT_SHAPES = {
    "orders": ("Order", ("customer_id: Int not null", "amount: Int not null")),
    "customers": ("Customer", ("name: Text not null", "region_id: Int not null")),
    "regions": ("Region", ("name: Text not null",)),
    "emps": ("Emp", ("manager_id: Int not null", "name: Text not null")),
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
_CUST = "    {} join customers as cust:\n        from orders\n"
_VIA_CUST = "        via order_customer: order -> customer\n"
_REG = "    inner join regions as reg:\n        from cust\n"
_VIA_REG = "        via customer_region: customer -> region\n"
_SELF = (
    "    inner join emps as boss:\n        from emps\n"
    "        via report_manager: report -> manager\n"
)
_FROM_SIDE = (("cust.name",), ("cname = cust.name", "top = max(orders.amount)"))
_TARGET_SIDE = (("orders.amount",), ("amt = orders.amount", "top = max(cust.id)"))
_FANOUT_CASES: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...], str]] = {
    **{
        f"{kind}_{match}_{side}": (
            "orders",
            _CUST.format(kind) + text,
            groups,
            outputs,
            "",
        )
        for kind, match, text in (
            ("inner", "via", _VIA_CUST),
            ("left", "via", _VIA_CUST),
            ("right", "via", _VIA_CUST),
            ("full", "via", _VIA_CUST),
            ("inner", "zero_hop", ""),
            ("inner", "via_on", _VIA_CUST + '        on cust.name != "x"\n'),
            ("inner", "on", "        on orders.customer_id == cust.id\n"),
            ("left", "on", "        on orders.customer_id == cust.id\n"),
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
        _CUST.format("inner")
        + _VIA_CUST
        + _REG
        + "        on cust.region_id == reg.id\n",
        ("orders.amount",),
        ("amt = orders.amount", "top = max(reg.id)"),
        "",
    ),
    "chain_partly_proven_last": (
        "orders",
        _CUST.format("inner") + _VIA_CUST + _REG + _VIA_REG,
        ("orders.amount",),
        ("amt = orders.amount", "n = count(reg.id)"),
        "orders:unique proven on customer_id",
    ),
    "chain_partly_proven_first": (
        "orders",
        _CUST.format("inner") + _VIA_CUST + _REG + _VIA_REG,
        ("reg.name",),
        ("rname = reg.name", "top = max(orders.amount)"),
        "customers:unique proven on id",
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
    # A SEMI JOIN target repeats nothing and is never named.
    "semi_then_via": (
        "orders",
        "    semi join regions as sr:\n        from orders\n"
        "        on orders.amount == sr.id\n" + _CUST.format("inner") + _VIA_CUST,
        ("cust.name",),
        ("cname = cust.name", "top = max(orders.amount)"),
        "",
    ),
    **{
        f"{name}_{side}": (
            "orders",
            _CUST.format("inner") + f"        via {relationship}: order -> customer\n",
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
    # One key serves both JOINs and is listed once.
    "two_joins_one_key": (
        "orders",
        "".join(
            f"    inner join customers as {name}:\n        from orders\n{_VIA_CUST}"
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
        f"shape {shape}:\n    id: Int not null\n    uid: Int not null\n"
        + "".join(f"    {field}\n" for field in fields)
        + "".join(
            f"    {line.split(':', 1)[1]}\n"
            for line in dict.fromkeys(declared)
            if line.split(":", 1)[0] == relation
        )
        + f'source {relation}: {shape} is postgres.table("{relation}")\n'
        for relation, (shape, fields) in _FANOUT_SHAPES.items()
    )
    relationships = "".join(
        f"relationship {name}:\n    endpoint {left}: {left_relation}\n"
        f"    endpoint {right}: {right_relation}\n"
        f"    on {_FANOUT_CONDITIONS[name]}\n"
        for name, left, left_relation, right, right_relation in _FANOUT_RELATIONSHIPS
        # A repeated-operand relationship only where a JOIN reads it, so a
        # zero-hop JOIN keeps one candidate relationship.
        if name not in _FANOUT_REPEATED or f"via {name}:" in joins
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
def test_every_fanout_remedy_applied_alone_clears_the_refusal(
    tmp_path: Path, name: str
) -> None:
    """Over JOIN kinds, ON, zero-hop, VIA+ON, both aggregate directions, chains,
    a partly proven chain and a self-join: the refusal names a repeating JOIN,
    always offers the group-by remedy, and each remedy it offers, applied to
    the source alone, clears it."""

    case = _FANOUT_CASES[name]
    ((code, message),) = _fanout_check(tmp_path, "refused", _fanout_source(case))
    assert code == "PIE-S2333"
    assert message.startswith(
        f"{_UNAVAILABLE}q (an aggregate may read rows repeated by JOIN "
    )
    keys = [
        (relation, field or fields)
        for relation, field, fields in re.findall(
            r"a unique key on (\w+)(?:\.(\w+)| \(([\w, ]+)\)) "
            r"\(matched by JOINs? [\w ,]+\)",
            message,
        )
    ]
    grouped = re.search(
        r"group by (?:a unique key|unique keys) of (.+) whose fields are all not null",
        message,
    )
    assert grouped is not None
    names = re.split(r", | and ", grouped.group(1))
    remedies = {
        "group": (
            tuple(
                f"{_FANOUT_BINDINGS[item]}:unique group_key on uid" for item in names
            ),
            tuple(f"{item}.uid" for item in names),
        )
    }
    if keys:
        remedies["key"] = (
            tuple(
                f"{relation}:unique fix_{position} on {field}"
                for position, (relation, field) in enumerate(keys)
            ),
            (),
        )
    for remedy, (declarations, groups) in remedies.items():
        assert (
            _fanout_check(tmp_path, remedy, _fanout_source(case, declarations, groups))
            == []
        ), remedy


_DECLARABLE_HEADER = (
    "shape Customer:\n    id: Int not null\n    uid: Int not null\n"
    "    code: Int not null\n    name: Text not null\n"
    "shape Order:\n    id: Int not null\n    uid: Int not null\n"
    "    customer_id: Int not null\n    amount: Int not null\n"
    'source customers: Customer is postgres.table("customers")\n'
    'source customers_b: Customer is postgres.table("customers_b")\n'
    'source orders: Order is postgres.table("orders")\n'
)


def _endpoint(kind: str, groups: str, aggregate: str) -> str:
    return (
        f"{kind} bc:\n    from customers\n    select:\n        id = code\n"
        "        name\nrelationship order_bc:\n    endpoint order: orders\n"
        "    endpoint b: bc\n    on order.customer_id == b.id\n"
        "query q:\n    from orders\n    inner join bc as j0:\n        from orders\n"
        f"        via order_bc: order -> b\n    group by:\n        {groups}\n"
        f"    select:\n        g = {groups}\n        top = max({aggregate})\n"
    )


def test_fanout_remedies_never_name_an_undeclarable_input(tmp_path: Path) -> None:
    """A UNION input, a query or table relationship endpoint, and an import
    alias: the clause never asks for a key that cannot be declared or for a
    group key that cannot exist, and each remedy it does offer clears it."""

    union = (
        "query su:\n    union all:\n        from customers\n        from customers_b\n"
        "query q:\n    from orders\n    inner join su as s:\n        from orders\n"
        "        on orders.customer_id == s.id\n    group by:\n        s.name\n"
        "    select:\n        n = s.name\n        top = max(orders.amount)\n"
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

    # Over the endpoint's fields the declarable FROM-side key is offered.
    target = _endpoint("query", "orders.amount", "j0.id")
    assert _fanout_check(tmp_path, "target", _DECLARABLE_HEADER + target) == [
        (
            "PIE-S2333",
            f"{bare}j0; declare a unique key on orders.customer_id (matched by JOIN "
            "j0), or group by a unique key of orders whose fields are all not null)",
        )
    ]
    with_order = _DECLARABLE_HEADER.replace(
        "    amount: Int not null\n", "    amount: Int not null\n{}", 1
    )
    for fix, key, group in (
        ("target_key", "    unique fix on customer_id\n", ""),
        ("target_group", "    unique fix on uid\n", "        orders.uid\n"),
    ):
        fixed = with_order.format(key) + target.replace(
            "        orders.amount\n    select",
            f"        orders.amount\n{group}    select",
        )
        assert _fanout_check(tmp_path, fix, fixed) == []

    # An imported source is named by its own declaration, in its own module.
    module = (
        "shape Customer:\n    id: Int not null\n    uid: Int not null\n"
        "    name: Text not null\n{}"
        'source customers: Customer is postgres.table("customers")\n'
        "export:\n    source customers\n"
    )
    main = (
        'import "a.pietto":\n    source customers as cs\n'
        "shape Order:\n    id: Int not null\n    customer_id: Int not null\n"
        "    amount: Int not null\n"
        'source orders: Order is postgres.table("orders")\n'
        "relationship order_customer:\n    endpoint order: orders\n"
        "    endpoint customer: cs\n    on order.customer_id == customer.id\n"
        "query q:\n    from orders\n    inner join cs as cust:\n        from orders\n"
        "        via order_customer: order -> customer\n"
        "    group by:\n        cust.name\n{}"
        "    select:\n        n = cust.name\n        top = max(orders.amount)\n"
    )
    assert _fanout_check(
        tmp_path,
        "import",
        {"a.pietto": module.format(""), "main.pietto": main.format("")},
    ) == [
        (
            "PIE-S2333",
            f"{bare}cust; declare a unique key on customers.id (matched by JOIN "
            "cust), or group by a unique key of cust whose fields are all not null)",
        )
    ]
    for fix, key, group in (
        ("import_key", "    unique fix on id\n", ""),
        ("import_group", "    unique fix on uid\n", "        cust.uid\n"),
    ):
        files = {"a.pietto": module.format(key), "main.pietto": main.format(group)}
        assert _fanout_check(tmp_path, fix, files) == []


@pytest.mark.parametrize(
    ("first", "second", "spelled"),
    [
        (
            "src.x == dst.x and src.y == dst.y",
            "src.y == dst.y and src.x == dst.x",
            "x, y",
        ),
        # The first match wins over field declaration and alphabetical order.
        (
            "src.y == dst.y and src.x == dst.x",
            "src.x == dst.x and src.y == dst.y",
            "y, x",
        ),
    ],
)
def test_a_composite_key_matched_in_two_field_orders_is_offered_once(
    first: str,
    second: str,
    spelled: str,
    tmp_path: Path,
) -> None:
    """Two JOINs match the same composite key with their equalities in opposite
    orders: the clause offers that key once, spelled as first matched, and
    declaring it in either field order clears the refusal."""

    source = (
        "shape A:\n    id: Int not null\n    x: Int not null\n    y: Int not null\n"
        "    metric: Int not null\n"
        "shape B:\n    id: Int not null\n    x: Int not null\n    y: Int not null\n"
        "    name: Text not null\n{}"
        'source a: A is postgres.table("a")\nsource b: B is postgres.table("b")\n'
        + "".join(
            f"relationship {name}:\n    endpoint src: a\n    endpoint dst: b\n"
            f"    on {condition}\n"
            for name, condition in (("ab1", first), ("ab2", second))
        )
        + "query q:\n    from a\n"
        + "".join(
            f"    inner join b as {name}:\n        from a\n"
            f"        via {relationship}: src -> dst\n"
            for name, relationship in (("b1", "ab1"), ("b2", "ab2"))
        )
        + "    group by:\n        b1.name\n"
        "    select:\n        n = b1.name\n        top = max(a.metric)\n"
    )
    assert _fanout_check(tmp_path, "refused", source.format("")) == [
        (
            "PIE-S2333",
            f"{_UNAVAILABLE}q (an aggregate may read rows repeated by JOIN b1 and "
            f"JOIN b2; declare a unique key on b ({spelled}) (matched by JOINs b1 and b2), "
            "or group by unique keys of b1 and b2 whose fields are all not null)",
        )
    ]
    for name, key in (("xy", "x, y"), ("yx", "y, x")):
        declared = source.format(f"    unique bk on {key}\n")
        assert _fanout_check(tmp_path, name, declared) == []


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
        f"query {name}:\n    from accounts\n    inner join events as event:\n"
        "        from accounts\n        on event.account_id == accounts.id\n"
        f"    group by:\n        {key}\n    select:\n        key = {item}\n"
        f"        top = {top}\n        total = count(event.id)\n"
        f"    satisfying:\n        {predicate}\n"
        for name, key, item, top, predicate in (
            (
                "null_predicate",
                "accounts.id",
                "accounts.id",
                "max(event.metric)",
                "nb(null)",
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
        + "def nb(x: Bool not null) -> Bool not null: return x\n"
        + "def nn(x: Int not null) -> Int not null: return x\n"
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
            f"expected {expected} not null, got {actual}",
            line,
            column,
        )
        for name, expected, actual, line, column in (
            ("nb", "Bool", "null", 15, 9),
            ("nb", "Bool", "Bool of unknown nullability", 28, 9),
            ("nn", "Int", "Int nullable", 38, 15),
            ("nn", "Int", "Int nullable", 50, 15),
        )
    ]


def test_an_aggregate_reports_its_unfit_def_argument_alone(tmp_path: Path) -> None:
    """A field or `let:` name passed to a def it does not fit is PIE-S2395
    alone as an aggregate argument, grouped or not, as in a single file: it is
    no expression argument (PIE-S2315), as one that fits shows. An expression
    argument written by hand keeps PIE-S2315."""
    header = PROJECT_SOURCE.split("query absent_stage:")[0]
    joined = (
        "    from accounts\n    inner join events as event:\n"
        "        from accounts\n        on event.account_id == accounts.id\n"
    )
    grouped = "    group by: accounts.id\n    select:\n        key = accounts.id\n"
    queries = (
        f"query field:\n{joined}{grouped}        top = max(nn(event.metric))\n"
        f"query global:\n{joined}    select:\n"
        "        total = count(nn(event.metric))\n"
        f"query let_name:\n{joined}    let:\n        j = event.metric\n{grouped}"
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
        + "def nn(x: Int not null) -> Int not null: return x\n"
        + "def ni(x: Int nullable) -> Int nullable: return x\n"
        + "def tn(x: Text not null) -> Text not null: return x\n"
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
                f"expected {expected} not null, got Int nullable",
                line,
                column,
            )
            for name, expected, line, column in (
                ("nn", "Int", 9, 19),
                ("nn", "Int", 16, 23),
                ("nn", "Int", 27, 19),
                ("tn", "Text", 36, 19),
            )
        ),
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Int",
            54,
            19,
        ),
        (
            "PIE-S2315",
            "Aggregate function max requires a direct field argument; "
            "expression arguments are not supported yet",
            54,
            15,
        ),
    ]


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


def test_unknown_join_grain_with_an_aggregate_issue_reports_the_issue(
    tmp_path: Path,
) -> None:
    from _pietto_project_join import _completed

    result = _completed(
        tmp_path,
        "shape Customer:\n"
        "    id: Int not null\n"
        "    score: Int not null\n"
        'source customers: Customer is postgres.table("customers")\n'
        "query scores:\n"
        "    from customers\n"
        "    select:\n"
        "        score\n"
        "query q:\n"
        "    from generate_series(1, 5, 1) as gs\n"
        "    cross join scores as j0:\n"
        "        from gs\n"
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
