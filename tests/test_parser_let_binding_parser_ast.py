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
    CollectRelationExpr,
    ComparisonExpr,
    DottedNameExpr,
    QueryLetDeclaration,
    NameExpr,
    QueryDef,
    TableDef,
    UnaryExpr,
)
from pietto.parser_api import ParseResult, parse_source
from pietto.semantic import analyze


VALID_SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int\n"
    "    amount: Int\n"
    "    tax: Int\n"
    "    status: Text\n"
    'source orders: Order = postgres.table("orders")\n'
)


def test_table_let_after_from_preserves_ast() -> None:
    relation = _parse_relation(
        "table enriched_orders:\n"
        "    from orders\n"
        "\n"
        "    let gross = amount + tax\n"
        "    select:\n"
        "        amount\n"
    )

    assert isinstance(relation, TableDef)
    assert relation.let_clause is None
    assert relation.naming_declarations[0].span.line == 4
    assert relation.naming_declarations[0].span.column == 5
    assert [binding.name for binding in relation.naming_declarations] == ["gross"]

    binding = relation.naming_declarations[0]
    assert isinstance(binding, QueryLetDeclaration)
    assert binding.span.line == 4
    assert isinstance(binding.expression, BinaryExpr)
    assert binding.expression.operator == "+"


def test_query_let_after_from_preserves_ast() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "\n"
        "    let gross = amount + tax\n"
        "    select:\n"
        "        amount\n"
    )

    assert isinstance(relation, QueryDef)
    assert relation.let_clause is None
    assert relation.naming_declarations[0].name == "gross"


def test_multiple_let_bindings_preserve_source_order() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "\n"
        "    let gross = amount + tax\n"
        "    let net = amount - tax\n"
        '    let paid = status == "paid"\n'
        "    select:\n"
        "        amount\n"
    )

    bindings = relation.naming_declarations
    assert all(isinstance(item, QueryLetDeclaration) for item in bindings)
    assert [binding.name for binding in bindings] == [
        "gross",
        "net",
        "paid",
    ]
    assert [binding.span.line for binding in bindings] == [4, 5, 6]
    assert isinstance(bindings[2].expression, ComparisonExpr)


def test_source_qualified_field_leaves_parse_inside_let_expressions() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "\n"
        "    let gross = orders.amount + orders.tax\n"
        "    select:\n"
        "        amount\n"
    )

    bindings = relation.naming_declarations
    assert all(isinstance(item, QueryLetDeclaration) for item in bindings)
    expression = bindings[0].expression
    assert isinstance(expression, BinaryExpr)
    assert isinstance(expression.left, DottedNameExpr)
    assert expression.left.parts == ("orders", "amount")
    assert isinstance(expression.right, DottedNameExpr)
    assert expression.right.parts == ("orders", "tax")


def test_function_call_unary_and_binary_examples_parse_inside_let() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "\n"
        "    let normalized = lower(trim(status))\n"
        "    let negative_amount = -amount\n"
        "    let gross = amount + tax\n"
        "    select:\n"
        "        amount\n"
    )

    bindings = relation.naming_declarations
    assert all(isinstance(item, QueryLetDeclaration) for item in bindings)
    normalized, negative_amount, gross = bindings
    assert isinstance(normalized.expression, CallExpr)
    assert isinstance(normalized.expression.arguments[0], CallExpr)
    assert isinstance(negative_amount.expression, UnaryExpr)
    assert negative_amount.expression.operator == "-"
    assert isinstance(gross.expression, BinaryExpr)
    assert gross.expression.operator == "+"


def test_let_remains_usable_as_identifier_and_name_part() -> None:
    relation = _parse_relation(
        "query let:\n    from let\n\n    let let = let.let\n    select:\n        let\n"
    )

    assert relation.name == "let"
    assert relation.from_clause.source_name == "let"
    assert relation.let_clause is None
    binding = relation.naming_declarations[0]
    assert binding.name == "let"
    assert isinstance(binding.expression, DottedNameExpr)
    assert binding.expression.parts == ("let", "let")
    select_expression = relation.select_items[0].expression
    assert isinstance(select_expression, NameExpr)
    assert select_expression.name == "let"


def test_collect_is_contextual_in_projection_and_preserves_its_read_span() -> None:
    relation = _parse_relation(
        "query collect:\n"
        "    from collect\n"
        "    let unpacked = unnest(collect.items)\n"
        "    select:\n"
        "        nested = collect child_rows\n"
        "        named = collect\n"
        "        called = collect(child_rows)\n"
    )

    assert relation.name == "collect"
    assert relation.from_clause.source_name == "collect"
    (unpacked,) = relation.naming_declarations
    assert isinstance(unpacked, QueryLetDeclaration)
    assert isinstance(unpacked.expression, CallExpr)
    assert isinstance(unpacked.expression.callee, NameExpr)
    assert unpacked.expression.callee.name == "unnest"
    assert isinstance(unpacked.expression.arguments[0], DottedNameExpr)
    assert unpacked.expression.arguments[0].parts == ("collect", "items")

    nested, named, called = relation.select_items
    assert isinstance(nested.expression, CollectRelationExpr)
    assert nested.expression.relation_name == "child_rows"
    assert (
        nested.expression.span.line,
        nested.expression.span.column,
        nested.expression.span.end_line,
        nested.expression.span.end_column,
    ) == (5, 18, 5, 36)
    assert isinstance(named.expression, NameExpr)
    assert named.expression.name == "collect"
    assert isinstance(called.expression, CallExpr)
    assert isinstance(called.expression.callee, NameExpr)
    assert called.expression.callee.name == "collect"


