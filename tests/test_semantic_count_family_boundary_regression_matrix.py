from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.ir as ir_api
import pietto.sql as sql_api
from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    CallIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    LiteralIR,
    NullabilityIR,
    ProjectionIR,
    RelationIR,
    ScriptIR,
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, SemanticResult, TypeKind, analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SOURCE_PREFIX = (
    "enum Status:\n"
    "    active\n"
    "    paused\n"
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    enum_status: Status not null\n"
    "    active: Bool not null\n"
    "    optional_active: Bool nullable\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    payload: Json not null\n"
    "    raw: Bytes not null\n"
    "    id: UUID not null\n"
    "    anything: Any nullable\n"
)

ACCEPTED_SELECT_BODY = (
    "total = count()\n"
    "        known_amount = count(amount)\n"
    "        qualified_status = count(orders.status)\n"
    "        payloads = count(payload)\n"
    "        raws = count(raw)\n"
    "        ids = count(id)\n"
    "        amount_tax = count(amount + tax)\n"
    "        lowered = count(lower(status))\n"
    "        active_expr = count(active and true)\n"
    "        optional_active_expr = count(active or optional_active)\n"
    "        unique_ids = count_distinct(id)\n"
    "        unique_normalized = count_distinct(lower(trim(status)))"
)

ACCEPTED_ALIASES = (
    "total",
    "known_amount",
    "qualified_status",
    "payloads",
    "raws",
    "ids",
    "amount_tax",
    "lowered",
    "active_expr",
    "optional_active_expr",
    "unique_ids",
    "unique_normalized",
)

EMIT_SQL_KEYS = {
    "schema_version",
    "command",
    "ok",
    "path",
    "dialect",
    "diagnostics",
    "cli_errors",
    "artifacts",
    "output",
}

POSTGRES_COUNT_FAMILY_FRAGMENTS = (
    'COUNT(*) AS "total"',
    'COUNT("amount") AS "known_amount"',
    'COUNT("orders"."status") AS "qualified_status"',
    'COUNT("payload") AS "payloads"',
    'COUNT("raw") AS "raws"',
    'COUNT("id") AS "ids"',
    'COUNT(("amount" + "tax")) AS "amount_tax"',
    'COUNT(lower("status")) AS "lowered"',
    'COUNT(("active" AND TRUE)) AS "active_expr"',
    'COUNT(("active" OR "optional_active")) AS "optional_active_expr"',
    'COUNT(DISTINCT "id") AS "unique_ids"',
    'COUNT(DISTINCT lower(trim("status"))) AS "unique_normalized"',
)

MYSQL_COUNT_FAMILY_FRAGMENTS = (
    "COUNT(*) AS `total`",
    "COUNT(`amount`) AS `known_amount`",
    "COUNT(`orders`.`status`) AS `qualified_status`",
    "COUNT(`payload`) AS `payloads`",
    "COUNT(`raw`) AS `raws`",
    "COUNT(`id`) AS `ids`",
    "COUNT((`amount` + `tax`)) AS `amount_tax`",
    "COUNT(LOWER(`status`)) AS `lowered`",
    "COUNT((`active` AND TRUE)) AS `active_expr`",
    "COUNT((`active` OR `optional_active`)) AS `optional_active_expr`",
    "COUNT(DISTINCT `id`) AS `unique_ids`",
    "COUNT(DISTINCT LOWER(TRIM(`status`))) AS `unique_normalized`",
)


def test_count_family_accepted_matrix_has_int_non_null_semantic_results() -> None:
    result = analyze(_parse(_accepted_source("postgres.table")))
    relation = _semantic_relation(result)
    schema = result.model.relation_row_schemas[relation]

    assert _error_codes(result) == []
    assert list(schema.fields) == list(ACCEPTED_ALIASES)
    for item in relation.select_items:
        assert item.alias is not None
        _assert_semantic_field(
            schema.fields[item.alias],
            "Int",
            EffectiveNullability.NON_NULL,
        )
        _assert_semantic_value_type(
            result.model.expression_value_types[item.expression],
            "Int",
            EffectiveNullability.NON_NULL,
        )


