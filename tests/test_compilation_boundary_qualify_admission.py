"""Authored QUALIFY must never disappear at the legacy IR boundary."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pietto import cli
from pietto._project.check import check_project_parse_only
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.project_completed_semantics import (
    ProjectConcreteCompletedSemanticResult,
    build_project_completed_semantic_result,
)
from pietto._project.project_query_block_ir import build_project_query_block_ir
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockVerificationStatus,
    verify_project_query_block_ir,
)
from pietto.ast_nodes import QueryDef, TableDef
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.postgres import emit_postgres_sql


def _source(dialect: str, kind: str, predicate: str | None) -> str:
    source = f"""shape Row:
    id: Int not null
source rows: Row is {dialect}.table("rows")
{kind} ranked:
    from rows
    select:
        id
        rn = row_number() window:
            order by:
                id
"""
    if predicate is not None:
        source += f"    qualify:\n{predicate}\n"
    return source


PREDICATES = (
    "        rn <= 1",
    "        true",
    "        row_number() window:\n            order by:\n                id\n        <= 1",
)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("kind", ("table", "query"))
@pytest.mark.parametrize("predicate", PREDICATES)
def test_qualify_rejected_before_legacy_ir_can_drop_it(
    dialect: str, kind: str, predicate: str
) -> None:
    parsed = parse_source(_source(dialect, kind, predicate), path="main.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert not semantic.diagnostics
    definition = parsed.ast.definitions[-1]
    assert isinstance(definition, (TableDef, QueryDef))
    assert definition.qualify_clause is not None
    result = build_ir(parsed.ast, semantic.model)
    assert result.ir is None
    assert tuple(d.code for d in result.diagnostics) == ("PIE-I1000",)
    diagnostic = result.diagnostics[0]
    assert "QUALIFY" in diagnostic.message
    span = definition.qualify_clause.span
    assert (diagnostic.location.line, diagnostic.location.column) == (
        span.line,
        span.column,
    )


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("kind", ("table", "query"))
def test_no_qualify_retains_exact_sql(dialect: str, kind: str) -> None:
    parsed = parse_source(_source(dialect, kind, None))
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert not semantic.diagnostics
    result = build_ir(parsed.ast, semantic.model)
    assert result.ir is not None and not result.diagnostics
    emitted = (emit_postgres_sql if dialect == "postgres" else emit_mysql_sql)(
        result.ir
    )
    quote = '"' if dialect == "postgres" else "`"
    expected = (
        "SELECT\n"
        f"    {quote}id{quote} AS {quote}id{quote},\n"
        f"    ROW_NUMBER() OVER (ORDER BY {quote}id{quote} ASC) AS {quote}rn{quote}\n"
        f"FROM {quote}rows{quote}"
    )
    assert not emitted.diagnostics
    assert tuple(artifact.sql for artifact in emitted.artifacts) == (expected,)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("output_format", ("text", "json"))
def test_public_emit_never_returns_partial_sql(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], dialect: str, output_format: str
) -> None:
    source = _source(dialect, "query", PREDICATES[0])
    source += "query valid:\n    from rows\n    select:\n        id\n"
    path = tmp_path / "main.pietto"
    path.write_text(source, encoding="utf-8")
    parsed = parse_source(source)
    assert parsed.ast is not None
    direct = build_ir(parsed.ast, analyze(parsed.ast).model)
    assert direct.ir is None
    arguments = ["emit-sql", str(path), "--dialect", dialect]
    if output_format == "json":
        arguments += ["--format", "json"]
    assert cli.main(arguments) == 1
    captured = capsys.readouterr()
    if output_format == "json":
        document = json.loads(captured.out)
        assert not document["ok"]
        assert document["artifacts"] == []
        assert document["diagnostics"][0]["code"] == "PIE-I1000"
        assert captured.err == ""
    else:
        assert captured.out == ""
        assert "PIE-I1000" in captured.err
    assert "Traceback" not in captured.err


def test_existing_join_precedence_and_definition_error_order_are_preserved() -> None:
    joined = """query joined:
    from rows
    inner join rows as other:
        from rows
    select:
        id
    qualify:
        true
"""
    for predicate in (None, PREDICATES[0]):
        parsed = parse_source(_source("postgres", "query", predicate) + joined)
        assert parsed.ast is not None
        result = build_ir(parsed.ast, analyze(parsed.ast).model)
        assert result.ir is None
        assert all(d.code == "PIE-I1000" for d in result.diagnostics)
        assert "binary JOIN lowering" in result.diagnostics[-1].message
        assert len(result.diagnostics) == (1 if predicate is None else 2)
        if predicate is not None:
            assert "QUALIFY" in result.diagnostics[0].message
            assert (
                result.diagnostics[0].location.line
                < result.diagnostics[1].location.line
            )


def test_completed_project_qualify_and_private_ir_still_work(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        _source("postgres", "query", PREDICATES[0]), encoding="utf-8"
    )
    parsed = check_project_parse_only(tmp_path)
    assert parsed.ok
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(parsed)
    )
    assert isinstance(completed, ProjectConcreteCompletedSemanticResult)
    assert completed.ok and not completed.diagnostics
    snapshot = build_project_query_block_ir(completed)
    assert (
        verify_project_query_block_ir(snapshot).status
        is ProjectIRQueryBlockVerificationStatus.VERIFIED
    )
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"]
