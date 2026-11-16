from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import (
    AggregateCallIR,
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
from pietto.ir.model import OrderDirectionIR, OrderItemIR
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]

POSTGRES_INPUT = Path("tests/fixtures/phase21/postgres_group_by_aggregate.pietto")

MYSQL_INPUT = Path("tests/fixtures/phase21/mysql_group_by_aggregate.pietto")

SPAN = SourceSpan(
    path="phase21-group-by-hardening.pietto",
    line=1,
    column=1,
    end_line=1,
    end_column=2,
)

OWNER = SymbolId(SymbolNamespace.RELATION, "orders")

INT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)

FLOAT_NULLABLE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Float",
    canonical_name="Float",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NULLABLE,
)

TEXT_NON_NULL = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Text",
    canonical_name="Text",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)

DIALECT_CASES = (
    (POSTGRES_INPUT, "postgres", "postgres.table", 'FROM "grouped_orders"'),
    (MYSQL_INPUT, "mysql", "mysql.table", "FROM `grouped_orders`"),
)

INVALID_GROUPED_CASES = (
    (
        "duplicate_group_key",
        "    group by:\n"
        "        status\n"
        "        orders.status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        "PIE-S2317",
    ),
    (
        "unknown_group_key",
        "    group by:\n"
        "        missing\n"
        "    select:\n"
        "        missing\n"
        "        total = count()\n",
        "PIE-S2102",
    ),
    (
        "non_grouped_projection",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        customer_id\n"
        "        total = count()\n",
        "PIE-S2318",
    ),
    (
        "pure_grouping",
        "    group by:\n        status\n    select:\n        status\n",
        "PIE-S2320",
    ),
    (
        "grouped_order_by",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "    order by:\n"
        "        sum(amount) desc\n",
        "PIE-S2321",
    ),
    (
        "unaliased_aggregate",
        "    group by:\n        status\n    select:\n        status\n        count()\n",
        "PIE-S2313",
    ),
    (
        "nested_aggregate",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum(avg(amount))\n",
        "PIE-S2311",
    ),
    (
        "aggregate_composition",
        "    group by:\n        status\n    select:\n        status\n        revenue = sum(amount) if True else 1\n",
        "PIE-S2310",
    ),
    (
        "wrong_arity",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum()\n",
        "PIE-S2309",
    ),
    (
        "wrong_type",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum(status)\n",
        "PIE-S2314",
    ),
    (
        "aggregate_expression_argument",
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        revenue = sum(1)\n",
        "PIE-S2315",
    ),
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

EXPRESSION_ARGUMENT_SHAPE = (
    "shape Order:\n"
    "    status: Text\n"
    "    region: Text\n"
    "    amount: Int\n"
    "    tax: Int\n"
    "    score: Float\n"
    "    weight: Float\n"
    "    price: Decimal\n"
)

EXPRESSION_ARGUMENT_NO_GROUP_SELECT_BODY = (
    "total = sum(amount + tax)\n"
    "        weighted = avg(score * weight)\n"
    "        normalized = count_distinct(lower(status))\n"
    "        normalized_trimmed = count_distinct(lower(trim(status)))"
)

EXPRESSION_ARGUMENT_POSTGRES_NO_GROUP_SQL = (
    "SELECT\n"
    '    CAST(SUM(CAST(("amount" + "tax") AS pg_catalog.int8)) AS pg_catalog.int8) AS "total",\n'
    '    AVG(("score" * "weight")) AS "weighted",\n'
    '    COUNT(DISTINCT lower("status")) AS "normalized",\n'
    '    COUNT(DISTINCT lower(trim("status"))) AS "normalized_trimmed"\n'
    'FROM "orders"'
)

EXPRESSION_ARGUMENT_MYSQL_NO_GROUP_SQL = (
    "SELECT\n"
    "    SUM((`amount` + `tax`)) AS `total`,\n"
    "    AVG((`score` * `weight`)) AS `weighted`,\n"
    "    COUNT(DISTINCT LOWER(`status`)) AS `normalized`,\n"
    "    COUNT(DISTINCT LOWER(TRIM(`status`))) AS `normalized_trimmed`\n"
    "FROM `orders`"
)

EXPRESSION_ARGUMENT_POSTGRES_GROUPED_SQL = (
    "SELECT\n"
    '    "region" AS "region",\n'
    '    CAST(SUM(CAST(("amount" + "tax") AS pg_catalog.int8)) AS pg_catalog.int8) AS "total",\n'
    '    COUNT(DISTINCT lower(trim("status"))) AS "normalized"\n'
    'FROM "orders"\n'
    "GROUP BY\n"
    '    "region"'
)

EXPRESSION_ARGUMENT_MYSQL_GROUPED_SQL = (
    "SELECT\n"
    "    `region` AS `region`,\n"
    "    SUM((`amount` + `tax`)) AS `total`,\n"
    "    COUNT(DISTINCT LOWER(TRIM(`status`))) AS `normalized`\n"
    "FROM `orders`\n"
    "GROUP BY\n"
    "    `region`"
)

POSTGRES_TOTAL_HAVING_SQL = EXPRESSION_ARGUMENT_POSTGRES_GROUPED_SQL + (
    '\nHAVING\n    CAST(SUM(CAST(("amount" + "tax") AS pg_catalog.int8)) AS pg_catalog.int8) > 1000'
)

MYSQL_TOTAL_HAVING_SQL = EXPRESSION_ARGUMENT_MYSQL_GROUPED_SQL + (
    "\nHAVING\n    SUM((`amount` + `tax`)) > 1000"
)

POSTGRES_NORMALIZED_HAVING_SQL = EXPRESSION_ARGUMENT_POSTGRES_GROUPED_SQL + (
    '\nHAVING\n    COUNT(DISTINCT lower(trim("status"))) > 10'
)

MYSQL_NORMALIZED_HAVING_SQL = EXPRESSION_ARGUMENT_MYSQL_GROUPED_SQL + (
    "\nHAVING\n    COUNT(DISTINCT LOWER(TRIM(`status`))) > 10"
)

COUNT_EXPRESSION_SHAPE = (
    "shape Order:\n"
    "    region: Text\n"
    "    status: Text\n"
    "    active: Bool\n"
    "    optional_active: Bool | None\n"
    "    amount: Int\n"
    "    tax: Int\n"
)

COUNT_EXPRESSION_NO_GROUP_SELECT_BODY = (
    "amount_tax = count(amount + tax)\n"
    "        amount_one = count(amount + 1)\n"
    "        lowered = count(lower(status))\n"
    "        active_count = count(active and True)"
)

COUNT_EXPRESSION_POSTGRES_NO_GROUP_SQL = (
    "SELECT\n"
    '    COUNT(("amount" + "tax")) AS "amount_tax",\n'
    '    COUNT(("amount" + 1)) AS "amount_one",\n'
    '    COUNT(lower("status")) AS "lowered",\n'
    '    COUNT(("active" AND TRUE)) AS "active_count"\n'
    'FROM "orders"'
)

COUNT_EXPRESSION_MYSQL_NO_GROUP_SQL = (
    "SELECT\n"
    "    COUNT((`amount` + `tax`)) AS `amount_tax`,\n"
    "    COUNT((`amount` + 1)) AS `amount_one`,\n"
    "    COUNT(LOWER(`status`)) AS `lowered`,\n"
    "    COUNT((`active` AND TRUE)) AS `active_count`\n"
    "FROM `orders`"
)

COUNT_EXPRESSION_POSTGRES_GROUPED_SQL = (
    "SELECT\n"
    '    "region" AS "region",\n'
    '    COUNT(("amount" + "tax")) AS "amount_tax",\n'
    '    COUNT(lower("status")) AS "lowered",\n'
    '    COUNT(("active" OR "optional_active")) AS "active_count"\n'
    'FROM "orders"\n'
    "GROUP BY\n"
    '    "region"'
)

COUNT_EXPRESSION_MYSQL_GROUPED_SQL = (
    "SELECT\n"
    "    `region` AS `region`,\n"
    "    COUNT((`amount` + `tax`)) AS `amount_tax`,\n"
    "    COUNT(LOWER(`status`)) AS `lowered`,\n"
    "    COUNT((`active` OR `optional_active`)) AS `active_count`\n"
    "FROM `orders`\n"
    "GROUP BY\n"
    "    `region`"
)

GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"

COUNT_FIELD_POSTGRES_INPUT = Path(
    "tests/fixtures/phase23/postgres_count_field_aggregate.pietto"
)

COUNT_FIELD_MYSQL_INPUT = Path(
    "tests/fixtures/phase23/mysql_count_field_aggregate.pietto"
)

COUNT_FIELD_POSTGRES_GROUPED_INPUT = Path(
    "tests/fixtures/phase23/postgres_grouped_count_field_aggregate.pietto"
)

COUNT_FIELD_MYSQL_GROUPED_INPUT = Path(
    "tests/fixtures/phase23/mysql_grouped_count_field_aggregate.pietto"
)

POSTGRES_GOLDEN = "emit_sql_count_field_aggregate.sql"

MYSQL_GOLDEN = "emit_mysql_count_field_aggregate.sql"

POSTGRES_GROUPED_GOLDEN = "emit_sql_grouped_count_field_aggregate.sql"

MYSQL_GROUPED_GOLDEN = "emit_mysql_grouped_count_field_aggregate.sql"

COUNT_FIELD_CLI_CASES: tuple[tuple[Path, str, str, str], ...] = (
    (COUNT_FIELD_POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN, "order_completeness"),
    (COUNT_FIELD_MYSQL_INPUT, "mysql", MYSQL_GOLDEN, "order_completeness"),
    (
        COUNT_FIELD_POSTGRES_GROUPED_INPUT,
        "postgres",
        POSTGRES_GROUPED_GOLDEN,
        "order_completeness_by_status",
    ),
    (
        COUNT_FIELD_MYSQL_GROUPED_INPUT,
        "mysql",
        MYSQL_GROUPED_GOLDEN,
        "order_completeness_by_status",
    ),
)

COUNT_FIELD_OUTPUT_CASES: tuple[tuple[Path, str, str, str], ...] = (
    (COUNT_FIELD_POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN, "order_completeness"),
    (COUNT_FIELD_MYSQL_INPUT, "mysql", MYSQL_GOLDEN, "order_completeness"),
)

SOURCE_SHAPE = (
    "shape Order:\n"
    "    region: Text\n"
    "    status: Text\n"
    "    amount: Int\n"
    "    tax: Int\n"
    "    score: Float\n"
    "    weight: Float\n"
)

GROUPED_ORDER_POSTGRES_SQL = (
    "SELECT\n"
    '    "region" AS "region",\n'
    '    CAST(SUM(CAST(("amount" + "tax") AS pg_catalog.int8)) AS pg_catalog.int8) AS "total"\n'
    'FROM "orders"\n'
    "GROUP BY\n"
    '    "region"\n'
    "HAVING\n"
    '    CAST(SUM(CAST(("amount" + "tax") AS pg_catalog.int8)) AS pg_catalog.int8) > 1000\n'
    "ORDER BY\n"
    '    CAST(SUM(CAST(("amount" + "tax") AS pg_catalog.int8)) AS pg_catalog.int8) DESC,\n'
    '    "region" ASC\n'
    "LIMIT 10"
)

GROUPED_ORDER_MYSQL_SQL = (
    "SELECT\n"
    "    `region` AS `region`,\n"
    "    SUM((`amount` + `tax`)) AS `total`\n"
    "FROM `orders`\n"
    "GROUP BY\n"
    "    `region`\n"
    "HAVING\n"
    "    SUM((`amount` + `tax`)) > 1000\n"
    "ORDER BY\n"
    "    SUM((`amount` + `tax`)) DESC,\n"
    "    `region` ASC\n"
    "LIMIT 10"
)

NUMERIC_LITERAL_POSTGRES_SQL = (
    "SELECT\n"
    '    "region" AS "region",\n'
    '    CAST(SUM(CAST(("amount" + 1) AS pg_catalog.int8)) AS pg_catalog.int8) AS "total",\n'
    '    AVG(("score" * 2)) AS "average"\n'
    'FROM "orders"\n'
    "GROUP BY\n"
    '    "region"\n'
    "HAVING\n"
    '    CAST(SUM(CAST(("amount" + 1) AS pg_catalog.int8)) AS pg_catalog.int8) > 1000\n'
    "ORDER BY\n"
    '    AVG(("score" * 2)) DESC,\n'
    '    CAST(SUM(CAST(("amount" + 1) AS pg_catalog.int8)) AS pg_catalog.int8) ASC\n'
    "LIMIT 10"
)

NUMERIC_LITERAL_MYSQL_SQL = (
    "SELECT\n"
    "    `region` AS `region`,\n"
    "    SUM((`amount` + 1)) AS `total`,\n"
    "    AVG((`score` * 2)) AS `average`\n"
    "FROM `orders`\n"
    "GROUP BY\n"
    "    `region`\n"
    "HAVING\n"
    "    SUM((`amount` + 1)) > 1000\n"
    "ORDER BY\n"
    "    AVG((`score` * 2)) DESC,\n"
    "    SUM((`amount` + 1)) ASC\n"
    "LIMIT 10"
)


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
def test_valid_grouped_check_succeeds_for_both_dialects(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del dialect, connector, expected_from
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["check", str(input_path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {input_path}\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
def test_valid_grouped_emit_sql_text_and_json_smoke(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del connector, expected_from
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", str(input_path), "--dialect", dialect]) == 0
    text = capsys.readouterr()
    assert text.err == ""
    assert "GROUP BY" in text.out
    assert "COUNT(*)" in text.out

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                dialect,
                "--format",
                "json",
            ]
        )
        == 0
    )
    result = _read_json(capsys)
    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert len(artifacts) == 1
    assert "GROUP BY" in cast(str, artifacts[0]["sql"])


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
def test_valid_grouped_emit_sql_output_writes_sql_and_suppresses_stdout(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del connector, expected_from
    output_path = tmp_path / f"{dialect}-grouped.sql"
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                dialect,
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert "GROUP BY" in output_path.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "dialect,connector", [("postgres", "postgres.table"), ("mysql", "mysql.table")]
)
def test_admitted_grouped_scalar_json_output_writes_sql(
    dialect: str,
    connector: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = tmp_path / f"{dialect}-grouped-scalar.pietto"
    output_path = tmp_path / f"{dialect}-grouped-scalar.sql"
    source_path.write_text(
        _grouped_source(
            connector,
            "    group by:\n        status\n    select:\n"
            "        label = lower(status)\n        total = count()\n",
        ),
        encoding="utf-8",
    )
    output_path.write_text("existing SQL\n", encoding="utf-8")
    assert (
        cli.main(
            [
                "emit-sql",
                str(source_path),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )
    document = _read_json(capsys)
    assert document["ok"] is True
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    assert document["output"] == {"path": str(output_path), "written": True}
    artifacts = cast(list[dict[str, object]], document["artifacts"])
    assert len(artifacts) == 1
    written = output_path.read_text(encoding="utf-8")
    assert cast(str, artifacts[0]["sql"]) in written
    assert "existing SQL" not in written


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
@pytest.mark.parametrize(("case_name", "body", "expected_code"), INVALID_GROUPED_CASES)
def test_invalid_grouped_emit_sql_json_output_fails_before_sql_without_writing(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    case_name: str,
    body: str,
    expected_code: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del input_path, expected_from
    source_path = tmp_path / f"{dialect}-{case_name}.pietto"
    output_path = tmp_path / f"{dialect}-{case_name}.sql"
    output_path.write_text("existing SQL\n", encoding="utf-8")
    source_path.write_text(_grouped_source(connector, body), encoding="utf-8")
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(source_path),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    assert result["artifacts"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "existing SQL\n"
    assert codes == [expected_code]
    assert expected_code.startswith("PIE-S")
    assert "PIE-S2316" not in codes
    assert "PIE-B1000" not in codes


@pytest.mark.parametrize(
    ("input_path", "dialect", "connector", "expected_from"), DIALECT_CASES
)
def test_downstream_from_grouped_cli_json_defines_the_grouped_relation_as_a_cte(
    input_path: Path,
    dialect: str,
    connector: str,
    expected_from: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del input_path
    path = tmp_path / f"{dialect}-downstream-grouped.pietto"
    path.write_text(_grouped_chain_source(connector), encoding="utf-8")
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format",
                "json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    downstream_sql = cast(str, artifacts[1]["sql"])

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert [artifact["name"] for artifact in artifacts] == [
        "grouped_orders",
        "downstream",
    ]
    assert expected_from in downstream_sql
    quote = '"' if dialect == "postgres" else "`"
    assert downstream_sql.startswith(
        f"WITH {quote}grouped_orders{quote} AS (\n{artifacts[0]['sql']}\n)\nSELECT\n"
    )
    assert downstream_sql.count("SELECT") == 2
    assert downstream_sql.count("GROUP BY") == 1
    assert "(SELECT" not in downstream_sql
    assert "FROM (" not in downstream_sql


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
        "unresolved_group_key",
        "non_field_group_key",
        "duplicate_group_key",
        "grouped_order_by",
        "non_grouped_projection",
        "pure_grouped_output",
        "unsupported_aggregate",
    ],
)
def test_malformed_grouped_ir_direct_emitters_fail_closed_with_pie_b1000(
    input_path: Path,
    emitter: Callable[[ScriptIR], SqlResult],
    case: str,
) -> None:
    script_ir = _compile(input_path)
    relation = _relation_ir(script_ir, "revenue_by_status")
    bad_relation = _malformed_grouped_relation(relation, case)
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emitter(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", EXPRESSION_ARGUMENT_POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", EXPRESSION_ARGUMENT_MYSQL_NO_GROUP_SQL),
    ],
)
def test_cli_text_emits_supported_expression_argument_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-aggregate-expression-arguments.pietto",
        _expression_argument_source(
            connector, EXPRESSION_ARGUMENT_NO_GROUP_SELECT_BODY
        ),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == f"-- aggregate_stats\n{expected_sql};\n"


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", EXPRESSION_ARGUMENT_POSTGRES_GROUPED_SQL),
        ("mysql", "mysql.table", EXPRESSION_ARGUMENT_MYSQL_GROUPED_SQL),
    ],
)
def test_cli_text_emits_grouped_supported_expression_argument_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-grouped-aggregate-expression-arguments.pietto",
        _expression_argument_source(
            connector, _expression_argument_grouped_select_body(), grouped=True
        ),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == f"-- aggregate_stats\n{expected_sql};\n"


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", EXPRESSION_ARGUMENT_POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", EXPRESSION_ARGUMENT_MYSQL_NO_GROUP_SQL),
    ],
)
def test_cli_json_success_preserves_v1_shape_for_expression_arguments(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-aggregate-expression-arguments.pietto",
        _expression_argument_source(
            connector, EXPRESSION_ARGUMENT_NO_GROUP_SELECT_BODY
        ),
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

    assert set(result) == EMIT_SQL_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["path"] == str(path)
    assert result["dialect"] == dialect
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": "aggregate_stats",
            "sql": expected_sql,
        }
    ]
    assert set(artifacts[0]) == {"kind", "name", "sql"}
    for forbidden_key in ("schema_version_v2", "project", "project_root", "files"):
        assert forbidden_key not in result


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", EXPRESSION_ARGUMENT_POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", EXPRESSION_ARGUMENT_MYSQL_NO_GROUP_SQL),
    ],
)
def test_cli_text_output_replaces_file_with_supported_expression_argument_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-aggregate-expression-arguments.pietto",
        _expression_argument_source(
            connector, EXPRESSION_ARGUMENT_NO_GROUP_SELECT_BODY
        ),
    )
    output_path = _write(tmp_path, f"{dialect}.sql", "stale SQL\n")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert (
        output_path.read_text(encoding="utf-8")
        == f"-- aggregate_stats\n{expected_sql};\n"
    )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", EXPRESSION_ARGUMENT_POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", EXPRESSION_ARGUMENT_MYSQL_NO_GROUP_SQL),
    ],
)
def test_cli_json_output_writes_file_and_keeps_expression_argument_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-aggregate-expression-arguments.pietto",
        _expression_argument_source(
            connector, EXPRESSION_ARGUMENT_NO_GROUP_SELECT_BODY
        ),
    )
    output_path = _write(tmp_path, f"{dialect}-json.sql", "stale SQL\n")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format=json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    assert artifacts == [
        {
            "kind": "relation",
            "name": "aggregate_stats",
            "sql": expected_sql,
        }
    ]
    assert (
        output_path.read_text(encoding="utf-8")
        == f"-- aggregate_stats\n{expected_sql};\n"
    )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = sum(amount / tax)", "PIE-S2315"),
        ("value = sum(amount % tax)", "PIE-S2315"),
        ("value = count_distinct(len(status))", "PIE-S2315"),
        ("value = count_distinct(lower(amount))", "PIE-S2315"),
        # Phase 39 Slice 3 accepts "value = count(amount + tax)" semantically.
        ("value = count(1)", "PIE-S2315"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(score * weight)", "PIE-S2315"),
        ("value = sum(avg(amount))", "PIE-S2311"),
        ("value = sum(amount) if True else 1", "PIE-S2310"),
    ],
)
def test_unsupported_expression_argument_json_output_does_not_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    projection: str,
    expected_code: str,
) -> None:
    path = _write(
        tmp_path,
        "unsupported-aggregate-expression-argument.pietto",
        _expression_argument_source("postgres.table", projection),
    )
    output_path = _write(tmp_path, "unsupported.sql", "old SQL\n")
    _forbid_ir_and_sql(monkeypatch)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    # A `/` of two Int values also warns that it truncates (PIE-S2106).
    assert codes == [expected_code, *(["PIE-S2106"] if "/" in projection else [])]
    assert "PIE-B1000" not in codes
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "old SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("dialect", "connector", "satisfying", "expected_sql", "forbidden_alias"),
    [
        (
            "postgres",
            "postgres.table",
            "total > 1000",
            POSTGRES_TOTAL_HAVING_SQL,
            '"total" > 1000',
        ),
        (
            "mysql",
            "mysql.table",
            "total > 1000",
            MYSQL_TOTAL_HAVING_SQL,
            "`total` > 1000",
        ),
        (
            "postgres",
            "postgres.table",
            "normalized > 10",
            POSTGRES_NORMALIZED_HAVING_SQL,
            '"normalized" > 10',
        ),
        (
            "mysql",
            "mysql.table",
            "normalized > 10",
            MYSQL_NORMALIZED_HAVING_SQL,
            "`normalized` > 10",
        ),
    ],
)
def test_cli_text_grouped_satisfying_uses_underlying_aggregate_expression(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    satisfying: str,
    expected_sql: str,
    forbidden_alias: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-satisfying-aggregate-expression-argument.pietto",
        _expression_argument_source(
            connector,
            _expression_argument_grouped_select_body(),
            grouped=True,
            satisfying=satisfying,
        ),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == f"-- aggregate_stats\n{expected_sql};\n"
    having = _having_clause(captured.out)
    assert forbidden_alias not in having


@pytest.mark.parametrize(
    ("satisfying", "expected_code"),
    [
        ("sum(amount + tax) > 1000", "PIE-S2308"),
        ("count_distinct(lower(trim(status))) > 10", "PIE-S2308"),
        ("total > 1000", "PIE-S2323"),
    ],
)
def test_invalid_satisfying_expression_argument_boundaries_do_not_write_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    satisfying: str,
    expected_code: str,
) -> None:
    grouped = expected_code != "PIE-S2323"
    path = _write(
        tmp_path,
        "invalid-satisfying-aggregate-expression-argument.pietto",
        _expression_argument_source(
            "postgres.table",
            _expression_argument_grouped_select_body()
            if grouped
            else "total = sum(amount + tax)",
            grouped=grouped,
            satisfying=satisfying,
        ),
    )
    output_path = _write(tmp_path, "invalid-satisfying.sql", "old SQL\n")
    _forbid_ir_and_sql(monkeypatch)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    assert codes == [expected_code]
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "old SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", COUNT_EXPRESSION_POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", COUNT_EXPRESSION_MYSQL_NO_GROUP_SQL),
    ],
)
def test_cli_text_emits_count_expression_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-count-expression.pietto",
        _count_expression_source(connector, COUNT_EXPRESSION_NO_GROUP_SELECT_BODY),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == f"-- aggregate_stats\n{expected_sql};\n"


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", COUNT_EXPRESSION_POSTGRES_GROUPED_SQL),
        ("mysql", "mysql.table", COUNT_EXPRESSION_MYSQL_GROUPED_SQL),
    ],
)
def test_cli_text_emits_grouped_count_expression_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-grouped-count-expression.pietto",
        _count_expression_source(
            connector, _count_expression_grouped_select_body(), grouped=True
        ),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == f"-- aggregate_stats\n{expected_sql};\n"


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", COUNT_EXPRESSION_POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", COUNT_EXPRESSION_MYSQL_NO_GROUP_SQL),
    ],
)
def test_cli_json_success_preserves_v1_shape_for_count_expression(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-count-expression-json.pietto",
        _count_expression_source(connector, COUNT_EXPRESSION_NO_GROUP_SELECT_BODY),
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

    assert set(result) == EMIT_SQL_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["path"] == str(path)
    assert result["dialect"] == dialect
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    assert artifacts == [
        {
            "kind": "relation",
            "name": "aggregate_stats",
            "sql": expected_sql,
        }
    ]
    assert set(artifacts[0]) == {"kind", "name", "sql"}
    _assert_no_json_schema_expansion(result)


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", COUNT_EXPRESSION_POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", COUNT_EXPRESSION_MYSQL_NO_GROUP_SQL),
    ],
)
def test_cli_text_output_writes_count_expression_sql_on_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-count-expression-output.pietto",
        _count_expression_source(connector, COUNT_EXPRESSION_NO_GROUP_SELECT_BODY),
    )
    output_path = _write(tmp_path, f"{dialect}-count-expression.sql", "stale SQL\n")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert (
        output_path.read_text(encoding="utf-8")
        == f"-- aggregate_stats\n{expected_sql};\n"
    )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", COUNT_EXPRESSION_POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", COUNT_EXPRESSION_MYSQL_NO_GROUP_SQL),
    ],
)
def test_cli_json_output_writes_count_expression_sql_and_keeps_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-count-expression-json-output.pietto",
        _count_expression_source(connector, COUNT_EXPRESSION_NO_GROUP_SELECT_BODY),
    )
    output_path = _write(
        tmp_path,
        f"{dialect}-count-expression-json.sql",
        "stale SQL\n",
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format=json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    assert artifacts == [
        {
            "kind": "relation",
            "name": "aggregate_stats",
            "sql": expected_sql,
        }
    ]
    assert (
        output_path.read_text(encoding="utf-8")
        == f"-- aggregate_stats\n{expected_sql};\n"
    )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = count(1)", "PIE-S2315"),
        ("value = count(amount > 1)", "PIE-S2315"),
        ("value = count_if(active)", "PIE-S2103"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(amount + tax)", "PIE-S2315"),
        ("value = count(count())", "PIE-S2311"),
        ("value = count(amount) if True else 1", "PIE-S2310"),
    ],
)
def test_deferred_count_expression_forms_do_not_write_json_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    projection: str,
    expected_code: str,
) -> None:
    path = _write(
        tmp_path,
        "deferred-count-expression-form.pietto",
        _count_expression_source("postgres.table", projection),
    )
    output_path = _write(tmp_path, "deferred-count-expression.sql", "old SQL\n")
    _forbid_ir_and_sql(monkeypatch)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    codes = [diagnostic["code"] for diagnostic in diagnostics]

    assert result["ok"] is False
    assert codes == [expected_code]
    assert "PIE-B1000" not in codes
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "old SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name", "artifact_name"),
    COUNT_FIELD_CLI_CASES,
)
def test_cli_text_count_field_sql_matches_reviewed_golden(
    input_path: Path,
    dialect: str,
    golden_name: str,
    artifact_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del artifact_name
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", input_path.as_posix(), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name", "artifact_name"),
    COUNT_FIELD_CLI_CASES,
)
def test_cli_json_count_field_sql_success_preserves_v1_shape(
    input_path: Path,
    dialect: str,
    golden_name: str,
    artifact_name: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                input_path.as_posix(),
                "--dialect",
                dialect,
                "--format",
                "json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)

    assert set(result) == EMIT_SQL_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["path"] == str(input_path)  # the platform's spelling
    assert result["dialect"] == dialect
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": artifact_name,
            "sql": _golden_sql(golden_name),
        }
    ]
    assert set(artifacts[0]) == {"kind", "name", "sql"}


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name", "artifact_name"),
    COUNT_FIELD_OUTPUT_CASES,
)
def test_cli_text_count_field_output_writes_exact_sql(
    input_path: Path,
    dialect: str,
    golden_name: str,
    artifact_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del artifact_name
    output_path = tmp_path / f"{dialect}-count-field.sql"
    output_path.write_text("stale SQL\n", encoding="utf-8")
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                input_path.as_posix(),
                "--dialect",
                dialect,
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert output_path.read_bytes() == _golden_bytes(golden_name)
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    ("input_path", "dialect", "golden_name", "artifact_name"),
    COUNT_FIELD_OUTPUT_CASES,
)
def test_cli_json_count_field_output_writes_exact_sql_and_keeps_artifacts(
    input_path: Path,
    dialect: str,
    golden_name: str,
    artifact_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / f"{dialect}-count-field-json.sql"
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                input_path.as_posix(),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = _read_json(capsys)

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": artifact_name,
            "sql": _golden_sql(golden_name),
        }
    ]
    assert output_path.read_bytes() == _golden_bytes(golden_name)
    assert not tuple(tmp_path.glob("*.tmp"))


