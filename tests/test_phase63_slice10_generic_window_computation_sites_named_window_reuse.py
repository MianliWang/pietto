from __future__ import annotations

import ast
from dataclasses import dataclass, fields, replace
from pathlib import Path
from typing import cast

import pytest

import test_phase63_slice9_joined_grouping_aggregate_global_satisfying_risk_linkage as slice9
from pietto._project import project_completion as completion
from pietto._project import project_joined_aggregation as aggregation
from pietto._project import project_joined_row_filter as row_filter
from pietto._project import project_joined_windows as windows
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_completion import ProjectEffectiveOutputTerminalReason
from pietto._project.project_ir_properties import ProjectIRPropertyAvailability
from pietto._project.window_semantics import WindowDependencyRole
from pietto.ast_nodes import Expression, NameExpr, QueryDef, WindowExpr
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
)
from pietto.semantic.window_analysis import (
    analyze_window_computation,
    analyze_window_expression,
)
from pietto.semantic.window_semantics import (
    NamedWindowResolutionFailure,
    WindowComputationAnalysis,
    WindowExpressionAnalysis,
    WindowOccurrenceIdentity,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_windows.py"
SEMANTIC_ANALYSIS = REPO_ROOT / "src/pietto/semantic/window_analysis.py"
SEMANTIC_NAVIGATION = REPO_ROOT / "src/pietto/semantic/window_navigation_analysis.py"
SEMANTIC_MODEL = REPO_ROOT / "src/pietto/semantic/window_semantics.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice10-generic-window-computation-sites-named-window-reuse-v1.md"
)

WINDOW_SOURCE = (
    slice9.PROJECT_SOURCE
    + """
query window_joined_ok:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        direct = event.id
        chain = direct
        computed = event.metric + 1
    select:
        ordinary = accounts.label
        ranked = row_number() window:
            partition by:
                chain
            order by:
                event.id
        navigated = lag(event.metric, 1, accounts.metric) ignore nulls window:
            order by:
                direct desc
        framed = first_value(event.metric) ignore nulls window:
            order by:
                event.id
            rows between unbounded preceding and current row exclude ties
query window_ambiguous:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                id
query window_computed_let:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        computed = event.metric + 1
    select:
        ranked = rank() window:
            order by:
                computed
query window_relation_fallback:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                events.id
query window_sequential:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = row_number() window:
            order by:
                event.id
        later = rank() window:
            order by:
                ranked
query window_projection_alias:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ordinary = event.id
        ranked = rank() window:
            order by:
                ordinary
query window_grouped_ok:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.id
        key_chain = key
    group by:
        key
    select:
        event_id = event.id
        total = sum(accounts.metric)
        ranked = rank() window:
            partition by:
                key_chain
            order by:
                total
        navigated = lead(total, 0, total) window:
            order by:
                event_id
query window_grouped_raw_input:
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
                accounts.metric
query window_grouped_qualified_input:
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
                event.id
query window_global:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
        ranked = row_number() window:
            order by:
                total
query window_named_ok:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window alias
        extended = dense_rank() window ordered:
            partition by:
                accounts.id
        framed = nth_value(event.metric, 2) from last ignore nulls window framed
    window framed = ordered:
        rows between unbounded preceding and current row exclude current row
    window alias = ordered
    window ordered:
        order by:
            event.id desc
    window later = ordered
query window_named_conflict:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window repeated
    window base:
        order by:
            event.id
    window repeated = base:
        order by:
            accounts.id
query window_named_dangling:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window dangling
    window dangling = missing
query window_named_cycle:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window first
    window first = second
    window second = first
query window_hidden_multihop:
    from accounts
    inner join signals as signal:
        from accounts
        via account_dimension: account -> dimension
        via dimension_signals: dimension -> signal
    select:
        ranked = rank() window:
            order by:
                dimensions.id
"""
)


@dataclass(frozen=True, slots=True)
class _Built:
    completion: completion.ProjectCompletion
    filters: row_filter.ProjectJoinedRowFilterSet
    aggregations: aggregation.ProjectJoinedAggregationSet
    stages: windows.ProjectJoinedWindowStageSet


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    semantic = slice9.slice7._semantic_project(
        tmp_path_factory.mktemp("p63s10") / "project",
        {"main.pietto": WINDOW_SOURCE},
        reverse_creation=False,
    )
    completed = completion.build_project_completion(slice9.slice7._phase62(semantic))
    filters = row_filter.build_project_joined_row_filters(completed)
    aggregations = aggregation.build_project_joined_aggregations(filters)
    return _Built(
        completion=completed,
        filters=filters,
        aggregations=aggregations,
        stages=windows.build_project_joined_window_stages(aggregations),
    )


