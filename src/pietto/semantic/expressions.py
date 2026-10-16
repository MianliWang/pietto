"""Minimal expression value typing for supported field environments."""

from __future__ import annotations

import functools
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import TYPE_CHECKING, ParamSpec, cast

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
    WindowFrameUnit,
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
        ast.RelationScalarExpr,
        ast.RelationMembershipExpr,
        ast.CastExpr,
        ast.BinaryExpr,
        ast.ComparisonExpr,
        ast.BetweenExpr,
        ast.IsNullExpr,
        ast.WindowExpr,
        ast.ParameterRefExpr,
        ast.CapturedFieldExpr,
    }
)
QUERY_PARAMETER_TYPES = ("Bool", "Int", "Float", "Text")
_QUERY_PARAMETER_NULLABILITY = {
    Nullability.NOT_NULL: EffectiveNullability.NON_NULL,
    Nullability.NULLABLE: EffectiveNullability.NULLABLE,
}


_P = ParamSpec("_P")


def checks_inlined_arguments(
    infer: Callable[_P, ValueType],
) -> Callable[_P, ValueType]:
    """Check each inlined argument a clause-specific typer types itself; it
    takes the expression first and ``diagnostics`` by keyword."""

    @functools.wraps(infer)
    def checked(*args: _P.args, **kwargs: _P.kwargs) -> ValueType:
        return _check_inlined_argument(
            cast(Expression, args[0]),
            infer(*args, **kwargs),
            cast(list[Diagnostic], kwargs["diagnostics"]),
            cast(
                Mapping[TypeExpr, ResolvedType] | None,
                kwargs.get("type_expansions"),
            ),
        )

    return checked


