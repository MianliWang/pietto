"""Independent verification and derived analyses for Phase-63 query-block IR."""

from __future__ import annotations

from pietto._project.project_verification_scope import once
from pietto._project import project_grain as grain
from pietto._project import project_joined_aggregation as joined_aggregation
from pietto._project import project_multifact as multifact

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pietto._project.project_query_block_ir import CompiledQueryBlockIR

from pietto._project.project_query_block_ir_algebra import ProjectIRComposedJoinPrefix
from pietto._project.project_final_outputs import (
    ProjectDistinct,
    ProjectCompletedSetOutput,
)

from pietto._project.project_current_join_inputs import ProjectCurrentMaterializedInput
from pietto._project.project_current_joins import (
    ProjectCurrentJoinRegion,
    ProjectCurrentJoinProperties,
    ProjectCurrentBinaryJoin,
    resolved_join_field_nullability,
)
from pietto._project.project_query_block import ProjectCurrentJoinedRowSource
from pietto._project.project_single_match import (
    ProjectSingleMatchProof,
    ProjectSingleMatchState,
)

from pietto._project.project_ir_joins import (
    ProjectIRJoinUnavailableProperty,
)


from dataclasses import dataclass, field
from enum import StrEnum
from heapq import heappop, heappush
from typing import Any, cast

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectRelationClauseDependencyKind,
)
from pietto._project.aggregate_grouped_schema import (
    ProjectComputedGroupKeyFact,
    ProjectGroupKeyFact,
)
from pietto._project.model import (
    ProjectResolvedTypeKind,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleWindowOutputFact,
    ProjectModuleRelationSemanticFacts,
)
from pietto._project.project_completion import ProjectExistingEffectiveOutput
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectEffectiveOutputCompletionTerminal,
    ProjectEffectiveOutputCompletionTerminalReason,
    ProjectCompletedOutputField,
    ProjectConcreteNoJoinReplay,
    ProjectNoJoinGroupedOutput,
    ProjectNoJoinQualifyKind,
    ProjectNoJoinScalarExpression,
    ProjectNoJoinWhereKind,
)
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectGrainFactorIdentity,
    ProjectGrainOriginKind,
    ProjectGroupedGrainFactorIdentity,
    ProjectJoinGrainFactorIdentity,
)
from pietto._project.project_ir import (
    _declaration_identity,
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIRJoinInputUseOccurrence,
    ProjectIRSetInputUseOccurrence,
    ProjectIROperatorFlowUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRRelationAnchor,
    ProjectIRUseOccurrence,
    ProjectIRUseRef,
)
from pietto._project.project_ir_operators import (
    ProjectIRLogicalOperatorKind,
    ProjectIRLogicalOperatorOccurrence,
)
from pietto._project.project_ir_properties import (
    ProjectIRDeterminismEvidence,
    ProjectIRErrorBehaviorEvidence,
    ProjectIREvaluationCountEvidence,
    ProjectIRJoinRowOutput,
    ProjectIRRelationRowOutput,
    ProjectIRSideEffectEvidence,
    ProjectIRProvidedNullExtension,
    ProjectIRProvidedPropertySlot,
    ProjectIRPropertyAvailability,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputRelationalProperties,
)
from pietto._project.project_ir_verification import (
    _verify_cross_relation_endpoints,
    _verify_operator_flow,
    ProjectIRChangeDomain,
    ProjectIRReachabilityEntry,
    ProjectIRVerificationIssue,
    ProjectIRVerificationRequirement,
)
from pietto._project.project_phase62_verification import (
    _comparison_valid,
)
from pietto._project.project_joined_aggregation import (
    ProjectJoinedAggregationMode,
    ProjectConcreteJoinedAggregation,
    ProjectJoinedComputedGroupKeyOccurrence,
    ProjectJoinedGroupKeyOccurrence,
    ProjectJoinedStageOutputOccurrence,
    ProjectJoinedStageOutputRole,
)
from pietto._project.project_joined_qualify import (
    ProjectConcreteJoinedQualify,
    ProjectNonConcreteJoinedQualify,
    ProjectJoinedQualifyStageKind,
)
from pietto._project.project_joined_row_filter import (
    ProjectJoinedRowFilterKind,
    ProjectNonConcreteJoinedRowFilter,
    ProjectJoinedRowMultiplicity,
)
from pietto._project.project_joined_row_semantics import (
    ProjectJoinedRowFieldSemantics,
    ProjectConcreteJoinedRowSemantics,
    ProjectNonConcreteJoinedRowSemantics,
)
from pietto._project.project_joined_windows import (
    ProjectSelectedWindowResultBinding,
)
from pietto._project.module_relation_resolution import (
    ProjectResolvedModuleRelationReference,
)
from pietto._project.project_relationship_uses import (
    ProjectRelationBindingOccurrence,
)
from pietto._project.relation_captures import (
    captured_field_reads,
    null_extended_bindings,
    outer_row_bindings,
)
from pietto._project.row_expression_type_facts import (
    project_row_field_to_semantic_value_type,
)
from pietto._project.project_query_block_ir import (
    ProjectIRCaptureStage,
    ProjectIRDistinctComparison,
    ProjectIRSingleMatchRetention,
    ProjectIRSingleMatchProofImage,
    ProjectIRQueryBlockGrainOrigin,
    ProjectIRQueryBlockRowField,
    ProjectIRQueryBlockRowDomainOrigin,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRCompletedSetOperationOutput,
    ProjectIRCompletedValuesOutput,
    ProjectIRQueryBlockAggregateEvaluationContext,
    ProjectIRQueryBlockEffectEvidence,
    ProjectIRQueryBlockEntry,
    ProjectIRQueryBlockOperatorExtensionKind,
    ProjectIRQueryBlockOperatorOccurrence,
    ProjectIRQueryBlockResultProperties,
    ProjectIRQueryBlockRowOutput,
    ProjectIRQueryBlockSnapshot,
    ProjectIRQueryBlockTerminal,
    ProjectIRQueryBlockTerminalReason,
    ProjectIRQueryBlockWindowEvidence,
    ProjectIRReboundExistingOutput,
    ProjectIRReusedEffectiveOutput,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength
from pietto._project.project_scalar_namespaces import (
    ProjectConcreteJoinedNamespaceExpression,
)
from pietto._project.project_scalar_references import ProjectScalarReferenceResolution
from pietto.ast_nodes import (
    AnyExpr,
    AuthoredJoinKind,
    WindowExpr,
    BlockRelationDef,
    CollectRelationExpr,
    DottedNameExpr,
    LetRelationDef,
    LiteralExpr,
    NameExpr,
    QueryDef,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    SelectBody,
    Span,
    TableDef,
    TableFunctionRelationDef,
    UnnestRelationDef,
    UnaryExpr,
)
from dataclasses import fields as _dataclass_fields, is_dataclass

__all__: tuple[str, ...] = ()


class ProjectIRQueryBlockVerificationStatus(StrEnum):
    VERIFIED = "verified"
    INVALID = "invalid"


class ProjectIRQueryBlockVerificationIssueKind(StrEnum):
    ROOT_CONTINUITY = "root_continuity"
    ALLOCATION = "allocation"
    LEDGER = "ledger"
    EXPRESSION_BLOCK_USE = "expression_block_use"
    CAPTURE_USE = "capture_use"
    ACTIVE_ROOT = "active_root"
    HISTORICAL_REUSE = "historical_reuse"
    JOIN_REUSE = "join_reuse"
    OPERATOR_SEQUENCE = "operator_sequence"
    SEMANTIC_EVIDENCE = "semantic_evidence"
    STRUCTURAL_ENDPOINT = "structural_endpoint"
    ROW_SHAPE = "row_shape"
    PROPERTIES = "properties"
    GRAIN_ORIGIN = "grain_origin"
    COMBINED_ACTUAL_USE_CYCLE = "combined_actual_use_cycle"
    CURRENT_JOIN_COMPOSITION_UNSUPPORTED = "current_join_composition_unsupported"


type ProjectIRQueryBlockVerificationCoordinate = (
    ProjectIRPlanNodeRef
    | ProjectIROutputValueRef
    | ProjectIRInputSlotRef
    | ProjectIRUseRef
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRQueryBlockVerificationIssue:
    kind: ProjectIRQueryBlockVerificationIssueKind
    coordinate: ProjectIRQueryBlockVerificationCoordinate | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectIRQueryBlockVerificationIssueKind:
            raise TypeError("Query-block verification issue requires an exact kind.")
        if self.coordinate is not None and type(self.coordinate) not in {
            ProjectIRPlanNodeRef,
            ProjectIROutputValueRef,
            ProjectIRInputSlotRef,
            ProjectIRUseRef,
        }:
            raise TypeError("Query-block verification issue coordinate is invalid.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockVerificationResult:
    root: ProjectIRQueryBlockSnapshot = field(
        repr=False,
        compare=False,
        hash=False,
    )
    status: ProjectIRQueryBlockVerificationStatus
    issues: tuple[ProjectIRQueryBlockVerificationIssue, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.root) is not ProjectIRQueryBlockSnapshot
            or type(self.status) is not ProjectIRQueryBlockVerificationStatus
        ):
            raise TypeError("Query-block verification requires exact typed roots.")
        if type(self.issues) is not tuple or any(
            type(item) is not ProjectIRQueryBlockVerificationIssue
            for item in self.issues
        ):
            raise TypeError("Query-block verification issues must be exact.")
        order = tuple(ProjectIRQueryBlockVerificationIssueKind)
        positions = tuple(order.index(item.kind) for item in self.issues)
        if positions != tuple(sorted(positions)) or len(set(positions)) != len(
            positions
        ):
            raise ValueError("Query-block issues require one fixed ordered pass.")
        if (self.status is ProjectIRQueryBlockVerificationStatus.VERIFIED) is bool(
            self.issues
        ):
            raise ValueError("Query-block verification status and issues disagree.")
        if self.status is ProjectIRQueryBlockVerificationStatus.VERIFIED and any(
            isinstance(entry, ProjectIRCompletedQueryBlockOutput)
            and entry.join_prefix is None
            and any(
                region.ledger.owner is entry.owner
                for region in self.root.completed.effective_outputs.current_regions
            )
            for entry in self.root.entries
        ):
            raise ValueError(
                "Current JOIN requires retained composition before VERIFIED."
            )

    @property
    def verified(self) -> bool:
        return self.status is ProjectIRQueryBlockVerificationStatus.VERIFIED


def _coordinate(
    subject: object | None,
) -> ProjectIRQueryBlockVerificationCoordinate | None:
    if type(subject) in {
        ProjectIRPlanNodeRef,
        ProjectIROutputValueRef,
        ProjectIRInputSlotRef,
        ProjectIRUseRef,
    }:
        return cast(ProjectIRQueryBlockVerificationCoordinate, subject)
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
    if isinstance(
        subject, (ProjectIRJoinInputUseOccurrence, ProjectIRSetInputUseOccurrence)
    ):
        return subject.ref
    if type(subject) is ProjectIRQueryBlockOperatorOccurrence:
        return subject.node.ref
    return None


def _record(
    issues: list[ProjectIRQueryBlockVerificationIssue],
    kind: ProjectIRQueryBlockVerificationIssueKind,
    subject: object | None = None,
) -> None:
    if any(item.kind is kind for item in issues):
        return
    issues.append(
        ProjectIRQueryBlockVerificationIssue(
            kind=kind,
            coordinate=_coordinate(subject),
        )
    )


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


type ProjectIRQueryBlockCombinedUse = (
    ProjectIRUseOccurrence
    | ProjectIROperatorFlowUseOccurrence
    | ProjectIRJoinInputUseOccurrence
    | ProjectIRSetInputUseOccurrence
)


def _combined_parts(
    root: ProjectIRQueryBlockSnapshot,
) -> tuple[
    tuple[ProjectIRPlanNodeOccurrence, ...],
    tuple[ProjectIROutputValueOccurrence, ...],
    tuple[ProjectIRQueryBlockCombinedUse, ...],
]:
    return (
        (*root.base_plan.structural_stage.nodes, *root.structural.nodes),
        (*root.base_plan.structural_stage.outputs, *root.structural.outputs),
        (*root.base_plan.structural_stage.uses, *root.structural.uses),
    )


def _combined_topology(
    root: ProjectIRQueryBlockSnapshot,
) -> (
    tuple[
        tuple[ProjectIRPlanNodeOccurrence, ...],
        tuple[ProjectIROutputValueOccurrence, ...],
        tuple[ProjectIRQueryBlockCombinedUse, ...],
        tuple[tuple[int, ...], ...],
        tuple[ProjectIRPlanNodeOccurrence, ...],
        tuple[ProjectIRReachabilityEntry, ...],
    ]
    | None
):
    nodes, outputs, uses = _combined_parts(root)
    node_positions = {node.ref: position for position, node in enumerate(nodes)}
    output_positions = {output.ref: position for position, output in enumerate(outputs)}
    if len(node_positions) != len(nodes) or len(output_positions) != len(outputs):
        return None
    successors: list[list[int]] = [[] for _node in nodes]
    indegree = [0] * len(nodes)
    for use in uses:
        producer = node_positions.get(use.output.producer.ref)
        consumer = node_positions.get(use.slot.consumer.ref)
        output = output_positions.get(use.output.ref)
        if (
            producer is None
            or consumer is None
            or output is None
            or nodes[producer] is not use.output.producer
            or nodes[consumer] is not use.slot.consumer
            or outputs[output] is not use.output
        ):
            return None
        successors[producer].append(consumer)
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
    if len(order) != len(nodes):
        return None
    reachability: list[ProjectIRReachabilityEntry] = []
    for source_position, source in enumerate(nodes):
        seen: set[int] = set()
        pending = list(successors[source_position])
        while pending:
            position = pending.pop()
            if position in seen:
                continue
            seen.add(position)
            pending.extend(successors[position])
        reachability.append(
            ProjectIRReachabilityEntry(
                source=source,
                reachable=tuple(
                    node for position, node in enumerate(nodes) if position in seen
                ),
            )
        )
    return (
        nodes,
        outputs,
        uses,
        tuple(tuple(values) for values in successors),
        tuple(order),
        tuple(reachability),
    )


def _entry_for_owner(
    root: ProjectIRQueryBlockSnapshot,
    owner: object,
) -> ProjectIRQueryBlockEntry | None:
    matches = tuple(entry for entry in root.entries if entry.owner is owner)
    return matches[0] if len(matches) == 1 else None


def _active_output(
    entry: ProjectIRQueryBlockEntry | None,
) -> ProjectIROutputValueOccurrence | None:
    if type(entry) is ProjectIRReusedEffectiveOutput:
        return entry.active_output.occurrence
    if type(entry) is ProjectIRReboundExistingOutput:
        return entry.active_output.occurrence
    if isinstance(
        entry,
        (
            ProjectIRCompletedQueryBlockOutput,
            ProjectIRCompletedSetOperationOutput,
            ProjectIRCompletedValuesOutput,
        ),
    ):
        return entry.active_output.occurrence
    return None


def _completed_active_operator(
    entry: ProjectIRCompletedQueryBlockOutput,
) -> ProjectIRQueryBlockOperatorOccurrence | None:
    semantic = entry.semantic_entry
    if semantic.limit is not None:
        kind = ProjectIRLogicalOperatorKind.LIMIT
        evidence = semantic.limit
    elif semantic.ordering is not None:
        kind = ProjectIRLogicalOperatorKind.RELATION_ORDERING
        evidence = semantic.ordering
    elif semantic.row_domain.distinct is not None:
        kind = ProjectIRQueryBlockOperatorExtensionKind.DISTINCT
        matches = tuple(
            operator
            for operator in entry.operators
            if operator.kind is kind
            and isinstance(operator.evidence, ProjectIRDistinctComparison)
            and operator.evidence.semantic is semantic.row_domain.distinct
        )
        return matches[0] if len(matches) == 1 else None
    else:
        kind = ProjectIRLogicalOperatorKind.FINAL_PROJECTION
        evidence = semantic
    matches = tuple(
        operator
        for operator in entry.operators
        if operator.kind is kind and operator.evidence is evidence
    )
    return matches[0] if len(matches) == 1 else None


def _rebound_row_outputs(
    entry: ProjectIRReboundExistingOutput,
) -> tuple[ProjectIRRelationRowOutput, ...]:
    values: list[ProjectIRRelationRowOutput] = []
    for operator in entry.rebuilt_fragment.logical_stage.operators:
        matches = tuple(
            output
            for output in entry.rebuilt_fragment.property_stage.outputs
            if type(output) is ProjectIRRelationRowOutput
            and output.occurrence.producer is operator.node
        )
        if len(matches) != 1:
            return ()
        values.append(matches[0])
    return tuple(values)


def _verify_active_roots(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    for entry in root.entries:
        if type(entry) is ProjectIRReusedEffectiveOutput:
            fragment = entry.semantic_entry.fragment
            historical_properties = (
                root.completed.verification.root.base_relational.outputs
            )
            valid = (
                entry.active_output is entry.semantic_entry.output
                and entry.active_output is fragment.root_relation_output
                and entry.active_output.occurrence.producer is fragment.root
                and entry.active_properties.relational
                is entry.semantic_entry.properties
                and entry.active_properties.output is entry.active_output
                and sum(
                    properties is entry.active_properties.relational
                    for properties in historical_properties
                )
                == 1
            )
        elif type(entry) is ProjectIRReboundExistingOutput:
            row_outputs = _rebound_row_outputs(entry)
            fragment = entry.rebuilt_fragment
            valid = (
                entry.active_output is fragment.root_relation_output
                and entry.active_output.occurrence.producer is fragment.root
                and sum(output is entry.active_output for output in row_outputs) == 1
                and entry.active_properties.output is entry.active_output
                and sum(
                    properties is entry.active_properties
                    for properties in entry.row_properties
                )
                == 1
            )
        elif type(entry) is ProjectIRCompletedQueryBlockOutput:
            operator = _completed_active_operator(entry)
            valid = (
                operator is not None
                and sum(output is entry.active_output for output in entry.row_outputs)
                == 1
                and entry.active_output.occurrence.producer is operator.node
                and entry.active_properties.output is entry.active_output
                and sum(
                    properties is entry.active_properties
                    for properties in entry.row_properties
                )
                == 1
            )
        elif isinstance(
            entry,
            (ProjectIRCompletedSetOperationOutput, ProjectIRCompletedValuesOutput),
        ):
            valid = (
                entry.active_output.row_shape.operator is entry.operator
                and entry.operator.evidence is entry.semantic_entry
                and entry.active_properties.output is entry.active_output
                and entry.active_output.occurrence.producer is entry.operator.node
            )
        elif type(entry) is ProjectIRQueryBlockTerminal:
            continue
        else:
            valid = False
        if not valid:
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.ACTIVE_ROOT,
                _active_output(entry),
            )
            return

    for entry in root.entries:
        if type(entry) is ProjectIRReboundExistingOutput:
            relation_input = entry.relation_input
        elif type(entry) is ProjectIRCompletedQueryBlockOutput:
            relation_input = entry.relation_input
        else:
            relation_input = None
        if relation_input is None:
            continue
        upstream = _entry_for_owner(root, relation_input.dependency.target)
        if type(upstream) not in {
            ProjectIRReusedEffectiveOutput,
            ProjectIRReboundExistingOutput,
            ProjectIRCompletedQueryBlockOutput,
            ProjectIRCompletedSetOperationOutput,
            ProjectIRCompletedValuesOutput,
        }:
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.ACTIVE_ROOT,
                relation_input.use,
            )
            return
        concrete_upstream = cast(
            ProjectIRReusedEffectiveOutput
            | ProjectIRReboundExistingOutput
            | ProjectIRCompletedQueryBlockOutput
            | ProjectIRCompletedSetOperationOutput
            | ProjectIRCompletedValuesOutput,
            upstream,
        )
        if (
            relation_input.use.output is not concrete_upstream.active_output.occurrence
            or relation_input.producer is not concrete_upstream.active_properties
        ):
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.ACTIVE_ROOT,
                relation_input.use,
            )
            return


def _verify_root_continuity(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> bool:
    completed = root.completed
    verification = completed.verification
    valid = (
        completed.roots.verification is verification
        and completed.roots.completion is completed.completion
        and completed.roots.effective_outputs is completed.effective_outputs
        and completed.effective_outputs.base is completed.completion
        and completed.completion.verification is verification
        and verification.verified
        and verification.root.evaluation.project_plan is root.base_plan
        and verification.root.join_regions is root.join_stage
        and root.join_stage.base_plan is root.base_plan
        and root.structural.base_plan is root.base_plan
        and root.structural.join_stage is root.join_stage
        and root.structural.starting_allocation is root.join_stage.ending_allocation
        and root.structural.starting_allocation.scope
        is root.base_plan.structural_stage.scope
    )
    if not valid:
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.ROOT_CONTINUITY)
    return valid


def _scheduled_entries(
    root: ProjectIRQueryBlockSnapshot,
) -> tuple[ProjectIRQueryBlockEntry, ...] | None:
    values: list[ProjectIRQueryBlockEntry] = []
    for owner in root.schedule:
        entry = _entry_for_owner(root, owner)
        if entry is None:
            return None
        values.append(entry)
    return tuple(values)


