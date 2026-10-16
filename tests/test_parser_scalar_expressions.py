from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import CommonToken
from antlr4.tree.Tree import TerminalNodeImpl

from pietto.ast_builder import AstBuilder

from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    CastExpr,
    ComparisonExpr,
    ConditionalExpr,
    DottedNameExpr,
    MembershipExpr,
    NameExpr,
    QueryDef,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    Span,
    TableDef,
    TypeDef,
    UnaryExpr,
)
from pietto.generated.PiettoParser import PiettoParser
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


def test_relation_references_are_distinct_from_lists_calls_and_names() -> None:
    expression = _ensure_expression("id not in vip and exists recent")

    assert type(expression) is BinaryExpr
    membership, exists = expression.left, expression.right
    assert type(membership) is RelationMembershipExpr
    assert (membership.relation_name, membership.negated) == ("vip", True)
    assert type(membership.value) is NameExpr
    assert membership.span == Span(
        path="scalar.pietto", line=1, column=27, end_line=1, end_column=40
    )
    assert type(exists) is RelationExistsExpr
    assert exists.relation_name == "recent"
    assert exists.span == Span(
        path="scalar.pietto", line=1, column=45, end_line=1, end_column=58
    )

    negated = _ensure_expression("not exists recent")
    assert type(negated) is UnaryExpr
    assert type(negated.operand) is RelationExistsExpr

    listed = _ensure_expression("id in (vip)")
    assert type(listed) is MembershipExpr
    assert [type(option) for option in listed.options] == [NameExpr]
    call = _ensure_expression("exists(recent)")
    assert type(call) is CallExpr and type(call.callee) is NameExpr
    assert call.callee.name == "exists"


def test_scalar_reads_exactly_one_relation_column() -> None:
    expression = _ensure_expression("total == scalar customer_top.top")

    assert type(expression) is ComparisonExpr
    read = expression.right
    assert type(read) is RelationScalarExpr
    assert (read.relation_name, read.column_name) == ("customer_top", "top")
    assert read.span == Span(
        path="scalar.pietto", line=1, column=36, end_line=1, end_column=59
    )
    call = _ensure_expression("scalar(total)")
    assert type(call) is CallExpr and type(call.callee) is NameExpr
    nested = _ensure_expression("scalar t.a in r")
    assert type(nested) is RelationMembershipExpr
    assert type(nested.value) is RelationScalarExpr


@pytest.mark.parametrize(
    "text",
    [
        "scalar last_day",
        "scalar a.b.c",
        "id in vip.id",
        "exists a.b",
        "id in f(1)",
    ],
)
def test_unlisted_relation_reference_spellings_are_syntax_errors(text: str) -> None:
    result = parse_source(f"type Result = Bool ensure {text}\n")

    assert result.ast is None
    assert any(item.code == "PIE-P1000" for item in result.diagnostics)


def test_new_words_remain_ordinary_names_and_order_columns() -> None:
    expression = _ensure_expression("values == exists and capture.scalar")

    assert type(expression) is BinaryExpr
    comparison = expression.left
    assert type(comparison) is ComparisonExpr
    assert [comparison.left, comparison.right] == [
        NameExpr(span=comparison.left.span, name="values"),
        NameExpr(span=comparison.right.span, name="exists"),
    ]
    assert type(expression.right) is DottedNameExpr
    assert expression.right.parts == ("capture", "scalar")

    result = parse_source(
        "query q:\n"
        "    from rows\n"
        "    select:\n"
        "        values = count(value)\n"
        "    order by:\n"
        "        exists asc\n"
        "        scalar desc\n"
    )
    assert result.diagnostics == () and result.ast is not None
    query = result.ast.definitions[0]
    assert type(query) is QueryDef and query.order_by_clause is not None
    assert query.select_items[0].alias == "values"
    assert [
        (type(item.expression), item.direction) for item in query.order_by_clause.items
    ] == [(NameExpr, "asc"), (NameExpr, "desc")]


def test_a_flat_operator_chain_computes_its_span_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contexts: list[str] = []
    span = AstBuilder._span

    def counted(self: AstBuilder, ctx: ParserRuleContext) -> Span:
        contexts.append(type(ctx).__name__)
        return span(self, ctx)

    monkeypatch.setattr(AstBuilder, "_span", counted)
    terms = " + ".join(["1"] * 2000)
    result = parse_source(f"derive total() -> Int not null:\n    {terms}\n")

    assert result.diagnostics == () and result.ast is not None
    assert contexts.count("AdditiveExpressionContext") == 1


class _Children(list[Any]):
    """Children that count how many of them a search touches."""

    touched = 0

    def __iter__(self) -> Iterator[Any]:
        for item in super().__iter__():
            self.touched += 1
            yield item

    def __reversed__(self) -> Iterator[Any]:
        for item in super().__reversed__():
            self.touched += 1
            yield item


class _Node:
    def __init__(self, children: _Children) -> None:
        self.children = children


def test_the_last_significant_token_search_touches_only_trailing_nodes() -> None:
    token = CommonToken(type=PiettoParser.IDENTIFIER)
    token.text = "x"
    children = _Children(
        [*(_Node(_Children()) for _ in range(5000)), TerminalNodeImpl(token)]
    )

    assert AstBuilder._last_significant_token(_Node(children)) is token
    assert children.touched == 1
