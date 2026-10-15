"""Closed EXISTS / NOT EXISTS: one expression reads one whole relation block.

An existence read is an expression block use of its owner, never one of the
owner's FROM, JOIN or set inputs. The read relation is emitted as a top-level
CTE (or read as a qualified source), so every source reached only through the
read is a source of the statement.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_sql_emission_ast import SQLRowQuery
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
    verify_row_bytes,
    verify_row_query,
)
from pietto._project.project_postgres_source_assurance import qualification_roots
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project.project_sql_plan_expressions import ProjectSQLParameterRead
from pietto._project.project_sql_plan_verification import verify_project_sql_plan

TARGETS = ("postgres", "mysql")
HIDDEN = """query result:
    let picked:
        from rhs
        where id > 0
        select:
            rid = id
    from lhs
    where not exists picked
    select:
        a = lhs.id
        e = exists rhs
"""
SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE ("s0"."order.id" > CAST(0 AS pg_catalog.int8))), '
        '"p1" ("c0") AS (SELECT "t1"."c0" AS "c0" FROM "p0" AS "t1"), '
        '"p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
        'WHERE (NOT EXISTS (SELECT 1 FROM "p1" AS "e0"))) '
        'SELECT "t3"."c0" AS "a", '
        'EXISTS (SELECT 1 FROM "public"."phase66 rhs é" AS "e1") AS "e" '
        'FROM "p2" AS "t3"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`order.id` AS `c0`, "
        "`s0`.`key value` AS `c1` FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE (`s0`.`order.id` > CAST(0 AS SIGNED))), "
        "`p1` (`c0`) AS (SELECT `t1`.`c0` AS `c0` FROM `p0` AS `t1`), "
        "`p2` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, "
        "`s1`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` "
        "WHERE (NOT EXISTS (SELECT 1 FROM `p1` AS `e0`))) "
        "SELECT `t3`.`c0` AS `a`, "
        "EXISTS (SELECT 1 FROM `phase66`.`phase66 rhs é` AS `e1`) AS `e` "
        "FROM `p2` AS `t3`"
    ),
}
# Each read target shape: a module query, a grouped producer, a set body, a
# JOIN producer and a JOIN consumer, all read only through existence.
SHAPES = {
    "grouped": """query counts:
    from rhs
    group by:
        id
    select:
        id
        n = count()
query result:
    from lhs
    where exists counts
    select:
        a = lhs.id
""",
    "set": """query both:
    union all:
        from lhs
        from rhs
query result:
    from lhs
    where not exists both
    select:
        a = lhs.id
""",
    "join_producer": """query pairs:
    from lhs
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    select:
        a = lhs.id
query result:
    from lhs
    where exists pairs
    select:
        a = lhs.id
""",
    "join_consumer": """query result:
    from lhs
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    where exists rhs
    select:
        a = lhs.id
        e = exists rhs
""",
    "grouped_consumer": """query result:
    let picked:
        from rhs
        select:
            id
    from lhs
    where exists picked
    group by:
        id
    select:
        id
        n = count()
""",
    # A typed VALUES query and a zero-row VALUES let are read like any block.
    "values": """query seeds:
    values(rid: Int not null):
        1
query result:
    let none:
        values(rid: Int not null)
    from lhs
    where exists seeds and not exists none
    select:
        a = lhs.id
""",
    "repeated": """query counts:
    from rhs
    select:
        id
query result:
    from lhs
    where exists counts and exists counts
    select:
        a = lhs.id
        e = exists counts
