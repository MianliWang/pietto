from __future__ import annotations

import ast
from dataclasses import dataclass, fields
from pathlib import Path
from typing import cast

import pytest

import test_phase63_slice10_generic_window_computation_sites_named_window_reuse as slice10
from pietto._project import project_completion as completion
from pietto._project import project_joined_aggregation as aggregation
from pietto._project import project_joined_qualify as qualify
from pietto._project import project_joined_row_filter as row_filter
from pietto._project import project_joined_windows as windows
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_completion import ProjectEffectiveOutputTerminalReason
from pietto._project.project_ir_properties import ProjectIRPropertyAvailability
from pietto.ast_nodes import (
    BinaryExpr,
    ComparisonExpr,
    DottedNameExpr,
    NameExpr,
    QualifyClause,
    QueryDef,
    WindowExpr,
    WindowUseKind,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic.model import EffectiveNullability


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR = REPO_ROOT / "grammar/Pietto.g4"
AST_NODES = REPO_ROOT / "src/pietto/ast_nodes.py"
AST_BUILDER = REPO_ROOT / "src/pietto/ast_builder.py"
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_qualify.py"
HISTORICAL_BOUNDARY = (
    REPO_ROOT
    / "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py"
)
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice11-qualify-grammar-ast-semantics-property-transfer-v1.md"
)

QUALIFY_SOURCE = (
    slice10.WINDOW_SOURCE
    + """
shape FlagRow:
    id: Int not null
    account_id: Int not null
    active: Bool nullable
    unique flag_key on id
source flags: FlagRow is postgres.table("flags")
relationship account_flags:
    endpoint account: accounts
    endpoint flag: flags
    on account.id == flag.account_id
query qualify_selected:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        ranked <= 3 and event.account_id > 0
query qualify_selected_input_only:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                event.id
    qualify:
        account_id > 0
query qualify_hidden_only:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        row_number() window:
            order by:
                event.id
        <= 3
query qualify_no_window:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        account_id > 0
query qualify_unknown:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        missing > 0
query qualify_joined_ambiguous:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        id > 0
query qualify_cross_domain_collision:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = row_number() window:
            order by:
                event.id
    qualify:
        account_id > 0
query qualify_cross_domain_qualified:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = row_number() window:
            order by:
                event.id
    qualify:
        event.account_id > 0
query qualify_computed_alias:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        doubled = event.metric * 2
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        doubled > 0
query qualify_direct_alias:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        renamed = event.account_id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        renamed > 0
query qualify_direct_alias_input:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        renamed = event.account_id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        account_id > 0
query qualify_let:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.account_id
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        key > 0
query qualify_grouped:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.id
        chain = key
    group by:
        key
    select:
        event_id = event.id
        total = sum(accounts.metric)
        ranked = rank() window:
            order by:
                total
    qualify:
        event_id > 0 and total > 0 and chain > 0
query qualify_grouped_original:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(accounts.metric)
        ranked = rank() window:
            order by:
                total
    qualify:
        event.id > 0
query qualify_selected_bool:
    from accounts
    inner join flags as flag:
        from accounts
        via account_flags: account -> flag
    select:
        previous = lag(flag.active) window:
            order by:
                flag.id
    qualify:
        previous
query qualify_nullable_input_bool:
    from accounts
    inner join flags as flag:
        from accounts
        via account_flags: account -> flag
    select:
        ranked = rank() window:
            order by:
                flag.id
    qualify:
        flag.active
query qualify_scalar_selected:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        previous = lag(event.label) window:
            order by:
                event.id
    qualify:
        len(previous) > 0
query qualify_non_bool:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                event.id
    qualify:
        event.metric
query qualify_aggregate_call:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                event.id
    qualify:
        sum(event.metric) > 0
query qualify_hidden_rank:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        rank() window:
            order by:
                event.id
        <= 3
query qualify_hidden_lag:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        lag(event.metric, 0, event.metric) ignore nulls window:
            order by:
                event.id
        > 0
query qualify_hidden_first_rows:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        first_value(event.metric) ignore nulls window:
            order by:
                event.id
            rows between unbounded preceding and current row exclude ties
        is not null
query qualify_hidden_last_range:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        last_value(event.metric) window:
            order by:
                event.id
            range current row exclude current row
        is null
query qualify_hidden_nth_groups:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        nth_value(event.metric, 2) from last ignore nulls window:
            order by:
                event.id
            groups current row exclude group
        is null
query qualify_hidden_repeated:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        row_number() window:
            order by:
                event.id
        <= 3 and row_number() window:
            order by:
                event.id
        <= 5
query qualify_hidden_invalid:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    qualify:
        lag(missing) window:
            order by:
                event.id
        > 0
query qualify_hidden_selected_input:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        lag(ranked) window:
            order by:
                event.id
        > 0
query qualify_upstream_window_bad:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                id
    qualify:
        true
"""
)


