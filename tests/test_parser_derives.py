from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    ConstraintDef,
    DeriveDef,
    EnumDef,
    FunctionDef,
    NameExpr,
    Nullability,
    Parameter,
    ShapeDef,
    Span,
    TypeDef,
    TypeExpr,
)
from pietto.parser_api import ParseResult, parse_file, parse_source


def test_derive_parses_nested_call_expression() -> None:
    result = parse_source(
        "derive normalized_email(x: Text) -> Text:\n    lower(trim(x))\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, DeriveDef)
    assert definition.name == "normalized_email"
    assert len(definition.parameters) == 1
    assert isinstance(definition.parameters[0], Parameter)
    assert definition.parameters[0].name == "x"
    assert definition.parameters[0].type.name == "Text"
    assert isinstance(definition.return_type, TypeExpr)
    assert definition.return_type.name == "Text"
    assert isinstance(definition.body, CallExpr)
    assert isinstance(definition.body.callee, NameExpr)
    assert definition.body.callee.name == "lower"
    inner = definition.body.arguments[0]
    assert isinstance(inner, CallExpr)
    assert isinstance(inner.callee, NameExpr)
    assert inner.callee.name == "trim"


def test_derive_is_parse_only_without_semantic_checks() -> None:
    result = parse_source(
        "derive recursive(value: MissingType) -> UnexpectedType:\n"
        "    recursive(value)\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, DeriveDef)
    assert definition.parameters[0].type.name == "MissingType"
    assert definition.return_type.name == "UnexpectedType"


def test_derive_parameter_and_return_types_preserve_nullability() -> None:
    result = parse_source(
        "derive normalize(value: Text nullable) -> Text not null:\n    value\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, DeriveDef)
    assert definition.parameters[0].type.nullability is Nullability.NULLABLE
    assert definition.return_type.nullability is Nullability.NOT_NULL


def test_derive_allows_blank_lines_and_comments() -> None:
    result = parse_source(
        "derive normalized(x: Text) -> Text:\n"
        "\n"
        "    # The body remains one expression.\n"
        "    lower(x)\n"
        "\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert isinstance(result.ast.definitions[0], DeriveDef)


def test_derive_without_final_newline_closes_at_eof() -> None:
    result = parse_source(
        "derive normalized_email(x: Text) -> Text:\n    lower(trim(x))"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, DeriveDef)
    assert definition.span.end_line == 2
    assert definition.span.end_column == 19


def test_derive_span_is_one_based_half_open() -> None:
    path = Path("examples/derives/span.pietto")
    result = parse_source(
        "derive normalized_email(x: Text) -> Text:\n    lower(trim(x))\n",
        path=path,
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, DeriveDef)
    assert definition.span == Span(
        path=str(path),
        line=1,
        column=1,
        end_line=2,
        end_column=19,
    )
    assert definition.parameters[0].span == Span(
        path=str(path),
        line=1,
        column=25,
        end_line=1,
        end_column=32,
    )
    assert definition.return_type.span == Span(
        path=str(path),
        line=1,
        column=37,
        end_line=1,
        end_column=41,
    )
    assert definition.body.span == Span(
        path=str(path),
        line=2,
        column=5,
        end_line=2,
        end_column=19,
    )


def test_derive_keeps_top_level_definition_order() -> None:
    result = parse_source(
        "type Email = Text\n"
        "constraint valid(x: Email) -> Bool:\n"
        "    x is not null\n"
        "derive normalized(x: Email) -> Email:\n"
        "    lower(x)\n"
        "enum Status:\n"
        "    ready\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        TypeDef,
        ConstraintDef,
        DeriveDef,
        EnumDef,
    ]


def test_derive_example_fixture_parses() -> None:
    result = parse_file("examples/derives/normalized_email.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    assert isinstance(result.ast.definitions[0], DeriveDef)


def test_derive_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source(
        "derive normalized_email(x: Text) -> Text:\n    lower(trim(x))\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast.definitions[0])


@pytest.mark.parametrize(
    "source",
    [
        "derive (x: Text) -> Text:\n    x\n",
        "derive normalized x: Text -> Text:\n    x\n",
        "derive normalized(x) -> Text:\n    x\n",
        "derive normalized(x: Text) Text:\n    x\n",
        "derive normalized(x: Text) -> :\n    x\n",
        "derive normalized(x: Text) -> Text\n    x\n",
        "derive normalized(x: Text) -> Text:\nx\n",
        "derive normalized(x: Text) -> Text:\n",
    ],
)
def test_malformed_derives_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_derive_rejects_multiple_body_expressions() -> None:
    result = parse_source(
        "derive normalize(x: Text) -> Text:\n    trim(x)\n    lower(x)\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_derive_brace_block_reports_unsupported_brace() -> None:
    result = parse_source("derive normalize(x: Text) -> Text {\n    trim(x)\n}\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1005")


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


def test_def_header_line_and_block_bodies_build_one_function() -> None:
    header = parse_source(
        "def reachable(email: Text nullable, coupon: Text nullable) -> Bool nullable:"
        ' return email like "%@%" and coupon is null\n'
    )
    block = parse_source(
        "def reachable(\n"
        "    email: Text nullable,\n"
        "    coupon: Text nullable,\n"
        ") -> Bool nullable:\n"
        "    # the only statement\n"
        '    return email like "%@%" and coupon is null\n'
    )

    for result in (header, block):
        assert result.diagnostics == ()
        assert result.ast is not None
        (function,) = result.ast.definitions
        assert isinstance(function, FunctionDef)
        assert function.name == "reachable"
        assert [
            (p.name, p.type.name, p.type.nullability) for p in function.parameters
        ] == [
            ("email", "Text", Nullability.NULLABLE),
            ("coupon", "Text", Nullability.NULLABLE),
        ]
        assert function.return_type.nullability is Nullability.NULLABLE
        assert type(function.body) is BinaryExpr
    assert block.ast is not None
    span = block.ast.definitions[0].span
    assert (span.line, span.column, span.end_line, span.end_column) == (1, 1, 6, 47)


@pytest.mark.parametrize(
    ("source", "role", "column"),
    (
        ("def f(x: Int) -> Int not null: return x\n", "parameter", 10),
        ("def f(x: Int not null) -> Int: return x\n", "return type", 27),
        ("def f() -> Bool:\n    return true\n", "return type", 12),
    ),
)
def test_def_types_must_state_their_nullability(
    source: str, role: str, column: int
) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1000",
            f"A `def` {role} must state its nullability: write `nullable` or "
            "`not null` after the type.",
            1,
            column,
        )
    ]


@pytest.mark.parametrize(
    "source",
    (
        "def f() -> Int not null: 1\n",
        "def f() -> Int not null:\n    1\n",
        "def f() -> Int not null:\n    return 1\n    return 2\n",
        "def f():\n    return 1\n",
        "def f -> Int not null: return 1\n",
    ),
)
def test_def_bodies_are_exactly_one_return(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert {item.code for item in result.diagnostics} == {"PIE-P1000"}


def test_def_and_return_remain_ordinary_names() -> None:
    result = parse_source(
        "shape Row:\n    def: Int not null\n    return: Text nullable\n"
        "type return = Int\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    shape = result.ast.definitions[0]
    assert isinstance(shape, ShapeDef)
    assert [field.name for field in shape.fields] == [
        "def",
        "return",
    ]
    assert result.ast.definitions[1].name == "return"
