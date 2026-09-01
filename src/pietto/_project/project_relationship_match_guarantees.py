"""Private directional relationship match guarantees and coverage boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputCandidateKey,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueClass,
    ProjectIRRelationalPropertyStage,
)
from pietto._project.project_relationship_conditions import (
    ProjectConcreteRelationshipCondition,
    ProjectExactRowOutputConstraintScope,
    ProjectNonConcreteRelationshipCondition,
    ProjectRelationshipConditionSet,
    ProjectRelationshipEqualityCorrespondence,
)
from pietto._project.project_relationships import (
    ProjectConcreteRelationshipSubject,
    ProjectNonConcreteRelationshipSubject,
    ProjectRelationshipDeclarationIdentity,
    ProjectRelationshipEndpointOccurrence,
)

__all__: tuple[str, ...] = ()


class ProjectRelationshipMinimumBound(StrEnum):
    ZERO_ALLOWED = "zero_allowed"
    AT_LEAST_ONE = "at_least_one"


class ProjectRelationshipMaximumBound(StrEnum):
    AT_MOST_ZERO = "at_most_zero"
    AT_MOST_ONE = "at_most_one"
    UNBOUNDED_BY_ONE = "unbounded_by_one"


class ProjectReferentialMatchPolicy(StrEnum):
    MATCH_SIMPLE = "match_simple"
    MATCH_FULL = "match_full"


class ProjectReferentialCoverageState(StrEnum):
    CONCRETE = "concrete"
    NOT_CONSTRUCTIBLE_FROM_CURRENT_AUTHORED_SOURCE = (
        "not_constructible_from_current_authored_source"
    )


class ProjectReferentialCoverageOrigin(StrEnum):
    EXPLICIT_RULE_BOUNDARY = "explicit_rule_boundary"
    AUTHORED_CONTRACT = "authored_contract"
    CATALOG_CONSTRAINT = "catalog_constraint"


class ProjectReferentialCoverageTrust(StrEnum):
    TRUSTED = "trusted"
    UNTRUSTED = "untrusted"
    CONFLICT = "conflict"


class ProjectMatchApplicability(StrEnum):
    REQUIRES_MATCH = "requires_match"
    NULL_REFERENCE_ACCEPTED = "null_reference_accepted"
    NOT_APPLICABLE_SOURCE_NULL = "not_applicable_source_null"
    MIXED_NULL_VIOLATION = "mixed_null_violation"


class ProjectMatchGuaranteeFallbackReason(StrEnum):
    COVERAGE_NOT_CONSTRUCTIBLE = "coverage_not_constructible"
    SOURCE_NULLABILITY_NOT_PROVEN = "source_nullability_not_proven"
    TARGET_KEY_NOT_PROVEN = "target_key_not_proven"
    CONDITION_NOT_PROOF_CAPABLE = "condition_not_proof_capable"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipDirectionIdentity:
    declaration: ProjectRelationshipDeclarationIdentity
    source: ProjectRelationshipEndpointOccurrence = field(repr=False, hash=False)
    target: ProjectRelationshipEndpointOccurrence = field(repr=False, hash=False)

    def __post_init__(self) -> None:
        if type(self.declaration) is not ProjectRelationshipDeclarationIdentity:
            raise TypeError("Relationship direction requires a declaration identity.")
        if (
            type(self.source) is not ProjectRelationshipEndpointOccurrence
            or type(self.target) is not ProjectRelationshipEndpointOccurrence
            or self.source.identity.declaration != self.declaration
            or self.target.identity.declaration != self.declaration
            or self.source is self.target
            or {
                self.source.identity.endpoint_position,
                self.target.identity.endpoint_position,
            }
            != {0, 1}
        ):
            raise ValueError("Direction requires both exact endpoint occurrences.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectExplicitCoverageAuthority:
    """Opaque pure-rule authority; never constructed by the canonical builder."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectReferentialCoverageEvidence:
    direction: ProjectRelationshipDirectionIdentity
    correspondences: tuple[ProjectRelationshipEqualityCorrespondence, ...]
    source_scope: ProjectExactRowOutputConstraintScope
    target_scope: ProjectExactRowOutputConstraintScope
    policy: ProjectReferentialMatchPolicy
    origin: ProjectReferentialCoverageOrigin
    trust: ProjectReferentialCoverageTrust
    authority: ProjectExplicitCoverageAuthority = field(
        repr=False, compare=False, hash=False
    )
    state: ProjectReferentialCoverageState = field(
        default=ProjectReferentialCoverageState.CONCRETE, init=False
    )

    def __post_init__(self) -> None:
        if (
            type(self.direction) is not ProjectRelationshipDirectionIdentity
            or not self.correspondences
            or type(self.source_scope) is not ProjectExactRowOutputConstraintScope
            or type(self.target_scope) is not ProjectExactRowOutputConstraintScope
            or type(self.policy) is not ProjectReferentialMatchPolicy
            or type(self.authority) is not ProjectExplicitCoverageAuthority
            or self.origin
            is not ProjectReferentialCoverageOrigin.EXPLICIT_RULE_BOUNDARY
            or self.trust is not ProjectReferentialCoverageTrust.TRUSTED
        ):
            raise ValueError(
                "Concrete coverage requires exact explicit trusted authority."
            )
        source = self.direction.source.target
        target = self.direction.target.target
        assert source is not None and target is not None
        if self.source_scope.relation.owner is not source.target_occurrence:
            raise ValueError("Coverage source scope must match the exact direction.")
        if self.target_scope.relation.owner is not target.target_occurrence:
            raise ValueError("Coverage target scope must match the exact direction.")
        if any(
            correspondence.identity.base_match.declaration != self.direction.declaration
            for correspondence in self.correspondences
        ):
            raise ValueError("Coverage correspondences must belong to its direction.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectAbsentReferentialCoverage:
    direction: ProjectRelationshipDirectionIdentity
    state: ProjectReferentialCoverageState = (
        ProjectReferentialCoverageState.NOT_CONSTRUCTIBLE_FROM_CURRENT_AUTHORED_SOURCE
    )

    def __post_init__(self) -> None:
        if type(self.direction) is not ProjectRelationshipDirectionIdentity:
            raise TypeError("Absent coverage requires an exact direction.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectAtMostOneEvidence:
    direction: ProjectRelationshipDirectionIdentity
    target_keys: tuple[ProjectIROutputCandidateKey, ...]
    target_matched_classes: tuple[ProjectIROutputValueClass, ...]
    correspondences: tuple[ProjectRelationshipEqualityCorrespondence, ...]

    def __post_init__(self) -> None:
        if (
            not self.target_keys
            or not self.target_matched_classes
            or any(
                correspondence.identity.base_match.declaration
                != self.direction.declaration
                for correspondence in self.correspondences
            )
        ):
            raise ValueError("AT_MOST_ONE requires exact target-key evidence.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectAtLeastOneEvidence:
    coverage: ProjectReferentialCoverageEvidence
    source_matched_classes: tuple[ProjectIROutputValueClass, ...]

    def __post_init__(self) -> None:
        if not self.source_matched_classes or any(
            member.evidence.nullability is not ProjectRowFieldNullability.NON_NULL
            for value_class in self.source_matched_classes
            for member in value_class.members
        ):
            raise ValueError("AT_LEAST_ONE requires exact NON_NULL source evidence.")


type ProjectMinimumBoundEvidence = (
    ProjectAtLeastOneEvidence | ProjectMatchGuaranteeFallbackReason
)
type ProjectMaximumBoundEvidence = (
    ProjectAtMostOneEvidence | ProjectMatchGuaranteeFallbackReason
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectDirectionalRelationshipMatchGuarantee:
    direction: ProjectRelationshipDirectionIdentity
    source_output: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    target_output: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    source_matched_classes: tuple[ProjectIROutputValueClass, ...]
    target_matched_classes: tuple[ProjectIROutputValueClass, ...]
    minimum: ProjectRelationshipMinimumBound
    minimum_evidence: ProjectMinimumBoundEvidence
    maximum: ProjectRelationshipMaximumBound
    maximum_evidence: ProjectMaximumBoundEvidence
    coverage: ProjectReferentialCoverageEvidence | ProjectAbsentReferentialCoverage

    def __post_init__(self) -> None:
        source_target = self.direction.source.target
        target_target = self.direction.target.target
        if (
            type(self.direction) is not ProjectRelationshipDirectionIdentity
            or not self.source_matched_classes
            or not self.target_matched_classes
            or any(
                item.output is not self.source_output.output
                for item in self.source_matched_classes
            )
            or any(
                item.output is not self.target_output.output
                for item in self.target_matched_classes
            )
            or self.coverage.direction != self.direction
            or source_target is None
            or target_target is None
            or self.source_output.output.row_shape.relation.identity.identity
            != source_target.target_occurrence.identity
            or self.source_output.output.row_shape.relation.identity.module_position
            != source_target.target_occurrence.module_position
            or self.source_output.output.row_shape.relation.identity.declaration_position
            != source_target.target_occurrence.declaration_position
            or self.target_output.output.row_shape.relation.identity.identity
            != target_target.target_occurrence.identity
            or self.target_output.output.row_shape.relation.identity.module_position
            != target_target.target_occurrence.module_position
            or self.target_output.output.row_shape.relation.identity.declaration_position
            != target_target.target_occurrence.declaration_position
        ):
            raise ValueError(
                "Directional guarantee requires exact output-local evidence."
            )
        if self.minimum is ProjectRelationshipMinimumBound.AT_LEAST_ONE:
            if (
                type(self.minimum_evidence) is not ProjectAtLeastOneEvidence
                or self.minimum_evidence.coverage is not self.coverage
                or self.minimum_evidence.source_matched_classes
                != self.source_matched_classes
            ):
                raise ValueError("AT_LEAST_ONE bound requires exact positive evidence.")
        elif type(self.minimum_evidence) is not ProjectMatchGuaranteeFallbackReason:
            raise ValueError("ZERO_ALLOWED requires an epistemic fallback reason.")
        if self.maximum is ProjectRelationshipMaximumBound.AT_MOST_ZERO:
            raise ValueError("AT_MOST_ZERO is not constructible from current evidence.")
        if self.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE:
            if (
                type(self.maximum_evidence) is not ProjectAtMostOneEvidence
                or self.maximum_evidence.direction != self.direction
                or self.maximum_evidence.target_matched_classes
                != self.target_matched_classes
                or any(
                    key.output is not self.target_output.output
                    for key in self.maximum_evidence.target_keys
                )
                or any(
                    not set(key.determinants) <= set(self.target_matched_classes)
                    for key in self.maximum_evidence.target_keys
                )
            ):
                raise ValueError(
                    "AT_MOST_ONE bound requires exact target-key evidence."
                )
        elif type(self.maximum_evidence) is not ProjectMatchGuaranteeFallbackReason:
            raise ValueError("Unbounded maximum requires an epistemic fallback reason.")

    @property
    def display(self) -> str:
        lower = (
            "1" if self.minimum is ProjectRelationshipMinimumBound.AT_LEAST_ONE else "0"
        )
        upper = {
            ProjectRelationshipMaximumBound.AT_MOST_ZERO: "0",
            ProjectRelationshipMaximumBound.AT_MOST_ONE: "1",
            ProjectRelationshipMaximumBound.UNBOUNDED_BY_ONE: "N",
        }[self.maximum]
        return f"{lower}..{upper}"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNonConcreteMatchGuaranteeSubject:
    relationship: (
        ProjectConcreteRelationshipSubject | ProjectNonConcreteRelationshipSubject
    ) = field(repr=False, compare=False, hash=False)
    condition: ProjectNonConcreteRelationshipCondition | None = field(
        default=None, repr=False, compare=False, hash=False
    )
    reason: ProjectMatchGuaranteeFallbackReason


type ProjectRelationshipMatchGuaranteeSubject = (
    ProjectDirectionalRelationshipMatchGuarantee
    | ProjectNonConcreteMatchGuaranteeSubject
)


def classify_match_applicability(
    policy: ProjectReferentialMatchPolicy,
    source_nulls: tuple[bool, ...],
) -> ProjectMatchApplicability:
    if type(policy) is not ProjectReferentialMatchPolicy or not source_nulls:
        raise ValueError("MATCH applicability requires exact policy and tuple.")
    if policy is ProjectReferentialMatchPolicy.MATCH_SIMPLE:
        return (
            ProjectMatchApplicability.NOT_APPLICABLE_SOURCE_NULL
            if any(source_nulls)
            else ProjectMatchApplicability.REQUIRES_MATCH
        )
    if all(source_nulls):
        return ProjectMatchApplicability.NULL_REFERENCE_ACCEPTED
    if any(source_nulls):
        return ProjectMatchApplicability.MIXED_NULL_VIOLATION
    return ProjectMatchApplicability.REQUIRES_MATCH


def _final_output(stage, endpoint):
    target = endpoint.target
    assert target is not None
    identity = target.target_occurrence
    fragments = tuple(
        fragment
        for fragment in stage.analyses.stage.project_plan.concrete_fragments
        if fragment.semantic_facts.owner is identity
    )
    if len(fragments) != 1:
        raise ValueError("Relationship endpoint requires one exact concrete fragment.")
    root = fragments[0].root_relation_output
    matches = tuple(item for item in stage.outputs if item.output is root)
    if len(matches) != 1:
        raise ValueError("Relationship endpoint requires one exact final output.")
    return matches[0]


def _reference_class(output, reference):
    matches = tuple(
        value_class
        for value_class in output.value_classes
        if any(
            member.evidence is reference.semantic_field
            for member in value_class.members
        )
    )
    if len(matches) != 1:
        raise ValueError("Correspondence field requires one exact output value class.")
    return matches[0]


def derive_directional_match_guarantee(
    direction: ProjectRelationshipDirectionIdentity,
    condition: ProjectConcreteRelationshipCondition,
    source_output: ProjectIROutputRelationalProperties,
    target_output: ProjectIROutputRelationalProperties,
    coverage: ProjectReferentialCoverageEvidence | None = None,
) -> ProjectDirectionalRelationshipMatchGuarantee:
    if condition.relationship.occurrence.identity != direction.declaration:
        raise ValueError("Condition and direction must share one relationship.")
    if coverage is not None and coverage.correspondences != condition.correspondences:
        raise ValueError("Coverage requires the complete exact condition tuple.")
    source_position = direction.source.identity.endpoint_position
    target_position = direction.target.identity.endpoint_position
    source_classes = tuple(
        _reference_class(
            source_output,
            correspondence.endpoint_zero
            if source_position == 0
            else correspondence.endpoint_one,
        )
        for correspondence in condition.correspondences
    )
    target_classes = tuple(
        _reference_class(
            target_output,
            correspondence.endpoint_zero
            if target_position == 0
            else correspondence.endpoint_one,
        )
        for correspondence in condition.correspondences
    )
    matched_target_set = frozenset(target_classes)
    qualifying_keys = tuple(
        key
        for key in target_output.keys
        if frozenset(key.determinants) <= matched_target_set
    )
    if qualifying_keys:
        maximum = ProjectRelationshipMaximumBound.AT_MOST_ONE
        maximum_evidence: ProjectMaximumBoundEvidence = ProjectAtMostOneEvidence(
            direction=direction,
            target_keys=qualifying_keys,
            target_matched_classes=target_classes,
            correspondences=condition.correspondences,
        )
    else:
        maximum = ProjectRelationshipMaximumBound.UNBOUNDED_BY_ONE
        maximum_evidence = ProjectMatchGuaranteeFallbackReason.TARGET_KEY_NOT_PROVEN
    retained_coverage: (
        ProjectReferentialCoverageEvidence | ProjectAbsentReferentialCoverage
    )
    if coverage is None:
        minimum = ProjectRelationshipMinimumBound.ZERO_ALLOWED
        minimum_evidence: ProjectMinimumBoundEvidence = (
            ProjectMatchGuaranteeFallbackReason.COVERAGE_NOT_CONSTRUCTIBLE
        )
        retained_coverage = ProjectAbsentReferentialCoverage(direction=direction)
    elif all(
        member.evidence.nullability is ProjectRowFieldNullability.NON_NULL
        for value_class in source_classes
        for member in value_class.members
    ):
        if coverage.direction != direction:
            raise ValueError("Coverage direction must match the requested guarantee.")
        minimum = ProjectRelationshipMinimumBound.AT_LEAST_ONE
        minimum_evidence = ProjectAtLeastOneEvidence(
            coverage=coverage,
            source_matched_classes=source_classes,
        )
        retained_coverage = coverage
    else:
        minimum = ProjectRelationshipMinimumBound.ZERO_ALLOWED
        minimum_evidence = (
            ProjectMatchGuaranteeFallbackReason.SOURCE_NULLABILITY_NOT_PROVEN
        )
        retained_coverage = coverage
    return ProjectDirectionalRelationshipMatchGuarantee(
        direction=direction,
        source_output=source_output,
        target_output=target_output,
        source_matched_classes=source_classes,
        target_matched_classes=target_classes,
        minimum=minimum,
        minimum_evidence=minimum_evidence,
        maximum=maximum,
        maximum_evidence=maximum_evidence,
        coverage=retained_coverage,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipMatchGuaranteeSet:
    conditions: ProjectRelationshipConditionSet = field(
        repr=False, compare=False, hash=False
    )
    relational: ProjectIRRelationalPropertyStage = field(
        repr=False, compare=False, hash=False
    )
    subjects: tuple[ProjectRelationshipMatchGuaranteeSubject, ...]

    def __post_init__(self) -> None:
        if (
            type(self.conditions) is not ProjectRelationshipConditionSet
            or type(self.relational) is not ProjectIRRelationalPropertyStage
            or type(self.subjects) is not tuple
        ):
            raise TypeError("Match guarantee set requires exact typed roots.")
        semantic = self.conditions.relationships.semantic_result.module_semantic_facts
        if self.relational.analyses.stage.project_plan.semantic_facts is not semantic:
            raise ValueError("Match guarantee set requires one semantic snapshot.")
        condition_by_relationship = {
            id(condition.relationship): condition
            for condition in self.conditions.conditions
        }
        expected: list[
            tuple[
                ProjectConcreteRelationshipSubject
                | ProjectNonConcreteRelationshipSubject,
                int | None,
            ]
        ] = []
        for relationship in self.conditions.relationships.subjects:
            if type(relationship) is ProjectNonConcreteRelationshipSubject:
                expected.append((relationship, None))
                continue
            condition = condition_by_relationship[id(relationship)]
            if type(condition) is ProjectNonConcreteRelationshipCondition:
                expected.append((relationship, None))
            else:
                expected.extend(((relationship, 0), (relationship, 1)))
        if len(self.subjects) != len(expected):
            raise ValueError("Match guarantee subjects must be complete and ordered.")
        for subject, (relationship, source_position) in zip(
            self.subjects, expected, strict=True
        ):
            if source_position is None:
                if (
                    type(subject) is not ProjectNonConcreteMatchGuaranteeSubject
                    or subject.relationship is not relationship
                ):
                    raise ValueError("Non-concrete guarantee ledger is detached.")
            else:
                if type(relationship) is not ProjectConcreteRelationshipSubject:
                    raise AssertionError("Directional ledger requires concrete roots.")
                if (
                    type(subject) is not ProjectDirectionalRelationshipMatchGuarantee
                    or subject.direction.declaration != relationship.occurrence.identity
                    or subject.direction.source.identity.endpoint_position
                    != source_position
                ):
                    raise ValueError(
                        "Directional guarantee ledger is detached or reordered."
                    )


def build_project_relationship_match_guarantees(
    conditions: ProjectRelationshipConditionSet,
    relational: ProjectIRRelationalPropertyStage,
) -> ProjectRelationshipMatchGuaranteeSet:
    semantic = conditions.relationships.semantic_result.module_semantic_facts
    if relational.analyses.stage.project_plan.semantic_facts is not semantic:
        raise ValueError("Match guarantees require one exact semantic snapshot.")
    condition_by_relationship = {
        id(condition.relationship): condition for condition in conditions.conditions
    }
    subjects: list[ProjectRelationshipMatchGuaranteeSubject] = []
    for relationship in conditions.relationships.subjects:
        if type(relationship) is ProjectNonConcreteRelationshipSubject:
            subjects.append(
                ProjectNonConcreteMatchGuaranteeSubject(
                    relationship=relationship,
                    reason=ProjectMatchGuaranteeFallbackReason.CONDITION_NOT_PROOF_CAPABLE,
                )
            )
            continue
        condition = condition_by_relationship[id(relationship)]
        if type(condition) is ProjectNonConcreteRelationshipCondition:
            subjects.append(
                ProjectNonConcreteMatchGuaranteeSubject(
                    relationship=relationship,
                    condition=condition,
                    reason=ProjectMatchGuaranteeFallbackReason.CONDITION_NOT_PROOF_CAPABLE,
                )
            )
            continue
        if type(condition) is not ProjectConcreteRelationshipCondition:
            raise AssertionError("Unhandled relationship condition type.")
        endpoints = relationship.occurrence.endpoints
        for source_position in (0, 1):
            direction = ProjectRelationshipDirectionIdentity(
                declaration=relationship.occurrence.identity,
                source=endpoints[source_position],
                target=endpoints[1 - source_position],
            )
            subjects.append(
                derive_directional_match_guarantee(
                    direction,
                    condition,
                    _final_output(relational, direction.source),
                    _final_output(relational, direction.target),
                )
            )
    return ProjectRelationshipMatchGuaranteeSet(
        conditions=conditions,
        relational=relational,
        subjects=tuple(subjects),
    )
