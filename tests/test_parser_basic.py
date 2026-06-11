from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import EnumDef, Header, Script, Span, TypeDef
from pietto.parser_api import parse_file, parse_source


def test_empty_source_parses() -> None:
    result = parse_source("")

    assert result.diagnostics == ()
    assert isinstance(result.ast, Script)
    assert result.ast.header is None
    assert result.ast.definitions == ()


def test_complete_header_parses() -> None:
    result = parse_source("pietto 0.9\nmode checked\ndialect postgres\nencoding utf8\n")

    assert result.diagnostics == ()
    assert isinstance(result.ast, Script)
    assert result.ast.header is not None
    assert result.ast.header == Header(
        span=result.ast.header.span,
        version="0.9",
        mode="checked",
        dialect="postgres",
        encoding="utf8",
    )


def test_partial_header_without_final_newline_parses() -> None:
    result = parse_source("mode strict")

    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.header is not None
    assert result.ast.header.mode == "strict"


def test_example_fixture_parses() -> None:
    result = parse_file("examples/basic/types.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.header is not None
    assert [type(item) for item in result.ast.definitions] == [
        TypeDef,
        TypeDef,
        TypeDef,
        EnumDef,
    ]


def test_public_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source(
        "type Username = Text(max = 32, encoding = utf8):\n"
        "    ensure len(self) >= 3\n"
        "constraint valid_name(x: Text) -> Bool:\n"
        "    len(x) >= 3\n"
    )

    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast)


def test_spans_are_one_based_half_open_and_exclude_trailing_newline() -> None:
    path = Path("examples/span.pietto")
    result = parse_source("type UserId = UUID\n", path=path)

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    assert definition.span == Span(
        path=str(path),
        line=1,
        column=1,
        end_line=1,
        end_column=19,
    )
    assert definition.base.span == Span(
        path=str(path),
        line=1,
        column=15,
        end_line=1,
        end_column=19,
    )


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
