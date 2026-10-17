from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

import pietto.parser_api as parser_api
from pietto.ast_nodes import EnumDef, Header, Script, ShapeDef, Span, TypeDef
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


def test_line_breaks_inside_parentheses_join_lines_with_real_positions() -> None:
    result = parse_source(
        "shape Row:\n"
        "    amount: Decimal(10,\n"
        "# a comment line\n"
        "\n"
        "            2) not null derive coalesce(\n"
        "        amount, (1 +\n"
        "  2))\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    shape = result.ast.definitions[0]
    assert isinstance(shape, ShapeDef)
    field = shape.fields[0]
    assert [argument.value.span.line for argument in field.type_expr.arguments] == [
        2,
        5,
    ]
    derive = field.derive_expression
    assert derive is not None
    assert (derive.span.line, derive.span.column) == (5, 32)
    assert (derive.span.end_line, derive.span.end_column) == (7, 6)


@pytest.mark.parametrize(
    ("source", "line", "column"),
    (
        ("type Huge = Int(max = 1\n", 1, 16),
        ("shape Row:\n    id: Int derive f(a, (b\n\nshape Next:\n", 2, 25),
    ),
)
def test_an_unclosed_parenthesis_is_reported_once_at_the_innermost_open(
    source: str, line: int, column: int
) -> None:
    result = parse_source(source, path="open.pietto")

    assert result.ast is None
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [("PIE-P1008", "'(' is never closed.", line, column)]


def test_an_unmatched_closing_parenthesis_is_left_to_the_parser() -> None:
    result = parse_source("type T = Int)\n")

    assert result.ast is None
    assert [item.code for item in result.diagnostics] == ["PIE-P1000"]


def test_tabs_inside_joined_lines_are_still_reported() -> None:
    result = parse_source("type T = Text(max =\n\t255)\n")

    assert result.ast is None
    assert [(item.code, item.location.line) for item in result.diagnostics] == [
        ("PIE-P1004", 2)
    ]


@pytest.mark.parametrize(
    ("ending", "fields", "shape_end", "open_paren"),
    (
        ("\n", [(2, 5, 2, 21), (3, 5, 3, 15)], (3, 15), (5, 13)),
        ("\r\n", [(2, 5, 2, 21), (3, 5, 3, 15)], (3, 15), (5, 13)),
        ("\r", [(2, 5, 2, 21), (3, 5, 3, 15)], (3, 15), (5, 13)),
    ),
)
def test_lf_crlf_and_cr_give_the_same_positions_around_joined_lines(
    ending: str,
    fields: list[tuple[int, int, int, int]],
    shape_end: tuple[int, int],
    open_paren: tuple[int, int],
) -> None:
    source = "shape Row:\n    id: Int not null\n    name: Text\n"
    ok = parse_source(source.replace("\n", ending))
    assert ok.diagnostics == () and ok.ast is not None
    shape = ok.ast.definitions[0]
    assert isinstance(shape, ShapeDef)
    assert [
        (f.span.line, f.span.column, f.span.end_line, f.span.end_column)
        for f in shape.fields
    ] == fields
    assert (shape.span.end_line, shape.span.end_column) == shape_end
    broken = parse_source((source + "\ntype T = Int(\n").replace("\n", ending))
    assert [
        (item.code, item.location.line, item.location.column)
        for item in broken.diagnostics
    ] == [("PIE-P1008", *open_paren)]


@pytest.mark.parametrize(
    ("source", "line", "column"),
    (
        (
            "    shape A:\n        id: Int not null\nshape B:\n    id: Int not null\n",
            1,
            5,
        ),
        # Deeper than the next line: still the first line, and no PIE-P1003.
        ("     shape S:\n    id: Int not null\n", 1, 6),
        ("  shape S:\n    id: Int not null\n", 1, 3),
        ("    shape S:\r    id: Int not null\r", 1, 5),
        ("# c\n     shape A:\n    id: Int not null\n", 2, 6),
        ("\n    type T = Int\n", 2, 5),
    ),
)
def test_an_indented_first_code_line_is_one_unexpected_indentation(
    source: str, line: int, column: int
) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in result.diagnostics
    ] == [("PIE-P1000", line, column, "Unexpected indentation.")]


_INDENTED_AS_A_WHOLE = (
    "    shape A:\n        id: Int not null\n    shape B:\n        id: Int not null\n"
)
_UNEXPECTED = "Unexpected indentation."
_NO_OUTER_BLOCK = "Indentation does not match an outer block."


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            _INDENTED_AS_A_WHOLE,
            [
                ("PIE-P1000", 1, 5, _UNEXPECTED),
                ("PIE-P1003", 3, 5, _NO_OUTER_BLOCK),
            ],
        ),
        (
            "# c\n" + _INDENTED_AS_A_WHOLE,
            [
                ("PIE-P1000", 2, 5, _UNEXPECTED),
                ("PIE-P1003", 4, 5, _NO_OUTER_BLOCK),
            ],
        ),
        (
            "\n\n# c\n\n" + _INDENTED_AS_A_WHOLE,
            [
                ("PIE-P1000", 5, 5, _UNEXPECTED),
                ("PIE-P1003", 7, 5, _NO_OUTER_BLOCK),
            ],
        ),
        (
            '  shape R:\n    a: Int not null\n  source r: R is postgres.table("r")\n'
            "  query q:\n    from r\n    select: a\n",
            [
                ("PIE-P1000", 1, 3, _UNEXPECTED),
                ("PIE-P1003", 3, 3, _NO_OUTER_BLOCK),
            ],
        ),
        (
            "    type A = Int not null\n    type B = Int not null\n",
            [("PIE-P1000", 1, 5, _UNEXPECTED)],
        ),
        # The first declaration reports only its cause; a later one its own error.
        (
            "    shape A:\n        id Int\nshape B:\n    id Int\n",
            [
                ("PIE-P1000", 1, 5, _UNEXPECTED),
                ("PIE-P1000", 4, 8, "Missing ':' before 'Int'."),
            ],
        ),
    ),
)
def test_a_file_indented_as_a_whole_reports_its_first_code_line(
    source: str, expected: list[tuple[str, int, int, str]]
) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in result.diagnostics
    ] == expected


@pytest.mark.parametrize(
    ("source", "line"),
    (
        ("shape Row:\n\tid: Int\n", 2),
        ("shape Row:\r\n\tid: Int\r\n", 2),
        # A lone CR ends a line for the tab check as for every position.
        ("shape S:\r    a: Int not null\r\tx: Int\r", 3),
        # It also ends a line at a form feed inside a comment.
        ("# a\fb\nshape Row:\n\tid: Int\n", 4),
    ),
)
def test_tab_errors_count_lines_as_they_always_did(source: str, line: int) -> None:
    result = parse_source(source)

    assert [
        (item.code, item.location.line, item.location.column)
        for item in result.diagnostics
        if item.code == "PIE-P1004"
    ] == [("PIE-P1004", line, 1)]