def test_cli_text_count_field_semantic_error_stops_before_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = _write_invalid_count_field_source(tmp_path)

    assert cli.main(["emit-sql", str(input_path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2309 error:" in captured.err
    assert "PIE-B1000" not in captured.err


def test_cli_json_count_field_semantic_error_does_not_write_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = _write_invalid_count_field_source(tmp_path)
    output_path = tmp_path / "invalid-count-field.sql"
    output_path.write_text("original SQL\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "emit-sql",
                str(input_path),
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])

    assert result["ok"] is False
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2309"]
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "original SQL\n"


def test_cli_json_count_field_backend_error_does_not_write_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / "backend-error.sql"
    output_path.write_text("original SQL\n", encoding="utf-8")
    diagnostic = Diagnostic(
        code="PIE-B1000",
        severity=Severity.ERROR,
        message="unsupported backend case",
        location=SourceLocation(
            path=COUNT_FIELD_POSTGRES_INPUT.as_posix(),
            line=1,
            column=1,
            end_line=1,
            end_column=1,
        ),
    )

    def emit_backend_error(script_ir: ScriptIR) -> SqlResult:
        del script_ir
        return SqlResult(artifacts=(), diagnostics=(diagnostic,))

    monkeypatch.chdir(REPO_ROOT)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", emit_backend_error)

    assert (
        cli.main(
            [
                "emit-sql",
                COUNT_FIELD_POSTGRES_INPUT.as_posix(),
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])

    assert result["ok"] is False
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-B1000"]
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "original SQL\n"


def test_check_accepts_grouped_result_ordering(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "grouped-order-check.pietto",
        _grouped_order_source("postgres.table"),
    )

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql", "forbidden_order_alias"),
    [
        ("postgres", "postgres.table", GROUPED_ORDER_POSTGRES_SQL, '"total"'),
        ("mysql", "mysql.table", GROUPED_ORDER_MYSQL_SQL, "`total`"),
    ],
)
def test_text_emit_sql_carries_grouped_result_ordering(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
    forbidden_order_alias: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-grouped-order.pietto",
        _grouped_order_source(connector),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"-- grouped_orders\n{expected_sql};\n"
    assert captured.err == ""
    _assert_clause_order(captured.out)
    assert forbidden_order_alias not in _order_by_clause(captured.out)


def test_json_emit_sql_preserves_v1_shape_with_grouped_result_ordering(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "postgres-grouped-order-json.pietto",
        _grouped_order_source("postgres.table"),
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert set(result) == EMIT_SQL_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["path"] == str(path)
    assert result["dialect"] == "postgres"
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    assert artifacts == [
        {
            "kind": "relation",
            "name": "grouped_orders",
            "sql": GROUPED_ORDER_POSTGRES_SQL,
        }
    ]
    assert set(artifacts[0]) == {"kind", "name", "sql"}
    _assert_no_json_schema_expansion(result)
    _assert_clause_order(cast(str, artifacts[0]["sql"]))
    assert '"total"' not in _order_by_clause(cast(str, artifacts[0]["sql"]))


def test_text_output_writes_grouped_order_sql_on_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "postgres-grouped-order-output.pietto",
        _grouped_order_source("postgres.table"),
    )
    output_path = _write(tmp_path, "grouped-order.sql", "stale SQL\n")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert (
        output_path.read_text(encoding="utf-8")
        == f"-- grouped_orders\n{GROUPED_ORDER_POSTGRES_SQL};\n"
    )
    assert not tuple(tmp_path.glob("*.tmp"))


def test_json_output_writes_grouped_order_sql_and_keeps_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "postgres-grouped-order-json-output.pietto",
        _grouped_order_source("postgres.table"),
    )
    output_path = _write(tmp_path, "grouped-order-json.sql", "stale SQL\n")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    assert artifacts == [
        {
            "kind": "relation",
            "name": "grouped_orders",
            "sql": GROUPED_ORDER_POSTGRES_SQL,
        }
    ]
    assert (
        output_path.read_text(encoding="utf-8")
        == f"-- grouped_orders\n{GROUPED_ORDER_POSTGRES_SQL};\n"
    )
    assert not tuple(tmp_path.glob("*.tmp"))


def test_invalid_grouped_order_text_fails_before_sql_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "invalid-grouped-order.pietto",
        _unsupported_grouped_order_source("postgres.table"),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2321 error:" in captured.err
    assert "Unsupported grouped ORDER BY item" in captured.err
    assert "SELECT\n" not in captured.err


def test_invalid_grouped_order_json_fails_without_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "invalid-grouped-order-json.pietto",
        _unsupported_grouped_order_source("postgres.table"),
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])

    assert result["ok"] is False
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2321"]
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] is None


