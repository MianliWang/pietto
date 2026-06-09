from __future__ import annotations

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    EnumDef,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    Nullability,
    TypeDef,
    UnaryExpr,
)
from pietto.parser_api import parse_source


def test_bare_type_definition_parses() -> None:
    result = parse_source("type UserId = UUID\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    assert definition.name == "UserId"
    assert definition.base.name == "UUID"
    assert definition.base.arguments == ()
    assert definition.base.nullability is Nullability.IMPLICIT
    assert definition.ensures == ()


def test_nullable_parameterized_type_definition_parses() -> None:
    result = parse_source("type Nickname = Text(max = 32, encoding = utf8) nullable\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    assert definition.base.name == "Text"
    assert definition.base.nullability is Nullability.NULLABLE
    assert [argument.name for argument in definition.base.arguments] == [
        "max",
        "encoding",
    ]
    assert isinstance(definition.base.arguments[0].value, LiteralExpr)
    assert definition.base.arguments[0].value.value == 32
    assert isinstance(definition.base.arguments[1].value, NameExpr)
    assert definition.base.arguments[1].value.name == "utf8"


def test_nullable_type_alias_parses() -> None:
    result = parse_source("type MaybeAge = Int nullable\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    assert definition.base.nullability is Nullability.NULLABLE


def test_old_question_mark_nullability_is_rejected() -> None:
    result = parse_source("type MaybeAge = Int?\n")

    assert result.ast is None
    assert any(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


def test_inline_ensure_type_parses_between_expression() -> None:
    result = parse_source("type Percent = Float ensure self between 0 and 1\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    assert len(definition.ensures) == 1
    expression = definition.ensures[0].expression
    assert isinstance(expression, BetweenExpr)
    assert isinstance(expression.value, NameExpr)
    assert expression.value.name == "self"


def test_block_type_parses_multiple_ensure_clauses() -> None:
    result = parse_source(
        "type Username = Text(max = 32, encoding = utf8):\n"
        "    ensure len(self) >= 3\n"
        '    ensure matches(self, "^[a-zA-Z0-9_]+$")\n'
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    assert len(definition.ensures) == 2
    first = definition.ensures[0].expression
    assert isinstance(first, ComparisonExpr)
    assert first.operator == ">="
    assert isinstance(first.left, CallExpr)


def test_block_type_without_final_newline_closes_at_eof() -> None:
    result = parse_source("type Age = Int:\n    ensure self >= 0")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    assert len(definition.ensures) == 1
    assert definition.span.end_line == 2
    assert definition.span.end_column == 21


def test_block_type_allows_blank_lines_and_comments() -> None:
    result = parse_source(
        "type Age = Int:\n"
        "\n"
        "    # lower bound\n"
        "    ensure self >= 0\n"
        "\n"
        "    # upper bound\n"
        "    ensure self <= 130\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    assert len(definition.ensures) == 2


def test_expression_precedence_and_null_tests_parse() -> None:
    result = parse_source(
        "type Score = Int ensure score + 1 * 2 >= min_value "
        "and user.id is not null or value between 1 and 10\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    expression = definition.ensures[0].expression
    assert isinstance(expression, BinaryExpr)
    assert expression.operator == "or"
    assert isinstance(expression.left, BinaryExpr)
    assert expression.left.operator == "and"
    assert isinstance(expression.left.right, IsNullExpr)
    assert expression.left.right.negated is True
    assert isinstance(expression.left.right.value, DottedNameExpr)
    assert isinstance(expression.right, BetweenExpr)


def test_parentheses_unary_is_null_and_dotted_call_parse() -> None:
    result = parse_source("type Check = Bool ensure (validator.check(-self)) is null\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    expression = definition.ensures[0].expression
    assert isinstance(expression, IsNullExpr)
    assert expression.negated is False
    assert isinstance(expression.value, CallExpr)
    assert isinstance(expression.value.callee, DottedNameExpr)
    assert expression.value.callee.parts == ("validator", "check")
    argument = expression.value.arguments[0]
    assert isinstance(argument, UnaryExpr)
    assert argument.operator == "-"
    assert isinstance(argument.operand, NameExpr)


def test_enum_definition_parses_members() -> None:
    result = parse_source("enum Status:\n    draft\n    paid\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, EnumDef)
    assert definition.name == "Status"
    assert definition.members == ("draft", "paid")


def test_enum_without_final_newline_closes_at_eof() -> None:
    result = parse_source("enum Status:\n    draft\n    paid")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, EnumDef)
    assert definition.members == ("draft", "paid")
    assert definition.span.end_line == 3
    assert definition.span.end_column == 9
