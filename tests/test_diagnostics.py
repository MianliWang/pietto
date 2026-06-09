from __future__ import annotations

import pytest

from pietto.parser_api import parse_source


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


def _has_code(result: object, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)
