from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    CheckDef,
    EnumDef,
    FieldDef,
    IndexDef,
    IsNullExpr,
    LiteralExpr,
    ShapeDef,
    Span,
    TypeDef,
    UniqueDef,
)
from pietto.parser_api import ParseResult, parse_file, parse_source


def test_shape_index_parses_fields_and_optional_predicate() -> None:
    result = parse_source(
        "shape User:\n"
        "    tenant_id: UUID not null\n"
        "    email: Email not null\n"
        "    deleted_at: Timestamp nullable\n"
        "\n"
        "    index user_email_idx on email\n"
        "    index tenant_email_idx on tenant_id, email\n"
        "    index active_user_email_idx on email when deleted_at is null\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [index.name for index in definition.indexes] == [
        "user_email_idx",
        "tenant_email_idx",
        "active_user_email_idx",
    ]
    assert definition.indexes[0].field_names == ("email",)
    assert definition.indexes[0].predicate is None
    assert definition.indexes[1].field_names == ("tenant_id", "email")
    assert definition.indexes[1].predicate is None
    assert definition.indexes[2].field_names == ("email",)
    assert isinstance(definition.indexes[2].predicate, IsNullExpr)


def test_shape_index_is_parse_only_without_name_field_or_bool_checks() -> None:
    result = parse_source(
        "shape External:\n"
        "    duplicate: Text\n"
        "    check duplicate:\n"
        "        1\n"
        "    unique duplicate on missing\n"
        "    index duplicate on missing, missing when 1\n"
        "    index duplicate on missing\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [index.name for index in definition.indexes] == [
        "duplicate",
        "duplicate",
    ]
    assert definition.indexes[0].field_names == ("missing", "missing")
    assert isinstance(definition.indexes[0].predicate, LiteralExpr)


def test_shape_index_allows_blank_lines_comments_and_eof() -> None:
    result = parse_source(
        "shape User:\n"
        "    email: Email not null\n"
        "\n"
        "    # Index active email values.\n"
        "    index user_email_idx on email"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    index = definition.indexes[0]
    assert index.span.end_line == 5
    assert index.span.end_column == 34


def test_shape_preserves_mixed_field_check_unique_and_index_order() -> None:
    result = parse_source(
        "shape User:\n"
        "    check has_email:\n"
        "        email is not null\n"
        "    tenant_id: UUID not null\n"
        "    unique tenant_user_email on tenant_id, email\n"
        "    index tenant_email_idx on tenant_id, email\n"
        "    email: Email not null\n"
        "    index active_email_idx on email when deleted_at is null\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [type(item) for item in definition.items] == [
        CheckDef,
        FieldDef,
        UniqueDef,
        IndexDef,
        FieldDef,
        IndexDef,
    ]
    assert [item.name for item in definition.items] == [
        "has_email",
        "tenant_id",
        "tenant_user_email",
        "tenant_email_idx",
        "email",
        "active_email_idx",
    ]
    assert [field.name for field in definition.fields] == ["tenant_id", "email"]
    assert [check.name for check in definition.checks] == ["has_email"]
    assert [unique.name for unique in definition.uniques] == ["tenant_user_email"]
    assert [index.name for index in definition.indexes] == [
        "tenant_email_idx",
        "active_email_idx",
    ]


def test_shape_index_preserves_top_level_definition_order() -> None:
    result = parse_source(
        "type Email = Text\n"
        "shape User:\n"
        "    email: Email not null\n"
        "    index user_email_idx on email\n"
        "enum Status:\n"
        "    ready\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        TypeDef,
        ShapeDef,
        EnumDef,
    ]


def test_index_and_when_remain_available_in_dotted_expressions() -> None:
    result = parse_source(
        "shape User:\n"
        "    email: Email not null\n"
        "    check keyword_calls:\n"
        "        catalog.index(email) is not null and row.when is not null\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None


def test_shape_index_spans_are_one_based_half_open() -> None:
    path = Path("examples/shapes/index_span.pietto")
    result = parse_source(
        "shape User:\n"
        "    tenant_id: UUID not null\n"
        "    email: Email not null\n"
        "    deleted_at: Timestamp nullable\n"
        "    index active_user_email_idx on email when deleted_at is null\n"
        "    status: Text nullable\n",
        path=path,
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert definition.span == Span(
        path=str(path),
        line=1,
        column=1,
        end_line=6,
        end_column=26,
    )
    index = definition.indexes[0]
    assert index.span == Span(
        path=str(path),
        line=5,
        column=5,
        end_line=5,
        end_column=65,
    )
    assert index.predicate is not None
    assert index.predicate.span == Span(
        path=str(path),
        line=5,
        column=47,
        end_line=5,
        end_column=65,
    )


def test_shape_index_example_fixture_parses() -> None:
    result = parse_file("examples/shapes/user_indexes.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [field.name for field in definition.fields] == [
        "tenant_id",
        "email",
        "deleted_at",
    ]
    assert [index.name for index in definition.indexes] == [
        "user_email_idx",
        "tenant_email_idx",
        "active_user_email_idx",
    ]


def test_shape_index_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source(
        "shape User:\n"
        "    email: Email not null\n"
        "    deleted_at: Timestamp nullable\n"
        "    index active_user_email_idx on email when deleted_at is null\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast.definitions[0])


@pytest.mark.parametrize(
    "source",
    [
        "shape User:\n    index on email\n",
        "shape User:\n    index user_email_idx email\n",
        "shape User:\n    index user_email_idx on\n",
        "shape User:\n    index user_email_idx on , email\n",
        "shape User:\n    index user_email_idx on email,\n",
        "shape User:\n    index user_email_idx on email,, tenant_id\n",
        "shape User:\n    index user_email_idx on email tenant_id\n",
        "shape User:\n    index user_email_idx on email when\n",
        "shape User:\n    index lower_email_idx on lower(email)\n",
        "shape User:\n    index user_email_idx on email using btree\n",
        "shape User:\n    index user_email_idx on email include tenant_id\n",
        "shape User:\n    index user_email_idx on email desc\n",
    ],
)
def test_malformed_shape_indexes_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_shape_index_rejects_old_postfix_nullability() -> None:
    result = parse_source(
        "shape User:\n    email: Email?\n    index user_email_idx on email\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_shape_index_brace_block_reports_unsupported_brace() -> None:
    result = parse_source(
        "shape User:\n"
        "    email: Email not null\n"
        "    index user_email_idx on email {\n"
        "    }\n"
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


def _has_code(result: ParseResult, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)
