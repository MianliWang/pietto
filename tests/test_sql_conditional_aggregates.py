"""SQL of the conditional count and sum of a group (Phase73 S02):
`sum(1 for o in group if TEST)` and `sum(o.f for o in group if TEST)`."""

from __future__ import annotations

import json

import pytest

import _pietto_sql_emission as probe
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SOURCE = """shape Order:
    id: Int
    customer_id: Int | None
    amount: Int
    paid: Bool | None
    status: Text | None
source orders: Order = {target}.table("shop.orders")
query paid_per_customer:
    from orders
    group by customer_id
    select:
        customer_id
        paid_orders = {call}
    having:
        paid_orders > 1
    order by paid_orders desc
query paid_overall:
    from orders
    select:
        paid_orders = {call}
"""
COUNT = "sum(1 for o in group if o.paid)"
SUM = 'sum(o.amount for o in group if o.status == "refunded" or o.amount > 10)'


def _emit(target: str, call: str) -> SqlResult:
    parsed = parse_source(SOURCE.format(target=target, call=call))
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == () and semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None, lowered.diagnostics
    emit = emit_postgres_sql if target == "postgres" else emit_mysql_sql
    return emit(lowered.ir)


@pytest.mark.parametrize(
    ("call", "value"),
    [
        (COUNT, 'COUNT(CASE WHEN "paid" THEN 1 END)'),
        (
            SUM,
            "COALESCE(CAST(SUM(CASE WHEN (\"status\" = 'refunded') OR "
            '("amount" > 10) THEN CAST("amount" AS pg_catalog.int8) END) AS '
            "pg_catalog.int8), 0)",
        ),
    ],
)
def test_postgres_counts_and_adds_the_rows_whose_test_is_true(
    call: str, value: str
) -> None:
    """The count counts the rows whose test is True; the sum adds their
    non-None values exactly, narrowed to bigint by the checked CAST, 0 for no
    such row. A None test takes no CASE branch. HAVING and ORDER BY restate
    the aggregate, as for every grouped output."""
    result = _emit("postgres", call)

    assert result.diagnostics == ()
    assert [artifact.sql for artifact in result.artifacts] == [
        'SELECT\n    "customer_id" AS "customer_id",\n'
        f'    {value} AS "paid_orders"\n'
        'FROM "shop"."orders"\nGROUP BY\n    "customer_id"\n'
        f"HAVING\n    {value} > 1\nORDER BY\n    {value} DESC",
        f'SELECT\n    {value} AS "paid_orders"\nFROM "shop"."orders"',
    ]


def test_mysql_counts_with_the_same_case_form() -> None:
    """COUNT is a BIGINT on MySQL too; its two-database differential is the
    S02 package's (Phase73 Annex B). HAVING and ORDER BY restate it."""
    result = _emit("mysql", COUNT)
    value = "COUNT(CASE WHEN `paid` THEN 1 END)"

    assert result.diagnostics == ()
    assert [artifact.sql for artifact in result.artifacts] == [
        "SELECT\n    `customer_id` AS `customer_id`,\n"
        f"    {value} AS `paid_orders`\n"
        "FROM `shop`.`orders`\nGROUP BY\n    `customer_id`\n"
        f"HAVING\n    {value} > 1\nORDER BY\n    {value} DESC",
        f"SELECT\n    {value} AS `paid_orders`\nFROM `shop`.`orders`",
    ]


def test_mysql_refuses_the_conditional_sum() -> None:
    """MySQL SUM of an Int is DECIMAL, not a checked bigint (a later MySQL catch-up)."""
    result = _emit("mysql", SUM)

    assert result.artifacts == ()
    assert [(item.code, item.message) for item in result.diagnostics] == [
        (
            "PIE-B1000",
            f"MySQL SQL emission is not implemented for RelationIR: {name}. "
            "MySQL conditional sum of an Int argument is not supported",
        )
        for name in ("paid_per_customer", "paid_overall")
    ]


