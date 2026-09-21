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

import _pietto_phase66_sql_emission_probe as probe
from pietto._project.project_sql_emission import serialize_project_sql_emission

TARGETS = ("postgres", "mysql")
IDENTIFIER_CASE = {
    "postgres": "quoted_exact",
    "mysql": "lower_case_table_names=0",
}
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


def emit(target, body):
    """One published window fixture through the installed pipeline."""
    base = probe.fixture(target)
    header = base["source"].split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": IDENTIFIER_CASE[target],
        }
    )
    with tempfile.TemporaryDirectory() as directory:
        _, outcome = probe.build_case(
            Path(directory) / "case",
            header + body,
            probe.encoded(contract).decode(),
            "preserve_literals",
        )
    return outcome


def sql_of(outcome) -> str:
    assert outcome.artifact is not None
    return outcome.artifact.rendered.sql.decode()


def blockers(outcome) -> list[str]:
    return [item.detail for item in (outcome.blockers or ())]


def public(outcome) -> dict:
    return json.loads(serialize_project_sql_emission(outcome).decode())


def select_body(call, *, frame="", order="id", partition=None, alias="w"):
    lines = [
        "table result:",
        "    from rows",
        "    select:",
        "        id",
        f"        {alias} = {call} window:",
    ]
    if partition is not None:
        lines += ["            partition by:", f"                {partition}"]
    lines += ["            order by:"]
    lines += [f"                {key}" for key in order.split(",")]
    if frame:
        lines += [f"            {frame}"]
    return "\n".join(lines) + "\n"


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


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("frame", sorted(FRAMES))
def test_admitted_frames_emit_their_exact_unit_and_bounds(target, frame):
    """R15: an admitted frame is emitted exactly, never silently dropped."""
    authored, spelling = FRAMES[frame]
    outcome = emit(target, select_body("first_value(id)", frame=authored))
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
        outcome = emit("mysql", select_body("first_value(id)", frame=authored))
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
    )
    assert admitted.status == "VERIFIED", blockers(admitted)
    assert "RANGE BETWEEN 1 PRECEDING AND CURRENT ROW" in sql_of(admitted)


NAMED_BODY = """table result:
    from rows
    select:
        id
        w = rank() window named
        w2 = dense_rank() window named
    window named:
        order by:
            id
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
        w = row_number() window:
            order by:
                id
    qualify:
        w <= 2
"""
QUALIFY_HIDDEN = """table result:
    from rows
    select:
        id
    qualify:
        row_number() window:
            order by:
                id
        <= 2
"""
QUALIFY_BOTH = """table result:
    from rows
    select:
        id
        w = row_number() window:
            order by:
                id
    qualify:
        row_number() window:
            order by:
                id
        <= 3 and w <= 2
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
