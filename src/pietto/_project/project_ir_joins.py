"""Private post-base binary JOIN region and relational-property extension."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_grain import (
    ProjectBaseGrainFactorIdentity,
    ProjectGrainBasisState,
    ProjectGrainDependencyFact,
    ProjectGrainDomainFactor,
    ProjectGrainFactorIdentity,
    ProjectJoinGrainFactorIdentity,
)
from pietto._project.project_ir import (
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIRJoinInputUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRRelationAnchor,
    ProjectIRStructuralStage,
    ProjectIRUseRef,
)
from pietto._project.project_ir_composition import ProjectIRProjectPlan
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.project_ir_properties import (
    ProjectIRJoinRowOutput,
    ProjectIRJoinedRowField,
    ProjectIRJoinedRowShape,
    ProjectIRPropertyAvailability,
    ProjectIRProvidedNullExtension,
    ProjectIRProvidedPropertySlot,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRProvidedIntrinsicGrain,
    ProjectIRRelationalPropertyStage,
    ProjectIROutputCandidateKey,
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueClass,
    ProjectIROutputValueFD,
    _compile_output_fd_index,
    _field_occurrences,
    _frontier,
    _key_fds,
)
from pietto._project.project_relationship_conditions import (
    ProjectConcreteRelationshipCondition,
    ProjectRelationshipEqualityCorrespondence,
)
from pietto._project.project_relationship_match_guarantees import (
    ProjectDirectionalRelationshipMatchGuarantee,
    ProjectRelationshipMaximumBound,
    ProjectRelationshipMinimumBound,
)
from pietto._project.project_relationship_paths import (
    ProjectRelationshipFanoutEffect,
    ProjectRelationshipPathStep,
)
from pietto._project.project_relationship_uses import (
    ProjectConcreteJoinUse,
    ProjectJoinUseIdentity,
    ProjectJoinUseState,
    ProjectNonConcreteJoinUse,
    ProjectRelationJoinUseLedger,
    ProjectRelationshipUseSet,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength

__all__: tuple[str, ...] = ()


class ProjectIRBinaryJoinKind(StrEnum):
    INNER = "inner"
    LEFT = "left"


class ProjectIRJoinRowSurvivalEffect(StrEnum):
    GUARANTEES_LEFT_SURVIVAL = "guarantees_left_survival"
    MAY_DROP_LEFT_ROWS = "may_drop_left_rows"


class ProjectIRJoinNullExtensionEffect(StrEnum):
    NO_NEW_NULL_EXTENSION = "no_new_null_extension"
    MAY_NULL_EXTEND_RIGHT = "may_null_extend_right"


class ProjectIROuterJoinBarrier(StrEnum):
    NOT_APPLICABLE = "not_applicable"
    PRESENT = "present"


def _relationship_field_references(
    correspondence: ProjectRelationshipEqualityCorrespondence,
    guarantee: ProjectDirectionalRelationshipMatchGuarantee,
):
    source_endpoint = guarantee.direction.source.identity.endpoint_position
    return (
        (correspondence.endpoint_zero, correspondence.endpoint_one)
        if source_endpoint == 0
        else (correspondence.endpoint_one, correspondence.endpoint_zero)
    )


def _join_effects(
    kind: ProjectIRBinaryJoinKind,
    guarantee: ProjectDirectionalRelationshipMatchGuarantee,
    source_nulling: tuple[ProjectIRPlanNodeRef, ...],
) -> tuple[
    ProjectRelationshipFanoutEffect,
    ProjectIRJoinRowSurvivalEffect,
    ProjectIRJoinNullExtensionEffect,
    ProjectIROuterJoinBarrier,
]:
    actual_nulling = kind is ProjectIRBinaryJoinKind.LEFT and (
        guarantee.minimum is ProjectRelationshipMinimumBound.ZERO_ALLOWED
        or bool(source_nulling)
    )
    return (
        (
            ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY
            if guarantee.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
            else ProjectRelationshipFanoutEffect.MAY_MULTIPLY
        ),
        (
            ProjectIRJoinRowSurvivalEffect.GUARANTEES_LEFT_SURVIVAL
            if kind is ProjectIRBinaryJoinKind.LEFT
            or (
                not source_nulling
                and guarantee.minimum is ProjectRelationshipMinimumBound.AT_LEAST_ONE
            )
            else ProjectIRJoinRowSurvivalEffect.MAY_DROP_LEFT_ROWS
        ),
        (
            ProjectIRJoinNullExtensionEffect.MAY_NULL_EXTEND_RIGHT
            if actual_nulling
            else ProjectIRJoinNullExtensionEffect.NO_NEW_NULL_EXTENSION
        ),
        (
            ProjectIROuterJoinBarrier.PRESENT
            if kind is ProjectIRBinaryJoinKind.LEFT
            else ProjectIROuterJoinBarrier.NOT_APPLICABLE
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRBinaryJoinIdentity:
    use: ProjectJoinUseIdentity
    path_step_position: int

    def __post_init__(self) -> None:
        if type(self.use) is not ProjectJoinUseIdentity:
            raise TypeError("Binary JOIN identity requires an exact JOIN use.")
        if type(self.path_step_position) is not int or self.path_step_position < 0:
            raise ValueError("Binary JOIN path-step position must be non-negative.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRJoinMatchFieldPair:
    correspondence: ProjectRelationshipEqualityCorrespondence = field(
        repr=False, compare=False, hash=False
    )
    left: ProjectIRJoinedRowField
    right: ProjectIRJoinedRowField

    def __post_init__(self) -> None:
        if type(self.correspondence) is not ProjectRelationshipEqualityCorrespondence:
            raise TypeError("JOIN match pair requires an exact correspondence.")
        if (
            type(self.left) is not ProjectIRJoinedRowField
            or type(self.right) is not ProjectIRJoinedRowField
            or self.left is self.right
        ):
            raise ValueError("JOIN match pair requires two exact field instances.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRBinaryJoinOccurrence:
    identity: ProjectIRBinaryJoinIdentity
    use: ProjectConcreteJoinUse = field(repr=False, compare=False, hash=False)
    path_step: ProjectRelationshipPathStep = field(
        repr=False, compare=False, hash=False
    )
    guarantee: ProjectDirectionalRelationshipMatchGuarantee = field(
        repr=False, compare=False, hash=False
    )
    condition: ProjectConcreteRelationshipCondition = field(
        repr=False, compare=False, hash=False
    )
    node: ProjectIRPlanNodeOccurrence
    left_input: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    right_input: ProjectIROutputRelationalProperties = field(
        repr=False, compare=False, hash=False
    )
    input_slots: tuple[ProjectIRInputSlotOccurrence, ProjectIRInputSlotOccurrence]
    input_uses: tuple[ProjectIRJoinInputUseOccurrence, ProjectIRJoinInputUseOccurrence]
    output: ProjectIRJoinRowOutput
    matches: tuple[ProjectIRJoinMatchFieldPair, ...]
    kind: ProjectIRBinaryJoinKind = field(init=False)
    fanout: ProjectRelationshipFanoutEffect = field(init=False)
    survival: ProjectIRJoinRowSurvivalEffect = field(init=False)
    null_extension: ProjectIRJoinNullExtensionEffect = field(init=False)
    outer_join_barrier: ProjectIROuterJoinBarrier = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.identity) is not ProjectIRBinaryJoinIdentity
            or type(self.use) is not ProjectConcreteJoinUse
            or self.identity.use != self.use.identity
            or self.identity.path_step_position >= len(self.use.path.steps)
            or type(self.path_step) is not ProjectRelationshipPathStep
            or self.use.path.steps[self.identity.path_step_position]
            is not self.path_step
            or type(self.guarantee) is not ProjectDirectionalRelationshipMatchGuarantee
            or self.path_step.guarantee is not self.guarantee
        ):
            raise ValueError("Binary JOIN must retain its exact semantic path root.")
        if type(self.condition) is not ProjectConcreteRelationshipCondition or (
            self.condition.relationship.occurrence.identity
            != self.guarantee.direction.declaration
        ):
            raise ValueError("Binary JOIN requires its exact base-match condition.")
        if (
            type(self.node) is not ProjectIRPlanNodeOccurrence
            or self.node.anchor.identity != self.identity.use.owner
            or type(self.left_input) is not ProjectIROutputRelationalProperties
            or type(self.right_input) is not ProjectIROutputRelationalProperties
            or self.right_input is not self.guarantee.target_output
        ):
            raise ValueError("Binary JOIN requires exact node and input roots.")
        if (
            type(self.input_slots) is not tuple
            or len(self.input_slots) != 2
            or any(
                type(slot) is not ProjectIRInputSlotOccurrence
                for slot in self.input_slots
            )
            or tuple(slot.input_ordinal for slot in self.input_slots) != (0, 1)
            or any(slot.consumer is not self.node for slot in self.input_slots)
            or type(self.input_uses) is not tuple
            or len(self.input_uses) != 2
            or any(
                type(use) is not ProjectIRJoinInputUseOccurrence or use.slot is not slot
                for use, slot in zip(self.input_uses, self.input_slots, strict=True)
            )
            or self.input_uses[0].output is not self.left_input.output.occurrence
            or self.input_uses[1].output is not self.right_input.output.occurrence
        ):
            raise ValueError("Binary JOIN requires exactly two exact input uses.")
        if (
            type(self.output) is not ProjectIRJoinRowOutput
            or self.output.occurrence.producer is not self.node
            or type(self.matches) is not tuple
            or not self.matches
            or any(
                type(item) is not ProjectIRJoinMatchFieldPair for item in self.matches
            )
            or len(self.matches) != len(self.condition.correspondences)
        ):
            raise ValueError("Binary JOIN output and match evidence must be complete.")
        left_count = len(self.left_input.fields)
        row_fields = self.output.row_shape.fields
        if len(row_fields) != left_count + len(self.right_input.fields):
            raise ValueError("Binary JOIN output must contain exact left/right fields.")
        for correspondence, pair in zip(
            self.condition.correspondences, self.matches, strict=True
        ):
            source_reference, target_reference = _relationship_field_references(
                correspondence, self.guarantee
            )
            if (
                pair.correspondence is not correspondence
                or not 0 <= pair.left.field_position < left_count
                or not left_count <= pair.right.field_position < len(row_fields)
                or pair.left is not row_fields[pair.left.field_position]
                or pair.right is not row_fields[pair.right.field_position]
                or pair.left.evidence is not source_reference.semantic_field
                or pair.right.evidence is not target_reference.semantic_field
                or self.right_input.fields[
                    pair.right.field_position - left_count
                ].evidence
                is not target_reference.semantic_field
            ):
                raise ValueError("Binary JOIN match pairs must retain exact fields.")
        source_introduction = self.matches[0].left.introduction_use
        source_nulling = self.matches[0].left.nulling_joins
        if any(
            pair.left.introduction_use is not source_introduction
            or pair.left.nulling_joins != source_nulling
            for pair in self.matches
        ):
            raise ValueError("Binary JOIN matches require one exact source slice.")
        kind = ProjectIRBinaryJoinKind(self.use.kind.value)
        fanout, survival, null_extension, barrier = _join_effects(
            kind, self.guarantee, source_nulling
        )
        matched_left = {pair.left.field_position for pair in self.matches}
        matched_right = {
            pair.right.field_position - left_count for pair in self.matches
        }
        for position, incoming in enumerate(self.left_input.fields):
            retained = row_fields[position]
            if type(self.left_input.output) is ProjectIRJoinRowOutput:
                prior = self.left_input.output.row_shape.fields[position]
                introduction = prior.introduction_use
                nulling = prior.nulling_joins
                nullability = prior.effective_nullability
            else:
                introduction = self.input_uses[0]
                nulling = ()
                nullability = incoming.effective_nullability
            if (
                kind is ProjectIRBinaryJoinKind.INNER
                and position in matched_left
                and not nulling
            ):
                nullability = ProjectRowFieldNullability.NON_NULL
            if (
                retained.evidence is not incoming.evidence
                or retained.introduction_use is not introduction
                or retained.nulling_joins != nulling
                or retained.effective_nullability is not nullability
            ):
                raise ValueError(
                    "Binary JOIN left fields must retain exact provenance."
                )
        right_nulling = (
            (*source_nulling, self.node.ref)
            if null_extension is ProjectIRJoinNullExtensionEffect.MAY_NULL_EXTEND_RIGHT
            else ()
        )
        for position, incoming in enumerate(self.right_input.fields):
            retained = row_fields[left_count + position]
            nullability = (
                ProjectRowFieldNullability.NULLABLE
                if right_nulling
                else (
                    ProjectRowFieldNullability.NON_NULL
                    if position in matched_right
                    else incoming.effective_nullability
                )
            )
            if (
                retained.evidence is not incoming.evidence
                or retained.introduction_use is not self.input_uses[1]
                or retained.nulling_joins != right_nulling
                or retained.effective_nullability is not nullability
            ):
                raise ValueError(
                    "Binary JOIN right fields must retain exact provenance."
                )
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "fanout", fanout)
        object.__setattr__(self, "survival", survival)
        object.__setattr__(self, "null_extension", null_extension)
        object.__setattr__(self, "outer_join_barrier", barrier)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRJoinStructuralStage:
    base: ProjectIRStructuralStage = field(repr=False, compare=False, hash=False)
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    nodes: tuple[ProjectIRPlanNodeOccurrence, ...]
    outputs: tuple[ProjectIROutputValueOccurrence, ...]
    input_slots: tuple[ProjectIRInputSlotOccurrence, ...]
    uses: tuple[ProjectIRJoinInputUseOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.base) is not ProjectIRStructuralStage:
            raise TypeError("JOIN structure requires the exact base structural stage.")
        if not (
            type(self.starting_allocation) is ProjectIRAllocationState
            and type(self.ending_allocation) is ProjectIRAllocationState
            and self.starting_allocation.scope
            is self.ending_allocation.scope
            is self.base.scope
        ):
            raise ValueError("JOIN structure requires one exact snapshot scope.")
        for values, expected, label in (
            (self.nodes, ProjectIRPlanNodeOccurrence, "nodes"),
            (self.outputs, ProjectIROutputValueOccurrence, "outputs"),
            (self.input_slots, ProjectIRInputSlotOccurrence, "input slots"),
            (self.uses, ProjectIRJoinInputUseOccurrence, "uses"),
        ):
            if type(values) is not tuple or any(
                type(item) is not expected for item in values
            ):
                raise TypeError(f"JOIN structural {label} must be an exact tuple.")
        if tuple(node.ref.position for node in self.nodes) != tuple(
            range(
                self.starting_allocation.next_plan_node_position,
                self.ending_allocation.next_plan_node_position,
            )
        ):
            raise ValueError("JOIN nodes must continue the exact allocation order.")
        if tuple(output.ref.position for output in self.outputs) != tuple(
            range(
                self.starting_allocation.next_output_value_position,
                self.ending_allocation.next_output_value_position,
            )
        ):
            raise ValueError("JOIN outputs must continue the exact allocation order.")
        if tuple(slot.ref.position for slot in self.input_slots) != tuple(
            range(
                self.starting_allocation.next_input_slot_position,
                self.ending_allocation.next_input_slot_position,
            )
        ) or tuple(use.ref.position for use in self.uses) != tuple(
            range(
                self.starting_allocation.next_use_position,
                self.ending_allocation.next_use_position,
            )
        ):
            raise ValueError("JOIN slots and uses must continue exact allocation.")
        if not (
            len(self.nodes) == len(self.outputs)
            and len(self.input_slots) == len(self.uses) == 2 * len(self.nodes)
        ):
            raise ValueError("Every binary JOIN requires one output and two inputs.")
        for position, node in enumerate(self.nodes):
            slots = self.input_slots[2 * position : 2 * position + 2]
            uses = self.uses[2 * position : 2 * position + 2]
            available_outputs = (*self.base.outputs, *self.outputs[:position])
            if (
                self.outputs[position].producer is not node
                or tuple(slot.input_ordinal for slot in slots) != (0, 1)
                or any(slot.consumer is not node for slot in slots)
                or any(
                    use.slot is not slot for use, slot in zip(uses, slots, strict=True)
                )
                or any(
                    not any(use.output is output for output in available_outputs)
                    for use in uses
                )
            ):
                raise ValueError("JOIN structural objects must retain exact topology.")


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
class ProjectIRJoinGrainWitness:
    join: ProjectIRBinaryJoinIdentity
    left: ProjectIRProvidedIntrinsicGrain = field(repr=False, compare=False, hash=False)
    right: ProjectIRProvidedIntrinsicGrain = field(
        repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        if (
            type(self.join) is not ProjectIRBinaryJoinIdentity
            or type(self.left) is not ProjectIRProvidedIntrinsicGrain
            or type(self.right) is not ProjectIRProvidedIntrinsicGrain
            or self.left.origin_set is not self.right.origin_set
        ):
            raise ValueError("JOIN grain witness requires exact compatible inputs.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRJoinOutputProperties:
    join: ProjectIRBinaryJoinOccurrence = field(repr=False, compare=False, hash=False)
    relational: ProjectIROutputRelationalProperties
    null_extension: (
        ProjectIRProvidedNullExtension | ProjectIRJoinUnavailableProperty
    ) = field(init=False)
    ordering: ProjectIRJoinUnavailableProperty = field(init=False)

    def __post_init__(self) -> None:
        output = self.join.output
        if (
            type(self.join) is not ProjectIRBinaryJoinOccurrence
            or type(self.relational) is not ProjectIROutputRelationalProperties
            or self.relational.output is not output
        ):
            raise ValueError("JOIN relational properties require the exact output.")
        shape_fields = output.row_shape.fields
        if len(self.relational.fields) != len(shape_fields) or any(
            item.field_position != position
            or item.evidence is not shape.evidence
            or item.effective_nullability is not shape.effective_nullability
            for position, (item, shape) in enumerate(
                zip(self.relational.fields, shape_fields, strict=True)
            )
        ):
            raise ValueError(
                "JOIN relational fields must retain exact output evidence."
            )
        witness = self.relational.grain.witness
        if (
            type(witness) is not ProjectIRJoinGrainWitness
            or witness.join != self.join.identity
            or witness.left is not self.join.left_input.grain
            or witness.right is not self.join.right_input.grain
        ):
            raise ValueError("JOIN grain must retain its exact binary input witness.")
        null_extension: (
            ProjectIRProvidedNullExtension | ProjectIRJoinUnavailableProperty
        )
        if any(item.nulling_joins for item in shape_fields):
            null_extension = ProjectIRProvidedNullExtension(output=output)
        else:
            null_extension = ProjectIRJoinUnavailableProperty(
                output=output,
                property_slot=ProjectIRProvidedPropertySlot.NULL_EXTENSION,
            )
        object.__setattr__(self, "null_extension", null_extension)
        object.__setattr__(
            self,
            "ordering",
            ProjectIRJoinUnavailableProperty(
                output=output,
                property_slot=ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING,
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRConcreteJoinRegion:
    ledger: ProjectRelationJoinUseLedger = field(repr=False, compare=False, hash=False)
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    joins: tuple[ProjectIRBinaryJoinOccurrence, ...]

    def __post_init__(self) -> None:
        if (
            type(self.ledger) is not ProjectRelationJoinUseLedger
            or type(self.starting_allocation) is not ProjectIRAllocationState
            or type(self.ending_allocation) is not ProjectIRAllocationState
            or self.starting_allocation.scope is not self.ending_allocation.scope
            or type(self.joins) is not tuple
            or any(
                type(join) is not ProjectIRBinaryJoinOccurrence for join in self.joins
            )
            or any(type(use) is not ProjectConcreteJoinUse for use in self.ledger.uses)
            or not self.joins
        ):
            raise ValueError("Concrete JOIN region requires every authored path step.")
        expected = tuple(
            (use, position, step)
            for use in self.ledger.uses
            for position, step in enumerate(
                cast(ProjectConcreteJoinUse, use).path.steps
            )
        )
        if len(self.joins) != len(expected) or any(
            join.use is not use
            or join.identity.path_step_position != position
            or join.path_step is not step
            for join, (use, position, step) in zip(self.joins, expected, strict=True)
        ):
            raise ValueError(
                "Concrete JOIN region must retain canonical use/step order."
            )
        count = len(self.joins)
        if (
            self.ending_allocation.next_plan_node_position
            != self.starting_allocation.next_plan_node_position + count
            or self.ending_allocation.next_output_value_position
            != self.starting_allocation.next_output_value_position + count
            or self.ending_allocation.next_input_slot_position
            != self.starting_allocation.next_input_slot_position + 2 * count
            or self.ending_allocation.next_use_position
            != self.starting_allocation.next_use_position + 2 * count
        ):
            raise ValueError(
                "Concrete JOIN region must consume exact binary allocation."
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


type ProjectIRJoinRegion = ProjectIRConcreteJoinRegion | ProjectIRNonConcreteJoinRegion


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRJoinRelationalPropertyExtension:
    base: ProjectIRRelationalPropertyStage = field(
        repr=False, compare=False, hash=False
    )
    structural: ProjectIRJoinStructuralStage = field(
        repr=False, compare=False, hash=False
    )
    outputs: tuple[ProjectIRJoinOutputProperties, ...]

    def __post_init__(self) -> None:
        if (
            type(self.base) is not ProjectIRRelationalPropertyStage
            or (type(self.structural) is not ProjectIRJoinStructuralStage)
            or (
                self.structural.base
                is not self.base.analyses.stage.project_plan.structural_stage
            )
        ):
            raise TypeError("JOIN property extension requires exact base roots.")
        if (
            type(self.outputs) is not tuple
            or any(
                type(item) is not ProjectIRJoinOutputProperties for item in self.outputs
            )
            or len(self.outputs) != len(self.structural.nodes)
            or any(
                item.join.node is not node or item.join.output.occurrence is not output
                for item, node, output in zip(
                    self.outputs,
                    self.structural.nodes,
                    self.structural.outputs,
                    strict=True,
                )
            )
        ):
            raise ValueError("JOIN properties must cover every binary node once.")


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
    structural: ProjectIRJoinStructuralStage
    properties: ProjectIRJoinRelationalPropertyExtension

    def __post_init__(self) -> None:
        if (
            type(self.base_plan) is not ProjectIRProjectPlan
            or type(self.base_relational) is not ProjectIRRelationalPropertyStage
            or self.base_relational.analyses.stage.project_plan is not self.base_plan
            or type(self.uses) is not ProjectRelationshipUseSet
            or self.uses.relationships.semantic_result.module_semantic_facts
            is not self.base_plan.semantic_facts
            or self.starting_allocation is not self.base_plan.ending_allocation
        ):
            raise ValueError("JOIN region requires exact base plan/property/use roots.")
        if (
            type(self.ending_allocation) is not ProjectIRAllocationState
            or type(self.regions) is not tuple
            or any(
                type(region)
                not in {ProjectIRConcreteJoinRegion, ProjectIRNonConcreteJoinRegion}
                for region in self.regions
            )
            or len(self.regions) != len(self.uses.ledgers)
            or any(
                region.ledger is not ledger
                for region, ledger in zip(self.regions, self.uses.ledgers, strict=True)
            )
        ):
            raise ValueError("JOIN regions must retain declaration order.")
        if (
            type(self.structural) is not ProjectIRJoinStructuralStage
            or type(self.properties) is not ProjectIRJoinRelationalPropertyExtension
            or self.structural.base is not self.base_plan.structural_stage
            or self.structural.starting_allocation is not self.starting_allocation
            or self.structural.ending_allocation is not self.ending_allocation
            or self.properties.base is not self.base_relational
            or self.properties.structural is not self.structural
        ):
            raise ValueError("JOIN stage products must retain exact continuity.")
        current = self.starting_allocation
        for region in self.regions:
            if region.starting_allocation is not current:
                raise ValueError(
                    "JOIN regions must retain exact allocation continuity."
                )
            current = region.ending_allocation
        if current is not self.ending_allocation:
            raise ValueError("JOIN regions must end at the exact stage allocation.")
        joins = tuple(
            join
            for region in self.regions
            if type(region) is ProjectIRConcreteJoinRegion
            for join in region.joins
        )
        if (
            len(joins) != len(self.properties.outputs)
            or any(
                output.join is not join
                for output, join in zip(self.properties.outputs, joins, strict=True)
            )
            or not _same_objects(
                cast(tuple[object, ...], tuple(join.node for join in joins)),
                cast(tuple[object, ...], self.structural.nodes),
            )
            or not _same_objects(
                cast(
                    tuple[object, ...],
                    tuple(join.output.occurrence for join in joins),
                ),
                cast(tuple[object, ...], self.structural.outputs),
            )
            or not _same_objects(
                cast(
                    tuple[object, ...],
                    tuple(slot for join in joins for slot in join.input_slots),
                ),
                cast(tuple[object, ...], self.structural.input_slots),
            )
            or not _same_objects(
                cast(
                    tuple[object, ...],
                    tuple(use for join in joins for use in join.input_uses),
                ),
                cast(tuple[object, ...], self.structural.uses),
            )
        ):
            raise ValueError("JOIN stage must retain one exact flattened product.")
        _validate_join_stage_topology(self)


def _dominant_region_state(
    blockers: tuple[ProjectNonConcreteJoinUse, ...],
) -> ProjectJoinUseState:
    states = {item.state for item in blockers}
    if ProjectJoinUseState.AMBIGUOUS in states:
        return ProjectJoinUseState.AMBIGUOUS
    if ProjectJoinUseState.BLOCKED in states:
        return ProjectJoinUseState.BLOCKED
    return ProjectJoinUseState.UNKNOWN


def _condition(
    uses: ProjectRelationshipUseSet,
    guarantee: ProjectDirectionalRelationshipMatchGuarantee,
) -> ProjectConcreteRelationshipCondition:
    matches = tuple(
        item
        for item in uses.index.guarantees.conditions.conditions
        if type(item) is ProjectConcreteRelationshipCondition
        and item.relationship.occurrence.identity == guarantee.direction.declaration
    )
    if len(matches) != 1:
        raise ValueError("Binary JOIN requires one exact concrete condition.")
    return matches[0]


def _reverse_guarantee(
    uses: ProjectRelationshipUseSet,
    guarantee: ProjectDirectionalRelationshipMatchGuarantee,
) -> ProjectDirectionalRelationshipMatchGuarantee:
    matches = tuple(
        item
        for item in uses.index.by_declaration[guarantee.direction.declaration]
        if item.direction.source is guarantee.direction.target
        and item.direction.target is guarantee.direction.source
    )
    if len(matches) != 1:
        raise ValueError("Binary JOIN requires one exact reverse direction.")
    return matches[0]


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


def _class_for_field(
    classes: tuple[ProjectIROutputValueClass, ...],
    field: ProjectIRJoinedRowField,
) -> ProjectIROutputValueClass:
    matches = tuple(
        item
        for item in classes
        if any(member.field_position == field.field_position for member in item.members)
    )
    if len(matches) != 1:
        raise ValueError("JOIN field requires one exact output-local value class.")
    return matches[0]


def _source_slice_fields(
    join: ProjectIRBinaryJoinOccurrence,
) -> tuple[ProjectIRJoinedRowField, ...]:
    introduction = join.matches[0].left.introduction_use
    return tuple(
        item
        for item in join.output.row_shape.fields[: len(join.left_input.fields)]
        if item.introduction_use is introduction
    )


def _all_non_null(value_class: ProjectIROutputValueClass) -> bool:
    return all(
        member.effective_nullability is ProjectRowFieldNullability.NON_NULL
        for member in value_class.members
    )


def _base_factor(
    identity: ProjectGrainFactorIdentity,
) -> ProjectBaseGrainFactorIdentity:
    if type(identity) is ProjectJoinGrainFactorIdentity:
        return identity.base
    return cast(ProjectBaseGrainFactorIdentity, identity)


def _grain(
    *,
    join_identity: ProjectIRBinaryJoinIdentity,
    output: ProjectIRJoinRowOutput,
    left: ProjectIRProvidedIntrinsicGrain,
    right: ProjectIRProvidedIntrinsicGrain,
    left_use: ProjectIRJoinInputUseOccurrence,
    right_use: ProjectIRJoinInputUseOccurrence,
    source_factors: tuple[ProjectGrainFactorIdentity, ...] | None,
    nulling: tuple[ProjectIRPlanNodeRef, ...],
    forward_at_most_one: bool,
    reverse_at_most_one: bool,
) -> tuple[ProjectIRProvidedIntrinsicGrain, tuple[ProjectGrainFactorIdentity, ...]]:
    if left.origin_set is not right.origin_set:
        raise ValueError("JOIN grain transfer requires one exact origin set.")
    left_images: dict[ProjectGrainFactorIdentity, ProjectGrainFactorIdentity] = {}
    for factor in left.factors:
        identity = factor.identity
        left_images[identity] = (
            identity
            if type(identity) is ProjectJoinGrainFactorIdentity
            else ProjectJoinGrainFactorIdentity(
                base=_base_factor(identity),
                introduction_use=left_use.ref,
                nulling_joins=(),
            )
        )
    right_images = {
        factor.identity: ProjectJoinGrainFactorIdentity(
            base=_base_factor(factor.identity),
            introduction_use=right_use.ref,
            nulling_joins=nulling,
        )
        for factor in right.factors
    }
    left_active = tuple(left_images[item] for item in left.active)
    right_active = tuple(right_images[item] for item in right.active)
    active = (*left_active, *right_active)
    factor_identities = (
        *(left_images[item.identity] for item in left.factors),
        *(right_images[item.identity] for item in right.factors),
    )
    factors = tuple(
        ProjectGrainDomainFactor(identity=item) for item in factor_identities
    )
    dependencies: list[ProjectGrainDependencyFact] = []
    for fact, images in (
        *((fact, left_images) for fact in left.dependencies),
        *((fact, right_images) for fact in right.dependencies),
    ):
        dependencies.append(
            ProjectGrainDependencyFact(
                determinants=tuple(images[item] for item in fact.determinants),
                dependents=tuple(images[item] for item in fact.dependents),
            )
        )
    effective_source_factors = left_active if source_factors is None else source_factors
    if forward_at_most_one and effective_source_factors and right_active:
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
    state = (
        ProjectGrainBasisState.FACTORIZED if active else ProjectGrainBasisState.GLOBAL
    )
    return (
        ProjectIRProvidedIntrinsicGrain(
            output=output,
            state=state,
            factors=factors,
            active=active,
            dependencies=tuple(dependencies),
            origin_set=left.origin_set,
            witness=ProjectIRJoinGrainWitness(
                join=join_identity, left=left, right=right
            ),
        ),
        right_active,
    )


def _build_relational_properties(
    *,
    join: ProjectIRBinaryJoinOccurrence,
    left: ProjectIROutputRelationalProperties,
    right: ProjectIROutputRelationalProperties,
    source_factors: tuple[ProjectGrainFactorIdentity, ...] | None,
    right_nulling: tuple[ProjectIRPlanNodeRef, ...],
    reverse: ProjectDirectionalRelationshipMatchGuarantee,
) -> tuple[ProjectIROutputRelationalProperties, tuple[ProjectGrainFactorIdentity, ...]]:
    output = join.output
    fields = _field_occurrences(output)
    left_classes, left_images = _classes_for_output(
        old=left.value_classes, output=output, fields=fields, offset=0
    )
    right_offset = len(left.fields)
    right_classes, right_images = _classes_for_output(
        old=right.value_classes,
        output=output,
        fields=fields,
        offset=right_offset,
    )
    classes = (*left_classes, *right_classes)
    source_classes = _ordered_classes(
        tuple(_class_for_field(classes, pair.left) for pair in join.matches),
        classes,
    )
    source_binding_classes = _ordered_classes(
        tuple(_class_for_field(classes, item) for item in _source_slice_fields(join)),
        classes,
    )
    right_match_classes = _ordered_classes(
        tuple(_class_for_field(classes, pair.right) for pair in join.matches), classes
    )
    left_keys = tuple(
        _image_key(
            key,
            left_images,
            classes,
            output=output,
            support=join,
        )
        for key in left.keys
    )
    right_key_images: list[ProjectIROutputCandidateKey] = []
    actual_nulling = (
        join.null_extension is ProjectIRJoinNullExtensionEffect.MAY_NULL_EXTEND_RIGHT
    )
    for key in right.keys:
        right_key_images.append(
            _image_key(
                key,
                right_images,
                classes,
                output=output,
                force_lax=actual_nulling,
                support=join,
            )
        )
    forward_at_most_one = (
        join.guarantee.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    )
    reverse_at_most_one = reverse.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    candidates: list[ProjectIROutputCandidateKey] = []
    if forward_at_most_one:
        candidates.extend(left_keys)
    source_is_key = any(
        set(key.determinants) == set(source_classes) for key in left_keys
    )
    if reverse_at_most_one and source_is_key:
        candidates.extend(right_key_images)
    for left_key in left_keys:
        for right_key in right_key_images:
            determinants = _ordered_classes(
                (*left_key.determinants, *right_key.determinants), classes
            )
            strength = (
                ProjectRowUniquenessStrength.STRICT
                if (
                    left_key.strength is ProjectRowUniquenessStrength.STRICT
                    and right_key.strength is ProjectRowUniquenessStrength.STRICT
                )
                or all(_all_non_null(item) for item in determinants)
                else ProjectRowUniquenessStrength.LAX
            )
            candidates.append(
                ProjectIROutputCandidateKey(
                    output=output,
                    determinants=determinants,
                    strength=strength,
                    supports=(left_key, right_key, join),
                )
            )
    keys = _frontier(tuple(candidates))
    fds: list[ProjectIROutputValueFD] = []
    for fact in left.fds:
        image = _image_fd(
            fact,
            left_images,
            classes,
            output=output,
            strength=fact.strength,
            support=join,
        )
        if image is not None:
            fds.append(image)
    for fact in right.fds:
        strength = fact.strength
        if actual_nulling and strength is ProjectRowUniquenessStrength.STRICT:
            if not all(_all_non_null(item) for item in fact.determinants):
                strength = ProjectRowUniquenessStrength.LAX
        image = _image_fd(
            fact,
            right_images,
            classes,
            output=output,
            strength=strength,
            support=join,
        )
        if image is not None:
            fds.append(image)
    right_all = tuple(right_classes)
    if forward_at_most_one and source_classes and right_all:
        fds.append(
            ProjectIROutputValueFD(
                output=output,
                determinants=source_classes,
                dependents=right_all,
                strength=ProjectRowUniquenessStrength.STRICT,
                supports=(join.guarantee, join),
            )
        )
    if reverse_at_most_one and right_match_classes and source_binding_classes:
        fds.append(
            ProjectIROutputValueFD(
                output=output,
                determinants=right_match_classes,
                dependents=source_binding_classes,
                strength=(
                    ProjectRowUniquenessStrength.LAX
                    if actual_nulling
                    else ProjectRowUniquenessStrength.STRICT
                ),
                supports=(reverse, join),
            )
        )
    if join.kind is ProjectIRBinaryJoinKind.INNER or not actual_nulling:
        for pair in join.matches:
            left_class = _class_for_field(classes, pair.left)
            right_class = _class_for_field(classes, pair.right)
            fds.extend(
                (
                    ProjectIROutputValueFD(
                        output=output,
                        determinants=(left_class,),
                        dependents=(right_class,),
                        strength=ProjectRowUniquenessStrength.STRICT,
                        supports=(pair.correspondence, join),
                    ),
                    ProjectIROutputValueFD(
                        output=output,
                        determinants=(right_class,),
                        dependents=(left_class,),
                        strength=ProjectRowUniquenessStrength.STRICT,
                        supports=(pair.correspondence, join),
                    ),
                )
            )
    fds = list(_key_fds(output, classes, keys, tuple(fds)))
    fd_index = _compile_output_fd_index(output, classes, tuple(fds))
    grain, right_factors = _grain(
        join_identity=join.identity,
        output=output,
        left=left.grain,
        right=right.grain,
        left_use=join.input_uses[0],
        right_use=join.input_uses[1],
        source_factors=source_factors,
        nulling=right_nulling,
        forward_at_most_one=forward_at_most_one,
        reverse_at_most_one=reverse_at_most_one,
    )
    return (
        ProjectIROutputRelationalProperties(
            output=output,
            fields=fields,
            value_classes=classes,
            keys=keys,
            fds=tuple(fds),
            fd_index=fd_index,
            grain=grain,
        ),
        right_factors,
    )


def _matched_field_positions(
    condition: ProjectConcreteRelationshipCondition,
    guarantee: ProjectDirectionalRelationshipMatchGuarantee,
    source_fields: tuple[ProjectIRJoinedRowField, ...],
    right: ProjectIROutputRelationalProperties,
) -> tuple[tuple[int, int, ProjectRelationshipEqualityCorrespondence], ...]:
    result: list[tuple[int, int, ProjectRelationshipEqualityCorrespondence]] = []
    for correspondence in condition.correspondences:
        source_reference, target_reference = _relationship_field_references(
            correspondence, guarantee
        )
        left_matches = tuple(
            field
            for field in source_fields
            if field.evidence is source_reference.semantic_field
        )
        right_matches = tuple(
            field
            for field in right.fields
            if field.evidence is target_reference.semantic_field
        )
        if len(left_matches) != 1 or len(right_matches) != 1:
            raise ValueError("JOIN correspondence requires exact field instances.")
        result.append(
            (
                left_matches[0].field_position,
                right_matches[0].field_position,
                correspondence,
            )
        )
    return tuple(result)


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _validate_join_stage_topology(stage: ProjectIRJoinRegionStage) -> None:
    property_position = 0
    for region in stage.regions:
        if type(region) is ProjectIRNonConcreteJoinRegion:
            continue
        region = cast(ProjectIRConcreteJoinRegion, region)
        base_binding = region.ledger.bindings[0]
        if base_binding.output is None:
            raise ValueError("Concrete JOIN region requires a concrete base binding.")
        accumulated = base_binding.output
        binding_positions: dict[int, tuple[int, ...]] = {
            id(base_binding): tuple(range(len(accumulated.fields)))
        }
        join_position = 0
        for authored_use in region.ledger.uses:
            use = cast(ProjectConcreteJoinUse, authored_use)
            source_positions = binding_positions[id(use.source_binding)]
            for path_step in use.path.steps:
                join = region.joins[join_position]
                output_properties = stage.properties.outputs[property_position]
                if (
                    join.use is not use
                    or join.path_step is not path_step
                    or join.condition is not _condition(stage.uses, path_step.guarantee)
                    or join.left_input is not accumulated
                    or output_properties.join is not join
                ):
                    raise ValueError(
                        "JOIN stage topology must retain exact semantic roots."
                    )
                source_fields = tuple(
                    join.output.row_shape.fields[position]
                    for position in source_positions
                )
                expected_matches = _matched_field_positions(
                    join.condition,
                    join.guarantee,
                    source_fields,
                    join.right_input,
                )
                offset = len(join.left_input.fields)
                if len(join.matches) != len(expected_matches) or any(
                    pair.correspondence is not correspondence
                    or pair.left is not join.output.row_shape.fields[left_position]
                    or pair.right
                    is not join.output.row_shape.fields[offset + right_position]
                    for pair, (left_position, right_position, correspondence) in zip(
                        join.matches, expected_matches, strict=True
                    )
                ):
                    raise ValueError(
                        "JOIN stage matches must use the exact binding slice."
                    )
                if not _same_objects(
                    cast(tuple[object, ...], _source_slice_fields(join)),
                    cast(tuple[object, ...], source_fields),
                ):
                    raise ValueError("JOIN source slice must retain every exact field.")
                accumulated = output_properties.relational
                source_positions = tuple(
                    range(offset, offset + len(join.right_input.fields))
                )
                join_position += 1
                property_position += 1
            binding_positions[id(use.target_binding)] = source_positions
        region_uses = tuple(use for join in region.joins for use in join.input_uses)
        region_node_refs = tuple(join.node.ref for join in region.joins)
        for output_properties in stage.properties.outputs[
            property_position - len(region.joins) : property_position
        ]:
            for joined_field in output_properties.join.output.row_shape.fields:
                if not any(
                    joined_field.introduction_use is use for use in region_uses
                ) or any(
                    not any(ref == retained for retained in region_node_refs)
                    for ref in joined_field.nulling_joins
                ):
                    raise ValueError(
                        "JOIN field provenance must belong to its exact region."
                    )
            factor_identities = tuple(
                factor.identity for factor in output_properties.relational.grain.factors
            )
            if any(
                type(identity) is not ProjectJoinGrainFactorIdentity
                or not any(identity.introduction_use == use.ref for use in region_uses)
                or any(
                    not any(ref == retained for retained in region_node_refs)
                    for ref in identity.nulling_joins
                )
                for identity in factor_identities
            ) or any(
                item not in factor_identities
                for dependency in output_properties.relational.grain.dependencies
                for item in (*dependency.determinants, *dependency.dependents)
            ):
                raise ValueError(
                    "JOIN grain provenance must belong to its exact region."
                )
    if property_position != len(stage.properties.outputs):
        raise ValueError("JOIN topology must consume every property output once.")


def _build_join(
    *,
    uses: ProjectRelationshipUseSet,
    use: ProjectConcreteJoinUse,
    path_step: ProjectRelationshipPathStep,
    left: ProjectIROutputRelationalProperties,
    right: ProjectIROutputRelationalProperties,
    source_positions: tuple[int, ...],
    source_nulling: tuple[ProjectIRPlanNodeRef, ...],
    source_factors: tuple[ProjectGrainFactorIdentity, ...] | None,
    allocation: ProjectIRAllocationState,
) -> tuple[
    ProjectIRBinaryJoinOccurrence,
    ProjectIRJoinOutputProperties,
    ProjectIRAllocationState,
    tuple[int, ...],
    tuple[ProjectIRPlanNodeRef, ...],
    tuple[ProjectGrainFactorIdentity, ...],
]:
    guarantee = path_step.guarantee
    condition = _condition(uses, guarantee)
    reverse = _reverse_guarantee(uses, guarantee)
    anchor = ProjectIRRelationAnchor(identity=use.identity.owner)
    node = ProjectIRPlanNodeOccurrence(
        ref=ProjectIRPlanNodeRef(
            scope=allocation.scope,
            position=allocation.next_plan_node_position,
        ),
        anchor=anchor,
    )
    slots = tuple(
        ProjectIRInputSlotOccurrence(
            ref=ProjectIRInputSlotRef(
                scope=allocation.scope,
                position=allocation.next_input_slot_position + ordinal,
            ),
            consumer=node,
            input_ordinal=ordinal,
        )
        for ordinal in (0, 1)
    )
    input_outputs = (left.output.occurrence, right.output.occurrence)
    input_uses = tuple(
        ProjectIRJoinInputUseOccurrence(
            ref=ProjectIRUseRef(
                scope=allocation.scope,
                position=allocation.next_use_position + ordinal,
            ),
            output=input_outputs[ordinal],
            slot=slots[ordinal],
        )
        for ordinal in (0, 1)
    )
    source_fields = tuple(
        (
            cast(ProjectIRJoinRowOutput, left.output).row_shape.fields[position]
            if type(left.output) is ProjectIRJoinRowOutput
            else ProjectIRJoinedRowField(
                field_position=position,
                evidence=left.fields[position].evidence,
                introduction_use=input_uses[0],
                nulling_joins=(),
                effective_nullability=left.fields[position].effective_nullability,
            )
        )
        for position in source_positions
    )
    matched = _matched_field_positions(condition, guarantee, source_fields, right)
    matched_left = {item[0] for item in matched}
    matched_right = {item[1] for item in matched}
    kind = ProjectIRBinaryJoinKind(use.kind.value)
    _, _, null_extension, _ = _join_effects(kind, guarantee, source_nulling)
    actual_nulling = (
        null_extension is ProjectIRJoinNullExtensionEffect.MAY_NULL_EXTEND_RIGHT
    )
    right_nulling = (*source_nulling, node.ref) if actual_nulling else ()
    left_fields: list[ProjectIRJoinedRowField] = []
    for position, item in enumerate(left.fields):
        if type(left.output) is ProjectIRJoinRowOutput:
            old = left.output.row_shape.fields[position]
            introduction = old.introduction_use
            nulling = old.nulling_joins
            nullability = old.effective_nullability
        else:
            introduction = input_uses[0]
            nulling = ()
            nullability = item.effective_nullability
        if (
            kind is ProjectIRBinaryJoinKind.INNER
            and position in matched_left
            and not nulling
        ):
            nullability = ProjectRowFieldNullability.NON_NULL
        left_fields.append(
            ProjectIRJoinedRowField(
                field_position=position,
                evidence=item.evidence,
                introduction_use=introduction,
                nulling_joins=nulling,
                effective_nullability=nullability,
            )
        )
    offset = len(left_fields)
    right_fields = tuple(
        ProjectIRJoinedRowField(
            field_position=offset + position,
            evidence=item.evidence,
            introduction_use=input_uses[1],
            nulling_joins=right_nulling,
            effective_nullability=(
                ProjectRowFieldNullability.NULLABLE
                if actual_nulling
                else (
                    ProjectRowFieldNullability.NON_NULL
                    if position in matched_right
                    else item.effective_nullability
                )
            ),
        )
        for position, item in enumerate(right.fields)
    )
    shape = ProjectIRJoinedRowShape(
        relation=anchor,
        producer=node,
        fields=(*left_fields, *right_fields),
    )
    output = ProjectIRJoinRowOutput(
        occurrence=ProjectIROutputValueOccurrence(
            ref=ProjectIROutputValueRef(
                scope=allocation.scope,
                position=allocation.next_output_value_position,
            ),
            producer=node,
            anchor=anchor,
        ),
        row_shape=shape,
    )
    pairs = tuple(
        ProjectIRJoinMatchFieldPair(
            correspondence=correspondence,
            left=shape.fields[left_position],
            right=shape.fields[offset + right_position],
        )
        for left_position, right_position, correspondence in matched
    )
    identity = ProjectIRBinaryJoinIdentity(
        use=use.identity,
        path_step_position=path_step.position,
    )
    join = ProjectIRBinaryJoinOccurrence(
        identity=identity,
        use=use,
        path_step=path_step,
        guarantee=guarantee,
        condition=condition,
        node=node,
        left_input=left,
        right_input=right,
        input_slots=cast(
            tuple[ProjectIRInputSlotOccurrence, ProjectIRInputSlotOccurrence], slots
        ),
        input_uses=cast(
            tuple[ProjectIRJoinInputUseOccurrence, ProjectIRJoinInputUseOccurrence],
            input_uses,
        ),
        output=output,
        matches=pairs,
    )
    relational, right_factors = _build_relational_properties(
        join=join,
        left=left,
        right=right,
        source_factors=source_factors,
        right_nulling=right_nulling,
        reverse=reverse,
    )
    properties = ProjectIRJoinOutputProperties(
        join=join,
        relational=relational,
    )
    ending = ProjectIRAllocationState(
        scope=allocation.scope,
        next_plan_node_position=allocation.next_plan_node_position + 1,
        next_output_value_position=allocation.next_output_value_position + 1,
        next_input_slot_position=allocation.next_input_slot_position + 2,
        next_use_position=allocation.next_use_position + 2,
    )
    right_positions = tuple(range(offset, offset + len(right.fields)))
    return (
        join,
        properties,
        ending,
        right_positions,
        right_nulling,
        right_factors,
    )


def build_project_ir_join_region(
    *,
    base_plan: ProjectIRProjectPlan,
    base_relational: ProjectIRRelationalPropertyStage,
    uses: ProjectRelationshipUseSet,
    allocation: ProjectIRAllocationState,
) -> ProjectIRJoinRegionStage:
    """Extend one exact base plan with canonical all-or-none binary JOIN regions."""

    if (
        type(base_plan) is not ProjectIRProjectPlan
        or type(base_relational) is not ProjectIRRelationalPropertyStage
        or base_relational.analyses.stage.project_plan is not base_plan
        or type(uses) is not ProjectRelationshipUseSet
        or uses.relationships.semantic_result.module_semantic_facts
        is not base_plan.semantic_facts
        or allocation is not base_plan.ending_allocation
    ):
        raise ValueError(
            "JOIN construction requires exact base plan/property/use roots."
        )
    current = allocation
    regions: list[ProjectIRJoinRegion] = []
    joins: list[ProjectIRBinaryJoinOccurrence] = []
    properties: list[ProjectIRJoinOutputProperties] = []
    for ledger in uses.ledgers:
        blockers = tuple(
            use for use in ledger.uses if type(use) is ProjectNonConcreteJoinUse
        )
        if blockers:
            regions.append(
                ProjectIRNonConcreteJoinRegion(
                    ledger=ledger,
                    starting_allocation=current,
                )
            )
            continue
        region_start = current
        base_binding = ledger.bindings[0]
        if base_binding.output is None:
            raise ValueError("Concrete JOIN region requires a concrete base binding.")
        accumulated = base_binding.output
        binding_positions: dict[int, tuple[int, ...]] = {
            id(base_binding): tuple(range(len(accumulated.fields)))
        }
        binding_nulling: dict[int, tuple[ProjectIRPlanNodeRef, ...]] = {
            id(base_binding): ()
        }
        binding_factors: dict[int, tuple[ProjectGrainFactorIdentity, ...]] = {}
        region_joins: list[ProjectIRBinaryJoinOccurrence] = []
        for authored_use in ledger.uses:
            use = cast(ProjectConcreteJoinUse, authored_use)
            source_positions = binding_positions[id(use.source_binding)]
            source_nulling = binding_nulling[id(use.source_binding)]
            source_factors = binding_factors.get(id(use.source_binding))
            for step_position, path_step in enumerate(use.path.steps):
                right = path_step.guarantee.target_output
                built = _build_join(
                    uses=uses,
                    use=use,
                    path_step=path_step,
                    left=accumulated,
                    right=right,
                    source_positions=source_positions,
                    source_nulling=source_nulling,
                    source_factors=source_factors,
                    allocation=current,
                )
                (
                    join,
                    output_properties,
                    current,
                    right_positions,
                    right_nulling,
                    right_factors,
                ) = built
                if source_factors is None:
                    source_factors = tuple(
                        item
                        for item in output_properties.relational.grain.active
                        if type(item) is ProjectJoinGrainFactorIdentity
                        and item.introduction_use == join.input_uses[0].ref
                    )
                    if step_position == 0:
                        binding_factors.setdefault(
                            id(use.source_binding), source_factors
                        )
                accumulated = output_properties.relational
                source_positions = right_positions
                source_nulling = right_nulling
                source_factors = right_factors
                region_joins.append(join)
                joins.append(join)
                properties.append(output_properties)
            binding_positions[id(use.target_binding)] = source_positions
            binding_nulling[id(use.target_binding)] = source_nulling
            if source_factors is None:
                raise ValueError("Concrete JOIN use requires exact source factors.")
            binding_factors[id(use.target_binding)] = source_factors
        regions.append(
            ProjectIRConcreteJoinRegion(
                ledger=ledger,
                starting_allocation=region_start,
                ending_allocation=current,
                joins=tuple(region_joins),
            )
        )
    structural = ProjectIRJoinStructuralStage(
        base=base_plan.structural_stage,
        starting_allocation=allocation,
        ending_allocation=current,
        nodes=tuple(join.node for join in joins),
        outputs=tuple(join.output.occurrence for join in joins),
        input_slots=tuple(slot for join in joins for slot in join.input_slots),
        uses=tuple(use for join in joins for use in join.input_uses),
    )
    extension = ProjectIRJoinRelationalPropertyExtension(
        base=base_relational,
        structural=structural,
        outputs=tuple(properties),
    )
    return ProjectIRJoinRegionStage(
        base_plan=base_plan,
        base_relational=base_relational,
        uses=uses,
        starting_allocation=allocation,
        ending_allocation=current,
        regions=tuple(regions),
        structural=structural,
        properties=extension,
    )