def test_invalid_grouped_order_json_output_does_not_replace_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "invalid-grouped-order-output.pietto",
        _unsupported_grouped_order_source("postgres.table"),
    )
    output_path = _write(tmp_path, "invalid-grouped-order.sql", "old SQL\n")

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("invalid grouped order must stop before IR and SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])

    assert result["ok"] is False
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2321"]
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "old SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))


def test_no_group_projection_alias_order_emits_the_output_expression(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "no-group-alias-order.pietto",
        _source_prefix("postgres.table") + "table sorted_orders:\n"
        "    from orders\n"
        "    select:\n"
        "        sort_key = lower(status)\n"
        "    order by:\n"
        "        sort_key\n",
    )

    # Before: PIE-S2102 said an ORDER BY key outside a grouped query cannot
    # name a SELECT output. The key now reads the output and the SQL restates
    # its expression.
    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        "-- sorted_orders\n"
        "SELECT\n"
        '    lower("status") AS "sort_key"\n'
        'FROM "orders"\n'
        "ORDER BY\n"
        '    lower("status") ASC;\n'
    )


def test_check_accepts_numeric_literal_aggregate_arguments(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "numeric-literal-aggregate-check.pietto",
        _numeric_literal_source("postgres.table"),
    )

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql", "sum_fragment", "avg_fragment"),
    [
        (
            "postgres",
            "postgres.table",
            NUMERIC_LITERAL_POSTGRES_SQL,
            'CAST(SUM(CAST(("amount" + 1) AS pg_catalog.int8)) AS pg_catalog.int8)',
            'AVG(("score" * 2))',
        ),
        (
            "mysql",
            "mysql.table",
            NUMERIC_LITERAL_MYSQL_SQL,
            "SUM((`amount` + 1))",
            "AVG((`score` * 2))",
        ),
    ],
)
def test_text_emit_sql_carries_numeric_literal_aggregate_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    dialect: str,
    connector: str,
    expected_sql: str,
    sum_fragment: str,
    avg_fragment: str,
) -> None:
    path = _write(
        tmp_path,
        f"{dialect}-numeric-literal-aggregate.pietto",
        _numeric_literal_source(connector),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"-- aggregate_stats\n{expected_sql};\n"
    assert captured.err == ""
    assert sum_fragment in captured.out
    assert avg_fragment in captured.out
    assert "ORDER BY" in captured.out
    order_by = _order_by_clause(captured.out)
    assert '"total"' not in order_by
    assert '"average"' not in order_by
    assert "`total`" not in order_by
    assert "`average`" not in order_by


def test_json_emit_sql_preserves_v1_shape_for_numeric_literal_aggregates(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "postgres-numeric-literal-aggregate-json.pietto",
        _numeric_literal_source("postgres.table"),
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert set(result) == EMIT_SQL_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["path"] == str(path)
    assert result["dialect"] == "postgres"
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    assert artifacts == [
        {
            "kind": "relation",
            "name": "aggregate_stats",
            "sql": NUMERIC_LITERAL_POSTGRES_SQL,
        }
    ]
    assert set(artifacts[0]) == {"kind", "name", "sql"}
    _assert_no_json_schema_expansion(result)
    order_by = _order_by_clause(cast(str, artifacts[0]["sql"]))
    assert '"total"' not in order_by
    assert '"average"' not in order_by


def test_text_output_writes_numeric_literal_aggregate_sql_on_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "postgres-numeric-literal-aggregate-output.pietto",
        _numeric_literal_source("postgres.table"),
    )
    output_path = _write(tmp_path, "numeric-literal-aggregate.sql", "stale SQL\n")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert (
        output_path.read_text(encoding="utf-8")
        == f"-- aggregate_stats\n{NUMERIC_LITERAL_POSTGRES_SQL};\n"
    )
    assert not tuple(tmp_path.glob("*.tmp"))


def test_json_output_writes_numeric_literal_aggregate_sql_and_keeps_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "postgres-numeric-literal-aggregate-json-output.pietto",
        _numeric_literal_source("postgres.table"),
    )
    output_path = _write(
        tmp_path,
        "numeric-literal-aggregate-json.sql",
        "stale SQL\n",
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    assert artifacts == [
        {
            "kind": "relation",
            "name": "aggregate_stats",
            "sql": NUMERIC_LITERAL_POSTGRES_SQL,
        }
    ]
    assert (
        output_path.read_text(encoding="utf-8")
        == f"-- aggregate_stats\n{NUMERIC_LITERAL_POSTGRES_SQL};\n"
    )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize(
    "projection",
    [
        "value = sum(1)",
        "value = sum(amount / tax)",
        "value = count(1)",
    ],
)
def test_invalid_numeric_literal_aggregate_text_fails_before_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    projection: str,
) -> None:
    path = _write(
        tmp_path,
        "invalid-numeric-literal-aggregate.pietto",
        _invalid_source("postgres.table", projection),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2315 error:" in captured.err
    assert "SELECT\n" not in captured.err


def test_invalid_numeric_literal_aggregate_json_fails_without_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "invalid-numeric-literal-aggregate-json.pietto",
        _invalid_source("postgres.table", "value = count(1)"),
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])

    assert result["ok"] is False
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-S2315"]
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] is None


