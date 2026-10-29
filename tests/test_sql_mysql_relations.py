from __future__ import annotations

import inspect
import sys
from dataclasses import replace
from typing import Callable

import pytest

import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.sql.mysql as mysql_module
import pietto.sql.mysql_relations as relation_module
from pietto.errors import Severity
from pietto.ir import (
    CallIR,
    ComparisonIR,
    FieldRefIR,
    LiteralIR,
    RelationIR,
    ScriptIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.sql import SqlArtifactKind, SqlResult
from pietto.sql.mysql import emit_mysql_sql

SOURCE = (
    "shape User:\n"
    "    email: Text | None\n"
    "    age: Int\n"
    "    deleted_at: Timestamp | None\n"
    'source users: User = mysql.table("app.users")\n'
)


def test_source_backed_relation_renders_approved_format() -> None:
    result = emit_mysql_sql(
        _compile(
            SOURCE + "table active_users:\n"
            "    from users\n"
            "    where deleted_at is None\n"
            "    select:\n"
            "        email\n"
            "        normalized = lower(trim(email))\n"
            "        email_length = len(email)\n"
        )
    )

    assert len(result.artifacts) == 1
    artifact = result.artifacts[0]
    assert artifact.name == "active_users"
    assert artifact.kind is SqlArtifactKind.RELATION
    assert artifact.sql == (
        "SELECT\n"
        "    `email` AS `email`,\n"
        "    LOWER(TRIM(`email`)) AS `normalized`,\n"
        "    CHAR_LENGTH(`email`) AS `email_length`\n"
        "FROM `app`.`users`\n"
        "WHERE `deleted_at` IS NULL"
    )
    assert result.diagnostics == ()


def test_decimal_int_membership_renders_as_written() -> None:
    # `amount in (1, 2)` checks like `amount == 1 or amount == 2`; neither
    # side is cast.
    result = emit_mysql_sql(
        _compile(
            "type Money = Decimal(12, 2)\n"
            "shape Acct:\n"
            "    amount: Decimal(12, 2)\n"
            "    n: Int\n"
            "    m: Money\n"
            'source accts: Acct = mysql.table("accts")\n'
            "table q:\n"
            "    from accts\n"
            "    let listed = m in (n, None)\n"
            "    where amount in (1, 2)\n"
            "    select:\n"
            "        n\n"
            "        r = n not in (amount, -3)\n"
            "        s = listed\n"
        )
    )

    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n"
        "    `n` AS `n`,\n"
        "    `n` NOT IN (`amount`, (-3)) AS `r`,\n"
        "    `m` IN (`n`, NULL) AS `s`\n"
        "FROM `accts`\n"
        "WHERE `amount` IN (1, 2)"
    ]
    assert result.diagnostics == ()


def test_abs_of_every_numeric_type_renders_as_written() -> None:
    result = emit_mysql_sql(
        _compile(
            "shape Acct:\n"
            "    n: Int\n"
            "    f: Float | None\n"
            "    d: Decimal(10, 2)\n"
            'source accts: Acct = mysql.table("accts")\n'
            "table q:\n"
            "    from accts\n"
            "    where abs(n - 1) < 3\n"
            "    select:\n"
            "        an = abs(n)\n"
            "        af = abs(f)\n"
            "        ad = abs(d)\n"
            "        al = abs(-2)\n"
        )
    )

    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n"
        "    ABS(`n`) AS `an`,\n"
        "    ABS(`f`) AS `af`,\n"
        "    ABS(`d`) AS `ad`,\n"
        "    ABS((-2)) AS `al`\n"
        "FROM `accts`\n"
        "WHERE ABS((`n` - 1)) < 3"
    ]
    assert result.diagnostics == ()


def test_relation_reference_and_artifact_order_are_stable() -> None:
    result = emit_mysql_sql(
        _compile(
            SOURCE + "table first:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
            "query second:\n"
            "    from first\n"
            "    select:\n"
            "        email\n"
        )
    )

    assert [artifact.name for artifact in result.artifacts] == ["first", "second"]
    assert result.artifacts[0].sql.endswith("FROM `app`.`users`")
    # `second` defines `first`, the table it reads, as a CTE.
    assert result.artifacts[1].sql.startswith(
        f"WITH `first` AS (\n{result.artifacts[0].sql}\n)\nSELECT\n"
    )
    assert result.artifacts[1].sql.endswith("FROM `first`")
    assert result.diagnostics == ()


@pytest.mark.parametrize(
    ("table", "hidden"), (("kept", True), ("KEPT", True), ("app.kept", False))
)
def test_a_cte_that_could_hide_a_table_the_statement_reads_is_refused(
    table: str, hidden: bool
) -> None:
    """MySQL may compare a CTE name and a table name without case."""

    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n"
            'source raw: Row = mysql.table("raw_rows")\n'
            f'source shadow: Row = mysql.table("{table}")\n'
            "table kept:\n    from raw\n    select:\n        id\n"
            "query q:\n    from kept\n    where any(s.id == kept.id for s in shadow)\n"
            "    select:\n        id\n"
        )
    )

    if not hidden:
        assert result.diagnostics == ()
        assert result.artifacts[1].sql.startswith("WITH `kept` AS (\n")
        return
    assert [artifact.name for artifact in result.artifacts] == ["kept"]
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            "MySQL SQL emission is not implemented for RelationIR: q. Its SQL "
            f"defines relation kept as a CTE, which would hide table {table} read "
            "in the same SQL; rename the relation or read the table with its schema",
        )
    ]


