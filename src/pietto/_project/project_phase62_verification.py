"""Independent Phase-62 verification, analyses, and invalidation."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from heapq import heappop, heappush
from typing import cast

from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_grain import (
    ProjectBaseGrainFactorIdentity,
    ProjectGrainBasisState,
    ProjectGrainDependencyIndex,
    ProjectGrainDependencyFact,
    ProjectGrainFactorIdentity,
    ProjectGrainFactorSet,
    ProjectJoinGrainFactorIdentity,
    grain_dependency_closure,
)
from pietto._project.project_ir import (
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIRJoinInputUseOccurrence,
    ProjectIROperatorFlowUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRUseOccurrence,
    ProjectIRUseRef,
)
from pietto._project.project_ir_evaluation_context import (
    ProjectIREvaluationContextStage,
)
from pietto._project.project_ir_joins import (
    ProjectIRBinaryJoinKind,
    ProjectIRBinaryJoinOccurrence,
    ProjectIRConcreteJoinRegion,
    ProjectIRJoinNullExtensionEffect,
    ProjectIRJoinGrainWitness,
    ProjectIRJoinOutputProperties,
    ProjectIRJoinRegionStage,
    ProjectIRJoinRowSurvivalEffect,
    ProjectIRJoinUnavailableProperty,
    ProjectIRNonConcreteJoinRegion,
    ProjectIROuterJoinBarrier,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinRowOutput,
    ProjectIRJoinedRowField,
    ProjectIRPropertyAvailability,
    ProjectIRProvidedNullExtension,
    ProjectIRProvidedPropertySlot,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRProvidedIntrinsicGrain,
    ProjectIRRelationalPropertyStage,
    ProjectIROutputCandidateKey,
    ProjectIROutputFDIndex,
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueClass,
    ProjectIROutputValueFD,
)
from pietto._project.project_ir_verification import (
    ProjectIRVerificationResult,
    ProjectIRVerificationStatus,
    verify_project_ir_stage,
)
from pietto._project.project_multifact import (
    ProjectActualGrainAuthority,
    ProjectActualGrainAuthorityKind,
    ProjectActualGrainCandidate,
    ProjectAggregateFactHomeLocality,
    ProjectAggregateFactIdentity,
    ProjectAggregateFactJoinLocality,
    ProjectAggregateFactLocality,
    ProjectAggregateFactOccurrence,
    ProjectCommonGrainStatus,
    ProjectFactChasmCandidate,
    ProjectFactContextualGrain,
    ProjectFactGrainComparison,
    ProjectFactGrainDetermination,
    ProjectFactJoinInputSide,
    ProjectFactMultiplicityExposure,
    ProjectMultiFactAlignment,
    ProjectMultiFactAnalysis,
    ProjectMultiFactConcreteRegion,
    ProjectMultiFactMultiplicityRisk,
    ProjectMultiFactNonConcreteRegionSubject,
    ProjectMultiFactRequirement,
    ProjectMultiFactStructuralAlignment,
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
)
from pietto._project.project_relationship_uses import (
    ProjectConcreteJoinUse,
    ProjectJoinUseIssueKind,
    ProjectJoinUseState,
    ProjectNonConcreteJoinUse,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength

__all__: tuple[str, ...] = ()

_PATH_AMBIGUITY_ISSUES = frozenset(
    {
        ProjectJoinUseIssueKind.DIRECT_RELATIONSHIP_AMBIGUOUS,
        ProjectJoinUseIssueKind.AMBIGUOUS_RELATIONSHIP,
        ProjectJoinUseIssueKind.AMBIGUOUS_ENDPOINT_DIRECTION,
    }
)


class ProjectPhase62VerificationStatus(StrEnum):
    VERIFIED = "verified"
    INVALID = "invalid"


class ProjectPhase62VerificationIssueKind(StrEnum):
    ROOT_COHERENCE = "root_coherence"
    BASE_PROJECT_IR = "base_project_ir"
    JOIN_SCOPE_COORDINATE = "join_scope_coordinate"
    JOIN_STRUCTURAL_ENDPOINT = "join_structural_endpoint"
    JOIN_REGION_COMPLETENESS = "join_region_completeness"
    JOIN_CONDITION_MAPPING = "join_condition_mapping"
    JOIN_EFFECT_NULLING = "join_effect_nulling"
    JOIN_PROPERTY_TRANSFER = "join_property_transfer"
    JOIN_KEY_FD_GRAIN = "join_key_fd_grain"
    MULTIFACT_CATALOG = "multifact_catalog"
    MULTIFACT_LOCALITY = "multifact_locality"
    MULTIFACT_ALIGNMENT = "multifact_alignment"
    CHASM_RISK = "chasm_risk"
    COMBINED_ACTUAL_USE_CYCLE = "combined_actual_use_cycle"


type ProjectPhase62VerificationCoordinate = (
    ProjectIRPlanNodeRef
    | ProjectIROutputValueRef
    | ProjectIRUseRef
    | ProjectIRInputSlotRef
    | ProjectAggregateFactIdentity
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62VerificationIssue:
    kind: ProjectPhase62VerificationIssueKind
    coordinate: ProjectPhase62VerificationCoordinate | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectPhase62VerificationIssueKind:
            raise TypeError("Phase-62 verification issue requires an exact kind.")
        if self.coordinate is not None and type(self.coordinate) not in {
            ProjectIRPlanNodeRef,
            ProjectIROutputValueRef,
            ProjectIRUseRef,
            ProjectIRInputSlotRef,
            ProjectAggregateFactIdentity,
        }:
            raise TypeError("Phase-62 verification issue requires a typed coordinate.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62VerificationResult:
    root: ProjectMultiFactAnalysis = field(repr=False, compare=False, hash=False)
    base_verification: ProjectIRVerificationResult
    status: ProjectPhase62VerificationStatus
    issues: tuple[ProjectPhase62VerificationIssue, ...] = ()

    def __post_init__(self) -> None:
        if type(self.root) is not ProjectMultiFactAnalysis:
            raise TypeError("Phase-62 verification requires one exact checked root.")
        if type(self.base_verification) is not ProjectIRVerificationResult:
            raise TypeError("Phase-62 result requires one fresh base verification.")
        if type(self.status) is not ProjectPhase62VerificationStatus:
            raise TypeError("Phase-62 result requires an exact status.")
        if type(self.issues) is not tuple or any(
            type(issue) is not ProjectPhase62VerificationIssue for issue in self.issues
        ):
            raise TypeError("Phase-62 issues must be an exact tuple.")
        order = tuple(ProjectPhase62VerificationIssueKind)
        positions = tuple(order.index(issue.kind) for issue in self.issues)
        if positions != tuple(sorted(positions)) or len(set(positions)) != len(
            positions
        ):
            raise ValueError("Phase-62 issues must retain one fixed ordered pass.")
        if (self.status is ProjectPhase62VerificationStatus.VERIFIED) is bool(
            self.issues
        ):
            raise ValueError("Phase-62 verification status and issues disagree.")
        if self.base_verification.stage is not self.root.evaluation or (
            self.base_verification.status is ProjectIRVerificationStatus.INVALID
            and self.status is ProjectPhase62VerificationStatus.VERIFIED
        ):
            raise ValueError("Phase-62 result must retain fresh base verification.")

    @property
    def verified(self) -> bool:
        return self.status is ProjectPhase62VerificationStatus.VERIFIED


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _coordinate(subject: object | None) -> ProjectPhase62VerificationCoordinate | None:
    if type(subject) in {
        ProjectIRPlanNodeRef,
        ProjectIROutputValueRef,
        ProjectIRUseRef,
        ProjectIRInputSlotRef,
        ProjectAggregateFactIdentity,
    }:
        return cast(ProjectPhase62VerificationCoordinate, subject)
    if type(subject) is ProjectIRPlanNodeOccurrence:
        return subject.ref
    if type(subject) is ProjectIROutputValueOccurrence:
        return subject.ref
    if type(subject) is ProjectIRInputSlotOccurrence:
        return subject.ref
    if type(subject) is ProjectIRUseOccurrence:
        return subject.ref
    if type(subject) is ProjectIROperatorFlowUseOccurrence:
        return subject.ref
    if type(subject) is ProjectIRJoinInputUseOccurrence:
        return subject.ref
    if type(subject) is ProjectIRBinaryJoinOccurrence:
        return subject.node.ref
    if type(subject) is ProjectAggregateFactOccurrence:
        return subject.identity
    if type(subject) is ProjectAggregateFactHomeLocality:
        return subject.fact.identity
    if type(subject) is ProjectAggregateFactJoinLocality:
        return subject.fact.identity
    return None


def _record(
    issues: list[ProjectPhase62VerificationIssue],
    kind: ProjectPhase62VerificationIssueKind,
    subject: object | None = None,
) -> None:
    if any(issue.kind is kind for issue in issues):
        return
    issues.append(
        ProjectPhase62VerificationIssue(
            kind=kind,
            coordinate=_coordinate(subject),
        )
    )


def _root_is_coherent(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> bool:
    valid = (
        type(root.evaluation) is ProjectIREvaluationContextStage
        and type(root.base_relational) is ProjectIRRelationalPropertyStage
        and type(root.join_regions) is ProjectIRJoinRegionStage
        and root.base_relational.origins.evaluation is root.evaluation
        and root.join_regions.base_plan is root.evaluation.project_plan
        and root.join_regions.base_relational is root.base_relational
        and root.join_regions.uses.relationships.semantic_result.module_semantic_facts
        is root.evaluation.project_plan.semantic_facts
    )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.ROOT_COHERENCE)
    return valid


def _concrete_regions(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectIRConcreteJoinRegion, ...]:
    return tuple(
        region
        for region in root.join_regions.regions
        if type(region) is ProjectIRConcreteJoinRegion
    )


def _joins(root: ProjectMultiFactAnalysis) -> tuple[ProjectIRBinaryJoinOccurrence, ...]:
    return tuple(join for region in _concrete_regions(root) for join in region.joins)


def _property_by_join(
    root: ProjectMultiFactAnalysis,
) -> Mapping[ProjectIRPlanNodeRef, ProjectIRJoinOutputProperties]:
    return {
        item.join.node.ref: item
        for item in root.join_regions.properties.outputs
        if type(item) is ProjectIRJoinOutputProperties
    }


def _ref_at(ref: object, scope: object, position: int) -> bool:
    if type(ref) is ProjectIRPlanNodeRef:
        return ref.scope is scope and ref.position == position
    if type(ref) is ProjectIROutputValueRef:
        return ref.scope is scope and ref.position == position
    if type(ref) is ProjectIRInputSlotRef:
        return ref.scope is scope and ref.position == position
    if type(ref) is ProjectIRUseRef:
        return ref.scope is scope and ref.position == position
    return False


def _verify_join_scope_coordinates(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    stage = root.join_regions
    structural = stage.structural
    start = stage.starting_allocation
    end = stage.ending_allocation
    scope = root.evaluation.project_plan.structural_stage.scope
    values = (
        (structural.nodes, start.next_plan_node_position, end.next_plan_node_position),
        (
            structural.outputs,
            start.next_output_value_position,
            end.next_output_value_position,
        ),
        (
            structural.input_slots,
            start.next_input_slot_position,
            end.next_input_slot_position,
        ),
        (structural.uses, start.next_use_position, end.next_use_position),
    )
    valid = (
        structural.base is root.evaluation.project_plan.structural_stage
        and structural.starting_allocation is start
        and structural.ending_allocation is end
        and start is root.evaluation.project_plan.ending_allocation
        and start.scope is end.scope is scope
    )
    for occurrences, first, stop in values:
        refs = tuple(getattr(item, "ref", None) for item in occurrences)
        valid = (
            valid
            and len(refs) == stop - first
            and all(
                _ref_at(ref, scope, position)
                for position, ref in enumerate(refs, first)
            )
        )
    if not valid:
        coordinate = next(
            (
                item
                for collection in (
                    structural.nodes,
                    structural.outputs,
                    structural.input_slots,
                    structural.uses,
                )
                for item in collection
            ),
            None,
        )
        _record(
            issues,
            ProjectPhase62VerificationIssueKind.JOIN_SCOPE_COORDINATE,
            coordinate,
        )


def _verify_join_structural_endpoints(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    stage = root.join_regions
    joins = _joins(root)
    valid = len(stage.structural.nodes) == len(stage.structural.outputs) == len(
        joins
    ) and len(stage.structural.input_slots) == len(stage.structural.uses) == 2 * len(
        joins
    )
    available = list(root.evaluation.project_plan.structural_stage.outputs)
    for position, join in enumerate(joins):
        if type(join) is not ProjectIRBinaryJoinOccurrence:
            valid = False
            break
        slots = join.input_slots
        uses = join.input_uses
        valid = valid and (
            stage.structural.nodes[position] is join.node
            and stage.structural.outputs[position] is join.output.occurrence
            and _same_objects(
                cast(
                    tuple[object, ...],
                    tuple(
                        stage.structural.input_slots[2 * position : 2 * position + 2]
                    ),
                ),
                cast(tuple[object, ...], slots),
            )
            and _same_objects(
                cast(
                    tuple[object, ...],
                    tuple(stage.structural.uses[2 * position : 2 * position + 2]),
                ),
                cast(tuple[object, ...], uses),
            )
            and type(join.output) is ProjectIRJoinRowOutput
            and join.output.occurrence.producer is join.node
            and type(slots) is tuple
            and len(slots) == 2
            and all(type(slot) is ProjectIRInputSlotOccurrence for slot in slots)
            and tuple(slot.input_ordinal for slot in slots) == (0, 1)
            and all(slot.consumer is join.node for slot in slots)
            and type(uses) is tuple
            and len(uses) == 2
            and all(
                type(use) is ProjectIRJoinInputUseOccurrence and use.slot is slot
                for use, slot in zip(uses, slots, strict=True)
            )
            and uses[0].output is join.left_input.output.occurrence
            and uses[1].output is join.right_input.output.occurrence
            and all(any(use.output is output for output in available) for use in uses)
        )
        available.append(join.output.occurrence)
        if not valid:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.JOIN_STRUCTURAL_ENDPOINT,
                join,
            )
            return
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.JOIN_STRUCTURAL_ENDPOINT)


def _verify_join_region_completeness(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    stage = root.join_regions
    valid = len(stage.regions) == len(stage.uses.ledgers) and all(
        region.ledger is ledger
        for region, ledger in zip(stage.regions, stage.uses.ledgers, strict=True)
    )
    current = stage.starting_allocation
    flattened: list[ProjectIRBinaryJoinOccurrence] = []
    for region in stage.regions:
        if region.starting_allocation is not current:
            valid = False
        blockers = tuple(
            use for use in region.ledger.uses if type(use) is ProjectNonConcreteJoinUse
        )
        if blockers:
            valid = valid and (
                type(region) is ProjectIRNonConcreteJoinRegion
                and region.ending_allocation is region.starting_allocation
                and region.blockers == blockers
                and region.state
                in {
                    ProjectJoinUseState.UNKNOWN,
                    ProjectJoinUseState.BLOCKED,
                    ProjectJoinUseState.AMBIGUOUS,
                }
            )
        else:
            expected = tuple(
                (use, step_position, step)
                for use in region.ledger.uses
                if type(use) is ProjectConcreteJoinUse
                for step_position, step in enumerate(use.path.steps)
            )
            valid = valid and (
                type(region) is ProjectIRConcreteJoinRegion
                and len(region.joins) == len(expected)
                and all(
                    join.use is use
                    and join.identity.use == use.identity
                    and join.identity.path_step_position == step_position
                    and join.path_step is step
                    for join, (use, step_position, step) in zip(
                        region.joins, expected, strict=True
                    )
                )
            )
            if type(region) is ProjectIRConcreteJoinRegion:
                flattened.extend(region.joins)
        current = region.ending_allocation
        if not valid:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.JOIN_REGION_COMPLETENESS,
                region.joins[0]
                if type(region) is ProjectIRConcreteJoinRegion and region.joins
                else None,
            )
            return
    valid = valid and current is stage.ending_allocation
    valid = valid and _same_objects(
        cast(tuple[object, ...], tuple(flattened)),
        cast(tuple[object, ...], _joins(root)),
    )
    valid = (
        valid
        and len(stage.properties.outputs) == len(flattened)
        and all(
            item.join is join
            for item, join in zip(stage.properties.outputs, flattened, strict=True)
        )
    )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.JOIN_REGION_COMPLETENESS)


def _condition_for(
    root: ProjectMultiFactAnalysis,
    guarantee: ProjectDirectionalRelationshipMatchGuarantee,
) -> ProjectConcreteRelationshipCondition | None:
    matches = tuple(
        item
        for item in root.join_regions.uses.index.guarantees.conditions.conditions
        if type(item) is ProjectConcreteRelationshipCondition
        and item.relationship.occurrence.identity == guarantee.direction.declaration
    )
    return matches[0] if len(matches) == 1 else None


def _relationship_fields(
    correspondence: ProjectRelationshipEqualityCorrespondence,
    guarantee: ProjectDirectionalRelationshipMatchGuarantee,
):
    return (
        (correspondence.endpoint_zero, correspondence.endpoint_one)
        if guarantee.direction.source.identity.endpoint_position == 0
        else (correspondence.endpoint_one, correspondence.endpoint_zero)
    )


def _verify_join_conditions(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    properties = _property_by_join(root)
    for region in _concrete_regions(root):
        base = region.ledger.bindings[0]
        if base.output is None:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.JOIN_CONDITION_MAPPING,
            )
            return
        accumulated = base.output
        binding_positions = {base.identity: tuple(range(len(accumulated.fields)))}
        join_position = 0
        for authored in region.ledger.uses:
            if type(authored) is not ProjectConcreteJoinUse or (
                authored.source_binding.identity not in binding_positions
            ):
                _record(
                    issues,
                    ProjectPhase62VerificationIssueKind.JOIN_CONDITION_MAPPING,
                )
                return
            source_positions = binding_positions[authored.source_binding.identity]
            for path_step in authored.path.steps:
                if join_position >= len(region.joins):
                    _record(
                        issues,
                        ProjectPhase62VerificationIssueKind.JOIN_CONDITION_MAPPING,
                    )
                    return
                join = region.joins[join_position]
                condition = _condition_for(root, path_step.guarantee)
                output_properties = properties.get(join.node.ref)
                if condition is None or output_properties is None:
                    _record(
                        issues,
                        ProjectPhase62VerificationIssueKind.JOIN_CONDITION_MAPPING,
                        join,
                    )
                    return
                valid = (
                    join.use is authored
                    and join.path_step is path_step
                    and join.guarantee is path_step.guarantee
                    and join.condition is condition
                    and join.left_input is accumulated
                    and join.right_input is path_step.guarantee.target_output
                )
                if not valid:
                    _record(
                        issues,
                        ProjectPhase62VerificationIssueKind.JOIN_CONDITION_MAPPING,
                        join,
                    )
                    return
                fields = join.output.row_shape.fields
                left_count = len(join.left_input.fields)
                source_fields = tuple(fields[position] for position in source_positions)
                expected_pairs: list[
                    tuple[
                        ProjectIRJoinedRowField,
                        ProjectIRJoinedRowField,
                        ProjectRelationshipEqualityCorrespondence,
                    ]
                ] = []
                for correspondence in condition.correspondences:
                    source_reference, target_reference = _relationship_fields(
                        correspondence, join.guarantee
                    )
                    left_matches = tuple(
                        field
                        for field in source_fields
                        if field.evidence is source_reference.semantic_field
                    )
                    right_matches = tuple(
                        (position, field)
                        for position, field in enumerate(join.right_input.fields)
                        if field.evidence is target_reference.semantic_field
                    )
                    if len(left_matches) != 1 or len(right_matches) != 1:
                        valid = False
                        break
                    right_position, _ = right_matches[0]
                    expected_pairs.append(
                        (
                            left_matches[0],
                            fields[left_count + right_position],
                            correspondence,
                        )
                    )
                valid = (
                    valid
                    and len(join.matches) == len(expected_pairs)
                    and all(
                        pair.left is left
                        and pair.right is right
                        and pair.correspondence is correspondence
                        for pair, (left, right, correspondence) in zip(
                            join.matches, expected_pairs, strict=True
                        )
                    )
                )
                if not valid:
                    _record(
                        issues,
                        ProjectPhase62VerificationIssueKind.JOIN_CONDITION_MAPPING,
                        join,
                    )
                    return
                accumulated = output_properties.relational
                source_positions = tuple(
                    range(left_count, left_count + len(join.right_input.fields))
                )
                join_position += 1
            binding_positions[authored.target_binding.identity] = source_positions


def _expected_join_effects(
    join: ProjectIRBinaryJoinOccurrence,
) -> tuple[
    ProjectIRBinaryJoinKind,
    ProjectRelationshipFanoutEffect,
    ProjectIRJoinRowSurvivalEffect,
    ProjectIRJoinNullExtensionEffect,
    ProjectIROuterJoinBarrier,
    tuple[ProjectIRPlanNodeRef, ...],
]:
    kind = ProjectIRBinaryJoinKind(join.use.kind.value)
    source_nulling = join.matches[0].left.nulling_joins
    actual_nulling = kind is ProjectIRBinaryJoinKind.LEFT and (
        join.guarantee.minimum is ProjectRelationshipMinimumBound.ZERO_ALLOWED
        or bool(source_nulling)
    )
    return (
        kind,
        (
            ProjectRelationshipFanoutEffect.PRESERVES_SOURCE_MULTIPLICITY
            if join.guarantee.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
            else ProjectRelationshipFanoutEffect.MAY_MULTIPLY
        ),
        (
            ProjectIRJoinRowSurvivalEffect.GUARANTEES_LEFT_SURVIVAL
            if kind is ProjectIRBinaryJoinKind.LEFT
            or (
                not source_nulling
                and join.guarantee.minimum
                is ProjectRelationshipMinimumBound.AT_LEAST_ONE
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
        ((*source_nulling, join.node.ref) if actual_nulling else ()),
    )


def _verify_join_effects_and_nulling(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    properties = _property_by_join(root)
    for join in _joins(root):
        if not join.matches:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.JOIN_EFFECT_NULLING,
                join,
            )
            return
        kind, fanout, survival, null_extension, barrier, right_nulling = (
            _expected_join_effects(join)
        )
        fields = join.output.row_shape.fields
        left_count = len(join.left_input.fields)
        matched_left = {pair.left.field_position for pair in join.matches}
        matched_right = {
            pair.right.field_position - left_count for pair in join.matches
        }
        valid = (
            join.kind is kind
            and join.fanout is fanout
            and join.survival is survival
            and join.null_extension is null_extension
            and join.outer_join_barrier is barrier
            and len(fields) == left_count + len(join.right_input.fields)
        )
        for position, incoming in enumerate(join.left_input.fields):
            retained = fields[position]
            if type(join.left_input.output) is ProjectIRJoinRowOutput:
                prior = join.left_input.output.row_shape.fields[position]
                introduction = prior.introduction_use
                nulling = prior.nulling_joins
                nullability = prior.effective_nullability
            else:
                introduction = join.input_uses[0]
                nulling = ()
                nullability = incoming.effective_nullability
            if (
                kind is ProjectIRBinaryJoinKind.INNER
                and position in matched_left
                and not nulling
            ):
                nullability = ProjectRowFieldNullability.NON_NULL
            valid = valid and (
                retained.evidence is incoming.evidence
                and retained.introduction_use is introduction
                and retained.nulling_joins == nulling
                and retained.effective_nullability is nullability
            )
        for position, incoming in enumerate(join.right_input.fields):
            retained = fields[left_count + position]
            nullability = (
                ProjectRowFieldNullability.NULLABLE
                if right_nulling
                else (
                    ProjectRowFieldNullability.NON_NULL
                    if position in matched_right
                    else incoming.effective_nullability
                )
            )
            valid = valid and (
                retained.evidence is incoming.evidence
                and retained.introduction_use is join.input_uses[1]
                and retained.nulling_joins == right_nulling
                and retained.effective_nullability is nullability
            )
        output_properties = properties.get(join.node.ref)
        if output_properties is None:
            valid = False
        elif any(field.nulling_joins for field in fields):
            valid = valid and (
                type(output_properties.null_extension) is ProjectIRProvidedNullExtension
                and output_properties.null_extension.output is join.output
                and output_properties.null_extension.fields == fields
            )
        else:
            valid = valid and (
                type(output_properties.null_extension)
                is ProjectIRJoinUnavailableProperty
                and output_properties.null_extension.output is join.output
                and output_properties.null_extension.property_slot
                is ProjectIRProvidedPropertySlot.NULL_EXTENSION
                and output_properties.null_extension.availability
                is ProjectIRPropertyAvailability.NOT_APPLICABLE
            )
        if not valid:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.JOIN_EFFECT_NULLING,
                join,
            )
            return


def _class_positions(value_class: ProjectIROutputValueClass) -> tuple[int, ...]:
    return tuple(member.field_position for member in value_class.members)


def _class_images(
    join: ProjectIRBinaryJoinOccurrence,
    relational: ProjectIROutputRelationalProperties,
) -> (
    tuple[
        tuple[ProjectIROutputValueClass, ...],
        Mapping[ProjectIROutputValueClass, ProjectIROutputValueClass],
        Mapping[ProjectIROutputValueClass, ProjectIROutputValueClass],
    ]
    | None
):
    left_count = len(join.left_input.fields)
    expected_positions = (
        *(
            tuple(member.field_position for member in item.members)
            for item in join.left_input.value_classes
        ),
        *(
            tuple(left_count + member.field_position for member in item.members)
            for item in join.right_input.value_classes
        ),
    )
    if len(relational.value_classes) != len(expected_positions) or any(
        type(value_class) is not ProjectIROutputValueClass
        or value_class.output is not join.output
        or _class_positions(value_class) != positions
        or not _same_objects(
            cast(tuple[object, ...], value_class.members),
            cast(
                tuple[object, ...],
                tuple(relational.fields[position] for position in positions),
            ),
        )
        for value_class, positions in zip(
            relational.value_classes, expected_positions, strict=True
        )
    ):
        return None
    left_images = {
        old: relational.value_classes[position]
        for position, old in enumerate(join.left_input.value_classes)
    }
    right_offset = len(join.left_input.value_classes)
    right_images = {
        old: relational.value_classes[right_offset + position]
        for position, old in enumerate(join.right_input.value_classes)
    }
    return relational.value_classes, left_images, right_images


def _ordered_classes(
    classes: tuple[ProjectIROutputValueClass, ...],
    values: tuple[ProjectIROutputValueClass, ...],
) -> tuple[ProjectIROutputValueClass, ...]:
    selected = set(values)
    return tuple(item for item in classes if item in selected)


def _class_for_field(
    classes: tuple[ProjectIROutputValueClass, ...],
    field: ProjectIRJoinedRowField,
) -> ProjectIROutputValueClass | None:
    matches = tuple(
        item
        for item in classes
        if any(member.field_position == field.field_position for member in item.members)
    )
    return matches[0] if len(matches) == 1 else None


def _all_non_null(value_class: ProjectIROutputValueClass) -> bool:
    return all(
        member.effective_nullability is ProjectRowFieldNullability.NON_NULL
        for member in value_class.members
    )


def _reverse_guarantee(
    root: ProjectMultiFactAnalysis,
    guarantee: ProjectDirectionalRelationshipMatchGuarantee,
) -> ProjectDirectionalRelationshipMatchGuarantee | None:
    matches = tuple(
        item
        for item in root.join_regions.uses.index.by_declaration.get(
            guarantee.direction.declaration, ()
        )
        if item.direction.source is guarantee.direction.target
        and item.direction.target is guarantee.direction.source
    )
    return matches[0] if len(matches) == 1 else None


def _frontier_signatures(
    values: list[
        tuple[tuple[ProjectIROutputValueClass, ...], ProjectRowUniquenessStrength]
    ],
) -> tuple[
    tuple[tuple[ProjectIROutputValueClass, ...], ProjectRowUniquenessStrength], ...
]:
    merged: list[
        tuple[tuple[ProjectIROutputValueClass, ...], ProjectRowUniquenessStrength]
    ] = []
    for value in values:
        if value not in merged:
            merged.append(value)
    return tuple(
        value
        for position, value in enumerate(merged)
        if not any(
            set(other[0]) <= set(value[0])
            and (
                other[1] is ProjectRowUniquenessStrength.STRICT or other[1] is value[1]
            )
            for other_position, other in enumerate(merged)
            if other_position != position
        )
    )


def _expected_key_fd_signatures(
    root: ProjectMultiFactAnalysis,
    join: ProjectIRBinaryJoinOccurrence,
    classes: tuple[ProjectIROutputValueClass, ...],
    left_images: Mapping[ProjectIROutputValueClass, ProjectIROutputValueClass],
    right_images: Mapping[ProjectIROutputValueClass, ProjectIROutputValueClass],
) -> (
    tuple[
        tuple[
            tuple[tuple[ProjectIROutputValueClass, ...], ProjectRowUniquenessStrength],
            ...,
        ],
        tuple[
            tuple[
                tuple[ProjectIROutputValueClass, ...],
                tuple[ProjectIROutputValueClass, ...],
                ProjectRowUniquenessStrength,
            ],
            ...,
        ],
    ]
    | None
):
    reverse = _reverse_guarantee(root, join.guarantee)
    if reverse is None:
        return None
    left_keys = tuple(
        (
            _ordered_classes(
                classes, tuple(left_images[item] for item in key.determinants)
            ),
            (
                ProjectRowUniquenessStrength.STRICT
                if all(_all_non_null(left_images[item]) for item in key.determinants)
                else key.strength
            ),
        )
        for key in join.left_input.keys
    )
    actual_nulling = (
        join.null_extension is ProjectIRJoinNullExtensionEffect.MAY_NULL_EXTEND_RIGHT
    )
    right_keys = tuple(
        (
            _ordered_classes(
                classes, tuple(right_images[item] for item in key.determinants)
            ),
            (
                ProjectRowUniquenessStrength.LAX
                if actual_nulling
                else (
                    ProjectRowUniquenessStrength.STRICT
                    if all(
                        _all_non_null(right_images[item]) for item in key.determinants
                    )
                    else key.strength
                )
            ),
        )
        for key in join.right_input.keys
    )
    source_classes = _ordered_classes(
        classes,
        cast(
            tuple[ProjectIROutputValueClass, ...],
            tuple(_class_for_field(classes, pair.left) for pair in join.matches),
        ),
    )
    source_introduction = join.matches[0].left.introduction_use
    source_binding_classes = _ordered_classes(
        classes,
        tuple(
            value_class
            for value_class in classes
            if any(
                join.output.row_shape.fields[member.field_position].introduction_use
                is source_introduction
                for member in value_class.members
            )
        ),
    )
    right_match_classes = _ordered_classes(
        classes,
        cast(
            tuple[ProjectIROutputValueClass, ...],
            tuple(_class_for_field(classes, pair.right) for pair in join.matches),
        ),
    )
    if len(source_classes) != len(join.matches) or len(right_match_classes) != len(
        join.matches
    ):
        return None
    forward = join.guarantee.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    reverse_one = reverse.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
    candidates: list[
        tuple[tuple[ProjectIROutputValueClass, ...], ProjectRowUniquenessStrength]
    ] = []
    if forward:
        candidates.extend(left_keys)
    if reverse_one and any(set(key[0]) == set(source_classes) for key in left_keys):
        candidates.extend(right_keys)
    for left_key in left_keys:
        for right_key in right_keys:
            determinants = _ordered_classes(classes, (*left_key[0], *right_key[0]))
            candidates.append(
                (
                    determinants,
                    (
                        ProjectRowUniquenessStrength.STRICT
                        if (
                            left_key[1] is ProjectRowUniquenessStrength.STRICT
                            and right_key[1] is ProjectRowUniquenessStrength.STRICT
                        )
                        or all(_all_non_null(item) for item in determinants)
                        else ProjectRowUniquenessStrength.LAX
                    ),
                )
            )
    keys = _frontier_signatures(candidates)
    fds: list[
        tuple[
            tuple[ProjectIROutputValueClass, ...],
            tuple[ProjectIROutputValueClass, ...],
            ProjectRowUniquenessStrength,
        ]
    ] = []
    for fact, images, right_side in (
        *((fact, left_images, False) for fact in join.left_input.fds),
        *((fact, right_images, True) for fact in join.right_input.fds),
    ):
        determinants = _ordered_classes(
            classes, tuple(images[item] for item in fact.determinants)
        )
        dependents = tuple(
            item
            for item in _ordered_classes(
                classes, tuple(images[item] for item in fact.dependents)
            )
            if item not in determinants
        )
        if not dependents:
            continue
        strength = fact.strength
        if (
            right_side
            and actual_nulling
            and strength is ProjectRowUniquenessStrength.STRICT
            and not all(_all_non_null(item) for item in fact.determinants)
        ):
            strength = ProjectRowUniquenessStrength.LAX
        fds.append((determinants, dependents, strength))
    right_all = tuple(right_images[item] for item in join.right_input.value_classes)
    if forward and source_classes and right_all:
        fds.append((source_classes, right_all, ProjectRowUniquenessStrength.STRICT))
    if reverse_one and right_match_classes and source_binding_classes:
        fds.append(
            (
                right_match_classes,
                source_binding_classes,
                (
                    ProjectRowUniquenessStrength.LAX
                    if actual_nulling
                    else ProjectRowUniquenessStrength.STRICT
                ),
            )
        )
    if join.kind is ProjectIRBinaryJoinKind.INNER or not actual_nulling:
        for pair in join.matches:
            left_class = _class_for_field(classes, pair.left)
            right_class = _class_for_field(classes, pair.right)
            if left_class is None or right_class is None:
                return None
            fds.extend(
                (
                    (
                        (left_class,),
                        (right_class,),
                        ProjectRowUniquenessStrength.STRICT,
                    ),
                    (
                        (right_class,),
                        (left_class,),
                        ProjectRowUniquenessStrength.STRICT,
                    ),
                )
            )
    for determinants, strength in keys:
        dependents = tuple(item for item in classes if item not in determinants)
        if dependents:
            fds.append((determinants, dependents, strength))
    merged_fds: list[
        tuple[
            tuple[ProjectIROutputValueClass, ...],
            tuple[ProjectIROutputValueClass, ...],
            ProjectRowUniquenessStrength,
        ]
    ] = []
    for fact in fds:
        if fact not in merged_fds:
            merged_fds.append(fact)
    return keys, tuple(merged_fds)


def _verify_join_property_transfer(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    properties = _property_by_join(root)
    for join in _joins(root):
        output = properties.get(join.node.ref)
        if output is None or output.join is not join:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.JOIN_PROPERTY_TRANSFER,
                join,
            )
            return
        relational = output.relational
        fields = join.output.row_shape.fields
        valid = (
            relational.output is join.output
            and len(relational.fields) == len(fields)
            and all(
                type(item) is ProjectIROutputFieldOccurrence
                and item.output is join.output
                and item.field_position == position
                and item.evidence is field.evidence
                and item.effective_nullability is field.effective_nullability
                for position, (item, field) in enumerate(
                    zip(relational.fields, fields, strict=True)
                )
            )
        )
        images = _class_images(join, relational)
        valid = valid and images is not None
        if images is not None:
            classes, left_images, right_images = images
            member_positions = tuple(
                member.field_position
                for value_class in classes
                for member in value_class.members
            )
            valid = (
                valid
                and len(set(member_positions)) == len(fields)
                and set(member_positions) == set(range(len(fields)))
            )
            expected = _expected_key_fd_signatures(
                root, join, classes, left_images, right_images
            )
            if expected is None:
                valid = False
            else:
                expected_keys, expected_fds = expected
                actual_keys = tuple(
                    (key.determinants, key.strength) for key in relational.keys
                )
                actual_fds = tuple(
                    (fact.determinants, fact.dependents, fact.strength)
                    for fact in relational.fds
                )
                valid = (
                    valid
                    and actual_keys == expected_keys
                    and actual_fds == expected_fds
                )
        if not valid:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.JOIN_PROPERTY_TRANSFER,
                join,
            )
            return


def _base_factor(
    identity: ProjectGrainFactorIdentity,
) -> ProjectBaseGrainFactorIdentity:
    return (
        identity.base
        if type(identity) is ProjectJoinGrainFactorIdentity
        else cast(ProjectBaseGrainFactorIdentity, identity)
    )


def _expected_grain(
    root: ProjectMultiFactAnalysis,
    join: ProjectIRBinaryJoinOccurrence,
) -> (
    tuple[
        tuple[ProjectJoinGrainFactorIdentity, ...],
        tuple[ProjectJoinGrainFactorIdentity, ...],
        tuple[ProjectGrainDependencyFact, ...],
    ]
    | None
):
    reverse = _reverse_guarantee(root, join.guarantee)
    if reverse is None:
        return None
    left_images = {
        factor.identity: (
            factor.identity
            if type(factor.identity) is ProjectJoinGrainFactorIdentity
            else ProjectJoinGrainFactorIdentity(
                base=_base_factor(factor.identity),
                introduction_use=join.input_uses[0].ref,
                nulling_joins=(),
            )
        )
        for factor in join.left_input.grain.factors
    }
    right_nulling = _expected_join_effects(join)[-1]
    right_images = {
        factor.identity: ProjectJoinGrainFactorIdentity(
            base=_base_factor(factor.identity),
            introduction_use=join.input_uses[1].ref,
            nulling_joins=right_nulling,
        )
        for factor in join.right_input.grain.factors
    }
    left_active = tuple(left_images[item] for item in join.left_input.grain.active)
    right_active = tuple(right_images[item] for item in join.right_input.grain.active)
    factors = (
        *(left_images[item.identity] for item in join.left_input.grain.factors),
        *(right_images[item.identity] for item in join.right_input.grain.factors),
    )
    dependencies: list[ProjectGrainDependencyFact] = []
    for fact, images in (
        *((fact, left_images) for fact in join.left_input.grain.dependencies),
        *((fact, right_images) for fact in join.right_input.grain.dependencies),
    ):
        dependencies.append(
            ProjectGrainDependencyFact(
                determinants=tuple(images[item] for item in fact.determinants),
                dependents=tuple(images[item] for item in fact.dependents),
            )
        )
    source_introduction = join.matches[0].left.introduction_use.ref
    source_factors = tuple(
        factor
        for factor in left_active
        if factor.introduction_use == source_introduction
    )
    if (
        join.guarantee.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
        and source_factors
        and right_active
    ):
        dependencies.append(
            ProjectGrainDependencyFact(
                determinants=source_factors,
                dependents=right_active,
            )
        )
    if (
        reverse.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
        and not right_nulling
        and right_active
        and source_factors
    ):
        dependencies.append(
            ProjectGrainDependencyFact(
                determinants=right_active,
                dependents=source_factors,
            )
        )
    return (
        cast(tuple[ProjectJoinGrainFactorIdentity, ...], factors),
        (
            *left_active,
            *right_active,
        ),
        tuple(dependencies),
    )


def _fd_index_valid(
    relational: ProjectIROutputRelationalProperties,
) -> bool:
    index = relational.fd_index
    if (
        type(index) is not ProjectIROutputFDIndex
        or index.output is not relational.output
        or index.universe != relational.value_classes
        or index.facts != relational.fds
        or dict(index.positions)
        != {item: position for position, item in enumerate(index.universe)}
    ):
        return False
    positions = dict(index.positions)
    strict = tuple(
        fact
        for fact in relational.fds
        if fact.strength is ProjectRowUniquenessStrength.STRICT
    )
    lax = tuple(
        fact
        for fact in relational.fds
        if fact.strength is ProjectRowUniquenessStrength.LAX
    )
    for rules, facts in ((index.strict_rules, strict), (index.lax_rules, lax)):
        if len(rules) != len(facts) or any(
            rule.fact is not fact
            or rule.lhs_mask != sum(1 << positions[item] for item in fact.determinants)
            or rule.rhs_mask != sum(1 << positions[item] for item in fact.dependents)
            for rule, fact in zip(rules, facts, strict=True)
        ):
            return False
    return index.incidents == tuple(
        tuple(
            rule_position
            for rule_position, rule in enumerate(index.strict_rules)
            if rule.lhs_mask & (1 << position)
        )
        for position in range(len(index.universe))
    )


def _verify_join_key_fd_grain(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    properties = _property_by_join(root)
    for join in _joins(root):
        output = properties.get(join.node.ref)
        expected = _expected_grain(root, join)
        if output is None or expected is None:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.JOIN_KEY_FD_GRAIN,
                join,
            )
            return
        relational = output.relational
        factors, active, dependencies = expected
        grain = relational.grain
        witness = grain.witness
        valid = (
            _fd_index_valid(relational)
            and all(
                type(key) is ProjectIROutputCandidateKey
                and key.output is relational.output
                and key.determinants
                and key.supports
                for key in relational.keys
            )
            and all(
                type(fact) is ProjectIROutputValueFD
                and fact.output is relational.output
                and fact.determinants
                and fact.dependents
                and not set(fact.determinants) & set(fact.dependents)
                and fact.supports
                for fact in relational.fds
            )
            and tuple(factor.identity for factor in grain.factors) == factors
            and grain.active == active
            and grain.dependencies == dependencies
            and grain.state
            is (
                ProjectGrainBasisState.FACTORIZED
                if active
                else ProjectGrainBasisState.GLOBAL
            )
            and grain.origin_set
            is join.left_input.grain.origin_set
            is join.right_input.grain.origin_set
            and type(witness) is ProjectIRJoinGrainWitness
            and witness.join == join.identity
            and witness.left is join.left_input.grain
            and witness.right is join.right_input.grain
            and all(
                type(factor) is ProjectJoinGrainFactorIdentity
                and factor.introduction_use.scope is join.node.ref.scope
                and all(
                    ref.scope is join.node.ref.scope for ref in factor.nulling_joins
                )
                for factor in active
            )
        )
        if not valid:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.JOIN_KEY_FD_GRAIN,
                join,
            )
            return


def _base_properties(
    root: ProjectMultiFactAnalysis,
) -> Mapping[ProjectIROutputValueRef, ProjectIROutputRelationalProperties]:
    return {item.output.occurrence.ref: item for item in root.base_relational.outputs}


def _verify_multifact_catalog(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    properties = _base_properties(root)
    expected = tuple(
        (context, position, aggregate_result)
        for context in root.evaluation.aggregate_contexts
        for position, aggregate_result in enumerate(context.aggregate_results)
    )
    valid = len(root.facts) == len(expected)
    expected_by_context = {
        context.operator.node.ref: tuple(
            fact for fact in root.facts if fact.context is context
        )
        for context in root.evaluation.aggregate_contexts
    }
    expected_by_home: dict[
        ProjectIROutputValueRef, tuple[ProjectAggregateFactOccurrence, ...]
    ] = {}
    for fact, (context, position, aggregate_result) in zip(
        root.facts, expected, strict=True
    ):
        select_matches = tuple(
            item
            for item in context.semantic_facts.select_facts
            if item.aggregate_result_fact is aggregate_result
        )
        input_properties = properties.get(context.input_row_output.occurrence.ref)
        result_properties = properties.get(context.result_row_output.occurrence.ref)
        home_properties = properties.get(
            context.fragment.root_relation_output.occurrence.ref
        )
        valid = valid and (
            type(fact) is ProjectAggregateFactOccurrence
            and fact.identity.aggregate_node == context.operator.node.ref
            and fact.identity.aggregate_result_position == position
            and fact.context is context
            and fact.aggregate_result is aggregate_result
            and len(select_matches) == 1
            and fact.select_fact is select_matches[0]
            and fact.selected_output_ordinal
            == select_matches[0].selected_output_ordinal
            and input_properties is not None
            and fact.input_row_properties is input_properties
            and result_properties is not None
            and fact.result_row_properties is result_properties
            and home_properties is not None
            and fact.home_relation_properties is home_properties
        )
        if (
            not valid
            or input_properties is None
            or result_properties is None
            or home_properties is None
        ):
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG,
                fact,
            )
            return
        ordinal = fact.selected_output_ordinal
        final_matches = tuple(
            output
            for output in context.fragment.final_scalar_outputs
            if output.field.anchor.identity.field_position == ordinal
        )
        class_matches = tuple(
            value_class
            for value_class in home_properties.value_classes
            if any(member is fact.home_field for member in value_class.members)
        )
        valid = valid and (
            ordinal < len(result_properties.fields)
            and fact.stage_scalar_output is result_properties.fields[ordinal]
            and ordinal < len(home_properties.fields)
            and fact.home_field is home_properties.fields[ordinal]
            and fact.stage_scalar_output.evidence is fact.home_field.evidence
            and len(final_matches) == 1
            and fact.final_scalar_output is final_matches[0]
            and fact.final_scalar_output.field.evidence is fact.home_field.evidence
            and len(class_matches) == 1
            and fact.home_value_class is class_matches[0]
            and fact.source_intrinsic_grain is input_properties.grain
            and fact.result_intrinsic_grain is result_properties.grain
        )
        output_ref = home_properties.output.occurrence.ref
        expected_by_home[output_ref] = (*expected_by_home.get(output_ref, ()), fact)
        if not valid:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG,
                fact,
            )
            return
    valid = (
        valid
        and tuple(root.facts_by_context) == tuple(expected_by_context)
        and all(
            _same_objects(
                cast(tuple[object, ...], root.facts_by_context[key]),
                cast(tuple[object, ...], values),
            )
            for key, values in expected_by_context.items()
        )
    )
    valid = (
        valid
        and tuple(root.facts_by_home_output) == tuple(expected_by_home)
        and all(
            _same_objects(
                cast(tuple[object, ...], root.facts_by_home_output[key]),
                cast(tuple[object, ...], values),
            )
            for key, values in expected_by_home.items()
        )
    )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG)


def _determination_valid(determination: ProjectFactGrainDetermination) -> bool:
    if type(determination) is not ProjectFactGrainDetermination or not (
        determination.seed.universe
        is determination.requested.universe
        is determination.closure.universe
        is determination.index.universe
    ):
        return False
    expected = grain_dependency_closure(determination.index, determination.seed)
    proven = (
        determination.requested.mask & expected.mask == determination.requested.mask
    )
    return determination.closure.factors == expected.factors and (
        determination.status.value == ("proven" if proven else "not_proven")
    )


def _comparison_valid(comparison: ProjectFactGrainComparison) -> bool:
    if type(comparison) is not ProjectFactGrainComparison or not (
        comparison.left_to_right.index is comparison.index
        and comparison.right_to_left.index is comparison.index
        and _determination_valid(comparison.left_to_right)
        and _determination_valid(comparison.right_to_left)
        and comparison.left_to_right.seed.factors == comparison.left.factors
        and comparison.left_to_right.requested.factors == comparison.right.factors
        and comparison.right_to_left.seed.factors == comparison.right.factors
        and comparison.right_to_left.requested.factors == comparison.left.factors
    ):
        return False
    statuses = (
        comparison.left_to_right.status.value,
        comparison.right_to_left.status.value,
    )
    expected = {
        ("proven", "proven"): "equal",
        ("proven", "not_proven"): "left_finer",
        ("not_proven", "proven"): "right_finer",
        ("not_proven", "not_proven"): "incomparable",
    }[statuses]
    return comparison.status.value == expected


def _localized_factors(
    grain: ProjectIRProvidedIntrinsicGrain,
    introduction_use: ProjectIRJoinInputUseOccurrence,
    final_grain: ProjectIRProvidedIntrinsicGrain,
) -> tuple[ProjectGrainFactorIdentity, ...] | None:
    localized: list[ProjectGrainFactorIdentity] = []
    for factor in grain.active:
        matches = tuple(
            retained
            for retained in final_grain.active
            if (
                retained == factor
                if type(factor) is ProjectJoinGrainFactorIdentity
                else (
                    type(retained) is ProjectJoinGrainFactorIdentity
                    and retained.base == factor
                    and retained.introduction_use == introduction_use.ref
                )
            )
        )
        if len(matches) != 1:
            return None
        localized.append(matches[0])
    return tuple(localized)


def _verify_multifact_localities(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    valid = len(root.home_localities) == len(root.facts) and all(
        type(locality) is ProjectAggregateFactHomeLocality
        and locality.fact is fact
        and locality.home_relation_properties is fact.home_relation_properties
        and locality.home_field is fact.home_field
        and locality.relationship_entry_path is None
        and locality.introduction_use is None
        and locality.introduction_join is None
        and locality.contextual_grain.authority is fact.result_intrinsic_grain
        and locality.contextual_grain.state is fact.result_intrinsic_grain.state
        and locality.contextual_grain.factors == fact.result_intrinsic_grain.active
        for locality, fact in zip(root.home_localities, root.facts, strict=True)
    )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY)
        return
    wrappers = {item.region: item for item in root.concrete_regions}
    expected_wrappers = _concrete_regions(root)
    if len(wrappers) != len(expected_wrappers) or tuple(wrappers) != expected_wrappers:
        _record(issues, ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY)
        return
    expected_by_use: dict[
        ProjectIRUseRef, tuple[ProjectAggregateFactJoinLocality, ...]
    ] = {use.ref: () for use in root.join_regions.structural.uses}
    for region in expected_wrappers:
        wrapper = wrappers[region]
        final_properties = _property_by_join(root).get(region.joins[-1].node.ref)
        if final_properties is None or wrapper.final_properties is not final_properties:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY,
            )
            return
        expected_sites: list[
            tuple[
                ProjectAggregateFactOccurrence,
                ProjectIRBinaryJoinOccurrence,
                ProjectFactJoinInputSide,
            ]
        ] = []
        for fact in root.facts:
            for join in region.joins:
                if join.left_input is fact.home_relation_properties:
                    expected_sites.append((fact, join, ProjectFactJoinInputSide.LEFT))
                if join.right_input is fact.home_relation_properties:
                    expected_sites.append((fact, join, ProjectFactJoinInputSide.RIGHT))
        if len(wrapper.localities) != len(expected_sites):
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY,
            )
            return
        for locality, (fact, join, side) in zip(
            wrapper.localities, expected_sites, strict=True
        ):
            side_position = 0 if side is ProjectFactJoinInputSide.LEFT else 1
            introduction = join.input_uses[side_position]
            contextual = _localized_factors(
                fact.result_intrinsic_grain,
                introduction,
                final_properties.relational.grain,
            )
            start = region.joins.index(join)
            carried: list[ProjectIRJoinedRowField] = []
            for later in region.joins[start:]:
                matches = tuple(
                    field
                    for field in later.output.row_shape.fields
                    if field.evidence is fact.home_field.evidence
                    and field.introduction_use is introduction
                )
                if len(matches) != 1:
                    contextual = None
                    break
                carried.append(matches[0])
            valid = (
                type(locality) is ProjectAggregateFactJoinLocality
                and locality.fact is fact
                and locality.region is region
                and locality.introduction_join is join
                and locality.introduction_use is introduction
                and locality.side is side
                and locality.relationship_entry_path
                is (join.path_step if side is ProjectFactJoinInputSide.RIGHT else None)
                and locality.carried_fields == tuple(carried)
                and locality.final_region_properties is final_properties
                and carried
                and locality.final_field is carried[-1]
                and contextual is not None
                and locality.contextual_grain.authority
                is final_properties.relational.grain
                and locality.contextual_grain.factors == contextual
                and locality.contextual_grain.state is fact.result_intrinsic_grain.state
                and _comparison_valid(locality.final_grain_comparison)
            )
            if not valid:
                _record(
                    issues,
                    ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY,
                    locality,
                )
                return
            expected_by_use[introduction.ref] = (
                *expected_by_use[introduction.ref],
                locality,
            )
    valid = tuple(root.localities_by_introduction_use) == tuple(
        expected_by_use
    ) and all(
        _same_objects(
            cast(tuple[object, ...], root.localities_by_introduction_use[key]),
            cast(tuple[object, ...], values),
        )
        for key, values in expected_by_use.items()
    )
    expected_non_concrete = tuple(
        region
        for region in root.join_regions.regions
        if type(region) is ProjectIRNonConcreteJoinRegion
    )
    valid = valid and len(root.non_concrete_regions) == len(expected_non_concrete)
    for subject, region in zip(
        root.non_concrete_regions, expected_non_concrete, strict=True
    ):
        identifiable = tuple(
            fact
            for fact in root.facts
            if any(
                binding.output is fact.home_relation_properties
                or (
                    binding.target is not None
                    and binding.target.target_occurrence
                    is fact.context.semantic_facts.owner
                )
                for binding in region.ledger.bindings
            )
        )
        path_ambiguous = bool(identifiable) and any(
            issue.kind in _PATH_AMBIGUITY_ISSUES
            for blocker in region.blockers
            for issue in blocker.issues
        )
        expected_structural = (
            ProjectMultiFactStructuralAlignment.AMBIGUOUS_PATH
            if path_ambiguous
            else ProjectMultiFactStructuralAlignment.INSUFFICIENT_EVIDENCE
        )
        valid = valid and (
            type(subject) is ProjectMultiFactNonConcreteRegionSubject
            and subject.region is region
            and subject.blockers == region.blockers
            and subject.identifiable_facts == identifiable
            and subject.structural is expected_structural
        )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY)


def _factor_set(
    grain_index: ProjectGrainDependencyIndex,
    factors: tuple[ProjectGrainFactorIdentity, ...],
) -> ProjectGrainFactorSet | None:
    universe = grain_index.universe
    positions = grain_index.positions
    if any(factor not in positions for factor in factors):
        return None
    selected = set(factors)
    ordered = tuple(
        factor.identity for factor in universe.factors if factor.identity in selected
    )
    if len(ordered) != len(factors):
        return None
    return ProjectGrainFactorSet(universe=universe, factors=ordered)


def _reaches(
    grain_index: ProjectGrainDependencyIndex,
    source: tuple[ProjectGrainFactorIdentity, ...],
    target: tuple[ProjectGrainFactorIdentity, ...],
) -> bool:
    seed = _factor_set(grain_index, source)
    requested = _factor_set(grain_index, target)
    if seed is None or requested is None:
        return False
    closure = grain_dependency_closure(grain_index, seed)
    return requested.mask & closure.mask == requested.mask


def _add_factor_candidate(
    candidates: list[
        tuple[
            tuple[ProjectGrainFactorIdentity, ...],
            list[tuple[ProjectActualGrainAuthorityKind, tuple[object, ...]]],
        ]
    ],
    factors: tuple[ProjectGrainFactorIdentity, ...],
    *,
    allow_empty: bool,
    authority_kind: ProjectActualGrainAuthorityKind,
    evidence: tuple[object, ...],
) -> None:
    if not factors and not allow_empty:
        return
    existing = next((item for item in candidates if item[0] == factors), None)
    authority = (authority_kind, evidence)
    if existing is None:
        candidates.append((factors, [authority]))
    else:
        existing[1].append(authority)


def _expected_actual_candidates(
    root: ProjectMultiFactAnalysis,
    region: ProjectMultiFactConcreteRegion,
) -> (
    tuple[
        tuple[
            tuple[ProjectGrainFactorIdentity, ...],
            tuple[tuple[ProjectActualGrainAuthorityKind, tuple[object, ...]], ...],
        ],
        ...,
    ]
    | None
):
    final_grain = region.final_properties.relational.grain
    candidates: list[
        tuple[
            tuple[ProjectGrainFactorIdentity, ...],
            list[tuple[ProjectActualGrainAuthorityKind, tuple[object, ...]]],
        ]
    ] = []
    for locality in region.localities:
        _add_factor_candidate(
            candidates,
            locality.contextual_grain.factors,
            allow_empty=locality.contextual_grain.state
            is ProjectGrainBasisState.GLOBAL,
            authority_kind=ProjectActualGrainAuthorityKind.FACT_LOCALITY,
            evidence=(locality,),
        )
    properties = _property_by_join(root)
    for join in region.region.joins:
        for side, input_properties in enumerate((join.left_input, join.right_input)):
            localized = _localized_factors(
                input_properties.grain,
                join.input_uses[side],
                final_grain,
            )
            if localized is None:
                return None
            _add_factor_candidate(
                candidates,
                localized,
                allow_empty=input_properties.grain.state
                is ProjectGrainBasisState.GLOBAL,
                authority_kind=(
                    ProjectActualGrainAuthorityKind.JOIN_LEFT_INPUT
                    if side == 0
                    else ProjectActualGrainAuthorityKind.JOIN_RIGHT_INPUT
                ),
                evidence=(join, join.input_uses[side], input_properties.grain),
            )
        source_output = join.use.source_binding.output
        if source_output is None:
            return None
        source_introduction = join.matches[0].left.introduction_use.ref
        source_factors = tuple(
            factor
            for factor in final_grain.active
            if type(factor) is ProjectJoinGrainFactorIdentity
            and factor.introduction_use == source_introduction
        )
        _add_factor_candidate(
            candidates,
            source_factors,
            allow_empty=source_output.grain.state is ProjectGrainBasisState.GLOBAL,
            authority_kind=ProjectActualGrainAuthorityKind.JOIN_SOURCE_SLICE,
            evidence=(join, join.use.source_binding, source_output.grain),
        )
        output = properties.get(join.node.ref)
        if output is None:
            return None
        _add_factor_candidate(
            candidates,
            output.relational.grain.active,
            allow_empty=output.relational.grain.state is ProjectGrainBasisState.GLOBAL,
            authority_kind=ProjectActualGrainAuthorityKind.JOIN_OUTPUT,
            evidence=(join, output.relational.grain),
        )
    return tuple((factors, tuple(authorities)) for factors, authorities in candidates)


def _expected_common_positions(
    region: ProjectMultiFactConcreteRegion,
    left: ProjectFactContextualGrain,
    right: ProjectFactContextualGrain,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    candidates = tuple(item.factors.factors for item in region.actual_candidates)
    common = tuple(
        position
        for position, candidate in enumerate(candidates)
        if _reaches(region.grain_index, left.factors, candidate)
        and _reaches(region.grain_index, right.factors, candidate)
    )
    retained = tuple(
        position
        for position in common
        if not any(
            other != position
            and _reaches(region.grain_index, candidates[other], candidates[position])
            and not _reaches(
                region.grain_index, candidates[position], candidates[other]
            )
            for other in common
        )
    )
    return common, retained


def _identity_position(values: tuple[object, ...], target: object) -> int | None:
    matches = tuple(
        position for position, value in enumerate(values) if value is target
    )
    return matches[0] if len(matches) == 1 else None


def _common_result_valid(
    region: ProjectMultiFactConcreteRegion,
    alignment: ProjectMultiFactAlignment,
) -> bool:
    common, retained = _expected_common_positions(
        region, alignment.left.contextual_grain, alignment.right.contextual_grain
    )
    result = alignment.common_grain
    expected_status = (
        ProjectCommonGrainStatus.NONE
        if not retained
        else (
            ProjectCommonGrainStatus.UNIQUE
            if len(retained) == 1
            else ProjectCommonGrainStatus.AMBIGUOUS
        )
    )
    candidate_objects = cast(tuple[object, ...], region.actual_candidates)
    actual_common = tuple(
        _identity_position(candidate_objects, item.candidate)
        for item in result.common_candidates
    )
    actual_retained = tuple(
        _identity_position(candidate_objects, item.candidate)
        for item in result.candidates
    )
    return (
        result.status is expected_status
        and _same_objects(
            cast(tuple[object, ...], result.actual_candidates),
            cast(tuple[object, ...], region.actual_candidates),
        )
        and None not in actual_common
        and actual_common == common
        and None not in actual_retained
        and actual_retained == retained
        and all(
            _determination_valid(item.left_to_candidate)
            and _determination_valid(item.right_to_candidate)
            for item in result.common_candidates
        )
    )


def _expected_structural(
    alignment: ProjectMultiFactAlignment,
) -> tuple[ProjectMultiFactStructuralAlignment, ProjectAggregateFactLocality | None]:
    comparison = alignment.grain_comparison
    if (
        alignment.left.contextual_grain.state is alignment.right.contextual_grain.state
        and alignment.left.contextual_grain.factors
        == alignment.right.contextual_grain.factors
    ):
        return ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED, None
    if comparison is None:
        return ProjectMultiFactStructuralAlignment.INCOMPATIBLE, None
    if comparison.status.value == "equal":
        return ProjectMultiFactStructuralAlignment.STRUCTURALLY_ALIGNABLE, None
    if comparison.status.value == "left_finer":
        return (
            ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED,
            alignment.left,
        )
    if comparison.status.value == "right_finer":
        return (
            ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED,
            alignment.right,
        )
    if alignment.common_grain.status in {
        ProjectCommonGrainStatus.UNIQUE,
        ProjectCommonGrainStatus.AMBIGUOUS,
    }:
        return ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED, None
    return ProjectMultiFactStructuralAlignment.INCOMPATIBLE, None


def _exposures_valid(locality: ProjectAggregateFactLocality) -> bool:
    if type(locality) is ProjectAggregateFactHomeLocality:
        return True
    join_locality = cast(ProjectAggregateFactJoinLocality, locality)
    comparison = join_locality.final_grain_comparison
    if not _comparison_valid(comparison):
        return False
    unresolved = tuple(
        factor
        for factor in comparison.right.factors
        if factor not in comparison.left_to_right.closure.factors
    )
    additions = tuple(
        factor
        for exposure in join_locality.multiplicity_exposures
        for factor in exposure.factor_additions
    )
    if comparison.status.value == "right_finer":
        return (
            len(set(additions)) == len(additions)
            and set(additions) == set(unresolved)
            and all(
                type(exposure) is ProjectFactMultiplicityExposure
                and exposure.join
                in join_locality.region.joins[
                    join_locality.region.joins.index(join_locality.introduction_join) :
                ]
                for exposure in join_locality.multiplicity_exposures
            )
        )
    return not additions


def _expected_chasm_groups(
    region: ProjectMultiFactConcreteRegion,
    pair_alignments: Mapping[tuple[int, int], ProjectMultiFactAlignment],
) -> tuple[
    tuple[ProjectActualGrainCandidate, tuple[ProjectAggregateFactJoinLocality, ...]],
    ...,
]:
    groups: list[
        tuple[ProjectActualGrainCandidate, tuple[ProjectAggregateFactJoinLocality, ...]]
    ] = []

    def incomparable(alignment: ProjectMultiFactAlignment) -> bool:
        comparison = alignment.grain_comparison
        return comparison is not None and comparison.status.value == "incomparable"

    for candidate in region.actual_candidates:
        qualifying: list[tuple[int, int]] = []
        for left in range(len(region.localities)):
            for right in range(left + 1, len(region.localities)):
                alignment = pair_alignments[(left, right)]
                if (
                    incomparable(alignment)
                    and alignment.left.contextual_grain.factors
                    and alignment.right.contextual_grain.factors
                    and any(
                        item.candidate is candidate
                        for item in alignment.common_grain.candidates
                    )
                ):
                    qualifying.append((left, right))
        if not qualifying:
            continue
        positions = tuple(
            position
            for position in range(len(region.localities))
            if any(position in pair for pair in qualifying)
        )
        complete = len(positions) * (len(positions) - 1) // 2
        for selected in (
            (positions,)
            if len(qualifying) == complete
            else tuple((left, right) for left, right in qualifying)
        ):
            if all(
                incomparable(pair_alignments[(left, right)])
                for offset, left in enumerate(selected)
                for right in selected[offset + 1 :]
            ):
                groups.append(
                    (
                        candidate,
                        tuple(region.localities[position] for position in selected),
                    )
                )
    return tuple(groups)


def _authority_matches(
    actual: ProjectActualGrainAuthority,
    expected: tuple[ProjectActualGrainAuthorityKind, tuple[object, ...]],
) -> bool:
    kind, evidence = expected
    return (
        type(actual) is ProjectActualGrainAuthority
        and actual.kind is kind
        and _same_objects(
            cast(tuple[object, ...], actual.evidence),
            evidence,
        )
    )


def _chasm_evidence_valid(
    region: ProjectMultiFactConcreteRegion,
    chasm: ProjectFactChasmCandidate,
    candidate: ProjectActualGrainCandidate,
    localities: tuple[ProjectAggregateFactJoinLocality, ...],
) -> bool:
    expected_joins = tuple(
        join
        for join in region.region.joins
        if any(locality.introduction_join is join for locality in localities)
    )
    expected_pairs = tuple(
        (left, right)
        for left in range(len(localities))
        for right in range(left + 1, len(localities))
    )
    return (
        chasm.region is region.region
        and chasm.common_grain is candidate
        and _same_objects(
            cast(tuple[object, ...], chasm.localities),
            cast(tuple[object, ...], localities),
        )
        and _same_objects(
            cast(tuple[object, ...], chasm.introduction_joins),
            cast(tuple[object, ...], expected_joins),
        )
        and len(chasm.contextual_factor_sets) == len(localities)
        and all(
            factor_set.factors == locality.contextual_grain.factors
            for factor_set, locality in zip(
                chasm.contextual_factor_sets, localities, strict=True
            )
        )
        and len(chasm.pairwise_comparisons) == len(expected_pairs)
        and all(
            comparison.left is localities[left].contextual_grain
            and comparison.right is localities[right].contextual_grain
            and comparison.status.value == "incomparable"
            and _comparison_valid(comparison)
            for comparison, (left, right) in zip(
                chasm.pairwise_comparisons, expected_pairs, strict=True
            )
        )
        and len(chasm.common_determinations) == len(localities)
        and all(
            determination.seed.factors == locality.contextual_grain.factors
            and determination.requested is candidate.factors
            and determination.status.value == "proven"
            and _determination_valid(determination)
            for determination, locality in zip(
                chasm.common_determinations, localities, strict=True
            )
        )
    )


def _verify_multifact_alignments(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    expected_home_pairs = tuple(
        (root.home_localities[left], root.home_localities[right])
        for left in range(len(root.home_localities))
        for right in range(left + 1, len(root.home_localities))
        if root.facts[left].context is root.facts[right].context
    )
    valid = len(root.home_alignments) == len(expected_home_pairs) and all(
        alignment.left is left
        and alignment.right is right
        and _comparison_valid(
            cast(ProjectFactGrainComparison, alignment.grain_comparison)
        )
        and alignment.structural is ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED
        and not alignment.multiplicity_risks
        and not alignment.requirements
        for alignment, (left, right) in zip(
            root.home_alignments, expected_home_pairs, strict=True
        )
    )
    if not valid:
        _record(issues, ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT)
        return
    for region in root.concrete_regions:
        expected_candidates = _expected_actual_candidates(root, region)
        candidate_evidence_valid = expected_candidates is not None and len(
            region.actual_candidates
        ) == len(expected_candidates)
        if expected_candidates is not None:
            candidate_evidence_valid = candidate_evidence_valid and all(
                candidate.factors.factors == factors
                and len(candidate.authorities) == len(authorities)
                and all(
                    _authority_matches(actual, expected)
                    for actual, expected in zip(
                        candidate.authorities, authorities, strict=True
                    )
                )
                for candidate, (factors, authorities) in zip(
                    region.actual_candidates, expected_candidates, strict=True
                )
            )
        if not candidate_evidence_valid:
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT,
            )
            return
        if len(region.fact_buckets) != len(region.actual_candidates) or any(
            retained is not candidate
            for retained, candidate in zip(
                region.fact_buckets, region.actual_candidates, strict=True
            )
        ):
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT,
            )
            return
        for candidate in region.actual_candidates:
            expected_bucket = tuple(
                locality
                for locality in region.localities
                if _reaches(
                    region.grain_index,
                    locality.contextual_grain.factors,
                    candidate.factors.factors,
                )
            )
            if not _same_objects(
                cast(tuple[object, ...], region.fact_buckets[candidate]),
                cast(tuple[object, ...], expected_bucket),
            ):
                _record(
                    issues,
                    ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT,
                )
                return
        expected_pairs = tuple(
            (left, right)
            for left in range(len(region.localities))
            for right in range(left + 1, len(region.localities))
        )
        if len(region.alignments) != len(expected_pairs):
            _record(
                issues,
                ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT,
            )
            return
        by_pair: dict[tuple[int, int], ProjectMultiFactAlignment] = {}
        for alignment, (left, right) in zip(
            region.alignments, expected_pairs, strict=True
        ):
            expected_structural, expected_finer = _expected_structural(alignment)
            valid = (
                alignment.left is region.localities[left]
                and alignment.right is region.localities[right]
                and alignment.grain_comparison is not None
                and _comparison_valid(alignment.grain_comparison)
                and alignment.grain_comparison.left is alignment.left.contextual_grain
                and alignment.grain_comparison.right is alignment.right.contextual_grain
                and _common_result_valid(region, alignment)
                and alignment.structural is expected_structural
                and alignment.finer is expected_finer
                and _exposures_valid(alignment.left)
                and _exposures_valid(alignment.right)
            )
            if not valid:
                _record(
                    issues,
                    ProjectPhase62VerificationIssueKind.MULTIFACT_ALIGNMENT,
                    alignment.left,
                )
                return
            by_pair[(left, right)] = alignment
        expected_chasms = _expected_chasm_groups(region, by_pair)
        if len(region.chasms) != len(expected_chasms) or any(
            not _chasm_evidence_valid(region, chasm, candidate, localities)
            for chasm, (candidate, localities) in zip(
                region.chasms, expected_chasms, strict=True
            )
        ):
            _record(issues, ProjectPhase62VerificationIssueKind.CHASM_RISK)
            return
        for (left, right), alignment in by_pair.items():
            chasms = tuple(
                chasm
                for chasm in region.chasms
                if any(region.localities[left] is item for item in chasm.localities)
                and any(region.localities[right] is item for item in chasm.localities)
            )
            expected_risks = (
                (ProjectMultiFactMultiplicityRisk.FANOUT_RISK,)
                if cast(
                    ProjectAggregateFactJoinLocality, alignment.left
                ).multiplicity_exposures
                or cast(
                    ProjectAggregateFactJoinLocality, alignment.right
                ).multiplicity_exposures
                else ()
            )
            if chasms:
                expected_risks = (
                    *expected_risks,
                    ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION,
                )
            expected_requirements = (
                (ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
                if alignment.structural
                is ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
                or expected_risks
                else ()
            )
            if (
                alignment.chasms != chasms
                or alignment.multiplicity_risks != expected_risks
                or alignment.requirements != expected_requirements
            ):
                _record(
                    issues,
                    ProjectPhase62VerificationIssueKind.CHASM_RISK,
                    alignment.left,
                )
                return


type ProjectPhase62CombinedUse = (
    ProjectIRUseOccurrence
    | ProjectIROperatorFlowUseOccurrence
    | ProjectIRJoinInputUseOccurrence
)


def _combined_nodes(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectIRPlanNodeOccurrence, ...]:
    return (
        *root.evaluation.project_plan.structural_stage.nodes,
        *root.join_regions.structural.nodes,
    )


def _combined_outputs(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectIROutputValueOccurrence, ...]:
    return (
        *root.evaluation.project_plan.structural_stage.outputs,
        *root.join_regions.structural.outputs,
    )


def _combined_uses(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectPhase62CombinedUse, ...]:
    return (
        *root.evaluation.project_plan.structural_stage.uses,
        *root.join_regions.structural.uses,
    )


def _combined_successors(
    root: ProjectMultiFactAnalysis,
) -> tuple[tuple[int, ...], ...] | None:
    nodes = _combined_nodes(root)
    positions = {node.ref: position for position, node in enumerate(nodes)}
    if len(positions) != len(nodes):
        return None
    successors: list[list[int]] = [[] for _node in nodes]
    for use in _combined_uses(root):
        producer = positions.get(use.output.producer.ref)
        consumer = positions.get(use.slot.consumer.ref)
        if (
            producer is None
            or consumer is None
            or nodes[producer] is not use.output.producer
            or nodes[consumer] is not use.slot.consumer
        ):
            return None
        successors[producer].append(consumer)
    return tuple(tuple(values) for values in successors)


def _combined_topological_order(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectIRPlanNodeOccurrence, ...] | None:
    nodes = _combined_nodes(root)
    successors = _combined_successors(root)
    if successors is None:
        return None
    indegree = [0] * len(nodes)
    for values in successors:
        for consumer in values:
            indegree[consumer] += 1
    ready: list[tuple[int, int]] = []
    for position, (node, degree) in enumerate(zip(nodes, indegree, strict=True)):
        if degree == 0:
            heappush(ready, (node.ref.position, position))
    order: list[ProjectIRPlanNodeOccurrence] = []
    while ready:
        _, position = heappop(ready)
        order.append(nodes[position])
        for consumer in successors[position]:
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                heappush(ready, (nodes[consumer].ref.position, consumer))
    return tuple(order) if len(order) == len(nodes) else None


def _verify_combined_cycle(
    root: ProjectMultiFactAnalysis,
    issues: list[ProjectPhase62VerificationIssue],
) -> None:
    if (
        _combined_successors(root) is not None
        and _combined_topological_order(root) is None
    ):
        _record(issues, ProjectPhase62VerificationIssueKind.COMBINED_ACTUAL_USE_CYCLE)


def verify_project_phase62(
    root: ProjectMultiFactAnalysis,
) -> ProjectPhase62VerificationResult:
    """Freshly verify one exact Phase-62 root without invoking builders."""

    if type(root) is not ProjectMultiFactAnalysis:
        raise TypeError("Phase-62 verification requires one exact root.")
    issues: list[ProjectPhase62VerificationIssue] = []
    coherent = _root_is_coherent(root, issues)
    base_verification = verify_project_ir_stage(root.evaluation)
    if not base_verification.verified:
        _record(
            issues,
            ProjectPhase62VerificationIssueKind.BASE_PROJECT_IR,
            base_verification.issues[0].coordinate
            if base_verification.issues
            else None,
        )
    if coherent:
        _verify_join_scope_coordinates(root, issues)
        _verify_join_structural_endpoints(root, issues)
        _verify_join_region_completeness(root, issues)
        join_shape_valid = not any(
            issue.kind
            in {
                ProjectPhase62VerificationIssueKind.JOIN_SCOPE_COORDINATE,
                ProjectPhase62VerificationIssueKind.JOIN_STRUCTURAL_ENDPOINT,
                ProjectPhase62VerificationIssueKind.JOIN_REGION_COMPLETENESS,
            }
            for issue in issues
        )
        if join_shape_valid:
            _verify_join_conditions(root, issues)
            _verify_join_effects_and_nulling(root, issues)
            _verify_join_property_transfer(root, issues)
            _verify_join_key_fd_grain(root, issues)
        _verify_multifact_catalog(root, issues)
        if not any(
            issue.kind is ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG
            for issue in issues
        ):
            _verify_multifact_localities(root, issues)
        if not any(
            issue.kind
            in {
                ProjectPhase62VerificationIssueKind.MULTIFACT_CATALOG,
                ProjectPhase62VerificationIssueKind.MULTIFACT_LOCALITY,
            }
            for issue in issues
        ):
            _verify_multifact_alignments(root, issues)
        _verify_combined_cycle(root, issues)
    issue_tuple = tuple(issues)
    return ProjectPhase62VerificationResult(
        root=root,
        base_verification=base_verification,
        status=(
            ProjectPhase62VerificationStatus.VERIFIED
            if not issue_tuple
            else ProjectPhase62VerificationStatus.INVALID
        ),
        issues=issue_tuple,
    )


class ProjectPhase62AnalysisKind(StrEnum):
    COMBINED_REVERSE_USE_INDEX = "combined_reverse_use_index"
    COMBINED_TOPOLOGICAL_ORDER = "combined_topological_order"
    NULLING_PROVENANCE_INDEX = "nulling_provenance_index"
    FACT_LOCALITY_INDEX = "fact_locality_index"
    MULTIFACT_ALIGNMENT_INDEX = "multifact_alignment_index"


class ProjectPhase62ChangeDomain(StrEnum):
    BASE_TOPOLOGY = "base_topology"
    BASE_SEMANTICS = "base_semantics"
    RELATIONSHIP_USE_AUTHORITY = "relationship_use_authority"
    JOIN_TOPOLOGY = "join_topology"
    JOIN_SEMANTICS = "join_semantics"
    JOIN_PROPERTIES = "join_properties"
    MULTIFACT_LOCALITY = "multifact_locality"
    MULTIFACT_ALIGNMENT = "multifact_alignment"
    ESTIMATES = "estimates"


class ProjectPhase62VerificationRequirement(StrEnum):
    RERUN_REQUIRED = "rerun_required"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62CombinedReverseUseEntry:
    output: ProjectIROutputValueOccurrence
    uses: tuple[ProjectPhase62CombinedUse, ...]

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIROutputValueOccurrence:
            raise TypeError("Combined reverse-use entry requires an exact output.")
        if type(self.uses) is not tuple or any(
            type(use)
            not in {
                ProjectIRUseOccurrence,
                ProjectIROperatorFlowUseOccurrence,
                ProjectIRJoinInputUseOccurrence,
            }
            or use.output is not self.output
            for use in self.uses
        ):
            raise ValueError("Combined reverse-use entry requires exact direct uses.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62NullingCoordinate:
    output: ProjectIROutputValueRef
    field_position: int

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIROutputValueRef:
            raise TypeError("Nulling coordinate requires an exact output ref.")
        if type(self.field_position) is not int or self.field_position < 0:
            raise ValueError("Nulling field position must be non-negative.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62NullingProvenanceEntry:
    coordinate: ProjectPhase62NullingCoordinate
    field: ProjectIRJoinedRowField = field(repr=False, compare=False, hash=False)
    nulling_joins: tuple[ProjectIRPlanNodeRef, ...]

    def __post_init__(self) -> None:
        if (
            type(self.coordinate) is not ProjectPhase62NullingCoordinate
            or type(self.field) is not ProjectIRJoinedRowField
            or self.field.field_position != self.coordinate.field_position
            or self.field.nulling_joins != self.nulling_joins
        ):
            raise ValueError("Nulling entry requires one exact joined field.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62FactLocalityEntry:
    fact: ProjectAggregateFactOccurrence = field(repr=False, compare=False, hash=False)
    identity: ProjectAggregateFactIdentity
    localities: tuple[ProjectAggregateFactLocality, ...]

    def __post_init__(self) -> None:
        if (
            type(self.fact) is not ProjectAggregateFactOccurrence
            or self.identity != self.fact.identity
            or not self.localities
            or self.localities[0].fact is not self.fact
            or type(self.localities[0]) is not ProjectAggregateFactHomeLocality
            or any(locality.fact is not self.fact for locality in self.localities)
        ):
            raise ValueError("Fact-locality entry requires exact canonical localities.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62MultiFactAlignmentIndex:
    alignments: tuple[ProjectMultiFactAlignment, ...]
    chasms: tuple[ProjectFactChasmCandidate, ...]

    def __post_init__(self) -> None:
        if type(self.alignments) is not tuple or any(
            type(item) is not ProjectMultiFactAlignment for item in self.alignments
        ):
            raise TypeError("Alignment index requires exact alignments.")
        if type(self.chasms) is not tuple or any(
            type(item) is not ProjectFactChasmCandidate for item in self.chasms
        ):
            raise TypeError("Alignment index requires exact chasms.")


def _derive_reverse_uses(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectPhase62CombinedReverseUseEntry, ...]:
    uses = _combined_uses(root)
    return tuple(
        ProjectPhase62CombinedReverseUseEntry(
            output=output,
            uses=tuple(use for use in uses if use.output is output),
        )
        for output in _combined_outputs(root)
    )


def _derive_nulling_index(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectPhase62NullingProvenanceEntry, ...]:
    return tuple(
        ProjectPhase62NullingProvenanceEntry(
            coordinate=ProjectPhase62NullingCoordinate(
                output=join.output.occurrence.ref,
                field_position=field.field_position,
            ),
            field=field,
            nulling_joins=field.nulling_joins,
        )
        for join in _joins(root)
        for field in join.output.row_shape.fields
    )


def _derive_fact_locality_index(
    root: ProjectMultiFactAnalysis,
) -> tuple[ProjectPhase62FactLocalityEntry, ...]:
    return tuple(
        ProjectPhase62FactLocalityEntry(
            fact=fact,
            identity=fact.identity,
            localities=(
                root.home_localities[position],
                *(
                    locality
                    for locality in root.join_localities
                    if locality.fact is fact
                ),
            ),
        )
        for position, fact in enumerate(root.facts)
    )


def _derive_alignment_index(
    root: ProjectMultiFactAnalysis,
) -> ProjectPhase62MultiFactAlignmentIndex:
    return ProjectPhase62MultiFactAlignmentIndex(
        alignments=root.alignments,
        chasms=tuple(
            chasm for region in root.concrete_regions for chasm in region.chasms
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62AnalysisBundle:
    verification: ProjectPhase62VerificationResult
    combined_reverse_uses: tuple[ProjectPhase62CombinedReverseUseEntry, ...]
    combined_topological_order: tuple[ProjectIRPlanNodeOccurrence, ...]
    nulling_provenance: tuple[ProjectPhase62NullingProvenanceEntry, ...]
    fact_localities: tuple[ProjectPhase62FactLocalityEntry, ...]
    multifact_alignments: ProjectPhase62MultiFactAlignmentIndex

    def __post_init__(self) -> None:
        if (
            type(self.verification) is not ProjectPhase62VerificationResult
            or not self.verification.verified
            or self.verification.issues
        ):
            raise ValueError("Phase-62 analyses require one VERIFIED result.")
        root = self.verification.root
        expected_topological = _combined_topological_order(root)
        expected_alignment = _derive_alignment_index(root)
        valid = (
            _same_reverse_uses(self.combined_reverse_uses, _derive_reverse_uses(root))
            and expected_topological is not None
            and _same_objects(
                cast(tuple[object, ...], self.combined_topological_order),
                cast(tuple[object, ...], expected_topological or ()),
            )
            and _same_nulling(self.nulling_provenance, _derive_nulling_index(root))
            and _same_fact_localities(
                self.fact_localities, _derive_fact_locality_index(root)
            )
            and _same_objects(
                cast(tuple[object, ...], self.multifact_alignments.alignments),
                cast(tuple[object, ...], expected_alignment.alignments),
            )
            and _same_objects(
                cast(tuple[object, ...], self.multifact_alignments.chasms),
                cast(tuple[object, ...], expected_alignment.chasms),
            )
        )
        if not valid:
            raise ValueError("Phase-62 bundle must retain fresh canonical products.")

    @property
    def root(self) -> ProjectMultiFactAnalysis:
        return self.verification.root


def _same_reverse_uses(
    actual: tuple[ProjectPhase62CombinedReverseUseEntry, ...],
    expected: tuple[ProjectPhase62CombinedReverseUseEntry, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.output is retained.output
        and _same_objects(
            cast(tuple[object, ...], item.uses),
            cast(tuple[object, ...], retained.uses),
        )
        for item, retained in zip(actual, expected, strict=True)
    )


def _same_nulling(
    actual: tuple[ProjectPhase62NullingProvenanceEntry, ...],
    expected: tuple[ProjectPhase62NullingProvenanceEntry, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.coordinate == retained.coordinate
        and item.field is retained.field
        and item.nulling_joins == retained.nulling_joins
        for item, retained in zip(actual, expected, strict=True)
    )


def _same_fact_localities(
    actual: tuple[ProjectPhase62FactLocalityEntry, ...],
    expected: tuple[ProjectPhase62FactLocalityEntry, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.fact is retained.fact
        and item.identity == retained.identity
        and _same_objects(
            cast(tuple[object, ...], item.localities),
            cast(tuple[object, ...], retained.localities),
        )
        for item, retained in zip(actual, expected, strict=True)
    )


def build_project_phase62_analysis_bundle(
    verification: ProjectPhase62VerificationResult,
) -> ProjectPhase62AnalysisBundle:
    """Rederive all five detachable analyses from the verified current root."""

    if (
        type(verification) is not ProjectPhase62VerificationResult
        or not verification.verified
    ):
        raise ValueError("Only VERIFIED Phase-62 roots may produce analyses.")
    root = verification.root
    topological = _combined_topological_order(root)
    if topological is None:
        raise ValueError("Verified combined actual-use graph must remain acyclic.")
    return ProjectPhase62AnalysisBundle(
        verification=verification,
        combined_reverse_uses=_derive_reverse_uses(root),
        combined_topological_order=topological,
        nulling_provenance=_derive_nulling_index(root),
        fact_localities=_derive_fact_locality_index(root),
        multifact_alignments=_derive_alignment_index(root),
    )


def _analysis_dependencies(
    kind: ProjectPhase62AnalysisKind,
) -> tuple[ProjectPhase62ChangeDomain, ...]:
    if kind in {
        ProjectPhase62AnalysisKind.COMBINED_REVERSE_USE_INDEX,
        ProjectPhase62AnalysisKind.COMBINED_TOPOLOGICAL_ORDER,
    }:
        return (
            ProjectPhase62ChangeDomain.BASE_TOPOLOGY,
            ProjectPhase62ChangeDomain.JOIN_TOPOLOGY,
        )
    if kind is ProjectPhase62AnalysisKind.NULLING_PROVENANCE_INDEX:
        return (
            ProjectPhase62ChangeDomain.BASE_TOPOLOGY,
            ProjectPhase62ChangeDomain.JOIN_TOPOLOGY,
            ProjectPhase62ChangeDomain.RELATIONSHIP_USE_AUTHORITY,
            ProjectPhase62ChangeDomain.JOIN_SEMANTICS,
            ProjectPhase62ChangeDomain.JOIN_PROPERTIES,
        )
    if kind is ProjectPhase62AnalysisKind.FACT_LOCALITY_INDEX:
        return (
            ProjectPhase62ChangeDomain.BASE_TOPOLOGY,
            ProjectPhase62ChangeDomain.JOIN_TOPOLOGY,
            ProjectPhase62ChangeDomain.RELATIONSHIP_USE_AUTHORITY,
            ProjectPhase62ChangeDomain.JOIN_SEMANTICS,
            ProjectPhase62ChangeDomain.JOIN_PROPERTIES,
            ProjectPhase62ChangeDomain.BASE_SEMANTICS,
            ProjectPhase62ChangeDomain.MULTIFACT_LOCALITY,
        )
    return (
        ProjectPhase62ChangeDomain.BASE_TOPOLOGY,
        ProjectPhase62ChangeDomain.JOIN_TOPOLOGY,
        ProjectPhase62ChangeDomain.RELATIONSHIP_USE_AUTHORITY,
        ProjectPhase62ChangeDomain.JOIN_SEMANTICS,
        ProjectPhase62ChangeDomain.JOIN_PROPERTIES,
        ProjectPhase62ChangeDomain.BASE_SEMANTICS,
        ProjectPhase62ChangeDomain.MULTIFACT_LOCALITY,
        ProjectPhase62ChangeDomain.MULTIFACT_ALIGNMENT,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62AnalysisInvalidation:
    changed_domains: tuple[ProjectPhase62ChangeDomain, ...]
    invalidated: tuple[ProjectPhase62AnalysisKind, ...]
    preserved: tuple[ProjectPhase62AnalysisKind, ...]
    verification: ProjectPhase62VerificationRequirement = field(
        init=False,
        default=ProjectPhase62VerificationRequirement.RERUN_REQUIRED,
    )

    def __post_init__(self) -> None:
        order = tuple(ProjectPhase62ChangeDomain)
        if (
            type(self.changed_domains) is not tuple
            or not self.changed_domains
            or any(
                type(domain) is not ProjectPhase62ChangeDomain
                for domain in self.changed_domains
            )
            or len(set(self.changed_domains)) != len(self.changed_domains)
            or self.changed_domains
            != tuple(sorted(self.changed_domains, key=order.index))
        ):
            raise ValueError("Phase-62 change domains must be unique and canonical.")
        expected_invalidated = tuple(
            kind
            for kind in ProjectPhase62AnalysisKind
            if any(
                domain in self.changed_domains
                for domain in _analysis_dependencies(kind)
            )
        )
        expected_preserved = tuple(
            kind
            for kind in ProjectPhase62AnalysisKind
            if kind not in expected_invalidated
        )
        if (
            self.invalidated != expected_invalidated
            or self.preserved != expected_preserved
        ):
            raise ValueError("Phase-62 invalidation disagrees with dependencies.")


def assess_project_phase62_analysis_invalidation(
    changed_domains: tuple[ProjectPhase62ChangeDomain, ...],
) -> ProjectPhase62AnalysisInvalidation:
    """Derive conservative preservation without ever preserving verification."""

    invalidated = tuple(
        kind
        for kind in ProjectPhase62AnalysisKind
        if any(domain in changed_domains for domain in _analysis_dependencies(kind))
    )
    return ProjectPhase62AnalysisInvalidation(
        changed_domains=changed_domains,
        invalidated=invalidated,
        preserved=tuple(
            kind for kind in ProjectPhase62AnalysisKind if kind not in invalidated
        ),
    )
