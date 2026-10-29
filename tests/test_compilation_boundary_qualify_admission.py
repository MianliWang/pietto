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
# The SQL of `_source(..., predicate)` for PostgreSQL; MySQL quotes with
# backticks. A window of the predicate is a hidden port of the derived table.
_QUALIFIED_SQL = {
    predicate: (
        'SELECT\n    "id",\n    "rn"\nFROM (\nSELECT\n    "id" AS "id",\n'
        f'    ROW_NUMBER() OVER (ORDER BY "id" ASC) AS "rn"{port}\n'
        f'FROM "rows"\n) AS "__pietto_qualify"\nWHERE\n    {where}'
    )
    for predicate, port, where in (
        (PREDICATES[0], "", '"rn" <= 1'),
        (PREDICATES[1], "", "TRUE"),
        (
            PREDICATES[2],
            ',\n    ROW_NUMBER() OVER (ORDER BY "id" ASC) AS "__pietto_qualify_0"',
            '"__pietto_qualify_0" <= 1',
        ),
    )
}


def _quoted(sql: str, dialect: str) -> str:
    return sql if dialect == "postgres" else sql.replace('"', "`")


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
    assert tuple(artifact.sql for artifact in emitted.artifacts) == (
        _quoted(_QUALIFIED_SQL[predicate], dialect),
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
    assert tuple(artifact.sql for artifact in emitted.artifacts) == (
        _quoted(
            'SELECT\n    "k",\n    "rn"\nFROM (\nSELECT\n    "id" + 1 AS "k",\n'
            '    ROW_NUMBER() OVER (ORDER BY "id" ASC) AS "rn",\n'
            '    "rows"."id" AS "__pietto_qualify_0"\nFROM "rows" AS "rows"\n'
            ') AS "__pietto_qualify"\nWHERE\n    "__pietto_qualify_0" > 0\n'
            'ORDER BY\n    "rn" DESC\nLIMIT 1',
            dialect,
        ),
    )


# MySQL compares column names without case, so a port also skips an output
# that differs from its name only in case.
@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("name", ("__pietto_qualify_0", "__PIETTO_QUALIFY_0"))
def test_qualify_hidden_ports_freshen_past_a_user_output_name(
    dialect: str, name: str
) -> None:
    source = f"""shape Row:
    id: Int
source rows: Row = {dialect}.table("rows")
query ranked:
    from rows
    select:
        {name} = id
    qualify:
        row_number() window(order by id) <= 1
"""
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert not semantic.diagnostics
    lowered = build_ir(parsed.ast, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    emitted = (emit_postgres_sql if dialect == "postgres" else emit_mysql_sql)(
        lowered.ir
    )
    assert not emitted.diagnostics
    assert tuple(artifact.sql for artifact in emitted.artifacts) == (
        _quoted(
            f'SELECT\n    "{name}"\nFROM (\nSELECT\n    "id" AS "{name}",\n'
            '    ROW_NUMBER() OVER (ORDER BY "id" ASC) AS "__pietto_qualify_1"\n'
            'FROM "rows"\n) AS "__pietto_qualify"\nWHERE\n'
            '    "__pietto_qualify_1" <= 1',
            dialect,
        ),
    )


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


def _grouped_qualify(dialect: str, predicate: str, *, context: str = "grouped") -> str:
    """Line 19, column 9 holds ``predicate``."""

    body = {
        "grouped": """    group by cat
    select:
        cat
        total = sum(price)
        rk = rank() window(order by cat desc)
""",
        "rows": """    select:
        id
        c = cat
        n = price
        rk = rank() window(order by cat desc)
""",
        # Aggregates without GROUP BY: one group without keys.
        "aggregated": """    select:
        total = sum(price)
        n = count()
        low = min(price)
        high = max(price)
""",
    }[context]
    return f"""shape Row:
    id: Int
    cat: Text
    price: Int
source items: Row = {dialect}.table("items")
query g:
    from items
    let p = price
    let pp = price * 2
    let k = cat
    let has = any(o.price > items.price for o in items)
    let hk = any(o.cat == items.cat for o in items)
{body}    qualify:
        {predicate}
"""


def _aggregate_context(name: str) -> str:
    return (
        f"Aggregate {name}() is not allowed in qualify clause; use it only as a "
        "direct aliased select projection"
    )


def _hidden_window(name: str) -> str:
    return (
        f"Unsupported window computation for function {name}: a query with "
        "aggregates and no GROUP BY admits no hidden QUALIFY window"
    )


# Under GROUP BY the rows QUALIFY filters are groups: of the input it reads
# the GROUP BY keys only, also through a `let` or
# inside its `any(...)`, and an aggregate only as the selected output that
# computes it. Aggregates without GROUP BY make one group without keys.
@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize(
    ("predicate", "context", "code", "message"),
    (
        ("price > 10", "grouped", "PIE-S2102", "Unknown field: price"),
        ("items.price > 10", "grouped", "PIE-S2102", "Unknown field: items.price"),
        ("p > 10", "grouped", "PIE-S2102", "Unknown field: p"),
        ("pp > 10", "grouped", "PIE-S2102", "Unknown field: pp"),
        ("has and rk <= 2", "grouped", "PIE-S2102", "Unknown field: has"),
        (
            "rk <= 2 and count() > 1",
            "grouped",
            "PIE-S2308",
            _aggregate_context("count"),
        ),
        ("sum(price) > 5", "grouped", "PIE-S2308", _aggregate_context("sum")),
        ("count(id) > 1", "grouped", "PIE-S2308", _aggregate_context("count")),
        ("min(price) > 1", "grouped", "PIE-S2308", _aggregate_context("min")),
        ("sum(price) > 5", "rows", "PIE-S2308", _aggregate_context("sum")),
        ("count() > 1", "rows", "PIE-S2308", _aggregate_context("count")),
        ("price > 10", "aggregated", "PIE-S2102", "Unknown field: price"),
        ("items.price > 10", "aggregated", "PIE-S2102", "Unknown field: items.price"),
        ("p > 10", "aggregated", "PIE-S2102", "Unknown field: p"),
        ("hk", "aggregated", "PIE-S2102", "Unknown field: hk"),
        ("sum(price) > 5", "aggregated", "PIE-S2308", _aggregate_context("sum")),
        (
            "row_number() window(order by total) <= 1",
            "aggregated",
            "PIE-S2103",
            _hidden_window("row_number"),
        ),
        ("count() window() >= 1", "aggregated", "PIE-S2103", _hidden_window("count")),
    ),
)
def test_qualify_reads_no_value_its_stage_does_not_hold(
    dialect: str, predicate: str, context: str, code: str, message: str
) -> None:
    parsed = parse_source(
        _grouped_qualify(dialect, predicate, context=context), path="main.pietto"
    )
    assert parsed.ast is not None and not parsed.diagnostics
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
    ] == [(code, message, 19, 9)]


def test_grouped_qualify_walks_each_shared_let_value_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pietto.semantic import expressions

    # Each let names the one before it twice: a walk along every path would
    # take 2**40 steps, a walk of each let value once takes some hundreds.
    depth = 40
    lets = "    let a0 = 1\n" + "".join(
        f"    let a{i} = a{i - 1} + a{i - 1}\n" for i in range(1, depth + 1)
    )
    source = _grouped_qualify("postgres", "rk <= 2").replace(
        "    let p = price\n", lets + "    let p = price\n", 1
    )
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    original = expressions._captured_field_children
    calls = 0

    def counted(expression):
        nonlocal calls
        calls += 1
        assert calls <= 20 * depth, "QUALIFY walked a shared let value again"
        return original(expression)

    monkeypatch.setattr(expressions, "_captured_field_children", counted)
    assert analyze(parsed.ast).diagnostics == ()


# The name is still ambiguous under GROUP BY; the message offers the input
# field only where QUALIFY can read it, as a GROUP BY key.
@pytest.mark.parametrize(
    ("predicate", "message"),
    (
        (
            "total > 5",
            "Ambiguous field: total is both the input field items.total and a "
            "SELECT output; give the output another name",
        ),
        (
            'cat != "x"',
            "Ambiguous field: cat is both the input field items.cat and a SELECT "
            "output; write items.cat, or give the output another name",
        ),
    ),
)
def test_grouped_qualify_ambiguity_offers_only_a_readable_input(
    predicate: str, message: str
) -> None:
    source = _grouped_qualify("postgres", predicate).replace(
        "    price: Int\n", "    price: Int\n    total: Int\n", 1
    )
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
    ] == [("PIE-S2102", message, 20, 9)]


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_qualify_without_group_by_reads_the_aggregate_outputs(dialect: str) -> None:
    parsed = parse_source(
        _grouped_qualify(dialect, "total > 5 and n > 1", context="aggregated")
    )
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
    assert tuple(artifact.sql for artifact in emitted.artifacts) == (
        _quoted(
            'SELECT\n    "total",\n    "n",\n    "low",\n    "high"\nFROM (\nSELECT\n'
            '    SUM("price") AS "total",\n    COUNT(*) AS "n",\n'
            '    MIN("price") AS "low",\n    MAX("price") AS "high"\nFROM "items"\n'
            ') AS "__pietto_qualify"\nWHERE\n    ("total" > 5) AND ("n" > 1)',
            dialect,
        ),
    )


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_grouped_qualify_reads_group_keys_and_selected_outputs(dialect: str) -> None:
    parsed = parse_source(
        _grouped_qualify(
            dialect, 'total > 5 and rk <= 2 and items.cat != "x" and k != "y" and hk'
        )
    )
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
    assert tuple(artifact.sql for artifact in emitted.artifacts) == (
        _quoted(
            'SELECT\n    "cat",\n    "total",\n    "rk"\nFROM (\nSELECT\n'
            '    "cat" AS "cat",\n    SUM("price") AS "total",\n'
            '    RANK() OVER (ORDER BY "cat" DESC) AS "rk",\n'
            '    "items"."cat" AS "__pietto_qualify_0"\nFROM "items" AS "items"\n'
            'GROUP BY\n    "cat"\n) AS "__pietto_qualify"\nWHERE\n'
            '    (((("total" > 5) AND ("rk" <= 2)) AND '
            "(\"__pietto_qualify_0\" <> 'x')) AND (\"__pietto_qualify_0\" <> 'y'))"
            ' AND EXISTS (SELECT 1 FROM "items" AS "_pietto_value_2" WHERE '
            '"_pietto_value_2"."cat" = "__pietto_qualify"."__pietto_qualify_0")',
            dialect,
        ),
    )


