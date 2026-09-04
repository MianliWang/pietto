"""Verified-only private inspection of Phase-63 query-block Project IR."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleRowFieldIdentity,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleWindowOutputFact,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_completion import (
    ProjectCompletion,
    ProjectCompletionDependency,
)
from pietto._project.project_final_outputs import ProjectEffectiveOutputCompletion
from pietto._project.project_grain import (
    ProjectGrainDependencyFact,
    ProjectGrainDomainFactor,
    ProjectGrainFactorIdentity,
    ProjectGroupedGrainFactorIdentity,
    ProjectJoinGrainFactorIdentity,
    ProjectSourceGrainFactorIdentity,
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
    ProjectIRSnapshotScope,
    ProjectIRUseOccurrence,
    ProjectIRUseRef,
    _declaration_identity,
)
from pietto._project.project_ir_composition import ProjectIRProjectPlan
from pietto._project.project_ir_joins import ProjectIRJoinRegionStage
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorOccurrence
from pietto._project.project_ir_properties import (
    ProjectIREffectEvidence,
    ProjectIRProvidedRelationOrdering,
    ProjectIRRelationRowOutput,
    ProjectIRRowField,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputCandidateKey,
    ProjectIROutputFDIndex,
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueClass,
    ProjectIROutputValueFD,
)
from pietto._project.project_ir_verification import ProjectIRReachabilityEntry
from pietto._project.project_multifact import ProjectMultiFactAnalysis
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationResult,
)
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockEffectEvidence,
    ProjectIRQueryBlockEntry,
    ProjectIRQueryBlockGrainOrigin,
    ProjectIRQueryBlockOperatorOccurrence,
    ProjectIRQueryBlockRelationInputEdge,
    ProjectIRQueryBlockResultProperties,
    ProjectIRQueryBlockRowField,
    ProjectIRQueryBlockRowOutput,
    ProjectIRQueryBlockScalarOutput,
    ProjectIRQueryBlockSnapshot,
    ProjectIRQueryBlockTerminal,
    ProjectIRQueryBlockWindowEvidence,
    ProjectIRQueryBlockWindowHiddenEvidence,
    ProjectIRQueryBlockWindowPolicy,
    ProjectIRReboundExistingOutput,
    ProjectIRReusedEffectiveOutput,
)
from pietto._project.project_final_outputs import (
    ProjectConcreteNoJoinReplay,
    ProjectRelationOrdering,
)
from pietto._project.project_joined_windows import (
    ProjectConcreteWindowComputation,
    ProjectSelectedWindowResultBinding,
)
from pietto._project.project_query_block_ir_pure_boundary import (
    PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT,
    PROJECT_QUERY_BLOCK_IR_PURE_ABSENT,
    ProjectQueryBlockIRPortableRef,
    ProjectQueryBlockIRPortableRefDomain,
    ProjectQueryBlockIRPureDocument,
    ProjectQueryBlockIRPureField,
    ProjectQueryBlockIRPureRecord,
    ProjectQueryBlockIRPureStatus,
    ProjectQueryBlockIRPureValue,
    ProjectQueryBlockIRRecordKind,
    evaluate_project_query_block_ir_document,
    project_query_block_ir_pure_boolean,
    project_query_block_ir_pure_enumeration,
    project_query_block_ir_pure_enumerations,
    project_query_block_ir_pure_integer,
    project_query_block_ir_pure_ref,
    project_query_block_ir_pure_refs,
    project_query_block_ir_pure_text,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
    ProjectIRQueryBlockReverseUseEntry,
    ProjectIRQueryBlockVerificationResult,
    ProjectIRQueryBlockVerificationStatus,
)

__all__: tuple[str, ...] = ()


type ProjectIRQueryBlockInspectionOperator = (
    ProjectIRLogicalOperatorOccurrence | ProjectIRQueryBlockOperatorOccurrence
)
type ProjectIRQueryBlockInspectionUse = (
    ProjectIRUseOccurrence
    | ProjectIROperatorFlowUseOccurrence
    | ProjectIRJoinInputUseOccurrence
)
type ProjectIRQueryBlockInspectionActiveOutput = (
    ProjectIRRelationRowOutput | ProjectIRQueryBlockRowOutput
)
type ProjectIRQueryBlockInspectionEffect = (
    ProjectIREffectEvidence | ProjectIRQueryBlockEffectEvidence
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRQueryBlockInspectionSummary:
    scope: ProjectIRSnapshotScope = field(repr=False, compare=False, hash=False)
    owner_count: int
    entry_count: int
    terminal_count: int
    node_count: int
    output_count: int
    input_slot_count: int
    use_count: int
    operator_count: int
    row_field_count: int
    relational_property_count: int
    grain_origin_count: int
    analysis_entry_count: int

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectIRSnapshotScope:
            raise TypeError("Query-block inspection requires one exact scope.")
        for value in (
            self.owner_count,
            self.entry_count,
            self.terminal_count,
            self.node_count,
            self.output_count,
            self.input_slot_count,
            self.use_count,
            self.operator_count,
            self.row_field_count,
            self.relational_property_count,
            self.grain_origin_count,
            self.analysis_entry_count,
        ):
            if type(value) is not int or value < 0:
                raise TypeError("Query-block inspection counts must be non-negative.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockInspection:
    """Complete identity-retaining observation of one verified Slice-14 bundle."""

    analysis_bundle: ProjectIRQueryBlockAnalysisBundle = field(
        repr=False, compare=False, hash=False
    )
    summary: ProjectIRQueryBlockInspectionSummary
    verification: ProjectIRQueryBlockVerificationResult
    root: ProjectIRQueryBlockSnapshot = field(repr=False, compare=False, hash=False)
    completed: ProjectConcreteCompletedSemanticResult = field(
        repr=False, compare=False, hash=False
    )
    project_completion: ProjectCompletion = field(repr=False, compare=False, hash=False)
    effective_output_completion: ProjectEffectiveOutputCompletion = field(
        repr=False, compare=False, hash=False
    )
    phase62_verification: ProjectPhase62VerificationResult = field(
        repr=False, compare=False, hash=False
    )
    phase62_root: ProjectMultiFactAnalysis = field(
        repr=False, compare=False, hash=False
    )
    base_plan: ProjectIRProjectPlan = field(repr=False, compare=False, hash=False)
    join_stage: ProjectIRJoinRegionStage = field(repr=False, compare=False, hash=False)
    owners: tuple[ProjectDeclarationOccurrence, ...]
    dependencies: tuple[ProjectCompletionDependency, ...]
    schedule: tuple[ProjectDeclarationOccurrence, ...]
    entries: tuple[ProjectIRQueryBlockEntry, ...]
    reused_entries: tuple[ProjectIRReusedEffectiveOutput, ...]
    rebound_entries: tuple[ProjectIRReboundExistingOutput, ...]
    completed_entries: tuple[ProjectIRCompletedQueryBlockOutput, ...]
    terminals: tuple[ProjectIRQueryBlockTerminal, ...]
    terminal_blockers: tuple[object, ...] = field(repr=False, compare=False, hash=False)
    active_outputs: tuple[ProjectIRQueryBlockInspectionActiveOutput, ...]
    active_properties: tuple[ProjectIRQueryBlockResultProperties, ...]
    combined_nodes: tuple[ProjectIRPlanNodeOccurrence, ...]
    combined_outputs: tuple[ProjectIROutputValueOccurrence, ...]
    combined_input_slots: tuple[ProjectIRInputSlotOccurrence, ...]
    combined_uses: tuple[ProjectIRQueryBlockInspectionUse, ...]
    slice14_nodes: tuple[ProjectIRPlanNodeOccurrence, ...]
    slice14_outputs: tuple[ProjectIROutputValueOccurrence, ...]
    slice14_input_slots: tuple[ProjectIRInputSlotOccurrence, ...]
    slice14_uses: tuple[
        ProjectIRUseOccurrence | ProjectIROperatorFlowUseOccurrence, ...
    ]
    operators: tuple[ProjectIRQueryBlockInspectionOperator, ...]
    relation_inputs: tuple[ProjectIRQueryBlockRelationInputEdge, ...]
    query_block_row_outputs: tuple[ProjectIRQueryBlockRowOutput, ...]
    query_block_scalar_outputs: tuple[ProjectIRQueryBlockScalarOutput, ...]
    query_block_row_fields: tuple[ProjectIRQueryBlockRowField, ...]
    final_field_identities: tuple[ProjectModuleRowFieldIdentity, ...]
    result_properties: tuple[ProjectIRQueryBlockResultProperties, ...]
    relational_properties: tuple[ProjectIROutputRelationalProperties, ...]
    relational_fields: tuple[ProjectIROutputFieldOccurrence, ...]
    value_classes: tuple[ProjectIROutputValueClass, ...]
    candidate_keys: tuple[ProjectIROutputCandidateKey, ...]
    value_fds: tuple[ProjectIROutputValueFD, ...]
    fd_indexes: tuple[ProjectIROutputFDIndex, ...]
    grain_origins: tuple[ProjectIRQueryBlockGrainOrigin, ...]
    grain_factors: tuple[ProjectGrainDomainFactor, ...]
    grain_dependencies: tuple[ProjectGrainDependencyFact, ...]
    window_evidence: tuple[ProjectIRQueryBlockWindowEvidence, ...]
    window_policies: tuple[ProjectIRQueryBlockWindowPolicy, ...]
    selected_window_scalars: tuple[ProjectIRQueryBlockScalarOutput, ...]
    hidden_window_evidence: tuple[ProjectIRQueryBlockWindowHiddenEvidence, ...]
    effect_evidence: tuple[ProjectIRQueryBlockInspectionEffect, ...]
    combined_reverse_uses: tuple[ProjectIRQueryBlockReverseUseEntry, ...]
    combined_topological_order: tuple[ProjectIRPlanNodeOccurrence, ...]
    combined_reachability: tuple[ProjectIRReachabilityEntry, ...]

    def __post_init__(self) -> None:
        bundle = self.analysis_bundle
        root = (
            bundle.root if type(bundle) is ProjectIRQueryBlockAnalysisBundle else None
        )
        if (
            type(bundle) is not ProjectIRQueryBlockAnalysisBundle
            or bundle.verification.status
            is not ProjectIRQueryBlockVerificationStatus.VERIFIED
            or bundle.verification.issues
            or root is None
            or self.verification is not bundle.verification
            or self.root is not root
            or self.completed is not root.completed
            or self.project_completion is not root.completed.completion
            or self.effective_output_completion is not root.completed.effective_outputs
            or self.phase62_verification is not root.completed.verification
            or self.phase62_root is not root.completed.verification.root
            or self.base_plan is not root.base_plan
            or self.join_stage is not root.join_stage
            or self.combined_reverse_uses is not bundle.combined_reverse_uses
            or self.combined_topological_order is not bundle.combined_topological_order
            or self.combined_reachability is not bundle.combined_reachability
        ):
            raise ValueError(
                "Query-block inspection requires one exact VERIFIED analysis bundle."
            )
        expected = _runtime_sections(root)
        for name, retained in expected.items():
            actual = cast(tuple[object, ...], getattr(self, name))
            if not _same_objects(actual, retained):
                raise ValueError(
                    "Query-block inspection sections must retain exact canonical "
                    f"objects: {name}."
                )
        expected_summary = _inspection_summary(bundle, expected)
        if (
            self.summary != expected_summary
            or self.summary.scope is not expected_summary.scope
        ):
            raise ValueError("Query-block inspection summary lost exact authority.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRQueryBlockInspectionProduct:
    inspection: ProjectIRQueryBlockInspection
    document: ProjectQueryBlockIRPureDocument = field(init=False)
    canonical_bytes: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if type(self.inspection) is not ProjectIRQueryBlockInspection:
            raise TypeError("Query-block product requires an exact inspection.")
        document = _project_query_block_ir_document(self.inspection)
        outcome = evaluate_project_query_block_ir_document(document)
        if (
            outcome.status is not ProjectQueryBlockIRPureStatus.OK
            or outcome.canonical_bytes is None
        ):
            raise ValueError(
                "Authority-derived query-block inspection must evaluate exactly: "
                f"{outcome.status.value} at {outcome.record_position}:"
                f"{outcome.field_position}."
            )
        object.__setattr__(self, "document", document)
        object.__setattr__(self, "canonical_bytes", outcome.canonical_bytes)


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _entry_result_properties(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectIRQueryBlockResultProperties, ...]:
    if type(entry) is ProjectIRReusedEffectiveOutput:
        return (entry.active_properties,)
    if type(entry) is ProjectIRReboundExistingOutput:
        return entry.row_properties
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return entry.row_properties
    if type(entry) is ProjectIRQueryBlockTerminal:
        return ()
    raise TypeError("Query-block inspection encountered an unknown entry.")


def _entry_operators(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectIRQueryBlockInspectionOperator, ...]:
    if type(entry) is ProjectIRReboundExistingOutput:
        return cast(
            tuple[ProjectIRQueryBlockInspectionOperator, ...],
            entry.rebuilt_fragment.logical_stage.operators,
        )
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return cast(tuple[ProjectIRQueryBlockInspectionOperator, ...], entry.operators)
    return ()


def _entry_effects(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectIRQueryBlockInspectionEffect, ...]:
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return cast(tuple[ProjectIRQueryBlockInspectionEffect, ...], entry.effects)
    return tuple(
        cast(ProjectIRQueryBlockInspectionEffect, properties.effect)
        for properties in _entry_result_properties(entry)
    )


def _entry_relation_inputs(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectIRQueryBlockRelationInputEdge, ...]:
    if type(entry) is ProjectIRReboundExistingOutput:
        return (entry.relation_input,)
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return () if entry.relation_input is None else (entry.relation_input,)
    return ()


def _entry_active_roots(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[
    tuple[
        ProjectIRQueryBlockInspectionActiveOutput,
        ProjectIRQueryBlockResultProperties,
    ],
    ...,
]:
    if type(entry) is ProjectIRReusedEffectiveOutput:
        return ((entry.active_output, entry.active_properties),)
    if type(entry) is ProjectIRReboundExistingOutput:
        return ((entry.active_output, entry.active_properties),)
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return ((entry.active_output, entry.active_properties),)
    return ()


def _runtime_sections(
    root: ProjectIRQueryBlockSnapshot,
) -> dict[str, tuple[object, ...]]:
    entries = root.entries
    reused = tuple(
        entry for entry in entries if type(entry) is ProjectIRReusedEffectiveOutput
    )
    rebound = tuple(
        entry for entry in entries if type(entry) is ProjectIRReboundExistingOutput
    )
    completed = tuple(
        entry for entry in entries if type(entry) is ProjectIRCompletedQueryBlockOutput
    )
    terminals = tuple(
        entry for entry in entries if type(entry) is ProjectIRQueryBlockTerminal
    )
    active_pairs = tuple(
        pair for entry in entries for pair in _entry_active_roots(entry)
    )
    result_properties = tuple(
        properties
        for entry in entries
        for properties in _entry_result_properties(entry)
    )
    relational = tuple(item.relational for item in result_properties)
    operators = tuple(
        operator for entry in entries for operator in _entry_operators(entry)
    )
    windows = tuple(
        cast(ProjectIRQueryBlockWindowEvidence, operator.evidence)
        for operator in operators
        if type(operator) is ProjectIRQueryBlockOperatorOccurrence
        and type(operator.evidence) is ProjectIRQueryBlockWindowEvidence
    )
    row_outputs = tuple(output for entry in completed for output in entry.row_outputs)
    scalar_outputs = tuple(
        output for entry in completed for output in entry.scalar_outputs
    )
    base = root.base_plan.structural_stage
    join = root.join_stage.structural
    values: dict[str, tuple[object, ...]] = {
        "owners": root.owners,
        "dependencies": root.dependencies,
        "schedule": root.schedule,
        "entries": entries,
        "reused_entries": reused,
        "rebound_entries": rebound,
        "completed_entries": completed,
        "terminals": terminals,
        "terminal_blockers": tuple(entry.blocker for entry in terminals),
        "active_outputs": tuple(pair[0] for pair in active_pairs),
        "active_properties": tuple(pair[1] for pair in active_pairs),
        "combined_nodes": (*base.nodes, *join.nodes, *root.structural.nodes),
        "combined_outputs": (*base.outputs, *join.outputs, *root.structural.outputs),
        "combined_input_slots": (
            *base.input_slots,
            *join.input_slots,
            *root.structural.input_slots,
        ),
        "combined_uses": (*base.uses, *join.uses, *root.structural.uses),
        "slice14_nodes": root.structural.nodes,
        "slice14_outputs": root.structural.outputs,
        "slice14_input_slots": root.structural.input_slots,
        "slice14_uses": root.structural.uses,
        "operators": operators,
        "relation_inputs": tuple(
            edge for entry in entries for edge in _entry_relation_inputs(entry)
        ),
        "query_block_row_outputs": row_outputs,
        "query_block_scalar_outputs": scalar_outputs,
        "query_block_row_fields": tuple(
            row_field for output in row_outputs for row_field in output.row_shape.fields
        ),
        "final_field_identities": tuple(
            row_field.final_identity
            for output in row_outputs
            for row_field in output.row_shape.fields
            if row_field.final_identity is not None
        ),
        "result_properties": result_properties,
        "relational_properties": relational,
        "relational_fields": tuple(
            field for properties in relational for field in properties.fields
        ),
        "value_classes": tuple(
            value_class
            for properties in relational
            for value_class in properties.value_classes
        ),
        "candidate_keys": tuple(
            key for properties in relational for key in properties.keys
        ),
        "value_fds": tuple(fd for properties in relational for fd in properties.fds),
        "fd_indexes": tuple(properties.fd_index for properties in relational),
        "grain_origins": root.grain_origins.origins,
        "grain_factors": tuple(
            factor for properties in relational for factor in properties.grain.factors
        ),
        "grain_dependencies": tuple(
            dependency
            for properties in relational
            for dependency in properties.grain.dependencies
        ),
        "window_evidence": windows,
        "window_policies": tuple(
            policy for entry in completed for policy in entry.window_policies
        ),
        "selected_window_scalars": tuple(
            output for output in scalar_outputs if output.final_identity is None
        ),
        "hidden_window_evidence": tuple(
            evidence for window in windows for evidence in window.hidden
        ),
        "effect_evidence": tuple(
            effect for entry in entries for effect in _entry_effects(entry)
        ),
    }
    return values


def _inspection_summary(
    bundle: ProjectIRQueryBlockAnalysisBundle,
    sections: dict[str, tuple[object, ...]],
) -> ProjectIRQueryBlockInspectionSummary:
    return ProjectIRQueryBlockInspectionSummary(
        scope=bundle.root.structural.starting_allocation.scope,
        owner_count=len(sections["owners"]),
        entry_count=len(sections["entries"]),
        terminal_count=len(sections["terminals"]),
        node_count=len(sections["combined_nodes"]),
        output_count=len(sections["combined_outputs"]),
        input_slot_count=len(sections["combined_input_slots"]),
        use_count=len(sections["combined_uses"]),
        operator_count=len(sections["operators"]),
        row_field_count=len(sections["query_block_row_fields"]),
        relational_property_count=len(sections["relational_properties"]),
        grain_origin_count=len(sections["grain_origins"]),
        analysis_entry_count=(
            len(bundle.combined_reverse_uses)
            + len(bundle.combined_topological_order)
            + len(bundle.combined_reachability)
        ),
    )


def _position(values: tuple[object, ...], subject: object, label: str) -> int:
    matches = tuple(position for position, item in enumerate(values) if item is subject)
    if len(matches) != 1:
        raise ValueError(f"Portable projection requires one exact {label}.")
    return matches[0]


def _portable_ref(
    domain: ProjectQueryBlockIRPortableRefDomain,
    position: int,
) -> ProjectQueryBlockIRPortableRef:
    return ProjectQueryBlockIRPortableRef(domain=domain, position=position)


def _runtime_ref(value: object) -> ProjectQueryBlockIRPortableRef:
    if type(value) is ProjectIRPlanNodeRef:
        domain = ProjectQueryBlockIRPortableRefDomain.PLAN_NODE
    elif type(value) is ProjectIROutputValueRef:
        domain = ProjectQueryBlockIRPortableRefDomain.OUTPUT_VALUE
    elif type(value) is ProjectIRInputSlotRef:
        domain = ProjectQueryBlockIRPortableRefDomain.INPUT_SLOT
    elif type(value) is ProjectIRUseRef:
        domain = ProjectQueryBlockIRPortableRefDomain.USE
    else:
        raise TypeError("Portable projection requires one exact runtime ref.")
    return _portable_ref(domain, value.position)


def _optional_ref(
    value: ProjectQueryBlockIRPortableRef | None,
) -> ProjectQueryBlockIRPureValue:
    return (
        PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
        if value is None
        else project_query_block_ir_pure_ref(value)
    )


def _optional_enumeration(value: str | None) -> ProjectQueryBlockIRPureValue:
    return (
        PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
        if value is None
        else project_query_block_ir_pure_enumeration(value)
    )


def _optional_integer(value: int | None) -> ProjectQueryBlockIRPureValue:
    return (
        PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
        if value is None
        else project_query_block_ir_pure_integer(value)
    )


def _record(
    records: list[ProjectQueryBlockIRPureRecord],
    kind: ProjectQueryBlockIRRecordKind,
    *fields: tuple[str, ProjectQueryBlockIRPureValue],
) -> None:
    records.append(
        ProjectQueryBlockIRPureRecord(
            kind=kind,
            fields=tuple(
                ProjectQueryBlockIRPureField(key=key, value=value)
                for key, value in fields
            ),
        )
    )


def _owner_ref(
    inspection: ProjectIRQueryBlockInspection,
    owner: ProjectDeclarationOccurrence,
) -> ProjectQueryBlockIRPortableRef:
    return _portable_ref(
        ProjectQueryBlockIRPortableRefDomain.OWNER_ENTRY,
        _position(cast(tuple[object, ...], inspection.owners), owner, "owner"),
    )


def _owner_identity_ref(
    inspection: ProjectIRQueryBlockInspection,
    identity: ProjectDeclarationOccurrenceIdentity,
) -> ProjectQueryBlockIRPortableRef:
    matches = tuple(
        owner for owner in inspection.owners if _declaration_identity(owner) == identity
    )
    if len(matches) != 1:
        raise ValueError("Portable field identity requires one exact owner.")
    return _owner_ref(inspection, matches[0])


def _operator_ref(
    inspection: ProjectIRQueryBlockInspection,
    operator: ProjectIRQueryBlockInspectionOperator,
) -> ProjectQueryBlockIRPortableRef:
    return _portable_ref(
        ProjectQueryBlockIRPortableRefDomain.OPERATOR,
        _position(
            cast(tuple[object, ...], inspection.operators),
            operator,
            "operator",
        ),
    )


def _result_property_ref(
    inspection: ProjectIRQueryBlockInspection,
    properties: ProjectIRQueryBlockResultProperties,
) -> ProjectQueryBlockIRPortableRef:
    return _portable_ref(
        ProjectQueryBlockIRPortableRefDomain.RELATIONAL_PROPERTY,
        _position(
            cast(tuple[object, ...], inspection.result_properties),
            properties,
            "result properties",
        ),
    )


def _local_ref(
    inspection: ProjectIRQueryBlockInspection,
    properties: ProjectIRQueryBlockResultProperties,
    subject: object,
    *,
    domain: ProjectQueryBlockIRPortableRefDomain,
    attribute: str,
    label: str,
) -> ProjectQueryBlockIRPortableRef:
    property_position = _position(
        cast(tuple[object, ...], inspection.result_properties),
        properties,
        "result properties",
    )
    local_values = cast(tuple[object, ...], getattr(properties.relational, attribute))
    local_position = _position(local_values, subject, label)
    preceding = sum(
        len(cast(tuple[object, ...], getattr(item.relational, attribute)))
        for item in inspection.result_properties[:property_position]
    )
    return _portable_ref(domain, preceding + local_position)


def _field_ref(
    inspection: ProjectIRQueryBlockInspection,
    properties: ProjectIRQueryBlockResultProperties,
    field: ProjectIROutputFieldOccurrence,
) -> ProjectQueryBlockIRPortableRef:
    return _local_ref(
        inspection,
        properties,
        field,
        domain=ProjectQueryBlockIRPortableRefDomain.ROW_FIELD,
        attribute="fields",
        label="relational field",
    )


def _class_ref(
    inspection: ProjectIRQueryBlockInspection,
    properties: ProjectIRQueryBlockResultProperties,
    value_class: ProjectIROutputValueClass,
) -> ProjectQueryBlockIRPortableRef:
    return _local_ref(
        inspection,
        properties,
        value_class,
        domain=ProjectQueryBlockIRPortableRefDomain.VALUE_CLASS,
        attribute="value_classes",
        label="value class",
    )


def _key_ref(
    inspection: ProjectIRQueryBlockInspection,
    properties: ProjectIRQueryBlockResultProperties,
    key: ProjectIROutputCandidateKey,
) -> ProjectQueryBlockIRPortableRef:
    return _local_ref(
        inspection,
        properties,
        key,
        domain=ProjectQueryBlockIRPortableRefDomain.CANDIDATE_KEY,
        attribute="keys",
        label="candidate key",
    )


def _fd_ref(
    inspection: ProjectIRQueryBlockInspection,
    properties: ProjectIRQueryBlockResultProperties,
    fd: ProjectIROutputValueFD,
) -> ProjectQueryBlockIRPortableRef:
    return _local_ref(
        inspection,
        properties,
        fd,
        domain=ProjectQueryBlockIRPortableRefDomain.VALUE_FD,
        attribute="fds",
        label="value FD",
    )


def _factor_ref(
    inspection: ProjectIRQueryBlockInspection,
    properties: ProjectIRQueryBlockResultProperties,
    factor: ProjectGrainDomainFactor,
) -> ProjectQueryBlockIRPortableRef:
    property_position = _position(
        cast(tuple[object, ...], inspection.result_properties),
        properties,
        "result properties",
    )
    local_position = _position(
        cast(tuple[object, ...], properties.relational.grain.factors),
        factor,
        "grain factor",
    )
    preceding = sum(
        len(item.relational.grain.factors)
        for item in inspection.result_properties[:property_position]
    )
    return _portable_ref(
        ProjectQueryBlockIRPortableRefDomain.GRAIN_FACTOR,
        preceding + local_position,
    )


def _factor_identity_refs(
    inspection: ProjectIRQueryBlockInspection,
    properties: ProjectIRQueryBlockResultProperties,
    identities: tuple[ProjectGrainFactorIdentity, ...],
) -> tuple[ProjectQueryBlockIRPortableRef, ...]:
    values: list[ProjectQueryBlockIRPortableRef] = []
    for identity in identities:
        matches = tuple(
            factor
            for factor in properties.relational.grain.factors
            if factor.identity is identity
        )
        if len(matches) != 1:
            raise ValueError("Portable grain dependency lost one exact factor.")
        values.append(_factor_ref(inspection, properties, matches[0]))
    return tuple(values)


def _entry_for_properties(
    inspection: ProjectIRQueryBlockInspection,
    properties: ProjectIRQueryBlockResultProperties,
) -> ProjectIRQueryBlockEntry:
    matches = tuple(
        entry
        for entry in inspection.entries
        if any(candidate is properties for candidate in _entry_result_properties(entry))
    )
    if len(matches) != 1:
        raise ValueError("Portable result properties require one exact entry.")
    return matches[0]


def _entry_for_operator(
    inspection: ProjectIRQueryBlockInspection,
    operator: ProjectIRQueryBlockInspectionOperator,
) -> ProjectIRQueryBlockEntry:
    matches = tuple(
        entry
        for entry in inspection.entries
        if any(candidate is operator for candidate in _entry_operators(entry))
    )
    if len(matches) != 1:
        raise ValueError("Portable operator requires one exact entry.")
    return matches[0]


def _entry_for_output(
    inspection: ProjectIRQueryBlockInspection,
    output: ProjectIROutputValueOccurrence,
) -> ProjectIRQueryBlockEntry | None:
    matches = tuple(
        entry
        for entry in inspection.entries
        if any(
            properties.output.occurrence is output
            for properties in _entry_result_properties(entry)
        )
        or (
            type(entry) is ProjectIRCompletedQueryBlockOutput
            and any(item.occurrence is output for item in entry.scalar_outputs)
        )
        or (
            type(entry) is ProjectIRReboundExistingOutput
            and any(
                item is output
                for item in entry.rebuilt_fragment.structural_stage.outputs
            )
        )
    )
    if len(matches) > 1:
        raise ValueError("Portable output cannot belong to multiple entries.")
    return None if not matches else matches[0]


def _entry_for_use(
    inspection: ProjectIRQueryBlockInspection,
    use: ProjectIRQueryBlockInspectionUse,
) -> ProjectIRQueryBlockEntry | None:
    matches = tuple(
        entry
        for entry in inspection.entries
        if any(edge.use is use for edge in _entry_relation_inputs(entry))
        or (
            type(entry) is ProjectIRReboundExistingOutput
            and any(
                candidate is use
                for candidate in entry.rebuilt_fragment.structural_stage.uses
            )
        )
        or (
            type(entry) is ProjectIRCompletedQueryBlockOutput
            and any(candidate is use for candidate in entry.uses)
        )
    )
    if len(matches) > 1:
        raise ValueError("Portable use cannot belong to multiple entries.")
    return None if not matches else matches[0]


def _owner_fields(
    owner: ProjectDeclarationOccurrence,
) -> tuple[tuple[str, ProjectQueryBlockIRPureValue], ...]:
    identity = owner.identity
    return (
        ("module_path", project_query_block_ir_pure_text(identity.module_path)),
        (
            "module_position",
            project_query_block_ir_pure_integer(owner.module_position),
        ),
        (
            "namespace",
            project_query_block_ir_pure_enumeration(identity.namespace.value),
        ),
        (
            "declaration_kind",
            project_query_block_ir_pure_enumeration(identity.declaration_kind.value),
        ),
        ("declared_name", project_query_block_ir_pure_text(identity.declared_name)),
        (
            "declaration_position",
            project_query_block_ir_pure_integer(owner.declaration_position),
        ),
    )


def _entry_variant(entry: ProjectIRQueryBlockEntry) -> str:
    if type(entry) is ProjectIRReusedEffectiveOutput:
        return "reused"
    if type(entry) is ProjectIRReboundExistingOutput:
        return "rebound"
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return "completed"
    if type(entry) is ProjectIRQueryBlockTerminal:
        return "terminal"
    raise TypeError("Portable projection encountered an unknown entry.")


def _active_values(
    inspection: ProjectIRQueryBlockInspection,
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectQueryBlockIRPureValue, ProjectQueryBlockIRPureValue]:
    roots = _entry_active_roots(entry)
    if not roots:
        return PROJECT_QUERY_BLOCK_IR_PURE_ABSENT, PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
    if len(roots) != 1:
        raise ValueError("Portable entry requires one explicit active root pair.")
    output, properties = roots[0]
    return (
        project_query_block_ir_pure_ref(_runtime_ref(output.occurrence.ref)),
        project_query_block_ir_pure_ref(_result_property_ref(inspection, properties)),
    )


def _terminal_values(
    inspection: ProjectIRQueryBlockInspection,
    entry: ProjectIRQueryBlockEntry,
) -> tuple[
    ProjectQueryBlockIRPureValue,
    ProjectQueryBlockIRPureValue,
    ProjectQueryBlockIRPureValue,
    ProjectQueryBlockIRPureValue,
]:
    if type(entry) is not ProjectIRQueryBlockTerminal:
        return (
            PROJECT_QUERY_BLOCK_IR_PURE_ABSENT,
            PROJECT_QUERY_BLOCK_IR_PURE_ABSENT,
            PROJECT_QUERY_BLOCK_IR_PURE_ABSENT,
            PROJECT_QUERY_BLOCK_IR_PURE_ABSENT,
        )
    blocker_entry = tuple(
        candidate for candidate in inspection.terminals if candidate is entry.blocker
    )
    if len(blocker_entry) > 1:
        raise ValueError("Portable terminal blocker is not unique.")
    blocker_uses = (
        cast(tuple[ProjectIRJoinInputUseOccurrence, ...], entry.blocker)
        if type(entry.blocker) is tuple
        and all(type(item) is ProjectIRJoinInputUseOccurrence for item in entry.blocker)
        else ()
    )
    return (
        project_query_block_ir_pure_enumeration(entry.reason.value),
        project_query_block_ir_pure_enumeration(type(entry.blocker).__name__),
        _optional_ref(
            None
            if not blocker_entry
            else _owner_ref(inspection, blocker_entry[0].owner)
        ),
        project_query_block_ir_pure_refs(
            tuple(_runtime_ref(use.ref) for use in blocker_uses)
        ),
    )


def _entry_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    for position, entry in enumerate(inspection.entries):
        active_output, active_property = _active_values(inspection, entry)
        relation_inputs = _entry_relation_inputs(entry)
        if len(relation_inputs) > 1:
            raise ValueError("Portable entry cannot retain multiple relation inputs.")
        relation_input = None if not relation_inputs else relation_inputs[0]
        terminal_reason, blocker_kind, blocker_entry, blocker_uses = _terminal_values(
            inspection, entry
        )
        _record(
            records,
            ProjectQueryBlockIRRecordKind.OWNER_ENTRY,
            (
                "ref",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.OWNER_ENTRY,
                        position,
                    )
                ),
            ),
            *_owner_fields(entry.owner),
            ("variant", project_query_block_ir_pure_enumeration(_entry_variant(entry))),
            ("active_output", active_output),
            ("active_property", active_property),
            (
                "relation_input_owner",
                _optional_ref(
                    None
                    if relation_input is None
                    else _owner_ref(inspection, relation_input.dependency.target)
                ),
            ),
            (
                "relation_input_use",
                _optional_ref(
                    None
                    if relation_input is None
                    else _runtime_ref(relation_input.use.ref)
                ),
            ),
            (
                "compatibility",
                _optional_enumeration(
                    None
                    if relation_input is None
                    else relation_input.compatibility.status.value
                ),
            ),
            ("terminal_reason", terminal_reason),
            ("blocker_kind", blocker_kind),
            ("blocker_entry", blocker_entry),
            ("blocker_uses", blocker_uses),
        )


def _dependency_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    for dependency in inspection.dependencies:
        _record(
            records,
            ProjectQueryBlockIRRecordKind.DEPENDENCY,
            (
                "consumer",
                project_query_block_ir_pure_ref(
                    _owner_ref(inspection, dependency.consumer)
                ),
            ),
            (
                "target",
                project_query_block_ir_pure_ref(
                    _owner_ref(inspection, dependency.target)
                ),
            ),
            (
                "ordinal",
                project_query_block_ir_pure_integer(dependency.dependency_ordinal),
            ),
            (
                "evidence_kind",
                project_query_block_ir_pure_enumeration(
                    type(dependency.evidence).__name__
                ),
            ),
        )


def _stage_for_node(
    inspection: ProjectIRQueryBlockInspection,
    node: ProjectIRPlanNodeOccurrence,
) -> str:
    if any(item is node for item in inspection.base_plan.structural_stage.nodes):
        return "phase61"
    if any(item is node for item in inspection.join_stage.structural.nodes):
        return "phase62"
    if any(item is node for item in inspection.slice14_nodes):
        return "phase63"
    raise ValueError("Portable node is outside the retained root chain.")


def _properties_for_output(
    inspection: ProjectIRQueryBlockInspection,
    output: ProjectIROutputValueOccurrence,
) -> ProjectIRQueryBlockResultProperties | None:
    matches = tuple(
        properties
        for properties in inspection.result_properties
        if properties.output.occurrence is output
    )
    if len(matches) > 1:
        raise ValueError("Portable output has multiple result-property carriers.")
    return None if not matches else matches[0]


def _scalar_for_output(
    inspection: ProjectIRQueryBlockInspection,
    output: ProjectIROutputValueOccurrence,
) -> ProjectIRQueryBlockScalarOutput | None:
    matches = tuple(
        scalar
        for scalar in inspection.query_block_scalar_outputs
        if scalar.occurrence is output
    )
    if len(matches) > 1:
        raise ValueError("Portable output has multiple scalar carriers.")
    return None if not matches else matches[0]


def _output_kind(
    inspection: ProjectIRQueryBlockInspection,
    output: ProjectIROutputValueOccurrence,
) -> str:
    scalar = _scalar_for_output(inspection, output)
    if scalar is not None:
        return "query_block_scalar"
    properties = _properties_for_output(inspection, output)
    if properties is not None:
        if type(properties.output) is ProjectIRQueryBlockRowOutput:
            return "query_block_row"
        return "relation_row"
    if any(item is output for item in inspection.base_plan.structural_stage.outputs):
        return "phase61_output"
    if any(item is output for item in inspection.join_stage.structural.outputs):
        return "phase62_output"
    owner = _entry_for_output(inspection, output)
    if type(owner) is ProjectIRReboundExistingOutput:
        return "rebound_auxiliary"
    raise ValueError("Slice-14 output lost its typed carrier.")


def _scalar_field_ref(
    inspection: ProjectIRQueryBlockInspection,
    scalar: ProjectIRQueryBlockScalarOutput,
) -> ProjectQueryBlockIRPortableRef:
    matches = tuple(
        properties
        for properties in inspection.result_properties
        if properties.output is scalar.row_output
    )
    if len(matches) != 1:
        raise ValueError("Portable scalar requires one exact row property.")
    properties = matches[0]
    return _field_ref(
        inspection,
        properties,
        properties.relational.fields[scalar.field_position],
    )


def _use_kind(use: ProjectIRQueryBlockInspectionUse) -> str:
    if type(use) is ProjectIRJoinInputUseOccurrence:
        return "join_input"
    if type(use) is ProjectIROperatorFlowUseOccurrence:
        return "operator_flow"
    if type(use) is ProjectIRUseOccurrence:
        return use.role.value
    raise TypeError("Portable use requires one closed runtime family.")


def _structural_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    for node in inspection.combined_nodes:
        _record(
            records,
            ProjectQueryBlockIRRecordKind.NODE,
            ("ref", project_query_block_ir_pure_ref(_runtime_ref(node.ref))),
            (
                "stage",
                project_query_block_ir_pure_enumeration(
                    _stage_for_node(inspection, node)
                ),
            ),
        )
    for output in inspection.combined_outputs:
        owner = _entry_for_output(inspection, output)
        scalar = _scalar_for_output(inspection, output)
        _record(
            records,
            ProjectQueryBlockIRRecordKind.OUTPUT,
            ("ref", project_query_block_ir_pure_ref(_runtime_ref(output.ref))),
            (
                "producer",
                project_query_block_ir_pure_ref(_runtime_ref(output.producer.ref)),
            ),
            (
                "kind",
                project_query_block_ir_pure_enumeration(
                    _output_kind(inspection, output)
                ),
            ),
            (
                "owner",
                _optional_ref(
                    None if owner is None else _owner_ref(inspection, owner.owner)
                ),
            ),
            (
                "row_field",
                _optional_ref(
                    None if scalar is None else _scalar_field_ref(inspection, scalar)
                ),
            ),
        )
    for slot in inspection.combined_input_slots:
        _record(
            records,
            ProjectQueryBlockIRRecordKind.INPUT_SLOT,
            ("ref", project_query_block_ir_pure_ref(_runtime_ref(slot.ref))),
            (
                "consumer",
                project_query_block_ir_pure_ref(_runtime_ref(slot.consumer.ref)),
            ),
            ("ordinal", project_query_block_ir_pure_integer(slot.input_ordinal)),
        )
    for use in inspection.combined_uses:
        owner = _entry_for_use(inspection, use)
        _record(
            records,
            ProjectQueryBlockIRRecordKind.USE,
            ("ref", project_query_block_ir_pure_ref(_runtime_ref(use.ref))),
            (
                "output",
                project_query_block_ir_pure_ref(_runtime_ref(use.output.ref)),
            ),
            (
                "slot",
                project_query_block_ir_pure_ref(_runtime_ref(use.slot.ref)),
            ),
            ("kind", project_query_block_ir_pure_enumeration(_use_kind(use))),
            (
                "owner",
                _optional_ref(
                    None if owner is None else _owner_ref(inspection, owner.owner)
                ),
            ),
        )


def _operator_properties(
    entry: ProjectIRQueryBlockEntry,
    operator: ProjectIRQueryBlockInspectionOperator,
) -> ProjectIRQueryBlockResultProperties:
    if type(entry) is ProjectIRReboundExistingOutput:
        position = _position(
            cast(tuple[object, ...], entry.rebuilt_fragment.logical_stage.operators),
            operator,
            "rebound operator",
        )
        return entry.row_properties[position]
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        position = _position(
            cast(tuple[object, ...], entry.operators),
            operator,
            "completed operator",
        )
        return entry.row_properties[position]
    raise TypeError("Portable operator requires a concrete allocating entry.")


def _operator_provenance(entry: ProjectIRQueryBlockEntry) -> str:
    if type(entry) is ProjectIRReboundExistingOutput:
        return "rebound_historical"
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return (
            "no_join_replay"
            if type(entry.semantic_entry.root) is ProjectConcreteNoJoinReplay
            else "joined"
        )
    raise TypeError("Portable operator provenance requires an allocating entry.")


def _operator_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    for position, operator in enumerate(inspection.operators):
        entry = _entry_for_operator(inspection, operator)
        local_operators = _entry_operators(entry)
        ordinal = _position(
            cast(tuple[object, ...], local_operators), operator, "entry operator"
        )
        properties = _operator_properties(entry, operator)
        window = (
            cast(ProjectIRQueryBlockWindowEvidence, operator.evidence)
            if type(operator) is ProjectIRQueryBlockOperatorOccurrence
            and type(operator.evidence) is ProjectIRQueryBlockWindowEvidence
            else None
        )
        _record(
            records,
            ProjectQueryBlockIRRecordKind.OPERATOR,
            (
                "ref",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.OPERATOR, position
                    )
                ),
            ),
            (
                "owner",
                project_query_block_ir_pure_ref(_owner_ref(inspection, entry.owner)),
            ),
            ("ordinal", project_query_block_ir_pure_integer(ordinal)),
            ("node", project_query_block_ir_pure_ref(_runtime_ref(operator.node.ref))),
            (
                "row_output",
                project_query_block_ir_pure_ref(
                    _runtime_ref(properties.output.occurrence.ref)
                ),
            ),
            ("kind", project_query_block_ir_pure_enumeration(operator.kind.value)),
            (
                "evidence_kind",
                project_query_block_ir_pure_enumeration(
                    type(operator.evidence).__name__
                ),
            ),
            (
                "provenance",
                project_query_block_ir_pure_enumeration(_operator_provenance(entry)),
            ),
            (
                "selected_count",
                project_query_block_ir_pure_integer(
                    0 if window is None else len(window.selected)
                ),
            ),
            (
                "hidden_count",
                project_query_block_ir_pure_integer(
                    0 if window is None else len(window.hidden)
                ),
            ),
        )


def _final_field_identity(
    properties: ProjectIRQueryBlockResultProperties,
    field: ProjectIROutputFieldOccurrence,
) -> ProjectModuleRowFieldIdentity | None:
    output = properties.output
    if type(output) is ProjectIRQueryBlockRowOutput:
        return output.row_shape.fields[field.field_position].final_identity
    if type(output) is ProjectIRRelationRowOutput:
        row_field = output.row_shape.fields[field.field_position]
        if type(row_field) is ProjectIRRowField:
            return row_field.anchor.identity
    return None


def _field_provenance(
    properties: ProjectIRQueryBlockResultProperties,
    field_occurrence: ProjectIROutputFieldOccurrence,
) -> tuple[str, ProjectIRUseRef | None, tuple[ProjectIRPlanNodeRef, ...]]:
    row_field = properties.output.row_shape.fields[field_occurrence.field_position]
    if type(properties.output) is ProjectIRQueryBlockRowOutput:
        query_field = properties.output.row_shape.fields[
            field_occurrence.field_position
        ]
        introduction = (
            None
            if query_field.introduction_use is None
            else query_field.introduction_use.ref
        )
        return (
            type(query_field.semantic_source).__name__,
            introduction,
            query_field.nulling_joins,
        )
    return type(row_field).__name__, None, ()


def _field_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    for properties in inspection.result_properties:
        property_ref = _result_property_ref(inspection, properties)
        for field_occurrence in properties.relational.fields:
            identity = _final_field_identity(properties, field_occurrence)
            provenance = field_occurrence.evidence.provenance
            semantic_source_kind, introduction_use, nulling_joins = _field_provenance(
                properties, field_occurrence
            )
            _record(
                records,
                ProjectQueryBlockIRRecordKind.ROW_FIELD,
                (
                    "ref",
                    project_query_block_ir_pure_ref(
                        _field_ref(inspection, properties, field_occurrence)
                    ),
                ),
                ("property", project_query_block_ir_pure_ref(property_ref)),
                (
                    "field_position",
                    project_query_block_ir_pure_integer(
                        field_occurrence.field_position
                    ),
                ),
                (
                    "name",
                    project_query_block_ir_pure_text(field_occurrence.evidence.name),
                ),
                (
                    "nullability",
                    project_query_block_ir_pure_enumeration(
                        field_occurrence.effective_nullability.value
                    ),
                ),
                (
                    "provenance",
                    project_query_block_ir_pure_enumeration(
                        "absent" if provenance is None else provenance.kind.value
                    ),
                ),
                (
                    "semantic_source_kind",
                    project_query_block_ir_pure_enumeration(semantic_source_kind),
                ),
                (
                    "introduction_use",
                    _optional_ref(
                        None
                        if introduction_use is None
                        else _runtime_ref(introduction_use)
                    ),
                ),
                (
                    "nulling_joins",
                    project_query_block_ir_pure_refs(
                        tuple(_runtime_ref(ref) for ref in nulling_joins)
                    ),
                ),
                (
                    "final_owner",
                    _optional_ref(
                        None
                        if identity is None
                        else _owner_identity_ref(inspection, identity.owner)
                    ),
                ),
                (
                    "final_kind",
                    _optional_enumeration(
                        None if identity is None else identity.kind.value
                    ),
                ),
                (
                    "final_position",
                    _optional_integer(
                        None if identity is None else identity.field_position
                    ),
                ),
                (
                    "final_name",
                    (
                        PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                        if identity is None
                        else project_query_block_ir_pure_text(identity.name)
                    ),
                ),
            )


def _ordering(
    properties: ProjectIRQueryBlockResultProperties,
) -> tuple[str, tuple[str, ...]]:
    ordering = properties.ordering
    if ordering is None:
        return "absent", ()
    if type(ordering) is ProjectIRProvidedRelationOrdering:
        return "historical", tuple(
            "asc" if item.direction is None else item.direction
            for item in ordering.items
        )
    if type(ordering) is ProjectRelationOrdering:
        return "relation", tuple(item.direction.value for item in ordering.items)
    raise TypeError("Portable ordering requires one closed authority.")


def _property_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    origin_refs = tuple(
        _portable_ref(ProjectQueryBlockIRPortableRefDomain.GRAIN_ORIGIN, position)
        for position in range(len(inspection.grain_origins))
    )
    for properties in inspection.result_properties:
        relational = properties.relational
        property_ref = _result_property_ref(inspection, properties)
        entry = _entry_for_properties(inspection, properties)
        ordering_kind, directions = _ordering(properties)
        local_factor_refs = tuple(
            _factor_ref(inspection, properties, factor)
            for factor in relational.grain.factors
        )
        _record(
            records,
            ProjectQueryBlockIRRecordKind.RELATIONAL_PROPERTY,
            ("ref", project_query_block_ir_pure_ref(property_ref)),
            (
                "owner",
                project_query_block_ir_pure_ref(_owner_ref(inspection, entry.owner)),
            ),
            (
                "ordinal",
                project_query_block_ir_pure_integer(
                    _position(
                        cast(
                            tuple[object, ...],
                            _entry_result_properties(entry),
                        ),
                        properties,
                        "entry result properties",
                    )
                ),
            ),
            (
                "output",
                project_query_block_ir_pure_ref(
                    _runtime_ref(properties.output.occurrence.ref)
                ),
            ),
            (
                "multiplicity",
                project_query_block_ir_pure_enumeration(properties.multiplicity.value),
            ),
            (
                "fields",
                project_query_block_ir_pure_refs(
                    tuple(
                        _field_ref(inspection, properties, field)
                        for field in relational.fields
                    )
                ),
            ),
            (
                "value_classes",
                project_query_block_ir_pure_refs(
                    tuple(
                        _class_ref(inspection, properties, value_class)
                        for value_class in relational.value_classes
                    )
                ),
            ),
            (
                "candidate_keys",
                project_query_block_ir_pure_refs(
                    tuple(
                        _key_ref(inspection, properties, key) for key in relational.keys
                    )
                ),
            ),
            (
                "value_fds",
                project_query_block_ir_pure_refs(
                    tuple(_fd_ref(inspection, properties, fd) for fd in relational.fds)
                ),
            ),
            (
                "fd_index_universe",
                project_query_block_ir_pure_refs(
                    tuple(
                        _class_ref(inspection, properties, value_class)
                        for value_class in relational.fd_index.universe
                    )
                ),
            ),
            (
                "fd_index_facts",
                project_query_block_ir_pure_refs(
                    tuple(
                        _fd_ref(inspection, properties, fd)
                        for fd in relational.fd_index.facts
                    )
                ),
            ),
            (
                "grain_state",
                project_query_block_ir_pure_enumeration(relational.grain.state.value),
            ),
            (
                "grain_origins",
                project_query_block_ir_pure_refs(
                    origin_refs
                    if relational.grain.origin_set is inspection.root.grain_origins
                    else ()
                ),
            ),
            (
                "grain_factors",
                project_query_block_ir_pure_refs(local_factor_refs),
            ),
            (
                "active_grain_factors",
                project_query_block_ir_pure_refs(
                    _factor_identity_refs(
                        inspection, properties, relational.grain.active
                    )
                ),
            ),
            (
                "ordering_kind",
                project_query_block_ir_pure_enumeration(ordering_kind),
            ),
            (
                "order_directions",
                project_query_block_ir_pure_enumerations(directions),
            ),
            (
                "cardinality_bound",
                _optional_integer(properties.row_count_upper_bound),
            ),
            (
                "determinism",
                project_query_block_ir_pure_enumeration(
                    properties.effect.determinism.value
                ),
            ),
            (
                "error_behavior",
                project_query_block_ir_pure_enumeration(
                    properties.effect.error_behavior.value
                ),
            ),
            (
                "side_effects",
                project_query_block_ir_pure_enumeration(
                    properties.effect.side_effects.value
                ),
            ),
            (
                "evaluation_count",
                project_query_block_ir_pure_enumeration(
                    properties.effect.evaluation_count.value
                ),
            ),
        )


def _relational_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    for properties in inspection.result_properties:
        property_ref = _result_property_ref(inspection, properties)
        relational = properties.relational
        for value_class in relational.value_classes:
            _record(
                records,
                ProjectQueryBlockIRRecordKind.VALUE_CLASS,
                (
                    "ref",
                    project_query_block_ir_pure_ref(
                        _class_ref(inspection, properties, value_class)
                    ),
                ),
                ("property", project_query_block_ir_pure_ref(property_ref)),
                (
                    "members",
                    project_query_block_ir_pure_refs(
                        tuple(
                            _field_ref(inspection, properties, member)
                            for member in value_class.members
                        )
                    ),
                ),
            )
    for properties in inspection.result_properties:
        property_ref = _result_property_ref(inspection, properties)
        for key in properties.relational.keys:
            _record(
                records,
                ProjectQueryBlockIRRecordKind.CANDIDATE_KEY,
                (
                    "ref",
                    project_query_block_ir_pure_ref(
                        _key_ref(inspection, properties, key)
                    ),
                ),
                ("property", project_query_block_ir_pure_ref(property_ref)),
                (
                    "determinants",
                    project_query_block_ir_pure_refs(
                        tuple(
                            _class_ref(inspection, properties, value_class)
                            for value_class in key.determinants
                        )
                    ),
                ),
                (
                    "strength",
                    project_query_block_ir_pure_enumeration(key.strength.value),
                ),
            )
    for properties in inspection.result_properties:
        property_ref = _result_property_ref(inspection, properties)
        for fd in properties.relational.fds:
            _record(
                records,
                ProjectQueryBlockIRRecordKind.VALUE_FD,
                (
                    "ref",
                    project_query_block_ir_pure_ref(
                        _fd_ref(inspection, properties, fd)
                    ),
                ),
                ("property", project_query_block_ir_pure_ref(property_ref)),
                (
                    "determinants",
                    project_query_block_ir_pure_refs(
                        tuple(
                            _class_ref(inspection, properties, value_class)
                            for value_class in fd.determinants
                        )
                    ),
                ),
                (
                    "dependents",
                    project_query_block_ir_pure_refs(
                        tuple(
                            _class_ref(inspection, properties, value_class)
                            for value_class in fd.dependents
                        )
                    ),
                ),
                (
                    "strength",
                    project_query_block_ir_pure_enumeration(fd.strength.value),
                ),
            )


def _base_factor_identity(
    identity: ProjectGrainFactorIdentity,
) -> ProjectSourceGrainFactorIdentity | ProjectGroupedGrainFactorIdentity:
    if type(identity) is ProjectJoinGrainFactorIdentity:
        return identity.base
    if type(identity) in {
        ProjectSourceGrainFactorIdentity,
        ProjectGroupedGrainFactorIdentity,
    }:
        return cast(
            ProjectSourceGrainFactorIdentity | ProjectGroupedGrainFactorIdentity,
            identity,
        )
    raise TypeError("Portable grain factor requires a closed identity.")


def _grain_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    for position, origin in enumerate(inspection.grain_origins):
        matching_factors = tuple(
            _factor_ref(inspection, properties, factor)
            for properties in inspection.result_properties
            for factor in properties.relational.grain.factors
            if origin.factor is not None and factor.identity is origin.factor
        )
        _record(
            records,
            ProjectQueryBlockIRRecordKind.GRAIN_ORIGIN,
            (
                "ref",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.GRAIN_ORIGIN,
                        position,
                    )
                ),
            ),
            (
                "operator",
                project_query_block_ir_pure_ref(_runtime_ref(origin.operator.ref)),
            ),
            ("kind", project_query_block_ir_pure_enumeration(origin.kind.value)),
            (
                "factors",
                project_query_block_ir_pure_refs(matching_factors),
            ),
        )
    for properties in inspection.result_properties:
        property_ref = _result_property_ref(inspection, properties)
        grain = properties.relational.grain
        for factor in grain.factors:
            identity = factor.identity
            base = _base_factor_identity(identity)
            grouped = base if type(base) is ProjectGroupedGrainFactorIdentity else None
            joined = (
                identity if type(identity) is ProjectJoinGrainFactorIdentity else None
            )
            _record(
                records,
                ProjectQueryBlockIRRecordKind.GRAIN_FACTOR,
                (
                    "ref",
                    project_query_block_ir_pure_ref(
                        _factor_ref(inspection, properties, factor)
                    ),
                ),
                ("property", project_query_block_ir_pure_ref(property_ref)),
                ("kind", project_query_block_ir_pure_enumeration(identity.kind.value)),
                (
                    "use_kind",
                    project_query_block_ir_pure_enumeration(
                        "join" if joined is not None else "direct"
                    ),
                ),
                (
                    "owner",
                    _optional_ref(_owner_identity_ref(inspection, base.owner)),
                ),
                (
                    "operator",
                    _optional_ref(
                        None if grouped is None else _runtime_ref(grouped.operator)
                    ),
                ),
                (
                    "introduction_use",
                    _optional_ref(
                        None
                        if joined is None
                        else _runtime_ref(joined.introduction_use)
                    ),
                ),
                (
                    "nulling_joins",
                    project_query_block_ir_pure_refs(
                        ()
                        if joined is None
                        else tuple(_runtime_ref(ref) for ref in joined.nulling_joins)
                    ),
                ),
                (
                    "active",
                    project_query_block_ir_pure_boolean(
                        any(item is identity for item in grain.active)
                    ),
                ),
            )
    for properties in inspection.result_properties:
        property_ref = _result_property_ref(inspection, properties)
        for dependency in properties.relational.grain.dependencies:
            _record(
                records,
                ProjectQueryBlockIRRecordKind.GRAIN_DEPENDENCY,
                ("property", project_query_block_ir_pure_ref(property_ref)),
                (
                    "determinants",
                    project_query_block_ir_pure_refs(
                        _factor_identity_refs(
                            inspection, properties, dependency.determinants
                        )
                    ),
                ),
                (
                    "dependents",
                    project_query_block_ir_pure_refs(
                        _factor_identity_refs(
                            inspection, properties, dependency.dependents
                        )
                    ),
                ),
            )


def _selected_scalar(
    entry: ProjectIRCompletedQueryBlockOutput,
    evidence: ProjectConcreteWindowComputation | ProjectModuleWindowOutputFact,
) -> ProjectIRQueryBlockScalarOutput:
    matches = tuple(
        scalar
        for scalar in entry.scalar_outputs
        if (
            type(evidence) is ProjectConcreteWindowComputation
            and type(scalar.semantic_source) is ProjectSelectedWindowResultBinding
            and scalar.semantic_source.computation is evidence
        )
        or (
            type(evidence) is ProjectModuleWindowOutputFact
            and scalar.semantic_source is evidence
        )
    )
    if len(matches) != 1:
        raise ValueError("Selected window evidence requires one exact scalar output.")
    return matches[0]


def _window_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    selected_records: list[
        tuple[
            ProjectIRQueryBlockInspectionOperator,
            ProjectIRQueryBlockEntry,
            int,
            ProjectIRQueryBlockScalarOutput,
            object,
        ]
    ] = []
    hidden_records: list[
        tuple[
            ProjectIRQueryBlockInspectionOperator,
            ProjectIRQueryBlockEntry,
            int,
            object,
        ]
    ] = []
    for operator in inspection.operators:
        if (
            type(operator) is not ProjectIRQueryBlockOperatorOccurrence
            or type(operator.evidence) is not ProjectIRQueryBlockWindowEvidence
        ):
            continue
        entry = _entry_for_operator(inspection, operator)
        if type(entry) is not ProjectIRCompletedQueryBlockOutput:
            raise ValueError("Window operator requires one exact completed entry.")
        window = operator.evidence
        selected_records.extend(
            (
                operator,
                entry,
                position,
                _selected_scalar(entry, evidence),
                evidence,
            )
            for position, evidence in enumerate(window.selected)
        )
        hidden_records.extend(
            (operator, entry, position, evidence)
            for position, evidence in enumerate(window.hidden)
        )
    for operator, entry, position, scalar, evidence in selected_records:
        _record(
            records,
            ProjectQueryBlockIRRecordKind.WINDOW_SELECTED,
            (
                "operator",
                project_query_block_ir_pure_ref(_operator_ref(inspection, operator)),
            ),
            (
                "owner",
                project_query_block_ir_pure_ref(_owner_ref(inspection, entry.owner)),
            ),
            ("ordinal", project_query_block_ir_pure_integer(position)),
            (
                "output",
                project_query_block_ir_pure_ref(_runtime_ref(scalar.occurrence.ref)),
            ),
            (
                "row_field",
                project_query_block_ir_pure_ref(_scalar_field_ref(inspection, scalar)),
            ),
            (
                "evidence_kind",
                project_query_block_ir_pure_enumeration(type(evidence).__name__),
            ),
        )
    for operator, entry, position, evidence in hidden_records:
        _record(
            records,
            ProjectQueryBlockIRRecordKind.WINDOW_HIDDEN,
            (
                "operator",
                project_query_block_ir_pure_ref(_operator_ref(inspection, operator)),
            ),
            (
                "owner",
                project_query_block_ir_pure_ref(_owner_ref(inspection, entry.owner)),
            ),
            ("ordinal", project_query_block_ir_pure_integer(position)),
            (
                "evidence_kind",
                project_query_block_ir_pure_enumeration(type(evidence).__name__),
            ),
        )


def _analysis_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    position = 0
    for entry in inspection.combined_reverse_uses:
        _record(
            records,
            ProjectQueryBlockIRRecordKind.ANALYSIS_REVERSE_USE,
            (
                "ref",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.ANALYSIS_ENTRY,
                        position,
                    )
                ),
            ),
            (
                "output",
                project_query_block_ir_pure_ref(_runtime_ref(entry.output.ref)),
            ),
            (
                "uses",
                project_query_block_ir_pure_refs(
                    tuple(_runtime_ref(use.ref) for use in entry.uses)
                ),
            ),
        )
        position += 1
    for topological_position, node in enumerate(inspection.combined_topological_order):
        _record(
            records,
            ProjectQueryBlockIRRecordKind.ANALYSIS_TOPOLOGICAL,
            (
                "ref",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.ANALYSIS_ENTRY,
                        position,
                    )
                ),
            ),
            (
                "position",
                project_query_block_ir_pure_integer(topological_position),
            ),
            ("node", project_query_block_ir_pure_ref(_runtime_ref(node.ref))),
        )
        position += 1
    for entry in inspection.combined_reachability:
        _record(
            records,
            ProjectQueryBlockIRRecordKind.ANALYSIS_REACHABILITY,
            (
                "ref",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.ANALYSIS_ENTRY,
                        position,
                    )
                ),
            ),
            (
                "source",
                project_query_block_ir_pure_ref(_runtime_ref(entry.source.ref)),
            ),
            (
                "reachable",
                project_query_block_ir_pure_refs(
                    tuple(_runtime_ref(node.ref) for node in entry.reachable)
                ),
            ),
        )
        position += 1


def _project_query_block_ir_document(
    inspection: ProjectIRQueryBlockInspection,
) -> ProjectQueryBlockIRPureDocument:
    if type(inspection) is not ProjectIRQueryBlockInspection:
        raise TypeError("Portable projection requires an exact inspection.")
    start = inspection.root.starting_allocation
    end = inspection.root.ending_allocation
    records: list[ProjectQueryBlockIRPureRecord] = []
    _record(
        records,
        ProjectQueryBlockIRRecordKind.HEADER,
        (
            "format",
            project_query_block_ir_pure_text(PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT),
        ),
        (
            "verification",
            project_query_block_ir_pure_enumeration(
                inspection.verification.status.value
            ),
        ),
        (
            "node_start",
            project_query_block_ir_pure_integer(start.next_plan_node_position),
        ),
        (
            "output_start",
            project_query_block_ir_pure_integer(start.next_output_value_position),
        ),
        (
            "slot_start",
            project_query_block_ir_pure_integer(start.next_input_slot_position),
        ),
        ("use_start", project_query_block_ir_pure_integer(start.next_use_position)),
        ("node_end", project_query_block_ir_pure_integer(end.next_plan_node_position)),
        (
            "output_end",
            project_query_block_ir_pure_integer(end.next_output_value_position),
        ),
        (
            "slot_end",
            project_query_block_ir_pure_integer(end.next_input_slot_position),
        ),
        ("use_end", project_query_block_ir_pure_integer(end.next_use_position)),
        (
            "schedule",
            project_query_block_ir_pure_refs(
                tuple(_owner_ref(inspection, owner) for owner in inspection.schedule)
            ),
        ),
    )
    _entry_records(inspection, records)
    _dependency_records(inspection, records)
    _structural_records(inspection, records)
    _operator_records(inspection, records)
    _field_records(inspection, records)
    _property_records(inspection, records)
    _relational_records(inspection, records)
    _grain_records(inspection, records)
    _window_records(inspection, records)
    _analysis_records(inspection, records)
    _record(records, ProjectQueryBlockIRRecordKind.END)
    return ProjectQueryBlockIRPureDocument(
        format_marker=PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT,
        records=tuple(records),
    )


def _derive_project_query_block_ir_inspection(
    bundle: ProjectIRQueryBlockAnalysisBundle,
) -> ProjectIRQueryBlockInspection:
    """Observe one exact VERIFIED Slice-14 bundle without rerunning producers."""

    if type(bundle) is not ProjectIRQueryBlockAnalysisBundle:
        raise TypeError("Query-block inspection requires an exact analysis bundle.")
    if (
        bundle.verification.status is not ProjectIRQueryBlockVerificationStatus.VERIFIED
        or bundle.verification.issues
        or bundle.root is not bundle.verification.root
    ):
        raise ValueError("Query-block inspection requires one VERIFIED bundle.")
    root = bundle.root
    sections = _runtime_sections(root)
    return ProjectIRQueryBlockInspection(
        analysis_bundle=bundle,
        summary=_inspection_summary(bundle, sections),
        verification=bundle.verification,
        root=root,
        completed=root.completed,
        project_completion=root.completed.completion,
        effective_output_completion=root.completed.effective_outputs,
        phase62_verification=root.completed.verification,
        phase62_root=root.completed.verification.root,
        base_plan=root.base_plan,
        join_stage=root.join_stage,
        combined_reverse_uses=bundle.combined_reverse_uses,
        combined_topological_order=bundle.combined_topological_order,
        combined_reachability=bundle.combined_reachability,
        **cast(dict[str, object], sections),  # pyright: ignore[reportArgumentType]
    )


def build_project_query_block_ir_inspection(
    bundle: ProjectIRQueryBlockAnalysisBundle,
) -> ProjectIRQueryBlockInspectionProduct:
    """Observe and project one exact VERIFIED Slice-14 analysis bundle."""

    return ProjectIRQueryBlockInspectionProduct(
        inspection=_derive_project_query_block_ir_inspection(bundle)
    )


def serialize_project_query_block_ir_inspection(
    inspection: ProjectIRQueryBlockInspection,
) -> bytes:
    if type(inspection) is not ProjectIRQueryBlockInspection:
        raise TypeError("Canonical serialization requires an exact inspection.")
    outcome = evaluate_project_query_block_ir_document(
        _project_query_block_ir_document(inspection)
    )
    if (
        outcome.status is not ProjectQueryBlockIRPureStatus.OK
        or outcome.canonical_bytes is None
    ):
        raise ValueError(
            "Query-block inspection did not pass pure evaluation: "
            f"{outcome.status.value} at {outcome.record_position}:"
            f"{outcome.field_position}."
        )
    return outcome.canonical_bytes


def _require_inspection(inspection: ProjectIRQueryBlockInspection) -> None:
    if type(inspection) is not ProjectIRQueryBlockInspection:
        raise TypeError("Query-block queries require an exact inspection.")


def _require_ref(
    inspection: ProjectIRQueryBlockInspection,
    ref: object,
    expected: type[object],
) -> None:
    if type(ref) is not expected:
        raise TypeError("Query-block queries require one exact typed ref.")
    typed = cast(
        ProjectIRPlanNodeRef
        | ProjectIROutputValueRef
        | ProjectIRInputSlotRef
        | ProjectIRUseRef,
        ref,
    )
    if typed.scope is not inspection.summary.scope:
        raise ValueError("Query-block query refs require the inspected snapshot scope.")


def _require_owner_identity(identity: ProjectDeclarationOccurrenceIdentity) -> None:
    if type(identity) is not ProjectDeclarationOccurrenceIdentity:
        raise TypeError("Query-block owner queries require an exact identity.")


def _owner_matches(
    entry: ProjectIRQueryBlockEntry,
    identity: ProjectDeclarationOccurrenceIdentity,
) -> bool:
    return _declaration_identity(entry.owner) == identity


# ponytail: direct tuple scans preserve complete winner-free authority; add
# ephemeral indexes only after a measured need and never replace retained tuples.
def query_project_query_block_entries(
    inspection: ProjectIRQueryBlockInspection,
    identity: ProjectDeclarationOccurrenceIdentity,
) -> tuple[ProjectIRQueryBlockEntry, ...]:
    _require_inspection(inspection)
    _require_owner_identity(identity)
    return tuple(
        entry for entry in inspection.entries if _owner_matches(entry, identity)
    )


def query_project_query_block_active_roots(
    inspection: ProjectIRQueryBlockInspection,
    identity: ProjectDeclarationOccurrenceIdentity,
) -> tuple[
    tuple[
        ProjectIRQueryBlockInspectionActiveOutput,
        ProjectIRQueryBlockResultProperties,
    ],
    ...,
]:
    return tuple(
        root
        for entry in query_project_query_block_entries(inspection, identity)
        for root in _entry_active_roots(entry)
    )


def query_project_query_block_nodes(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRPlanNodeOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRPlanNodeRef)
    return tuple(item for item in inspection.combined_nodes if item.ref == ref)


def query_project_query_block_outputs(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIROutputValueRef,
) -> tuple[ProjectIROutputValueOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIROutputValueRef)
    return tuple(item for item in inspection.combined_outputs if item.ref == ref)


def query_project_query_block_input_slots(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIRInputSlotRef,
) -> tuple[ProjectIRInputSlotOccurrence, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRInputSlotRef)
    return tuple(item for item in inspection.combined_input_slots if item.ref == ref)


def query_project_query_block_uses(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIRUseRef,
) -> tuple[ProjectIRQueryBlockInspectionUse, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRUseRef)
    return tuple(item for item in inspection.combined_uses if item.ref == ref)


def query_project_query_block_incoming_uses(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRQueryBlockInspectionUse, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRPlanNodeRef)
    return tuple(
        item for item in inspection.combined_uses if item.slot.consumer.ref == ref
    )


def query_project_query_block_outgoing_uses(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRQueryBlockInspectionUse, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRPlanNodeRef)
    return tuple(
        item for item in inspection.combined_uses if item.output.producer.ref == ref
    )


def query_project_query_block_operators(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRQueryBlockInspectionOperator, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRPlanNodeRef)
    return tuple(item for item in inspection.operators if item.node.ref == ref)


def query_project_query_block_final_fields(
    inspection: ProjectIRQueryBlockInspection,
    identity: ProjectModuleRowFieldIdentity,
) -> tuple[ProjectIRQueryBlockRowField, ...]:
    _require_inspection(inspection)
    if type(identity) is not ProjectModuleRowFieldIdentity:
        raise TypeError("Final-field queries require an exact field identity.")
    return tuple(
        field
        for field in inspection.query_block_row_fields
        if field.final_identity is identity
    )


def query_project_query_block_terminals(
    inspection: ProjectIRQueryBlockInspection,
    identity: ProjectDeclarationOccurrenceIdentity,
) -> tuple[ProjectIRQueryBlockTerminal, ...]:
    _require_inspection(inspection)
    _require_owner_identity(identity)
    return tuple(
        entry for entry in inspection.terminals if _owner_matches(entry, identity)
    )


def query_project_query_block_relation_inputs(
    inspection: ProjectIRQueryBlockInspection,
    identity: ProjectDeclarationOccurrenceIdentity,
) -> tuple[ProjectIRQueryBlockRelationInputEdge, ...]:
    entries = query_project_query_block_entries(inspection, identity)
    return tuple(edge for entry in entries for edge in _entry_relation_inputs(entry))


def query_project_query_block_grain_origins(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRQueryBlockGrainOrigin, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRPlanNodeRef)
    return tuple(item for item in inspection.grain_origins if item.operator.ref == ref)


def query_project_query_block_grain_factors(
    inspection: ProjectIRQueryBlockInspection,
    identity: ProjectGrainFactorIdentity,
) -> tuple[ProjectGrainDomainFactor, ...]:
    _require_inspection(inspection)
    if type(identity) not in {
        ProjectSourceGrainFactorIdentity,
        ProjectGroupedGrainFactorIdentity,
        ProjectJoinGrainFactorIdentity,
    }:
        raise TypeError("Grain-factor queries require an exact identity.")
    if type(identity) is ProjectGroupedGrainFactorIdentity:
        scope = identity.operator.scope
    elif type(identity) is ProjectJoinGrainFactorIdentity:
        scope = identity.introduction_use.scope
    else:
        scope = None
    if scope is not None and scope is not inspection.summary.scope:
        raise ValueError("Grain-factor queries require the inspected snapshot scope.")
    return tuple(item for item in inspection.grain_factors if item.identity is identity)


def query_project_query_block_reverse_uses(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIROutputValueRef,
) -> tuple[ProjectIRQueryBlockReverseUseEntry, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIROutputValueRef)
    return tuple(
        item for item in inspection.combined_reverse_uses if item.output.ref == ref
    )


def query_project_query_block_reachability(
    inspection: ProjectIRQueryBlockInspection,
    ref: ProjectIRPlanNodeRef,
) -> tuple[ProjectIRReachabilityEntry, ...]:
    _require_inspection(inspection)
    _require_ref(inspection, ref, ProjectIRPlanNodeRef)
    return tuple(
        item for item in inspection.combined_reachability if item.source.ref == ref
    )
