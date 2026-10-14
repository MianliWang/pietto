from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import ScriptIR
from pietto.sql import SqlResult

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"

POSTGRES_INPUT = Path("tests/fixtures/phase23/postgres_count_field_aggregate.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase23/mysql_count_field_aggregate.pietto")
POSTGRES_GROUPED_INPUT = Path(
    "tests/fixtures/phase23/postgres_grouped_count_field_aggregate.pietto"
)
MYSQL_GROUPED_INPUT = Path(
    "tests/fixtures/phase23/mysql_grouped_count_field_aggregate.pietto"
)
POSTGRES_GOLDEN = "emit_sql_count_field_aggregate.sql"
MYSQL_GOLDEN = "emit_mysql_count_field_aggregate.sql"
POSTGRES_GROUPED_GOLDEN = "emit_sql_grouped_count_field_aggregate.sql"
MYSQL_GROUPED_GOLDEN = "emit_mysql_grouped_count_field_aggregate.sql"

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

COUNT_FIELD_CLI_CASES: tuple[tuple[Path, str, str, str], ...] = (
    (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN, "order_completeness"),
    (MYSQL_INPUT, "mysql", MYSQL_GOLDEN, "order_completeness"),
    (
        POSTGRES_GROUPED_INPUT,
        "postgres",
        POSTGRES_GROUPED_GOLDEN,
        "order_completeness_by_status",
    ),
    (
        MYSQL_GROUPED_INPUT,
        "mysql",
        MYSQL_GROUPED_GOLDEN,
        "order_completeness_by_status",
    ),
)
COUNT_FIELD_OUTPUT_CASES: tuple[tuple[Path, str, str, str], ...] = (
    (POSTGRES_INPUT, "postgres", POSTGRES_GOLDEN, "order_completeness"),
    (MYSQL_INPUT, "mysql", MYSQL_GOLDEN, "order_completeness"),
)


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
    assert result["path"] == input_path.as_posix()
    assert result["dialect"] == dialect
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts == [
        {
            "kind": "relation",
            "name": artifact_name,
            "sql": _golden_text(golden_name).removesuffix("\n"),
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
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


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
            "sql": _golden_text(golden_name).removesuffix("\n"),
        }
    ]
    assert output_path.read_bytes() == _golden_bytes(golden_name)
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


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
            path=POSTGRES_INPUT.as_posix(),
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
                POSTGRES_INPUT.as_posix(),
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


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    document = cast(dict[str, object], json.loads(captured.out))
    assert captured.out.endswith("\n")
    assert captured.out.count("\n") == 1
    return document


def _write_invalid_count_field_source(tmp_path: Path) -> Path:
    path = tmp_path / "invalid-count-field.pietto"
    path.write_text(
        "shape Order:\n"
        "    status: Text not null\n"
        "    amount: Int nullable\n"
        'source orders: Order is postgres.table("orders")\n'
        "table invalid_count_field:\n"
        "    from orders\n"
        "    select:\n"
        "        known_amounts = count(amount, status)\n",
        encoding="utf-8",
    )
    return path


def _golden_text(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def _golden_bytes(name: str) -> bytes:
    return (GOLDEN_ROOT / name).read_bytes()