def _grouped_window_source(dialect: str, select: str, qualify: str) -> str:
    return f"""shape Row:
    id: Int
    cat: Text
    price: Int
source items: Row = {dialect}.table("items")
query q:
    from items
    group by cat
    select:
        c = cat
        cat = max(price)
        n = count()
{select}{qualify}"""


# A window under GROUP BY reads the selected keys and aggregates by their
# output names; a name an output shares with an input field of another value
# is ambiguous there, as in the outer predicate, so neither is read: before,
# `cat` below silently ranked by `max(price)`.
@pytest.mark.parametrize(
    ("select", "qualify", "columns"),
    (
        ("", "    qualify row_number() window(order by cat) <= 2\n", (42,)),
        (
            "",
            "    qualify lag(cat) window(partition by cat order by c) == 1\n",
            (17, 42),
        ),
        ("        rn = row_number() window(order by cat)\n", "", (43,)),
        # Two windows that share a named window read its names once.
        (
            "        rk = rank() window w\n        rn = row_number() window w\n",
            "",
            (29,),
        ),
    ),
    ids=("hidden-order", "hidden-value-partition", "selected", "named-shared"),
)
def test_grouped_window_reads_no_name_an_output_shares_with_an_input(
    select: str, qualify: str, columns: tuple[int, ...]
) -> None:
    source = _grouped_window_source("postgres", select, qualify)
    if "window w" in select:
        source = source.replace(
            "    group by", "    let w = window(order by cat)\n    group by"
        )
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
    ] == [
        (
            "PIE-S2102",
            "Ambiguous field: cat is both the input field items.cat and a SELECT "
            "output; give the output another name",
            8 if "window w" in select else 13,
            column,
        )
        for column in columns
    ]


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_grouped_hidden_window_reads_the_selected_key_and_aggregate(
    dialect: str,
) -> None:
    parsed = parse_source(
        _grouped_window_source(
            dialect,
            "",
            "    qualify rank() window(order by c) <= 1 and "
            "row_number() window(order by n desc) <= 2\n",
        )
    )
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
    assert tuple(artifact.sql for artifact in emitted.artifacts) == (
        _quoted(
            'SELECT\n    "c",\n    "cat",\n    "n"\nFROM (\nSELECT\n'
            '    "cat" AS "c",\n    MAX("price") AS "cat",\n    COUNT(*) AS "n",\n'
            '    RANK() OVER (ORDER BY "cat" ASC) AS "__pietto_qualify_0",\n'
            '    ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) AS "__pietto_qualify_1"\n'
            'FROM "items"\nGROUP BY\n    "cat"\n) AS "__pietto_qualify"\nWHERE\n'
            '    ("__pietto_qualify_0" <= 1) AND ("__pietto_qualify_1" <= 2)',
            dialect,
        ),
    )


