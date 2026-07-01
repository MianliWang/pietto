"""Internal MySQL rendering for the approved Semantic IR expressions."""

from __future__ import annotations

from pietto.ir.model import (
    AggregateCallIR,
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    NullabilityIR,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    UnaryIR,
)
from pietto.sql.mysql_render import (
    MySqlRenderError,
    quote_identifier,
    quote_qualified_identifier,
    render_literal,
)

_COMPARISON_OPERATORS = {
    "==": "=",
    "!=": "<>",
    "<": "<",
    "<=": "<=",
    ">": ">",
    ">=": ">=",
}
_BINARY_OPERATORS = {
    "and": "AND",
    "or": "OR",
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "%": "%",
}
_UNARY_OPERATORS = {
    "+": "+",
    "-": "-",
}
_FUNCTION_NAMES = {
    "lower": "LOWER",
    "trim": "TRIM",
    "len": "CHAR_LENGTH",
}
_NUMERIC_AGGREGATE_NAMES = {
    "sum": "SUM",
    "avg": "AVG",
}
_SUPPORTED_NUMERIC_AGGREGATE_ARGUMENT_TYPES = frozenset({"Int", "Float", "Decimal"})
_EXTREMA_AGGREGATE_NAMES = {
    "min": "MIN",
    "max": "MAX",
}
_SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES = frozenset(
    {"Int", "Float", "Decimal", "Date", "Timestamp"}
)
_SUPPORTED_COUNT_DISTINCT_ARGUMENT_TYPES = frozenset(
    {"Bool", "Int", "Float", "Decimal", "Text", "Date", "Timestamp", "UUID"}
)
_COUNT_DISTINCT_TRANSFORM_NAMES = frozenset({"lower", "trim"})
_COUNT_EXPRESSION_CALL_NAMES = frozenset({"lower", "trim", "len"})


def render_mysql_expression(expression: ExpressionIR) -> str:
    """Render one supported Semantic IR expression as MySQL SQL."""

    return _render_mysql_expression(expression, nested=False)


def _render_mysql_expression(expression: ExpressionIR, *, nested: bool) -> str:
    if isinstance(expression, LiteralIR):
        return render_literal(expression.value)
    if isinstance(expression, FieldRefIR):
        if expression.qualifier:
            return quote_qualified_identifier((*expression.qualifier, expression.name))
        return quote_identifier(expression.name, context="column identifier")
    if isinstance(expression, AggregateCallIR):
        return _render_aggregate_call(expression)
    if isinstance(expression, CallIR):
        return _render_call(expression)
    if isinstance(expression, ComparisonIR):
        operator = _supported_operator(
            _COMPARISON_OPERATORS,
            expression.operator,
            "comparison",
        )
        sql = (
            f"{_render_mysql_expression(expression.left, nested=True)} {operator} "
            f"{_render_mysql_expression(expression.right, nested=True)}"
        )
    elif isinstance(expression, IsNullIR):
        operator = "IS NOT NULL" if expression.negated else "IS NULL"
        sql = f"{_render_mysql_expression(expression.value, nested=True)} {operator}"
    elif isinstance(expression, BetweenIR):
        sql = (
            f"{_render_mysql_expression(expression.value, nested=True)} BETWEEN "
            f"{_render_mysql_expression(expression.lower, nested=True)} AND "
            f"{_render_mysql_expression(expression.upper, nested=True)}"
        )
    elif isinstance(expression, UnaryIR):
        operator = _supported_operator(
            _UNARY_OPERATORS,
            expression.operator,
            "unary",
        )
        sql = f"{operator}{_render_mysql_expression(expression.operand, nested=True)}"
    elif isinstance(expression, BinaryIR):
        operator = _supported_operator(
            _BINARY_OPERATORS,
            expression.operator,
            "binary",
        )
        sql = (
            f"{_render_mysql_expression(expression.left, nested=True)} {operator} "
            f"{_render_mysql_expression(expression.right, nested=True)}"
        )
    else:
        raise MySqlRenderError(
            f"Unsupported MySQL expression IR node: {type(expression).__name__}"
        )

    return f"({sql})" if nested else sql


def _render_aggregate_call(expression: AggregateCallIR) -> str:
    if expression.function == "count":
        return _render_count_aggregate(expression)
    if expression.function == "count_distinct":
        return _render_count_distinct_aggregate(expression)
    function_name = _EXTREMA_AGGREGATE_NAMES.get(expression.function)
    if function_name is not None:
        return _render_extrema_aggregate(expression, function_name=function_name)
    function_name = _NUMERIC_AGGREGATE_NAMES.get(expression.function)
    if function_name is None:
        raise MySqlRenderError(
            f"Unsupported MySQL aggregate call: {expression.function}"
        )
    return _render_numeric_aggregate(expression, function_name=function_name)


