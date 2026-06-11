"""Internal MySQL rendering for the approved Semantic IR expressions."""

from __future__ import annotations

from pietto.ir.model import (
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    SymbolId,
    SymbolNamespace,
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
