from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import cast

import pytest

from _pietto_project_join import _completed
from pietto._project import project_grain
from pietto._project import project_ir_joins as joins
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_row_keys
from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_current_joins import (
    ProjectCurrentBinaryJoin,
    ProjectCurrentJoinRegion,
    ProjectCurrentJoinProperties,
    ProjectCurrentJoinGrainWitness,
    current_forward_at_most_one,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectEffectiveOutputCompletionTerminal,
    ProjectEffectiveOutputCompletionTerminalReason,
)
from pietto._project.project_grain import ProjectJoinGrainFactorIdentity
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_properties import (
    ProjectIRJoinRowOutput,
    ProjectIRProvidedNullExtension,
)
from pietto._project.project_query_block_ir import (
    ProjectIRQueryBlockSnapshot,
    ProjectIRQueryBlockTerminal,
    build_project_query_block_ir,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockVerificationStatus,
    verify_project_query_block_ir,
)
from pietto._project.project_join_conditions import (
    ProjectRelationshipMinimumBound,
    ProjectRelationshipMaximumBound,
)
from pietto.ast_nodes import AuthoredJoinKind

REPO_ROOT = Path(__file__).resolve().parents[1]


def _source() -> str:
    return """shape ARow:
    id: Int
    b_id: Int
    a_key = unique(id)
shape BRow:
    id: Int
    c_id: Int
    b_key = unique(id)
shape CRow:
    id: Int
    c_key = unique(id)
shape DRow:
    rid: Int
    match_id: Int
    d_key = unique(rid)
source a_rows: ARow = postgres.table("a")
source b_rows: BRow = postgres.table("b")
source c_rows: CRow = postgres.table("c")
source d_rows: DRow = postgres.table("d")
relationship one_to_one(a: ARow, b: BRow):
    a.id == b.id
relationship b_to_c(b: BRow, c: CRow):
    b.c_id == c.id
relationship many(a: ARow, d: DRow):
    a.b_id == d.match_id
relationship self_b(child: BRow, parent: BRow):
    child.id == parent.id
query inner_one:
    from a_rows
    let b = b_rows
    inner join b on one_to_one(a_rows, b)
    select:
        id
query left_one:
    from a_rows
    let b = b_rows
    left join b on one_to_one(a_rows, b)
    select:
        id
query inner_many:
    from a_rows
    let d = d_rows
    inner join d on many(a_rows, d)
    select:
        id
query multi_left:
    from a_rows
    let b = b_rows
    left join b on one_to_one(a_rows, b)
    let c = c_rows
    left join c on b_to_c(b, c)
    select:
        id
query branching:
    from a_rows
    let b = b_rows
    inner join b on one_to_one(a_rows, b)
    let d = d_rows
    inner join d on many(a_rows, d)
    select:
        id
query self_join:
    from b_rows
    let parent = b_rows
    left join parent on self_b(b_rows, parent)
    select:
        id
query prior_null_inner:
    from a_rows
    let b = b_rows
    left join b on one_to_one(a_rows, b)
    let c = c_rows
    inner join c on b_to_c(b, c)
    select:
        id
query blocked_region:
    from a_rows
    let b = b_rows
    inner join b on one_to_one(a_rows, b)
    let c = c_rows
    inner join c
    select:
        id
query inner_one_explicit:
    from a_rows
    let b = b_rows
    inner join b on one_to_one(a_rows, b)
    select:
        id = a_rows.id
query inner_handwritten:
    from a_rows
    let b = b_rows
    inner join b on a_rows.id == b.id
    select:
        id = a_rows.id
query multi_full:
    from a_rows
    let b = b_rows
    left join b on one_to_one(a_rows, b)
    let c = c_rows
    full join c on b_to_c(b, c)
    select:
        id = a_rows.id
query unrelated:
    from d_rows
    select:
        rid
"""


@dataclass(frozen=True, slots=True)
class _Built:
    completed: ProjectConcreteCompletedSemanticResult
    snapshot: ProjectIRQueryBlockSnapshot


def _build(root: Path, source: str = "") -> _Built:
    completed = _completed(root, source or _source())
    snapshot = build_project_query_block_ir(completed)
    verified = verify_project_query_block_ir(snapshot)
    assert verified.status is ProjectIRQueryBlockVerificationStatus.VERIFIED, (
        verified.issues
    )
    return _Built(completed=completed, snapshot=snapshot)


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(tmp_path_factory.mktemp("p62s11"))


