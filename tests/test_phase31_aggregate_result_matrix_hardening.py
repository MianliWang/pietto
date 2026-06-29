from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

import pytest

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    CallIR,
    ExpressionIR,
    FieldRefIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    SemanticResult,
    TypeKind,
    ValueType,
    ValueTypeKind,
    analyze,
)
from pietto.semantic.aggregates import semantic_aggregate_result_value_type
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-31-v02-hardening-and-stable-completion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/v02-hardening-and-stable-completion-v1.md"
PHASE36_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
)
PHASE36_ENUM_SPEC_PATH = REPO_ROOT / "docs/spec/enum-support-resolution-v1.md"

MATRIX_SHAPE = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    region: Text not null\n"
    "    active: Bool not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    price: Decimal not null\n"
    "    discount: Decimal not null\n"
    "    order_date: Date nullable\n"
    "    created_at: Timestamp not null\n"
    "    raw: Bytes not null\n"
    "    payload: Json not null\n"
    "    customer_id: UUID not null\n"
    "    anything: Any nullable\n"
)

NO_GROUP_PROJECTIONS = (
    "        total = count()\n"
    "        count_status = count(status)\n"
    "        count_raw = count(raw)\n"
    "        count_payload = count(payload)\n"
    "        count_customer = count(customer_id)\n"
    "        unique_status = count_distinct(status)\n"
    "        unique_customer = count_distinct(customer_id)\n"
    "        unique_normalized = count_distinct(lower(trim(status)))\n"
    "        total_amount = sum(amount)\n"
    "        total_score = sum(score)\n"
    "        total_price = sum(price)\n"
    "        average_amount = avg(amount)\n"
    "        average_score = avg(score)\n"
    "        average_price = avg(price)\n"
    "        smallest_amount = min(amount)\n"
    "        smallest_score = min(score)\n"
    "        smallest_price = min(price)\n"
    "        first_order_date = min(order_date)\n"
    "        first_created_at = min(created_at)\n"
    "        largest_amount = max(amount)\n"
    "        largest_score = max(score)\n"
    "        largest_price = max(price)\n"
    "        latest_order_date = max(order_date)\n"
    "        latest_created_at = max(created_at)\n"
    "        total_expr = sum(amount + tax)\n"
    "        average_expr = avg(score * weight)\n"
    "        decimal_total_expr = sum(price + discount)\n"
    "        decimal_average_expr = avg(price - discount)\n"
)

NO_GROUP_ROW_SCHEMA = (
    ("total", "Int", EffectiveNullability.NON_NULL),
    ("count_status", "Int", EffectiveNullability.NON_NULL),
    ("count_raw", "Int", EffectiveNullability.NON_NULL),
    ("count_payload", "Int", EffectiveNullability.NON_NULL),
    ("count_customer", "Int", EffectiveNullability.NON_NULL),
    ("unique_status", "Int", EffectiveNullability.NON_NULL),
    ("unique_customer", "Int", EffectiveNullability.NON_NULL),
    ("unique_normalized", "Int", EffectiveNullability.NON_NULL),
    ("total_amount", "Int", EffectiveNullability.NULLABLE),
    ("total_score", "Float", EffectiveNullability.NULLABLE),
    ("total_price", "Decimal", EffectiveNullability.NULLABLE),
    ("average_amount", "Float", EffectiveNullability.NULLABLE),
    ("average_score", "Float", EffectiveNullability.NULLABLE),
    ("average_price", "Decimal", EffectiveNullability.NULLABLE),
    ("smallest_amount", "Int", EffectiveNullability.NULLABLE),
    ("smallest_score", "Float", EffectiveNullability.NULLABLE),
    ("smallest_price", "Decimal", EffectiveNullability.NULLABLE),
    ("first_order_date", "Date", EffectiveNullability.NULLABLE),
    ("first_created_at", "Timestamp", EffectiveNullability.NULLABLE),
    ("largest_amount", "Int", EffectiveNullability.NULLABLE),
    ("largest_score", "Float", EffectiveNullability.NULLABLE),
    ("largest_price", "Decimal", EffectiveNullability.NULLABLE),
    ("latest_order_date", "Date", EffectiveNullability.NULLABLE),
    ("latest_created_at", "Timestamp", EffectiveNullability.NULLABLE),
    ("total_expr", "Int", EffectiveNullability.NULLABLE),
    ("average_expr", "Float", EffectiveNullability.NULLABLE),
    ("decimal_total_expr", "Decimal", EffectiveNullability.NULLABLE),
    ("decimal_average_expr", "Decimal", EffectiveNullability.NULLABLE),
)

