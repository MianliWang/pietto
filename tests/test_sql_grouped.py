"""GROUPED/GLOBAL aggregation, satisfying and aggregate result representations.

Every artifact below is produced by the installed emission path from an ordinary
authored project, and every verdict is taken from the independent public consumer
reading the published bytes. No production builder, realization function or
renderer is called to decide whether a public document is acceptable.
"""

import json
from typing import Any

import pytest

import _pietto_sql_emission as probe
from pietto._project.project_sql_emission_ast import SQLRowQuery
from pietto._project.project_sql_emission import serialize_project_sql_emission

TARGETS = ("postgres", "mysql")
SIGNED64 = "9223372036854775807"


def emit(tmp_path, target, case, variant):
    """One published aggregation fixture through the installed pipeline."""
    item = probe.fixture(target, case, variant)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    return outcome


def emit_source(tmp_path, target, body, *, policy="preserve_literals"):
    """One ad-hoc aggregation body over the fixed aggregation source shape."""
    item = probe.aggregate_fixture(target, "X_aggregate_grouped", "hidden")
    contract = json.loads(item["contract"])
    if policy == "bind_safe_literals":
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": "postgres_extended"
                if target == "postgres"
                else "mysql_prepared",
            }
        )
    header = probe.AGGREGATE_HEADER.format(target=target)
    _, outcome = probe.build_case(
        tmp_path, header + body, probe.encoded(contract).decode(), policy
    )
    return outcome


def document(outcome) -> dict[str, Any]:
    return json.loads(serialize_project_sql_emission(outcome).decode())


def public(outcome) -> dict[str, Any]:
    """The independent consumer's verdict over the published bytes alone."""
    return probe.decode_public(serialize_project_sql_emission(outcome))


def column(data, label):
    found = [item for item in data["columns"] if item["label"] == label]
    assert len(found) == 1
    return found[0]


def origin(data, label):
    correspondence = column(data, label)["correspondence"]
    return (
        correspondence.get("aggregate_origin") or correspondence["aggregate_transport"]
    )


# --------------------------------------------------------------------------
# Native grouping structure
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_a_global_aggregation_emits_no_grouping_at_all(tmp_path, target):
    data = document(emit(tmp_path, target, "X_aggregate_global", "bag"))
    assert "GROUP BY" not in data["sql"]
    assert data["sql"].count("COUNT(*)") == 1
    public(emit(tmp_path, target, "X_aggregate_global", "bag"))


@pytest.mark.parametrize("target", TARGETS)
def test_a_grouped_aggregation_binds_group_by_to_its_input_column(tmp_path, target):
    """GROUP BY names the actual pre-aggregate value, never an alias or ordinal."""
    outcome = emit(tmp_path, target, "X_aggregate_grouped", "hidden")
    sql = document(outcome)["sql"]
    quote = '"' if target == "postgres" else "`"
    binding = f" GROUP BY {quote}s0{quote}.{quote}group key{quote}"
    assert binding in sql
    assert " GROUP BY 1" not in sql and " GROUP BY 2" not in sql
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_constant_valued_determinant_groups_by_its_established_value(
    tmp_path, target
):
    """C10: the constant key is a producer port, not the ordinal position one."""
    outcome = emit(tmp_path, target, "Y_aggregate_constant", "grouped")
    sql = document(outcome)["sql"]
    quote = '"' if target == "postgres" else "`"
    assert f" GROUP BY {quote}s1{quote}.{quote}c1{quote}" in sql
    assert " GROUP BY 1" not in sql
    # The producer materializes the constant once; grouping reads that port.
    assert "CAST(1 AS " in sql and sql.index("CAST(1 AS ") < sql.index(" GROUP BY ")
    # The selected label is spelled exactly like a generated column name and
    # still captures nothing: the final SELECT names its own stage column.
    assert f"{quote}t2{quote}.{quote}c0{quote} AS {quote}c0{quote}" in sql
    public(outcome)