def _new_entry_parts(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[
    tuple[ProjectIRPlanNodeOccurrence, ...],
    tuple[ProjectIROutputValueOccurrence, ...],
    tuple[ProjectIRInputSlotOccurrence, ...],
    tuple[ProjectIRQueryBlockCombinedUse, ...],
]:
    if type(entry) is ProjectIRReboundExistingOutput:
        fragment = entry.rebuilt_fragment
        return (
            fragment.structural_stage.nodes,
            fragment.structural_stage.outputs,
            (*fragment.structural_stage.input_slots, entry.relation_input.input_slot),
            (*fragment.structural_stage.uses, entry.relation_input.use),
        )
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return (
            entry.nodes,
            entry.output_occurrences,
            (
                *(() if entry.join_prefix is None else entry.join_prefix.slots),
                *entry.input_slots,
            ),
            (
                *(() if entry.join_prefix is None else entry.join_prefix.uses),
                *entry.uses,
            ),
        )
    if isinstance(entry, ProjectIRCompletedSetOperationOutput):
        return entry.nodes, entry.output_occurrences, entry.input_slots, entry.uses
    if isinstance(entry, ProjectIRCompletedValuesOutput):
        return entry.nodes, entry.output_occurrences, (), ()
    return (), (), (), ()


def _verify_allocation(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    structural = root.structural
    start = structural.starting_allocation
    end = structural.ending_allocation
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
    valid = all(
        tuple(item.ref.position for item in items) == tuple(range(first, last))
        and all(item.ref.scope is start.scope for item in items)
        for items, first, last in values
    )
    scheduled = _scheduled_entries(root)
    if scheduled is None:
        valid = False
    else:
        expected = tuple(_new_entry_parts(entry) for entry in scheduled)
        valid = valid and all(
            _same_objects(
                cast(tuple[object, ...], actual),
                cast(
                    tuple[object, ...],
                    tuple(item for parts in expected for item in parts[position]),
                ),
            )
            for position, actual in enumerate(
                (
                    structural.nodes,
                    structural.outputs,
                    structural.input_slots,
                    structural.uses,
                )
            )
        )
    for entry in root.entries:
        if type(entry) in {
            ProjectIRReusedEffectiveOutput,
            ProjectIRQueryBlockTerminal,
        }:
            valid = valid and entry.ending_allocation is entry.starting_allocation
        elif type(entry) is ProjectIRReboundExistingOutput:
            valid = valid and (
                entry.starting_allocation.scope is start.scope
                and entry.ending_allocation.scope is start.scope
            )
        elif isinstance(
            entry,
            (
                ProjectIRCompletedQueryBlockOutput,
                ProjectIRCompletedSetOperationOutput,
                ProjectIRCompletedValuesOutput,
            ),
        ):
            valid = valid and (
                entry.starting_allocation.scope is start.scope
                and entry.ending_allocation.scope is start.scope
            )
        else:
            valid = False
    if not valid:
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.ALLOCATION)


def _verify_ledger(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    overlay = root.completed.effective_outputs
    valid = (
        root.owners is overlay.owners
        and root.dependencies is overlay.dependencies
        and root.schedule is overlay.schedule
        and len(root.entries) == len(root.owners)
        and len({id(owner) for owner in root.owners}) == len(root.owners)
        and all(
            entry.owner is owner and entry.semantic_entry is semantic
            for entry, owner, semantic in zip(
                root.entries,
                root.owners,
                overlay.entries,
                strict=True,
            )
        )
    )
    completion = root.completed.completion
    completion.__post_init__()
    blocked = {id(owner) for owner in completion.topology.blocked_owners}
    schedule_positions = {
        id(owner): position for position, owner in enumerate(root.schedule)
    }
    valid = (
        valid
        and len(schedule_positions) + len(blocked) == len(root.owners)
        and not set(schedule_positions) & blocked
        and all(
            schedule_positions.get(id(dependency.target), len(root.schedule))
            < schedule_positions[id(dependency.consumer)]
            for dependency in root.dependencies
            if id(dependency.consumer) not in blocked
        )
        and all(
            type(entry) is ProjectIRQueryBlockTerminal
            and entry.reason
            is ProjectIRQueryBlockTerminalReason.SEMANTIC_OUTPUT_NON_CONCRETE
            and entry.blocker is entry.semantic_entry
            for entry in root.entries
            if id(entry.owner) in blocked
        )
    )
    if not valid:
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.LEDGER)


_RELATION_READS = frozenset(
    {
        RelationExistsExpr,
        RelationMembershipExpr,
        RelationScalarExpr,
        AnyExpr,
        CollectRelationExpr,
    }
)


def _authored_relation_reads(definition: object) -> tuple[object, ...]:
    """Every relation-read node under one owner's own clauses, re-walked here."""
    found: list[object] = []
    pending: list[object] = [definition]
    while pending:
        value = pending.pop()
        kind = type(value)
        if kind is tuple:
            pending.extend(cast(tuple[object, ...], value))
            continue
        if (
            kind is Span
            or kind.__module__ != "pietto.ast_nodes"
            or not is_dataclass(value)
        ):
            continue
        if kind in _RELATION_READS:
            found.append(value)
        pending.extend(getattr(value, item.name) for item in _dataclass_fields(value))
    return tuple(found)


def _read_column(expression: object, output: object) -> int | None:
    """A scalar read's one named output column, a membership read's sole
    column; an existence read and a Collect read, which reads whole rows,
    have none."""
    if (
        type(expression) in {RelationExistsExpr, AnyExpr, CollectRelationExpr}
        or output is None
    ):
        return None
    fields = cast(Any, output).row_shape.fields
    if type(expression) is RelationMembershipExpr:
        return 0 if len(fields) == 1 else None
    if type(expression) is not RelationScalarExpr:
        return -1
    names = [item.evidence.name for item in fields]
    if names.count(expression.column_name) != 1:
        return None
    return names.index(expression.column_name)


def _verify_expression_block_uses(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    """Re-derive every expression-to-block edge from the authored owners.

    Each authored relation read is retained exactly once by the relation-name
    authority; each resolved read is exactly one completion edge and one IR
    edge between the exact ledger entries, scheduled producer first.
    """
    completion = root.completed.completion
    resolutions = root.completed.semantic_result.module_relation_resolutions
    if resolutions is None:
        raise ValueError("Expression block uses require relation authority.")
    entries = {id(entry.owner): entry for entry in root.entries}
    positions = {id(owner): i for i, owner in enumerate(root.schedule)}
    blocked = {id(owner) for owner in completion.topology.blocked_owners}
    expected = []
    valid = True
    for owner in root.owners:
        environments = resolutions.find_module_path(owner.identity.module_path)
        if len(environments) != 1:
            valid = False
            break
        reads = tuple(
            item
            for item in environments[0].expression_reads
            if item.read.owner is owner
        )
        authored = {id(node) for node in _authored_relation_reads(owner.definition)}
        listed = [id(item.read.expression) for item in reads]
        if (
            len(listed) != len(set(listed))
            or set(listed) != authored
            or [item.read.ordinal for item in reads] != list(range(len(reads)))
        ):
            valid = False
            break
        expected.extend(item for item in reads if item.target_symbol is not None)
    uses = completion.expression_uses
    valid = (
        valid
        and len(root.expression_uses) == len(expected) == len(uses)
        and all(
            edge.use is use
            and use.evidence is item
            and use.consumer is item.read.owner
            and item.target_symbol is not None
            and use.target is item.target_symbol.target_occurrence
            and edge.consumer is entries[id(use.consumer)]
            and edge.producer is entries[id(use.target)]
            and edge.output is edge.producer.output
            and edge.column == _read_column(item.read.expression, edge.output)
            and (
                id(use.consumer) in blocked
                or id(use.target) in blocked
                or positions[id(use.target)] < positions[id(use.consumer)]
            )
            for edge, use, item in zip(
                root.expression_uses, uses, expected, strict=True
            )
        )
    )
    if not valid:
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.EXPRESSION_BLOCK_USE)


def _capture_binding_name(dependency) -> str | None:
    evidence = dependency.evidence
    if type(evidence) is ProjectRelationBindingOccurrence:
        return evidence.name
    if type(evidence) is ProjectResolvedModuleRelationReference:
        source = evidence.reference.from_clause
        return source.binding_name or source.source_name
    return None


def _capture_outer_row(entry):
    """The outer row stage, output and binding fields, re-derived here."""
    if type(entry) in {ProjectIRReusedEffectiveOutput, ProjectIRReboundExistingOutput}:
        fragment = (
            entry.semantic_entry.fragment
            if type(entry) is ProjectIRReusedEffectiveOutput
            else entry.rebuilt_fragment
        )
        operator = fragment.logical_stage.operators[0]
        if operator.kind is not ProjectIRLogicalOperatorKind.RELATION_INPUT:
            return None
        outputs = tuple(
            output
            for output in fragment.property_stage.outputs
            if output.occurrence.producer is operator.node
        )
        if len(outputs) != 1:
            return None
        width = len(outputs[0].row_shape.fields)
        return ProjectIRCaptureStage.INPUT, outputs[0], {0: tuple(range(width))}
    if type(entry) is not ProjectIRCompletedQueryBlockOutput:
        return None
    root = entry.semantic_entry.root
    if type(root) is ProjectConcreteNoJoinReplay:
        if entry.operators[0].kind is not ProjectIRLogicalOperatorKind.RELATION_INPUT:
            return None
        output = entry.row_outputs[0]
        return (
            ProjectIRCaptureStage.INPUT,
            output,
            {0: tuple(range(len(output.row_shape.fields)))},
        )
    if type(root) is not ProjectConcreteJoinedQualify or entry.join_prefix is None:
        return None
    output = entry.join_prefix.final_join.output
    environment = (
        root.window_stage.input_aggregation.input_filter.joined_semantics
    ).namespaces.binding_environment
    fields = output.row_shape.fields
    bindings: dict[int, tuple[int, ...]] = {}
    introductions: list[object] = []
    for visible in environment.bindings:
        positions = tuple(item.position for item in visible.fields)
        uses = {id(fields[i].introduction_use) for i in positions}
        if len(uses) > 1 or any(
            fields[i].evidence is not item.evidence
            for i, item in zip(positions, visible.fields, strict=True)
        ):
            return None
        introductions.extend(uses)
        bindings[visible.binding.identity.binding_position] = positions
    if len(set(introductions)) != len(introductions):
        return None
    return ProjectIRCaptureStage.JOINED, output, bindings


def _lateral_outer_row(entry, use):
    """The LATERAL read and row of one capture, re-derived here.

    The let is the right input of the outer JOIN written at the let's single
    JOIN read; its row is that JOIN's output restricted to the bindings left
    of it, positioned as the final joined namespace positions them.
    """
    if (
        type(entry) is not ProjectIRCompletedQueryBlockOutput
        or entry.join_prefix is None
        or type(entry.semantic_entry.root) is not ProjectConcreteJoinedQualify
    ):
        return None
    let = cast(LetRelationDef, use.inner.authored_block)
    clauses = cast(SelectBody, cast(BlockRelationDef, use.outer.authored_block).body)
    joins = entry.join_prefix.joins
    found = tuple(
        k
        for k, join in enumerate(joins)
        if join.inputs[1].producer is use.inner
        and k < len(clauses.join_clauses)
        and join.condition.use.clause is clauses.join_clauses[k]
        and clauses.join_clauses[k].target_relation_name == let.name
    )
    if len(found) != 1:
        return None
    k = found[0]
    output = joins[k].output
    fields = output.row_shape.fields
    root = entry.semantic_entry.root
    environment = (
        root.window_stage.input_aggregation.input_filter.joined_semantics
    ).namespaces.binding_environment
    bindings: dict[int, tuple[int, ...]] = {}
    for visible in environment.bindings:
        binding = visible.binding.identity.binding_position
        if binding > k:
            continue
        positions = tuple(item.position for item in visible.fields)
        if any(
            not 0 <= i < len(fields) or fields[i].evidence is not item.evidence
            for i, item in zip(positions, visible.fields, strict=True)
        ):
            return None
        bindings[binding] = positions
    return (joins[k].inputs[1],), (ProjectIRCaptureStage.LATERAL, output, bindings)


def _verify_capture_uses(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    """Re-derive every capture edge, stage checkpoint and captured field.

    Each capture line of an inventory let binds the FROM or JOIN dependency of
    its declaration body that has the line's name; its IR image reads the
    outer row of that body's single read of the let; each captured field read
    is the one field of that binding with its name, and the let types it as
    that field, nullable whenever an outer JOIN may null-extend the binding.
    """
    completion = root.completed.completion
    entries = {id(entry.owner): entry for entry in root.entries}
    outers = {
        (owner.identity.module_path, owner.declaration_position): owner
        for owner in root.owners
        if owner.let_position is None and owner.unnest_position is None
    }
    dependencies = {
        (id(edge.consumer), edge.dependency_ordinal): edge for edge in root.dependencies
    }
    facts = {
        id(fragment.semantic_facts.owner): fragment.semantic_facts
        for fragment in completion.plan.fragments
    }
    expected = []
    for owner in root.owners:
        let = owner.authored_block
        if type(let) is not LetRelationDef or not let.captures:
            continue
        outer = outers[(owner.identity.module_path, owner.declaration_position)]
        positions = dict(
            outer_row_bindings(cast(BlockRelationDef, outer.authored_block))
        )
        for ordinal, clause in enumerate(let.captures):
            dependency = dependencies.get((id(outer), positions[clause.name]))
            if dependency is not None:
                expected.append((owner, outer, ordinal, dependency, clause.name))
    uses = completion.capture_uses
    valid = len(uses) == len(expected) and all(
        use.inner is inner
        and use.outer is outer
        and use.ordinal == ordinal
        and use.dependency is dependency
        and _capture_binding_name(dependency) == name
        for use, (inner, outer, ordinal, dependency, name) in zip(
            uses, expected, strict=True
        )
    )
    imaged = []
    for use in uses if valid else ():
        inner, outer = entries[id(use.inner)], entries[id(use.outer)]
        reads = tuple(
            edge
            for edge in root.expression_uses
            if edge.use.consumer is use.outer and edge.use.target is use.inner
        )
        lateral = None if reads else _lateral_outer_row(outer, use)
        if lateral is not None:
            reads, row = lateral
        elif (
            len(reads) != 1
            or isinstance(inner, ProjectIRQueryBlockTerminal)
            or isinstance(outer, ProjectIRQueryBlockTerminal)
        ):
            continue
        else:
            row = _capture_outer_row(outer)
        if row is None or isinstance(inner, ProjectIRQueryBlockTerminal):
            continue
        stage, output, bindings = row
        fields = bindings.get(use.dependency.dependency_ordinal)
        if fields is None:
            continue
        imaged.append((use, inner, outer, reads[0], stage, output, bindings, fields))
    valid = valid and len(root.capture_uses) == len(imaged)
    checkpoints: dict[int, object] = {}
    captured = []
    for edge, (use, inner, outer, read, stage, output, bindings, fields) in zip(
        root.capture_uses if valid else (), imaged, strict=True
    ):
        checkpoint = edge.checkpoint
        shared = checkpoints.setdefault(id(read), checkpoint)
        outer_definition = cast(BlockRelationDef, outer.owner.authored_block)
        nulled = null_extended_bindings(
            outer_definition, cast(LetRelationDef, use.inner.authored_block)
        )
        valid = valid and (
            edge.capture is use
            and edge.inner is inner
            and shared is checkpoint
            and checkpoint.outer is outer
            and checkpoint.read is read
            and checkpoint.stage is stage
            and (
                stage is ProjectIRCaptureStage.LATERAL
                or (stage is ProjectIRCaptureStage.JOINED)
                is bool(cast(SelectBody, outer_definition.body).join_clauses)
            )
            and checkpoint.output is output
            and dict(checkpoint.bindings) == bindings
            and edge.fields == fields
            and all(
                not output.row_shape.fields[i].nulling_joins
                or use.dependency.dependency_ordinal in nulled
                for i in fields
                if stage is not ProjectIRCaptureStage.INPUT
            )
        )
        environment = facts[id(use.inner)].captured_value_types
        for read_node in captured_field_reads(use.inner.authored_block):
            if read_node.ordinal != use.ordinal:
                continue
            named = tuple(
                i
                for i in fields
                if output.row_shape.fields[i].evidence.name == read_node.field
            )
            if len(named) != 1:
                continue
            evidence = output.row_shape.fields[named[0]].evidence
            expected_type = project_row_field_to_semantic_value_type(
                evidence,
                ProjectRowFieldNullability.NULLABLE
                if use.dependency.dependency_ordinal in nulled
                else evidence.nullability,
            )
            valid = valid and environment.get(read_node) == expected_type
            captured.append((read_node, edge, named[0]))
    order = {
        id(edge.inner): i for i, edge in reversed(tuple(enumerate(root.capture_uses)))
    }
    captured.sort(
        key=lambda item: (
            order[id(item[1].inner)],
            item[0].span.line,
            item[0].span.column,
        )
    )
    valid = (
        valid
        and len(root.captured_fields) == len(captured)
        and all(
            item.expression is node and item.capture is edge and item.position == i
            for item, (node, edge, i) in zip(
                root.captured_fields, captured, strict=True
            )
        )
    )
    if not valid:
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.CAPTURE_USE)


def _historical_edge(
    root: ProjectIRQueryBlockSnapshot,
    semantic: ProjectExistingEffectiveOutput,
):
    matches = tuple(
        edge
        for edge in root.base_plan.cross_relation_edges
        if edge.consumer is semantic.fragment
    )
    return matches[0] if len(matches) == 1 else None


def _verify_historical_reuse(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    for entry in root.entries:
        if type(entry) is ProjectIRReusedEffectiveOutput:
            semantic = entry.semantic_entry
            if (
                entry.active_output is not semantic.output
                or entry.active_properties.relational is not semantic.properties
                or entry.ending_allocation is not entry.starting_allocation
            ):
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.HISTORICAL_REUSE,
                    semantic.output.occurrence,
                )
                return
            if semantic.dependencies:
                if len(semantic.dependencies) != 1:
                    _record(
                        issues,
                        ProjectIRQueryBlockVerificationIssueKind.HISTORICAL_REUSE,
                    )
                    return
                dependency = semantic.dependencies[0]
                producer = _entry_for_owner(root, dependency.target)
                edge = _historical_edge(root, semantic)
                if edge is None or edge.use.output is not _active_output(producer):
                    _record(
                        issues,
                        ProjectIRQueryBlockVerificationIssueKind.HISTORICAL_REUSE,
                        edge.use if edge is not None else None,
                    )
                    return
        elif type(entry) is ProjectIRReboundExistingOutput:
            semantic = entry.semantic_entry
            edge = _historical_edge(root, semantic)
            dependency = entry.relation_input.dependency
            producer = _entry_for_owner(root, dependency.target)
            active = _active_output(producer)
            if (
                edge is None
                or edge.use.output is active
                or entry.rebuilt_fragment is semantic.fragment
                or entry.rebuilt_fragment.semantic_facts
                is not semantic.fragment.semantic_facts
                or active is None
                or entry.relation_input.use.output is not active
                or entry.relation_input.producer.output.occurrence is not active
                or not entry.relation_input.compatibility.satisfied
            ):
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.HISTORICAL_REUSE,
                    entry.relation_input.use,
                )
                return


def _joined_external_uses(
    entry: ProjectCompletedEffectiveOutput,
) -> tuple[ProjectIRJoinInputUseOccurrence, ...]:
    root = entry.root
    if type(root) is not ProjectConcreteJoinedQualify:
        return ()
    region = root.window_stage.input_aggregation.input_filter.joined_semantics.row_source.region
    nodes = tuple(join.node for join in region.joins)
    return tuple(
        use
        for join in region.joins
        for use in join.input_uses
        if not any(use.output.producer is node for node in nodes)
    )


def _owner_for_external_use(
    root: ProjectIRQueryBlockSnapshot,
    use: ProjectIRJoinInputUseOccurrence,
):
    anchor = use.output.anchor
    if type(anchor) is not ProjectIRRelationAnchor:
        return None
    matches = tuple(
        owner for owner in root.owners if anchor.identity.identity == owner.identity
    )
    return matches[0] if len(matches) == 1 else None


def _stale_external_uses(
    root: ProjectIRQueryBlockSnapshot,
    semantic: ProjectCompletedEffectiveOutput,
) -> tuple[ProjectIRJoinInputUseOccurrence, ...]:
    stale: list[ProjectIRJoinInputUseOccurrence] = []
    for use in _joined_external_uses(semantic):
        owner = _owner_for_external_use(root, use)
        active = None if owner is None else _entry_for_owner(root, owner)
        if _active_output(active) is not use.output:
            stale.append(use)
    return tuple(stale)


def _verify_join_reuse(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    for entry in root.entries:
        semantic = entry.semantic_entry
        if (
            type(semantic) is not ProjectCompletedEffectiveOutput
            or type(semantic.root) is not ProjectConcreteJoinedQualify
        ):
            continue
        if (
            isinstance(entry, ProjectIRCompletedQueryBlockOutput)
            and entry.join_prefix is not None
        ):
            continue
        if isinstance(entry, ProjectIRQueryBlockTerminal) and entry.reason in {
            ProjectIRQueryBlockTerminalReason.INVALID_SINGLE_MATCH,
            ProjectIRQueryBlockTerminalReason.ACTIVE_INPUTS_IR_NON_CONCRETE,
            ProjectIRQueryBlockTerminalReason.ACTIVE_UPSTREAM_IR_NON_CONCRETE,
        }:
            continue
        stale = _stale_external_uses(root, semantic)
        if type(entry) is ProjectIRCompletedQueryBlockOutput:
            if stale or entry.source_properties.output is not (
                semantic.root.window_stage.input_aggregation.input_filter.joined_semantics.final_output
            ):
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE,
                    stale[0] if stale else None,
                )
                return
        elif type(entry) is ProjectIRQueryBlockTerminal and entry.reason is (
            ProjectIRQueryBlockTerminalReason.EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED
        ):
            if not stale or not _same_objects(
                cast(tuple[object, ...], entry.blocker),
                cast(tuple[object, ...], stale),
            ):
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE,
                )
                return
        elif not stale:
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE,
            )
            return


def _expected_operator_specs(
    semantic: ProjectCompletedEffectiveOutput,
) -> tuple[tuple[object, object], ...]:
    root = semantic.root
    values: list[tuple[object, object]] = []
    if type(root) is ProjectConcreteJoinedQualify:
        window = root.window_stage
        aggregation = window.input_aggregation
        input_filter = aggregation.input_filter
        if input_filter.kind is ProjectJoinedRowFilterKind.AUTHORED_WHERE:
            values.append((ProjectIRLogicalOperatorKind.ROW_FILTER, input_filter))
        if aggregation.mode is not ProjectJoinedAggregationMode.ABSENT:
            values.append((ProjectIRLogicalOperatorKind.GROUP_AGGREGATE, aggregation))
        if aggregation.satisfying is not None:
            values.append(
                (ProjectIRLogicalOperatorKind.RESULT_FILTER, aggregation.satisfying)
            )
        if window.computations or root.hidden_computations:
            values.append(
                (
                    ProjectIRLogicalOperatorKind.WINDOW_EVALUATION,
                    (window.computations, root.hidden_computations),
                )
            )
        if root.kind is ProjectJoinedQualifyStageKind.AUTHORED_QUALIFY:
            values.append((ProjectIRQueryBlockOperatorExtensionKind.QUALIFY, root))
    elif type(root) is ProjectConcreteNoJoinReplay:
        values.append((ProjectIRLogicalOperatorKind.RELATION_INPUT, root))
        if root.where.kind is ProjectNoJoinWhereKind.AUTHORED_WHERE:
            values.append((ProjectIRLogicalOperatorKind.ROW_FILTER, root))
        if root.mode is not ProjectJoinedAggregationMode.ABSENT:
            values.append((ProjectIRLogicalOperatorKind.GROUP_AGGREGATE, root))
        definition = root.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            raise TypeError("Replay operator sequence requires a derived owner.")
        derived = cast(TableDef | QueryDef, definition)
        if derived.satisfying_clause is not None:
            values.append((ProjectIRLogicalOperatorKind.RESULT_FILTER, root))
        if root.window_outputs or root.qualify.hidden_attempts:
            values.append(
                (
                    ProjectIRLogicalOperatorKind.WINDOW_EVALUATION,
                    (root.window_outputs, root.qualify.hidden_attempts),
                )
            )
        if root.qualify.kind is ProjectNoJoinQualifyKind.AUTHORED_QUALIFY:
            values.append((ProjectIRQueryBlockOperatorExtensionKind.QUALIFY, root))
    else:
        raise TypeError("Completed operator sequence requires a closed root.")
    values.append((ProjectIRLogicalOperatorKind.FINAL_PROJECTION, semantic))
    if semantic.row_domain.distinct is not None:
        values.append(
            (
                ProjectIRQueryBlockOperatorExtensionKind.DISTINCT,
                semantic.row_domain.distinct,
            )
        )
    if semantic.ordering is not None:
        values.append(
            (ProjectIRLogicalOperatorKind.RELATION_ORDERING, semantic.ordering)
        )
    if semantic.limit is not None:
        values.append((ProjectIRLogicalOperatorKind.LIMIT, semantic.limit))
    return tuple(values)


def _evidence_matches(
    operator: ProjectIRQueryBlockOperatorOccurrence,
    semantic: ProjectCompletedEffectiveOutput,
    expected: object,
) -> bool:
    if type(expected) is ProjectDistinct:
        evidence = operator.evidence
        return (
            isinstance(evidence, ProjectIRDistinctComparison)
            and evidence.semantic is expected
            and expected is semantic.row_domain.distinct
        )
    if type(expected) is tuple:
        evidence = operator.evidence
        return (
            type(evidence) is ProjectIRQueryBlockWindowEvidence
            and evidence.completed_output is semantic
            and len(expected) == 2
            and type(expected[0]) is tuple
            and type(expected[1]) is tuple
            and _same_objects(
                cast(tuple[object, ...], evidence.selected),
                cast(tuple[object, ...], expected[0]),
            )
            and _same_objects(
                cast(tuple[object, ...], evidence.hidden),
                cast(tuple[object, ...], expected[1]),
            )
        )
    return operator.evidence is expected


