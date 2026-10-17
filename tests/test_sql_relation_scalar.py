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
def test_a_scalar_read_of_a_soft_keyword_column_emits_like_any_other(
    tmp_path: Path, target: str
) -> None:
    body = CANONICAL.replace("rid = id", "select = id").replace(
        "picked.rid", "picked.select"
    )
    _, outcome = _emit(tmp_path, target, body)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == SQL[target]


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


# Phase70 S14: a scalar read of a let with capture lines renders that let
# inline at the read, `(SELECT e<n>.c<k> FROM (<let bodies>) AS e<n>)`, whose
# correlated references name the reading body's own alias; the let is never a
# CTE and every outer row, duplicates included, gets its own read.
CORRELATED = {
    "select": """query result:
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > 0
        select:
            id
            key
    from lhs
    where lhs.id > 1
    select:
        a = lhs.id
        k = scalar matched.key
""",
    "where": """query result:
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > 0
        select:
            id
            key
    from lhs
    where lhs.id == scalar matched.id
    select:
        a = lhs.id
""",
}
CORRELATED_SQL = {
    ("select", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
        'WHERE ("s1"."order.id" > CAST($1 AS pg_catalog.int8))) '
        'SELECT "t3"."c0" AS "a", (SELECT "e0"."c1" FROM '
        '(SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1" FROM '
        '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        'FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE (("s0"."key value" = "t3"."c1") AND '
        '("s0"."order.id" > CAST($2 AS pg_catalog.int8)))) AS "t1") AS "e0") '
        'AS "k" FROM "p0" AS "t3"'
    ),
    ("select", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, "
        "`s1`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` "
        "WHERE (`s1`.`order.id` > CAST(? AS SIGNED))) "
        "SELECT `t3`.`c0` AS `a`, (SELECT `e0`.`c1` FROM "
        "(SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1` FROM "
        "(SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` "
        "FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE ((`s0`.`key value` = `t3`.`c1`) AND "
        "(`s0`.`order.id` > CAST(? AS SIGNED)))) AS `t1`) AS `e0`) "
        "AS `k` FROM `p0` AS `t3`"
    ),
    ("where", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
        'WHERE ("s1"."order.id" = (SELECT "e0"."c0" FROM '
        '(SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1" FROM '
        '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        'FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE (("s0"."key value" = "s1"."key value") AND '
        '("s0"."order.id" > CAST($1 AS pg_catalog.int8)))) AS "t1") AS "e0"))) '
        'SELECT "t3"."c0" AS "a" FROM "p0" AS "t3"'
    ),
    ("where", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, "
        "`s1`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` "
        "WHERE (`s1`.`order.id` = (SELECT `e0`.`c0` FROM "
        "(SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1` FROM "
        "(SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` "
        "FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE ((`s0`.`key value` = `s1`.`key value`) AND "
        "(`s0`.`order.id` > CAST(? AS SIGNED)))) AS `t1`) AS `e0`))) "
        "SELECT `t3`.`c0` AS `a` FROM `p0` AS `t3`"
    ),
}


def _correlated(tmp_path: Path, target: str, shape: str, policy: str):
    item = probe.join_witness(target, CORRELATED[shape], policy=policy)
    return probe.build_case(tmp_path, item["source"], item["contract"], item["policy"])


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(CORRELATED))
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_correlated_scalar_read_renders_its_let_inline(
    tmp_path: Path, target: str, shape: str, policy: str
) -> None:
    from pietto._project import project_sql_plan_portable as transport

    checked, outcome = _correlated(tmp_path, target, shape, policy)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    expected = CORRELATED_SQL[shape, target]
    if policy == "preserve_literals":
        first, second = ("1", "0") if shape == "select" else ("0", None)
        expected = expected.replace("$1", first).replace("$2", str(second))
        expected = expected.replace("CAST(? AS", f"CAST({first} AS", 1)
        expected = expected.replace("CAST(? AS", f"CAST({second} AS", 1)
    assert document["sql"] == expected
    assert " LIMIT " not in document["sql"]
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    (capture,) = plan.captures
    assert type(plan.expressions[capture.read.position]) is row.ProjectSQLRelationScalar
    # The let is never a CTE: its read opens the one derived table.
    quote = "`" if target == "mysql" else '"'
    assert document["sql"].count(f"(SELECT {quote}e0{quote}.") == 1
    assert document["sql"].count(f"{quote}p1{quote}") == 0
    if shape == "select":
        assert [c["nullable"] for c in document["columns"]] == [False, True]
    artifact = outcome.artifact
    assert artifact is not None
    kinds = [(r.kind, r.rule) for r in artifact.generated_requirements]
    captured = sum(
        1 for e in plan.expressions if type(e) is row.ProjectSQLCapturedField
    )
    assert kinds.count(("capture", "R11")) == captured == 1
    assert kinds.count(("inline_stage_use", "R11")) == 1
    assert kinds.count(("scalar", "R11")) == 1
    if policy == "bind_safe_literals":
        # The outer literal renders first; the inline let's follows its read.
        assert [(u.ordinal, u.server_index) for u in artifact.parameter_uses] == (
            [(0, 1), (1, 2)] if shape == "select" else [(0, 1)]
        )
    _observed(outcome)
    with pytest.raises(transport.TransportError) as refused:
        transport.build_project_sql_plan_portable(checked)
    assert refused.value.issue is transport.RuntimeIssue.UNSUPPORTED_VALUE


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation", ("other_column", "inner_producer", "existence_kind", "not_null")
)
def test_a_forged_correlated_scalar_read_fails_the_verifiers(
    tmp_path: Path, target: str, mutation: str
) -> None:
    from dataclasses import replace

    from pietto._project.project_sql_emission_verification import (
        verify_row_bytes,
        verify_row_query,
    )

    _, outcome = _correlated(tmp_path, target, "select", "preserve_literals")
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLRowQuery and verify_row_query(artifact.request, query)
    final = query.bodies[-1]
    ((read, index),) = (
        (column.value, i)
        for i, column in enumerate(final.columns)
        if type(getattr(column, "value", None)) is rows.SQLBlockRead
    )
    inner = read.target.producer
    assert (read.column, inner.symbol, inner.cte_columns) == (1, None, ())
    # Valid-looking values: the let's other output, its own inner stage body,
    # an existence read of the same target, a NOT NULL read of the same carrier.
    forged = {
        "other_column": lambda: replace(read, column=0),
        "inner_producer": lambda: replace(
            read, target=replace(read.target, producer=inner.scan.body)
        ),
        "existence_kind": lambda: replace(read, kind="exists", column=None),
        "not_null": lambda: replace(
            read, realization=replace(read.realization, nullable=False)
        ),
    }[mutation]()
    columns = list(final.columns)
    columns[index] = replace(columns[index], value=forged)
    bodies = (*query.bodies[:-1], replace(final, columns=tuple(columns)))
    assert not verify_row_query(artifact.request, replace(query, bodies=bodies))
    # The bytes of the let's other output under the same alias are refused.
    q = '"' if target == "postgres" else "`"
    sql = artifact.rendered.sql.decode()
    corrupted = sql.replace(f"(SELECT {q}e0{q}.{q}c1{q}", f"(SELECT {q}e0{q}.{q}c0{q}")
    assert corrupted != sql
    changed = replace(artifact.rendered, sql=corrupted.encode("utf-8"))
    assert not verify_row_bytes(artifact.ast, changed)