""",
}


def _emit(tmp_path: Path, target: str, body: str, *, contract=None):
    item = probe.join_witness(target, body)
    return probe.build_case(
        tmp_path, item["source"], contract or item["contract"], item["policy"]
    )


@pytest.mark.parametrize("target", TARGETS)
def test_existence_reads_emit_top_level_ctes_and_exists_subqueries(
    tmp_path: Path, target: str
) -> None:
    _, outcome = _emit(tmp_path, target, HIDDEN)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == SQL[target]
    assert [c["label"] for c in document["columns"]] == ["a", "e"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_source_read_only_through_an_existence_read_is_a_statement_source(
    tmp_path: Path, target: str
) -> None:
    checked, outcome = _emit(tmp_path, target, HIDDEN.replace("e = exists rhs", "id"))
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
    assert use.target.let_position == 0 and use.evidence.read.position.value == "where"
    definitions = {d.ref: d for d in plan.bindings.definitions}
    assert definitions[read.producer].entry.owner is use.target
    # The read never occupies one of the consumer's relation-input slots.
    consumer_inputs = [u for u in plan.input_uses if u.consumer is read.consumer]
    assert [
        definitions[u.producer].entry.owner.definition.name for u in consumer_inputs
    ] == ["lhs"]
    request = outcome.artifact.request
    assert [s.name for s in request.sources] == ["phase66 lhs é", "phase66 rhs é"]
    # PostgreSQL source assurance and the MySQL closure both start from them.
    assert qualification_roots(request.sources, ()) == tuple(
        (s.namespace, s.name) for s in request.sources
    )
    report = request.report.report
    inner = [
        u
        for u in report.input_uses
        if u.binding.target_occurrence.definition.name == "rhs"
    ]
    assert [u.dependency.consumer.let_position for u in inner] == [0]
    assert report.indexes.by_input_use[inner[0].ref]


@pytest.mark.parametrize("target", TARGETS)
def test_an_inner_source_needs_its_contract_mapping_and_target_family(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(target, HIDDEN)
    contract = json.loads(item["contract"])
    contract["sources"] = contract["sources"][:1]
    _, outcome = _emit(
        tmp_path / "missing", target, HIDDEN, contract=json.dumps(contract)
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "BLOCKED"
    assert {(b["code"], b["subject"]["detail"]) for b in document["blockers"]} == {
        ("PIE-B1001", "source_mapping_missing")
    }
    other = "mysql" if target == "postgres" else "postgres"
    foreign = item["source"].replace(
        f'source rhs: Row is {target}.table("rhs")',
        f'source rhs: Row is {other}.table("rhs")',
    )
    _, outcome = probe.build_case(
        tmp_path / "foreign", foreign, item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "BLOCKED"
    assert [
        (b["code"], b["location"]["line"])
        for b in document["blockers"]
        if b["subject"]["detail"] == "source_family_mismatch"
    ] == [("PIE-B1001", 5)]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_existence_reads_of_every_producer_shape_verify(
    tmp_path: Path, target: str, shape: str
) -> None:
    checked, outcome = _emit(tmp_path, target, SHAPES[shape])
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    reads = plan.expression_block_uses
    assert document["sql"].count("EXISTS (SELECT 1 FROM ") == len(reads) > 0
    # Equal reads stay distinct occurrences with distinct aliases.
    assert len({id(r.edge.use.expression) for r in reads}) == len(reads)
    for position in range(len(reads)):
        assert f"e{position}" in document["sql"]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "body",
    (
        "query result:\n    from lhs\n    let:\n        f = exists rhs\n"
        "    select:\n        id\n        f\n",
        "query result:\n    from lhs\n    select:\n        id\n"
        "    order by:\n        exists rhs\n",
    ),
    ids=("row_let", "order_by"),
)
def test_a_read_outside_where_and_select_is_not_lowered(
    tmp_path: Path, target: str, body: str
) -> None:
    _, outcome = _emit(tmp_path, target, body)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "BLOCKED" and "sql" not in document


def _reads(query):
    """Every existence read of a realized statement, by its generated alias."""
    found, pending, seen = [], list(query.bodies), set()
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        if type(value) is rows.SQLBlockRead:
            found.append(value)
        elif type(value) is tuple:
            pending.extend(value)
        elif type(value).__module__.startswith("pietto._project.project_sql_emission"):
            if dataclasses.is_dataclass(value):
                pending.extend(
                    getattr(value, f.name) for f in dataclasses.fields(value)
                )
    return sorted(found, key=lambda read: read.target.symbol.name)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation",
    ("targets_swapped", "alias_of_the_other_read", "nullable", "other_producer"),
)
def test_a_forged_existence_read_fails_the_independent_verifier(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _emit(tmp_path, target, HIDDEN)
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLRowQuery
    first, second = _reads(query)
    assert [r.target.symbol.name for r in (first, second)] == ["e0", "e1"]
    if mutation == "targets_swapped":
        changes = [(first, "target", second.target), (second, "target", first.target)]
    elif mutation == "alias_of_the_other_read":
        changes = [(first.target, "symbol", second.target.symbol)]
    elif mutation == "nullable":
        changes = [
            (
                first,
                "realization",
                dataclasses.replace(first.realization, nullable=True),
            )
        ]
    else:
        other = next(u for u in query.bodies if u is not first.target.producer)
        changes = [(first.target, "producer", other)]
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
@pytest.mark.parametrize("mutation", ("alias_renamed", "producer_renamed"))
def test_forged_existence_read_bytes_fail_the_byte_verifier(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _emit(tmp_path, target, HIDDEN)
    artifact = outcome.artifact
    assert artifact is not None
    q = '"' if target == "postgres" else "`"
    sql = artifact.rendered.sql.decode()
    if mutation == "alias_renamed":
        corrupted = sql.replace(f"AS {q}e0{q})", f"AS {q}e7{q})", 1)
    else:
        corrupted = sql.replace(
            f"FROM {q}p1{q} AS {q}e0{q}", f"FROM {q}p0{q} AS {q}e0{q}"
        )
    assert corrupted != sql
    changed = dataclasses.replace(artifact.rendered, sql=corrupted.encode("utf-8"))
    assert not verify_row_bytes(artifact.ast, changed)
    checked = verify_project_sql_emission(
        dataclasses.replace(artifact, rendered=changed), artifact.request
    )
    assert not checked.verified


PARAMETERIZED = """query result(cut: Int not null):
    from lhs
    where id > cut and not exists rhs
    select:
        id
        e = exists rhs
"""
PARAMETERIZED_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s0" '
        'WHERE (("s0"."order.id" > CAST($1 AS pg_catalog.int8)) AND '
        '(NOT EXISTS (SELECT 1 FROM "public"."phase66 rhs é" AS "e0")))) '
        'SELECT "t1"."c0" AS "id", '
        'EXISTS (SELECT 1 FROM "public"."phase66 rhs é" AS "e1") AS "e" '
        'FROM "p0" AS "t1"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`order.id` AS `c0`, "
        "`s0`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s0` "
        "WHERE ((`s0`.`order.id` > CAST(? AS SIGNED)) AND "
        "(NOT EXISTS (SELECT 1 FROM `phase66`.`phase66 rhs é` AS `e0`)))) "
        "SELECT `t1`.`c0` AS `id`, "
        "EXISTS (SELECT 1 FROM `phase66`.`phase66 rhs é` AS `e1`) AS `e` "
        "FROM `p0` AS `t1`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_an_entry_query_with_parameters_reads_blocks_by_existence(
    tmp_path: Path, target: str
) -> None:
    """A header parameter keeps its one native placeholder beside the reads."""
    item = probe.join_witness(target, PARAMETERIZED, policy="bind_safe_literals")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == PARAMETERIZED_SQL[target]
    assert outcome.artifact is not None
    assert [
        (use.ordinal, use.server_index) for use in outcome.artifact.parameter_uses
    ] == [(0, 1)]


# Phase70 S10: a let with capture lines reads the current row of its reader's
# FROM or JOIN input. It is emitted inside that EXISTS read as nested derived
# tables (a correlated reference cannot live in a CTE); every capture-free
# block stays a top-level CTE.
CORRELATED = {
    "where": """query result:
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key
        select:
            id
    from lhs
    where exists matched
    select:
        a = lhs.id
