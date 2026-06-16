from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    FieldId,
    FieldRefIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

GROUP_BY_DEFERRED_MESSAGE = (
    "GROUP BY is semantically validated but IR/SQL lowering is deferred"
)


def test_grouped_relation_lowers_group_keys_despite_semantic_gate() -> None:
    script_ir, semantic_result = _compile_grouped_ir(
        _grouped_source(
            connector="postgres.table",
            group_keys=("status", "orders.region"),
            select_body=(
                "        status\n"
                "        region = orders.region\n"
                "        total = count()\n"
                "        revenue = sum(amount)\n"
            ),
        )
    )
    relation = _relation_ir(script_ir, "grouped_orders")

    assert _errors(semantic_result) == [("PIE-S2316", GROUP_BY_DEFERRED_MESSAGE)]
    assert [key.name for key in relation.group_keys] == ["status", "region"]
    assert [key.qualifier for key in relation.group_keys] == [(), ("orders",)]
    assert [key.field for key in relation.group_keys] == [
        FieldId(owner=_orders_symbol(), name="status"),
        FieldId(owner=_orders_symbol(), name="region"),
    ]
    assert all(isinstance(key, FieldRefIR) for key in relation.group_keys)
    assert relation.group_keys[0].value_type.canonical_name == "Text"
    assert relation.group_keys[0].value_type.nullability is NullabilityIR.NON_NULL
    assert relation.group_keys[1].value_type.canonical_name == "Text"
    assert relation.group_keys[1].value_type.nullability is NullabilityIR.NULLABLE


def test_no_group_relation_uses_empty_group_keys_default() -> None:
    script_ir, semantic_result = _compile_grouped_ir(
        _prefix("postgres.table") + "table paid_orders:\n"
        "    from orders\n"
        "    select:\n"
        "        status\n"
    )
    relation = _relation_ir(script_ir, "paid_orders")

    assert _errors(semantic_result) == []
    assert relation.group_keys == ()


def test_bare_and_qualified_duplicate_group_keys_lower_once_in_source_order() -> None:
    script_ir, semantic_result = _compile_grouped_ir(
        _grouped_source(
            connector="postgres.table",
            group_keys=("orders.status", "region", "status", "orders.region"),
            select_body=("        status\n        region\n        total = count()\n"),
        )
    )
    relation = _relation_ir(script_ir, "grouped_orders")

    assert _errors(semantic_result) == [
        ("PIE-S2316", GROUP_BY_DEFERRED_MESSAGE),
        ("PIE-S2317", "Duplicate GROUP BY key: status"),
        ("PIE-S2317", "Duplicate GROUP BY key: orders.region"),
    ]
    assert [(key.name, key.qualifier, key.field) for key in relation.group_keys] == [
        ("status", ("orders",), FieldId(owner=_orders_symbol(), name="status")),
        ("region", (), FieldId(owner=_orders_symbol(), name="region")),
    ]


def test_unknown_group_key_is_not_lowered_into_precise_group_key_ir() -> None:
    script_ir, semantic_result = _compile_grouped_ir(
        _grouped_source(
            connector="postgres.table",
            group_keys=("missing", "status"),
            select_body=("        missing\n        status\n        total = count()\n"),
        )
    )
    relation = _relation_ir(script_ir, "grouped_orders")

    assert _errors(semantic_result) == [
        ("PIE-S2316", GROUP_BY_DEFERRED_MESSAGE),
        ("PIE-S2102", "Unknown field: missing"),
    ]
    assert [key.name for key in relation.group_keys] == ["status"]
    assert all(
        key.field != FieldId(owner=_orders_symbol(), name="missing")
        for key in relation.group_keys
    )


