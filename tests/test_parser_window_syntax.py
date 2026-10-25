from __future__ import annotations

import textwrap
from typing import Any, cast


import pytest
from antlr4 import CommonTokenStream, InputStream
from antlr4.ListTokenSource import ListTokenSource
from antlr4.Token import Token

from pietto.errors import Diagnostic, DiagnosticErrorListener, Severity
from pietto.generated.PiettoLexer import PiettoLexer
from pietto.generated.PiettoParser import PiettoParser
from pietto.indentation import (
    find_leading_tab_diagnostics,
    inject_indentation,
    join_parenthesized_lines,
)
from pietto.parser_api import parse_source
from pietto.ast_nodes import NameExpr, QueryDef, WindowExpr


WINDOW_FUNCTION_NAMES = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
)


def _window_query(
    body: str,
    *,
    projection: str = "rn = row_number()",
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
) -> str:
    body_text = textwrap.dedent(body).strip("\n") + "\n"
    return (
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        + "".join(f"        {item}\n" for item in before)
        + f"        {projection} window(\n"
        + textwrap.indent(body_text, "            ")
        + "        )\n"
        + "".join(f"        {item}\n" for item in after)
    )


def _raw_tokens(lexer: PiettoLexer) -> list[Token]:
    tokens: list[Token] = []
    while True:
        token = lexer.nextToken()
        assert token is not None
        tokens.append(token)
        if token.type == Token.EOF:
            return tokens


def _raw_parse(
    source: str,
    *,
    path: str = "slice2-window-raw.pietto",
) -> tuple[Any, tuple[Token, ...], tuple[Diagnostic, ...]]:
    lexer_listener = DiagnosticErrorListener(path)
    lexer = PiettoLexer(InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_listener)
    joined = join_parenthesized_lines(
        _raw_tokens(lexer),
        newline_type=PiettoLexer.NEWLINE,
        open_type=PiettoLexer.LPAREN,
        close_type=PiettoLexer.RPAREN,
        window_type=PiettoLexer.WINDOW,
        colon_type=PiettoLexer.COLON,
        path=path,
    )
    indentation = inject_indentation(
        joined.tokens,
        newline_type=PiettoLexer.NEWLINE,
        indent_type=PiettoParser.INDENT,
        dedent_type=PiettoParser.DEDENT,
        path=path,
    )

    parser_listener = DiagnosticErrorListener(path)
    token_source = ListTokenSource(list(indentation.tokens), path)
    token_stream = CommonTokenStream(cast(Any, token_source))
    parser = PiettoParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(parser_listener)
    tree = parser.script()

    diagnostics = tuple(
        sorted(
            (
                *lexer_listener.diagnostics,
                *joined.diagnostics,
                *find_leading_tab_diagnostics(source, path=path),
                *indentation.diagnostics,
                *parser_listener.diagnostics,
            ),
            key=lambda item: (
                item.location.line,
                item.location.column,
                item.code,
                item.message,
            ),
        )
    )
    return tree, indentation.tokens, diagnostics


def _window_select_items(tree: Any) -> tuple[Any, ...]:
    items: list[Any] = []
    for definition in tree.definition():
        query = definition.queryDefinition()
        table = definition.tableDefinition()
        relation = query if query is not None else table
        if relation is None:
            continue
        items.extend(
            line.selectWindowItem()
            for line in relation.tableBody().selectClause().selectBody().selectLine()
            if line.selectWindowItem() is not None
        )
    return tuple(items)


RAW_POSITIVE_CASES = (
    ("order_only_omitted_direction", _window_query("order by observed_at"), 1),
    (
        "one_partition_one_ascending_order",
        _window_query("partition by account_id order by observed_at asc"),
        1,
    ),
    (
        "multiple_partition_mixed_order",
        _window_query(
            "partition by account_id, region\n"
            "order by observed_at desc, sequence_id asc"
        ),
        1,
    ),
    (
        "blank_lines",
        _window_query("""
            partition by

                account_id

            order by

                observed_at
        """),
        1,
    ),
    (
        "qualified_call",
        _window_query("order by observed_at", projection="rn = analytics.row_number()"),
        1,
    ),
    (
        "arguments_and_trailing_comma",
        _window_query("order by observed_at", projection="previous = lag(value, 1,)"),
        1,
    ),
    (
        "unrelated_function",
        _window_query(
            "partition by account_id", projection="custom_value = custom(value)"
        ),
        1,
    ),
    (
        "two_independent_windows",
        "query ranked:\n    from rows\n    select:\n"
        "        rn = row_number() window(order by observed_at)\n"
        "        previous = lag(value, 1) window(partition by account_id order by observed_at desc)\n",
        2,
    ),
    (
        "surrounding_ordinary_items",
        _window_query("order by observed_at", before=("account_id",), after=("value",)),
        1,
    ),
    ("empty_window", _window_query(""), 1),
    (
        "continuation_at_select_indentation",
        "query ranked:\n    from rows\n    select:\n"
        "        rn = row_number() window(\n"
        "        order by observed_at\n        )\n",
        1,
    ),
    (
        "continuation_indentation",
        "query ranked:\n    from rows\n    select:\n"
        "        rn = row_number() window(\n"
        "            order by observed_at,\n"
        "              sequence_id\n        )\n",
        1,
    ),
    (
        "qualify",
        _window_query("order by observed_at") + "    qualify rn == 1\n",
        1,
    ),
)

