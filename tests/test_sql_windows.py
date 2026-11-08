"""Admitted window emission: families, frames, named uses, modifiers and QUALIFY.

Every artifact below is produced by the installed emission path from an ordinary
authored project. A verdict is taken from the published status and the emitted
bytes, never from a production builder deciding that its own output is correct.
"""

import json
import re
import tempfile
from pathlib import Path

import pytest

import _pietto_sql_emission as probe
from _pietto_sql_window import select_body
from pietto._project.project_sql_emission import serialize_project_sql_emission

TARGETS = ("postgres", "mysql")
# R14 admits exactly these identities; R15 owns the three frame-sensitive ones.
FAMILIES = {
    "row_number": ("row_number()", "ROW_NUMBER()"),
    "rank": ("rank()", "RANK()"),
    "dense_rank": ("dense_rank()", "DENSE_RANK()"),
    "percent_rank": ("percent_rank()", "PERCENT_RANK()"),
    "cume_dist": ("cume_dist()", "CUME_DIST()"),
    "ntile": ("ntile(2)", "NTILE(2)"),
    "lag": ("lag(id, 1, 0)", "LAG("),
    "lead": ("lead(id, 1)", "LEAD("),
    "first_value": ("first_value(id)", "FIRST_VALUE("),
    "last_value": ("last_value(id)", "LAST_VALUE("),
    "nth_value": ("nth_value(id, 2)", "NTH_VALUE("),
}
FRAMES = {
    "rows_unbounded": (
        "rows between unbounded preceding and current row",
        "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW",
    ),
    "rows_offset": (
        "rows between 1 preceding and current row",
        "ROWS BETWEEN 1 PRECEDING AND CURRENT ROW",
    ),
    "rows_following": (
        "rows between 1 preceding and 1 following",
        "ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING",
    ),
    "range_unbounded": (
        "range between unbounded preceding and current row",
        "RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW",
    ),
    "range_offset": (
        "range between 1 preceding and current row",
        "RANGE BETWEEN 1 PRECEDING AND CURRENT ROW",
    ),
}
POSTGRES_ONLY_FRAMES = {
    "groups_current": (
        "groups between 1 preceding and current row exclude current row",
        "GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW EXCLUDE CURRENT ROW",
    ),
    "groups_ties": (
        "groups between 1 preceding and current row exclude ties",
        "GROUPS BETWEEN 1 PRECEDING AND CURRENT ROW EXCLUDE TIES",
    ),
}


def emit(target, body, *, range_safe=False):
    """One published window fixture through the installed pipeline."""
    item = probe.parameterized_fixture(target, body, protocol=False)
    if range_safe:
        # RANGE offsets need physical headroom, not merely a narrow declared domain.
        contract = json.loads(item["contract"])
        contract["sources"][0]["fields"][0]["representation"] = {
            "storage": {"kind": "pg_int4" if target == "postgres" else "my_int"},
            "domain": {"kind": "int_range", "min": "0", "max": "1"},
            "nullable": False,
        }
        item["contract"] = probe.encoded(contract).decode()
    with tempfile.TemporaryDirectory() as directory:
        _, outcome = probe.build_case(
            Path(directory) / "case", item["source"], item["contract"], item["policy"]
        )
    return outcome


def sql_of(outcome) -> str:
    assert outcome.artifact is not None
    return outcome.artifact.rendered.sql.decode()


def blockers(outcome) -> list[str]:
    return [item.detail for item in (outcome.blockers or ())]


def public(outcome) -> dict:
    return json.loads(serialize_project_sql_emission(outcome).decode())


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("family", sorted(FAMILIES))
def test_every_admitted_family_emits_its_own_native_call(target, family):
    """R14: each retained identity lowers to its own spelling over its own input."""
    call, spelling = FAMILIES[family]
    outcome = emit(target, select_body(call))
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert spelling in sql
    # The OVER specification is present and carries this window's own ordering.
    assert re.search(r"\)\s*OVER\s*\(ORDER BY ", sql)
    # No other admitted identity leaks in. The comparison is on the whole call
    # token, because RANK( is a substring of DENSE_RANK( and PERCENT_RANK(.
    emitted = set(re.findall(r"(?<![A-Z_])([A-Z_]+)\(", sql))
    admitted = {spelling.rstrip("(").rstrip(")").split("(")[0]}
    assert admitted <= emitted
    for other, (_, other_spelling) in FAMILIES.items():
        name = other_spelling.rstrip("(").rstrip(")").split("(")[0]
        if name not in admitted:
            assert name not in emitted


@pytest.mark.parametrize("target", TARGETS)
def test_partition_and_order_bind_established_pre_window_ports(target):
    """R14: partition and order read their exact pre-window input columns."""
    outcome = emit(target, select_body("row_number()", partition="flag"))
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert "PARTITION BY " in sql
    assert re.search(r"PARTITION BY .*? ORDER BY ", sql)
    assert " ASC" in sql