GROUP_TEST = """shape Order:
    id: Int
    customer_id: Int | None
    paid: Bool | None
    status: Text | None
source orders: Order = {target}.table("shop.orders")
query tested:
    from orders
    group by customer_id
    select:
        customer_id
        all_paid = all(o.paid for o in group)
        any_open = any(not o.paid or o.status == "open" for o in group)
    having all_paid or any_open
    order by any_open desc
query tested_overall:
    from orders
    select:
        all_paid = all(o.paid for o in group)
        any_open = any(o.status is None for o in group)
"""


def _emit_group_test(target: str) -> SqlResult:
    parsed = parse_source(GROUP_TEST.format(target=target))
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == () and semantic.script is not None
    lowered = build_ir(semantic.script, semantic.model)
    assert lowered.ir is not None, lowered.diagnostics
    emit = emit_postgres_sql if target == "postgres" else emit_mysql_sql
    return emit(lowered.ir)


def test_postgres_tests_a_group_with_one_count() -> None:
    """`any` counts the rows whose test is True; `all` counts the rows whose
    test is not True, a None test included, which takes no `WHEN` branch.
    COUNT is never NULL, so no row gives False and True, as in Python."""
    result = _emit_group_test("postgres")

    every = '(COUNT(CASE WHEN "paid" THEN NULL ELSE 1 END) = 0)'
    some = '(COUNT(CASE WHEN (NOT "paid") OR ("status" = \'open\') THEN 1 END) > 0)'
    assert result.diagnostics == ()
    assert [artifact.sql for artifact in result.artifacts] == [
        f'SELECT\n    "customer_id" AS "customer_id",\n    {every} AS "all_paid",\n'
        f'    {some} AS "any_open"\nFROM "shop"."orders"\nGROUP BY\n    '
        f'"customer_id"\nHAVING\n    {every} OR {some}\nORDER BY\n    {some} DESC',
        f'SELECT\n    {every} AS "all_paid",\n'
        '    (COUNT(CASE WHEN "status" IS NULL THEN 1 END) > 0) AS "any_open"\n'
        'FROM "shop"."orders"',
    ]


def test_mysql_tests_a_group_with_the_postgres_form() -> None:
    """MySQL writes the PostgreSQL form (`ba` differential): `COUNT(...) > 0`
    is an integer 0/1 there, the computed-Bool wire type."""
    result = _emit_group_test("mysql")

    every = "(COUNT(CASE WHEN `paid` THEN NULL ELSE 1 END) = 0)"
    some = "(COUNT(CASE WHEN (NOT `paid`) OR (`status` = 'open') THEN 1 END) > 0)"
    assert result.diagnostics == ()
    assert [artifact.sql for artifact in result.artifacts] == [
        f"SELECT\n    `customer_id` AS `customer_id`,\n    {every} AS `all_paid`,\n"
        f"    {some} AS `any_open`\nFROM `shop`.`orders`\nGROUP BY\n    "
        f"`customer_id`\nHAVING\n    {every} OR {some}\nORDER BY\n    {some} DESC",
        f"SELECT\n    {every} AS `all_paid`,\n"
        "    (COUNT(CASE WHEN `status` IS NULL THEN 1 END) > 0) AS `any_open`\n"
        "FROM `shop`.`orders`",
    ]


# A schema_version = 2 project over the fixed aggregation source: `key`,
# `value`, `flag`, `label`, `ratio` and `rid` are its fields.
PROJECT_GROUPED = """query result:
    from agg
    group by key
    select:
        key
        paid = sum(1 for o in group if o.flag)
        big = sum(o.value for o in group if o.label == "a" or o.ratio > 0.5)
    having paid > 0
    order by big desc
"""
PROJECT_WHOLE = """query result:
    from agg
    select:
        paid = sum(1 for o in group if o.flag is None)
        big = sum(o.rid for o in group if not o.flag)
"""
_COUNT_SQL = 'COUNT(CASE WHEN "s0"."flag value" THEN 1 END)'
_SUM_SQL = (
    'COALESCE(CAST(SUM(CASE WHEN (("s0"."text `""é" = CAST(E\'\\141\' AS '
    'pg_catalog.text) COLLATE "C") OR ("s0"."ratio value" > CAST(\'0.5\' AS '
    'pg_catalog.float8))) THEN CAST("s0"."value é" AS pg_catalog.int8) END) AS '
    "pg_catalog.int8), 0)"
)