_PG_SCAN = (
    'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7") AS (SELECT'
    ' "s0"."group key" AS "c0", "s0"."value é" AS "c1", "s0"."flag value" AS "c2",'
    ' "s0"."text `""é" AS "c3", "s0"."amount value" AS "c4",'
    ' "s0"."ratio value" AS "c5", "s0"."row id" AS "c6", '
)
_MY_SCAN = (
    "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`) AS (SELECT"
    " `s0`.`group key` AS `c0`, `s0`.`value é` AS `c1`, `s0`.`flag value` AS `c2`,"
    ' `s0`.`text ``"é` AS `c3`, `s0`.`amount value` AS `c4`,'
    " `s0`.`ratio value` AS `c5`, `s0`.`row id` AS `c6`, "
)
_PG_CARRY = (
    ' "p1" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8") AS (SELECT'
    ' "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c2" AS "c2", "t1"."c3" AS "c3",'
    ' "t1"."c4" AS "c4", "t1"."c5" AS "c5", "t1"."c6" AS "c6", "t1"."c7" AS "c7", '
)
_MY_CARRY = (
    " `p1` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`, `c8`) AS (SELECT"
    " `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1`, `t1`.`c2` AS `c2`, `t1`.`c3` AS `c3`,"
    " `t1`.`c4` AS `c4`, `t1`.`c5` AS `c5`, `t1`.`c6` AS `c6`, `t1`.`c7` AS `c7`, "
)
_PG_TAIL = (
    ' "p2" ("c0", "c1", "c2") AS (SELECT "t2"."c7" AS "c0", COUNT(*) AS "c1",'
    ' MAX("t2"."c8") AS "c2" FROM "p1" AS "t2" GROUP BY "t2"."c7") SELECT'
    ' "t3"."c0" AS "b", "t3"."c1" AS "total", "t3"."c2" AS "top" FROM "p2" AS "t3"'
)
_MY_TAIL = (
    " `p2` (`c0`, `c1`, `c2`) AS (SELECT `t2`.`c7` AS `c0`, COUNT(*) AS `c1`,"
    " MAX(`t2`.`c8`) AS `c2` FROM `p1` AS `t2` GROUP BY `t2`.`c7`) SELECT"
    " `t3`.`c0` AS `b`, `t3`.`c1` AS `total`, `t3`.`c2` AS `top` FROM `p2` AS `t3`"
)
# S05g: each LET value is established once by its own stage; GROUP BY names the
# qualified LET column, never the expression, an ordinal or an output alias.
COMPUTED_SQL = {
    ("postgres", "let_key"): _PG_SCAN
    + '(CASE WHEN ("s0"."group key" > CAST(1 AS pg_catalog.int8)) THEN CAST(1 AS'
    ' pg_catalog.int8) ELSE CAST(0 AS pg_catalog.int8) END) AS "c7" FROM'
    ' "public"."phase66 agg é" AS "s0"),'
    + _PG_CARRY
    + '(CASE WHEN ("t1"."c1" > CAST(15 AS pg_catalog.int8)) THEN CAST(2 AS'
    ' pg_catalog.int8) ELSE CAST(1 AS pg_catalog.int8) END) AS "c8" FROM "p0" AS'
    ' "t1"),' + _PG_TAIL,
    ("postgres", "bind"): _PG_SCAN
    + '(CASE WHEN ("s0"."group key" > CAST($1 AS pg_catalog.int8)) THEN CAST($2 AS'
    ' pg_catalog.int8) ELSE CAST($3 AS pg_catalog.int8) END) AS "c7" FROM'
    ' "public"."phase66 agg é" AS "s0"),'
    + _PG_CARRY
    + '(CASE WHEN ("t1"."c1" > CAST($4 AS pg_catalog.int8)) THEN CAST($5 AS'
    ' pg_catalog.int8) ELSE CAST($6 AS pg_catalog.int8) END) AS "c8" FROM "p0" AS'
    ' "t1"),' + _PG_TAIL,
    ("mysql", "let_key"): _MY_SCAN
    + "(CASE WHEN (`s0`.`group key` > CAST(1 AS SIGNED)) THEN CAST(1 AS SIGNED)"
    " ELSE CAST(0 AS SIGNED) END) AS `c7` FROM `phase66`.`phase66 agg é` AS `s0`),"
    + _MY_CARRY
    + "(CASE WHEN (`t1`.`c1` > CAST(15 AS SIGNED)) THEN CAST(2 AS SIGNED)"
    " ELSE CAST(1 AS SIGNED) END) AS `c8` FROM `p0` AS `t1`)," + _MY_TAIL,
    ("mysql", "bind"): _MY_SCAN
    + "(CASE WHEN (`s0`.`group key` > CAST(? AS SIGNED)) THEN CAST(? AS SIGNED)"
    " ELSE CAST(? AS SIGNED) END) AS `c7` FROM `phase66`.`phase66 agg é` AS `s0`),"
    + _MY_CARRY
    + "(CASE WHEN (`t1`.`c1` > CAST(? AS SIGNED)) THEN CAST(? AS SIGNED)"
    " ELSE CAST(? AS SIGNED) END) AS `c8` FROM `p0` AS `t1`)," + _MY_TAIL,
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("variant", ("let_key", "bind"))
def test_a_computed_let_determinant_groups_by_its_let_stage_column(
    tmp_path, target, variant
):
    outcome = emit(tmp_path, target, "Y_aggregate_computed", variant)
    data = document(outcome)
    assert data["sql"] == COMPUTED_SQL[target, variant]
    assert data["sql"].count(" GROUP BY ") == 1
    assert data["sql"].count("CASE WHEN") == 2
    assert len(data["parameter_uses"]) == (6 if variant == "bind" else 0)
    # The determinant carries its LET-site proven range; MAX keeps the range of
    # its own LET argument and only gains the empty-input NULL.
    key, total, top = (column(data, label) for label in ("b", "total", "top"))
    assert key["representation"]["domain"] == {
        "kind": "int_range",
        "min": "0",
        "max": "1",
    }
    assert key["nullable"] is False
    assert total["nullable"] is False
    assert top["representation"]["domain"] == {
        "kind": "int_range",
        "min": "1",
        "max": "2",
    }
    assert top["nullable"] is True
    assert origin(data, "b")["role"] == "group_key"
    assert origin(data, "top")["function"] == "max"
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("let", "logical", "nullable"),
    (
        ("grp = value > 5", ("Bool", None), "unknown"),
        ("grp = lower(label)", ("Text", None), False),
        ("grp = abs(amount)", ("Decimal", {"precision": 9, "scale": 2}), False),
        ("grp = key + 0", ("Int", None), "unknown"),
        ("grp = 1.5 + 0.5", None, None),
        ("grp = ratio", None, None),
    ),
)
def test_computed_determinants_keep_the_reviewed_comparison_domains(
    tmp_path, target, let, logical, nullable
):
    """Bool, Text, Decimal and Int keep their domains; Float stays refused."""
    # A refused key is not selected, so its one blocker is the key's own.
    selected = "" if logical is None else "        g = grp\n"
    outcome = emit_source(
        tmp_path,
        target,
        f"""query result:
    from agg
    let:
        {let}
    group by:
        grp
    select:
{selected}        total = count()
""",
    )
    data = document(outcome)
    if logical is None:
        assert data["status"] == "BLOCKED"
        (blocker,) = data["blockers"]
        assert blocker["code"] == "PIE-B1003"
        assert blocker["subject"] == {
            "reference": {"kind": "group_key", "position": 0},
            "detail": "group_key_type_outside_reviewed_comparison_domain",
        }
    else:
        quote = '"' if target == "postgres" else "`"
        assert data["status"] == "VERIFIED"
        assert f" GROUP BY {quote}t1{quote}.{quote}c7{quote}" in data["sql"]
        key = column(data, "g")
        name, parameters = logical
        assert key["logical_type"] == {
            "kind": "builtin",
            "name": name,
            "parameters": parameters,
        }
        assert key["nullable"] == nullable
    public(outcome)


ORDERED_COMPUTED_KEY = """query result:
    from agg
    let:
        bucket = {value}
    group by:
        bucket
    select:
        b = bucket
        total = count()
    order by:
        b desc
"""


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("value", "nullable"), (("1 if key > 1 else 0", False), ("key + 0", "unknown"))
)
def test_grouped_order_by_a_computed_key_keeps_its_null_posture_law(
    tmp_path, target, value, nullable
):
    """Only a key whose LET value is proven non-null omits the NULL posture."""
    outcome = emit_source(tmp_path, target, ORDERED_COMPUTED_KEY.format(value=value))
    data = document(outcome)
    quote = '"' if target == "postgres" else "`"
    assert data["sql"].endswith(f" ORDER BY {quote}t0{quote}.{quote}c2{quote} DESC")
    assert column(data, "b")["nullable"] == nullable
    postures = [r for r in data["requirements"] if r["kind"] == "order_null_posture"]
    assert len(postures) == (0 if nullable is False else 1)
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("claim", ("column", "missing_posture", "redundant_posture"))
def test_public_null_claims_over_a_computed_key_follow_its_proof(
    tmp_path, target, claim
):
    """A nullable key keeps its posture; a proven key carries none."""
    value = "1 if key > 1 else 0" if claim == "redundant_posture" else "key + 0"
    data = document(
        emit_source(tmp_path, target, ORDERED_COMPUTED_KEY.format(value=value))
    )
    probe.decode_public(probe.encoded(data))
    requirements = data["requirements"]
    if claim == "column":
        key = column(data, "b")
        key["nullable"] = key["representation"]["nullable"] = False
        message = "NON_NULL claimed over a nullable operand: b"
    else:
        if claim == "missing_posture":
            (posture,) = (r for r in requirements if r["kind"] == "order_null_posture")
            requirements.remove(posture)
        else:
            (item,) = (r for r in requirements if r["kind"] == "order_item")
            requirements.insert(
                requirements.index(item) + 1, {**item, "kind": "order_null_posture"}
            )
        generated = (r for r in requirements if r["denominator"] == "generated")
        for ordinal, requirement in enumerate(generated):
            requirement["ordinal"] = ordinal
        message = "generated requirement denominator"
    with pytest.raises(ValueError, match=message):
        probe.decode_public(probe.encoded(data))


