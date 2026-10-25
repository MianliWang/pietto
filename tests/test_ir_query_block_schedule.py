from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, cast

import pytest


from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import project_completion as completion
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
)
from pietto._project.project_ir_construction import (
    ProjectIRConcreteSingleRelationFragment,
    ProjectIRNonConcreteSingleRelationFragment,
)
from pietto._project.project_joined_row_semantics import (
    ProjectConcreteJoinedRowSemantics,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectConcreteNoJoinReplay,
    ProjectEffectiveOutputCompletionTerminal,
    ProjectEffectiveOutputCompletionTerminalReason,
)
from pietto._project.project_query_block import ProjectNonConcreteQueryBlock
from pietto._project.project_ir_joins import ProjectIRNonConcreteJoinRegion
from pietto.ast_nodes import QueryDef, TableDef

from _pietto_project_completion_ledger import (
    REPO_ROOT,
    PRODUCTION,
    _project_files,
    _semantic_project,
    _owner,
    _entry,
    _coordinates,
)


@dataclass(frozen=True, slots=True)
class _Built:
    completed: ProjectConcreteCompletedSemanticResult
    reverse_completed: ProjectConcreteCompletedSemanticResult

    @property
    def result(self):
        return self.completed.completion

    @property
    def verification(self):
        return self.completed.verification

    @property
    def reverse_result(self):
        return self.reverse_completed.completion


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    root = tmp_path_factory.mktemp("completion-current")
    forward = build_project_completed_semantic_result(
        _semantic_project(root / "forward", _project_files(), reverse_creation=False)
    )
    reverse = build_project_completed_semantic_result(
        _semantic_project(root / "reverse", _project_files(), reverse_creation=True)
    )
    assert isinstance(forward, ProjectConcreteCompletedSemanticResult)
    assert isinstance(reverse, ProjectConcreteCompletedSemanticResult)
    return _Built(forward, reverse)


def test_inventory_ledger_and_schedule_cover_exact_owners_deterministically(
    built: _Built,
) -> None:
    result = built.result
    expected = tuple(
        fragment.semantic_facts.owner for fragment in result.plan.fragments
    )
    assert result.verification is built.verification
    assert result.plan is built.verification.root.evaluation.project_plan
    assert result.owners == expected
    assert len(result.entries) == len(result.owners)
    assert all(
        entry.owner is owner
        for entry, owner in zip(result.entries, result.owners, strict=True)
    )
    assert len({id(owner) for owner in result.schedule}) == len(result.owners)
    assert _coordinates(result.owners) == _coordinates(built.reverse_result.owners)
    assert _coordinates(result.schedule) == _coordinates(built.reverse_result.schedule)
    schedule_positions = {
        id(owner): position for position, owner in enumerate(result.schedule)
    }
    assert all(
        schedule_positions[id(edge.target)] < schedule_positions[id(edge.consumer)]
        for edge in result.dependencies
    )


def test_dependencies_retain_exact_resolution_and_join_binding_occurrences(
    built: _Built,
) -> None:
    result = built.result
    downstream = _owner(result, "a.pietto", "downstream_b")
    dependency = next(
        item for item in result.dependencies if item.consumer is downstream
    )
    semantic = next(
        fragment.semantic_facts
        for fragment in result.plan.fragments
        if fragment.semantic_facts.owner is downstream
    )
    assert dependency.evidence is semantic.resolution
    assert dependency.target is _owner(result, "c.pietto", "joined_a")
    assert semantic.resolution is not None
    assert semantic.resolution.target_symbol.local_name == "JoinedInput"
    assert dependency.target.identity.declared_name == "joined_a"

    repeated = _owner(result, "c.pietto", "repeated_join")
    repeated_dependencies = tuple(
        item for item in result.dependencies if item.consumer is repeated
    )
    region = next(
        item
        for item in built.completed.effective_outputs.current_regions
        if item.ledger.owner is repeated
    )
    assert tuple(item.evidence for item in repeated_dependencies) == tuple(
        binding for binding in region.ledger.bindings if binding.target is not None
    )
    assert tuple(item.dependency_ordinal for item in repeated_dependencies) == (0, 1, 2)
    assert repeated_dependencies[1].target is repeated_dependencies[2].target
    assert repeated_dependencies[1] is not repeated_dependencies[2]


def test_existing_concrete_outputs_and_properties_are_retained_without_rebuild(
    built: _Built,
) -> None:
    result = built.result
    for name in ("customers", "orders", "plain", "local_rows"):
        module_path = "a.pietto" if name == "local_rows" else "c.pietto"
        entry = _entry(result, module_path, name)
        assert type(entry) is completion.ProjectExistingEffectiveOutput
        fragment = next(
            item
            for item in result.plan.fragments
            if item.semantic_facts.owner is entry.owner
        )
        assert type(fragment) is ProjectIRConcreteSingleRelationFragment
        assert entry.fragment is fragment
        assert entry.output is fragment.root_relation_output
        assert entry.properties is next(
            item
            for item in built.verification.root.base_relational.outputs
            if item.output is fragment.root_relation_output
        )


