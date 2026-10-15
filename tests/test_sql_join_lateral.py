"""LATERAL JOIN of a let with capture lines: emission, requirements, verifiers.

Phase70 S12 (D70.03): a JOIN of the declaration body whose target is a let with
capture lines reads it LATERAL. The let is never a CTE: it is the derived
relation of that JOIN's right input, `<KIND> JOIN LATERAL (<let>) AS m<n>`,
whose correlated references name the JOIN's own left input alias and column.
Every capture-free block stays a top-level CTE and an INNER JOIN keeps its
authored ON (`on true` for a pure LATERAL); a LEFT JOIN (S13) keeps every left
row and null-extends the let's columns. Each artifact below is produced by the
installed emission path from an ordinary authored project.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_query_block_ir import ProjectIRCaptureStage
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_ast import SQLJoinQuery, inline_body
from pietto._project.project_sql_emission_joins import JoinBody
from pietto._project.project_sql_emission_results import RowResultBody
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
    verify_row_bytes,
    verify_row_query,
)
from pietto._project.project_sql_plan import ProjectSQLPlan, ProjectSQLPlanRefKind

TARGETS = ("postgres", "mysql")
LET = """query result:
    let m:
        capture lhs
        from rhs
        where rhs.key == lhs.key
        select:
            id
            v = rhs.key
    from lhs
"""
SHAPES = {
    "cross": LET
    + "    cross join m as m1:\n        from lhs\n"
    + "    select:\n        a = lhs.id\n        b = m1.v\n",
    "inner": LET
    + "    inner join m as m1:\n        from lhs\n        on true\n"
    + "    select:\n        a = lhs.id\n        b = m1.v\n",
    # The lateral JOIN reads the row of a LEFT JOIN (r is null-extended) and
    # is followed by another JOIN and a WHERE; its literals render between
    # the left relation and its ON.
    "chain": """query result:
    let m:
        capture lhs
        capture r
        from rhs
        where rhs.key == lhs.key and rhs.id > 5 and rhs.id != r.id
        select:
            id
            w = r.key
    from lhs
    left join rhs as r:
        from lhs
        on lhs.id == r.id
    inner join m as m1:
        from lhs
        on m1.id > 7
    cross join rhs as z:
        from lhs
    where m1.id > 9
    select:
        a = lhs.id
        b = m1.w
        c = z.id