@pytest.mark.parametrize("target", TARGETS)
def test_global_extrema_over_a_let_value_keep_its_range(tmp_path, target):
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    let:
        weight = 2 if value > 15 else 1
    select:
        lo = min(weight)
        hi = max(weight)
""",
    )
    data = document(outcome)
    quote = '"' if target == "postgres" else "`"
    let_column = f"{quote}t1{quote}.{quote}c7{quote}"
    assert f"MIN({let_column})" in data["sql"] and f"MAX({let_column})" in data["sql"]
    for label in ("lo", "hi"):
        assert column(data, label)["representation"]["domain"] == {
            "kind": "int_range",
            "min": "1",
            "max": "2",
        }
        assert column(data, label)["nullable"] is True
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "mutation",
    (
        "other_let_column",
        "repeated_expression",
        "output_alias",
        "unqualified",
        "ordinal",
        "dropped",
    ),
)
def test_public_computed_determinant_corruptions_are_rejected(
    tmp_path, target, mutation
):
    data = document(emit(tmp_path, target, "Y_aggregate_computed", "let_key"))
    probe.decode_public(probe.encoded(data))
    sql = data["sql"]
    q = '"' if target == "postgres" else "`"
    int8 = "pg_catalog.int8" if target == "postgres" else "SIGNED"
    grouping = f" GROUP BY {q}t2{q}.{q}c7{q}"
    replacement = {
        "other_let_column": f" GROUP BY {q}t2{q}.{q}c8{q}",
        "repeated_expression": f" GROUP BY (CASE WHEN ({q}t2{q}.{q}c0{q} > CAST(1 AS"
        f" {int8})) THEN CAST(1 AS {int8}) ELSE CAST(0 AS {int8}) END)",
        "output_alias": f" GROUP BY {q}c0{q}",
        "unqualified": f" GROUP BY {q}c7{q}",
        "ordinal": " GROUP BY 1",
        "dropped": "",
    }[mutation]
    data["sql"] = sql.replace(grouping, replacement, 1)
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


# Each pair is one computation as a relation let and as a module query.
LET_FORMS = {
    "key_inside_let": (
        """query result:
    let g:
        from agg
        let:
            bucket = 1 if key > 1 else 0
        group by:
            bucket
        select:
            b = bucket
            total = count()
    from g
    select:
        b
        total
""",
        """query g:
    from agg
    let:
        bucket = 1 if key > 1 else 0
    group by:
        bucket
    select:
        b = bucket
        total = count()
query result:
    from g
    select:
        b
        total
""",
    ),
    "key_over_let": (
        """query result:
    let base:
        from agg
        select:
            key
            value
    from base
    let:
        bucket = 1 if key > 1 else 0
    group by:
        bucket
    select:
        b = bucket
        total = count()
""",
        """query base:
    from agg
    select:
        key
        value
query result:
    from base
    let:
        bucket = 1 if key > 1 else 0
    group by:
        bucket
    select:
        b = bucket
        total = count()
