from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, cast


import pytest
from antlr4 import CommonTokenStream, InputStream
from antlr4.ListTokenSource import ListTokenSource
from antlr4.Token import Token

from pietto.errors import Diagnostic, DiagnosticErrorListener, Severity
from pietto.generated.PiettoLexer import PiettoLexer
from pietto.generated.PiettoParser import PiettoParser
from pietto.indentation import find_leading_tab_diagnostics, inject_indentation
from pietto.parser_api import parse_source
from pietto.ast_nodes import QueryDef, WindowExpr


REPO_ROOT = Path(__file__).resolve().parents[1]
GRAMMAR_REL = "grammar/Pietto.g4"
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
FAIL_CLOSED_MESSAGE = (
    "Window syntax is recognized, but WindowSpec AST preservation starts in "
    "Phase 53 Slice 3."
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


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
        + f"        {projection} window:\n"
        + textwrap.indent(body_text, "            ")
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
    indentation = inject_indentation(
        _raw_tokens(lexer),
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
        items.extend(relation.tableBody().selectClause().selectBody().selectItem())
    return tuple(item for item in items if item.windowExpression() is not None)


RAW_POSITIVE_CASES = (
    (
        "order_only_omitted_direction",
        _window_query("""
            order by:
                observed_at
        """),
        1,
    ),
    (
        "one_partition_one_ascending_order",
        _window_query("""
            partition by:
                account_id
            order by:
                observed_at asc
        """),
        1,
    ),
    (
        "multiple_partition_mixed_order",
        _window_query("""
            partition by:
                account_id
                region
            order by:
                observed_at desc
                sequence_id asc
        """),
        1,
    ),
    (
        "blank_lines",
        _window_query("""

            partition by:

                account_id

            order by:

                observed_at

        """),
        1,
    ),
    (
        "qualified_call",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="rn = analytics.row_number()",
        ),
        1,
    ),
    (
        "arguments_and_trailing_comma",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="previous = lag(value, 1,)",
        ),
        1,
    ),
    (
        "unrelated_function",
        _window_query(
            """
            partition by:
                account_id
            """,
            projection="custom_value = custom(value)",
        ),
        1,
    ),
    (
        "two_independent_windows",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "            order by:\n"
            "                observed_at\n"
            "        previous = lag(value, 1) window:\n"
            "            partition by:\n"
            "                account_id\n"
            "            order by:\n"
            "                observed_at desc\n"
        ),
        2,
    ),
    (
        "surrounding_ordinary_items",
        _window_query(
            """
            order by:
                observed_at
            """,
            before=("account_id",),
            after=("value",),
        ),
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
        "missing_window_colon",
        _window_query("""
            order by:
                observed_at
        """).replace(" window:\n", " window\n", 1),
    ),
    (
        "missing_outer_window_indent",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "        order by:\n"
            "            observed_at\n"
        ),
    ),
    (
        "inconsistent_nested_indent",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "            order by:\n"
            "                observed_at\n"
            "              sequence_id\n"
        ),
    ),
    (
        "empty_window",
        "query ranked:\n    from rows\n    select:\n        rn = row_number() window:\n",
    ),
    (
        "empty_partition",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "            partition by:\n"
            "            order by:\n"
            "                observed_at\n"
        ),
    ),
    (
        "empty_order",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "            order by:\n"
        ),
    ),
    (
        "duplicate_partition",
        _window_query("""
            partition by:
                account_id
            partition by:
                region
            order by:
                observed_at
        """),
    ),
    (
        "duplicate_order",
        _window_query("""
            order by:
                observed_at
            order by:
                sequence_id
        """),
    ),
    (
        "partition_after_order",
        _window_query("""
            order by:
                observed_at
            partition by:
                account_id
        """),
    ),
    (
        "unknown_subclause",
        _window_query("""
            cluster by:
                account_id
        """),
    ),
    (
        "named_window_reference",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window recent\n"
        ),
    ),
    (
        "named_window_declaration",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "    window recent:\n"
            "        order by:\n"
            "            observed_at\n"
        ),
    ),
    (
        "nulls_first",
        _window_query("""
            order by:
                observed_at nulls first
        """),
    ),
    (
        "nulls_last",
        _window_query("""
            order by:
                observed_at nulls last
        """),
    ),
    (
        "qualify",
        _window_query("""
            order by:
                observed_at
        """)
        + "    qualify rn == 1\n",
    ),
    (
        "multiple_window_suffixes",
        _window_query("""
            order by:
                observed_at
        """)
        + "        window:\n            order by:\n                sequence_id\n",
    ),
    (
        "suffix_on_non_call_shape",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="rn = (row_number())",
        ),
    ),
    (
        "malformed_order_item",
        _window_query("""
            order by:
                observed_at +
        """),
    ),
    (
        "malformed_partition_item",
        _window_query("""
            partition by:
                account_id +
            order by:
                observed_at
        """),
    ),
)

FAIL_CLOSED_CASES = (
    (
        "order_only",
        _window_query("""
            order by:
                observed_at
        """),
        27,
    ),
    (
        "qualified",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="rn = analytics.row_number()",
        ),
        37,
    ),
    (
        "arguments",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="previous = lag(value, 1)",
        ),
        34,
    ),
    (
        "unrelated",
        _window_query(
            """
            partition by:
                account_id
            """,
            projection="custom_value = custom(value)",
        ),
        38,
    ),
)

