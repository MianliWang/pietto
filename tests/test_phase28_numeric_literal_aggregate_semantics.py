from __future__ import annotations

from pathlib import Path

import pytest

import pietto.cli as cli
from pietto.ast_nodes import CallExpr, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)

SOURCE_PREFIX = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float nullable\n"
    "    price: Decimal not null\n"
    "    discount: Decimal not null\n"
    "    active: Bool not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


@pytest.mark.parametrize(
    (
        "projection",
        "expected_argument_type",
        "expected_argument_nullability",
        "expected_result_type",
    ),
    [
        ("value = sum(amount + 1)", "Int", EffectiveNullability.UNKNOWN, "Int"),
        ("value = sum(1 + amount)", "Int", EffectiveNullability.UNKNOWN, "Int"),
        ("value = sum(amount - 1)", "Int", EffectiveNullability.UNKNOWN, "Int"),
        ("value = sum(amount * 2)", "Int", EffectiveNullability.UNKNOWN, "Int"),
        ("value = sum(score + 1)", "Float", EffectiveNullability.UNKNOWN, "Float"),
        ("value = sum(amount + 1.5)", "Float", EffectiveNullability.UNKNOWN, "Float"),
        ("value = avg(amount + 1)", "Int", EffectiveNullability.UNKNOWN, "Float"),
        ("value = avg(score * 2)", "Float", EffectiveNullability.UNKNOWN, "Float"),
        ("value = avg(score + 1.5)", "Float", EffectiveNullability.UNKNOWN, "Float"),
    ],
)
def test_sum_avg_numeric_literal_expression_arguments_are_semantically_accepted(
    projection: str,
    expected_argument_type: str,
    expected_argument_nullability: EffectiveNullability,
    expected_result_type: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, 0)
    assert isinstance(expression, CallExpr)
    argument = expression.arguments[0]
    schema = result.model.relation_row_schemas[relation]
    field = schema.fields["value"]
    expression_type = result.model.expression_value_types[expression]
    argument_type = result.model.expression_value_types[argument]

    assert _errors(result) == []
    _assert_field(field, expected_result_type, EffectiveNullability.NULLABLE)
    _assert_value_type(
        expression_type,
        expected_result_type,
        EffectiveNullability.NULLABLE,
    )
    _assert_value_type(
        argument_type,
        expected_argument_type,
        expected_argument_nullability,
    )


def test_qualified_field_and_unary_leaves_are_semantically_accepted() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = sum(+orders.amount + 1)\n"
            "        average = avg(-orders.score + 1.5)\n"
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["average"], "Float", EffectiveNullability.NULLABLE)


def test_grouped_numeric_literal_aggregate_arguments_are_semantically_accepted() -> (
    None
):
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount + 1)\n"
            "        average = avg(score * 2)\n"
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["status", "total", "average"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["average"], "Float", EffectiveNullability.NULLABLE)


def test_phase26_decimal_field_only_expression_arguments_remain_accepted() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = sum(price + discount)\n"
            "        average = avg(price - discount)\n"
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(schema.fields["total"], "Decimal", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["average"], "Decimal", EffectiveNullability.NULLABLE)


def test_cli_check_accepts_numeric_literal_aggregate_arguments(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "numeric-literal-aggregate.pietto",
        SOURCE_PREFIX + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + 1)\n"
        "        average = avg(score * 2)\n",
    )

    assert cli.main(["check", str(path)]) == 0
    captured = capsys.readouterr()

    assert captured.err == ""
    assert captured.out == f"OK: {path}\n"


@pytest.mark.parametrize(
    ("projection", "function_name"),
    [
        ("value = sum(1)", "sum"),
        ("value = avg(1)", "avg"),
        ("value = sum(1 + 2)", "sum"),
        ("value = avg(1.5 * 2)", "avg"),
        ('value = sum(amount + "x")', "sum"),
        ("value = sum(amount + true)", "sum"),
        ("value = sum(amount + null)", "sum"),
        ("value = sum(amount / tax)", "sum"),
        ("value = sum(amount % tax)", "sum"),
        ("value = sum(amount + len(status))", "sum"),
        ("value = count(1)", "count"),
        ("value = min(amount + 1)", "min"),
        ("value = max(score * 2)", "max"),
        ("value = count_distinct(len(status))", "count_distinct"),
    ],
)
def test_unsupported_literal_and_expression_shapes_still_use_s2315(
    projection: str,
    function_name: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2315",
            f"Aggregate function {function_name} requires a direct field argument; "
            "expression arguments are deferred",
        )
    ]


@pytest.mark.parametrize(
    "projection",
    [
        "value = sum(price * discount)",
        "value = sum(price + 1)",
        "value = sum(price + 1.5)",
        "value = sum(price + score)",
        "value = avg(price * price)",
    ],
)
def test_decimal_literal_multiplication_and_mixed_promotion_remain_deferred(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2315",
            "Aggregate function "
            f"{projection.split('(', maxsplit=1)[0].removeprefix('value = ')} "
            "requires a direct field argument; expression arguments are deferred",
        )
    ]


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = sum(lower(status))",
            (
                "PIE-S2314",
                "Aggregate function sum expects Int, Float, or Decimal field "
                "argument, got Text",
            ),
        ),
        (
            "value = sum(avg(amount))",
            ("PIE-S2311", "Nested aggregate avg() is not supported"),
        ),
        (
            "value = sum(amount) + 1",
            (
                "PIE-S2310",
                "Aggregate projection must be a direct aggregate call; "
                "composition around sum() is deferred",
            ),
        ),
    ],
)
def test_existing_primary_aggregate_diagnostics_remain_primary(
    projection: str,
    expected: tuple[str, str],
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )

    assert _errors(result) == [expected]


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(result: SemanticResult) -> TableDef | QueryDef:
    relation = next(iter(result.model.relation_row_schemas))
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _select_expression(relation: TableDef | QueryDef, index: int) -> object:
    return relation.select_items[index].expression


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_field(
    field: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(field, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(field, "resolved_type").name == expected_type
    assert getattr(field, "nullability") is expected_nullability


def _assert_value_type(
    value_type: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "kind") is not ValueTypeKind.UNKNOWN
    assert getattr(value_type, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(value_type, "resolved_type").name == expected_type
    assert getattr(value_type, "nullability") is expected_nullability


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
