"""Minimal expression value typing for supported field environments."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    CheckDef,
    ComparisonExpr,
    ConstraintDef,
    DeriveDef,
    DottedNameExpr,
    Expression,
    FromClause,
    IndexDef,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    QueryDef,
    Script,
    SelectItem,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeExpr,
    UnaryExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    aggregate_argument_can_use_let_scope,
    contains_semantic_aggregate,
    has_unknown_field_reference,
    invalid_context_diagnostic,
    is_semantic_aggregate_call,
    is_supported_semantic_aggregate_argument_expression,
    semantic_aggregate_call_name,
    semantic_projection_aggregate_result_value_type,
)
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


def type_callable_bodies(
    script: Script,
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type top-level callable bodies against their parameter environments."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if not isinstance(definition, (ConstraintDef, DeriveDef)):
            continue
        row_schema = _callable_row_schema(
            definition,
            type_expansions=type_expansions,
            type_nullability=type_nullability,
        )
        _append_invalid_count_context_diagnostic(
            definition.body,
            diagnostics,
            context=(
                "constraint body"
                if isinstance(definition, ConstraintDef)
                else "derive body"
            ),
        )
        _infer(
            definition.body,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=True,
        )

    return value_types, diagnostics


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
                context = "shape check"
            elif isinstance(item, IndexDef) and item.predicate is not None:
                expression = item.predicate
                context = "index predicate"
            else:
                continue
            _append_invalid_count_context_diagnostic(
                expression,
                diagnostics,
                context=context,
            )
            _infer(
                expression,
                row_schema,
                value_types,
                diagnostics,
                report_unknown_name=True,
            )

    return value_types, diagnostics


def type_shape_field_derives(
    script: Script,
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type field derive expressions against all fields in their shape."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if not isinstance(definition, ShapeDef):
            continue
        row_schema = _shape_row_schema(
            definition,
            type_resolutions=type_expansions,
            type_nullability=type_nullability,
        )
        for field in definition.fields:
            if field.derive_expression is None:
                continue
            _append_invalid_count_context_diagnostic(
                field.derive_expression,
                diagnostics,
                context="field derive body",
            )
            _infer(
                field.derive_expression,
                row_schema,
                value_types,
                diagnostics,
                report_unknown_name=True,
            )

    return value_types, diagnostics


def type_source_connector_arguments(
    script: Script,
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type source connector arguments without typing the connector call."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    empty_environment = RowSchema()

    for definition in script.definitions:
        if not isinstance(definition, SourceDef):
            continue
        connector = definition.connector
        if not isinstance(connector, CallExpr):
            continue
        for argument in connector.arguments:
            _append_invalid_count_context_diagnostic(
                argument,
                diagnostics,
                context="source connector argument",
            )
            _infer(
                argument,
                empty_environment,
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
    relation_let_value_types: Mapping[DerivedRelation, Mapping[str, ValueType]]
    | None = None,
    relation_let_expressions: Mapping[DerivedRelation, Mapping[str, Expression]]
    | None = None,
) -> tuple[dict[Expression, ValueType], list[Diagnostic]]:
    """Type supported table/query expressions without validating consumers."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    relation_let_value_types = relation_let_value_types or {}
    relation_let_expressions = (
        relation_let_expressions
        if relation_let_expressions is not None
        else _relation_let_expressions(script, relation_let_value_types)
    )

    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        input_schema = _input_schema(
            definition,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
        )
        let_value_types = relation_let_value_types.get(definition)
        let_expressions = relation_let_expressions.get(definition)
        if definition.where_clause is not None:
            _append_invalid_count_context_diagnostic(
                definition.where_clause.expression,
                diagnostics,
                context="where clause",
            )
            _infer(
                definition.where_clause.expression,
                input_schema,
                value_types,
                diagnostics,
                report_unknown_name=True,
                field_qualifier=definition.from_clause.source_name,
                bare_value_types=let_value_types,
            )
        for selected_output_ordinal, item in enumerate(definition.select_items):
            if type(item.expression) is WindowExpr:
                from pietto.semantic.window_analysis import (
                    analyze_window_expression,
                )

                analyze_window_expression(
                    definition=definition,
                    item=item,
                    selected_output_ordinal=selected_output_ordinal,
                    source_id=item.expression.span.path or definition.name,
                    input_schema=input_schema,
                    field_qualifier=definition.from_clause.source_name,
                    value_types=value_types,
                    diagnostics=diagnostics,
                    let_value_types=let_value_types or {},
                    let_expressions=let_expressions or {},
                )
                continue
            select_let_value_types = (
                let_value_types
                if (
                    definition.group_by_clause is None
                    and not contains_semantic_aggregate(item.expression)
                )
                or _is_direct_aggregate_projection(item)
                else None
            )
            _infer(
                item.expression,
                input_schema,
                value_types,
                diagnostics,
                # Bare projection diagnostics are owned by schema propagation.
                report_unknown_name=not isinstance(item.expression, NameExpr),
                field_qualifier=definition.from_clause.source_name,
                allow_aggregate_projection=_is_direct_aggregate_projection(item),
                bare_value_types=select_let_value_types,
                bare_value_expressions=let_expressions,
            )
        if (
            definition.order_by_clause is not None
            and definition.group_by_clause is None
        ):
            for item in definition.order_by_clause.items:
                _append_invalid_count_context_diagnostic(
                    item.expression,
                    diagnostics,
                    context="order by",
                )
                _infer(
                    item.expression,
                    input_schema,
                    value_types,
                    diagnostics,
                    report_unknown_name=True,
                    field_qualifier=definition.from_clause.source_name,
                    bare_value_types=let_value_types,
                    bare_value_expressions=let_expressions,
                )

    return value_types, diagnostics