LOWERCASE_WINDOW_IDENTIFIER_CASES = (
    ("query_name", "query window:\n    from rows\n    select:\n        id\n"),
    ("source_name", 'source window is postgres.table("rows")\n'),
    ("table_name", "table window:\n    from rows\n    select:\n        id\n"),
    ("from_relation", "query q:\n    from window\n    select:\n        id\n"),
    ("shape_field", "shape Row:\n    window: Int\n"),
    (
        "selected_alias",
        "query q:\n    from rows\n    select:\n        window = value\n",
    ),
    (
        "let_name",
        "query q:\n    from rows\n    let:\n        window = value\n    select:\n        value\n",
    ),
    ("derive_parameter", "derive f(window: Int) -> Int:\n    window\n"),
    ("dotted_part", 'source s is postgres.window("rows")\n'),
    ("function_name", "source s is window()\n"),
    (
        "relationship_name",
        "relationship window:\n    endpoint left: rows\n    endpoint right: rows\n",
    ),
    (
        "endpoint_local_name",
        "relationship r:\n    endpoint window: rows\n    endpoint right: rows\n",
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


def test_candidate_b_global_window_and_contextual_keyword_policy_is_locked() -> None:
    grammar = _read(GRAMMAR_REL)
    assert "WINDOW: 'window';" in grammar
    assert "PARTITION: 'partition';" in grammar
    identifier_token = grammar.index("IDENTIFIER\n    :")
    assert grammar.index("WINDOW: 'window';") < identifier_token
    assert grammar.index("PARTITION: 'partition';") < identifier_token
    for token in (
        "ROWS",
        "RANGE",
        "GROUPS",
        "CURRENT",
        "ROW",
        "UNBOUNDED",
        "PRECEDING",
        "FOLLOWING",
    ):
        assert grammar.index(f"{token}: '{token.lower()}';") < identifier_token
    identifier_start = grammar.index("\nidentifier\n") + 1
    call_suffix_start = grammar.index("\ncallSuffix\n") + 1
    name_part_start = grammar.index("\nnamePart\n") + 1
    identifier_rule = grammar[identifier_start:call_suffix_start]
    name_part_rule = grammar[name_part_start:identifier_start]
    assert "| PARTITION" in identifier_rule
    assert all(
        f"| {token}" in identifier_rule
        for token in (
            "ROWS",
            "RANGE",
            "GROUPS",
            "CURRENT",
            "ROW",
            "UNBOUNDED",
            "PRECEDING",
            "FOLLOWING",
        )
    )
    assert "WINDOW" not in identifier_rule
    assert "WINDOW" not in name_part_rule
    assert "OVER:" not in grammar
    for name in WINDOW_FUNCTION_NAMES:
        assert f"{name.upper()}:" not in grammar


def test_combined_grammar_rules_and_token_order_are_exact() -> None:
    grammar = _read(GRAMMAR_REL)
    normalized = " ".join(grammar.split())
    for rule in (
        "selectItem : identifier ASSIGN windowExpression | identifier ASSIGN expression NEWLINE | expression NEWLINE ;",
        "windowExpression : dottedName callSuffix windowSpec ;",
        "windowSpec : WINDOW COLON NEWLINE NEWLINE* INDENT windowSpecBody DEDENT ;",
        "windowSpecBody : NEWLINE* partitionByClause NEWLINE* orderByClause? NEWLINE* windowFrameClause? NEWLINE* | NEWLINE* orderByClause NEWLINE* windowFrameClause? NEWLINE* | NEWLINE* windowFrameClause NEWLINE* ;",
        "partitionByClause : PARTITION BY COLON NEWLINE NEWLINE* INDENT windowPartitionBody DEDENT ;",
        "windowPartitionBody : NEWLINE* windowPartitionItem (windowPartitionItem | NEWLINE)* ;",
        "windowPartitionItem : expression NEWLINE ;",
        "windowFrameClause : (ROWS | RANGE | GROUPS) (BETWEEN frameBound AND frameBound | frameBound) NEWLINE ;",
        "frameBound : UNBOUNDED (PRECEDING | FOLLOWING) | CURRENT ROW | expression (PRECEDING | FOLLOWING) ;",
    ):
        assert rule in normalized, rule
    assert normalized.count("windowExpression :") == 1
    assert normalized.count("windowSpec :") == 1
    assert normalized.count("partitionByClause :") == 1
    assert normalized.count("windowFrameClause :") == 1
    assert normalized.count("frameBound :") == 1


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
        partition by:
            {partition_expression}
        order by:
            {order_expression}
        """
    )
    tree, _, diagnostics = _raw_parse(source)
    assert diagnostics == (), name
    window_spec = _window_select_items(tree)[0].windowExpression().windowSpec()
    assert (
        len(
            window_spec.windowSpecBody()
            .partitionByClause()
            .windowPartitionBody()
            .windowPartitionItem()
        )
        == 1
    )
    assert (
        len(window_spec.windowSpecBody().orderByClause().orderByBody().orderItem()) == 1
    )


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
    assert FAIL_CLOSED_MESSAGE not in repr(result)


def test_fail_closed_diagnostic_code_message_and_window_location_are_exact() -> None:
    source = _window_query("""
        partition by:
            account_id
            region
        order by:
            observed_at desc
            sequence_id
    """)
    result = parse_source(source, path="slice2-window.pietto")
    assert result.ast is not None
    assert result.diagnostics == ()
    relation = cast(QueryDef, result.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert isinstance(expression, WindowExpr)
    assert expression.span.path == "slice2-window.pietto"
    assert (expression.spec.span.line, expression.spec.span.column) == (4, 27)
    assert FAIL_CLOSED_MESSAGE not in repr(result)


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
