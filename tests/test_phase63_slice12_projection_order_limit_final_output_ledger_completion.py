from __future__ import annotations

import ast
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

import pytest

import test_phase63_slice11_qualify_grammar_ast_semantics_property_transfer as slice11
import test_phase63_slice7_completion_scheduling_effective_output_ledger_module_propagation as slice7
from pietto._project import project_completion as completion
from pietto._project import project_final_outputs as final_outputs
from pietto._project import project_joined_aggregation as aggregation
from pietto._project import project_joined_qualify as qualify
from pietto._project import project_joined_row_filter as row_filter
from pietto._project import project_joined_windows as windows
from pietto._project.module_attribution import ProjectModuleRowFieldKind
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_completion import (
    ProjectEffectiveOutputTerminalReason,
    ProjectExistingEffectiveOutput,
)
from pietto._project.project_joined_aggregation import (
    ProjectJoinedAggregationMode,
    ProjectJoinedGroupKeyOccurrence,
)
from pietto._project.project_joined_windows import (
    ProjectSelectedWindowResultBinding,
)
from pietto._project.project_scalar_namespaces import (
    ProjectConcreteJoinedNamespaceExpression,
)
from pietto._project.project_scalar_references import (
    ProjectScalarReferenceResolution,
)
from pietto.ast_nodes import DottedNameExpr, QueryDef


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_final_outputs.py"
QUALIFY_PRODUCTION = REPO_ROOT / "src/pietto/_project/project_joined_qualify.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice12-projection-order-limit-final-output-ledger-completion-v1.md"
)

SLICE12_SOURCE = (
    slice11.QUALIFY_SOURCE
    + """
query final_projection:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.account_id
    select:
        account_id
        bound = event.id
        let_key = key
        doubled = event.metric * 2
        ranked = row_number() window:
            order by:
                event.id
query final_alias_backward:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        first = event.account_id
        second = first
query final_unnamed:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event.metric + 1
query final_duplicate:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        repeated = event.id
        repeated = event.account_id
query final_unknown:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        missing
query final_order_absent:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    let:
        key = event.account_id
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id desc
    order by:
        event.metric desc
        key asc
        ranked
query final_order_input_precedence:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        account_id = row_number() window:
            order by:
                event.id
    order by:
        account_id
query final_order_ambiguous_input:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        id = row_number() window:
            order by:
                event.id
    order by:
        id
query final_order_projection_alias:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        renamed = event.account_id
    order by:
        renamed
query final_grouped_order:
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
            order by:
                total
    order by:
        event_id
        total desc
        key_chain asc
        ranked
query final_grouped_order_raw:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(accounts.metric)
    order by:
        metric
query final_grouped_order_scalar:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(accounts.metric)
    order by:
        total + 1
query final_global_order:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        total = sum(event.metric)
    order by:
        total
query final_window_order_only:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        ranked = rank() window:
            order by:
                event.id desc
query final_limit_zero:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit 0
query final_limit_one:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit 1
query final_limit_max:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit 9223372036854775807
query final_limit_large:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit 9223372036854775808
query final_limit_negative:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit -1
query final_limit_float:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit 1.5
query final_limit_string:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit "1"
query final_limit_name:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit event_id
query final_limit_call:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    limit len("x")
query replay_passthrough:
    from accounts
    select:
        id
query replay_selected:
    from accounts
    select:
        id
        ranked = row_number() window:
            order by:
                id
    qualify:
        ranked <= 3 and id > 0
query replay_hidden:
    from accounts
    select:
        id
    qualify:
        row_number() window:
            order by:
                id
        <= 3
query replay_no_window:
    from accounts
    select:
        id
    qualify:
        id > 0
query replay_global_hidden:
    from accounts
    select:
        total = sum(metric)
    qualify:
        row_number() window:
            order by:
                total
        <= 1
query replay_ambiguous:
    from accounts
    select:
        id = row_number() window:
            order by:
                accounts.id
    qualify:
        id > 0
query replay_order:
    from accounts
    let:
        key = id
    where id > 0
    select:
        id
        ranked = row_number() window:
            order by:
                id
    qualify:
        ranked <= 3
    order by:
        metric desc
        key asc
        ranked
    limit 1
query replay_grouped:
    from accounts
    group by:
        id
    select:
        id
        total = sum(metric)
        ranked = rank() window:
            order by:
                total
    qualify:
        ranked <= 3
    order by:
        id desc
        ranked
"""
)


