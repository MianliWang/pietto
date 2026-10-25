"""SQL identity and placement of local ANY generator filters."""

from __future__ import annotations

import pytest

from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql.postgres import emit_postgres_sql
from pietto.sql.model import SqlResult

_PREFIX = """shape Row:
    id: Int
    active: Bool | None
shape Other:
    id: Int
    active: Bool | None
    threshold: Int
source rows: Row = postgres.table("shop.rows")
source others: Other = postgres.table("shop.others")
relationship Matches(left: Row, right: Other):
    left.id == right.id and right.active
"""


def _sql(body: str) -> SqlResult:
    parsed = parse_source(_PREFIX + body, path="any-sql.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None, parsed.diagnostics
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == () and semantic.script is not None, (
        semantic.diagnostics
    )
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.diagnostics == () and lowered.ir is not None, lowered.diagnostics
    return emit_postgres_sql(lowered.ir)


@pytest.mark.parametrize("negative", (False, True))
def test_any_tail_sql_preserves_true_only_nullable_body(
    negative: bool,
) -> None:
    predicate = (
        "not " if negative else ""
    ) + "any(Matches(rows, candidate) for candidate in others)"
    generated = _sql(
        "query q:\n    from rows\n    where "
        + predicate
        + "\n    select:\n        id = rows.id\n"
    )
    assert generated.diagnostics == ()
    text = generated.artifacts[0].sql
    assert "EXISTS (" in text
    assert "\nWHERE" in text
    assert '."active"' in text
    assert ("NOT" in text) is negative


def test_any_before_right_join_is_placed_in_right_on_not_final_where() -> None:
    result = _sql("""query q:
    from rows
    where any(Matches(rows, candidate) for candidate in others)
    let after = others
    right join after on rows.id == after.id
    select:
        id = after.id
""")
    assert result.diagnostics == ()
    text = result.artifacts[0].sql
    right = text.index("RIGHT JOIN")
    exists = text.index("EXISTS (")
    assert right < exists
    assert "\nWHERE" not in text


def test_any_before_full_join_retains_the_existing_backend_boundary() -> None:
    result = _sql("""query q:
    from rows
    where any(Matches(rows, candidate) for candidate in others)
    let after = others
    full join after on rows.id == after.id
    select:
        id = after.id
""")
    assert result.artifacts == ()
    assert [item.code for item in result.diagnostics] == ["PIE-B1000"]
    assert "A SEMI or ANTI JOIN before FULL JOIN after" in result.diagnostics[0].message


def test_any_tail_let_capture_renders_outer_value_not_local_same_named_field() -> None:
    result = _sql("""query q:
    from rows
    let threshold = rows.id
    where any(candidate.id > threshold for candidate in others)
    select:
        id = rows.id
""")
    assert result.diagnostics == ()
    assert '."id" > "rows"."id"' in result.artifacts[0].sql


def test_not_any_and_any_of_not_keep_distinct_sql_three_valued_meanings() -> None:
    negative_any = _sql("""query q:
    from rows
    where not any(Matches(rows, candidate) for candidate in others)
    select:
        id = rows.id
""")
    negative_body = _sql("""query q:
    from rows
    where any(not Matches(rows, candidate) for candidate in others)
    select:
        id = rows.id
""")
    assert negative_any.diagnostics == negative_body.diagnostics == ()
    assert (
        "NOT" in negative_any.artifacts[0].sql
        and "EXISTS (" in negative_any.artifacts[0].sql
    )
    assert "NOT EXISTS (" not in negative_body.artifacts[0].sql
    assert "EXISTS (" in negative_body.artifacts[0].sql
    assert "NOT " in negative_body.artifacts[0].sql
    assert negative_any.artifacts != negative_body.artifacts


def test_any_select_and_tail_or_preserve_row_count_and_two_valued_truth() -> None:
    import sqlite3

    result = _sql("""query q:
    from rows
    where rows.id == 1 or any(Matches(rows, candidate) for candidate in others)
    select:
        id = rows.id
        matched = any(Matches(rows, candidate) for candidate in others)
        absent = not any(Matches(rows, candidate) for candidate in others)
""")
    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    assert sql.count("EXISTS (") == 3
    with sqlite3.connect(":memory:") as database:
        database.execute("attach database ':memory:' as shop")
        database.execute("create table shop.rows(id integer, active boolean)")
        database.execute(
            "create table shop.others(id integer, active boolean, threshold integer)"
        )
        database.executemany(
            "insert into shop.rows values (?, ?)", ((1, None), (2, True), (3, False))
        )
        database.executemany(
            "insert into shop.others values (?, ?, ?)",
            ((1, None, 0), (2, True, 0), (2, True, 1)),
        )
        assert sorted(database.execute(sql).fetchall()) == [(1, 0, 1), (2, 1, 0)]


def test_any_on_is_scalar_and_keeps_current_target_inside_join_scope() -> None:
    result = _sql("""query q:
    from rows
    let target = others
    left join target on any(candidate.id == target.id and candidate.id == rows.id for candidate in others)
    select:
        id = rows.id
""")
    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    assert sql.index("LEFT JOIN") < sql.index("EXISTS (")
    assert '"target"."id"' in sql and '"rows"."id"' in sql
    assert "\nWHERE" not in sql[: sql.index("EXISTS (")]


def test_nested_any_let_capture_and_shadow_keep_exact_sql_aliases() -> None:
    import sqlite3

    result = _sql("""query q:
    let base = rows
    from base
    let floor = base.id + 1
    select:
        id = base.id
        matched = any(any(nested_row.id == parent_row.id and nested_row.threshold >= floor for nested_row in others) for parent_row in others)
        shadowed = any(base.threshold >= floor for base in others)
""")
    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    assert 'AS "base"' in sql and '"base"."id"' in sql
    with sqlite3.connect(":memory:") as database:
        database.execute("attach database ':memory:' as shop")
        database.execute("create table shop.rows(id integer, active boolean)")
        database.execute(
            "create table shop.others(id integer, active boolean, threshold integer)"
        )
        database.executemany(
            "insert into shop.rows values (?, ?)", ((1, True), (4, False))
        )
        database.execute("insert into shop.others values (7, NULL, 3)")
        assert sorted(database.execute(sql).fetchall()) == [(1, 1, 1), (4, 0, 0)]


def test_any_unknown_predicate_and_not_any_have_distinct_sql_truth() -> None:
    import sqlite3

    result = _sql("""query q:
    from rows
    select:
        unknown_value = any(candidate.active for candidate in others)
        absent = not any(candidate.active for candidate in others)
        negated_body = any(not candidate.active for candidate in others)
        literal_unknown = any(None for candidate in others)
""")
    assert result.diagnostics == ()
    with sqlite3.connect(":memory:") as database:
        database.execute("attach database ':memory:' as shop")
        database.execute("create table shop.rows(id integer, active boolean)")
        database.execute(
            "create table shop.others(id integer, active boolean, threshold integer)"
        )
        database.execute("insert into shop.rows values (1, NULL)")
        database.execute("insert into shop.others values (1, NULL, 0)")
        assert database.execute(result.artifacts[0].sql).fetchall() == [(0, 1, 0, 0)]


def test_any_derived_iterator_cte_dependency_is_emitted_before_reader() -> None:
    result = _sql("""query q:
    from rows
    select:
        matched = any(candidate.id == rows.id for candidate in later)
table later:
    from others
    select:
        id = others.id
""")
    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    assert '"later" AS (' in sql and 'FROM "later" AS' in sql


def test_scalar_wrapper_duplicates_each_any_sql_occurrence() -> None:
    result = _sql("""def Twice(value: Bool) -> Bool | None:
    return value and value
query q:
    from rows
    select:
        duplicated = Twice(any(Matches(rows, candidate) for candidate in others))
""")
    assert result.diagnostics == ()
    assert result.artifacts[0].sql.count("EXISTS (") == 2


_LATER = """table later:
    from others
    select:
        id = others.id
"""


def _hiding(name: str, cte: str, table: str) -> str:
    return (
        f"PostgreSQL SQL emission is not implemented for RelationIR: {name}. "
        f"PostgreSQL scalar ANY defines relation {cte} as a CTE, which would hide "
        f"table {table} read in the same SQL; rename the relation or read the "
        "table with its schema"
    )


# A CTE takes the place of a same-named table read without a schema in the
# CTEs after it and in the main SELECT; emitting it would read the CTE's rows.
@pytest.mark.parametrize(
    ("body", "refused", "emitted"),
    (
        pytest.param(
            'source shadowed: Row = postgres.table("later")\n'
            + _LATER
            + """query q:
    from shadowed
    select:
        id = shadowed.id
        matched = any(candidate.id == shadowed.id for candidate in later)
""",
            (("q", 17, "later", "later"),),
            ("later",),
            id="main-from",
        ),
        pytest.param(
            'source shadowed: Row = postgres.table("later")\n'
            + _LATER
            + """query q:
    from rows
    select:
        id = rows.id
        a = any(candidate.id == rows.id for candidate in later)
        b = any(other.id == rows.id for other in shadowed)
""",
            (("q", 17, "later", "later"),),
            ("later",),
            id="any-over-source",
        ),
        pytest.param(
            'source shadowed: Row = postgres.table("later")\n'
            + _LATER
            + """query q:
    from rows
    inner join shadowed on shadowed.id == rows.id
    select:
        id = rows.id
        matched = any(candidate.id == rows.id for candidate in later)
""",
            (("q", 17, "later", "later"),),
            ("later",),
            id="join-input",
        ),
        pytest.param(
            """source shadowed: Row = postgres.table("prior")
table prior:
    from others
    select:
        id = others.id
table later:
    from others
    where any(p.id == others.id for p in prior) and any(seen.id == others.id for seen in shadowed)
    select:
        id = others.id
query q:
    from rows
    select:
        id = rows.id
        matched = any(candidate.id == rows.id for candidate in later)
""",
            (("later", 17, "prior", "prior"), ("q", 22, "prior", "prior")),
            ("prior",),
            id="later-cte-body",
        ),
        pytest.param(
            """source shadowed: Row = postgres.table("later")
table later:
    from shadowed
    where shadowed.active
    select:
        id = shadowed.id
query q:
    from shadowed
    select:
        id = shadowed.id
        matched = any(candidate.id == shadowed.id for candidate in later)
""",
            (("q", 18, "later", "later"),),
            ("later",),
            id="relation-named-like-its-table",
        ),
    ),
)
def test_any_dependency_cte_never_hides_a_table_read_without_a_schema(
    body: str,
    refused: tuple[tuple[str, int, str, str], ...],
    emitted: tuple[str, ...],
) -> None:
    result = _sql(body)
    assert [
        (
            item.code,
            item.message,
            item.location.path,
            item.location.line,
            item.location.column,
        )
        for item in result.diagnostics
    ] == [
        ("PIE-B1000", _hiding(name, cte, table), "any-sql.pietto", line, 1)
        for name, line, cte, table in refused
    ]
    assert tuple(artifact.name for artifact in result.artifacts) == emitted


# The CTE's own body and a table named with its schema still read the table.
@pytest.mark.parametrize(
    ("body", "sql"),
    (
        pytest.param(
            """source shadowed: Row = postgres.table("later")
table later:
    from shadowed
    where shadowed.active
    select:
        id = shadowed.id
query q:
    from rows
    select:
        id = rows.id
        matched = any(candidate.id == rows.id for candidate in later)
""",
            '''WITH "later" AS (
SELECT
    "shadowed"."id" AS "id"
FROM "later" AS "shadowed"
WHERE "shadowed"."active"
)
SELECT
    "rows"."id" AS "id",
    EXISTS (SELECT 1 FROM "later" AS "_pietto_value_1" WHERE "_pietto_value_1"."id" = "rows"."id") AS "matched"
FROM "shop"."rows" AS "rows"''',
            id="own-body",
        ),
        pytest.param(
            'source shadowed: Row = postgres.table("shop.later")\n'
            + _LATER
            + """query q:
    from shadowed
    select:
        id = shadowed.id
        matched = any(candidate.id == shadowed.id for candidate in later)
""",
            '''WITH "later" AS (
SELECT
    "others"."id" AS "id"
FROM "shop"."others" AS "others"
)
SELECT
    "shadowed"."id" AS "id",
    EXISTS (SELECT 1 FROM "later" AS "_pietto_value_1" WHERE "_pietto_value_1"."id" = "shadowed"."id") AS "matched"
FROM "shop"."later" AS "shadowed"''',
            id="schema-qualified",
        ),
    ),
)
def test_any_dependency_cte_keeps_reads_it_cannot_hide(body: str, sql: str) -> None:
    result = _sql(body)
    assert result.diagnostics == ()
    assert [artifact.name for artifact in result.artifacts] == ["later", "q"]
    assert result.artifacts[1].sql == sql


def test_an_any_chain_operand_emits_the_exists_of_each_comparison() -> None:
    """``a == any(...) == c`` reads its inner ANY in both comparisons, each its
    own occurrence, so it emits the SQL of the comparisons written out."""
    test = "any(Matches(rows, candidate) for candidate in others)"
    chain, written = (
        _sql(f"query q:\n    from rows\n    select:\n        x = {value}\n")
        for value in (
            f"False == {test} == True",
            f"False == {test} and {test} == True",
        )
    )
    assert chain.diagnostics == written.diagnostics == ()
    assert chain.artifacts[0].sql == written.artifacts[0].sql
    assert chain.artifacts[0].sql.count("EXISTS (") == 2
