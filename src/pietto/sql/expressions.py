"""Internal PostgreSQL rendering for the supported Semantic IR expressions."""

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
    TypeKindIR,
    UnaryIR,
)
from pietto.sql.render import (
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
    "lower": "lower",
    "trim": "trim",
    "len": "length",
}
_FUNCTION_ARITIES = {
    "lower": 1,
    "trim": 1,
    "len": 1,
    "matches": 2,
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


def render_expression_sql(expression: ExpressionIR) -> str:
    """Render one supported Semantic IR expression as PostgreSQL SQL."""

    return _render_expression_sql(expression, nested=False)


def expression_uses_qualified_field(expression: ExpressionIR) -> bool:
    """Return whether an expression contains a qualified field reference."""

    if isinstance(expression, FieldRefIR):
        return bool(expression.qualifier)
    if isinstance(expression, AggregateCallIR):
        return any(
            expression_uses_qualified_field(argument)
            for argument in expression.arguments
        )
    if isinstance(expression, CallIR):
        return any(
            expression_uses_qualified_field(argument)
            for argument in expression.arguments
        )
    if isinstance(expression, (ComparisonIR, BinaryIR)):
        return expression_uses_qualified_field(
            expression.left
        ) or expression_uses_qualified_field(expression.right)
    if isinstance(expression, IsNullIR):
        return expression_uses_qualified_field(expression.value)
    if isinstance(expression, BetweenIR):
        return (
            expression_uses_qualified_field(expression.value)
            or expression_uses_qualified_field(expression.lower)
            or expression_uses_qualified_field(expression.upper)
        )
    if isinstance(expression, UnaryIR):
        return expression_uses_qualified_field(expression.operand)
    return False


def _render_expression_sql(expression: ExpressionIR, *, nested: bool) -> str:
    if isinstance(expression, LiteralIR):
        return render_literal(expression.value)
    if isinstance(expression, FieldRefIR):
        if expression.qualifier:
            return quote_qualified_identifier((*expression.qualifier, expression.name))
        return quote_identifier(expression.name)
    if isinstance(expression, AggregateCallIR):
        return _render_aggregate_call(expression)
    if isinstance(expression, CallIR):
        sql = _render_call(expression)
        return f"({sql})" if nested and expression.callee == "matches" else sql
    if isinstance(expression, ComparisonIR):
        operator = _supported_operator(
            _COMPARISON_OPERATORS,
            expression.operator,
            "comparison",
        )
        sql = (
            f"{_render_expression_sql(expression.left, nested=True)} {operator} "
            f"{_render_expression_sql(expression.right, nested=True)}"
        )
    elif isinstance(expression, IsNullIR):
        operator = "IS NOT NULL" if expression.negated else "IS NULL"
        sql = f"{_render_expression_sql(expression.value, nested=True)} {operator}"
    elif isinstance(expression, BetweenIR):
        sql = (
            f"{_render_expression_sql(expression.value, nested=True)} BETWEEN "
            f"{_render_expression_sql(expression.lower, nested=True)} AND "
            f"{_render_expression_sql(expression.upper, nested=True)}"
        )
    elif isinstance(expression, UnaryIR):
        operator = _supported_operator(
            _UNARY_OPERATORS,
            expression.operator,
            "unary",
        )
        sql = f"{operator}{_render_expression_sql(expression.operand, nested=True)}"
    elif isinstance(expression, BinaryIR):
        operator = _supported_operator(
            _BINARY_OPERATORS,
            expression.operator,
            "binary",
        )
        sql = (
            f"{_render_expression_sql(expression.left, nested=True)} {operator} "
            f"{_render_expression_sql(expression.right, nested=True)}"
        )
    else:
        raise ValueError(
            f"Unsupported PostgreSQL expression IR node: {type(expression).__name__}"
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
        raise ValueError(
            f"Unsupported PostgreSQL aggregate call: {expression.function}"
        )
    return _render_numeric_aggregate(expression, function_name=function_name)


def _render_count_aggregate(expression: AggregateCallIR) -> str:
    if not _has_builtin_type(expression, "Int", NullabilityIR.NON_NULL):
        raise ValueError("PostgreSQL aggregate count expects Int non-null result")
    if not expression.arguments:
        return "COUNT(*)"
    if len(expression.arguments) != 1:
        raise ValueError("PostgreSQL aggregate count expects 0 or 1 argument(s)")
    argument = expression.arguments[0]
    if not isinstance(argument, FieldRefIR) or argument.field is None:
        raise ValueError("PostgreSQL aggregate count expects a direct field argument")
    if (
        argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
        or argument.value_type.canonical_name == "Any"
    ):
        raise ValueError(
            "PostgreSQL aggregate count supports only concrete non-Any field arguments"
        )
    return f"COUNT({_render_expression_sql(argument, nested=True)})"


def _render_count_distinct_aggregate(expression: AggregateCallIR) -> str:
    if not _has_builtin_type(expression, "Int", NullabilityIR.NON_NULL):
        raise ValueError(
            "PostgreSQL aggregate count_distinct expects Int non-null result"
        )
    if len(expression.arguments) != 1:
        raise ValueError("PostgreSQL aggregate count_distinct expects 1 argument(s)")
    argument = expression.arguments[0]
    if not isinstance(argument, FieldRefIR) or argument.field is None:
        raise ValueError(
            "PostgreSQL aggregate count_distinct expects a direct field argument"
        )
    argument_type = argument.value_type.canonical_name
    if (
        argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
        or argument_type not in _SUPPORTED_COUNT_DISTINCT_ARGUMENT_TYPES
    ):
        raise ValueError(
            "PostgreSQL aggregate count_distinct supports only Bool, Int, Float, "
            "Decimal, Text, Date, Timestamp, or UUID field arguments"
        )
    return f"COUNT(DISTINCT {_render_expression_sql(argument, nested=True)})"


def _render_numeric_aggregate(
    expression: AggregateCallIR,
    *,
    function_name: str,
) -> str:
    if len(expression.arguments) != 1:
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    if not isinstance(argument, FieldRefIR) or argument.field is None:
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} expects a direct field "
            "argument"
        )
    argument_type = argument.value_type.canonical_name
    if (
        argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
        or argument_type not in _SUPPORTED_NUMERIC_AGGREGATE_ARGUMENT_TYPES
    ):
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} supports only Int, "
            "Float, or Decimal field arguments"
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
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} result type does not "
            "match approved logical shape"
        )
    return f"{function_name}({_render_expression_sql(argument, nested=True)})"