""",
    "left_join": """query result:
    let matched:
        capture r
        capture lhs
        from rhs
        where rhs.key == r.key and rhs.id == lhs.id
        select:
            id
    from lhs
    left join rhs as r:
        from lhs
        on lhs.id == r.id
    where exists matched
    select:
        a = lhs.id
        b = r.key
""",
    "select": """query result:
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > 0
        select:
            id
            k = lhs.id
    from lhs
    where lhs.id > 0
    select:
        a = lhs.id
        e = not exists matched
""",
}
CORRELATED_SQL = {
    ("where", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
        'WHERE EXISTS (SELECT 1 FROM (SELECT "t1"."c0" AS "c0" FROM '
        '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        'FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE ("s0"."key value" = "s1"."key value")) AS "t1") AS "e0")) '
        'SELECT "t3"."c0" AS "a" FROM "p0" AS "t3"'
    ),
    ("where", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, "
        "`s1`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` "
        "WHERE EXISTS (SELECT 1 FROM (SELECT `t1`.`c0` AS `c0` FROM "
        "(SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` "
        "FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE (`s0`.`key value` = `s1`.`key value`)) AS `t1`) AS `e0`)) "
        "SELECT `t3`.`c0` AS `a` FROM `p0` AS `t3`"
    ),
    ("left_join", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."order.id" AS "c2", '
        '"m1"."key value" AS "c3" FROM "public"."phase66 lhs é" AS "m0" '
        'LEFT JOIN "public"."phase66 rhs é" AS "m1" '
        'ON ("m0"."order.id" = "m1"."order.id")), '
        '"p1" ("c0", "c1", "c2", "c3") AS (SELECT "t0"."c0" AS "c0", '
        '"t0"."c1" AS "c1", "t0"."c2" AS "c2", "t0"."c3" AS "c3" '
        'FROM "p0" AS "t0" WHERE EXISTS (SELECT 1 FROM (SELECT "t1"."c0" AS "c0" '
        'FROM (SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        'FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE (("s0"."key value" = "t0"."c3") AND '
        '("s0"."order.id" = "t0"."c0"))) AS "t1") AS "e0")) '
        'SELECT "t3"."c0" AS "a", "t3"."c3" AS "b" FROM "p1" AS "t3"'
    ),
    ("left_join", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `m0`.`order.id` AS `c0`, "
        "`m0`.`key value` AS `c1`, `m1`.`order.id` AS `c2`, "
        "`m1`.`key value` AS `c3` FROM `phase66`.`phase66 lhs é` AS `m0` "
        "LEFT JOIN `phase66`.`phase66 rhs é` AS `m1` "
        "ON (`m0`.`order.id` = `m1`.`order.id`)), "
        "`p1` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `t0`.`c0` AS `c0`, "
        "`t0`.`c1` AS `c1`, `t0`.`c2` AS `c2`, `t0`.`c3` AS `c3` "
        "FROM `p0` AS `t0` WHERE EXISTS (SELECT 1 FROM (SELECT `t1`.`c0` AS `c0` "
        "FROM (SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` "
        "FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE ((`s0`.`key value` = `t0`.`c3`) AND "
        "(`s0`.`order.id` = `t0`.`c0`))) AS `t1`) AS `e0`)) "
        "SELECT `t3`.`c0` AS `a`, `t3`.`c3` AS `b` FROM `p1` AS `t3`"
    ),
    ("select", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
        'WHERE ("s1"."order.id" > CAST($1 AS pg_catalog.int8))) '
        'SELECT "t3"."c0" AS "a", (NOT EXISTS (SELECT 1 FROM '
        '(SELECT "t1"."c0" AS "c0", "t3"."c0" AS "c1" FROM '
        '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        'FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE (("s0"."key value" = "t3"."c1") AND '
        '("s0"."order.id" > CAST($2 AS pg_catalog.int8)))) AS "t1") AS "e0")) '
        'AS "e" FROM "p0" AS "t3"'
    ),
    ("select", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, "
        "`s1`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` "
        "WHERE (`s1`.`order.id` > CAST(? AS SIGNED))) "
        "SELECT `t3`.`c0` AS `a`, (NOT EXISTS (SELECT 1 FROM "
        "(SELECT `t1`.`c0` AS `c0`, `t3`.`c0` AS `c1` FROM "
        "(SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` "
        "FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE ((`s0`.`key value` = `t3`.`c1`) AND "
        "(`s0`.`order.id` > CAST(? AS SIGNED)))) AS `t1`) AS `e0`)) "
        "AS `e` FROM `p0` AS `t3`"
    ),
}


def _correlated(tmp_path: Path, target: str, shape: str, policy: str):
    item = probe.join_witness(target, CORRELATED[shape], policy=policy)
    return probe.build_case(tmp_path, item["source"], item["contract"], item["policy"])


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(CORRELATED))
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_capturing_let_is_emitted_inside_its_exists_read(
    tmp_path: Path, target: str, shape: str, policy: str
) -> None:
    checked, outcome = _correlated(tmp_path, target, shape, policy)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    expected = CORRELATED_SQL[shape, target]
    if policy == "preserve_literals":
        expected = (
            expected.replace("$1", "0")
            .replace("$2", "0")
            .replace("CAST(? AS", "CAST(0 AS")
        )
    assert document["sql"] == expected
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    # Capture-free blocks stay CTEs; the capturing let is never one.
    assert [c.use.clause.name for c in plan.captures] == (
        ["r", "lhs"] if shape == "left_join" else ["lhs"]
    )
    # The capturing let is never a CTE: its read opens a derived table.
    assert document["sql"].count("EXISTS (SELECT 1 FROM (SELECT ") == 1
    assert outcome.artifact is not None
    # Each correlated reference keeps its own R11 obligation, and the inline
    # derived tables their own read-only bodies.
    kinds = [(r.kind, r.rule) for r in outcome.artifact.generated_requirements]
    references = sum(
        1 for e in plan.expressions if type(e) is row.ProjectSQLCapturedField
    )
    assert kinds.count(("capture", "R11")) == references > 0
    assert kinds.count(("inline_stage_use", "R11")) == 1
    if policy == "bind_safe_literals" and shape == "select":
        # Native placeholders follow the text: the inner literal renders second.
        assert [
            (use.ordinal, use.server_index) for use in outcome.artifact.parameter_uses
        ] == [(0, 1), (1, 2)]
    # The private observation carries the inline bodies and captured fields
    # and corresponds; the plan transport has no capture record yet and
    # refuses the plan instead of dropping its captures.
    from pietto._project import project_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_plan_portable as transport
    from pietto._project.project_sql_emission_portable import (
        ObservationStatus,
        export_emission_observation,
        verify_emission_observation,
    )

    artifact = outcome.artifact
    observed = export_emission_observation(artifact, artifact.request)
    assert observed.status is ObservationStatus.OK
    assert observed.canonical_bytes is not None
    decoded = pure.parse_emission_observation(observed.canonical_bytes)
    assert decoded.status is pure.Status.OK and decoded.view is not None
    assert len(decoded.view.kind("sql_captured_reference")) == references
    assert verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    with pytest.raises(transport.TransportError) as refused:
        transport.build_project_sql_plan_portable(checked)
    assert refused.value.issue is transport.RuntimeIssue.UNSUPPORTED_VALUE


def _nodes(query, kind):
    """Every realized node of one class, inline let bodies included."""
    found, pending, seen = [], list(query.bodies), set()
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
    ("inner_alias", "other_outer_column", "nullable_drift", "inner_producer"),
)
def test_a_forged_correlated_read_fails_the_independent_verifier(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _correlated(tmp_path, target, "left_join", "preserve_literals")
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    first, second = sorted(
        _nodes(query, rows.SQLCapturedReference),
        key=lambda value: value.original.ref.position,
    )
    assert [first.column.name, second.column.name] == ["c3", "c0"]
    (read,) = _nodes(query, rows.SQLBlockRead)
    inner = read.target.producer
    if mutation == "inner_alias":
        # A valid alias of the same statement: the inline let's own scan.
        changes = [(first, "scope", inner.scan.body.scan.symbol)]
    elif mutation == "other_outer_column":
        changes = [(first, "column", second.column)]
    elif mutation == "nullable_drift":
        changes = [
            (
                second,
                "realization",
                dataclasses.replace(second.realization, nullable=True),
            )
        ]
    else:
        changes = [(read.target, "producer", inner.scan.body)]
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
@pytest.mark.parametrize("mutation", ("correlation_to_inner", "inline_to_cte"))
def test_forged_correlated_bytes_fail_the_byte_verifier(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _correlated(tmp_path, target, "where", "preserve_literals")
    artifact = outcome.artifact
    assert artifact is not None
    q = '"' if target == "postgres" else "`"
    sql = artifact.rendered.sql.decode()
    if mutation == "correlation_to_inner":
        corrupted = sql.replace(
            f"= {q}s1{q}.{q}key value{q})", f"= {q}s0{q}.{q}key value{q})"
        )
    else:
        corrupted = sql.replace(
            f"FROM (SELECT {q}t1{q}", f"FROM {q}p0{q} AS (SELECT {q}t1{q}"
        )
    assert corrupted != sql
    changed = dataclasses.replace(artifact.rendered, sql=corrupted.encode("utf-8"))
    assert not verify_row_bytes(artifact.ast, changed)
    assert not verify_project_sql_emission(
        dataclasses.replace(artifact, rendered=changed), artifact.request
    ).verified


# Lets are reused and read forward (Phase70 S05): a let with capture lines may
# read a chain of capture-free lets written after it, one of them also read by
# the declaration body, or a let grouped by a computed key (S05g). Those stay
# top-level CTEs emitted once; only the capturing let is inline, and native
# placeholders follow the text, the inline let's own literal included.
CORRELATED_CHAINS = {
    "forward_chain": """query result:
    let m:
        capture lhs
        from others
        where others.key == lhs.key and others.id > 3
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
    where exists m and exists base
    select:
        a = lhs.id
