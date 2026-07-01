from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

import pytest

from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    build_ir,
)
from pietto.ir.model import StaticValue
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.mysql_render import MySqlRenderError

SPAN = SourceSpan(
    path="phase39-count-expression-sql.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
OWNER = SymbolId(SymbolNamespace.RELATION, "orders")
INT_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Int"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Int"),
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
INT_UNKNOWN = replace(INT_NON_NULL, nullability=NullabilityIR.UNKNOWN)
FLOAT_UNKNOWN = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Float"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Float"),
    declared_name="Float",
    canonical_name="Float",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.UNKNOWN,
)
TEXT_UNKNOWN = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
    declared_name="Text",
    canonical_name="Text",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.UNKNOWN,
)
BOOL_UNKNOWN = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Bool"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Bool"),
    declared_name="Bool",
    canonical_name="Bool",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.UNKNOWN,
)
ANY_NULLABLE = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Any"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Any"),
    declared_name="Any",
    canonical_name="Any",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
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

BASE_SHAPE = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    optional_active: Bool nullable\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
)


@pytest.mark.parametrize(
    ("projection", "expected_postgres", "expected_mysql"),
    [
        (
            "amount_tax = count(amount + tax)",
            'COUNT(("amount" + "tax"))',
            "COUNT((`amount` + `tax`))",
        ),
        (
            "amount_one = count(amount + 1)",
            'COUNT(("amount" + 1))',
            "COUNT((`amount` + 1))",
        ),
        (
            "positive_amount = count(+amount)",
            'COUNT((+"amount"))',
            "COUNT((+`amount`))",
        ),
        (
            "modulo_amount = count(amount % tax)",
            'COUNT(("amount" % "tax"))',
            "COUNT((`amount` % `tax`))",
        ),
        (
            "weighted = count(score * weight)",
            'COUNT(("score" * "weight"))',
            "COUNT((`score` * `weight`))",
        ),
        (
            "lowered = count(lower(status))",
            'COUNT(lower("status"))',
            "COUNT(LOWER(`status`))",
        ),
        (
            "trimmed = count(trim(status))",
            'COUNT(trim("status"))',
            "COUNT(TRIM(`status`))",
        ),
        (
            "length_status = count(len(status))",
            'COUNT(length("status"))',
            "COUNT(CHAR_LENGTH(`status`))",
        ),
        (
            "active_count = count(active and true)",
            'COUNT(("active" AND TRUE))',
            "COUNT((`active` AND TRUE))",
        ),
        (
            "optional_active_count = count(active or optional_active)",
            'COUNT(("active" OR "optional_active"))',
            "COUNT((`active` OR `optional_active`))",
        ),
    ],
)
def test_direct_renderers_render_count_expression_arguments(
    projection: str,
    expected_postgres: str,
    expected_mysql: str,
) -> None:
    expression = _single_projection_expression(_source("postgres.table", projection))

    assert render_expression_sql(expression) == expected_postgres
    assert render_mysql_expression(expression) == expected_mysql


