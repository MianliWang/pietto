from __future__ import annotations

from pathlib import Path

import pytest

from pietto.ast_nodes import (
    BinaryExpr,
    ComparisonExpr,
    Expression,
    Script,
    SelectItem,
    TableDef,
)
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
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float nullable\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    order_date: Date nullable\n"
    "    price: Decimal not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_slice2_status_is_numeric_scalar_audit_only() -> None:
    plan = _normalized_plan()

    for required in (
        "Phase 26 Slice 2 is complete as numeric scalar expression semantics "
        "audit and status work only",
        "It locks the already-implemented Int/Float `+`, `-`, and `*` "
        "ordinary scalar expression semantics",
        "Slice 2 adds no production behavior",
        "Decimal arithmetic",
        "aggregate expression argument acceptance",
    ):
        assert required in plan


@pytest.mark.parametrize(
    ("expression_source", "expected_type"),
    [
        ("amount + tax", "Int"),
        ("amount - tax", "Int"),
        ("amount * tax", "Int"),
        ("score + weight", "Float"),
        ("score - weight", "Float"),
        ("score * weight", "Float"),
        ("amount + score", "Float"),
        ("score + amount", "Float"),
        ("amount * score", "Float"),
        ("score * amount", "Float"),
    ],
)
def test_int_float_binary_arithmetic_computed_projection_schema_is_locked(
    expression_source: str,
    expected_type: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            f"        value = {expression_source}\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, 0)
    field = result.model.relation_row_schemas[relation].fields["value"]
    value_type = result.model.expression_value_types[expression]

    assert isinstance(expression, BinaryExpr)
    assert result.diagnostics == ()
    assert field.resolved_type.name == expected_type
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert value_type.resolved_type.name == expected_type
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_numeric_arithmetic_inside_where_comparison_is_locked() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table filtered:\n"
            "    from orders\n"
            "    where amount + tax > 100\n"
            "    select:\n"
            "        amount\n"
        )
    )
    relation = _relation(result)
    assert relation.where_clause is not None
    where_expression = relation.where_clause.expression
    assert isinstance(where_expression, ComparisonExpr)
    arithmetic = where_expression.left
    assert isinstance(arithmetic, BinaryExpr)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[arithmetic].resolved_type.name == "Int"
    assert result.model.expression_value_types[arithmetic].nullability is (
        EffectiveNullability.UNKNOWN
    )
    assert result.model.expression_value_types[where_expression].resolved_type.name == (
        "Bool"
    )


@pytest.mark.parametrize(
    ("expression_source", "expected_type", "expected_nullability"),
    [
        ("+amount", "Int", EffectiveNullability.NON_NULL),
        ("-amount", "Int", EffectiveNullability.NON_NULL),
        ("+weight", "Float", EffectiveNullability.NULLABLE),
        ("-weight", "Float", EffectiveNullability.NULLABLE),
    ],
)
def test_unary_numeric_semantics_remain_unchanged(
    expression_source: str,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            f"        value = {expression_source}\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, 0)
    field = result.model.relation_row_schemas[relation].fields["value"]
    value_type = result.model.expression_value_types[expression]

    assert result.diagnostics == ()
    assert field.resolved_type.name == expected_type
    assert field.nullability is expected_nullability
    assert value_type.resolved_type.name == expected_type
    assert value_type.nullability is expected_nullability


@pytest.mark.parametrize(
    ("expression_source", "message"),
    [
        (
            "status + amount",
            "Invalid operands for operator +: expected numeric operands",
        ),
        (
            "active * amount",
            "Invalid operands for operator *: expected numeric operands",
        ),
        (
            "order_date - amount",
            "Invalid operands for operator -: expected numeric operands",
        ),
    ],
)
def test_invalid_known_numeric_operands_reuse_s2105(
    expression_source: str,
    message: str,
) -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            f"        value = {expression_source}\n"
        )
    )
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == [("PIE-S2105", message)]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


def test_unknown_numeric_operand_suppresses_s2105_cascade() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = missing + amount\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, 0)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == [("PIE-S2102", "Unknown field: missing")]
    assert "PIE-S2105" not in [diagnostic.code for diagnostic in result.diagnostics]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_division_remains_deferred_without_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = amount / tax\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, 0)
    field = result.model.relation_row_schemas[relation].fields["value"]
    value_type = result.model.expression_value_types[expression]

    assert result.diagnostics == ()
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert value_type.kind is ValueTypeKind.UNKNOWN
    assert value_type.resolved_type.kind is TypeKind.UNKNOWN


def test_decimal_multiplication_remains_deferred_to_later_slice() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = price * price\n"
        )
    )
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _errors(result) == [
        ("PIE-S2105", "Invalid operands for operator *: expected numeric operands")
    ]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = sum(1 + 2)",
            (
                "PIE-S2315",
                "Aggregate function sum requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
        (
            "value = count_distinct(len(status))",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
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
def test_aggregate_expression_boundaries_remain_deferred(
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
            "        total = sum(amount)\n"
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


def _normalized_plan() -> str:
    return " ".join(PLAN_PATH.read_text(encoding="utf-8").split())


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(result: SemanticResult) -> TableDef:
    relation = next(
        definition
        for definition in result.model.relation_symbols.values()
        if isinstance(definition, TableDef)
    )
    return relation


def _select_expression(relation: TableDef, index: int) -> Expression:
    item = relation.select_items[index]
    assert isinstance(item, SelectItem)
    return item.expression


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
