"""Private semantic analysis for the bounded row_number window subset."""

from __future__ import annotations

from pietto._window_identity import WindowFunctionIdentity, WindowFunctionRole
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    NameExpr,
    QueryDef,
    SelectItem,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import contains_semantic_aggregate
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.generic_compatibility import (
    ConcreteTypeExpression,
    GenericSignature,
    LogicalTypeIdentity,
    SignatureMatch,
    bind_signature,
)
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.nullability_formulas import (
    NonNullFormula,
    NullabilityEvaluationContext,
    NullabilityEvaluationMatch,
    SignatureResultFormula,
    evaluate_signature_result_nullability,
)
from pietto.semantic.window_semantics import (
    WindowExpressionSemanticFact,
    WindowExpressionUnsupported,
    WindowOccurrenceIdentity,
    WindowResultAvailability,
    WindowResultAvailabilityKind,
)

__all__: tuple[str, ...] = ()

_ROW_NUMBER_RESULT_IDENTITY = LogicalTypeIdentity(
    name="Int",
    kind=TypeKind.BUILTIN,
)
_ROW_NUMBER_SIGNATURE = GenericSignature(
    type_variables=(),
    parameters=(),
    result=ConcreteTypeExpression(logical_type=_ROW_NUMBER_RESULT_IDENTITY),
)
_ROW_NUMBER_RESULT_FORMULA = SignatureResultFormula(
    signature=_ROW_NUMBER_SIGNATURE,
    nullability=NonNullFormula(),
)


def analyze_row_number_window_expression(
    *,
    definition: TableDef | QueryDef,
    item: SelectItem,
    selected_output_ordinal: int,
    source_id: str,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
) -> WindowExpressionSemanticFact | WindowExpressionUnsupported:
    """Analyze one direct selected row_number expression without publishing it."""

    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("definition must be an exact TableDef or QueryDef")
    if type(item) is not SelectItem:
        raise TypeError("item must be an exact SelectItem")
    if type(item.expression) is not WindowExpr:
        raise TypeError("item expression must be an exact WindowExpr")
    if type(input_schema) is not RowSchema:
        raise TypeError("input_schema must be an exact RowSchema")
    if type(field_qualifier) is not str:
        raise TypeError("field_qualifier must be an exact string")
    if type(value_types) is not dict:
        raise TypeError("value_types must be an exact dict")
    if type(diagnostics) is not list:
        raise TypeError("diagnostics must be an exact list")

    expression = item.expression
    occurrence = WindowOccurrenceIdentity(
        source_id=source_id,
        relation_name=definition.name,
        selected_output_ordinal=selected_output_ordinal,
        span=expression.span,
    )

    if not _is_exact_row_number_identity(expression):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="unsupported window function identity",
            diagnostics=diagnostics,
        )

    if expression.call.arguments:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="row_number requires zero arguments",
            diagnostics=diagnostics,
            code="PIE-S2104",
            message=(
                "Invalid arguments for function row_number: expected 0, got "
                f"{len(expression.call.arguments)}"
            ),
        )

    if item.alias is None:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="row_number requires a direct selected output alias",
            diagnostics=diagnostics,
        )

    if (
        definition.group_by_clause is not None
        or definition.satisfying_clause is not None
        or definition.let_clause is not None
        or any(
            contains_semantic_aggregate(selected.expression)
            for selected in definition.select_items
        )
    ):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="relation context does not admit row_number",
            diagnostics=diagnostics,
        )

    if (
        sum(
            type(selected.expression) is WindowExpr
            for selected in definition.select_items
        )
        != 1
    ):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="relation requires exactly one window output",
            diagnostics=diagnostics,
        )

    if expression.spec.partition_by:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="row_number partitioning is deferred",
            diagnostics=diagnostics,
        )

    if len(expression.spec.order_by) != 1:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="row_number requires exactly one window order field",
            diagnostics=diagnostics,
        )

    order_item = expression.spec.order_by[0]
    if order_item.direction is not None:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="explicit window order direction is deferred",
            diagnostics=diagnostics,
        )

    order_expression = order_item.expression
    if not isinstance(order_expression, (NameExpr, DottedNameExpr)):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="window order expression must be a direct field",
            diagnostics=diagnostics,
        )

    if input_schema.is_unknown:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="window input schema must be concrete",
            diagnostics=diagnostics,
        )

    diagnostics_before = len(diagnostics)
    order_value_type = infer_row_expression(
        order_expression,
        input_schema,
        value_types,
        diagnostics,
        report_unknown_name=True,
        field_qualifier=field_qualifier,
    )
    if (
        order_value_type.kind is ValueTypeKind.UNKNOWN
        or order_value_type.resolved_type.kind is TypeKind.UNKNOWN
    ):
        if len(diagnostics) == diagnostics_before:
            _append_call_diagnostic(
                diagnostics,
                expression.call,
                code="PIE-S2103",
                message=f"Unknown function: {_source_function_name(expression.call)}",
            )
        return WindowExpressionUnsupported(
            occurrence=occurrence,
            expression=expression,
            identity=expression.identity,
            reason="window order field type must be concrete",
        )

    signature_match = bind_signature(_ROW_NUMBER_SIGNATURE, ())
    if type(signature_match) is not SignatureMatch:
        raise AssertionError("row_number signature must bind without arguments")
    nullability_match = evaluate_signature_result_nullability(
        _ROW_NUMBER_RESULT_FORMULA,
        NullabilityEvaluationContext(
            argument_nullabilities=(),
            omitted_positions=(),
        ),
    )
    if type(nullability_match) is not NullabilityEvaluationMatch:
        raise AssertionError("row_number nullability formula must evaluate")

    result_type = ValueType(
        resolved_type=ResolvedType(
            name=signature_match.result_type.name,
            kind=signature_match.result_type.kind,
        ),
        nullability=nullability_match.value,
    )
    if result_type.nullability is not EffectiveNullability.NON_NULL:
        raise AssertionError("row_number result must be non-null")
    return WindowExpressionSemanticFact(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        result=WindowResultAvailability(
            kind=WindowResultAvailabilityKind.CONCRETE,
            value_type=result_type,
        ),
    )


def _is_exact_row_number_identity(expression: WindowExpr) -> bool:
    identity = expression.identity
    callee = expression.call.callee
    return (
        identity
        == WindowFunctionIdentity(
            namespace=(),
            name="row_number",
            role=WindowFunctionRole.WINDOW_FUNCTION,
        )
        and type(callee) is NameExpr
        and callee.name == "row_number"
    )


def _unsupported(
    *,
    occurrence: WindowOccurrenceIdentity,
    expression: WindowExpr,
    reason: str,
    diagnostics: list[Diagnostic],
    code: str = "PIE-S2103",
    message: str | None = None,
) -> WindowExpressionUnsupported:
    _append_call_diagnostic(
        diagnostics,
        expression.call,
        code=code,
        message=message
        or f"Unknown function: {_source_function_name(expression.call)}",
    )
    return WindowExpressionUnsupported(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        reason=reason,
    )


def _source_function_name(call: CallExpr) -> str:
    if type(call.callee) is NameExpr:
        return call.callee.name
    assert isinstance(call.callee, DottedNameExpr)
    return ".".join(call.callee.parts)


def _append_call_diagnostic(
    diagnostics: list[Diagnostic],
    call: CallExpr,
    *,
    code: str,
    message: str,
) -> None:
    span = call.span
    diagnostics.append(
        Diagnostic(
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
    )
