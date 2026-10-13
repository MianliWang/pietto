from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import (
    FieldId,
    FieldRefIR,
    RelationIR,
    ScriptIR,
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.ir.model import OrderDirectionIR
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze
from pietto.sql import SqlArtifactKind, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    status: Text not null\n"
    "    region: Text nullable\n"
    "    active: Bool not null\n"
    'source orders: Order is postgres.table("orders")\n'
)
MYSQL_SOURCE_PREFIX = SOURCE_PREFIX.replace("postgres.table", "mysql.table")


def test_grouped_order_by_direct_field_row_let_is_semantically_accepted() -> None:
    semantic = _semantic_for(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "    order by:\n"
        "        key\n"
    )

    assert _errors(semantic) == []


def test_grouped_order_by_qualified_chained_alias_row_let_is_accepted() -> None:
    semantic = _semantic_for(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        region_key = orders.region\n"
        "        bucket = region_key\n"
        "    group by:\n"
        "        bucket\n"
        "    select:\n"
        "        bucket_name = orders.region\n"
        "        total = count()\n"
        "    order by:\n"
        "        bucket desc\n"
    )

    assert _errors(semantic) == []


def test_ir_lowers_grouped_order_row_let_to_selected_field_expression() -> None:
    relation = _relation_ir(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        region_key = orders.region\n"
        "        bucket = region_key\n"
        "    group by:\n"
        "        bucket\n"
        "    select:\n"
        "        bucket_name = orders.region\n"
        "        total = count()\n"
        "    order by:\n"
        "        bucket desc\n"
    )

    assert len(relation.order_by) == 1
    order_item = relation.order_by[0]
    assert order_item.direction is OrderDirectionIR.DESC
    field = _assert_field_ref(order_item.expression, name="region")
    assert field.qualifier == ("orders",)
    assert field.name != "bucket"
    assert not _field_refs_named(relation, {"region_key", "bucket"})


@pytest.mark.parametrize(
    ("prefix", "dialect", "expected_order", "forbidden"),
    [
        (
            SOURCE_PREFIX,
            "postgres",
            '    "orders"."status" DESC',
            ('"key"', "WITH ", "FROM (SELECT"),
        ),
        (
            MYSQL_SOURCE_PREFIX,
            "mysql",
            "    `orders`.`status` DESC",
            ("`key`", "WITH ", "FROM (SELECT"),
        ),
    ],
)
def test_sql_inlines_grouped_order_by_row_let_without_hidden_layers(
    prefix: str,
    dialect: str,
    expected_order: str,
    forbidden: tuple[str, ...],
) -> None:
    sql = _sql_for(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        key = orders.status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status = orders.status\n"
        "        total = count()\n"
        "    order by:\n"
        "        key desc\n",
        prefix=prefix,
        dialect=dialect,
    )

    assert _order_by_clause(sql) == expected_order
    for fragment in forbidden:
        if fragment.endswith(" "):
            assert fragment not in sql.upper()
        else:
            assert fragment not in sql


def test_cli_json_and_explain_shapes_remain_compatible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(
        tmp_path,
        "grouped_order_let.pietto",
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "    order by:\n"
        "        key\n",
    )

    assert cli.main(["check", str(source_path)]) == 0
    check_output = capsys.readouterr()
    assert check_output.err == ""
    assert f"OK: {source_path}" in check_output.out

    assert (
        cli.main(
            [
                "emit-sql",
                str(source_path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )
    emit_document = _read_json(capsys)
    assert emit_document["ok"] is True
    assert emit_document["diagnostics"] == []
    assert len(cast(list[object], emit_document["artifacts"])) == 1
    assert "let_scopes" not in json.dumps(emit_document)

    assert cli.main(["explain", str(source_path), "--format", "json"]) == 0
    explain_document = _read_json(capsys)
    assert explain_document["ok"] is True
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert "metadata" in explain_document
    assert "let_scopes" not in json.dumps(explain_document)


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    order by:\n"
            "        gross\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        normalized = lower(trim(status))\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    order by:\n"
            "        normalized\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        one = 1\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    order by:\n"
            "        one\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        key = status\n"
            "    group by:\n"
            "        key\n"
            "    select:\n"
            "        total = count()\n"
            "    order by:\n"
            "        key\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        key = status\n"
            "    group by:\n"
            "        key\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    order by:\n"
            "        orders.key\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        key = status\n"
            "    group by:\n"
            "        key\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    satisfying:\n"
            "        key > 0\n",
            "PIE-S2324",
        ),
    ],
)
def test_non_slice5_grouped_order_let_consumers_remain_rejected(
    body: str,
    expected_code: str,
) -> None:
    semantic = _semantic_for("query grouped_orders:\n" + body)

    assert expected_code in _error_codes(semantic)


def _semantic_for(source: str) -> SemanticResult:
    result = parse_source(SOURCE_PREFIX + source, path="phase43-slice5.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return analyze(result.ast)


def _relation_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> RelationIR:
    script_ir = _script_ir(source, prefix=prefix)
    relation = script_ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    return relation


def _script_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> ScriptIR:
    result = parse_source(prefix + source, path="phase43-slice5.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic = analyze(result.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(result.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _sql_for(source: str, *, prefix: str, dialect: str) -> str:
    script_ir = _script_ir(source, prefix=prefix)
    result = (
        emit_mysql_sql(script_ir)
        if dialect == "mysql"
        else emit_postgres_sql(script_ir)
    )
    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].kind is SqlArtifactKind.RELATION
    return result.artifacts[0].sql


def _write_source(tmp_path: Path, filename: str, relation_source: str) -> Path:
    path = tmp_path / filename
    path.write_text(SOURCE_PREFIX + relation_source, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    return cast(dict[str, object], json.loads(captured.out))


def _order_by_clause(sql: str) -> str:
    return sql.split("ORDER BY\n", maxsplit=1)[1].split("\nLIMIT", maxsplit=1)[0]


def _assert_field_ref(expression: object, *, name: str) -> FieldRefIR:
    assert isinstance(expression, FieldRefIR)
    assert expression.name == name
    assert expression.field == FieldId(owner=_orders_symbol(), name=name)
    return expression


def _field_refs_named(relation: RelationIR, names: set[str]) -> bool:
    return any(ref.name in names for ref in _field_refs(relation))


def _field_refs(value: object) -> tuple[FieldRefIR, ...]:
    refs: list[FieldRefIR] = []
    if isinstance(value, FieldRefIR):
        refs.append(value)
    if isinstance(value, tuple):
        for item in value:
            refs.extend(_field_refs(item))
    elif is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            refs.extend(_field_refs(getattr(value, field.name)))
    return tuple(refs)


def _orders_symbol() -> SymbolId:
    return SymbolId(SymbolNamespace.RELATION, "orders")


def _error_codes(semantic: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _errors(semantic: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
