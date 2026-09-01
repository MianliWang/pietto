from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from pietto._project import check as project_check
from pietto._project import project_grain
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_relationship_conditions as conditions
from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project import project_relationship_paths as paths
from pietto._project import project_relationships
from pietto._project import project_row_keys
from pietto._project import project_value_fds
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_ir import ProjectIRSnapshotScope
from pietto._project.project_ir_composition import build_project_ir_project_plan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_evaluation_context import (
    build_project_ir_evaluation_context_stage,
)
from pietto._project.project_ir_verification import (
    build_project_ir_analysis_bundle,
    verify_project_ir_stage,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice9-explicit-relationship-paths-fanout-survival-null-effects-join-shape-analysis-v1.md"
)


def _source() -> str:
    return """shape ARow:
    b_id: Int not null
source a_rows: ARow is postgres.table("a")
shape BRow:
    a_id: Int nullable
    c_id: Int not null
    unique a_key on a_id
source b_rows: BRow is postgres.table("b")
shape CRow:
    id: Int not null
    unique id_key on id
source c_rows: CRow is postgres.table("c")
shape DRow:
    id: Int not null
source d_rows: DRow is postgres.table("d")
relationship ab_one:
    endpoint a: a_rows
    endpoint b: b_rows
    on a.b_id == b.a_id
relationship ab_two:
    endpoint a: a_rows
    endpoint b: b_rows
    on a.b_id == b.a_id
relationship bc:
    endpoint b: b_rows
    endpoint c: c_rows
    on b.c_id == c.id
relationship bd_many:
    endpoint b: b_rows
    endpoint d: d_rows
    on b.c_id == d.id
relationship self_b:
    endpoint child: b_rows
    endpoint parent: b_rows
    on child.a_id == parent.a_id
relationship absent_condition:
    endpoint c: c_rows
    endpoint d: d_rows
"""