# Over a source without a shape a QUALIFY or ORDER BY name that is no selected
# output reads the input by name, through a private port as a typed input
# read does; `explain` and `emit-sql` lower it.
@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_qualify_over_a_source_without_a_shape_carries_its_input_reads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], dialect: str
) -> None:
    path = tmp_path / "main.pietto"
    path.write_text(
        f'source items = {dialect}.table("items")\n'
        "query q:\n    from items\n    select:\n        id\n        e = lower(email)\n"
        '    qualify:\n        items.price > 1 and e != "x" and price < id\n'
        "    order by price\n",
        encoding="utf-8",
    )
    assert cli.main(["explain", str(path)]) == 0
    capsys.readouterr()
    arguments = ["emit-sql", str(path), "--dialect", dialect, "--format", "json"]
    assert cli.main(arguments) == 0
    document = json.loads(capsys.readouterr().out)
    assert document["artifacts"] == [
        {
            "kind": "relation",
            "name": "q",
            "sql": _quoted(
                'SELECT\n    "id",\n    "e"\nFROM (\nSELECT\n    "id" AS "id",\n'
                f"    {'lower' if dialect == 'postgres' else 'LOWER'}"
                '("email") AS "e",\n'
                '    "items"."price" AS "__pietto_qualify_0"\n'
                'FROM "items" AS "items"\n) AS "__pietto_qualify"\nWHERE\n'
                '    (("__pietto_qualify_0" > 1) AND ("e" <> \'x\')) AND '
                '("__pietto_qualify_0" < "id")\n'
                'ORDER BY\n    "__pietto_qualify_0" ASC',
                dialect,
            ),
        }
    ]
    assert [item["code"] for item in document["diagnostics"]] == ["PIE-S2303"]