GROUPED_PROJECTIONS = (
    "        status\n"
    "        total = count()\n"
    "        count_customer = count(customer_id)\n"
    "        unique_customer = count_distinct(customer_id)\n"
    "        total_amount = sum(amount)\n"
    "        average_score = avg(score)\n"
    "        smallest_price = min(price)\n"
    "        latest_created_at = max(created_at)\n"
    "        total_expr = sum(amount + tax)\n"
    "        decimal_average_expr = avg(price - discount)\n"
)

GROUPED_ROW_SCHEMA = (
    ("status", "Text", EffectiveNullability.NON_NULL),
    ("total", "Int", EffectiveNullability.NON_NULL),
    ("count_customer", "Int", EffectiveNullability.NON_NULL),
    ("unique_customer", "Int", EffectiveNullability.NON_NULL),
    ("total_amount", "Int", EffectiveNullability.NULLABLE),
    ("average_score", "Float", EffectiveNullability.NULLABLE),
    ("smallest_price", "Decimal", EffectiveNullability.NULLABLE),
    ("latest_created_at", "Timestamp", EffectiveNullability.NULLABLE),
    ("total_expr", "Int", EffectiveNullability.NULLABLE),
    ("decimal_average_expr", "Decimal", EffectiveNullability.NULLABLE),
)


def test_phase31_slice2_plan_and_spec_lock_tests_static_audit_scope() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    phase36 = f"{_normalized(PHASE36_PLAN_PATH)} {_normalized(PHASE36_ENUM_SPEC_PATH)}"
    combined = f"{plan} {spec}"

    for required in (
        "Phase 31 Slice 2 is complete as aggregate result matrix hardening, "
        "tests, static audit, and status work only",
        "Slice 8 is complete",
        "Phase 29 aggregate freeze remains active",
        "Phase 30 type-system contracts are carried forward",
        "min(Decimal) and max(Decimal) are included only as current accepted "
        "behavior with existing semantic, IR, and SQL test evidence",
        "Bytes and Json are recorded only as existing count(field) concrete "
        "builtin non-Any behavior",
        "does not imply broader Bytes or Json expression, comparison, SQL, or "
        "type-system support",
        "count(Enum field) remains a documented risk",
        "Phase 31 Slice 5 is complete as UUID / Enum readiness decision, "
        "tests, static audit, and status work only",
        "Phase 31 Slice 6 is complete as Diagnostic / CLI / JSON stability "
        "hardening, tests, static audit, status, and docs work only",
        "UUID remains limited/frozen readiness",
        "Enum remains metadata readiness only",
        "semantic/IR acceptance with PostgreSQL/private MySQL fail-closed output",
        "requires separate explicit approval before any behavior fix",
        "Accepted locked matrix rows have concrete expected nullability",
        "Unsupported or invalid forms may preserve unknown schema/value facts "
        "through existing diagnostics",
    ):
        assert required in combined

    for forbidden in (
        "aggregate expansion",
        "behavior fix",
        "v0.2 completion declaration in Slice 2",
        "Phase 32 implementation",
        "Slice 3 work",
        "JSON v2",
        "public MySQL API expansion",
        "diagnostic behavior change",
        "CLI behavior change",
        "JSON v1 schema expansion",
    ):
        assert forbidden in combined

    for required in (
        "Phase 36 Slice 5 selects Option C: narrow semantic fail-closed behavior change",
        "`count(Enum field)` now fails in semantic aggregate validation with existing diagnostic `PIE-S2314`",
        "Enum remains metadata/readiness, not a builtin scalar",
    ):
        assert required in phase36


