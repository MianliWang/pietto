from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, cast

import pytest

from pietto._project import check as project_check
from pietto._project import project_grain
from pietto._project import project_ir_joins as joins
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_relationship_conditions as conditions
from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project import project_relationship_paths as paths
from pietto._project import project_relationship_uses as relationship_uses
from pietto._project import project_relationships, project_row_keys, project_value_fds
from pietto._project.model import (
    ProjectRowFieldNullability,
    build_empty_project_semantic_result,
)
from pietto._project.project_grain import ProjectJoinGrainFactorIdentity
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_properties import (
    ProjectIRPropertyAvailability,
    ProjectIRProvidedNullExtension,
)
from pietto._project.project_ir_verification import (
    build_project_ir_analysis_bundle,
    verify_project_ir_stage,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice11-project-ir-binary-join-region-multi-input-topology-null-extension-property-transfer-v1.md"
)


def _source() -> str:
    return """shape ARow:
    id: Int not null
    b_id: Int not null
    unique a_key on id
shape BRow:
    id: Int not null
    c_id: Int not null
    unique b_key on id
shape CRow:
    id: Int not null
    unique c_key on id
shape DRow:
    rid: Int not null
    match_id: Int not null
    unique d_key on rid
source a_rows: ARow is postgres.table("a")
source b_rows: BRow is postgres.table("b")
source c_rows: CRow is postgres.table("c")
source d_rows: DRow is postgres.table("d")
relationship one_to_one:
    endpoint a: a_rows
    endpoint b: b_rows
    on a.id == b.id
relationship b_to_c:
    endpoint b: b_rows
    endpoint c: c_rows
    on b.c_id == c.id
relationship many:
    endpoint a: a_rows
    endpoint d: d_rows
    on a.b_id == d.match_id
relationship self_b:
    endpoint child: b_rows
    endpoint parent: b_rows
    on child.id == parent.id
query inner_one:
    from a_rows
    inner join b_rows as b:
        from a_rows
        via one_to_one: a -> b
    select:
        id
query left_one:
    from a_rows
    left join b_rows as b:
        from a_rows
        via one_to_one: a -> b
    select:
        id
query inner_many:
    from a_rows
    inner join d_rows as d:
        from a_rows
        via many: a -> d
    select:
        id
query multi_left:
    from a_rows
    left join c_rows as c:
        from a_rows
        via one_to_one: a -> b
        via b_to_c: b -> c
    select:
        id
query branching:
    from a_rows
    inner join b_rows as b:
        from a_rows
        via one_to_one: a -> b
    inner join d_rows as d:
        from a_rows
        via many: a -> d
    select:
        id
query self_join:
    from b_rows
    left join b_rows as parent:
        from b_rows
        via self_b: child -> parent
    select:
        id
query prior_null_inner:
    from a_rows
    left join b_rows as b:
        from a_rows
        via one_to_one: a -> b
    inner join c_rows as c:
        from b
        via b_to_c: b -> c
    select:
        id
query blocked_region:
    from a_rows
    inner join b_rows as b:
        from a_rows
        via one_to_one: a -> b
    inner join c_rows as c:
        from a_rows
    select:
        id
query unrelated:
    from d_rows
    select:
        rid
"""


@dataclass(frozen=True, slots=True)
class _Built:
    semantic: Any
    plan: Any
    base_properties: relational.ProjectIRRelationalPropertyStage
    relationships: project_relationships.ProjectRelationshipSet
    guarantees: guarantees.ProjectRelationshipMatchGuaranteeSet
    use_set: relationship_uses.ProjectRelationshipUseSet
    stage: joins.ProjectIRJoinRegionStage


