"""Verified-only private inspection of Phase-63 query-block Project IR."""

from __future__ import annotations

import json
from enum import Enum
from pietto.ast_nodes import (
    Node,
    Span,
    JoinOnClause,
    WhereClause,
    SelectItem,
    ShapeDef,
    LetBinding,
)
from pietto.errors import Diagnostic
from pietto._project.project_query_block_ir_algebra import ProjectIRComposedJoin
from pietto._project.project_row_equivalence import ProjectRowEquivalenceField
from pietto._project.module_catalog import ProjectNominalDeclarationIdentity
from pietto._project.project_grain import (
    ProjectDistinctGrainFactorIdentity,
    ProjectSetGrainFactorIdentity,
    ProjectBaseGrainFactorIdentity,
)

from pietto._project.project_ir_properties import ProjectIRJoinRowOutput


from dataclasses import dataclass, field, fields as dataclass_fields
from typing import cast, TypedDict, Literal

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
    ProjectIRSetInputUseOccurrence,
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
from pietto.semantic.existence_generators import AnyUseInfo, AnyValueInfo
from pietto._project.existence_values import (
    ProjectAnyValue,
    ProjectAnyField,
    ProjectAnyLetValue,
    ProjectAnyRowBinding,
)
from pietto._project.project_joined_row_filter import ProjectConcreteJoinedRowFilter
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
    ProjectIRDistinctComparison,
    _semantic_entry_identities,
    ProjectIRSingleMatchRetention,
    ProjectIRSingleMatchProofImage,
    ProjectIRQueryBlockRowDomainOrigin,
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRCompletedSetOperationOutput,
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
    _entry_schema,
    ProjectCompletedEffectiveOutput,
    ProjectRelationOrdering,
    _has_set_outputs,
    _has_distinct,
)
from pietto._project.project_joined_windows import (
    ProjectConcreteWindowComputation,
    ProjectSelectedWindowResultBinding,
)
from pietto._project.project_query_block_ir_pure_boundary import (
    PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT,
    PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT,
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
    project_query_block_ir_pure_integers,
    project_query_block_ir_pure_ref,
    project_query_block_ir_pure_refs,
    project_query_block_ir_pure_text,
    project_query_block_ir_pure_texts,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
    ProjectIRQueryBlockReverseUseEntry,
    ProjectIRQueryBlockVerificationResult,
    ProjectIRQueryBlockVerificationStatus,
)

from pietto._project.project_relationship_predicates import (
    ProjectRelationshipPredicateExpression,
)
from pietto._project.project_join_conditions import (
    ProjectJoinConditionEquality,
    ProjectJoinConditionKeyMatch,
)
from pietto.semantic.model import RelationshipCallInfo
from pietto._project.project_relationship_uses import ProjectRelationBindingOccurrence

__all__: tuple[str, ...] = ()


