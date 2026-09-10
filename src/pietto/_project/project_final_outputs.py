"""Private Phase-63 final semantic outputs and completion overlay."""

from __future__ import annotations

from pietto._flat_relational_admission import syntax_diagnostics

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from pietto._project.aggregate_grouped_clause_facts import (
    ProjectAggregateGroupedClauseReadiness,
    ProjectAggregateGroupedClauseReadinessStatus,
    ProjectRelationClauseDependencyFact,
    ProjectRelationClauseDependencyKind,
    build_project_aggregate_grouped_clause_readiness,
)
from pietto._project.let_scope_facts import (
    ProjectLetScopeFactsStatus,
    ProjectRelationLetScopeFacts,
    build_project_relation_let_scope_facts,
)
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSymbol,
    _project_direct_relation_row_schema,
    _project_relation_row_schema_state_from_result,
)
from pietto._project.module_attribution import (
    ProjectModuleRowFieldIdentity,
    ProjectModuleRowFieldKind,
    _declaration_identity,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_resolution import ProjectTypeSourceResolutionSet
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
    ProjectModuleClauseDependencyFact,
    ProjectModuleFactOccurrenceRole,
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSelectFact,
    ProjectModuleWindowOutputFact,
    _clause_dependency_facts,
    _project_symbol_for_resolution,
    _window_output_facts,
)
from pietto._project.project_completion import (
    ProjectCompletion,
    ProjectCompletionDependency,
    ProjectEffectiveOutputEntry,
    ProjectEffectiveOutputTerminal,
    ProjectEffectiveOutputTerminalReason,
    ProjectExistingEffectiveOutput,
    build_project_joined_completion,
)
from pietto._project.project_current_joins import ProjectCurrentJoinRegion
from pietto._project.project_join_conditions import (
    ProjectJoinCondition,
    ProjectJoinConditionSet,
    ProjectJoinConditionCompletion,
    rebuild_project_join_condition,
)
from pietto._project.project_current_join_inputs import (
    ProjectCurrentInputAuthority,
    ProjectCurrentInputField,
    ProjectCurrentSourceField,
    ProjectCurrentBindingInput,
    ProjectCurrentJoinInputScope,
    ProjectCurrentPreMatchInputs,
    ProjectCurrentMaterializedInput,
    ProjectCurrentJoinInputFailure,
)
from pietto._project.project_ir_construction import ProjectIRAllocationState
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_query_block import (
    ProjectConcreteQueryBlock,
    ProjectCurrentJoinedRowSource,
    ProjectQueryBlockOwnerBridge,
)
from pietto._project.project_joined_row_semantics import (
    ProjectConcreteJoinedRowSemantics,
    ProjectNonConcreteJoinedRowSemantics,
    _canonical_field,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRProvidedIntrinsicGrain,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueClass,
    ProjectIROutputCandidateKey,
    _field_occurrences,
    _singleton_classes,
    _projection_classes_from_sources,
    _image_keys_and_fds,
    _compile_output_fd_index,
    _key_fds,
    ProjectIROutputValueClassSet,
    ProjectIROutputDeterminationStatus,
    ProjectIROutputDeterminationResult,
    strictly_determines_output,
    transfer_set_properties,
    distinct_output_grain,
)
from pietto._project.project_ir import (
    ProjectIRPlanNodeOccurrence,
    ProjectIRRelationAnchor,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.project_ir_evaluation_context import (
    ProjectIRGroupedEvaluationContext,
)
from pietto._project.project_grain import (
    ProjectDistinctGrainOrigin,
    ProjectSetGrainOrigin,
    ProjectGrainOriginAuthority,
    ProjectGrainBasisState,
    ProjectGrainDomainFactor,
    ProjectGroupedGrainFactorIdentity,
    ProjectGrainDependencyFact,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength
from pietto._project.project_set_operations import (
    ProjectSetInputScope,
    ProjectSetOperandUse,
    ProjectSetOperation,
    ProjectSetColumn,
    ProjectSetFailure,
    ProjectSetFailureReason,
    set_diagnostic,
)
from pietto._project.project_row_equivalence import (
    ProjectRowEquivalence,
    ProjectRowEquivalenceInput,
    ProjectRowEquivalenceField,
    compatible_row_types,
)
from pietto._project.project_relationship_uses import ProjectJoinUseState
from pietto._project.project_joined_aggregation import (
    ProjectConcreteJoinedAggregation,
    ProjectJoinedAggregationMode,
    ProjectJoinedGroupKeyOccurrence,
    ProjectJoinedStageOutputOccurrence,
    ProjectJoinedStageOutputRole,
    _mode,
)
from pietto._project.project_joined_qualify import (
    ProjectConcreteJoinedQualify,
    ProjectJoinedQualifyResult,
    ProjectJoinedQualifySet,
    ProjectNonConcreteJoinedQualify,
    _ProjectQualifyPredicateAnalysis,
    _ProjectQualifyPredicateNonConcreteReason,
    _analyze_qualify_predicate,
    _qualify_operands,
    _qualify_reference_diagnostic,
    build_project_joined_tail,
)
from pietto._project.project_joined_row_filter import (
    ProjectJoinedRowFilterSet,
    build_project_joined_row_filter,
    ProjectJoinedRowRetentionEffect,
    _SQL_ROW_RETENTION_EFFECTS,
)
from pietto._project.project_joined_windows import (
    ProjectJoinedWindowInputBinding,
    ProjectSelectedWindowResultBinding,
)
from pietto._project.project_scalar_namespaces import (
    ProjectConcreteJoinedNamespaceExpression,
    ProjectJoinedLetReferenceResolution,
    ProjectNonConcreteJoinedNamespaceExpression,
    analyze_project_joined_namespace_expression,
)
from pietto._project.project_scalar_references import (
    ProjectScalarReferenceResolution,
    ProjectScalarEnvironmentField,
)
from pietto._project.row_expression_schema import (
    _project_nullability,
    _project_resolved_type,
)
from pietto._project.row_expression_type_facts import (
    scalar_field_reference_leaves,
    project_row_field_to_semantic_value_type,
    project_row_schema_to_semantic_row_schema,
)
from pietto.ast_nodes import (
    DistinctClause,
    SetRelationDef,
    SetOperationKind,
    SetOperationQuantifier,
    AuthoredJoinKind,
    DottedNameExpr,
    Expression,
    LimitClause,
    LiteralExpr,
    NameExpr,
    OrderByClause,
    OrderItem,
    QualifyClause,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
    WindowExpr,
    WindowUseKind,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic import predicate_checks as semantic_predicates
from pietto.semantic.aggregates import (
    contains_semantic_aggregate,
    invalid_context_diagnostic,
)
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.group_by import _grouped_order_by_unsupported_diagnostic
from pietto.semantic.model import CheckMode, ValueType, ValueTypeKind
from pietto.semantic.relation_schemas import (
    _duplicate_projection_diagnostic,
    _projection_output_name,
    _unnamed_projection_diagnostic,
)
from pietto.semantic.relation_limits import MAX_RELATION_LIMIT, check_relation_limits
from pietto.semantic.window_analysis import (
    _WindowComputationAdmissionFailure,
    analyze_window_computation,
)
from pietto.semantic.window_input_analysis import (
    WindowInputBinding,
    WindowInputOriginKind,
    WindowInputScope,
    WindowInputScopeKind,
    build_window_input_scope,
)
from pietto.semantic.window_semantics import (
    NamedWindowResolutionFailure,
    ResolvedNamedWindowNamespace,
    WindowComputationAnalysis,
    WindowComputationUnsupported,
)

__all__: tuple[str, ...] = ()

_DerivedRelation = TableDef | QueryDef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectDistinctFullRowUniqueness:
    """NULL-equal full-row uniqueness; neither a smaller key nor cardinality."""

    distinct: ProjectDistinct = field(repr=False)
    nulls_equal: bool = field(default=True, init=False)

    @property
    def fields(self) -> tuple[ProjectCompletedOutputField, ...]:
        return self.distinct.fields

    @property
    def equivalence(self) -> ProjectRowEquivalence:
        return self.distinct.equivalence


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectDistinct:
    """One authored quotient; repeated operators retain separate authority."""

    owner: ProjectDeclarationOccurrence = field(repr=False)
    clause: DistinctClause
    root: ProjectFinalOutputRoot = field(repr=False)
    fields: tuple[ProjectCompletedOutputField, ...] = field(repr=False)
    types: ProjectTypeSourceResolutionSet = field(repr=False)
    equivalence: ProjectRowEquivalence = field(init=False, repr=False)
    ordering: ProjectRelationOrdering | None = field(repr=False)
    order_proofs: tuple[object, ...] = field(repr=False)
    input_domain: ProjectCompletedRowDomain = field(repr=False)
    global_input: bool
    origin: ProjectDistinctGrainOrigin = field(init=False)
    uniqueness: ProjectDistinctFullRowUniqueness = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "equivalence",
            ProjectRowEquivalence(fields=self.fields, types=self.types),
        )
        definition = self.owner.definition
        if (
            not isinstance(definition, (TableDef, QueryDef))
            or definition.distinct_clause is not self.clause
            or type(self.equivalence) is not ProjectRowEquivalence
            or self.equivalence.fields is not self.fields
            or not self.equivalence.supported
            or len(self.fields) != len(definition.select_items)
            or any(item.owner is not self.owner for item in self.fields)
            or type(self.global_input) is not bool
        ):
            raise ValueError("DISTINCT requires exact authored visible-row authority.")
        if type(self.root) is ProjectConcreteJoinedQualify:
            base_entry = self.root.window_stage.input_aggregation.input_filter.entry
        elif type(self.root) is ProjectConcreteNoJoinReplay:
            base_entry = self.root.base_entry
        else:
            raise TypeError("DISTINCT requires an exact completed projection root.")
        _validate_projection_domain(
            self.owner, base_entry, self.root, self.input_domain
        )
        if any(
            not _completed_field_source_is_rooted(item.source, self.root)
            for item in self.fields
        ):
            raise ValueError("DISTINCT field sources must retain their exact root.")
        if (definition.order_by_clause is None) != (self.ordering is None) or (
            self.ordering is not None
            and (
                self.ordering.owner is not self.owner
                or self.ordering.clause is not definition.order_by_clause
                or any(
                    not _relation_order_source_is_rooted(item.source, self.root)
                    for item in self.ordering.items
                )
            )
        ):
            raise ValueError("DISTINCT ORDER requires exact authored/source roots.")
        _validate_distinct_projection(self.root, self.fields)
        if self.global_input != _distinct_global_input(self.root, self.input_domain):
            raise ValueError("DISTINCT requires exact input cardinality evidence.")
        _validate_distinct_order_proofs(self)
        object.__setattr__(self, "origin", ProjectDistinctGrainOrigin(witness=self))
        object.__setattr__(
            self, "uniqueness", ProjectDistinctFullRowUniqueness(distinct=self)
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectDistinctUnsupported:
    """Complete offending-field evidence with no quotient or uniqueness proof."""

    equivalence: ProjectRowEquivalence
    diagnostics: tuple[Diagnostic, ...] = field(init=False)

    def __post_init__(self) -> None:
        if self.equivalence.supported:
            raise ValueError(
                "Unsupported DISTINCT requires unsupported field evidence."
            )
        diagnostics = []
        for evidence in self.equivalence.evidence:
            if evidence.reason is None:
                continue
            selected = evidence.selected
            if not isinstance(selected, ProjectCompletedOutputField):
                raise TypeError(
                    "SELECT DISTINCT diagnostics require selected field evidence."
                )
            span = selected.item.expression.span
            diagnostics.append(
                Diagnostic(
                    code="PIE-S2339",
                    severity=Severity.ERROR,
                    message=f"DISTINCT field '{selected.output_name}' of type '{selected.field.resolved_type.name}' has unsupported row equivalence: {evidence.reason.value}.",
                    location=SourceLocation(
                        path=span.path,
                        line=span.line,
                        column=span.column,
                        end_line=span.end_line,
                        end_column=span.end_column,
                    ),
                )
            )
        object.__setattr__(self, "diagnostics", tuple(diagnostics))


class ProjectCompletedRowDomainKind(StrEnum):
    """Semantic result-row postures without a new normative grain graph."""

    PRESERVED = "preserved"
    GROUPED = "grouped"
    GLOBAL = "global"
    DISTINCT = "distinct"
    SET = "set"


type ProjectPreservedRowDomainAuthority = (
    ProjectIRProvidedIntrinsicGrain | ProjectCompletedRowDomain
)
type ProjectGroupedRowDomainBasis = (
    ProjectJoinedGroupKeyOccurrence | ProjectRelationClauseDependencyFact
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletedRowDomain:
    """One explicit final semantic row-domain posture."""

    kind: ProjectCompletedRowDomainKind
    distinct: ProjectDistinct | None = field(default=None, repr=False)
    set_origin: ProjectSetGrainOrigin | None = field(default=None, repr=False)
    preserved: ProjectPreservedRowDomainAuthority | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    grouped_basis: tuple[ProjectGroupedRowDomainBasis, ...] = field(
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectCompletedRowDomainKind:
            raise TypeError("Completed row domain requires an exact posture.")
        if type(self.grouped_basis) is not tuple or any(
            type(item)
            not in {
                ProjectJoinedGroupKeyOccurrence,
                ProjectRelationClauseDependencyFact,
            }
            for item in self.grouped_basis
        ):
            raise TypeError("Grouped row-domain basis must retain exact occurrences.")
        if self.kind is ProjectCompletedRowDomainKind.SET:
            if (
                type(self.set_origin) is not ProjectSetGrainOrigin
                or self.distinct is not None
                or self.preserved is not None
                or self.grouped_basis
            ):
                raise ValueError("Set row domain requires exact operation provenance.")
            return
        if self.set_origin is not None:
            raise ValueError("Non-set row domains cannot carry a set origin.")
        if self.distinct is not None:
            expected = (
                ProjectCompletedRowDomainKind.GLOBAL
                if self.distinct.global_input
                else ProjectCompletedRowDomainKind.DISTINCT
            )
            if (
                self.kind is not expected
                or self.preserved is not None
                or self.grouped_basis
            ):
                raise ValueError(
                    "DISTINCT row domain requires its exact quotient witness."
                )
            return
        if self.kind is ProjectCompletedRowDomainKind.DISTINCT:
            raise ValueError("DISTINCT row domain requires an authored witness.")
        if self.kind is ProjectCompletedRowDomainKind.PRESERVED:
            if (
                type(self.preserved)
                not in {
                    ProjectIRProvidedIntrinsicGrain,
                    ProjectCompletedRowDomain,
                }
                or self.grouped_basis
            ):
                raise ValueError("Preserved row domain requires one exact authority.")
        elif self.kind is ProjectCompletedRowDomainKind.GROUPED:
            if self.preserved is not None or not self.grouped_basis:
                raise ValueError(
                    "Grouped row domain requires exact group-key evidence."
                )
        elif self.preserved is not None or self.grouped_basis:
            raise ValueError("GLOBAL row domain has no inherited or grouped factors.")


class ProjectNoJoinScalarStatus(StrEnum):
    """Availability of one replayed no-JOIN scalar expression."""

    CONCRETE = "concrete"
    TYPE_NON_CONCRETE = "type_non_concrete"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNoJoinScalarExpression:
    """One no-JOIN expression analyzed once through the existing scalar kernel."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_schema: ProjectRowSchema = field(
        repr=False,
        compare=False,
        hash=False,
    )
    let_scope: ProjectRelationLetScopeFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: Expression = field(repr=False, compare=False, hash=False)
    status: ProjectNoJoinScalarStatus
    value_type: ValueType | None = None
    value_types: Mapping[Expression, ValueType] = field(
        default_factory=dict,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.owner) is not ProjectDeclarationOccurrence
            or type(self.input_schema) is not ProjectRowSchema
            or type(self.let_scope) is not (ProjectRelationLetScopeFacts)
        ):
            raise TypeError("No-JOIN scalar analysis requires exact replay roots.")
        if (
            not isinstance(self.expression, Expression)
            or type(self.status) is not ProjectNoJoinScalarStatus
        ):
            raise TypeError("No-JOIN scalar analysis requires exact expression state.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
        ):
            raise TypeError("No-JOIN scalar diagnostics must be exact.")
        value_types = MappingProxyType(dict(self.value_types))
        object.__setattr__(self, "value_types", value_types)
        if self.status is ProjectNoJoinScalarStatus.CONCRETE:
            valid = (
                type(self.value_type) is ValueType
                and self.value_type.kind is ValueTypeKind.KNOWN
                and value_types.get(self.expression) is self.value_type
                and not any(
                    diagnostic.severity is Severity.ERROR
                    for diagnostic in self.diagnostics
                )
            )
        else:
            valid = type(self.value_type) is ValueType and (
                self.value_type.kind is ValueTypeKind.UNKNOWN
                or any(
                    diagnostic.severity is Severity.ERROR
                    for diagnostic in self.diagnostics
                )
            )
        if not valid:
            raise ValueError("No-JOIN scalar status lost its causal evidence.")


class ProjectNoJoinWhereKind(StrEnum):
    ABSENT = "absent"
    AUTHORED_WHERE = "authored_where"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteNoJoinWhere:
    """One absent or known-Bool no-JOIN WHERE replay."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    kind: ProjectNoJoinWhereKind
    expression_analysis: ProjectNoJoinScalarExpression | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = ()
    retention_effects: tuple[ProjectJoinedRowRetentionEffect, ...] = ()

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        if type(self.kind) is not ProjectNoJoinWhereKind:
            raise TypeError("No-JOIN WHERE requires an exact kind.")
        if self.kind is ProjectNoJoinWhereKind.ABSENT:
            if definition.where_clause is not None or any(
                (
                    self.expression_analysis is not None,
                    self.diagnostics,
                    self.retention_effects,
                )
            ):
                raise ValueError("Absent no-JOIN WHERE cannot manufacture evidence.")
            return
        analysis = self.expression_analysis
        if (
            definition.where_clause is None
            or type(analysis) is not ProjectNoJoinScalarExpression
            or analysis.expression is not definition.where_clause.expression
            or analysis.status is not ProjectNoJoinScalarStatus.CONCRETE
            or analysis.value_type is None
            or analysis.value_type.resolved_type.name != "Bool"
            or self.diagnostics != analysis.diagnostics
            or any(
                diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
            )
            or self.retention_effects is not _SQL_ROW_RETENTION_EFFECTS
        ):
            raise ValueError("Authored no-JOIN WHERE requires exact Bool authority.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNoJoinGroupedOutput:
    """One exact current helper-owned grouped/global selected result."""

    readiness: ProjectAggregateGroupedClauseReadiness = field(
        repr=False,
        compare=False,
        hash=False,
    )
    select_fact: ProjectModuleSelectFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    field: ProjectRowField

    def __post_init__(self) -> None:
        schema = self.readiness.finalization.state.schema
        if (
            type(self.readiness) is not ProjectAggregateGroupedClauseReadiness
            or type(self.select_fact) is not ProjectModuleSelectFact
            or type(self.field) is not ProjectRowField
            or schema is None
            or self.select_fact.output_name is None
            or schema.fields.get(self.select_fact.output_name) is not self.field
            or self.field.result_role
            not in {
                ProjectRowResultRole.GROUP_KEY,
                ProjectRowResultRole.AGGREGATE_RESULT,
            }
        ):
            raise ValueError("No-JOIN grouped output requires exact helper authority.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNoJoinHiddenWindowComputation:
    """One occurrence-neutral hidden inline window attempt."""

    scope: WindowInputScope = field(repr=False, compare=False, hash=False)
    expression: WindowExpr = field(repr=False, compare=False, hash=False)
    analysis: WindowComputationAnalysis | WindowComputationUnsupported | None
    value_types: Mapping[Expression, ValueType] = field(
        default_factory=dict,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if type(self.scope) is not WindowInputScope or type(self.expression) is not (
            WindowExpr
        ):
            raise TypeError("Hidden replay window requires exact scope and AST.")
        if type(self.analysis) not in {
            WindowComputationAnalysis,
            WindowComputationUnsupported,
            type(None),
        }:
            raise TypeError("Hidden replay window requires a closed kernel result.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
        ):
            raise TypeError("Hidden replay diagnostics must be exact.")
        object.__setattr__(
            self,
            "value_types",
            MappingProxyType(dict(self.value_types)),
        )
        if self.expression.use_kind is not WindowUseKind.INLINE:
            if self.analysis is not None or self.value_types or self.diagnostics:
                raise ValueError("Hidden named window rejection cannot invent a site.")
        elif self.analysis is None:
            raise ValueError("Hidden inline window requires a kernel result.")
        elif type(self.analysis) is WindowComputationAnalysis and (
            self.analysis.expression is not self.expression
            or self.analysis.result.value_type is None
        ):
            raise ValueError("Concrete hidden window lost its exact result type.")

    @property
    def value_type(self) -> ValueType | None:
        if type(self.analysis) is not WindowComputationAnalysis:
            return None
        return self.analysis.result.value_type


type ProjectNoJoinQualifyCandidate = WindowInputBinding | ProjectModuleWindowOutputFact


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNoJoinQualifyReferenceResolution:
    """One no-JOIN QUALIFY reference and its complete cross-domain bucket."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    scope: WindowInputScope = field(repr=False, compare=False, hash=False)
    selected_windows: tuple[ProjectModuleWindowOutputFact, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: NameExpr | DottedNameExpr = field(
        repr=False,
        compare=False,
        hash=False,
    )
    candidates: tuple[ProjectNoJoinQualifyCandidate, ...]
    status: ProjectModuleCandidateBucketStatus = field(init=False)
    target: ProjectNoJoinQualifyCandidate | None = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.owner) is not ProjectDeclarationOccurrence
            or type(self.scope) is not WindowInputScope
            or type(self.expression)
            not in {
                NameExpr,
                DottedNameExpr,
            }
        ):
            raise TypeError("No-JOIN QUALIFY resolution requires exact roots.")
        if type(self.selected_windows) is not tuple or any(
            type(item) is not ProjectModuleWindowOutputFact
            for item in self.selected_windows
        ):
            raise TypeError("Selected replay windows must be exact occurrences.")
        if self.candidates != _no_join_qualify_candidates(
            self.owner,
            self.scope,
            self.selected_windows,
            self.expression,
        ):
            raise ValueError("No-JOIN QUALIFY candidates must be complete and ordered.")
        status = (
            ProjectModuleCandidateBucketStatus.ABSENT
            if not self.candidates
            else (
                ProjectModuleCandidateBucketStatus.CONCRETE
                if len(self.candidates) == 1
                else ProjectModuleCandidateBucketStatus.AMBIGUOUS
            )
        )
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "target",
            self.candidates[0] if len(self.candidates) == 1 else None,
        )


class ProjectNoJoinQualifyKind(StrEnum):
    ABSENT = "absent"
    AUTHORED_QUALIFY = "authored_qualify"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNoJoinQualify:
    """One replayed no-JOIN QUALIFY result delegated to the shared kernel."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    kind: ProjectNoJoinQualifyKind
    mode: ProjectJoinedAggregationMode
    scope: WindowInputScope = field(repr=False, compare=False, hash=False)
    selected_windows: tuple[ProjectModuleWindowOutputFact, ...]
    clause: QualifyClause | None = field(default=None, repr=False, compare=False)
    references: tuple[ProjectNoJoinQualifyReferenceResolution, ...] = ()
    hidden_attempts: tuple[ProjectNoJoinHiddenWindowComputation, ...] = ()
    predicate: _ProjectQualifyPredicateAnalysis | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        if (
            type(self.kind) is not ProjectNoJoinQualifyKind
            or type(self.mode) is not ProjectJoinedAggregationMode
            or type(self.scope) is not WindowInputScope
        ):
            raise TypeError("No-JOIN QUALIFY requires exact replay authority.")
        if type(self.selected_windows) is not tuple or any(
            type(item) is not ProjectModuleWindowOutputFact
            for item in self.selected_windows
        ):
            raise TypeError("No-JOIN QUALIFY windows must be exact.")
        expected_scope_kind = (
            WindowInputScopeKind.ROW
            if self.mode is ProjectJoinedAggregationMode.ABSENT
            else WindowInputScopeKind.GROUPED_RESULT
        )
        if self.scope.kind is not expected_scope_kind or (
            self.mode is ProjectJoinedAggregationMode.GLOBAL and self.selected_windows
        ):
            raise ValueError("No-JOIN QUALIFY scope must match its exact stage mode.")
        if self.kind is ProjectNoJoinQualifyKind.ABSENT:
            if any(
                (
                    definition.qualify_clause is not None,
                    self.clause is not None,
                    self.references,
                    self.hidden_attempts,
                    self.predicate is not None,
                )
            ):
                raise ValueError("Absent no-JOIN QUALIFY cannot manufacture evidence.")
            return
        if (
            type(self.clause) is not QualifyClause
            or self.clause is not definition.qualify_clause
            or type(self.predicate) is not _ProjectQualifyPredicateAnalysis
            or self.predicate.clause is not self.clause
        ):
            raise ValueError("Authored no-JOIN QUALIFY requires the shared kernel.")
        operands = _qualify_operands(self.clause.expression)
        reference_operands = tuple(
            operand
            for operand in operands
            if type(operand) in {NameExpr, DottedNameExpr}
        )
        hidden_operands = tuple(
            operand for operand in operands if type(operand) is WindowExpr
        )
        if len(self.references) != len(reference_operands) or any(
            resolution.expression is not expression
            or resolution.owner is not self.owner
            or resolution.scope is not self.scope
            or resolution.selected_windows is not self.selected_windows
            for resolution, expression in zip(
                self.references,
                reference_operands,
                strict=True,
            )
        ):
            raise ValueError("No-JOIN QUALIFY references lost source order.")
        if len(self.hidden_attempts) != len(hidden_operands) or any(
            attempt.expression is not expression or attempt.scope is not self.scope
            for attempt, expression in zip(
                self.hidden_attempts,
                hidden_operands,
                strict=True,
            )
        ):
            raise ValueError("No-JOIN hidden windows lost source order.")
        _validate_no_join_qualify_predicate(self)

    @property
    def concrete(self) -> bool:
        return self.predicate is None or self.predicate.reason is None


type ProjectCompletedOutputSource = (
    ProjectConcreteJoinedNamespaceExpression
    | ProjectJoinedStageOutputOccurrence
    | ProjectSelectedWindowResultBinding
    | ProjectNoJoinScalarExpression
    | ProjectNoJoinGroupedOutput
    | ProjectModuleWindowOutputFact
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletedOutputField:
    """One final selected occurrence with canonical module field identity."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    select_fact: ProjectModuleSelectFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    selected_output_ordinal: int
    item: SelectItem = field(repr=False, compare=False, hash=False)
    output_name: str
    identity: ProjectModuleRowFieldIdentity
    source: ProjectCompletedOutputSource = field(
        repr=False,
        compare=False,
        hash=False,
    )
    type_sources: tuple[ProjectRowEquivalenceField, ...] = field(default=(), repr=False)
    field: ProjectRowField
    result_role: ProjectRowResultRole

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        canonical_owner = _declaration_identity(self.owner)
        if (
            type(self.select_fact) is not ProjectModuleSelectFact
            or self.select_fact.owner is not self.owner
            or type(self.selected_output_ordinal) is not int
            or self.selected_output_ordinal < 0
            or self.selected_output_ordinal >= len(definition.select_items)
            or definition.select_items[self.selected_output_ordinal] is not self.item
            or self.select_fact.selected_output_ordinal != self.selected_output_ordinal
            or self.select_fact.item is not self.item
            or self.select_fact.output_name != self.output_name
            or type(self.output_name) is not str
            or not self.output_name
        ):
            raise ValueError(
                "Completed field requires exact selected occurrence authority."
            )
        if (
            type(self.identity) is not ProjectModuleRowFieldIdentity
            or self.identity.owner != canonical_owner
            or self.identity.kind is not ProjectModuleRowFieldKind.RELATION_OUTPUT
            or self.identity.field_position != self.selected_output_ordinal
            or self.identity.name != self.output_name
            or type(self.field) is not ProjectRowField
            or self.field.name != self.output_name
            or type(self.result_role) is not ProjectRowResultRole
            or self.field.result_role is not self.result_role
        ):
            raise ValueError(
                "Completed field requires canonical identity and row facts."
            )
        if type(self.source) not in {
            ProjectConcreteJoinedNamespaceExpression,
            ProjectJoinedStageOutputOccurrence,
            ProjectSelectedWindowResultBinding,
            ProjectNoJoinScalarExpression,
            ProjectNoJoinGroupedOutput,
            ProjectModuleWindowOutputFact,
        }:
            raise TypeError(
                "Completed field source must be one closed exact authority."
            )
        _validate_completed_field_source(self)
        if type(self.type_sources) is not tuple or any(
            type(source) is not ProjectRowEquivalenceField
            for source in self.type_sources
        ):
            raise TypeError("SELECT field type images require exact parent evidence.")


class ProjectRelationOrderDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


type ProjectRelationOrderSource = (
    ProjectConcreteJoinedNamespaceExpression
    | ProjectJoinedWindowInputBinding
    | ProjectSelectedWindowResultBinding
    | ProjectNoJoinScalarExpression
    | ProjectModuleClauseDependencyFact
    | ProjectModuleWindowOutputFact
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectRelationOrderItem:
    """One source-ordered relation key with exact effective direction."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    clause: OrderByClause = field(repr=False, compare=False, hash=False)
    source_ordinal: int
    item: OrderItem = field(repr=False, compare=False, hash=False)
    expression: Expression = field(repr=False, compare=False, hash=False)
    direction: ProjectRelationOrderDirection
    value_type: ValueType
    source: ProjectRelationOrderSource = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        if (
            definition.order_by_clause is not self.clause
            or type(self.source_ordinal) is not int
            or self.source_ordinal < 0
            or self.source_ordinal >= len(self.clause.items)
            or self.clause.items[self.source_ordinal] is not self.item
            or self.item.expression is not self.expression
            or type(self.direction) is not ProjectRelationOrderDirection
            or self.direction
            is not ProjectRelationOrderDirection(
                "asc" if self.item.direction is None else self.item.direction
            )
            or type(self.value_type) is not ValueType
            or self.value_type.kind is not ValueTypeKind.KNOWN
        ):
            raise ValueError("Relation order item lost exact source/type authority.")
        if type(self.source) not in {
            ProjectConcreteJoinedNamespaceExpression,
            ProjectJoinedWindowInputBinding,
            ProjectSelectedWindowResultBinding,
            ProjectNoJoinScalarExpression,
            ProjectModuleClauseDependencyFact,
            ProjectModuleWindowOutputFact,
        }:
            raise TypeError(
                "Relation order source must be an exact admitted authority."
            )
        _validate_relation_order_source(self)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectRelationOrdering:
    """The first final relation-order authority, distinct from window ordering."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    clause: OrderByClause = field(repr=False, compare=False, hash=False)
    items: tuple[ProjectRelationOrderItem, ...]

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        if (
            definition.order_by_clause is not self.clause
            or type(self.items) is not tuple
            or len(self.items) != len(self.clause.items)
            or any(
                result.owner is not self.owner
                or result.clause is not self.clause
                or result.source_ordinal != ordinal
                or result.item is not item
                for ordinal, (result, item) in enumerate(
                    zip(self.items, self.clause.items, strict=True)
                )
            )
        ):
            raise ValueError("Relation ordering must retain complete source order.")


class ProjectRelationOrderingNonConcreteReason(StrEnum):
    EXPRESSION_NON_CONCRETE = "expression_non_concrete"
    GROUPED_ORDER_UNSUPPORTED = "grouped_order_unsupported"
    GLOBAL_ORDER_UNSUPPORTED = "global_order_unsupported"
    DISTINCT_ORDER_NOT_DETERMINED = "distinct_order_not_determined"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteRelationOrdering:
    """One all-or-none relation ORDER blocker."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    clause: OrderByClause = field(repr=False, compare=False, hash=False)
    reason: ProjectRelationOrderingNonConcreteReason
    blocker: object = field(repr=False, compare=False, hash=False)
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        if (
            _derived_definition(self.owner).order_by_clause is not self.clause
            or type(self.reason) is not ProjectRelationOrderingNonConcreteReason
        ):
            raise ValueError("Relation ORDER terminal requires exact authored roots.")
        if type(self.diagnostics) is not tuple or any(
            type(item) is not Diagnostic for item in self.diagnostics
        ):
            raise TypeError("Relation ORDER diagnostics must be exact.")


type ProjectRelationOrderingResult = (
    ProjectRelationOrdering | ProjectNonConcreteRelationOrdering | None
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectRelationLimit:
    """One exact valid static limit and row-count upper bound."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    clause: LimitClause = field(repr=False, compare=False, hash=False)
    literal: LiteralExpr = field(repr=False, compare=False, hash=False)
    value: int
    row_count_upper_bound: int = field(init=False)

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        if (
            definition.limit_clause is not self.clause
            or self.clause.expression is not self.literal
            or type(self.literal.value) is not int
            or type(self.value) is not int
            or self.value != self.literal.value
            or not 0 <= self.value <= MAX_RELATION_LIMIT
        ):
            raise ValueError("Relation limit must retain one valid exact literal.")
        object.__setattr__(self, "row_count_upper_bound", self.value)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteRelationLimit:
    """One invalid authored limit with only PIE-S2307 authority."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    clause: LimitClause = field(repr=False, compare=False, hash=False)
    diagnostics: tuple[Diagnostic, ...]

    def __post_init__(self) -> None:
        if _derived_definition(self.owner).limit_clause is not self.clause or (
            len(self.diagnostics) != 1
            or self.diagnostics[0].code != "PIE-S2307"
            or self.diagnostics[0].severity is not Severity.ERROR
        ):
            raise ValueError("Invalid relation limit requires exact PIE-S2307 only.")


type ProjectRelationLimitResult = (
    ProjectRelationLimit | ProjectNonConcreteRelationLimit | None
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNoJoinReplayRoot:
    """One owner-local no-JOIN replay identity retained by the overlay."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    base_entry: ProjectEffectiveOutputEntry = field(
        repr=False,
        compare=False,
        hash=False,
    )
    upstream_entry: ProjectConcreteEffectiveOutputEntry = field(
        repr=False,
        compare=False,
        hash=False,
    )
    semantic_facts: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    blocker: object | None = field(default=None, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        resolution = self.semantic_facts.resolution
        if definition.join_clauses:
            raise ValueError("No-JOIN replay root cannot reopen authored JOIN.")
        if (
            type(self.base_entry)
            not in {ProjectExistingEffectiveOutput, ProjectEffectiveOutputTerminal}
            or self.base_entry.owner is not self.owner
            or type(self.upstream_entry)
            not in {
                ProjectExistingEffectiveOutput,
                ProjectCompletedEffectiveOutput,
                ProjectCompletedSetOutput,
            }
            or type(self.semantic_facts) is not ProjectModuleRelationSemanticFacts
            or self.semantic_facts.owner is not self.owner
            or resolution is None
            or len(self.base_entry.dependencies) != 1
            or self.base_entry.dependencies[0].evidence is not resolution
            or self.base_entry.dependencies[0].target is not self.upstream_entry.owner
        ):
            raise ValueError("No-JOIN replay root requires exact retained authority.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteNoJoinReplay:
    """Exact pre-final semantic authority for one replayed no-JOIN relation."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    replay_root: ProjectNoJoinReplayRoot = field(
        repr=False,
        compare=False,
        hash=False,
    )
    base_entry: ProjectEffectiveOutputEntry = field(
        repr=False,
        compare=False,
        hash=False,
    )
    upstream_entry: ProjectConcreteEffectiveOutputEntry = field(
        repr=False,
        compare=False,
        hash=False,
    )
    semantic_facts: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_schema: ProjectRowSchema = field(
        repr=False,
        compare=False,
        hash=False,
    )
    let_scope: ProjectRelationLetScopeFacts
    where: ProjectConcreteNoJoinWhere
    mode: ProjectJoinedAggregationMode
    aggregate_readiness: ProjectAggregateGroupedClauseReadiness | None
    base_state: ProjectRelationRowSchemaState
    window_state: ProjectRelationRowSchemaState
    window_outputs: tuple[ProjectModuleWindowOutputFact, ...]
    window_scope: WindowInputScope
    clause_dependencies: tuple[ProjectModuleClauseDependencyFact, ...]
    qualify: ProjectNoJoinQualify

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        if (
            type(self.replay_root) is not ProjectNoJoinReplayRoot
            or self.replay_root.owner is not self.owner
            or self.replay_root.base_entry is not self.base_entry
            or self.replay_root.upstream_entry is not self.upstream_entry
            or self.replay_root.semantic_facts is not self.semantic_facts
            or self.replay_root.blocker is not None
            or _entry_schema(self.upstream_entry) is not self.input_schema
            or type(self.input_schema) is not ProjectRowSchema
            or self.input_schema.is_unknown
            or type(self.let_scope) is not ProjectRelationLetScopeFacts
            or self.let_scope.status
            not in {
                ProjectLetScopeFactsStatus.ABSENT,
                ProjectLetScopeFactsStatus.CONCRETE,
            }
            or type(self.where) is not ProjectConcreteNoJoinWhere
            or self.where.owner is not self.owner
            or type(self.mode) is not ProjectJoinedAggregationMode
            or type(self.base_state) is not ProjectRelationRowSchemaState
            or self.base_state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or type(self.window_state) is not ProjectRelationRowSchemaState
            or self.window_state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or type(self.window_scope) is not WindowInputScope
            or type(self.qualify) is not ProjectNoJoinQualify
            or self.qualify.owner is not self.owner
            or self.qualify.mode is not self.mode
            or self.qualify.scope is not self.window_scope
            or self.qualify.selected_windows is not self.window_outputs
            or not self.qualify.concrete
        ):
            raise ValueError("Concrete no-JOIN replay requires every closed stage.")
        expected_windows = tuple(
            item
            for item in definition.select_items
            if type(item.expression) is WindowExpr
        )
        if len(self.window_outputs) != len(expected_windows) or any(
            output.owner is not self.owner
            or output.item is not item
            or output.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            for output, item in zip(
                self.window_outputs,
                expected_windows,
                strict=True,
            )
        ):
            raise ValueError("No-JOIN replay windows must be complete and concrete.")
        if type(self.clause_dependencies) is not tuple or any(
            type(item) is not ProjectModuleClauseDependencyFact
            or item.owner is not self.owner
            for item in self.clause_dependencies
        ):
            raise ValueError("No-JOIN replay clause facts require the exact owner.")
        if self.mode is ProjectJoinedAggregationMode.ABSENT:
            if self.aggregate_readiness is not None:
                raise ValueError("Absent aggregation cannot retain grouped readiness.")
        elif (
            type(self.aggregate_readiness) is not ProjectAggregateGroupedClauseReadiness
            or self.aggregate_readiness.definition is not definition
            or self.aggregate_readiness.finalization.state is not self.base_state
        ):
            raise ValueError("Aggregate replay requires exact current readiness.")


type ProjectFinalOutputRoot = ProjectConcreteJoinedQualify | ProjectConcreteNoJoinReplay


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletedEffectiveOutput:
    """One all-or-none Phase-63 semantic effective output, with no Project IR."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    base_entry: ProjectEffectiveOutputEntry = field(
        repr=False,
        compare=False,
        hash=False,
    )
    root: ProjectFinalOutputRoot = field(repr=False, compare=False, hash=False)
    fields: tuple[ProjectCompletedOutputField, ...]
    schema: ProjectRowSchema
    row_domain: ProjectCompletedRowDomain
    ordering: ProjectRelationOrdering | None
    limit: ProjectRelationLimit | None
    dependencies: tuple[ProjectCompletionDependency, ...]

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        if (
            type(self.base_entry)
            not in {ProjectExistingEffectiveOutput, ProjectEffectiveOutputTerminal}
            or self.base_entry.owner is not self.owner
            or type(self.root)
            not in {ProjectConcreteJoinedQualify, ProjectConcreteNoJoinReplay}
            or type(self.schema) is not ProjectRowSchema
            or self.schema.is_unknown
            or type(self.row_domain) is not ProjectCompletedRowDomain
            or self.dependencies is not self.base_entry.dependencies
        ):
            raise ValueError(
                "Completed effective output requires exact base authority."
            )
        if (
            type(self.fields) is not tuple
            or len(self.fields) != len(definition.select_items)
            or any(
                output.owner is not self.owner
                or output.selected_output_ordinal != ordinal
                or output.item is not item
                for ordinal, (output, item) in enumerate(
                    zip(self.fields, definition.select_items, strict=True)
                )
            )
        ):
            raise ValueError("Completed effective output must cover every select once.")
        if tuple(self.schema.fields) != tuple(
            output.output_name for output in self.fields
        ) or any(
            self.schema.fields[output.output_name] is not output.field
            for output in self.fields
        ):
            raise ValueError("Final schema must project the exact ordered field tuple.")
        if (definition.order_by_clause is None) is not (self.ordering is None) or (
            self.ordering is not None and self.ordering.owner is not self.owner
        ):
            raise ValueError("Final relation ordering must match exact authorship.")
        if (definition.limit_clause is None) is not (self.limit is None) or (
            self.limit is not None and self.limit.owner is not self.owner
        ):
            raise ValueError("Final relation limit must match exact authorship.")
        _validate_completed_output_root(self)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletedSetOutputField:
    """A canonical non-SELECT field with complete positional operand provenance."""

    root: ProjectSetOperation = field(repr=False)
    source: ProjectSetColumn = field(repr=False)
    output_position: int
    owner: ProjectDeclarationOccurrence = field(init=False)
    output_name: str = field(init=False)
    identity: ProjectModuleRowFieldIdentity = field(init=False)
    field: ProjectRowField = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.output_position) is not int
            or not 0 <= self.output_position < len(self.root.columns)
            or self.root.columns[self.output_position] is not self.source
        ):
            raise ValueError("Set field requires its exact operation column.")
        first = self.source.inputs[0].selected
        if not isinstance(first, ProjectRowEquivalenceInput):
            raise TypeError("Set label requires the first completed operand field.")
        object.__setattr__(self, "owner", self.root.owner)
        object.__setattr__(self, "output_name", first.identity.name)
        object.__setattr__(
            self,
            "identity",
            _completed_field_identity(
                self.owner, self.output_position, self.output_name
            ),
        )
        object.__setattr__(
            self,
            "field",
            ProjectRowField(
                name=self.output_name,
                resolved_type=self.source.resolved_type,
                nullability=self.source.nullability,
                result_role=ProjectRowResultRole.ORDINARY_ROW_VALUE,
            ),
        )

    @property
    def type_sources(self) -> tuple[ProjectRowEquivalenceField, ...]:
        return self.source.inputs


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSetFullRowUniqueness:
    output: ProjectCompletedSetOutput = field(repr=False)
    nulls_equal: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        if (
            not self.output.root.full_row_unique
            or not self.output.root.requires_equivalence
        ):
            raise ValueError("Set uniqueness requires an exact DISTINCT set operator.")

    @property
    def fields(self) -> tuple[ProjectCompletedSetOutputField, ...]:
        return self.output.fields


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletedSetOutput:
    """The non-SELECT variant in the canonical effective-output ledger."""

    root: ProjectSetOperation = field(repr=False)
    fields: tuple[ProjectCompletedSetOutputField, ...] = field(init=False)
    schema: ProjectRowSchema = field(init=False)
    row_domain: ProjectCompletedRowDomain = field(init=False)
    uniqueness: ProjectSetFullRowUniqueness | None = field(init=False)
    ordering: None = field(default=None, init=False)
    limit: None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if type(self.root) is not ProjectSetOperation:
            raise TypeError(
                "Completed set output requires its exact semantic operation."
            )
        fields = tuple(
            ProjectCompletedSetOutputField(
                root=self.root, source=column, output_position=i
            )
            for i, column in enumerate(self.root.columns)
        )
        object.__setattr__(self, "fields", fields)
        object.__setattr__(
            self,
            "schema",
            ProjectRowSchema(fields={f.output_name: f.field for f in fields}),
        )
        origin = ProjectSetGrainOrigin(
            witness=self.root,
            input_domains=tuple(
                _entry_row_domain(use.authority.entry) for use in self.root.uses
            ),
        )
        object.__setattr__(
            self,
            "row_domain",
            ProjectCompletedRowDomain(
                kind=ProjectCompletedRowDomainKind.SET, set_origin=origin
            ),
        )
        object.__setattr__(
            self,
            "uniqueness",
            ProjectSetFullRowUniqueness(output=self)
            if self.root.full_row_unique
            else None,
        )
        self.validate()

    @property
    def owner(self) -> ProjectDeclarationOccurrence:
        return self.root.owner

    @property
    def base_entry(self) -> ProjectEffectiveOutputEntry:
        return self.root.scope.base_entry

    @property
    def dependencies(self) -> tuple[ProjectCompletionDependency, ...]:
        return self.base_entry.dependencies

    def validate(self) -> None:
        if len(self.fields) != len(self.root.columns) or any(
            f.root is not self.root
            or f.source is not column
            or f.output_position != i
            or f.owner is not self.owner
            or self.schema.fields.get(f.output_name) is not f.field
            or f.field.resolved_type is not column.resolved_type
            or f.field.nullability is not column.nullability
            or f.field.result_role is not ProjectRowResultRole.ORDINARY_ROW_VALUE
            for i, (f, column) in enumerate(
                zip(self.fields, self.root.columns, strict=True)
            )
        ):
            raise ValueError(
                "Completed set output lost exact source/field/type mappings."
            )
        if tuple(self.schema.fields) != tuple(f.output_name for f in self.fields):
            raise ValueError(
                "Set output labels must retain first-operand positional order."
            )
        origin = self.row_domain.set_origin
        if (
            origin is None
            or origin.witness is not self.root
            or not _same_objects(
                origin.input_domains,
                tuple(_entry_row_domain(use.authority.entry) for use in self.root.uses),
            )
        ):
            raise ValueError("Set output lost its exact row-domain provenance.")
        if self.uniqueness is not None and self.uniqueness.output is not self:
            raise ValueError("Set uniqueness cannot be grafted from another output.")


class ProjectEffectiveOutputCompletionTerminalReason(StrEnum):
    CURRENT_JOIN_CONDITION_NON_CONCRETE = "current_join_condition_non_concrete"
    CURRENT_JOIN_INPUT_NON_CONCRETE = "current_join_input_non_concrete"
    CURRENT_JOIN_TAIL_NON_CONCRETE = "current_join_tail_non_concrete"
    JOINED_QUALIFY_NON_CONCRETE = "joined_qualify_non_concrete"
    UPSTREAM_EFFECTIVE_OUTPUT_NON_CONCRETE = "upstream_effective_output_non_concrete"
    LET_NON_CONCRETE = "let_non_concrete"
    WHERE_NON_CONCRETE = "where_non_concrete"
    AGGREGATION_NON_CONCRETE = "aggregation_non_concrete"
    WINDOW_NON_CONCRETE = "window_non_concrete"
    QUALIFY_NON_CONCRETE = "qualify_non_concrete"
    PROJECTION_NON_CONCRETE = "projection_non_concrete"
    ORDER_NON_CONCRETE = "order_non_concrete"
    LIMIT_NON_CONCRETE = "limit_non_concrete"
    DISTINCT_NON_CONCRETE = "distinct_non_concrete"
    SET_NON_CONCRETE = "set_non_concrete"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectEffectiveOutputCompletionTerminal:
    """One typed new causal terminal with no partial final output."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    base_entry: ProjectEffectiveOutputEntry = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectEffectiveOutputCompletionTerminalReason
    blocker: object = field(repr=False, compare=False, hash=False)
    dependencies: tuple[ProjectCompletionDependency, ...]
    joined_qualify: ProjectJoinedQualifyResult | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    replay_root: ProjectNoJoinReplayRoot | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    upstream_entry: ProjectEffectiveOutputCompletionEntry | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = ()
    current_region: ProjectCurrentJoinRegion | None = field(default=None, repr=False)
    current_inputs: ProjectCurrentJoinInputScope | None = field(
        default=None, repr=False
    )
    output: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if (
            type(self.base_entry)
            not in {ProjectExistingEffectiveOutput, ProjectEffectiveOutputTerminal}
            or self.base_entry.owner is not self.owner
            or type(self.reason) is not ProjectEffectiveOutputCompletionTerminalReason
            or self.dependencies is not self.base_entry.dependencies
        ):
            raise ValueError("Completion terminal requires exact base authority.")
        if type(self.diagnostics) is not tuple or any(
            type(item) is not Diagnostic for item in self.diagnostics
        ):
            raise TypeError("Completion terminal diagnostics must be exact.")
        if (
            self.reason
            is ProjectEffectiveOutputCompletionTerminalReason.SET_NON_CONCRETE
        ):
            if (
                not isinstance(self.owner.definition, SetRelationDef)
                or type(self.blocker) is not ProjectSetFailure
                or self.blocker.scope.base_entry is not self.base_entry
                or self.diagnostics is not self.blocker.diagnostics
                or any(
                    (
                        self.joined_qualify is not None,
                        self.replay_root is not None,
                        self.upstream_entry is not None,
                        self.current_region is not None,
                        self.current_inputs is not None,
                    )
                )
            ):
                raise ValueError(
                    "Set terminal requires its exact failure scope and no partial output."
                )
            return
        if self.current_region is not None:
            _validate_current_terminal(self)
            return
        if self.current_inputs is not None:
            if (
                self.current_inputs.ledger.owner is not self.owner
                or self.joined_qualify is not None
                or self.replay_root is not None
                or self.upstream_entry is not None
            ):
                raise ValueError(
                    "Current input terminal requires its exact complete blocker scope."
                )
            if (
                self.reason
                is ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_INPUT_NON_CONCRETE
            ):
                valid = (
                    type(self.blocker) is ProjectCurrentJoinInputFailure
                    and self.blocker.scope is self.current_inputs
                )
            else:
                valid = (
                    self.reason
                    is ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_CONDITION_NON_CONCRETE
                    and type(self.blocker) is tuple
                    and bool(self.blocker)
                    and all(
                        type(item) is ProjectJoinCondition
                        and not item.ready
                        and item.ledger is self.current_inputs.ledger
                        for item in self.blocker
                    )
                )
            if not valid:
                raise ValueError(
                    "Current terminal must retain its exact input/condition failure."
                )
            return
        joined_tail = type(self.base_entry) is ProjectEffectiveOutputTerminal and (
            self.base_entry.reason
            is ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
        )
        if joined_tail:
            result = self.joined_qualify
            if type(result) not in {
                ProjectConcreteJoinedQualify,
                ProjectNonConcreteJoinedQualify,
            }:
                raise ValueError(
                    "Joined completion terminal requires an exact Slice-11 result."
                )
            result = cast(ProjectJoinedQualifyResult, result)
            if (
                _joined_result_owner(result) is not self.owner
                or self.replay_root is not None
                or self.upstream_entry is not None
            ):
                raise ValueError(
                    "Joined completion terminal requires an exact Slice-11 result."
                )
            if self.reason is (
                ProjectEffectiveOutputCompletionTerminalReason.JOINED_QUALIFY_NON_CONCRETE
            ):
                if (
                    type(result) is not ProjectNonConcreteJoinedQualify
                    or self.blocker is not result
                ):
                    raise ValueError(
                        "Joined terminal requires its exact Slice-11 blocker."
                    )
            elif type(
                result
            ) is not ProjectConcreteJoinedQualify or self.reason not in {
                ProjectEffectiveOutputCompletionTerminalReason.DISTINCT_NON_CONCRETE,
                ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE,
                ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE,
                ProjectEffectiveOutputCompletionTerminalReason.LIMIT_NON_CONCRETE,
            }:
                raise ValueError(
                    "Joined terminal reason requires exact concrete Slice-11 authority."
                )
            return
        upstream = self.upstream_entry
        if (
            self.joined_qualify is not None
            or len(self.dependencies) != 1
            or type(upstream)
            not in {
                ProjectExistingEffectiveOutput,
                ProjectEffectiveOutputTerminal,
                ProjectCompletedEffectiveOutput,
                ProjectCompletedSetOutput,
                ProjectEffectiveOutputCompletionTerminal,
            }
        ):
            raise ValueError("No-JOIN terminal requires exact upstream authority.")
        assert upstream is not None
        if self.dependencies[0].target is not upstream.owner:
            raise ValueError("No-JOIN terminal lost its exact upstream dependency.")
        if self.reason is (
            ProjectEffectiveOutputCompletionTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_NON_CONCRETE
        ):
            if (
                self.replay_root is not None
                or type(upstream)
                not in {
                    ProjectEffectiveOutputTerminal,
                    ProjectEffectiveOutputCompletionTerminal,
                }
                or self.blocker is not upstream
            ):
                raise ValueError("Upstream terminal requires exact earlier evidence.")
            return
        if type(upstream) not in {
            ProjectExistingEffectiveOutput,
            ProjectCompletedEffectiveOutput,
            ProjectCompletedSetOutput,
        } or self.reason is (
            ProjectEffectiveOutputCompletionTerminalReason.JOINED_QUALIFY_NON_CONCRETE
        ):
            raise ValueError(
                "Local no-JOIN blocker requires concrete upstream evidence."
            )
        root = self.replay_root
        if (
            type(root) is not ProjectNoJoinReplayRoot
            or root.owner is not self.owner
            or root.base_entry is not self.base_entry
            or root.upstream_entry is not upstream
            or root.blocker is not self.blocker
        ):
            raise ValueError(
                "No-JOIN terminal requires its exact local replay blocker."
            )


type ProjectConcreteEffectiveOutputEntry = (
    ProjectExistingEffectiveOutput
    | ProjectCompletedEffectiveOutput
    | ProjectCompletedSetOutput
)
type ProjectEffectiveOutputCompletionEntry = (
    ProjectExistingEffectiveOutput
    | ProjectEffectiveOutputTerminal
    | ProjectCompletedEffectiveOutput
    | ProjectCompletedSetOutput
    | ProjectEffectiveOutputCompletionTerminal
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectEffectiveJoinInputAuthority(ProjectCurrentInputAuthority):
    """Exact already-completed producer; no reinterpretation as an endpoint."""

    completion: ProjectCompletion = field(repr=False)
    entry: ProjectConcreteEffectiveOutputEntry = field(repr=False)
    owner: ProjectDeclarationOccurrence = field(init=False)
    fields: tuple[ProjectCurrentSourceField, ...] = field(init=False)
    historical_properties: ProjectIROutputRelationalProperties | None = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        self.validate()
        object.__setattr__(self, "owner", self.entry.owner)
        if isinstance(self.entry, ProjectExistingEffectiveOutput):
            properties = self.entry.properties
            fields = properties.fields
        else:
            properties = None
            fields = tuple(
                ProjectCurrentInputField(authority=self, field_position=position)
                for position in range(len(self.entry.fields))
            )
        object.__setattr__(self, "historical_properties", properties)
        object.__setattr__(self, "fields", fields)

    def validate(self) -> None:
        if type(self.completion) is not ProjectCompletion or type(self.entry) not in {
            ProjectExistingEffectiveOutput,
            ProjectCompletedEffectiveOutput,
            ProjectCompletedSetOutput,
        }:
            raise TypeError(
                "Effective input requires exact concrete completion authority."
            )
        entries = self.completion.find_owner(self.entry.owner)
        base = (
            self.entry
            if isinstance(self.entry, ProjectExistingEffectiveOutput)
            else self.entry.base_entry
        )
        if len(entries) != 1 or entries[0] is not base:
            raise ValueError(
                "Effective input is detached from the exact completion snapshot."
            )
        if isinstance(self.entry, ProjectCompletedSetOutput):
            self.entry.validate()
        else:
            self.entry.__post_init__()
            if isinstance(self.entry, ProjectCompletedEffectiveOutput):
                _validate_distinct_projection(self.entry.root, self.entry.fields)

    def type_sources(
        self, field_position: int
    ) -> tuple[ProjectRowEquivalenceField, ...]:
        return _entry_type_sources(self.entry, field_position)

    def field_parts(
        self,
    ) -> tuple[tuple[ProjectModuleRowFieldIdentity, ProjectRowField, object], ...]:
        self.validate()
        if isinstance(self.entry, ProjectExistingEffectiveOutput):
            return tuple(
                (
                    _canonical_field(
                        self.completion.plan.attribution, self.entry.properties, member
                    ),
                    member.evidence,
                    member,
                )
                for member in self.entry.properties.fields
            )
        return tuple(
            (member.identity, member.field, member) for member in self.entry.fields
        )

    def materialized_properties(
        self,
        output: ProjectCurrentMaterializedInput,
        incoming: ProjectIROutputRelationalProperties | None,
    ) -> ProjectIROutputRelationalProperties:
        return _current_input_properties(self, output, incoming)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentInputGroupedContext(ProjectIRGroupedEvaluationContext):
    """A grouped semantic result at its current input boundary, not a tail operator."""

    authority: ProjectEffectiveJoinInputAuthority = field(repr=False)
    node: ProjectIRPlanNodeOccurrence

    def __post_init__(self) -> None:
        if (
            not isinstance(self.authority.entry, ProjectCompletedEffectiveOutput)
            or _projection_domain(self.authority.entry).kind
            is not ProjectCompletedRowDomainKind.GROUPED
            or type(self.node.anchor) is not ProjectIRRelationAnchor
            or self.node.anchor.identity != _declaration_identity(self.authority.owner)
            or self.node.ref.scope
            is not self.authority.completion.plan.structural_stage.scope
        ):
            raise ValueError(
                "Grouped input context requires exact completed group evidence."
            )

    @property
    def grouped_operator_node(self) -> ProjectIRPlanNodeOccurrence:
        return self.node

    @property
    def grouped_owner(self):
        return _declaration_identity(self.authority.owner)

    @property
    def grouped_keys(self) -> tuple[object, ...]:
        entry = self.authority.entry
        if not isinstance(entry, ProjectCompletedEffectiveOutput):
            raise TypeError("Grouped input requires completed semantic fields.")
        return _projection_domain(entry).grouped_basis


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentInputGrainAuthority(ProjectGrainOriginAuthority):
    source: ProjectEffectiveJoinInputAuthority = field(repr=False)
    incoming: ProjectIRProvidedIntrinsicGrain = field(repr=False)
    context: ProjectCurrentInputGroupedContext | None = field(repr=False)


def _input_source_class(
    properties: ProjectIROutputRelationalProperties, position: int
) -> ProjectIROutputValueClass:
    matches = tuple(
        group
        for group in properties.value_classes
        if any(member is properties.fields[position] for member in group.members)
    )
    if len(matches) != 1:
        raise ValueError("Input image requires an exact incoming value class.")
    return matches[0]


def _current_input_properties(
    authority: ProjectEffectiveJoinInputAuthority,
    output: ProjectCurrentMaterializedInput,
    incoming: ProjectIROutputRelationalProperties | None,
) -> ProjectIROutputRelationalProperties:
    entry = authority.entry
    if isinstance(entry, ProjectCompletedSetOutput):
        if (
            output.authority is not authority
            or incoming is not None
            or len(output.set_inputs) != len(entry.root.uses)
        ):
            raise ValueError(
                "Set materialization requires its exact operand property tuple."
            )
        for use, properties in zip(entry.root.uses, output.set_inputs, strict=True):
            if use.authority.historical_properties is not None:
                valid = properties is use.authority.historical_properties
            else:
                valid = (
                    isinstance(properties.output, ProjectCurrentMaterializedInput)
                    and properties.output.authority is use.authority
                    and properties.output.properties is properties
                )
            if not valid:
                raise ValueError(
                    "Set properties cannot borrow another operand producer."
                )
        origin = entry.row_domain.set_origin
        if origin is None:
            raise ValueError("Set materialization lost its exact grain origin.")
        return transfer_set_properties(output, output.set_inputs, origin)
    if output.set_inputs:
        raise ValueError(
            "SELECT materialization cannot acquire set operand properties."
        )
    if (
        type(entry) is not ProjectCompletedEffectiveOutput
        or output.authority is not authority
    ):
        raise ValueError(
            "Current input properties require the exact completed producer."
        )
    root = entry.root
    if isinstance(root, ProjectConcreteJoinedQualify):
        source_properties = root.window_stage.input_aggregation.input_filter.joined_semantics.property_bridge.relational
        if incoming is not None and incoming is not source_properties:
            raise ValueError(
                "Current joined input cannot substitute its property root."
            )
        incoming = source_properties
    elif incoming is None:
        raise ValueError("Replayed input properties require an exact upstream image.")
    else:
        upstream = root.upstream_entry
        if isinstance(upstream, ProjectExistingEffectiveOutput):
            valid = incoming is upstream.properties
        else:
            valid = (
                isinstance(incoming.output, ProjectCurrentMaterializedInput)
                and incoming.output.authority.entry is upstream
                and incoming is incoming.output.properties
            )
        if not valid:
            raise ValueError(
                "Current replay input cannot borrow a stale upstream image."
            )
    fields = _field_occurrences(output)
    domain = entry.row_domain
    distinct = domain.distinct
    if distinct is not None:
        domain = distinct.input_domain
    if domain.kind is ProjectCompletedRowDomainKind.PRESERVED:
        source_classes: list[ProjectIROutputValueClass | None] = []
        for selected in entry.fields:
            position = None
            source = selected.source
            if (
                isinstance(source, ProjectConcreteJoinedNamespaceExpression)
                and isinstance(source.expression, (NameExpr, DottedNameExpr))
                and len(source.resolutions) == 1
            ):
                resolution = source.resolutions[0]
                if (
                    isinstance(resolution, ProjectScalarReferenceResolution)
                    and resolution.target is not None
                ):
                    position = resolution.target.position
            elif (
                isinstance(source, ProjectNoJoinScalarExpression)
                and isinstance(root, ProjectConcreteNoJoinReplay)
                and isinstance(source.expression, (NameExpr, DottedNameExpr))
            ):
                expression = source.expression
                name = (
                    expression.name
                    if isinstance(expression, NameExpr)
                    else expression.parts[-1]
                )
                if (
                    not isinstance(expression, NameExpr)
                    or name not in root.let_scope.value_types
                ):
                    member = root.input_schema.fields.get(name)
                    matches = tuple(
                        i
                        for i, value in enumerate(incoming.fields)
                        if value.evidence is member
                    )
                    if len(matches) == 1:
                        position = matches[0]
            source_classes.append(
                None if position is None else _input_source_class(incoming, position)
            )
        classes, images = _projection_classes_from_sources(
            incoming, output, fields, tuple(source_classes)
        )
        keys, fds = _image_keys_and_fds(
            incoming, output, classes, images, support=authority
        )
        original = incoming.grain
        grain = ProjectIRProvidedIntrinsicGrain(
            output=output,
            state=original.state,
            factors=original.factors,
            active=original.active,
            dependencies=original.dependencies,
            origin_set=original.origin_set,
            witness=authority,
        )
    else:
        classes = _singleton_classes(output, fields)
        original = incoming.grain
        context = (
            ProjectCurrentInputGroupedContext(authority=authority, node=output.node)
            if domain.kind is ProjectCompletedRowDomainKind.GROUPED
            else None
        )
        origins = ProjectCurrentInputGrainAuthority(
            source=authority, incoming=original, context=context
        )
        dependencies = list(original.dependencies)
        if context is None:
            active, factors, keys = (), original.factors, ()
            state = ProjectGrainBasisState.GLOBAL
        else:
            factor = ProjectGroupedGrainFactorIdentity(
                owner=context.grouped_owner, operator=output.node.ref, context=context
            )
            active = (factor,)
            factors = (*original.factors, ProjectGrainDomainFactor(identity=factor))
            if original.active:
                dependencies.append(
                    ProjectGrainDependencyFact(
                        determinants=original.active, dependents=active
                    )
                )
            selected_keys: list[ProjectIROutputValueClass] = []
            represented: list[object] = []
            for i, selected in enumerate(entry.fields):
                source = selected.source
                basis = None
                if isinstance(source, ProjectJoinedStageOutputOccurrence):
                    basis = source.group_key
                elif (
                    isinstance(source, ProjectNoJoinGroupedOutput)
                    and selected.result_role is ProjectRowResultRole.GROUP_KEY
                    and isinstance(root, ProjectConcreteNoJoinReplay)
                ):
                    expression = selected.item.expression
                    name = (
                        expression.name
                        if isinstance(expression, NameExpr)
                        else expression.parts[-1]
                        if isinstance(expression, DottedNameExpr)
                        else None
                    )
                    target = (
                        None if name is None else root.input_schema.fields.get(name)
                    )
                    matches = tuple(
                        item
                        for item in domain.grouped_basis
                        if isinstance(item, ProjectRelationClauseDependencyFact)
                        and item.target_field is target
                    )
                    basis = matches[0] if len(matches) == 1 else None
                if basis is not None:
                    selected_keys.append(classes[i])
                    represented.append(basis)
            complete = all(
                any(item is retained for retained in represented)
                for item in domain.grouped_basis
            )
            keys = (
                (
                    ProjectIROutputCandidateKey(
                        output=output,
                        determinants=tuple(selected_keys),
                        strength=ProjectRowUniquenessStrength.STRICT,
                        supports=(authority, context),
                    ),
                )
                if complete and selected_keys
                else ()
            )
            state = ProjectGrainBasisState.FACTORIZED
        fds = _key_fds(output, classes, keys)
        grain = ProjectIRProvidedIntrinsicGrain(
            output=output,
            state=state,
            factors=factors,
            active=active,
            dependencies=tuple(dependencies),
            origin_set=origins,
            witness=origins,
        )
    if distinct is not None:
        grain = distinct_output_grain(output, distinct.origin, witness=authority)
    return ProjectIROutputRelationalProperties(
        output=output,
        fields=fields,
        value_classes=classes,
        keys=keys,
        fds=fds,
        fd_index=_compile_output_fd_index(output, classes, fds),
        grain=grain,
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCurrentJoinAdmission:
    """Exact owner-held temporary diagnostics retired by a successful JOIN region."""

    completion: ProjectCompletion = field(repr=False)
    region: ProjectCurrentJoinRegion = field(repr=False)
    semantic_facts: ProjectModuleRelationSemanticFacts = field(init=False, repr=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.completion) is not ProjectCompletion
            or type(self.region) is not ProjectCurrentJoinRegion
            or self.region.conditions.uses
            is not self.completion.verification.root.join_regions.uses
        ):
            raise ValueError(
                "JOIN admission retirement requires exact completed operation roots."
            )
        facts = _semantic_facts(self.completion, self.region.ledger.owner)
        definition = _derived_definition(facts.owner)
        if facts.helper_diagnostics != syntax_diagnostics(
            definition, allow_distinct=True
        ) or any(
            join.use.kind
            not in {
                AuthoredJoinKind.INNER,
                AuthoredJoinKind.LEFT,
                AuthoredJoinKind.CROSS,
                AuthoredJoinKind.RIGHT,
                AuthoredJoinKind.FULL,
                AuthoredJoinKind.SEMI,
                AuthoredJoinKind.ANTI,
            }
            for join in self.region.joins
        ):
            raise ValueError(
                "JOIN retirement requires its exact syntax-availability producer."
            )
        object.__setattr__(self, "semantic_facts", facts)
        object.__setattr__(self, "diagnostics", facts.helper_diagnostics)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectEffectiveOutputCompletion:
    """Immutable Slice-12 overlay over the exact Slice-7 completion ledger."""

    base: ProjectCompletion = field(repr=False, compare=False, hash=False)
    joined_qualifies: ProjectJoinedQualifySet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    replay_roots: tuple[ProjectNoJoinReplayRoot, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    owners: tuple[ProjectDeclarationOccurrence, ...]
    dependencies: tuple[ProjectCompletionDependency, ...]
    schedule: tuple[ProjectDeclarationOccurrence, ...]
    entries: tuple[ProjectEffectiveOutputCompletionEntry, ...]
    current_regions: tuple[ProjectCurrentJoinRegion, ...] = field(
        default=(), repr=False
    )
    current_readiness: tuple[
        ProjectConcreteJoinedRowSemantics | ProjectNonConcreteJoinedRowSemantics, ...
    ] = field(default=(), repr=False)
    current_tails: tuple[ProjectJoinedQualifySet, ...] = field(default=(), repr=False)
    condition_authority: ProjectJoinConditionSet | None = field(
        default=None, repr=False
    )
    operative_conditions: (
        ProjectJoinConditionSet | ProjectJoinConditionCompletion | None
    ) = field(default=None, repr=False)
    input_scopes: tuple[ProjectCurrentJoinInputScope, ...] = field(
        default=(), repr=False
    )
    allocation_events: tuple[
        ProjectCurrentMaterializedInput | ProjectCurrentJoinRegion, ...
    ] = field(default=(), repr=False)
    join_admissions: tuple[ProjectCurrentJoinAdmission, ...] = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        if (
            type(self.base) is not ProjectCompletion
            or type(self.joined_qualifies) is not ProjectJoinedQualifySet
        ):
            raise TypeError("Effective-output completion requires exact roots.")
        if type(self.entries) is not tuple or any(
            type(entry)
            not in {
                ProjectExistingEffectiveOutput,
                ProjectEffectiveOutputTerminal,
                ProjectCompletedEffectiveOutput,
                ProjectCompletedSetOutput,
                ProjectEffectiveOutputCompletionTerminal,
            }
            for entry in self.entries
        ):
            raise TypeError("Completion overlay requires an exact entry tuple.")
        if type(self.replay_roots) is not tuple or any(
            type(root) is not ProjectNoJoinReplayRoot for root in self.replay_roots
        ):
            raise TypeError("Completion overlay requires an exact replay-root tuple.")
        if len({id(root) for root in self.replay_roots}) != len(self.replay_roots):
            raise ValueError("Completion overlay cannot repeat one replay root.")
        completion = (
            self.joined_qualifies.window_set.aggregation_set.filter_set.completion
        )
        if completion is not self.base or any(
            (
                self.owners is not self.base.owners,
                self.dependencies is not self.base.dependencies,
                self.schedule is not self.base.schedule,
            )
        ):
            raise ValueError("Completion overlay must retain exact Slice-7 authority.")
        if len(self.entries) != len(self.owners) or any(
            entry.owner is not owner
            or (
                type(entry)
                in {
                    ProjectCompletedEffectiveOutput,
                    ProjectCompletedSetOutput,
                    ProjectEffectiveOutputCompletionTerminal,
                }
                and cast(
                    ProjectCompletedEffectiveOutput
                    | ProjectEffectiveOutputCompletionTerminal,
                    entry,
                ).base_entry
                is not base_entry
            )
            or (
                type(entry)
                in {ProjectExistingEffectiveOutput, ProjectEffectiveOutputTerminal}
                and entry is not base_entry
            )
            for entry, base_entry, owner in zip(
                self.entries,
                self.base.entries,
                self.owners,
                strict=True,
            )
        ):
            raise ValueError("Completion overlay requires one exact entry per owner.")
        _validate_completion_overlay_membership(self)
        object.__setattr__(
            self,
            "join_admissions",
            tuple(
                ProjectCurrentJoinAdmission(completion=self.base, region=region)
                for region in self.current_regions
            ),
        )

    def find_owner(
        self,
        owner: ProjectDeclarationOccurrence,
    ) -> tuple[ProjectEffectiveOutputCompletionEntry, ...]:
        if type(owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Completion lookup requires an exact owner occurrence.")
        return tuple(entry for entry in self.entries if entry.owner is owner)


def _derived_definition(
    owner: ProjectDeclarationOccurrence,
) -> _DerivedRelation:
    if type(owner) is not ProjectDeclarationOccurrence or type(
        owner.definition
    ) not in {TableDef, QueryDef}:
        raise TypeError("Final relation semantics require a table or query owner.")
    return cast(_DerivedRelation, owner.definition)


def _source_location(expression: Expression) -> SourceLocation:
    span = expression.span
    return SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _validate_completed_field_source(output: ProjectCompletedOutputField) -> None:
    source = output.source
    if type(source) is ProjectConcreteJoinedNamespaceExpression:
        valid = (
            source.namespace.binding_environment.ledger.owner is output.owner
            and source.expression is output.item.expression
            and output.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE
        )
    elif type(source) is ProjectJoinedStageOutputOccurrence:
        expected_role = (
            ProjectRowResultRole.GROUP_KEY
            if source.role is ProjectJoinedStageOutputRole.GROUP_KEY
            else ProjectRowResultRole.AGGREGATE_RESULT
        )
        valid = (
            source.input_filter.entry.owner is output.owner
            and source.selected_output_ordinal == output.selected_output_ordinal
            and source.item is output.item
            and source.output_name == output.output_name
            and output.result_role is expected_role
        )
    elif type(source) is ProjectSelectedWindowResultBinding:
        valid = (
            source.computation.input_namespace.aggregation.input_filter.entry.owner
            is output.owner
            and source.selected_output_ordinal == output.selected_output_ordinal
            and source.item is output.item
            and source.output_name == output.output_name
            and output.result_role is ProjectRowResultRole.WINDOW_RESULT
        )
    elif type(source) is ProjectNoJoinScalarExpression:
        valid = (
            source.owner is output.owner
            and source.expression is output.item.expression
            and source.status is ProjectNoJoinScalarStatus.CONCRETE
            and output.result_role is ProjectRowResultRole.ORDINARY_ROW_VALUE
        )
    elif type(source) is ProjectNoJoinGroupedOutput:
        valid = (
            source.select_fact is output.select_fact
            and source.field is output.field
            and source.readiness.definition is output.owner.definition
        )
    else:
        assert type(source) is ProjectModuleWindowOutputFact
        valid = (
            source.owner is output.owner
            and source.selected_output_ordinal == output.selected_output_ordinal
            and source.item is output.item
            and source.output_name == output.output_name
            and source.status is ProjectModuleCandidateBucketStatus.CONCRETE
            and output.result_role is ProjectRowResultRole.WINDOW_RESULT
        )
    if not valid:
        raise ValueError("Completed field source must retain exact owner occurrence.")


def _validate_relation_order_source(output: ProjectRelationOrderItem) -> None:
    source = output.source
    if type(source) is ProjectConcreteJoinedNamespaceExpression:
        valid = (
            source.namespace.binding_environment.ledger.owner is output.owner
            and source.expression is output.expression
            and source.value_type is output.value_type
        )
    elif type(source) is ProjectJoinedWindowInputBinding:
        valid = (
            source.aggregation.input_filter.entry.owner is output.owner
            and type(output.expression) is NameExpr
            and source.name == output.expression.name
            and source.value_type is output.value_type
        )
    elif type(source) is ProjectSelectedWindowResultBinding:
        valid = (
            source.computation.input_namespace.aggregation.input_filter.entry.owner
            is output.owner
            and type(output.expression) is NameExpr
            and source.output_name == output.expression.name
            and source.value_type is output.value_type
        )
    elif type(source) is ProjectNoJoinScalarExpression:
        valid = (
            source.owner is output.owner
            and source.expression is output.expression
            and source.status is ProjectNoJoinScalarStatus.CONCRETE
            and source.value_type is output.value_type
        )
    elif type(source) is ProjectModuleClauseDependencyFact:
        valid = (
            source.owner is output.owner
            and source.role is ProjectModuleFactOccurrenceRole.GROUPED_ORDER
            and source.source_occurrence is output.item
            and len(source.target_fields) == 1
            and project_row_field_to_semantic_value_type(
                source.target_fields[0],
                source.target_fields[0].nullability,
            )
            == output.value_type
        )
    else:
        assert type(source) is ProjectModuleWindowOutputFact
        valid = (
            source.owner is output.owner
            and type(output.expression) is NameExpr
            and source.output_name == output.expression.name
            and _window_output_value_type(source) is output.value_type
        )
    if not valid:
        raise ValueError("Relation order source must retain exact owner evidence.")


def _semantic_facts(
    completion: ProjectCompletion,
    owner: ProjectDeclarationOccurrence,
) -> ProjectModuleRelationSemanticFacts:
    matches = completion.plan.semantic_facts.find_owner(owner)
    if len(matches) != 1:
        raise ValueError("Final output requires one exact historical semantic fact.")
    return matches[0]


def _select_facts(
    completion: ProjectCompletion,
    owner: ProjectDeclarationOccurrence,
) -> tuple[ProjectModuleSelectFact, ...]:
    facts = _semantic_facts(completion, owner).select_facts
    definition = _derived_definition(owner)
    if len(facts) != len(definition.select_items) or any(
        fact.owner is not owner
        or fact.selected_output_ordinal != ordinal
        or fact.item is not item
        for ordinal, (fact, item) in enumerate(
            zip(facts, definition.select_items, strict=True)
        )
    ):
        raise ValueError("Final output requires the exact historical select ledger.")
    return facts


def _output_names(
    definition: _DerivedRelation,
) -> tuple[tuple[str, ...] | None, tuple[Diagnostic, ...]]:
    names: list[str] = []
    diagnostics: list[Diagnostic] = []
    seen: set[str] = set()
    for item in definition.select_items:
        name = _projection_output_name(item)
        if name is None:
            diagnostic = _unnamed_projection_diagnostic(item, CheckMode.STRICT)
            if diagnostic is None:
                raise AssertionError("Strict projection naming lost its diagnostic.")
            diagnostics.append(diagnostic)
            continue
        names.append(name)
        if name in seen:
            diagnostics.append(_duplicate_projection_diagnostic(item, name))
        seen.add(name)
    if diagnostics or len(names) != len(definition.select_items):
        return None, tuple(diagnostics)
    return tuple(names), ()


def _entry_schema(entry: ProjectConcreteEffectiveOutputEntry) -> ProjectRowSchema:
    if isinstance(entry, (ProjectCompletedEffectiveOutput, ProjectCompletedSetOutput)):
        return entry.schema
    if type(entry) is ProjectExistingEffectiveOutput:
        state = entry.fragment.semantic_facts.state
        schema = state.schema
        if (
            state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or schema is None
            or schema.is_unknown
        ):
            raise ValueError("Historical effective output requires a concrete schema.")
        return schema
    raise TypeError("Effective input requires one concrete overlay entry.")


def _entry_row_domain(
    entry: ProjectConcreteEffectiveOutputEntry,
) -> ProjectPreservedRowDomainAuthority:
    if isinstance(entry, (ProjectCompletedEffectiveOutput, ProjectCompletedSetOutput)):
        return entry.row_domain
    if type(entry) is ProjectExistingEffectiveOutput:
        return entry.properties.grain
    raise TypeError("Effective input requires one exact row-domain authority.")


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _is_exact_member(value: object, retained: tuple[object, ...]) -> bool:
    return any(value is item for item in retained)


def _validate_projection_domain(
    owner: ProjectDeclarationOccurrence,
    base_entry: ProjectEffectiveOutputEntry,
    root: ProjectFinalOutputRoot,
    domain: ProjectCompletedRowDomain,
) -> None:
    if type(root) is ProjectConcreteJoinedQualify:
        aggregation = root.window_stage.input_aggregation
        mode = aggregation.mode
        valid_root = (
            aggregation.input_filter.entry.owner is owner
            and aggregation.input_filter.entry is base_entry
        )
        grouped_basis: tuple[object, ...] = aggregation.group_keys
        preserved = root.preservation.intrinsic_grain
    else:
        assert type(root) is ProjectConcreteNoJoinReplay
        mode = root.mode
        valid_root = root.owner is owner and root.base_entry is base_entry
        readiness = root.aggregate_readiness
        grouped_basis = (
            ()
            if readiness is None
            else tuple(
                fact
                for fact in readiness.dependency_facts
                if fact.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT
            )
        )
        preserved = _entry_row_domain(root.upstream_entry)
    if not valid_root:
        raise ValueError(
            "Completed output root must retain the exact owner/base entry."
        )
    if mode is ProjectJoinedAggregationMode.ABSENT:
        valid_domain = (
            domain.kind is ProjectCompletedRowDomainKind.PRESERVED
            and domain.preserved is preserved
            and not domain.grouped_basis
        )
    elif mode is ProjectJoinedAggregationMode.GROUPED:
        valid_domain = (
            domain.kind is ProjectCompletedRowDomainKind.GROUPED
            and domain.preserved is None
            and _same_objects(domain.grouped_basis, grouped_basis)
        )
    else:
        valid_domain = (
            domain.kind is ProjectCompletedRowDomainKind.GLOBAL
            and domain.preserved is None
            and not domain.grouped_basis
        )
    if not valid_domain:
        raise ValueError("Completed output row domain must match its exact stage root.")


def _validate_completed_output_root(output: ProjectCompletedEffectiveOutput) -> None:
    root = output.root
    domain = output.row_domain
    distinct = domain.distinct
    if (_derived_definition(output.owner).distinct_clause is None) != (
        distinct is None
    ):
        raise ValueError("Completed output cannot erase authored DISTINCT.")
    if distinct is not None:
        if (
            distinct.root is not root
            or distinct.fields is not output.fields
            or distinct.owner is not output.owner
        ):
            raise ValueError("DISTINCT cannot substitute an alternate projection/root.")
        if distinct.ordering is not output.ordering:
            raise ValueError("DISTINCT cannot substitute another ORDER root.")
        if distinct.global_input != _distinct_global_input(root, distinct.input_domain):
            raise ValueError("DISTINCT must retain exact input cardinality posture.")
        _validate_distinct_projection(root, output.fields)
        _validate_distinct_order_proofs(distinct)
        domain = distinct.input_domain
    _validate_projection_domain(output.owner, output.base_entry, root, domain)
    _validate_completed_output_sources(output)
    for selected in output.fields:
        if not _same_objects(
            selected.type_sources, _selected_type_sources(output.root, selected)
        ):
            raise ValueError(
                "Completed SELECT type images lost their exact input fields."
            )


def _validate_completed_output_sources(
    output: ProjectCompletedEffectiveOutput,
) -> None:
    if any(
        not _completed_field_source_is_rooted(field.source, output.root)
        for field in output.fields
    ):
        raise ValueError("Completed field source must retain its exact entry root.")
    if output.ordering is not None and any(
        not _relation_order_source_is_rooted(item.source, output.root)
        for item in output.ordering.items
    ):
        raise ValueError("Relation ORDER source must retain its exact entry root.")


def _completed_field_source_is_rooted(
    source: ProjectCompletedOutputSource,
    root: ProjectFinalOutputRoot,
) -> bool:
    if type(root) is ProjectConcreteJoinedQualify:
        stage = root.window_stage
        aggregation = stage.input_aggregation
        if type(source) is ProjectConcreteJoinedNamespaceExpression:
            return source.namespace is aggregation.input_filter.namespace
        if type(source) is ProjectJoinedStageOutputOccurrence:
            return _is_exact_member(source, aggregation.stage_outputs)
        if type(source) is ProjectSelectedWindowResultBinding:
            return _is_exact_member(source, stage.selected_results)
        return False
    assert type(root) is ProjectConcreteNoJoinReplay
    if type(source) is ProjectNoJoinScalarExpression:
        return (
            source.input_schema is root.input_schema
            and source.let_scope is root.let_scope
        )
    if type(source) is ProjectNoJoinGroupedOutput:
        return source.readiness is root.aggregate_readiness
    return type(source) is ProjectModuleWindowOutputFact and _is_exact_member(
        source,
        root.window_outputs,
    )


def _relation_order_source_is_rooted(
    source: ProjectRelationOrderSource,
    root: ProjectFinalOutputRoot,
) -> bool:
    if type(root) is ProjectConcreteJoinedQualify:
        stage = root.window_stage
        if type(source) is ProjectConcreteJoinedNamespaceExpression:
            return source.namespace is stage.input_aggregation.input_filter.namespace
        if type(source) is ProjectJoinedWindowInputBinding:
            return _is_exact_member(source, stage.pre_window.bindings)
        if type(source) is ProjectSelectedWindowResultBinding:
            return _is_exact_member(source, stage.selected_results)
        return False
    assert type(root) is ProjectConcreteNoJoinReplay
    if type(source) is ProjectNoJoinScalarExpression:
        return (
            source.input_schema is root.input_schema
            and source.let_scope is root.let_scope
        )
    if type(source) is ProjectModuleClauseDependencyFact:
        return _is_exact_member(source, root.clause_dependencies)
    return type(source) is ProjectModuleWindowOutputFact and _is_exact_member(
        source,
        root.window_outputs,
    )


def _entry_replay_root(
    entry: ProjectEffectiveOutputCompletionEntry,
) -> ProjectNoJoinReplayRoot | None:
    if (
        type(entry) is ProjectCompletedEffectiveOutput
        and type(entry.root) is ProjectConcreteNoJoinReplay
    ):
        return entry.root.replay_root
    if type(entry) is ProjectEffectiveOutputCompletionTerminal:
        return entry.replay_root
    return None


def _validate_completion_overlay_membership(
    overlay: ProjectEffectiveOutputCompletion,
) -> None:
    by_owner = {id(entry.owner): entry for entry in overlay.entries}
    available = [by_owner[id(owner)] for owner in overlay.base.topology.blocked_owners]
    for owner in overlay.schedule:
        entry = by_owner[id(owner)]
        scope = (
            entry.root.scope
            if isinstance(entry, ProjectCompletedSetOutput)
            else entry.blocker.scope
            if isinstance(entry, ProjectEffectiveOutputCompletionTerminal)
            and isinstance(entry.blocker, ProjectSetFailure)
            else None
        )
        if scope is not None and (
            scope.completion is not overlay.base
            or not _same_objects(scope.available, tuple(available))
        ):
            raise ValueError("Set scope must retain the exact current producer prefix.")
        available.append(entry)
    current = _validate_current_inventory(overlay)
    expected_replay_roots = tuple(
        root
        for owner in overlay.schedule
        for entry in overlay.find_owner(owner)
        if (root := _entry_replay_root(entry)) is not None
    )
    if not _same_objects(overlay.replay_roots, expected_replay_roots):
        raise ValueError(
            "Completion overlay requires every exact owner-local replay root."
        )
    for entry, base_entry in zip(
        overlay.entries,
        overlay.base.entries,
        strict=True,
    ):
        if isinstance(entry, ProjectCompletedSetOutput):
            if (
                entry.base_entry is not base_entry
                or entry.root.scope.completion is not overlay.base
            ):
                raise ValueError(
                    "Set output is detached from its exact completion root."
                )
            entry.validate()
            continue
        if (
            isinstance(entry, ProjectEffectiveOutputCompletionTerminal)
            and entry.reason
            is ProjectEffectiveOutputCompletionTerminalReason.SET_NON_CONCRETE
        ):
            if (
                type(entry.blocker) is not ProjectSetFailure
                or entry.blocker.scope.completion is not overlay.base
            ):
                raise ValueError(
                    "Set failure is detached from its exact completion root."
                )
            continue
        if (
            isinstance(entry, ProjectCompletedEffectiveOutput)
            and entry.row_domain.distinct is not None
        ):
            if (
                entry.row_domain.distinct.types
                is not overlay.base.plan.attribution._authority.type_source_resolutions
            ):
                raise ValueError(
                    "DISTINCT type evidence must retain the exact completion root."
                )
        if (
            type(entry) is ProjectEffectiveOutputCompletionTerminal
            and entry.current_inputs is not None
        ):
            if entry.current_inputs.completion is not overlay.base or not any(
                entry.current_inputs is scope for scope in overlay.input_scopes
            ):
                raise ValueError(
                    "Current terminal requires its exact retained input scope."
                )
            if (
                entry.reason
                is ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_CONDITION_NON_CONCRETE
            ):
                operative = overlay.operative_conditions
                if (
                    operative is None
                    or type(entry.blocker) is not tuple
                    or any(
                        not any(item is retained for retained in operative.entries)
                        for item in entry.blocker
                    )
                ):
                    raise ValueError(
                        "Current terminal cannot substitute alternate condition failures."
                    )
            continue
        if id(entry.owner) in current:
            region, readiness, result = current[id(entry.owner)]
            if result is None:
                valid = (
                    type(entry) is ProjectEffectiveOutputCompletionTerminal
                    and entry.current_region is region
                    and entry.blocker is readiness
                )
            else:
                valid = (
                    type(entry) is ProjectCompletedEffectiveOutput
                    and entry.root is result
                ) or (
                    type(entry) is ProjectEffectiveOutputCompletionTerminal
                    and entry.current_region is region
                    and entry.joined_qualify is result
                )
            if not valid:
                raise ValueError(
                    "Current completion must retain its exact local tail root."
                )
            continue
        joined_tail = type(base_entry) is ProjectEffectiveOutputTerminal and (
            base_entry.reason
            is ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
        )
        if joined_tail:
            matches = tuple(
                result
                for result in overlay.joined_qualifies.results
                if _joined_result_owner(result) is entry.owner
            )
            if len(matches) != 1:
                raise ValueError(
                    "Completion overlay requires one exact Slice-11 result."
                )
            result = matches[0]
            valid = (
                type(entry) is ProjectCompletedEffectiveOutput
                and type(result) is ProjectConcreteJoinedQualify
                and entry.root is result
            ) or (
                type(entry) is ProjectEffectiveOutputCompletionTerminal
                and entry.joined_qualify is result
            )
            if not valid:
                raise ValueError(
                    "Completion entry must retain its exact Slice-11 result."
                )
            continue
        if type(entry) not in {
            ProjectCompletedEffectiveOutput,
            ProjectCompletedSetOutput,
            ProjectEffectiveOutputCompletionTerminal,
        }:
            continue
        if len(base_entry.dependencies) != 1:
            raise ValueError("No-JOIN completion requires one exact upstream entry.")
        target = base_entry.dependencies[0].target
        upstream = tuple(item for item in overlay.entries if item.owner is target)
        if len(upstream) != 1:
            raise ValueError("No-JOIN completion requires one exact upstream entry.")
        retained = upstream[0]
        if type(entry) is ProjectCompletedEffectiveOutput:
            valid = (
                type(entry.root) is ProjectConcreteNoJoinReplay
                and entry.root.upstream_entry is retained
            )
        else:
            assert type(entry) is ProjectEffectiveOutputCompletionTerminal
            valid = entry.joined_qualify is None and entry.upstream_entry is retained
        if not valid:
            raise ValueError(
                "No-JOIN completion requires its exact upstream overlay entry."
            )


def _project_type_symbols(
    fields: tuple[ProjectRowField, ...],
) -> Mapping[str, ProjectSymbol]:
    symbols: dict[str, ProjectSymbol] = {}
    conflicts: set[str] = set()
    for row_field in fields:
        resolved = row_field.resolved_type
        symbol = resolved.symbol
        if symbol is None:
            continue
        retained = symbols.get(resolved.name)
        if retained is not None and retained is not symbol:
            conflicts.add(resolved.name)
            continue
        symbols[resolved.name] = symbol
    for name in conflicts:
        symbols.pop(name, None)
    return MappingProxyType(symbols)


def _field_from_value_type(
    *,
    name: str,
    value_type: ValueType,
    role: ProjectRowResultRole,
    type_symbols: Mapping[str, ProjectSymbol],
    provenance_kind: ProjectRowFieldProvenanceKind,
    location: SourceLocation,
    field_def=None,
) -> ProjectRowField | None:
    resolved_type = _project_resolved_type(
        value_type,
        project_type_symbols=type_symbols,
    )
    nullability = _project_nullability(value_type.nullability)
    if resolved_type is None:
        return None
    return ProjectRowField(
        name=name,
        resolved_type=resolved_type,
        nullability=nullability,
        field_def=field_def,
        provenance=ProjectRowFieldProvenance(
            kind=provenance_kind,
            location=location,
        ),
        result_role=role,
    )


def _completed_field_identity(
    owner: ProjectDeclarationOccurrence, position: int, name: str
) -> ProjectModuleRowFieldIdentity:
    """Shared canonical identity constructor for SELECT and non-SELECT outputs."""
    return ProjectModuleRowFieldIdentity(
        owner=_declaration_identity(owner),
        kind=ProjectModuleRowFieldKind.RELATION_OUTPUT,
        field_position=position,
        name=name,
    )


def _completed_field(
    *,
    owner: ProjectDeclarationOccurrence,
    select_fact: ProjectModuleSelectFact,
    name: str,
    row_field: ProjectRowField,
    source: ProjectCompletedOutputSource,
) -> ProjectCompletedOutputField:
    ordinal = select_fact.selected_output_ordinal
    return ProjectCompletedOutputField(
        owner=owner,
        select_fact=select_fact,
        selected_output_ordinal=ordinal,
        item=select_fact.item,
        output_name=name,
        identity=_completed_field_identity(owner, ordinal, name),
        field=row_field,
        result_role=row_field.result_role,
        source=source,
    )


def _analyze_no_join_scalar(
    *,
    owner: ProjectDeclarationOccurrence,
    input_schema: ProjectRowSchema,
    let_scope: ProjectRelationLetScopeFacts,
    expression: Expression,
) -> ProjectNoJoinScalarExpression:
    definition = _derived_definition(owner)
    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    value_type = infer_row_expression(
        expression,
        project_row_schema_to_semantic_row_schema(input_schema),
        value_types,
        diagnostics,
        report_unknown_name=True,
        field_qualifier=definition.from_clause.source_name,
        bare_value_types=let_scope.value_types,
        bare_value_expressions=let_scope.binding_expressions,
    )
    retained_diagnostics = tuple(diagnostics)
    status = (
        ProjectNoJoinScalarStatus.TYPE_NON_CONCRETE
        if value_type.kind is ValueTypeKind.UNKNOWN
        or any(item.severity is Severity.ERROR for item in retained_diagnostics)
        else ProjectNoJoinScalarStatus.CONCRETE
    )
    return ProjectNoJoinScalarExpression(
        owner=owner,
        input_schema=input_schema,
        let_scope=let_scope,
        expression=expression,
        status=status,
        value_type=value_type,
        value_types=value_types,
        diagnostics=retained_diagnostics,
    )


def _no_join_where(
    *,
    owner: ProjectDeclarationOccurrence,
    input_schema: ProjectRowSchema,
    let_scope: ProjectRelationLetScopeFacts,
) -> ProjectConcreteNoJoinWhere | ProjectNoJoinScalarExpression:
    definition = _derived_definition(owner)
    clause = definition.where_clause
    if clause is None:
        return ProjectConcreteNoJoinWhere(
            owner=owner,
            kind=ProjectNoJoinWhereKind.ABSENT,
        )
    analysis = _analyze_no_join_scalar(
        owner=owner,
        input_schema=input_schema,
        let_scope=let_scope,
        expression=clause.expression,
    )
    diagnostics = list(analysis.diagnostics)
    if contains_semantic_aggregate(clause.expression):
        diagnostics.insert(
            0,
            invalid_context_diagnostic(clause.expression, context="where clause"),
        )
    if diagnostics != list(analysis.diagnostics):
        return ProjectNoJoinScalarExpression(
            owner=owner,
            input_schema=input_schema,
            let_scope=let_scope,
            expression=analysis.expression,
            status=ProjectNoJoinScalarStatus.TYPE_NON_CONCRETE,
            value_type=analysis.value_type,
            value_types=analysis.value_types,
            diagnostics=tuple(diagnostics),
        )
    if analysis.status is not ProjectNoJoinScalarStatus.CONCRETE:
        return analysis
    bool_diagnostic = semantic_predicates._check_bool_expression(
        clause.expression,
        context="where clause",
        expression_value_types=analysis.value_types,
    )
    if bool_diagnostic is not None:
        return ProjectNoJoinScalarExpression(
            owner=owner,
            input_schema=input_schema,
            let_scope=let_scope,
            expression=analysis.expression,
            status=ProjectNoJoinScalarStatus.TYPE_NON_CONCRETE,
            value_type=analysis.value_type,
            value_types=analysis.value_types,
            diagnostics=(*analysis.diagnostics, bool_diagnostic),
        )
    return ProjectConcreteNoJoinWhere(
        owner=owner,
        kind=ProjectNoJoinWhereKind.AUTHORED_WHERE,
        expression_analysis=analysis,
        diagnostics=analysis.diagnostics,
        retention_effects=_SQL_ROW_RETENTION_EFFECTS,
    )


def _relation_limit(
    owner: ProjectDeclarationOccurrence,
) -> ProjectRelationLimitResult:
    definition = _derived_definition(owner)
    clause = definition.limit_clause
    if clause is None:
        return None
    diagnostics = check_relation_limits(
        Script(
            span=definition.span,
            header=None,
            definitions=(definition,),
        )
    )
    if diagnostics:
        return ProjectNonConcreteRelationLimit(
            owner=owner,
            clause=clause,
            diagnostics=diagnostics,
        )
    literal = clause.expression
    if type(literal) is not LiteralExpr or type(literal.value) is not int:
        raise AssertionError("Valid relation limit lost its exact integer literal.")
    return ProjectRelationLimit(
        owner=owner,
        clause=clause,
        literal=literal,
        value=literal.value,
    )


def _joined_type_symbols(
    aggregation: ProjectConcreteJoinedAggregation,
) -> Mapping[str, ProjectSymbol]:
    return _project_type_symbols(
        tuple(
            semantics.scalar_field.evidence
            for semantics in aggregation.input_filter.fields
        )
    )


def _direct_joined_field(
    *,
    name: str,
    analysis: ProjectConcreteJoinedNamespaceExpression,
) -> ProjectRowField | None:
    if (
        type(analysis.expression) not in {NameExpr, DottedNameExpr}
        or len(analysis.resolutions) != 1
    ):
        return None
    resolution = analysis.resolutions[0]
    if type(resolution) is not ProjectScalarReferenceResolution or (
        resolution.target is None
    ):
        return None
    source_field = resolution.target.evidence
    return ProjectRowField(
        name=name,
        resolved_type=source_field.resolved_type,
        nullability=_project_nullability(analysis.value_type.nullability),
        field_def=source_field.field_def,
        provenance=ProjectRowFieldProvenance(
            kind=ProjectRowFieldProvenanceKind.DIRECT_PROJECTION,
            location=_source_location(analysis.expression),
        ),
    )


def _joined_final_fields(
    *,
    completion: ProjectCompletion,
    result: ProjectConcreteJoinedQualify,
    names: tuple[str, ...],
) -> tuple[
    tuple[ProjectCompletedOutputField, ...] | None,
    object | None,
    tuple[Diagnostic, ...],
]:
    stage = result.window_stage
    aggregation = stage.input_aggregation
    owner = aggregation.input_filter.entry.owner
    definition = _derived_definition(owner)
    select_facts = _select_facts(completion, owner)
    selected_windows = {
        item.selected_output_ordinal: item for item in stage.selected_results
    }
    stage_outputs = {
        item.selected_output_ordinal: item for item in aggregation.stage_outputs
    }
    type_symbols = _joined_type_symbols(aggregation)
    completed: list[ProjectCompletedOutputField] = []
    for ordinal, (item, name, select_fact) in enumerate(
        zip(definition.select_items, names, select_facts, strict=True)
    ):
        if type(item.expression) is WindowExpr:
            source = selected_windows.get(ordinal)
            if source is None:
                return None, stage, stage.diagnostics
            row_field = _field_from_value_type(
                name=name,
                value_type=source.value_type,
                role=ProjectRowResultRole.WINDOW_RESULT,
                type_symbols=type_symbols,
                provenance_kind=ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION,
                location=_source_location(item.expression),
            )
        elif aggregation.mode is ProjectJoinedAggregationMode.ABSENT:
            analysis = analyze_project_joined_namespace_expression(
                aggregation.input_filter.namespace,
                item.expression,
            )
            if type(analysis) is ProjectNonConcreteJoinedNamespaceExpression:
                return None, analysis, analysis.diagnostics
            if type(analysis) is not ProjectConcreteJoinedNamespaceExpression:
                raise AssertionError(
                    "Joined projection lost its scalar result variant."
                )
            source = analysis
            row_field = _direct_joined_field(name=name, analysis=analysis)
            row_field = row_field or _field_from_value_type(
                name=name,
                value_type=analysis.value_type,
                role=ProjectRowResultRole.ORDINARY_ROW_VALUE,
                type_symbols=type_symbols,
                provenance_kind=(
                    ProjectRowFieldProvenanceKind.LET_DERIVED
                    if any(
                        type(resolution) is ProjectJoinedLetReferenceResolution
                        for resolution in analysis.resolutions
                    )
                    else ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
                ),
                location=_source_location(item.expression),
            )
        else:
            source = stage_outputs.get(ordinal)
            if source is None:
                return None, aggregation, aggregation.diagnostics
            role = (
                ProjectRowResultRole.GROUP_KEY
                if source.role is ProjectJoinedStageOutputRole.GROUP_KEY
                else ProjectRowResultRole.AGGREGATE_RESULT
            )
            row_field = _field_from_value_type(
                name=name,
                value_type=source.value_type,
                role=role,
                type_symbols=type_symbols,
                provenance_kind=(
                    ProjectRowFieldProvenanceKind.DIRECT_PROJECTION
                    if role is ProjectRowResultRole.GROUP_KEY
                    else ProjectRowFieldProvenanceKind.AGGREGATE
                ),
                location=_source_location(item.expression),
            )
        if row_field is None:
            return None, source, ()
        completed.append(
            _completed_field(
                owner=owner,
                select_fact=select_fact,
                name=name,
                row_field=row_field,
                source=source,
            )
        )
    return tuple(completed), None, ()


def _order_direction(item: OrderItem) -> ProjectRelationOrderDirection:
    return ProjectRelationOrderDirection(
        "asc" if item.direction is None else item.direction
    )


def _joined_fallback_is_absent(
    analysis: ProjectNonConcreteJoinedNamespaceExpression,
) -> bool:
    return bool(analysis.resolutions) and all(
        type(resolution) is ProjectScalarReferenceResolution
        and resolution.status is ProjectModuleCandidateBucketStatus.ABSENT
        for resolution in analysis.resolutions
    )


def _joined_relation_ordering(
    result: ProjectConcreteJoinedQualify,
) -> ProjectRelationOrderingResult:
    stage = result.window_stage
    aggregation = stage.input_aggregation
    owner = aggregation.input_filter.entry.owner
    definition = _derived_definition(owner)
    clause = definition.order_by_clause
    if clause is None:
        return None
    if aggregation.mode is ProjectJoinedAggregationMode.GLOBAL:
        return ProjectNonConcreteRelationOrdering(
            owner=owner,
            clause=clause,
            reason=(ProjectRelationOrderingNonConcreteReason.GLOBAL_ORDER_UNSUPPORTED),
            blocker=aggregation,
        )

    ordered: list[ProjectRelationOrderItem] = []
    for ordinal, item in enumerate(clause.items):
        expression = item.expression
        source: ProjectRelationOrderSource
        value_type: ValueType
        if aggregation.mode is ProjectJoinedAggregationMode.GROUPED:
            if type(expression) is not NameExpr:
                diagnostic = _grouped_order_by_unsupported_diagnostic(expression)
                return ProjectNonConcreteRelationOrdering(
                    owner=owner,
                    clause=clause,
                    reason=(
                        ProjectRelationOrderingNonConcreteReason.GROUPED_ORDER_UNSUPPORTED
                    ),
                    blocker=item,
                    diagnostics=(diagnostic,),
                )
            input_candidates = stage.post_window.pre_window.candidates(expression)
            selected_candidates = stage.post_window.selected_candidates(expression.name)
            if len(input_candidates) == 1:
                source = input_candidates[0]
                value_type = source.value_type
            elif not input_candidates and len(selected_candidates) == 1:
                source = selected_candidates[0]
                value_type = source.value_type
            else:
                diagnostic = _grouped_order_by_unsupported_diagnostic(expression)
                return ProjectNonConcreteRelationOrdering(
                    owner=owner,
                    clause=clause,
                    reason=(
                        ProjectRelationOrderingNonConcreteReason.GROUPED_ORDER_UNSUPPORTED
                    ),
                    blocker=(input_candidates, selected_candidates),
                    diagnostics=(diagnostic,),
                )
        else:
            analysis = analyze_project_joined_namespace_expression(
                aggregation.input_filter.namespace,
                expression,
            )
            if type(analysis) is ProjectConcreteJoinedNamespaceExpression:
                source = analysis
                value_type = analysis.value_type
            else:
                if type(analysis) is not ProjectNonConcreteJoinedNamespaceExpression:
                    raise AssertionError("Joined ORDER lost its scalar result variant.")
                selected_candidates = (
                    stage.post_window.selected_candidates(expression.name)
                    if type(expression) is NameExpr
                    and _joined_fallback_is_absent(analysis)
                    else ()
                )
                if len(selected_candidates) != 1:
                    return ProjectNonConcreteRelationOrdering(
                        owner=owner,
                        clause=clause,
                        reason=(
                            ProjectRelationOrderingNonConcreteReason.EXPRESSION_NON_CONCRETE
                        ),
                        blocker=analysis,
                        diagnostics=analysis.diagnostics,
                    )
                source = selected_candidates[0]
                value_type = source.value_type
        ordered.append(
            ProjectRelationOrderItem(
                owner=owner,
                clause=clause,
                source_ordinal=ordinal,
                item=item,
                expression=expression,
                direction=_order_direction(item),
                value_type=value_type,
                source=source,
            )
        )
    return ProjectRelationOrdering(
        owner=owner,
        clause=clause,
        items=tuple(ordered),
    )


def _joined_row_domain(
    result: ProjectConcreteJoinedQualify,
) -> ProjectCompletedRowDomain:
    aggregation = result.window_stage.input_aggregation
    if aggregation.mode is ProjectJoinedAggregationMode.ABSENT:
        return ProjectCompletedRowDomain(
            kind=ProjectCompletedRowDomainKind.PRESERVED,
            preserved=result.preservation.intrinsic_grain,
        )
    if aggregation.mode is ProjectJoinedAggregationMode.GLOBAL:
        return ProjectCompletedRowDomain(kind=ProjectCompletedRowDomainKind.GLOBAL)
    return ProjectCompletedRowDomain(
        kind=ProjectCompletedRowDomainKind.GROUPED,
        grouped_basis=aggregation.group_keys,
    )


def _window_output_value_type(output: ProjectModuleWindowOutputFact) -> ValueType:
    fact = output.project_fact
    if (
        output.status is not ProjectModuleCandidateBucketStatus.CONCRETE
        or fact is None
        or fact.semantic_fact.result.value_type is None
    ):
        raise ValueError("Concrete replay window requires one exact result type.")
    return fact.semantic_fact.result.value_type


def _no_join_window_scope(
    *,
    definition: _DerivedRelation,
    input_schema: ProjectRowSchema,
    let_scope: ProjectRelationLetScopeFacts,
    mode: ProjectJoinedAggregationMode,
    base_schema: ProjectRowSchema,
) -> WindowInputScope:
    semantic_input = project_row_schema_to_semantic_row_schema(input_schema)
    value_types: dict[Expression, ValueType] = {}
    for item in definition.select_items:
        if type(item.expression) is WindowExpr:
            continue
        name = _projection_output_name(item)
        field = None if name is None else base_schema.fields.get(name)
        if field is not None:
            value_types[item.expression] = project_row_field_to_semantic_value_type(
                field,
                field.nullability,
            )
    if mode is not ProjectJoinedAggregationMode.GLOBAL:
        return build_window_input_scope(
            definition=definition,
            input_schema=semantic_input,
            field_qualifier=definition.from_clause.source_name,
            value_types=value_types,
            let_value_types=let_scope.value_types,
            let_expressions=let_scope.binding_expressions,
        )
    semantic_output = project_row_schema_to_semantic_row_schema(base_schema)
    return WindowInputScope(
        kind=WindowInputScopeKind.GROUPED_RESULT,
        row_schema=semantic_output,
        bindings=tuple(
            WindowInputBinding(
                name=field.name,
                value_type=project_row_field_to_semantic_value_type(
                    field,
                    field.nullability,
                ),
                origin=WindowInputOriginKind.AGGREGATE_RESULT,
                target_name=field.name,
            )
            for field in base_schema.fields.values()
        ),
        allows_qualified_fields=False,
        has_valid_group_aggregate=True,
    )


def _no_join_qualify_candidates(
    owner: ProjectDeclarationOccurrence,
    scope: WindowInputScope,
    selected_windows: tuple[ProjectModuleWindowOutputFact, ...],
    expression: NameExpr | DottedNameExpr,
) -> tuple[ProjectNoJoinQualifyCandidate, ...]:
    definition = _derived_definition(owner)
    if type(expression) is NameExpr:
        return (
            *(item for item in scope.bindings if item.name == expression.name),
            *(item for item in selected_windows if item.output_name == expression.name),
        )
    if (
        type(expression) is not DottedNameExpr
        or not scope.allows_qualified_fields
        or len(expression.parts) != 2
        or expression.parts[0] != definition.from_clause.source_name
    ):
        return ()
    name = expression.parts[1]
    return tuple(
        item
        for item in scope.bindings
        if item.name == name and item.origin is WindowInputOriginKind.UPSTREAM_FIELD
    )


def _no_join_qualify_candidate_value_type(
    candidate: ProjectNoJoinQualifyCandidate,
) -> ValueType:
    if type(candidate) is WindowInputBinding:
        return candidate.value_type
    if type(candidate) is ProjectModuleWindowOutputFact:
        return _window_output_value_type(candidate)
    raise TypeError("No-JOIN QUALIFY candidate must be exact.")


def _validate_no_join_qualify_predicate(result: ProjectNoJoinQualify) -> None:
    predicate = result.predicate
    clause = result.clause
    if predicate is None or type(clause) is not QualifyClause:
        raise ValueError("Authored no-JOIN QUALIFY requires a predicate result.")
    hidden_blocked = any(
        type(attempt.analysis) is not WindowComputationAnalysis
        for attempt in result.hidden_attempts
    )
    reference_blocked = any(
        resolution.target is None for resolution in result.references
    )
    has_window = bool(result.selected_windows or result.hidden_attempts)
    expected_early = (
        _ProjectQualifyPredicateNonConcreteReason.WINDOW_COMPUTATION_REQUIRED
        if not has_window
        else (
            _ProjectQualifyPredicateNonConcreteReason.HIDDEN_WINDOW_NON_CONCRETE
            if hidden_blocked
            else (
                _ProjectQualifyPredicateNonConcreteReason.REFERENCE_NON_CONCRETE
                if reference_blocked
                else None
            )
        )
    )
    if expected_early is not None:
        if (
            predicate.reason is not expected_early
            or predicate.kernel_value_type is not None
            or predicate.value_types
            or predicate.retention_effects
        ):
            raise ValueError("No-JOIN QUALIFY blocker precedence must remain exact.")
        return
    for resolution in result.references:
        target = resolution.target
        if target is None or predicate.value_types.get(resolution.expression) is not (
            _no_join_qualify_candidate_value_type(target)
        ):
            raise ValueError("No-JOIN QUALIFY references require exact type seeds.")
    for attempt in result.hidden_attempts:
        value_type = attempt.value_type
        if value_type is None or predicate.value_types.get(attempt.expression) is not (
            value_type
        ):
            raise ValueError("No-JOIN hidden windows require exact type seeds.")
    value_type = predicate.kernel_value_type
    if (
        type(value_type) is not ValueType
        or predicate.value_types.get(clause.expression) is not value_type
    ):
        raise ValueError("No-JOIN QUALIFY requires its exact kernel root type.")
    if predicate.reason is None:
        valid = (
            value_type.kind is ValueTypeKind.KNOWN
            and value_type.resolved_type.name == "Bool"
            and predicate.retention_effects is _SQL_ROW_RETENTION_EFFECTS
            and not any(
                item.severity is Severity.ERROR for item in predicate.diagnostics
            )
        )
    elif predicate.reason is (
        _ProjectQualifyPredicateNonConcreteReason.SCALAR_KERNEL_NON_CONCRETE
    ):
        valid = not predicate.retention_effects and (
            value_type.kind is ValueTypeKind.UNKNOWN
            or any(item.severity is Severity.ERROR for item in predicate.diagnostics)
        )
    else:
        valid = (
            predicate.reason
            is _ProjectQualifyPredicateNonConcreteReason.KNOWN_NON_BOOL_PREDICATE
            and value_type.kind is ValueTypeKind.KNOWN
            and value_type.resolved_type.name != "Bool"
            and not predicate.retention_effects
            and any(item.code == "PIE-S2202" for item in predicate.diagnostics)
        )
    if not valid:
        raise ValueError("No-JOIN QUALIFY predicate result lost exact semantics.")


def _hidden_no_join_window(
    *,
    owner: ProjectDeclarationOccurrence,
    mode: ProjectJoinedAggregationMode,
    scope: WindowInputScope,
    expression: WindowExpr,
) -> ProjectNoJoinHiddenWindowComputation:
    if expression.use_kind is not WindowUseKind.INLINE:
        return ProjectNoJoinHiddenWindowComputation(
            scope=scope,
            expression=expression,
            analysis=None,
        )
    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    analysis = analyze_window_computation(
        expression=expression,
        input_schema=scope.row_schema,
        field_qualifier=_derived_definition(owner).from_clause.source_name,
        value_types=value_types,
        diagnostics=diagnostics,
        bare_value_types=scope.bare_value_types,
        allow_qualified_fields=scope.allows_qualified_fields,
        admission_failure=(
            _WindowComputationAdmissionFailure(
                reason=(
                    "no-group aggregate context does not admit "
                    f"{expression.identity.name}"
                ),
                code=None,
            )
            if mode is ProjectJoinedAggregationMode.GLOBAL
            else None
        ),
    )
    return ProjectNoJoinHiddenWindowComputation(
        scope=scope,
        expression=expression,
        analysis=analysis,
        value_types=value_types,
        diagnostics=tuple(diagnostics),
    )


def _no_join_qualify(
    *,
    owner: ProjectDeclarationOccurrence,
    mode: ProjectJoinedAggregationMode,
    scope: WindowInputScope,
    selected_windows: tuple[ProjectModuleWindowOutputFact, ...],
) -> ProjectNoJoinQualify:
    definition = _derived_definition(owner)
    clause = definition.qualify_clause
    if clause is None:
        return ProjectNoJoinQualify(
            owner=owner,
            kind=ProjectNoJoinQualifyKind.ABSENT,
            mode=mode,
            scope=scope,
            selected_windows=selected_windows,
        )
    references: list[ProjectNoJoinQualifyReferenceResolution] = []
    hidden: list[ProjectNoJoinHiddenWindowComputation] = []
    diagnostics: list[Diagnostic] = []
    for operand in _qualify_operands(clause.expression):
        if type(operand) is WindowExpr:
            attempt = _hidden_no_join_window(
                owner=owner,
                mode=mode,
                scope=scope,
                expression=operand,
            )
            hidden.append(attempt)
            diagnostics.extend(attempt.diagnostics)
            continue
        expression = cast(NameExpr | DottedNameExpr, operand)
        resolution = ProjectNoJoinQualifyReferenceResolution(
            owner=owner,
            scope=scope,
            selected_windows=selected_windows,
            expression=expression,
            candidates=_no_join_qualify_candidates(
                owner,
                scope,
                selected_windows,
                expression,
            ),
        )
        references.append(resolution)
        if resolution.target is None:
            diagnostics.append(
                _qualify_reference_diagnostic(expression, resolution.status)
            )
    hidden_failures = tuple(
        attempt
        for attempt in hidden
        if type(attempt.analysis) is not WindowComputationAnalysis
    )
    reference_failures = tuple(
        resolution for resolution in references if resolution.target is None
    )
    value_types: dict[Expression, ValueType] = {}
    if not hidden_failures and not reference_failures:
        for resolution in references:
            target = resolution.target
            if target is None:
                raise AssertionError("Concrete replay QUALIFY reference lost target.")
            value_types[resolution.expression] = _no_join_qualify_candidate_value_type(
                target
            )
        for attempt in hidden:
            value_type = attempt.value_type
            if value_type is None:
                raise AssertionError("Concrete replay hidden window lost value type.")
            value_types[attempt.expression] = value_type
    predicate = _analyze_qualify_predicate(
        clause=clause,
        has_window=bool(selected_windows or hidden),
        hidden_blocked=bool(hidden_failures),
        reference_blocked=bool(reference_failures),
        value_types=value_types,
        diagnostics=tuple(diagnostics),
    )
    return ProjectNoJoinQualify(
        owner=owner,
        kind=ProjectNoJoinQualifyKind.AUTHORED_QUALIFY,
        mode=mode,
        scope=scope,
        selected_windows=selected_windows,
        clause=clause,
        references=tuple(references),
        hidden_attempts=tuple(hidden),
        predicate=predicate,
    )


def _no_join_final_fields(
    *,
    completion: ProjectCompletion,
    owner: ProjectDeclarationOccurrence,
    input_schema: ProjectRowSchema,
    let_scope: ProjectRelationLetScopeFacts,
    mode: ProjectJoinedAggregationMode,
    aggregate_readiness: ProjectAggregateGroupedClauseReadiness | None,
    base_schema: ProjectRowSchema,
    window_outputs: tuple[ProjectModuleWindowOutputFact, ...],
    names: tuple[str, ...],
) -> tuple[
    tuple[ProjectCompletedOutputField, ...] | None,
    object | None,
    tuple[Diagnostic, ...],
]:
    definition = _derived_definition(owner)
    select_facts = _select_facts(completion, owner)
    windows_by_ordinal = {item.selected_output_ordinal: item for item in window_outputs}
    type_symbols = _project_type_symbols(tuple(input_schema.fields.values()))
    completed: list[ProjectCompletedOutputField] = []
    for ordinal, (item, name, select_fact) in enumerate(
        zip(definition.select_items, names, select_facts, strict=True)
    ):
        if type(item.expression) is WindowExpr:
            source = windows_by_ordinal.get(ordinal)
            if source is None:
                return None, window_outputs, ()
            row_field = _field_from_value_type(
                name=name,
                value_type=_window_output_value_type(source),
                role=ProjectRowResultRole.WINDOW_RESULT,
                type_symbols=type_symbols,
                provenance_kind=ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION,
                location=_source_location(item.expression),
            )
        elif mode is ProjectJoinedAggregationMode.ABSENT:
            analysis = _analyze_no_join_scalar(
                owner=owner,
                input_schema=input_schema,
                let_scope=let_scope,
                expression=item.expression,
            )
            if analysis.status is not ProjectNoJoinScalarStatus.CONCRETE:
                return None, analysis, analysis.diagnostics
            source = analysis
            row_field = base_schema.fields.get(name)
        else:
            if aggregate_readiness is None:
                raise AssertionError("Grouped projection lost its exact readiness.")
            row_field = base_schema.fields.get(name)
            if row_field is None:
                return None, aggregate_readiness, ()
            source = ProjectNoJoinGroupedOutput(
                readiness=aggregate_readiness,
                select_fact=select_fact,
                field=row_field,
            )
        if row_field is None or row_field.resolved_type.kind is (
            ProjectResolvedTypeKind.UNKNOWN
        ):
            return None, source, ()
        completed.append(
            _completed_field(
                owner=owner,
                select_fact=select_fact,
                name=name,
                row_field=row_field,
                source=source,
            )
        )
    return tuple(completed), None, ()


def _no_join_fallback_is_absent(
    analysis: ProjectNoJoinScalarExpression,
) -> bool:
    expression = analysis.expression
    return (
        type(expression) is NameExpr
        and expression.name not in analysis.input_schema.fields
        and expression.name not in analysis.let_scope.value_types
    )


def _no_join_relation_ordering(
    *,
    owner: ProjectDeclarationOccurrence,
    input_schema: ProjectRowSchema,
    let_scope: ProjectRelationLetScopeFacts,
    mode: ProjectJoinedAggregationMode,
    clause_dependencies: tuple[ProjectModuleClauseDependencyFact, ...],
    window_outputs: tuple[ProjectModuleWindowOutputFact, ...],
) -> ProjectRelationOrderingResult:
    definition = _derived_definition(owner)
    clause = definition.order_by_clause
    if clause is None:
        return None
    if mode is ProjectJoinedAggregationMode.GLOBAL:
        return ProjectNonConcreteRelationOrdering(
            owner=owner,
            clause=clause,
            reason=ProjectRelationOrderingNonConcreteReason.GLOBAL_ORDER_UNSUPPORTED,
            blocker=clause,
        )
    ordered: list[ProjectRelationOrderItem] = []
    for ordinal, item in enumerate(clause.items):
        expression = item.expression
        source: ProjectRelationOrderSource
        value_type: ValueType
        if mode is ProjectJoinedAggregationMode.GROUPED:
            facts = tuple(
                fact
                for fact in clause_dependencies
                if fact.role is ProjectModuleFactOccurrenceRole.GROUPED_ORDER
                and fact.source_ordinal == ordinal
                and fact.source_occurrence is item
            )
            if (
                type(expression) is not NameExpr
                or len(facts) != 1
                or facts[0].status is not ProjectModuleCandidateBucketStatus.CONCRETE
                or len(facts[0].target_occurrences) != 1
                or len(facts[0].target_fields) != 1
            ):
                diagnostic = _grouped_order_by_unsupported_diagnostic(expression)
                return ProjectNonConcreteRelationOrdering(
                    owner=owner,
                    clause=clause,
                    reason=(
                        ProjectRelationOrderingNonConcreteReason.GROUPED_ORDER_UNSUPPORTED
                    ),
                    blocker=facts,
                    diagnostics=(diagnostic,),
                )
            fact = facts[0]
            target = fact.target_occurrences[0]
            selected_window = tuple(
                output for output in window_outputs if output.item is target
            )
            if selected_window:
                if len(selected_window) != 1:
                    raise ValueError("Grouped ORDER window target must be unique.")
                source = selected_window[0]
                value_type = _window_output_value_type(source)
            else:
                source = fact
                target_field = fact.target_fields[0]
                value_type = project_row_field_to_semantic_value_type(
                    target_field,
                    target_field.nullability,
                )
        else:
            if contains_semantic_aggregate(expression):
                diagnostic = invalid_context_diagnostic(
                    expression,
                    context="order by",
                )
                return ProjectNonConcreteRelationOrdering(
                    owner=owner,
                    clause=clause,
                    reason=(
                        ProjectRelationOrderingNonConcreteReason.EXPRESSION_NON_CONCRETE
                    ),
                    blocker=item,
                    diagnostics=(diagnostic,),
                )
            analysis = _analyze_no_join_scalar(
                owner=owner,
                input_schema=input_schema,
                let_scope=let_scope,
                expression=expression,
            )
            if analysis.status is ProjectNoJoinScalarStatus.CONCRETE:
                if analysis.value_type is None:
                    raise AssertionError("Concrete no-JOIN ORDER lost its type.")
                source = analysis
                value_type = analysis.value_type
            else:
                selected = (
                    tuple(
                        output
                        for output in window_outputs
                        if output.output_name == expression.name
                    )
                    if type(expression) is NameExpr
                    and _no_join_fallback_is_absent(analysis)
                    else ()
                )
                if len(selected) != 1:
                    return ProjectNonConcreteRelationOrdering(
                        owner=owner,
                        clause=clause,
                        reason=(
                            ProjectRelationOrderingNonConcreteReason.EXPRESSION_NON_CONCRETE
                        ),
                        blocker=analysis,
                        diagnostics=analysis.diagnostics,
                    )
                source = selected[0]
                value_type = _window_output_value_type(source)
        ordered.append(
            ProjectRelationOrderItem(
                owner=owner,
                clause=clause,
                source_ordinal=ordinal,
                item=item,
                expression=expression,
                direction=_order_direction(item),
                value_type=value_type,
                source=source,
            )
        )
    return ProjectRelationOrdering(
        owner=owner,
        clause=clause,
        items=tuple(ordered),
    )


def _no_join_row_domain(
    *,
    upstream_entry: ProjectConcreteEffectiveOutputEntry,
    mode: ProjectJoinedAggregationMode,
    readiness: ProjectAggregateGroupedClauseReadiness | None,
) -> ProjectCompletedRowDomain:
    if mode is ProjectJoinedAggregationMode.ABSENT:
        return ProjectCompletedRowDomain(
            kind=ProjectCompletedRowDomainKind.PRESERVED,
            preserved=_entry_row_domain(upstream_entry),
        )
    if mode is ProjectJoinedAggregationMode.GLOBAL:
        return ProjectCompletedRowDomain(kind=ProjectCompletedRowDomainKind.GLOBAL)
    if readiness is None:
        raise AssertionError("Grouped row domain lost its exact readiness.")
    basis = tuple(
        fact
        for fact in readiness.dependency_facts
        if fact.kind is ProjectRelationClauseDependencyKind.GROUP_KEY_INPUT
    )
    if not basis:
        raise ValueError("Grouped row domain requires exact group-key occurrences.")
    return ProjectCompletedRowDomain(
        kind=ProjectCompletedRowDomainKind.GROUPED,
        grouped_basis=basis,
    )


def _terminal(
    *,
    base_entry: ProjectEffectiveOutputEntry,
    reason: ProjectEffectiveOutputCompletionTerminalReason,
    blocker: object,
    diagnostics: tuple[Diagnostic, ...] = (),
    joined_qualify: ProjectJoinedQualifyResult | None = None,
    replay_root: ProjectNoJoinReplayRoot | None = None,
    upstream_entry: ProjectEffectiveOutputCompletionEntry | None = None,
    current_region: ProjectCurrentJoinRegion | None = None,
    current_inputs: ProjectCurrentJoinInputScope | None = None,
) -> ProjectEffectiveOutputCompletionTerminal:
    if current_region is None and joined_qualify is not None:
        current_region = _current_region_for_result(joined_qualify)
    return ProjectEffectiveOutputCompletionTerminal(
        owner=base_entry.owner,
        base_entry=base_entry,
        reason=reason,
        blocker=blocker,
        dependencies=base_entry.dependencies,
        joined_qualify=joined_qualify,
        replay_root=replay_root,
        upstream_entry=upstream_entry,
        diagnostics=diagnostics,
        current_region=current_region,
        current_inputs=current_inputs,
    )


def _no_join_terminal(
    *,
    semantic_facts: ProjectModuleRelationSemanticFacts,
    base_entry: ProjectEffectiveOutputEntry,
    upstream_entry: ProjectConcreteEffectiveOutputEntry,
    reason: ProjectEffectiveOutputCompletionTerminalReason,
    blocker: object,
    diagnostics: tuple[Diagnostic, ...] = (),
) -> ProjectEffectiveOutputCompletionTerminal:
    replay_root = ProjectNoJoinReplayRoot(
        owner=base_entry.owner,
        base_entry=base_entry,
        upstream_entry=upstream_entry,
        semantic_facts=semantic_facts,
        blocker=blocker,
    )
    return _terminal(
        base_entry=base_entry,
        reason=reason,
        blocker=blocker,
        diagnostics=diagnostics,
        replay_root=replay_root,
        upstream_entry=upstream_entry,
    )


def _entry_type_sources(
    entry: ProjectConcreteEffectiveOutputEntry, position: int
) -> tuple[ProjectRowEquivalenceField, ...]:
    if isinstance(entry, ProjectExistingEffectiveOutput):
        return ()
    return entry.fields[position].type_sources


def _selected_type_sources(
    root: ProjectFinalOutputRoot, selected: ProjectCompletedOutputField
) -> tuple[ProjectRowEquivalenceField, ...]:
    expression = selected.item.expression
    if not isinstance(expression, (NameExpr, DottedNameExpr)):
        return ()
    source = selected.source
    if isinstance(root, ProjectConcreteNoJoinReplay) and isinstance(
        source, ProjectNoJoinScalarExpression
    ):
        name = (
            expression.name
            if isinstance(expression, NameExpr)
            else expression.parts[-1]
        )
        if isinstance(expression, NameExpr) and name in root.let_scope.value_types:
            return ()
        member = root.input_schema.fields.get(name)
        positions = tuple(
            i
            for i, field in enumerate(root.input_schema.fields.values())
            if field is member
        )
        return (
            _entry_type_sources(root.upstream_entry, positions[0])
            if len(positions) == 1
            else ()
        )
    if (
        isinstance(root, ProjectConcreteJoinedQualify)
        and isinstance(source, ProjectConcreteJoinedNamespaceExpression)
        and len(source.resolutions) == 1
    ):
        resolution = source.resolutions[0]
        if (
            isinstance(resolution, ProjectScalarReferenceResolution)
            and resolution.target is not None
        ):
            semantic = root.window_stage.input_aggregation.input_filter.joined_semantics.fields[
                resolution.target.position
            ]
            current = semantic.current_input
            if current is not None:
                return _entry_type_sources(
                    current.authority.entry, current.field_position
                )
    return ()


def _projection_domain(
    entry: ProjectCompletedEffectiveOutput,
) -> ProjectCompletedRowDomain:
    distinct = entry.row_domain.distinct
    return entry.row_domain if distinct is None else distinct.input_domain


def _validate_distinct_projection(
    root: ProjectFinalOutputRoot, fields: tuple[ProjectCompletedOutputField, ...]
) -> None:
    """Bind type and Decimal provenance to the exact selected source value."""
    for selected in fields:
        source, row_field = selected.source, selected.field
        if isinstance(root, ProjectConcreteNoJoinReplay) and isinstance(
            source, (ProjectNoJoinScalarExpression, ProjectNoJoinGroupedOutput)
        ):
            schema = root.base_state.schema
            if (
                schema is None
                or schema.fields.get(selected.output_name) is not row_field
            ):
                raise ValueError(
                    "DISTINCT field requires its exact pre-projection type/source."
                )
            continue
        if isinstance(source, ProjectConcreteJoinedNamespaceExpression):
            direct = _direct_joined_field(name=selected.output_name, analysis=source)
            if direct is not None:
                if (
                    row_field.resolved_type is not direct.resolved_type
                    or row_field.field_def is not direct.field_def
                    or row_field.nullability is not direct.nullability
                ):
                    raise ValueError(
                        "DISTINCT field cannot borrow another source type."
                    )
                continue
            value_type = source.value_type
        elif isinstance(
            source,
            (ProjectJoinedStageOutputOccurrence, ProjectSelectedWindowResultBinding),
        ):
            value_type = source.value_type
        elif isinstance(source, ProjectModuleWindowOutputFact):
            value_type = _window_output_value_type(source)
        else:
            raise ValueError("DISTINCT field requires an exact completed source.")
        actual = project_row_field_to_semantic_value_type(
            row_field, row_field.nullability
        )
        if (
            row_field.field_def is not None
            or actual.resolved_type != value_type.resolved_type
            or actual.nullability is not value_type.nullability
        ):
            raise ValueError(
                "DISTINCT computed field cannot substitute its type evidence."
            )


def _validate_distinct_order_proofs(distinct: ProjectDistinct) -> None:
    expected, failure = _distinct_ordering(
        distinct.root, distinct.fields, distinct.ordering
    )
    if failure is not None or len(distinct.order_proofs) != len(expected):
        raise ValueError("DISTINCT ORDER requires complete determination evidence.")
    for actual, required in zip(distinct.order_proofs, expected, strict=True):
        if (
            not isinstance(actual, tuple)
            or not isinstance(required, tuple)
            or len(actual) != len(required)
            or actual[0] is not required[0]
        ):
            raise ValueError("DISTINCT ORDER proof lost its exact item.")
        if len(actual) == 3:
            if not _same_objects(actual[1], required[1]) or not _same_objects(
                actual[2], required[2]
            ):
                raise ValueError("DISTINCT ORDER proof lost its visible source roots.")
        else:
            proof, current = actual[1], required[1]
            if (
                type(proof) is not ProjectIROutputDeterminationResult
                or type(current) is not ProjectIROutputDeterminationResult
                or proof.seed.index is not current.seed.index
                or not _same_objects(proof.seed.classes, current.seed.classes)
                or not _same_objects(proof.requested.classes, current.requested.classes)
                or proof.status is not ProjectIROutputDeterminationStatus.PROVEN
                or not _same_objects(
                    proof.closure.classes.classes, current.closure.classes.classes
                )
                or not _same_objects(
                    tuple(step.fact for step in proof.closure.witness),
                    tuple(step.fact for step in current.closure.witness),
                )
            ):
                raise ValueError(
                    "DISTINCT ORDER FD proof must retain its exact property roots."
                )


def _domain_is_global(domain: ProjectPreservedRowDomainAuthority) -> bool:
    if isinstance(domain, ProjectIRProvidedIntrinsicGrain):
        return domain.state is ProjectGrainBasisState.GLOBAL
    if domain.kind is ProjectCompletedRowDomainKind.GLOBAL:
        return True
    if domain.kind is ProjectCompletedRowDomainKind.SET:
        origin = domain.set_origin
        if origin is None or origin.factor is not None:
            return False
        definition = origin.witness.owner.definition
        assert isinstance(definition, SetRelationDef)
        domains = (
            origin.input_domains
            if definition.body.kind is SetOperationKind.INTERSECT
            else origin.input_domains[:1]
        )
        return any(
            _domain_is_global(cast(ProjectPreservedRowDomainAuthority, item))
            for item in domains
        )
    return domain.preserved is not None and _domain_is_global(domain.preserved)


def _distinct_global_input(
    root: ProjectFinalOutputRoot, domain: ProjectCompletedRowDomain
) -> bool:
    if _domain_is_global(domain):
        return True
    if (
        isinstance(root, ProjectConcreteNoJoinReplay)
        and root.mode is ProjectJoinedAggregationMode.ABSENT
    ):
        upstream = root.upstream_entry
        if isinstance(upstream, ProjectCompletedEffectiveOutput):
            return upstream.limit is not None and upstream.limit.value <= 1
        if isinstance(upstream, ProjectExistingEffectiveOutput) and isinstance(
            upstream.owner.definition, (TableDef, QueryDef)
        ):
            bound = _relation_limit(upstream.owner)
            operators = tuple(
                operator
                for operator in upstream.fragment.logical_stage.operators
                if operator.kind is ProjectIRLogicalOperatorKind.LIMIT
                and operator.node is upstream.fragment.root
            )
            return (
                isinstance(bound, ProjectRelationLimit)
                and bound.value <= 1
                and len(operators) == 1
            )
    return False


def _distinct_source_targets(source) -> tuple[object, ...] | None:
    """Read retained scalar/group/window references; never infer inverse expressions."""
    if isinstance(source, ProjectConcreteJoinedNamespaceExpression):
        return tuple(resolution.target for resolution in source.resolutions)
    if isinstance(source, ProjectNoJoinScalarExpression):
        targets: list[object] = []
        for leaf in scalar_field_reference_leaves(source.expression):
            name = leaf.name if isinstance(leaf, NameExpr) else leaf.parts[-1]
            target = (
                source.let_scope.binding_expressions.get(name)
                if isinstance(leaf, NameExpr) and name in source.let_scope.value_types
                else source.input_schema.fields.get(name)
            )
            if target is None:
                return None
            targets.append(target)
        return tuple(targets)
    if isinstance(source, ProjectJoinedWindowInputBinding):
        return (source.stage_output,) if source.stage_output is not None else None
    if isinstance(source, ProjectModuleClauseDependencyFact):
        return source.target_occurrences
    if isinstance(source, ProjectNoJoinGroupedOutput):
        return (source.select_fact.item,)
    return (source,)


def _distinct_ordering(
    root: ProjectFinalOutputRoot,
    fields: tuple[ProjectCompletedOutputField, ...],
    ordering: ProjectRelationOrdering | None,
) -> tuple[tuple[object, ...], ProjectNonConcreteRelationOrdering | None]:
    if ordering is None:
        return (), None
    visible: list[object] = []
    for selected in fields:
        source = selected.source
        # A projected expression proves its result only, not its free inputs.
        if isinstance(
            source,
            (ProjectNoJoinScalarExpression, ProjectConcreteJoinedNamespaceExpression),
        ) and not isinstance(source.expression, (NameExpr, DottedNameExpr)):
            continue
        targets = _distinct_source_targets(source)
        if targets is not None:
            visible.extend(targets)
    if isinstance(root, ProjectConcreteJoinedQualify):
        properties = root.window_stage.input_aggregation.input_filter.joined_semantics.property_bridge.relational
    elif isinstance(root.upstream_entry, ProjectExistingEffectiveOutput):
        properties = root.upstream_entry.properties
    else:
        properties = None

    def value_class(target):
        if properties is None:
            return None
        matches = tuple(
            group
            for group in properties.value_classes
            if any(
                (
                    isinstance(target, ProjectScalarEnvironmentField)
                    and target.position == member.field_position
                )
                or target is member.evidence
                for member in group.members
            )
        )
        return matches[0] if len(matches) == 1 else None

    proofs: list[object] = []
    for item in ordering.items:
        targets = _distinct_source_targets(item.source)
        if targets is not None and all(
            any(target is value for value in visible) for target in targets
        ):
            proofs.append((item, tuple(visible), targets))
            continue
        if properties is not None and targets is not None:
            seed_classes = tuple(value_class(value) for value in visible)
            requested_classes = tuple(value_class(value) for value in targets)
            if all(value is not None for value in requested_classes):
                index = properties.fd_index
                proof = strictly_determines_output(
                    index,
                    ProjectIROutputValueClassSet(
                        index=index,
                        classes=tuple(
                            value
                            for value in index.universe
                            if any(value is seed for seed in seed_classes)
                        ),
                    ),
                    ProjectIROutputValueClassSet(
                        index=index,
                        classes=tuple(
                            value
                            for value in index.universe
                            if any(value is target for target in requested_classes)
                        ),
                    ),
                )
                if proof.status is ProjectIROutputDeterminationStatus.PROVEN:
                    proofs.append((item, proof))
                    continue
        span = item.expression.span
        diagnostic = Diagnostic(
            code="PIE-S2340",
            severity=Severity.ERROR,
            message="DISTINCT ORDER value is not proved determined by the complete visible row; selecting a hidden representative is unsupported.",
            location=SourceLocation(
                path=span.path,
                line=span.line,
                column=span.column,
                end_line=span.end_line,
                end_column=span.end_column,
            ),
        )
        return (), ProjectNonConcreteRelationOrdering(
            owner=ordering.owner,
            clause=ordering.clause,
            reason=ProjectRelationOrderingNonConcreteReason.DISTINCT_ORDER_NOT_DETERMINED,
            blocker=item,
            diagnostics=(diagnostic,),
        )
    return tuple(proofs), None


def _finish_completed_output(
    *,
    completion: ProjectCompletion,
    owner: ProjectDeclarationOccurrence,
    base_entry: ProjectEffectiveOutputEntry,
    root: ProjectFinalOutputRoot,
    fields: tuple[ProjectCompletedOutputField, ...],
    schema: ProjectRowSchema,
    row_domain: ProjectCompletedRowDomain,
    ordering: ProjectRelationOrdering | None,
    limit: ProjectRelationLimit | None,
    dependencies: tuple[ProjectCompletionDependency, ...],
) -> ProjectCompletedEffectiveOutput | ProjectEffectiveOutputCompletionTerminal:
    sources = tuple(_selected_type_sources(root, selected) for selected in fields)
    if any(sources):
        fields = tuple(
            replace(selected, type_sources=parents)
            for selected, parents in zip(fields, sources, strict=True)
        )
    clause = _derived_definition(owner).distinct_clause
    if clause is not None:
        _validate_distinct_projection(root, fields)
        equivalence = ProjectRowEquivalence(
            fields=fields,
            types=completion.plan.attribution._authority.type_source_resolutions,
        )
        if not equivalence.supported:
            failure = ProjectDistinctUnsupported(equivalence=equivalence)
            if isinstance(root, ProjectConcreteJoinedQualify):
                return _terminal(
                    base_entry=base_entry,
                    reason=ProjectEffectiveOutputCompletionTerminalReason.DISTINCT_NON_CONCRETE,
                    blocker=failure,
                    diagnostics=failure.diagnostics,
                    joined_qualify=root,
                )
            return _no_join_terminal(
                semantic_facts=root.semantic_facts,
                base_entry=base_entry,
                upstream_entry=root.upstream_entry,
                reason=ProjectEffectiveOutputCompletionTerminalReason.DISTINCT_NON_CONCRETE,
                blocker=failure,
                diagnostics=failure.diagnostics,
            )
        order_proofs, order_failure = _distinct_ordering(root, fields, ordering)
        if order_failure is not None:
            if isinstance(root, ProjectConcreteJoinedQualify):
                return _terminal(
                    base_entry=base_entry,
                    reason=ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE,
                    blocker=order_failure,
                    diagnostics=order_failure.diagnostics,
                    joined_qualify=root,
                )
            return _no_join_terminal(
                semantic_facts=root.semantic_facts,
                base_entry=base_entry,
                upstream_entry=root.upstream_entry,
                reason=ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE,
                blocker=order_failure,
                diagnostics=order_failure.diagnostics,
            )
        distinct = ProjectDistinct(
            owner=owner,
            clause=clause,
            root=root,
            fields=fields,
            types=equivalence.types,
            ordering=ordering,
            order_proofs=order_proofs,
            input_domain=row_domain,
            global_input=_distinct_global_input(root, row_domain),
        )
        row_domain = ProjectCompletedRowDomain(
            kind=ProjectCompletedRowDomainKind.GLOBAL
            if distinct.global_input
            else ProjectCompletedRowDomainKind.DISTINCT,
            distinct=distinct,
        )
    return ProjectCompletedEffectiveOutput(
        owner=owner,
        base_entry=base_entry,
        root=root,
        fields=fields,
        schema=schema,
        row_domain=row_domain,
        ordering=ordering,
        limit=limit,
        dependencies=dependencies,
    )


def _complete_set_output(
    completion: ProjectCompletion,
    base_entry: ProjectEffectiveOutputEntry,
    available: tuple[ProjectEffectiveOutputCompletionEntry, ...],
    current: _CurrentJoinBuild | None = None,
) -> ProjectCompletedSetOutput | ProjectEffectiveOutputCompletionTerminal:
    scope = ProjectSetInputScope(
        completion=completion, base_entry=base_entry, available=available
    )
    definition = base_entry.owner.definition
    assert isinstance(definition, SetRelationDef)
    body = definition.body

    def failed(
        reason: ProjectSetFailureReason,
        blockers: tuple[object, ...],
        diagnostics: tuple[Diagnostic, ...],
    ):
        failure = ProjectSetFailure(
            scope=scope, reason=reason, blockers=blockers, diagnostics=diagnostics
        )
        return _terminal(
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.SET_NON_CONCRETE,
            blocker=failure,
            diagnostics=failure.diagnostics,
        )

    environment = scope.references[0].environment
    owner_symbols = environment.find_relation_name(definition.name)
    if (
        len(owner_symbols) != 1
        or owner_symbols[0].target_occurrence is not base_entry.owner
    ):
        issues = tuple(
            issue for issue in environment.issues if issue.local_name == definition.name
        )
        owner_diagnostics = tuple(
            d
            for issue in issues
            for d in (
                (issue.diagnostic,)
                if issue.diagnostic is not None
                else issue.suppressing_diagnostics
            )
        )
        return failed(
            ProjectSetFailureReason.INPUT_UNAVAILABLE, issues, owner_diagnostics
        )
    if body.quantifier is None or len(body.operands) < 2:
        reason = (
            ProjectSetFailureReason.QUANTIFIER_REQUIRED
            if body.quantifier is None
            else ProjectSetFailureReason.OPERAND_ARITY
        )
        return failed(
            reason,
            (body,),
            (
                set_diagnostic(
                    scope,
                    "PIE-S2341",
                    "Set operations require explicit ALL/DISTINCT and at least two authored operands.",
                ),
            ),
        )
    uses: list[ProjectSetOperandUse] = []
    blockers: list[object] = []
    diagnostics: list[Diagnostic] = []
    for resolution in scope.references:
        target = resolution.target_symbol
        ordinal = resolution.reference.operand_ordinal
        if target is None:
            blockers.append(resolution)
            diagnostics.extend(resolution.diagnostics)
            continue
        entries = tuple(e for e in available if e.owner is target.target_occurrence)
        if len(entries) != 1 or not isinstance(
            entries[0],
            (
                ProjectExistingEffectiveOutput,
                ProjectCompletedEffectiveOutput,
                ProjectCompletedSetOutput,
            ),
        ):
            blockers.extend(entries or (resolution,))
            diagnostics.append(
                set_diagnostic(
                    scope,
                    "PIE-S2342",
                    f"Set operand {ordinal + 1} has no concrete completed output.",
                    ordinal,
                )
            )
            continue
        entry = entries[0]
        dependencies = tuple(
            d for d in base_entry.dependencies if d.evidence is resolution
        )
        if len(dependencies) != 1:
            raise ValueError(
                "Set operand must have one exact pre-scheduling dependency."
            )
        authority = (
            current.provider(entry)
            if current is not None
            else ProjectEffectiveJoinInputAuthority(completion=completion, entry=entry)
        )
        uses.append(
            ProjectSetOperandUse(
                scope=scope,
                resolution=resolution,
                dependency=dependencies[0],
                authority=authority,
            )
        )
    if blockers:
        return failed(
            ProjectSetFailureReason.INPUT_UNAVAILABLE,
            tuple(blockers),
            tuple(diagnostics),
        )
    widths = tuple(len(use.fields) for use in uses)
    if len(set(widths)) != 1:
        return failed(
            ProjectSetFailureReason.WIDTH_MISMATCH,
            tuple(uses),
            (
                set_diagnostic(
                    scope, "PIE-S2342", f"Set operand widths differ: {widths}."
                ),
            ),
        )
    for operand, use in enumerate(uses):
        for position, (first, other) in enumerate(
            zip(uses[0].fields, use.fields, strict=True)
        ):
            if not compatible_row_types(first, other):
                blockers.extend((first, other))
                diagnostics.append(
                    set_diagnostic(
                        scope,
                        "PIE-S2343",
                        f"Set operand {operand + 1}, field {position + 1} requires exact compatible types and validated identical Decimal precision/scale.",
                        operand,
                    )
                )
    if blockers:
        return failed(
            ProjectSetFailureReason.TYPE_MISMATCH, tuple(blockers), tuple(diagnostics)
        )
    if (
        body.kind is not SetOperationKind.UNION
        or body.quantifier is SetOperationQuantifier.DISTINCT
    ):
        for operand, use in enumerate(uses):
            for position, fact in enumerate(use.fields):
                if fact.reason is not None:
                    blockers.append(fact)
                    diagnostics.append(
                        set_diagnostic(
                            scope,
                            "PIE-S2344",
                            f"Set operand {operand + 1}, field {position + 1} of type '{fact.selected.field.resolved_type.name}' lacks required row equivalence: {fact.reason.value}.",
                            operand,
                        )
                    )
    if blockers:
        return failed(
            ProjectSetFailureReason.EQUIVALENCE_UNSUPPORTED,
            tuple(blockers),
            tuple(diagnostics),
        )
    return ProjectCompletedSetOutput(
        root=ProjectSetOperation(scope=scope, uses=tuple(uses))
    )


def _complete_joined_output(
    *,
    completion: ProjectCompletion,
    base_entry: ProjectEffectiveOutputTerminal,
    result: ProjectJoinedQualifyResult,
) -> ProjectCompletedEffectiveOutput | ProjectEffectiveOutputCompletionTerminal:
    if type(result) is ProjectNonConcreteJoinedQualify:
        return _terminal(
            base_entry=base_entry,
            reason=(
                ProjectEffectiveOutputCompletionTerminalReason.JOINED_QUALIFY_NON_CONCRETE
            ),
            blocker=result,
            diagnostics=result.diagnostics,
            joined_qualify=result,
        )
    if type(result) is not ProjectConcreteJoinedQualify:
        raise TypeError("Joined completion requires one exact Slice-11 variant.")
    owner = base_entry.owner
    definition = _derived_definition(owner)
    names, name_diagnostics = _output_names(definition)
    if names is None:
        return _terminal(
            base_entry=base_entry,
            reason=(
                ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
            ),
            blocker=definition.select_items,
            diagnostics=name_diagnostics,
            joined_qualify=result,
        )
    fields, blocker, diagnostics = _joined_final_fields(
        completion=completion,
        result=result,
        names=names,
    )
    if fields is None:
        return _terminal(
            base_entry=base_entry,
            reason=(
                ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
            ),
            blocker=blocker,
            diagnostics=diagnostics,
            joined_qualify=result,
        )
    ordering = _joined_relation_ordering(result)
    if type(ordering) is ProjectNonConcreteRelationOrdering:
        return _terminal(
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE,
            blocker=ordering,
            diagnostics=ordering.diagnostics,
            joined_qualify=result,
        )
    limit = _relation_limit(owner)
    if type(limit) is ProjectNonConcreteRelationLimit:
        return _terminal(
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.LIMIT_NON_CONCRETE,
            blocker=limit,
            diagnostics=limit.diagnostics,
            joined_qualify=result,
        )
    schema = ProjectRowSchema(
        fields={output.output_name: output.field for output in fields}
    )
    return _finish_completed_output(
        completion=completion,
        owner=owner,
        base_entry=base_entry,
        root=result,
        fields=fields,
        schema=schema,
        row_domain=_joined_row_domain(result),
        ordering=cast(ProjectRelationOrdering | None, ordering),
        limit=cast(ProjectRelationLimit | None, limit),
        dependencies=base_entry.dependencies,
    )


def _complete_no_join_output(
    *,
    completion: ProjectCompletion,
    base_entry: ProjectEffectiveOutputEntry,
    upstream_entry: ProjectConcreteEffectiveOutputEntry,
) -> ProjectCompletedEffectiveOutput | ProjectEffectiveOutputCompletionTerminal:
    owner = base_entry.owner
    definition = _derived_definition(owner)
    if definition.join_clauses:
        raise ValueError("Effective no-JOIN replay cannot reopen authored JOIN.")
    semantic = _semantic_facts(completion, owner)
    resolution = semantic.resolution
    if (
        resolution is None
        or len(base_entry.dependencies) != 1
        or (
            base_entry.dependencies[0].evidence is not resolution
            or base_entry.dependencies[0].target is not upstream_entry.owner
        )
    ):
        raise ValueError("No-JOIN replay requires one exact retained dependency.")
    names, name_diagnostics = _output_names(definition)
    if names is None:
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=(
                ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
            ),
            blocker=definition.select_items,
            diagnostics=name_diagnostics,
            upstream_entry=upstream_entry,
        )
    input_schema = _entry_schema(upstream_entry)
    upstream_definition = resolution.target_symbol.target_occurrence.definition
    if type(upstream_definition) not in {SourceDef, TableDef, QueryDef, SetRelationDef}:
        raise TypeError("No-JOIN replay upstream must produce rows.")
    let_scope = build_project_relation_let_scope_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_definition=cast(
            SourceDef | TableDef | QueryDef | SetRelationDef, upstream_definition
        ),
    )
    if let_scope.status not in {
        ProjectLetScopeFactsStatus.ABSENT,
        ProjectLetScopeFactsStatus.CONCRETE,
    }:
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.LET_NON_CONCRETE,
            blocker=let_scope,
            upstream_entry=upstream_entry,
        )
    where = _no_join_where(
        owner=owner,
        input_schema=input_schema,
        let_scope=let_scope,
    )
    if type(where) is ProjectNoJoinScalarExpression:
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.WHERE_NON_CONCRETE,
            blocker=where,
            diagnostics=where.diagnostics,
            upstream_entry=upstream_entry,
        )
    if type(where) is not ProjectConcreteNoJoinWhere:
        raise AssertionError("No-JOIN WHERE lost its exact result variant.")

    upstream_symbol = _project_symbol_for_resolution(resolution)
    mode = _mode(definition)
    limit = _relation_limit(owner)
    aggregate_readiness: ProjectAggregateGroupedClauseReadiness | None = None
    if mode is ProjectJoinedAggregationMode.ABSENT:
        schema_result = _project_direct_relation_row_schema(
            definition,
            source_schema=input_schema,
            source_symbol=upstream_symbol,
            upstream_definition=cast(
                SourceDef | TableDef | QueryDef | SetRelationDef,
                upstream_definition,
            ),
            fallback_path=owner.identity.module_path,
            let_scope_facts=let_scope,
        )
        base_state = _project_relation_row_schema_state_from_result(
            schema_result,
            concrete_reason=(
                ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
                if type(upstream_definition) is SourceDef
                else ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
            ),
        )
        if base_state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
            return _no_join_terminal(
                semantic_facts=semantic,
                base_entry=base_entry,
                reason=(
                    ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
                ),
                blocker=base_state,
                diagnostics=schema_result.diagnostics,
                upstream_entry=upstream_entry,
            )
        aggregate_result_facts = ()
    else:
        aggregate_readiness = build_project_aggregate_grouped_clause_readiness(
            definition=definition,
            input_schema=input_schema,
            upstream_symbol=upstream_symbol,
            fallback_path=owner.identity.module_path,
            let_scope_facts=let_scope,
        )
        base_state = aggregate_readiness.finalization.state
        if (
            base_state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or (
                definition.satisfying_clause is not None
                and aggregate_readiness.status
                is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
            )
            or (
                aggregate_readiness.status
                is not ProjectAggregateGroupedClauseReadinessStatus.CONCRETE
                and definition.order_by_clause is None
                and type(limit) is not ProjectNonConcreteRelationLimit
            )
        ):
            return _no_join_terminal(
                semantic_facts=semantic,
                base_entry=base_entry,
                reason=(
                    ProjectEffectiveOutputCompletionTerminalReason.AGGREGATION_NON_CONCRETE
                ),
                blocker=aggregate_readiness,
                upstream_entry=upstream_entry,
            )
        aggregate_result_facts = tuple(
            fact
            for item in definition.select_items
            if type(item.expression) is not WindowExpr
            if (name := _projection_output_name(item)) is not None
            and (
                fact := aggregate_readiness.finalization.aggregate_result_facts.get(
                    name
                )
            )
            is not None
        )
    base_schema = base_state.schema
    if base_schema is None or base_schema.is_unknown:
        raise AssertionError("Concrete replay base state lost its schema.")

    selected_window_items = tuple(
        item for item in definition.select_items if type(item.expression) is WindowExpr
    )
    if mode is ProjectJoinedAggregationMode.GLOBAL and selected_window_items:
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.WINDOW_NON_CONCRETE,
            blocker=selected_window_items,
            upstream_entry=upstream_entry,
        )
    named = semantic.named_window_namespace
    if type(named) is NamedWindowResolutionFailure:
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.WINDOW_NON_CONCRETE,
            blocker=named,
            upstream_entry=upstream_entry,
        )
    window_state, window_outputs = _window_output_facts(
        owner=owner,
        definition=definition,
        input_schema=input_schema,
        upstream_symbol=upstream_symbol,
        let_scope=let_scope,
        base_state=base_state,
        capabilities=completion.plan.semantic_facts.capabilities,
        named_window_namespace=(
            named if type(named) is ResolvedNamedWindowNamespace else None
        ),
    )
    if window_state.status is not ProjectRelationRowSchemaStatus.CONCRETE or any(
        output.status is not ProjectModuleCandidateBucketStatus.CONCRETE
        for output in window_outputs
    ):
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.WINDOW_NON_CONCRETE,
            blocker=window_outputs,
            diagnostics=tuple(
                diagnostic
                for output in window_outputs
                for diagnostic in output.diagnostics
            ),
            upstream_entry=upstream_entry,
        )
    window_scope = _no_join_window_scope(
        definition=definition,
        input_schema=input_schema,
        let_scope=let_scope,
        mode=mode,
        base_schema=base_schema,
    )
    clause_dependencies = _clause_dependency_facts(
        owner=owner,
        definition=definition,
        input_schema=input_schema,
        group_input_status=ProjectModuleCandidateBucketStatus.CONCRETE,
        state=base_state,
        grouped_order_state=window_state,
        let_scope=let_scope,
        aggregate_result_facts=aggregate_result_facts,
    )
    qualify = _no_join_qualify(
        owner=owner,
        mode=mode,
        scope=window_scope,
        selected_windows=window_outputs,
    )
    if not qualify.concrete:
        predicate = qualify.predicate
        if predicate is None:
            raise AssertionError("Authored replay QUALIFY lost its predicate result.")
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.QUALIFY_NON_CONCRETE,
            blocker=qualify,
            diagnostics=predicate.diagnostics,
            upstream_entry=upstream_entry,
        )
    fields, blocker, diagnostics = _no_join_final_fields(
        completion=completion,
        owner=owner,
        input_schema=input_schema,
        let_scope=let_scope,
        mode=mode,
        aggregate_readiness=aggregate_readiness,
        base_schema=base_schema,
        window_outputs=window_outputs,
        names=names,
    )
    if fields is None:
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=(
                ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE
            ),
            blocker=blocker,
            diagnostics=diagnostics,
            upstream_entry=upstream_entry,
        )
    ordering = _no_join_relation_ordering(
        owner=owner,
        input_schema=input_schema,
        let_scope=let_scope,
        mode=mode,
        clause_dependencies=clause_dependencies,
        window_outputs=window_outputs,
    )
    if type(ordering) is ProjectNonConcreteRelationOrdering:
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE,
            blocker=ordering,
            diagnostics=ordering.diagnostics,
            upstream_entry=upstream_entry,
        )
    if type(limit) is ProjectNonConcreteRelationLimit:
        return _no_join_terminal(
            semantic_facts=semantic,
            base_entry=base_entry,
            reason=ProjectEffectiveOutputCompletionTerminalReason.LIMIT_NON_CONCRETE,
            blocker=limit,
            diagnostics=limit.diagnostics,
            upstream_entry=upstream_entry,
        )
    replay_root = ProjectNoJoinReplayRoot(
        owner=owner,
        base_entry=base_entry,
        upstream_entry=upstream_entry,
        semantic_facts=semantic,
    )
    replay = ProjectConcreteNoJoinReplay(
        owner=owner,
        replay_root=replay_root,
        base_entry=base_entry,
        upstream_entry=upstream_entry,
        semantic_facts=semantic,
        input_schema=input_schema,
        let_scope=let_scope,
        where=where,
        mode=mode,
        aggregate_readiness=aggregate_readiness,
        base_state=base_state,
        window_state=window_state,
        window_outputs=window_outputs,
        window_scope=window_scope,
        clause_dependencies=clause_dependencies,
        qualify=qualify,
    )
    schema = ProjectRowSchema(
        fields={output.output_name: output.field for output in fields}
    )
    return _finish_completed_output(
        completion=completion,
        owner=owner,
        base_entry=base_entry,
        root=replay,
        fields=fields,
        schema=schema,
        row_domain=_no_join_row_domain(
            upstream_entry=upstream_entry,
            mode=mode,
            readiness=aggregate_readiness,
        ),
        ordering=cast(ProjectRelationOrdering | None, ordering),
        limit=cast(ProjectRelationLimit | None, limit),
        dependencies=base_entry.dependencies,
    )


def _joined_result_owner(
    result: ProjectJoinedQualifyResult,
) -> ProjectDeclarationOccurrence:
    return result.window_stage.input_aggregation.input_filter.entry.owner


def _current_region_for_result(
    result: ProjectJoinedQualifyResult,
) -> ProjectCurrentJoinRegion | None:
    source = (
        result.window_stage.input_aggregation.input_filter.joined_semantics.row_source
    )
    return source.region if type(source) is ProjectCurrentJoinedRowSource else None


def _validate_current_terminal(
    terminal: ProjectEffectiveOutputCompletionTerminal,
) -> None:
    region = terminal.current_region
    if (
        type(region) is not ProjectCurrentJoinRegion
        or region.ledger.owner is not terminal.owner
        or type(terminal.base_entry) is not ProjectEffectiveOutputTerminal
        or terminal.base_entry.cycle_blocker is not None
        or terminal.replay_root is not None
        or terminal.upstream_entry is not None
    ):
        raise ValueError("Current terminal requires exact local JOIN authority.")
    result = terminal.joined_qualify
    if result is None:
        blocker = terminal.blocker
        if (
            terminal.reason
            is not ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_TAIL_NON_CONCRETE
            or type(blocker) is not ProjectNonConcreteJoinedRowSemantics
        ):
            raise ValueError("Current readiness terminal requires its exact blocker.")
        source = blocker.namespaces.binding_environment.row_source
        if (
            type(source) is not ProjectCurrentJoinedRowSource
            or source.region is not region
        ):
            raise ValueError("Current readiness blocker lost exact JOIN membership.")
    elif _current_region_for_result(result) is not region:
        raise ValueError("Current terminal cannot substitute an alternate tail root.")
    elif (
        terminal.reason
        is ProjectEffectiveOutputCompletionTerminalReason.JOINED_QUALIFY_NON_CONCRETE
    ):
        if (
            type(result) is not ProjectNonConcreteJoinedQualify
            or terminal.blocker is not result
        ):
            raise ValueError("Current terminal must retain its exact QUALIFY blocker.")
    elif type(result) is not ProjectConcreteJoinedQualify or terminal.reason not in {
        ProjectEffectiveOutputCompletionTerminalReason.DISTINCT_NON_CONCRETE,
        ProjectEffectiveOutputCompletionTerminalReason.PROJECTION_NON_CONCRETE,
        ProjectEffectiveOutputCompletionTerminalReason.ORDER_NON_CONCRETE,
        ProjectEffectiveOutputCompletionTerminalReason.LIMIT_NON_CONCRETE,
    }:
        raise ValueError(
            "Current terminal requires concrete tail evidence for finalization."
        )


def _validate_current_inventory(overlay: ProjectEffectiveOutputCompletion):
    historical = overlay.condition_authority
    if historical is None:
        if (
            overlay.current_regions
            or overlay.current_readiness
            or overlay.current_tails
            or overlay.input_scopes
            or overlay.allocation_events
            or overlay.operative_conditions is not None
        ):
            raise ValueError(
                "Current completion requires its exact condition authority."
            )
        return {}
    if historical.uses is not overlay.base.verification.root.join_regions.uses:
        raise ValueError(
            "Current completion roots must share exact historical authority."
        )
    operative = overlay.operative_conditions
    if operative is not historical and (
        type(operative) is not ProjectJoinConditionCompletion
        or operative.historical is not historical
    ):
        raise ValueError(
            "Current completion requires its exact operative condition tuple."
        )
    assert operative is not None
    scope_owners = tuple(scope.ledger.owner for scope in overlay.input_scopes)
    expected_scope_owners = tuple(
        owner
        for owner in overlay.schedule
        if any(owner is item for item in scope_owners)
    )
    if not _same_objects(scope_owners, expected_scope_owners):
        raise ValueError("Current input scopes require unique scheduled owner order.")
    entries = {id(entry.owner): entry for entry in overlay.entries}
    prefix = [entries[id(owner)] for owner in overlay.base.topology.blocked_owners]
    for owner in overlay.schedule:
        scopes = tuple(
            scope for scope in overlay.input_scopes if scope.ledger.owner is owner
        )
        if scopes:
            scope = scopes[0]
            if (
                scope.completion is not overlay.base
                or scope.uses is not historical.uses
                or not _same_objects(scope.available_entries, tuple(prefix))
            ):
                raise ValueError(
                    "Current input scope must retain the exact available prefix."
                )
            scope.__post_init__()
            for binding in scope.bindings:
                authority = binding.authority
                if authority is None:
                    continue
                if type(authority) is not ProjectEffectiveJoinInputAuthority:
                    raise TypeError(
                        "Current inputs require exact completed-entry adapters."
                    )
                authority.validate()
                original = authority.entry
                if isinstance(original, ProjectExistingEffectiveOutput):
                    valid = _same_objects(authority.fields, original.properties.fields)
                else:
                    valid = len(authority.fields) == len(original.fields) and all(
                        type(actual) is ProjectCurrentInputField
                        and actual.authority is authority
                        and actual.original is retained
                        and actual.evidence is retained.field
                        and actual.identity is retained.identity
                        and actual.field_position == position
                        for position, (actual, retained) in enumerate(
                            zip(authority.fields, original.fields, strict=True)
                        )
                    )
                if not valid:
                    raise ValueError(
                        "Current adapter fields cannot graft alternate producer evidence."
                    )
        prefix.append(entries[id(owner)])
    for condition in operative.entries:
        if condition.inputs is not None and not any(
            condition.inputs.scope is scope for scope in overlay.input_scopes
        ):
            raise ValueError("Operative condition lost its exact retained input scope.")
        if condition.inputs is not None:
            expected_prefix = tuple(
                item
                for item in operative.entries
                if item.ledger is condition.ledger
                and item.use.identity.join_position
                < condition.use.identity.join_position
            )
            if not _same_objects(condition.inputs.prefix, expected_prefix):
                raise ValueError(
                    "Operative condition cannot substitute an alternate prefix."
                )
    events = overlay.allocation_events
    event_regions = tuple(
        event for event in events if type(event) is ProjectCurrentJoinRegion
    )
    if not _same_objects(event_regions, overlay.current_regions) or len(
        overlay.current_regions
    ) != len(overlay.current_readiness):
        raise ValueError(
            "Current allocation ledger must retain every exact region once."
        )
    allocation = overlay.base.verification.root.join_regions.ending_allocation
    materialized: list[ProjectCurrentMaterializedInput] = []
    for event in events:
        if (
            type(event)
            not in {ProjectCurrentMaterializedInput, ProjectCurrentJoinRegion}
            or event.starting_allocation is not allocation
        ):
            raise ValueError(
                "Current allocations require exact contiguous construction roots."
            )
        allocation = event.ending_allocation
        if isinstance(event, ProjectCurrentMaterializedInput):
            if any(
                event.authority.entry is item.authority.entry for item in materialized
            ):
                raise ValueError(
                    "One current producer cannot have competing materializations."
                )
            materialized.append(event)
    for item in materialized:
        consumed = any(
            properties.output is item
            for region in overlay.current_regions
            for properties in region.input_properties
        ) or any(
            (other.incoming is not None and other.incoming.output is item)
            or any(parent.output is item for parent in other.set_inputs)
            for other in materialized
        )
        if not consumed:
            raise ValueError(
                "Current input materialization requires an exact consumer."
            )
    owners = tuple(region.ledger.owner for region in overlay.current_regions)
    expected = tuple(
        owner
        for owner in overlay.schedule
        if any(owner is current for current in owners)
    )
    if not _same_objects(owners, expected):
        raise ValueError("Current JOIN regions must retain complete scheduled order.")
    results = {}
    tails = iter(overlay.current_tails)
    for region, readiness in zip(
        overlay.current_regions, overlay.current_readiness, strict=True
    ):
        if (
            region.conditions is not historical
            or region.input_scope is None
            or not any(region.input_scope is scope for scope in overlay.input_scopes)
        ):
            raise ValueError(
                "Current JOIN region lost exact condition/input authority."
            )
        selected = tuple(
            item for item in operative.entries if item.ledger is region.ledger
        )
        if not _same_objects(region.operative, selected):
            raise ValueError("Current JOIN cannot consume stale condition readiness.")
        source = readiness.namespaces.binding_environment.row_source
        if (
            type(source) is not ProjectCurrentJoinedRowSource
            or source.region is not region
            or source.base_verification is not overlay.base.verification
        ):
            raise ValueError("Current readiness must retain its exact input region.")
        result = None
        if isinstance(readiness, ProjectConcreteJoinedRowSemantics):
            tail = next(tails, None)
            if tail is None or len(tail.results) != 1:
                raise ValueError(
                    "Current completion requires each exact local tail once."
                )
            filters = tail.window_set.aggregation_set.filter_set
            if (
                filters.completion is not overlay.base
                or filters.current_semantics is not readiness
            ):
                raise ValueError(
                    "Current tail cannot use foreign owner-local readiness."
                )
            result = tail.results[0]
        results[id(region.ledger.owner)] = (region, readiness, result)
    if next(tails, None) is not None:
        raise ValueError("Current completion cannot retain an unrelated tail.")
    return results


@dataclass(slots=True, kw_only=True)
class _CurrentJoinBuild:
    """Transient work state inside the existing completion schedule."""

    completion: ProjectCompletion
    conditions: ProjectJoinConditionSet
    allocation: ProjectIRAllocationState = field(init=False)
    providers: dict[int, ProjectEffectiveJoinInputAuthority] = field(
        default_factory=dict
    )
    materialized: dict[int, ProjectCurrentMaterializedInput] = field(
        default_factory=dict
    )
    operative: dict[int, ProjectJoinCondition] = field(init=False)
    scopes: list[ProjectCurrentJoinInputScope] = field(default_factory=list)
    events: list[ProjectCurrentMaterializedInput | ProjectCurrentJoinRegion] = field(
        default_factory=list
    )
    regions: list[ProjectCurrentJoinRegion] = field(default_factory=list)
    readiness: list[
        ProjectConcreteJoinedRowSemantics | ProjectNonConcreteJoinedRowSemantics
    ] = field(default_factory=list)
    tails: list[ProjectJoinedQualifySet] = field(default_factory=list)

    def __post_init__(self) -> None:
        if (
            self.conditions.uses
            is not self.completion.verification.root.join_regions.uses
        ):
            raise ValueError(
                "Current JOIN work requires exact completion/condition roots."
            )
        self.allocation = (
            self.completion.verification.root.join_regions.ending_allocation
        )
        self.operative = {id(item.use): item for item in self.conditions.entries}

    def provider(
        self, entry: ProjectConcreteEffectiveOutputEntry
    ) -> ProjectEffectiveJoinInputAuthority:
        key = id(entry)
        if key not in self.providers:
            self.providers[key] = ProjectEffectiveJoinInputAuthority(
                completion=self.completion, entry=entry
            )
        return self.providers[key]

    def materialize(
        self, authority: ProjectEffectiveJoinInputAuthority
    ) -> ProjectIROutputRelationalProperties:
        if authority.historical_properties is not None:
            return authority.historical_properties
        key = id(authority.entry)
        if key in self.materialized:
            result = self.materialized[key]
            if result.authority is not authority:
                raise ValueError(
                    "Current materialization cannot replace its exact producer."
                )
            return result.properties
        entry = authority.entry
        if not isinstance(
            entry, (ProjectCompletedEffectiveOutput, ProjectCompletedSetOutput)
        ):
            raise TypeError("Materialization requires a completed producer.")
        set_inputs = (
            tuple(self.materialize(use.authority) for use in entry.root.uses)
            if isinstance(entry, ProjectCompletedSetOutput)
            else ()
        )
        incoming = None
        if isinstance(entry.root, ProjectConcreteNoJoinReplay):
            incoming = self.materialize(self.provider(entry.root.upstream_entry))
        result = ProjectCurrentMaterializedInput(
            authority=authority,
            starting_allocation=self.allocation,
            incoming=incoming,
            set_inputs=set_inputs,
        )
        self.materialized[key] = result
        self.events.append(result)
        self.allocation = result.ending_allocation
        return result.properties

    def attempt(
        self,
        base_entry: ProjectEffectiveOutputTerminal,
        available: tuple[ProjectEffectiveOutputCompletionEntry, ...],
    ) -> ProjectEffectiveOutputCompletionEntry | None:
        ledgers = tuple(
            ledger
            for ledger in self.conditions.uses.ledgers
            if ledger.owner is base_entry.owner
        )
        if len(ledgers) != 1:
            return None
        ledger = ledgers[0]
        predicates = tuple(
            item for item in self.conditions.entries if item.ledger is ledger
        )
        by_owner = {id(entry.owner): entry for entry in available}
        changed_input = any(
            by_owner.get(id(dependency.target))
            is not self.completion.find_owner(dependency.target)[0]
            for dependency in base_entry.dependencies
        )
        if not changed_input and not any(
            item.use.clause.on_clause is not None
            or item.use.kind
            in {
                AuthoredJoinKind.CROSS,
                AuthoredJoinKind.RIGHT,
                AuthoredJoinKind.FULL,
                AuthoredJoinKind.SEMI,
                AuthoredJoinKind.ANTI,
            }
            for item in predicates
        ):
            return None
        bindings: list[ProjectCurrentBindingInput] = []
        for binding in ledger.bindings:
            dependencies = tuple(
                item for item in base_entry.dependencies if item.evidence is binding
            )
            if len(dependencies) != 1:
                bindings.append(
                    ProjectCurrentBindingInput(
                        binding=binding, dependency=None, blocker=binding
                    )
                )
                continue
            dependency = dependencies[0]
            source = by_owner.get(id(dependency.target))
            if source is None:
                raise ValueError(
                    "Scheduled current input lost its exact earlier producer."
                )
            if isinstance(
                source,
                (
                    ProjectExistingEffectiveOutput,
                    ProjectCompletedEffectiveOutput,
                    ProjectCompletedSetOutput,
                ),
            ):
                bindings.append(
                    ProjectCurrentBindingInput(
                        binding=binding,
                        dependency=dependency,
                        authority=self.provider(source),
                    )
                )
            else:
                bindings.append(
                    ProjectCurrentBindingInput(
                        binding=binding, dependency=dependency, blocker=source
                    )
                )
        scope = ProjectCurrentJoinInputScope(
            completion=self.completion,
            uses=self.conditions.uses,
            ledger=ledger,
            available_entries=available,
            bindings=tuple(bindings),
        )
        rebuilt: list[ProjectJoinCondition] = []
        for old in predicates:
            inputs = ProjectCurrentPreMatchInputs(
                scope=scope, use=old.use, prefix=tuple(rebuilt)
            )
            current = rebuild_project_join_condition(old, inputs)
            rebuilt.append(current)
            self.operative[id(old.use)] = current
        changed = any(
            current is not old for current, old in zip(rebuilt, predicates, strict=True)
        )
        unavailable = any(
            item.authority is None
            or item.binding.state is ProjectJoinUseState.AMBIGUOUS
            for item in bindings
        )
        supported = bool(rebuilt) and all(
            item.ready
            and (
                item.use.kind in {AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT}
                and item.mode in {"M1", "M2", "M3", "M4"}
                or item.use.kind is AuthoredJoinKind.CROSS
                and item.mode == "M5"
                or item.use.kind
                in {
                    AuthoredJoinKind.RIGHT,
                    AuthoredJoinKind.FULL,
                    AuthoredJoinKind.SEMI,
                    AuthoredJoinKind.ANTI,
                }
                and item.mode in {"M1", "M2", "M3", "M4"}
            )
            for item in rebuilt
        )
        if (
            changed
            or unavailable
            or supported
            or any(not item.ready for item in rebuilt)
        ):
            self.scopes.append(scope)
        if unavailable:
            return _terminal(
                base_entry=base_entry,
                reason=ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_INPUT_NON_CONCRETE,
                blocker=ProjectCurrentJoinInputFailure(scope=scope),
                current_inputs=scope,
                diagnostics=_semantic_facts(
                    self.completion, base_entry.owner
                ).helper_diagnostics,
            )
        failures = tuple(item for item in rebuilt if not item.ready)
        if failures:
            return _terminal(
                base_entry=base_entry,
                reason=ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_CONDITION_NON_CONCRETE,
                blocker=failures,
                current_inputs=scope,
                diagnostics=_semantic_facts(
                    self.completion, base_entry.owner
                ).helper_diagnostics,
            )
        if not supported:
            return base_entry
        properties: list[ProjectIROutputRelationalProperties] = []
        for item in bindings:
            authority = item.authority
            if type(authority) is not ProjectEffectiveJoinInputAuthority:
                raise TypeError(
                    "Current input requires its exact effective-output adapter."
                )
            properties.append(self.materialize(authority))
        region = ProjectCurrentJoinRegion(
            conditions=self.conditions,
            ledger=ledger,
            starting_allocation=self.allocation,
            input_scope=scope,
            input_properties=tuple(properties),
            operative=tuple(rebuilt),
        )
        self.events.append(region)
        self.regions.append(region)
        self.allocation = region.ending_allocation
        row_source = ProjectCurrentJoinedRowSource(
            base_verification=self.completion.verification, region=region
        )
        block = ProjectConcreteQueryBlock(
            compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
            owner_bridge=ProjectQueryBlockOwnerBridge(owner=base_entry.owner),
            row_source=row_source,
        )
        readiness = build_project_joined_completion(
            block, self.completion.plan.attribution
        )
        if not isinstance(
            readiness,
            (ProjectConcreteJoinedRowSemantics, ProjectNonConcreteJoinedRowSemantics),
        ):
            raise TypeError("Current row source lost its exact semantic result.")
        self.readiness.append(readiness)
        if isinstance(readiness, ProjectNonConcreteJoinedRowSemantics):
            return _terminal(
                base_entry=base_entry,
                reason=ProjectEffectiveOutputCompletionTerminalReason.CURRENT_JOIN_TAIL_NON_CONCRETE,
                blocker=readiness,
                current_region=region,
            )
        row_filter = build_project_joined_row_filter(
            self.completion, base_entry, current_semantics=readiness
        )
        filters = ProjectJoinedRowFilterSet(
            completion=self.completion,
            results=(row_filter,),
            current_semantics=readiness,
        )
        tail = build_project_joined_tail(filters)
        self.tails.append(tail)
        return _complete_joined_output(
            completion=self.completion, base_entry=base_entry, result=tail.results[0]
        )

    def condition_result(
        self,
    ) -> ProjectJoinConditionSet | ProjectJoinConditionCompletion:
        entries = tuple(
            self.operative[id(item.use)] for item in self.conditions.entries
        )
        if all(
            actual is old
            for actual, old in zip(entries, self.conditions.entries, strict=True)
        ):
            return self.conditions
        return ProjectJoinConditionCompletion(
            historical=self.conditions, entries=entries
        )


def build_project_effective_output_completion(
    completion: ProjectCompletion,
    joined_qualifies: ProjectJoinedQualifySet,
    *,
    join_conditions: ProjectJoinConditionSet | None = None,
) -> ProjectEffectiveOutputCompletion:
    """Complete recoverable outputs once in the exact Slice-7 schedule."""

    if (
        type(completion) is not ProjectCompletion
        or type(joined_qualifies) is not ProjectJoinedQualifySet
    ):
        raise TypeError("Effective-output completion requires exact Slice-7/11 roots.")
    if (
        joined_qualifies.window_set.aggregation_set.filter_set.completion
        is not completion
    ):
        raise ValueError("Effective-output completion roots must share one snapshot.")
    qualify_by_owner: dict[int, ProjectJoinedQualifyResult] = {}
    for result in joined_qualifies.results:
        owner = _joined_result_owner(result)
        if id(owner) in qualify_by_owner:
            raise ValueError("One joined owner cannot have multiple Slice-11 results.")
        qualify_by_owner[id(owner)] = result
    base_by_owner = {
        id(owner): entry
        for owner, entry in zip(
            completion.owners,
            completion.entries,
            strict=True,
        )
    }
    built_by_owner: dict[int, ProjectEffectiveOutputCompletionEntry] = {
        id(owner): base_by_owner[id(owner)]
        for owner in completion.topology.blocked_owners
    }
    replay_roots: list[ProjectNoJoinReplayRoot] = []
    current_state = (
        None
        if join_conditions is None
        else _CurrentJoinBuild(completion=completion, conditions=join_conditions)
    )
    required_current = {
        id(owner)
        for owner in completion.owners
        if isinstance(owner.definition, SetRelationDef)
        or isinstance(owner.definition, (TableDef, QueryDef))
        and owner.definition.distinct_clause is not None
    }
    if join_conditions is not None:
        required_current |= {
            id(item.use.owner)
            for item in join_conditions.entries
            if item.use.clause.on_clause is not None
            or item.use.kind
            in {
                AuthoredJoinKind.CROSS,
                AuthoredJoinKind.RIGHT,
                AuthoredJoinKind.FULL,
                AuthoredJoinKind.SEMI,
                AuthoredJoinKind.ANTI,
            }
        }
        for required_owner in reversed(completion.schedule):
            if id(required_owner) in required_current:
                required_current.update(
                    id(dependency.target)
                    for dependency in completion.dependencies
                    if dependency.consumer is required_owner
                )
    changed_current: set[int] = set()
    for owner in completion.schedule:
        base_entry = base_by_owner[id(owner)]
        definition = owner.definition
        current_needed = id(owner) in required_current or any(
            id(dependency.target) in changed_current
            for dependency in base_entry.dependencies
        )
        if isinstance(definition, SetRelationDef):
            entry = _complete_set_output(
                completion, base_entry, tuple(built_by_owner.values()), current_state
            )
            built_by_owner[id(owner)] = entry
            changed_current.add(id(owner))
            continue
        current = (
            current_state.attempt(base_entry, tuple(built_by_owner.values()))
            if type(base_entry) is ProjectEffectiveOutputTerminal
            and current_state is not None
            and current_needed
            else None
        )
        if current is not None:
            entry = current
        elif type(base_entry) is ProjectExistingEffectiveOutput:
            changed_upstream = (
                current_needed
                and len(base_entry.dependencies) == 1
                and built_by_owner[id(base_entry.dependencies[0].target)]
                is not base_by_owner[id(base_entry.dependencies[0].target)]
            )
            if (
                type(definition) not in {TableDef, QueryDef}
                or cast(
                    _DerivedRelation,
                    definition,
                ).qualify_clause
                is None
                and not changed_upstream
                and cast(_DerivedRelation, definition).distinct_clause is None
            ):
                entry: ProjectEffectiveOutputCompletionEntry = base_entry
            else:
                dependency = base_entry.dependencies
                if len(dependency) != 1:
                    raise ValueError("Historical QUALIFY replay requires one upstream.")
                upstream = built_by_owner[id(dependency[0].target)]
                if type(upstream) in {
                    ProjectExistingEffectiveOutput,
                    ProjectCompletedEffectiveOutput,
                    ProjectCompletedSetOutput,
                }:
                    entry = _complete_no_join_output(
                        completion=completion,
                        base_entry=base_entry,
                        upstream_entry=cast(
                            ProjectConcreteEffectiveOutputEntry, upstream
                        ),
                    )
                else:
                    entry = _terminal(
                        base_entry=base_entry,
                        reason=(
                            ProjectEffectiveOutputCompletionTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_NON_CONCRETE
                        ),
                        blocker=upstream,
                        upstream_entry=upstream,
                    )
        elif type(
            base_entry
        ) is ProjectEffectiveOutputTerminal and base_entry.reason is (
            ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
        ):
            result = qualify_by_owner.get(id(owner))
            if result is None:
                raise ValueError("Joined-tail completion requires one Slice-11 result.")
            entry = _complete_joined_output(
                completion=completion,
                base_entry=base_entry,
                result=result,
            )
        elif type(base_entry) is ProjectEffectiveOutputTerminal and (
            base_entry.reason
            is ProjectEffectiveOutputTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_PENDING
            or (
                current_needed
                and isinstance(definition, (TableDef, QueryDef))
                and not definition.join_clauses
                and len(base_entry.dependencies) == 1
                and base_entry.fragment.semantic_facts.resolution
                is base_entry.dependencies[0].evidence
                and (
                    definition.distinct_clause is not None
                    or built_by_owner[id(base_entry.dependencies[0].target)]
                    is not base_by_owner[id(base_entry.dependencies[0].target)]
                )
            )
        ):
            if len(base_entry.dependencies) != 1:
                raise ValueError(
                    "Pending no-JOIN output requires one exact dependency."
                )
            upstream = built_by_owner[id(base_entry.dependencies[0].target)]
            if type(upstream) in {
                ProjectExistingEffectiveOutput,
                ProjectCompletedEffectiveOutput,
                ProjectCompletedSetOutput,
            }:
                entry = _complete_no_join_output(
                    completion=completion,
                    base_entry=base_entry,
                    upstream_entry=cast(ProjectConcreteEffectiveOutputEntry, upstream),
                )
            else:
                entry = _terminal(
                    base_entry=base_entry,
                    reason=(
                        ProjectEffectiveOutputCompletionTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_NON_CONCRETE
                    ),
                    blocker=upstream,
                    upstream_entry=upstream,
                )
        else:
            entry = base_entry
        replay_root = _entry_replay_root(entry)
        if replay_root is not None:
            replay_roots.append(replay_root)
        built_by_owner[id(owner)] = entry
        if current_needed and entry is not base_entry:
            changed_current.add(id(owner))
    entries = tuple(built_by_owner[id(owner)] for owner in completion.owners)
    if set(qualify_by_owner) != {
        id(entry.owner)
        for entry in completion.entries
        if type(entry) is ProjectEffectiveOutputTerminal
        and entry.reason is ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
    }:
        raise ValueError("Slice-11 results must cover the exact joined-tail inventory.")
    return ProjectEffectiveOutputCompletion(
        base=completion,
        joined_qualifies=joined_qualifies,
        replay_roots=tuple(replay_roots),
        owners=completion.owners,
        dependencies=completion.dependencies,
        schedule=completion.schedule,
        entries=entries,
        current_regions=() if current_state is None else tuple(current_state.regions),
        current_readiness=()
        if current_state is None
        else tuple(current_state.readiness),
        current_tails=() if current_state is None else tuple(current_state.tails),
        condition_authority=join_conditions,
        operative_conditions=None
        if current_state is None
        else current_state.condition_result(),
        input_scopes=() if current_state is None else tuple(current_state.scopes),
        allocation_events=() if current_state is None else tuple(current_state.events),
    )


def _has_distinct(completed) -> bool:
    """Whether a completed root requires the deferred DISTINCT IR consumer."""
    return any(
        isinstance(owner.definition, (TableDef, QueryDef))
        and owner.definition.distinct_clause is not None
        for owner in completed.effective_outputs.owners
    )


def _has_set_outputs(completed) -> bool:
    return any(
        isinstance(owner.definition, SetRelationDef)
        for owner in completed.effective_outputs.owners
    )


def completed_set_admission_diagnostics(
    overlay: ProjectEffectiveOutputCompletion,
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    for entry in overlay.entries:
        if isinstance(entry, ProjectCompletedSetOutput):
            facts = _semantic_facts(overlay.base, entry.owner)
            if facts.helper_diagnostics != syntax_diagnostics(entry.owner.definition):
                raise ValueError(
                    "Set admission requires its exact owner-held temporary cause."
                )
            diagnostics.extend(facts.helper_diagnostics)
    return tuple(diagnostics)
