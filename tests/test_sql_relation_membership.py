"""Closed `[not] in` relation reads: three-valued membership in one whole block.

`v in r` compares `v` with the one output column of the relation `r` through
an expression block use of its owner, never one of the owner's FROM, JOIN or
set inputs. It keeps the three-valued logic of the literal-list `in` (NULL for
a NULL left value over a non-empty relation and for a NULL candidate without a
match), is never folded into literal options, SEMI/ANTI JOIN or COALESCE, and
reads `r` as a top-level CTE or a qualified source, so the LIMIT of a closed
relation stays inside its own CTE and no `IN (... LIMIT ...)` shape exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import _pietto_sql_emission as probe
from pietto._project import project_sql_emission_portable as portable
from pietto._project import project_sql_emission_pure_boundary as pure
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_postgres_source_assurance import qualification_roots
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_ast import RowValueColumn
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)
from pietto._project.project_sql_plan import ProjectSQLPlan

TARGETS = ("postgres", "mysql")
LIMITED = """query result:
    let picked:
        from rhs
        select:
            id
        order by:
            id
        limit 2
    from lhs
    where key not in picked
    select:
        a = lhs.id
        f = id in keys
query keys:
    from rhs
    select:
        key
"""
SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", '
        '"s0"."order.id" AS "c1" FROM "public"."phase66 rhs é" AS "s0"), '
        '"p1" ("c0") AS (SELECT "t0"."c0" AS "c0" FROM "p0" AS "t0" '
        'ORDER BY "t0"."c1" ASC LIMIT 2), '
        '"p2" ("c0") AS (SELECT "s2"."key value" AS "c0" '
        'FROM "public"."phase66 rhs é" AS "s2"), '
        '"p3" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
        'WHERE ("s1"."key value" NOT IN (SELECT "e0"."c0" FROM "p1" AS "e0"))) '
        'SELECT "t3"."c0" AS "a", '
        '("t3"."c0" IN (SELECT "e1"."c0" FROM "p2" AS "e1")) AS "f" '
        'FROM "p3" AS "t3"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`order.id` AS `c0`, "
        "`s0`.`order.id` AS `c1` FROM `phase66`.`phase66 rhs é` AS `s0`), "
        "`p1` (`c0`) AS (SELECT `t0`.`c0` AS `c0` FROM `p0` AS `t0` "
        "ORDER BY `t0`.`c1` ASC LIMIT 2), "
        "`p2` (`c0`) AS (SELECT `s2`.`key value` AS `c0` "
        "FROM `phase66`.`phase66 rhs é` AS `s2`), "
        "`p3` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, "
        "`s1`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` "
        "WHERE (`s1`.`key value` NOT IN (SELECT `e0`.`c0` FROM `p1` AS `e0`))) "
        "SELECT `t3`.`c0` AS `a`, "
        "(`t3`.`c0` IN (SELECT `e1`.`c0` FROM `p2` AS `e1`)) AS `f` "
        "FROM `p3` AS `t3`"
    ),
}
ONE = """shape One:
    id: Int not null
source ones: One is {target}.table("ones")
query result:
    from lhs
    where id not in ones
    select:
        a = lhs.id