def _verify_operator_sequence(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    for entry in root.entries:
        if type(entry) is ProjectIRReboundExistingOutput:
            original = entry.semantic_entry.fragment.logical_stage.operators
            rebuilt = entry.rebuilt_fragment.logical_stage.operators
            valid = len(original) == len(rebuilt) and all(
                actual.kind is retained.kind
                and actual.evidence is retained.evidence
                and actual.node.anchor.identity == retained.node.anchor.identity
                for actual, retained in zip(rebuilt, original, strict=True)
            )
            if not valid:
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.OPERATOR_SEQUENCE,
                    rebuilt[0] if rebuilt else None,
                )
                return
            continue
        if type(entry) is not ProjectIRCompletedQueryBlockOutput:
            continue
        expected = _expected_operator_specs(entry.semantic_entry)
        if len(entry.operators) != len(expected) or tuple(
            item.kind for item in entry.operators
        ) != tuple(item[0] for item in expected):
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.OPERATOR_SEQUENCE,
                entry.operators[0] if entry.operators else None,
            )
            return
        kinds = tuple(item.kind for item in entry.operators)
        root_semantic = entry.semantic_entry.root
        if type(root_semantic) is ProjectConcreteJoinedQualify and (
            ProjectIRLogicalOperatorKind.RELATION_INPUT in kinds
        ):
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.OPERATOR_SEQUENCE,
                entry.operators[0],
            )
            return
        qualify_positions = tuple(
            position
            for position, kind in enumerate(kinds)
            if kind is ProjectIRQueryBlockOperatorExtensionKind.QUALIFY
        )
        if qualify_positions and (
            len(qualify_positions) != 1
            or qualify_positions[0] == 0
            or kinds[qualify_positions[0] - 1]
            is not ProjectIRLogicalOperatorKind.WINDOW_EVALUATION
            or kinds[qualify_positions[0] + 1]
            is not ProjectIRLogicalOperatorKind.FINAL_PROJECTION
        ):
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.OPERATOR_SEQUENCE,
                entry.operators[qualify_positions[0]],
            )
            return


def _verify_semantic_evidence(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    for entry in root.entries:
        if type(entry) is not ProjectIRCompletedQueryBlockOutput:
            continue
        expected = _expected_operator_specs(entry.semantic_entry)
        if len(expected) != len(entry.operators) or any(
            not _evidence_matches(operator, entry.semantic_entry, evidence)
            for operator, (_, evidence) in zip(
                entry.operators,
                expected,
                strict=True,
            )
        ):
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                entry.operators[0] if entry.operators else None,
            )
            return
        group_operators = tuple(
            item
            for item in entry.operators
            if item.kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
        )
        if len(group_operators) != len(entry.aggregate_contexts) or any(
            context.operator is not operator
            for context, operator in zip(
                entry.aggregate_contexts,
                group_operators,
                strict=True,
            )
        ):
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                group_operators[0] if group_operators else None,
            )
            return
        for operator in entry.operators:
            if operator.kind is ProjectIRQueryBlockOperatorExtensionKind.DISTINCT:
                comparison = operator.evidence
                incoming = tuple(
                    use.output
                    for use in entry.uses
                    if use.slot.consumer is operator.node
                )
                if (
                    not isinstance(comparison, ProjectIRDistinctComparison)
                    or len(incoming) != 1
                    or incoming[0] is not comparison.input_output.occurrence
                    or not any(
                        output is comparison.input_output
                        for output in entry.row_outputs
                    )
                    or comparison.input_output.row_shape.operator.kind
                    is not ProjectIRLogicalOperatorKind.FINAL_PROJECTION
                    or comparison.input_output.row_shape.operator.evidence
                    is not entry.semantic_entry
                    or len(comparison.fields) != len(entry.semantic_entry.fields)
                    or any(
                        field.semantic_source is not selected
                        or field.final_identity is not selected.identity
                        for field, selected in zip(
                            comparison.fields, entry.semantic_entry.fields, strict=True
                        )
                    )
                ):
                    _record(
                        issues,
                        ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                        operator,
                    )
                    return
            owned = tuple(
                scalar
                for scalar in entry.scalar_outputs
                if scalar.occurrence.producer is operator.node
            )
            if operator.kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION:
                evidence = operator.evidence
                if type(evidence) is not ProjectIRQueryBlockWindowEvidence or len(
                    owned
                ) != len(evidence.selected):
                    _record(
                        issues,
                        ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                        operator,
                    )
                    return
            elif operator.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
                if len(owned) != len(entry.semantic_entry.fields) or any(
                    scalar.semantic_source is not completed
                    or scalar.final_identity is not completed.identity
                    for scalar, completed in zip(
                        owned,
                        entry.semantic_entry.fields,
                        strict=True,
                    )
                ):
                    _record(
                        issues,
                        ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                        operator,
                    )
                    return
            elif owned:
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                    operator,
                )
                return


def _verify_structural_endpoints(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    nodes, outputs, uses = _combined_parts(root)
    slots = (
        *root.base_plan.structural_stage.input_slots,
        *root.structural.input_slots,
    )
    # Each historical use reads exactly the output its Phase-62 owner names:
    # a relation read its edge producer's root at the edge slot and an
    # operator flow its previous operator's row.
    historical: list[ProjectIRVerificationIssue] = []
    _verify_cross_relation_endpoints(root.base_plan, historical)
    _verify_operator_flow(root.base_plan, historical)
    valid = (
        not historical
        and len({node.ref for node in nodes}) == len(nodes)
        and len({output.ref for output in outputs}) == len(outputs)
        and len({slot.ref for slot in slots}) == len(slots)
        and len({use.ref for use in uses}) == len(uses)
        and all(any(output.producer is node for node in nodes) for output in outputs)
        and all(any(slot.consumer is node for node in nodes) for slot in slots)
        and all(
            any(use.output is output for output in outputs)
            and any(use.slot is slot for slot in slots)
            for use in uses
        )
        # Base-plan relation reads follow declaration order, so a read of a
        # later declaration points backwards; acyclicity covers them.
        and all(
            type(use) is ProjectIRUseOccurrence
            or use.output.producer.ref.position < use.slot.consumer.ref.position
            for use in root.base_plan.structural_stage.uses
        )
        and all(
            use.output.producer.ref.position < use.slot.consumer.ref.position
            for use in root.structural.uses
        )
        and len({use.slot.ref for use in uses}) == len(uses)
    )
    for entry in root.entries:
        # Each new operator reads exactly the row before it.
        if type(entry) is ProjectIRCompletedQueryBlockOutput:
            valid = valid and all(
                use.slot is slot
                and slot.consumer is operator.node
                and slot.input_ordinal == 0
                and use.output is incoming.occurrence
                for operator, slot, use, incoming in zip(
                    entry.operators,
                    entry.input_slots,
                    entry.uses,
                    (entry.source_properties.output, *entry.row_outputs[:-1]),
                    strict=True,
                )
            )
        elif type(entry) is ProjectIRReboundExistingOutput:
            fragment = entry.rebuilt_fragment
            valid = valid and all(
                use.slot.consumer is operator.node and use.output is incoming.occurrence
                for operator, use, incoming in zip(
                    fragment.logical_stage.operators[1:],
                    fragment.structural_stage.uses,
                    _rebound_row_outputs(entry)[:-1],
                    strict=True,
                )
            )
    if not valid:
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.STRUCTURAL_ENDPOINT)


def _verify_row_shapes(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    for entry in root.entries:
        if type(entry) is not ProjectIRCompletedQueryBlockOutput:
            continue
        for operator, output in zip(
            entry.operators,
            entry.row_outputs,
            strict=True,
        ):
            fields = output.row_shape.fields
            if (
                output.row_shape.operator is not operator
                or tuple(field.field_position for field in fields)
                != tuple(range(len(fields)))
                or any(
                    field.nulling_joins
                    and field.effective_nullability
                    is not ProjectRowFieldNullability.NULLABLE
                    for field in fields
                )
            ):
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.ROW_SHAPE,
                    output.occurrence,
                )
                return
            if operator.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
                if len(fields) != len(entry.semantic_entry.fields) or any(
                    field.evidence is not completed.field
                    or field.semantic_source is not completed
                    or field.final_identity is not completed.identity
                    for field, completed in zip(
                        fields,
                        entry.semantic_entry.fields,
                        strict=True,
                    )
                ):
                    _record(
                        issues,
                        ProjectIRQueryBlockVerificationIssueKind.ROW_SHAPE,
                        output.occurrence,
                    )
                    return
            elif any(field.final_identity is not None for field in fields):
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.ROW_SHAPE,
                    output.occurrence,
                )
                return


def _class_signatures(
    properties: ProjectIROutputRelationalProperties,
) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(member.field_position for member in value_class.members)
        for value_class in properties.value_classes
    )


def _nested_positions(properties: ProjectIROutputRelationalProperties) -> set[int]:
    """A nested relation has no equality, so it is in no value class
    (D-S04-3)."""
    return {
        field.field_position
        for field in properties.fields
        if field.evidence.resolved_type.kind is ProjectResolvedTypeKind.NESTED_RELATION
    }


def _property_shape_valid(properties: ProjectIROutputRelationalProperties) -> bool:
    output = properties.output
    fields = properties.fields
    if len(fields) != len(output.row_shape.fields) or any(
        field.field_position != position
        or field.evidence is not output.row_shape.fields[position].evidence
        for position, field in enumerate(fields)
    ):
        return False
    nested = _nested_positions(properties)
    classed = tuple(field for field in fields if field.field_position not in nested)
    members = tuple(
        member
        for value_class in properties.value_classes
        for member in value_class.members
    )
    return (
        len(members) == len(classed)
        and len({id(member) for member in members}) == len(classed)
        and all(any(member is field for member in members) for field in classed)
        and tuple(
            min(member.field_position for member in value_class.members)
            for value_class in properties.value_classes
        )
        == tuple(
            sorted(
                min(member.field_position for member in value_class.members)
                for value_class in properties.value_classes
            )
        )
    )


def _fd_index_valid(properties: ProjectIROutputRelationalProperties) -> bool:
    index = properties.fd_index
    classes = properties.value_classes
    if (
        index.output is not properties.output
        or not _same_objects(
            cast(tuple[object, ...], index.universe),
            cast(tuple[object, ...], classes),
        )
        or not _same_objects(
            cast(tuple[object, ...], index.facts),
            cast(tuple[object, ...], properties.fds),
        )
        or dict(index.positions)
        != {item: position for position, item in enumerate(classes)}
    ):
        return False
    positions = {item: position for position, item in enumerate(classes)}
    expected_strict = tuple(
        fact
        for fact in properties.fds
        if fact.strength is ProjectRowUniquenessStrength.STRICT
    )
    expected_lax = tuple(
        fact
        for fact in properties.fds
        if fact.strength is ProjectRowUniquenessStrength.LAX
    )
    for rules, facts in (
        (index.strict_rules, expected_strict),
        (index.lax_rules, expected_lax),
    ):
        if len(rules) != len(facts) or any(
            rule.fact is not fact
            or rule.lhs_mask != sum(1 << positions[item] for item in fact.determinants)
            or rule.rhs_mask != sum(1 << positions[item] for item in fact.dependents)
            for rule, fact in zip(rules, facts, strict=True)
        ):
            return False
    expected_incidents = tuple(
        tuple(
            rule_position
            for rule_position, rule in enumerate(index.strict_rules)
            if rule.lhs_mask & (1 << position)
        )
        for position in range(len(classes))
    )
    return index.incidents == expected_incidents


def _preserved_class_signatures(
    incoming: ProjectIROutputRelationalProperties,
    output_count: int,
) -> tuple[tuple[int, ...], ...]:
    values: list[tuple[int, ...]] = []
    used: set[int] = set()
    for value_class in incoming.value_classes:
        members = tuple(
            member.field_position
            for member in value_class.members
            if member.field_position < output_count
        )
        if members:
            values.append(members)
            used.update(members)
    values.extend(
        (position,) for position in range(output_count) if position not in used
    )
    values.sort(key=min)
    return tuple(values)


def _input_class_position(
    incoming: ProjectIROutputRelationalProperties,
    field_position: int,
) -> int | None:
    matches = tuple(
        position
        for position, value_class in enumerate(incoming.value_classes)
        if any(
            member.field_position == field_position for member in value_class.members
        )
    )
    return matches[0] if len(matches) == 1 else None


def _query_input_semantic_source(
    entry: ProjectIRCompletedQueryBlockOutput,
    incoming: ProjectIROutputRelationalProperties,
    field_position: int,
) -> object:
    input_output = incoming.output
    if type(input_output) is ProjectIRQueryBlockRowOutput:
        return input_output.row_shape.fields[field_position].semantic_source
    if type(input_output) is ProjectIRJoinRowOutput:
        semantic_root = entry.semantic_entry.root
        if type(semantic_root) is not ProjectConcreteJoinedQualify:
            raise TypeError("JOIN input requires exact joined semantic authority.")
        fields = semantic_root.window_stage.input_aggregation.input_filter.fields
        return fields[field_position]
    raise TypeError("Completed query-block source requires an exact row output.")


def _direct_query_input_position(
    entry: ProjectIRCompletedQueryBlockOutput,
    completed: object,
    incoming: ProjectIROutputRelationalProperties,
) -> int | None:
    if type(completed) is not ProjectCompletedOutputField:
        return None
    authority = completed.source
    root = entry.semantic_entry.root
    if type(root) is ProjectConcreteJoinedQualify:
        if type(authority) is ProjectConcreteJoinedNamespaceExpression:
            if (
                type(authority.expression) not in {NameExpr, DottedNameExpr}
                or len(authority.resolutions) != 1
            ):
                return None
            resolution = authority.resolutions[0]
            if type(resolution) is not ProjectScalarReferenceResolution or (
                resolution.target is None
            ):
                return None
            matches = tuple(
                field.field_position
                for field in incoming.fields
                if type(
                    _query_input_semantic_source(
                        entry,
                        incoming,
                        field.field_position,
                    )
                )
                is ProjectJoinedRowFieldSemantics
                and cast(
                    ProjectJoinedRowFieldSemantics,
                    _query_input_semantic_source(
                        entry,
                        incoming,
                        field.field_position,
                    ),
                ).scalar_field
                is resolution.target
            )
        elif type(authority) in {
            ProjectJoinedStageOutputOccurrence,
            ProjectSelectedWindowResultBinding,
        }:
            matches = tuple(
                field.field_position
                for field in incoming.fields
                if _query_input_semantic_source(
                    entry,
                    incoming,
                    field.field_position,
                )
                is authority
            )
        else:
            return None
    elif type(root) is ProjectConcreteNoJoinReplay:
        if type(authority) is ProjectNoJoinScalarExpression:
            provenance = completed.field.provenance
            expression = authority.expression
            if (
                provenance is None
                or provenance.kind
                is not ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
                or type(expression) not in {NameExpr, DottedNameExpr}
            ):
                return None
            if type(expression) is NameExpr:
                name = expression.name
            elif type(expression) is DottedNameExpr:
                definition = root.owner.definition
                if (
                    type(definition) not in {TableDef, QueryDef}
                    or len(expression.parts) != 2
                ):
                    return None
                derived = cast(TableDef | QueryDef, definition)
                if expression.parts[0] != (
                    derived.from_clause.binding_name or derived.from_clause.source_name
                ):
                    return None
                name = expression.parts[1]
            else:
                return None
            target = root.input_schema.fields.get(name)
            matches = tuple(
                field.field_position
                for field in incoming.fields
                if target is not None and field.evidence is target
            )
        elif type(authority) in {
            ProjectNoJoinGroupedOutput,
            ProjectModuleWindowOutputFact,
        }:
            matches = tuple(
                field.field_position
                for field in incoming.fields
                if _query_input_semantic_source(
                    entry,
                    incoming,
                    field.field_position,
                )
                is authority
            )
        else:
            return None
    else:
        return None
    return matches[0] if len(matches) == 1 else None


def _query_projection_class_signatures(
    entry: ProjectIRCompletedQueryBlockOutput,
    incoming: ProjectIROutputRelationalProperties,
) -> tuple[tuple[int, ...], ...]:
    members_by_class: list[list[int]] = [list() for _ in incoming.value_classes]
    assigned: set[int] = set()
    for output_position, completed in enumerate(entry.semantic_entry.fields):
        input_position = _direct_query_input_position(entry, completed, incoming)
        if input_position is None:
            continue
        class_position = _input_class_position(incoming, input_position)
        if class_position is None:
            return ()
        members_by_class[class_position].append(output_position)
        assigned.add(output_position)
    values = [tuple(items) for items in members_by_class if items]
    values.extend(
        (position,)
        for position in range(len(entry.semantic_entry.fields))
        if position not in assigned
    )
    values.sort(key=min)
    return tuple(values)


def _historical_projection_class_signatures(
    entry: ProjectIRReboundExistingOutput,
    incoming: ProjectIROutputRelationalProperties,
) -> tuple[tuple[int, ...], ...]:
    semantic = entry.rebuilt_fragment.semantic_facts
    members_by_class: list[list[int]] = [list() for _ in incoming.value_classes]
    assigned: set[int] = set()
    output_count = len(entry.active_output.row_shape.fields)
    for fact in semantic.select_facts:
        if (
            fact.selected_output_ordinal >= output_count
            or len(fact.references) != 1
            or type(fact.item.expression) not in {NameExpr, DottedNameExpr}
        ):
            continue
        reference = fact.references[0]
        matches = tuple(
            position
            for position, value_class in enumerate(incoming.value_classes)
            if any(
                reference.input_field is member.evidence
                or fact.field is member.evidence
                for member in value_class.members
            )
        )
        if len(matches) == 1:
            members_by_class[matches[0]].append(fact.selected_output_ordinal)
            assigned.add(fact.selected_output_ordinal)
    values = [tuple(items) for items in members_by_class if items]
    values.extend(
        (position,) for position in range(output_count) if position not in assigned
    )
    values.sort(key=min)
    return tuple(values)


type _KeySignature = tuple[tuple[int, ...], ProjectRowUniquenessStrength]
type _FDSignature = tuple[
    tuple[int, ...],
    tuple[int, ...],
    ProjectRowUniquenessStrength,
]
type _VerifiedOperator = (
    ProjectIRLogicalOperatorOccurrence | ProjectIRQueryBlockOperatorOccurrence
)


def _actual_key_signatures(
    properties: ProjectIROutputRelationalProperties,
) -> tuple[_KeySignature, ...]:
    positions = {
        value_class: position
        for position, value_class in enumerate(properties.value_classes)
    }
    return tuple(
        (
            tuple(positions[item] for item in key.determinants),
            key.strength,
        )
        for key in properties.keys
    )


def _actual_fd_signatures(
    properties: ProjectIROutputRelationalProperties,
) -> tuple[_FDSignature, ...]:
    positions = {
        value_class: position
        for position, value_class in enumerate(properties.value_classes)
    }
    return tuple(
        (
            tuple(positions[item] for item in fact.determinants),
            tuple(positions[item] for item in fact.dependents),
            fact.strength,
        )
        for fact in properties.fds
    )


def _frontier_key_signatures(
    values: tuple[_KeySignature, ...],
) -> tuple[_KeySignature, ...]:
    merged: list[_KeySignature] = []
    for value in values:
        if value not in merged:
            merged.append(value)
    retained: list[_KeySignature] = []
    for position, key in enumerate(merged):
        determinants, strength = key
        fields = frozenset(determinants)
        if any(
            frozenset(other[0]) <= fields
            and (
                other[1] is ProjectRowUniquenessStrength.STRICT or other[1] is strength
            )
            for other_position, other in enumerate(merged)
            if other_position != position
        ):
            continue
        retained.append(key)
    return tuple(retained)


def _mapped_class_signatures(
    *,
    kind: ProjectIRLogicalOperatorKind | ProjectIRQueryBlockOperatorExtensionKind,
    owner_entry: ProjectIRCompletedQueryBlockOutput | ProjectIRReboundExistingOutput,
    incoming: ProjectIROutputRelationalProperties,
    output_count: int,
) -> tuple[tuple[int, ...] | None, ...]:
    if kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
        members: list[list[int]] = [list() for _ in incoming.value_classes]
        if type(owner_entry) is ProjectIRCompletedQueryBlockOutput:
            for output_position, completed in enumerate(
                owner_entry.semantic_entry.fields
            ):
                input_position = _direct_query_input_position(
                    owner_entry,
                    completed,
                    incoming,
                )
                if input_position is None:
                    continue
                class_position = _input_class_position(incoming, input_position)
                if class_position is not None:
                    members[class_position].append(output_position)
        elif type(owner_entry) is ProjectIRReboundExistingOutput:
            semantic = owner_entry.rebuilt_fragment.semantic_facts
            for fact in semantic.select_facts:
                if (
                    fact.selected_output_ordinal >= output_count
                    or len(fact.references) != 1
                    or type(fact.item.expression) not in {NameExpr, DottedNameExpr}
                ):
                    continue
                reference = fact.references[0]
                matches = tuple(
                    position
                    for position, value_class in enumerate(incoming.value_classes)
                    if any(
                        reference.input_field is member.evidence
                        or fact.field is member.evidence
                        for member in value_class.members
                    )
                )
                if len(matches) == 1:
                    members[matches[0]].append(fact.selected_output_ordinal)
        else:
            raise TypeError("Projection image requires one closed IR entry.")
        return tuple(tuple(items) if items else None for items in members)
    return tuple(
        (
            tuple(
                member.field_position
                for member in value_class.members
                if member.field_position < output_count
            )
            or None
        )
        for value_class in incoming.value_classes
    )


def _expected_imaged_key_fd_signatures(
    *,
    incoming: ProjectIROutputRelationalProperties,
    output: ProjectIROutputRelationalProperties,
    images: tuple[tuple[int, ...] | None, ...],
    coalesced: bool = False,
) -> tuple[tuple[_KeySignature, ...], tuple[_FDSignature, ...]]:
    class_signatures = _class_signatures(output)
    target_positions = {
        signature: position for position, signature in enumerate(class_signatures)
    }
    image_positions = tuple(
        None if image is None else target_positions.get(image) for image in images
    )
    incoming_positions = {
        value_class: position
        for position, value_class in enumerate(incoming.value_classes)
    }
    candidates: list[_KeySignature] = []
    for key in incoming.keys:
        old_positions = tuple(incoming_positions[item] for item in key.determinants)
        mapped = tuple(image_positions[position] for position in old_positions)
        if any(position is None for position in mapped):
            continue
        determinants = tuple(cast(int, position) for position in mapped)
        if coalesced:
            determinants = tuple(
                position
                for position in range(len(output.value_classes))
                if position in determinants
            )
        strength = (
            ProjectRowUniquenessStrength.STRICT
            if all(
                all(
                    member.effective_nullability is ProjectRowFieldNullability.NON_NULL
                    for member in output.value_classes[position].members
                )
                for position in determinants
            )
            else key.strength
        )
        candidates.append((determinants, strength))
    keys = _frontier_key_signatures(tuple(candidates))
    facts: list[_FDSignature] = []
    for fact in incoming.fds:
        determinants = tuple(
            image_positions[incoming_positions[item]] for item in fact.determinants
        )
        if any(position is None for position in determinants):
            continue
        dependents = tuple(
            cast(int, image_positions[incoming_positions[item]])
            for item in fact.dependents
            if image_positions[incoming_positions[item]] is not None
        )
        if coalesced:
            determinants = tuple(
                position
                for position in range(len(output.value_classes))
                if position in determinants
            )
            dependents = tuple(
                position
                for position in range(len(output.value_classes))
                if position in dependents and position not in determinants
            )
        if dependents:
            facts.append(
                (
                    tuple(cast(int, position) for position in determinants),
                    dependents,
                    fact.strength,
                )
            )
    for determinants, strength in keys:
        dependents = tuple(
            position
            for position in range(len(output.value_classes))
            if position not in determinants
        )
        if dependents:
            facts.append((determinants, dependents, strength))
    merged: list[_FDSignature] = []
    for fact in facts:
        if fact not in merged:
            merged.append(fact)
    return keys, tuple(merged)