def _check_inlined_argument(
    expression: Expression,
    value_type: ValueType,
    diagnostics: list[Diagnostic],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    """An argument whose canonical type or nullability does not fit a
    parameter it is inlined for (``Expression.argument_of``) is an error at the
    call; the argument then stays Unknown so the expansion reports nothing
    else."""

    if not expression.argument_of or value_type.kind is ValueTypeKind.UNKNOWN:
        return value_type
    canonical = _canonical_resolved_type(value_type, type_expansions)
    fits = True
    for slot in expression.argument_of:
        if (
            canonical is not None
            and canonical.kind is TypeKind.BUILTIN
            and canonical.name == slot.type_name
            and (
                slot.nullable or value_type.nullability is EffectiveNullability.NON_NULL
            )
        ):
            continue
        fits = False
        actual = (canonical or value_type.resolved_type).name
        expected = "nullable" if slot.nullable else "not null"
        diagnostics.append(
            Diagnostic(
                code="PIE-S2395",
                severity=Severity.ERROR,
                message=(
                    f"Invalid argument for def {slot.function} at position "
                    f"{slot.position} ({slot.parameter}): expected "
                    f"{slot.type_name} {expected}, got {actual} "
                    f"{_NULLABILITY_TEXT[value_type.nullability]}"
                ),
                location=SourceLocation(
                    path=slot.call.path,
                    line=slot.call.line,
                    column=slot.call.column,
                    end_line=slot.call.end_line,
                    end_column=slot.call.end_column,
                ),
            )
        )
    return value_type if fits else _UNKNOWN_VALUE_TYPE


_NULLABILITY_TEXT = MappingProxyType(
    {
        EffectiveNullability.NON_NULL: "not null",
        EffectiveNullability.NULLABLE: "nullable",
        EffectiveNullability.UNKNOWN: "of unknown nullability",
    }
)


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
    let_diagnostics: Sequence[Diagnostic] = (),
) -> tuple[
    dict[Expression, ValueType],
    list[Diagnostic],
    dict[WindowExpr, WindowExpressionAnalysis],
    dict[DerivedRelation, ResolvedNamedWindowNamespace],
]:
    """Type supported table/query expressions without validating consumers.

    ``let_diagnostics`` are the relation `let:` diagnostics; a window frame
    offset that reads a binding with one of them reports no PIE-S2104.
    """

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
        rejected_lets = set(rejected_let_names(definition, let_value_types))
        erroneous_lets = rejected_lets | _let_names_with_diagnostics(
            definition, let_diagnostics
        )
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
                bare_value_expressions=let_expressions,
                suppressed_unknown_names=rejected_lets,
                type_expansions=type_expansions,
            )
        for selected_output_ordinal, item in enumerate(definition.select_items):
            if type(item.expression) is WindowExpr:
                if named_window_namespace_failed:
                    continue
                from pietto.semantic.window_analysis import (
                    analyze_window_expression,
                )

                window_diagnostic_count = len(diagnostics)
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
                # A window read of a let name PIE-S2329 refused reports nothing
                # more. Dropping its unknown-field report afterwards keeps the
                # analysis stopping there without a fallback in its place.
                refused_reads = {f"Unknown field: {name}" for name in rejected_lets}
                diagnostics[window_diagnostic_count:] = [
                    diagnostic
                    for diagnostic in diagnostics[window_diagnostic_count:]
                    if diagnostic.code != "PIE-S2102"
                    or diagnostic.message not in refused_reads
                ]
                from pietto.semantic.window_semantics import (
                    WindowExpressionAnalysis,
                    WindowResultAvailabilityKind,
                )

                if type(analysis) is WindowExpressionAnalysis:
                    window_analyses[item.expression] = analysis
                    diagnostics.extend(
                        _window_literal_range_diagnostics(
                            item.expression,
                            analysis,
                            input_schema,
                            let_expressions or {},
                            erroneous_lets,
                        )
                    )
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
                suppressed_unknown_names=rejected_lets,
                type_expansions=type_expansions,
            )
        if (
            definition.order_by_clause is not None
            and definition.group_by_clause is None
        ):
            aggregated = any(
                contains_semantic_aggregate(selected.expression)
                for selected in definition.select_items
            )
            for item in definition.order_by_clause.items:
                key_diagnostic_count = len(diagnostics)
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
                order_suppressed_names = rejected_lets
                if (
                    type(item.expression) is NameExpr
                    and item.expression.name in selected_output_name_counts
                    and not _names_window_output(definition, item.expression.name)
                    and item.expression.name not in rejected_lets
                    and item.expression.name not in (order_bare_value_types or {})
                    and not input_schema.is_unknown
                    and item.expression.name not in input_schema.fields
                ):
                    diagnostics.append(
                        _order_by_output_name_diagnostic(
                            item.expression,
                            tuple(
                                selected.expression
                                for name, selected in zip(
                                    selected_output_names,
                                    definition.select_items,
                                    strict=True,
                                )
                                if name == item.expression.name
                            ),
                            input_schema,
                            let_expressions,
                        )
                    )
                    order_suppressed_names = {*rejected_lets, item.expression.name}
                _infer(
                    item.expression,
                    input_schema,
                    value_types,
                    diagnostics,
                    report_unknown_name=True,
                    field_qualifier=definition.from_clause.source_name,
                    bare_value_types=order_bare_value_types,
                    bare_value_expressions=let_expressions,
                    suppressed_unknown_names=order_suppressed_names,
                    type_expansions=type_expansions,
                )
                # A key that already reported its own error gets no PIE-S2380.
                # A bare constant key needs no field knowledge: with an unknown
                # input row a `let:` name is inlined, as emission inlines it.
                problem = (
                    None
                    if len(diagnostics) > key_diagnostic_count
                    else _order_key_problem(
                        item.expression,
                        input_schema,
                        let_expressions or {},
                        aggregated=aggregated and not input_schema.is_unknown,
                    )
                )
                if problem is not None:
                    diagnostics.append(_order_key_diagnostic(item.expression, problem))

    return value_types, diagnostics, window_analyses, named_window_namespaces


_SIGNED64_MAX = (1 << 63) - 1
# The literal count argument of each window function that takes one.
_WINDOW_COUNT_POSITIONS = {"ntile": 0, "lag": 1, "lead": 1, "nth_value": 1}