"""
ONE_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s0" '
        'WHERE ("s0"."order.id" NOT IN (SELECT "e0"."one id" '
        'FROM "public"."ones table" AS "e0"))) '
        'SELECT "t1"."c0" AS "a" FROM "p0" AS "t1"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`order.id` AS `c0`, "
        "`s0`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s0` "
        "WHERE (`s0`.`order.id` NOT IN (SELECT `e0`.`one id` "
        "FROM `phase66`.`ones table` AS `e0`))) "
        "SELECT `t1`.`c0` AS `a` FROM `p0` AS `t1`"
    ),
}
IDS = "query ids:\n    from rhs\n    select:\n        id\n"


def _emit(tmp_path: Path, target: str, body: str, *, contract=None, policy=None):
    item = probe.join_witness(target, body, policy=policy or "preserve_literals")
    return probe.build_case(
        tmp_path, item["source"], contract or item["contract"], item["policy"]
    )


def _one_source(tmp_path: Path, target: str):
    item = probe.join_witness(target, ONE.format(target=target))
    contract = json.loads(item["contract"])
    one = json.loads(json.dumps(contract["sources"][0]))
    one["selector"]["name"] = "ones"
    one["relation"]["name"] = "ones table"
    one["fields"] = one["fields"][:1]
    one["fields"][0]["column"] = "one id"
    contract["sources"].append(one)
    return probe.build_case(
        tmp_path, item["source"], json.dumps(contract), item["policy"]
    )


def _observed(artifact) -> None:
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    decoded = pure.parse_emission_observation(observed.canonical_bytes)
    assert decoded.status is pure.Status.OK, decoded
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds


def _blocked(outcome):
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "BLOCKED" and "sql" not in document
    return [
        (
            b["code"],
            b["subject"]["detail"],
            None if b["location"] is None else b["location"]["line"],
            None if b["location"] is None else b["location"]["column"],
        )
        for b in document["blockers"]
    ]


def _block_reads(artifact):
    query = artifact.ast
    values = [
        *(
            column.value
            for body in query.bodies
            for column in body.columns
            if type(column) is RowValueColumn
        ),
        *(
            body.predicate.value
            for body in query.bodies
            if getattr(body, "predicate", None) is not None
        ),
    ]
    return [
        node
        for value in values
        for node in rows.value_nodes(value)
        if type(node) is rows.SQLBlockRead
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_membership_reads_emit_in_subqueries_over_top_level_ctes(
    tmp_path: Path, target: str
) -> None:
    checked, outcome = _emit(tmp_path, target, LIMITED)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == SQL[target]
    # The closed LIMIT stays in its own CTE; no IN subquery carries a LIMIT.
    assert document["sql"].count("LIMIT 2") == 1
    assert all(
        "LIMIT" not in part.split(")")[0] for part in document["sql"].split(" IN (")[1:]
    )
    assert [
        (c["label"], c["logical_type"]["name"], c["nullable"])
        for c in document["columns"]
    ] == [("a", "Int", False), ("f", "Bool", True)]
    assert outcome.artifact is not None
    _observed(outcome.artifact)


@pytest.mark.parametrize("target", TARGETS)
def test_membership_is_three_valued_nullable_and_never_folded(
    tmp_path: Path, target: str
) -> None:
    checked, outcome = _emit(tmp_path, target, LIMITED)
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    reads = [e for e in plan.expressions if type(e) is row.ProjectSQLRelationMembership]
    # Conservatively nullable, even for a non-null left value over a non-null
    # column (`id in keys` reads the nullable `key`; `key not in picked` the
    # non-null `id`): three-valued membership is never proven non-NULL.
    assert [
        (
            e.expression.negated,
            e.value_type.resolved_type.name,
            e.value_type.nullability.value,
        )
        for e in reads
    ] == [(True, "Bool", "nullable"), (False, "Bool", "nullable")]
    assert [e.use for e in reads] == [u.ref for u in plan.expression_block_uses]
    assert [u.edge.column for u in plan.expression_block_uses] == [0, 0]
    assert not any(type(e) is row.ProjectSQLMembership for e in plan.expressions)
    artifact = outcome.artifact
    assert artifact is not None
    found = _block_reads(artifact)
    assert sorted((r.kind, r.realization.nullable) for r in found) == [
        ("in", True),
        ("not_in", True),
    ]
    sql = artifact.rendered.sql.decode()
    assert "COALESCE" not in sql and "EXISTS" not in sql and " JOIN " not in sql
    generated = [r.kind for r in artifact.generated_requirements]
    assert generated.count("relation_membership") == 2


@pytest.mark.parametrize("target", TARGETS)
def test_a_null_left_value_takes_the_read_column_type(
    tmp_path: Path, target: str
) -> None:
    """A bare NULL compares with the one known column like a NULL in a literal
    list, and is rendered as NULL, never folded."""
    _, outcome = _emit(
        tmp_path,
        target,
        IDS + "query result:\n    from lhs\n    where null in ids\n    select:\n"
        "        a = lhs.id\n        f = null not in ids\n",
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    q = '"' if target == "postgres" else "`"
    sql = document["sql"].replace(q, "")
    assert "WHERE (NULL IN (SELECT e0.c0 FROM p0 AS e0))" in sql
    assert "(NULL NOT IN (SELECT e1.c0 FROM p0 AS e1)) AS f" in sql
    assert [
        (c["label"], c["logical_type"]["name"], c["nullable"])
        for c in document["columns"]
    ] == [("a", "Int", False), ("f", "Bool", True)]


@pytest.mark.parametrize("target", TARGETS)
def test_a_single_column_source_is_read_as_a_qualified_relation(
    tmp_path: Path, target: str
) -> None:
    checked, outcome = _one_source(tmp_path, target)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == ONE_SQL[target]
    artifact = outcome.artifact
    assert artifact is not None
    # Like a JOIN input, the read keeps its physical relation's obligations.
    kinds = [(r.kind, r.rule) for r in artifact.generated_requirements]
    start = kinds.index(("relation_membership", "R11"))
    assert kinds[start : start + 3] == [
        ("relation_membership", "R11"),
        ("qualified_scan", "R01"),
        ("source_representation", "R02"),
    ]
    assert type(checked.plan) is ProjectSQLPlan
    assert [s.declaration.name for s in checked.plan.sources] == ["lhs", "ones"]
    assert "ones table" in [s.name for s in artifact.request.sources]
    _observed(artifact)


@pytest.mark.parametrize("target", TARGETS)
def test_a_source_read_only_through_membership_is_a_statement_source(
    tmp_path: Path, target: str
) -> None:
    body = (
        "query result:\n    let picked:\n        from rhs\n        select:\n"
        "            id\n    from lhs\n    where id in picked\n    select:\n"
        "        a = lhs.id\n"
    )
    checked, outcome = _emit(tmp_path, target, body)
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    assert [s.declaration.name for s in plan.sources] == ["lhs", "rhs"]
    (read,) = plan.expression_block_uses
    assert (
        read.edge.use.consumer.definition.name,
        read.edge.use.target.let_position,
    ) == (
        "result",
        0,
    )
    definitions = {d.ref: d for d in plan.bindings.definitions}
    consumer_inputs = [u for u in plan.input_uses if u.consumer is read.consumer]
    assert [
        definitions[u.producer].entry.owner.definition.name for u in consumer_inputs
    ] == ["lhs"]
    request = outcome.artifact.request
    assert [s.name for s in request.sources] == ["phase66 lhs é", "phase66 rhs é"]
    assert qualification_roots(request.sources, ()) == tuple(
        (s.namespace, s.name) for s in request.sources
    )
    # Without its contract mapping the inner source blocks the statement.
    item = probe.join_witness(target, body)
    contract = json.loads(item["contract"])
    contract["sources"] = contract["sources"][:1]
    _, missing = _emit(
        tmp_path / "missing", target, body, contract=json.dumps(contract)
    )
    assert _blocked(missing) == [
        ("PIE-B1001", "source_mapping_missing", None, None),
        ("PIE-B1001", "source_mapping_missing", 5, 1),
    ]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            # A set's columns are known only after completion, so emission
            # checks its width, pairs its column and leaves a bare NULL
            # untyped like an all-NULL literal list.
            "query u:\n    union all:\n        from rhs\n        from rhs\n"
            "query result:\n    from lhs\n    where id in u\n    select:\n"
            "        a = lhs.id\n",
            [("PIE-B1003", "relation_membership_width_not_one", 12, 5)],
        ),
        (
            "query u:\n    union all:\n        from ids\n        from ids\n"
            + IDS
            + 'query result:\n    from lhs\n    where "a" in u\n'
            "    select:\n        a = lhs.id\n",
            [("PIE-B1003", "membership_type_pair_not_admitted", 16, 5)],
        ),
        (
            "query u:\n    union all:\n        from ids\n        from ids\n"
            + IDS
            + "query result:\n    from lhs\n    where null in u\n"
            "    select:\n        a = lhs.id\n",
            [("PIE-B1003", "expression_evidence_unavailable", 14, 1)],
        ),
    ),
    ids=("set_width", "type_pair", "set_null"),
)
def test_width_and_type_pairs_are_refused_at_the_membership(
    tmp_path: Path, target: str, body: str, expected: list
) -> None:
    _, outcome = _emit(tmp_path, target, body)
    assert _blocked(outcome) == expected


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation", ("kind", "operand", "target", "realization", "rendered_sql")
)
def test_membership_emission_tampering_is_refused(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _emit(tmp_path, target, LIMITED)
    artifact = outcome.artifact
    assert artifact is not None
    request = artifact.request
    assert verify_project_sql_emission(artifact, request).verified
    first, second = sorted(_block_reads(artifact), key=lambda r: r.kind)
    if mutation == "rendered_sql":
        sql = artifact.rendered.sql
        changed = sql.replace(b" NOT IN (", b" IN (", 1)
        assert changed != sql
        object.__setattr__(artifact.rendered, "sql", changed)
        try:
            assert not verify_project_sql_emission(artifact, request).verified
        finally:
            object.__setattr__(artifact.rendered, "sql", sql)
        return
    field, value = {
        # Each forged value is itself well formed: the other read's kind,
        # operand or target, or the existence carrier.
        "kind": ("kind", second.kind),
        "operand": ("operands", second.operands),
        "target": ("target", second.target),
        "realization": ("realization", rows._bool(target, False)),
    }[mutation]
    original = getattr(first, field)
    object.__setattr__(first, field, value)
    try:
        assert not verify_project_sql_emission(artifact, request).verified
    finally:
        object.__setattr__(first, field, original)
    assert verify_project_sql_emission(artifact, request).verified


# The read kinds of the stacked slices together: a scalar read as the left
# value of `in`, all three kinds inside a let body that reads earlier lets,
# and reads beside a computed GROUP BY key.
COMBINED = {
    "scalar_in_in": (
        IDS
        + "query top:\n    from rhs\n    select:\n        n = count()\n"
        + "query result:\n    from lhs\n    where scalar top.n in ids\n"
        + "    select:\n        a = lhs.id\n",
        ["(SELECT e1.c0 FROM p2 AS e1) IN (SELECT e0.c0 FROM p0 AS e0)"],
    ),
    "let_bodies": (
        "query result:\n"
        + "    let a:\n        from rhs\n        select:\n            id\n"
        + "    let b:\n        from rhs\n        select:\n            n = count()\n"
        + "    let c:\n        from rhs\n        select:\n            key\n"
        + "    let d:\n        from rhs\n"
        + "        where id in a and exists c and id <= scalar b.n\n"
        + "        select:\n            id\n"
        + "    from lhs\n    where id not in d\n    select:\n        x = lhs.id\n",
        [
            "WHERE (((s3.order.id IN (SELECT e0.c0 FROM p0 AS e0)) AND EXISTS "
            "(SELECT 1 FROM p3 AS e1)) AND (s3.order.id <= (SELECT e2.c0 FROM p2 "
            "AS e2)))",
            "WHERE (s4.order.id NOT IN (SELECT e3.c0 FROM p5 AS e3))",
        ],
    ),
    "computed_group_key": (
        IDS
        + "query top:\n    from rhs\n    select:\n        n = count()\n"
        + "query result:\n    from lhs\n    let:\n        big = id > 5\n"
        + "    where id in ids and exists ids and id <= scalar top.n\n"
        + "    group by:\n        big\n    select:\n        big\n        n = count()\n",
        [
            "WHERE (((t4.c0 IN (SELECT e0.c0 FROM p0 AS e0)) AND EXISTS (SELECT 1 "
            "FROM p0 AS e1)) AND (t4.c0 <= (SELECT e2.c0 FROM p2 AS e2)))",
            "GROUP BY t5.c2",
        ],
    ),
    # Typed VALUES lets, one of them with no row, read by all three kinds.
    "values": (
        "query result:\n"
        + "    let seed:\n        values(rid: Int not null):\n            1\n"
        + "            2\n"
        + "    let top:\n        values(n: Int not null):\n            5\n"
        + "    let none:\n        values(rid: Int not null)\n"
        + "    from lhs\n"
        + "    where id in seed and not exists none and id <= scalar top.n\n"
        + "    select:\n        a = lhs.id\n",
        [
            "WHERE (((s0.order.id IN (SELECT e0.c0 FROM p0 AS e0)) AND (NOT EXISTS "
            "(SELECT 1 FROM p2 AS e1))) AND (s0.order.id <= (SELECT e2.c0 FROM p1 "
            "AS e2)))",
        ],
    ),
}


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", tuple(COMBINED))
def test_read_kinds_combine_in_one_statement_let_bodies_and_grouped_queries(
    tmp_path: Path, shape: str, target: str, policy: str
) -> None:
    body, fragments = COMBINED[shape]
    _, outcome = _emit(tmp_path, target, body, policy=policy)
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    sql = outcome.artifact.rendered.sql.decode()
    plain = sql.replace('"', "").replace("`", "")
    for fragment in fragments:
        assert fragment in plain, (fragment, sql)
    # Each read has its own alias, numbered by its block use.
    reads = _block_reads(outcome.artifact)
    assert sorted(r.target.symbol.name for r in reads) == [
        f"e{n}" for n in range(len(reads))
    ]
    if shape != "values":
        # The private emission observation does not describe VALUES bodies.
        _observed(outcome.artifact)


PARAMETERIZED = (
    "query ids:\n    from rows\n    select:\n        id\n"
    "query top:\n    from rows\n    select:\n        n = count()\n"
    "query result(cutoff: Int not null):\n    from rows\n"
    "    where id >= cutoff and 3 in ids and exists ids and id <= scalar top.n\n"
    "    select:\n        record_id = id\n"
)


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("target", TARGETS)
def test_reads_share_a_parameterized_statement_and_its_placeholder_stream(
    tmp_path: Path, target: str, policy: str
) -> None:
    from _pietto_sql_query_parameters import parameterized_case

    _, outcome = parameterized_case(tmp_path, target, PARAMETERIZED, policy)
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    document = json.loads(serialize_project_sql_emission(outcome))
    # The bind-safe left value of `in` follows the header parameter in one
    # placeholder stream.
    literal = {
        ("postgres", "preserve_literals"): "CAST(3 AS pg_catalog.int8)",
        ("postgres", "bind_safe_literals"): "CAST($2 AS pg_catalog.int8)",
        ("mysql", "preserve_literals"): "CAST(3 AS SIGNED)",
        ("mysql", "bind_safe_literals"): "CAST(? AS SIGNED)",
    }[target, policy]
    plain = document["sql"].replace('"', "").replace("`", "")
    assert f"({literal} IN (SELECT e0.c0 FROM p0 AS e0))" in plain
    assert "EXISTS (SELECT 1 FROM p0 AS e1)" in plain
    assert "(SELECT e2.c0 FROM p2 AS e2)" in plain
    assert [
        (u["owner"]["kind"], u["server_index"]) for u in document["parameter_uses"]
    ] == [("parameter", 1), *([("slot", 2)] if "bind" in policy else [])]


# Phase70 S14: `v [NOT] IN m` of a let with capture lines renders that let
# inline at the read, `(v [NOT] IN (SELECT e<n>.c0 FROM (<let bodies>) AS
# e<n>))`; its correlated references name the reading body's alias, its left
# value renders first and keeps the literal-list three-valued logic.
CORRELATED = {
    "select": """query result:
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > 0
        select:
            id
    from lhs
    where lhs.id > 1
    select:
        a = lhs.id
        f = lhs.id in matched
