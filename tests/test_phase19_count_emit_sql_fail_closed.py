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
def test_count_emit_sql_fails_closed_without_sql_artifacts(
    dialect: str,
    connector: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_count_program(tmp_path, connector=connector)

    assert cli.main(["emit-sql", str(path), "--dialect", dialect]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-B1000 error:" in captured.err
    assert "function call: count" in captured.err


def test_count_emit_sql_json_preserves_v1_shape_with_empty_artifacts(
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
    assert "function call: count" in cast(str, diagnostics[0]["message"])


def test_count_emit_sql_output_path_remains_unwritten_on_backend_failure(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_count_program(tmp_path, connector="postgres.table")
    output_path = tmp_path / "count.sql"

    # Slice 1A intentionally leaves aggregate IR provisional; SQL emission must
    # still fail closed before writing a requested output file.
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
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output_path), "written": False}
    assert not output_path.exists()


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
