from __future__ import annotations

import inspect
from typing import cast

import pytest

import pietto.sql as sql_api
import pietto.sql.mysql_expressions as expression_module
from pietto.ir.model import (
    BetweenIR,
    BinaryIR,
    CastIR,
    CallIR,
    ConditionalIR,
    ComparisonIR,
    ExpressionIR,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    MembershipIR,
    NullabilityIR,
    SourceSpan,
    StaticValue,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    UnaryIR,
)
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.mysql_render import MySqlRenderError

SPAN = SourceSpan(
    path="mysql-expressions.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
UNKNOWN_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="<unknown>",
    canonical_name="<unknown>",
    kind=TypeKindIR.UNKNOWN,
    canonical_kind=TypeKindIR.UNKNOWN,
    nullability=NullabilityIR.UNKNOWN,
)
FLOAT_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Float",
    canonical_name="Float",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
INT_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)


def _literal(value: StaticValue) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=UNKNOWN_TYPE, value=value)


def _field(
    name: str,
    *,
    qualifier: tuple[str, ...] = (),
) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        name=name,
        qualifier=qualifier,
        field=None,
    )


def _call(callee: str, *arguments: ExpressionIR) -> CallIR:
    return CallIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        callee=callee,
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, callee),
        arguments=arguments,
    )


def test_literals_and_field_references_render_with_mysql_policies() -> None:
    assert render_mysql_expression(_literal("O'Reilly")) == "'O''Reilly'"
    assert render_mysql_expression(_field("order")) == "`order`"
    assert (
        render_mysql_expression(_field("email", qualifier=("app", "users")))
        == "`app`.`users`.`email`"
    )


def test_approved_function_mappings_are_uppercase_and_recursive() -> None:
    expression = _call("lower", _call("trim", _field("email")))

    assert render_mysql_expression(expression) == "LOWER(TRIM(`email`))"
    assert render_mysql_expression(_call("len", _field("email"))) == (
        "CHAR_LENGTH(`email`)"
    )


def test_q1_control_expressions_and_fixed_like_escape_render() -> None:
    condition = ComparisonIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        left=_field("age"),
        operator=">=",
        right=_literal(18),
    )
    conditional = ConditionalIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        when_true=_literal("adult"),
        condition=condition,
        when_false=_literal("minor"),
    )
    membership = MembershipIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        value=_field("id"),
        options=(_literal(1), _literal(2)),
        negated=True,
    )
    like = ComparisonIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        left=_field("label"),
        operator="not like",
        right=_literal("100!%%"),
    )

    assert render_mysql_expression(conditional) == (
        "CASE WHEN (`age` >= 18) THEN 'adult' ELSE 'minor' END"
    )
    assert render_mysql_expression(membership) == "`id` NOT IN (1, 2)"
    assert render_mysql_expression(like) == "`label` NOT LIKE '100!%%' ESCAPE '!'"
    assert (
        render_mysql_expression(
            UnaryIR(
                span=SPAN,
                value_type=UNKNOWN_TYPE,
                operator="not",
                operand=membership,
            )
        )
        == "NOT (`id` NOT IN (1, 2))"
    )


@pytest.mark.parametrize(
    ("negated", "expected"),
    [(False, "FALSE"), (True, "TRUE")],
)
def test_q1_empty_membership_is_a_checked_boolean_constant(
    negated: bool,
    expected: str,
) -> None:
    expression = MembershipIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        value=_field("id"),
        options=(),
        negated=negated,
    )

    assert render_mysql_expression(expression) == expected
    with pytest.raises(MySqlRenderError):
        render_mysql_expression(
            MembershipIR(
                span=SPAN,
                value_type=UNKNOWN_TYPE,
                value=_call("unknown", _literal(1)),
                options=(),
                negated=negated,
            )
        )


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        (
            _call(
                "coalesce", _field("nickname"), _field("name"), _literal("anonymous")
            ),
            "COALESCE(`nickname`, `name`, 'anonymous')",
        ),
        (_call("nullif", _field("name"), _literal("")), "NULLIF(`name`, '')"),
        (_call("upper", _field("name")), "UPPER(`name`)"),
        (
            _call("substr", _field("name"), _literal(2), _literal(3)),
            "SUBSTRING(`name`, 2, 3)",
        ),
        (
            _call("replace", _field("name"), _literal("a"), _literal("b")),
            "REPLACE(`name`, 'a', 'b')",
        ),
        (_call("contains", _field("name"), _literal("et")), "INSTR(`name`, 'et') > 0"),
        (
            _call("starts_with", _field("name"), _literal("pi")),
            "LEFT(`name`, CHAR_LENGTH('pi')) = 'pi'",
        ),
        (
            _call("ends_with", _field("name"), _literal("to")),
            "RIGHT(`name`, CHAR_LENGTH('to')) = 'to'",
        ),
        (_call("abs", _field("amount")), "ABS(`amount`)"),
        (_call("sign", _field("amount")), "SIGN(`amount`)"),
        (_call("date_of", _field("happened_at")), "DATE(`happened_at`)"),
        (_call("year", _field("happened_at")), "YEAR(`happened_at`)"),
    ],
)
def test_q1_closed_function_rendering(expression: ExpressionIR, expected: str) -> None:
    assert render_mysql_expression(expression) == expected