# Generated collisions: an input field that QUALIFY or ORDER BY reads, directly
# or through a `let`, crosses the derived table by a private port, never by a
# name that a SELECT output holds there (MySQL compares names without case),
# and a shape that matches the table does not change the SQL. Before: over a
# source without a shape the let read named the output and filtered price*2.
# A name that is a SELECT output reads that output over such a source.
@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("shaped", (True, False), ids=("shape", "no-shape"))
@pytest.mark.parametrize(
    ("body", "output", "predicate", "tail"),
    (
        (
            "    let lp = price\n    select:\n        id\n        price = price * 2\n"
            "    qualify:\n        lp > 100\n",
            "price",
            '"__pietto_qualify_0" > 100',
            "",
        ),
        (
            "    select:\n        id\n        Price = price * 2\n"
            "    qualify:\n        price > 100\n",
            "Price",
            '"__pietto_qualify_0" > 100',
            "",
        ),
        (
            "    let p = price\n    select:\n        id\n        price = price * 2\n"
            "    qualify:\n        p > 100\n    order by p\n",
            "price",
            '"__pietto_qualify_0" > 100',
            '\nORDER BY\n    "__pietto_qualify_0" ASC',
        ),
        (
            "    select:\n        id\n        price = price * 2\n"
            "    qualify:\n        price > 100\n",
            "price",
            '"price" > 100',
            "",
        ),
    ),
    ids=("let-same-name", "case-only", "let-in-order-by", "output"),
)
def test_qualify_input_reads_cross_by_a_port_with_or_without_a_shape(
    dialect: str, shaped: bool, body: str, output: str, predicate: str, tail: str
) -> None:
    source = (
        "shape Item:\n    id: Int\n    price: Int\n"
        f'source items: Item = {dialect}.table("items")\n'
        if shaped
        else f'source items = {dialect}.table("items")\n'
    ) + f"query q:\n    from items\n{body}"
    parsed = parse_source(source)
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = analyze(parsed.ast)
    ported = "__pietto_qualify_0" in predicate
    if shaped and not ported:
        # With a shape that name is both an input field and an output.
        assert [item.code for item in semantic.diagnostics] == ["PIE-S2102"]
        return
    assert [item.code for item in semantic.diagnostics] == (
        [] if shaped else ["PIE-S2303"]
    )
    assert semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    emitted = (emit_postgres_sql if dialect == "postgres" else emit_mysql_sql)(
        lowered.ir
    )
    assert not emitted.diagnostics
    inner = f'    "price" * 2 AS "{output}"'
    if ported:
        inner += ',\n    "price" AS "__pietto_qualify_0"'
    assert tuple(artifact.sql for artifact in emitted.artifacts) == (
        _quoted(
            f'SELECT\n    "id",\n    "{output}"\nFROM (\nSELECT\n    "id" AS "id",\n'
            f'{inner}\nFROM "items"\n) AS "__pietto_qualify"\nWHERE\n'
            f"    {predicate}{tail}",
            dialect,
        ),
    )