def _stage(built: _Built, name: str) -> windows.ProjectJoinedWindowStageResult:
    matches = tuple(
        result
        for result in built.stages.results
        if result.input_aggregation.input_filter.entry.owner.identity.declared_name
        == name
    )
    assert len(matches) == 1
    return matches[0]


def _codes(result: windows.ProjectJoinedWindowStageResult) -> tuple[str, ...]:
    return tuple(
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )


def _selected_expression(stage: windows.ProjectConcreteJoinedWindowStage, index: int):
    return stage.computations[index].site.expression


def test_selected_and_hidden_site_identity_domains_are_exact(built: _Built) -> None:
    stage = _stage(built, "window_joined_ok")
    assert type(stage) is windows.ProjectConcreteJoinedWindowStage
    selected = stage.computations[0]
    definition = stage.input_aggregation.input_filter.entry.owner.definition
    assert type(definition) is QueryDef
    assert (
        selected.site.kind is windows.ProjectWindowComputationSiteKind.SELECTED_OUTPUT
    )
    assert selected.site.root is stage.input_aggregation
    assert selected.site.item is definition.select_items[1]
    assert selected.site.occurrence is stage.selected_results[0].occurrence
    assert tuple(field.name for field in fields(WindowOccurrenceIdentity)) == (
        "source_id",
        "relation_name",
        "selected_output_ordinal",
        "span",
    )

    hidden = windows.analyze_hidden_project_window_computation(
        stage,
        selected.site.expression,
    )
    assert type(hidden) is windows.ProjectConcreteWindowComputation
    assert hidden.site.kind is windows.ProjectWindowComputationSiteKind.HIDDEN_INLINE
    assert hidden.site.root is stage
    assert hidden.site.item is None
    assert hidden.site.selected_output_ordinal is None
    assert hidden.site.occurrence is None
    assert hidden not in stage.computations
    assert stage.post_window.selected_results is stage.selected_results


def test_exact_query_block_and_named_dag_are_reused(built: _Built) -> None:
    stage = _stage(built, "window_named_ok")
    assert type(stage) is windows.ProjectConcreteJoinedWindowStage
    bridge = stage.input_aggregation.input_filter.namespace.binding_environment.scalar_environment.query_block.owner_bridge
    assert stage.named_namespace.query_block is bridge.query_block
    assert tuple(item.declaration.name for item in stage.named_namespace.templates) == (
        "framed",
        "alias",
        "ordered",
        "later",
    )
    assert tuple(
        next(
            template.declaration.name
            for template in stage.named_namespace.templates
            if template.occurrence is occurrence
        )
        for occurrence in stage.named_namespace.resolution_order
    ) == ("ordered", "alias", "framed", "later")
    direct, extended, framed = stage.computations
    assert direct.analysis.resolved_named_use is not None
    assert extended.analysis.resolved_named_use is not None
    assert framed.analysis.resolved_named_use is not None
    alias_template = stage.named_namespace.template_for_name("alias")
    ordered_template = stage.named_namespace.template_for_name("ordered")
    framed_template = stage.named_namespace.template_for_name("framed")
    assert alias_template is not None
    assert ordered_template is not None
    assert framed_template is not None
    assert direct.semantic_provenance.named_target is alias_template.occurrence
    assert extended.semantic_provenance.named_target is ordered_template.occurrence
    assert framed.semantic_provenance.named_target is framed_template.occurrence
    assert framed.semantic_provenance.order_origin.value == "inherited"
    assert framed.semantic_provenance.frame_origin.value == "inherited"
    assert framed_template.frame_provenance is not None
    assert framed_template.frame_provenance.origin.value == "locally_authored"
    assert framed.semantic_provenance.nth_direction is not None
    assert framed.semantic_provenance.nth_direction_is_explicit
    assert framed.semantic_provenance.null_treatment is not None
    assert framed.semantic_provenance.null_treatment_is_explicit


