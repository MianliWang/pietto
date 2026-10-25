from __future__ import annotations

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    EnumDef,
    FunctionDef,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    Nullability,
    ShapeDef,
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
    assert definition.base.nullability is Nullability.NOT_NULL
    assert definition.ensures == ()


def test_nullable_parameterized_field_type_parses() -> None:
    result = parse_source(
        "shape User:\n    nickname: Text(max = 32, encoding = utf8) | None\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, ShapeDef)
    field_type = definition.fields[0].type_expr
    assert field_type.name == "Text"
    assert field_type.nullability is Nullability.NULLABLE
    assert [argument.name for argument in field_type.arguments] == [
        "max",
        "encoding",
    ]
    assert isinstance(field_type.arguments[0].value, LiteralExpr)
    assert field_type.arguments[0].value.value == 32
    assert isinstance(field_type.arguments[1].value, NameExpr)
    assert field_type.arguments[1].value.name == "utf8"


def test_maximum_supported_integer_literal_length_parses() -> None:
    literal = "9" * 4096
    result = parse_source(f"type Huge = Int(max = {literal})\n")

    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    argument = definition.base.arguments[0].value
    assert isinstance(argument, LiteralExpr)
    assert argument.value == int(literal)


def test_type_alias_including_none_is_refused_where_the_alias_is_declared() -> None:
    result = parse_source("type MaybeAge = Int | None\ntype Other = Int nullable\n")

    assert result.ast is None
    assert [
        (item.code, item.location.line, item.location.column, item.suggestion)
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1000",
            line,
            column,
            "Declare 'type Name = T' and write 'Name | None' where a value may be None.",
        )
        for line, column in ((1, 21), (2, 18))
    ]


def test_bare_types_are_not_null_and_not_null_is_a_retired_spelling() -> None:
    bare = parse_source(
        "shape Row:\n"
        "    id: Int\n"
        "    price: Decimal(12, 2)\n"
        "    note: Text | None\n"
        "def f(x: Int, y: Int | None) -> Int: return x\n"
    )
    assert bare.diagnostics == ()
    assert bare.ast is not None
    shape, function = bare.ast.definitions
    assert isinstance(shape, ShapeDef) and isinstance(function, FunctionDef)
    assert [item.type_expr.nullability for item in shape.fields] == [
        Nullability.NOT_NULL,
        Nullability.NOT_NULL,
        Nullability.NULLABLE,
    ]
    assert [item.type.nullability for item in function.parameters] == [
        Nullability.NOT_NULL,
        Nullability.NULLABLE,
    ]
    assert function.return_type.nullability is Nullability.NOT_NULL

    retired = parse_source(
        "shape Row:\n"
        "    id: Int not null\n"
        "    price: Decimal(12, 2) not null\n"
        "type Code = Text not null\n"
    )
    assert retired.ast is None
    assert [
        (item.code, item.location.line, item.location.column, item.suggestion)
        for item in retired.diagnostics
    ] == [
        (
            "PIE-P1000",
            line,
            column,
            "Write 'T' instead of 'T not null'; a bare type is never None.",
        )
        for line, column in ((2, 13), (3, 27), (4, 18))
    ]


def test_old_question_mark_nullability_is_rejected() -> None:
    result = parse_source("type MaybeAge = Int?\n")

    assert result.ast is None
    assert any(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


def test_inline_ensure_type_parses_between_expression() -> None:
    result = parse_source("type Percent = Float ensure 0 <= self <= 1\n")

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
        "type Score = Int ensure score + 1 * 2 >= min_value and user.id is not None or 1 <= value <= 10\n"
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
    result = parse_source("type Check = Bool ensure (validator.check(-self)) is None\n")

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


def test_enum_members_may_share_lines_or_follow_the_header() -> None:
    header = parse_source("enum OrderStatus: pending, paid, shipped\n")
    block = parse_source("enum OrderStatus:\n    pending, paid\n\n    shipped\n")
    long = parse_source("enum OrderStatus:\n    pending\n    paid\n    shipped\n")

    for result in (header, block, long):
        assert result.diagnostics == ()
        assert result.ast is not None
        definition = result.ast.definitions[0]
        assert isinstance(definition, EnumDef)
        assert definition.members == ("pending", "paid", "shipped")
    assert header.ast is not None
    span = header.ast.definitions[0].span
    assert (span.line, span.column, span.end_line, span.end_column) == (1, 1, 1, 41)


def test_enum_header_line_without_colon_is_refused_with_a_suggestion() -> None:
    result = parse_source("enum OrderStatus pending, paid\n")

    assert result.ast is None
    assert [
        (item.code, item.location.line, item.location.column, item.suggestion)
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1000",
            1,
            18,
            "Write ':' after the enum name, as in 'enum Status: active, suspended'.",
        )
    ]


def test_enum_header_line_rejects_a_trailing_comma_and_a_following_block() -> None:
    trailing = parse_source("enum S: a, b,\n")
    block = parse_source("enum S: a\n    b\n")

    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for result in (trailing, block)
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1000",
            "A trailing comma does not continue a list on the next line; "
            "remove the comma.",
            1,
            13,
        ),
        (
            "PIE-P1000",
            "This clause already has its content on the header line after ':'; "
            "an indented block cannot follow it.",
            2,
            5,
        ),
    ]


def test_modern_literals_nullability_and_numeric_separators() -> None:
    result = parse_source(
        "type A = Int\n"
        "shape B:\n"
        "    c: Int | None\n"
        "type D = Int ensure 1_000 <= value <= 2_000 and value is not None\n"
        "type E = Bool ensure True or False\n"
    )
    assert result.diagnostics == ()
    assert result.ast is not None
    a, b, d, e = result.ast.definitions
    assert all(isinstance(item, TypeDef) for item in (a, d, e))
    assert isinstance(a, TypeDef) and a.base.nullability is Nullability.NOT_NULL
    assert isinstance(b, ShapeDef)
    assert b.fields[0].type_expr.nullability is Nullability.NULLABLE
    assert isinstance(d, TypeDef)
    predicate = d.ensures[0].expression
    assert isinstance(predicate, BinaryExpr)
    assert isinstance(predicate.left, BetweenExpr)
    assert isinstance(predicate.left.lower, LiteralExpr)
    assert predicate.left.lower.value == 1000
    assert isinstance(predicate.right, IsNullExpr) and predicate.right.negated


def test_modern_inclusive_chain_preserves_nullable_between_node() -> None:
    result = parse_source("type A = Int ensure None <= value <= 3\n")
    assert result.diagnostics == ()
    assert result.ast is not None
    definition = result.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    expression = definition.ensures[0].expression
    assert isinstance(expression, BetweenExpr)
    assert isinstance(expression.lower, LiteralExpr) and expression.lower.value is None


def test_modern_version_metadata_does_not_gain_digit_separators() -> None:
    result = parse_source("pietto 1_0\ntype A = Int\n")
    assert result.ast is None
    assert len(result.diagnostics) == 1
    assert "version metadata" in (result.diagnostics[0].suggestion or "")