def _render_count_aggregate(expression: AggregateCallIR) -> str:
    if not _has_builtin_type(expression, "Int", NullabilityIR.NON_NULL):
        raise MySqlRenderError("MySQL aggregate count expects Int non-null result")
    if not expression.arguments:
        return "COUNT(*)"
    if len(expression.arguments) != 1:
        raise MySqlRenderError("MySQL aggregate count expects 0 or 1 argument(s)")
    argument = expression.arguments[0]
    if (
        isinstance(argument, FieldRefIR)
        and argument.field is not None
        and not (
            argument.value_type.canonical_kind is TypeKindIR.BUILTIN
            and argument.value_type.canonical_name != "Any"
        )
    ):
        raise MySqlRenderError(
            "MySQL aggregate count supports only concrete non-Any field arguments"
        )
    if not _is_count_argument_expression(argument):
        raise MySqlRenderError(
            "MySQL aggregate count expects a direct field argument or approved "
            "field-bearing expression argument"
        )
    return f"COUNT({_render_mysql_expression(argument, nested=True)})"


def _render_count_distinct_aggregate(expression: AggregateCallIR) -> str:
    if not _has_builtin_type(expression, "Int", NullabilityIR.NON_NULL):
        raise MySqlRenderError(
            "MySQL aggregate count_distinct expects Int non-null result"
        )
    if len(expression.arguments) != 1:
        raise MySqlRenderError("MySQL aggregate count_distinct expects 1 argument(s)")
    argument = expression.arguments[0]

    if isinstance(argument, FieldRefIR):
        if argument.field is None:
            raise MySqlRenderError(
                "MySQL aggregate count_distinct expects a resolved field argument"
            )
        argument_type = argument.value_type.canonical_name
        if (
            argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
            or argument_type not in _SUPPORTED_COUNT_DISTINCT_ARGUMENT_TYPES
        ):
            raise MySqlRenderError(
                "MySQL aggregate count_distinct supports only Bool, Int, Float, "
                "Decimal, Text, Date, Timestamp, or UUID field arguments"
            )
    elif not _is_count_distinct_text_transform_argument(argument):
        raise MySqlRenderError(
            "MySQL aggregate count_distinct expects a direct field or lower/trim "
            "Text transform argument"
        )

    return f"COUNT(DISTINCT {_render_mysql_expression(argument, nested=True)})"


def _render_numeric_aggregate(
    expression: AggregateCallIR,
    *,
    function_name: str,
) -> str:
    if len(expression.arguments) != 1:
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    argument_type = _numeric_aggregate_argument_type(argument)
    if argument_type is None:
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects a field-only Int, "
            "Float, or Decimal expression argument"
        )

    if argument_type == "Decimal":
        expected_result_type = "Decimal"
    elif expression.function == "sum" and argument_type == "Int":
        expected_result_type = "Int"
    else:
        expected_result_type = "Float"
    if not _has_builtin_type(
        expression,
        expected_result_type,
        NullabilityIR.NULLABLE,
    ):
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} result type does not match "
            "approved logical shape"
        )
    return f"{function_name}({_render_mysql_expression(argument, nested=True)})"


def _numeric_aggregate_argument_type(expression: ExpressionIR) -> str | None:
    expression_type, has_field, has_literal = _numeric_aggregate_argument_shape(
        expression
    )
    if expression_type is None:
        return None
    if has_literal and (not has_field or expression_type not in {"Int", "Float"}):
        return None
    return expression_type


def _numeric_aggregate_argument_shape(
    expression: ExpressionIR,
) -> tuple[str | None, bool, bool]:
    """Return (builtin type, has resolved field, has Int/Float literal)."""

    expression_type = _builtin_type_name(expression)
    if expression_type not in _SUPPORTED_NUMERIC_AGGREGATE_ARGUMENT_TYPES:
        return None, False, False

    if isinstance(expression, FieldRefIR):
        if expression.field is None:
            return None, False, False
        return expression_type, True, False

    if isinstance(expression, LiteralIR):
        if type(expression.value) is int and expression_type == "Int":
            return expression_type, False, True
        if type(expression.value) is float and expression_type == "Float":
            return expression_type, False, True
        return None, False, False

    if isinstance(expression, UnaryIR):
        if expression.operator not in _UNARY_OPERATORS:
            return None, False, False
        (
            operand_type,
            operand_has_field,
            operand_has_literal,
        ) = _numeric_aggregate_argument_shape(expression.operand)
        if operand_type != expression_type:
            return None, False, False
        return expression_type, operand_has_field, operand_has_literal

    if isinstance(expression, BinaryIR):
        if expression.operator not in {"+", "-", "*"}:
            return None, False, False
        left_type, left_has_field, left_has_literal = _numeric_aggregate_argument_shape(
            expression.left
        )
        right_type, right_has_field, right_has_literal = (
            _numeric_aggregate_argument_shape(expression.right)
        )
        if left_type is None or right_type is None:
            return None, False, False
        if expression_type == "Decimal":
            if (
                expression.operator == "*"
                or left_type != "Decimal"
                or right_type != "Decimal"
            ):
                return None, False, False
            return (
                expression_type,
                left_has_field or right_has_field,
                left_has_literal or right_has_literal,
            )
        if expression_type == "Int":
            if left_type == "Int" and right_type == "Int":
                return (
                    expression_type,
                    left_has_field or right_has_field,
                    left_has_literal or right_has_literal,
                )
            return None, False, False
        if expression_type == "Float" and {left_type, right_type} <= {"Int", "Float"}:
            return (
                expression_type,
                left_has_field or right_has_field,
                left_has_literal or right_has_literal,
            )

    return None, False, False