def _group_key_positions(
    properties: ProjectIROutputRelationalProperties,
    context: ProjectIRQueryBlockAggregateEvaluationContext,
) -> tuple[int, ...] | None:
    """Independently check determinant authority and its visible occurrence image."""
    readiness = None
    basis = context.semantic_basis
    if type(basis) is ProjectConcreteJoinedAggregation:
        definition = basis.input_filter.entry.owner.definition
        keys = basis.group_keys
        outputs = basis.stage_outputs
        if basis.mode is not context.mode:
            return None
        items = tuple(key.item for key in keys)
        if any(
            type(key.source_ordinal) is not int
            or key.source_ordinal != i
            or key.input_filter is not basis.input_filter
            or not (
                type(key) is ProjectJoinedComputedGroupKeyOccurrence
                or type(key) is ProjectJoinedGroupKeyOccurrence
                and any(
                    key.field_semantics is row_field
                    for row_field in basis.input_filter.fields
                )
            )
            for i, key in enumerate(keys)
        ):
            return None
        selected = {}
        for output in outputs:
            if output.role is ProjectJoinedStageOutputRole.GROUP_KEY:
                matches = [i for i, key in enumerate(keys) if output.group_key is key]
                if len(matches) != 1:
                    return None
                selected[id(output)] = matches[0]
    elif type(basis) in {
        ProjectConcreteNoJoinReplay,
        ProjectModuleRelationSemanticFacts,
    }:
        assert isinstance(
            basis, (ProjectConcreteNoJoinReplay, ProjectModuleRelationSemanticFacts)
        )
        if isinstance(basis, ProjectConcreteNoJoinReplay):
            definition = basis.owner.definition
            readiness = basis.aggregate_readiness
            schema = basis.base_state.schema
            outputs = () if schema is None else tuple(schema.fields.values())
            if basis.mode is not context.mode:
                return None
        else:
            definition = basis.owner.definition
            readiness = basis.aggregate_grouped_clause_readiness
            outputs = basis.aggregate_result_facts
        if not isinstance(definition, (TableDef, QueryDef)):
            return None
        if readiness is None or readiness.definition is not definition:
            return None
        dependencies = tuple(
            fact
            for fact in readiness.dependency_facts
            if fact.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT
        )
        items = tuple(fact.source_occurrence for fact in dependencies)
        keys = (
            dependencies
            if isinstance(basis, ProjectConcreteNoJoinReplay)
            else basis.group_key_occurrences
        )
        selected = {}
        for i, fact in enumerate(dependencies):
            key = fact.target_occurrence
            if (
                not isinstance(key, (ProjectGroupKeyFact, ProjectComputedGroupKeyFact))
                or key.item is not items[i]
                or key.key_field is not fact.target_field
            ):
                return None
            for item, projected_key in readiness.finalization.group_projections:
                if (
                    projected_key.item is not key.item
                    or projected_key.key_field is not key.key_field
                ):
                    continue
                if id(item) in selected or not any(
                    item is authored for authored in definition.select_items
                ):
                    return None
                selected[id(item)] = i
    else:
        return None
    if not isinstance(definition, (TableDef, QueryDef)):
        return None
    clause = definition.group_by_clause
    if clause is None or not keys or len({id(item) for item in items}) != len(items):
        return None
    if len(items) != len(clause.items) or any(
        a is not b for a, b in zip(items, clause.items)
    ):
        return None
    if len(context.group_keys) != len(keys) or any(
        a is not b for a, b in zip(context.group_keys, keys)
    ):
        return None
    if len(context.aggregate_outputs) != len(outputs) or any(
        a is not b for a, b in zip(context.aggregate_outputs, outputs)
    ):
        return None
    covered = set()
    positions = []
    for position, row_field in enumerate(properties.output.row_shape.fields):
        if row_field.evidence.result_role is not ProjectRowResultRole.GROUP_KEY:
            continue
        if type(basis) is ProjectConcreteJoinedAggregation:
            if (
                type(row_field) is not ProjectIRQueryBlockRowField
                or id(row_field.semantic_source) not in selected
            ):
                return None
            index = selected[id(row_field.semantic_source)]
        elif type(basis) is ProjectConcreteNoJoinReplay:
            if (
                type(row_field) is not ProjectIRQueryBlockRowField
                or type(row_field.semantic_source) is not ProjectNoJoinGroupedOutput
            ):
                return None
            source = row_field.semantic_source
            if (
                source.readiness is not readiness
                or id(source.select_fact.item) not in selected
            ):
                return None
            index = selected[id(source.select_fact.item)]
        else:
            assert isinstance(basis, ProjectModuleRelationSemanticFacts)
            selections = [
                fact for fact in basis.select_facts if fact.field is row_field.evidence
            ]
            if len(selections) != 1 or id(selections[0].item) not in selected:
                return None
            index = selected[id(selections[0].item)]
        covered.add(index)
        positions.append(position)
    return tuple(positions) if len(covered) == len(keys) else ()


def _group_input_has_key(context, incoming, root) -> bool | None:
    """Use existing input classes and keys; no FD or grain inference."""
    basis = context.semantic_basis
    positions = []
    if isinstance(basis, ProjectConcreteJoinedAggregation):
        entries = root.find_owner(basis.input_filter.entry.owner)
        if len(entries) != 1 or not isinstance(
            entries[0], ProjectIRCompletedQueryBlockOutput
        ):
            return None
        prefix = entries[0].join_prefix
        for key in basis.group_keys:
            if type(key) is not ProjectJoinedGroupKeyOccurrence:
                # Independently: a computed determinant is never an input key.
                continue
            if isinstance(incoming.output, ProjectIRQueryBlockRowOutput):
                matches = [
                    i
                    for i, item in enumerate(incoming.output.row_shape.fields)
                    if item.semantic_source is key.field_semantics
                ]
            elif prefix is not None:
                if incoming.output is not prefix.final_join.output:
                    return None
                matches = [
                    i
                    for i, item in enumerate(
                        prefix.final_join.source.output.row_shape.fields
                    )
                    if item is key.field_semantics.joined_field
                ]
            else:
                matches = [
                    i
                    for i, item in enumerate(incoming.output.row_shape.fields)
                    if item is key.field_semantics.joined_field
                ]
            if len(matches) != 1:
                return None
            positions.append(matches[0])
    else:
        readiness = (
            basis.aggregate_readiness
            if isinstance(basis, ProjectConcreteNoJoinReplay)
            else basis.aggregate_grouped_clause_readiness
        )
        if readiness is None:
            return None
        for fact in readiness.dependency_facts:
            if fact.kind is not ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT:
                continue
            if type(fact.target_occurrence) is ProjectComputedGroupKeyFact:
                # Independently: a computed determinant is never an input key.
                if any(item.evidence is fact.target_field for item in incoming.fields):
                    return None
                continue
            matches = [
                item.field_position
                for item in incoming.fields
                if item.evidence is fact.target_field
            ]
            if len(matches) != 1:
                return None
            positions.append(matches[0])
    classes = tuple(
        value
        for value in incoming.value_classes
        if any(member.field_position in positions for member in value.members)
    )
    return any(
        key.strength is ProjectRowUniquenessStrength.STRICT
        and all(
            any(determinant is value for value in classes)
            for determinant in key.determinants
        )
        for key in incoming.keys
    )


def _group_properties_valid(
    properties: ProjectIROutputRelationalProperties,
    context: object,
    incoming: ProjectIROutputRelationalProperties,
    root: ProjectIRQueryBlockSnapshot,
) -> bool:
    if type(context) is not ProjectIRQueryBlockAggregateEvaluationContext:
        return False
    basis = context.semantic_basis
    if context.mode is ProjectJoinedAggregationMode.GLOBAL:
        if isinstance(basis, ProjectConcreteJoinedAggregation):
            outputs = basis.stage_outputs
            if basis.mode is not ProjectJoinedAggregationMode.GLOBAL:
                return False
        elif isinstance(basis, ProjectConcreteNoJoinReplay):
            schema = basis.base_state.schema
            outputs = () if schema is None else tuple(schema.fields.values())
            if basis.mode is not ProjectJoinedAggregationMode.GLOBAL:
                return False
        elif isinstance(basis, ProjectModuleRelationSemanticFacts):
            definition = basis.owner.definition
            if (
                not isinstance(definition, (TableDef, QueryDef))
                or definition.group_by_clause is not None
            ):
                return False
            outputs = basis.aggregate_result_facts
        else:
            return False
        if (
            context.group_keys
            or not outputs
            or len(context.aggregate_outputs) != len(outputs)
            or any(a is not b for a, b in zip(context.aggregate_outputs, outputs))
        ):
            return False
    origin_matches = tuple(
        origin
        for origin in root.grain_origins.origins
        if isinstance(origin, ProjectIRQueryBlockGrainOrigin)
        and origin.context is context
    )
    if len(origin_matches) != 1:
        return False
    origin = origin_matches[0]
    if context.mode is ProjectJoinedAggregationMode.GROUPED:
        positions = _group_key_positions(properties, context)
        if positions is None:
            return False
        key = ((positions, ProjectRowUniquenessStrength.STRICT),) if positions else ()
        expected_fds = (
            (
                positions,
                tuple(
                    position
                    for position in range(len(properties.value_classes))
                    if position not in positions
                ),
                ProjectRowUniquenessStrength.STRICT,
            ),
        )
        expected_fds = (
            tuple(item for item in expected_fds if item[1]) if positions else ()
        )
        input_has_key = _group_input_has_key(context, incoming, root)
        if input_has_key is None:
            return False
        factor = origin.factor
        if type(factor) is not ProjectGroupedGrainFactorIdentity:
            return False
        dependencies = properties.grain.dependencies
        prefix = incoming.grain.dependencies
        if len(dependencies) != len(prefix) + int(bool(incoming.grain.active)) * (
            1 + int(input_has_key)
        ) or any(
            actual is not expected for actual, expected in zip(dependencies, prefix)
        ):
            return False
        tail = dependencies[len(prefix) :]
        expected_edges: list[
            tuple[
                tuple[ProjectGrainFactorIdentity, ...],
                tuple[ProjectGrainFactorIdentity, ...],
            ]
        ] = [(incoming.grain.active, (factor,))] if incoming.grain.active else []
        if incoming.grain.active and input_has_key:
            expected_edges.append(((factor,), incoming.grain.active))
        if any(
            len(edge.determinants) != len(left)
            or len(edge.dependents) != len(right)
            or any(a is not b for a, b in zip(edge.determinants, left))
            or any(a is not b for a, b in zip(edge.dependents, right))
            for edge, (left, right) in zip(tail, expected_edges, strict=True)
        ):
            return False
        factors = properties.grain.factors
        if (
            len(factors) != len(incoming.grain.factors) + 1
            or any(a is not b for a, b in zip(factors, incoming.grain.factors))
            or factors[len(incoming.grain.factors)].identity is not factor
        ):
            return False
        grain_valid = (
            origin.kind is ProjectGrainOriginKind.GROUPED_RESULT
            and type(factor) is ProjectGroupedGrainFactorIdentity
            and properties.grain.state is ProjectGrainBasisState.FACTORIZED
            and properties.grain.active == (factor,)
            and all(
                item not in properties.grain.active for item in incoming.grain.active
            )
            and (
                not incoming.grain.active
                or any(
                    dependency.determinants == incoming.grain.active
                    and dependency.dependents == (factor,)
                    for dependency in properties.grain.dependencies
                )
            )
        )
        return (
            _actual_key_signatures(properties) == key
            and _actual_fd_signatures(properties) == expected_fds
            and grain_valid
        )
    return (
        context.mode is ProjectJoinedAggregationMode.GLOBAL
        and origin.kind is ProjectGrainOriginKind.GLOBAL_AGGREGATE
        and origin.factor is None
        and properties.grain.state is ProjectGrainBasisState.GLOBAL
        and not properties.grain.active
        and not properties.keys
        and not properties.fds
    )


def _entry_property_inputs(
    entry: ProjectIRCompletedQueryBlockOutput | ProjectIRReboundExistingOutput,
) -> tuple[
    tuple[_VerifiedOperator, ...],
    tuple[ProjectIRQueryBlockResultProperties, ...],
    ProjectIROutputRelationalProperties,
]:
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return entry.operators, entry.row_properties, entry.source_properties
    if type(entry) is ProjectIRReboundExistingOutput:
        return (
            entry.rebuilt_fragment.logical_stage.operators,
            entry.row_properties,
            entry.relation_input.producer.relational,
        )
    raise TypeError("Property verification requires one closed concrete entry.")


def _operator_context(
    entry: ProjectIRCompletedQueryBlockOutput | ProjectIRReboundExistingOutput,
    operator: _VerifiedOperator,
) -> ProjectIRQueryBlockAggregateEvaluationContext | None:
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        contexts = entry.aggregate_contexts
    elif type(entry) is ProjectIRReboundExistingOutput:
        contexts = entry.aggregate_contexts
    else:
        return None
    matches = tuple(context for context in contexts if context.operator is operator)
    return matches[0] if len(matches) == 1 else None


def _expected_class_signatures(
    *,
    entry: ProjectIRCompletedQueryBlockOutput | ProjectIRReboundExistingOutput,
    kind: ProjectIRLogicalOperatorKind | ProjectIRQueryBlockOperatorExtensionKind,
    incoming: ProjectIROutputRelationalProperties,
    output: ProjectIROutputRelationalProperties,
) -> tuple[tuple[int, ...], ...]:
    if kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
        signatures = tuple((position,) for position in range(len(output.fields)))
    elif kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
        if type(entry) is ProjectIRCompletedQueryBlockOutput:
            signatures = _query_projection_class_signatures(entry, incoming)
        elif type(entry) is ProjectIRReboundExistingOutput:
            signatures = _historical_projection_class_signatures(entry, incoming)
        else:
            raise TypeError("Projection verification requires one closed entry.")
    else:
        signatures = _preserved_class_signatures(incoming, len(output.fields))
    nested = _nested_positions(output)
    return tuple(
        members
        for members in (
            tuple(position for position in signature if position not in nested)
            for signature in signatures
        )
        if members
    )


def _properties_are_imaged(
    *,
    entry: ProjectIRCompletedQueryBlockOutput | ProjectIRReboundExistingOutput,
    kind: ProjectIRLogicalOperatorKind | ProjectIRQueryBlockOperatorExtensionKind,
    incoming: ProjectIROutputRelationalProperties,
    output: ProjectIROutputRelationalProperties,
) -> bool:
    images = _mapped_class_signatures(
        kind=kind,
        owner_entry=entry,
        incoming=incoming,
        output_count=len(output.fields),
    )
    expected_keys, expected_fds = _expected_imaged_key_fd_signatures(
        incoming=incoming,
        output=output,
        images=images,
    )
    grain_valid = (
        output.grain.state is incoming.grain.state
        and output.grain.factors == incoming.grain.factors
        and output.grain.active == incoming.grain.active
        and output.grain.dependencies == incoming.grain.dependencies
    )
    if kind is ProjectIRQueryBlockOperatorExtensionKind.DISTINCT:
        if not isinstance(entry, ProjectIRCompletedQueryBlockOutput):
            return False
        distinct = entry.semantic_entry.row_domain.distinct
        if distinct is None:
            return False
        factor = distinct.origin.factor
        comparison = output.grain.witness
        grain_valid = (
            isinstance(comparison, ProjectIRDistinctComparison)
            and comparison.semantic is distinct
            and comparison.input_output is incoming.output
            and not output.grain.dependencies
            and output.grain.state
            is (
                ProjectGrainBasisState.GLOBAL
                if factor is None
                else ProjectGrainBasisState.FACTORIZED
            )
            and _same_objects(output.grain.active, () if factor is None else (factor,))
            and _same_objects(
                tuple(f.identity for f in output.grain.factors),
                () if factor is None else (factor,),
            )
        )
    return (
        _actual_key_signatures(output) == expected_keys
        and _actual_fd_signatures(output) == expected_fds
        and grain_valid
    )


def _verify_properties(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    for ledger_entry in root.entries:
        if type(ledger_entry) not in {
            ProjectIRCompletedQueryBlockOutput,
            ProjectIRReboundExistingOutput,
        }:
            continue
        entry = cast(
            ProjectIRCompletedQueryBlockOutput | ProjectIRReboundExistingOutput,
            ledger_entry,
        )
        operators, property_rows, current = _entry_property_inputs(entry)
        expected_ordering = None
        expected_cardinality = None
        for operator, result in zip(operators, property_rows, strict=True):
            output = result.relational
            kind = operator.kind
            if (
                result.multiplicity is not ProjectJoinedRowMultiplicity.BAG
                or not _property_shape_valid(output)
                or not _fd_index_valid(output)
                or output.grain.origin_set is not root.grain_origins
            ):
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.PROPERTIES,
                    output.output.occurrence,
                )
                return
            class_signatures = _expected_class_signatures(
                entry=entry,
                kind=kind,
                incoming=current,
                output=output,
            )
            if _class_signatures(output) != class_signatures:
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.PROPERTIES,
                    output.output.occurrence,
                )
                return
            if kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
                context = _operator_context(entry, operator)
                if context is None or not _group_properties_valid(
                    output,
                    context,
                    current,
                    root,
                ):
                    _record(
                        issues,
                        ProjectIRQueryBlockVerificationIssueKind.PROPERTIES,
                        output.output.occurrence,
                    )
                    return
            elif not _properties_are_imaged(
                entry=entry,
                kind=kind,
                incoming=current,
                output=output,
            ):
                _record(
                    issues,
                    ProjectIRQueryBlockVerificationIssueKind.PROPERTIES,
                    output.output.occurrence,
                )
                return
            if type(entry) is ProjectIRCompletedQueryBlockOutput:
                if kind is ProjectIRLogicalOperatorKind.RELATION_ORDERING:
                    expected_ordering = entry.semantic_entry.ordering
                if kind is ProjectIRLogicalOperatorKind.LIMIT:
                    expected_cardinality = entry.semantic_entry.limit
                effect = result.effect
                if (
                    result.ordering is not expected_ordering
                    or result.cardinality is not expected_cardinality
                    or type(effect) is not ProjectIRQueryBlockEffectEvidence
                    or effect.determinism is not ProjectIRDeterminismEvidence.UNKNOWN
                    or effect.error_behavior
                    is not ProjectIRErrorBehaviorEvidence.UNKNOWN
                    or effect.side_effects is not ProjectIRSideEffectEvidence.UNKNOWN
                    or effect.evaluation_count
                    is not ProjectIREvaluationCountEvidence.UNKNOWN
                ):
                    _record(
                        issues,
                        ProjectIRQueryBlockVerificationIssueKind.PROPERTIES,
                        output.output.occurrence,
                    )
                    return
            current = output
        if type(entry) is ProjectIRCompletedQueryBlockOutput and (
            entry.active_properties.ordering is not entry.semantic_entry.ordering
            or entry.active_properties.cardinality is not entry.semantic_entry.limit
        ):
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.PROPERTIES,
                entry.active_output.occurrence,
            )
            return


def _verify_grain_origins(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    contexts: list[ProjectIRQueryBlockAggregateEvaluationContext] = []
    for owner in root.schedule:
        entry = _entry_for_owner(root, owner)
        if type(entry) is ProjectIRCompletedQueryBlockOutput:
            contexts.extend(entry.aggregate_contexts)
        elif type(entry) is ProjectIRReboundExistingOutput:
            contexts.extend(entry.aggregate_contexts)
    origins = tuple(
        origin
        for origin in root.grain_origins.origins
        if isinstance(origin, ProjectIRQueryBlockGrainOrigin)
    )
    domain_origins = tuple(
        origin
        for origin in root.grain_origins.origins
        if isinstance(origin, ProjectIRQueryBlockRowDomainOrigin)
    )
    expected_domains = tuple(
        operator
        for owner in root.schedule
        for entry in root.find_owner(owner)
        for operator in (
            (entry.operator,)
            if isinstance(entry, ProjectIRCompletedSetOperationOutput)
            else entry.operators
            if isinstance(entry, ProjectIRCompletedQueryBlockOutput)
            else ()
        )
        if isinstance(
            operator.evidence, (ProjectIRDistinctComparison, ProjectCompletedSetOutput)
        )
    )
    valid = (
        len(root.grain_origins.origins) == len(origins) + len(domain_origins)
        and len(domain_origins) == len(expected_domains)
        and all(
            origin.occurrence is operator
            and origin.origin
            is (
                operator.evidence.semantic.origin
                if isinstance(operator.evidence, ProjectIRDistinctComparison)
                else operator.evidence.row_domain.set_origin
                if isinstance(operator.evidence, ProjectCompletedSetOutput)
                else None
            )
            for origin, operator in zip(domain_origins, expected_domains, strict=True)
        )
        and tuple(origin.operator.ref.position for origin in root.grain_origins.origins)
        == tuple(
            sorted(
                origin.operator.ref.position for origin in root.grain_origins.origins
            )
        )
        and root.grain_origins.base
        is root.completed.verification.root.base_relational.origins
        and len(origins) == len(contexts)
        and all(
            origin.context is context
            and origin.operator.ref.position == context.operator.node.ref.position
            and (
                (
                    context.mode is ProjectJoinedAggregationMode.GROUPED
                    and origin.kind is ProjectGrainOriginKind.GROUPED_RESULT
                    and type(origin.factor) is ProjectGroupedGrainFactorIdentity
                    and origin.factor.context is context
                )
                or (
                    context.mode is ProjectJoinedAggregationMode.GLOBAL
                    and origin.kind is ProjectGrainOriginKind.GLOBAL_AGGREGATE
                    and origin.factor is None
                )
            )
            for origin, context in zip(origins, contexts, strict=True)
        )
        and tuple(origin.operator.ref.position for origin in origins)
        == tuple(sorted(origin.operator.ref.position for origin in origins))
    )
    if not valid:
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.GRAIN_ORIGIN)


def _current_factor_set_valid(value, index, factors) -> bool:
    return (
        type(value) is grain.ProjectGrainFactorSet
        and value.universe is index.universe
        and _same_objects(value.factors, factors)
        and value.mask == multifact._factor_set(index, factors).mask
    )


def _current_determination_valid(value, index, seed, requested) -> bool:
    if not (
        type(value) is multifact.ProjectFactGrainDetermination
        and value.index is index
        and _current_factor_set_valid(value.seed, index, seed)
        and _current_factor_set_valid(value.requested, index, requested)
    ):
        return False
    expected = grain.grain_dependency_closure(index, value.seed)
    return _current_factor_set_valid(value.closure, index, expected.factors) and (
        value.status
        is (
            multifact.ProjectFactGrainDirectionStatus.PROVEN
            if value.requested.mask & expected.mask == value.requested.mask
            else multifact.ProjectFactGrainDirectionStatus.NOT_PROVEN
        )
    )