def _window_literal_range_diagnostics(
    expression: WindowExpr,
    analysis: WindowExpressionAnalysis,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression],
    erroneous_lets: set[str],
) -> list[Diagnostic]:
    """Refuse window literals that no SQL target accepts, before emission.

    A ROWS or GROUPS offset, after the `let:` inlining emission performs, must
    be a nonnegative signed 64-bit Int literal, and a count argument may not
    exceed that range; the narrower PostgreSQL int4 count range is checked
    when PostgreSQL SQL is emitted. An offset that reads a `let:` name in
    `erroneous_lets` already has its error.
    """

    name = expression.identity.name
    messages: list[str] = []
    frame = analysis.validated_specification.resolved.frame
    unit = frame.unit
    offsets = tuple(
        (bound.offset, let_value(bound.offset, input_schema, let_expressions))
        for bound in (frame.start, frame.end)
        if bound is not None and bound.offset is not None
    )
    if (unit is WindowFrameUnit.ROWS or unit is WindowFrameUnit.GROUPS) and any(
        not (
            type(value) is LiteralExpr
            and type(value.value) is int
            and 0 <= value.value <= _SIGNED64_MAX
        )
        and not _reads_erroneous_let(
            offset, input_schema, let_expressions, erroneous_lets
        )
        for offset, value in offsets
    ):
        messages.append(
            f"Invalid window frame for function {name}: "
            f"{unit.value.upper()} offsets must be nonnegative integer "
            f"literals up to {_SIGNED64_MAX}"
        )
    position = _WINDOW_COUNT_POSITIONS.get(name)
    arguments = expression.call.arguments
    if position is not None and position < len(arguments):
        count = arguments[position]
        if (
            type(count) is LiteralExpr
            and type(count.value) is int
            and count.value > _SIGNED64_MAX
        ):
            messages.append(
                f"Invalid arguments for function {name}: integer literal must not "
                f"exceed {_SIGNED64_MAX}"
            )
    span = expression.call.span
    return [
        Diagnostic(
            code="PIE-S2104",
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
        for message in messages
    ]


def _reads_erroneous_let(
    expression: Expression,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression],
    erroneous_lets: set[str],
) -> bool:
    """Whether the expression reads, through `let:` names, an erroneous let."""

    pending = [expression]
    expanded: set[str] = set()
    while pending:
        node = pending.pop()
        if type(node) is NameExpr and node.name not in input_schema.fields:
            if node.name in erroneous_lets:
                return True
            if node.name in let_expressions and node.name not in expanded:
                expanded.add(node.name)
                pending.append(let_expressions[node.name])
            continue
        pending.extend(_captured_field_children(node))
    return False


def _let_names_with_diagnostics(
    definition: TableDef | QueryDef,
    diagnostics: Sequence[Diagnostic],
) -> set[str]:
    """Return the relation's let names whose binding has a diagnostic."""

    if definition.let_clause is None:
        return set()
    return {
        binding.name
        for binding in definition.let_clause.bindings
        for diagnostic in diagnostics
        if (location := diagnostic.location) is not None
        and location.path == binding.span.path
        and (binding.span.line, binding.span.column)
        <= (location.line, location.column)
        < (binding.span.end_line, binding.span.end_column)
    }


def let_value(
    expression: Expression,
    row_schema: RowSchema,
    let_expressions: Mapping[str, Expression] | None,
) -> Expression:
    """Follow bare `let:` names, never input fields, to the inlined expression."""

    expanded: set[str] = set()
    while (
        type(expression) is NameExpr
        and let_expressions
        and expression.name in let_expressions
        and expression.name not in row_schema.fields
        and expression.name not in expanded
    ):
        expanded.add(expression.name)
        expression = let_expressions[expression.name]
    return expression


def _order_key_problem(
    expression: Expression,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression],
    *,
    aggregated: bool,
) -> str | None:
    """Return why a target would misread or reject an ungrouped ORDER BY key.

    After `let:` inlining and unary signs a bare constant remains: PostgreSQL
    and MySQL read an integer as a column position, and PostgreSQL rejects any
    other bare constant (a computed constant such as `1 + 1` sorts nothing and
    stays accepted). In a query with aggregates and no GROUP BY, a key that
    reads an input field outside an aggregate is rejected by the targets.
    """

    if _is_bare_constant(expression, input_schema, let_expressions):
        return (
            "Constant ORDER BY key: a target reads a bare constant key as a "
            "column position or rejects it"
        )
    if aggregated and _reads_input_field_outside_aggregate(
        expression, input_schema, let_expressions
    ):
        return (
            "ORDER BY key reads an input field outside an aggregate in a query "
            "with aggregates and no GROUP BY, which SQL targets reject"
        )
    return None


def _is_bare_constant(
    expression: Expression,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression] | None,
) -> bool:
    """Return whether a literal remains after `let:` inlining and unary signs."""

    value = let_value(expression, input_schema, let_expressions)
    while type(value) is UnaryExpr and value.operator in {"+", "-"}:
        value = let_value(value.operand, input_schema, let_expressions)
    return type(value) is LiteralExpr