def infer_row_expression(
    expression: Expression,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None = None,
    bare_value_types: Mapping[str, ValueType] | None = None,
    bare_value_expressions: Mapping[str, Expression] | None = None,
    suppressed_unknown_names: set[str] | None = None,
) -> ValueType:
    """Infer one row-level expression with optional bare-only local bindings."""

    return _infer(
        expression,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
    )


def _callable_row_schema(
    definition: ConstraintDef | DeriveDef,
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType],
    type_nullability: Mapping[TypeExpr, EffectiveNullability],
) -> RowSchema:
    """Build a local value environment from the first parameter binding."""

    fields: dict[str, RowField] = {}
    for parameter in definition.parameters:
        if parameter.name in fields:
            continue
        fields[parameter.name] = RowField(
            name=parameter.name,
            resolved_type=type_expansions[parameter.type],
            nullability=type_nullability[parameter.type],
        )
    return RowSchema(fields=fields)


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


def _is_direct_aggregate_projection(item: SelectItem) -> bool:
    expression = item.expression
    return (
        item.alias is not None
        and isinstance(expression, CallExpr)
        and is_semantic_aggregate_call(expression)
    )


def _relation_let_expressions(
    script: Script,
    relation_let_value_types: Mapping[DerivedRelation, Mapping[str, ValueType]],
) -> dict[DerivedRelation, dict[str, Expression]]:
    expressions: dict[DerivedRelation, dict[str, Expression]] = {}
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        if definition.let_clause is None:
            continue
        admitted_names = relation_let_value_types.get(definition)
        if not admitted_names:
            continue
        expressions[definition] = {
            binding.name: binding.expression
            for binding in definition.let_clause.bindings
            if binding.name in admitted_names
        }
    return expressions