def test_invalid_numeric_literal_aggregate_json_output_does_not_replace_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "invalid-numeric-literal-aggregate-output.pietto",
        _invalid_source("postgres.table", "value = sum(amount / tax)"),
    )
    output_path = _write(tmp_path, "invalid-numeric-literal-aggregate.sql", "old SQL\n")
    _forbid_ir_and_sql(monkeypatch)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format=json",
                "--output",
                str(output_path),
            ]
        )
        == 1
    )

    result = _read_json(capsys)
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])

    assert result["ok"] is False
    # `amount / tax` divides two Int values, so it also warns (PIE-S2106).
    assert [diagnostic["code"] for diagnostic in diagnostics] == [
        "PIE-S2315",
        "PIE-S2106",
    ]
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "old SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))


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


def _relation_ir(script_ir: ScriptIR, name: str) -> RelationIR:
    matches = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    ]
    assert len(matches) == 1
    return matches[0]


def _malformed_grouped_relation(relation: RelationIR, case: str) -> RelationIR:
    if case == "unresolved_group_key":
        return replace(
            relation, group_keys=(replace(relation.group_keys[0], field=None),)
        )
    if case == "non_field_group_key":
        return replace(
            relation, group_keys=cast(tuple[FieldRefIR, ...], (_literal(1),))
        )
    if case == "duplicate_group_key":
        return replace(
            relation, group_keys=(relation.group_keys[0], relation.group_keys[0])
        )
    if case == "grouped_order_by":
        return replace(
            relation,
            order_by=(
                OrderItemIR(
                    expression=_field("customer_id", TEXT_NON_NULL),
                    direction=OrderDirectionIR.ASC,
                    span=SPAN,
                ),
            ),
        )
    if case == "non_grouped_projection":
        projection = relation.projections[0]
        return replace(
            relation,
            projections=(
                replace(
                    projection,
                    name="customer_id",
                    expression=_field("customer_id", TEXT_NON_NULL),
                ),
                *relation.projections[1:],
            ),
        )
    if case == "pure_grouped_output":
        return replace(relation, projections=(relation.projections[0],))
    if case == "unsupported_aggregate":
        projection = relation.projections[2]
        assert isinstance(projection.expression, AggregateCallIR)
        return replace(
            relation,
            projections=(
                *relation.projections[:2],
                replace(
                    projection,
                    expression=replace(
                        projection.expression,
                        function="kurtosis",
                        value_type=FLOAT_NULLABLE,
                    ),
                ),
            ),
        )
    raise AssertionError(f"Unknown malformed grouped IR case: {case}")


