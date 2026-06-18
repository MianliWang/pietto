from __future__ import annotations

import importlib.util
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
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
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.mysql_render import MySqlRenderError

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts" / "check_goldens.py"

POSTGRES_INPUT = Path("tests/fixtures/phase24/postgres_count_distinct_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase24/mysql_count_distinct_aggregate.pietto")
POSTGRES_GROUPED_INPUT = Path(
    "tests/fixtures/phase24/postgres_grouped_count_distinct_aggregate.pietto"
)
MYSQL_GROUPED_INPUT = Path(
    "tests/fixtures/phase24/mysql_grouped_count_distinct_aggregate.pietto"
)
POSTGRES_GOLDEN = "emit_sql_count_distinct_aggregate.sql"
MYSQL_GOLDEN = "emit_mysql_count_distinct_aggregate.sql"
POSTGRES_GROUPED_GOLDEN = "emit_sql_grouped_count_distinct_aggregate.sql"
MYSQL_GROUPED_GOLDEN = "emit_mysql_grouped_count_distinct_aggregate.sql"

COUNT_DISTINCT_SQL_CASES: tuple[
    tuple[Path, str, Callable[[ScriptIR], SqlResult], str],
    ...,
] = (
    (POSTGRES_INPUT, POSTGRES_GOLDEN, emit_postgres_sql, "unique_order_values"),
    (MYSQL_INPUT, MYSQL_GOLDEN, emit_mysql_sql, "unique_order_values"),
    (
        POSTGRES_GROUPED_INPUT,
        POSTGRES_GROUPED_GOLDEN,
        emit_postgres_sql,
        "unique_customers_by_status",
    ),
    (
        MYSQL_GROUPED_INPUT,
        MYSQL_GROUPED_GOLDEN,
        emit_mysql_sql,
        "unique_customers_by_status",
    ),
)
PHASE24_SQL_GOLDENS = {
    POSTGRES_GOLDEN,
    MYSQL_GOLDEN,
    POSTGRES_GROUPED_GOLDEN,
    MYSQL_GROUPED_GOLDEN,
}

SPAN = SourceSpan(
    path="phase24-count-distinct-sql.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)
OWNER = SymbolId(SymbolNamespace.RELATION, "orders")
UNKNOWN_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="<unknown>",
    canonical_name="<unknown>",
    kind=TypeKindIR.UNKNOWN,
    canonical_kind=TypeKindIR.UNKNOWN,
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
BOOL_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Bool"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Bool"),
    declared_name="Bool",
    canonical_name="Bool",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
INT_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Int"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Int"),
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
INT_NULLABLE = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Int"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Int"),
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)
FLOAT_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Float"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Float"),
    declared_name="Float",
    canonical_name="Float",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
FLOAT_NULLABLE = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Float"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Float"),
    declared_name="Float",
    canonical_name="Float",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)
DECIMAL_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Decimal"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Decimal"),
    declared_name="Decimal",
    canonical_name="Decimal",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
TEXT_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
    declared_name="Text",
    canonical_name="Text",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
DATE_NULLABLE = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Date"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Date"),
    declared_name="Date",
    canonical_name="Date",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)
TIMESTAMP_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Timestamp"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Timestamp"),
    declared_name="Timestamp",
    canonical_name="Timestamp",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
UUID_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "UUID"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "UUID"),
    declared_name="UUID",
    canonical_name="UUID",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
BYTES_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Bytes"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Bytes"),
    declared_name="Bytes",
    canonical_name="Bytes",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
JSON_NON_NULL = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Json"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Json"),
    declared_name="Json",
    canonical_name="Json",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)


@pytest.mark.parametrize(
    ("field_name", "value_type"),
    [
        ("active", BOOL_NON_NULL),
        ("amount", INT_NON_NULL),
        ("score", FLOAT_NULLABLE),
        ("price", DECIMAL_NON_NULL),
        ("status", TEXT_NON_NULL),
        ("order_date", DATE_NULLABLE),
        ("created_at", TIMESTAMP_NON_NULL),
        ("customer_id", UUID_NON_NULL),
    ],
)
def test_direct_renderers_support_count_distinct_field_types(
    field_name: str,
    value_type: TypeRefIR,
) -> None:
    aggregate = _aggregate(
        "count_distinct",
        INT_NON_NULL,
        _field(field_name, value_type),
    )

    assert render_expression_sql(aggregate) == f'COUNT(DISTINCT "{field_name}")'
    assert render_mysql_expression(aggregate) == f"COUNT(DISTINCT `{field_name}`)"