def _region(built: _Built, name: str) -> ProjectCurrentJoinRegion:
    matches = tuple(
        item
        for item in built.completed.effective_outputs.current_regions
        if item.ledger.owner.definition.name == name
    )
    assert len(matches) == 1
    return matches[0]


def _properties(built: _Built, name: str) -> tuple[ProjectCurrentJoinProperties, ...]:
    properties = _region(built, name).join_properties
    assert properties and all(
        type(item) is ProjectCurrentJoinProperties for item in properties
    )
    return cast(tuple[ProjectCurrentJoinProperties, ...], properties)


def test_binary_topology_allocation_multihop_and_accumulated_left(
    built: _Built,
) -> None:
    direct = _region(built, "inner_one")
    multi = _region(built, "multi_left")
    branching = _region(built, "branching")
    assert len(direct.joins) == 1 and len(multi.joins) == len(branching.joins) == 2
    for region in (direct, multi, branching):
        assert all(type(item) is ProjectCurrentBinaryJoin for item in region.joins)
        assert all(
            tuple(slot.input_ordinal for slot in item.input_slots) == (0, 1)
            and len(item.input_uses) == 2
            for item in region.joins
        )
        count = len(region.joins)
        start, end = region.starting_allocation, region.ending_allocation
        assert end.next_plan_node_position == start.next_plan_node_position + count
        assert (
            end.next_output_value_position == start.next_output_value_position + count
        )
        assert (
            end.next_input_slot_position == start.next_input_slot_position + 2 * count
        )
        assert end.next_use_position == start.next_use_position + 2 * count
    assert multi.joins[1].left_input.output is multi.joins[0].output
    assert branching.joins[1].left_input.output is branching.joins[0].output
    named_source = branching.input_properties[0]
    assert branching.joins[1].left_input.output is not named_source.output
    second = cast(ProjectCurrentBinaryJoin, branching.joins[1])
    assert second.left_fields[0][0] is branching.ledger.bindings[0]
    left_output = second.left_input.output
    assert type(left_output) is ProjectIRJoinRowOutput
    assert (
        left_output.row_shape.fields[0].introduction_use
        is branching.joins[0].input_uses[0]
    )
    entries = {
        item.owner.definition.name: item
        for item in built.completed.effective_outputs.entries
    }
    ambiguous = entries["inner_one"]
    assert type(ambiguous) is ProjectEffectiveOutputCompletionTerminal
    assert (
        ambiguous.reason
        is ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
    )
    assert type(entries["inner_one_explicit"]) is ProjectCompletedEffectiveOutput


def test_non_concrete_ledger_is_zero_allocation_without_prefix_leak(
    built: _Built,
) -> None:
    (terminal,) = tuple(
        item
        for item in built.snapshot.entries
        if item.owner.definition.name == "blocked_region"
    )
    assert type(terminal) is ProjectIRQueryBlockTerminal
    assert terminal.ending_allocation is terminal.starting_allocation
    assert terminal.blocker is terminal.semantic_entry
    assert terminal.output is None and terminal.result_properties is None
    assert not any(
        item.ledger.owner is terminal.owner
        for item in built.completed.effective_outputs.current_regions
    )
    assert any(
        fragment.semantic_facts.owner.definition.name == "unrelated"
        for fragment in built.snapshot.base_plan.concrete_fragments
    )


def test_field_instances_nulling_provenance_self_roles_and_positive_property(
    built: _Built,
) -> None:
    multi = _properties(built, "multi_left")
    first_ref = multi[0].join.node.ref
    second_ref = multi[1].join.node.ref
    final_fields = multi[-1].join.output.row_shape.fields
    assert tuple(item.evidence.name for item in final_fields) == (
        "id",
        "b_id",
        "id",
        "c_id",
        "id",
    )
    assert all(item.nulling_joins == () for item in final_fields[:2])
    assert all(item.nulling_joins == (first_ref,) for item in final_fields[2:4])
    assert final_fields[4].nulling_joins == (second_ref,)
    assert all(
        item.effective_nullability is ProjectRowFieldNullability.NULLABLE
        for item in final_fields[2:]
    )
    assert type(multi[0].null_extension) is ProjectIRProvidedNullExtension
    assert type(multi[1].null_extension) is ProjectIRProvidedNullExtension

    full = _properties(built, "multi_full")
    first_full, second_full = (item.join.node.ref for item in full)
    full_fields = full[-1].join.output.row_shape.fields
    assert all(item.nulling_joins == (second_full,) for item in full_fields[:2])
    assert all(
        item.nulling_joins == (first_full, second_full) for item in full_fields[2:4]
    )
    assert full_fields[4].nulling_joins == (second_full,)

    self_output = _properties(built, "self_join")[0].join.output.row_shape
    left_id, left_c, right_id, right_c = self_output.fields
    assert left_id.evidence is right_id.evidence
    assert left_c.evidence is right_c.evidence
    assert left_id.introduction_use is not right_id.introduction_use


