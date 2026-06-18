from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import cast

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    ComparisonExpr,
    DottedNameExpr,
    LimitClause,
    LiteralExpr,
    NameExpr,
    OrderByClause,
    QueryDef,
    SatisfyingClause,
    TableDef,
)
from pietto.parser_api import ParseResult, parse_source


def test_table_satisfying_after_select_preserves_predicate_ast() -> None:
    relation = _parse_relation(
        "table high_value_regions:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total_amount = sum(amount)\n"
        "    satisfying:\n"
        "        total_amount > 1000\n"
    )

    assert isinstance(relation, TableDef)
    clause = relation.satisfying_clause
    assert isinstance(clause, SatisfyingClause)
    assert isinstance(clause.expression, ComparisonExpr)
    assert clause.expression.operator == ">"
    assert isinstance(clause.expression.left, NameExpr)
    assert clause.expression.left.name == "total_amount"
    assert isinstance(clause.expression.right, LiteralExpr)
    assert clause.expression.right.value == 1000


def test_query_satisfying_after_select_preserves_predicate_ast() -> None:
    relation = _parse_relation(
        "query high_value_regions:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total_amount = sum(amount)\n"
        "    satisfying:\n"
        "        total_amount > 1000\n"
    )

    assert isinstance(relation, QueryDef)
    assert isinstance(relation.satisfying_clause, SatisfyingClause)
    assert isinstance(relation.satisfying_clause.expression, ComparisonExpr)


def test_satisfying_parses_before_order_by_and_limit() -> None:
    relation = _parse_relation(
        "query high_value_regions:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total_amount = sum(amount)\n"
        "    satisfying:\n"
        "        total_amount > 1000\n"
        "    order by:\n"
        "        total_amount desc\n"
        "    limit 10\n"
    )

    assert isinstance(relation.satisfying_clause, SatisfyingClause)
    assert isinstance(relation.order_by_clause, OrderByClause)
    assert isinstance(relation.limit_clause, LimitClause)


def test_satisfying_allows_blank_lines_and_comments_around_predicate() -> None:
    relation = _parse_relation(
        "query high_value_regions:\n"
        "    from orders\n"
        "    select:\n"
        "        total_amount = sum(amount)\n"
        "\n"
        "    # Result predicate.\n"
        "    satisfying:\n"
        "\n"
        "        # Later semantic slices resolve this output name.\n"
        "        total_amount >= 1000\n"
        "\n"
    )

    assert isinstance(relation.satisfying_clause, SatisfyingClause)
    assert relation.satisfying_clause.span.line == 7
    assert isinstance(relation.satisfying_clause.expression, ComparisonExpr)


@pytest.mark.parametrize(
    "source",
    [
        "table plain:\n    from orders\n    select:\n        id\n",
        "query plain:\n    from orders\n    select:\n        id\n",
    ],
)
def test_relations_without_satisfying_keep_none_field(source: str) -> None:
    relation = _parse_relation(source)

    assert relation.satisfying_clause is None


@pytest.mark.parametrize(
    "body",
    [
        (
            "    from orders\n"
            "    satisfying:\n"
            "        total_amount > 1000\n"
            "    select:\n"
            "        total_amount = sum(amount)\n"
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        total_amount = sum(amount)\n"
            "    satisfying:\n"
            "        total_amount > 1000\n"
            "    satisfying:\n"
            "        total_amount < 5000\n"
        ),
        "    from orders\n    select:\n        total_amount\n    satisfying:\n",
        (
            "    from orders\n"
            "    select:\n"
            "        region\n"
            "    having:\n"
            '        region == "US"\n'
        ),
    ],
)
def test_invalid_satisfying_shapes_are_parser_errors(body: str) -> None:
    result = parse_source(f"query bad:\n{body}", path="satisfying.pietto")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_satisfying_remains_soft_identifier_and_name_part() -> None:
    relation = _parse_relation(
        "query satisfying:\n"
        "    from satisfying\n"
        "    select:\n"
        "        satisfying\n"
        "        satisfying = satisfying.satisfying\n"
        "    satisfying:\n"
        "        satisfying.satisfying == satisfying\n"
    )

    assert relation.name == "satisfying"
    assert relation.from_clause.source_name == "satisfying"
    first_projection = relation.select_items[0].expression
    assert isinstance(first_projection, NameExpr)
    assert first_projection.name == "satisfying"
    assert relation.select_items[1].alias == "satisfying"
    second_projection = relation.select_items[1].expression
    assert isinstance(second_projection, DottedNameExpr)
    assert second_projection.parts == ("satisfying", "satisfying")

    assert relation.satisfying_clause is not None
    predicate = relation.satisfying_clause.expression
    assert isinstance(predicate, ComparisonExpr)
    assert isinstance(predicate.left, DottedNameExpr)
    assert predicate.left.parts == ("satisfying", "satisfying")
    assert isinstance(predicate.right, NameExpr)
    assert predicate.right.name == "satisfying"


def test_satisfying_ast_does_not_expose_antlr_nodes() -> None:
    relation = _parse_relation(
        "table high_value_regions:\n"
        "    from orders\n"
        "    select:\n"
        "        total_amount = sum(amount)\n"
        "    satisfying:\n"
        "        total_amount > 1000\n"
    )

    _assert_no_antlr_nodes(relation)


def _parse_relation(source: str) -> TableDef | QueryDef:
    result = parse_source(source)

    assert result.diagnostics == ()
    assert result.ast is not None
    return cast(TableDef | QueryDef, result.ast.definitions[0])


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)
    elif isinstance(value, dict):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)


def _has_code(result: ParseResult, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)
