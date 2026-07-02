from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.ir import BinaryIR, ComparisonIR, FieldRefIR, RelationIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze
from pietto.sql import SqlArtifactKind, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


REPO_ROOT = Path(__file__).resolve().parents[1]
IR_SURFACE_PATHS = (
    REPO_ROOT / "src/pietto/ir/model.py",
    REPO_ROOT / "src/pietto/ir/builder.py",
    REPO_ROOT / "src/pietto/ir/lowering.py",
)

SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)
MYSQL_SOURCE_PREFIX = SOURCE_PREFIX.replace("postgres.table", "mysql.table")

SUPPORTED_RELATION = (
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

CHECK_JSON_KEYS = (
    "schema_version",
    "command",
    "ok",
    "path",
    "diagnostics",
    "cli_errors",
)
EMIT_JSON_KEYS = (
    "schema_version",
    "command",
    "ok",
    "path",
    "dialect",
    "diagnostics",
    "cli_errors",
    "artifacts",
    "output",
)
EXPLAIN_JSON_KEYS = (
    "artifact",
    "schema_version",
    "command",
    "ok",
    "path",
    "diagnostics",
    "metadata",
)


@pytest.mark.parametrize("keyword", ["table", "query"])
def test_table_and_query_supported_row_level_matrix_inline_expands(
    keyword: str,
) -> None:
    relation = _relation_ir(
        f"{keyword} enriched_orders:\n"
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


def test_supported_grouped_where_remains_pre_aggregate_row_scope() -> None:
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
        "        total = sum(amount)\n"
    )

    assert relation.filter is not None
    assert isinstance(relation.filter.expression, ComparisonIR)
    assert isinstance(relation.filter.expression.left, BinaryIR)
    assert not _field_refs_named(relation, {"gross"})


def test_supported_dependency_and_qualified_input_matrix_inline_expands() -> None:
    relation = _relation_ir(
        "query enriched_orders:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = orders.amount + orders.tax\n"
        "        net = gross - 5\n"
        "    select:\n"
        "        net_value = net\n"
        "    order by:\n"
        "        net\n"
    )

    projection = relation.projections[0].expression
    assert isinstance(projection, BinaryIR)
    assert projection.operator == "-"
    assert isinstance(projection.left, BinaryIR)
    assert {(ref.qualifier, ref.name) for ref in _field_refs(projection)} == {
        (("orders",), "amount"),
        (("orders",), "tax"),
    }
    assert isinstance(relation.order_by[0].expression, BinaryIR)
    assert not _field_refs_named(relation, {"gross", "net"})


def test_postgres_and_mysql_supported_matrix_emit_inline_sql() -> None:
    postgres_sql = _postgres_sql(SUPPORTED_RELATION)
    mysql_sql = _mysql_sql(SUPPORTED_RELATION)

    assert '"gross"' not in postgres_sql
    assert '("amount" + "tax") > 0' in postgres_sql
    assert '"amount" + "tax" AS "gross_value"' in postgres_sql
    assert "WITH " not in postgres_sql.upper()
    assert "FROM (SELECT" not in postgres_sql.upper()

    assert "`gross`" not in mysql_sql
    assert "(`amount` + `tax`) > 0" in mysql_sql
    assert "`amount` + `tax` AS `gross_value`" in mysql_sql
    assert "WITH " not in mysql_sql.upper()
    assert "FROM (SELECT" not in mysql_sql.upper()


def test_cli_json_output_and_explain_supported_matrix_is_schema_stable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(tmp_path, "supported.pietto", SUPPORTED_RELATION)

    assert cli.main(["check", str(path), "--format", "json"]) == 0
    check_document = _read_json(capsys)
    assert tuple(check_document) == CHECK_JSON_KEYS
    assert check_document["schema_version"] == 1
    assert check_document["ok"] is True
    assert check_document["diagnostics"] == []
    assert "let_scopes" not in json.dumps(check_document)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )
    emit_document = _read_json(capsys)
    assert tuple(emit_document) == EMIT_JSON_KEYS
    assert emit_document["schema_version"] == 1
    assert emit_document["ok"] is True
    assert emit_document["diagnostics"] == []
    artifacts = cast(list[dict[str, object]], emit_document["artifacts"])
    assert len(artifacts) == 1
    sql = cast(str, artifacts[0]["sql"])
    assert '"gross"' not in sql
    assert "let_scopes" not in json.dumps(emit_document)

    output = tmp_path / "supported.sql"
    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    captured = capsys.readouterr()
    output_sql = output.read_text(encoding="utf-8")
    assert captured.out == ""
    assert captured.err == ""
    assert '"gross"' not in output_sql
    assert "WITH " not in output_sql.upper()
    assert "FROM (SELECT" not in output_sql.upper()

    assert cli.main(["explain", str(path), "--format", "json"]) == 0
    explain_document = _read_json(capsys)
    assert tuple(explain_document) == EXPLAIN_JSON_KEYS
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert explain_document["schema_version"] == 1
    assert explain_document["ok"] is True
    assert explain_document["diagnostics"] == []
    assert "metadata" in explain_document
    assert "let_scopes" not in json.dumps(explain_document)


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        total = sum(gross)\n",
            "PIE-S2102",
            id="sum-let-argument",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        average = avg(gross)\n",
            "PIE-S2102",
            id="avg-let-argument",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        counted = count(gross)\n",
            "PIE-S2102",
            id="count-let-argument",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        distinct_count = count_distinct(gross)\n",
            "PIE-S2102",
            id="count-distinct-let-argument",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    group by:\n"
            "        gross\n"
            "    select:\n"
            "        status\n"
            "        total = sum(amount)\n",
            "PIE-S2102",
            id="group-by-let-name",
        ),
        pytest.param(
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
            id="satisfying-let-name",
        ),
        pytest.param(
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
            id="grouped-order-let-name",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        amount\n"
            "    limit gross\n",
            "PIE-S2307",
            id="limit-let-name",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        gross_value = orders.gross\n",
            "PIE-S2102",
            id="qualified-let-like-reference",
        ),
        pytest.param(
            "    from orders\n"
            "    select:\n"
            "        gross = amount + tax\n"
            "        net = gross - 5\n",
            "PIE-S2102",
            id="projection-alias-expression-leaf",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "        gross = amount - tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
            id="duplicate-let-name",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        amount = tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
            id="let-shadows-input-field",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        orders = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2329",
            id="let-shadows-source-name",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = amount + tax\n"
            "    select:\n"
            "        gross = amount\n",
            "PIE-S2329",
            id="projection-conflicts-with-let",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = net + tax\n"
            "        net = amount\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
            id="later-let-reference",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = gross + tax\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
            id="self-reference",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = net\n"
            "        net = gross\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2330",
            id="source-order-cycle-like-case",
        ),
        pytest.param(
            "    from orders\n"
            "    let:\n"
            "        gross = sum(amount)\n"
            "    select:\n"
            "        amount\n",
            "PIE-S2308",
            id="aggregate-call-inside-let",
        ),
    ],
)
def test_deferred_and_fail_closed_matrix_preserves_diagnostics(
    body: str,
    expected_code: str,
) -> None:
    semantic = _semantic_for("query boundary_matrix:\n" + body)
    codes = _error_codes(semantic)

    assert expected_code in codes
    assert "PIE-S2328" not in codes