""",
}
_PG_LATERAL = (
    'LATERAL (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1" FROM '
    '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
    'FROM "public"."phase66 rhs é" AS "s0" '
    'WHERE ("s0"."key value" = "m0"."key value")) AS "t1") AS "m1"'
)
_MY_LATERAL = (
    "LATERAL (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1` FROM "
    "(SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` "
    "FROM `phase66`.`phase66 rhs é` AS `s0` "
    "WHERE (`s0`.`key value` = `m0`.`key value`)) AS `t1`) AS `m1`"
)
_PG_HEAD = (
    'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS "c0", '
    '"m0"."key value" AS "c1", "m1"."c0" AS "c2", "m1"."c1" AS "c3" '
    'FROM "public"."phase66 lhs é" AS "m0" '
)
_MY_HEAD = (
    "WITH `p0` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `m0`.`order.id` AS `c0`, "
    "`m0`.`key value` AS `c1`, `m1`.`c0` AS `c2`, `m1`.`c1` AS `c3` "
    "FROM `phase66`.`phase66 lhs é` AS `m0` "
)
_PG_TAIL = ') SELECT "t0"."c0" AS "a", "t0"."c3" AS "b" FROM "p0" AS "t0"'
_MY_TAIL = ") SELECT `t0`.`c0` AS `a`, `t0`.`c3` AS `b` FROM `p0` AS `t0`"
SQL = {
    ("cross", "postgres"): _PG_HEAD + "CROSS JOIN " + _PG_LATERAL + _PG_TAIL,
    ("cross", "mysql"): _MY_HEAD + "CROSS JOIN " + _MY_LATERAL + _MY_TAIL,
    ("inner", "postgres"): _PG_HEAD
    + "INNER JOIN "
    + _PG_LATERAL
    + " ON CAST($1 AS pg_catalog.bool)"
    + _PG_TAIL,
    ("inner", "mysql"): _MY_HEAD
    + "INNER JOIN "
    + _MY_LATERAL
    + " ON CAST(? AS SIGNED)"
    + _MY_TAIL,
    ("chain", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."order.id" AS "c2", '
        '"m1"."key value" AS "c3" FROM "public"."phase66 lhs é" AS "m0" '
        'LEFT JOIN "public"."phase66 rhs é" AS "m1" '
        'ON ("m0"."order.id" = "m1"."order.id")), '
        '"p1" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "m2"."c0" AS "c0", '
        '"m2"."c1" AS "c1", "m2"."c2" AS "c2", "m2"."c3" AS "c3", '
        '"m3"."c0" AS "c4", "m3"."c1" AS "c5" FROM "p0" AS "m2" '
        'INNER JOIN LATERAL (SELECT "t1"."c0" AS "c0", "m2"."c3" AS "c1" FROM '
        '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        'FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE ((("s0"."key value" = "m2"."c1") AND '
        '("s0"."order.id" > CAST($1 AS pg_catalog.int8))) AND '
        '("s0"."order.id" <> "m2"."c2"))) AS "t1") AS "m3" '
        'ON ("m3"."c0" > CAST($2 AS pg_catalog.int8))), '
        '"p2" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7") AS '
        '(SELECT "m4"."c0" AS "c0", "m4"."c1" AS "c1", "m4"."c2" AS "c2", '
        '"m4"."c3" AS "c3", "m4"."c4" AS "c4", "m4"."c5" AS "c5", '
        '"m5"."order.id" AS "c6", "m5"."key value" AS "c7" FROM "p1" AS "m4" '
        'CROSS JOIN "public"."phase66 rhs é" AS "m5"), '
        '"p3" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7") AS '
        '(SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", "t0"."c2" AS "c2", '
        '"t0"."c3" AS "c3", "t0"."c4" AS "c4", "t0"."c5" AS "c5", '
        '"t0"."c6" AS "c6", "t0"."c7" AS "c7" FROM "p2" AS "t0" '
        'WHERE ("t0"."c4" > CAST($3 AS pg_catalog.int8))) '
        'SELECT "t3"."c0" AS "a", "t3"."c5" AS "b", "t3"."c6" AS "c" '
        'FROM "p3" AS "t3"'
    ),
    ("chain", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `m0`.`order.id` AS `c0`, "
        "`m0`.`key value` AS `c1`, `m1`.`order.id` AS `c2`, "
        "`m1`.`key value` AS `c3` FROM `phase66`.`phase66 lhs é` AS `m0` "
        "LEFT JOIN `phase66`.`phase66 rhs é` AS `m1` "
        "ON (`m0`.`order.id` = `m1`.`order.id`)), "
        "`p1` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `m2`.`c0` AS `c0`, "
        "`m2`.`c1` AS `c1`, `m2`.`c2` AS `c2`, `m2`.`c3` AS `c3`, "
        "`m3`.`c0` AS `c4`, `m3`.`c1` AS `c5` FROM `p0` AS `m2` "
        "INNER JOIN LATERAL (SELECT `t1`.`c0` AS `c0`, `m2`.`c3` AS `c1` FROM "
        "(SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` "
        "FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE (((`s0`.`key value` = `m2`.`c1`) AND "
        "(`s0`.`order.id` > CAST(? AS SIGNED))) AND "
        "(`s0`.`order.id` <> `m2`.`c2`))) AS `t1`) AS `m3` "
        "ON (`m3`.`c0` > CAST(? AS SIGNED))), "
        "`p2` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`) AS "
        "(SELECT `m4`.`c0` AS `c0`, `m4`.`c1` AS `c1`, `m4`.`c2` AS `c2`, "
        "`m4`.`c3` AS `c3`, `m4`.`c4` AS `c4`, `m4`.`c5` AS `c5`, "
        "`m5`.`order.id` AS `c6`, `m5`.`key value` AS `c7` FROM `p1` AS `m4` "
        "CROSS JOIN `phase66`.`phase66 rhs é` AS `m5`), "
        "`p3` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`) AS "
        "(SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1`, `t0`.`c2` AS `c2`, "
        "`t0`.`c3` AS `c3`, `t0`.`c4` AS `c4`, `t0`.`c5` AS `c5`, "
        "`t0`.`c6` AS `c6`, `t0`.`c7` AS `c7` FROM `p2` AS `t0` "
        "WHERE (`t0`.`c4` > CAST(? AS SIGNED))) "
        "SELECT `t3`.`c0` AS `a`, `t3`.`c5` AS `b`, `t3`.`c6` AS `c` "
        "FROM `p3` AS `t3`"
    ),
}
PRESERVED = {
    "cross": (),
    "inner": ("TRUE",),
    "chain": ("5", "7", "9"),
}


def _lateral(tmp_path: Path, target: str, shape: str, policy="bind_safe_literals"):
    item = probe.join_witness(target, SHAPES[shape], policy=policy)
    return probe.build_case(tmp_path, item["source"], item["contract"], item["policy"])


def _preserved(sql: str, target: str, shape: str) -> str:
    """The bind-safe statement with its placeholders preserved inline."""
    for index, value in enumerate(PRESERVED[shape], start=1):
        sql = (
            sql.replace(f"${index} ", f"{value} ", 1)
            if target == "postgres"
            else sql.replace("CAST(? ", f"CAST({value} ", 1)
        )
    return sql


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(SHAPES))
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_capturing_join_input_is_emitted_lateral(
    tmp_path: Path, target: str, shape: str, policy: str
) -> None:
    checked, outcome = _lateral(tmp_path, target, shape, policy)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    expected = SQL[shape, target]
    if policy == "preserve_literals":
        expected = _preserved(expected, target, shape)
    assert document["sql"] == expected
    # The capturing let is never a CTE: it is the JOIN's own derived relation.
    assert document["sql"].count("JOIN LATERAL (SELECT ") == 1
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    (capture,) = [c for c in plan.captures if c.use.clause.name == "lhs"]
    assert capture.edge.checkpoint.stage is ProjectIRCaptureStage.LATERAL
    (join,) = [j for j in plan.joins if j.ref is capture.block]
    right = next(i for i in plan.join_inputs if i.ref is capture.read)
    assert capture.read.kind is ProjectSQLPlanRefKind.JOIN_INPUT
    assert (right.join, right.ordinal, join.inputs[1]) == (join.ref, 1, right.ref)
    left = next(i for i in plan.join_inputs if i.ref is join.inputs[0])
    assert set(capture.ports) <= set(left.ports)
    assert outcome.artifact is not None
    kinds = [(r.kind, r.rule) for r in outcome.artifact.generated_requirements]
    references = sum(
        1 for e in plan.expressions if type(e) is row.ProjectSQLCapturedField
    )
    assert kinds.count(("lateral_input", "R11")) == 1
    assert kinds.count(("capture", "R11")) == references > 0
    # rhs is read only inside the lateral let and keeps its own scan.
    assert kinds.count(("qualified_scan", "R01")) == (4 if shape == "chain" else 2)
    if policy == "bind_safe_literals":
        assert [
            (use.ordinal, use.server_index) for use in outcome.artifact.parameter_uses
        ] == [(i, i + 1) for i in range(len(PRESERVED[shape]))]


def test_the_lateral_let_reads_its_null_extended_left_row(tmp_path: Path) -> None:
    checked, outcome = _lateral(tmp_path, "postgres", "chain")
    document = json.loads(serialize_project_sql_emission(outcome))
    # b is the captured r.key of a row the LEFT JOIN may null-extend.
    assert [(c["label"], c["nullable"]) for c in document["columns"]] == [
        ("a", False),
        ("b", True),
        ("c", False),
    ]
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    captured = {
        (e.expression.capture, e.expression.field): e.value_type.nullability.value
        for e in plan.expressions
        if type(e) is row.ProjectSQLCapturedField
    }
    assert captured == {
        ("lhs", "key"): "nullable",
        ("r", "id"): "nullable",
        ("r", "key"): "nullable",
    }


def _nodes(query, kind):
    """Every realized node of one class, inline let bodies included."""
    found, pending, seen = [], list(query.units), set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        if type(value) is kind:
            found.append(value)
        if type(value) is tuple:
            pending.extend(value)
        elif type(value).__module__.startswith("pietto._project.project_sql_emission"):
            if dataclasses.is_dataclass(value):
                pending.extend(
                    getattr(value, f.name) for f in dataclasses.fields(value)
                )
    return found


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation",
    (
        "right_alias",
        "other_left_column",
        "nullable_drift",
        "truncated_let",
        "named_producer",
    ),
)
def test_a_forged_lateral_input_fails_the_independent_verifier(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _lateral(tmp_path, target, "chain", "preserve_literals")
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLJoinQuery
    (unit,) = [
        u
        for u in query.units
        if type(u) is JoinBody and inline_body(u.inputs[1].producer)
    ]
    left, right = unit.inputs
    first, second, third = sorted(
        _nodes(query, rows.SQLCapturedReference),
        key=lambda value: value.original.ref.position,
    )
    # lhs.key and r.id in the let's WHERE, then r.key in its SELECT.
    assert [first.column.name, second.column.name, third.column.name] == [
        "c1",
        "c2",
        "c3",
    ]
    assert {first.scope, second.scope, third.scope} == {left.symbol}
    if mutation == "right_alias":
        # A valid alias of the same JOIN: its own right input.
        changes = [(second, "scope", right.symbol)]
    elif mutation == "other_left_column":
        changes = [(second, "column", third.column)]
    elif mutation == "nullable_drift":
        changes = [
            (
                second,
                "realization",
                dataclasses.replace(second.realization, nullable=False),
            )
        ]
    elif mutation == "truncated_let":
        changes = [(right, "producer", right.producer.scan.body)]
    else:
        # The capture-free left producer of the same statement.
        changes = [(right, "producer", left.producer)]
    originals = [(node, name, getattr(node, name)) for node, name, _ in changes]
    try:
        for node, name, value in changes:
            object.__setattr__(node, name, value)
        assert not verify_row_query(artifact.request, query)
    finally:
        for node, name, value in originals:
            object.__setattr__(node, name, value)
    assert verify_row_query(artifact.request, query)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("mutation", ("dropped_lateral", "correlation_to_right"))
def test_forged_lateral_bytes_fail_the_byte_verifier(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _lateral(tmp_path, target, "cross", "preserve_literals")
    artifact = outcome.artifact
    assert artifact is not None
    q = '"' if target == "postgres" else "`"
    sql = artifact.rendered.sql.decode()
    if mutation == "dropped_lateral":
        corrupted = sql.replace("CROSS JOIN LATERAL (", "CROSS JOIN (")
    else:
        corrupted = sql.replace(
            f"= {q}m0{q}.{q}key value{q})", f"= {q}m1{q}.{q}key value{q})"
        )
    assert corrupted != sql
    changed = dataclasses.replace(artifact.rendered, sql=corrupted.encode("utf-8"))
    assert not verify_row_bytes(artifact.ast, changed)
    assert not verify_project_sql_emission(
        dataclasses.replace(artifact, rendered=changed), artifact.request
    ).verified


@pytest.mark.parametrize("top_k", (False, True))
@pytest.mark.parametrize("target", TARGETS)
def test_private_observations_of_a_lateral_artifact_fail_closed(
    tmp_path: Path, target: str, top_k: bool
) -> None:
    from pietto._project.project_sql_emission_portable import (
        ObservationStatus,
        export_emission_observation,
    )
    from pietto._project.project_sql_plan_portable import (
        TransportError,
        build_project_sql_plan_portable,
    )

    checked, outcome = (_top_k if top_k else _lateral)(tmp_path, target, "cross")
    artifact = outcome.artifact
    assert artifact is not None
    assert (
        export_emission_observation(artifact, artifact.request).status
        is ObservationStatus.OUTSIDE_SCHEMA
    )
    with pytest.raises(TransportError):
        build_project_sql_plan_portable(checked)


# An entry query with parameters may also read a table that joins a let with
# capture lines LATERAL and reads another by exists: both inline lets'
# literals render in that table's CTEs first, then the parameter, which
# PostgreSQL reuses ($3) and MySQL repeats (?).
PARAMETER_OVER_LATERAL = """table t:
    let later:
        capture lhs
        from rhs
        where rhs.id > lhs.id and rhs.id > 6
        select:
            later_id = id
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > 5
        select:
            id
    from lhs
    cross join later as l:
        from lhs
    where exists matched
    select:
        id = lhs.id
        later_id = l.later_id