# Owner decision 2026-10-15 (D70.05): a correlated scalar read of a let ending
# in ORDER BY and LIMIT is PostgreSQL only. The let's result body is one more
# derived table inside the read's own, which carries each ORDER BY key as an
# extra column: `(SELECT e<n>.c<k> FROM (SELECT ... FROM (<let bodies>) AS t<n>
# ORDER BY ... LIMIT <n>) AS e<n>)`. MySQL emission refuses the read before any
# SQL exists; the program itself is valid on both targets.
ORDERED = CORRELATED["select"].replace(
    "            key\n    from lhs",
    "            key\n        order by:\n            id desc\n        limit 1\n"
    "    from lhs",
)
ORDERED_SQL = (
    'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
    '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
    'WHERE ("s1"."order.id" > CAST($1 AS pg_catalog.int8))) '
    'SELECT "t3"."c0" AS "a", (SELECT "e0"."c1" FROM '
    '(SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1" FROM '
    '(SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c0" AS "c2" FROM '
    '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
    'FROM "public"."phase66 rhs é" AS "s0" '
    'WHERE (("s0"."key value" = "t3"."c1") AND '
    '("s0"."order.id" > CAST($2 AS pg_catalog.int8)))) AS "t1") AS "t0" '
    'ORDER BY "t0"."c2" DESC LIMIT 1) AS "e0") AS "k" FROM "p0" AS "t3"'
)
MYSQL_ORDERED_READ = (
    "PIE-B1003",
    "UNSUPPORTED_RULE",
    "mysql_correlated_order_or_limit_read_not_admitted",
)


