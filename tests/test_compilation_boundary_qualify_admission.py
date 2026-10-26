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
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.postgres import emit_postgres_sql


def _source(dialect: str, kind: str, predicate: str | None) -> str:
    source = f"""shape Row:
    id: Int
source rows: Row = {dialect}.table("rows")
{kind} ranked:
    from rows
    select:
        id
        rn = row_number() window(order by id)
"""
    if predicate is not None:
        source += f"    qualify:\n{predicate}\n"
    return source


PREDICATES = (
    "        rn <= 1",
    "        True",
    "        row_number() window(order by id) <= 1",
)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("kind", ("table", "query"))
@pytest.mark.parametrize("predicate", PREDICATES)
def test_qualify_is_lowered_before_the_public_sql_boundary(
    dialect: str, kind: str, predicate: str
) -> None:
    parsed = parse_source(_source(dialect, kind, predicate), path="main.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert not semantic.diagnostics
    result = build_ir(parsed.ast, semantic.model)
    assert result.ir is not None and not result.diagnostics
    emitted = (emit_postgres_sql if dialect == "postgres" else emit_mysql_sql)(
        result.ir
    )
    assert not emitted.diagnostics
    sql = emitted.artifacts[-1].sql
    assert "FROM (" in sql
    assert 'AS "__pietto_qualify"' in sql or "AS `__pietto_qualify`" in sql
    assert "WHERE" in sql


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


def test_qualify_bare_input_and_selected_output_are_ambiguous() -> None:
    source = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
query ranked:
    from rows
    select:
        id
        rn = row_number() window(order by id)
    qualify:
        id > 0
"""
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in semantic.diagnostics
    ] == [
        (
            "PIE-S2102",
            "Ambiguous field: id is both the input field rows.id and a SELECT "
            "output; write rows.id, or give the output another name",
        )
    ]


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_qualify_carries_qualified_input_then_orders_and_limits(dialect: str) -> None:
    source = f"""shape Row:
    id: Int
source rows: Row = {dialect}.table("rows")
query ranked:
    from rows
    select:
        k = id + 1
        rn = row_number() window(order by id)
    qualify:
        rows.id > 0
    order by:
        rn desc
    limit 1
"""
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert not semantic.diagnostics
    assert semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    emitted = (emit_postgres_sql if dialect == "postgres" else emit_mysql_sql)(
        lowered.ir
    )
    assert not emitted.diagnostics
    sql = emitted.artifacts[-1].sql
    quote = '"' if dialect == "postgres" else "`"
    assert (
        f"{quote}rows{quote}.{quote}id{quote} AS {quote}__pietto_qualify_0{quote}"
        in sql
    )
    assert f"WHERE\n    {quote}__pietto_qualify_0{quote} > 0" in sql
    assert f"ORDER BY\n    {quote}rn{quote} DESC\nLIMIT 1" in sql


def test_qualify_hidden_ports_freshen_past_a_user_output_name() -> None:
    source = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
query ranked:
    from rows
    select:
        __pietto_qualify_0 = id
    qualify:
        row_number() window(order by id) <= 1
"""
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert not semantic.diagnostics
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    emitted = emit_postgres_sql(lowered.ir)
    assert not emitted.diagnostics
    sql = emitted.artifacts[-1].sql
    assert 'AS "__pietto_qualify_0"' in sql
    assert 'AS "__pietto_qualify_1"' in sql
    assert 'WHERE\n    "__pietto_qualify_1" <= 1' in sql


def test_qualify_carries_a_let_expanded_input_reference() -> None:
    source = """shape Row:
    id: Int
source rows: Row = postgres.table("rows")
query ranked:
    from rows
    let positive = id > 0
    select:
        rn = row_number() window(order by id)
    qualify:
        positive
"""
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert not semantic.diagnostics
    assert semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    emitted = emit_postgres_sql(lowered.ir)
    assert not emitted.diagnostics
    sql = emitted.artifacts[-1].sql
    assert '"id" AS "__pietto_qualify_0"' in sql
    assert 'WHERE\n    "__pietto_qualify_0" > 0' in sql


def test_grouped_qualify_orders_by_the_completed_aggregate_value() -> None:
    source = """shape Row:
    region: Text
    amount: Int
source orders: Row = postgres.table("orders")
query ranked:
    from orders
    group by:
        region
    select:
        region
        total = sum(amount)
        rn = row_number() window(order by region)
    qualify:
        rn <= 2
    order by:
        total desc
"""
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert not semantic.diagnostics
    assert semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    emitted = emit_postgres_sql(lowered.ir)
    assert not emitted.diagnostics
    sql = emitted.artifacts[-1].sql
    assert 'SUM("amount") AS "__pietto_qualify_0"' in sql
    assert 'ORDER BY\n    "__pietto_qualify_0" DESC' in sql


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("output_format", ("text", "json"))
def test_public_emit_returns_complete_qualify_sql(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], dialect: str, output_format: str
) -> None:
    source = _source(dialect, "query", PREDICATES[0])
    source += "query valid:\n    from rows\n    select:\n        id\n"
    path = tmp_path / "main.pietto"
    path.write_text(source, encoding="utf-8")
    arguments = ["emit-sql", str(path), "--dialect", dialect]
    if output_format == "json":
        arguments += ["--format", "json"]
    assert cli.main(arguments) == 0
    captured = capsys.readouterr()
    if output_format == "json":
        document = json.loads(captured.out)
        assert document["ok"]
        assert document["artifacts"]
        assert not document["diagnostics"]
        assert captured.err == ""
    else:
        assert "SELECT" in captured.out
        assert captured.err == ""
    assert "Traceback" not in captured.err


def test_join_facts_remain_the_precondition_for_joined_qualify() -> None:
    joined = """query joined:
    from rows
    let other = rows
    inner join other on rows.id == other.id
    select:
        id
    qualify:
        True
"""
    for predicate in (None, PREDICATES[0]):
        parsed = parse_source(_source("postgres", "query", predicate) + joined)
        assert parsed.ast is not None
        result = build_ir(parsed.ast, analyze(parsed.ast).model)
        assert result.ir is None
        assert tuple(d.code for d in result.diagnostics) == ("PIE-I1000",)
        assert "resolved JOIN facts" in result.diagnostics[0].message


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
