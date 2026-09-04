"""Private Phase-63 joined QUALIFY semantics and preservation authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_joined_row_filter import (
    ProjectJoinedRowFilterPreservationWitness,
    ProjectJoinedRowMultiplicity,
    ProjectJoinedRowRetentionEffect,
    _SQL_ROW_RETENTION_EFFECTS,
)
from pietto._project.project_joined_windows import (
    ProjectConcreteJoinedWindowStage,
    ProjectConcreteWindowComputation,
    ProjectHiddenWindowComputationResult,
    ProjectJoinedPostWindowNamespace,
    ProjectJoinedWindowInputBinding,
    ProjectJoinedWindowPreservationWitness,
    ProjectJoinedWindowStageResult,
    ProjectJoinedWindowStageSet,
    ProjectNonConcreteHiddenWindowComputation,
    ProjectNonConcreteJoinedWindowStage,
    ProjectNonConcreteWindowComputation,
    ProjectSelectedWindowResultBinding,
    analyze_hidden_project_window_computation,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    NameExpr,
    QualifyClause,
    QueryDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic import predicate_checks as semantic_predicates
from pietto.semantic.aggregates import (
    child_expressions,
    contains_semantic_aggregate,
    invalid_context_diagnostic,
)
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import RowSchema, ValueType, ValueTypeKind

__all__: tuple[str, ...] = ()


def _definition(
    stage: ProjectJoinedWindowStageResult,
) -> TableDef | QueryDef:
    definition = stage.input_aggregation.input_filter.entry.owner.definition
    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("Joined QUALIFY requires a table or query owner.")
    return cast(TableDef | QueryDef, definition)


type ProjectQualifyReferenceCandidate = (
    ProjectJoinedWindowInputBinding | ProjectSelectedWindowResultBinding
)


def _reference_candidates(
    stage: ProjectConcreteJoinedWindowStage,
    expression: NameExpr | DottedNameExpr,
) -> tuple[ProjectQualifyReferenceCandidate, ...]:
    if type(expression) is NameExpr:
        return (
            *stage.post_window.pre_window.candidates(expression),
            *stage.post_window.selected_candidates(expression.name),
        )
    return stage.post_window.pre_window.candidates(expression)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectQualifyReferenceResolution:
    """One outer QUALIFY reference with its complete cross-domain bucket."""

    stage: ProjectConcreteJoinedWindowStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: NameExpr | DottedNameExpr = field(
        repr=False,
        compare=False,
        hash=False,
    )
    candidates: tuple[ProjectQualifyReferenceCandidate, ...]
    status: ProjectModuleCandidateBucketStatus = field(init=False)
    target: ProjectQualifyReferenceCandidate | None = field(init=False)

    def __post_init__(self) -> None:
        if type(self.stage) is not ProjectConcreteJoinedWindowStage or type(
            self.expression
        ) not in {NameExpr, DottedNameExpr}:
            raise TypeError("QUALIFY resolution requires exact stage and expression.")
        if type(self.candidates) is not tuple or any(
            type(candidate)
            not in {
                ProjectJoinedWindowInputBinding,
                ProjectSelectedWindowResultBinding,
            }
            for candidate in self.candidates
        ):
            raise TypeError("QUALIFY candidates must be an exact occurrence tuple.")
        if self.candidates != _reference_candidates(self.stage, self.expression):
            raise ValueError("QUALIFY candidates must be complete and ordered.")
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


type _QualifyOperand = NameExpr | DottedNameExpr | WindowExpr


def _qualify_operands(expression: Expression) -> tuple[_QualifyOperand, ...]:
    """Enumerate outer references and atomic hidden windows in source order."""

    if type(expression) in {NameExpr, DottedNameExpr, WindowExpr}:
        return (cast(_QualifyOperand, expression),)
    return tuple(
        operand
        for child in child_expressions(expression)
        for operand in _qualify_operands(child)
    )


def _reference_diagnostic(
    resolution: ProjectQualifyReferenceResolution,
) -> Diagnostic:
    expression = resolution.expression
    if type(expression) is NameExpr:
        name = expression.name
    else:
        assert type(expression) is DottedNameExpr
        name = ".".join(expression.parts)
    adjective = (
        "Unknown"
        if resolution.status is ProjectModuleCandidateBucketStatus.ABSENT
        else "Ambiguous"
    )
    span = expression.span
    return Diagnostic(
        code="PIE-S2332",
        severity=Severity.ERROR,
        message=f"{adjective} QUALIFY reference: {name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _window_required_diagnostic(clause: QualifyClause) -> Diagnostic:
    span = clause.span
    return Diagnostic(
        code="PIE-S2331",
        severity=Severity.ERROR,
        message=(
            "QUALIFY requires at least one selected or predicate window computation"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _candidate_value_type(candidate: ProjectQualifyReferenceCandidate) -> ValueType:
    if type(candidate) is ProjectJoinedWindowInputBinding:
        return candidate.value_type
    if type(candidate) is ProjectSelectedWindowResultBinding:
        return candidate.value_type
    raise TypeError("QUALIFY candidate must be an exact visible binding.")


def _hidden_value_type(computation: ProjectConcreteWindowComputation) -> ValueType:
    value_type = computation.analysis.result.value_type
    if value_type is None:
        raise ValueError("Concrete hidden window requires one result value type.")
    return value_type


class ProjectJoinedQualifyStageKind(StrEnum):
    """Concrete clause absence versus authored post-window filtering."""

    ABSENT = "absent"
    AUTHORED_QUALIFY = "authored_qualify"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedQualifyPreservationWitness:
    """Reference-only preservation over one exact concrete Slice-10 stage."""

    window_stage: ProjectConcreteJoinedWindowStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    filters_rows: bool
    window_preservation: ProjectJoinedWindowPreservationWitness = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    input_filter_preservation: ProjectJoinedRowFilterPreservationWitness = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    multiplicity: ProjectJoinedRowMultiplicity = field(init=False)
    establishes_relation_order: bool = field(init=False, default=False)
    selected_results: tuple[ProjectSelectedWindowResultBinding, ...] = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.window_stage) is not ProjectConcreteJoinedWindowStage
            or type(self.filters_rows) is not bool
        ):
            raise TypeError("QUALIFY preservation requires exact stage and filter law.")
        expected_filters = _definition(self.window_stage).qualify_clause is not None
        if self.filters_rows is not expected_filters:
            raise ValueError(
                "QUALIFY filter effect must match exact clause authorship."
            )
        window_preservation = self.window_stage.preservation
        input_preservation = window_preservation.input_filter_preservation
        object.__setattr__(self, "window_preservation", window_preservation)
        object.__setattr__(self, "input_filter_preservation", input_preservation)
        object.__setattr__(self, "multiplicity", window_preservation.multiplicity)
        object.__setattr__(self, "selected_results", self.window_stage.selected_results)

    @property
    def intrinsic_grain(self):
        return self.window_stage.preservation.intrinsic_grain

    @property
    def relation_ordering(self):
        return self.window_stage.preservation.relation_ordering


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedPostQualifyReadiness:
    """Exact pass-through row/window authority ready for Slice 12."""

    window_stage: ProjectConcreteJoinedWindowStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    preservation: ProjectJoinedQualifyPreservationWitness
    post_window: ProjectJoinedPostWindowNamespace = field(init=False)
    selected_results: tuple[ProjectSelectedWindowResultBinding, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.window_stage) is not ProjectConcreteJoinedWindowStage or (
            type(self.preservation) is not ProjectJoinedQualifyPreservationWitness
            or self.preservation.window_stage is not self.window_stage
        ):
            raise ValueError("Post-QUALIFY readiness requires exact window authority.")
        object.__setattr__(self, "post_window", self.window_stage.post_window)
        object.__setattr__(self, "selected_results", self.window_stage.selected_results)


def _require_operand_coverage(
    *,
    stage: ProjectConcreteJoinedWindowStage,
    clause: QualifyClause,
    references: tuple[ProjectQualifyReferenceResolution, ...],
    hidden: tuple[ProjectHiddenWindowComputationResult, ...],
) -> None:
    operands = _qualify_operands(clause.expression)
    expected_references = tuple(
        operand for operand in operands if type(operand) in {NameExpr, DottedNameExpr}
    )
    expected_hidden = tuple(
        operand for operand in operands if type(operand) is WindowExpr
    )
    if (
        type(references) is not tuple
        or len(references) != len(expected_references)
        or any(
            type(resolution) is not ProjectQualifyReferenceResolution
            or resolution.stage is not stage
            or resolution.expression is not expression
            for resolution, expression in zip(
                references,
                expected_references,
                strict=True,
            )
        )
    ):
        raise ValueError("QUALIFY references must cover exact outer occurrences.")
    if type(hidden) is not tuple or len(hidden) != len(expected_hidden):
        raise ValueError("QUALIFY hidden attempts must cover exact WindowExpr values.")
    for attempt, expression in zip(hidden, expected_hidden, strict=True):
        if type(attempt) is ProjectNonConcreteHiddenWindowComputation:
            retained_expression = attempt.expression
            retained_stage = attempt.stage
        elif type(attempt) is ProjectConcreteWindowComputation:
            retained_expression = attempt.site.expression
            retained_stage = cast(ProjectConcreteJoinedWindowStage, attempt.site.root)
        else:
            assert type(attempt) is ProjectNonConcreteWindowComputation
            retained_expression = attempt.site.expression
            retained_stage = cast(ProjectConcreteJoinedWindowStage, attempt.site.root)
        if retained_expression is not expression or retained_stage is not stage:
            raise ValueError("QUALIFY hidden attempts must retain exact site order.")


def _has_exact_value_type_seeds(
    references: tuple[ProjectQualifyReferenceResolution, ...],
    hidden: tuple[ProjectConcreteWindowComputation, ...],
    value_types: Mapping[Expression, ValueType],
) -> bool:
    return all(
        resolution.target is not None
        and value_types.get(resolution.expression)
        is _candidate_value_type(resolution.target)
        for resolution in references
    ) and all(
        value_types.get(computation.site.expression) is _hidden_value_type(computation)
        for computation in hidden
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteJoinedQualify:
    """One closed absent or known-Bool joined QUALIFY stage."""

    window_set: ProjectJoinedWindowStageSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    window_stage: ProjectConcreteJoinedWindowStage = field(
        repr=False,
        compare=False,
        hash=False,
    )
    kind: ProjectJoinedQualifyStageKind
    qualify_clause: QualifyClause | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    references: tuple[ProjectQualifyReferenceResolution, ...] = ()
    hidden_computations: tuple[ProjectConcreteWindowComputation, ...] = ()
    predicate_value_type: ValueType | None = None
    value_types: Mapping[Expression, ValueType] = field(
        default_factory=dict,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = ()
    retention_effects: tuple[ProjectJoinedRowRetentionEffect, ...] = ()
    preservation: ProjectJoinedQualifyPreservationWitness
    post_qualify: ProjectJoinedPostQualifyReadiness

    def __post_init__(self) -> None:
        definition = _definition(self.window_stage)
        if (
            type(self.window_set) is not ProjectJoinedWindowStageSet
            or not any(self.window_stage is item for item in self.window_set.results)
            or type(self.kind) is not ProjectJoinedQualifyStageKind
            or type(self.diagnostics) is not tuple
            or any(
                type(diagnostic) is not Diagnostic
                or diagnostic.severity is Severity.ERROR
                for diagnostic in self.diagnostics
            )
            or type(self.preservation) is not ProjectJoinedQualifyPreservationWitness
            or self.preservation.window_stage is not self.window_stage
            or type(self.post_qualify) is not ProjectJoinedPostQualifyReadiness
            or self.post_qualify.window_stage is not self.window_stage
            or self.post_qualify.preservation is not self.preservation
        ):
            raise ValueError("Concrete QUALIFY requires exact Slice-10 authority.")
        if self.kind is ProjectJoinedQualifyStageKind.ABSENT:
            if any(
                (
                    definition.qualify_clause is not None,
                    self.qualify_clause is not None,
                    self.references,
                    self.hidden_computations,
                    self.predicate_value_type is not None,
                    bool(self.value_types),
                    self.diagnostics,
                    self.retention_effects,
                    self.preservation.filters_rows,
                )
            ):
                raise ValueError("Absent QUALIFY cannot manufacture a predicate.")
        else:
            if (
                type(self.qualify_clause) is not QualifyClause
                or self.qualify_clause is not definition.qualify_clause
                or type(self.predicate_value_type) is not ValueType
                or self.predicate_value_type.kind is not ValueTypeKind.KNOWN
                or self.predicate_value_type.resolved_type.name != "Bool"
                or self.value_types.get(self.qualify_clause.expression)
                is not self.predicate_value_type
                or self.retention_effects is not _SQL_ROW_RETENTION_EFFECTS
                or not self.preservation.filters_rows
                or not (self.window_stage.selected_results or self.hidden_computations)
            ):
                raise ValueError("Authored QUALIFY requires one known Bool predicate.")
            _require_operand_coverage(
                stage=self.window_stage,
                clause=self.qualify_clause,
                references=self.references,
                hidden=self.hidden_computations,
            )
            if not _has_exact_value_type_seeds(
                self.references,
                self.hidden_computations,
                self.value_types,
            ):
                raise ValueError("Concrete QUALIFY must retain exact value-type seeds.")
        object.__setattr__(
            self, "value_types", MappingProxyType(dict(self.value_types))
        )


class ProjectJoinedQualifyNonConcreteReason(StrEnum):
    """Closed Slice-11 terminal reasons."""

    UPSTREAM_WINDOW_NON_CONCRETE = "upstream_window_non_concrete"
    WINDOW_COMPUTATION_REQUIRED = "window_computation_required"
    REFERENCE_NON_CONCRETE = "reference_non_concrete"
    HIDDEN_WINDOW_NON_CONCRETE = "hidden_window_non_concrete"
    SCALAR_KERNEL_NON_CONCRETE = "scalar_kernel_non_concrete"
    KNOWN_NON_BOOL_PREDICATE = "known_non_bool_predicate"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteJoinedQualify:
    """One exact QUALIFY blocker with no post-stage readiness."""

    window_set: ProjectJoinedWindowStageSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    window_stage: ProjectJoinedWindowStageResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectJoinedQualifyNonConcreteReason
    qualify_clause: QualifyClause | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    references: tuple[ProjectQualifyReferenceResolution, ...] = ()
    hidden_attempts: tuple[ProjectHiddenWindowComputationResult, ...] = ()
    kernel_value_type: ValueType | None = None
    value_types: Mapping[Expression, ValueType] = field(
        default_factory=dict,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = ()
    preservation: None = field(init=False, default=None)
    post_qualify: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if (
            type(self.window_set) is not ProjectJoinedWindowStageSet
            or not any(self.window_stage is item for item in self.window_set.results)
            or type(self.reason) is not ProjectJoinedQualifyNonConcreteReason
            or type(self.diagnostics) is not tuple
            or any(type(item) is not Diagnostic for item in self.diagnostics)
        ):
            raise ValueError("QUALIFY terminal requires exact Slice-10 authority.")
        definition = _definition(self.window_stage)
        if (
            self.reason
            is ProjectJoinedQualifyNonConcreteReason.UPSTREAM_WINDOW_NON_CONCRETE
        ):
            valid = (
                type(self.window_stage) is ProjectNonConcreteJoinedWindowStage
                and self.qualify_clause is definition.qualify_clause
                and not self.references
                and not self.hidden_attempts
                and self.kernel_value_type is None
                and not self.value_types
                and not self.diagnostics
            )
        else:
            valid = (
                type(self.window_stage) is ProjectConcreteJoinedWindowStage
                and type(self.qualify_clause) is QualifyClause
                and self.qualify_clause is definition.qualify_clause
            )
            if valid:
                assert type(self.window_stage) is ProjectConcreteJoinedWindowStage
                assert type(self.qualify_clause) is QualifyClause
                _require_operand_coverage(
                    stage=self.window_stage,
                    clause=self.qualify_clause,
                    references=self.references,
                    hidden=self.hidden_attempts,
                )
                hidden_failures = tuple(
                    attempt
                    for attempt in self.hidden_attempts
                    if type(attempt) is not ProjectConcreteWindowComputation
                )
                reference_failures = tuple(
                    resolution
                    for resolution in self.references
                    if resolution.target is None
                )
                has_window = bool(
                    self.window_stage.selected_results or self.hidden_attempts
                )
                if self.reason is (
                    ProjectJoinedQualifyNonConcreteReason.WINDOW_COMPUTATION_REQUIRED
                ):
                    valid = (
                        not has_window
                        and self.kernel_value_type is None
                        and not self.value_types
                        and any(item.code == "PIE-S2331" for item in self.diagnostics)
                    )
                elif self.reason is (
                    ProjectJoinedQualifyNonConcreteReason.HIDDEN_WINDOW_NON_CONCRETE
                ):
                    valid = (
                        bool(hidden_failures)
                        and self.kernel_value_type is None
                        and not self.value_types
                    )
                elif self.reason is (
                    ProjectJoinedQualifyNonConcreteReason.REFERENCE_NON_CONCRETE
                ):
                    valid = (
                        not hidden_failures
                        and bool(reference_failures)
                        and self.kernel_value_type is None
                        and not self.value_types
                    )
                else:
                    concrete_hidden = cast(
                        tuple[ProjectConcreteWindowComputation, ...],
                        self.hidden_attempts,
                    )
                    kernel_value_type = self.kernel_value_type
                    seeds_are_exact = (
                        not hidden_failures
                        and not reference_failures
                        and has_window
                        and type(kernel_value_type) is ValueType
                        and _has_exact_value_type_seeds(
                            self.references,
                            concrete_hidden,
                            self.value_types,
                        )
                    )
                    if self.reason is (
                        ProjectJoinedQualifyNonConcreteReason.SCALAR_KERNEL_NON_CONCRETE
                    ):
                        valid = type(kernel_value_type) is ValueType and (
                            seeds_are_exact
                            and (
                                kernel_value_type.kind is ValueTypeKind.UNKNOWN
                                or any(
                                    item.severity is Severity.ERROR
                                    for item in self.diagnostics
                                )
                            )
                        )
                    else:
                        valid = (
                            type(kernel_value_type) is ValueType
                            and seeds_are_exact
                            and kernel_value_type.kind is ValueTypeKind.KNOWN
                            and kernel_value_type.resolved_type.name != "Bool"
                            and any(
                                item.code == "PIE-S2202" for item in self.diagnostics
                            )
                        )
        if not valid:
            raise ValueError("QUALIFY terminal reason must retain exact causal roots.")
        object.__setattr__(
            self, "value_types", MappingProxyType(dict(self.value_types))
        )


type ProjectJoinedQualifyResult = (
    ProjectConcreteJoinedQualify | ProjectNonConcreteJoinedQualify
)


def _analyze_operands(
    stage: ProjectConcreteJoinedWindowStage,
    clause: QualifyClause,
) -> tuple[
    tuple[ProjectQualifyReferenceResolution, ...],
    tuple[ProjectHiddenWindowComputationResult, ...],
    tuple[Diagnostic, ...],
]:
    references: list[ProjectQualifyReferenceResolution] = []
    hidden: list[ProjectHiddenWindowComputationResult] = []
    diagnostics: list[Diagnostic] = []
    for operand in _qualify_operands(clause.expression):
        if type(operand) is WindowExpr:
            attempt = analyze_hidden_project_window_computation(stage, operand)
            hidden.append(attempt)
            if type(attempt) is ProjectNonConcreteWindowComputation:
                diagnostics.extend(attempt.diagnostics)
            continue
        resolution = ProjectQualifyReferenceResolution(
            stage=stage,
            expression=cast(NameExpr | DottedNameExpr, operand),
            candidates=_reference_candidates(
                stage,
                cast(NameExpr | DottedNameExpr, operand),
            ),
        )
        references.append(resolution)
        if resolution.target is None:
            diagnostics.append(_reference_diagnostic(resolution))
    return tuple(references), tuple(hidden), tuple(diagnostics)


def _build_preservation(
    stage: ProjectConcreteJoinedWindowStage,
    *,
    filters_rows: bool,
) -> tuple[
    ProjectJoinedQualifyPreservationWitness,
    ProjectJoinedPostQualifyReadiness,
]:
    preservation = ProjectJoinedQualifyPreservationWitness(
        window_stage=stage,
        filters_rows=filters_rows,
    )
    return preservation, ProjectJoinedPostQualifyReadiness(
        window_stage=stage,
        preservation=preservation,
    )


def build_project_joined_qualify(
    window_set: ProjectJoinedWindowStageSet,
    window_stage: ProjectJoinedWindowStageResult,
) -> ProjectJoinedQualifyResult:
    """Build one exact Slice-11 result without rebuilding Slice-10 authority."""

    if type(window_set) is not ProjectJoinedWindowStageSet or not any(
        window_stage is item for item in window_set.results
    ):
        raise ValueError("Joined QUALIFY requires exact Slice-10 membership.")
    definition = _definition(window_stage)
    clause = definition.qualify_clause
    if type(window_stage) is ProjectNonConcreteJoinedWindowStage:
        return ProjectNonConcreteJoinedQualify(
            window_set=window_set,
            window_stage=window_stage,
            reason=ProjectJoinedQualifyNonConcreteReason.UPSTREAM_WINDOW_NON_CONCRETE,
            qualify_clause=clause,
        )
    if type(window_stage) is not ProjectConcreteJoinedWindowStage:
        raise TypeError("Joined QUALIFY requires one closed Slice-10 variant.")
    if clause is None:
        preservation, readiness = _build_preservation(
            window_stage,
            filters_rows=False,
        )
        return ProjectConcreteJoinedQualify(
            window_set=window_set,
            window_stage=window_stage,
            kind=ProjectJoinedQualifyStageKind.ABSENT,
            preservation=preservation,
            post_qualify=readiness,
        )

    references, hidden_attempts, operand_diagnostics = _analyze_operands(
        window_stage,
        clause,
    )
    hidden_expressions = tuple(
        operand
        for operand in _qualify_operands(clause.expression)
        if type(operand) is WindowExpr
    )
    has_required_window = bool(window_stage.selected_results or hidden_expressions)
    if not has_required_window:
        return ProjectNonConcreteJoinedQualify(
            window_set=window_set,
            window_stage=window_stage,
            reason=ProjectJoinedQualifyNonConcreteReason.WINDOW_COMPUTATION_REQUIRED,
            qualify_clause=clause,
            references=references,
            hidden_attempts=hidden_attempts,
            diagnostics=(_window_required_diagnostic(clause), *operand_diagnostics),
        )

    hidden_failures = tuple(
        attempt
        for attempt in hidden_attempts
        if type(attempt) is not ProjectConcreteWindowComputation
    )
    reference_failures = tuple(
        resolution for resolution in references if resolution.target is None
    )
    if hidden_failures or reference_failures:
        return ProjectNonConcreteJoinedQualify(
            window_set=window_set,
            window_stage=window_stage,
            reason=(
                ProjectJoinedQualifyNonConcreteReason.HIDDEN_WINDOW_NON_CONCRETE
                if hidden_failures
                else ProjectJoinedQualifyNonConcreteReason.REFERENCE_NON_CONCRETE
            ),
            qualify_clause=clause,
            references=references,
            hidden_attempts=hidden_attempts,
            diagnostics=operand_diagnostics,
        )

    hidden = cast(tuple[ProjectConcreteWindowComputation, ...], hidden_attempts)
    value_types: dict[Expression, ValueType] = {}
    for resolution in references:
        target = resolution.target
        if target is None:
            raise AssertionError("Concrete QUALIFY reference lost its target.")
        value_types[resolution.expression] = _candidate_value_type(target)
    for computation in hidden:
        value_types[computation.site.expression] = _hidden_value_type(computation)

    diagnostics = list(operand_diagnostics)
    if contains_semantic_aggregate(clause.expression):
        diagnostics.append(
            invalid_context_diagnostic(
                clause.expression,
                context="qualify clause",
            )
        )
    predicate_type = infer_row_expression(
        clause.expression,
        RowSchema(),
        value_types,
        diagnostics,
        report_unknown_name=True,
    )
    retained_diagnostics = tuple(diagnostics)
    if predicate_type.kind is ValueTypeKind.UNKNOWN or any(
        diagnostic.severity is Severity.ERROR for diagnostic in retained_diagnostics
    ):
        return ProjectNonConcreteJoinedQualify(
            window_set=window_set,
            window_stage=window_stage,
            reason=ProjectJoinedQualifyNonConcreteReason.SCALAR_KERNEL_NON_CONCRETE,
            qualify_clause=clause,
            references=references,
            hidden_attempts=hidden_attempts,
            kernel_value_type=predicate_type,
            value_types=value_types,
            diagnostics=retained_diagnostics,
        )

    bool_diagnostic = semantic_predicates._check_bool_expression(
        clause.expression,
        context="qualify clause",
        expression_value_types=value_types,
    )
    if bool_diagnostic is not None:
        return ProjectNonConcreteJoinedQualify(
            window_set=window_set,
            window_stage=window_stage,
            reason=ProjectJoinedQualifyNonConcreteReason.KNOWN_NON_BOOL_PREDICATE,
            qualify_clause=clause,
            references=references,
            hidden_attempts=hidden_attempts,
            kernel_value_type=predicate_type,
            value_types=value_types,
            diagnostics=(*retained_diagnostics, bool_diagnostic),
        )

    preservation, readiness = _build_preservation(
        window_stage,
        filters_rows=True,
    )
    return ProjectConcreteJoinedQualify(
        window_set=window_set,
        window_stage=window_stage,
        kind=ProjectJoinedQualifyStageKind.AUTHORED_QUALIFY,
        qualify_clause=clause,
        references=references,
        hidden_computations=hidden,
        predicate_value_type=predicate_type,
        value_types=value_types,
        diagnostics=retained_diagnostics,
        retention_effects=_SQL_ROW_RETENTION_EFFECTS,
        preservation=preservation,
        post_qualify=readiness,
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedQualifySet:
    """Canonical Slice-10-order Slice-11 results."""

    window_set: ProjectJoinedWindowStageSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    results: tuple[ProjectJoinedQualifyResult, ...]

    def __post_init__(self) -> None:
        if type(self.window_set) is not ProjectJoinedWindowStageSet or (
            type(self.results) is not tuple
            or len(self.results) != len(self.window_set.results)
            or any(
                type(result)
                not in {ProjectConcreteJoinedQualify, ProjectNonConcreteJoinedQualify}
                or result.window_set is not self.window_set
                or result.window_stage is not window_stage
                for result, window_stage in zip(
                    self.results,
                    self.window_set.results,
                    strict=True,
                )
            )
        ):
            raise ValueError("QUALIFY results must retain canonical Slice-10 order.")


def build_project_joined_qualifies(
    window_set: ProjectJoinedWindowStageSet,
) -> ProjectJoinedQualifySet:
    """Build one closed Slice-11 result per exact Slice-10 result."""

    if type(window_set) is not ProjectJoinedWindowStageSet:
        raise TypeError("QUALIFY set requires exact Slice-10 authority.")
    return ProjectJoinedQualifySet(
        window_set=window_set,
        results=tuple(
            build_project_joined_qualify(window_set, stage)
            for stage in window_set.results
        ),
    )
