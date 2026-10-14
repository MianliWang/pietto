from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest

import pietto.cli as cli
import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"

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
    "    active: Bool not null\n"
    "    optional_active: Bool nullable\n"
    "    amount: Int not null\n"
    "    tax: Int not null\n"
)

NO_GROUP_SELECT_BODY = (
    "amount_tax = count(amount + tax)\n"
    "        amount_one = count(amount + 1)\n"
    "        lowered = count(lower(status))\n"
    "        active_count = count(active and true)"
)

POSTGRES_NO_GROUP_SQL = (
    "SELECT\n"
    '    COUNT(("amount" + "tax")) AS "amount_tax",\n'
    '    COUNT(("amount" + 1)) AS "amount_one",\n'
    '    COUNT(lower("status")) AS "lowered",\n'
    '    COUNT(("active" AND TRUE)) AS "active_count"\n'
    'FROM "orders"'
)

MYSQL_NO_GROUP_SQL = (
    "SELECT\n"
    "    COUNT((`amount` + `tax`)) AS `amount_tax`,\n"
    "    COUNT((`amount` + 1)) AS `amount_one`,\n"
    "    COUNT(LOWER(`status`)) AS `lowered`,\n"
    "    COUNT((`active` AND TRUE)) AS `active_count`\n"
    "FROM `orders`"
)

POSTGRES_GROUPED_SQL = (
    "SELECT\n"
    '    "region" AS "region",\n'
    '    COUNT(("amount" + "tax")) AS "amount_tax",\n'
    '    COUNT(lower("status")) AS "lowered",\n'
    '    COUNT(("active" OR "optional_active")) AS "active_count"\n'
    'FROM "orders"\n'
    "GROUP BY\n"
    '    "region"'
)

MYSQL_GROUPED_SQL = (
    "SELECT\n"
    "    `region` AS `region`,\n"
    "    COUNT((`amount` + `tax`)) AS `amount_tax`,\n"
    "    COUNT(LOWER(`status`)) AS `lowered`,\n"
    "    COUNT((`active` OR `optional_active`)) AS `active_count`\n"
    "FROM `orders`\n"
    "GROUP BY\n"
    "    `region`"
)


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", MYSQL_NO_GROUP_SQL),
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
        ("postgres", "postgres.table", POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", MYSQL_NO_GROUP_SQL),
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
        _source(connector, NO_GROUP_SELECT_BODY),
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
    assert output_path.read_text(encoding="utf-8") == expected_sql + "\n"
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        ("postgres", "postgres.table", POSTGRES_NO_GROUP_SQL),
        ("mysql", "mysql.table", MYSQL_NO_GROUP_SQL),
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
        _source(connector, NO_GROUP_SELECT_BODY),
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
    assert output_path.read_text(encoding="utf-8") == expected_sql + "\n"
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


@pytest.mark.parametrize(
    ("projection", "expected_code"),
    [
        ("value = count(1)", "PIE-S2315"),
        ("value = count(amount > 1)", "PIE-S2315"),
        ("value = count_if(active)", "PIE-S2103"),
        ("value = min(amount + tax)", "PIE-S2315"),
        ("value = max(amount + tax)", "PIE-S2315"),
        ("value = count(count())", "PIE-S2311"),
        ("value = count(amount) + 1", "PIE-S2310"),
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
        _source("postgres.table", projection),
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
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


def test_public_mysql_api_remains_private() -> None:
    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert not hasattr(sql_api, "emit_mysql_sql")


def test_slice6_does_not_add_golden_inventory() -> None:
    check_goldens = _load_check_goldens()

    classified_fixtures = cast(frozenset[str], check_goldens.CLASSIFIED_FIXTURES)

    assert check_goldens.audit(REPO_ROOT) == ()
    assert not any("phase39" in fixture for fixture in classified_fixtures)
    assert not any("count_expression" in fixture for fixture in classified_fixtures)


def _source(
    connector: str,
    select_body: str,
    *,
    grouped: bool = False,
) -> str:
    group_block = "    group by:\n        region\n" if grouped else ""
    return (
        SOURCE_SHAPE + f'source orders: Order is {connector}("orders")\n'
        "table aggregate_stats:\n"
        "    from orders\n"
        f"{group_block}"
        "    select:\n"
        f"        {select_body}\n"
    )


def _grouped_select_body() -> str:
    return (
        "region\n"
        "        amount_tax = count(amount + tax)\n"
        "        lowered = count(lower(status))\n"
        "        active_count = count(active or optional_active)"
    )


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("{")
    assert captured.out.endswith("}\n")
    assert captured.out.count("\n") == 1
    result = json.loads(captured.out)
    assert isinstance(result, dict)
    return cast(dict[str, object], result)


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


def _forbid_ir_and_sql(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("semantic errors must stop before IR and SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
    monkeypatch.setattr(cli.mysql_backend, "emit_mysql_sql", unexpected_call)


def _load_check_goldens() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "phase39_check_goldens", CHECK_GOLDENS_PATH
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