def test_ctes_whose_names_differ_only_in_case_are_refused() -> None:
    """MySQL may compare CTE names without case, so one WITH cannot hold both."""

    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n"
            'source raw: Row = mysql.table("raw_rows")\n'
            "table Kept:\n    from raw\n    select:\n        id\n"
            "table kept:\n    from raw\n    select:\n        id\n"
            "query q:\n    from Kept\n    where any(k.id == Kept.id for k in kept)\n"
            "    select:\n        id\n"
        )
    )

    assert [artifact.name for artifact in result.artifacts] == ["Kept", "kept"]
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            "MySQL SQL emission is not implemented for RelationIR: q. Its SQL "
            "defines relations Kept and kept as CTEs, whose names MySQL may "
            "compare without case; rename one of them",
        )
    ]


def test_round_float_reads_a_relation_output_only_as_a_double() -> None:
    """PostgreSQL holds an output of exact values alone as numeric, which MySQL
    may compute as a DOUBLE, so their round(Float) could differ."""

    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n    ratio: Float\n"
            'source items: Row = mysql.table("items")\n'
            "table k:\n    from items\n    select:\n        id\n"
            "        v = 0.5 - 0.00000000000000001\n        w = ratio * 2\n"
            "        a = avg(id) window(order by id)\n"
            "query exact:\n    from k\n    select:\n        r = round(v)\n"
            "query double:\n    from k\n    select:\n        id\n"
            "        x = w\n    qualify:\n"
            "        round(x) > row_number() window(order by id)\n"
            "query full:\n    from items\n    let kk = k\n"
            "    full join kk on kk.id == items.id\n    select:\n"
            "        id = items.id\n        r = round(kk.w + kk.a - 0.5)\n"
        )
    )

    assert [artifact.name for artifact in result.artifacts] == ["k", "double", "full"]
    assert "TRUNCATE(`x`, 0)" in result.artifacts[1].sql
    assert "UNION ALL" in result.artifacts[2].sql
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            "MySQL SQL emission is not implemented for RelationIR: exact. MySQL "
            "function round(Float) reads Float field v, which is not proved a "
            "DOUBLE on both targets",
        )
    ]


def test_round_float_proves_each_output_of_a_deep_chain_of_reads_once() -> None:
    """The proof walks reads on an explicit stack and decides each relation
    output once, so neither depth nor two outputs that each read both upstream
    outputs make it exhaust the recursion limit or grow with every layer."""

    depth = sys.getrecursionlimit() + 10
    script_ir = _compile(
        "shape T:\n    f: Float\n    h: Float\n"
        'source t0: T = mysql.table("t0")\n'
        "table t1:\n    from t0\n    select:\n        f\n        h\n"
        "        g = 0.5 - 0.00000000000000001\n"
        + "".join(
            f"table t{index}:\n    from t{index - 1}\n    select:\n"
            "        f = f + h\n        h = h + f\n        g = g + f\n"
            for index in range(2, depth + 1)
        )
        + f"query double:\n    from t{depth}\n    select:\n        r = round(f)\n"
        + f"query exact:\n    from t{depth}\n    select:\n        r = round(g)\n"
    )
    sources = {
        item.symbol: item
        for item in script_ir.definitions
        if isinstance(item, SourceIR)
    }
    relations = {
        item.symbol: item
        for item in script_ir.definitions
        if isinstance(item, RelationIR)
    }

    assert relation_module.render_mysql_relation(
        _definition(script_ir, RelationIR, "double"),
        sources=sources,
        relations=relations,
    ).endswith(
        "\nSELECT\n    CASE WHEN ABS(`f` - TRUNCATE(`f`, 0)) >= 0.5 THEN "
        "TRUNCATE(`f`, 0) + CASE WHEN `f` < 0 THEN -1.0 ELSE 1.0 END "
        f"ELSE TRUNCATE(`f`, 0) END AS `r`\nFROM `t{depth}`"
    )
    with pytest.raises(
        relation_module.MySqlRenderError,
        match=r"^MySQL function round\(Float\) reads Float field g, which is not "
        "proved a DOUBLE on both targets$",
    ):
        relation_module.render_mysql_relation(
            _definition(script_ir, RelationIR, "exact"),
            sources=sources,
            relations=relations,
        )


def test_round_float_reads_a_float_expression_as_deep_as_let_inlining_admits() -> None:
    """The DOUBLE check of round(Float) and of the outputs it reads walks an
    expression on an explicit stack, so a let-inlined Float expression that
    PostgreSQL emits never exhausts the recursion limit on MySQL."""

    terms = " + ".join(["ratio"] * 251)
    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n    ratio: Float\n"
            'source items: Row = mysql.table("items")\n'
            "query q:\n    from items\n"
            f"    let a1 = {terms}\n    let a2 = a1 + {terms}\n"
            "    select:\n        r = round(a2)\n"
            "table k:\n    from items\n"
            f"    let b1 = {terms}\n    let b2 = b1 + {terms}\n"
            "    select:\n        v = b2\n"
            "query fin:\n    from k\n    select:\n        r = round(v)\n"
        )
    )

    assert result.diagnostics == ()
    assert [artifact.name for artifact in result.artifacts] == ["q", "k", "fin"]
    assert result.artifacts[2].sql.endswith(
        "SELECT\n    CASE WHEN ABS(`v` - TRUNCATE(`v`, 0)) >= 0.5 THEN "
        "TRUNCATE(`v`, 0) + CASE WHEN `v` < 0 THEN -1.0 ELSE 1.0 END "
        "ELSE TRUNCATE(`v`, 0) END AS `r`\nFROM `k`"
    )