type ProjectIRQueryBlockInspectionOperator = (
    ProjectIRLogicalOperatorOccurrence | ProjectIRQueryBlockOperatorOccurrence
)
type ProjectIRQueryBlockInspectionUse = (
    ProjectIRUseOccurrence
    | ProjectIROperatorFlowUseOccurrence
    | ProjectIRJoinInputUseOccurrence
    | ProjectIRSetInputUseOccurrence
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
    set_entries: tuple[ProjectIRCompletedSetOperationOutput, ...]
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
    slice14_uses: tuple[ProjectIRQueryBlockInspectionUse, ...]
    algebra_joins: tuple[ProjectIRComposedJoin, ...]
    historical_matches: tuple[ProjectIRComposedJoin, ...]
    existence_uses: tuple[AnyUseInfo, ...]
    scalar_existence_uses: tuple[AnyValueInfo, ...]
    scalar_existence_values: tuple[ProjectAnyValue, ...]
    predicate_expressions: tuple[ProjectRelationshipPredicateExpression, ...]
    predicate_calls: tuple[RelationshipCallInfo, ...]
    predicate_equalities: tuple[ProjectJoinConditionEquality, ...]
    predicate_key_matches: tuple[ProjectJoinConditionKeyMatch, ...]
    requirements: tuple[ProjectIRSingleMatchRetention, ...]
    diagnostics: tuple[Diagnostic, ...]
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
    grain_origins: tuple[
        ProjectIRQueryBlockGrainOrigin | ProjectIRQueryBlockRowDomainOrigin, ...
    ]
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
        return (*entry.join_properties, *entry.row_properties)
    if type(entry) is ProjectIRCompletedSetOperationOutput:
        return (entry.active_properties,)
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
    if type(entry) is ProjectIRCompletedSetOperationOutput:
        return (entry.operator,)
    return ()


def _entry_effects(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectIRQueryBlockInspectionEffect, ...]:
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return cast(
            tuple[ProjectIRQueryBlockInspectionEffect, ...],
            (*(p.effect for p in entry.join_properties), *entry.effects),
        )
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
    if isinstance(
        entry,
        (ProjectIRCompletedQueryBlockOutput, ProjectIRCompletedSetOperationOutput),
    ):
        return ((entry.active_output, entry.active_properties),)
    return ()


def _existence_uses(root: ProjectIRQueryBlockSnapshot) -> tuple[AnyUseInfo, ...]:
    """Retain canonical authored ANY occurrences for the inspected owners."""
    return tuple(
        use
        for module in root.completed.semantic_result.modules
        if module.parsed_input is not None
        for use in module.parsed_input.existence_generators
        if any(
            owner.identity.module_path == module.path and owner.definition is use.owner
            for owner in root.owners
        )
    )


def _scalar_existence_uses(
    root: ProjectIRQueryBlockSnapshot,
) -> tuple[AnyValueInfo, ...]:
    return tuple(
        use
        for module in root.completed.semantic_result.modules
        if module.parsed_input is not None
        for use in module.parsed_input.existence_values
        if any(
            owner.identity.module_path == module.path and owner.definition is use.owner
            for owner in root.owners
        )
    )


def _scalar_existence_values(
    root: ProjectIRQueryBlockSnapshot,
) -> tuple[ProjectAnyValue, ...]:
    candidates: list[ProjectAnyValue] = []

    def retain(roots):
        pending = list(reversed(roots))
        while pending:
            value = pending.pop()
            if not any(value is previous for previous in candidates):
                candidates.append(value)
                pending.extend(reversed(value.nested))

    for entry in root.entries:
        if not isinstance(entry, ProjectIRCompletedQueryBlockOutput):
            continue
        joins = () if entry.join_prefix is None else entry.join_prefix.joins
        for joined in joins:
            retain(joined.condition.environment.existence_values)
        for operator in entry.operators:
            evidence = operator.evidence
            if isinstance(evidence, ProjectConcreteJoinedRowFilter):
                for value in evidence.joined_semantics.namespaces.values:
                    retain(value.existence_values)
                if evidence.expression_analysis is not None:
                    retain(evidence.expression_analysis.existence_values)
        semantic = entry.semantic_entry
        if isinstance(semantic.root, ProjectConcreteNoJoinReplay):
            retain(semantic.root.let_scope.existence_values)
            if semantic.root.where.expression_analysis is not None:
                retain(semantic.root.where.expression_analysis.existence_values)
        for selected in semantic.fields:
            retain(getattr(selected.source, "existence_values", ()))
    for joined in root.retained_joins:
        retain(joined.condition.environment.existence_values)
    uses = _scalar_existence_uses(root)
    result = tuple(
        value
        for use in uses
        for value in candidates
        if value.input.binding.origin is use
    )
    if len(result) != len(candidates):
        raise ValueError(
            "Scalar ANY inspection lost canonical source occurrence authority."
        )
    return result


def _predicate_expressions(
    root: ProjectIRQueryBlockSnapshot,
) -> tuple[ProjectRelationshipPredicateExpression, ...]:
    """Every actual predicate-use context, from its canonical owner in source order."""
    joined = root.completed.roots.join_conditions.predicate_expressions
    replayed = tuple(
        value
        for entry in root.completed.effective_outputs.entries
        if isinstance(entry, ProjectCompletedEffectiveOutput)
        and isinstance(entry.root, ProjectConcreteNoJoinReplay)
        for value in entry.root.predicate_expressions
    )
    result = tuple(
        value
        for owner in root.owners
        for value in (*joined, *replayed)
        if value.owner is owner and (value.calls or value.any_bindings)
    )
    if len({(id(value.owner), id(value.context)) for value in result}) != len(result):
        raise ValueError(
            "Predicate inspection requires one canonical record per context."
        )
    return result


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
    row_outputs = tuple(
        output
        for entry in entries
        for output in (
            entry.row_outputs
            if isinstance(entry, ProjectIRCompletedQueryBlockOutput)
            else (entry.active_output,)
            if isinstance(entry, ProjectIRCompletedSetOperationOutput)
            else ()
        )
    )
    scalar_outputs = tuple(
        output for entry in completed for output in entry.scalar_outputs
    )
    predicates = _predicate_expressions(root)
    conditions = tuple(
        joined.condition
        for joined in sorted(
            (
                *root.retained_joins,
                *(
                    joined
                    for entry in completed
                    if entry.join_prefix is not None
                    for joined in entry.join_prefix.joins
                ),
            ),
            key=lambda joined: joined.node.ref.position,
        )
        if joined.condition.environment.predicate_expression is not None
        and (
            joined.condition.environment.predicate_expression.calls
            or joined.condition.environment.predicate_expression.any_bindings
        )
    )
    base = root.base_plan.structural_stage
    join = root.join_stage.structural
    values: dict[str, tuple[object, ...]] = {
        "owners": root.owners,
        "requirements": root.requirements,
        "historical_matches": root.retained_joins,
        "existence_uses": _existence_uses(root),
        "scalar_existence_uses": _scalar_existence_uses(root),
        "scalar_existence_values": _scalar_existence_values(root),
        "predicate_expressions": predicates,
        "predicate_calls": tuple(call for value in predicates for call in value.calls),
        "predicate_equalities": tuple(
            value
            for condition in conditions
            for value in condition.mandatory_equalities
        ),
        "predicate_key_matches": tuple(
            value for condition in conditions for value in condition.key_matches
        ),
        "diagnostics": root.completed.diagnostics,
        "dependencies": root.dependencies,
        "schedule": root.schedule,
        "entries": entries,
        "reused_entries": reused,
        "rebound_entries": rebound,
        "completed_entries": completed,
        "set_entries": tuple(
            entry
            for entry in entries
            if isinstance(entry, ProjectIRCompletedSetOperationOutput)
        ),
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
        "algebra_joins": tuple(
            join
            for entry in completed
            if entry.join_prefix is not None
            for join in entry.join_prefix.joins
        ),
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
        if (
            _uses_flat_format(inspection)
            and any(
                match.output.occurrence is output
                and match.condition.use.owner is entry.owner
                for match in inspection.historical_matches
            )
        )
        or any(
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
        if (
            _uses_flat_format(inspection)
            and any(
                match.condition.use.owner is entry.owner
                and any(use is item for item in match.input_uses)
                for match in inspection.historical_matches
            )
        )
        or any(edge.use is use for edge in _entry_relation_inputs(entry))
        or (
            type(entry) is ProjectIRReboundExistingOutput
            and any(
                candidate is use
                for candidate in entry.rebuilt_fragment.structural_stage.uses
            )
        )
        or (
            isinstance(entry, ProjectIRCompletedSetOperationOutput)
            and any(candidate is use for candidate in entry.uses)
        )
        or (
            type(entry) is ProjectIRCompletedQueryBlockOutput
            and (
                any(candidate is use for candidate in entry.uses)
                or entry.join_prefix is not None
                and any(candidate is use for candidate in entry.join_prefix.uses)
            )
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
    if type(entry) is ProjectIRCompletedSetOperationOutput:
        return "set"
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
    for position, entry in enumerate(inspection.entries):
        if entry.owner.let_position is not None:
            _record(
                records,
                ProjectQueryBlockIRRecordKind.OWNER_LET,
                (
                    "owner",
                    project_query_block_ir_pure_ref(
                        _portable_ref(
                            ProjectQueryBlockIRPortableRefDomain.OWNER_ENTRY,
                            position,
                        )
                    ),
                ),
                (
                    "let_position",
                    project_query_block_ir_pure_integer(entry.owner.let_position),
                ),
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
    if any(item.node is node for item in inspection.algebra_joins):
        return "phase64"
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
    if type(use) is ProjectIRSetInputUseOccurrence:
        return "set_input"
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
    if (
        type(entry) is ProjectIRCompletedSetOperationOutput
        and entry.operator is operator
    ):
        return entry.active_properties
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
    if type(entry) is ProjectIRCompletedSetOperationOutput:
        return "set_operation"
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
    if type(properties.output) is ProjectIRJoinRowOutput:
        joined_field = properties.output.row_shape.fields[
            field_occurrence.field_position
        ]
        return (
            type(joined_field).__name__,
            joined_field.introduction_use.ref,
            joined_field.nulling_joins,
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
            if identity is None and _uses_flat_format(inspection):
                active = tuple(
                    entry
                    for entry in inspection.entries
                    if not isinstance(entry, ProjectIRQueryBlockTerminal)
                    and entry.active_properties is properties
                )
                if len(active) == 1:
                    identity = _semantic_entry_identities(active[0].semantic_entry)[
                        field_occurrence.field_position
                    ]
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
) -> ProjectBaseGrainFactorIdentity:
    return (
        identity.base
        if isinstance(identity, ProjectJoinGrainFactorIdentity)
        else cast(ProjectBaseGrainFactorIdentity, identity)
    )


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
    marker = (
        PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
        if _uses_flat_format(inspection)
        else PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT
    )
    records: list[ProjectQueryBlockIRPureRecord] = []
    _record(
        records,
        ProjectQueryBlockIRRecordKind.HEADER,
        (
            "format",
            project_query_block_ir_pure_text(marker),
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
    if marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT:
        _algebra_records(inspection, records)
    _predicate_records(inspection, records)
    _existence_records(inspection, records)
    _scalar_any_records(inspection, records)
    _predicate_any_scope_records(inspection, records)
    capabilities: list[
        tuple[ProjectQueryBlockIRPortableRef, ProjectRowEquivalenceField]
    ] = []
    order_records: list[ProjectQueryBlockIRPureRecord] = []
    _distinct_records(inspection, records, capabilities, order_records)
    _set_records(inspection, records, capabilities)
    _capability_records(inspection, records, capabilities)
    for kind in (
        ProjectQueryBlockIRRecordKind.ORDER_SOURCE,
        ProjectQueryBlockIRRecordKind.ORDER_BINDING,
        ProjectQueryBlockIRRecordKind.ORDER_PROOF,
    ):
        records.extend(record for record in order_records if record.kind is kind)
    if marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT:
        _requirement_records(inspection, records)
    _analysis_records(inspection, records)
    _record(records, ProjectQueryBlockIRRecordKind.END)
    return ProjectQueryBlockIRPureDocument(
        format_marker=marker,
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
) -> tuple[ProjectIRQueryBlockGrainOrigin | ProjectIRQueryBlockRowDomainOrigin, ...]:
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
        ProjectDistinctGrainFactorIdentity,
        ProjectSetGrainFactorIdentity,
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


def _authored_data(
    value: object, module_path: str, *, include_occurrence: bool = False
) -> object:
    """Portable authored syntax, using the containing logical module path."""
    if isinstance(value, Enum):
        return value.value
    if value is None or type(value) in {str, int, bool}:
        return value
    if type(value) is float:
        return {"float_hex": value.hex()}
    if type(value) is tuple:
        return [
            _authored_data(item, module_path, include_occurrence=include_occurrence)
            for item in value
        ]
    if type(value) is Span:
        return {
            "path": module_path,
            "line": value.line,
            "column": value.column,
            "end_line": value.end_line,
            "end_column": value.end_column,
            **({"occurrence": value.occurrence} if include_occurrence else {}),
        }
    if isinstance(value, Node):
        return {
            "node": type(value).__name__,
            **{
                item.name: _authored_data(
                    getattr(value, item.name),
                    module_path,
                    include_occurrence=include_occurrence,
                )
                for item in dataclass_fields(value)
            },
        }
    raise TypeError("Portable authored evidence requires a closed AST value.")


def _authored_text(value: object, module_path: str) -> str:
    return json.dumps(
        _authored_data(value, module_path),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )


def _predicate_records(inspection, records):
    """Formal predicate-use and proof records, emitted only for actual calls."""
    K, D = ProjectQueryBlockIRRecordKind, ProjectQueryBlockIRPortableRefDomain
    text = project_query_block_ir_pure_text
    integer = project_query_block_ir_pure_integer
    refs = project_query_block_ir_pure_refs
    integers = project_query_block_ir_pure_integers
    reference = project_query_block_ir_pure_ref
    enum = project_query_block_ir_pure_enumeration
    expressions = inspection.predicate_expressions
    call_values = inspection.predicate_calls
    expression_refs = {
        id(value): _portable_ref(D.PREDICATE_EXPRESSION, i)
        for i, value in enumerate(expressions)
    }
    call_refs = {
        id(value): _portable_ref(D.PREDICATE_CALL, i)
        for i, value in enumerate(call_values)
    }
    equalities = inspection.predicate_equalities
    equality_refs = {
        id(value): _portable_ref(D.PREDICATE_EQUALITY, i)
        for i, value in enumerate(equalities)
    }
    matches = inspection.predicate_key_matches
    match_refs = {
        id(value): _portable_ref(D.PREDICATE_KEY_MATCH, i)
        for i, value in enumerate(matches)
    }
    joined = tuple(
        sorted(
            (*inspection.historical_matches, *inspection.algebra_joins),
            key=lambda value: value.node.ref.position,
        )
    )
    joined = tuple(
        value
        for value in joined
        if value.condition.environment.predicate_expression is not None
        and (
            value.condition.environment.predicate_expression.calls
            or value.condition.environment.predicate_expression.any_bindings
        )
    )
    input_keys = tuple(
        (value.condition, binding, properties, i, key)
        for value in joined
        for binding, properties in value.condition.match_inputs
        for i, key in enumerate(properties.keys)
    )

    def syntax(value, module_path):
        return text(
            json.dumps(
                _authored_data(value, module_path, include_occurrence=True),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        )

    def join_ref(condition):
        values = tuple(value for value in joined if value.condition is condition)
        if len(values) != 1:
            raise ValueError("Predicate proof requires one exact JOIN image.")
        return reference(_runtime_ref(values[0].node.ref))

    def key_ref(condition, binding, key):
        positions = tuple(
            i
            for i, (c, b, _, _, k) in enumerate(input_keys)
            if c is condition and b is binding and k is key
        )
        if len(positions) != 1:
            raise ValueError("Predicate key proof requires one exact input key.")
        return _portable_ref(D.PREDICATE_INPUT_KEY, positions[0])

    for value in expressions:
        path = value.owner.identity.module_path
        role = {
            JoinOnClause: "on",
            WhereClause: "where",
            SelectItem: "select",
            LetBinding: "let",
        }[type(value.context)]
        _record(
            records,
            K.PREDICATE_EXPRESSION,
            ("ref", reference(expression_refs[id(value)])),
            ("owner", reference(_owner_ref(inspection, value.owner))),
            ("role", enum(role)),
            ("context", syntax(value.context, path)),
            ("authored", syntax(value.authored, path)),
            ("normalized", syntax(value.expression, path)),
            ("calls", refs(tuple(call_refs[id(call)] for call in value.calls))),
        )
    for value in expressions:
        path = value.owner.identity.module_path
        for call in value.calls:
            template_path = call.template.declaration.span.path or path
            _record(
                records,
                K.PREDICATE_CALL,
                ("ref", reference(call_refs[id(call)])),
                ("expression", reference(expression_refs[id(value)])),
                ("ordinal", integer(call.ordinal)),
                ("call", syntax(call.call, path)),
                ("template", syntax(call.template.declaration, template_path)),
                (
                    "shapes",
                    project_query_block_ir_pure_texts(
                        tuple(
                            json.dumps(
                                _authored_data(
                                    shape,
                                    shape.span.path or path,
                                    include_occurrence=True,
                                ),
                                ensure_ascii=False,
                                allow_nan=False,
                                separators=(",", ":"),
                            )
                            for shape in call.template.parameter_shapes
                        )
                    ),
                ),
                ("expanded", syntax(call.expanded, path)),
                (
                    "mandatory",
                    project_query_block_ir_pure_texts(
                        tuple(
                            json.dumps(
                                _authored_data(equality, path, include_occurrence=True),
                                ensure_ascii=False,
                                allow_nan=False,
                                separators=(",", ":"),
                            )
                            for equality in call.mandatory_equalities
                        )
                    ),
                ),
            )
    for value in expressions:
        path = value.owner.identity.module_path
        for call, bindings in zip(value.calls, value.argument_bindings, strict=True):
            for i, (argument, binding) in enumerate(
                zip(call.arguments, bindings, strict=True)
            ):
                ordinal = (
                    binding.identity.binding_position
                    if isinstance(binding, ProjectRelationBindingOccurrence)
                    else 0
                )
                if isinstance(binding, ProjectAnyRowBinding):
                    target_owner = binding.target
                else:
                    symbol = (
                        binding.target
                        if isinstance(binding, ProjectRelationBindingOccurrence)
                        else binding.target_symbol
                    )
                    target_owner = None if symbol is None else symbol.target_occurrence
                if target_owner is None:
                    raise ValueError(
                        "Predicate argument lost its resolved relation target."
                    )
                _record(
                    records,
                    K.PREDICATE_ARGUMENT,
                    ("call", reference(call_refs[id(call)])),
                    ("ordinal", integer(i)),
                    ("binding", integer(ordinal)),
                    (
                        "target",
                        reference(_owner_ref(inspection, target_owner)),
                    ),
                    (
                        "parameter",
                        syntax(
                            argument.parameter,
                            call.template.declaration.span.path or path,
                        ),
                    ),
                    ("argument", syntax(argument.argument, path)),
                    ("occurrence", syntax(argument.occurrence, path)),
                    (
                        "relation",
                        syntax(argument.relation, argument.relation.span.path or path),
                    ),
                    ("shape", syntax(argument.shape, argument.shape.span.path or path)),
                )
    for value in joined:
        condition = value.condition
        predicate = condition.environment.predicate_expression
        _record(
            records,
            K.PREDICATE_JOIN,
            ("node", join_ref(condition)),
            ("expression", reference(expression_refs[id(predicate)])),
            (
                "equalities",
                refs(
                    tuple(equality_refs[id(e)] for e in condition.mandatory_equalities)
                ),
            ),
            (
                "bindings",
                integers(
                    tuple(
                        b.identity.binding_position for b, _ in condition.match_inputs
                    )
                ),
            ),
            (
                "key_counts",
                integers(tuple(len(p.keys) for _, p in condition.match_inputs)),
            ),
            (
                "keys",
                refs(
                    tuple(
                        key_ref(condition, b, k)
                        for b, p in condition.match_inputs
                        for k in p.keys
                    )
                ),
            ),
            ("matches", refs(tuple(match_refs[id(m)] for m in condition.key_matches))),
        )
    for equality in equalities:
        condition = equality.condition
        _record(
            records,
            K.PREDICATE_EQUALITY,
            ("ref", reference(equality_refs[id(equality)])),
            ("node", join_ref(condition)),
            ("position", integer(equality.conjunct_position)),
            (
                "comparison",
                syntax(equality.comparison, condition.use.owner.identity.module_path),
            ),
            ("left_binding", integer(equality.left.binding.identity.binding_position)),
            ("left_field", integer(equality.left.input_field.field_position)),
            (
                "right_binding",
                integer(equality.right.binding.identity.binding_position),
            ),
            ("right_field", integer(equality.right.input_field.field_position)),
            ("calls", refs(tuple(call_refs[id(call)] for call in equality.calls))),
        )
    for i, (condition, binding, _, ordinal, key) in enumerate(input_keys):
        _record(
            records,
            K.PREDICATE_INPUT_KEY,
            ("ref", reference(_portable_ref(D.PREDICATE_INPUT_KEY, i))),
            ("node", join_ref(condition)),
            ("binding", integer(binding.identity.binding_position)),
            ("ordinal", integer(ordinal)),
            ("strength", enum(key.strength.value)),
            (
                "class_sizes",
                integers(tuple(len(group.members) for group in key.determinants)),
            ),
            (
                "fields",
                integers(
                    tuple(
                        member.field_position
                        for group in key.determinants
                        for member in group.members
                    )
                ),
            ),
        )
    for match in matches:
        _record(
            records,
            K.PREDICATE_KEY_MATCH,
            ("ref", reference(match_refs[id(match)])),
            ("node", join_ref(match.condition)),
            ("key", reference(key_ref(match.condition, match.binding, match.key))),
            ("equalities", refs(tuple(equality_refs[id(e)] for e in match.equalities))),
            ("minimum", enum(match.minimum.value)),
            ("maximum", enum(match.maximum.value)),
        )


def _existence_records(inspection, records):
    """Project inter-JOIN authored filters and their actual generated stages."""
    K, D = ProjectQueryBlockIRRecordKind, ProjectQueryBlockIRPortableRefDomain
    joins = (*inspection.historical_matches, *inspection.algebra_joins)
    for i, use in enumerate(inspection.existence_uses):
        owners = tuple(
            owner for owner in inspection.owners if owner.definition is use.owner
        )
        if len(owners) != 1:
            raise ValueError("Inter-JOIN ANY requires one exact owner.")
        owner = owners[0]
        path = owner.identity.module_path

        def syntax(value):
            return project_query_block_ir_pure_text(
                json.dumps(
                    _authored_data(value, path, include_occurrence=True),
                    ensure_ascii=False,
                    allow_nan=False,
                    separators=(",", ":"),
                )
            )

        matches = tuple(
            join
            for join in joins
            if join.condition.use.clause is use.clause
            and join.condition.use.owner is owner
        )
        if len(matches) > 1:
            raise ValueError("Inter-JOIN ANY cannot have multiple JOIN images.")
        _record(
            records,
            K.EXISTENCE_USE,
            ("ref", project_query_block_ir_pure_ref(_portable_ref(D.EXISTENCE_USE, i))),
            ("owner", project_query_block_ir_pure_ref(_owner_ref(inspection, owner))),
            ("authored_owner", syntax(use.authored_owner)),
            ("context", syntax(use.context)),
            ("any", syntax(use.expression)),
            ("clause", syntax(use.clause)),
            ("input_ordinal", project_query_block_ir_pure_integer(use.input_ordinal)),
            (
                "preceding_join_count",
                project_query_block_ir_pure_integer(use.preceding_join_count),
            ),
            (
                "node",
                project_query_block_ir_pure_ref(_runtime_ref(matches[0].node.ref))
                if matches
                else PROJECT_QUERY_BLOCK_IR_PURE_ABSENT,
            ),
        )


def _scalar_any_records(inspection, records):
    K, D = ProjectQueryBlockIRRecordKind, ProjectQueryBlockIRPortableRefDomain
    text, integer = (
        project_query_block_ir_pure_text,
        project_query_block_ir_pure_integer,
    )
    ref, refs, enum = (
        project_query_block_ir_pure_ref,
        project_query_block_ir_pure_refs,
        project_query_block_ir_pure_enumeration,
    )
    uses, values = inspection.scalar_existence_uses, inspection.scalar_existence_values
    use_refs = tuple(_portable_ref(D.SCALAR_ANY_USE, i) for i in range(len(uses)))
    value_refs = tuple(_portable_ref(D.SCALAR_ANY_VALUE, i) for i in range(len(values)))
    fields = tuple(
        (value, i, item) for value in values for i, item in enumerate(value.fields)
    )
    references = tuple(
        (value, i, item) for value in values for i, item in enumerate(value.references)
    )
    candidates = tuple(
        (reference, i, item)
        for _, _, reference in references
        for i, item in enumerate(reference.candidates)
    )
    field_refs = tuple(_portable_ref(D.SCALAR_ANY_FIELD, i) for i in range(len(fields)))
    reference_refs = tuple(
        _portable_ref(D.SCALAR_ANY_REFERENCE, i) for i in range(len(references))
    )
    candidate_refs = tuple(
        _portable_ref(D.SCALAR_ANY_CANDIDATE, i) for i in range(len(candidates))
    )

    def syntax(value, path):
        return text(
            json.dumps(
                _authored_data(value, path, include_occurrence=True),
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        )

    def owner_of(use):
        return next(
            owner for owner in inspection.owners if owner.definition is use.owner
        )

    def optional_owner(owner):
        return (
            PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
            if owner is None
            else ref(_owner_ref(inspection, owner))
        )

    def field_path(field, fallback):
        if field is None:
            return fallback
        matches = tuple(
            module.path
            for module in inspection.root.completed.semantic_result.modules
            if module.parsed_input is not None
            and module.parsed_input.script is not None
            for definition in module.parsed_input.script.definitions
            if isinstance(definition, ShapeDef)
            for candidate in definition.fields
            if candidate is field
        )
        if len(matches) != 1:
            raise ValueError(
                "ANY field definition requires one exact declaring module."
            )
        return matches[0]

    for i, use in enumerate(uses):
        owner = owner_of(use)
        path = owner.identity.module_path
        related = tuple(
            value_refs[j]
            for j, value in enumerate(values)
            if value.input.binding.origin is use
        )
        _record(
            records,
            K.SCALAR_ANY_USE,
            ("ref", ref(use_refs[i])),
            ("owner", ref(_owner_ref(inspection, owner))),
            ("authored", syntax(use.authored_expression, path)),
            ("authored_owner", syntax(use.authored_owner, path)),
            ("authored_context", syntax(use.authored_context, path)),
            ("current", syntax(use.expression, path)),
            ("context", syntax(use.context, path)),
            ("owner_definition", syntax(use.owner, path)),
            ("authored_prefix", integer(use.authored_join_count)),
            ("current_prefix", integer(use.join_prefix_count)),
            ("values", refs(related)),
        )
    for i, value in enumerate(values):
        use = value.input.binding.origin
        use_index = _position(cast(tuple[object, ...], uses), use, "scalar ANY origin")
        parents = tuple(
            j
            for j, parent in enumerate(values)
            if any(child is value for child in parent.nested)
        )
        if len(parents) > 1:
            raise ValueError("Scalar ANY scope cannot have multiple parents.")
        path = value.input.binding.owner.identity.module_path
        local_fields = tuple(
            field_refs[j] for j, (owner, _, _) in enumerate(fields) if owner is value
        )
        local_refs = tuple(
            reference_refs[j]
            for j, (owner, _, _) in enumerate(references)
            if owner is value
        )
        nested = tuple(
            value_refs[
                _position(cast(tuple[object, ...], values), child, "nested ANY value")
            ]
            for child in value.nested
        )
        _record(
            records,
            K.SCALAR_ANY_VALUE,
            ("ref", ref(value_refs[i])),
            ("use", ref(use_refs[use_index])),
            (
                "parent",
                ref(value_refs[parents[0]])
                if parents
                else PROJECT_QUERY_BLOCK_IR_PURE_ABSENT,
            ),
            ("target", optional_owner(value.input.binding.target)),
            ("context", syntax(value.context, path)),
            ("expression", syntax(value.expression, path)),
            ("type", text(value.value_type.resolved_type.name)),
            ("nullability", enum(value.value_type.nullability.value)),
            ("field_count", integer(len(local_fields))),
            (
                "input_names",
                project_query_block_ir_pure_texts(
                    tuple(value.input.schema.fields)
                    if value.input.schema is not None
                    and not value.input.schema.is_unknown
                    else ()
                ),
            ),
            ("fields", refs(local_fields)),
            ("reference_count", integer(len(local_refs))),
            ("references", refs(local_refs)),
            ("nested", refs(nested)),
        )
    for i, (value, ordinal, item) in enumerate(fields):
        index = _position(cast(tuple[object, ...], values), value, "ANY value")
        path = value.input.binding.owner.identity.module_path
        _record(
            records,
            K.SCALAR_ANY_FIELD,
            ("ref", ref(field_refs[i])),
            ("value", ref(value_refs[index])),
            ("ordinal", integer(ordinal)),
            ("name", text(item.evidence.name)),
            ("type", text(item.value_type.resolved_type.name)),
            ("nullability", enum(item.value_type.nullability.value)),
            (
                "definition",
                syntax(
                    item.evidence.field_def, field_path(item.evidence.field_def, path)
                ),
            ),
        )
    for i, (value, ordinal, item) in enumerate(references):
        index = _position(cast(tuple[object, ...], values), value, "ANY value")
        path = value.input.binding.owner.identity.module_path
        local = tuple(
            candidate_refs[j]
            for j, (owner, _, _) in enumerate(candidates)
            if owner is item
        )
        _record(
            records,
            K.SCALAR_ANY_REFERENCE,
            ("ref", ref(reference_refs[i])),
            ("value", ref(value_refs[index])),
            ("ordinal", integer(ordinal)),
            ("expression", syntax(item.expression, path)),
            ("candidate_count", integer(len(local))),
            ("candidates", refs(local)),
        )
    for i, (reference, ordinal, item) in enumerate(candidates):
        index = _position(
            tuple(item for _, _, item in references), reference, "ANY reference"
        )
        value = references[index][0]
        path = value.input.binding.owner.identity.module_path
        local = target = position = field_position = let_expression = None
        input_names = ()
        if isinstance(item, ProjectAnyLetValue):
            kind, binding, name, field = (
                "let",
                item.binding,
                item.binding.name,
                item.binding,
            )
            let_expression = item.expression
        else:
            assert isinstance(item, ProjectAnyField)
            kind, name, field = "field", item.binding_name, item.evidence.field_def
            if isinstance(item.binding, ProjectAnyRowBinding):
                binding = item.binding.expression
                local = item.binding.origin
                target = item.binding.target
                scope = value
                visited = set()
                while scope.input.binding is not item.binding:
                    if id(scope) in visited:
                        raise ValueError("Scalar ANY scope cannot contain a cycle.")
                    visited.add(id(scope))
                    parents = tuple(
                        parent
                        for parent in values
                        if any(child is scope for child in parent.nested)
                    )
                    if len(parents) != 1:
                        raise ValueError(
                            "Scalar ANY capture requires an exact enclosing scope."
                        )
                    scope = parents[0]
                positions = tuple(
                    j
                    for j, field_value in enumerate(scope.fields)
                    if field_value.evidence is item.evidence
                )
                if len(positions) != 1:
                    raise ValueError(
                        "Scalar ANY capture requires one exact producer field."
                    )
                position = field_position = positions[0]
                input_names = tuple(field.evidence.name for field in scope.fields)
            elif isinstance(item.binding, ProjectRelationBindingOccurrence):
                binding = item.binding.site
                target = (
                    None
                    if item.binding.target is None
                    else item.binding.target.target_occurrence
                )
                position = item.binding.identity.binding_position
            else:
                binding = item.binding.reference.from_clause
                target = item.binding.target_symbol.target_occurrence
                position = 0
        if isinstance(item, ProjectAnyField) and local is None:
            matching = tuple(
                entry
                for entry in inspection.root.completed.effective_outputs.entries
                if entry.owner is target
            )
            if len(matching) != 1:
                raise ValueError(
                    "Scalar ANY capture requires one exact input producer."
                )
            source_schema = _entry_schema(matching[0])
            input_names = tuple(source_schema.fields)
            positions = tuple(
                i
                for i, source in enumerate(source_schema.fields.values())
                if source is item.evidence
            )
            if len(positions) != 1:
                raise ValueError(
                    "Scalar ANY capture lost its exact input field identity."
                )
            field_position = positions[0]
        value_type = item.value_type
        _record(
            records,
            K.SCALAR_ANY_CANDIDATE,
            ("ref", ref(candidate_refs[i])),
            ("reference", ref(reference_refs[index])),
            ("ordinal", integer(ordinal)),
            ("kind", enum(kind)),
            ("binding", syntax(binding, path)),
            ("name", text(name)),
            (
                "field_name",
                text(
                    item.binding.name
                    if isinstance(item, ProjectAnyLetValue)
                    else item.evidence.name
                ),
            ),
            ("type", text(value_type.resolved_type.name)),
            ("nullability", enum(value_type.nullability.value)),
            (
                "field",
                syntax(
                    field,
                    field_path(field, path)
                    if isinstance(item, ProjectAnyField)
                    else path,
                ),
            ),
            (
                "local",
                PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                if local is None
                else ref(
                    use_refs[
                        _position(
                            cast(tuple[object, ...], uses), local, "ANY local binding"
                        )
                    ]
                ),
            ),
            ("target", optional_owner(target)),
            (
                "position",
                PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                if position is None
                else integer(position),
            ),
            (
                "field_position",
                PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                if field_position is None
                else integer(field_position),
            ),
            ("input_names", project_query_block_ir_pure_texts(input_names)),
            (
                "let_expression",
                PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                if let_expression is None
                else syntax(let_expression, path),
            ),
        )


def _predicate_any_scope_records(inspection, records):
    """Retain every actual predicate ANY binding and its normalized image."""
    K, D = ProjectQueryBlockIRRecordKind, ProjectQueryBlockIRPortableRefDomain
    uses = inspection.scalar_existence_uses
    for index, record in enumerate(inspection.predicate_expressions):
        path = record.owner.identity.module_path
        for ordinal, binding in enumerate(record.any_bindings):
            images = tuple(
                after
                for before, after in record.any_expressions
                if before is binding.expression
            )
            if len(images) != 1:
                raise ValueError("Predicate ANY requires one exact normalized image.")
            origin = _position(
                cast(tuple[object, ...], uses),
                binding.origin,
                "ANY predicate scope origin",
            )

            def syntax(value, module_path):
                return project_query_block_ir_pure_text(
                    json.dumps(
                        _authored_data(value, module_path, include_occurrence=True),
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                    )
                )

            read = binding.resolution.read
            _record(
                records,
                K.PREDICATE_ANY_SCOPE,
                (
                    "expression",
                    project_query_block_ir_pure_ref(
                        _portable_ref(D.PREDICATE_EXPRESSION, index)
                    ),
                ),
                ("ordinal", project_query_block_ir_pure_integer(ordinal)),
                (
                    "use",
                    project_query_block_ir_pure_ref(
                        _portable_ref(D.SCALAR_ANY_USE, origin)
                    ),
                ),
                (
                    "target",
                    PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                    if binding.target is None
                    else project_query_block_ir_pure_ref(
                        _owner_ref(inspection, binding.target)
                    ),
                ),
                (
                    "relation",
                    PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                    if binding.target is None
                    else syntax(
                        binding.target.definition, binding.target.identity.module_path
                    ),
                ),
                (
                    "position",
                    project_query_block_ir_pure_enumeration(read.position.value),
                ),
                (
                    "container_ordinal",
                    project_query_block_ir_pure_integer(read.container_ordinal),
                ),
                ("read_ordinal", project_query_block_ir_pure_integer(read.ordinal)),
                ("before", syntax(binding.expression, path)),
                ("after", syntax(images[0], path)),
            )


def _algebra_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    joins = tuple(
        sorted(
            (*inspection.historical_matches, *inspection.algebra_joins),
            key=lambda item: item.node.ref.position,
        )
    )
    for joined in joins:
        condition = joined.condition
        _record(
            records,
            ProjectQueryBlockIRRecordKind.ALGEBRA,
            ("node", project_query_block_ir_pure_ref(_runtime_ref(joined.node.ref))),
            (
                "owner",
                project_query_block_ir_pure_ref(
                    _owner_ref(inspection, condition.use.owner)
                ),
            ),
            (
                "output",
                project_query_block_ir_pure_ref(
                    _runtime_ref(joined.output.occurrence.ref)
                ),
            ),
            ("kind", project_query_block_ir_pure_enumeration(condition.use.kind.value)),
            (
                "inputs",
                project_query_block_ir_pure_refs(
                    tuple(_runtime_ref(item.use.ref) for item in joined.inputs)
                ),
            ),
            (
                "span",
                project_query_block_ir_pure_text(
                    _authored_text(
                        condition.use.clause.span,
                        condition.use.owner.identity.module_path,
                    )
                ),
            ),
        )
    for joined in joins:
        condition = joined.condition
        module_path = condition.use.owner.identity.module_path
        references = tuple(
            json.dumps(
                {
                    "position": reference.position,
                    "expression": _authored_data(reference.expression, module_path),
                    "state": reference.state.value,
                    "binding_candidates": [
                        binding.identity.binding_position
                        for binding in reference.binding_candidates
                    ],
                    "candidates": [
                        {
                            "position": candidate.position,
                            "binding": candidate.binding.identity.binding_position,
                            "field_position": candidate.input_field.field_position,
                            "name": candidate.input_field.evidence.name,
                            "nullability": candidate.nullability.value,
                            "type": candidate.input_field.evidence.resolved_type.name,
                        }
                        for candidate in reference.candidates
                    ],
                    "target": None
                    if reference.target is None
                    else reference.target.position,
                },
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
            for reference in condition.references
        )
        _record(
            records,
            ProjectQueryBlockIRRecordKind.CONDITION,
            ("node", project_query_block_ir_pure_ref(_runtime_ref(joined.node.ref))),
            ("mode", project_query_block_ir_pure_enumeration(condition.mode)),
            (
                "scope",
                _optional_enumeration(
                    None if condition.scope is None else condition.scope.value
                ),
            ),
            (
                "expression",
                PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                if condition.expression is None
                else project_query_block_ir_pure_text(
                    _authored_text(condition.expression, module_path)
                ),
            ),
            (
                "conjuncts",
                project_query_block_ir_pure_texts(
                    tuple(
                        _authored_text(item, module_path)
                        for item in condition.conjuncts
                    )
                ),
            ),
            (
                "base",
                project_query_block_ir_pure_texts(
                    tuple(
                        _authored_text(
                            base.clause,
                            base.relationship.occurrence.identity.module.path,
                        )
                        for base in condition.base_conditions
                    )
                ),
            ),
            ("references", project_query_block_ir_pure_texts(references)),
        )
    for joined in joins:
        for ordinal, item in enumerate(joined.inputs):
            _record(
                records,
                ProjectQueryBlockIRRecordKind.INPUT_CORRESPONDENCE,
                (
                    "node",
                    project_query_block_ir_pure_ref(_runtime_ref(joined.node.ref)),
                ),
                ("ordinal", project_query_block_ir_pure_integer(ordinal)),
                ("use", project_query_block_ir_pure_ref(_runtime_ref(item.use.ref))),
                (
                    "producer",
                    _optional_ref(
                        None
                        if item.producer is None
                        else _owner_ref(inspection, item.producer)
                    ),
                ),
                (
                    "output",
                    project_query_block_ir_pure_ref(_runtime_ref(item.use.output.ref)),
                ),
            )


def _identity_data(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if type(value) in {str, int}:
        return value
    if type(value) in {
        ProjectNominalDeclarationIdentity,
        ProjectDeclarationOccurrenceIdentity,
        ProjectModuleRowFieldIdentity,
    }:
        identity = cast(
            ProjectNominalDeclarationIdentity
            | ProjectDeclarationOccurrenceIdentity
            | ProjectModuleRowFieldIdentity,
            value,
        )
        # A module declaration has no let position; only a relation let's
        # locator carries one. A table-function locator has no portable form
        # yet, so its inspection fails closed here.
        if getattr(identity, "table_function", False) is not False:
            raise TypeError("Portable identity has no table-function locator.")
        return {
            item.name: _identity_data(getattr(identity, item.name))
            for item in dataclass_fields(identity)
            if not (
                item.name == "let_position" and getattr(identity, item.name) is None
            )
            and item.name != "table_function"
        }
    raise TypeError("Portable identity requires a closed semantic locator.")


def _capability_data(capability: ProjectRowEquivalenceField) -> dict[str, object]:
    resolved = capability.selected.field.resolved_type
    resolution = capability.resolution
    return {
        "selected": _identity_data(capability.selected.identity),
        "kind": resolved.kind.value,
        "name": resolved.name,
        "nominal": None
        if resolution is None or resolution.canonical_target_identity is None
        else _identity_data(resolution.canonical_target_identity),
        "declared": None
        if resolution is None
        else _authored_data(
            resolution.reference.type_expr,
            resolution.reference.owner.identity.module_path,
        ),
        "aliases": []
        if resolution is None
        else [_identity_data(identity) for identity in resolution.alias_chain],
        "decimal": None
        if capability.decimal is None
        else [capability.decimal.precision, capability.decimal.scale],
        "reason": None if capability.reason is None else capability.reason.value,
        "declaration_owner": None
        if resolution is None
        else _identity_data(_declaration_identity(resolution.reference.owner)),
        "declaration_role": None
        if resolution is None
        else resolution.reference.role.value,
    }


def _distinct_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
    capabilities: list[
        tuple[ProjectQueryBlockIRPortableRef, ProjectRowEquivalenceField]
    ],
    order_records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    operators = tuple(
        operator
        for operator in inspection.operators
        if isinstance(operator, ProjectIRQueryBlockOperatorOccurrence)
        and isinstance(operator.evidence, ProjectIRDistinctComparison)
    )
    for operator in operators:
        comparison = cast(ProjectIRDistinctComparison, operator.evidence)
        semantic = comparison.semantic
        incoming = tuple(
            p
            for p in inspection.result_properties
            if p.output is comparison.input_output
        )
        if len(incoming) != 1:
            raise ValueError(
                "Portable DISTINCT requires its exact input property root."
            )
        properties = incoming[0]
        fields = tuple(
            _field_ref(inspection, properties, field)
            for field in properties.relational.fields
        )
        first = len(capabilities)
        capabilities.extend(zip(fields, semantic.equivalence.evidence, strict=True))
        origins = tuple(
            i
            for i, origin in enumerate(inspection.grain_origins)
            if isinstance(origin, ProjectIRQueryBlockRowDomainOrigin)
            and origin.occurrence is operator
            and origin.origin is semantic.origin
        )
        if len(origins) != 1:
            raise ValueError("Portable DISTINCT requires its exact quotient origin.")
        order_proofs = _portable_order_evidence(
            inspection, operator, semantic, order_records
        )
        _record(
            records,
            ProjectQueryBlockIRRecordKind.DISTINCT,
            ("node", project_query_block_ir_pure_ref(_runtime_ref(operator.node.ref))),
            (
                "input",
                project_query_block_ir_pure_ref(
                    _runtime_ref(comparison.input_output.occurrence.ref)
                ),
            ),
            ("fields", project_query_block_ir_pure_refs(fields)),
            (
                "types",
                project_query_block_ir_pure_refs(
                    tuple(
                        _portable_ref(
                            ProjectQueryBlockIRPortableRefDomain.TYPE_EVIDENCE,
                            first + i,
                        )
                        for i in range(len(fields))
                    )
                ),
            ),
            (
                "origin",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.GRAIN_ORIGIN, origins[0]
                    )
                ),
            ),
            (
                "nulls_equal",
                project_query_block_ir_pure_boolean(semantic.uniqueness.nulls_equal),
            ),
            ("full_row_unique", project_query_block_ir_pure_boolean(True)),
            (
                "clause",
                project_query_block_ir_pure_text(
                    _authored_text(semantic.clause, semantic.owner.identity.module_path)
                ),
            ),
            ("order_proofs", project_query_block_ir_pure_refs(order_proofs)),
        )


def _portable_order_evidence(inspection, operator, semantic, records):
    """The single adapter for the two retained semantic ORDER proof variants."""
    from pietto._project.project_scalar_references import ProjectScalarEnvironmentField
    from pietto._project.model import ProjectRowField

    K, D = ProjectQueryBlockIRRecordKind, ProjectQueryBlockIRPortableRefDomain
    source_objects = []
    source_refs = []
    result = []
    owner = _owner_ref(inspection, semantic.owner)
    orderings = tuple(
        op for op in inspection.operators if op.evidence is semantic.ordering
    )
    if not semantic.order_proofs:
        return ()
    if len(orderings) != 1 or semantic.ordering is None:
        raise ValueError("ORDER proofs require their exact ordering operator.")

    def allocate(kind, domain):
        return _portable_ref(domain, sum(record.kind is kind for record in records))

    def source_ref(source):
        for original, ref in zip(source_objects, source_refs, strict=True):
            if original is source:
                return ref
        ref = allocate(K.ORDER_SOURCE, D.ORDER_SOURCE)
        source_objects.append(source)
        source_refs.append(ref)
        evidence = (
            source.evidence
            if isinstance(source, ProjectScalarEnvironmentField)
            else source
        )
        field_refs = tuple(
            _field_ref(inspection, properties, field)
            for properties in inspection.result_properties
            for field in properties.relational.fields
            if field.evidence is evidence
        )
        syntax = (
            source
            if isinstance(source, Node)
            else evidence.field_def
            if isinstance(evidence, ProjectRowField)
            else None
        )
        source_module = semantic.owner.identity.module_path
        if isinstance(evidence, ProjectRowField) and evidence.field_def is not None:
            references = tuple(
                resolution.reference
                for environment in semantic.equivalence.types.environments
                for resolution in environment.type_resolutions
                if resolution.reference.type_expr is evidence.field_def.type_expr
            )
            if len(references) != 1:
                raise ValueError(
                    "ORDER field source requires its exact declaration location."
                )
            source_module = references[0].owner.identity.module_path
        _record(
            records,
            K.ORDER_SOURCE,
            ("ref", project_query_block_ir_pure_ref(ref)),
            ("owner", project_query_block_ir_pure_ref(owner)),
            ("source_kind", project_query_block_ir_pure_text(type(source).__name__)),
            ("fields", project_query_block_ir_pure_refs(field_refs)),
            (
                "site",
                PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                if syntax is None
                else project_query_block_ir_pure_text(
                    _authored_text(syntax.span, source_module)
                ),
            ),
        )
        return ref

    for ordinal, proof in enumerate(semantic.order_proofs):
        item = semantic.ordering.items[ordinal]
        if type(proof) is not tuple or len(proof) not in {2, 3} or proof[0] is not item:
            raise ValueError("ORDER proof requires its exact closed item variant.")
        visible = targets = ()
        data = None
        if len(proof) == 3:
            mode = "visible"
            visible = tuple(source_ref(value) for value in proof[1])
            targets = tuple(source_ref(value) for value in proof[2])
        else:
            mode = "strict_fd"
            data = _portable_fd_determination(inspection, proof[1])
        binding_ref = allocate(K.ORDER_BINDING, D.ORDER_BINDING)
        proof_ref = allocate(K.ORDER_PROOF, D.ORDER_PROOF)
        common = (
            ("mode", project_query_block_ir_pure_enumeration(mode)),
            ("visible", project_query_block_ir_pure_refs(visible)),
            ("targets", project_query_block_ir_pure_refs(targets)),
            (
                "property",
                _optional_ref(
                    None
                    if data is None
                    else _portable_ref(D.RELATIONAL_PROPERTY, data["property"])
                ),
            ),
            (
                "seed",
                project_query_block_ir_pure_refs(
                    ()
                    if data is None
                    else tuple(_portable_ref(D.VALUE_CLASS, i) for i in data["seed"])
                ),
            ),
            (
                "requested",
                project_query_block_ir_pure_refs(
                    ()
                    if data is None
                    else tuple(
                        _portable_ref(D.VALUE_CLASS, i) for i in data["requested"]
                    )
                ),
            ),
        )
        _record(
            records,
            K.ORDER_BINDING,
            ("ref", project_query_block_ir_pure_ref(binding_ref)),
            ("owner", project_query_block_ir_pure_ref(owner)),
            (
                "ordering",
                project_query_block_ir_pure_ref(_runtime_ref(orderings[0].node.ref)),
            ),
            ("ordinal", project_query_block_ir_pure_integer(ordinal)),
            (
                "item",
                project_query_block_ir_pure_text(
                    _authored_text(item.item, semantic.owner.identity.module_path)
                ),
            ),
            *common,
        )
        _record(
            records,
            K.ORDER_PROOF,
            ("ref", project_query_block_ir_pure_ref(proof_ref)),
            ("binding", project_query_block_ir_pure_ref(binding_ref)),
            *common,
            (
                "closure",
                project_query_block_ir_pure_refs(
                    ()
                    if data is None
                    else tuple(_portable_ref(D.VALUE_CLASS, i) for i in data["closure"])
                ),
            ),
            (
                "steps",
                project_query_block_ir_pure_texts(
                    ()
                    if data is None
                    else tuple(
                        json.dumps(step, separators=(",", ":"))
                        for step in data["steps"]
                    )
                ),
            ),
        )
        result.append(proof_ref)
    return tuple(result)


class _PortableFDStep(TypedDict):
    fact: int
    derived: list[int]


class _PortableFDDetermination(TypedDict):
    mode: Literal["strict_fd"]
    property: int
    seed: list[int]
    requested: list[int]
    closure: list[int]
    steps: list[_PortableFDStep]
    status: str


def _portable_fd_determination(
    inspection: ProjectIRQueryBlockInspection, proof: object
) -> _PortableFDDetermination:
    from pietto._project.project_ir_relational_properties import (
        ProjectIROutputDeterminationResult,
    )

    if type(proof) is not ProjectIROutputDeterminationResult:
        raise TypeError("Portable ORDER proof requires exact strict-FD evidence.")
    if proof.status.value != "proven":
        raise ValueError("ORDER requires an already-proven retained FD witness.")
    index = proof.seed.index
    matches = tuple(
        p
        for p in inspection.result_properties
        if p.relational.fd_index is index
        or any(
            join.source_properties.fd_index is index and p.output is join.output
            for join in inspection.algebra_joins
        )
    )
    if len(matches) != 1:
        raise ValueError("ORDER proof requires its exact combined property image.")
    properties = matches[0]

    def mapped_class(value):
        if properties.relational.fd_index is index:
            return value
        positions = tuple(member.field_position for member in value.members)
        matches = tuple(
            item
            for item in properties.relational.value_classes
            if tuple(member.field_position for member in item.members) == positions
        )
        if len(matches) != 1:
            raise ValueError("FD class requires its exact composed field image.")
        return matches[0]

    def positions(values):
        return [
            _class_ref(inspection, properties, mapped_class(value)).position
            for value in values
        ]

    def fact_position(fact):
        if properties.relational.fd_index is index:
            return _fd_ref(inspection, properties, fact).position
        determinants = tuple(mapped_class(value) for value in fact.determinants)
        dependents = tuple(mapped_class(value) for value in fact.dependents)
        matches = tuple(
            item
            for item in properties.relational.fds
            if item.strength is fact.strength
            and _same_objects(item.determinants, determinants)
            and _same_objects(item.dependents, dependents)
        )
        if len(matches) != 1:
            raise ValueError("FD witness requires its exact composed fact image.")
        return _fd_ref(inspection, properties, matches[0]).position

    return {
        "mode": "strict_fd",
        "property": _result_property_ref(inspection, properties).position,
        "seed": positions(proof.seed.classes),
        "requested": positions(proof.requested.classes),
        "closure": positions(proof.closure.classes.classes),
        "steps": [
            {"fact": fact_position(step.fact), "derived": positions(step.derived)}
            for step in proof.closure.witness
        ],
        "status": proof.status.value,
    }


def _capability_field(inspection, capability):
    from pietto._project.project_row_equivalence import ProjectRowEquivalenceInput
    from pietto._project.project_final_outputs import ProjectCompletedEffectiveOutput

    selected = capability.selected
    if isinstance(selected, ProjectRowEquivalenceInput):
        entries = tuple(
            entry
            for entry in inspection.entries
            if not isinstance(entry, ProjectIRQueryBlockTerminal)
            and entry.semantic_entry is selected.authority.entry
        )
    else:
        entries = tuple(
            entry
            for entry in inspection.entries
            if not isinstance(entry, ProjectIRQueryBlockTerminal)
            and isinstance(entry.semantic_entry, ProjectCompletedEffectiveOutput)
            and any(field is selected for field in entry.semantic_entry.fields)
        )
    if len(entries) != 1:
        raise ValueError("Type parent requires its exact represented producer.")
    properties = entries[0].active_properties
    return _field_ref(
        inspection,
        properties,
        properties.relational.fields[selected.identity.field_position],
    )


def _capability_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
    capabilities: list[
        tuple[ProjectQueryBlockIRPortableRef, ProjectRowEquivalenceField]
    ],
) -> None:
    from pietto.ast_nodes import LiteralExpr

    K, D = ProjectQueryBlockIRRecordKind, ProjectQueryBlockIRPortableRefDomain
    parent_rows: list[tuple[ProjectQueryBlockIRPortableRef, ...]] = []
    # Keep each root/input and each parent-use occurrence; never deduplicate uses.
    ancestry: list[tuple[ProjectRowEquivalenceField, ...]] = [()] * len(capabilities)
    position = 0
    while position < len(capabilities):
        capability = capabilities[position][1]
        path = (*ancestry[position], capability)
        if any(
            parent is ancestor for parent in capability.parents for ancestor in path
        ):
            raise ValueError("Type parent evidence cannot contain a cycle.")
        ancestry.extend(path for _ in capability.parents)
        start = len(capabilities)
        capabilities.extend(
            (_capability_field(inspection, parent), parent)
            for parent in capability.parents
        )
        parent_rows.append(
            tuple(
                _portable_ref(D.TYPE_EVIDENCE, start + i)
                for i in range(len(capability.parents))
            )
        )
        position += 1
    sources: list[ProjectQueryBlockIRPureRecord] = []
    for position, ((field_ref, capability), parents) in enumerate(
        zip(capabilities, parent_rows, strict=True)
    ):
        cap_ref = _portable_ref(D.TYPE_EVIDENCE, position)
        expression = capability.decimal_type_expr
        source_ref = None
        if expression is not None:
            matches = tuple(
                resolution.reference
                for environment in capability.types.environments
                for resolution in environment.type_resolutions
                if resolution.reference.type_expr is expression
            )
            if len(matches) != 1 or capability.decimal is None:
                raise ValueError(
                    "Decimal source requires its exact terminal type authority."
                )
            reference = matches[0]
            arguments = tuple(argument.value for argument in expression.arguments)
            if len(arguments) != 2 or any(
                not isinstance(argument, LiteralExpr) or type(argument.value) is not int
                for argument in arguments
            ):
                raise ValueError(
                    "Decimal source must retain validated literal parameters."
                )
            parameters = tuple(
                argument.value
                for argument in arguments
                if isinstance(argument, LiteralExpr) and type(argument.value) is int
            )
            if parameters != (capability.decimal.precision, capability.decimal.scale):
                raise ValueError(
                    "Decimal recorded parameters disagree with retained validation."
                )
            source_ref = _portable_ref(D.TYPE_PARAMETER_SOURCE, len(sources))
            _record(
                sources,
                K.TYPE_PARAMETER_SOURCE,
                ("ref", project_query_block_ir_pure_ref(source_ref)),
                ("capability", project_query_block_ir_pure_ref(cap_ref)),
                (
                    "owner",
                    project_query_block_ir_pure_text(
                        json.dumps(
                            _identity_data(_declaration_identity(reference.owner)),
                            separators=(",", ":"),
                        )
                    ),
                ),
                ("role", project_query_block_ir_pure_enumeration(reference.role.value)),
                ("type_name", project_query_block_ir_pure_enumeration(expression.name)),
                (
                    "site",
                    project_query_block_ir_pure_text(
                        _authored_text(
                            expression.span, reference.owner.identity.module_path
                        )
                    ),
                ),
                ("parameters", project_query_block_ir_pure_integers(parameters)),
                (
                    "argument_sites",
                    project_query_block_ir_pure_texts(
                        tuple(
                            _authored_text(
                                argument.span, reference.owner.identity.module_path
                            )
                            for argument in expression.arguments
                        )
                    ),
                ),
            )
        _record(
            records,
            K.TYPE_EQUIVALENCE,
            ("ref", project_query_block_ir_pure_ref(cap_ref)),
            ("field", project_query_block_ir_pure_ref(field_ref)),
            (
                "capability",
                project_query_block_ir_pure_text(
                    json.dumps(
                        _capability_data(capability),
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                    )
                ),
            ),
            ("parents", project_query_block_ir_pure_refs(parents)),
            ("parameter_source", _optional_ref(source_ref)),
        )
    records.extend(sources)


def _set_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
    capabilities: list[
        tuple[ProjectQueryBlockIRPortableRef, ProjectRowEquivalenceField]
    ],
) -> None:
    from pietto.ast_nodes import SetRelationDef

    for entry in inspection.set_entries:
        semantic = entry.semantic_entry
        definition = semantic.owner.definition
        if (
            not isinstance(definition, SetRelationDef)
            or definition.body.quantifier is None
        ):
            raise ValueError(
                "Set observation requires an explicit authored quantifier."
            )
        origins = tuple(
            i
            for i, origin in enumerate(inspection.grain_origins)
            if isinstance(origin, ProjectIRQueryBlockRowDomainOrigin)
            and origin.occurrence is entry.operator
            and origin.origin is semantic.row_domain.set_origin
        )
        if len(origins) != 1:
            raise ValueError("Set observation requires its exact row-domain origin.")
        _record(
            records,
            ProjectQueryBlockIRRecordKind.SET,
            (
                "node",
                project_query_block_ir_pure_ref(_runtime_ref(entry.operator.node.ref)),
            ),
            (
                "output",
                project_query_block_ir_pure_ref(
                    _runtime_ref(entry.active_output.occurrence.ref)
                ),
            ),
            (
                "kind",
                project_query_block_ir_pure_enumeration(definition.body.kind.value),
            ),
            (
                "quantifier",
                project_query_block_ir_pure_enumeration(
                    definition.body.quantifier.value
                ),
            ),
            ("operand_count", project_query_block_ir_pure_integer(len(entry.operands))),
            (
                "requires_equivalence",
                project_query_block_ir_pure_boolean(semantic.root.requires_equivalence),
            ),
            (
                "full_row_unique",
                project_query_block_ir_pure_boolean(semantic.root.full_row_unique),
            ),
            (
                "origin",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.GRAIN_ORIGIN, origins[0]
                    )
                ),
            ),
            (
                "span",
                project_query_block_ir_pure_text(
                    _authored_text(
                        definition.body.operator_span,
                        semantic.owner.identity.module_path,
                    )
                ),
            ),
        )
    for entry in inspection.set_entries:
        for ordinal, operand in enumerate(entry.operands):
            properties = operand.producer.active_properties
            fields = tuple(
                _field_ref(inspection, properties, field)
                for field in properties.relational.fields
            )
            first = len(capabilities)
            capabilities.extend(zip(fields, operand.source.fields, strict=True))
            _record(
                records,
                ProjectQueryBlockIRRecordKind.SET_OPERAND,
                (
                    "node",
                    project_query_block_ir_pure_ref(
                        _runtime_ref(entry.operator.node.ref)
                    ),
                ),
                ("ordinal", project_query_block_ir_pure_integer(ordinal)),
                ("use", project_query_block_ir_pure_ref(_runtime_ref(operand.use.ref))),
                (
                    "producer",
                    project_query_block_ir_pure_ref(
                        _owner_ref(inspection, operand.producer.owner)
                    ),
                ),
                (
                    "output",
                    project_query_block_ir_pure_ref(
                        _runtime_ref(operand.producer.active_output.occurrence.ref)
                    ),
                ),
                ("fields", project_query_block_ir_pure_refs(fields)),
                (
                    "types",
                    project_query_block_ir_pure_refs(
                        tuple(
                            _portable_ref(
                                ProjectQueryBlockIRPortableRefDomain.TYPE_EVIDENCE,
                                first + i,
                            )
                            for i in range(len(fields))
                        )
                    ),
                ),
            )
    for entry in inspection.set_entries:
        uses = tuple(operand.source for operand in entry.operands)
        for position, set_field in enumerate(entry.semantic_entry.fields):

            def mapped_uses(sources):
                return tuple(
                    _runtime_ref(
                        entry.operands[
                            _position(uses, use, "set operand occurrence")
                        ].use.ref
                    )
                    for use, _capability in sources
                )

            _record(
                records,
                ProjectQueryBlockIRRecordKind.SET_FIELD_MAP,
                (
                    "node",
                    project_query_block_ir_pure_ref(
                        _runtime_ref(entry.operator.node.ref)
                    ),
                ),
                ("position", project_query_block_ir_pure_integer(position)),
                (
                    "output",
                    project_query_block_ir_pure_ref(
                        _field_ref(
                            inspection,
                            entry.active_properties,
                            entry.active_properties.relational.fields[position],
                        )
                    ),
                ),
                (
                    "inputs",
                    project_query_block_ir_pure_refs(
                        tuple(
                            _field_ref(
                                inspection,
                                operand.producer.active_properties,
                                operand.producer.active_properties.relational.fields[
                                    position
                                ],
                            )
                            for operand in entry.operands
                        )
                    ),
                ),
                (
                    "value_uses",
                    project_query_block_ir_pure_refs(
                        mapped_uses(set_field.source.value_sources)
                    ),
                ),
                (
                    "membership_uses",
                    project_query_block_ir_pure_refs(
                        mapped_uses(set_field.source.membership_sources)
                    ),
                ),
            )


def _requirement_records(
    inspection: ProjectIRQueryBlockInspection,
    records: list[ProjectQueryBlockIRPureRecord],
) -> None:
    proof_rows: list[
        tuple[ProjectIRSingleMatchRetention, ProjectIRSingleMatchProofImage]
    ] = []

    def collect(requirement, proof):
        proof_rows.append((requirement, proof))
        for child in proof.children:
            collect(requirement, child)

    for requirement in inspection.requirements:
        for proof in requirement.proofs:
            collect(requirement, proof)

    def proof_ref(proof):
        return _portable_ref(
            ProjectQueryBlockIRPortableRefDomain.PROOF,
            _position(tuple(row[1] for row in proof_rows), proof, "proof image"),
        )

    for position, diagnostic in enumerate(inspection.diagnostics):
        location = diagnostic.location
        _record(
            records,
            ProjectQueryBlockIRRecordKind.DIAGNOSTIC,
            (
                "ref",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.DIAGNOSTIC, position
                    )
                ),
            ),
            ("code", project_query_block_ir_pure_text(diagnostic.code)),
            (
                "severity",
                project_query_block_ir_pure_enumeration(diagnostic.severity.value),
            ),
            ("message", project_query_block_ir_pure_text(diagnostic.message)),
            (
                "path",
                PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                if location.path is None
                else project_query_block_ir_pure_text(location.path),
            ),
            ("line", project_query_block_ir_pure_integer(location.line)),
            ("column", project_query_block_ir_pure_integer(location.column)),
            ("end_line", _optional_integer(location.end_line)),
            ("end_column", _optional_integer(location.end_column)),
        )
    for requirement in inspection.requirements:
        assessment = requirement.assessment
        request = assessment.request
        condition = assessment.condition
        diagnostic = assessment.diagnostic
        _record(
            records,
            ProjectQueryBlockIRRecordKind.REQUIREMENT,
            (
                "ref",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.REQUIREMENT,
                        requirement.position,
                    )
                ),
            ),
            (
                "owner",
                _optional_ref(
                    None
                    if requirement.owner_entry is None
                    else _owner_ref(inspection, requirement.owner_entry.owner)
                ),
            ),
            (
                "scope",
                project_query_block_ir_pure_enumeration(
                    request.scope.value
                    if isinstance(request.scope, Enum)
                    else "invalid"
                ),
            ),
            (
                "unit",
                project_query_block_ir_pure_enumeration(
                    request.unit.value if isinstance(request.unit, Enum) else "invalid"
                ),
            ),
            ("state", project_query_block_ir_pure_enumeration(assessment.state.value)),
            (
                "enforcement_required",
                project_query_block_ir_pure_boolean(
                    assessment.downstream_enforcement_required
                ),
            ),
            (
                "represented",
                project_query_block_ir_pure_boolean(bool(requirement.boundaries)),
            ),
            (
                "joins",
                project_query_block_ir_pure_refs(
                    tuple(
                        _runtime_ref(join.node.ref) for join in requirement.boundaries
                    )
                ),
            ),
            (
                "inputs",
                project_query_block_ir_pure_refs(
                    tuple(
                        _runtime_ref(use.ref)
                        for pair in requirement.input_pairs
                        for use in pair
                    )
                ),
            ),
            (
                "proofs",
                project_query_block_ir_pure_refs(
                    tuple(proof_ref(proof) for proof in requirement.proofs)
                ),
            ),
            (
                "diagnostic",
                _optional_ref(
                    None
                    if diagnostic is None
                    else _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.DIAGNOSTIC,
                        _position(
                            inspection.diagnostics, diagnostic, "request diagnostic"
                        ),
                    )
                ),
            ),
            (
                "site",
                PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
                if condition is None
                else project_query_block_ir_pure_text(
                    _authored_text(
                        condition.use.clause, condition.use.owner.identity.module_path
                    )
                ),
            ),
            ("problems", project_query_block_ir_pure_texts(assessment.problems)),
        )
    for requirement, proof in proof_rows:
        _record(
            records,
            ProjectQueryBlockIRRecordKind.PROOF,
            ("ref", project_query_block_ir_pure_ref(proof_ref(proof))),
            (
                "requirement",
                project_query_block_ir_pure_ref(
                    _portable_ref(
                        ProjectQueryBlockIRPortableRefDomain.REQUIREMENT,
                        requirement.position,
                    )
                ),
            ),
            ("kind", project_query_block_ir_pure_enumeration(proof.source.kind.value)),
            (
                "joins",
                project_query_block_ir_pure_refs(
                    tuple(_runtime_ref(join.node.ref) for join in proof.boundaries)
                ),
            ),
            (
                "inputs",
                project_query_block_ir_pure_refs(
                    tuple(
                        _runtime_ref(use.ref)
                        for join in proof.boundaries
                        for use in join.input_uses
                    )
                ),
            ),
            (
                "producers",
                project_query_block_ir_pure_refs(
                    tuple(
                        _owner_ref(inspection, entry.owner) for entry in proof.producers
                    )
                ),
            ),
            (
                "premise_nodes",
                project_query_block_ir_pure_refs(
                    tuple(_runtime_ref(node.ref) for node in proof.premise_nodes)
                ),
            ),
            (
                "children",
                project_query_block_ir_pure_refs(
                    tuple(proof_ref(child) for child in proof.children)
                ),
            ),
            (
                "roots",
                project_query_block_ir_pure_texts(
                    tuple(
                        json.dumps(
                            _proof_root_data(root, requirement, proof, inspection),
                            ensure_ascii=False,
                            allow_nan=False,
                            separators=(",", ":"),
                        )
                        for root in proof.source.roots
                    )
                ),
            ),
        )
    for entry in inspection.terminals:
        if entry.reason.value != "active_inputs_ir_non_concrete":
            continue
        for ordinal, blocker in enumerate(
            cast(tuple[ProjectIRQueryBlockTerminal, ...], entry.blocker)
        ):
            _record(
                records,
                ProjectQueryBlockIRRecordKind.TERMINAL_INPUT,
                (
                    "owner",
                    project_query_block_ir_pure_ref(
                        _owner_ref(inspection, entry.owner)
                    ),
                ),
                ("ordinal", project_query_block_ir_pure_integer(ordinal)),
                (
                    "blocker",
                    project_query_block_ir_pure_ref(
                        _owner_ref(inspection, blocker.owner)
                    ),
                ),
            )


