from __future__ import annotations

import pytest

from pietto.parser_api import ParseResult, parse_source


def test_malformed_type_reports_generic_syntax_error() -> None:
    result = parse_source("type = Int\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_parser_diagnostic_uses_canonical_code_format() -> None:
    result = parse_source("type = Int\n")

    assert result.diagnostics[0].code == "PIE-P1000"


def test_brace_block_reports_unsupported_brace_diagnostic() -> None:
    result = parse_source("type Age = Int {\n    ensure self >= 0\n}\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1005")


def test_braces_inside_strings_and_comments_do_not_report_p1005() -> None:
    result = parse_source(
        'type Pattern = Text(default = "{")\n# this comment has a }\n'
    )

    assert result.diagnostics == ()
    assert result.ast is not None


def test_tab_indentation_reports_tab_diagnostic() -> None:
    result = parse_source("type Age = Int:\n\tensure self >= 0\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1004")


def test_inconsistent_dedent_reports_indentation_diagnostic() -> None:
    result = parse_source(
        "type Age = Int:\n    ensure self >= 0\n  ensure self <= 130\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1003")


def test_case_expression_is_not_supported_yet() -> None:
    result = parse_source("type Age = Int ensure case self\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_assignment_is_not_a_general_expression() -> None:
    result = parse_source("type Age = Int ensure self = 1\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_invalid_string_escape_returns_diagnostic() -> None:
    result = parse_source(r'type Pattern = Text(default = "\x")' "\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")
    assert "escape" in result.diagnostics[0].message.lower()


def test_overly_long_integer_literal_returns_diagnostic() -> None:
    result = parse_source(
        "type Huge = Int(max = " + "9" * 5000 + ") not null\n",
        path="huge-integer.pietto",
    )

    assert result.ast is None
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-P1000"
    assert diagnostic.location.path == "huge-integer.pietto"
    assert "maximum supported length" in diagnostic.message


def test_overly_long_decimal_literal_returns_diagnostic() -> None:
    result = parse_source(
        "type Huge = Float(max = " + "9" * 2500 + "." + "9" * 2500 + ") not null\n"
    )

    assert result.ast is None
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-P1000"
    assert "maximum supported length" in result.diagnostics[0].message


def test_non_finite_decimal_literal_returns_diagnostic() -> None:
    result = parse_source("type Huge = Float(max = " + "9" * 1000 + ".0) not null\n")

    assert result.ast is None
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-P1000"
    assert "finite" in result.diagnostics[0].message


def test_deep_unary_expression_returns_parser_diagnostic() -> None:
    result = parse_source(
        "derive deep() -> Int not null:\n    " + "+" * 1500 + "1\n",
        path="deep-unary.pietto",
    )

    assert result.ast is None
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-P1000"
    assert diagnostic.location.path == "deep-unary.pietto"
    assert "recursion limit" in diagnostic.message


def test_reasonable_unary_expression_still_parses() -> None:
    result = parse_source("derive nested() -> Int not null:\n    " + "+" * 20 + "1\n")

    assert result.ast is not None
    assert result.diagnostics == ()


def test_empty_enum_reports_syntax_error() -> None:
    result = parse_source("enum Status:\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_missing_indentation_after_colon_reports_syntax_error() -> None:
    result = parse_source("enum Status:\ndraft\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


@pytest.mark.parametrize(
    "source",
    [
        "mode checked\nmode strict\n",
        "encoding utf8\nmode checked\n",
    ],
)
def test_duplicate_or_out_of_order_header_reports_syntax_error(
    source: str,
) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


_LINE_END_CASES = {
    "tab": (
        "type Age = Int:\n    ensure self >= 0\n\tensure self < 9\n",
        [("PIE-P1004", 3, 1), ("PIE-P1000", 3, 2), ("PIE-P1003", 3, 2)],
    ),
    "dedent": (
        "type Age = Int:\n    ensure self >= 0\n  ensure self <= 130\n",
        [("PIE-P1000", 3, 3), ("PIE-P1003", 3, 3)],
    ),
    "brace": (
        "type A = Int\n\ntype Age = Int {\n",
        [("PIE-P1000", 3, 16), ("PIE-P1005", 3, 16)],
    ),
    "escape": (
        'type A = Int\ntype P = Text(default = "a\\q")\n',
        [("PIE-P1000", 2, 27)],
    ),
}


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"], ids=["lf", "crlf", "cr"])
@pytest.mark.parametrize("case", sorted(_LINE_END_CASES))
def test_lf_crlf_and_lone_cr_each_end_one_line_in_diagnostics(
    case: str, ending: str
) -> None:
    source, expected = _LINE_END_CASES[case]
    result = parse_source(source.replace("\n", ending))

    assert [
        (item.code, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == expected


def test_mixed_line_ends_each_end_one_line_in_diagnostics() -> None:
    result = parse_source(
        "type A = Int\r\r\n\rtype Age = Int:\n"
        "    ensure self >= 0\r\tensure self < 9\r\n"
    )

    assert [
        (item.code, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [("PIE-P1004", 6, 1), ("PIE-P1000", 6, 2), ("PIE-P1003", 6, 2)]


@pytest.mark.parametrize(
    ("ending", "quoted"),
    [("\n", "\\n"), ("\r\n", "\\r\\n"), ("\r", "\\r")],
    ids=["lf", "crlf", "cr"],
)
def test_syntax_error_quotes_the_line_end_as_written(ending: str, quoted: str) -> None:
    result = parse_source(f"type A = Int{ending}{ending}type B ={ending}")

    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in result.diagnostics
    ] == [("PIE-P1000", 3, 9, f"no viable alternative at input 'typeB={quoted}'")]


def _has_code(result: ParseResult, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)