def test_outputs_that_differ_only_in_case_never_share_a_cte_or_derived_table() -> None:
    """MySQL compares column names without case, and a CTE body or a derived
    table must name its columns uniquely; a top-level SELECT may repeat one."""

    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n    price: Int\n"
            'source items: Row = mysql.table("items")\n'
            "table pair:\n    from items\n    select:\n        a = id\n"
            "        A = price\n"
            "query reader:\n    from pair\n    select:\n        a\n"
            "query q_case:\n    from items\n    select:\n        a = id\n"
            "        A = price\n"
            "    qualify:\n        row_number() window(order by id) <= 2\n"
            "query q_reader:\n    from q_case\n    select:\n        a\n"
        )
    )

    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n    `id` AS `a`,\n    `price` AS `A`\nFROM `items`"
    ]
    derived = (
        "Its QUALIFY derived table has outputs a and A, whose names MySQL "
        "compares without case; rename one of them"
    )
    assert [
        (item.code, item.message, item.location.line) for item in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            "MySQL SQL emission is not implemented for RelationIR: reader. Its SQL "
            "defines relation pair as a CTE with outputs a and A, whose names "
            "MySQL compares without case; rename one of them",
            10,
        ),
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: q_case. {derived}",
            14,
        ),
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: q_reader. {derived}",
            21,
        ),
    ]


# MySQL names an unaliased item by rules of its own, and a CTE's column names
# must differ without case: in a CTE each unaliased output (PIE-S2304 warns
# of it) takes a private alias, while the relation's own SELECT keeps it
# unaliased. Before: `"ID"` beside `id` and `"x"` twice were refused.
@pytest.mark.parametrize(
    "outputs",
    ('"ID"', '"x"\n        "x"', '"x"\n        lower(cat)'),
    ids=("value", "twice", "distinct"),
)
def test_an_unnamed_cte_output_takes_a_private_alias(outputs: str) -> None:
    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n    cat: Text\n"
            'source items: Row = mysql.table("items")\n'
            f"table base:\n    from items\n    select:\n        id\n        {outputs}\n"
            "query reader:\n    from base\n    select:\n        id\n"
        )
    )

    items = [
        "LOWER(`cat`)" if item == "lower(cat)" else item.replace('"', "'")
        for item in outputs.split("\n        ")
    ]
    aliased = [
        f"{item} AS `__pietto_column_{number}`"
        for number, item in enumerate(items, start=1)
    ]
    assert result.diagnostics == ()
    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n    `id` AS `id`,\n    " + ",\n    ".join(items) + "\nFROM `items`",
        "WITH `base` AS (\nSELECT\n    `id` AS `id`,\n    "
        + ",\n    ".join(aliased)
        + "\nFROM `items`\n)\nSELECT\n    `id` AS `id`\nFROM `base`",
    ]


# MySQL binds a bare ORDER BY name, compared without case, to a SELECT item by
# rules of its own; beside an unaliased item or another output whose name
# differs only in case, an output key sorts by its position. Before: these
# were refused, or bound by MySQL's rules as Pietto emulated them.
@pytest.mark.parametrize(
    ("source", "body", "position"),
    (
        (
            "items: Row",
            "    select:\n        id\n        RN = 0 - price\n"
            "        rn = row_number() window(order by price)\n    order by rn\n",
            3,
        ),
        (
            "items: Row",
            '    select:\n        id\n        "rn"\n'
            "        rn = row_number() window(order by price)\n    order by rn\n",
            3,
        ),
        (
            "items: Row",
            '    select:\n        id\n        " rn"\n'
            "        rn = row_number() window(order by price)\n    order by rn\n",
            3,
        ),
        (
            "items",
            "    select:\n        id\n        price\n        PRICE = 0 - price\n"
            "    order by price\n",
            2,
        ),
        (
            "items: Row",
            "    group by cat\n    select:\n        cat\n        N = count()\n"
            "        n = rank() window(order by cat)\n    order by n\n",
            3,
        ),
        (
            "items: Row",
            "    select:\n        id\n        Rn = id\n"
            "        rn = row_number() window(order by price)\n    order by rn\n",
            3,
        ),
        (
            "items: Row",
            "    group by cat\n    select:\n        cat\n"
            "        n = rank() window(order by cat)\n        N = count()\n"
            "    order by n\n",
            2,
        ),
    ),
    ids=(
        "computed",
        "literal",
        "spaced-literal",
        "later",
        "grouped",
        "column",
        "first",
    ),
)
def test_an_order_by_output_key_is_never_bound_to_another_item(
    source: str, body: str, position: int
) -> None:
    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n    cat: Text\n    price: Int\n"
            f'source {source} = mysql.table("items")\n'
            f"table q:\n    from items\n{body}"
        )
    )

    assert result.diagnostics == ()
    sql = result.artifacts[0].sql
    assert sql.endswith(f"ORDER BY\n    {position} ASC")
    key = body.rsplit(" ", 1)[1].strip()
    selected = sql.split("\nFROM ", 1)[0].split(",\n    ")
    assert selected[position - 1].endswith(f" AS `{key}`")


_QUALIFY_ANY = (
    "shape Row:\n    id: Int\n"
    "shape Ord:\n    item_id: Int\n    qty: Int\n"
    'source items: Row = mysql.table("items")\n'
    'source orders: Ord = mysql.table("orders")\n'
    "table big_orders:\n    from orders\n    where qty > 10\n    select:\n"
    "        item_id\n"
    "table q_any:\n    from items\n"
    "    let has = any(b.item_id == items.id for b in big_orders)\n"
    "    select:\n        id\n        rn = row_number() window(order by id)\n"
)
_QUALIFY_ANY_EXISTS = (
    "EXISTS (SELECT 1 FROM `big_orders` AS `_pietto_value_1` "
    "WHERE `_pietto_value_1`.`item_id` = `__pietto_qualify`.`__pietto_qualify_0`)"
)


