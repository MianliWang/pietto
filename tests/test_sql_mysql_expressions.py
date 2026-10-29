from __future__ import annotations

import ast
import inspect
import sys
from dataclasses import replace
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


def _builtin_type(name: str, nullability: NullabilityIR) -> TypeRefIR:
    symbol = SymbolId(SymbolNamespace.TYPE, name)
    return TypeRefIR(
        symbol=symbol,
        canonical_symbol=symbol,
        declared_name=name,
        canonical_name=name,
        kind=TypeKindIR.BUILTIN,
        canonical_kind=TypeKindIR.BUILTIN,
        nullability=nullability,
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


def test_mysql_only_emits_proven_decimal_round_and_int_text_cast() -> None:
    decimal = _builtin_type("Decimal", NullabilityIR.NULLABLE)
    int_type = _builtin_type("Int", NullabilityIR.NON_NULL)
    text = _builtin_type("Text", NullabilityIR.NON_NULL)
    value = FieldRefIR(
        span=SPAN,
        value_type=decimal,
        name="amount",
        qualifier=(),
        field=None,
    )
    round_decimal = CallIR(
        span=SPAN,
        value_type=decimal,
        callee="round",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "round"),
        arguments=(
            value,
            UnaryIR(
                span=SPAN,
                value_type=int_type,
                operator="-",
                operand=LiteralIR(span=SPAN, value_type=int_type, value=2),
            ),
        ),
    )
    text_cast = CastIR(
        span=SPAN,
        value_type=text,
        value=FieldRefIR(
            span=SPAN,
            value_type=int_type,
            name="id",
            qualifier=(),
            field=None,
        ),
        target=text,
    )

    assert render_mysql_expression(round_decimal) == "ROUND(`amount`, (-2))"
    assert render_mysql_expression(text_cast) == "CAST(`id` AS CHAR)"


def _typed_call(callee: str, type_name: str, *arguments: ExpressionIR) -> CallIR:
    return replace(
        _call(callee, *arguments),
        value_type=_builtin_type(type_name, NullabilityIR.NULLABLE),
    )


def _typed_field(name: str, type_name: str) -> FieldRefIR:
    return replace(
        _field(name), value_type=_builtin_type(type_name, NullabilityIR.NULLABLE)
    )


def _text(value: str) -> LiteralIR:
    return replace(
        _literal(value), value_type=_builtin_type("Text", NullabilityIR.NON_NULL)
    )


def test_mysql_rounds_a_float_half_away_from_zero_without_round() -> None:
    expression = _typed_call("round", "Float", _typed_field("ratio", "Float"))

    # MySQL ROUND of a DOUBLE may round half to even, so Pietto never uses it.
    assert render_mysql_expression(expression) == (
        "CASE WHEN ABS(`ratio` - TRUNCATE(`ratio`, 0)) >= 0.5 THEN "
        "TRUNCATE(`ratio`, 0) + CASE WHEN `ratio` < 0 THEN -1.0 ELSE 1.0 END "
        "ELSE TRUNCATE(`ratio`, 0) END"
    )