query result(cut: Int not null):
    from t
    where id > cut and later_id != cut
    select:
        a = id
"""
PARAMETER_OVER_LATERAL_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."c0" AS "c2" FROM "public"."phase66 lhs é" '
        'AS "m0" CROSS JOIN LATERAL (SELECT "t1"."c0" AS "c0" FROM (SELECT '
        '"s0"."order.id" AS "c0", "s0"."key value" AS "c1" FROM '
        '"public"."phase66 rhs é" AS "s0" WHERE (("s0"."order.id" > '
        '"m0"."order.id") AND ("s0"."order.id" > CAST($1 AS '
        'pg_catalog.int8)))) AS "t1") AS "m1"), "p1" ("c0", "c1", "c2") AS '
        '(SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", "t0"."c2" AS "c2" FROM '
        '"p0" AS "t0" WHERE EXISTS (SELECT 1 FROM (SELECT "t3"."c0" AS "c0" '
        'FROM (SELECT "s1"."order.id" AS "c0", "s1"."key value" AS "c1" FROM '
        '"public"."phase66 rhs é" AS "s1" WHERE (("s1"."key value" = '
        '"t0"."c1") AND ("s1"."order.id" > CAST($2 AS pg_catalog.int8)))) AS '
        '"t3") AS "e0")), "p2" ("c0", "c1") AS (SELECT "t5"."c0" AS "c0", '
        '"t5"."c2" AS "c1" FROM "p1" AS "t5"), "p3" ("c0", "c1") AS (SELECT '
        '"s4"."c0" AS "c0", "s4"."c1" AS "c1" FROM "p2" AS "s4" WHERE '
        '(("s4"."c0" > CAST($3 AS pg_catalog.int8)) AND ("s4"."c1" <> CAST($3 '
        'AS pg_catalog.int8)))) SELECT "t7"."c0" AS "a" FROM "p3" AS "t7"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`, `c2`) AS (SELECT `m0`.`order.id` AS `c0`, "
        "`m0`.`key value` AS `c1`, `m1`.`c0` AS `c2` FROM `phase66`.`phase66 lhs é` "
        "AS `m0` CROSS JOIN LATERAL (SELECT `t1`.`c0` AS `c0` FROM (SELECT "
        "`s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 rhs é` AS `s0` WHERE ((`s0`.`order.id` > "
        "`m0`.`order.id`) AND (`s0`.`order.id` > CAST(? AS SIGNED)))) AS "
        "`t1`) AS `m1`), `p1` (`c0`, `c1`, `c2`) AS (SELECT `t0`.`c0` AS "
        "`c0`, `t0`.`c1` AS `c1`, `t0`.`c2` AS `c2` FROM `p0` AS `t0` WHERE "
        "EXISTS (SELECT 1 FROM (SELECT `t3`.`c0` AS `c0` FROM (SELECT "
        "`s1`.`order.id` AS `c0`, `s1`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 rhs é` AS `s1` WHERE ((`s1`.`key value` = "
        "`t0`.`c1`) AND (`s1`.`order.id` > CAST(? AS SIGNED)))) AS `t3`) AS "
        "`e0`)), `p2` (`c0`, `c1`) AS (SELECT `t5`.`c0` AS `c0`, `t5`.`c2` AS "
        "`c1` FROM `p1` AS `t5`), `p3` (`c0`, `c1`) AS (SELECT `s4`.`c0` AS "
        "`c0`, `s4`.`c1` AS `c1` FROM `p2` AS `s4` WHERE ((`s4`.`c0` > CAST(? "
        "AS SIGNED)) AND (`s4`.`c1` <> CAST(? AS SIGNED)))) SELECT `t7`.`c0` "
        "AS `a` FROM `p3` AS `t7`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_an_entry_query_with_parameters_reads_a_table_with_a_lateral_let(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(
        target, PARAMETER_OVER_LATERAL, policy="bind_safe_literals"
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == PARAMETER_OVER_LATERAL_SQL[target]
    assert outcome.artifact is not None
    assert [
        (use.ordinal, use.server_index) for use in outcome.artifact.parameter_uses
    ] == [(0, 1), (1, 2), (2, 3), (3, 3 if target == "postgres" else 4)]


# Lets are reused and read forward (Phase70 S05): the LATERAL right input may
# read a chain of capture-free lets written after it, one of them also read by
# the declaration body, or a let grouped by a computed key (S05g). Those stay
# top-level CTEs; the lateral let's own literal renders before the ON and the
# body's own ones after it.
LATERAL_CHAINS = {
    "forward_chain": """query result:
    let m:
        capture lhs
        from others
        where others.key == lhs.key and others.id > 2
        select:
            id
    let others:
        from base
        where id > 1
        select:
            id
            key
    let base:
        from rhs
        select:
            id
            key
    from lhs
    cross join m as x:
        from lhs
    where exists base and lhs.id > 3
    select:
        a = lhs.id
        b = x.id
""",
    "computed_key": """query result:
    let m:
        capture lhs
        from buckets
        where buckets.n > lhs.key
        select:
            big
    let buckets:
        from rhs
        let:
            big = id > 1
        group by:
            big
        select:
            big
            n = count()
    from lhs
    inner join m as x:
        from lhs
        on true
    select:
        a = lhs.id
        b = x.big
