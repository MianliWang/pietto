from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from pietto.ast_nodes import (
    BinaryExpr,
    Expression,
    LiteralExpr,
    QueryDef,
    Script,
    ShapeDef,
    TableDef,
)
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    FieldRefIR,
    NullabilityIR,
    ProjectionIR,
    RelationIR,
    ScriptIR,
    TypeKindIR,
    UnaryIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
SEMANTIC_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
SEMANTIC_ANALYZER_PATH = REPO_ROOT / "src/pietto/semantic/analyzer.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"

BOUNDARY_SHAPE = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    optional_amount: Int nullable\n"
    "    score: Float not null\n"
    "    weight: Float nullable\n"
    "    price: Decimal not null\n"
    "    discount: Decimal nullable\n"
    "    order_date: Date nullable\n"
    "    created_at: Timestamp not null\n"
)


def test_semantic_numeric_promotion_matrix_is_locked() -> None:
    source = (
        _source_prefix("postgres.table") + "table projected:\n"
        "    from orders\n"
        "    select:\n"
        "        int_literal = 1\n"
        "        float_literal = 1.5\n"
        "        plus_amount = +amount\n"
        "        minus_weight = -weight\n"
        "        int_total = amount + tax\n"
        "        int_delta = amount - tax\n"
        "        int_product = amount * tax\n"
        "        mixed_total = amount + score\n"
        "        mixed_product = score * amount\n"
        "        float_total = score + weight\n"
        "        decimal_total = price + discount\n"
        "        decimal_delta = price - discount\n"
        "        modulo = amount % tax\n"
    )
    script = _parse(source)
    relation = _relation_ast(script)

    result = analyze(script)

    assert _error_codes(result) == []
    expected = {
        "int_literal": ("Int", EffectiveNullability.NON_NULL, LiteralExpr),
        "float_literal": ("Float", EffectiveNullability.NON_NULL, LiteralExpr),
        "plus_amount": ("Int", EffectiveNullability.NON_NULL, object),
        "minus_weight": ("Float", EffectiveNullability.NULLABLE, object),
        "int_total": ("Int", EffectiveNullability.UNKNOWN, BinaryExpr),
        "int_delta": ("Int", EffectiveNullability.UNKNOWN, BinaryExpr),
        "int_product": ("Int", EffectiveNullability.UNKNOWN, BinaryExpr),
        "mixed_total": ("Float", EffectiveNullability.UNKNOWN, BinaryExpr),
        "mixed_product": ("Float", EffectiveNullability.UNKNOWN, BinaryExpr),
        "float_total": ("Float", EffectiveNullability.UNKNOWN, BinaryExpr),
        "decimal_total": ("Decimal", EffectiveNullability.UNKNOWN, BinaryExpr),
        "decimal_delta": ("Decimal", EffectiveNullability.UNKNOWN, BinaryExpr),
        "modulo": ("Int", EffectiveNullability.UNKNOWN, BinaryExpr),
    }
    for alias, (
        expected_name,
        expected_nullability,
        expected_expression_type,
    ) in expected.items():
        expression = _select_expression(relation, alias)
        field = result.model.relation_row_schemas[relation].fields[alias]
        value_type = result.model.expression_value_types[expression]

        if expected_expression_type is not object:
            assert isinstance(expression, expected_expression_type)
        _assert_semantic_type(field, expected_name, expected_nullability)
        _assert_semantic_type(value_type, expected_name, expected_nullability)


@pytest.mark.parametrize(
    "projection",
    [
        "value = +price",
        "value = price * discount",
        "value = score + price",
        "value = status + status",
        "value = order_date + amount",
        "value = created_at - amount",
        "value = active + amount",
        "value = score % score",
        "value = amount % score",
    ],
)
def test_decimal_and_unsupported_numeric_boundaries_fail_closed(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            _source_prefix("postgres.table") + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, "value")
    field = result.model.relation_row_schemas[relation].fields["value"]

    assert _error_codes(result) == ["PIE-S2105"]
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert result.model.expression_value_types[expression].kind is (
        ValueTypeKind.UNKNOWN
    )