def test_historical_join_terminals_and_current_outputs_keep_distinct_authority(
    built: _Built,
) -> None:
    base_joined = _entry(built.result, "c.pietto", "joined_a")
    base_derived = _entry(built.result, "c.pietto", "lineage_blocked_join")
    for entry in (base_joined, base_derived):
        assert type(entry) is completion.ProjectEffectiveOutputTerminal
        assert (
            entry.reason
            is completion.ProjectEffectiveOutputTerminalReason.JOINED_COMPLETION_NON_CONCRETE
        )
        assert entry.output is None
        assert entry.joined_completion is not None
        assert type(entry.joined_completion) is not ProjectConcreteJoinedRowSemantics
    overlay = built.completed.effective_outputs
    entries = {entry.owner.definition.name: entry for entry in overlay.entries}
    joined = entries["joined_a"]
    assert type(joined) is ProjectEffectiveOutputCompletionTerminal
    assert joined.base_entry is base_joined
    assert (
        joined.reason
        is ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
    )
    (region,) = tuple(
        region
        for region in overlay.current_regions
        if region.ledger.owner is joined.owner
    )
    assert joined.current_region is region and len(region.joins) == 1
    assert all(condition.ready for condition in region.operative)
    derived = entries["lineage_blocked_join"]
    assert type(derived) is ProjectCompletedEffectiveOutput
    assert derived.base_entry is base_derived
    (derived_region,) = tuple(
        region
        for region in overlay.current_regions
        if region.ledger.owner is derived.owner
    )
    assert derived_region.input_scope is not None
    producer = entries["computed_orders"]
    assert type(producer) is ProjectCompletedEffectiveOutput
    authority = derived_region.input_scope.bindings[1].authority
    assert authority is not None
    assert authority.entry is producer
    assert all(
        condition.ready and condition.key_matches == ()
        for condition in derived_region.operative
    )
    assert tuple(derived.schema.fields) == ("id",)


def test_explicit_projection_completes_without_changing_the_bare_id_control(
    tmp_path,
) -> None:
    files = _project_files()
    anchor = """query joined_a:
    from customers
    let order_input = orders
    inner join order_input on customer_orders(customers, order_input)
    select:
        id
"""
    assert files["c.pietto"].count(anchor) == 1
    files["c.pietto"] = files["c.pietto"].replace(
        anchor, anchor.replace("        id\n", "        id = customers.id\n")
    )
    completed = build_project_completed_semantic_result(
        _semantic_project(tmp_path / "project", files, reverse_creation=False)
    )
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    entries = {
        entry.owner.definition.name: entry
        for entry in completed.effective_outputs.entries
    }
    for name in ("joined_a", "downstream_b", "downstream_c"):
        entry = entries[name]
        assert type(entry) is ProjectCompletedEffectiveOutput
        assert tuple(entry.schema.fields) == ("id",)
    for name, upstream in (
        ("downstream_b", "joined_a"),
        ("downstream_c", "downstream_b"),
    ):
        entry = entries[name]
        assert type(entry) is ProjectCompletedEffectiveOutput
        assert type(entry.root) is ProjectConcreteNoJoinReplay
        assert entry.root.upstream_entry is entries[upstream]


def test_same_and_cross_module_pending_propagation_chain_is_exact(
    built: _Built,
) -> None:
    result = built.result
    base_joined = _entry(result, "c.pietto", "joined_a")
    base_b = _entry(result, "a.pietto", "downstream_b")
    base_c = _entry(result, "a.pietto", "downstream_c")
    overlay = built.completed.effective_outputs
    (joined,) = overlay.find_owner(base_joined.owner)
    (downstream_b,) = overlay.find_owner(base_b.owner)
    (downstream_c,) = overlay.find_owner(base_c.owner)
    assert type(joined) is ProjectEffectiveOutputCompletionTerminal
    assert joined.base_entry is base_joined
    for base, entry, upstream in (
        (base_b, downstream_b, joined),
        (base_c, downstream_c, downstream_b),
    ):
        assert type(base) is completion.ProjectEffectiveOutputTerminal
        assert (
            base.reason
            is completion.ProjectEffectiveOutputTerminalReason.HISTORICAL_NON_CONCRETE
        )
        assert type(entry) is ProjectEffectiveOutputCompletionTerminal
        assert (
            entry.reason
            is ProjectEffectiveOutputCompletionTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_NON_CONCRETE
        )
        assert entry.base_entry is base and entry.output is None
        assert entry.upstream_entry is entry.blocker is upstream
        assert entry.dependencies is base.dependencies
        assert len(entry.dependencies) == 1
        (dependency,) = entry.dependencies
        assert (
            dependency.consumer is entry.owner and dependency.target is upstream.owner
        )
        assert dependency.evidence is base.fragment.semantic_facts.resolution
    resolution = base_b.fragment.semantic_facts.resolution
    assert resolution is not None
    assert resolution.target_symbol.target_occurrence is joined.owner
    assert resolution.target_symbol.local_name == "JoinedInput"
    positions = {id(owner): index for index, owner in enumerate(result.schedule)}
    assert (
        positions[id(joined.owner)]
        < positions[id(downstream_b.owner)]
        < positions[id(downstream_c.owner)]
    )


def test_unrelated_nonconcrete_state_is_not_promoted_to_recoverable(
    built: _Built,
) -> None:
    opaque = _entry(built.result, "c.pietto", "opaque")
    child = _entry(built.result, "c.pietto", "unknown_child")
    for entry in (opaque, child):
        assert type(entry) is completion.ProjectEffectiveOutputTerminal
        assert (
            entry.reason
            is completion.ProjectEffectiveOutputTerminalReason.HISTORICAL_NON_CONCRETE
        )
        assert entry.output is None
        assert entry.pending_entries == ()
    assert (
        opaque.fragment.semantic_facts.state.status
        is ProjectRelationRowSchemaStatus.UNKNOWN
    )
    assert (
        child.fragment.semantic_facts.state.reason
        is ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN
    )


