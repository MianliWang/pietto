from __future__ import annotations

import signal
import sys
from threading import Event, Thread
from typing import Any, cast

import pytest
from antlr4 import CommonTokenStream, InputStream

import pietto.parser_api as parser_api
from pietto.ast_builder import AstBuilder
from pietto.errors import ParseCancelled
from pietto.generated.PiettoLexer import PiettoLexer
from pietto.generated.PiettoParser import PiettoParser
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


_ORDER = (
    "a relation body lists from, joins, let:, where, group by:, select:, "
    "windows, satisfying:, qualify:, order by: and limit in that order."
)
_SHAPE = 'shape R:\n    a: Int not null\nsource r: R is postgres.table("r")\n'


def _query(body: str) -> str:
    return _SHAPE + "query q:\n    from r\n" + body


PRESENTATION_CASES = {
    # Build-time messages come in source order, also within one clause.
    "trailing_comma_before_the_block_after_it": (
        _query("    select: id,\n        amount\n"),
        [
            (
                6,
                15,
                "A trailing comma does not continue a list on the next line; "
                "remove the comma.",
            )
        ],
    ),
    "window_call_before_its_window_use": (
        _query('    select:\n        n = lag("\\q") window: order by: a\n'),
        [(7, 18, 'Unsupported string escape "\\q".')],
    ),
    "type_before_its_ensure": (
        'type T = Text(max = "\\q") ensure self == "\\z"\n',
        [(1, 22, 'Unsupported string escape "\\q".')],
    ),
    "def_parameter_before_its_return_type": (
        'def f(x: Int) -> Text(max = "\\q") not null: return 1\n',
        [
            (
                1,
                10,
                "A `def` parameter must state its nullability: write `nullable` "
                "or `not null` after the type.",
            )
        ],
    ),
    "def_parameter_before_a_later_parameter": (
        'def f(x: Int, y: Text(max = "\\q") not null) -> Int not null: return x\n',
        [
            (
                1,
                10,
                "A `def` parameter must state its nullability: write `nullable` "
                "or `not null` after the type.",
            )
        ],
    ),
    "condition_line_before_the_lines_after_it": (
        _query('    where:\n        "\\q" == a\n        and b\n    select: a\n'),
        [(7, 10, 'Unsupported string escape "\\q".')],
    ),
    "header_line_item_before_its_trailing_comma": (
        _query('    select: x = "\\q",\n'),
        [(6, 18, 'Unsupported string escape "\\q".')],
    ),
    "block_line_item_before_its_trailing_comma": (
        _query('    select:\n        x = "\\q",\n'),
        [(7, 14, 'Unsupported string escape "\\q".')],
    ),
    "number_before_its_trailing_comma": (
        _query("    select: x = 1" + "0" * 5000 + ",\n"),
        [
            (
                6,
                17,
                "Numeric literal exceeds the maximum supported length of 4096 "
                "characters.",
            )
        ],
    ),
    "ordinal_group_by_before_its_trailing_comma": (
        _query("    group by: 1,\n    select: a\n"),
        [(6, 15, "Ordinal GROUP BY expressions are not supported.")],
    ),
    # Whitespace the lexer does not know is the cause in a line's indentation.
    "form_feed_in_indentation": (
        _query("\x0c    select: a\n"),
        [(6, 1, "Unexpected character U+000C in indentation; indent with spaces.")],
    ),
    "no_break_space_in_indentation": (
        _query("\u00a0   select: a\n"),
        [(6, 1, "Unexpected character U+00A0 in indentation; indent with spaces.")],
    ),
    "stray_character_starts_its_own_declaration": (
        "shape A:\n    id Int\n$\nshape B:\n    id: Int not null\n",
        [
            (2, 8, "Missing ':' before 'Int'."),
            (
                3,
                1,
                "Unexpected '$'; expected a declaration, end of file or end of line.",
            ),
        ],
    ),
    # Build-time messages appear only without parser errors, first in the file.
    "only_the_first_build_message": (
        "relationship r: a.x < b.y\nenum A: a, b,\nenum B: c, d,\n",
        [
            (
                1,
                17,
                "A one-line relationship compares fields of two different relations "
                "with `==`, joined by `and`, as in `a.x == b.y`; use the endpoint "
                "block form for any other match.",
            )
        ],
    ),
    "build_messages_wait_for_parser_errors": (
        "enum A: a, b,\ntype T = = Int\n",
        [(2, 10, "Unexpected '='.")],
    ),
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
            (
                18,
                19,
                "Unexpected 'as'; expected ',' or end of line. Name a select output with "
                "`name = expression`.",
            ),
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


_EARLIER = (
    "constraint valid(email: Text not null) -> Bool not null:\n"
    '    matches(email, ".+@.+":)\n'
)
_LATER = (
    "query tagged:\n    from generate_series(3, 1:, -1) as n\n    select:\n        n\n"
)


def test_syntax_error_text_does_not_depend_on_earlier_parses() -> None:
    # Recovering from the stray ':' used to grow the expected-token set that
    # ANTLR caches for the whole process, so a later file listed operators and
    # clauses that cannot follow its own ':'.
    expected = "Unexpected ':'; expected ')' or ','."
    for source in (_LATER, _EARLIER, _LATER, _EARLIER):
        assert [item.message for item in parse_source(source).diagnostics] == [expected]


_ANNOTATION_CALL = 'shape User:\n    id: UUID @pii("yes")\n'
_CAPTURE_ONLY_LET = "query result:\n    let same:\n        capture second\n"
_FIRST_PARSE_MESSAGES = {
    _ANNOTATION_CALL: [
        ("PIE-P1000", 2, 18, "Unexpected '('; expected 'ensure', '@' or end of line.")
    ],
    _CAPTURE_ONLY_LET: [
        (
            "PIE-P1000",
            3,
            23,
            "Unexpected end of block; expected 'from', 'union', 'intersect', "
            "'except', 'values', 'capture' or end of line.",
        )
    ],
}


def test_a_file_parsed_again_after_another_keeps_its_exact_messages() -> None:
    for source in (_ANNOTATION_CALL, _CAPTURE_ONLY_LET, _ANNOTATION_CALL):
        assert [
            (item.code, item.location.line, item.location.column, item.message)
            for item in parse_source(source).diagnostics
        ] == _FIRST_PARSE_MESSAGES[source]


def test_error_recovery_leaves_the_shared_expected_token_cache_unchanged() -> None:
    for source in (
        _EARLIER,
        _LATER,
        "enum E:\n    a b\n",
        "shape S:\n    a Int\n",
        _ANNOTATION_CALL,
        _CAPTURE_ONLY_LET,
    ):
        parse_source(source)

    atn = PiettoParser.atn

    def spans(found: Any) -> tuple[tuple[int, int], ...]:
        return tuple((item.start, item.stop) for item in found.intervals)

    grown = [
        state.stateNumber
        for state in atn.states
        if state.nextTokenWithinRule is not None
        and spans(state.nextTokenWithinRule)
        != spans(atn.nextTokensInContext(state, None))
    ]
    assert grown == []


# The deepest nesting each shape reached in some position before the layout
# rules; every position must still accept it.
_BASE_NESTING = {
    "unary": (314, lambda n: "-" * n + "a"),
    "not": (235, lambda n: "not " * n + "b"),
    "parentheses": (25, lambda n: "(" * n + "a" + ")" * n),
    "calls": (24, lambda n: "abs(" * n + "a" + ")" * n),
    "if_else": (235, lambda n: "a if b else " * n + "a"),
    "binary": (25, lambda n: "a + (" * n + "a" + ")" * n),
    "comparison": (25, lambda n: "(a == " * n + "a" + ")" * n),
}
_ROWS = (
    'shape R:\n    a: Int not null\n    b: Bool not null\nsource r: R is postgres.table("r")\n'
    "query q:\n    from r\n"
)
_NESTING_POSITIONS = {
    "select_alias": lambda e: _ROWS + "    select:\n        y = " + e + "\n",
    "select_item": lambda e: _ROWS + "    select:\n        " + e + "\n",
    "where": lambda e: _ROWS + "    where " + e + "\n    select:\n        a\n",
    "let": lambda e: (
        _ROWS + "    let:\n        y = " + e + "\n    select:\n        a\n"
    ),
    "order_by": lambda e: (
        _ROWS + "    select:\n        a\n    order by:\n        " + e + "\n"
    ),
    "satisfying": lambda e: (
        _ROWS + "    group by:\n        a\n    select:\n        a\n"
        "    satisfying:\n        " + e + "\n"
    ),
    "qualify": lambda e: (
        _ROWS + "    select:\n        a\n    qualify:\n        " + e + "\n"
    ),
    "derive": lambda e: "derive d() -> Int not null:\n    " + e + "\n",
    "check": lambda e: (
        "shape S:\n    a: Int not null\n    b: Bool not null\n    check c:\n        "
        + e
        + "\n"
    ),
}


@pytest.mark.parametrize("position", sorted(_NESTING_POSITIONS))
@pytest.mark.parametrize("shape", sorted(_BASE_NESTING))
def test_nesting_accepted_before_the_layout_rules_still_parses(
    shape: str, position: str
) -> None:
    depth, build = _BASE_NESTING[shape]
    result = parse_source(_NESTING_POSITIONS[position](build(depth)))
    assert result.diagnostics == () and result.ast is not None


# In an argument list the parser itself sets the limit; these are the depths a
# caller at module level reached there before the layout rules.
_ARGUMENT_POSITIONS = {
    "type_argument": lambda e: "type T = Text(max = " + e + ")\n",
    "window_argument": lambda e: (
        _ROWS + "    select:\n        w = lag(" + e + ") window:\n"
        "            order by:\n                a\n"
    ),
    "named_window_argument": lambda e: (
        _ROWS + "    select:\n        w = lag(" + e + ") window x\n"
        "    window x:\n        order by:\n            a\n"
    ),
    "call_argument": lambda e: _ROWS + "    select:\n        y = abs(" + e + ")\n",
    "qualify_window_argument": lambda e: (
        _ROWS + "    select:\n        a\n    qualify:\n        lag(" + e + ") window:\n"
        "            order by:\n                a\n        > 1\n"
    ),
}
_ARGUMENT_NESTING = {
    "type_argument": {"unary": 304, "not": 233, "if_else": 182, "parentheses": 25},
    "window_argument": {"unary": 304, "not": 232, "if_else": 182, "parentheses": 25},
    "named_window_argument": {
        "unary": 304,
        "not": 232,
        "if_else": 182,
        "parentheses": 25,
    },
    "call_argument": {"unary": 298, "not": 224, "if_else": 182, "parentheses": 24},
    "qualify_window_argument": {
        "unary": 297,
        "not": 223,
        "if_else": 181,
        "parentheses": 24,
    },
}


@pytest.mark.parametrize("position", sorted(_ARGUMENT_POSITIONS))
@pytest.mark.parametrize("shape", ("unary", "not", "if_else", "parentheses"))
def test_nesting_in_an_argument_list_still_parses(shape: str, position: str) -> None:
    depth = _ARGUMENT_NESTING[position][shape]
    _, build = _BASE_NESTING[shape]
    result = parse_source(_ARGUMENT_POSITIONS[position](build(depth)))
    assert result.diagnostics == () and result.ast is not None


def test_recursion_exhaustion_is_reported_at_its_declaration() -> None:
    source = _query("    select: y = " + "(" * 400 + "a" + ")" * 400 + "\n")
    limit = sys.getrecursionlimit()
    try:
        located = []
        for budget in (limit, limit + 500):
            sys.setrecursionlimit(budget)
            located.append(parse_source(source).diagnostics)
    finally:
        sys.setrecursionlimit(limit)
    assert located[0] == located[1]
    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in located[0]
    ] == [
        (
            "PIE-P1000",
            4,
            1,
            "Parser recursion limit exceeded while processing source.",
        )
    ]