def test_actual_effects_use_direction_and_prior_null_source(built: _Built) -> None:
    inner = cast(ProjectCurrentBinaryJoin, _properties(built, "inner_one")[0].join)
    many = cast(ProjectCurrentBinaryJoin, _properties(built, "inner_many")[0].join)
    assert current_forward_at_most_one(inner.condition)
    assert not current_forward_at_most_one(many.condition)
    assert inner.condition.key_matches
    for proof in inner.condition.key_matches:
        assert proof.condition is inner.condition
        assert proof.minimum is ProjectRelationshipMinimumBound.ZERO_ALLOWED
        assert proof.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
        assert proof.equalities == inner.condition.mandatory_equalities
        assert all(
            equality.condition is inner.condition and equality.calls
            for equality in proof.equalities
        )
    # A hand-written ON equality matches the same keys with no call.
    handwritten = cast(
        ProjectCurrentBinaryJoin, _properties(built, "inner_handwritten")[0].join
    )
    assert handwritten.condition.ready
    assert current_forward_at_most_one(handwritten.condition)
    (equality,) = handwritten.condition.mandatory_equalities
    assert equality.calls == ()
    assert [
        (proof.binding.name, proof.equalities)
        for proof in handwritten.condition.key_matches
    ] == [(proof.binding.name, (equality,)) for proof in inner.condition.key_matches]
    left = _properties(built, "left_one")[0]
    assert type(left.null_extension) is ProjectIRProvidedNullExtension
    assert all(
        field.nulling_joins == (left.join.node.ref,)
        for field in left.join.output.row_shape.fields[2:]
    )
    prior = _properties(built, "prior_null_inner")
    assert type(prior[-1].null_extension) is ProjectIRProvidedNullExtension
    assert all(
        field.nulling_joins == (prior[0].join.node.ref,)
        for field in prior[-1].join.output.row_shape.fields[2:4]
    )
    assert prior[-1].join.output.row_shape.fields[-1].nulling_joins == ()


def test_key_and_fd_transfer_obey_direction_nulling_and_no_left_leakage(
    built: _Built,
) -> None:
    inner = _properties(built, "inner_one")[0].relational
    left_output = _properties(built, "left_one")[0]
    left = left_output.relational
    many = _properties(built, "inner_many")[0].relational
    assert any(
        key.strength is project_row_keys.ProjectRowUniquenessStrength.STRICT
        and tuple(
            member.evidence.name for item in key.determinants for member in item.members
        )
        == ("id",)
        for key in inner.keys
    )
    right_only = tuple(
        key
        for key in left.keys
        if all(
            member.field_position >= 2
            for item in key.determinants
            for member in item.members
        )
    )
    assert right_only and all(
        key.strength is project_row_keys.ProjectRowUniquenessStrength.LAX
        for key in right_only
    )
    assert any(
        tuple(
            member.evidence.name for item in key.determinants for member in item.members
        )
        == ("id", "rid")
        for key in many.keys
    )
    left_match = next(
        item for item in left.value_classes if item.members[0].field_position == 0
    )
    right_match = next(
        item for item in left.value_classes if item.members[0].field_position == 2
    )
    assert not any(
        fact.strength is project_row_keys.ProjectRowUniquenessStrength.STRICT
        and fact.determinants == (left_match,)
        and fact.dependents == (right_match,)
        for fact in left.fds
    )
    assert any(
        fact.strength is project_row_keys.ProjectRowUniquenessStrength.LAX
        and fact.determinants == (right_match,)
        and left_match in fact.dependents
        for fact in left.fds
    )
    reverse_fact = next(
        fact
        for fact in left.fds
        if fact.strength is project_row_keys.ProjectRowUniquenessStrength.LAX
        and fact.determinants == (right_match,)
        and left_match in fact.dependents
    )
    assert reverse_fact.supports
    assert all(
        any(support is key for key in right_only) for support in reverse_fact.supports
    )
    assert all(
        any(support is left_output.join for support in key.supports)
        for key in right_only
    )
    assert tuple(
        member.field_position
        for item in reverse_fact.dependents
        for member in item.members
    ) == (0, 1, 3)
    right_local = next(
        fact
        for fact in left.fds
        if tuple(item.members[0].field_position for item in fact.determinants) == (2,)
        and tuple(item.members[0].field_position for item in fact.dependents) == (3,)
    )
    assert right_local.strength is project_row_keys.ProjectRowUniquenessStrength.STRICT