def test_join_over_pending_effective_input_retains_the_exact_historical_blocker(
    built: _Built,
) -> None:
    base = _entry(built.result, "a.pietto", "unsupported_join")
    assert type(base) is completion.ProjectEffectiveOutputTerminal
    assert (
        base.reason
        is completion.ProjectEffectiveOutputTerminalReason.JOINED_COMPLETION_NON_CONCRETE
    )
    (entry,) = built.completed.effective_outputs.find_owner(base.owner)
    assert entry is base and base.output is None
    blocker = base.joined_completion
    assert type(blocker) is ProjectNonConcreteQueryBlock
    assert blocker.verification is built.verification
    (region,) = tuple(
        region
        for region in built.verification.root.join_regions.regions
        if region.ledger.owner is base.owner
    )
    assert type(region) is ProjectIRNonConcreteJoinRegion
    assert blocker.join_region is region
    assert blocker.owner_bridge.owner is base.owner
    assert region.blockers == region.ledger.uses and len(region.blockers) == 1
    assert region.ending_allocation is region.starting_allocation
    assert len(region.ledger.bindings) == len(base.dependencies) == 2
    joined = _owner(built.result, "c.pietto", "joined_a")
    local = _owner(built.result, "a.pietto", "local_rows")
    assert tuple(item.target for item in base.dependencies) == (joined, local)
    for binding, dependency in zip(
        region.ledger.bindings, base.dependencies, strict=True
    ):
        assert dependency.evidence is binding and dependency.consumer is base.owner
    overlay = built.completed.effective_outputs
    (pending,) = overlay.find_owner(joined)
    (available,) = overlay.find_owner(local)
    assert type(pending) is ProjectEffectiveOutputCompletionTerminal
    assert (
        pending.reason
        is ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
    )
    assert type(available) is completion.ProjectExistingEffectiveOutput
    historical, operative = overlay.condition_authority, overlay.operative_conditions
    assert historical is not None and operative is not None
    (condition,) = tuple(
        item for item in historical.entries if item.use.owner is base.owner
    )
    (retained,) = tuple(
        item for item in operative.entries if item.use.owner is base.owner
    )
    assert retained is condition and condition.inputs is None
    assert condition.use is region.blockers[0] and not condition.ready
    assert condition.use.clause.on_clause is None
    # An unsuccessful optional attempt must not publish partial current authority.
    assert not any(scope.ledger.owner is base.owner for scope in overlay.input_scopes)
    assert not any(
        region.ledger.owner is base.owner for region in overlay.current_regions
    )
    assert any(region.ledger.owner is joined for region in overlay.current_regions)
    use_set = built.verification.root.join_regions.uses
    assert all(
        binding.target is None
        or any(
            binding.target.target_occurrence is owner for owner in built.result.owners
        )
        for ledger in use_set.ledgers
        for binding in ledger.bindings
    )


def test_ledger_preserves_historical_fragments_states_and_xor_shape(
    built: _Built,
) -> None:
    result = built.result
    assert all(
        (type(entry) is completion.ProjectExistingEffectiveOutput)
        != (type(entry) is completion.ProjectEffectiveOutputTerminal)
        for entry in result.entries
    )
    assert all(
        (entry.output is not None)
        if type(entry) is completion.ProjectExistingEffectiveOutput
        else (entry.output is None)
        for entry in result.entries
    )
    for entry, fragment in zip(result.entries, result.plan.fragments, strict=True):
        assert entry.owner is fragment.semantic_facts.owner
        assert entry.fragment is fragment
        if type(fragment) is ProjectIRNonConcreteSingleRelationFragment:
            assert fragment.semantic_facts.state is entry.fragment.semantic_facts.state
    for name in ("joined_a", "repeated_join", "lineage_blocked_join"):
        terminal = _entry(result, "c.pietto", name)
        assert type(terminal) is completion.ProjectEffectiveOutputTerminal
        definition = terminal.owner.definition
        assert type(definition) in {TableDef, QueryDef}
        assert cast(TableDef | QueryDef, definition).join_clauses
        assert (
            terminal.fragment.semantic_facts.state.reason
            is ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED
        )
    unsupported = _entry(result, "a.pietto", "unsupported_join")
    assert type(unsupported) is completion.ProjectEffectiveOutputTerminal
    assert (
        unsupported.fragment.semantic_facts.state.reason
        is ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED
    )


def test_slice7_scope_dependency_and_contract_are_exact() -> None:
    facts = REPOSITORY_FACTS.python(PRODUCTION)
    assert completion.__all__ == ()
    assert "deque" in facts.identifiers
    assert not re.search(r"^class .*Graph", facts.text, re.MULTILINE)
    for required in (
        "ProjectIRProjectPlan",
        "ProjectResolvedModuleRelationReference",
        "ProjectRelationBindingOccurrence",
        "ProjectConcreteJoinedRowSemantics",
        "ProjectIROutputRelationalProperties",
    ):
        assert required in facts.identifiers
    for forbidden in (
        "build_project_relationships",
        "build_project_relationship_uses",
        "build_explicit_relationship_path",
        "whereclause",
        "groupbyclause",
        "windowexpr",
        "qualify",
        "finalprojection",
        "executor",
        "arrow",
        "sql",
    ):
        assert forbidden not in facts.text.casefold()
    assert "ProjectRowSchema" not in facts.identifiers
    for relative in (
        "src/pietto/_project/project_ir_composition.py",
        "src/pietto/_project/module_relation_resolution.py",
        "src/pietto/_project/module_semantic_fact_preservation.py",
        "src/pietto/_project/project_relationship_uses.py",
        "src/pietto/_project/project_phase62_verification.py",
        "src/pietto/_project/project_joined_row_semantics.py",
    ):
        assert not any(
            name.endswith(".project_completion")
            for name in REPOSITORY_FACTS.python(REPO_ROOT / relative).imported_modules
        )


