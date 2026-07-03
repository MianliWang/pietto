from __future__ import annotations

from dataclasses import fields

import pytest

from pietto.ast_nodes import CallExpr, QueryDef, Script, ShapeDef, TableDef, TypeExpr
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    ExpressionIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    TypeRefIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    SemanticResult,
    TypeKind,
    ValueType,
    analyze,
)
from pietto.semantic.model import DecimalPrecisionScale
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

_FORBIDDEN_PUBLIC_OUTPUT_TOKENS = ("DECIMAL(", "NUMERIC(", "precision", "scale")


def test_decimal_precision_scale_direct_aggregates_remain_logical_decimal() -> None:
    script, semantic_result, script_ir = _compile(
        _source(
            "postgres.table",
            "table decimal_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = sum(amount)\n"
            "        average = avg(amount)\n"
            "        smallest = min(amount)\n"
            "        largest = max(amount)\n"
            "        known_amounts = count(amount)\n"
            "        unique_amounts = count_distinct(amount)\n",
        )
    )

    amount_type_expr = _shape_field_type_expr(script, "amount")
    assert semantic_result.model.decimal_precision_scale_for(
        amount_type_expr
    ) == DecimalPrecisionScale(12, 2)

    semantic_fields = semantic_result.model.relation_row_schemas[
        _relation_ast(script)
    ].fields
    for field_name in ("total", "average", "smallest", "largest"):
        _assert_semantic_field(
            semantic_fields[field_name],
            "Decimal",
            EffectiveNullability.NULLABLE,
        )
    for field_name in ("known_amounts", "unique_amounts"):
        _assert_semantic_field(
            semantic_fields[field_name],
            "Int",
            EffectiveNullability.NON_NULL,
        )

    ir_fields = {
        field.name: field for field in _relation_ir(script_ir).row_schema.fields
    }
    for field_name in ("total", "average", "smallest", "largest"):
        _assert_ir_type_ref(
            ir_fields[field_name].type_ref,
            canonical_name="Decimal",
            nullability=NullabilityIR.NULLABLE,
        )
    for field_name in ("known_amounts", "unique_amounts"):
        _assert_ir_type_ref(
            ir_fields[field_name].type_ref,
            canonical_name="Int",
            nullability=NullabilityIR.NON_NULL,
        )


def test_decimal_precision_scale_aggregate_expressions_preserve_existing_boundary() -> (
    None
):
    script, semantic_result, script_ir = _compile(
        _source(
            "postgres.table",
            "table decimal_expression_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        decimal_total = sum(amount + tax)\n"
            "        decimal_average = avg(amount - tax)\n"
            "        known_decimal_expression = count(amount + tax)\n",
        )
    )
    relation = _relation_ast(script)
    semantic_fields = semantic_result.model.relation_row_schemas[relation].fields

    _assert_semantic_field(
        semantic_fields["decimal_total"],
        "Decimal",
        EffectiveNullability.NULLABLE,
    )
    _assert_semantic_field(
        semantic_fields["decimal_average"],
        "Decimal",
        EffectiveNullability.NULLABLE,
    )
    _assert_semantic_field(
        semantic_fields["known_decimal_expression"],
        "Int",
        EffectiveNullability.NON_NULL,
    )

    for select_item, operator, result_type in (
        (relation.select_items[0], "+", "Decimal"),
        (relation.select_items[1], "-", "Decimal"),
        (relation.select_items[2], "+", "Int"),
    ):
        expression = select_item.expression
        assert isinstance(expression, CallExpr)
        argument = expression.arguments[0]
        _assert_semantic_value_type(
            semantic_result.model.expression_value_types[argument],
            "Decimal",
            EffectiveNullability.UNKNOWN,
        )
        _assert_semantic_value_type(
            semantic_result.model.expression_value_types[expression],
            result_type,
            EffectiveNullability.NULLABLE
            if result_type == "Decimal"
            else EffectiveNullability.NON_NULL,
        )

        assert select_item.alias is not None
        aggregate = _projection_expression(script_ir, select_item.alias)
        assert isinstance(aggregate, AggregateCallIR)
        assert len(aggregate.arguments) == 1
        assert isinstance(aggregate.arguments[0], BinaryIR)
        assert aggregate.arguments[0].operator == operator
        _assert_ir_type_ref(
            aggregate.arguments[0].value_type,
            canonical_name="Decimal",
            nullability=NullabilityIR.UNKNOWN,
        )
        _assert_ir_type_ref(
            aggregate.value_type,
            canonical_name=result_type,
            nullability=NullabilityIR.NULLABLE
            if result_type == "Decimal"
            else NullabilityIR.NON_NULL,
        )


