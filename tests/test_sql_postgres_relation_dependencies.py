from __future__ import annotations

import sys
from dataclasses import replace

import pytest

from pietto.errors import Severity
from pietto.ir import (
    RelationIR,
    ScriptIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlArtifactKind, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.relations import render_relation_sql

SOURCE = (
    "shape User:\n"
    "    id: UUID\n"
    "    email: Text | None\n"
    "    active: Bool\n"
    'source users: User = postgres.table("users")\n'
)


def test_source_table_query_chain_emits_ordered_relation_artifacts() -> None:
    result = emit_postgres_sql(_chain_ir())

    assert [(artifact.name, artifact.kind) for artifact in result.artifacts] == [
        ("active_users", SqlArtifactKind.RELATION),
        ("active_user_emails", SqlArtifactKind.RELATION),
    ]
    assert result.artifacts[0].sql == (
        "SELECT\n"
        '    "id" AS "id",\n'
        '    "email" AS "email"\n'
        'FROM "users"\n'
        'WHERE "active" = TRUE'
    )
    assert result.artifacts[1].sql == (
        'WITH "active_users" AS (\n'
        "SELECT\n"
        '    "id" AS "id",\n'
        '    "email" AS "email"\n'
        'FROM "users"\n'
        'WHERE "active" = TRUE\n'
        ")\n"
        "SELECT\n"
        '    lower("email") AS "normalized_email"\n'
        'FROM "active_users"\n'
        'WHERE "email" IS NOT NULL'
    )
    assert result.diagnostics == ()


def test_a_relation_of_the_file_is_a_cte_of_its_readers_sql() -> None:
    """The CTE is the relation's own artifact SQL, so the reader runs without
    that relation in the database."""

    upstream, downstream = emit_postgres_sql(_chain_ir()).artifacts

    assert downstream.sql.startswith(f'WITH "active_users" AS (\n{upstream.sql}\n)\n')
    assert downstream.sql.count("WITH") == 1


def test_each_relation_a_statement_reads_is_one_cte_after_the_ones_it_reads() -> None:
    """FROM, JOIN and ANY reads, also through other relations of the file:
    each relation is defined once, after the relations it reads, in the order
    the statement reads them."""

    result = emit_postgres_sql(
        _compile_ir(
            SOURCE + "table base:\n    from users\n    select:\n        id\n"
            "        email\n"
            "table named:\n    from base\n    where email is not None\n"
            "    select:\n        id\n"
            "query joined:\n    from base\n    let n = named\n"
            "    inner join n on n.id == base.id\n    select:\n"
            "        id = base.id\n"
            "query tested:\n    from users\n"
            "    where any(n.id == users.id for n in named)\n"
            "    select:\n        id\n"
            "query chained:\n    from joined\n"
            "    where any(t.id == joined.id for t in tested)\n"
            "    select:\n        id\n"
        )
    )

    assert result.diagnostics == ()
    sql = {artifact.name: artifact.sql for artifact in result.artifacts}
    base = f'WITH "base" AS (\n{sql["base"]}\n)'
    assert sql["base"].startswith("SELECT\n")
    assert sql["named"].startswith(f"{base}\nSELECT\n")
    named = sql["named"].removeprefix(f"{base}\n")
    assert sql["joined"].startswith(f'{base},\n"named" AS (\n{named}\n)\nSELECT\n')
    assert 'INNER JOIN "named" AS "n"' in sql["joined"]
    assert sql["tested"].startswith('WITH "base" AS (\n')
    assert 'EXISTS (SELECT 1 FROM "named" AS' in sql["tested"]
    ctes = [
        line.split('"')[1]
        for line in sql["chained"].splitlines()
        if line.endswith(" AS (")
    ]
    assert ctes == ["base", "named", "joined", "tested"]


def test_direct_source_backed_relation_behavior_is_unchanged() -> None:
    script_ir = _compile_ir(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )

    result = emit_postgres_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == ["user_emails"]
    assert result.artifacts[0].sql.endswith('FROM "users"')


def test_unresolved_relation_source_target_reports_pie_b1000() -> None:
    script_ir = _chain_ir()
    downstream = _relation(script_ir, "active_user_emails")
    unresolved = replace(
        downstream,
        source=replace(
            downstream.source,
            target=SymbolId(SymbolNamespace.RELATION, "missing_relation"),
        ),
    )
    definitions = tuple(
        unresolved if definition is downstream else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert [artifact.name for artifact in result.artifacts] == ["active_users"]
    diagnostic = next(
        item for item in result.diagnostics if "active_user_emails" in item.message
    )
    assert diagnostic.code == "PIE-B1000"
    assert diagnostic.severity is Severity.ERROR
    assert "does not resolve to SourceIR or RelationIR" in diagnostic.message


def test_bad_source_connector_still_reports_pie_b1000() -> None:
    script_ir = _compile_ir(
        SOURCE + "table user_emails:\n    from users\n    select:\n        email\n"
    )
    source = _source(script_ir, "users")
    invalid_source = replace(
        source,
        connector=replace(source.connector, name="unsupported.table"),
    )
    definitions = tuple(
        invalid_source if definition is source else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    diagnostic = next(
        item for item in result.diagnostics if "user_emails" in item.message
    )
    assert diagnostic.code == "PIE-B1000"
    assert "postgres.table(Text)" in diagnostic.message


_HIDING = (
    "shape Row:\n    id: Int\n"
    'source raw: Row = postgres.table("raw_rows")\n'
    'source shadow: Row = postgres.table("{table}")\n'
    "table kept:\n    from raw\n    select:\n        id\n"
)
_LATER = "table later:\n    from shadow\n    select:\n        id\n"
_READS_SHADOW = (
    "query q:\n    from kept\n    where any(s.id == kept.id for s in shadow)\n"
    "    select:\n        id\n"
)


# A CTE takes the place of a same-named table without a schema in the CTEs
# after it and in the main SELECT, so emitting it would read the CTE's rows.
@pytest.mark.parametrize(
    ("reader", "artifacts", "line"),
    (
        (_READS_SHADOW, ["kept"], 9),
        (
            _LATER + "query q:\n    from kept\n"
            "    where any(l.id == kept.id for l in later)\n    select:\n        id\n",
            ["kept", "later"],
            13,
        ),
    ),
    ids=("main_select", "later_cte_body"),
)
def test_a_cte_that_would_hide_a_table_the_statement_reads_is_refused(
    reader: str, artifacts: list[str], line: int
) -> None:
    result = emit_postgres_sql(_compile_ir(_HIDING.format(table="kept") + reader))

    assert [artifact.name for artifact in result.artifacts] == artifacts
    assert [
        (item.code, item.severity, item.message, item.location.line)
        for item in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            Severity.ERROR,
            "PostgreSQL SQL emission is not implemented for RelationIR: q. Its SQL "
            "defines relation kept as a CTE, which would hide table kept read in "
            "the same SQL; rename the relation or read the table with its schema",
            line,
        )
    ]


# A CTE is not visible in its own body or in the CTEs before it.
@pytest.mark.parametrize(
    ("source", "sql"),
    (
        (
            "shape Row:\n    id: Int\n"
            'source raw: Row = postgres.table("kept")\n'
            "table kept:\n    from raw\n    select:\n        id\n"
            "query q:\n    from kept\n    select:\n        id\n",
            'WITH "kept" AS (\nSELECT\n    "id" AS "id"\nFROM "kept"\n)\n'
            'SELECT\n    "id" AS "id"\nFROM "kept"',
        ),
        (
            _HIDING.format(table="kept") + _LATER + "query q:\n    from later\n"
            "    where any(k.id == later.id for k in kept)\n    select:\n        id\n",
            'WITH "later" AS (\nSELECT\n    "id" AS "id"\nFROM "kept"\n),\n'
            '"kept" AS (\nSELECT\n    "id" AS "id"\nFROM "raw_rows"\n)\n'
            'SELECT\n    "id" AS "id"\nFROM "later" AS "later"\n'
            'WHERE EXISTS (SELECT 1 FROM "kept" AS "_pietto_value_1" '
            'WHERE "_pietto_value_1"."id" = "later"."id")',
        ),
    ),
    ids=("own_body", "earlier_cte_body"),
)
def test_a_cte_hides_no_table_read_where_it_is_not_visible(
    source: str, sql: str
) -> None:
    result = emit_postgres_sql(_compile_ir(source))

    assert result.diagnostics == ()
    assert result.artifacts[-1].sql == sql


@pytest.mark.parametrize(
    ("table", "quoted"),
    (
        ("public.kept", '"public"."kept"'),
        ("Kept", '"Kept"'),
        ("kept_rows", '"kept_rows"'),
    ),
)
def test_a_cte_hides_no_table_of_another_name_or_with_a_schema(
    table: str, quoted: str
) -> None:
    result = emit_postgres_sql(_compile_ir(_HIDING.format(table=table) + _READS_SHADOW))

    assert result.diagnostics == ()
    assert result.artifacts[1].sql == (
        'WITH "kept" AS (\nSELECT\n    "id" AS "id"\nFROM "raw_rows"\n)\n'
        'SELECT\n    "id" AS "id"\nFROM "kept" AS "kept"\n'
        f'WHERE EXISTS (SELECT 1 FROM {quoted} AS "_pietto_value_1" '
        'WHERE "_pietto_value_1"."id" = "kept"."id")'
    )


def test_a_relation_whose_sql_is_refused_refuses_its_readers() -> None:
    result = emit_postgres_sql(
        _compile_ir(
            SOURCE + "table unset:\n    from users\n    select:\n        id\n"
            "        nothing = None\n"
            "query reader:\n    from unset\n    select:\n        id\n"
            "table direct:\n    from users\n    select:\n        id\n"
        )
    )

    assert [artifact.name for artifact in result.artifacts] == ["direct"]
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            f"PostgreSQL SQL emission is not implemented for RelationIR: {name}. "
            "PostgreSQL types a NULL output that another relation reads as text, "
            "which Pietto leaves untyped",
        )
        for name in ("unset", "reader")
    ]


