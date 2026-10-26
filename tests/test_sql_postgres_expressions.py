from __future__ import annotations

import ast
import inspect
from dataclasses import replace

import pytest

import pietto.sql as sql_api
import pietto.sql.expressions as expression_module
from pietto.ir.model import (
    AggregateCallIR,
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
    OrderDirectionIR,
    OrderItemIR,
    SourceSpan,
    StaticValue,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    UnaryIR,
)
from pietto.sql.expressions import (
    expression_uses_qualified_field,
    render_expression_sql,
)

SPAN = SourceSpan(
    path="expressions.pietto",
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


def _typed_field(name: str, value_type: TypeRefIR) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=(),
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
    value: StaticValue,
    expected: str,
) -> None:
    assert render_expression_sql(_literal(value)) == expected


def test_literal_ir_uses_explicit_escape_string_for_backslashes() -> None:
    assert render_expression_sql(_literal("\\'; --")) == "E'\\\\''; --'"


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


@pytest.mark.parametrize("position", (1, 2))
def test_substr_refuses_static_indexes_outside_postgres_int32(position: int) -> None:
    arguments: list[ExpressionIR] = [_field("name"), _literal(1), _literal(1)]
    arguments[position] = _literal(1 << 31)

    with pytest.raises(ValueError, match="substring index"):
        render_expression_sql(_call("substr", *arguments))


def test_matches_call_uses_postgres_regex_operator() -> None:
    expression = _call("matches", _field("email"), _literal(".+@.+"))

    assert render_expression_sql(expression) == "\"email\" ~ '.+@.+'"


@pytest.mark.parametrize(
    "callee_symbol",
    [None, SymbolId(SymbolNamespace.CALLABLE, "upper")],
)
def test_postgres_call_requires_exact_callable_identity(
    callee_symbol: SymbolId | None,
) -> None:
    expression = CallIR(
        span=SPAN,
        value_type=UNKNOWN_TYPE,
        callee="lower",
        callee_symbol=callee_symbol,
        arguments=(_literal("x"),),
    )

    with pytest.raises(ValueError, match="function identity"):
        render_expression_sql(expression)


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

    assert render_expression_sql(conditional) == (
        "CASE WHEN (\"age\" >= 18) THEN 'adult' ELSE 'minor' END"
    )
    assert render_expression_sql(membership) == '"id" NOT IN (1, 2)'
    assert render_expression_sql(like) == "\"label\" NOT LIKE '100!%%' ESCAPE '!'"
    assert (
        render_expression_sql(
            UnaryIR(
                span=SPAN,
                value_type=UNKNOWN_TYPE,
                operator="not",
                operand=membership,
            )
        )
        == 'NOT ("id" NOT IN (1, 2))'
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

    assert render_expression_sql(expression) == expected
    with pytest.raises(ValueError):
        render_expression_sql(
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
            'COALESCE("nickname", "name", \'anonymous\')',
        ),
        (_call("nullif", _field("name"), _literal("")), "NULLIF(\"name\", '')"),
        (_call("upper", _field("name")), 'upper("name")'),
        (
            _call("substr", _field("name"), _literal(2), _literal(3)),
            'substring("name" FROM 2 FOR 3)',
        ),
        (
            _call("replace", _field("name"), _literal("a"), _literal("b")),
            "replace(\"name\", 'a', 'b')",
        ),
        (
            _call("contains", _field("name"), _literal("et")),
            "position('et' IN \"name\") > 0",
        ),
        (
            _call("starts_with", _field("name"), _literal("pi")),
            "left(\"name\", length('pi')) = 'pi'",
        ),
        (
            _call("ends_with", _field("name"), _literal("to")),
            "right(\"name\", length('to')) = 'to'",
        ),
        (_call("abs", _field("amount")), 'abs("amount")'),
        (_call("sign", _field("amount")), 'CAST(sign("amount") AS bigint)'),
        (_call("date_of", _field("happened_at")), 'CAST("happened_at" AS date)'),
        (
            _call("year", _field("happened_at")),
            'CAST(EXTRACT(YEAR FROM "happened_at") AS bigint)',
        ),
        # PostgreSQL resolves no EXTRACT of an untyped NULL.
        (_call("year", _literal(None)), "CAST(NULL AS bigint)"),
        (_call("minute", _literal(None)), "CAST(NULL AS bigint)"),
    ],
)
def test_q1_closed_function_rendering(expression: ExpressionIR, expected: str) -> None:
    assert render_expression_sql(expression) == expected


