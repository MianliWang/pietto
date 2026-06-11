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
    ShapeDef,
    Span,
    TypeDef,
    UniqueDef,
)
from pietto.parser_api import parse_file, parse_source


def test_shape_unique_parses_single_and_multiple_fields() -> None:
    result = parse_source(
        "shape User:\n"
        "    tenant_id: UUID not null\n"
        "    email: Email not null\n"
        "\n"
        "    unique user_email on email\n"
        "    unique tenant_user_email on tenant_id, email\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [unique.name for unique in definition.uniques] == [
        "user_email",
        "tenant_user_email",
    ]
    assert definition.uniques[0].field_names == ("email",)
    assert definition.uniques[1].field_names == ("tenant_id", "email")


def test_shape_unique_is_parse_only_without_name_or_field_checks() -> None:
    result = parse_source(
        "shape External:\n"
        "    duplicate: Text\n"
        "    unique duplicate on missing, missing\n"
        "    unique duplicate on missing\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [unique.name for unique in definition.uniques] == [
        "duplicate",
        "duplicate",
    ]
    assert definition.uniques[0].field_names == ("missing", "missing")


def test_shape_unique_allows_blank_lines_comments_and_eof() -> None:
    result = parse_source(
        "shape User:\n"
        "    email: Email not null\n"
        "\n"
        "    # Keep emails unique.\n"
        "    unique user_email on email"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    unique = definition.uniques[0]
    assert unique.span.end_line == 5
    assert unique.span.end_column == 31


def test_shape_preserves_mixed_field_check_and_unique_order() -> None:
    result = parse_source(
        "shape User:\n"
        "    check has_email:\n"
        "        email is not null\n"
        "    tenant_id: UUID not null\n"
        "    unique tenant_user_email on tenant_id, email\n"
        "    email: Email not null\n"
        "    unique user_email on email\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [type(item) for item in definition.items] == [
        CheckDef,
        FieldDef,
        UniqueDef,
        FieldDef,
        UniqueDef,
    ]
    assert [item.name for item in definition.items] == [
        "has_email",
        "tenant_id",
        "tenant_user_email",
        "email",
        "user_email",
    ]
    assert [field.name for field in definition.fields] == ["tenant_id", "email"]
    assert [check.name for check in definition.checks] == ["has_email"]
    assert [unique.name for unique in definition.uniques] == [
        "tenant_user_email",
        "user_email",
    ]


def test_shape_unique_preserves_top_level_definition_order() -> None:
    result = parse_source(
        "type Email = Text\n"
        "shape User:\n"
        "    email: Email not null\n"
        "    unique user_email on email\n"
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


def test_unique_and_on_remain_available_in_dotted_expressions() -> None:
    result = parse_source(
        "shape User:\n"
        "    email: Email not null\n"
        "    check keyword_calls:\n"
        "        validator.unique(email) is not null and row.on is not null\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None


def test_shape_unique_span_is_one_based_half_open() -> None:
    path = Path("examples/shapes/unique_span.pietto")
    result = parse_source(
        "shape User:\n"
        "    tenant_id: UUID not null\n"
        "    email: Email not null\n"
        "    unique tenant_user_email on tenant_id, email\n"
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
        end_line=5,
        end_column=26,
    )
    assert definition.uniques[0].span == Span(
        path=str(path),
        line=4,
        column=5,
        end_line=4,
        end_column=49,
    )


def test_shape_unique_example_fixture_parses() -> None:
    result = parse_file("examples/shapes/user_uniques.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [field.name for field in definition.fields] == ["tenant_id", "email"]
    assert [unique.name for unique in definition.uniques] == [
        "user_email",
        "tenant_user_email",
    ]


def test_shape_unique_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source(
        "shape User:\n"
        "    tenant_id: UUID not null\n"
        "    email: Email not null\n"
        "    unique tenant_user_email on tenant_id, email\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast.definitions[0])


@pytest.mark.parametrize(
    "source",
    [
        "shape User:\n    unique on email\n",
        "shape User:\n    unique user_email email\n",
        "shape User:\n    unique user_email on\n",
        "shape User:\n    unique user_email on , email\n",
        "shape User:\n    unique user_email on email,\n",
        "shape User:\n    unique user_email on email,, tenant_id\n",
        "shape User:\n    unique user_email on email tenant_id\n",
        "shape User:\n    unique email\n",
    ],
)
def test_malformed_shape_uniques_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_shape_unique_rejects_old_postfix_nullability() -> None:
    result = parse_source(
        "shape User:\n    email: Email?\n    unique user_email on email\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_shape_unique_brace_block_reports_unsupported_brace() -> None:
    result = parse_source(
        "shape User:\n"
        "    email: Email not null\n"
        "    unique user_email on email {\n"
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


def _has_code(result: object, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)
