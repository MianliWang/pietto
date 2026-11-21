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
import _pietto_sql_float_cells as float_cells
from pietto._project.check import check_project_parse_only
from pietto._project import project_sql_emission_aggregation as grouping
from pietto._project.project_sql_emission_ast import SQLRowQuery
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)

TARGETS = ("postgres", "mysql")
SIGNED64 = "9223372036854775807"
CHECKED = [{"overflow": "target_checked_signed64_narrowing"}]


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


def test_postgres_string_agg_keeps_its_internal_order_inputs(tmp_path):
    outcome = emit_source(
        tmp_path,
        "postgres",
        "table result:\n    from agg\n    select:\n"
        '        summary = string_agg(label, "//", order by key desc, label)\n',
    )
    data = document(outcome)
    assert data["status"] == "VERIFIED"
    sql = data["sql"]
    assert "string_agg(" in sql and " ORDER BY " in sql
    assert '"s0"."group key" DESC, "s0"."text `""é" ASC' in sql
    assert column(data, "summary")["nullable"] is True

    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).request.family == "postgres"


def test_postgres_string_agg_compiled_order_keys_keep_scalar_operations(tmp_path):
    outcome = emit_source(
        tmp_path,
        "postgres",
        "table result:\n    from agg\n    select:\n"
        '        summary = string_agg(label, "//", order by lower(label) desc, lower(label))\n',
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    sql = document(outcome)["sql"]
    assert sql.count("lower(") >= 2 and " DESC" in sql and " ASC" in sql

    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).request.family == "postgres"


