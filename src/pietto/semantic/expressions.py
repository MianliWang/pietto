"""Minimal expression value typing for supported field environments."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    CallExpr,
    CheckDef,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    FromClause,
    IndexDef,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.catalog import BUILTIN_FUNCTIONS, BuiltinFunction
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef

_UNKNOWN_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)


def type_shape_predicates(
    script: Script,
    *,
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type shape check bodies and index predicates against shape fields."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if not isinstance(definition, ShapeDef):
            continue
        row_schema = _shape_row_schema(
            definition,
            type_resolutions=type_resolutions,
            type_nullability=type_nullability,
        )
        for item in definition.items:
            if isinstance(item, CheckDef):
                expression = item.expression
            elif isinstance(item, IndexDef) and item.predicate is not None:
                expression = item.predicate
            else:
                continue
            _infer(
                expression,
                row_schema,
                value_types,
                diagnostics,
                report_unknown_name=True,
            )

    return value_types, diagnostics


def type_relation_expressions(
    script: Script,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type supported table/query expressions without validating consumers."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        input_schema = _input_schema(
            definition,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
        )
        if definition.where_clause is not None:
            _infer(
                definition.where_clause.expression,
                input_schema,
                value_types,
                diagnostics,
                report_unknown_name=True,
            )
        for item in definition.select_items:
            _infer(
                item.expression,
                input_schema,
                value_types,
                diagnostics,
                # Bare projection diagnostics are owned by schema propagation.
                report_unknown_name=not isinstance(item.expression, NameExpr),
            )

    return value_types, diagnostics


def _shape_row_schema(
    shape: ShapeDef,
    *,
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> RowSchema:
    """Build the local field environment used by shape predicates."""

    fields: dict[str, RowField] = {}
    for field in shape.fields:
        if field.name in fields:
            continue
        fields[field.name] = RowField(
            name=field.name,
            resolved_type=type_resolutions[field.type_expr],
            nullability=type_nullability[field.type_expr],
            definition=field,
        )
    return RowSchema(fields=fields)


def _input_schema(
    definition: DerivedRelation,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> RowSchema:
    """Return a relation's resolved input schema or an Unknown schema."""

    target = from_resolutions.get(definition.from_clause)
    if isinstance(target, SourceDef):
        return source_row_schemas[target]
    if isinstance(target, (TableDef, QueryDef)):
        return relation_row_schemas[target]
    return RowSchema(is_unknown=True)


def _infer(
    expression: Expression,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
) -> ValueType:
    """Infer only the expression forms supported by this scaffold."""

    existing = value_types.get(expression)
    if existing is not None:
        return existing

    if isinstance(expression, LiteralExpr):
        value_type = _literal_value_type(expression)
    elif isinstance(expression, NameExpr):
        value_type = _name_value_type(
            expression,
            row_schema,
            diagnostics,
            report_unknown=report_unknown_name,
        )
    elif isinstance(expression, CallExpr):
        value_type = _call_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
        )
    elif isinstance(expression, IsNullExpr):
        _infer(
            expression.value,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
        )
        value_type = _builtin_value_type(
            "Bool",
            EffectiveNullability.NON_NULL,
        )
    elif isinstance(expression, ComparisonExpr):
        _infer(
            expression.left,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
        )
        _infer(
            expression.right,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
        )
        value_type = _builtin_value_type(
            "Bool",
            EffectiveNullability.UNKNOWN,
        )
    else:
        # Unsupported forms remain opaque so calls and arithmetic are not
        # accidentally checked through their child expressions.
        value_type = _UNKNOWN_VALUE_TYPE

    value_types[expression] = value_type
    return value_type