def test_q1_int_to_float_cast_uses_explicit_double() -> None:
    cast = CastIR(
        span=SPAN,
        value_type=FLOAT_TYPE,
        value=FieldRefIR(
            span=SPAN,
            value_type=INT_TYPE,
            name="id",
            qualifier=(),
            field=None,
        ),
        target=FLOAT_TYPE,
    )

    assert render_mysql_expression(cast) == "CAST(`id` AS DOUBLE)"


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("==", "`count` = 1"),
        ("!=", "`count` <> 1"),
        ("<", "`count` < 1"),
        ("<=", "`count` <= 1"),
        (">", "`count` > 1"),
        (">=", "`count` >= 1"),
    ],
)
def test_comparison_ir_maps_approved_operators(
    operator: str,
    expected: str,
) -> None:
    expression = ComparisonIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        left=_field("count"),
        operator=operator,
        right=_literal(1),
    )

    assert render_mysql_expression(expression) == expected


@pytest.mark.parametrize(
    ("negated", "expected"),
    [
        (False, "`deleted_at` IS NULL"),
        (True, "`deleted_at` IS NOT NULL"),
    ],
)
def test_is_null_ir_renders_both_forms(negated: bool, expected: str) -> None:
    expression = IsNullIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        value=_field("deleted_at"),
        negated=negated,
    )

    assert render_mysql_expression(expression) == expected


def test_between_ir_renders_inclusive_predicate() -> None:
    expression = BetweenIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        value=_field("age"),
        lower=_literal(18),
        upper=_literal(65),
    )

    assert render_mysql_expression(expression) == "`age` BETWEEN 18 AND 65"


@pytest.mark.parametrize(("operator", "expected"), [("+", "+1"), ("-", "-1")])
def test_unary_ir_renders_approved_operators(
    operator: str,
    expected: str,
) -> None:
    expression = UnaryIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        operator=operator,
        operand=_literal(1),
    )

    assert render_mysql_expression(expression) == expected


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("+", "1 + 2"),
        ("-", "1 - 2"),
        ("*", "1 * 2"),
        ("/", "1 / 2"),
        ("%", "1 % 2"),
        ("and", "TRUE AND FALSE"),
        ("or", "TRUE OR FALSE"),
    ],
)
def test_binary_ir_renders_approved_operators(
    operator: str,
    expected: str,
) -> None:
    expression = BinaryIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        left=_literal(True if operator in {"and", "or"} else 1),
        operator=operator,
        right=_literal(False if operator in {"and", "or"} else 2),
    )

    assert render_mysql_expression(expression) == expected


def test_nested_compound_expressions_are_parenthesized() -> None:
    expression = BinaryIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        left=ComparisonIR(
            span=SPAN,
            value_type=UNKNOWN_TYPE,
            left=_field("age"),
            operator=">=",
            right=_literal(18),
        ),
        operator="and",
        right=IsNullIR(
            span=SPAN,
            value_type=UNKNOWN_TYPE,
            value=_field("deleted_at"),
            negated=False,
        ),
    )

    assert render_mysql_expression(expression) == (
        "(`age` >= 18) AND (`deleted_at` IS NULL)"
    )


@pytest.mark.parametrize(
    "expression",
    [
        _call("matches", _field("email"), _literal("@")),
        _call("unknown", _literal(1)),
        _call("lower", _literal("a"), _literal("b")),
        CallIR(
            span=SPAN,
            value_type=UNKNOWN_TYPE,
            callee="lower",
            callee_symbol=None,
            arguments=(_literal("a"),),
        ),
        CallIR(
            span=SPAN,
            value_type=UNKNOWN_TYPE,
            callee="lower",
            callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "upper"),
            arguments=(_literal("a"),),
        ),
        BinaryIR(
            span=SPAN,
            value_type=UNKNOWN_TYPE,
            left=_literal(1),
            operator="^",
            right=_literal(2),
        ),
        ExpressionIR(span=SPAN, value_type=UNKNOWN_TYPE),
        LiteralIR(
            span=SPAN,
            value_type=UNKNOWN_TYPE,
            value=cast(StaticValue, object()),
        ),
    ],
)
def test_unsupported_expressions_fail_closed(expression: ExpressionIR) -> None:
    with pytest.raises(MySqlRenderError):
        render_mysql_expression(expression)


def test_mysql_expression_renderer_remains_private_and_isolated() -> None:
    source = inspect.getsource(expression_module)

    assert "render_mysql_expression" not in sql_api.__all__
    for dependency in (
        "antlr",
        "pietto.parser",
        "pietto.semantic",
        "pietto.ir.builder",
        "pietto.ir.lowering",
        "sqlglot",
        "database",
        "connector",
        "pietto.cli",
    ):
        assert dependency not in source