def test_mysql_round_float_refuses_float_arithmetic_without_a_double_operand() -> None:
    def float_op(left: ExpressionIR, operator: str, right: ExpressionIR) -> BinaryIR:
        float_type = _builtin_type("Float", NullabilityIR.NULLABLE)
        return BinaryIR(
            span=SPAN, value_type=float_type, left=left, operator=operator, right=right
        )

    ratio = _typed_field("ratio", "Float")
    amount = _typed_field("amount", "Int")
    half = replace(_literal(0.5), value_type=FLOAT_TYPE)
    tiny = replace(_literal(1e-17), value_type=FLOAT_TYPE)

    # PostgreSQL computes 0.5 - 1e-17 and amount + 0.5 - 1e-17 exactly as
    # numeric and rounds them to 0 at amount 0; MySQL reads 1e-17 as a
    # DOUBLE, gets 0.5 and would round it to 1.
    for value in (
        float_op(half, "-", tiny),
        float_op(ratio, "-", float_op(half, "-", tiny)),
        float_op(float_op(amount, "+", half), "-", tiny),
        float_op(float_op(amount, "*", tiny), "+", half),
        float_op(amount, "/", half),
    ):
        with pytest.raises(MySqlRenderError) as raised:
            render_mysql_expression(_typed_call("round", "Float", value))
        assert str(raised.value) == (
            "MySQL function round(Float) supports Float arithmetic only with a "
            "DOUBLE operand"
        )
    # Beside a DOUBLE, each operand is read as a DOUBLE on both targets.
    for value, text in (
        (float_op(ratio, "-", tiny), "(`ratio` - 1e-17)"),
        (
            float_op(float_op(amount, "+", ratio), "-", tiny),
            "((`amount` + `ratio`) - 1e-17)",
        ),
        (
            float_op(amount, "/", _typed_call("nullif", "Float", ratio, half)),
            "(`amount` / NULLIF(`ratio`, 0.5))",
        ),
    ):
        assert render_mysql_expression(_typed_call("round", "Float", value)).startswith(
            f"CASE WHEN ABS({text} - TRUNCATE({text}, 0))"
        )


@pytest.mark.parametrize(
    ("type_name", "unit", "expected"),
    [
        ("Date", "year", "DATE_SUB(`at`, INTERVAL (DAYOFYEAR(`at`) - 1) DAY)"),
        ("Date", "month", "DATE_SUB(`at`, INTERVAL (DAYOFMONTH(`at`) - 1) DAY)"),
        ("Date", "day", "`at`"),
        (
            "Timestamp",
            "year",
            "TIMESTAMP(DATE_SUB(DATE(`at`), INTERVAL (DAYOFYEAR(`at`) - 1) DAY))",
        ),
        (
            "Timestamp",
            "month",
            "TIMESTAMP(DATE_SUB(DATE(`at`), INTERVAL (DAYOFMONTH(`at`) - 1) DAY))",
        ),
        ("Timestamp", "day", "TIMESTAMP(DATE(`at`))"),
        ("Timestamp", "hour", "TIMESTAMP(DATE(`at`), MAKETIME(HOUR(`at`), 0, 0))"),
        (
            "Timestamp",
            "minute",
            "TIMESTAMP(DATE(`at`), MAKETIME(HOUR(`at`), MINUTE(`at`), 0))",
        ),
    ],
)
def test_mysql_truncates_a_date_or_timestamp_from_its_parts(
    type_name: str, unit: str, expected: str
) -> None:
    expression = _typed_call(
        "date_trunc", type_name, _text(unit), _typed_field("at", type_name)
    )

    assert render_mysql_expression(expression) == expected


def test_mysql_date_trunc_repeats_its_value_only_without_another_date_trunc() -> None:
    """Each unit but day repeats its value, so nested date_trunc calls would
    grow the SQL exponentially; only a day truncation holds another."""

    minute = _typed_call(
        "date_trunc", "Timestamp", _text("minute"), _typed_field("at", "Timestamp")
    )

    assert render_mysql_expression(
        _typed_call("date_trunc", "Timestamp", _text("day"), minute)
    ) == (
        "TIMESTAMP(DATE(TIMESTAMP(DATE(`at`), MAKETIME(HOUR(`at`), MINUTE(`at`), 0))))"
    )
    with pytest.raises(MySqlRenderError) as raised:
        render_mysql_expression(
            _typed_call(
                "date_trunc",
                "Timestamp",
                _text("hour"),
                _typed_call("date_trunc", "Timestamp", _text("day"), minute),
            )
        )
    assert str(raised.value) == (
        "MySQL function date_trunc with unit hour repeats its value, which must "
        "not hold another date_trunc"
    )


