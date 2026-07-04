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
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    discount: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float nullable\n"
    "    status: Text not null\n"
    "    active: Bool not null\n"
    "    price: Decimal not null\n"
    'source orders: Order is postgres.table("orders")\n'
)
MYSQL_SOURCE_PREFIX = SOURCE_PREFIX.replace("postgres.table", "mysql.table")


def test_sum_avg_row_let_arguments_are_semantically_accepted() -> None:
    semantic = _semantic_for(
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        net = gross - discount\n"
        "        weighted = score * weight\n"
        "    select:\n"
        "        total = sum(gross)\n"
        "        average_net = avg(net)\n"
        "        average_weighted = avg(weighted)\n"
    )
    relation = _relation_ast(semantic)
    schema = semantic.model.relation_row_schemas[relation]

    assert _errors(semantic) == []
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(
        schema.fields["average_net"],
        "Float",
        EffectiveNullability.NULLABLE,
    )
    _assert_field(
        schema.fields["average_weighted"],
        "Float",
        EffectiveNullability.NULLABLE,
    )


def test_grouped_sum_avg_row_let_arguments_are_semantically_accepted() -> None:
    semantic = _semantic_for(
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        weighted = score * weight\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = sum(gross)\n"
        "        average_weighted = avg(weighted)\n"
    )
    relation = _relation_ast(semantic)
    schema = semantic.model.relation_row_schemas[relation]

    assert _errors(semantic) == []
    assert list(schema.fields) == ["status", "total", "average_weighted"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NULLABLE)
    _assert_field(
        schema.fields["average_weighted"],
        "Float",
        EffectiveNullability.NULLABLE,
    )


@pytest.mark.parametrize(
    ("prefix", "dialect", "expected_fragments", "forbidden"),
    [
        (
            SOURCE_PREFIX,
            "postgres",
            (
                'SUM(("amount" + "tax")) AS "total"',
                'AVG((("amount" + "tax") - "discount")) AS "average_net"',
            ),
            ('"gross"', '"net"', "WITH ", "FROM (SELECT"),
        ),
        (
            MYSQL_SOURCE_PREFIX,
            "mysql",
            (
                "SUM((`amount` + `tax`)) AS `total`",
                "AVG(((`amount` + `tax`) - `discount`)) AS `average_net`",
            ),
            ("`gross`", "`net`", "WITH ", "FROM (SELECT"),
        ),
    ],
)
def test_sql_inlines_sum_avg_row_let_arguments_without_hidden_layers(
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
        "    select:\n"
        "        total = sum(gross)\n"
        "        average_net = avg(net)\n",
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


def test_ir_aggregate_arguments_inline_expand_row_let_names() -> None:
    relation = _relation_ir(
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        net = gross - discount\n"
        "    select:\n"
        "        total = sum(gross)\n"
        "        average_net = avg(net)\n"
    )

    total = _aggregate_projection(relation, "total")
    average_net = _aggregate_projection(relation, "average_net")

    assert isinstance(total.arguments[0], BinaryIR)
    assert isinstance(average_net.arguments[0], BinaryIR)
    assert not _field_refs_named(relation, {"gross", "net"})


def test_cli_json_and_explain_shapes_remain_compatible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(
        tmp_path,
        "aggregate_let.pietto",
        "query aggregate_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        total = sum(gross)\n",
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
            "    select:\n"
            "        counted = count(gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        label = status\n"
            "    select:\n"
            "        distinct_count = count_distinct(label)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        gross\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount)\n",
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
            "        total = sum(amount)\n"
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
            "        total = sum(amount)\n"
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
            "        total = sum(orders.gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        gross = amount + tax\n"
            "        total = sum(gross)\n",
            "PIE-S2102",
        ),
    ],
)
def test_non_slice2_let_consumers_remain_rejected(
    body: str,
    expected_code: str,
) -> None:
    semantic = _semantic_for("query aggregate_orders:\n" + body)

    assert expected_code in _error_codes(semantic)


@pytest.mark.parametrize(
    ("binding", "projection", "expected_code"),
    [
        ("one = 1", "total = sum(one)", "PIE-S2315"),
        ("ratio = amount / tax", "total = sum(ratio)", "PIE-S2315"),
        ("label = status", "total = sum(label)", "PIE-S2314"),
        ("flag = active", "average = avg(flag)", "PIE-S2314"),
    ],
)
def test_unsupported_sum_avg_let_expansion_shapes_keep_existing_diagnostics(
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


def _semantic_for(source: str) -> SemanticResult:
    result = parse_source(SOURCE_PREFIX + source, path="phase43-slice2.pietto")
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
    result = parse_source(prefix + source, path="phase43-slice2.pietto")
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
