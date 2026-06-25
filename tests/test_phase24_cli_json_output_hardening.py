from __future__ import annotations

import hashlib
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

POSTGRES_COUNT_DISTINCT_INPUT = Path(
    "tests/fixtures/phase24/postgres_count_distinct_aggregate.pietto"
)
POSTGRES_GROUPED_COUNT_DISTINCT_INPUT = Path(
    "tests/fixtures/phase24/postgres_grouped_count_distinct_aggregate.pietto"
)
POSTGRES_DECIMAL_INPUT = Path(
    "tests/fixtures/phase24/postgres_decimal_aggregate.pietto"
)
POSTGRES_GROUPED_DECIMAL_INPUT = Path(
    "tests/fixtures/phase24/postgres_grouped_decimal_aggregate.pietto"
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

PHASE24_POSTGRES_CASES: tuple[tuple[Path, str, str, str], ...] = (
    (
        POSTGRES_COUNT_DISTINCT_INPUT,
        "emit_sql_count_distinct_aggregate.sql",
        "unique_order_values",
        "COUNT(DISTINCT",
    ),
    (
        POSTGRES_GROUPED_COUNT_DISTINCT_INPUT,
        "emit_sql_grouped_count_distinct_aggregate.sql",
        "unique_customers_by_status",
        "GROUP BY",
    ),
    (
        POSTGRES_DECIMAL_INPUT,
        "emit_sql_decimal_aggregate.sql",
        "decimal_order_stats",
        'SUM("amount")',
    ),
    (
        POSTGRES_GROUPED_DECIMAL_INPUT,
        "emit_sql_grouped_decimal_aggregate.sql",
        "decimal_order_stats_by_status",
        'MAX("orders"."amount")',
    ),
)

LOCKED_BOUNDARY_SURFACES = {
    "cli": (
        "src/pietto/cli.py",
        1,
        "af378ad655ed3ffc230983e94ee40cfef3b4f67e01d902901c5933c317c1f90f",
    ),
    "semantic": (
        "src/pietto/semantic",
        20,
        "dfa4af8c0dd699431ac068f1ee007e3a744d9384fe1b602aa5ab682a1f42579b",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "7438c72875751eeadf8b12b3aad1825499061f3f4e0dd73d8c1a339c614ae884",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "67aeafa622d3147b08930cebcf18862322eec692d547d328b18966afa81f3530",
    ),
    "check_goldens": (
        "scripts/check_goldens.py",
        1,
        "59c3921f21de398e06f6deca28f18871120bbf411110974c3df6ba7fa85970c4",
    ),
    "fixtures": (
        "tests/fixtures",
        68,
        "dbd457dd7e79f41d0e1740187818478941861cabf9ae9f3b06f908bdc81cd11c",
    ),
    "goldens": (
        "tests/fixtures/golden",
        37,
        "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004",
    ),
    "grammar": (
        "grammar/Pietto.g4",
        1,
        "4078b89d21126706746e07052ac8870a70f7275bd02dfc0433552f5edf06c082",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1",
    ),
    "pyproject": (
        "pyproject.toml",
        1,
        "cf5894a9cb7ef0399126a7d424da4e3958fc92d8e6bed295939a6e6bac469099",
    ),
    "uv_lock": (
        "uv.lock",
        1,
        "b48bb27656ff3344a95ba92347f45173904801cd8bdccfd2b55106549c445ac0",
    ),
    "github": (
        ".github",
        1,
        "129f96212b5025e66254b2485195977770cf7765bd8977215c6dfaefd9e6e5ae",
    ),
    "makefile": (
        "Makefile",
        1,
        "14c05902d307dbc803c31d522ebe6d2614d36f2c428e4c1eca2d4441661dbe09",
    ),
    "readme": (
        "README.md",
        1,
        "edf2f8f39d52d259c762116b669fa86377792ff8403b5cdbef7c3b57de50ca94",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "238ac13ec9193d9377fd05485b3c83ec105f8bfc6996b665fd50385b9598d584",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "a93d7ed31c446c41fb671ab809723730a3e9839ec6abd37d6c7ac34f56e46094",
    ),
}


@pytest.mark.parametrize(
    ("input_path", "golden_name", "artifact_name", "expected_fragment"),
    PHASE24_POSTGRES_CASES,
)
def test_cli_text_phase24_postgres_aggregate_sql_matches_reviewed_golden(
    input_path: Path,
    golden_name: str,
    artifact_name: str,
    expected_fragment: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del artifact_name, expected_fragment
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["emit-sql", input_path.as_posix(), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == _golden_bytes(golden_name)


@pytest.mark.parametrize(
    ("input_path", "golden_name", "artifact_name", "expected_fragment"),
    PHASE24_POSTGRES_CASES,
)
def test_cli_json_phase24_postgres_aggregate_sql_preserves_v1_shape(
    input_path: Path,
    golden_name: str,
    artifact_name: str,
    expected_fragment: str,
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
                "postgres",
                "--format",
                "json",
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
    assert result["path"] == input_path.as_posix()
    assert result["dialect"] == "postgres"
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] is None
    assert artifacts == [
        {
            "kind": "relation",
            "name": artifact_name,
            "sql": _golden_text(golden_name).removesuffix("\n"),
        }
    ]
    assert set(artifacts[0]) == {"kind", "name", "sql"}
    assert expected_fragment in cast(str, artifacts[0]["sql"])
    for forbidden_key in ("schema_version_v2", "project", "project_root", "files"):
        assert forbidden_key not in result


@pytest.mark.parametrize(
    ("input_path", "golden_name", "artifact_name", "expected_fragment"),
    PHASE24_POSTGRES_CASES,
)
def test_cli_text_phase24_output_writes_exact_sql(
    input_path: Path,
    golden_name: str,
    artifact_name: str,
    expected_fragment: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    del artifact_name, expected_fragment
    output_path = tmp_path / f"{input_path.stem}.sql"
    output_path.write_text("stale SQL\n", encoding="utf-8")
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                input_path.as_posix(),
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
    assert output_path.read_bytes() == _golden_bytes(golden_name)
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


@pytest.mark.parametrize(
    ("input_path", "golden_name", "artifact_name", "expected_fragment"),
    PHASE24_POSTGRES_CASES,
)
def test_cli_json_phase24_output_writes_sql_and_keeps_artifacts(
    input_path: Path,
    golden_name: str,
    artifact_name: str,
    expected_fragment: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_path = tmp_path / f"{input_path.stem}-json.sql"
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                input_path.as_posix(),
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

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])

    assert result["schema_version"] == 1
    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output_path), "written": True}
    assert artifacts == [
        {
            "kind": "relation",
            "name": artifact_name,
            "sql": _golden_text(golden_name).removesuffix("\n"),
        }
    ]
    assert expected_fragment in cast(str, artifacts[0]["sql"])
    assert output_path.read_bytes() == _golden_bytes(golden_name)
    assert not tuple(tmp_path.glob(f".{output_path.name}.*.tmp"))


def test_cli_text_aggregate_expression_argument_emits_sql_after_sql_slice(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = _write_supported_expression_aggregate_source(tmp_path)

    assert cli.main(["emit-sql", str(input_path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == (
        'SELECT\n    SUM(("amount" + "amount")) AS "value"\nFROM "orders"\n'
    )


def test_cli_json_aggregate_expression_argument_writes_output_after_sql_slice(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = _write_supported_expression_aggregate_source(tmp_path)
    output_path = tmp_path / "supported-expression-aggregate.sql"
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
        == 0
    )

    result = _read_json(capsys)
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    expected_sql = 'SELECT\n    SUM(("amount" + "amount")) AS "value"\nFROM "orders"'

    assert result["ok"] is True
    assert result["diagnostics"] == []
    assert result["cli_errors"] == []
    assert artifacts == [
        {
            "kind": "relation",
            "name": "invalid_expression_aggregate",
            "sql": expected_sql,
        }
    ]
    assert result["output"] == {"path": str(output_path), "written": True}
    assert output_path.read_text(encoding="utf-8") == expected_sql + "\n"


def test_cli_json_backend_pie_b1000_does_not_write_output(
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
            path=POSTGRES_COUNT_DISTINCT_INPUT.as_posix(),
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
                POSTGRES_COUNT_DISTINCT_INPUT.as_posix(),
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


def test_slice8_boundary_surfaces_remain_post_slice7_hash_locked() -> None:
    for _name, (
        path_or_paths,
        expected_count,
        expected_hash,
    ) in LOCKED_BOUNDARY_SURFACES.items():
        paths = _paths(path_or_paths)

        assert len(paths) == expected_count
        assert _digest(paths) == expected_hash


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("{")
    assert captured.out.endswith("}\n")
    assert captured.out.count("\n") == 1
    document = json.loads(captured.out)
    assert isinstance(document, dict)
    return cast(dict[str, object], document)


def _write_supported_expression_aggregate_source(tmp_path: Path) -> Path:
    path = tmp_path / "supported-expression-aggregate.pietto"
    path.write_text(
        "shape Order:\n"
        "    amount: Decimal not null\n"
        'source orders: Order is postgres.table("orders")\n'
        "table invalid_expression_aggregate:\n"
        "    from orders\n"
        "    select:\n"
        "        value = sum(amount + amount)\n",
        encoding="utf-8",
    )
    return path


def _golden_text(name: str) -> str:
    return (GOLDEN_ROOT / name).read_text(encoding="utf-8")


def _golden_bytes(name: str) -> bytes:
    return (GOLDEN_ROOT / name).read_bytes()


def _paths(path_or_paths: str | tuple[str, ...]) -> tuple[Path, ...]:
    if isinstance(path_or_paths, tuple):
        return tuple(REPO_ROOT / path for path in path_or_paths)

    path = REPO_ROOT / path_or_paths
    if path.is_file():
        return (path,)
    return tuple(
        item
        for item in sorted(path.rglob("*"))
        if item.is_file() and "__pycache__" not in item.parts
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative_path = path.relative_to(REPO_ROOT).as_posix().encode()
        digest.update(relative_path + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()