# In a CTE each unaliased output (PIE-S2304 warns of it) takes a private
# alias, so a read of another output by its name binds to that output alone;
# the relation's own SELECT keeps the item unaliased. Before: PostgreSQL named
# `lower(cat)` and `CASE ... ELSE lower(cat) END` `lower`, and `trim(cat)`
# `btrim`, and Pietto refused, or missed, a read of an output of that name.
def test_an_unnamed_cte_output_takes_a_private_alias() -> None:
    result = emit_postgres_sql(
        _compile_ir(
            "shape Row:\n    id: Int\n    cat: Text\n"
            'source items: Row = postgres.table("items")\n'
            "table base:\n    from items\n    select:\n        id\n"
            "        lower = id\n        lower(cat)\n"
            '        "" if id > 1 else lower(cat)\n        btrim = id\n'
            "        trim(cat)\n"
            "query reader:\n    from base\n    select:\n        lower\n"
            "        btrim\n"
            "query joined:\n    from items\n    let b = base\n"
            "    inner join b on b.id == items.id\n    select:\n"
            "        x = b.lower\n"
            "query filtered:\n    from items\n"
            "    where any(b.lower == items.id for b in base)\n    select:\n"
            "        id\n"
        )
    )

    items = (
        '"id" AS "id"',
        '"id" AS "lower"',
        'lower("cat")',
        'CASE WHEN ("id" > 1) THEN \'\' ELSE lower("cat") END',
        '"id" AS "btrim"',
        'trim("cat")',
    )
    aliased = {2: "__pietto_column_1", 3: "__pietto_column_2", 5: "__pietto_column_3"}
    base = "SELECT\n    " + ",\n    ".join(items) + '\nFROM "items"'
    cte = (
        'WITH "base" AS (\nSELECT\n    '
        + ",\n    ".join(
            f'{item} AS "{aliased[index]}"' if index in aliased else item
            for index, item in enumerate(items)
        )
        + '\nFROM "items"\n)\n'
    )
    assert result.diagnostics == ()
    assert [artifact.sql for artifact in result.artifacts] == [
        base,
        f'{cte}SELECT\n    "lower" AS "lower",\n    "btrim" AS "btrim"\nFROM "base"',
        f'{cte}SELECT\n    "b"."lower" AS "x"\nFROM "items" AS "items"\n'
        'INNER JOIN "base" AS "b" ON "b"."id" = "items"."id"',
        f'{cte}SELECT\n    "id" AS "id"\nFROM "items" AS "items"\nWHERE EXISTS '
        '(SELECT 1 FROM "base" AS "_pietto_value_1" '
        'WHERE "_pietto_value_1"."lower" = "items"."id")',
    ]