def test_decimal_precision_scale_sql_output_remains_logical_and_unparameterized() -> (
    None
):
    for connector, emitter in (
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ):
        _, _, script_ir = _compile(
            _source(
                connector,
                "table decimal_stats:\n"
                "    from orders\n"
                "    select:\n"
                "        total = sum(amount)\n"
                "        average = avg(amount - tax)\n"
                "        known_decimal_expression = count(amount + tax)\n"
                "        unique_amounts = count_distinct(amount)\n",
            )
        )

        sql_result = emitter(script_ir)
        assert sql_result.diagnostics == ()
        assert sql_result.artifacts
        _assert_public_text_has_no_precision_scale(
            "\n".join(artifact.sql for artifact in sql_result.artifacts)
        )


def test_decimal_precision_scale_alias_aggregate_arguments_remain_fail_closed() -> None:
    semantic_result = analyze(
        _parse(
            _source(
                "postgres.table",
                "table decimal_stats:\n"
                "    from orders\n"
                "    select:\n"
                "        alias_total = sum(money)\n",
            )
        )
    )

    assert _errors(semantic_result) == [
        (
            "PIE-S2314",
            "Aggregate function sum expects Int, Float, or Decimal field "
            "argument, got Money",
        )
    ]


@pytest.mark.parametrize(
    ("projection", "function_name"),
    [
        ("value = sum(amount * tax)", "sum"),
        ("value = avg(amount * tax)", "avg"),
        ("value = sum(amount / tax)", "sum"),
        ("value = sum(amount + 1)", "sum"),
        ("value = sum(1.23)", "sum"),
        ("value = count(1)", "count"),
    ],
)
def test_deferred_decimal_numeric_aggregate_boundaries_remain_s2315(
    projection: str,
    function_name: str,
) -> None:
    semantic_result = analyze(
        _parse(
            _source(
                "postgres.table",
                "table decimal_stats:\n"
                "    from orders\n"
                "    select:\n"
                f"        {projection}\n",
            )
        )
    )

    assert _errors(semantic_result) == [
        (
            "PIE-S2315",
            f"Aggregate function {function_name} requires a direct field "
            "argument; expression arguments are deferred",
        )
    ]


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = 1.0 + amount", "PIE-S2105"),
        ("value = amount * tax", "PIE-S2105"),
    ],
)
def test_deferred_decimal_numeric_scalar_boundaries_remain_fail_closed(
    projection: str,
    expected_code: str,
) -> None:
    semantic_result = analyze(
        _parse(
            _source(
                "postgres.table",
                "table decimal_values:\n"
                "    from orders\n"
                "    select:\n"
                f"        {projection}\n",
            )
        )
    )

    assert [code for code, _ in _errors(semantic_result)] == [expected_code]


def test_public_type_surfaces_still_have_no_precision_scale_fields() -> None:
    for type_surface in (ResolvedType, ValueType, TypeRefIR):
        assert {"precision", "scale"}.isdisjoint(
            {field.name for field in fields(type_surface)}
        )


def _source(connector: str, relation: str) -> str:
    return (
        "type Money = Decimal(12, 2) not null\n"
        "shape Order:\n"
        "    amount: Decimal(12, 2) not null\n"
        "    tax: Decimal(12, 2) not null\n"
        "    money: Money not null\n"
        f'source orders: Order is {connector}("orders")\n'
        f"{relation}"
    )


def _parse(source: str) -> Script:
    parse_result = parse_source(source, path="slice5.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    return parse_result.ast


def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    script = _parse(source)
    semantic_result = analyze(script)
    assert _errors(semantic_result) == []

    ir_result = build_ir(script, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return script, semantic_result, ir_result.ir


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _relation_ast(script: Script) -> TableDef | QueryDef:
    relation = script.definitions[-1]
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _projection_expression(script_ir: ScriptIR, name: str) -> ExpressionIR:
    relation = _relation_ir(script_ir)
    projection = next(
        projection for projection in relation.projections if projection.name == name
    )
    return projection.expression


def _shape_field_type_expr(script: Script, field_name: str) -> TypeExpr:
    shape = next(
        definition
        for definition in script.definitions
        if isinstance(definition, ShapeDef)
    )
    field = next(field for field in shape.fields if field.name == field_name)
    return field.type_expr


def _assert_semantic_field(
    field,
    expected_name: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert field.resolved_type.name == expected_name
    assert field.resolved_type.kind is TypeKind.BUILTIN
    assert field.nullability is expected_nullability


def _assert_semantic_value_type(
    value_type: ValueType,
    expected_name: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert value_type.resolved_type.name == expected_name
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.nullability is expected_nullability


def _assert_ir_type_ref(
    type_ref: TypeRefIR,
    *,
    canonical_name: str,
    nullability: NullabilityIR,
) -> None:
    assert type_ref.canonical_name == canonical_name
    assert type_ref.nullability is nullability
    assert not hasattr(type_ref, "precision")
    assert not hasattr(type_ref, "scale")


def _assert_public_text_has_no_precision_scale(text: str) -> None:
    for forbidden in _FORBIDDEN_PUBLIC_OUTPUT_TOKENS:
        assert forbidden not in text, forbidden