@dataclass(frozen=True, slots=True)
class _Built:
    completion: completion.ProjectCompletion
    filters: row_filter.ProjectJoinedRowFilterSet
    aggregations: aggregation.ProjectJoinedAggregationSet
    windows: windows.ProjectJoinedWindowStageSet
    qualifies: qualify.ProjectJoinedQualifySet


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic = slice10.slice9.slice7._semantic_project(
        tmp_path_factory.mktemp("p63s11") / "project",
        {"main.pietto": QUALIFY_SOURCE},
        reverse_creation=False,
    )
    completed = completion.build_project_completion(
        slice10.slice9.slice7._phase62(semantic)
    )
    filters = row_filter.build_project_joined_row_filters(completed)
    aggregations = aggregation.build_project_joined_aggregations(filters)
    window_set = windows.build_project_joined_window_stages(aggregations)
    return _Built(
        completion=completed,
        filters=filters,
        aggregations=aggregations,
        windows=window_set,
        qualifies=qualify.build_project_joined_qualifies(window_set),
    )


def _result(built: _Built, name: str) -> qualify.ProjectJoinedQualifyResult:
    matches = tuple(
        result
        for result in built.qualifies.results
        if result.window_stage.input_aggregation.input_filter.entry.owner.identity.declared_name
        == name
    )
    assert len(matches) == 1
    return matches[0]


def _codes(result: qualify.ProjectJoinedQualifyResult) -> tuple[str, ...]:
    return tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )


def _parse(source: str):
    return parse_source(source, path="phase63-slice11.pietto")


MINIMAL_PREFIX = """shape Row:
    item: Int not null
    qualify: Int not null
source rows: Row is postgres.table("rows")
"""