def _build(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(_source(), encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    semantic = build_empty_project_semantic_result(parsed)
    keys = project_row_keys.build_project_row_keys(semantic)
    fds = project_value_fds.build_project_value_fds(keys)
    facts = semantic.module_semantic_facts
    attribution = semantic.module_attribution_facts
    assert facts is not None and attribution is not None
    plan = build_project_ir_project_plan(
        semantic_facts=facts,
        attribution=attribution,
        allocation=ProjectIRAllocationState(scope=ProjectIRSnapshotScope()),
    )
    evaluation = build_project_ir_evaluation_context_stage(plan)
    origins = project_grain.build_project_grain_origins(fds, evaluation)
    analyses = build_project_ir_analysis_bundle(verify_project_ir_stage(evaluation))
    properties = relational.build_project_ir_relational_property_stage(
        origins, analyses
    )
    relationship_set = project_relationships.build_project_relationships(semantic)
    condition_set = conditions.build_project_relationship_conditions(relationship_set)
    guarantee_set = guarantees.build_project_relationship_match_guarantees(
        condition_set, properties
    )
    return guarantee_set, paths.build_project_relationship_join_shape_index(
        guarantee_set
    )


def _direction(result, name: str, source_role: str):
    identity = next(
        subject.occurrence.identity
        for subject in result.conditions.relationships.subjects
        if subject.occurrence.name == name
    )
    matches = tuple(
        item
        for item in result.subjects
        if type(item) is guarantees.ProjectDirectionalRelationshipMatchGuarantee
        and item.direction.declaration == identity
        and item.direction.source.authored_role == source_role
    )
    assert len(matches) == 1
    return matches[0]


def _positive(result, direction, name: str):
    condition = next(
        item
        for item in result.conditions.conditions
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


def _index_with(result, replacements):
    subjects = tuple(
        replacements.get(id(subject), subject) for subject in result.subjects
    )
    updated = replace(result, subjects=subjects)
    return paths.build_project_relationship_join_shape_index(updated)


def test_direct_index_absent_unique_ambiguous_parallel_and_self(tmp_path: Path) -> None:
    result, index = _build(tmp_path)
    ab = _direction(result, "ab_one", "a")
    bc = _direction(result, "bc", "b")
    assert index.resolve_direct(ab.source_output, ab.target_output).status is (
        paths.ProjectDirectRelationshipCandidateStatus.AMBIGUOUS
    )
    assert index.resolve_direct(bc.source_output, bc.target_output).status is (
        paths.ProjectDirectRelationshipCandidateStatus.CONCRETE
    )
    assert index.resolve_direct(bc.target_output, ab.source_output).status is (
        paths.ProjectDirectRelationshipCandidateStatus.ABSENT
    )
    self_b = _direction(result, "self_b", "child")
    assert index.resolve_direct(self_b.source_output, self_b.target_output).status is (
        paths.ProjectDirectRelationshipCandidateStatus.AMBIGUOUS
    )
    assert index.non_concrete


def test_explicit_paths_are_ordered_contiguous_and_never_auto_selected(
    tmp_path: Path,
) -> None:
    result, index = _build(tmp_path)
    ab = _direction(result, "ab_one", "a")
    bc = _direction(result, "bc", "b")
    explicit = paths.build_explicit_relationship_path(index, (ab, bc))
    assert tuple(step.position for step in explicit.steps) == (0, 1)
    assert explicit.steps[0].guarantee is ab and explicit.steps[1].guarantee is bc
    with pytest.raises(ValueError, match="contiguous"):
        paths.build_explicit_relationship_path(index, (bc, ab))
    self_b = _direction(result, "self_b", "child")
    repeated = paths.build_explicit_relationship_path(index, (self_b, self_b))
    assert tuple(step.position for step in repeated.steps) == (0, 1)
    assert not hasattr(index, "find_path")


def test_zero_minimum_effects_are_independent_and_nulling_propagates(
    tmp_path: Path,
) -> None:
    result, index = _build(tmp_path)
    ab = _direction(result, "ab_one", "a")
    bd = _direction(result, "bd_many", "b")
    analysis = paths.analyze_relationship_path(
        paths.build_explicit_relationship_path(index, (ab, bd))
    )
    assert analysis.fanout is paths.ProjectRelationshipFanoutEffect.MAY_MULTIPLY
    assert analysis.multiplying_hops == (analysis.path.steps[1],)
    assert analysis.inner_survival is (
        paths.ProjectRelationshipInnerSurvivalEffect.MAY_DROP_SOURCE_ROWS
    )
    assert analysis.survival_risk_hops == analysis.path.steps
    assert (
        analysis.left_nulling
        is paths.ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
    )
    assert analysis.local_nulling_roots == analysis.path.steps
    assert analysis.propagated_null_positions == (0, 1)
    assert analysis.hops[0].fanout is (
        paths.ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY
    )
    with pytest.raises(ValueError, match="complete exact evidence"):
        replace(analysis, multiplying_hops=())
    with pytest.raises(ValueError, match="complete exact evidence"):
        replace(analysis, propagated_null_positions=(0,))
    with pytest.raises(ValueError, match="complete exact evidence"):
        replace(
            analysis,
            fanout=paths.ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY,
        )


def test_positive_minimum_variants_and_early_late_null_propagation(
    tmp_path: Path,
) -> None:
    result, _index = _build(tmp_path)
    ab = _direction(result, "ab_one", "a")
    bd = _direction(result, "bd_many", "b")
    positive_ab = _positive(result, ab, "ab_one")
    positive_bd = _positive(result, bd, "bd_many")

    early_index = _index_with(result, {id(bd): positive_bd})
    early = paths.analyze_relationship_path(
        paths.build_explicit_relationship_path(early_index, (ab, positive_bd))
    )
    assert early.local_nulling_roots == (early.path.steps[0],)
    assert early.propagated_null_positions == (0, 1)

    late_index = _index_with(result, {id(ab): positive_ab})
    late = paths.analyze_relationship_path(
        paths.build_explicit_relationship_path(late_index, (positive_ab, bd))
    )
    assert late.local_nulling_roots == (late.path.steps[1],)
    assert late.propagated_null_positions == (1,)

    all_positive_index = _index_with(result, {id(ab): positive_ab, id(bd): positive_bd})
    all_positive = paths.analyze_relationship_path(
        paths.build_explicit_relationship_path(
            all_positive_index, (positive_ab, positive_bd)
        )
    )
    assert all_positive.inner_survival is (
        paths.ProjectRelationshipInnerSurvivalEffect.GUARANTEES_SOURCE_SURVIVAL
    )
    assert all_positive.left_nulling is (
        paths.ProjectRelationshipLeftNullingEffect.NO_MISSING_MATCH_NULLING
    )
    assert all_positive.fanout is paths.ProjectRelationshipFanoutEffect.MAY_MULTIPLY


def test_closed_vocabulary_private_boundaries_and_contract() -> None:
    assert tuple(paths.ProjectRelationshipFanoutEffect) == (
        paths.ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY,
        paths.ProjectRelationshipFanoutEffect.MAY_MULTIPLY,
        paths.ProjectRelationshipFanoutEffect.UNKNOWN,
        paths.ProjectRelationshipFanoutEffect.CONFLICT,
    )
    assert paths.__all__ == ()
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "6dd7dec031bb23d4d675ecf03542186b6df5f371",
        "ec3c885527968f4fad65b619bc4fccd5253392dd",
        "33502717286",
        "A3/M5/D0",
        "MAY_MULTIPLY != proof that multiplication occurs",
        "ZERO_ALLOWED != proof that a row is actually unmatched",
        "relationship declaration != relationship direction != path step",
        "Phase 62 Slice 10 = NEXT / NOT IMPLEMENTED",
        "Add Phase 62 relationship path and fanout analysis",
    ):
        assert evidence in normalized