GROUPED_WINDOWS_FIRST = """table result:
    from rows
    group by:
        text
    select:
        w = rank() window(order by total desc)
        text
        total = max(id)
        n = row_number() window(order by text)
        c = count()
"""
GROUPED_WINDOWS_LAST = """table result:
    from rows
    group by:
        text
    select:
        text
        total = max(id)
        c = count()
        w = rank() window(order by total desc)
        n = row_number() window(order by text)
"""
GROUPED_WINDOWS_FIRST_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1", "c2") AS (SELECT "s0"."text `""é" AS "c0", '
        'MAX("s0"."order.id") AS "c1", COUNT(*) AS "c2" '
        'FROM "public"."phase66 source é" AS "s0" GROUP BY "s0"."text `""é"), '
        '"p1" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "t1"."c0" AS "c0", '
        '"t1"."c1" AS "c1", "t1"."c2" AS "c2", '
        'RANK() OVER (ORDER BY "t1"."c1" DESC) AS "c3", '
        'ROW_NUMBER() OVER (ORDER BY "t1"."c0" ASC) AS "c4" FROM "p0" AS "t1") '
        'SELECT "t2"."c3" AS "w", "t2"."c0" AS "text", "t2"."c1" AS "total", '
        '"t2"."c4" AS "n", "t2"."c2" AS "c" FROM "p1" AS "t2"'
    ),
    "mysql": (
        'WITH `p0` (`c0`, `c1`, `c2`) AS (SELECT `s0`.`text ``"é` AS `c0`, '
        "MAX(`s0`.`order.id`) AS `c1`, COUNT(*) AS `c2` "
        'FROM `phase66`.`phase66 source é` AS `s0` GROUP BY `s0`.`text ``"é`), '
        "`p1` (`c0`, `c1`, `c2`, `c3`, `c4`) AS (SELECT `t1`.`c0` AS `c0`, "
        "`t1`.`c1` AS `c1`, `t1`.`c2` AS `c2`, "
        "RANK() OVER (ORDER BY `t1`.`c1` DESC) AS `c3`, "
        "ROW_NUMBER() OVER (ORDER BY `t1`.`c0` ASC) AS `c4` FROM `p0` AS `t1`) "
        "SELECT `t2`.`c3` AS `w`, `t2`.`c0` AS `text`, `t2`.`c1` AS `total`, "
        "`t2`.`c4` AS `n`, `t2`.`c2` AS `c` FROM `p1` AS `t2`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_grouped_windows_selected_before_aggregates_keep_their_stage_columns(target):
    """Selection order moves only the final projection, never a stage column."""
    first = emit(target, GROUPED_WINDOWS_FIRST)
    last = emit(target, GROUPED_WINDOWS_LAST)
    assert first.status == "VERIFIED", blockers(first)
    assert last.status == "VERIFIED", blockers(last)
    sql = sql_of(first)
    assert sql == GROUPED_WINDOWS_FIRST_SQL[target]
    assert [column["label"] for column in public(first)["columns"]] == [
        "w",
        "text",
        "total",
        "n",
        "c",
    ]
    stages = sql.rsplit(") SELECT ", 1)[0]
    assert sql_of(last).rsplit(") SELECT ", 1)[0] == stages


# A window key may name a `let` computed from input fields, also through a
# `def` call and in QUALIFY: each key reads that let's own pre-window column.
COMPUTED_KEYS = """def far(v: Int) -> Bool:
    return v > 1

query result:
    from rows
    let off = id != 1
    let f = far(id)
    let ordered = window(partition by off order by f desc)
    select:
        record_id = id
        n = row_number() window(partition by off order by f desc, id)
        r = rank() window ordered
    qualify row_number() window(partition by off order by id) <= 2
"""
COMPUTED_KEYS_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "s0"."order.id" '
        'AS "c0", "s0"."flag value" AS "c1", "s0"."text `""é" AS "c2", "s0"."amount '
        'value" AS "c3", "s0"."ratio value" AS "c4", ("s0"."order.id" <> CAST(1 AS '
        'pg_catalog.int8)) AS "c5" FROM "public"."phase66 source é" AS "s0"), "p1" '
        '("c0", "c1", "c2", "c3", "c4", "c5", "c6") AS (SELECT "t1"."c0" AS "c0", '
        '"t1"."c1" AS "c1", "t1"."c2" AS "c2", "t1"."c3" AS "c3", "t1"."c4" AS "c4", '
        '"t1"."c5" AS "c5", ("t1"."c0" > CAST(1 AS pg_catalog.int8)) AS "c6" FROM '
        '"p0" AS "t1"), "p2" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", '
        '"c9") AS (SELECT "t2"."c0" AS "c0", "t2"."c1" AS "c1", "t2"."c2" AS "c2", '
        '"t2"."c3" AS "c3", "t2"."c4" AS "c4", "t2"."c5" AS "c5", "t2"."c6" AS "c6", '
        'ROW_NUMBER() OVER (PARTITION BY "t2"."c5" ORDER BY "t2"."c6" DESC, '
        '"t2"."c0" ASC) AS "c7", RANK() OVER "w0" AS "c8", ROW_NUMBER() OVER '
        '(PARTITION BY "t2"."c5" ORDER BY "t2"."c0" ASC) AS "c9" FROM "p1" AS "t2" '
        'WINDOW "w0" AS (PARTITION BY "t2"."c5" ORDER BY "t2"."c6" DESC)), "p3" '
        '("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9") AS (SELECT '
        '"t3"."c0" AS "c0", "t3"."c1" AS "c1", "t3"."c2" AS "c2", "t3"."c3" AS "c3", '
        '"t3"."c4" AS "c4", "t3"."c5" AS "c5", "t3"."c6" AS "c6", "t3"."c7" AS "c7", '
        '"t3"."c8" AS "c8", "t3"."c9" AS "c9" FROM "p2" AS "t3" WHERE ("t3"."c9" <= '
        'CAST(2 AS pg_catalog.int8))) SELECT "t4"."c0" AS "record_id", "t4"."c7" AS '
        '"n", "t4"."c8" AS "r" FROM "p3" AS "t4"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `s0`.`order.id` "
        'AS `c0`, `s0`.`flag value` AS `c1`, `s0`.`text ``"é` AS `c2`, `s0`.`amount '
        "value` AS `c3`, `s0`.`ratio value` AS `c4`, (`s0`.`order.id` <> CAST(1 AS "
        "SIGNED)) AS `c5` FROM `phase66`.`phase66 source é` AS `s0`), `p1` (`c0`, "
        "`c1`, `c2`, `c3`, `c4`, `c5`, `c6`) AS (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` "
        "AS `c1`, `t1`.`c2` AS `c2`, `t1`.`c3` AS `c3`, `t1`.`c4` AS `c4`, `t1`.`c5` "
        "AS `c5`, (`t1`.`c0` > CAST(1 AS SIGNED)) AS `c6` FROM `p0` AS `t1`), `p2` "
        "(`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`, `c8`, `c9`) AS (SELECT "
        "`t2`.`c0` AS `c0`, `t2`.`c1` AS `c1`, `t2`.`c2` AS `c2`, `t2`.`c3` AS `c3`, "
        "`t2`.`c4` AS `c4`, `t2`.`c5` AS `c5`, `t2`.`c6` AS `c6`, ROW_NUMBER() OVER "
        "(PARTITION BY `t2`.`c5` ORDER BY `t2`.`c6` DESC, `t2`.`c0` ASC) AS `c7`, "
        "RANK() OVER `w0` AS `c8`, ROW_NUMBER() OVER (PARTITION BY `t2`.`c5` ORDER "
        "BY `t2`.`c0` ASC) AS `c9` FROM `p1` AS `t2` WINDOW `w0` AS (PARTITION BY "
        "`t2`.`c5` ORDER BY `t2`.`c6` DESC)), `p3` (`c0`, `c1`, `c2`, `c3`, `c4`, "
        "`c5`, `c6`, `c7`, `c8`, `c9`) AS (SELECT `t3`.`c0` AS `c0`, `t3`.`c1` AS "
        "`c1`, `t3`.`c2` AS `c2`, `t3`.`c3` AS `c3`, `t3`.`c4` AS `c4`, `t3`.`c5` AS "
        "`c5`, `t3`.`c6` AS `c6`, `t3`.`c7` AS `c7`, `t3`.`c8` AS `c8`, `t3`.`c9` AS "
        "`c9` FROM `p2` AS `t3` WHERE (`t3`.`c9` <= CAST(2 AS SIGNED))) SELECT "
        "`t4`.`c0` AS `record_id`, `t4`.`c7` AS `n`, `t4`.`c8` AS `r` FROM `p3` AS "
        "`t4`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_window_keys_read_the_columns_of_computed_lets(target):
    """A PARTITION BY or ORDER BY key that names a computed `let` (a comparison,
    a `def` call) reads that let's stage column in a selected, a named and a
    QUALIFY window; the inline expression stays refused (PIE-S2103)."""
    outcome = emit(target, COMPUTED_KEYS)
    assert outcome.status == "VERIFIED", blockers(outcome)
    assert sql_of(outcome) == COMPUTED_KEYS_SQL[target]


@pytest.mark.parametrize(
    ("target", "collated"),
    (
        ("postgres", 'COLLATE "C" END) AS "c5"'),
        ("mysql", "COLLATE utf8mb4_0900_bin END) AS `c5`"),
    ),
)
def test_a_computed_text_window_key_reads_a_binary_collated_stage_column(
    target, collated
):
    """A Text `let` key computed from literals is a stage column whose
    literals carry the binary collation, so 'A' and 'a' stay two keys on both
    targets (single-file MySQL refuses such a key, PIE-B1000)."""
    outcome = emit(
        target,
        "query result:\n    from rows\n"
        '    let s = "A" if id > 2 else "a"\n    select:\n        record_id = id\n'
        "        t = row_number() window(partition by s order by id desc)\n"
        "        d = dense_rank() window(order by s)\n",
    )
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    quote = '"' if target == "postgres" else "`"
    assert collated in sql
    assert (
        "ROW_NUMBER() OVER (PARTITION BY {q}t1{q}.{q}c5{q} ORDER BY {q}t1{q}.{q}c0{q} "
        "DESC)".format(q=quote)
        in sql
    )
    assert "DENSE_RANK() OVER (ORDER BY {q}t1{q}.{q}c5{q} ASC)".format(q=quote) in sql


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_admitted_frames_emit_their_exact_unit_and_bounds(target, frame):
    """R15: an admitted frame is emitted exactly, never silently dropped."""
    authored, spelling = FRAMES[frame]
    outcome = emit(
        target,
        select_body("first_value(id)", frame=authored),
        range_safe=frame == "range_offset",
    )
    assert outcome.status == "VERIFIED", blockers(outcome)
    assert spelling in sql_of(outcome)


@pytest.mark.parametrize("frame", sorted(POSTGRES_ONLY_FRAMES))
def test_postgres_realizes_groups_and_exclude(frame):
    """R15: PostgreSQL emits the retained GROUPS frame and its exclusion."""
    authored, spelling = POSTGRES_ONLY_FRAMES[frame]
    outcome = emit("postgres", select_body("first_value(id)", frame=authored))
    assert outcome.status == "VERIFIED", blockers(outcome)
    assert spelling in sql_of(outcome)


@pytest.mark.parametrize("frame", sorted(POSTGRES_ONLY_FRAMES))
def test_mysql_blocks_groups_and_exclude_without_emulation(frame):
    """R15: MySQL keeps a typed blocker and is never given an emulation."""
    authored, _ = POSTGRES_ONLY_FRAMES[frame]
    outcome = emit("mysql", select_body("first_value(id)", frame=authored))
    assert outcome.status == "BLOCKED"
    assert blockers(outcome) == ["window_frame_groups_approved_non_support_on_mysql"]
    assert outcome.artifact is None


def test_mysql_still_emits_its_adjacent_supported_frames():
    """The MySQL GROUPS blocker is feature-specific, not a whole-window refusal."""
    for authored, spelling in FRAMES.values():
        outcome = emit(
            "mysql",
            select_body("first_value(id)", frame=authored),
            range_safe=authored.startswith("range "),
        )
        assert outcome.status == "VERIFIED", blockers(outcome)
        assert spelling in sql_of(outcome)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "modifier,detail",
    (
        ("ignore nulls", "window_ignore_nulls_approved_non_support_in_phase66"),
        ("from last", "window_from_last_approved_non_support_in_phase66"),
    ),
)
def test_non_supported_modifiers_keep_their_exact_blocker(target, modifier, detail):
    """R16: IGNORE NULLS and FROM LAST are never emulated and never erased."""
    call = "nth_value(id, 2)" if modifier == "from last" else "first_value(id)"
    outcome = emit(
        target,
        select_body(
            f"{call} {modifier}",
            frame="rows between unbounded preceding and current row",
        ),
    )
    assert outcome.status == "BLOCKED"
    assert blockers(outcome) == [detail]
    assert outcome.artifact is None


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("modifier", ("respect nulls", "from first"))
def test_identity_modifiers_are_omitted_rather_than_spelled(target, modifier):
    """R16: a reviewed identity omission emits no target syntax of its own."""
    call = "nth_value(id, 2)" if modifier == "from first" else "first_value(id)"
    outcome = emit(
        target,
        select_body(
            f"{call} {modifier}",
            frame="rows between unbounded preceding and current row",
        ),
    )
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert "RESPECT NULLS" not in sql and "FROM FIRST" not in sql
    assert "IGNORE NULLS" not in sql and "FROM LAST" not in sql