""",
}
LATERAL_CHAIN_SQL = {
    ("forward_chain", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", "s0"."key value" '
        'AS "c1" FROM "public"."phase66 rhs é" AS "s0"), "p1" ("c0", "c1") AS '
        '(SELECT "s1"."c0" AS "c0", "s1"."c1" AS "c1" FROM "p0" AS "s1" WHERE '
        '("s1"."c0" > CAST($1 AS pg_catalog.int8))), "p2" ("c0", "c1") AS '
        '(SELECT "t2"."c0" AS "c0", "t2"."c1" AS "c1" FROM "p1" AS "t2"), '
        '"p3" ("c0", "c1", "c2") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."c0" AS "c2" FROM "public"."phase66 lhs é" '
        'AS "m0" CROSS JOIN LATERAL (SELECT "t4"."c0" AS "c0" FROM (SELECT '
        '"s2"."c0" AS "c0", "s2"."c1" AS "c1" FROM "p2" AS "s2" WHERE '
        '(("s2"."c1" = "m0"."key value") AND ("s2"."c0" > CAST($2 AS '
        'pg_catalog.int8)))) AS "t4") AS "m1"), "p4" ("c0", "c1", "c2") AS '
        '(SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", "t0"."c2" AS "c2" FROM '
        '"p3" AS "t0" WHERE (EXISTS (SELECT 1 FROM "p0" AS "e0") AND '
        '("t0"."c0" > CAST($3 AS pg_catalog.int8)))) SELECT "t6"."c0" AS "a", '
        '"t6"."c2" AS "b" FROM "p4" AS "t6"'
    ),
    ("forward_chain", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` "
        "AS `c1` FROM `phase66`.`phase66 rhs é` AS `s0`), `p1` (`c0`, `c1`) "
        "AS (SELECT `s1`.`c0` AS `c0`, `s1`.`c1` AS `c1` FROM `p0` AS `s1` "
        "WHERE (`s1`.`c0` > CAST(? AS SIGNED))), `p2` (`c0`, `c1`) AS (SELECT "
        "`t2`.`c0` AS `c0`, `t2`.`c1` AS `c1` FROM `p1` AS `t2`), `p3` (`c0`, "
        "`c1`, `c2`) AS (SELECT `m0`.`order.id` AS `c0`, `m0`.`key value` AS "
        "`c1`, `m1`.`c0` AS `c2` FROM `phase66`.`phase66 lhs é` AS `m0` CROSS "
        "JOIN LATERAL (SELECT `t4`.`c0` AS `c0` FROM (SELECT `s2`.`c0` AS "
        "`c0`, `s2`.`c1` AS `c1` FROM `p2` AS `s2` WHERE ((`s2`.`c1` = "
        "`m0`.`key value`) AND (`s2`.`c0` > CAST(? AS SIGNED)))) AS `t4`) AS "
        "`m1`), `p4` (`c0`, `c1`, `c2`) AS (SELECT `t0`.`c0` AS `c0`, "
        "`t0`.`c1` AS `c1`, `t0`.`c2` AS `c2` FROM `p3` AS `t0` WHERE (EXISTS "
        "(SELECT 1 FROM `p0` AS `e0`) AND (`t0`.`c0` > CAST(? AS SIGNED)))) "
        "SELECT `t6`.`c0` AS `a`, `t6`.`c2` AS `b` FROM `p4` AS `t6`"
    ),
    ("computed_key", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1", ("s0"."order.id" > CAST($1 AS '
        'pg_catalog.int8)) AS "c2" FROM "public"."phase66 rhs é" AS "s0"), '
        '"p1" ("c0", "c1") AS (SELECT "t1"."c2" AS "c0", COUNT(*) AS "c1" '
        'FROM "p0" AS "t1" GROUP BY "t1"."c2"), "p2" ("c0", "c1") AS (SELECT '
        '"t2"."c0" AS "c0", "t2"."c1" AS "c1" FROM "p1" AS "t2"), "p3" ("c0", '
        '"c1", "c2") AS (SELECT "m0"."order.id" AS "c0", "m0"."key value" AS '
        '"c1", "m1"."c0" AS "c2" FROM "public"."phase66 lhs é" AS "m0" INNER '
        'JOIN LATERAL (SELECT "t4"."c0" AS "c0" FROM (SELECT "s1"."c0" AS '
        '"c0", "s1"."c1" AS "c1" FROM "p2" AS "s1" WHERE ("s1"."c1" > '
        '"m0"."key value")) AS "t4") AS "m1" ON CAST($2 AS pg_catalog.bool)) '
        'SELECT "t0"."c0" AS "a", "t0"."c2" AS "b" FROM "p3" AS "t0"'
    ),
    ("computed_key", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`) AS (SELECT `s0`.`order.id` AS `c0`, "
        "`s0`.`key value` AS `c1`, (`s0`.`order.id` > CAST(? AS SIGNED)) AS "
        "`c2` FROM `phase66`.`phase66 rhs é` AS `s0`), `p1` (`c0`, `c1`) AS "
        "(SELECT `t1`.`c2` AS `c0`, COUNT(*) AS `c1` FROM `p0` AS `t1` GROUP "
        "BY `t1`.`c2`), `p2` (`c0`, `c1`) AS (SELECT `t2`.`c0` AS `c0`, "
        "`t2`.`c1` AS `c1` FROM `p1` AS `t2`), `p3` (`c0`, `c1`, `c2`) AS "
        "(SELECT `m0`.`order.id` AS `c0`, `m0`.`key value` AS `c1`, `m1`.`c0` "
        "AS `c2` FROM `phase66`.`phase66 lhs é` AS `m0` INNER JOIN LATERAL "
        "(SELECT `t4`.`c0` AS `c0` FROM (SELECT `s1`.`c0` AS `c0`, `s1`.`c1` "
        "AS `c1` FROM `p2` AS `s1` WHERE (`s1`.`c1` > `m0`.`key value`)) AS "
        "`t4`) AS `m1` ON CAST(? AS SIGNED)) SELECT `t0`.`c0` AS `a`, "
        "`t0`.`c2` AS `b` FROM `p3` AS `t0`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(LATERAL_CHAINS))
def test_a_lateral_let_reads_lets_that_read_lets(
    tmp_path: Path, target: str, shape: str
) -> None:
    item = probe.join_witness(
        target, LATERAL_CHAINS[shape], policy="bind_safe_literals"
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == LATERAL_CHAIN_SQL[shape, target]
    assert document["sql"].count(" JOIN LATERAL (SELECT ") == 1
    assert outcome.artifact is not None
    count = 3 if shape == "forward_chain" else 2
    assert [
        (use.ordinal, use.server_index) for use in outcome.artifact.parameter_uses
    ] == [(n, n + 1) for n in range(count)]


# A let joined LATERAL may read a relation whose columns are known only after
# completion (a typed VALUES body or a set, read through a let), like a let
# read by `exists`; that relation stays a top-level CTE.
LATERAL_OWN_FROM = {
    "own_from_values": """query result:
    let s:
        values(n: Int not null):
            1
            2
    let m:
        capture lhs
        from s
        where s.n <= lhs.id
        select:
            n
            k = lhs.key
    from lhs
    cross join m as x:
        from lhs
    select:
        a = lhs.id
        b = x.n
""",
    "own_from_set": """query result:
    let s:
        union all:
            from lhs
            from rhs
    let m:
        capture lhs
        from s
        where s.id == lhs.id
        select:
            id
    from lhs
    inner join m as x:
        from lhs
        on x.id > 3
    select:
        a = lhs.id
        b = x.id
