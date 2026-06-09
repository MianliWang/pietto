from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    DottedNameExpr,
    EnumDef,
    FromClause,
    IsNullExpr,
    NameExpr,
    SelectItem,
    SourceDef,
    Span,
    TableDef,
    TypeDef,
    WhereClause,
)
from pietto.parser_api import parse_file, parse_source


def test_minimal_table_parses_from_where_and_ordered_select_items() -> None:
    result = parse_source(
        "table active_users:\n"
        "    from users\n"
        "    where deleted_at is null\n"
        "    select:\n"
        "        id\n"
        "        email\n"
        "        email_norm = lower(trim(email))\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TableDef)
    assert definition.name == "active_users"
    assert isinstance(definition.from_clause, FromClause)
    assert definition.from_clause.source_name == "users"
    assert isinstance(definition.where_clause, WhereClause)
    assert isinstance(definition.where_clause.expression, IsNullExpr)
    assert [item.alias for item in definition.select_items] == [
        None,
        None,
        "email_norm",
    ]
    assert all(isinstance(item, SelectItem) for item in definition.select_items)
    assert isinstance(definition.select_items[0].expression, NameExpr)
    assert isinstance(definition.select_items[2].expression, CallExpr)


def test_table_without_where_parses_expressions_and_aliases() -> None:
    result = parse_source(
        "table projected:\n"
        "    from missing_source\n"
        "    select:\n"
        "        missing_field\n"
        "        score = missing_field + 1\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TableDef)
    assert definition.where_clause is None
    assert definition.from_clause.source_name == "missing_source"
    assert isinstance(definition.select_items[1].expression, BinaryExpr)


def test_table_is_parse_only_without_source_field_or_type_checks() -> None:
    result = parse_source(
        "table duplicate:\n"
        "    from unknown_source\n"
        "    where 1\n"
        "    select:\n"
        "        missing\n"
        "        missing = unknown_function(missing)\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TableDef)
    assert definition.from_clause.source_name == "unknown_source"
    assert definition.where_clause is not None
    assert [item.alias for item in definition.select_items] == [None, "missing"]


def test_table_allows_blank_lines_comments_and_eof() -> None:
    result = parse_source(
        "table active_users:\n"
        "\n"
        "    # Input relation.\n"
        "    from users\n"
        "\n"
        "    # Optional row filter.\n"
        "    where deleted_at is null\n"
        "\n"
        "    select:\n"
        "\n"
        "        # Stable identifier.\n"
        "        id\n"
        "\n"
        "        email"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TableDef)
    assert definition.span.end_line == 14
    assert definition.span.end_column == 14
    assert [item.alias for item in definition.select_items] == [None, None]


def test_table_preserves_top_level_definition_order() -> None:
    result = parse_source(
        "type UserId = UUID\n"
        'source users is postgres.table("public.users")\n'
        "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "enum Status:\n"
        "    ready\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        TypeDef,
        SourceDef,
        TableDef,
        EnumDef,
    ]


def test_table_keywords_remain_available_in_dotted_expressions() -> None:
    result = parse_source(
        "table keyword_calls:\n"
        "    from users\n"
        "    where row.where is not null\n"
        "    select:\n"
        "        catalog.table(row.from)\n"
        "        selected = row.select\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TableDef)
    first = definition.select_items[0].expression
    assert isinstance(first, CallExpr)
    assert isinstance(first.callee, DottedNameExpr)
    assert first.callee.parts == ("catalog", "table")
    assert isinstance(first.arguments[0], DottedNameExpr)
    assert first.arguments[0].parts == ("row", "from")
    second = definition.select_items[1].expression
    assert isinstance(second, DottedNameExpr)
    assert second.parts == ("row", "select")


def test_table_spans_are_one_based_half_open() -> None:
    path = Path("examples/tables/span.pie")
    result = parse_source(
        "table active_users:\n"
        "    from users\n"
        "    where deleted_at is null\n"
        "    select:\n"
        "        id\n"
        "        email_norm = lower(trim(email))\n",
        path=path,
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TableDef)
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
        end_column=15,
    )
    assert definition.where_clause is not None
    assert definition.where_clause.span == Span(
        path=str(path),
        line=3,
        column=5,
        end_line=3,
        end_column=29,
    )
    assert definition.select_items[0].span == Span(
        path=str(path),
        line=5,
        column=9,
        end_line=5,
        end_column=11,
    )
    assert definition.select_items[1].span == Span(
        path=str(path),
        line=6,
        column=9,
        end_line=6,
        end_column=40,
    )
    assert definition.select_items[1].expression.span == Span(
        path=str(path),
        line=6,
        column=22,
        end_line=6,
        end_column=40,
    )


def test_table_example_fixture_parses() -> None:
    result = parse_file("examples/tables/active_users.pie")

    assert result.diagnostics == ()
    assert result.ast is not None
    source, table = result.ast.definitions
    assert isinstance(source, SourceDef)
    assert isinstance(table, TableDef)
    assert table.name == "active_users"
    assert table.from_clause.source_name == "users"
    assert [item.alias for item in table.select_items] == [
        None,
        None,
        "email_norm",
    ]


def test_table_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source(
        "table active_users:\n"
        "    from users\n"
        "    where deleted_at is null\n"
        "    select:\n"
        "        id\n"
        "        email_norm = lower(trim(email))\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast.definitions[0])


@pytest.mark.parametrize(
    "source",
    [
        "table :\n    from users\n    select:\n        id\n",
        "table active_users\n    from users\n    select:\n        id\n",
        "table active_users:\n    select:\n        id\n",
        "table active_users:\n    from\n    select:\n        id\n",
        "table active_users:\n    from users\n",
        "table active_users:\n    from users\n    select:\n",
        "table active_users:\n    from users\n    select: id\n",
        "table active_users:\n    from users\n    where\n    select:\n        id\n",
        (
            "table active_users:\n"
            "    where deleted_at is null\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
        ),
        (
            "table active_users:\n"
            "    from users\n"
            "    select:\n"
            "        id\n"
            "    where deleted_at is null\n"
        ),
        ("table active_users:\n    from users\n    select:\n        alias =\n"),
    ],
)
def test_malformed_tables_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_select_assignment_remains_local_to_select_items() -> None:
    result = parse_source(
        "table active_users:\n"
        "    from users\n"
        "    where email_norm = lower(email)\n"
        "    select:\n"
        "        id\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_table_rejects_old_postfix_nullability() -> None:
    result = parse_source(
        "shape User:\n"
        "    email: Email?\n"
        "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_table_brace_block_reports_unsupported_brace() -> None:
    result = parse_source(
        "table active_users {\n    from users\n    select:\n        id\n}\n"
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