def test_existing_count_star_and_direct_count_field_sql_remain_byte_compatible() -> (
    None
):
    count_star = _aggregate("count", INT_NON_NULL)
    count_amount = _aggregate("count", INT_NON_NULL, _field("amount", INT_UNKNOWN))
    count_qualified_status = _aggregate(
        "count",
        INT_NON_NULL,
        _field("status", TEXT_UNKNOWN, qualifier=("orders",)),
    )

    assert render_expression_sql(count_star) == "COUNT(*)"
    assert render_mysql_expression(count_star) == "COUNT(*)"
    assert render_expression_sql(count_amount) == 'COUNT("amount")'
    assert render_mysql_expression(count_amount) == "COUNT(`amount`)"
    assert render_expression_sql(count_qualified_status) == 'COUNT("orders"."status")'
    assert render_mysql_expression(count_qualified_status) == "COUNT(`orders`.`status`)"


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_sql"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "SELECT\n"
            '    "region" AS "region",\n'
            '    COUNT(("amount" + "tax")) AS "amount_tax",\n'
            '    COUNT(lower("status")) AS "lowered",\n'
            '    COUNT(("active" OR "optional_active")) AS "active_count"\n'
            'FROM "orders"\n'
            "GROUP BY\n"
            '    "region"',
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "SELECT\n"
            "    `region` AS `region`,\n"
            "    COUNT((`amount` + `tax`)) AS `amount_tax`,\n"
            "    COUNT(LOWER(`status`)) AS `lowered`,\n"
            "    COUNT((`active` OR `optional_active`)) AS `active_count`\n"
            "FROM `orders`\n"
            "GROUP BY\n"
            "    `region`",
        ),
    ],
)
def test_backends_emit_grouped_count_expression_sql(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_sql: str,
) -> None:
    result = emitter(
        _compile(
            _source(
                connector,
                "region\n"
                "        amount_tax = count(amount + tax)\n"
                "        lowered = count(lower(status))\n"
                "        active_count = count(active or optional_active)",
                grouped=True,
            )
        )
    )

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].sql == expected_sql


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = count(1)", "PIE-S2315"),
        ('value = count("x")', "PIE-S2315"),
        ("value = count(true)", "PIE-S2315"),
        ("value = count(1 + 2)", "PIE-S2315"),
        ("value = count(amount > 1)", "PIE-S2315"),
        ("value = count(amount between 1 and 10)", "PIE-S2315"),
        ("value = count(amount is null)", "PIE-S2315"),
        ('value = count(matches(status, "active"))', "PIE-S2315"),
        ("value = count_distinct(amount + tax)", "PIE-S2315"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(amount + tax)", "PIE-S2315"),
        ("value = count(count())", "PIE-S2311"),
        ("value = count(amount) + 1", "PIE-S2310"),
        ("value = count_if(active)", "PIE-S2103"),
    ],
)
def test_deferred_count_family_forms_stop_before_sql(
    projection: str,
    expected_code: str,
) -> None:
    parse_result = parse_source(_source("postgres.table", projection))
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    ir_result = build_ir(parse_result.ast, semantic_result.model)

    assert _error_codes(semantic_result) == [expected_code]
    if ir_result.ir is not None:
        result = emit_postgres_sql(ir_result.ir)
        assert result.artifacts == ()


@pytest.mark.parametrize(
    "case",
    [
        "literal",
        "literal_only_binary",
        "unresolved_field",
        "division",
        "comparison",
        "between",
        "is_null",
        "nested_aggregate",
        "matches_call",
        "wrong_call_arity",
        "unresolved_call",
    ],
)
def test_malformed_hand_built_count_expression_ir_fails_closed(
    case: str,
) -> None:
    aggregate = _aggregate("count", INT_NON_NULL, _malformed_argument(case))

    with pytest.raises(ValueError, match="direct field argument"):
        render_expression_sql(aggregate)
    with pytest.raises(MySqlRenderError, match="direct field argument"):
        render_mysql_expression(aggregate)


def test_direct_any_and_unknown_field_count_ir_still_fail_closed() -> None:
    for argument in (
        _field("anything", ANY_NULLABLE),
        _field("mystery", UNKNOWN_TYPE),
    ):
        aggregate = _aggregate("count", INT_NON_NULL, argument)

        with pytest.raises(ValueError):
            render_expression_sql(aggregate)
        with pytest.raises(MySqlRenderError):
            render_mysql_expression(aggregate)


def test_phase39_slice5_does_not_add_deferred_relation_or_public_mysql_surface() -> (
    None
):
    import pietto.ir as ir_api
    import pietto.sql as sql_api

    assert not hasattr(ir_api, "RelationLayerIR")
    assert "emit_mysql_sql" not in sql_api.__all__


def _source(
    connector: str,
    projections: str,
    *,
    grouped: bool = False,
) -> str:
    group_by = "    group by:\n        region\n" if grouped else ""
    return (
        BASE_SHAPE + f'source orders: Order is {connector}("orders")\n'
        "table order_counts:\n"
        "    from orders\n"
        f"{group_by}"
        "    select:\n"
        f"        {projections}\n"
    )


