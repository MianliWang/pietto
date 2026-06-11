from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    EnumDef,
    LiteralExpr,
    ShapeDef,
    SourceDef,
    Span,
    TypeDef,
)
from pietto.parser_api import ParseResult, parse_file, parse_source


def test_typed_and_untyped_sources_parse_connector_expressions() -> None:
    result = parse_source(
        'source users: User is postgres.table("public.users")\n'
        'source raw_events is postgres.table("public.events")\n'
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    typed, untyped = result.ast.definitions
    assert isinstance(typed, SourceDef)
    assert typed.name == "users"
    assert typed.shape_name == "User"
    assert isinstance(typed.connector, CallExpr)
    assert isinstance(typed.connector.callee, DottedNameExpr)
    assert typed.connector.callee.parts == ("postgres", "table")
    assert len(typed.connector.arguments) == 1
    assert isinstance(typed.connector.arguments[0], LiteralExpr)
    assert typed.connector.arguments[0].value == "public.users"

    assert isinstance(untyped, SourceDef)
    assert untyped.name == "raw_events"
    assert untyped.shape_name is None
    assert isinstance(untyped.connector, CallExpr)
    assert isinstance(untyped.connector.arguments[0], LiteralExpr)
    assert untyped.connector.arguments[0].value == "public.events"


def test_source_is_parse_only_without_shape_or_connector_validation() -> None:
    result = parse_source(
        "source duplicate: MissingShape is unknown.connector(1, true)\n"
        "source duplicate is 42\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    first, second = result.ast.definitions
    assert isinstance(first, SourceDef)
    assert first.shape_name == "MissingShape"
    assert isinstance(first.connector, CallExpr)
    assert isinstance(second, SourceDef)
    assert isinstance(second.connector, LiteralExpr)
    assert second.connector.value == 42


def test_source_allows_blank_lines_comments_and_eof() -> None:
    result = parse_source(
        "# External relation binding.\n"
        "\n"
        'source users: User is postgres.table("public.users")'
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, SourceDef)
    assert definition.span.end_line == 3
    assert definition.span.end_column == 53


def test_source_preserves_top_level_definition_order() -> None:
    result = parse_source(
        "type UserId = UUID\n"
        "shape User:\n"
        "    id: UserId not null\n"
        'source users: User is postgres.table("public.users")\n'
        "enum Status:\n"
        "    ready\n"
        'source raw_events is postgres.table("public.events")\n'
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        TypeDef,
        ShapeDef,
        SourceDef,
        EnumDef,
        SourceDef,
    ]


def test_source_and_is_remain_available_in_dotted_expressions() -> None:
    result = parse_source("source registry is connector.source(row.is)\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, SourceDef)
    assert isinstance(definition.connector, CallExpr)
    assert isinstance(definition.connector.callee, DottedNameExpr)
    assert definition.connector.callee.parts == ("connector", "source")
    argument = definition.connector.arguments[0]
    assert isinstance(argument, DottedNameExpr)
    assert argument.parts == ("row", "is")


def test_source_spans_are_one_based_half_open() -> None:
    path = Path("examples/sources/span.pietto")
    result = parse_source(
        'source users: User is postgres.table("public.users")\n',
        path=path,
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, SourceDef)
    assert definition.span == Span(
        path=str(path),
        line=1,
        column=1,
        end_line=1,
        end_column=53,
    )
    assert definition.connector.span == Span(
        path=str(path),
        line=1,
        column=23,
        end_line=1,
        end_column=53,
    )
    assert isinstance(definition.connector, CallExpr)
    assert definition.connector.arguments[0].span == Span(
        path=str(path),
        line=1,
        column=38,
        end_line=1,
        end_column=52,
    )


def test_source_example_fixture_parses() -> None:
    result = parse_file("examples/sources/users.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    sources = tuple(
        definition
        for definition in result.ast.definitions
        if isinstance(definition, SourceDef)
    )
    assert [source.name for source in sources] == [
        "users",
        "raw_events",
    ]


def test_source_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source('source users: User is postgres.table("public.users")\n')

    assert result.diagnostics == ()
    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast.definitions[0])


@pytest.mark.parametrize(
    "source",
    [
        'source : User is postgres.table("public.users")\n',
        'source users: is postgres.table("public.users")\n',
        'source users User is postgres.table("public.users")\n',
        'source users: User postgres.table("public.users")\n',
        "source users: User is\n",
        'source users: User is postgres.table("public.users"\n',
        'source users: User is postgres.table("public.users") extra\n',
        "source users:\n",
    ],
)
def test_malformed_sources_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_source_rejects_old_postfix_nullability() -> None:
    result = parse_source('source users: User? is postgres.table("public.users")\n')

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_source_brace_block_reports_unsupported_brace() -> None:
    result = parse_source('source users: User is postgres.table("public.users") {\n}\n')

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