@pytest.mark.parametrize(
    ("clauses", "outer"),
    (
        (
            "    qualify:\n        rn <= 3 and has\n",
            f"WHERE\n    (`rn` <= 3) AND {_QUALIFY_ANY_EXISTS}",
        ),
        (
            "    qualify:\n        rn <= 3\n    order by has desc, id\n",
            f"WHERE\n    `rn` <= 3\nORDER BY\n    {_QUALIFY_ANY_EXISTS} DESC,\n"
            "    `__pietto_qualify_0` ASC",
        ),
    ),
    ids=("qualify", "order_by_after_qualify"),
)
def test_a_qualify_statement_defines_the_relations_its_outer_stage_reads(
    clauses: str, outer: str
) -> None:
    result = emit_mysql_sql(_compile(_QUALIFY_ANY + clauses))

    assert result.diagnostics == ()
    assert result.artifacts[-1].sql == (
        "WITH `big_orders` AS (\nSELECT\n    `item_id` AS `item_id`\n"
        "FROM `orders`\nWHERE `qty` > 10\n)\n"
        "SELECT\n    `id`,\n    `rn`\nFROM (\nSELECT\n    `id` AS `id`,\n"
        "    ROW_NUMBER() OVER (ORDER BY `id` ASC) AS `rn`,\n"
        "    `items`.`id` AS `__pietto_qualify_0`\nFROM `items` AS `items`\n"
        f") AS `__pietto_qualify`\n{outer}"
    )


def test_a_qualify_port_read_inside_exists_names_its_derived_table() -> None:
    """MySQL compares column names without case, so a column spelled in
    capitals would capture a bare port inside EXISTS."""

    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n"
            "shape Ord:\n    __PIETTO_QUALIFY_0: Int\n"
            'source items: Row = mysql.table("items")\n'
            'source orders: Ord = mysql.table("orders")\n'
            "query q_any:\n    from items\n"
            "    let has = any(o.__PIETTO_QUALIFY_0 == items.id for o in orders)\n"
            "    select:\n        id\n        rn = row_number() window(order by id)\n"
            "    qualify:\n        rn <= 3 and has\n"
        )
    )

    assert result.diagnostics == ()
    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n    `id`,\n    `rn`\nFROM (\nSELECT\n    `id` AS `id`,\n"
        "    ROW_NUMBER() OVER (ORDER BY `id` ASC) AS `rn`,\n"
        "    `items`.`id` AS `__pietto_qualify_0`\nFROM `items` AS `items`\n"
        ") AS `__pietto_qualify`\nWHERE\n    (`rn` <= 3) AND EXISTS (SELECT 1 "
        "FROM `orders` AS `_pietto_value_1` WHERE "
        "`_pietto_value_1`.`__PIETTO_QUALIFY_0` = "
        "`__pietto_qualify`.`__pietto_qualify_0`)"
    ]


@pytest.mark.parametrize(
    ("limit", "limit_sql"),
    [
        # Without its own LIMIT, MySQL could merge the CTE into each read and
        # run its windows once per read.
        pytest.param("", "LIMIT 18446744073709551615", id="every-row"),
        pytest.param("    limit 2\n", "LIMIT 2", id="authored"),
    ],
)
def test_a_qualify_relation_read_as_a_cte_defines_each_relation_once(
    limit: str, limit_sql: str
) -> None:
    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n    cat: Text\n"
            'source items: Row = mysql.table("items")\n'
            "table base:\n    from items\n    select:\n        id\n        cat\n"
            "table top:\n    from base\n    select:\n        id\n        cat\n"
            "        rn = row_number() window(partition by cat order by id)\n"
            f"    qualify:\n        rn == 1\n{limit}"
            "query reader:\n    from top\n    where id > 5\n    select:\n"
            "        id\n"
        )
    )

    assert result.diagnostics == ()
    assert result.artifacts[-1].sql == (
        "WITH `base` AS (\nSELECT\n    `id` AS `id`,\n    `cat` AS `cat`\n"
        "FROM `items`\n),\n"
        "`top` AS (\nSELECT\n    `id`,\n    `cat`,\n    `rn`\nFROM (\nSELECT\n"
        "    `id` AS `id`,\n    `cat` AS `cat`,\n"
        "    ROW_NUMBER() OVER (PARTITION BY `cat` ORDER BY `id` ASC) AS `rn`\n"
        "FROM `base`\n) AS `__pietto_qualify`\nWHERE\n    `rn` = 1\n"
        f"{limit_sql}\n)\n"
        "SELECT\n    `id` AS `id`\nFROM `top`\nWHERE `id` > 5"
    )


def test_a_relation_read_only_by_a_qualify_any_refuses_its_reader() -> None:
    result = emit_mysql_sql(
        _compile(
            "shape Row:\n    id: Int\n    name: Text\n"
            'source items: Row = mysql.table("items")\n'
            "table bad:\n    from items\n    select:\n        id\n"
            '        s = matches(name, "@")\n'
            "query reader:\n    from items\n"
            "    let has = any(b.id == items.id for b in bad)\n"
            "    select:\n        id\n        rn = row_number() window(order by id)\n"
            "    qualify:\n        has\n"
        )
    )

    assert result.artifacts == ()
    assert [
        (item.code, item.message, item.location.line) for item in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: {name}. "
            "Unsupported MySQL function call: matches",
            line,
        )
        for name, line in (("bad", 5), ("reader", 10))
    ]


def test_a_relation_whose_sql_is_refused_refuses_its_readers() -> None:
    """A reader is never emitted with a by-name read of a refused relation."""

    result = emit_mysql_sql(
        _compile(
            SOURCE + "table refused:\n    from users\n"
            '    where matches(email, "@")\n    select:\n        age\n'
            "query reader:\n    from users\n    let r = refused\n"
            "    inner join r on users.age == r.age\n    select:\n        users.age\n"
            "table direct:\n    from users\n    select:\n        age\n"
        )
    )

    assert [artifact.name for artifact in result.artifacts] == ["direct"]
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: {name}. "
            "Unsupported MySQL function call: matches",
        )
        for name in ("refused", "reader")
    ]


_JOINED = (
    "shape Order:\n    id: Int\n    customer_id: Int | None\n    amount: Int\n"
    "    status: Status\n"
    "shape Customer:\n    id: Int\n    name: Text\n    region_id: Int | None\n"
    "enum Status:\n    open\n    closed\n"
    'source orders: Order = mysql.table("shop.orders")\n'
    'source customers: Customer = mysql.table("shop.customers")\n'
)