def _ordered(tmp_path: Path, target: str, policy: str = "bind_safe_literals"):
    item = probe.join_witness(target, ORDERED, policy=policy)
    return probe.build_case(tmp_path, item["source"], item["contract"], item["policy"])


def _ordered_read(artifact):
    query = artifact.ast
    assert type(query) is SQLRowQuery
    final = query.bodies[-1]
    ((read, index),) = (
        (column.value, i)
        for i, column in enumerate(final.columns)
        if type(getattr(column, "value", None)) is rows.SQLBlockRead
    )
    return query, final, read, index


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_correlated_scalar_read_takes_its_lets_order_and_limit_on_postgres(
    tmp_path: Path, target: str, policy: str
) -> None:
    from pietto._project.project_sql_emission_ast import inline_body
    from pietto._project.project_sql_emission_results import RowResultBody

    checked, outcome = _ordered(tmp_path, target, policy)
    document = json.loads(serialize_project_sql_emission(outcome))
    if target == "mysql":
        assert (document["status"], document["diagnostics"]) == ("BLOCKED", [])
        assert "sql" not in document and outcome.artifact is None
        assert [
            (
                b["code"],
                b["reason"],
                b["subject"]["detail"],
                b["location"]["line"],
                b["location"]["column"],
            )
            for b in document["blockers"]
        ] == [(*MYSQL_ORDERED_READ, 21, 13)]
        return
    assert document["status"] == "VERIFIED", document
    expected = ORDERED_SQL
    if policy == "preserve_literals":
        expected = expected.replace("$1", "1").replace("$2", "0")
    assert document["sql"] == expected
    assert [c["nullable"] for c in document["columns"]] == [False, True]
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    (capture,) = plan.captures
    assert type(plan.expressions[capture.read.position]) is row.ProjectSQLRelationScalar
    assert [
        b.kind.value for b in plan.result_boundaries if b.definition is capture.inner
    ] == ["relation_ordering", "limit"]
    artifact = outcome.artifact
    assert artifact is not None
    _, _, read, _ = _ordered_read(artifact)
    result = read.target.producer
    # The let's third body (filter, projection, result), unnamed and not final.
    assert type(result) is RowResultBody and inline_body(result.scan.body)
    assert (result.final, result.symbol, result.cte_columns) == (False, None, ())
    assert result.limit is not None and result.limit.value == 1
    assert read.column == 1 and len(result.columns) == 2
    kinds = [(r.kind, r.rule) for r in artifact.generated_requirements]
    assert kinds.count(("inline_stage_use", "R11")) == 2
    assert kinds.count(("static_limit", "R21")) == 1
    if policy == "bind_safe_literals":
        assert [(u.ordinal, u.server_index) for u in artifact.parameter_uses] == [
            (0, 1),
            (1, 2),
        ]
    # The private observation has no schema for an inline result body.
    assert (
        portable.export_emission_observation(artifact, artifact.request).status
        is portable.ObservationStatus.OUTSIDE_SCHEMA
    )


# Every scalar, IN and NOT IN read of an ordered capturing let is refused on
# MySQL at its own read, in source order across the statement's relations,
# never only the first.
ORDERED_READS = """table t:
    let m1:
        capture lhs
        from rhs
        where rhs.key == lhs.key
        select:
            id
        order by:
            id desc
        limit 1
    from lhs
    where lhs.id in m1
    select:
        id
        key
query result:
    let m2:
        capture t
        from rhs
        where rhs.key == t.key
        select:
            id
        order by:
            id desc
        limit 1
    let m3:
        capture t
        from rhs
        where rhs.id == t.id
        select:
            key
        order by:
            id
        limit 2
    from t
    where t.key not in m3
    select:
        a = t.id
        k = scalar m2.id
"""


