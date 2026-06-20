from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli

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

BASE_SHAPE = (
    "shape Order:\n"
    "    status: Text not null\n"
    "    region: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
    "    price: Decimal not null\n"
)

NO_GROUP_SELECT_BODY = (
    "total = sum(amount + tax)\n"
    "        weighted = avg(score * weight)\n"
    "        normalized = count_distinct(lower(status))\n"
    "        normalized_trimmed = count_distinct(lower(trim(status)))"
)
POSTGRES_NO_GROUP_SQL = (
    "SELECT\n"
    '    SUM(("amount" + "tax")) AS "total",\n'
    '    AVG(("score" * "weight")) AS "weighted",\n'
    '    COUNT(DISTINCT lower("status")) AS "normalized",\n'
    '    COUNT(DISTINCT lower(trim("status"))) AS "normalized_trimmed"\n'
    'FROM "orders"'
)
MYSQL_NO_GROUP_SQL = (
    "SELECT\n"
    "    SUM((`amount` + `tax`)) AS `total`,\n"
    "    AVG((`score` * `weight`)) AS `weighted`,\n"
    "    COUNT(DISTINCT LOWER(`status`)) AS `normalized`,\n"
    "    COUNT(DISTINCT LOWER(TRIM(`status`))) AS `normalized_trimmed`\n"
    "FROM `orders`"
)
POSTGRES_GROUPED_SQL = (
    "SELECT\n"
    '    "region" AS "region",\n'
    '    SUM(("amount" + "tax")) AS "total",\n'
    '    COUNT(DISTINCT lower(trim("status"))) AS "normalized"\n'
    'FROM "orders"\n'
    "GROUP BY\n"
    '    "region"'
)
MYSQL_GROUPED_SQL = (
    "SELECT\n"
    "    `region` AS `region`,\n"
    "    SUM((`amount` + `tax`)) AS `total`,\n"
    "    COUNT(DISTINCT LOWER(TRIM(`status`))) AS `normalized`\n"
    "FROM `orders`\n"
    "GROUP BY\n"
    "    `region`"
)
POSTGRES_TOTAL_HAVING_SQL = POSTGRES_GROUPED_SQL + (
    '\nHAVING\n    SUM(("amount" + "tax")) > 1000'
)
MYSQL_TOTAL_HAVING_SQL = MYSQL_GROUPED_SQL + (
    "\nHAVING\n    SUM((`amount` + `tax`)) > 1000"
)
POSTGRES_NORMALIZED_HAVING_SQL = POSTGRES_GROUPED_SQL + (
    '\nHAVING\n    COUNT(DISTINCT lower(trim("status"))) > 10'
)
MYSQL_NORMALIZED_HAVING_SQL = MYSQL_GROUPED_SQL + (
    "\nHAVING\n    COUNT(DISTINCT LOWER(TRIM(`status`))) > 10"
)


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", MYSQL_NO_GROUP_SQL),
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
        _source(connector, NO_GROUP_SELECT_BODY),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == expected_sql + "\n"


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", POSTGRES_GROUPED_SQL),
        ("mysql", "mysql.table", MYSQL_GROUPED_SQL),
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
        _source(connector, _grouped_select_body(), grouped=True),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == expected_sql + "\n"


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", MYSQL_NO_GROUP_SQL),
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
        _source(connector, NO_GROUP_SELECT_BODY),
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
        ("postgres", "postgres.table", POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", MYSQL_NO_GROUP_SQL),
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
        _source(connector, NO_GROUP_SELECT_BODY),
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
    assert output_path.read_text(encoding="utf-8") == expected_sql + "\n"
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", MYSQL_NO_GROUP_SQL),
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
        _source(connector, NO_GROUP_SELECT_BODY),
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
    assert output_path.read_text(encoding="utf-8") == expected_sql + "\n"
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = sum(amount / tax)", "PIE-S2315"),
        ("value = sum(amount % tax)", "PIE-S2315"),
        ("value = avg(price * price)", "PIE-S2315"),
        ("value = count_distinct(len(status))", "PIE-S2315"),
        ("value = count_distinct(lower(amount))", "PIE-S2315"),
        ("value = count(amount + tax)", "PIE-S2315"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(score * weight)", "PIE-S2315"),
        ("value = sum(avg(amount))", "PIE-S2311"),
        ("value = sum(amount) + 1", "PIE-S2310"),
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
        _source("postgres.table", projection),
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
    assert codes == [expected_code]
    assert "PIE-B1000" not in codes
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert output_path.read_text(encoding="utf-8") == "old SQL\n"
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


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
        _source(
            connector,
            _grouped_select_body(),
            grouped=True,
            satisfying=satisfying,
        ),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == expected_sql + "\n"
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
        _source(
            "postgres.table",
            _grouped_select_body() if grouped else "total = sum(amount + tax)",
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
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


def _source(
    connector: str,
    select_body: str,
    *,
    grouped: bool = False,
    satisfying: str | None = None,
) -> str:
    group_block = "    group by:\n        region\n" if grouped else ""
    satisfying_block = (
        f"    satisfying:\n        {satisfying}\n" if satisfying is not None else ""
    )
    return (
        BASE_SHAPE + f'source orders: Order is {connector}("orders")\n'
        "table aggregate_stats:\n"
        "    from orders\n"
        f"{group_block}"
        "    select:\n"
        f"        {select_body}\n"
        f"{satisfying_block}"
    )


def _grouped_select_body() -> str:
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