@pytest.mark.parametrize("target", TARGETS)
def test_a_group_key_over_another_relations_window_result_emits(tmp_path, target):
    """A GROUP BY key over another table's `rank()` column is that window
    result: the emitted key and its projected column keep the read's window
    origin, and the independent verifier rebuilds them with it (it once
    rebuilt them without, and the query was BLOCKED PIE-B1008)."""
    outcome = emit_source(
        tmp_path,
        target,
        "table ranked:\n    from agg\n    select:\n"
        "        rk = rank() window(order by rid)\n"
        "query result:\n    from ranked\n    group by ranked.rk\n    select:\n"
        "        rk = ranked.rk\n        n = count()\n",
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    data = public(outcome)
    assert column(data, "rk")["logical_type"]["name"] == "Int"
    quote = '"' if target == "postgres" else "`"
    assert f" GROUP BY {quote}s1{quote}.{quote}c0{quote}" in data["sql"]


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


GROUPED_OVER_GLOBAL_SQL = {
    "postgres": 'WITH "p0" ("c0") AS (SELECT COUNT(*) AS "c0" FROM "public".'
    '"phase66 agg é" AS "s0"), "p1" ("c0") AS (SELECT "t1"."c0" AS "c0" FROM '
    '"p0" AS "t1"), "p2" ("c0", "c1") AS (SELECT "s1"."c0" AS "c0", COUNT(*) '
    'AS "c1" FROM "p1" AS "s1" GROUP BY "s1"."c0") SELECT "t3"."c0" AS "c", '
    '"t3"."c1" AS "k" FROM "p2" AS "t3"',
    "mysql": "WITH `p0` (`c0`) AS (SELECT COUNT(*) AS `c0` FROM `phase66`."
    "`phase66 agg é` AS `s0`), `p1` (`c0`) AS (SELECT `t1`.`c0` AS `c0` FROM "
    "`p0` AS `t1`), `p2` (`c0`, `c1`) AS (SELECT `s1`.`c0` AS `c0`, COUNT(*) "
    "AS `c1` FROM `p1` AS `s1` GROUP BY `s1`.`c0`) SELECT `t3`.`c0` AS `c`, "
    "`t3`.`c1` AS `k` FROM `p2` AS `t3`",
}


@pytest.mark.parametrize("target", TARGETS)
def test_a_grouped_aggregation_over_a_global_table_groups_its_one_row(tmp_path, target):
    """GROUP BY over a table that is one global aggregate row groups that row.
    Before, its input's empty grain made a dependency with no determinants, and
    `check --project` and `emit-sql --project` of either relation raised a
    TypeError."""
    outcome = emit_source(
        tmp_path,
        target,
        "table totals:\n    from agg\n    select:\n        c = count()\n"
        "query result:\n    from totals\n    group by c\n    select:\n"
        "        c\n        k = count()\n",
    )
    data = document(outcome)
    assert data["status"] == "VERIFIED"
    assert data["sql"] == GROUPED_OVER_GLOBAL_SQL[target]
    assert [(item["label"], item["nullable"]) for item in data["columns"]] == [
        ("c", False),
        ("k", False),
    ]
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
        ("grp = 1.5 + 0.5", ("Float", None), "unknown"),
        ("grp = Float(key)", ("Float", None), True),
        ("grp = abs(ratio)", ("Float", None), False),
        ("grp = -0.0 if key > 0 else 0.0", ("Float", None), False),
        ("grp = ratio * 2.0", ("Float", None), "unknown"),
    ),
)
def test_computed_determinants_keep_the_reviewed_comparison_domains(
    tmp_path, target, let, logical, nullable
):
    """Bool, Text, Decimal, Int and (on PostgreSQL) Float keep their domains.
    MySQL kept -0.0 and 0.0 in two groups beside a wide key, so its Float key
    stays refused; its Float field arithmetic is refused first (E4 opens it on
    PostgreSQL only)."""
    if logical is not None and logical[0] == "Float" and target == "mysql":
        logical = None
    # A refused key is not selected, so its one blocker is the key's own.
    selected = "" if logical is None else "        g = grp\n"
    outcome = emit_source(
        tmp_path,
        target,
        f"""query result:
    from agg
    let {let}
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
        if "*" in let:
            assert blocker["subject"]["detail"] == "float_literal_operands_required"
            return
        assert blocker["subject"] == {
            "reference": {"kind": "group_key", "position": 0},
            "detail": "group_key_type_outside_reviewed_comparison_domain",
        }
    else:
        quote = '"' if target == "postgres" else "`"
        assert data["status"] == "VERIFIED"
        assert f" GROUP BY {quote}t1{quote}.{quote}c7{quote}" in data["sql"]
        if "-0.0" in let:
            # The LET stage computes the key once; -0.0 keeps its own carrier.
            assert "THEN (-CAST('0.0' AS pg_catalog.float8)) ELSE" in data["sql"]
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
    let bucket = {value}
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
    let weight = 2 if value > 15 else 1
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
        let bucket = 1 if key > 1 else 0
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
    let bucket = 1 if key > 1 else 0
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
    let bucket = 1 if key > 1 else 0
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
    let bucket = 1 if key > 1 else 0
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
    let r = rhs
    inner join r on lhs.id == r.id
    let k = lhs.id * 0 + 9223372036854775807 + 1
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
        let r = rhs
        inner join r on lhs.id == r.id
        let k = lhs.id * 0 + 9223372036854775807 + 1
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
    # The key is admitted; only its representation, which can never fit signed
    # 64 bits on either target, blocks.
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
        ("(p: Int | None)", "p + 1", "bind_safe_literals"),
    ),
)
def test_joined_extrema_over_a_field_free_let_value_match_the_module_form(
    tmp_path, target, header, value, policy
):
    """A12: a LET value that reads no joined field (a constant or a parameter)
    keeps the module form's MIN/MAX result; it links no JOIN side, and MIN and
    MAX need no fan-out proof, exactly as for a direct field argument."""
    joined = (
        f"query result{header}:\n    from agg\n    let r = agg\n"
        "    inner join r on agg.key == r.key\n"
        f"    let level = {value}\n    group by:\n{{keys}}"
        "    select:\n        a = agg.rid\n        low = min({arg})\n"
        "        top = max({arg})\n"
    )
    module = (
        f"query result{header}:\n    from agg\n    let level = {value}\n"
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
    # With only the left key the right side repeats rows, which MIN and MAX,
    # depending only on the values they read, need no proof against: the
    # field-free value and the left side's own field both emit.
    left = "        agg.rid\n"
    for name, arg in (("free", "level"), ("field", "agg.value")):
        repeated = document(
            emit_source(
                tmp_path / name,
                target,
                joined.format(keys=left, arg=arg),
                policy=policy,
            )
        )
        assert repeated["status"] == "VERIFIED", repeated


@pytest.mark.parametrize("target", TARGETS)
def test_a_joined_computed_key_output_filters_and_orders_the_result(tmp_path, target):
    """`having` and grouped ORDER BY name the selected key's output."""
    outcome = emit_source(
        tmp_path,
        target,
        probe.AGGREGATE_COMPUTED_JOIN
        + "    having:\n        b\n    order by:\n        b desc\n",
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
    """A nonnegative signed64 count cannot be doubled without overflow room:
    MySQL refuses it, and PostgreSQL's checked bigint `+` bounds it (Q2)."""
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
    if target == "postgres":
        assert outcome.status == "VERIFIED", outcome.blockers
        data = public(outcome)
        assert column(data, "bumped")["representation"]["domain"] == {
            "kind": "int_range",
            "min": "0",
            "max": SIGNED64,
        }
        assert [
            r["evidence"] for r in data["requirements"] if r["kind"] == "arithmetic"
        ] == [[{"operator": "+"}, CHECKED[0]]]
        return
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
    having:
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
def test_sum_of_an_int_is_a_checked_bigint_narrowing(tmp_path, target, variant):
    """Q1: PostgreSQL sums exactly and narrows to bigint with a checked CAST,
    refusing an out-of-range sum with SQLSTATE 22003; MySQL's CAST(DECIMAL AS
    SIGNED) would clamp one, so MySQL keeps the range-proof blocker outside
    its S02 cell. The direct sum is in that cell: MySQL emits the guarded SUM
    with the same evidence and a nullable signed 64-bit carrier."""
    outcome = emit(tmp_path, target, "V_aggregate_blocked", variant)
    if target == "mysql" and variant == "sum_direct":
        assert outcome.status == "VERIFIED", outcome.blockers
        data = public(outcome)
        assert data["sql"].count("CASE WHEN SUM(`s0`.`value é`) > ") == 1
        (aggregate,) = [r for r in data["requirements"] if r["kind"] == "aggregate"]
        assert (aggregate["rule"], aggregate["evidence"]) == ("R13", CHECKED)
        assert column(data, "s")["representation"] == {
            "storage": {"kind": "my_signed_int"},
            "nullable": True,
            "domain": {
                "kind": "int_range",
                "min": "-9223372036854775808",
                "max": SIGNED64,
            },
        }
        return
    if target == "mysql":
        assert outcome.status == "BLOCKED"
        assert [(item.code, item.detail) for item in outcome.blockers] == [
            ("PIE-B1004", "sum_int_aggregate_range_proof_missing")
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    data = public(outcome)
    assert data["sql"].count(
        'CAST(SUM(CAST("s0"."value é" AS pg_catalog.int8)) AS pg_catalog.int8)'
    ) == 1 and "SUM(" not in data["sql"].replace("CAST(SUM(", "")
    (aggregate,) = [r for r in data["requirements"] if r["kind"] == "aggregate"]
    assert (aggregate["rule"], aggregate["evidence"]) == ("R13", CHECKED)
    # No other generated requirement claims the target check.
    assert all(
        "overflow" not in item
        for r in data["requirements"]
        if r["kind"] != "aggregate"
        for item in r["evidence"]
        if type(item) is dict
    )
    if variant == "sum_direct":
        assert column(data, "s")["representation"] == {
            "storage": {"kind": "pg_int8"},
            "nullable": True,
            "domain": {
                "kind": "int_range",
                "min": "-9223372036854775808",
                "max": SIGNED64,
            },
        }


@pytest.mark.parametrize("target", TARGETS)
def test_a_grouped_sum_of_a_narrow_int_is_spelled_exactly(tmp_path, target):
    """A grouped sum over an int4 field, read by a later filter, has the same
    two casts: PostgreSQL never accumulates it in an unchecked bigint."""
    checked, outcome = probe.temporal_case(
        tmp_path,
        target,
        "    from rows\n    group by:\n        u\n    select:\n        key = u\n"
        "        total = sum(id)\n    having:\n        total > 5\n",
    )
    assert checked.verified
    if target == "mysql":
        assert [(b.code, b.detail) for b in outcome.blockers] == [
            ("PIE-B1004", "sum_int_aggregate_range_proof_missing")
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    data = public(outcome)
    assert data["sql"] == (
        'WITH "p0" ("c0", "c1") AS (SELECT "s0"."u" AS "c0", '
        'CAST(SUM(CAST("s0"."id" AS pg_catalog.int8)) AS pg_catalog.int8) AS "c1" '
        'FROM "public"."phase66 safe int source" AS "s0" GROUP BY "s0"."u"), '
        '"p1" ("c0", "c1") AS (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1" '
        'FROM "p0" AS "t1" WHERE ("t1"."c1" > CAST(5 AS pg_catalog.int8))) '
        'SELECT "t2"."c0" AS "key", "t2"."c1" AS "total" FROM "p1" AS "t2"'
    )
    assert [
        (r["kind"], r["evidence"])
        for r in data["requirements"]
        if r["kind"] == "aggregate"
    ] == [("aggregate", CHECKED)]


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
    ("variant", "field", "evidence", "mysql_blocker"),
    (
        (
            "stddev_direct",
            "value é",
            [],
            ("PIE-B1003", "stddev_int_not_admitted_on_target"),
        ),
        (
            "stddev_float",
            "ratio value",
            [{"overflow": "target_checked_binary64_overflow"}],
            ("PIE-B1004", "float_aggregate_finite_result_proof_missing"),
        ),
    ),
)
def test_stddev_is_the_postgres_root_of_the_float8_sample_variance(
    tmp_path, target, variant, field, evidence, mysql_blocker
):
    """Lane F: PostgreSQL emits SQRT(CAST(VAR_SAMP(x) AS float8)) for an Int
    with no range evidence, and for a Float with the binary64 overflow token;
    MySQL keeps both refused, each with a suggestion."""
    outcome = emit(tmp_path, target, "V_aggregate_blocked", variant)
    if target == "mysql":
        data = public(outcome)
        assert data["status"] == "BLOCKED"
        (blocker,) = data["blockers"]
        assert (blocker["code"], blocker["subject"]["detail"]) == mysql_blocker
        assert blocker["suggestion"]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    data = public(outcome)
    assert column(data, "d")["logical_type"] == {
        "kind": "builtin",
        "name": "Float",
        "parameters": None,
    }
    assert column(data, "d")["representation"] == {
        "storage": {"kind": "pg_float8"},
        "nullable": True,
        "domain": {"kind": "finite_float", "format": "binary64"},
    }
    assert (
        f'SQRT(CAST(VAR_SAMP("s0"."{field}") AS pg_catalog.float8)) AS "c0"'
        in data["sql"]
    )
    assert "STDDEV" not in data["sql"] and "VAR_SAMP(CAST(" not in data["sql"]
    assert [
        r["evidence"] for r in data["requirements"] if r["kind"] == "aggregate"
    ] == [evidence]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("grouped", (True, False))
@pytest.mark.parametrize(
    ("field", "column_name", "evidence", "mysql_blocker"),
    (
        (
            "value",
            "value é",
            [],
            ("PIE-B1003", "{function}_int_not_admitted_on_target"),
        ),
        (
            "ratio",
            "ratio value",
            [{"overflow": "target_checked_binary64_overflow"}],
            ("PIE-B1004", "float_aggregate_finite_result_proof_missing"),
        ),
    ),
)
def test_variance_and_population_deviation_are_the_postgres_float8_variance(
    tmp_path, target, grouped, field, column_name, evidence, mysql_blocker
):
    """PostgreSQL emits `variance` and `pvariance` as VAR_SAMP and VAR_POP
    cast once to float8 and `pstdev` as the SQRT of the cast VAR_POP, for an
    Int with no range evidence and for a Float with the binary64 overflow
    token, as `stddev`; MySQL keeps each refused, with a suggestion."""
    keys = (
        "    group by key\n    select:\n        key\n" if grouped else "    select:\n"
    )
    outcome = emit_source(
        tmp_path,
        target,
        "query result:\n    from agg\n"
        + keys
        + f"        v = variance({field})\n        pv = pvariance({field})\n"
        + f"        ps = pstdev({field})\n",
    )
    data = public(outcome)
    functions = ("variance", "pvariance", "pstdev")
    if target == "mysql":
        assert data["status"] == "BLOCKED"
        code, detail = mysql_blocker
        assert [(b["code"], b["subject"]["detail"]) for b in data["blockers"]] == [
            (code, detail.format(function=function)) for function in functions
        ]
        assert all(b["suggestion"] for b in data["blockers"])
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    for label in ("v", "pv", "ps"):
        assert column(data, label)["logical_type"] == {
            "kind": "builtin",
            "name": "Float",
            "parameters": None,
        }
        assert column(data, label)["representation"] == {
            "storage": {"kind": "pg_float8"},
            "nullable": True,
            "domain": {"kind": "finite_float", "format": "binary64"},
        }
    read = f'"s0"."{column_name}"'
    first = 1 if grouped else 0
    for offset, sql in enumerate(
        (
            f"CAST(VAR_SAMP({read}) AS pg_catalog.float8)",
            f"CAST(VAR_POP({read}) AS pg_catalog.float8)",
            f"SQRT(CAST(VAR_POP({read}) AS pg_catalog.float8))",
        )
    ):
        assert f'{sql} AS "c{first + offset}"' in data["sql"]
    assert not any(
        token in data["sql"]
        for token in ("VARIANCE(", "STDDEV", "VAR_SAMP(CAST(", "VAR_POP(CAST(")
    )
    assert [
        r["evidence"] for r in data["requirements"] if r["kind"] == "aggregate"
    ] == [evidence] * 3


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("grouped", (True, False))
def test_median_and_quantile_are_the_postgres_percentile_of_an_int(
    tmp_path, target, policy, grouped
):
    """PostgreSQL emits PERCENTILE_CONT over the float8 image of an Int, the
    `quantile` fraction an anchored literal under either policy; MySQL, which
    has no interpolated percentile, refuses each with a suggestion."""
    keys = (
        "    group by key\n    select:\n        key\n" if grouped else "    select:\n"
    )
    outcome = emit_source(
        tmp_path,
        target,
        "query result:\n    from agg\n" + keys + "        m = median(value)\n"
        "        q = quantile(rid, 0.9)\n",
        policy=policy,
    )
    data = public(outcome)
    if target == "mysql":
        assert data["status"] == "BLOCKED"
        assert [
            (b["code"], b["subject"]["detail"], b["location"]["line"], b["suggestion"])
            for b in data["blockers"]
        ] == [
            (
                "PIE-B1003",
                "quantile_not_admitted_on_target",
                line,
                "Emit this median or quantile for PostgreSQL, or keep it in "
                "check/plan: MySQL has no interpolated percentile.",
            )
            for line in ((16, 17) if grouped else (14, 15))
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    for label in ("m", "q"):
        assert column(data, label)["logical_type"] == {
            "kind": "builtin",
            "name": "Float",
            "parameters": None,
        }
        assert column(data, label)["representation"] == {
            "storage": {"kind": "pg_float8"},
            "nullable": True,
            "domain": {"kind": "finite_float", "format": "binary64"},
        }
    assert (
        'PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY CAST("s0"."value é" AS '
        'pg_catalog.float8)) AS "c'
    ) in data["sql"]
    assert (
        "PERCENTILE_CONT(CAST('0.9' AS pg_catalog.float8)) WITHIN GROUP (ORDER BY "
        'CAST("s0"."row id" AS pg_catalog.float8)) AS "c'
    ) in data["sql"]
    assert [
        r["evidence"] for r in data["requirements"] if r["kind"] == "aggregate"
    ] == [[], []]


@pytest.mark.parametrize("grouped", [False, True])
def test_postgres_median_and_quantile_read_left_join_rows(tmp_path, grouped):
    """Over a LEFT JOIN's rows, as `sum` reads them: the quantile fraction is
    a literal beside the joined argument, not another read of it."""
    item = probe.fixture("postgres", "Z_aggregate_joined", "left_nullable")
    header = item["source"].split("query result:", 1)[0]
    keys = (
        "    group by:\n        keys.rid\n    select:\n        k = keys.rid\n"
        if grouped
        else "    select:\n"
    )
    _, outcome = probe.build_case(
        tmp_path,
        header
        + "query result:\n    from keys\n    let r = agg\n"
        + "    left join r on keys.rid == r.rid\n"
        + keys
        + "        m = median(r.rid)\n        q = quantile(r.rid, 0.75)\n",
        item["contract"],
        item["policy"],
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    order = 'WITHIN GROUP (ORDER BY CAST("t0"."c13" AS pg_catalog.float8))'
    sql = public(outcome)["sql"]
    assert f"PERCENTILE_CONT(0.5) {order}" in sql
    assert f"PERCENTILE_CONT(CAST('0.75' AS pg_catalog.float8)) {order}" in sql
    import _pietto_sql_emission_portable as portable

    artifact = outcome.artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds


@pytest.mark.parametrize(
    ("arguments", "row"),
    [
        ("keys.label, r.rid", '"t0"."c3", "t0"."c13"'),
        # A `let:` name of a field in any position reads that field.
        ("keys.value, lb", '"t1"."c1", "t1"."c14"'),
        ("lb, keys.value", '"t1"."c14", "t1"."c1"'),
    ],
)
@pytest.mark.parametrize("grouped", [False, True])
def test_postgres_count_distinct_tuple_reads_left_join_rows(
    tmp_path, grouped, arguments, row
):
    """`count_distinct(a, b)` over a LEFT JOIN's rows reads one field of each
    input, a NULL-extended field included, which the CASE skips."""
    item = probe.fixture("postgres", "Z_aggregate_joined", "left_nullable")
    header = item["source"].split("query result:", 1)[0]
    keys = (
        "    group by:\n        keys.rid\n    select:\n        k = keys.rid\n"
        if grouped
        else "    select:\n"
    )
    _, outcome = probe.build_case(
        tmp_path,
        header
        + "query result:\n    from keys\n    let r = agg\n"
        + "    left join r on keys.rid == r.rid\n"
        + ("    let lb = r.label\n" if "lb" in arguments else "")
        + keys
        + f"        d = count_distinct({arguments})\n",
        item["contract"],
        item["policy"],
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    first, second = row.split(", ")
    assert (
        f"COUNT(DISTINCT CASE WHEN {first} IS NOT NULL AND {second} IS NOT NULL "
        f"THEN ROW({row}) END)"
    ) in public(outcome)["sql"]
    import _pietto_sql_emission_portable as portable

    artifact = outcome.artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds


@pytest.mark.parametrize("target", TARGETS)
def test_a_float_median_needs_a_finite_result_proof(tmp_path, target):
    """PERCENTILE_CONT between two finite Floats more than the largest float8
    apart returns an infinity unchecked, so a project keeps a Float median or
    quantile refused, as a Float `sum` or `avg`."""
    outcome = emit_source(
        tmp_path,
        target,
        "query result:\n    from agg\n    select:\n        m = median(ratio)\n",
    )
    assert outcome.status == "BLOCKED"
    assert [(item.code, item.detail) for item in outcome.blockers] == [
        ("PIE-B1004", "float_aggregate_finite_result_proof_missing")
        if target == "postgres"
        else ("PIE-B1003", "quantile_not_admitted_on_target")
    ]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("variant", "calls", "representations", "evidence", "mysql_blockers"),
    (
        (
            "sum_float",
            ('SUM("s0"."ratio value") AS "c0"',),
            ("float",),
            [[{"overflow": "target_checked_binary64_overflow"}]],
            [("PIE-B1004", "float_aggregate_finite_result_proof_missing")],
        ),
        (
            "avg_float",
            ('AVG("s0"."ratio value") AS "c0"',),
            ("float",),
            [[{"overflow": "target_checked_binary64_overflow"}]],
            [("PIE-B1004", "float_aggregate_finite_result_proof_missing")],
        ),
        (
            "postgres_carriers",
            (
                'COUNT("s0"."text `""é") AS "c0"',
                'COUNT(DISTINCT "s0"."text `""é") AS "c1"',
                'COUNT(DISTINCT "s0"."flag value") AS "c2"',
                'MIN("s0"."amount value") AS "c3"',
                'MAX("s0"."ratio value") AS "c4"',
            ),
            ("count", "count", "count", "decimal", "float"),
            [[]] * 5,
            # MySQL emits these too, with its own carriers (below).
            None,
        ),
        (
            "inline_arguments",
            (
                'CAST(SUM(CAST(("s0"."value é" * CAST(2 AS pg_catalog.int8))'
                ' AS pg_catalog.int8)) AS pg_catalog.int8) AS "c0"',
                'COUNT(("s0"."value é" + CAST(1 AS pg_catalog.int8))) AS "c1"',
                'AVG(CAST(("s0"."value é" + CAST(1 AS pg_catalog.int8))'
                ' AS pg_catalog.float8)) AS "c2"',
            ),
            ("sum", "count", "float"),
            [CHECKED, [], []],
            [("PIE-B1002", "arithmetic_outside_physical_range")] * 3,
        ),
        (
            "count_distinct_tuple",
            (
                'COUNT(DISTINCT CASE WHEN "s0"."text `""é" IS NOT NULL AND '
                '"s0"."flag value" IS NOT NULL THEN ROW("s0"."text `""é", '
                '"s0"."flag value") END) AS "c0"',
                'COUNT(DISTINCT CASE WHEN "s0"."amount value" IS NOT NULL AND '
                '"s0"."ratio value" IS NOT NULL THEN ROW("s0"."amount value", '
                '"s0"."ratio value") END) AS "c1"',
                'COUNT(DISTINCT CASE WHEN "s0"."group key" IS NOT NULL AND '
                '"s0"."value é" IS NOT NULL THEN ROW("s0"."group key", '
                '"s0"."value é") END) AS "c2"',
                'COUNT(DISTINCT CASE WHEN "s0"."text `""é" IS NOT NULL AND '
                '"s0"."amount value" IS NOT NULL AND "s0"."row id" IS NOT NULL '
                'THEN ROW("s0"."text `""é", "s0"."amount value", "s0"."row id") '
                'END) AS "c3"',
            ),
            ("count",) * 4,
            [[]] * 4,
            [("PIE-B1003", "count_distinct_tuple_not_admitted_on_target")] * 4,
        ),
    ),
)
def test_postgres_aggregates_reach_single_file_argument_parity(
    tmp_path, target, variant, calls, representations, evidence, mysql_blockers
):
    """S16: PostgreSQL emits the single-file SQL shape of a Float sum or
    average (finite by the target's checked binary64 overflow), of a count,
    distinct count or extreme of a Text, Bool, Float or Decimal carrier (the
    group-key comparison law), and of an aggregate over a row expression,
    lowered as a LET would be. MySQL counts, deduplicates and compares the
    same carriers by the group-key law, with the carriers PostgreSQL uses (a
    non-null BIGINT count and the argument's own nullable carrier for an
    extreme; utf8mb4_0900_bin NO PAD distinguishes "a", "A" and "a "), and
    keeps the Float sum and average and this Int expression refused, with a
    suggestion."""
    outcome = emit(tmp_path, target, "V_aggregate_blocked", variant)
    data = public(outcome)
    if target == "mysql" and mysql_blockers is None:
        assert outcome.status == "VERIFIED", outcome.blockers
        assert (
            'SELECT COUNT(`s0`.`text ``"é`) AS `c0`,'
            ' COUNT(DISTINCT `s0`.`text ``"é`) AS `c1`,'
            " COUNT(DISTINCT `s0`.`flag value`) AS `c2`,"
            " MIN(`s0`.`amount value`) AS `c3`, MAX(`s0`.`ratio value`) AS `c4`"
        ) in data["sql"]
        count = {
            "storage": {"kind": "my_bigint"},
            "nullable": False,
            "domain": {"kind": "int_range", "min": "0", "max": SIGNED64},
        }
        assert [item["representation"] for item in data["columns"]] == [
            count,
            count,
            count,
            {
                "storage": {"kind": "my_decimal", "precision": 9, "scale": 2},
                "nullable": True,
                "domain": {"kind": "decimal", "precision": 9, "scale": 2},
            },
            {
                "storage": {"kind": "my_double"},
                "nullable": True,
                "domain": {"kind": "finite_float", "format": "binary64"},
            },
        ]
        assert [
            r["evidence"] for r in data["requirements"] if r["kind"] == "aggregate"
        ] == evidence
        return
    if target == "mysql":
        assert data["status"] == "BLOCKED"
        assert [
            (blocker["code"], blocker["subject"]["detail"])
            for blocker in data["blockers"]
        ] == mysql_blockers
        assert all(blocker["suggestion"] for blocker in data["blockers"])
        if variant == "count_distinct_tuple":
            # Only the project emitter lacks the spelling (a two-database
            # differential passed for the single file's).
            assert {blocker["suggestion"] for blocker in data["blockers"]} == {
                "Emit this count_distinct of several columns for PostgreSQL, or "
                "keep it in check/plan: a project's MySQL emission has no "
                "COUNT(DISTINCT a, b) yet (a single file emits it)."
            }
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    for call in calls:
        assert call in data["sql"]
    shapes = {
        "float": {
            "storage": {"kind": "pg_float8"},
            "nullable": True,
            "domain": {"kind": "finite_float", "format": "binary64"},
        },
        "count": {
            "storage": {"kind": "pg_int8"},
            "nullable": False,
            "domain": {"kind": "int_range", "min": "0", "max": SIGNED64},
        },
        "sum": {
            "storage": {"kind": "pg_int8"},
            "nullable": True,
            "domain": {
                "kind": "int_range",
                "min": str(-(1 << 63)),
                "max": SIGNED64,
            },
        },
        "decimal": {
            "storage": {"kind": "pg_numeric", "precision": 9, "scale": 2},
            "nullable": True,
            "domain": {"kind": "decimal", "precision": 9, "scale": 2},
        },
    }
    assert [item["representation"] for item in data["columns"]] == [
        shapes[name] for name in representations
    ]
    assert [
        r["evidence"] for r in data["requirements"] if r["kind"] == "aggregate"
    ] == evidence


@pytest.mark.parametrize("target", TARGETS)
def test_row_expression_and_float_arguments_count_and_compare_on_both_targets(
    tmp_path, target
):
    """A Text, Bool or Float row expression argument is lowered as a
    LET would be on both targets, and a Float counts and takes its extreme
    (-0.0 and 0.0 tie: the extreme is some member). Only MySQL refuses a
    distinct count of a Float, which it deduplicated apart beside a wide key."""
    outcome = emit_source(
        tmp_path / "open",
        target,
        """query result:
    from agg
    select:
        n = count(ratio)
        lo = min(ratio)
        l = count(lower(label))
        d = count_distinct(trim(lower(label)))
        b = count(flag and flag)
        m = max(amount)
""",
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    data = public(outcome)
    if target == "postgres":
        calls = (
            'COUNT("s0"."ratio value") AS "c0", MIN("s0"."ratio value") AS "c1",'
            ' COUNT(lower("s0"."text `""é")) AS "c2",'
            ' COUNT(DISTINCT trim(lower("s0"."text `""é"))) AS "c3",'
            ' COUNT(("s0"."flag value" AND "s0"."flag value")) AS "c4",'
            ' MAX("s0"."amount value") AS "c5"'
        )
    else:
        calls = (
            "COUNT(`s0`.`ratio value`) AS `c0`, MIN(`s0`.`ratio value`) AS `c1`,"
            ' COUNT(LOWER(`s0`.`text ``"é`)) AS `c2`,'
            ' COUNT(DISTINCT TRIM(LOWER(`s0`.`text ``"é`))) AS `c3`,'
            " COUNT((`s0`.`flag value` AND `s0`.`flag value`)) AS `c4`,"
            " MAX(`s0`.`amount value`) AS `c5`"
        )
    assert calls in data["sql"]
    assert [item["logical_type"]["name"] for item in data["columns"]] == [
        "Int",
        "Float",
        "Int",
        "Int",
        "Int",
        "Decimal",
    ]
    refused = emit_source(
        tmp_path / "distinct",
        target,
        "query result:\n    from agg\n    select:\n        d = count_distinct(ratio)\n",
    )
    if target == "postgres":
        assert refused.status == "VERIFIED", refused.blockers
        return
    (blocker,) = public(refused)["blockers"]
    assert (blocker["code"], blocker["subject"]["detail"]) == (
        "PIE-B1003",
        "count_distinct_argument_outside_reviewed_int_domain",
    )
    assert blocker["suggestion"]


@pytest.mark.parametrize(
    ("target", "expression", "detail"),
    (
        ("postgres", "avg(amount)", "decimal_aggregate_range_proof_missing"),
        ("mysql", "sum(amount)", "decimal_aggregate_range_proof_missing"),
        ("mysql", "avg(amount)", "decimal_aggregate_range_proof_missing"),
        ("mysql", "sum(ratio)", "float_aggregate_finite_result_proof_missing"),
        ("mysql", "avg(ratio)", "float_aggregate_finite_result_proof_missing"),
    ),
)
def test_numeric_aggregate_domains_require_proofs_beyond_source_declarations(
    tmp_path, target, expression, detail
):
    """A Decimal AVG has no fixed scale; MySQL also keeps Decimal SUM and
    Float SUM/AVG refused without their result proofs."""
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
def test_joined_grouped_aggregates_keep_the_same_parity(tmp_path, target):
    """S16: over a LEFT JOIN's unique right rows, PostgreSQL counts a Text
    field, deduplicates a Bool, takes Decimal and Float extremes, sums and
    averages a Float and sums a row expression; MySQL emits the counts and
    extremes and refuses the Float sum and average and the Int expression at
    their own items."""
    item = probe.fixture(target, "Z_aggregate_joined", "left_nullable")
    header = item["source"].split("query result:", 1)[0]
    _, outcome = probe.build_case(
        tmp_path,
        header
        + """query result:
    from keys
    let r = agg
    left join r on keys.rid == r.rid
    group by:
        keys.rid
    select:
        k = keys.rid
        n = count(r.label)
        d = count_distinct(r.flag)
        lo = min(r.amount)
        hi = max(r.ratio)
        s = sum(r.ratio)
        a = avg(r.ratio)
        w = sum(r.value * 2)
""",
        item["contract"],
        item["policy"],
    )
    data = public(outcome)
    if target == "mysql":
        assert [(b["code"], b["subject"]["detail"]) for b in data["blockers"]] == [
            ("PIE-B1004", "float_aggregate_finite_result_proof_missing"),
            ("PIE-B1004", "float_aggregate_finite_result_proof_missing"),
            ("PIE-B1002", "arithmetic_outside_physical_range"),
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    assert (
        'COUNT("t0"."c10") AS "c1", COUNT(DISTINCT "t0"."c9") AS "c2",'
        ' MIN("t0"."c11") AS "c3", MAX("t0"."c12") AS "c4",'
        ' SUM("t0"."c12") AS "c5", AVG("t0"."c12") AS "c6",'
        ' CAST(SUM(CAST(("t0"."c8" * CAST(2 AS pg_catalog.int8))'
        ' AS pg_catalog.int8)) AS pg_catalog.int8) AS "c7"'
    ) in data["sql"]
    assert [
        column(data, label)["logical_type"]["name"]
        for label in ("lo", "hi", "s", "a", "w")
    ] == ["Decimal", "Float", "Float", "Float", "Int"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_float_determinant_groups_by_float_equality_on_postgres(tmp_path, target):
    """F2/F4: a PostgreSQL Float key groups -0.0 with 0.0 by the target's own
    GROUP BY; MySQL does so only in the Phase77 S07 cells, such as this one
    Float key with its count, and keeps one group-key blocker at the GROUP BY
    item beside another aggregate."""
    outcome = emit(tmp_path, target, "V_aggregate_blocked", "float_key")
    if target == "mysql":
        assert outcome.status == "VERIFIED", outcome.blockers
        assert " GROUP BY `s0`.`ratio value`" in public(outcome)["sql"]
        outcome = emit_source(
            tmp_path / "beside",
            target,
            "query result:\n    from agg\n    group by:\n        ratio\n"
            "    select:\n        r = ratio\n        total = count()\n"
            "        top = max(rid)\n",
        )
        assert outcome.status == "BLOCKED"
        (blocker,) = public(outcome)["blockers"]
        # At the GROUP BY item `ratio`, line 14.
        assert (blocker["code"], blocker["subject"], blocker["location"]) == (
            "PIE-B1003",
            {
                "reference": {"kind": "group_key", "position": 0},
                "detail": "group_key_type_outside_reviewed_comparison_domain",
            },
            {
                "path": "main.pietto",
                "line": 14,
                "column": 9,
                "end_line": 14,
                "end_column": 14,
            },
        )
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    data = public(outcome)
    assert ' GROUP BY "s0"."ratio value"' in data["sql"]
    assert column(data, "r")["logical_type"]["name"] == "Float"


def test_the_verifier_refuses_a_mysql_float_group_key_artifact(tmp_path, monkeypatch):
    """A MySQL artifact built while the group-key law admitted every Float is
    refused by verify_project_sql_emission once the law is the real one (here
    a Float key beside another aggregate, outside every Phase77 S07 cell)."""
    strict = grouping.group_key_problem
    with monkeypatch.context() as patched:
        patched.setattr(
            grouping,
            "group_key_problem",
            lambda realization, **_: (
                None if realization.tag == "Float" else strict(realization)
            ),
        )
        outcome = emit_source(
            tmp_path,
            "mysql",
            "query result:\n    from agg\n    group by:\n        ratio\n"
            "    select:\n        r = ratio\n        total = count()\n"
            "        top = max(rid)\n",
        )
    artifact = outcome.artifact
    assert outcome.status == "VERIFIED" and artifact is not None, outcome.blockers
    checked = verify_project_sql_emission(artifact, artifact.request)
    assert not checked.verified and "plan_ast_correspondence" in checked.issues


@pytest.mark.parametrize("target", TARGETS)
def test_a_float_having_filter_compares_a_target_average(tmp_path, target):
    """R5: avg(Int) is the target's own Float; a literal comparison filters it."""
    outcome = emit_source(
        tmp_path,
        target,
        "query result:\n    from agg\n    group by:\n        key\n    select:\n"
        "        key\n        a = avg(value)\n    having:\n        a < 15.0\n",
    )
    data = public(outcome)
    assert data["status"] == "VERIFIED", data["blockers"]
    carrier = (
        "CAST('15.0' AS pg_catalog.float8)"
        if target == "postgres"
        else "CAST(15.0e0 AS DOUBLE)"
    )
    assert f" < {carrier})" in data["sql"]


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
def test_an_aggregate_argument_is_a_field_or_a_lowered_row_expression(tmp_path, target):
    """Both targets count a Text field or its lowered value (MySQL
    too)."""
    outcome = emit_source(
        tmp_path,
        target,
        """query result:
    from agg
    select:
        total = count_distinct(label)
        lowered = count(lower(label))
""",
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    assert (
        'COUNT(DISTINCT "s0"."text `""é") AS "c0", COUNT(lower("s0"."text `""é"))'
        if target == "postgres"
        else 'COUNT(DISTINCT `s0`.`text ``"é`) AS `c0`, COUNT(LOWER(`s0`.`text ``"é`))'
    ) in public(outcome)["sql"]


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


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_min_and_max_of_a_temporal_carrier_keep_it(tmp_path, target):
    """MIN/MAX keep one exact Timestamp or Date carrier, NULL for an empty
    group: PostgreSQL timestamp(6) and date, MySQL DATETIME(6) and DATE."""
    checked, outcome = probe.temporal_case(
        tmp_path,
        target,
        "    from rows\n    group by id\n    select:\n        key = id\n"
        "        first = min(ts)\n        last = max(d2)\n",
    )
    assert checked.verified
    assert outcome.status == "VERIFIED", outcome.blockers
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    q = '"' if target == "postgres" else "`"
    assert (
        f"MIN({q}s0{q}.{q}ts{q}) AS {q}c1{q}, MAX({q}s0{q}.{q}d2{q}) AS {q}c2{q}"
        in public["sql"]
    )
    pg = target == "postgres"
    assert [c["representation"] for c in public["columns"][1:]] == [
        {
            "storage": {
                "kind": "pg_timestamp" if pg else "my_datetime",
                "fractional_seconds": 6,
            },
            "nullable": True,
            "domain": {"kind": "timestamp"},
        },
        {
            "storage": {"kind": "pg_date" if pg else "my_date"},
            "nullable": True,
            "domain": {"kind": "date"},
        },
    ]


# Phase77 S05: MySQL emits a Float statistic only in the one cell whose
# primitive the raw qualification ran: one nullable DOUBLE field of one source,
# the only item of a global aggregate with no other clause.
MYSQL_STATISTICS = {
    "stddev": "STDDEV_SAMP",
    "variance": "VAR_SAMP",
    "pvariance": "VAR_POP",
    "pstdev": "STDDEV_POP",
}
STATISTIC_SELECT = "query result:\n    from agg\n    select:\n"
FLOAT_PROOF = ("PIE-B1004", "float_aggregate_finite_result_proof_missing")
# Each shape beside or around that cell, with its refusal as measured on
# main `e0116e41`.
STATISTIC_SHAPES = {
    "grouped": (
        "query result:\n    from agg\n    group by key\n    select:\n"
        "        key\n        d = stddev(ratio)\n",
        [FLOAT_PROOF],
    ),
    "where": (
        "query result:\n    from agg\n    where rid > 1\n    select:\n"
        "        d = pstdev(ratio)\n",
        [FLOAT_PROOF],
    ),
    "two_statistics": (
        STATISTIC_SELECT + "        d = stddev(ratio)\n        v = variance(ratio)\n",
        [FLOAT_PROOF, FLOAT_PROOF],
    ),
    "beside_count": (
        STATISTIC_SELECT + "        d = variance(ratio)\n        n = count()\n",
        [FLOAT_PROOF],
    ),
    "beside_min": (
        STATISTIC_SELECT + "        n = min(ratio)\n        d = pvariance(ratio)\n",
        [FLOAT_PROOF],
    ),
    "let_alias": (
        "query result:\n    let x = agg\n    from x\n    select:\n"
        "        d = stddev(ratio)\n",
        [FLOAT_PROOF],
    ),
    "let_chain": (
        "query result:\n    let x = agg\n    let y = x\n    from y\n    select:\n"
        "        d = stddev(ratio)\n",
        [FLOAT_PROOF],
    ),
    "let_unused_relation": (
        "query result:\n    from agg\n    let r = agg\n    select:\n"
        "        d = stddev(ratio)\n",
        [FLOAT_PROOF],
    ),
    "let_unused_relation_first": (
        "query result:\n    let r = agg\n    from agg\n    select:\n"
        "        d = stddev(ratio)\n",
        [FLOAT_PROOF],
    ),
    "unused_named_window": (
        "query result:\n    from agg\n    let w = window(order by rid)\n"
        "    select:\n        d = stddev(ratio)\n",
        [FLOAT_PROOF],
    ),
    "upstream_table": (
        "table base:\n    from agg\n    select:\n        ratio\n"
        "query result:\n    from base\n    select:\n        d = stddev(ratio)\n",
        [FLOAT_PROOF],
    ),
    "read_downstream": (
        "query spread:\n    from agg\n    select:\n        d = stddev(ratio)\n"
        "query result:\n    from spread\n    select:\n        d\n",
        [FLOAT_PROOF],
    ),
    "self_join": (
        "query result:\n    from agg\n    let r = agg\n"
        "    inner join r on agg.rid == r.rid\n    select:\n"
        "        d = stddev(r.ratio)\n",
        [FLOAT_PROOF],
    ),
    "limit": (
        STATISTIC_SELECT + "        d = stddev(ratio)\n    limit 1\n",
        [FLOAT_PROOF],
    ),
    "header_parameter": (
        "query result(low: Int):\n    from agg\n    select:\n        d = stddev(ratio)\n",
        [FLOAT_PROOF],
    ),
    "union_all": (
        "query a:\n    from agg\n    select:\n        d = stddev(ratio)\n"
        "query b:\n    from agg\n    select:\n        d = variance(ratio)\n"
        "query result:\n    union all:\n        from a\n        from b\n",
        [FLOAT_PROOF],
    ),
    "inside_coalesce": (
        STATISTIC_SELECT + "        d = coalesce(stddev(ratio), 0.0)\n",
        [("PIE-B1003", "aggregate_composition_not_admitted_on_target")],
    ),
    "float_sum": (STATISTIC_SELECT + "        s = sum(ratio)\n", [FLOAT_PROOF]),
    "float_avg": (STATISTIC_SELECT + "        a = avg(ratio)\n", [FLOAT_PROOF]),
    # Rule two (D77.37): the cell refused for another reason, an output label
    # past 256 characters, reports main's whole list (main `a015afcf`).
    "long_label": (
        STATISTIC_SELECT + "        " + "d" * 257 + " = stddev(ratio)\n",
        [FLOAT_PROOF, ("PIE-B1002", "output_label_unrepresentable")],
    ),
}


def emit_nullable(tmp_path, target, body, policy="preserve_literals"):
    item = probe.nullable_ratio_fixture(target, body, policy)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    return outcome


@pytest.mark.parametrize(
    ("declaration", "policy"),
    (("query", "preserve_literals"), ("table", "bind_safe_literals")),
)
@pytest.mark.parametrize("function", sorted(MYSQL_STATISTICS))
def test_mysql_emits_a_float_statistic_of_one_nullable_field_alone(
    tmp_path, function, declaration, policy
):
    """The qualified primitive, uncast and outside SQRT, with a nullable
    DOUBLE result and the binary64 overflow evidence (MySQL raises 22003 on
    an overflow); the live, pure and public readers each accept it."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    outcome = emit_nullable(
        tmp_path,
        "mysql",
        f"{declaration} result:\n    from agg\n    select:\n"
        f"        d = {function}(ratio)\n",
        policy,
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    data = public(outcome)
    assert data["sql"] == (
        f"WITH `p0` (`c0`) AS (SELECT {MYSQL_STATISTICS[function]}(`s0`.`ratio value`)"
        " AS `c0` FROM `phase66`.`phase66 agg é` AS `s0`)"
        " SELECT `t1`.`c0` AS `d` FROM `p0` AS `t1`"
    )
    assert column(data, "d")["logical_type"] == {
        "kind": "builtin",
        "name": "Float",
        "parameters": None,
    }
    assert column(data, "d")["representation"] == {
        "storage": {"kind": "my_double"},
        "nullable": True,
        "domain": {"kind": "finite_float", "format": "binary64"},
    }
    assert [
        r["evidence"] for r in data["requirements"] if r["kind"] == "aggregate"
    ] == [[{"overflow": "target_checked_binary64_overflow"}]]
    artifact = outcome.artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert pure.parse_emission_observation(observed.canonical_bytes).status is (
        pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds


@pytest.mark.parametrize("shape", ("not_null_field", *STATISTIC_SHAPES))
def test_mysql_keeps_every_other_float_statistic_shape_refused(tmp_path, shape):
    """A non-nullable field, and the cell beside, inside or around any other
    form, keep main's code and detail, and the cell refused for another
    reason main's whole list; a Float `sum` and `avg` stay refused."""
    if shape == "not_null_field":
        outcome = emit_source(
            tmp_path, "mysql", STATISTIC_SELECT + "        d = stddev(ratio)\n"
        )
        expected = [FLOAT_PROOF]
    else:
        body, expected = STATISTIC_SHAPES[shape]
        outcome = emit_nullable(tmp_path, "mysql", body)
    assert outcome.status == "BLOCKED"
    assert [(b.code, b.detail) for b in outcome.blockers] == expected
    assert [
        (b["code"], b["subject"]["detail"]) for b in public(outcome)["blockers"]
    ] == expected


def test_other_declarations_leave_the_mysql_float_statistic_statement_alone(
    tmp_path,
):
    """The cell is one emitted statement: another declaration with a header
    parameter, and others that read the cell through `from` or a JOIN, leave
    its SQL byte for byte, and its compiled replay too."""
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    cell = STATISTIC_SELECT + "        d = stddev(ratio)\n"
    alone = emit_nullable(tmp_path / "alone", "mysql", cell)
    beside = emit_nullable(
        tmp_path / "beside",
        "mysql",
        cell + "query other(low: Int):\n    from agg\n    where rid > low\n"
        "    select:\n        rid\n"
        "query reader:\n    from result\n    select:\n        d\n"
        "query joined:\n    from agg\n    let s = result\n    cross join s\n"
        "    select:\n        rid\n        d = s.d\n",
    )
    assert (alone.status, beside.status) == ("VERIFIED", "VERIFIED"), beside.blockers
    assert public(beside)["sql"] == public(alone)["sql"]
    assert beside.artifact is not None
    built = build_compiled(beside.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).rendered.sql.decode() == public(alone)["sql"]


# Each forged shape, with the pure reader's and the public decoder's details.
# An observation document does not record an unread header parameter, so the
# pure reader accepts that one forgery; every other reader refuses it, the
# public decoder from the v2 document that a header parameter makes.
FORGED_STATISTICS = {
    "grouped": ("mysql statistic cell", "aggregate argument carrier"),
    "where": ("mysql statistic cell", "aggregate argument carrier"),
    "two_statistics": ("mysql statistic cell", "aggregate argument carrier"),
    "beside_count": ("mysql statistic cell", "aggregate argument carrier"),
    "upstream_table": ("mysql statistic cell", "aggregate argument carrier"),
    "header_parameter": (None, "mysql statistic header parameter"),
    "not_null_field": ("variance or deviation result", "stddev casts"),
}


@pytest.mark.parametrize("shape", sorted(FORGED_STATISTICS))
def test_a_forged_mysql_float_statistic_outside_its_cell_fails_every_reader(
    tmp_path, monkeypatch, shape
):
    """With the plan's cell check bypassed in the producer, its live verifier
    and serializer (for a non-nullable field the argument law too), the live
    verifier refuses from the plan, also by its own aggregate body check, the
    public decoder from the published document and the compiled readers from
    the records; the pure reader refuses from the observation document,
    except an unread header parameter, which that document does not record."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_verification as verification
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_compiled_schema import CompiledError

    pure_detail, public_detail = FORGED_STATISTICS[shape]
    with monkeypatch.context() as patch:
        patch.setattr(grouping, "mysql_spread_cell", lambda *args: True)
        if shape == "not_null_field":
            law = grouping.resolved_argument_problem
            patch.setattr(
                grouping,
                "resolved_argument_problem",
                lambda function, *args, **kwargs: (
                    None
                    if function in grouping.SPREAD_FUNCTIONS
                    else law(function, *args, **kwargs)
                ),
            )
            forged = emit_source(
                tmp_path, "mysql", STATISTIC_SELECT + "        d = stddev(ratio)\n"
            )
        else:
            forged = emit_nullable(tmp_path, "mysql", STATISTIC_SHAPES[shape][0])
        assert forged.status == "VERIFIED"
        published = serialize_project_sql_emission(forged)
        artifact = forged.artifact
        assert artifact is not None
        built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    with pytest.raises(CompiledError, match="^COMPILED_AGGREGATE_ARGUMENT$"):
        emit_compiled(loaded, ())
    verdict = verify_project_sql_emission(artifact, artifact.request)
    assert not verdict.verified and "plan_ast_correspondence" in verdict.issues
    with monkeypatch.context() as patch:
        # Its own aggregate body check refuses without its re-derived blockers.
        patch.setattr(verification, "_structural_blockers", lambda *args: ())
        assert not verify_project_sql_emission(artifact, artifact.request).verified
    assert json.loads(serialize_project_sql_emission(forged))["status"] == "BLOCKED"
    result = pure.parse_emission_observation(
        portable._Export(artifact, artifact.request).run()
    )
    assert (result.status, result.detail) == (
        (pure.Status.OK, None)
        if pure_detail is None
        else (pure.Status.INVALID_RELATION, pure_detail)
    )
    assert json.loads(published)["status"] == "VERIFIED"
    with pytest.raises(ValueError, match=f"^{public_detail}$"):
        probe.decode_public(published)


def _set_spelling(document):
    _statistic_column(document)["spelling"] = "STDDEV_POP"


def _set_result_cast(document):
    _statistic_column(document)["result_cast"] = "DOUBLE"


def _drop_evidence(document):
    (requirement,) = (
        row["fields"]
        for row in document["records"]
        if row["ref"][0] == "generated_requirement"
        and row["fields"]["kind"] == "aggregate"
    )
    requirement["evidence"] = []


def _set_grouped(document):
    (stage,) = (
        row["fields"]
        for row in document["records"]
        if row["ref"][0] == "aggregate_stage"
    )
    stage["mode"] = "grouped"


def _statistic_column(document):
    (column,) = (
        row["fields"]
        for row in document["records"]
        if row["ref"][0] == "aggregate_value_column"
    )
    return column


@pytest.mark.parametrize(
    "edit", (_set_spelling, _set_result_cast, _drop_evidence, _set_grouped)
)
def test_a_tampered_mysql_float_statistic_observation_is_refused(tmp_path, edit):
    """The pure reader refuses a MySQL `stddev` observation whose spelling,
    result cast, overflow evidence or aggregation mode was changed."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    outcome = emit_nullable(
        tmp_path, "mysql", STATISTIC_SELECT + "        d = stddev(ratio)\n"
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    document = json.loads(observed.canonical_bytes)
    edit(document)
    data = (
        json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n"
    ).encode()
    assert pure.parse_emission_observation(data).status is not pure.Status.OK


# --------------------------------------------------------------------------
# Phase77 S02: MySQL sum(Int) in its cells
# --------------------------------------------------------------------------

# The public nullability of each cell body's columns.
S02_NULLABLE = {
    "s02_scalar": [True],
    "s02_where": [True],
    "s02_grouped": [False, True],
    "s02_unselected_key": [True],
    "s02_two_sums": [False, True, True],
    "s02_beside_count": [False, True, False, True],
    "s02_bigint_key": [False, True],
    "s02_key_alias": [False, True],
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("cell", sorted(S02_NULLABLE))
def test_mysql_sum_int_cells_emit_the_guarded_sum(tmp_path, cell, target):
    """S02: a MySQL project emits a direct `sum` of a nullable BIGINT source
    field, the whole value of a SELECT item of a query that reads its source
    through a WHERE at most and groups by at most one non-null Int source
    field, as the guarded SUM the native qualification ran: an exact DECIMAL
    sum, CAST to SIGNED in range and a BIGINT overflow (1690, SQLSTATE 22003)
    outside it, never a clamped value. The result is a nullable Int, NULL for
    no or only NULL values. Both families emit the pinned SQL, PostgreSQL's
    unchanged, and every reader accepts it."""
    checked, outcome = probe.numeric_world(tmp_path, target, probe.NUMERIC_CELLS[cell])
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert (
        outcome.artifact.rendered.sql.decode() == probe.NUMERIC_CELL_SQL[cell, target]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert [column["nullable"] for column in document["columns"]] == (
        S02_NULLABLE[cell]
    )


# A MIN or MAX of an INT field straight from the source or over a stage (a
# WHERE, a let, an upstream query), each with the MySQL SQL of its aggregate:
# MySQL returns such an extreme over a merged stage or a view as BIGINT (G1's
# WHERE, group by, sum and min form failed PIE-R3005 on every MySQL route,
# 2026-11-17) and emission cannot tell a view from a table, so every one is
# cast to SIGNED and declared my_signed_int (PL.67, PL.73). Each entry is the
# body, the MySQL SQL it holds and SQL it must not hold. An extreme of an
# upstream query's extreme reads that query's cast my_signed_int, a BIGINT,
# so only the inner one is cast; the outer keeps that carrier uncast.
MYSQL_INT_EXTREMA = {
    "source_min": (
        "query result:\n    from rows\n    group by k\n    select:\n"
        "        lo = min(c)\n",
        ("CAST(MIN(`s0`.`narrow`) AS SIGNED) AS `c1`",),
        (),
    ),
    "source_max": (
        "query result:\n    from rows\n    group by k\n    select:\n"
        "        lo = max(c)\n",
        ("CAST(MAX(`s0`.`narrow`) AS SIGNED) AS `c1`",),
        (),
    ),
    "s02_where_min": (
        "query result:\n    from rows\n    where id > 3\n    group by k\n"
        "    select:\n        x = sum(a)\n        lo = min(c)\n",
        ("CAST(MIN(`t1`.`c5`) AS SIGNED)",),
        (),
    ),
    "where_scalar_max_key": (
        "query result:\n    from rows\n    where id > 3\n    select:\n"
        "        lo = max(k)\n",
        ("CAST(MAX(`t1`.`c3`) AS SIGNED)",),
        (),
    ),
    "let_min": (
        "query result:\n    from rows\n    let t = c\n    group by k\n"
        "    select:\n        k\n        lo = min(t)\n",
        ("CAST(MIN(`t1`.`c6`) AS SIGNED)",),
        (),
    ),
    "upstream_min": (
        "query base:\n    from rows\n    group by k\n    select:\n        k\n"
        "        lo = min(c)\n"
        "query result:\n    from base\n    select:\n        m = min(lo)\n",
        ("CAST(MIN(`s0`.`narrow`) AS SIGNED)", "MIN(`s1`.`c1`)"),
        ("CAST(MIN(`s1`.`c1`)",),
    ),
}


@pytest.mark.parametrize("shape", sorted(MYSQL_INT_EXTREMA))
def test_a_mysql_int_extreme_is_cast_to_signed(tmp_path, shape):
    """MySQL keeps a MIN or MAX of an INT base-table column INT, but returns
    one over a view's or a merged stage's column as BIGINT. Every one is
    therefore cast to SIGNED, a BIGINT whatever its source, and declared
    my_signed_int with the field's own range; every reader accepts it. An
    extreme of such an extreme already reads a my_signed_int and keeps it
    uncast. PostgreSQL's SQL and int4 carrier are unchanged."""
    body, present, absent = MYSQL_INT_EXTREMA[shape]
    _, mysql = probe.numeric_world(tmp_path / "mysql", "mysql", body)
    probe.numeric_readers_accept(mysql)
    assert mysql.artifact is not None
    sql = mysql.artifact.rendered.sql.decode()
    assert all(part in sql for part in present)
    assert not any(part in sql for part in absent)
    column = json.loads(serialize_project_sql_emission(mysql))["columns"][-1]
    assert column["representation"]["storage"] == {"kind": "my_signed_int"}
    assert column["representation"]["domain"] == {
        "kind": "int_range",
        "min": "-2147483648",
        "max": "2147483647",
    }
    _, postgres = probe.numeric_world(tmp_path / "postgres", "postgres", body)
    probe.numeric_readers_accept(postgres)
    assert postgres.artifact is not None
    assert "CAST(M" not in postgres.artifact.rendered.sql.decode()
    column = json.loads(serialize_project_sql_emission(postgres))["columns"][-1]
    assert column["representation"]["storage"] == {"kind": "pg_int4"}


# The my_smallint branch of MYSQL_WIDENED_EXTREMA over the R08 world's
# nullable SMALLINT `s` (numeric_world declares no SMALLINT): through a
# WHERE or straight from the source the MIN is cast alike.
SMALLINT_EXTREMA = {
    "where": (
        "    where id > 3\n",
        "CAST(MIN(`t1`.`c3`) AS SIGNED) AS `c1`",
        "my_signed_int",
    ),
    "source": ("", "CAST(MIN(`s0`.`s`) AS SIGNED) AS `c1`", "my_signed_int"),
}


@pytest.mark.parametrize("shape", sorted(SMALLINT_EXTREMA))
def test_a_mysql_smallint_extreme_is_cast_to_signed(tmp_path, shape):
    """A MySQL MIN of a SMALLINT, read through a WHERE or straight from the
    source, is cast to SIGNED and declared my_signed_int with the field's
    own range. Every reader accepts both."""
    where, extreme, storage = SMALLINT_EXTREMA[shape]
    body = (
        f"query result:\n    from nums\n{where}    group by j\n    select:\n"
        "        lo = min(s)\n"
    )
    _, outcome = probe.division_world(tmp_path, "mysql", body)
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert extreme in outcome.artifact.rendered.sql.decode()
    column = json.loads(serialize_project_sql_emission(outcome))["columns"][-1]
    assert column["representation"]["storage"] == {"kind": storage}
    assert column["representation"]["domain"] == {
        "kind": "int_range",
        "min": "-32768",
        "max": "32767",
    }


@pytest.mark.parametrize(
    "spelling", [name for name in probe.NUMERIC_SPELLINGS if name.startswith("s02")]
)
def test_mysql_sum_int_spellings_emit_the_direct_sql(tmp_path, spelling):
    """A `group by:` block, a `table` declaration, parentheses, an identity
    `def` around the argument and a read qualified by the source's own name
    change nothing."""
    _, outcome = probe.numeric_world(
        tmp_path / "spelled", "mysql", probe.NUMERIC_SPELLINGS[spelling]
    )
    _, direct = probe.numeric_world(
        tmp_path / "direct", "mysql", probe.NUMERIC_CELLS["s02_grouped"]
    )
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert direct.artifact is not None
    assert outcome.artifact.rendered.sql == direct.artifact.rendered.sql


def _numeric_blockers(outcome):
    return [
        (
            blocker["code"],
            blocker["subject"]["detail"],
            *(
                (None, None)
                if blocker["location"] is None
                else (blocker["location"]["line"], blocker["location"]["column"])
            ),
        )
        for blocker in json.loads(serialize_project_sql_emission(outcome))["blockers"]
    ]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize(
    "shape", [name for name in probe.NUMERIC_REFUSALS if name.startswith("sum_")]
)
def test_mysql_sum_int_outside_its_cells_keeps_its_refusal(tmp_path, shape, policy):
    """Every other MySQL `sum(Int)` keeps the refusal main reports, object for
    object: a computed argument, a chain of relation aliases (MC G4 takes
    the others, windows nothing reads, imported sources and upstreams), a
    composed or conditional sum, a HAVING line on two outputs, or a LIMIT
    after an ORDER BY of keys only (MC G3 takes the others; MC G5 takes a
    header parameter, read or not); a cell sum beside
    another refused sum keeps its own refusal too (owner
    2026-11-13T00:20Z). PostgreSQL emits each as before."""
    body = probe.NUMERIC_REFUSALS[shape]
    _, outcome = probe.numeric_world(tmp_path / "mysql", "mysql", body, policy)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == probe.NUMERIC_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.numeric_world(tmp_path / "postgres", "postgres", body, policy)
    assert postgres.status == "VERIFIED", postgres.blockers


def test_a_forged_guarded_mysql_sum_column_is_refused(tmp_path):
    """The guarded SUM renders no DISTINCT and no cast, so the renderer and
    the byte verifier each refuse an S02 column that carries one instead of
    dropping it (no emitted cell holds one)."""
    from pietto._project.project_sql_emission_rendering import render_row_sql
    from pietto._project.project_sql_emission_verification import verify_row_bytes

    _, outcome = probe.numeric_world(
        tmp_path, "mysql", probe.NUMERIC_CELLS["s02_grouped"]
    )
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLRowQuery
    (column,) = (
        column
        for body in query.bodies
        for column in body.columns
        if type(column) is grouping.AggregateValueColumn
    )
    for name, value in (
        ("distinct", True),
        ("argument_cast", "SIGNED"),
        ("result_cast", "SIGNED"),
    ):
        original = getattr(column, name)
        object.__setattr__(column, name, value)
        try:
            with pytest.raises(ValueError, match="^unrenderable MySQL sum$"):
                render_row_sql(query)
            assert not verify_row_bytes(query, artifact.rendered)
        finally:
            object.__setattr__(column, name, original)
    assert verify_row_bytes(query, artifact.rendered)


def test_mysql_sum_cells_are_derived_once_per_aggregation(tmp_path, monkeypatch):
    """Emission and its verification each ask whether an aggregation can hold
    an S02 cell once, however many sums it holds (P76-PERF-2)."""
    from pietto._project import project_sql_emission_rows as rows

    counts = []
    for count in (1, 40):
        calls = []
        original = rows.mysql_sum_query
        with monkeypatch.context() as patch:
            patch.setattr(
                rows,
                "mysql_sum_query",
                lambda plan, stage, keys, columns: (
                    calls.append(plan) or original(plan, stage, keys, columns)
                ),
            )
            sums = "".join(f"        x{index} = sum(a)\n" for index in range(count))
            _, outcome = probe.numeric_world(
                tmp_path / str(count),
                "mysql",
                "query result:\n    from rows\n    group by k\n    select:\n"
                "        k\n" + sums,
            )
        assert outcome.status == "VERIFIED", outcome.blockers
        counts.append(len(calls))
    assert counts[0] == counts[1] > 0


# MC G1 (Carrier): the public nullability of each form's columns, which only
# a non-null GROUP BY key and a count leave non-null.
G1_NON_NULL = {
    "N1": set(),
    "N2": {"k"},
    "N3": set(),
    "N4": {"k", "m"},
    "I1": set(),
    "I2": {"k"},
    "I3": set(),
    "I4": {"n"},
    "I5": {"k"},
    "I6": {"m"},
    "L1": {"k"},
    "L2": set(),
    "L3": {"k"},
    "L4": {"g"},
}
# The storage of each form's `min` or `max` column on (PostgreSQL, MySQL):
# a BIGINT one keeps its field's carrier, an INT one is MySQL's cast
# my_signed_int over any source (PL.67, PL.73) and PostgreSQL's int4.
_EXTREME_BIGINT = ("pg_int8", "my_bigint")
_EXTREME_INT = ("pg_int4", "my_signed_int")
G1_EXTREMES = {"N4": {"lo": _EXTREME_BIGINT}, "I6": {"lo": _EXTREME_INT}}


def _assert_extreme_carriers(document, target, extremes):
    """Each named extreme column's storage on ``target``."""
    position = 0 if target == "postgres" else 1
    storages = {
        column["label"]: column["representation"]["storage"]
        for column in document["columns"]
    }
    for label, kinds in extremes.items():
        assert storages[label] == {"kind": kinds[position]}, label


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(probe.G1_FORMS))
def test_mysql_g1_forms_emit_the_guarded_sum(tmp_path, form, target):
    """MC G1: a MySQL project emits S02's guarded SUM of a nullable or
    non-null BIGINT or INT source field, or of a `let` name whose value is
    one, in an S02 cell otherwise: a nullable Int, NULL for no or only NULL
    values, 1690 (SQLSTATE 22003) outside signed 64 bits. Both families emit
    the pinned SQL, pairwise distinct per family and PostgreSQL's
    unchanged, and every reader accepts it."""
    checked, outcome = probe.numeric_world(tmp_path, target, probe.G1_FORMS[form])
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G1_FORM_SQL[form, target]
    document = json.loads(serialize_project_sql_emission(outcome))
    assert {
        column["label"] for column in document["columns"] if not column["nullable"]
    } == G1_NON_NULL[form]
    _assert_extreme_carriers(document, target, G1_EXTREMES.get(form, {}))
    texts = [probe.G1_FORM_SQL[name, target] for name in probe.G1_FORMS]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("spelling", sorted(probe.G1_SPELLINGS))
def test_mysql_g1_spellings_emit_their_form_sql(tmp_path, spelling):
    """A read qualified by the source's name, parentheses, an identity `def`,
    a `table` declaration and a `group by:` block, in a sum or in its
    `let`, and parentheses or an identity `def` around a `let` name in its
    sum, emit the form's bytes."""
    form, body = probe.G1_SPELLINGS[spelling]
    _, outcome = probe.numeric_world(tmp_path, "mysql", body)
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G1_FORM_SQL[form, "mysql"]


def _unguarded_sum(data):
    """``data`` with its one guarded SUM cut down to a bare SUM(x): the
    first read of x kept, the guard's other tokens and reads gone and
    every later range moved."""
    guard = {
        item["role"]: item
        for item in data["ranges"]
        if item["role"].startswith("aggregate_guard")
    }
    opened, high, closed = (
        guard["aggregate_guard_" + name] for name in ("open", "high", "close")
    )
    start, cut, end = opened["start"], high["start"], closed["end"]
    raw = data["sql"].encode("utf-8")
    data["sql"] = (
        raw[:start] + b"SUM(" + raw[opened["end"] : cut] + b")" + raw[end:]
    ).decode("utf-8")
    inner = len(b"SUM(") - (opened["end"] - start)
    later = inner + len(b")") + cut - end
    kept = []
    for item in data["ranges"]:
        if item is opened:
            item.update(role="aggregate_open", end=start + len(b"SUM("))
        elif item is closed:
            item.update(role="aggregate_close", start=cut + inner, end=cut + inner + 1)
        elif cut <= item["start"] and item["end"] <= end:
            continue
        elif opened["end"] <= item["start"] and item["end"] <= cut:
            item.update(start=item["start"] + inner, end=item["end"] + inner)
        else:
            for name in ("start", "end"):
                item[name] += later if item[name] >= end else 0
        kept.append(item)
    data["ranges"] = kept
    return data


@pytest.mark.parametrize("form", ("I1", "N2"))
def test_the_public_decoder_refuses_an_unguarded_mysql_sum(tmp_path, form):
    """S02, MC G1: the public decoder takes a MySQL SUM only as S02's
    guarded one. A form's public document with its guard cut down to a
    bare SUM(x) and its ranges moved, which no emitter writes and which
    returns MySQL's DECIMAL, is refused for that alone."""
    _, outcome = probe.numeric_world(tmp_path, "mysql", probe.G1_FORMS[form])
    assert public(outcome)["status"] == "VERIFIED"
    forged = _unguarded_sum(document(outcome))
    assert "CASE" not in forged["sql"] and "SUM(" in forged["sql"]
    with pytest.raises(ValueError, match="^unguarded MySQL SUM$"):
        probe.decode_public(probe.encoded(forged))


def test_the_public_decoder_refuses_a_guarded_mysql_sum_of_a_smallint(tmp_path):
    """MC G1: the public decoder takes S02's guarded SUM over a BIGINT or INT
    field only. I1's public document with its nullable INT field `c`
    retexted as a SMALLINT, its declared range with it, which no emitter
    writes, is refused for that alone."""
    _, outcome = probe.numeric_world(tmp_path, "mysql", probe.G1_FORMS["I1"])
    published = serialize_project_sql_emission(outcome)
    assert probe.decode_public(published)["status"] == "VERIFIED"
    field = b'"max":"2147483647","min":"-2147483648"},"nullable":true,"storage":'
    assert published.count(field + b'{"kind":"my_int"}') == 1
    forged = published.replace(
        field + b'{"kind":"my_int"}',
        field.replace(b"2147483647", b"32767").replace(b"2147483648", b"32768")
        + b'{"kind":"my_smallint"}',
    )
    with pytest.raises(ValueError, match="^guarded SUM argument$"):
        probe.decode_public(forged)


def _mysql_spelling(sql, body, ints: set[str] | frozenset[str] = frozenset({"k", "c"})):
    """PostgreSQL SQL in MySQL's spelling, each checked bigint SUM replaced
    by S02's guarded SUM of its argument, each float8 cast of an `avg`
    argument a DOUBLE one and each grouped MIN or MAX of an INT field (one
    of ``ints``, NUMERIC_HEADER's `k` and `c` by default, also through a
    `let` name) cast to SIGNED, whether ``body`` reads it straight from the
    source or through a `let` or WHERE stage, as main's MySQL SQL casts it
    (PL.73)."""
    import re

    guard = grouping.MYSQL_SUM_GUARD
    lets = dict(re.findall(r"^    let (\w+) = (.+)$", body, re.M))
    widened = [
        re.findall(r"\w+", lets.get(name, name))[-1] in ints
        for name in (
            re.findall(r"\w+", argument)[-1]
            for argument in re.findall(r"= (?:min|max)\((.+)\)$", body, re.M)
        )
    ]
    extremes = re.compile(r"(?:MIN|MAX)\([^()]+\)")
    assert len(widened) == len(extremes.findall(sql))
    marks = iter(widened)
    sql = extremes.sub(
        lambda found: (
            f"CAST({found.group(0)} AS SIGNED)" if next(marks) else found.group(0)
        ),
        sql,
    )
    return (
        re.sub(
            r"CAST\(SUM\(CAST\((\S+) AS pg_catalog\.int8\)\) AS pg_catalog\.int8\)",
            lambda found: "".join(
                (found.group(1) if position else "") + text
                for position, (_, text) in enumerate(guard)
            ),
            sql,
        )
        .replace("AS pg_catalog.int8)", "AS SIGNED)")
        .replace("AS pg_catalog.float8)", "AS DOUBLE)")
        .replace('"', "`")
        .replace("`public`.", "`phase66`.")
    )


@pytest.mark.parametrize(
    "name", sorted({*probe.G1_FORMS, *probe.G1_CELLS, *probe.G1_SPELLINGS})
)
def test_mysql_g1_sql_is_main_postgresql_sql_but_the_guard(tmp_path, name):
    """Each G1 body's MySQL SQL is main's PostgreSQL SQL of it, `let` stages
    included, in MySQL's spelling with each sum S02's guarded SUM and each
    `min` of an INT field cast to SIGNED, from the source or through a stage
    (I6's `lo`, `let_beside_count`'s `lo`),
    and every reader accepts it: so a combination the forms do not run (a `let` sum
    beside `count`, one `let` read by two sums) rests on the forms' parts."""
    body = (
        probe.G1_SPELLINGS.get(name, (None, None))[1]
        or {
            **probe.G1_FORMS,
            **probe.G1_CELLS,
        }[name]
    )
    _, postgres = probe.numeric_world(tmp_path / "postgres", "postgres", body)
    _, mysql = probe.numeric_world(tmp_path / "mysql", "mysql", body)
    probe.numeric_readers_accept(mysql)
    assert postgres.artifact is not None and mysql.artifact is not None
    assert mysql.artifact.rendered.sql.decode() == _mysql_spelling(
        postgres.artifact.rendered.sql.decode(), body
    )


@pytest.mark.parametrize("field", ("n", "c"))
@pytest.mark.parametrize(
    "cell", sorted(name for name in probe.NUMERIC_CELLS if name.startswith("s02"))
)
def test_mysql_g1_argument_changes_only_the_guarded_sum(tmp_path, cell, field):
    """An S02 cell body whose `sum(a)` sums a non-null BIGINT or a nullable
    INT field instead emits the S02 SQL with only that guarded SUM's
    argument changed."""
    column = {"n": ("nn", "c4"), "c": ("narrow", "c5")}[field]
    _, outcome = probe.numeric_world(
        tmp_path,
        "mysql",
        probe.NUMERIC_CELLS[cell].replace("sum(a)", "sum(%s)" % field),
    )
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    expected = (
        probe.NUMERIC_CELL_SQL[cell, "mysql"]
        .replace("SUM(`s0`.`left_value`)", "SUM(`s0`.`%s`)" % column[0])
        .replace("SUM(`t1`.`c1`)", "SUM(`t1`.`%s`)" % column[1])
    )
    assert outcome.artifact.rendered.sql.decode() == expected


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G1_REFUSALS))
def test_mysql_g1_neighbours_keep_main_refusal(tmp_path, shape, policy):
    """Rule two (D77.37): a statement the G1 law matches beside another
    blocker (a label too long, a sum outside every cell) and one outside
    the law (a SMALLINT
    field, a `let` chain, a `let` value other than one field read, a `let`
    read outside a sum argument, its GROUP BY key included, a value `let`
    that nothing reads) keep main's blockers, object for
    object, under each policy they are refused with; PostgreSQL emits each
    but the long label as main does."""
    if policy not in probe.G1_REFUSAL_POLICIES.get(shape, (policy,)):
        pytest.skip("refused under its own policy only")
    body = probe.G1_REFUSALS[shape]
    world = probe.G1_REFUSAL_WORLDS.get(shape, {})
    _, outcome = probe.numeric_world(tmp_path / "mysql", "mysql", body, policy, **world)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == probe.G1_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.numeric_world(
        tmp_path / "postgres", "postgres", body, policy, **world
    )
    if shape in probe.G1_POSTGRES_BLOCKERS:
        assert _numeric_blockers(postgres) == probe.G1_POSTGRES_BLOCKERS[shape]
    else:
        assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_mysql_smallint_reads_keep_s02_own_cell_beside_g1(tmp_path, policy):
    """MC G1 (lead ruling of 2026-11-21, S02-SMALLINT): no G1 form reads a
    SMALLINT field, so S02's own SMALLINT GROUP BY key, and a `count` or
    `min` of a SMALLINT field, stay in S02's cell: beside sums of nullable
    BIGINT fields and no `let` every reader accepts them, while beside a
    sum of an INT or non-null BIGINT field or of a `let` they keep main's
    blockers, object for object; PostgreSQL emits each."""
    for name, body in probe.G1_SMALLINT_CELLS.items():
        _, outcome = probe.division_world(tmp_path / name, "mysql", body, policy)
        probe.numeric_readers_accept(outcome)
    for name, (body, blockers) in probe.G1_SMALLINT_REFUSALS.items():
        _, refused = probe.division_world(tmp_path / name, "mysql", body, policy)
        assert refused.status == "BLOCKED" and refused.artifact is None
        assert _numeric_blockers(refused) == blockers, name
        _, postgres = probe.division_world(
            tmp_path / f"{name}-postgres", "postgres", body, policy
        )
        assert postgres.status == "VERIFIED", postgres.blockers


# MC G2 (Aggregates and grouping): the public nullability of each form's
# columns, which only a non-null GROUP BY key and a count leave non-null.
G2_NON_NULL = {
    "A1": set(),
    "A2": {"k"},
    "A3": {"g", "r", "d", "m"},
    "A4": {"d"},
    "K1": set(),
    "K2": {"r"},
    "K3": {"k", "n"},
    "K4": {"tag"},
    "K5": set(),
    "K6": set(),
    "K7": {"kk", "m"},
    "M1": {"tag", "m"},
    "M2": {"r"},
}
# A3's `max(c)` reads its INT field straight from the base table, A4's,
# M1's and M2's through `let` and WHERE stages: each is a my_signed_int.
G2_EXTREMES = {
    "A1": {"hi": _EXTREME_BIGINT},
    "A2": {"lo": _EXTREME_BIGINT, "hi": _EXTREME_BIGINT},
    "A3": {"hc": _EXTREME_INT},
    "A4": {"hi": _EXTREME_INT},
    "K5": {"hi": _EXTREME_BIGINT},
    "M1": {"hi": _EXTREME_BIGINT, "lo": _EXTREME_INT},
    "M2": {"hi": _EXTREME_INT},
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(probe.G2_FORMS))
def test_mysql_g2_forms_emit_the_guarded_sum(tmp_path, form, target):
    """MC G2: a MySQL project emits S02's guarded SUM beside `count`,
    `count()`, `min`, a `count_distinct` of a BIGINT, INT or VARCHAR field
    and a `max` or `avg` of a BIGINT or INT field, by any number of BIGINT,
    INT or VARCHAR keys, nullable or not, in G1's cell otherwise. Both
    families emit the pinned SQL, pairwise distinct per family and
    PostgreSQL's unchanged; every reader accepts it, the pure boundary's
    re-rendering included."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    checked, outcome = probe.grouping_world(tmp_path, target, probe.G2_FORMS[form])
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G2_FORM_SQL[form, target]
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    ).canonical_bytes
    assert observed is not None and pure.rendering_refusal(observed) is None
    document = json.loads(serialize_project_sql_emission(outcome))
    assert {
        column["label"] for column in document["columns"] if not column["nullable"]
    } == G2_NON_NULL[form]
    _assert_extreme_carriers(document, target, G2_EXTREMES.get(form, {}))
    texts = [probe.G2_FORM_SQL[name, target] for name in probe.G2_FORMS]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("spelling", sorted(probe.G2_SPELLINGS))
def test_mysql_g2_spellings_emit_their_form_sql(tmp_path, spelling):
    """A read qualified by the source's name in a sum, a count or a `let`,
    parentheses around a `max` argument, an identity `def` around an `avg`
    argument, a `table` declaration and a `group by:` block of two keys emit
    the form's bytes."""
    form, body = probe.G2_SPELLINGS[spelling]
    _, outcome = probe.grouping_world(tmp_path, "mysql", body)
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G2_FORM_SQL[form, "mysql"]


def _guarded_maxima(sql, summed):
    """MySQL SQL whose n-th MAX(arg) is S02's guarded SUM of arg wherever
    ``summed``[n] holds; where main's MySQL SQL casts that MAX to SIGNED
    (a grouped MAX of an INT, over any source), the whole cast is replaced,
    so no cast wraps a guard."""
    import re

    marks = iter(summed)
    return re.sub(
        r"CAST\(MAX\(([^()]+)\) AS SIGNED\)|MAX\(([^()]+)\)",
        lambda found: (
            "".join(
                (found.group(1) or found.group(2) if position else "") + text
                for position, (_, text) in enumerate(grouping.MYSQL_SUM_GUARD)
            )
            if next(marks)
            else found.group(0)
        ),
        sql,
    )


@pytest.mark.parametrize(
    "name",
    sorted(
        {*probe.G2_FORMS, *probe.G2_CELLS, *probe.G2_SPELLINGS, *probe.G2_ORDERS_CELLS}
    ),
)
def test_mysql_g2_sql_is_main_max_sql_but_the_guard(tmp_path, name):
    """B2: each G2 body's MySQL SQL, `let` stages kept as G1 keeps them, is
    main's MySQL SQL of the same body with every `sum(x)` written `max(x)`,
    each such MAX(x), or the whole CAST(MAX(x) AS SIGNED) where main casts
    it (a grouped MAX of an INT, over any source), S02's guarded SUM of x:
    so every key,
    every other aggregate, FROM, WHERE and GROUP BY are main's verified
    MySQL emission, and a combination the forms do not run (four keys, a key
    selected twice, a `count` of a Bool beside `max`) rests on the forms'
    parts. As for G1, it is also main's PostgreSQL SQL of the body, `let`
    stages included, in MySQL's spelling with each sum S02's guarded SUM and
    each `min` or `max` of an INT field cast to SIGNED, from the source or
    through a stage."""
    import re

    body = (
        probe.G2_SPELLINGS.get(name, (None, None))[1]
        or {**probe.G2_FORMS, **probe.G2_CELLS, **probe.G2_ORDERS_CELLS}[name]
    )
    world = probe.s03_world if name in probe.G2_ORDERS_CELLS else probe.grouping_world
    _, maxima = world(tmp_path / "max", "mysql", body.replace("sum(", "max("))
    _, outcome = world(tmp_path / "sum", "mysql", body)
    probe.numeric_readers_accept(outcome)
    assert maxima.artifact is not None and outcome.artifact is not None
    summed = [found == "sum" for found in re.findall(r"= (sum|max)\(", body)]
    assert outcome.artifact.rendered.sql.decode() == _guarded_maxima(
        maxima.artifact.rendered.sql.decode(), summed
    )
    _, postgres = world(tmp_path / "postgres", "postgres", body)
    assert postgres.artifact is not None, postgres.blockers
    assert outcome.artifact.rendered.sql.decode() == _mysql_spelling(
        postgres.artifact.rendered.sql.decode(),
        body,
        {"customer"} if name in probe.G2_ORDERS_CELLS else {"k", "c"},
    )


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G2_REFUSALS))
def test_mysql_g2_neighbours_keep_main_refusal(tmp_path, shape, policy):
    """Rule two (D77.37): a statement the G2 law matches beside another
    blocker (a label too long, a sum outside every cell) and one outside
    it (`string_agg`, a conditional count (a conditional sum is MC G7's
    cell), a `count_distinct` of two
    fields, `stddev`, `variance`, `pvariance`, `pstdev`, `median`,
    `quantile`, `any` or `all`, an `avg` of an expression, a Bool key or
    `count_distinct`, a `max` of a `let`) keep main's blockers, object for
    object, under each policy they are refused with; PostgreSQL emits each
    but the long label as main does."""
    if policy not in probe.G2_REFUSAL_POLICIES.get(shape, (policy,)):
        pytest.skip("refused under its own policy only")
    body = probe.G2_REFUSALS[shape]
    world = probe.G2_REFUSAL_WORLDS.get(shape, {})
    _, outcome = probe.grouping_world(
        tmp_path / "mysql", "mysql", body, policy, **world
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == probe.G2_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.grouping_world(
        tmp_path / "postgres", "postgres", body, policy, **world
    )
    if shape in probe.G2_POSTGRES_BLOCKERS:
        assert _numeric_blockers(postgres) == probe.G2_POSTGRES_BLOCKERS[shape]
    else:
        assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_a_refused_g3_neighbour_with_an_int_extreme_keeps_main_refusal(
    tmp_path, policy
):
    """Rule two under PL.73: a statement outside the law, here MC G3's
    (ORDER BY on its INT key `k` then `limit 2`, G3's X2: a LIMIT after a
    key first), whose `max` of an INT field reads the base table directly
    keeps exactly the sum's blocker; the extreme's cast adds none, and
    PostgreSQL emits it. G3 opens the same body ordered by `k` alone (an
    ORDER BY key that is an INT key) and G2 the body with no clause: each
    emits that `max` cast to SIGNED as a my_signed_int, its sum S02's
    guarded SUM (main's MySQL SQL of the body with the sum written `max`),
    every reader accepting it."""
    import re

    grouped = (
        "query result:\n    from rows\n    group by k\n    select:\n        k\n"
        "        x = sum(n)\n        hc = max(c)\n"
    )
    ordered = grouped + "    order by:\n        k\n"
    limited = ordered + "    limit 2\n"
    _, refused = probe.grouping_world(tmp_path / "mysql", "mysql", limited, policy)
    assert refused.status == "BLOCKED" and refused.artifact is None
    assert _numeric_blockers(refused) == [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 16, 9)
    ]
    _, postgres = probe.grouping_world(
        tmp_path / "postgres", "postgres", limited, policy
    )
    assert postgres.status == "VERIFIED", postgres.blockers
    for name, body in (("open", grouped), ("ordered", ordered)):
        _, opened = probe.grouping_world(tmp_path / name, "mysql", body, policy)
        probe.numeric_readers_accept(opened)
        assert opened.artifact is not None, opened.blockers
        sql = opened.artifact.rendered.sql.decode()
        assert "CAST(MAX(`s0`.`narrow`) AS SIGNED)" in sql
        assert "CAST(CASE WHEN SUM(" not in sql
        _assert_extreme_carriers(
            json.loads(serialize_project_sql_emission(opened)),
            "mysql",
            {"hc": _EXTREME_INT},
        )
        _, maxima = probe.grouping_world(
            tmp_path / (name + "max"), "mysql", body.replace("sum(", "max("), policy
        )
        assert maxima.artifact is not None, maxima.blockers
        summed = [found == "sum" for found in re.findall(r"= (sum|max)\(", body)]
        assert sql == _guarded_maxima(maxima.artifact.rendered.sql.decode(), summed)


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_mysql_s02_smallint_key_keeps_its_cell_beside_g2(tmp_path, policy):
    """G2 keeps S02's own law beside its own: a non-null SMALLINT key beside
    a sum, a count and a min stays in the cell with main's bytes, every
    reader accepting them, while beside a `max`, ordered by or read by a
    HAVING line (MC G3: an ORDER BY key is BIGINT, INT or VARCHAR, a HAVING
    one BIGINT or INT), nullable, or beside a second key it keeps main's
    blockers, and so does a `count` or `min` of a SMALLINT field beside a G2
    aggregate or a second key, and that key or such a `count` or `min`
    under any G3 clause (lead ruling of 2026-11-21, S02-SMALLINT), and a
    `max`, `avg` or `count_distinct` of one, outside G2's storages;
    PostgreSQL emits each."""
    _, outcome = probe.division_world(
        tmp_path / "cell", "mysql", probe.G2_S02_KEY, policy
    )
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G2_S02_KEY_SQL
    # `min(i)` of a nullable INT straight from the base table (PL.73).
    _assert_extreme_carriers(
        json.loads(serialize_project_sql_emission(outcome)),
        "mysql",
        {"lo": _EXTREME_INT},
    )
    for name, (body, blockers) in probe.G2_S02_KEY_REFUSALS.items():
        _, refused = probe.division_world(tmp_path / name, "mysql", body, policy)
        assert refused.status == "BLOCKED" and refused.artifact is None
        assert _numeric_blockers(refused) == blockers
        _, postgres = probe.division_world(
            tmp_path / f"{name}-postgres", "postgres", body, policy
        )
        assert postgres.status == "VERIFIED", postgres.blockers


# MC G3 (Later clauses): the public nullability of each form's columns, which
# HAVING, ORDER BY, LIMIT and DISTINCT leave as G2 has them.
G3_NON_NULL = {
    "H1": {"k"},
    "H2": {"r"},
    "H3": {"k", "tag"},
    "H4": {"g", "m"},
    "H5": {"d"},
    "O1": {"k"},
    "O2": {"tag"},
    "O3": {"kk"},
    "L1": {"k"},
    "L2": {"tag", "r"},
    "L3": set(),
    "D1": set(),
    "D2": {"tag"},
    "M1": {"tag", "r"},
    "M2": set(),
    "M3": {"kk"},
}
# The storage of each G3 form's `min` or `max` column, as G1_EXTREMES.
G3_EXTREMES = {"H3": {"hi": _EXTREME_BIGINT}}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(probe.G3_FORMS))
def test_mysql_g3_forms_emit_the_guarded_sum(tmp_path, form, target):
    """MC G3: a MySQL project emits S02's guarded SUM in G2's cell with a
    GROUP BY key and HAVING lines comparing a BIGINT or INT key or an
    aggregate other than `avg` with an unsigned literal (a line on a sum
    alone), ORDER BY keys of such outputs or Text keys, a LIMIT after an
    ORDER BY whose first key is an aggregate, and DISTINCT beside no `avg`.
    Both families emit the pinned SQL, pairwise distinct per family and
    PostgreSQL's unchanged, H3's `max` of a BIGINT field keeping its
    carrier (G3_EXTREMES); every reader accepts it, the pure boundary's
    re-rendering included."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    checked, outcome = probe.grouping_world(tmp_path, target, probe.G3_FORMS[form])
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G3_FORM_SQL[form, target]
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    ).canonical_bytes
    assert observed is not None and pure.rendering_refusal(observed) is None
    document = json.loads(serialize_project_sql_emission(outcome))
    assert {
        column["label"] for column in document["columns"] if not column["nullable"]
    } == G3_NON_NULL[form]
    _assert_extreme_carriers(document, target, G3_EXTREMES.get(form, {}))
    texts = [probe.G3_FORM_SQL[name, target] for name in probe.G3_FORMS]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("spelling", sorted(probe.G3_SPELLINGS))
def test_mysql_g3_spellings_emit_their_form_sql(tmp_path, spelling):
    """`order by x desc` on one line, `asc` written out, a `table`
    declaration, a `group by:` block, a sum argument qualified by the
    source's name, an identity `def` around it and a `def` call in place of
    the HAVING literal it returns emit the form's bytes."""
    form, body = probe.G3_SPELLINGS[spelling]
    _, outcome = probe.grouping_world(tmp_path, "mysql", body)
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G3_FORM_SQL[form, "mysql"]


@pytest.mark.parametrize(
    "name",
    sorted(
        {*probe.G3_FORMS, *probe.G3_CELLS, *probe.G3_SPELLINGS, *probe.G3_ORDERS_CELLS}
    ),
)
def test_mysql_g3_sql_is_main_max_sql_but_the_guard(tmp_path, name):
    """B: each G3 body's MySQL SQL, `let` stages kept, is main's MySQL SQL of
    the same body with every `sum(x)` written `max(x)`, each such MAX(x)
    (or main's whole cast of it) S02's guarded SUM of x: HAVING, ORDER BY,
    LIMIT and DISTINCT read the aggregation stage's columns, so they and
    every key, every other aggregate, FROM and WHERE are main's verified
    MySQL emission (language.md's own example, P1, included). It is also
    main's PostgreSQL SQL of the body in MySQL's spelling with each sum
    S02's guarded SUM and each `min` or `max` of an INT field cast to
    SIGNED, from the source or through a stage (PL.73)."""
    import re

    body = (
        probe.G3_SPELLINGS.get(name, (None, None))[1]
        or {**probe.G3_FORMS, **probe.G3_CELLS, **probe.G3_ORDERS_CELLS}[name]
    )
    world = probe.s03_world if name in probe.G3_ORDERS_CELLS else probe.grouping_world
    _, maxima = world(tmp_path / "max", "mysql", body.replace("sum(", "max("))
    _, outcome = world(tmp_path / "sum", "mysql", body)
    probe.numeric_readers_accept(outcome)
    assert maxima.artifact is not None and outcome.artifact is not None
    summed = [found == "sum" for found in re.findall(r"= (sum|max)\(", body)]
    assert outcome.artifact.rendered.sql.decode() == _guarded_maxima(
        maxima.artifact.rendered.sql.decode(), summed
    )
    _, postgres = world(tmp_path / "postgres", "postgres", body)
    assert postgres.artifact is not None, postgres.blockers
    assert outcome.artifact.rendered.sql.decode() == _mysql_spelling(
        postgres.artifact.rendered.sql.decode(),
        body,
        {"customer"} if name in probe.G3_ORDERS_CELLS else {"k", "c"},
    )


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G3_REFUSALS))
def test_mysql_g3_neighbours_keep_main_refusal(tmp_path, shape, policy):
    """Rule two (D77.37): a statement the G3 law matches beside another
    blocker (a label too long, a sum outside every cell) and one outside it
    (a LIMIT with no ORDER BY, after an ORDER BY of keys only or of a key
    first, `limit 0`, a HAVING line on a sum beside another line, on two
    outputs, with `or`, written literal first, on a Text key or on an
    `avg`, DISTINCT beside an `avg` or with no GROUP BY, an ORDER BY key
    that is an `avg`) keep
    main's blockers, object for object, under each policy they are refused
    with; PostgreSQL emits each but the long label as main does."""
    if policy not in probe.G3_REFUSAL_POLICIES.get(shape, (policy,)):
        pytest.skip("refused under its own policy only")
    body = probe.G3_REFUSALS[shape]
    _, outcome = probe.grouping_world(tmp_path / "mysql", "mysql", body, policy)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == probe.G3_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.grouping_world(tmp_path / "postgres", "postgres", body, policy)
    if shape in probe.G3_POSTGRES_BLOCKERS:
        assert _numeric_blockers(postgres) == probe.G3_POSTGRES_BLOCKERS[shape]
    else:
        assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize("shape", sorted(probe.G3_SEMANTIC_REFUSALS))
def test_mysql_g3_shapes_outside_semantics_reach_no_emission_law(tmp_path, shape):
    """`is not None` or a signed literal in HAVING, HAVING or ORDER BY with
    no GROUP BY, an ORDER BY key that is no selected output or an
    expression, and a HAVING line on a key not selected fail semantics on
    both targets alike, so G3's law never sees them."""
    lists = []
    for target in ("postgres", "mysql"):
        _, outcome = probe.grouping_world(
            tmp_path / target, target, probe.G3_SEMANTIC_REFUSALS[shape]
        )
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        lists.append(_numeric_blockers(outcome))
    assert lists[0] == lists[1]
    assert lists[0][0][:2] == ("PIE-B1003", "semantic_result_unsuccessful")


# MC G4 (Source organization): the public nullability of each form's
# columns, through an upstream the nullability of the field a key carries.
G4_NON_NULL = {
    "S1": {"k"},
    "S2": {"m"},
    "S3": {"tag"},
    "S4": set(),
    "U1": {"k"},
    "U2": {"r"},
    "U3": {"tag"},
    "U4": {"k"},
    "U5": set(),
    "A1": {"k"},
    "A2": {"m"},
    "A3": set(),
    "A4": set(),
    "L1": {"k"},
    "L2": {"k"},
}
# The storage of each G4 form's `min` or `max` column, as G1_EXTREMES': S3's
# of the BIGINT `a`, U5's of the INT `c` over a plain upstream and A3's of the
# INT key `k` of an aggregating one, each cast to SIGNED on MySQL.
G4_EXTREMES = {
    "S3": {"hi": _EXTREME_BIGINT},
    "U5": {"lo": _EXTREME_INT},
    "A3": {"kk": _EXTREME_INT},
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(probe.G4_FORMS))
def test_mysql_g4_forms_emit_the_guarded_sum(tmp_path, form, target):
    """MC G4: a MySQL project emits S02's guarded SUM in the cell of G1 to G3
    reached through relation aliases of what FROM reads, windows that
    nothing reads, reads qualified by a relation's name, and one upstream
    `query` or `table` that projects field reads or aggregates by a key with
    a sum, each of whose sums the query reads, at both levels. Both families
    emit the pinned SQL, pairwise distinct per family and PostgreSQL's
    unchanged; every reader accepts it, the pure boundary's re-rendering
    included."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    checked, outcome = probe.grouping_world(tmp_path, target, probe.G4_FORMS[form])
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G4_FORM_SQL[form, target]
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    ).canonical_bytes
    assert observed is not None and pure.rendering_refusal(observed) is None
    document = json.loads(serialize_project_sql_emission(outcome))
    assert {
        column["label"] for column in document["columns"] if not column["nullable"]
    } == G4_NON_NULL[form]
    _assert_extreme_carriers(document, target, G4_EXTREMES.get(form, {}))
    texts = [probe.G4_FORM_SQL[name, target] for name in probe.G4_FORMS]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    "name", sorted({*probe.G4_SPELLINGS, *(f"B3_{form}" for form in probe.G4_PLAIN)})
)
def test_mysql_g4_spellings_emit_their_form_sql(tmp_path, name, target):
    """B3: a form's plain body (each relation alias read as its relation,
    each unread window dropped, each read unqualified), the form with its
    source or upstream imported, under its own name or another or through a
    re-export, and G2's spellings (`table`, `group by:` blocks, parentheses,
    an identity `def`) emit the form's bytes on both targets."""
    form, body = (
        (name[3:], probe.G4_PLAIN[name[3:]])
        if name.startswith("B3_")
        else probe.G4_SPELLINGS[name]
    )
    _, outcome = probe.grouping_world(tmp_path, target, body)
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G4_FORM_SQL[form, target]


@pytest.mark.parametrize(
    "name", sorted({*probe.G4_FORMS, *probe.G4_CELLS, *probe.G4_ORDERS_CELLS})
)
def test_mysql_g4_sql_is_main_max_sql_but_the_guard(tmp_path, name):
    """B2, after B3: each G4 body's MySQL SQL (a form's plain body), `let`
    stages kept, is main's MySQL SQL of the same body with every `sum(x)`
    written `max(x)` at both levels, each such MAX(x) (or main's whole cast
    of it) S02's guarded SUM of x: every key, every other aggregate, FROM,
    WHERE, the upstream's stages and the query's reads of them are main's
    verified MySQL emission. The bodies the law opens beyond the forms
    (main's refused relation aliases, unread windows, imported sources and
    plain upstreams, S03's `ctl_t_plain_first_level` among them) keep it
    too."""
    import re

    body = (
        probe.G4_PLAIN.get(name)
        or {
            **probe.G4_FORMS,
            **probe.G4_CELLS,
            **probe.G4_ORDERS_CELLS,
        }[name]
    )
    world = probe.s03_world if name in probe.G4_ORDERS_CELLS else probe.grouping_world
    files = body if type(body) is dict else {"main.pietto": body}
    _, maxima = world(
        tmp_path / "max",
        "mysql",
        {path: text.replace("sum(", "max(") for path, text in files.items()},
    )
    _, outcome = world(tmp_path / "sum", "mysql", body)
    probe.numeric_readers_accept(outcome)
    assert maxima.artifact is not None and outcome.artifact is not None
    summed = [
        found == "sum"
        for text in files.values()
        for found in re.findall(r"= (sum|max)\(", text)
    ]
    assert outcome.artifact.rendered.sql.decode() == _guarded_maxima(
        maxima.artifact.rendered.sql.decode(), summed
    )


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G4_REFUSALS))
def test_mysql_g4_neighbours_keep_main_refusal(tmp_path, shape, policy):
    """Rule two (D77.37): a statement the G4 law matches beside another
    blocker (a label too long, over one level or two, an upstream item that
    computes) and one outside it (an
    upstream with HAVING, ORDER BY with LIMIT or not, DISTINCT, a JOIN or a
    read window, or a set operation (a third level is MC G8's chain), an
    alias of an alias or of a relation FROM does not read (a
    second import name of FROM's upstream included), an upstream declared
    as a relation `let` block, an aggregating upstream with an unread sum,
    no key or no sum, under a
    WHERE, HAVING, ORDER BY with LIMIT or not, or DISTINCT, an upstream sum
    or `avg` as a key or as the argument of `max`, `avg` or
    `count_distinct`, a sum of an `avg`,
    an upstream `min` of an INT field, MySQL's cast `my_signed_int`, as a
    key or `max`, `avg` or `count_distinct` argument, below the upstream's
    WHERE or not (Law item 5), a `min` of an upstream `min` or `max` of an
    INT, Float, Timestamp, Decimal or Date field, a count or distinct count
    of an upstream extreme, a min or count of an upstream average,
    a query with no sum or no aggregate over an aggregating upstream, a
    plain upstream with a `let` or a computed item) keep main's blockers,
    object for object, under each policy they are refused with; PostgreSQL
    emits each but the long labels and the set operation as main does."""
    if policy not in probe.G4_REFUSAL_POLICIES.get(shape, (policy,)):
        pytest.skip("refused under its own policy only")
    body = probe.G4_REFUSALS[shape]
    world = probe.G4_REFUSAL_WORLDS.get(shape, {})
    _, outcome = probe.grouping_world(
        tmp_path / "mysql", "mysql", body, policy, **world
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == probe.G4_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.grouping_world(
        tmp_path / "postgres", "postgres", body, policy, **world
    )
    if shape in probe.G4_POSTGRES_BLOCKERS:
        assert _numeric_blockers(postgres) == probe.G4_POSTGRES_BLOCKERS[shape]
    else:
        assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G4_SMALLINT_REFUSALS))