def _literal(value: int) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=INT_NON_NULL, value=value)


def _field(name: str, value_type: TypeRefIR) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=value_type,
        name=name,
        qualifier=(),
        field=FieldId(owner=OWNER, name=name),
    )


def _grouped_source(connector: str, body: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text\n"
        "    customer_id: Text\n"
        "    amount: Int\n"
        f'source orders: Order = {connector}("orders")\n'
        "table grouped_orders:\n"
        "    from orders\n"
        f"{body}"
    )


def _grouped_chain_source(connector: str) -> str:
    return (
        "shape Order:\n"
        "    status: Text\n"
        "    amount: Int\n"
        f'source orders: Order = {connector}("orders")\n'
        "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        status\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
        "query downstream:\n"
        "    from grouped_orders\n"
        "    select:\n"
        "        status\n"
        "        total\n"
    )


def _expression_argument_source(
    connector: str,
    select_body: str,
    *,
    grouped: bool = False,
    satisfying: str | None = None,
) -> str:
    group_block = "    group by:\n        region\n" if grouped else ""
    satisfying_block = (
        f"    having:\n        {satisfying}\n" if satisfying is not None else ""
    )
    return (
        EXPRESSION_ARGUMENT_SHAPE + f'source orders: Order = {connector}("orders")\n'
        "table aggregate_stats:\n"
        "    from orders\n"
        f"{group_block}"
        "    select:\n"
        f"        {select_body}\n"
        f"{satisfying_block}"
    )