def _compile(source: str) -> ScriptIR:
    parse_result = parse_source(source)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert _error_codes(semantic_result) == []

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _single_projection_expression(source: str) -> AggregateCallIR:
    relation = _single_relation_ir(source)
    assert len(relation.projections) == 1
    expression = relation.projections[0].expression
    assert isinstance(expression, AggregateCallIR)
    assert expression.function == "count"
    return expression


def _single_relation_ir(source: str) -> RelationIR:
    relations = [
        definition
        for definition in _compile(source).definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _aggregate(
    function: str,
    value_type: TypeRefIR,
    *arguments: ExpressionIR,
) -> AggregateCallIR:
    return AggregateCallIR(
        span=SPAN,
        value_type=value_type,
        function=function,
        arguments=arguments,
    )


def _field(
    name: str,
    value_type: TypeRefIR,
    *,
    qualifier: tuple[str, ...] = (),
    resolved: bool = True,
) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=qualifier,
        field=FieldId(owner=OWNER, name=name) if resolved else None,
    )


def _literal(value: StaticValue, value_type: TypeRefIR) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=value_type, value=value)


def _binary(
    left: ExpressionIR,
    operator: str,
    right: ExpressionIR,
    *,
    value_type: TypeRefIR = INT_UNKNOWN,
) -> BinaryIR:
    return BinaryIR(
        span=SPAN,
        value_type=value_type,
        left=left,
        operator=operator,
        right=right,
    )


def _call(
    callee: str,
    value_type: TypeRefIR,
    *arguments: ExpressionIR,
    resolved: bool = True,
) -> CallIR:
    return CallIR(
        span=SPAN,
        value_type=value_type,
        callee=callee,
        callee_symbol=(
            SymbolId(SymbolNamespace.CALLABLE, callee) if resolved else None
        ),
        arguments=arguments,
    )


def _malformed_argument(case: str) -> ExpressionIR:
    if case == "literal":
        return _literal(1, INT_NON_NULL)
    if case == "literal_only_binary":
        return _binary(_literal(1, INT_NON_NULL), "+", _literal(2, INT_NON_NULL))
    if case == "unresolved_field":
        return _field("amount", INT_UNKNOWN, resolved=False)
    if case == "division":
        return _binary(_field("amount", INT_UNKNOWN), "/", _field("tax", INT_UNKNOWN))
    if case == "comparison":
        return ComparisonIR(
            span=SPAN,
            value_type=BOOL_UNKNOWN,
            left=_field("amount", INT_UNKNOWN),
            operator=">",
            right=_literal(1, INT_NON_NULL),
        )
    if case == "between":
        return BetweenIR(
            span=SPAN,
            value_type=BOOL_UNKNOWN,
            value=_field("amount", INT_UNKNOWN),
            lower=_literal(1, INT_NON_NULL),
            upper=_literal(10, INT_NON_NULL),
        )
    if case == "is_null":
        return IsNullIR(
            span=SPAN,
            value_type=BOOL_UNKNOWN,
            value=_field("amount", INT_UNKNOWN),
            negated=False,
        )
    if case == "nested_aggregate":
        return _aggregate("count", INT_NON_NULL)
    if case == "matches_call":
        return _call(
            "matches",
            BOOL_UNKNOWN,
            _field("status", TEXT_UNKNOWN),
            _literal("x", TEXT_UNKNOWN),
        )
    if case == "wrong_call_arity":
        return _call(
            "lower",
            TEXT_UNKNOWN,
            _field("status", TEXT_UNKNOWN),
            _literal("x", TEXT_UNKNOWN),
        )
    if case == "unresolved_call":
        return _call(
            "lower",
            TEXT_UNKNOWN,
            _field("status", TEXT_UNKNOWN),
            resolved=False,
        )
    raise AssertionError(f"Unknown malformed count expression IR case: {case}")


def _error_codes(result: object) -> list[str]:
    diagnostics = getattr(result, "diagnostics")
    return [
        diagnostic.code
        for diagnostic in diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
