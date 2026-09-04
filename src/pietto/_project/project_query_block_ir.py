"""Private Phase-63 query-block Project IR overlay and property transfer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectRelationClauseDependencyFact,
    ProjectRelationClauseDependencyKind,
)
from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
)
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleDependencyKind,
    ProjectModuleReferenceOccurrenceIdentity,
    ProjectModuleReferenceRole,
    ProjectModuleRowFieldIdentity,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_relation_resolution import (
    ProjectResolvedModuleRelationReference,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
    ProjectModuleWindowOutputFact,
)
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
)
from pietto._project.project_completion import (
    ProjectCompletionDependency,
    ProjectEffectiveOutputTerminal,
    ProjectExistingEffectiveOutput,
)
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectCompletedOutputField,
    ProjectConcreteNoJoinReplay,
    ProjectEffectiveOutputCompletionEntry,
    ProjectEffectiveOutputCompletionTerminal,
    ProjectNoJoinGroupedOutput,
    ProjectNoJoinHiddenWindowComputation,
    ProjectNoJoinQualifyKind,
    ProjectNoJoinScalarExpression,
    ProjectNoJoinWhereKind,
    ProjectRelationLimit,
    ProjectRelationOrdering,
)
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectGrainDependencyFact,
    ProjectGrainDomainFactor,
    ProjectGrainFactorIdentity,
    ProjectGrainOriginAuthority,
    ProjectGrainOriginKind,
    ProjectGrainOriginSet,
    ProjectGroupedGrainFactorIdentity,
)
from pietto._project.project_ir import (
    ProjectIRFieldAnchor,
    ProjectIRInputSlotOccurrence,
    ProjectIRInputSlotRef,
    ProjectIRJoinInputUseOccurrence,
    ProjectIROperatorFlowUseOccurrence,
    ProjectIROutputValueOccurrence,
    ProjectIROutputValueRef,
    ProjectIRPlanNodeOccurrence,
    ProjectIRPlanNodeRef,
    ProjectIRRelationAnchor,
    ProjectIRResolvedRelationAnchor,
    ProjectIRStageFieldAnchor,
    ProjectIRUseOccurrence,
    ProjectIRUseRef,
    _declaration_identity,
)
from pietto._project.project_ir_composition import (
    ProjectIRCrossRelationEdge,
    ProjectIRProjectPlan,
)
from pietto._project.project_ir_construction import (
    ProjectIRAllocationState,
    ProjectIRConcreteSingleRelationFragment,
    build_project_ir_single_relation_fragment,
)
from pietto._project.project_ir_evaluation_context import (
    ProjectIRGroupedEvaluationContext,
)
from pietto._project.project_ir_joins import (
    ProjectIRConcreteJoinRegion,
    ProjectIRJoinRegionStage,
)
from pietto._project.project_ir_operators import (
    ProjectIRLogicalOperatorKind,
    ProjectIRLogicalOperatorOccurrence,
)
from pietto._project.project_ir_properties import (
    ProjectIRDeterminismEvidence,
    ProjectIREffectEvidence,
    ProjectIRErrorBehaviorEvidence,
    ProjectIREvaluationCountEvidence,
    ProjectIRJoinRowOutput,
    ProjectIRJoinedRowField,
    ProjectIRProvidedCardinalityUpperBound,
    ProjectIRProvidedRelationOrdering,
    ProjectIRRelationRowOutput,
    ProjectIRRowField,
    ProjectIRSideEffectEvidence,
    ProjectIRStageRowField,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRProvidedIntrinsicGrain,
    ProjectIRRelationalRowOutput,
    ProjectIRRelationalRowOutputExtension,
    ProjectIROutputCandidateKey,
    ProjectIROutputFieldOccurrence,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueClass,
    _compile_output_fd_index,
    _field_occurrences,
    _image_keys_and_fds,
    _key_fds,
    _preserving_classes,
    _projection_classes_from_sources,
    _projection_images,
    _singleton_classes,
)
from pietto._project.project_joined_aggregation import (
    ProjectConcreteJoinedAggregation,
    ProjectJoinedAggregationMode,
    ProjectJoinedSatisfyingAnalysis,
    ProjectJoinedStageOutputOccurrence,
    ProjectJoinedStageOutputRole,
)
from pietto._project.project_joined_qualify import (
    ProjectConcreteJoinedQualify,
    ProjectJoinedQualifyStageKind,
)
from pietto._project.project_joined_row_filter import (
    ProjectConcreteJoinedRowFilter,
    ProjectJoinedRowFilterKind,
    ProjectJoinedRowMultiplicity,
)
from pietto._project.project_joined_row_semantics import (
    ProjectJoinedRowFieldSemantics,
)
from pietto._project.project_joined_windows import (
    ProjectConcreteWindowComputation,
    ProjectSelectedWindowResultBinding,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength
from pietto._project.project_scalar_references import (
    ProjectScalarReferenceResolution,
)
from pietto._project.project_scalar_namespaces import (
    ProjectConcreteJoinedNamespaceExpression,
)
from pietto.ast_nodes import DottedNameExpr, NameExpr, QueryDef, SourceDef, TableDef

__all__: tuple[str, ...] = ()


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


class ProjectIRQueryBlockOperatorExtensionKind(StrEnum):
    """The sole additive operator absent from the historical eight-value enum."""

    QUALIFY = "qualify"


type ProjectIRQueryBlockOperatorKind = (
    ProjectIRLogicalOperatorKind | ProjectIRQueryBlockOperatorExtensionKind
)


type ProjectIRQueryBlockWindowSelectedEvidence = (
    ProjectConcreteWindowComputation | ProjectModuleWindowOutputFact
)
type ProjectIRQueryBlockWindowHiddenEvidence = (
    ProjectConcreteWindowComputation | ProjectNoJoinHiddenWindowComputation
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockWindowEvidence:
    """Exact selected and hidden computations for one semantic window stage."""

    completed_output: ProjectCompletedEffectiveOutput = field(
        repr=False,
        compare=False,
        hash=False,
    )
    selected: tuple[ProjectIRQueryBlockWindowSelectedEvidence, ...]
    hidden: tuple[ProjectIRQueryBlockWindowHiddenEvidence, ...]

    def __post_init__(self) -> None:
        if type(self.completed_output) is not ProjectCompletedEffectiveOutput:
            raise TypeError("Window evidence requires one exact completed output.")
        root = self.completed_output.root
        if type(root) is ProjectConcreteJoinedQualify:
            expected_selected = root.window_stage.computations
            expected_hidden = root.hidden_computations
        else:
            if type(root) is not ProjectConcreteNoJoinReplay:
                raise TypeError("Window evidence requires one closed semantic root.")
            expected_selected = root.window_outputs
            expected_hidden = root.qualify.hidden_attempts
        if not _same_objects(
            cast(tuple[object, ...], self.selected),
            cast(tuple[object, ...], expected_selected),
        ) or not _same_objects(
            cast(tuple[object, ...], self.hidden),
            cast(tuple[object, ...], expected_hidden),
        ):
            raise ValueError("Window evidence must retain exact Slice-10/12 roots.")


type ProjectIRQueryBlockOperatorEvidence = (
    ProjectConcreteJoinedRowFilter
    | ProjectConcreteJoinedAggregation
    | ProjectJoinedSatisfyingAnalysis
    | ProjectIRQueryBlockWindowEvidence
    | ProjectConcreteJoinedQualify
    | ProjectConcreteNoJoinReplay
    | ProjectCompletedEffectiveOutput
    | ProjectRelationOrdering
    | ProjectRelationLimit
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockOperatorOccurrence:
    """One query-block operator with exact retained semantic-stage evidence."""

    node: ProjectIRPlanNodeOccurrence
    kind: ProjectIRQueryBlockOperatorKind
    evidence: ProjectIRQueryBlockOperatorEvidence = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.node) is not ProjectIRPlanNodeOccurrence:
            raise TypeError("Query-block operator requires an exact plan node.")
        if type(self.kind) not in {
            ProjectIRLogicalOperatorKind,
            ProjectIRQueryBlockOperatorExtensionKind,
        }:
            raise TypeError("Query-block operator requires one closed kind.")
        if type(self.evidence) not in {
            ProjectConcreteJoinedRowFilter,
            ProjectConcreteJoinedAggregation,
            ProjectJoinedSatisfyingAnalysis,
            ProjectIRQueryBlockWindowEvidence,
            ProjectConcreteJoinedQualify,
            ProjectConcreteNoJoinReplay,
            ProjectCompletedEffectiveOutput,
            ProjectRelationOrdering,
            ProjectRelationLimit,
        }:
            raise TypeError("Query-block operator requires closed semantic evidence.")
        if _operator_evidence_owner(self.evidence) != self.node.anchor.identity:
            raise ValueError("Query-block operator evidence must match its owner.")


def _operator_evidence_owner(
    evidence: ProjectIRQueryBlockOperatorEvidence,
) -> ProjectDeclarationOccurrenceIdentity:
    if type(evidence) is ProjectConcreteJoinedRowFilter:
        owner = evidence.entry.owner
    elif type(evidence) is ProjectConcreteJoinedAggregation:
        owner = evidence.input_filter.entry.owner
    elif type(evidence) is ProjectJoinedSatisfyingAnalysis:
        owner = evidence.input_filter.entry.owner
    elif type(evidence) is ProjectIRQueryBlockWindowEvidence:
        owner = evidence.completed_output.owner
    elif type(evidence) is ProjectConcreteJoinedQualify:
        owner = evidence.window_stage.input_aggregation.input_filter.entry.owner
    elif type(evidence) is ProjectConcreteNoJoinReplay:
        owner = evidence.owner
    elif type(evidence) is ProjectCompletedEffectiveOutput:
        owner = evidence.owner
    elif type(evidence) is ProjectRelationOrdering:
        owner = evidence.owner
    elif type(evidence) is ProjectRelationLimit:
        owner = evidence.owner
    else:
        raise TypeError("Operator evidence requires a closed exact owner.")
    return _declaration_identity(owner)


type ProjectIRQueryBlockAggregateOperator = (
    ProjectIRLogicalOperatorOccurrence | ProjectIRQueryBlockOperatorOccurrence
)
type ProjectIRQueryBlockAggregateSemanticBasis = (
    ProjectConcreteJoinedAggregation
    | ProjectConcreteNoJoinReplay
    | ProjectModuleRelationSemanticFacts
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockAggregateEvaluationContext(ProjectIRGroupedEvaluationContext):
    """Exact aggregate authority adapter for a newly allocated group node."""

    operator: ProjectIRQueryBlockAggregateOperator
    semantic_basis: ProjectIRQueryBlockAggregateSemanticBasis = field(
        repr=False,
        compare=False,
        hash=False,
    )
    mode: ProjectJoinedAggregationMode
    group_keys: tuple[object, ...]
    aggregate_outputs: tuple[object, ...]

    def __post_init__(self) -> None:
        if (
            type(self.operator)
            not in {
                ProjectIRLogicalOperatorOccurrence,
                ProjectIRQueryBlockOperatorOccurrence,
            }
            or self.operator.kind is not ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
        ):
            raise ValueError("Aggregate context requires one exact group operator.")
        if (
            type(self.semantic_basis)
            not in {
                ProjectConcreteJoinedAggregation,
                ProjectConcreteNoJoinReplay,
                ProjectModuleRelationSemanticFacts,
            }
            or type(self.mode) is not ProjectJoinedAggregationMode
        ):
            raise TypeError("Aggregate context requires closed semantic authority.")
        owner = _aggregate_basis_owner(self.semantic_basis)
        if self.operator.node.anchor.identity != _declaration_identity(owner):
            raise ValueError("Aggregate context owner must match exact semantics.")
        expected_keys, expected_outputs = _aggregate_basis_values(
            self.semantic_basis,
            self.mode,
        )
        if not _same_objects(self.group_keys, expected_keys) or not _same_objects(
            self.aggregate_outputs,
            expected_outputs,
        ):
            raise ValueError("Aggregate context must retain exact semantic members.")
        if self.mode is ProjectJoinedAggregationMode.GROUPED:
            if not self.group_keys or not self.aggregate_outputs:
                raise ValueError("GROUPED context requires keys and aggregate outputs.")
        elif self.mode is ProjectJoinedAggregationMode.GLOBAL:
            if self.group_keys or not self.aggregate_outputs:
                raise ValueError("GLOBAL context requires aggregate outputs only.")
        else:
            raise ValueError("Absent aggregation cannot create a group context.")

    @property
    def grouped_operator_node(self) -> ProjectIRPlanNodeOccurrence:
        return self.operator.node

    @property
    def grouped_owner(self) -> ProjectDeclarationOccurrenceIdentity:
        return self.operator.node.anchor.identity

    @property
    def grouped_keys(self) -> tuple[object, ...]:
        return self.group_keys


def _aggregate_basis_owner(
    basis: ProjectIRQueryBlockAggregateSemanticBasis,
) -> ProjectDeclarationOccurrence:
    if type(basis) is ProjectConcreteJoinedAggregation:
        return basis.input_filter.entry.owner
    if type(basis) is ProjectConcreteNoJoinReplay:
        return basis.owner
    if type(basis) is ProjectModuleRelationSemanticFacts:
        return basis.owner
    raise TypeError("Aggregate basis requires a closed exact owner.")


def _aggregate_basis_values(
    basis: ProjectIRQueryBlockAggregateSemanticBasis,
    mode: ProjectJoinedAggregationMode,
) -> tuple[tuple[object, ...], tuple[object, ...]]:
    if type(basis) is ProjectConcreteJoinedAggregation:
        return cast(tuple[object, ...], basis.group_keys), cast(
            tuple[object, ...], basis.stage_outputs
        )
    if type(basis) is ProjectConcreteNoJoinReplay:
        readiness = basis.aggregate_readiness
        if type(readiness) is not ProjectAggregateGroupedClauseReadiness:
            raise ValueError("Replay aggregate context requires exact readiness.")
        keys = tuple(
            fact
            for fact in readiness.dependency_facts
            if fact.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT
        )
        schema = basis.base_state.schema
        if schema is None:
            raise ValueError(
                "Replay aggregate context requires a concrete base schema."
            )
        outputs = tuple(schema.fields.values())
        return cast(tuple[object, ...], keys), cast(tuple[object, ...], outputs)
    if type(basis) is ProjectModuleRelationSemanticFacts:
        return cast(tuple[object, ...], basis.group_key_occurrences), cast(
            tuple[object, ...], basis.aggregate_result_facts
        )
    raise TypeError("Aggregate basis requires exact retained semantics.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockGrainOrigin:
    """One new grouped/global origin without replacing historical origins."""

    kind: ProjectGrainOriginKind
    context: ProjectIRQueryBlockAggregateEvaluationContext = field(
        repr=False,
        compare=False,
        hash=False,
    )
    factor: ProjectGroupedGrainFactorIdentity | None

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectGrainOriginKind or self.kind not in {
            ProjectGrainOriginKind.GROUPED_RESULT,
            ProjectGrainOriginKind.GLOBAL_AGGREGATE,
        }:
            raise ValueError("Query-block origin requires grouped/global kind.")
        if type(self.context) is not ProjectIRQueryBlockAggregateEvaluationContext:
            raise TypeError("Query-block origin requires an exact aggregate context.")
        grouped = self.kind is ProjectGrainOriginKind.GROUPED_RESULT
        if grouped:
            if (
                self.context.mode is not ProjectJoinedAggregationMode.GROUPED
                or type(self.factor) is not ProjectGroupedGrainFactorIdentity
                or self.factor.context is not self.context
                or self.factor.operator != self.context.operator.node.ref
                or self.factor.owner != self.context.grouped_owner
            ):
                raise ValueError("GROUPED origin requires its exact existing factor.")
        elif (
            self.context.mode is not ProjectJoinedAggregationMode.GLOBAL
            or self.factor is not None
        ):
            raise ValueError("GLOBAL origin has no grouped factor.")

    @property
    def operator(self) -> ProjectIRPlanNodeOccurrence:
        return self.context.operator.node


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockGrainOriginExtension(ProjectGrainOriginAuthority):
    """Immutable Slice-14 origin extension rooted in exact historical authority."""

    base: ProjectGrainOriginSet = field(repr=False, compare=False, hash=False)
    origins: tuple[ProjectIRQueryBlockGrainOrigin, ...]

    def __post_init__(self) -> None:
        if (
            type(self.base) is not ProjectGrainOriginSet
            or type(self.origins) is not tuple
        ):
            raise TypeError("Query-block origins require exact base and tuple roots.")
        if any(
            type(item) is not ProjectIRQueryBlockGrainOrigin for item in self.origins
        ):
            raise TypeError("Query-block origins require exact origin carriers.")
        positions = tuple(item.operator.ref.position for item in self.origins)
        if positions != tuple(sorted(positions)) or len(set(positions)) != len(
            positions
        ):
            raise ValueError("Query-block origins must retain allocation order.")


type ProjectIRQueryBlockSemanticFieldSource = (
    ProjectIROutputFieldOccurrence
    | ProjectJoinedRowFieldSemantics
    | ProjectJoinedStageOutputOccurrence
    | ProjectSelectedWindowResultBinding
    | ProjectNoJoinGroupedOutput
    | ProjectModuleWindowOutputFact
    | ProjectCompletedOutputField
    | ProjectIRRowField
    | ProjectIRStageRowField
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockRowField:
    """One plan-local positional field with exact semantic/provenance evidence."""

    field_position: int
    evidence: ProjectRowField = field(repr=False)
    semantic_source: ProjectIRQueryBlockSemanticFieldSource = field(
        repr=False,
        compare=False,
        hash=False,
    )
    effective_nullability: ProjectRowFieldNullability
    introduction_use: ProjectIRJoinInputUseOccurrence | ProjectIRUseOccurrence | None
    nulling_joins: tuple[ProjectIRPlanNodeRef, ...]
    final_identity: ProjectModuleRowFieldIdentity | None = None

    def __post_init__(self) -> None:
        if type(self.field_position) is not int or self.field_position < 0:
            raise ValueError("Query-block field position must be non-negative.")
        if (
            type(self.evidence) is not ProjectRowField
            or type(self.effective_nullability) is not ProjectRowFieldNullability
        ):
            raise TypeError("Query-block field requires exact row evidence.")
        if type(self.semantic_source) not in {
            ProjectIROutputFieldOccurrence,
            ProjectJoinedRowFieldSemantics,
            ProjectJoinedStageOutputOccurrence,
            ProjectSelectedWindowResultBinding,
            ProjectNoJoinGroupedOutput,
            ProjectModuleWindowOutputFact,
            ProjectCompletedOutputField,
            ProjectIRRowField,
            ProjectIRStageRowField,
        }:
            raise TypeError("Query-block field requires a closed semantic source.")
        if self.introduction_use is not None and type(self.introduction_use) not in {
            ProjectIRJoinInputUseOccurrence,
            ProjectIRUseOccurrence,
        }:
            raise TypeError("Query-block field introduction requires an exact use.")
        if type(self.nulling_joins) is not tuple or any(
            type(item) is not ProjectIRPlanNodeRef for item in self.nulling_joins
        ):
            raise TypeError("Query-block nulling provenance must be an exact tuple.")
        if self.nulling_joins and (
            self.effective_nullability is not ProjectRowFieldNullability.NULLABLE
        ):
            raise ValueError("Null-generated query-block fields must be nullable.")
        if (
            self.final_identity is not None
            and type(self.final_identity) is not ProjectModuleRowFieldIdentity
        ):
            raise TypeError("Final query-block field identity must be canonical.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockRowShape:
    """Occurrence-complete query-block row shape without a name-keyed schema."""

    relation: ProjectIRRelationAnchor
    producer: ProjectIRPlanNodeOccurrence
    operator: ProjectIRQueryBlockOperatorOccurrence
    fields: tuple[ProjectIRQueryBlockRowField, ...]

    def __post_init__(self) -> None:
        if type(self.relation) is not ProjectIRRelationAnchor or (
            type(self.producer) is not ProjectIRPlanNodeOccurrence
            or self.producer.anchor != self.relation
            or self.operator.node is not self.producer
        ):
            raise ValueError("Query-block row shape requires its exact operator node.")
        if (
            type(self.fields) is not tuple
            or any(
                type(item) is not ProjectIRQueryBlockRowField for item in self.fields
            )
            or tuple(item.field_position for item in self.fields)
            != tuple(range(len(self.fields)))
        ):
            raise ValueError(
                "Query-block fields must retain complete ordered positions."
            )
        final = self.operator.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION
        if any((item.final_identity is not None) is not final for item in self.fields):
            raise ValueError("Only FINAL_PROJECTION fields have final identity.")
        scope = self.producer.ref.scope
        if any(
            (
                field.introduction_use is not None
                and field.introduction_use.ref.scope is not scope
            )
            or any(ref.scope is not scope for ref in field.nulling_joins)
            for field in self.fields
        ):
            raise ValueError(
                "Query-block field provenance requires one snapshot scope."
            )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockRowOutput(ProjectIRRelationalRowOutputExtension):
    """One query-block BAG row output admitted to the existing property algebra."""

    occurrence: ProjectIROutputValueOccurrence
    row_shape: ProjectIRQueryBlockRowShape

    def __post_init__(self) -> None:
        if (
            type(self.occurrence) is not ProjectIROutputValueOccurrence
            or type(self.row_shape) is not ProjectIRQueryBlockRowShape
        ):
            raise TypeError("Query-block output requires exact occurrence and shape.")
        if (
            self.occurrence.producer is not self.row_shape.producer
            or type(self.occurrence.anchor) is not ProjectIRRelationAnchor
            or self.occurrence.anchor != self.row_shape.relation
        ):
            raise ValueError("Query-block output must retain its exact producer row.")


type ProjectIRActiveRowOutput = (
    ProjectIRRelationRowOutput | ProjectIRQueryBlockRowOutput
)
type ProjectIRQueryBlockInputRowOutput = (
    ProjectIRRelationRowOutput | ProjectIRJoinRowOutput | ProjectIRQueryBlockRowOutput
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockScalarOutput:
    """Selected-window or final-field scalar output in an existing coordinate domain."""

    occurrence: ProjectIROutputValueOccurrence
    row_output: ProjectIRQueryBlockRowOutput
    field_position: int
    semantic_source: (
        ProjectSelectedWindowResultBinding
        | ProjectModuleWindowOutputFact
        | ProjectCompletedOutputField
    ) = field(repr=False, compare=False, hash=False)
    final_identity: ProjectModuleRowFieldIdentity | None = None

    def __post_init__(self) -> None:
        if type(self.occurrence) is not ProjectIROutputValueOccurrence or (
            type(self.row_output) is not ProjectIRQueryBlockRowOutput
            or self.occurrence.producer is not self.row_output.occurrence.producer
            or type(self.field_position) is not int
            or not 0 <= self.field_position < len(self.row_output.row_shape.fields)
        ):
            raise ValueError("Query-block scalar requires an exact owned row field.")
        anchor = self.occurrence.anchor
        if self.final_identity is None:
            if type(self.semantic_source) not in {
                ProjectSelectedWindowResultBinding,
                ProjectModuleWindowOutputFact,
            } or (
                type(anchor) is not ProjectIRStageFieldAnchor
                or anchor.producer is not self.occurrence.producer
                or anchor.field_position != self.field_position
            ):
                raise ValueError("Window scalar requires one plan-local field anchor.")
        elif (
            type(self.semantic_source) is not ProjectCompletedOutputField
            or self.semantic_source.identity is not self.final_identity
            or type(anchor) is not ProjectIRFieldAnchor
            or anchor.identity is not self.final_identity
        ):
            raise ValueError("Final scalar must reuse the exact Slice-12 identity.")


type ProjectIRQueryBlockEffectOutput = (
    ProjectIRQueryBlockRowOutput | ProjectIRQueryBlockScalarOutput
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRQueryBlockEffectEvidence:
    """Conservative effect posture for one new query-block output."""

    output: ProjectIRQueryBlockEffectOutput
    determinism: ProjectIRDeterminismEvidence = field(
        init=False,
        default=ProjectIRDeterminismEvidence.UNKNOWN,
    )
    error_behavior: ProjectIRErrorBehaviorEvidence = field(
        init=False,
        default=ProjectIRErrorBehaviorEvidence.UNKNOWN,
    )
    side_effects: ProjectIRSideEffectEvidence = field(
        init=False,
        default=ProjectIRSideEffectEvidence.UNKNOWN,
    )
    evaluation_count: ProjectIREvaluationCountEvidence = field(
        init=False,
        default=ProjectIREvaluationCountEvidence.UNKNOWN,
    )

    def __post_init__(self) -> None:
        if type(self.output) not in {
            ProjectIRQueryBlockRowOutput,
            ProjectIRQueryBlockScalarOutput,
        }:
            raise TypeError("Query-block effects require an exact new output.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockWindowPolicy:
    """Existing semantic window policy attached to one selected scalar output."""

    output: ProjectIRQueryBlockScalarOutput
    evidence: ProjectIRQueryBlockWindowSelectedEvidence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    policy: object = field(init=False)

    def __post_init__(self) -> None:
        if type(self.output) is not ProjectIRQueryBlockScalarOutput or (
            self.output.final_identity is not None
        ):
            raise TypeError("Window policy requires one stage-local scalar output.")
        if type(self.evidence) is ProjectConcreteWindowComputation:
            source = self.output.semantic_source
            valid = (
                type(source) is ProjectSelectedWindowResultBinding
                and source.computation is self.evidence
            )
            policy = self.evidence.analysis.validated_specification.function_policy
        elif type(self.evidence) is ProjectModuleWindowOutputFact:
            fact = self.evidence.project_fact
            valid = self.output.semantic_source is self.evidence and fact is not None
            policy = (
                None
                if fact is None
                else fact.analysis.validated_specification.function_policy
            )
        else:
            raise TypeError(
                "Window policy requires exact selected computation evidence."
            )
        if not valid or policy is None:
            raise ValueError("Window policy must retain exact semantic authority.")
        object.__setattr__(self, "policy", policy)


type ProjectIRQueryBlockRelationOrdering = (
    ProjectIRProvidedRelationOrdering | ProjectRelationOrdering
)
type ProjectIRQueryBlockCardinality = (
    ProjectIRProvidedCardinalityUpperBound | ProjectRelationLimit
)
type ProjectIRQueryBlockOutputEffect = (
    ProjectIREffectEvidence | ProjectIRQueryBlockEffectEvidence
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockResultProperties:
    """All current row/property/effect authority for one active row output."""

    relational: ProjectIROutputRelationalProperties
    multiplicity: ProjectJoinedRowMultiplicity
    ordering: ProjectIRQueryBlockRelationOrdering | None
    cardinality: ProjectIRQueryBlockCardinality | None
    effect: ProjectIRQueryBlockOutputEffect

    def __post_init__(self) -> None:
        if type(self.relational) is not ProjectIROutputRelationalProperties or (
            self.multiplicity is not ProjectJoinedRowMultiplicity.BAG
        ):
            raise ValueError("Query-block result requires exact BAG relational facts.")
        output = self.relational.output
        if self.ordering is not None and type(self.ordering) not in {
            ProjectIRProvidedRelationOrdering,
            ProjectRelationOrdering,
        }:
            raise TypeError("Query-block ordering requires exact current authority.")
        if type(self.ordering) is ProjectIRProvidedRelationOrdering and (
            self.ordering.output is not output
        ):
            raise ValueError("Historical ordering must belong to the exact output.")
        if self.cardinality is not None and type(self.cardinality) not in {
            ProjectIRProvidedCardinalityUpperBound,
            ProjectRelationLimit,
        }:
            raise TypeError("Query-block cardinality requires exact current authority.")
        if type(self.cardinality) is ProjectIRProvidedCardinalityUpperBound and (
            self.cardinality.output is not output
        ):
            raise ValueError("Historical cardinality must belong to the exact output.")
        if type(self.effect) is ProjectIREffectEvidence:
            if self.effect.output is not output:
                raise ValueError("Historical effect must belong to the exact output.")
        elif type(self.effect) is ProjectIRQueryBlockEffectEvidence:
            if self.effect.output is not output:
                raise ValueError("Query-block effect must belong to the exact output.")
        else:
            raise TypeError("Query-block result requires exact effect authority.")

    @property
    def output(self) -> ProjectIRRelationalRowOutput:
        return self.relational.output

    @property
    def row_count_upper_bound(self) -> int | None:
        if type(self.cardinality) is ProjectIRProvidedCardinalityUpperBound:
            return self.cardinality.upper_bound
        if type(self.cardinality) is ProjectRelationLimit:
            return self.cardinality.row_count_upper_bound
        return None


class ProjectIRQueryBlockRowCompatibilityStatus(StrEnum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockRowCompatibility:
    """Nominal identity plus typed ordered-shape compatibility for one active input."""

    output: ProjectIRActiveRowOutput = field(repr=False, compare=False, hash=False)
    target: ProjectDeclarationOccurrenceIdentity
    expected_identities: tuple[ProjectModuleRowFieldIdentity, ...]
    required_fields: tuple[ProjectRowField, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    status: ProjectIRQueryBlockRowCompatibilityStatus = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.output)
            not in {
                ProjectIRRelationRowOutput,
                ProjectIRQueryBlockRowOutput,
            }
            or type(self.target) is not ProjectDeclarationOccurrenceIdentity
        ):
            raise TypeError("Row compatibility requires an exact active output.")
        if (
            type(self.expected_identities) is not tuple
            or any(
                type(item) is not ProjectModuleRowFieldIdentity
                for item in self.expected_identities
            )
            or type(self.required_fields) is not tuple
            or any(type(item) is not ProjectRowField for item in self.required_fields)
        ):
            raise TypeError("Row compatibility requires exact ordered field authority.")
        actual_identities = _active_output_identities(self.output)
        actual_fields = tuple(item.evidence for item in self.output.row_shape.fields)
        compatible = (
            self.output.row_shape.relation.identity == self.target
            and actual_identities == self.expected_identities
            and len(actual_fields) == len(self.required_fields)
            and all(
                actual.resolved_type == required.resolved_type
                and actual.nullability is required.nullability
                for actual, required in zip(
                    actual_fields,
                    self.required_fields,
                    strict=True,
                )
            )
        )
        object.__setattr__(
            self,
            "status",
            (
                ProjectIRQueryBlockRowCompatibilityStatus.SATISFIED
                if compatible
                else ProjectIRQueryBlockRowCompatibilityStatus.NOT_SATISFIED
            ),
        )

    @property
    def satisfied(self) -> bool:
        return self.status is ProjectIRQueryBlockRowCompatibilityStatus.SATISFIED


def _active_output_identities(
    output: ProjectIRActiveRowOutput,
) -> tuple[ProjectModuleRowFieldIdentity, ...]:
    if type(output) is ProjectIRRelationRowOutput:
        identities = tuple(
            field.anchor.identity
            for field in output.row_shape.fields
            if type(field) is ProjectIRRowField
        )
    elif type(output) is ProjectIRQueryBlockRowOutput:
        identities = tuple(
            field.final_identity
            for field in output.row_shape.fields
            if field.final_identity is not None
        )
    else:
        raise TypeError("Active output requires one closed row-output family.")
    if len(identities) != len(output.row_shape.fields):
        raise ValueError("Active final output requires canonical field identities.")
    return cast(tuple[ProjectModuleRowFieldIdentity, ...], identities)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockRelationInputEdge:
    """Exact active producer use at a rebuilt/replayed RELATION_INPUT."""

    dependency: ProjectCompletionDependency = field(
        repr=False,
        compare=False,
        hash=False,
    )
    authority: ProjectIRResolvedRelationAnchor = field(
        repr=False,
        compare=False,
        hash=False,
    )
    producer: ProjectIRQueryBlockResultProperties = field(
        repr=False,
        compare=False,
        hash=False,
    )
    consumer: ProjectIRPlanNodeOccurrence
    input_slot: ProjectIRInputSlotOccurrence
    use: ProjectIRUseOccurrence
    compatibility: ProjectIRQueryBlockRowCompatibility

    def __post_init__(self) -> None:
        output = self.producer.output
        if type(self.dependency) is not ProjectCompletionDependency or (
            type(self.authority) is not ProjectIRResolvedRelationAnchor
            or self.authority.resolution is not self.dependency.evidence
            or self.authority.reference.owner != self.consumer.anchor.identity
            or self.authority.target != output.row_shape.relation.identity
        ):
            raise ValueError("Relation-input edge requires exact dependency authority.")
        if (
            type(self.input_slot) is not ProjectIRInputSlotOccurrence
            or self.input_slot.consumer is not self.consumer
            or self.input_slot.input_ordinal != 0
            or type(self.use) is not ProjectIRUseOccurrence
            or self.use.output is not output.occurrence
            or self.use.slot is not self.input_slot
            or self.use.anchor is not self.authority
            or self.use.role is not ProjectModuleFactOccurrenceRole.RELATION_INPUT
            or self.use.source_order != 0
        ):
            raise ValueError("Relation-input edge requires exact structural endpoints.")
        if (
            type(self.compatibility) is not ProjectIRQueryBlockRowCompatibility
            or self.compatibility.output is not output
            or not self.compatibility.satisfied
        ):
            raise ValueError("Relation-input edge requires proven row compatibility.")


class ProjectIRQueryBlockTerminalReason(StrEnum):
    """Closed reasons for an effective semantic output without active Slice-14 IR."""

    SEMANTIC_OUTPUT_NON_CONCRETE = "semantic_output_non_concrete"
    ACTIVE_UPSTREAM_IR_NON_CONCRETE = "active_upstream_ir_non_concrete"
    ACTIVE_UPSTREAM_ROW_INCOMPATIBLE = "active_upstream_row_incompatible"
    EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED = "effective_join_input_rebind_unsupported"


type ProjectIRQueryBlockSemanticEntry = ProjectEffectiveOutputCompletionEntry


def _active_root_operator_kind(
    entry: ProjectCompletedEffectiveOutput,
) -> ProjectIRLogicalOperatorKind:
    if entry.limit is not None:
        return ProjectIRLogicalOperatorKind.LIMIT
    if entry.ordering is not None:
        return ProjectIRLogicalOperatorKind.RELATION_ORDERING
    return ProjectIRLogicalOperatorKind.FINAL_PROJECTION


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRReusedEffectiveOutput:
    """Zero-allocation exact historical Project IR reuse."""

    semantic_entry: ProjectExistingEffectiveOutput = field(
        repr=False,
        compare=False,
        hash=False,
    )
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    active_output: ProjectIRRelationRowOutput
    active_properties: ProjectIRQueryBlockResultProperties

    def __post_init__(self) -> None:
        if type(self.semantic_entry) is not ProjectExistingEffectiveOutput or (
            self.ending_allocation is not self.starting_allocation
            or self.active_output is not self.semantic_entry.output
            or self.active_output
            is not self.semantic_entry.fragment.root_relation_output
            or self.active_properties.relational is not self.semantic_entry.properties
            or self.active_properties.output is not self.active_output
        ):
            raise ValueError(
                "Historical reuse requires exact roots and zero allocation."
            )

    @property
    def owner(self) -> ProjectDeclarationOccurrence:
        return self.semantic_entry.owner

    @property
    def output(self) -> ProjectIRRelationRowOutput:
        return self.active_output

    @property
    def result_properties(self) -> ProjectIRQueryBlockResultProperties:
        return self.active_properties


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRReboundExistingOutput:
    """Historical no-JOIN fragment reconstructed against one active upstream."""

    semantic_entry: ProjectExistingEffectiveOutput = field(
        repr=False,
        compare=False,
        hash=False,
    )
    rebuilt_fragment: ProjectIRConcreteSingleRelationFragment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    relation_input: ProjectIRQueryBlockRelationInputEdge
    aggregate_contexts: tuple[ProjectIRQueryBlockAggregateEvaluationContext, ...]
    row_properties: tuple[ProjectIRQueryBlockResultProperties, ...]
    active_output: ProjectIRRelationRowOutput
    active_properties: ProjectIRQueryBlockResultProperties

    def __post_init__(self) -> None:
        fragment = self.rebuilt_fragment
        if type(self.semantic_entry) is not ProjectExistingEffectiveOutput or (
            type(fragment) is not ProjectIRConcreteSingleRelationFragment
            or fragment is self.semantic_entry.fragment
            or fragment.semantic_facts
            is not self.semantic_entry.fragment.semantic_facts
            or fragment.starting_allocation is not self.starting_allocation
            or self.relation_input.consumer is not _relation_input_node(fragment)
        ):
            raise ValueError("Rebound output requires exact historical semantic roots.")
        if (
            self.ending_allocation.scope is not self.starting_allocation.scope
            or self.ending_allocation.next_plan_node_position
            != fragment.ending_allocation.next_plan_node_position
            or self.ending_allocation.next_output_value_position
            != fragment.ending_allocation.next_output_value_position
            or self.ending_allocation.next_input_slot_position
            != fragment.ending_allocation.next_input_slot_position + 1
            or self.ending_allocation.next_use_position
            != fragment.ending_allocation.next_use_position + 1
            or self.relation_input.input_slot.ref.position
            != fragment.ending_allocation.next_input_slot_position
            or self.relation_input.use.ref.position
            != fragment.ending_allocation.next_use_position
        ):
            raise ValueError("Rebound edge must continue the fragment allocation.")
        row_outputs = _fragment_row_outputs(fragment)
        if len(self.row_properties) != len(row_outputs) or any(
            item.output is not output
            for item, output in zip(self.row_properties, row_outputs, strict=True)
        ):
            raise ValueError("Rebound properties must cover every operator row once.")
        if (
            self.active_output is not fragment.root_relation_output
            or self.active_output.occurrence.producer is not fragment.root
            or sum(output is self.active_output for output in row_outputs) != 1
        ):
            raise ValueError("Rebound output requires an explicit active row root.")
        if (
            self.active_properties.output is not self.active_output
            or sum(
                properties is self.active_properties
                for properties in self.row_properties
            )
            != 1
        ):
            raise ValueError(
                "Rebound output requires an explicit active property root."
            )
        group_operators = tuple(
            operator
            for operator in fragment.logical_stage.operators
            if operator.kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
        )
        if len(self.aggregate_contexts) != len(group_operators) or any(
            context.operator is not operator
            for context, operator in zip(
                self.aggregate_contexts,
                group_operators,
                strict=True,
            )
        ):
            raise ValueError("Rebound aggregate contexts must retain exact operators.")

    @property
    def owner(self) -> ProjectDeclarationOccurrence:
        return self.semantic_entry.owner

    @property
    def output(self) -> ProjectIRRelationRowOutput:
        return self.active_output

    @property
    def result_properties(self) -> ProjectIRQueryBlockResultProperties:
        return self.active_properties


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRCompletedQueryBlockOutput:
    """One freshly allocated completed joined or replay query-block fragment."""

    semantic_entry: ProjectCompletedEffectiveOutput = field(
        repr=False,
        compare=False,
        hash=False,
    )
    source_properties: ProjectIROutputRelationalProperties = field(
        repr=False,
        compare=False,
        hash=False,
    )
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    operators: tuple[ProjectIRQueryBlockOperatorOccurrence, ...]
    row_outputs: tuple[ProjectIRQueryBlockRowOutput, ...]
    scalar_outputs: tuple[ProjectIRQueryBlockScalarOutput, ...]
    input_slots: tuple[ProjectIRInputSlotOccurrence, ...]
    uses: tuple[ProjectIRUseOccurrence | ProjectIROperatorFlowUseOccurrence, ...]
    aggregate_contexts: tuple[ProjectIRQueryBlockAggregateEvaluationContext, ...]
    window_policies: tuple[ProjectIRQueryBlockWindowPolicy, ...]
    effects: tuple[ProjectIRQueryBlockEffectEvidence, ...]
    row_properties: tuple[ProjectIRQueryBlockResultProperties, ...]
    active_output: ProjectIRQueryBlockRowOutput
    active_properties: ProjectIRQueryBlockResultProperties
    relation_input: ProjectIRQueryBlockRelationInputEdge | None = None

    def __post_init__(self) -> None:
        if type(self.semantic_entry) is not ProjectCompletedEffectiveOutput or (
            type(self.source_properties) is not ProjectIROutputRelationalProperties
            or not self.operators
            or len(self.operators) != len(self.row_outputs)
            or any(
                output.occurrence.producer is not operator.node
                for operator, output in zip(
                    self.operators,
                    self.row_outputs,
                    strict=True,
                )
            )
        ):
            raise ValueError(
                "Completed query-block output requires every operator row."
            )
        if len(self.input_slots) != len(self.operators) or len(self.uses) != len(
            self.operators
        ):
            raise ValueError("Every completed unary operator requires one direct use.")
        occurrences = (
            *(output.occurrence for output in self.row_outputs),
            *(output.occurrence for output in self.scalar_outputs),
        )
        positions = tuple(sorted(item.ref.position for item in occurrences))
        if len(set(positions)) != len(positions) or positions != tuple(
            range(
                self.starting_allocation.next_output_value_position,
                self.ending_allocation.next_output_value_position,
            )
        ):
            raise ValueError("Completed outputs must continue dense allocation.")
        if any(
            effect.output not in (*self.row_outputs, *self.scalar_outputs)
            for effect in self.effects
        ) or len(self.effects) != len(occurrences):
            raise ValueError("Every completed output requires one unknown effect.")
        if len(self.row_properties) != len(self.row_outputs) or any(
            properties.output is not output
            for properties, output in zip(
                self.row_properties,
                self.row_outputs,
                strict=True,
            )
        ):
            raise ValueError("Completed properties must cover every row output.")
        active_kind = _active_root_operator_kind(self.semantic_entry)
        active_operators = tuple(
            operator for operator in self.operators if operator.kind is active_kind
        )
        if (
            len(active_operators) != 1
            or sum(output is self.active_output for output in self.row_outputs) != 1
            or self.active_output.occurrence.producer is not active_operators[0].node
            or self.active_output.row_shape.relation.identity
            != _declaration_identity(self.semantic_entry.owner)
        ):
            raise ValueError("Completed output requires an explicit active row root.")
        if (
            self.active_properties.output is not self.active_output
            or sum(
                properties is self.active_properties
                for properties in self.row_properties
            )
            != 1
        ):
            raise ValueError(
                "Completed output requires an explicit active property root."
            )
        root = self.semantic_entry.root
        if type(root) is ProjectConcreteNoJoinReplay:
            if (
                self.operators[0].kind
                is not ProjectIRLogicalOperatorKind.RELATION_INPUT
                or self.relation_input is None
                or self.relation_input.consumer is not self.operators[0].node
                or self.relation_input.producer.relational is not self.source_properties
            ):
                raise ValueError(
                    "Replay output requires one exact RELATION_INPUT edge."
                )
        elif (
            type(root) is not ProjectConcreteJoinedQualify
            or self.operators[0].kind is ProjectIRLogicalOperatorKind.RELATION_INPUT
            or self.relation_input is not None
        ):
            raise ValueError("Joined tail cannot manufacture RELATION_INPUT.")
        if self.ending_allocation.scope is not self.starting_allocation.scope:
            raise ValueError("Completed query-block allocation requires one scope.")

    @property
    def owner(self) -> ProjectDeclarationOccurrence:
        return self.semantic_entry.owner

    @property
    def output(self) -> ProjectIRQueryBlockRowOutput:
        return self.active_output

    @property
    def result_properties(self) -> ProjectIRQueryBlockResultProperties:
        return self.active_properties

    @property
    def nodes(self) -> tuple[ProjectIRPlanNodeOccurrence, ...]:
        return tuple(item.node for item in self.operators)

    @property
    def output_occurrences(self) -> tuple[ProjectIROutputValueOccurrence, ...]:
        return tuple(
            sorted(
                (
                    *(item.occurrence for item in self.row_outputs),
                    *(item.occurrence for item in self.scalar_outputs),
                ),
                key=lambda item: item.ref.position,
            )
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockTerminal:
    """One typed all-or-none IR terminal with zero owner-local allocation."""

    semantic_entry: ProjectIRQueryBlockSemanticEntry = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectIRQueryBlockTerminalReason
    blocker: object = field(repr=False, compare=False, hash=False)
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    output: None = field(init=False, default=None)
    result_properties: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if (
            type(self.semantic_entry)
            not in {
                ProjectEffectiveOutputTerminal,
                ProjectEffectiveOutputCompletionTerminal,
                ProjectExistingEffectiveOutput,
                ProjectCompletedEffectiveOutput,
            }
            or type(self.reason) is not ProjectIRQueryBlockTerminalReason
        ):
            raise TypeError("IR terminal requires exact semantic entry and reason.")
        if self.ending_allocation is not self.starting_allocation:
            raise ValueError("IR terminal must allocate zero Slice-14 refs.")
        if (
            self.reason
            is ProjectIRQueryBlockTerminalReason.SEMANTIC_OUTPUT_NON_CONCRETE
        ):
            valid = (
                type(self.semantic_entry)
                in {
                    ProjectEffectiveOutputTerminal,
                    ProjectEffectiveOutputCompletionTerminal,
                }
                and self.blocker is self.semantic_entry
            )
        elif self.reason is (
            ProjectIRQueryBlockTerminalReason.ACTIVE_UPSTREAM_IR_NON_CONCRETE
        ):
            valid = type(self.blocker) is ProjectIRQueryBlockTerminal
        elif self.reason is (
            ProjectIRQueryBlockTerminalReason.ACTIVE_UPSTREAM_ROW_INCOMPATIBLE
        ):
            valid = (
                type(self.blocker) is ProjectIRQueryBlockRowCompatibility
                and not self.blocker.satisfied
            )
        else:
            valid = (
                type(self.semantic_entry) is ProjectCompletedEffectiveOutput
                and type(self.blocker) is tuple
                and bool(self.blocker)
                and all(
                    type(item) is ProjectIRJoinInputUseOccurrence
                    for item in self.blocker
                )
            )
        if not valid:
            raise ValueError("IR terminal reason must retain exact causal evidence.")

    @property
    def owner(self) -> ProjectDeclarationOccurrence:
        return self.semantic_entry.owner


type ProjectIRQueryBlockEntry = (
    ProjectIRReusedEffectiveOutput
    | ProjectIRReboundExistingOutput
    | ProjectIRCompletedQueryBlockOutput
    | ProjectIRQueryBlockTerminal
)
type ProjectIRConcreteQueryBlockEntry = (
    ProjectIRReusedEffectiveOutput
    | ProjectIRReboundExistingOutput
    | ProjectIRCompletedQueryBlockOutput
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockStructuralExtension:
    """Dense additive occurrences after the exact Phase-62 ending allocation."""

    base_plan: ProjectIRProjectPlan = field(repr=False, compare=False, hash=False)
    join_stage: ProjectIRJoinRegionStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    nodes: tuple[ProjectIRPlanNodeOccurrence, ...]
    outputs: tuple[ProjectIROutputValueOccurrence, ...]
    input_slots: tuple[ProjectIRInputSlotOccurrence, ...]
    uses: tuple[ProjectIRUseOccurrence | ProjectIROperatorFlowUseOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.base_plan) is not ProjectIRProjectPlan or (
            type(self.join_stage) is not ProjectIRJoinRegionStage
            or self.join_stage.base_plan is not self.base_plan
            or self.starting_allocation is not self.join_stage.ending_allocation
        ):
            raise ValueError("Query-block structure requires exact Phase-61/62 roots.")
        if self.ending_allocation.scope is not self.starting_allocation.scope:
            raise ValueError("Query-block structure requires one snapshot scope.")
        for values, item_type, label in (
            (self.nodes, ProjectIRPlanNodeOccurrence, "nodes"),
            (self.outputs, ProjectIROutputValueOccurrence, "outputs"),
            (self.input_slots, ProjectIRInputSlotOccurrence, "input slots"),
        ):
            if type(values) is not tuple or any(
                type(item) is not item_type for item in values
            ):
                raise TypeError(f"Query-block structural {label} must be exact.")
        if type(self.uses) is not tuple or any(
            type(item)
            not in {ProjectIRUseOccurrence, ProjectIROperatorFlowUseOccurrence}
            for item in self.uses
        ):
            raise TypeError("Query-block structural uses must be exact.")
        for values, start, end, label in (
            (
                self.nodes,
                self.starting_allocation.next_plan_node_position,
                self.ending_allocation.next_plan_node_position,
                "node",
            ),
            (
                self.outputs,
                self.starting_allocation.next_output_value_position,
                self.ending_allocation.next_output_value_position,
                "output",
            ),
            (
                self.input_slots,
                self.starting_allocation.next_input_slot_position,
                self.ending_allocation.next_input_slot_position,
                "input-slot",
            ),
            (
                self.uses,
                self.starting_allocation.next_use_position,
                self.ending_allocation.next_use_position,
                "use",
            ),
        ):
            if tuple(item.ref.position for item in values) != tuple(range(start, end)):
                raise ValueError(f"Query-block {label} coordinates must be dense.")
        available_nodes = {
            *(self.base_plan.structural_stage.nodes),
            *(self.join_stage.structural.nodes),
            *self.nodes,
        }
        available_outputs = {
            *(self.base_plan.structural_stage.outputs),
            *(self.join_stage.structural.outputs),
            *self.outputs,
        }
        if (
            any(output.producer not in available_nodes for output in self.outputs)
            or any(slot.consumer not in self.nodes for slot in self.input_slots)
            or any(
                use.output not in available_outputs or use.slot not in self.input_slots
                for use in self.uses
            )
        ):
            raise ValueError("Query-block structure requires exact retained endpoints.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectIRQueryBlockSnapshot:
    """Complete active-output overlay over exact Phase-61 and Phase-62 snapshots."""

    completed: ProjectConcreteCompletedSemanticResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    base_plan: ProjectIRProjectPlan = field(repr=False, compare=False, hash=False)
    join_stage: ProjectIRJoinRegionStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    owners: tuple[ProjectDeclarationOccurrence, ...]
    dependencies: tuple[ProjectCompletionDependency, ...]
    schedule: tuple[ProjectDeclarationOccurrence, ...]
    entries: tuple[ProjectIRQueryBlockEntry, ...]
    grain_origins: ProjectIRQueryBlockGrainOriginExtension
    structural: ProjectIRQueryBlockStructuralExtension

    def __post_init__(self) -> None:
        if type(self.completed) is not ProjectConcreteCompletedSemanticResult or (
            self.completed.verification.root.evaluation.project_plan
            is not self.base_plan
            or self.completed.verification.root.join_regions is not self.join_stage
            or self.completed.effective_outputs.owners is not self.owners
            or self.completed.effective_outputs.dependencies is not self.dependencies
            or self.completed.effective_outputs.schedule is not self.schedule
        ):
            raise ValueError("Query-block snapshot requires exact Slice-13 roots.")
        if len(self.entries) != len(self.owners) or any(
            type(entry)
            not in {
                ProjectIRReusedEffectiveOutput,
                ProjectIRReboundExistingOutput,
                ProjectIRCompletedQueryBlockOutput,
                ProjectIRQueryBlockTerminal,
            }
            or entry.owner is not owner
            or entry.semantic_entry is not semantic_entry
            for entry, owner, semantic_entry in zip(
                self.entries,
                self.owners,
                self.completed.effective_outputs.entries,
                strict=True,
            )
        ):
            raise ValueError(
                "Query-block ledger requires one canonical entry per owner."
            )
        if (
            self.grain_origins.base
            is not self.completed.verification.root.base_relational.origins
        ):
            raise ValueError("Query-block grain roots must retain Phase-61 authority.")
        if self.structural.base_plan is not self.base_plan or (
            self.structural.join_stage is not self.join_stage
        ):
            raise ValueError("Query-block snapshot must retain its structural roots.")
        new_relational: list[ProjectIROutputRelationalProperties] = []
        for entry in self.entries:
            if type(entry) is ProjectIRReboundExistingOutput:
                new_relational.extend(
                    properties.relational for properties in entry.row_properties
                )
            elif type(entry) is ProjectIRCompletedQueryBlockOutput:
                new_relational.extend(
                    properties.relational for properties in entry.row_properties
                )
        if any(
            item.grain.origin_set is not self.grain_origins for item in new_relational
        ):
            raise ValueError("Every new grain product requires one extension root.")

    @property
    def starting_allocation(self) -> ProjectIRAllocationState:
        return self.structural.starting_allocation

    @property
    def ending_allocation(self) -> ProjectIRAllocationState:
        return self.structural.ending_allocation

    def find_owner(
        self,
        owner: ProjectDeclarationOccurrence,
    ) -> tuple[ProjectIRQueryBlockEntry, ...]:
        if type(owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Query-block lookup requires an exact owner occurrence.")
        return tuple(entry for entry in self.entries if entry.owner is owner)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class _PendingReuse:
    semantic_entry: ProjectExistingEffectiveOutput
    allocation: ProjectIRAllocationState
    active_output: ProjectIRRelationRowOutput

    def __post_init__(self) -> None:
        if self.active_output is not self.semantic_entry.output:
            raise ValueError("Pending reuse requires its explicit historical root.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class _PendingRebound:
    semantic_entry: ProjectExistingEffectiveOutput
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    fragment: ProjectIRConcreteSingleRelationFragment
    dependency: ProjectCompletionDependency
    upstream_owner: ProjectDeclarationOccurrence
    authority: ProjectIRResolvedRelationAnchor
    slot: ProjectIRInputSlotOccurrence
    use: ProjectIRUseOccurrence
    compatibility: ProjectIRQueryBlockRowCompatibility
    aggregate_contexts: tuple[ProjectIRQueryBlockAggregateEvaluationContext, ...]
    active_output: ProjectIRRelationRowOutput

    def __post_init__(self) -> None:
        if self.active_output is not self.fragment.root_relation_output:
            raise ValueError("Pending rebound requires its explicit fragment root.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class _PendingCompleted:
    semantic_entry: ProjectCompletedEffectiveOutput
    source_owner: ProjectDeclarationOccurrence | None
    source_relational: ProjectIROutputRelationalProperties | None
    starting_allocation: ProjectIRAllocationState
    ending_allocation: ProjectIRAllocationState
    operators: tuple[ProjectIRQueryBlockOperatorOccurrence, ...]
    row_outputs: tuple[ProjectIRQueryBlockRowOutput, ...]
    scalar_outputs: tuple[ProjectIRQueryBlockScalarOutput, ...]
    slots: tuple[ProjectIRInputSlotOccurrence, ...]
    uses: tuple[ProjectIRUseOccurrence | ProjectIROperatorFlowUseOccurrence, ...]
    aggregate_contexts: tuple[ProjectIRQueryBlockAggregateEvaluationContext, ...]
    window_policies: tuple[ProjectIRQueryBlockWindowPolicy, ...]
    effects: tuple[ProjectIRQueryBlockEffectEvidence, ...]
    dependency: ProjectCompletionDependency | None
    authority: ProjectIRResolvedRelationAnchor | None
    compatibility: ProjectIRQueryBlockRowCompatibility | None
    active_output: ProjectIRQueryBlockRowOutput


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class _PendingTerminal:
    semantic_entry: ProjectIRQueryBlockSemanticEntry
    reason: ProjectIRQueryBlockTerminalReason
    blocker: object
    allocation: ProjectIRAllocationState

    @property
    def output(self) -> None:
        return None


type _PendingEntry = (
    _PendingReuse | _PendingRebound | _PendingCompleted | _PendingTerminal
)


def _relation_input_node(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> ProjectIRPlanNodeOccurrence:
    matches = tuple(
        operator.node
        for operator in fragment.logical_stage.operators
        if operator.kind is ProjectIRLogicalOperatorKind.RELATION_INPUT
    )
    if len(matches) != 1:
        raise ValueError("Rebound fragment requires one RELATION_INPUT node.")
    return matches[0]


def _fragment_row_outputs(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> tuple[ProjectIRRelationRowOutput, ...]:
    values: list[ProjectIRRelationRowOutput] = []
    for operator in fragment.logical_stage.operators:
        matches = tuple(
            output
            for output in fragment.property_stage.outputs
            if type(output) is ProjectIRRelationRowOutput
            and output.occurrence.producer is operator.node
        )
        if len(matches) != 1:
            raise ValueError("Historical operator requires one exact row output.")
        values.append(matches[0])
    return tuple(values)


def _semantic_entry_identities(
    entry: ProjectExistingEffectiveOutput | ProjectCompletedEffectiveOutput,
) -> tuple[ProjectModuleRowFieldIdentity, ...]:
    if type(entry) is ProjectCompletedEffectiveOutput:
        return tuple(item.identity for item in entry.fields)
    if type(entry) is not ProjectExistingEffectiveOutput:
        raise TypeError("Semantic output identity requires one concrete entry.")
    shape = entry.output.row_shape
    identities = tuple(
        item.anchor.identity for item in shape.fields if type(item) is ProjectIRRowField
    )
    if len(identities) != len(shape.fields):
        raise ValueError("Historical final output requires canonical field anchors.")
    return identities


def _historical_cross_edge(
    plan: ProjectIRProjectPlan,
    entry: ProjectExistingEffectiveOutput,
) -> ProjectIRCrossRelationEdge:
    matches = tuple(
        edge for edge in plan.cross_relation_edges if edge.consumer is entry.fragment
    )
    if len(matches) != 1:
        raise ValueError("Historical derived output requires one exact cross edge.")
    return matches[0]


def _resolved_relation_anchor(
    *,
    dependency: ProjectCompletionDependency,
    plan: ProjectIRProjectPlan,
) -> ProjectIRResolvedRelationAnchor:
    resolution = dependency.evidence
    if (
        dependency.dependency_ordinal != 0
        or type(resolution) is not ProjectResolvedModuleRelationReference
    ):
        raise ValueError("RELATION_INPUT requires one exact resolution dependency.")
    reference = ProjectModuleReferenceOccurrenceIdentity(
        owner=_declaration_identity(dependency.consumer),
        role=ProjectModuleReferenceRole.RELATION_FROM,
        member_position=0,
    )
    target = _declaration_identity(dependency.target)
    dependencies = plan.attribution.find_reference_dependencies(reference)
    matches = tuple(
        item
        for item in dependencies
        if item.kind is ProjectModuleDependencyKind.RELATION_REFERENCE
        and item.target_declaration == target
    )
    if len(dependencies) != 1 or len(matches) != 1:
        raise ValueError("RELATION_INPUT requires exact attribution provenance.")
    return ProjectIRResolvedRelationAnchor(
        resolution=resolution,
        dependency=matches[0],
    )


def _row_compatibility(
    *,
    output: ProjectIRActiveRowOutput,
    target: ProjectDeclarationOccurrenceIdentity,
    expected_identities: tuple[ProjectModuleRowFieldIdentity, ...],
    required_fields: tuple[ProjectRowField, ...],
) -> ProjectIRQueryBlockRowCompatibility:
    return ProjectIRQueryBlockRowCompatibility(
        output=output,
        target=target,
        expected_identities=expected_identities,
        required_fields=required_fields,
    )


def _historical_rebound_contexts(
    fragment: ProjectIRConcreteSingleRelationFragment,
) -> tuple[ProjectIRQueryBlockAggregateEvaluationContext, ...]:
    semantic = fragment.semantic_facts
    operators = tuple(
        operator
        for operator in fragment.logical_stage.operators
        if operator.kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE
    )
    if not operators:
        return ()
    if len(operators) != 1:
        raise ValueError("Historical fragment requires at most one aggregate stage.")
    mode = (
        ProjectJoinedAggregationMode.GROUPED
        if semantic.group_key_occurrences
        else ProjectJoinedAggregationMode.GLOBAL
    )
    keys, outputs = _aggregate_basis_values(semantic, mode)
    return (
        ProjectIRQueryBlockAggregateEvaluationContext(
            operator=operators[0],
            semantic_basis=semantic,
            mode=mode,
            group_keys=keys,
            aggregate_outputs=outputs,
        ),
    )


def _operator_specs(
    entry: ProjectCompletedEffectiveOutput,
) -> tuple[
    tuple[ProjectIRQueryBlockOperatorKind, ProjectIRQueryBlockOperatorEvidence], ...
]:
    root = entry.root
    values: list[
        tuple[ProjectIRQueryBlockOperatorKind, ProjectIRQueryBlockOperatorEvidence]
    ] = []
    if type(root) is ProjectConcreteJoinedQualify:
        window_stage = root.window_stage
        aggregation = window_stage.input_aggregation
        input_filter = aggregation.input_filter
        if input_filter.kind is ProjectJoinedRowFilterKind.AUTHORED_WHERE:
            values.append((ProjectIRLogicalOperatorKind.ROW_FILTER, input_filter))
        if aggregation.mode is not ProjectJoinedAggregationMode.ABSENT:
            values.append((ProjectIRLogicalOperatorKind.GROUP_AGGREGATE, aggregation))
        if aggregation.satisfying is not None:
            values.append(
                (ProjectIRLogicalOperatorKind.RESULT_FILTER, aggregation.satisfying)
            )
        if window_stage.computations or root.hidden_computations:
            values.append(
                (
                    ProjectIRLogicalOperatorKind.WINDOW_EVALUATION,
                    ProjectIRQueryBlockWindowEvidence(
                        completed_output=entry,
                        selected=window_stage.computations,
                        hidden=root.hidden_computations,
                    ),
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
        definition = cast(TableDef | QueryDef, root.owner.definition)
        if definition.satisfying_clause is not None:
            values.append((ProjectIRLogicalOperatorKind.RESULT_FILTER, root))
        if root.window_outputs or root.qualify.hidden_attempts:
            values.append(
                (
                    ProjectIRLogicalOperatorKind.WINDOW_EVALUATION,
                    ProjectIRQueryBlockWindowEvidence(
                        completed_output=entry,
                        selected=root.window_outputs,
                        hidden=root.qualify.hidden_attempts,
                    ),
                )
            )
        if root.qualify.kind is ProjectNoJoinQualifyKind.AUTHORED_QUALIFY:
            values.append((ProjectIRQueryBlockOperatorExtensionKind.QUALIFY, root))
    else:
        raise TypeError("Completed output requires one closed final semantic root.")
    values.append((ProjectIRLogicalOperatorKind.FINAL_PROJECTION, entry))
    if entry.ordering is not None:
        values.append((ProjectIRLogicalOperatorKind.RELATION_ORDERING, entry.ordering))
    if entry.limit is not None:
        values.append((ProjectIRLogicalOperatorKind.LIMIT, entry.limit))
    return tuple(values)


def _shape_field_provenance(
    output: ProjectIRQueryBlockInputRowOutput,
    position: int,
) -> tuple[
    ProjectIRJoinInputUseOccurrence | ProjectIRUseOccurrence | None,
    tuple[ProjectIRPlanNodeRef, ...],
]:
    field_ = output.row_shape.fields[position]
    if type(output) is ProjectIRJoinRowOutput:
        joined_field = cast(ProjectIRJoinedRowField, field_)
        return joined_field.introduction_use, joined_field.nulling_joins
    if type(output) is ProjectIRQueryBlockRowOutput:
        query_field = cast(ProjectIRQueryBlockRowField, field_)
        return query_field.introduction_use, query_field.nulling_joins
    return None, ()


def _shape_field_source(
    output: ProjectIRQueryBlockInputRowOutput,
    position: int,
    joined_sources: tuple[ProjectJoinedRowFieldSemantics, ...],
) -> ProjectIRQueryBlockSemanticFieldSource:
    field_ = output.row_shape.fields[position]
    if type(output) is ProjectIRJoinRowOutput:
        if len(joined_sources) != len(output.row_shape.fields):
            raise ValueError("Joined input requires complete Slice-6 field semantics.")
        return joined_sources[position]
    if type(output) is ProjectIRQueryBlockRowOutput:
        return cast(ProjectIRQueryBlockRowField, field_).semantic_source
    if type(output) is not ProjectIRRelationRowOutput or type(field_) not in {
        ProjectIRRowField,
        ProjectIRStageRowField,
    }:
        raise TypeError("Historical row requires exact field evidence.")
    return cast(ProjectIRRowField | ProjectIRStageRowField, field_)


def _preserved_query_fields(
    output: ProjectIRQueryBlockInputRowOutput,
    joined_sources: tuple[ProjectJoinedRowFieldSemantics, ...],
) -> tuple[ProjectIRQueryBlockRowField, ...]:
    values: list[ProjectIRQueryBlockRowField] = []
    for position, field_ in enumerate(output.row_shape.fields):
        introduction, nulling = _shape_field_provenance(output, position)
        if type(output) is ProjectIRJoinRowOutput:
            effective_nullability = cast(
                ProjectIRJoinedRowField, field_
            ).effective_nullability
        elif type(output) is ProjectIRQueryBlockRowOutput:
            effective_nullability = cast(
                ProjectIRQueryBlockRowField, field_
            ).effective_nullability
        else:
            effective_nullability = field_.evidence.nullability
        values.append(
            ProjectIRQueryBlockRowField(
                field_position=position,
                evidence=field_.evidence,
                semantic_source=_shape_field_source(output, position, joined_sources),
                effective_nullability=effective_nullability,
                introduction_use=introduction,
                nulling_joins=nulling,
            )
        )
    return tuple(values)


def _completed_field_for_source(
    entry: ProjectCompletedEffectiveOutput,
    source: object,
) -> ProjectCompletedOutputField:
    matches = tuple(field for field in entry.fields if field.source is source)
    if len(matches) != 1:
        raise ValueError("Stage output requires one exact completed field source.")
    return matches[0]


def _group_query_fields(
    entry: ProjectCompletedEffectiveOutput,
) -> tuple[ProjectIRQueryBlockRowField, ...]:
    root = entry.root
    if type(root) is ProjectConcreteJoinedQualify:
        sources: tuple[object, ...] = root.window_stage.input_aggregation.stage_outputs
    elif type(root) is ProjectConcreteNoJoinReplay:
        sources = tuple(
            field.source
            for field in entry.fields
            if type(field.source) is ProjectNoJoinGroupedOutput
        )
    else:
        raise TypeError("Group fields require one exact completed root.")
    values: list[ProjectIRQueryBlockRowField] = []
    for position, source in enumerate(sources):
        completed = _completed_field_for_source(entry, source)
        if type(source) is ProjectJoinedStageOutputOccurrence and (
            source.role is ProjectJoinedStageOutputRole.GROUP_KEY
        ):
            assert source.group_key is not None
            field_semantics = source.group_key.field_semantics
            introduction = field_semantics.introduction_use
            nulling = field_semantics.nulling_joins
        else:
            introduction = None
            nulling = ()
        values.append(
            ProjectIRQueryBlockRowField(
                field_position=position,
                evidence=completed.field,
                semantic_source=cast(ProjectIRQueryBlockSemanticFieldSource, source),
                effective_nullability=completed.field.nullability,
                introduction_use=introduction,
                nulling_joins=nulling,
            )
        )
    if not values:
        raise ValueError("Concrete aggregate stage requires exact output fields.")
    return tuple(values)


def _window_selected_sources(
    entry: ProjectCompletedEffectiveOutput,
) -> tuple[ProjectIRQueryBlockWindowSelectedEvidence, ...]:
    root = entry.root
    if type(root) is ProjectConcreteJoinedQualify:
        return cast(
            tuple[ProjectIRQueryBlockWindowSelectedEvidence, ...],
            root.window_stage.computations,
        )
    if type(root) is ProjectConcreteNoJoinReplay:
        return cast(
            tuple[ProjectIRQueryBlockWindowSelectedEvidence, ...],
            root.window_outputs,
        )
    raise TypeError("Window outputs require one exact completed root.")


def _window_source_binding(
    entry: ProjectCompletedEffectiveOutput,
    evidence: ProjectIRQueryBlockWindowSelectedEvidence,
) -> ProjectSelectedWindowResultBinding | ProjectModuleWindowOutputFact:
    if type(evidence) is ProjectConcreteWindowComputation:
        root = cast(ProjectConcreteJoinedQualify, entry.root)
        matches = tuple(
            item
            for item in root.window_stage.selected_results
            if item.computation is evidence
        )
        if len(matches) != 1:
            raise ValueError("Selected computation requires one exact result binding.")
        return matches[0]
    if type(evidence) is ProjectModuleWindowOutputFact:
        return evidence
    raise TypeError("Window scalar requires exact selected evidence.")


def _window_query_fields(
    entry: ProjectCompletedEffectiveOutput,
    incoming: tuple[ProjectIRQueryBlockRowField, ...],
) -> tuple[
    tuple[ProjectIRQueryBlockRowField, ...],
    tuple[ProjectSelectedWindowResultBinding | ProjectModuleWindowOutputFact, ...],
]:
    selected_sources: list[
        ProjectSelectedWindowResultBinding | ProjectModuleWindowOutputFact
    ] = []
    additions: list[ProjectIRQueryBlockRowField] = []
    for offset, evidence in enumerate(_window_selected_sources(entry)):
        source = _window_source_binding(entry, evidence)
        completed = _completed_field_for_source(entry, source)
        selected_sources.append(source)
        additions.append(
            ProjectIRQueryBlockRowField(
                field_position=len(incoming) + offset,
                evidence=completed.field,
                semantic_source=source,
                effective_nullability=completed.field.nullability,
                introduction_use=None,
                nulling_joins=(),
            )
        )
    return (*incoming, *additions), tuple(selected_sources)


def _direct_source_position(
    entry: ProjectCompletedEffectiveOutput,
    source: ProjectCompletedOutputField,
    incoming_fields: tuple[ProjectIRQueryBlockRowField, ...],
) -> int | None:
    authority = source.source
    root = entry.root
    if type(root) is ProjectConcreteJoinedQualify:
        if type(authority) is ProjectConcreteJoinedNamespaceExpression:
            expression = authority.expression
            resolutions = authority.resolutions
            if (
                type(expression) not in {NameExpr, DottedNameExpr}
                or len(resolutions) != 1
            ):
                return None
            resolution = resolutions[0]
            if type(resolution) is not ProjectScalarReferenceResolution or (
                resolution.target is None
            ):
                return None
            matches = tuple(
                field.field_position
                for field in incoming_fields
                if type(field.semantic_source) is ProjectJoinedRowFieldSemantics
                and field.semantic_source.scalar_field is resolution.target
            )
        elif type(authority) in {
            ProjectJoinedStageOutputOccurrence,
            ProjectSelectedWindowResultBinding,
        }:
            matches = tuple(
                field.field_position
                for field in incoming_fields
                if field.semantic_source is authority
            )
        else:
            return None
    elif type(root) is ProjectConcreteNoJoinReplay:
        if type(authority) is ProjectNoJoinScalarExpression:
            expression = authority.expression
            provenance = source.field.provenance
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
                definition = cast(TableDef | QueryDef, root.owner.definition)
                if len(expression.parts) != 2 or (
                    expression.parts[0] != definition.from_clause.source_name
                ):
                    return None
                name = expression.parts[1]
            else:
                return None
            target = root.input_schema.fields.get(name)
            if target is None:
                return None
            matches = tuple(
                field.field_position
                for field in incoming_fields
                if field.evidence is target
            )
        elif type(authority) in {
            ProjectNoJoinGroupedOutput,
            ProjectModuleWindowOutputFact,
        }:
            matches = tuple(
                field.field_position
                for field in incoming_fields
                if field.semantic_source is authority
            )
        else:
            return None
    else:
        raise TypeError("Direct source mapping requires one exact completed root.")
    return matches[0] if len(matches) == 1 else None


def _final_query_fields(
    entry: ProjectCompletedEffectiveOutput,
    incoming: tuple[ProjectIRQueryBlockRowField, ...],
) -> tuple[ProjectIRQueryBlockRowField, ...]:
    values: list[ProjectIRQueryBlockRowField] = []
    for position, completed in enumerate(entry.fields):
        direct = _direct_source_position(entry, completed, incoming)
        if direct is None:
            introduction = None
            nulling = ()
        else:
            introduction = incoming[direct].introduction_use
            nulling = incoming[direct].nulling_joins
        values.append(
            ProjectIRQueryBlockRowField(
                field_position=position,
                evidence=completed.field,
                semantic_source=completed,
                effective_nullability=completed.field.nullability,
                introduction_use=introduction,
                nulling_joins=nulling,
                final_identity=completed.identity,
            )
        )
    return tuple(values)


def _joined_input_sources(
    entry: ProjectCompletedEffectiveOutput,
) -> tuple[ProjectJoinedRowFieldSemantics, ...]:
    root = entry.root
    if type(root) is not ProjectConcreteJoinedQualify:
        return ()
    return root.window_stage.input_aggregation.input_filter.fields


def _completed_aggregate_context(
    entry: ProjectCompletedEffectiveOutput,
    operator: ProjectIRQueryBlockOperatorOccurrence,
) -> ProjectIRQueryBlockAggregateEvaluationContext:
    root = entry.root
    if type(root) is ProjectConcreteJoinedQualify:
        basis: ProjectIRQueryBlockAggregateSemanticBasis = (
            root.window_stage.input_aggregation
        )
        mode = basis.mode
    elif type(root) is ProjectConcreteNoJoinReplay:
        basis = root
        mode = root.mode
    else:
        raise TypeError("Aggregate context requires one completed semantic root.")
    keys, outputs = _aggregate_basis_values(basis, mode)
    return ProjectIRQueryBlockAggregateEvaluationContext(
        operator=operator,
        semantic_basis=basis,
        mode=mode,
        group_keys=keys,
        aggregate_outputs=outputs,
    )


def _build_completed_structure(
    *,
    entry: ProjectCompletedEffectiveOutput,
    input_output: ProjectIRQueryBlockInputRowOutput,
    allocation: ProjectIRAllocationState,
    source_owner: ProjectDeclarationOccurrence | None,
    source_relational: ProjectIROutputRelationalProperties | None,
    dependency: ProjectCompletionDependency | None,
    authority: ProjectIRResolvedRelationAnchor | None,
    compatibility: ProjectIRQueryBlockRowCompatibility | None,
) -> _PendingCompleted:
    specs = _operator_specs(entry)
    relation = ProjectIRRelationAnchor(identity=_declaration_identity(entry.owner))
    current = allocation
    incoming = input_output
    joined_sources = _joined_input_sources(entry)
    operators: list[ProjectIRQueryBlockOperatorOccurrence] = []
    row_outputs: list[ProjectIRQueryBlockRowOutput] = []
    scalar_outputs: list[ProjectIRQueryBlockScalarOutput] = []
    slots: list[ProjectIRInputSlotOccurrence] = []
    uses: list[ProjectIRUseOccurrence | ProjectIROperatorFlowUseOccurrence] = []
    contexts: list[ProjectIRQueryBlockAggregateEvaluationContext] = []
    policies: list[ProjectIRQueryBlockWindowPolicy] = []
    effects: list[ProjectIRQueryBlockEffectEvidence] = []
    active_kind = _active_root_operator_kind(entry)
    active_output: ProjectIRQueryBlockRowOutput | None = None

    for kind, evidence in specs:
        node = ProjectIRPlanNodeOccurrence(
            ref=ProjectIRPlanNodeRef(
                scope=allocation.scope,
                position=current.next_plan_node_position,
            ),
            anchor=relation,
        )
        operator = ProjectIRQueryBlockOperatorOccurrence(
            node=node,
            kind=kind,
            evidence=evidence,
        )
        incoming_fields = _preserved_query_fields(
            incoming,
            joined_sources if type(incoming) is ProjectIRJoinRowOutput else (),
        )
        selected_sources: tuple[
            ProjectSelectedWindowResultBinding | ProjectModuleWindowOutputFact,
            ...,
        ] = ()
        if kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
            fields = _group_query_fields(entry)
        elif kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION:
            fields, selected_sources = _window_query_fields(entry, incoming_fields)
        elif kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
            fields = _final_query_fields(entry, incoming_fields)
        else:
            fields = incoming_fields
        row_occurrence = ProjectIROutputValueOccurrence(
            ref=ProjectIROutputValueRef(
                scope=allocation.scope,
                position=current.next_output_value_position,
            ),
            producer=node,
            anchor=relation,
        )
        row_output = ProjectIRQueryBlockRowOutput(
            occurrence=row_occurrence,
            row_shape=ProjectIRQueryBlockRowShape(
                relation=relation,
                producer=node,
                operator=operator,
                fields=fields,
            ),
        )
        if kind is active_kind:
            if active_output is not None:
                raise ValueError("Completed output cannot retain two active row roots.")
            active_output = row_output
        owned_scalars: list[ProjectIRQueryBlockScalarOutput] = []
        if kind is ProjectIRLogicalOperatorKind.WINDOW_EVALUATION:
            first_position = len(fields) - len(selected_sources)
            for offset, source in enumerate(selected_sources):
                field_position = first_position + offset
                occurrence = ProjectIROutputValueOccurrence(
                    ref=ProjectIROutputValueRef(
                        scope=allocation.scope,
                        position=current.next_output_value_position + offset + 1,
                    ),
                    producer=node,
                    anchor=ProjectIRStageFieldAnchor(
                        producer=node,
                        field_position=field_position,
                    ),
                )
                scalar = ProjectIRQueryBlockScalarOutput(
                    occurrence=occurrence,
                    row_output=row_output,
                    field_position=field_position,
                    semantic_source=source,
                )
                evidence_item = (
                    source.computation
                    if type(source) is ProjectSelectedWindowResultBinding
                    else source
                )
                owned_scalars.append(scalar)
                policies.append(
                    ProjectIRQueryBlockWindowPolicy(
                        output=scalar,
                        evidence=cast(
                            ProjectIRQueryBlockWindowSelectedEvidence,
                            evidence_item,
                        ),
                    )
                )
        elif kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION:
            for offset, completed in enumerate(entry.fields):
                occurrence = ProjectIROutputValueOccurrence(
                    ref=ProjectIROutputValueRef(
                        scope=allocation.scope,
                        position=current.next_output_value_position + offset + 1,
                    ),
                    producer=node,
                    anchor=ProjectIRFieldAnchor(identity=completed.identity),
                )
                owned_scalars.append(
                    ProjectIRQueryBlockScalarOutput(
                        occurrence=occurrence,
                        row_output=row_output,
                        field_position=offset,
                        semantic_source=completed,
                        final_identity=completed.identity,
                    )
                )
        slot = ProjectIRInputSlotOccurrence(
            ref=ProjectIRInputSlotRef(
                scope=allocation.scope,
                position=current.next_input_slot_position,
            ),
            consumer=node,
            input_ordinal=0,
        )
        if kind is ProjectIRLogicalOperatorKind.RELATION_INPUT:
            if dependency is None or authority is None:
                raise ValueError(
                    "Replay RELATION_INPUT requires exact dependency roots."
                )
            use: ProjectIRUseOccurrence | ProjectIROperatorFlowUseOccurrence = (
                ProjectIRUseOccurrence(
                    ref=ProjectIRUseRef(
                        scope=allocation.scope,
                        position=current.next_use_position,
                    ),
                    output=incoming.occurrence,
                    slot=slot,
                    role=ProjectModuleFactOccurrenceRole.RELATION_INPUT,
                    source_order=0,
                    anchor=authority,
                )
            )
        else:
            use = ProjectIROperatorFlowUseOccurrence(
                ref=ProjectIRUseRef(
                    scope=allocation.scope,
                    position=current.next_use_position,
                ),
                output=incoming.occurrence,
                slot=slot,
            )
        operators.append(operator)
        row_outputs.append(row_output)
        scalar_outputs.extend(owned_scalars)
        slots.append(slot)
        uses.append(use)
        effects.append(ProjectIRQueryBlockEffectEvidence(output=row_output))
        effects.extend(
            ProjectIRQueryBlockEffectEvidence(output=scalar) for scalar in owned_scalars
        )
        if kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
            contexts.append(_completed_aggregate_context(entry, operator))
        current = ProjectIRAllocationState(
            scope=allocation.scope,
            next_plan_node_position=current.next_plan_node_position + 1,
            next_output_value_position=(
                current.next_output_value_position + 1 + len(owned_scalars)
            ),
            next_input_slot_position=current.next_input_slot_position + 1,
            next_use_position=current.next_use_position + 1,
        )
        incoming = row_output

    if active_output is None:
        raise ValueError("Completed output requires one constructed active row root.")
    return _PendingCompleted(
        semantic_entry=entry,
        source_owner=source_owner,
        source_relational=source_relational,
        starting_allocation=allocation,
        ending_allocation=current,
        operators=tuple(operators),
        row_outputs=tuple(row_outputs),
        scalar_outputs=tuple(scalar_outputs),
        slots=tuple(slots),
        uses=tuple(uses),
        aggregate_contexts=tuple(contexts),
        window_policies=tuple(policies),
        effects=tuple(effects),
        dependency=dependency,
        authority=authority,
        compatibility=compatibility,
        active_output=active_output,
    )


def _pending_active_output(
    entry: _PendingEntry,
) -> ProjectIRActiveRowOutput | None:
    if type(entry) is _PendingReuse:
        return entry.active_output
    if type(entry) is _PendingRebound:
        return entry.active_output
    if type(entry) is _PendingCompleted:
        return entry.active_output
    if type(entry) is _PendingTerminal:
        return None
    raise TypeError("Pending active output requires a closed entry.")


def _owner_for_output(
    owners: tuple[ProjectDeclarationOccurrence, ...],
    output: ProjectIROutputValueOccurrence,
) -> ProjectDeclarationOccurrence | None:
    if type(output.anchor) is not ProjectIRRelationAnchor:
        return None
    matches = tuple(
        owner
        for owner in owners
        if _declaration_identity(owner) == output.anchor.identity
    )
    if len(matches) > 1:
        raise ValueError("Output relation identity cannot select an owner winner.")
    return matches[0] if matches else None


def _stale_join_inputs(
    *,
    entry: ProjectCompletedEffectiveOutput,
    owners: tuple[ProjectDeclarationOccurrence, ...],
    pending_by_owner: dict[int, _PendingEntry],
) -> tuple[ProjectIRJoinInputUseOccurrence, ...]:
    root = entry.root
    if type(root) is not ProjectConcreteJoinedQualify:
        return ()
    region = root.window_stage.input_aggregation.input_filter.joined_semantics.row_source.region
    if type(region) is not ProjectIRConcreteJoinRegion:
        raise ValueError("Joined completion requires one exact concrete JOIN region.")
    region_nodes = tuple(join.node for join in region.joins)
    stale: list[ProjectIRJoinInputUseOccurrence] = []
    for join in region.joins:
        for use in join.input_uses:
            if any(use.output.producer is node for node in region_nodes):
                continue
            owner = _owner_for_output(owners, use.output)
            active = None if owner is None else pending_by_owner.get(id(owner))
            active_output = None if active is None else _pending_active_output(active)
            if active_output is None or active_output.occurrence is not use.output:
                stale.append(use)
    return tuple(stale)


def _historical_required_fields(
    entry: ProjectExistingEffectiveOutput,
) -> tuple[ProjectRowField, ...]:
    state = entry.fragment.semantic_facts.input_state
    if (
        state is None
        or state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        or state.schema is None
        or state.schema.is_unknown
    ):
        raise ValueError("Historical rebound requires concrete INPUT row authority.")
    return tuple(state.schema.fields.values())


def _build_rebound_pending(
    *,
    entry: ProjectExistingEffectiveOutput,
    dependency: ProjectCompletionDependency,
    upstream_owner: ProjectDeclarationOccurrence,
    active_output: ProjectIRActiveRowOutput,
    compatibility: ProjectIRQueryBlockRowCompatibility,
    plan: ProjectIRProjectPlan,
    allocation: ProjectIRAllocationState,
) -> _PendingRebound:
    fragment = build_project_ir_single_relation_fragment(
        semantic=entry.fragment.semantic_facts,
        attribution=plan.attribution,
        allocation=allocation,
    )
    if type(fragment) is not ProjectIRConcreteSingleRelationFragment:
        raise ValueError("Historical rebound requires concrete local semantics.")
    authority = _resolved_relation_anchor(dependency=dependency, plan=plan)
    slot = ProjectIRInputSlotOccurrence(
        ref=ProjectIRInputSlotRef(
            scope=allocation.scope,
            position=fragment.ending_allocation.next_input_slot_position,
        ),
        consumer=_relation_input_node(fragment),
        input_ordinal=0,
    )
    use = ProjectIRUseOccurrence(
        ref=ProjectIRUseRef(
            scope=allocation.scope,
            position=fragment.ending_allocation.next_use_position,
        ),
        output=active_output.occurrence,
        slot=slot,
        role=ProjectModuleFactOccurrenceRole.RELATION_INPUT,
        source_order=0,
        anchor=authority,
    )
    ending = ProjectIRAllocationState(
        scope=allocation.scope,
        next_plan_node_position=fragment.ending_allocation.next_plan_node_position,
        next_output_value_position=fragment.ending_allocation.next_output_value_position,
        next_input_slot_position=(
            fragment.ending_allocation.next_input_slot_position + 1
        ),
        next_use_position=fragment.ending_allocation.next_use_position + 1,
    )
    return _PendingRebound(
        semantic_entry=entry,
        starting_allocation=allocation,
        ending_allocation=ending,
        fragment=fragment,
        dependency=dependency,
        upstream_owner=upstream_owner,
        authority=authority,
        slot=slot,
        use=use,
        compatibility=compatibility,
        aggregate_contexts=_historical_rebound_contexts(fragment),
        active_output=fragment.root_relation_output,
    )


def _build_pending_entries(
    completed: ProjectConcreteCompletedSemanticResult,
) -> tuple[
    tuple[_PendingEntry, ...],
    dict[int, _PendingEntry],
    ProjectIRAllocationState,
]:
    verification = completed.verification
    overlay = completed.effective_outputs
    plan = verification.root.evaluation.project_plan
    if (
        not verification.verified
        or completed.completion is not overlay.base
        or completed.completion.verification is not verification
        or overlay.owners is not completed.completion.owners
        or overlay.schedule is not completed.completion.schedule
    ):
        raise ValueError("Query-block construction requires exact Slice-13 roots.")
    semantic_by_owner = {
        id(owner): entry
        for owner, entry in zip(overlay.owners, overlay.entries, strict=True)
    }
    pending_by_owner: dict[int, _PendingEntry] = {}
    current = verification.root.join_regions.ending_allocation
    for owner in overlay.schedule:
        semantic_entry = semantic_by_owner[id(owner)]
        if type(semantic_entry) in {
            ProjectEffectiveOutputTerminal,
            ProjectEffectiveOutputCompletionTerminal,
        }:
            pending: _PendingEntry = _PendingTerminal(
                semantic_entry=semantic_entry,
                reason=(ProjectIRQueryBlockTerminalReason.SEMANTIC_OUTPUT_NON_CONCRETE),
                blocker=semantic_entry,
                allocation=current,
            )
        elif type(semantic_entry) is ProjectExistingEffectiveOutput:
            definition = semantic_entry.owner.definition
            if type(definition) is SourceDef:
                pending = _PendingReuse(
                    semantic_entry=semantic_entry,
                    allocation=current,
                    active_output=semantic_entry.output,
                )
            else:
                if len(semantic_entry.dependencies) != 1:
                    raise ValueError(
                        "Historical no-JOIN output requires one dependency."
                    )
                dependency = semantic_entry.dependencies[0]
                upstream = pending_by_owner[id(dependency.target)]
                active_output = _pending_active_output(upstream)
                if active_output is None:
                    pending = _PendingTerminal(
                        semantic_entry=semantic_entry,
                        reason=(
                            ProjectIRQueryBlockTerminalReason.ACTIVE_UPSTREAM_IR_NON_CONCRETE
                        ),
                        blocker=upstream,
                        allocation=current,
                    )
                else:
                    edge = _historical_cross_edge(plan, semantic_entry)
                    if edge.use.output is active_output.occurrence:
                        pending = _PendingReuse(
                            semantic_entry=semantic_entry,
                            allocation=current,
                            active_output=semantic_entry.output,
                        )
                    else:
                        compatibility = _row_compatibility(
                            output=active_output,
                            target=edge.authority.target,
                            expected_identities=_active_output_identities(
                                edge.producer.root_relation_output
                            ),
                            required_fields=_historical_required_fields(semantic_entry),
                        )
                        if not compatibility.satisfied:
                            pending = _PendingTerminal(
                                semantic_entry=semantic_entry,
                                reason=(
                                    ProjectIRQueryBlockTerminalReason.ACTIVE_UPSTREAM_ROW_INCOMPATIBLE
                                ),
                                blocker=compatibility,
                                allocation=current,
                            )
                        else:
                            pending = _build_rebound_pending(
                                entry=semantic_entry,
                                dependency=dependency,
                                upstream_owner=dependency.target,
                                active_output=active_output,
                                compatibility=compatibility,
                                plan=plan,
                                allocation=current,
                            )
                            current = pending.ending_allocation
        elif type(semantic_entry) is ProjectCompletedEffectiveOutput:
            root = semantic_entry.root
            if type(root) is ProjectConcreteJoinedQualify:
                stale = _stale_join_inputs(
                    entry=semantic_entry,
                    owners=overlay.owners,
                    pending_by_owner=pending_by_owner,
                )
                if stale:
                    pending = _PendingTerminal(
                        semantic_entry=semantic_entry,
                        reason=(
                            ProjectIRQueryBlockTerminalReason.EFFECTIVE_JOIN_INPUT_REBIND_UNSUPPORTED
                        ),
                        blocker=stale,
                        allocation=current,
                    )
                else:
                    bridge = root.window_stage.input_aggregation.input_filter.preservation.input_property_bridge
                    input_output = bridge.relational.output
                    if type(input_output) is not ProjectIRJoinRowOutput:
                        raise ValueError(
                            "Joined tail requires the exact Phase-62 JOIN output."
                        )
                    pending = _build_completed_structure(
                        entry=semantic_entry,
                        input_output=input_output,
                        allocation=current,
                        source_owner=None,
                        source_relational=bridge.relational,
                        dependency=None,
                        authority=None,
                        compatibility=None,
                    )
                    current = pending.ending_allocation
            elif type(root) is ProjectConcreteNoJoinReplay:
                if len(semantic_entry.dependencies) != 1:
                    raise ValueError("No-JOIN replay requires one exact dependency.")
                dependency = semantic_entry.dependencies[0]
                upstream = pending_by_owner[id(dependency.target)]
                active_output = _pending_active_output(upstream)
                if active_output is None:
                    pending = _PendingTerminal(
                        semantic_entry=semantic_entry,
                        reason=(
                            ProjectIRQueryBlockTerminalReason.ACTIVE_UPSTREAM_IR_NON_CONCRETE
                        ),
                        blocker=upstream,
                        allocation=current,
                    )
                else:
                    upstream_semantic = semantic_by_owner[id(dependency.target)]
                    if type(upstream_semantic) not in {
                        ProjectExistingEffectiveOutput,
                        ProjectCompletedEffectiveOutput,
                    }:
                        raise ValueError("Concrete replay requires concrete semantics.")
                    concrete_upstream = cast(
                        ProjectExistingEffectiveOutput
                        | ProjectCompletedEffectiveOutput,
                        upstream_semantic,
                    )
                    authority = _resolved_relation_anchor(
                        dependency=dependency,
                        plan=plan,
                    )
                    compatibility = _row_compatibility(
                        output=active_output,
                        target=authority.target,
                        expected_identities=_semantic_entry_identities(
                            concrete_upstream
                        ),
                        required_fields=tuple(root.input_schema.fields.values()),
                    )
                    if not compatibility.satisfied:
                        pending = _PendingTerminal(
                            semantic_entry=semantic_entry,
                            reason=(
                                ProjectIRQueryBlockTerminalReason.ACTIVE_UPSTREAM_ROW_INCOMPATIBLE
                            ),
                            blocker=compatibility,
                            allocation=current,
                        )
                    else:
                        pending = _build_completed_structure(
                            entry=semantic_entry,
                            input_output=active_output,
                            allocation=current,
                            source_owner=dependency.target,
                            source_relational=None,
                            dependency=dependency,
                            authority=authority,
                            compatibility=compatibility,
                        )
                        current = pending.ending_allocation
            else:
                raise TypeError("Completed output lost its exact final root.")
        else:
            raise TypeError("Effective output overlay lost its closed entry family.")
        pending_by_owner[id(owner)] = pending
    return (
        tuple(pending_by_owner[id(owner)] for owner in overlay.owners),
        pending_by_owner,
        current,
    )


def _grain_origin_extension(
    completed: ProjectConcreteCompletedSemanticResult,
    pending_by_owner: dict[int, _PendingEntry],
) -> ProjectIRQueryBlockGrainOriginExtension:
    contexts: list[ProjectIRQueryBlockAggregateEvaluationContext] = []
    for owner in completed.effective_outputs.schedule:
        pending = pending_by_owner[id(owner)]
        if type(pending) is _PendingRebound:
            contexts.extend(pending.aggregate_contexts)
        elif type(pending) is _PendingCompleted:
            contexts.extend(pending.aggregate_contexts)
    origins: list[ProjectIRQueryBlockGrainOrigin] = []
    for context in contexts:
        if context.mode is ProjectJoinedAggregationMode.GROUPED:
            factor = ProjectGroupedGrainFactorIdentity(
                owner=context.grouped_owner,
                operator=context.operator.node.ref,
                context=context,
            )
            kind = ProjectGrainOriginKind.GROUPED_RESULT
        else:
            factor = None
            kind = ProjectGrainOriginKind.GLOBAL_AGGREGATE
        origins.append(
            ProjectIRQueryBlockGrainOrigin(
                kind=kind,
                context=context,
                factor=factor,
            )
        )
    return ProjectIRQueryBlockGrainOriginExtension(
        base=completed.verification.root.base_relational.origins,
        origins=tuple(origins),
    )


def _origin_for_context(
    origins: ProjectIRQueryBlockGrainOriginExtension,
    context: ProjectIRQueryBlockAggregateEvaluationContext,
) -> ProjectIRQueryBlockGrainOrigin:
    matches = tuple(item for item in origins.origins if item.context is context)
    if len(matches) != 1:
        raise ValueError("Aggregate context requires one exact new grain origin.")
    return matches[0]


def _class_for_position(
    properties: ProjectIROutputRelationalProperties,
    position: int,
) -> ProjectIROutputValueClass:
    matches = tuple(
        value_class
        for value_class in properties.value_classes
        if any(member.field_position == position for member in value_class.members)
    )
    if len(matches) != 1:
        raise ValueError("Field position requires one exact value class.")
    return matches[0]


def _group_input_classes(
    context: ProjectIRQueryBlockAggregateEvaluationContext,
    incoming: ProjectIROutputRelationalProperties,
) -> tuple[ProjectIROutputValueClass, ...]:
    basis = context.semantic_basis
    positions: list[int] = []
    if type(basis) is ProjectConcreteJoinedAggregation:
        for key in basis.group_keys:
            if type(incoming.output) is ProjectIRQueryBlockRowOutput:
                matches = tuple(
                    field.field_position
                    for field in incoming.output.row_shape.fields
                    if field.semantic_source is key.field_semantics
                )
            else:
                matches = tuple(
                    member.field_position
                    for member in incoming.fields
                    if member.evidence is key.field_semantics.joined_field.evidence
                )
            if len(matches) != 1:
                raise ValueError("Joined group key requires one exact input field.")
            positions.append(matches[0])
    elif type(basis) is ProjectConcreteNoJoinReplay:
        for fact in context.group_keys:
            if type(fact) is not ProjectRelationClauseDependencyFact:
                raise TypeError("Replay group key requires exact dependency evidence.")
            matches = tuple(
                member.field_position
                for member in incoming.fields
                if member.evidence is fact.target_field
            )
            if len(matches) != 1:
                raise ValueError("Replay group key requires one exact input field.")
            positions.append(matches[0])
    else:
        assert type(basis) is ProjectModuleRelationSemanticFacts
        targets = tuple(
            target
            for fact in basis.clause_dependencies
            if fact.role is ProjectModuleFactOccurrenceRole.GROUP_KEY
            for target in fact.target_fields
        )
        for target in targets:
            matches = tuple(
                member.field_position
                for member in incoming.fields
                if member.evidence is target
            )
            if len(matches) != 1:
                raise ValueError("Historical group key requires one exact input field.")
            positions.append(matches[0])
    selected: list[ProjectIROutputValueClass] = []
    for value_class in incoming.value_classes:
        if (
            any(member.field_position in positions for member in value_class.members)
            and value_class not in selected
        ):
            selected.append(value_class)
    return tuple(selected)


def _group_output_positions(
    output: ProjectIRRelationalRowOutput,
    context: ProjectIRQueryBlockAggregateEvaluationContext,
) -> tuple[int, ...]:
    if type(output) is ProjectIRQueryBlockRowOutput:
        positions = tuple(
            field.field_position
            for field in output.row_shape.fields
            if (
                type(field.semantic_source) is ProjectJoinedStageOutputOccurrence
                and field.semantic_source.role is ProjectJoinedStageOutputRole.GROUP_KEY
            )
            or (
                type(field.semantic_source) is ProjectNoJoinGroupedOutput
                and field.semantic_source.field.result_role.value == "group_key"
            )
        )
    else:
        positions = tuple(
            position
            for position, field in enumerate(output.row_shape.fields)
            if field.evidence.result_role.value == "group_key"
        )
    if len(positions) != len(context.group_keys):
        raise ValueError("GROUPED output must expose every exact group key.")
    return positions


def _grouped_relational_properties(
    *,
    incoming: ProjectIROutputRelationalProperties,
    output: ProjectIRRelationalRowOutput,
    context: ProjectIRQueryBlockAggregateEvaluationContext,
    origins: ProjectIRQueryBlockGrainOriginExtension,
) -> ProjectIROutputRelationalProperties:
    fields = _field_occurrences(output)
    classes = _singleton_classes(output, fields)
    origin = _origin_for_context(origins, context)
    dependencies = list(incoming.grain.dependencies)
    if context.mode is ProjectJoinedAggregationMode.GROUPED:
        factor = origin.factor
        if type(factor) is not ProjectGroupedGrainFactorIdentity:
            raise ValueError("GROUPED output requires one exact factor.")
        active: tuple[ProjectGrainFactorIdentity, ...] = (factor,)
        factors = (*incoming.grain.factors, ProjectGrainDomainFactor(identity=factor))
        if incoming.grain.active:
            dependencies.append(
                ProjectGrainDependencyFact(
                    determinants=incoming.grain.active,
                    dependents=active,
                )
            )
        input_group_classes = _group_input_classes(context, incoming)
        if incoming.grain.active and any(
            key.strength is ProjectRowUniquenessStrength.STRICT
            and set(key.determinants) <= set(input_group_classes)
            for key in incoming.keys
        ):
            dependencies.append(
                ProjectGrainDependencyFact(
                    determinants=active,
                    dependents=incoming.grain.active,
                )
            )
        key_classes = tuple(
            classes[position] for position in _group_output_positions(output, context)
        )
        keys = (
            ProjectIROutputCandidateKey(
                output=output,
                determinants=key_classes,
                strength=ProjectRowUniquenessStrength.STRICT,
                supports=(context, origin),
            ),
        )
        state = ProjectGrainBasisState.FACTORIZED
    else:
        active = ()
        factors = incoming.grain.factors
        keys = ()
        state = ProjectGrainBasisState.GLOBAL
    fds = _key_fds(output, classes, keys)
    grain = ProjectIRProvidedIntrinsicGrain(
        output=output,
        state=state,
        factors=factors,
        active=active,
        dependencies=tuple(dependencies),
        origin_set=origins,
        witness=(incoming.grain, context, origin),
    )
    return ProjectIROutputRelationalProperties(
        output=output,
        fields=fields,
        value_classes=classes,
        keys=keys,
        fds=fds,
        fd_index=_compile_output_fd_index(output, classes, fds),
        grain=grain,
    )


def _imaged_relational_properties(
    *,
    incoming: ProjectIROutputRelationalProperties,
    output: ProjectIRRelationalRowOutput,
    fields: tuple[ProjectIROutputFieldOccurrence, ...],
    classes: tuple[ProjectIROutputValueClass, ...],
    images: dict[ProjectIROutputValueClass, ProjectIROutputValueClass | None],
    operator: ProjectIRQueryBlockAggregateOperator,
    origins: ProjectIRQueryBlockGrainOriginExtension,
) -> ProjectIROutputRelationalProperties:
    keys, fds = _image_keys_and_fds(
        incoming,
        output,
        classes,
        images,
        support=operator,
    )
    grain = ProjectIRProvidedIntrinsicGrain(
        output=output,
        state=incoming.grain.state,
        factors=incoming.grain.factors,
        active=incoming.grain.active,
        dependencies=incoming.grain.dependencies,
        origin_set=origins,
        witness=(incoming.grain, operator),
    )
    return ProjectIROutputRelationalProperties(
        output=output,
        fields=fields,
        value_classes=classes,
        keys=keys,
        fds=fds,
        fd_index=_compile_output_fd_index(output, classes, fds),
        grain=grain,
    )


def _query_projection_images(
    *,
    incoming: ProjectIROutputRelationalProperties,
    output: ProjectIRQueryBlockRowOutput,
    entry: ProjectCompletedEffectiveOutput,
    fields: tuple[ProjectIROutputFieldOccurrence, ...],
) -> tuple[
    tuple[ProjectIROutputValueClass, ...],
    dict[ProjectIROutputValueClass, ProjectIROutputValueClass | None],
]:
    input_output = incoming.output
    if type(input_output) is ProjectIRQueryBlockRowOutput:
        input_fields = input_output.row_shape.fields
    elif type(input_output) is ProjectIRJoinRowOutput:
        input_fields = _preserved_query_fields(
            input_output,
            _joined_input_sources(entry),
        )
    else:
        raise TypeError("Completed projection requires an exact active input row.")
    source_classes: list[ProjectIROutputValueClass | None] = []
    for completed in entry.fields:
        position = _direct_source_position(
            entry,
            completed,
            input_fields,
        )
        source_classes.append(
            None if position is None else _class_for_position(incoming, position)
        )
    return _projection_classes_from_sources(
        incoming,
        output,
        fields,
        tuple(source_classes),
    )


def _context_for_operator(
    contexts: tuple[ProjectIRQueryBlockAggregateEvaluationContext, ...],
    operator: ProjectIRQueryBlockAggregateOperator,
) -> ProjectIRQueryBlockAggregateEvaluationContext:
    matches = tuple(item for item in contexts if item.operator is operator)
    if len(matches) != 1:
        raise ValueError("GROUP_AGGREGATE requires one exact query-block context.")
    return matches[0]


def _query_relational_properties(
    *,
    pending: _PendingCompleted,
    source: ProjectIROutputRelationalProperties,
    origins: ProjectIRQueryBlockGrainOriginExtension,
) -> tuple[
    tuple[ProjectIRQueryBlockResultProperties, ...],
    ProjectIRQueryBlockResultProperties,
]:
    current = source
    relation_ordering: ProjectRelationOrdering | None = None
    cardinality: ProjectRelationLimit | None = None
    results: list[ProjectIRQueryBlockResultProperties] = []
    active_properties: ProjectIRQueryBlockResultProperties | None = None
    for operator, output in zip(
        pending.operators,
        pending.row_outputs,
        strict=True,
    ):
        if operator.kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
            relational = _grouped_relational_properties(
                incoming=current,
                output=output,
                context=_context_for_operator(
                    pending.aggregate_contexts,
                    operator,
                ),
                origins=origins,
            )
        else:
            fields = _field_occurrences(output)
            classes, images = (
                _query_projection_images(
                    incoming=current,
                    output=output,
                    entry=pending.semantic_entry,
                    fields=fields,
                )
                if operator.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION
                else _preserving_classes(current, output, fields)
            )
            relational = _imaged_relational_properties(
                incoming=current,
                output=output,
                fields=fields,
                classes=classes,
                images=images,
                operator=operator,
                origins=origins,
            )
        if operator.kind is ProjectIRLogicalOperatorKind.RELATION_ORDERING:
            relation_ordering = pending.semantic_entry.ordering
            if relation_ordering is None:
                raise ValueError("ORDER operator requires exact Slice-12 ordering.")
        if operator.kind is ProjectIRLogicalOperatorKind.LIMIT:
            cardinality = pending.semantic_entry.limit
            if cardinality is None:
                raise ValueError("LIMIT operator requires exact Slice-12 authority.")
        effects = tuple(item for item in pending.effects if item.output is output)
        if len(effects) != 1:
            raise ValueError("Query-block row requires one unknown effect object.")
        result = ProjectIRQueryBlockResultProperties(
            relational=relational,
            multiplicity=ProjectJoinedRowMultiplicity.BAG,
            ordering=relation_ordering,
            cardinality=cardinality,
            effect=effects[0],
        )
        results.append(result)
        if output is pending.active_output:
            if active_properties is not None:
                raise ValueError("Completed output cannot retain two property roots.")
            active_properties = result
        current = relational
    if active_properties is None:
        raise ValueError("Completed output requires one active property root.")
    return tuple(results), active_properties


def _historical_provided[
    PropertyT: ProjectIRProvidedRelationOrdering
    | ProjectIRProvidedCardinalityUpperBound,
](
    fragment: ProjectIRConcreteSingleRelationFragment,
    output: ProjectIRRelationRowOutput,
    property_type: type[PropertyT],
) -> PropertyT | None:
    matches = tuple(
        item
        for item in fragment.property_stage.provided
        if type(item) is property_type and item.output is output
    )
    if len(matches) > 1:
        raise ValueError("Historical output cannot select a property winner.")
    return cast(PropertyT | None, matches[0] if matches else None)


def _historical_effect(
    fragment: ProjectIRConcreteSingleRelationFragment,
    output: ProjectIRRelationRowOutput,
) -> ProjectIREffectEvidence:
    matches = tuple(
        item for item in fragment.property_stage.effects if item.output is output
    )
    if len(matches) != 1:
        raise ValueError("Historical output requires one exact effect object.")
    return matches[0]


def _historical_result_properties(
    *,
    fragment: ProjectIRConcreteSingleRelationFragment,
    relational: ProjectIROutputRelationalProperties,
) -> ProjectIRQueryBlockResultProperties:
    output = relational.output
    if type(output) is not ProjectIRRelationRowOutput:
        raise TypeError("Historical properties require one relation-row output.")
    return ProjectIRQueryBlockResultProperties(
        relational=relational,
        multiplicity=ProjectJoinedRowMultiplicity.BAG,
        ordering=_historical_provided(
            fragment,
            output,
            ProjectIRProvidedRelationOrdering,
        ),
        cardinality=_historical_provided(
            fragment,
            output,
            ProjectIRProvidedCardinalityUpperBound,
        ),
        effect=_historical_effect(fragment, output),
    )


def _rebound_relational_properties(
    *,
    pending: _PendingRebound,
    source: ProjectIROutputRelationalProperties,
    origins: ProjectIRQueryBlockGrainOriginExtension,
) -> tuple[
    tuple[ProjectIRQueryBlockResultProperties, ...],
    ProjectIRQueryBlockResultProperties,
]:
    current = source
    values: list[ProjectIRQueryBlockResultProperties] = []
    active_properties: ProjectIRQueryBlockResultProperties | None = None
    row_outputs = _fragment_row_outputs(pending.fragment)
    for operator, output in zip(
        pending.fragment.logical_stage.operators,
        row_outputs,
        strict=True,
    ):
        if operator.kind is ProjectIRLogicalOperatorKind.GROUP_AGGREGATE:
            relational = _grouped_relational_properties(
                incoming=current,
                output=output,
                context=_context_for_operator(
                    pending.aggregate_contexts,
                    operator,
                ),
                origins=origins,
            )
        else:
            fields = _field_occurrences(output)
            classes, images = (
                _projection_images(current, operator, output, fields)
                if operator.kind is ProjectIRLogicalOperatorKind.FINAL_PROJECTION
                else _preserving_classes(current, output, fields)
            )
            relational = _imaged_relational_properties(
                incoming=current,
                output=output,
                fields=fields,
                classes=classes,
                images=images,
                operator=operator,
                origins=origins,
            )
        result = _historical_result_properties(
            fragment=pending.fragment,
            relational=relational,
        )
        values.append(result)
        if output is pending.active_output:
            if active_properties is not None:
                raise ValueError("Rebound output cannot retain two property roots.")
            active_properties = result
        current = relational
    if active_properties is None:
        raise ValueError("Rebound output requires one active property root.")
    return tuple(values), active_properties


def _find_built_entry(
    built_by_owner: dict[int, ProjectIRQueryBlockEntry],
    owner: ProjectDeclarationOccurrence,
) -> ProjectIRQueryBlockEntry:
    try:
        return built_by_owner[id(owner)]
    except KeyError as error:
        raise ValueError(
            "Active IR dependency must be built dependency-first."
        ) from error


def _active_properties(
    entry: ProjectIRQueryBlockEntry,
) -> ProjectIRQueryBlockResultProperties:
    if type(entry) is ProjectIRReusedEffectiveOutput:
        return entry.active_properties
    if type(entry) is ProjectIRReboundExistingOutput:
        return entry.active_properties
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return entry.active_properties
    raise ValueError("Active IR dependency requires a concrete output.")


def _build_final_entries(
    *,
    completed: ProjectConcreteCompletedSemanticResult,
    pending_by_owner: dict[int, _PendingEntry],
    origins: ProjectIRQueryBlockGrainOriginExtension,
) -> tuple[tuple[ProjectIRQueryBlockEntry, ...], dict[int, ProjectIRQueryBlockEntry]]:
    built_by_owner: dict[int, ProjectIRQueryBlockEntry] = {}
    for owner in completed.effective_outputs.schedule:
        pending = pending_by_owner[id(owner)]
        if type(pending) is _PendingTerminal:
            blocker = pending.blocker
            if pending.reason is (
                ProjectIRQueryBlockTerminalReason.ACTIVE_UPSTREAM_IR_NON_CONCRETE
            ):
                if type(blocker) is not _PendingTerminal:
                    raise ValueError("Upstream IR terminal lost its pending blocker.")
                blocker = _find_built_entry(
                    built_by_owner,
                    blocker.semantic_entry.owner,
                )
            built: ProjectIRQueryBlockEntry = ProjectIRQueryBlockTerminal(
                semantic_entry=pending.semantic_entry,
                reason=pending.reason,
                blocker=blocker,
                starting_allocation=pending.allocation,
                ending_allocation=pending.allocation,
            )
        elif type(pending) is _PendingReuse:
            active_properties = _historical_result_properties(
                fragment=pending.semantic_entry.fragment,
                relational=pending.semantic_entry.properties,
            )
            built = ProjectIRReusedEffectiveOutput(
                semantic_entry=pending.semantic_entry,
                starting_allocation=pending.allocation,
                ending_allocation=pending.allocation,
                active_output=pending.active_output,
                active_properties=active_properties,
            )
        elif type(pending) is _PendingRebound:
            producer = _active_properties(
                _find_built_entry(built_by_owner, pending.upstream_owner)
            )
            row_properties, active_properties = _rebound_relational_properties(
                pending=pending,
                source=producer.relational,
                origins=origins,
            )
            relation_input = ProjectIRQueryBlockRelationInputEdge(
                dependency=pending.dependency,
                authority=pending.authority,
                producer=producer,
                consumer=_relation_input_node(pending.fragment),
                input_slot=pending.slot,
                use=pending.use,
                compatibility=pending.compatibility,
            )
            built = ProjectIRReboundExistingOutput(
                semantic_entry=pending.semantic_entry,
                rebuilt_fragment=pending.fragment,
                starting_allocation=pending.starting_allocation,
                ending_allocation=pending.ending_allocation,
                relation_input=relation_input,
                aggregate_contexts=pending.aggregate_contexts,
                row_properties=row_properties,
                active_output=pending.active_output,
                active_properties=active_properties,
            )
        elif type(pending) is _PendingCompleted:
            if pending.source_owner is None:
                source = pending.source_relational
                if source is None:
                    raise ValueError("Joined tail requires exact Phase-62 properties.")
                producer = None
            else:
                producer = _active_properties(
                    _find_built_entry(built_by_owner, pending.source_owner)
                )
                source = producer.relational
            row_properties, active_properties = _query_relational_properties(
                pending=pending,
                source=source,
                origins=origins,
            )
            relation_input = None
            if producer is not None:
                if (
                    pending.dependency is None
                    or pending.authority is None
                    or pending.compatibility is None
                ):
                    raise ValueError("Replay input requires exact dependency evidence.")
                relation_input = ProjectIRQueryBlockRelationInputEdge(
                    dependency=pending.dependency,
                    authority=pending.authority,
                    producer=producer,
                    consumer=pending.operators[0].node,
                    input_slot=pending.slots[0],
                    use=cast(ProjectIRUseOccurrence, pending.uses[0]),
                    compatibility=pending.compatibility,
                )
            built = ProjectIRCompletedQueryBlockOutput(
                semantic_entry=pending.semantic_entry,
                source_properties=source,
                starting_allocation=pending.starting_allocation,
                ending_allocation=pending.ending_allocation,
                operators=pending.operators,
                row_outputs=pending.row_outputs,
                scalar_outputs=pending.scalar_outputs,
                input_slots=pending.slots,
                uses=pending.uses,
                aggregate_contexts=pending.aggregate_contexts,
                window_policies=pending.window_policies,
                effects=pending.effects,
                row_properties=row_properties,
                active_output=pending.active_output,
                active_properties=active_properties,
                relation_input=relation_input,
            )
        else:
            raise TypeError("Pending IR ledger lost its closed entry family.")
        built_by_owner[id(owner)] = built
    return (
        tuple(
            built_by_owner[id(owner)] for owner in completed.effective_outputs.owners
        ),
        built_by_owner,
    )


def _entry_structural_nodes(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectIRPlanNodeOccurrence, ...]:
    if type(entry) is ProjectIRReboundExistingOutput:
        return entry.rebuilt_fragment.structural_stage.nodes
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return entry.nodes
    return ()


def _entry_structural_outputs(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectIROutputValueOccurrence, ...]:
    if type(entry) is ProjectIRReboundExistingOutput:
        return entry.rebuilt_fragment.structural_stage.outputs
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return entry.output_occurrences
    return ()


def _entry_structural_slots(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectIRInputSlotOccurrence, ...]:
    if type(entry) is ProjectIRReboundExistingOutput:
        return (
            *entry.rebuilt_fragment.structural_stage.input_slots,
            entry.relation_input.input_slot,
        )
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return entry.input_slots
    return ()


def _entry_structural_uses(
    entry: ProjectIRQueryBlockEntry,
) -> tuple[ProjectIRUseOccurrence | ProjectIROperatorFlowUseOccurrence, ...]:
    if type(entry) is ProjectIRReboundExistingOutput:
        return (
            *entry.rebuilt_fragment.structural_stage.uses,
            entry.relation_input.use,
        )
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        return entry.uses
    return ()


def _build_structural_extension(
    *,
    completed: ProjectConcreteCompletedSemanticResult,
    built_by_owner: dict[int, ProjectIRQueryBlockEntry],
    ending_allocation: ProjectIRAllocationState,
) -> ProjectIRQueryBlockStructuralExtension:
    plan = completed.verification.root.evaluation.project_plan
    join_stage = completed.verification.root.join_regions
    scheduled = tuple(
        built_by_owner[id(owner)] for owner in completed.effective_outputs.schedule
    )
    return ProjectIRQueryBlockStructuralExtension(
        base_plan=plan,
        join_stage=join_stage,
        starting_allocation=join_stage.ending_allocation,
        ending_allocation=ending_allocation,
        nodes=tuple(
            node for entry in scheduled for node in _entry_structural_nodes(entry)
        ),
        outputs=tuple(
            output for entry in scheduled for output in _entry_structural_outputs(entry)
        ),
        input_slots=tuple(
            slot for entry in scheduled for slot in _entry_structural_slots(entry)
        ),
        uses=tuple(use for entry in scheduled for use in _entry_structural_uses(entry)),
    )


def build_project_query_block_ir(
    completed: ProjectConcreteCompletedSemanticResult,
) -> ProjectIRQueryBlockSnapshot:
    """Build one all-or-none active IR entry per exact Slice-12 output owner."""

    if type(completed) is not ProjectConcreteCompletedSemanticResult:
        raise TypeError("Query-block IR requires an exact concrete Slice-13 result.")
    verification = completed.verification
    overlay = completed.effective_outputs
    plan = verification.root.evaluation.project_plan
    join_stage = verification.root.join_regions
    if (
        completed.roots.verification is not verification
        or completed.roots.completion is not completed.completion
        or completed.roots.effective_outputs is not overlay
        or overlay.base is not completed.completion
        or completed.completion.plan is not plan
        or join_stage.base_plan is not plan
        or join_stage.ending_allocation.scope is not plan.structural_stage.scope
    ):
        raise ValueError("Query-block IR requires one exact completed snapshot root.")
    pending_entries, pending_by_owner, ending = _build_pending_entries(completed)
    if len(pending_entries) != len(overlay.owners):
        raise AssertionError("Pending IR ledger lost an effective owner.")
    origins = _grain_origin_extension(completed, pending_by_owner)
    entries, built_by_owner = _build_final_entries(
        completed=completed,
        pending_by_owner=pending_by_owner,
        origins=origins,
    )
    structural = _build_structural_extension(
        completed=completed,
        built_by_owner=built_by_owner,
        ending_allocation=ending,
    )
    return ProjectIRQueryBlockSnapshot(
        completed=completed,
        base_plan=plan,
        join_stage=join_stage,
        owners=overlay.owners,
        dependencies=overlay.dependencies,
        schedule=overlay.schedule,
        entries=entries,
        grain_origins=origins,
        structural=structural,
    )