EXISTS_HEAD = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
source tags: Row = postgres.table("tags")
"""
# `flagged` is declared after its reader, so only the read orders it first.
EXISTS_READS = """query result:
    let picked:
        from tags
        select:
            id
    from rows
    where exists picked and not exists flagged
    select:
        id
query flagged:
    from tags
    select:
        id
"""


def _exists_completed(tmp_path, body: str):
    from _pietto_project_join import _completed

    return _completed(tmp_path, EXISTS_HEAD + body)


def test_expression_reads_order_their_targets_without_input_slots(
    tmp_path,
) -> None:
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )

    completed = _exists_completed(tmp_path, EXISTS_READS)
    assert completed.ok, completed.diagnostics
    result = completed.completion
    uses = result.expression_uses
    assert [
        (u.consumer.definition.name, u.target.definition.name, u.ordinal) for u in uses
    ] == [("result", "picked", 0), ("result", "flagged", 1)]
    assert [u.evidence.read.position.value for u in uses] == ["where", "where"]
    positions = {id(owner): i for i, owner in enumerate(result.schedule)}
    assert all(positions[id(u.target)] < positions[id(u.consumer)] for u in uses)
    # A read is never one of its consumer's relation-input dependencies.
    consumer = uses[0].consumer
    assert [
        d.target.definition.name for d in result.dependencies if d.consumer is consumer
    ] == ["rows"]
    snapshot = build_project_query_block_ir(completed)
    assert verify_project_query_block_ir(snapshot).verified
    for edge, use in zip(snapshot.expression_uses, uses, strict=True):
        assert edge.use is use and edge.column is None
        assert edge.consumer.owner is use.consumer
        assert edge.producer.owner is use.target
        assert edge.output is edge.producer.output and edge.schema is not None


def test_the_ir_rejects_a_deleted_forged_or_swapped_expression_edge(
    tmp_path,
) -> None:
    from copy import copy

    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        ProjectIRQueryBlockVerificationIssueKind,
        verify_project_query_block_ir,
    )

    def graft(value, **changes):
        changed = copy(value)
        for name, item in changes.items():
            object.__setattr__(changed, name, item)
        return changed

    snapshot = build_project_query_block_ir(_exists_completed(tmp_path, EXISTS_READS))
    first, second = snapshot.expression_uses
    rows = next(e for e in snapshot.entries if e.owner.definition.name == "rows")
    for edges in (
        (),
        (first,),
        (second, first),
        (graft(first, producer=rows, output=rows.output), second),
        (graft(first, use=second.use), second),
    ):
        issues = verify_project_query_block_ir(
            graft(snapshot, expression_uses=edges)
        ).issues
        assert ProjectIRQueryBlockVerificationIssueKind.EXPRESSION_BLOCK_USE in {
            issue.kind for issue in issues
        }


def test_a_read_that_closes_a_relation_cycle_is_reported_and_unresolved(
    tmp_path,
) -> None:
    body = """query a:
    from rows
    where exists b
    select:
        id
query b:
    from tags
    where exists a
    select:
        id
query self:
    from rows
    where exists self
    select:
        id
"""
    completed = _exists_completed(tmp_path, body)
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in completed.diagnostics
    ] == [
        ("PIE-S2302", "Relation cycle detected: a -> b -> a", 12, 11),
        ("PIE-S2302", "Relation cycle detected: self -> self", 17, 11),
    ]
    result = completed.completion
    # Only the accepted read remains an edge; nothing is cycle-blocked.
    assert [
        (u.consumer.definition.name, u.target.definition.name)
        for u in result.expression_uses
    ] == [("a", "b")]
    assert not result.topology.blocked_owners and not result.topology.cycles


SCALAR_READS = """shape Row:
    id: Int
    key: Int | None
source rows: Row = postgres.table("rows")
source tags: Row = postgres.table("tags")
query result:
    let picked:
        from tags
        select:
            id
            key
    from rows
    where id == scalar picked.key
    select:
        id
        k = scalar tags.id
"""


def test_a_scalar_read_edge_binds_its_one_named_output_column(tmp_path) -> None:
    from copy import copy

    from _pietto_project_join import _completed
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        ProjectIRQueryBlockVerificationIssueKind,
        verify_project_query_block_ir,
    )

    def graft(value, **changes):
        changed = copy(value)
        for name, item in changes.items():
            object.__setattr__(changed, name, item)
        return changed

    snapshot = build_project_query_block_ir(_completed(tmp_path, SCALAR_READS))
    assert verify_project_query_block_ir(snapshot).verified
    first, second = snapshot.expression_uses
    assert [(e.producer.owner.definition.name, e.column) for e in (first, second)] == [
        ("picked", 1),
        ("tags", 0),
    ]
    assert first.output is not None
    assert [f.evidence.name for f in first.output.row_shape.fields] == ["id", "key"]
    for edges in (
        # Another existing column of the same block, and no column at all.
        (graft(first, column=0), second),
        (first, graft(second, column=None)),
    ):
        issues = verify_project_query_block_ir(
            graft(snapshot, expression_uses=edges)
        ).issues
        assert ProjectIRQueryBlockVerificationIssueKind.EXPRESSION_BLOCK_USE in {
            issue.kind for issue in issues
        }


MEMBERSHIP_READS = """query result:
    let picked:
        from tags
        select:
            id
    from rows
    where id in picked and id not in tags and id in pairs
    select:
        id