""",
}
LATERAL_OWN_FROM_SQL = {
    ("own_from_values", "postgres"): (
        'WITH "p0" ("c0") AS (VALUES (CAST(1 AS pg_catalog.int8)), (CAST(2 '
        'AS pg_catalog.int8))), "p1" ("c0", "c1", "c2", "c3") AS (SELECT '
        '"m0"."order.id" AS "c0", "m0"."key value" AS "c1", "m1"."c0" AS '
        '"c2", "m1"."c1" AS "c3" FROM "public"."phase66 lhs é" AS "m0" '
        'CROSS JOIN LATERAL (SELECT "t1"."c0" AS "c0", "m0"."key value" AS '
        '"c1" FROM (SELECT "s0"."c0" AS "c0" FROM "p0" AS "s0" WHERE '
        '("s0"."c0" <= "m0"."order.id")) AS "t1") AS "m1") SELECT "t0"."c0" '
        'AS "a", "t0"."c2" AS "b" FROM "p1" AS "t0"'
    ),
    ("own_from_values", "mysql"): (
        "WITH `p0` (`c0`) AS (VALUES ROW(CAST(1 AS SIGNED)), ROW(CAST(2 AS "
        "SIGNED))), `p1` (`c0`, `c1`, `c2`, `c3`) AS (SELECT "
        "`m0`.`order.id` AS `c0`, `m0`.`key value` AS `c1`, `m1`.`c0` AS "
        "`c2`, `m1`.`c1` AS `c3` FROM `phase66`.`phase66 lhs é` AS `m0` "
        "CROSS JOIN LATERAL (SELECT `t1`.`c0` AS `c0`, `m0`.`key value` AS "
        "`c1` FROM (SELECT `s0`.`c0` AS `c0` FROM `p0` AS `s0` WHERE "
        "(`s0`.`c0` <= `m0`.`order.id`)) AS `t1`) AS `m1`) SELECT `t0`.`c0` "
        "AS `a`, `t0`.`c2` AS `b` FROM `p1` AS `t0`"
    ),
    ("own_from_set", "postgres"): (
        'WITH "p0" ("c0", "c1") AS ((SELECT "o0"."order.id" AS "c0", '
        '"o0"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "o0") '
        'UNION ALL (SELECT "o1"."order.id" AS "c0", "o1"."key value" AS '
        '"c1" FROM "public"."phase66 rhs é" AS "o1")), "p1" ("c0", "c1", '
        '"c2") AS (SELECT "m0"."order.id" AS "c0", "m0"."key value" AS '
        '"c1", "m1"."c0" AS "c2" FROM "public"."phase66 lhs é" AS "m0" '
        'INNER JOIN LATERAL (SELECT "t1"."c0" AS "c0" FROM (SELECT '
        '"s2"."c0" AS "c0", "s2"."c1" AS "c1" FROM "p0" AS "s2" WHERE '
        '("s2"."c0" = "m0"."order.id")) AS "t1") AS "m1" ON ("m1"."c0" > '
        'CAST($1 AS pg_catalog.int8))) SELECT "t0"."c0" AS "a", "t0"."c2" '
        'AS "b" FROM "p1" AS "t0"'
    ),
    ("own_from_set", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS ((SELECT `o0`.`order.id` AS `c0`, "
        "`o0`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `o0`) "
        "UNION ALL (SELECT `o1`.`order.id` AS `c0`, `o1`.`key value` AS "
        "`c1` FROM `phase66`.`phase66 rhs é` AS `o1`)), `p1` (`c0`, `c1`, "
        "`c2`) AS (SELECT `m0`.`order.id` AS `c0`, `m0`.`key value` AS "
        "`c1`, `m1`.`c0` AS `c2` FROM `phase66`.`phase66 lhs é` AS `m0` "
        "INNER JOIN LATERAL (SELECT `t1`.`c0` AS `c0` FROM (SELECT "
        "`s2`.`c0` AS `c0`, `s2`.`c1` AS `c1` FROM `p0` AS `s2` WHERE "
        "(`s2`.`c0` = `m0`.`order.id`)) AS `t1`) AS `m1` ON (`m1`.`c0` > "
        "CAST(? AS SIGNED))) SELECT `t0`.`c0` AS `a`, `t0`.`c2` AS `b` FROM "
        "`p1` AS `t0`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(LATERAL_OWN_FROM))
def test_a_lateral_let_reads_a_relation_known_after_completion(
    tmp_path: Path, target: str, shape: str
) -> None:
    item = probe.join_witness(
        target, LATERAL_OWN_FROM[shape], policy="bind_safe_literals"
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == LATERAL_OWN_FROM_SQL[shape, target]
    assert document["sql"].count(" JOIN LATERAL (SELECT ") == 1


# Phase70 S13: a LEFT JOIN reads the let LATERAL and keeps every left row: a
# left row without a pair gets one row whose let fields are NULL, its ON only
# chooses pairs, and every later reader sees the let's fields null-extended.
LEFT_SHAPES = {
    "left": LET
    + "    left join m as m1:\n        from lhs\n        on m1.id > 3\n"
    + "    select:\n        a = lhs.id\n        b = m1.v\n        c = m1.id\n",
    # A later EXISTS let captures the null-extended m1 and a WHERE tests it.
    "downstream": LET.replace(
        "    from lhs\n",
        "    let e:\n        capture m1\n        from rhs\n"
        "        where rhs.id == m1.id\n        select:\n            id\n"
        "    from lhs\n",
    )
    + "    left join m as m1:\n        from lhs\n        on true\n"
    + "    where exists e or m1.id is null\n"
    + "    select:\n        a = lhs.id\n        c = m1.id\n",
}
_PG_LEFT = (
    'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS "c0", '
    '"m0"."key value" AS "c1", "m1"."c0" AS "c2", "m1"."c1" AS "c3" '
    'FROM "public"."phase66 lhs é" AS "m0" LEFT JOIN ' + _PG_LATERAL
)
_MY_LEFT = (
    "WITH `p0` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `m0`.`order.id` AS `c0`, "
    "`m0`.`key value` AS `c1`, `m1`.`c0` AS `c2`, `m1`.`c1` AS `c3` "
    "FROM `phase66`.`phase66 lhs é` AS `m0` LEFT JOIN " + _MY_LATERAL
)
LEFT_SQL = {
    ("left", "postgres"): _PG_LEFT
    + ' ON ("m1"."c0" > CAST($1 AS pg_catalog.int8))) SELECT "t0"."c0" AS "a", '
    '"t0"."c3" AS "b", "t0"."c2" AS "c" FROM "p0" AS "t0"',
    ("left", "mysql"): _MY_LEFT
    + " ON (`m1`.`c0` > CAST(? AS SIGNED))) SELECT `t0`.`c0` AS `a`, "
    "`t0`.`c3` AS `b`, `t0`.`c2` AS `c` FROM `p0` AS `t0`",
    ("downstream", "postgres"): _PG_LEFT
    + ' ON CAST($1 AS pg_catalog.bool)), "p1" ("c0", "c1", "c2", "c3") AS '
    '(SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", "t0"."c2" AS "c2", '
    '"t0"."c3" AS "c3" FROM "p0" AS "t0" WHERE (EXISTS (SELECT 1 FROM '
    '(SELECT "t3"."c0" AS "c0" FROM (SELECT "s1"."order.id" AS "c0", '
    '"s1"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s1" '
    'WHERE ("s1"."order.id" = "t0"."c2")) AS "t3") AS "e0") OR '
    '("t0"."c2" IS NULL))) SELECT "t5"."c0" AS "a", "t5"."c2" AS "c" '
    'FROM "p1" AS "t5"',
    ("downstream", "mysql"): _MY_LEFT
    + " ON CAST(? AS SIGNED)), `p1` (`c0`, `c1`, `c2`, `c3`) AS "
    "(SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1`, `t0`.`c2` AS `c2`, "
    "`t0`.`c3` AS `c3` FROM `p0` AS `t0` WHERE (EXISTS (SELECT 1 FROM "
    "(SELECT `t3`.`c0` AS `c0` FROM (SELECT `s1`.`order.id` AS `c0`, "
    "`s1`.`key value` AS `c1` FROM `phase66`.`phase66 rhs é` AS `s1` "
    "WHERE (`s1`.`order.id` = `t0`.`c2`)) AS `t3`) AS `e0`) OR "
    "(`t0`.`c2` IS NULL))) SELECT `t5`.`c0` AS `a`, `t5`.`c2` AS `c` "
    "FROM `p1` AS `t5`",
}


def _left(tmp_path: Path, target: str, shape: str):
    item = probe.join_witness(target, LEFT_SHAPES[shape], policy="bind_safe_literals")
    return probe.build_case(tmp_path, item["source"], item["contract"], item["policy"])


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(LEFT_SHAPES))
def test_a_left_lateral_join_null_extends_the_lets_columns(
    tmp_path: Path, target: str, shape: str
) -> None:
    checked, outcome = _left(tmp_path, target, shape)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == LEFT_SQL[shape, target]
    assert document["sql"].count(" LEFT JOIN LATERAL (SELECT ") == 1
    # The let's id is NOT NULL, yet the LEFT JOIN's output may null-extend it.
    assert [(c["label"], c["nullable"]) for c in document["columns"]] == (
        [("a", False), ("b", True), ("c", True)]
        if shape == "left"
        else [("a", False), ("c", True)]
    )
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    (join,) = plan.joins
    assert join.kind.value == "left" and join.on is not None
    ports = {p.ref: p for p in plan.join_ports}
    right = next(i for i in plan.join_inputs if i.ref is join.inputs[1])
    nulled = [ports[ref].nulling for ref in join.outputs]
    assert [bool(n) for n in nulled] == [False] * 2 + [True] * len(right.ports)
    captured = {
        (e.expression.capture, e.expression.field): e.value_type.nullability.value
        for e in plan.expressions
        if type(e) is row.ProjectSQLCapturedField
    }
    expected = {("lhs", "key"): "nullable"}
    if shape == "downstream":
        # The EXISTS let reads m1 after its LEFT JOIN: null-extended.
        expected[("m1", "id")] = "nullable"
    assert captured == expected
    assert outcome.artifact is not None
    kinds = [(r.kind, r.rule) for r in outcome.artifact.generated_requirements]
    assert kinds.count(("lateral_input", "R11")) == 1
    assert kinds.count(("join", "R08")) == 1
    assert kinds.count(("null_extension", "R08")) == len(right.ports)


@pytest.mark.parametrize("target", TARGETS)
def test_a_forged_left_lateral_output_fails_the_independent_verifier(
    tmp_path: Path, target: str
) -> None:
    _, outcome = _left(tmp_path, target, "left")
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLJoinQuery
    (unit,) = [u for u in query.units if type(u) is JoinBody]
    column = unit.columns[2]
    assert column.column.realization.nullable is True
    original = column.column
    # The let's NOT NULL id claimed non-null after the LEFT JOIN.
    object.__setattr__(
        column,
        "column",
        dataclasses.replace(
            original,
            realization=dataclasses.replace(original.realization, nullable=False),
        ),
    )
    try:
        assert not verify_row_query(artifact.request, query)
    finally:
        object.__setattr__(column, "column", original)
    assert verify_row_query(artifact.request, query)


# Phase70 S12: a let joined LATERAL may end in ORDER BY and LIMIT, a top-k per
# left row. They stay inside that JOIN's derived relation as one more unnamed
# body over the let's projection, so every left row, duplicates included, gets
# its own first rows; an ORDER BY input the let does not select is carried as a
# hidden column of the projection, as for any result body.
TOP_K = LET.replace(
    "            v = rhs.key\n",
    "            v = rhs.key\n        order by:\n            key desc\n            id\n"
    "        limit 2\n",
)
TOP_K_SHAPES = {
    "cross": TOP_K
    + "    cross join m as m1:\n        from lhs\n"
    + "    select:\n        a = lhs.id\n        b = m1.v\n",
    "inner": TOP_K
    + "    inner join m as m1:\n        from lhs\n        on true\n"
    + "    select:\n        a = lhs.id\n        b = m1.v\n",
    "left": TOP_K
    + "    left join m as m1:\n        from lhs\n        on m1.id > 3\n"
    + "    select:\n        a = lhs.id\n        b = m1.v\n        c = m1.id\n",
}
TOP_K_PRESERVED = {"cross": (), "inner": ("TRUE",), "left": ("3",)}
_PG_TOP_K = (
    'LATERAL (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1" FROM '
    '(SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c1" AS "c2", '
    '"t1"."c0" AS "c3" FROM (SELECT "s0"."order.id" AS "c0", '
    '"s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0" '
    'WHERE ("s0"."key value" = "m0"."key value")) AS "t1") AS "t0" '
    'ORDER BY "t0"."c2" DESC, "t0"."c3" ASC LIMIT 2) AS "m1"'
)
_MY_TOP_K = (
    "LATERAL (SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1` FROM "
    "(SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1`, `t1`.`c1` AS `c2`, "
    "`t1`.`c0` AS `c3` FROM (SELECT `s0`.`order.id` AS `c0`, "
    "`s0`.`key value` AS `c1` FROM `phase66`.`phase66 rhs é` AS `s0` "
    "WHERE (`s0`.`key value` = `m0`.`key value`)) AS `t1`) AS `t0` "
    "ORDER BY `t0`.`c2` DESC, `t0`.`c3` ASC LIMIT 2) AS `m1`"
)
TOP_K_SQL = {
    ("cross", "postgres"): _PG_HEAD + "CROSS JOIN " + _PG_TOP_K + _PG_TAIL,
    ("cross", "mysql"): _MY_HEAD + "CROSS JOIN " + _MY_TOP_K + _MY_TAIL,
    ("inner", "postgres"): _PG_HEAD
    + "INNER JOIN "
    + _PG_TOP_K
    + " ON CAST($1 AS pg_catalog.bool)"
    + _PG_TAIL,
    ("inner", "mysql"): _MY_HEAD
    + "INNER JOIN "
    + _MY_TOP_K
    + " ON CAST(? AS SIGNED)"
    + _MY_TAIL,
    ("left", "postgres"): _PG_HEAD
    + "LEFT JOIN "
    + _PG_TOP_K
    + ' ON ("m1"."c0" > CAST($1 AS pg_catalog.int8))) SELECT "t0"."c0" AS "a", '
    '"t0"."c3" AS "b", "t0"."c2" AS "c" FROM "p0" AS "t0"',
    ("left", "mysql"): _MY_HEAD
    + "LEFT JOIN "
    + _MY_TOP_K
    + " ON (`m1`.`c0` > CAST(? AS SIGNED))) SELECT `t0`.`c0` AS `a`, "
    "`t0`.`c3` AS `b`, `t0`.`c2` AS `c` FROM `p0` AS `t0`",
}


def _top_k(tmp_path: Path, target: str, kind: str, policy="bind_safe_literals"):
    item = probe.join_witness(target, TOP_K_SHAPES[kind], policy=policy)
    return probe.build_case(tmp_path, item["source"], item["contract"], item["policy"])


def _top_k_result(query):
    (unit,) = [
        u
        for u in query.units
        if type(u) is JoinBody and inline_body(u.inputs[1].producer)
    ]
    result = unit.inputs[1].producer
    assert type(result) is RowResultBody
    return unit, result


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", sorted(TOP_K_SHAPES))
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_lateral_lets_order_and_limit_stay_in_its_derived_relation(
    tmp_path: Path, target: str, kind: str, policy: str
) -> None:
    checked, outcome = _top_k(tmp_path, target, kind, policy)
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert document["status"] == "VERIFIED", document
    expected = TOP_K_SQL[kind, target]
    for index, value in enumerate(TOP_K_PRESERVED[kind], start=1):
        if policy == "preserve_literals":
            expected = (
                expected.replace(f"${index} ", f"{value} ", 1)
                if target == "postgres"
                else expected.replace("CAST(? ", f"CAST({value} ", 1)
            )
    assert document["sql"] == expected
    assert document["sql"].count("JOIN LATERAL (SELECT ") == 1
    assert document["sql"].count(" LIMIT 2) AS ") == 1
    assert probe.decode_public(raw) == document
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    (capture,) = plan.captures
    boundaries = [b for b in plan.result_boundaries if b.definition is capture.inner]
    assert [b.kind.value for b in boundaries] == ["relation_ordering", "limit"]
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLJoinQuery
    _, result = _top_k_result(query)
    # The let's third body (filter, projection, result), unnamed and not final.
    assert (result.index, result.final, result.symbol, result.cte_columns) == (
        2,
        False,
        None,
        (),
    )
    assert inline_body(result.scan.body) and result.limit is not None
    assert result.limit.value == 2
    kinds = [(r.kind, r.rule) for r in artifact.generated_requirements]
    assert kinds.count(("lateral_input", "R11")) == 1
    # The projection reads the let's filter body and the result body reads
    # the projection, each inline, never a CTE.
    assert kinds.count(("inline_stage_use", "R11")) == 2
    assert ("stage_use", result.scan.body.block.ref) not in [
        (r.kind, r.subject) for r in artifact.generated_requirements
    ]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation",
    ("limit_value", "order_direction", "named_result", "dropped_result"),
)
def test_a_forged_lateral_top_k_fails_the_independent_verifier(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _top_k(tmp_path, target, "left")
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLJoinQuery
    unit, result = _top_k_result(query)
    right = unit.inputs[1]
    assert result.limit is not None and result.order is not None
    first = result.order.items[0]
    if mutation == "limit_value":
        changes = [(result.limit, "value", 3)]
    elif mutation == "order_direction":
        changes = [(first, "direction", "ASC")]
    elif mutation == "named_result":
        # The name an ordinary result body of the same position would take.
        changes = [(result, "symbol", query.units[0].symbol)]
    else:
        # ORDER BY and LIMIT dropped: the JOIN reads the let's projection.
        changes = [(right, "producer", result.scan.body)]
    originals = [(node, name, getattr(node, name)) for node, name, _ in changes]
    try:
        for node, name, value in changes:
            object.__setattr__(node, name, value)
        assert not verify_row_query(artifact.request, query)
    finally:
        for node, name, value in originals:
            object.__setattr__(node, name, value)
    assert verify_row_query(artifact.request, query)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("mutation", ("dropped_limit", "flipped_direction"))
def test_forged_lateral_top_k_bytes_fail_the_byte_verifier(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _top_k(tmp_path, target, "cross")
    artifact = outcome.artifact
    assert artifact is not None
    sql = artifact.rendered.sql.decode()
    corrupted = (
        sql.replace(" LIMIT 2) AS ", ") AS ")
        if mutation == "dropped_limit"
        else sql.replace(" DESC, ", " ASC, ")
    )
    assert corrupted != sql
    changed = dataclasses.replace(artifact.rendered, sql=corrupted.encode("utf-8"))
    assert not verify_row_bytes(artifact.ast, changed)
    assert not verify_project_sql_emission(
        dataclasses.replace(artifact, rendered=changed), artifact.request
    ).verified


@pytest.mark.parametrize("target", TARGETS)
def test_a_computed_lateral_order_key_keeps_its_result_body_refusal(
    tmp_path: Path, target: str
) -> None:
    # A computed ORDER BY key needs an established port inside a LATERAL let
    # as in any result body: the emission refuses it with no artifact.
    source = TOP_K_SHAPES["cross"].replace(
        "            key desc\n", "            id + 1\n"
    )
    item = probe.join_witness(target, source, policy="bind_safe_literals")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert (document["status"], document["diagnostics"]) == ("BLOCKED", [])
    assert outcome.artifact is None
    assert [
        (
            b["code"],
            b["reason"],
            b["subject"]["detail"],
            b["location"]["line"],
            b["location"]["column"],
        )
        for b in document["blockers"]
    ] == [
        (
            "PIE-B1003",
            "UNSUPPORTED_RULE",
            "order_expression_requires_established_port",
            15,
            13,
        )
    ]


# Phase70 S11 x S12/S13: a let joined LATERAL reads the entry query's header
# like any other let of it, also when it ends in ORDER BY and LIMIT (a top-k
# per left row) and in the ON of a LEFT join. Each read renders where it is
# written, in rendering order with the bind-safe slots: PostgreSQL reuses one
# `$n` per parameter, MySQL writes one `?` per read.
HEADER_IN_LATERAL = {
    "top_k_cross": """query result(cut: Int not null, hi: Int nullable):
    let m:
        capture lhs
        from rhs
        where rhs.id > lhs.id and rhs.id < hi and rhs.id != 100
        select:
            id
        order by:
            id desc
        limit 2
    from lhs
    cross join m as x:
        from lhs
    where lhs.id > cut
    select:
        a = lhs.id
        b = x.id
