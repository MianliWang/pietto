from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from pietto._project import check as project_check
from pietto._project import project_grain
from pietto._project import project_ir_relational_properties as relational
from pietto._project import project_relationship_conditions as conditions
from pietto._project import project_relationship_match_guarantees as guarantees
from pietto._project import project_relationships
from pietto._project import project_row_keys
from pietto._project import project_value_fds
from pietto._project.model import (
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
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
from pietto.semantic.model import SemanticModel

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice8-referential-coverage-match-simple-full-directional-match-guarantees-v1.md"
)


def _source() -> str:
    return """shape OrderRow:
    customer_id: Int nullable
    tenant_id: Int not null
    composite_id: Int not null
source orders: OrderRow is postgres.table("orders")
shape CustomerRow:
    id: Int not null
    nullable_code: Int nullable
    unique id_key on id
    unique nullable_key on nullable_code
source customers: CustomerRow is postgres.table("customers")
shape CompositeRow:
    tenant_id: Int not null
    id: Int not null
    extra: Int nullable
    unique composite_key on tenant_id, id
source composites: CompositeRow is postgres.table("composites")
relationship strict_target:
    endpoint order: orders
    endpoint customer: customers
    on order.customer_id == customer.id
relationship lax_target:
    endpoint order: orders
    endpoint customer: customers
    on order.customer_id == customer.nullable_code
relationship composite_target:
    endpoint order: orders
    endpoint target: composites
    on order.tenant_id == target.tenant_id and order.composite_id == target.id
relationship composite_superset:
    endpoint order: orders
    endpoint target: composites
    on order.tenant_id == target.tenant_id and order.composite_id == target.id and order.customer_id == target.extra
relationship composite_partial:
    endpoint order: orders
    endpoint target: composites
    on order.tenant_id == target.tenant_id
relationship repeated_pair:
    endpoint order: orders
    endpoint customer: customers
    on order.customer_id == customer.id
relationship self_link:
    endpoint child: customers
    endpoint parent: customers
    on child.id == parent.id
relationship no_condition:
    endpoint order: orders
    endpoint customer: customers
"""