def test_semantic_aggregate_result_helper_matrix_is_locked() -> None:
    accepted = (
        ("count", None, "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Bool"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Int"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Float"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Decimal"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Text"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Date"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Timestamp"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Bytes"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("Json"), "Int", EffectiveNullability.NON_NULL),
        ("count", _builtin("UUID"), "Int", EffectiveNullability.NON_NULL),
        ("count_distinct", _builtin("Bool"), "Int", EffectiveNullability.NON_NULL),
        ("count_distinct", _builtin("Int"), "Int", EffectiveNullability.NON_NULL),
        ("count_distinct", _builtin("Float"), "Int", EffectiveNullability.NON_NULL),
        (
            "count_distinct",
            _builtin("Decimal"),
            "Int",
            EffectiveNullability.NON_NULL,
        ),
        ("count_distinct", _builtin("Text"), "Int", EffectiveNullability.NON_NULL),
        ("count_distinct", _builtin("Date"), "Int", EffectiveNullability.NON_NULL),
        (
            "count_distinct",
            _builtin("Timestamp"),
            "Int",
            EffectiveNullability.NON_NULL,
        ),
        ("count_distinct", _builtin("UUID"), "Int", EffectiveNullability.NON_NULL),
        ("sum", _builtin("Int"), "Int", EffectiveNullability.NULLABLE),
        ("sum", _builtin("Float"), "Float", EffectiveNullability.NULLABLE),
        ("sum", _builtin("Decimal"), "Decimal", EffectiveNullability.NULLABLE),
        ("avg", _builtin("Int"), "Float", EffectiveNullability.NULLABLE),
        ("avg", _builtin("Float"), "Float", EffectiveNullability.NULLABLE),
        ("avg", _builtin("Decimal"), "Decimal", EffectiveNullability.NULLABLE),
    )
    extrema = (
        ("min", _builtin("Int"), "Int", EffectiveNullability.NULLABLE),
        ("min", _builtin("Float"), "Float", EffectiveNullability.NULLABLE),
        ("min", _builtin("Decimal"), "Decimal", EffectiveNullability.NULLABLE),
        ("min", _builtin("Date"), "Date", EffectiveNullability.NULLABLE),
        ("min", _builtin("Timestamp"), "Timestamp", EffectiveNullability.NULLABLE),
        ("max", _builtin("Int"), "Int", EffectiveNullability.NULLABLE),
        ("max", _builtin("Float"), "Float", EffectiveNullability.NULLABLE),
        ("max", _builtin("Decimal"), "Decimal", EffectiveNullability.NULLABLE),
        ("max", _builtin("Date"), "Date", EffectiveNullability.NULLABLE),
        ("max", _builtin("Timestamp"), "Timestamp", EffectiveNullability.NULLABLE),
    )

    for function, argument, expected_name, expected_nullability in (
        *accepted,
        *extrema,
    ):
        result = semantic_aggregate_result_value_type(function, argument)
        assert result is not None, function
        _assert_value_type(result, expected_name, expected_nullability)

    for function, argument in (
        ("count", _builtin("Any")),
        ("count", _enum("Status")),
        ("count", _unknown()),
        ("count_distinct", None),
        ("count_distinct", _builtin("Bytes")),
        ("count_distinct", _builtin("Json")),
        ("count_distinct", _enum("Status")),
        ("count_distinct", _builtin("Any")),
        ("count_distinct", _unknown()),
        ("sum", None),
        ("sum", _builtin("Text")),
        ("sum", _builtin("Date")),
        ("sum", _builtin("UUID")),
        ("sum", _unknown()),
        ("avg", None),
        ("avg", _builtin("Bool")),
        ("avg", _builtin("Timestamp")),
        ("avg", _unknown()),
        ("min", None),
        ("min", _builtin("Text")),
        ("min", _builtin("Bool")),
        ("min", _builtin("UUID")),
        ("min", _unknown()),
        ("max", None),
        ("max", _builtin("Json")),
        ("max", _builtin("Any")),
        ("max", _unknown()),
        ("median", _builtin("Int")),
    ):
        assert semantic_aggregate_result_value_type(function, argument) is None


def test_no_group_semantic_row_schema_matrix_is_locked() -> None:
    script = _parse(_matrix_source("postgres.table", grouped=False))
    relation = _relation_ast(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _error_codes(result) == []
    assert tuple(schema.fields) == tuple(name for name, _, _ in NO_GROUP_ROW_SCHEMA)
    for name, expected_type, expected_nullability in NO_GROUP_ROW_SCHEMA:
        field = schema.fields[name]
        _assert_value_type(field, expected_type, expected_nullability)
        select_item = next(item for item in relation.select_items if item.alias == name)
        _assert_value_type(
            result.model.expression_value_types[select_item.expression],
            expected_type,
            expected_nullability,
        )


def test_grouped_semantic_row_schema_matrix_is_locked() -> None:
    script = _parse(_matrix_source("postgres.table", grouped=True))
    relation = _relation_ast(script)

    result = analyze(script)
    schema = result.model.relation_row_schemas[relation]

    assert _error_codes(result) == []
    assert tuple(schema.fields) == tuple(name for name, _, _ in GROUPED_ROW_SCHEMA)
    for name, expected_type, expected_nullability in GROUPED_ROW_SCHEMA:
        _assert_value_type(schema.fields[name], expected_type, expected_nullability)


def test_ir_aggregate_call_matrix_matches_semantic_results() -> None:
    for grouped, expected_schema in (
        (False, NO_GROUP_ROW_SCHEMA),
        (True, GROUPED_ROW_SCHEMA),
    ):
        script_ir = _compile(_matrix_source("postgres.table", grouped=grouped))
        relation = _relation_ir(script_ir)
        projections = {
            projection.name: projection for projection in relation.projections
        }

        if grouped:
            assert [key.name for key in relation.group_keys] == ["status"]

        for name, expected_type, expected_nullability in expected_schema:
            projection = projections[name]
            row_field = next(
                field for field in relation.row_schema.fields if field.name == name
            )
            assert row_field.type_ref.canonical_name == expected_type
            assert row_field.nullability is _ir_nullability(expected_nullability)
            if name == "status":
                assert isinstance(projection.expression, FieldRefIR)
                continue
            assert isinstance(projection.expression, AggregateCallIR), name
            assert projection.expression.value_type.canonical_name == expected_type
            assert projection.expression.value_type.nullability is _ir_nullability(
                expected_nullability
            )

        aggregate_expectations = {
            "total": ("count", 0, ()),
            "count_status": ("count", 1, ("status",)),
            "count_raw": ("count", 1, ("raw",)),
            "count_payload": ("count", 1, ("payload",)),
            "count_customer": ("count", 1, ("customer_id",)),
            "unique_status": ("count_distinct", 1, ("status",)),
            "unique_customer": ("count_distinct", 1, ("customer_id",)),
            "unique_normalized": ("count_distinct", 1, ("status",)),
            "total_amount": ("sum", 1, ("amount",)),
            "total_score": ("sum", 1, ("score",)),
            "total_price": ("sum", 1, ("price",)),
            "average_amount": ("avg", 1, ("amount",)),
            "average_score": ("avg", 1, ("score",)),
            "average_price": ("avg", 1, ("price",)),
            "smallest_amount": ("min", 1, ("amount",)),
            "smallest_score": ("min", 1, ("score",)),
            "smallest_price": ("min", 1, ("price",)),
            "first_order_date": ("min", 1, ("order_date",)),
            "first_created_at": ("min", 1, ("created_at",)),
            "largest_amount": ("max", 1, ("amount",)),
            "largest_score": ("max", 1, ("score",)),
            "largest_price": ("max", 1, ("price",)),
            "latest_order_date": ("max", 1, ("order_date",)),
            "latest_created_at": ("max", 1, ("created_at",)),
            "total_expr": ("sum", 1, ("amount", "tax")),
            "average_expr": ("avg", 1, ("score", "weight")),
            "decimal_total_expr": ("sum", 1, ("price", "discount")),
            "decimal_average_expr": ("avg", 1, ("price", "discount")),
        }
        for name, (
            function,
            argument_count,
            field_names,
        ) in aggregate_expectations.items():
            if name not in projections:
                continue
            aggregate = projections[name].expression
            assert isinstance(aggregate, AggregateCallIR), name
            assert aggregate.function == function
            assert len(aggregate.arguments) == argument_count
            assert _field_names(aggregate) == field_names


def test_postgres_and_private_mysql_sql_matrix_is_stable() -> None:
    cases: tuple[tuple[str, Callable[[ScriptIR], SqlResult], tuple[str, ...]], ...] = (
        (
            "postgres.table",
            emit_postgres_sql,
            (
                'COUNT(*) AS "total"',
                'COUNT("raw") AS "count_raw"',
                'COUNT("payload") AS "count_payload"',
                'COUNT("customer_id") AS "count_customer"',
                'COUNT(DISTINCT "customer_id") AS "unique_customer"',
                'COUNT(DISTINCT lower(trim("status"))) AS "unique_normalized"',
                'SUM("price") AS "total_price"',
                'AVG("price") AS "average_price"',
                'MIN("price") AS "smallest_price"',
                'MAX("price") AS "largest_price"',
                'SUM(("amount" + "tax")) AS "total_expr"',
                'AVG(("price" - "discount")) AS "decimal_average_expr"',
            ),
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            (
                "COUNT(*) AS `total`",
                "COUNT(`raw`) AS `count_raw`",
                "COUNT(`payload`) AS `count_payload`",
                "COUNT(`customer_id`) AS `count_customer`",
                "COUNT(DISTINCT `customer_id`) AS `unique_customer`",
                "COUNT(DISTINCT LOWER(TRIM(`status`))) AS `unique_normalized`",
                "SUM(`price`) AS `total_price`",
                "AVG(`price`) AS `average_price`",
                "MIN(`price`) AS `smallest_price`",
                "MAX(`price`) AS `largest_price`",
                "SUM((`amount` + `tax`)) AS `total_expr`",
                "AVG((`price` - `discount`)) AS `decimal_average_expr`",
            ),
        ),
    )

    for connector, emitter, expected_fragments in cases:
        result = emitter(_compile(_matrix_source(connector, grouped=False)))

        assert result.diagnostics == ()
        assert len(result.artifacts) == 1
        sql = result.artifacts[0].sql
        for fragment in expected_fragments:
            assert fragment in sql


def test_count_field_boundary_types_are_locked_with_enum_fail_closed() -> None:
    accepted_cases = (
        ("Bytes", "raw", 'COUNT("raw")', "COUNT(`raw`)"),
        ("Json", "payload", 'COUNT("payload")', "COUNT(`payload`)"),
        ("UUID", "id", 'COUNT("id")', "COUNT(`id`)"),
    )
    for field_type, field_name, postgres_fragment, mysql_fragment in accepted_cases:
        source = _count_field_source(field_type, field_name, "postgres.table")
        mysql_source = _count_field_source(field_type, field_name, "mysql.table")

        postgres_result = emit_postgres_sql(_compile(source))
        mysql_result = emit_mysql_sql(_compile(mysql_source))

        assert postgres_result.diagnostics == ()
        assert mysql_result.diagnostics == ()
        assert postgres_fragment in postgres_result.artifacts[0].sql
        assert mysql_fragment in mysql_result.artifacts[0].sql

    any_result = analyze(
        _parse(_count_field_source("Any", "anything", "postgres.table"))
    )
    assert _error_codes(any_result) == ["PIE-S2314"]

    for connector in ("postgres.table", "mysql.table"):
        script = _parse(_enum_count_source(connector))
        semantic_result = analyze(script)
        ir_result = build_ir(script, semantic_result.model)

        assert _error_codes(semantic_result) == ["PIE-S2314"]
        assert ir_result.ir is not None
        projection = _relation_ir(ir_result.ir).projections[0]
        assert not isinstance(projection.expression, AggregateCallIR)

    combined = f"{_normalized(PHASE36_PLAN_PATH)} {_normalized(PHASE36_ENUM_SPEC_PATH)}"
    assert (
        "Direct `count(Enum field)` must fail closed in semantic aggregate validation using existing diagnostic `PIE-S2314`"
        in combined
    )
    assert (
        "It no longer reaches IR and PostgreSQL/private MySQL SQL backend fail-closed output as `PIE-B1000`"
        in combined
    )


@pytest.mark.parametrize(
    "projection",
    [
        "value = count(amount + tax)",
        "value = count_distinct(len(status))",
        "value = count_distinct(amount + tax)",
        "value = min(amount + tax)",
        "value = max(score * weight)",
        "value = sum(1)",
        "value = avg(1)",
        "value = sum(avg(amount))",
        "value = sum(amount) + 1",
        "value = sum(amount / tax)",
    ],
)
def test_unsupported_aggregate_expansion_boundaries_fail_closed(
    projection: str,
) -> None:
    script = _parse(
        MATRIX_SHAPE
        + 'source orders: Order is postgres.table("orders")\n'
        + "table aggregate_stats:\n"
        + "    from orders\n"
        + "    select:\n"
        + f"        {projection}\n"
    )

    semantic_result = analyze(script)

    assert _error_codes(semantic_result) != []
    ir_result = build_ir(script, semantic_result.model)
    if ir_result.ir is not None:
        sql_result = emit_postgres_sql(ir_result.ir)
        assert sql_result.artifacts == ()


def _matrix_source(connector: str, *, grouped: bool) -> str:
    relation = (
        "table aggregate_stats_by_status:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        f"{GROUPED_PROJECTIONS}"
        if grouped
        else "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"{NO_GROUP_PROJECTIONS}"
    )
    return MATRIX_SHAPE + f'source orders: Order is {connector}("orders")\n' + relation


def _count_field_source(field_type: str, field_name: str, connector: str) -> str:
    return (
        "shape BoundaryOrder:\n"
        f"    {field_name}: {field_type} not null\n"
        f'source orders: BoundaryOrder is {connector}("orders")\n'
        "table counts:\n"
        "    from orders\n"
        "    select:\n"
        f"        value = count({field_name})\n"
    )


def _enum_count_source(connector: str) -> str:
    return (
        "enum Status:\n"
        "    active\n"
        "    paused\n"
        "shape EnumOrder:\n"
        "    status: Status not null\n"
        f'source orders: EnumOrder is {connector}("orders")\n'
        "table status_counts:\n"
        "    from orders\n"
        "    select:\n"
        "        value = count(status)\n"
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


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _assert_value_type(
    value_type: object,
    expected_name: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "resolved_type").name == expected_name
    assert getattr(value_type, "nullability") is expected_nullability


def _builtin(
    name: str,
    nullability: EffectiveNullability = EffectiveNullability.NON_NULL,
) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.BUILTIN),
        nullability=nullability,
    )


def _enum(name: str) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.ENUM),
        nullability=EffectiveNullability.NON_NULL,
    )


def _unknown() -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
        nullability=EffectiveNullability.UNKNOWN,
        kind=ValueTypeKind.UNKNOWN,
    )


def _ir_nullability(nullability: EffectiveNullability) -> NullabilityIR:
    if nullability is EffectiveNullability.NON_NULL:
        return NullabilityIR.NON_NULL
    if nullability is EffectiveNullability.NULLABLE:
        return NullabilityIR.NULLABLE
    return NullabilityIR.UNKNOWN


def _field_names(expression: AggregateCallIR) -> tuple[str, ...]:
    names: list[str] = []
    for argument in expression.arguments:
        names.extend(_walk_field_names(argument))
    return tuple(names)


def _walk_field_names(expression: ExpressionIR) -> Iterable[str]:
    if isinstance(expression, FieldRefIR):
        yield ".".join((*expression.qualifier, expression.name))
        return
    if isinstance(expression, BinaryIR):
        yield from _walk_field_names(expression.left)
        yield from _walk_field_names(expression.right)
        return
    if isinstance(expression, CallIR):
        for argument in expression.arguments:
            yield from _walk_field_names(argument)
        return


def _normalized(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())
