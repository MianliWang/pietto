"""Private Phase-63 joined grouping, aggregate, satisfying, and risk authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from pietto._project import project_multifact as multifact
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectGrainFactorIdentity,
    ProjectGrainFactorSet,
    grain_dependency_closure,
)
from pietto._project.project_ir import ProjectIRJoinInputUseOccurrence
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputCandidateKey,
    ProjectIROutputDeterminationResult,
    ProjectIROutputDeterminationStatus,
    ProjectIROutputRelationalProperties,
    ProjectIROutputValueClass,
    ProjectIROutputValueClassSet,
    strictly_determines_output,
)
from pietto._project.project_joined_row_filter import (
    ProjectConcreteJoinedRowFilter,
    ProjectJoinedRowFilterResult,
    ProjectJoinedRowFilterSet,
    ProjectJoinedRowRetentionEffect,
    ProjectNonConcreteJoinedRowFilter,
    ProjectSQLPredicateTruth,
)
from pietto._project.project_joined_row_semantics import (
    ProjectJoinedRowFieldSemantics,
)
from pietto._project.project_scalar_namespaces import (
    ProjectConcreteJoinedNamespaceExpression,
    ProjectJoinedLetReferenceResolution,
    ProjectJoinedLetValue,
    ProjectJoinedNamespaceExpressionResult,
    ProjectJoinedNamespaceReferenceResolution,
    ProjectJoinedScalarNamespace,
    ProjectNonConcreteJoinedNamespaceExpression,
    analyze_project_joined_namespace_expression,
    resolve_project_joined_namespace_reference,
)
from pietto._project.project_scalar_references import (
    ProjectScalarEnvironmentField,
    ProjectScalarReferenceOccurrence,
    ProjectScalarReferenceResolution,
    scalar_field_reference_leaves,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    GroupByItem,
    LiteralExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity
from pietto.semantic import group_by as semantic_group_by
from pietto.semantic import satisfying as semantic_satisfying
from pietto.semantic import aggregates as semantic_aggregates
from pietto.semantic.model import ValueType, ValueTypeKind

__all__: tuple[str, ...] = ()


class ProjectJoinedAggregationMode(StrEnum):
    """The closed joined-row aggregate stage modes."""

    ABSENT = "absent"
    GROUPED = "grouped"
    GLOBAL = "global"


class ProjectJoinedGroupKeyIssueKind(StrEnum):
    """Closed group-key blocker families."""

    REFERENCE_NON_CONCRETE = "reference_non_concrete"
    COMPUTED_LET_EXPRESSION = "computed_let_expression"
    DUPLICATE_EFFECTIVE_FIELD = "duplicate_effective_field"


def _definition(
    input_filter: ProjectConcreteJoinedRowFilter,
) -> TableDef | QueryDef:
    definition = input_filter.entry.owner.definition
    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("Joined aggregation requires a table or query owner.")
    return cast(TableDef | QueryDef, definition)


def _field_semantics(
    input_filter: ProjectConcreteJoinedRowFilter,
    scalar_field: ProjectScalarEnvironmentField,
) -> ProjectJoinedRowFieldSemantics:
    matches = tuple(
        field for field in input_filter.fields if field.scalar_field is scalar_field
    )
    if len(matches) != 1:
        raise ValueError("Joined scalar field requires one exact Slice-6 occurrence.")
    return matches[0]


def _direct_field_resolution(
    input_filter: ProjectConcreteJoinedRowFilter,
    expression: NameExpr | DottedNameExpr,
    *,
    expand_let: bool,
) -> tuple[
    tuple[ProjectJoinedNamespaceReferenceResolution, ...],
    ProjectJoinedRowFieldSemantics | None,
    bool,
]:
    namespace = input_filter.namespace
    current: NameExpr | DottedNameExpr = expression
    resolutions: list[ProjectJoinedNamespaceReferenceResolution] = []
    seen_lets: set[int] = set()
    while True:
        resolution = resolve_project_joined_namespace_reference(
            namespace,
            ProjectScalarReferenceOccurrence(
                environment=namespace.binding_environment.scalar_environment,
                expression=current,
            ),
        )
        resolutions.append(resolution)
        if type(resolution) is ProjectScalarReferenceResolution:
            return (
                tuple(resolutions),
                None
                if resolution.target is None
                else _field_semantics(input_filter, resolution.target),
                False,
            )
        if type(resolution) is not ProjectJoinedLetReferenceResolution:
            raise AssertionError("direct field resolution lost its exact sum variant")
        if not expand_let:
            return tuple(resolutions), None, True
        target = resolution.target
        if id(target) in seen_lets:
            raise ValueError("Exact LET prefixes cannot contain a dependency cycle.")
        seen_lets.add(id(target))
        target_expression = target.occurrence.expression
        if type(target_expression) not in {NameExpr, DottedNameExpr}:
            return tuple(resolutions), None, True
        namespace = target.namespace
        current = cast(NameExpr | DottedNameExpr, target_expression)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedGroupKeyOccurrence:
    """One exact authored group key resolved to one final joined occurrence."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    source_ordinal: int
    item: GroupByItem = field(repr=False, compare=False, hash=False)
    effective_expression: NameExpr | DottedNameExpr = field(
        repr=False,
        compare=False,
        hash=False,
    )
    resolutions: tuple[ProjectJoinedNamespaceReferenceResolution, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    field_semantics: ProjectJoinedRowFieldSemantics
    value_type: ValueType

    def __post_init__(self) -> None:
        definition = _definition(self.input_filter)
        clause = definition.group_by_clause
        if (
            clause is None
            or type(self.source_ordinal) is not int
            or self.source_ordinal < 0
            or self.source_ordinal >= len(clause.items)
            or clause.items[self.source_ordinal] is not self.item
            or type(self.item) is not GroupByItem
            or not self.resolutions
            or self.item.key is not self.resolutions[0].reference.expression
            or self.effective_expression
            is not self.resolutions[-1].reference.expression
            or type(self.resolutions[-1]) is not ProjectScalarReferenceResolution
            or self.resolutions[-1].target is not self.field_semantics.scalar_field
            or self.value_type is not self.field_semantics.scalar_field.value_type
        ):
            raise ValueError(
                "Group key must retain exact authored and field authority."
            )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedGroupKeyIssue:
    """One authored group-key blocker retaining exact resolution evidence."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    source_ordinal: int
    item: GroupByItem = field(repr=False, compare=False, hash=False)
    kind: ProjectJoinedGroupKeyIssueKind
    resolutions: tuple[ProjectJoinedNamespaceReferenceResolution, ...] = field(
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    duplicate_of: ProjectJoinedGroupKeyOccurrence | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...]

    def __post_init__(self) -> None:
        definition = _definition(self.input_filter)
        clause = definition.group_by_clause
        if (
            clause is None
            or type(self.source_ordinal) is not int
            or self.source_ordinal < 0
            or self.source_ordinal >= len(clause.items)
            or clause.items[self.source_ordinal] is not self.item
            or type(self.kind) is not ProjectJoinedGroupKeyIssueKind
            or not self.diagnostics
            or any(type(item) is not Diagnostic for item in self.diagnostics)
        ):
            raise ValueError("Group-key issue requires exact authored evidence.")
        if self.kind is ProjectJoinedGroupKeyIssueKind.DUPLICATE_EFFECTIVE_FIELD:
            if type(self.duplicate_of) is not ProjectJoinedGroupKeyOccurrence:
                raise ValueError("Duplicate group key requires its earlier occurrence.")
        elif self.duplicate_of is not None:
            raise ValueError("Non-duplicate group-key issue cannot retain a winner.")


type ProjectJoinedGroupKeyResult = (
    ProjectJoinedGroupKeyOccurrence | ProjectJoinedGroupKeyIssue
)


class ProjectJoinedAggregateIssueKind(StrEnum):
    """Closed aggregate syntax/type blocker families."""

    NESTED = "nested"
    COMPOSED = "composed"
    ALIAS_REQUIRED = "alias_required"
    WRONG_ARITY = "wrong_arity"
    ARGUMENT_NON_CONCRETE = "argument_non_concrete"
    WRONG_ARGUMENT_TYPE = "wrong_argument_type"
    ARGUMENT_EXPRESSION_UNSUPPORTED = "argument_expression_unsupported"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedAggregateFieldDependency:
    """One exact underlying joined field read by an aggregate argument."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    selected_output_ordinal: int
    item: SelectItem = field(repr=False, compare=False, hash=False)
    reference: ProjectScalarReferenceOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    resolution: ProjectScalarReferenceResolution = field(
        repr=False,
        compare=False,
        hash=False,
    )
    let_path: tuple[ProjectJoinedLetValue, ...] = field(
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    field_semantics: ProjectJoinedRowFieldSemantics

    def __post_init__(self) -> None:
        definition = _definition(self.input_filter)
        if (
            self.selected_output_ordinal < 0
            or self.selected_output_ordinal >= len(definition.select_items)
            or definition.select_items[self.selected_output_ordinal] is not self.item
            or self.resolution.reference is not self.reference
            or self.resolution.target is not self.field_semantics.scalar_field
            or any(type(value) is not ProjectJoinedLetValue for value in self.let_path)
        ):
            raise ValueError(
                "Aggregate dependency requires exact joined-field evidence."
            )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedAggregateOccurrence:
    """One valid direct selected aggregate without final-output identity."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    selected_output_ordinal: int
    item: SelectItem = field(repr=False, compare=False, hash=False)
    call: CallExpr = field(repr=False, compare=False, hash=False)
    function_name: str
    argument_analysis: ProjectConcreteJoinedNamespaceExpression | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    field_dependencies: tuple[ProjectJoinedAggregateFieldDependency, ...] = ()
    result_value_type: ValueType

    def __post_init__(self) -> None:
        definition = _definition(self.input_filter)
        if (
            type(self.selected_output_ordinal) is not int
            or self.selected_output_ordinal < 0
            or self.selected_output_ordinal >= len(definition.select_items)
            or definition.select_items[self.selected_output_ordinal] is not self.item
            or self.item.expression is not self.call
            or self.item.alias is None
            or semantic_aggregates.semantic_aggregate_call_name(self.call)
            != self.function_name
        ):
            raise ValueError("Aggregate occurrence requires one exact selected call.")
        if self.call.arguments:
            if (
                type(self.argument_analysis)
                is not ProjectConcreteJoinedNamespaceExpression
                or self.argument_analysis.expression is not self.call.arguments[0]
                or self.argument_analysis.namespace is not self.input_filter.namespace
                or not self.field_dependencies
            ):
                raise ValueError("Aggregate argument requires exact namespace typing.")
        elif self.argument_analysis is not None or self.field_dependencies:
            raise ValueError("Zero-argument aggregate has no argument dependency.")
        if any(
            type(dependency) is not ProjectJoinedAggregateFieldDependency
            or dependency.input_filter is not self.input_filter
            or dependency.selected_output_ordinal != self.selected_output_ordinal
            or dependency.item is not self.item
            for dependency in self.field_dependencies
        ):
            raise ValueError("Aggregate dependencies must retain source order.")
        argument_type = (
            None
            if self.argument_analysis is None
            else self.argument_analysis.value_type
        )
        expected = semantic_aggregates.semantic_projection_aggregate_result_value_type(
            self.function_name,
            argument_type,
        )
        if expected is None or self.result_value_type != expected:
            raise ValueError(
                "Aggregate result type must come from the existing kernel."
            )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedAggregateIssue:
    """One invalid selected aggregate attempt with existing diagnostics."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    selected_output_ordinal: int
    item: SelectItem = field(repr=False, compare=False, hash=False)
    kind: ProjectJoinedAggregateIssueKind
    argument_analysis: ProjectJoinedNamespaceExpressionResult | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...]

    def __post_init__(self) -> None:
        definition = _definition(self.input_filter)
        if (
            self.selected_output_ordinal < 0
            or self.selected_output_ordinal >= len(definition.select_items)
            or definition.select_items[self.selected_output_ordinal] is not self.item
            or type(self.kind) is not ProjectJoinedAggregateIssueKind
            or not self.diagnostics
            or any(type(item) is not Diagnostic for item in self.diagnostics)
        ):
            raise ValueError("Aggregate issue requires exact selected evidence.")


type ProjectJoinedAggregateResult = (
    ProjectJoinedAggregateOccurrence | ProjectJoinedAggregateIssue
)


def _build_group_keys(
    input_filter: ProjectConcreteJoinedRowFilter,
) -> tuple[ProjectJoinedGroupKeyResult, ...]:
    definition = _definition(input_filter)
    clause = definition.group_by_clause
    if clause is None:
        return ()
    built: list[ProjectJoinedGroupKeyResult] = []
    retained_by_field: dict[int, ProjectJoinedGroupKeyOccurrence] = {}
    for source_ordinal, item in enumerate(clause.items):
        resolutions, field_semantics, computed = _direct_field_resolution(
            input_filter,
            item.key,
            expand_let=True,
        )
        if field_semantics is None:
            built.append(
                ProjectJoinedGroupKeyIssue(
                    input_filter=input_filter,
                    source_ordinal=source_ordinal,
                    item=item,
                    kind=(
                        ProjectJoinedGroupKeyIssueKind.COMPUTED_LET_EXPRESSION
                        if computed
                        else ProjectJoinedGroupKeyIssueKind.REFERENCE_NON_CONCRETE
                    ),
                    resolutions=resolutions,
                    diagnostics=(
                        semantic_group_by._unknown_field_diagnostic(item.key),
                    ),
                )
            )
            continue
        duplicate = retained_by_field.get(id(field_semantics))
        if duplicate is not None:
            built.append(
                ProjectJoinedGroupKeyIssue(
                    input_filter=input_filter,
                    source_ordinal=source_ordinal,
                    item=item,
                    kind=ProjectJoinedGroupKeyIssueKind.DUPLICATE_EFFECTIVE_FIELD,
                    resolutions=resolutions,
                    duplicate_of=duplicate,
                    diagnostics=(
                        semantic_group_by._duplicate_group_key_diagnostic(item.key),
                    ),
                )
            )
            continue
        occurrence = ProjectJoinedGroupKeyOccurrence(
            input_filter=input_filter,
            source_ordinal=source_ordinal,
            item=item,
            effective_expression=resolutions[-1].reference.expression,
            resolutions=resolutions,
            field_semantics=field_semantics,
            value_type=field_semantics.scalar_field.value_type,
        )
        retained_by_field[id(field_semantics)] = occurrence
        built.append(occurrence)
    return tuple(built)


def _let_expansions(
    input_filter: ProjectConcreteJoinedRowFilter,
) -> Mapping[str, Expression]:
    return {
        value.occurrence.binding.name: value.occurrence.expression
        for value in input_filter.namespace.let_values
    }


def _aggregate_dependencies(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    selected_output_ordinal: int,
    item: SelectItem,
    expression: Expression,
) -> tuple[ProjectJoinedAggregateFieldDependency, ...]:
    return tuple(
        ProjectJoinedAggregateFieldDependency(
            input_filter=input_filter,
            selected_output_ordinal=selected_output_ordinal,
            item=item,
            reference=reference,
            resolution=resolution,
            let_path=let_path,
            field_semantics=field_semantics,
        )
        for reference, resolution, let_path, field_semantics in (
            _resolved_field_dependencies(
                input_filter=input_filter,
                namespace=input_filter.namespace,
                expression=expression,
            )
        )
    )


type _ResolvedFieldDependency = tuple[
    ProjectScalarReferenceOccurrence,
    ProjectScalarReferenceResolution,
    tuple[ProjectJoinedLetValue, ...],
    ProjectJoinedRowFieldSemantics,
]


def _resolved_field_dependencies(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    namespace: ProjectJoinedScalarNamespace,
    expression: Expression,
) -> tuple[_ResolvedFieldDependency, ...]:
    dependencies: list[_ResolvedFieldDependency] = []

    def visit(
        namespace: ProjectJoinedScalarNamespace,
        root: Expression,
        let_path: tuple[ProjectJoinedLetValue, ...],
    ) -> None:
        for leaf in scalar_field_reference_leaves(root):
            resolution = resolve_project_joined_namespace_reference(
                namespace,
                ProjectScalarReferenceOccurrence(
                    environment=namespace.binding_environment.scalar_environment,
                    expression=leaf,
                ),
            )
            if type(resolution) is ProjectJoinedLetReferenceResolution:
                target = resolution.target
                if any(target is value for value in let_path):
                    raise ValueError("Exact LET prefixes cannot contain a cycle.")
                visit(
                    target.namespace,
                    target.occurrence.expression,
                    (*let_path, target),
                )
                continue
            if type(resolution) is not ProjectScalarReferenceResolution or (
                resolution.target is None
            ):
                raise ValueError("Valid aggregate lost a concrete field dependency.")
            dependencies.append(
                (
                    resolution.reference,
                    resolution,
                    let_path,
                    _field_semantics(input_filter, resolution.target),
                )
            )

    visit(namespace, expression, ())
    return tuple(dependencies)


def _reference_blocker_diagnostics(
    analysis: ProjectNonConcreteJoinedNamespaceExpression,
) -> tuple[Diagnostic, ...]:
    if analysis.blocking_resolutions:
        return tuple(
            semantic_group_by._unknown_field_diagnostic(resolution.reference.expression)
            for resolution in analysis.blocking_resolutions
        )
    return analysis.diagnostics


def _aggregate_attempt(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    selected_output_ordinal: int,
    item: SelectItem,
) -> ProjectJoinedAggregateResult:
    expression = item.expression
    nested = semantic_aggregates.nested_semantic_aggregate(expression)
    if nested is not None:
        return ProjectJoinedAggregateIssue(
            input_filter=input_filter,
            selected_output_ordinal=selected_output_ordinal,
            item=item,
            kind=ProjectJoinedAggregateIssueKind.NESTED,
            diagnostics=(semantic_aggregates.nested_aggregate_diagnostic(nested),),
        )
    if not semantic_aggregates.is_semantic_aggregate_call(expression):
        return ProjectJoinedAggregateIssue(
            input_filter=input_filter,
            selected_output_ordinal=selected_output_ordinal,
            item=item,
            kind=ProjectJoinedAggregateIssueKind.COMPOSED,
            diagnostics=(
                semantic_aggregates.deferred_composition_diagnostic(expression),
            ),
        )
    if type(expression) is not CallExpr:
        raise AssertionError("semantic aggregate call lost its CallExpr root")
    function_name = semantic_aggregates.semantic_aggregate_call_name(expression)
    if function_name is None:
        raise AssertionError("semantic aggregate call lost its canonical name")
    if item.alias is None:
        return ProjectJoinedAggregateIssue(
            input_filter=input_filter,
            selected_output_ordinal=selected_output_ordinal,
            item=item,
            kind=ProjectJoinedAggregateIssueKind.ALIAS_REQUIRED,
            diagnostics=(
                semantic_aggregates.aggregate_alias_required_diagnostic(expression),
            ),
        )
    if not semantic_aggregates.is_supported_semantic_aggregate_arity(
        function_name,
        len(expression.arguments),
    ):
        return ProjectJoinedAggregateIssue(
            input_filter=input_filter,
            selected_output_ordinal=selected_output_ordinal,
            item=item,
            kind=ProjectJoinedAggregateIssueKind.WRONG_ARITY,
            diagnostics=(semantic_aggregates.wrong_arity_diagnostic(expression),),
        )

    argument_analysis: ProjectConcreteJoinedNamespaceExpression | None = None
    dependencies: tuple[ProjectJoinedAggregateFieldDependency, ...] = ()
    argument_type: ValueType | None = None
    if expression.arguments:
        argument = expression.arguments[0]
        analysis = analyze_project_joined_namespace_expression(
            input_filter.namespace,
            argument,
        )
        if type(analysis) is ProjectNonConcreteJoinedNamespaceExpression:
            diagnostics = _reference_blocker_diagnostics(analysis)
            if not analysis.blocking_resolutions:
                diagnostics = (
                    *diagnostics,
                    semantic_aggregates.deferred_argument_expression_diagnostic(
                        expression
                    ),
                )
            return ProjectJoinedAggregateIssue(
                input_filter=input_filter,
                selected_output_ordinal=selected_output_ordinal,
                item=item,
                kind=ProjectJoinedAggregateIssueKind.ARGUMENT_NON_CONCRETE,
                argument_analysis=analysis,
                diagnostics=diagnostics,
            )
        if type(analysis) is not ProjectConcreteJoinedNamespaceExpression:
            raise AssertionError("aggregate argument analysis lost its exact variant")
        argument_analysis = analysis
        argument_type = analysis.value_type
        let_resolutions = tuple(
            resolution
            for resolution in analysis.resolutions
            if type(resolution) is ProjectJoinedLetReferenceResolution
        )
        let_expansions = _let_expansions(input_filter)
        if (
            let_resolutions
            and not semantic_aggregates.aggregate_argument_can_use_let_scope(
                function_name,
                argument,
                let_expansions,
            )
        ):
            return ProjectJoinedAggregateIssue(
                input_filter=input_filter,
                selected_output_ordinal=selected_output_ordinal,
                item=item,
                kind=(ProjectJoinedAggregateIssueKind.ARGUMENT_EXPRESSION_UNSUPPORTED),
                argument_analysis=analysis,
                diagnostics=(
                    semantic_aggregates.deferred_argument_expression_diagnostic(
                        expression
                    ),
                ),
            )
        if not semantic_aggregates.is_supported_semantic_aggregate_argument(
            function_name,
            argument_type,
        ):
            return ProjectJoinedAggregateIssue(
                input_filter=input_filter,
                selected_output_ordinal=selected_output_ordinal,
                item=item,
                kind=ProjectJoinedAggregateIssueKind.WRONG_ARGUMENT_TYPE,
                argument_analysis=analysis,
                diagnostics=(
                    semantic_aggregates.wrong_argument_type_diagnostic(
                        expression,
                        actual_name=argument_type.resolved_type.name,
                    ),
                ),
            )
        if not semantic_aggregates.is_supported_semantic_aggregate_argument_expression(
            function_name,
            argument,
            argument_type,
            let_expansions=let_expansions,
        ):
            return ProjectJoinedAggregateIssue(
                input_filter=input_filter,
                selected_output_ordinal=selected_output_ordinal,
                item=item,
                kind=(ProjectJoinedAggregateIssueKind.ARGUMENT_EXPRESSION_UNSUPPORTED),
                argument_analysis=analysis,
                diagnostics=(
                    semantic_aggregates.deferred_argument_expression_diagnostic(
                        expression
                    ),
                ),
            )
        dependencies = _aggregate_dependencies(
            input_filter=input_filter,
            selected_output_ordinal=selected_output_ordinal,
            item=item,
            expression=argument,
        )

    result_type = semantic_aggregates.semantic_projection_aggregate_result_value_type(
        function_name,
        argument_type,
    )
    if result_type is None:
        raise AssertionError("valid aggregate inputs lost an existing result type")
    return ProjectJoinedAggregateOccurrence(
        input_filter=input_filter,
        selected_output_ordinal=selected_output_ordinal,
        item=item,
        call=expression,
        function_name=function_name,
        argument_analysis=argument_analysis,
        field_dependencies=dependencies,
        result_value_type=result_type,
    )


def _build_aggregate_results(
    input_filter: ProjectConcreteJoinedRowFilter,
) -> tuple[ProjectJoinedAggregateResult, ...]:
    definition = _definition(input_filter)
    return tuple(
        _aggregate_attempt(
            input_filter=input_filter,
            selected_output_ordinal=ordinal,
            item=item,
        )
        for ordinal, item in enumerate(definition.select_items)
        if type(item.expression) is not WindowExpr
        and semantic_aggregates.contains_semantic_aggregate(item.expression)
    )


class ProjectJoinedStageOutputRole(StrEnum):
    """The two Slice-9 plan-independent stage output roles."""

    GROUP_KEY = "group_key"
    AGGREGATE_RESULT = "aggregate_result"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedStageOutputOccurrence:
    """One selected grouped-stage value without final field identity."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    selected_output_ordinal: int
    item: SelectItem = field(repr=False, compare=False, hash=False)
    output_name: str
    role: ProjectJoinedStageOutputRole
    value_type: ValueType
    group_key: ProjectJoinedGroupKeyOccurrence | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    aggregate: ProjectJoinedAggregateOccurrence | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        definition = _definition(self.input_filter)
        if (
            type(self.selected_output_ordinal) is not int
            or self.selected_output_ordinal < 0
            or self.selected_output_ordinal >= len(definition.select_items)
            or definition.select_items[self.selected_output_ordinal] is not self.item
            or type(self.output_name) is not str
            or not self.output_name
            or self.output_name != _projection_output_name(self.item)
            or type(self.role) is not ProjectJoinedStageOutputRole
        ):
            raise ValueError(
                "Stage output requires exact selected occurrence evidence."
            )
        if self.role is ProjectJoinedStageOutputRole.GROUP_KEY:
            if (
                type(self.group_key) is not ProjectJoinedGroupKeyOccurrence
                or self.aggregate is not None
                or self.value_type is not self.group_key.value_type
            ):
                raise ValueError(
                    "Group output requires one exact group-key occurrence."
                )
        elif (
            self.group_key is not None
            or type(self.aggregate) is not ProjectJoinedAggregateOccurrence
            or self.value_type is not self.aggregate.result_value_type
        ):
            raise ValueError(
                "Aggregate output requires one exact aggregate occurrence."
            )


class ProjectJoinedSelectedOutputIssueKind(StrEnum):
    """Closed grouped/global selected-output blocker families."""

    DUPLICATE_OUTPUT_NAME = "duplicate_output_name"
    UNKNOWN_GROUP_KEY_PROJECTION = "unknown_group_key_projection"
    NON_GROUPED_FIELD_PROJECTION = "non_grouped_field_projection"
    GROUPED_SCALAR_PROJECTION = "grouped_scalar_projection"
    MIXED_GLOBAL_ROW_PROJECTION = "mixed_global_row_projection"
    PURE_GROUPING = "pure_grouping"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedSelectedOutputIssue:
    """One selected-output blocker with an existing diagnostic."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    selected_output_ordinal: int | None
    item: SelectItem | None = field(repr=False, compare=False, hash=False)
    kind: ProjectJoinedSelectedOutputIssueKind
    diagnostics: tuple[Diagnostic, ...]

    def __post_init__(self) -> None:
        definition = _definition(self.input_filter)
        if type(self.kind) is not ProjectJoinedSelectedOutputIssueKind or (
            not self.diagnostics
            or any(type(item) is not Diagnostic for item in self.diagnostics)
        ):
            raise ValueError("Selected-output issue requires an exact diagnostic.")
        if self.kind is ProjectJoinedSelectedOutputIssueKind.PURE_GROUPING:
            if self.selected_output_ordinal is not None or self.item is not None:
                raise ValueError("Pure grouping issue belongs to the GROUP BY clause.")
        elif (
            type(self.selected_output_ordinal) is not int
            or self.selected_output_ordinal < 0
            or self.selected_output_ordinal >= len(definition.select_items)
            or definition.select_items[self.selected_output_ordinal] is not self.item
        ):
            raise ValueError("Selected-output issue lost its exact source ordinal.")


def _projection_output_name(item: SelectItem) -> str | None:
    return semantic_group_by._projection_output_name(item)


def _group_key_projection(
    input_filter: ProjectConcreteJoinedRowFilter,
    item: SelectItem,
    group_keys: tuple[ProjectJoinedGroupKeyOccurrence, ...],
) -> ProjectJoinedGroupKeyOccurrence | None:
    if type(item.expression) not in {NameExpr, DottedNameExpr}:
        return None
    _, field_semantics, _ = _direct_field_resolution(
        input_filter,
        cast(NameExpr | DottedNameExpr, item.expression),
        expand_let=False,
    )
    if field_semantics is None:
        return None
    matches = tuple(key for key in group_keys if key.field_semantics is field_semantics)
    if len(matches) > 1:
        raise ValueError("Concrete group keys cannot repeat one field occurrence.")
    return None if not matches else matches[0]


def _build_stage_outputs(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    mode: ProjectJoinedAggregationMode,
    group_keys: tuple[ProjectJoinedGroupKeyOccurrence, ...],
    aggregate_results: tuple[ProjectJoinedAggregateResult, ...],
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
) -> tuple[
    tuple[ProjectJoinedStageOutputOccurrence, ...],
    tuple[ProjectJoinedSelectedOutputIssue, ...],
]:
    definition = _definition(input_filter)
    if mode is ProjectJoinedAggregationMode.ABSENT:
        return (), ()
    aggregate_by_item = {id(aggregate.item): aggregate for aggregate in aggregates}
    outputs: list[ProjectJoinedStageOutputOccurrence] = []
    issues: list[ProjectJoinedSelectedOutputIssue] = []
    seen_names: set[str] = set()
    non_aggregate_items: list[tuple[int, SelectItem]] = []
    for ordinal, item in enumerate(definition.select_items):
        output_name = _projection_output_name(item)
        if output_name is not None:
            if output_name in seen_names:
                issues.append(
                    ProjectJoinedSelectedOutputIssue(
                        input_filter=input_filter,
                        selected_output_ordinal=ordinal,
                        item=item,
                        kind=(
                            ProjectJoinedSelectedOutputIssueKind.DUPLICATE_OUTPUT_NAME
                        ),
                        diagnostics=(
                            semantic_group_by._duplicate_projection_diagnostic(
                                item,
                                output_name,
                            ),
                        ),
                    )
                )
                continue
            seen_names.add(output_name)
        if type(item.expression) is WindowExpr:
            continue
        if semantic_aggregates.contains_semantic_aggregate(item.expression):
            aggregate = aggregate_by_item.get(id(item))
            if aggregate is not None and output_name is not None:
                outputs.append(
                    ProjectJoinedStageOutputOccurrence(
                        input_filter=input_filter,
                        selected_output_ordinal=ordinal,
                        item=item,
                        output_name=output_name,
                        role=ProjectJoinedStageOutputRole.AGGREGATE_RESULT,
                        value_type=aggregate.result_value_type,
                        aggregate=aggregate,
                    )
                )
            continue
        non_aggregate_items.append((ordinal, item))
        if mode is ProjectJoinedAggregationMode.GLOBAL:
            continue
        output_name = _projection_output_name(item)
        key = _group_key_projection(input_filter, item, group_keys)
        if key is not None and output_name is not None:
            outputs.append(
                ProjectJoinedStageOutputOccurrence(
                    input_filter=input_filter,
                    selected_output_ordinal=ordinal,
                    item=item,
                    output_name=output_name,
                    role=ProjectJoinedStageOutputRole.GROUP_KEY,
                    value_type=key.value_type,
                    group_key=key,
                )
            )
            continue
        if type(item.expression) in {NameExpr, DottedNameExpr}:
            _, field_semantics, _ = _direct_field_resolution(
                input_filter,
                cast(NameExpr | DottedNameExpr, item.expression),
                expand_let=False,
            )
            if field_semantics is None:
                issue_kind = (
                    ProjectJoinedSelectedOutputIssueKind.UNKNOWN_GROUP_KEY_PROJECTION
                )
                diagnostic = semantic_group_by._unknown_field_diagnostic(
                    cast(NameExpr | DottedNameExpr, item.expression)
                )
            else:
                issue_kind = (
                    ProjectJoinedSelectedOutputIssueKind.NON_GROUPED_FIELD_PROJECTION
                )
                diagnostic = semantic_group_by._non_grouped_projection_diagnostic(
                    cast(NameExpr | DottedNameExpr, item.expression)
                )
        else:
            issue_kind = ProjectJoinedSelectedOutputIssueKind.GROUPED_SCALAR_PROJECTION
            diagnostic = semantic_group_by._scalar_grouped_projection_diagnostic(
                item.expression
            )
        issues.append(
            ProjectJoinedSelectedOutputIssue(
                input_filter=input_filter,
                selected_output_ordinal=ordinal,
                item=item,
                kind=issue_kind,
                diagnostics=(diagnostic,),
            )
        )

    if (
        mode is ProjectJoinedAggregationMode.GLOBAL
        and aggregates
        and non_aggregate_items
    ):
        first = aggregates[0]
        issues.append(
            ProjectJoinedSelectedOutputIssue(
                input_filter=input_filter,
                selected_output_ordinal=first.selected_output_ordinal,
                item=first.item,
                kind=ProjectJoinedSelectedOutputIssueKind.MIXED_GLOBAL_ROW_PROJECTION,
                diagnostics=(
                    semantic_aggregates.mixed_projection_diagnostic(first.call),
                ),
            )
        )
    if (
        mode is ProjectJoinedAggregationMode.GROUPED
        and not aggregate_results
        and not issues
    ):
        issues.append(
            ProjectJoinedSelectedOutputIssue(
                input_filter=input_filter,
                selected_output_ordinal=None,
                item=None,
                kind=ProjectJoinedSelectedOutputIssueKind.PURE_GROUPING,
                diagnostics=(
                    semantic_group_by._pure_grouped_output_deferred_diagnostic(
                        definition
                    ),
                ),
            )
        )
    return tuple(outputs), tuple(issues)


def _value_class_for_input_field(
    properties: ProjectIROutputRelationalProperties,
    field_semantics: ProjectJoinedRowFieldSemantics,
) -> ProjectIROutputValueClass:
    matches = tuple(
        value_class
        for value_class in properties.value_classes
        if any(member is field_semantics.input_field for member in value_class.members)
    )
    if len(matches) != 1:
        raise ValueError("Group field requires one exact input value class.")
    return matches[0]


def _value_class_set(
    properties: ProjectIROutputRelationalProperties,
    classes: tuple[ProjectIROutputValueClass, ...],
) -> ProjectIROutputValueClassSet:
    selected = set(classes)
    return ProjectIROutputValueClassSet(
        index=properties.fd_index,
        classes=tuple(
            value_class
            for value_class in properties.fd_index.universe
            if value_class in selected
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedGroupProtection:
    """Complete STRICT-FD protection evidence for one exact JOIN input use."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_properties: ProjectIROutputRelationalProperties = field(
        repr=False,
        compare=False,
        hash=False,
    )
    introduction_use: ProjectIRJoinInputUseOccurrence
    group_keys: tuple[ProjectJoinedGroupKeyOccurrence, ...]
    seed: ProjectIROutputValueClassSet
    strict_keys: tuple[ProjectIROutputCandidateKey, ...]
    determinations: tuple[ProjectIROutputDeterminationResult, ...]
    protected_factors: tuple[ProjectGrainFactorIdentity, ...]

    def __post_init__(self) -> None:
        if (
            type(self.input_properties) is not ProjectIROutputRelationalProperties
            or type(self.introduction_use) is not ProjectIRJoinInputUseOccurrence
            or not self.group_keys
            or any(
                type(key) is not ProjectJoinedGroupKeyOccurrence
                or key.input_filter is not self.input_filter
                or key.field_semantics.input_properties is not self.input_properties
                or key.field_semantics.introduction_use is not self.introduction_use
                for key in self.group_keys
            )
            or self.seed.index is not self.input_properties.fd_index
            or self.strict_keys
            != tuple(
                key
                for key in self.input_properties.keys
                if key.strength is ProjectRowUniquenessStrength.STRICT
            )
            or len(self.determinations) != len(self.strict_keys)
            or any(
                determination.requested.classes != key.determinants
                for determination, key in zip(
                    self.determinations,
                    self.strict_keys,
                    strict=True,
                )
            )
        ):
            raise ValueError("Group protection requires complete exact key evidence.")
        proven = any(
            determination.status is ProjectIROutputDeterminationStatus.PROVEN
            for determination in self.determinations
        )
        expected_protected = (
            multifact._localized_input_factors(
                grain=self.input_properties.grain,
                introduction_use=self.introduction_use,
                final_grain=(
                    self.input_filter.joined_semantics.multifact_region.final_properties.relational.grain
                ),
            )
            if proven
            else ()
        )
        if (
            any(
                determination.seed.index is not self.input_properties.fd_index
                or determination.seed is not self.seed
                for determination in self.determinations
            )
            or self.protected_factors != expected_protected
        ):
            raise ValueError("Protected factors require a proven STRICT key.")


def _build_group_protections(
    input_filter: ProjectConcreteJoinedRowFilter,
    group_keys: tuple[ProjectJoinedGroupKeyOccurrence, ...],
) -> tuple[ProjectJoinedGroupProtection, ...]:
    region = input_filter.joined_semantics.multifact_region
    final_grain = region.final_properties.relational.grain
    roots: list[
        tuple[ProjectIROutputRelationalProperties, ProjectIRJoinInputUseOccurrence]
    ] = []
    for key in group_keys:
        root = (
            key.field_semantics.input_properties,
            key.field_semantics.introduction_use,
        )
        if not any(
            retained[0] is root[0] and retained[1] is root[1] for retained in roots
        ):
            roots.append(root)
    protections: list[ProjectJoinedGroupProtection] = []
    for properties, introduction_use in roots:
        local_keys = tuple(
            key
            for key in group_keys
            if key.field_semantics.input_properties is properties
            and key.field_semantics.introduction_use is introduction_use
        )
        classes = tuple(
            _value_class_for_input_field(properties, key.field_semantics)
            for key in local_keys
        )
        seed = _value_class_set(properties, classes)
        strict_keys = tuple(
            key
            for key in properties.keys
            if key.strength is ProjectRowUniquenessStrength.STRICT
        )
        determinations = tuple(
            strictly_determines_output(
                properties.fd_index,
                seed,
                _value_class_set(properties, key.determinants),
            )
            for key in strict_keys
        )
        protected = (
            multifact._localized_input_factors(
                grain=properties.grain,
                introduction_use=introduction_use,
                final_grain=final_grain,
            )
            if any(
                determination.status is ProjectIROutputDeterminationStatus.PROVEN
                for determination in determinations
            )
            else ()
        )
        protections.append(
            ProjectJoinedGroupProtection(
                input_filter=input_filter,
                input_properties=properties,
                introduction_use=introduction_use,
                group_keys=local_keys,
                seed=seed,
                strict_keys=strict_keys,
                determinations=determinations,
                protected_factors=protected,
            )
        )
    return tuple(protections)


def _ordered_factors(
    final_factors: tuple[ProjectGrainFactorIdentity, ...],
    values: tuple[ProjectGrainFactorIdentity, ...],
) -> tuple[ProjectGrainFactorIdentity, ...]:
    selected = set(values)
    ordered = tuple(factor for factor in final_factors if factor in selected)
    if len(ordered) != len(selected):
        raise ValueError("Contextual factors require the exact final grain universe.")
    return ordered


def _argument_factors(
    aggregate: ProjectJoinedAggregateOccurrence,
) -> tuple[ProjectGrainFactorIdentity, ...]:
    final_grain = aggregate.input_filter.joined_semantics.property_bridge.grain
    if not aggregate.call.arguments:
        return final_grain.active
    factors = tuple(
        factor
        for dependency in aggregate.field_dependencies
        for factor in multifact._localized_input_factors(
            grain=dependency.field_semantics.input_properties.grain,
            introduction_use=dependency.field_semantics.introduction_use,
            final_grain=final_grain,
        )
    )
    return _ordered_factors(final_grain.active, factors)


def _multiplicity_exposures(
    *,
    aggregate: ProjectJoinedAggregateOccurrence,
    comparison: multifact.ProjectFactGrainComparison,
) -> tuple[multifact.ProjectFactMultiplicityExposure, ...]:
    if comparison.status is not multifact.ProjectIRGrainComparisonStatus.RIGHT_FINER:
        return ()
    unresolved = tuple(
        factor
        for factor in comparison.right.factors
        if factor not in comparison.left_to_right.closure.factors
    )
    region = aggregate.input_filter.joined_semantics.row_source.region
    exposures: list[multifact.ProjectFactMultiplicityExposure] = []
    covered: set[ProjectGrainFactorIdentity] = set()
    for join in region.joins:
        additions = tuple(
            cast(multifact.ProjectJoinGrainFactorIdentity, factor)
            for factor in unresolved
            if type(factor) is multifact.ProjectJoinGrainFactorIdentity
            and any(factor.introduction_use == use.ref for use in join.input_uses)
        )
        if additions:
            exposures.append(
                multifact.ProjectFactMultiplicityExposure(
                    join=join,
                    factor_additions=additions,
                )
            )
            covered.update(additions)
    if covered != set(unresolved):
        raise ValueError("Aggregate fanout evidence must cover every finer factor.")
    return tuple(exposures)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedAggregateGrainLinkage:
    """One aggregate's exact contextual grain and final fanout proof."""

    aggregate: ProjectJoinedAggregateOccurrence
    multifact_region: multifact.ProjectMultiFactConcreteRegion = field(
        repr=False,
        compare=False,
        hash=False,
    )
    argument_factors: tuple[ProjectGrainFactorIdentity, ...]
    group_protection_factors: tuple[ProjectGrainFactorIdentity, ...]
    combined_seed: ProjectGrainFactorSet
    closure: ProjectGrainFactorSet
    contextual_grain: multifact.ProjectFactContextualGrain
    final_grain: multifact.ProjectIRProvidedIntrinsicGrain
    final_comparison: multifact.ProjectFactGrainComparison
    multiplicity_exposures: tuple[multifact.ProjectFactMultiplicityExposure, ...]
    multiplicity_risks: tuple[multifact.ProjectMultiFactMultiplicityRisk, ...]
    requirements: tuple[multifact.ProjectMultiFactRequirement, ...]

    def __post_init__(self) -> None:
        if (
            type(self.aggregate) is not ProjectJoinedAggregateOccurrence
            or type(self.multifact_region)
            is not multifact.ProjectMultiFactConcreteRegion
            or type(self.final_grain) is not multifact.ProjectIRProvidedIntrinsicGrain
            or type(self.combined_seed) is not ProjectGrainFactorSet
            or type(self.closure) is not ProjectGrainFactorSet
            or type(self.contextual_grain) is not multifact.ProjectFactContextualGrain
            or type(self.final_comparison) is not multifact.ProjectFactGrainComparison
        ):
            raise TypeError("Aggregate grain linkage requires exact typed evidence.")
        expected_argument = _argument_factors(self.aggregate)
        expected_combined = _ordered_factors(
            self.final_grain.active,
            (*self.argument_factors, *self.group_protection_factors),
        )
        expected_closure = grain_dependency_closure(
            self.multifact_region.grain_index,
            self.combined_seed,
        )
        if (
            self.multifact_region
            is not self.aggregate.input_filter.joined_semantics.multifact_region
            or self.final_grain
            is not self.multifact_region.final_properties.relational.grain
            or self.combined_seed.universe
            is not self.multifact_region.grain_index.universe
            or self.closure.universe is not self.combined_seed.universe
            or self.contextual_grain.authority is not self.final_grain
            or self.contextual_grain.factors != self.closure.factors
            or self.final_comparison.left is not self.contextual_grain
            or self.final_comparison.right.authority is not self.final_grain
            or self.argument_factors != expected_argument
            or self.combined_seed.factors != expected_combined
            or self.closure.factors != expected_closure.factors
        ):
            raise ValueError("Aggregate grain linkage requires exact Phase-62 roots.")
        has_risk = bool(self.multiplicity_exposures)
        unresolved = tuple(
            factor
            for factor in self.final_comparison.right.factors
            if factor not in self.final_comparison.left_to_right.closure.factors
        )
        retained_additions = tuple(
            factor
            for exposure in self.multiplicity_exposures
            for factor in exposure.factor_additions
        )
        expected_risks = (
            (multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,)
            if has_risk
            else ()
        )
        expected_requirements = (
            (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
            if has_risk
            else ()
        )
        if (
            self.multiplicity_risks != expected_risks
            or self.requirements != expected_requirements
            or has_risk
            is not (
                self.final_comparison.status
                is multifact.ProjectIRGrainComparisonStatus.RIGHT_FINER
            )
            or len(set(retained_additions)) != len(retained_additions)
            or set(retained_additions) != set(unresolved)
        ):
            raise ValueError("Aggregate risk must derive from exact finer grain.")


def _build_grain_linkages(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
    protections: tuple[ProjectJoinedGroupProtection, ...],
) -> tuple[ProjectJoinedAggregateGrainLinkage, ...]:
    region = input_filter.joined_semantics.multifact_region
    index = region.grain_index
    final_grain = region.final_properties.relational.grain
    protection_factors = _ordered_factors(
        final_grain.active,
        tuple(
            factor
            for protection in protections
            for factor in protection.protected_factors
        ),
    )
    full = multifact.ProjectFactContextualGrain(
        authority=final_grain,
        state=final_grain.state,
        factors=final_grain.active,
        evidence=region.final_properties,
    )
    linkages: list[ProjectJoinedAggregateGrainLinkage] = []
    for aggregate in aggregates:
        argument_factors = _argument_factors(aggregate)
        combined = _ordered_factors(
            final_grain.active,
            (*argument_factors, *protection_factors),
        )
        seed = multifact._factor_set(index, combined)
        closure = grain_dependency_closure(index, seed)
        contextual = multifact.ProjectFactContextualGrain(
            authority=final_grain,
            state=(
                ProjectGrainBasisState.FACTORIZED
                if closure.factors
                else ProjectGrainBasisState.GLOBAL
            ),
            factors=closure.factors,
            evidence=aggregate,
        )
        comparison = multifact._compare_grains(index, contextual, full)
        exposures = _multiplicity_exposures(
            aggregate=aggregate,
            comparison=comparison,
        )
        linkages.append(
            ProjectJoinedAggregateGrainLinkage(
                aggregate=aggregate,
                multifact_region=region,
                argument_factors=argument_factors,
                group_protection_factors=protection_factors,
                combined_seed=seed,
                closure=closure,
                contextual_grain=contextual,
                final_grain=final_grain,
                final_comparison=comparison,
                multiplicity_exposures=exposures,
                multiplicity_risks=(
                    (multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,)
                    if exposures
                    else ()
                ),
                requirements=(
                    (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
                    if exposures
                    else ()
                ),
            )
        )
    return tuple(linkages)


def _pair_shape(
    *,
    left: ProjectJoinedAggregateGrainLinkage,
    right: ProjectJoinedAggregateGrainLinkage,
    comparison: multifact.ProjectFactGrainComparison,
    common: multifact.ProjectCommonGrainResult,
) -> tuple[
    multifact.ProjectMultiFactStructuralAlignment,
    ProjectJoinedAggregateGrainLinkage | None,
    tuple[multifact.ProjectCommonGrainCandidateEvidence, ...],
]:
    chasm_candidates = (
        common.candidates
        if comparison.status is multifact.ProjectIRGrainComparisonStatus.INCOMPARABLE
        and left.contextual_grain.factors
        and right.contextual_grain.factors
        else ()
    )
    finer: ProjectJoinedAggregateGrainLinkage | None = None
    if (
        left.contextual_grain.state is right.contextual_grain.state
        and left.contextual_grain.factors == right.contextual_grain.factors
    ):
        structural = multifact.ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED
    elif comparison.status is multifact.ProjectIRGrainComparisonStatus.EQUAL:
        structural = (
            multifact.ProjectMultiFactStructuralAlignment.STRUCTURALLY_ALIGNABLE
        )
    elif comparison.status is multifact.ProjectIRGrainComparisonStatus.LEFT_FINER:
        structural = (
            multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        )
        finer = left
    elif comparison.status is multifact.ProjectIRGrainComparisonStatus.RIGHT_FINER:
        structural = (
            multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        )
        finer = right
    elif common.status in {
        multifact.ProjectCommonGrainStatus.UNIQUE,
        multifact.ProjectCommonGrainStatus.AMBIGUOUS,
    }:
        structural = (
            multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        )
    else:
        structural = multifact.ProjectMultiFactStructuralAlignment.INCOMPATIBLE
    return structural, finer, chasm_candidates


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedAggregatePairLinkage:
    """Winner-free pairwise contextual-grain and chasm evidence."""

    left: ProjectJoinedAggregateGrainLinkage
    right: ProjectJoinedAggregateGrainLinkage
    grain_comparison: multifact.ProjectFactGrainComparison
    common_grain: multifact.ProjectCommonGrainResult
    chasm_candidates: tuple[multifact.ProjectCommonGrainCandidateEvidence, ...]
    structural: multifact.ProjectMultiFactStructuralAlignment
    finer: ProjectJoinedAggregateGrainLinkage | None
    multiplicity_risks: tuple[multifact.ProjectMultiFactMultiplicityRisk, ...]
    requirements: tuple[multifact.ProjectMultiFactRequirement, ...]

    def __post_init__(self) -> None:
        if (
            type(self.left) is not ProjectJoinedAggregateGrainLinkage
            or type(self.right) is not ProjectJoinedAggregateGrainLinkage
            or self.left is self.right
            or self.left.multifact_region is not self.right.multifact_region
            or self.grain_comparison.left is not self.left.contextual_grain
            or self.grain_comparison.right is not self.right.contextual_grain
            or any(
                not any(
                    candidate is retained for retained in self.common_grain.candidates
                )
                for candidate in self.chasm_candidates
            )
        ):
            raise ValueError("Aggregate pair linkage requires exact shared authority.")
        expected_structural, expected_finer, expected_chasms = _pair_shape(
            left=self.left,
            right=self.right,
            comparison=self.grain_comparison,
            common=self.common_grain,
        )
        has_chasm = bool(self.chasm_candidates)
        expected_risks: list[multifact.ProjectMultiFactMultiplicityRisk] = []
        if self.left.multiplicity_exposures or self.right.multiplicity_exposures:
            expected_risks.append(
                multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK
            )
        if has_chasm:
            expected_risks.append(
                multifact.ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION
            )
        needs_algebra = (
            self.structural
            is multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
            or bool(expected_risks)
        )
        if (
            self.structural is not expected_structural
            or self.finer is not expected_finer
            or self.chasm_candidates != expected_chasms
            or self.multiplicity_risks != tuple(expected_risks)
            or self.requirements
            != (
                (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
                if needs_algebra
                else ()
            )
        ):
            raise ValueError("Aggregate pair risks must replay exact grain evidence.")


def _build_pair_linkage(
    left: ProjectJoinedAggregateGrainLinkage,
    right: ProjectJoinedAggregateGrainLinkage,
) -> ProjectJoinedAggregatePairLinkage:
    region = left.multifact_region
    if right.multifact_region is not region:
        raise ValueError("Aggregate pair requires one exact multi-fact region.")
    comparison = multifact._compare_grains(
        region.grain_index,
        left.contextual_grain,
        right.contextual_grain,
    )
    common = multifact._common_grain(
        index=region.grain_index,
        left=left.contextual_grain,
        right=right.contextual_grain,
        actual_candidates=region.actual_candidates,
    )
    structural, finer, chasm_candidates = _pair_shape(
        left=left,
        right=right,
        comparison=comparison,
        common=common,
    )
    risks: list[multifact.ProjectMultiFactMultiplicityRisk] = []
    if left.multiplicity_exposures or right.multiplicity_exposures:
        risks.append(multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK)
    if chasm_candidates:
        risks.append(
            multifact.ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION
        )
    requirements = (
        (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
        if structural
        is multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        or risks
        else ()
    )
    return ProjectJoinedAggregatePairLinkage(
        left=left,
        right=right,
        grain_comparison=comparison,
        common_grain=common,
        chasm_candidates=chasm_candidates,
        structural=structural,
        finer=finer,
        multiplicity_risks=tuple(risks),
        requirements=requirements,
    )


def _build_pair_linkages(
    linkages: tuple[ProjectJoinedAggregateGrainLinkage, ...],
) -> tuple[ProjectJoinedAggregatePairLinkage, ...]:
    return tuple(
        _build_pair_linkage(linkages[left], linkages[right])
        for left in range(len(linkages))
        for right in range(left + 1, len(linkages))
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedSatisfyingOutputReference:
    """One exact satisfying name resolved to one stage output occurrence."""

    expression: NameExpr = field(repr=False, compare=False, hash=False)
    output: ProjectJoinedStageOutputOccurrence

    def __post_init__(self) -> None:
        if type(self.expression) is not NameExpr or (
            self.expression.name != self.output.output_name
        ):
            raise ValueError("Satisfying output reference requires exact name lookup.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedSatisfyingAggregateReference:
    """One approved aggregate-LET call resolved to an existing occurrence."""

    expression: CallExpr = field(repr=False, compare=False, hash=False)
    aggregate: ProjectJoinedAggregateOccurrence

    def __post_init__(self) -> None:
        if type(self.expression) is not CallExpr or (
            semantic_aggregates.semantic_aggregate_call_name(self.expression)
            != self.aggregate.function_name
        ):
            raise ValueError("Satisfying aggregate reference requires an exact call.")


type ProjectJoinedSatisfyingReference = (
    ProjectJoinedSatisfyingOutputReference | ProjectJoinedSatisfyingAggregateReference
)


class ProjectJoinedSatisfyingStatus(StrEnum):
    """Closed satisfying analysis outcomes."""

    CONCRETE = "concrete"
    NON_CONCRETE = "non_concrete"


_SATISFYING_RETENTION_EFFECTS = (
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


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedSatisfyingAnalysis:
    """Exact grouped-output predicate evidence without runtime evaluation."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    mode: ProjectJoinedAggregationMode
    stage_outputs: tuple[ProjectJoinedStageOutputOccurrence, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    status: ProjectJoinedSatisfyingStatus
    predicate_value_type: ValueType
    value_types: Mapping[Expression, ValueType] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    references: tuple[ProjectJoinedSatisfyingReference, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    retention_effects: tuple[ProjectJoinedRowRetentionEffect, ...] = ()

    def __post_init__(self) -> None:
        definition = _definition(self.input_filter)
        clause = definition.satisfying_clause
        if (
            clause is None
            or type(self.mode) is not ProjectJoinedAggregationMode
            or type(self.status) is not ProjectJoinedSatisfyingStatus
            or type(self.predicate_value_type) is not ValueType
            or self.value_types.get(clause.expression) is not self.predicate_value_type
            or any(
                type(output) is not ProjectJoinedStageOutputOccurrence
                or output.input_filter is not self.input_filter
                for output in self.stage_outputs
            )
            or any(
                type(aggregate) is not ProjectJoinedAggregateOccurrence
                or aggregate.input_filter is not self.input_filter
                for aggregate in self.aggregates
            )
            or any(
                type(reference)
                not in {
                    ProjectJoinedSatisfyingOutputReference,
                    ProjectJoinedSatisfyingAggregateReference,
                }
                for reference in self.references
            )
            or any(
                type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
            )
        ):
            raise ValueError("Satisfying analysis requires exact grouped-stage roots.")
        if self.status is ProjectJoinedSatisfyingStatus.CONCRETE:
            if (
                self.mode is not ProjectJoinedAggregationMode.GROUPED
                or self.predicate_value_type.kind is not ValueTypeKind.KNOWN
                or self.predicate_value_type.resolved_type.name != "Bool"
                or any(
                    diagnostic.severity is Severity.ERROR
                    for diagnostic in self.diagnostics
                )
                or self.retention_effects != _SATISFYING_RETENTION_EFFECTS
            ):
                raise ValueError("Concrete satisfying requires one known Bool result.")
        elif not self.diagnostics or self.retention_effects:
            raise ValueError("Non-concrete satisfying requires exact blockers only.")
        object.__setattr__(
            self, "value_types", MappingProxyType(dict(self.value_types))
        )


def _authored_unsupported_output_names(
    input_filter: ProjectConcreteJoinedRowFilter,
    outputs: tuple[ProjectJoinedStageOutputOccurrence, ...],
) -> set[str]:
    definition = _definition(input_filter)
    supported = {output.output_name for output in outputs}
    return {
        name
        for item in definition.select_items
        if (name := _projection_output_name(item)) is not None and name not in supported
    }


def _matching_aggregate_reference(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    expression: CallExpr,
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
) -> tuple[ProjectJoinedAggregateOccurrence, ...]:
    function_name = semantic_aggregates.semantic_aggregate_call_name(expression)
    if function_name is None or len(expression.arguments) != 1:
        return ()
    argument = expression.arguments[0]
    let_expansions = _let_expansions(input_filter)
    if not semantic_aggregates.aggregate_argument_can_use_let_scope(
        function_name,
        argument,
        let_expansions,
    ):
        return ()
    if type(argument) is not NameExpr:
        raise AssertionError("approved aggregate LET reference lost its name root")
    resolution = resolve_project_joined_namespace_reference(
        input_filter.namespace,
        ProjectScalarReferenceOccurrence(
            environment=input_filter.namespace.binding_environment.scalar_environment,
            expression=argument,
        ),
    )
    if type(resolution) is not ProjectJoinedLetReferenceResolution:
        return ()
    effective = semantic_aggregates.effective_semantic_aggregate_argument_expression(
        function_name,
        argument,
        let_expansions=let_expansions,
    )
    satisfying_fields = tuple(
        field_semantics
        for _, _, _, field_semantics in _resolved_field_dependencies(
            input_filter=input_filter,
            namespace=input_filter.namespace,
            expression=argument,
        )
    )
    return tuple(
        aggregate
        for aggregate in aggregates
        if aggregate.function_name == function_name
        and len(aggregate.call.arguments) == 1
        and semantic_aggregates.effective_semantic_aggregate_argument_expression(
            function_name,
            aggregate.call.arguments[0],
            let_expansions=let_expansions,
        )
        == effective
        and len(aggregate.field_dependencies) == len(satisfying_fields)
        and all(
            dependency.field_semantics is field_semantics
            for dependency, field_semantics in zip(
                aggregate.field_dependencies,
                satisfying_fields,
                strict=True,
            )
        )
    )


def _infer_satisfying_value(
    expression: Expression,
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    outputs: tuple[ProjectJoinedStageOutputOccurrence, ...],
    unsupported_names: set[str],
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
    diagnostics: list[Diagnostic],
    value_types: dict[Expression, ValueType],
    references: list[ProjectJoinedSatisfyingReference],
) -> ValueType:
    if type(expression) is LiteralExpr:
        value_type = semantic_satisfying._literal_value_type(expression)
    elif type(expression) is NameExpr:
        matches = tuple(
            output for output in outputs if output.output_name == expression.name
        )
        if len(matches) == 1:
            output = matches[0]
            references.append(
                ProjectJoinedSatisfyingOutputReference(
                    expression=expression,
                    output=output,
                )
            )
            value_type = output.value_type
        elif matches:
            raise ValueError("Concrete stage output names must remain unique.")
        else:
            if expression.name in unsupported_names:
                diagnostic = semantic_satisfying._unsupported_output_diagnostic(
                    expression
                )
            elif any(
                field.evidence.name == expression.name
                for field in input_filter.namespace.visible_fields
            ):
                diagnostic = semantic_satisfying._input_field_reference_diagnostic(
                    expression
                )
            else:
                diagnostic = semantic_satisfying._unknown_output_diagnostic(expression)
            diagnostics.append(diagnostic)
            value_type = semantic_satisfying._UNKNOWN_VALUE_TYPE
    elif type(expression) is CallExpr:
        if semantic_aggregates.is_semantic_aggregate_call(expression):
            matches = _matching_aggregate_reference(
                input_filter=input_filter,
                expression=expression,
                aggregates=aggregates,
            )
            if len(matches) == 1:
                aggregate = matches[0]
                references.append(
                    ProjectJoinedSatisfyingAggregateReference(
                        expression=expression,
                        aggregate=aggregate,
                    )
                )
                value_type = aggregate.result_value_type
            else:
                diagnostics.append(
                    semantic_aggregates.invalid_context_diagnostic(
                        expression,
                        context="satisfying clause",
                    )
                )
                value_type = semantic_satisfying._UNKNOWN_VALUE_TYPE
        else:
            diagnostics.append(
                semantic_satisfying._unsupported_expression_diagnostic(expression)
            )
            value_type = semantic_satisfying._UNKNOWN_VALUE_TYPE
    elif semantic_aggregates.contains_semantic_aggregate(expression):
        diagnostics.append(
            semantic_aggregates.invalid_context_diagnostic(
                expression,
                context="satisfying clause",
            )
        )
        value_type = semantic_satisfying._UNKNOWN_VALUE_TYPE
    else:
        diagnostics.append(
            semantic_satisfying._unsupported_expression_diagnostic(expression)
        )
        value_type = semantic_satisfying._UNKNOWN_VALUE_TYPE
    value_types[expression] = value_type
    return value_type


def _infer_satisfying_predicate(
    expression: Expression,
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    outputs: tuple[ProjectJoinedStageOutputOccurrence, ...],
    unsupported_names: set[str],
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
    diagnostics: list[Diagnostic],
    value_types: dict[Expression, ValueType],
    references: list[ProjectJoinedSatisfyingReference],
) -> ValueType:
    if type(expression) in {NameExpr, LiteralExpr, CallExpr}:
        return _infer_satisfying_value(
            expression,
            input_filter=input_filter,
            outputs=outputs,
            unsupported_names=unsupported_names,
            aggregates=aggregates,
            diagnostics=diagnostics,
            value_types=value_types,
            references=references,
        )
    if type(expression) is ComparisonExpr:
        if expression.operator not in semantic_satisfying._ALLOWED_COMPARISON_OPERATORS:
            diagnostics.append(
                semantic_satisfying._unsupported_expression_diagnostic(
                    expression,
                    form=f"comparison operator `{expression.operator}`",
                )
            )
            value_types[expression] = semantic_satisfying._UNKNOWN_VALUE_TYPE
            return semantic_satisfying._UNKNOWN_VALUE_TYPE
        left = _infer_satisfying_value(
            expression.left,
            input_filter=input_filter,
            outputs=outputs,
            unsupported_names=unsupported_names,
            aggregates=aggregates,
            diagnostics=diagnostics,
            value_types=value_types,
            references=references,
        )
        right = _infer_satisfying_value(
            expression.right,
            input_filter=input_filter,
            outputs=outputs,
            unsupported_names=unsupported_names,
            aggregates=aggregates,
            diagnostics=diagnostics,
            value_types=value_types,
            references=references,
        )
        value_type = (
            semantic_satisfying._UNKNOWN_VALUE_TYPE
            if left.kind is ValueTypeKind.UNKNOWN or right.kind is ValueTypeKind.UNKNOWN
            else semantic_satisfying._BOOL_VALUE_TYPE
        )
        value_types[expression] = value_type
        return value_type
    if type(expression) is BinaryExpr and expression.operator in {"and", "or"}:
        left = _infer_satisfying_predicate(
            expression.left,
            input_filter=input_filter,
            outputs=outputs,
            unsupported_names=unsupported_names,
            aggregates=aggregates,
            diagnostics=diagnostics,
            value_types=value_types,
            references=references,
        )
        right = _infer_satisfying_predicate(
            expression.right,
            input_filter=input_filter,
            outputs=outputs,
            unsupported_names=unsupported_names,
            aggregates=aggregates,
            diagnostics=diagnostics,
            value_types=value_types,
            references=references,
        )
        if left.kind is ValueTypeKind.UNKNOWN or right.kind is ValueTypeKind.UNKNOWN:
            value_type = semantic_satisfying._UNKNOWN_VALUE_TYPE
        elif semantic_satisfying._is_bool(left) and semantic_satisfying._is_bool(right):
            value_type = semantic_satisfying._BOOL_VALUE_TYPE
        else:
            diagnostics.append(
                semantic_satisfying._invalid_bool_operands_diagnostic(expression)
            )
            value_type = semantic_satisfying._UNKNOWN_VALUE_TYPE
        value_types[expression] = value_type
        return value_type
    diagnostics.append(
        semantic_satisfying._unsupported_expression_diagnostic(expression)
    )
    value_types[expression] = semantic_satisfying._UNKNOWN_VALUE_TYPE
    return semantic_satisfying._UNKNOWN_VALUE_TYPE


def _build_satisfying_analysis(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    mode: ProjectJoinedAggregationMode,
    outputs: tuple[ProjectJoinedStageOutputOccurrence, ...],
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
) -> ProjectJoinedSatisfyingAnalysis | None:
    definition = _definition(input_filter)
    clause = definition.satisfying_clause
    if clause is None:
        return None
    if mode is not ProjectJoinedAggregationMode.GROUPED:
        diagnostic = (
            semantic_aggregates.invalid_context_diagnostic(
                clause.expression,
                context="satisfying clause",
            )
            if semantic_aggregates.contains_semantic_aggregate(clause.expression)
            else semantic_satisfying._no_group_diagnostic(definition)
        )
        value_types = {clause.expression: semantic_satisfying._UNKNOWN_VALUE_TYPE}
        return ProjectJoinedSatisfyingAnalysis(
            input_filter=input_filter,
            mode=mode,
            stage_outputs=outputs,
            aggregates=aggregates,
            status=ProjectJoinedSatisfyingStatus.NON_CONCRETE,
            predicate_value_type=semantic_satisfying._UNKNOWN_VALUE_TYPE,
            value_types=value_types,
            diagnostics=(diagnostic,),
        )

    diagnostics: list[Diagnostic] = []
    value_types: dict[Expression, ValueType] = {}
    references: list[ProjectJoinedSatisfyingReference] = []
    value_type = _infer_satisfying_predicate(
        clause.expression,
        input_filter=input_filter,
        outputs=outputs,
        unsupported_names=_authored_unsupported_output_names(input_filter, outputs),
        aggregates=aggregates,
        diagnostics=diagnostics,
        value_types=value_types,
        references=references,
    )
    if not diagnostics:
        bool_diagnostic = semantic_satisfying._bool_predicate_diagnostic(
            clause.expression,
            value_type,
        )
        if bool_diagnostic is not None:
            diagnostics.append(bool_diagnostic)
    status = (
        ProjectJoinedSatisfyingStatus.CONCRETE
        if not diagnostics
        and value_type.kind is ValueTypeKind.KNOWN
        and value_type.resolved_type.name == "Bool"
        else ProjectJoinedSatisfyingStatus.NON_CONCRETE
    )
    return ProjectJoinedSatisfyingAnalysis(
        input_filter=input_filter,
        mode=mode,
        stage_outputs=outputs,
        aggregates=aggregates,
        status=status,
        predicate_value_type=value_type,
        value_types=value_types,
        references=tuple(references),
        diagnostics=tuple(diagnostics),
        retention_effects=(
            _SATISFYING_RETENTION_EFFECTS
            if status is ProjectJoinedSatisfyingStatus.CONCRETE
            else ()
        ),
    )


def _require_stage_evidence(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    mode: ProjectJoinedAggregationMode,
    group_keys: tuple[ProjectJoinedGroupKeyOccurrence, ...],
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
    stage_outputs: tuple[ProjectJoinedStageOutputOccurrence, ...],
    group_protections: tuple[ProjectJoinedGroupProtection, ...],
    grain_linkages: tuple[ProjectJoinedAggregateGrainLinkage, ...],
    pair_linkages: tuple[ProjectJoinedAggregatePairLinkage, ...],
) -> None:
    definition = _definition(input_filter)
    expected_aggregate_items = tuple(
        item
        for item in definition.select_items
        if type(item.expression) is not WindowExpr
        and semantic_aggregates.contains_semantic_aggregate(item.expression)
    )
    if (
        any(
            type(key) is not ProjectJoinedGroupKeyOccurrence
            or key.input_filter is not input_filter
            for key in group_keys
        )
        or any(
            type(aggregate) is not ProjectJoinedAggregateOccurrence
            or aggregate.input_filter is not input_filter
            for aggregate in aggregates
        )
        or any(
            type(output) is not ProjectJoinedStageOutputOccurrence
            or output.input_filter is not input_filter
            for output in stage_outputs
        )
        or tuple(output.selected_output_ordinal for output in stage_outputs)
        != tuple(sorted(output.selected_output_ordinal for output in stage_outputs))
        or any(
            type(protection) is not ProjectJoinedGroupProtection
            or protection.input_filter is not input_filter
            for protection in group_protections
        )
        or len(aggregates) != len(expected_aggregate_items)
        or any(
            aggregate.item is not item
            for aggregate, item in zip(
                aggregates,
                expected_aggregate_items,
                strict=True,
            )
        )
        or len(grain_linkages) != len(aggregates)
        or any(
            linkage.aggregate is not aggregate
            for linkage, aggregate in zip(grain_linkages, aggregates, strict=True)
        )
    ):
        raise ValueError("Joined aggregation evidence lost exact source order.")
    expected_pairs = tuple(
        (grain_linkages[left], grain_linkages[right])
        for left in range(len(grain_linkages))
        for right in range(left + 1, len(grain_linkages))
    )
    if len(pair_linkages) != len(expected_pairs) or any(
        pair.left is not left or pair.right is not right
        for pair, (left, right) in zip(pair_linkages, expected_pairs, strict=True)
    ):
        raise ValueError("Aggregate pairs must retain deterministic i < j order.")
    if mode is ProjectJoinedAggregationMode.GROUPED:
        clause = definition.group_by_clause
        if (
            clause is None
            or len(group_keys) != len(clause.items)
            or any(
                key.item is not item
                for key, item in zip(group_keys, clause.items, strict=True)
            )
        ):
            raise ValueError("Concrete grouped evidence must cover every group key.")
    elif group_keys or group_protections:
        raise ValueError("Non-grouped modes cannot retain group authority.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedPostAggregateNamespace:
    """Exact Slice-10 input namespace without final-output identity."""

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    mode: ProjectJoinedAggregationMode
    outputs: tuple[ProjectJoinedStageOutputOccurrence, ...]
    input_namespace: ProjectJoinedScalarNamespace | None = field(init=False)

    def __post_init__(self) -> None:
        if type(self.mode) is not ProjectJoinedAggregationMode or any(
            type(output) is not ProjectJoinedStageOutputOccurrence
            or output.input_filter is not self.input_filter
            for output in self.outputs
        ):
            raise ValueError("Post-aggregate namespace requires exact stage outputs.")
        names = tuple(output.output_name for output in self.outputs)
        if len(set(names)) != len(names):
            raise ValueError("Post-aggregate output names must be unique.")
        if self.mode is ProjectJoinedAggregationMode.ABSENT:
            if self.outputs:
                raise ValueError("Absent aggregation has no stage output occurrence.")
            input_namespace = self.input_filter.namespace
        else:
            if not self.outputs:
                raise ValueError("Aggregate namespace requires selected stage outputs.")
            input_namespace = None
        object.__setattr__(self, "input_namespace", input_namespace)

    def find_output(
        self,
        name: str,
    ) -> tuple[ProjectJoinedStageOutputOccurrence, ...]:
        if type(name) is not str:
            raise TypeError("Post-aggregate lookup requires an exact name.")
        return tuple(output for output in self.outputs if output.output_name == name)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteJoinedAggregation:
    """One closed risk-free joined aggregate stage or exact absent stage."""

    filter_set: ProjectJoinedRowFilterSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    mode: ProjectJoinedAggregationMode
    group_keys: tuple[ProjectJoinedGroupKeyOccurrence, ...]
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...]
    stage_outputs: tuple[ProjectJoinedStageOutputOccurrence, ...]
    group_protections: tuple[ProjectJoinedGroupProtection, ...]
    grain_linkages: tuple[ProjectJoinedAggregateGrainLinkage, ...]
    pair_linkages: tuple[ProjectJoinedAggregatePairLinkage, ...]
    satisfying: ProjectJoinedSatisfyingAnalysis | None
    post_aggregate: ProjectJoinedPostAggregateNamespace
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _require_stage_evidence(
            input_filter=self.input_filter,
            mode=self.mode,
            group_keys=self.group_keys,
            aggregates=self.aggregates,
            stage_outputs=self.stage_outputs,
            group_protections=self.group_protections,
            grain_linkages=self.grain_linkages,
            pair_linkages=self.pair_linkages,
        )
        if (
            type(self.filter_set) is not ProjectJoinedRowFilterSet
            or type(self.input_filter) is not ProjectConcreteJoinedRowFilter
            or not any(
                self.input_filter is retained for retained in self.filter_set.results
            )
            or type(self.mode) is not ProjectJoinedAggregationMode
            or self.post_aggregate.input_filter is not self.input_filter
            or self.post_aggregate.mode is not self.mode
            or self.post_aggregate.outputs != self.stage_outputs
            or any(
                diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
            )
            or any(linkage.requirements for linkage in self.grain_linkages)
            or any(linkage.requirements for linkage in self.pair_linkages)
            or (
                self.satisfying is not None
                and self.satisfying.status is not ProjectJoinedSatisfyingStatus.CONCRETE
            )
        ):
            raise ValueError(
                "Concrete joined aggregation requires closed exact authority."
            )
        if self.mode is ProjectJoinedAggregationMode.ABSENT:
            if any(
                (
                    self.group_keys,
                    self.aggregates,
                    self.stage_outputs,
                    self.group_protections,
                    self.grain_linkages,
                    self.pair_linkages,
                    self.satisfying is not None,
                )
            ):
                raise ValueError("Absent aggregation cannot manufacture a stage.")
        elif self.mode is ProjectJoinedAggregationMode.GROUPED:
            if not self.group_keys or not self.aggregates:
                raise ValueError("Concrete GROUPED mode requires keys and aggregates.")
        elif self.group_keys or not self.aggregates or self.group_protections:
            raise ValueError("Concrete GLOBAL mode requires only aggregate authority.")


class ProjectJoinedAggregationNonConcreteReason(StrEnum):
    """Closed Slice-9 terminal reasons."""

    UPSTREAM_FILTER_NON_CONCRETE = "upstream_filter_non_concrete"
    GROUP_KEY_NON_CONCRETE = "group_key_non_concrete"
    AGGREGATE_NON_CONCRETE = "aggregate_non_concrete"
    SELECTED_OUTPUT_NON_CONCRETE = "selected_output_non_concrete"
    AGGREGATE_ALGEBRA_REQUIRED = "aggregate_algebra_required"
    SATISFYING_NON_CONCRETE = "satisfying_non_concrete"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteJoinedAggregation:
    """One complete Slice-9 blocker with no post-aggregate namespace."""

    filter_set: ProjectJoinedRowFilterSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    input_filter: ProjectJoinedRowFilterResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectJoinedAggregationNonConcreteReason
    mode: ProjectJoinedAggregationMode | None = None
    group_key_results: tuple[ProjectJoinedGroupKeyResult, ...] = ()
    aggregate_results: tuple[ProjectJoinedAggregateResult, ...] = ()
    stage_outputs: tuple[ProjectJoinedStageOutputOccurrence, ...] = ()
    selected_output_issues: tuple[ProjectJoinedSelectedOutputIssue, ...] = ()
    group_protections: tuple[ProjectJoinedGroupProtection, ...] = ()
    grain_linkages: tuple[ProjectJoinedAggregateGrainLinkage, ...] = ()
    pair_linkages: tuple[ProjectJoinedAggregatePairLinkage, ...] = ()
    satisfying: ProjectJoinedSatisfyingAnalysis | None = None
    diagnostics: tuple[Diagnostic, ...] = ()
    post_aggregate: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if (
            type(self.filter_set) is not ProjectJoinedRowFilterSet
            or type(self.input_filter)
            not in {
                ProjectConcreteJoinedRowFilter,
                ProjectNonConcreteJoinedRowFilter,
            }
            or not any(
                self.input_filter is retained for retained in self.filter_set.results
            )
            or type(self.reason) is not ProjectJoinedAggregationNonConcreteReason
        ):
            raise ValueError("Joined aggregation terminal requires exact filter roots.")
        if self.reason is (
            ProjectJoinedAggregationNonConcreteReason.UPSTREAM_FILTER_NON_CONCRETE
        ):
            if type(self.input_filter) is not ProjectNonConcreteJoinedRowFilter or any(
                (
                    self.mode is not None,
                    self.group_key_results,
                    self.aggregate_results,
                    self.stage_outputs,
                    self.selected_output_issues,
                    self.group_protections,
                    self.grain_linkages,
                    self.pair_linkages,
                    self.satisfying is not None,
                    self.diagnostics,
                )
            ):
                raise ValueError(
                    "Upstream filter terminal cannot publish partial stage."
                )
            return
        if type(self.input_filter) is not ProjectConcreteJoinedRowFilter or (
            type(self.mode) is not ProjectJoinedAggregationMode
        ):
            raise ValueError(
                "Local aggregation blocker requires concrete filtered rows."
            )
        has_group_issue = any(
            type(item) is ProjectJoinedGroupKeyIssue for item in self.group_key_results
        )
        has_aggregate_issue = any(
            type(item) is ProjectJoinedAggregateIssue for item in self.aggregate_results
        )
        has_output_issue = bool(self.selected_output_issues)
        has_risk = any(item.requirements for item in self.grain_linkages) or any(
            item.requirements for item in self.pair_linkages
        )
        has_satisfying_issue = self.satisfying is not None and (
            self.satisfying.status is ProjectJoinedSatisfyingStatus.NON_CONCRETE
        )
        expected = (
            ProjectJoinedAggregationNonConcreteReason.GROUP_KEY_NON_CONCRETE
            if has_group_issue
            else (
                ProjectJoinedAggregationNonConcreteReason.AGGREGATE_NON_CONCRETE
                if has_aggregate_issue
                else (
                    ProjectJoinedAggregationNonConcreteReason.SELECTED_OUTPUT_NON_CONCRETE
                    if has_output_issue
                    else (
                        ProjectJoinedAggregationNonConcreteReason.AGGREGATE_ALGEBRA_REQUIRED
                        if has_risk
                        else ProjectJoinedAggregationNonConcreteReason.SATISFYING_NON_CONCRETE
                    )
                )
            )
        )
        if self.reason is not expected or not any(
            (
                has_group_issue,
                has_aggregate_issue,
                has_output_issue,
                has_risk,
                has_satisfying_issue,
            )
        ):
            raise ValueError("Joined aggregation terminal reason lost its root cause.")


type ProjectJoinedAggregationResult = (
    ProjectConcreteJoinedAggregation | ProjectNonConcreteJoinedAggregation
)


def _mode(definition: TableDef | QueryDef) -> ProjectJoinedAggregationMode:
    if definition.group_by_clause is not None:
        return ProjectJoinedAggregationMode.GROUPED
    if any(
        type(item.expression) is not WindowExpr
        and semantic_aggregates.contains_semantic_aggregate(item.expression)
        for item in definition.select_items
    ):
        return ProjectJoinedAggregationMode.GLOBAL
    return ProjectJoinedAggregationMode.ABSENT


def _ordered_diagnostics(
    *,
    group_key_results: tuple[ProjectJoinedGroupKeyResult, ...],
    aggregate_results: tuple[ProjectJoinedAggregateResult, ...],
    selected_output_issues: tuple[ProjectJoinedSelectedOutputIssue, ...],
    satisfying: ProjectJoinedSatisfyingAnalysis | None,
) -> tuple[Diagnostic, ...]:
    group_diagnostics = tuple(
        diagnostic
        for item in group_key_results
        if type(item) is ProjectJoinedGroupKeyIssue
        for diagnostic in item.diagnostics
    )
    selected = sorted(
        (
            *(
                (item.selected_output_ordinal, item.diagnostics)
                for item in aggregate_results
                if type(item) is ProjectJoinedAggregateIssue
            ),
            *(
                (
                    -1
                    if item.selected_output_ordinal is None
                    else item.selected_output_ordinal,
                    item.diagnostics,
                )
                for item in selected_output_issues
            ),
        ),
        key=lambda item: item[0],
    )
    return (
        *group_diagnostics,
        *(diagnostic for _, values in selected for diagnostic in values),
        *(() if satisfying is None else satisfying.diagnostics),
    )


def build_project_joined_aggregation(
    filter_set: ProjectJoinedRowFilterSet,
    input_filter: ProjectJoinedRowFilterResult,
) -> ProjectJoinedAggregationResult:
    """Build one exact Slice-9 result without Project IR allocation or repair."""

    if type(filter_set) is not ProjectJoinedRowFilterSet or not any(
        input_filter is retained for retained in filter_set.results
    ):
        raise ValueError("Joined aggregation requires exact Slice-8 membership.")
    if type(input_filter) is ProjectNonConcreteJoinedRowFilter:
        return ProjectNonConcreteJoinedAggregation(
            filter_set=filter_set,
            input_filter=input_filter,
            reason=(
                ProjectJoinedAggregationNonConcreteReason.UPSTREAM_FILTER_NON_CONCRETE
            ),
        )
    if type(input_filter) is not ProjectConcreteJoinedRowFilter:
        raise TypeError("Joined aggregation requires a closed Slice-8 result.")
    definition = _definition(input_filter)
    mode = _mode(definition)
    group_key_results = _build_group_keys(input_filter)
    group_keys = tuple(
        item
        for item in group_key_results
        if type(item) is ProjectJoinedGroupKeyOccurrence
    )
    aggregate_results = _build_aggregate_results(input_filter)
    aggregates = tuple(
        item
        for item in aggregate_results
        if type(item) is ProjectJoinedAggregateOccurrence
    )
    stage_outputs, selected_output_issues = _build_stage_outputs(
        input_filter=input_filter,
        mode=mode,
        group_keys=group_keys,
        aggregate_results=aggregate_results,
        aggregates=aggregates,
    )
    group_protections = (
        _build_group_protections(input_filter, group_keys)
        if mode is ProjectJoinedAggregationMode.GROUPED
        and not any(
            type(item) is ProjectJoinedGroupKeyIssue for item in group_key_results
        )
        else ()
    )
    grain_linkages = _build_grain_linkages(
        input_filter=input_filter,
        aggregates=aggregates,
        protections=group_protections,
    )
    pair_linkages = _build_pair_linkages(grain_linkages)
    satisfying = _build_satisfying_analysis(
        input_filter=input_filter,
        mode=mode,
        outputs=stage_outputs,
        aggregates=aggregates,
    )
    diagnostics = _ordered_diagnostics(
        group_key_results=group_key_results,
        aggregate_results=aggregate_results,
        selected_output_issues=selected_output_issues,
        satisfying=satisfying,
    )
    has_group_issue = any(
        type(item) is ProjectJoinedGroupKeyIssue for item in group_key_results
    )
    has_aggregate_issue = any(
        type(item) is ProjectJoinedAggregateIssue for item in aggregate_results
    )
    has_risk = any(item.requirements for item in grain_linkages) or any(
        item.requirements for item in pair_linkages
    )
    has_satisfying_issue = satisfying is not None and (
        satisfying.status is ProjectJoinedSatisfyingStatus.NON_CONCRETE
    )
    if any(
        (
            has_group_issue,
            has_aggregate_issue,
            bool(selected_output_issues),
            has_risk,
            has_satisfying_issue,
        )
    ):
        reason = (
            ProjectJoinedAggregationNonConcreteReason.GROUP_KEY_NON_CONCRETE
            if has_group_issue
            else (
                ProjectJoinedAggregationNonConcreteReason.AGGREGATE_NON_CONCRETE
                if has_aggregate_issue
                else (
                    ProjectJoinedAggregationNonConcreteReason.SELECTED_OUTPUT_NON_CONCRETE
                    if selected_output_issues
                    else (
                        ProjectJoinedAggregationNonConcreteReason.AGGREGATE_ALGEBRA_REQUIRED
                        if has_risk
                        else ProjectJoinedAggregationNonConcreteReason.SATISFYING_NON_CONCRETE
                    )
                )
            )
        )
        return ProjectNonConcreteJoinedAggregation(
            filter_set=filter_set,
            input_filter=input_filter,
            reason=reason,
            mode=mode,
            group_key_results=group_key_results,
            aggregate_results=aggregate_results,
            stage_outputs=stage_outputs,
            selected_output_issues=selected_output_issues,
            group_protections=group_protections,
            grain_linkages=grain_linkages,
            pair_linkages=pair_linkages,
            satisfying=satisfying,
            diagnostics=diagnostics,
        )
    post_aggregate = ProjectJoinedPostAggregateNamespace(
        input_filter=input_filter,
        mode=mode,
        outputs=stage_outputs,
    )
    return ProjectConcreteJoinedAggregation(
        filter_set=filter_set,
        input_filter=input_filter,
        mode=mode,
        group_keys=group_keys,
        aggregates=aggregates,
        stage_outputs=stage_outputs,
        group_protections=group_protections,
        grain_linkages=grain_linkages,
        pair_linkages=pair_linkages,
        satisfying=satisfying,
        post_aggregate=post_aggregate,
        diagnostics=diagnostics,
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedAggregationSet:
    """Canonical Slice-8-order joined aggregation results."""

    filter_set: ProjectJoinedRowFilterSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    results: tuple[ProjectJoinedAggregationResult, ...]

    def __post_init__(self) -> None:
        if type(self.filter_set) is not ProjectJoinedRowFilterSet or (
            type(self.results) is not tuple
            or len(self.results) != len(self.filter_set.results)
            or any(
                type(result)
                not in {
                    ProjectConcreteJoinedAggregation,
                    ProjectNonConcreteJoinedAggregation,
                }
                or result.filter_set is not self.filter_set
                or result.input_filter is not input_filter
                for result, input_filter in zip(
                    self.results,
                    self.filter_set.results,
                    strict=True,
                )
            )
        ):
            raise ValueError(
                "Joined aggregation set must retain canonical Slice-8 order."
            )


def build_project_joined_aggregations(
    filter_set: ProjectJoinedRowFilterSet,
) -> ProjectJoinedAggregationSet:
    """Build one closed Slice-9 result per exact Slice-8 result."""

    if type(filter_set) is not ProjectJoinedRowFilterSet:
        raise TypeError("Joined aggregation set requires exact Slice-8 authority.")
    return ProjectJoinedAggregationSet(
        filter_set=filter_set,
        results=tuple(
            build_project_joined_aggregation(filter_set, input_filter)
            for input_filter in filter_set.results
        ),
    )