def test_direct_renderers_support_qualified_count_distinct_and_existing_aggregates() -> (
    None
):
    count_star = _aggregate("count", INT_NON_NULL)
    count_amount = _aggregate("count", INT_NON_NULL, _field("amount", INT_NULLABLE))
    count_distinct_status = _aggregate(
        "count_distinct",
        INT_NON_NULL,
        _field("status", TEXT_NON_NULL, qualifier=("orders",)),
    )

    assert render_expression_sql(count_star) == "COUNT(*)"
    assert render_mysql_expression(count_star) == "COUNT(*)"
    assert render_expression_sql(count_amount) == 'COUNT("amount")'
    assert render_mysql_expression(count_amount) == "COUNT(`amount`)"
    assert (
        render_expression_sql(count_distinct_status)
        == 'COUNT(DISTINCT "orders"."status")'
    )
    assert (
        render_mysql_expression(count_distinct_status)
        == "COUNT(DISTINCT `orders`.`status`)"
    )
    assert (
        render_expression_sql(
            _aggregate("sum", INT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == 'SUM("amount")'
    )
    assert (
        render_mysql_expression(
            _aggregate("sum", INT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == "SUM(`amount`)"
    )
    assert (
        render_expression_sql(
            _aggregate("avg", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == 'AVG("amount")'
    )
    assert (
        render_mysql_expression(
            _aggregate("avg", FLOAT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == "AVG(`amount`)"
    )
    assert (
        render_expression_sql(
            _aggregate("min", INT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == 'MIN("amount")'
    )
    assert (
        render_mysql_expression(
            _aggregate("max", INT_NULLABLE, _field("amount", INT_NON_NULL))
        )
        == "MAX(`amount`)"
    )


@pytest.mark.parametrize(
    ("input_path", "golden_name", "emitter", "artifact_name"),
    COUNT_DISTINCT_SQL_CASES,
)
def test_direct_backend_count_distinct_sql_matches_reviewed_golden(
    input_path: Path,
    golden_name: str,
    emitter: Callable[[ScriptIR], SqlResult],
    artifact_name: str,
) -> None:
    result = emitter(_compile(input_path))

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].name == artifact_name
    assert _render_artifacts(result) == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("golden_name", "expected_fragments"),
    [
        (
            POSTGRES_GOLDEN,
            (
                'COUNT(DISTINCT "customer_id") AS "unique_customers"',
                'COUNT(DISTINCT "orders"."status") AS "unique_statuses"',
                'FROM "orders" AS "orders"',
            ),
        ),
        (
            MYSQL_GOLDEN,
            (
                "COUNT(DISTINCT `customer_id`) AS `unique_customers`",
                "COUNT(DISTINCT `orders`.`status`) AS `unique_statuses`",
                "FROM `orders` AS `orders`",
            ),
        ),
        (
            POSTGRES_GROUPED_GOLDEN,
            (
                'COUNT(DISTINCT "customer_id") AS "unique_customers"',
                'COUNT(DISTINCT "orders"."status") AS "unique_statuses"',
                "GROUP BY",
                '    "status"',
            ),
        ),
        (
            MYSQL_GROUPED_GOLDEN,
            (
                "COUNT(DISTINCT `customer_id`) AS `unique_customers`",
                "COUNT(DISTINCT `orders`.`status`) AS `unique_statuses`",
                "GROUP BY",
                "    `status`",
            ),
        ),
    ],
)
def test_count_distinct_goldens_lock_function_and_qualification_shape(
    golden_name: str,
    expected_fragments: tuple[str, ...],
) -> None:
    sql = _golden_text(golden_name)

    for fragment in expected_fragments:
        assert fragment in sql


@pytest.mark.parametrize(
    ("input_path", "golden_name", "emitter"),
    [
        (
            Path("tests/fixtures/phase19/postgres_count_aggregate.pietto"),
            "emit_sql_count_aggregate.sql",
            emit_postgres_sql,
        ),
        (
            Path("tests/fixtures/phase19/mysql_count_aggregate.pietto"),
            "emit_mysql_count_aggregate.sql",
            emit_mysql_sql,
        ),
        (
            Path("tests/fixtures/phase20/postgres_sum_avg_aggregate.pietto"),
            "emit_sql_sum_avg_aggregate.sql",
            emit_postgres_sql,
        ),
        (
            Path("tests/fixtures/phase20/mysql_sum_avg_aggregate.pietto"),
            "emit_mysql_sum_avg_aggregate.sql",
            emit_mysql_sql,
        ),
        (
            Path("tests/fixtures/phase22/postgres_min_max_aggregate.pietto"),
            "emit_sql_min_max_aggregate.sql",
            emit_postgres_sql,
        ),
        (
            Path("tests/fixtures/phase22/mysql_min_max_aggregate.pietto"),
            "emit_mysql_min_max_aggregate.sql",
            emit_mysql_sql,
        ),
        (
            Path("tests/fixtures/phase23/postgres_count_field_aggregate.pietto"),
            "emit_sql_count_field_aggregate.sql",
            emit_postgres_sql,
        ),
        (
            Path("tests/fixtures/phase23/mysql_count_field_aggregate.pietto"),
            "emit_mysql_count_field_aggregate.sql",
            emit_mysql_sql,
        ),
    ],
)
def test_existing_aggregate_goldens_remain_byte_stable(
    input_path: Path,
    golden_name: str,
    emitter: Callable[[ScriptIR], SqlResult],
) -> None:
    result = emitter(_compile(input_path))

    assert result.diagnostics == ()
    assert _render_artifacts(result) == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "emitter"),
    [
        (POSTGRES_INPUT, emit_postgres_sql),
        (MYSQL_INPUT, emit_mysql_sql),
    ],
)
@pytest.mark.parametrize(
    "case",
    [
        "no_arguments",
        "too_many_arguments",
        "non_field_argument",
        "unresolved_field_argument",
        "unknown_field_type",
        "any_field_type",
        "bytes_field_type",
        "json_field_type",
        "malformed_result_type",
        "malformed_result_nullability",
    ],
)
def test_malformed_hand_built_count_distinct_ir_fails_closed_with_pie_b1000(
    input_path: Path,
    emitter: Callable[[ScriptIR], SqlResult],
    case: str,
) -> None:
    script_ir = _compile(input_path)
    relation = _relation_ir(script_ir)
    projection = relation.projections[0]
    bad_relation = replace(
        relation,
        projections=(replace(projection, expression=_malformed_count_distinct(case)),),
    )
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emitter(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert result.diagnostics[0].severity is Severity.ERROR


def test_direct_malformed_count_distinct_renderer_errors_stay_dialect_specific() -> (
    None
):
    count_literal = _aggregate(
        "count_distinct",
        INT_NON_NULL,
        _literal(1, INT_NON_NULL),
    )

    with pytest.raises(ValueError, match="direct field argument"):
        render_expression_sql(count_literal)
    with pytest.raises(MySqlRenderError, match="direct field argument"):
        render_mysql_expression(count_literal)


def test_phase24_count_distinct_goldens_are_registered_and_audited() -> None:
    goldens = _check_goldens()
    sql_fixtures = cast(frozenset[str], getattr(goldens, "SQL_FIXTURES"))
    json_fixtures = cast(frozenset[str], getattr(goldens, "JSON_FIXTURES"))
    fixture_inputs = cast(
        dict[str, tuple[str, ...]],
        getattr(goldens, "FIXTURE_INPUTS"),
    )
    reference_tests = cast(tuple[Path, ...], getattr(goldens, "REFERENCE_TESTS"))
    audit = cast(Callable[[Path], tuple[str, ...]], getattr(goldens, "audit"))

    assert len(sql_fixtures) == 32
    assert len(json_fixtures) == 5
    assert PHASE24_SQL_GOLDENS <= sql_fixtures
    assert fixture_inputs[POSTGRES_GOLDEN] == (POSTGRES_INPUT.as_posix(),)
    assert fixture_inputs[MYSQL_GOLDEN] == (MYSQL_INPUT.as_posix(),)
    assert fixture_inputs[POSTGRES_GROUPED_GOLDEN] == (
        POSTGRES_GROUPED_INPUT.as_posix(),
    )
    assert fixture_inputs[MYSQL_GROUPED_GOLDEN] == (MYSQL_GROUPED_INPUT.as_posix(),)
    assert Path("tests/test_phase24_count_distinct_sql.py") in reference_tests
    assert audit(REPO_ROOT) == ()


def _compile(path: Path) -> ScriptIR:
    parse_result = parse_file(REPO_ROOT / path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _malformed_count_distinct(case: str) -> AggregateCallIR:
    if case == "no_arguments":
        return _aggregate("count_distinct", INT_NON_NULL)
    if case == "too_many_arguments":
        return _aggregate(
            "count_distinct",
            INT_NON_NULL,
            _field("customer_id", UUID_NON_NULL),
            _field("status", TEXT_NON_NULL),
        )
    if case == "non_field_argument":
        return _aggregate("count_distinct", INT_NON_NULL, _literal(1, INT_NON_NULL))
    if case == "unresolved_field_argument":
        return _aggregate(
            "count_distinct",
            INT_NON_NULL,
            _field("customer_id", UUID_NON_NULL, resolved=False),
        )
    if case == "unknown_field_type":
        return _aggregate("count_distinct", INT_NON_NULL, _field("value", UNKNOWN_TYPE))
    if case == "any_field_type":
        return _aggregate(
            "count_distinct",
            INT_NON_NULL,
            _field("anything", ANY_NULLABLE),
        )
    if case == "bytes_field_type":
        return _aggregate(
            "count_distinct",
            INT_NON_NULL,
            _field("raw", BYTES_NON_NULL),
        )
    if case == "json_field_type":
        return _aggregate(
            "count_distinct",
            INT_NON_NULL,
            _field("payload", JSON_NON_NULL),
        )
    if case == "malformed_result_type":
        return _aggregate(
            "count_distinct",
            FLOAT_NON_NULL,
            _field("customer_id", UUID_NON_NULL),
        )
    if case == "malformed_result_nullability":
        return _aggregate(
            "count_distinct",
            INT_NULLABLE,
            _field("customer_id", UUID_NON_NULL),
        )
    raise AssertionError(f"Unknown malformed count_distinct case: {case}")


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


def _check_goldens() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "pietto_phase24_check_goldens",
        CHECK_GOLDENS_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _golden_text(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def _golden_bytes(name: str) -> bytes:
    return (GOLDEN_ROOT / name).read_bytes()


def _render_artifacts(result: SqlResult) -> bytes:
    return ("\n\n".join(artifact.sql for artifact in result.artifacts) + "\n").encode(
        "utf-8"
    )