""",
    # A correlated scalar read is the left value of a correlated NOT IN.
    "where": """query result:
    let same:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > 1
        select:
            id
    let other:
        capture lhs
        from rhs
        where rhs.id == lhs.id and rhs.id > 2
        select:
            id
    from lhs
    where scalar other.id not in same and lhs.id > 3
    select:
        a = lhs.id
""",
}
CORRELATED_SQL = {
    ("select", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
        'WHERE ("s1"."order.id" > CAST($1 AS pg_catalog.int8))) '
        'SELECT "t3"."c0" AS "a", ("t3"."c0" IN (SELECT "e0"."c0" FROM '
        '(SELECT "t1"."c0" AS "c0" FROM (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE (("s0"."key value" = "t3"."c1") AND '
        '("s0"."order.id" > CAST($2 AS pg_catalog.int8)))) AS "t1") AS "e0")) '
        'AS "f" FROM "p0" AS "t3"'
    ),
    ("select", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, "
        "`s1`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` "
        "WHERE (`s1`.`order.id` > CAST(? AS SIGNED))) "
        "SELECT `t3`.`c0` AS `a`, (`t3`.`c0` IN (SELECT `e0`.`c0` FROM "
        "(SELECT `t1`.`c0` AS `c0` FROM (SELECT `s0`.`order.id` AS `c0`, "
        "`s0`.`key value` AS `c1` FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE ((`s0`.`key value` = `t3`.`c1`) AND "
        "(`s0`.`order.id` > CAST(? AS SIGNED)))) AS `t1`) AS `e0`)) "
        "AS `f` FROM `p0` AS `t3`"
    ),
    ("where", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (SELECT "s2"."order.id" AS "c0", '
        '"s2"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s2" '
        'WHERE (((SELECT "e1"."c0" FROM (SELECT "t3"."c0" AS "c0" FROM '
        '(SELECT "s1"."order.id" AS "c0", "s1"."key value" AS "c1" '
        'FROM "public"."phase66 rhs é" AS "s1" '
        'WHERE (("s1"."order.id" = "s2"."order.id") AND '
        '("s1"."order.id" > CAST($1 AS pg_catalog.int8)))) AS "t3") AS "e1") '
        'NOT IN (SELECT "e0"."c0" FROM (SELECT "t1"."c0" AS "c0" FROM '
        '(SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" '
        'FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE (("s0"."key value" = "s2"."key value") AND '
        '("s0"."order.id" > CAST($2 AS pg_catalog.int8)))) AS "t1") AS "e0")) '
        'AND ("s2"."order.id" > CAST($3 AS pg_catalog.int8)))) '
        'SELECT "t5"."c0" AS "a" FROM "p0" AS "t5"'
    ),
    ("where", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s2`.`order.id` AS `c0`, "
        "`s2`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s2` "
        "WHERE (((SELECT `e1`.`c0` FROM (SELECT `t3`.`c0` AS `c0` FROM "
        "(SELECT `s1`.`order.id` AS `c0`, `s1`.`key value` AS `c1` "
        "FROM `phase66`.`phase66 rhs é` AS `s1` "
        "WHERE ((`s1`.`order.id` = `s2`.`order.id`) AND "
        "(`s1`.`order.id` > CAST(? AS SIGNED)))) AS `t3`) AS `e1`) "
        "NOT IN (SELECT `e0`.`c0` FROM (SELECT `t1`.`c0` AS `c0` FROM "
        "(SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` "
        "FROM `phase66`.`phase66 rhs é` AS `s0` "
        "WHERE ((`s0`.`key value` = `s2`.`key value`) AND "
        "(`s0`.`order.id` > CAST(? AS SIGNED)))) AS `t1`) AS `e0`)) "
        "AND (`s2`.`order.id` > CAST(? AS SIGNED)))) "
        "SELECT `t5`.`c0` AS `a` FROM `p0` AS `t5`"
    ),
}
# The literals of each shape in rendering order (outer before inner in SELECT;
# the left value's let before the read let before the later conjunct in WHERE).
CORRELATED_LITERALS = {"select": ("1", "0"), "where": ("2", "1", "3")}


def _preserved(sql: str, literals) -> str:
    for index, literal in enumerate(literals, start=1):
        sql = sql.replace(f"${index} ", f"{literal} ", 1)
        sql = sql.replace("CAST(? AS", f"CAST({literal} AS", 1)
    return sql


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(CORRELATED))
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_correlated_membership_renders_its_let_inline_after_its_value(
    tmp_path: Path, target: str, shape: str, policy: str
) -> None:
    from pietto._project import project_sql_plan_portable as transport

    checked, outcome = _emit(tmp_path, target, CORRELATED[shape], policy=policy)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    expected = CORRELATED_SQL[shape, target]
    literals = CORRELATED_LITERALS[shape]
    if policy == "preserve_literals":
        expected = _preserved(expected, literals)
    assert document["sql"] == expected
    assert " LIMIT " not in document["sql"]
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    kinds = {type(plan.expressions[c.read.position]).__name__ for c in plan.captures}
    assert kinds == (
        {"ProjectSQLRelationMembership"}
        if shape == "select"
        else {"ProjectSQLRelationMembership", "ProjectSQLRelationScalar"}
    )
    # Every let is inline: no CTE but the reading body's own.
    quote = "`" if target == "mysql" else '"'
    assert f"{quote}p1{quote}" not in document["sql"]
    if shape == "select":
        assert [(c["label"], c["nullable"]) for c in document["columns"]] == [
            ("a", False),
            ("f", True),
        ]
    artifact = outcome.artifact
    assert artifact is not None
    kinds_rules = [(r.kind, r.rule) for r in artifact.generated_requirements]
    assert kinds_rules.count(("inline_stage_use", "R11")) == len(plan.captures)
    if policy == "bind_safe_literals":
        assert [(u.ordinal, u.server_index) for u in artifact.parameter_uses] == [
            (i, i + 1) for i in range(len(literals))
        ]
    _observed(artifact)
    with pytest.raises(transport.TransportError) as refused:
        transport.build_project_sql_plan_portable(checked)
    assert refused.value.issue is transport.RuntimeIssue.UNSUPPORTED_VALUE


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation", ("swapped_targets", "other_kind", "inner_producer", "rendered_sql")
)
def test_a_forged_correlated_membership_fails_the_verifiers(
    tmp_path: Path, target: str, mutation: str
) -> None:
    _, outcome = _emit(tmp_path, target, CORRELATED["where"])
    artifact = outcome.artifact
    assert artifact is not None
    request = artifact.request
    assert verify_project_sql_emission(artifact, request).verified
    membership, scalar = sorted(_block_reads(artifact), key=lambda r: r.kind)
    assert (membership.kind, scalar.kind) == ("not_in", "scalar")
    if mutation == "rendered_sql":
        # The let's alias of the other read: a valid alias of the statement.
        sql = artifact.rendered.sql
        q = b'"' if target == "postgres" else b"`"
        changed = sql.replace(
            b"NOT IN (SELECT " + q + b"e0", b"NOT IN (SELECT " + q + b"e1"
        )
        assert changed != sql
        object.__setattr__(artifact.rendered, "sql", changed)
        try:
            assert not verify_project_sql_emission(artifact, request).verified
        finally:
            object.__setattr__(artifact.rendered, "sql", sql)
        return
    # Valid-looking values: the other inline let's target (both read the same
    # row), the membership's other kind, the let's own inner stage body.
    changes = {
        "swapped_targets": [
            (membership, "target", scalar.target),
            (scalar, "target", membership.target),
        ],
        "other_kind": [(membership, "kind", "in")],
        "inner_producer": [
            (membership.target, "producer", membership.target.producer.scan.body)
        ],
    }[mutation]
    originals = [(node, name, getattr(node, name)) for node, name, _ in changes]
    try:
        for node, name, value in changes:
            object.__setattr__(node, name, value)
        assert not verify_project_sql_emission(artifact, request).verified
    finally:
        for node, name, value in originals:
            object.__setattr__(node, name, value)
    assert verify_project_sql_emission(artifact, request).verified


# A let read by `in` or `not in` may read a relation whose columns are known
# only after completion (a set or a typed VALUES body, read through a let); on
# PostgreSQL its ORDER BY and LIMIT wrapper may repeat a JOIN reader's alias,
# since every correlated reference lies inside the derived table it names.
OWN_FROM_MEMBERSHIP = {
    "set_not_in": """query result:
    let s:
        union all:
            from lhs
            from rhs
    let m:
        capture lhs
        from s
        where s.key == lhs.key
        select:
            id
    from lhs
    where lhs.id not in m
    select:
        a = lhs.id
