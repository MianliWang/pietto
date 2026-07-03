from __future__ import annotations

import json
from pathlib import Path
from typing import cast

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

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-26-aggregate-expression-arguments-numeric-foundation.md"
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


def test_slice4_status_is_semantic_only_with_fail_closed_guard() -> None:
    plan = _normalized_plan()

    for required in (
        "Phase 26 Slice 4 is complete as a semantic-only aggregate "
        "expression argument slice",
        "It admits only field-only numeric scalar expression arguments for "
        "direct aliased `sum` and `avg` projections",
        "Literal-containing aggregate arguments such as `sum(amount + 1)` "
        "and `avg(score * 2)` remain deferred through `PIE-S2315`",
        "Slice 4 intentionally adds no IR, SQL backend, CLI, JSON, fixture, "
        "or golden behavior",
        "The focused fail-closed guard proves that semantically accepted "
        "`sum(amount + tax)` does not emit SQL artifacts before the later "
        "IR/SQL slices",
    ):
        assert required in plan


@pytest.mark.parametrize(
    (
        "projection",
        "expected_argument_type",
        "expected_argument_nullability",
        "expected_result_type",
    ),
    [
        ("value = sum(amount + tax)", "Int", EffectiveNullability.UNKNOWN, "Int"),
        ("value = sum(+amount)", "Int", EffectiveNullability.NON_NULL, "Int"),
        ("value = sum(-amount)", "Int", EffectiveNullability.NON_NULL, "Int"),
        ("value = sum(amount * tax)", "Int", EffectiveNullability.UNKNOWN, "Int"),
        ("value = avg(score * score)", "Float", EffectiveNullability.UNKNOWN, "Float"),
        ("value = avg(score + weight)", "Float", EffectiveNullability.UNKNOWN, "Float"),
        ("value = avg(score * weight)", "Float", EffectiveNullability.UNKNOWN, "Float"),
        (
            "value = sum(price + price)",
            "Decimal",
            EffectiveNullability.UNKNOWN,
            "Decimal",
        ),
        (
            "value = sum(price + discount)",
            "Decimal",
            EffectiveNullability.UNKNOWN,
            "Decimal",
        ),
        (
            "value = sum(price + amount)",
            "Decimal",
            EffectiveNullability.UNKNOWN,
            "Decimal",
        ),
        (
            "value = avg(price - discount)",
            "Decimal",
            EffectiveNullability.UNKNOWN,
            "Decimal",
        ),
    ],
)
def test_sum_avg_field_only_expression_arguments_are_semantically_accepted(
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


def test_grouped_sum_avg_expression_arguments_are_semantically_accepted() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount + tax)\n"
            "        average = avg(score * weight)\n"
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    assert list(schema.fields) == ["status", "total", "average"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["average"], "Float", EffectiveNullability.NULLABLE)


def test_qualified_field_leaves_are_semantically_accepted() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        total = sum(orders.amount + orders.tax)\n"
            "        average = avg(+orders.score)\n"
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _errors(result) == []
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["average"], "Float", EffectiveNullability.NULLABLE)


@pytest.mark.parametrize(
    ("projection", "function_name"),
    [
        ("value = sum(1 + 2)", "sum"),
        ("value = avg(1)", "avg"),
        ("value = sum(amount / tax)", "sum"),
        ("value = sum(amount % tax)", "sum"),
        ("value = sum(price * discount)", "sum"),
        ("value = avg(price * price)", "avg"),
        ("value = sum(price + score)", "sum"),
        ("value = count(1)", "count"),
        ("value = count_distinct(len(status))", "count_distinct"),
        ("value = min(amount + tax)", "min"),
        ("value = max(score * weight)", "max"),
    ],
)
def test_unsupported_aggregate_expression_arguments_use_s2315(
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
    ("projection", "function_name", "actual_type"),
    [
        ("value = sum(lower(status))", "sum", "Text"),
        ("value = avg(active)", "avg", "Bool"),
    ],
)
def test_known_nonnumeric_sum_avg_arguments_use_s2314(
    projection: str,
    function_name: str,
    actual_type: str,
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
            "PIE-S2314",
            f"Aggregate function {function_name} expects Int, Float, or "
            f"Decimal field argument, got {actual_type}",
        )
    ]


def test_unknown_field_leaf_suppresses_aggregate_cascade() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        value = sum(missing + amount)\n"
        )
    )
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == [("PIE-S2102", "Unknown field: missing")]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_projection_alias_is_not_an_aggregate_argument_leaf() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    select:\n"
            "        subtotal = amount + tax\n"
            "        value = sum(subtotal + tax)\n"
        )
    )
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == [("PIE-S2102", "Unknown field: subtotal")]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
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
def test_nested_aggregate_and_composition_boundaries_remain_unchanged(
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


def test_direct_aggregate_inside_satisfying_still_uses_s2308() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table aggregate_stats:\n"
            "    from orders\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount + tax)\n"
            "    satisfying:\n"
            "        sum(amount + tax) > 1000\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate sum() is not allowed in satisfying clause; "
            "use it only as a direct aliased select projection",
        )
    ]


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        (
            "postgres",
            "postgres.table",
            'SELECT\n    SUM(("amount" + "tax")) AS "total"\nFROM "orders"',
        ),
        (
            "mysql",
            "mysql.table",
            "SELECT\n    SUM((`amount` + `tax`)) AS `total`\nFROM `orders`",
        ),
    ],
)
def test_emit_sql_for_aggregate_expression_argument_succeeds_after_sql_slice(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    source = (
        SOURCE_PREFIX.replace("postgres.table", connector) + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        "        total = sum(amount + tax)\n"
    )
    semantic_result = analyze(_parse(source))
    path = _write(tmp_path, f"aggregate-expression-{dialect}.pietto", source)
    output = tmp_path / f"{dialect}.sql"

    assert _errors(semantic_result) == []
    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format=json",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    result = cast(dict[str, object], json.loads(captured.out))
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert captured.err == ""
    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["output"] == {"path": str(output), "written": True}
    assert artifacts == [
        {
            "kind": "relation",
            "name": "aggregate_stats",
            "sql": expected_sql,
        }
    ]
    assert output.read_text(encoding="utf-8") == expected_sql + "\n"


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


def _normalized_plan() -> str:
    return " ".join(PLAN_PATH.read_text(encoding="utf-8").split())