""",
    "computed_key": """query result:
    let m:
        capture lhs
        from buckets
        where buckets.bucket == lhs.key
        select:
            bucket
    let buckets:
        from rhs
        let:
            bucket = 1 if key > 1 else 0
        group by:
            bucket
        select:
            bucket
            n = count()
    from lhs
    where exists m
    select:
        a = lhs.id
""",
}
CORRELATED_CHAIN_SQL = {
    ("forward_chain", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", "s0"."key value" '
        'AS "c1" FROM "public"."phase66 rhs é" AS "s0"), "p1" ("c0", "c1") AS '
        '(SELECT "s1"."c0" AS "c0", "s1"."c1" AS "c1" FROM "p0" AS "s1" WHERE '
        '("s1"."c0" > CAST($1 AS pg_catalog.int8))), "p2" ("c0", "c1") AS '
        '(SELECT "t2"."c0" AS "c0", "t2"."c1" AS "c1" FROM "p1" AS "t2"), '
        '"p3" ("c0", "c1") AS (SELECT "s3"."order.id" AS "c0", "s3"."key value" '
        'AS "c1" FROM "public"."phase66 lhs é" AS "s3" WHERE (EXISTS (SELECT '
        '1 FROM (SELECT "t4"."c0" AS "c0" FROM (SELECT "s2"."c0" AS "c0", '
        '"s2"."c1" AS "c1" FROM "p2" AS "s2" WHERE (("s2"."c1" = "s3"."key value") '
        'AND ("s2"."c0" > CAST($2 AS pg_catalog.int8)))) AS "t4") AS "e0") '
        'AND EXISTS (SELECT 1 FROM "p0" AS "e1"))) SELECT "t6"."c0" AS "a" '
        'FROM "p3" AS "t6"'
    ),
    ("forward_chain", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` "
        "AS `c1` FROM `phase66`.`phase66 rhs é` AS `s0`), `p1` (`c0`, `c1`) "
        "AS (SELECT `s1`.`c0` AS `c0`, `s1`.`c1` AS `c1` FROM `p0` AS `s1` "
        "WHERE (`s1`.`c0` > CAST(? AS SIGNED))), `p2` (`c0`, `c1`) AS (SELECT "
        "`t2`.`c0` AS `c0`, `t2`.`c1` AS `c1` FROM `p1` AS `t2`), `p3` (`c0`, "
        "`c1`) AS (SELECT `s3`.`order.id` AS `c0`, `s3`.`key value` AS `c1` "
        "FROM `phase66`.`phase66 lhs é` AS `s3` WHERE (EXISTS (SELECT 1 FROM "
        "(SELECT `t4`.`c0` AS `c0` FROM (SELECT `s2`.`c0` AS `c0`, `s2`.`c1` "
        "AS `c1` FROM `p2` AS `s2` WHERE ((`s2`.`c1` = `s3`.`key value`) AND "
        "(`s2`.`c0` > CAST(? AS SIGNED)))) AS `t4`) AS `e0`) AND EXISTS "
        "(SELECT 1 FROM `p0` AS `e1`))) SELECT `t6`.`c0` AS `a` FROM `p3` AS "
        "`t6`"
    ),
    ("computed_key", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1", (CASE WHEN ("s0"."key value" > CAST($1 AS '
        "pg_catalog.int8)) THEN CAST($2 AS pg_catalog.int8) ELSE CAST($3 AS "
        'pg_catalog.int8) END) AS "c2" FROM "public"."phase66 rhs é" AS '
        '"s0"), "p1" ("c0", "c1") AS (SELECT "t1"."c2" AS "c0", COUNT(*) AS '
        '"c1" FROM "p0" AS "t1" GROUP BY "t1"."c2"), "p2" ("c0", "c1") AS '
        '(SELECT "t2"."c0" AS "c0", "t2"."c1" AS "c1" FROM "p1" AS "t2"), '
        '"p3" ("c0", "c1") AS (SELECT "s2"."order.id" AS "c0", "s2"."key value" '
        'AS "c1" FROM "public"."phase66 lhs é" AS "s2" WHERE EXISTS (SELECT 1 '
        'FROM (SELECT "t4"."c0" AS "c0" FROM (SELECT "s1"."c0" AS "c0", '
        '"s1"."c1" AS "c1" FROM "p2" AS "s1" WHERE ("s1"."c0" = "s2"."key value")) '
        'AS "t4") AS "e0")) SELECT "t6"."c0" AS "a" FROM "p3" AS "t6"'
    ),
    ("computed_key", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`) AS (SELECT `s0`.`order.id` AS `c0`, "
        "`s0`.`key value` AS `c1`, (CASE WHEN (`s0`.`key value` > CAST(? AS "
        "SIGNED)) THEN CAST(? AS SIGNED) ELSE CAST(? AS SIGNED) END) AS `c2` "
        "FROM `phase66`.`phase66 rhs é` AS `s0`), `p1` (`c0`, `c1`) AS "
        "(SELECT `t1`.`c2` AS `c0`, COUNT(*) AS `c1` FROM `p0` AS `t1` GROUP "
        "BY `t1`.`c2`), `p2` (`c0`, `c1`) AS (SELECT `t2`.`c0` AS `c0`, "
        "`t2`.`c1` AS `c1` FROM `p1` AS `t2`), `p3` (`c0`, `c1`) AS (SELECT "
        "`s2`.`order.id` AS `c0`, `s2`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 lhs é` AS `s2` WHERE EXISTS (SELECT 1 FROM "
        "(SELECT `t4`.`c0` AS `c0` FROM (SELECT `s1`.`c0` AS `c0`, `s1`.`c1` "
        "AS `c1` FROM `p2` AS `s1` WHERE (`s1`.`c0` = `s2`.`key value`)) AS "
        "`t4`) AS `e0`)) SELECT `t6`.`c0` AS `a` FROM `p3` AS `t6`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(CORRELATED_CHAINS))
def test_a_capturing_let_reads_lets_that_read_lets(
    tmp_path: Path, target: str, shape: str
) -> None:
    item = probe.join_witness(
        target, CORRELATED_CHAINS[shape], policy="bind_safe_literals"
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == CORRELATED_CHAIN_SQL[shape, target]
    assert document["sql"].count("EXISTS (SELECT 1 FROM (SELECT ") == 1
    assert outcome.artifact is not None
    count = 2 if shape == "forward_chain" else 3
    assert [
        (use.ordinal, use.server_index) for use in outcome.artifact.parameter_uses
    ] == [(n, n + 1) for n in range(count)]


# A let with capture lines may read a relation whose columns are known only
# after completion (a typed VALUES body, a set or an authored JOIN, read
# through a let): its WHERE and SELECT read the captured fields once those
# columns are, and the relation it reads stays a top-level CTE.
CORRELATED_OWN_FROM = {
    "own_from_values": """query result:
    let s:
        values(n: Int not null, k: Int nullable):
            1, 7
            2, null
    let m:
        capture lhs
        from s
        where s.n <= lhs.id and s.k != 3
        select:
            n
    from lhs
    where exists m
    select:
        a = lhs.id