""",
    "values_in": """query result:
    let s:
        values(id: Int not null, key: Int nullable):
            1, 2
            3, null
    let m:
        capture lhs
        from s
        where s.key == lhs.key or s.id > 5
        select:
            id
    from lhs
    select:
        a = lhs.id
        b = lhs.id in m
""",
}
OWN_FROM_MEMBERSHIP_SQL = {
    ("set_not_in", "postgres"): (
        'WITH "p0" ("c0", "c1") AS ((SELECT "o0"."order.id" AS "c0", '
        '"o0"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "o0") '
        'UNION ALL (SELECT "o1"."order.id" AS "c0", "o1"."key value" AS '
        '"c1" FROM "public"."phase66 rhs é" AS "o1")), "p1" ("c0", "c1") AS '
        '(SELECT "s3"."order.id" AS "c0", "s3"."key value" AS "c1" FROM '
        '"public"."phase66 lhs é" AS "s3" WHERE ("s3"."order.id" NOT IN '
        '(SELECT "e0"."c0" FROM (SELECT "t1"."c0" AS "c0" FROM (SELECT '
        '"s2"."c0" AS "c0", "s2"."c1" AS "c1" FROM "p0" AS "s2" WHERE '
        '("s2"."c1" = "s3"."key value")) AS "t1") AS "e0"))) SELECT '
        '"t3"."c0" AS "a" FROM "p1" AS "t3"'
    ),
    ("set_not_in", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS ((SELECT `o0`.`order.id` AS `c0`, "
        "`o0`.`key value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `o0`) "
        "UNION ALL (SELECT `o1`.`order.id` AS `c0`, `o1`.`key value` AS "
        "`c1` FROM `phase66`.`phase66 rhs é` AS `o1`)), `p1` (`c0`, `c1`) "
        "AS (SELECT `s3`.`order.id` AS `c0`, `s3`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 lhs é` AS `s3` WHERE (`s3`.`order.id` NOT IN "
        "(SELECT `e0`.`c0` FROM (SELECT `t1`.`c0` AS `c0` FROM (SELECT "
        "`s2`.`c0` AS `c0`, `s2`.`c1` AS `c1` FROM `p0` AS `s2` WHERE "
        "(`s2`.`c1` = `s3`.`key value`)) AS `t1`) AS `e0`))) SELECT "
        "`t3`.`c0` AS `a` FROM `p1` AS `t3`"
    ),
    ("values_in", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (VALUES (CAST(1 AS pg_catalog.int8), '
        "CAST(2 AS pg_catalog.int8)), (CAST(3 AS pg_catalog.int8), "
        'CAST(NULL AS pg_catalog.int8))) SELECT "s1"."order.id" AS "a", '
        '("s1"."order.id" IN (SELECT "e0"."c0" FROM (SELECT "t1"."c0" AS '
        '"c0" FROM (SELECT "s0"."c0" AS "c0", "s0"."c1" AS "c1" FROM "p0" '
        'AS "s0" WHERE (("s0"."c1" = "s1"."key value") OR ("s0"."c0" > '
        'CAST($1 AS pg_catalog.int8)))) AS "t1") AS "e0")) AS "b" FROM '
        '"public"."phase66 lhs é" AS "s1"'
    ),
    ("values_in", "mysql"): (
        "WITH `p0` (`c0`, `c1`) AS (VALUES ROW(CAST(1 AS SIGNED), CAST(2 AS "
        "SIGNED)), ROW(CAST(3 AS SIGNED), CAST(NULL AS SIGNED))) SELECT "
        "`s1`.`order.id` AS `a`, (`s1`.`order.id` IN (SELECT `e0`.`c0` FROM "
        "(SELECT `t1`.`c0` AS `c0` FROM (SELECT `s0`.`c0` AS `c0`, "
        "`s0`.`c1` AS `c1` FROM `p0` AS `s0` WHERE ((`s0`.`c1` = `s1`.`key "
        "value`) OR (`s0`.`c0` > CAST(? AS SIGNED)))) AS `t1`) AS `e0`)) AS "
        "`b` FROM `phase66`.`phase66 lhs é` AS `s1`"
    ),
}
OWN_FROM_ORDERED = {
    "values_in_ordered": """query result:
    let s:
        values(id: Int not null, key: Int nullable):
            1, 2
            3, null
    let m:
        capture lhs
        from s
        where s.key == lhs.key
        select:
            id
        order by:
            id desc
        limit 1
    from lhs
    inner join rhs as r:
        from lhs
        on r.id == lhs.id
    where lhs.id in m
    select:
        a = lhs.id
