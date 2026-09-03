"""Private Phase-63 joined WHERE analysis and preservation authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import cast

from pietto._project.project_completion import (
    ProjectCompletion,
    ProjectEffectiveOutputTerminal,
    ProjectEffectiveOutputTerminalReason,
)
from pietto._project.project_ir_properties import ProjectIRPropertyAvailability
from pietto._project.project_joined_row_semantics import (
    ProjectConcreteJoinedRowSemantics,
    ProjectJoinedRowFieldSemantics,
    ProjectJoinedRowPropertyBridge,
)
from pietto._project.project_scalar_namespaces import (
    ProjectConcreteJoinedNamespaceExpression,
    ProjectJoinedNamespaceExpressionResult,
    ProjectJoinedScalarNamespace,
    ProjectNonConcreteJoinedNamespaceExpression,
    analyze_project_joined_namespace_expression,
)
from pietto.ast_nodes import QueryDef, TableDef, WhereClause
from pietto.errors import Diagnostic, Severity
from pietto.semantic import predicate_checks as semantic_predicates
from pietto.semantic.aggregates import (
    contains_semantic_aggregate,
    invalid_context_diagnostic,
)

__all__: tuple[str, ...] = ()


class ProjectJoinedRowFilterKind(StrEnum):
    """Whether one concrete joined row has an authored WHERE stage."""

    ABSENT = "absent"
    AUTHORED_WHERE = "authored_where"


class ProjectSQLPredicateTruth(Enum):
    """Target-neutral runtime SQL predicate outcomes, not Pietto nullability."""

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectJoinedRowRetentionEffect:
    """One declarative SQL truth-to-row-retention rule without execution."""

    truth: ProjectSQLPredicateTruth
    retain_row: bool

    def __post_init__(self) -> None:
        if (
            type(self.truth) is not ProjectSQLPredicateTruth
            or type(self.retain_row) is not bool
        ):
            raise TypeError("Row retention requires exact truth and Bool evidence.")
        if self.retain_row is not (self.truth is ProjectSQLPredicateTruth.TRUE):
            raise ValueError("Only SQL TRUE retains a filtered row.")


_SQL_ROW_RETENTION_EFFECTS = (
    ProjectJoinedRowRetentionEffect(
        truth=ProjectSQLPredicateTruth.TRUE,
        retain_row=True,
    ),
    ProjectJoinedRowRetentionEffect(
        truth=ProjectSQLPredicateTruth.FALSE,
        retain_row=False,
    ),
    ProjectJoinedRowRetentionEffect(
        truth=ProjectSQLPredicateTruth.UNKNOWN,
        retain_row=False,
    ),
)


class ProjectJoinedRowMultiplicity(StrEnum):
    """The exact duplicate-preserving input relation semantics."""

    BAG = "bag"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedRowFilterPreservationWitness:
    """Reference-only preservation premises over the exact Slice-6 input."""

    joined_semantics: ProjectConcreteJoinedRowSemantics = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_property_bridge: ProjectJoinedRowPropertyBridge = field(init=False)
    multiplicity: ProjectJoinedRowMultiplicity = field(
        init=False,
        default=ProjectJoinedRowMultiplicity.BAG,
    )

    def __post_init__(self) -> None:
        if type(self.joined_semantics) is not ProjectConcreteJoinedRowSemantics:
            raise TypeError("Filter preservation requires exact joined semantics.")
        bridge = self.joined_semantics.property_bridge
        if (
            bridge.relational.output is not self.joined_semantics.final_output
            or bridge.ordering.availability is not ProjectIRPropertyAvailability.UNKNOWN
        ):
            raise ValueError("Filter preservation requires exact joined properties.")
        object.__setattr__(self, "input_property_bridge", bridge)

    @property
    def fields(self) -> tuple[ProjectJoinedRowFieldSemantics, ...]:
        return self.joined_semantics.fields


def _admitted_joined_semantics(
    completion: ProjectCompletion,
    entry: ProjectEffectiveOutputTerminal,
) -> ProjectConcreteJoinedRowSemantics:
    if type(completion) is not ProjectCompletion:
        raise TypeError("Joined filtering requires an exact completion snapshot.")
    if type(entry) is not ProjectEffectiveOutputTerminal or not any(
        entry is retained for retained in completion.entries
    ):
        raise ValueError("Joined filtering requires exact ledger membership.")
    joined = entry.joined_completion
    if (
        entry.reason is not ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
        or type(joined) is not ProjectConcreteJoinedRowSemantics
    ):
        raise ValueError("Joined filtering requires exact joined-tail readiness.")
    return joined


def _definition(
    entry: ProjectEffectiveOutputTerminal,
) -> TableDef | QueryDef:
    definition = entry.owner.definition
    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("Joined filtering requires a table or query owner.")
    return cast(TableDef | QueryDef, definition)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteJoinedRowFilter:
    """One closed absent or known-Bool joined row-filter result."""

    completion: ProjectCompletion = field(repr=False, compare=False, hash=False)
    entry: ProjectEffectiveOutputTerminal = field(
        repr=False,
        compare=False,
        hash=False,
    )
    kind: ProjectJoinedRowFilterKind
    namespace: ProjectJoinedScalarNamespace = field(
        repr=False,
        compare=False,
        hash=False,
    )
    where_clause: WhereClause | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    expression_analysis: ProjectConcreteJoinedNamespaceExpression | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    preservation: ProjectJoinedRowFilterPreservationWitness
    diagnostics: tuple[Diagnostic, ...] = ()
    retention_effects: tuple[ProjectJoinedRowRetentionEffect, ...] = ()
    joined_semantics: ProjectConcreteJoinedRowSemantics = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    fields: tuple[ProjectJoinedRowFieldSemantics, ...] = field(init=False)

    def __post_init__(self) -> None:
        joined = _admitted_joined_semantics(self.completion, self.entry)
        definition = _definition(self.entry)
        if type(self.kind) is not ProjectJoinedRowFilterKind or (
            self.namespace is not joined.post_let
            or type(self.preservation) is not ProjectJoinedRowFilterPreservationWitness
            or self.preservation.joined_semantics is not joined
        ):
            raise ValueError("Concrete filter requires exact Slice-6 input authority.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
        ):
            raise TypeError("Filter diagnostics must be an exact tuple.")
        if any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        ):
            raise ValueError("Concrete joined filtering forbids blocking diagnostics.")
        if self.kind is ProjectJoinedRowFilterKind.ABSENT:
            if any(
                (
                    definition.where_clause is not None,
                    self.where_clause is not None,
                    self.expression_analysis is not None,
                    bool(self.diagnostics),
                    bool(self.retention_effects),
                )
            ):
                raise ValueError("Absent filtering cannot manufacture a predicate.")
        elif (
            type(self.where_clause) is not WhereClause
            or self.where_clause is not definition.where_clause
            or type(self.expression_analysis)
            is not ProjectConcreteJoinedNamespaceExpression
            or self.expression_analysis.namespace is not self.namespace
            or self.expression_analysis.expression is not self.where_clause.expression
            or self.expression_analysis.diagnostics != self.diagnostics
            or self.retention_effects != _SQL_ROW_RETENTION_EFFECTS
            or semantic_predicates._check_bool_expression(
                self.where_clause.expression,
                context="where clause",
                expression_value_types=self.expression_analysis.value_types,
            )
            is not None
        ):
            raise ValueError(
                "Authored filtering requires one exact known-Bool predicate."
            )
        object.__setattr__(self, "joined_semantics", joined)
        object.__setattr__(self, "fields", joined.fields)


class ProjectJoinedRowFilterNonConcreteReason(StrEnum):
    """Closed Slice-8 blocker families."""

    NAMESPACE_EXPRESSION_NON_CONCRETE = "namespace_expression_non_concrete"
    INVALID_PREDICATE_CONTEXT = "invalid_predicate_context"
    KNOWN_NON_BOOL_PREDICATE = "known_non_bool_predicate"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteJoinedRowFilter:
    """One exact predicate blocker with no concrete post-filter authority."""

    completion: ProjectCompletion = field(repr=False, compare=False, hash=False)
    entry: ProjectEffectiveOutputTerminal = field(
        repr=False,
        compare=False,
        hash=False,
    )
    namespace: ProjectJoinedScalarNamespace = field(
        repr=False,
        compare=False,
        hash=False,
    )
    where_clause: WhereClause = field(repr=False, compare=False, hash=False)
    expression_analysis: ProjectJoinedNamespaceExpressionResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectJoinedRowFilterNonConcreteReason
    diagnostics: tuple[Diagnostic, ...] = ()
    joined_semantics: ProjectConcreteJoinedRowSemantics = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    post_filter: None = field(init=False, default=None)
    preservation: None = field(init=False, default=None)
    fields: tuple[ProjectJoinedRowFieldSemantics, ...] = field(
        init=False,
        default=(),
    )

    def __post_init__(self) -> None:
        joined = _admitted_joined_semantics(self.completion, self.entry)
        definition = _definition(self.entry)
        if (
            self.namespace is not joined.post_let
            or type(self.where_clause) is not WhereClause
            or self.where_clause is not definition.where_clause
            or type(self.expression_analysis)
            not in {
                ProjectConcreteJoinedNamespaceExpression,
                ProjectNonConcreteJoinedNamespaceExpression,
            }
            or self.expression_analysis.namespace is not self.namespace
            or self.expression_analysis.expression is not self.where_clause.expression
            or type(self.reason) is not ProjectJoinedRowFilterNonConcreteReason
            or type(self.diagnostics) is not tuple
            or any(
                type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
            )
        ):
            raise ValueError("Filter blocker requires exact authored input evidence.")
        aggregate_diagnostic = (
            invalid_context_diagnostic(
                self.where_clause.expression,
                context="where clause",
            )
            if contains_semantic_aggregate(self.where_clause.expression)
            else None
        )
        bool_diagnostic = (
            semantic_predicates._check_bool_expression(
                self.where_clause.expression,
                context="where clause",
                expression_value_types=self.expression_analysis.value_types,
            )
            if type(self.expression_analysis)
            is ProjectConcreteJoinedNamespaceExpression
            else None
        )
        if (
            self.reason
            is ProjectJoinedRowFilterNonConcreteReason.INVALID_PREDICATE_CONTEXT
        ):
            expected = (
                *(() if aggregate_diagnostic is None else (aggregate_diagnostic,)),
                *self.expression_analysis.diagnostics,
            )
            valid = aggregate_diagnostic is not None
        elif (
            self.reason
            is ProjectJoinedRowFilterNonConcreteReason.KNOWN_NON_BOOL_PREDICATE
        ):
            expected = (
                *self.expression_analysis.diagnostics,
                *(() if bool_diagnostic is None else (bool_diagnostic,)),
            )
            valid = aggregate_diagnostic is None and bool_diagnostic is not None
        else:
            expected = self.expression_analysis.diagnostics
            valid = (
                aggregate_diagnostic is None
                and type(self.expression_analysis)
                is ProjectNonConcreteJoinedNamespaceExpression
            )
        if not valid or self.diagnostics != expected:
            raise ValueError("Filter blocker reason must match exact diagnostics.")
        object.__setattr__(self, "joined_semantics", joined)


type ProjectJoinedRowFilterResult = (
    ProjectConcreteJoinedRowFilter | ProjectNonConcreteJoinedRowFilter
)


def build_project_joined_row_filter(
    completion: ProjectCompletion,
    entry: ProjectEffectiveOutputTerminal,
) -> ProjectJoinedRowFilterResult:
    """Analyze WHERE only for one exact joined-tail ledger entry."""

    joined = _admitted_joined_semantics(completion, entry)
    definition = _definition(entry)
    where_clause = definition.where_clause
    if where_clause is None:
        return ProjectConcreteJoinedRowFilter(
            completion=completion,
            entry=entry,
            kind=ProjectJoinedRowFilterKind.ABSENT,
            namespace=joined.post_let,
            preservation=ProjectJoinedRowFilterPreservationWitness(
                joined_semantics=joined,
            ),
        )

    analysis = analyze_project_joined_namespace_expression(
        joined.post_let,
        where_clause.expression,
    )
    if contains_semantic_aggregate(where_clause.expression):
        diagnostic = invalid_context_diagnostic(
            where_clause.expression,
            context="where clause",
        )
        return ProjectNonConcreteJoinedRowFilter(
            completion=completion,
            entry=entry,
            namespace=joined.post_let,
            where_clause=where_clause,
            expression_analysis=analysis,
            reason=ProjectJoinedRowFilterNonConcreteReason.INVALID_PREDICATE_CONTEXT,
            diagnostics=(diagnostic, *analysis.diagnostics),
        )
    if type(analysis) is ProjectNonConcreteJoinedNamespaceExpression:
        return ProjectNonConcreteJoinedRowFilter(
            completion=completion,
            entry=entry,
            namespace=joined.post_let,
            where_clause=where_clause,
            expression_analysis=analysis,
            reason=(
                ProjectJoinedRowFilterNonConcreteReason.NAMESPACE_EXPRESSION_NON_CONCRETE
            ),
            diagnostics=analysis.diagnostics,
        )
    if type(analysis) is not ProjectConcreteJoinedNamespaceExpression:
        raise AssertionError("joined expression analysis lost its closed variant")
    bool_diagnostic = semantic_predicates._check_bool_expression(
        where_clause.expression,
        context="where clause",
        expression_value_types=analysis.value_types,
    )
    if bool_diagnostic is not None:
        return ProjectNonConcreteJoinedRowFilter(
            completion=completion,
            entry=entry,
            namespace=joined.post_let,
            where_clause=where_clause,
            expression_analysis=analysis,
            reason=ProjectJoinedRowFilterNonConcreteReason.KNOWN_NON_BOOL_PREDICATE,
            diagnostics=(*analysis.diagnostics, bool_diagnostic),
        )
    return ProjectConcreteJoinedRowFilter(
        completion=completion,
        entry=entry,
        kind=ProjectJoinedRowFilterKind.AUTHORED_WHERE,
        namespace=joined.post_let,
        where_clause=where_clause,
        expression_analysis=analysis,
        preservation=ProjectJoinedRowFilterPreservationWitness(
            joined_semantics=joined,
        ),
        diagnostics=analysis.diagnostics,
        retention_effects=_SQL_ROW_RETENTION_EFFECTS,
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedRowFilterSet:
    """Canonical-ledger-ordered Slice-8 results for one completion snapshot."""

    completion: ProjectCompletion = field(repr=False, compare=False, hash=False)
    results: tuple[ProjectJoinedRowFilterResult, ...]

    def __post_init__(self) -> None:
        if (
            type(self.completion) is not ProjectCompletion
            or type(self.results) is not tuple
        ):
            raise TypeError("Joined filter set requires exact completion and results.")
        expected = tuple(
            entry
            for entry in self.completion.entries
            if type(entry) is ProjectEffectiveOutputTerminal
            and entry.reason is ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
            and type(entry.joined_completion) is ProjectConcreteJoinedRowSemantics
        )
        if len(self.results) != len(expected) or any(
            type(result)
            not in {
                ProjectConcreteJoinedRowFilter,
                ProjectNonConcreteJoinedRowFilter,
            }
            or result.completion is not self.completion
            or result.entry is not entry
            for result, entry in zip(self.results, expected, strict=True)
        ):
            raise ValueError(
                "Joined filter results must retain canonical ledger order."
            )


def build_project_joined_row_filters(
    completion: ProjectCompletion,
) -> ProjectJoinedRowFilterSet:
    """Build exactly one Slice-8 result per eligible canonical ledger entry."""

    if type(completion) is not ProjectCompletion:
        raise TypeError("Joined filtering requires an exact completion snapshot.")
    entries = tuple(
        entry
        for entry in completion.entries
        if type(entry) is ProjectEffectiveOutputTerminal
        and entry.reason is ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
        and type(entry.joined_completion) is ProjectConcreteJoinedRowSemantics
    )
    return ProjectJoinedRowFilterSet(
        completion=completion,
        results=tuple(
            build_project_joined_row_filter(completion, entry) for entry in entries
        ),
    )
