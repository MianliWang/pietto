"""JOIN and EXISTS emission, its outer nulling and its public consumer.

Every artifact below is produced by the installed emission path from an ordinary
authored project, and every verdict is taken from the independent public consumer
reading the published bytes. No production builder, realization function or
renderer is called to decide whether a public document is acceptable.
"""

import json
from typing import Any

import pytest

import _pietto_sql_emission as probe
from pietto._project.project_sql_emission import (
    EmissionArtifact,
    EmissionOutcome,
    serialize_project_sql_emission,
)

TARGETS = ("postgres", "mysql")
KINDS = ("cross", "inner", "left", "right", "full", "semi", "anti")
NATIVE = {
    "cross": " CROSS JOIN ",
    "inner": " INNER JOIN ",
    "left": " LEFT JOIN ",
    "right": " RIGHT JOIN ",
    "full": " FULL JOIN ",
}
MEMBERSHIP = {"semi": " WHERE EXISTS (", "anti": " WHERE NOT EXISTS ("}
# A SEMI/ANTI JOIN is written as a JOIN-prefix `[not] any(...)`: before a later
# JOIN it is the hidden SEMI/ANTI JOIN whose membership is under test here.
LATER_JOIN = "    let later = rhs\n    cross join later\n"


def emit(tmp_path, target, body, *, link=False, policy="preserve_literals"):
    """One authored project through parse, completion, plan and emission."""
    item = probe.join_witness(target, body, link=link, policy=policy)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    return outcome


def public(outcome):
    """The independent consumer's verdict over the published bytes alone."""
    return probe.decode_public(serialize_project_sql_emission(outcome))


def document(outcome):
    return json.loads(serialize_project_sql_emission(outcome).decode())


def join_line(kind, predicate="lhs.id == r.id", name="r"):
    """The JOIN of ``name`` of ``kind``; SEMI/ANTI as the JOIN-prefix `[not] any`."""
    if kind in MEMBERSHIP:
        negation = "not " if kind == "anti" else ""
        return (
            f"    where {negation}any({predicate} for {name} in {name})\n" + LATER_JOIN
        )
    condition = "" if kind == "cross" else f" on {predicate}"
    return f"    {kind} join {name}{condition}\n"


def kinds_body(kind, *, predicate="lhs.id == r.id", select="        a = lhs.id\n"):
    return f"""query result:
    from lhs
    let r = rhs
{join_line(kind, predicate)}    select:
{select}"""


def nullability(doc):
    return [(column["label"], column["nullable"]) for column in doc["columns"]]


def requirement_kinds(doc):
    from collections import Counter

    return Counter(item["kind"] for item in doc["requirements"])


# --------------------------------------------------------------------------
# The seven kinds, per target, inside their own approved domains
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", KINDS)
def test_each_join_kind_emits_inside_its_own_approved_domain(tmp_path, target, kind):
    """PostgreSQL admits all seven; MySQL FULL stays a typed non-support."""
    select = (
        "        a = lhs.id\n"
        if kind in MEMBERSHIP
        else "        a = lhs.id\n        b = r.id\n"
    )
    outcome = emit(tmp_path, target, kinds_body(kind, select=select))
    doc = public(outcome)
    if kind == "full" and target == "mysql":
        # R10: a typed non-support with NO usable SQL, never a blanket refusal.
        assert doc["status"] == "BLOCKED"
        assert "sql" not in doc and "columns" not in doc
        assert [item["code"] for item in doc["blockers"]] == ["PIE-B1003"]
        assert (
            doc["blockers"][0]["subject"]["detail"]
            == "mysql_full_join_approved_non_support"
        )
        return
    assert doc["status"] == "VERIFIED"
    if kind in MEMBERSHIP:
        # The existence test is a membership filter, never a JOIN of its own:
        # the one JOIN in the SQL is the later CROSS JOIN.
        assert MEMBERSHIP[kind] in doc["sql"]
        assert doc["sql"].count(" JOIN ") == doc["sql"].count(NATIVE["cross"]) == 1
    else:
        assert NATIVE[kind] in doc["sql"]


@pytest.mark.parametrize("kind", ("left", "right", "inner", "cross", "semi", "anti"))
def test_a_mysql_full_rejection_does_not_refuse_its_neighbours(tmp_path, kind):
    """Only FULL is withheld on MySQL; the neighbouring kinds still emit."""
    select = (
        "        a = lhs.id\n"
        if kind in MEMBERSHIP
        else "        a = lhs.id\n        b = r.id\n"
    )
    assert (
        public(emit(tmp_path, "mysql", kinds_body(kind, select=select)))["status"]
        == "VERIFIED"
    )