def _render_extrema_aggregate(
    expression: AggregateCallIR,
    *,
    function_name: str,
) -> str:
    if len(expression.arguments) != 1:
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    if not isinstance(argument, FieldRefIR) or argument.field is None:
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} expects a direct field "
            "argument"
        )
    argument_type = argument.value_type.canonical_name
    if (
        argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
        or argument_type not in _SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES
    ):
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} supports only Int, "
            "Float, Decimal, Date, or Timestamp field arguments"
        )

    if not _has_builtin_type(expression, argument_type, NullabilityIR.NULLABLE):
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} result type does not "
            "match approved logical shape"
        )
    return f"{function_name}({_render_expression_sql(argument, nested=True)})"


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
    if expression.callee not in _FUNCTION_ARITIES:
        raise ValueError(f"Unsupported PostgreSQL function call: {expression.callee}")
    expected_arity = _FUNCTION_ARITIES[expression.callee]
    if len(expression.arguments) != expected_arity:
        raise ValueError(
            f"PostgreSQL function {expression.callee} expects "
            f"{expected_arity} argument(s)"
        )

    arguments = tuple(
        _render_expression_sql(argument, nested=True)
        for argument in expression.arguments
    )
    if expression.callee == "matches":
        return f"{arguments[0]} ~ {arguments[1]}"
    return f"{_FUNCTION_NAMES[expression.callee]}({arguments[0]})"


def _supported_operator(
    supported: dict[str, str],
    operator: str,
    kind: str,
) -> str:
    try:
        return supported[operator]
    except KeyError as error:
        raise ValueError(
            f"Unsupported PostgreSQL {kind} operator: {operator}"
        ) from error