""",
    "own_from_set": """query result:
    let s:
        union all:
            from lhs
            from rhs
    let m:
        capture lhs
        from s
        where s.id == lhs.id and s.key > 3
        select:
            id
    from lhs
    where exists m
    select:
        a = lhs.id
""",
    "own_from_join": """query result:
    let s:
        from lhs
        inner join rhs as r:
            from lhs
            on r.id == lhs.id
        select:
            id = lhs.id
            k = r.key
    let m:
        capture lhs
        from s
        where s.k == lhs.key and s.id > 3
        select:
            id
    from lhs
    where exists m
    select:
        a = lhs.id
""",
}
CORRELATED_OWN_FROM_SQL = {
    ("own_from_values", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (VALUES (CAST(1 AS pg_catalog.int8), '
        "CAST(7 AS pg_catalog.int8)), (CAST(2 AS pg_catalog.int8), "
        'CAST(NULL AS pg_catalog.int8))), "p1" ("c0", "c1") AS (SELECT '
        '"s1"."order.id" AS "c0", "s1"."key value" AS "c1" FROM '
        '"public"."phase66 lhs é" AS "s1" WHERE EXISTS (SELECT 1 FROM '
        '(SELECT "t1"."c0" AS "c0" FROM (SELECT "s0"."c0" AS "c0", '
        '"s0"."c1" AS "c1" FROM "p0" AS "s0" WHERE (("s0"."c0" <= '
        '"s1"."order.id") AND ("s0"."c1" <> CAST($1 AS pg_catalog.int8)))) '
        'AS "t1") AS "e0")) SELECT "t3"."c0" AS "a" FROM "p1" AS "t3"'
    ),
    ("own_from_values", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (VALUES ROW(CAST(1 AS SIGNED), CAST(7 AS "
        "SIGNED)), ROW(CAST(2 AS SIGNED), CAST(NULL AS SIGNED))), `p1` "
        "(`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, `s1`.`key value` "
        "AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` WHERE EXISTS "
        "(SELECT 1 FROM (SELECT `t1`.`c0` AS `c0` FROM (SELECT `s0`.`c0` AS "
        "`c0`, `s0`.`c1` AS `c1` FROM `p0` AS `s0` WHERE ((`s0`.`c0` <= "
        "`s1`.`order.id`) AND (`s0`.`c1` <> CAST(? AS SIGNED)))) AS `t1`) "
        "AS `e0`)) SELECT `t3`.`c0` AS `a` FROM `p1` AS `t3`"
    ),
    ("own_from_set", "postgres"): (
        'WITH "p0" ("c0", "c1") AS ((SELECT "o0"."order.id" AS "c0", '
        '"o0"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "o0") '
        'UNION ALL (SELECT "o1"."order.id" AS "c0", "o1"."key value" AS '
        '"c1" FROM "public"."phase66 rhs é" AS "o1")), "p1" ("c0", "c1") AS '
        '(SELECT "s3"."order.id" AS "c0", "s3"."key value" AS "c1" FROM '
        '"public"."phase66 lhs é" AS "s3" WHERE EXISTS (SELECT 1 FROM '
        '(SELECT "t1"."c0" AS "c0" FROM (SELECT "s2"."c0" AS "c0", '
        '"s2"."c1" AS "c1" FROM "p0" AS "s2" WHERE (("s2"."c0" = '
        '"s3"."order.id") AND ("s2"."c1" > CAST($1 AS pg_catalog.int8)))) '
        'AS "t1") AS "e0")) SELECT "t3"."c0" AS "a" FROM "p1" AS "t3"'
    ),
    ("own_from_set", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS ((SELECT `o0`.`order.id` AS `c0`, "
        "`o0`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `o0`) "
        "UNION ALL (SELECT `o1`.`order.id` AS `c0`, `o1`.`key value` AS "
        "`c1` FROM `phase66`.`phase66 rhs é` AS `o1`)), `p1` (`c0`, `c1`) "
        "AS (SELECT `s3`.`order.id` AS `c0`, `s3`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 lhs é` AS `s3` WHERE EXISTS (SELECT 1 FROM "
        "(SELECT `t1`.`c0` AS `c0` FROM (SELECT `s2`.`c0` AS `c0`, "
        "`s2`.`c1` AS `c1` FROM `p0` AS `s2` WHERE ((`s2`.`c0` = "
        "`s3`.`order.id`) AND (`s2`.`c1` > CAST(? AS SIGNED)))) AS `t1`) AS "
        "`e0`)) SELECT `t3`.`c0` AS `a` FROM `p1` AS `t3`"
    ),
    ("own_from_join", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS '
        '"c0", "m0"."key value" AS "c1", "m1"."order.id" AS "c2", "m1"."key '
        'value" AS "c3" FROM "public"."phase66 lhs é" AS "m0" INNER JOIN '
        '"public"."phase66 rhs é" AS "m1" ON ("m1"."order.id" = '
        '"m0"."order.id")), "p1" ("c0", "c1") AS (SELECT "t0"."c0" AS "c0", '
        '"t0"."c3" AS "c1" FROM "p0" AS "t0"), "p2" ("c0", "c1") AS (SELECT '
        '"s3"."order.id" AS "c0", "s3"."key value" AS "c1" FROM '
        '"public"."phase66 lhs é" AS "s3" WHERE EXISTS (SELECT 1 FROM '
        '(SELECT "t2"."c0" AS "c0" FROM (SELECT "s2"."c0" AS "c0", '
        '"s2"."c1" AS "c1" FROM "p1" AS "s2" WHERE (("s2"."c1" = "s3"."key '
        'value") AND ("s2"."c0" > CAST($1 AS pg_catalog.int8)))) AS "t2") '
        'AS "e0")) SELECT "t4"."c0" AS "a" FROM "p2" AS "t4"'
    ),
    ("own_from_join", "mysql"): (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `m0`.`order.id` AS "
        "`c0`, `m0`.`key value` AS `c1`, `m1`.`order.id` AS `c2`, `m1`.`key "
        "value` AS `c3` FROM `phase66`.`phase66 lhs é` AS `m0` INNER JOIN "
        "`phase66`.`phase66 rhs é` AS `m1` ON (`m1`.`order.id` = "
        "`m0`.`order.id`)), `p1` (`c0`, `c1`) AS (SELECT `t0`.`c0` AS `c0`, "
        "`t0`.`c3` AS `c1` FROM `p0` AS `t0`), `p2` (`c0`, `c1`) AS (SELECT "
        "`s3`.`order.id` AS `c0`, `s3`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 lhs é` AS `s3` WHERE EXISTS (SELECT 1 FROM "
        "(SELECT `t2`.`c0` AS `c0` FROM (SELECT `s2`.`c0` AS `c0`, "
        "`s2`.`c1` AS `c1` FROM `p1` AS `s2` WHERE ((`s2`.`c1` = `s3`.`key "
        "value`) AND (`s2`.`c0` > CAST(? AS SIGNED)))) AS `t2`) AS `e0`)) "
        "SELECT `t4`.`c0` AS `a` FROM `p2` AS `t4`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(CORRELATED_OWN_FROM))
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_capturing_let_reads_a_relation_known_after_completion(
    tmp_path: Path, target: str, shape: str, policy: str
) -> None:
    item = probe.join_witness(target, CORRELATED_OWN_FROM[shape], policy=policy)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert document["status"] == "VERIFIED", document
    expected = CORRELATED_OWN_FROM_SQL[shape, target]
    if policy == "preserve_literals":
        expected = expected.replace("CAST($1 AS", "CAST(3 AS").replace(
            "CAST(? AS", "CAST(3 AS"
        )
    assert document["sql"] == expected
    assert document["sql"].count("EXISTS (SELECT 1 FROM (SELECT ") == 1
    assert probe.decode_public(raw) == document


# An entry query with parameters may also read a table whose let has capture
# lines (its own lets read the header too: see below). The
# inline let's own literal renders in that table's CTE before the parameter,
# which PostgreSQL reuses ($2) and MySQL repeats (?).
PARAMETER_OVER_CAPTURE = """table t:
    let m:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > 5
        select:
            id
    from lhs
    where exists m
    select:
        id
        key