GENERIC_EXPRESSION_CASES = (
    ("qualified", "account.id", "events.observed_at"),
    ("arithmetic", "account_id + region_id", "observed_at + 1"),
    ("calls", "lower(region)", "coalesce(observed_at, fallback_at)"),
    ("parenthesized", "(account_id == owner_id)", "(observed_at + offset)"),
)

RAW_NEGATIVE_CASES = (
    (
        "missing_select_indent",
        _window_query("order by observed_at").replace("        rn =", "    rn =", 1),
    ),
    (
        "tab_continuation",
        _window_query("order by observed_at").replace(
            "            order", "\torder", 1
        ),
    ),
    ("empty_partition", _window_query("partition by order by observed_at")),
    ("empty_order", _window_query("order by")),
    (
        "duplicate_partition",
        _window_query(
            "partition by account_id partition by region order by observed_at"
        ),
    ),
    ("duplicate_order", _window_query("order by observed_at order by sequence_id")),
    (
        "partition_after_order",
        _window_query("order by observed_at partition by account_id"),
    ),
    ("unknown_subclause", _window_query("cluster by account_id")),
    ("nulls_first", _window_query("order by observed_at nulls first")),
    ("nulls_last", _window_query("order by observed_at nulls last")),
    (
        "multiple_window_suffixes",
        _window_query("order by observed_at")
        + "        window(order by sequence_id)\n",
    ),
    (
        "suffix_on_non_call_shape",
        _window_query("order by observed_at", projection="rn = (row_number())"),
    ),
    ("malformed_order_item", _window_query("order by observed_at +")),
    (
        "malformed_partition_item",
        _window_query("partition by account_id + order by observed_at"),
    ),
)

FAIL_CLOSED_CASES = (
    (
        "qualified",
        _window_query(
            """
            order by observed_at
            """,
            projection="rn = analytics.row_number()",
        ),
        37,
    ),
    (
        "arguments",
        _window_query(
            """
            order by observed_at
            """,
            projection="previous = lag(value, 1)",
        ),
        34,
    ),
    (
        "unrelated",
        _window_query(
            """
            partition by account_id
            """,
            projection="custom_value = custom(value)",
        ),
        38,
    ),
)

LOWERCASE_WINDOW_IDENTIFIER_CASES = (
    ("query_name", "query window:\n    from rows\n    select:\n        id\n"),
    ("source_name", 'source window = postgres.table("rows")\n'),
    ("table_name", "table window:\n    from rows\n    select:\n        id\n"),
    ("from_relation", "query q:\n    from window\n    select:\n        id\n"),
    ("shape_field", "shape Row:\n    window: Int\n"),
    (
        "selected_alias",
        "query q:\n    from rows\n    select:\n        window = value\n",
    ),
    (
        "let_name",
        "query q:\n    from rows\n    let window = value\n    select:\n        value\n",
    ),
    ("derive_parameter", "derive f(window: Int) -> Int:\n    return window\n"),
    ("dotted_part", 'source s = postgres.window("rows")\n'),
    ("function_name", "source s = window()\n"),
    (
        "relationship_name",
        "relationship window(left: Row, right: Row):\n    left.id == right.id\n",
    ),
    (
        "relationship_parameter",
        "relationship r(window: Row, right: Row):\n    window.id == right.id\n",
    ),
)

CASE_VARIANT_IDENTIFIERS = ("Window", "WINDOW")
CONTEXTUAL_IDENTIFIERS = ("partition", "over")
HISTORICAL_NEGATIVE_SOURCES = (
    (
        "window_clause",
        (
            "query projected:\n"
            "    from input_relation\n"
            "    window recent\n"
            "    select:\n"
            "        id\n"
        ),
    ),
    (
        "sql_over_shape",
        (
            "query projected:\n"
            "    from input_relation\n"
            "    select:\n"
            "        total = sum(amount) over (region)\n"
        ),
    ),
)


