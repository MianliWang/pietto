"""Closed scalar reads: ``scalar r.c`` reads one output column of one whole block.

A scalar read is an expression block use of its owner, never one of its FROM,
JOIN or set inputs. It is emitted as ``(SELECT e.c FROM p AS e)`` over the read
block's top-level CTE (or its qualified source), reads NULL when that block has
no row, and leaves more than one row to the database's own runtime error; no
LIMIT is added.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_portable as portable
from pietto._project import project_sql_emission_pure_boundary as pure
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_postgres_source_assurance import qualification_roots
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_ast import SQLRowQuery
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project import project_sql_plan_expressions as row

TARGETS = ("postgres", "mysql")
CANONICAL = """query result:
    let picked:
        from rhs
        where id > 0
        select:
            rid = id
    let counted:
        from rhs
        select:
            n = count()
    from lhs
    where id == scalar picked.rid
    select:
        a = lhs.id
        n = scalar counted.n
        k = scalar rhs.key
"""
SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE ("s0"."order.id" > CAST(0 AS pg_catalog.int8))), '
        '"p1" ("c0") AS (SELECT "t1"."c0" AS "c0" FROM "p0" AS "t1"), '
        '"p2" ("c0") AS (SELECT COUNT(*) AS "c0" FROM "public"."phase66 rhs é" '
        'AS "s1"), "p3" ("c0") AS (SELECT "t3"."c0" AS "c0" FROM "p2" AS "t3"), '
        '"p4" ("c0", "c1") AS (SELECT "s2"."order.id" AS "c0", '
        '"s2"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s2" '
        'WHERE ("s2"."order.id" = (SELECT "e0"."c0" FROM "p1" AS "e0"))) '
        'SELECT "t5"."c0" AS "a", (SELECT "e1"."c0" FROM "p3" AS "e1") AS "n", '
        '(SELECT "e2"."key value" FROM "public"."phase66 rhs é" AS "e2") AS "k" '
        'FROM "p4" AS "t5"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`order.id` AS `c0`, "
        "`s0`.`key value` AS `c1` FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE (`s0`.`order.id` > CAST(0 AS SIGNED))), "
        "`p1` (`c0`) AS (SELECT `t1`.`c0` AS `c0` FROM `p0` AS `t1`), "
        "`p2` (`c0`) AS (SELECT COUNT(*) AS `c0` FROM `phase66`.`phase66 rhs é` "
        "AS `s1`), `p3` (`c0`) AS (SELECT `t3`.`c0` AS `c0` FROM `p2` AS `t3`), "
        "`p4` (`c0`, `c1`) AS (SELECT `s2`.`order.id` AS `c0`, "
        "`s2`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s2` "
        "WHERE (`s2`.`order.id` = (SELECT `e0`.`c0` FROM `p1` AS `e0`))) "
        "SELECT `t5`.`c0` AS `a`, (SELECT `e1`.`c0` FROM `p3` AS `e1`) AS `n`, "
        "(SELECT `e2`.`key value` FROM `phase66`.`phase66 rhs é` AS `e2`) AS `k` "
        "FROM `p4` AS `t5`"
    ),
}
HIDDEN = """query result:
    let picked:
        from rhs
        select:
            rid = id
    from lhs
    where id == scalar picked.rid
    select:
        a = lhs.id
"""
# Each consumer and read-block shape: a JOIN consumer, a consumer completed
# over a set input, a grouped consumer's WHERE, and grouped/DISTINCT/ordered
# and limited/global-aggregate read blocks.
SHAPES = {
    # A typed VALUES let and a zero-row VALUES query are typed by their header.
    "values": """query none:
    values(rid: Int not null)
query result:
    let seed:
        values(rid: Int not null, t: Text nullable):
            1, "a"
            2, null
    from lhs
    where lhs.id == scalar seed.rid
    select:
        a = lhs.id
        e = scalar seed.t
        z = scalar none.rid
""",
    "join_consumer": """query result:
    let picked:
        from rhs
        select:
            rid = id
    from lhs
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    where lhs.id == scalar picked.rid
    select:
        a = lhs.id
        k = scalar rhs.key
""",
    "set_input_consumer": """query both:
    union all:
        from lhs
        from rhs
query result:
    let picked:
        from rhs
        select:
            rid = id
    from both
    where id == scalar picked.rid
    select:
        a = id
        k = scalar rhs.key
""",
    "grouped_consumer_where": """query result:
    let picked:
        from rhs
        select:
            rid = id
    from lhs
    where id == scalar picked.rid
    group by:
        id
    select:
        id
        n = count()
""",
    "read_blocks": """query grouped:
    from rhs
    group by:
        id
    select:
        id
        n = count()
    satisfying:
        n > 1
query distinct_keys:
    from rhs
    select distinct:
        key
query top:
    from rhs
    select:
        id
    order by:
        id desc
    limit 1
query result:
    let total:
        from rhs
        select:
            m = max(id)
    from lhs
    where id == scalar top.id and key == scalar distinct_keys.key
    select:
        a = lhs.id
        g = scalar grouped.n
        m = scalar total.m