@pytest.mark.skipif(not hasattr(signal, "setitimer"), reason="needs POSIX timers")
def test_an_interrupted_parse_is_cancelled_before_the_call_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long = _SHAPE + "".join(
        f"query q{index}:\n    from r\n    where a > {index}\n    select: a\n"
        for index in range(3000)
    )
    ends: list[str] = []
    parse = parser_api._parse_source

    def recorded(source: str, *, path: object, cancel: Any) -> ParseResult:
        try:
            result = parse(source, path=cast(Any, path), cancel=cancel)
        except ParseCancelled:
            ends.append("cancelled")
            raise
        ends.append("finished")
        return result

    monkeypatch.setattr(parser_api, "_parse_source", recorded)

    class Interrupted(Exception):
        pass

    def interrupt(signum: int, frame: object) -> None:
        raise Interrupted

    previous = signal.signal(signal.SIGALRM, interrupt)
    try:
        signal.setitimer(signal.ITIMER_REAL, 0.05)
        with pytest.raises(Interrupted):
            parse_source(long)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
    # The parse stopped at a cancellation check, and before the call returned.
    assert ends == ["cancelled"]
    assert parse_source(_query("    select: a\n")).diagnostics == ()


def test_a_cancelled_parse_stops_at_its_next_token_or_node() -> None:
    source = _query("    select: a\n")
    cancel = Event()
    cancel.set()
    with pytest.raises(ParseCancelled):
        parser_api._parse_source(source, path=None, cancel=cancel)
    tree = PiettoParser(CommonTokenStream(PiettoLexer(InputStream(source)))).script()
    with pytest.raises(ParseCancelled):
        AstBuilder(None, cancel=cancel).visit(tree)


