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
    Nullability,
    TypeDef,
    UnaryExpr,
)
from pietto.parser_api import ParseResult, parse_file, parse_source


def test_constraint_with_nullable_parameter_parses() -> None:
    result = parse_source(
        "constraint valid_email(x: Text | None) -> Bool:\n"
        '    return x is not None and x like "%@%"\n',
        path=Path("constraints.pietto"),
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ConstraintDef)
    assert definition.name == "valid_email"
    assert definition.span.path == "constraints.pietto"
    assert definition.span.line == 1
    assert definition.span.column == 1
    assert definition.span.end_line == 2
    assert definition.span.end_column == 42
    assert len(definition.parameters) == 1
    parameter = definition.parameters[0]
    assert parameter.name == "x"
    assert parameter.type.name == "Text"
    assert parameter.type.nullability is Nullability.NULLABLE
    assert definition.return_type.name == "Bool"
    assert isinstance(definition.body, BinaryExpr)
    assert definition.body.operator == "and"
    assert isinstance(definition.body.left, IsNullExpr)
    assert definition.body.left.negated is True


def test_constraint_without_parameters_and_non_bool_return_parse_only() -> None:
    result = parse_source('constraint label() -> Text:\n    return "ok"\n')

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
        "    return x > 0 and len(y) > 0\n"
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
        "constraint positive(x: Int) -> Bool:\n\n    # parse-only body\n    return x > 0"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ConstraintDef)
    assert definition.span.end_line == 4
    assert definition.span.end_column == 17


def test_constraint_keeps_top_level_definition_order() -> None:
    result = parse_source(
        "type Age = Int\n"
        "enum Status:\n"
        "    draft\n"
        "constraint positive(x: Age) -> Bool:\n"
        "    return x > 0\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [type(definition) for definition in result.ast.definitions] == [
        TypeDef,
        EnumDef,
        ConstraintDef,
    ]


def test_constraint_example_fixture_parses() -> None:
    result = parse_file("examples/constraints/valid_email.pietto")

    assert result.diagnostics == ()
    assert result.ast is not None
    assert isinstance(result.ast.definitions[0], ConstraintDef)


def test_constraint_body_preserves_existing_expression_ast() -> None:
    result = parse_source(
        "constraint identity(x: Int) -> Bool:\n    return x is None\n"
    )

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
        "constraint positive(x) -> Bool:\n    return x > 0\n",
        "constraint positive(x: Int) Bool:\n    return x > 0\n",
        "constraint positive(x: Int) -> :\n    return x > 0\n",
        "constraint positive(x: Int) -> Bool\n    return x > 0\n",
        "constraint positive(x: Int) -> Bool:\nx > 0\n",
        "constraint positive(x: Int) -> Bool:\n",
    ],
)
def test_malformed_constraints_return_syntax_diagnostic(source: str) -> None:
    result = parse_source(source)

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_constraint_brace_block_reports_unsupported_brace() -> None:
    result = parse_source("constraint c() -> Bool {\n    return True\n}\n")

    assert result.ast is None
    assert _has_code(result, "PIE-P1005")


def test_constraint_one_line_body_returns_on_the_header_line() -> None:
    one_line = parse_source("constraint positive(x: Int) -> Bool: return x > 0\n")
    block = parse_source("constraint positive(x: Int) -> Bool:\n    return x > 0\n")

    assert one_line.diagnostics == block.diagnostics == ()
    assert one_line.ast is not None and block.ast is not None
    definition = one_line.ast.definitions[0]
    assert isinstance(definition, ConstraintDef)
    assert (definition.span.end_line, definition.span.end_column) == (1, 50)
    body = definition.body
    assert (body.span.line, body.span.column, body.span.end_column) == (1, 45, 50)
    other = block.ast.definitions[0]
    assert isinstance(other, ConstraintDef)
    assert type(body) is type(other.body)
    assert definition.parameters[0].name == other.parameters[0].name == "x"


def test_constraint_one_line_body_starts_with_return() -> None:
    result = parse_source("constraint positive(x: Int) -> Bool: x > 0\n")

    assert result.ast is None
    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in result.diagnostics
    ] == [("PIE-P1000", 1, 38, "Unexpected 'x'; expected 'return' or end of line.")]


def test_constraint_rejects_multiple_body_expressions() -> None:
    result = parse_source(
        "constraint positive(x: Int) -> Bool:\n    return x > 0\n    x < 10\n"
    )

    assert result.ast is None
    assert _has_code(result, "PIE-P1000")


def test_a_constraint_block_body_nests_as_deep_as_the_other_expressions() -> None:
    # Its `return` is taken by its own token, so the depth that every position
    # accepts (tests/test_diagnostics.py) is left to the expression.
    result = parse_source(
        "constraint c(a: Int) -> Bool:\n    return " + "-" * 314 + "a\n"
    )

    # The minus signs are written together, so they warn once that `--` is
    # no comment (PIE-P1009).
    assert [item.code for item in result.diagnostics] == ["PIE-P1009"]
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ConstraintDef)
    body = definition.body
    for _ in range(314):
        assert isinstance(body, UnaryExpr) and body.operator == "-"
        body = body.operand
    assert isinstance(body, NameExpr) and body.name == "a"


@pytest.mark.parametrize("body", ["return and True", "return.size > 1"])
def test_a_constraint_body_reading_the_name_return_keeps_its_refusal(
    body: str,
) -> None:
    result = parse_source(f"constraint c(return: Bool) -> Bool:\n    {body}\n")

    assert result.ast is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.message,
            item.suggestion,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1000",
            2,
            5,
            "This spelling is not accepted by the modern syntax. "
            "Add 'return' before the body expression.",
            "Add 'return' before the body expression.",
        )
    ]


def _has_code(result: ParseResult, code: str) -> bool:
    return any(diagnostic.code == code for diagnostic in result.diagnostics)