def test_q1_cast_and_qualified_field_traversal_render() -> None:
    cast = CastIR(
        span=SPAN,
        value_type=FLOAT_TYPE,
        value=FieldRefIR(
            span=SPAN,
            value_type=INT_TYPE,
            name="id",
            qualifier=("app", "users"),
            field=None,
        ),
        target=FLOAT_TYPE,
    )

    assert render_expression_sql(cast) == 'CAST("app"."users"."id" AS double precision)'
    assert expression_uses_qualified_field(cast)


def test_c5_text_cast_and_scalar_function_sql_shapes() -> None:
    decimal = _builtin_type("Decimal", NullabilityIR.NULLABLE)
    float_type = _builtin_type("Float", NullabilityIR.NULLABLE)
    int_type = _builtin_type("Int", NullabilityIR.NON_NULL)
    date = _builtin_type("Date", NullabilityIR.NULLABLE)
    timestamp = _builtin_type("Timestamp", NullabilityIR.NULLABLE)
    text = _builtin_type("Text", NullabilityIR.NON_NULL)
    decimal_value = FieldRefIR(
        span=SPAN,
        value_type=decimal,
        name="amount",
        qualifier=(),
        field=None,
    )
    float_value = FieldRefIR(
        span=SPAN,
        value_type=float_type,
        name="ratio",
        qualifier=(),
        field=None,
    )
    scale = LiteralIR(span=SPAN, value_type=int_type, value=2)
    negative_scale = UnaryIR(
        span=SPAN,
        value_type=int_type,
        operator="-",
        operand=scale,
    )
    round_decimal = CallIR(
        span=SPAN,
        value_type=decimal,
        callee="round",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "round"),
        arguments=(decimal_value, scale),
    )
    round_float = CallIR(
        span=SPAN,
        value_type=float_type,
        callee="round",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "round"),
        arguments=(float_value,),
    )
    round_decimal_negative = CallIR(
        span=SPAN,
        value_type=decimal,
        callee="round",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "round"),
        arguments=(decimal_value, negative_scale),
    )
    date_trunc = CallIR(
        span=SPAN,
        value_type=date,
        callee="date_trunc",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "date_trunc"),
        arguments=(
            LiteralIR(span=SPAN, value_type=text, value="month"),
            _typed_field("opened_on", date),
        ),
    )
    timestamp_trunc = CallIR(
        span=SPAN,
        value_type=timestamp,
        callee="date_trunc",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "date_trunc"),
        arguments=(
            LiteralIR(span=SPAN, value_type=text, value="minute"),
            _typed_field("opened_at", timestamp),
        ),
    )
    text_cast = CastIR(
        span=SPAN,
        value_type=text,
        value=_typed_field("id", int_type),
        target=text,
    )

    assert render_expression_sql(round_decimal) == 'round("amount", 2)'
    assert render_expression_sql(round_decimal_negative) == 'round("amount", (-2))'
    assert render_expression_sql(round_float) == (
        'CASE WHEN abs(("ratio" - trunc("ratio"))) >= 0.5 THEN trunc("ratio") '
        '+ CASE WHEN "ratio" < 0 THEN -1.0 ELSE 1.0 END ELSE trunc("ratio") END'
    )
    assert render_expression_sql(date_trunc) == (
        "CAST(date_trunc('month', CAST(\"opened_on\" AS timestamp)) AS date)"
    )
    assert (
        render_expression_sql(timestamp_trunc) == "date_trunc('minute', \"opened_at\")"
    )
    assert render_expression_sql(text_cast) == 'CAST("id" AS text)'


