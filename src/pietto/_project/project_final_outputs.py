"""Private Phase-63 final semantic outputs and completion overlay."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
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
)
from pietto._project.project_ir_relational_properties import (
    ProjectIRProvidedIntrinsicGrain,
)
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
)
from pietto._project.project_joined_row_filter import (
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
)
from pietto._project.row_expression_schema import (
    _project_nullability,
    _project_resolved_type,
)
from pietto._project.row_expression_type_facts import (
    project_row_field_to_semantic_value_type,
    project_row_schema_to_semantic_row_schema,
)
from pietto.ast_nodes import (
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


class ProjectCompletedRowDomainKind(StrEnum):
    """Semantic result-row postures without a new normative grain graph."""

    PRESERVED = "preserved"
    GROUPED = "grouped"
    GLOBAL = "global"


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
            not in {ProjectExistingEffectiveOutput, ProjectCompletedEffectiveOutput}
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


class ProjectEffectiveOutputCompletionTerminalReason(StrEnum):
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
    ProjectExistingEffectiveOutput | ProjectCompletedEffectiveOutput
)
type ProjectEffectiveOutputCompletionEntry = (
    ProjectExistingEffectiveOutput
    | ProjectEffectiveOutputTerminal
    | ProjectCompletedEffectiveOutput
    | ProjectEffectiveOutputCompletionTerminal
)


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
    if type(entry) is ProjectCompletedEffectiveOutput:
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
    if type(entry) is ProjectCompletedEffectiveOutput:
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


def _validate_completed_output_root(output: ProjectCompletedEffectiveOutput) -> None:
    root = output.root
    if type(root) is ProjectConcreteJoinedQualify:
        aggregation = root.window_stage.input_aggregation
        mode = aggregation.mode
        valid_root = (
            aggregation.input_filter.entry.owner is output.owner
            and aggregation.input_filter.entry is output.base_entry
        )
        grouped_basis: tuple[object, ...] = aggregation.group_keys
        preserved = root.preservation.intrinsic_grain
    else:
        assert type(root) is ProjectConcreteNoJoinReplay
        mode = root.mode
        valid_root = root.owner is output.owner and root.base_entry is output.base_entry
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
            output.row_domain.kind is ProjectCompletedRowDomainKind.PRESERVED
            and output.row_domain.preserved is preserved
            and not output.row_domain.grouped_basis
        )
    elif mode is ProjectJoinedAggregationMode.GROUPED:
        valid_domain = (
            output.row_domain.kind is ProjectCompletedRowDomainKind.GROUPED
            and output.row_domain.preserved is None
            and _same_objects(output.row_domain.grouped_basis, grouped_basis)
        )
    else:
        valid_domain = (
            output.row_domain.kind is ProjectCompletedRowDomainKind.GLOBAL
            and output.row_domain.preserved is None
            and not output.row_domain.grouped_basis
        )
    if not valid_domain:
        raise ValueError("Completed output row domain must match its exact stage root.")
    _validate_completed_output_sources(output)


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
        identity=ProjectModuleRowFieldIdentity(
            owner=_declaration_identity(owner),
            kind=ProjectModuleRowFieldKind.RELATION_OUTPUT,
            field_position=ordinal,
            name=name,
        ),
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
) -> ProjectEffectiveOutputCompletionTerminal:
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
    return ProjectCompletedEffectiveOutput(
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
    if type(upstream_definition) not in {SourceDef, TableDef, QueryDef}:
        raise TypeError("No-JOIN replay upstream must produce rows.")
    let_scope = build_project_relation_let_scope_facts(
        definition=definition,
        input_schema=input_schema,
        upstream_definition=cast(SourceDef | TableDef | QueryDef, upstream_definition),
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
                SourceDef | TableDef | QueryDef,
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
    return ProjectCompletedEffectiveOutput(
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


def build_project_effective_output_completion(
    completion: ProjectCompletion,
    joined_qualifies: ProjectJoinedQualifySet,
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
    built_by_owner: dict[int, ProjectEffectiveOutputCompletionEntry] = {}
    replay_roots: list[ProjectNoJoinReplayRoot] = []
    for owner in completion.schedule:
        base_entry = base_by_owner[id(owner)]
        definition = owner.definition
        if type(base_entry) is ProjectExistingEffectiveOutput:
            if (
                type(definition) not in {TableDef, QueryDef}
                or cast(
                    _DerivedRelation,
                    definition,
                ).qualify_clause
                is None
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
        elif type(
            base_entry
        ) is ProjectEffectiveOutputTerminal and base_entry.reason is (
            ProjectEffectiveOutputTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_PENDING
        ):
            if len(base_entry.dependencies) != 1:
                raise ValueError(
                    "Pending no-JOIN output requires one exact dependency."
                )
            upstream = built_by_owner[id(base_entry.dependencies[0].target)]
            if type(upstream) in {
                ProjectExistingEffectiveOutput,
                ProjectCompletedEffectiveOutput,
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
    )