def test_mysql_g4_keeps_smallint_reads_in_s02_cell(tmp_path, shape, policy):
    """MC G4 over G1 to G3 (lead ruling of 2026-11-21, S02-SMALLINT): S02's
    own SMALLINT GROUP BY key, and a `count` or `min` of a SMALLINT field,
    stay in S02's cell as main takes it, so a relation alias, an unread
    window, an imported source and a plain or aggregating upstream beside
    one keep main's blockers, object for object, under both policies;
    PostgreSQL emits each."""
    body, blockers = probe.G4_SMALLINT_REFUSALS[shape]
    name, keywords = probe.G4_SMALLINT_WORLDS.get(shape, ("division_world", {}))
    world = getattr(probe, name)
    _, outcome = world(tmp_path / "mysql", "mysql", body, policy, **keywords)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == blockers
    _, postgres = world(tmp_path / "postgres", "postgres", body, policy, **keywords)
    assert postgres.status == "VERIFIED", postgres.blockers


# MC G5 (Parameters): the public nullability of each form's columns, which
# header parameters and bind-safe literals leave as G2 to G4 have them.
G5_NON_NULL = {
    "U1": {"k"},
    "U2": set(),
    "P1": {"r"},
    "P2": {"k", "m"},
    "P3": {"k"},
    "P4": {"d", "tag"},
    "P5": {"m"},
    "B1": {"k"},
    "B2": {"m"},
    "B3": {"r"},
    "M1": {"tag"},
    "M2": set(),
    "L1": {"k"},
    "L2": set(),
    "L3": set(),
    "L4": {"r", "tag"},
    "S1": {"k"},
    "S2": {"r"},
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(probe.G5_FORMS))
def test_mysql_g5_forms_emit_the_guarded_sum(tmp_path, form, target):
    """MC G5: a MySQL project emits S02's guarded SUM in the cell of G1 to G4
    with header parameters of Bool, Int, Float or Text, read or not, a read
    in the selected query's WHERE under Bool operations alone (so no check
    waits for a bound value) or as a non-null Int on HAVING's one line on a
    sum, and with bind-safe WHERE literals of the query or a plain upstream.
    Both families emit the pinned SQL under the form's policy, pairwise
    distinct per family and PostgreSQL's unchanged, with no binding
    obligation; every reader accepts it, the pure boundary's re-rendering
    included where its schema reaches (no header parameter)."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    checked, outcome = probe.grouping_world(
        tmp_path, target, probe.G5_FORMS[form], probe.G5_FORM_POLICY[form]
    )
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G5_FORM_SQL[form, target]
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    ).canonical_bytes
    assert observed is None or pure.rendering_refusal(observed) is None
    document = json.loads(serialize_project_sql_emission(outcome))
    assert {
        column["label"] for column in document["columns"] if not column["nullable"]
    } == G5_NON_NULL[form]
    assert document.get("binding_obligations", []) == []
    texts = [probe.G5_FORM_SQL[name, target] for name in probe.G5_FORMS]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("spelling", sorted(probe.G5_SPELLINGS))
def test_mysql_g5_spellings_emit_their_form_sql(tmp_path, spelling, target):
    """A read qualified by the source's name, a parameter read in
    parentheses, a `group by:` block, an identity `def`, an ORDER BY on one
    line or with `asc` written out, a `table` declaration, an imported
    source and an unread relation alias and window emit the form's bytes on
    both targets."""
    form, body = probe.G5_SPELLINGS[spelling]
    _, outcome = probe.grouping_world(
        tmp_path, target, body, probe.G5_FORM_POLICY[form]
    )
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G5_FORM_SQL[form, target]


@pytest.mark.parametrize(
    "name", sorted({*probe.G5_FORMS, *probe.G5_CELLS, *probe.G5_SPELLINGS})
)
def test_mysql_g5_sql_is_main_max_sql_but_the_guard(tmp_path, name):
    """B: each G5 body's MySQL SQL, `let` stages kept, is main's MySQL SQL
    of the same body under the same header and policy with every `sum(x)`
    written `max(x)`, each such MAX(x) (or main's whole cast of it) S02's
    guarded SUM of x, and its placeholders (owner, physical type, server
    index) and fixed values are that body's in the same order: every
    placeholder, WHERE, HAVING, ORDER BY, LIMIT, key and other aggregate is
    main's verified MySQL emission. The bodies the law opens beyond the
    forms (main's refused header parameters, G1's to G4's bind-safe
    controls, G4's R10 and an unread parameter over an aggregating upstream)
    keep it too."""
    import re

    if name in probe.G5_SPELLINGS:
        form, body = probe.G5_SPELLINGS[name]
        policy = probe.G5_FORM_POLICY[form]
    else:
        body = {**probe.G5_FORMS, **probe.G5_CELLS}[name]
        policy = probe.G5_FORM_POLICY.get(name) or probe.G5_CELL_POLICIES.get(
            name, "preserve_literals"
        )
    files = body if type(body) is dict else {"main.pietto": body}
    _, maxima = probe.grouping_world(
        tmp_path / "max",
        "mysql",
        {path: text.replace("sum(", "max(") for path, text in files.items()},
        policy,
    )
    _, outcome = probe.grouping_world(tmp_path / "sum", "mysql", body, policy)
    probe.numeric_readers_accept(outcome)
    assert maxima.artifact is not None and outcome.artifact is not None
    summed = [
        found == "sum"
        for text in files.values()
        for found in re.findall(r"= (sum|max)\(", text)
    ]
    assert outcome.artifact.rendered.sql.decode() == _guarded_maxima(
        maxima.artifact.rendered.sql.decode(), summed
    )
    sums, maxes = (
        json.loads(serialize_project_sql_emission(item)) for item in (outcome, maxima)
    )
    for key in ("parameters", "fixed_values", "binding_obligations"):
        assert sums.get(key) == maxes.get(key)
    assert [
        {field: use[field] for field in use if field != "range"}
        for use in sums.get("parameter_uses", [])
    ] == [
        {field: use[field] for field in use if field != "range"}
        for use in maxes.get("parameter_uses", [])
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_mysql_g5_unread_parameters_add_nothing(tmp_path, target):
    """B0: a parameter that nothing reads puts nothing in the SQL; U1 and U2
    without their headers, and G4's A1 without N7's unread `lo`, emit the
    same bytes on both targets."""
    import re

    for form in ("U1", "U2"):
        _, bare = probe.grouping_world(
            tmp_path / form,
            target,
            re.sub(r"^query result\(.*?\):", "query result:", probe.G5_FORMS[form]),
            probe.G5_FORM_POLICY[form],
        )
        assert bare.artifact is not None
        assert bare.artifact.rendered.sql.decode() == probe.G5_FORM_SQL[form, target]
    _, unread = probe.grouping_world(
        tmp_path / "unread", target, probe.G5_CELLS["unread_over_aggregate"]
    )
    assert unread.artifact is not None
    assert unread.artifact.rendered.sql.decode() == (probe.G4_FORM_SQL["A1", target])


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G5_REFUSALS))
def test_mysql_g5_neighbours_keep_main_refusal(tmp_path, shape, policy):
    """Rule two (D77.37): a statement the G5 law matches beside another
    blocker (a label too long, a Date, Decimal, UUID or Timestamp parameter,
    which main reports alone) and one outside it (a bind-safe literal in a conditional
    sum or an aggregating upstream's WHERE, a Float parameter read, a
    parameter under a minus or `Int` arithmetic in the WHERE, which leaves a
    binding obligation, a parameter or a placeholder beside a HAVING line
    that reads no sum, a nullable parameter on a HAVING line, a parameter
    that a HAVING line on a sum compares by `==`, `!=`, `<` or `<=`: lead
    ruling R-witness) keep main's blockers, object for object, under each
    policy they are refused with; PostgreSQL emits each but the long label
    as main does."""
    if policy not in probe.G5_REFUSAL_POLICIES.get(shape, (policy,)):
        pytest.skip("refused under its own policy only")
    body = probe.G5_REFUSALS[shape]
    _, outcome = probe.grouping_world(tmp_path / "mysql", "mysql", body, policy)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == probe.G5_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.grouping_world(tmp_path / "postgres", "postgres", body, policy)
    if shape in probe.G5_POSTGRES_BLOCKERS:
        assert _numeric_blockers(postgres) == probe.G5_POSTGRES_BLOCKERS[shape]
    else:
        assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G5_SMALLINT_REFUSALS))
def test_mysql_g5_keeps_smallint_reads_in_s02_cell(tmp_path, shape, policy):
    """MC G5 over G1 to G3 (lead ruling of 2026-11-21, S02-SMALLINT): S02's
    own SMALLINT GROUP BY key, and a `count` or `min` of a SMALLINT field,
    stay in S02's cell as main takes it, so a header parameter, read or
    not, and a bind-safe `?` beside one keep main's blockers, object for
    object, under each policy that refuses them; PostgreSQL emits each."""
    if policy not in probe.G5_SMALLINT_POLICIES.get(shape, (policy,)):
        pytest.skip("refused under its own policy only")
    body, blockers = probe.G5_SMALLINT_REFUSALS[shape]
    _, outcome = probe.division_world(tmp_path / "mysql", "mysql", body, policy)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == blockers
    _, postgres = probe.division_world(tmp_path / "postgres", "postgres", body, policy)
    assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize("shape", sorted(probe.G5_SEMANTIC_REFUSALS))
def test_mysql_g5_shapes_outside_semantics_reach_no_emission_law(tmp_path, shape):
    """A parameter as a grouped SELECT item or a GROUP BY key, a `limit` of
    one and a summed `let` that reads one fail before semantics with
    PIE-S2355 (R8's body with `max` verifies); a Float parameter compared
    with an Int field, a query that reads a query with parameters, and a
    parameter under a minus or `Int` arithmetic on a HAVING line fail
    semantics with their PIE-B1003 lists; each on both targets alike, so
    G5's law never sees them."""
    body = probe.G5_SEMANTIC_REFUSALS[shape]
    for target in ("postgres", "mysql"):
        try:
            _, outcome = probe.grouping_world(tmp_path / target, target, body)
        except ValueError as error:
            assert str(error) == "probe source failed parsing"
            parsed = check_project_parse_only(tmp_path / target)
            found = [diagnostic.code for diagnostic in parsed.diagnostics]
        else:
            assert outcome.status == "BLOCKED" and outcome.artifact is None
            found = _numeric_blockers(outcome)
        assert found == probe.G5_SEMANTIC_REFUSAL_BLOCKERS[shape]
    if shape == "R8":
        _, maxima = probe.grouping_world(
            tmp_path / "max", "mysql", body.replace("sum(", "max(")
        )
        assert maxima.status == "VERIFIED", maxima.blockers


_GROUP_FORMS = {
    **{
        name: form
        for name, form in float_cells.KEY_FORMS.items()
        if form[0][0] == "group"
    },
    **{
        name: form
        for name, form in float_cells.KEY_SAME_CLASS.items()
        if form[0][0] == "group"
    },
}


@pytest.mark.parametrize("name", sorted(_GROUP_FORMS))
def test_mysql_float_group_key_cells_emit_the_postgresql_statement(tmp_path, name):
    """Phase77 S07 (D77.39): each paired GROUP BY form of the S07 native
    qualification and each program of its class emits on MySQL the
    PostgreSQL statement in MySQL spelling, whose text with identifiers
    erased is its probe's; emission, compiled replay and the pure boundary
    each derive its cell, and the live verifier and pure accept it."""
    float_cells.assert_key_cell_emits(tmp_path, *_GROUP_FORMS[name])


@pytest.mark.parametrize(
    "name",
    sorted(
        n
        for n in float_cells.KEY_REFUSED
        if n.startswith(("group", "count_distinct", "distribution_group"))
    ),
)
def test_other_mysql_float_group_keys_keep_their_refusal(tmp_path, name):
    """Every other MySQL Float GROUP BY keeps main's blockers (wide keys and
    others outside the cells, other clauses, inputs and select lists), and
    the program emits on PostgreSQL."""
    float_cells.assert_key_refused(tmp_path, name)


def test_a_refused_mysql_float_group_key_cell_reports_main_blockers(
    tmp_path, monkeypatch
):
    """D77.37: the GROUP BY cell form group.h refused by another check (an
    unreviewed target release, a later correspondence check) reports
    main's whole blocker list."""
    float_cells.assert_refused_key_cell_reports_main(tmp_path, "group.h", monkeypatch)


@pytest.mark.parametrize(
    "name",
    (
        "group.hwh",
        "group_mixed_nullability",
        "group_width_255",
        "group_other_aggregate",
        "group_where",
        "group_select_reordered",
        "group_key_unselected",
        "group_upstream",
    ),
)
def test_a_mysql_float_group_key_forged_past_its_cell_is_refused(
    tmp_path, monkeypatch, name
):
    """Emission forced to admit a GROUP BY outside every cell: the live
    verifier refuses it from its plan and the pure boundary from the
    document."""
    float_cells.assert_forged_key_refused(
        tmp_path, float_cells.KEY_REFUSED[name][0], monkeypatch
    )


def _reversed_keys(records):
    (stage,) = (r for r in records if r["ref"][0] == "aggregate_stage")
    stage["fields"]["keys"].reverse()


def test_a_tampered_mysql_float_group_key_document_is_refused(tmp_path):
    """group.hh with its GROUP BY keys reversed against its select list."""
    float_cells.assert_tampered_key_refused(tmp_path, "group.hh", _reversed_keys)


# Phase77 S03: MySQL conditional, JOIN and two-level sums in their forms.
def _s03_blockers(outcome):
    return [
        (
            blocker["code"],
            blocker["subject"]["detail"],
            blocker["location"]["line"],
            blocker["location"]["column"],
        )
        for blocker in json.loads(serialize_project_sql_emission(outcome))["blockers"]
    ]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.S03_REFUSALS))
def test_mysql_sums_outside_the_s03_forms_keep_main_refusal(tmp_path, shape, policy):
    """D77.24: every MySQL statement that is not, names aside, one of the
    nine paired forms, nor in the cells that MC G6 (G6_S03_CELLS) and MC G7
    (G7_CELLS) open, nor one of MC s03n's forms and spellings, keeps main's
    blockers, object for object, under both policies (rule two, D77.37): a
    test outside G7's atoms and a form beside a composed aggregate.
    PostgreSQL emits each as main does."""
    body = probe.S03_REFUSALS[shape]
    _, outcome = probe.s03_world(tmp_path / "mysql", "mysql", body, policy)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _s03_blockers(outcome) == probe.S03_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.s03_world(tmp_path / "postgres", "postgres", body, policy)
    assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize("spelling", sorted(probe.S03_SPELLINGS))
def test_mysql_s03_forms_are_paired_names_aliases_and_item_order_aside(
    tmp_path, spelling
):
    """A `table` declaration, an aliased key, SELECT items in another order
    and a subset of a form's items with one sum at least are the form, and
    every reader accepts them."""
    form, body = probe.S03_SPELLINGS[spelling]
    _, outcome = probe.s03_world(tmp_path, "mysql", body)
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert b"CASE WHEN SUM(" in outcome.artifact.rendered.sql


@pytest.mark.parametrize("form", sorted(probe.S03_FORMS))
def test_mysql_s03_forms_are_paired_under_other_names(tmp_path, form):
    """Relations and fields renamed one to one (their columns kept) are the
    same form: the SQL is the form's with the renamed output names."""
    _, outcome = probe.s03_world(
        tmp_path, "mysql", probe.S03_FORMS[form], names=probe.S03_RENAMES
    )
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    expected = probe.S03_FORM_SQL[form, "mysql"]
    for old, new in probe.S03_RENAMES.items():
        expected = expected.replace(" AS `%s`" % old, " AS `%s`" % new)
    assert outcome.artifact.rendered.sql.decode() == expected


def test_a_refused_s03_statement_reports_main_blockers_from_a_later_check(
    tmp_path, monkeypatch
):
    """A paired JOIN form that a check after emission_blockers refuses (here
    plan correspondence) is derived again with every cell shut and reports
    main's blocker (owner 2026-11-13T00:20Z)."""
    from pietto._project import project_sql_emission as emission

    monkeypatch.setattr(emission, "verify_row_query", lambda request, query: False)
    _, outcome = probe.s03_world(tmp_path, "mysql", probe.S03_FORMS["J2"])
    assert _s03_blockers(outcome) == [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 22, 9)
    ]