def _reads_input_field_outside_aggregate(
    expression: Expression,
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression],
) -> bool:
    pending = [expression]
    expanded: set[str] = set()
    while pending:
        node = pending.pop()
        if type(node) is NameExpr:
            if node.name in input_schema.fields:
                return True
            if node.name in let_expressions and node.name not in expanded:
                expanded.add(node.name)
                pending.append(let_expressions[node.name])
            continue
        if type(node) is DottedNameExpr:
            return True
        if type(node) is WindowExpr or (
            type(node) is CallExpr and is_semantic_aggregate_call(node)
        ):
            continue
        pending.extend(_captured_field_children(node))
    return False


def _order_key_diagnostic(expression: Expression, message: str) -> Diagnostic:
    span = expression.span
    return Diagnostic(
        code="PIE-S2380",
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


def rejected_let_names(
    definition: TableDef | QueryDef,
    admitted: Mapping[str, object] | None,
) -> frozenset[str]:
    """Return the relation's let names that its scope did not admit.

    PIE-S2329 already reports each such binding, so a read of its name does
    not also report an unknown field.
    """

    if definition.let_clause is None or admitted is None:
        return frozenset()
    return frozenset(
        binding.name
        for binding in definition.let_clause.bindings
        if binding.name not in admitted
    )


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
    relation_columns: Mapping[Expression, ValueType] | None = None,
    captured_value_types: (
        Mapping[ast.CapturedFieldExpr, ValueType | Diagnostic] | None
    ) = None,
) -> ValueType:
    """Infer one row-level expression with optional bare-only local bindings.

    ``relation_columns`` holds the known column type of each ``in`` relation
    read, keyed by its expression; its left value must pair with it.

    Each captured outer field below ``expression`` takes its type from
    ``captured_value_types``, the capture environment of its let; a field its
    outer input lacks maps to that environment's own diagnostic instead.
    """

    refused: list[Diagnostic] = []
    if captured_value_types:
        pending: list[Expression] = [expression]
        while pending:
            node = pending.pop()
            if type(node) is not ast.CapturedFieldExpr:
                pending.extend(reversed(_captured_field_children(node)))
                continue
            if node in value_types:
                continue
            captured = captured_value_types[node]
            if type(captured) is Diagnostic:
                if report_unknown_name:
                    refused.append(captured)
                captured = _UNKNOWN_VALUE_TYPE
            value_types[node] = cast(ValueType, captured)
    start = len(diagnostics)
    value_type = _infer(
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
        relation_columns=relation_columns,
    )
    if refused:
        # A refused captured field reports in source order with the
        # expression's other diagnostics, which keep their own order.
        inferred = diagnostics[start:]
        del diagnostics[start:]
        for diagnostic in inferred:
            while refused and _source_before(refused[0], diagnostic):
                diagnostics.append(refused.pop(0))
            diagnostics.append(diagnostic)
        diagnostics.extend(refused)
    return value_type


def _source_before(first: Diagnostic, second: Diagnostic) -> bool:
    if first.location is None or second.location is None:
        return False
    return (first.location.line, first.location.column) < (
        second.location.line,
        second.location.column,
    )


