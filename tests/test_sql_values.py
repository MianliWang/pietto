"""Typed VALUES emission: exact dialect SQL, declared types and target refusal.

A VALUES body is one generated unit. Every cell, NULL included, is CAST to its
column's declared type and every column alias is written by the SQL itself, so
no name or type is left to the database. A statement that reads no physical
relation is refused on MySQL before any connection.
"""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from typing import Any, cast

import pytest

import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_values as valuing
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_verification import (
    verify_row_bytes,
    verify_row_query,
)

TARGETS = ("postgres", "mysql")
PG_TEXT = ' AS pg_catalog.text) COLLATE "C"'
MY_TEXT = " AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin"
PG_LHS = '"public"."phase66 lhs é"'
MY_LHS = "`phase66`.`phase66 lhs é`"


def _emit(tmp_path: Path, target: str, body: str, policy="preserve_literals"):
    item = probe.join_witness(target, body, policy=policy)
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    return outcome, json.loads(serialize_project_sql_emission(outcome))


TOP = (
    "query result:\n    values(id: Int not null, label: Text nullable):\n"
    '        1, "a"\n        2, null\n'
)
LET_FROM = (
    "query result:\n    let seed:\n"
    "        values(id: Int not null, label: Text nullable):\n"
    '            1, "a"\n            2, null\n'
    "    from seed\n    where id > 1\n    select:\n        id\n        label\n"
)
LET_JOIN = (
    "query result:\n    let seed:\n"
    "        values(rid: Int not null, label: Text nullable):\n"
    '            1, "a"\n            2, null\n'
    "    from lhs\n    inner join seed as s:\n        from lhs\n"
    "        on lhs.id == s.rid\n    select:\n        a = lhs.id\n        b = s.label\n"
)
ZERO_JOIN = (
    "query result:\n    let seed:\n"
    "        values(rid: Int not null, label: Text nullable)\n"
    "    from lhs\n    left join seed as s:\n        from lhs\n"
    "        on lhs.id == s.rid\n    select:\n        a = lhs.id\n        b = s.label\n"
)
# A row-level let over a VALUES let reads its declared schema like any relation.
ROW_LET = (
    "query result:\n    let seed:\n"
    "        values(id: Int not null, label: Text nullable):\n"
    '            1, "a"\n            2, null\n'
    "    from seed\n    let:\n        missing = label is null\n"
    "    where id > 1\n    select:\n        id\n        missing\n"
)
SET_OPERAND = (
    "query result:\n    let seed:\n        values(id: Int not null, key: Int nullable):\n"
    "            7, null\n    union all:\n        from seed\n        from lhs\n"
)