def _build(root: Path, source: str = "") -> _Built:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(source or _source(), encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    semantic = build_empty_project_semantic_result(parsed)
    keys = project_row_keys.build_project_row_keys(semantic)
    value_fds = project_value_fds.build_project_value_fds(keys)
    semantic_facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert semantic_facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=semantic_facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = project_grain.build_project_grain_origins(value_fds, evaluation)
    analysis = build_project_ir_analysis_bundle(verify_project_ir_stage(evaluation))
    base_properties = relational.build_project_ir_relational_property_stage(
        origins, analysis
    )
    relationships = project_relationships.build_project_relationships(semantic)
    condition_set = conditions.build_project_relationship_conditions(relationships)
    guarantee_set = guarantees.build_project_relationship_match_guarantees(
        condition_set, base_properties
    )
    index = paths.build_project_relationship_join_shape_index(guarantee_set)
    use_set = relationship_uses.build_project_relationship_uses(relationships, index)
    stage = joins.build_project_ir_join_region(
        base_plan=plan,
        base_relational=base_properties,
        uses=use_set,
        allocation=plan.ending_allocation,
    )
    return _Built(
        semantic=semantic,
        plan=plan,
        base_properties=base_properties,
        relationships=relationships,
        guarantees=guarantee_set,
        use_set=use_set,
        stage=stage,
    )


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> _Built:
    return _build(tmp_path_factory.mktemp("p62s11"))


def _region(built: _Built, name: str) -> joins.ProjectIRJoinRegion:
    matches = tuple(
        item
        for item in built.stage.regions
        if item.ledger.owner.definition.name == name
    )
    assert len(matches) == 1
    return matches[0]


def _properties(
    built: _Built, name: str
) -> tuple[joins.ProjectIRJoinOutputProperties, ...]:
    return tuple(
        item
        for item in built.stage.properties.outputs
        if item.join.use.owner.definition.name == name
    )


def _direction(
    built: _Built, name: str, source_role: str
) -> guarantees.ProjectDirectionalRelationshipMatchGuarantee:
    identity = next(
        subject.occurrence.identity
        for subject in built.relationships.subjects
        if subject.occurrence.name == name
    )
    matches = tuple(
        item
        for item in built.guarantees.subjects
        if type(item) is guarantees.ProjectDirectionalRelationshipMatchGuarantee
        and item.direction.declaration == identity
        and item.direction.source.authored_role == source_role
    )
    assert len(matches) == 1
    return matches[0]


def _positive(
    built: _Built,
    direction: guarantees.ProjectDirectionalRelationshipMatchGuarantee,
    name: str,
) -> guarantees.ProjectDirectionalRelationshipMatchGuarantee:
    condition = next(
        item
        for item in built.guarantees.conditions.conditions
        if item.relationship.occurrence.name == name
    )
    assert type(condition) is conditions.ProjectConcreteRelationshipCondition
    source_position = direction.direction.source.identity.endpoint_position
    target_position = direction.direction.target.identity.endpoint_position
    source_ref = (
        condition.correspondences[0].endpoint_zero
        if source_position == 0
        else condition.correspondences[0].endpoint_one
    )
    target_ref = (
        condition.correspondences[0].endpoint_zero
        if target_position == 0
        else condition.correspondences[0].endpoint_one
    )
    coverage = guarantees.ProjectReferentialCoverageEvidence(
        direction=direction.direction,
        correspondences=condition.correspondences,
        source_scope=source_ref.constraint_scope,
        target_scope=target_ref.constraint_scope,
        policy=guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE,
        origin=guarantees.ProjectReferentialCoverageOrigin.EXPLICIT_RULE_BOUNDARY,
        trust=guarantees.ProjectReferentialCoverageTrust.TRUSTED,
        authority=guarantees.ProjectExplicitCoverageAuthority(),
    )
    return guarantees.derive_directional_match_guarantee(
        direction.direction,
        condition,
        direction.source_output,
        direction.target_output,
        coverage,
    )


def _stage_with_positive(
    built: _Built,
    replacements: dict[int, guarantees.ProjectDirectionalRelationshipMatchGuarantee],
) -> joins.ProjectIRJoinRegionStage:
    updated = replace(
        built.guarantees,
        subjects=tuple(
            replacements.get(id(subject), subject)
            for subject in built.guarantees.subjects
        ),
    )
    index = paths.build_project_relationship_join_shape_index(updated)
    use_set = relationship_uses.build_project_relationship_uses(
        built.relationships, index
    )
    return joins.build_project_ir_join_region(
        base_plan=built.plan,
        base_relational=built.base_properties,
        uses=use_set,
        allocation=built.plan.ending_allocation,
    )


def test_binary_topology_allocation_multihop_and_accumulated_left(
    built: _Built,
) -> None:
    direct = cast(joins.ProjectIRConcreteJoinRegion, _region(built, "inner_one"))
    multi = cast(joins.ProjectIRConcreteJoinRegion, _region(built, "multi_left"))
    branching = cast(joins.ProjectIRConcreteJoinRegion, _region(built, "branching"))
    assert len(direct.joins) == 1 and len(multi.joins) == 2
    assert all(
        tuple(slot.input_ordinal for slot in item.input_slots) == (0, 1)
        and len(item.input_uses) == 2
        for item in (*direct.joins, *multi.joins, *branching.joins)
    )
    assert multi.joins[1].left_input.output is multi.joins[0].output
    assert branching.joins[1].left_input.output is branching.joins[0].output
    named_source = branching.ledger.bindings[0].output
    assert named_source is not None
    assert branching.joins[1].left_input.output is not named_source.output
    assert (
        branching.joins[1].matches[0].left.introduction_use
        is (branching.joins[0].input_uses[0])
    )
    assert built.stage.starting_allocation is built.plan.ending_allocation
    count = len(built.stage.structural.nodes)
    assert built.stage.ending_allocation.next_plan_node_position == (
        built.stage.starting_allocation.next_plan_node_position + count
    )
    assert built.stage.ending_allocation.next_output_value_position == (
        built.stage.starting_allocation.next_output_value_position + count
    )
    assert built.stage.ending_allocation.next_input_slot_position == (
        built.stage.starting_allocation.next_input_slot_position + 2 * count
    )


def test_non_concrete_ledger_is_zero_allocation_without_prefix_leak(
    built: _Built,
) -> None:
    region = cast(
        joins.ProjectIRNonConcreteJoinRegion, _region(built, "blocked_region")
    )
    assert region.ending_allocation is region.starting_allocation
    assert region.state is relationship_uses.ProjectJoinUseState.UNKNOWN
    assert region.blockers
    assert not any(
        item.join.use.owner.definition.name == "blocked_region"
        for item in built.stage.properties.outputs
    )
    assert any(
        fragment.semantic_facts.owner.definition.name == "unrelated"
        for fragment in built.plan.concrete_fragments
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
    assert final_fields[4].nulling_joins == (first_ref, second_ref)
    assert all(
        item.effective_nullability is ProjectRowFieldNullability.NULLABLE
        for item in final_fields[2:]
    )
    assert type(multi[0].null_extension) is ProjectIRProvidedNullExtension
    assert type(multi[1].null_extension) is ProjectIRProvidedNullExtension

    self_output = _properties(built, "self_join")[0].join.output.row_shape
    left_id, left_c, right_id, right_c = self_output.fields
    assert left_id.evidence is right_id.evidence
    assert left_c.evidence is right_c.evidence
    assert left_id.introduction_use is not right_id.introduction_use


def test_actual_effects_use_direction_and_prior_null_source(built: _Built) -> None:
    inner = _properties(built, "inner_one")[0].join
    many = _properties(built, "inner_many")[0].join
    assert (
        inner.fanout
        is paths.ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY
    )
    assert inner.survival is joins.ProjectIRJoinRowSurvivalEffect.MAY_DROP_LEFT_ROWS
    assert many.fanout is paths.ProjectRelationshipFanoutEffect.MAY_MULTIPLY

    one = _direction(built, "one_to_one", "a")
    bc = _direction(built, "b_to_c", "b")
    positive_one = _positive(built, one, "one_to_one")
    positive_bc = _positive(built, bc, "b_to_c")
    stage = _stage_with_positive(
        built,
        {id(one): positive_one, id(bc): positive_bc},
    )
    by_owner = {
        item.join.use.owner.definition.name: [] for item in stage.properties.outputs
    }
    for item in stage.properties.outputs:
        by_owner[item.join.use.owner.definition.name].append(item)
    positive_inner = by_owner["inner_one"][0].join
    assert positive_inner.survival is (
        joins.ProjectIRJoinRowSurvivalEffect.GUARANTEES_LEFT_SURVIVAL
    )
    positive_left = by_owner["left_one"][0]
    assert positive_left.join.null_extension is (
        joins.ProjectIRJoinNullExtensionEffect.NO_NEW_NULL_EXTENSION
    )
    assert (
        positive_left.join.outer_join_barrier is joins.ProjectIROuterJoinBarrier.PRESENT
    )
    assert positive_left.null_extension.availability is (
        ProjectIRPropertyAvailability.NOT_APPLICABLE
    )
    prior_stage = _stage_with_positive(built, {id(bc): positive_bc})
    prior_output = next(
        item
        for item in prior_stage.properties.outputs
        if item.join.use.owner.definition.name == "prior_null_inner"
        and item.join.use.identity.join_position == 1
    )
    prior = prior_output.join
    assert prior.survival is joins.ProjectIRJoinRowSurvivalEffect.MAY_DROP_LEFT_ROWS
    assert type(prior_output.null_extension) is ProjectIRProvidedNullExtension
    assert any(field.nulling_joins for field in prior_output.null_extension.fields)
    prior_left_stage = _stage_with_positive(built, {id(bc): positive_bc})
    prior_left = _properties(replace(built, stage=prior_left_stage), "multi_left")[-1]
    first_ref = _properties(replace(built, stage=prior_left_stage), "multi_left")[
        0
    ].join.node.ref
    assert prior_left.join.output.row_shape.fields[-1].nulling_joins == (
        first_ref,
        prior_left.join.node.ref,
    )


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
    reverse = _direction(built, "one_to_one", "b")
    reverse_fact = next(
        fact for fact in left.fds if fact.supports == (reverse, left_output.join)
    )
    assert tuple(
        member.field_position
        for item in reverse_fact.dependents
        for member in item.members
    ) == (0, 1)
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
    id: Int nullable
    unique left_key on id
shape RightRow:
    id: Int nullable
    value: Int nullable
    unique right_key on id
source left_rows: LeftRow is postgres.table("left_rows")
source right_rows: RightRow is postgres.table("right_rows")
relationship match_rows:
    endpoint left: left_rows
    endpoint right: right_rows
    on left.id == right.id
query recomputed_keys:
    from left_rows
    inner join right_rows as right:
        from left_rows
        via match_rows: left -> right
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
    id: Int not null
source left_rows: Row is postgres.table("left_rows")
source right_rows: Row is postgres.table("right_rows")
query global_left:
    from left_rows
    select:
        total = count()
query global_right:
    from right_rows
    select:
        total = count()
relationship globals:
    endpoint left: global_left
    endpoint right: global_right
    on left.total == right.total
query global_join:
    from global_left
    inner join global_right as right:
        from global_left
        via globals: left -> right
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
    id: Int not null
    unique row_key on id
source factor_rows: Row is postgres.table("factor_rows")
source right_rows: Row is postgres.table("right_rows")
query global_rows:
    from factor_rows
    select:
        total = count()
relationship factor_to_global:
    endpoint factor: factor_rows
    endpoint global: global_rows
    on factor.id == global.total
relationship global_to_right:
    endpoint global: global_rows
    endpoint right: right_rows
    on global.total == right.id
query global_branch:
    from factor_rows
    inner join global_rows as global:
        from factor_rows
        via factor_to_global: factor -> global
    inner join right_rows as right:
        from global
        via global_to_right: global -> right
    select:
        id
"""
    outputs = _properties(_build(tmp_path / "global-branch", source), "global_branch")
    second = outputs[1].relational.grain
    assert len(second.active) == 2
    assert second.dependencies == ()


def test_join_carriers_reject_forged_effect_topology_and_match_evidence(
    built: _Built,
) -> None:
    direct = _properties(built, "inner_one")[0].join
    with pytest.raises((TypeError, ValueError), match="init=False"):
        replace(
            direct,
            survival=joins.ProjectIRJoinRowSurvivalEffect.GUARANTEES_LEFT_SURVIVAL,
        )
    with pytest.raises(ValueError, match="exact fields"):
        replace(
            direct,
            matches=(
                replace(
                    direct.matches[0],
                    left=direct.output.row_shape.fields[1],
                ),
            ),
        )
    multi = cast(joins.ProjectIRConcreteJoinRegion, _region(built, "multi_left"))
    with pytest.raises(ValueError, match="canonical use/step order"):
        replace(multi, joins=multi.joins[::-1])
    with pytest.raises(ValueError, match="exact"):
        replace(built.stage.structural, uses=built.stage.structural.uses[::-1])


def test_join_fd_index_preserves_arbitrary_width_python_int_masks(
    tmp_path: Path,
) -> None:
    left_fields = "".join(f"    a{position}: Int not null\n" for position in range(72))
    right_fields = "".join(f"    b{position}: Int not null\n" for position in range(72))
    source = (
        "shape LeftRow:\n"
        + left_fields
        + "    unique left_key on a0\n"
        + "shape RightRow:\n"
        + right_fields
        + "    unique right_key on b0\n"
        + 'source left_rows: LeftRow is postgres.table("left_rows")\n'
        + 'source right_rows: RightRow is postgres.table("right_rows")\n'
        + "relationship wide:\n"
        + "    endpoint left: left_rows\n"
        + "    endpoint right: right_rows\n"
        + "    on left.a0 == right.b0\n"
        + "query wide_join:\n"
        + "    from left_rows\n"
        + "    inner join right_rows as right:\n"
        + "        from left_rows\n"
        + "        via wide: left -> right\n"
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
    assert all(
        fact.state.reason.value == "authored_join_deferred"
        for environment in built.semantic.module_semantic_facts.environments
        for fact in environment.relation_facts
        if getattr(fact.owner.definition, "join_clauses", ())
    )
    assert joins.__all__ == ()
    assert not hasattr(built.plan, "join_regions")
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
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "b26e394e5f8238f2c69d86844fb15f7bcb52362b",
        "fcbd2b5cf661ae9b8793371c9ae750768fe164e3",
        "33559281666",
        "A3/M9/D0",
        "ProjectIRJoinInputUseOccurrence",
        "Phase 62 Slice 12 = NEXT / NOT IMPLEMENTED",
        "Add Phase 62 binary Project IR joins",
    ):
        assert evidence in normalized