# Over a source without a shape a check reads any name of a relation, yet its
# CTE has only the outputs the relation names, each unaliased one under a
# private alias that takes no name the statement reads; a read of another
# name, such as the one a database gives an unaliased output, is refused at
# its reader, and MySQL compares the names without case. ORDER BY reads the
# reader's own output only by a whole key of its exact name, so `Z` beside an
# output `z`, or `z + 1`, reads the CTE. The hint to name an unaliased output
# is conditional, and a read that differs from an output only in case gets
# none. Before: emission read `lower`, which names no column of the CTE, and
# the database rejected the statement; a key such as `Z` or `z + 1` beside an
# output `z` passed the check by the output's name and read the CTE.
@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
def test_a_read_of_a_name_a_cte_does_not_give_is_refused(dialect: str) -> None:
    emitter = emit_postgres_sql if dialect == "postgres" else emit_mysql_sql
    q, label = ('"', "PostgreSQL") if dialect == "postgres" else ("`", "MySQL")
    result = emitter(
        _compile_ir(
            f'source items = {dialect}.table("items")\n'
            "table base:\n    from items\n    select:\n        id\n"
            "        lower(email)\n        __pietto_column_1\n"
            "query reader:\n    from base\n    select:\n        __pietto_column_1\n"
            "        y = id\n    order by y\n"
            "query implicit:\n    from base\n    select:\n        id\n"
            "        x = lower\n"
            "query unknown:\n    from base\n    where nosuch > 1\n    select:\n"
            "        id\n"
            "query cased:\n    from base\n    select:\n        x = ID\n"
            "table named:\n    from items\n    select:\n        id\n"
            "query stray:\n    from named\n    select:\n        x = nosuch\n"
            "query sorted:\n    from named\n    select:\n        z = id\n"
            "    order by Z\n"
            "query shifted:\n    from named\n    select:\n        z = id\n"
            "    order by z + 1\n"
        )
    )

    lower = "lower" if dialect == "postgres" else "LOWER"
    column = f"{q}__pietto_column_1{q} AS {q}__pietto_column_1{q}"
    cte = (
        f"WITH {q}base{q} AS (\nSELECT\n    {q}id{q} AS {q}id{q},\n"
        f"    {lower}({q}email{q}) AS {q}__pietto_column_2{q},\n    {column}\n"
        f"FROM {q}items{q}\n)\n"
    )
    sql = [
        f"SELECT\n    {q}id{q} AS {q}id{q},\n    {lower}({q}email{q}),\n"
        f"    {column}\nFROM {q}items{q}",
        f"{cte}SELECT\n    {column},\n    {q}id{q} AS {q}y{q}\nFROM {q}base{q}\n"
        f"ORDER BY\n    {q}y{q} ASC",
    ]
    hint = (
        "; if it means the unaliased output at line 6, column 9, which has no "
        "name a reader can use, write `{} = ...` there to name it"
    )
    refused = [
        ("implicit", 14, "lower", "base", hint.format("lower")),
        ("unknown", 19, "nosuch", "base", hint.format("nosuch")),
    ]
    if dialect == "postgres":
        refused.append(("cased", 24, "ID", "base", ""))
    else:
        sql.append(f"{cte}SELECT\n    {q}ID{q} AS {q}x{q}\nFROM {q}base{q}")
    sql.append(f"SELECT\n    {q}id{q} AS {q}id{q}\nFROM {q}items{q}")
    refused += [
        ("stray", 32, "nosuch", "named", ""),
        ("sorted", 36, "Z", "named", ""),
        ("shifted", 41, "z", "named", ""),
    ]
    assert [artifact.sql for artifact in result.artifacts] == sql
    assert [
        (item.code, item.location.line, item.location.column, item.message)
        for item in result.diagnostics
    ] == [
        (
            "PIE-B1000",
            line,
            1,
            f"{label} SQL emission is not implemented for RelationIR: {name}. "
            f"Its SQL reads {read} from relation {cte_name}, which names no output "
            f"{read}{tail}",
        )
        for name, line, read, cte_name, tail in refused
    ]