def test_named_namespace_failures_precede_function_computation(built: _Built) -> None:
    conflict = _stage(built, "window_named_conflict")
    dangling = _stage(built, "window_named_dangling")
    cycle = _stage(built, "window_named_cycle")
    assert all(
        type(result) is windows.ProjectNonConcreteJoinedWindowStage
        and result.reason
        is windows.ProjectJoinedWindowStageNonConcreteReason.NAMED_NAMESPACE_NON_CONCRETE
        and type(result.named_failure) is NamedWindowResolutionFailure
        and result.attempts == ()
        and result.post_window is None
        for result in (conflict, dangling, cycle)
    )
    assert _codes(conflict) == ("PIE-S2113",)
    assert _codes(dangling) == ("PIE-S2111",)
    assert _codes(cycle) == ("PIE-S2112",)


def test_joined_input_is_occurrence_safe_and_let_admission_is_bounded(
    built: _Built,
) -> None:
    good = _stage(built, "window_joined_ok")
    ambiguous = _stage(built, "window_ambiguous")
    computed = _stage(built, "window_computed_let")
    fallback = _stage(built, "window_relation_fallback")
    hidden = _stage(built, "window_hidden_multihop")
    assert type(good) is windows.ProjectConcreteJoinedWindowStage
    assert good.named_namespace.declarations == ()
    kinds = tuple(binding.kind for binding in good.pre_window.bindings)
    assert windows.ProjectJoinedWindowInputBindingKind.FIELD_BACKED_LET in kinds
    assert tuple(
        binding.name
        for binding in good.pre_window.bindings
        if binding.kind is windows.ProjectJoinedWindowInputBindingKind.FIELD_BACKED_LET
    ) == ("direct", "chain")
    assert not any(binding.name == "computed" for binding in good.pre_window.bindings)
    assert any(
        binding.qualifier == "event" and binding.name == "id"
        for binding in good.pre_window.bindings
    )
    assert not any(
        binding.qualifier == "events" for binding in good.pre_window.bindings
    )
    bare_unique = good.pre_window.candidates(
        NameExpr(
            span=good.computations[0].analysis.order_bindings[0].expression.span,
            name="account_id",
        )
    )
    assert len(bare_unique) == 1 and bare_unique[0].name == "account_id"

    assert all(
        type(result) is windows.ProjectNonConcreteJoinedWindowStage
        and result.post_window is None
        for result in (ambiguous, computed, fallback, hidden)
    )
    ambiguous_attempt = cast(
        windows.ProjectNonConcreteJoinedWindowStage,
        ambiguous,
    ).attempts[0]
    assert type(ambiguous_attempt) is windows.ProjectNonConcreteWindowComputation
    ambiguous_resolution = next(
        item
        for item in ambiguous_attempt.resolutions
        if type(item.expression) is NameExpr and item.expression.name == "id"
    )
    assert ambiguous_resolution.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS
    assert len(ambiguous_resolution.candidates) == 2
    assert ambiguous_resolution.target is None


def test_grouped_inputs_are_exact_stage_outputs_and_group_key_let_aliases(
    built: _Built,
) -> None:
    good = _stage(built, "window_grouped_ok")
    raw = _stage(built, "window_grouped_raw_input")
    qualified = _stage(built, "window_grouped_qualified_input")
    assert type(good) is windows.ProjectConcreteJoinedWindowStage
    assert tuple(binding.name for binding in good.pre_window.bindings) == (
        "event_id",
        "total",
        "key",
        "key_chain",
    )
    assert tuple(binding.kind for binding in good.pre_window.bindings) == (
        windows.ProjectJoinedWindowInputBindingKind.GROUP_KEY,
        windows.ProjectJoinedWindowInputBindingKind.AGGREGATE_RESULT,
        windows.ProjectJoinedWindowInputBindingKind.GROUP_KEY_BACKED_LET,
        windows.ProjectJoinedWindowInputBindingKind.GROUP_KEY_BACKED_LET,
    )
    assert all(binding.qualifier is None for binding in good.pre_window.bindings)
    targets = tuple(
        dependency.target
        for computation in good.computations
        for dependency in computation.dependencies
        if dependency.role is not WindowDependencyRole.RELATION_INPUT
    )
    assert all(
        type(target) is windows.ProjectJoinedWindowInputBinding for target in targets
    )
    assert tuple(
        cast(windows.ProjectJoinedWindowInputBinding, target).name for target in targets
    ) == ("key_chain", "total", "total", "total", "event_id")
    assert all(
        type(result) is windows.ProjectNonConcreteJoinedWindowStage
        and result.post_window is None
        for result in (raw, qualified)
    )


