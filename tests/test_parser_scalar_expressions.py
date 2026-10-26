from __future__ import annotations

from collections.abc import Iterator
from dataclasses import fields, replace
from typing import Any

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import CommonToken
from antlr4.tree.Tree import TerminalNodeImpl

from pietto.ast_builder import AstBuilder

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    BlockRelationDef,
    CallExpr,
    ComparisonExpr,
    ConditionalExpr,
    DottedNameExpr,
    Expression,
    MembershipExpr,
    NameExpr,
    QueryDef,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    SelectBody,
    Span,
    TableDef,
    TypeDef,
    UnaryExpr,
)
from pietto.errors import Severity
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


def _expression_nodes(root: Expression) -> list[Expression]:
    nodes: list[Expression] = []
    pending = [root]
    while pending:
        node = pending.pop()
        nodes.append(node)
        pending.extend(
            value
            for value in (getattr(node, item.name) for item in fields(node))
            if isinstance(value, Expression)
        )
    return nodes


def _as_written(node: Expression) -> Expression:
    """``node`` with every span at its written occurrence 0."""

    changes: dict[str, Any] = {
        item.name: _as_written(value)
        for item in fields(node)
        if isinstance(value := getattr(node, item.name), Expression)
    }
    return replace(node, span=replace(node.span, occurrence=0), **changes)


def test_a_comparison_chain_copies_each_inner_operand_as_a_new_occurrence() -> None:
    expression = _ensure_expression("0 < low + 1 <= high < 10")

    assert isinstance(expression, BinaryExpr)
    assert isinstance(expression.left, BinaryExpr)
    comparisons: list[ComparisonExpr] = []
    for item in (expression.left.left, expression.left.right, expression.right):
        assert isinstance(item, ComparisonExpr)
        comparisons.append(item)
    assert [item.operator for item in comparisons] == ["<", "<=", "<"]
    # Each later comparison reads its own copy of the operand before it: the
    # same text, told apart only by its span occurrence.
    for before, after in zip(comparisons, comparisons[1:]):
        assert after.left != before.right
        assert _as_written(after.left) == before.right
    assert [
        (item.left.span.column, item.left.span.occurrence, item.right.span.column)
        for item in comparisons
    ] == [(27, 0, 31), (31, 1, 42), (42, 2, 49)]
    copy = _expression_nodes(comparisons[1].left)
    assert [node.span.occurrence for node in copy] == [1, 1, 1]
    nodes = _expression_nodes(expression)
    assert len(set(nodes)) == len(nodes) == 15


def test_a_chain_in_an_inner_operand_copies_its_own_operand_again() -> None:
    expression = _ensure_expression("True == (0 < x < 10) == True")

    nodes = _expression_nodes(expression)
    assert sorted(
        (node.span.column, node.span.occurrence)
        for node in nodes
        if type(node) is NameExpr
    ) == [(40, 0), (40, 1), (40, 2), (40, 3)]
    assert len(set(nodes)) == len(nodes) == 19


def test_an_inclusive_range_chain_stays_one_between_of_written_operands() -> None:
    expression = _ensure_expression("0 <= x <= 10")

    assert isinstance(expression, BetweenExpr)
    assert isinstance(expression.value, NameExpr)
    assert expression.value.name == "x"
    nodes = _expression_nodes(expression)
    assert [node.span.occurrence for node in nodes] == [0, 0, 0, 0]


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


def test_float_call_retains_the_value_and_callee_spans() -> None:
    expression = _ensure_expression("Float(value)")

    assert isinstance(expression, CallExpr)
    assert isinstance(expression.arguments[0], NameExpr)
    assert expression.arguments[0].name == "value"
    assert isinstance(expression.callee, NameExpr)
    assert expression.callee.name == "Float"
    assert expression.callee.span.line == 1
    assert expression.callee.span.column == 27


def test_string_agg_preserves_its_internal_order_items() -> None:
    expression = _ensure_expression(
        'string_agg(value, ",", order by first desc, second)'
    )

    assert isinstance(expression, CallExpr)
    assert [item.direction for item in expression.aggregate_order_by] == ["desc", None]
    names = []
    for item in expression.aggregate_order_by:
        assert isinstance(item.expression, NameExpr)
        names.append(item.expression.name)
    assert names == ["first", "second"]


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