# Generated: whatever name PostgreSQL or MySQL gives an unaliased item (MySQL:
# a Text value without its leading spaces; PostgreSQL: a CASE by its ELSE,
# `trim` as `btrim`, a cast by its value), a CTE holds it under a private
# alias, so a read of an output of that name, or of a name that differs from
# it only in case, binds to that output alone, directly or inside `any(...)`.
_UNALIASED_ITEMS = (
    ('" price"', ("price", "PRICE")),
    ('"price  "', ("price",)),
    ('"Price"', ("price",)),
    ("0 if id > 1 else price", ("price", "case")),
    ("0 if id > 1 else abs(cost)", ("abs", "ABS")),
    ("lower(name)", ("lower", "LOWER")),
    ("trim(name)", ("btrim", "trim")),
    ("Float(price)", ("price", "float8")),
    ("price + 1", ("price",)),
)


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize(
    ("item", "name"),
    tuple((item, name) for item, names in _UNALIASED_ITEMS for name in names),
)
def test_no_cte_read_binds_by_the_name_of_an_unaliased_item(
    item: str, name: str, dialect: str
) -> None:
    emitter = emit_postgres_sql if dialect == "postgres" else emit_mysql_sql
    quote = '"' if dialect == "postgres" else "`"
    result = emitter(
        _compile_ir(
            "shape Row:\n    id: Int\n    price: Int\n    cost: Int\n    name: Text\n"
            f'source items: Row = {dialect}.table("items")\n'
            "table base:\n    from items\n    select:\n        id\n"
            f"        {name} = cost\n        {item}\n"
            f"query reader:\n    from base\n    select:\n        x = {name}\n"
            "query filtered:\n    from items\n"
            f"    where any(b.{name} == items.id for b in base)\n"
            "    select:\n        id\n"
        )
    )

    assert result.diagnostics == ()
    base, *readers = (artifact.sql for artifact in result.artifacts)
    # The relation's own SELECT keeps the item unaliased, its result's name.
    assert not base.split("\nFROM ", 1)[0].endswith(quote)
    for sql in readers:
        cte = sql.split(" AS (\nSELECT\n    ", 1)[1].split("\nFROM ", 1)[0]
        aliases = [
            selected.rsplit(f" AS {quote}", 1)[1].rstrip(quote)
            for selected in cte.split(",\n    ")
        ]
        assert len(aliases) == 3, sql
        assert len({alias.casefold() for alias in aliases}) == 3, sql
        assert aliases[1] == name, sql