query pairs:
    from tags
    let r = rows
    inner join r on tags.id == r.id
    select:
        id = tags.id
        twice = r.id
"""


def test_a_membership_read_binds_the_sole_column_of_its_target(tmp_path) -> None:
    from copy import copy

    from _pietto_project_join import _completed
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        ProjectIRQueryBlockVerificationIssueKind,
        verify_project_query_block_ir,
    )

    def graft(value, **changes):
        changed = copy(value)
        for name, item in changes.items():
            object.__setattr__(changed, name, item)
        return changed

    completed = _completed(tmp_path, EXISTS_HEAD + MEMBERSHIP_READS)
    assert completed.ok, completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    assert verify_project_query_block_ir(snapshot).verified
    edges = snapshot.expression_uses
    # A let, a source and a two-column JOIN query, whose columns are known
    # only after completion: only one-column targets bind.
    assert [(e.producer.owner.definition.name, e.column) for e in edges] == [
        ("picked", 0),
        ("tags", 0),
        ("pairs", None),
    ]
    for index, column in ((0, None), (0, 1), (2, 0)):
        forged = tuple(
            graft(edge, column=column) if position == index else edge
            for position, edge in enumerate(edges)
        )
        issues = verify_project_query_block_ir(
            graft(snapshot, expression_uses=forged)
        ).issues
        assert ProjectIRQueryBlockVerificationIssueKind.EXPRESSION_BLOCK_USE in {
            issue.kind for issue in issues
        }


CAPTURE_HEAD = """shape Row:
    id: Int
    key: Int | None
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
"""
# Phase70 S10: the let reads the current row of the body's FROM and LEFT JOIN
# inputs; only the body's EXISTS read orders the let first.
CAPTURE_JOINED = """query result:
    let matched:
        capture r
        capture lhs
        from rhs
        where rhs.key == r.key and rhs.id == lhs.id
        select:
            id
    from lhs
    let r = rhs
    left join r on lhs.id == r.id
    where exists matched
    select:
        a = lhs.id
"""
CAPTURE_INPUT = """query result:
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key
        select:
            id
    from lhs
    select:
        a = lhs.id
        e = exists matched