query result(cut: Int not null):
    from t
    where id > cut and key != cut
    select:
        a = id
"""
PARAMETER_OVER_CAPTURE_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", "s1"."key value" '
        'AS "c1" FROM "public"."phase66 lhs é" AS "s1" WHERE EXISTS (SELECT 1 '
        'FROM (SELECT "t1"."c0" AS "c0" FROM (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0" WHERE '
        '(("s0"."key value" = "s1"."key value") AND ("s0"."order.id" > '
        'CAST($1 AS pg_catalog.int8)))) AS "t1") AS "e0")), "p1" ("c0", "c1") '
        'AS (SELECT "t3"."c0" AS "c0", "t3"."c1" AS "c1" FROM "p0" AS "t3"), '
        '"p2" ("c0", "c1") AS (SELECT "s2"."c0" AS "c0", "s2"."c1" AS "c1" '
        'FROM "p1" AS "s2" WHERE (("s2"."c0" > CAST($2 AS pg_catalog.int8)) '
        'AND ("s2"."c1" <> CAST($2 AS pg_catalog.int8)))) SELECT "t5"."c0" AS '
        '"a" FROM "p2" AS "t5"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, `s1`.`key value` "
        "AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` WHERE EXISTS (SELECT "
        "1 FROM (SELECT `t1`.`c0` AS `c0` FROM (SELECT `s0`.`order.id` AS "
        "`c0`, `s0`.`key value` AS `c1` FROM `phase66`.`phase66 rhs é` AS "
        "`s0` WHERE ((`s0`.`key value` = `s1`.`key value`) AND "
        "(`s0`.`order.id` > CAST(? AS SIGNED)))) AS `t1`) AS `e0`)), `p1` "
        "(`c0`, `c1`) AS (SELECT `t3`.`c0` AS `c0`, `t3`.`c1` AS `c1` FROM "
        "`p0` AS `t3`), `p2` (`c0`, `c1`) AS (SELECT `s2`.`c0` AS `c0`, "
        "`s2`.`c1` AS `c1` FROM `p1` AS `s2` WHERE ((`s2`.`c0` > CAST(? AS "
        "SIGNED)) AND (`s2`.`c1` <> CAST(? AS SIGNED)))) SELECT `t5`.`c0` AS "
        "`a` FROM `p2` AS `t5`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_an_entry_query_with_parameters_reads_a_table_with_a_capturing_let(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(
        target, PARAMETER_OVER_CAPTURE, policy="bind_safe_literals"
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == PARAMETER_OVER_CAPTURE_SQL[target]
    assert outcome.artifact is not None
    assert [
        (use.ordinal, use.server_index) for use in outcome.artifact.parameter_uses
    ] == (
        [(0, 1), (1, 2), (2, 2)] if target == "postgres" else [(0, 1), (1, 2), (2, 3)]
    )


# Phase70 S11 x S10: a let with capture lines reads the entry query's header
# like any other let of it. The read renders inside the EXISTS subquery and
# takes its placeholder in rendering order with the bind-safe slots:
# PostgreSQL reuses `$1` for `cut`, MySQL writes one `?` per read.
HEADER_IN_CAPTURE = """query result(cut: Int not null, hi: Int nullable):
    let m:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > cut and rhs.id != 100
        select:
            id
    from lhs
    where exists m and lhs.id < hi and lhs.id != 200
    select:
        a = lhs.id
        b = cut
