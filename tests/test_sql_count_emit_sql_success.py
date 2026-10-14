from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli


@pytest.mark.parametrize(
    ("dialect", "connector", "expected_sql"),
    [
        (
            "postgres",
            "postgres.table",
            "SELECT\n"
            '    COUNT(*) AS "total"\n'
            'FROM "orders"\n'
            "WHERE \"status\" = 'paid'\n",
        ),
        (
            "mysql",
            "mysql.table",
            "SELECT\n    COUNT(*) AS `total`\nFROM `orders`\nWHERE `status` = 'paid'\n",
        ),
    ],
)
def test_count_emit_sql_succeeds_with_sql_artifact(
    dialect: str,
    connector: str,
    expected_sql: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_count_program(tmp_path, connector=connector)

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 0

    captured = capsys.readouterr()
    assert captured.out == expected_sql
    assert captured.err == ""


def test_count_emit_sql_json_preserves_v1_success_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_count_program(tmp_path, connector="postgres.table")

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

    captured = capsys.readouterr()
    assert captured.err == ""
    result = cast(dict[str, object], json.loads(captured.out))

    assert set(result) == {
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
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is True
    assert result["dialect"] == "postgres"
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": "paid_order_stats",
            "sql": (
                "SELECT\n"
                '    COUNT(*) AS "total"\n'
                'FROM "orders"\n'
                "WHERE \"status\" = 'paid'"
            ),
        }
    ]


def test_count_emit_sql_output_path_is_written_on_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_count_program(tmp_path, connector="postgres.table")
    output_path = tmp_path / "count.sql"

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
                str(output_path),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    result = cast(dict[str, object], json.loads(captured.out))

    assert captured.err == ""
    assert result["diagnostics"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    assert output_path.read_text(encoding="utf-8") == (
        'SELECT\n    COUNT(*) AS "total"\nFROM "orders"\nWHERE "status" = \'paid\'\n'
    )


def _write_count_program(
    tmp_path: Path,
    *,
    connector: str,
) -> Path:
    path = tmp_path / "count.pietto"
    path.write_text(
        "shape Order:\n"
        "    status: Text not null\n"
        f'source orders: Order is {connector}("orders")\n'
        "table paid_order_stats:\n"
        "    from orders\n"
        '    where status == "paid"\n'
        "    select:\n"
        "        total = count()\n",
        encoding="utf-8",
    )
    return path