""",
}
OWN_FROM_ORDERED_SQL = {
    ("values_in_ordered", "postgres"): (
        'WITH "p0" ("c0", "c1") AS (VALUES (CAST(1 AS pg_catalog.int8), '
        "CAST(2 AS pg_catalog.int8)), (CAST(3 AS pg_catalog.int8), "
        'CAST(NULL AS pg_catalog.int8))), "p1" ("c0", "c1", "c2", "c3") AS '
        '(SELECT "m0"."order.id" AS "c0", "m0"."key value" AS "c1", '
        '"m1"."order.id" AS "c2", "m1"."key value" AS "c3" FROM '
        '"public"."phase66 lhs é" AS "m0" INNER JOIN "public"."phase66 rhs '
        'é" AS "m1" ON ("m1"."order.id" = "m0"."order.id")), "p2" ("c0", '
        '"c1", "c2", "c3") AS (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", '
        '"t0"."c2" AS "c2", "t0"."c3" AS "c3" FROM "p1" AS "t0" WHERE '
        '("t0"."c0" IN (SELECT "e0"."c0" FROM (SELECT "t0"."c0" AS "c0" '
        'FROM (SELECT "t1"."c0" AS "c0", "t1"."c0" AS "c1" FROM (SELECT '
        '"s0"."c0" AS "c0", "s0"."c1" AS "c1" FROM "p0" AS "s0" WHERE '
        '("s0"."c1" = "t0"."c1")) AS "t1") AS "t0" ORDER BY "t0"."c1" DESC '
        'LIMIT 1) AS "e0"))) SELECT "t3"."c0" AS "a" FROM "p2" AS "t3"'
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(OWN_FROM_MEMBERSHIP))
def test_a_membership_read_let_reads_a_relation_known_after_completion(
    tmp_path: Path, target: str, shape: str
) -> None:
    _, outcome = _emit(
        tmp_path, target, OWN_FROM_MEMBERSHIP[shape], policy="bind_safe_literals"
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == OWN_FROM_MEMBERSHIP_SQL[shape, target]


@pytest.mark.parametrize("target", TARGETS)
def test_an_ordered_membership_of_a_join_reader_reads_a_relation_known_later(
    tmp_path: Path, target: str
) -> None:
    _, outcome = _emit(
        tmp_path,
        target,
        OWN_FROM_ORDERED["values_in_ordered"],
        policy="bind_safe_literals",
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    if target == "mysql":
        assert document["status"] == "BLOCKED"
        assert [
            (b["code"], b["subject"]["detail"], b["location"]["line"])
            for b in document["blockers"]
        ] == [("PIE-B1003", "mysql_correlated_order_or_limit_read_not_admitted", 24)]
        return
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == OWN_FROM_ORDERED_SQL["values_in_ordered", target]


# Owner decision 2026-10-15 (D70.05): a correlated `[not] in` of a let ending in
# ORDER BY and LIMIT is PostgreSQL only. The let's result body stays inside the
# read's own derived table, so no IN subquery carries a LIMIT itself:
# `(v [NOT] IN (SELECT e<n>.c0 FROM (... ORDER BY ... LIMIT <n>) AS e<n>))`.
# MySQL emission refuses the read before any SQL exists.
ORDERED = {
    # ORDER BY a field the let does not select (a hidden column), then its own.
    "select": CORRELATED["select"].replace(
        "            id\n    from lhs",
        "            id\n        order by:\n            key desc\n            id\n"
        "        limit 2\n    from lhs",
    ),
    "where": """query result:
    let matched:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id > 2
        select:
            id
        order by:
            id
        limit 2
    from lhs
    where lhs.id not in matched and lhs.id > 3
    select:
        a = lhs.id