"""


def _capture_snapshot(tmp_path, body: str):
    from _pietto_project_join import _completed

    from pietto._project.project_query_block_ir import build_project_query_block_ir

    completed = _completed(tmp_path, CAPTURE_HEAD + body)
    assert completed.ok, completed.diagnostics
    return completed, build_project_query_block_ir(completed)


def test_capture_edges_carry_outer_rows_without_ordering_blocks(tmp_path) -> None:
    from pietto._project.project_query_block_ir import ProjectIRCaptureStage
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )

    completed, snapshot = _capture_snapshot(tmp_path, CAPTURE_JOINED)
    completion = completed.completion
    captures = completion.capture_uses
    assert [
        (c.inner.let_position, c.outer.let_position, c.ordinal, c.clause.name)
        for c in captures
    ] == [(0, None, 0, "r"), (0, None, 1, "lhs")]
    # Each line binds the body's own JOIN (1) or FROM (0) dependency; no
    # capture edge is a dependency, and only the EXISTS read orders the let.
    assert [c.dependency.dependency_ordinal for c in captures] == [1, 0]
    assert all(c.dependency.consumer is c.outer for c in captures)
    inner, outer = captures[0].inner, captures[0].outer
    assert not any(
        {id(d.consumer), id(d.target)} == {id(inner), id(outer)}
        for d in completion.dependencies
    )
    positions = {id(owner): i for i, owner in enumerate(completion.schedule)}
    assert positions[id(inner)] < positions[id(outer)]
    assert verify_project_query_block_ir(snapshot).verified
    right, left = snapshot.capture_uses
    assert right.checkpoint is left.checkpoint
    checkpoint = right.checkpoint
    assert checkpoint.stage is ProjectIRCaptureStage.JOINED
    outer: Any = checkpoint.outer
    assert checkpoint.output is outer.join_prefix.final_join.output
    assert checkpoint.read.producer is right.inner
    assert checkpoint.bindings == ((0, (0, 1)), (1, (2, 3)))
    assert (right.fields, left.fields) == ((2, 3), (0, 1))
    # The captured r.key is the null-extended joined occurrence.
    fields: Any = checkpoint.output.row_shape.fields
    assert [
        (f.expression.capture, f.expression.field, f.position)
        for f in snapshot.captured_fields
    ] == [("r", "key", 3), ("lhs", "id", 0)]
    assert fields[3].nulling_joins and not fields[0].nulling_joins


def test_a_capture_of_an_unjoined_body_reads_its_input_row(tmp_path) -> None:
    from pietto._project.project_query_block_ir import (
        ProjectIRCaptureStage,
        ProjectIRExpressionBlockUse,
    )
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )

    _, snapshot = _capture_snapshot(tmp_path, CAPTURE_INPUT)
    assert verify_project_query_block_ir(snapshot).verified
    (use,) = snapshot.capture_uses
    assert use.checkpoint.stage is ProjectIRCaptureStage.INPUT
    read = use.checkpoint.read
    assert isinstance(read, ProjectIRExpressionBlockUse)
    assert read.use.evidence.read.position.value == "select"
    assert use.fields == (0, 1)
    (captured,) = snapshot.captured_fields
    assert (captured.expression.field, captured.position) == ("key", 1)


def test_the_ir_rejects_forged_or_swapped_capture_edges(tmp_path) -> None:
    from copy import copy

    from pietto._project.project_query_block_ir import ProjectIRCaptureStage
    from pietto._project.project_query_block_ir_verification import (
        ProjectIRQueryBlockVerificationIssueKind,
        verify_project_query_block_ir,
    )

    def graft(value, **changes):
        changed = copy(value)
        for name, item in changes.items():
            object.__setattr__(changed, name, item)
        return changed

    _, snapshot = _capture_snapshot(tmp_path, CAPTURE_JOINED)
    right, left = snapshot.capture_uses
    first, second = snapshot.captured_fields
    checkpoint = right.checkpoint
    outer: Any = checkpoint.outer
    filter_output = outer.row_outputs[0]
    forged = (
        {"capture_uses": ()},
        {"capture_uses": (left, right)},
        {"capture_uses": (graft(right, fields=left.fields), left)},
        {"capture_uses": (graft(right, capture=left.capture), left)},
        {
            "capture_uses": (
                graft(
                    right,
                    checkpoint=graft(checkpoint, stage=ProjectIRCaptureStage.INPUT),
                ),
                left,
            )
        },
        {
            "capture_uses": (
                graft(right, checkpoint=graft(checkpoint, output=filter_output)),
                left,
            )
        },
        {"captured_fields": (graft(first, position=2), second)},
        {"captured_fields": (second, first)},
        {"captured_fields": (first,)},
    )
    for changes in forged:
        issues = verify_project_query_block_ir(graft(snapshot, **changes)).issues
        assert ProjectIRQueryBlockVerificationIssueKind.CAPTURE_USE in {
            issue.kind for issue in issues
        }, changes


# Phase70 S14: a scalar and an IN read of two capturing lets in one body; each
# capture checkpoint names its own let's read edge and that edge's column.
CAPTURE_SCALAR_IN = """query result:
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key
        select:
            id
            key
    let other:
        capture lhs
        from rhs
        where rhs.id == lhs.id
        select:
            id
    from lhs
    where lhs.id not in other
    select:
        a = lhs.id
        k = scalar matched.key
"""


def test_scalar_and_in_reads_keep_their_own_capture_edges(tmp_path) -> None:
    from copy import copy

    from pietto._project.project_query_block_ir import ProjectIRCaptureStage
    from pietto._project.project_query_block_ir_verification import (
        ProjectIRQueryBlockVerificationIssueKind as Kind,
        verify_project_query_block_ir,
    )

    def graft(value, **changes):
        changed = copy(value)
        for name, item in changes.items():
            object.__setattr__(changed, name, item)
        return changed

    _, snapshot = _capture_snapshot(tmp_path, CAPTURE_SCALAR_IN)
    assert verify_project_query_block_ir(snapshot).verified
    membership, scalar = snapshot.expression_uses
    assert [
        (e.producer.owner.definition.name, e.column, type(e.use.expression).__name__)
        for e in (membership, scalar)
    ] == [
        ("other", 0, "RelationMembershipExpr"),
        ("matched", 1, "RelationScalarExpr"),
    ]
    matched, other = snapshot.capture_uses
    assert matched.checkpoint.read is scalar and other.checkpoint.read is membership
    assert {matched.checkpoint.stage, other.checkpoint.stage} == {
        ProjectIRCaptureStage.INPUT
    }
    assert [(f.expression.field, f.position) for f in snapshot.captured_fields] == [
        ("key", 1),
        ("id", 0),
    ]
    for changes, kind in (
        # Each checkpoint names the other let's read of the same body.
        (
            {
                "capture_uses": (
                    graft(matched, checkpoint=other.checkpoint),
                    graft(other, checkpoint=matched.checkpoint),
                )
            },
            Kind.CAPTURE_USE,
        ),
        # The scalar read names another existing column of its let, and the
        # membership read no column.
        ({"expression_uses": (membership, graft(scalar, column=0))}, None),
        ({"expression_uses": (graft(membership, column=None), scalar)}, None),
    ):
        issues = verify_project_query_block_ir(graft(snapshot, **changes)).issues
        assert (kind or Kind.EXPRESSION_BLOCK_USE) in {i.kind for i in issues}, changes


# Phase70 S12: a JOIN reads the let LATERAL; its capture lines read the row of
# the bindings left of that JOIN (the LEFT JOIN's null-extended r included),
# never the final joined row, and the JOIN orders the let first.
CAPTURE_LATERAL = """query result:
    let matched:
        capture r
        capture lhs
        from rhs
        where rhs.key == r.key and rhs.id == lhs.id
        select:
            id
    from lhs
    let r = rhs
    left join r on lhs.id == r.id
    let m = matched
    cross join m
    let z = rhs
    inner join z on z.id == m.id
    select:
        a = lhs.id
