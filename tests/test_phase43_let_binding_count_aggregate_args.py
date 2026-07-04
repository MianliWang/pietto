from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import QueryDef, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    BinaryIR,
    CallIR,
    FieldRefIR,
    RelationIR,
    ScriptIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, RowField, SemanticResult, analyze
from pietto.sql import SqlArtifactKind, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SOURCE_PREFIX = (
    "enum Status:\n"
    "    active\n"
    "    paused\n"
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    discount: Int not null\n"
    "    score: Float not null\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    raw: Bytes not null\n"
    "    payload: Json not null\n"
    "    anything: Any nullable\n"
    "    enum_status: Status not null\n"
    'source orders: Order is postgres.table("orders")\n'
)
MYSQL_SOURCE_PREFIX = SOURCE_PREFIX.replace("postgres.table", "mysql.table")


def test_count_row_let_arguments_are_semantically_accepted() -> None:
    semantic = _semantic_for(
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        amount_value = amount\n"
        "        gross = amount + tax\n"
        "        net = gross - discount\n"
        "        normalized = lower(trim(status))\n"
        "    select:\n"
        "        known_amounts = count(amount_value)\n"
        "        known_gross = count(gross)\n"
        "        known_net = count(net)\n"
        "        known_normalized = count(normalized)\n"
    )
    relation = _relation_ast(semantic)
    schema = semantic.model.relation_row_schemas[relation]

    assert _errors(semantic) == []
    assert list(schema.fields) == [
        "known_amounts",
        "known_gross",
        "known_net",
        "known_normalized",
    ]
    for field_name in schema.fields:
        _assert_field(schema.fields[field_name], "Int", EffectiveNullability.NON_NULL)


def test_count_distinct_row_let_arguments_are_semantically_accepted() -> None:
    semantic = _semantic_for(
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        amount_value = amount\n"
        "        label = status\n"
        "        normalized = lower(trim(status))\n"
        "    select:\n"
        "        unique_amounts = count_distinct(amount_value)\n"
        "        unique_labels = count_distinct(label)\n"
        "        unique_normalized = count_distinct(normalized)\n"
    )
    relation = _relation_ast(semantic)
    schema = semantic.model.relation_row_schemas[relation]

    assert _errors(semantic) == []
    assert list(schema.fields) == [
        "unique_amounts",
        "unique_labels",
        "unique_normalized",
    ]
    for field_name in schema.fields:
        _assert_field(schema.fields[field_name], "Int", EffectiveNullability.NON_NULL)


def test_grouped_count_family_row_let_arguments_are_semantically_accepted() -> None:
    semantic = _semantic_for(
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        normalized = lower(trim(status))\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        known_gross = count(gross)\n"
        "        unique_normalized = count_distinct(normalized)\n"
    )
    relation = _relation_ast(semantic)
    schema = semantic.model.relation_row_schemas[relation]

    assert _errors(semantic) == []
    assert list(schema.fields) == ["status", "known_gross", "unique_normalized"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["known_gross"], "Int", EffectiveNullability.NON_NULL)
    _assert_field(
        schema.fields["unique_normalized"],
        "Int",
        EffectiveNullability.NON_NULL,
    )


@pytest.mark.parametrize(
    ("prefix", "dialect", "expected_fragments", "forbidden"),
    [
        (
            SOURCE_PREFIX,
            "postgres",
            (
                'COUNT((("amount" + "tax") - "discount")) AS "known_net"',
                'COUNT(DISTINCT lower(trim("status"))) AS "unique_normalized"',
            ),
            ('"gross"', '"net"', '"normalized"', "WITH ", "FROM (SELECT"),
        ),
        (
            MYSQL_SOURCE_PREFIX,
            "mysql",
            (
                "COUNT(((`amount` + `tax`) - `discount`)) AS `known_net`",
                "COUNT(DISTINCT LOWER(TRIM(`status`))) AS `unique_normalized`",
            ),
            ("`gross`", "`net`", "`normalized`", "WITH ", "FROM (SELECT"),
        ),
    ],
)
def test_sql_inlines_count_family_row_let_arguments_without_hidden_layers(
    prefix: str,
    dialect: str,
    expected_fragments: tuple[str, str],
    forbidden: tuple[str, ...],
) -> None:
    sql = _sql_for(
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        net = gross - discount\n"
        "        normalized = lower(trim(status))\n"
        "    select:\n"
        "        known_net = count(net)\n"
        "        unique_normalized = count_distinct(normalized)\n",
        prefix=prefix,
        dialect=dialect,
    )

    for fragment in expected_fragments:
        assert fragment in sql
    for fragment in forbidden:
        if fragment.endswith(" "):
            assert fragment not in sql.upper()
        else:
            assert fragment not in sql