""",
    ),
}


# S05j: the JOIN image, then one LET stage that establishes the determinant from
# both sides once, then GROUP BY that qualified LET column only.
_PG_JOIN_LET = (
    'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8",'
    ' "c9", "c10", "c11", "c12", "c13") AS (SELECT "m0"."group key" AS'
    ' "c0", "m0"."value é" AS "c1", "m0"."flag value" AS "c2", "m0"."text'
    ' `""é" AS "c3", "m0"."amount value" AS "c4", "m0"."ratio value" AS'
    ' "c5", "m0"."row id" AS "c6", "m1"."group key" AS "c7", "m1"."value'
    ' é" AS "c8", "m1"."flag value" AS "c9", "m1"."text `""é" AS "c10",'
    ' "m1"."amount value" AS "c11", "m1"."ratio value" AS "c12", "m1"."row'
    ' id" AS "c13" FROM "public"."phase66 agg é" AS "m0" INNER JOIN'
    ' "public"."phase66 agg é" AS "m1" ON ("m0"."group key" = "m1"."group'
    ' key")), "p1" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8",'
    ' "c9", "c10", "c11", "c12", "c13", "c14") AS (SELECT "t0"."c0" AS'
    ' "c0", "t0"."c1" AS "c1", "t0"."c2" AS "c2", "t0"."c3" AS "c3",'
    ' "t0"."c4" AS "c4", "t0"."c5" AS "c5", "t0"."c6" AS "c6", "t0"."c7"'
    ' AS "c7", "t0"."c8" AS "c8", "t0"."c9" AS "c9", "t0"."c10" AS "c10",'
    ' "t0"."c11" AS "c11", "t0"."c12" AS "c12", "t0"."c13" AS "c13", '
)
_MY_JOIN_LET = (
    "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`, `c8`,"
    " `c9`, `c10`, `c11`, `c12`, `c13`) AS (SELECT `m0`.`group key` AS"
    " `c0`, `m0`.`value é` AS `c1`, `m0`.`flag value` AS `c2`, `m0`.`text"
    ' ``"é` AS `c3`, `m0`.`amount value` AS `c4`, `m0`.`ratio value` AS'
    " `c5`, `m0`.`row id` AS `c6`, `m1`.`group key` AS `c7`, `m1`.`value"
    ' é` AS `c8`, `m1`.`flag value` AS `c9`, `m1`.`text ``"é` AS `c10`,'
    " `m1`.`amount value` AS `c11`, `m1`.`ratio value` AS `c12`, `m1`.`row"
    " id` AS `c13` FROM `phase66`.`phase66 agg é` AS `m0` INNER JOIN"
    " `phase66`.`phase66 agg é` AS `m1` ON (`m0`.`group key` = `m1`.`group"
    " key`)), `p1` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`, `c8`,"
    " `c9`, `c10`, `c11`, `c12`, `c13`, `c14`) AS (SELECT `t0`.`c0` AS"
    " `c0`, `t0`.`c1` AS `c1`, `t0`.`c2` AS `c2`, `t0`.`c3` AS `c3`,"
    " `t0`.`c4` AS `c4`, `t0`.`c5` AS `c5`, `t0`.`c6` AS `c6`, `t0`.`c7`"
    " AS `c7`, `t0`.`c8` AS `c8`, `t0`.`c9` AS `c9`, `t0`.`c10` AS `c10`,"
    " `t0`.`c11` AS `c11`, `t0`.`c12` AS `c12`, `t0`.`c13` AS `c13`, "
)
_PG_JOIN_MID = (
    ' AS "c14" FROM "p0" AS "t0"), "p2" ("c0", "c1", "c2", "c3", "c4",'
    ' "c5", "c6", "c7", "c8", "c9", "c10", "c11", "c12", "c13", "c14",'
    ' "c15") AS (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c2"'
    ' AS "c2", "t1"."c3" AS "c3", "t1"."c4" AS "c4", "t1"."c5" AS "c5",'
    ' "t1"."c6" AS "c6", "t1"."c7" AS "c7", "t1"."c8" AS "c8",'
    ' "t1"."c9" AS "c9", "t1"."c10" AS "c10", "t1"."c11" AS "c11",'
    ' "t1"."c12" AS "c12", "t1"."c13" AS "c13", "t1"."c14" AS "c14", '
)
_MY_JOIN_MID = (
    " AS `c14` FROM `p0` AS `t0`), `p2` (`c0`, `c1`, `c2`, `c3`, `c4`,"
    " `c5`, `c6`, `c7`, `c8`, `c9`, `c10`, `c11`, `c12`, `c13`, `c14`,"
    " `c15`) AS (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1`, `t1`.`c2`"
    " AS `c2`, `t1`.`c3` AS `c3`, `t1`.`c4` AS `c4`, `t1`.`c5` AS `c5`,"
    " `t1`.`c6` AS `c6`, `t1`.`c7` AS `c7`, `t1`.`c8` AS `c8`,"
    " `t1`.`c9` AS `c9`, `t1`.`c10` AS `c10`, `t1`.`c11` AS `c11`,"
    " `t1`.`c12` AS `c12`, `t1`.`c13` AS `c13`, `t1`.`c14` AS `c14`, "
)
# MIN/MAX read the second LET stage's `level` column; GROUP BY reads `later`.
_PG_JOIN_TAIL = (
    ' AS "c15" FROM "p1" AS "t1"), "p3" ("c0", "c1", "c2", "c3") AS'
    ' (SELECT "t2"."c14" AS "c0", COUNT(*) AS "c1", MIN("t2"."c15") AS'
    ' "c2", MAX("t2"."c15") AS "c3" FROM "p2" AS "t2" GROUP BY'
    ' "t2"."c14") SELECT "t3"."c0" AS "b", "t3"."c1" AS "total",'
    ' "t3"."c2" AS "low", "t3"."c3" AS "top" FROM "p3" AS "t3"'
)
_MY_JOIN_TAIL = (
    " AS `c15` FROM `p1` AS `t1`), `p3` (`c0`, `c1`, `c2`, `c3`) AS"
    " (SELECT `t2`.`c14` AS `c0`, COUNT(*) AS `c1`, MIN(`t2`.`c15`) AS"
    " `c2`, MAX(`t2`.`c15`) AS `c3` FROM `p2` AS `t2` GROUP BY"
    " `t2`.`c14`) SELECT `t3`.`c0` AS `b`, `t3`.`c1` AS `total`,"
    " `t3`.`c2` AS `low`, `t3`.`c3` AS `top` FROM `p3` AS `t3`"
)
JOIN_COMPUTED_SQL = {
    ("postgres", "preserve_literals"): _PG_JOIN_LET
    + '(("t0"."c6" > "t0"."c13") OR ("t0"."c13" > CAST(12 AS pg_catalog.int8)))'
    + _PG_JOIN_MID
    + '("t1"."c13" + ("t1"."c6" * CAST(0 AS pg_catalog.int8)))'
    + _PG_JOIN_TAIL,
    ("postgres", "bind_safe_literals"): _PG_JOIN_LET
    + '(("t0"."c6" > "t0"."c13") OR ("t0"."c13" > CAST($1 AS pg_catalog.int8)))'
    + _PG_JOIN_MID
    + '("t1"."c13" + ("t1"."c6" * CAST($2 AS pg_catalog.int8)))'
    + _PG_JOIN_TAIL,
    ("mysql", "preserve_literals"): _MY_JOIN_LET
    + "((`t0`.`c6` > `t0`.`c13`) OR (`t0`.`c13` > CAST(12 AS SIGNED)))"
    + _MY_JOIN_MID
    + "(`t1`.`c13` + (`t1`.`c6` * CAST(0 AS SIGNED)))"
    + _MY_JOIN_TAIL,
    ("mysql", "bind_safe_literals"): _MY_JOIN_LET
    + "((`t0`.`c6` > `t0`.`c13`) OR (`t0`.`c13` > CAST(? AS SIGNED)))"
    + _MY_JOIN_MID
    + "(`t1`.`c13` + (`t1`.`c6` * CAST(? AS SIGNED)))"
    + _MY_JOIN_TAIL,
}
INT64_RANGE = {"kind": "int_range", "min": "-9223372036854775808", "max": SIGNED64}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("form", tuple(LET_FORMS))
def test_a_computed_key_inside_or_over_a_relation_let_groups_like_a_module_query(
    tmp_path, target, form
):
    let_form, module_form = LET_FORMS[form]
    outcome = emit_source(tmp_path / "let", target, let_form)
    data = document(outcome)
    module = document(emit_source(tmp_path / "module", target, module_form))
    assert data["status"] == module["status"] == "VERIFIED"
    assert data["sql"] == module["sql"]
    assert data["sql"].count(" GROUP BY ") == 1
    assert data["sql"].count("CASE WHEN") == 1
    assert column(data, "b")["nullable"] is False
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_joined_computed_key_inside_a_relation_let_matches_top_level(
    tmp_path, target
):
    """A JOIN inside a let treats a computed key exactly like a top-level JOIN."""

    def diagnostics(name, body):
        item = probe.join_witness(target, body)
        _, outcome = probe.build_case(
            tmp_path / name, item["source"], item["contract"], item["policy"]
        )
        data = document(outcome)
        assert data["status"] == "BLOCKED"
        return [
            (
                d["code"],
                d["location"]["line"],
                d["location"]["column"],
                d.get("message", d.get("subject")),
            )
            for d in (*data["diagnostics"], *data["blockers"])
        ]

    top = diagnostics(
        "top",
        """query result:
    from lhs
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    let:
        k = lhs.id + 1
    group by:
        k
    select:
        kk = k
        n = count()