def test_a_cancelled_parse_stops_in_tokens_a_lookahead_already_fetched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Deciding what the select line holds fetches the whole call first.
    chain = " + ".join(["a"] * 2000)
    source = _query(f"    select:\n        x = f({chain})\n")
    cancel = Event()
    after: list[str] = []

    class Watched(parser_api._PiettoParser):
        def consume(self) -> Any:
            token: Any = super().consume()
            if cancel.is_set():
                after.append(token.text)
            elif token.text == "f":
                cancel.set()
            return token

    monkeypatch.setattr(parser_api, "_PiettoParser", Watched)
    with pytest.raises(ParseCancelled):
        parser_api._parse_source(source, path=None, cancel=cancel)
    assert after == []


def test_a_cancelled_parse_stops_inside_one_long_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = "# " + "a" * 100_000 + "\n" + _query("    select: a\n")
    cancel = Event()
    lexers: list[PiettoLexer] = []

    class Watched(PiettoLexer):
        def nextToken(self) -> Any:
            lexers.append(self)
            cancel.set()
            return super().nextToken()

    monkeypatch.setattr(parser_api, "PiettoLexer", Watched)
    with pytest.raises(ParseCancelled):
        parser_api._parse_source(source, path=None, cancel=cancel)
    # It stopped inside the comment, long before the comment's end.
    assert len(lexers) == 1 and lexers[0].inputStream.index <= 4096


