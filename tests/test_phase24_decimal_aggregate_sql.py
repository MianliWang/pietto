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

POSTGRES_INPUT = Path("tests/fixtures/phase24/postgres_decimal_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase24/mysql_decimal_aggregate.pietto")
POSTGRES_GROUPED_INPUT = Path(
    "tests/fixtures/phase24/postgres_grouped_decimal_aggregate.pietto"
)
MYSQL_GROUPED_INPUT = Path(
    "tests/fixtures/phase24/mysql_grouped_decimal_aggregate.pietto"
)
POSTGRES_GOLDEN = "emit_sql_decimal_aggregate.sql"
MYSQL_GOLDEN = "emit_mysql_decimal_aggregate.sql"
POSTGRES_GROUPED_GOLDEN = "emit_sql_grouped_decimal_aggregate.sql"
MYSQL_GROUPED_GOLDEN = "emit_mysql_grouped_decimal_aggregate.sql"

DECIMAL_SQL_CASES: tuple[
    tuple[Path, str, Callable[[ScriptIR], SqlResult], str],
    ...,
] = (
    (POSTGRES_INPUT, POSTGRES_GOLDEN, emit_postgres_sql, "decimal_order_stats"),
    (MYSQL_INPUT, MYSQL_GOLDEN, emit_mysql_sql, "decimal_order_stats"),
    (
        POSTGRES_GROUPED_INPUT,
        POSTGRES_GROUPED_GOLDEN,
        emit_postgres_sql,
        "decimal_order_stats_by_status",
    ),
    (
        MYSQL_GROUPED_INPUT,
        MYSQL_GROUPED_GOLDEN,
        emit_mysql_sql,
        "decimal_order_stats_by_status",
    ),
)
PHASE24_DECIMAL_SQL_GOLDENS = {
    POSTGRES_GOLDEN,
    MYSQL_GOLDEN,
    POSTGRES_GROUPED_GOLDEN,
    MYSQL_GROUPED_GOLDEN,
}

