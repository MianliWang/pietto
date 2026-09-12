"""Closed contextual row expressions and private stage-value transport."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from enum import StrEnum
from typing import TYPE_CHECKING

from pietto._project import project_sql_plan_aggregation as aggregation
from pietto._project import project_sql_plan_windows as windows
from pietto.ast_nodes import (
    Expression,
    LiteralExpr,
    NameExpr,
    DottedNameExpr,
    UnaryExpr,
    BinaryExpr,
    ComparisonExpr,
    IsNullExpr,
    BetweenExpr,
    CallExpr,
    LetBinding,
    SelectItem,
    WhereClause,
)
from pietto.ast_nodes import JoinOnClause
from pietto._project.project_join_conditions import (
    ProjectJoinCondition,
    ProjectJoinConditionReference,
)
from pietto._project.project_scalar_namespaces import (
    ProjectJoinedLetValue,
    ProjectJoinedLetOccurrence,
    ProjectJoinedScalarNamespace,
    ProjectConcreteJoinedNamespaceExpression,
    ProjectConcreteJoinedLetNamespaces,
    ProjectJoinedNamespaceReferenceResolution,
    ProjectJoinedLetReferenceResolution,
)
from pietto._project.project_scalar_references import ProjectScalarEnvironmentField
from pietto._project.project_scalar_bindings import (
    ProjectJoinedScalarBindingEnvironment,
)
from pietto._project.project_joined_qualify import ProjectConcreteJoinedQualify
from pietto._project.model import ProjectRowSchema, ProjectRowField
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleLetBindingFact,
    ProjectModuleSelectFact,
    ProjectModuleSelectExpressionFact,
    ProjectModuleWhereFact,
    ProjectModuleExpressionReferenceFact,
)
from pietto._project.project_final_outputs import (
    ProjectConcreteNoJoinReplay,
    ProjectNoJoinScalarExpression,
)
from pietto._project.project_query_block_ir import (
    ProjectIRConcreteQueryBlockEntry,
    ProjectIRReusedEffectiveOutput,
    ProjectIRReboundExistingOutput,
    ProjectIRCompletedQueryBlockOutput,
)
from pietto._project.project_joined_row_filter import ProjectJoinedRowRetentionEffect
from pietto.semantic.model import ValueType

if TYPE_CHECKING:
    from pietto._project.project_completed_semantics import (
        ProjectConcreteCompletedSemanticResult,
    )
    from pietto._project.project_sql_plan import ProjectSQLPlanRef, ProjectSQLSymbol

__all__: tuple[str, ...] = ()


type ProjectSQLOrdinaryEvidence = (
    ProjectModuleLetBindingFact
    | ProjectModuleSelectExpressionFact
    | ProjectModuleWhereFact
    | ProjectNoJoinScalarExpression
)
type ProjectSQLScalarEvidence = (
    ProjectSQLOrdinaryEvidence
    | ProjectJoinedLetValue
    | ProjectConcreteJoinedNamespaceExpression
    | ProjectJoinCondition
    | aggregation.Evidence
    | windows.Qualify
)


class ProjectSQLExpressionRole(StrEnum):
    MATCH = "match"
    LET = "let"
    WHERE = "where"
    SELECT = "select"
    AGGREGATE_ARGUMENT = "aggregate_argument"
    SATISFYING = "satisfying"
    QUALIFY = "qualify"


class ProjectSQLStageKind(StrEnum):
    LET = "let"
    WHERE = "where"
    PROJECTION = "projection"
    AGGREGATE = "aggregate"
    SATISFYING = "satisfying"
    WINDOW = "window"
    QUALIFY = "qualify"


class ProjectSQLStagePortKind(StrEnum):
    INPUT = "input"
    EXPORT = "export"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLExpressionSite:
    ref: ProjectSQLPlanRef
    owner: ProjectDeclarationOccurrence
    block: ProjectSQLPlanRef
    role: ProjectSQLExpressionRole
    ordinal: int
    occurrence: LetBinding | WhereClause | SelectItem
    input_schema: ProjectRowSchema
    let_scope: ProjectRelationLetScopeFacts
    let_prefix: tuple[LetBinding, ...]
    evidence: ProjectSQLScalarEvidence
    references: tuple[ProjectModuleExpressionReferenceFact, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLJoinedSite:
    ref: ProjectSQLPlanRef
    owner: ProjectDeclarationOccurrence
    block: ProjectSQLPlanRef
    role: ProjectSQLExpressionRole
    ordinal: int
    occurrence: LetBinding | WhereClause | SelectItem
    namespace: ProjectJoinedScalarNamespace
    evidence: ProjectJoinedLetValue | ProjectConcreteJoinedNamespaceExpression
    references: tuple[ProjectJoinedNamespaceReferenceResolution, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLMatchSite:
    ref: ProjectSQLPlanRef
    owner: ProjectDeclarationOccurrence
    block: ProjectSQLPlanRef
    role: ProjectSQLExpressionRole
    ordinal: int
    occurrence: JoinOnClause
    evidence: ProjectJoinCondition
    references: tuple[ProjectJoinConditionReference, ...]


type ProjectSQLSite = (
    ProjectSQLExpressionSite
    | ProjectSQLJoinedSite
    | ProjectSQLMatchSite
    | aggregation.ProjectSQLAggregateSite
    | windows.ProjectSQLQualifySite
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLExpressionBase:
    ref: ProjectSQLPlanRef
    site: ProjectSQLSite
    value_type: ValueType


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLLiteral(ProjectSQLExpressionBase):
    expression: LiteralExpr


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLReference(ProjectSQLExpressionBase):
    expression: NameExpr | DottedNameExpr
    reference: ProjectModuleExpressionReferenceFact
    port: ProjectSQLPlanRef
    symbol: ProjectSQLSymbol


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLJoinedReference(ProjectSQLExpressionBase):
    expression: NameExpr | DottedNameExpr
    reference: ProjectJoinedNamespaceReferenceResolution
    port: ProjectSQLPlanRef
    symbol: ProjectSQLSymbol


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLMatchReference(ProjectSQLExpressionBase):
    expression: NameExpr | DottedNameExpr
    reference: ProjectJoinConditionReference
    port: ProjectSQLPlanRef
    symbol: ProjectSQLSymbol


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLUnary(ProjectSQLExpressionBase):
    expression: UnaryExpr
    operand: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLBinary(ProjectSQLExpressionBase):
    expression: BinaryExpr
    left: ProjectSQLPlanRef
    right: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLComparison(ProjectSQLExpressionBase):
    expression: ComparisonExpr
    left: ProjectSQLPlanRef
    right: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLIsNull(ProjectSQLExpressionBase):
    expression: IsNullExpr
    value: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLBetween(ProjectSQLExpressionBase):
    expression: BetweenExpr
    value: ProjectSQLPlanRef
    lower: ProjectSQLPlanRef
    upper: ProjectSQLPlanRef


type ProjectSQLExpression = (
    ProjectSQLLiteral
    | ProjectSQLReference
    | ProjectSQLJoinedReference
    | ProjectSQLMatchReference
    | ProjectSQLUnary
    | ProjectSQLBinary
    | ProjectSQLComparison
    | ProjectSQLIsNull
    | ProjectSQLBetween
    | aggregation.ProjectSQLResultReference
    | windows.ProjectSQLWindowReference
    | aggregation.ProjectSQLAggregateArgumentCall
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLExpressionOperand:
    ref: ProjectSQLPlanRef
    site: ProjectSQLSite
    parent: ProjectSQLPlanRef
    position: int
    child: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLStagePort:
    """A private input/export occurrence; never a canonical field identity."""

    ref: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    kind: ProjectSQLStagePortKind
    key: (
        ProjectRowField
        | LetBinding
        | ProjectScalarEnvironmentField
        | ProjectJoinedLetOccurrence
        | aggregation.ResultKey
        | windows.Source
    )
    source: ProjectSQLPlanRef
    type_evidence: ProjectRowField | ValueType


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLStageContext:
    block: ProjectSQLPlanRef
    ports: tuple[ProjectSQLStagePort, ...]
    symbols: tuple[ProjectSQLSymbol, ...]
    _ports: Mapping[ProjectSQLPlanRef, ProjectSQLStagePort] = field(
        init=False, repr=False
    )
    _symbols: Mapping[ProjectSQLPlanRef, ProjectSQLSymbol] = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        ports = {p.ref: p for p in self.ports}
        symbols = {s.ref: s for s in self.symbols}
        if (
            len(ports) != len(self.ports)
            or len(symbols) != len(self.symbols)
            or len(symbols) != len(ports)
            or len({s.subject for s in self.symbols}) != len(ports)
            or any(p.block is not self.block for p in self.ports)
            or any(
                s.scope is not self.block or s.subject not in ports
                for s in self.symbols
            )
        ):
            raise ValueError("Stage context requires exact local ports and symbols.")
        object.__setattr__(self, "_ports", MappingProxyType(ports))
        object.__setattr__(self, "_symbols", MappingProxyType(symbols))

    def lookup(self, ref: ProjectSQLPlanRef) -> ProjectSQLStagePort:
        symbol = self._symbols.get(ref)
        port = self._ports.get(ref if symbol is None else symbol.subject)
        if (
            port is None
            or port.block is not self.block
            or (symbol is not None and symbol.scope is not self.block)
        ):
            raise ValueError("Reference is not a member of this SELECT-block scope.")
        return port


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLLetValue:
    ref: ProjectSQLPlanRef
    site: ProjectSQLExpressionSite | ProjectSQLJoinedSite
    expression: ProjectSQLPlanRef
    port: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLFilter:
    ref: ProjectSQLPlanRef
    site: (
        ProjectSQLExpressionSite
        | ProjectSQLJoinedSite
        | aggregation.ProjectSQLAggregateSite
        | windows.ProjectSQLQualifySite
        | windows.ProjectSQLQualifySite
    )
    predicate: ProjectSQLPlanRef
    retention_effects: tuple[ProjectJoinedRowRetentionEffect, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLExpressionDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    site: ProjectSQLSite
    expression: Expression
    value_type: ValueType
    operand_types: tuple[ValueType, ...]
    origin: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLStageValueDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    block: ProjectSQLPlanRef
    type_evidence: ProjectRowField | ValueType
    origin: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLFilterDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    site: (
        ProjectSQLExpressionSite
        | ProjectSQLJoinedSite
        | aggregation.ProjectSQLAggregateSite
        | windows.ProjectSQLQualifySite
        | windows.ProjectSQLQualifySite
    )
    value_type: ValueType
    retention_effects: tuple[ProjectJoinedRowRetentionEffect, ...]
    origin: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLScopeDemand:
    ref: ProjectSQLPlanRef
    subject: ProjectSQLPlanRef
    predecessor: ProjectSQLPlanRef
    inputs: tuple[ProjectSQLPlanRef, ...]
    exports: tuple[ProjectSQLPlanRef, ...]
    origin: ProjectSQLPlanRef


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLRowAuthority:
    """Invocation-local view of retained roots; no inference or allocation of values."""

    input_schema: ProjectRowSchema
    let_scope: ProjectRelationLetScopeFacts
    lets: tuple[ProjectModuleLetBindingFact, ...]
    selections: tuple[ProjectModuleSelectFact, ...]
    selected_evidence: tuple[
        ProjectModuleSelectExpressionFact | ProjectNoJoinScalarExpression | None, ...
    ]
    selected_references: tuple[tuple[ProjectModuleExpressionReferenceFact, ...], ...]
    where: ProjectModuleWhereFact | ProjectNoJoinScalarExpression | None
    where_references: tuple[ProjectModuleExpressionReferenceFact, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLJoinedRowAuthority:
    binding_environment: ProjectJoinedScalarBindingEnvironment
    namespaces: ProjectConcreteJoinedLetNamespaces
    lets: tuple[ProjectJoinedLetValue, ...]
    selections: tuple[ProjectModuleSelectFact, ...]
    selected_evidence: tuple[ProjectConcreteJoinedNamespaceExpression | None, ...]
    selected_references: tuple[
        tuple[ProjectJoinedNamespaceReferenceResolution, ...], ...
    ]
    where: ProjectConcreteJoinedNamespaceExpression | None
    where_references: tuple[ProjectJoinedNamespaceReferenceResolution, ...]


def row_authority(
    completed: ProjectConcreteCompletedSemanticResult,
    entry: ProjectIRConcreteQueryBlockEntry,
) -> ProjectSQLRowAuthority | ProjectSQLJoinedRowAuthority | None:
    if isinstance(
        entry, (ProjectIRReusedEffectiveOutput, ProjectIRReboundExistingOutput)
    ):
        facts = entry.semantic_entry.fragment.semantic_facts
        if (
            facts.input_state is None
            or facts.input_state.schema is None
            or facts.let_scope_facts is None
            or facts.let_scope_facts.input_state is not facts.input_state
            or len(facts.select_expressions) != len(facts.select_facts)
            or any(
                context.selection is not selection
                for context, selection in zip(
                    facts.select_expressions, facts.select_facts
                )
            )
        ):
            return None
        return ProjectSQLRowAuthority(
            input_schema=facts.input_state.schema,
            let_scope=facts.let_scope_facts,
            lets=facts.let_bindings,
            selections=facts.select_facts,
            selected_evidence=facts.select_expressions,
            selected_references=tuple(f.references for f in facts.select_facts),
            where=facts.where_fact,
            where_references=()
            if facts.where_fact is None
            else facts.where_fact.references,
        )
    if isinstance(entry, ProjectIRCompletedQueryBlockOutput) and isinstance(
        entry.semantic_entry.root, ProjectConcreteJoinedQualify
    ):
        semantic = entry.semantic_entry
        tail = entry.semantic_entry.root.window_stage.input_aggregation.input_filter
        namespaces = tail.joined_semantics.namespaces
        joined_selected: list[ProjectConcreteJoinedNamespaceExpression | None] = []
        for output in semantic.fields:
            if isinstance(output.source, ProjectConcreteJoinedNamespaceExpression):
                joined_selected.append(output.source)
            else:
                joined_selected.append(None)
        return ProjectSQLJoinedRowAuthority(
            binding_environment=namespaces.binding_environment,
            namespaces=namespaces,
            lets=namespaces.values,
            selections=tuple(f.select_fact for f in semantic.fields),
            selected_evidence=tuple(joined_selected),
            selected_references=tuple(
                () if value is None else value.resolutions for value in joined_selected
            ),
            where=tail.expression_analysis,
            where_references=()
            if tail.expression_analysis is None
            else tail.expression_analysis.resolutions,
        )
    if isinstance(entry, ProjectIRCompletedQueryBlockOutput) and isinstance(
        entry.semantic_entry.root, ProjectConcreteNoJoinReplay
    ):
        semantic = entry.semantic_entry
        root = entry.semantic_entry.root
        retained = tuple(
            r for r in completed.roots.row_references if r.entry is semantic
        )
        if len(retained) != 1:
            return None
        selected = tuple(
            output.source
            if isinstance(output.source, ProjectNoJoinScalarExpression)
            else None
            for output in semantic.fields
        )
        return ProjectSQLRowAuthority(
            input_schema=root.input_schema,
            let_scope=root.let_scope,
            lets=retained[0].let_bindings,
            selections=tuple(f.select_fact for f in semantic.fields),
            selected_evidence=tuple(selected),
            selected_references=retained[0].selections,
            where=root.where.expression_analysis,
            where_references=retained[0].where,
        )
    return None


def input_keys(
    entry, authority: ProjectSQLRowAuthority, ports
) -> tuple[ProjectRowField, ...]:
    """Use the original ordered IR compatibility proof for a rebound consumer."""
    if isinstance(entry, ProjectIRReboundExistingOutput):
        compatibility = entry.relation_input.compatibility
        required = tuple(authority.input_schema.fields.values())
        if (
            not compatibility.satisfied
            or len(compatibility.required_fields) != len(required)
            or any(
                a is not b
                for a, b in zip(compatibility.required_fields, required, strict=True)
            )
            or len(ports) != len(required)
            or any(port.field.output is not compatibility.output for port in ports)
        ):
            raise ValueError(
                "Rebound input lost its original field compatibility proof"
            )
        return compatibility.required_fields
    return tuple(port.field.evidence for port in ports)


def evidence_types(
    evidence: ProjectSQLScalarEvidence,
) -> Mapping[Expression, ValueType]:
    if isinstance(
        evidence, (windows.ProjectNoJoinQualify, windows.ProjectConcreteJoinedQualify)
    ):
        return windows.qualify_types(evidence)
    if isinstance(evidence, aggregation.ProjectAggregateExpressionAnalysis):
        return evidence.argument_value_types
    if isinstance(evidence, aggregation.ProjectJoinedSatisfyingAnalysis):
        return evidence.value_types
    if isinstance(evidence, ProjectModuleLetBindingFact):
        return evidence.scope_facts.expression_value_types
    if isinstance(
        evidence,
        (
            ProjectNoJoinScalarExpression,
            ProjectJoinedLetValue,
            ProjectConcreteJoinedNamespaceExpression,
            ProjectJoinCondition,
        ),
    ):
        return evidence.value_types
    return evidence.expression_value_types


def reference_expression(reference) -> Expression:
    if isinstance(
        reference,
        (
            windows.ProjectNoJoinQualifyReferenceResolution,
            windows.ProjectQualifyReferenceResolution,
            windows.ProjectNoJoinHiddenWindowComputation,
            windows.ProjectConcreteWindowComputation,
        ),
    ):
        return windows.reference_expression(reference)
    if isinstance(reference, aggregation.ProjectRelationClauseDependencyFact):
        if not isinstance(reference.source_occurrence, Expression):
            raise ValueError("Expression reference requires an expression occurrence")
        return reference.source_occurrence
    if isinstance(
        reference,
        (
            aggregation.ProjectJoinedSatisfyingOutputReference,
            aggregation.ProjectJoinedSatisfyingAggregateReference,
        ),
    ):
        return reference.expression
    if isinstance(
        reference, (ProjectModuleExpressionReferenceFact, ProjectJoinConditionReference)
    ):
        return reference.expression
    return reference.reference.expression


def reference_key(reference):
    if isinstance(reference, ProjectModuleExpressionReferenceFact):
        if reference.input_field is not None:
            return reference.input_field
        return (
            reference.let_candidates[0] if len(reference.let_candidates) == 1 else None
        )
    if isinstance(reference, ProjectJoinedLetReferenceResolution):
        return reference.target.occurrence
    return reference.target


def stage_key_label(key):
    if isinstance(key, windows.ProjectModuleWindowOutputFact):
        if key.output_name is None:
            raise ValueError("Selected window port lost its authored output name")
        return key.output_name
    if isinstance(
        key,
        (
            windows.ProjectNoJoinHiddenWindowComputation,
            windows.ProjectConcreteWindowComputation,
        ),
    ):
        return "window_result"
    if isinstance(key, SelectItem):
        if key.alias is None:
            raise ValueError("Aggregate result ports require an authored alias")
        return key.alias
    if isinstance(key, aggregation.ProjectGroupKeyFact):
        return key.field_identity
    if isinstance(key, aggregation.ProjectJoinedGroupKeyOccurrence):
        return key.field_semantics.scalar_field.evidence.name
    if isinstance(key, ProjectScalarEnvironmentField):
        return key.evidence.name
    if isinstance(key, ProjectJoinedLetOccurrence):
        return key.binding.name
    return key.name


def scalar_children(expression: Expression) -> tuple[Expression, ...]:
    if isinstance(expression, (BinaryExpr, ComparisonExpr)):
        return expression.left, expression.right
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    if isinstance(expression, BetweenExpr):
        return expression.value, expression.lower, expression.upper
    if isinstance(expression, CallExpr):
        return expression.arguments
    return ()


def scalar_nodes(
    expression: Expression, leaves: tuple[Expression, ...] = ()
) -> tuple[Expression, ...]:
    terminal = {id(leaf) for leaf in leaves}
    pending = [expression]
    result: list[Expression] = []
    while pending:
        node = pending.pop()
        result.append(node)
        if id(node) not in terminal:
            pending.extend(reversed(scalar_children(node)))
    return tuple(result)