@pytest.mark.parametrize("target", TARGETS)
def test_every_ordered_correlated_read_is_refused_on_mysql(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(target, ORDERED_READS, policy="bind_safe_literals")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    if target == "postgres":
        assert document["status"] == "VERIFIED", document
        assert document["sql"].count(" LIMIT ") == 3
        return
    lines = item["source"].splitlines()
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
        (*MYSQL_ORDERED_READ, lines.index("    where lhs.id in m1") + 1, 11),
        (*MYSQL_ORDERED_READ, lines.index("    where t.key not in m3") + 1, 11),
        (*MYSQL_ORDERED_READ, lines.index("        k = scalar m2.id") + 1, 13),
    ]


@pytest.mark.parametrize(
    "mutation", ("limit_value", "order_direction", "dropped_result", "named_result")
)
def test_a_forged_ordered_scalar_read_fails_the_verifiers(
    tmp_path: Path, mutation: str
) -> None:
    from dataclasses import replace

    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
        verify_row_bytes,
        verify_row_query,
    )

    _, outcome = _ordered(tmp_path, "postgres")
    artifact = outcome.artifact
    assert artifact is not None
    query, final, read, _ = _ordered_read(artifact)
    result = read.target.producer
    assert result.limit is not None and result.order is not None
    # Valid-looking values: another static limit, the other direction, the
    # let's own projection (it has the read column too) and the name of the
    # statement's own CTE.
    changes = {
        "limit_value": [(result.limit, "value", 2)],
        "order_direction": [(result.order.items[0], "direction", "ASC")],
        "dropped_result": [(read.target, "producer", result.scan.body)],
        "named_result": [(result, "symbol", query.bodies[0].symbol)],
    }[mutation]
    originals = [(node, name, getattr(node, name)) for node, name, _ in changes]
    try:
        for node, name, value in changes:
            object.__setattr__(node, name, value)
        assert not verify_row_query(artifact.request, query)
    finally:
        for node, name, value in originals:
            object.__setattr__(node, name, value)
    assert verify_row_query(artifact.request, query)
    # The bytes of another limit or direction under the same tree are refused.
    sql = artifact.rendered.sql.decode()
    corrupted = (
        sql.replace(" LIMIT 1) AS ", " LIMIT 2) AS ")
        if mutation == "limit_value"
        else sql.replace(" DESC LIMIT 1)", " ASC LIMIT 1)")
    )
    assert corrupted != sql
    changed = replace(artifact.rendered, sql=corrupted.encode("utf-8"))
    assert not verify_row_bytes(artifact.ast, changed)
    assert not verify_project_sql_emission(
        replace(artifact, rendered=changed), artifact.request
    ).verified


def test_the_verifier_refuses_a_mysql_ordered_scalar_read_on_its_own(
    tmp_path: Path, monkeypatch
) -> None:
    # With the emission's own refusal lifted, the independent verifier still
    # refuses the MySQL tree, so no artifact exists.
    from pietto._project import project_sql_emission_ast as sql_ast

    monkeypatch.setattr(
        sql_ast, "ORDERED_INLINE_READ_TARGETS", frozenset({"postgres", "mysql"})
    )
    _, outcome = _ordered(tmp_path, "mysql")
    document = json.loads(serialize_project_sql_emission(outcome))
    assert outcome.artifact is None and document["status"] == "BLOCKED"
    assert [(b["code"], b["subject"]["detail"]) for b in document["blockers"]] == [
        ("PIE-B1008", "plan_ast_correspondence")
    ]