def _infer(
    expression: Expression,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None = None,
    allow_aggregate_projection: bool = False,
    bare_value_types: Mapping[str, ValueType] | None = None,
    bare_value_expressions: Mapping[str, Expression] | None = None,
    suppressed_unknown_names: set[str] | None = None,
) -> ValueType:
    """Infer only the expression forms supported by this scaffold."""

    existing = value_types.get(expression)
    if existing is not None:
        return existing

    if isinstance(expression, WindowExpr):
        diagnostics.append(
            _unknown_function_diagnostic(
                expression.call,
                _callee_name(expression.call),
            )
        )
        return _UNKNOWN_VALUE_TYPE

    if isinstance(expression, LiteralExpr):
        value_type = _literal_value_type(expression)
    elif isinstance(expression, NameExpr):
        value_type = _name_value_type(
            expression,
            row_schema,
            diagnostics,
            report_unknown=report_unknown_name,
            bare_value_types=bare_value_types,
            suppressed_unknown_names=suppressed_unknown_names,
        )
    elif isinstance(expression, DottedNameExpr) and field_qualifier is not None:
        value_type = _qualified_name_value_type(
            expression,
            row_schema,
            diagnostics,
            field_qualifier=field_qualifier,
            report_unknown=report_unknown_name,
        )
    elif isinstance(expression, CallExpr):
        value_type = _call_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            allow_aggregate_projection=allow_aggregate_projection,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
    elif isinstance(expression, IsNullExpr):
        _infer(
            expression.value,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
        value_type = _builtin_value_type(
            "Bool",
            EffectiveNullability.NON_NULL,
        )
    elif isinstance(expression, UnaryExpr):
        value_type = _unary_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
    elif isinstance(expression, BinaryExpr):
        value_type = _binary_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
    elif isinstance(expression, ComparisonExpr):
        _infer(
            expression.left,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
        _infer(
            expression.right,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
        value_type = _builtin_value_type(
            "Bool",
            EffectiveNullability.UNKNOWN,
        )
    elif isinstance(expression, BetweenExpr):
        value_type = _between_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
    else:
        # Unsupported forms remain opaque so calls and arithmetic are not
        # accidentally checked through their child expressions.
        value_type = _UNKNOWN_VALUE_TYPE

    value_types[expression] = value_type
    return value_type


def _unary_value_type(
    expression: UnaryExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
) -> ValueType:
    """Type one prefix arithmetic expression."""

    operand_type = _infer(
        expression.operand,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
    )
    if operand_type.kind is ValueTypeKind.UNKNOWN:
        return _UNKNOWN_VALUE_TYPE
    if not _is_numeric(operand_type):
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="numeric operand",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    return ValueType(
        resolved_type=operand_type.resolved_type,
        nullability=operand_type.nullability,
    )


def _binary_value_type(
    expression: BinaryExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
) -> ValueType:
    """Type one arithmetic or Boolean binary expression."""

    left_type = _infer(
        expression.left,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
    )
    right_type = _infer(
        expression.right,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
    )
    if expression.operator == "/":
        return _UNKNOWN_VALUE_TYPE
    if (
        left_type.kind is ValueTypeKind.UNKNOWN
        or right_type.kind is ValueTypeKind.UNKNOWN
    ):
        return _UNKNOWN_VALUE_TYPE

    if expression.operator in {"and", "or"}:
        if _is_builtin(left_type, "Bool") and _is_builtin(right_type, "Bool"):
            return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="Bool operands",
            )
        )
        return _UNKNOWN_VALUE_TYPE

    if expression.operator == "%":
        if _is_builtin(left_type, "Int") and _is_builtin(right_type, "Int"):
            return _builtin_value_type("Int", EffectiveNullability.UNKNOWN)
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="Int operands",
            )
        )
        return _UNKNOWN_VALUE_TYPE

    if expression.operator in {"+", "-", "*"}:
        return_type = _binary_arithmetic_result_type(
            expression.operator,
            left_type,
            right_type,
        )
        if return_type is not None:
            return _builtin_value_type(return_type, EffectiveNullability.UNKNOWN)
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="numeric operands",
            )
        )
        return _UNKNOWN_VALUE_TYPE

    return _UNKNOWN_VALUE_TYPE


def _between_value_type(
    expression: BetweenExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
) -> ValueType:
    """Type an inclusive between predicate without compatibility checks."""

    child_types = tuple(
        _infer(
            child,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
        for child in (expression.value, expression.lower, expression.upper)
    )
    if any(child_type.kind is ValueTypeKind.UNKNOWN for child_type in child_types):
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)


def _call_value_type(
    expression: CallExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    allow_aggregate_projection: bool,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
) -> ValueType:
    """Type one exact built-in call while suppressing Unknown cascades."""

    function_name = _callee_name(expression)
    argument_types = _call_argument_types(
        expression,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        allow_aggregate_projection=allow_aggregate_projection,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
    )
    if any(
        argument_type.kind is ValueTypeKind.UNKNOWN for argument_type in argument_types
    ):
        return _UNKNOWN_VALUE_TYPE

    if is_semantic_aggregate_call(expression):
        if allow_aggregate_projection:
            result_type = _aggregate_value_type(
                expression,
                argument_types,
                let_expansions=bare_value_expressions,
            )
            if result_type is not None:
                return result_type
        return _UNKNOWN_VALUE_TYPE

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


def _call_argument_types(
    expression: CallExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    allow_aggregate_projection: bool,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
) -> tuple[ValueType, ...]:
    if (
        allow_aggregate_projection
        and is_semantic_aggregate_call(expression)
        and len(expression.arguments) == 1
        and not contains_semantic_aggregate(expression.arguments[0])
    ):
        argument = expression.arguments[0]
        temporary_diagnostics: list[Diagnostic] = []
        function_name = _callee_name(expression)
        argument_bare_value_types = (
            bare_value_types
            if aggregate_argument_can_use_let_scope(
                function_name,
                argument,
                bare_value_expressions,
            )
            else None
        )
        argument_type = _infer(
            argument,
            row_schema,
            value_types,
            temporary_diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=argument_bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
        if is_supported_semantic_aggregate_argument_expression(
            function_name,
            argument,
            argument_type,
            let_expansions=bare_value_expressions,
        ) or has_unknown_field_reference(argument, value_types):
            diagnostics.extend(temporary_diagnostics)
        return (argument_type,)

    return tuple(
        _infer(
            argument,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
        )
        for argument in expression.arguments
    )


def _callee_name(expression: CallExpr) -> str:
    """Return a source-level name for a simple or dotted call target."""

    if isinstance(expression.callee, NameExpr):
        return expression.callee.name
    assert isinstance(expression.callee, DottedNameExpr)
    return ".".join(expression.callee.parts)


def _aggregate_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    *,
    let_expansions: Mapping[str, Expression] | None,
) -> ValueType | None:
    """Return a precise aggregate type only for approved direct projections."""

    function_name = semantic_aggregate_call_name(expression)
    if function_name is None:
        return None
    if not expression.arguments:
        return semantic_projection_aggregate_result_value_type(function_name)
    if len(expression.arguments) != 1:
        return None
    argument = expression.arguments[0]
    if not is_supported_semantic_aggregate_argument_expression(
        function_name,
        argument,
        argument_types[0],
        let_expansions=let_expansions,
    ):
        return None
    return semantic_projection_aggregate_result_value_type(
        function_name,
        argument_types[0],
    )