_QUALIFY_ANY = (
    "shape Row:\n    id: Int\n"
    "shape Ord:\n    item_id: Int\n    qty: Int\n"
    'source items: Row = postgres.table("items")\n'
    'source orders: Ord = postgres.table("orders")\n'
    "table big_orders:\n    from orders\n    where qty > 10\n    select:\n"
    "        item_id\n"
    "table q_any:\n    from items\n"
    "    let has = any(b.item_id == items.id for b in big_orders)\n"
    "    select:\n        id\n        rn = row_number() window(order by id)\n"
)
_QUALIFY_ANY_EXISTS = (
    'EXISTS (SELECT 1 FROM "big_orders" AS "_pietto_value_1" '
    'WHERE "_pietto_value_1"."item_id" = "__pietto_qualify"."__pietto_qualify_0")'
)


@pytest.mark.parametrize(
    ("clauses", "outer"),
    (
        (
            "    qualify:\n        rn <= 3 and has\n",
            f'WHERE\n    ("rn" <= 3) AND {_QUALIFY_ANY_EXISTS}',
        ),
        (
            "    qualify:\n        rn <= 3\n    order by has desc, id\n",
            f'WHERE\n    "rn" <= 3\nORDER BY\n    {_QUALIFY_ANY_EXISTS} DESC,\n'
            '    "__pietto_qualify_0" ASC',
        ),
    ),
    ids=("qualify", "order_by_after_qualify"),
)
def test_a_qualify_statement_defines_the_relations_its_outer_stage_reads(
    clauses: str, outer: str
) -> None:
    """An `any` read that only QUALIFY or the ORDER BY after it keeps is
    defined as a CTE at the top of the statement, as any other read."""

    result = emit_postgres_sql(_compile_ir(_QUALIFY_ANY + clauses))

    assert result.diagnostics == ()
    assert result.artifacts[-1].sql == (
        'WITH "big_orders" AS (\nSELECT\n    "item_id" AS "item_id"\n'
        'FROM "orders"\nWHERE "qty" > 10\n)\n'
        'SELECT\n    "id",\n    "rn"\nFROM (\nSELECT\n    "id" AS "id",\n'
        '    ROW_NUMBER() OVER (ORDER BY "id" ASC) AS "rn",\n'
        '    "items"."id" AS "__pietto_qualify_0"\nFROM "items" AS "items"\n'
        f') AS "__pietto_qualify"\n{outer}'
    )