""",
    )
    nested = diagnostics(
        "let",
        """query result:
    let pairs:
        from lhs
        inner join rhs as r:
            from lhs
            on lhs.id == r.id
        let:
            k = lhs.id + 1
        group by:
            k
        select:
            kk = k
            n = count()
    from pairs
    select:
        kk
        n
""",
    )
    # The key is admitted; only the unproven `lhs.id + 1` representation blocks.
    assert [item[0] for item in top] == ["PIE-B1002"]
    # The let body is one line lower and one indentation level deeper.
    assert nested == [
        (code, line + 1, column + 4, message) for code, line, column, message in top
    ]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_joined_computed_determinant_groups_by_its_let_stage_column(
    tmp_path, target, policy
):
    """Both JOIN sides feed the LET value once; GROUP BY never repeats it."""
    outcome = (
        emit(tmp_path, target, "Y_aggregate_computed", "join_key")
        if policy == "preserve_literals"
        else emit_source(tmp_path, target, probe.AGGREGATE_COMPUTED_JOIN, policy=policy)
    )
    data = document(outcome)
    assert data["sql"] == JOIN_COMPUTED_SQL[target, policy]
    assert data["sql"].count(" GROUP BY ") == 1
    assert len(data["parameter_uses"]) == (2 if policy == "bind_safe_literals" else 0)
    assert origin(data, "b")["role"] == "group_key"
    # The joined LET value carries no stronger nullability claim than proven.
    assert column(data, "b")["nullable"] == "unknown"
    # MIN/MAX keep the LET site's proven range (here the whole Int carrier)
    # and only gain the empty-group NULL.
    for label, function in (("low", "min"), ("top", "max")):
        assert origin(data, label)["function"] == function
        assert column(data, label)["representation"]["domain"] == INT64_RANGE
        assert column(data, label)["nullable"] is True
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_joined_extrema_keep_a_narrow_let_site_range(tmp_path, target):
    """The result range is the LET value's own proof, not the field's."""
    outcome = emit_source(
        tmp_path,
        target,
        probe.AGGREGATE_COMPUTED_JOIN.replace(
            "level = r.rid + agg.rid * 0", "level = r.rid * 0 + agg.rid * 0"
        ),
    )
    data = document(outcome)
    for label in ("low", "top"):
        assert column(data, label)["representation"]["domain"] == {
            "kind": "int_range",
            "min": "0",
            "max": "0",
        }
        assert column(data, label)["nullable"] is True
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "header, value, policy",
    (
        ("", "3", "preserve_literals"),
        ("", "3 * 2 + 1", "bind_safe_literals"),
        ("(p: Int nullable)", "p + 1", "bind_safe_literals"),
    ),
)
def test_joined_extrema_over_a_field_free_let_value_match_the_module_form(
    tmp_path, target, header, value, policy
):
    """A12: a LET value that reads no joined field (a constant or a parameter)
    keeps the module form's MIN/MAX result; it links no JOIN side, so the group
    keys must fix both sides, exactly as for a direct field argument."""
    joined = (
        f"query result{header}:\n    from agg\n    inner join agg as r:\n"
        "        from agg\n        on agg.key == r.key\n"
        f"    let:\n        level = {value}\n    group by:\n{{keys}}"
        "    select:\n        a = agg.rid\n        low = min({arg})\n"
        "        top = max({arg})\n"
    )
    module = (
        f"query result{header}:\n    from agg\n    let:\n        level = {value}\n"
        "    group by:\n        rid\n    select:\n        a = rid\n"
        "        low = min(level)\n        top = max(level)\n"
    )
    both = "        agg.rid\n        r.rid\n"
    outcome = emit_source(
        tmp_path / "join",
        target,
        joined.format(keys=both, arg="level"),
        policy=policy,
    )
    data, expected = (
        document(outcome),
        document(emit_source(tmp_path / "module", target, module, policy=policy)),
    )
    assert data["status"] == expected["status"] == "VERIFIED"
    for label in ("low", "top"):
        assert column(data, label)["nullable"] is True
        assert (
            column(data, label)["representation"]
            == column(expected, label)["representation"]
        )
    public(outcome)
    # With only the left key the right side fans out: the field-free value is
    # refused exactly like MIN/MAX over the left side's own field.
    left = "        agg.rid\n"
    refused, direct = (
        document(
            emit_source(
                tmp_path / name,
                target,
                joined.format(keys=left, arg=arg),
                policy=policy,
            )
        )
        for name, arg in (("free", "level"), ("field", "agg.value"))
    )
    assert refused["status"] == direct["status"] == "BLOCKED"
    assert (
        [(d["code"], d["message"]) for d in refused["diagnostics"]]
        == [(d["code"], d["message"]) for d in direct["diagnostics"]]
        == [
            ("PIE-S2333", "Project relation semantic completion is unavailable: result")
        ]
    )


@pytest.mark.parametrize("target", TARGETS)
def test_a_joined_computed_key_output_filters_and_orders_the_result(tmp_path, target):
    """`satisfying` and grouped ORDER BY name the selected key's output."""
    outcome = emit_source(
        tmp_path,
        target,
        probe.AGGREGATE_COMPUTED_JOIN
        + "    satisfying:\n        b\n    order by:\n        b desc\n",
    )
    data = document(outcome)
    q = '"' if target == "postgres" else "`"
    # The grouped key result c0 is filtered, carried as the ordering column c4
    # and ordered; nothing re-evaluates the LET expression.
    for fragment in (
        f" FROM {q}p3{q} AS {q}t3{q} WHERE {q}t3{q}.{q}c0{q})",
        f", {q}t4{q}.{q}c0{q} AS {q}c4{q} FROM {q}p4{q} AS {q}t4{q})",
    ):
        assert fragment in data["sql"]
    assert data["sql"].endswith(
        f" FROM {q}p5{q} AS {q}t0{q} ORDER BY {q}t0{q}.{q}c4{q} DESC"
    )
    public(outcome)