def _expression_argument_grouped_select_body() -> str:
    return (
        "region\n"
        "        total = sum(amount + tax)\n"
        "        normalized = count_distinct(lower(trim(status)))"
    )


def _having_clause(sql: str) -> str:
    _prefix, having = sql.split("HAVING\n", maxsplit=1)
    return having


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


def _forbid_ir_and_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("semantic errors must stop before IR and SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
    monkeypatch.setattr(cli.mysql_backend, "emit_mysql_sql", unexpected_call)


def _count_expression_source(
    connector: str,
    select_body: str,
    *,
    grouped: bool = False,
) -> str:
    group_block = "    group by:\n        region\n" if grouped else ""
    return (
        COUNT_EXPRESSION_SHAPE + f'source orders: Order = {connector}("orders")\n'
        "table aggregate_stats:\n"
        "    from orders\n"
        f"{group_block}"
        "    select:\n"
        f"        {select_body}\n"
    )


def _count_expression_grouped_select_body() -> str:
    return (
        "region\n"
        "        amount_tax = count(amount + tax)\n"
        "        lowered = count(lower(status))\n"
        "        active_count = count(active or optional_active)"
    )


def _assert_no_json_schema_expansion(result: dict[str, object]) -> None:
    for forbidden_key in (
        "schema_version_v2",
        "project",
        "project_root",
        "files",
    ):
        assert forbidden_key not in result


def _write_invalid_count_field_source(tmp_path: Path) -> Path:
    path = tmp_path / "invalid-count-field.pietto"
    path.write_text(
        "shape Order:\n"
        "    status: Text\n"
        "    amount: Int | None\n"
        'source orders: Order = postgres.table("orders")\n'
        "table invalid_count_field:\n"
        "    from orders\n"
        "    select:\n"
        "        known_amounts = count(amount, status)\n",
        encoding="utf-8",
    )
    return path


def _golden_text(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def _golden_sql(name: str) -> str:
    """The SQL of a one-artifact golden, without its `--` name line and `;`."""

    return _golden_text(name).split("\n", 1)[1].removesuffix(";\n")


def _golden_bytes(name: str) -> bytes:
    return (GOLDEN_ROOT / name).read_bytes()


def _grouped_order_source(connector: str) -> str:
    return (
        _source_prefix(connector) + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount + tax)\n"
        "    having:\n"
        "        total > 1000\n"
        "    order by:\n"
        "        total desc\n"
        "        region asc\n"
        "    limit 10\n"
    )


def _unsupported_grouped_order_source(connector: str) -> str:
    return (
        _source_prefix(connector) + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount + tax)\n"
        "    order by:\n"
        "        sum(amount)\n"
    )