def _captured_field_children(expression: Expression) -> tuple[Expression, ...]:
    """Direct value children where a captured field read may be written."""

    if isinstance(expression, CallExpr):
        return expression.arguments
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, ConditionalExpr):
        return (expression.when_true, expression.condition, expression.when_false)
    if isinstance(expression, MembershipExpr):
        return (expression.value, *expression.options)
    if isinstance(expression, (CastExpr, ast.RelationMembershipExpr)):
        return (expression.value,)
    if isinstance(expression, (BinaryExpr, ComparisonExpr)):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    if type(expression) in _KNOWN_EXPRESSIONS:
        return ()
    raise AssertionError(f"Unsupported expression: {type(expression).__name__}")


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
    relation_columns: Mapping[Expression, ValueType] | None = None,
) -> ValueType:
    """Infer only the expression forms supported by this scaffold."""

    if type(expression) not in _KNOWN_EXPRESSIONS:
        raise AssertionError(f"Unsupported expression: {type(expression).__name__}")
    existing = value_types.get(expression)
    if existing is not None:
        if expression.argument_of:
            # A caller may seed the type of a read it owns (a captured field,
            # a scalar read, a QUALIFY output); the seed itself stays exact.
            return _check_inlined_argument(
                expression, existing, diagnostics, type_expansions
            )
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
            relation_columns=relation_columns,
        )
    elif isinstance(expression, ast.CapturedFieldExpr):
        # A captured field is typed only by its let's capture environment.
        raise AssertionError("Captured field read lacks its capture environment.")
    elif isinstance(expression, ast.RelationExistsExpr):
        # An existence test is never NULL; its relation is resolved, scheduled
        # and checked by the owner of the relation name, not by this kernel.
        value_type = _builtin_value_type("Bool", EffectiveNullability.NON_NULL)
    elif isinstance(expression, ast.RelationScalarExpr):
        # A scalar read's type is its read block column's, which only the
        # relation-name owner knows; a caller supplies it in ``value_types``.
        value_type = _UNKNOWN_VALUE_TYPE
    elif isinstance(expression, ast.RelationMembershipExpr):
        # The left value is checked here; the read relation is resolved,
        # scheduled and checked by the relation-name owner, which supplies the
        # type of its one column in ``relation_columns`` when it is known, and
        # the pair then follows the literal-list rule. Three-valued IN is NULL
        # for a NULL left value over a non-empty relation and for a NULL
        # candidate without a match, so the result is conservatively nullable.
        left_type = _infer(
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
            relation_columns=relation_columns,
        )
        column = None if relation_columns is None else relation_columns.get(expression)
        if column is not None and _is_null_literal(expression.value):
            # A bare NULL takes the known column's type, as in the literal list.
            contextual = _contextual_null_literal_types(
                (expression.value, expression),
                (left_type, column),
                value_types,
                type_expansions,
            )
            if contextual is not None:
                left_type = contextual[0]
        if left_type.kind is ValueTypeKind.UNKNOWN:
            value_type = _UNKNOWN_VALUE_TYPE
        elif (
            column is not None
            and _shared_canonical_type((left_type, column), type_expansions) is None
        ):
            diagnostics.append(
                _invalid_operator_operands_diagnostic(
                    expression, expected="same canonical membership operands"
                )
            )
            value_type = _UNKNOWN_VALUE_TYPE
        else:
            value_type = _builtin_value_type("Bool", EffectiveNullability.NULLABLE)
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
            relation_columns=relation_columns,
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
            relation_columns=relation_columns,
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
            relation_columns=relation_columns,
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
            relation_columns=relation_columns,
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
            relation_columns=relation_columns,
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
            relation_columns=relation_columns,
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
            relation_columns=relation_columns,
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
            relation_columns=relation_columns,
        )
        if expression.operator in {"like", "not like"}:
            value_type, expected = resolved_like_value_type(left_type, right_type)
            if expected is None and _ends_in_unpaired_like_escape(
                let_value(expression.right, row_schema, bare_value_expressions)
            ):
                expected = (
                    "a pattern that does not end in the escape character ! "
                    "(write !! for a literal !)"
                )
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
            relation_columns=relation_columns,
        )
    else:
        # Unsupported forms remain opaque so calls and arithmetic are not
        # accidentally checked through their child expressions.
        value_type = _UNKNOWN_VALUE_TYPE

    if expression.argument_of:
        value_type = _check_inlined_argument(
            expression, value_type, diagnostics, type_expansions
        )
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
    relation_columns: Mapping[Expression, ValueType] | None,
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
        relation_columns=relation_columns,
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
    relation_columns: Mapping[Expression, ValueType] | None,
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
        relation_columns=relation_columns,
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
        relation_columns=relation_columns,
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
        relation_columns=relation_columns,
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
    relation_columns: Mapping[Expression, ValueType] | None,
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
            relation_columns=relation_columns,
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
    relation_columns: Mapping[Expression, ValueType] | None,
) -> ValueType:
    """Admit only the explicit portable Int-to-Float conversion."""

    diagnostic_count = len(diagnostics)
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
        relation_columns=relation_columns,
    )
    float_target = (
        expression.target.name == "Float"
        and not expression.target.arguments
        and expression.target.nullability is Nullability.IMPLICIT
    )
    if value_type.kind is ValueTypeKind.UNKNOWN:
        # A null operand and the target are known without the operand's type;
        # a silent unknown operand is refused unless the cast is to Float.
        explained = len(diagnostics) > diagnostic_count or row_schema.is_unknown
        # A `let:` name bound to null is the null literal emission inlines.
        null_operand = _is_null_literal(
            let_value(expression.value, row_schema, bare_value_expressions)
        )
        if null_operand or not (explained or float_target):
            diagnostics.append(
                _invalid_cast_diagnostic(
                    expression,
                    value_type,
                    type_expansions,
                    null_operand=null_operand,
                )
            )
        return _UNKNOWN_VALUE_TYPE
    if not float_target or not _is_canonical_builtin(
        value_type, "Int", type_expansions
    ):
        diagnostics.append(
            _invalid_cast_diagnostic(expression, value_type, type_expansions)
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
    relation_columns: Mapping[Expression, ValueType] | None,
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
        relation_columns=relation_columns,
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
        relation_columns=relation_columns,
    )
    if expression.operator == "/":
        # Division reads a type alias as the type it expands to.
        left_type = _canonical_value_type(left_type, type_expansions)
        right_type = _canonical_value_type(right_type, type_expansions)
    result, expected = resolved_binary_value_type(
        expression.operator, left_type, right_type
    )
    if expected is not None:
        diagnostics.append(
            _invalid_operator_operands_diagnostic(expression, expected=expected)
        )
    return result