def test_c5_postgres_typed_null_arguments_select_unambiguous_overloads() -> None:
    decimal = _builtin_type("Decimal", NullabilityIR.NULLABLE)
    date = _builtin_type("Date", NullabilityIR.NULLABLE)
    timestamp = _builtin_type("Timestamp", NullabilityIR.NULLABLE)
    text = _builtin_type("Text", NullabilityIR.NON_NULL)
    decimal_round = CallIR(
        span=SPAN,
        value_type=decimal,
        callee="round",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "round"),
        arguments=(LiteralIR(span=SPAN, value_type=decimal, value=None),),
    )
    date_trunc = CallIR(
        span=SPAN,
        value_type=date,
        callee="date_trunc",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "date_trunc"),
        arguments=(
            LiteralIR(span=SPAN, value_type=text, value="year"),
            LiteralIR(span=SPAN, value_type=date, value=None),
        ),
    )
    timestamp_trunc = CallIR(
        span=SPAN,
        value_type=timestamp,
        callee="date_trunc",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "date_trunc"),
        arguments=(
            LiteralIR(span=SPAN, value_type=text, value="minute"),
            LiteralIR(span=SPAN, value_type=timestamp, value=None),
        ),
    )

    assert render_expression_sql(decimal_round) == "round(CAST(NULL AS numeric))"
    assert render_expression_sql(date_trunc) == (
        "CAST(date_trunc('year', CAST(NULL AS timestamp)) AS date)"
    )
    assert render_expression_sql(timestamp_trunc) == (
        "date_trunc('minute', CAST(NULL AS timestamp))"
    )


def test_c5_qualified_internal_aggregate_order_key_is_not_lost() -> None:
    text = _builtin_type("Text", NullabilityIR.NON_NULL)
    aggregate = AggregateCallIR(
        span=SPAN,
        value_type=_builtin_type("Text", NullabilityIR.NULLABLE),
        function="string_agg",
        arguments=(
            LiteralIR(span=SPAN, value_type=text, value="value"),
            LiteralIR(span=SPAN, value_type=text, value=","),
        ),
        order_by=(
            OrderItemIR(
                expression=FieldRefIR(
                    span=SPAN,
                    value_type=INT_TYPE,
                    name="sequence",
                    qualifier=("items",),
                    field=None,
                ),
                direction=OrderDirectionIR.DESC,
                span=SPAN,
            ),
        ),
    )

    assert expression_uses_qualified_field(aggregate)


@pytest.mark.parametrize(
    "expression",
    [
        CallIR(
            span=SPAN,
            value_type=_builtin_type("Float", NullabilityIR.NON_NULL),
            callee="round",
            callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "round"),
            arguments=(
                _typed_field("ratio", _builtin_type("Float", NullabilityIR.NON_NULL)),
                LiteralIR(span=SPAN, value_type=INT_TYPE, value=1),
            ),
        ),
        CallIR(
            span=SPAN,
            value_type=_builtin_type("Date", NullabilityIR.NON_NULL),
            callee="date_trunc",
            callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "date_trunc"),
            arguments=(
                LiteralIR(
                    span=SPAN,
                    value_type=_builtin_type("Text", NullabilityIR.NON_NULL),
                    value="hour",
                ),
                _typed_field(
                    "opened_on", _builtin_type("Date", NullabilityIR.NON_NULL)
                ),
            ),
        ),
        CallIR(
            span=SPAN,
            value_type=_builtin_type("Date", NullabilityIR.NON_NULL),
            callee="date_trunc",
            callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "date_trunc"),
            arguments=(
                LiteralIR(span=SPAN, value_type=INT_TYPE, value="year"),
                _typed_field(
                    "opened_on", _builtin_type("Date", NullabilityIR.NON_NULL)
                ),
            ),
        ),
    ],
)
def test_c5_scalar_renderer_refuses_unapproved_typed_shapes(
    expression: ExpressionIR,
) -> None:
    with pytest.raises(ValueError):
        render_expression_sql(expression)


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


def test_division_renders_sql_division_without_a_cast() -> None:
    left = FieldRefIR(
        span=SPAN, value_type=INT_TYPE, name="n", qualifier=(), field=None
    )
    right = LiteralIR(span=SPAN, value_type=INT_TYPE, value=2)
    integer = BinaryIR(
        span=SPAN, value_type=INT_TYPE, left=left, operator="/", right=right
    )

    assert render_expression_sql(integer) == '"n" / 2'
    for other in (
        replace(
            integer, value_type=FLOAT_TYPE, left=replace(left, value_type=FLOAT_TYPE)
        ),
        replace(integer, value_type=UNKNOWN_TYPE),
        replace(integer, left=_field("n")),
    ):
        assert render_expression_sql(other) == '"n" / 2'


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
    imported = tuple(
        name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for name in (
            *(() if isinstance(node, ast.Import) else (node.module or "",)),
            *(alias.name for alias in node.names),
        )
    )

    assert "render_expression_sql" not in sql_api.__all__
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