@dataclass(frozen=True, slots=True)
class _Built:
    completion: completion.ProjectCompletion
    qualifies: qualify.ProjectJoinedQualifySet
    outputs: final_outputs.ProjectEffectiveOutputCompletion


def _build(root: Path, files: dict[str, str]) -> _Built:
    semantic = slice7._semantic_project(root, files, reverse_creation=False)
    base = completion.build_project_completion(slice7._phase62(semantic))
    filters = row_filter.build_project_joined_row_filters(base)
    aggregations = aggregation.build_project_joined_aggregations(filters)
    window_set = windows.build_project_joined_window_stages(aggregations)
    qualifies = qualify.build_project_joined_qualifies(window_set)
    return _Built(
        completion=base,
        qualifies=qualifies,
        outputs=final_outputs.build_project_effective_output_completion(
            base,
            qualifies,
        ),
    )


def _rebuild_from_same_completion(built: _Built) -> _Built:
    filters = row_filter.build_project_joined_row_filters(built.completion)
    aggregations = aggregation.build_project_joined_aggregations(filters)
    window_set = windows.build_project_joined_window_stages(aggregations)
    qualifies = qualify.build_project_joined_qualifies(window_set)
    return _Built(
        completion=built.completion,
        qualifies=qualifies,
        outputs=final_outputs.build_project_effective_output_completion(
            built.completion,
            qualifies,
        ),
    )


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(
        tmp_path_factory.mktemp("p63s12") / "project",
        {"main.pietto": SLICE12_SOURCE},
    )