@pytest.mark.parametrize(
    "mutation",
    ("other_join_column", "repeated_expression", "ordinal", "extremum_field"),
)
def test_public_joined_computed_determinant_corruptions_are_rejected(
    tmp_path, mutation
):
    data = document(emit(tmp_path, "postgres", "Y_aggregate_computed", "join_key"))
    sql = data["sql"]
    original, replacement = {
        "other_join_column": (' GROUP BY "t2"."c14"', ' GROUP BY "t2"."c13"'),
        "repeated_expression": (
            ' GROUP BY "t2"."c14"',
            ' GROUP BY (("t2"."c6" > "t2"."c13") OR'
            ' ("t2"."c13" > CAST(12 AS pg_catalog.int8)))',
        ),
        "ordinal": (' GROUP BY "t2"."c14"', " GROUP BY 1"),
        # MAX over the right rid field instead of its established LET value.
        "extremum_field": ('MAX("t2"."c15")', 'MAX("t2"."c13")'),
    }[mutation]
    data["sql"] = sql.replace(original, replacement, 1)
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


@pytest.mark.parametrize("target", TARGETS)
def test_a_hidden_determinant_stays_out_of_the_visible_result(tmp_path, target):
    outcome = emit(tmp_path, target, "X_aggregate_grouped", "hidden")
    data = document(outcome)
    assert [item["label"] for item in data["columns"]] == ["total", "cf"]
    # The determinant is still a real grouping column inside the stage.
    assert " GROUP BY " in data["sql"]
    assert all(
        item["correspondence"]["aggregate_origin"]["role"] == "aggregate_result"
        for item in data["columns"]
    )
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_multiple_determinants_keep_their_order_rename_and_repeat(tmp_path, target):
    outcome = emit(tmp_path, target, "X_aggregate_grouped", "visible")
    data = document(outcome)
    assert [item["label"] for item in data["columns"]] == [
        "f",
        "renamed",
        "again",
        "total",
    ]
    # Two visible outputs project the same determinant; each keeps its own
    # projection while naming the one retained group key.
    first, second = origin(data, "renamed"), origin(data, "again")
    assert first["determinant"] == second["determinant"]
    assert (
        column(data, "renamed")["correspondence"]["projection"]
        != column(data, "again")["correspondence"]["projection"]
    )
    assert origin(data, "f")["determinant"] != first["determinant"]
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_two_identical_declarations_keep_two_result_ports(tmp_path, target):
    """No CSE: repeated aggregates are distinct occurrences with distinct ports."""
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    select:
        a = count()
        b = count()
""",
    )
    data = document(outcome)
    assert data["sql"].count("COUNT(*)") == 2
    left, right = origin(data, "a"), origin(data, "b")
    assert left["aggregate"] != right["aggregate"]
    assert left["result"] != right["result"]
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_no_representative_row_repair_is_emitted(tmp_path, target):
    """ONLY_FULL_GROUP_BY stays on: no ANY_VALUE and no wrapping repair."""
    for variant in ("hidden", "visible"):
        sql = document(emit(tmp_path, target, "X_aggregate_grouped", variant))["sql"]
        assert "ANY_VALUE" not in sql and "any_value" not in sql
        assert "DISTINCT" not in sql
        assert "sql_mode" not in sql.lower()


# --------------------------------------------------------------------------
# Function identity and result domains
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_each_promised_function_keeps_its_own_spelling(tmp_path, target):
    outcome = emit(tmp_path, target, "X_aggregate_global", "bag")
    data = document(outcome)
    sql = data["sql"]
    quote = '"' if target == "postgres" else "`"
    value = f"{quote}s0{quote}.{quote}value é{quote}"
    assert "COUNT(*)" in sql
    assert f"COUNT({value})" in sql
    assert f"COUNT(DISTINCT {value})" in sql
    assert f"MIN({value})" in sql and f"MAX({value})" in sql
    assert [
        origin(data, label)["function"] for label in ("c", "cf", "cd", "lo", "hi")
    ] == [
        "count",
        "count",
        "count_distinct",
        "min",
        "max",
    ]
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_row_count_declares_the_whole_input_and_no_argument(tmp_path, target):
    """Count's empty scalar argument set is not an empty dependency set."""
    data = document(emit(tmp_path, target, "X_aggregate_global", "bag"))
    row_count, field_count = origin(data, "c"), origin(data, "cf")
    assert row_count["arguments"] == []
    assert len(row_count["inputs"]) == 7
    assert len(field_count["arguments"]) == 1 and len(field_count["inputs"]) == 1
    assert field_count["inputs"] != row_count["inputs"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_count_result_is_non_null_and_not_its_argument_range(tmp_path, target):
    data = document(emit(tmp_path, target, "X_aggregate_global", "bag"))
    for label in ("c", "cf", "cd"):
        published = column(data, label)
        assert published["nullable"] is False
        assert published["representation"]["domain"] == {
            "kind": "int_range",
            "min": "0",
            "max": SIGNED64,
        }
        assert published["representation"]["storage"] == {
            "kind": "pg_int8" if target == "postgres" else "my_bigint"
        }


@pytest.mark.parametrize("target", TARGETS)
def test_an_extreme_value_admits_null_over_a_non_null_argument(tmp_path, target):
    """An empty or all-null input has no extreme value, so the result is nullable."""
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    select:
        lo = min(rid)
        hi = max(rid)
""",
    )
    data = document(outcome)
    source_field = [item for item in data["columns"] if item["label"] == "lo"][0][
        "representation"
    ]
    assert source_field["nullable"] is True
    assert source_field["domain"] == {
        "kind": "int_range",
        "min": "-9007199254740993",
        "max": "9007199254740993",
    }
    assert column(data, "hi")["nullable"] is True
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_count_result_does_not_license_wider_arithmetic(tmp_path, target):
    """A nonnegative signed64 count cannot be incremented without overflow room."""
    outcome = emit_source(
        tmp_path,
        target,
        """table grouped:
    from agg
    select:
        total = count()
query result:
    from grouped
    select:
        bumped = total + total
""",
    )
    assert outcome.status == "BLOCKED"
    assert any(
        item.code == "PIE-B1002" and item.detail == "arithmetic_outside_physical_range"
        for item in outcome.blockers
    )


# --------------------------------------------------------------------------
# Empty input and NULL behavior
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("variant", "mode", "empty_input"),
    (
        ("bag", "global", "one_global_row"),
        ("empty", "global", "one_global_row"),
        ("all_null", "global", "one_global_row"),
        ("where_false", "global", "one_global_row"),
    ),
)
def test_a_global_result_declares_its_one_row_disposition(
    tmp_path, target, variant, mode, empty_input
):
    data = document(emit(tmp_path, target, "X_aggregate_global", variant))
    for label in ("c", "cf", "cd", "lo", "hi"):
        item = origin(data, label)
        assert (item["mode"], item["empty_input"]) == (mode, empty_input)


@pytest.mark.parametrize("target", TARGETS)
def test_a_grouped_result_declares_zero_groups_on_empty_input(tmp_path, target):
    data = document(emit(tmp_path, target, "X_aggregate_grouped", "empty"))
    assert origin(data, "total")["empty_input"] == "no_groups"
    assert origin(data, "total")["mode"] == "grouped"


@pytest.mark.parametrize("target", TARGETS)
def test_a_false_pre_input_filter_keeps_the_global_row_stage(tmp_path, target):
    """WHERE false is its own stage below the aggregation, never a folded result."""
    outcome = emit(tmp_path, target, "X_aggregate_global", "where_false")
    sql = document(outcome)["sql"]
    assert " WHERE " in sql and sql.index(" WHERE ") < sql.rindex("COUNT(*)")
    public(outcome)


# --------------------------------------------------------------------------
# satisfying
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_satisfying_is_one_post_aggregation_predicate_over_result_columns(
    tmp_path, target
):
    outcome = emit(tmp_path, target, "Y_aggregate_satisfying", "retained")
    sql = document(outcome)["sql"]
    quote = '"' if target == "postgres" else "`"
    # The aggregation publishes its own stage; the predicate reads that stage's
    # result columns in a later SELECT, never the pre-aggregate input.
    grouping = sql.index(" GROUP BY ")
    predicate = sql.rindex(" WHERE ")
    assert grouping < predicate
    # The predicate reads the aggregation stage's own result columns.
    assert f"{quote}t1{quote}.{quote}c1{quote} <" in sql
    assert f"{quote}t1{quote}.{quote}c2{quote} >" in sql
    assert "HAVING" not in sql
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_satisfying_use_is_a_use_and_not_a_new_computation(tmp_path, target):
    """Three authored references resolve to one already-established result."""
    outcome = emit(tmp_path, target, "Y_aggregate_satisfying", "retained")
    sql = document(outcome)["sql"]
    assert sql.count("COUNT(*)") == 1 and sql.count("MIN(") == 1
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_unique_aggregate_let_reference_reuses_its_result_port(tmp_path, target):
    outcome = emit(tmp_path, target, "Y_aggregate_satisfying", "let_reference")
    sql = document(outcome)["sql"]
    assert sql.count("COUNT(") == 1
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_a_satisfying_literal_stays_specialized_under_bind_safe(tmp_path, target):
    """The extraction rule never admits a satisfying slot; a WHERE literal binds."""
    bound = document(emit(tmp_path, target, "Y_aggregate_satisfying", "bind"))
    assert bound["request"]["literal_policy"] == "bind_safe_literals"
    assert bound["parameter_uses"] == [] and bound["fixed_values"] == []
    preserved = document(emit(tmp_path, target, "Y_aggregate_satisfying", "retained"))
    assert preserved["sql"] == bound["sql"]
    public(emit(tmp_path, target, "Y_aggregate_satisfying", "bind"))


@pytest.mark.parametrize("target", TARGETS)
def test_a_pre_group_filter_literal_still_binds(tmp_path, target):
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    where key > 0
    group by:
        key
    select:
        total = count()
""",
        policy="bind_safe_literals",
    )
    data = document(outcome)
    assert len(data["fixed_values"]) == 1 and len(data["parameter_uses"]) == 1
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_filtering_before_and_after_aggregation_are_different_stages(tmp_path, target):
    before = document(emit(tmp_path, target, "Y_aggregate_satisfying", "before_input"))
    after = document(emit(tmp_path, target, "Y_aggregate_satisfying", "retained"))
    assert before["sql"].index(" WHERE ") < before["sql"].index(" GROUP BY ")
    assert after["sql"].index(" GROUP BY ") < after["sql"].rindex(" WHERE ")