def test_a_join_reads_a_relation_of_the_file_as_a_cte() -> None:
    result = emit_mysql_sql(
        _compile(
            _JOINED + "table named:\n    from customers\n"
            '    where name != ""\n    select:\n        id\n        name\n'
            "query q:\n    from orders\n    let c = named\n"
            "    left join c on orders.customer_id == c.id\n    select:\n"
            "        oid = orders.id\n        cname = c.name\n"
        )
    )

    assert result.diagnostics == ()
    assert result.artifacts[-1].sql == (
        "WITH `named` AS (\nSELECT\n    `id` AS `id`,\n    `name` AS `name`\n"
        "FROM `shop`.`customers`\nWHERE `name` <> ''\n)\n"
        "SELECT\n    `orders`.`id` AS `oid`,\n    `c`.`name` AS `cname`\n"
        "FROM `shop`.`orders` AS `orders`\n"
        "LEFT JOIN `named` AS `c` ON `orders`.`customer_id` = `c`.`id`"
    )


def test_an_any_inside_a_join_on_reads_its_table_correlated() -> None:
    result = emit_mysql_sql(
        _compile(
            _JOINED + "query q:\n    from orders\n    let c = customers\n"
            "    inner join c on orders.customer_id == c.id and "
            "any(o.amount > orders.amount for o in orders)\n"
            "    select:\n        oid = orders.id\n"
        )
    )

    assert result.diagnostics == ()
    assert result.artifacts[-1].sql == (
        "SELECT\n    `orders`.`id` AS `oid`\nFROM `shop`.`orders` AS `orders`\n"
        "INNER JOIN `shop`.`customers` AS `c` ON (`orders`.`customer_id` = `c`.`id`) "
        "AND EXISTS (SELECT 1 FROM `shop`.`orders` AS `_pietto_value_1` "
        "WHERE `_pietto_value_1`.`amount` > `orders`.`amount`)"
    )


def test_a_qualify_over_a_join_keeps_its_hidden_input_port() -> None:
    result = emit_mysql_sql(
        _compile(
            _JOINED + "query q:\n    from orders\n    let c = customers\n"
            "    inner join c on orders.customer_id == c.id\n    select:\n"
            "        oid = orders.id\n"
            "    qualify:\n        c.region_id is not None and "
            "row_number() window(partition by c.id order by orders.id) <= 2\n"
        )
    )

    assert result.diagnostics == ()
    assert result.artifacts[-1].sql == (
        "SELECT\n    `oid`\nFROM (\nSELECT\n    `orders`.`id` AS `oid`,\n"
        "    ROW_NUMBER() OVER (PARTITION BY `c`.`id` ORDER BY `orders`.`id` ASC) "
        "AS `__pietto_qualify_0`,\n    `c`.`region_id` AS `__pietto_qualify_1`\n"
        "FROM `shop`.`orders` AS `orders`\n"
        "INNER JOIN `shop`.`customers` AS `c` ON `orders`.`customer_id` = `c`.`id`\n"
        ") AS `__pietto_qualify`\nWHERE\n"
        "    (`__pietto_qualify_1` IS NOT NULL) AND (`__pietto_qualify_0` <= 2)"
    )


def test_a_full_join_derived_table_skips_an_alias_of_its_name_in_any_case() -> None:
    """MySQL may compare aliases without case, so `__PIETTO_FULL` would be the
    derived table `__pietto_full`."""

    result = emit_mysql_sql(
        _compile(
            _JOINED + "query q:\n    from orders\n    let __PIETTO_FULL = customers\n"
            "    full join __PIETTO_FULL on orders.customer_id == __PIETTO_FULL.id\n"
            "    select:\n        a = orders.id\n"
        )
    )

    assert result.diagnostics == ()
    branch = (
        "SELECT\n    `orders`.`id` AS `__pietto_full2_0`\n"
        "FROM `shop`.`orders` AS `orders`\n"
        "{} JOIN `shop`.`customers` AS `__PIETTO_FULL` "
        "ON `orders`.`customer_id` = `__PIETTO_FULL`.`id`\n"
    )
    assert result.artifacts[-1].sql == (
        "SELECT\n    `__pietto_full2`.`__pietto_full2_0` AS `a`\nFROM (\n"
        + branch.format("LEFT")
        + "UNION ALL\n"
        + branch.format("RIGHT")
        + "WHERE `orders`.`customer_id` IS NULL\n) AS `__pietto_full2`"
    )