# Under GROUP BY or aggregates QUALIFY reads the GROUP BY keys of the input
# only, also over a source without a shape, whose other fields it reads by
# name, as its grouping does.
@pytest.mark.parametrize(
    ("body", "name", "column"),
    (
        (
            "    group by cat\n    select:\n        cat\n        total = sum(price)\n"
            "    qualify:\n        price > 1\n",
            "price",
            9,
        ),
        (
            "    select:\n        total = sum(price)\n    qualify:\n        price > 1\n",
            "price",
            9,
        ),
        (
            "    let p = price\n    select:\n        total = sum(price)\n"
            "    qualify:\n        p > 1\n",
            "p",
            9,
        ),
        (
            "    select:\n        n = count()\n    qualify:\n        n > 1 and id == 3\n",
            "id",
            19,
        ),
    ),
)
def test_grouped_qualify_over_a_source_without_a_shape_reads_only_its_keys(
    body: str, name: str, column: int
) -> None:
    source = 'source items = postgres.table("items")\nquery q:\n    from items\n' + body
    parsed = parse_source(source, path="main.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in analyze(parsed.ast).diagnostics
    ] == [
        (
            "PIE-S2303",
            "Source items has no bound shape; row schema is unknown",
            1,
            1,
        ),
        (
            "PIE-S2102",
            f"Unknown field: {name}",
            len(source.splitlines()),
            column,
        ),
    ]


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
    assert captured.err == ""
    sql = {
        "ranked": _quoted(_QUALIFIED_SQL[PREDICATES[0]], dialect),
        "valid": _quoted('SELECT\n    "id" AS "id"\nFROM "rows"', dialect),
    }
    if output_format == "json":
        document = json.loads(captured.out)
        assert document["ok"]
        assert document["artifacts"] == [
            {"kind": "relation", "name": name, "sql": text}
            for name, text in sql.items()
        ]
        assert document["diagnostics"] == []
    else:
        assert captured.out == "\n".join(
            f"-- {name}\n{text};\n" for name, text in sql.items()
        )


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