def test_a_parse_without_a_free_thread_runs_on_the_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def no_thread(*_: object) -> int:
        raise RuntimeError("can't start new thread")

    monkeypatch.setattr(parser_api, "start_new_thread", no_thread)
    result = parse_source(_query("    select: a\n"))
    assert result.diagnostics == () and result.ast is not None


def test_a_refused_thread_start_is_raised_without_waiting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Refused(Exception):
        pass

    def refused(*_: object) -> int:  # such as an audit hook, before any thread
        raise Refused

    monkeypatch.setattr(parser_api, "start_new_thread", refused)
    raised: list[BaseException] = []

    def call() -> None:
        try:
            parse_source(_query("    select: a\n"))
        except Refused as error:
            raised.append(error)

    caller = Thread(target=call, daemon=True)
    caller.start()
    caller.join(timeout=10)
    assert not caller.is_alive() and len(raised) == 1


class _Interrupted(Exception):
    pass


def _interrupted_in_time(source: str) -> bool:
    """Parse on a helper thread, so that a hang fails the test, not the run."""

    raised: list[BaseException] = []

    def call() -> None:
        try:
            parse_source(source)
        except _Interrupted as error:
            raised.append(error)

    caller = Thread(target=call, daemon=True)
    caller.start()
    caller.join(timeout=10)
    return not caller.is_alive() and len(raised) == 1


def test_an_interrupt_as_a_finished_parse_is_handed_over_does_not_wait_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_lock, real_start = parser_api.allocate_lock, parser_api.start_new_thread
    ended = Event()

    class HandOver:
        """A lock whose second acquire, the wait, takes it and is interrupted."""

        def __init__(self) -> None:
            self.lock = real_lock()
            self.acquires = 0

        def acquire(self) -> bool:
            self.acquires += 1
            taken = self.lock.acquire()
            if self.acquires == 2:
                raise _Interrupted
            return taken

        def release(self) -> None:
            self.lock.release()

    def start(function: Any, arguments: tuple[object, ...]) -> int:
        def run() -> None:
            function(*arguments)
            ended.set()

        return real_start(run, ())

    monkeypatch.setattr(parser_api, "allocate_lock", HandOver)
    monkeypatch.setattr(parser_api, "start_new_thread", start)
    assert _interrupted_in_time(_query("    select: a\n"))
    assert ended.wait(10)  # and the parse thread has ended


def test_an_interrupt_as_the_parse_thread_starts_cancels_the_parse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    long = _SHAPE + "".join(
        f"query q{index}:\n    from r\n    where a > {index}\n    select: a\n"
        for index in range(3000)
    )
    ends: list[str] = []
    parse = parser_api._parse_source
    ended = Event()

    def recorded(source: str, *, path: object, cancel: Any) -> ParseResult:
        try:
            result = parse(source, path=cast(Any, path), cancel=cancel)
        except ParseCancelled:
            ends.append("cancelled")
            raise
        ends.append("finished")
        return result

    def starting(start: Any, functions: Any, arguments: Any) -> Any:
        """``map`` interrupted just after it returned the started thread."""

        for function, function_arguments in zip(functions, arguments, strict=True):

            def run() -> None:
                function(*function_arguments)
                ended.set()

            yield start(run, ())
            raise _Interrupted

    monkeypatch.setattr(parser_api, "_parse_source", recorded)
    monkeypatch.setattr(parser_api, "map", starting, raising=False)
    assert _interrupted_in_time(long)
    assert ends == ["cancelled"]
    assert ended.wait(10)  # and the parse thread has ended
