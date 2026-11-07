"""SQL of the conditional count and sum of a group (Phase73 S02):
`sum(1 for o in group if TEST)` and `sum(o.f for o in group if TEST)`."""

from __future__ import annotations

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
