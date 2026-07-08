"""Private project row expression schema adapter."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from pietto._project.model import (
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowFieldNullability,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
)
from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    FieldDef,
    IsNullExpr,
    NameExpr,
    UnaryExpr,
)
from pietto.errors import SourceLocation
from pietto.semantic.model import (
    EffectiveNullability,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

_PROJECT_BUILTIN_TYPE_NAMES = frozenset(
    {
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    }
)
_SEMANTIC_AGGREGATE_NAMES = frozenset(
    {"count", "count_distinct", "sum", "avg", "min", "max"}
)


class ProjectExpressionSchemaStatus(StrEnum):
    """Private availability status for one row expression schema result."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


class ProjectExpressionSchemaReason(StrEnum):
    """Private deterministic reason for one row expression schema result."""

    DIRECT_FIELD = "direct_field"
    RENAMED_PROJECTION = "renamed_projection"
    KNOWN_EXPRESSION_VALUE = "known_expression_value"
    KNOWN_LET_VALUE = "known_let_value"
    MISSING_VALUE_TYPE = "missing_value_type"
    UNKNOWN_VALUE_TYPE = "unknown_value_type"
    UPSTREAM_UNKNOWN = "upstream_unknown"
    UPSTREAM_DEFERRED = "upstream_deferred"
    UPSTREAM_BLOCKED = "upstream_blocked"
    AGGREGATE_OR_GROUPED_DEFERRED = "aggregate_grouped_deferred"
    MISSING_INPUT_FIELD = "missing_input_field"
    UNAVAILABLE_PROJECT_TYPE = "unavailable_project_type"


class ProjectExpressionSchemaOriginKind(StrEnum):
    """Private origin category for one row expression schema result."""

    SOURCE_FIELD = "source_field"
    DIRECT_PROJECTION = "direct_projection"
    RENAMED_PROJECTION = "renamed_projection"
    DERIVED_EXPRESSION = "derived_expression"
    LET_DERIVED = "let_derived"
    AGGREGATE = "aggregate"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProjectExpressionSchemaResult:
    """Private adapter result for one project row expression output."""

    status: ProjectExpressionSchemaStatus
    reason: ProjectExpressionSchemaReason
    output_name: str
    origin: ProjectExpressionSchemaOriginKind
    resolved_type: ProjectResolvedType | None = None
    nullability: ProjectRowFieldNullability | None = None
    field_def: FieldDef | None = None
    location: SourceLocation | None = None
    dependency_placeholders: tuple[Expression, ...] = ()
    lineage_placeholders: tuple[Expression, ...] = ()

    def __post_init__(self) -> None:
        """Normalize inert placeholder tuples and enforce concrete invariants."""

        object.__setattr__(
            self,
            "dependency_placeholders",
            tuple(self.dependency_placeholders),
        )
        object.__setattr__(
            self,
            "lineage_placeholders",
            tuple(self.lineage_placeholders),
        )
        if self.status is ProjectExpressionSchemaStatus.CONCRETE:
            if self.resolved_type is None or self.nullability is None:
                raise ValueError("Concrete expression schema requires type facts")
            return
        if self.field_def is not None:
            raise ValueError("Non-concrete expression schema cannot carry field_def")


