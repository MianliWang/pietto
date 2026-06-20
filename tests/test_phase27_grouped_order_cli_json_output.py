from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.sql as sql_api

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

SOURCE_SHAPE = (
    "shape Order:\n"
    "    region: Text not null\n"
    "    status: Text not null\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
    "    score: Float not null\n"
    "    weight: Float not null\n"
)

POSTGRES_SQL = (
    "SELECT\n"
    '    "region" AS "region",\n'
    '    SUM(("amount" + "tax")) AS "total"\n'
    'FROM "orders"\n'
    "GROUP BY\n"
    '    "region"\n'
    "HAVING\n"
    '    SUM(("amount" + "tax")) > 1000\n'
    "ORDER BY\n"
    '    SUM(("amount" + "tax")) DESC,\n'
    '    "region" ASC\n'
    "LIMIT 10"
)

MYSQL_SQL = (
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


def test_check_accepts_grouped_result_ordering(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "grouped-order-check.pietto",
        _accepted_source("postgres.table"),
    )

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql", "forbidden_order_alias"),
    [
        ("postgres", "postgres.table", POSTGRES_SQL, '"total"'),
        ("mysql", "mysql.table", MYSQL_SQL, "`total`"),
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
        _accepted_source(connector),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.out == expected_sql + "\n"
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
        _accepted_source("postgres.table"),
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
            "sql": POSTGRES_SQL,
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
        _accepted_source("postgres.table"),
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
    assert output_path.read_text(encoding="utf-8") == POSTGRES_SQL + "\n"
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


def test_json_output_writes_grouped_order_sql_and_keeps_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "postgres-grouped-order-json-output.pietto",
        _accepted_source("postgres.table"),
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
            "sql": POSTGRES_SQL,
        }
    ]
    assert output_path.read_text(encoding="utf-8") == POSTGRES_SQL + "\n"
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


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
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


def test_no_group_projection_alias_order_still_fails_before_sql(
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

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2102 error: Unknown field: sort_key" in captured.err


def test_public_mysql_api_remains_private() -> None:
    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert not hasattr(sql_api, "emit_mysql_sql")


def _accepted_source(connector: str) -> str:
    return (
        _source_prefix(connector) + "table grouped_orders:\n"
        "    from orders\n"
        "    group by:\n"
        "        region\n"
        "    select:\n"
        "        region\n"
        "        total = sum(amount + tax)\n"
        "    satisfying:\n"
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
    return SOURCE_SHAPE + f'source orders: Order is {connector}("orders")\n'


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("{")
    assert captured.out.endswith("}\n")
    assert captured.out.count("\n") == 1
    result = json.loads(captured.out)
    assert isinstance(result, dict)
    return cast(dict[str, object], result)


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


def _assert_no_json_schema_expansion(result: dict[str, object]) -> None:
    for forbidden_key in (
        "schema_version_v2",
        "project",
        "project_root",
        "files",
    ):
        assert forbidden_key not in result


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
