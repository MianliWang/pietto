from __future__ import annotations

import inspect

import pytest

import pietto.sql as sql_api
import pietto.sql.expressions as expression_module
from pietto.ir.model import (
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    NullabilityIR,
    SourceSpan,
    TypeKindIR,
    TypeRefIR,
    UnaryIR,
)
from pietto.sql.expressions import render_expression_sql

SPAN = SourceSpan(
    path="expressions.pie",
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


def _literal(value: object) -> LiteralIR:
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
        callee_symbol=None,
        arguments=arguments,
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "NULL"),
        (True, "TRUE"),
        (42, "42"),
        (1.5, "1.5"),
        ("O'Reilly", "'O''Reilly'"),
    ],
)
def test_literal_ir_uses_scalar_literal_rendering(
    value: object,
    expected: str,
) -> None:
    assert render_expression_sql(_literal(value)) == expected


def test_field_ref_ir_quotes_identifiers_and_qualifiers() -> None:
    assert render_expression_sql(_field('user"name')) == '"user""name"'
    assert render_expression_sql(_field("email", qualifier=("public", "users"))) == (
        '"public"."users"."email"'
    )


def test_lower_and_trim_calls_render_recursively() -> None:
    expression = _call("lower", _call("trim", _field("email")))

    assert render_expression_sql(expression) == 'lower(trim("email"))'


def test_len_call_uses_postgres_length() -> None:
    assert render_expression_sql(_call("len", _field("email"))) == 'length("email")'


def test_matches_call_uses_postgres_regex_operator() -> None:
    expression = _call("matches", _field("email"), _literal(".+@.+"))

    assert render_expression_sql(expression) == "\"email\" ~ '.+@.+'"


@pytest.mark.parametrize(
    ("operator", "expected"),
    [
        ("==", '"count" = 1'),
        ("!=", '"count" <> 1'),
        ("<", '"count" < 1'),
        ("<=", '"count" <= 1'),
        (">", '"count" > 1'),
        (">=", '"count" >= 1'),
    ],
)
def test_comparison_ir_maps_supported_operators(
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

    assert render_expression_sql(expression) == expected


@pytest.mark.parametrize(
    ("negated", "expected"),
    [
        (False, '"deleted_at" IS NULL'),
        (True, '"deleted_at" IS NOT NULL'),
    ],
)
def test_is_null_ir_renders_both_forms(negated: bool, expected: str) -> None:
    expression = IsNullIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        value=_field("deleted_at"),
        negated=negated,
    )

    assert render_expression_sql(expression) == expected


def test_between_ir_renders_inclusive_predicate() -> None:
    expression = BetweenIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        value=_field("age"),
        lower=_literal(18),
        upper=_literal(65),
    )

    assert render_expression_sql(expression) == '"age" BETWEEN 18 AND 65'


@pytest.mark.parametrize(
    ("operator", "expected"),
    [("+", "+1"), ("-", "-1")],
)
def test_unary_ir_renders_supported_operators(
    operator: str,
    expected: str,
) -> None:
    expression = UnaryIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        operator=operator,
        operand=_literal(1),
    )

    assert render_expression_sql(expression) == expected


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
def test_binary_ir_renders_supported_operators(
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

    assert render_expression_sql(expression) == expected


def test_nested_compound_expressions_are_parenthesized() -> None:
    left = ComparisonIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        left=_field("age"),
        operator=">=",
        right=_literal(18),
    )
    right = IsNullIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        value=_field("deleted_at"),
        negated=False,
    )
    expression = BinaryIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        left=left,
        operator="and",
        right=right,
    )

    assert render_expression_sql(expression) == (
        '("age" >= 18) AND ("deleted_at" IS NULL)'
    )


@pytest.mark.parametrize(
    "expression",
    [
        _call("unknown", _literal(1)),
        _call("lower", _literal("a"), _literal("b")),
        ComparisonIR(
            span=SPAN,
            value_type=UNKNOWN_TYPE,
            left=_literal(1),
            operator="like",
            right=_literal("1"),
        ),
        UnaryIR(
            span=SPAN,
            value_type=UNKNOWN_TYPE,
            operator="not",
            operand=_literal(True),
        ),
        BinaryIR(
            span=SPAN,
            value_type=UNKNOWN_TYPE,
            left=_literal(1),
            operator="^",
            right=_literal(2),
        ),
        ExpressionIR(span=SPAN, value_type=UNKNOWN_TYPE),
    ],
)
def test_unsupported_calls_kinds_and_operators_are_not_silently_rendered(
    expression: ExpressionIR,
) -> None:
    with pytest.raises(ValueError):
        render_expression_sql(expression)


def test_expression_renderer_remains_internal_and_dependency_isolated() -> None:
    source = inspect.getsource(expression_module)

    assert "render_expression_sql" not in sql_api.__all__
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
