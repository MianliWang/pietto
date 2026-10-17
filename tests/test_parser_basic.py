from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

import pietto.parser_api as parser_api
from pietto.ast_nodes import EnumDef, Header, Script, Span, TypeDef
from pietto.parser_api import parse_file, parse_source


def test_empty_source_parses() -> None:
    result = parse_source("")

    assert result.diagnostics == ()
    assert isinstance(result.ast, Script)
    assert result.ast.header is None
    assert result.ast.definitions == ()


def test_leading_bom_preserves_parsed_ast_and_spans(tmp_path: Path) -> None:
    source = 'type Label = Text:\n    ensure matches(self, "中文😀")\n'
    path = tmp_path / "label.pietto"
    path.write_bytes(b"\xef\xbb\xbf" + source.encode("utf-8"))

    plain_result = parse_source(source, path=path)
    bom_result = parse_file(path)

    assert bom_result == plain_result


def test_only_leading_bom_parses_as_empty_source() -> None:
    result = parse_source("\ufeff")

    assert result.diagnostics == ()
    assert isinstance(result.ast, Script)
    assert result.ast.header is None
    assert result.ast.definitions == ()


def test_only_one_leading_bom_is_ignored() -> None:
    for source in ("\ufeff\ufeff", "type Label = \ufeffText\n"):
        result = parse_source(source)

        assert result.ast is None
        assert any(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


def test_leading_bom_does_not_relax_source_size_limit() -> None:
    result = parse_source(
        "\ufeff" + "#" + "a" * (parser_api._MAX_SOURCE_UTF8_BYTES - 1)
    )

    assert result.ast is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-P1006"]


def test_leading_bom_does_not_shift_tab_diagnostic_location() -> None:
    result = parse_source("\ufeff\tshape User:\n")

    assert result.ast is None
    tab_diagnostic = next(
        diagnostic
        for diagnostic in result.diagnostics
        if diagnostic.code == "PIE-P1004"
    )
    assert (tab_diagnostic.location.line, tab_diagnostic.location.column) == (1, 1)


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
    assert result.ast.header is None
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


@pytest.mark.parametrize(
    "source",
    [
        "type A = Int\n\ntype Age = Int:\n    ensure self >= 0\n",
        "type A = Int\r\n\r\ntype Age = Int:\r\n    ensure self >= 0\r\n",
        "type A = Int\r\rtype Age = Int:\r    ensure self >= 0\r",
        "type A = Int\r\r\ntype Age = Int:\r    ensure self >= 0",
        "type A = Int\n\rtype Age = Int:\r\n    ensure self >= 0\r",
    ],
    ids=["lf", "crlf", "cr", "cr-crlf", "lf-cr"],
)
def test_lf_crlf_and_lone_cr_each_end_one_line_in_spans(source: str) -> None:
    path = Path("examples/line-ends.pietto")
    result = parse_source(source, path=path)

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[1]
    assert isinstance(definition, TypeDef)
    assert definition.span == Span(
        path=str(path), line=3, column=1, end_line=4, end_column=21
    )
    assert definition.base.span == Span(
        path=str(path), line=3, column=12, end_line=3, end_column=15
    )
    assert [item.span for item in definition.ensures] == [
        Span(path=str(path), line=4, column=5, end_line=4, end_column=21)
    ]


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