def _current_comparison_valid(value, index, left, right) -> bool:
    return (
        type(value) is multifact.ProjectFactGrainComparison
        and value.left is left
        and value.right is right
        and value.index is index
        and _current_determination_valid(
            value.left_to_right, index, left.factors, right.factors
        )
        and _current_determination_valid(
            value.right_to_left, index, right.factors, left.factors
        )
        and _comparison_valid(value)
    )


def _check_current_candidates(region) -> None:
    final = region.region.final_properties
    basis, index = final.relational.grain, region.grain_index
    # Reject cyclic forged factor ancestry before the localization law walks it.
    for factor in basis.active:
        seen = set()
        while type(factor) is ProjectJoinGrainFactorIdentity:
            if id(factor) in seen:
                raise ValueError("Current grain factor ancestry is cyclic.")
            seen.add(id(factor))
            factor = factor.source_factor
    expected_index = grain._compile_grain_dependency_index(
        index.universe, basis.dependencies
    )
    if not (
        type(region) is multifact.ProjectCurrentMultiFactRegion
        and type(index) is grain.ProjectGrainDependencyIndex
        and region.final_properties is final
        and _same_objects(index.universe.factors, basis.factors)
        and _same_objects(index.facts, basis.dependencies)
        and dict(index.positions) == dict(expected_index.positions)
        and len(index.rules) == len(expected_index.rules)
        and all(
            actual.fact is expected.fact
            and actual.lhs_mask == expected.lhs_mask
            and actual.rhs_mask == expected.rhs_mask
            for actual, expected in zip(index.rules, expected_index.rules, strict=True)
        )
        and index.incidents == expected_index.incidents
    ):
        raise ValueError("Current grain index lost its exact final authority.")
    grounds = {}
    for kind, evidence, factors, allow_empty in multifact.current_candidate_grounds(
        region.region
    ):
        if factors or allow_empty:
            ordered = multifact._factor_set(index, factors).factors
            grounds.setdefault(ordered, []).append((kind, evidence))
    if type(region.actual_candidates) is not tuple or len(
        region.actual_candidates
    ) != len(grounds):
        raise ValueError("Current candidates must retain every factor bucket.")
    for candidate, (factors, authorities) in zip(
        region.actual_candidates, grounds.items(), strict=True
    ):
        if not (
            type(candidate) is multifact.ProjectActualGrainCandidate
            and _current_factor_set_valid(candidate.factors, index, factors)
            and len(candidate.authorities) == len(authorities)
            and all(
                type(actual) is multifact.ProjectActualGrainAuthority
                and actual.kind is kind
                and _same_objects(actual.evidence, evidence)
                for actual, (kind, evidence) in zip(
                    candidate.authorities, authorities, strict=True
                )
            )
        ):
            raise ValueError("Current candidates lost ordered input/output grounds.")


def _check_current_common(pair, region) -> None:
    index, actual = region.grain_index, region.actual_candidates
    result = pair.common_grain
    left, right = pair.left.contextual_grain, pair.right.contextual_grain
    determinations = multifact._candidate_determinations(
        index=index, grains=(left, right), candidates=actual
    )
    positions = tuple(
        position
        for position, candidate in enumerate(actual)
        if all(
            item.status is multifact.ProjectFactGrainDirectionStatus.PROVEN
            for item in determinations[candidate]
        )
    )
    masks = multifact._candidate_dominator_masks(index, actual)
    common_mask = sum(1 << position for position in positions)
    if not (
        type(result) is multifact.ProjectCommonGrainResult
        and _same_objects(result.actual_candidates, actual)
        and len(result.common_candidates) == len(positions)
    ):
        raise ValueError("Common grain must retain the complete actual candidates.")
    for evidence, position in zip(result.common_candidates, positions, strict=True):
        candidate = actual[position]
        if not (
            type(evidence) is multifact.ProjectCommonGrainCandidateEvidence
            and evidence.candidate is candidate
            and evidence.left_to_candidate.requested is candidate.factors
            and evidence.right_to_candidate.requested is candidate.factors
            and _current_determination_valid(
                evidence.left_to_candidate,
                index,
                left.factors,
                candidate.factors.factors,
            )
            and _current_determination_valid(
                evidence.right_to_candidate,
                index,
                right.factors,
                candidate.factors.factors,
            )
        ):
            raise ValueError("Common grain must retain exact candidate determinations.")
    retained = tuple(
        evidence
        for evidence, position in zip(result.common_candidates, positions, strict=True)
        if not masks[position] & common_mask
    )
    expected_status = (
        multifact.ProjectCommonGrainStatus.NONE
        if not retained
        else multifact.ProjectCommonGrainStatus.UNIQUE
        if len(retained) == 1
        else multifact.ProjectCommonGrainStatus.AMBIGUOUS
    )
    if (
        not _same_objects(result.candidates, retained)
        or result.status is not expected_status
    ):
        raise ValueError("Common grain cannot omit candidates or select a winner.")


def _check_current_join_properties(region) -> None:
    if not region.joins or region.final_properties is not region.join_properties[-1]:
        raise ValueError("Current region lost its final JOIN properties.")
    previous = None
    for join, properties in zip(region.joins, region.join_properties, strict=True):
        if (
            type(properties) is not ProjectCurrentJoinProperties
            or properties.join is not join
            or properties.relational.output is not join.output
            or previous is not None
            and join.left_input is not previous.relational
            or join.properties is not properties
            or not _property_shape_valid(properties.relational)
            or not _fd_index_valid(properties.relational)
        ):
            raise ValueError(
                "Current JOIN properties require exact input/output roots."
            )
        fields = join.output.row_shape.fields
        left_only = join.kind in {AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI}
        inputs = (
            join.left_input.fields
            if left_only
            else (*join.left_input.fields, *join.right_input.fields)
        )
        if len(fields) != len(inputs):
            raise ValueError("Current JOIN must retain every surviving row occurrence.")
        if type(join) is not ProjectCurrentBinaryJoin:
            raise ValueError("Current region requires an exact binary JOIN variant.")
        rejected = {
            (id(proof.field.binding), id(proof.field.input_field))
            for proof in join.condition.null_rejections
        }
        for position, (retained, incoming) in enumerate(
            zip(fields, inputs, strict=True)
        ):
            is_right = position >= len(join.left_input.fields)
            nullability = incoming.effective_nullability
            if not is_right and type(join.left_input.output) is ProjectIRJoinRowOutput:
                previous_field = join.left_input.output.row_shape.fields[position]
                introduction, nulling_refs = (
                    previous_field.introduction_use,
                    previous_field.nulling_joins,
                )
                nullability = previous_field.effective_nullability
            else:
                introduction, nulling_refs = join.input_uses[1 if is_right else 0], ()
            null_extended = join.kind in (
                {AuthoredJoinKind.LEFT, AuthoredJoinKind.FULL}
                if is_right
                else {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}
            )
            if null_extended:
                nulling_refs = (*nulling_refs, join.node.ref)
            binding, original = join.field_inputs[position]
            nullability = resolved_join_field_nullability(
                join.kind,
                incoming.effective_nullability,
                bool(nulling_refs),
                (id(binding), id(original)) in rejected,
            )
            if (
                retained.field_position != position
                or retained.evidence is not incoming.evidence
                or retained.introduction_use is not introduction
                or not _same_objects(retained.nulling_joins, nulling_refs)
                or retained.effective_nullability is not nullability
            ):
                raise ValueError(
                    "JOIN field must retain its exact input and NULL proof."
                )
        nulling = properties.null_extension
        if any(field.nulling_joins for field in fields):
            valid_null = (
                type(nulling) is ProjectIRProvidedNullExtension
                and nulling.output is join.output
                and _same_objects(nulling.fields, fields)
            )
        else:
            valid_null = (
                type(nulling) is ProjectIRJoinUnavailableProperty
                and nulling.output is join.output
                and nulling.property_slot
                is ProjectIRProvidedPropertySlot.NULL_EXTENSION
                and nulling.availability is ProjectIRPropertyAvailability.NOT_APPLICABLE
            )
        if not valid_null or not (
            type(properties.ordering) is ProjectIRJoinUnavailableProperty
            and properties.ordering.output is join.output
            and properties.ordering.property_slot
            is ProjectIRProvidedPropertySlot.RELATION_RESULT_ORDERING
            and properties.ordering.availability
            is ProjectIRPropertyAvailability.UNKNOWN
        ):
            raise ValueError(
                "Current JOIN NULL/order properties cannot borrow an output."
            )
        previous = properties


def _check_current_readiness(readiness, region) -> None:
    bridge = readiness.property_bridge
    if not (
        bridge.row_source is readiness.namespaces.binding_environment.row_source
        and bridge.multifact_region.region is region
        and bridge.properties is region.final_properties
        and len(readiness.fields) == len(bridge.relational.fields)
        and _same_objects(
            tuple(member.scalar_field for member in readiness.fields),
            readiness.namespaces.binding_environment.scalar_environment.fields,
        )
    ):
        raise ValueError("Current readiness lost its exact JOIN property bridge.")
    uses = tuple(
        (use, properties)
        for join in region.joins
        for use, properties in zip(
            join.input_uses, (join.left_input, join.right_input), strict=True
        )
    )
    for member, joined, property_field in zip(
        readiness.fields,
        region.joins[-1].output.row_shape.fields,
        bridge.relational.fields,
        strict=True,
    ):
        if not (
            type(member) is ProjectJoinedRowFieldSemantics
            and member.joined_field is joined
            and member.property_field is property_field
            and member.scalar_field.source_field is joined
            and property_field.effective_nullability is joined.effective_nullability
            and member.scalar_field.value_type
            == project_row_field_to_semantic_value_type(
                joined.evidence, joined.effective_nullability
            )
            and member.input_field.output is member.input_properties.output
            and member.input_field.evidence is joined.evidence
            and any(
                member.input_field is item for item in member.input_properties.fields
            )
            and any(
                joined.introduction_use is use and member.input_properties is properties
                for use, properties in uses
            )
        ):
            raise ValueError("Current field lost its exact input introduction.")
    _check_current_candidates(bridge.multifact_region)


def _check_current_protections(result, keys, region) -> None:
    group_issue = type(
        result
    ) is joined_aggregation.ProjectNonConcreteJoinedAggregation and any(
        type(key) is joined_aggregation.ProjectJoinedGroupKeyIssue
        for key in result.group_key_results
    )
    members = (
        joined_aggregation._protection_members(keys)
        if result.mode is ProjectJoinedAggregationMode.GROUPED and not group_issue
        else ()
    )
    if len(result.group_protections) != len(members):
        raise ValueError("Current group protections must cover every input root.")
    for protection, (properties, introduction, direct, computed) in zip(
        result.group_protections, members, strict=True
    ):
        seed, strict_keys, determinations, factors = (
            joined_aggregation.resolved_group_protection(
                properties,
                introduction,
                region.final_properties.relational.grain,
                tuple(
                    joined_aggregation._value_class_for_input_field(
                        properties, key.field_semantics
                    )
                    for key in direct
                ),
            )
        )
        if not (
            type(protection) is joined_aggregation.ProjectJoinedGroupProtection
            and protection.input_filter is result.input_filter
            and protection.input_properties is properties
            and protection.introduction_use is introduction
            and _same_objects(protection.group_keys, direct)
            and _same_objects(protection.computed_keys, computed)
            and protection.seed.index is properties.fd_index
            and protection.seed == seed
            and _same_objects(protection.strict_keys, strict_keys)
            and len(protection.determinations) == len(determinations)
            and all(
                actual.seed is protection.seed
                and actual.requested.index is properties.fd_index
                and actual.requested == expected.requested
                and actual.closure == expected.closure
                and actual.status is expected.status
                for actual, expected in zip(
                    protection.determinations, determinations, strict=True
                )
            )
            and _same_objects(protection.protected_factors, factors)
        ):
            raise ValueError(
                "Current group protection lost its complete STRICT-key proof."
            )


def _current_orphan_dependencies(aggregate, keys, region):
    if not aggregate.call.arguments or not any(
        type(join) is ProjectCurrentBinaryJoin
        and join.kind in {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}
        for join in region.region.joins
    ):
        return ()
    input_filter = aggregate.input_filter
    groups = joined_aggregation._protection_members(
        tuple(key for key in keys if type(key) is ProjectJoinedGroupKeyOccurrence)
    )

    def grouped_holder(target):
        return any(
            use is target
            and joined_aggregation._grouped_nullable_key(
                properties,
                tuple(
                    joined_aggregation._value_class_for_input_field(
                        properties, key.field_semantics
                    )
                    for key in direct
                ),
                joined_aggregation._current_non_null_classes(
                    input_filter, properties, use
                ),
            )
            for properties, use, direct, _ in groups
        )

    return joined_aggregation.resolved_orphan_free_dependencies(
        region.final_properties.relational.grain,
        tuple(
            joined_aggregation._region_join(region.region, join)
            for join in region.region.joins
        ),
        joined_aggregation.current_unread(input_filter, aggregate.call.arguments[0]),
        grouped_holder,
        joined_aggregation.current_held(input_filter),
    )


def _check_current_aggregate_result(result, readiness) -> None:
    if type(result) not in {
        ProjectConcreteJoinedAggregation,
        joined_aggregation.ProjectNonConcreteJoinedAggregation,
    }:
        raise ValueError("Current aggregate requires an exact result variant.")
    terminal = type(result) is joined_aggregation.ProjectNonConcreteJoinedAggregation
    reasons = joined_aggregation.ProjectJoinedAggregationNonConcreteReason
    input_filter = result.input_filter
    if input_filter.joined_semantics is not readiness:
        raise ValueError("Current aggregate lost its retained row semantics.")
    if type(input_filter) is ProjectNonConcreteJoinedRowFilter:
        if (
            not terminal
            or result.reason is not reasons.UPSTREAM_FILTER_NON_CONCRETE
            or any(
                (
                    result.mode is not None,
                    result.group_key_results,
                    result.aggregate_results,
                    result.stage_outputs,
                    result.selected_output_issues,
                    result.group_protections,
                    result.grain_linkages,
                    result.pair_linkages,
                    result.grain_blocker is not None,
                    result.satisfying is not None,
                    result.diagnostics,
                )
            )
        ):
            raise ValueError(
                "Upstream filter terminal cannot publish partial aggregate proof."
            )
        return
    region = readiness.multifact_region
    basis, index = region.final_properties.relational.grain, region.grain_index
    definition = joined_aggregation._definition(input_filter)
    key_results = result.group_key_results if terminal else result.group_keys
    aggregate_results = result.aggregate_results if terminal else result.aggregates
    expected_keys = (
        () if definition.group_by_clause is None else definition.group_by_clause.items
    )
    expected_aggregates = tuple(
        (position, item)
        for position, item in enumerate(definition.select_items)
        if type(item.expression) is not WindowExpr
        and joined_aggregation.semantic_aggregates.contains_semantic_aggregate(
            item.expression
        )
    )
    if (
        result.mode is not joined_aggregation._mode(definition)
        or len(key_results) != len(expected_keys)
        or any(
            key.input_filter is not input_filter
            or key.item is not item
            or key.source_ordinal != position
            for position, (key, item) in enumerate(
                zip(key_results, expected_keys, strict=True)
            )
        )
        or len(aggregate_results) != len(expected_aggregates)
        or any(
            item.input_filter is not input_filter
            or item.item is not source
            or item.selected_output_ordinal != position
            for item, (position, source) in zip(
                aggregate_results, expected_aggregates, strict=True
            )
        )
    ):
        raise ValueError(
            "Current aggregate evidence must retain authored occurrence order."
        )
    keys = tuple(
        key
        for key in key_results
        if isinstance(key, joined_aggregation.ProjectJoinedAnyGroupKey)
    )
    aggregates = tuple(
        item
        for item in aggregate_results
        if type(item) is joined_aggregation.ProjectJoinedAggregateOccurrence
    )
    if (
        not _same_objects(input_filter.fields, readiness.fields)
        or input_filter.namespace is not readiness.post_let
    ):
        raise ValueError("Current filter must retain every exact input field.")
    for key in keys:
        resolutions, source_field, computed_key = (
            joined_aggregation._direct_field_resolution(
                input_filter, key.item.key, expand_let=True
            )
        )
        if len(key.resolutions) != len(resolutions) or any(
            type(actual) is not type(expected)
            or actual.reference.expression is not expected.reference.expression
            or actual.reference.environment is not expected.reference.environment
            or actual.target is not expected.target
            for actual, expected in zip(key.resolutions, resolutions, strict=True)
        ):
            raise ValueError(
                "Current group key lost its exact resolved reference path."
            )
        if type(key) is ProjectJoinedGroupKeyOccurrence:
            valid_key = (
                not computed_key
                and key.field_semantics is source_field
                and key.effective_expression is resolutions[-1].reference.expression
            )
        else:
            valid_key = (
                computed_key
                and type(key) is ProjectJoinedComputedGroupKeyOccurrence
                and len(resolutions) == 1
                and _same_objects(
                    key.field_dependencies,
                    joined_aggregation._let_field_dependencies(
                        input_filter, key.let_value
                    ),
                )
            )
        if not valid_key:
            raise ValueError("Current group key borrowed field semantics.")
    for aggregate in aggregates:
        if aggregate.call is not aggregate.item.expression:
            raise ValueError("Current aggregate lost its exact selected call.")
        analysis = aggregate.argument_analysis
        if aggregate.call.arguments:
            if (
                type(analysis) is not ProjectConcreteJoinedNamespaceExpression
                or analysis.expression is not aggregate.call.arguments[0]
                or analysis.namespace is not input_filter.namespace
            ):
                raise ValueError("Current aggregate lost its exact argument analysis.")
            dependencies = joined_aggregation._resolved_field_dependencies(
                input_filter=input_filter,
                namespace=input_filter.namespace,
                expression=analysis.normalized_expression,
                existence_values=analysis.existence_values,
            )
        else:
            if analysis is not None:
                raise ValueError(
                    "Zero-argument aggregate cannot retain argument analysis."
                )
            dependencies = ()
        if len(aggregate.field_dependencies) != len(dependencies) or any(
            dependency.input_filter is not input_filter
            or dependency.item is not aggregate.item
            or dependency.selected_output_ordinal != aggregate.selected_output_ordinal
            or dependency.reference is not dependency.resolution.reference
            or dependency.reference.expression is not reference.expression
            or dependency.reference.environment is not reference.environment
            or dependency.resolution.target is not resolution.target
            or not _same_objects(dependency.let_path, let_path)
            or dependency.field_semantics is not source_field
            for dependency, (reference, resolution, let_path, source_field) in zip(
                aggregate.field_dependencies, dependencies, strict=True
            )
        ):
            raise ValueError("Current aggregate must retain every ordered field read.")
    _check_current_protections(result, keys, region)
    link_aggregates = (
        () if basis.state is ProjectGrainBasisState.UNKNOWN else aggregates
    )
    if not _same_objects(
        tuple(link.aggregate for link in result.grain_linkages), link_aggregates
    ):
        raise ValueError(
            "Current aggregate grain links must cover every retained aggregate."
        )
    protected = joined_aggregation._ordered_factors(
        basis.active,
        tuple(
            factor
            for protection in result.group_protections
            for factor in protection.protected_factors
        ),
    )
    computed = (
        joined_aggregation.computed_key_factors(
            basis,
            tuple(
                (read.input_properties.grain, read.introduction_use)
                for key in keys
                if type(key) is ProjectJoinedComputedGroupKeyOccurrence
                for read in key.field_dependencies
            ),
        )
        if result.grain_linkages
        else ()
    )
    for link in result.grain_linkages:
        aggregate = link.aggregate
        arguments = joined_aggregation.resolved_argument_factors(
            basis,
            bool(aggregate.call.arguments),
            tuple(
                (
                    dependency.field_semantics.input_properties.grain,
                    dependency.field_semantics.introduction_use,
                )
                for dependency in aggregate.field_dependencies
            ),
        )
        combined = joined_aggregation._ordered_factors(
            basis.active, (*arguments, *protected)
        )
        if not (
            type(link) is joined_aggregation.ProjectJoinedAggregateGrainLinkage
            and link.multifact_region is region
            and link.final_grain is basis
            and _same_objects(link.argument_factors, arguments)
            and _same_objects(link.group_protection_factors, protected)
            and _same_objects(link.computed_key_factors, computed)
            and _current_factor_set_valid(link.combined_seed, index, combined)
        ):
            raise ValueError(
                "Current aggregate grain link lost its exact roots or seed."
            )
        closure = grain.grain_dependency_closure(
            joined_aggregation.aggregate_grain_index(
                index, _current_orphan_dependencies(aggregate, keys, region)
            ),
            link.combined_seed,
        )
        context, full = link.contextual_grain, link.final_comparison.right
        if not (
            _current_factor_set_valid(link.closure, index, closure.factors)
            and type(context) is multifact.ProjectFactContextualGrain
            and type(full) is multifact.ProjectFactContextualGrain
            and context.authority is basis
            and context.evidence is aggregate
            and context.state
            is (
                ProjectGrainBasisState.FACTORIZED
                if closure.factors
                else ProjectGrainBasisState.GLOBAL
            )
            and _same_objects(context.factors, closure.factors)
            and full.authority is basis
            and full.evidence is region.final_properties
            and full.state is basis.state
            and _same_objects(full.factors, basis.active)
            and _current_comparison_valid(link.final_comparison, index, context, full)
        ):
            raise ValueError(
                "Current aggregate contextual grain lost its closure proof."
            )
        exposures = joined_aggregation.resolved_multiplicity_exposures(
            link.final_comparison,
            tuple(
                (join, tuple(use.ref for use in join.input_uses))
                for join in region.region.joins
            ),
        )
        if (
            len(link.multiplicity_exposures) != len(exposures)
            or any(
                type(exposure) is not multifact.ProjectCurrentMultiplicityExposure
                or exposure.join is not join
                or not _same_objects(exposure.factor_additions, factors)
                for exposure, (join, factors) in zip(
                    link.multiplicity_exposures, exposures, strict=True
                )
            )
            or link.multiplicity_risks
            != (
                (multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,)
                if exposures
                else ()
            )
            or link.requirements
            != (
                (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
                if exposures
                else ()
            )
        ):
            raise ValueError(
                "Current aggregate fanout must retain every exact exposure."
            )
    pairs = tuple(
        (left, right)
        for position, left in enumerate(result.grain_linkages)
        for right in result.grain_linkages[position + 1 :]
    )
    if len(result.pair_linkages) != len(pairs):
        raise ValueError("Current aggregate pairs must retain every ordered pair.")
    for pair, (left, right) in zip(result.pair_linkages, pairs, strict=True):
        if not (
            type(pair) is joined_aggregation.ProjectJoinedAggregatePairLinkage
            and pair.left is left
            and pair.right is right
            and _current_comparison_valid(
                pair.grain_comparison,
                index,
                left.contextual_grain,
                right.contextual_grain,
            )
        ):
            raise ValueError("Current aggregate pair lost its exact participants.")
        _check_current_common(pair, region)
        structural, finer, chasms = joined_aggregation.resolved_pair_shape(
            left.contextual_grain,
            right.contextual_grain,
            pair.grain_comparison,
            pair.common_grain,
        )
        risks = (
            *(
                (multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,)
                if left.multiplicity_exposures or right.multiplicity_exposures
                else ()
            ),
            *(
                (multifact.ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION,)
                if chasms
                else ()
            ),
        )
        required = (
            structural
            is multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
            or bool(risks)
        )
        if not (
            pair.structural is structural
            and pair.finer is (None if finer is None else (left, right)[finer])
            and _same_objects(pair.chasm_candidates, chasms)
            and pair.multiplicity_risks == risks
            and pair.requirements
            == (
                (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
                if required
                else ()
            )
        ):
            raise ValueError(
                "Current aggregate pair cannot omit risks or choose candidates."
            )
    has_risk = any(
        link.requirements for link in (*result.grain_linkages, *result.pair_linkages)
    )
    if terminal:
        expected_reason = (
            reasons.GROUP_KEY_NON_CONCRETE
            if any(
                type(key) is joined_aggregation.ProjectJoinedGroupKeyIssue
                for key in key_results
            )
            else reasons.AGGREGATE_NON_CONCRETE
            if any(
                type(item) is joined_aggregation.ProjectJoinedAggregateIssue
                for item in aggregate_results
            )
            else reasons.SELECTED_OUTPUT_NON_CONCRETE
            if result.selected_output_issues
            else reasons.INTRINSIC_GRAIN_NON_CONCRETE
            if aggregates and basis.state is ProjectGrainBasisState.UNKNOWN
            else reasons.AGGREGATE_ALGEBRA_REQUIRED
            if has_risk
            else reasons.SATISFYING_NON_CONCRETE
            if result.satisfying is not None
            and result.satisfying.status
            is joined_aggregation.ProjectJoinedSatisfyingStatus.NON_CONCRETE
            else None
        )
        if result.reason is not expected_reason or result.grain_blocker is not (
            basis if expected_reason is reasons.INTRINSIC_GRAIN_NON_CONCRETE else None
        ):
            raise ValueError(
                "Current aggregate terminal lost its actual blocking proof."
            )
    elif has_risk:
        raise ValueError("Concrete aggregate cannot retain unresolved risk.")


def _verify_current_proofs(root, issues) -> None:
    """Check retained current proofs even when their owner allocates no IR."""
    overlay = root.completed.effective_outputs
    regions, readiness_values = overlay.current_regions, overlay.current_readiness
    if not (
        len(regions) == len(readiness_values)
        and _same_objects(
            tuple(region.ledger.owner for region in regions),
            tuple(
                owner
                for owner in overlay.schedule
                if any(region.ledger.owner is owner for region in regions)
            ),
        )
        and _same_objects(
            regions,
            tuple(
                event
                for event in overlay.allocation_events
                if type(event) is ProjectCurrentJoinRegion
            ),
        )
    ):
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE)
        return
    tails = iter(overlay.current_tails)
    for region, readiness in zip(regions, readiness_values, strict=True):
        tail = (
            next(tails, None)
            if type(readiness) is ProjectConcreteJoinedRowSemantics
            else None
        )
        try:
            owners = tuple(
                entry for entry in root.entries if entry.owner is region.ledger.owner
            )
            if (
                len(owners) != 1
                or region.conditions is not overlay.condition_authority
                or not _same_objects(
                    region.operative,
                    tuple(
                        condition
                        for condition in overlay.operative_conditions.entries
                        if condition.ledger is region.ledger
                    ),
                )
            ):
                raise ValueError(
                    "Current proofs require one exact retained owner and condition root."
                )
            ir_entry = owners[0]
            if type(
                ir_entry.semantic_entry
            ) is ProjectEffectiveOutputCompletionTerminal and not (
                type(ir_entry) is ProjectIRQueryBlockTerminal
                and ir_entry.reason
                is ProjectIRQueryBlockTerminalReason.SEMANTIC_OUTPUT_NON_CONCRETE
                and ir_entry.blocker is ir_entry.semantic_entry
                and ir_entry.ending_allocation is ir_entry.starting_allocation
            ):
                raise ValueError(
                    "Current semantic terminal must retain its exact zero-allocation blocker."
                )
            source = readiness.namespaces.binding_environment.row_source
            if (
                type(source) is not ProjectCurrentJoinedRowSource
                or source.region is not region
                or source.base_verification is not overlay.base.verification
            ):
                raise ValueError("Current readiness cannot borrow a region root.")
            _check_current_join_properties(region)
            if type(readiness) is not ProjectConcreteJoinedRowSemantics:
                semantic = owners[0].semantic_entry
                if not (
                    type(readiness) is ProjectNonConcreteJoinedRowSemantics
                    and type(semantic) is ProjectEffectiveOutputCompletionTerminal
                    and semantic.current_region is region
                    and semantic.joined_qualify is None
                    and semantic.reason
                    is ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_TAIL_NON_CONCRETE
                    and semantic.blocker is readiness
                ):
                    raise ValueError(
                        "Current readiness terminal lost its exact blocker."
                    )
                continue
            _check_current_readiness(readiness, region)
            if tail is None or len(tail.results) != 1:
                raise ValueError("Current owner must retain its exact local tail.")
            aggregation_set = tail.window_set.aggregation_set
            if not _same_objects(
                tuple(stage.input_aggregation for stage in tail.window_set.results),
                aggregation_set.results,
            ) or not _same_objects(
                tuple(result.window_stage for result in tail.results),
                tail.window_set.results,
            ):
                raise ValueError(
                    "Current tail must retain complete aggregate/window stage order."
                )
            filters = aggregation_set.filter_set
            if (
                filters.completion is not overlay.base
                or filters.current_semantics is not readiness
                or len(aggregation_set.results) != len(filters.results)
            ):
                raise ValueError("Current aggregate inventory lost its filter roots.")
            semantic = owners[0].semantic_entry
            if type(semantic) is ProjectEffectiveOutputCompletionTerminal:
                if semantic.current_region is not region:
                    raise ValueError("Current terminal lost its exact region.")
                qualifier = semantic.joined_qualify
                if type(qualifier) is ProjectNonConcreteJoinedQualify:
                    if (
                        semantic.reason
                        is not ProjectEffectiveOutputCompletionTerminalReason.JOINED_QUALIFY_NON_CONCRETE
                        or semantic.blocker is not qualifier
                    ):
                        raise ValueError(
                            "Current terminal must retain its exact QUALIFY blocker."
                        )
                elif type(
                    qualifier
                ) is not ProjectConcreteJoinedQualify or semantic.reason not in {
                    ProjectEffectiveOutputCompletionTerminalReason.DISTINCT_NON_CONCRETE,
                    ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE,
                    ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE,
                    ProjectEffectiveOutputCompletionTerminalReason.LIMIT_NON_CONCRETE,
                }:
                    raise ValueError(
                        "Current finalization terminal requires its concrete tail."
                    )
            elif type(semantic) is ProjectCompletedEffectiveOutput:
                qualifier = semantic.root
            else:
                raise ValueError("Current tail requires a completed or terminal owner.")
            if qualifier is not tail.results[0]:
                raise ValueError("Current owner lost its exact retained tail result.")
            for result, input_filter in zip(
                aggregation_set.results, filters.results, strict=True
            ):
                if (
                    result.filter_set is not filters
                    or result.input_filter is not input_filter
                    or input_filter.entry is not semantic.base_entry
                ):
                    raise ValueError(
                        "Current aggregate results must retain complete filter order."
                    )
                _check_current_aggregate_result(result, readiness)
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            _record(issues, ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE)
    if next(tails, None) is not None:
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE)