def _is_count_distinct_text_transform_argument(expression: ExpressionIR) -> bool:
    if not isinstance(expression, CallIR):
        return False
    if _builtin_type_name(expression) != "Text":
        return False
    if expression.callee not in _COUNT_DISTINCT_TRANSFORM_NAMES:
        return False
    expected_symbol = SymbolId(SymbolNamespace.CALLABLE, expression.callee)
    if expression.callee_symbol != expected_symbol:
        return False
    if len(expression.arguments) != 1:
        return False
    argument = expression.arguments[0]
    if isinstance(argument, FieldRefIR):
        return argument.field is not None and _builtin_type_name(argument) == "Text"
    return _is_count_distinct_text_transform_argument(argument)


def _is_count_argument_expression(expression: ExpressionIR) -> bool:
    is_valid, has_field = _count_argument_expression_shape(expression)
    return is_valid and has_field


def _count_argument_expression_shape(
    expression: ExpressionIR,
) -> tuple[bool, bool]:
    """Return (valid shape, has resolved field leaf) for count expressions."""

    if _builtin_type_name(expression) in {None, "Any"}:
        return False, False

    if isinstance(expression, FieldRefIR):
        return expression.field is not None, expression.field is not None
    if isinstance(expression, LiteralIR):
        return True, False
    if isinstance(expression, UnaryIR):
        if expression.operator not in _UNARY_OPERATORS:
            return False, False
        return _count_argument_expression_shape(expression.operand)
    if isinstance(expression, BinaryIR):
        if expression.operator not in {"+", "-", "*", "%", "and", "or"}:
            return False, False
        left_valid, left_has_field = _count_argument_expression_shape(expression.left)
        right_valid, right_has_field = _count_argument_expression_shape(
            expression.right
        )
        return left_valid and right_valid, left_has_field or right_has_field
    if isinstance(expression, CallIR):
        if expression.callee not in _COUNT_EXPRESSION_CALL_NAMES:
            return False, False
        expected_symbol = SymbolId(SymbolNamespace.CALLABLE, expression.callee)
        if expression.callee_symbol != expected_symbol:
            return False, False
        if len(expression.arguments) != 1:
            return False, False
        return _count_argument_expression_shape(expression.arguments[0])
    return False, False


def _builtin_type_name(expression: ExpressionIR) -> str | None:
    if expression.value_type.canonical_kind is not TypeKindIR.BUILTIN:
        return None
    return expression.value_type.canonical_name


def _render_extrema_aggregate(
    expression: AggregateCallIR,
    *,
    function_name: str,
) -> str:
    if len(expression.arguments) != 1:
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    if not isinstance(argument, FieldRefIR) or argument.field is None:
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects a direct field argument"
        )
    argument_type = argument.value_type.canonical_name
    if (
        argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
        or argument_type not in _SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES
    ):
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} supports only Int, Float, "
            "Decimal, Date, or Timestamp field arguments"
        )

    if not _has_builtin_type(expression, argument_type, NullabilityIR.NULLABLE):
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} result type does not match "
            "approved logical shape"
        )
    return f"{function_name}({_render_mysql_expression(argument, nested=True)})"


def _has_builtin_type(
    expression: ExpressionIR,
    canonical_name: str,
    nullability: NullabilityIR,
) -> bool:
    return (
        expression.value_type.canonical_kind is TypeKindIR.BUILTIN
        and expression.value_type.canonical_name == canonical_name
        and expression.value_type.nullability is nullability
    )


def _render_call(expression: CallIR) -> str:
    if expression.callee == "matches":
        raise MySqlRenderError("Unsupported MySQL function call: matches")
    function_name = _FUNCTION_NAMES.get(expression.callee)
    if function_name is None:
        raise MySqlRenderError(f"Unsupported MySQL function call: {expression.callee}")
    expected_symbol = SymbolId(SymbolNamespace.CALLABLE, expression.callee)
    if expression.callee_symbol != expected_symbol:
        raise MySqlRenderError(
            f"Unsupported MySQL function identity: {expression.callee}"
        )
    if len(expression.arguments) != 1:
        raise MySqlRenderError(
            f"MySQL function {expression.callee} expects 1 argument(s)"
        )
    argument = _render_mysql_expression(expression.arguments[0], nested=True)
    return f"{function_name}({argument})"


def _supported_operator(
    supported: dict[str, str],
    operator: str,
    kind: str,
) -> str:
    try:
        return supported[operator]
    except KeyError as error:
        raise MySqlRenderError(
            f"Unsupported MySQL {kind} operator: {operator}"
        ) from error