@pytest.mark.parametrize("value,premise", probe.WRONG_IDENTIFIER_CASES)
@pytest.mark.parametrize("form", ("C1", "C4", "J1", "s02_grouped"))
def test_a_mysql_sum_form_without_its_naming_premise_reports_it_after_main(
    tmp_path, monkeypatch, form, value, premise
):
    """A paired form or an S02 cell whose contract has no identifier_case or
    another value is refused: it reports main's blockers (D77.37), here its
    sum's refusal, and then the naming premise its named stages need, the
    one premise between it and its SQL."""
    build = probe.build_case
    monkeypatch.setattr(
        probe,
        "build_case",
        lambda directory, source, contract, *rest: build(
            directory, source, probe.with_identifier_case(contract, value), *rest
        ),
    )
    _, outcome = (
        probe.s03_world(tmp_path, "mysql", probe.S03_FORMS[form])
        if form in probe.S03_FORMS
        else probe.numeric_world(tmp_path, "mysql", probe.NUMERIC_CELLS[form])
    )
    assert [(b.code, b.detail) for b in outcome.blockers] == [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing"),
        premise,
    ]


def test_mysql_s03_forms_are_derived_once_per_aggregation(tmp_path, monkeypatch):
    """Emission asks whether its statement is a form once per aggregation,
    and compiled replay and the pure boundary derive it a fixed number of
    times per reading, with 1 conditional sum or 40 (P76-PERF-2): with the
    shared form law open, so that both are accepted, every reader reduces
    each statement as many times."""
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project import project_sql_emission_sum_forms as sum_forms

    forty = "".join(
        "        s%d = sum(o.amount for o in group if o.flag)\n" % index
        for index in range(40)
    )
    counts = []
    for index, body in enumerate(
        (
            probe.S03_FORMS["C1"],
            probe.S03_FORMS["C1"].replace(
                "        paid = sum(o.amount for o in group if o.flag)\n", forty
            ),
        )
    ):
        calls = {"emission": 0, "compiled": 0, "pure": 0}
        with monkeypatch.context() as patch:
            patch.setattr(sum_forms, "paired", lambda levels, preserve, *_: True)
            for name, module, attribute in (
                ("emission", rows, "mysql_s03_statement"),
                ("compiled", rows, "mysql_s03_compiled"),
                ("pure", pure, "_mysql_s03"),
            ):
                original = getattr(module, attribute)

                def counted(*arguments, _original=original, _name=name):
                    calls[_name] += 1
                    return _original(*arguments)

                patch.setattr(module, attribute, counted)
            _, outcome = probe.s03_world(tmp_path / str(index), "mysql", body)
            probe.numeric_readers_accept(outcome)
        counts.append(calls)
    assert counts[0] == counts[1]
    assert all(counts[0].values())


