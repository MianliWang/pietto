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


def _has_code(result: ParseResult, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)


_ORDER = (
    "a relation body lists from, joins, let:, where, group by:, select:, "
    "windows, satisfying:, qualify:, order by: and limit in that order."
)
_SHAPE = 'shape R:\n    a: Int not null\nsource r: R is postgres.table("r")\n'


def _query(body: str) -> str:
    return _SHAPE + "query q:\n    from r\n" + body


PRESENTATION_CASES = {
    "clause_after_select": (
        _query("    select:\n        a\n    where a > 1\n"),
        [(8, 5, "Clause `where` is out of order or repeated; " + _ORDER)],
    ),
    "repeated_clause": (
        _query("    where a > 1\n    where a < 9\n    select: a\n"),
        [(7, 5, "Clause `where` is out of order or repeated; " + _ORDER)],
    ),
    "unknown_clause_with_hint": (
        _query("    select: a\n    having a > 1\n"),
        [
            (
                7,
                5,
                "Unknown clause 'having'; "
                + _ORDER
                + " Filter groups with `satisfying:` after `select:`.",
            )
        ],
    ),
    "missing_select_located_after_the_last_clause": (
        _query("    where a > 1\n\n"),
        [(6, 16, "Missing `select:` clause; " + _ORDER)],
    ),
    "header_line_then_block": (
        _query("    select: a\n        b\n"),
        [
            (
                7,
                9,
                "This clause already has its content on the header line after "
                "':'; an indented block cannot follow it.",
            )
        ],
    ),
    "unexpected_indentation": (
        "    type T = Int\n",
        [(1, 5, "Unexpected indentation.")],
    ),
    "expected_block": (
        "enum Status:\ndraft\n",
        [(2, 1, "Expected an indented block after ':'.")],
    ),
    "missing_colon": (
        "query q\n    from r\n    select: a\n",
        [(1, 8, "Missing ':' before end of line.")],
    ),
    "block_header_without_colon": (
        _query("    select\n        a\n"),
        [
            (
                6,
                11,
                "Unexpected end of line. A clause header ends with ':'; its items "
                "follow on the same line or in an indented block.",
            )
        ],
    ),
    "list_header_without_colon": (
        _query("    group by a\n    select: a\n"),
        [
            (
                6,
                14,
                "Unexpected 'a'. A clause header ends with ':'; its items follow "
                "on the same line or in an indented block.",
            )
        ],
    ),
    "expression_set_and_line_break_hint": (
        _query("    where a > 1 and\n    select: a\n"),
        [
            (
                6,
                20,
                "Unexpected end of line; expected an expression. A line break "
                "ends the clause unless it is inside parentheses.",
            )
        ],
    ),
    "declaration_set": (
        _SHAPE + "-- note\n",
        [
            (
                4,
                1,
                "Unexpected '-'; expected a declaration, end of file or end of "
                "line. Comments start with `#`.",
            )
        ],
    ),
    "assignment_compares_with_double_equals": (
        _query("    where a = 1\n    select: a\n"),
        [
            (
                6,
                13,
                "Unexpected '='; expected end of line. Compare with `==`; `=` "
                "only names a select output, a let binding or a type argument.",
            )
        ],
    ),
    "uppercase_keyword": (
        _query("    where a > 1 AND a < 9\n    select: a\n"),
        [
            (
                6,
                17,
                "Unexpected 'AND'; expected end of line. Keywords are lowercase: "
                "write `and`.",
            )
        ],
    ),
    "star_count_distinct_over_case_as": (
        _query(
            "    select: n = count(*)\n"
            "query q2:\n    from r\n    select: n = count(distinct a)\n"
            "query q3:\n    from r\n    select: n = rank() over (a)\n"
            "query q4:\n    from r\n    select: n = case when a\n"
            "query q5:\n    from r\n    select: a * 2 as b\n"
        ),
        [
            (
                6,
                23,
                "Unexpected '*'. `*` is not supported; write `count()` or list "
                "the fields.",
            ),
            (
                9,
                32,
                "Unexpected 'a'. Write `count_distinct(x)` for COUNT(DISTINCT x).",
            ),
            (
                12,
                24,
                "Unexpected 'over'. A window function takes `window:` with an "
                "indented block or `window name`, not OVER (...).",
            ),
            (
                15,
                22,
                "Unexpected 'when'. Write `a if condition else b` instead of CASE.",
            ),
            (18, 19, "Unexpected 'as'. Name a select output with `name = expression`."),
        ],
    ),
    "not_equal_semicolon_and_join_kind": (
        _query(
            "    where a <> 1\n    select: a\n"
            "query q2:\n    from r\n    select: a;\n"
            "query q3:\n    from r\n    join r as s:\n        from r\n    select: a\n"
        ),
        [
            (
                6,
                14,
                "Unexpected '>'; expected an expression. Write `!=` for not-equal.",
            ),
            (10, 14, "Unexpected ';'. Lines do not end with `;`."),
            (
                13,
                5,
                "Unknown clause 'join'; "
                + _ORDER
                + " A JOIN starts with its kind: `inner`, `left`, `cross`, `right`, "
                "`full`, `semi` or `anti`.",
            ),
        ],
    ),
    "unterminated_string_hides_its_follow_on_errors": (
        _query('    where lower(a == "paid\n    select: a\n'),
        [
            (
                6,
                22,
                "Unterminated string literal; close it with a matching quote on "
                "the same line.",
            )
        ],
    ),
    "controls_and_invisible_marks_are_escaped": (
        "type \u009bT = Int\ntype U\u2028 = Int\ntype V\x1b = Int\ntype W\x7f = Int\n",
        [
            (
                1,
                6,
                "Unexpected '\\u009b'. Names use ASCII letters, digits and `_`.",
            ),
            (
                2,
                7,
                "Unexpected '\\u2028'. Names use ASCII letters, digits and `_`.",
            ),
            # C0 controls and DEL use the CLI's \xNN spelling.
            (3, 7, "Unexpected '\\x1b'."),
            (4, 7, "Unexpected '\\x7f'."),
        ],
    ),
}