def test_compact_window_tokens_and_ast_keep_clause_order() -> None:
    source = _window_query(
        "partition by account_id, region\n"
        "order by observed_at desc, sequence_id asc\n"
        "rows between 2 preceding and current row exclude ties"
    )
    _, tokens, diagnostics = _raw_parse(source)
    assert diagnostics == ()
    start = next(
        i for i, token in enumerate(tokens) if token.type == PiettoLexer.WINDOW
    )
    end = next(
        i for i in range(start, len(tokens)) if tokens[i].type == PiettoLexer.RPAREN
    )
    assert tuple(token.text for token in tokens[start : end + 1]) == (
        "window",
        "(",
        "partition",
        "by",
        "account_id",
        ",",
        "region",
        "order",
        "by",
        "observed_at",
        "desc",
        ",",
        "sequence_id",
        "asc",
        "rows",
        "between",
        "2",
        "preceding",
        "and",
        "current",
        "row",
        "exclude",
        "ties",
        ")",
    )
    result = parse_source(source)
    assert result.diagnostics == () and result.ast is not None
    expression = cast(
        WindowExpr, cast(QueryDef, result.ast.definitions[0]).select_items[0].expression
    )
    assert [cast(NameExpr, item).name for item in expression.spec.partition_by] == [
        "account_id",
        "region",
    ]
    assert [item.direction for item in expression.spec.order_by] == ["desc", "asc"]
    assert expression.spec.frame.kind.value == "between"
    assert expression.spec.frame.exclusion.value == "ties"


@pytest.mark.parametrize(
    ("name", "source", "expected_windows"),
    RAW_POSITIVE_CASES,
    ids=[case[0] for case in RAW_POSITIVE_CASES],
)
def test_raw_parser_accepts_canonical_window_shapes(
    name: str,
    source: str,
    expected_windows: int,
) -> None:
    tree, tokens, diagnostics = _raw_parse(source)
    assert diagnostics == (), name
    public = parse_source(source)
    assert public.diagnostics == () and public.ast is not None, name
    relation = cast(QueryDef, public.ast.definitions[0])
    expressions = tuple(
        item.expression
        for item in relation.select_items
        if isinstance(item.expression, WindowExpr)
    )
    assert len(expressions) == expected_windows
    assert len({id(expression.spec) for expression in expressions}) == expected_windows
    if name == "empty_window":
        assert not expressions[0].spec.has_components
    if name == "continuation_indentation":
        assert len(expressions[0].spec.order_by) == 2
    window_items = _window_select_items(tree)
    assert len(window_items) == expected_windows
    window_tokens = tuple(token for token in tokens if token.type == PiettoLexer.WINDOW)
    assert len(window_tokens) == expected_windows
    assert all(
        item.windowExpression().windowSpec().WINDOW() is not None
        for item in window_items
    )
    if name == "surrounding_ordinary_items":
        assert (window_tokens[0].line, window_tokens[0].column + 1) == (5, 27)


@pytest.mark.parametrize(
    ("name", "partition_expression", "order_expression"),
    GENERIC_EXPRESSION_CASES,
    ids=[case[0] for case in GENERIC_EXPRESSION_CASES],
)
def test_partition_and_order_items_accept_generic_expression_shapes(
    name: str,
    partition_expression: str,
    order_expression: str,
) -> None:
    source = _window_query(
        f"""
        partition by {partition_expression}
        order by {order_expression}
        """
    )
    tree, _, diagnostics = _raw_parse(source)
    assert diagnostics == (), name
    window_spec = _window_select_items(tree)[0].windowExpression().windowSpec()
    compact = window_spec.compactWindowSpec()
    assert len(compact.expression()) == 1
    assert len(compact.orderItem()) == 1
    public = parse_source(source)
    assert public.diagnostics == () and public.ast is not None, name
    expression = cast(
        WindowExpr, cast(QueryDef, public.ast.definitions[0]).select_items[0].expression
    )
    assert len(expression.spec.partition_by) == len(expression.spec.order_by) == 1


@pytest.mark.parametrize(
    ("name", "source"),
    RAW_NEGATIVE_CASES,
    ids=[case[0] for case in RAW_NEGATIVE_CASES],
)
def test_raw_parser_rejects_malformed_or_deferred_window_shapes(
    name: str,
    source: str,
) -> None:
    _, _, diagnostics = _raw_parse(source)
    _, _, repeated = _raw_parse(source)
    assert diagnostics, name
    assert diagnostics == repeated
    public = parse_source(source, path="slice2-window-raw.pietto")
    assert public.ast is None and public.diagnostics, name
    assert all(
        diagnostic.severity is Severity.ERROR
        and diagnostic.location.path == "slice2-window-raw.pietto"
        and diagnostic.location.line >= 1
        and diagnostic.location.column >= 1
        for diagnostic in diagnostics
    )