def test_global_and_upstream_terminals_remain_fail_closed(built: _Built) -> None:
    global_absent = _stage(built, "global_safe")
    global_window = _stage(built, "window_global")
    upstream = _stage(built, "upstream_filter_blocked")
    assert type(global_absent) is windows.ProjectConcreteJoinedWindowStage
    assert global_absent.kind is windows.ProjectJoinedWindowStageKind.ABSENT
    assert global_absent.computations == ()
    assert global_absent.post_window.selected_results == ()
    assert type(global_window) is windows.ProjectNonConcreteJoinedWindowStage
    assert global_window.reason is (
        windows.ProjectJoinedWindowStageNonConcreteReason.SELECTED_COMPUTATION_NON_CONCRETE
    )
    assert global_window.post_window is None
    assert type(upstream) is windows.ProjectNonConcreteJoinedWindowStage
    assert upstream.reason is (
        windows.ProjectJoinedWindowStageNonConcreteReason.UPSTREAM_AGGREGATION_NON_CONCRETE
    )
    assert (
        upstream.input_aggregation
        is _stage(built, "upstream_filter_blocked").input_aggregation
    )


def test_same_pre_window_namespace_blocks_sequential_and_projection_alias_leaks(
    built: _Built,
) -> None:
    sequential = _stage(built, "window_sequential")
    projection = _stage(built, "window_projection_alias")
    assert type(sequential) is windows.ProjectNonConcreteJoinedWindowStage
    assert len(sequential.attempts) == 2
    assert type(sequential.attempts[0]) is windows.ProjectConcreteWindowComputation
    assert type(sequential.attempts[1]) is windows.ProjectNonConcreteWindowComputation
    assert all(
        attempt.input_namespace is sequential.pre_window
        for attempt in sequential.attempts
    )
    later = cast(windows.ProjectNonConcreteWindowComputation, sequential.attempts[1])
    assert later.resolutions[-1].status is ProjectModuleCandidateBucketStatus.ABSENT
    assert type(later.resolutions[-1].expression) is NameExpr
    assert later.resolutions[-1].expression.name == "ranked"
    assert sequential.post_window is None and sequential.selected_results == ()

    assert type(projection) is windows.ProjectNonConcreteJoinedWindowStage
    attempt = cast(windows.ProjectNonConcreteWindowComputation, projection.attempts[0])
    assert attempt.resolutions[-1].status is ProjectModuleCandidateBucketStatus.ABSENT
    assert type(attempt.resolutions[-1].expression) is NameExpr
    assert attempt.resolutions[-1].expression.name == "ordinary"


