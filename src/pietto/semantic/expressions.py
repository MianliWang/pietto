"""Minimal expression value typing for supported field environments."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import TYPE_CHECKING

from pietto import ast_nodes as ast
from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CastExpr,
    CallExpr,
    ConditionalExpr,
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
    MembershipExpr,
    NameExpr,
    Nullability,
    ParameterRefExpr,
    QueryDef,
    Script,
    SelectItem,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
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

if TYPE_CHECKING:
    from pietto.semantic.window_semantics import (
        ResolvedNamedWindowNamespace,
        WindowExpressionAnalysis,
    )

RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef

_UNKNOWN_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)
_NULLIF_SIGNATURE = BuiltinFunction("nullif", ("T", "T"), "T")
_SIGN_SIGNATURE = BuiltinFunction("sign", ("Int|Decimal",), "Int")
_Q1_FIXED_CANONICAL_FUNCTIONS = frozenset(
    {
        "upper",
        "substr",
        "replace",
        "contains",
        "starts_with",
        "ends_with",
        "abs",
        "date_of",
        "hour",
        "minute",
    }
)


_KNOWN_EXPRESSIONS = frozenset(
    {
        ast.LiteralExpr,
        ast.NameExpr,
        ast.DottedNameExpr,
        ast.CallExpr,
        ast.UnaryExpr,
        ast.ConditionalExpr,
        ast.MembershipExpr,
        ast.RelationExistsExpr,
        ast.CastExpr,
        ast.BinaryExpr,
        ast.ComparisonExpr,
        ast.BetweenExpr,
        ast.IsNullExpr,
        ast.WindowExpr,
        ast.ParameterRefExpr,
    }
)
QUERY_PARAMETER_TYPES = ("Bool", "Int", "Float", "Text")
_QUERY_PARAMETER_NULLABILITY = {
    Nullability.NOT_NULL: EffectiveNullability.NON_NULL,
    Nullability.NULLABLE: EffectiveNullability.NULLABLE,
}


def query_parameter_value_type(type_name: str, nullability: Nullability) -> ValueType:
    """The value type of a validated header parameter or of one of its reads."""

    effective = _QUERY_PARAMETER_NULLABILITY.get(nullability)
    if type_name not in QUERY_PARAMETER_TYPES or effective is None:
        raise ValueError("Query parameter lacks a validated declaration.")
    return _builtin_value_type(type_name, effective)


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
    type_expansions: Mapping[TypeExpr, ResolvedType],
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
                type_expansions=type_expansions,
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
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
) -> tuple[
    dict[Expression, ValueType],
    list[Diagnostic],
    dict[WindowExpr, WindowExpressionAnalysis],
    dict[DerivedRelation, ResolvedNamedWindowNamespace],
]:
    """Type supported table/query expressions without validating consumers."""

    value_types: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    window_analyses: dict[WindowExpr, WindowExpressionAnalysis] = {}
    named_window_namespaces: dict[
        DerivedRelation,
        ResolvedNamedWindowNamespace,
    ] = {}
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
        named_window_namespace_failed = False
        named_window_namespace = None
        if definition.named_windows:
            from pietto.semantic.window_analysis import (
                named_window_resolution_diagnostics,
            )
            from pietto.semantic.window_semantics import (
                NamedWindowResolutionFailure,
                ResolvedNamedWindowNamespace,
                resolve_named_window_namespace,
            )

            named_window_namespace = resolve_named_window_namespace(definition)
            if type(named_window_namespace) is NamedWindowResolutionFailure:
                diagnostics.extend(
                    named_window_resolution_diagnostics(named_window_namespace)
                )
                named_window_namespace_failed = True
                named_window_namespace = None
            else:
                assert type(named_window_namespace) is ResolvedNamedWindowNamespace
                named_window_namespaces[definition] = named_window_namespace
        selected_output_names = tuple(
            _relation_projection_output_name(item) for item in definition.select_items
        )
        selected_output_name_counts = Counter(
            name for name in selected_output_names if name is not None
        )
        duplicate_window_output_names = {
            item.alias
            for item in definition.select_items
            if type(item.expression) is WindowExpr
            and item.alias is not None
            and selected_output_name_counts[item.alias] != 1
        }
        window_alias_value_types: dict[str, ValueType] = {}
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
                type_expansions=type_expansions,
            )
        for selected_output_ordinal, item in enumerate(definition.select_items):
            if type(item.expression) is WindowExpr:
                if named_window_namespace_failed:
                    continue
                from pietto.semantic.window_analysis import (
                    analyze_window_expression,
                )

                analysis = analyze_window_expression(
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
                    named_window_namespace=named_window_namespace,
                )
                from pietto.semantic.window_semantics import (
                    WindowExpressionAnalysis,
                    WindowResultAvailabilityKind,
                )

                if type(analysis) is WindowExpressionAnalysis:
                    window_analyses[item.expression] = analysis
                    result = analysis.semantic_fact.result
                    if (
                        result.kind is WindowResultAvailabilityKind.CONCRETE
                        and result.value_type is not None
                    ):
                        value_types[item.expression] = result.value_type
                        if (
                            item.alias is not None
                            and selected_output_name_counts[item.alias] == 1
                        ):
                            window_alias_value_types[item.alias] = result.value_type
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
                type_expansions=type_expansions,
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
                order_bare_value_types = let_value_types
                if (
                    type(item.expression) is NameExpr
                    and item.expression.name in window_alias_value_types
                ):
                    order_bare_value_types = dict(window_alias_value_types)
                    order_bare_value_types.update(let_value_types or {})
                elif (
                    type(item.expression) is NameExpr
                    and item.expression.name in duplicate_window_output_names
                ):
                    order_bare_value_types = {
                        item.expression.name: _UNKNOWN_VALUE_TYPE,
                        **(let_value_types or {}),
                    }
                _infer(
                    item.expression,
                    input_schema,
                    value_types,
                    diagnostics,
                    report_unknown_name=True,
                    field_qualifier=definition.from_clause.source_name,
                    bare_value_types=order_bare_value_types,
                    bare_value_expressions=let_expressions,
                    type_expansions=type_expansions,
                )

    return value_types, diagnostics, window_analyses, named_window_namespaces


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
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
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
        type_expansions=type_expansions,
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


def _relation_projection_output_name(item: SelectItem) -> str | None:
    """Return one selected output name for duplicate-scope accounting."""

    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


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
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
) -> ValueType:
    """Infer only the expression forms supported by this scaffold."""

    if type(expression) not in _KNOWN_EXPRESSIONS:
        raise AssertionError(f"Unsupported expression: {type(expression).__name__}")
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
    elif isinstance(expression, ParameterRefExpr):
        value_type = query_parameter_value_type(
            expression.type_name, expression.nullability
        )
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
            type_expansions=type_expansions,
        )
    elif isinstance(expression, ast.RelationExistsExpr):
        # An existence test is never NULL; its relation is resolved, scheduled
        # and checked by the owner of the relation name, not by this kernel.
        value_type = _builtin_value_type("Bool", EffectiveNullability.NON_NULL)
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
            type_expansions=type_expansions,
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
            type_expansions=type_expansions,
        )
    elif isinstance(expression, ConditionalExpr):
        value_type = _conditional_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
        )
    elif isinstance(expression, MembershipExpr):
        value_type = _membership_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
        )
    elif isinstance(expression, CastExpr):
        value_type = _cast_value_type(
            expression,
            row_schema,
            value_types,
            diagnostics,
            report_unknown_name=report_unknown_name,
            field_qualifier=field_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            suppressed_unknown_names=suppressed_unknown_names,
            type_expansions=type_expansions,
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
            type_expansions=type_expansions,
        )
    elif isinstance(expression, ComparisonExpr):
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
            type_expansions=type_expansions,
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
            type_expansions=type_expansions,
        )
        if expression.operator in {"like", "not like"}:
            value_type, expected = resolved_like_value_type(left_type, right_type)
        else:
            value_type, expected = resolved_comparison_value_type(
                left_type, right_type, type_expansions
            )
        if expected is not None:
            diagnostics.append(
                _invalid_operator_operands_diagnostic(expression, expected=expected)
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
            type_expansions=type_expansions,
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
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
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
        type_expansions=type_expansions,
    )
    if expression.operator == "not" and _is_canonical_builtin(
        operand_type, "Bool", type_expansions
    ):
        result, expected = _builtin_value_type("Bool", operand_type.nullability), None
    else:
        result, expected = resolved_unary_value_type(expression.operator, operand_type)
    if expected is not None:
        diagnostics.append(
            _invalid_operator_operands_diagnostic(expression, expected=expected)
        )
    return result


def resolved_unary_value_type(
    operator: str | ValueType,
    operand_type: ValueType | None = None,
) -> tuple[ValueType, str | None]:
    """Return the closed unary result without source lookup or elaboration.

    The one-argument form remains the historic numeric rule for internal
    callers that have not yet selected an authored operator.
    """

    if operand_type is None:
        assert isinstance(operator, ValueType)
        operand_type = operator
        operator = "+"
    assert isinstance(operator, str)
    assert isinstance(operand_type, ValueType)
    if operand_type.kind is ValueTypeKind.UNKNOWN:
        return _UNKNOWN_VALUE_TYPE, None
    if operator == "not":
        if _is_builtin(operand_type, "Bool"):
            return ValueType(
                resolved_type=operand_type.resolved_type,
                nullability=operand_type.nullability,
            ), None
        return _UNKNOWN_VALUE_TYPE, "Bool operand"
    if not _is_numeric(operand_type):
        return _UNKNOWN_VALUE_TYPE, "numeric operand"
    return ValueType(
        resolved_type=operand_type.resolved_type,
        nullability=operand_type.nullability,
    ), None


def _conditional_value_type(
    expression: ConditionalExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    """Type source-ordered conditional operands with no branch promotion."""

    when_true_type = _infer(
        expression.when_true,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
    )
    condition_type = _infer(
        expression.condition,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
    )
    when_false_type = _infer(
        expression.when_false,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
    )
    branch_types = _contextual_null_literal_types(
        (expression.when_true, expression.when_false),
        (when_true_type, when_false_type),
        value_types,
        type_expansions,
    )
    if branch_types is not None:
        when_true_type, when_false_type = branch_types
    if (
        _is_null_literal(expression.condition)
        and condition_type.kind is ValueTypeKind.UNKNOWN
    ):
        condition_type = _contextual_null_literal_type("Bool")
        value_types[expression.condition] = condition_type
    if any(
        value_type.kind is ValueTypeKind.UNKNOWN
        for value_type in (when_true_type, condition_type, when_false_type)
    ):
        return _UNKNOWN_VALUE_TYPE
    if not _is_canonical_builtin(condition_type, "Bool", type_expansions):
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="Bool condition",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    canonical = _shared_canonical_type(
        (when_true_type, when_false_type),
        type_expansions,
    )
    if canonical is None:
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="same canonical branch types",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    return ValueType(
        resolved_type=canonical,
        nullability=_join_nullability(
            (when_true_type.nullability, when_false_type.nullability)
        ),
    )


def _membership_value_type(
    expression: MembershipExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    """Type fixed scalar-list membership while retaining every occurrence."""

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
            type_expansions=type_expansions,
        )
        for child in (expression.value, *expression.options)
    )
    contextual = _contextual_null_literal_types(
        (expression.value, *expression.options),
        child_types,
        value_types,
        type_expansions,
    )
    if contextual is not None:
        child_types = contextual
    if any(value_type.kind is ValueTypeKind.UNKNOWN for value_type in child_types):
        return _UNKNOWN_VALUE_TYPE
    if _shared_canonical_type(child_types, type_expansions) is None:
        diagnostics.append(
            _invalid_operator_operands_diagnostic(
                expression,
                expected="same canonical membership operands",
            )
        )
        return _UNKNOWN_VALUE_TYPE
    if not expression.options:
        return _builtin_value_type("Bool", EffectiveNullability.NON_NULL)
    return _builtin_value_type(
        "Bool",
        _join_nullability(tuple(value_type.nullability for value_type in child_types)),
    )


def _cast_value_type(
    expression: CastExpr,
    row_schema: RowSchema,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    *,
    report_unknown_name: bool,
    field_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None,
    bare_value_expressions: Mapping[str, Expression] | None,
    suppressed_unknown_names: set[str] | None,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    """Admit only the explicit portable Int-to-Float conversion."""

    value_type = _infer(
        expression.value,
        row_schema,
        value_types,
        diagnostics,
        report_unknown_name=report_unknown_name,
        field_qualifier=field_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        type_expansions=type_expansions,
    )
    if value_type.kind is ValueTypeKind.UNKNOWN:
        return _UNKNOWN_VALUE_TYPE
    if (
        expression.target.name != "Float"
        or expression.target.arguments
        or expression.target.nullability is not Nullability.IMPLICIT
        or not _is_canonical_builtin(value_type, "Int", type_expansions)
    ):
        diagnostics.append(
            _invalid_cast_diagnostic(expression, expected="cast(Int as Float)")
        )
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type("Float", value_type.nullability)


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
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
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
        type_expansions=type_expansions,
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
        type_expansions=type_expansions,
    )
    result, expected = resolved_binary_value_type(
        expression.operator, left_type, right_type
    )
    if expected is not None:
        diagnostics.append(
            _invalid_operator_operands_diagnostic(expression, expected=expected)
        )
    return result


def resolved_binary_value_type(
    operator: str, left_type: ValueType, right_type: ValueType
) -> tuple[ValueType, str | None]:
    """Original binary rule; no expression, name lookup or source elaboration."""
    if operator == "/" or (
        left_type.kind is ValueTypeKind.UNKNOWN
        or right_type.kind is ValueTypeKind.UNKNOWN
    ):
        return _UNKNOWN_VALUE_TYPE, None
    if operator in {"and", "or"}:
        if _is_builtin(left_type, "Bool") and _is_builtin(right_type, "Bool"):
            return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN), None
        return _UNKNOWN_VALUE_TYPE, "Bool operands"
    if operator == "%":
        if _is_builtin(left_type, "Int") and _is_builtin(right_type, "Int"):
            return _builtin_value_type("Int", EffectiveNullability.UNKNOWN), None
        return _UNKNOWN_VALUE_TYPE, "Int operands"
    if operator in {"+", "-", "*"}:
        name = _binary_arithmetic_result_type(operator, left_type, right_type)
        if name is not None:
            return _builtin_value_type(name, EffectiveNullability.UNKNOWN), None
        return _UNKNOWN_VALUE_TYPE, "numeric operands"
    return _UNKNOWN_VALUE_TYPE, None


# Builtin families from the canonical scalar type registry trait vocabulary.
# Any, Bytes, Json, enums and shapes stay unchecked (deferred).
_COMPARISON_FAMILIES = {
    "Int": "numeric",
    "Float": "numeric",
    "Decimal": "numeric",
    "Text": "text",
    "Bool": "boolean",
    "Date": "temporal",
    "Timestamp": "temporal",
    "UUID": "identifier",
}
# Text against types without literal syntax awaits a typed-constant decision.
_DEFERRED_COMPARISON_FAMILY_PAIRS = ({"text", "temporal"}, {"text", "identifier"})


def resolved_comparison_value_type(
    left_type: ValueType,
    right_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
) -> tuple[ValueType, str | None]:
    """Comparison rule over resolved operands; no implicit cross-family conversion."""
    families = {
        _comparison_family(left_type, type_expansions),
        _comparison_family(right_type, type_expansions),
    }
    if (
        None in families
        or len(families) == 1
        or families in _DEFERRED_COMPARISON_FAMILY_PAIRS
    ):
        return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN), None
    return _UNKNOWN_VALUE_TYPE, "comparable operands"


def resolved_like_value_type(
    left_type: ValueType,
    right_type: ValueType,
) -> tuple[ValueType, str | None]:
    """Return the closed Text/Text LIKE result without collation claims."""

    if (
        left_type.kind is ValueTypeKind.UNKNOWN
        or right_type.kind is ValueTypeKind.UNKNOWN
    ):
        return _UNKNOWN_VALUE_TYPE, None
    if not (_is_builtin(left_type, "Text") and _is_builtin(right_type, "Text")):
        return _UNKNOWN_VALUE_TYPE, "Text operands"
    return _builtin_value_type(
        "Bool",
        _join_nullability((left_type.nullability, right_type.nullability)),
    ), None


def _canonical_resolved_type(
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ResolvedType | None:
    if value_type.kind is ValueTypeKind.UNKNOWN:
        return None
    resolved = value_type.resolved_type
    if resolved.kind is not TypeKind.TYPE_ALIAS:
        return resolved
    if type_expansions is None or not isinstance(resolved.definition, TypeDef):
        return None
    return type_expansions.get(resolved.definition.base)


def _shared_canonical_type(
    value_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ResolvedType | None:
    canonical_types = tuple(
        _canonical_resolved_type(value_type, type_expansions)
        for value_type in value_types
    )
    if not canonical_types or any(value_type is None for value_type in canonical_types):
        return None
    canonical = canonical_types[0]
    assert canonical is not None
    if any(
        value_type is None
        or value_type.kind is not canonical.kind
        or value_type.name != canonical.name
        or value_type.definition is not canonical.definition
        for value_type in canonical_types[1:]
    ):
        return None
    return canonical


def _join_nullability(
    nullabilities: tuple[EffectiveNullability, ...],
) -> EffectiveNullability:
    if EffectiveNullability.NULLABLE in nullabilities:
        return EffectiveNullability.NULLABLE
    if EffectiveNullability.UNKNOWN in nullabilities:
        return EffectiveNullability.UNKNOWN
    return EffectiveNullability.NON_NULL


def _comparison_family(
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> str | None:
    resolved_type = value_type.resolved_type
    if type_expansions is not None and resolved_type.kind is TypeKind.TYPE_ALIAS:
        # Single-file row fields keep alias names; compare the canonical expansion.
        definition = resolved_type.definition
        assert isinstance(definition, TypeDef)
        resolved_type = type_expansions[definition.base]
    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or resolved_type.kind is not TypeKind.BUILTIN
    ):
        return None
    return _COMPARISON_FAMILIES.get(resolved_type.name)


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
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    """Type an inclusive between predicate as two bound comparisons."""

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
            type_expansions=type_expansions,
        )
        for child in (expression.value, expression.lower, expression.upper)
    )
    if any(child_type.kind is ValueTypeKind.UNKNOWN for child_type in child_types):
        return _UNKNOWN_VALUE_TYPE
    for bound_type in child_types[1:]:
        _, expected = resolved_comparison_value_type(
            child_types[0], bound_type, type_expansions
        )
        if expected is not None:
            diagnostics.append(
                _invalid_operator_operands_diagnostic(expression, expected=expected)
            )
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
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
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
        type_expansions=type_expansions,
    )
    if function_name in {"coalesce", "nullif"}:
        contextual = _contextual_null_literal_types(
            expression.arguments,
            argument_types,
            value_types,
            type_expansions,
        )
        if contextual is None:
            return _UNKNOWN_VALUE_TYPE
        argument_types = contextual
        if function_name == "coalesce":
            return _coalesce_value_type(
                expression, argument_types, type_expansions, diagnostics
            )
        return _nullif_value_type(
            expression, argument_types, type_expansions, diagnostics
        )

    if is_semantic_aggregate_call(expression):
        if any(
            argument_type.kind is ValueTypeKind.UNKNOWN
            for argument_type in argument_types
        ):
            return _UNKNOWN_VALUE_TYPE
        if allow_aggregate_projection:
            result_type = _aggregate_value_type(
                expression,
                argument_types,
                let_expansions=bare_value_expressions,
            )
            if result_type is not None:
                return result_type
        return _UNKNOWN_VALUE_TYPE

    if any(
        argument_type.kind is ValueTypeKind.UNKNOWN for argument_type in argument_types
    ) and function_name in {"sign", "year", "month", "day"}:
        return _UNKNOWN_VALUE_TYPE
    if function_name == "sign":
        return _sign_value_type(
            expression, argument_types, diagnostics, type_expansions=type_expansions
        )
    if function_name in {"year", "month", "day"}:
        return _civil_date_part_value_type(
            expression, argument_types, diagnostics, type_expansions=type_expansions
        )

    signature = BUILTIN_FUNCTIONS.get(function_name)
    if signature is None:
        if any(
            argument_type.kind is ValueTypeKind.UNKNOWN
            for argument_type in argument_types
        ):
            return _UNKNOWN_VALUE_TYPE
        diagnostics.append(_unknown_function_diagnostic(expression, function_name))
        return _UNKNOWN_VALUE_TYPE

    if len(argument_types) != len(signature.parameter_types):
        diagnostics.append(_wrong_arity_diagnostic(expression, signature))
        return _UNKNOWN_VALUE_TYPE

    argument_types = _contextual_fixed_null_literal_types(
        expression.arguments,
        argument_types,
        signature.parameter_types,
        value_types,
    )
    if any(
        argument_type.kind is ValueTypeKind.UNKNOWN for argument_type in argument_types
    ):
        return _UNKNOWN_VALUE_TYPE

    for position, (argument_type, expected_name) in enumerate(
        zip(argument_types, signature.parameter_types, strict=True),
        start=1,
    ):
        matches = (
            _is_canonical_builtin(argument_type, expected_name, type_expansions)
            if function_name in _Q1_FIXED_CANONICAL_FUNCTIONS
            else _is_builtin(argument_type, expected_name)
        )
        if not matches:
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

    if function_name == "substr" and not _valid_static_substr_bounds(expression):
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    "Invalid arguments for function substr: start must be a positive "
                    "Int literal and count must be a non-negative Int literal"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE

    if function_name == "matches":
        return _builtin_value_type("Bool", EffectiveNullability.UNKNOWN)

    return _builtin_value_type(
        signature.return_type,
        _join_nullability(
            tuple(argument_type.nullability for argument_type in argument_types)
        ),
    )


def _coalesce_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    diagnostics: list[Diagnostic],
) -> ValueType:
    if len(argument_types) < 2:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    "Invalid arguments for function coalesce: expected at least 2, got "
                    f"{len(argument_types)}"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    canonical = _shared_canonical_type(argument_types, type_expansions)
    if canonical is None:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    "Invalid argument types for function coalesce: expected same "
                    "canonical type"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    if EffectiveNullability.NON_NULL in {
        argument_type.nullability for argument_type in argument_types
    }:
        nullability = EffectiveNullability.NON_NULL
    elif EffectiveNullability.UNKNOWN in {
        argument_type.nullability for argument_type in argument_types
    }:
        nullability = EffectiveNullability.UNKNOWN
    else:
        nullability = EffectiveNullability.NULLABLE
    return ValueType(resolved_type=canonical, nullability=nullability)


def _nullif_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    diagnostics: list[Diagnostic],
) -> ValueType:
    if len(argument_types) != 2:
        diagnostics.append(_wrong_arity_diagnostic(expression, _NULLIF_SIGNATURE))
        return _UNKNOWN_VALUE_TYPE
    canonical = _shared_canonical_type(argument_types, type_expansions)
    if canonical is None:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    "Invalid argument types for function nullif: expected same "
                    "canonical comparable type"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    left_nullability = argument_types[0].nullability
    return ValueType(
        resolved_type=canonical,
        nullability=(
            EffectiveNullability.NULLABLE
            if left_nullability is EffectiveNullability.NON_NULL
            else left_nullability
        ),
    )


def _is_null_literal(expression: Expression) -> bool:
    return isinstance(expression, LiteralExpr) and expression.value is None


def _contextual_null_literal_type(resolved: ResolvedType | str) -> ValueType:
    return ValueType(
        resolved_type=(
            _builtin_value_type(resolved, EffectiveNullability.NULLABLE).resolved_type
            if isinstance(resolved, str)
            else resolved
        ),
        nullability=EffectiveNullability.NULLABLE,
    )


def _contextual_null_literal_types(
    expressions: tuple[Expression, ...],
    value_types: tuple[ValueType, ...],
    recorded: dict[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> tuple[ValueType, ...] | None:
    """Type only literal NULLs from one local approved common-type context."""

    if any(
        value_type.kind is ValueTypeKind.UNKNOWN and not _is_null_literal(expression)
        for expression, value_type in zip(expressions, value_types, strict=True)
    ):
        return None
    known = tuple(
        value_type
        for value_type in value_types
        if value_type.kind is ValueTypeKind.KNOWN
    )
    if not known:
        return None
    canonical = _shared_canonical_type(known, type_expansions)
    if canonical is None:
        return value_types
    result = []
    for expression, value_type in zip(expressions, value_types, strict=True):
        if value_type.kind is ValueTypeKind.UNKNOWN and _is_null_literal(expression):
            value_type = _contextual_null_literal_type(canonical)
            recorded[expression] = value_type
        result.append(value_type)
    return tuple(result)


def _contextual_fixed_null_literal_types(
    expressions: tuple[Expression, ...],
    value_types: tuple[ValueType, ...],
    parameter_types: tuple[str, ...],
    recorded: dict[Expression, ValueType],
) -> tuple[ValueType, ...]:
    """Type literal NULLs only where one closed built-in parameter type selects it."""

    result = []
    for expression, value_type, parameter_type in zip(
        expressions, value_types, parameter_types, strict=True
    ):
        if value_type.kind is ValueTypeKind.UNKNOWN and _is_null_literal(expression):
            value_type = _contextual_null_literal_type(parameter_type)
            recorded[expression] = value_type
        result.append(value_type)
    return tuple(result)


def _sign_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    diagnostics: list[Diagnostic],
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    if len(argument_types) != 1:
        diagnostics.append(_wrong_arity_diagnostic(expression, _SIGN_SIGNATURE))
        return _UNKNOWN_VALUE_TYPE
    argument_type = argument_types[0]
    if not (
        _is_canonical_builtin(argument_type, "Int", type_expansions)
        or _is_canonical_builtin(argument_type, "Decimal", type_expansions)
    ):
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    "Invalid argument type for function sign at position 1: "
                    f"expected Int or Decimal, got {argument_type.resolved_type.name}"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type("Int", argument_type.nullability)


def _civil_date_part_value_type(
    expression: CallExpr,
    argument_types: tuple[ValueType, ...],
    diagnostics: list[Diagnostic],
    *,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    if len(argument_types) != 1:
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    f"Invalid arguments for function {_callee_name(expression)}: "
                    f"expected 1, got {len(argument_types)}"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    argument_type = argument_types[0]
    if not (
        _is_canonical_builtin(argument_type, "Date", type_expansions)
        or _is_canonical_builtin(argument_type, "Timestamp", type_expansions)
    ):
        diagnostics.append(
            _call_diagnostic(
                expression,
                code="PIE-S2104",
                message=(
                    f"Invalid argument type for function {_callee_name(expression)} at "
                    "position 1: expected Date or Timestamp, got "
                    f"{argument_type.resolved_type.name}"
                ),
            )
        )
        return _UNKNOWN_VALUE_TYPE
    return _builtin_value_type("Int", argument_type.nullability)


def _valid_static_substr_bounds(expression: CallExpr) -> bool:
    start, count = expression.arguments[1:]
    return (
        isinstance(start, LiteralExpr)
        and type(start.value) is int
        and start.value > 0
        and isinstance(count, LiteralExpr)
        and type(count.value) is int
        and count.value >= 0
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
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
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
            type_expansions=type_expansions,
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
            type_expansions=type_expansions,
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

    return resolved_literal_value_type(expression.value)


def resolved_literal_value_type(value: object) -> ValueType:
    """Original scalar literal law, independent of a source expression owner."""
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
        operator in {"+", "-", "*"}
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


def _is_canonical_builtin(
    value_type: ValueType,
    name: str,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> bool:
    resolved = _canonical_resolved_type(value_type, type_expansions)
    return (
        resolved is not None
        and resolved.kind is TypeKind.BUILTIN
        and resolved.name == name
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
    expression: (
        UnaryExpr
        | BinaryExpr
        | ComparisonExpr
        | BetweenExpr
        | ConditionalExpr
        | MembershipExpr
    ),
    *,
    expected: str,
) -> Diagnostic:
    """Report incompatible known operands at the full operator expression span."""

    span = expression.span
    if isinstance(expression, BetweenExpr):
        operator = "between"
    elif isinstance(expression, ConditionalExpr):
        operator = "conditional"
    elif isinstance(expression, MembershipExpr):
        operator = "in" if not expression.negated else "not in"
    else:
        operator = expression.operator
    return Diagnostic(
        code="PIE-S2105",
        severity=Severity.ERROR,
        message=f"Invalid operands for operator {operator}: expected {expected}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _invalid_cast_diagnostic(expression: CastExpr, *, expected: str) -> Diagnostic:
    """Report a rejected explicit conversion at the complete cast span."""

    span = expression.span
    return Diagnostic(
        code="PIE-S2105",
        severity=Severity.ERROR,
        message=f"Invalid cast: expected {expected}",
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
