"""Private post-base JOIN region stage and shared JOIN property helpers.

No authored JOIN joins by itself, so the stage records every join-bearing
owner as a non-concrete region and allocates nothing; current JOIN regions
(`project_current_joins`) build JOIN rows from ready `on` conditions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast, TypeGuard

from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_grain import (
    ProjectBaseGrainFactorIdentity,
    CompiledGrainFactorIdentity,
    ProjectGrainBasisState,
    ProjectGrainDependencyFact,
    ProjectGrainDomainFactor,
    ProjectGrainFactorIdentity,
    ProjectGrainOriginAuthority,
    ProjectJoinGrainFactorIdentity,
)
from pietto._project.project_ir import (
    ProjectIRJoinInputUseOccurrence,
    ProjectIRPlanNodeRef,
)
from pietto._project.project_ir_composition import ProjectIRProjectPlan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_properties import (
    ProjectIRJoinRowOutput,
    ProjectIRPropertyAvailability,
    ProjectIRProvidedPropertySlot,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRProvidedIntrinsicGrain,
    ProjectIRRelationalPropertyStage,
    ProjectIROutputCandidateKey,
    ProjectIROutputFieldOccurrence,
    ProjectIROutputValueClass,
    ProjectIROutputValueFD,
)
from pietto._project.project_relationship_uses import (
    ProjectJoinUseState,
    ProjectNonConcreteJoinUse,
    ProjectRelationJoinUseLedger,
    ProjectRelationshipUseSet,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRJoinUnavailableProperty:
    output: ProjectIRJoinRowOutput
    property_slot: ProjectIRProvidedPropertySlot
    availability: ProjectIRPropertyAvailability = field(init=False)

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIRJoinRowOutput:
            raise TypeError("Unavailable JOIN property requires a JOIN output.")
        if type(self.property_slot) is not ProjectIRProvidedPropertySlot or (
            self.property_slot
            not in {
                ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING,
                ProjectIRProvidedPropertySlot.NULL_EXTENSION,
            }
        ):
            raise ValueError("JOIN unavailability is limited to ordering and nulling.")
        object.__setattr__(
            self,
            "availability",
            (
                ProjectIRPropertyAvailability.UNKNOWN
                if self.property_slot
                is ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING
                else ProjectIRPropertyAvailability.NOT_APPLICABLE
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRNonConcreteJoinRegion:
    ledger: ProjectRelationJoinUseLedger = field(repr=False, compare=False, hash=False)
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState = field(init=False)
    state: ProjectJoinUseState = field(init=False)
    blockers: tuple[ProjectNonConcreteJoinUse, ...] = field(
        init=False, repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        if (
            type(self.ledger) is not ProjectRelationJoinUseLedger
            or type(self.starting_allocation) is not ProjectIRAllocationState
        ):
            raise TypeError("Non-concrete JOIN region requires exact roots.")
        expected = tuple(
            use for use in self.ledger.uses if type(use) is ProjectNonConcreteJoinUse
        )
        if not expected:
            raise ValueError("Non-concrete JOIN region must consume zero allocation.")
        object.__setattr__(self, "ending_allocation", self.starting_allocation)
        object.__setattr__(self, "state", _dominant_region_state(expected))
        object.__setattr__(self, "blockers", expected)


type ProjectIRJoinRegion = ProjectIRNonConcreteJoinRegion


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRJoinRegionStage:
    base_plan: ProjectIRProjectPlan = field(repr=False, compare=False, hash=False)
    base_relational: ProjectIRRelationalPropertyStage = field(
        repr=False, compare=False, hash=False
    )
    uses: ProjectRelationshipUseSet = field(repr=False, compare=False, hash=False)
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    regions: tuple[ProjectIRJoinRegion, ...]

    def __post_init__(self) -> None:
        if (
            type(self.base_plan) is not ProjectIRProjectPlan
            or type(self.base_relational) is not ProjectIRRelationalPropertyStage
            or self.base_relational.analyses.stage.project_plan is not self.base_plan
            or type(self.uses) is not ProjectRelationshipUseSet
            or self.uses.semantic_result.module_semantic_facts
            is not self.base_plan.semantic_facts
            or self.starting_allocation is not self.base_plan.ending_allocation
        ):
            raise ValueError("JOIN region requires exact base plan/property/use roots.")
        if (
            type(self.ending_allocation) is not ProjectIRAllocationState
            or type(self.regions) is not tuple
            or any(
                type(region) is not ProjectIRNonConcreteJoinRegion
                for region in self.regions
            )
            or len(self.regions) != len(self.uses.ledgers)
            or any(
                region.ledger is not ledger
                for region, ledger in zip(self.regions, self.uses.ledgers, strict=True)
            )
        ):
            raise ValueError("JOIN regions must retain declaration order.")
        current = self.starting_allocation
        for region in self.regions:
            if region.starting_allocation is not current:
                raise ValueError(
                    "JOIN regions must retain exact allocation continuity."
                )
            current = region.ending_allocation
        if current is not self.ending_allocation:
            raise ValueError("JOIN regions must end at the exact stage allocation.")


def _dominant_region_state(
    blockers: tuple[ProjectNonConcreteJoinUse, ...],
) -> ProjectJoinUseState:
    states = {item.state for item in blockers}
    if ProjectJoinUseState.AMBIGUOUS in states:
        return ProjectJoinUseState.AMBIGUOUS
    if ProjectJoinUseState.BLOCKED in states:
        return ProjectJoinUseState.BLOCKED
    return ProjectJoinUseState.UNKNOWN


def _classes_for_output(
    *,
    old: tuple[ProjectIROutputValueClass, ...],
    output: ProjectIRJoinRowOutput,
    fields: tuple[ProjectIROutputFieldOccurrence, ...],
    offset: int,
) -> tuple[
    tuple[ProjectIROutputValueClass, ...],
    dict[ProjectIROutputValueClass, ProjectIROutputValueClass],
]:
    classes: list[ProjectIROutputValueClass] = []
    images: dict[ProjectIROutputValueClass, ProjectIROutputValueClass] = {}
    for value_class in old:
        image = ProjectIROutputValueClass(
            output=output,
            members=tuple(
                fields[offset + item.field_position] for item in value_class.members
            ),
        )
        classes.append(image)
        images[value_class] = image
    return tuple(classes), images


def _ordered_classes(
    values: tuple[ProjectIROutputValueClass, ...],
    universe: tuple[ProjectIROutputValueClass, ...],
) -> tuple[ProjectIROutputValueClass, ...]:
    selected = set(values)
    return tuple(item for item in universe if item in selected)


def _image_key(
    key: ProjectIROutputCandidateKey,
    images: dict[ProjectIROutputValueClass, ProjectIROutputValueClass],
    universe: tuple[ProjectIROutputValueClass, ...],
    *,
    output: ProjectIRJoinRowOutput,
    force_lax: bool = False,
    support: object,
) -> ProjectIROutputCandidateKey:
    determinants = _ordered_classes(
        tuple(images[item] for item in key.determinants), universe
    )
    return ProjectIROutputCandidateKey(
        output=output,
        determinants=determinants,
        strength=(
            ProjectRowUniquenessStrength.LAX
            if force_lax
            else (
                ProjectRowUniquenessStrength.STRICT
                if all(_all_non_null(item) for item in determinants)
                else key.strength
            )
        ),
        supports=(*key.supports, support),
    )


def _image_fd(
    fact: ProjectIROutputValueFD,
    images: dict[ProjectIROutputValueClass, ProjectIROutputValueClass],
    universe: tuple[ProjectIROutputValueClass, ...],
    *,
    output: ProjectIRJoinRowOutput,
    strength: ProjectRowUniquenessStrength,
    support: object,
) -> ProjectIROutputValueFD | None:
    determinants = _ordered_classes(
        tuple(images[item] for item in fact.determinants), universe
    )
    dependents = tuple(
        item
        for item in _ordered_classes(
            tuple(images[item] for item in fact.dependents), universe
        )
        if item not in determinants
    )
    if not dependents:
        return None
    return ProjectIROutputValueFD(
        output=output,
        determinants=determinants,
        dependents=dependents,
        strength=strength,
        supports=(*fact.supports, support),
    )


def _all_non_null(value_class: ProjectIROutputValueClass) -> bool:
    return all(
        member.effective_nullability is ProjectRowFieldNullability.NON_NULL
        for member in value_class.members
    )


def _is_join_factor(
    identity: object,
) -> TypeGuard[ProjectJoinGrainFactorIdentity | CompiledGrainFactorIdentity]:
    return type(identity) is ProjectJoinGrainFactorIdentity or (
        type(identity) is CompiledGrainFactorIdentity and identity.base is not None
    )


def _join_factor(*, base, introduction_use, nulling_joins, source_factor=None):
    if type(base) is CompiledGrainFactorIdentity:
        from pietto._project.project_compiled_schema import Address

        origin = base.origin
        consumer = origin.root.records[
            Address(introduction_use.kind, introduction_use.position)
        ].get("consumer")
        return CompiledGrainFactorIdentity(
            origin=origin,
            ref=origin.references[consumer],
            kind=base.kind,
            base=base,
            introduction_use=introduction_use,
            nulling_joins=nulling_joins,
            source_factor=source_factor,
        )
    return ProjectJoinGrainFactorIdentity(
        base=base,
        introduction_use=introduction_use,
        nulling_joins=nulling_joins,
        source_factor=source_factor,
    )


def _base_factor(
    identity: ProjectGrainFactorIdentity,
) -> ProjectBaseGrainFactorIdentity | CompiledGrainFactorIdentity:
    if _is_join_factor(identity):
        assert identity.base is not None
        return identity.base
    return cast(ProjectBaseGrainFactorIdentity, identity)


def _grain(
    *,
    output: ProjectIRJoinRowOutput,
    left: ProjectIRProvidedIntrinsicGrain,
    right: ProjectIRProvidedIntrinsicGrain,
    left_use: ProjectIRJoinInputUseOccurrence,
    right_use: ProjectIRJoinInputUseOccurrence,
    source_factors: tuple[ProjectGrainFactorIdentity, ...] | None,
    nulling: tuple[ProjectIRPlanNodeRef, ...],
    left_nulling: tuple[ProjectIRPlanNodeRef, ...] = (),
    forward_at_most_one: bool,
    reverse_at_most_one: bool,
    witness: object,
    origin_set: ProjectGrainOriginAuthority | None = None,
    preserve_nested_inputs: bool = False,
    named_left_input: bool = False,
    left_only: bool = False,
    empty_state: ProjectGrainBasisState = ProjectGrainBasisState.GLOBAL,
    local_reverse_sources: tuple[tuple[ProjectGrainFactorIdentity, ...], ...] = (),
) -> tuple[ProjectIRProvidedIntrinsicGrain, tuple[ProjectGrainFactorIdentity, ...]]:
    if not left_only and origin_set is None and left.origin_set is not right.origin_set:
        raise ValueError("JOIN grain transfer requires one exact origin set.")
    left_images: dict[ProjectGrainFactorIdentity, ProjectGrainFactorIdentity] = {}
    for factor in left.factors:
        identity = factor.identity
        left_images[identity] = (
            identity
            if _is_join_factor(identity)
            and not (preserve_nested_inputs and named_left_input)
            and not left_nulling
            else _join_factor(
                base=_base_factor(identity),
                introduction_use=(
                    identity.introduction_use
                    if _is_join_factor(identity)
                    and left_nulling
                    and not (preserve_nested_inputs and named_left_input)
                    else left_use.ref
                ),
                nulling_joins=(
                    (*identity.nulling_joins, *left_nulling)
                    if _is_join_factor(identity)
                    and left_nulling
                    and not (preserve_nested_inputs and named_left_input)
                    else left_nulling
                ),
                source_factor=identity
                if _is_join_factor(identity)
                and (preserve_nested_inputs or bool(left_nulling))
                else None,
            )
        )
    right_images = {
        factor.identity: _join_factor(
            base=_base_factor(factor.identity),
            introduction_use=right_use.ref,
            nulling_joins=nulling,
            source_factor=factor.identity
            if preserve_nested_inputs and _is_join_factor(factor.identity)
            else None,
        )
        for factor in (() if left_only else right.factors)
    }
    left_active = tuple(left_images[item] for item in left.active)
    right_active = (
        () if left_only else tuple(right_images[item] for item in right.active)
    )
    active = (*left_active, *right_active)
    factor_identities = (
        *(left_images[item.identity] for item in left.factors),
        *(right_images[item.identity] for item in (() if left_only else right.factors)),
    )
    factors = tuple(
        ProjectGrainDomainFactor(identity=item) for item in factor_identities
    )
    dependencies: list[ProjectGrainDependencyFact] = []
    for fact, images in (
        *((fact, left_images) for fact in left.dependencies),
        *((fact, right_images) for fact in (() if left_only else right.dependencies)),
    ):
        dependencies.append(
            ProjectGrainDependencyFact(
                determinants=tuple(images[item] for item in fact.determinants),
                dependents=tuple(images[item] for item in fact.dependents),
            )
        )
    effective_source_factors = (
        left_active
        if source_factors is None
        else tuple(left_images[item] for item in source_factors)
    )
    # A JOIN that NULL-extends its left side (RIGHT, FULL) keeps every right row
    # that matches no left row beside one NULL left part, so with NULL as a value
    # the left side determines nothing; an aggregate that never reads such a row
    # gets this dependency back (`project_joined_aggregation`).
    if (
        forward_at_most_one
        and not left_nulling
        and effective_source_factors
        and right_active
    ):
        dependencies.append(
            ProjectGrainDependencyFact(
                determinants=effective_source_factors,
                dependents=right_active,
            )
        )
    if (
        reverse_at_most_one
        and not nulling
        and right_active
        and effective_source_factors
    ):
        dependencies.append(
            ProjectGrainDependencyFact(
                determinants=right_active,
                dependents=effective_source_factors,
            )
        )
    if not reverse_at_most_one and not nulling and right_active:
        for source in local_reverse_sources:
            if source:
                dependencies.append(
                    ProjectGrainDependencyFact(
                        determinants=right_active,
                        dependents=tuple(left_images[item] for item in source),
                    )
                )
    if left_only:
        state = left.state
    elif ProjectGrainBasisState.UNKNOWN in {left.state, right.state}:
        state = ProjectGrainBasisState.UNKNOWN
    elif active:
        state = ProjectGrainBasisState.FACTORIZED
    elif empty_state in {
        ProjectGrainBasisState.GLOBAL,
        ProjectGrainBasisState.UNKNOWN,
    }:
        state = empty_state
    else:
        raise ValueError("Empty JOIN grain requires GLOBAL or UNKNOWN authority.")
    return (
        ProjectIRProvidedIntrinsicGrain(
            output=output,
            state=state,
            factors=factors,
            active=active,
            dependencies=tuple(dependencies),
            origin_set=left.origin_set if origin_set is None else origin_set,
            witness=witness,
        ),
        right_active,
    )


def build_project_ir_join_region(
    *,
    base_plan: ProjectIRProjectPlan,
    base_relational: ProjectIRRelationalPropertyStage,
    uses: ProjectRelationshipUseSet,
    allocation: ProjectIRAllocationState,
) -> ProjectIRJoinRegionStage:
    """Extend one exact base plan with one zero-allocation region per owner."""

    if (
        type(base_plan) is not ProjectIRProjectPlan
        or type(base_relational) is not ProjectIRRelationalPropertyStage
        or base_relational.analyses.stage.project_plan is not base_plan
        or type(uses) is not ProjectRelationshipUseSet
        or uses.semantic_result.module_semantic_facts is not base_plan.semantic_facts
        or allocation is not base_plan.ending_allocation
    ):
        raise ValueError(
            "JOIN construction requires exact base plan/property/use roots."
        )
    return ProjectIRJoinRegionStage(
        base_plan=base_plan,
        base_relational=base_relational,
        uses=uses,
        starting_allocation=allocation,
        ending_allocation=allocation,
        regions=tuple(
            ProjectIRNonConcreteJoinRegion(
                ledger=ledger, starting_allocation=allocation
            )
            for ledger in uses.ledgers
        ),
    )