_S03_WIDER_BLOCKERS = {
    "t2_wider_orders": [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", 24, 9),
    ],
}


@pytest.mark.parametrize("shape", sorted(probe.S03_WIDER))
def test_mysql_s03_join_forms_need_the_paired_tables_whole(tmp_path, shape):
    """A JOIN form's SQL carries every field of both sources, so a source
    with one more field is no form and T2's keeps main's blockers, also in
    plain verification, the live template, compiled replay and the pure
    boundary when forged past emission (J2's is MC G6's, T1's over one more
    nullable BIGINT field of `orders` MC s03n's T-4); a conditional form
    reads only its own fields and stays one."""
    from pietto._project import project_compiled_schema as wire
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_execution_template import (
        BindingError,
        prepare_live_template,
    )
    from pietto._project.project_sql_emission_verification import (
        verify_project_sql_emission,
    )

    form, extra = probe.S03_WIDER[shape]
    body = probe.S03_FORMS[form]
    _, outcome = probe.s03_world(tmp_path / "mysql", "mysql", body, extra=extra)
    if shape not in _S03_WIDER_BLOCKERS:
        probe.numeric_readers_accept(outcome)
        return
    assert _s03_blockers(outcome) == _S03_WIDER_BLOCKERS[shape]
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(rows, "mysql_s03_statement", lambda request: True)
        _, forged = probe.s03_world(tmp_path / "forged", "mysql", body, extra=extra)
        artifact = forged.artifact
        assert artifact is not None
        built = build_compiled(artifact)
        observed = portable.export_emission_observation(artifact, artifact.request)
    assert not verify_project_sql_emission(artifact, artifact.request).verified
    with pytest.raises(BindingError, match="^BINDING_ARTIFACT$"):
        prepare_live_template(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    with pytest.raises(wire.CompiledError, match="^COMPILED_AGGREGATE_ARGUMENT$"):
        emit_compiled(loaded, ())
    assert observed.canonical_bytes is not None
    refused = pure.parse_emission_observation(observed.canonical_bytes)
    assert (refused.status, refused.detail) == (
        pure.Status.INVALID_RELATION,
        "sum result",
    )


# MC G6 (JOIN extension): the public nullability of each form's columns: a
# GROUP BY key of a non-null field of an input no outer JOIN NULL-extends,
# and a count.
G6_NON_NULL = {
    "K1": {"id"},
    "K2": set(),
    "K3": {"id", "m"},
    "K4": {"city"},
    "K5": {"id"},
    "K6": {"city", "region", "r"},
    "K7": {"id"},
    "K8": set(),
    "O1": {"region"},
    "O2": {"id", "m"},
    "O3": set(),
    "C1": {"city"},
    "C2": {"customer"},
    "Y1": {"order_id", "r"},
    "Y2": {"units", "d"},
    "M1": {"customer", "region"},
    "M2": set(),
}


# The result columns each G8 form declares non-null on both targets: a
# non-null key or field carried up, and each count (the G8 list's
# non_null).
G8_NON_NULL = {
    "D1": {"g"},
    "D2": {"k"},
    "D3": {"m"},
    "D4": set(),
    "D5": {"m"},
    "D6": {"k", "r"},
    "D7": {"tag", "m"},
    "D8": {"m"},
    "S1": {"customer_id"},
    "S2": {"customers"},
    "S3": {"n"},
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(probe.G6_FORMS))
def test_mysql_g6_forms_emit_the_guarded_sum(tmp_path, form, target):
    """MC G6: a MySQL project emits S02's guarded SUM over the rows of one
    or more INNER, LEFT or RIGHT JOINs of sources of its module, each `on` a
    conjunction of linking Int equalities and, outside a RIGHT JOIN, `>` or
    `>=` literal comparisons of a non-null Int field of the joined input,
    in G2's cell otherwise. Both families emit the pinned SQL, pairwise
    distinct per family and PostgreSQL's unchanged; every reader accepts it,
    the pure boundary's re-rendering included."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    checked, outcome = probe.join_world(tmp_path, target, probe.G6_FORMS[form])
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G6_FORM_SQL[form, target]
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    ).canonical_bytes
    assert observed is not None and pure.rendering_refusal(observed) is None
    document = json.loads(serialize_project_sql_emission(outcome))
    assert {
        column["label"] for column in document["columns"] if not column["nullable"]
    } == G6_NON_NULL[form]
    texts = [probe.G6_FORM_SQL[name, target] for name in probe.G6_FORMS]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(probe.G8_FORMS))
def test_mysql_g8_forms_emit_the_guarded_sum_at_every_level(tmp_path, form, target):
    """MC G8: a MySQL project whose definitions form a chain of levels,
    three or more over a source or two or more over the style page's
    per-order level, emits S02's guarded SUM for every `sum` at every
    level. Both families emit the pinned SQL, pairwise distinct per family
    and PostgreSQL's unchanged; every reader accepts it, the pure boundary's
    re-rendering included."""
    import _pietto_sql_emission_portable as portable
    import _pietto_sql_emission_pure_boundary as pure

    checked, outcome = probe.levels_world(tmp_path, target, probe.G8_FORMS[form])
    assert checked.verified
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G8_FORM_SQL[form, target]
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    ).canonical_bytes
    assert observed is not None and pure.rendering_refusal(observed) is None
    document = json.loads(serialize_project_sql_emission(outcome))
    assert {
        column["label"] for column in document["columns"] if not column["nullable"]
    } == G8_NON_NULL[form]
    texts = [probe.G8_FORM_SQL[name, target] for name in probe.G8_FORMS]
    assert len(set(texts)) == len(texts)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("spelling", sorted(probe.G6_SPELLINGS))
def test_mysql_g6_spellings_emit_their_form_sql(tmp_path, spelling, target):
    """A relationship call read as its body, parentheses around the `on` or
    a sum, bare field reads where one input has the field, a `table`
    declaration and a `group by:` block emit the form's bytes."""
    form, body = probe.G6_SPELLINGS[spelling]
    _, outcome = probe.join_world(tmp_path, target, body)
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G6_FORM_SQL[form, target]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("spelling", sorted(probe.G8_SPELLINGS))
def test_mysql_g8_spellings_emit_their_form_sql(tmp_path, spelling, target):
    """`table` for `query` at a level, the style page's one-line `select`, a
    read qualified by the source's name in a bottom level, an identity
    `def` and parentheses around a `sum` argument emit the form's bytes."""
    form, body = probe.G8_SPELLINGS[spelling]
    _, outcome = probe.levels_world(tmp_path, target, body)
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == probe.G8_FORM_SQL[form, target]


# MC G6 and G8 replace each summed maximum, cast or not, by S02's guarded SUM
# as G2's _guarded_maxima above does.
def _g6_bodies():
    """Each G6 body with its world: the forms, their spellings, the cells
    the law opens and S03's JOIN neighbours it opens, and S03's J1-J3
    (`S03_` before its name)."""
    bodies = {
        **{name: (probe.join_world, {}, body) for name, body in probe.G6_FORMS.items()},
        **{
            name: (probe.join_world, {}, body)
            for name, (_, body) in probe.G6_SPELLINGS.items()
        },
        **{name: (probe.join_world, {}, body) for name, body in probe.G6_CELLS.items()},
        **{
            name: (probe.s03_world, {"extra": extra}, body)
            for name, (body, extra) in probe.G6_S03_CELLS.items()
        },
    }
    for form in ("J1", "J2", "J3"):
        bodies["S03_" + form] = (probe.s03_world, {}, probe.S03_FORMS[form])
    return bodies


_G6_BODIES = _g6_bodies()


@pytest.mark.parametrize("name", sorted(_G6_BODIES))
def test_mysql_g6_sql_is_main_max_sql_but_the_guard(tmp_path, name):
    """B: each G6 body's MySQL SQL, `let` stages kept, is main's MySQL SQL of
    the same body with every `sum(x)` written `max(x)`, the whole text main
    emits for each such `max`, MAX(x) or CAST(MAX(x) AS SIGNED), S02's
    guarded SUM of x and no guard inside a CAST: so the JOIN stage, every
    key, every other aggregate, WHERE and GROUP BY are main's verified MySQL
    emission, and a combination the forms do not run (a self-join, three
    JOINs, more `on` conjuncts) rests on the forms' parts. S03's J1-J3 keep
    S03_FORM_SQL's bytes; every reader accepts each body, and PostgreSQL
    emits it as main does."""
    import re

    world, keywords, body = _G6_BODIES[name]
    _, maxima = world(
        tmp_path / "max", "mysql", body.replace("sum(", "max("), **keywords
    )
    _, outcome = world(tmp_path / "sum", "mysql", body, **keywords)
    probe.numeric_readers_accept(outcome)
    assert maxima.artifact is not None and outcome.artifact is not None
    sql = outcome.artifact.rendered.sql.decode()
    summed = [found == "sum" for found in re.findall(r"= \(?(sum|max)\(", body)]
    assert sql == _guarded_maxima(maxima.artifact.rendered.sql.decode(), summed)
    assert "CAST(CASE WHEN SUM(" not in sql
    if name.startswith("S03_"):
        assert sql == probe.S03_FORM_SQL[name[4:], "mysql"]
    _, postgres = world(tmp_path / "postgres", "postgres", body, **keywords)
    assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G6_REFUSALS))
