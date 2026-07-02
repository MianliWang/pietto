from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.ir import (
    BinaryIR,
    ComparisonIR,
    FieldRefIR,
    RelationIR,
    ScriptIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlArtifactKind, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)
MYSQL_SOURCE_PREFIX = SOURCE_PREFIX.replace("postgres.table", "mysql.table")


def test_ir_inline_expands_let_in_where_select_and_order_by() -> None:
    relation = _relation_ir(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    where gross > 0\n"
        "    select:\n"
        "        gross_value = gross\n"
        "    order by:\n"
        "        gross\n"
    )

    assert relation.filter is not None
    assert isinstance(relation.filter.expression, ComparisonIR)
    assert isinstance(relation.filter.expression.left, BinaryIR)
    assert isinstance(relation.projections[0].expression, BinaryIR)
    assert isinstance(relation.order_by[0].expression, BinaryIR)
    assert not _field_refs_named(relation, {"gross"})


def test_ir_inline_expands_grouped_where_without_aggregate_let_visibility() -> None:
    relation = _relation_ir(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    where gross > 0\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total_amount = sum(amount)\n"
    )

    assert relation.filter is not None
    assert isinstance(relation.filter.expression, ComparisonIR)
    assert isinstance(relation.filter.expression.left, BinaryIR)
    assert not _field_refs_named(relation, {"gross"})


def test_ir_recursively_expands_earlier_let_dependencies() -> None:
    relation = _relation_ir(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "        net = gross - 5\n"
        "    select:\n"
        "        net_value = net\n"
    )

    projection = relation.projections[0].expression
    assert isinstance(projection, BinaryIR)
    assert projection.operator == "-"
    assert isinstance(projection.left, BinaryIR)
    assert projection.left.operator == "+"
    assert not _field_refs_named(relation, {"gross", "net"})


def test_source_qualified_fields_inside_let_lower_to_qualified_field_refs() -> None:
    relation = _relation_ir(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = orders.amount + orders.tax\n"
        "    select:\n"
        "        gross_value = gross\n"
    )

    projection = relation.projections[0].expression
    assert isinstance(projection, BinaryIR)
    refs = _field_refs(projection)
    assert {(ref.qualifier, ref.name) for ref in refs} == {
        (("orders",), "amount"),
        (("orders",), "tax"),
    }


def test_no_let_or_layer_ir_surface_is_introduced() -> None:
    script_ir = _script_ir(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        gross_value = gross\n"
    )
    type_names = {type(node).__name__ for node in _walk_objects(script_ir)}

    assert "LetBindingIR" not in type_names
    assert "RelationLayerIR" not in type_names


def test_postgres_emit_sql_inlines_supported_let_expressions() -> None:
    sql = _postgres_sql(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    where gross > 0\n"
        "    select:\n"
        "        gross_value = gross\n"
        "    order by:\n"
        "        gross\n"
    )

    assert '"gross"' not in sql
    assert '("amount" + "tax") > 0' in sql
    assert '"amount" + "tax" AS "gross_value"' in sql
    assert 'ORDER BY\n    "amount" + "tax" ASC' in sql
    assert "WITH " not in sql.upper()
    assert "FROM (SELECT" not in sql.upper()


def test_mysql_emit_sql_inlines_supported_let_expressions_without_sql_changes() -> None:
    sql = _mysql_sql(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    where gross > 0\n"
        "    select:\n"
        "        gross_value = gross\n"
        "    order by:\n"
        "        gross\n"
    )

    assert "`gross`" not in sql
    assert "(`amount` + `tax`) > 0" in sql
    assert "`amount` + `tax` AS `gross_value`" in sql
    assert "ORDER BY\n    `amount` + `tax` ASC" in sql
    assert "WITH " not in sql.upper()
    assert "FROM (SELECT" not in sql.upper()


def test_cli_check_emit_sql_and_explain_succeed_for_supported_let(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(
        tmp_path,
        "supported.pietto",
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        gross_value = gross\n",
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
    emit_output = capsys.readouterr()
    emit_document = json.loads(emit_output.out)
    assert emit_output.err == ""
    assert emit_document["ok"] is True
    assert len(emit_document["artifacts"]) == 1
    assert emit_document["diagnostics"] == []

    assert cli.main(["explain", str(source_path), "--format", "json"]) == 0
    explain_output = capsys.readouterr()
    explain_document = json.loads(explain_output.out)
    assert explain_output.err == ""
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
            "        total = sum(gross)\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        average = avg(gross)\n",
            "PIE-S2102",
        ),
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
            "    satisfying:\n"
            "        gross > 0\n",
            "PIE-S2324",
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
            "    select:\n"
            "        amount\n"
            "    limit gross\n",
            "PIE-S2307",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "        net = orders.gross\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "        gross = amount - tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        amount = tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = gross + tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = net + tax\n"
            "        net = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    let:\n"
            "        gross = net\n"
            "        net = gross\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
        ),
        (
            "    from orders\n"
            "    select:\n"
            "        gross = amount + tax\n"
            "        net = gross - 5\n",
            "PIE-S2102",
        ),
    ],
)
def test_unsupported_let_cases_fail_closed_without_sql_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    body: str,
    expected_code: str,
) -> None:
    source_path = _write_source(tmp_path, "unsupported.pietto", "query bad:\n" + body)

    exit_code = cli.main(
        [
            "emit-sql",
            str(source_path),
            "--dialect",
            "postgres",
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()
    document = json.loads(captured.out)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert exit_code == 1
    assert captured.err == ""
    assert document["ok"] is False
    assert document["artifacts"] == []
    assert expected_code in codes
    assert "PIE-S2328" not in codes


def _script_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> ScriptIR:
    result = parse_source(prefix + source, path="let_ir_sql.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic = analyze(result.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(result.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation_ir(source: str) -> RelationIR:
    script_ir = _script_ir(source)
    relation = script_ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    return relation


def _postgres_sql(source: str) -> str:
    result = emit_postgres_sql(_script_ir(source))
    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].kind is SqlArtifactKind.RELATION
    return result.artifacts[0].sql


def _mysql_sql(source: str) -> str:
    result = emit_mysql_sql(_script_ir(source, prefix=MYSQL_SOURCE_PREFIX))
    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].kind is SqlArtifactKind.RELATION
    return result.artifacts[0].sql


def _write_source(tmp_path: Path, filename: str, relation_source: str) -> Path:
    path = tmp_path / filename
    path.write_text(SOURCE_PREFIX + relation_source, encoding="utf-8")
    return path


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


def _walk_objects(value: object) -> tuple[object, ...]:
    walked = [value]
    if isinstance(value, tuple):
        for item in value:
            walked.extend(_walk_objects(item))
    elif is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            walked.extend(_walk_objects(getattr(value, field.name)))
    return tuple(walked)