"""
HEADER_IN_CAPTURE_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", "s1"."key '
        'value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" WHERE ((EXISTS '
        '(SELECT 1 FROM (SELECT "t1"."c0" AS "c0" FROM (SELECT "s0"."order.id" AS '
        '"c0", "s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE ((("s0"."key value" = "s1"."key value") AND ("s0"."order.id" > '
        'CAST($1 AS pg_catalog.int8))) AND ("s0"."order.id" <> CAST($2 AS '
        'pg_catalog.int8)))) AS "t1") AS "e0") AND ("s1"."order.id" < CAST($3 AS '
        'pg_catalog.int8))) AND ("s1"."order.id" <> CAST($4 AS '
        'pg_catalog.int8)))) SELECT "t3"."c0" AS "a", CAST($1 AS pg_catalog.int8) '
        'AS "b" FROM "p0" AS "t3"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, `s1`.`key "
        "value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` WHERE ((EXISTS "
        "(SELECT 1 FROM (SELECT `t1`.`c0` AS `c0` FROM (SELECT `s0`.`order.id` AS "
        "`c0`, `s0`.`key value` AS `c1` FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE (((`s0`.`key value` = `s1`.`key value`) AND (`s0`.`order.id` > "
        "CAST(? AS SIGNED))) AND (`s0`.`order.id` <> CAST(? AS SIGNED)))) AS "
        "`t1`) AS `e0`) AND (`s1`.`order.id` < CAST(? AS SIGNED))) AND "
        "(`s1`.`order.id` <> CAST(? AS SIGNED)))) SELECT `t3`.`c0` AS `a`, CAST(? "
        "AS SIGNED) AS `b` FROM `p0` AS `t3`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_a_capturing_let_reads_the_entry_query_header(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(target, HEADER_IN_CAPTURE, policy="bind_safe_literals")
    checked, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == HEADER_IN_CAPTURE_SQL[target]
    assert [
        (u["owner"]["kind"], u["owner"][u["owner"]["kind"]], u["server_index"])
        for u in document["parameter_uses"]
    ] == [
        ("parameter", 0, 1),
        ("slot", 0, 2),
        ("parameter", 1, 3),
        ("slot", 1, 4),
        ("parameter", 0, 1 if target == "postgres" else 5),
    ]
    assert probe.decoded_arguments(probe.decode_public(raw), {"cut": 3, "hi": 7}) == (
        (3, 100, 7, 200) if target == "postgres" else (3, 100, 7, 200, 3)
    )
    # The let's read belongs to the plan: a well-formed swap of it to the
    # other header entry is refused by the plan verifier.
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    (read,) = [
        e
        for e in plan.expressions
        if type(e) is ProjectSQLParameterRead
        and e.site.owner is not checked.selected_owner
    ]
    object.__setattr__(read, "parameter", plan.parameters[1])
    assert not verify_project_sql_plan(
        plan,
        checked.completed,
        checked.analysis_bundle,
        checked.selected_owner,
        literal_policy=checked.literal_policy,
    ).verified