""",
    "left_on": """query result(cut: Int not null, hi: Int nullable):
    let m:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id < hi
        select:
            id
    from lhs
    left join m as x:
        from lhs
        on x.id > cut and x.id != 100
    where lhs.id > cut
    select:
        a = lhs.id
        b = x.id
""",
}
HEADER_IN_LATERAL_SQL = {
    ("top_k_cross", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."c0" AS "c2" FROM "public"."phase66 lhs '
        'é" AS "m0" CROSS JOIN LATERAL (SELECT "t0"."c0" AS "c0" FROM (SELECT '
        '"t1"."c0" AS "c0", "t1"."c0" AS "c1" FROM (SELECT "s0"."order.id" AS '
        '"c0", "s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE ((("s0"."order.id" > "m0"."order.id") AND ("s0"."order.id" < '
        'CAST($1 AS pg_catalog.int8))) AND ("s0"."order.id" <> CAST($2 AS '
        'pg_catalog.int8)))) AS "t1") AS "t0" ORDER BY "t0"."c1" DESC LIMIT 2) AS '
        '"m1"), "p1" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS "c0", "t0"."c1" '
        'AS "c1", "t0"."c2" AS "c2" FROM "p0" AS "t0" WHERE ("t0"."c0" > CAST($3 '
        'AS pg_catalog.int8))) SELECT "t3"."c0" AS "a", "t3"."c2" AS "b" FROM '
        '"p1" AS "t3"'
    ),
    ("top_k_cross", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`) AS (SELECT `m0`.`order.id` AS `c0`, "
        "`m0`.`key value` AS `c1`, `m1`.`c0` AS `c2` FROM `phase66`.`phase66 lhs "
        "é` AS `m0` CROSS JOIN LATERAL (SELECT `t0`.`c0` AS `c0` FROM (SELECT "
        "`t1`.`c0` AS `c0`, `t1`.`c0` AS `c1` FROM (SELECT `s0`.`order.id` AS "
        "`c0`, `s0`.`key value` AS `c1` FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE (((`s0`.`order.id` > `m0`.`order.id`) AND (`s0`.`order.id` < "
        "CAST(? AS SIGNED))) AND (`s0`.`order.id` <> CAST(? AS SIGNED)))) AS "
        "`t1`) AS `t0` ORDER BY `t0`.`c1` DESC LIMIT 2) AS `m1`), `p1` (`c0`, "
        "`c1`, `c2`) AS (SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1`, `t0`.`c2` "
        "AS `c2` FROM `p0` AS `t0` WHERE (`t0`.`c0` > CAST(? AS SIGNED))) SELECT "
        "`t3`.`c0` AS `a`, `t3`.`c2` AS `b` FROM `p1` AS `t3`"
    ),
    ("left_on", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."c0" AS "c2" FROM "public"."phase66 lhs '
        'é" AS "m0" LEFT JOIN LATERAL (SELECT "t1"."c0" AS "c0" FROM (SELECT '
        '"s0"."order.id" AS "c0", "s0"."key value" AS "c1" FROM "public"."phase66 '
        'rhs é" AS "s0" WHERE (("s0"."key value" = "m0"."key value") AND '
        '("s0"."order.id" < CAST($1 AS pg_catalog.int8)))) AS "t1") AS "m1" ON '
        '(("m1"."c0" > CAST($2 AS pg_catalog.int8)) AND ("m1"."c0" <> CAST($3 AS '
        'pg_catalog.int8)))), "p1" ("c0", "c1", "c2") AS (SELECT "t0"."c0" AS '
        '"c0", "t0"."c1" AS "c1", "t0"."c2" AS "c2" FROM "p0" AS "t0" WHERE '
        '("t0"."c0" > CAST($2 AS pg_catalog.int8))) SELECT "t3"."c0" AS "a", '
        '"t3"."c2" AS "b" FROM "p1" AS "t3"'
    ),
    ("left_on", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`) AS (SELECT `m0`.`order.id` AS `c0`, "
        "`m0`.`key value` AS `c1`, `m1`.`c0` AS `c2` FROM `phase66`.`phase66 lhs "
        "é` AS `m0` LEFT JOIN LATERAL (SELECT `t1`.`c0` AS `c0` FROM (SELECT "
        "`s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 rhs é` AS `s0` WHERE ((`s0`.`key value` = `m0`.`key "
        "value`) AND (`s0`.`order.id` < CAST(? AS SIGNED)))) AS `t1`) AS `m1` ON "
        "((`m1`.`c0` > CAST(? AS SIGNED)) AND (`m1`.`c0` <> CAST(? AS SIGNED)))), "
        "`p1` (`c0`, `c1`, `c2`) AS (SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1`, "
        "`t0`.`c2` AS `c2` FROM `p0` AS `t0` WHERE (`t0`.`c0` > CAST(? AS "
        "SIGNED))) SELECT `t3`.`c0` AS `a`, `t3`.`c2` AS `b` FROM `p1` AS `t3`"
    ),
}
# (owner kind, owner ordinal, PostgreSQL index, MySQL index) per occurrence.
HEADER_IN_LATERAL_USES = {
    "top_k_cross": [("parameter", 1, 1, 1), ("slot", 0, 2, 2), ("parameter", 0, 3, 3)],
    "left_on": [
        ("parameter", 1, 1, 1),
        ("parameter", 0, 2, 2),
        ("slot", 0, 3, 3),
        ("parameter", 0, 2, 4),
    ],
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(HEADER_IN_LATERAL))
def test_a_lateral_let_reads_the_entry_query_header(
    tmp_path: Path, target: str, shape: str
) -> None:
    item = probe.join_witness(
        target, HEADER_IN_LATERAL[shape], policy="bind_safe_literals"
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == HEADER_IN_LATERAL_SQL[shape, target]
    uses = HEADER_IN_LATERAL_USES[shape]
    index = TARGETS.index(target)
    assert [
        (u["owner"]["kind"], u["owner"][u["owner"]["kind"]], u["server_index"])
        for u in document["parameter_uses"]
    ] == [(kind, owner, indices[index]) for kind, owner, *indices in uses]
    assert outcome.artifact is not None
    assert verify_project_sql_emission(
        outcome.artifact, outcome.artifact.request
    ).verified
    arguments = probe.decoded_arguments(probe.decode_public(raw), {"cut": 3, "hi": 7})
    assert (
        arguments
        == {
            ("top_k_cross", "postgres"): (7, 100, 3),
            ("top_k_cross", "mysql"): (7, 100, 3),
            ("left_on", "postgres"): (7, 3, 100),
            ("left_on", "mysql"): (7, 3, 100, 3),
        }[shape, target]
    )


# Phase70 S16: the body that joins a capturing let LEFT LATERAL groups by the
# let's null-extended column: every left row without a later row joins the one
# NULL group, and the let stays that JOIN's derived relation, never a CTE.
GROUPED_LEFT = """query result:
    let later:
        capture lhs
        from rhs
        where rhs.id > lhs.id
        select:
            later_id = id
    from lhs
    left join later as l:
        from lhs
        on true
    group by:
        l.later_id
    select:
        later_id = l.later_id
        n = count()
