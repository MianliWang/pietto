from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import (
    Annotation,
    BetweenExpr,
    BinaryExpr,
    ComparisonExpr,
    ConstraintDef,
    DeriveDef,
    EnumDef,
    FieldDef,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    ShapeDef,
    Span,
    TypeDef,
    TypeExpr,
)
from pietto.parser_api import parse_file, parse_source


def test_shape_parses_ordered_fields_and_nullability_syntax() -> None:
    result = parse_source(
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Text(max = 255, encoding = utf8)?\n"
        "    age: Age?\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert definition.name == "User"
    assert [field.name for field in definition.fields] == ["id", "email", "age"]

    identifier, email, age = definition.fields
    assert isinstance(identifier, FieldDef)
    assert isinstance(identifier.type_expr, TypeExpr)
    assert identifier.type_expr.name == "UUID"
    assert identifier.type_expr.nullable is False
    assert identifier.not_null is True
    assert identifier.annotations == ()
    assert identifier.ensure_clauses == ()

    assert email.type_expr.name == "Text"
    assert email.type_expr.nullable is True
    assert email.not_null is False
    assert [argument.name for argument in email.type_expr.arguments] == [
        "max",
        "encoding",
    ]
    assert isinstance(email.type_expr.arguments[0].value, LiteralExpr)
    assert email.type_expr.arguments[0].value.value == 255
    assert isinstance(email.type_expr.arguments[1].value, NameExpr)
    assert email.type_expr.arguments[1].value.name == "utf8"

    assert age.type_expr.name == "Age"
    assert age.type_expr.nullable is True
    assert age.not_null is False


def test_shape_field_modifiers_parse_only() -> None:
    result = parse_source(
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Email @pii @sensitive\n"
        "    age: Age? ensure self is null or self between 0 and 130\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)

    identifier, email, age = definition.fields
    assert identifier.name == "id"
    assert identifier.not_null is True

    assert email.type_expr.name == "Email"
    assert [annotation.name for annotation in email.annotations] == [
        "pii",
        "sensitive",
    ]
    assert all(isinstance(annotation, Annotation) for annotation in email.annotations)
    assert email.ensure_clauses == ()

    assert age.type_expr.name == "Age"
    assert age.type_expr.nullable is True
    assert len(age.ensure_clauses) == 1
    expression = age.ensure_clauses[0].expression
    assert isinstance(expression, BinaryExpr)
    assert expression.operator == "or"
    assert isinstance(expression.left, IsNullExpr)
    assert isinstance(expression.right, BetweenExpr)


def test_shape_field_modifier_order_is_preserved_within_each_kind() -> None:
    result = parse_source(
        "shape User:\n"
        "    name: Text @pii ensure self is not null @sensitive "
        "ensure len(self) > 0\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    field = definition.fields[0]
    assert [annotation.name for annotation in field.annotations] == [
        "pii",
        "sensitive",
    ]
    assert len(field.ensure_clauses) == 2
    assert isinstance(field.ensure_clauses[0].expression, IsNullExpr)
    assert isinstance(field.ensure_clauses[1].expression, ComparisonExpr)


def test_shape_bare_field_type_is_parse_only() -> None:
    result = parse_source("shape External:\n    value: MissingType @unknown ensure 1\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    field = definition.fields[0]
    assert field.type_expr.name == "MissingType"
    assert field.type_expr.nullable is False
    assert field.not_null is False
    assert field.annotations[0].name == "unknown"
    assert isinstance(field.ensure_clauses[0].expression, LiteralExpr)


def test_shape_allows_blank_lines_and_comments() -> None:
    result = parse_source(
        "shape User:\n"
        "\n"
        "    # Stable external identifier.\n"
        "    id: UUID not null\n"
        "\n"
        "    # Optional display name.\n"
        "    display_name: Text?\n"
        "\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [field.name for field in definition.fields] == ["id", "display_name"]


def test_shape_without_final_newline_closes_at_eof() -> None:
    result = parse_source(
        "shape User:\n"
        "    id: UUID not null\n"
        "    age: Age? ensure self between 0 and 130"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert definition.span.end_line == 3
    assert definition.span.end_column == 44
    assert [field.name for field in definition.fields] == ["id", "age"]
    assert len(definition.fields[1].ensure_clauses) == 1


def test_shape_and_field_spans_are_one_based_half_open() -> None:
    path = Path("examples/shapes/span.pie")
    result = parse_source(
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Text(max = 255, encoding = utf8)?\n"
        "    age: Age?\n",
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
        end_line=4,
        end_column=14,
    )
    assert definition.fields[0].span == Span(
        path=str(path),
        line=2,
        column=5,
        end_line=2,
        end_column=22,
    )
    assert definition.fields[0].type_expr.span == Span(
        path=str(path),
        line=2,
        column=9,
        end_line=2,
        end_column=13,
    )
    assert definition.fields[1].span == Span(
        path=str(path),
        line=3,
        column=5,
        end_line=3,
        end_column=45,
    )
    assert definition.fields[1].type_expr.span == Span(
        path=str(path),
        line=3,
        column=12,
        end_line=3,
        end_column=45,
    )


def test_shape_field_modifier_spans_are_one_based_half_open() -> None:
    path = Path("examples/shapes/modifier_span.pie")
    result = parse_source(
        "shape User:\n"
        "    email: Email @pii @sensitive\n"
        "    age: Age? ensure self is null or self between 0 and 130\n",
        path=path,
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)

    email = definition.fields[0]
    assert email.span == Span(
        path=str(path),
        line=2,
        column=5,
        end_line=2,
        end_column=33,
    )
    assert email.type_expr.span == Span(
        path=str(path),
        line=2,
        column=12,
        end_line=2,
        end_column=17,
    )
    assert email.annotations[0].span == Span(
        path=str(path),
        line=2,
        column=18,
        end_line=2,
        end_column=22,
    )
    assert email.annotations[1].span == Span(
        path=str(path),
        line=2,
        column=23,
        end_line=2,
        end_column=33,
    )

    age = definition.fields[1]
    assert age.span == Span(
        path=str(path),
        line=3,
        column=5,
        end_line=3,
        end_column=60,
    )
    assert age.type_expr.span == Span(
        path=str(path),
        line=3,
        column=10,
        end_line=3,
        end_column=14,
    )
    assert age.ensure_clauses[0].span == Span(
        path=str(path),
        line=3,
        column=15,
        end_line=3,
        end_column=60,
    )


def test_shape_keeps_top_level_definition_order() -> None:
    result = parse_source(
        "type Age = Int\n"
        "constraint positive(x: Age) -> Bool:\n"
        "    x > 0\n"
        "derive increment(x: Age) -> Age:\n"
        "    x + 1\n"
        "shape User:\n"
        "    age: Age?\n"
        "enum Status:\n"
        "    ready\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        TypeDef,
        ConstraintDef,
        DeriveDef,
        ShapeDef,
        EnumDef,
    ]


def test_shape_example_fixture_parses() -> None:
    result = parse_file("examples/shapes/user.pie")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    assert [field.name for field in definition.fields] == ["id", "email", "age"]
    assert [annotation.name for annotation in definition.fields[1].annotations] == [
        "pii",
        "sensitive",
    ]
    assert len(definition.fields[2].ensure_clauses) == 1


def test_shape_ast_does_not_expose_antlr_nodes() -> None:
    result = parse_source(
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Email @pii\n"
        "    age: Age? ensure self is null or self between 0 and 130\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    _assert_no_antlr_nodes(result.ast.definitions[0])


@pytest.mark.parametrize(
    "source",
    [
        "shape :\n    id: UUID\n",
        "shape User\n    id: UUID\n",
        "shape User:\nid: UUID\n",
        "shape User:\n    : UUID\n",
        "shape User:\n    id UUID\n",
        "shape User:\n    id:\n",
        "shape User:\n",
        "shape User:\n    id: UUID not\n",
        "shape User:\n    id: UUID null\n",
        "shape User:\n    id: UUID? not null\n",
        "shape User:\n    id: UUID @\n",
        'shape User:\n    id: UUID @pii("yes")\n',
        "shape User:\n    id: UUID ensure\n",
    ],
)
def test_malformed_shapes_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "P1000")


@pytest.mark.parametrize(
    "body",
    [
        "    id: UUID derive normalize(id)\n",
        "    check valid_id:\n        id is not null\n",
        "    unique id\n",
        "    index users_id_idx on id\n",
    ],
)
def test_shape_rejects_not_yet_supported_body_syntax(body: str) -> None:
    result = parse_source(f"shape User:\n{body}")

    assert result.ast is None
    assert _has_code(result, "P1000")


def test_shape_brace_block_reports_unsupported_brace() -> None:
    result = parse_source("shape User {\n    id: UUID\n}\n")

    assert result.ast is None
    assert _has_code(result, "P1005")


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