def _source_prefix(connector: str) -> str:
    return SOURCE_SHAPE + f'source orders: Order = {connector}("orders")\n'


def _assert_clause_order(sql: str) -> None:
    assert "GROUP BY" in sql
    assert "HAVING" in sql
    assert "ORDER BY" in sql
    assert "LIMIT" in sql
    assert sql.index("GROUP BY") < sql.index("HAVING") < sql.index("ORDER BY")
    assert sql.index("ORDER BY") < sql.index("LIMIT")


def _order_by_clause(sql: str) -> str:
    _prefix, order_by = sql.split("ORDER BY\n", maxsplit=1)
    return order_by.split("\nLIMIT", maxsplit=1)[0]


def _numeric_literal_source(connector: str) -> str:
    return (
        SOURCE_SHAPE + f'source orders: Order = {connector}("orders")\n'
        "table aggregate_stats:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount + 1)\n"
        "        average = avg(score * 2)\n"
        "    having:\n"
        "        total > 1000\n"
        "    order by:\n"
        "        average desc\n"
        "        total asc\n"
        "    limit 10\n"
    )


def _invalid_source(connector: str, projection: str) -> str:
    return (
        SOURCE_SHAPE + f'source orders: Order = {connector}("orders")\n'
        "table aggregate_stats:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )
