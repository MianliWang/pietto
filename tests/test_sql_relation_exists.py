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
from pietto._project.project_sql_emission_ast import SQLRowQuery
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
    verify_row_bytes,
    verify_row_query,
)
from pietto._project.project_postgres_source_assurance import qualification_roots
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_plan import ProjectSQLPlan

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