def test_no_null_join_recomputes_key_strength_from_output_local_nullability(
    tmp_path: Path,
) -> None:
    source = """shape LeftRow:
    id: Int | None
    left_key = unique(id)
shape RightRow:
    id: Int | None
    value: Int | None
    right_key = unique(id)
source left_rows: LeftRow = postgres.table("left_rows")
source right_rows: RightRow = postgres.table("right_rows")
relationship match_rows(left: LeftRow, right: RightRow):
    left.id == right.id
query recomputed_keys:
    from left_rows
    let right = right_rows
    inner join right on match_rows(left_rows, right)
    select:
        id
"""
    output = _properties(_build(tmp_path / "key-strength", source), "recomputed_keys")[
        0
    ].relational
    singleton_keys = tuple(key for key in output.keys if len(key.determinants) == 1)
    assert len(singleton_keys) == 2
    assert all(
        key.strength is project_row_keys.ProjectRowUniquenessStrength.STRICT
        and all(
            member.effective_nullability is ProjectRowFieldNullability.NON_NULL
            for item in key.determinants
            for member in item.members
        )
        for key in singleton_keys
    )


def test_grain_factor_uses_and_directional_dependencies_are_occurrence_safe(
    built: _Built,
) -> None:
    left = _properties(built, "left_one")[0]
    factors = cast(
        tuple[ProjectJoinGrainFactorIdentity, ...], left.relational.grain.active
    )
    assert all(type(item) is ProjectJoinGrainFactorIdentity for item in factors)
    assert factors[0].introduction_use != factors[-1].introduction_use
    assert factors[-1].nulling_joins == (left.join.node.ref,)
    assert any(
        dependency.determinants == (factors[0],)
        and dependency.dependents == (factors[-1],)
        for dependency in left.relational.grain.dependencies
    )
    assert not any(
        dependency.determinants == (factors[-1],)
        and dependency.dependents == (factors[0],)
        for dependency in left.relational.grain.dependencies
    )
    assert left.relational.grain.dependencies
    witness = left.relational.grain.witness
    assert type(witness) is ProjectCurrentJoinGrainWitness
    assert witness.condition is cast(ProjectCurrentBinaryJoin, left.join).condition
    assert witness.left is left.join.left_input.grain
    assert witness.right is left.join.right_input.grain
    self_factors = cast(
        tuple[ProjectJoinGrainFactorIdentity, ...],
        _properties(built, "self_join")[0].relational.grain.active,
    )
    assert self_factors[0].base == self_factors[-1].base
    assert self_factors[0].introduction_use != self_factors[-1].introduction_use


def test_two_exact_global_inputs_remain_global_without_fake_factors(
    tmp_path: Path,
) -> None:
    source = """shape Row:
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
    let right = global_right
    inner join right on global_left.total == right.total
    select:
        total
"""
    grain = _properties(_build(tmp_path / "global", source), "global_join")[
        0
    ].relational.grain
    assert grain.state is project_grain.ProjectGrainBasisState.GLOBAL
    assert grain.active == ()
    assert len(grain.factors) == 2
    assert grain.dependencies == ()