def test_mysql_g6_neighbours_keep_main_refusal(tmp_path, shape, policy):
    """Rule two (D77.37): a statement the G6 law matches beside another
    blocker (a label too long, a sum outside every cell, HAVING, ORDER BY,
    LIMIT, DISTINCT, a header parameter, a bind-safe `?`, a relation alias,
    read by FROM or not, an unread window, an imported source, a FROM that
    reads a query, S02's own SMALLINT key, a `min` of a SMALLINT field) and
    one outside it (a FULL or CROSS JOIN, a JOIN of a query or `table`
    or with no `let`, a JOIN upstream, an `on` that links nothing, holds a
    Text equality, a NULL test or a `def` call, or a literal comparison of
    another operator, order, field, input or JOIN kind, a negative literal,
    a `def` argument or relationship body's literal) keep main's blockers,
    object for object, under each policy they are refused with;
    a sum of the "one" side of a JOIN and a CROSS JOIN sum with no key are
    refused before emission on both targets, and PostgreSQL emits every
    other but the long label as main does."""
    if policy not in probe.G6_REFUSAL_POLICIES.get(shape, (policy,)):
        pytest.skip("refused under its own policy only")
    body = probe.G6_REFUSALS[shape]
    world = probe.G6_REFUSAL_WORLDS.get(shape, {})
    _, outcome = probe.join_world(tmp_path / "mysql", "mysql", body, policy, **world)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == probe.G6_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.join_world(
        tmp_path / "postgres", "postgres", body, policy, **world
    )
    if shape in probe.G6_POSTGRES_BLOCKERS:
        assert _numeric_blockers(postgres) == probe.G6_POSTGRES_BLOCKERS[shape]
    else:
        assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize(
    "name", sorted({*probe.G8_FORMS, *probe.G8_SPELLINGS, *probe.G8_CELLS})
)
def test_mysql_g8_sql_is_main_max_sql_but_the_guard(tmp_path, name):
    """B2: each G8 body's MySQL SQL, `let` stages kept, is main's MySQL SQL
    of the same body with every `sum(x)` at every level written `max(x)`,
    each such maximum, cast where main casts it, wholly replaced by S02's
    guarded SUM of x, which no cast wraps: so every level's keys, other
    aggregates, plain items, `let` stages, FROM, the per-order JOIN, WHERE
    and GROUP BY are main's verified MySQL emission, and a chain the forms
    do not run (five levels, a bottom `let`, a `min` of a min column)
    rests on the forms' parts. It is also main's PostgreSQL SQL of the
    body in MySQL's spelling with each sum S02's guarded SUM."""
    import re

    body: Any = (
        probe.G8_SPELLINGS.get(name, (None, None))[1]
        or {
            **probe.G8_FORMS,
            **probe.G8_CELLS,
        }[name]
    )
    text = body if type(body) is str else body["main.pietto"]
    maximum: Any = text.replace("sum(", "max(")
    if type(body) is dict:
        maximum = dict(body, **{"main.pietto": maximum})
    _, maxima = probe.levels_world(tmp_path / "max", "mysql", maximum)
    _, outcome = probe.levels_world(tmp_path / "sum", "mysql", body)
    probe.numeric_readers_accept(outcome)
    assert maxima.artifact is not None and outcome.artifact is not None
    summed = [found == "sum" for found in re.findall(r"= (sum|max)\(", text)]
    sql = outcome.artifact.rendered.sql.decode()
    assert sql == _guarded_maxima(maxima.artifact.rendered.sql.decode(), summed)
    assert "CAST(CASE WHEN SUM(" not in sql
    _, postgres = probe.levels_world(tmp_path / "postgres", "postgres", body)
    assert postgres.artifact is not None, postgres.blockers
    assert sql == _mysql_spelling(postgres.artifact.rendered.sql.decode(), text)


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("shape", sorted(probe.G8_REFUSALS))
def test_mysql_g8_neighbours_keep_main_refusal(tmp_path, shape, policy):
    """Rule two (D77.37): a chain the G8 law matches beside another blocker
    (a label too long, `sum(a + b)`, HAVING, ORDER BY, LIMIT, DISTINCT, a
    header parameter, a bind-safe `?`, a relation alias, an unread or read
    window, a read qualified by a definition's name above the bottom, an
    imported definition or source, a JOIN above the bottom, a conditional
    sum at any level) and one outside it
    (a WHERE above the lowest sum level, a lower sum that reaches no sum, a
    sum, count, min or `avg` column as a key, a min column summed, a sum or
    count column counted or under `max`, a count column averaged, an `avg`
    column counted or under `max`, a `Float` sum, a min column of a BIGINT
    field counted, a min or max column of
    an INT field, MySQL's cast `my_signed_int` at every level above it,
    under `min`, `max` or `avg`, a min column of a `Float` or `Timestamp`
    field under `min`, a lower aggregate level without a key or a sum, a
    per-order level or second level that is not T1's, a plain one among
    them, another JOIN kind, other `Order` carriers, a `count` or `min` of
    a SMALLINT field) keep main's blockers, object for object, under
    each policy they are refused with: only the lowest level's sums, never
    a higher level's that main does not list. (Two levels over a source are
    MC G4's upstream, which G4 opens as its `sum_upstream` cell.)
    PostgreSQL emits each but the long label as main does."""
    if policy not in probe.G8_REFUSAL_POLICIES.get(shape, (policy,)):
        pytest.skip("refused under its own policy only")
    body = probe.G8_REFUSALS[shape]
    world = probe.G8_REFUSAL_WORLDS.get(shape, {})
    _, outcome = probe.levels_world(tmp_path / "mysql", "mysql", body, policy, **world)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == probe.G8_REFUSAL_BLOCKERS[shape]
    _, postgres = probe.levels_world(
        tmp_path / "postgres", "postgres", body, policy, **world
    )
    if shape in probe.G8_POSTGRES_BLOCKERS:
        assert _numeric_blockers(postgres) == probe.G8_POSTGRES_BLOCKERS[shape]
    else:
        assert postgres.status == "VERIFIED", postgres.blockers


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_conditional_sum_over_join_rows_is_refused_at_check(tmp_path, capsys, target):
    """G6's X3: project checking refuses a conditional sum over JOIN rows
    on both targets before any emission law, so no family opens it."""
    from pietto import cli

    body, expected = probe.G6_CHECK_REFUSAL
    with pytest.raises(ValueError, match="failed parsing"):
        probe.join_world(tmp_path, target, body)
    capsys.readouterr()
    assert cli.main(["check", "--project", str(tmp_path), "--format", "json"]) == 1
    assert [
        (item["code"], item["location"]["line"], item["location"]["column"])
        for item in json.loads(capsys.readouterr().out)["diagnostics"]
    ] == [expected]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_mysql_g8_leaves_the_s03_route_as_main(tmp_path, policy):
    """Over S03's sources G8 opens nothing: T1 and T2 keep main's bytes,
    which are also their bodies' with each sum written `max` and each such
    MAX the guarded SUM (B3). S03's two-level neighbours are MC s03n's
    (its forms, spellings and rule two below) or MC G4's
    (`ctl_t_plain_first_level`, its G4_ORDERS_CELLS P1)."""
    import re

    for form in ("T1", "T2"):
        body = probe.S03_FORMS[form]
        _, outcome = probe.s03_world(tmp_path / form, "mysql", body, policy)
        _, maxima = probe.s03_world(
            tmp_path / (form + "max"), "mysql", body.replace("sum(", "max("), policy
        )
        assert outcome.artifact is not None and maxima.artifact is not None
        sql = outcome.artifact.rendered.sql.decode()
        assert sql == probe.S03_FORM_SQL[form, "mysql"]
        summed = [found == "sum" for found in re.findall(r"= (sum|max)\(", body)]
        assert sql == _guarded_maxima(maxima.artifact.rendered.sql.decode(), summed)


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize(
    ("header", "shape"),
    (
        ("    order_id: Int\n", "    order_id: Int\n    item_key = unique(id)\n"),
        (
            "    order_key = unique(id)\n",
            "    order_key = unique(id)\n    pair_key = unique(customer_id, amount)\n",
        ),
        ("    order_key = unique(id)\n", "    order_key = unique(customer_id)\n"),
        ("    order_key = unique(id)\n", "    order_key = unique(id, amount)\n"),
    ),
)
def test_mysql_g8_per_order_level_needs_the_style_pages_keys(
    tmp_path, monkeypatch, header, shape, policy
):
    """The per-order level reads the style page's `Order`, whose one key is
    `unique(id)`, and `Item`, which has none: another key on either, or
    `Order`'s one key over other fields, keeps main's blockers under each
    policy, though the SQL would be S1's (the pure document holds no key,
    so emission and compiled replay refuse it)."""
    monkeypatch.setattr(
        probe, "LEVELS_HEADER", probe.LEVELS_HEADER.replace(header, shape)
    )
    _, outcome = probe.levels_world(
        tmp_path / "mysql", "mysql", probe.G8_FORMS["S1"], policy
    )
    line = 36 + shape.count("\n") - header.count("\n")
    assert _numeric_blockers(outcome) == [
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", line, 9),
        ("PIE-B1004", "sum_int_aggregate_range_proof_missing", line + 1, 9),
    ]
    _, postgres = probe.levels_world(
        tmp_path / "postgres", "postgres", probe.G8_FORMS["S1"], policy
    )
    assert postgres.status == "VERIFIED", postgres.blockers