@pytest.mark.parametrize("target", TARGETS)
def test_offset_range_requires_its_exact_single_key_premise(target):
    """R15/C16: a second ORDER key makes an offset RANGE inadmissible."""
    outcome = emit(
        target,
        select_body(
            "last_value(id)",
            frame="range between 1 preceding and current row",
            order="id,flag",
        ),
    )
    assert outcome.status == "BLOCKED"
    assert blockers(outcome) == ["offset_range_requires_exactly_one_order_key"]
    # The same frame over the admitted single non-null Int key still emits.
    admitted = emit(
        target,
        select_body(
            "last_value(id)", frame="range between 1 preceding and current row"
        ),
        range_safe=True,
    )
    assert admitted.status == "VERIFIED", blockers(admitted)
    assert "RANGE BETWEEN 1 PRECEDING AND CURRENT ROW" in sql_of(admitted)


@pytest.mark.parametrize("target", TARGETS)
def test_full_width_range_key_with_narrow_declared_domain_is_rejected(target):
    """A configured 0..1 domain cannot prove endpoint safety for an Int64 key."""
    outcome = emit(
        target,
        select_body(
            "last_value(id)", frame="range between 1 preceding and current row"
        ),
    )
    assert outcome.status == "BLOCKED"
    assert blockers(outcome) == ["window_range_boundary_out_of_signed64_range"]