def test_a_qualify_port_read_inside_exists_names_its_derived_table() -> None:
    """Inside EXISTS a bare port would first bind to a same-named column of
    the `any` target, so there the outer read names the derived table."""

    result = emit_postgres_sql(
        _compile_ir(
            "shape Row:\n    id: Int\n"
            "shape Ord:\n    __pietto_qualify_0: Int\n"
            'source items: Row = postgres.table("items")\n'
            'source orders: Ord = postgres.table("orders")\n'
            "query q_any:\n    from items\n"
            "    let has = any(o.__pietto_qualify_0 == items.id for o in orders)\n"
            "    select:\n        id\n        rn = row_number() window(order by id)\n"
            "    qualify:\n        rn <= 3 and has\n"
        )
    )

    assert result.diagnostics == ()
    assert [artifact.sql for artifact in result.artifacts] == [
        'SELECT\n    "id",\n    "rn"\nFROM (\nSELECT\n    "id" AS "id",\n'
        '    ROW_NUMBER() OVER (ORDER BY "id" ASC) AS "rn",\n'
        '    "items"."id" AS "__pietto_qualify_0"\nFROM "items" AS "items"\n'
        ') AS "__pietto_qualify"\nWHERE\n    ("rn" <= 3) AND EXISTS (SELECT 1 '
        'FROM "orders" AS "_pietto_value_1" WHERE '
        '"_pietto_value_1"."__pietto_qualify_0" = '
        '"__pietto_qualify"."__pietto_qualify_0")'
    ]


def test_a_qualify_relation_read_as_a_cte_defines_each_relation_once() -> None:
    """A CTE's body is the relation's own statement without its WITH, also
    for QUALIFY: its derived table defines no CTE of its own."""

    result = emit_postgres_sql(
        _compile_ir(
            "shape Row:\n    id: Int\n    cat: Text\n"
            'source items: Row = postgres.table("items")\n'
            "table base:\n    from items\n    select:\n        id\n        cat\n"
            "table q1:\n    from base\n    select:\n        id\n        cat\n"
            "        rn = row_number() window(partition by cat order by id)\n"
            "    qualify:\n        rn <= 2\n"
            "table q2:\n    from q1\n    select:\n        id\n"
            "        rk = row_number() window(order by id)\n"
            "    qualify:\n        rk <= 5\n"
            "query reader:\n    from q2\n    select:\n        id\n"
        )
    )

    assert result.diagnostics == ()
    assert result.artifacts[-1].sql == (
        'WITH "base" AS (\nSELECT\n    "id" AS "id",\n    "cat" AS "cat"\n'
        'FROM "items"\n),\n'
        '"q1" AS (\nSELECT\n    "id",\n    "cat",\n    "rn"\nFROM (\nSELECT\n'
        '    "id" AS "id",\n    "cat" AS "cat",\n'
        '    ROW_NUMBER() OVER (PARTITION BY "cat" ORDER BY "id" ASC) AS "rn"\n'
        'FROM "base"\n) AS "__pietto_qualify"\nWHERE\n    "rn" <= 2\n),\n'
        '"q2" AS (\nSELECT\n    "id",\n    "rk"\nFROM (\nSELECT\n'
        '    "id" AS "id",\n    ROW_NUMBER() OVER (ORDER BY "id" ASC) AS "rk"\n'
        'FROM "q1"\n) AS "__pietto_qualify"\nWHERE\n    "rk" <= 5\n)\n'
        'SELECT\n    "id" AS "id"\nFROM "q2"'
    )