@pytest.mark.parametrize("target", TARGETS)
def test_global_with_satisfying_stays_rejected_at_its_own_boundary(tmp_path, target):
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    select:
        total = count()
    satisfying:
        total > 1
""",
    )
    assert outcome.status == "BLOCKED"
    assert [item.code for item in outcome.diagnostics] == ["PIE-S2323"]


# --------------------------------------------------------------------------
# Numeric proof boundaries
# --------------------------------------------------------------------------


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("variant", ("sum_direct", "sum_hidden_right"))
def test_sum_requires_an_actual_aggregate_range_proof(tmp_path, target, variant):
    outcome = emit(tmp_path, target, "V_aggregate_blocked", variant)
    assert outcome.status == "BLOCKED"
    assert [(item.code, item.detail) for item in outcome.blockers] == [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing")
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_avg_int_casts_the_target_result_to_the_finite_float_carrier(tmp_path, target):
    outcome = emit(tmp_path, target, "V_aggregate_blocked", "avg_direct")
    assert outcome.status == "VERIFIED"
    data = document(outcome)
    assert column(data, "a")["logical_type"] == {
        "kind": "builtin",
        "name": "Float",
        "parameters": None,
    }
    assert column(data, "a")["representation"] == {
        "storage": {"kind": "pg_float8" if target == "postgres" else "my_double"},
        "nullable": True,
        "domain": {"kind": "finite_float", "format": "binary64"},
    }
    cast = "pg_catalog.float8" if target == "postgres" else "DOUBLE"
    assert "AVG(CAST(" in data["sql"] and f" AS {cast}))" in data["sql"]
    assert "CAST(AVG(" not in data["sql"]
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("expression", "detail"),
    (
        ("sum(amount)", "decimal_aggregate_range_proof_missing"),
        ("avg(amount)", "decimal_aggregate_range_proof_missing"),
        ("sum(ratio)", "float_aggregate_finite_result_proof_missing"),
        ("avg(ratio)", "float_aggregate_finite_result_proof_missing"),
    ),
)
def test_numeric_aggregate_domains_require_proofs_beyond_source_declarations(
    tmp_path, target, expression, detail
):
    outcome = emit_source(
        tmp_path,
        target,
        f"""query result:
    from agg
    select:
        value = {expression}