@pytest.mark.parametrize(
    ("body", "message"),
    [
        pytest.param(
            "query q:\n    from orders\n    let c = customers\n"
            "    inner join c on orders.customer_id == c.id\n"
            "    let C = customers\n    inner join C on orders.customer_id == C.id\n"
            "    select:\n        a = c.name\n        b = C.name\n",
            "Its SQL aliases inputs c and C, whose names MySQL may compare without "
            "case; rename one of them",
            id="two-bindings",
        ),
        pytest.param(
            "query q:\n    from orders\n    let Orders = orders\n"
            "    cross join Orders\n    select:\n        a = orders.id\n"
            "        b = Orders.id\n",
            "Its SQL aliases inputs orders and Orders, whose names MySQL may compare "
            "without case; rename one of them",
            id="binding-and-from",
        ),
        pytest.param(
            "query q:\n    from orders\n    let c = customers\n"
            "    inner join c on orders.customer_id == c.id\n"
            "    let C = customers\n    inner join C on orders.customer_id == C.id\n"
            "    select:\n        a = c.name\n        A = C.name\n"
            "    qualify:\n        row_number() window(order by orders.id) <= 2\n",
            "Its SQL aliases inputs c and C, whose names MySQL may compare without "
            "case; rename one of them",
            id="two-bindings-before-qualify-outputs",
        ),
        pytest.param(
            "query q:\n    from orders\n    let __PIETTO_FULL = customers\n"
            "    full join __PIETTO_FULL on orders.customer_id == __PIETTO_FULL.id "
            "and orders.amount > 0\n"
            "    select:\n        a = orders.id\n",
            "MySQL FULL JOIN __PIETTO_FULL needs an ON made only of equalities "
            "between Int fields of its two sides; Pietto does not rewrite other "
            "FULL JOIN conditions yet",
            id="full-derived-table-alias-outside-full-limits",
        ),
        pytest.param(
            "query q:\n    from orders\n    let c = customers\n"
            "    full join c on orders.customer_id == c.id\n"
            "    select:\n        cid = c.id\n        status = orders.status\n",
            "MySQL emulates FULL JOIN c with UNION ALL, which keeps the column types "
            "of builtin types other than Any only; orders.status has type Status",
            id="full-enum-port",
        ),
        pytest.param(
            "query q:\n    from orders\n"
            + "".join(
                f"    let c{index} = customers\n"
                f"    full join c{index} on orders.id == c{index}.id\n"
                for index in range(9)
            )
            + "    select:\n        a = orders.id\n",
            "MySQL emulates at most 8 FULL JOINs in one relation, as each repeats "
            "the inputs before it",
            id="full-past-the-doubling-limit",
        ),
        pytest.param(
            "query q:\n    from orders\n"
            + "".join(
                f"    let c{index} = customers\n"
                f"    full join c{index} on orders.id == c{index}.id"
                + (" and orders.amount > 0\n" if index == 8 else "\n")
                for index in range(9)
            )
            + "    select:\n        a = orders.id\n",
            "MySQL FULL JOIN c8 needs an ON made only of equalities between Int "
            "fields of its two sides; Pietto does not rewrite other FULL JOIN "
            "conditions yet",
            id="full-predicate-before-the-doubling-limit",
        ),
        pytest.param(
            "query q:\n    from orders\n"
            "    where any(x.id == orders.customer_id for x in customers)\n"
            + "".join(
                f"    let c{index} = customers\n"
                f"    full join c{index} on orders.id == c{index}.id\n"
                for index in range(9)
            )
            + "    select:\n        a = orders.id\n",
            "A SEMI or ANTI JOIN before FULL JOIN c0 is not available in MySQL "
            "emission yet",
            id="full-pending-filter-before-the-doubling-limit",
        ),
        pytest.param(
            "query q:\n    from orders\n    let c = customers\n"
            "    full join c on orders.customer_id == c.id\n"
            "    let d = customers\n"
            "    full join d on orders.id == d.id and orders.amount > 0\n"
            "    select:\n        status = orders.status\n",
            "MySQL FULL JOIN d needs an ON made only of equalities between Int "
            "fields of its two sides; Pietto does not rewrite other FULL JOIN "
            "conditions yet",
            id="full-predicate-before-an-earlier-enum-port",
        ),
    ],
)
def test_mysql_refuses_a_join_it_cannot_keep_exact(body: str, message: str) -> None:
    result = emit_mysql_sql(_compile(_JOINED + body))

    assert result.artifacts == ()
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: q. {message}",
        )
    ]


def test_a_join_cte_with_outputs_that_differ_only_in_case_refuses_its_reader() -> None:
    result = emit_mysql_sql(
        _compile(
            _JOINED + "table base:\n    from orders\n    let c = customers\n"
            "    inner join c on orders.customer_id == c.id\n    select:\n"
            "        name = c.name\n        NAME = orders.id\n"
            "query reader:\n    from base\n    select:\n        name\n"
        )
    )

    assert [artifact.name for artifact in result.artifacts] == ["base"]
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            "MySQL SQL emission is not implemented for RelationIR: reader. Its SQL "
            "defines relation base as a CTE with outputs name and NAME, whose names "
            "MySQL compares without case; rename one of them",
        )
    ]


def test_physical_source_name_parts_are_quoted_and_escape_backticks() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )
    source = _definition(script_ir, SourceIR, "users")
    connector = replace(source.connector, arguments=("a`pp.we`ird",))
    bad_source = replace(source, connector=connector)
    definitions = tuple(
        bad_source if definition is source else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts[0].sql.endswith("FROM `a``pp`.`we``ird`")
    assert result.diagnostics == ()


def test_reserved_alias_is_backtick_quoted() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )
    relation = _definition(script_ir, RelationIR, "selected")
    projection = replace(relation.projections[0], name="order")
    bad_relation = replace(relation, projections=(projection,))
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts[0].sql.startswith("SELECT\n    `email` AS `order`\n")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda source: replace(
            source,
            connector=replace(source.connector, name="postgres.table"),
        ),
        lambda source: replace(
            source,
            connector=replace(source.connector, arguments=("",)),
        ),
        lambda source: replace(
            source,
            connector=replace(source.connector, arguments=("x" * 65,)),
        ),
        lambda source: replace(
            source,
            connector=replace(source.connector, arguments=("bad\x00name",)),
        ),
        lambda source: replace(
            source,
            connector=replace(source.connector, arguments=("a.b.c",)),
        ),
        lambda source: replace(
            source,
            connector=replace(source.connector, arguments=("app.",)),
        ),
        lambda source: replace(
            source,
            connector=replace(source.connector, arguments=("app." + "x" * 65,)),
        ),
    ],
)
def test_unsupported_or_invalid_connectors_emit_no_partial_artifact(
    mutate: Callable[[SourceIR], SourceIR],
) -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )
    source = _definition(script_ir, SourceIR, "users")
    bad_source = mutate(source)
    definitions = tuple(
        bad_source if definition is source else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-B1000"
    assert "selected" in result.diagnostics[0].message


def test_matches_relation_fails_closed_without_approximation() -> None:
    result = emit_mysql_sql(
        _compile(
            SOURCE + "table matching:\n"
            "    from users\n"
            '    where matches(email, "@")\n'
            "    select:\n"
            "        email\n"
        )
    )

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert "Unsupported MySQL function call: matches" in (result.diagnostics[0].message)


def test_invalid_projection_expression_emits_no_partial_artifact() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        normalized = lower(email)\n"
    )
    relation = _definition(script_ir, RelationIR, "selected")
    projection = relation.projections[0]
    assert isinstance(projection.expression, CallIR)
    bad_projection = replace(
        projection,
        expression=replace(
            projection.expression,
            callee="unknown",
            callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "unknown"),
        ),
    )
    bad_relation = replace(relation, projections=(bad_projection,))
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert "Unsupported MySQL function call: unknown" in (result.diagnostics[0].message)


