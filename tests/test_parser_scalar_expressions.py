from __future__ import annotations

from pietto.ast_nodes import (
    CallExpr,
    CastExpr,
    ComparisonExpr,
    ConditionalExpr,
    MembershipExpr,
    NameExpr,
    TableDef,
    TypeDef,
    UnaryExpr,
)
from pietto.parser_api import parse_source


def _ensure_expression(text: str):
    result = parse_source(f"type Result = Bool ensure {text}\n", path="scalar.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    return definition.ensures[0].expression


def test_conditional_expression_is_lowest_precedence_and_right_associative() -> None:
    expression = _ensure_expression("a if active else b if fallback else c")

    assert isinstance(expression, ConditionalExpr)
    assert isinstance(expression.when_true, NameExpr)
    assert expression.when_true.name == "a"
    assert isinstance(expression.condition, NameExpr)
    assert expression.condition.name == "active"
    assert isinstance(expression.when_false, ConditionalExpr)
    assert expression.span.path == "scalar.pietto"
    assert expression.span.line == 1
    assert expression.span.column == 27


def test_not_wraps_a_comparison_and_not_like_retains_its_operator() -> None:
    expression = _ensure_expression('not name not like "A%"')

    assert isinstance(expression, UnaryExpr)
    assert expression.operator == "not"
    assert isinstance(expression.operand, ComparisonExpr)
    assert expression.operand.operator == "not like"


def test_membership_preserves_order_empty_list_and_negation() -> None:
    expression = _ensure_expression("id in (first, second,)")

    assert isinstance(expression, MembershipExpr)
    assert expression.negated is False
    assert [
        option.name for option in expression.options if isinstance(option, NameExpr)
    ] == [
        "first",
        "second",
    ]

    empty = _ensure_expression("id not in ()")

    assert isinstance(empty, MembershipExpr)
    assert empty.negated is True
    assert empty.options == ()


def test_cast_retains_the_value_and_target_type_spans() -> None:
    expression = _ensure_expression("cast(value as Float)")

    assert isinstance(expression, CastExpr)
    assert isinstance(expression.value, NameExpr)
    assert expression.value.name == "value"
    assert expression.target.name == "Float"
    assert expression.target.span.line == 1
    assert expression.target.span.column == 41


def test_new_expression_keywords_remain_compatible_identifier_and_call_names() -> None:
    expression = _ensure_expression("cast(value)")

    assert isinstance(expression, CallExpr)
    assert isinstance(expression.callee, NameExpr)
    assert expression.callee.name == "cast"
    assert isinstance(expression.arguments[0], NameExpr)

    expression = _ensure_expression("if == else")

    assert isinstance(expression, ComparisonExpr)
    assert isinstance(expression.left, NameExpr)
    assert expression.left.name == "if"
    assert isinstance(expression.right, NameExpr)
    assert expression.right.name == "else"

    expression = _ensure_expression("in == cast")

    assert isinstance(expression, ComparisonExpr)
    assert isinstance(expression.left, NameExpr)
    assert expression.left.name == "in"
    assert isinstance(expression.right, NameExpr)
    assert expression.right.name == "cast"


def test_qualify_uses_the_same_conditional_and_membership_ast_shapes() -> None:
    result = parse_source(
        "table selected:\n"
        "    from rows\n"
        "    select:\n"
        "        value\n"
        "    qualify:\n"
        "        value if active else fallback in (1,)\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TableDef)
    assert definition.qualify_clause is not None
    expression = definition.qualify_clause.expression
    assert isinstance(expression, ConditionalExpr)
    assert isinstance(expression.when_false, MembershipExpr)