@pytest.mark.parametrize(
    "projection",
    [
        "value = amount / tax",
        "value = price / discount",
    ],
)
def test_division_remains_deferred_unknown_without_new_diagnostic(
    projection: str,
) -> None:
    result = analyze(
        _parse(
            _source_prefix("postgres.table") + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            f"        {projection}\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, "value")
    field = result.model.relation_row_schemas[relation].fields["value"]
    value_type = result.model.expression_value_types[expression]

    assert result.diagnostics == ()
    assert field.resolved_type.kind is TypeKind.UNKNOWN
    assert field.nullability is EffectiveNullability.UNKNOWN
    assert value_type.kind is ValueTypeKind.UNKNOWN
    assert value_type.resolved_type.kind is TypeKind.UNKNOWN


def test_unknown_operand_suppresses_invalid_operand_cascade() -> None:
    result = analyze(
        _parse(
            _source_prefix("postgres.table") + "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = missing + amount\n"
        )
    )
    relation = _relation(result)
    expression = _select_expression(relation, "value")

    assert _error_codes(result) == ["PIE-S2102"]
    assert "PIE-S2105" not in [diagnostic.code for diagnostic in result.diagnostics]
    assert result.model.expression_value_types[expression].kind is (
        ValueTypeKind.UNKNOWN
    )


def test_scalar_row_schema_and_ir_numeric_decimal_matrix_match() -> None:
    script_ir = _compile(
        _source_prefix("postgres.table") + "table projected:\n"
        "    from orders\n"
        "    select:\n"
        "        plus_amount = +amount\n"
        "        minus_weight = -weight\n"
        "        int_total = amount + tax\n"
        "        mixed_total = amount + score\n"
        "        decimal_total = price + discount\n"
        "        decimal_delta = price - discount\n"
        "        modulo = amount % tax\n"
    )
    projections = _projections(_relation_ir(script_ir))

    unary_expectations = {
        "plus_amount": ("+", "Int", NullabilityIR.NON_NULL),
        "minus_weight": ("-", "Float", NullabilityIR.NULLABLE),
    }
    for alias, (
        operator,
        expected_name,
        expected_nullability,
    ) in unary_expectations.items():
        expression = projections[alias].expression
        assert isinstance(expression, UnaryIR)
        assert expression.operator == operator
        assert isinstance(expression.operand, FieldRefIR)
        _assert_ir_type(expression, expected_name, expected_nullability)

    binary_expectations = {
        "int_total": ("+", "Int"),
        "mixed_total": ("+", "Float"),
        "decimal_total": ("+", "Decimal"),
        "decimal_delta": ("-", "Decimal"),
        "modulo": ("%", "Int"),
    }
    for alias, (operator, expected_name) in binary_expectations.items():
        expression = projections[alias].expression
        assert isinstance(expression, BinaryIR)
        assert expression.operator == operator
        _assert_ir_type(expression, expected_name, NullabilityIR.UNKNOWN)


def test_postgres_and_private_mysql_sql_for_accepted_expressions_is_stable() -> None:
    scalar_projection = (
        "int_total = amount + tax\n"
        "        mixed_total = amount + score\n"
        "        decimal_total = price + discount\n"
        "        decimal_delta = price - discount\n"
        "        modulo = amount % tax"
    )
    aggregate_projection = (
        "literal_total = sum(amount + 1)\n"
        "        literal_average = avg(score * 2)\n"
        "        decimal_total = sum(price + discount)\n"
        "        decimal_average = avg(price - discount)"
    )
    cases: tuple[tuple[str, Callable[[ScriptIR], SqlResult], tuple[str, ...]], ...] = (
        (
            "postgres.table",
            emit_postgres_sql,
            (
                '"amount" + "tax" AS "int_total"',
                '"amount" + "score" AS "mixed_total"',
                '"price" + "discount" AS "decimal_total"',
                '"price" - "discount" AS "decimal_delta"',
                '"amount" % "tax" AS "modulo"',
                'SUM(("amount" + 1)) AS "literal_total"',
                'AVG(("score" * 2)) AS "literal_average"',
                'SUM(("price" + "discount")) AS "decimal_total"',
                'AVG(("price" - "discount")) AS "decimal_average"',
            ),
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            (
                "`amount` + `tax` AS `int_total`",
                "`amount` + `score` AS `mixed_total`",
                "`price` + `discount` AS `decimal_total`",
                "`price` - `discount` AS `decimal_delta`",
                "`amount` % `tax` AS `modulo`",
                "SUM((`amount` + 1)) AS `literal_total`",
                "AVG((`score` * 2)) AS `literal_average`",
                "SUM((`price` + `discount`)) AS `decimal_total`",
                "AVG((`price` - `discount`)) AS `decimal_average`",
            ),
        ),
    )

    for connector, emitter, expected_fragments in cases:
        scalar_result = emitter(
            _compile(_projected_source(connector, scalar_projection))
        )
        aggregate_result = emitter(
            _compile(_aggregate_source(connector, aggregate_projection))
        )

        assert scalar_result.diagnostics == ()
        assert aggregate_result.diagnostics == ()
        sql = "\n".join(
            artifact.sql
            for result in (scalar_result, aggregate_result)
            for artifact in result.artifacts
        )
        for fragment in expected_fragments:
            assert fragment in sql


def test_sum_avg_numeric_expression_boundaries_are_locked() -> None:
    result = analyze(
        _parse(
            _aggregate_source(
                "postgres.table",
                "total = sum(amount + tax)\n"
                "        weighted = avg(score * weight)\n"
                "        decimal_total = sum(price + discount)\n"
                "        decimal_average = avg(price - discount)\n"
                "        literal_total = sum(amount + 1)\n"
                "        literal_average = avg(score * 2)",
            )
        )
    )
    relation = _relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _error_codes(result) == []
    for name, expected_type in (
        ("total", "Int"),
        ("weighted", "Float"),
        ("decimal_total", "Decimal"),
        ("decimal_average", "Decimal"),
        ("literal_total", "Int"),
        ("literal_average", "Float"),
    ):
        _assert_semantic_type(
            schema.fields[name],
            expected_type,
            EffectiveNullability.NULLABLE,
        )

    script_ir = _compile(
        _aggregate_source(
            "postgres.table",
            "total = sum(amount + tax)\n"
            "        decimal_average = avg(price - discount)\n"
            "        literal_total = sum(amount + 1)",
        )
    )
    projections = _projections(_relation_ir(script_ir))
    for name in ("total", "decimal_average", "literal_total"):
        aggregate = projections[name].expression
        assert isinstance(aggregate, AggregateCallIR)
        assert isinstance(aggregate.arguments[0], BinaryIR)


@pytest.mark.parametrize(
    "projection",
    [
        "value = sum(1)",
        "value = avg(1)",
        "value = sum(1 + 2)",
        "value = avg(1.5 * 2)",
        "value = sum(price + 1)",
        "value = sum(price + score)",
        "value = sum(price * discount)",
        "value = sum(amount / tax)",
        "value = sum(amount % tax)",
        "value = count(1)",
        "value = min(amount + 1)",
        "value = max(score * 2)",
    ],
)
def test_unsupported_sum_avg_literal_and_expression_boundaries_fail_closed(
    projection: str,
) -> None:
    script = _parse(_aggregate_source("postgres.table", projection))
    semantic_result = analyze(script)

    assert _error_codes(semantic_result) == ["PIE-S2315"]
    ir_result = build_ir(script, semantic_result.model)
    if ir_result.ir is not None:
        sql_result = emit_postgres_sql(ir_result.ir)
        assert sql_result.artifacts == ()


def test_decimal_precision_scale_literal_and_cast_boundaries_remain_absent() -> None:
    source = (
        "shape PricedOrder:\n"
        "    price: Decimal(12, 2) not null\n"
        'source orders: PricedOrder is postgres.table("orders")\n'
        "table projected:\n"
        "    from orders\n"
        "    select:\n"
        "        price\n"
    )
    script = _parse(source)
    shape = script.definitions[0]
    assert isinstance(shape, ShapeDef)
    type_expr = shape.fields[0].type_expr
    assert type_expr.name == "Decimal"
    assert [argument.name for argument in type_expr.arguments] == [None, None]
    assert [
        getattr(argument.value, "value", None) for argument in type_expr.arguments
    ] == [12, 2]

    semantic_result = analyze(script)
    schema = next(iter(semantic_result.model.source_row_schemas.values()))
    semantic_field = schema.fields["price"]
    _assert_semantic_type(
        semantic_field,
        "Decimal",
        EffectiveNullability.NON_NULL,
    )

    script_ir = _compile(source)
    ir_field = _relation_ir(script_ir).row_schema.fields[0]
    _assert_ir_type(ir_field.type_ref, "Decimal", NullabilityIR.NON_NULL)

    for semantic_object in (
        semantic_field.resolved_type,
        semantic_result.model.expression_value_types[
            _select_expression(
                _relation(semantic_result),
                "price",
            )
        ],
    ):
        assert not hasattr(semantic_object, "precision")
        assert not hasattr(semantic_object, "scale")
    assert not hasattr(ir_field.type_ref, "precision")
    assert not hasattr(ir_field.type_ref, "scale")

    semantic_model = _read(SEMANTIC_MODEL_PATH)
    ir_model = _read(IR_MODEL_PATH)
    analyzer = _read(SEMANTIC_ANALYZER_PATH)
    expressions = _read(SEMANTIC_EXPRESSIONS_PATH)
    aggregates = _read(AGGREGATES_PATH)
    postgres = _read(POSTGRES_EXPRESSIONS_PATH)
    mysql = _read(MYSQL_EXPRESSIONS_PATH)

    for required in (
        "class DecimalPrecisionScale:",
        "precision: int",
        "scale: int",
        "decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale]",
    ):
        assert required in semantic_model

    for forbidden in ("precision", "scale"):
        assert forbidden not in _class_body(semantic_model, "class ResolvedType:")
        assert forbidden not in _class_body(semantic_model, "class ValueType:")
        assert forbidden not in _class_body(ir_model, "class TypeRefIR:")

    assert "type_expr.arguments" not in _function_body(analyzer, "def _resolve_type(")
    decimal_validator = _function_body(
        analyzer,
        "def _decimal_precision_scale_fact(",
    )
    assert 'if type_expr.name != "Decimal":' in decimal_validator
    assert "arguments = type_expr.arguments" in decimal_validator
    assert "_DECIMAL_PRECISION_MAX = 38" in analyzer
    assert "PIE-S2004" in analyzer
    assert 'if expression.operator == "/":' in expressions
    assert "return _UNKNOWN_VALUE_TYPE" in expressions
    assert "Decimal" not in _function_body(expressions, "def _is_numeric(")
    assert "Decimal" in aggregates

    for renderer_source in (postgres, mysql):
        for forbidden in ("DECIMAL(", "NUMERIC(", "precision", "scale"):
            assert forbidden not in renderer_source


def _source_prefix(connector: str) -> str:
    return BOUNDARY_SHAPE + f'source orders: Order is {connector}("orders")\n'


def _projected_source(connector: str, projections: str) -> str:
    return (
        _source_prefix(connector) + "table projected:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projections}\n"
    )


def _aggregate_source(connector: str, projections: str) -> str:
    return (
        _source_prefix(connector) + "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projections}\n"
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _compile(source: str) -> ScriptIR:
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation(result: SemanticResult) -> TableDef | QueryDef:
    relation = next(iter(result.model.relation_row_schemas))
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


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


def _projections(relation: RelationIR) -> dict[str, ProjectionIR]:
    return {str(projection.name): projection for projection in relation.projections}


def _select_expression(relation: TableDef | QueryDef, alias: str) -> Expression:
    for item in relation.select_items:
        if item.alias == alias:
            return item.expression
        if item.alias is None and getattr(item.expression, "name", None) == alias:
            return item.expression
    raise AssertionError(f"Missing select item: {alias}")


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_semantic_type(
    value_type: object,
    expected_name: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(value_type, "resolved_type").name == expected_name
    assert getattr(value_type, "nullability") is expected_nullability


def _assert_ir_type(
    value_type: object,
    expected_name: str,
    expected_nullability: NullabilityIR,
) -> None:
    if hasattr(value_type, "value_type"):
        value_type = getattr(value_type, "value_type")
    assert getattr(value_type, "canonical_kind") is TypeKindIR.BUILTIN
    assert getattr(value_type, "canonical_name") == expected_name
    assert getattr(value_type, "nullability") is expected_nullability


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _function_body(source: str, marker: str) -> str:
    start = source.index(marker)
    rest = source[start:]
    next_def = rest.find("\n\ndef ", len(marker))
    return rest if next_def == -1 else rest[:next_def]


def _class_body(source: str, marker: str) -> str:
    start = source.index(marker)
    rest = source[start:]
    next_class = rest.find("\n\n@dataclass", len(marker))
    return rest if next_class == -1 else rest[:next_class]