def _project(tmp_path, target: str, body: str) -> dict:
    """The published emission document of ``body``, read by the independent
    public decoder."""
    item = probe.aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    header = probe.AGGREGATE_HEADER.format(target=target)
    _, outcome = probe.build_case(
        tmp_path, header + body, item["contract"], item["policy"]
    )
    return probe.decode_public(serialize_project_sql_emission(outcome))


@pytest.mark.parametrize(
    ("body", "sql"),
    (
        (
            PROJECT_GROUPED,
            f'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."group key" AS "c0", '
            f'{_COUNT_SQL} AS "c1", {_SUM_SQL} AS "c2" FROM "public"."phase66 agg '
            'é" AS "s0" GROUP BY "s0"."group key"), "p1" ("c0", "c1", "c2") AS '
            '(SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c2" AS "c2" FROM '
            '"p0" AS "t1" WHERE ("t1"."c1" > CAST(0 AS pg_catalog.int8))), "p2" '
            '("c0", "c1", "c2", "c3") AS (SELECT "t2"."c0" AS "c0", "t2"."c1" AS '
            '"c1", "t2"."c2" AS "c2", "t2"."c2" AS "c3" FROM "p1" AS "t2") SELECT '
            '"t0"."c0" AS "key", "t0"."c1" AS "paid", "t0"."c2" AS "big" FROM '
            '"p2" AS "t0" ORDER BY "t0"."c3" DESC',
        ),
        (
            PROJECT_WHOLE,
            'WITH "p0" ("c0", "c1") AS (SELECT COUNT(CASE WHEN ("s0"."flag value" '
            'IS NULL) THEN 1 END) AS "c0", COALESCE(CAST(SUM(CASE WHEN (NOT '
            '"s0"."flag value") THEN CAST("s0"."row id" AS pg_catalog.int8) END) '
            'AS pg_catalog.int8), 0) AS "c1" FROM "public"."phase66 agg é" AS '
            '"s0") SELECT "t1"."c0" AS "paid", "t1"."c1" AS "big" FROM "p0" AS "t1"',
        ),
    ),
    ids=("grouped", "no_group_by"),
)
def test_a_project_emits_the_conditional_count_and_sum_on_postgres(
    tmp_path, body: str, sql: str
) -> None:
    """Project SQL writes the single-file shapes; both results are a non-null
    bigint, the sum's bounded by its checked CAST (R13 evidence), and HAVING
    and ORDER BY read the grouped outputs."""
    data = _project(tmp_path, "postgres", body)

    assert data["status"] == "VERIFIED"
    assert data["sql"] == sql
    assert [item["representation"] for item in data["columns"]][-2:] == [
        {
            "storage": {"kind": "pg_int8"},
            "nullable": False,
            "domain": {"kind": "int_range", "min": str(low), "max": str((1 << 63) - 1)},
        }
        for low in (0, -(1 << 63))
    ]
    assert [
        r["evidence"] for r in data["requirements"] if r["kind"] == "aggregate"
    ] == [
        [],
        [{"overflow": "target_checked_signed64_narrowing"}],
    ]


