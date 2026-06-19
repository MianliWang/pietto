from __future__ import annotations

import hashlib
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
GRAMMAR_HASH = "d75052cfc4c5de426388cc9d8a34eef607e8023a5e1789f2e497979ea2dde9f6"
GENERATED_HASH = "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1"

SOURCE_PREFIX = (
    "shape Order:\n"
    "    price: Decimal not null\n"
    "    amount: Int not null\n"
    "    score: Float not null\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)


def test_slice3_status_is_decimal_scalar_semantics_only() -> None:
    plan = _normalized_plan()

    for required in (
        "Phase 26 Slice 3 is complete as a narrow Decimal scalar arithmetic "
        "semantics slice",
        "It implements only `Decimal + Decimal -> Decimal` and "
        "`Decimal - Decimal -> Decimal`",
        "Slice 3 changes no IR, SQL backend, CLI, JSON, fixture, or golden behavior",
        "Aggregate expression argument acceptance remains deferred",
    ):
        assert required in plan


@pytest.mark.parametrize(
    "expression_source",
    [
        "price + price",
        "price - price",
    ],
)
def test_decimal_add_subtract_computed_projection_schema_is_locked(
    expression_source: str,
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
    assert field.resolved_type.name == "Decimal"
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert value_type.resolved_type.name == "Decimal"
    assert value_type.nullability is EffectiveNullability.UNKNOWN


def test_decimal_arithmetic_inside_decimal_comparison_shape_is_locked() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table filtered:\n"
            "    from orders\n"
            "    where price - price == price - price\n"
            "    select:\n"
            "        price\n"
        )
    )
    relation = _relation(result)
    assert relation.where_clause is not None
    where_expression = relation.where_clause.expression
    assert isinstance(where_expression, ComparisonExpr)
    assert isinstance(where_expression.left, BinaryExpr)
    assert isinstance(where_expression.right, BinaryExpr)

    left_type = result.model.expression_value_types[where_expression.left]
    right_type = result.model.expression_value_types[where_expression.right]
    where_type = result.model.expression_value_types[where_expression]

    assert result.diagnostics == ()
    assert left_type.resolved_type.name == "Decimal"
    assert left_type.nullability is EffectiveNullability.UNKNOWN
    assert right_type.resolved_type.name == "Decimal"
    assert right_type.nullability is EffectiveNullability.UNKNOWN
    assert where_type.resolved_type.name == "Bool"
    assert where_type.nullability is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize(
    ("expression_source", "message"),
    [
        (
            "price * price",
            "Invalid operands for operator *: expected numeric operands",
        ),
        (
            "price * amount",
            "Invalid operands for operator *: expected numeric operands",
        ),
        (
            "amount * price",
            "Invalid operands for operator *: expected numeric operands",
        ),
        (
            "score + price",
            "Invalid operands for operator +: expected numeric operands",
        ),
        (
            "price + score",
            "Invalid operands for operator +: expected numeric operands",
        ),
    ],
)
def test_invalid_decimal_arithmetic_forms_reuse_s2105(
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


def test_unknown_decimal_operand_suppresses_s2105_cascade() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = missing + price\n"
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


def test_decimal_division_remains_deferred_without_diagnostic() -> None:
    result = analyze(
        _parse(
            SOURCE_PREFIX + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = price / price\n"
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


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            "value = sum(price * price)",
            (
                "PIE-S2315",
                "Aggregate function sum requires a direct field argument; "
                "expression arguments are deferred",
            ),
        ),
        (
            "value = count_distinct(lower(status))",
            (
                "PIE-S2315",
                "Aggregate function count_distinct requires a direct field "
                "argument; expression arguments are deferred",
            ),
        ),
        (
            "value = sum(avg(price))",
            ("PIE-S2311", "Nested aggregate avg() is not supported"),
        ),
        (
            "value = sum(price) + 1",
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
            "        total = sum(price)\n"
            "    satisfying:\n"
            "        sum(price + price) > 1000\n"
        )
    )

    assert _errors(result) == [
        (
            "PIE-S2308",
            "Aggregate sum() is not allowed in satisfying clause; "
            "use it only as a direct aliased select projection",
        )
    ]


def test_phase26_slice3_changes_no_grammar_or_generated_antlr() -> None:
    assert _sha256(REPO_ROOT / "grammar/Pietto.g4") == GRAMMAR_HASH
    generated = tuple(
        path
        for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
        if path.is_file()
    )
    assert _aggregate_sha256(generated) == GENERATED_HASH


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate_sha256(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