def test_empty_global_source_factor_set_is_not_replaced_by_accumulated_factors(
    tmp_path: Path,
) -> None:
    source = """shape Row:
    id: Int
    row_key = unique(id)
shape RightRow:
    id: Int
source factor_rows: Row = postgres.table("factor_rows")
source right_rows: RightRow = postgres.table("right_rows")
query global_rows:
    from factor_rows
    select:
        total = count()
query global_branch:
    from factor_rows
    let counted = global_rows
    inner join counted on factor_rows.id == counted.total
    let right = right_rows
    inner join right on counted.total == right.id
    select:
        id
"""
    built = _build(tmp_path / "global-branch", source)
    outputs = _properties(built, "global_branch")
    second_join = cast(ProjectCurrentBinaryJoin, outputs[1].join)
    assert second_join.condition.key_matches == ()
    assert second_join.condition.inputs is not None
    assert _region(built, "global_branch").input_properties[1].grain.active == ()
    second = outputs[1].relational.grain
    assert len(second.active) == 2
    assert second.dependencies == ()


def test_join_carriers_reject_forged_effect_topology_and_match_evidence(
    built: _Built,
) -> None:
    direct = cast(ProjectCurrentBinaryJoin, _properties(built, "inner_one")[0].join)
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(direct, kind=AuthoredJoinKind.LEFT)
    with pytest.raises(ValueError, match="exact binding/input authority"):
        replace(direct, left_fields=(direct.left_fields[1], direct.left_fields[0]))
    match = next(
        item
        for item in direct.condition.key_matches
        if item.binding is direct.condition.use.target_binding
    )
    with pytest.raises(ValueError, match="complete exact input key"):
        replace(match, key=direct.left_input.keys[0])
    multi = _region(built, "multi_left")
    with pytest.raises(ValueError, match="exact operative condition/input membership"):
        replace(multi, operative=multi.operative[::-1])
    with pytest.raises(ValueError, match="exact allocation scope"):
        replace(
            direct,
            starting_allocation=replace(
                direct.starting_allocation, scope=ProjectIRSnapshotScope()
            ),
        )
    assert len(built.snapshot.structural.uses) > 1
    with pytest.raises(ValueError, match="dense"):
        replace(built.snapshot.structural, uses=built.snapshot.structural.uses[::-1])


def test_join_fd_index_preserves_arbitrary_width_python_int_masks(
    tmp_path: Path,
) -> None:
    left_fields = "".join(f"    a{position}: Int\n" for position in range(72))
    right_fields = "".join(f"    b{position}: Int\n" for position in range(72))
    source = (
        "shape LeftRow:\n"
        + left_fields
        + "    left_key = unique(a0)\n"
        + "shape RightRow:\n"
        + right_fields
        + "    right_key = unique(b0)\n"
        + 'source left_rows: LeftRow = postgres.table("left_rows")\n'
        + 'source right_rows: RightRow = postgres.table("right_rows")\n'
        + "relationship wide(left: LeftRow, right: RightRow):\n"
        + "    left.a0 == right.b0\n"
        + "query wide_join:\n"
        + "    from left_rows\n"
        + "    let right = right_rows\n"
        + "    inner join right on wide(left_rows, right)\n"
        + "    select:\n"
        + "        a0\n"
    )
    output = _properties(_build(tmp_path / "wide", source), "wide_join")[0].relational
    assert len(output.value_classes) == len(output.fd_index.universe) == 144
    all_classes = relational.ProjectIROutputValueClassSet(
        index=output.fd_index,
        classes=output.value_classes,
    )
    assert all_classes.mask.bit_count() == 144
    closure = relational.strict_output_fd_closure(
        output.fd_index,
        relational.ProjectIROutputValueClassSet(
            index=output.fd_index,
            classes=(output.value_classes[0],),
        ),
    )
    assert closure.classes.mask.bit_count() == 144


def test_base_barrier_private_boundaries_and_contract_are_exact(built: _Built) -> None:
    module_facts = built.completed.semantic_result.module_semantic_facts
    assert module_facts is not None
    assert all(
        fact.state.reason.value == "authored_join_deferred"
        for environment in module_facts.environments
        for fact in environment.relation_facts
        if getattr(fact.owner.definition, "join_clauses", ())
    )
    assert joins.__all__ == ()
    assert not hasattr(built.snapshot.base_plan, "join_regions")
    source = (
        (REPO_ROOT / "src/pietto/_project/project_ir_joins.py")
        .read_text(encoding="utf-8")
        .lower()
    )
    for forbidden in (
        "build_project_ir_pipeline",
        "join reorder",
        "shortest_path",
        "sql join",
        "chasm",
        "multi_fact",
    ):
        assert forbidden not in source