def test_unsupported_aggregate_let_matrix_never_reaches_successful_ir() -> None:
    semantic = _semantic_for(
        "query boundary_matrix:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        total = sum(gross)\n"
    )

    assert "PIE-S2102" in _error_codes(semantic)
    assert semantic.diagnostics != ()


def test_ir_surface_has_no_let_or_relation_layer_nodes() -> None:
    combined_ir = "\n".join(
        path.read_text(encoding="utf-8") for path in IR_SURFACE_PATHS
    )

    assert "LetBindingIR" not in combined_ir
    assert "RelationLayerIR" not in combined_ir


def test_unsupported_matrix_emit_sql_json_and_output_fail_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_source(
        tmp_path,
        "unsupported.pietto",
        "query boundary_matrix:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = amount + tax\n"
        "    select:\n"
        "        total = sum(gross)\n",
    )
    missing_output = tmp_path / "missing.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(missing_output),
            ]
        )
        == 1
    )
    document = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])

    assert document["ok"] is False
    assert document["artifacts"] == []
    assert document["output"] == {"path": str(missing_output), "written": False}
    assert "PIE-S2102" in [diagnostic["code"] for diagnostic in diagnostics]
    assert "let_scopes" not in json.dumps(document)
    assert not missing_output.exists()

    existing_output = tmp_path / "existing.sql"
    existing_output.write_text("original SQL\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(existing_output),
            ]
        )
        == 1
    )
    text_failure = capsys.readouterr()
    assert "PIE-S2102" in text_failure.err
    assert existing_output.read_text(encoding="utf-8") == "original SQL\n"


def _relation_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> RelationIR:
    result = parse_source(prefix + source, path="boundary_matrix.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic = analyze(result.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(result.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    relation = ir_result.ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    return relation


def _semantic_for(source: str) -> SemanticResult:
    result = parse_source(SOURCE_PREFIX + source, path="boundary_matrix.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return analyze(result.ast)


def _postgres_sql(source: str) -> str:
    result = parse_source(SOURCE_PREFIX + source, path="boundary_matrix.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic = analyze(result.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(result.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    sql_result = emit_postgres_sql(ir_result.ir)
    assert sql_result.diagnostics == ()
    assert len(sql_result.artifacts) == 1
    assert sql_result.artifacts[0].kind is SqlArtifactKind.RELATION
    return sql_result.artifacts[0].sql


def _mysql_sql(source: str) -> str:
    result = parse_source(MYSQL_SOURCE_PREFIX + source, path="boundary_matrix.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic = analyze(result.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(result.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    sql_result = emit_mysql_sql(ir_result.ir)
    assert sql_result.diagnostics == ()
    assert len(sql_result.artifacts) == 1
    assert sql_result.artifacts[0].kind is SqlArtifactKind.RELATION
    return sql_result.artifacts[0].sql


def _error_codes(semantic: SemanticResult) -> list[str]:
    return [
        diagnostic.code
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
    assert not captured.out.endswith("\n\n")
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