def _proof_root_data(
    root: object,
    requirement: ProjectIRSingleMatchRetention,
    proof: ProjectIRSingleMatchProofImage,
    inspection: ProjectIRQueryBlockInspection,
) -> dict[str, object]:
    from pietto._project.project_single_match import ProjectSingleMatchProof
    from pietto._project.project_completion import ProjectExistingEffectiveOutput
    from pietto._project.project_relationship_paths import (
        ProjectRelationshipPath,
        ProjectRelationshipPathStep,
    )
    from pietto._project.project_relationship_match_guarantees import (
        ProjectDirectionalRelationshipMatchGuarantee,
        ProjectRefinedMatchBounds,
    )
    from pietto._project.project_join_conditions import ProjectJoinCondition
    from pietto._project.project_final_outputs import (
        ProjectRelationLimit,
        ProjectCompletedEffectiveOutput,
        ProjectCompletedSetOutput,
    )
    from pietto._project.project_joined_aggregation import (
        ProjectConcreteJoinedAggregation,
    )
    from pietto._project.project_current_joins import ProjectCurrentBinaryJoin
    from pietto._project.project_ir_joins import ProjectIRBinaryJoinOccurrence

    data: dict[str, object] = {"kind": type(root).__name__}
    if isinstance(
        root,
        (
            ProjectExistingEffectiveOutput,
            ProjectCompletedEffectiveOutput,
            ProjectCompletedSetOutput,
        ),
    ):
        matches = tuple(
            entry for entry in proof.producers if entry.semantic_entry is root
        )
        if len(matches) != 1:
            raise ValueError("Proof producer lost its exact IR entry image.")
        data["owner"] = _owner_ref(inspection, matches[0].owner).position
    elif isinstance(root, ProjectSingleMatchProof):
        data["child"] = _position(
            tuple(child.source for child in proof.children), root, "proof child"
        )
        data["proof_kind"] = root.kind.value
    elif isinstance(root, ProjectRelationshipPath):
        data["steps"] = [
            _proof_root_data(step, requirement, proof, inspection)
            for step in root.steps
        ]
    elif isinstance(root, ProjectRelationshipPathStep):
        data["position"] = root.position
        data["guarantee"] = _proof_root_data(
            root.guarantee, requirement, proof, inspection
        )
    elif isinstance(root, ProjectRefinedMatchBounds):
        data["base"] = _proof_root_data(root.base, requirement, proof, inspection)
        data["maximum"] = root.maximum.value
        data["minimum"] = root.minimum.value
    elif isinstance(root, ProjectDirectionalRelationshipMatchGuarantee):
        direction = root.direction
        data.update(
            {
                "module": direction.declaration.module.path,
                "relationship_position": direction.declaration.relationship_position,
                "source_endpoint": direction.source.identity.endpoint_position,
                "target_endpoint": direction.target.identity.endpoint_position,
                "maximum": root.maximum.value,
                "minimum": root.minimum.value,
                "maximum_evidence": type(root.maximum_evidence).__name__,
                "source_matched": [
                    [field.field_position for field in group.members]
                    for group in root.source_matched_classes
                ],
                "target_matched": [
                    [field.field_position for field in group.members]
                    for group in root.target_matched_classes
                ],
            }
        )
    elif isinstance(root, ProjectJoinConditionKeyMatch):
        data["key_match"] = _position(
            inspection.predicate_key_matches, root, "predicate key match"
        )
    elif isinstance(root, ProjectJoinConditionEquality):
        data["equality"] = _position(
            inspection.predicate_equalities, root, "predicate equality"
        )
    elif isinstance(root, ProjectIROutputCandidateKey):
        data["key_matches"] = [
            _position(inspection.predicate_key_matches, match, "predicate key match")
            for match in proof.source.roots
            if isinstance(match, ProjectJoinConditionKeyMatch) and match.key is root
        ]
        if not data["key_matches"]:
            raise ValueError("Matched-key root lost its exact key-match proof.")
    elif isinstance(root, ProjectJoinCondition):
        data.update(
            {
                "mode": root.mode,
                "clause": _authored_data(
                    root.use.clause, root.use.owner.identity.module_path
                ),
            }
        )
    elif isinstance(root, ProjectRelationLimit):
        data.update(
            {
                "owner": _owner_ref(inspection, root.owner).position,
                "bound": root.row_count_upper_bound,
                "clause": _authored_data(root.clause, root.owner.identity.module_path),
            }
        )
    elif isinstance(root, (ProjectIRBinaryJoinOccurrence, ProjectCurrentBinaryJoin)):
        matches = tuple(
            join
            for join in requirement.boundaries
            if join is root
            or isinstance(join, ProjectIRComposedJoin)
            and join.source is root
        )
        data["nodes"] = [join.node.ref.position for join in matches]
    elif isinstance(root, ProjectIRJoinInputUseOccurrence):
        pairs = tuple(
            (old, new)
            for original, mapped in zip(
                requirement.assessment.joins, requirement.boundaries, strict=False
            )
            for old, new in zip(original.input_uses, mapped.input_uses, strict=True)
        )
        data["uses"] = [new.ref.position for old, new in pairs if old is root]
    elif isinstance(root, ProjectIRLogicalOperatorOccurrence):
        data["operator_kind"] = root.kind.value
        data["premise_nodes"] = [node.ref.position for node in proof.premise_nodes]
    elif isinstance(root, ProjectConcreteNoJoinReplay):
        data.update(
            {
                "owner": _owner_ref(inspection, root.owner).position,
                "mode": root.mode.value,
            }
        )
    elif isinstance(root, ProjectConcreteJoinedAggregation):
        data.update(
            {
                "owner": _owner_ref(inspection, root.input_filter.entry.owner).position,
                "mode": root.mode.value,
            }
        )
    else:
        raise TypeError("Proof observation requires a closed retained root family.")
    return data


def _uses_flat_format(inspection: ProjectIRQueryBlockInspection) -> bool:
    return bool(
        inspection.algebra_joins
        or inspection.set_entries
        or inspection.requirements
        or _has_set_outputs(inspection.completed)
        or _has_distinct(inspection.completed)
    )