def test_ir_count_family_aggregate_arguments_inline_expand_row_let_names() -> None:
    relation = _relation_ir(
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        net = gross - discount\n"
        "        normalized = lower(trim(status))\n"
        "    select:\n"
        "        known_net = count(net)\n"
        "        unique_normalized = count_distinct(normalized)\n"
    )

    known_net = _aggregate_projection(relation, "known_net")
    unique_normalized = _aggregate_projection(relation, "unique_normalized")

    assert isinstance(known_net.arguments[0], BinaryIR)
    assert isinstance(unique_normalized.arguments[0], CallIR)
    assert not _field_refs_named(relation, {"gross", "net", "normalized"})


def test_cli_json_and_explain_shapes_remain_compatible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(
        tmp_path,
        "count_aggregate_let.pietto",
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        normalized = lower(trim(status))\n"
        "    select:\n"
        "        known_gross = count(gross)\n"
        "        unique_normalized = count_distinct(normalized)\n",
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
    ("binding", "projection", "expected_code"),
    [
        ("one = 1", "known = count(one)", "PIE-S2315"),
        ("label = status", "known = count_distinct(len(label))", "PIE-S2102"),
        ("gross = amount + tax", "known = count_distinct(gross)", "PIE-S2315"),
        ("raw_value = raw", "known = count_distinct(raw_value)", "PIE-S2314"),
        (
            "payload_value = payload",
            "known = count_distinct(payload_value)",
            "PIE-S2314",
        ),
        ("anything_value = anything", "known = count(anything_value)", "PIE-S2314"),
        ("enum_value = enum_status", "known = count(enum_value)", "PIE-S2314"),
        ("gross = amount + tax", "smallest = min(gross)", "PIE-S2102"),
        ("gross = amount + tax", "largest = max(gross)", "PIE-S2102"),
    ],
)
def test_unsupported_count_family_let_expansion_shapes_keep_existing_diagnostics(
    binding: str,
    projection: str,
    expected_code: str,
) -> None:
    semantic = _semantic_for(
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        f"        {binding}\n"
        "    select:\n"
        f"        {projection}\n"
    )

    assert _error_codes(semantic) == [expected_code]


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        gross\n"
            "    select:\n"
            "        status\n"
            "        known = count(amount)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        known = count(amount)\n"
            "    order by:\n"
            "        gross\n",
            "PIE-S2321",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        status\n"
            "    select:\n"
            "        status\n"
            "        known = count(amount)\n"
            "    satisfying:\n"
            "        gross > 0\n",
            "PIE-S2324",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        amount\n"
            "    limit gross\n",
            "PIE-S2307",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        known = count(orders.gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        gross = amount + tax\n"
            "        known = count(gross)\n",
            "PIE-S2102",
        ),
    ],
)
def test_non_slice3_let_consumers_remain_rejected(
    body: str,
    expected_code: str,
) -> None:
    semantic = _semantic_for("query aggregate_orders:\n" + body)

    assert expected_code in _error_codes(semantic)


def _semantic_for(source: str) -> SemanticResult:
    result = parse_source(SOURCE_PREFIX + source, path="phase43-slice3.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return analyze(result.ast)


def _relation_ast(semantic: SemanticResult) -> TableDef | QueryDef:
    for definition in semantic.model.relation_row_schemas:
        if definition.name == "aggregate_orders":
            return definition
    raise AssertionError("aggregate_orders relation not found")


def _relation_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> RelationIR:
    script_ir = _script_ir(source, prefix=prefix)
    relation = script_ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    return relation


def _script_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> ScriptIR:
    result = parse_source(prefix + source, path="phase43-slice3.pietto")
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


def _aggregate_projection(relation: RelationIR, name: str) -> AggregateCallIR:
    for projection in relation.projections:
        if projection.name != name:
            continue
        assert isinstance(projection.expression, AggregateCallIR)
        return projection.expression
    raise AssertionError(f"projection not found: {name}")


def _assert_field(
    field: RowField,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert field.resolved_type.name == expected_type
    assert field.nullability is expected_nullability


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


def _write_source(tmp_path: Path, filename: str, relation_source: str) -> Path:
    path = tmp_path / filename
    path.write_text(SOURCE_PREFIX + relation_source, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    return cast(dict[str, object], json.loads(captured.out))


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