def _canonical_value_type(
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
) -> ValueType:
    """Return a type alias value as the builtin type it expands to."""

    if (
        value_type.kind is not ValueTypeKind.KNOWN
        or value_type.resolved_type.kind is not TypeKind.TYPE_ALIAS
    ):
        return value_type
    canonical = _canonical_resolved_type(value_type, type_expansions)
    if canonical is None or canonical.kind is not TypeKind.BUILTIN:
        return value_type
    return ValueType(resolved_type=canonical, nullability=value_type.nullability)


def resolved_binary_value_type(
    operator: str, left_type: ValueType, right_type: ValueType
) -> tuple[ValueType, str | None]:
    """Original binary rule; no expression, name lookup or source elaboration."""
    if (
        left_type.kind is ValueTypeKind.UNKNOWN
        or right_type.kind is ValueTypeKind.UNKNOWN
    ):
        return _UNKNOWN_VALUE_TYPE, None
    if operator == "/":
        # SQL division: Int / Int is Int, truncated toward zero, and a Float
        # operand gives Float. A Decimal operand has no decided rule and stays
        # deferred; every other known operand type is not numeric.
        if _is_numeric(left_type) and _is_numeric(right_type):
            name = (
                "Float"
                if _is_builtin(left_type, "Float") or _is_builtin(right_type, "Float")
                else "Int"
            )
            return _builtin_value_type(name, EffectiveNullability.UNKNOWN), None
        if not all(
            _is_numeric(value_type) or _is_builtin(value_type, "Decimal")
            for value_type in (left_type, right_type)
        ):
            return _UNKNOWN_VALUE_TYPE, "numeric operands"
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