def adapt_project_row_expression_schema(
    *,
    expression: Expression,
    output_name: str,
    input_schema: ProjectRowSchema | None,
    upstream_state: ProjectRelationRowSchemaState | None,
    relation_qualifier: str | None,
    expression_value_types: Mapping[Expression, ValueType],
    let_value_types: Mapping[str, ValueType] | None = None,
    project_type_symbols: Mapping[str, ProjectSymbol] | None = None,
    fallback_path: str | None = None,
) -> ProjectExpressionSchemaResult:
    """Adapt supplied row-level type facts into one private project result."""

    location = _expression_location(expression, fallback_path=fallback_path)
    upstream_result = _upstream_non_concrete_result(
        upstream_state,
        output_name=output_name,
        location=location,
    )
    if upstream_result is not None:
        return upstream_result

    effective_input_schema = _effective_input_schema(
        input_schema,
        upstream_state=upstream_state,
    )
    direct_result = _direct_projection_result(
        expression,
        output_name=output_name,
        input_schema=effective_input_schema,
        relation_qualifier=relation_qualifier,
        location=location,
    )
    if direct_result is not None:
        return direct_result

    let_result = _let_reference_result(
        expression,
        output_name=output_name,
        let_value_types=let_value_types,
        project_type_symbols=project_type_symbols,
        location=location,
    )
    if let_result is not None:
        return let_result

    if _contains_semantic_aggregate(expression):
        return _non_concrete_result(
            status=ProjectExpressionSchemaStatus.DEFERRED,
            reason=ProjectExpressionSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED,
            output_name=output_name,
            origin=ProjectExpressionSchemaOriginKind.AGGREGATE,
            location=location,
        )

    if _is_direct_projection_shape(expression):
        return _non_concrete_result(
            status=ProjectExpressionSchemaStatus.UNKNOWN,
            reason=ProjectExpressionSchemaReason.MISSING_INPUT_FIELD,
            output_name=output_name,
            origin=ProjectExpressionSchemaOriginKind.UNKNOWN,
            location=location,
        )

    value_type = expression_value_types.get(expression)
    return _value_type_result(
        value_type,
        output_name=output_name,
        success_reason=ProjectExpressionSchemaReason.KNOWN_EXPRESSION_VALUE,
        origin=ProjectExpressionSchemaOriginKind.DERIVED_EXPRESSION,
        project_type_symbols=project_type_symbols,
        location=location,
    )


def _upstream_non_concrete_result(
    upstream_state: ProjectRelationRowSchemaState | None,
    *,
    output_name: str,
    location: SourceLocation,
) -> ProjectExpressionSchemaResult | None:
    if upstream_state is None:
        return None
    if upstream_state.status is ProjectRelationRowSchemaStatus.CONCRETE:
        return None
    if upstream_state.status is ProjectRelationRowSchemaStatus.UNKNOWN:
        return _non_concrete_result(
            status=ProjectExpressionSchemaStatus.UNKNOWN,
            reason=ProjectExpressionSchemaReason.UPSTREAM_UNKNOWN,
            output_name=output_name,
            origin=ProjectExpressionSchemaOriginKind.UNKNOWN,
            location=location,
        )
    if upstream_state.status is ProjectRelationRowSchemaStatus.DEFERRED:
        return _non_concrete_result(
            status=ProjectExpressionSchemaStatus.DEFERRED,
            reason=ProjectExpressionSchemaReason.UPSTREAM_DEFERRED,
            output_name=output_name,
            origin=ProjectExpressionSchemaOriginKind.UNKNOWN,
            location=location,
        )
    return _non_concrete_result(
        status=ProjectExpressionSchemaStatus.BLOCKED,
        reason=ProjectExpressionSchemaReason.UPSTREAM_BLOCKED,
        output_name=output_name,
        origin=ProjectExpressionSchemaOriginKind.UNKNOWN,
        location=location,
    )


def _effective_input_schema(
    input_schema: ProjectRowSchema | None,
    *,
    upstream_state: ProjectRelationRowSchemaState | None,
) -> ProjectRowSchema | None:
    if input_schema is not None:
        return input_schema
    if (
        upstream_state is not None
        and upstream_state.status is ProjectRelationRowSchemaStatus.CONCRETE
    ):
        return upstream_state.schema
    return None


