"""Private bounded argument analysis for lag and lead navigation windows."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeGuard

from pietto._window_identity import WindowFunctionIdentity, WindowFunctionRole
from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.generic_compatibility import (
    ConcreteTypeExpression,
    GenericSignature,
    LogicalTypeIdentity,
    ParameterDefault,
    SignatureMatch,
    SignatureParameter,
    TypeVariable,
    VariableTypeExpression,
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
    AlwaysNullableFormula,
    AnyNullableFormula,
    AnyOfFormula,
    NullabilityEvaluationContext,
    NullabilityEvaluationMatch,
    NullableIfDefaultOmittedFormula,
    SameAsArgumentFormula,
    SignatureResultFormula,
    evaluate_signature_result_nullability,
)
from pietto.semantic.window_semantics import (
    NavigationDefaultFact,
    NavigationDirection,
    NavigationOffsetFact,
    NavigationWindowSemanticFact,
    WindowExpressionSemanticFact,
    WindowExpressionUnsupported,
    WindowOccurrenceIdentity,
    WindowResultAvailability,
    WindowResultAvailabilityKind,
)

__all__: tuple[str, ...] = ()

_INT_IDENTITY = LogicalTypeIdentity(name="Int", kind=TypeKind.BUILTIN)
_TYPE_VARIABLE = TypeVariable(name="T", constraints=())
_TYPE_REFERENCE = VariableTypeExpression(name="T")
_NAVIGATION_SIGNATURE = GenericSignature(
    type_variables=(_TYPE_VARIABLE,),
    parameters=(
        SignatureParameter(position=0, type_expression=_TYPE_REFERENCE),
        SignatureParameter(
            position=1,
            type_expression=ConcreteTypeExpression(logical_type=_INT_IDENTITY),
            optional=True,
            default=ParameterDefault.OMITTED,
        ),
        SignatureParameter(
            position=2,
            type_expression=_TYPE_REFERENCE,
            optional=True,
            default=ParameterDefault.OMITTED,
        ),
    ),
    result=_TYPE_REFERENCE,
)
_BOUNDARY_RESULT_FORMULA = SignatureResultFormula(
    signature=_NAVIGATION_SIGNATURE,
    nullability=AnyOfFormula(
        children=(
            AnyNullableFormula(argument_indices=(0, 2)),
            NullableIfDefaultOmittedFormula(parameter_index=2),
        )
    ),
)
_ZERO_RESULT_FORMULA = SignatureResultFormula(
    signature=_NAVIGATION_SIGNATURE,
    nullability=SameAsArgumentFormula(argument_index=0),
)
_ZERO_ALWAYS_NULL_RESULT_FORMULA = SignatureResultFormula(
    signature=_NAVIGATION_SIGNATURE,
    nullability=AlwaysNullableFormula(),
)

_NAVIGATION_IDENTITIES = (
    (
        WindowFunctionIdentity(
            namespace=(),
            name="lag",
            role=WindowFunctionRole.WINDOW_FUNCTION,
        ),
        NavigationDirection.LAG,
    ),
    (
        WindowFunctionIdentity(
            namespace=(),
            name="lead",
            role=WindowFunctionRole.WINDOW_FUNCTION,
        ),
        NavigationDirection.LEAD,
    ),
)

type BoundedNavigationExpression = NameExpr | DottedNameExpr | LiteralExpr


def navigation_direction(expression: WindowExpr) -> NavigationDirection | None:
    """Return the exact recognized lowercase unqualified navigation identity."""

    if type(expression) is not WindowExpr:
        raise TypeError("expression must be an exact WindowExpr")
    callee = expression.call.callee
    if type(callee) is not NameExpr:
        return None
    for identity, direction in _NAVIGATION_IDENTITIES:
        if expression.identity == identity and callee.name == identity.name:
            return direction
    return None


def analyze_navigation_arguments(
    *,
    occurrence: WindowOccurrenceIdentity,
    expression: WindowExpr,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    bare_value_types: Mapping[str, ValueType] | None = None,
    allow_qualified_fields: bool = True,
) -> NavigationWindowSemanticFact | WindowExpressionUnsupported:
    """Analyze bounded value, offset, default, generic, and nullability facts."""

    if type(occurrence) is not WindowOccurrenceIdentity:
        raise TypeError("occurrence must be an exact WindowOccurrenceIdentity")
    if type(expression) is not WindowExpr:
        raise TypeError("expression must be an exact WindowExpr")
    if type(input_schema) is not RowSchema:
        raise TypeError("input_schema must be an exact RowSchema")
    if type(field_qualifier) is not str:
        raise TypeError("field_qualifier must be an exact string")
    if type(value_types) is not dict:
        raise TypeError("value_types must be an exact dict")
    if type(diagnostics) is not list:
        raise TypeError("diagnostics must be an exact list")

    direction = navigation_direction(expression)
    if direction is None:
        raise ValueError("navigation argument analysis requires lag or lead")
    arguments = expression.call.arguments
    if len(arguments) not in {1, 2, 3}:
        raise ValueError("navigation arity must be validated before arguments")

    value_expression = arguments[0]
    if not _is_bounded_value_expression(
        value_expression,
        field_qualifier,
        allow_qualified_fields=allow_qualified_fields,
    ):
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="navigation value must be a direct field or scalar literal",
            diagnostics=diagnostics,
            message=(
                f"Invalid arguments for function {direction.value}: value must be "
                "a direct field or Bool, Text, Int, Float, or NULL literal"
            ),
        )
    value_before = len(diagnostics)
    value_type = infer_row_expression(
        value_expression,
        input_schema,
        value_types,
        diagnostics,
        report_unknown_name=True,
        field_qualifier=field_qualifier if allow_qualified_fields else "",
        bare_value_types=bare_value_types,
    )
    value_always_null = _is_null_literal(value_expression)
    if not value_always_null and not _is_concrete_value_type(value_type):
        return _unsupported_after_inference(
            occurrence=occurrence,
            expression=expression,
            reason="navigation value type must be concrete",
            diagnostics=diagnostics,
            diagnostics_before=value_before,
            message=(
                f"Invalid arguments for function {direction.value}: value type must "
                "be concrete"
            ),
        )

    if len(arguments) == 1:
        offset_fact = NavigationOffsetFact(
            expression=None,
            effective_value=1,
            span=expression.call.span,
        )
    else:
        offset_expression = arguments[1]
        if (
            type(offset_expression) is not LiteralExpr
            or type(offset_expression.value) is not int
            or offset_expression.value < 0
        ):
            return _unsupported(
                occurrence=occurrence,
                expression=expression,
                reason="navigation offset must be a nonnegative integer literal",
                diagnostics=diagnostics,
                message=(
                    f"Invalid arguments for function {direction.value}: offset must "
                    "be a nonnegative integer literal"
                ),
            )
        offset_fact = NavigationOffsetFact(
            expression=offset_expression,
            effective_value=offset_expression.value,
            span=offset_expression.span,
        )

    default_type: ValueType | None = None
    default_always_null = False
    if len(arguments) < 3:
        default_fact = NavigationDefaultFact(
            expression=None,
            value_type=None,
            always_null=False,
            span=expression.call.span,
        )
    else:
        default_expression = arguments[2]
        if not _is_bounded_value_expression(
            default_expression,
            field_qualifier,
            allow_qualified_fields=allow_qualified_fields,
        ):
            return _unsupported(
                occurrence=occurrence,
                expression=expression,
                reason="navigation default must be a direct field or scalar literal",
                diagnostics=diagnostics,
                message=(
                    f"Invalid arguments for function {direction.value}: default must "
                    "be a direct field or Bool, Text, Int, Float, or NULL literal"
                ),
            )
        default_before = len(diagnostics)
        default_type = infer_row_expression(
            default_expression,
            input_schema,
            value_types,
            diagnostics,
            report_unknown_name=True,
            field_qualifier=field_qualifier if allow_qualified_fields else "",
            bare_value_types=bare_value_types,
        )
        default_always_null = _is_null_literal(default_expression)
        if not default_always_null and not _is_concrete_value_type(default_type):
            return _unsupported_after_inference(
                occurrence=occurrence,
                expression=expression,
                reason="navigation default type must be concrete",
                diagnostics=diagnostics,
                diagnostics_before=default_before,
                message=(
                    f"Invalid arguments for function {direction.value}: default type "
                    "must be concrete"
                ),
            )
        default_fact = NavigationDefaultFact(
            expression=default_expression,
            value_type=default_type,
            always_null=default_always_null,
            span=default_expression.span,
        )

    value_identity = None if value_always_null else _logical_type_identity(value_type)
    default_identity = (
        None
        if default_fact.omitted or default_always_null
        else _logical_type_identity(default_type)
    )
    binding_identity = value_identity or default_identity
    if binding_identity is None:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="navigation type variable T is unbound",
            diagnostics=diagnostics,
            message=(
                f"Invalid arguments for function {direction.value}: type variable T "
                "requires a non-NULL value or default"
            ),
        )

    signature_arguments: list[LogicalTypeIdentity] = [
        value_identity or binding_identity
    ]
    if len(arguments) >= 2:
        signature_arguments.append(_INT_IDENTITY)
    if len(arguments) == 3:
        signature_arguments.append(default_identity or binding_identity)
    signature_result = bind_signature(
        _NAVIGATION_SIGNATURE,
        tuple(signature_arguments),
    )
    if type(signature_result) is not SignatureMatch:
        return _unsupported(
            occurrence=occurrence,
            expression=expression,
            reason="navigation value and default types must match exactly",
            diagnostics=diagnostics,
            message=(
                f"Invalid arguments for function {direction.value}: value and "
                "default must have the same exact type"
            ),
        )

    argument_nullabilities = [
        (EffectiveNullability.NULLABLE if value_always_null else value_type.nullability)
    ]
    if len(arguments) >= 2:
        argument_nullabilities.append(EffectiveNullability.NON_NULL)
    if len(arguments) == 3:
        assert default_type is not None
        argument_nullabilities.append(
            (
                EffectiveNullability.NULLABLE
                if default_always_null
                else default_type.nullability
            )
        )
    result_formula = (
        _ZERO_ALWAYS_NULL_RESULT_FORMULA
        if offset_fact.effective_value == 0 and value_always_null
        else _ZERO_RESULT_FORMULA
        if offset_fact.effective_value == 0
        else _BOUNDARY_RESULT_FORMULA
    )
    nullability_result = evaluate_signature_result_nullability(
        result_formula,
        NullabilityEvaluationContext(
            argument_nullabilities=tuple(argument_nullabilities),
            omitted_positions=signature_result.omitted_positions,
        ),
    )
    if type(nullability_result) is not NullabilityEvaluationMatch:
        raise AssertionError("navigation nullability formula must evaluate")

    result_type = ValueType(
        resolved_type=ResolvedType(
            name=signature_result.result_type.name,
            kind=signature_result.result_type.kind,
        ),
        nullability=nullability_result.value,
    )
    semantic_fact = WindowExpressionSemanticFact(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        result=WindowResultAvailability(
            kind=WindowResultAvailabilityKind.CONCRETE,
            value_type=result_type,
        ),
    )
    return NavigationWindowSemanticFact(
        semantic_fact=semantic_fact,
        direction=direction,
        value_expression=value_expression,
        value_type=value_type,
        value_always_null=value_always_null,
        offset_fact=offset_fact,
        default_fact=default_fact,
        signature_match=signature_result,
        nullability_match=nullability_result,
    )


def _is_bounded_value_expression(
    expression: Expression,
    field_qualifier: str,
    *,
    allow_qualified_fields: bool,
) -> TypeGuard[BoundedNavigationExpression]:
    if type(expression) is NameExpr:
        return True
    if type(expression) is DottedNameExpr:
        return len(expression.parts) == 2 and (
            not allow_qualified_fields or expression.parts[0] == field_qualifier
        )
    if type(expression) is not LiteralExpr:
        return False
    return expression.value is None or type(expression.value) in {
        bool,
        str,
        int,
        float,
    }


def _is_null_literal(expression: Expression) -> bool:
    return type(expression) is LiteralExpr and expression.value is None


def _is_concrete_value_type(value_type: ValueType) -> bool:
    return (
        value_type.kind is ValueTypeKind.KNOWN
        and value_type.resolved_type.kind
        in {TypeKind.BUILTIN, TypeKind.ENUM, TypeKind.SHAPE}
        and value_type.nullability
        in {EffectiveNullability.NON_NULL, EffectiveNullability.NULLABLE}
    )


def _logical_type_identity(value_type: ValueType | None) -> LogicalTypeIdentity:
    if value_type is None or not _is_concrete_value_type(value_type):
        raise ValueError("logical identity requires one concrete value type")
    return LogicalTypeIdentity(
        name=value_type.resolved_type.name,
        kind=value_type.resolved_type.kind,
    )


def _unsupported_after_inference(
    *,
    occurrence: WindowOccurrenceIdentity,
    expression: WindowExpr,
    reason: str,
    diagnostics: list[Diagnostic],
    diagnostics_before: int,
    message: str,
) -> WindowExpressionUnsupported:
    if len(diagnostics) == diagnostics_before:
        _append_call_diagnostic(diagnostics, expression.call, message=message)
    return WindowExpressionUnsupported(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        reason=reason,
    )


def _unsupported(
    *,
    occurrence: WindowOccurrenceIdentity,
    expression: WindowExpr,
    reason: str,
    diagnostics: list[Diagnostic],
    message: str,
) -> WindowExpressionUnsupported:
    _append_call_diagnostic(diagnostics, expression.call, message=message)
    return WindowExpressionUnsupported(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        reason=reason,
    )


def _append_call_diagnostic(
    diagnostics: list[Diagnostic],
    call: CallExpr,
    *,
    message: str,
) -> None:
    span = call.span
    diagnostics.append(
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
    )