SPAN = SourceSpan(
    path="phase24-decimal-aggregate-sql.pietto",
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
DECIMAL_NULLABLE = TypeRefIR(
    symbol=SymbolId(SymbolNamespace.TYPE, "Decimal"),
    canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Decimal"),
    declared_name="Decimal",
    canonical_name="Decimal",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
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


@pytest.mark.parametrize(
    ("function", "postgres_sql", "mysql_sql"),
    [
        ("sum", 'SUM("amount")', "SUM(`amount`)"),
        ("avg", 'AVG("amount")', "AVG(`amount`)"),
        ("min", 'MIN("amount")', "MIN(`amount`)"),
        ("max", 'MAX("amount")', "MAX(`amount`)"),
    ],
)
def test_direct_renderers_support_decimal_aggregate_shapes(
    function: str,
    postgres_sql: str,
    mysql_sql: str,
) -> None:
    aggregate = _aggregate(
        function, DECIMAL_NULLABLE, _field("amount", DECIMAL_NON_NULL)
    )

    assert render_expression_sql(aggregate) == postgres_sql
    assert render_mysql_expression(aggregate) == mysql_sql


@pytest.mark.parametrize(
    ("function", "postgres_sql", "mysql_sql"),
    [
        ("sum", 'SUM("orders"."amount")', "SUM(`orders`.`amount`)"),
        ("avg", 'AVG("orders"."amount")', "AVG(`orders`.`amount`)"),
        ("min", 'MIN("orders"."amount")', "MIN(`orders`.`amount`)"),
        ("max", 'MAX("orders"."amount")', "MAX(`orders`.`amount`)"),
    ],
)
def test_direct_renderers_support_qualified_decimal_aggregate_shapes(
    function: str,
    postgres_sql: str,
    mysql_sql: str,
) -> None:
    aggregate = _aggregate(
        function,
        DECIMAL_NULLABLE,
        _field("amount", DECIMAL_NON_NULL, qualifier=("orders",)),
    )

    assert render_expression_sql(aggregate) == postgres_sql
    assert render_mysql_expression(aggregate) == mysql_sql


@pytest.mark.parametrize(
    ("input_path", "golden_name", "emitter", "artifact_name"),
    DECIMAL_SQL_CASES,
)
def test_direct_backend_decimal_aggregate_sql_matches_reviewed_golden(
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
                'SUM("amount") AS "total_amount"',
                'SUM("orders"."amount") AS "total_amount_qualified"',
                'AVG("amount") AS "average_amount"',
                'AVG("orders"."amount") AS "average_amount_qualified"',
                'MIN("amount") AS "smallest_amount"',
                'MIN("orders"."amount") AS "smallest_amount_qualified"',
                'MAX("amount") AS "largest_amount"',
                'MAX("orders"."amount") AS "largest_amount_qualified"',
            ),
        ),
        (
            MYSQL_GOLDEN,
            (
                "SUM(`amount`) AS `total_amount`",
                "SUM(`orders`.`amount`) AS `total_amount_qualified`",
                "AVG(`amount`) AS `average_amount`",
                "AVG(`orders`.`amount`) AS `average_amount_qualified`",
                "MIN(`amount`) AS `smallest_amount`",
                "MIN(`orders`.`amount`) AS `smallest_amount_qualified`",
                "MAX(`amount`) AS `largest_amount`",
                "MAX(`orders`.`amount`) AS `largest_amount_qualified`",
            ),
        ),
        (
            POSTGRES_GROUPED_GOLDEN,
            (
                'SUM("amount") AS "total_amount"',
                'AVG("amount") AS "average_amount"',
                'MIN("amount") AS "smallest_amount"',
                'MAX("orders"."amount") AS "largest_amount"',
                "GROUP BY",
                '    "status"',
            ),
        ),
        (
            MYSQL_GROUPED_GOLDEN,
            (
                "SUM(`amount`) AS `total_amount`",
                "AVG(`amount`) AS `average_amount`",
                "MIN(`amount`) AS `smallest_amount`",
                "MAX(`orders`.`amount`) AS `largest_amount`",
                "GROUP BY",
                "    `status`",
            ),
        ),
    ],
)
def test_decimal_aggregate_goldens_lock_no_cast_function_shape(
    golden_name: str,
    expected_fragments: tuple[str, ...],
) -> None:
    sql = _golden_text(golden_name)

    for fragment in expected_fragments:
        assert fragment in sql
    assert "CAST(" not in sql
    assert "::" not in sql


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
        "wrong_arity",
        "non_field_argument",
        "unresolved_field_argument",
        "unsupported_type",
        "malformed_decimal_result_type",
        "malformed_decimal_result_nullability",
    ],
)
def test_malformed_hand_built_decimal_aggregate_ir_fails_closed_with_pie_b1000(
    input_path: Path,
    emitter: Callable[[ScriptIR], SqlResult],
    case: str,
) -> None:
    script_ir = _compile(input_path)
    relation = _relation_ir(script_ir)
    projection = relation.projections[0]
    bad_relation = replace(
        relation,
        projections=(replace(projection, expression=_malformed_aggregate(case)),),
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


def test_direct_malformed_decimal_renderer_errors_stay_dialect_specific() -> None:
    aggregate = _aggregate("sum", DECIMAL_NULLABLE, _literal(1, INT_NON_NULL))

    with pytest.raises(
        ValueError,
        match="field-only Int, Float, or Decimal expression argument",
    ):
        render_expression_sql(aggregate)
    with pytest.raises(
        MySqlRenderError,
        match="field-only Int, Float, or Decimal expression argument",
    ):
        render_mysql_expression(aggregate)


def test_phase24_decimal_aggregate_goldens_are_registered_and_audited() -> None:
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
    assert len(sql_fixtures | json_fixtures) == 37
    assert PHASE24_DECIMAL_SQL_GOLDENS <= sql_fixtures
    assert fixture_inputs[POSTGRES_GOLDEN] == (POSTGRES_INPUT.as_posix(),)
    assert fixture_inputs[MYSQL_GOLDEN] == (MYSQL_INPUT.as_posix(),)
    assert fixture_inputs[POSTGRES_GROUPED_GOLDEN] == (
        POSTGRES_GROUPED_INPUT.as_posix(),
    )
    assert fixture_inputs[MYSQL_GROUPED_GOLDEN] == (MYSQL_GROUPED_INPUT.as_posix(),)
    assert Path("tests/test_phase24_decimal_aggregate_sql.py") in reference_tests
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


def _malformed_aggregate(case: str) -> AggregateCallIR:
    if case == "wrong_arity":
        return _aggregate("sum", DECIMAL_NULLABLE)
    if case == "non_field_argument":
        return _aggregate("sum", DECIMAL_NULLABLE, _literal(1, INT_NON_NULL))
    if case == "unresolved_field_argument":
        return _aggregate(
            "sum",
            DECIMAL_NULLABLE,
            _field("amount", DECIMAL_NON_NULL, resolved=False),
        )
    if case == "unsupported_type":
        return _aggregate("sum", DECIMAL_NULLABLE, _field("status", TEXT_NON_NULL))
    if case == "malformed_decimal_result_type":
        return _aggregate("avg", FLOAT_NULLABLE, _field("amount", DECIMAL_NON_NULL))
    if case == "malformed_decimal_result_nullability":
        return _aggregate("max", DECIMAL_NON_NULL, _field("amount", DECIMAL_NON_NULL))
    raise AssertionError(f"Unknown malformed decimal aggregate case: {case}")


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
        "pietto_phase24_decimal_check_goldens",
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
