from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    FromClause,
    IsNullExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    ShapeDef,
    SourceDef,
    Span,
    TableDef,
    WhereClause,
)
from pietto.parser_api import parse_file, parse_source


def test_minimal_query_parses() -> None:
    result = parse_source(
        "query active_user_emails:\n    from active_users\n    select:\n        email\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, QueryDef)
    assert definition.name == "active_user_emails"
    assert isinstance(definition.from_clause, FromClause)
    assert definition.from_clause.source_name == "active_users"
    assert definition.where_clause is None
    assert len(definition.select_items) == 1
    assert isinstance(definition.select_items[0], SelectItem)
    assert definition.select_items[0].alias is None
    assert isinstance(definition.select_items[0].expression, NameExpr)


def test_query_with_where_parses() -> None:
    result = parse_source(
        "query active_user_emails:\n"
        "    from active_users\n"
        "    where email is not null\n"
        "    select:\n"
        "        email\n"
        "        email_norm\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, QueryDef)
    assert isinstance(definition.where_clause, WhereClause)
    assert isinstance(definition.where_clause.expression, IsNullExpr)
    assert definition.where_clause.expression.negated is True


def test_query_with_aliased_select_item_parses() -> None:
    result = parse_source(
        "query active_user_emails:\n"
        "    from active_users\n"
        "    select:\n"
        "        email\n"
        "        email_norm = lower(trim(email))\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, QueryDef)
    assert [item.alias for item in definition.select_items] == [None, "email_norm"]
    assert isinstance(definition.select_items[1].expression, CallExpr)


def test_query_is_parse_only_without_target_field_or_type_checks() -> None:
    result = parse_source(
        "query duplicate:\n"
        "    from missing_relation\n"
        "    where 1\n"
        "    select:\n"
        "        missing\n"
        "        missing = unknown_function(missing)\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, QueryDef)
    assert definition.from_clause.source_name == "missing_relation"
    assert definition.where_clause is not None
    assert [item.alias for item in definition.select_items] == [None, "missing"]


def test_query_preserves_source_table_and_query_top_level_order() -> None:
    result = parse_source(
        'source users is postgres.table("public.users")\n'
        "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    select:\n"
        "        email\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        SourceDef,
        TableDef,
        QueryDef,
    ]


def test_query_preserves_select_item_order() -> None:
    result = parse_source(
        "query ordered:\n"
        "    from active_users\n"
        "    select:\n"
        "        email_norm\n"
        "        email\n"
        "        normalized = lower(email)\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, QueryDef)
    assert [item.alias for item in definition.select_items] == [
        None,
        None,
        "normalized",
    ]
    first = definition.select_items[0].expression
    second = definition.select_items[1].expression
    assert isinstance(first, NameExpr)
    assert isinstance(second, NameExpr)
    assert [first.name, second.name] == ["email_norm", "email"]


def test_query_allows_blank_lines_comments_and_eof() -> None:
    result = parse_source(
        "query active_user_emails:\n"
        "\n"
        "    # Reusable relation input.\n"
        "    from active_users\n"
        "\n"
        "    # Filter incomplete rows.\n"
        "    where email is not null\n"
        "\n"
        "    select:\n"
        "\n"
        "        # User-facing value.\n"
        "        email\n"
        "\n"
        "        email_norm"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, QueryDef)
    assert definition.span.end_line == 14
    assert definition.span.end_column == 19
    assert len(definition.select_items) == 2


def test_query_keyword_remains_available_in_dotted_expressions() -> None:
    result = parse_source(
        "query keyword_call:\n"
        "    from active_users\n"
        "    select:\n"
        "        catalog.query(row.from)\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, QueryDef)
    expression = definition.select_items[0].expression
    assert isinstance(expression, CallExpr)
    assert isinstance(expression.callee, DottedNameExpr)
    assert expression.callee.parts == ("catalog", "query")


def test_query_spans_are_one_based_half_open() -> None:
    path = Path("examples/queries/span.pietto")
    result = parse_source(
        "query active_user_emails:\n"
        "    from active_users\n"
        "    where email is not null\n"
        "    select:\n"
        "        email\n"
        "        email_norm = lower(trim(email))\n",
        path=path,
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, QueryDef)
    assert definition.span == Span(
        path=str(path),
        line=1,
        column=1,
        end_line=6,
        end_column=40,
    )
    assert definition.from_clause.span == Span(
        path=str(path),
        line=2,
        column=5,
        end_line=2,
        end_column=22,
    )
    assert definition.where_clause is not None
    assert definition.where_clause.span == Span(
        path=str(path),
        line=3,
        column=5,
        end_line=3,
        end_column=28,
    )
    assert definition.select_items[0].span == Span(
        path=str(path),
        line=5,
        column=9,
        end_line=5,
        end_column=14,
    )
    assert definition.select_items[1].span == Span(
        path=str(path),
        line=6,
        column=9,
        end_line=6,
        end_column=40,
    )


def test_query_example_fixture_parses() -> None:
    result = parse_file("examples/queries/active_user_emails.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    shape, source, table, query = result.ast.definitions
    assert isinstance(shape, ShapeDef)
    assert isinstance(source, SourceDef)
    assert isinstance(table, TableDef)
    assert isinstance(query, QueryDef)
    assert query.name == "active_user_emails"
    assert query.from_clause.source_name == "active_users"
    assert [item.alias for item in query.select_items] == [None, None]


def test_query_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source(
        "query active_user_emails:\n"
        "    from active_users\n"
        "    where email is not null\n"
        "    select:\n"
        "        email\n"
        "        email_norm = lower(trim(email))\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast.definitions[0])


@pytest.mark.parametrize(
    "source",
    [
        "query :\n    from active_users\n    select:\n        email\n",
        "query active_user_emails\n    from active_users\n    select:\n        email\n",
        "query active_user_emails:\n    select:\n        email\n",
        "query active_user_emails:\n    from\n    select:\n        email\n",
        "query active_user_emails:\n    from active_users\n",
        "query active_user_emails:\n    from active_users\n    select:\n",
        "query active_user_emails:\n    from active_users\n    select: email\n",
        (
            "query active_user_emails:\n"
            "    from active_users\n"
            "    where\n"
            "    select:\n"
            "        email\n"
        ),
        (
            "query active_user_emails:\n"
            "    where email is not null\n"
            "    from active_users\n"
            "    select:\n"
            "        email\n"
        ),
        (
            "query active_user_emails:\n"
            "    from active_users\n"
            "    select:\n"
            "        alias =\n"
        ),
        (
            "query active_user_emails(parameter: Text):\n"
            "    from active_users\n"
            "    select:\n"
            "        email\n"
        ),
    ],
)
def test_malformed_queries_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_query_rejects_nested_query_syntax() -> None:
    result = parse_source(
        "query outer_query:\n"
        "    from active_users\n"
        "    select:\n"
        "        query inner_query:\n"
        "            from active_users\n"
        "            select:\n"
        "                email\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_query_select_assignment_remains_local_to_select_items() -> None:
    result = parse_source(
        "query active_user_emails:\n"
        "    from active_users\n"
        "    where normalized = lower(email)\n"
        "    select:\n"
        "        email\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_query_rejects_old_postfix_nullability() -> None:
    result = parse_source(
        "shape User:\n"
        "    email: Email?\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    select:\n"
        "        email\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_query_brace_block_reports_unsupported_brace() -> None:
    result = parse_source(
        "query active_user_emails {\n"
        "    from active_users\n"
        "    select:\n"
        "        email\n"
        "}\n"
    )

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


def _has_code(result: object, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)
