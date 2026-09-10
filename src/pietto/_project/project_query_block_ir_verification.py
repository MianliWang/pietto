"""Independent verification and derived analyses for Phase-63 query-block IR."""

from __future__ import annotations

from pietto._project.project_query_block_ir_algebra import ProjectIRComposedJoinPrefix
from pietto._project.project_final_outputs import (
    ProjectDistinct,
    ProjectCompletedSetOutput,
)

from pietto._project.project_current_join_inputs import ProjectCurrentMaterializedInput
from pietto._project.project_current_joins import (
    ProjectCurrentJoinRegion,
    ProjectCurrentBinaryJoin,
)
from pietto._project.project_single_match import (
    ProjectSingleMatchProof,
    ProjectSingleMatchProofKind,
    ProjectSingleMatchState,
)

from pietto._project.project_ir_joins import (
    ProjectIRConcreteJoinRegion,
    ProjectIRBinaryJoinOccurrence,
)


from dataclasses import dataclass, field
from enum import StrEnum
from heapq import heappop, heappush
from typing import cast

from pietto._project.model import (
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleWindowOutputFact,
)
from pietto._project.project_completion import ProjectExistingEffectiveOutput
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectCompletedOutputField,
    ProjectConcreteNoJoinReplay,
    ProjectNoJoinGroupedOutput,
    ProjectNoJoinQualifyKind,
    ProjectNoJoinScalarExpression,
    ProjectNoJoinWhereKind,
)
from pietto._project.project_grain import (
    ProjectGrainBasisState,
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
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputRelationalProperties,
)
from pietto._project.project_ir_verification import (
    ProjectIRChangeDomain,
    ProjectIRReachabilityEntry,
    ProjectIRVerificationRequirement,
)
from pietto._project.project_joined_aggregation import (
    ProjectJoinedAggregationMode,
    ProjectJoinedStageOutputOccurrence,
    ProjectJoinedStageOutputRole,
)
from pietto._project.project_joined_qualify import (
    ProjectConcreteJoinedQualify,
    ProjectJoinedQualifyStageKind,
)
from pietto._project.project_joined_row_filter import (
    ProjectJoinedRowFilterKind,
    ProjectJoinedRowMultiplicity,
)
from pietto._project.project_joined_row_semantics import (
    ProjectJoinedRowFieldSemantics,
)
from pietto._project.project_joined_windows import (
    ProjectSelectedWindowResultBinding,
)
from pietto._project.project_query_block_ir import (
    ProjectIRDistinctComparison,
    ProjectIRSingleMatchRetention,
    ProjectIRSingleMatchProofImage,
    ProjectIRQueryBlockGrainOrigin,
    ProjectIRQueryBlockRowDomainOrigin,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRCompletedSetOperationOutput,
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
from pietto.ast_nodes import DottedNameExpr, NameExpr, QueryDef, TableDef

__all__: tuple[str, ...] = ()


class ProjectIRQueryBlockVerificationStatus(StrEnum):
    VERIFIED = "verified"
    INVALID = "invalid"


class ProjectIRQueryBlockVerificationIssueKind(StrEnum):
    ROOT_CONTINUITY = "root_continuity"
    ALLOCATION = "allocation"
    LEDGER = "ledger"
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
        (
            *root.base_plan.structural_stage.nodes,
            *root.join_stage.structural.nodes,
            *root.structural.nodes,
        ),
        (
            *root.base_plan.structural_stage.outputs,
            *root.join_stage.structural.outputs,
            *root.structural.outputs,
        ),
        (
            *root.base_plan.structural_stage.uses,
            *root.join_stage.structural.uses,
            *root.structural.uses,
        ),
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
        (ProjectIRCompletedQueryBlockOutput, ProjectIRCompletedSetOperationOutput),
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
        elif type(entry) is ProjectIRCompletedSetOperationOutput:
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
            | ProjectIRCompletedSetOperationOutput,
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
            (ProjectIRCompletedQueryBlockOutput, ProjectIRCompletedSetOperationOutput),
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
        *root.join_stage.structural.input_slots,
        *root.structural.input_slots,
    )
    valid = (
        len({node.ref for node in nodes}) == len(nodes)
        and len({output.ref for output in outputs}) == len(outputs)
        and len({slot.ref for slot in slots}) == len(slots)
        and len({use.ref for use in uses}) == len(uses)
        and all(any(output.producer is node for node in nodes) for output in outputs)
        and all(any(slot.consumer is node for node in nodes) for slot in slots)
        and all(
            any(use.output is output for output in outputs)
            and any(use.slot is slot for slot in slots)
            and use.output.producer.ref.position < use.slot.consumer.ref.position
            for use in uses
        )
        and len({use.slot.ref for use in uses}) == len(uses)
    )
    for entry in root.entries:
        if type(entry) is ProjectIRCompletedQueryBlockOutput:
            valid = valid and all(
                use.slot is slot
                and slot.consumer is operator.node
                and slot.input_ordinal == 0
                for operator, slot, use in zip(
                    entry.operators,
                    entry.input_slots,
                    entry.uses,
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


def _property_shape_valid(properties: ProjectIROutputRelationalProperties) -> bool:
    output = properties.output
    fields = properties.fields
    if len(fields) != len(output.row_shape.fields) or any(
        field.field_position != position
        or field.evidence is not output.row_shape.fields[position].evidence
        for position, field in enumerate(fields)
    ):
        return False
    members = tuple(
        member
        for value_class in properties.value_classes
        for member in value_class.members
    )
    return (
        len(members) == len(fields)
        and len({id(member) for member in members}) == len(fields)
        and all(any(member is field for member in members) for field in fields)
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
                if expression.parts[0] != derived.from_clause.source_name:
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
) -> tuple[int, ...]:
    output = properties.output
    if type(output) is ProjectIRQueryBlockRowOutput:
        return tuple(
            field.field_position
            for field in output.row_shape.fields
            if (
                type(field.semantic_source) is ProjectJoinedStageOutputOccurrence
                and field.semantic_source.role is ProjectJoinedStageOutputRole.GROUP_KEY
            )
            or (
                type(field.semantic_source) is ProjectNoJoinGroupedOutput
                and field.semantic_source.field.result_role
                is ProjectRowResultRole.GROUP_KEY
            )
        )
    return tuple(
        position
        for position, field in enumerate(output.row_shape.fields)
        if field.evidence.result_role is ProjectRowResultRole.GROUP_KEY
    )


def _group_properties_valid(
    properties: ProjectIROutputRelationalProperties,
    context: object,
    incoming: ProjectIROutputRelationalProperties,
    root: ProjectIRQueryBlockSnapshot,
) -> bool:
    if type(context) is not ProjectIRQueryBlockAggregateEvaluationContext:
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
        positions = _group_key_positions(properties)
        key = ((positions, ProjectRowUniquenessStrength.STRICT),)
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
        expected_fds = tuple(item for item in expected_fds if item[1])
        factor = origin.factor
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
            bool(positions)
            and _actual_key_signatures(properties) == key
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
        return tuple((position,) for position in range(len(output.fields)))
    if kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
        if type(entry) is ProjectIRCompletedQueryBlockOutput:
            return _query_projection_class_signatures(entry, incoming)
        if type(entry) is ProjectIRReboundExistingOutput:
            return _historical_projection_class_signatures(entry, incoming)
        raise TypeError("Projection verification requires one closed entry.")
    return _preserved_class_signatures(incoming, len(output.fields))


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
        _verify_active_roots,
        _verify_historical_reuse,
        _verify_join_reuse,
        _verify_composed_joins,
        _verify_set_operations,
        _verify_single_match_retention,
        _verify_operator_sequence,
        _verify_semantic_evidence,
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
                    _verify_active_roots: (
                        ProjectIRQueryBlockVerificationIssueKind.ACTIVE_ROOT
                    ),
                    _verify_historical_reuse: (
                        ProjectIRQueryBlockVerificationIssueKind.HISTORICAL_REUSE
                    ),
                    _verify_join_reuse: ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE,
                    _verify_composed_joins: ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE,
                    _verify_set_operations: ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                    _verify_single_match_retention: ProjectIRQueryBlockVerificationIssueKind.SEMANTIC_EVIDENCE,
                    _verify_operator_sequence: (
                        ProjectIRQueryBlockVerificationIssueKind.OPERATOR_SEQUENCE
                    ),
                    _verify_semantic_evidence: (
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
    historical_uses = root.join_stage.structural.uses
    expected_historical = tuple(
        join
        for entry in root.entries
        if isinstance(entry, ProjectIRCompletedQueryBlockOutput)
        and entry.join_prefix is None
        and isinstance(entry.semantic_entry.root, ProjectConcreteJoinedQualify)
        for join in entry.semantic_entry.root.window_stage.input_aggregation.input_filter.joined_semantics.row_source.region.joins
    )
    if len(root.retained_joins) != len(expected_historical) or any(
        item.source is not original
        or item.node is not original.node
        or item.output is not original.output
        or not _same_objects(
            tuple(image.source for image in item.inputs), original.input_uses
        )
        or not _same_objects(item.input_uses, original.input_uses)
        for item, original in zip(root.retained_joins, expected_historical, strict=True)
    ):
        _record(issues, ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE)
    operative = root.completed.effective_outputs.operative_conditions
    for item, original in zip(root.retained_joins, expected_historical, strict=True):
        conditions = (
            ()
            if operative is None
            else tuple(
                condition
                for condition in operative.entries
                if condition.effective_use is original.use
            )
        )
        properties = tuple(
            value.relational
            for value in root.join_stage.properties.outputs
            if value.join is original
        )
        valid = _same_objects(conditions, (item.condition,)) and _same_objects(
            properties, (item.source_properties,)
        )
        for image, source in zip(
            item.inputs, (original.left_input, original.right_input), strict=True
        ):
            producers = tuple(
                entry.owner
                for entry in root.entries
                if not isinstance(entry, ProjectIRQueryBlockTerminal)
                and entry.active_output.occurrence is image.use.output
            )
            internal = any(
                image.use.output is join.output.occurrence
                and join.node.ref.position < original.node.ref.position
                for join in expected_historical
            )
            valid = (
                valid
                and image.source_properties is source
                and (
                    (len(producers) == 1 and image.producer is producers[0])
                    or (not producers and internal and image.producer is None)
                )
            )
        if not valid:
            _record(issues, ProjectIRQueryBlockVerificationIssueKind.JOIN_REUSE)
    historical_refs = tuple(
        item.ref
        for items in (
            root.base_plan.structural_stage.nodes,
            root.base_plan.structural_stage.uses,
            root.join_stage.structural.nodes,
            historical_uses,
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
        available_regions = regions or tuple(
            region
            for region in root.join_stage.regions
            if isinstance(region, ProjectIRConcreteJoinRegion)
            and region.ledger.owner is semantic.owner
        )
        valid = (
            len(available_regions) == 1
            and prefix.region is available_regions[0]
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
        factor_images: dict[int, object] = {}
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
                    for old, new in zip(old_factors, new_factors, strict=True):
                        prior = factor_images.get(id(old.identity))
                        if prior is not None and prior is not new.identity:
                            valid = False
                        factor_images[id(old.identity)] = new.identity

        def factor_matches(old, new):
            known = factor_images.get(id(old))
            if known is not None:
                return known is new
            if isinstance(old, ProjectJoinGrainFactorIdentity):
                if not isinstance(new, ProjectJoinGrainFactorIdentity):
                    return False
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
                    and factor_matches(old.base, new.base)
                    and (
                        (old.source_factor is None and new.source_factor is None)
                        or old.source_factor is not None
                        and new.source_factor is not None
                        and factor_matches(old.source_factor, new.source_factor)
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
                if c.ledger is prefix.region.ledger
                and (c.use is original.use or c.effective_use is original.use)
            )
            sources = (
                tuple(
                    p.relational
                    for p in prefix.region.join_properties
                    if p.join is original
                )
                if isinstance(prefix.region, ProjectCurrentJoinRegion)
                else tuple(
                    p.relational
                    for p in root.join_stage.properties.outputs
                    if p.join is original
                )
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
                if introduction is None and any(
                    old.introduction_use is use for use in historical_uses
                ):
                    introduction = old.introduction_use
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
    historical = tuple(
        join
        for region in root.join_stage.regions
        if isinstance(region, ProjectIRConcreteJoinRegion)
        for join in region.joins
    )
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
                elif not candidates and any(original is join for join in historical):
                    expected_boundaries.append(original)
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
                if proof.kind is ProjectSingleMatchProofKind.WHOLE_PATH:
                    selected = tuple(expected_boundaries)
                else:
                    selected = tuple(
                        mapped
                        for original, mapped in zip(
                            assessment.joins, expected_boundaries, strict=True
                        )
                        if any(
                            item is original.input_uses[1]
                            or isinstance(original, ProjectIRBinaryJoinOccurrence)
                            and item is original.path_step
                            or isinstance(original, ProjectCurrentBinaryJoin)
                            and item is original.condition
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