def _direct_projection_result(
    expression: Expression,
    *,
    output_name: str,
    input_schema: ProjectRowSchema | None,
    relation_qualifier: str | None,
    location: SourceLocation,
) -> ProjectExpressionSchemaResult | None:
    lookup_name = _direct_lookup_name(expression, relation_qualifier=relation_qualifier)
    if lookup_name is None or input_schema is None or input_schema.is_unknown:
        return None

    input_field = input_schema.fields.get(lookup_name)
    if input_field is None:
        return None

    renamed = output_name != input_field.name
    return ProjectExpressionSchemaResult(
        status=ProjectExpressionSchemaStatus.CONCRETE,
        reason=(
            ProjectExpressionSchemaReason.RENAMED_PROJECTION
            if renamed
            else ProjectExpressionSchemaReason.DIRECT_FIELD
        ),
        output_name=output_name,
        origin=(
            ProjectExpressionSchemaOriginKind.RENAMED_PROJECTION
            if renamed
            else ProjectExpressionSchemaOriginKind.DIRECT_PROJECTION
        ),
        resolved_type=input_field.resolved_type,
        nullability=input_field.nullability,
        field_def=input_field.field_def,
        location=location,
        dependency_placeholders=(expression,),
        lineage_placeholders=(expression,),
    )


def _direct_lookup_name(
    expression: Expression,
    *,
    relation_qualifier: str | None,
) -> str | None:
    if isinstance(expression, NameExpr):
        return expression.name
    if (
        isinstance(expression, DottedNameExpr)
        and relation_qualifier is not None
        and len(expression.parts) == 2
        and expression.parts[0] == relation_qualifier
    ):
        return expression.parts[1]
    return None


def _is_direct_projection_shape(expression: Expression) -> bool:
    return isinstance(expression, (NameExpr, DottedNameExpr))


def _let_reference_result(
    expression: Expression,
    *,
    output_name: str,
    let_value_types: Mapping[str, ValueType] | None,
    project_type_symbols: Mapping[str, ProjectSymbol] | None,
    location: SourceLocation,
) -> ProjectExpressionSchemaResult | None:
    if not isinstance(expression, NameExpr) or let_value_types is None:
        return None
    value_type = let_value_types.get(expression.name)
    if value_type is None:
        return None
    return _value_type_result(
        value_type,
        output_name=output_name,
        success_reason=ProjectExpressionSchemaReason.KNOWN_LET_VALUE,
        origin=ProjectExpressionSchemaOriginKind.LET_DERIVED,
        project_type_symbols=project_type_symbols,
        location=location,
        dependency_placeholders=(expression,),
        lineage_placeholders=(expression,),
    )


def _value_type_result(
    value_type: ValueType | None,
    *,
    output_name: str,
    success_reason: ProjectExpressionSchemaReason,
    origin: ProjectExpressionSchemaOriginKind,
    project_type_symbols: Mapping[str, ProjectSymbol] | None,
    location: SourceLocation,
    dependency_placeholders: tuple[Expression, ...] = (),
    lineage_placeholders: tuple[Expression, ...] = (),
) -> ProjectExpressionSchemaResult:
    if value_type is None:
        return _non_concrete_result(
            status=ProjectExpressionSchemaStatus.UNKNOWN,
            reason=ProjectExpressionSchemaReason.MISSING_VALUE_TYPE,
            output_name=output_name,
            origin=ProjectExpressionSchemaOriginKind.UNKNOWN,
            location=location,
        )
    if value_type.kind is ValueTypeKind.UNKNOWN:
        return _non_concrete_result(
            status=ProjectExpressionSchemaStatus.UNKNOWN,
            reason=ProjectExpressionSchemaReason.UNKNOWN_VALUE_TYPE,
            output_name=output_name,
            origin=ProjectExpressionSchemaOriginKind.UNKNOWN,
            location=location,
        )

    converted_type = _project_resolved_type(
        value_type,
        project_type_symbols=project_type_symbols,
    )
    converted_nullability = _project_nullability(value_type.nullability)
    if converted_type is None:
        return _non_concrete_result(
            status=ProjectExpressionSchemaStatus.UNKNOWN,
            reason=ProjectExpressionSchemaReason.UNAVAILABLE_PROJECT_TYPE,
            output_name=output_name,
            origin=ProjectExpressionSchemaOriginKind.UNKNOWN,
            location=location,
        )

    return ProjectExpressionSchemaResult(
        status=ProjectExpressionSchemaStatus.CONCRETE,
        reason=success_reason,
        output_name=output_name,
        origin=origin,
        resolved_type=converted_type,
        nullability=converted_nullability,
        field_def=None,
        location=location,
        dependency_placeholders=dependency_placeholders,
        lineage_placeholders=lineage_placeholders,
    )