# --------------------------------------------------------------------------
# Outer nulling, derived by the consumer from the parsed structure
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_a_left_join_transports_and_nulls_every_right_value_shape(tmp_path, target):
    """C07: a source value, a literal, a computed value and a LET, together."""
    outcome = emit(
        tmp_path,
        target,
        """table prod:
    from rhs
    let step = id + 0
    where id > 0
    select:
        pid = id
        marker = 1
        computed = id + 0
        stepped = step
query result:
    from lhs
    let r = prod
    left join r on lhs.id == r.pid
    select:
        a = lhs.id
        p = r.pid
        m = r.marker
        c = r.computed
        t = r.stepped
""",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert nullability(doc) == [
        ("a", False),
        ("p", True),
        ("m", True),
        ("c", True),
        ("t", True),
    ]
    # One null-extension obligation per published right port, and none for the
    # preserved left: the consumer derives the denominator from the parsed kind.
    assert requirement_kinds(doc)["null_extension"] == 4


@pytest.mark.parametrize("target", TARGETS)
def test_a_right_join_nulls_the_whole_accumulated_left(tmp_path, target):
    outcome = emit(
        tmp_path,
        target,
        """table leftish:
    from lhs
    where id > 0
    select:
        lid = id
query result:
    from leftish
    let r = rhs
    right join r on leftish.lid == r.id
    select:
        a = leftish.lid
        b = r.id
""",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert nullability(doc) == [("a", True), ("b", False)]


_UNMATCHED_HEADER = """shape Row:
    id: Int
    key: Int | None
    row_key = unique(id)
source lhs: Row = {target}.table("lhs")
source rhs: Row = {target}.table("rhs")
relationship link(l: Row, r: Row):
    l.key == r.id
query result:
    from lhs
    let c = rhs
    right join c on link(lhs, c)
    let r = rhs
    {join}
{where}    group by lhs.id
    select:
        lid = lhs.id
        n = count(r.id)
"""


@pytest.mark.parametrize("target", ("postgres",))
@pytest.mark.parametrize(
    ("join", "where", "status"),
    (
        ("cross join r", "", "BLOCKED"),
        ("cross join r", "r.id is None", "VERIFIED"),
        ("cross join r", "lhs.id is not None or r.id is None", "VERIFIED"),
        ("cross join r", "c.id > 5 and c.id < 3", "VERIFIED"),
        ("inner join r on lhs.id == r.id or r.id is None", "", "VERIFIED"),
        ("cross join r", "c.id == 3", "VERIFIED"),
        ("cross join r", "c.id is not None", "BLOCKED"),
        ("cross join r", "c.key == 3", "BLOCKED"),
    ),
)
def test_a_value_that_excludes_unmatched_rows_emits_the_aggregate(
    tmp_path, target, join, where, status
):
    """D-11: an aggregate over a RIGHT JOIN's preserved rows emits VERIFIED
    SQL when that SQL never reads a row that matches no left row twice in a
    group: a never-None field tested `is None`, a vacuous `or` test or
    contradictory bounds (0.1.4 emitted these VERIFIED too), or a key of the
    preserved input held to one value, which leaves one such row. Without
    such a proof the CROSS JOIN repeats those rows in the NULL group and the
    relation stays BLOCKED."""

    source = _UNMATCHED_HEADER.format(
        target=target, join=join, where=f"    where {where}\n" if where else ""
    )
    item = probe.join_witness(target, {"main.pietto": source})
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    doc = public(outcome)
    assert doc["status"] == status
    if status == "VERIFIED":
        assert " RIGHT JOIN " in doc["sql"] and "COUNT(" in doc["sql"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_declared_source_field_keeps_its_own_domain(tmp_path, target):
    """An outer JOIN never rewrites a source declaration to accept itself."""
    outcome = emit(
        tmp_path,
        target,
        kinds_body("left", select="        a = lhs.id\n        j = lhs.key\n"),
    )
    doc = public(outcome)
    # `lhs` is the PRESERVED side, so `key` is nullable only because it was
    # declared `Int | None` -- not because the JOIN nulled anything.
    assert nullability(doc) == [("a", False), ("j", True)]
    assert requirement_kinds(doc)["null_extension"] == 2


# --------------------------------------------------------------------------
# The ON condition's own NULL-rejection, re-derived from the public bytes
# --------------------------------------------------------------------------

NARROWING = (
    # kind, ON predicate, selected right value, expected published nullability
    ("inner", "lhs.key == r.key", "r.key", False),
    ("inner", "lhs.key > r.key", "r.key", False),
    ("inner", "lhs.id == r.id or lhs.key == r.key", "r.key", True),
    ("inner", "lhs.id == r.id and r.key is None", "r.key", True),
    ("inner", "lhs.key + 0 == r.key", "lhs.key", True),
    ("inner", "lhs.key + 0 == r.key", "r.key", False),
    ("left", "lhs.key == r.key", "r.key", True),
    ("right", "lhs.key == r.key", "r.key", True),
    ("semi", "lhs.key == r.key", "lhs.key", True),
    ("anti", "lhs.key == r.key", "lhs.key", True),
)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(("kind", "predicate", "value", "nullable"), NARROWING)
def test_only_a_matched_pairs_condition_narrows_its_own_direct_operands(
    tmp_path, target, kind, predicate, value, nullable
):
    """A conjunct proves its own operands; an OR, a NULL test and a computed
    operand prove nothing, and a preserved side is never narrowed at all."""
    outcome = emit(
        tmp_path,
        target,
        kinds_body(kind, predicate=predicate, select=f"        k = {value}\n"),
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert nullability(doc) == [("k", nullable)]


# --------------------------------------------------------------------------
# Authored literals inside the ON condition, under both policies
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_a_preserved_on_literal_is_emitted_inline_with_no_argument(tmp_path, target):
    outcome = emit(
        tmp_path, target, kinds_body("inner", predicate="lhs.id == r.id and r.id > 7")
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert probe.decoded_arguments(doc) == ()
    assert doc["fixed_values"] == []


@pytest.mark.parametrize("target", TARGETS)
def test_a_bound_on_literal_becomes_one_ordered_native_argument(tmp_path, target):
    outcome = emit(
        tmp_path,
        target,
        kinds_body("inner", predicate="lhs.id == r.id and r.id > 7"),
        policy="bind_safe_literals",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert probe.decoded_arguments(doc) == (7,)
    marker = "$1" if target == "postgres" else "?"
    assert doc["sql"].count(marker) == 1


@pytest.mark.parametrize("target", TARGETS)
def test_two_bound_on_literals_keep_their_authored_argument_order(tmp_path, target):
    outcome = emit(
        tmp_path,
        target,
        kinds_body("inner", predicate="lhs.id > 3 and r.id > 7"),
        policy="bind_safe_literals",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert probe.decoded_arguments(doc) == (3, 7)


# --------------------------------------------------------------------------
# Relationship calls: the predicate they stand for, refinement, and endpoints
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("inner", "left"))
def test_a_relationship_call_emits_its_predicate_as_the_match_condition(
    tmp_path, target, kind
):
    """A shape-typed relationship is a row predicate: its call is the JOIN's one
    match condition and emits the SQL of the predicate it stands for. Only the
    retired source-bound VIA declared a separate relationship equality."""
    called, written = (
        public(
            emit(tmp_path / label, target, kinds_body(kind, predicate=on), link=True)
        )
        for label, on in (("call", "link(lhs, r)"), ("on", "lhs.id == r.id"))
    )
    assert called["status"] == written["status"] == "VERIFIED"
    assert called["sql"] == written["sql"]
    assert requirement_kinds(called)["match_condition"] == 1
    assert requirement_kinds(called)["comparison"] == 1
    assert requirement_kinds(called)["relationship_equality"] == 0


@pytest.mark.parametrize("target", TARGETS)
def test_a_relationship_call_refined_by_an_authored_predicate_emits_both(
    tmp_path, target
):
    outcome = emit(
        tmp_path,
        target,
        kinds_body("inner", predicate="link(lhs, r) and lhs.key == r.key"),
        link=True,
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    # One ON condition holding the call's equality and the authored refinement.
    assert requirement_kinds(doc)["match_condition"] == 1
    assert requirement_kinds(doc)["comparison"] == 2
    q = '"' if target == "postgres" else "`"
    assert (
        f" ON (({q}m0{q}.{q}order.id{q} = {q}m1{q}.{q}order.id{q}) AND"
        f" ({q}m0{q}.{q}key value{q} = {q}m1{q}.{q}key value{q}))"
    ) in doc["sql"]


@pytest.mark.parametrize(
    "condition",
    [
        "l.id == r.id and l.id == r.key",
        "l.id == r.id and l.key == r.id",
        "l.id == r.id and l.id == r.id",
    ],
    ids=["same_source", "same_target", "same_equality"],
)
@pytest.mark.parametrize("refinement", [False, True])
@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "semi", "anti"))
def test_a_relationship_with_a_repeated_operand_emits_each_equality(
    tmp_path, kind, refinement, condition
):
    """A repeated operand only narrows the match: the call emits each equality
    of its body, for every kind and with an authored refinement."""
    predicate = "link(lhs, r)" + (" and lhs.key == r.key" if refinement else "")
    outcome = emit(
        tmp_path,
        "postgres",
        f"relationship link(l: Row, r: Row): {condition}\n"
        + kinds_body(kind, predicate=predicate),
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert requirement_kinds(doc)["comparison"] == (3 if refinement else 2)
    assert requirement_kinds(doc)["match_condition"] == 1


DISTINCT_ENDPOINT_SQL = {
    "source": 'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0",'
    ' "s0"."key value" AS "c1" FROM "public"."phase66 lhs é" AS "s0"),'
    ' "p1" ("c0", "c1") AS (SELECT DISTINCT "t0"."c0" AS "c0", "t0"."c1" AS "c1"'
    ' FROM "p0" AS "t0"), "p2" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."c0" AS'
    ' "c0", "m0"."c1" AS "c1", "m1"."order.id" AS "c2", "m1"."key value" AS "c3"'
    ' FROM "p1" AS "m0" INNER JOIN "public"."phase66 rhs é" AS "m1" ON'
    ' ("m0"."c0" = "m1"."order.id")) SELECT "t0"."c0" AS "a", "t0"."c3" AS "b"'
    ' FROM "p2" AS "t0"',
    "target": 'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0",'
    ' "s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0"),'
    ' "p1" ("c0", "c1") AS (SELECT DISTINCT "t0"."c0" AS "c0", "t0"."c1" AS "c1"'
    ' FROM "p0" AS "t0"), "p2" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id"'
    ' AS "c0", "m0"."key value" AS "c1", "m1"."c0" AS "c2", "m1"."c1" AS "c3"'
    ' FROM "public"."phase66 lhs é" AS "m0" INNER JOIN "p1" AS "m1" ON'
    ' ("m0"."order.id" = "m1"."c0")) SELECT "t0"."c0" AS "a", "t0"."c3" AS "b"'
    ' FROM "p2" AS "t0"',
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("inner", "left"))
@pytest.mark.parametrize("side", ("source", "target"))
@pytest.mark.parametrize("reads", ("other", "joined"))
def test_a_join_over_a_distinct_endpoint_emits_its_on_form(
    tmp_path, target, kind, side, reads
):
    """A DISTINCT query on either side of a JOIN emits the SQL of its explicit
    ON, whether the JOIN names its target with `let` or directly, also when the
    query reads the relation it is joined with. A shape-typed relationship
    cannot take the query's row, so a call over that endpoint fails closed
    with PIE-S2604 instead of guessing the retired source-bound route."""
    left, right = ("d", "rhs") if side == "source" else ("lhs", "d")
    producer, other = ("lhs", "rhs") if side == "source" else ("rhs", "lhs")
    if reads == "joined":
        producer, other = other, producer
    head = (
        f"query d:\n    from {producer}\n    select distinct:\n        id\n        key\n"
        "relationship near(l: Row, r: Row): l.id == r.id\n"
        f"query result:\n    from {left}\n"
    )
    joins = {
        "named": (
            f"    let r = {right}\n    {kind} join r on {left}.id == r.id\n",
            "r",
        ),
        "direct": (f"    {kind} join {right} on {left}.id == {right}.id\n", right),
        "call": (f"    let r = {right}\n    {kind} join r on near({left}, r)\n", "r"),
    }
    docs = {
        route: public(
            emit(
                tmp_path / route,
                target,
                head
                + join
                + f"    select:\n        a = {left}.id\n        b = {name}.key\n",
            )
        )
        for route, (join, name) in joins.items()
    }
    expected = (
        DISTINCT_ENDPOINT_SQL[side]
        .replace(" INNER ", f" {kind.upper()} ")
        .replace(f'"phase66 {other} é" AS "s0"', f'"phase66 {producer} é" AS "s0"')
    )
    if target == "mysql":
        expected = expected.replace('"public"', '"phase66"').replace('"', "`")
    call = docs.pop("call")
    assert [doc["status"] for doc in docs.values()] == ["VERIFIED"] * 2
    assert [doc["sql"] for doc in docs.values()] == [expected] * 2
    assert [requirement_kinds(doc)["match_condition"] for doc in docs.values()] == [
        1,
        1,
    ]
    assert call["status"] == "BLOCKED"
    parameter = "l" if side == "source" else "r"
    assert [(d["code"], d["message"]) for d in call["diagnostics"]] == [
        (
            "PIE-S2604",
            f"Unavailable row argument for relationship near parameter {parameter}",
        )
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_a_join_of_two_distinct_reads_of_one_source_emits(tmp_path, target):
    """Each input keeps its own DISTINCT grain, although both read one source."""
    doc = public(
        emit(
            tmp_path,
            target,
            """query d1:
    from rhs
    select distinct:
        id
        key
query d2:
    from rhs
    select distinct:
        id
        key
query result:
    from d1
    let r = d2
    inner join r on d1.id == r.id
    select:
        a = d1.id
        b = r.key
""",
        )
    )
    expected = (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0",'
        ' "s0"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s0"),'
        ' "p1" ("c0", "c1") AS (SELECT DISTINCT "t0"."c0" AS "c0", "t0"."c1" AS "c1"'
        ' FROM "p0" AS "t0"), "p2" ("c0", "c1") AS (SELECT "s1"."order.id" AS "c0",'
        ' "s1"."key value" AS "c1" FROM "public"."phase66 rhs é" AS "s1"),'
        ' "p3" ("c0", "c1") AS (SELECT DISTINCT "t1"."c0" AS "c0", "t1"."c1" AS "c1"'
        ' FROM "p2" AS "t1"), "p4" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."c0" AS'
        ' "c0", "m0"."c1" AS "c1", "m1"."c0" AS "c2", "m1"."c1" AS "c3"'
        ' FROM "p1" AS "m0" INNER JOIN "p3" AS "m1" ON ("m0"."c0" = "m1"."c0"))'
        ' SELECT "t0"."c0" AS "a", "t0"."c3" AS "b" FROM "p4" AS "t0"'
    )
    if target == "mysql":
        expected = expected.replace('"public"', '"phase66"').replace('"', "`")
    assert doc["status"] == "VERIFIED"
    assert doc["sql"] == expected


# --------------------------------------------------------------------------
# Producers: shared uses, membership-changing right sides, imports
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_one_named_producer_used_twice_is_scanned_by_each_use(tmp_path, target):
    """R03: two uses of one declared source are two physical occurrences."""
    outcome = emit(
        tmp_path,
        target,
        """table prod:
    from rhs
    select:
        pid = id
query result:
    from prod
    let r = prod
    inner join r on prod.pid == r.pid
    select:
        a = prod.pid
        b = r.pid
""",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    # One declared source, scanned once, feeding a CTE that both JOIN inputs
    # read: a named reference is not another physical scan.
    assert requirement_kinds(doc)["qualified_scan"] == 1
    assert requirement_kinds(doc)["join_input"] == 2


@pytest.mark.parametrize("target", TARGETS)
def test_two_physical_join_inputs_each_keep_their_scan_obligations(tmp_path, target):
    outcome = emit(tmp_path, target, kinds_body("inner"))
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert requirement_kinds(doc)["qualified_scan"] == 2
    assert requirement_kinds(doc)["source_representation"] == 4


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("semi", "anti"))
def test_a_membership_join_keeps_its_right_side_dependencies(tmp_path, target, kind):
    """SEMI/ANTI expose no right column, yet the right side is fully retained."""
    outcome = emit(
        tmp_path,
        target,
        """table prod:
    from rhs
    let step = id + 0
    where id > 0
    select:
        pid = step
query result:
    from lhs
    let r = prod
"""
        + join_line(kind, "lhs.id == r.pid")
        + """    select:
        a = lhs.id
""",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert [column["label"] for column in doc["columns"]] == ["a"]
    # The right producer's own scan, filter and LET all survive inside the
    # membership wrapper even though nothing of it reaches the result; the
    # third scan is the later JOIN's.
    assert requirement_kinds(doc)["qualified_scan"] == 3
    assert requirement_kinds(doc)["membership"] == 1
    assert requirement_kinds(doc)["sentinel"] == 1
    assert requirement_kinds(doc)["correlation"] == 1


@pytest.mark.parametrize("target", TARGETS)
def test_an_imported_and_reexported_producer_joins(tmp_path, target):
    item = probe.join_witness(
        target,
        {
            "a.pietto": probe.JOIN_WITNESS_HEADER.format(target=target)
            + """table prod:
    from rhs
    select:
        pid = id
        marker = 1
table base:
    from lhs
    select:
        lid = id
export table prod, table base
""",
            "b.pietto": 'from "a.pietto" import table prod as Mid, table base as Root\n'
            "export table Mid, table Root\n",
            "main.pietto": 'from "b.pietto" import table Mid as Public, table Root as Left\n'
            "query result:\n    from Left\n    let r = Public\n"
            "    inner join r on Left.lid == r.pid\n"
            "    select:\n        a = Left.lid\n        b = r.pid\n",
        },
        module="a.pietto",
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert [column["label"] for column in doc["columns"]] == ["a", "b"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_joined_tail_carries_its_own_let_and_filter(tmp_path, target):
    outcome = emit(
        tmp_path,
        target,
        """query result:
    from lhs
    let r = rhs
    inner join r on lhs.id == r.id
    let doubled = lhs.id + 0
    where lhs.id > 0
    select:
        a = doubled
        b = r.id
""",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert [column["label"] for column in doc["columns"]] == ["a", "b"]


@pytest.mark.parametrize("target", TARGETS)
def test_an_ordered_join_chain_emits_one_unit_per_occurrence(tmp_path, target):
    outcome = emit(
        tmp_path,
        target,
        """query result:
    from lhs
    let r = rhs
    inner join r on lhs.id == r.id
    let s = rhs
    right join s on lhs.id == s.id
    select:
        a = lhs.id
        b = r.id
        c = s.id
""",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert requirement_kinds(doc)["join_use"] == 1
    # The accumulated left of the second JOIN is null-extended by the RIGHT.
    assert nullability(doc) == [("a", True), ("b", True), ("c", False)]


# A grouped result read by a JOIN whose result another JOIN reads.
GROUPED_JOIN_CHAIN = """table up:
    from lhs
    group by:
        id
    select:
        id
        n = count()
query mid:
    from up
    let m = rhs
    {kind} join m{mid_on}
    select:
        id = up.id
        n = up.n
query result:
    from mid
    let z = rhs
    {kind} join z{result_on}
    select:
        id = mid.id
        n = mid.n
"""
GROUPED_JOIN_CHAIN_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."order.id" AS "c0", COUNT(*) AS "c1"'
        ' FROM "public"."phase66 lhs é" AS "s0" GROUP BY "s0"."order.id"), "p1" ("c0",'
        ' "c1") AS (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1" FROM "p0" AS "t1"),'
        ' "p2" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."c0" AS "c0", "m0"."c1" AS'
        ' "c1", "m1"."order.id" AS "c2", "m1"."key value" AS "c3" FROM "p1" AS "m0"'
        ' {join} "public"."phase66 rhs é" AS "m1"{mid_on}), "p3" ("c0", "c1") AS'
        ' (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1" FROM "p2" AS "t0"), "p4" ("c0",'
        ' "c1", "c2", "c3") AS (SELECT "m2"."c0" AS "c0", "m2"."c1" AS "c1",'
        ' "m3"."order.id" AS "c2", "m3"."key value" AS "c3" FROM "p3" AS "m2" {join}'
        ' "public"."phase66 rhs é" AS "m3"{result_on}) SELECT "t1"."c0" AS "id",'
        ' "t1"."c1" AS "n" FROM "p4" AS "t1"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`) AS (SELECT `s0`.`order.id` AS `c0`, COUNT(*) AS `c1`"
        " FROM `phase66`.`phase66 lhs é` AS `s0` GROUP BY `s0`.`order.id`), `p1` (`c0`,"
        " `c1`) AS (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1` FROM `p0` AS `t1`),"
        " `p2` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `m0`.`c0` AS `c0`, `m0`.`c1` AS"
        " `c1`, `m1`.`order.id` AS `c2`, `m1`.`key value` AS `c3` FROM `p1` AS `m0`"
        " {join} `phase66`.`phase66 rhs é` AS `m1`{mid_on}), `p3` (`c0`, `c1`) AS"
        " (SELECT `t0`.`c0` AS `c0`, `t0`.`c1` AS `c1` FROM `p2` AS `t0`), `p4` (`c0`,"
        " `c1`, `c2`, `c3`) AS (SELECT `m2`.`c0` AS `c0`, `m2`.`c1` AS `c1`,"
        " `m3`.`order.id` AS `c2`, `m3`.`key value` AS `c3` FROM `p3` AS `m2` {join}"
        " `phase66`.`phase66 rhs é` AS `m3`{result_on}) SELECT `t1`.`c0` AS `id`,"
        " `t1`.`c1` AS `n` FROM `p4` AS `t1`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("cross", "inner"))
def test_a_grouped_result_joined_twice_emits(tmp_path, target, kind):
    inner = kind == "inner"
    outcome = emit(
        tmp_path,
        target,
        GROUPED_JOIN_CHAIN.format(
            kind=kind,
            mid_on=" on up.id == m.id" if inner else "",
            result_on=" on mid.id == z.id" if inner else "",
        ),
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED", document(outcome)
    q = '"' if target == "postgres" else "`"
    assert doc["sql"] == GROUPED_JOIN_CHAIN_SQL[target].format(
        join=f"{kind.upper()} JOIN",
        mid_on=f" ON ({q}m0{q}.{q}c0{q} = {q}m1{q}.{q}order.id{q})" if inner else "",
        result_on=f" ON ({q}m2{q}.{q}c0{q} = {q}m3{q}.{q}order.id{q})" if inner else "",
    )
    assert [column["label"] for column in doc["columns"]] == ["id", "n"]


# A chain of two JOINs that reads relations its module declares after it.
FORWARD_JOIN_CHAIN = """query result:
    from mid
{joins}    select:
        a = mid.id
        b = {z}.key
        c = {w}.key
"""
FORWARD_DECLARATIONS = """query d:
    from rhs
    where key > 0
    select:
        id
        key
table mid:
    from lhs
    where id > 1
    select:
        id
        key
"""
FORWARD_JOINS = {
    "named": (
        "    let z = rhs\n    left join z on mid.id == z.id\n"
        "    let w = d\n    inner join w on z.key == w.id\n",
        "z",
        "w",
    ),
    "direct": (
        "    left join rhs on mid.id == rhs.id\n    inner join d on rhs.key == d.id\n",
        "rhs",
        "d",
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_a_join_chain_over_later_declarations_emits_its_let_named_sql(tmp_path, target):
    """A chain over the shape, sources and relations declared after it emits
    the same SQL whether its targets are named with `let` or directly."""
    header = probe.JOIN_WITNESS_HEADER.format(target=target)
    docs = [
        public(
            emit(
                tmp_path / name,
                target,
                {
                    "main.pietto": FORWARD_JOIN_CHAIN.format(joins=joins, z=z, w=w)
                    + FORWARD_DECLARATIONS
                    + header
                },
            )
        )
        for name, (joins, z, w) in FORWARD_JOINS.items()
    ]
    assert [doc["status"] for doc in docs] == ["VERIFIED"] * 2
    for key in ("sql", "columns"):
        assert [doc[key] for doc in docs] == [docs[0][key]] * 2, key
    assert [requirement_kinds(doc) for doc in docs] == [requirement_kinds(docs[0])] * 2


# --------------------------------------------------------------------------
# The migrated inputs whose only remaining restriction was the JOIN family
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("case", "variant", "label"),
    (
        ("V_row_blocked", "match_join", "record_id"),
        ("O_named_later", "self_join", "id"),
    ),
)
def test_a_rebound_join_input_now_emits_and_decodes(
    tmp_path, target, case, variant, label
):
    item = probe.fixture(target, case, variant)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert probe.expected_status(case, variant, target) == "VERIFIED"
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert [column["label"] for column in doc["columns"]] == [label]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("variant", ("cross", "inner", "semi", "anti"))
def test_every_new_manifest_join_shape_decodes(tmp_path, target, variant):
    item = probe.fixture(target, "W_join_shapes", variant)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert [column["label"] for column in doc["columns"]] == list(
        probe.JOIN_LABELS[variant]
    )


@pytest.mark.parametrize("target", TARGETS)
def test_the_restricted_full_manifest_case_splits_by_target(tmp_path, target):
    item = probe.fixture(target, "V_join_full", "restricted")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    doc = public(outcome)
    expected = probe.expected_status("V_join_full", "restricted", target)
    assert doc["status"] == expected
    assert expected == ("VERIFIED" if target == "postgres" else "BLOCKED")


# --------------------------------------------------------------------------
# A JOIN named directly or matched by a relationship publishes its explicit form
# --------------------------------------------------------------------------


def _authored_layout_free(value):
    """The document without what only the source text decides: its digest,
    its size and authored locations."""
    if isinstance(value, dict):
        return {
            key: _authored_layout_free(item)
            for key, item in value.items()
            if key not in {"sha256", "byte_count", "location"}
        }
    if isinstance(value, list):
        return [_authored_layout_free(item) for item in value]
    return value


def _as_written(value):
    """A relationship call's expansion origin (the call, its body and its row
    argument) read as the one authored cause of the predicate written in its
    place. Inside `any`, the ANY expansion leads and the call is a generated
    call: its body and its binder argument read as the ANY's own copy of the
    written predicate, an authored row argument as that row's authored cause."""
    if isinstance(value, dict):
        sources = value.get("sources") or []
        kinds = [source.get("kind") for source in sources]
        if kinds[:1] == ["relationship_predicate_call"] or (
            kinds[1:2] == ["relationship_predicate_generated_call"]
            and kinds[-1] == "relationship_predicate_argument"
        ):
            authored = {"kind": "authored_cause", "path": sources[0]["path"]}
            value = {**value, "sources": [authored]}
        elif kinds[1:2] == ["relationship_predicate_generated_call"]:
            value = {**value, "sources": sources[:1]}
        return {key: _as_written(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_as_written(item) for item in value]
    return value


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "semi", "anti"))
@pytest.mark.parametrize(
    ("name", "predicate"),
    (("rhs", "lhs.id == rhs.id"), ("r", "link(lhs, r)")),
    ids=("direct", "relationship"),
)
def test_a_direct_or_relationship_join_publishes_its_explicit_form(
    tmp_path, target, kind, name, predicate
):
    """A JOIN target named directly instead of with `let`, or matched by a
    relationship call instead of the predicate the call stands for, publishes
    the explicit form; the ranges of a call record its expansion."""
    head = "query result:\n    from lhs\n"
    tail = "    select:\n        a = lhs.id\n"
    named = "    let r = rhs\n"
    explicit = named + join_line(kind)
    spelled = ("" if name == "rhs" else named) + join_line(kind, predicate, name)
    written, found = (
        document(emit(tmp_path / label, target, head + layout + tail, link=True))
        for label, layout in (("explicit", explicit), ("spelled", spelled))
    )
    assert found["status"] == written["status"]
    assert found.get("sql") == written.get("sql")
    assert _as_written(_authored_layout_free(found)) == _authored_layout_free(written)
    call = (
        "relationship_predicate_generated_call"
        if kind in MEMBERSHIP
        else "relationship_predicate_call"
    )
    expansion = call in json.dumps(found)
    assert expansion is ("link(" in predicate and "ranges" in written)


@pytest.mark.parametrize("target", TARGETS)
def test_a_one_line_relationship_publishes_its_block_form(tmp_path, target):
    """Its body may follow the header's ':' on the same line."""
    join = (
        "query result:\n    from lhs\n    let r = rhs\n    inner join r on link(lhs, r)\n"
        "    select:\n        a = lhs.id\n"
    )
    block = "relationship link(l: Row, r: Row):\n    l.id == r.id\n" + join
    one_line = "relationship link(l: Row, r: Row): l.id == r.id\n" + join
    written, found = (
        document(emit(tmp_path / label, target, body))
        for label, body in (("block", block), ("one_line", one_line))
    )
    assert found["status"] == written["status"] == "VERIFIED"
    assert _authored_layout_free(found) == _authored_layout_free(written)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("head", "source"),
    (
        (
            "    let v:\n        values(id: Int):\n            1\n"
            "    from lhs\n    let vv = v\n    inner join vv on vv.id == lhs.id\n",
            "lhs",
        ),
        (
            "    from generate_series(1, 3, 1) as n\n    let l = lhs\n"
            "    inner join l on l.id == n.n\n",
            "l",
        ),
    ),
    ids=("values_let", "table_function"),
)
def test_a_relationship_join_after_an_unmodelled_input_publishes_its_explicit_form(
    tmp_path, target, head, source
):
    """After a VALUES or table-function input, which no relationship parameter
    can take, a call over the rows it names publishes the explicit predicate."""
    tail = "    select:\n        a = r.id\n"
    written, found = (
        document(
            emit(
                tmp_path / label,
                target,
                f"query result:\n{head}    let r = rhs\n    inner join r on {on}\n{tail}",
                link=True,
            )
        )
        for label, on in (
            ("explicit", f"{source}.id == r.id"),
            ("relationship", f"link({source}, r)"),
        )
    )
    assert found["status"] == written["status"]
    assert target == "mysql" or written["status"] == "VERIFIED"
    assert found.get("sql") == written.get("sql")
    assert _as_written(_authored_layout_free(found)) == _authored_layout_free(written)


# --------------------------------------------------------------------------
# Rejection controls over the published bytes
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation",
    (
        "join_kind_token",
        "membership_polarity",
        "sentinel_value",
        "input_alias_capture",
        "published_port_column",
        "on_operator",
    ),
)
def test_public_join_byte_corruptions_are_rejected(tmp_path, mutation):
    kind = "semi" if mutation in {"membership_polarity", "sentinel_value"} else "inner"
    select = (
        "        a = lhs.id\n"
        if kind == "semi"
        else "        a = lhs.id\n        b = r.id\n"
    )
    outcome = emit(tmp_path, "postgres", kinds_body(kind, select=select))
    data = document(outcome)
    sql = data["sql"]
    if mutation == "join_kind_token":
        data["sql"] = sql.replace(" INNER JOIN ", " LEFT JOIN ", 1)
    elif mutation == "membership_polarity":
        data["sql"] = sql.replace(" WHERE EXISTS (", " WHERE NOT EXISTS (", 1)
    elif mutation == "sentinel_value":
        data["sql"] = sql.replace("SELECT 1 FROM", "SELECT 2 FROM", 1)
    elif mutation == "input_alias_capture":
        data["sql"] = sql.replace('AS "m1"', 'AS "m0"', 1)
    elif mutation == "published_port_column":
        data["sql"] = sql.replace(
            '"m0"."order.id" AS "c0"', '"m0"."key value" AS "c0"', 1
        )
    else:
        data["sql"] = sql.replace(" = ", " <> ", 1)
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


def test_deleting_a_scan_and_its_requirements_together_is_rejected(tmp_path):
    """A coordinated deletion must not look like a smaller, consistent query."""
    outcome = emit(tmp_path, "postgres", kinds_body("inner"))
    data = document(outcome)
    dropped = {"qualified_scan", "source_representation", "source_realization"}
    data["requirements"] = [
        item for item in data["requirements"] if item["kind"] not in dropped
    ]
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


def test_dropping_a_membership_right_dependency_is_rejected(tmp_path):
    outcome = emit(
        tmp_path, "postgres", kinds_body("semi", select="        a = lhs.id\n")
    )
    data = document(outcome)
    data["requirements"] = [
        item
        for item in data["requirements"]
        if item["kind"] not in {"membership", "correlation", "sentinel"}
    ]
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


def test_dropping_an_unprojected_producer_value_is_rejected(tmp_path):
    """A right producer value nothing selects still has to be accounted for."""
    outcome = emit(
        tmp_path,
        "postgres",
        """table prod:
    from rhs
    select:
        pid = id
        marker = 1
query result:
    from lhs
    let r = prod
    left join r on lhs.id == r.pid
    select:
        a = lhs.id
        b = r.pid
""",
    )
    data = document(outcome)
    sql = data["sql"]
    # `marker` is published by the producer CTE and carried through the JOIN even
    # though the result never selects it. Removing that carrier must be refused.
    data["sql"] = sql.replace(', CAST(1 AS pg_catalog.int8) AS "c1"', "", 1)
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


def test_a_null_extension_requirement_cannot_be_moved_to_the_preserved_side(tmp_path):
    outcome = emit(
        tmp_path,
        "postgres",
        kinds_body("left", select="        a = lhs.id\n        b = r.id\n"),
    )
    data = document(outcome)
    extensions = [
        item for item in data["requirements"] if item["kind"] == "null_extension"
    ]
    assert extensions
    others = [
        item
        for item in data["requirements"]
        if item["kind"] == "join_output" and item not in extensions
    ]
    assert others
    for item in extensions:
        item["subject"] = others[0]["subject"]
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


# --------------------------------------------------------------------------
# The private debug representation of an emission result is bounded work
# --------------------------------------------------------------------------


REPR_LIMIT = 1024


class _Exploding:
    """A child whose display must never be reached by a root representation."""

    def __repr__(self) -> str:
        raise AssertionError("a child representation was formatted")

    __str__ = __repr__


def _verified(tmp_path, target):
    item = probe.fixture(target, "V_row_blocked", "match_join")
    return probe.build_case(tmp_path, item["source"], item["contract"], item["policy"])


@pytest.mark.parametrize("target", TARGETS)
def test_emission_result_reprs_are_bounded_and_deterministic(tmp_path, target):
    _, verified = _verified(tmp_path, target)
    item = probe.fixture(target, "V_join_full", "restricted")
    _, restricted = probe.build_case(
        tmp_path / "restricted", item["source"], item["contract"], item["policy"]
    )

    for outcome in (verified, restricted):
        text = repr(outcome)
        assert len(text.encode("utf-8")) <= REPR_LIMIT
        assert text == repr(outcome)
        assert text.startswith("EmissionOutcome(status=")
        # The displayed status is the bounded scalar, never a nested object.
        assert repr(outcome.status) in text
        if outcome.artifact is None:
            assert "artifact=none" in text
            continue
        assert "artifact=present" in text
        # Displaying the artifact directly, not only its container, is safe.
        nested = repr(outcome.artifact)
        assert len(nested.encode("utf-8")) <= REPR_LIMIT
        assert nested == repr(outcome.artifact)
        assert nested.startswith("EmissionArtifact(request=..., ast=..., rendered=...")


def test_neither_repr_formats_any_child() -> None:
    # Deliberately ill-typed children: the point is that they are never shown.
    child: Any = _Exploding()
    outcome = EmissionOutcome(
        status="VERIFIED",
        diagnostics=(child, child),
        artifact=child,
        blockers=(child,),
        cli_errors=(child,),
    )
    text = repr(outcome)
    assert "diagnostics=<2>" in text and "blockers=<1>" in text
    assert "artifact=present" in text

    artifact = EmissionArtifact(
        request=child,
        ast=child,
        rendered=child,
        original_requirements=(child, child, child),
        generated_requirements=(child,),
        fixed_values=(child,),
        parameter_uses=(),
    )
    nested = repr(artifact)
    assert "original_requirements=<3>" in nested
    assert "generated_requirements=<1>" in nested
    assert "parameter_uses=<0>" in nested


@pytest.mark.parametrize("target", TARGETS)
def test_repr_size_follows_counts_and_not_the_shared_graph(tmp_path, target):
    _, outcome = _verified(tmp_path, target)
    assert outcome.artifact is not None
    # A synthetic outcome with the same scalar shape but no reachable graph, and
    # one whose single artifact is repeated across every tuple slot, produce the
    # identical text: representation work never follows sharing or reach.
    opaque: Any = None
    synthetic = EmissionOutcome(
        status=outcome.status,
        diagnostics=(),
        artifact=EmissionArtifact(
            request=opaque,
            ast=opaque,
            rendered=opaque,
            original_requirements=outcome.artifact.original_requirements,
            generated_requirements=outcome.artifact.generated_requirements,
            fixed_values=outcome.artifact.fixed_values,
            parameter_uses=outcome.artifact.parameter_uses,
        ),
    )
    assert repr(synthetic) == repr(outcome)
    assert repr(synthetic.artifact) == repr(outcome.artifact)

    shared: Any = outcome.artifact
    repeated = EmissionArtifact(
        request=shared,
        ast=shared,
        rendered=shared,
        original_requirements=(shared,) * 64,
        generated_requirements=(shared,) * 64,
        fixed_values=(),
        parameter_uses=(),
    )
    assert len(repr(repeated).encode("utf-8")) <= REPR_LIMIT


@pytest.mark.parametrize("target", TARGETS)
def test_repr_changes_no_field_verification_or_published_byte(tmp_path, target):
    checked, outcome = _verified(tmp_path, target)
    before = serialize_project_sql_emission(outcome)
    document = probe.decode_public(before)
    identity = (outcome.status, outcome.artifact, outcome.diagnostics)

    repr(outcome)
    repr(outcome.artifact)

    assert (outcome.status, outcome.artifact, outcome.diagnostics) == identity
    assert checked.verified
    after = serialize_project_sql_emission(outcome)
    assert after == before
    assert probe.decode_public(after) == document


# A current limitation (docs/language.md): an INNER JOIN whose ON has a nullable
# Bool field as an AND conjunct of its own is BLOCKED at emission on both
# targets; the same test in WHERE emits.
NULLABLE_BOOL_ON = (
    "query result:\n    from rows\n    let o = rows\n"
    "    inner join o on rows.id == o.id{on}\n{where}    select:\n        a = rows.id\n"
)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("place", ("on", "where"))
def test_a_nullable_bool_on_conjunct_is_blocked_and_its_where_form_emits(
    tmp_path, target, place
):
    item = probe.join_fixture(target, "W_join_shapes", "inner")
    header = item["source"].split("query result:", 1)[0]
    body = NULLABLE_BOOL_ON.format(
        on=" and o.flag" if place == "on" else "",
        where="    where o.flag\n" if place == "where" else "",
    )
    _, outcome = probe.build_case(
        tmp_path, header + body, item["contract"], item["policy"]
    )
    published = json.loads(serialize_project_sql_emission(outcome))
    if place == "where":
        assert published["status"] == "VERIFIED", published
        return
    assert (published["status"], published["diagnostics"]) == ("BLOCKED", [])
    assert [
        (b["code"], b["subject"]["detail"], b["location"])
        for b in published["blockers"]
    ] == [("PIE-B1002", "join_output_nullability_drift", None)]


# An enum or shape field is outside the initial representation domain of
# project SQL emission, so a source declaring one is BLOCKED whether or not a
# JOIN reads it, whether or not the field's type admits None.
ENUM_TEXT_DOMAIN = {
    "postgres": ({"kind": "pg_text"}, "UTF8", "C"),
    "mysql": ({"kind": "my_varchar", "length": 64}, "utf8mb4", "utf8mb4_0900_bin"),
}
ENUM_STATUS = ("enum Status:\n    active\n    closed\n", "Status")
SHAPE_PAYLOAD = ("shape Payload:\n    a: Int\n", "Payload")
# The declared `state` field: `T | None` admits None, a bare `T` never does.
MODIFIERS = (" | None", "")


def enum_field_document(directory, target, body, modifier, declared=ENUM_STATUS):
    item = probe.join_witness(target, body)
    declaration, type_name = declared
    source = declaration + item["source"].replace(
        "    key: Int | None\n",
        f"    key: Int | None\n    state: {type_name}{modifier}\n",
    )
    assert f"    state: {type_name}{modifier}\n" in source
    storage, encoding, collation = ENUM_TEXT_DOMAIN[target]
    contract = json.loads(item["contract"])
    for declared in contract["sources"]:
        declared["fields"].append(
            {
                "ordinal": 2,
                "name": "state",
                "column": "state",
                "representation": {
                    "storage": storage,
                    "nullable": modifier == " | None",
                    "domain": {
                        "kind": "text",
                        "max_characters": 64,
                        "encoding": encoding,
                        "collation": collation,
                        "padding": "NO PAD",
                    },
                },
            }
        )
    _, outcome = probe.build_case(
        directory, source, probe.encoded(contract).decode(), item["policy"]
    )
    return document(outcome)


def state_field(line, type_name, modifier):
    """The authored span of the declared `state` field."""
    end = 5 + len(f"state: {type_name}{modifier}")
    return {"path": "main.pietto", "line": line, "column": 5} | {
        "end_line": line,
        "end_column": end,
    }


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("modifier", MODIFIERS, ids=("nullable", "not_null"))
def test_an_enum_field_of_a_join_input_blocks_as_without_the_join(
    tmp_path, target, modifier
):
    field = state_field(7, "Status", modifier)
    join_input = (
        "PIE-B1004",
        {
            "detail": "join_input_field_representation_missing",
            "reference": {"kind": "join_port", "position": 2},
        },
        None,
    )

    def outside_domain(position):
        reference = {"kind": "source_port", "position": position}
        detail = "representation_not_in_initial_domain"
        return ("PIE-B1003", {"detail": detail, "reference": reference}, field)

    def blockers(directory, body):
        published = enum_field_document(directory, target, body, modifier)
        assert (published["status"], published["diagnostics"]) == ("BLOCKED", [])
        return [(b["code"], b["subject"], b["location"]) for b in published["blockers"]]

    unjoined = "query result:\n    from lhs\n    select:\n        a = lhs.id\n"
    assert blockers(tmp_path / "unjoined", unjoined) == [outside_domain(2)]
    for kind in KINDS:
        assert blockers(tmp_path / kind, kinds_body(kind)) == [
            join_input,
            outside_domain(2),
            outside_domain(5),
        ]


@pytest.mark.parametrize("target", TARGETS)
def test_a_window_value_of_an_enum_field_blocks_as_any_window_of_its_source(
    tmp_path, target
):
    """`lag` of an enum field, and a later relation's `first_value` of that
    column, are typed as the enum and blocked as a window over the source that
    reads no enum field is: by the stage input and the enum field's source
    port. Before, their project check crashed with a ValueError."""
    window = "window(order by id)\n"
    field = state_field(7, "Status", "")
    blocked = [
        (
            "PIE-B1001",
            {
                "detail": "stage_input_not_bound",
                "reference": {"kind": "stage_port", "position": 2},
            },
            None,
        ),
        (
            "PIE-B1003",
            {
                "detail": "representation_not_in_initial_domain",
                "reference": {"kind": "source_port", "position": 2},
            },
            field,
        ),
    ]
    for name, body in (
        ("integer", f"        p = lag(id) {window}"),
        ("enum", f"        p = lag(state) {window}"),
        (
            "later",
            f"        p = lag(state) {window}query result:\n    from navigated\n"
            f"    select:\n        id\n        f = first_value(p) {window}",
        ),
    ):
        relation = "table navigated" if name == "later" else "query result"
        published = enum_field_document(
            tmp_path / name,
            target,
            f"{relation}:\n    from lhs\n    select:\n        id\n{body}",
            "",
        )
        assert (published["status"], published["diagnostics"]) == ("BLOCKED", [])
        assert [
            (b["code"], b["subject"], b["location"]) for b in published["blockers"]
        ] == blocked


@pytest.mark.parametrize("target", TARGETS)
def test_a_window_value_of_a_shape_field_blocks_as_any_window_of_its_source(
    tmp_path, target
):
    """`lag` and `first_value` of a shape field, and a later relation's
    `first_value` of that column, are typed as the shape and blocked as a
    window over the source that reads no shape field is: by the stage input
    and the shape field's source port. Before, `check --project` refused each
    shape window with PIE-S2104 `value type must be concrete`."""
    window = "window(order by id)\n"
    field = state_field(6, "Payload", "")
    blocked = [
        (
            "PIE-B1001",
            {
                "detail": "stage_input_not_bound",
                "reference": {"kind": "stage_port", "position": 2},
            },
            None,
        ),
        (
            "PIE-B1003",
            {
                "detail": "representation_not_in_initial_domain",
                "reference": {"kind": "source_port", "position": 2},
            },
            field,
        ),
    ]
    for name, body in (
        ("integer", f"        p = lag(id) {window}"),
        ("shape", f"        p = lag(state) {window}"),
        ("first", f"        p = first_value(state) {window}"),
        (
            "later",
            f"        p = lag(state) {window}query result:\n    from navigated\n"
            f"    select:\n        id\n        f = first_value(p) {window}",
        ),
    ):
        relation = "table navigated" if name == "later" else "query result"
        published = enum_field_document(
            tmp_path / name,
            target,
            f"{relation}:\n    from lhs\n    select:\n        id\n{body}",
            "",
            SHAPE_PAYLOAD,
        )
        assert (published["status"], published["diagnostics"]) == ("BLOCKED", [])
        assert [
            (b["code"], b["subject"], b["location"]) for b in published["blockers"]
        ] == blocked


@pytest.mark.parametrize("target", TARGETS)
def test_a_window_of_a_join_relation_computed_column_emits(tmp_path, target):
    """A later relation's `last_value` and `lag` of a JOIN relation's computed
    columns, `v = r.id + 1` and `w = k + 1` with `k = r.id`, emit verified
    PostgreSQL; MySQL blocks the integer window result, as for any computed
    integer value. Before, `check --project` refused both windows with
    PIE-S2104 `value type must be concrete`."""
    window = "window(order by id)\n"
    item = probe.join_witness(
        target,
        "table joined:\n    from lhs\n    let r = rhs\n"
        "    inner join r on lhs.key == r.key\n    let k = r.id\n    select:\n"
        "        id = lhs.id\n        v = r.id + 1\n        w = k + 1\n"
        "query result:\n    from joined\n    select:\n        id\n"
        f"        last = last_value(v) {window}"
        f"        previous = lag(w) {window}",
    )
    contract = json.loads(item["contract"])
    for declared in contract["sources"]:
        for field in declared["fields"]:
            # A 32-bit carrier proves `+ 1` inside the 64-bit result.
            field["representation"]["storage"] = {
                "kind": "pg_int4" if target == "postgres" else "my_int"
            }
            field["representation"]["domain"] = {
                "kind": "int_range",
                "min": "-1000",
                "max": "1000",
            }
    _, outcome = probe.build_case(
        tmp_path, item["source"], probe.encoded(contract).decode(), item["policy"]
    )
    published = public(outcome)

    if target == "mysql":
        assert (published["status"], published["diagnostics"]) == ("BLOCKED", [])
        assert [
            (b["code"], b["subject"]["detail"], b["location"]["line"])
            for b in published["blockers"]
        ] == [
            (
                "PIE-B1002",
                "mysql_window_integer_result_origin_not_supported_in_phase66",
                # The `last = last_value(v) ...` line of the query.
                19,
            )
        ]
        return
    assert published["status"] == "VERIFIED"
    assert published["sql"] == (
        'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "m0"."order.id" AS "c0", '
        '"m0"."key value" AS "c1", "m1"."order.id" AS "c2", "m1"."key value" AS '
        '"c3" FROM "public"."phase66 lhs é" AS "m0" INNER JOIN "public"."phase66 '
        'rhs é" AS "m1" ON ("m0"."key value" = "m1"."key value")), "p1" ("c0", '
        '"c1", "c2", "c3", "c4") AS (SELECT "t0"."c0" AS "c0", "t0"."c1" AS "c1", '
        '"t0"."c2" AS "c2", "t0"."c3" AS "c3", "t0"."c2" AS "c4" FROM "p0" AS '
        '"t0"), "p2" ("c0", "c1", "c2") AS (SELECT "t1"."c0" AS "c0", ("t1"."c2" '
        '+ CAST(1 AS pg_catalog.int8)) AS "c1", ("t1"."c4" + CAST(1 AS '
        'pg_catalog.int8)) AS "c2" FROM "p1" AS "t1"), "p3" ("c0", "c1", "c2", '
        '"c3", "c4") AS (SELECT "s2"."c0" AS "c0", "s2"."c1" AS "c1", "s2"."c2" AS '
        '"c2", LAST_VALUE("s2"."c1") OVER (ORDER BY "s2"."c0" ASC RANGE BETWEEN '
        'UNBOUNDED PRECEDING AND CURRENT ROW) AS "c3", LAG("s2"."c2") OVER (ORDER '
        'BY "s2"."c0" ASC) AS "c4" FROM "p2" AS "s2") SELECT "t3"."c0" AS "id", '
        '"t3"."c3" AS "last", "t3"."c4" AS "previous" FROM "p3" AS "t3"'
    )
    assert [
        (column["label"], column["logical_type"]["name"], column["nullable"])
        for column in published["columns"]
    ] == [("id", "Int", False), ("last", "Int", True), ("previous", "Int", True)]