# Phase70 S11 x S14: a let read by a correlated scalar reads the entry query's
# header like any other let of it. On PostgreSQL a let ending in ORDER BY and
# LIMIT keeps them in the wrapper around its read; MySQL refuses that read as
# it does without parameters.
HEADER_IN_SCALAR = """query result(cut: Int not null, hi: Int nullable):
    let m:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > cut and rhs.id != 100
        select:
            id
            key
    from lhs
    where lhs.id > hi
    select:
        a = lhs.id
        k = scalar m.key
"""
HEADER_IN_SCALAR_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", "s1"."key '
        'value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" WHERE '
        '("s1"."order.id" > CAST($1 AS pg_catalog.int8))) SELECT "t3"."c0" AS '
        '"a", (SELECT "e0"."c1" FROM (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1" '
        'FROM (SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" FROM '
        '"public"."phase66 rhs é" AS "s0" WHERE ((("s0"."key value" = "t3"."c1") '
        'AND ("s0"."order.id" > CAST($2 AS pg_catalog.int8))) AND '
        '("s0"."order.id" <> CAST($3 AS pg_catalog.int8)))) AS "t1") AS "e0") AS '
        '"k" FROM "p0" AS "t3"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, `s1`.`key "
        "value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` WHERE "
        "(`s1`.`order.id` > CAST(? AS SIGNED))) SELECT `t3`.`c0` AS `a`, (SELECT "
        "`e0`.`c1` FROM (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1` FROM (SELECT "
        "`s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 rhs é` AS `s0` WHERE (((`s0`.`key value` = `t3`.`c1`) "
        "AND (`s0`.`order.id` > CAST(? AS SIGNED))) AND (`s0`.`order.id` <> "
        "CAST(? AS SIGNED)))) AS `t1`) AS `e0`) AS `k` FROM `p0` AS `t3`"
    ),
}
HEADER_IN_ORDERED_SCALAR = """query result(cut: Int not null, hi: Int nullable):
    let m:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > cut
        select:
            id
            key
        order by:
            id desc
        limit 1
    from lhs
    where lhs.id < hi
    select:
        a = lhs.id
        k = scalar m.key
"""
HEADER_IN_ORDERED_SCALAR_SQL = (
    'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", "s1"."key '
    'value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" WHERE '
    '("s1"."order.id" < CAST($1 AS pg_catalog.int8))) SELECT "t3"."c0" AS '
    '"a", (SELECT "e0"."c1" FROM (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1" '
    'FROM (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c0" AS "c2" '
    'FROM (SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" FROM '
    '"public"."phase66 rhs é" AS "s0" WHERE (("s0"."key value" = "t3"."c1") '
    'AND ("s0"."order.id" > CAST($2 AS pg_catalog.int8)))) AS "t1") AS "t0" '
    'ORDER BY "t0"."c2" DESC LIMIT 1) AS "e0") AS "k" FROM "p0" AS "t3"'
)


@pytest.mark.parametrize("target", TARGETS)
def test_a_scalar_read_let_reads_the_entry_query_header(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(target, HEADER_IN_SCALAR, policy="bind_safe_literals")
    _, outcome = probe.build_case(
        tmp_path / "plain", item["source"], item["contract"], item["policy"]
    )
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == HEADER_IN_SCALAR_SQL[target]
    # `hi` renders first (the outer WHERE stage), then the let's `cut`, then
    # the let's own literal slot.
    assert [
        (u["owner"]["kind"], u["owner"][u["owner"]["kind"]], u["server_index"])
        for u in document["parameter_uses"]
    ] == [("parameter", 1, 1), ("parameter", 0, 2), ("slot", 0, 3)]
    assert probe.decoded_arguments(probe.decode_public(raw), {"cut": 3, "hi": 7}) == (
        7,
        3,
        100,
    )
    item = probe.join_witness(
        target, HEADER_IN_ORDERED_SCALAR, policy="bind_safe_literals"
    )
    _, outcome = probe.build_case(
        tmp_path / "ordered", item["source"], item["contract"], item["policy"]
    )
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    if target == "mysql":
        assert (document["status"], outcome.artifact) == ("BLOCKED", None)
        assert [
            (
                b["code"],
                b["reason"],
                b["subject"]["detail"],
                b["location"]["line"],
                b["location"]["column"],
            )
            for b in document["blockers"]
        ] == [(*MYSQL_ORDERED_READ, 21, 13)]
        return
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == HEADER_IN_ORDERED_SCALAR_SQL
    assert probe.decoded_arguments(
        probe.decode_public(raw), {"cut": 3, "hi": None}
    ) == (None, 3)