@pytest.mark.parametrize("case", sorted(PRESENTATION_CASES))
def test_syntax_errors_name_the_problem_once_per_declaration(case: str) -> None:
    source, expected = PRESENTATION_CASES[case]
    result = parse_source(source)

    assert result.ast is None
    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in result.diagnostics
    ] == [("PIE-P1000", *item) for item in expected]


def test_brace_blocks_report_only_the_braces() -> None:
    result = parse_source("shape R {\n    a: Int\n}\nshape S\n")

    assert [(item.code, item.location.line) for item in result.diagnostics] == [
        ("PIE-P1005", 1),
        ("PIE-P1005", 3),
        ("PIE-P1000", 4),
    ]


def test_syntax_error_text_does_not_depend_on_earlier_parses() -> None:
    source = "query r2:\n    from r1\n    select:\n\n"
    first = parse_source(source).diagnostics
    for warm in (
        _query("    select: a\n"),
        "query a:\n    from b\n    select:\n        c\n",
        source,
    ):
        parse_source(warm)
    assert parse_source(source).diagnostics == first
    assert [item.message for item in first] == ["Expected an indented block after ':'."]


def test_deep_nesting_parses_and_recursion_is_reported_where_it_happens() -> None:
    def nested(depth: int) -> str:
        return _query("    select: y = " + "(" * depth + "a" + ")" * depth + "\n")

    assert parse_source(nested(90)).diagnostics == ()

    def at_depth(frames: int) -> ParseResult:
        return parse_source(nested(400)) if frames == 0 else at_depth(frames - 1)

    shallow, deep = at_depth(0), at_depth(200)
    assert shallow.diagnostics == deep.diagnostics
    (diagnostic,) = shallow.diagnostics
    assert (
        diagnostic.message == "Parser recursion limit exceeded while processing source."
    )
    assert diagnostic.location.line == 6 and diagnostic.location.column > 17