def test_grouped_aggregate_projections_and_row_schema_survive_ir_lowering() -> None:
    script_ir, _semantic_result = _compile_grouped_ir(
        _grouped_source(
            connector="postgres.table",
            group_keys=("status", "orders.region"),
            select_body=(
                "        status\n"
                "        bucket = orders.region\n"
                "        total = count()\n"
                "        revenue = sum(amount)\n"
                "        average_score = avg(score)\n"
            ),
        )
    )
    relation = _relation_ir(script_ir, "grouped_orders")
    projections = {projection.name: projection for projection in relation.projections}

    assert isinstance(projections["total"].expression, AggregateCallIR)
    assert isinstance(projections["revenue"].expression, AggregateCallIR)
    assert isinstance(projections["average_score"].expression, AggregateCallIR)
    assert [
        (projection.name, type(projection.expression))
        for projection in relation.projections
    ] == [
        ("status", FieldRefIR),
        ("bucket", FieldRefIR),
        ("total", AggregateCallIR),
        ("revenue", AggregateCallIR),
        ("average_score", AggregateCallIR),
    ]
    assert [
        (field.name, field.type_ref.canonical_name, field.nullability)
        for field in relation.row_schema.fields
    ] == [
        ("status", "Text", NullabilityIR.NON_NULL),
        ("bucket", "Text", NullabilityIR.NULLABLE),
        ("total", "Int", NullabilityIR.NON_NULL),
        ("revenue", "Int", NullabilityIR.NULLABLE),
        ("average_score", "Float", NullabilityIR.NULLABLE),
    ]


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_message"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "PostgreSQL grouped relation SQL lowering is not implemented",
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "MySQL grouped relation SQL lowering is not implemented",
        ),
    ],
)
def test_direct_sql_emitters_fail_closed_for_grouped_ir(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_message: str,
) -> None:
    script_ir, _semantic_result = _compile_grouped_ir(
        _grouped_source(
            connector=connector,
            group_keys=("status",),
            select_body="        status\n        total = count()\n",
        )
    )

    result = emitter(script_ir)

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert expected_message in result.diagnostics[0].message


@pytest.mark.parametrize(
    ("connector", "emitter", "expected_message"),
    [
        (
            "postgres.table",
            emit_postgres_sql,
            "PostgreSQL relation input depends on unsupported grouped lowering",
        ),
        (
            "mysql.table",
            emit_mysql_sql,
            "MySQL relation input depends on unsupported grouped lowering",
        ),
    ],
)
def test_direct_sql_emitters_fail_closed_for_downstream_from_grouped_ir(
    connector: str,
    emitter: Callable[[ScriptIR], SqlResult],
    expected_message: str,
) -> None:
    script_ir, _semantic_result = _compile_grouped_ir(
        _grouped_source(
            connector=connector,
            group_keys=("status",),
            select_body="        status\n        total = count()\n",
        )
        + "query downstream:\n"
        "    from grouped_orders\n"
        "    select:\n"
        "        status\n"
        "        total\n"
    )

    result = emitter(script_ir)

    assert result.artifacts == ()
    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "PIE-B1000",
        "PIE-B1000",
    ]
    assert expected_message in result.diagnostics[1].message


@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
def test_cli_emit_sql_still_fails_before_sql_without_artifacts(
    dialect: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    connector = "postgres.table" if dialect == "postgres" else "mysql.table"
    path = tmp_path / f"grouped-{dialect}.pietto"
    path.write_text(
        _grouped_source(
            connector=connector,
            group_keys=("status",),
            select_body="        status\n        total = count()\n",
        ),
        encoding="utf-8",
    )

    assert (
        cli.main(["emit-sql", str(path), "--dialect", dialect, "--format", "json"]) == 1
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    result = cast(dict[str, object], json.loads(captured.out))
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert result["ok"] is False
    assert result["artifacts"] == []
    assert [(item["code"], item["message"]) for item in diagnostics] == [
        ("PIE-S2316", GROUP_BY_DEFERRED_MESSAGE)
    ]


def _compile_grouped_ir(source: str) -> tuple[ScriptIR, SemanticResult]:
    parse_result = parse_source(source)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    semantic_result = analyze(parse_result.ast)
    ir_result = build_ir(parse_result.ast, semantic_result.model)

    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir, semantic_result


def _grouped_source(
    *,
    connector: str,
    group_keys: tuple[str, ...],
    select_body: str,
) -> str:
    keys = "".join(f"        {key}\n" for key in group_keys)
    return (
        _prefix(connector) + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        f"{keys}"
        "    select:\n"
        f"{select_body}"
    )


def _prefix(connector: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text not null\n"
        "    region: Text nullable\n"
        "    amount: Int not null\n"
        "    score: Float not null\n"
        f'source orders: Order is {connector}("orders")\n'
    )


def _relation_ir(script_ir: ScriptIR, name: str) -> RelationIR:
    matches = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _orders_symbol() -> SymbolId:
    return SymbolId(SymbolNamespace.RELATION, "orders")


def _errors(result: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