""",
}
ORDERED_SQL = {
    "select": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
        'WHERE ("s1"."order.id" > CAST($1 AS pg_catalog.int8))) '
        'SELECT "t3"."c0" AS "a", ("t3"."c0" IN (SELECT "e0"."c0" FROM '
        '(SELECT "t0"."c0" AS "c0" FROM (SELECT "t1"."c0" AS "c0", '
        '"t1"."c1" AS "c1", "t1"."c0" AS "c2" FROM (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE (("s0"."key value" = "t3"."c1") AND '
        '("s0"."order.id" > CAST($2 AS pg_catalog.int8)))) AS "t1") AS "t0" '
        'ORDER BY "t0"."c1" DESC, "t0"."c2" ASC LIMIT 2) AS "e0")) AS "f" '
        'FROM "p0" AS "t3"'
    ),
    "where": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" '
        'WHERE (("s1"."order.id" NOT IN (SELECT "e0"."c0" FROM '
        '(SELECT "t0"."c0" AS "c0" FROM (SELECT "t1"."c0" AS "c0", '
        '"t1"."c0" AS "c1" FROM (SELECT "s0"."order.id" AS "c0", '
        '"s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0" '
        'WHERE (("s0"."key value" = "s1"."key value") AND '
        '("s0"."order.id" > CAST($1 AS pg_catalog.int8)))) AS "t1") AS "t0" '
        'ORDER BY "t0"."c1" ASC LIMIT 2) AS "e0")) AND '
        '("s1"."order.id" > CAST($2 AS pg_catalog.int8)))) '
        'SELECT "t3"."c0" AS "a" FROM "p0" AS "t3"'
    ),
}
# The literals in rendering order and the read's (line, column) in the source.
ORDERED_LITERALS = {"select": ("1", "0"), "where": ("2", "3")}
ORDERED_READ_AT = {"select": (21, 13), "where": (17, 11)}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", sorted(ORDERED))
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_correlated_membership_takes_its_lets_order_and_limit_on_postgres(
    tmp_path: Path, target: str, shape: str, policy: str
) -> None:
    from pietto._project.project_sql_emission_results import RowResultBody

    checked, outcome = _emit(tmp_path, target, ORDERED[shape], policy=policy)
    document = json.loads(serialize_project_sql_emission(outcome))
    if target == "mysql":
        assert (document["status"], document["diagnostics"]) == ("BLOCKED", [])
        assert outcome.artifact is None and "sql" not in document
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
                "mysql_correlated_order_or_limit_read_not_admitted",
                *ORDERED_READ_AT[shape],
            )
        ]
        return
    assert document["status"] == "VERIFIED", document
    expected = ORDERED_SQL[shape]
    if policy == "preserve_literals":
        expected = _preserved(expected, ORDERED_LITERALS[shape])
    assert document["sql"] == expected
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    (capture,) = plan.captures
    assert [
        b.kind.value for b in plan.result_boundaries if b.definition is capture.inner
    ] == ["relation_ordering", "limit"]
    artifact = outcome.artifact
    assert artifact is not None
    (read,) = _block_reads(artifact)
    result = read.target.producer
    assert type(result) is RowResultBody and len(result.columns) == 1
    assert (result.symbol, result.final) == (None, False)
    kinds = [(r.kind, r.rule) for r in artifact.generated_requirements]
    assert kinds.count(("inline_stage_use", "R11")) == 2
    if policy == "bind_safe_literals":
        assert [(u.ordinal, u.server_index) for u in artifact.parameter_uses] == [
            (0, 1),
            (1, 2),
        ]
    assert (
        portable.export_emission_observation(artifact, artifact.request).status
        is portable.ObservationStatus.OUTSIDE_SCHEMA
    )


@pytest.mark.parametrize(
    "mutation", ("limit_value", "dropped_result", "negated", "rendered_limit")
)
def test_a_forged_ordered_membership_fails_the_verifiers(
    tmp_path: Path, mutation: str
) -> None:
    _, outcome = _emit(tmp_path, "postgres", ORDERED["where"])
    artifact = outcome.artifact
    assert artifact is not None
    request = artifact.request
    assert verify_project_sql_emission(artifact, request).verified
    (read,) = _block_reads(artifact)
    result = read.target.producer
    if mutation == "rendered_limit":
        sql = artifact.rendered.sql
        changed = sql.replace(b" LIMIT 2) AS ", b" LIMIT 3) AS ")
        assert changed != sql
        object.__setattr__(artifact.rendered, "sql", changed)
        try:
            assert not verify_project_sql_emission(artifact, request).verified
        finally:
            object.__setattr__(artifact.rendered, "sql", sql)
        return
    # Valid-looking values: another static limit, the let's own projection
    # (one-column reads of it stay well formed) and the other membership kind.
    assert result.limit is not None
    changes = {
        "limit_value": [(result.limit, "value", 3)],
        "dropped_result": [(read.target, "producer", result.scan.body)],
        "negated": [(read, "kind", "in")],
    }[mutation]
    originals = [(node, name, getattr(node, name)) for node, name, _ in changes]
    try:
        for node, name, value in changes:
            object.__setattr__(node, name, value)
        assert not verify_project_sql_emission(artifact, request).verified
    finally:
        for node, name, value in originals:
            object.__setattr__(node, name, value)
    assert verify_project_sql_emission(artifact, request).verified


# Phase70 S11 x S14: a let read by a correlated IN reads the entry query's
# header like any other let of it; its literal slot and reads take their
# placeholders in rendering order.
HEADER_IN_MEMBERSHIP = """query result(cut: Int not null, hi: Int nullable):
    let m:
        capture lhs
        from rhs
        where rhs.key == lhs.key and rhs.id != 100 and rhs.id > cut
        select:
            id
    from lhs
    where lhs.id in m and lhs.id < hi
    select:
        a = lhs.id