"""


def test_a_lateral_capture_reads_the_row_left_of_its_join(tmp_path) -> None:
    from pietto._project.project_query_block_ir import (
        ProjectIRCaptureCheckpoint,
        ProjectIRCaptureStage,
        ProjectIRCompletedQueryBlockOutput,
    )
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )

    completed, snapshot = _capture_snapshot(tmp_path, CAPTURE_LATERAL)
    assert verify_project_query_block_ir(snapshot).verified
    right, left = snapshot.capture_uses
    checkpoint = right.checkpoint
    assert checkpoint is left.checkpoint
    assert checkpoint.stage is ProjectIRCaptureStage.LATERAL
    outer = checkpoint.outer
    assert type(outer) is ProjectIRCompletedQueryBlockOutput
    assert outer.join_prefix is not None
    joins = outer.join_prefix.joins
    assert checkpoint.read is joins[1].inputs[1]
    assert checkpoint.output is joins[1].output
    assert checkpoint.producer is right.inner.owner
    assert checkpoint.bindings == ((0, (0, 1)), (1, (2, 3)))
    assert (right.fields, left.fields) == ((2, 3), (0, 1))
    assert joins[1].output.row_shape.fields[3].nulling_joins
    positions = {id(owner): i for i, owner in enumerate(completed.completion.schedule)}
    assert positions[id(right.inner.owner)] < positions[id(checkpoint.outer.owner)]
    # Another JOIN's right input is not this let's read.
    try:
        ProjectIRCaptureCheckpoint(
            outer=checkpoint.outer,
            read=joins[2].inputs[1],
            stage=checkpoint.stage,
            output=checkpoint.output,
            bindings=checkpoint.bindings,
        )
    except ValueError as error:
        assert "exact outer row" in str(error)
    else:
        raise AssertionError("a foreign JOIN input imaged this let's read")


def test_the_ir_rejects_forged_lateral_capture_checkpoints(tmp_path) -> None:
    from copy import copy

    from pietto._project.project_query_block_ir import (
        ProjectIRCaptureStage,
        ProjectIRCompletedQueryBlockOutput,
    )
    from pietto._project.project_query_block_ir_verification import (
        ProjectIRQueryBlockVerificationIssueKind,
        verify_project_query_block_ir,
    )

    def graft(value, **changes):
        changed = copy(value)
        for name, item in changes.items():
            object.__setattr__(changed, name, item)
        return changed

    _, snapshot = _capture_snapshot(tmp_path, CAPTURE_LATERAL)
    right, left = snapshot.capture_uses
    checkpoint = right.checkpoint
    outer = checkpoint.outer
    assert type(outer) is ProjectIRCompletedQueryBlockOutput
    assert outer.join_prefix is not None
    joins = outer.join_prefix.joins
    for changes in (
        {"read": joins[2].inputs[1]},
        {"read": joins[1].inputs[0]},
        {"output": joins[2].output},
        {"stage": ProjectIRCaptureStage.JOINED},
        {"bindings": checkpoint.bindings + ((2, (4,)),)},
    ):
        forged = graft(checkpoint, **changes)
        candidate = graft(
            snapshot,
            capture_uses=(
                graft(right, checkpoint=forged),
                graft(left, checkpoint=forged),
            ),
        )
        issues = verify_project_query_block_ir(candidate).issues
        assert ProjectIRQueryBlockVerificationIssueKind.CAPTURE_USE in {
            issue.kind for issue in issues
        }, changes


_GROUPED_ENDPOINT_SOURCE = """shape Sale:
    id: Int
    uid: Int
    amount: Int
source sales: Sale = postgres.table("sales")
query per_user:
    from sales
    group by:
        uid
    select:
        k = uid
        total = sum(amount)
query q:
    from per_user
    let x = sales
    left join x on per_user.k == x.uid
    select:
        v = x.amount
"""


def test_join_over_grouped_input_retains_history_and_uses_current_producer(
    tmp_path,
) -> None:
    from _pietto_project_join import _completed
    from pietto._project.model import ProjectRowFieldNullability
    from pietto._project.project_query_block_ir import build_project_query_block_ir
    from pietto._project.project_query_block_ir_verification import (
        verify_project_query_block_ir,
    )

    result = _completed(tmp_path, _GROUPED_ENDPOINT_SOURCE)
    (base,) = tuple(
        entry
        for entry in result.completion.entries
        if entry.owner.identity.declared_name == "q"
    )
    assert type(base) is completion.ProjectEffectiveOutputTerminal
    assert (
        base.reason
        is completion.ProjectEffectiveOutputTerminalReason.JOINED_COMPLETION_NON_CONCRETE
    )
    assert (
        base.fragment.semantic_facts.state.reason
        is ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED
    )
    entries = {
        entry.owner.definition.name: entry for entry in result.effective_outputs.entries
    }
    current, grouped = entries["q"], entries["per_user"]
    assert type(current) is ProjectCompletedEffectiveOutput
    assert type(grouped) is ProjectCompletedEffectiveOutput
    assert current.base_entry is base
    assert tuple(grouped.schema.fields) == ("k", "total")
    assert tuple(current.schema.fields) == ("v",)
    assert current.schema.fields["v"].nullability is ProjectRowFieldNullability.NULLABLE
    (region,) = tuple(
        region
        for region in result.effective_outputs.current_regions
        if region.ledger.owner is current.owner
    )
    assert region.input_scope is not None
    authority = region.input_scope.bindings[0].authority
    assert authority is not None
    assert authority.entry is grouped
    assert all(
        condition.ready and condition.key_matches == ()
        for condition in region.operative
    )
    assert result.ok, result.diagnostics
    assert verify_project_query_block_ir(build_project_query_block_ir(result)).verified


_GLOBAL_JOIN_SOURCE = """shape Row:
    id: Int