def test_mysql_round_float_decides_a_deep_float_expression_without_recursion() -> None:
    float_type = _builtin_type("Float", NullabilityIR.NULLABLE)
    exact = replace(_literal(0.5), value_type=FLOAT_TYPE)
    double = _typed_field("ratio", "Float")
    for leaf, inexact in ((double, False), (exact, True)):
        value: ExpressionIR = leaf
        for _ in range(sys.getrecursionlimit() + 10):
            value = BinaryIR(
                span=SPAN, value_type=float_type, left=value, operator="+", right=exact
            )

        assert expression_module.is_mysql_double(value) is not inexact
        assert expression_module.has_inexact_float_arithmetic(value) is inexact


@pytest.mark.parametrize(
    ("expression", "message"),
    [
        pytest.param(
            _typed_call(
                "round",
                "Float",
                _typed_field("ratio", "Float"),
                replace(_literal(2), value_type=INT_TYPE),
            ),
            "MySQL function round(Float) expects 1 argument",
            id="float-with-scale",
        ),
        pytest.param(
            _typed_call("round", "Int", _typed_field("id", "Int")),
            "MySQL supports round only for Decimal and Float",
            id="int",
        ),
        pytest.param(
            _typed_call("date_trunc", "Date"),
            "MySQL function date_trunc expects 2 argument(s)",
            id="date-trunc-arity",
        ),
        pytest.param(
            _typed_call(
                "date_trunc", "Date", _text("hour"), _typed_field("at", "Date")
            ),
            "MySQL function date_trunc unit is unsupported",
            id="date-trunc-hour-of-a-date",
        ),
        pytest.param(
            _typed_call(
                "date_trunc",
                "Timestamp",
                _text("week"),
                _typed_field("at", "Timestamp"),
            ),
            "MySQL function date_trunc unit is unsupported",
            id="date-trunc-week",
        ),
        pytest.param(
            _typed_call(
                "date_trunc",
                "Timestamp",
                _typed_field("unit", "Text"),
                _typed_field("at", "Timestamp"),
            ),
            "MySQL function date_trunc unit must be a Text literal",
            id="date-trunc-unit-field",
        ),
        pytest.param(
            _typed_call(
                "date_trunc", "Date", _text("day"), _typed_field("at", "Timestamp")
            ),
            "MySQL function date_trunc has an invalid typed shape",
            id="date-trunc-type-mismatch",
        ),
    ],
)
def test_mysql_refuses_unproven_function_shapes(
    expression: ExpressionIR, message: str
) -> None:
    with pytest.raises(MySqlRenderError) as raised:
        render_mysql_expression(expression)

    assert str(raised.value) == message


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


def test_division_renders_sql_division_without_a_cast() -> None:
    left = FieldRefIR(
        span=SPAN, value_type=INT_TYPE, name="n", qualifier=(), field=None
    )
    right = LiteralIR(span=SPAN, value_type=INT_TYPE, value=2)
    integer = BinaryIR(
        span=SPAN, value_type=INT_TYPE, left=left, operator="/", right=right
    )

    assert render_mysql_expression(integer) == "`n` DIV 2"
    for other in (
        replace(
            integer, value_type=FLOAT_TYPE, left=replace(left, value_type=FLOAT_TYPE)
        ),
        replace(integer, value_type=UNKNOWN_TYPE),
        replace(integer, left=_field("n")),
    ):
        assert render_mysql_expression(other) == "`n` / 2"


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
    imported = tuple(
        name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for name in (
            *(() if isinstance(node, ast.Import) else (node.module or "",)),
            *(alias.name for alias in node.names),
        )
    )

    assert "render_mysql_expression" not in sql_api.__all__
    for dependency in (
        "antlr",
        "pietto.parser",
        "pietto.semantic",
        "pietto.ir.builder",
        "pietto.ir.lowering",
        "sqlglot",
        "database",
        "pietto.cli",
    ):
        assert dependency not in source
    # Scalar ANY reads the checked `ExistsIR.connector`, as the relation emitter
    # reads `SourceIR.connector`; importing a connector stays forbidden.
    assert not any("connector" in name for name in imported)
