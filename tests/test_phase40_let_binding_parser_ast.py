from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

import pietto.cli as cli
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    LetBinding,
    LetClause,
    NameExpr,
    QueryDef,
    TableDef,
    UnaryExpr,
)
from pietto.errors import Severity
from pietto.parser_api import ParseResult, parse_source
from pietto.semantic import analyze


VALID_SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_table_let_after_from_preserves_ast() -> None:
    relation = _parse_relation(
        "table enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        amount\n"
    )

    assert isinstance(relation, TableDef)
    assert isinstance(relation.let_clause, LetClause)
    assert relation.let_clause.span.line == 3
    assert relation.let_clause.span.column == 5
    assert [binding.name for binding in relation.let_clause.bindings] == ["gross"]

    binding = relation.let_clause.bindings[0]
    assert isinstance(binding, LetBinding)
    assert binding.span.line == 4
    assert isinstance(binding.expression, BinaryExpr)
    assert binding.expression.operator == "+"


def test_query_let_after_from_preserves_ast() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        amount\n"
    )

    assert isinstance(relation, QueryDef)
    assert isinstance(relation.let_clause, LetClause)
    assert relation.let_clause.bindings[0].name == "gross"


def test_multiple_let_bindings_preserve_source_order() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        net = amount - tax\n"
        '        paid = status == "paid"\n'
        "    select:\n"
        "        amount\n"
    )

    clause = relation.let_clause
    assert isinstance(clause, LetClause)
    assert [binding.name for binding in clause.bindings] == [
        "gross",
        "net",
        "paid",
    ]
    assert [binding.span.line for binding in clause.bindings] == [4, 5, 6]
    assert isinstance(clause.bindings[2].expression, ComparisonExpr)


def test_source_qualified_field_leaves_parse_inside_let_expressions() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = orders.amount + orders.tax\n"
        "    select:\n"
        "        amount\n"
    )

    clause = relation.let_clause
    assert isinstance(clause, LetClause)
    expression = clause.bindings[0].expression
    assert isinstance(expression, BinaryExpr)
    assert isinstance(expression.left, DottedNameExpr)
    assert expression.left.parts == ("orders", "amount")
    assert isinstance(expression.right, DottedNameExpr)
    assert expression.right.parts == ("orders", "tax")


def test_function_call_unary_and_binary_examples_parse_inside_let() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        normalized = lower(trim(status))\n"
        "        negative_amount = -amount\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        amount\n"
    )

    clause = relation.let_clause
    assert isinstance(clause, LetClause)
    normalized, negative_amount, gross = clause.bindings
    assert isinstance(normalized.expression, CallExpr)
    assert isinstance(normalized.expression.arguments[0], CallExpr)
    assert isinstance(negative_amount.expression, UnaryExpr)
    assert negative_amount.expression.operator == "-"
    assert isinstance(gross.expression, BinaryExpr)
    assert gross.expression.operator == "+"


def test_let_remains_usable_as_identifier_and_name_part() -> None:
    relation = _parse_relation(
        "query let:\n"
        "    from let\n"
        "    let:\n"
        "        let = let.let\n"
        "    select:\n"
        "        let\n"
    )

    assert relation.name == "let"
    assert relation.from_clause.source_name == "let"
    assert isinstance(relation.let_clause, LetClause)
    binding = relation.let_clause.bindings[0]
    assert binding.name == "let"
    assert isinstance(binding.expression, DottedNameExpr)
    assert binding.expression.parts == ("let", "let")
    select_expression = relation.select_items[0].expression
    assert isinstance(select_expression, NameExpr)
    assert select_expression.name == "let"


@pytest.mark.parametrize(
    "body",
    [
        (
            "    from orders\n"
            "    where amount > 0\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        amount\n"
        ),
        (
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        status\n"
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        amount\n"
            "    let:\n"
            "        gross = amount + tax\n"
        ),
        (
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total_amount = sum(amount)\n"
            "    satisfying:\n"
            "        total_amount > 0\n"
            "    let:\n"
            "        gross = amount + tax\n"
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        amount\n"
            "    order by:\n"
            "        amount\n"
            "    let:\n"
            "        gross = amount + tax\n"
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        amount\n"
            "    limit 10\n"
            "    let:\n"
            "        gross = amount + tax\n"
        ),
    ],
)
def test_misplaced_let_blocks_are_parser_errors(body: str) -> None:
    result = parse_source(f"query bad:\n{body}", path="bad_let.pietto")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


@pytest.mark.parametrize(
    "body",
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    let:\n"
            "        net = amount - tax\n"
            "    select:\n"
            "        amount\n"
        ),
        ("    from orders\n    let:\n    select:\n        amount\n"),
        (
            "    from orders\n"
            "    let:\n"
            "        amount AS gross\n"
            "    select:\n"
            "        amount\n"
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        (gross, net) = amount\n"
            "    select:\n"
            "        amount\n"
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross, net = amount\n"
            "    select:\n"
            "        amount\n"
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = net = amount\n"
            "    select:\n"
            "        amount\n"
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross: Int = amount\n"
            "    select:\n"
            "        amount\n"
        ),
    ],
)
def test_rejected_let_binding_shapes_are_parser_errors(body: str) -> None:
    result = parse_source(f"query bad:\n{body}", path="bad_binding.pietto")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_parsed_let_produces_semantic_unsupported_diagnostic() -> None:
    result = parse_source(
        VALID_SOURCE_PREFIX
        + "query enriched_orders:\n"
        + "    from orders\n"
        + "    let:\n"
        + "        gross = amount + tax\n"
        + "    select:\n"
        + "        amount\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    semantic_result = analyze(result.ast)
    error_codes = [
        diagnostic.code
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]

    assert error_codes == ["PIE-S2328"]
    diagnostic = semantic_result.diagnostics[0]
    assert diagnostic.location.line == 9
    assert "parsed" in diagnostic.message
    assert "not semantically supported yet" in diagnostic.message


def test_cli_check_does_not_silently_accept_parsed_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / "with_let.pietto"
    source_path.write_text(
        VALID_SOURCE_PREFIX
        + "query enriched_orders:\n"
        + "    from orders\n"
        + "    let:\n"
        + "        gross = amount + tax\n"
        + "    select:\n"
        + "        amount\n",
        encoding="utf-8",
    )

    exit_code = cli.main(["check", str(source_path)])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "PIE-S2328" in captured.err
    assert "OK:" not in captured.out


def test_let_ast_does_not_expose_antlr_nodes() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        amount\n"
    )

    _assert_no_antlr_nodes(relation)


def _parse_relation(source: str) -> TableDef | QueryDef:
    result = parse_source(source)

    assert result.diagnostics == ()
    assert result.ast is not None
    return cast(TableDef | QueryDef, result.ast.definitions[0])


def _has_code(result: ParseResult, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)


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
