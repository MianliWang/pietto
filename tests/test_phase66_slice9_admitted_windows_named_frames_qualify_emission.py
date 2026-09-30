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
@pytest.mark.parametrize("value", ("-1", "true", "1.5"))
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
        w = nth_value(id, 2147483648) window:
            order by:
                id
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

    base = probe.fixture("postgres")
    header = base["source"].split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"}
    )
    encoded = probe.encoded(contract)
    checked, refused = probe.build_case(
        tmp_path, header + select_body(structural_call(function, value)), encoded
    )
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