def test_a_project_refuses_the_conditional_count_and_sum_on_mysql(tmp_path) -> None:
    """MySQL has no conditional count yet, and its SUM of an Int is DECIMAL, as
    for `sum(Int)`: each is refused at its select item."""
    data = _project(tmp_path, "mysql", PROJECT_GROUPED)

    assert data["status"] == "BLOCKED"
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"], b["suggestion"])
        for b in data["blockers"]
    ] == [
        (
            "PIE-B1003",
            "conditional_count_not_admitted_on_target",
            16,
            "MySQL has no conditional count yet; emit with --dialect postgres.",
        ),
        (
            "PIE-B1004",
            "sum_int_aggregate_range_proof_missing",
            17,
            "Keep this expression in check/plan, or select a direct field with a "
            "reviewed carrier: the compiler lacks the required proof. Do not invent "
            "a range, meaning or bound in the contract.",
        ),
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_project_refuses_a_test_that_reads_no_field(tmp_path, target) -> None:
    """A test that reads no field is the same for every row: project SQL
    refuses it at its select item and says to test a member field."""
    body = (
        "query result:\n    from agg\n    group by key\n    select:\n        key\n"
        "        n = sum(1 for o in group if True)\n"
        "        s = sum(o.rid for o in group if not False)\n"
    )
    data = _project(tmp_path, target, body)

    assert data["status"] == "BLOCKED"
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"], b["suggestion"])
        for b in data["blockers"]
    ] == [
        (
            "PIE-B1003",
            "conditional_test_reads_no_field",
            line,
            "Test a field of the member, such as `if o.paid`: a test that reads no "
            "field is the same for every row.",
        )
        for line in (16, 17)
    ]


@pytest.mark.parametrize(
    ("body", "line"),
    (
        (
            "query result:\n    from agg\n    let v2 = value * 2\n    group by key\n"
            "    select:\n        key\n        m = sum(v2)\n"
            "        n = sum(1 for o in group if o.label > 1)\n",
            18,
        ),
        (
            "query result(lim: Int):\n    from agg\n    group by key\n    select:\n"
            "        key\n        n = sum(1 for o in group if o.label > 1)\n"
            "    having n > lim\n",
            16,
        ),
    ),
    ids=("let", "parameter"),
)
def test_a_project_blocks_at_a_generator_test_error(tmp_path, body, line) -> None:
    """A relation that reads a let or a query parameter blocks at its generator
    test's error, as `check` reports it, not at the whole relation."""
    data = _project(tmp_path, "postgres", body)

    assert data["status"] == "BLOCKED"
    assert [
        (d["code"], d["message"], d["location"]["line"], d["location"]["column"])
        for d in data["diagnostics"]
    ] == [
        (
            "PIE-S2105",
            "Invalid operands for operator >: expected comparable operands",
            line,
            37,
        )
    ]


PROJECT_GROUP_TEST = """query result:
    from agg
    group by key
    select:
        key
        every_flag = all(o.flag for o in group)
        some_a = any(o.label == "a" or o.flag is None for o in group)
    having every_flag or some_a
"""


def test_a_project_emits_the_test_of_a_group_on_postgres(tmp_path) -> None:
    """Project SQL writes the single-file shape: a count of the test compared
    with 0, a non-null Bool with no R13 evidence."""
    data = _project(tmp_path, "postgres", PROJECT_GROUP_TEST)

    every = '(COUNT(CASE WHEN "s0"."flag value" THEN NULL ELSE 1 END) = 0)'
    some = (
        '(COUNT(CASE WHEN (("s0"."text `""é" = CAST(E\'\\141\' AS pg_catalog.text) '
        'COLLATE "C") OR ("s0"."flag value" IS NULL)) THEN 1 END) > 0)'
    )
    assert data["status"] == "VERIFIED"
    assert data["sql"] == (
        f'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."group key" AS "c0", {every} '
        f'AS "c1", {some} AS "c2" FROM "public"."phase66 agg é" AS "s0" GROUP BY '
        '"s0"."group key"), "p1" ("c0", "c1", "c2") AS (SELECT "t1"."c0" AS "c0", '
        '"t1"."c1" AS "c1", "t1"."c2" AS "c2" FROM "p0" AS "t1" WHERE ("t1"."c1" OR '
        '"t1"."c2")) SELECT "t2"."c0" AS "key", "t2"."c1" AS "every_flag", '
        '"t2"."c2" AS "some_a" FROM "p1" AS "t2"'
    )
    assert [item["representation"] for item in data["columns"]][-2:] == [
        {
            "storage": {"kind": "pg_bool"},
            "nullable": False,
            "domain": {"kind": "bool01"},
        }
    ] * 2
    assert [
        r["evidence"] for r in data["requirements"] if r["kind"] == "aggregate"
    ] == [[], []]


