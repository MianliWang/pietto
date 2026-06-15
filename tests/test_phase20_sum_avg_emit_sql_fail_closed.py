from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli


@pytest.mark.parametrize(
    ("dialect", "connector"),
    [
        ("postgres", "postgres.table"),
        ("mysql", "mysql.table"),
    ],
)
def test_sum_avg_emit_sql_fails_closed_without_sql_artifact(
    dialect: str,
    connector: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_sum_avg_program(tmp_path, connector=connector)

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-B1000" in captured.err
    assert "sum" in captured.err


def test_sum_avg_emit_sql_json_preserves_v1_failure_shape(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_sum_avg_program(tmp_path, connector="postgres.table")

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
        == 1
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
    assert result["ok"] is False
    assert result["dialect"] == "postgres"
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] is None
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-B1000"]


def test_sum_avg_emit_sql_output_path_is_unwritten_on_backend_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_sum_avg_program(tmp_path, connector="postgres.table")
    output_path = tmp_path / "sum-avg.sql"

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
        == 1
    )

    captured = capsys.readouterr()
    result = cast(dict[str, object], json.loads(captured.out))

    assert captured.err == ""
    assert result["ok"] is False
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert not output_path.exists()


def _write_sum_avg_program(
    tmp_path: Path,
    *,
    connector: str,
) -> Path:
    path = tmp_path / "sum-avg.pietto"
    path.write_text(
        "shape Order:\n"
        "    status: Text not null\n"
        "    amount: Int not null\n"
        f'source orders: Order is {connector}("orders")\n'
        "table paid_order_stats:\n"
        "    from orders\n"
        '    where status == "paid"\n'
        "    select:\n"
        "        total = count()\n"
        "        revenue = sum(amount)\n"
        "        average = avg(amount)\n",
        encoding="utf-8",
    )
    return path