NAMED_BODY = """table result:
    from rows
    let named = window(order by id)
    select:
        id
        w = rank() window named
        w2 = dense_rank() window named
"""


@pytest.mark.parametrize("target", TARGETS)
def test_two_uses_of_one_named_declaration_share_one_generated_definition(target):
    """R14: a native WINDOW clause with a capture-safe generated symbol."""
    outcome = emit(target, NAMED_BODY)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    symbol = re.search(r"WINDOW [\"`](w\d+)[\"`] AS \(", sql)
    assert symbol is not None, sql
    name = symbol.group(1)
    assert name == "w0"
    # Both uses reference that one definition; neither is inlined.
    assert len(re.findall(rf"OVER [\"`]{name}[\"`]", sql)) == 2
    assert "RANK() OVER" in sql and "DENSE_RANK() OVER" in sql
    # The generated symbol is never an authored name.
    assert 'OVER "named"' not in sql and "OVER `named`" not in sql
    assert sql.count("WINDOW ") == 1


QUALIFY_SELECTED = """table result:
    from rows
    select:
        id
        w = row_number() window(order by id)
    qualify:
        w <= 2
"""
QUALIFY_HIDDEN = """table result:
    from rows
    select:
        id
    qualify:
        row_number() window(order by id) <= 2
"""
QUALIFY_BOTH = """table result:
    from rows
    select:
        id
        w = row_number() window(order by id)
    qualify:
        row_number() window(order by id) <= 3 and w <= 2
"""