def test_a_project_refuses_the_test_of_a_group_on_mysql(tmp_path) -> None:
    data = _project(tmp_path, "mysql", PROJECT_GROUP_TEST)

    assert data["status"] == "BLOCKED"
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"], b["suggestion"])
        for b in data["blockers"]
    ] == [
        (
            "PIE-B1003",
            "group_test_not_admitted_on_target",
            line,
            "MySQL has no group any or all yet; emit with --dialect postgres.",
        )
        for line in (16, 17)
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_project_refuses_a_group_test_that_reads_no_field(tmp_path, target) -> None:
    body = (
        "query result:\n    from agg\n    group by key\n    select:\n        key\n"
        "        a = any(True for o in group)\n"
        "        b = all(not False for o in group)\n"
    )
    data = _project(tmp_path, target, body)

    assert data["status"] == "BLOCKED"
    assert [
        (b["code"], b["subject"]["detail"], b["location"]["line"], b["suggestion"])
        for b in data["blockers"]
    ] == [
        (
            "PIE-B1003",
            "group_test_reads_no_field",
            line,
            "Test a field of the member, such as `any(o.paid for o in group)`: a "
            "test that reads no field is the same for every row.",
        )
        for line in (16, 17)
    ]


# Phase77 S03: conditional sums on MySQL.
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", ("C1", "C2", "C3", "C4", "c3_zero", "c3_largest"))
def test_mysql_conditional_sums_emit_the_guarded_sum(tmp_path, form, target, policy):
    """S03: a MySQL project emits the paired conditional sums, `if F`
    grouped by one INT key (C1 over a nullable, C4 over a non-null BIGINT),
    `if not F` and `if F is None` (C2) and `if I > L` for a non-negative Int
    literal L (C3, also over 0 and the largest Int), as COALESCE of S02's
    guarded SUM of CASE WHEN test THEN x END, 0: a non-null Int, 0 when no
    row matches, 1690 (SQLSTATE 22003) outside signed 64 bits. Under
    bind_safe_literals C3's literal stays in the SQL, so C3 emits its
    preserve_literals SQL on both families (on MySQL since MC G7). Every
    reader accepts each emitted form."""
    body = probe.S03_FORMS.get(form) or probe.S03_SPELLINGS[form][1]
    checked, outcome = probe.s03_world(tmp_path, target, body, policy)
    assert checked.verified
    if target == "mysql" or policy == "preserve_literals":
        # The public decoder reads no bind-safe aggregate test literal (main).
        probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.S03_FORM_SQL[form, target]
    document = json.loads(serialize_project_sql_emission(outcome))
    assert all(column["nullable"] is False for column in document["columns"])


# MC G7 (Conditional `sum` extension): the public nullability of each form's
# columns: a non-null GROUP BY key, each count and each conditional sum are
# non-null; a direct sum, `min`, `max` and `avg` are nullable.
G7_NON_NULL = {
    "T1": {"customer", "paid"},
    "T2": {"x", "y"},
    "T3": {"z"},
    "T4": {"customer", "t"},
    "T5": {"x"},
    "T6": {"k", "s", "t"},
    "B1": {"customer", "paid", "c"},
    "B2": {"customer", "y", "c"},
    "B3": {"y", "r"},
    "B4": {"customer", "nn", "x", "y", "m", "d"},
    "M1": {"customer", "paid"},
    "M2": {"x"},
    "M3": {"y"},
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(probe.G7_FORMS))
def test_mysql_g7_forms_emit_the_guarded_conditional_sum(tmp_path, form, target):
    """MC G7: in G2's cell a MySQL project emits a conditional sum of a
    BIGINT or INT field whose test is `not`, `and` and `or` over a Bool
    read, its `is None` and a BIGINT or INT read `>` an Int literal `N` or
    `-N`, beside other conditional sums, direct sums and G2's other
    aggregates, under G2's keys, WHERE and `let`s, as S03's COALESCE of the
    guarded SUM: a non-null Int, 0 when no row's test is True. Both families
    emit the pinned SQL, pairwise distinct per family and PostgreSQL's
    unchanged; every reader accepts it, the pure re-rendering included."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    checked, outcome = probe.s03_world(tmp_path, target, probe.G7_FORMS[form])
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G7_FORM_SQL[form, target]
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    ).canonical_bytes
    assert observed is not None and pure.rendering_refusal(observed) is None
    document = json.loads(serialize_project_sql_emission(outcome))
    assert {
        column["label"] for column in document["columns"] if not column["nullable"]
    } == G7_NON_NULL[form]
    texts = [probe.G7_FORM_SQL[name, target] for name in probe.G7_FORMS]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("spelling", sorted(probe.G7_SPELLINGS))
def test_mysql_g7_spellings_emit_their_form_sql(tmp_path, spelling, target):
    """The list's sixteen other spellings (a `table`, parentheses around a
    test, its atoms, the argument, a negative literal, its digits or a
    SELECT item, another generator name, a `def` in the test, a read
    qualified by the source's name) emit the form's bytes on both families,
    and every reader accepts them."""
    form, body = probe.G7_SPELLINGS[spelling]
    _, outcome = probe.s03_world(tmp_path, target, body)
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G7_FORM_SQL[form, target]


@pytest.mark.parametrize(
    ("name", "policy"),
    [
        (name, policy)
        for name, (_, _, policies) in sorted(probe.G7_CELLS.items())
        for policy in policies
    ],
)
def test_mysql_g7_cells_emit_the_sql_they_spell(tmp_path, name, policy):
    """The neighbours the law opens (MC.14), five of S03's eleven refusals
    among them (T1, T3, B1, B2 and M1 are five more, C3 under
    bind_safe_literals its S03 case): a qualified key or key read,
    parentheses, a `def` at any position of a test, with or without
    arguments, a bare GROUP BY key in a test, `not` over `and`, `is None` or
    `not`, S02's conditional sum (G2's neighbour conditional_sum among them)
    and one by S02's own non-null SMALLINT key.
    Every reader accepts each (on PostgreSQL under preserve_literals: the
    public decoder reads no bind-safe aggregate test literal there), and
    each emits on both families the SQL of the S03 form or statement it
    spells under preserve_literals, so no reader takes a spelling another
    refuses."""
    body, equal, _ = probe.G7_CELLS[name]
    world = getattr(probe, probe.G7_WORLDS.get(name, "s03_world"))
    for target in ("postgres", "mysql"):
        _, outcome = world(tmp_path / target, target, body, policy)
        if target == "mysql" or policy == "preserve_literals":
            probe.numeric_readers_accept(outcome)
        assert outcome.artifact is not None
        if equal in probe.S03_FORMS:
            expected = probe.S03_FORM_SQL[equal, target]
        elif equal is not None:
            _, spelled = probe.s03_world(tmp_path / f"{target}-equal", target, equal)
            assert spelled.artifact is not None
            expected = spelled.artifact.rendered.sql.decode()
        else:
            continue
        assert outcome.artifact.rendered.sql.decode() == expected


# The SMALLINT and INT fields of each world a G7 body runs in, by name: a
# MIN or MAX of one is the SIGNED cast `my_signed_int` on MySQL (A20), which
# PostgreSQL leaves uncast over its int2 or int4.
_G7_NARROW_FIELDS = {
    "s03_world": frozenset({"customer"}),
    "numeric_world": frozenset({"k", "c"}),
    "division_world": frozenset({"i", "j", "s", "t"}),
}


def _g7_spelling(sql, body, world="s03_world"):
    """BM: main's PostgreSQL SQL in MySQL's spelling, each conditional sum
    COALESCE of S02's guarded SUM of CASE WHEN test THEN x END, 0, each
    direct sum the guarded SUM of x, each bigint cast of a literal SIGNED,
    each float8 cast of an `avg` argument DOUBLE, and each MIN or MAX of a
    SMALLINT or INT field of ``world`` (_G7_NARROW_FIELDS; qualified or
    through a `let` name, as ``body`` writes it) cast to SIGNED, as main's
    MySQL SQL casts it (A20): the casts follow from ``body`` and the world's
    shapes, not from the MySQL SQL under test."""
    import re

    from pietto._project.project_sql_emission_aggregation import MYSQL_SUM_GUARD

    guard = [text for _, text in MYSQL_SUM_GUARD]
    text = body if type(body) is str else body["main.pietto"]
    lets = dict(re.findall(r"^    let (\w+) = (.+)$", text, re.M))
    narrow = _G7_NARROW_FIELDS[world]
    widened = [
        re.findall(r"\w+", lets.get(name, name))[-1] in narrow
        for name in (
            re.findall(r"\w+", argument)[-1]
            for argument in re.findall(r"= \(?(?:min|max)\((.+?)\)\)?$", text, re.M)
        )
    ]
    extremes = re.compile(r"(?:MIN|MAX)\([^()]+\)")
    assert len(widened) == len(extremes.findall(sql))
    marks = iter(widened)
    sql = extremes.sub(
        lambda found: (
            f"CAST({found.group(0)} AS SIGNED)" if next(marks) else found.group(0)
        ),
        sql,
    )

    def guarded(argument):
        return argument.join(guard)

    sql = re.sub(
        r"COALESCE\(CAST\(SUM\(CASE WHEN (.*?) THEN CAST\((\S+) AS pg_catalog\.int8\)"
        r" END\) AS pg_catalog\.int8\), 0\)",
        lambda found: (
            "COALESCE(%s, 0)"
            % guarded("CASE WHEN %s THEN %s END" % (found.group(1), found.group(2)))
        ),
        sql,
    )
    sql = re.sub(
        r"CAST\(SUM\(CAST\((\S+) AS pg_catalog\.int8\)\) AS pg_catalog\.int8\)",
        lambda found: guarded(found.group(1)),
        sql,
    )
    return (
        sql.replace("AS pg_catalog.int8)", "AS SIGNED)")
        .replace("AS pg_catalog.float8)", "AS DOUBLE)")
        .replace('"', "`")
        .replace("`public`.", "`phase66`.")
    )


@pytest.mark.parametrize(
    "name",
    sorted(
        {
            *probe.G7_FORMS,
            *probe.G7_SPELLINGS,
            *probe.G7_CELLS,
        }
    ),
)
def test_mysql_g7_sql_is_main_postgresql_sql_in_mysql_spelling(tmp_path, name):
    """BM: each G7 body's MySQL SQL is main's PostgreSQL SQL of it in
    MySQL's spelling, each sum the guarded SUM (_g7_spelling): so every
    test, key, other aggregate, FROM, WHERE and `let` stage is the SQL that
    main spells on both families, and a combination the forms do not run
    rests on the forms' parts. Every reader accepts S02's conditional sum over
    numeric_world. A `min` or `max` of an
    INT field among them (B3's `lo = min(customer)`) is MySQL's SIGNED cast
    (A20), which PostgreSQL leaves uncast."""
    world_name = probe.G7_WORLDS.get(name, "s03_world")
    world = getattr(probe, world_name)
    body = (
        probe.G7_FORMS.get(name)
        or probe.G7_SPELLINGS.get(name, (None, None))[1]
        or probe.G7_CELLS[name][0]
    )
    _, postgres = world(tmp_path / "postgres", "postgres", body)
    _, mysql = world(tmp_path / "mysql", "mysql", body)
    probe.numeric_readers_accept(mysql)
    assert postgres.artifact is not None and mysql.artifact is not None
    assert mysql.artifact.rendered.sql.decode() == _g7_spelling(
        postgres.artifact.rendered.sql.decode(), body, world_name
    )


@pytest.mark.parametrize("form", sorted(probe.G7_FORMS))
def test_mysql_g7_test_literals_stay_under_bind_safe_literals(tmp_path, form):
    """BB: a test literal is an aggregate argument's, which
    bind_safe_literals keeps in the SQL, so a form without a WHERE literal
    emits its preserve_literals SQL on both families, every reader
    accepting it; M1 to M3 bind their WHERE literal, a bind-safe `?`, and
    keep main's blockers on MySQL, PIE-B1004 at each sum."""
    body = probe.G7_FORMS[form]
    _, postgres = probe.s03_world(
        tmp_path / "postgres", "postgres", body, "bind_safe_literals"
    )
    _, mysql = probe.s03_world(tmp_path / "mysql", "mysql", body, "bind_safe_literals")
    assert postgres.artifact is not None
    if form.startswith("M"):
        assert "$1" in postgres.artifact.rendered.sql.decode()
        assert mysql.status == "BLOCKED" and mysql.artifact is None
        assert [(blocker.code, blocker.detail) for blocker in mysql.blockers] == [
            ("PIE-B1004", "sum_int_aggregate_range_proof_missing")
        ] * body.count("= sum(")
        return
    probe.numeric_readers_accept(mysql)
    assert mysql.artifact is not None
    for target, outcome in (("postgres", postgres), ("mysql", mysql)):
        assert outcome.artifact is not None
        assert outcome.artifact.rendered.sql.decode() == probe.G7_FORM_SQL[form, target]


def test_mysql_g7_test_sign_belongs_to_the_unary_operator(tmp_path):
    from dataclasses import replace

    from pietto._project.project_sql_emission_ast import SQLRowQuery
    from pietto._project.project_sql_emission_rows import mysql_sum_test

    _, outcome = probe.s03_world(tmp_path, "mysql", probe.G7_FORMS["T3"])
    assert outcome.artifact is not None
    assert type(outcome.artifact.ast) is SQLRowQuery
    comparison = outcome.artifact.ast.bodies[0].columns[0].delimiter
    left, minus = comparison.operands
    anchor = minus.operand
    assert anchor.operand.value == 5 and mysql_sum_test(comparison)
    negative = replace(anchor, operand=replace(anchor.operand, value=-5))
    for right in (negative, replace(minus, operand=negative)):
        assert not mysql_sum_test(replace(comparison, operands=(left, right)))


def _g7_blockers(outcome):
    return [
        (
            blocker["code"],
            blocker["subject"]["detail"],
            *(
                (None, None)
                if blocker["location"] is None
                else (blocker["location"]["line"], blocker["location"]["column"])
            ),
        )
        for blocker in json.loads(serialize_project_sql_emission(outcome))["blockers"]
    ]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G7_REFUSALS))