def _call_value_type(
    expression: CallExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
) -> ValueType:
    """Type one exact built-in call while suppressing Unknown cascades."""

    argument_types = tuple(
        _infer(
            argument,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
        )
        for argument in expression.arguments
    )
    if any(
        argument_type.kind is ValueTypeKind.UNKNOWN for argument_type in argument_types
    ):
        return _UNKNOWN_VALUE_TYPE

    function_name = _callee_name(expression)
    signature = BUILTIN_FUNCTIONS.get(function_name)
    if signature is None:
        diagnostics.append(_unknown_function_diagnostic(expression, function_name))
        return _UNKNOWN_VALUE_TYPE

    if len(argument_types) != len(signature.parameter_types):
        diagnostics.append(_wrong_arity_diagnostic(expression, signature))
        return _UNKNOWN_VALUE_TYPE

    for position, (argument_type, expected_name) in enumerate(
        zip(argument_types, signature.parameter_types, strict=True),
        start=1,
    ):
        if (
            argument_type.resolved_type.kind is not TypeKind.BUILTIN
            or argument_type.resolved_type.name != expected_name
        ):
            diagnostics.append(
                _wrong_argument_type_diagnostic(
                    expression,
                    signature,
                    position=position,
                    expected_name=expected_name,
                    actual_name=argument_type.resolved_type.name,
                )
            )
            return _UNKNOWN_VALUE_TYPE

    return _builtin_value_type(
        signature.return_type,
        EffectiveNullability.UNKNOWN,
    )


def _callee_name(expression: CallExpr) -> str:
    """Return a source-level name for a simple or dotted call target."""

    if isinstance(expression.callee, NameExpr):
        return expression.callee.name
    assert isinstance(expression.callee, DottedNameExpr)
    return ".".join(expression.callee.parts)


def _literal_value_type(expression: LiteralExpr) -> ValueType:
    """Map supported scalar literals to portable built-in types."""

    value = expression.value
    if isinstance(value, bool):
        name = "Bool"
    elif isinstance(value, str):
        name = "Text"
    elif isinstance(value, int):
        name = "Int"
    elif isinstance(value, float):
        name = "Float"
    else:
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type(name, EffectiveNullability.NON_NULL)


def _name_value_type(
    expression: NameExpr,
    row_schema: RowSchema,
    diagnostics: list[Diagnostic],
    *,
    report_unknown: bool,
) -> ValueType:
    """Resolve a bare field name against a known row schema."""

    if row_schema.is_unknown:
        return _UNKNOWN_VALUE_TYPE
    field = row_schema.fields.get(expression.name)
    if field is None:
        if report_unknown:
            diagnostics.append(_unknown_field_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE
    if field.resolved_type.kind is TypeKind.UNKNOWN:
        return _UNKNOWN_VALUE_TYPE
    return ValueType(
        resolved_type=field.resolved_type,
        nullability=field.nullability,
    )


def _builtin_value_type(
    name: str,
    nullability: EffectiveNullability,
) -> ValueType:
    """Create a known value type for one portable built-in."""

    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.BUILTIN),
        nullability=nullability,
    )


def _unknown_field_diagnostic(expression: NameExpr) -> Diagnostic:
    """Report an unknown field reference at its expression span."""

    span = expression.span
    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=f"Unknown field: {expression.name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _unknown_function_diagnostic(
    expression: CallExpr,
    function_name: str,
) -> Diagnostic:
    """Report a call target absent from the explicit built-in catalog."""

    return _call_diagnostic(
        expression,
        code="PIE-S2103",
        message=f"Unknown function: {function_name}",
    )


def _wrong_arity_diagnostic(
    expression: CallExpr,
    signature: BuiltinFunction,
) -> Diagnostic:
    """Report a built-in call with the wrong argument count."""

    return _call_diagnostic(
        expression,
        code="PIE-S2104",
        message=(
            f"Invalid arguments for function {signature.name}: expected "
            f"{len(signature.parameter_types)}, got {len(expression.arguments)}"
        ),
    )


def _wrong_argument_type_diagnostic(
    expression: CallExpr,
    signature: BuiltinFunction,
    *,
    position: int,
    expected_name: str,
    actual_name: str,
) -> Diagnostic:
    """Report the first incompatible known argument in a built-in call."""

    return _call_diagnostic(
        expression,
        code="PIE-S2104",
        message=(
            f"Invalid argument type for function {signature.name} at position "
            f"{position}: expected {expected_name}, got {actual_name}"
        ),
    )


def _call_diagnostic(
    expression: CallExpr,
    *,
    code: str,
    message: str,
) -> Diagnostic:
    """Create a call diagnostic at the complete call-expression span."""

    span = expression.span
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