def test_count_family_accepted_matrix_preserves_ir_shapes() -> None:
    relation = _compile_relation(_accepted_source("postgres.table"))
    projections = _projections(relation)

    total = _assert_aggregate(projections["total"].expression, "count")
    assert total.arguments == ()
    _assert_count_field(projections["known_amount"].expression, "amount")
    _assert_count_field(
        projections["qualified_status"].expression,
        "orders.status",
    )
    _assert_count_field(projections["payloads"].expression, "payload")
    _assert_count_field(projections["raws"].expression, "raw")
    _assert_count_field(projections["ids"].expression, "id")
    _assert_binary_aggregate(
        projections["amount_tax"].expression,
        "count",
        operator="+",
        argument_type="Int",
        left="amount",
        right="tax",
    )
    _assert_call_aggregate(
        projections["lowered"].expression,
        "count",
        callee="lower",
        field_name="status",
        argument_type="Text",
    )
    _assert_binary_aggregate(
        projections["active_expr"].expression,
        "count",
        operator="and",
        argument_type="Bool",
        left="active",
        right=True,
    )
    _assert_binary_aggregate(
        projections["optional_active_expr"].expression,
        "count",
        operator="or",
        argument_type="Bool",
        left="active",
        right="optional_active",
    )
    _assert_count_field(projections["unique_ids"].expression, "id", "count_distinct")
    normalized = _assert_call_aggregate(
        projections["unique_normalized"].expression,
        "count_distinct",
        callee="lower",
        field_name=None,
        argument_type="Text",
    )
    inner = normalized.arguments[0]
    assert isinstance(inner, CallIR)
    assert inner.callee == "trim"
    _assert_field(inner.arguments[0], "status")


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_fragments"),
    [
        ("postgres.table", emit_postgres_sql, POSTGRES_COUNT_FAMILY_FRAGMENTS),
        ("mysql.table", emit_mysql_sql, MYSQL_COUNT_FAMILY_FRAGMENTS),
    ],
)
def test_count_family_accepted_matrix_sql_fragments_remain_stable(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_fragments: tuple[str, ...],
) -> None:
    result = emitter(_compile_script_ir(_accepted_source(connector)))

    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    sql = result.artifacts[0].sql
    for fragment in expected_fragments:
        assert fragment in sql


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_fragments"),
    [
        ("postgres", "postgres.table", POSTGRES_COUNT_FAMILY_FRAGMENTS),
        ("mysql", "mysql.table", MYSQL_COUNT_FAMILY_FRAGMENTS),
    ],
)
def test_count_family_cli_json_artifact_success_remains_generic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_fragments: tuple[str, ...],
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-count-family-regression-matrix.pietto",
        _accepted_source(connector),
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format=json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    sql = cast(str, artifacts[0]["sql"])

    assert set(result) == EMIT_SQL_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["path"] == str(path)
    assert result["dialect"] == dialect
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    assert artifacts[0]["kind"] == "relation"
    assert artifacts[0]["name"] == "count_family_matrix"
    for fragment in expected_fragments:
        assert fragment in sql


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = count(1)", "PIE-S2315"),
        ('value = count("x")', "PIE-S2315"),
        ("value = count(true)", "PIE-S2315"),
        ("value = count(1 + 2)", "PIE-S2315"),
        ("value = count_if(active)", "PIE-S2103"),
        ("value = count(enum_status)", "PIE-S2314"),
        ("value = count(anything)", "PIE-S2314"),
        ("value = count(amount > 1)", "PIE-S2315"),
        ("value = count(amount between 1 and 10)", "PIE-S2315"),
        ("value = count(amount is null)", "PIE-S2315"),
        ('value = count(matches(status, "active"))', "PIE-S2315"),
        ("value = count_distinct(amount + tax)", "PIE-S2315"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(amount + tax)", "PIE-S2315"),
        ("value = count(count())", "PIE-S2311"),
        ("value = count(amount) + 1", "PIE-S2310"),
    ],
)
def test_count_family_rejected_semantic_matrix_remains_fail_closed(
    projection: str,
    expected_code: str,
) -> None:
    result = analyze(_parse(_projection_source(projection)))

    assert _error_codes(result) == [expected_code]


def test_projection_aliases_remain_excluded_as_count_argument_leaves() -> None:
    result = analyze(
        _parse(
            _source(
                "postgres.table",
                "subtotal = amount + tax\n        value = count(subtotal + tax)",
            )
        )
    )

    assert _error_codes(result) == ["PIE-S2102"]


@pytest.mark.parametrize(
    "projection",
    [
        "value = count(distinct id)",
        "value = count(amount) filter where amount > 0",
        "value = count(amount) FILTER (WHERE amount > 0)",
    ],
)
def test_sql_style_distinct_and_filter_syntax_remain_unsupported(
    projection: str,
) -> None:
    parse_result = parse_source(_projection_source(projection))

    assert "PIE-P1000" in _diagnostic_codes(parse_result)