@pytest.mark.parametrize("column", ["select", "from", "where", "type", "is", "limit"])
def test_scalar_reads_a_soft_keyword_column(column: str) -> None:
    expression = _ensure_expression(f"scalar m.{column} > 0")

    assert type(expression) is ComparisonExpr
    assert expression.left == RelationScalarExpr(
        span=Span(
            path="scalar.pietto",
            line=1,
            column=27,
            end_line=1,
            end_column=36 + len(column),
        ),
        relation_name="m",
        column_name=column,
    )


def test_scalar_reads_a_soft_keyword_column_in_select_and_qualify() -> None:
    result = parse_source(
        "query q:\n"
        "    let m:\n"
        "        values (select: Int):\n"
        "            1\n"
        "    from m\n"
        "    select x = scalar m.select\n"
        "    qualify:\n"
        "        scalar m.select > 0\n"
    )

    assert result.diagnostics == () and result.ast is not None
    query = result.ast.definitions[0]
    assert type(query) is BlockRelationDef and type(query.body) is SelectBody
    assert query.body.select_items[0].expression == RelationScalarExpr(
        span=Span(path=None, line=6, column=16, end_line=6, end_column=31),
        relation_name="m",
        column_name="select",
    )
    assert query.body.qualify_clause is not None
    qualified = query.body.qualify_clause.expression
    assert type(qualified) is ComparisonExpr
    assert qualified.left == RelationScalarExpr(
        span=Span(path=None, line=8, column=9, end_line=8, end_column=24),
        relation_name="m",
        column_name="select",
    )


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
    result = parse_source(f"derive total() -> Int:\n    return {terms}\n")

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


def test_modern_scalar_float_spelling_keeps_callable_resolution_open() -> None:
    from pietto.ast_nodes import CallExpr, FunctionDef

    result = parse_source(
        "def Float(value: Int) -> Float:\n"
        "    return value + 1\n"
        "type Sample = Float ensure Float(value) > 1\n"
    )
    assert result.diagnostics == ()
    assert result.ast is not None
    assert isinstance(result.ast.definitions[0], FunctionDef)
    definition = result.ast.definitions[1]
    assert isinstance(definition, TypeDef)
    expression = definition.ensures[0].expression
    assert isinstance(expression, ComparisonExpr)
    assert isinstance(expression.left, CallExpr)


def test_modern_constraint_and_derive_bodies_require_explicit_return() -> None:
    from pietto.ast_nodes import ConstraintDef, DeriveDef

    result = parse_source(
        "constraint Positive(value: Int) -> Bool:\n"
        "    return value > 0\n"
        "derive Increment(value: Int) -> Int:\n"
        "    return value + 1\n"
    )
    assert result.diagnostics == ()
    assert result.ast is not None
    assert isinstance(result.ast.definitions[0], ConstraintDef)
    assert isinstance(result.ast.definitions[1], DeriveDef)
    retired = parse_source("constraint Positive(value: Int) -> Bool:\n    value > 0\n")
    assert retired.ast is None
    assert (
        retired.diagnostics[0].suggestion == "Add 'return' before the body expression."
    )


def test_minus_signs_written_together_warn_that_they_are_no_comment() -> None:
    # `100 -- 50` is `100 - (-50)`, which SQL would read as `100` and a
    # comment. Each run of minus signs written together warns once, at its
    # first two; spaced signs, a `#` comment and text do not warn.
    result = parse_source(
        "type A = Int ensure self > 100 -- 50\n"
        "type B = Int ensure self == --1 + 1 --- 2\n"
        "type C = Int ensure self > 100 - -50 # -- not code\n"
        'type D = Text ensure self != "a--b"\n',
        path="minus.pietto",
    )

    assert result.ast is not None
    assert [
        (
            item.code,
            item.severity,
            item.location.line,
            item.location.column,
            item.location.end_column,
        )
        for item in result.diagnostics
    ] == [
        ("PIE-P1009", Severity.WARNING, 1, 32, 34),
        ("PIE-P1009", Severity.WARNING, 2, 29, 31),
        ("PIE-P1009", Severity.WARNING, 2, 37, 39),
    ]
    assert result.diagnostics[0].message == (
        "`--` is not a comment in Pietto: it is two minus signs, so `a -- b` is "
        "`a - (-b)`; start a comment with `#`, or write `- -b` for the minus signs"
    )
