from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ast_nodes import QueryDef, TableDef
from pietto.errors import Severity
from pietto.ir import FieldRefIR, RelationIR, ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, RowField, SemanticResult, analyze
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


def test_group_by_direct_field_row_let_is_semantically_accepted() -> None:
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
    )
    relation = _relation_ast(semantic)
    schema = semantic.model.relation_row_schemas[relation]

    assert _errors(semantic) == []
    assert list(schema.fields) == ["status", "total"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)


def test_group_by_qualified_and_chained_field_row_lets_are_semantically_accepted() -> (
    None
):
    semantic = _semantic_for(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        region_key = orders.region\n"
        "        bucket = region_key\n"
        "    group by:\n"
        "        bucket\n"
        "    select:\n"
        "        region = orders.region\n"
        "        total = count()\n"
    )
    relation = _relation_ast(semantic)
    schema = semantic.model.relation_row_schemas[relation]

    assert _errors(semantic) == []
    assert list(schema.fields) == ["region", "total"]
    _assert_field(schema.fields["region"], "Text", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)


def test_ir_group_keys_inline_expand_row_let_names_to_field_refs() -> None:
    relation = _relation_ir(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        status_key = status\n"
        "        region_key = orders.region\n"
        "        bucket = region_key\n"
        "    group by:\n"
        "        status_key\n"
        "        bucket\n"
        "    select:\n"
        "        status\n"
        "        region = orders.region\n"
        "        total = count()\n"
    )

    assert [(key.name, key.qualifier) for key in relation.group_keys] == [
        ("status", ()),
        ("region", ("orders",)),
    ]
    assert not _field_refs_named(relation, {"status_key", "region_key", "bucket"})


@pytest.mark.parametrize(
    ("prefix", "dialect", "expected_fragments", "forbidden"),
    [
        (
            SOURCE_PREFIX,
            "postgres",
            (
                'GROUP BY\n    "status"',
                'COUNT(*) AS "total"',
            ),
            ('"key"', "WITH ", "FROM (SELECT"),
        ),
        (
            MYSQL_SOURCE_PREFIX,
            "mysql",
            (
                "GROUP BY\n    `status`",
                "COUNT(*) AS `total`",
            ),
            ("`key`", "WITH ", "FROM (SELECT"),
        ),
    ],
)
def test_sql_inlines_group_by_row_let_without_hidden_layers(
    prefix: str,
    dialect: str,
    expected_fragments: tuple[str, str],
    forbidden: tuple[str, ...],
) -> None:
    sql = _sql_for(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
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


def test_cli_json_and_explain_shapes_remain_compatible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(
        tmp_path,
        "group_by_let.pietto",
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
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
            "        gross\n"
            "    select:\n"
            "        amount\n"
            "        total = count()\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        normalized = lower(trim(status))\n"
            "    group by:\n"
            "        normalized\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        one = 1\n"
            "    group by:\n"
            "        one\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2102",
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
            "    satisfying:\n"
            "        key > 0\n",
            "PIE-S2324",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        key = status\n"
            "    select:\n"
            "        amount\n"
            "    limit key\n",
            "PIE-S2307",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = status\n"
            "    group by:\n"
            "        orders.gross\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        key = status\n"
            "    group by:\n"
            "        key\n"
            "    select:\n"
            "        key\n"
            "        total = count()\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        key = status\n"
            "    select:\n"
            "        smallest = min(key)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        key = status\n"
            "    select:\n"
            "        largest = max(key)\n",
            "PIE-S2102",
        ),
    ],
)
def test_non_slice4_group_by_let_consumers_remain_rejected(
    body: str,
    expected_code: str,
) -> None:
    semantic = _semantic_for("query grouped_orders:\n" + body)

    assert expected_code in _error_codes(semantic)


def _semantic_for(source: str) -> SemanticResult:
    result = parse_source(SOURCE_PREFIX + source, path="phase43-slice4.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return analyze(result.ast)


def _relation_ast(semantic: SemanticResult) -> TableDef | QueryDef:
    for definition in semantic.model.relation_row_schemas:
        if definition.name == "grouped_orders":
            return definition
    raise AssertionError("grouped_orders relation not found")


def _relation_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> RelationIR:
    script_ir = _script_ir(source, prefix=prefix)
    relation = script_ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    return relation


def _script_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> ScriptIR:
    result = parse_source(prefix + source, path="phase43-slice4.pietto")
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
