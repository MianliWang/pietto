"""Private Phase-63 joined grouping, aggregate, satisfying, and risk authority."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, NamedTuple, cast

from pietto._project import project_multifact as multifact
from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_current_joins import (
    ProjectCurrentJoinRegion,
    compiled_forward_at_most_one,
    current_forward_at_most_one,
)
from pietto._project.project_grain import (
    ProjectGrainBasisState,
    ProjectGrainDependencyFact,
    ProjectGrainDependencyIndex,
    ProjectGrainFactorIdentity,
    ProjectGrainFactorSet,
    _compile_grain_dependency_index,
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
from pietto._project.project_relationship_match_guarantees import (
    resolved_matching_keys,
)
from pietto._project.project_row_keys import ProjectRowUniquenessStrength
from pietto.ast_nodes import (
    AuthoredJoinKind,
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    CastExpr,
    ComparisonExpr,
    ConditionalExpr,
    DottedNameExpr,
    Expression,
    GroupByItem,
    IsNullExpr,
    LiteralExpr,
    MembershipExpr,
    ParameterRefExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    SourceDef,
    TableDef,
    UnaryExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity
from pietto.semantic import catalog as semantic_catalog
from pietto.semantic import group_by as semantic_group_by
from pietto.semantic import satisfying as semantic_satisfying
from pietto.semantic import aggregates as semantic_aggregates
from pietto.semantic.expressions import (
    _check_inlined_argument,
    checks_inlined_arguments,
    comparison_literals,
    query_parameter_value_type,
    resolved_comparison_value_type,
)
from pietto.semantic.model import RowSchema, TypeKind, ValueType, ValueTypeKind

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
class ProjectJoinedComputedGroupKeyOccurrence:
    """One authored group key naming one computed row LET value over JOIN inputs.

    The determinant compares that established LET value, never an input field,
    so it is not assumed injective: it seeds no protection class and supplies no
    grain. ``field_dependencies`` records every JOIN-side field occurrence the
    value reads, in the existing occurrence-safe dependency order.
    """

    input_filter: ProjectConcreteJoinedRowFilter = field(
        repr=False,
        compare=False,
        hash=False,
    )
    source_ordinal: int
    item: GroupByItem = field(repr=False, compare=False, hash=False)
    resolutions: tuple[ProjectJoinedLetReferenceResolution] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    field_dependencies: tuple[ProjectJoinedRowFieldSemantics, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
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
            or type(self.resolutions) is not tuple
            or len(self.resolutions) != 1
            or type(self.resolutions[0]) is not ProjectJoinedLetReferenceResolution
            or self.item.key is not self.resolutions[0].reference.expression
            or type(self.let_value.occurrence.expression) in {NameExpr, DottedNameExpr}
            or self.value_type is not self.let_value.value_type
            or self.value_type.resolved_type.kind is not TypeKind.BUILTIN
            or not _same_objects(
                self.field_dependencies,
                _let_field_dependencies(self.input_filter, self.let_value),
            )
        ):
            raise ValueError("Computed group key must retain its exact LET authority.")

    @property
    def let_value(self) -> ProjectJoinedLetValue:
        """The one admitted LET value this determinant compares."""

        return self.resolutions[0].target


ProjectJoinedAnyGroupKey = (
    ProjectJoinedGroupKeyOccurrence | ProjectJoinedComputedGroupKeyOccurrence
)


def _same_objects(left: tuple[object, ...], right: tuple[object, ...]) -> bool:
    return (
        type(left) is tuple
        and len(left) == len(right)
        and all(a is b for a, b in zip(left, right, strict=True))
    )


def _let_field_dependencies(
    input_filter: ProjectConcreteJoinedRowFilter,
    value: ProjectJoinedLetValue,
) -> tuple[ProjectJoinedRowFieldSemantics, ...]:
    return tuple(
        field_semantics
        for _, _, _, field_semantics in _resolved_field_dependencies(
            input_filter=input_filter,
            namespace=value.namespace,
            expression=value.occurrence.expression,
        )
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
    duplicate_of: ProjectJoinedAnyGroupKey | None = field(
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
            if type(self.duplicate_of) not in {
                ProjectJoinedGroupKeyOccurrence,
                ProjectJoinedComputedGroupKeyOccurrence,
            }:
                raise ValueError("Duplicate group key requires its earlier occurrence.")
        elif self.duplicate_of is not None:
            raise ValueError("Non-duplicate group-key issue cannot retain a winner.")


type ProjectJoinedGroupKeyResult = (
    ProjectJoinedGroupKeyOccurrence
    | ProjectJoinedComputedGroupKeyOccurrence
    | ProjectJoinedGroupKeyIssue
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
    DEF_ARGUMENT_MISMATCH = "def_argument_mismatch"


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
                or not (
                    self.field_dependencies
                    or _is_let_extremum(
                        self.function_name,
                        self.call.arguments[0],
                        _let_expansions(self.input_filter),
                    )
                )
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
    retained_by_field: dict[int, ProjectJoinedAnyGroupKey] = {}
    for source_ordinal, item in enumerate(clause.items):
        resolutions, field_semantics, computed = _direct_field_resolution(
            input_filter,
            item.key,
            expand_let=True,
        )
        computed_key = (
            _computed_group_key(input_filter, source_ordinal, item, resolutions)
            if computed
            else None
        )
        if computed_key is not None:
            # One LET value is one determinant identity, like one field occurrence.
            duplicate = retained_by_field.get(id(computed_key.let_value))
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
            retained_by_field[id(computed_key.let_value)] = computed_key
            built.append(computed_key)
            continue
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


def _computed_group_key(
    input_filter: ProjectConcreteJoinedRowFilter,
    source_ordinal: int,
    item: GroupByItem,
    resolutions: tuple[ProjectJoinedNamespaceReferenceResolution, ...],
) -> ProjectJoinedComputedGroupKeyOccurrence | None:
    """Admit a key naming one computed LET value directly; an alias stays refused."""

    if len(resolutions) != 1:
        return None
    resolution = resolutions[0]
    if type(resolution) is not ProjectJoinedLetReferenceResolution:
        return None
    value = resolution.target
    if value.value_type.resolved_type.kind is not TypeKind.BUILTIN:
        return None
    return ProjectJoinedComputedGroupKeyOccurrence(
        input_filter=input_filter,
        source_ordinal=source_ordinal,
        item=item,
        resolutions=(resolution,),
        field_dependencies=_let_field_dependencies(input_filter, value),
        value_type=value.value_type,
    )


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
            if not analysis.blocking_resolutions and not _unfit_argument_alone(
                function_name,
                argument,
                analysis,
                _let_expansions(input_filter),
            ):
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
            and not _is_let_extremum(function_name, argument, let_expansions)
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
    # An aggregate passed to a def is its result, which must fit the parameter
    # (PIE-S2395) as in a single file.
    unfit: list[Diagnostic] = []
    _check_inlined_argument(expression, result_type, unfit, None)
    if unfit:
        return ProjectJoinedAggregateIssue(
            input_filter=input_filter,
            selected_output_ordinal=selected_output_ordinal,
            item=item,
            kind=ProjectJoinedAggregateIssueKind.DEF_ARGUMENT_MISMATCH,
            argument_analysis=argument_analysis,
            diagnostics=tuple(unfit),
        )
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


def _unfit_argument_alone(
    function_name: str,
    argument: Expression,
    analysis: ProjectNonConcreteJoinedNamespaceExpression,
    let_expansions: Mapping[str, Expression],
) -> bool:
    """Whether ``argument`` is unknown here only because a ``def`` argument in
    it, at any depth, does not fit its parameter (PIE-S2395), as in a single
    file, in a form the aggregate accepts for some argument type: its
    PIE-S2395 is then its one error. A form it accepts for no type, or one
    that reads a `let:` name other than as the whole argument, is also
    PIE-S2315, which no argument type would avoid."""

    return (
        {
            diagnostic.code
            for diagnostic in analysis.diagnostics
            if diagnostic.severity is Severity.ERROR
        }
        == {"PIE-S2395"}
        and (
            all(
                type(resolution) is not ProjectJoinedLetReferenceResolution
                for resolution in analysis.resolutions
            )
            or semantic_aggregates.aggregate_argument_can_use_let_scope(
                function_name, argument, let_expansions
            )
            or _is_let_extremum(function_name, argument, let_expansions)
        )
        and semantic_aggregates.accepts_argument_form(
            function_name, argument, let_expansions=let_expansions
        )
    )


def _is_let_extremum(
    function_name: str,
    argument: Expression,
    let_expansions: Mapping[str, Expression],
) -> bool:
    """MIN/MAX over one row LET name, as in explicit modules without JOIN."""

    return (
        function_name
        in {
            semantic_aggregates.MIN_AGGREGATE_NAME,
            semantic_aggregates.MAX_AGGREGATE_NAME,
        }
        and type(argument) is NameExpr
        and argument.name in let_expansions
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
    group_key: ProjectJoinedAnyGroupKey | None = field(
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
                not isinstance(self.group_key, ProjectJoinedAnyGroupKey)
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
    DEF_ARGUMENT_MISMATCH = "def_argument_mismatch"
    # A `let:` name selecting no group key: no unknown field (PIE-S2102), so
    # the relation fails closed with PIE-S2333.
    LET_READ_PROJECTION = "let_read_projection"


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
            # Only a `let:` read leaves its PIE-S2333 to the relation.
            (not self.diagnostics)
            != (self.kind is ProjectJoinedSelectedOutputIssueKind.LET_READ_PROJECTION)
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
    group_keys: tuple[ProjectJoinedAnyGroupKey, ...],
) -> ProjectJoinedAnyGroupKey | None:
    if type(item.expression) not in {NameExpr, DottedNameExpr}:
        return None
    resolutions, field_semantics, _ = _direct_field_resolution(
        input_filter,
        cast(NameExpr | DottedNameExpr, item.expression),
        expand_let=False,
    )
    if field_semantics is None:
        # Only the exact LET value of a computed determinant selects that key.
        target = resolutions[0].target
        computed = tuple(
            key
            for key in group_keys
            if type(key) is ProjectJoinedComputedGroupKeyOccurrence
            and key.let_value is target
        )
        if computed:
            return computed[0] if len(computed) == 1 else None
        # A `let:` name that only renames a field selects that field's key, as
        # the field does.
        _, field_semantics, _ = _direct_field_resolution(
            input_filter,
            cast(NameExpr | DottedNameExpr, item.expression),
            expand_let=True,
        )
        if field_semantics is None:
            return None
    matches = tuple(
        key
        for key in group_keys
        if type(key) is ProjectJoinedGroupKeyOccurrence
        and key.field_semantics is field_semantics
    )
    if len(matches) > 1:
        raise ValueError("Concrete group keys cannot repeat one field occurrence.")
    return None if not matches else matches[0]


def _build_stage_outputs(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    mode: ProjectJoinedAggregationMode,
    group_keys: tuple[ProjectJoinedAnyGroupKey, ...],
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
            # A key passed to a def must fit the parameter (PIE-S2395).
            unfit: list[Diagnostic] = []
            _check_inlined_argument(item.expression, key.value_type, unfit, None)
            if unfit:
                issues.append(
                    ProjectJoinedSelectedOutputIssue(
                        input_filter=input_filter,
                        selected_output_ordinal=ordinal,
                        item=item,
                        kind=ProjectJoinedSelectedOutputIssueKind.DEF_ARGUMENT_MISMATCH,
                        diagnostics=tuple(unfit),
                    )
                )
                continue
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
        diagnostic: Diagnostic | None
        if type(item.expression) in {NameExpr, DottedNameExpr}:
            _, field_semantics, reads_let = _direct_field_resolution(
                input_filter,
                cast(NameExpr | DottedNameExpr, item.expression),
                expand_let=False,
            )
            if reads_let:
                issue_kind = ProjectJoinedSelectedOutputIssueKind.LET_READ_PROJECTION
                diagnostic = None
            elif field_semantics is None:
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
                diagnostics=() if diagnostic is None else (diagnostic,),
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
    computed_keys: tuple[ProjectJoinedComputedGroupKeyOccurrence, ...]
    seed: ProjectIROutputValueClassSet
    strict_keys: tuple[ProjectIROutputCandidateKey, ...]
    determinations: tuple[ProjectIROutputDeterminationResult, ...]
    protected_factors: tuple[ProjectGrainFactorIdentity, ...]

    def __post_init__(self) -> None:
        if (
            type(self.input_properties) is not ProjectIROutputRelationalProperties
            or type(self.introduction_use) is not ProjectIRJoinInputUseOccurrence
            or not (self.group_keys or self.computed_keys)
            or any(
                type(key) is not ProjectJoinedGroupKeyOccurrence
                or key.input_filter is not self.input_filter
                or key.field_semantics.input_properties is not self.input_properties
                or key.field_semantics.introduction_use is not self.introduction_use
                for key in self.group_keys
            )
            # A computed key is recorded on every JOIN side it reads; it never
            # contributes a seed class, so it can never prove a STRICT key.
            or any(
                type(key) is not ProjectJoinedComputedGroupKeyOccurrence
                or key.input_filter is not self.input_filter
                or not any(
                    dependency.input_properties is self.input_properties
                    and dependency.introduction_use is self.introduction_use
                    for dependency in key.field_dependencies
                )
                for key in self.computed_keys
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


def _protection_members(
    group_keys: tuple[ProjectJoinedAnyGroupKey, ...],
) -> tuple[
    tuple[
        ProjectIROutputRelationalProperties,
        ProjectIRJoinInputUseOccurrence,
        tuple[ProjectJoinedGroupKeyOccurrence, ...],
        tuple[ProjectJoinedComputedGroupKeyOccurrence, ...],
    ],
    ...,
]:
    """Every JOIN-side root the keys read, in key/dependency order, with the
    direct keys of that root and the computed keys reading it."""

    roots: list[
        tuple[ProjectIROutputRelationalProperties, ProjectIRJoinInputUseOccurrence]
    ] = []
    for key in group_keys:
        for read in (
            (key.field_semantics,)
            if type(key) is ProjectJoinedGroupKeyOccurrence
            else cast(ProjectJoinedComputedGroupKeyOccurrence, key).field_dependencies
        ):
            root = (read.input_properties, read.introduction_use)
            if not any(
                retained[0] is root[0] and retained[1] is root[1] for retained in roots
            ):
                roots.append(root)
    return tuple(
        (
            properties,
            introduction_use,
            tuple(
                key
                for key in group_keys
                if type(key) is ProjectJoinedGroupKeyOccurrence
                and key.field_semantics.input_properties is properties
                and key.field_semantics.introduction_use is introduction_use
            ),
            tuple(
                key
                for key in group_keys
                if type(key) is ProjectJoinedComputedGroupKeyOccurrence
                and any(
                    read.input_properties is properties
                    and read.introduction_use is introduction_use
                    for read in key.field_dependencies
                )
            ),
        )
        for properties, introduction_use in roots
    )


def _build_group_protections(
    input_filter: ProjectConcreteJoinedRowFilter,
    group_keys: tuple[ProjectJoinedAnyGroupKey, ...],
) -> tuple[ProjectJoinedGroupProtection, ...]:
    region = input_filter.joined_semantics.multifact_region
    final_grain = region.final_properties.relational.grain
    protections: list[ProjectJoinedGroupProtection] = []
    members = _protection_members(group_keys)
    for properties, introduction_use, local_keys, computed_keys in members:
        classes = tuple(
            _value_class_for_input_field(properties, key.field_semantics)
            for key in local_keys
        )
        seed, strict_keys, determinations, protected = resolved_group_protection(
            properties, introduction_use, final_grain, classes
        )
        protections.append(
            ProjectJoinedGroupProtection(
                input_filter=input_filter,
                input_properties=properties,
                introduction_use=introduction_use,
                group_keys=local_keys,
                computed_keys=computed_keys,
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
    return resolved_argument_factors(
        final_grain,
        bool(aggregate.call.arguments),
        tuple(
            (
                dependency.field_semantics.input_properties.grain,
                dependency.field_semantics.introduction_use,
            )
            for dependency in aggregate.field_dependencies
        ),
    )


_NULL_PROPAGATING_CALLS = frozenset(
    {*semantic_catalog.BUILTIN_FUNCTIONS, "sign", "year", "month", "day"}
)


def operation_null_when(role: str, token: object, operands: tuple[bool, ...]) -> bool:
    """Whether an operation (compiled operator names) is NULL in every row in
    which some inputs are all NULL-extended, from whether each operand is:
    ``and``, ``or`` and ``coalesce`` when every operand is, a conditional when
    its else branch is and its other branch is or its condition is never TRUE
    (the condition's operand says whether it never is), ``between`` when its
    value or both bounds are, ``in`` and ``not in`` when their value is and
    their list is not empty (``in ()`` is FALSE, ``not in ()`` TRUE),
    ``nullif`` when its first operand is, another operator or builtin that
    passes NULL on when one operand is, and nothing else (``is null``, a
    literal)."""

    call = role == "scalar_call"
    if (role == "binary" and token in {"and", "or"}) or (call and token == "coalesce"):
        return bool(operands) and all(operands)
    if role == "conditional":  # when_true, condition, when_false
        return operands[2] and (operands[0] or operands[1])
    if role == "between":  # value, lower, upper
        return operands[0] or (operands[1] and operands[2])
    if role == "membership":  # value, options
        return len(operands) > 1 and operands[0]
    if call and token == "nullif":
        return bool(operands) and operands[0]
    return (
        role in {"unary", "not", "binary", "comparison", "cast"}
        or (call and token in _NULL_PROPAGATING_CALLS)
    ) and any(operands)


def _expression_answer(expression: Expression, truth: bool | None, nulls, leaf) -> bool:
    """Evaluate the existing NULL/truth laws without nesting WHERE and LET stacks."""
    pending: list[tuple[Any, ...]] = [(expression, truth, None, None, 0)]
    answers: list[bool] = []
    while pending:
        node, question, role, token, count = pending.pop()
        if role is not None:
            operands = tuple(answers[-count:]) if count else ()
            if count:
                del answers[-count:]
            if role == "truth":
                conjunction = (token == "and") == question
                answers.append(any(operands) if conjunction else all(operands))
            else:
                answers.append(operation_null_when(role, token, operands))
            continue
        if isinstance(node, (NameExpr, DottedNameExpr)):
            answers.append(leaf(node, nulls, question))
            continue
        if question is not None:
            if isinstance(node, BinaryExpr) and node.operator in {"and", "or"}:
                role, token = "truth", node.operator
                children = ((node.left, question), (node.right, question))
            elif isinstance(node, UnaryExpr) and node.operator == "not":
                pending.append((node.operand, not question, None, None, 0))
                continue
            elif isinstance(node, IsNullExpr):
                if node.negated == question:
                    pending.append((node.value, None, None, None, 0))
                else:
                    answers.append(False)
                continue
            elif isinstance(node, MembershipExpr) and not node.options:
                answers.append(node.negated != question)
                continue
            else:
                pending.append((node, None, None, None, 0))
                continue
        else:
            if isinstance(node, UnaryExpr):
                role, operands = "unary", (node.operand,)
            elif isinstance(node, BinaryExpr):
                role, token = "binary", node.operator
                operands = (node.left, node.right)
            elif isinstance(node, ComparisonExpr):
                role, operands = "comparison", (node.left, node.right)
            elif isinstance(node, CastExpr):
                role, operands = "cast", (node.value,)
            elif isinstance(node, ConditionalExpr):
                role = "conditional"
                operands = (node.when_true, node.condition, node.when_false)
            elif isinstance(node, BetweenExpr):
                role, operands = "between", (node.value, node.lower, node.upper)
            elif isinstance(node, MembershipExpr):
                role, operands = "membership", (node.value, *node.options)
            elif isinstance(node, CallExpr) and type(node.callee) is NameExpr:
                role, token, operands = "scalar_call", node.callee.name, node.arguments
            else:
                answers.append(False)
                continue
            children = tuple(
                (operand, True if role == "conditional" and i == 1 else None)
                for i, operand in enumerate(operands)
            )
        pending.append((None, question, role, token, len(children)))
        pending.extend((child, q, None, None, 0) for child, q in reversed(children))
    return answers[0]


def _null_when(expression: Expression, nulls: frozenset, leaf) -> bool:
    """Whether the expression is NULL whenever these inputs are NULL-extended."""
    return _expression_answer(expression, None, nulls, leaf)


def _never(expression: Expression, truth: bool, nulls: frozenset, leaf) -> bool:
    """Whether the condition is never this truth under these NULL extensions."""
    return _expression_answer(expression, truth, nulls, leaf)


def _namespace_leaf(
    input_filter: ProjectConcreteJoinedRowFilter,
    namespace: ProjectJoinedScalarNamespace,
    answers: dict[tuple[int, frozenset, bool | None], bool] | None = None,
):
    """Names of one joined namespace: a field is NULL with its JOIN input, a
    LET value as its expression. A LET value and the values it reads, directly
    or through others, are answered in declaration order for the input set and
    every question, so each reads only answers already known and a LET chain
    needs no recursion."""

    known = {} if answers is None else answers

    def leaf(
        expression: NameExpr | DottedNameExpr, nulls: frozenset, truth: bool | None
    ) -> bool:
        resolution = resolve_project_joined_namespace_reference(
            namespace,
            ProjectScalarReferenceOccurrence(
                environment=namespace.binding_environment.scalar_environment,
                expression=expression,
            ),
        )
        if type(resolution) is ProjectJoinedLetReferenceResolution:
            target = resolution.target
            if (id(target), nulls, truth) not in known:
                read, pending = {id(target)}, [target]
                while pending:
                    for item in pending.pop().resolutions:
                        if type(item) is ProjectJoinedLetReferenceResolution and (
                            id(item.target) not in read
                        ):
                            read.add(id(item.target))
                            pending.append(item.target)
                for value in (*target.namespace.let_values, target):
                    if id(value) not in read or (id(value), nulls, None) in known:
                        continue
                    inner = _namespace_leaf(input_filter, value.namespace, known)
                    written = value.occurrence.expression
                    known[id(value), nulls, None] = _null_when(written, nulls, inner)
                    for question in (True, False):
                        known[id(value), nulls, question] = _never(
                            written, question, nulls, inner
                        )
            return known[id(target), nulls, truth]
        if (
            type(resolution) is ProjectScalarReferenceResolution
            and resolution.target is not None
        ):
            field_semantics = _field_semantics(input_filter, resolution.target)
            return field_semantics.introduction_use in nulls
        return False

    return leaf


class _RegionJoin(NamedTuple):
    """One JOIN of an aggregate's region: its kind, whether each left row
    matches at most one right row, its left and right inputs (grain,
    introduction), the inputs of its left side, its right input, whether its
    condition is never TRUE where some inputs are all NULL-extended, and the
    earlier inputs it pins: its relationship or its `on` equalities match a
    key of each one, so a right row matches at most one row of it."""

    kind: str
    forward_one: bool
    left: tuple[Any, Any]
    right: tuple[Any, Any]
    left_inputs: frozenset
    target: object
    rejects: Callable[[frozenset], bool]
    pins: frozenset
    # Introducing use, exact source domains, complete field pairs, and no extra ON.
    source_match: tuple | None = None


def resolved_orphan_free_dependencies(final_grain, joins, unread, grouped_holder):
    """The left-to-right dependency of each RIGHT or FULL JOIN that holds on
    the rows one aggregate reads; ``project_ir_joins._grain`` leaves it out.

    Such a JOIN with an at-most-one match keeps each right row that matches no
    left row (an orphan) beside a left side NULL-extended in every input, so
    its left side determines its right input everywhere but on orphans.
    ``unread(nulls)`` is whether the aggregate reads no row in which every
    input of ``nulls`` is NULL-extended (its argument is NULL there, or WHERE
    is not TRUE). A later JOIN whose condition is never TRUE on an orphan
    drops it (INNER, SEMI, RIGHT) or NULL-extends its right input there (LEFT,
    FULL). An aggregate that reads no orphan gets the dependency back. One
    that reads only orphans holding a row of a later JOIN reached from the
    right input through JOINs that each pin the input they match from gets it
    with that JOIN's input added to the determinants: on an orphan that row
    pins the right input. A complete reverse match into the same direct source
    also eliminates the first JOIN's orphans when that JOIN has no extra ON.
    A grouped, final non-null nullable key may fix that exact holder within
    the group; then only the original left-to-right dependency is restored,
    never a generic holder factor. Each dependency keeps the whole left side
    among its determinants.
    """

    def factors(side):
        grain, introduction = side
        return multifact._localized_input_factors(
            grain=grain, introduction_use=introduction, final_grain=final_grain
        )

    def unread_orphans(position, nulls, holder=None):
        # Orphans of JOIN `position`, those with JOIN `holder`'s input NULL.
        for index in range(position + 1, len(joins)):
            join = joins[index]
            first_match, later_match = joins[position].source_match, join.source_match
            if (
                position == 0
                and join.kind in {"inner", "semi"}
                and first_match is not None
                and later_match is not None
                and first_match[4]
                and later_match[0] == joins[position].target
                and later_match[1:3] == first_match[1:3][::-1]
                and Counter(later_match[3])
                == Counter((b, a) for a, b in first_match[3])
            ):
                # A reversed match in the same source cannot exist on its orphan.
                return True
            if index == holder:
                if join.kind in {"inner", "right"}:
                    return True
                nulls |= {join.target}
            elif join.rejects(nulls):
                if join.kind in {"inner", "semi", "right"}:
                    return True
                if join.kind in {"left", "full"}:
                    nulls |= {join.target}
        return unread(nulls)

    dependencies = []
    for position, join in enumerate(joins):
        if join.kind not in {"right", "full"} or not join.forward_one:
            continue
        determinants, dependents = factors(join.left), factors(join.right)
        if not (determinants and dependents):
            continue
        if unread_orphans(position, join.left_inputs):
            dependencies.append(
                ProjectGrainDependencyFact(
                    determinants=determinants, dependents=dependents
                )
            )
            continue
        reached = {join.target}
        for index in range(position + 1, len(joins)):
            later = joins[index]
            if later.kind not in {"inner", "left", "right", "full"} or not (
                later.pins & reached
            ):
                continue
            reached.add(later.target)
            holder = factors(later.right)
            if holder and unread_orphans(position, join.left_inputs, index):
                dependencies.append(
                    ProjectGrainDependencyFact(
                        determinants=(
                            determinants
                            if grouped_holder(later.target)
                            else _ordered_factors(
                                final_grain.active, (*determinants, *holder)
                            )
                        ),
                        dependents=dependents,
                    )
                )
    return tuple(dependencies)


def _holds_key(properties, matched) -> bool:
    """Whether matched value classes of an input cover one of its keys."""

    return bool(matched) and bool(resolved_matching_keys(properties.keys, matched))


def _current_source_match(guarantee, source, unconditional):
    """Complete equality match between exact direct source declaration domains."""
    direction = guarantee.direction
    endpoints = (direction.source.target, direction.target.target)
    if any(
        endpoint is None or type(endpoint.target_occurrence.definition) is not SourceDef
        for endpoint in endpoints
    ):
        return None
    pairs = tuple(
        zip(
            guarantee.source_matched_classes,
            guarantee.target_matched_classes,
            strict=True,
        )
    )
    if any(len(a.members) != 1 or len(b.members) != 1 for a, b in pairs):
        return None
    return (
        source,
        endpoints[0].target_occurrence,
        endpoints[1].target_occurrence,
        tuple(
            (a.members[0].field_position, b.members[0].field_position) for a, b in pairs
        ),
        unconditional,
    )


def _region_join(region: ProjectCurrentJoinRegion, join) -> _RegionJoin:
    """One JOIN of a current region for `resolved_orphan_free_dependencies`."""

    target = join.input_uses[1]
    left = (join.left_input.grain, join.input_uses[0])
    right = (join.right_input.grain, target)
    if not isinstance(join, multifact.ProjectCurrentBinaryJoin):
        # One relationship hop: its equalities read one source input.
        sources = frozenset(pair.left.introduction_use for pair in join.matches)
        guarantee = join.guarantee
        return _RegionJoin(
            join.kind.value,
            False,
            left,
            right,
            frozenset(),
            target,
            lambda nulls: not sources.isdisjoint(nulls),
            sources
            if _holds_key(guarantee.source_output, guarantee.source_matched_classes)
            else frozenset(),
            _current_source_match(guarantee, next(iter(sources)), True)
            if len(sources) == 1
            else None,
        )
    condition = join.condition
    references = {
        id(reference.expression): reference.target
        for reference in condition.references
        if reference.target is not None
    }

    def leaf(
        expression: NameExpr | DottedNameExpr, nulls: frozenset, _truth: object
    ) -> bool:
        field = references.get(id(expression))
        return field is not None and region.introduction(field.binding) in nulls

    # A relationship's field equalities read its one source input.
    base = condition.base_guarantee
    sources = condition.environment.source_candidates
    source = (
        region.introduction(sources[0])
        if base is not None and len(sources) == 1
        else None
    )
    expression = condition.expression

    def rejects(nulls: frozenset) -> bool:
        return source in nulls or (
            expression is not None and _never(expression, True, nulls, leaf)
        )

    pins = set()
    if (
        base is not None
        and source is not None
        and _holds_key(base.source_output, base.source_matched_classes)
    ):
        pins.add(source)
    # `on` equalities of the right input's fields with another input's.
    equated: dict[int, tuple[Any, list[Any]]] = {}
    target_binding = condition.use.target_binding
    for conjunct in condition.conjuncts:
        if type(conjunct) is not ComparisonExpr or conjunct.operator != "==":
            continue
        sides = (references.get(id(conjunct.left)), references.get(id(conjunct.right)))
        for own, other in (sides, sides[::-1]):
            if (
                own is not None
                and other is not None
                and own.binding is target_binding
                and other.binding is not target_binding
            ):
                binding = other.binding
                equated.setdefault(id(binding), (binding, []))[1].append(
                    other.input_field
                )
    for binding, fields in equated.values():
        properties = binding.output
        if properties is not None and _holds_key(
            properties,
            tuple(
                c
                for c in properties.value_classes
                if any(member is item for member in c.members for item in fields)
            ),
        ):
            pins.add(region.introduction(binding))
    return _RegionJoin(
        join.kind.value,
        current_forward_at_most_one(condition),
        left,
        right,
        frozenset(
            field.introduction_use
            for field in join.output.row_shape.fields[: len(join.left_input.fields)]
        ),
        target,
        rejects,
        frozenset(pins),
        _current_source_match(base, source, expression is None)
        if base is not None and source is not None
        else None,
    )


def orphan_free_dependencies(
    aggregate: ProjectJoinedAggregateOccurrence,
) -> tuple[ProjectGrainDependencyFact, ...]:
    input_filter = aggregate.input_filter
    region = input_filter.joined_semantics.multifact_region
    if (
        not aggregate.call.arguments
        or type(region) is not multifact.ProjectCurrentMultiFactRegion
        or not any(
            isinstance(join, multifact.ProjectCurrentBinaryJoin)
            and join.kind in {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}
            for join in region.region.joins
        )
    ):
        return ()
    leaf = _namespace_leaf(input_filter, input_filter.namespace)
    argument, where = aggregate.call.arguments[0], input_filter.where_clause
    groups = None

    def grouped_holder(target):
        nonlocal groups
        if groups is None:
            groups = _protection_members(
                tuple(
                    key
                    for key in _build_group_keys(input_filter)
                    if type(key) is ProjectJoinedGroupKeyOccurrence
                )
            )
        return any(
            use is target
            and _grouped_nullable_key(
                properties,
                tuple(
                    _value_class_for_input_field(properties, key.field_semantics)
                    for key in keys
                ),
                _current_non_null_classes(input_filter, properties, use),
            )
            for properties, use, keys, _ in groups
        )

    return resolved_orphan_free_dependencies(
        region.final_properties.relational.grain,
        tuple(_region_join(region.region, join) for join in region.region.joins),
        lambda nulls: (
            _null_when(argument, nulls, leaf)
            or (where is not None and _never(where.expression, True, nulls, leaf))
        ),
        grouped_holder,
    )


def aggregate_grain_index(
    index: ProjectGrainDependencyIndex,
    dependencies: tuple[ProjectGrainDependencyFact, ...],
) -> ProjectGrainDependencyIndex:
    """The region's dependency index with one aggregate's own dependencies."""

    if not dependencies:
        return index
    return _compile_grain_dependency_index(
        index.universe, (*index.facts, *dependencies)
    )


def resolved_argument_factors(final_grain, has_arguments, dependencies):
    if not has_arguments:
        return final_grain.active
    factors = tuple(
        factor
        for grain, introduction in dependencies
        for factor in multifact._localized_input_factors(
            grain=grain, introduction_use=introduction, final_grain=final_grain
        )
    )
    return _ordered_factors(final_grain.active, factors)


def _multiplicity_exposures(
    *,
    aggregate: ProjectJoinedAggregateOccurrence,
    comparison: multifact.ProjectFactGrainComparison,
) -> tuple[
    multifact.ProjectFactMultiplicityExposure
    | multifact.ProjectCurrentMultiplicityExposure,
    ...,
]:
    region = aggregate.input_filter.joined_semantics.row_source.region
    pairs = resolved_multiplicity_exposures(
        comparison,
        tuple(
            (join, tuple(use.ref for use in join.input_uses)) for join in region.joins
        ),
    )
    if any(
        type(factor) is not multifact.ProjectJoinGrainFactorIdentity
        for _join, additions in pairs
        for factor in additions
    ):
        raise ValueError("Source aggregate exposure requires source JOIN factors.")
    return tuple(
        multifact.ProjectCurrentMultiplicityExposure(
            join=join,
            factor_additions=cast(
                tuple[multifact.ProjectJoinGrainFactorIdentity, ...], additions
            ),
        )
        if isinstance(join, multifact.ProjectCurrentBinaryJoin)
        else multifact.ProjectFactMultiplicityExposure(
            join=join,
            factor_additions=cast(
                tuple[multifact.ProjectJoinGrainFactorIdentity, ...], additions
            ),
        )
        for join, additions in pairs
    )


def resolved_multiplicity_exposures(
    comparison, joins
) -> tuple[tuple[Any, tuple[ProjectGrainFactorIdentity, ...]], ...]:
    """Cover every unresolved finer factor in original JOIN authority order."""
    from pietto._project.project_ir_joins import _is_join_factor

    if comparison.status is not multifact.ProjectIRGrainComparisonStatus.RIGHT_FINER:
        return ()
    unresolved = tuple(
        factor
        for factor in comparison.right.factors
        if factor not in comparison.left_to_right.closure.factors
    )
    result: list[tuple[Any, tuple[ProjectGrainFactorIdentity, ...]]] = []
    covered: set[ProjectGrainFactorIdentity] = set()
    for join, uses in joins:
        additions = tuple(
            factor
            for factor in unresolved
            if _is_join_factor(factor) and factor.introduction_use in uses
        )
        if additions:
            result.append((join, additions))
            covered.update(additions)
    if covered != set(unresolved):
        raise ValueError("Aggregate fanout evidence must cover every finer factor.")
    return tuple(result)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedAggregateGrainLinkage:
    """One aggregate's exact contextual grain and final fanout proof."""

    aggregate: ProjectJoinedAggregateOccurrence
    multifact_region: (
        multifact.ProjectMultiFactConcreteRegion
        | multifact.ProjectCurrentMultiFactRegion
    ) = field(
        repr=False,
        compare=False,
        hash=False,
    )
    argument_factors: tuple[ProjectGrainFactorIdentity, ...]
    group_protection_factors: tuple[ProjectGrainFactorIdentity, ...]
    # The JOIN-side factors computed determinants read; recorded, never seeded.
    computed_key_factors: tuple[ProjectGrainFactorIdentity, ...]
    combined_seed: ProjectGrainFactorSet
    closure: ProjectGrainFactorSet
    contextual_grain: multifact.ProjectFactContextualGrain
    final_grain: multifact.ProjectIRProvidedIntrinsicGrain
    final_comparison: multifact.ProjectFactGrainComparison
    multiplicity_exposures: tuple[
        multifact.ProjectFactMultiplicityExposure
        | multifact.ProjectCurrentMultiplicityExposure,
        ...,
    ]
    multiplicity_risks: tuple[multifact.ProjectMultiFactMultiplicityRisk, ...]
    requirements: tuple[multifact.ProjectMultiFactRequirement, ...]

    def __post_init__(self) -> None:
        if (
            type(self.aggregate) is not ProjectJoinedAggregateOccurrence
            or type(self.multifact_region)
            not in {
                multifact.ProjectMultiFactConcreteRegion,
                multifact.ProjectCurrentMultiFactRegion,
            }
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
            aggregate_grain_index(
                self.multifact_region.grain_index,
                orphan_free_dependencies(self.aggregate),
            ),
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
            or self.computed_key_factors
            != _ordered_factors(self.final_grain.active, self.computed_key_factors)
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


def _computed_key_factors(
    input_filter: ProjectConcreteJoinedRowFilter,
    group_keys: tuple[ProjectJoinedAnyGroupKey, ...],
) -> tuple[ProjectGrainFactorIdentity, ...]:
    """The localized factors of every JOIN side a computed determinant reads."""

    final_grain = (
        input_filter.joined_semantics.multifact_region.final_properties.relational.grain
    )
    return computed_key_factors(
        final_grain,
        tuple(
            (read.input_properties.grain, read.introduction_use)
            for key in group_keys
            if type(key) is ProjectJoinedComputedGroupKeyOccurrence
            for read in key.field_dependencies
        ),
    )


def computed_key_factors(final_grain, reads):
    """Original side law shared with compiled replay; it never feeds a seed."""
    return _ordered_factors(
        final_grain.active,
        tuple(
            factor
            for grain, introduction in reads
            for factor in multifact._localized_input_factors(
                grain=grain, introduction_use=introduction, final_grain=final_grain
            )
        ),
    )


def _build_grain_linkages(
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    group_keys: tuple[ProjectJoinedAnyGroupKey, ...],
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
    protections: tuple[ProjectJoinedGroupProtection, ...],
) -> tuple[ProjectJoinedAggregateGrainLinkage, ...]:
    region = input_filter.joined_semantics.multifact_region
    index = region.grain_index
    final_grain = region.final_properties.relational.grain
    # An UNKNOWN grain has no contextual factors; only a result that already
    # has a group-key, aggregate or output issue reaches here with one.
    if not aggregates or final_grain.state is ProjectGrainBasisState.UNKNOWN:
        return ()
    protection_factors = _ordered_factors(
        final_grain.active,
        tuple(
            factor
            for protection in protections
            for factor in protection.protected_factors
        ),
    )
    computed_factors = _computed_key_factors(input_filter, group_keys)
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
        closure = grain_dependency_closure(
            aggregate_grain_index(index, orphan_free_dependencies(aggregate)), seed
        )
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
                computed_key_factors=computed_factors,
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
    structural, finer, chasm_candidates = resolved_pair_shape(
        left.contextual_grain, right.contextual_grain, comparison, common
    )
    return (
        structural,
        (None if finer is None else (left, right)[finer]),
        chasm_candidates,
    )


def resolved_pair_shape(left, right, comparison, common):
    """Original winner-free contextual grain alignment law."""
    chasm_candidates = (
        common.candidates
        if comparison.status is multifact.ProjectIRGrainComparisonStatus.INCOMPARABLE
        and left.factors
        and right.factors
        else ()
    )
    finer = None
    if left.state is right.state and left.factors == right.factors:
        structural = multifact.ProjectMultiFactStructuralAlignment.EXACTLY_ALIGNED
    elif comparison.status is multifact.ProjectIRGrainComparisonStatus.EQUAL:
        structural = (
            multifact.ProjectMultiFactStructuralAlignment.STRUCTURALLY_ALIGNABLE
        )
    elif comparison.status is multifact.ProjectIRGrainComparisonStatus.LEFT_FINER:
        structural = (
            multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        )
        finer = 0
    elif comparison.status is multifact.ProjectIRGrainComparisonStatus.RIGHT_FINER:
        structural = (
            multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
        )
        finer = 1
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
    # Outputs read whose def argument does not fit: Unknown here, and their
    # PIE-S2395 blocks the predicate.
    unfit_outputs: tuple[str, ...] = ()
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
                or self.unfit_outputs
                or self.retention_effects != _SATISFYING_RETENTION_EFFECTS
            ):
                raise ValueError("Concrete satisfying requires one known Bool result.")
        elif (
            not (self.diagnostics or self.unfit_outputs)
            and self.predicate_value_type.kind is not ValueTypeKind.UNKNOWN
        ) or self.retention_effects:
            # A predicate of unknown type with no error of its own blocks
            # alone; the relation then fails closed with PIE-S2333.
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


@checks_inlined_arguments
def _infer_satisfying_value(
    expression: Expression,
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    outputs: tuple[ProjectJoinedStageOutputOccurrence, ...],
    unsupported_names: set[str],
    mismatched_names: set[str],
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
    diagnostics: list[Diagnostic],
    value_types: dict[Expression, ValueType],
    references: list[ProjectJoinedSatisfyingReference],
) -> ValueType:
    if type(expression) is LiteralExpr:
        value_type = semantic_satisfying._literal_value_type(expression)
    elif type(expression) is ParameterRefExpr:
        value_type = query_parameter_value_type(
            expression.type_name, expression.nullability
        )
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
        elif expression.name in mismatched_names:
            # The output's def argument does not fit (PIE-S2395), so it is
            # Unknown here, as in a single file.
            value_type = semantic_satisfying._UNKNOWN_VALUE_TYPE
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
                # The `let:` name must fit each `def` parameter it is the
                # argument of, as wherever it is typed.
                argument = cast(NameExpr, expression.arguments[0])
                for value in input_filter.namespace.let_values:
                    if value.occurrence.binding.name == argument.name:
                        _check_inlined_argument(
                            argument, value.value_type, diagnostics, None
                        )
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


@checks_inlined_arguments
def _infer_satisfying_predicate(
    expression: Expression,
    *,
    input_filter: ProjectConcreteJoinedRowFilter,
    outputs: tuple[ProjectJoinedStageOutputOccurrence, ...],
    unsupported_names: set[str],
    mismatched_names: set[str],
    aggregates: tuple[ProjectJoinedAggregateOccurrence, ...],
    diagnostics: list[Diagnostic],
    value_types: dict[Expression, ValueType],
    references: list[ProjectJoinedSatisfyingReference],
) -> ValueType:
    if type(expression) in {NameExpr, LiteralExpr, ParameterRefExpr, CallExpr}:
        return _infer_satisfying_value(
            expression,
            input_filter=input_filter,
            outputs=outputs,
            unsupported_names=unsupported_names,
            mismatched_names=mismatched_names,
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
            mismatched_names=mismatched_names,
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
            mismatched_names=mismatched_names,
            aggregates=aggregates,
            diagnostics=diagnostics,
            value_types=value_types,
            references=references,
        )
        if left.kind is ValueTypeKind.UNKNOWN or right.kind is ValueTypeKind.UNKNOWN:
            value_type = semantic_satisfying._UNKNOWN_VALUE_TYPE
        else:
            value_type, expected = resolved_comparison_value_type(
                left,
                right,
                literals=comparison_literals(
                    expression.left, expression.right, RowSchema(), None
                ),
            )
            if expected is not None:
                diagnostics.append(
                    semantic_satisfying._invalid_operands_diagnostic(
                        expression, expected
                    )
                )
        value_types[expression] = value_type
        return value_type
    if type(expression) is BinaryExpr and expression.operator in {"and", "or"}:
        left = _infer_satisfying_predicate(
            expression.left,
            input_filter=input_filter,
            outputs=outputs,
            unsupported_names=unsupported_names,
            mismatched_names=mismatched_names,
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
            mismatched_names=mismatched_names,
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
                semantic_satisfying._invalid_operands_diagnostic(
                    expression, "Bool operands"
                )
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
    mismatched_names: set[str],
) -> ProjectJoinedSatisfyingAnalysis | None:
    definition = _definition(input_filter)
    clause = definition.satisfying_clause
    if clause is None:
        return None
    diagnostic = semantic_satisfying.no_group_satisfying_diagnostic(definition)
    if diagnostic is not None:
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
        mismatched_names=mismatched_names,
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
        elif value_type.kind is ValueTypeKind.UNKNOWN:
            # As in a single file, a null literal compared or combined in the
            # predicate is PIE-S2327; any other predicate of unknown type
            # leaves the relation to its completion's PIE-S2333.
            null_literal = semantic_satisfying._null_literal_leaf(clause.expression)
            if null_literal is not None:
                diagnostics.append(
                    semantic_satisfying._unsupported_expression_diagnostic(
                        null_literal, form="null literal"
                    )
                )
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
        unfit_outputs=tuple(
            dict.fromkeys(
                expression.name
                for expression in value_types
                if type(expression) is NameExpr and expression.name in mismatched_names
            )
        ),
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
    group_keys: tuple[ProjectJoinedAnyGroupKey, ...],
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
    final_grain = (
        input_filter.joined_semantics.multifact_region.final_properties.relational.grain
    )
    if (
        any(
            type(key)
            not in {
                ProjectJoinedGroupKeyOccurrence,
                ProjectJoinedComputedGroupKeyOccurrence,
            }
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
            or linkage.computed_key_factors
            != _computed_key_factors(input_filter, group_keys)
            or linkage.group_protection_factors
            != _ordered_factors(
                final_grain.active,
                tuple(
                    factor
                    for protection in group_protections
                    for factor in protection.protected_factors
                ),
            )
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
        members = _protection_members(group_keys)
        if (
            clause is None
            or len(group_keys) != len(clause.items)
            or any(
                key.item is not item
                for key, item in zip(group_keys, clause.items, strict=True)
            )
            # Every JOIN side a key reads keeps exactly its own protection record.
            or len(group_protections) != len(members)
            or any(
                protection.input_properties is not properties
                or protection.introduction_use is not introduction_use
                or not _same_objects(protection.group_keys, direct)
                or not _same_objects(protection.computed_keys, computed)
                for protection, (properties, introduction_use, direct, computed) in zip(
                    group_protections, members, strict=True
                )
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
    group_keys: tuple[ProjectJoinedAnyGroupKey, ...]
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
    INTRINSIC_GRAIN_NON_CONCRETE = "intrinsic_grain_non_concrete"
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
    grain_blocker: multifact.ProjectIRProvidedIntrinsicGrain | None = field(
        default=None, repr=False, compare=False, hash=False
    )
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
                    self.grain_blocker is not None,
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
        if self.reason is (
            ProjectJoinedAggregationNonConcreteReason.INTRINSIC_GRAIN_NON_CONCRETE
        ):
            final_grain = self.input_filter.joined_semantics.multifact_region.final_properties.relational.grain
            if (
                self.grain_blocker is not final_grain
                or final_grain.state is not ProjectGrainBasisState.UNKNOWN
                or self.mode is ProjectJoinedAggregationMode.ABSENT
                or not self.aggregate_results
                or any(
                    type(item) is ProjectJoinedGroupKeyIssue
                    for item in self.group_key_results
                )
                or any(
                    type(item) is ProjectJoinedAggregateIssue
                    for item in self.aggregate_results
                )
                or self.selected_output_issues
                or self.grain_linkages
                or self.pair_linkages
                or self.satisfying is not None
                or self.diagnostics
            ):
                raise ValueError(
                    "Unknown-grain terminal requires its exact aggregate blocker."
                )
            return
        if self.grain_blocker is not None:
            raise ValueError("Other aggregate terminals cannot borrow a grain blocker.")
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
        item for item in group_key_results if isinstance(item, ProjectJoinedAnyGroupKey)
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
    has_group_issue = any(
        type(item) is ProjectJoinedGroupKeyIssue for item in group_key_results
    )
    has_aggregate_issue = any(
        type(item) is ProjectJoinedAggregateIssue for item in aggregate_results
    )
    if (
        not has_group_issue
        and not has_aggregate_issue
        and not selected_output_issues
        and aggregates
    ):
        final_grain = input_filter.joined_semantics.multifact_region.final_properties.relational.grain
        if final_grain.state is ProjectGrainBasisState.UNKNOWN:
            return ProjectNonConcreteJoinedAggregation(
                filter_set=filter_set,
                input_filter=input_filter,
                reason=(
                    ProjectJoinedAggregationNonConcreteReason.INTRINSIC_GRAIN_NON_CONCRETE
                ),
                mode=mode,
                group_key_results=group_key_results,
                aggregate_results=aggregate_results,
                stage_outputs=stage_outputs,
                group_protections=group_protections,
                grain_blocker=final_grain,
            )
    grain_linkages = _build_grain_linkages(
        input_filter=input_filter,
        group_keys=group_keys,
        aggregates=aggregates,
        protections=group_protections,
    )
    pair_linkages = _build_pair_linkages(grain_linkages)
    satisfying = _build_satisfying_analysis(
        input_filter=input_filter,
        mode=mode,
        outputs=stage_outputs,
        aggregates=aggregates,
        # Outputs whose def argument does not fit (PIE-S2395).
        mismatched_names={
            name
            for issue in (
                *(
                    item
                    for item in aggregate_results
                    if type(item) is ProjectJoinedAggregateIssue
                ),
                *selected_output_issues,
            )
            if issue.kind
            in {
                ProjectJoinedAggregateIssueKind.DEF_ARGUMENT_MISMATCH,
                ProjectJoinedSelectedOutputIssueKind.DEF_ARGUMENT_MISMATCH,
            }
            and issue.item is not None
            and (name := _projection_output_name(issue.item)) is not None
        },
    )
    diagnostics = _ordered_diagnostics(
        group_key_results=group_key_results,
        aggregate_results=aggregate_results,
        selected_output_issues=selected_output_issues,
        satisfying=satisfying,
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


def _current_non_null_classes(input_filter, properties, introduction_use):
    """Input classes whose exact final joined occurrence is proved non-null."""
    fields = {
        field.input_field
        for field in input_filter.fields
        if field.input_properties is properties
        and field.introduction_use is introduction_use
        and field.effective_nullability is ProjectRowFieldNullability.NON_NULL
    }
    return tuple(
        value_class
        for value_class in properties.value_classes
        if any(member in fields for member in value_class.members)
    )


def _grouped_nullable_key(properties, classes, non_null_classes):
    """A fixed non-null key for one orphan holder, never a generic grain seed."""
    keys = tuple(
        key
        for key in properties.keys
        if key.strength is ProjectRowUniquenessStrength.LAX
        and all(value_class in non_null_classes for value_class in key.determinants)
    )
    if not keys:
        return False
    seed = _value_class_set(properties, classes)
    return any(
        strictly_determines_output(
            properties.fd_index, seed, _value_class_set(properties, key.determinants)
        ).status
        is ProjectIROutputDeterminationStatus.PROVEN
        for key in keys
    )


def resolved_group_protection(properties, introduction_use, final_grain, classes):
    """Original complete STRICT-key proof law after field/use resolution."""
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
    return seed, strict_keys, determinations, protected


@dataclass(frozen=True, slots=True, eq=False)
class CompiledAggregateFieldDependency:
    expression: Any
    path: tuple
    input_properties: ProjectIROutputRelationalProperties
    introduction_use: multifact.CompiledGrainUse
    input_field: Any


@dataclass(frozen=True, slots=True, eq=False)
class CompiledAggregateOccurrence:
    stage: Any = field(repr=False)
    ref: Any
    function: str
    arguments: tuple
    field_dependencies: tuple[CompiledAggregateFieldDependency, ...]


@dataclass(frozen=True, slots=True, eq=False)
class CompiledGroupProtection:
    stage: Any = field(repr=False)
    input_properties: ProjectIROutputRelationalProperties
    introduction_use: multifact.CompiledGrainUse
    group_keys: tuple
    computed_keys: tuple
    seed: Any
    strict_keys: tuple
    determinations: tuple
    protected_factors: tuple


@dataclass(frozen=True, slots=True, eq=False)
class CompiledAggregateGrainLinkage:
    aggregate: CompiledAggregateOccurrence
    multifact_region: multifact.CompiledMultiFactRegion
    argument_factors: tuple
    group_protection_factors: tuple
    computed_key_factors: tuple
    combined_seed: Any
    closure: Any
    contextual_grain: multifact.ProjectFactContextualGrain
    final_grain: Any
    final_comparison: multifact.ProjectFactGrainComparison
    multiplicity_exposures: tuple[multifact.CompiledMultiplicityExposure, ...]
    multiplicity_risks: tuple
    requirements: tuple


@dataclass(frozen=True, slots=True, eq=False)
class CompiledAggregatePairLinkage:
    left: CompiledAggregateGrainLinkage
    right: CompiledAggregateGrainLinkage
    grain_comparison: multifact.ProjectFactGrainComparison
    common_grain: multifact.ProjectCommonGrainResult
    chasm_candidates: tuple
    structural: multifact.ProjectMultiFactStructuralAlignment
    finer: CompiledAggregateGrainLinkage | None
    multiplicity_risks: tuple
    requirements: tuple


@dataclass(frozen=True, slots=True, eq=False)
class CompiledAggregateEvidence:
    stage: Any = field(repr=False)
    region: multifact.CompiledMultiFactRegion
    group_protections: tuple[CompiledGroupProtection, ...]
    aggregates: tuple[CompiledAggregateOccurrence, ...]
    grain_linkages: tuple[CompiledAggregateGrainLinkage, ...]
    pair_linkages: tuple[CompiledAggregatePairLinkage, ...]

    @property
    def risks(self):
        return (*self.group_protections, *self.grain_linkages, *self.pair_linkages)


def compiled_field_dependencies(ir, region, arguments):
    """Resolved field-use ancestry, stopping at each original JOIN introduction."""
    from pietto._project.project_compiled_schema import Address, MAX_RECORDS

    records, refs = ir.completed.root.records, ir.references
    joins = {join.record.address for join in region.joins}
    retained, visits = [], 0
    for argument in arguments:
        pending: list[tuple[Address, tuple[Address, ...]]] = [(argument, ())]
        while pending:
            address, path = pending.pop()
            visits += 1
            if visits > MAX_RECORDS or address in path:
                raise ValueError("COMPILED_AGGREGATE_DEPENDENCY_EXPANSION")
            record = records[address]
            path = (*path, address)
            if address.kind == "read":
                use_address = record.get("use")
                if (
                    use_address in region.uses
                    and records[use_address].get("producer") not in joins
                ):
                    use = region.uses[use_address]
                    properties = use.producer.properties.relational
                    port = records[record.get("port")]
                    retained.append(
                        (
                            refs[address],
                            tuple(refs[a] for a in path),
                            properties,
                            use,
                            properties.fields[port.get("ordinal")],
                        )
                    )
                    continue
                pending.append((record.get("port"), path))
            elif address.kind == "port":
                pending.append((record.get("source"), path))
            elif address.kind == "join_value":
                pending.append((record.get("input"), path))
            elif address.kind == "operation":
                pending.extend((a, path) for a in reversed(record.get("operands")))
            elif address.kind not in ("literal", "null_literal"):
                raise ValueError("COMPILED_AGGREGATE_DEPENDENCY")
    return tuple(retained)


def compiled_orphan_free_dependencies(ir, region, stage, arguments):
    """`orphan_free_dependencies` over compiled records: a read is followed
    through the region's JOIN outputs to the input that introduced it, and
    WHERE is the predicate of each row stage between the JOINs and ``stage``."""
    from pietto._project.project_compiled_schema import MAX_RECORDS

    records = ir.completed.root.records
    joins = {join.record.address: join for join in region.joins}
    known: dict[tuple[Any, frozenset, bool | None], bool] = {}
    visits = 0

    def introductions(use):
        join = joins.get(records[use].get("producer"))
        if join is None:
            return frozenset((use,))
        inputs = join.record.get("inputs")
        if join.record.get("kind") in ("semi", "anti"):
            inputs = inputs[:1]
        return frozenset().union(*map(introductions, inputs))

    def origin(address):
        # The introducing input and its field ordinal one read takes.
        record = records[address]
        if address.kind == "read":
            use = record.get("use")
            if use in region.uses and records[use].get("producer") not in joins:
                return use, records[record.get("port")].get("ordinal")
            return origin(record.get("port"))
        if address.kind in ("port", "join_value"):
            return origin(record.get("source" if address.kind == "port" else "input"))
        return None

    def ask(address, nulls, truth=None):
        # `_null_when` for ``truth`` None, else `_never`, over compiled records.
        nonlocal visits
        if (address, nulls, truth) in known:
            return known[address, nulls, truth]
        visits += 1
        if visits > MAX_RECORDS:
            raise ValueError("COMPILED_AGGREGATE_DEPENDENCY_EXPANSION")
        record = records[address]
        if address.kind == "read":
            use = record.get("use")
            if use in region.uses and records[use].get("producer") not in joins:
                result = use in nulls
            else:
                result = ask(record.get("port"), nulls, truth)
        elif address.kind in ("port", "join_value"):
            source = record.get("source" if address.kind == "port" else "input")
            result = ask(source, nulls, truth)
        elif address.kind == "operation":
            (role, token), operands = record.get("operator"), record.get("operands")
            if truth is not None and role == "binary" and token in ("and", "or"):
                left, right = (ask(a, nulls, truth) for a in operands)
                conjunction = (token == "and") == truth
                result = (left or right) if conjunction else (left and right)
            elif truth is not None and role == "not":
                result = ask(operands[0], nulls, not truth)
            elif truth is not None and role == "null_test":
                result = (token == "is_not_null") == truth and ask(operands[0], nulls)
            elif truth is not None and role == "membership" and len(operands) == 1:
                result = (token == "not_in") != truth
            else:
                result = operation_null_when(
                    role,
                    token,
                    tuple(
                        ask(
                            a, nulls, True if role == "conditional" and i == 1 else None
                        )
                        for i, a in enumerate(operands)
                    ),
                )
        else:
            result = False
        known[address, nulls, truth] = result
        return result

    if not arguments or not any(
        join.record.get("kind") in ("right", "full") for join in region.joins
    ):
        return ()
    entries = []
    for join in region.joins:
        kind = join.record.get("kind")
        left_address, right_address = join.record.get("inputs")
        left, right = region.uses[left_address], region.uses[right_address]
        right_properties = right.producer.properties.relational
        equalities = tuple(
            records[a].get("left") for a in join.record.get("equalities")
        )
        predicate = join.record.get("predicate")
        # The fields each other input's equalities with the right input match.
        equated: dict[Any, set[int]] = {}
        reads = [read for read in map(origin, equalities) if read is not None]
        if len(reads) == len(equalities) and len({use for use, _ in reads}) == 1:
            equated[reads[0][0]] = {ordinal for _, ordinal in reads}
        pending = [] if predicate is None else [predicate]
        while pending:
            address = pending.pop()
            if address.kind != "operation":
                continue
            operator, operands = (
                records[address].get("operator"),
                records[address].get("operands"),
            )
            if tuple(operator) == ("binary", "and"):
                pending.extend(operands)
            elif tuple(operator) == ("comparison", "=="):
                sides = tuple(origin(a) for a in operands)
                for own, other in (sides, sides[::-1]):
                    if (
                        own is not None
                        and other is not None
                        and own[0] == right_address
                        and other[0] != right_address
                    ):
                        equated.setdefault(other[0], set()).add(other[1])
        pins = set()
        for use, ordinals in equated.items():
            properties = region.uses[use].producer.properties.relational
            if _holds_key(
                properties,
                tuple(
                    c
                    for c in properties.value_classes
                    if any(m.field_position in ordinals for m in c.members)
                ),
            ):
                pins.add(use)
        source_match = None
        correspondence = tuple(
            (origin(records[a].get("left")), origin(records[a].get("right")))
            for a in join.record.get("equalities")
        )
        pairs = tuple(
            (a, b) for a, b in correspondence if a is not None and b is not None
        )
        if (
            pairs
            and len(pairs) == len(correspondence)
            and len({a[0] for a, _ in pairs}) == 1
            and all(b[0] == right_address for _, b in pairs)
        ):
            source_use = pairs[0][0][0]
            producers = tuple(
                records[records[u].get("producer")] for u in (source_use, right_address)
            )
            if all(p.address.kind == "source" for p in producers):
                source_match = (
                    source_use,
                    producers[0].get("declaration"),
                    producers[1].get("declaration"),
                    tuple((a[1], b[1]) for a, b in pairs),
                    predicate is None,
                )
        entries.append(
            _RegionJoin(
                kind,
                kind in ("right", "full")
                and compiled_forward_at_most_one(
                    records, join.record, right_properties
                ),
                (left.producer.properties.relational.grain, left),
                (right_properties.grain, right),
                introductions(left_address),
                right_address,
                lambda nulls, equalities=equalities, predicate=predicate: (
                    any(ask(a, nulls) for a in equalities)
                    or (predicate is not None and ask(predicate, nulls, True))
                ),
                frozenset(pins),
                source_match,
            )
        )
    predicates = []
    producer = stage.record.get("input")
    while producer.kind == "row" and records[producer].get("owner") == (
        stage.record.get("owner")
    ):
        if records[producer].get("predicate") is not None:
            predicates.append(records[producer].get("predicate"))
        producer = records[producer].get("input")
    groups = None

    def grouped_holder(target):
        nonlocal groups
        if groups is None:
            groups, _ = _compiled_protection_inputs(ir, stage, region)
        return any(
            use is region.uses[target]
            and bool(keys)
            and _grouped_nullable_key(
                properties,
                classes,
                _compiled_non_null_classes(ir, region, properties, use),
            )
            for properties, use, keys, classes, _ in groups
        )

    return resolved_orphan_free_dependencies(
        region.final_properties.grain,
        tuple(entries),
        lambda nulls: (
            ask(arguments[0], nulls) or any(ask(p, nulls, True) for p in predicates)
        ),
        grouped_holder,
    )


def _compiled_non_null_classes(ir, region, properties, use):
    from pietto._project.project_compiled_schema import Address

    fields = set()
    for final_field in region.joins[-1].fields:
        if final_field.effective_nullability is not ProjectRowFieldNullability.NON_NULL:
            continue
        dependencies = compiled_field_dependencies(
            ir, region, (Address(final_field.ref.kind, final_field.ref.position),)
        )
        fields.update(
            original
            for _, _, incoming, introduction, original in dependencies
            if incoming is properties and introduction is use
        )
    return tuple(
        value_class
        for value_class in properties.value_classes
        if any(member in fields for member in value_class.members)
    )


def _compiled_protection_inputs(ir, stage, region):
    """Per JOIN-side root: direct keys with their classes, then computed keys.

    A determinant is direct iff it reaches exactly one field without any
    operation; any other determinant is a computed LET value, recorded on every
    side it reads and never seeding a class. Also returns those computed reads.
    """
    groups, computed_reads = [], []

    def root(properties, use):
        existing = next((g for g in groups if g[0] is properties and g[1] is use), None)
        if existing is None:
            existing = (properties, use, [], [], [])
            groups.append(existing)
        return existing

    for key in stage.record.get("keys"):
        dependencies = compiled_field_dependencies(ir, region, (key,))
        if len(dependencies) == 1 and not any(
            step.kind == "operation" for step in dependencies[0][1]
        ):
            _expression, _path, properties, use, field = dependencies[0]
            matches = tuple(
                c
                for c in properties.value_classes
                if any(f is field for f in c.members)
            )
            if len(matches) != 1:
                raise ValueError("COMPILED_GROUP_KEY_CLASS")
            existing = root(properties, use)
            existing[2].append(ir.references[key])
            existing[3].append(matches[0])
            continue
        for _expression, _path, properties, use, _field in dependencies:
            existing = root(properties, use)
            if not any(k is ir.references[key] for k in existing[4]):
                existing[4].append(ir.references[key])
            computed_reads.append((properties.grain, use))
    return tuple(
        (properties, use, tuple(keys), tuple(classes), tuple(computed))
        for properties, use, keys, classes, computed in groups
    ), tuple(computed_reads)


def _compiled_pair_values(left, right):
    region = left.multifact_region
    comparison = multifact._compare_grains(
        region.grain_index, left.contextual_grain, right.contextual_grain
    )
    common = multifact._common_grain(
        index=region.grain_index,
        left=left.contextual_grain,
        right=right.contextual_grain,
        actual_candidates=region.actual_candidates,
    )
    structural, finer, chasms = resolved_pair_shape(
        left.contextual_grain, right.contextual_grain, comparison, common
    )
    risks = []
    if left.multiplicity_exposures or right.multiplicity_exposures:
        risks.append(multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK)
    if chasms:
        risks.append(
            multifact.ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION
        )
    requirements = (
        (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
        if (
            structural
            is multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
            or risks
        )
        else ()
    )
    return (
        comparison,
        common,
        chasms,
        structural,
        None if finer is None else (left, right)[finer],
        tuple(risks),
        requirements,
    )


def build_compiled_aggregate_evidence(ir):
    records, refs = ir.completed.root.records, ir.references
    result = []
    for stage in ir.operators:
        if stage.kind != "aggregate" or stage.record.get("risk_law") is None:
            continue
        region = multifact.build_compiled_region(ir, stage)
        grain, index = region.final_properties.grain, region.grain_index
        protections = []
        groups, computed_reads = _compiled_protection_inputs(ir, stage, region)
        computed_factors = computed_key_factors(grain, computed_reads)
        for properties, use, keys, classes, computed in groups:
            seed, strict_keys, determinations, factors = resolved_group_protection(
                properties,
                use,
                grain,
                classes,
            )
            protections.append(
                CompiledGroupProtection(
                    stage,
                    properties,
                    use,
                    keys,
                    computed,
                    seed,
                    strict_keys,
                    determinations,
                    factors,
                )
            )
        protected = _ordered_factors(
            grain.active, tuple(f for p in protections for f in p.protected_factors)
        )
        aggregates, linkages = [], []
        full = multifact.ProjectFactContextualGrain(
            authority=grain,
            state=grain.state,
            factors=grain.active,
            evidence=region.final_properties,
        )
        for address in stage.record.get("values"):
            record = records[address]
            arguments = record.get("arguments")
            dependencies = tuple(
                CompiledAggregateFieldDependency(*parts)
                for parts in compiled_field_dependencies(ir, region, arguments)
            )
            aggregate = CompiledAggregateOccurrence(
                stage,
                refs[address],
                record.get("function"),
                tuple(refs[a] for a in arguments),
                dependencies,
            )
            aggregates.append(aggregate)
            argument_factors = resolved_argument_factors(
                grain,
                bool(arguments),
                tuple(
                    (d.input_properties.grain, d.introduction_use) for d in dependencies
                ),
            )
            combined = _ordered_factors(grain.active, (*argument_factors, *protected))
            seed = multifact._factor_set(index, combined)
            closure = grain_dependency_closure(
                aggregate_grain_index(
                    index,
                    compiled_orphan_free_dependencies(ir, region, stage, arguments),
                ),
                seed,
            )
            contextual = multifact.ProjectFactContextualGrain(
                authority=grain,
                state=ProjectGrainBasisState.FACTORIZED
                if closure.factors
                else ProjectGrainBasisState.GLOBAL,
                factors=closure.factors,
                evidence=aggregate,
            )
            comparison = multifact._compare_grains(index, contextual, full)
            additions = resolved_multiplicity_exposures(
                comparison,
                tuple(
                    (join, tuple(refs[a] for a in join.record.get("inputs")))
                    for join in region.joins
                ),
            )
            exposures = tuple(
                multifact.CompiledMultiplicityExposure(join, factors)
                for join, factors in additions
            )
            risks = (
                (multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,)
                if exposures
                else ()
            )
            requirements = (
                (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
                if exposures
                else ()
            )
            linkages.append(
                CompiledAggregateGrainLinkage(
                    aggregate,
                    region,
                    argument_factors,
                    protected,
                    computed_factors,
                    seed,
                    closure,
                    contextual,
                    grain,
                    comparison,
                    exposures,
                    risks,
                    requirements,
                )
            )
        pairs = tuple(
            CompiledAggregatePairLinkage(
                left, right, *_compiled_pair_values(left, right)
            )
            for i, left in enumerate(linkages)
            for right in linkages[i + 1 :]
        )
        result.append(
            CompiledAggregateEvidence(
                stage,
                region,
                tuple(protections),
                tuple(aggregates),
                tuple(linkages),
                pairs,
            )
        )
    return tuple(result)


def verify_compiled_aggregate_evidence(
    ir, supplied: tuple[CompiledAggregateEvidence, ...]
):
    """Inspect every current FD, dependency, localization and pair relationship."""
    from pietto._project.project_compiled_verification import need
    from pietto._project.project_ir_relational_properties import (
        strict_output_fd_closure,
    )

    stages = tuple(
        o
        for o in ir.operators
        if o.kind == "aggregate" and o.record.get("risk_law") is not None
    )
    records, refs = ir.completed.root.records, ir.references
    need(
        type(supplied) is tuple and len(supplied) == len(stages),
        "AGGREGATE_EVIDENCE_INVENTORY",
    )

    def same(a, b):
        return (
            type(a) is tuple
            and len(a) == len(b)
            and all(x is y for x, y in zip(a, b, strict=True))
        )

    for evidence, stage in zip(supplied, stages, strict=True):
        need(
            type(evidence) is CompiledAggregateEvidence and evidence.stage is stage,
            "AGGREGATE_EVIDENCE_ROOT",
        )
        region = evidence.region
        multifact.verify_compiled_region(region, ir, stage)
        grain, index = region.final_properties.grain, region.grain_index
        groups, computed_reads = _compiled_protection_inputs(ir, stage, region)
        computed_factors = computed_key_factors(grain, computed_reads)
        need(
            type(evidence.group_protections) is tuple
            and len(evidence.group_protections) == len(groups),
            "GROUP_PROTECTION_INVENTORY",
        )
        for protection, (properties, use, keys, classes, computed) in zip(
            evidence.group_protections, groups, strict=True
        ):
            need(
                type(protection) is CompiledGroupProtection
                and protection.stage is stage
                and protection.input_properties is properties
                and protection.introduction_use is use
                and same(protection.group_keys, keys)
                and same(protection.computed_keys, computed)
                and protection.seed.index is properties.fd_index
                and same(
                    protection.seed.classes,
                    tuple(c for c in properties.fd_index.universe if c in classes),
                ),
                "GROUP_PROTECTION_ROOT",
            )
            strict_keys = tuple(
                key
                for key in properties.keys
                if key.strength is ProjectRowUniquenessStrength.STRICT
            )
            need(
                same(protection.strict_keys, strict_keys)
                and len(protection.determinations) == len(strict_keys),
                "GROUP_PROTECTION_KEYS",
            )
            closure = strict_output_fd_closure(properties.fd_index, protection.seed)
            for determination, key in zip(
                protection.determinations, strict_keys, strict=True
            ):
                status = (
                    ProjectIROutputDeterminationStatus.PROVEN
                    if all(c in closure.classes.classes for c in key.determinants)
                    else ProjectIROutputDeterminationStatus.NOT_PROVEN
                )
                need(
                    determination.seed is protection.seed
                    and determination.requested.index is properties.fd_index
                    and same(determination.requested.classes, key.determinants)
                    and determination.closure == closure
                    and determination.status is status,
                    "GROUP_PROTECTION_DETERMINATION",
                )
            proven = any(
                d.status is ProjectIROutputDeterminationStatus.PROVEN
                for d in protection.determinations
            )
            factors = (
                multifact._localized_input_factors(
                    grain=properties.grain, introduction_use=use, final_grain=grain
                )
                if proven
                else ()
            )
            need(
                same(protection.protected_factors, factors), "GROUP_PROTECTION_FACTORS"
            )
        values = stage.record.get("values")
        need(
            len(evidence.aggregates) == len(values) == len(evidence.grain_linkages),
            "AGGREGATE_LINKAGE_INVENTORY",
        )
        protected = _ordered_factors(
            grain.active,
            tuple(f for p in evidence.group_protections for f in p.protected_factors),
        )
        for aggregate, linkage, address in zip(
            evidence.aggregates, evidence.grain_linkages, values, strict=True
        ):
            record = records[address]
            parts = compiled_field_dependencies(ir, region, record.get("arguments"))
            need(
                type(aggregate) is CompiledAggregateOccurrence
                and aggregate.stage is stage
                and aggregate.ref is refs[address]
                and aggregate.function == record.get("function")
                and same(
                    aggregate.arguments, tuple(refs[a] for a in record.get("arguments"))
                )
                and len(aggregate.field_dependencies) == len(parts),
                "AGGREGATE_OCCURRENCE",
            )
            for dependency, (expression, path, properties, use, input_field) in zip(
                aggregate.field_dependencies, parts, strict=True
            ):
                need(
                    type(dependency) is CompiledAggregateFieldDependency
                    and dependency.expression is expression
                    and same(dependency.path, path)
                    and dependency.input_properties is properties
                    and dependency.introduction_use is use
                    and dependency.input_field is input_field,
                    "AGGREGATE_FIELD_DEPENDENCY",
                )
            argument_factors = resolved_argument_factors(
                grain,
                bool(record.get("arguments")),
                tuple((part[2].grain, part[3]) for part in parts),
            )
            combined = _ordered_factors(grain.active, (*argument_factors, *protected))
            need(
                type(linkage) is CompiledAggregateGrainLinkage
                and linkage.aggregate is aggregate
                and linkage.multifact_region is region
                and same(linkage.argument_factors, argument_factors)
                and same(linkage.group_protection_factors, protected)
                and same(linkage.computed_key_factors, computed_factors)
                and linkage.combined_seed.universe is index.universe
                and same(linkage.combined_seed.factors, combined)
                and linkage.final_grain is grain,
                "AGGREGATE_LINKAGE_ROOT",
            )
            closure = grain_dependency_closure(
                aggregate_grain_index(
                    index,
                    compiled_orphan_free_dependencies(
                        ir, region, stage, record.get("arguments")
                    ),
                ),
                linkage.combined_seed,
            )
            need(
                linkage.closure.universe is index.universe
                and same(linkage.closure.factors, closure.factors)
                and linkage.contextual_grain.authority is grain
                and linkage.contextual_grain.evidence is aggregate
                and same(linkage.contextual_grain.factors, closure.factors),
                "AGGREGATE_LINKAGE_CLOSURE",
            )
            comparison = linkage.final_comparison
            need(
                comparison.left is linkage.contextual_grain
                and comparison.right.authority is grain
                and same(comparison.right.factors, grain.active)
                and comparison.right.evidence is region.final_properties,
                "AGGREGATE_FINAL_COMPARISON",
            )
            multifact.verify_compiled_grain_comparison(
                comparison, index, linkage.contextual_grain, comparison.right
            )
            additions = resolved_multiplicity_exposures(
                comparison,
                tuple(
                    (j, tuple(refs[a] for a in j.record.get("inputs")))
                    for j in region.joins
                ),
            )
            need(
                len(linkage.multiplicity_exposures) == len(additions),
                "AGGREGATE_EXPOSURE_INVENTORY",
            )
            for exposure, (join, factors) in zip(
                linkage.multiplicity_exposures, additions, strict=True
            ):
                need(
                    type(exposure) is multifact.CompiledMultiplicityExposure
                    and exposure.join is join
                    and same(exposure.factor_additions, factors),
                    "AGGREGATE_EXPOSURE",
                )
            need(
                linkage.multiplicity_risks
                == (
                    (multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,)
                    if additions
                    else ()
                )
                and linkage.requirements
                == (
                    (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
                    if additions
                    else ()
                ),
                "AGGREGATE_RISKS",
            )
        pairs = tuple(
            (left, right)
            for i, left in enumerate(evidence.grain_linkages)
            for right in evidence.grain_linkages[i + 1 :]
        )
        need(len(evidence.pair_linkages) == len(pairs), "AGGREGATE_PAIR_INVENTORY")
        for pair, (left, right) in zip(evidence.pair_linkages, pairs, strict=True):
            need(
                type(pair) is CompiledAggregatePairLinkage
                and pair.left is left
                and pair.right is right,
                "AGGREGATE_PAIR_ROOT",
            )
            comparison = pair.grain_comparison
            need(
                comparison.left is left.contextual_grain
                and comparison.right is right.contextual_grain,
                "AGGREGATE_PAIR_COMPARISON",
            )
            multifact.verify_compiled_grain_comparison(
                comparison, index, left.contextual_grain, right.contextual_grain
            )
            expected_common = multifact._common_grain(
                index=index,
                left=left.contextual_grain,
                right=right.contextual_grain,
                actual_candidates=region.actual_candidates,
            )
            need(pair.common_grain == expected_common, "AGGREGATE_COMMON_GRAIN")
            structural, finer, chasms = resolved_pair_shape(
                left.contextual_grain,
                right.contextual_grain,
                comparison,
                pair.common_grain,
            )
            need(
                pair.structural is structural
                and pair.finer is (None if finer is None else (left, right)[finer])
                and same(pair.chasm_candidates, chasms),
                "AGGREGATE_PAIR_SHAPE",
            )
            risks = tuple(
                risk
                for risk, present in (
                    (
                        multifact.ProjectMultiFactMultiplicityRisk.FANOUT_RISK,
                        bool(
                            left.multiplicity_exposures or right.multiplicity_exposures
                        ),
                    ),
                    (
                        multifact.ProjectMultiFactMultiplicityRisk.CROSS_FACT_MULTIPLICATION,
                        bool(chasms),
                    ),
                )
                if present
            )
            need(
                pair.multiplicity_risks == risks
                and pair.requirements
                == (
                    (multifact.ProjectMultiFactRequirement.AGGREGATE_ALGEBRA_REQUIRED,)
                    if structural
                    is multifact.ProjectMultiFactStructuralAlignment.REAGGREGATION_REQUIRED
                    or risks
                    else ()
                ),
                "AGGREGATE_PAIR_RISKS",
            )
    return supplied