def verify_project_query_block_ir(
    root: ProjectIRQueryBlockSnapshot,
) -> ProjectIRQueryBlockVerificationResult:
    """Freshly verify one Slice-14 snapshot without invoking its constructor."""

    if type(root) is not ProjectIRQueryBlockSnapshot:
        raise TypeError("Query-block verification requires an exact snapshot.")
    issues: list[ProjectIRQueryBlockVerificationIssue] = []
    passes = (
        _verify_allocation,
        _verify_ledger,
        _verify_expression_block_uses,
        _verify_capture_uses,
        _verify_active_roots,
        _verify_historical_reuse,
        _verify_join_reuse,
        _verify_composed_joins,
        _verify_set_operations,
        _verify_values,
        _verify_single_match_retention,
        _verify_operator_sequence,
        _verify_semantic_evidence,
        _verify_current_proofs,
        _verify_structural_endpoints,
        _verify_row_shapes,
        _verify_properties,
        _verify_grain_origins,
    )
    coherent = _verify_root_continuity(root, issues)
    if coherent:
        for verification_pass in passes:
            try:
                verification_pass(root, issues)
            except (AttributeError, IndexError, KeyError, TypeError, ValueError):
                issue_kind = {
                    _verify_allocation: ProjectIRQueryBlockVerificationIssueKind.ALLOCATION,
                    _verify_ledger: ProjectIRQueryBlockVerificationIssueKind.LEDGER,
                    _verify_expression_block_uses: (
                        ProjectIRQueryBlockVerificationIssueKind.EXPRESSION_BLOCK_USE
                    ),
                    _verify_capture_uses: (
                        ProjectIRQueryBlockVerificationIssueKind.CAPTURE_USE
                    ),
                    _verify_active_roots: (
                        ProjectIRQueryBlockVerificationIssueKind.ACTIVE_ROOT
                    ),
                    _verify_historical_reuse: (
                        ProjectIRQueryBlockVerificationIssueKind.HISTORICAL_REUSE
                    ),
                    _verify_join_reuse: ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE,
                    _verify_composed_joins: ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE,
                    _verify_set_operations: ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                    _verify_values: ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                    _verify_single_match_retention: ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                    _verify_operator_sequence: (
                        ProjectIRQueryBlockVerificationIssueKind.OPERATOR_SEQUENCE
                    ),
                    _verify_semantic_evidence: (
                        ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE
                    ),
                    _verify_current_proofs: (
                        ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE
                    ),
                    _verify_structural_endpoints: (
                        ProjectIRQueryBlockVerificationIssueKind.STRUCTURAL_ENDPOINT
                    ),
                    _verify_row_shapes: ProjectIRQueryBlockVerificationIssueKind.ROW_SHAPE,
                    _verify_properties: ProjectIRQueryBlockVerificationIssueKind.PROPERTIES,
                    _verify_grain_origins: (
                        ProjectIRQueryBlockVerificationIssueKind.GRAIN_ORIGIN
                    ),
                }[verification_pass]
                _record(issues, issue_kind)
        if _combined_topology(root) is None:
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.COMBINED_ACTUAL_USE_CYCLE,
            )
    issue_tuple = tuple(issues)
    return ProjectIRQueryBlockVerificationResult(
        root=root,
        status=(
            ProjectIRQueryBlockVerificationStatus.VERIFIED
            if not issue_tuple
            else ProjectIRQueryBlockVerificationStatus.INVALID
        ),
        issues=issue_tuple,
    )


class ProjectIRQueryBlockAnalysisKind(StrEnum):
    COMBINED_REVERSE_USE_INDEX = "combined_reverse_use_index"
    COMBINED_TOPOLOGICAL_ORDER = "combined_topological_order"
    COMBINED_REACHABILITY = "combined_reachability"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockReverseUseEntry:
    output: ProjectIROutputValueOccurrence
    uses: tuple[ProjectIRQueryBlockCombinedUse, ...]

    def __post_init__(self) -> None:
        if (
            type(self.output) is not ProjectIROutputValueOccurrence
            or type(self.uses) is not tuple
        ):
            raise TypeError("Combined reverse-use entry requires exact occurrences.")
        if any(
            type(use)
            not in {
                ProjectIRUseOccurrence,
                ProjectIROperatorFlowUseOccurrence,
                ProjectIRJoinInputUseOccurrence,
                ProjectIRSetInputUseOccurrence,
            }
            or use.output is not self.output
            for use in self.uses
        ):
            raise ValueError("Combined reverse uses must retain exact direct uses.")


def _derive_reverse_uses(
    root: ProjectIRQueryBlockSnapshot,
) -> tuple[ProjectIRQueryBlockReverseUseEntry, ...]:
    _, outputs, uses = _combined_parts(root)
    return tuple(
        ProjectIRQueryBlockReverseUseEntry(
            output=output,
            uses=tuple(use for use in uses if use.output is output),
        )
        for output in outputs
    )