"""
HEADER_IN_MEMBERSHIP_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0", "s1"."key '
        'value" AS "c1" FROM "public"."phase66 lhs é" AS "s1" WHERE '
        '(("s1"."order.id" IN (SELECT "e0"."c0" FROM (SELECT "t1"."c0" AS "c0" '
        'FROM (SELECT "s0"."order.id" AS "c0", "s0"."key value" AS "c1" FROM '
        '"public"."phase66 rhs é" AS "s0" WHERE ((("s0"."key value" = "s1"."key '
        'value") AND ("s0"."order.id" <> CAST($1 AS pg_catalog.int8))) AND '
        '("s0"."order.id" > CAST($2 AS pg_catalog.int8)))) AS "t1") AS "e0")) AND '
        '("s1"."order.id" < CAST($3 AS pg_catalog.int8)))) SELECT "t3"."c0" AS '
        '"a" FROM "p0" AS "t3"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s1`.`order.id` AS `c0`, `s1`.`key "
        "value` AS `c1` FROM `phase66`.`phase66 lhs é` AS `s1` WHERE "
        "((`s1`.`order.id` IN (SELECT `e0`.`c0` FROM (SELECT `t1`.`c0` AS `c0` "
        "FROM (SELECT `s0`.`order.id` AS `c0`, `s0`.`key value` AS `c1` FROM "
        "`phase66`.`phase66 rhs é` AS `s0` WHERE (((`s0`.`key value` = `s1`.`key "
        "value`) AND (`s0`.`order.id` <> CAST(? AS SIGNED))) AND (`s0`.`order.id` "
        "> CAST(? AS SIGNED)))) AS `t1`) AS `e0`)) AND (`s1`.`order.id` < CAST(? "
        "AS SIGNED)))) SELECT `t3`.`c0` AS `a` FROM `p0` AS `t3`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_a_membership_read_let_reads_the_entry_query_header(
    tmp_path: Path, target: str
) -> None:
    item = probe.join_witness(target, HEADER_IN_MEMBERSHIP, policy="bind_safe_literals")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == HEADER_IN_MEMBERSHIP_SQL[target]
    assert [
        (u["owner"]["kind"], u["owner"][u["owner"]["kind"]], u["server_index"])
        for u in document["parameter_uses"]
    ] == [("slot", 0, 1), ("parameter", 0, 2), ("parameter", 1, 3)]
    assert probe.decoded_arguments(probe.decode_public(raw), {"cut": 3, "hi": 7}) == (
        100,
        3,
        7,
    )