""",
}


def _emit(tmp_path: Path, target: str, body: str, *, contract=None):
    item = probe.join_witness(target, body)
    return probe.build_case(
        tmp_path, item["source"], contract or item["contract"], item["policy"]
    )


def _observed(outcome) -> None:
    artifact = outcome.artifact
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds


@pytest.mark.parametrize("target", TARGETS)
def test_scalar_reads_emit_one_column_subqueries_without_a_limit(
    tmp_path: Path, target: str
) -> None:
    _, outcome = _emit(tmp_path, target, CANONICAL)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == SQL[target]
    assert " LIMIT " not in document["sql"]
    # No row reads NULL: every scalar read is nullable, even of a non-null
    # COUNT; the read keeps its column's physical carrier.
    columns = [
        (c["label"], c["logical_type"]["name"], c["nullable"])
        for c in document["columns"]
    ]
    assert columns == [("a", "Int", False), ("n", "Int", True), ("k", "Int", True)]
    representation = document["columns"][1]["representation"]
    assert representation["nullable"] is True
    assert representation["domain"]["min"] == "0"
    assert [r["rule"] for r in document["requirements"] if r["kind"] == "scalar"] == [
        "R11",
        "R11",
        "R11",
    ]
    _observed(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_source_read_only_through_a_scalar_read_is_a_statement_source(
    tmp_path: Path, target: str
) -> None:
    checked, outcome = _emit(tmp_path, target, HIDDEN)
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    assert [s.declaration.name for s in plan.sources] == ["lhs", "rhs"]
    (read,) = plan.expression_block_uses
    use = read.edge.use
    assert (use.consumer.definition.name, use.target.definition.name) == (
        "result",
        "picked",
    )
    assert read.edge.column == 0 and use.evidence.read.position.value == "where"
    (leaf,) = (e for e in plan.expressions if type(e) is row.ProjectSQLRelationScalar)
    assert leaf.use is read.ref
    assert (leaf.value_type.resolved_type.name, leaf.value_type.nullability.value) == (
        "Int",
        "nullable",
    )
    # The read never occupies one of the consumer's relation-input slots.
    definitions = {d.ref: d for d in plan.bindings.definitions}
    assert [
        definitions[u.producer].entry.owner.definition.name
        for u in plan.input_uses
        if u.consumer is read.consumer
    ] == ["lhs"]
    request = outcome.artifact.request
    assert [s.name for s in request.sources] == ["phase66 lhs é", "phase66 rhs é"]
    assert qualification_roots(request.sources, ()) == tuple(
        (s.namespace, s.name) for s in request.sources
    )
    # The read is realized from the read block's own column, made nullable.
    query = outcome.artifact.ast
    assert type(query) is SQLRowQuery
    (value,) = (
        node
        for body in query.bodies
        if body.predicate is not None
        for node in rows.value_nodes(body.predicate.value)
        if type(node) is rows.SQLBlockRead
    )
    assert (value.kind, value.column, value.realization.nullable) == (
        "scalar",
        0,
        True,
    )


@pytest.mark.parametrize("target", TARGETS)
def test_an_inner_source_needs_its_contract_mapping(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(target, HIDDEN)
    contract = json.loads(item["contract"])
    contract["sources"] = contract["sources"][:1]
    _, outcome = _emit(tmp_path, target, HIDDEN, contract=json.dumps(contract))
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "BLOCKED"
    assert {(b["code"], b["subject"]["detail"]) for b in document["blockers"]} == {
        ("PIE-B1001", "source_mapping_missing")
    }


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_scalar_reads_of_every_consumer_and_read_block_shape_verify(
    tmp_path: Path, target: str, shape: str
) -> None:
    checked, outcome = _emit(tmp_path, target, SHAPES[shape])
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    reads = plan.expression_block_uses
    quote = "`" if target == "mysql" else '"'
    assert document["sql"].count(f"(SELECT {quote}e") == len(reads) > 0
    assert all(r.edge.column is not None for r in reads)
    if shape != "values":
        # The private emission observation does not describe VALUES bodies.
        _observed(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_tampered_scalar_read_is_refused_by_the_emission_verifier(
    tmp_path: Path, target: str
) -> None:
    from dataclasses import replace

    from pietto._project.project_sql_emission_verification import verify_row_query

    _, outcome = _emit(tmp_path, target, CANONICAL)
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLRowQuery and verify_row_query(artifact.request, query)
    final = query.bodies[-1]
    (other, _), (read, index) = (
        (column.value, i)
        for i, column in enumerate(final.columns)
        if type(column.value) is rows.SQLBlockRead
    )
    assert (read.target.source is not None, read.column) == (True, 1)
    for forged in (
        # The source's other existing column, the other read's block, an
        # existence kind, and a NOT NULL realization of the same carrier.
        replace(read, column=0),
        replace(read, target=other.target),
        replace(read, kind="exists"),
        replace(read, realization=replace(read.realization, nullable=False)),
    ):
        columns = list(final.columns)
        columns[index] = replace(columns[index], value=forged)
        bodies = (*query.bodies[:-1], replace(final, columns=tuple(columns)))
        assert not verify_row_query(artifact.request, replace(query, bodies=bodies))
