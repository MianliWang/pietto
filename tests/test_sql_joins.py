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


def kinds_body(kind, *, predicate="lhs.id == r.id", select="        a = lhs.id\n"):
    condition = "" if kind == "cross" else f"        on {predicate}\n"
    return f"""query result:
    from lhs
    {kind} join rhs as r:
        from lhs
{condition}    select:
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
        if kind in {"semi", "anti"}
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
        assert MEMBERSHIP[kind] in doc["sql"]
        assert " JOIN " not in doc["sql"]
    else:
        assert NATIVE[kind] in doc["sql"]


@pytest.mark.parametrize("kind", ("left", "right", "inner", "cross", "semi", "anti"))
def test_a_mysql_full_rejection_does_not_refuse_its_neighbours(tmp_path, kind):
    """Only FULL is withheld on MySQL; the neighbouring kinds still emit."""
    select = (
        "        a = lhs.id\n"
        if kind in {"semi", "anti"}
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
    let:
        step = id + 0
    where id > 0
    select:
        pid = id
        marker = 1
        computed = id + 0
        stepped = step
query result:
    from lhs
    left join prod as r:
        from lhs
        on lhs.id == r.pid
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
    right join rhs as r:
        from leftish
        on leftish.lid == r.id
    select:
        a = leftish.lid
        b = r.id
""",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert nullability(doc) == [("a", True), ("b", False)]


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
    # declared nullable -- not because the JOIN nulled anything.
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
    ("inner", "lhs.id == r.id and r.key is null", "r.key", True),
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
# Relationship routes: valid equality, refinement, and the retained limitation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("inner", "left"))
def test_a_relationship_only_via_emits_its_retained_equality(tmp_path, target, kind):
    outcome = emit(
        tmp_path,
        target,
        f"""query result:
    from lhs
    {kind} join rhs as r:
        from lhs
        via link: l -> r
    select:
        a = lhs.id
""",
        link=True,
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert requirement_kinds(doc)["relationship_equality"] == 1
    assert requirement_kinds(doc)["match_condition"] == 0


@pytest.mark.parametrize("target", TARGETS)
def test_a_via_route_refined_by_an_authored_predicate_emits_both(tmp_path, target):
    outcome = emit(
        tmp_path,
        target,
        """query result:
    from lhs
    inner join rhs as r:
        from lhs
        via link: l -> r
        on lhs.key == r.key
    select:
        a = lhs.id
""",
        link=True,
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert requirement_kinds(doc)["relationship_equality"] == 1
    assert requirement_kinds(doc)["match_condition"] == 1


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
    """A repeated operand only narrows the match, for every kind and VIA+ON."""
    outcome = emit(
        tmp_path,
        "postgres",
        f"""relationship link:
    endpoint l: lhs
    endpoint r: rhs
    on {condition}
query result:
    from lhs
    {kind} join rhs as r:
        from lhs
        via link: l -> r
"""
        + ("        on lhs.key == r.key\n" if refinement else "")
        + """    select:
        a = lhs.id
""",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert requirement_kinds(doc)["relationship_equality"] == 2
    assert requirement_kinds(doc)["match_condition"] == (1 if refinement else 0)


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
def test_a_relationship_only_via_over_a_distinct_endpoint_emits_its_on_form(
    tmp_path, target, kind, side, reads
):
    """Its relationship equality is the SQL of the equivalent explicit ON,
    also when the JOIN leaves its source or VIA roles to be inferred and when
    the endpoint reads the relation it is joined with."""
    left, right = ("d", "rhs") if side == "source" else ("lhs", "d")
    producer, other = ("lhs", "rhs") if side == "source" else ("rhs", "lhs")
    if reads == "joined":
        producer, other = other, producer
    block = f"    {kind} join {right} as r:\n        from {left}\n"
    docs = {
        route: public(
            emit(
                tmp_path / route,
                target,
                f"""query d:
    from {producer}
    select distinct:
        id
        key
relationship near:
    endpoint l: {left}
    endpoint r: {right}
    on l.id == r.id
query result:
    from {left}
{join}    select:
        a = {left}.id
        b = r.key
""",
            )
        )
        for route, join in (
            ("via", block + "        via near: l -> r\n"),
            ("zero_via", block),
            ("on", block + f"        on {left}.id == r.id\n"),
            ("inferred", f"    {kind} join {right} as r\n"),
            ("inferred_roles", f"    {kind} join {right} as r: via near\n"),
        )
    }
    expected = (
        DISTINCT_ENDPOINT_SQL[side]
        .replace(" INNER ", f" {kind.upper()} ")
        .replace(f'"phase66 {other} é" AS "s0"', f'"phase66 {producer} é" AS "s0"')
    )
    if target == "mysql":
        expected = expected.replace('"public"', '"phase66"').replace('"', "`")
    assert [doc["status"] for doc in docs.values()] == ["VERIFIED"] * 5
    assert [doc["sql"] for doc in docs.values()] == [expected] * 5
    assert [
        requirement_kinds(doc)["relationship_equality"] for doc in docs.values()
    ] == [1, 1, 0, 1, 1]


@pytest.mark.parametrize("target", TARGETS)
def test_a_relationship_join_of_two_distinct_reads_of_one_source_emits(
    tmp_path, target
):
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
relationship near:
    endpoint l: d1
    endpoint r: d2
    on l.id == r.id
query result:
    from d1
    inner join d2 as r:
        from d1
        via near: l -> r
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
    inner join prod as r:
        from prod
        on prod.pid == r.pid
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
        f"""table prod:
    from rhs
    let:
        step = id + 0
    where id > 0
    select:
        pid = step
query result:
    from lhs
    {kind} join prod as r:
        from lhs
        on lhs.id == r.pid
    select:
        a = lhs.id
""",
    )
    doc = public(outcome)
    assert doc["status"] == "VERIFIED"
    assert [column["label"] for column in doc["columns"]] == ["a"]
    # The right producer's own scan, filter and LET all survive inside the
    # membership wrapper even though nothing of it reaches the result.
    assert requirement_kinds(doc)["qualified_scan"] == 2
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
export:
    table prod
    table base
""",
            "b.pietto": 'import "a.pietto":\n'
            "    table prod as Mid\n    table base as Root\n"
            "export:\n    table Mid\n    table Root\n",
            "main.pietto": 'import "b.pietto":\n'
            "    table Mid as Public\n    table Root as Left\n"
            "query result:\n    from Left\n    inner join Public as r:\n"
            "        from Left\n        on Left.lid == r.pid\n"
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
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    let:
        doubled = lhs.id + 0
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
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    right join rhs as s:
        from lhs
        on lhs.id == s.id
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
    {kind} join rhs as m:
        from up
{mid_on}    select:
        id = up.id
        n = up.n
query result:
    from mid
    {kind} join rhs as z:
        from mid
{result_on}    select:
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
            mid_on="        on up.id == m.id\n" if inner else "",
            result_on="        on mid.id == z.id\n" if inner else "",
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


# A chain of two relationship JOINs that reads relations and relationships
# its module declares after it.
FORWARD_JOIN_CHAIN = """query result:
    from mid
{joins}    select:
        a = mid.id
        b = z.key
        c = w.key
relationship mr:
    endpoint m: mid
    endpoint r: rhs
    on m.id == r.id
relationship rd:
    endpoint r: rhs
    endpoint x: d
    on r.key == x.id
query d:
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
    "written": "    left join rhs as z:\n        from mid\n        via mr: m -> r\n"
    "    inner join d as w:\n        from z\n        via rd: r -> x\n",
    "inferred": "    left join rhs as z\n    inner join d as w\n",
    "header_steps": "    left join rhs as z: via mr\n    inner join d as w: from z\n",
}


@pytest.mark.parametrize("target", TARGETS)
def test_a_join_chain_over_later_declarations_infers_its_written_sql(tmp_path, target):
    header = probe.JOIN_WITNESS_HEADER.format(target=target)
    docs = [
        public(
            emit(
                tmp_path / name,
                target,
                {"main.pietto": FORWARD_JOIN_CHAIN.format(joins=joins) + header},
            )
        )
        for name, joins in FORWARD_JOINS.items()
    ]
    assert [doc["status"] for doc in docs] == ["VERIFIED"] * 3
    for key in ("sql", "columns"):
        assert [doc[key] for doc in docs] == [docs[0][key]] * 3, key
    assert [requirement_kinds(doc) for doc in docs] == [requirement_kinds(docs[0])] * 3


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
# A JOIN without `from` or VIA roles publishes its explicit form
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


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("kind", ("inner", "left", "right", "full", "semi", "anti"))
@pytest.mark.parametrize(
    ("explicit", "inferred"),
    (
        (":\n        from lhs\n", "\n"),
        (":\n        from lhs\n        via link: l -> r\n", ": via link\n"),
    ),
    ids=("direct", "via"),
)
def test_an_inferred_join_publishes_its_explicit_form(
    tmp_path, target, kind, explicit, inferred
):
    head = f"query result:\n    from lhs\n    {kind} join rhs as r"
    tail = "    select:\n        a = lhs.id\n"
    written, found = (
        document(emit(tmp_path / label, target, head + layout + tail, link=True))
        for label, layout in (("explicit", explicit), ("inferred", inferred))
    )
    assert found["status"] == written["status"]
    assert found.get("sql") == written.get("sql")
    assert _authored_layout_free(found) == _authored_layout_free(written)


@pytest.mark.parametrize("target", TARGETS)
def test_a_one_line_relationship_publishes_its_block_form(tmp_path, target):
    """Its endpoint roles are the relation names."""
    block = (
        "relationship link:\n    endpoint lhs: lhs\n    endpoint rhs: rhs\n"
        "    on lhs.id == rhs.id\n"
        "query result:\n    from lhs\n    inner join rhs as r:\n        from lhs\n"
        "        via link: lhs -> rhs\n    select:\n        a = lhs.id\n"
    )
    one_line = (
        "relationship link: lhs.id == rhs.id\n"
        "query result:\n    from lhs\n    inner join rhs as r: via link\n"
        "    select:\n        a = lhs.id\n"
    )
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
            "    let v:\n        values(id: Int not null):\n            1\n"
            "    from lhs\n    inner join v as vv:\n        from lhs\n"
            "        on vv.id == lhs.id\n",
            "lhs",
        ),
        (
            "    from generate_series(1, 3, 1) as n\n    inner join lhs as l:\n"
            "        from n\n        on l.id == n.n\n",
            "l",
        ),
    ),
    ids=("values_let", "table_function"),
)
def test_an_inferred_join_after_an_unmodelled_input_publishes_its_explicit_form(
    tmp_path, target, head, source
):
    """A VALUES or table-function binding with no relationship is no candidate."""
    tail = "    select:\n        a = r.id\n"
    written, found = (
        document(
            emit(
                tmp_path / label,
                target,
                f"query result:\n{head}    inner join rhs as r{layout}{tail}",
                link=True,
            )
        )
        for label, layout in (
            ("explicit", f":\n        from {source}\n"),
            ("inferred", "\n"),
        )
    )
    assert found["status"] == written["status"]
    assert target == "mysql" or written["status"] == "VERIFIED"
    assert found.get("sql") == written.get("sql")
    assert _authored_layout_free(found) == _authored_layout_free(written)


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
    left join prod as r:
        from lhs
        on lhs.id == r.pid
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
    "query result:\n    from rows\n    inner join rows as o:\n        from rows\n"
    "        on rows.id == o.id{on}\n{where}    select:\n        a = rows.id\n"
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
# JOIN reads it, whatever the field's nullability modifier.
ENUM_TEXT_DOMAIN = {
    "postgres": ({"kind": "pg_text"}, "UTF8", "C"),
    "mysql": ({"kind": "my_varchar", "length": 64}, "utf8mb4", "utf8mb4_0900_bin"),
}
ENUM_STATUS = ("enum Status:\n    active\n    closed\n", "Status")
SHAPE_PAYLOAD = ("shape Payload:\n    a: Int not null\n", "Payload")