def test_a_relation_read_only_by_a_qualify_any_refuses_its_reader() -> None:
    range_offset = (
        "PostgreSQL RANGE offsets are not supported in single-file emit-sql; "
        "use ROWS, RANGE without an offset, or emit-sql --project with a "
        "nonnegative Int literal offset and one non-null Int ORDER key stored "
        "in at most 32 bits"
    )
    result = emit_postgres_sql(
        _compile_ir(
            "shape Row:\n    id: Int\n    price: Int\n"
            'source items: Row = postgres.table("items")\n'
            "table bad:\n    from items\n    select:\n        id\n"
            "        s = sum(price) window(order by id range between 2 preceding"
            " and current row)\n"
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
            "PostgreSQL SQL emission is not implemented for RelationIR: "
            f"{name}. {range_offset}",
            line,
        )
        for name, line in (("bad", 5), ("reader", 10))
    ]


def test_outputs_that_differ_only_in_case_are_two_postgresql_columns() -> None:
    """PostgreSQL compares quoted names with case (MySQL refuses these)."""

    result = emit_postgres_sql(
        _compile_ir(
            "shape Row:\n    id: Int\n    price: Int\n"
            'source items: Row = postgres.table("items")\n'
            "table pair:\n    from items\n    select:\n        a = id\n"
            "        A = price\n"
            "query reader:\n    from pair\n    select:\n        a\n"
            "query q_case:\n    from items\n    select:\n        a = id\n"
            "        A = price\n"
            "    qualify:\n        row_number() window(order by id) <= 2\n"
        )
    )

    assert result.diagnostics == ()
    pair = 'SELECT\n    "id" AS "a",\n    "price" AS "A"\nFROM "items"'
    assert [artifact.sql for artifact in result.artifacts] == [
        pair,
        f'WITH "pair" AS (\n{pair}\n)\nSELECT\n    "a" AS "a"\nFROM "pair"',
        'SELECT\n    "a",\n    "A"\nFROM (\nSELECT\n    "id" AS "a",\n'
        '    "price" AS "A",\n'
        '    ROW_NUMBER() OVER (ORDER BY "id" ASC) AS "__pietto_qualify_0"\n'
        'FROM "items"\n) AS "__pietto_qualify"\nWHERE\n'
        '    "__pietto_qualify_0" <= 2',
    ]


def test_a_chain_of_reads_deeper_than_the_recursion_limit_defines_each_cte() -> None:
    """Finding the CTE order takes no stack depth per relation read."""

    depth = sys.getrecursionlimit() + 10
    script_ir = _compile_ir(
        "shape T:\n    a: Int\n"
        'source t0: T = postgres.table("t0")\n'
        + "".join(
            f"table t{index}:\n    from t{index - 1}\n    select:\n        a\n"
            for index in range(1, depth + 1)
        )
    )
    definitions = {
        definition.symbol: definition
        for definition in script_ir.definitions
        if isinstance(definition, (RelationIR, SourceIR))
    }

    assert (
        render_relation_sql(
            _relation(script_ir, f"t{depth}"),
            sources={
                symbol: item
                for symbol, item in definitions.items()
                if isinstance(item, SourceIR)
            },
            relations={
                symbol: item
                for symbol, item in definitions.items()
                if isinstance(item, RelationIR)
            },
        )
        == "WITH "
        + ",\n".join(
            f'"t{index}" AS (\nSELECT\n    "a" AS "a"\nFROM "t{index - 1}"\n)'
            for index in range(1, depth)
        )
        + f'\nSELECT\n    "a" AS "a"\nFROM "t{depth - 1}"'
    )


def _chain_ir() -> ScriptIR:
    return _compile_ir(
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    where active == True\n"
        "    select:\n"
        "        id\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    where email is not None\n"
        "    select:\n"
        "        normalized_email = lower(email)\n"
    )


def _compile_ir(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="relation-dependencies.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    # As the CLI does: JOIN lowering reads the normalized script.
    assert semantic_result.script is not None
    ir_result = build_ir(semantic_result.script, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation(script_ir: ScriptIR, name: str) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _source(script_ir: ScriptIR, name: str) -> SourceIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, SourceIR) and definition.name == name
    )
