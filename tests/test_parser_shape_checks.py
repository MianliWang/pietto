from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    CheckDef,
    ComparisonExpr,
    EnumDef,
    FieldDef,
    LiteralExpr,
    NameExpr,
    ShapeDef,
    Span,
    TypeDef,
)
from pietto.parser_api import parse_file, parse_source


def test_shape_check_parses_one_expression() -> None:
    result = parse_source(
        "shape Order:\n"
        "    amount: Decimal not null\n"
        "\n"
        "    check valid_amount:\n"
        "        amount >= 0\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [type(item) for item in definition.items] == [FieldDef, CheckDef]
    assert [field.name for field in definition.fields] == ["amount"]
    assert [check.name for check in definition.checks] == ["valid_amount"]

    check = definition.checks[0]
    assert isinstance(check.expression, ComparisonExpr)
    assert check.expression.operator == ">="
    assert isinstance(check.expression.left, NameExpr)
    assert check.expression.left.name == "amount"
    assert isinstance(check.expression.right, LiteralExpr)
    assert check.expression.right.value == 0


def test_shape_check_is_parse_only_without_semantic_checks() -> None:
    result = parse_source(
        "shape External:\n"
        "    check duplicate:\n"
        "        missing_value\n"
        "    check duplicate:\n"
        "        unknown_function(missing_value)\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [check.name for check in definition.checks] == ["duplicate", "duplicate"]


def test_shape_check_allows_blank_lines_comments_and_eof() -> None:
    result = parse_source(
        "shape Order:\n"
        "    amount: Decimal not null\n"
        "\n"
        "    # Validate the row contract.\n"
        "    check valid_amount:\n"
        "\n"
        "        # The body remains one expression.\n"
        "        amount >= 0"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    check = definition.checks[0]
    assert check.span.end_line == 8
    assert check.span.end_column == 20


def test_shape_preserves_mixed_field_and_check_order() -> None:
    result = parse_source(
        "shape Order:\n"
        "    check has_amount:\n"
        "        amount is not null\n"
        "    amount: Decimal not null\n"
        "    check valid_amount:\n"
        "        amount >= 0\n"
        "    status: Text nullable\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [type(item) for item in definition.items] == [
        CheckDef,
        FieldDef,
        CheckDef,
        FieldDef,
    ]
    assert [item.name for item in definition.items] == [
        "has_amount",
        "amount",
        "valid_amount",
        "status",
    ]
    assert [field.name for field in definition.fields] == ["amount", "status"]
    assert [check.name for check in definition.checks] == [
        "has_amount",
        "valid_amount",
    ]


def test_shape_check_preserves_top_level_definition_order() -> None:
    result = parse_source(
        "type Amount = Decimal\n"
        "shape Order:\n"
        "    amount: Amount not null\n"
        "    check valid_amount:\n"
        "        amount >= 0\n"
        "enum Status:\n"
        "    ready\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        TypeDef,
        ShapeDef,
        EnumDef,
    ]


def test_shape_check_spans_are_one_based_half_open() -> None:
    path = Path("examples/shapes/check_span.pie")
    result = parse_source(
        "shape Order:\n"
        "    amount: Decimal not null\n"
        "    check valid_amount:\n"
        "        amount >= 0\n"
        "    status: Text nullable\n",
        path=path,
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert definition.span == Span(
        path=str(path),
        line=1,
        column=1,
        end_line=5,
        end_column=26,
    )
    check = definition.checks[0]
    assert check.span == Span(
        path=str(path),
        line=3,
        column=5,
        end_line=4,
        end_column=20,
    )
    assert check.expression.span == Span(
        path=str(path),
        line=4,
        column=9,
        end_line=4,
        end_column=20,
    )


def test_shape_check_example_fixture_parses() -> None:
    result = parse_file("examples/shapes/order.pie")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [field.name for field in definition.fields] == ["amount"]
    assert [check.name for check in definition.checks] == ["valid_amount"]


def test_shape_check_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source(
        "shape Order:\n"
        "    amount: Decimal not null\n"
        "    check valid_amount:\n"
        "        amount >= 0\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast.definitions[0])


@pytest.mark.parametrize(
    "source",
    [
        "shape Order:\n    check :\n        amount >= 0\n",
        "shape Order:\n    check valid_amount\n        amount >= 0\n",
        "shape Order:\n    check valid_amount: amount >= 0\n",
        "shape Order:\n    check valid_amount:\n    amount >= 0\n",
        "shape Order:\n    check valid_amount:\n",
        (
            "shape Order:\n"
            "    check valid_amount:\n"
            "        amount >= 0\n"
            "        amount <= 100\n"
        ),
    ],
)
def test_malformed_shape_checks_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "P1000")


def test_shape_check_brace_block_reports_unsupported_brace() -> None:
    result = parse_source(
        "shape Order:\n"
        "    amount: Decimal not null\n"
        "    check valid_amount {\n"
        "        amount >= 0\n"
        "    }\n"
    )

    assert result.ast is None
    assert _has_code(result, "P1005")


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


def _has_code(result: object, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)