# MC s03n: S03's neighbours that MC G7 and G8 hand on (the s03n list's Law C
# and Law T). The result columns each form declares non-null on both
# targets: the INT key and, in Law C's forms, the conditional sum (the
# list's non_null).
_S03N_LAW_C = (
    "ctl_c_order_by",
    "r3_order_by",
    "ctl_c_upstream",
    "r7_upstream",
    "c1_having",
)
_S03N_NON_NULL = {
    **{form: {"customer", "paid"} for form in _S03N_LAW_C},
    **{
        form: {"customer"}
        for form in (
            "ctl_t_second_where",
            "t1_upstream_subset",
            "t1_wider_orders",
            "t2_upstream_subset",
            "t2_extra_upstream_count",
        )
    },
    "ctl_t_third_level": set(),
    "t1_third_level": set(),
}


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(probe.S03N_FORMS))
def test_mysql_s03n_forms_emit_the_guarded_sum(tmp_path, form, target, policy):
    """MC s03n: a MySQL project emits each of the list's twelve forms, Law
    C's conditional sum with ORDER BY of its key, a plain upstream or the
    HAVING line `paid >= 0` over the bases each names, and Law T's chains
    over S03's T1 or T2 per-order bottom with `where lines > 0` in T1's
    second level, a key left unselected, an unread `count()`, one more
    field of `orders` or a scalar third level, every sum S02's guarded SUM
    and a conditional one inside S03's COALESCE, with the SQL the list
    predicts under both literal policies, but T-1's form, whose `0` is a
    bind-safe `?` under bind_safe_literals: there MySQL keeps main's
    blockers (the list's control, rule two below) and PostgreSQL binds it
    (S03N_BOUND_SQL). PostgreSQL emits main's SQL, the twelve texts are
    pairwise distinct per target, every reader accepts each (on PostgreSQL
    under preserve_literals, as the G6 to G8 form tests), the INT key's
    column is my_int (pg_int4) and every sum's my_signed_int (pg_int8), and
    only the key and Law C's sum are non-null (the list's Interface)."""
    bound = form in probe.S03N_BOUND_SQL and policy == "bind_safe_literals"
    if bound and target == "mysql":
        pytest.skip("the list's control: rule two pins its refusal")
    checked, outcome = probe.s03n_world(
        tmp_path, target, probe.S03N_FORMS[form], policy
    )
    assert checked.verified
    if target == "mysql" or policy == "preserve_literals":
        probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None
    assert outcome.artifact.rendered.sql.decode() == (
        probe.S03N_BOUND_SQL[form] if bound else probe.S03N_FORM_SQL[form, target]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert {
        column["label"] for column in document["columns"] if not column["nullable"]
    } == _S03N_NON_NULL[form]
    key, total = (
        ("my_int", "my_signed_int") if target == "mysql" else ("pg_int4", "pg_int8")
    )
    assert {
        column["label"]: column["representation"]["storage"]["kind"]
        for column in document["columns"]
    } == {
        column["label"]: key if column["label"] == "customer" else total
        for column in document["columns"]
    }
    texts = [probe.S03N_FORM_SQL[name, target] for name in probe.S03N_FORMS]
    assert len(set(texts)) == len(texts)


def test_the_s03n_world_builds_only_the_forms(tmp_path):
    """s03n_world builds a form's body with its own extra fields alone, and
    refuses any other body."""
    for body in (probe.S03_FORMS["C1"], probe.S03N_FORMS["ctl_c_order_by"] + "\n"):
        with pytest.raises(ValueError, match="^not the body of an s03n form$"):
            probe.s03n_world(tmp_path, "mysql", body)
    _, wider = probe.s03n_world(tmp_path, "mysql", probe.S03N_FORMS["t1_wider_orders"])
    assert wider.artifact is not None
    assert [
        field.name
        for source in wider.artifact.request.sources
        for field in source.fields
        if json.loads(source.selector)["name"] == "orders"
    ][-1] == "note"


def _s03n_mysql_spelling(postgres):
    """main's PostgreSQL SQL of an s03n form in MySQL's spelling, each
    checked bigint SUM S02's guarded SUM of its argument and each
    conditional one S03's COALESCE of the guard (the list's BM)."""
    import re

    def guarded(argument):
        return "".join(
            (argument if position else "") + text
            for position, (_, text) in enumerate(grouping.MYSQL_SUM_GUARD)
        )

    sql = re.sub(
        r"COALESCE\(CAST\(SUM\(CASE WHEN (.+?) THEN CAST\((\S+) AS"
        r" pg_catalog\.int8\) END\) AS pg_catalog\.int8\), 0\)",
        lambda found: (
            "COALESCE(%s, 0)"
            % guarded(f"CASE WHEN {found.group(1)} THEN {found.group(2)} END")
        ),
        postgres,
    )
    sql = re.sub(
        r"CAST\(SUM\(CAST\((\S+) AS pg_catalog\.int8\)\) AS pg_catalog\.int8\)",
        lambda found: guarded(found.group(1)),
        sql,
    )
    return (
        sql.replace("AS pg_catalog.int8)", "AS SIGNED)")
        .replace('"', "`")
        .replace("`public`.", "`phase66`.")
    )


def _conditional_maxima(sql, postgres):
    """MySQL SQL whose one MAX(arg) is S03's guarded conditional SUM of arg,
    `COALESCE(` the guard over `CASE WHEN t THEN arg END` `, 0)`, ``t`` the
    test that ``postgres`` (main's PostgreSQL SQL of the conditional
    statement) writes, in MySQL's spelling (the s03n list's BC)."""
    import re

    (test,) = re.findall(
        r"COALESCE\(CAST\(SUM\(CASE WHEN (.+?) THEN CAST\(\S+ AS pg_catalog\.int8\)",
        postgres,
    )
    test = test.replace('"', "`").replace("AS pg_catalog.int8)", "AS SIGNED)")
    (argument,) = re.findall(r"MAX\(([^()]+)\)", sql)
    return sql.replace(
        f"MAX({argument})",
        "COALESCE(%s, 0)"
        % "".join(
            (f"CASE WHEN {test} THEN {argument} END" if position else "") + text
            for position, (_, text) in enumerate(grouping.MYSQL_SUM_GUARD)
        ),
    )


@pytest.mark.parametrize("form", sorted(probe.S03N_FORMS))
def test_mysql_s03n_sql_is_main_max_sql_but_the_guard(tmp_path, form):
    """BC and BT: each s03n form's MySQL SQL is main's MySQL SQL of its B
    body, Law C's conditional sum written `max` of its argument with that
    MAX S03's guarded conditional SUM under the form's test in MySQL's
    spelling, or Law T's every `sum(x)` at every level written `max(x)`
    with each such MAX S02's guarded SUM of x, which no cast wraps: so the
    upstream stage, the JOIN stage, ORDER BY's stage and clause, the HAVING
    line's WHERE over the aggregation stage and every key and other
    aggregate are main's verified MySQL emission. It is also main's
    PostgreSQL SQL in MySQL's spelling with each sum guarded, under both
    literal policies alike (T-1's form under preserve_literals, the one
    policy that opens it)."""
    import re

    body = probe.S03N_FORMS[form]
    extra = probe.S03N_EXTRA.get(form)
    maximum = (
        re.sub(
            r"sum\(o\.(\w+) for o in group if [^\n]*\)$", r"max(\1)", body, flags=re.M
        )
        if form in _S03N_LAW_C
        else body.replace("sum(", "max(")
    )
    texts = set()
    policies = ("preserve_literals", "bind_safe_literals")
    for policy in policies[:1] if form in probe.S03N_BOUND_SQL else policies:
        _, maxima = probe.s03_world(
            tmp_path / ("max-" + policy), "mysql", maximum, policy, extra=extra
        )
        _, postgres = probe.s03n_world(
            tmp_path / ("postgres-" + policy), "postgres", body, policy
        )
        assert maxima.artifact is not None and postgres.artifact is not None
        sql = maxima.artifact.rendered.sql.decode()
        main = postgres.artifact.rendered.sql.decode()
        texts.add(
            _conditional_maxima(sql, main)
            if form in _S03N_LAW_C
            else _guarded_maxima(
                sql, [found == "sum" for found in re.findall(r"= (sum|max)\(", body)]
            )
        )
        assert probe.S03N_FORM_SQL[form, "mysql"] == _s03n_mysql_spelling(main)
    assert texts == {probe.S03N_FORM_SQL[form, "mysql"]}
    assert "CAST(CASE WHEN SUM(" not in probe.S03N_FORM_SQL[form, "mysql"]


@pytest.mark.parametrize("form", sorted(probe.S03N_FORMS))
def test_mysql_s03n_forms_are_open_under_other_names(tmp_path, form):
    """Relations and fields renamed one to one (S03_RENAMES, their columns
    kept) leave each form open: the SQL is the form's with the renamed
    output names."""
    _, outcome = probe.s03_world(
        tmp_path,
        "mysql",
        probe.S03N_FORMS[form],
        names=probe.S03_RENAMES,
        extra=probe.S03N_EXTRA.get(form),
    )
    assert outcome.artifact is not None, outcome.blockers
    expected = probe.S03N_FORM_SQL[form, "mysql"]
    for old, new in probe.S03_RENAMES.items():
        expected = expected.replace(" AS `%s`" % old, " AS `%s`" % new)
    assert outcome.artifact.rendered.sql.decode() == expected


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize("spelling", sorted(probe.S03N_SPELLINGS))
def test_mysql_s03n_spellings_emit_their_base_sql(tmp_path, spelling, target, policy):
    """C-2's relation alias over C1 and over G7's R6's base and its imported
    source over C1 and over G7's T1, C-1's other ORDER BY spelling of each
    C-1 form, C-4's `having paid >= 0` on one line, T-1's `where:` block
    of `lines > 0`, a call of a `def` with no parameters in place of R3's
    `3`, C-4's `0` and T-1's `0` (`lines > zero()`), the imported source
    over G7's T1 beside an imported such `def` in place of its `3`, G8's
    P4 (T-5 under another output label) and a sampled spelling of each
    group of the s03n paragraph's classes I, L, S and N emit the bytes of
    the statement each spells, on both targets under both policies, and
    every reader accepts them: the alias and the import leave the base's
    compiled records and pure document (D77.24; S03_ALIASES says so of the
    first two), so compiled replay replays the base's bytes. On MySQL under
    bind_safe_literals T-1's spellings keep the control's blockers,
    positions aside."""
    body, base, labels = probe.S03N_SPELLINGS[spelling]
    assert body != base
    _, outcome = probe.s03_world(tmp_path / "spelling", target, body, policy)
    _, direct = probe.s03_world(tmp_path / "base", target, base, policy)
    if (target, policy) == ("mysql", "bind_safe_literals") and base in [
        probe.S03N_FORMS[form] for form in probe.S03N_BOUND_SQL
    ]:
        assert outcome.artifact is None and direct.artifact is None
        assert [blocker[:2] for blocker in _numeric_blockers(outcome)] == [
            blocker[:2] for blocker in _numeric_blockers(direct)
        ]
        return
    if target == "mysql":
        probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None and direct.artifact is not None
    expected = direct.artifact.rendered.sql.decode()
    quote = '"' if target == "postgres" else "`"
    for old, new in labels.items():
        expected = expected.replace(
            f" AS {quote}{old}{quote}", f" AS {quote}{new}{quote}"
        )
    assert outcome.artifact.rendered.sql.decode() == expected
    if spelling in probe.S03_ALIASES:
        assert expected == probe.S03_FORM_SQL[probe.S03_ALIASES[spelling], target]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("spelling", sorted(probe.S03N_RESPELLINGS))
def test_mysql_s03n_respellings_emit_main_sql_guarded(
    tmp_path, monkeypatch, spelling, policy
):
    """The s03n spellings that S03N_SPELLINGS cannot state: SELECT item
    order of a Law C and a Law T form, the selected `result` written
    before its upstream, `o.nn > 3` for R3's `o.id > 3` and the header's
    `mysql.table('orders')` emit on MySQL, under both policies, main's
    PostgreSQL SQL of the same body in MySQL's spelling with each sum
    guarded (the list's BM), and every reader accepts them. Only the
    header's quoting emits the form's own bytes."""
    body, form, header = probe.S03N_RESPELLINGS[spelling]
    written = probe.S03_HEADER
    for old, new in header:
        assert written.count(old) == 1
        written = written.replace(old, new)
    monkeypatch.setattr(probe, "S03_HEADER", written)
    extra = probe.S03N_EXTRA.get(form)
    _, outcome = probe.s03_world(tmp_path / "mysql", "mysql", body, policy, extra=extra)
    _, postgres = probe.s03_world(
        tmp_path / "postgres", "postgres", body, policy, extra=extra
    )
    probe.numeric_readers_accept(outcome)
    assert outcome.artifact is not None and postgres.artifact is not None
    sql = outcome.artifact.rendered.sql.decode()
    assert sql == _s03n_mysql_spelling(postgres.artifact.rendered.sql.decode())
    assert (sql == probe.S03N_FORM_SQL[form, "mysql"]) is bool(header)


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("cell", sorted(probe.S03N_REFUSALS))
def test_mysql_s03n_rule_two_keeps_main_refusal(tmp_path, cell, policy):
    """Rule two (D77.37): the control, T-1's form under bind_safe_literals,
    whose `0` is then a bind-safe `?` (G5's), keeps main's blockers, and so
    does each Z cell at the edges of Law C and Law T, object for object,
    under both policies: a long label beside the law
    (Z1, Z2); ORDER BY `desc`, by the sum, by two keys, of a key that is no
    INT, with `asc` written out, of a parenthesized key or with LIMIT (Z4,
    Z10, Z18, Z26, Z28, Z29, Z30, Z31); a test's literal other than 3
    (Z27); an upstream with a WHERE, another item, a GROUP BY or of another
    module (Z5, Z15, Z33, Z34, Z35), or selecting the key or the summed
    field under another name (Z71, Z72); an import under another name or
    re-exported (Z36, Z37); a HAVING line with another operator, on the
    key, with another literal or a header parameter, or a second line (Z24,
    Z25, Z17, Z32, Z11); LIMIT and DISTINCT (Z19, Z20); each item over a
    base it does not name, another test, C3, C4 or another of G7's forms
    (Z8, Z12 to Z14, Z16, Z38 to Z44, Z70); an item subset or a count in
    place of the selected key (Z45, Z76); two of Law C's items (Z46 to Z52);
    T-4's extra field read, of another type, one more or before `flag`
    (Z53 to Z56); two of T-2 to T-6, a third level over T-2, T-3 or T-4
    among them (Z21, Z22, Z57 to Z60); a fourth level, a keyed third level,
    one that skips or repeats a sum or adds an aggregate (Z6, Z23, Z61,
    Z62, Z74, Z75); a first grouping key outside the JOIN (Z73); a read of
    T-3's count (Z7); an ORDER BY above the JOIN bottom (Z63); a
    second-level item subset or `max`, T1's bottom with a `count()`, the
    count of the ON field, an INNER JOIN or no `amount` (Z64 to Z69); and
    at T-1's edges a WHERE in T1's second level that reads a field column
    (Z9), one in T2's that reads its sum column or T-3's count (Z77, Z78),
    another operator or literal, the literal first, a parenthesized test, a
    second test or a header parameter (Z79 to Z84), T-1 with HAVING, ORDER
    BY, T-2, T-4 or T-6 (Z85 to Z89) and a WHERE in T-6's third level or in
    the per-order bottom (Z90, Z91); and at T-1's `0`, C-4's `0` and Law
    C's `3` a parenthesized call, a call with an argument, a parenthesized
    literal or column and a call in place of the test, and T-1's column
    read as `per_order.lines` (Z92 to Z107); and the other spellings that
    only the plan's readers refuse: C-4's HAVING line in parentheses (Z108,
    Z109), a parenthesized operand of TEST's `and`, `or` or `not` (Z110 to
    Z115), a key or item read through its source's name (Z116 to Z118),
    G7's C1 spellings under C-1 (Z119 to Z124), a space or line break
    inside a sum's parentheses (Z125 to Z127), and under T-1 a
    parenthesized ON comparison or operand (Z128 to Z130) or a per-order
    key read without its JOIN input's name (Z131); and the other shapes
    that only the plan's readers refuse: C-2's alias unread beside a
    direct FROM, beside a second alias, of an alias or parenthesized (Z132
    to Z138), C-2's import beside another import item or statement, of
    `orders` under another name, of `items` or of a shape, or beside an
    alias, read or not (Z139 to Z145), an unread `let` at C-3's or T-1's
    levels (Z146 to Z149), an alias or an import read by C-3's upstream
    (Z150, Z151), an alias of the level below (Z152, Z153), T-1 over
    imported sources (Z154) and an unread window (Z155, Z156); and C-2
    over a G7 statement that the list does not name (Z157, Z158), C-3's
    upstream as a `let up:` block (Z159), under T-1 a space, line break
    or trailing comma at a plain sum's parentheses, a per-order item
    without its JOIN input's name or a sum argument read through its
    relation's name (Z160 to Z164), a key or item read through C-2's
    alias's name (Z165, Z166), T-3's `count()` with a space (Z167, Z168),
    C-2's import beside an imported relationship, in a second statement
    or item (Z169, Z170), and at Law C's `3` an operation over Int
    literals, such as `1 + 2` (Z171). Only the lowest level's sums are
    listed, never a higher level's that main does not list.
    PostgreSQL emits each but the two long labels as main does."""
    if policy not in probe.S03N_REFUSAL_POLICIES.get(cell, (policy,)):
        pytest.skip("refused under its own policy only")
    body = probe.S03N_REFUSALS[cell]
    extra = probe.S03N_REFUSAL_EXTRA.get(cell)
    _, outcome = probe.s03_world(tmp_path / "mysql", "mysql", body, policy, extra=extra)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _numeric_blockers(outcome) == probe.S03N_REFUSAL_BLOCKERS[cell]
    _, postgres = probe.s03_world(
        tmp_path / "postgres", "postgres", body, policy, extra=extra
    )
    if cell in probe.S03N_POSTGRES_BLOCKERS:
        assert _numeric_blockers(postgres) == probe.S03N_POSTGRES_BLOCKERS[cell]
    else:
        assert postgres.status == "VERIFIED", postgres.blockers