def test_relation_layer_runtime_and_public_mysql_surfaces_remain_out_of_scope() -> None:
    assert not hasattr(ir_api, "RelationLayerIR")
    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert not hasattr(sql_api, "emit_mysql_sql")


def _accepted_source(connector: str) -> str:
    return _source(connector, ACCEPTED_SELECT_BODY)


def _projection_source(projection: str) -> str:
    return _source("postgres.table", projection)


def _source(connector: str, select_body: str) -> str:
    return (
        SOURCE_PREFIX + f'source orders: Order is {connector}("orders")\n'
        "table count_family_matrix:\n"
        "    from orders\n"
        "    select:\n"
        f"        {select_body}\n"
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _compile_script_ir(source: str) -> ScriptIR:
    script = _parse(source)
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)

    assert _error_codes(semantic_result) == []
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _compile_relation(source: str) -> RelationIR:
    return _relation_ir(_compile_script_ir(source))


def _semantic_relation(result: SemanticResult) -> TableDef | QueryDef:
    relation = next(iter(result.model.relation_row_schemas))
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


def _assert_semantic_field(
    field: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(field, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(field, "resolved_type").name == expected_type
    assert getattr(field, "nullability") is expected_nullability


def _assert_semantic_value_type(
    value_type: object,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "resolved_type").kind is TypeKind.BUILTIN
    assert getattr(value_type, "resolved_type").name == expected_type
    assert getattr(value_type, "nullability") is expected_nullability


def _assert_aggregate(
    expression: ExpressionIR,
    expected_function: str,
) -> AggregateCallIR:
    assert isinstance(expression, AggregateCallIR)
    assert expression.function == expected_function
    assert expression.value_type.canonical_name == "Int"
    assert expression.value_type.nullability is NullabilityIR.NON_NULL
    return expression


def _assert_count_field(
    expression: ExpressionIR,
    expected_name: str,
    expected_function: str = "count",
) -> None:
    aggregate = _assert_aggregate(expression, expected_function)
    assert len(aggregate.arguments) == 1
    _assert_field(aggregate.arguments[0], expected_name)


def _assert_binary_aggregate(
    expression: ExpressionIR,
    expected_function: str,
    *,
    operator: str,
    argument_type: str,
    left: str | bool,
    right: str | bool,
) -> BinaryIR:
    aggregate = _assert_aggregate(expression, expected_function)
    assert len(aggregate.arguments) == 1
    argument = aggregate.arguments[0]
    assert isinstance(argument, BinaryIR)
    assert argument.operator == operator
    assert argument.value_type.canonical_name == argument_type
    _assert_operand(argument.left, left)
    _assert_operand(argument.right, right)
    return argument


def _assert_call_aggregate(
    expression: ExpressionIR,
    expected_function: str,
    *,
    callee: str,
    field_name: str | None,
    argument_type: str,
) -> CallIR:
    aggregate = _assert_aggregate(expression, expected_function)
    assert len(aggregate.arguments) == 1
    argument = aggregate.arguments[0]
    assert isinstance(argument, CallIR)
    assert argument.callee == callee
    assert argument.value_type.canonical_name == argument_type
    assert len(argument.arguments) == 1
    if field_name is not None:
        _assert_field(argument.arguments[0], field_name)
    return argument


def _assert_operand(expression: ExpressionIR, expected: str | bool) -> None:
    if isinstance(expected, str):
        _assert_field(expression, expected)
        return
    assert isinstance(expression, LiteralIR)
    assert expression.value is expected
    assert expression.value_type.canonical_name == "Bool"


def _assert_field(expression: ExpressionIR, expected_name: str) -> None:
    assert isinstance(expression, FieldRefIR)
    parts = expected_name.split(".")
    assert expression.name == parts[-1]
    assert expression.qualifier == tuple(parts[:-1])
    assert expression.field == FieldId(owner=_orders_symbol(), name=parts[-1])


def _orders_symbol() -> SymbolId:
    return SymbolId(SymbolNamespace.RELATION, "orders")


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("{")
    assert captured.out.endswith("}\n")
    assert captured.out.count("\n") == 1
    result = json.loads(captured.out)
    assert isinstance(result, dict)
    return cast(dict[str, object], result)


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _error_codes(result: object) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in getattr(result, "diagnostics")
        if diagnostic.severity is Severity.ERROR
    ]


def _diagnostic_codes(result: object) -> list[str]:
    return [diagnostic.code for diagnostic in getattr(result, "diagnostics")]