source left_rows: Row = postgres.table("left_rows")
source right_rows: Row = postgres.table("right_rows")
query global_left:
    from left_rows
    select:
        total = count()
query global_right:
    from right_rows
    select:
        total = count()
query global_join:
    from global_left
    let counted_right = global_right
    inner join counted_right on global_left.total == counted_right.total
    select:
        total
"""
_SHARED_PROJECTION_TERMINALS = (
    "aligned_join",
    "comparable_join",
    "incompatible_join",
    "self_fact_join",
    "global_join",
    "ambiguous_fact_join",
)


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            "join_differential",
            (
                *_SHARED_PROJECTION_TERMINALS,
                "unique_target_inner",
                "unique_target_left",
                "fanout_join",
            ),
        ),
        ("project_aggregate", _SHARED_PROJECTION_TERMINALS),
        ("global_join", ("global_join",)),
    ),
)
def test_project_check_of_test_join_sources_reports_instead_of_raising(
    tmp_path, source: str, expected: tuple[str, ...]
) -> None:
    from _pietto_ir_join_differential import PRIMARY_MAIN_SOURCE
    from _pietto_project_aggregate import _source as aggregate_source
    from _pietto_project_join import _completed
    from pietto._project.project_final_outputs import (
        ProjectCompletedEffectiveOutput,
        ProjectEffectiveOutputCompletionTerminal,
        ProjectEffectiveOutputCompletionTerminalReason,
    )

    text = {
        "join_differential": PRIMARY_MAIN_SOURCE,
        "project_aggregate": aggregate_source(),
        "global_join": _GLOBAL_JOIN_SOURCE,
    }[source]
    result = _completed(tmp_path, text)
    entries = {
        entry.owner.definition.name: entry for entry in result.effective_outputs.entries
    }
    regions = result.effective_outputs.current_regions
    actual_projection = tuple(
        entry.owner.definition.name
        for entry in result.effective_outputs.entries
        if type(entry) is ProjectEffectiveOutputCompletionTerminal
        and entry.reason
        is ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
    )
    expected_projection = tuple(
        owner.definition.name
        for owner in result.effective_outputs.owners
        if owner.definition.name in expected
    )
    assert len(expected_projection) == len(expected)
    assert actual_projection == expected_projection
    for name in expected:
        terminal = entries[name]
        assert type(terminal) is ProjectEffectiveOutputCompletionTerminal
        assert terminal.output is None
        (prefix,) = tuple(
            region for region in regions if region.ledger.owner is terminal.owner
        )
        assert prefix.joins and all(condition.ready for condition in prefix.operative)
    if source == "project_aggregate":
        assert isinstance(
            entries["aggregate_left_outputs"], ProjectCompletedEffectiveOutput
        )
    if source != "global_join":
        from pietto._project.project_join_conditions import ProjectJoinConditionState
        from pietto._project.project_ir_joins import ProjectIRNonConcreteJoinRegion
        from pietto._project.project_query_block import (
            ProjectNonConcreteQueryBlock,
            ProjectQueryBlockNonConcreteReason,
        )

        missing = entries["missing_fact_join"]
        operative = result.effective_outputs.operative_conditions
        assert operative is not None
        (condition,) = tuple(
            item for item in operative.entries if item.use.owner is missing.owner
        )
        assert condition.state is ProjectJoinConditionState.UNAVAILABLE
        assert not condition.ready and condition.expression is None
        assert condition.use.clause.on_clause is None
        assert all(binding.target is not None for binding in condition.ledger.bindings)
        assert isinstance(
            missing,
            (
                completion.ProjectEffectiveOutputTerminal,
                ProjectEffectiveOutputCompletionTerminal,
            ),
        )
        assert missing.output is None
        if type(missing) is completion.ProjectEffectiveOutputTerminal:
            assert (
                missing.reason
                is completion.ProjectEffectiveOutputTerminalReason.JOINED_COMPLETION_NON_CONCRETE
            )
            blocker = missing.joined_completion
            assert type(blocker) is ProjectNonConcreteQueryBlock
            assert (
                blocker.reason
                is ProjectQueryBlockNonConcreteReason.JOIN_REGION_NON_CONCRETE
            )
            assert blocker.row_source is None
            assert type(blocker.join_region) is ProjectIRNonConcreteJoinRegion
            assert blocker.join_region.ledger is condition.ledger
            assert any(
                blocker.join_region is region
                for region in result.verification.root.join_regions.regions
            )
            assert len(blocker.join_region.blockers) == 1
            assert blocker.join_region.blockers[0] is condition.use
        else:
            assert type(missing) is ProjectEffectiveOutputCompletionTerminal
            assert (
                missing.reason
                is ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_CONDITION_NON_CONCRETE
            )
            assert type(missing.blocker) is tuple and len(missing.blocker) == 1
            assert missing.blocker[0] is condition
            assert (
                condition.inputs is not None
                and condition.inputs.scope is missing.current_inputs
            )
            assert missing.current_region is None
    assert not result.ok and result.diagnostics