def test_selected_results_and_dependencies_preserve_source_order_and_multiplicity(
    built: _Built,
) -> None:
    stage = _stage(built, "window_joined_ok")
    assert type(stage) is windows.ProjectConcreteJoinedWindowStage
    assert tuple(result.output_name for result in stage.selected_results) == (
        "ranked",
        "navigated",
        "framed",
    )
    assert tuple(
        result.selected_output_ordinal for result in stage.selected_results
    ) == (
        1,
        2,
        3,
    )
    assert stage.post_window.input_candidates("ordinary") == ()
    assert stage.post_window.selected_candidates("ranked") == (
        stage.selected_results[0],
    )
    assert tuple(item.role for item in stage.computations[0].dependencies) == (
        WindowDependencyRole.RELATION_INPUT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(item.role for item in stage.computations[1].dependencies) == (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_DEFAULT,
        WindowDependencyRole.WINDOW_ORDER,
    )
    assert tuple(
        item.global_ordinal for item in stage.computations[1].dependencies
    ) == (
        0,
        1,
        2,
    )


def test_hidden_inline_reuses_kernel_but_never_becomes_nameable(built: _Built) -> None:
    stage = _stage(built, "window_joined_ok")
    named = _stage(built, "window_named_ok")
    assert type(stage) is windows.ProjectConcreteJoinedWindowStage
    assert type(named) is windows.ProjectConcreteJoinedWindowStage
    hidden_ranking = windows.analyze_hidden_project_window_computation(
        stage,
        _selected_expression(stage, 0),
    )
    hidden_navigation = windows.analyze_hidden_project_window_computation(
        stage,
        _selected_expression(stage, 1),
    )
    hidden_frame = windows.analyze_hidden_project_window_computation(
        stage,
        _selected_expression(stage, 2),
    )
    assert all(
        type(result) is windows.ProjectConcreteWindowComputation
        and result.site.occurrence is None
        and result.site.item is None
        and result.site.selected_output_ordinal is None
        for result in (hidden_ranking, hidden_navigation, hidden_frame)
    )
    assert (
        cast(
            windows.ProjectConcreteWindowComputation, hidden_navigation
        ).analysis.navigation
        is not None
    )
    assert (
        cast(
            windows.ProjectConcreteWindowComputation, hidden_frame
        ).analysis.frame_value
        is not None
    )
    assert stage.post_window.selected_results == stage.selected_results
    rejected = windows.analyze_hidden_project_window_computation(
        stage,
        named.computations[0].site.expression,
    )
    assert type(rejected) is windows.ProjectNonConcreteHiddenWindowComputation
    assert rejected.site is None and rejected.occurrence is None
    global_stage = _stage(built, "global_safe")
    assert type(global_stage) is windows.ProjectConcreteJoinedWindowStage
    hidden_global = windows.analyze_hidden_project_window_computation(
        global_stage,
        _selected_expression(stage, 0),
    )
    assert type(hidden_global) is windows.ProjectNonConcreteWindowComputation
    assert hidden_global.site.occurrence is None
    assert hidden_global.result_binding is None


def test_exact_namespace_and_dependency_carriers_reject_lossy_grafts(
    built: _Built,
) -> None:
    stage = _stage(built, "window_joined_ok")
    assert type(stage) is windows.ProjectConcreteJoinedWindowStage
    with pytest.raises(ValueError, match="complete and ordered"):
        replace(stage.pre_window, bindings=stage.pre_window.bindings[1:])
    computation = stage.computations[0]
    with pytest.raises(ValueError, match="cover exact input occurrences"):
        replace(computation, resolutions=computation.resolutions[1:])
    cloned_namespace = replace(stage.pre_window)
    relation_dependency = computation.dependencies[0]
    assert relation_dependency.role is WindowDependencyRole.RELATION_INPUT
    grafted_dependency = replace(relation_dependency, target=cloned_namespace)
    with pytest.raises(ValueError, match="exact role and targets"):
        replace(
            computation,
            dependencies=(grafted_dependency, *computation.dependencies[1:]),
        )


def _standalone_pair(call: str, *, frame: str | None = None):
    frame_source = "" if frame is None else f"            {frame}\n"
    parsed = parse_source(
        "shape Row:\n"
        "    id: Int not null\n"
        "    value: Int nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        "query result:\n"
        "    from rows\n"
        "    select:\n"
        f"        result = {call} window:\n"
        "            partition by:\n"
        "                id\n"
        "            order by:\n"
        "                value desc\n"
        f"{frame_source}",
        path="slice10-differential.pietto",
    )
    assert parsed.diagnostics == () and parsed.ast is not None
    definition = cast(QueryDef, parsed.ast.definitions[-1])
    item = definition.select_items[0]
    expression = cast(WindowExpr, item.expression)
    schema = RowSchema(
        fields={
            "id": RowField(
                name="id",
                resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
                nullability=EffectiveNullability.NON_NULL,
            ),
            "value": RowField(
                name="value",
                resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
                nullability=EffectiveNullability.NULLABLE,
            ),
        }
    )
    historical_types: dict[Expression, ValueType] = {}
    historical_diagnostics = []
    historical = analyze_window_expression(
        definition=definition,
        item=item,
        selected_output_ordinal=0,
        source_id="slice10-differential.pietto",
        input_schema=schema,
        field_qualifier="rows",
        value_types=historical_types,
        diagnostics=historical_diagnostics,
    )
    common_types: dict[Expression, ValueType] = {}
    common_diagnostics = []
    common = analyze_window_computation(
        expression=expression,
        input_schema=schema,
        field_qualifier="rows",
        value_types=common_types,
        diagnostics=common_diagnostics,
    )
    assert historical_diagnostics == common_diagnostics == []
    assert type(historical) is WindowExpressionAnalysis
    assert type(common) is WindowComputationAnalysis
    return historical, common


@pytest.mark.parametrize(
    "call",
    (
        "row_number()",
        "rank()",
        "dense_rank()",
        "percent_rank()",
        "cume_dist()",
        "ntile(4)",
        "lag(value)",
        "lead(value, 0, value)",
        "first_value(value)",
        "last_value(value) ignore nulls",
        "nth_value(value, 2) from last",
    ),
)
def test_common_kernel_is_differentially_compatible_for_all_builtin_families(
    call: str,
) -> None:
    historical, common = _standalone_pair(call)
    assert historical.semantic_fact.result == common.result
    assert historical.validated_specification == common.validated_specification
    assert historical.partition_binding_fact.bindings == common.partition_bindings
    assert historical.order_binding_fact.bindings == common.order_bindings
    assert (historical.ranking_fact is None) is (common.ranking_advance_policy is None)
    assert (historical.distribution_fact is None) is (
        common.distribution_policy is None
    )
    assert (historical.navigation_fact is None) is (common.navigation is None)
    assert (historical.frame_value_fact is None) is (common.frame_value is None)


@pytest.mark.parametrize(
    ("call", "frame", "unit", "exclusion"),
    (
        (
            "first_value(value)",
            "rows between unbounded preceding and current row exclude ties",
            "rows",
            "ties",
        ),
        (
            "last_value(value) ignore nulls",
            "range current row exclude current row",
            "range",
            "current_row",
        ),
        (
            "nth_value(value, 2) from last",
            "groups current row exclude group",
            "groups",
            "group",
        ),
    ),
)
def test_common_kernel_projects_rows_range_groups_exclude_and_modifiers(
    call: str,
    frame: str,
    unit: str,
    exclusion: str,
) -> None:
    historical, common = _standalone_pair(call, frame=frame)
    resolved = common.validated_specification.resolved.frame
    assert resolved.unit is not None and resolved.unit.value == unit
    assert resolved.exclusion is not None and resolved.exclusion.value == exclusion
    assert historical.validated_specification == common.validated_specification


def test_window_stage_preserves_rows_grain_properties_and_pending_ledger(
    built: _Built,
) -> None:
    stage = _stage(built, "window_joined_ok")
    assert type(stage) is windows.ProjectConcreteJoinedWindowStage
    preservation = stage.preservation
    input_preservation = stage.input_aggregation.input_filter.preservation
    assert preservation.input_filter_preservation is input_preservation
    assert preservation.multiplicity is row_filter.ProjectJoinedRowMultiplicity.BAG
    assert (
        preservation.intrinsic_grain is input_preservation.input_property_bridge.grain
    )
    assert (
        preservation.relation_ordering
        is input_preservation.input_property_bridge.ordering
    )
    assert (
        preservation.relation_ordering.availability
        is ProjectIRPropertyAvailability.UNKNOWN
    )
    assert not preservation.filters_rows
    assert not preservation.establishes_relation_order
    assert stage.input_aggregation.input_filter.entry.reason is (
        ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
    )
    assert stage.input_aggregation.input_filter.entry in built.completion.entries


def test_collection_is_one_for_one_in_canonical_slice9_order(built: _Built) -> None:
    assert len(built.stages.results) == len(built.aggregations.results)
    assert all(
        stage.input_aggregation is aggregate
        for stage, aggregate in zip(
            built.stages.results,
            built.aggregations.results,
            strict=True,
        )
    )


def test_scope_identity_kernel_and_contract_boundaries_are_static() -> None:
    production = PRODUCTION.read_text(encoding="utf-8")
    production_names = {
        node.id for node in ast.walk(ast.parse(production)) if type(node) is ast.Name
    }
    analysis = SEMANTIC_ANALYSIS.read_text(encoding="utf-8")
    navigation = SEMANTIC_NAVIGATION.read_text(encoding="utf-8")
    semantic_model = SEMANTIC_MODEL.read_text(encoding="utf-8")
    spec = SPEC.read_text(encoding="utf-8")
    assert {
        "RowSchema",
        "build_project_window_persistence",
        "ProjectIROutputRelationalProperties",
        "WindowResultIdentity",
        "ProjectModuleRowFieldIdentity",
    }.isdisjoint(production_names)
    assert "analyze_window_computation(" in analysis
    assert "analyze_navigation_computation_arguments(" in navigation
    assert "analyze_frame_value_computation_arguments(" in navigation
    assert "class WindowComputationAnalysis" in semantic_model
    assert "resolve_named_window_namespace_for_query_block" in semantic_model
    assert "171 -> 172" in spec and "414 -> 415" in spec
    assert "A3/M7/D0" in spec
    assert "Slice 11 = `NEXT / NOT IMPLEMENTED`" in spec