def _same_reverse_uses(
    actual: tuple[ProjectIRQueryBlockReverseUseEntry, ...],
    expected: tuple[ProjectIRQueryBlockReverseUseEntry, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.output is retained.output
        and _same_objects(
            cast(tuple[object, ...], item.uses),
            cast(tuple[object, ...], retained.uses),
        )
        for item, retained in zip(actual, expected, strict=True)
    )


def _same_reachability(
    actual: tuple[ProjectIRReachabilityEntry, ...],
    expected: tuple[ProjectIRReachabilityEntry, ...],
) -> bool:
    return len(actual) == len(expected) and all(
        item.source is retained.source
        and _same_objects(
            cast(tuple[object, ...], item.reachable),
            cast(tuple[object, ...], retained.reachable),
        )
        for item, retained in zip(actual, expected, strict=True)
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockAnalysisBundle:
    verification: ProjectIRQueryBlockVerificationResult
    combined_reverse_uses: tuple[ProjectIRQueryBlockReverseUseEntry, ...]
    combined_topological_order: tuple[ProjectIRPlanNodeOccurrence, ...]
    combined_reachability: tuple[ProjectIRReachabilityEntry, ...]

    def __post_init__(self) -> None:
        if type(self.verification) is not ProjectIRQueryBlockVerificationResult or (
            not self.verification.verified or self.verification.issues
        ):
            raise ValueError("Query-block analyses require one VERIFIED result.")
        topology = _combined_topology(self.verification.root)
        if topology is None:
            raise ValueError("Verified combined topology must remain acyclic.")
        _, _, _, _, expected_order, expected_reachability = topology
        if (
            not _same_reverse_uses(
                self.combined_reverse_uses,
                _derive_reverse_uses(self.verification.root),
            )
            or not _same_objects(
                cast(tuple[object, ...], self.combined_topological_order),
                cast(tuple[object, ...], expected_order),
            )
            or not _same_reachability(
                self.combined_reachability,
                expected_reachability,
            )
        ):
            raise ValueError("Query-block analyses must retain fresh graph products.")

    @property
    def root(self) -> ProjectIRQueryBlockSnapshot:
        return self.verification.root


def build_project_query_block_ir_analysis_bundle(
    verification: ProjectIRQueryBlockVerificationResult,
) -> ProjectIRQueryBlockAnalysisBundle:
    """Freshly derive all combined topology analyses from one VERIFIED root."""

    if type(verification) is not ProjectIRQueryBlockVerificationResult or (
        not verification.verified
    ):
        raise ValueError("Only VERIFIED query-block IR may produce analyses.")
    topology = _combined_topology(verification.root)
    if topology is None:
        raise ValueError("Verified query-block topology must remain acyclic.")
    _, _, _, _, order, reachability = topology
    return ProjectIRQueryBlockAnalysisBundle(
        verification=verification,
        combined_reverse_uses=_derive_reverse_uses(verification.root),
        combined_topological_order=order,
        combined_reachability=reachability,
    )


class ProjectIRQueryBlockOverlayRequirement(StrEnum):
    PRESERVED = "preserved"
    REBUILD_REQUIRED = "rebuild_required"


_OVERLAY_DOMAINS = frozenset(
    {
        ProjectIRChangeDomain.TOPOLOGY,
        ProjectIRChangeDomain.OPERATOR_SEMANTICS,
        ProjectIRChangeDomain.OUTPUT_SEMANTICS,
        ProjectIRChangeDomain.PROPERTIES,
        ProjectIRChangeDomain.EFFECTS,
        ProjectIRChangeDomain.EVALUATION_CONTEXT,
        ProjectIRChangeDomain.PROVENANCE,
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRQueryBlockAnalysisInvalidation:
    changed_domains: tuple[ProjectIRChangeDomain, ...]
    completed_semantic_root_changed: bool
    invalidated: tuple[ProjectIRQueryBlockAnalysisKind, ...]
    preserved: tuple[ProjectIRQueryBlockAnalysisKind, ...]
    overlay: ProjectIRQueryBlockOverlayRequirement
    verification: ProjectIRVerificationRequirement = field(
        init=False,
        default=ProjectIRVerificationRequirement.RERUN_REQUIRED,
    )

    def __post_init__(self) -> None:
        order = tuple(ProjectIRChangeDomain)
        if (
            type(self.changed_domains) is not tuple
            or any(
                type(item) is not ProjectIRChangeDomain for item in self.changed_domains
            )
            or len(set(self.changed_domains)) != len(self.changed_domains)
            or self.changed_domains
            != tuple(sorted(self.changed_domains, key=order.index))
            or type(self.completed_semantic_root_changed) is not bool
            or (not self.changed_domains and not self.completed_semantic_root_changed)
        ):
            raise ValueError(
                "Query-block invalidation requires explicit changed roots."
            )
        topology_changed = ProjectIRChangeDomain.TOPOLOGY in self.changed_domains
        expected_invalidated = (
            tuple(ProjectIRQueryBlockAnalysisKind)
            if self.completed_semantic_root_changed or topology_changed
            else ()
        )
        expected_preserved = tuple(
            item
            for item in ProjectIRQueryBlockAnalysisKind
            if item not in expected_invalidated
        )
        expected_overlay = (
            ProjectIRQueryBlockOverlayRequirement.REBUILD_REQUIRED
            if self.completed_semantic_root_changed
            or any(item in _OVERLAY_DOMAINS for item in self.changed_domains)
            else ProjectIRQueryBlockOverlayRequirement.PRESERVED
        )
        if (
            self.invalidated != expected_invalidated
            or self.preserved != expected_preserved
            or self.overlay is not expected_overlay
        ):
            raise ValueError("Query-block invalidation disagrees with dependencies.")


def assess_project_query_block_ir_invalidation(
    changed_domains: tuple[ProjectIRChangeDomain, ...],
    *,
    completed_semantic_root_changed: bool = False,
) -> ProjectIRQueryBlockAnalysisInvalidation:
    """Conservatively invalidate the overlay and detachable graph analyses."""

    topology_changed = ProjectIRChangeDomain.TOPOLOGY in changed_domains
    invalidated = (
        tuple(ProjectIRQueryBlockAnalysisKind)
        if completed_semantic_root_changed or topology_changed
        else ()
    )
    return ProjectIRQueryBlockAnalysisInvalidation(
        changed_domains=changed_domains,
        completed_semantic_root_changed=completed_semantic_root_changed,
        invalidated=invalidated,
        preserved=tuple(
            item for item in ProjectIRQueryBlockAnalysisKind if item not in invalidated
        ),
        overlay=(
            ProjectIRQueryBlockOverlayRequirement.REBUILD_REQUIRED
            if completed_semantic_root_changed
            or any(item in _OVERLAY_DOMAINS for item in changed_domains)
            else ProjectIRQueryBlockOverlayRequirement.PRESERVED
        ),
    )


# The image of a historical factor that two composed inputs image differently.
_NO_IMAGE = object()


def _verify_composed_joins(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    """Independently check semantic membership and every composed binary image."""
    prefixes = tuple(
        entry.join_prefix
        for entry in root.entries
        if isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        and entry.join_prefix is not None
    )
    image_pairs = tuple(pair for prefix in prefixes for pair in prefix.ref_images)
    ref_images = {id(source): target for source, target in image_pairs}
    use_images = {
        id(item.source): item.use
        for prefix in prefixes
        for join in prefix.joins
        for item in join.inputs
    }
    # Every joined tail reads a composed JOIN prefix: no authored JOIN joins
    # by itself, so no historical JOIN is retained.
    if any(
        isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        and entry.join_prefix is None
        and isinstance(entry.semantic_entry.root, ProjectConcreteJoinedQualify)
        for entry in root.entries
    ):
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE)
    historical_refs = tuple(
        item.ref
        for items in (
            root.base_plan.structural_stage.nodes,
            root.base_plan.structural_stage.uses,
        )
        for item in items
    )
    operative = root.completed.effective_outputs.operative_conditions
    if operative is None:
        if prefixes:
            _record(issues, ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE)
        return
    for entry in root.entries:
        if not isinstance(entry, ProjectIRCompletedQueryBlockOutput):
            continue
        prefix = entry.join_prefix
        semantic = entry.semantic_entry
        regions = tuple(
            region
            for region in root.completed.effective_outputs.current_regions
            if region.ledger.owner is semantic.owner
        )
        if prefix is None:
            if regions:
                _record(issues, ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE)
            continue
        if (
            type(prefix) is not ProjectIRComposedJoinPrefix
            or prefix.semantic_entry is not semantic
            or prefix.starting_allocation is not entry.starting_allocation
        ):
            _record(issues, ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE)
            continue
        valid = (
            len(regions) == 1
            and prefix.region is regions[0]
            and len(prefix.joins)
            == len(prefix.region.joins)
            == len(entry.join_properties)
            and isinstance(semantic.root, ProjectConcreteJoinedQualify)
            and any(join is prefix.final_join for join in prefix.joins)
            and prefix.final_join.source.output
            is semantic.root.window_stage.input_aggregation.input_filter.joined_semantics.final_output
            and entry.source_properties.output is prefix.final_join.output
        )
        expected_pairs: list[tuple[object, object]] = []
        # Each input's images, and the one image across the inputs: two inputs
        # may share one historical factor that their producers no longer share,
        # so a factor a JOIN introduces at an input is imaged through that input.
        factor_images: dict[int, object] = {}
        input_images: dict[int, dict[int, object]] = {}
        for joined in prefix.joins:
            for image in joined.inputs:
                if image.producer is not None:
                    producer_entry = _entry_for_owner(root, image.producer)
                    if producer_entry is None or isinstance(
                        producer_entry, ProjectIRQueryBlockTerminal
                    ):
                        valid = False
                        continue
                    old_factors = image.source_properties.grain.factors
                    new_factors = (
                        producer_entry.active_properties.relational.grain.factors
                    )
                    valid = valid and len(old_factors) == len(new_factors)
                    scoped = input_images.setdefault(id(image.source.ref), {})
                    # A JOIN factor's image also images its nested base and
                    # source factors: a grouped factor two JOIN hops back is
                    # reachable only through them.
                    pending = [
                        (old.identity, new.identity)
                        for old, new in zip(old_factors, new_factors, strict=True)
                    ]
                    while pending:
                        old, new = pending.pop()
                        prior = scoped.get(id(old))
                        if prior is not None and prior is not new:
                            valid = False
                        scoped[id(old)] = new
                        prior = factor_images.get(id(old))
                        factor_images[id(old)] = (
                            new if prior is None or prior is new else _NO_IMAGE
                        )
                        if isinstance(
                            old, ProjectJoinGrainFactorIdentity
                        ) and isinstance(new, ProjectJoinGrainFactorIdentity):
                            pending.append((old.base, new.base))
                            if (
                                old.source_factor is not None
                                and new.source_factor is not None
                            ):
                                pending.append((old.source_factor, new.source_factor))

        def factor_matches(old, new, scope=None):
            known = None if scope is None else scope.get(id(old))
            if known is None:
                known = factor_images.get(id(old))
            if known is not None:
                return known is new
            if isinstance(old, ProjectJoinGrainFactorIdentity):
                if not isinstance(new, ProjectJoinGrainFactorIdentity):
                    return False
                inner = input_images.get(id(old.introduction_use))
                introduction = ref_images.get(
                    id(old.introduction_use),
                    old.introduction_use
                    if any(old.introduction_use is ref for ref in historical_refs)
                    else None,
                )
                nulling = tuple(
                    ref_images.get(
                        id(ref),
                        ref if any(ref is item for item in historical_refs) else None,
                    )
                    for ref in old.nulling_joins
                )
                return (
                    new.introduction_use is introduction
                    and _same_objects(new.nulling_joins, nulling)
                    and factor_matches(old.base, new.base, inner)
                    and (
                        (old.source_factor is None and new.source_factor is None)
                        or old.source_factor is not None
                        and new.source_factor is not None
                        and factor_matches(old.source_factor, new.source_factor, inner)
                    )
                )
            return old is new

        def factor_tuple_matches(old, new):
            return len(old) == len(new) and all(
                factor_matches(a, b) for a, b in zip(old, new, strict=True)
            )

        previous: dict[int, ProjectIRJoinRowOutput] = {}
        for joined, original, result_properties in zip(
            prefix.joins, prefix.region.joins, entry.join_properties, strict=True
        ):
            properties = result_properties.relational
            conditions = tuple(
                c
                for c in operative.entries
                if c.ledger is prefix.region.ledger and c.use is original.use
            )
            sources = tuple(
                p.relational
                for p in prefix.region.join_properties
                if p.join is original
            )
            valid = (
                valid
                and joined.source is original
                and len(conditions) == 1
                and joined.condition is conditions[0]
                and len(sources) == 1
                and joined.source_properties is sources[0]
            )
            valid = (
                valid
                and len(joined.inputs) == 2
                and properties.output is joined.output
                and joined.output.occurrence.producer is joined.node
            )
            expected_pairs.append((original.node.ref, joined.node.ref))
            for ordinal, image in enumerate(joined.inputs):
                source = (original.left_input, original.right_input)[ordinal]
                valid = (
                    valid
                    and image.source is original.input_uses[ordinal]
                    and image.source_properties is source
                    and image.use.slot.input_ordinal == ordinal
                    and image.use.slot.consumer is joined.node
                )
                local = previous.get(id(source.output))
                if local is not None:
                    valid = (
                        valid
                        and image.producer is None
                        and image.use.output is local.occurrence
                    )
                else:
                    anchor = source.output.occurrence.anchor
                    if isinstance(source.output, ProjectCurrentMaterializedInput):
                        expected_owners = (source.output.authority.owner,)
                    elif isinstance(anchor, ProjectIRRelationAnchor):
                        expected_owners = tuple(
                            owner
                            for owner in root.owners
                            if _declaration_identity(owner) == anchor.identity
                        )
                    else:
                        expected_owners = ()
                    valid = (
                        valid
                        and len(expected_owners) == 1
                        and image.producer is expected_owners[0]
                    )
                    producer = (
                        None
                        if image.producer is None
                        else _entry_for_owner(root, image.producer)
                    )
                    output = None if producer is None else _active_output(producer)
                    valid = valid and output is not None and image.use.output is output
                expected_pairs.extend(
                    (
                        (image.source.ref, image.use.ref),
                        (image.source.slot.ref, image.use.slot.ref),
                    )
                )
            expected_pairs.append(
                (original.output.occurrence.ref, joined.output.occurrence.ref)
            )
            valid = valid and len(joined.output.row_shape.fields) == len(
                original.output.row_shape.fields
            )
            for old, new in zip(
                original.output.row_shape.fields,
                joined.output.row_shape.fields,
                strict=True,
            ):
                introduction = use_images.get(id(old.introduction_use))
                nulling = tuple(
                    ref_images.get(
                        id(ref),
                        ref
                        if any(ref is retained for retained in historical_refs)
                        else None,
                    )
                    for ref in old.nulling_joins
                )
                valid = (
                    valid
                    and new.field_position == old.field_position
                    and new.evidence is old.evidence
                    and new.effective_nullability is old.effective_nullability
                    and new.introduction_use is introduction
                    and _same_objects(new.nulling_joins, nulling)
                )
            valid = (
                valid
                and _property_shape_valid(properties)
                and _fd_index_valid(properties)
                and _class_signatures(properties)
                == _class_signatures(joined.source_properties)
                and _actual_key_signatures(properties)
                == _actual_key_signatures(joined.source_properties)
                and _actual_fd_signatures(properties)
                == _actual_fd_signatures(joined.source_properties)
                and properties.grain.state is joined.source_properties.grain.state
                and properties.grain.origin_set is root.grain_origins
                and properties.grain.witness is joined.source_properties
            )
            old_grain = joined.source_properties.grain
            new_grain = properties.grain
            valid = (
                valid
                and factor_tuple_matches(
                    tuple(f.identity for f in old_grain.factors),
                    tuple(f.identity for f in new_grain.factors),
                )
                and factor_tuple_matches(old_grain.active, new_grain.active)
                and len(old_grain.dependencies) == len(new_grain.dependencies)
                and all(
                    factor_tuple_matches(a.determinants, b.determinants)
                    and factor_tuple_matches(a.dependents, b.dependents)
                    for a, b in zip(
                        old_grain.dependencies, new_grain.dependencies, strict=True
                    )
                )
            )
            previous[id(original.output)] = joined.output
        valid = (
            valid
            and len(expected_pairs) == len(prefix.ref_images)
            and all(
                a is c and b is d
                for (a, b), (c, d) in zip(
                    expected_pairs, prefix.ref_images, strict=True
                )
            )
        )
        if not valid:
            _record(issues, ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE)


def _verify_values(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    """A VALUES producer has no use, singleton classes and no key, FD or grain."""
    for entry in root.entries:
        if not isinstance(entry, ProjectIRCompletedValuesOutput):
            continue
        semantic = entry.semantic_entry
        result = entry.active_properties.relational
        valid = (
            entry.operator.evidence is semantic
            and entry.operator.kind is ProjectIRQueryBlockOperatorExtensionKind.VALUES
            and len(entry.active_output.row_shape.fields) == len(semantic.fields)
            and _property_shape_valid(result)
            and _fd_index_valid(result)
            and not result.keys
            and not result.fds
            and _class_signatures(result)
            == tuple((i,) for i in range(len(result.fields)))
            and result.grain.state is ProjectGrainBasisState.UNKNOWN
            and not result.grain.factors
            and not result.grain.dependencies
            and result.grain.origin_set is root.grain_origins
            and result.grain.witness is semantic.origin
            and _zero_input_root_valid(semantic, entry)
            and _unnest_root_valid(root, semantic)
        )
        for position, (actual, expected) in enumerate(
            zip(entry.active_output.row_shape.fields, semantic.fields, strict=True)
        ):
            valid = (
                valid
                and actual.semantic_source is expected
                and actual.evidence is expected.field
                and actual.final_identity is expected.identity
                and actual.field_position == position
                and actual.effective_nullability is expected.field.nullability
                and actual.introduction_use is None
                and not actual.nulling_joins
            )
        if not valid:
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                entry.active_output.occurrence,
            )


def _unnest_root_valid(root, semantic) -> bool:
    """An Unnest occurrence's rows are its one typed input fact's element
    fields, in child order (D-S05-7); no other relation has an Unnest root."""
    from pietto._project.project_unnest import ProjectUnnestRelation

    relation, owner = semantic.root, semantic.owner
    unnest = type(owner.definition) is UnnestRelationDef
    if not unnest or type(relation) is not ProjectUnnestRelation:
        return unnest is (type(relation) is ProjectUnnestRelation)
    facts = root.completed.completion.plan.semantic_facts.find_owner(owner)
    fact = relation.fact
    elements = () if fact.nested_type is None else fact.nested_type.element_fields
    return (
        relation.definition is owner.definition
        and fact.query_let is owner.unnest
        and len(facts) == 1
        and facts[0].unnest_occurrence is fact
        and fact.diagnostic is None
        and not relation.diagnostics
        and len(elements) == len(semantic.fields) > 0
        and all(
            field.field is element.field and field.identity == identity
            for field, element, identity in zip(
                semantic.fields, elements, fact.element_fields, strict=True
            )
        )
    )


# The one admitted table function, re-derived here without the semantic owner.
GENERATE_SERIES = (
    "pg_catalog.generate_series(pg_catalog.int8,pg_catalog.int8,pg_catalog.int8)"
)
GENERATE_SERIES_ROWS = 1_048_576


def _authored_int(expression):
    """A fixed int64 literal written directly, or with one sign on it."""
    sign = 1
    if type(expression) is UnaryExpr and expression.operator in {"-", "+"}:
        sign = -1 if expression.operator == "-" else 1
        expression = expression.operand
    if type(expression) is not LiteralExpr:
        return None
    value = expression.value
    if type(value) is not int:
        return None
    value *= sign
    return value if -(2**63) <= value <= 2**63 - 1 else None


def table_function_facts(authored):
    """Identity, three values and rows of one admitted call, from its AST alone.

    None unless the call is exactly the admitted ``generate_series`` with three
    fixed int64 values, a nonzero step and at most the D70.07 row bound.
    """
    if type(authored) is not TableFunctionRelationDef:
        return None
    call = authored.source.call
    values = tuple(_authored_int(argument) for argument in call.arguments)
    if (
        type(call.callee) is not NameExpr
        or call.callee.name != "generate_series"
        or authored.name != authored.source.binding_name
        or len(values) != 3
        or any(value is None for value in values)
    ):
        return None
    start, stop, step = cast(tuple[int, int, int], values)
    if step == 0:
        return None
    rows = (
        0
        if (step > 0 and start > stop) or (step < 0 and start < stop)
        else (abs(stop - start) // abs(step)) + 1
    )
    if rows > GENERATE_SERIES_ROWS:
        return None
    return GENERATE_SERIES, (start, stop, step), rows


def _zero_input_root_valid(semantic, entry) -> bool:
    """A table-function root is re-derived from its call; effects stay local.

    Its occurrence evidence is exactly the admitted function's: deterministic
    and side-effect free, with error behavior and evaluation count unknown.
    The output-level effect evidence stays unknown on every axis.
    """
    from pietto._project.project_table_function import ProjectTableFunctionRelation

    root = semantic.root
    if type(root) is not ProjectTableFunctionRelation:
        return type(semantic.owner.definition) is not TableFunctionRelationDef
    facts = table_function_facts(semantic.owner.definition)
    signature = root.signature
    effect = entry.active_properties.effect
    return (
        facts is not None
        and signature is not None
        and not root.diagnostics
        and (signature.identity, root.arguments, root.row_count) == facts
        and signature.determinism == ProjectIRDeterminismEvidence.DETERMINISTIC.value
        and signature.side_effects == ProjectIRSideEffectEvidence.SIDE_EFFECT_FREE.value
        and signature.error_behavior == ProjectIRErrorBehaviorEvidence.UNKNOWN.value
        and signature.evaluation_count == ProjectIREvaluationCountEvidence.UNKNOWN.value
        and len(root.columns) == 1
        and root.columns[0].name == semantic.owner.definition.name
        and root.columns[0].logical_type == "Int"
        and root.columns[0].nullable is False
        and effect.determinism is ProjectIRDeterminismEvidence.UNKNOWN
        and effect.error_behavior is ProjectIRErrorBehaviorEvidence.UNKNOWN
        and effect.side_effects is ProjectIRSideEffectEvidence.UNKNOWN
        and effect.evaluation_count is ProjectIREvaluationCountEvidence.UNKNOWN
    )


def _verify_set_operations(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    """Check N-ary authored uses and subset/alternative images, without building IR."""
    for entry in root.entries:
        if not isinstance(entry, ProjectIRCompletedSetOperationOutput):
            continue
        semantic = entry.semantic_entry
        operation = semantic.root
        origin = semantic.row_domain.set_origin
        result = entry.active_properties.relational
        witness = result.grain.witness
        witness_valid = (
            witness is operation
            or type(witness) is tuple
            and len(witness) == 2
            and witness[0] is operation
            and witness[1] is entry.operands[0].producer.active_properties.relational
        )
        valid = (
            entry.operator.evidence is semantic
            and entry.operator.kind
            is ProjectIRQueryBlockOperatorExtensionKind.SET_OPERATION
            and len(entry.operands) == len(operation.uses)
            and len(entry.active_output.row_shape.fields) == len(semantic.fields)
            and _property_shape_valid(result)
            and _fd_index_valid(result)
            and result.grain.origin_set is root.grain_origins
            and witness_valid
        )
        inputs: list[ProjectIROutputRelationalProperties] = []
        for ordinal, (image, source) in enumerate(
            zip(entry.operands, operation.uses, strict=True)
        ):
            producer = _entry_for_owner(root, source.authority.owner)
            valid = (
                valid
                and image.source is source
                and image.producer is producer
                and producer is not None
                and producer.semantic_entry is source.authority.entry
                and image.use.output is _active_output(producer)
                and image.use.slot.consumer is entry.operator.node
                and image.use.slot.input_ordinal == ordinal
                and type(image.use) is ProjectIRSetInputUseOccurrence
            )
            inputs.append(image.producer.active_properties.relational)
        for position, (actual, expected) in enumerate(
            zip(entry.active_output.row_shape.fields, semantic.fields, strict=True)
        ):
            valid = (
                valid
                and actual.semantic_source is expected
                and actual.evidence is expected.field
                and actual.final_identity is expected.identity
                and actual.field_position == position
                and actual.effective_nullability is expected.field.nullability
                and actual.introduction_use is None
                and not actual.nulling_joins
            )
        kind = operation.multiplicity.value.split("_", 1)[0]
        subsets = (
            ()
            if kind == "union"
            else tuple(inputs)
            if kind == "intersect"
            else tuple(inputs[:1])
        )
        groups = [set((i,)) for i in range(len(result.fields))]
        for incoming in subsets:
            for value_class in incoming.value_classes:
                members = {field.field_position for field in value_class.members}
                overlap = tuple(group for group in groups if group & members)
                if not overlap:
                    valid = False
                    continue
                combined = set().union(*overlap)
                groups = [group for group in groups if not group & members]
                groups.append(combined)
        signatures = tuple(tuple(sorted(group)) for group in sorted(groups, key=min))
        valid = valid and _class_signatures(result) == signatures
        keys: list[_KeySignature] = []
        facts: list[_FDSignature] = []
        for incoming in subsets:
            images = tuple(
                next(
                    (
                        signature
                        for signature in signatures
                        if all(
                            member.field_position in signature
                            for member in value_class.members
                        )
                    ),
                    None,
                )
                for value_class in incoming.value_classes
            )
            imaged_keys, imaged_fds = _expected_imaged_key_fd_signatures(
                incoming=incoming, output=result, images=images, coalesced=True
            )
            keys.extend(imaged_keys)
            facts.extend(imaged_fds)
        expected_keys = _frontier_key_signatures(tuple(keys))
        for determinants, strength in expected_keys:
            dependents = tuple(
                i for i in range(len(result.value_classes)) if i not in determinants
            )
            if dependents:
                facts.append((determinants, dependents, strength))
        expected_fds: list[_FDSignature] = []
        for fact in facts:
            if fact not in expected_fds:
                expected_fds.append(fact)
        valid = (
            valid
            and _actual_key_signatures(result) == expected_keys
            and _actual_fd_signatures(result) == tuple(expected_fds)
        )
        if origin is None:
            valid = False
        elif origin.factor is not None:
            valid = (
                valid
                and result.grain.state is ProjectGrainBasisState.FACTORIZED
                and _same_objects(result.grain.active, (origin.factor,))
                and _same_objects(
                    tuple(factor.identity for factor in result.grain.factors),
                    (origin.factor,),
                )
                and not result.grain.dependencies
            )
        else:
            left = inputs[0].grain
            global_input = (
                left.state is ProjectGrainBasisState.GLOBAL
                or kind == "intersect"
                and any(p.grain.state is ProjectGrainBasisState.GLOBAL for p in inputs)
            )
            retained = left.state is ProjectGrainBasisState.FACTORIZED and any(
                key.strength is ProjectRowUniquenessStrength.STRICT
                for key in inputs[0].keys
            )
            expected_state = (
                ProjectGrainBasisState.GLOBAL
                if global_input
                else ProjectGrainBasisState.FACTORIZED
                if retained
                else ProjectGrainBasisState.UNKNOWN
            )
            valid = valid and result.grain.state is expected_state
            if global_input:
                valid = (
                    valid
                    and not result.grain.factors
                    and not result.grain.active
                    and not result.grain.dependencies
                )
            else:
                valid = (
                    valid
                    and _same_objects(result.grain.factors, left.factors)
                    and _same_objects(
                        result.grain.active, left.active if retained else ()
                    )
                    and _same_objects(result.grain.dependencies, left.dependencies)
                )
        if not valid:
            _record(
                issues,
                ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                entry.operator,
            )


def _verify_single_match_retention(
    root: ProjectIRQueryBlockSnapshot,
    issues: list[ProjectIRQueryBlockVerificationIssue],
) -> None:
    source = root.completed.single_matches
    if source.root is not root.completed.effective_outputs or len(
        root.requirements
    ) != len(source.entries):
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE)
        return
    for position, (retained, assessment) in enumerate(
        zip(root.requirements, source.entries, strict=True)
    ):
        owner = _entry_for_owner(root, assessment.request.owner)
        valid = (
            type(retained) is ProjectIRSingleMatchRetention
            and retained.position == position
            and retained.assessment is assessment
            and retained.owner_entry is owner
            and owner is not None
        )
        represented = (
            owner is not None
            and not isinstance(owner, ProjectIRQueryBlockTerminal)
            and assessment.state is not ProjectSingleMatchState.INVALID
        )
        if assessment.state is ProjectSingleMatchState.INVALID:
            valid = (
                valid
                and isinstance(owner, ProjectIRQueryBlockTerminal)
                and owner.reason
                in {
                    ProjectIRQueryBlockTerminalReason.INVALID_SINGLE_MATCH,
                    ProjectIRQueryBlockTerminalReason.SEMANTIC_OUTPUT_NON_CONCRETE,
                }
            )
        expected_boundaries: list[object] = []
        if represented:
            for original in assessment.joins:
                candidates = (
                    tuple(
                        join
                        for join in owner.join_prefix.joins
                        if join.source is original
                    )
                    if isinstance(owner, ProjectIRCompletedQueryBlockOutput)
                    and owner.join_prefix is not None
                    else ()
                )
                if len(candidates) == 1:
                    expected_boundaries.append(candidates[0])
                else:
                    valid = False
        valid = (
            valid
            and _same_objects(retained.boundaries, tuple(expected_boundaries))
            and len(retained.proofs) == len(assessment.proofs)
        )

        def check_proof(
            image: ProjectIRSingleMatchProofImage, proof: ProjectSingleMatchProof
        ) -> bool:
            if (
                type(image) is not ProjectIRSingleMatchProofImage
                or image.source is not proof
            ):
                return False
            selected = ()
            if represented:
                selected = tuple(
                    mapped
                    for original, mapped in zip(
                        assessment.joins, expected_boundaries, strict=True
                    )
                    if any(
                        item is original.input_uses[1] or item is original.condition
                        for item in proof.roots
                    )
                )
                if len(selected) != 1:
                    return False
            producers = tuple(
                entry
                for item in proof.roots
                for entry in root.entries
                if entry.semantic_entry is item
            )
            nodes: list[ProjectIRPlanNodeOccurrence] = []
            for producer in producers:
                if isinstance(producer, ProjectIRCompletedQueryBlockOutput):
                    nodes.extend(
                        operator.node
                        for operator in producer.operators
                        if any(operator.evidence is item for item in proof.roots)
                    )
                elif isinstance(producer, ProjectIRReusedEffectiveOutput):
                    nodes.extend(
                        operator.node
                        for operator in producer.semantic_entry.fragment.logical_stage.operators
                        if any(operator is item for item in proof.roots)
                    )
                elif isinstance(producer, ProjectIRReboundExistingOutput):
                    original_ops = (
                        producer.semantic_entry.fragment.logical_stage.operators
                    )
                    rebuilt_ops = producer.rebuilt_fragment.logical_stage.operators
                    if len(original_ops) != len(rebuilt_ops):
                        return False
                    nodes.extend(
                        rebuilt_ops[i].node
                        for i, operator in enumerate(original_ops)
                        if any(operator is item for item in proof.roots)
                    )
            children = tuple(
                item
                for item in proof.roots
                if isinstance(item, ProjectSingleMatchProof)
            )
            return (
                _same_objects(image.boundaries, selected)
                and _same_objects(image.producers, producers)
                and _same_objects(image.premise_nodes, tuple(nodes))
                and len(image.children) == len(children)
                and all(
                    check_proof(child, original)
                    for child, original in zip(image.children, children, strict=True)
                )
            )

        valid = valid and all(
            check_proof(image, proof)
            for image, proof in zip(retained.proofs, assessment.proofs, strict=True)
        )
        if assessment.diagnostic is not None:
            valid = valid and any(
                assessment.diagnostic is diagnostic
                for diagnostic in root.completed.diagnostics
            )
        if not valid:
            _record(issues, ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE)
    for entry in root.entries:
        invalid = tuple(
            item
            for item in source.entries
            if item.request.owner is entry.owner
            and item.state is ProjectSingleMatchState.INVALID
        )
        if (
            isinstance(entry, ProjectIRQueryBlockTerminal)
            and entry.reason is ProjectIRQueryBlockTerminalReason.INVALID_SINGLE_MATCH
        ):
            if (
                not invalid
                or type(entry.blocker) is not tuple
                or not _same_objects(entry.blocker, invalid)
            ):
                _record(
                    issues, ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE
                )
        if (
            isinstance(entry, ProjectIRQueryBlockTerminal)
            and entry.reason
            is ProjectIRQueryBlockTerminalReason.ACTIVE_INPUTS_IR_NON_CONCRETE
        ):
            expected = tuple(
                target
                for dependency in entry.semantic_entry.dependencies
                if isinstance(
                    target := _entry_for_owner(root, dependency.target),
                    ProjectIRQueryBlockTerminal,
                )
            )
            if (
                not expected
                or type(entry.blocker) is not tuple
                or not _same_objects(entry.blocker, expected)
            ):
                _record(
                    issues, ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE
                )


def _verify_compiled_query_block_ir(root: CompiledQueryBlockIR):
    """Check every resolved operator, ordered input and retained_field against its owner."""
    from pietto._project.project_query_block_ir import (
        CompiledQueryBlockIR,
        CompiledIROperator,
        CompiledIRField,
        CompiledIRReference,
    )
    from pietto._project.project_completed_semantics import (
        CompiledCompletedSemanticResult,
    )
    from pietto._project.project_compiled_verification import RELATIONS, need
    from pietto._project.model import ProjectRowField, ProjectResolvedTypeKind

    need(type(root) is CompiledQueryBlockIR, "IR_ROOT")
    completed = root.completed
    need(type(completed) is CompiledCompletedSemanticResult, "IR_SEMANTICS")
    from pietto._project.project_completed_semantics import verify_compiled_semantics

    verify_compiled_semantics(completed)
    records = completed.root.records
    need(set(root.references) == set(records), "IR_REFERENCE_INVENTORY")
    for address, reference in root.references.items():
        need(
            type(reference) is CompiledIRReference
            and reference.scope is root.scope
            and reference.kind == address.kind
            and reference.position == address.position,
            "IR_REFERENCE",
        )
    expected = tuple(r for r in records.values() if r.address.kind in RELATIONS)
    need(
        type(root.operators) is tuple and len(root.operators) == len(expected),
        "IR_OPERATOR_INVENTORY",
    )
    owners = {d.address: d for d in completed.declarations}
    facts = {f.address: f for f in completed.facts}
    need(len(facts) == len(completed.facts), "IR_FACT_INVENTORY")
    for actual, record in zip(root.operators, expected, strict=True):
        declaration = (
            record.get("declaration")
            if record.address.kind == "source"
            else record.get("owner")
        )
        need(
            type(actual) is CompiledIROperator
            and actual.ref is root.references[record.address]
            and actual.record is record
            and actual.owner is owners[declaration]
            and actual.kind == record.address.kind,
            "IR_OPERATOR",
        )
        inputs = tuple(
            root.references[r.get("producer")]
            for r in records.values()
            if r.address.kind == "use" and r.get("consumer") == record.address
        )
        need(
            type(actual.inputs) is tuple
            and len(actual.inputs) == len(inputs)
            and all(a is b for a, b in zip(actual.inputs, inputs, strict=True)),
            "IR_INPUTS",
        )
        ports = tuple(
            r
            for r in records.values()
            if r.address.kind == "port" and r.get("owner") == record.address
        )
        need(
            type(actual.fields) is tuple and len(actual.fields) == len(ports),
            "IR_FIELDS",
        )
        for position, (retained_field, port) in enumerate(
            zip(actual.fields, ports, strict=True)
        ):
            fact = facts[port.address]
            need(
                type(retained_field) is CompiledIRField
                and retained_field.ref is root.references[port.address]
                and retained_field.owner is actual.ref
                and retained_field.field_position == position
                and retained_field.fact is fact
                and fact.root is completed.root,
                "IR_FIELD_OWNER",
            )
            need(
                type(retained_field.evidence) is ProjectRowField
                and retained_field.evidence.field_def is None
                and retained_field.evidence.resolved_type.kind
                is ProjectResolvedTypeKind.BUILTIN
                and retained_field.evidence.name == port.get("label")
                and retained_field.evidence.resolved_type.name
                == fact.value_type.resolved_type.name
                and retained_field.evidence.nullability.value
                == fact.value_type.nullability.value,
                "IR_FIELD_FACT",
            )
    from pietto._project.project_query_block_ir import (
        CompiledIRProperties,
        CompiledIRProperty,
    )

    from pietto._project.project_query_block_ir import CompiledIRRowOutput
    from pietto._project.project_grain import (
        CompiledGrainOrigin,
        CompiledGrainFactorIdentity,
    )

    need(
        type(root.grain_origin) is CompiledGrainOrigin
        and root.grain_origin.root is completed.root
        and root.grain_origin.scope is root.scope,
        "IR_GRAIN_ORIGIN",
    )
    for position, operator in enumerate(root.operators):
        output = operator.output
        need(
            type(output) is CompiledIRRowOutput
            and output.node is operator.ref
            and output.ref.scope is root.scope
            and output.ref.kind == "relation_output"
            and output.ref.position == position
            and output.fields is operator.fields,
            "IR_OUTPUT",
        )
        props = operator.properties
        need(
            type(props) is CompiledIRProperties
            and type(props.multiplicity) is CompiledIRProperty
            and type(props.ordering) is CompiledIRProperty,
            "IR_PROPERTIES",
        )
        need(
            props.multiplicity.owner is operator.ref
            and props.multiplicity.kind == "bag_multiplicity"
            and props.multiplicity.value == ("bag",),
            "IR_MULTIPLICITY",
        )
        expected_order = (
            operator.record.get("ordering") if operator.kind == "result" else ()
        )
        need(
            props.ordering.owner is operator.ref
            and props.ordering.kind == "ordering"
            and props.ordering.value == expected_order,
            "IR_ORDERING",
        )
        relational = props.relational
        need(
            type(relational) is ProjectIROutputRelationalProperties
            and relational.output is output
            and _property_shape_valid(relational)
            and _fd_index_valid(relational),
            "IR_RELATIONAL",
        )
        need(
            relational.grain.output is output
            and relational.grain.origin_set is root.grain_origin,
            "IR_GRAIN_ROOT",
        )
        for factor in relational.grain.factors:
            need(
                type(factor.identity) is CompiledGrainFactorIdentity
                and factor.identity.origin is root.grain_origin,
                "IR_GRAIN_FACTOR",
            )
            factor.identity.__post_init__()
        expected_limit = (
            operator.record.get("limit") if operator.kind == "result" else None
        )
        need((props.cardinality is None) is (expected_limit is None), "IR_CARDINALITY")
        if props.cardinality is not None:
            need(
                props.cardinality.owner is operator.ref
                and props.cardinality.kind == "cardinality"
                and props.cardinality.value == (expected_limit,),
                "IR_CARDINALITY",
            )
    verify_compiled_property_laws(root)
    terminal = records[completed.root.description.query].get("terminal")
    need(
        any(
            root.selected is item and item.ref is root.references[terminal]
            for item in root.operators
        ),
        "IR_SELECTED",
    )
    return root


def verify_compiled_query_block_ir(root: CompiledQueryBlockIR):
    """The complete IR check; repeated checks of these exact objects inside one top-level call rely on the completed one."""
    once(_verify_compiled_query_block_ir, root)
    return root


def verify_compiled_property_laws(root):
    """Independent signatures from resolved inputs; never call property builders."""
    from pietto._project.project_compiled_verification import need
    from pietto._project.project_grain import (
        ProjectGrainBasisState,
        ProjectGrainFactorKind,
    )
    from pietto._project.project_row_keys import resolved_uniqueness_strength

    records = root.completed.root.records
    built = {}

    def key_fds(keys, width, inherited=()):
        result = list(inherited)
        for determinants, strength in keys:
            dependent = tuple(i for i in range(width) if i not in determinants)
            item = (determinants, dependent, strength)
            if dependent and item not in result:
                result.append(item)
        return tuple(dict.fromkeys(result))

    def base_grain(operator, kind, state, incoming=None):
        actual = operator.properties.relational.grain
        if kind is None:
            need(actual.state is state and not actual.active, "PROPERTY_GLOBAL")
            return None
        need(actual.state is state and len(actual.active) == 1, "PROPERTY_BASE_GRAIN")
        factor = actual.active[0]
        need(
            factor.base is None
            and factor.ref is operator.ref
            and factor.kind is kind
            and factor.introduction_use is None,
            "PROPERTY_BASE_FACTOR",
        )
        expected = (
            ()
            if incoming is None
            else tuple(f.identity for f in incoming.grain.factors)
        ) + (factor,)
        need(
            tuple(f.identity for f in actual.factors) == expected,
            "PROPERTY_BASE_FACTORS",
        )
        return factor

    for operator in root.operators:
        record = operator.record
        kind = operator.kind
        actual = operator.properties.relational
        if kind == "source":
            need(
                _class_signatures(actual)
                == tuple((i,) for i in range(len(actual.fields))),
                "PROPERTY_SOURCE_CLASSES",
            )
            candidates = []
            for unique in records.values():
                if (
                    unique.address.kind != "source_unique"
                    or unique.get("source") != record.address
                ):
                    continue
                indices = tuple(
                    i
                    for i in range(len(actual.fields))
                    if any(records[a].get("ordinal") == i for a in unique.get("fields"))
                )
                candidates.append(
                    (
                        indices,
                        resolved_uniqueness_strength(
                            tuple(
                                actual.fields[i].effective_nullability for i in indices
                            )
                        ),
                    )
                )
            keys = _frontier_key_signatures(tuple(candidates))
            fds = key_fds(keys, len(actual.value_classes))
            base_grain(
                operator,
                ProjectGrainFactorKind.SOURCE_DOMAIN,
                ProjectGrainBasisState.FACTORIZED,
            )
            need(not actual.grain.dependencies, "PROPERTY_SOURCE_DEPENDENCIES")
        elif kind in ("row", "window", "result"):
            incoming = built[record.get("input")].properties.relational
            port_sources = tuple(
                records[records[a].get("source")] for a in record.get("outputs")
            )
            images = tuple(
                tuple(
                    i
                    for i, source in enumerate(port_sources)
                    if source.address.kind == "read"
                    and source.get("role") != "capture"
                    and any(
                        m.field_position == records[source.get("port")].get("ordinal")
                        for m in value.members
                    )
                )
                or None
                for value in incoming.value_classes
            )
            groups = tuple(image for image in images if image)
            used = {i for group in groups for i in group}
            expected_classes = tuple(
                sorted(
                    (
                        *groups,
                        *((i,) for i in range(len(actual.fields)) if i not in used),
                    ),
                    key=min,
                )
            )
            need(
                _class_signatures(actual) == expected_classes, "PROPERTY_IMAGE_CLASSES"
            )
            keys, fds = _expected_imaged_key_fd_signatures(
                incoming=incoming, output=actual, images=images
            )
            if kind == "result" and record.get("distinct"):
                factor_kind = (
                    None
                    if incoming.grain.state is ProjectGrainBasisState.GLOBAL
                    else ProjectGrainFactorKind.DISTINCT_DOMAIN
                )
                base_grain(
                    operator,
                    factor_kind,
                    ProjectGrainBasisState.GLOBAL
                    if factor_kind is None
                    else ProjectGrainBasisState.FACTORIZED,
                )
                need(not actual.grain.dependencies, "PROPERTY_DISTINCT_DEPENDENCIES")
            else:
                need(
                    actual.grain.state is incoming.grain.state
                    and actual.grain.factors == incoming.grain.factors
                    and actual.grain.active == incoming.grain.active
                    and actual.grain.dependencies == incoming.grain.dependencies,
                    "PROPERTY_IMAGE_GRAIN",
                )
        elif kind == "aggregate":
            incoming = built[record.get("input")].properties.relational
            count = len(record.get("keys"))
            need(
                _class_signatures(actual)
                == tuple((i,) for i in range(len(actual.fields))),
                "PROPERTY_GROUP_CLASSES",
            )
            keys = (
                ((tuple(range(count)), ProjectRowUniquenessStrength.STRICT),)
                if count
                else ()
            )
            fds = key_fds(keys, len(actual.value_classes))
            if count:
                factor = base_grain(
                    operator,
                    ProjectGrainFactorKind.GROUP_DOMAIN,
                    ProjectGrainBasisState.FACTORIZED,
                    incoming,
                )
                grouped_positions = {
                    records[records[a].get("port")].get("ordinal")
                    for a in record.get("keys")
                }
                grouped_classes = tuple(
                    c
                    for c in incoming.value_classes
                    if any(m.field_position in grouped_positions for m in c.members)
                )
                determines = any(
                    k.strength is ProjectRowUniquenessStrength.STRICT
                    and set(k.determinants) <= set(grouped_classes)
                    for k in incoming.keys
                )
                edges = (
                    [(incoming.grain.active, (factor,))]
                    if incoming.grain.active
                    else []
                )
                if incoming.grain.active and determines:
                    edges.append(((factor,), incoming.grain.active))
                prefix = incoming.grain.dependencies
                need(
                    actual.grain.dependencies[: len(prefix)] == prefix
                    and tuple(
                        (d.determinants, d.dependents)
                        for d in actual.grain.dependencies[len(prefix) :]
                    )
                    == tuple(edges),
                    "PROPERTY_GROUP_DEPENDENCIES",
                )
            else:
                base_grain(operator, None, ProjectGrainBasisState.GLOBAL)
                need(
                    actual.grain.factors == incoming.grain.factors
                    and actual.grain.dependencies == incoming.grain.dependencies,
                    "PROPERTY_GLOBAL_GRAIN",
                )
        elif kind == "set":
            inputs = tuple(
                built[records[a].get("producer")].properties.relational
                for a in record.get("operands")
            )
            subset = (
                ()
                if record.get("kind") == "union"
                else inputs
                if record.get("kind") == "intersect"
                else inputs[:1]
            )
            groups = [{i} for i in range(len(actual.fields))]
            for incoming in subset:
                for c in incoming.value_classes:
                    positions = {m.field_position for m in c.members}
                    merged = set().union(*(g for g in groups if g & positions))
                    groups = [g for g in groups if not g & positions] + [merged]
            classes = tuple(tuple(sorted(g)) for g in sorted(groups, key=min))
            need(_class_signatures(actual) == classes, "PROPERTY_SET_CLASSES")
            candidates, inherited = [], []
            for incoming in subset:
                images = tuple(
                    next(g for g in classes if c.members[0].field_position in g)
                    for c in incoming.value_classes
                )
                mapped_keys, mapped_fds = _expected_imaged_key_fd_signatures(
                    incoming=incoming, output=actual, images=images, coalesced=True
                )
                candidates.extend(mapped_keys)
                inherited.extend(mapped_fds)
            keys = _frontier_key_signatures(tuple(candidates))
            fds = key_fds(keys, len(classes), inherited)
            quotient = (
                record.get("quantifier") == "distinct" or record.get("kind") == "union"
            )
            if quotient:
                base_grain(
                    operator,
                    ProjectGrainFactorKind.SET_DOMAIN,
                    ProjectGrainBasisState.FACTORIZED,
                )
                need(not actual.grain.dependencies, "PROPERTY_SET_DEPENDENCIES")
            else:
                left = inputs[0].grain
                expected_state = (
                    ProjectGrainBasisState.GLOBAL
                    if left.state is ProjectGrainBasisState.GLOBAL
                    or record.get("kind") == "intersect"
                    and any(
                        i.grain.state is ProjectGrainBasisState.GLOBAL for i in inputs
                    )
                    else left.state
                    if left.state is ProjectGrainBasisState.FACTORIZED
                    and any(
                        k.strength is ProjectRowUniquenessStrength.STRICT
                        for k in inputs[0].keys
                    )
                    else ProjectGrainBasisState.UNKNOWN
                )
                need(actual.grain.state is expected_state, "PROPERTY_SET_GRAIN")
                if expected_state is ProjectGrainBasisState.GLOBAL:
                    need(
                        not actual.grain.active
                        and not actual.grain.factors
                        and not actual.grain.dependencies,
                        "PROPERTY_SET_GLOBAL",
                    )
                else:
                    need(
                        actual.grain.factors == left.factors
                        and actual.grain.dependencies == left.dependencies
                        and actual.grain.active
                        == (
                            left.active
                            if expected_state is ProjectGrainBasisState.FACTORIZED
                            else ()
                        ),
                        "PROPERTY_SET_SUBSET",
                    )
        elif kind == "join":
            keys, fds = compiled_join_property_signatures(root, operator, built)
            verify_compiled_join_grain(root, operator, built)
        elif kind in ("values", "table_function"):
            need(
                operator.inputs == ()
                and _class_signatures(actual)
                == tuple((i,) for i in range(len(actual.fields)))
                and actual.grain.state is ProjectGrainBasisState.UNKNOWN
                and not actual.grain.factors
                and not actual.grain.active
                and not actual.grain.dependencies,
                "PROPERTY_VALUES",
            )
            keys, fds = (), ()
        else:
            raise ValueError("COMPILED_PROPERTY_OPERATOR")
        need(
            _actual_key_signatures(actual) == keys
            and _actual_fd_signatures(actual) == fds,
            "PROPERTY_KEY_FD_DERIVATION",
        )
        built[record.address] = operator


def _compiled_join_inputs(root, operator, built):
    records = root.completed.root.records
    record = operator.record
    uses = tuple(records[a] for a in record.get("inputs"))
    parents = tuple(built[u.get("producer")] for u in uses)
    left, right = (p.properties.relational for p in parents)
    matched = []
    for side, incoming in enumerate((left, right)):
        positions = {
            records[
                records[records[a].get("left" if side == 0 else "right")].get("port")
            ].get("ordinal")
            for a in record.get("equalities")
        }
        matched.append(
            tuple(
                i
                for i, c in enumerate(incoming.value_classes)
                if any(m.field_position in positions for m in c.members)
            )
        )
    left_keys, right_keys = _actual_key_signatures(left), _actual_key_signatures(right)
    forward = bool(matched[1]) and any(set(k[0]) <= set(matched[1]) for k in right_keys)
    reverse = bool(matched[0]) and any(set(k[0]) <= set(matched[0]) for k in left_keys)
    if record.get("law") == "current":
        from pietto._project.project_compiled_schema import predicate_equalities

        reverse = (
            bool(matched[0])
            and any(set(k[0]) == set(matched[0]) for k in left_keys)
            and reverse
        )
        # Modern key bounds come only from the ON's positive equalities, written
        # by hand or in a mandatory predicate call's body. Keep these separate
        # from the retained legacy equalities.
        predicate_positions = (set(), set())
        for equality in predicate_equalities(records, record):
            operands = equality.get("operands")
            for lhs, rhs in (operands, operands[::-1]):
                if lhs.kind == rhs.kind == "read" and (
                    records[lhs].get("use") == uses[0].address
                    and records[rhs].get("use") == uses[1].address
                ):
                    for side, read in enumerate((lhs, rhs)):
                        predicate_positions[side].add(
                            records[records[read].get("port")].get("ordinal")
                        )
        predicate_matched = tuple(
            tuple(
                i
                for i, group in enumerate(incoming.value_classes)
                if any(
                    member.field_position in predicate_positions[side]
                    for member in group.members
                )
            )
            for side, incoming in enumerate((left, right))
        )
        forward |= any(set(key[0]) <= set(predicate_matched[1]) for key in right_keys)
        reverse |= any(set(key[0]) <= set(predicate_matched[0]) for key in left_keys)
        forward |= right.grain.state is ProjectGrainBasisState.GLOBAL
        reverse |= left.grain.state is ProjectGrainBasisState.GLOBAL
    return uses, parents, left, right, tuple(matched), forward, reverse


def compiled_join_property_signatures(root, operator, built):
    from pietto._project.project_compiled_verification import need

    record = operator.record
    _uses, _parents, left, right, _matched, forward, reverse = _compiled_join_inputs(
        root, operator, built
    )
    actual = operator.properties.relational
    kind = record.get("kind")
    left_only = kind in ("semi", "anti")
    offset = len(left.value_classes)
    classes = _class_signatures(left) + (
        ()
        if left_only
        else tuple(
            tuple(i + len(left.fields) for i in c) for c in _class_signatures(right)
        )
    )
    need(_class_signatures(actual) == classes, "PROPERTY_JOIN_CLASSES")
    left_null, right_null = kind in ("right", "full"), kind in ("left", "full")

    def mapped_keys(parent, shift, weaken):
        result = []
        for positions, strength in _actual_key_signatures(parent):
            image = tuple(i + shift for i in positions)
            non_null = all(
                all(
                    m.effective_nullability is ProjectRowFieldNullability.NON_NULL
                    for m in actual.value_classes[i].members
                )
                for i in image
            )
            result.append(
                (
                    image,
                    ProjectRowUniquenessStrength.LAX
                    if weaken
                    else ProjectRowUniquenessStrength.STRICT
                    if non_null
                    else strength,
                )
            )
        return tuple(result)

    left_keys = mapped_keys(left, 0, left_null)
    right_keys = () if left_only else mapped_keys(right, offset, right_null)
    candidates = list(left_keys) if left_only or forward else []
    if not left_only and reverse:
        candidates.extend(right_keys)
    if not left_only:
        for lhs, rhs in ((a, b) for a in left_keys for b in right_keys):
            determinants = tuple(
                i for i in range(len(classes)) if i in (*lhs[0], *rhs[0])
            )
            strict = (lhs[1] is rhs[1] is ProjectRowUniquenessStrength.STRICT) or all(
                all(
                    m.effective_nullability is ProjectRowFieldNullability.NON_NULL
                    for m in actual.value_classes[i].members
                )
                for i in determinants
            )
            candidates.append(
                (
                    determinants,
                    ProjectRowUniquenessStrength.STRICT
                    if strict
                    else ProjectRowUniquenessStrength.LAX,
                )
            )
    keys = _frontier_key_signatures(tuple(candidates))
    fds = []
    for parent, shift, weaken in (
        (left, 0, left_null),
        *(((right, offset, right_null),) if not left_only else ()),
    ):
        for determinants, dependent, strength in _actual_fd_signatures(parent):
            non_null = all(
                all(
                    m.effective_nullability is ProjectRowFieldNullability.NON_NULL
                    for m in parent.value_classes[i].members
                )
                for i in determinants
            )
            if weaken and (kind in ("right", "full") or not non_null):
                strength = ProjectRowUniquenessStrength.LAX
            item = (
                tuple(i + shift for i in determinants),
                tuple(i + shift for i in dependent),
                strength,
            )
            if item not in fds:
                fds.append(item)
    for determinants, strength in keys:
        dependent = tuple(i for i in range(len(classes)) if i not in determinants)
        if dependent:
            fds.append((determinants, dependent, strength))
    return keys, tuple(dict.fromkeys(fds))


def verify_compiled_join_grain(root, operator, built):
    from pietto._project.project_compiled_verification import need
    from pietto._project.project_grain import CompiledGrainFactorIdentity

    refs, record = root.references, operator.record
    uses, _parents, left, right, _matched, forward, reverse = _compiled_join_inputs(
        root, operator, built
    )
    actual = operator.properties.relational.grain
    kind = record.get("kind")
    left_only = kind in ("semi", "anti")
    named_left = uses[0].get("producer").kind != "join"
    left_nulling = (operator.ref,) if kind in ("right", "full") else ()
    right_nulling = (operator.ref,) if kind in ("left", "full") else ()
    expected_count = len(left.grain.factors) + (
        0 if left_only else len(right.grain.factors)
    )
    need(len(actual.factors) == expected_count, "PROPERTY_JOIN_FACTORS")
    images = ({}, {})
    position = 0
    for side, parent in enumerate((left, right)):
        if side and left_only:
            continue
        for old_factor in parent.grain.factors:
            old = old_factor.identity
            new = actual.factors[position].identity
            position += 1
            need(type(new) is CompiledGrainFactorIdentity, "PROPERTY_JOIN_FACTOR_TYPE")
            old_join = old.base is not None
            reuse = side == 0 and old_join and not named_left and not left_nulling
            if reuse:
                need(new is old, "PROPERTY_JOIN_FACTOR_REUSE")
            else:
                keep_intro = (
                    side == 0 and old_join and bool(left_nulling) and not named_left
                )
                introduction = (
                    old.introduction_use if keep_intro else refs[uses[side].address]
                )
                nulling = (
                    (
                        (*old.nulling_joins, *left_nulling)
                        if keep_intro
                        else left_nulling
                    )
                    if side == 0
                    else right_nulling
                )
                source = old if old_join else None
                need(
                    new.base is (old.base if old_join else old)
                    and new.introduction_use is introduction
                    and new.nulling_joins == nulling
                    and new.source_factor is source,
                    "PROPERTY_JOIN_FACTOR_IMAGE",
                )
            images[side][old] = new
    left_active = tuple(images[0][f] for f in left.grain.active)
    right_active = () if left_only else tuple(images[1][f] for f in right.grain.active)
    need(actual.active == (*left_active, *right_active), "PROPERTY_JOIN_ACTIVE")
    edges = []
    for side, parent in enumerate((left, right)):
        if side and left_only:
            continue
        edges.extend(
            (
                tuple(images[side][f] for f in d.determinants),
                tuple(images[side][f] for f in d.dependents),
            )
            for d in parent.grain.dependencies
        )
    source_active = left_active
    # No left-to-right edge when the JOIN NULL-extends its left side.
    if (
        not left_only
        and forward
        and not left_nulling
        and source_active
        and right_active
    ):
        edges.append((source_active, right_active))
    if (
        not left_only
        and reverse
        and not right_nulling
        and right_active
        and source_active
    ):
        edges.append((right_active, source_active))
    if not reverse and not right_nulling and right_active:
        from pietto._project.project_current_joins import compiled_local_reverse_sources

        for source in compiled_local_reverse_sources(
            root.completed.root.records, record, left, built, refs
        ):
            if source:
                edges.append(
                    (right_active, tuple(images[0][factor] for factor in source))
                )
    need(
        tuple((d.determinants, d.dependents) for d in actual.dependencies)
        == tuple(edges),
        "PROPERTY_JOIN_DEPENDENCIES",
    )
    expected_state = (
        left.grain.state
        if left_only
        else ProjectGrainBasisState.UNKNOWN
        if ProjectGrainBasisState.UNKNOWN in (left.grain.state, right.grain.state)
        else ProjectGrainBasisState.FACTORIZED
        if actual.active
        else ProjectGrainBasisState.UNKNOWN
        if kind == "full"
        else ProjectGrainBasisState.GLOBAL
    )
    need(actual.state is expected_state, "PROPERTY_JOIN_GRAIN")
