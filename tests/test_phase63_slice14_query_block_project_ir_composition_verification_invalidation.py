from __future__ import annotations

import ast
from copy import copy
from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

import pytest

import test_phase63_slice13_completed_project_semantic_result_public_check_boundaries as slice13
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectGroupedGrainFactorIdentity,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.project_ir_verification import (
    ProjectIRChangeDomain,
    ProjectIRVerificationRequirement,
)
from pietto._project.project_joined_qualify import ProjectConcreteJoinedQualify
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockOperatorExtensionKind,
    ProjectIRQueryBlockRowOutput,
    ProjectIRQueryBlockSnapshot,
    ProjectIRQueryBlockTerminal,
    ProjectIRQueryBlockTerminalReason,
    ProjectIRQueryBlockWindowEvidence,
    ProjectIRReboundExistingOutput,
    ProjectIRReusedEffectiveOutput,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisKind,
    ProjectIRQueryBlockOverlayRequirement,
    ProjectIRQueryBlockVerificationIssueKind,
    ProjectIRQueryBlockVerificationStatus,
    assess_project_query_block_ir_invalidation,
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice14-query-block-project-ir-composition-verification-invalidation-v1.md"
)
PRODUCTION = REPO_ROOT / "src/pietto/_project/project_query_block_ir.py"
VERIFICATION = REPO_ROOT / "src/pietto/_project/project_query_block_ir_verification.py"
HISTORICAL_OPERATORS = REPO_ROOT / "src/pietto/_project/project_ir_operators.py"

SLICE14_SOURCE = (
    slice13.POSITIVE_SOURCE
    + """
query filtered:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where event.id > 0
    select:
        event_id = event.id
query satisfying:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.metric)
    satisfying:
        event_id > 0 and total > 0
query hidden_qualify:
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
query ordered_limited:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
    order by:
        event.id desc
    limit 1
query computed:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        doubled = event.metric * 2
query key_drop:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    select:
        metric = event.metric
query mixed:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    where event.id > 0
    group by:
        event.id
    select:
        event_id = event.id
        total = sum(event.metric)
        ranked = rank() window:
            order by:
                total
    satisfying:
        event_id > 0 and total > 0
    qualify:
        ranked <= 3
    order by:
        event_id desc
        ranked
    limit 5
query replay_selected:
    from accounts
    select:
        id
        ranked = row_number() window:
            order by:
                id
    qualify:
        ranked <= 3
query replay_full:
    from accounts
    where id > 0
    select:
        id
        ranked = row_number() window:
            order by:
                id
    qualify:
        ranked <= 3
    order by:
        id desc
        ranked
    limit 2
query rebound_one:
    from replay_selected
    select:
        id
query rebound_two:
    from rebound_one
    select:
        id
query qualified_events:
    from events
    select:
        id
        account_id
        metric
    qualify:
        row_number() window:
            order by:
                id
        <= 3
relationship account_qualified_events:
    endpoint account: accounts
    endpoint event: qualified_events
    on account.id == event.account_id
query stale_join:
    from accounts
    inner join qualified_events as event:
        from accounts
        via account_qualified_events: account -> event
    select:
        event_id = event.id
query downstream_stale:
    from stale_join
    select:
        event_id
shape DetailRow:
    id: Int not null
    event_id: Int not null
    unique detail_key on id
source details: DetailRow is postgres.table("details")
relationship event_details:
    endpoint event: events
    endpoint detail: details
    on event.id == detail.event_id
query multi_join:
    from accounts
    inner join events as event:
        from accounts
        via account_events: account -> event
    left join details as detail:
        from event
        via event_details: event -> detail
    select:
        account_id = accounts.id
        event_id = event.id
        detail_id = detail.id
query left_selected_hidden:
    from accounts
    left join events as event:
        from accounts
        via account_events: account -> event
    select:
        event_id = event.id
        ranked = row_number() window:
            order by:
                event.id
    qualify:
        ranked <= 3 and row_number() window:
            order by:
                event.id
        <= 3
query semantic_bad:
    from missing
    select:
        id
query semantic_bad_downstream:
    from semantic_bad
    select:
        id
"""
)


@dataclass(frozen=True, slots=True)
class _Built:
    completed: slice13.completed_semantics.ProjectConcreteCompletedSemanticResult
    snapshot: ProjectIRQueryBlockSnapshot