def _project_resolved_type(
    value_type: ValueType,
    *,
    project_type_symbols: Mapping[str, ProjectSymbol] | None,
) -> ProjectResolvedType | None:
    resolved_type = value_type.resolved_type
    if (
        resolved_type.kind is TypeKind.BUILTIN
        and resolved_type.name in _PROJECT_BUILTIN_TYPE_NAMES
    ):
        return ProjectResolvedType(
            name=resolved_type.name,
            kind=ProjectResolvedTypeKind.BUILTIN,
        )

    if project_type_symbols is None:
        return None

    symbol = project_type_symbols.get(resolved_type.name)
    if symbol is None:
        return None
    kind = _project_type_kind(resolved_type.kind, symbol.kind)
    if kind is None:
        return None
    return ProjectResolvedType(
        name=resolved_type.name,
        kind=kind,
        symbol=symbol,
    )


def _project_type_kind(
    semantic_kind: TypeKind,
    symbol_kind: ProjectSymbolKind,
) -> ProjectResolvedTypeKind | None:
    if (
        semantic_kind is TypeKind.TYPE_ALIAS
        and symbol_kind is ProjectSymbolKind.TYPE_ALIAS
    ):
        return ProjectResolvedTypeKind.TYPE_ALIAS
    if semantic_kind is TypeKind.ENUM and symbol_kind is ProjectSymbolKind.ENUM:
        return ProjectResolvedTypeKind.ENUM
    if semantic_kind is TypeKind.SHAPE and symbol_kind is ProjectSymbolKind.SHAPE:
        return ProjectResolvedTypeKind.SHAPE
    return None


def _project_nullability(
    nullability: EffectiveNullability,
) -> ProjectRowFieldNullability:
    if nullability is EffectiveNullability.NON_NULL:
        return ProjectRowFieldNullability.NON_NULL
    if nullability is EffectiveNullability.NULLABLE:
        return ProjectRowFieldNullability.NULLABLE
    return ProjectRowFieldNullability.UNKNOWN


def _non_concrete_result(
    *,
    status: ProjectExpressionSchemaStatus,
    reason: ProjectExpressionSchemaReason,
    output_name: str,
    origin: ProjectExpressionSchemaOriginKind,
    location: SourceLocation,
) -> ProjectExpressionSchemaResult:
    return ProjectExpressionSchemaResult(
        status=status,
        reason=reason,
        output_name=output_name,
        origin=origin,
        location=location,
    )


def _contains_semantic_aggregate(expression: Expression) -> bool:
    if (
        isinstance(expression, CallExpr)
        and isinstance(expression.callee, NameExpr)
        and expression.callee.name in _SEMANTIC_AGGREGATE_NAMES
    ):
        return True
    return any(
        _contains_semantic_aggregate(child) for child in _child_expressions(expression)
    )


def _child_expressions(expression: Expression) -> tuple[Expression, ...]:
    if isinstance(expression, CallExpr):
        return (expression.callee, *expression.arguments)
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, BinaryExpr):
        return (expression.left, expression.right)
    if isinstance(expression, ComparisonExpr):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    return ()


def _expression_location(
    expression: Expression,
    *,
    fallback_path: str | None,
) -> SourceLocation:
    span = expression.span
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )
