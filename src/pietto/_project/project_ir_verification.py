"""Independent Project IR verification and detachable derived analyses."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from heapq import heappop, heappush
from typing import cast

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadinessStatus,
)
from pietto._project.model import ProjectRelationRowSchemaStatus, ProjectSymbolKind
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleDependencyKind,
    ProjectModuleReferenceRole,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
)
from pietto._project.project_ir import (
    ProjectIRConcreteRelationSubject,
    ProjectIRFieldAnchor,
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIRNonConcreteRelationSubject,
    ProjectIROperatorFlowUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRRelationAnchor,
    ProjectIRRelationConstructionState,
    ProjectIRResolvedFieldAnchor,
    ProjectIRResolvedRelationAnchor,
    ProjectIRSnapshotScope,
    ProjectIRStageFieldAnchor,
    ProjectIRStructuralStage,
    ProjectIRUseOccurrence,
    ProjectIRUseRef,
)
from pietto._project.project_ir_composition import (
    ProjectIRCrossRelationEdge,
    ProjectIRProjectPlan,
)
from pietto._project.project_ir_construction import (
    ProjectIRAllocationState,
    ProjectIRConcreteSingleRelationFragment,
    ProjectIRNonConcreteSingleRelationFragment,
)
from pietto._project.project_ir_evaluation_context import (
    ProjectIRAggregateEvaluationContext,
    ProjectIREvaluationContextStage,
    ProjectIRWindowOperatorEvaluationContext,
    ProjectIRWindowResultEvaluationContext,
)
from pietto._project.project_ir_operators import (
    ProjectIREstablishedPropertyTransfer,
    ProjectIRLogicalOperatorKind,
    ProjectIRLogicalOperatorOccurrence,
    ProjectIRPreservedPropertyTransfer,
    ProjectIRRowShapeCompatibility,
    ProjectIRRowShapeCompatibilityStatus,
    ProjectIRUnavailablePropertyTransfer,
)
from pietto._project.project_ir_properties import (
    ProjectIRCurrentOutput,
    ProjectIRDeterminismEvidence,
    ProjectIREffectEvidence,
    ProjectIRErrorBehaviorEvidence,
    ProjectIREvaluationCountEvidence,
    ProjectIRPropertyStage,
    ProjectIRPropertyAvailability,
    ProjectIRProvidedBagMultiplicity,
    ProjectIRProvidedCardinalityUpperBound,
    ProjectIRProvidedClosedBindings,
    ProjectIRProvidedEvaluationPolicy,
    ProjectIRProvidedLocalGrainEvidence,
    ProjectIRProvidedOutputShape,
    ProjectIRProvidedProperty,
    ProjectIRProvidedPropertySlot,
    ProjectIRProvidedRelationOrdering,
    ProjectIRRelationRowOutput,
    ProjectIRRequiredRowShape,
    ProjectIRRowField,
    ProjectIRRowShape,
    ProjectIRScalarFieldOutput,
    ProjectIRSideEffectEvidence,
    ProjectIRStageRowCheckpoint,
    ProjectIRStageRowCheckpointKind,
    ProjectIRStageRowField,
    ProjectIRStageRowShape,
    ProjectIRStageScalarFieldOutput,
    ProjectIRUnavailableProvidedProperty,
)
from pietto.ast_nodes import LiteralExpr, QueryDef, SourceDef, TableDef
from pietto.semantic.relation_limits import MAX_RELATION_LIMIT

__all__: tuple[str, ...] = ()


class ProjectIRVerificationStatus(StrEnum):
    """Independent verification outcome, never semantic authority."""

    VERIFIED = "verified"
    INVALID = "invalid"


class ProjectIRVerificationIssueKind(StrEnum):
    """Fixed independent verification-pass order."""

    SNAPSHOT_SCOPE = "snapshot_scope"
    REF_COORDINATE = "ref_coordinate"
    STRUCTURAL_ENDPOINT = "structural_endpoint"
    INPUT_SLOT_ATTACHMENT = "input_slot_attachment"
    FRAGMENT_COMPOSITION = "fragment_composition"
    OPERATOR_LEGALITY = "operator_legality"
    OPERATOR_FLOW = "operator_flow"
    CROSS_RELATION_ENDPOINT = "cross_relation_endpoint"
    ROW_COMPATIBILITY = "row_compatibility"
    PROPERTY_ATTACHMENT = "property_attachment"
    PROPERTY_TRANSFER = "property_transfer"
    EFFECT_ATTACHMENT = "effect_attachment"
    NON_CONCRETE_TERMINAL = "non_concrete_terminal"
    EVALUATION_CONTEXT = "evaluation_context"
    ACTUAL_USE_CYCLE = "actual_use_cycle"
    PROVENANCE_REACHABILITY = "provenance_reachability"


type ProjectIRVerificationCoordinate = (
    ProjectIRPlanNodeRef
    | ProjectIROutputValueRef
    | ProjectIRUseRef
    | ProjectIRInputSlotRef
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRVerificationIssue:
    """One typed issue at an optional exact Project occurrence coordinate."""

    kind: ProjectIRVerificationIssueKind
    coordinate: ProjectIRVerificationCoordinate | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectIRVerificationIssueKind:
            raise TypeError("Verification issue requires an exact kind.")
        if self.coordinate is not None and type(self.coordinate) not in {
            ProjectIRPlanNodeRef,
            ProjectIROutputValueRef,
            ProjectIRUseRef,
            ProjectIRInputSlotRef,
        }:
            raise TypeError("Verification issue requires a typed coordinate.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRVerificationResult:
    """Deterministic verification result retaining the exact checked stage."""

    stage: ProjectIREvaluationContextStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    status: ProjectIRVerificationStatus
    issues: tuple[ProjectIRVerificationIssue, ...] = ()

    def __post_init__(self) -> None:
        if type(self.stage) is not ProjectIREvaluationContextStage:
            raise TypeError("Verification result requires the exact checked stage.")
        if type(self.status) is not ProjectIRVerificationStatus:
            raise TypeError("Verification result requires an exact status.")
        if type(self.issues) is not tuple or any(
            type(issue) is not ProjectIRVerificationIssue for issue in self.issues
        ):
            raise TypeError("Verification issues must be an exact tuple.")
        issue_order = tuple(ProjectIRVerificationIssueKind)
        if tuple(issue_order.index(issue.kind) for issue in self.issues) != tuple(
            sorted(issue_order.index(issue.kind) for issue in self.issues)
        ):
            raise ValueError("Verification issues must retain fixed pass order.")
        if (self.status is ProjectIRVerificationStatus.VERIFIED) is bool(self.issues):
            raise ValueError("Verification status and issue collection disagree.")

    @property
    def verified(self) -> bool:
        return self.status is ProjectIRVerificationStatus.VERIFIED


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is expected_item
        for item, expected_item in zip(actual, expected, strict=True)
    )


def _identity_indices(values: tuple[object, ...], target: object) -> tuple[int, ...]:
    return tuple(index for index, value in enumerate(values) if value is target)


def _coordinate(subject: object | None) -> ProjectIRVerificationCoordinate | None:
    if type(subject) in {
        ProjectIRPlanNodeRef,
        ProjectIROutputValueRef,
        ProjectIRUseRef,
        ProjectIRInputSlotRef,
    }:
        return cast(ProjectIRVerificationCoordinate, subject)
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
    if type(subject) is ProjectIRCrossRelationEdge:
        return subject.use.ref
    if type(subject) is ProjectIRConcreteSingleRelationFragment:
        return subject.root.ref
    if type(subject) is ProjectIRLogicalOperatorOccurrence:
        return subject.node.ref
    if type(subject) is ProjectIRAggregateEvaluationContext:
        return subject.operator.node.ref
    if type(subject) is ProjectIRWindowOperatorEvaluationContext:
        return subject.operator.node.ref
    if type(subject) is ProjectIRWindowResultEvaluationContext:
        return subject.stage_scalar_output.occurrence.ref
    return None


def _record(
    issues: list[ProjectIRVerificationIssue],
    kind: ProjectIRVerificationIssueKind,
    subject: object | None = None,
) -> None:
    issues.append(
        ProjectIRVerificationIssue(kind=kind, coordinate=_coordinate(subject))
    )


def _verify_scopes_and_coordinates(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    structural = plan.structural_stage
    start = plan.starting_allocation
    end = plan.ending_allocation
    if (
        type(structural.scope) is not ProjectIRSnapshotScope
        or type(start) is not ProjectIRAllocationState
        or type(end) is not ProjectIRAllocationState
        or start.scope is not structural.scope
        or end.scope is not structural.scope
    ):
        _record(issues, ProjectIRVerificationIssueKind.SNAPSHOT_SCOPE)
        return

    collections = (
        (
            structural.nodes,
            ProjectIRPlanNodeRef,
            start.next_plan_node_position,
            end.next_plan_node_position,
        ),
        (
            structural.outputs,
            ProjectIROutputValueRef,
            start.next_output_value_position,
            end.next_output_value_position,
        ),
        (
            structural.input_slots,
            ProjectIRInputSlotRef,
            start.next_input_slot_position,
            end.next_input_slot_position,
        ),
        (
            structural.uses,
            ProjectIRUseRef,
            start.next_use_position,
            end.next_use_position,
        ),
    )
    for values, ref_type, first, stop in collections:
        expected_positions = tuple(range(first, stop))
        if len(values) != len(expected_positions):
            _record(issues, ProjectIRVerificationIssueKind.REF_COORDINATE)
        for index, value in enumerate(values):
            ref = value.ref
            if type(ref) is not ref_type or ref.scope is not structural.scope:
                _record(issues, ProjectIRVerificationIssueKind.SNAPSHOT_SCOPE, ref)
                continue
            if (
                index >= len(expected_positions)
                or ref.position != expected_positions[index]
            ):
                _record(issues, ProjectIRVerificationIssueKind.REF_COORDINATE, ref)

    for fragment in plan.fragments:
        if (
            fragment.structural_stage.scope is not structural.scope
            or fragment.starting_allocation.scope is not structural.scope
            or fragment.ending_allocation.scope is not structural.scope
        ):
            _record(issues, ProjectIRVerificationIssueKind.SNAPSHOT_SCOPE, fragment)


def _verify_structural_endpoints(
    structural: ProjectIRStructuralStage,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    nodes = cast(tuple[object, ...], structural.nodes)
    outputs = cast(tuple[object, ...], structural.outputs)
    slots = cast(tuple[object, ...], structural.input_slots)
    for output in structural.outputs:
        producer_matches = _identity_indices(nodes, output.producer)
        anchor = output.anchor
        anchor_ok = (
            (
                type(anchor) is ProjectIRRelationAnchor
                and anchor == output.producer.anchor
            )
            or (
                type(anchor) is ProjectIRFieldAnchor
                and anchor.identity.owner == output.producer.anchor.identity
            )
            or (
                type(anchor) is ProjectIRStageFieldAnchor
                and anchor.producer is output.producer
            )
        )
        if len(producer_matches) != 1 or not anchor_ok:
            _record(
                issues,
                ProjectIRVerificationIssueKind.STRUCTURAL_ENDPOINT,
                output,
            )
    for slot in structural.input_slots:
        if len(_identity_indices(nodes, slot.consumer)) != 1:
            _record(
                issues,
                ProjectIRVerificationIssueKind.STRUCTURAL_ENDPOINT,
                slot,
            )
    for use in structural.uses:
        if (
            len(_identity_indices(outputs, use.output)) != 1
            or len(_identity_indices(slots, use.slot)) != 1
        ):
            _record(
                issues,
                ProjectIRVerificationIssueKind.STRUCTURAL_ENDPOINT,
                use,
            )
            continue
        if type(use) is ProjectIROperatorFlowUseOccurrence:
            valid = (
                type(use.output.anchor) is ProjectIRRelationAnchor
                and use.output.producer.anchor == use.slot.consumer.anchor
                and use.output.producer is not use.slot.consumer
                and use.slot.input_ordinal == 0
            )
        elif type(use) is ProjectIRUseOccurrence:
            anchor = use.anchor
            valid = False
            if type(anchor) is ProjectIRResolvedRelationAnchor:
                valid = (
                    use.role is ProjectModuleFactOccurrenceRole.RELATION_INPUT
                    and type(use.output.anchor) is ProjectIRRelationAnchor
                    and anchor.target == use.output.anchor.identity
                    and anchor.reference.owner == use.slot.consumer.anchor.identity
                )
            elif type(anchor) is ProjectIRResolvedFieldAnchor:
                valid = (
                    use.role is not ProjectModuleFactOccurrenceRole.RELATION_INPUT
                    and type(use.output.anchor) is ProjectIRFieldAnchor
                    and anchor.target == use.output.anchor.identity
                    and anchor.reference.owner == use.slot.consumer.anchor.identity
                )
        else:
            valid = False
        if not valid:
            _record(
                issues,
                ProjectIRVerificationIssueKind.STRUCTURAL_ENDPOINT,
                use,
            )


def _verify_slot_attachments(
    structural: ProjectIRStructuralStage,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    keys: list[tuple[ProjectIRPlanNodeRef, int]] = []
    for slot in structural.input_slots:
        keys.append((slot.consumer.ref, slot.input_ordinal))
        if sum(use.slot is slot for use in structural.uses) != 1:
            _record(
                issues,
                ProjectIRVerificationIssueKind.INPUT_SLOT_ATTACHMENT,
                slot,
            )
    if len(set(keys)) != len(keys):
        _record(issues, ProjectIRVerificationIssueKind.INPUT_SLOT_ATTACHMENT)


def _canonical_semantic_facts(
    plan: ProjectIRProjectPlan,
) -> tuple[ProjectModuleRelationSemanticFacts, ...]:
    return tuple(
        fact
        for environment in plan.semantic_facts.environments
        for fact in environment.relation_facts
    )


def _semantic_identity(
    evidence: ProjectModuleRelationSemanticFacts,
) -> ProjectDeclarationOccurrenceIdentity:
    owner = evidence.owner
    return ProjectDeclarationOccurrenceIdentity(
        identity=owner.identity,
        module_position=owner.module_position,
        declaration_position=owner.declaration_position,
    )


def _semantic_has_ambiguity(evidence: ProjectModuleRelationSemanticFacts) -> bool:
    ambiguous = ProjectModuleCandidateBucketStatus.AMBIGUOUS
    return (
        any(item.status is ambiguous for item in evidence.clause_dependencies)
        or any(
            reference.status is ambiguous
            for binding in evidence.let_bindings
            for reference in binding.references
        )
        or any(
            reference.status is ambiguous
            for selected in evidence.select_facts
            for reference in selected.references
        )
    )


def _subject_valid(fragment: object) -> bool:
    if type(fragment) is ProjectIRConcreteSingleRelationFragment:
        subject = fragment.subject
        return (
            type(subject) is ProjectIRConcreteRelationSubject
            and subject.evidence is fragment.semantic_facts
            and subject.anchor.identity == _semantic_identity(fragment.semantic_facts)
            and fragment.semantic_facts.state.status
            is ProjectRelationRowSchemaStatus.CONCRETE
            and subject.root is fragment.root
            and subject.root.anchor == subject.anchor
        )
    if type(fragment) is not ProjectIRNonConcreteSingleRelationFragment:
        return False
    subject = fragment.subject
    evidence = subject.evidence
    if (
        type(subject) is not ProjectIRNonConcreteRelationSubject
        or type(evidence) is not ProjectModuleRelationSemanticFacts
        or evidence is not fragment.semantic_facts
        or subject.anchor.identity != _semantic_identity(evidence)
    ):
        return False
    expected = (
        ProjectIRRelationConstructionState.AMBIGUOUS
        if _semantic_has_ambiguity(evidence)
        else {
            ProjectRelationRowSchemaStatus.UNKNOWN: (
                ProjectIRRelationConstructionState.UNKNOWN
            ),
            ProjectRelationRowSchemaStatus.DEFERRED: (
                ProjectIRRelationConstructionState.DEFERRED
            ),
            ProjectRelationRowSchemaStatus.BLOCKED: (
                ProjectIRRelationConstructionState.BLOCKED
            ),
        }.get(evidence.state.status)
    )
    return subject.state is expected


def _fragment_type(fragment: object) -> bool:
    return type(fragment) in {
        ProjectIRConcreteSingleRelationFragment,
        ProjectIRNonConcreteSingleRelationFragment,
    }


def _verify_fragment_composition(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    if plan.attribution._authority.semantic_facts is not plan.semantic_facts or any(
        not _fragment_type(fragment) for fragment in plan.fragments
    ):
        _record(issues, ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION)
    canonical = _canonical_semantic_facts(plan)
    if len(plan.fragments) != len(canonical) or any(
        fragment.semantic_facts is not fact
        for fragment, fact in zip(plan.fragments, canonical, strict=False)
    ):
        _record(issues, ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION)

    current = plan.starting_allocation
    for fragment in plan.fragments:
        valid = (
            _subject_valid(fragment)
            and fragment.attribution is plan.attribution
            and fragment.starting_allocation is current
            and fragment.property_stage.structural is fragment.structural_stage
            and fragment.logical_stage.property_stage is fragment.property_stage
            and fragment.structural_stage.subjects == (fragment.subject,)
        )
        if type(fragment) is ProjectIRConcreteSingleRelationFragment:
            final_operator = next(
                (
                    operator
                    for operator in fragment.logical_stage.operators
                    if operator.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION
                ),
                None,
            )
            expected_scalars = tuple(
                output
                for output in fragment.property_stage.outputs
                if type(output) is ProjectIRScalarFieldOutput
                and final_operator is not None
                and output.occurrence.producer is final_operator.node
            )
            valid = valid and (
                fragment.subject.root is fragment.root
                and type(fragment.root_relation_output) is ProjectIRRelationRowOutput
                and fragment.root_relation_output.occurrence.producer is fragment.root
                and any(
                    fragment.root_relation_output is output
                    for output in fragment.property_stage.outputs
                )
                and _same_objects(
                    cast(tuple[object, ...], fragment.final_scalar_outputs),
                    cast(tuple[object, ...], expected_scalars),
                )
            )
        else:
            valid = valid and fragment.ending_allocation is fragment.starting_allocation
        if not valid:
            _record(
                issues,
                ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION,
                fragment,
            )
        current = fragment.ending_allocation

    expected_nodes = tuple(
        node for fragment in plan.fragments for node in fragment.structural_stage.nodes
    )
    expected_outputs = tuple(
        output
        for fragment in plan.fragments
        for output in fragment.structural_stage.outputs
    )
    expected_slots = (
        *(
            slot
            for fragment in plan.fragments
            for slot in fragment.structural_stage.input_slots
        ),
        *(edge.input_slot for edge in plan.cross_relation_edges),
    )
    expected_uses = (
        *(use for fragment in plan.fragments for use in fragment.structural_stage.uses),
        *(edge.use for edge in plan.cross_relation_edges),
    )
    expected_subjects = tuple(
        subject
        for fragment in plan.fragments
        for subject in fragment.structural_stage.subjects
    )
    structural = plan.structural_stage
    if not (
        _same_objects(cast(tuple[object, ...], structural.nodes), expected_nodes)
        and _same_objects(
            cast(tuple[object, ...], structural.outputs), expected_outputs
        )
        and _same_objects(
            cast(tuple[object, ...], structural.input_slots), expected_slots
        )
        and _same_objects(cast(tuple[object, ...], structural.uses), expected_uses)
        and _same_objects(
            cast(tuple[object, ...], structural.subjects), expected_subjects
        )
    ):
        _record(issues, ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION)

    expected_consumers = tuple(
        fragment
        for fragment in plan.fragments
        if type(fragment) is ProjectIRConcreteSingleRelationFragment
        and fragment.semantic_facts.owner.identity.declaration_kind
        in {ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY}
    )
    if len(plan.cross_relation_edges) != len(expected_consumers) or any(
        edge.consumer is not consumer
        for edge, consumer in zip(
            plan.cross_relation_edges,
            expected_consumers,
            strict=False,
        )
    ):
        _record(issues, ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION)
    expected_end = (
        current.next_plan_node_position,
        current.next_output_value_position,
        current.next_input_slot_position + len(plan.cross_relation_edges),
        current.next_use_position + len(plan.cross_relation_edges),
    )
    actual_end = (
        plan.ending_allocation.next_plan_node_position,
        plan.ending_allocation.next_output_value_position,
        plan.ending_allocation.next_input_slot_position,
        plan.ending_allocation.next_use_position,
    )
    if actual_end != expected_end:
        _record(issues, ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION)


def _independent_operator_kinds(
    evidence: ProjectModuleRelationSemanticFacts,
) -> tuple[ProjectIRLogicalOperatorKind, ...] | None:
    definition = evidence.owner.definition
    if type(definition) is SourceDef:
        return (
            (ProjectIRLogicalOperatorKind.RELATION_INPUT,)
            if evidence.resolution is None
            else None
        )
    if type(definition) not in {TableDef, QueryDef} or evidence.resolution is None:
        return None
    definition = cast(TableDef | QueryDef, definition)
    kinds: list[ProjectIRLogicalOperatorKind] = [
        ProjectIRLogicalOperatorKind.RELATION_INPUT
    ]
    if definition.where_clause is not None:
        kinds.append(ProjectIRLogicalOperatorKind.ROW_FILTER)
    readiness = evidence.aggregate_grouped_clause_readiness
    if readiness is not None:
        if (
            readiness.status
            is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
        ):
            return None
        kinds.append(ProjectIRLogicalOperatorKind.GROUP_AGGREGATE)
    if definition.satisfying_clause is not None:
        satisfying = tuple(
            item
            for item in evidence.clause_dependencies
            if item.role is ProjectModuleFactOccurrenceRole.SATISFYING
        )
        if any(
            item.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            for item in satisfying
        ):
            return None
        kinds.append(ProjectIRLogicalOperatorKind.RESULT_FILTER)
    if evidence.window_outputs:
        if any(
            item.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            or item.project_fact is None
            for item in evidence.window_outputs
        ):
            return None
        kinds.append(ProjectIRLogicalOperatorKind.WINDOW_EVALUATION)
    if len(evidence.select_facts) != len(definition.select_items):
        return None
    kinds.append(ProjectIRLogicalOperatorKind.FINAL_PROJECTION)
    if definition.order_by_clause is not None:
        kinds.append(ProjectIRLogicalOperatorKind.RELATION_ORDERING)
    if definition.limit_clause is not None:
        expression = definition.limit_clause.expression
        if (
            type(expression) is not LiteralExpr
            or type(expression.value) is not int
            or not 0 <= expression.value <= MAX_RELATION_LIMIT
        ):
            return None
        kinds.append(ProjectIRLogicalOperatorKind.LIMIT)
    return tuple(kinds)


def _operator_row_outputs(
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> tuple[ProjectIRRelationRowOutput, ...]:
    return tuple(
        output
        for output in fragment.property_stage.outputs
        if type(output) is ProjectIRRelationRowOutput
        and output.occurrence.producer is operator.node
    )


def _row_shape_matches_operator(
    operator: ProjectIRLogicalOperatorOccurrence,
    output: ProjectIRRelationRowOutput,
) -> bool:
    definition = operator.evidence.owner.definition
    shape = output.row_shape
    if type(definition) is SourceDef:
        return type(shape) is ProjectIRRowShape and shape.evidence is operator.evidence
    expected = {
        ProjectIRLogicalOperatorKind.RELATION_INPUT: (
            ProjectIRStageRowCheckpointKind.INPUT
        ),
        ProjectIRLogicalOperatorKind.ROW_FILTER: (
            ProjectIRStageRowCheckpointKind.INPUT
        ),
        ProjectIRLogicalOperatorKind.GROUP_AGGREGATE: (
            ProjectIRStageRowCheckpointKind.BASE_RESULT
        ),
        ProjectIRLogicalOperatorKind.RESULT_FILTER: (
            ProjectIRStageRowCheckpointKind.BASE_RESULT
        ),
        ProjectIRLogicalOperatorKind.WINDOW_EVALUATION: (
            ProjectIRStageRowCheckpointKind.FINAL
        ),
    }.get(operator.kind)
    if expected is None:
        return type(shape) is ProjectIRRowShape and shape.evidence is operator.evidence
    expected_state = {
        ProjectIRStageRowCheckpointKind.INPUT: operator.evidence.input_state,
        ProjectIRStageRowCheckpointKind.BASE_RESULT: (
            operator.evidence.base_result_state
        ),
        ProjectIRStageRowCheckpointKind.FINAL: operator.evidence.state,
    }[expected]
    return (
        type(shape) is ProjectIRStageRowShape
        and shape.checkpoint.kind is expected
        and shape.checkpoint.evidence is operator.evidence
        and shape.checkpoint.state is expected_state
    )


def _verify_operator_legality(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    for fragment in plan.concrete_fragments:
        operators = fragment.logical_stage.operators
        expected = _independent_operator_kinds(fragment.semantic_facts)
        valid = (
            expected is not None
            and len(operators) == len(fragment.structural_stage.nodes)
            and all(
                operator.node is node
                and operator.evidence is fragment.semantic_facts
                and type(operator.kind) is ProjectIRLogicalOperatorKind
                for operator, node in zip(
                    operators,
                    fragment.structural_stage.nodes,
                    strict=False,
                )
            )
            and tuple(operator.kind for operator in operators) == expected
            and bool(operators)
            and fragment.root is operators[-1].node
        )
        if not valid:
            _record(
                issues,
                ProjectIRVerificationIssueKind.OPERATOR_LEGALITY,
                fragment,
            )
        for operator in operators:
            rows = _operator_row_outputs(fragment, operator)
            if len(rows) != 1 or not _row_shape_matches_operator(operator, rows[0]):
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.OPERATOR_LEGALITY,
                    operator,
                )


def _verify_operator_flow(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    flow_uses = tuple(
        use
        for use in plan.structural_stage.uses
        if type(use) is ProjectIROperatorFlowUseOccurrence
    )
    retained: list[ProjectIROperatorFlowUseOccurrence] = []
    for fragment in plan.concrete_fragments:
        pipeline = fragment.logical_stage.operators
        rows = tuple(
            outputs[0] if len(outputs) == 1 else None
            for outputs in (
                _operator_row_outputs(fragment, operator) for operator in pipeline
            )
        )
        if not pipeline:
            continue
        first = tuple(use for use in flow_uses if use.slot.consumer is pipeline[0].node)
        if first:
            _record(
                issues,
                ProjectIRVerificationIssueKind.OPERATOR_FLOW,
                pipeline[0],
            )
        for previous, current, output in zip(
            pipeline,
            pipeline[1:],
            rows,
            strict=False,
        ):
            incoming = tuple(
                use for use in flow_uses if use.slot.consumer is current.node
            )
            if (
                output is None
                or len(incoming) != 1
                or incoming[0].output is not output.occurrence
                or incoming[0].output.producer is not previous.node
            ):
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.OPERATOR_FLOW,
                    current,
                )
            else:
                retained.append(incoming[0])
    if len(retained) != len(flow_uses) or any(
        not any(use is expected for expected in retained) for use in flow_uses
    ):
        _record(issues, ProjectIRVerificationIssueKind.OPERATOR_FLOW)


def _relation_input_operator(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> ProjectIRLogicalOperatorOccurrence | None:
    matches = tuple(
        operator
        for operator in fragment.logical_stage.operators
        if operator.kind is ProjectIRLogicalOperatorKind.RELATION_INPUT
    )
    return matches[0] if len(matches) == 1 else None


def _relation_input_row(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> ProjectIRRelationRowOutput | None:
    operator = _relation_input_operator(fragment)
    if operator is None:
        return None
    matches = _operator_row_outputs(fragment, operator)
    return matches[0] if len(matches) == 1 else None


def _root_shape_properties(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> tuple[ProjectIRProvidedOutputShape, ...]:
    return tuple(
        property_
        for property_ in fragment.property_stage.provided
        if type(property_) is ProjectIRProvidedOutputShape
        and property_.output is fragment.root_relation_output
    )


def _verify_cross_relation_endpoints(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    semantic_uses = tuple(
        use for use in plan.structural_stage.uses if type(use) is ProjectIRUseOccurrence
    )
    if not _same_objects(
        cast(tuple[object, ...], semantic_uses),
        tuple(edge.use for edge in plan.cross_relation_edges),
    ):
        _record(issues, ProjectIRVerificationIssueKind.CROSS_RELATION_ENDPOINT)
    for edge in plan.cross_relation_edges:
        input_operator = _relation_input_operator(edge.consumer)
        valid = (
            type(edge) is ProjectIRCrossRelationEdge
            and any(edge.producer is fragment for fragment in plan.concrete_fragments)
            and any(edge.consumer is fragment for fragment in plan.concrete_fragments)
            and input_operator is not None
            and edge.authority.resolution is edge.consumer.semantic_facts.resolution
            and edge.authority.target == edge.producer.subject.anchor.identity
            and edge.authority.reference.owner == edge.consumer.subject.anchor.identity
            and edge.input_slot.consumer is input_operator.node
            and edge.input_slot.input_ordinal == 0
            and edge.use.output is edge.producer.root_relation_output.occurrence
            and edge.use.slot is edge.input_slot
            and edge.use.role is ProjectModuleFactOccurrenceRole.RELATION_INPUT
            and edge.use.source_order == 0
            and edge.use.anchor is edge.authority
            and any(
                edge.input_slot is slot for slot in plan.structural_stage.input_slots
            )
            and any(edge.use is use for use in plan.structural_stage.uses)
        )
        if not valid:
            _record(
                issues,
                ProjectIRVerificationIssueKind.CROSS_RELATION_ENDPOINT,
                edge,
            )


def _verify_row_compatibility(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    for edge in plan.cross_relation_edges:
        roots = _root_shape_properties(edge.producer)
        input_row = _relation_input_row(edge.consumer)
        input_shape = None if input_row is None else input_row.row_shape
        compatible = (
            len(roots) == 1
            and edge.provided_row_shape is roots[0]
            and type(edge.required_row_shape) is ProjectIRRequiredRowShape
            and edge.required_row_shape.input_slot is edge.input_slot
            and edge.required_row_shape.authority is edge.authority
            and edge.required_row_shape.row_shape
            is edge.producer.root_relation_output.row_shape
            and type(edge.compatibility) is ProjectIRRowShapeCompatibility
            and edge.compatibility.provided is edge.provided_row_shape
            and edge.compatibility.required is edge.required_row_shape
            and edge.compatibility.status
            is ProjectIRRowShapeCompatibilityStatus.SATISFIED
            and type(input_shape) is ProjectIRStageRowShape
            and input_shape.checkpoint.kind is ProjectIRStageRowCheckpointKind.INPUT
            and input_shape.checkpoint.state is edge.producer.semantic_facts.state
            and edge.consumer.semantic_facts.input_state
            is edge.producer.semantic_facts.state
        )
        if not compatible:
            _record(
                issues,
                ProjectIRVerificationIssueKind.ROW_COMPATIBILITY,
                edge,
            )


_PROVIDED_TYPES = (
    ProjectIRProvidedOutputShape,
    ProjectIRProvidedBagMultiplicity,
    ProjectIRProvidedClosedBindings,
    ProjectIRProvidedRelationOrdering,
    ProjectIRProvidedLocalGrainEvidence,
    ProjectIRProvidedCardinalityUpperBound,
    ProjectIRProvidedEvaluationPolicy,
    ProjectIRUnavailableProvidedProperty,
)


def _preserved_slots(
    kind: ProjectIRLogicalOperatorKind,
) -> tuple[ProjectIRProvidedPropertySlot, ...]:
    shape = ProjectIRProvidedPropertySlot.OUTPUT_SHAPE
    cardinality = ProjectIRProvidedPropertySlot.CARDINALITY_BOUNDS
    bag = ProjectIRProvidedPropertySlot.MULTIPLICITY
    ordering = ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING
    grain = ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE
    closed = ProjectIRProvidedPropertySlot.FREE_BINDINGS
    if kind is ProjectIRLogicalOperatorKind.ROW_FILTER:
        return (shape, cardinality, bag, ordering, closed)
    if kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
        return (closed,)
    if kind is ProjectIRLogicalOperatorKind.RESULT_FILTER:
        return (shape, cardinality, bag, ordering, grain, closed)
    if kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION:
        return (cardinality, bag, grain, closed)
    if kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
        return (cardinality, bag, closed)
    if kind is ProjectIRLogicalOperatorKind.RELATION_ORDERING:
        return (shape, cardinality, bag, closed)
    if kind is ProjectIRLogicalOperatorKind.LIMIT:
        return (shape, cardinality, bag, ordering, grain, closed)
    return ()


def _established_slots(
    kind: ProjectIRLogicalOperatorKind,
) -> tuple[ProjectIRProvidedPropertySlot, ...]:
    shape = ProjectIRProvidedPropertySlot.OUTPUT_SHAPE
    cardinality = ProjectIRProvidedPropertySlot.CARDINALITY_BOUNDS
    bag = ProjectIRProvidedPropertySlot.MULTIPLICITY
    ordering = ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING
    grain = ProjectIRProvidedPropertySlot.LOCAL_GRAIN_EVIDENCE
    closed = ProjectIRProvidedPropertySlot.FREE_BINDINGS
    policy = ProjectIRProvidedPropertySlot.POLICY_EVALUATION
    if kind is ProjectIRLogicalOperatorKind.RELATION_INPUT:
        return (shape, bag, closed)
    if kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
        return (shape, bag, grain)
    if kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION:
        return (shape, policy)
    if kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
        return (shape,)
    if kind is ProjectIRLogicalOperatorKind.RELATION_ORDERING:
        return (ordering,)
    if kind is ProjectIRLogicalOperatorKind.LIMIT:
        return (cardinality,)
    return ()


def _identity_items_match(
    actual: tuple[object, ...], expected: tuple[object, ...]
) -> bool:
    return _same_objects(actual, expected)


def _row_shape_payload_valid(shape: object) -> bool:
    if type(shape) is ProjectIRRowShape:
        schema = shape.evidence.state.schema
        if (
            shape.relation.identity != _semantic_identity(shape.evidence)
            or shape.evidence.state.status
            is not ProjectRelationRowSchemaStatus.CONCRETE
            or schema is None
            or len(shape.fields) != len(schema.fields)
        ):
            return False
        return all(
            type(field) is ProjectIRRowField
            and field.anchor.identity.owner == shape.relation.identity
            and field.anchor.identity.field_position == index
            and field.anchor.identity.name == expected.name
            and field.evidence is expected
            for index, (field, expected) in enumerate(
                zip(shape.fields, schema.fields.values(), strict=True)
            )
        )
    if type(shape) is not ProjectIRStageRowShape:
        return False
    checkpoint = shape.checkpoint
    if (
        type(checkpoint) is not ProjectIRStageRowCheckpoint
        or type(checkpoint.kind) is not ProjectIRStageRowCheckpointKind
    ):
        return False
    expected_state = {
        ProjectIRStageRowCheckpointKind.INPUT: checkpoint.evidence.input_state,
        ProjectIRStageRowCheckpointKind.BASE_RESULT: (
            checkpoint.evidence.base_result_state
        ),
        ProjectIRStageRowCheckpointKind.FINAL: checkpoint.evidence.state,
    }[checkpoint.kind]
    schema = checkpoint.state.schema
    if (
        checkpoint.relation.identity != _semantic_identity(checkpoint.evidence)
        or checkpoint.state is not expected_state
        or checkpoint.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        or schema is None
        or len(shape.fields) != len(schema.fields)
    ):
        return False
    return all(
        type(field) is ProjectIRStageRowField
        and field.checkpoint is checkpoint
        and field.field_position == index
        and field.evidence is expected
        for index, (field, expected) in enumerate(
            zip(shape.fields, schema.fields.values(), strict=True)
        )
    )


def _current_output_payload_valid(output: ProjectIRCurrentOutput) -> bool:
    occurrence = output.occurrence
    if type(output) is ProjectIRRelationRowOutput:
        return (
            type(occurrence.anchor) is ProjectIRRelationAnchor
            and occurrence.anchor == output.row_shape.relation
            and occurrence.producer.anchor == output.row_shape.relation
            and _row_shape_payload_valid(output.row_shape)
        )
    if type(output) is ProjectIRScalarFieldOutput:
        return (
            type(occurrence.anchor) is ProjectIRFieldAnchor
            and occurrence.anchor == output.field.anchor
            and occurrence.producer.anchor == output.row_shape.relation
            and any(field is output.field for field in output.row_shape.fields)
            and _row_shape_payload_valid(output.row_shape)
        )
    if type(output) is ProjectIRStageScalarFieldOutput:
        anchor = occurrence.anchor
        return (
            type(anchor) is ProjectIRStageFieldAnchor
            and anchor.producer is occurrence.producer
            and anchor.field_position == output.field.field_position
            and output.field.checkpoint is output.row_shape.checkpoint
            and occurrence.producer.anchor == output.row_shape.relation
            and _row_shape_payload_valid(output.row_shape)
        )
    return False


def _provided_property_payload_valid(property_: ProjectIRProvidedProperty) -> bool:
    output = property_.output
    if type(property_) is ProjectIRProvidedOutputShape:
        return True
    if type(property_) is ProjectIRProvidedBagMultiplicity:
        return type(output) is ProjectIRRelationRowOutput
    if type(property_) is ProjectIRProvidedClosedBindings:
        return type(output) is ProjectIRRelationRowOutput and not property_.bindings
    if type(property_) is ProjectIRProvidedRelationOrdering:
        definition = property_.evidence.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            return False
        derived = cast(TableDef | QueryDef, definition)
        if (
            type(output) is not ProjectIRRelationRowOutput
            or property_.evidence is not output.row_shape.evidence
            or derived.order_by_clause is None
            or not _identity_items_match(
                cast(tuple[object, ...], property_.items),
                cast(tuple[object, ...], derived.order_by_clause.items),
            )
        ):
            return False
        if derived.group_by_clause is None:
            return True
        facts = tuple(
            item
            for item in property_.evidence.clause_dependencies
            if item.role is ProjectModuleFactOccurrenceRole.GROUPED_ORDER
        )
        return len(facts) == len(property_.items) and all(
            fact.status is ProjectModuleCandidateBucketStatus.CONCRETE
            and fact.source_ordinal == index
            and fact.source_occurrence is item
            for index, (fact, item) in enumerate(
                zip(facts, property_.items, strict=True)
            )
        )
    if type(property_) is ProjectIRProvidedLocalGrainEvidence:
        return (
            type(output) is ProjectIRRelationRowOutput
            and property_.evidence is output.row_shape.evidence
            and bool(property_.evidence.group_key_occurrences)
            and _identity_items_match(
                cast(tuple[object, ...], property_.occurrences),
                cast(
                    tuple[object, ...],
                    property_.evidence.group_key_occurrences,
                ),
            )
        )
    if type(property_) is ProjectIRProvidedCardinalityUpperBound:
        definition = property_.evidence.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            return False
        derived = cast(TableDef | QueryDef, definition)
        expression = (
            None if derived.limit_clause is None else derived.limit_clause.expression
        )
        return (
            type(output) is ProjectIRRelationRowOutput
            and property_.evidence is output.row_shape.evidence
            and type(expression) is LiteralExpr
            and type(expression.value) is int
            and 0 <= expression.value <= MAX_RELATION_LIMIT
            and property_.upper_bound == expression.value
        )
    if type(property_) is ProjectIRProvidedEvaluationPolicy:
        evidence = property_.evidence
        project_fact = evidence.project_fact
        if type(output) is ProjectIRScalarFieldOutput:
            position = output.field.anchor.identity.field_position
            name = output.field.anchor.identity.name
        elif type(output) is ProjectIRStageScalarFieldOutput:
            position = output.field.field_position
            name = output.field.evidence.name
        else:
            return False
        if (
            evidence.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            or project_fact is None
            or not any(
                evidence is item for item in output.row_shape.evidence.window_outputs
            )
        ):
            return False
        return (
            evidence.selected_output_ordinal == position
            and evidence.output_name == name
            and property_.policy
            == project_fact.analysis.validated_specification.function_policy
        )
    return (
        type(property_) is ProjectIRUnavailableProvidedProperty
        and type(property_.property_slot) is ProjectIRProvidedPropertySlot
        and property_.property_slot is not ProjectIRProvidedPropertySlot.OUTPUT_SHAPE
        and type(property_.availability) is ProjectIRPropertyAvailability
    )


def _property_semantics_match(
    input_property: ProjectIRProvidedProperty,
    output_property: ProjectIRProvidedProperty,
) -> bool:
    input_output = input_property.output
    output_output = output_property.output
    if (
        type(input_output) is not type(output_output)
        or input_output.row_shape.evidence is not output_output.row_shape.evidence
    ):
        return False
    if type(input_property) is ProjectIRProvidedOutputShape:
        return (
            type(output_property) is ProjectIRProvidedOutputShape
            and input_output.row_shape == output_output.row_shape
        )
    if type(input_property) is ProjectIRProvidedBagMultiplicity:
        return type(output_property) is ProjectIRProvidedBagMultiplicity
    if type(input_property) is ProjectIRProvidedClosedBindings:
        return type(output_property) is ProjectIRProvidedClosedBindings
    if type(input_property) is ProjectIRProvidedRelationOrdering:
        return type(output_property) is ProjectIRProvidedRelationOrdering and (
            _identity_items_match(
                cast(tuple[object, ...], input_property.items),
                cast(tuple[object, ...], output_property.items),
            )
        )
    if type(input_property) is ProjectIRProvidedLocalGrainEvidence:
        return type(output_property) is ProjectIRProvidedLocalGrainEvidence and (
            _identity_items_match(
                cast(tuple[object, ...], input_property.occurrences),
                cast(tuple[object, ...], output_property.occurrences),
            )
        )
    if type(input_property) is ProjectIRProvidedCardinalityUpperBound:
        return (
            type(output_property) is ProjectIRProvidedCardinalityUpperBound
            and output_property.upper_bound <= input_property.upper_bound
        )
    if type(input_property) is ProjectIRProvidedEvaluationPolicy:
        return (
            type(output_property) is ProjectIRProvidedEvaluationPolicy
            and input_property.policy == output_property.policy
        )
    return (
        type(input_property) is ProjectIRUnavailableProvidedProperty
        and type(output_property) is ProjectIRUnavailableProvidedProperty
        and input_property.availability is output_property.availability
    )


def _incoming_flow_row(
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> ProjectIRRelationRowOutput | None:
    incoming = tuple(
        use
        for use in fragment.structural_stage.uses
        if type(use) is ProjectIROperatorFlowUseOccurrence
        and use.slot.consumer is operator.node
    )
    if len(incoming) != 1:
        return None
    matches = tuple(
        output
        for output in fragment.property_stage.outputs
        if type(output) is ProjectIRRelationRowOutput
        and output.occurrence is incoming[0].output
    )
    return matches[0] if len(matches) == 1 else None


def _verify_property_attachments(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    slot_order = tuple(ProjectIRProvidedPropertySlot)
    for fragment in plan.concrete_fragments:
        stage = fragment.property_stage
        valid = (
            type(stage) is ProjectIRPropertyStage
            and stage.structural is fragment.structural_stage
            and len(stage.outputs) == len(stage.structural.outputs)
            and all(_current_output_payload_valid(output) for output in stage.outputs)
            and all(
                output.occurrence is occurrence
                for output, occurrence in zip(
                    stage.outputs,
                    stage.structural.outputs,
                    strict=False,
                )
            )
            and not stage.required
            and stage.estimates.scope is stage.structural.scope
            and not stage.estimates.statistics
        )
        if not valid:
            _record(
                issues,
                ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
                fragment,
            )
        keys: list[tuple[int, int]] = []
        for property_ in stage.provided:
            if type(property_) not in _PROVIDED_TYPES or not any(
                property_.output is output for output in stage.outputs
            ):
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
                    property_.output if hasattr(property_, "output") else fragment,
                )
                continue
            if not _provided_property_payload_valid(property_):
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
                    property_.output.occurrence,
                )
            keys.append(
                (
                    property_.output.occurrence.ref.position,
                    slot_order.index(property_.property_slot),
                )
            )
            if type(property_) is ProjectIRProvidedLocalGrainEvidence and (
                not property_.output.row_shape.evidence.group_key_occurrences
                or not _identity_items_match(
                    cast(tuple[object, ...], property_.occurrences),
                    cast(
                        tuple[object, ...],
                        property_.output.row_shape.evidence.group_key_occurrences,
                    ),
                )
            ):
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
                    property_.output.occurrence,
                )
        if len(keys) != len(set(keys)) or keys != sorted(keys):
            _record(
                issues,
                ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
                fragment,
            )
        for output in stage.outputs:
            shapes = tuple(
                property_
                for property_ in stage.provided
                if type(property_) is ProjectIRProvidedOutputShape
                and property_.output is output
            )
            if len(shapes) != 1:
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
                    output.occurrence,
                )
            if type(output) is ProjectIRRelationRowOutput:
                bags = tuple(
                    property_
                    for property_ in stage.provided
                    if type(property_) is ProjectIRProvidedBagMultiplicity
                    and property_.output is output
                )
                closed = tuple(
                    property_
                    for property_ in stage.provided
                    if type(property_) is ProjectIRProvidedClosedBindings
                    and property_.output is output
                )
                if len(bags) != 1 or len(closed) != 1 or closed[0].bindings:
                    _record(
                        issues,
                        ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
                        output.occurrence,
                    )
            if type(output) is ProjectIRStageScalarFieldOutput:
                policies = tuple(
                    property_
                    for property_ in stage.provided
                    if type(property_) is ProjectIRProvidedEvaluationPolicy
                    and property_.output is output
                )
                if len(policies) != 1:
                    _record(
                        issues,
                        ProjectIRVerificationIssueKind.PROPERTY_ATTACHMENT,
                        output.occurrence,
                    )


def _verify_property_transfers(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    slot_order = tuple(ProjectIRProvidedPropertySlot)
    for fragment in plan.concrete_fragments:
        provided = fragment.property_stage.provided
        transfers = fragment.logical_stage.transfers
        keys: list[tuple[int, int, int]] = []
        for transfer in transfers:
            if type(transfer) not in {
                ProjectIRPreservedPropertyTransfer,
                ProjectIREstablishedPropertyTransfer,
                ProjectIRUnavailablePropertyTransfer,
            }:
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.PROPERTY_TRANSFER,
                    fragment,
                )
                continue
            output_property = transfer.output_property
            valid = (
                any(
                    transfer.operator is item
                    for item in fragment.logical_stage.operators
                )
                and any(output_property is item for item in provided)
                and output_property.output.occurrence.producer is transfer.operator.node
            )
            if type(transfer) is ProjectIRPreservedPropertyTransfer:
                input_row = _incoming_flow_row(fragment, transfer.operator)
                valid = valid and (
                    output_property.property_slot
                    in _preserved_slots(transfer.operator.kind)
                    and any(transfer.input_property is item for item in provided)
                    and input_row is not None
                    and transfer.input_property.output is input_row
                    and transfer.input_property.property_slot
                    is output_property.property_slot
                    and _property_semantics_match(
                        transfer.input_property,
                        output_property,
                    )
                )
            elif type(transfer) is ProjectIREstablishedPropertyTransfer:
                valid = valid and (
                    type(output_property) is not ProjectIRUnavailableProvidedProperty
                    and output_property.property_slot
                    in _established_slots(transfer.operator.kind)
                )
            else:
                valid = (
                    valid
                    and type(output_property) is ProjectIRUnavailableProvidedProperty
                )
            if not valid:
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.PROPERTY_TRANSFER,
                    output_property.output.occurrence,
                )
            keys.append(
                (
                    transfer.operator.node.ref.position,
                    output_property.output.occurrence.ref.position,
                    slot_order.index(output_property.property_slot),
                )
            )
        if (
            len(keys) != len(set(keys))
            or keys != sorted(keys)
            or any(
                sum(transfer.output_property is property_ for transfer in transfers)
                != 1
                for property_ in provided
            )
        ):
            _record(
                issues,
                ProjectIRVerificationIssueKind.PROPERTY_TRANSFER,
                fragment,
            )


def _verify_effect_attachments(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    for fragment in plan.concrete_fragments:
        effects = fragment.property_stage.effects
        outputs = fragment.property_stage.outputs
        if len(effects) != len(outputs):
            _record(
                issues,
                ProjectIRVerificationIssueKind.EFFECT_ATTACHMENT,
                fragment,
            )
        for output in outputs:
            matches = tuple(effect for effect in effects if effect.output is output)
            if len(matches) != 1:
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.EFFECT_ATTACHMENT,
                    output.occurrence,
                )
                continue
            effect = matches[0]
            if (
                type(effect) is not ProjectIREffectEvidence
                or effect.determinism is not ProjectIRDeterminismEvidence.UNKNOWN
                or effect.error_behavior is not ProjectIRErrorBehaviorEvidence.UNKNOWN
                or effect.side_effects is not ProjectIRSideEffectEvidence.UNKNOWN
                or effect.evaluation_count
                is not ProjectIREvaluationCountEvidence.UNKNOWN
            ):
                _record(
                    issues,
                    ProjectIRVerificationIssueKind.EFFECT_ATTACHMENT,
                    output.occurrence,
                )


def _verify_non_concrete_terminals(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    for fragment in plan.non_concrete_fragments:
        structural = fragment.structural_stage
        property_stage = fragment.property_stage
        logical = fragment.logical_stage
        valid = (
            type(fragment.subject) is ProjectIRNonConcreteRelationSubject
            and structural.subjects == (fragment.subject,)
            and fragment.ending_allocation is fragment.starting_allocation
            and not structural.nodes
            and not structural.outputs
            and not structural.input_slots
            and not structural.uses
            and not property_stage.outputs
            and not property_stage.provided
            and not property_stage.required
            and not property_stage.effects
            and not logical.operators
            and not logical.transfers
            and not logical.compatibilities
            and fragment.root is None
            and fragment.root_relation_output is None
            and not fragment.final_scalar_outputs
        )
        if not valid:
            _record(issues, ProjectIRVerificationIssueKind.NON_CONCRETE_TERMINAL)


def _one_incoming_flow(
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> ProjectIROperatorFlowUseOccurrence | None:
    matches = tuple(
        use
        for use in fragment.structural_stage.uses
        if type(use) is ProjectIROperatorFlowUseOccurrence
        and use.slot.consumer is operator.node
    )
    return matches[0] if len(matches) == 1 else None


def _row_for_occurrence(
    fragment: ProjectIRConcreteSingleRelationFragment,
    occurrence: ProjectIROutputValueOccurrence,
) -> ProjectIRRelationRowOutput | None:
    matches = tuple(
        output
        for output in fragment.property_stage.outputs
        if type(output) is ProjectIRRelationRowOutput
        and output.occurrence is occurrence
    )
    return matches[0] if len(matches) == 1 else None


def _result_row(
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> ProjectIRRelationRowOutput | None:
    matches = _operator_row_outputs(fragment, operator)
    return matches[0] if len(matches) == 1 else None


def _closed_property(
    fragment: ProjectIRConcreteSingleRelationFragment,
    output: ProjectIRRelationRowOutput,
) -> ProjectIRProvidedClosedBindings | None:
    matches = tuple(
        property_
        for property_ in fragment.property_stage.provided
        if type(property_) is ProjectIRProvidedClosedBindings
        and property_.output is output
    )
    return matches[0] if len(matches) == 1 else None


def _effect_for_output(
    fragment: ProjectIRConcreteSingleRelationFragment,
    output: ProjectIRCurrentOutput,
) -> ProjectIREffectEvidence | None:
    matches = tuple(
        effect for effect in fragment.property_stage.effects if effect.output is output
    )
    return matches[0] if len(matches) == 1 else None


def _verify_aggregate_context(
    context: ProjectIRAggregateEvaluationContext,
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> bool:
    flow = _one_incoming_flow(fragment, operator)
    if flow is None:
        return False
    input_row = _row_for_occurrence(fragment, flow.output)
    result_row = _result_row(fragment, operator)
    if input_row is None or result_row is None:
        return False
    result_shape = result_row.row_shape
    return (
        type(context) is ProjectIRAggregateEvaluationContext
        and context.fragment is fragment
        and context.operator is operator
        and context.incoming_flow is flow
        and context.input_row_output is input_row
        and context.result_row_output is result_row
        and context.semantic_facts is fragment.semantic_facts
        and context.readiness
        is fragment.semantic_facts.aggregate_grouped_clause_readiness
        and context.group_keys is fragment.semantic_facts.group_key_occurrences
        and context.aggregate_results is fragment.semantic_facts.aggregate_result_facts
        and context.let_scope is fragment.semantic_facts.let_scope_facts
        and type(result_shape) is ProjectIRStageRowShape
        and result_shape.checkpoint.kind is ProjectIRStageRowCheckpointKind.BASE_RESULT
        and result_shape.checkpoint.state is fragment.semantic_facts.base_result_state
        and context.input_closed_bindings is _closed_property(fragment, input_row)
        and context.result_closed_bindings is _closed_property(fragment, result_row)
        and not context.input_closed_bindings.bindings
        and not context.result_closed_bindings.bindings
        and context.input_effect is _effect_for_output(fragment, input_row)
        and context.result_effect is _effect_for_output(fragment, result_row)
    )


def _verify_window_context(
    context: ProjectIRWindowOperatorEvaluationContext,
    fragment: ProjectIRConcreteSingleRelationFragment,
    operator: ProjectIRLogicalOperatorOccurrence,
) -> bool:
    flow = _one_incoming_flow(fragment, operator)
    if flow is None:
        return False
    input_row = _row_for_occurrence(fragment, flow.output)
    result_row = _result_row(fragment, operator)
    if input_row is None or result_row is None:
        return False
    base = context.semantic_base_checkpoint
    result_shape = result_row.row_shape
    return (
        type(context) is ProjectIRWindowOperatorEvaluationContext
        and context.fragment is fragment
        and context.operator is operator
        and context.incoming_flow is flow
        and context.stream_input_row_output is input_row
        and context.result_row_output is result_row
        and context.semantic_facts is fragment.semantic_facts
        and type(base) is ProjectIRStageRowCheckpoint
        and base.evidence is fragment.semantic_facts
        and base.kind is ProjectIRStageRowCheckpointKind.BASE_RESULT
        and base.state is fragment.semantic_facts.base_result_state
        and context.let_scope is fragment.semantic_facts.let_scope_facts
        and context.named_window_namespace
        is fragment.semantic_facts.named_window_namespace
        and type(input_row.row_shape) is ProjectIRStageRowShape
        and type(result_shape) is ProjectIRStageRowShape
        and result_shape.checkpoint.kind is ProjectIRStageRowCheckpointKind.FINAL
        and context.stream_closed_bindings is _closed_property(fragment, input_row)
        and context.result_closed_bindings is _closed_property(fragment, result_row)
        and not context.stream_closed_bindings.bindings
        and not context.result_closed_bindings.bindings
        and context.stream_effect is _effect_for_output(fragment, input_row)
        and context.result_effect is _effect_for_output(fragment, result_row)
    )


def _stage_scalar_for_fact(
    context: ProjectIRWindowOperatorEvaluationContext,
    output_ordinal: int,
) -> ProjectIRStageScalarFieldOutput | None:
    matches = tuple(
        output
        for output in context.fragment.property_stage.outputs
        if type(output) is ProjectIRStageScalarFieldOutput
        and output.occurrence.producer is context.operator.node
        and output.field.field_position == output_ordinal
    )
    return matches[0] if len(matches) == 1 else None


def _policy_for_scalar(
    context: ProjectIRWindowOperatorEvaluationContext,
    scalar: ProjectIRStageScalarFieldOutput,
    fact: object,
) -> ProjectIRProvidedEvaluationPolicy | None:
    matches = tuple(
        property_
        for property_ in context.fragment.property_stage.provided
        if type(property_) is ProjectIRProvidedEvaluationPolicy
        and property_.output is scalar
        and property_.evidence is fact
    )
    return matches[0] if len(matches) == 1 else None


def _verify_evaluation_contexts(
    stage: ProjectIREvaluationContextStage,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    plan = stage.project_plan
    aggregate_expected = tuple(
        (fragment, operator)
        for fragment in plan.concrete_fragments
        for operator in fragment.logical_stage.operators
        if operator.kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
    )
    if len(stage.aggregate_contexts) != len(aggregate_expected):
        _record(issues, ProjectIRVerificationIssueKind.EVALUATION_CONTEXT)
    for index, expected in enumerate(aggregate_expected):
        if index >= len(stage.aggregate_contexts) or not _verify_aggregate_context(
            stage.aggregate_contexts[index],
            *expected,
        ):
            _record(
                issues,
                ProjectIRVerificationIssueKind.EVALUATION_CONTEXT,
                expected[1],
            )

    window_expected = tuple(
        (fragment, operator)
        for fragment in plan.concrete_fragments
        for operator in fragment.logical_stage.operators
        if operator.kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION
    )
    if len(stage.window_operator_contexts) != len(window_expected):
        _record(issues, ProjectIRVerificationIssueKind.EVALUATION_CONTEXT)
    for index, expected in enumerate(window_expected):
        if index >= len(stage.window_operator_contexts) or not _verify_window_context(
            stage.window_operator_contexts[index],
            *expected,
        ):
            _record(
                issues,
                ProjectIRVerificationIssueKind.EVALUATION_CONTEXT,
                expected[1],
            )

    result_expected = tuple(
        (fragment, operator, fact)
        for fragment, operator in window_expected
        for fact in fragment.semantic_facts.window_outputs
    )
    if len(stage.window_result_contexts) != len(result_expected):
        _record(issues, ProjectIRVerificationIssueKind.EVALUATION_CONTEXT)
    for index, (fragment, operator, fact) in enumerate(result_expected):
        if index >= len(stage.window_result_contexts):
            _record(
                issues,
                ProjectIRVerificationIssueKind.EVALUATION_CONTEXT,
                operator,
            )
            continue
        result = stage.window_result_contexts[index]
        operator_context = result.operator_context
        scalar = _stage_scalar_for_fact(operator_context, fact.selected_output_ordinal)
        policy = (
            None
            if scalar is None
            else _policy_for_scalar(operator_context, scalar, fact)
        )
        final_matches = tuple(
            output
            for output in fragment.final_scalar_outputs
            if output.field.anchor.identity.field_position
            == fact.selected_output_ordinal
        )
        valid = (
            type(result) is ProjectIRWindowResultEvaluationContext
            and any(
                operator_context is context
                for context in stage.window_operator_contexts
            )
            and operator_context.fragment is fragment
            and operator_context.operator is operator
            and result.window_fact is fact
            and result.project_fact is fact.project_fact
            and scalar is not None
            and result.stage_scalar_output is scalar
            and result.policy is policy
            and result.effect is _effect_for_output(fragment, scalar)
            and len(final_matches) == 1
            and final_matches[0].occurrence is not scalar.occurrence
        )
        if not valid:
            _record(
                issues,
                ProjectIRVerificationIssueKind.EVALUATION_CONTEXT,
                result,
            )


def _graph_successors(
    structural: ProjectIRStructuralStage,
) -> tuple[tuple[int, ...], ...] | None:
    nodes = cast(tuple[object, ...], structural.nodes)
    successors: list[list[int]] = [[] for _ in structural.nodes]
    for use in structural.uses:
        producer = _identity_indices(nodes, use.output.producer)
        consumer = _identity_indices(nodes, use.slot.consumer)
        if len(producer) != 1 or len(consumer) != 1:
            return None
        successors[producer[0]].append(consumer[0])
    return tuple(tuple(items) for items in successors)


def _fresh_topological_order(
    structural: ProjectIRStructuralStage,
) -> tuple[ProjectIRPlanNodeOccurrence, ...] | None:
    successors = _graph_successors(structural)
    if successors is None:
        return None
    indegree = [0] * len(structural.nodes)
    for items in successors:
        for consumer in items:
            indegree[consumer] += 1
    ready: list[tuple[int, int]] = []
    for index, (node, degree) in enumerate(
        zip(structural.nodes, indegree, strict=True)
    ):
        if degree == 0:
            heappush(ready, (node.ref.position, index))
    order: list[ProjectIRPlanNodeOccurrence] = []
    while ready:
        _, index = heappop(ready)
        order.append(structural.nodes[index])
        for consumer in successors[index]:
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                node = structural.nodes[consumer]
                heappush(ready, (node.ref.position, consumer))
    return tuple(order) if len(order) == len(structural.nodes) else None


def _verify_actual_use_acyclicity(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    if _graph_successors(plan.structural_stage) is not None and (
        _fresh_topological_order(plan.structural_stage) is None
    ):
        _record(issues, ProjectIRVerificationIssueKind.ACTUAL_USE_CYCLE)


def _verify_provenance_reachability(
    plan: ProjectIRProjectPlan,
    issues: list[ProjectIRVerificationIssue],
) -> None:
    for edge in plan.cross_relation_edges:
        dependency = edge.authority.dependency
        origin = dependency.origin_path
        valid = (
            type(dependency.kind) is ProjectModuleDependencyKind
            and dependency.kind is ProjectModuleDependencyKind.RELATION_REFERENCE
            and any(
                dependency is retained for retained in plan.attribution.dependencies
            )
            and origin is not None
            and any(origin is retained for retained in plan.attribution.origins)
            and dependency.reference == edge.authority.reference
            and dependency.target_declaration == edge.producer.subject.anchor.identity
            and origin.target_occurrence == edge.producer.subject.anchor.identity
            and origin.owning_module_path
            == edge.consumer.subject.anchor.identity.identity.module_path
            and edge.authority.reference.role
            is ProjectModuleReferenceRole.RELATION_FROM
        )
        if not valid:
            _record(
                issues,
                ProjectIRVerificationIssueKind.PROVENANCE_REACHABILITY,
                edge,
            )


def verify_project_ir_stage(
    stage: ProjectIREvaluationContextStage,
) -> ProjectIRVerificationResult:
    """Independently verify one exact Slice 7 stage from fresh retained facts."""

    if type(stage) is not ProjectIREvaluationContextStage:
        raise TypeError("Project IR verification requires an exact Slice 7 stage.")
    issues: list[ProjectIRVerificationIssue] = []
    plan = stage.project_plan
    if (
        type(plan) is not ProjectIRProjectPlan
        or type(plan.structural_stage) is not ProjectIRStructuralStage
    ):
        _record(issues, ProjectIRVerificationIssueKind.FRAGMENT_COMPOSITION)
    else:
        _verify_scopes_and_coordinates(plan, issues)
        _verify_structural_endpoints(plan.structural_stage, issues)
        _verify_slot_attachments(plan.structural_stage, issues)
        _verify_fragment_composition(plan, issues)
        _verify_operator_legality(plan, issues)
        _verify_operator_flow(plan, issues)
        _verify_cross_relation_endpoints(plan, issues)
        _verify_row_compatibility(plan, issues)
        _verify_property_attachments(plan, issues)
        _verify_property_transfers(plan, issues)
        _verify_effect_attachments(plan, issues)
        _verify_non_concrete_terminals(plan, issues)
        _verify_evaluation_contexts(stage, issues)
        _verify_actual_use_acyclicity(plan, issues)
        _verify_provenance_reachability(plan, issues)
    issue_tuple = tuple(issues)
    return ProjectIRVerificationResult(
        stage=stage,
        status=(
            ProjectIRVerificationStatus.VERIFIED
            if not issue_tuple
            else ProjectIRVerificationStatus.INVALID
        ),
        issues=issue_tuple,
    )


class ProjectIRAnalysisKind(StrEnum):
    """Current detachable analyses, excluding verification itself."""

    REVERSE_USE_INDEX = "reverse_use_index"
    TOPOLOGICAL_ORDER = "topological_order"
    REACHABILITY = "reachability"
    SEMANTIC_EQUIVALENCE_CANDIDATES = "semantic_equivalence_candidates"


class ProjectIRChangeDomain(StrEnum):
    """Typed future transform-change declarations."""

    TOPOLOGY = "topology"
    OPERATOR_SEMANTICS = "operator_semantics"
    OUTPUT_SEMANTICS = "output_semantics"
    PROPERTIES = "properties"
    EFFECTS = "effects"
    EVALUATION_CONTEXT = "evaluation_context"
    PROVENANCE = "provenance"
    ESTIMATES = "estimates"


class ProjectIRVerificationRequirement(StrEnum):
    """Verification is never a preservable analysis."""

    RERUN_REQUIRED = "rerun_required"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRReverseUseEntry:
    """Every exact use of one output in structural use order."""

    output: ProjectIROutputValueOccurrence
    uses: tuple[ProjectIRUseOccurrence | ProjectIROperatorFlowUseOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIROutputValueOccurrence:
            raise TypeError("Reverse-use entry requires an exact output.")
        if type(self.uses) is not tuple or any(
            type(use)
            not in {ProjectIRUseOccurrence, ProjectIROperatorFlowUseOccurrence}
            or use.output is not self.output
            for use in self.uses
        ):
            raise ValueError("Reverse-use entry requires exact matching uses.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRReachabilityEntry:
    """Fresh transitive successors for one exact node."""

    source: ProjectIRPlanNodeOccurrence
    reachable: tuple[ProjectIRPlanNodeOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.source) is not ProjectIRPlanNodeOccurrence:
            raise TypeError("Reachability entry requires an exact source node.")
        if type(self.reachable) is not tuple or any(
            type(node) is not ProjectIRPlanNodeOccurrence for node in self.reachable
        ):
            raise TypeError("Reachability targets must be exact nodes.")
        if any(node is self.source for node in self.reachable):
            raise ValueError("Acyclic reachability cannot contain its source.")


class ProjectIRSemanticDimension(StrEnum):
    """Nontrivial semantic dimensions required by future rewrites."""

    SCHEMA_TYPES = "schema_types"
    VALUES = "values"
    BAG_MULTIPLICITY = "bag_multiplicity"
    NULL_EMPTY_BEHAVIOR = "null_empty_behavior"
    CARDINALITY_GUARANTEES = "cardinality_guarantees"
    ORDERING = "ordering"
    EFFECTS_ERROR_BEHAVIOR = "effects_error_behavior"
    EVALUATION_COUNT = "evaluation_count"
    POLICY_CONTEXT = "policy_context"
    REQUIRED_CAPABILITIES = "required_capabilities"
    PROVENANCE_TRACEABILITY = "provenance_traceability"


class ProjectIRSemanticDimensionStatus(StrEnum):
    """Evidence posture for one semantic-equivalence dimension."""

    EVIDENCED = "evidenced"
    INCOMPATIBLE = "incompatible"
    NOT_PROVEN = "not_proven"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRSemanticDimensionAssessment:
    """One explicit dimension-by-dimension evidence posture."""

    dimension: ProjectIRSemanticDimension
    status: ProjectIRSemanticDimensionStatus

    def __post_init__(self) -> None:
        if type(self.dimension) is not ProjectIRSemanticDimension:
            raise TypeError("Semantic assessment requires an exact dimension.")
        if type(self.status) is not ProjectIRSemanticDimensionStatus:
            raise TypeError("Semantic assessment requires an exact evidence status.")


class ProjectIRSemanticEquivalenceStatus(StrEnum):
    """Candidate analysis is distinct from a rewrite proof."""

    KNOWN_INCOMPATIBLE = "known_incompatible"
    CANDIDATE_NOT_DISPROVEN = "candidate_not_disproven"
    REWRITE_EQUIVALENCE_PROVEN = "rewrite_equivalence_proven"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRSemanticEquivalenceAssessment:
    """One canonical distinct-fragment pair and all required dimensions."""

    left: ProjectIRConcreteSingleRelationFragment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    right: ProjectIRConcreteSingleRelationFragment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    dimensions: tuple[ProjectIRSemanticDimensionAssessment, ...]
    status: ProjectIRSemanticEquivalenceStatus

    def __post_init__(self) -> None:
        if (
            type(self.left) is not ProjectIRConcreteSingleRelationFragment
            or type(self.right) is not ProjectIRConcreteSingleRelationFragment
            or self.left is self.right
        ):
            raise ValueError("Semantic assessment requires distinct fragments.")
        if type(self.dimensions) is not tuple or tuple(
            assessment.dimension for assessment in self.dimensions
        ) != tuple(ProjectIRSemanticDimension):
            raise ValueError("Semantic assessment requires every canonical dimension.")
        statuses = tuple(assessment.status for assessment in self.dimensions)
        expected = (
            ProjectIRSemanticEquivalenceStatus.KNOWN_INCOMPATIBLE
            if ProjectIRSemanticDimensionStatus.INCOMPATIBLE in statuses
            else (
                ProjectIRSemanticEquivalenceStatus.REWRITE_EQUIVALENCE_PROVEN
                if all(
                    status is ProjectIRSemanticDimensionStatus.EVIDENCED
                    for status in statuses
                )
                else ProjectIRSemanticEquivalenceStatus.CANDIDATE_NOT_DISPROVEN
            )
        )
        if type(self.status) is not ProjectIRSemanticEquivalenceStatus or (
            self.status is not expected
        ):
            raise ValueError("Semantic-equivalence status disagrees with evidence.")


class ProjectIRRewriteReadinessStatus(StrEnum):
    """Pure readiness result; no transform or witness is implemented."""

    ADMISSIBLE = "admissible"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRRewriteReadiness:
    """Readiness for one exact candidate pair without performing a rewrite."""

    assessment: ProjectIRSemanticEquivalenceAssessment
    status: ProjectIRRewriteReadinessStatus
    blockers: tuple[ProjectIRSemanticDimension, ...]

    def __post_init__(self) -> None:
        if type(self.assessment) is not ProjectIRSemanticEquivalenceAssessment:
            raise TypeError("Rewrite readiness requires an exact assessment.")
        if type(self.status) is not ProjectIRRewriteReadinessStatus:
            raise TypeError("Rewrite readiness requires an exact status.")
        expected_blockers = tuple(
            evidence.dimension
            for evidence in self.assessment.dimensions
            if evidence.status is not ProjectIRSemanticDimensionStatus.EVIDENCED
        )
        expected_status = (
            ProjectIRRewriteReadinessStatus.ADMISSIBLE
            if not expected_blockers
            and self.assessment.status
            is ProjectIRSemanticEquivalenceStatus.REWRITE_EQUIVALENCE_PROVEN
            else ProjectIRRewriteReadinessStatus.BLOCKED
        )
        if self.blockers != expected_blockers or self.status is not expected_status:
            raise ValueError("Rewrite readiness disagrees with semantic evidence.")


def _analysis_dependencies(
    kind: ProjectIRAnalysisKind,
) -> tuple[ProjectIRChangeDomain, ...]:
    if kind in {
        ProjectIRAnalysisKind.REVERSE_USE_INDEX,
        ProjectIRAnalysisKind.TOPOLOGICAL_ORDER,
        ProjectIRAnalysisKind.REACHABILITY,
    }:
        return (ProjectIRChangeDomain.TOPOLOGY,)
    return (
        ProjectIRChangeDomain.TOPOLOGY,
        ProjectIRChangeDomain.OPERATOR_SEMANTICS,
        ProjectIRChangeDomain.OUTPUT_SEMANTICS,
        ProjectIRChangeDomain.PROPERTIES,
        ProjectIRChangeDomain.EFFECTS,
        ProjectIRChangeDomain.EVALUATION_CONTEXT,
        ProjectIRChangeDomain.PROVENANCE,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRAnalysisInvalidation:
    """Explicit preservation/invalidation derived from typed change domains."""

    changed_domains: tuple[ProjectIRChangeDomain, ...]
    invalidated: tuple[ProjectIRAnalysisKind, ...]
    preserved: tuple[ProjectIRAnalysisKind, ...]
    verification: ProjectIRVerificationRequirement = field(
        init=False,
        default=ProjectIRVerificationRequirement.RERUN_REQUIRED,
    )

    def __post_init__(self) -> None:
        domain_order = tuple(ProjectIRChangeDomain)
        if (
            type(self.changed_domains) is not tuple
            or not self.changed_domains
            or any(
                type(domain) is not ProjectIRChangeDomain
                for domain in self.changed_domains
            )
            or len(set(self.changed_domains)) != len(self.changed_domains)
            or self.changed_domains
            != tuple(sorted(self.changed_domains, key=domain_order.index))
        ):
            raise ValueError("Changed domains must be explicit, unique, and canonical.")
        expected_invalidated = tuple(
            kind
            for kind in ProjectIRAnalysisKind
            if any(
                domain in self.changed_domains
                for domain in _analysis_dependencies(kind)
            )
        )
        expected_preserved = tuple(
            kind for kind in ProjectIRAnalysisKind if kind not in expected_invalidated
        )
        if (
            self.invalidated != expected_invalidated
            or self.preserved != expected_preserved
        ):
            raise ValueError("Analysis invalidation disagrees with dependencies.")


def assess_project_ir_analysis_invalidation(
    changed_domains: tuple[ProjectIRChangeDomain, ...],
) -> ProjectIRAnalysisInvalidation:
    """Derive current preserved analyses without ever preserving verification."""

    invalidated = tuple(
        kind
        for kind in ProjectIRAnalysisKind
        if any(domain in changed_domains for domain in _analysis_dependencies(kind))
    )
    return ProjectIRAnalysisInvalidation(
        changed_domains=changed_domains,
        invalidated=invalidated,
        preserved=tuple(
            kind for kind in ProjectIRAnalysisKind if kind not in invalidated
        ),
    )


def _derive_reverse_uses(
    stage: ProjectIREvaluationContextStage,
) -> tuple[ProjectIRReverseUseEntry, ...]:
    structural = stage.project_plan.structural_stage
    return tuple(
        ProjectIRReverseUseEntry(
            output=output,
            uses=tuple(use for use in structural.uses if use.output is output),
        )
        for output in structural.outputs
    )


def _derive_reachability(
    structural: ProjectIRStructuralStage,
) -> tuple[ProjectIRReachabilityEntry, ...]:
    successors = _graph_successors(structural)
    if successors is None:
        raise ValueError("Verified structural endpoints are required for reachability.")
    entries: list[ProjectIRReachabilityEntry] = []
    for source in range(len(structural.nodes)):
        reachable = [False] * len(structural.nodes)
        pending = deque(successors[source])
        while pending:
            current = pending.popleft()
            if reachable[current]:
                continue
            reachable[current] = True
            pending.extend(successors[current])
        entries.append(
            ProjectIRReachabilityEntry(
                source=structural.nodes[source],
                reachable=tuple(
                    node
                    for index, node in enumerate(structural.nodes)
                    if reachable[index]
                ),
            )
        )
    return tuple(entries)


def _schema_signature(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> tuple[tuple[object, ...], ...]:
    shape = fragment.root_relation_output.row_shape
    if type(shape) is not ProjectIRRowShape:
        raise ValueError("Concrete root requires a final semantic row shape.")
    return tuple(
        (
            field.evidence.name,
            field.evidence.resolved_type,
            field.evidence.nullability,
            field.evidence.result_role,
        )
        for field in shape.fields
    )


def _root_properties(
    fragment: ProjectIRConcreteSingleRelationFragment,
    property_type: type[object],
) -> tuple[ProjectIRProvidedProperty, ...]:
    return tuple(
        property_
        for property_ in fragment.property_stage.provided
        if type(property_) is property_type
        and property_.output is fragment.root_relation_output
    )


def _dimension_statuses(
    left: ProjectIRConcreteSingleRelationFragment,
    right: ProjectIRConcreteSingleRelationFragment,
) -> tuple[ProjectIRSemanticDimensionAssessment, ...]:
    schema = (
        ProjectIRSemanticDimensionStatus.EVIDENCED
        if _schema_signature(left) == _schema_signature(right)
        else ProjectIRSemanticDimensionStatus.INCOMPATIBLE
    )
    values = ProjectIRSemanticDimensionStatus.NOT_PROVEN
    left_bag = _root_properties(left, ProjectIRProvidedBagMultiplicity)
    right_bag = _root_properties(right, ProjectIRProvidedBagMultiplicity)
    bag = (
        ProjectIRSemanticDimensionStatus.EVIDENCED
        if len(left_bag) == len(right_bag) == 1
        else ProjectIRSemanticDimensionStatus.INCOMPATIBLE
    )
    left_cardinality = _root_properties(
        left,
        ProjectIRProvidedCardinalityUpperBound,
    )
    right_cardinality = _root_properties(
        right,
        ProjectIRProvidedCardinalityUpperBound,
    )
    if not left_cardinality and not right_cardinality:
        cardinality = ProjectIRSemanticDimensionStatus.NOT_PROVEN
    elif len(left_cardinality) == len(right_cardinality) == 1 and (
        cast(ProjectIRProvidedCardinalityUpperBound, left_cardinality[0]).upper_bound
        == cast(
            ProjectIRProvidedCardinalityUpperBound,
            right_cardinality[0],
        ).upper_bound
    ):
        cardinality = ProjectIRSemanticDimensionStatus.EVIDENCED
    else:
        cardinality = ProjectIRSemanticDimensionStatus.INCOMPATIBLE
    left_order = _root_properties(left, ProjectIRProvidedRelationOrdering)
    right_order = _root_properties(right, ProjectIRProvidedRelationOrdering)
    if not left_order and not right_order:
        ordering = ProjectIRSemanticDimensionStatus.NOT_PROVEN
    elif len(left_order) == len(right_order) == 1 and (
        cast(ProjectIRProvidedRelationOrdering, left_order[0]).items
        == cast(ProjectIRProvidedRelationOrdering, right_order[0]).items
    ):
        ordering = ProjectIRSemanticDimensionStatus.EVIDENCED
    else:
        ordering = ProjectIRSemanticDimensionStatus.INCOMPATIBLE
    left_effects = left.property_stage.effects
    right_effects = right.property_stage.effects
    effect_axes = tuple(
        (effect.determinism, effect.error_behavior, effect.side_effects)
        for effect in left_effects
    )
    other_effect_axes = tuple(
        (effect.determinism, effect.error_behavior, effect.side_effects)
        for effect in right_effects
    )
    if effect_axes != other_effect_axes:
        effects = ProjectIRSemanticDimensionStatus.INCOMPATIBLE
    elif any(
        effect.determinism is ProjectIRDeterminismEvidence.UNKNOWN
        or effect.error_behavior is ProjectIRErrorBehaviorEvidence.UNKNOWN
        or effect.side_effects is ProjectIRSideEffectEvidence.UNKNOWN
        for effect in left_effects
    ):
        effects = ProjectIRSemanticDimensionStatus.NOT_PROVEN
    else:
        effects = ProjectIRSemanticDimensionStatus.EVIDENCED
    left_counts = tuple(effect.evaluation_count for effect in left_effects)
    right_counts = tuple(effect.evaluation_count for effect in right_effects)
    if left_counts != right_counts:
        evaluation_count = ProjectIRSemanticDimensionStatus.INCOMPATIBLE
    elif ProjectIREvaluationCountEvidence.UNKNOWN in left_counts:
        evaluation_count = ProjectIRSemanticDimensionStatus.NOT_PROVEN
    else:
        evaluation_count = ProjectIRSemanticDimensionStatus.EVIDENCED
    left_policies = tuple(
        property_.policy
        for property_ in left.property_stage.provided
        if type(property_) is ProjectIRProvidedEvaluationPolicy
    )
    right_policies = tuple(
        property_.policy
        for property_ in right.property_stage.provided
        if type(property_) is ProjectIRProvidedEvaluationPolicy
    )
    policy = (
        ProjectIRSemanticDimensionStatus.EVIDENCED
        if left_policies == right_policies
        else ProjectIRSemanticDimensionStatus.INCOMPATIBLE
    )
    statuses = (
        schema,
        values,
        bag,
        ProjectIRSemanticDimensionStatus.NOT_PROVEN,
        cardinality,
        ordering,
        effects,
        evaluation_count,
        policy,
        ProjectIRSemanticDimensionStatus.NOT_PROVEN,
        ProjectIRSemanticDimensionStatus.NOT_PROVEN,
    )
    return tuple(
        ProjectIRSemanticDimensionAssessment(dimension=dimension, status=status)
        for dimension, status in zip(
            ProjectIRSemanticDimension,
            statuses,
            strict=True,
        )
    )


def _derive_equivalence_assessments(
    stage: ProjectIREvaluationContextStage,
) -> tuple[ProjectIRSemanticEquivalenceAssessment, ...]:
    fragments = stage.project_plan.concrete_fragments
    assessments: list[ProjectIRSemanticEquivalenceAssessment] = []
    for left_index, left in enumerate(fragments):
        for right in fragments[left_index + 1 :]:
            dimensions = _dimension_statuses(left, right)
            statuses = tuple(item.status for item in dimensions)
            status = (
                ProjectIRSemanticEquivalenceStatus.KNOWN_INCOMPATIBLE
                if ProjectIRSemanticDimensionStatus.INCOMPATIBLE in statuses
                else (
                    ProjectIRSemanticEquivalenceStatus.REWRITE_EQUIVALENCE_PROVEN
                    if all(
                        item is ProjectIRSemanticDimensionStatus.EVIDENCED
                        for item in statuses
                    )
                    else ProjectIRSemanticEquivalenceStatus.CANDIDATE_NOT_DISPROVEN
                )
            )
            assessments.append(
                ProjectIRSemanticEquivalenceAssessment(
                    left=left,
                    right=right,
                    dimensions=dimensions,
                    status=status,
                )
            )
    return tuple(assessments)


def _rewrite_readiness(
    assessment: ProjectIRSemanticEquivalenceAssessment,
) -> ProjectIRRewriteReadiness:
    blockers = tuple(
        evidence.dimension
        for evidence in assessment.dimensions
        if evidence.status is not ProjectIRSemanticDimensionStatus.EVIDENCED
    )
    return ProjectIRRewriteReadiness(
        assessment=assessment,
        status=(
            ProjectIRRewriteReadinessStatus.ADMISSIBLE
            if not blockers
            and assessment.status
            is ProjectIRSemanticEquivalenceStatus.REWRITE_EQUIVALENCE_PROVEN
            else ProjectIRRewriteReadinessStatus.BLOCKED
        ),
        blockers=blockers,
    )


def _reverse_uses_match(
    actual: tuple[ProjectIRReverseUseEntry, ...],
    expected: tuple[ProjectIRReverseUseEntry, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.output is expected_item.output
        and _same_objects(
            cast(tuple[object, ...], item.uses),
            cast(tuple[object, ...], expected_item.uses),
        )
        for item, expected_item in zip(actual, expected, strict=True)
    )


def _reachability_matches(
    actual: tuple[ProjectIRReachabilityEntry, ...],
    expected: tuple[ProjectIRReachabilityEntry, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.source is expected_item.source
        and _same_objects(
            cast(tuple[object, ...], item.reachable),
            cast(tuple[object, ...], expected_item.reachable),
        )
        for item, expected_item in zip(actual, expected, strict=True)
    )


def _equivalence_matches(
    actual: tuple[ProjectIRSemanticEquivalenceAssessment, ...],
    expected: tuple[ProjectIRSemanticEquivalenceAssessment, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.left is expected_item.left
        and item.right is expected_item.right
        and item.dimensions == expected_item.dimensions
        and item.status is expected_item.status
        for item, expected_item in zip(actual, expected, strict=True)
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRAnalysisBundle:
    """Fresh detachable analyses over one independently verified stage."""

    verification: ProjectIRVerificationResult
    reverse_uses: tuple[ProjectIRReverseUseEntry, ...]
    topological_order: tuple[ProjectIRPlanNodeOccurrence, ...]
    reachability: tuple[ProjectIRReachabilityEntry, ...]
    equivalence_assessments: tuple[ProjectIRSemanticEquivalenceAssessment, ...]
    rewrite_readiness: tuple[ProjectIRRewriteReadiness, ...]

    def __post_init__(self) -> None:
        if (
            type(self.verification) is not ProjectIRVerificationResult
            or not self.verification.verified
            or self.verification.issues
        ):
            raise ValueError("Analyses require a freshly verified exact stage.")
        structural = self.verification.stage.project_plan.structural_stage
        expected_reverse = _derive_reverse_uses(self.verification.stage)
        expected_reachability = _derive_reachability(structural)
        expected_equivalence = _derive_equivalence_assessments(self.verification.stage)
        if (
            type(self.reverse_uses) is not tuple
            or not _reverse_uses_match(self.reverse_uses, expected_reverse)
            or not _same_objects(
                cast(tuple[object, ...], self.topological_order),
                cast(
                    tuple[object, ...],
                    _fresh_topological_order(structural) or (),
                ),
            )
            or not _reachability_matches(
                self.reachability,
                expected_reachability,
            )
            or not _equivalence_matches(
                self.equivalence_assessments,
                expected_equivalence,
            )
            or len(self.rewrite_readiness) != len(self.equivalence_assessments)
            or any(
                readiness.assessment is not assessment
                for readiness, assessment in zip(
                    self.rewrite_readiness,
                    self.equivalence_assessments,
                    strict=False,
                )
            )
        ):
            raise ValueError("Analysis bundle must retain fresh canonical products.")

    @property
    def stage(self) -> ProjectIREvaluationContextStage:
        return self.verification.stage


def build_project_ir_analysis_bundle(
    verification: ProjectIRVerificationResult,
) -> ProjectIRAnalysisBundle:
    """Recompute every current analysis from exact direct uses and facts."""

    if (
        type(verification) is not ProjectIRVerificationResult
        or not verification.verified
    ):
        raise ValueError("Only a VERIFIED exact stage may produce analyses.")
    stage = verification.stage
    topological = _fresh_topological_order(stage.project_plan.structural_stage)
    if topological is None:
        raise ValueError("Verified ordinary Project IR must remain acyclic.")
    equivalence = _derive_equivalence_assessments(stage)
    return ProjectIRAnalysisBundle(
        verification=verification,
        reverse_uses=_derive_reverse_uses(stage),
        topological_order=topological,
        reachability=_derive_reachability(stage.project_plan.structural_stage),
        equivalence_assessments=equivalence,
        rewrite_readiness=tuple(_rewrite_readiness(item) for item in equivalence),
    )