def test_qualify_ast_retains_exact_clause_hidden_window_and_precedence() -> None:
    parsed = _parse(
        MINIMAL_PREFIX + "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        "        item\n"
        "    qualify:\n"
        "        row_number() window:\n"
        "            order by:\n"
        "                item\n"
        "        <= 3 and item > 0\n"
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    query = cast(QueryDef, parsed.ast.definitions[-1])
    assert type(query.qualify_clause) is QualifyClause
    assert type(query.qualify_clause.expression) is BinaryExpr
    assert query.qualify_clause.expression.operator == "and"
    left = query.qualify_clause.expression.left
    assert type(left) is ComparisonExpr
    assert type(left.left) is WindowExpr
    assert left.left.use_kind is WindowUseKind.INLINE
    assert left.left.base is None
    assert left.left.span.path == "phase63-slice11.pietto"
    assert tuple(field.name for field in fields(QualifyClause)) == (
        "span",
        "expression",
    )
    assert query.satisfying_clause is None


def test_qualify_keyword_remains_identifier_compatible() -> None:
    parsed = _parse(
        MINIMAL_PREFIX + "query qualify:\n"
        "    from rows\n"
        "    select:\n"
        "        qualify\n"
        "    qualify:\n"
        "        qualify > 0\n"
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    query = cast(QueryDef, parsed.ast.definitions[-1])
    assert query.name == "qualify"
    assert type(query.select_items[0].expression) is NameExpr
    assert query.select_items[0].expression.name == "qualify"
    assert query.qualify_clause is not None
    assert type(query.qualify_clause.expression) is ComparisonExpr
    assert type(query.qualify_clause.expression.left) is NameExpr
    assert query.qualify_clause.expression.left.name == "qualify"


@pytest.mark.parametrize(
    "body",
    (
        "    qualify:\n        item > 0\n    qualify:\n        item < 10\n",
        "    qualify:\n        item > 0\n    satisfying:\n        item > 0\n",
        "    order by:\n        item\n    qualify:\n        item > 0\n",
        "    limit 1\n    qualify:\n        item > 0\n",
        "    qualify:\n",
        "    qualify:\n        row_number() window named\n",
    ),
)
def test_qualify_clause_order_empty_duplicate_and_hidden_named_are_parser_negative(
    body: str,
) -> None:
    parsed = _parse(
        MINIMAL_PREFIX + "query bad:\n    from rows\n    select:\n        item\n" + body
    )
    assert parsed.ast is None
    assert parsed.diagnostics and parsed.diagnostics[0].code == "PIE-P1000"


@pytest.mark.parametrize(
    "body",
    (
        "    where row_number() window:\n        order by:\n            item\n",
        "    let:\n        bad = row_number() window:\n            order by:\n                item\n",
        "    group by:\n        row_number() window:\n            order by:\n                item\n",
    ),
)
def test_global_expression_contexts_still_reject_window_expression(body: str) -> None:
    parsed = _parse(
        MINIMAL_PREFIX + "query bad:\n"
        "    from rows\n" + body + "    select:\n"
        "        item\n"
    )
    assert parsed.ast is None
    assert parsed.diagnostics and parsed.diagnostics[0].code == "PIE-P1000"


def test_existing_source_has_none_qualify_and_selected_window_ast_is_unchanged() -> (
    None
):
    parsed = _parse(
        MINIMAL_PREFIX + "query old:\n"
        "    from rows\n"
        "    select:\n"
        "        ranked = row_number() window:\n"
        "            order by:\n"
        "                item\n"
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    query = cast(QueryDef, parsed.ast.definitions[-1])
    assert query.qualify_clause is None
    expression = query.select_items[0].expression
    assert type(expression) is WindowExpr
    assert expression.use_kind is WindowUseKind.INLINE


def test_absent_and_upstream_nonconcrete_stages_are_closed(built: _Built) -> None:
    absent = _result(built, "absent_stage")
    upstream = _result(built, "qualify_upstream_window_bad")
    assert type(absent) is qualify.ProjectConcreteJoinedQualify
    assert absent.kind is qualify.ProjectJoinedQualifyStageKind.ABSENT
    assert absent.qualify_clause is None
    assert absent.references == () and absent.hidden_computations == ()
    assert not absent.preservation.filters_rows
    assert absent.retention_effects == ()
    assert absent.post_qualify.window_stage is absent.window_stage
    assert type(upstream) is qualify.ProjectNonConcreteJoinedQualify
    assert upstream.reason is (
        qualify.ProjectJoinedQualifyNonConcreteReason.UPSTREAM_WINDOW_NON_CONCRETE
    )
    assert upstream.references == () and upstream.hidden_attempts == ()
    assert upstream.post_qualify is None


def test_selected_result_and_pre_window_references_share_exact_outer_lookup(
    built: _Built,
) -> None:
    selected = _result(built, "qualify_selected")
    input_only = _result(built, "qualify_selected_input_only")
    qualified = _result(built, "qualify_cross_domain_qualified")
    assert all(
        type(result) is qualify.ProjectConcreteJoinedQualify
        for result in (selected, input_only, qualified)
    )
    selected = cast(qualify.ProjectConcreteJoinedQualify, selected)
    assert tuple(type(item.target) for item in selected.references) == (
        windows.ProjectSelectedWindowResultBinding,
        windows.ProjectJoinedWindowInputBinding,
    )
    assert selected.references[0].target is selected.window_stage.selected_results[0]
    assert selected.references[1].target in selected.window_stage.pre_window.bindings
    assert selected.predicate_value_type is not None
    assert selected.predicate_value_type.resolved_type.name == "Bool"
    assert selected.hidden_computations == ()
    assert input_only.window_stage.selected_results
    assert type(qualified.references[0].expression) is DottedNameExpr
    assert qualified.references[0].expression.parts == ("event", "account_id")


def test_joined_and_cross_domain_ambiguity_retain_complete_buckets_without_winner(
    built: _Built,
) -> None:
    joined = _result(built, "qualify_joined_ambiguous")
    collision = _result(built, "qualify_cross_domain_collision")
    assert all(
        type(result) is qualify.ProjectNonConcreteJoinedQualify
        and result.reason
        is qualify.ProjectJoinedQualifyNonConcreteReason.REFERENCE_NON_CONCRETE
        and result.post_qualify is None
        for result in (joined, collision)
    )
    joined_resolution = joined.references[0]
    collision_resolution = collision.references[0]
    assert joined_resolution.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
    assert len(joined_resolution.candidates) == 2
    assert joined_resolution.target is None
    assert collision_resolution.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
    assert tuple(type(item) for item in collision_resolution.candidates) == (
        windows.ProjectJoinedWindowInputBinding,
        windows.ProjectSelectedWindowResultBinding,
    )
    assert collision_resolution.target is None
    assert _codes(joined) == _codes(collision) == ("PIE-S2332",)


def test_projection_aliases_never_flow_backward_but_actual_input_and_let_do(
    built: _Built,
) -> None:
    computed = _result(built, "qualify_computed_alias")
    direct = _result(built, "qualify_direct_alias")
    actual = _result(built, "qualify_direct_alias_input")
    let = _result(built, "qualify_let")
    assert all(
        type(result) is qualify.ProjectNonConcreteJoinedQualify
        and result.references[0].status is ProjectModuleCandidateBucketStatus.ABSENT
        and _codes(result) == ("PIE-S2332",)
        for result in (computed, direct)
    )
    assert type(actual) is qualify.ProjectConcreteJoinedQualify
    assert type(let) is qualify.ProjectConcreteJoinedQualify
    assert actual.references[0].target in actual.window_stage.pre_window.bindings
    assert let.references[0].target in let.window_stage.pre_window.bindings


def test_grouped_outputs_and_group_key_let_are_visible_but_joined_input_is_not(
    built: _Built,
) -> None:
    grouped = _result(built, "qualify_grouped")
    original = _result(built, "qualify_grouped_original")
    assert type(grouped) is qualify.ProjectConcreteJoinedQualify
    assert tuple(
        cast(windows.ProjectJoinedWindowInputBinding, item.target).name
        for item in grouped.references
    ) == ("event_id", "total", "chain")
    assert type(original) is qualify.ProjectNonConcreteJoinedQualify
    assert original.references[0].status is ProjectModuleCandidateBucketStatus.ABSENT
    assert _codes(original) == ("PIE-S2332",)


def test_nullable_bool_selected_input_and_scalar_selected_result_are_legal(
    built: _Built,
) -> None:
    selected_bool = _result(built, "qualify_selected_bool")
    input_bool = _result(built, "qualify_nullable_input_bool")
    scalar = _result(built, "qualify_scalar_selected")
    assert all(
        type(result) is qualify.ProjectConcreteJoinedQualify
        for result in (selected_bool, input_bool, scalar)
    )
    selected_bool = cast(qualify.ProjectConcreteJoinedQualify, selected_bool)
    target = cast(
        windows.ProjectSelectedWindowResultBinding, selected_bool.references[0].target
    )
    assert target.value_type.resolved_type.name == "Bool"
    assert target.value_type.nullability is EffectiveNullability.NULLABLE
    assert selected_bool.predicate_value_type is target.value_type
    input_bool = cast(qualify.ProjectConcreteJoinedQualify, input_bool)
    assert input_bool.predicate_value_type is not None
    assert input_bool.predicate_value_type.nullability is EffectiveNullability.NULLABLE


def test_hidden_window_families_frames_modifiers_and_repeated_sites_reuse_slice10(
    built: _Built,
) -> None:
    names = (
        "qualify_hidden_only",
        "qualify_hidden_rank",
        "qualify_hidden_lag",
        "qualify_hidden_first_rows",
        "qualify_hidden_last_range",
        "qualify_hidden_nth_groups",
        "qualify_hidden_repeated",
    )
    results = tuple(_result(built, name) for name in names)
    assert all(
        type(result) is qualify.ProjectConcreteJoinedQualify for result in results
    )
    concrete = cast(tuple[qualify.ProjectConcreteJoinedQualify, ...], results)
    assert tuple(len(result.hidden_computations) for result in concrete) == (
        1,
        1,
        1,
        1,
        1,
        1,
        2,
    )
    assert all(
        computation.site.occurrence is None
        and computation.site.selected_output_ordinal is None
        and computation.site.item is None
        and computation.site.root is result.window_stage
        for result in concrete
        for computation in result.hidden_computations
    )
    frames = tuple(
        concrete[index]
        .hidden_computations[0]
        .analysis.validated_specification.resolved.frame
        for index in (3, 4, 5)
    )
    assert all(frame.unit is not None for frame in frames)
    units = tuple(frame.unit.value for frame in frames if frame.unit is not None)
    assert units == ("rows", "range", "groups")
    repeated = concrete[-1].hidden_computations
    assert repeated[0] is not repeated[1]
    assert repeated[0].site.expression is not repeated[1].site.expression
    assert all(result.post_qualify.selected_results == () for result in concrete)


def test_hidden_failures_are_atomic_complete_and_cannot_see_selected_results(
    built: _Built,
) -> None:
    invalid = _result(built, "qualify_hidden_invalid")
    sequential = _result(built, "qualify_hidden_selected_input")
    assert all(
        type(result) is qualify.ProjectNonConcreteJoinedQualify
        and result.reason
        is qualify.ProjectJoinedQualifyNonConcreteReason.HIDDEN_WINDOW_NON_CONCRETE
        and result.references == ()
        and len(result.hidden_attempts) == 1
        and result.kernel_value_type is None
        for result in (invalid, sequential)
    )
    assert type(invalid) is qualify.ProjectNonConcreteJoinedQualify
    assert type(sequential) is qualify.ProjectNonConcreteJoinedQualify
    invalid_attempt = cast(
        windows.ProjectNonConcreteWindowComputation,
        invalid.hidden_attempts[0],
    )
    sequential_attempt = cast(
        windows.ProjectNonConcreteWindowComputation,
        sequential.hidden_attempts[0],
    )
    assert invalid_attempt.site.occurrence is None
    assert sequential_attempt.site.occurrence is None
    assert any(
        resolution.expression.name == "ranked"
        and resolution.status is ProjectModuleCandidateBucketStatus.ABSENT
        for resolution in sequential_attempt.resolutions
        if type(resolution.expression) is NameExpr
    )
    assert "PIE-S2103" not in _codes(invalid)
    assert "PIE-S2331" not in _codes(invalid)


def test_window_requirement_reference_bool_and_aggregate_failures_are_distinct(
    built: _Built,
) -> None:
    required = _result(built, "qualify_no_window")
    unknown = _result(built, "qualify_unknown")
    non_bool = _result(built, "qualify_non_bool")
    aggregate_call = _result(built, "qualify_aggregate_call")
    assert type(required) is qualify.ProjectNonConcreteJoinedQualify
    assert required.reason is (
        qualify.ProjectJoinedQualifyNonConcreteReason.WINDOW_COMPUTATION_REQUIRED
    )
    assert _codes(required) == ("PIE-S2331",)
    assert type(unknown) is qualify.ProjectNonConcreteJoinedQualify
    assert (
        unknown.reason
        is qualify.ProjectJoinedQualifyNonConcreteReason.REFERENCE_NON_CONCRETE
    )
    assert _codes(unknown) == ("PIE-S2332",)
    assert "PIE-S2202" not in _codes(unknown)
    assert type(non_bool) is qualify.ProjectNonConcreteJoinedQualify
    assert (
        non_bool.reason
        is qualify.ProjectJoinedQualifyNonConcreteReason.KNOWN_NON_BOOL_PREDICATE
    )
    assert _codes(non_bool) == ("PIE-S2202",)
    assert type(aggregate_call) is qualify.ProjectNonConcreteJoinedQualify
    assert aggregate_call.reason is (
        qualify.ProjectJoinedQualifyNonConcreteReason.SCALAR_KERNEL_NON_CONCRETE
    )
    assert _codes(aggregate_call) == ("PIE-S2308",)


def test_sql_truth_property_and_output_boundaries_are_exact(built: _Built) -> None:
    result = _result(built, "qualify_selected")
    assert type(result) is qualify.ProjectConcreteJoinedQualify
    assert result.retention_effects is row_filter._SQL_ROW_RETENTION_EFFECTS
    assert tuple(
        (item.truth.value, item.retain_row) for item in result.retention_effects
    ) == (("true", True), ("false", False), ("unknown", False))
    preservation = result.preservation
    assert preservation.filters_rows
    assert preservation.multiplicity is row_filter.ProjectJoinedRowMultiplicity.BAG
    assert preservation.window_preservation is result.window_stage.preservation
    assert (
        preservation.intrinsic_grain is result.window_stage.preservation.intrinsic_grain
    )
    assert (
        preservation.relation_ordering
        is result.window_stage.preservation.relation_ordering
    )
    assert (
        preservation.relation_ordering.availability
        is ProjectIRPropertyAvailability.UNKNOWN
    )
    assert not preservation.establishes_relation_order
    assert preservation.selected_results is result.window_stage.selected_results
    assert result.post_qualify.selected_results is result.window_stage.selected_results
    assert result.window_stage.input_aggregation.input_filter.entry.reason is (
        ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
    )
    assert all(
        hidden not in result.post_qualify.selected_results
        for hidden in result.hidden_computations
    )


def test_collection_preserves_exact_slice10_order_and_membership(built: _Built) -> None:
    assert len(built.qualifies.results) == len(built.windows.results)
    assert all(
        result.window_stage is stage
        for result, stage in zip(
            built.qualifies.results,
            built.windows.results,
            strict=True,
        )
    )


def test_scope_kernel_generated_and_contract_boundaries_are_static() -> None:
    grammar = GRAMMAR.read_text(encoding="utf-8")
    production = PRODUCTION.read_text(encoding="utf-8")
    production_names = {
        node.id for node in ast.walk(ast.parse(production)) if type(node) is ast.Name
    }
    ast_source = AST_NODES.read_text(encoding="utf-8")
    builder_source = AST_BUILDER.read_text(encoding="utf-8")
    spec = SPEC.read_text(encoding="utf-8")
    assert "primaryExpression\n    : qualifyWindowExpression" not in grammar
    assert grammar.count("qualifyWindowExpression") == 2
    assert "qualifyWindowExpression\n    : dottedName callSuffix" in grammar
    assert "class QualifyClause" in ast_source
    assert "def _window_expression(" in builder_source
    assert {
        "ProjectIROutputRelationalProperties",
        "ProjectIR",
        "WindowOccurrenceIdentity",
    }.isdisjoint(production_names)
    assert "infer_row_expression(" in production
    assert "analyze_hidden_project_window_computation(" in production
    assert "172 -> 173" in spec and "415 -> 416" in spec
    historical = HISTORICAL_BOUNDARY.read_text(encoding="utf-8")
    assert 'assert "qualifyClause : QUALIFY" in grammar' in historical
    assert "assert \"QUALIFY: 'qualify';\" in grammar" in historical
    assert "A3/M17/D0" in spec
    assert "Slice 12 = `NEXT / NOT IMPLEMENTED`" in spec