@pytest.mark.parametrize("target", TARGETS)
def test_qualify_filters_outside_the_window_stage(target):
    """R17: QUALIFY consumes an established window port in an outer filter."""
    outcome = emit(target, QUALIFY_SELECTED)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    window = sql.index("ROW_NUMBER()")
    condition = sql.index(" WHERE ", window)
    # The predicate follows the window computation and never moves before it.
    assert condition > window
    assert sql.count("ROW_NUMBER()") == 1
    assert [column["label"] for column in public(outcome)["columns"]] == ["id", "w"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_hidden_window_never_reaches_the_public_schema(target):
    """R17/C12: a hidden result filters rows without becoming a result column."""
    outcome = emit(target, QUALIFY_HIDDEN)
    assert outcome.status == "VERIFIED", blockers(outcome)
    assert "ROW_NUMBER()" in sql_of(outcome)
    assert [column["label"] for column in public(outcome)["columns"]] == ["id"]


@pytest.mark.parametrize("target", TARGETS)
def test_a_selected_and_a_hidden_sibling_stay_two_computations(target):
    """R17: identity comes from retained references, never from equal SQL text."""
    outcome = emit(target, QUALIFY_BOTH)
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    # Two occurrences with identical spellings remain two computations.
    assert sql.count("ROW_NUMBER()") == 2
    assert [column["label"] for column in public(outcome)["columns"]] == ["id", "w"]


@pytest.mark.parametrize("target", TARGETS)
def test_public_artifact_publishes_window_identity(target):
    """R23: the published document carries this occurrence's retained identity."""
    document = public(emit(target, QUALIFY_SELECTED))
    assert document["format"] == "pietto.sql-emission.v1"
    windows = [
        column["correspondence"]["window_origin"]
        for column in document["columns"]
        if "window_origin" in column["correspondence"]
    ]
    assert len(windows) == 1
    origin = windows[0]
    assert origin["function"] == "row_number"
    assert origin["selected"] is True
    assert origin["role"] == "window_result"
    for key in ("window", "stage", "definition", "policy", "result", "inputs"):
        assert key in origin


@pytest.mark.parametrize("target", TARGETS)
def test_generated_requirements_cover_every_window_structure(target):
    """R23/R30: each generated window structure keeps its own original cause."""
    document = public(emit(target, select_body("row_number()", partition="flag")))
    generated = [
        item for item in document["requirements"] if item["denominator"] == "generated"
    ]
    kinds = {item["kind"] for item in generated}
    assert "window_computation" in kinds
    assert "window_specification" in kinds
    assert "window_partition_comparison" in kinds
    assert "window_order_comparison" in kinds
    rules = {item["kind"]: item["rule"] for item in generated}
    assert rules["window_computation"] == "R14"
    assert rules["window_specification"] == "R15"
    assert rules["window_partition_comparison"] == "R14"
    assert rules["window_order_comparison"] == "R14"


# Current S06 correction: the PG function signature, not Int/frame/result width.
STRUCTURAL_FUNCTIONS = ("ntile", "nth_value", "lag", "lead")


def structural_call(function, value):
    return f"ntile({value})" if function == "ntile" else f"{function}(id, {value})"


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("function", STRUCTURAL_FUNCTIONS)
@pytest.mark.parametrize("value", (0, 1, 2147483647, 2147483648, 9223372036854775807))
def test_structural_window_argument_target_boundary(target, function, value):
    outcome = emit(target, select_body(structural_call(function, value)))
    if value == 0 and function in ("ntile", "nth_value"):
        assert blockers(outcome) == [
            "semantic_result_unsuccessful",
            "active_output_unavailable",
        ]
    elif target == "postgres" and value > 2147483647:
        assert blockers(outcome) == [
            "postgres_window_structural_argument_out_of_int32_range"
        ]
        assert outcome.blockers[0].code == "PIE-B1002"
    else:
        assert outcome.status == "VERIFIED", blockers(outcome)
        assert str(value) in sql_of(outcome)
        return
    assert outcome.status == "BLOCKED" and outcome.artifact is None


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("function", STRUCTURAL_FUNCTIONS)
@pytest.mark.parametrize("value", ("-1", "True", "1.5"))
def test_structural_window_existing_invalid_values_stay_semantic_rejections(
    target, function, value
):
    outcome = emit(target, select_body(structural_call(function, value)))
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert blockers(outcome) == [
        "semantic_result_unsuccessful",
        "active_output_unavailable",
    ]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("function", ("lag", "lead"))
def test_navigation_omission_and_wide_value_default_are_not_structure_bounds(
    target, function
):
    for call in (f"{function}(id)", f"{function}(id, 1, 9007199254740993)"):
        outcome = emit(target, select_body(call))
        assert outcome.status == "VERIFIED", blockers(outcome)
        if "9007199254740993" in call:
            assert "9007199254740993" in sql_of(outcome)
        else:
            from pietto._project.project_sql_emission_ast import SQLRowQuery

            assert outcome.artifact is not None
            assert type(outcome.artifact.ast) is SQLRowQuery
            column = next(
                c
                for b in outcome.artifact.ast.bodies
                for c in b.columns
                if type(c).__name__ == "WindowColumn"
            )
            assert tuple(a.role for a in column.arguments) == ("value",)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("unit", ("rows", "range", "groups"))
def test_frame_offsets_above_int32_remain_the_existing_separate_domain(target, unit):
    outcome = emit(
        target,
        select_body(
            "first_value(id)",
            frame=f"{unit} between 2147483648 preceding and current row",
        ),
        range_safe=unit == "range",
    )
    if target == "mysql" and unit == "groups":
        assert blockers(outcome) == [
            "window_frame_groups_approved_non_support_on_mysql"
        ]
    else:
        assert outcome.status == "VERIFIED", blockers(outcome)
        assert "2147483648 PRECEDING" in sql_of(outcome)


@pytest.mark.parametrize(
    "body",
    (
        QUALIFY_HIDDEN.replace("row_number()", "lead(id, 2147483648)"),
        NAMED_BODY.replace("rank() window named", "ntile(2147483648) window named", 1),
        """table producer:
    from rows
    select:
        id
        w = nth_value(id, 2147483648) window(order by id)
table result:
    from producer
    select:
        id
""",
    ),
)
def test_hidden_named_and_carried_arguments_cannot_escape_target_check(body):
    outcome = emit("postgres", body)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert blockers(outcome) == [
        "postgres_window_structural_argument_out_of_int32_range"
    ]


@pytest.mark.parametrize("function", STRUCTURAL_FUNCTIONS)
@pytest.mark.parametrize("value", (2147483648, 9223372036854775807))
def test_independent_verifiers_reject_coherent_faulty_builder_arguments(
    tmp_path, monkeypatch, function, value
):
    from pietto._project import project_sql_emission as emission
    from pietto._project import project_sql_emission_windows as windowing
    from pietto._project import project_sql_emission_verification as verification
    from pietto._project import project_sql_emission_portable as portable
    from pietto._project import project_sql_emission_pure_boundary as pure
    from pietto._project.project_sql_emission_contract import (
        prepare_project_sql_emission,
    )
    from pietto._project.project_result_output import prepare_output

    item = probe.parameterized_fixture(
        "postgres", select_body(structural_call(function, value)), protocol=False
    )
    encoded = item["contract"].encode()
    checked, refused = probe.build_case(tmp_path, item["source"], encoded)
    assert checked.verified and refused.artifact is None
    request = prepare_project_sql_emission(checked, encoded)
    assert verification.prepared_current(request)
    # Simulate one coherently faulty constructor, without granting its output
    # verification authority. Native SQL, event ranges and argument facts are
    # rebuilt together, so a token-length/reference mismatch is not the oracle.
    with monkeypatch.context() as patch:
        patch.setattr(windowing, "I32_MAX", value)
        realization = emission.realize_rows(request)
        query = realization.query
        assert type(query) is emission.SQLRowQuery
        rendered = emission.render_row_sql(query)
        original, generated = emission.build_row_requirements(request, query)
        artifact = emission.EmissionArtifact(
            request,
            query,
            rendered,
            original,
            generated,
            request.plan.fixed_envelope.values,
            tuple(p.use for p in emission.row_parameter_leaves(query)),
        )
        assert not verification.verify_project_sql_emission(artifact, request).verified
    with pytest.raises(ValueError):
        prepare_output(artifact)
    assert (
        portable.export_emission_observation(artifact, request).status
        is portable.ObservationStatus.UNVERIFIED
    )
    # Test data export deliberately bypasses the public exporter refusal. The
    # pure consumer receives only bytes, and independently names the range defect.
    data = portable._Export(artifact, request).run()
    result = pure.parse_emission_observation(data)
    assert result.status is pure.Status.INVALID_RELATION
    assert result.detail == "postgres window structural argument range"
    document = json.loads(data)
    role = (
        "bucket"
        if function == "ntile"
        else "position"
        if function == "nth_value"
        else "offset"
    )
    for record in document["records"]:
        if record["ref"][0] == "window_argument" and record["fields"]["role"] == role:
            record["fields"]["role"] = "default"
    result = pure.parse_emission_observation(json.dumps(document))
    assert result.status is pure.Status.INVALID_RELATION
    assert result.detail == "postgres window structural argument roles"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_temporal_and_uuid_window_keys(tmp_path, target):
    """Timestamp and Date keys order a window; Timestamp, Date and UUID keys
    partition it by equality, as GROUP BY compares them. A UUID orders one by
    its unsigned big-endian bytes, and a RANGE offset needs a signed Int key."""
    checked, outcome = probe.temporal_case(
        tmp_path / "keys",
        target,
        "    from rows\n    select:\n        t = ts\n"
        "        r = row_number() window(partition by u, ts, d order by ts desc, d2)\n",
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    q = '"' if target == "postgres" else "`"

    def col(name):
        return f"{q}s0{q}.{q}{name}{q}"

    assert (
        f"ROW_NUMBER() OVER (PARTITION BY {col('u')}, {col('ts')}, {col('d')}"
        f" ORDER BY {col('ts')} DESC, {col('d2')} ASC)"
    ) in public["sql"]
    checked, outcome = probe.temporal_case(
        tmp_path / "uuid_order",
        target,
        "    from rows\n    select:\n"
        "        r = row_number() window(partition by d order by u desc, id)\n",
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    public = probe.decode_public(serialize_project_sql_emission(outcome))
    assert (
        f"ROW_NUMBER() OVER (PARTITION BY {col('d')}"
        f" ORDER BY {col('u')} DESC, {col('id')} ASC) AS {q}c6{q}"
    ) in public["sql"]
    checked, outcome = probe.temporal_case(
        tmp_path / "uuid_range",
        target,
        "    from rows\n    select:\n"
        "        r = first_value(id) window(order by u range between 1 preceding"
        " and current row)\n",
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    checked, outcome = probe.temporal_case(
        tmp_path / "range_offset",
        target,
        "    from rows\n    select:\n"
        "        r = first_value(id) window(order by ts range between 1 preceding"
        " and current row)\n",
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None


@pytest.mark.parametrize("target", TARGETS)
def test_window_distribution_results_and_floats_key_on_postgres_only(target):
    """L13: percent_rank and cume_dist results are finite Floats in [0, 1]; they
    compare with a literal (and in a chain). E6: on PostgreSQL they are also
    DISTINCT, GROUP BY and relation ORDER keys, and a Float is a window
    PARTITION and ORDER key, by Float equality and real-value order; MySQL
    keeps each refused."""
    q = '"' if target == "postgres" else "`"
    half, quarter = (
        ("CAST('0.5' AS pg_catalog.float8)", "CAST('0.25' AS pg_catalog.float8)")
        if target == "postgres"
        else ("CAST(0.5e0 AS DOUBLE)", "CAST(0.25e0 AS DOUBLE)")
    )
    for window, condition, spelling in (
        ("percent_rank", "p > 0.5", f"> {half}"),
        ("cume_dist", "p <= 0.5", f"<= {half}"),
        ("cume_dist", "0.25 <= p <= 0.5", f"BETWEEN {quarter} AND {half}"),
    ):
        outcome = emit(
            target,
            "query result:\n    from rows\n    select:\n        id\n"
            f"        p = {window}() window(order by id)\n"
            f"    qualify:\n        {condition}\n",
        )
        assert outcome.status == "VERIFIED", outcome.blockers
        public = probe.decode_public(serialize_project_sql_emission(outcome))
        assert f"WHERE ({q}t1{q}.{q}c5{q} {spelling}))" in public["sql"]
    table = (
        "table w:\n    from rows\n    select:\n"
        "        p = percent_rank() window(order by id)\n"
    )
    for body, detail, line in (
        (
            "    select distinct:\n        p\n",
            "distinct_field_comparison_domain_unsupported",
            15,
        ),
        (
            "    group by:\n        p\n    select:\n        p\n        n = count()\n",
            "group_key_type_outside_reviewed_comparison_domain",
            15,
        ),
        (
            "    select:\n        p\n    order by:\n        p\n",
            "order_comparison_domain_unsupported",
            17,
        ),
    ):
        outcome = emit(target, table + "query result:\n    from w\n" + body)
        if target == "postgres":
            assert outcome.status == "VERIFIED", outcome.blockers
            probe.decode_public(serialize_project_sql_emission(outcome))
            continue
        assert outcome.status == "BLOCKED" and outcome.diagnostics == ()
        public = probe.decode_public(serialize_project_sql_emission(outcome))
        assert [
            (b["code"], b["subject"]["detail"], b["location"]["line"])
            for b in public["blockers"]
        ] == [("PIE-B1003", detail, line)]
    for spec, detail, over in (
        (
            "partition by ratio order by id",
            "window_partition_comparison_domain_unsupported",
            'OVER (PARTITION BY "s0"."ratio value" ORDER BY "s0"."order.id" ASC)',
        ),
        (
            "order by ratio",
            "window_order_comparison_domain_unsupported",
            'OVER (ORDER BY "s0"."ratio value" ASC)',
        ),
    ):
        outcome = emit(
            target,
            "query result:\n    from rows\n    select:\n"
            f"        n = row_number() window({spec})\n",
        )
        if target == "postgres":
            assert outcome.status == "VERIFIED", outcome.blockers
            assert (
                over
                in probe.decode_public(serialize_project_sql_emission(outcome))["sql"]
            )
            continue
        assert outcome.status == "BLOCKED"
        assert [(b.code, b.detail) for b in outcome.blockers] == [("PIE-B1002", detail)]


# An aggregate over a window keeps R13's argument law and casts over R15's
# frame: PostgreSQL SUM(Int) accumulates int8 and narrows by a checked CAST,
# AVG(Int) reads binary64, and count() is COUNT(*). MySQL keeps them refused
# until its real-database differential.
_COLUMN = r'"[^"]+"\."[^"]+"'
AGGREGATE_WINDOWS = {
    "sum": ("sum(id)", rf"CAST\(SUM\(CAST\({_COLUMN} AS pg_catalog\.int8\)\) OVER \("),
    "count": ("count(id)", rf"[ (]COUNT\({_COLUMN}\) OVER \("),
    "count_rows": ("count()", r"COUNT\(\*\) OVER \("),
    "avg": ("avg(id)", rf"AVG\(CAST\({_COLUMN} AS pg_catalog\.float8\)\) OVER \("),
    "min": ("min(id)", rf"MIN\({_COLUMN}\) OVER \("),
    "max": ("max(id)", rf"MAX\({_COLUMN}\) OVER \("),
}
AGGREGATE_WINDOW_FORMS = {
    "partition_only": (
        "table result:\n    from rows\n    select:\n        id\n"
        "        t = sum(id) window(partition by flag)\n",
        rf"SUM\(CAST\({_COLUMN} AS pg_catalog\.int8\)\) OVER \(PARTITION BY {_COLUMN} RANGE ",
    ),
    "rows_frame": (
        select_body("sum(id)", frame="rows between 1 preceding and current row"),
        r"ROWS BETWEEN 1 PRECEDING AND CURRENT ROW\) AS pg_catalog\.int8\)",
    ),
    "grouped": (
        "table result:\n    from rows\n    group by:\n        flag\n    select:\n"
        "        flag\n        total = sum(id)\n"
        "        running = sum(total) window(order by flag)\n",
        rf" GROUP BY .*CAST\(SUM\(CAST\({_COLUMN} AS pg_catalog\.int8\)\) OVER \(ORDER BY ",
    ),
    "qualify_hidden": (
        "table result:\n    from rows\n    select:\n        id\n"
        "    qualify:\n        count(id) window(order by id) > 1\n",
        rf"COUNT\({_COLUMN}\) OVER .* WHERE \({_COLUMN} > CAST\(1 AS pg_catalog\.int8\)\)",
    ),
    "qualify_selected": (
        "table result:\n    from rows\n    select:\n        id\n"
        "        n = count() window(partition by flag)\n    qualify:\n        n > 1\n",
        rf"COUNT\(\*\) OVER .* WHERE \({_COLUMN} > CAST\(1 AS pg_catalog\.int8\)\)",
    ),
    # A hidden window reads a `let` name bound to a field, as a selected one.
    "qualify_hidden_let": (
        "query result:\n    from rows\n    let v = id\n    select:\n"
        "        record_id = id\n"
        "    qualify:\n        sum(v) window(order by id) > 1\n",
        rf"SUM\(CAST\({_COLUMN} AS pg_catalog\.int8\)\) OVER \(ORDER BY {_COLUMN} ASC",
    ),
    "joined": (
        "query result:\n    from rows\n    let other = rows\n"
        "    inner join other on rows.id == other.id\n"
        "    select:\n        id = rows.id\n"
        "        total = sum(other.id) window(partition by rows.flag order by rows.id)\n",
        rf" INNER JOIN .*CAST\(SUM\(CAST\({_COLUMN} AS pg_catalog\.int8\)\) OVER \(PARTITION ",
    ),
    # A key may name a computed `let`, selected and hidden, as for any window.
    "computed_let_key": (
        "query result:\n    from rows\n    let off = id > 2\n    select:\n"
        "        record_id = id\n"
        "        t = sum(id) window(partition by off order by id)\n",
        rf"SUM\(CAST\({_COLUMN} AS pg_catalog\.int8\)\) OVER \(PARTITION BY "
        rf"{_COLUMN} ORDER BY {_COLUMN} ASC RANGE ",
    ),
    "computed_let_key_hidden": (
        "query result:\n    from rows\n    let off = id > 2\n    select:\n"
        "        record_id = id\n"
        "    qualify:\n        count(id) window(partition by off) > 1\n",
        rf"COUNT\({_COLUMN}\) OVER \(PARTITION BY {_COLUMN} RANGE ",
    ),
}


def _observed(outcome, edit=None) -> str:
    """The private emission observation of a VERIFIED artifact, after an
    optional edit of its decoded document, as the independent pure consumer
    decodes it."""
    from pietto._project import project_sql_emission_portable as portable
    from pietto._project import project_sql_emission_pure_boundary as pure

    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    )
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    data = observed.canonical_bytes
    if edit is not None:
        document = json.loads(data)
        edit(document)
        data = (
            json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n"
        ).encode()
    return pure.parse_emission_observation(data).status.value


CHECKED = "target_checked_signed64_narrowing"


def _flip_window_evidence(document) -> None:
    (requirement,) = (
        row["fields"]
        for row in document["records"]
        if row["ref"][0] == "generated_requirement"
        and row["fields"]["kind"] == "window_computation"
    )
    requirement["evidence"] = [] if requirement["evidence"] else [CHECKED]


@pytest.mark.parametrize("aggregate", sorted(AGGREGATE_WINDOWS))
def test_postgres_emits_each_aggregate_window_with_its_aggregate_casts(aggregate):
    call, pattern = AGGREGATE_WINDOWS[aggregate]
    outcome = emit("postgres", select_body(call))
    assert outcome.status == "VERIFIED", blockers(outcome)
    sql = sql_of(outcome)
    assert re.search(pattern, sql)
    assert (
        sql.count(" AS pg_catalog.int8)") == (2 if aggregate == "sum" else 0)
        and "OVER (ORDER BY " in sql
    )
    origins = [
        column["correspondence"]["window_origin"]["function"]
        for column in public(outcome)["columns"]
        if "window_origin" in column["correspondence"]
    ]
    assert origins == [call.partition("(")[0]]
    # Only SUM(Int) rests on the checked bigint narrowing, as a grouped one.
    assert [
        item["evidence"]
        for item in public(outcome)["requirements"]
        if item["kind"] == "window_computation"
    ] == [[{"overflow": CHECKED}] if aggregate == "sum" else []]
    assert _observed(outcome) == "ok"
    assert _observed(outcome, _flip_window_evidence) != "ok"


@pytest.mark.parametrize("form", sorted(AGGREGATE_WINDOW_FORMS))
def test_postgres_aggregate_windows_over_frames_groups_qualify_and_joins(form):
    body, pattern = AGGREGATE_WINDOW_FORMS[form]
    outcome = emit("postgres", body)
    assert outcome.status == "VERIFIED", blockers(outcome)
    assert re.search(pattern, sql_of(outcome))
    assert _observed(outcome) == "ok"


@pytest.mark.parametrize(
    ("call", "code", "detail"),
    (
        ("sum(money)", "PIE-B1004", "decimal_aggregate_range_proof_missing"),
        ("avg(money)", "PIE-B1004", "decimal_aggregate_range_proof_missing"),
        ("avg(ratio)", "PIE-B1004", "float_aggregate_finite_result_proof_missing"),
        ("sum(ratio)", "PIE-B1004", "float_aggregate_finite_result_proof_missing"),
        ("min(money)", "PIE-B1003", "min_argument_outside_reviewed_int_domain"),
        ("max(ratio)", "PIE-B1003", "max_argument_outside_reviewed_int_domain"),
        ("count(text)", "PIE-B1003", "count_argument_outside_reviewed_int_domain"),
        ("count(flag)", "PIE-B1003", "count_argument_outside_reviewed_int_domain"),
    ),
)
def test_postgres_aggregate_window_arguments_keep_the_aggregate_domain(
    call, code, detail
):
    outcome = emit("postgres", select_body(call))
    assert outcome.status == "BLOCKED"
    assert [(b.code, b.detail) for b in outcome.blockers] == [(code, detail)]


@pytest.mark.parametrize("aggregate", sorted(AGGREGATE_WINDOWS))
def test_mysql_keeps_aggregate_windows_refused_before_its_database_evidence(
    aggregate,
):
    outcome = emit("mysql", select_body(AGGREGATE_WINDOWS[aggregate][0]))
    assert outcome.status == "BLOCKED"
    assert [(b.code, b.detail) for b in outcome.blockers] == [
        ("PIE-B1003", "window_aggregate_approved_non_support_on_mysql")
    ]
    # The public document carries the refusal with its suggestion.
    assert [
        (b["code"], b["subject"]["detail"], b["suggestion"])
        for b in public(outcome)["blockers"]
    ] == [
        (
            "PIE-B1003",
            "window_aggregate_approved_non_support_on_mysql",
            "Emit this aggregate window for PostgreSQL, or keep it in check/plan: "
            "a project's MySQL aggregate window awaits its real-database "
            "differential.",
        )
    ]


@pytest.mark.parametrize("legacy_cast", (False, True))
def test_independent_readers_reject_decimal_sum_window_artifacts(
    tmp_path, monkeypatch, legacy_cast
):
    from pietto._project import project_sql_emission as emission
    from pietto._project import project_sql_emission_windows as windowing
    from pietto._project import project_sql_emission_verification as verification
    from pietto._project import project_sql_emission_portable as portable
    from pietto._project import project_sql_emission_pure_boundary as pure
    from pietto._project.project_sql_emission_contract import (
        prepare_project_sql_emission,
    )

    item = probe.parameterized_fixture(
        "postgres", select_body("sum(money)"), protocol=False
    )
    encoded = item["contract"].encode()
    checked, refused = probe.build_case(tmp_path, item["source"], encoded)
    assert checked.verified and refused.artifact is None
    assert [(b.code, b.detail) for b in refused.blockers] == [
        ("PIE-B1004", "decimal_aggregate_range_proof_missing")
    ]
    request = prepare_project_sql_emission(checked, encoded)
    # Bypass only construction admission, rebuilding SQL and all occurrence
    # evidence together. Also exercise the old Int result-cast spelling.
    with monkeypatch.context() as patch:
        patch.setattr(windowing, "aggregate_argument_problem", lambda *args: None)
        if legacy_cast:
            patch.setattr(
                windowing, "aggregate_casts", lambda *args: (None, "pg_catalog.int8")
            )
        realization = emission.realize_rows(request)
        query = realization.query
        assert type(query) is emission.SQLRowQuery
        rendered = emission.render_row_sql(query)
        original, generated = emission.build_row_requirements(request, query)
        artifact = emission.EmissionArtifact(
            request,
            query,
            rendered,
            original,
            generated,
            request.plan.fixed_envelope.values,
            tuple(p.use for p in emission.row_parameter_leaves(query)),
        )
    verdict = verification.verify_project_sql_emission(artifact, request)
    assert not verdict.verified
    assert "plan_ast_correspondence" in verdict.issues
    assert (
        portable.export_emission_observation(artifact, request).status
        is portable.ObservationStatus.UNVERIFIED
    )
    data = portable._Export(artifact, request).run()
    result = pure.parse_emission_observation(data)
    assert result.status is pure.Status.INVALID_RELATION
    assert result.detail == "window aggregate"