""",
    )
    assert outcome.status == "BLOCKED"
    assert [(item.code, item.detail) for item in outcome.blockers] == [
        ("PIE-B1004", detail)
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_a_float_determinant_stays_outside_group_comparison(tmp_path, target):
    outcome = emit(tmp_path, target, "V_aggregate_blocked", "float_key")
    assert outcome.status == "BLOCKED"
    assert any(
        item.detail == "group_key_type_outside_reviewed_comparison_domain"
        for item in outcome.blockers
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("variant", ("bool_domain_key", "decimal_parameter_key"))
def test_a_violated_determinant_domain_is_a_representation_failure(
    tmp_path, target, variant
):
    outcome = emit(tmp_path, target, "V_aggregate_blocked", variant)
    assert outcome.status == "BLOCKED"
    assert all(item.code == "PIE-B1002" for item in outcome.blockers)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("variant", ("bool_key", "text_key", "decimal_key"))
def test_the_reviewed_determinant_domains_still_emit(tmp_path, target, variant):
    """The negatives above are domain failures, not a refusal of every key type."""
    outcome = emit(tmp_path, target, "Y_aggregate_domains", variant)
    assert outcome.status == "VERIFIED"
    public(outcome)


@pytest.mark.parametrize("target", TARGETS)
def test_an_aggregate_argument_must_be_one_direct_established_field(tmp_path, target):
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    select:
        total = count_distinct(label)
""",
    )
    assert outcome.status == "BLOCKED"
    assert any(
        item.detail == "count_distinct_argument_outside_reviewed_int_domain"
        for item in outcome.blockers
    )


# --------------------------------------------------------------------------
# Independent public consumer: finite mutations
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "mutation",
    (
        "count_form",
        "distinct_modifier",
        "grouping_column",
        "grouping_ordinal",
        "extra_grouping_key",
        "dropped_grouping",
        "satisfying_operator",
    ),
)
def test_public_aggregate_byte_corruptions_are_rejected(tmp_path, mutation):
    case, variant = (
        ("Y_aggregate_satisfying", "retained")
        if mutation == "satisfying_operator"
        else ("X_aggregate_global", "bag")
        if mutation in {"count_form", "distinct_modifier"}
        else ("X_aggregate_grouped", "hidden")
    )
    data = document(emit(tmp_path, "postgres", case, variant))
    sql = data["sql"]
    if mutation == "count_form":
        data["sql"] = sql.replace('COUNT("s0"."value é")', "COUNT(*)", 1)
    elif mutation == "distinct_modifier":
        data["sql"] = sql.replace('COUNT(DISTINCT "s0"."value é")', "COUNT(*)", 1)
    elif mutation == "grouping_column":
        data["sql"] = sql.replace(
            ' GROUP BY "s0"."group key"', ' GROUP BY "s0"."value é"', 1
        )
    elif mutation == "grouping_ordinal":
        data["sql"] = sql.replace(' GROUP BY "s0"."group key"', " GROUP BY 1", 1)
    elif mutation == "extra_grouping_key":
        data["sql"] = sql.replace(
            ' GROUP BY "s0"."group key"',
            ' GROUP BY "s0"."group key", "s0"."value é"',
            1,
        )
    elif mutation == "dropped_grouping":
        data["sql"] = sql.replace(' GROUP BY "s0"."group key"', "", 1)
    else:
        data["sql"] = sql.replace(" < ", " > ", 1)
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


@pytest.mark.parametrize(
    "mutation",
    (
        "mode",
        "empty_input",
        "function",
        "determinant",
        "result_port",
        "input_port",
        "arguments",
    ),
)
def test_public_aggregate_provenance_corruptions_are_rejected(tmp_path, mutation):
    data = document(emit(tmp_path, "postgres", "X_aggregate_global", "bag"))
    target = column(data, "cf")["correspondence"]["aggregate_origin"]
    other = column(data, "cd")["correspondence"]["aggregate_origin"]
    if mutation == "mode":
        target["mode"] = "grouped"
    elif mutation == "empty_input":
        target["empty_input"] = "no_groups"
    elif mutation == "function":
        target["function"] = "count_distinct"
    elif mutation == "determinant":
        target["determinant"] = {"kind": "group_key", "position": 0}
    elif mutation == "result_port":
        target["result"] = other["result"]
    elif mutation == "input_port":
        target["inputs"] = column(data, "c")["correspondence"]["aggregate_origin"][
            "inputs"
        ]
    else:
        target["arguments"] = []
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


@pytest.mark.parametrize(
    "kinds",
    (
        ("aggregation",),
        ("group_key",),
        ("aggregate",),
        ("result_projection",),
        ("satisfying_root",),
    ),
)
def test_deleting_an_aggregate_requirement_family_is_rejected(tmp_path, kinds):
    case, variant = (
        ("Y_aggregate_satisfying", "retained")
        if "satisfying_root" in kinds
        else ("X_aggregate_grouped", "hidden")
    )
    data = document(emit(tmp_path, "postgres", case, variant))
    before = len(data["requirements"])
    data["requirements"] = [
        item for item in data["requirements"] if item["kind"] not in kinds
    ]
    assert len(data["requirements"]) < before
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


def test_a_coordinated_stage_and_requirement_deletion_is_rejected(tmp_path):
    """Removing a determinant everywhere must still fail the input denominator."""
    data = document(emit(tmp_path, "postgres", "X_aggregate_grouped", "hidden"))
    sql = data["sql"]
    data["sql"] = sql.replace(' GROUP BY "s0"."group key"', "", 1).replace(
        '"s0"."group key" AS "c0", ', "", 1
    )
    data["requirements"] = [
        item for item in data["requirements"] if item["kind"] != "group_key"
    ]
    assert data["sql"] != sql
    with pytest.raises(ValueError):
        probe.decode_public(probe.encoded(data))


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("case", "variant"),
    (
        ("X_aggregate_global", "bag"),
        ("X_aggregate_global", "empty"),
        ("X_aggregate_grouped", "hidden"),
        ("X_aggregate_grouped", "visible"),
        ("Y_aggregate_constant", "grouped"),
        ("Y_aggregate_satisfying", "retained"),
        ("Y_aggregate_domains", "text_key"),
    ),
)
def test_valid_aggregate_documents_are_still_accepted(tmp_path, target, case, variant):
    """The controls above must not have turned into a refusal of every document."""
    assert public(emit(tmp_path, target, case, variant))["status"] == "VERIFIED"


# --------------------------------------------------------------------------
# Bounded failure reporting
# --------------------------------------------------------------------------


REPR_LIMIT = 1024


def test_an_aggregate_outcome_repr_stays_bounded(tmp_path):
    """A failing aggregate assertion must not allocate the whole shared graph."""
    item = probe.fixture("postgres", "X_aggregate_grouped", "visible")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    for text in (repr(outcome), repr(artifact)):
        assert len(text) < REPR_LIMIT
    # The realized aggregation stage is graph bearing; its own display must stay
    # a bounded summary rather than an expansion of every retained product.
    query = artifact.ast
    assert type(query) is SQLRowQuery
    body = [item for item in query.bodies if item.aggregation is not None]
    assert len(body) == 1
    assert len(repr(body[0].aggregation)) < REPR_LIMIT