@pytest.fixture(scope="module")
def propagated(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    files = slice7._project_files()
    files["c.pietto"] = files["c.pietto"].replace(
        "query joined_a:\n"
        "    from customers\n"
        "    inner join orders as orders:\n"
        "        from customers\n"
        "        via customer_orders: customer -> orders\n"
        "    select:\n"
        "        id\n",
        "query joined_a:\n"
        "    from customers\n"
        "    inner join orders as orders:\n"
        "        from customers\n"
        "        via customer_orders: customer -> orders\n"
        "    select:\n"
        "        order_id = orders.id\n",
    )
    files["a.pietto"] = files["a.pietto"].replace(
        "query downstream_b:\n"
        "    from JoinedInput\n"
        "    select:\n"
        "        id\n"
        "query downstream_c:\n"
        "    from downstream_b\n"
        "    select:\n"
        "        id\n",
        "query downstream_b:\n"
        "    from JoinedInput\n"
        "    select:\n"
        "        order_id\n"
        "query downstream_c:\n"
        "    from downstream_b\n"
        "    select:\n"
        "        order_id\n",
    )
    return _build(
        tmp_path_factory.mktemp("p63s12-propagation") / "project",
        files,
    )


def _entry(
    built: _Built,
    name: str,
) -> final_outputs.ProjectEffectiveOutputCompletionEntry:
    matches = tuple(
        entry
        for entry in built.outputs.entries
        if entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _base_entry(
    built: _Built,
    name: str,
) -> completion.ProjectEffectiveOutputEntry:
    matches = tuple(
        entry
        for entry in built.completion.entries
        if entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _completed(
    built: _Built,
    name: str,
) -> final_outputs.ProjectCompletedEffectiveOutput:
    result = _entry(built, name)
    assert type(result) is final_outputs.ProjectCompletedEffectiveOutput
    return result


def _terminal(
    built: _Built,
    name: str,
) -> final_outputs.ProjectEffectiveOutputCompletionTerminal:
    result = _entry(built, name)
    assert type(result) is final_outputs.ProjectEffectiveOutputCompletionTerminal
    return result


def test_overlay_retains_exact_slice7_roots_order_schedule_and_entry_cardinality(
    built: _Built,
) -> None:
    outputs = built.outputs
    assert outputs.base is built.completion
    assert outputs.joined_qualifies is built.qualifies
    assert outputs.owners is built.completion.owners
    assert outputs.dependencies is built.completion.dependencies
    assert outputs.schedule is built.completion.schedule
    assert len(outputs.entries) == len(outputs.owners)
    assert tuple(entry.owner for entry in outputs.entries) == outputs.owners
    assert len({id(entry.owner) for entry in outputs.entries}) == len(outputs.entries)


def test_historical_complete_output_is_reused_but_authored_qualify_is_replayed(
    built: _Built,
) -> None:
    passthrough = _base_entry(built, "replay_passthrough")
    selected = _base_entry(built, "replay_selected")
    assert type(passthrough) is ProjectExistingEffectiveOutput
    assert type(selected) is ProjectExistingEffectiveOutput
    assert _entry(built, "replay_passthrough") is passthrough
    replayed = _completed(built, "replay_selected")
    assert replayed.base_entry is selected
    assert type(replayed.root) is final_outputs.ProjectConcreteNoJoinReplay
    assert replayed.root.semantic_facts is selected.fragment.semantic_facts


def test_final_projection_retains_select_identity_role_and_closed_source_union(
    built: _Built,
) -> None:
    result = _completed(built, "final_projection")
    definition = cast(QueryDef, result.owner.definition)
    semantic = built.completion.plan.semantic_facts.find_owner(result.owner)[0]
    assert tuple(field.item for field in result.fields) == definition.select_items
    assert tuple(field.select_fact for field in result.fields) == semantic.select_facts
    assert tuple(field.selected_output_ordinal for field in result.fields) == tuple(
        range(5)
    )
    assert tuple(field.output_name for field in result.fields) == (
        "account_id",
        "bound",
        "let_key",
        "doubled",
        "ranked",
    )
    for ordinal, output in enumerate(result.fields):
        assert output.identity.owner == final_outputs._declaration_identity(
            result.owner
        )
        assert output.identity.kind is ProjectModuleRowFieldKind.RELATION_OUTPUT
        assert output.identity.field_position == ordinal
        assert output.identity.name == output.output_name == output.field.name
        assert result.schema.fields[output.output_name] is output.field
    assert all(
        field.result_role is final_outputs.ProjectRowResultRole.ORDINARY_ROW_VALUE
        for field in result.fields[:-1]
    )
    assert (
        result.fields[-1].result_role
        is final_outputs.ProjectRowResultRole.WINDOW_RESULT
    )
    assert all(
        type(field.source) is ProjectConcreteJoinedNamespaceExpression
        for field in result.fields[:-1]
    )
    assert type(result.fields[-1].source) is ProjectSelectedWindowResultBinding
    dotted = cast(
        ProjectConcreteJoinedNamespaceExpression,
        result.fields[1].source,
    )
    resolution = cast(ProjectScalarReferenceResolution, dotted.resolutions[0])
    assert type(dotted.expression) is DottedNameExpr
    assert resolution.target is not None
    assert resolution.target.evidence.name == "id"
    assert result.fields[1].field.resolved_type is (
        resolution.target.evidence.resolved_type
    )


def test_grouped_global_and_window_projection_roles_reuse_exact_slice9_10_results(
    built: _Built,
) -> None:
    grouped = _completed(built, "window_grouped_ok")
    assert tuple(item.result_role for item in grouped.fields) == (
        final_outputs.ProjectRowResultRole.GROUP_KEY,
        final_outputs.ProjectRowResultRole.AGGREGATE_RESULT,
        final_outputs.ProjectRowResultRole.WINDOW_RESULT,
        final_outputs.ProjectRowResultRole.WINDOW_RESULT,
    )
    assert all(
        type(item.source) is aggregation.ProjectJoinedStageOutputOccurrence
        for item in grouped.fields[:2]
    )
    assert all(
        type(item.source) is ProjectSelectedWindowResultBinding
        for item in grouped.fields[2:]
    )
    global_result = _completed(built, "global_safe")
    assert all(
        item.result_role is final_outputs.ProjectRowResultRole.AGGREGATE_RESULT
        for item in global_result.fields
    )
    assert all(
        type(item.source) is aggregation.ProjectJoinedStageOutputOccurrence
        for item in global_result.fields
    )


@pytest.mark.parametrize(
    "name, code",
    [
        ("final_unnamed", "PIE-S2304"),
        ("final_duplicate", "PIE-S2305"),
        ("final_unknown", None),
        ("final_alias_backward", None),
    ],
)
def test_projection_failures_publish_no_partial_output(
    built: _Built,
    name: str,
    code: str | None,
) -> None:
    result = _terminal(built, name)
    assert result.reason is (
        final_outputs.ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
    )
    assert result.output is None
    if code is not None:
        assert tuple(item.code for item in result.diagnostics) == (code,)


def test_hidden_qualify_window_never_becomes_an_automatic_final_field(
    built: _Built,
) -> None:
    result = _completed(built, "qualify_hidden_only")
    assert tuple(item.output_name for item in result.fields) == ("event_id",)
    root = cast(qualify.ProjectConcreteJoinedQualify, result.root)
    assert len(root.hidden_computations) == 1


def test_row_domain_postures_do_not_leak_grouped_preaggregation_grain(
    built: _Built,
) -> None:
    absent = _completed(built, "final_projection")
    grouped = _completed(built, "grouped_safe")
    global_result = _completed(built, "global_safe")
    assert (
        absent.row_domain.kind is final_outputs.ProjectCompletedRowDomainKind.PRESERVED
    )
    absent_root = cast(qualify.ProjectConcreteJoinedQualify, absent.root)
    assert absent.row_domain.preserved is absent_root.preservation.intrinsic_grain
    assert (
        grouped.row_domain.kind is final_outputs.ProjectCompletedRowDomainKind.GROUPED
    )
    assert grouped.row_domain.preserved is None
    grouped_root = cast(qualify.ProjectConcreteJoinedQualify, grouped.root)
    assert grouped.row_domain.grouped_basis == (
        grouped_root.window_stage.input_aggregation.group_keys
    )
    assert all(
        type(item) is ProjectJoinedGroupKeyOccurrence
        for item in grouped.row_domain.grouped_basis
    )
    assert (
        global_result.row_domain.kind
        is final_outputs.ProjectCompletedRowDomainKind.GLOBAL
    )
    assert global_result.row_domain.preserved is None
    assert global_result.row_domain.grouped_basis == ()


def test_absent_relation_order_preserves_scope_precedence_source_order_and_direction(
    built: _Built,
) -> None:
    result = _completed(built, "final_order_absent")
    ordering = result.ordering
    assert ordering is not None
    definition = cast(QueryDef, result.owner.definition)
    clause = definition.order_by_clause
    assert clause is not None
    assert ordering.clause is clause
    assert tuple(item.item for item in ordering.items) == clause.items
    assert tuple(item.source_ordinal for item in ordering.items) == (0, 1, 2)
    assert tuple(item.direction for item in ordering.items) == (
        final_outputs.ProjectRelationOrderDirection.DESC,
        final_outputs.ProjectRelationOrderDirection.ASC,
        final_outputs.ProjectRelationOrderDirection.ASC,
    )
    assert tuple(type(item.source) for item in ordering.items) == (
        ProjectConcreteJoinedNamespaceExpression,
        ProjectConcreteJoinedNamespaceExpression,
        ProjectSelectedWindowResultBinding,
    )
    assert tuple(item.expression for item in ordering.items) == (
        clause.items[0].expression,
        clause.items[1].expression,
        clause.items[2].expression,
    )


def test_order_input_wins_over_window_alias_and_other_aliases_do_not_leak(
    built: _Built,
) -> None:
    precedence = _completed(built, "final_order_input_precedence")
    assert precedence.ordering is not None
    assert type(precedence.ordering.items[0].source) is (
        ProjectConcreteJoinedNamespaceExpression
    )
    ambiguous = _terminal(built, "final_order_ambiguous_input")
    projection_alias = _terminal(built, "final_order_projection_alias")
    assert ambiguous.reason is (
        final_outputs.ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE
    )
    assert projection_alias.reason is ambiguous.reason
    blocker = cast(final_outputs.ProjectNonConcreteRelationOrdering, ambiguous.blocker)
    analysis = cast(
        final_outputs.ProjectNonConcreteJoinedNamespaceExpression,
        blocker.blocker,
    )
    resolution = cast(ProjectScalarReferenceResolution, analysis.resolutions[0])
    assert resolution.status is ProjectModuleCandidateBucketStatus.AMBIGUOUS


def test_grouped_order_uses_only_group_aggregate_let_and_window_outputs(
    built: _Built,
) -> None:
    result = _completed(built, "final_grouped_order")
    ordering = result.ordering
    assert ordering is not None
    assert tuple(type(item.source) for item in ordering.items) == (
        windows.ProjectJoinedWindowInputBinding,
        windows.ProjectJoinedWindowInputBinding,
        windows.ProjectJoinedWindowInputBinding,
        ProjectSelectedWindowResultBinding,
    )
    for name in ("final_grouped_order_raw", "final_grouped_order_scalar"):
        terminal = _terminal(built, name)
        assert terminal.reason is (
            final_outputs.ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE
        )
        assert tuple(item.code for item in terminal.diagnostics) == ("PIE-S2321",)
    global_order = _terminal(built, "final_global_order")
    assert global_order.reason is (
        final_outputs.ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE
    )


def test_window_local_order_never_establishes_relation_order(built: _Built) -> None:
    result = _completed(built, "final_window_order_only")
    assert result.ordering is None
    source = cast(ProjectSelectedWindowResultBinding, result.fields[0].source)
    assert source.computation.analysis.expression.spec.order_by


@pytest.mark.parametrize(
    "name, value",
    [
        ("final_limit_zero", 0),
        ("final_limit_one", 1),
        ("final_limit_max", 9_223_372_036_854_775_807),
    ],
)
def test_valid_limit_is_only_an_exact_row_count_upper_bound(
    built: _Built,
    name: str,
    value: int,
) -> None:
    result = _completed(built, name)
    assert result.limit is not None
    assert result.limit.clause.expression is result.limit.literal
    assert result.limit.value == value
    assert result.limit.row_count_upper_bound == value
    assert not hasattr(result.limit, "key")
    assert not hasattr(result.limit, "fd")
    assert not hasattr(result.limit, "unique")
    assert not hasattr(result.limit, "relationship")
    assert not hasattr(result.limit, "grain")


@pytest.mark.parametrize(
    "name",
    [
        "final_limit_large",
        "final_limit_negative",
        "final_limit_float",
        "final_limit_string",
        "final_limit_name",
        "final_limit_call",
    ],
)
def test_invalid_limit_is_atomic_and_retains_only_pie_s2307(
    built: _Built,
    name: str,
) -> None:
    result = _terminal(built, name)
    assert result.reason is (
        final_outputs.ProjectEffectiveOutputCompletionTerminalReason.LIMIT_NON_CONCRETE
    )
    assert tuple(item.code for item in result.diagnostics) == ("PIE-S2307",)
    assert result.output is None


def test_replayed_no_join_selected_hidden_input_ambiguity_and_window_requirement(
    built: _Built,
) -> None:
    selected = _completed(built, "replay_selected")
    selected_root = cast(final_outputs.ProjectConcreteNoJoinReplay, selected.root)
    assert selected_root.qualify.predicate is not None
    assert selected_root.qualify.predicate.reason is None
    assert len(selected_root.qualify.references) == 2
    assert not selected_root.qualify.hidden_attempts
    hidden = _completed(built, "replay_hidden")
    hidden_root = cast(final_outputs.ProjectConcreteNoJoinReplay, hidden.root)
    assert len(hidden_root.qualify.hidden_attempts) == 1
    assert hidden_root.qualify.hidden_attempts[0].analysis is not None
    assert tuple(item.output_name for item in hidden.fields) == ("id",)
    ambiguous = _terminal(built, "replay_ambiguous")
    assert tuple(item.code for item in ambiguous.diagnostics) == ("PIE-S2332",)
    no_window = _terminal(built, "replay_no_window")
    assert tuple(item.code for item in no_window.diagnostics) == ("PIE-S2331",)
    global_hidden = _terminal(built, "replay_global_hidden")
    assert global_hidden.reason is (
        final_outputs.ProjectEffectiveOutputCompletionTerminalReason.QUALIFY_NON_CONCRETE
    )
    global_qualify = cast(final_outputs.ProjectNoJoinQualify, global_hidden.blocker)
    assert len(global_qualify.hidden_attempts) == 1
    assert type(global_qualify.hidden_attempts[0].analysis) is (
        final_outputs.WindowComputationUnsupported
    )


def test_replayed_no_join_order_limit_and_grouped_domain_are_exact(
    built: _Built,
) -> None:
    ordinary = _completed(built, "replay_order")
    root = cast(final_outputs.ProjectConcreteNoJoinReplay, ordinary.root)
    assert ordinary.row_domain.preserved is final_outputs._entry_row_domain(
        root.upstream_entry
    )
    assert ordinary.ordering is not None
    assert tuple(type(item.source) for item in ordinary.ordering.items) == (
        final_outputs.ProjectNoJoinScalarExpression,
        final_outputs.ProjectNoJoinScalarExpression,
        final_outputs.ProjectModuleWindowOutputFact,
    )
    assert ordinary.limit is not None and ordinary.limit.value == 1
    grouped = _completed(built, "replay_grouped")
    grouped_root = cast(final_outputs.ProjectConcreteNoJoinReplay, grouped.root)
    assert grouped_root.mode is ProjectJoinedAggregationMode.GROUPED
    assert (
        grouped.row_domain.kind is final_outputs.ProjectCompletedRowDomainKind.GROUPED
    )
    assert grouped.row_domain.preserved is None
    basis = cast(
        tuple[final_outputs.ProjectRelationClauseDependencyFact, ...],
        grouped.row_domain.grouped_basis,
    )
    assert all(
        item.kind is final_outputs.ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT
        for item in basis
    )


def test_module_propagation_uses_exact_existing_schedule_and_dependency_evidence(
    propagated: _Built,
) -> None:
    joined = _completed(propagated, "joined_a")
    downstream_b = _completed(propagated, "downstream_b")
    downstream_c = _completed(propagated, "downstream_c")
    positions = {
        id(owner): position
        for position, owner in enumerate(propagated.outputs.schedule)
    }
    assert positions[id(joined.owner)] < positions[id(downstream_b.owner)]
    assert positions[id(downstream_b.owner)] < positions[id(downstream_c.owner)]
    assert downstream_b.dependencies is downstream_b.base_entry.dependencies
    assert downstream_c.dependencies is downstream_c.base_entry.dependencies
    root_b = cast(final_outputs.ProjectConcreteNoJoinReplay, downstream_b.root)
    root_c = cast(final_outputs.ProjectConcreteNoJoinReplay, downstream_c.root)
    assert root_b.upstream_entry is joined
    assert root_c.upstream_entry is downstream_b
    assert downstream_b.row_domain.preserved is joined.row_domain
    assert downstream_c.row_domain.preserved is downstream_b.row_domain


def test_upstream_failure_propagates_typed_terminals_without_fake_outputs(
    tmp_path: Path,
) -> None:
    built = _build(tmp_path / "failed", slice7._project_files())
    joined = _entry(built, "joined_a")
    downstream_b = _entry(built, "downstream_b")
    downstream_c = _entry(built, "downstream_c")
    assert type(joined) is final_outputs.ProjectEffectiveOutputCompletionTerminal
    assert type(downstream_b) is final_outputs.ProjectEffectiveOutputCompletionTerminal
    assert type(downstream_c) is final_outputs.ProjectEffectiveOutputCompletionTerminal
    assert downstream_b.upstream_entry is joined
    assert downstream_c.upstream_entry is downstream_b
    assert downstream_b.output is downstream_c.output is None


def test_nonrecoverable_effective_join_terminal_is_retained_by_identity(
    propagated: _Built,
) -> None:
    base = _base_entry(propagated, "unsupported_join")
    assert type(base) is completion.ProjectEffectiveOutputTerminal
    assert base.reason is (
        ProjectEffectiveOutputTerminalReason.EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED
    )
    assert _entry(propagated, "unsupported_join") is base


def test_completion_allocates_no_project_ir_or_historical_attribution() -> None:
    source = PRODUCTION.read_text(encoding="utf-8")
    names = {node.id for node in ast.walk(ast.parse(source)) if type(node) is ast.Name}
    assert "ProjectModuleRelationOutputFieldAttribution" not in names
    assert "ProjectGroupedGrainFactorIdentity" not in names
    assert "ProjectIROutputRelationalProperties" not in names
    assert "ProjectIRLogicalOperatorKind" not in names
    assert "build_project_ir_single_relation_fragment" not in names
    assert "build_project_completion" not in names
    assert "class ProjectModuleRowFieldIdentity" not in source
    assert "class ProjectNoJoinScalarReference" not in source
    assert "class ProjectSemanticResult" not in source


def test_completion_carriers_reject_cross_owner_and_seed_grafts(built: _Built) -> None:
    joined = _completed(built, "final_projection")
    with pytest.raises(ValueError, match="source must retain exact owner"):
        replace(joined.fields[0], source=joined.fields[1].source)
    other = _completed(built, "final_order_absent")
    with pytest.raises(ValueError, match="exact owner/base entry"):
        replace(joined, root=other.root)
    with pytest.raises(ValueError, match="row domain"):
        replace(
            joined,
            row_domain=final_outputs.ProjectCompletedRowDomain(
                kind=final_outputs.ProjectCompletedRowDomainKind.GLOBAL
            ),
        )

    replayed = _completed(built, "replay_selected")
    replay_root = cast(final_outputs.ProjectConcreteNoJoinReplay, replayed.root)
    replay_qualify = replay_root.qualify
    predicate = replay_qualify.predicate
    assert predicate is not None and len(replay_qualify.references) == 2
    value_types = dict(predicate.value_types)
    first, second = replay_qualify.references
    assert second.target is not None
    value_types[first.expression] = final_outputs._no_join_qualify_candidate_value_type(
        second.target
    )
    grafted_predicate = replace(predicate, value_types=value_types)
    with pytest.raises(ValueError, match="exact type seeds"):
        replace(replay_qualify, predicate=grafted_predicate)

    replay_order = _completed(built, "replay_order")
    order_root = cast(final_outputs.ProjectConcreteNoJoinReplay, replay_order.root)
    with pytest.raises(ValueError, match="exact Bool authority"):
        replace(
            order_root.where,
            retention_effects=tuple(list(order_root.where.retention_effects)),
        )


def test_completion_rejects_same_base_foreign_joined_authority_grafts(
    built: _Built,
) -> None:
    foreign = _rebuild_from_same_completion(built)
    assert foreign.completion is built.completion
    assert foreign.qualifies is not built.qualifies
    assert foreign.qualifies.window_set is not built.qualifies.window_set
    assert len(foreign.qualifies.results) == len(built.qualifies.results)
    assert all(
        final_outputs._joined_result_owner(local)
        is final_outputs._joined_result_owner(alternate)
        and local is not alternate
        for local, alternate in zip(
            built.qualifies.results,
            foreign.qualifies.results,
            strict=True,
        )
    )

    exact = replace(built.outputs)
    assert exact.joined_qualifies is built.qualifies
    assert exact.entries is built.outputs.entries
    with pytest.raises(ValueError, match="exact Slice-11"):
        replace(built.outputs, joined_qualifies=foreign.qualifies)

    local_completed = _completed(built, "final_projection")
    foreign_completed = _completed(foreign, "final_projection")
    grafted_completed = replace(
        local_completed,
        root=foreign_completed.root,
        fields=foreign_completed.fields,
        schema=foreign_completed.schema,
        row_domain=foreign_completed.row_domain,
    )
    with pytest.raises(ValueError, match="exact Slice-11"):
        replace(
            built.outputs,
            entries=tuple(
                grafted_completed if entry is local_completed else entry
                for entry in built.outputs.entries
            ),
        )

    grafted_field = replace(
        local_completed.fields[-1],
        source=foreign_completed.fields[-1].source,
    )
    with pytest.raises(ValueError, match="field source"):
        replace(
            local_completed,
            fields=(*local_completed.fields[:-1], grafted_field),
        )
    local_grouped = _completed(built, "window_grouped_ok")
    foreign_grouped = _completed(foreign, "window_grouped_ok")
    for ordinal in (0, 1):
        grafted_grouped_field = replace(
            local_grouped.fields[ordinal],
            source=foreign_grouped.fields[ordinal].source,
        )
        with pytest.raises(ValueError, match="field source"):
            replace(
                local_grouped,
                fields=(
                    *local_grouped.fields[:ordinal],
                    grafted_grouped_field,
                    *local_grouped.fields[ordinal + 1 :],
                ),
            )

    local_ordered = _completed(built, "final_order_absent")
    foreign_ordered = _completed(foreign, "final_order_absent")
    assert local_ordered.ordering is not None
    assert foreign_ordered.ordering is not None
    grafted_order_item = replace(
        local_ordered.ordering.items[-1],
        source=foreign_ordered.ordering.items[-1].source,
        value_type=foreign_ordered.ordering.items[-1].value_type,
    )
    grafted_ordering = replace(
        local_ordered.ordering,
        items=(*local_ordered.ordering.items[:-1], grafted_order_item),
    )
    with pytest.raises(ValueError, match="ORDER source"):
        replace(local_ordered, ordering=grafted_ordering)

    local_terminal = _terminal(built, "qualify_unknown")
    foreign_terminal = _terminal(foreign, "qualify_unknown")
    assert local_terminal.joined_qualify is local_terminal.blocker
    with pytest.raises(ValueError, match="Slice-11 blocker"):
        replace(local_terminal, blocker=foreign_terminal.blocker)


def test_completion_rejects_foreign_downstream_replay_overlay_entry(
    propagated: _Built,
) -> None:
    foreign = _rebuild_from_same_completion(propagated)
    local_joined = _completed(propagated, "joined_a")
    foreign_joined = _completed(foreign, "joined_a")
    local_downstream = _completed(propagated, "downstream_b")
    foreign_downstream = _completed(foreign, "downstream_b")
    local_root = cast(
        final_outputs.ProjectConcreteNoJoinReplay,
        local_downstream.root,
    )
    foreign_root = cast(
        final_outputs.ProjectConcreteNoJoinReplay,
        foreign_downstream.root,
    )
    assert foreign_joined is not local_joined
    assert foreign_root.upstream_entry is foreign_joined
    grafted_field = replace(
        local_downstream.fields[0],
        source=foreign_downstream.fields[0].source,
    )
    with pytest.raises(ValueError, match="field source"):
        replace(local_downstream, fields=(grafted_field,))
    with pytest.raises(ValueError, match="exact upstream overlay entry"):
        replace(
            propagated.outputs,
            replay_roots=tuple(
                foreign_root.replay_root if root is local_root.replay_root else root
                for root in propagated.outputs.replay_roots
            ),
            entries=tuple(
                foreign_downstream if entry.owner is foreign_downstream.owner else entry
                for entry in propagated.outputs.entries
            ),
        )


def test_no_join_replay_roots_reject_all_foreign_success_and_terminal_grafts(
    built: _Built,
) -> None:
    foreign = _rebuild_from_same_completion(built)
    local_terminal = _terminal(built, "replay_ambiguous")
    foreign_terminal = _terminal(foreign, "replay_ambiguous")
    with pytest.raises(ValueError, match="local replay blocker"):
        replace(local_terminal, blocker=foreign_terminal.blocker)

    def replay_root(
        entry: final_outputs.ProjectEffectiveOutputCompletionEntry,
    ) -> final_outputs.ProjectNoJoinReplayRoot | None:
        if (
            type(entry) is final_outputs.ProjectCompletedEffectiveOutput
            and type(entry.root) is final_outputs.ProjectConcreteNoJoinReplay
        ):
            return entry.root.replay_root
        if type(entry) is final_outputs.ProjectEffectiveOutputCompletionTerminal:
            return entry.replay_root
        return None

    expected = tuple(
        root
        for owner in built.outputs.schedule
        for entry in built.outputs.find_owner(owner)
        if (root := replay_root(entry)) is not None
    )
    assert len(expected) == len(built.outputs.replay_roots)
    assert all(
        actual is retained
        for actual, retained in zip(
            built.outputs.replay_roots,
            expected,
            strict=True,
        )
    )
    assert len({id(root) for root in expected}) == len(expected)
    assert all(root.upstream_entry is not None for root in expected)

    for local_entry in built.outputs.entries:
        local_root = replay_root(local_entry)
        if local_root is None:
            continue
        foreign_entry = foreign.outputs.find_owner(local_entry.owner)[0]
        foreign_root = replay_root(foreign_entry)
        assert foreign_root is not None and foreign_root is not local_root
        with pytest.raises(ValueError, match="owner-local replay root"):
            replace(
                built.outputs,
                entries=tuple(
                    foreign_entry if entry is local_entry else entry
                    for entry in built.outputs.entries
                ),
            )

    with pytest.raises(TypeError, match="entry tuple"):
        replace(built.outputs, entries=list(built.outputs.entries))  # type: ignore[arg-type]


def test_joined_and_no_join_qualify_delegate_to_one_shared_predicate_kernel() -> None:
    joined_source = QUALIFY_PRODUCTION.read_text(encoding="utf-8")
    final_source = PRODUCTION.read_text(encoding="utf-8")
    assert joined_source.count("def _analyze_qualify_predicate(") == 1
    assert joined_source.count("_analyze_qualify_predicate(") == 2
    assert final_source.count("_analyze_qualify_predicate(") == 1
    assert (
        "infer_row_expression("
        not in final_source.split("def _no_join_qualify(", 1)[1].split(
            "def _no_join_final_fields(", 1
        )[0]
    )


def test_spec_records_exact_contract_and_inventory_transition() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for phrase in (
        "ProjectEffectiveOutputCompletion",
        "ProjectNoJoinReplayRoot",
        "ProjectModuleRowFieldIdentity",
        "ProjectModuleSelectFact",
        "PIE-S2304",
        "PIE-S2305",
        "PIE-S2307",
        "PIE-S2321",
        "PIE-S2331",
        "PIE-S2332",
        "173 -> 174",
        "416 -> 417",
        "A3/M5/D0",
        "same Slice-7 base",
        "object identity",
        "replay-root tuple",
        "Slice 13",
    ):
        assert phrase in text
