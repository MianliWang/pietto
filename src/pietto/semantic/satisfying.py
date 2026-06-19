"""Semantic validation for Phase 25 ``satisfying:`` result predicates."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping

from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    FromClause,
    GroupByItem,
    LiteralExpr,
    NameExpr,
    Node,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    contains_semantic_aggregate,
    invalid_context_diagnostic,
    is_semantic_aggregate_call,
)
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
    SatisfyingResultPredicateInfo,
)

DerivedRelation = TableDef | QueryDef
RelationDefinition = SourceDef | TableDef | QueryDef

_UNKNOWN_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)

_BOOL_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Bool", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.UNKNOWN,
)

_ALLOWED_COMPARISON_OPERATORS = frozenset({"==", "!=", "<", "<=", ">", ">="})


@dataclass(frozen=True, slots=True)
class _SatisfyingOutput:
    field: RowField | None
    supported: bool
    expression: Expression


def check_satisfying_clauses(
    script: Script,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> tuple[dict[DerivedRelation, SatisfyingResultPredicateInfo], list[Diagnostic]]:
    """Validate parsed satisfying clauses and collect lowering facts."""

    result_predicates: dict[DerivedRelation, SatisfyingResultPredicateInfo] = {}
    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        if definition.satisfying_clause is None:
            continue

        expression = definition.satisfying_clause.expression
        if contains_semantic_aggregate(expression):
            diagnostics.append(
                invalid_context_diagnostic(
                    expression,
                    context="satisfying clause",
                )
            )
            continue

        if definition.group_by_clause is None:
            diagnostics.append(_no_group_diagnostic(definition))
            continue

        input_schema = _input_schema(
            definition,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
        )
        output_scope = _satisfying_output_scope(
            definition,
            input_schema=input_schema,
            relation_row_schemas=relation_row_schemas,
        )
        relation_diagnostics: list[Diagnostic] = []
        expression_value_types: dict[Expression, ValueType] = {}
        value_type = _infer_predicate(
            expression,
            output_scope,
            input_schema=input_schema,
            diagnostics=relation_diagnostics,
            value_types=expression_value_types,
        )
        if relation_diagnostics:
            diagnostics.extend(relation_diagnostics)
            continue

        bool_diagnostic = _bool_predicate_diagnostic(expression, value_type)
        if bool_diagnostic is not None:
            diagnostics.append(bool_diagnostic)
            continue
        if value_type.kind is ValueTypeKind.UNKNOWN:
            continue

        assert definition.satisfying_clause is not None
        result_predicates[definition] = SatisfyingResultPredicateInfo(
            clause=definition.satisfying_clause,
            output_expressions={
                name: output.expression
                for name, output in output_scope.items()
                if output.supported
            },
            expression_value_types=expression_value_types,
        )

    return result_predicates, diagnostics


def _input_schema(
    definition: DerivedRelation,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> RowSchema:
    target = from_resolutions.get(definition.from_clause)
    if isinstance(target, SourceDef):
        return source_row_schemas[target]
    if isinstance(target, (TableDef, QueryDef)):
        return relation_row_schemas[target]
    return RowSchema(is_unknown=True)


def _satisfying_output_scope(
    definition: DerivedRelation,
    *,
    input_schema: RowSchema,
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> dict[str, _SatisfyingOutput]:
    group_key_identities = {
        identity
        for item in _group_by_items(definition)
        if (identity := _field_identity(definition, item.key, input_schema)) is not None
    }
    schema = relation_row_schemas.get(definition, RowSchema(is_unknown=True))
    scope: dict[str, _SatisfyingOutput] = {}
    for item in definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is None or output_name in scope:
            continue
        supported = _is_group_key_projection(
            definition,
            item,
            input_schema=input_schema,
            group_key_identities=group_key_identities,
        ) or _is_direct_aggregate_projection(item)
        scope[output_name] = _SatisfyingOutput(
            field=schema.fields.get(output_name),
            supported=supported,
            expression=item.expression,
        )
    return scope


def _group_by_items(definition: DerivedRelation) -> tuple[GroupByItem, ...]:
    if definition.group_by_clause is None:
        return ()
    return definition.group_by_clause.items


def _projection_output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _is_group_key_projection(
    definition: DerivedRelation,
    item: SelectItem,
    *,
    input_schema: RowSchema,
    group_key_identities: set[str],
) -> bool:
    identity = _field_identity(definition, item.expression, input_schema)
    return identity is not None and identity in group_key_identities


def _field_identity(
    definition: DerivedRelation,
    expression: Expression,
    input_schema: RowSchema,
) -> str | None:
    if input_schema.is_unknown:
        return None
    if isinstance(expression, NameExpr):
        field = input_schema.fields.get(expression.name)
        return None if field is None else field.name
    if isinstance(expression, DottedNameExpr):
        if (
            len(expression.parts) != 2
            or expression.parts[0] != definition.from_clause.source_name
        ):
            return None
        field = input_schema.fields.get(expression.parts[1])
        return None if field is None else field.name
    return None


def _is_direct_aggregate_projection(item: SelectItem) -> bool:
    return (
        item.alias is not None
        and isinstance(item.expression, CallExpr)
        and is_semantic_aggregate_call(item.expression)
    )


def _infer_predicate(
    expression: Expression,
    output_scope: Mapping[str, _SatisfyingOutput],
    *,
    input_schema: RowSchema,
    diagnostics: list[Diagnostic],
    value_types: dict[Expression, ValueType],
) -> ValueType:
    if isinstance(expression, (NameExpr, LiteralExpr)):
        value_type = _infer_value(
            expression,
            output_scope,
            input_schema=input_schema,
            diagnostics=diagnostics,
            value_types=value_types,
        )
        value_types[expression] = value_type
        return value_type

    if isinstance(expression, ComparisonExpr):
        if expression.operator not in _ALLOWED_COMPARISON_OPERATORS:
            diagnostics.append(
                _unsupported_expression_diagnostic(
                    expression,
                    form=f"comparison operator `{expression.operator}`",
                )
            )
            value_types[expression] = _UNKNOWN_VALUE_TYPE
            return _UNKNOWN_VALUE_TYPE
        left_type = _infer_value(
            expression.left,
            output_scope,
            input_schema=input_schema,
            diagnostics=diagnostics,
            value_types=value_types,
        )
        right_type = _infer_value(
            expression.right,
            output_scope,
            input_schema=input_schema,
            diagnostics=diagnostics,
            value_types=value_types,
        )
        if (
            left_type.kind is ValueTypeKind.UNKNOWN
            or right_type.kind is ValueTypeKind.UNKNOWN
        ):
            value_types[expression] = _UNKNOWN_VALUE_TYPE
            return _UNKNOWN_VALUE_TYPE
        value_types[expression] = _BOOL_VALUE_TYPE
        return _BOOL_VALUE_TYPE

    if isinstance(expression, BinaryExpr) and expression.operator in {"and", "or"}:
        left_type = _infer_predicate(
            expression.left,
            output_scope,
            input_schema=input_schema,
            diagnostics=diagnostics,
            value_types=value_types,
        )
        right_type = _infer_predicate(
            expression.right,
            output_scope,
            input_schema=input_schema,
            diagnostics=diagnostics,
            value_types=value_types,
        )
        if (
            left_type.kind is ValueTypeKind.UNKNOWN
            or right_type.kind is ValueTypeKind.UNKNOWN
        ):
            value_types[expression] = _UNKNOWN_VALUE_TYPE
            return _UNKNOWN_VALUE_TYPE
        if _is_bool(left_type) and _is_bool(right_type):
            value_types[expression] = _BOOL_VALUE_TYPE
            return _BOOL_VALUE_TYPE
        diagnostics.append(_invalid_bool_operands_diagnostic(expression))
        value_types[expression] = _UNKNOWN_VALUE_TYPE
        return _UNKNOWN_VALUE_TYPE

    diagnostics.append(_unsupported_expression_diagnostic(expression))
    value_types[expression] = _UNKNOWN_VALUE_TYPE
    return _UNKNOWN_VALUE_TYPE


def _infer_value(
    expression: Expression,
    output_scope: Mapping[str, _SatisfyingOutput],
    *,
    input_schema: RowSchema,
    diagnostics: list[Diagnostic],
    value_types: dict[Expression, ValueType],
) -> ValueType:
    if isinstance(expression, LiteralExpr):
        value_type = _literal_value_type(expression)
        value_types[expression] = value_type
        return value_type
    if isinstance(expression, NameExpr):
        value_type = _name_value_type(
            expression,
            output_scope,
            input_schema=input_schema,
            diagnostics=diagnostics,
        )
        value_types[expression] = value_type
        return value_type
    diagnostics.append(_unsupported_expression_diagnostic(expression))
    value_types[expression] = _UNKNOWN_VALUE_TYPE
    return _UNKNOWN_VALUE_TYPE


def _literal_value_type(expression: LiteralExpr) -> ValueType:
    value = expression.value
    if isinstance(value, bool):
        return _builtin_value_type("Bool", EffectiveNullability.NON_NULL)
    if isinstance(value, str):
        return _builtin_value_type("Text", EffectiveNullability.NON_NULL)
    if isinstance(value, int):
        return _builtin_value_type("Int", EffectiveNullability.NON_NULL)
    if isinstance(value, float):
        return _builtin_value_type("Float", EffectiveNullability.NON_NULL)
    return _UNKNOWN_VALUE_TYPE


def _name_value_type(
    expression: NameExpr,
    output_scope: Mapping[str, _SatisfyingOutput],
    *,
    input_schema: RowSchema,
    diagnostics: list[Diagnostic],
) -> ValueType:
    scoped = output_scope.get(expression.name)
    if scoped is None:
        if _is_input_field(expression.name, input_schema):
            diagnostics.append(_input_field_reference_diagnostic(expression))
        else:
            diagnostics.append(_unknown_output_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE

    if not scoped.supported:
        diagnostics.append(_unsupported_output_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE
    field = scoped.field
    if field is None or field.resolved_type.kind is TypeKind.UNKNOWN:
        return _UNKNOWN_VALUE_TYPE
    return ValueType(
        resolved_type=field.resolved_type,
        nullability=field.nullability,
    )


def _is_input_field(name: str, input_schema: RowSchema) -> bool:
    return not input_schema.is_unknown and name in input_schema.fields


def _builtin_value_type(
    name: str,
    nullability: EffectiveNullability,
) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.BUILTIN),
        nullability=nullability,
    )


def _is_bool(value_type: ValueType) -> bool:
    return (
        value_type.resolved_type.kind is TypeKind.BUILTIN
        and value_type.resolved_type.name == "Bool"
    )


def _no_group_diagnostic(definition: DerivedRelation) -> Diagnostic:
    assert definition.satisfying_clause is not None
    return _diagnostic(
        definition.satisfying_clause,
        code="PIE-S2323",
        message="`satisfying` requires GROUP BY in the Phase 25 MVP",
    )


def _unknown_output_diagnostic(expression: NameExpr) -> Diagnostic:
    return _diagnostic(
        expression,
        code="PIE-S2324",
        message=f"Unknown select output in satisfying: {expression.name}",
    )


def _input_field_reference_diagnostic(expression: NameExpr) -> Diagnostic:
    return _diagnostic(
        expression,
        code="PIE-S2325",
        message=(
            "Satisfying reference must use select output name, "
            f"not input field: {expression.name}"
        ),
    )


def _unsupported_output_diagnostic(expression: NameExpr) -> Diagnostic:
    return _diagnostic(
        expression,
        code="PIE-S2326",
        message=(
            "Satisfying output is not a group-key or direct aggregate "
            f"projection: {expression.name}"
        ),
    )


def _unsupported_expression_diagnostic(
    expression: Expression,
    *,
    form: str | None = None,
) -> Diagnostic:
    label = form or type(expression).__name__
    return _diagnostic(
        expression,
        code="PIE-S2327",
        message=f"Unsupported satisfying expression form: {label} is deferred",
    )


def _bool_predicate_diagnostic(
    expression: Expression,
    value_type: ValueType,
) -> Diagnostic | None:
    if value_type.kind is ValueTypeKind.UNKNOWN or _is_bool(value_type):
        return None
    return _diagnostic(
        expression,
        code="PIE-S2202",
        message="Expected Bool expression in satisfying clause",
    )


def _invalid_bool_operands_diagnostic(expression: BinaryExpr) -> Diagnostic:
    return _diagnostic(
        expression,
        code="PIE-S2105",
        message=f"Invalid operands for operator {expression.operator}: expected Bool operands",
    )


def _diagnostic(
    node: Node,
    *,
    code: str,
    message: str,
) -> Diagnostic:
    span = node.span
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