def _append_invalid_count_context_diagnostic(
    expression: Expression,
    diagnostics: list[Diagnostic],
    *,
    context: str,
) -> None:
    """Report aggregate use where aggregate semantics are not admitted."""

    if contains_semantic_aggregate(expression):
        diagnostics.append(invalid_context_diagnostic(expression, context=context))


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
    bare_value_types: Mapping[str, ValueType] | None,
    suppressed_unknown_names: set[str] | None,
) -> ValueType:
    """Resolve a bare field name against a known row schema."""

    if row_schema.is_unknown:
        return _UNKNOWN_VALUE_TYPE
    field = row_schema.fields.get(expression.name)
    if field is not None:
        if field.resolved_type.kind is TypeKind.UNKNOWN:
            return _UNKNOWN_VALUE_TYPE
        return ValueType(
            resolved_type=field.resolved_type,
            nullability=field.nullability,
        )

    if bare_value_types is not None:
        value_type = bare_value_types.get(expression.name)
        if value_type is not None:
            return value_type

    if report_unknown and expression.name not in (suppressed_unknown_names or set()):
        diagnostics.append(_unknown_field_diagnostic(expression))
    return _UNKNOWN_VALUE_TYPE


def _qualified_name_value_type(
    expression: DottedNameExpr,
    row_schema: RowSchema,
    diagnostics: list[Diagnostic],
    *,
    field_qualifier: str,
    report_unknown: bool,
) -> ValueType:
    """Resolve one two-part field reference against the sole relation input."""

    if row_schema.is_unknown:
        return _UNKNOWN_VALUE_TYPE
    if len(expression.parts) != 2 or expression.parts[0] != field_qualifier:
        if report_unknown:
            diagnostics.append(_unknown_field_diagnostic(expression))
        return _UNKNOWN_VALUE_TYPE

    field = row_schema.fields.get(expression.parts[1])
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


def _is_numeric(value_type: ValueType) -> bool:
    """Return whether a known value type is one of Pietto's numeric scalars."""

    return _is_builtin(value_type, "Int") or _is_builtin(value_type, "Float")


def _binary_arithmetic_result_type(
    operator: str,
    left_type: ValueType,
    right_type: ValueType,
) -> str | None:
    """Return the approved result type for one binary arithmetic expression."""

    if _is_numeric(left_type) and _is_numeric(right_type):
        return (
            "Float"
            if _is_builtin(left_type, "Float") or _is_builtin(right_type, "Float")
            else "Int"
        )
    if (
        operator in {"+", "-"}
        and _is_builtin(left_type, "Decimal")
        and _is_builtin(right_type, "Decimal")
    ):
        return "Decimal"
    if operator in {"+", "-"} and _is_decimal_int_pair(left_type, right_type):
        return "Decimal"
    return None


def _is_decimal_int_pair(left_type: ValueType, right_type: ValueType) -> bool:
    return (_is_builtin(left_type, "Decimal") and _is_builtin(right_type, "Int")) or (
        _is_builtin(left_type, "Int") and _is_builtin(right_type, "Decimal")
    )


def _is_builtin(value_type: ValueType, name: str) -> bool:
    """Return whether a known value type names one exact built-in type."""

    return (
        value_type.resolved_type.kind is TypeKind.BUILTIN
        and value_type.resolved_type.name == name
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


def _invalid_operator_operands_diagnostic(
    expression: UnaryExpr | BinaryExpr,
    *,
    expected: str,
) -> Diagnostic:
    """Report incompatible known operands at the full operator expression span."""

    span = expression.span
    return Diagnostic(
        code="PIE-S2105",
        severity=Severity.ERROR,
        message=(
            f"Invalid operands for operator {expression.operator}: expected {expected}"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _unknown_field_diagnostic(expression: NameExpr | DottedNameExpr) -> Diagnostic:
    """Report an unknown field reference at its expression span."""

    span = expression.span
    name = (
        expression.name
        if isinstance(expression, NameExpr)
        else ".".join(expression.parts)
    )
    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=f"Unknown field: {name}",
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