def test_mysql_g7_neighbours_keep_main_refusal(tmp_path, shape, policy):
    """Rule two (D77.37): a statement the G7 law matches beside another
    blocker (a label too long, a sum outside every cell, a header parameter,
    a bind-safe `?`; MC s03n opens G7's R3 and R6 to R8, an ORDER BY, a
    relation alias, an upstream query and an imported source over the bases
    its Law C names) and one outside it (`>=`, `is None` of an Int, the
    conditional count, a sum in an expression, `is not None`, two fields
    compared, a literal on the left, an Int literal outside the range, a
    Bool literal, literal arithmetic, `+N`, `-(-N)`, a SMALLINT field
    compared or summed, a SMALLINT key read in a test, S02's own SMALLINT
    key, `count` or `min` beside any conditional sum) keep main's blockers, object for
    object, under each policy they are refused with;
    PostgreSQL emits each but the long label and the two literals as main
    does."""
    if policy not in probe.G7_REFUSAL_POLICIES.get(shape, (policy,)):
        pytest.skip("refused under its own policy only")
    body = probe.G7_REFUSALS[shape]
    world = getattr(probe, probe.G7_WORLDS.get(shape, "s03_world"))
    _, outcome = world(tmp_path / "mysql", "mysql", body, policy)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _g7_blockers(outcome) == probe.G7_REFUSAL_BLOCKERS[shape]
    _, postgres = world(tmp_path / "postgres", "postgres", body, policy)
    if shape in probe.G7_POSTGRES_BLOCKERS:
        assert _g7_blockers(postgres) == probe.G7_POSTGRES_BLOCKERS[shape]
    else:
        assert postgres.status == "VERIFIED", postgres.blockers