EXPECTED = {
    ("top", "postgres"): (
        'SELECT "v0"."c0" AS "id", "v0"."c1" AS "label" FROM (VALUES '
        "(CAST(1 AS pg_catalog.int8), CAST(E'\\141'" + PG_TEXT + "), "
        "(CAST(2 AS pg_catalog.int8), CAST(NULL" + PG_TEXT + ')) AS "v0" ("c0", "c1")'
    ),
    ("let_from", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (VALUES '
        "(CAST(1 AS pg_catalog.int8), CAST(E'\\141'" + PG_TEXT + "), "
        "(CAST(2 AS pg_catalog.int8), CAST(NULL" + PG_TEXT + ")), "
        '"p1" ("c0", "c1") AS (SELECT "s0"."c0" AS "c0", "s0"."c1" AS "c1" '
        'FROM "p0" AS "s0" WHERE ("s0"."c0" > CAST(1 AS pg_catalog.int8))) '
        'SELECT "t1"."c0" AS "id", "t1"."c1" AS "label" FROM "p1" AS "t1"'
    ),
    ("let_join", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (VALUES '
        "(CAST(1 AS pg_catalog.int8), CAST(E'\\141'" + PG_TEXT + "), "
        "(CAST(2 AS pg_catalog.int8), CAST(NULL" + PG_TEXT + ")), "
        '"p1" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."c0" AS "c2", "m1"."c1" AS "c3" '
        f'FROM {PG_LHS} AS "m0" INNER JOIN "p0" AS "m1" '
        'ON ("m0"."order.id" = "m1"."c0")) '
        'SELECT "t0"."c0" AS "a", "t0"."c3" AS "b" FROM "p1" AS "t0"'
    ),
    ("let_join", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (VALUES "
        "ROW(CAST(1 AS SIGNED), CAST(X'61'" + MY_TEXT + "), "
        "ROW(CAST(2 AS SIGNED), CAST(NULL" + MY_TEXT + ")), "
        "`p1` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `m0`.`order.id` AS `c0`, "
        "`m0`.`key value` AS `c1`, `m1`.`c0` AS `c2`, `m1`.`c1` AS `c3` "
        f"FROM {MY_LHS} AS `m0` INNER JOIN `p0` AS `m1` "
        "ON (`m0`.`order.id` = `m1`.`c0`)) "
        "SELECT `t0`.`c0` AS `a`, `t0`.`c3` AS `b` FROM `p1` AS `t0`"
    ),
    ("zero_join", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT CAST(NULL AS pg_catalog.int8) AS "c0", '
        "CAST(NULL" + PG_TEXT + ' AS "c1" WHERE FALSE), '
        '"p1" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."c0" AS "c2", "m1"."c1" AS "c3" '
        f'FROM {PG_LHS} AS "m0" LEFT JOIN "p0" AS "m1" '
        'ON ("m0"."order.id" = "m1"."c0")) '
        'SELECT "t0"."c0" AS "a", "t0"."c3" AS "b" FROM "p1" AS "t0"'
    ),
    ("zero_join", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT CAST(NULL AS SIGNED) AS `c0`, "
        "CAST(NULL" + MY_TEXT + " AS `c1` WHERE FALSE), "
        "`p1` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `m0`.`order.id` AS `c0`, "
        "`m0`.`key value` AS `c1`, `m1`.`c0` AS `c2`, `m1`.`c1` AS `c3` "
        f"FROM {MY_LHS} AS `m0` LEFT JOIN `p0` AS `m1` "
        "ON (`m0`.`order.id` = `m1`.`c0`)) "
        "SELECT `t0`.`c0` AS `a`, `t0`.`c3` AS `b` FROM `p1` AS `t0`"
    ),
    ("row_let", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (VALUES '
        "(CAST(1 AS pg_catalog.int8), CAST(E'\\141'" + PG_TEXT + "), "
        "(CAST(2 AS pg_catalog.int8), CAST(NULL" + PG_TEXT + ")), "
        '"p1" ("c0", "c1", "c2") AS (SELECT "s0"."c0" AS "c0", "s0"."c1" AS "c1", '
        '("s0"."c1" IS NULL) AS "c2" FROM "p0" AS "s0"), '
        '"p2" ("c0", "c1", "c2") AS (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", '
        '"t1"."c2" AS "c2" FROM "p1" AS "t1" '
        'WHERE ("t1"."c0" > CAST(1 AS pg_catalog.int8))) '
        'SELECT "t2"."c0" AS "id", "t2"."c2" AS "missing" FROM "p2" AS "t2"'
    ),
    ("set_operand", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (VALUES '
        "(CAST(7 AS pg_catalog.int8), CAST(NULL AS pg_catalog.int8))) "
        '(SELECT "o0"."c0" AS "id", "o0"."c1" AS "key" FROM "p0" AS "o0") '
        'UNION ALL (SELECT "o1"."order.id" AS "id", "o1"."key value" AS "key" '
        f'FROM {PG_LHS} AS "o1")'
    ),
    ("set_operand", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (VALUES "
        "ROW(CAST(7 AS SIGNED), CAST(NULL AS SIGNED))) "
        "(SELECT `o0`.`c0` AS `id`, `o0`.`c1` AS `key` FROM `p0` AS `o0`) "
        "UNION ALL (SELECT `o1`.`order.id` AS `id`, `o1`.`key value` AS `key` "
        f"FROM {MY_LHS} AS `o1`)"
    ),
}
BODIES = {
    "top": TOP,
    "let_from": LET_FROM,
    "let_join": LET_JOIN,
    "zero_join": ZERO_JOIN,
    "row_let": ROW_LET,
    "set_operand": SET_OPERAND,
}


@pytest.mark.parametrize("case,target", sorted(EXPECTED))
def test_values_emits_exact_typed_dialect_sql(
    tmp_path: Path, case: str, target: str
) -> None:
    outcome, document = _emit(tmp_path, target, BODIES[case])
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == EXPECTED[case, target]
    if case != "set_operand":
        # The independent public decoder re-derives every token and column.
        probe.decode_public(serialize_project_sql_emission(outcome))
    # Bind-safe policy binds ordinary literals; VALUES cells stay fixed.
    _, bound = _emit(tmp_path / "bind", target, BODIES[case], "bind_safe_literals")
    assert bound["status"] == "VERIFIED", bound
    fixed = [v for v in bound["fixed_values"]]
    assert len(fixed) == (1 if case in {"let_from", "row_let"} else 0)
    sql = bound["sql"]
    assert sql == EXPECTED[case, target].replace(
        "> CAST(1 AS pg_catalog.int8)", "> CAST($1 AS pg_catalog.int8)"
    )


@pytest.mark.parametrize("case", ("top", "let_from"))
def test_mysql_refuses_a_statement_without_physical_source(
    tmp_path: Path, case: str
) -> None:
    outcome, document = _emit(tmp_path, "mysql", BODIES[case])
    assert document["status"] == "BLOCKED"
    (blocker,) = document["blockers"]
    assert (blocker["code"], blocker["subject"]["detail"]) == (
        "PIE-B1003",
        "zero_physical_source_not_admitted_on_target",
    )
    assert blocker["location"]["line"] == (7 if case == "top" else 8)


# A header query reads a VALUES table; a header beside a relation let is gated.
PARAMETER_FROM = (
    "table v:\n    values(id: Int not null, label: Text nullable):\n"
    '        1, "a"\n        2, null\n'
    "query result(low: Int not null):\n    from v\n    where id > low\n"
    "    select:\n        id\n        label\n"
)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("case", ("top", "let_from", "parameter_from"))
def test_the_public_decoder_reads_a_source_free_values_statement(
    tmp_path: Path, target: str, case: str
) -> None:
    """compile_query refuses a contract that lists an unread source, so a
    VALUES-only statement is emitted against no contract source at all; the
    independent decoder reads that document (and MySQL's BLOCKED form). A
    physical read still needs its contract source."""
    body = PARAMETER_FROM if case == "parameter_from" else BODIES[case]
    item = probe.join_witness(target, body, policy="bind_safe_literals")
    contract = json.loads(item["contract"])
    contract["sources"] = []
    _, outcome = probe.build_case(
        tmp_path, item["source"], probe.encoded(contract).decode(), item["policy"]
    )
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert document["status"] == ("VERIFIED" if target == "postgres" else "BLOCKED")
    if target == "postgres" and case == "parameter_from":
        assert document["format"] == probe.PARAMETERIZED_FORMAT
    _, physical = _emit(tmp_path / "physical", target, LET_JOIN)
    physical["request"]["contract"]["sources"] = []
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(physical))


SHADOW_VALUES = (
    "query v:\n    values(code: Int not null, note: Text nullable):\n"
    '        1, "a"\n        2, null\n'
)


def test_a_header_named_like_a_values_column_emits_no_sql(tmp_path: Path) -> None:
    """The column `code` is never read as the parameter `code`."""
    shadowed = SHADOW_VALUES + (
        "query result(code: Int not null):\n    from v\n    where code > 1\n"
        "    select:\n        note\n"
    )
    _, document = _emit(
        tmp_path / "shadowed", "postgres", shadowed, policy="bind_safe_literals"
    )
    assert document["status"] == "BLOCKED" and "sql" not in document
    assert [
        (d["code"], d["location"]["line"], d["location"]["column"])
        for d in document["diagnostics"]
    ] == [("PIE-S2354", 10, 14)]
    distinct = shadowed.replace("result(code:", "result(low:").replace(
        "code > 1", "code > low"
    )
    _, document = _emit(
        tmp_path / "distinct", "postgres", distinct, policy="bind_safe_literals"
    )
    assert document["status"] == "VERIFIED"
    assert document["sql"].endswith(
        'FROM "p0" AS "s0" WHERE ("s0"."c0" > CAST($1 AS pg_catalog.int8)))'
        ' SELECT "t1"."c1" AS "note" FROM "p1" AS "t1"'
    )


# `a` reads `seed`, written after it, and the body reads `seed` again.
REUSED_FORWARD = (
    "query result:\n    let a:\n        from seed\n        where rid > 1\n"
    "        select:\n            rid\n    let seed:\n"
    "        values(rid: Int not null):\n            1\n            2\n"
    "    from lhs\n    inner join a as x:\n        from lhs\n"
    "        on lhs.id == x.rid\n    inner join seed as s:\n        from lhs\n"
    "        on lhs.id == s.rid\n    select:\n        id = lhs.id\n"
)


@pytest.mark.parametrize("target", TARGETS)
def test_a_reused_forward_values_let_is_one_cte(tmp_path: Path, target: str) -> None:
    outcome, document = _emit(tmp_path, target, REUSED_FORWARD)
    assert document["status"] == "VERIFIED"
    sql = document["sql"]
    q = '"' if target == "postgres" else "`"
    assert sql.count("VALUES") == 1 and sql.startswith(f"WITH {q}p0{q} ")
    # Both readers refer to that one CTE.
    assert f"FROM {q}p0{q} AS {q}s0{q} WHERE" in sql
    assert f"INNER JOIN {q}p0{q} AS {q}m3{q} ON" in sql
    probe.decode_public(serialize_project_sql_emission(outcome))


# The native Q_values_rows/reads witness: `seed` is read before it is written
# and again as the JOIN target, every closed read kind reads a VALUES let or a
# let over one, and `spare` is read only through `not exists gone`.
READS_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (VALUES (CAST(0 AS pg_catalog.int8), CAST(E\'\\172\' AS pg_catalog.text) COLLATE "C"), (CAST(1 AS pg_catalog.int8), CAST(NULL AS pg_catalog.text) COLLATE "C"), (CAST(1 AS pg_catalog.int8), CAST(E\'\\171\' AS pg_catalog.text) COLLATE "C")), '
        '"p1" ("c0") AS (VALUES (CAST(E\'\\171\' AS pg_catalog.text) COLLATE "C")), '
        '"p2" ("c0") AS (VALUES (CAST(1 AS pg_catalog.int8)), (CAST(NULL AS pg_catalog.int8))), '
        '"p3" ("c0") AS (SELECT CAST(NULL AS pg_catalog.text) COLLATE "C" AS "c0" WHERE FALSE), '
        '"p4" ("c0") AS (VALUES (CAST(0 AS pg_catalog.int8))), '
        '"p5" ("c0") AS (SELECT "s0"."order.id" AS "c0" FROM "public"."phase66 empty é" AS "s0"), '
        '"p6" ("c0", "c1") AS (SELECT "s1"."c0" AS "c0", "s1"."c1" AS "c1" FROM "p0" AS "s1" WHERE ("s1"."c1" = CAST(E\'\\171\' AS pg_catalog.text) COLLATE "C")), '
        '"p7" ("c0") AS (SELECT "t2"."c0" AS "c0" FROM "p6" AS "t2"), '
        '"p8" ("c0", "c1", "c2", "c3", "c4", "c5", "c6") AS (SELECT "m0"."order.id" AS "c0", "m0"."flag value" AS "c1", "m0"."text `""é" AS "c2", "m0"."amount value" AS "c3", "m0"."ratio value" AS "c4", "m1"."c0" AS "c5", "m1"."c1" AS "c6" FROM "public"."phase66 source é" AS "m0" INNER JOIN "p0" AS "m1" ON ("m0"."order.id" = "m1"."c0")), '
        '"p9" ("c0", "c1", "c2", "c3", "c4", "c5", "c6") AS (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", "t0"."c2" AS "c2", "t0"."c3" AS "c3", "t0"."c4" AS "c4", "t0"."c5" AS "c5", "t0"."c6" AS "c6" FROM "p8" AS "t0" WHERE (EXISTS (SELECT 1 FROM "p7" AS "e0") AND (NOT EXISTS (SELECT 1 FROM "p5" AS "e1")))) '
        'SELECT "t4"."c0" AS "a", "t4"."c6" AS "b", ("t4"."c6" IN (SELECT "e2"."c0" FROM "p1" AS "e2")) AS "hit", ("t4"."c0" NOT IN (SELECT "e3"."c0" FROM "p2" AS "e3")) AS "miss", ("t4"."c2" NOT IN (SELECT "e4"."c0" FROM "p3" AS "e4")) AS "kept", (SELECT "e5"."c0" FROM "p4" AS "e5") AS "low" FROM "p9" AS "t4"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (VALUES ROW(CAST(0 AS SIGNED), CAST(X'7a' AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin), ROW(CAST(1 AS SIGNED), CAST(NULL AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin), ROW(CAST(1 AS SIGNED), CAST(X'79' AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin)), "
        "`p1` (`c0`) AS (VALUES ROW(CAST(X'79' AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin)), "
        "`p2` (`c0`) AS (VALUES ROW(CAST(1 AS SIGNED)), ROW(CAST(NULL AS SIGNED))), "
        "`p3` (`c0`) AS (SELECT CAST(NULL AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin AS `c0` WHERE FALSE), "
        "`p4` (`c0`) AS (VALUES ROW(CAST(0 AS SIGNED))), "
        "`p5` (`c0`) AS (SELECT `s0`.`order.id` AS `c0` FROM `phase66`.`phase66 empty é` AS `s0`), "
        "`p6` (`c0`, `c1`) AS (SELECT `s1`.`c0` AS `c0`, `s1`.`c1` AS `c1` FROM `p0` AS `s1` WHERE (`s1`.`c1` = CAST(X'79' AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin)), "
        "`p7` (`c0`) AS (SELECT `t2`.`c0` AS `c0` FROM `p6` AS `t2`), "
        '`p8` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`) AS (SELECT `m0`.`order.id` AS `c0`, `m0`.`flag value` AS `c1`, `m0`.`text ``"é` AS `c2`, `m0`.`amount value` AS `c3`, `m0`.`ratio value` AS `c4`, `m1`.`c0` AS `c5`, `m1`.`c1` AS `c6` FROM `phase66`.`phase66 source é` AS `m0` INNER JOIN `p0` AS `m1` ON (`m0`.`order.id` = `m1`.`c0`)), '
        "`p9` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`) AS (SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1`, `t0`.`c2` AS `c2`, `t0`.`c3` AS `c3`, `t0`.`c4` AS `c4`, `t0`.`c5` AS `c5`, `t0`.`c6` AS `c6` FROM `p8` AS `t0` WHERE (EXISTS (SELECT 1 FROM `p7` AS `e0`) AND (NOT EXISTS (SELECT 1 FROM `p5` AS `e1`)))) "
        "SELECT `t4`.`c0` AS `a`, `t4`.`c6` AS `b`, (`t4`.`c6` IN (SELECT `e2`.`c0` FROM `p1` AS `e2`)) AS `hit`, (`t4`.`c0` NOT IN (SELECT `e3`.`c0` FROM `p2` AS `e3`)) AS `miss`, (`t4`.`c2` NOT IN (SELECT `e4`.`c0` FROM `p3` AS `e4`)) AS `kept`, (SELECT `e5`.`c0` FROM `p4` AS `e5`) AS `low` FROM `p9` AS `t4`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_values_lets_feed_every_read_kind_beside_a_join(
    tmp_path: Path, target: str
) -> None:
    from pietto._project.project_postgres_source_assurance import (
        qualification_roots,
    )
    from pietto._project.project_sql_plan import ProjectSQLPlan

    item = probe.fixture(target, "Q_values_rows", "reads")
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == "".join(READS_SQL[target])
    # `in`/`not in` stay three-valued and nullable; `scalar` is nullable.
    assert [
        (c["label"], c["logical_type"]["name"], c["nullable"])
        for c in document["columns"]
    ] == [
        ("a", "Int", False),
        ("b", "Text", True),
        ("hit", "Bool", True),
        ("miss", "Bool", True),
        ("kept", "Bool", True),
        ("low", "Int", True),
    ]
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    assert [s.declaration.name for s in plan.sources] == ["rows", "spare"]
    assert outcome.artifact is not None
    request = outcome.artifact.request
    assert [s.name for s in request.sources] == [
        "phase66 source é",
        "phase66 empty é",
    ]
    assert qualification_roots(request.sources, ()) == tuple(
        (s.namespace, s.name) for s in request.sources
    )
    probe.decode_public(serialize_project_sql_emission(outcome))
    # Without its contract mapping the source read only by `exists` blocks.
    contract = json.loads(item["contract"])
    contract["sources"] = contract["sources"][:1]
    _, missing = probe.build_case(
        tmp_path / "missing", item["source"], json.dumps(contract), item["policy"]
    )
    blocked = json.loads(serialize_project_sql_emission(missing))
    assert blocked["status"] == "BLOCKED" and "sql" not in blocked
    assert [
        (
            b["code"],
            b["subject"]["detail"],
            None if b["location"] is None else b["location"]["line"],
        )
        for b in blocked["blockers"]
    ] == [
        ("PIE-B1001", "source_mapping_missing", None),
        ("PIE-B1001", "source_mapping_missing", 8),
    ]


def test_every_declared_type_null_duplicate_and_bound_cell_is_written(
    tmp_path: Path,
) -> None:
    body = (
        "query result:\n"
        "    values(id: Int not null, n: Int nullable, f: Float nullable,"
        " b: Bool nullable, t: Text nullable):\n"
        "        1, null, null, null, null\n        1, null, null, null, null\n"
        '        -9223372036854775808, 9223372036854775807, -2.5, true, "it\'s"\n'
    )
    outcome, document = _emit(tmp_path, "postgres", body)
    assert document["status"] == "VERIFIED", document
    nulls = (
        "CAST(NULL AS pg_catalog.int8), CAST(NULL AS pg_catalog.float8), "
        "CAST(NULL AS pg_catalog.bool), CAST(NULL" + PG_TEXT
    )
    assert document["sql"] == (
        'SELECT "v0"."c0" AS "id", "v0"."c1" AS "n", "v0"."c2" AS "f", '
        '"v0"."c3" AS "b", "v0"."c4" AS "t" FROM (VALUES '
        f"(CAST(1 AS pg_catalog.int8), {nulls}), "
        f"(CAST(1 AS pg_catalog.int8), {nulls}), "
        "(CAST(-9223372036854775808 AS pg_catalog.int8), "
        "CAST(9223372036854775807 AS pg_catalog.int8), "
        "CAST('-2.5' AS pg_catalog.float8), CAST(TRUE AS pg_catalog.bool), "
        "CAST(E'\\151\\164\\047\\163'" + PG_TEXT + ')) AS "v0" '
        '("c0", "c1", "c2", "c3", "c4")'
    )
    columns = document["columns"]
    assert [
        (c["label"], c["logical_type"]["name"], c["nullable"]) for c in columns
    ] == [
        ("id", "Int", False),
        ("n", "Int", True),
        ("f", "Float", True),
        ("b", "Bool", True),
        ("t", "Text", True),
    ]
    assert [c["representation"]["domain"] for c in columns] == [
        {"kind": "int_range", "min": "-9223372036854775808", "max": "1"},
        {
            "kind": "int_range",
            "min": "9223372036854775807",
            "max": "9223372036854775807",
        },
        {"kind": "finite_float", "format": "binary64"},
        {"kind": "bool01"},
        {
            "kind": "text",
            "max_characters": 4,
            "encoding": "UTF8",
            "collation": "C",
            "padding": "NO PAD",
        },
    ]
    assert document["request"]["contract"]["sources"][0]["selector"]["name"] == "lhs"
    assert {r["kind"] for r in document["requirements"]} >= {
        "values",
        "values_rows",
        "values_column",
    }


def test_a_zero_row_statement_is_a_typed_empty_select(tmp_path: Path) -> None:
    body = "query result:\n    values(id: Int not null, t: Text nullable)\n"
    _, document = _emit(tmp_path, "postgres", body)
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == (
        'SELECT CAST(NULL AS pg_catalog.int8) AS "id", CAST(NULL'
        + PG_TEXT
        + ' AS "t" WHERE FALSE'
    )


def test_the_independent_checks_reject_a_changed_values_unit(tmp_path: Path) -> None:
    outcome, document = _emit(tmp_path, "postgres", LET_JOIN)
    assert document["status"] == "VERIFIED"
    artifact = cast(Any, outcome.artifact)
    query = artifact.ast
    (unit,) = (u for u in query.units if type(u) is valuing.ValuesBody)
    assert verify_row_query(artifact.request, query)
    assert verify_row_bytes(query, artifact.rendered)
    changed_rows = replace(unit, rows=((1, "a"), (3, None)))
    changed_type = replace(
        unit, columns=(replace(unit.columns[0], physical="pg_int4"), unit.columns[1])
    )
    for changed in (changed_rows, changed_type):
        units = tuple(changed if u is unit else u for u in query.units)
        swapped = replace(query, units=units)
        assert not verify_row_query(artifact.request, swapped)
    tampered = replace(
        artifact.rendered,
        sql=artifact.rendered.sql.replace(b"CAST(2 AS", b"CAST(3 AS"),
    )
    assert not verify_row_bytes(query, tampered)


def _int_body(rows: int, columns: int) -> str:
    names = ", ".join(f"c{i}: Int not null" for i in range(columns))
    row = ", ".join("0" for _ in range(columns))
    return f"query result:\n    values({names}):\n" + f"        {row}\n" * rows


@pytest.mark.parametrize(
    "target,rows,columns,blockers",
    (
        ("postgres", 1000, 10, []),
        (
            "postgres",
            1000,
            13,
            [("PIE-B1007", "public_artifact_byte_limit")],
        ),
        (
            "postgres",
            1000,
            64,
            [("PIE-B1007", "generated_structure_limit")],
        ),
        (
            "mysql",
            1000,
            64,
            [
                ("PIE-B1007", "generated_structure_limit"),
                ("PIE-B1003", "zero_physical_source_not_admitted_on_target"),
            ],
        ),
    ),
)
def test_the_static_values_bound_is_no_emission_guarantee(
    tmp_path: Path, target: str, rows: int, columns: int, blockers: list
) -> None:
    """PIE-S2365 admits 1,000 rows of 64 columns, but every cell counts against
    the compiler's generated-structure and public-document limits, which bind
    long before it: 1,000 rows of short cells emit with about a dozen columns."""
    _, document = _emit(tmp_path, target, _int_body(rows, columns))
    assert document["status"] == ("BLOCKED" if blockers else "VERIFIED")
    assert [
        (b["code"], b["subject"]["detail"]) for b in document.get("blockers", [])
    ] == blockers