def _build(root: Path) -> _Built:
    completed = slice13._build(root, SLICE14_SOURCE).completed
    return _Built(
        completed=completed,
        snapshot=build_project_query_block_ir(completed),
    )


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(tmp_path_factory.mktemp("p63s14"))


@pytest.fixture(scope="module")
def foreign(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(tmp_path_factory.mktemp("p63s14-foreign"))


def _entry(built: _Built, name: str):
    matches = tuple(
        entry
        for entry in built.snapshot.entries
        if entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _completed(built: _Built, name: str) -> ProjectIRCompletedQueryBlockOutput:
    entry = _entry(built, name)
    assert type(entry) is ProjectIRCompletedQueryBlockOutput
    return entry


def _kinds(entry: ProjectIRCompletedQueryBlockOutput) -> tuple[str, ...]:
    return tuple(operator.kind.value for operator in entry.operators)


def _class_positions(entry: ProjectIRCompletedQueryBlockOutput, stage: int = -1):
    properties = entry.row_properties[stage].relational
    return tuple(
        tuple(member.field_position for member in value_class.members)
        for value_class in properties.value_classes
    )


def test_snapshot_reuses_exact_roots_scope_allocation_ledger_and_verifies(
    built: _Built,
) -> None:
    snapshot = built.snapshot
    phase62 = built.completed.verification.root
    overlay = built.completed.effective_outputs
    assert snapshot.completed is built.completed
    assert snapshot.base_plan is phase62.evaluation.project_plan
    assert snapshot.join_stage is phase62.join_regions
    assert snapshot.starting_allocation is phase62.join_regions.ending_allocation
    assert snapshot.owners is overlay.owners
    assert snapshot.dependencies is overlay.dependencies
    assert snapshot.schedule is overlay.schedule
    assert tuple(entry.semantic_entry for entry in snapshot.entries) == overlay.entries
    assert tuple(entry.owner for entry in snapshot.entries) == overlay.owners
    assert len(snapshot.entries) == len(overlay.owners)

    for values, start, end in (
        (
            snapshot.structural.nodes,
            snapshot.starting_allocation.next_plan_node_position,
            snapshot.ending_allocation.next_plan_node_position,
        ),
        (
            snapshot.structural.outputs,
            snapshot.starting_allocation.next_output_value_position,
            snapshot.ending_allocation.next_output_value_position,
        ),
        (
            snapshot.structural.input_slots,
            snapshot.starting_allocation.next_input_slot_position,
            snapshot.ending_allocation.next_input_slot_position,
        ),
        (
            snapshot.structural.uses,
            snapshot.starting_allocation.next_use_position,
            snapshot.ending_allocation.next_use_position,
        ),
    ):
        assert tuple(item.ref.position for item in values) == tuple(range(start, end))
        assert all(
            item.ref.scope is snapshot.starting_allocation.scope for item in values
        )

    verification = verify_project_query_block_ir(snapshot)
    assert verification.status is ProjectIRQueryBlockVerificationStatus.VERIFIED
    assert verification.issues == ()
    analyses = build_project_query_block_ir_analysis_bundle(verification)
    combined_nodes = (
        *snapshot.base_plan.structural_stage.nodes,
        *snapshot.join_stage.structural.nodes,
        *snapshot.structural.nodes,
    )
    combined_outputs = (
        *snapshot.base_plan.structural_stage.outputs,
        *snapshot.join_stage.structural.outputs,
        *snapshot.structural.outputs,
    )
    assert len(analyses.combined_reverse_uses) == len(combined_outputs)
    assert len(analyses.combined_topological_order) == len(combined_nodes)
    assert len(analyses.combined_reachability) == len(combined_nodes)
    assert {id(node) for node in analyses.combined_topological_order} == {
        id(node) for node in combined_nodes
    }


def test_exact_authored_operator_sequences_cover_joined_replay_and_full_mixed_tail(
    built: _Built,
) -> None:
    assert _kinds(_completed(built, "joined")) == ("final_projection",)
    assert _kinds(_completed(built, "filtered")) == (
        "row_filter",
        "final_projection",
    )
    assert _kinds(_completed(built, "grouped")) == (
        "group_aggregate",
        "final_projection",
    )
    assert _kinds(_completed(built, "global")) == (
        "group_aggregate",
        "final_projection",
    )
    assert _kinds(_completed(built, "satisfying")) == (
        "group_aggregate",
        "result_filter",
        "final_projection",
    )
    assert _kinds(_completed(built, "hidden_qualify")) == (
        "window_evaluation",
        "qualify",
        "final_projection",
    )
    assert _kinds(_completed(built, "ordered_limited")) == (
        "final_projection",
        "relation_ordering",
        "limit",
    )
    assert _kinds(_completed(built, "mixed")) == (
        "row_filter",
        "group_aggregate",
        "result_filter",
        "window_evaluation",
        "qualify",
        "final_projection",
        "relation_ordering",
        "limit",
    )
    assert _kinds(_completed(built, "replay_full")) == (
        "relation_input",
        "row_filter",
        "window_evaluation",
        "qualify",
        "final_projection",
        "relation_ordering",
        "limit",
    )
    assert tuple(ProjectIRLogicalOperatorKind) == (
        ProjectIRLogicalOperatorKind.RELATION_INPUT,
        ProjectIRLogicalOperatorKind.ROW_FILTER,
        ProjectIRLogicalOperatorKind.GROUP_AGGREGATE,
        ProjectIRLogicalOperatorKind.RESULT_FILTER,
        ProjectIRLogicalOperatorKind.WINDOW_EVALUATION,
        ProjectIRLogicalOperatorKind.FINAL_PROJECTION,
        ProjectIRLogicalOperatorKind.RELATION_ORDERING,
        ProjectIRLogicalOperatorKind.LIMIT,
    )
    assert tuple(ProjectIRQueryBlockOperatorExtensionKind) == (
        ProjectIRQueryBlockOperatorExtensionKind.QUALIFY,
    )


def test_row_shapes_final_identity_window_scalar_and_hidden_non_output_are_exact(
    built: _Built,
) -> None:
    for name in (
        "joined",
        "grouped",
        "global",
        "qualified",
        "mixed",
        "replay_full",
        "downstream",
        "multi_join",
        "left_selected_hidden",
    ):
        entry = _completed(built, name)
        final = entry.row_outputs[_kinds(entry).index("final_projection")]
        assert type(final) is ProjectIRQueryBlockRowOutput
        assert len(final.row_shape.fields) == len(entry.semantic_entry.fields)
        assert all(
            field.evidence is completed.field
            and field.semantic_source is completed
            and field.final_identity is completed.identity
            for field, completed in zip(
                final.row_shape.fields,
                entry.semantic_entry.fields,
                strict=True,
            )
        )
        final_scalars = tuple(
            scalar
            for scalar in entry.scalar_outputs
            if scalar.final_identity is not None
        )
        assert tuple(scalar.final_identity for scalar in final_scalars) == tuple(
            completed.identity for completed in entry.semantic_entry.fields
        )

    hidden = _completed(built, "hidden_qualify")
    window = next(
        operator
        for operator in hidden.operators
        if operator.kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION
    )
    assert type(window.evidence) is ProjectIRQueryBlockWindowEvidence
    assert not tuple(
        scalar
        for scalar in hidden.scalar_outputs
        if scalar.occurrence.producer is window.node
    )
    assert len(window.evidence.hidden) == 1
    assert not window.evidence.selected

    selected = _completed(built, "qualified")
    selected_window = next(
        operator
        for operator in selected.operators
        if operator.kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION
    )
    assert type(selected_window.evidence) is ProjectIRQueryBlockWindowEvidence
    selected_scalars = tuple(
        scalar
        for scalar in selected.scalar_outputs
        if scalar.occurrence.producer is selected_window.node
    )
    assert len(selected_scalars) == len(selected_window.evidence.selected) == 1
    assert selected.window_policies[0].output is selected_scalars[0]

    selected_hidden = _completed(built, "left_selected_hidden")
    selected_hidden_window = next(
        operator
        for operator in selected_hidden.operators
        if operator.kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION
    )
    assert type(selected_hidden_window.evidence) is ProjectIRQueryBlockWindowEvidence
    assert len(selected_hidden_window.evidence.selected) == 1
    assert len(selected_hidden_window.evidence.hidden) == 1
    assert (
        len(
            tuple(
                scalar
                for scalar in selected_hidden.scalar_outputs
                if scalar.occurrence.producer is selected_hidden_window.node
            )
        )
        == 1
    )
    assert any(
        field.effective_nullability.value == "nullable" and field.nulling_joins
        for field in selected_hidden.row_outputs[0].row_shape.fields
    )

    multi = _completed(built, "multi_join")
    multi_root = multi.semantic_entry.root
    assert type(multi_root) is ProjectConcreteJoinedQualify
    region = multi_root.window_stage.input_aggregation.input_filter.joined_semantics.row_source.region
    assert len(region.joins) == 2
    assert region.joins[1].input_uses[0].output is region.joins[0].output.occurrence


def test_property_transfer_group_global_projection_order_and_limit_are_narrow(
    built: _Built,
) -> None:
    grouped = _completed(built, "grouped")
    grouped_properties = grouped.row_properties[0].relational
    assert grouped_properties.grain.state is ProjectGrainBasisState.FACTORIZED
    assert len(grouped_properties.grain.active) == 1
    factor = grouped_properties.grain.active[0]
    assert type(factor) is ProjectGroupedGrainFactorIdentity
    assert factor.operator == grouped.operators[0].node.ref
    assert factor.owner == grouped.operators[0].node.anchor.identity
    assert len(grouped_properties.keys) == 1
    assert grouped_properties.keys[0].strength is ProjectRowUniquenessStrength.STRICT
    assert not any(
        dependency.determinants == (factor,)
        and dependency.dependents == grouped.source_properties.grain.active
        for dependency in grouped_properties.grain.dependencies
    )

    satisfying = _completed(built, "satisfying")
    satisfying_properties = satisfying.row_properties[0].relational
    satisfying_factor = satisfying_properties.grain.active[0]
    assert any(
        dependency.determinants == (satisfying_factor,)
        and dependency.dependents == satisfying.source_properties.grain.active
        for dependency in satisfying_properties.grain.dependencies
    )

    global_entry = _completed(built, "global")
    global_properties = global_entry.row_properties[0].relational
    assert global_properties.grain.state is ProjectGrainBasisState.GLOBAL
    assert global_properties.grain.active == ()
    assert global_properties.keys == ()
    assert global_properties.fds == ()

    computed = _completed(built, "computed")
    assert _class_positions(computed) == ((0,), (1,))
    key_drop = _completed(built, "key_drop")
    assert key_drop.result_properties.relational.keys == ()

    qualified = _completed(built, "qualified")
    window_position = _kinds(qualified).index("window_evaluation")
    before_count = len(qualified.source_properties.value_classes)
    window_classes = _class_positions(qualified, window_position)
    assert len(window_classes) == before_count + 1
    assert window_classes[-1] == (
        len(qualified.row_outputs[window_position].row_shape.fields) - 1,
    )

    ordered = _completed(built, "ordered_limited")
    assert ordered.row_properties[-2].ordering is ordered.semantic_entry.ordering
    assert ordered.row_properties[-2].cardinality is None
    assert ordered.result_properties.ordering is ordered.semantic_entry.ordering
    assert ordered.result_properties.cardinality is ordered.semantic_entry.limit
    assert ordered.result_properties.row_count_upper_bound == 1
    assert tuple(
        (key.strength, tuple(len(item.members) for item in key.determinants))
        for key in ordered.row_properties[-2].relational.keys
    ) == tuple(
        (key.strength, tuple(len(item.members) for item in key.determinants))
        for key in ordered.result_properties.relational.keys
    )


def test_reuse_rebind_and_no_join_chains_consume_exact_active_outputs(
    built: _Built,
) -> None:
    accounts = _entry(built, "accounts")
    plain = _entry(built, "plain")
    assert type(accounts) is ProjectIRReusedEffectiveOutput
    assert type(plain) is ProjectIRReusedEffectiveOutput
    assert accounts.output is accounts.semantic_entry.output
    assert plain.output is plain.semantic_entry.output
    assert accounts.starting_allocation is accounts.ending_allocation
    assert plain.starting_allocation is plain.ending_allocation

    replay = _completed(built, "replay_selected")
    rebound_one = _entry(built, "rebound_one")
    rebound_two = _entry(built, "rebound_two")
    assert type(rebound_one) is ProjectIRReboundExistingOutput
    assert type(rebound_two) is ProjectIRReboundExistingOutput
    assert rebound_one.rebuilt_fragment is not rebound_one.semantic_entry.fragment
    assert rebound_one.rebuilt_fragment.semantic_facts is (
        rebound_one.semantic_entry.fragment.semantic_facts
    )
    assert rebound_one.relation_input.use.output is replay.output.occurrence
    assert rebound_one.relation_input.producer is replay.result_properties
    assert rebound_two.relation_input.use.output is rebound_one.output.occurrence
    assert rebound_two.relation_input.producer is rebound_one.result_properties
    assert rebound_one.relation_input.compatibility.satisfied
    assert rebound_two.relation_input.compatibility.satisfied

    downstream = _completed(built, "downstream")
    joined = _completed(built, "joined")
    assert downstream.relation_input is not None
    assert downstream.relation_input.use.output is joined.output.occurrence
    assert downstream.operators[0].kind is ProjectIRLogicalOperatorKind.RELATION_INPUT


def test_concrete_ledger_entries_retain_explicit_active_row_and_property_roots(
    built: _Built,
    foreign: _Built,
) -> None:
    concrete = tuple(
        cast(
            ProjectIRReusedEffectiveOutput
            | ProjectIRReboundExistingOutput
            | ProjectIRCompletedQueryBlockOutput,
            entry,
        )
        for entry in built.snapshot.entries
        if type(entry)
        in {
            ProjectIRReusedEffectiveOutput,
            ProjectIRReboundExistingOutput,
            ProjectIRCompletedQueryBlockOutput,
        }
    )
    assert concrete
    for entry in concrete:
        assert entry.output is entry.active_output
        assert entry.result_properties is entry.active_properties
        assert entry.active_properties.output is entry.active_output
        if type(entry) is ProjectIRCompletedQueryBlockOutput:
            assert (
                sum(output is entry.active_output for output in entry.row_outputs) == 1
            )
            assert (
                sum(
                    properties is entry.active_properties
                    for properties in entry.row_properties
                )
                == 1
            )
            assert entry.active_output.occurrence.producer is next(
                operator.node
                for operator in entry.operators
                if operator.kind
                is (
                    ProjectIRLogicalOperatorKind.LIMIT
                    if entry.semantic_entry.limit is not None
                    else (
                        ProjectIRLogicalOperatorKind.RELATION_ORDERING
                        if entry.semantic_entry.ordering is not None
                        else ProjectIRLogicalOperatorKind.FINAL_PROJECTION
                    )
                )
            )
            reordered_entry = copy(entry)
            object.__setattr__(
                reordered_entry,
                "row_outputs",
                tuple(reversed(entry.row_outputs)),
            )
            assert reordered_entry.active_output is entry.active_output
            assert (
                sum(
                    output is reordered_entry.active_output
                    for output in reordered_entry.row_outputs
                )
                == 1
            )
        elif type(entry) is ProjectIRReboundExistingOutput:
            assert entry.active_output is entry.rebuilt_fragment.root_relation_output
            assert (
                sum(
                    properties is entry.active_properties
                    for properties in entry.row_properties
                )
                == 1
            )
        else:
            assert type(entry) is ProjectIRReusedEffectiveOutput
            assert entry.active_output is entry.semantic_entry.output
            assert entry.active_properties.relational is entry.semantic_entry.properties

    local = _completed(built, "mixed")
    foreign_entry = _completed(foreign, "mixed")
    with pytest.raises(ValueError, match="explicit active row root"):
        replace(local, active_output=foreign_entry.active_output)
    with pytest.raises(ValueError, match="explicit active property root"):
        replace(local, active_properties=foreign_entry.active_properties)

    for attribute, foreign_root in (
        ("active_output", foreign_entry.active_output),
        ("active_properties", foreign_entry.active_properties),
    ):
        grafted_entry = copy(local)
        object.__setattr__(grafted_entry, attribute, foreign_root)
        grafted_snapshot = copy(built.snapshot)
        object.__setattr__(
            grafted_snapshot,
            "entries",
            tuple(
                grafted_entry if entry is local else entry
                for entry in built.snapshot.entries
            ),
        )
        grafted_result = verify_project_query_block_ir(grafted_snapshot)
        assert ProjectIRQueryBlockVerificationIssueKind.ACTIVE_ROOT in {
            issue.kind for issue in grafted_result.issues
        }

    replay = _completed(built, "replay_selected")
    rebound = _entry(built, "rebound_one")
    downstream = _completed(built, "downstream")
    joined = _completed(built, "joined")
    assert type(rebound) is ProjectIRReboundExistingOutput
    assert rebound.relation_input.use.output is replay.active_output.occurrence
    assert rebound.relation_input.producer is replay.active_properties
    assert downstream.relation_input is not None
    assert downstream.relation_input.use.output is joined.active_output.occurrence
    assert downstream.relation_input.producer is joined.active_properties


def test_active_root_authority_has_no_negative_one_subscript() -> None:
    for path in (PRODUCTION, VERIFICATION):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        forbidden = tuple(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.UnaryOp)
            and isinstance(node.slice.op, ast.USub)
            and isinstance(node.slice.operand, ast.Constant)
            and node.slice.operand.value == 1
        )
        assert forbidden == ()


def test_stale_join_and_upstream_terminals_allocate_no_fake_ir(built: _Built) -> None:
    stale = _entry(built, "stale_join")
    downstream = _entry(built, "downstream_stale")
    assert type(stale) is ProjectIRQueryBlockTerminal
    assert stale.reason is (
        ProjectIRQueryBlockTerminalReason.EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED
    )
    assert stale.starting_allocation is stale.ending_allocation
    assert stale.output is None
    assert stale.blocker
    assert type(downstream) is ProjectIRQueryBlockTerminal
    assert downstream.reason is (
        ProjectIRQueryBlockTerminalReason.ACTIVE_UPSTREAM_IR_NON_CONCRETE
    )
    assert downstream.blocker is stale
    assert downstream.starting_allocation is downstream.ending_allocation

    for name in ("semantic_bad", "semantic_bad_downstream"):
        terminal = _entry(built, name)
        assert type(terminal) is ProjectIRQueryBlockTerminal
        assert terminal.reason is (
            ProjectIRQueryBlockTerminalReason.SEMANTIC_OUTPUT_NON_CONCRETE
        )
        assert terminal.blocker is terminal.semantic_entry
        assert terminal.output is None
        assert terminal.starting_allocation is terminal.ending_allocation


def test_foreign_equal_looking_roots_stage_evidence_and_final_fields_are_rejected(
    built: _Built,
    foreign: _Built,
) -> None:
    grafted_root = copy(built.snapshot)
    object.__setattr__(grafted_root, "completed", foreign.completed)
    root_result = verify_project_query_block_ir(grafted_root)
    assert root_result.status is ProjectIRQueryBlockVerificationStatus.INVALID
    assert tuple(issue.kind for issue in root_result.issues) == (
        ProjectIRQueryBlockVerificationIssueKind.ROOT_CONTINUITY,
    )

    local = _completed(built, "mixed")
    foreign_entry = _completed(foreign, "mixed")
    local_final = next(
        item
        for item in local.operators
        if item.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION
    )
    foreign_final = next(
        item
        for item in foreign_entry.operators
        if item.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION
    )
    grafted_operator = replace(local_final, evidence=foreign_final.evidence)
    grafted_entry = copy(local)
    object.__setattr__(
        grafted_entry,
        "operators",
        tuple(
            grafted_operator if item is local_final else item
            for item in local.operators
        ),
    )
    grafted_snapshot = copy(built.snapshot)
    object.__setattr__(
        grafted_snapshot,
        "entries",
        tuple(
            grafted_entry if item is local else item for item in built.snapshot.entries
        ),
    )
    evidence_result = verify_project_query_block_ir(grafted_snapshot)
    assert ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE in {
        issue.kind for issue in evidence_result.issues
    }

    final_output = local.row_outputs[_kinds(local).index("final_projection")]
    foreign_field = foreign_entry.semantic_entry.fields[0]
    grafted_field = replace(
        final_output.row_shape.fields[0],
        semantic_source=foreign_field,
    )
    grafted_shape = replace(
        final_output.row_shape,
        fields=(grafted_field, *final_output.row_shape.fields[1:]),
    )
    grafted_output = replace(final_output, row_shape=grafted_shape)
    grafted_fields_entry = copy(local)
    object.__setattr__(
        grafted_fields_entry,
        "row_outputs",
        tuple(
            grafted_output if item is final_output else item
            for item in local.row_outputs
        ),
    )
    grafted_fields_snapshot = copy(built.snapshot)
    object.__setattr__(
        grafted_fields_snapshot,
        "entries",
        tuple(
            grafted_fields_entry if item is local else item
            for item in built.snapshot.entries
        ),
    )
    field_result = verify_project_query_block_ir(grafted_fields_snapshot)
    assert ProjectIRQueryBlockVerificationIssueKind.ROW_SHAPE in {
        issue.kind for issue in field_result.issues
    }

    local_policy = _completed(built, "qualified").window_policies[0]
    foreign_policy = _completed(foreign, "qualified").window_policies[0]
    with pytest.raises(ValueError, match="exact semantic authority"):
        replace(local_policy, evidence=foreign_policy.evidence)


def test_invalidation_reuses_change_domains_and_never_preserves_verification() -> None:
    topology = assess_project_query_block_ir_invalidation(
        (ProjectIRChangeDomain.TOPOLOGY,)
    )
    assert topology.invalidated == tuple(ProjectIRQueryBlockAnalysisKind)
    assert topology.preserved == ()
    assert topology.overlay is ProjectIRQueryBlockOverlayRequirement.REBUILD_REQUIRED
    assert topology.verification is ProjectIRVerificationRequirement.RERUN_REQUIRED

    properties = assess_project_query_block_ir_invalidation(
        (ProjectIRChangeDomain.PROPERTIES,)
    )
    assert properties.invalidated == ()
    assert properties.preserved == tuple(ProjectIRQueryBlockAnalysisKind)
    assert properties.overlay is ProjectIRQueryBlockOverlayRequirement.REBUILD_REQUIRED
    assert properties.verification is ProjectIRVerificationRequirement.RERUN_REQUIRED

    estimates = assess_project_query_block_ir_invalidation(
        (ProjectIRChangeDomain.ESTIMATES,)
    )
    assert estimates.invalidated == ()
    assert estimates.preserved == tuple(ProjectIRQueryBlockAnalysisKind)
    assert estimates.overlay is ProjectIRQueryBlockOverlayRequirement.PRESERVED

    root = assess_project_query_block_ir_invalidation(
        (),
        completed_semantic_root_changed=True,
    )
    assert root.invalidated == tuple(ProjectIRQueryBlockAnalysisKind)
    assert root.overlay is ProjectIRQueryBlockOverlayRequirement.REBUILD_REQUIRED
    assert root.verification is ProjectIRVerificationRequirement.RERUN_REQUIRED

    with pytest.raises(ValueError, match="explicit changed roots"):
        assess_project_query_block_ir_invalidation(
            (
                ProjectIRChangeDomain.PROPERTIES,
                ProjectIRChangeDomain.TOPOLOGY,
            )
        )


def test_private_boundary_historical_enum_and_verifier_independence_are_static() -> (
    None
):
    production = PRODUCTION.read_text(encoding="utf-8")
    verification = VERIFICATION.read_text(encoding="utf-8")
    historical = HISTORICAL_OPERATORS.read_text(encoding="utf-8")
    assert "class ProjectIRQueryBlockOperatorExtensionKind" in production
    assert production.count('QUALIFY = "qualify"') == 1
    assert "class ProjectIRLogicalOperatorKind" not in production
    assert historical.count("class ProjectIRLogicalOperatorKind") == 1
    assert "build_project_query_block_ir(" not in verification
    assert "__all__: tuple[str, ...] = ()" in production
    assert "__all__: tuple[str, ...] = ()" in verification
    for forbidden in (
        "project_ir_inspection",
        "project_ir_pure_boundary",
        "pietto.cli",
        "json_v2",
        "ProjectExplain",
        "emit_sql",
    ):
        assert forbidden not in production
        assert forbidden not in verification


def test_spec_records_exact_frozen_closure_budgets_and_slice_boundaries() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "8b56db95ab45933d05db2123b3e89fb81b8ac2fa",
        "c07493ab11dcf308a0cde01f9ef33a567096eb3c",
        "33855263140",
        "push / main / attempt 1 / success",
        "ProjectIRQueryBlockOperatorExtensionKind.QUALIFY",
        "EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED",
        "exact 11-path core closure",
        "A4/M7/D0",
        "175 -> 177",
        "418 -> 419",
        "production repairs 是 `10/12`",
        "mechanical closure paths 是 `0/12`",
        "authoritative validator starts 是 `0/4`",
        "Slice 15 单独拥有 observation/pure/E2E",
        "Phase 64 单独拥有 generic JOIN semantics",
    ):
        assert evidence in document
