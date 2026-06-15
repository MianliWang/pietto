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
    if expression.function != "count":
        raise ValueError(
            f"Unsupported PostgreSQL aggregate call: {expression.function}"
        )
    if expression.arguments:
        raise ValueError("PostgreSQL aggregate count expects 0 argument(s)")
    return "COUNT(*)"


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