"""
GROUPED_LEFT_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."c0" AS "c2" FROM "public"."phase66 lhs é" '
        'AS "m0" LEFT JOIN LATERAL (SELECT "t1"."c0" AS "c0" FROM (SELECT '
        '"s0"."order.id" AS "c0", "s0"."key value" AS "c1" FROM '
        '"public"."phase66 rhs é" AS "s0" WHERE ("s0"."order.id" > '
        '"m0"."order.id")) AS "t1") AS "m1" ON CAST(TRUE AS pg_catalog.bool)), '
        '"p1" ("c0", "c1") AS (SELECT "t0"."c2" AS "c0", COUNT(*) AS "c1" FROM '
        '"p0" AS "t0" GROUP BY "t0"."c2") SELECT "t3"."c0" AS "later_id", '
        '"t3"."c1" AS "n" FROM "p1" AS "t3"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`, `c2`) AS (SELECT `m0`.`order.id` AS `c0`, "
        "`m0`.`key value` AS `c1`, `m1`.`c0` AS `c2` FROM `phase66`.`phase66 lhs é` "
        "AS `m0` LEFT JOIN LATERAL (SELECT `t1`.`c0` AS `c0` FROM (SELECT "
        "`s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 rhs é` AS `s0` WHERE (`s0`.`order.id` > "
        "`m0`.`order.id`)) AS `t1`) AS `m1` ON CAST(TRUE AS SIGNED)), "
        "`p1` (`c0`, `c1`) AS (SELECT `t0`.`c2` AS `c0`, COUNT(*) AS `c1` FROM "
        "`p0` AS `t0` GROUP BY `t0`.`c2`) SELECT `t3`.`c0` AS `later_id`, "
        "`t3`.`c1` AS `n` FROM `p1` AS `t3`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_the_outer_body_groups_by_a_null_extended_lateral_column(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(target, GROUPED_LEFT)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == GROUPED_LEFT_SQL[target]
    assert [(c["label"], c["nullable"]) for c in document["columns"]] == [
        ("later_id", True),
        ("n", False),
    ]
    assert probe.decode_public(raw) == document
    with pytest.raises(ValueError):
        probe.decode_public(raw.replace(b"LATERAL (", b"NOTLATER", 1))


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(("shape", "forged"), (("inner", "RIGHT"), ("left", "FULL")))
def test_lateral_is_rejected_for_other_native_join_kinds(
    tmp_path: Path, target: str, shape: str, forged: str
) -> None:
    _, outcome = _top_k(tmp_path, target, shape)
    raw = serialize_project_sql_emission(outcome)
    original = f" {shape.upper()} JOIN LATERAL ".encode()
    replacement = f" {forged} JOIN LATERAL ".encode()
    assert len(original) == len(replacement) and raw.count(original) == 1
    with pytest.raises(ValueError):
        probe.decode_public(raw.replace(original, replacement, 1))


@pytest.mark.parametrize("target", TARGETS)
def test_lateral_capture_terminal_alias_cannot_be_substituted_at_the_same_length(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(target, GROUPED_LEFT)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    quote = b'"' if target == "postgres" else b"`"
    original = (
        " > "
        + quote.decode()
        + "m0"
        + quote.decode()
        + "."
        + quote.decode()
        + "order.id"
        + quote.decode()
    )
    replacement = (
        " > "
        + quote.decode()
        + "m1"
        + quote.decode()
        + "."
        + quote.decode()
        + "order.id"
        + quote.decode()
    )
    assert len(original) == len(replacement) and document["sql"].count(original) == 1
    with pytest.raises(ValueError):
        probe.decode_public(
            probe.encoded(
                {**document, "sql": document["sql"].replace(original, replacement, 1)}
            )
        )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("rule", ("R19", "R21"))
def test_lateral_top_k_order_and_limit_evidence_is_exact(
    tmp_path: Path, target: str, rule: str
) -> None:
    _, outcome = _top_k(tmp_path, target, "left")
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert probe.decode_public(raw) == document
    checks = [
        requirement
        for requirement in document["requirements"]
        if requirement["denominator"] == "generated" and requirement["rule"] == rule
    ]
    assert checks and all(requirement["evidence"] == [] for requirement in checks)
    checks[0]["evidence"] = [["unmapped_proposition"]]
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(document))
