"""Private explicit relationship paths and future JOIN-shape effects."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from pietto._project.project_ir_relational_properties import (
    ProjectIROutputRelationalProperties,
)
from pietto._project.project_relationship_match_guarantees import (
    ProjectDirectionalRelationshipMatchGuarantee,
    ProjectNonConcreteMatchGuaranteeSubject,
    ProjectRelationshipMatchGuaranteeSet,
    ProjectRelationshipMaximumBound,
    ProjectRelationshipMinimumBound,
)
from pietto._project.project_relationships import ProjectRelationshipDeclarationIdentity

__all__: tuple[str, ...] = ()


class ProjectDirectRelationshipCandidateStatus(StrEnum):
    ABSENT = "absent"
    CONCRETE = "concrete"
    AMBIGUOUS = "ambiguous"


class ProjectRelationshipFanoutEffect(StrEnum):
    PRESERVES_SOURCE_MULTIPLICITY = "preserves_source_multiplicity"
    MAY_MULTIPLY = "may_multiply"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class ProjectRelationshipInnerSurvivalEffect(StrEnum):
    GUARANTEES_SOURCE_SURVIVAL = "guarantees_source_survival"
    MAY_DROP_SOURCE_ROWS = "may_drop_source_rows"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


class ProjectRelationshipLeftNullingEffect(StrEnum):
    NO_MISSING_MATCH_NULLING = "no_missing_match_nulling"
    MAY_NULL_EXTEND = "may_null_extend"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipDirectCandidateResult:
    source: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    target: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    status: ProjectDirectRelationshipCandidateStatus
    candidates: tuple[ProjectDirectionalRelationshipMatchGuarantee, ...]

    def __post_init__(self) -> None:
        expected = {
            0: ProjectDirectRelationshipCandidateStatus.ABSENT,
            1: ProjectDirectRelationshipCandidateStatus.CONCRETE,
        }.get(len(self.candidates), ProjectDirectRelationshipCandidateStatus.AMBIGUOUS)
        if self.status is not expected or any(
            item.source_output is not self.source
            or item.target_output is not self.target
            for item in self.candidates
        ):
            raise ValueError(
                "Direct candidate result must retain every exact candidate."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipJoinShapeIndex:
    guarantees: ProjectRelationshipMatchGuaranteeSet = field(
        repr=False, compare=False, hash=False
    )
    directions: tuple[ProjectDirectionalRelationshipMatchGuarantee, ...]
    non_concrete: tuple[ProjectNonConcreteMatchGuaranteeSubject, ...]
    by_pair: Mapping[
        tuple[object, object],
        tuple[ProjectDirectionalRelationshipMatchGuarantee, ...],
    ] = field(repr=False, compare=False, hash=False)
    by_declaration: Mapping[
        ProjectRelationshipDeclarationIdentity,
        tuple[ProjectDirectionalRelationshipMatchGuarantee, ...],
    ] = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        expected_directions = tuple(
            subject
            for subject in self.guarantees.subjects
            if type(subject) is ProjectDirectionalRelationshipMatchGuarantee
        )
        expected_non_concrete = tuple(
            subject
            for subject in self.guarantees.subjects
            if type(subject) is ProjectNonConcreteMatchGuaranteeSubject
        )
        if (
            self.directions != expected_directions
            or self.non_concrete != expected_non_concrete
        ):
            raise ValueError(
                "Join-shape index must retain the complete Slice-8 ledger."
            )
        expected_pairs: dict[
            tuple[object, object],
            list[ProjectDirectionalRelationshipMatchGuarantee],
        ] = {}
        expected_declarations: dict[
            ProjectRelationshipDeclarationIdentity,
            list[ProjectDirectionalRelationshipMatchGuarantee],
        ] = {}
        for direction in self.directions:
            key = (
                direction.source_output.output.occurrence.ref,
                direction.target_output.output.occurrence.ref,
            )
            expected_pairs.setdefault(key, []).append(direction)
            expected_declarations.setdefault(
                direction.direction.declaration, []
            ).append(direction)
        pair_values = {key: tuple(values) for key, values in expected_pairs.items()}
        declaration_values = {
            key: tuple(values) for key, values in expected_declarations.items()
        }
        if (
            dict(self.by_pair) != pair_values
            or dict(self.by_declaration) != declaration_values
        ):
            raise ValueError(
                "Join-shape index buckets must preserve exact authority order."
            )
        object.__setattr__(self, "by_pair", MappingProxyType(pair_values))
        object.__setattr__(self, "by_declaration", MappingProxyType(declaration_values))

    def resolve_direct(
        self,
        source: ProjectIROutputRelationalProperties,
        target: ProjectIROutputRelationalProperties,
    ) -> ProjectRelationshipDirectCandidateResult:
        candidates = self.by_pair.get(
            (source.output.occurrence.ref, target.output.occurrence.ref), ()
        )
        status = {
            0: ProjectDirectRelationshipCandidateStatus.ABSENT,
            1: ProjectDirectRelationshipCandidateStatus.CONCRETE,
        }.get(len(candidates), ProjectDirectRelationshipCandidateStatus.AMBIGUOUS)
        return ProjectRelationshipDirectCandidateResult(
            source=source,
            target=target,
            status=status,
            candidates=candidates,
        )


def build_project_relationship_join_shape_index(
    guarantees: ProjectRelationshipMatchGuaranteeSet,
) -> ProjectRelationshipJoinShapeIndex:
    directions = tuple(
        subject
        for subject in guarantees.subjects
        if type(subject) is ProjectDirectionalRelationshipMatchGuarantee
    )
    non_concrete = tuple(
        subject
        for subject in guarantees.subjects
        if type(subject) is ProjectNonConcreteMatchGuaranteeSubject
    )
    pairs: dict[
        tuple[object, object], list[ProjectDirectionalRelationshipMatchGuarantee]
    ] = {}
    declarations: dict[
        ProjectRelationshipDeclarationIdentity,
        list[ProjectDirectionalRelationshipMatchGuarantee],
    ] = {}
    for direction in directions:
        pair = (
            direction.source_output.output.occurrence.ref,
            direction.target_output.output.occurrence.ref,
        )
        pairs.setdefault(pair, []).append(direction)
        declarations.setdefault(direction.direction.declaration, []).append(direction)
    return ProjectRelationshipJoinShapeIndex(
        guarantees=guarantees,
        directions=directions,
        non_concrete=non_concrete,
        by_pair={key: tuple(values) for key, values in pairs.items()},
        by_declaration={key: tuple(values) for key, values in declarations.items()},
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipPathStep:
    position: int
    guarantee: ProjectDirectionalRelationshipMatchGuarantee = field(
        repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        if type(self.position) is not int or self.position < 0:
            raise ValueError("Path-step position must be non-negative.")
        if type(self.guarantee) is not ProjectDirectionalRelationshipMatchGuarantee:
            raise TypeError("Path step requires an exact directional guarantee.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipPath:
    index: ProjectRelationshipJoinShapeIndex = field(
        repr=False, compare=False, hash=False
    )
    steps: tuple[ProjectRelationshipPathStep, ...]

    def __post_init__(self) -> None:
        if not self.steps or tuple(step.position for step in self.steps) != tuple(
            range(len(self.steps))
        ):
            raise ValueError("Relationship path requires non-empty contiguous steps.")
        if any(
            not any(step.guarantee is retained for retained in self.index.directions)
            for step in self.steps
        ):
            raise ValueError("Relationship path step is detached from the exact index.")
        if any(
            left.guarantee.target_output is not right.guarantee.source_output
            for left, right in zip(self.steps, self.steps[1:], strict=False)
        ):
            raise ValueError("Relationship path steps must be exact-object contiguous.")


def build_explicit_relationship_path(
    index: ProjectRelationshipJoinShapeIndex,
    directions: tuple[ProjectDirectionalRelationshipMatchGuarantee, ...],
) -> ProjectRelationshipPath:
    if (
        type(index) is not ProjectRelationshipJoinShapeIndex
        or type(directions) is not tuple
    ):
        raise TypeError("Explicit path construction requires exact typed inputs.")
    return ProjectRelationshipPath(
        index=index,
        steps=tuple(
            ProjectRelationshipPathStep(position=position, guarantee=direction)
            for position, direction in enumerate(directions)
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipHopEffect:
    step: ProjectRelationshipPathStep
    fanout: ProjectRelationshipFanoutEffect
    inner_survival: ProjectRelationshipInnerSurvivalEffect
    left_nulling: ProjectRelationshipLeftNullingEffect

    def __post_init__(self) -> None:
        guarantee = self.step.guarantee
        expected_fanout = (
            ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY
            if guarantee.maximum
            in {
                ProjectRelationshipMaximumBound.AT_MOST_ZERO,
                ProjectRelationshipMaximumBound.AT_MOST_ONE,
            }
            else ProjectRelationshipFanoutEffect.MAY_MULTIPLY
        )
        expected_survival = (
            ProjectRelationshipInnerSurvivalEffect.GUARANTEES_SOURCE_SURVIVAL
            if guarantee.minimum is ProjectRelationshipMinimumBound.AT_LEAST_ONE
            else ProjectRelationshipInnerSurvivalEffect.MAY_DROP_SOURCE_ROWS
        )
        expected_nulling = (
            ProjectRelationshipLeftNullingEffect.NO_MISSING_MATCH_NULLING
            if guarantee.minimum is ProjectRelationshipMinimumBound.AT_LEAST_ONE
            else ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
        )
        if (
            self.fanout is not expected_fanout
            or self.inner_survival is not expected_survival
            or self.left_nulling is not expected_nulling
        ):
            raise ValueError("Hop effects must derive from independent exact bounds.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipPathAnalysis:
    path: ProjectRelationshipPath
    hops: tuple[ProjectRelationshipHopEffect, ...]
    fanout: ProjectRelationshipFanoutEffect
    multiplying_hops: tuple[ProjectRelationshipPathStep, ...]
    inner_survival: ProjectRelationshipInnerSurvivalEffect
    survival_risk_hops: tuple[ProjectRelationshipPathStep, ...]
    left_nulling: ProjectRelationshipLeftNullingEffect
    local_nulling_roots: tuple[ProjectRelationshipPathStep, ...]
    propagated_null_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.hops) != len(self.path.steps) or any(
            effect.step is not step
            for effect, step in zip(self.hops, self.path.steps, strict=True)
        ):
            raise ValueError("Path analysis must retain every exact hop.")
        expected_multiplying = tuple(
            effect.step
            for effect in self.hops
            if effect.fanout is ProjectRelationshipFanoutEffect.MAY_MULTIPLY
        )
        expected_survival_risks = tuple(
            effect.step
            for effect in self.hops
            if effect.inner_survival
            is ProjectRelationshipInnerSurvivalEffect.MAY_DROP_SOURCE_ROWS
        )
        expected_local_nulling = tuple(
            effect.step
            for effect in self.hops
            if effect.left_nulling
            is ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
        )
        source_may_be_null = False
        expected_propagated: list[int] = []
        for effect in self.hops:
            source_may_be_null = source_may_be_null or (
                effect.left_nulling
                is ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
            )
            if source_may_be_null:
                expected_propagated.append(effect.step.position)
        expected_fanout = (
            ProjectRelationshipFanoutEffect.MAY_MULTIPLY
            if expected_multiplying
            else ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY
        )
        expected_survival = (
            ProjectRelationshipInnerSurvivalEffect.MAY_DROP_SOURCE_ROWS
            if expected_survival_risks
            else ProjectRelationshipInnerSurvivalEffect.GUARANTEES_SOURCE_SURVIVAL
        )
        expected_nulling = (
            ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
            if expected_propagated
            else ProjectRelationshipLeftNullingEffect.NO_MISSING_MATCH_NULLING
        )
        if (
            self.fanout is not expected_fanout
            or self.multiplying_hops != expected_multiplying
            or self.inner_survival is not expected_survival
            or self.survival_risk_hops != expected_survival_risks
            or self.left_nulling is not expected_nulling
            or self.local_nulling_roots != expected_local_nulling
            or self.propagated_null_positions != tuple(expected_propagated)
        ):
            raise ValueError("Path aggregate effects require complete exact evidence.")


def analyze_relationship_path(
    path: ProjectRelationshipPath,
) -> ProjectRelationshipPathAnalysis:
    hops = tuple(
        ProjectRelationshipHopEffect(
            step=step,
            fanout=(
                ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY
                if step.guarantee.maximum
                in {
                    ProjectRelationshipMaximumBound.AT_MOST_ZERO,
                    ProjectRelationshipMaximumBound.AT_MOST_ONE,
                }
                else ProjectRelationshipFanoutEffect.MAY_MULTIPLY
            ),
            inner_survival=(
                ProjectRelationshipInnerSurvivalEffect.GUARANTEES_SOURCE_SURVIVAL
                if step.guarantee.minimum
                is ProjectRelationshipMinimumBound.AT_LEAST_ONE
                else ProjectRelationshipInnerSurvivalEffect.MAY_DROP_SOURCE_ROWS
            ),
            left_nulling=(
                ProjectRelationshipLeftNullingEffect.NO_MISSING_MATCH_NULLING
                if step.guarantee.minimum
                is ProjectRelationshipMinimumBound.AT_LEAST_ONE
                else ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
            ),
        )
        for step in path.steps
    )
    multiplying = tuple(
        effect.step
        for effect in hops
        if effect.fanout is ProjectRelationshipFanoutEffect.MAY_MULTIPLY
    )
    survival_risks = tuple(
        effect.step
        for effect in hops
        if effect.inner_survival
        is ProjectRelationshipInnerSurvivalEffect.MAY_DROP_SOURCE_ROWS
    )
    local_nulling = tuple(
        effect.step
        for effect in hops
        if effect.left_nulling is ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
    )
    source_may_be_null = False
    propagated: list[int] = []
    for effect in hops:
        source_may_be_null = source_may_be_null or (
            effect.left_nulling is ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
        )
        if source_may_be_null:
            propagated.append(effect.step.position)
    return ProjectRelationshipPathAnalysis(
        path=path,
        hops=hops,
        fanout=(
            ProjectRelationshipFanoutEffect.MAY_MULTIPLY
            if multiplying
            else ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY
        ),
        multiplying_hops=multiplying,
        inner_survival=(
            ProjectRelationshipInnerSurvivalEffect.MAY_DROP_SOURCE_ROWS
            if survival_risks
            else ProjectRelationshipInnerSurvivalEffect.GUARANTEES_SOURCE_SURVIVAL
        ),
        survival_risk_hops=survival_risks,
        left_nulling=(
            ProjectRelationshipLeftNullingEffect.MAY_NULL_EXTEND
            if propagated
            else ProjectRelationshipLeftNullingEffect.NO_MISSING_MATCH_NULLING
        ),
        local_nulling_roots=local_nulling,
        propagated_null_positions=tuple(propagated),
    )