def test_invalid_literal_emits_no_partial_artifact() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n"
        "    from users\n"
        '    where email == "safe"\n'
        "    select:\n"
        "        email\n"
    )
    relation = _definition(script_ir, RelationIR, "selected")
    assert relation.filter is not None
    expression = relation.filter.expression
    assert isinstance(expression, ComparisonIR)
    assert isinstance(expression.right, LiteralIR)
    bad_filter = replace(
        relation.filter,
        expression=replace(
            expression,
            right=replace(expression.right, value="bad\x00value"),
        ),
    )
    bad_relation = replace(relation, filter=bad_filter)
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert "string literal must not contain NUL" in result.diagnostics[0].message
    assert "\x00" not in result.diagnostics[0].message


def test_invalid_field_identifier_emits_no_partial_artifact() -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )
    relation = _definition(script_ir, RelationIR, "selected")
    projection = relation.projections[0]
    assert isinstance(projection.expression, FieldRefIR)
    bad_expression = replace(projection.expression, name="x" * 65)
    bad_relation = replace(
        relation,
        projections=(replace(projection, expression=bad_expression),),
    )
    definitions = tuple(
        bad_relation if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    assert "column identifier must not exceed 64 characters" in (
        result.diagnostics[0].message
    )


def test_supported_artifacts_and_diagnostics_preserve_definition_order() -> None:
    script_ir = _compile(
        SOURCE + "table first:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "table second:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "table third:\n"
        "    from users\n"
        "    select:\n"
        "        deleted_at\n"
    )
    second = _definition(script_ir, RelationIR, "second")
    projection = second.projections[0]
    bad_expression = CallIR(
        span=projection.expression.span,
        value_type=projection.expression.value_type,
        callee="matches",
        callee_symbol=SymbolId(SymbolNamespace.CALLABLE, "matches"),
        arguments=(
            projection.expression,
            LiteralIR(
                span=projection.expression.span,
                value_type=projection.expression.value_type,
                value="@",
            ),
        ),
    )
    bad_second = replace(
        second,
        projections=(replace(projection, expression=bad_expression),),
    )
    definitions = tuple(
        bad_second if definition is second else definition
        for definition in script_ir.definitions
    )

    result = emit_mysql_sql(ScriptIR(definitions=definitions))

    assert [artifact.name for artifact in result.artifacts] == ["first", "third"]
    assert len(result.diagnostics) == 1
    assert "second" in result.diagnostics[0].message
    assert "Unsupported MySQL function call: matches" in result.diagnostics[0].message


def test_metadata_remains_non_emitting() -> None:
    script_ir = _compile(
        "type Email = Text\n"
        "enum Status:\n"
        "    active\n"
        "constraint valid_email(email: Text) -> Bool:\n"
        "    return email is not None\n"
        "derive normalize_email(email: Text) -> Text:\n"
        "    return trim(email)\n"
        + SOURCE
        + "table selected:\n    from users\n    select:\n        email\n"
    )

    result = emit_mysql_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["selected"]
    assert result.diagnostics == ()


def test_mysql_emitter_does_not_run_frontend_or_ir_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("MySQL emission must consume ScriptIR directly")

    monkeypatch.setattr(parser_api, "parse_source", unexpected_call)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)

    result = emit_mysql_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["selected"]
    assert result.diagnostics == ()


@pytest.mark.parametrize("exception_type", [TypeError, ValueError])
def test_unexpected_renderer_errors_remain_visible(
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[Exception],
) -> None:
    script_ir = _compile(
        SOURCE + "table selected:\n    from users\n    select:\n        email\n"
    )

    def unexpected_error(*args: object, **kwargs: object) -> str:
        del args, kwargs
        raise exception_type("unexpected renderer defect")

    monkeypatch.setattr(mysql_module, "render_mysql_relation", unexpected_error)

    with pytest.raises(exception_type, match="unexpected renderer defect"):
        emit_mysql_sql(script_ir)


def test_mysql_sql_modules_have_no_runtime_or_sqlglot_dependencies() -> None:
    source = inspect.getsource(mysql_module) + inspect.getsource(relation_module)

    for dependency in (
        "antlr",
        "pietto.parser",
        "pietto.semantic",
        "pietto.ir.builder",
        "pietto.ir.lowering",
        "sqlglot",
        "database",
        "connector execution",
        "pietto.cli",
    ):
        assert dependency not in source


def _compile(source: str) -> ScriptIR:
    parse_result = parser_api.parse_source(source, path="mysql-relations.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None
    semantic_result = semantic_api.analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    # IR lowers the analyzed script, in which each `let name = value` is
    # already resolved, as the CLI lowers it.
    assert semantic_result.script is not None
    ir_result = build_ir(semantic_result.script, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _definition[DefinitionT: (SourceIR, RelationIR)](
    script_ir: ScriptIR,
    definition_type: type[DefinitionT],
    name: str,
) -> DefinitionT:
    definition = next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, definition_type) and definition.name == name
    )
    return definition


