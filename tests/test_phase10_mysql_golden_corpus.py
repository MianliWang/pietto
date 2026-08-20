from __future__ import annotations

from pathlib import Path

import pytest

import pietto.cli as cli
import pietto.sql as sql_api
from pietto.errors import Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_file
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
MYSQL_CASES = (
    (
        "tests/fixtures/mysql/compatibility_literals_identifiers.pietto",
        "emit_mysql_compatibility_literals_identifiers.sql",
        ("LiteralCompatibility",),
    ),
    (
        "tests/fixtures/mysql/compatibility_expressions.pietto",
        "emit_mysql_compatibility_expressions.sql",
        ("expression_compatibility",),
    ),
    (
        "tests/fixtures/mysql/compatibility_ordering_metadata.pietto",
        "emit_mysql_compatibility_ordering_metadata.sql",
        ("FirstRelation", "SecondRelation"),
    ),
)
POSTGRES_CASES = (
    ("examples/tables/active_users.pietto", "emit_sql_active_users.sql"),
    ("examples/queries/active_user_emails.pietto", "emit_sql_active_user_emails.sql"),
    (
        "tests/fixtures/postgres/compatibility_literals_identifiers.pietto",
        "emit_sql_compatibility_literals_identifiers.sql",
    ),
    (
        "tests/fixtures/postgres/compatibility_expressions.pietto",
        "emit_sql_compatibility_expressions.sql",
    ),
    (
        "tests/fixtures/postgres/compatibility_ordering_metadata.pietto",
        "emit_sql_compatibility_ordering_metadata.sql",
    ),
)


@pytest.mark.parametrize(("source_path", "golden_name", "artifact_names"), MYSQL_CASES)
def test_private_mysql_output_matches_byte_exact_golden(
    source_path: str,
    golden_name: str,
    artifact_names: tuple[str, ...],
) -> None:
    result = emit_mysql_sql(_compile(source_path))

    assert tuple(artifact.name for artifact in result.artifacts) == artifact_names
    assert result.diagnostics == ()
    assert _render_artifacts(result) == (GOLDEN_ROOT / golden_name).read_bytes()


@pytest.mark.parametrize(("source_path", "golden_name"), POSTGRES_CASES)
def test_postgres_output_still_matches_every_existing_sql_golden(
    source_path: str, golden_name: str
) -> None:
    result = emit_postgres_sql(_compile(source_path))

    assert result.diagnostics == ()
    assert _render_artifacts(result) == (GOLDEN_ROOT / golden_name).read_bytes()


def test_postgres_public_backend_and_mysql_private_backend_remain_distinct() -> None:
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert "return mysql_backend.emit_mysql_sql" in _read("src/pietto/cli.py")
    assert cli.main(["emit-sql", "missing.pietto", "--dialect", "sqlite"]) == 2


def test_mysql_failures_preserve_artifact_and_diagnostic_order() -> None:
    result = emit_mysql_sql(
        _compile("tests/fixtures/mysql/compatibility_failures.pietto")
    )

    assert [artifact.name for artifact in result.artifacts] == ["first_ok", "second_ok"]
    assert [
        diagnostic.message.split(": ", maxsplit=1)[1].split(".", maxsplit=1)[0]
        for diagnostic in result.diagnostics
    ] == ["first_bad", "second_bad"]
    assert all(diagnostic.code == "PIE-B1000" for diagnostic in result.diagnostics)


def _compile(path: str) -> ScriptIR:
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


def _render_artifacts(result: SqlResult) -> bytes:
    return ("\n\n".join(artifact.sql for artifact in result.artifacts) + "\n").encode(
        "utf-8"
    )


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