def _ends_in_unpaired_like_escape(pattern: Expression) -> bool:
    """Whether a literal LIKE pattern ends in an unpaired `ESCAPE '!'` character.

    PostgreSQL rejects such a pattern and MySQL matches its final `!` literally.
    """

    if type(pattern) is not LiteralExpr or type(pattern.value) is not str:
        return False
    return (len(pattern.value) - len(pattern.value.rstrip("!"))) % 2 == 1


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
    relation_columns: Mapping[Expression, ValueType] | None,
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
            relation_columns=relation_columns,
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
    relation_columns: Mapping[Expression, ValueType] | None,
) -> ValueType:
    """Type one exact built-in call while suppressing Unknown cascades.

    An Unknown argument suppresses only the checks that need its type. When an
    argument reported its own error or the input row is unknown, the call adds
    nothing more; otherwise the name, arity and window checks still run.
    """

    function_name = _callee_name(expression)
    diagnostic_count = len(diagnostics)
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
        relation_columns=relation_columns,
    )
    # An unknown input row or an argument's own error explains an Unknown
    # argument; the call then adds nothing.
    cascade = (len(diagnostics) > diagnostic_count or row_schema.is_unknown) and any(
        argument_type.kind is ValueTypeKind.UNKNOWN for argument_type in argument_types
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

    if (
        function_name in {"sign", "year", "month", "day"}
        and any(
            argument_type.kind is ValueTypeKind.UNKNOWN
            for argument_type in argument_types
        )
        and (cascade or len(argument_types) == 1)
    ):
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
        if cascade:
            return _UNKNOWN_VALUE_TYPE
        from pietto.semantic.window_semantics import WINDOW_FUNCTION_NAMES

        if function_name in WINDOW_FUNCTION_NAMES:
            diagnostics.append(
                _window_without_spec_diagnostic(expression, function_name)
            )
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
    relation_columns: Mapping[Expression, ValueType] | None,
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
            relation_columns=relation_columns,
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
            relation_columns=relation_columns,
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
        | ast.RelationMembershipExpr
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
    elif isinstance(expression, (MembershipExpr, ast.RelationMembershipExpr)):
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


def _invalid_cast_diagnostic(
    expression: CastExpr,
    value_type: ValueType,
    type_expansions: Mapping[TypeExpr, ResolvedType] | None,
    *,
    null_operand: bool = False,
) -> Diagnostic:
    """Report a rejected explicit conversion, echoing the attempted pair."""

    if value_type.kind is ValueTypeKind.UNKNOWN:
        source = "null" if null_operand else "unknown"
    else:
        canonical = _canonical_resolved_type(value_type, type_expansions)
        source = (value_type.resolved_type if canonical is None else canonical).name
    target = _type_expression_text(expression.target)
    span = expression.span
    return Diagnostic(
        code="PIE-S2105",
        severity=Severity.ERROR,
        message=(
            f"Invalid cast: cast({source} as {target}) is not supported; "
            "expected cast(Int as Float), the only supported cast"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _type_expression_text(type_expr: TypeExpr) -> str:
    """Render an authored type with its arguments and nullability marker."""

    text = type_expr.name
    if type_expr.arguments:
        text += f"({', '.join(map(_type_argument_text, type_expr.arguments))})"
    if type_expr.nullability is Nullability.NULLABLE:
        return f"{text} nullable"
    if type_expr.nullability is Nullability.NOT_NULL:
        return f"{text} not null"
    return text


def _type_argument_text(argument: ast.TypeArgument) -> str:
    """Render numeric literal arguments; elide any other argument value."""

    value = argument.value
    text = (
        str(value.value)
        if type(value) is LiteralExpr and type(value.value) in (int, float)
        else "..."
    )
    return text if argument.name is None else f"{argument.name} = {text}"


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


def _names_window_output(definition: TableDef | QueryDef, name: str) -> bool:
    return any(
        type(item.expression) is WindowExpr and item.alias == name
        for item in definition.select_items
    )


def _order_by_output_name_diagnostic(
    expression: NameExpr,
    outputs: tuple[Expression, ...],
    input_schema: RowSchema,
    let_expressions: Mapping[str, Expression] | None,
) -> Diagnostic:
    """Report an ungrouped ORDER BY key that names only a SELECT output.

    ``outputs`` are the expressions selected under that name. An aggregate is
    refused in an ungrouped ORDER BY key and in `let:` too, so for an
    aggregate output the remedy is the grouped form instead; a bare constant
    key is refused (PIE-S2380), so a constant output gets no remedy.
    """

    span = expression.span
    if any(contains_semantic_aggregate(output) for output in outputs):
        remedy = (
            ", and an aggregate output cannot be ordered there (a grouped "
            "query can order by its name)"
        )
    elif any(
        _is_bare_constant(output, input_schema, let_expressions) for output in outputs
    ):
        remedy = ", and a constant output sorts nothing and cannot be an ORDER BY key"
    else:
        remedy = " (restate its expression or bind it in `let:`)"
    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=(
            f"Unknown field: {expression.name}; outside a grouped query an "
            f"ORDER BY key cannot name a SELECT output{remedy}"
        ),
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


def _window_without_spec_diagnostic(
    expression: CallExpr,
    function_name: str,
) -> Diagnostic:
    """Report a window function called without a window specification."""

    call = f"{function_name}({'...' if expression.arguments else ''})"
    return _call_diagnostic(
        expression,
        code="PIE-S2103",
        message=(
            f"Window function needs a `window` specification: {function_name} "
            f"(write `{call} window:` in a SELECT item, with an indented "
            "`order by:`)"
        ),
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