@pytest.mark.parametrize(
    "body",
    [
        (
            "    from orders\n"
            "    where amount > 0\n"
            "\n"
            "    let gross = amount + tax\n"
            "    select:\n"
            "        amount\n"
        ),
        (
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "\n"
            "    let gross = amount + tax\n"
            "    select:\n"
            "        status\n"
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        amount\n"
            "\n"
            "    let gross = amount + tax\n"
        ),
        (
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total_amount = sum(amount)\n"
            "    having:\n"
            "        total_amount > 0\n"
            "\n"
            "    let gross = amount + tax\n"
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        amount\n"
            "    order by:\n"
            "        amount\n"
            "\n"
            "    let gross = amount + tax\n"
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        amount\n"
            "    limit 10\n"
            "\n"
            "    let gross = amount + tax\n"
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
        ("    from orders\n    let:\n    select:\n        amount\n"),
        ("    from orders\n\n    let amount AS gross\n    select:\n        amount\n"),
        (
            "    from orders\n"
            "\n"
            "    let (gross, net) = amount\n"
            "    select:\n"
            "        amount\n"
        ),
        (
            "    from orders\n"
            "\n"
            "    let gross, net = amount\n"
            "    select:\n"
            "        amount\n"
        ),
        (
            "    from orders\n"
            "\n"
            "    let gross = net = amount\n"
            "    select:\n"
            "        amount\n"
        ),
        (
            "    from orders\n"
            "\n"
            "    let gross: Int = amount\n"
            "    select:\n"
            "        amount\n"
        ),
    ],
)
def test_rejected_let_binding_shapes_are_parser_errors(body: str) -> None:
    result = parse_source(f"query bad:\n{body}", path="bad_binding.pietto")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_consecutive_naming_declarations_preserve_source_order() -> None:
    relation = _parse_relation(
        "query q:\n    from orders\n"
        "    let gross = amount + tax\n"
        "    let net = amount - tax\n"
        "    select amount\n"
    )
    assert [(item.name, item.span.line) for item in relation.naming_declarations] == [
        ("gross", 3),
        ("net", 4),
    ]


def test_parsed_supported_let_has_no_semantic_unsupported_diagnostic() -> None:
    result = parse_source(
        VALID_SOURCE_PREFIX
        + "query enriched_orders:\n"
        + "    from orders\n"
        + "    let gross = amount + tax\n"
        + "    select:\n"
        + "        amount\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    semantic_result = analyze(result.ast)

    assert semantic_result.diagnostics == ()


def test_cli_check_accepts_supported_parsed_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / "with_let.pietto"
    source_path.write_text(
        VALID_SOURCE_PREFIX
        + "query enriched_orders:\n"
        + "    from orders\n"
        + "    let gross = amount + tax\n"
        + "    select:\n"
        + "        amount\n",
        encoding="utf-8",
    )

    exit_code = cli.main(["check", str(source_path)])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert f"OK: {source_path}" in captured.out


def test_let_ast_does_not_expose_antlr_nodes() -> None:
    relation = _parse_relation(
        "query enriched_orders:\n"
        "    from orders\n"
        "\n"
        "    let gross = amount + tax\n"
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


def test_modern_query_names_preserve_all_positions_without_guessing_roles() -> None:
    from pietto.ast_nodes import NameExpr, QueryLetDeclaration

    result = parse_source(
        "query q:\n"
        "    let base = orders\n"
        "    from base\n"
        "    let buyer = customers\n"
        "    left join buyer on Match(base, buyer)\n"
        "    let copied = id\n"
        "    let copied = other\n"
        "    select copied\n"
    )
    assert result.diagnostics == ()
    assert result.ast is not None
    query = result.ast.definitions[0]
    assert isinstance(query, QueryDef)
    assert query.let_clause is None
    assert all(
        isinstance(item, QueryLetDeclaration) for item in query.naming_declarations
    )
    assert [(item.name, item.span.line) for item in query.naming_declarations] == [
        ("base", 2),
        ("buyer", 4),
        ("copied", 6),
        ("copied", 7),
    ]
    assert isinstance(query.naming_declarations[-1].expression, NameExpr)
    assert query.naming_declarations[-1].name_span.column == 9