def _semantic(root: Path) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(_source(), encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok, parsed.diagnostics
    return build_empty_project_semantic_result(parsed)


def _build(root: Path):
    semantic = _semantic(root)
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
    relationships = project_relationships.build_project_relationships(semantic)
    condition_set = conditions.build_project_relationship_conditions(relationships)
    result = guarantees.build_project_relationship_match_guarantees(
        condition_set, properties
    )
    return result


def _directions(result, relationship_name: str):
    identity = next(
        subject.occurrence.identity
        for subject in result.conditions.relationships.subjects
        if subject.occurrence.name == relationship_name
    )
    return tuple(
        subject
        for subject in result.subjects
        if type(subject) is guarantees.ProjectDirectionalRelationshipMatchGuarantee
        and subject.direction.declaration == identity
    )


def _direction(result, relationship_name: str, source_role: str):
    matches = tuple(
        item
        for item in _directions(result, relationship_name)
        if item.direction.source.authored_role == source_role
    )
    assert len(matches) == 1
    return matches[0]


def test_directions_are_occurrence_safe_complete_and_deterministic(
    tmp_path: Path,
) -> None:
    result = _build(tmp_path)
    strict = _directions(result, "strict_target")
    assert len(strict) == 2
    assert strict[0].direction != strict[1].direction
    assert strict[0].direction.source.identity.endpoint_position == 0
    assert strict[1].direction.source.identity.endpoint_position == 1
    self_directions = _directions(result, "self_link")
    assert len(self_directions) == 2
    assert self_directions[0].direction != self_directions[1].direction
    repeated = _directions(result, "repeated_pair")
    assert repeated[0].direction.declaration != strict[0].direction.declaration
    absent = tuple(
        item
        for item in result.subjects
        if type(item) is guarantees.ProjectNonConcreteMatchGuaranteeSubject
    )
    assert len(absent) == 1


def test_target_strict_lax_composite_and_superset_keys_prove_at_most_one(
    tmp_path: Path,
) -> None:
    result = _build(tmp_path)
    for relationship_name in (
        "strict_target",
        "lax_target",
        "composite_target",
        "composite_superset",
    ):
        direction = _direction(result, relationship_name, "order")
        assert (
            direction.maximum is guarantees.ProjectRelationshipMaximumBound.AT_MOST_ONE
        )
        assert type(direction.maximum_evidence) is guarantees.ProjectAtMostOneEvidence
        assert direction.maximum_evidence.target_keys
        assert (
            direction.minimum is guarantees.ProjectRelationshipMinimumBound.ZERO_ALLOWED
        )
        assert type(direction.coverage) is guarantees.ProjectAbsentReferentialCoverage
    lax = _direction(result, "lax_target", "order")
    assert type(lax.maximum_evidence) is guarantees.ProjectAtMostOneEvidence
    assert lax.maximum_evidence.target_keys[0].strength is (
        project_row_keys.ProjectRowUniquenessStrength.LAX
    )


def test_partial_or_wrong_side_authority_does_not_prove_at_most_one(
    tmp_path: Path,
) -> None:
    result = _build(tmp_path)
    partial = _direction(result, "composite_partial", "order")
    assert partial.maximum is (
        guarantees.ProjectRelationshipMaximumBound.UNBOUNDED_BY_ONE
    )
    reverse = _direction(result, "strict_target", "customer")
    assert reverse.maximum is (
        guarantees.ProjectRelationshipMaximumBound.UNBOUNDED_BY_ONE
    )
    assert partial.maximum_evidence is (
        guarantees.ProjectMatchGuaranteeFallbackReason.TARGET_KEY_NOT_PROVEN
    )


def test_match_simple_and_full_null_applicability_are_distinct() -> None:
    simple = guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE
    full = guarantees.ProjectReferentialMatchPolicy.MATCH_FULL
    assert guarantees.classify_match_applicability(simple, (False, False)) is (
        guarantees.ProjectMatchApplicability.REQUIRES_MATCH
    )
    assert guarantees.classify_match_applicability(simple, (True, False)) is (
        guarantees.ProjectMatchApplicability.NOT_APPLICABLE_SOURCE_NULL
    )
    assert guarantees.classify_match_applicability(full, (True, True)) is (
        guarantees.ProjectMatchApplicability.NULL_REFERENCE_ACCEPTED
    )
    assert guarantees.classify_match_applicability(full, (True, False)) is (
        guarantees.ProjectMatchApplicability.MIXED_NULL_VIOLATION
    )
    assert guarantees.classify_match_applicability(full, (False, False)) is (
        guarantees.ProjectMatchApplicability.REQUIRES_MATCH
    )


def test_explicit_coverage_and_non_null_source_are_both_required_for_minimum(
    tmp_path: Path,
) -> None:
    result = _build(tmp_path)
    canonical = _direction(result, "composite_target", "order")
    condition = next(
        item
        for item in result.conditions.conditions
        if item.relationship.occurrence.name == "composite_target"
    )
    assert type(condition) is conditions.ProjectConcreteRelationshipCondition
    source_reference = condition.correspondences[0].endpoint_zero
    target_reference = condition.correspondences[0].endpoint_one
    coverage = guarantees.ProjectReferentialCoverageEvidence(
        direction=canonical.direction,
        correspondences=condition.correspondences,
        source_scope=source_reference.constraint_scope,
        target_scope=target_reference.constraint_scope,
        policy=guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE,
        origin=guarantees.ProjectReferentialCoverageOrigin.EXPLICIT_RULE_BOUNDARY,
        trust=guarantees.ProjectReferentialCoverageTrust.TRUSTED,
        authority=guarantees.ProjectExplicitCoverageAuthority(),
    )
    proven = guarantees.derive_directional_match_guarantee(
        canonical.direction,
        condition,
        canonical.source_output,
        canonical.target_output,
        coverage,
    )
    assert proven.minimum is guarantees.ProjectRelationshipMinimumBound.AT_LEAST_ONE
    nullable = _direction(result, "strict_target", "order")
    nullable_condition = next(
        item
        for item in result.conditions.conditions
        if item.relationship.occurrence.name == "strict_target"
    )
    assert type(nullable_condition) is conditions.ProjectConcreteRelationshipCondition
    nullable_coverage = guarantees.ProjectReferentialCoverageEvidence(
        direction=nullable.direction,
        correspondences=nullable_condition.correspondences,
        source_scope=nullable_condition.correspondences[
            0
        ].endpoint_zero.constraint_scope,
        target_scope=nullable_condition.correspondences[
            0
        ].endpoint_one.constraint_scope,
        policy=guarantees.ProjectReferentialMatchPolicy.MATCH_FULL,
        origin=guarantees.ProjectReferentialCoverageOrigin.EXPLICIT_RULE_BOUNDARY,
        trust=guarantees.ProjectReferentialCoverageTrust.TRUSTED,
        authority=guarantees.ProjectExplicitCoverageAuthority(),
    )
    not_proven = guarantees.derive_directional_match_guarantee(
        nullable.direction,
        nullable_condition,
        nullable.source_output,
        nullable.target_output,
        nullable_coverage,
    )
    assert not_proven.minimum is guarantees.ProjectRelationshipMinimumBound.ZERO_ALLOWED


def test_private_closed_vocabulary_and_public_boundaries() -> None:
    assert tuple(guarantees.ProjectRelationshipMinimumBound) == (
        guarantees.ProjectRelationshipMinimumBound.ZERO_ALLOWED,
        guarantees.ProjectRelationshipMinimumBound.AT_LEAST_ONE,
    )
    assert tuple(guarantees.ProjectReferentialMatchPolicy) == (
        guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE,
        guarantees.ProjectReferentialMatchPolicy.MATCH_FULL,
    )
    assert guarantees.__all__ == ()
    assert "match_guarantees" not in {
        item.name for item in fields(ProjectSemanticResult)
    }
    assert "match_guarantees" not in {item.name for item in fields(SemanticModel)}


def test_carriers_reject_detached_bounds_correspondences_and_incomplete_ledger(
    tmp_path: Path,
) -> None:
    result = _build(tmp_path)
    direction = _direction(result, "strict_target", "order")
    with pytest.raises(ValueError, match="AT_MOST_ONE bound"):
        replace(
            direction,
            maximum_evidence=guarantees.ProjectMatchGuaranteeFallbackReason.TARGET_KEY_NOT_PROVEN,
        )
    with pytest.raises(ValueError, match="AT_MOST_ZERO"):
        replace(
            direction,
            maximum=guarantees.ProjectRelationshipMaximumBound.AT_MOST_ZERO,
            maximum_evidence=guarantees.ProjectMatchGuaranteeFallbackReason.TARGET_KEY_NOT_PROVEN,
        )
    with pytest.raises(ValueError, match="complete and ordered"):
        replace(result, subjects=result.subjects[:-1])

    composite = _direction(result, "composite_target", "order")
    composite_condition = next(
        item
        for item in result.conditions.conditions
        if item.relationship.occurrence.name == "composite_target"
    )
    strict_condition = next(
        item
        for item in result.conditions.conditions
        if item.relationship.occurrence.name == "strict_target"
    )
    assert type(composite_condition) is conditions.ProjectConcreteRelationshipCondition
    assert type(strict_condition) is conditions.ProjectConcreteRelationshipCondition
    with pytest.raises(ValueError, match="belong to its direction"):
        guarantees.ProjectReferentialCoverageEvidence(
            direction=composite.direction,
            correspondences=strict_condition.correspondences,
            source_scope=composite_condition.correspondences[
                0
            ].endpoint_zero.constraint_scope,
            target_scope=composite_condition.correspondences[
                0
            ].endpoint_one.constraint_scope,
            policy=guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE,
            origin=guarantees.ProjectReferentialCoverageOrigin.EXPLICIT_RULE_BOUNDARY,
            trust=guarantees.ProjectReferentialCoverageTrust.TRUSTED,
            authority=guarantees.ProjectExplicitCoverageAuthority(),
        )

    partial_coverage = guarantees.ProjectReferentialCoverageEvidence(
        direction=composite.direction,
        correspondences=composite_condition.correspondences[:1],
        source_scope=composite_condition.correspondences[
            0
        ].endpoint_zero.constraint_scope,
        target_scope=composite_condition.correspondences[
            0
        ].endpoint_one.constraint_scope,
        policy=guarantees.ProjectReferentialMatchPolicy.MATCH_SIMPLE,
        origin=guarantees.ProjectReferentialCoverageOrigin.EXPLICIT_RULE_BOUNDARY,
        trust=guarantees.ProjectReferentialCoverageTrust.TRUSTED,
        authority=guarantees.ProjectExplicitCoverageAuthority(),
    )
    with pytest.raises(ValueError, match="complete exact condition"):
        guarantees.derive_directional_match_guarantee(
            composite.direction,
            composite_condition,
            composite.source_output,
            composite.target_output,
            partial_coverage,
        )


def test_contract_locks_direction_coverage_bounds_and_handoff() -> None:
    normalized = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "01e3c910ec29f85a4b31e4d1a9dcfa6571d19af1",
        "35f040a8c12d2244d8007dd3b367be67a81344bf",
        "33498869865",
        "A3/M5/D0",
        "UNBOUNDED_BY_ONE != proof that multiple matches exist",
        "target key / FD != referential coverage != existence proof",
        "MATCH_SIMPLE",
        "MATCH_FULL",
        "ZERO_ALLOWED != proof that an unmatched row exists",
        "Phase 62 Slice 9 = NEXT / NOT IMPLEMENTED",
        "Add Phase 62 directional relationship match guarantees",
    ):
        assert evidence in normalized