@pytest.mark.parametrize(
    ("name", "source", "expected_column"),
    FAIL_CLOSED_CASES,
    ids=[case[0] for case in FAIL_CLOSED_CASES],
)
def test_parse_source_fails_closed_before_slice3_ast_preservation(
    name: str,
    source: str,
    expected_column: int,
) -> None:
    result = parse_source(source, path="slice2-window.pietto")
    assert result.ast is not None, name
    assert result.diagnostics == ()
    relation = cast(QueryDef, result.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert isinstance(expression, WindowExpr)
    assert (expression.spec.span.line, expression.spec.span.column) == (
        4,
        expected_column,
    )


@pytest.mark.parametrize(
    ("position", "source"),
    LOWERCASE_WINDOW_IDENTIFIER_CASES,
    ids=[case[0] for case in LOWERCASE_WINDOW_IDENTIFIER_CASES],
)
def test_lowercase_window_is_rejected_in_every_identifier_position(
    position: str,
    source: str,
) -> None:
    result = parse_source(source, path=f"window-{position}.pietto")
    assert result.ast is None, position
    assert result.diagnostics
    assert all(
        diagnostic.code == "PIE-P1000"
        and diagnostic.severity is Severity.ERROR
        and diagnostic.location.path == f"window-{position}.pietto"
        for diagnostic in result.diagnostics
    )


@pytest.mark.parametrize("identifier", CASE_VARIANT_IDENTIFIERS)
def test_case_variant_window_identifiers_remain_accepted(identifier: str) -> None:
    result = parse_source(f"type {identifier} = Int\n")
    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.definitions[0].name == identifier


@pytest.mark.parametrize("identifier", CONTEXTUAL_IDENTIFIERS)
def test_partition_and_over_remain_usable_contextual_identifiers(
    identifier: str,
) -> None:
    result = parse_source(f"type {identifier} = Int\n")
    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.definitions[0].name == identifier


@pytest.mark.parametrize("function_name", WINDOW_FUNCTION_NAMES)
def test_approved_function_names_remain_ordinary_identifiers(
    function_name: str,
) -> None:
    result = parse_source(f"type {function_name} = Int\n")
    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.definitions[0].name == function_name


@pytest.mark.parametrize(
    ("name", "source"),
    HISTORICAL_NEGATIVE_SOURCES,
    ids=[case[0] for case in HISTORICAL_NEGATIVE_SOURCES],
)
def test_historical_unsupported_window_samples_remain_negative(
    name: str,
    source: str,
) -> None:
    result = parse_source(source, path=f"historical-{name}.pietto")
    assert result.ast is None
    assert result.diagnostics
    assert any(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


# Phase 53 Slice 13 reader migration.


def test_window_list_clauses_may_follow_their_header_on_one_line() -> None:
    short = parse_source(
        "query q:\n    from rows\n"
        "    let by_time = window(order by observed_at)\n"
        "    select:\n"
        "        rn = row_number() window(partition by account_id, region order by observed_at desc, id)\n"
    )
    long = parse_source(
        "query q:\n    from rows\n"
        "    let by_time = window(\n        order by observed_at)\n"
        "    select:\n"
        "        rn = row_number() window(\n"
        "            partition by account_id,\n                region\n"
        "            order by observed_at desc,\n                id)\n"
    )
    assert short.diagnostics == long.diagnostics == ()
    assert short.ast is not None and long.ast is not None
    short_query = cast(QueryDef, short.ast.definitions[0])
    long_query = cast(QueryDef, long.ast.definitions[0])
    short_window = cast(WindowExpr, short_query.select_items[0].expression)
    long_window = cast(WindowExpr, long_query.select_items[0].expression)
    assert [type(item).__name__ for item in short_window.spec.partition_by] == [
        "NameExpr",
        "NameExpr",
    ]
    assert [item.direction for item in short_window.spec.order_by] == ["desc", None]
    assert [item.direction for item in long_window.spec.order_by] == ["desc", None]
    assert short_query.named_windows[0].spec is not None
    assert len(short_query.named_windows[0].spec.order_by) == 1


@pytest.mark.parametrize(
    ("body", "line", "column", "suggestion"),
    (
        (
            "    select:\n        rn = row_number() window: order by id\n",
            4,
            33,
            "Use 'window(partition by ... order by ...)' with parentheses.",
        ),
        (
            "    let w = window(order by id)\n"
            "    select:\n        rn = row_number() window w: order by id\n",
            5,
            35,
            "Use 'window(partition by ... order by ...)' with parentheses.",
        ),
        (
            "    select id\n    window w: partition by id\n",
            4,
            5,
            "Name the window with 'let name = window(...)' among the lets after FROM and every JOIN, before 'where', 'group by' and 'select'.",
        ),
        (
            "    select id\n    window w = base: order by id\n",
            4,
            5,
            "Name the window with 'let name = window(...)' among the lets after FROM and every JOIN, before 'where', 'group by' and 'select'.",
        ),
        (
            "    window w: partition by id\n    select id\n",
            3,
            5,
            "Name the window with 'let name = window(...)' among the lets after FROM and every JOIN, before 'where', 'group by' and 'select'.",
        ),
    ),
)
def test_legacy_window_blocks_have_located_modern_rewrites(
    body: str, line: int, column: int, suggestion: str
) -> None:
    result = parse_source("query q:\n    from rows\n" + body)
    assert result.ast is None
    assert [
        (
            item.code,
            item.message,
            item.location.line,
            item.location.column,
            item.suggestion,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1000",
            "This spelling is not accepted by the modern syntax. " + suggestion,
            line,
            column,
            suggestion,
        )
    ]


MOVE_WINDOW = (
    "Move the window before 'select', among the lets after FROM and every JOIN, "
    "before 'where' and 'group by'."
)
WINDOW_LET_HINT = (
    "A named window is a `let` among the lets after FROM and every JOIN, "
    "before `where`, `group by` and `select`."
)
CLAUSE_ORDER = (
    "a relation body lists from, joins, let, where, group by, select, having, "
    "qualify, order by and limit in that order."
)


def test_named_windows_are_lets_after_the_joins_and_before_where() -> None:
    result = parse_source(
        "query q:\n"
        "    from rows\n"
        "    let net = value - 1\n"
        "    let ordered = window(order by observed_at)\n"
        "    let per_account = window ordered(partition by account_id)\n"
        "    where net > 0\n"
        "    select:\n"
        "        rn = row_number() window per_account\n",
        path="windows.pietto",
    )
    assert result.diagnostics == () and result.ast is not None
    query = cast(QueryDef, result.ast.definitions[0])
    assert [
        (item.name, item.span.line, item.span.column) for item in query.named_windows
    ] == [("ordered", 4, 5), ("per_account", 5, 5)]
    assert [item.name for item in query.naming_declarations] == ["net"]
    use = cast(WindowExpr, query.select_items[0].expression)
    assert use.base is not None and use.base.name == "per_account"


def test_named_windows_after_select_are_located_retired_spellings() -> None:
    result = parse_source(
        "query q:\n"
        "    from rows\n"
        "    select:\n"
        "        rn = row_number() window alias\n"
        "    let ordered = window(order by observed_at)\n"
        "    let alias = window ordered\n",
        path="late.pietto",
    )
    assert result.ast is None
    assert [
        (
            item.code,
            item.message,
            item.location.path,
            item.location.line,
            item.location.column,
            item.suggestion,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1000",
            "This spelling is not accepted by the modern syntax. " + MOVE_WINDOW,
            "late.pietto",
            line,
            5,
            MOVE_WINDOW,
        )
        for line in (5, 6)
    ]


@pytest.mark.parametrize(
    ("body", "line", "column", "message"),
    (
        (
            "    let ordered = window(order by id)\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window ordered\n",
            2,
            19,
            "Unexpected 'window'; expected an expression. " + WINDOW_LET_HINT,
        ),
        (
            "    from rows\n"
            "    where id > 0\n"
            "    let ordered = window(order by id)\n"
            "    select:\n"
            "        rn = row_number() window ordered\n",
            4,
            5,
            "Clause `let` is out of order or repeated; " + CLAUSE_ORDER,
        ),
        (
            "    from rows\n"
            "    let ordered = window(order by id)\n"
            "    inner join others on rows.id == others.id\n"
            "    select:\n"
            "        rn = row_number() window ordered\n",
            4,
            5,
            "Clause `join` is out of order or repeated; " + CLAUSE_ORDER,
        ),
    ),
    ids=("before_from", "after_where", "before_a_join"),
)
def test_named_windows_outside_the_lets_are_syntax_errors(
    body: str, line: int, column: int, message: str
) -> None:
    result = parse_source("query q:\n" + body, path="misplaced.pietto")
    assert result.ast is None
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [("PIE-P1000", message, line, column)]