def test_scalar_any_in_or_preserves_outer_capture_and_binding() -> None:
    source = """shape Row:
    id: Int
source orders: Row = mysql.table("orders")
source customers: Row = mysql.table("customers")
query result:
    from orders
    where orders.id > 0 or any(buyer.id == orders.id for buyer in customers)
    select id = orders.id
"""
    parsed = parser_api.parse_source(source, path="any-mysql.pietto")
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = semantic_api.analyze(parsed.ast)
    assert semantic.script is not None and not semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    result = emit_mysql_sql(lowered.ir)
    assert not result.diagnostics
    (artifact,) = result.artifacts
    assert "EXISTS (SELECT 1 FROM " in artifact.sql
    assert " OR " in artifact.sql
    assert "`orders`.`id`" in artifact.sql


def test_scalar_any_null_predicate_emits_unknown_filter() -> None:
    parsed = parser_api.parse_source("""shape Row:
    id: Int
source rows: Row = mysql.table("rows")
query result:
    from rows
    select found = any(None for candidate in rows)
""")
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = semantic_api.analyze(parsed.ast)
    assert semantic.script is not None and not semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    result = emit_mysql_sql(lowered.ir)
    assert not result.diagnostics
    assert " WHERE NULL)" in result.artifacts[0].sql


def test_scalar_any_derived_iterator_includes_transitive_ctes() -> None:
    parsed = parser_api.parse_source("""shape Row:
    id: Int
source rows: Row = mysql.table("rows")
query result:
    from rows
    select:
        found = any(candidate.id == rows.id for candidate in later)
table later:
    from prior
    select:
        id = prior.id
table prior:
    from rows
    select:
        id = rows.id
""")
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = semantic_api.analyze(parsed.ast)
    assert semantic.script is not None and not semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    result = emit_mysql_sql(lowered.ir)
    assert not result.diagnostics
    sql = {artifact.name: artifact.sql for artifact in result.artifacts}
    assert (
        sql["result"].index("`prior` AS (")
        < sql["result"].index("`later` AS (")
        < sql["result"].index("EXISTS (")
    )
    assert "FROM `later` AS" in sql["result"]
    # `later` defines `prior`, the table it reads, as a CTE too.
    assert sql["later"] == (
        "WITH `prior` AS (\nSELECT\n    `rows`.`id` AS `id`\nFROM `rows` AS `rows`\n)\n"
        "SELECT\n    `prior`.`id` AS `id`\nFROM `prior` AS `prior`"
    )


def _emit_any_reader(table: str) -> SqlResult:
    parsed = parser_api.parse_source(
        f"""shape Row:
    id: Int
source outer_rows: Row = mysql.table("{table}")
source inner_rows: Row = mysql.table("items")
query filtered:
    from inner_rows
    where id > 1
    select id
query q:
    from outer_rows
    select:
        id
        matched = any(candidate.id == outer_rows.id for candidate in filtered)
""",
        path="any-mysql.pietto",
    )
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = semantic_api.analyze(parsed.ast)
    assert semantic.script is not None and not semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    return emit_mysql_sql(lowered.ir)


# A CTE takes the place of a same-named table read without a schema in the
# main SELECT (MySQL compares the names case-insensitively); emitting it would
# read the CTE's rows.
@pytest.mark.parametrize("table", ("filtered", "FILTERED"))
def test_scalar_any_dependency_cte_never_hides_a_table_read_without_a_schema(
    table: str,
) -> None:
    result = _emit_any_reader(table)
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
        (
            "PIE-B1000",
            "MySQL SQL emission is not implemented for RelationIR: q. Its SQL "
            "defines relation filtered as a CTE, which would hide table "
            f"{table} read in the same SQL; rename the relation or read the table "
            "with its schema",
            "any-mysql.pietto",
            9,
            1,
        )
    ]
    assert [artifact.name for artifact in result.artifacts] == ["filtered"]


def test_scalar_any_dependency_cte_keeps_a_table_read_with_its_schema() -> None:
    result = _emit_any_reader("app.filtered")
    assert result.diagnostics == ()
    assert result.artifacts[1].sql == (
        "WITH `filtered` AS (\n"
        "SELECT\n"
        "    `id` AS `id`\n"
        "FROM `items`\n"
        "WHERE `id` > 1\n"
        ")\n"
        "SELECT\n"
        "    `id` AS `id`,\n"
        "    EXISTS (SELECT 1 FROM `filtered` AS `_pietto_value_1` WHERE "
        "`_pietto_value_1`.`id` = `outer_rows`.`id`) AS `matched`\n"
        "FROM `app`.`filtered` AS `outer_rows`"
    )


# A server that compares names case-insensitively refuses a WITH clause whose
# CTE names differ only in letter case as one name defined twice.
def test_scalar_any_dependency_ctes_never_differ_only_in_letter_case() -> None:
    parsed = parser_api.parse_source(
        """shape Row:
    id: Int
source rows: Row = mysql.table("items")
query chosen:
    from rows
    where id == 1
    select id
query CHOSEN:
    from rows
    where id == 2
    select id
query q:
    from rows
    select:
        first_match = any(c.id == rows.id for c in chosen)
        second_match = any(c.id == rows.id for c in CHOSEN)
""",
        path="any-mysql.pietto",
    )
    assert parsed.ast is not None and not parsed.diagnostics
    semantic = semantic_api.analyze(parsed.ast)
    assert semantic.script is not None and not semantic.diagnostics
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None and not lowered.diagnostics
    result = emit_mysql_sql(lowered.ir)
    assert [
        (item.code, item.message, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            "MySQL SQL emission is not implemented for RelationIR: q. Its SQL "
            "defines relations chosen and CHOSEN as CTEs, whose names MySQL may "
            "compare without case; rename one of them",
            12,
            1,
        )
    ]
    assert [artifact.name for artifact in result.artifacts] == ["chosen", "CHOSEN"]
