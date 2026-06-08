from __future__ import annotations

from pathlib import Path

import pytest

from pietto.ast_nodes import (
    BinaryExpr,
    ConstraintDef,
    EnumDef,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    TypeDef,
)
from pietto.parser_api import parse_file, parse_source


def test_constraint_with_nullable_parameter_parses() -> None:
    result = parse_source(
        "constraint valid_email(x: Text?) -> Bool:\n"
        '    x is not null and x like "%@%"\n',
        path=Path("constraints.pie"),
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ConstraintDef)
    assert definition.name == "valid_email"
    assert definition.span.path == "constraints.pie"
    assert definition.span.line == 1
    assert definition.span.column == 1
    assert definition.span.end_line == 2
    assert definition.span.end_column == 35
    assert len(definition.parameters) == 1
    parameter = definition.parameters[0]
    assert parameter.name == "x"
    assert parameter.type.name == "Text"
    assert parameter.type.nullable is True
    assert definition.return_type.name == "Bool"
    assert isinstance(definition.body, BinaryExpr)
    assert definition.body.operator == "and"
    assert isinstance(definition.body.left, IsNullExpr)
    assert definition.body.left.negated is True


def test_constraint_without_parameters_and_non_bool_return_parse_only() -> None:
    result = parse_source('constraint label() -> Text:\n    "ok"\n')

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ConstraintDef)
    assert definition.parameters == ()
    assert definition.return_type.name == "Text"
    assert isinstance(definition.body, LiteralExpr)
    assert definition.body.value == "ok"


def test_constraint_with_multiple_parameter_types_and_trailing_comma() -> None:
    result = parse_source(
        "constraint compatible(x: Int, y: Text(max = 3),) -> Bool:\n"
        "    x > 0 and len(y) > 0\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ConstraintDef)
    assert [parameter.name for parameter in definition.parameters] == ["x", "y"]
    assert definition.parameters[0].type.name == "Int"
    assert definition.parameters[1].type.name == "Text"
    assert definition.parameters[1].type.arguments[0].name == "max"
    assert definition.return_type.name == "Bool"


def test_constraint_allows_blank_lines_comments_and_no_final_newline() -> None:
    result = parse_source(
        "constraint positive(x: Int) -> Bool:\n\n    # parse-only body\n    x > 0"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ConstraintDef)
    assert definition.span.end_line == 4
    assert definition.span.end_column == 10


def test_constraint_keeps_top_level_definition_order() -> None:
    result = parse_source(
        "type Age = Int\n"
        "enum Status:\n"
        "    draft\n"
        "constraint positive(x: Age) -> Bool:\n"
        "    x > 0\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        TypeDef,
        EnumDef,
        ConstraintDef,
    ]


def test_constraint_example_fixture_parses() -> None:
    result = parse_file("examples/constraints/valid_email.pie")

    assert result.diagnostics == ()
    assert result.ast is not None
    assert isinstance(result.ast.definitions[0], ConstraintDef)


def test_constraint_body_preserves_existing_expression_ast() -> None:
    result = parse_source("constraint identity(x: Int) -> Bool:\n    x is null\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ConstraintDef)
    assert isinstance(definition.body, IsNullExpr)
    assert definition.body.negated is False
    assert isinstance(definition.body.value, NameExpr)
    assert definition.body.value.name == "x"


@pytest.mark.parametrize(
    "source",
    [
        "constraint (x: Int) -> Bool:\n    x > 0\n",
        "constraint positive x: Int -> Bool:\n    x > 0\n",
        "constraint positive(x) -> Bool:\n    x > 0\n",
        "constraint positive(x: Int) Bool:\n    x > 0\n",
        "constraint positive(x: Int) -> :\n    x > 0\n",
        "constraint positive(x: Int) -> Bool\n    x > 0\n",
        "constraint positive(x: Int) -> Bool:\nx > 0\n",
        "constraint positive(x: Int) -> Bool:\n",
    ],
)
def test_malformed_constraints_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "P1000")


def test_constraint_brace_block_reports_unsupported_brace() -> None:
    result = parse_source("constraint c() -> Bool {\n    true\n}\n")

    assert result.ast is None
    assert _has_code(result, "P1005")


def test_constraint_rejects_multiple_body_expressions() -> None:
    result = parse_source(
        "constraint positive(x: Int) -> Bool:\n    x > 0\n    x < 10\n"
    )

    assert result.ast is None
    assert _has_code(result, "P1000")


def _has_code(result: object, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)