def enum_field_document(directory, target, body, modifier, declared=ENUM_STATUS):
    item = probe.join_witness(target, body)
    declaration, type_name = declared
    source = declaration + item["source"].replace(
        "    key: Int nullable\n",
        f"    key: Int nullable\n    state: {type_name}{modifier}\n",
    )
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
                    "nullable": modifier == " nullable",
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


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("modifier", (" nullable", " not null"))
def test_an_enum_field_of_a_join_input_blocks_as_without_the_join(
    tmp_path, target, modifier
):
    field = {
        "path": "main.pietto",
        "line": 7,
        "column": 5,
        "end_line": 7,
        "end_column": 27,
    }
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
    window = "window:\n            order by:\n                id\n"
    field = {"path": "main.pietto", "line": 7, "column": 5}
    field |= {"end_line": 7, "end_column": 27}
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
            " not null",
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
    window = "window:\n            order by:\n                id\n"
    field = {"path": "main.pietto", "line": 6, "column": 5}
    field |= {"end_line": 6, "end_column": 28}
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
            " not null",
            SHAPE_PAYLOAD,
        )
        assert (published["status"], published["diagnostics"]) == ("BLOCKED", [])
        assert [
            (b["code"], b["subject"], b["location"]) for b in published["blockers"]
        ] == blocked


@pytest.mark.parametrize("target", TARGETS)
def test_a_window_of_a_join_relation_computed_column_emits(tmp_path, target):
    """A later relation's `last_value` and `lag` of a JOIN relation's computed
    columns, `v = r.id + 1` and `w = k + 1` with `k = r.id`, whose
    nullability is unknown, emit verified PostgreSQL; MySQL blocks the
    integer window result, as for any computed integer value. Before,
    `check --project` refused both windows with PIE-S2104 `value type must
    be concrete`."""
    window = "window:\n            order by:\n                id\n"
    item = probe.join_witness(
        target,
        "table joined:\n    from lhs\n    inner join rhs as r:\n        from lhs\n"
        "        on lhs.key == r.key\n    let:\n        k = r.id\n    select:\n"
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
                21,
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
