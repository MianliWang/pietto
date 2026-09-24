"""Phase66 pre-Slice16 completion corrective closure: G1 and G3 repairs, G2-G6 evidence.

G1: one named window declaration no longer collapses distinct use-local
specifications. G3 (R15-INT-OFFSET-V1): every finite frame offset is a signed64
count or distance, and every RANGE threshold an exact signed64 value. G2, G4, G5
and G6 close promised witnesses without changing product semantics. Expected
values below are derived by hand or from the fixture rows, never from the
emitter under test.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
from typing import Any

import pytest

import _pietto_phase66_sql_emission_probe as probe
import _pietto_target_conformance_cases as cases
from pietto._project import project_sql_emission_ast as sql_ast
from pietto._project import project_sql_emission_portable as portable
from pietto._project import project_sql_emission_pure_boundary as pure
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_verification as verification
from pietto._project import project_sql_emission_windows as windowing
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_rendering import render_row_sql

TARGETS = ("postgres", "mysql")
I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1
WIDE = (-9007199254740993, 9007199254740993)
SPEC = (
    Path(__file__).resolve().parents[1]
    / "docs/spec/phase66-pre-slice16-completion-corrective-closure-v1.md"
)
OFFSET_MISSING = ("PIE-B1004", "window_frame_offset_evidence_missing")
OFFSET_WIDE = ("PIE-B1002", "window_frame_offset_out_of_signed64_range")
BOUNDARY_WIDE = ("PIE-B1002", "window_range_boundary_out_of_signed64_range")


def _build(item: dict[str, Any]) -> Any:
    with tempfile.TemporaryDirectory() as directory:
        return probe.build_case(
            Path(directory) / "case", item["source"], item["contract"], item["policy"]
        )[1]


def _item(target: str, body: str, *, key=None, policy="preserve_literals") -> dict:
    """The published rows source, optionally with its `id` representation replaced."""
    base = probe.fixture(target)
    header = base["source"].split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    if key is not None:
        contract["sources"][0]["fields"][0]["representation"] = key
    return {
        "source": header + body,
        "contract": probe.encoded(contract).decode(),
        "policy": policy,
    }


def _int_key(target: str, low: int, high: int, *, width: int = 64) -> dict:
    kind = {
        ("postgres", 16): "pg_int2",
        ("postgres", 64): "pg_int8",
        ("mysql", 16): "my_smallint",
        ("mysql", 64): "my_bigint",
    }[target, width]
    return {
        "storage": {"kind": kind},
        "nullable": False,
        "domain": {"kind": "int_range", "min": str(low), "max": str(high)},
    }


def _window(call: str, frame: str = "", order: str = "id") -> str:
    lines = [
        "query result:",
        "    from rows",
        "    select:",
        "        record_id = id",
        f"        w = {call} window:",
        "            order by:",
        f"                {order}",
    ]
    if frame:
        lines.append(f"            {frame}")
    return "\n".join(lines) + "\n"


def _refusal(outcome: Any) -> list[tuple[str, str]]:
    return [(item.code, item.detail) for item in outcome.blockers or ()]


def _sql(outcome: Any) -> str:
    assert outcome.status == "VERIFIED", _refusal(outcome)
    return outcome.artifact.rendered.sql.decode()


def _generated(artifact: Any) -> list[Any]:
    return list(artifact.generated_requirements)


# -- G1: named declaration identity versus use-local specification -----------

NAMED_PLAIN_FIRST = """query result:
    from rows
    select:
        id
        a = rank() window base
        c = row_number() window base:
            partition by:
                flag
        d = dense_rank() window base
        e = first_value(id) window base:
            rows between 1 preceding and current row
    window base:
        order by:
            id
"""
INLINE_PLAIN_FIRST = """query result:
    from rows
    select:
        id
        a = rank() window:
            order by:
                id
        c = row_number() window:
            partition by:
                flag
            order by:
                id
        d = dense_rank() window:
            order by:
                id
        e = first_value(id) window:
            order by:
                id
            rows between 1 preceding and current row
"""


def _reorder(body: str) -> str:
    """The same uses with the extended one authored first."""
    plain = "        a = rank() window base\n"
    assert body.count(plain) == 1
    moved = body.replace(plain, "")
    tail = "    window base:\n"
    assert tail in moved
    return moved.replace(tail, plain + tail)


def _over(sql: str) -> dict[str, str]:
    """Each generated column's resolved OVER text, through WINDOW definitions."""
    definitions = dict(re.findall(r'["`](w\d+)["`] AS \(([^()]*)\)', sql))
    resolved = {}
    for symbol, inline, column in re.findall(
        r'OVER (?:["`](w\d+)["`]|\(([^()]*)\)) AS ["`](c\d+)["`]', sql
    ):
        resolved[column] = definitions[symbol] if symbol else inline
    return resolved


def _column_by_label(sql: str) -> dict[str, str]:
    pairs = re.findall(r'["`]t\d+["`]\.["`](c\d+)["`] AS ["`]([a-z])["`]', sql)
    return {label: column for column, label in pairs}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("extended_first", (False, True))
def test_each_named_use_keeps_its_own_complete_window(target, extended_first):
    """Named output windows equal an independent inline control, in both orders."""
    # Columns are matched by label, so one inline control serves both orders.
    named = _reorder(NAMED_PLAIN_FIRST) if extended_first else NAMED_PLAIN_FIRST
    named_sql = _sql(_build(_item(target, named)))
    inline_sql = _sql(_build(_item(target, INLINE_PLAIN_FIRST)))
    named_over, inline_over = _over(named_sql), _over(inline_sql)
    named_columns, inline_columns = (
        _column_by_label(named_sql),
        _column_by_label(inline_sql),
    )
    assert set(named_columns) == set(inline_columns) == {"a", "c", "d", "e"}
    for label in ("a", "c", "d", "e"):
        assert named_over[named_columns[label]] == inline_over[inline_columns[label]], (
            label
        )
    assert "PARTITION BY" in named_over[named_columns["c"]]
    assert "PARTITION BY" not in named_over[named_columns["a"]]
    assert "ROWS BETWEEN 1 PRECEDING" in named_over[named_columns["e"]]
    # Three distinct complete specifications, one shared by the two plain uses.
    definitions = re.findall(r'["`](w\d+)["`] AS \(', named_sql)
    assert definitions == ["w0", "w1", "w2"]
    references = re.findall(r'OVER ["`](w\d+)["`]', named_sql)
    assert sorted(Counter(references).values()) == [1, 1, 2]


@pytest.mark.parametrize("target", TARGETS)
def test_identical_uses_share_and_equal_declarations_stay_apart(target):
    shared = probe.fixture(target, "A_window_named", "shared")
    sql = _sql(_build(shared))
    assert (
        sql.count(" WINDOW ") == 1 and len(re.findall(r"OVER [\"`]w0[\"`]", sql)) == 2
    )
    twins = """query result:
    from rows
    select:
        id
        a = rank() window first
        b = rank() window second
    window first:
        order by:
            id
    window second:
        order by:
            id
"""
    sql = _sql(_build(_item(target, twins)))
    definitions = re.findall(r'["`](w\d+)["`] AS \(([^()]*)\)', sql)
    assert [name for name, _ in definitions] == ["w0", "w1"]
    assert definitions[0][1] == definitions[1][1]


def test_an_exclusion_difference_is_its_own_definition_on_postgres():
    body = """query result:
    from rows
    select:
        id
        a = first_value(id) window base
        b = first_value(id) window base:
            groups between 1 preceding and current row exclude current row
    window base:
        order by:
            id
"""
    sql = _sql(_build(_item("postgres", body)))
    definitions = dict(re.findall(r'"(w\d+)" AS \(([^()]*)\)', sql))
    assert len(definitions) == 2
    assert "EXCLUDE CURRENT ROW" in definitions["w1"]
    assert "EXCLUDE" not in definitions["w0"]
    mysql = _build(_item("mysql", body))
    assert _refusal(mysql) == [
        ("PIE-B1003", "window_frame_groups_approved_non_support_on_mysql")
    ]


def _named_artifact(target: str) -> Any:
    artifact = _build(_item(target, NAMED_PLAIN_FIRST)).artifact
    assert artifact is not None and type(artifact.ast) is sql_ast.SQLRowQuery
    return artifact


def _with_stage(artifact: Any, change) -> Any:
    """Coordinated drift: rebuild SQL bytes, ranges and both denominators."""
    query = artifact.ast
    bodies = list(query.bodies)
    index = next(i for i, body in enumerate(bodies) if body.window is not None)
    bodies[index] = change(bodies[index])
    drifted = replace(query, bodies=tuple(bodies))
    rendered = render_row_sql(drifted)
    original, generated = sql_ast.build_row_requirements(artifact.request, drifted)
    return replace(
        artifact,
        ast=drifted,
        rendered=rendered,
        original_requirements=original,
        generated_requirements=generated,
    )


def _swap_definitions(body: Any) -> Any:
    stage = body.window
    first, second = stage.definitions[:2]
    definitions = (
        replace(first, specification=second.specification),
        replace(second, specification=first.specification),
        *stage.definitions[2:],
    )
    return replace(body, window=replace(stage, definitions=definitions))


def _one_definition_for_all(body: Any) -> Any:
    stage = body.window
    symbol = stage.definitions[0].symbol

    def retarget(column):
        if type(column) is not windowing.WindowColumn:
            return column
        specification = column.specification
        if specification.symbol is None:
            return column
        return replace(column, specification=replace(specification, symbol=symbol))

    columns = tuple(retarget(column) for column in body.columns)
    return replace(
        body,
        columns=columns,
        window=replace(
            stage,
            definitions=stage.definitions[:1],
            columns=tuple(c for c in columns if type(c) is windowing.WindowColumn),
        ),
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("mutation", (_swap_definitions, _one_definition_for_all))
def test_wrong_named_definitions_meet_the_independent_walk(target, mutation):
    artifact = _named_artifact(target)
    drifted = _with_stage(artifact, mutation)
    assert drifted.rendered.sql != artifact.rendered.sql
    checked = verification.verify_project_sql_emission(drifted, artifact.request)
    assert checked.issues == ("plan_ast_correspondence",)


@pytest.mark.parametrize("target", TARGETS)
def test_a_first_use_collapse_constructor_fault_is_refused(target, monkeypatch):
    """Fault injection: the builder shares every named use's first definition."""
    monkeypatch.setattr(windowing, "same_specification", lambda *_: True)
    outcome = _build(_item(target, NAMED_PLAIN_FIRST))
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _refusal(outcome) == [("PIE-B1008", "plan_ast_correspondence")]


# -- G3: R15-INT-OFFSET-V1 ----------------------------------------------------

EXAMPLES = (
    # (key domain, offset, direction, bound kind, passes the arithmetic check)
    ((I64_MIN, I64_MIN + 2), 1, "asc", "offset_preceding", False),
    ((I64_MIN, I64_MIN + 2), 1, "asc", "offset_following", True),
    ((I64_MIN, I64_MIN + 2), 1, "desc", "offset_preceding", True),
    ((I64_MIN, I64_MIN + 2), 1, "desc", "offset_following", False),
    ((I64_MAX - 2, I64_MAX), 1, "asc", "offset_preceding", True),
    ((I64_MAX - 2, I64_MAX), 1, "asc", "offset_following", False),
    ((I64_MAX - 2, I64_MAX), 1, "desc", "offset_preceding", False),
    ((I64_MAX - 2, I64_MAX), 1, "desc", "offset_following", True),
    (WIDE, I64_MAX, "asc", "offset_preceding", False),
    (WIDE, I64_MAX, "asc", "offset_following", False),
    (WIDE, I64_MAX, "desc", "offset_preceding", False),
    ((I64_MIN, I64_MAX), 0, "asc", "offset_preceding", True),
    ((I64_MIN, I64_MAX), 0, "desc", "offset_following", True),
    ((I64_MIN + 1, 0), 1, "asc", "offset_preceding", True),
    ((0, I64_MAX - 1), 1, "asc", "offset_following", True),
)


def _key_read(low: int, high: int, kind: str = "pg_int8") -> Any:
    domain = {"kind": "int_range", "min": str(low), "max": str(high)}
    return SimpleNamespace(
        realization=rows.Realization("Int", {"kind": kind}, False, domain)
    )


@pytest.mark.parametrize("domain,offset,direction,kind,passes", EXAMPLES)
def test_the_four_independent_threshold_checks_agree_with_hand_intervals(
    domain, offset, direction, kind, passes
):
    """Builder, runtime verifier, pure checker and public decoder: one table."""
    read = _key_read(*domain)
    order = windowing.WindowOrderItem(0, read, direction, None, None)
    frame = windowing.WindowFrameSpec("range", (kind, ""), ("current_row", ""))
    offsets = ((kind, offset),)
    built = windowing.range_arithmetic_problem(frame, offsets, (order,))
    assert (built is None) is passes
    if not passes:
        assert built == BOUNDARY_WIDE
    assert verification._range_thresholds_exact("range", offsets, (order,)) is passes
    serialized = {
        "tag": "Int",
        "storage": {"kind": "pg_int8"},
        "nullable": False,
        "domain": read.realization.domain,
    }
    assert pure._thresholds_exact(serialized, direction, offsets) is passes
    computed = {**serialized, "storage": {"kind": "my_signed_int"}}
    assert pure._thresholds_exact(computed, direction, offsets) is passes
    suffix = "PRECEDING" if kind == "offset_preceding" else "FOLLOWING"
    assert probe.range_thresholds_exact(serialized, direction, ((suffix, offset),)) is (
        passes
    )
    assert probe.range_thresholds_exact(computed, direction, ((suffix, offset),)) is (
        passes
    )


def test_missing_or_contradictory_key_domains_are_internal_evidence_faults():
    """Labelled internal controls: normal contracts reject these shapes earlier."""
    frame = windowing.WindowFrameSpec(
        "range", ("offset_preceding", ""), ("current_row", "")
    )
    offsets = (("offset_preceding", 1),)
    unusable = (
        SimpleNamespace(
            realization=rows.Realization("Int", {"kind": "pg_int8"}, False, {})
        ),
        SimpleNamespace(
            realization=rows.Realization("Int", {"kind": "pg_numeric"}, False, {})
        ),
        _key_read(5, 4),
    )
    for read in unusable:
        order = windowing.WindowOrderItem(0, read, "asc", None, None)
        assert windowing.range_arithmetic_problem(frame, offsets, (order,)) == (
            "PIE-B1004",
            "window_range_arithmetic_evidence_missing",
        )
        assert not verification._range_thresholds_exact("range", offsets, (order,))
    outside = windowing.WindowOrderItem(
        0, _key_read(0, 40000, "pg_int2"), "asc", None, None
    )
    assert windowing.range_arithmetic_problem(frame, offsets, (outside,)) == (
        "PIE-B1002",
        "window_range_key_domain_out_of_storage_range",
    )
    assert not verification._range_thresholds_exact("range", offsets, (outside,))
    # A narrow key's domain inside its storage admits a wider threshold.
    narrow = windowing.WindowOrderItem(
        0, _key_read(0, 10, "pg_int2"), "asc", None, None
    )
    assert (
        windowing.range_arithmetic_problem(
            frame, (("offset_preceding", 40000),), (narrow,)
        )
        is None
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "frame,refusal",
    (
        ("rows between 0 preceding and current row", None),
        ("rows between 1 preceding and current row", None),
        (f"rows between {I64_MAX} preceding and current row", None),
        (f"rows between {I64_MAX + 1} preceding and current row", OFFSET_WIDE),
        (f"rows between {10**30} preceding and current row", OFFSET_WIDE),
        ("rows between 2 preceding and 3 following", None),
        (f"rows between 2 preceding and {I64_MAX + 1} following", OFFSET_WIDE),
        ("rows between -1 preceding and current row", OFFSET_MISSING),
        ("rows between id preceding and current row", OFFSET_MISSING),
        ("range between 1 preceding and current row", None),
        (f"range between {I64_MAX} preceding and current row", BOUNDARY_WIDE),
        (f"range between {I64_MAX + 1} preceding and current row", OFFSET_WIDE),
        ("range between 0 preceding and 0 following", None),
    ),
)
def test_finite_offsets_over_the_published_key(target, frame, refusal):
    outcome = _build(_item(target, _window("first_value(id)", frame)))
    if refusal is None:
        assert outcome.status == "VERIFIED", _refusal(outcome)
    else:
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        assert _refusal(outcome) == [refusal]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "call,frame",
    (
        (
            "last_value(id)",
            "range between 100000000000000000000 preceding and current row",
        ),
        (
            "last_value(id)",
            "range between 9223372036854775807 preceding and current row",
        ),
        (
            "last_value(id)",
            "range between 18446744073709551616 following and unbounded following",
        ),
        (
            "first_value(id)",
            "rows between 100000000000000000000 preceding and current row",
        ),
        (
            "first_value(id)",
            "rows between 9223372036854775808 preceding and current row",
        ),
    ),
)
def test_the_five_reported_huge_offsets_are_no_longer_verified(target, call, frame):
    outcome = _build(_item(target, _window(call, frame)))
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    expected = BOUNDARY_WIDE if frame.startswith("range between 9223") else OFFSET_WIDE
    assert _refusal(outcome) == [expected]


@pytest.mark.parametrize("target", TARGETS)
def test_counts_never_depend_on_the_order_key_storage(target):
    narrow = _int_key(target, 0, 10, width=16)
    for frame in (
        "rows between 40000 preceding and current row",
        f"rows between {I64_MAX} preceding and current row",
        "range between 40000 preceding and current row",
    ):
        outcome = _build(_item(target, _window("first_value(id)", frame), key=narrow))
        assert outcome.status == "VERIFIED", (frame, _refusal(outcome))
    outcome = _build(
        _item(
            target,
            _window(
                "first_value(id)",
                f"rows between {I64_MAX + 1} preceding and current row",
            ),
            key=narrow,
        )
    )
    assert _refusal(outcome) == [OFFSET_WIDE]


def test_groups_share_the_count_domain_only_where_admitted():
    frame = "groups between {} preceding and current row"
    admitted = _build(
        _item("postgres", _window("first_value(id)", frame.format(I64_MAX)))
    )
    assert admitted.status == "VERIFIED", _refusal(admitted)
    too_wide = _build(
        _item("postgres", _window("first_value(id)", frame.format(I64_MAX + 1)))
    )
    assert _refusal(too_wide) == [OFFSET_WIDE]
    for offset in (1, I64_MAX + 1):
        mysql = _build(_item("mysql", _window("first_value(id)", frame.format(offset))))
        assert _refusal(mysql) == [
            ("PIE-B1003", "window_frame_groups_approved_non_support_on_mysql")
        ]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "domain,order,frame,passes",
    (
        (
            (I64_MIN, I64_MIN + 2),
            "id",
            "range between 1 preceding and current row",
            False,
        ),
        (
            (I64_MIN, I64_MIN + 2),
            "id",
            "range between current row and 1 following",
            True,
        ),
        (
            (I64_MIN, I64_MIN + 2),
            "id desc",
            "range between 1 preceding and current row",
            True,
        ),
        (
            (I64_MIN, I64_MIN + 2),
            "id desc",
            "range between current row and 1 following",
            False,
        ),
        (
            (I64_MAX - 2, I64_MAX),
            "id",
            "range between 1 preceding and current row",
            True,
        ),
        (
            (I64_MAX - 2, I64_MAX),
            "id",
            "range between current row and 1 following",
            False,
        ),
        (
            (I64_MAX - 2, I64_MAX),
            "id desc",
            "range between 1 preceding and current row",
            False,
        ),
        (
            (I64_MAX - 2, I64_MAX),
            "id desc",
            "range between current row and 1 following",
            True,
        ),
        ((I64_MIN, I64_MAX), "id", "range between 0 preceding and 0 following", True),
        ((I64_MIN + 1, 0), "id", "range between 1 preceding and current row", True),
        ((0, I64_MAX - 7), "id", "range between 5 preceding and 7 following", True),
        ((0, I64_MAX - 6), "id", "range between 5 preceding and 7 following", False),
        ((I64_MIN + 5, 0), "id", "range between 5 preceding and 5 preceding", True),
        ((I64_MIN + 4, 0), "id", "range between 5 preceding and 5 preceding", False),
    ),
)
def test_range_thresholds_are_direction_sensitive_and_inclusive(
    target, domain, order, frame, passes
):
    outcome = _build(
        _item(
            target,
            _window("last_value(id)", frame, order),
            key=_int_key(target, *domain),
        )
    )
    if passes:
        assert outcome.status == "VERIFIED", _refusal(outcome)
    else:
        assert _refusal(outcome) == [BOUNDARY_WIDE]


def _window_requirements(artifact: Any) -> list[Any]:
    return [
        g
        for g in _generated(artifact)
        if g.kind
        in {
            "window_specification",
            "window_frame_offset_domain",
            "window_range_arithmetic",
        }
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_offset_requirements_sit_beside_each_use_specification(target):
    for variant, kinds in (
        (
            "rows",
            [
                "window_specification",
                "window_frame_offset_domain",
                "window_specification",
                "window_frame_offset_domain",
            ],
        ),
        (
            "range",
            [
                "window_specification",
                "window_frame_offset_domain",
                "window_range_arithmetic",
            ],
        ),
    ):
        artifact = _build(probe.fixture(target, "A_window_frame", variant)).artifact
        found = _window_requirements(artifact)
        assert [g.kind for g in found] == kinds
        generated = _generated(artifact)
        for requirement in found:
            assert requirement.rule == "R15"
            # Each obligation directly follows its own use's specification.
            position = generated.index(requirement)
            if requirement.kind != "window_specification":
                previous = generated[position - 1]
                assert previous.subject is requirement.subject
        for requirement in found:
            if requirement.kind == "window_frame_offset_domain":
                assert requirement.premises == ()
            if requirement.kind == "window_range_arithmetic":
                assert [p.key for p in requirement.premises] == ["operator_environment"]
    plain = _build(_item(target, _window("row_number()"))).artifact
    assert [g.kind for g in _window_requirements(plain)] == ["window_specification"]


def _requirement_mutations(generated: list[Any]) -> list[list[Any]]:
    arithmetic = next(
        i for i, g in enumerate(generated) if g.kind == "window_range_arithmetic"
    )
    domain = arithmetic - 1
    return [
        generated[:arithmetic] + generated[arithmetic + 1 :],
        generated[:domain] + generated[domain + 1 :],
        generated[: arithmetic + 1]
        + [generated[arithmetic]]
        + generated[arithmetic + 1 :],
        generated[:domain]
        + [generated[arithmetic], generated[domain]]
        + generated[arithmetic + 1 :],
        generated[:domain]
        + [replace(generated[domain], premises=generated[arithmetic].premises)]
        + generated[domain + 1 :],
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_deleted_duplicated_reordered_or_misattributed_offset_claims_reject(target):
    artifact = _build(probe.fixture(target, "A_window_frame", "range")).artifact
    assert verification.verify_project_sql_emission(artifact, artifact.request).verified
    for mutated in _requirement_mutations(_generated(artifact)):
        forged = replace(artifact, generated_requirements=tuple(mutated))
        assert not verification.verify_project_sql_emission(
            forged, artifact.request
        ).verified
    # Two uses: the first use's offset claim attributed to the second use.
    two = _build(probe.fixture(target, "A_window_frame", "rows")).artifact
    generated = _generated(two)
    claims = [
        i for i, g in enumerate(generated) if g.kind == "window_frame_offset_domain"
    ]
    assert len(claims) == 2
    swapped = list(generated)
    swapped[claims[0]] = replace(
        generated[claims[0]], subject=generated[claims[1]].subject
    )
    forged = replace(two, generated_requirements=tuple(swapped))
    assert not verification.verify_project_sql_emission(forged, two.request).verified
    document = json.loads(
        serialize_project_sql_emission(
            _build(probe.fixture(target, "A_window_frame", "range"))
        )
    )
    for kind in ("window_frame_offset_domain", "window_range_arithmetic"):
        forged_document = json.loads(json.dumps(document))
        forged_document["requirements"] = [
            item for item in forged_document["requirements"] if item["kind"] != kind
        ]
        with pytest.raises(ValueError):
            probe.decode_public(probe.encoded(forged_document))


def _drift_frame(artifact: Any, change) -> Any:
    def body_change(body):
        stage = body.window
        columns = []
        for column in body.columns:
            if type(column) is windowing.WindowColumn:
                column = replace(column, specification=change(column.specification))
            columns.append(column)
        return replace(
            body,
            columns=tuple(columns),
            window=replace(
                stage,
                columns=tuple(c for c in columns if type(c) is windowing.WindowColumn),
            ),
        )

    return _with_stage(artifact, body_change)


@pytest.mark.parametrize("target", TARGETS)
def test_coordinated_unsafe_offsets_and_intervals_meet_the_independent_walk(target):
    artifact = _build(probe.fixture(target, "A_window_frame", "range")).artifact

    def unsafe_offset(specification):
        frame = specification.frame
        start = ("offset_preceding", f"{I64_MAX} PRECEDING")
        return replace(specification, frame=replace(frame, start=start))

    def reversed_direction(specification):
        orders = tuple(replace(item, direction="desc") for item in specification.orders)
        return replace(specification, orders=orders)

    def false_interval(specification):
        item = specification.orders[0]
        realization = replace(
            item.read.realization,
            domain={"kind": "int_range", "min": str(I64_MIN), "max": str(I64_MAX)},
        )
        read = replace(item.read, realization=realization)
        return replace(specification, orders=(replace(item, read=read),))

    for change in (unsafe_offset, reversed_direction, false_interval):
        drifted = _drift_frame(artifact, change)
        assert drifted.rendered.sql != artifact.rendered.sql or change is false_interval
        checked = verification.verify_project_sql_emission(drifted, artifact.request)
        assert "plan_ast_correspondence" in checked.issues, change.__name__


@pytest.mark.parametrize("target", TARGETS)
def test_an_omitted_builder_threshold_check_is_refused(target, monkeypatch):
    """Fault injection: the builder skips RANGE arithmetic; the walk does not."""
    monkeypatch.setattr(windowing, "range_arithmetic_problem", lambda *_: None)
    body = _window(
        "last_value(id)", f"range between {I64_MAX} preceding and current row"
    )
    outcome = _build(_item(target, body))
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _refusal(outcome) == [("PIE-B1008", "plan_ast_correspondence")]


def _observation(artifact: Any) -> dict:
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OK
    correspondence = portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    )
    assert correspondence.corresponds, correspondence.issues
    assert observed.canonical_bytes is not None
    return json.loads(observed.canonical_bytes)


def _pure(document: dict) -> tuple[Any, Any]:
    data = (
        json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    outcome = pure.parse_emission_observation(data)
    return outcome.status, outcome.detail


@pytest.mark.parametrize("target", TARGETS)
def test_serialized_offsets_and_thresholds_are_checked_data_only(target):
    artifact = _build(probe.fixture(target, "A_window_frame", "range")).artifact
    document = _observation(artifact)
    assert _pure(document)[0] is pure.Status.OK
    frames = [
        record
        for record in document["records"]
        if record["ref"][0] == "window_frame" and record["fields"]["unit"] == "range"
    ]
    assert frames
    for text, detail in (
        (f"{I64_MAX + 1} PRECEDING", "frame offset"),
        (f"{I64_MAX} PRECEDING", "range threshold arithmetic"),
    ):
        forged = json.loads(json.dumps(document))
        for record in forged["records"]:
            if record["ref"] == frames[0]["ref"]:
                record["fields"]["start"] = ["offset_preceding", text]
        status, found = _pure(forged)
        assert status is not pure.Status.OK and found == detail


# -- G1 + G4 target witness ------------------------------------------------------


def _agg_rows() -> list[tuple[Any, ...]]:
    return sorted(cases.AGGREGATE_TABLE_ROWS["phase66 agg é"], key=lambda row: row[6])


def _lag(values, *, ignore_nulls: bool):
    result, seen = [], []
    for value in values:
        if ignore_nulls:
            result.append(seen[-1] if seen else None)
            if value is not None:
                seen.append(value)
        else:
            result.append(seen[-1] if seen else None)
            seen.append(value)
    return result


def _first_of_two(values, *, ignore_nulls: bool):
    result = []
    for index in range(len(values)):
        frame = values[max(0, index - 1) : index + 1]
        if ignore_nulls:
            frame = [value for value in frame if value is not None]
        result.append(frame[0] if frame else None)
    return result


def test_the_use_local_oracle_is_derived_from_the_fixture_rows():
    """Hand semantics over the fixed relation: RESPECT NULLS is the oracle."""
    ordered = _agg_rows()
    values = [row[1] for row in ordered]

    def cell(value):
        return (
            {"kind": "null"} if value is None else {"kind": "int", "value": str(value)}
        )

    respected = [
        [cell(row[6]), cell(previous), cell(earliest)]
        for row, previous, earliest in zip(
            ordered,
            _lag(values, ignore_nulls=False),
            _first_of_two(values, ignore_nulls=False),
            strict=True,
        )
    ]
    expected = cases.WINDOW_EXPECTATIONS[
        cases.window_key("A_window_named", "use_local")
    ]
    assert respected == expected
    assert _lag(values, ignore_nulls=True) != _lag(values, ignore_nulls=False)
    assert _first_of_two(values, ignore_nulls=True) != _first_of_two(
        values, ignore_nulls=False
    )
    # A first-use collapse would give `earliest` the plain use's default frame,
    # whose first value is the first row's.
    assert [row[2] for row in expected] != [cell(values[0])] * len(values)


@pytest.mark.parametrize("target", TARGETS)
def test_use_local_witness_verifies_and_decodes_in_every_consumer(target):
    item = probe.fixture(target, "A_window_named", "use_local")
    outcome = _build(item)
    sql = _sql(outcome)
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["label"] for c in document["columns"]] == [
        "record_id",
        "previous",
        "earliest",
    ]
    definitions = dict(re.findall(r'["`](w\d+)["`] AS \(([^()]*)\)', sql))
    assert list(definitions) == ["w0", "w1"]
    assert "ROWS" not in definitions["w0"]
    assert "ROWS BETWEEN 1 PRECEDING AND CURRENT ROW" in definitions["w1"]
    _observation(outcome.artifact)


@pytest.mark.parametrize("target", TARGETS)
def test_respect_nulls_and_from_first_are_the_default_bytes_over_nullable_values(
    target,
):
    item = probe.fixture(target, "A_window_named", "use_local")
    default = _sql(_build(item))
    explicit = dict(item)
    explicit["source"] = (
        item["source"]
        .replace("lag(value) window", "lag(value) respect nulls window")
        .replace(
            "earliest = first_value(value) window",
            "earliest = first_value(value) respect nulls window",
        )
    )
    assert explicit["source"] != item["source"]
    assert _sql(_build(explicit)) == default
    nth = item["source"].replace(
        "earliest = first_value(value) window base",
        "earliest = nth_value(value, 2) window base",
    )
    assert nth != item["source"]
    nth_first = nth.replace(
        "nth_value(value, 2) window", "nth_value(value, 2) from first window"
    )
    assert _sql(_build({**item, "source": nth})) == _sql(
        _build({**item, "source": nth_first})
    )
    refused = _build(
        {
            **item,
            "source": item["source"].replace(
                "lag(value) window", "lag(value) ignore nulls window"
            ),
        }
    )
    assert _refusal(refused) == [
        ("PIE-B1003", "window_ignore_nulls_approved_non_support_in_phase66")
    ]
    from_last = nth.replace(
        "nth_value(value, 2) window", "nth_value(value, 2) from last window"
    )
    assert _refusal(_build({**item, "source": from_last})) == [
        ("PIE-B1003", "window_from_last_approved_non_support_in_phase66")
    ]


# -- G2: restricted PostgreSQL FULL ---------------------------------------------


def test_the_null_key_full_oracle_is_derived_from_the_fixture_rows():
    left = [row[1] for row in cases.AGGREGATE_TABLE_ROWS["phase66 set left é"]]
    right = [row[0] for row in _agg_rows() if row[6] > 11]
    assert (left, right) == ([1, 2, None], [2, None, 3])
    matched = [(a, b) for a in left for b in right if a is not None and a == b]
    unmatched_left = [
        (a, None) for a in left if not any(a is not None and a == b for b in right)
    ]
    unmatched_right = [
        (None, b) for b in right if not any(b is not None and a == b for a in left)
    ]

    def cell(value):
        return (
            {"kind": "null"} if value is None else {"kind": "int", "value": str(value)}
        )

    derived = Counter(
        json.dumps([cell(a), cell(b)])
        for a, b in matched + unmatched_left + unmatched_right
    )
    assert derived == Counter(json.dumps(row) for row in cases.join_rows("null_keys"))
    assert derived[json.dumps([cell(None), cell(None)])] == 2


@pytest.mark.parametrize("target", TARGETS)
def test_the_null_key_full_witness_is_postgres_only(target):
    outcome = _build(probe.fixture(target, "V_join_full", "null_keys"))
    if target == "mysql":
        assert _refusal(outcome) == [
            ("PIE-B1003", "mysql_full_join_approved_non_support")
        ]
        return
    sql = _sql(outcome)
    assert sql.count(" FULL JOIN ") == 1
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [(c["label"], c["nullable"]) for c in document["columns"]] == [
        ("a", True),
        ("b", True),
    ]


FULL = """query result:
    from lhs
    full join rhs as r:
        from lhs
        on {}
    select:
        a = lhs.id
        b = r.id
"""


@pytest.mark.parametrize(
    "predicate,detail",
    (
        ("false", "full_join_condition_not_an_equality_tree"),
        ("lhs.key < r.key", "full_join_condition_not_an_equality"),
        ("lhs.key != r.key", "full_join_condition_not_an_equality"),
        ("lhs.key == r.key and r.id > 7", "full_join_condition_not_an_equality"),
        ("lhs.key == r.key or lhs.id == r.id", "full_join_condition_uses_or"),
        (
            "lhs.key == r.key and lhs.id == lhs.key",
            "full_join_equality_within_one_input",
        ),
        ("lhs.key + 1 == r.key", "full_join_equality_operand_not_a_direct_field"),
    ),
)
def test_postgres_full_boundaries_are_exact_non_support(predicate, detail):
    item = probe.join_witness("postgres", FULL.format(predicate))
    assert _refusal(_build(item)) == [("PIE-B1003", detail)]
    mysql = _build(probe.join_witness("mysql", FULL.format(predicate)))
    assert _refusal(mysql) == [("PIE-B1003", "mysql_full_join_approved_non_support")]


def test_a_full_equality_outside_the_reviewed_int_pairing_is_refused():
    item = probe.join_witness("postgres", FULL.format("lhs.key == r.key"))
    assert _build(item).status == "VERIFIED"
    contract = json.loads(item["contract"])
    contract["sources"][1]["fields"][1]["representation"] = {
        "storage": {"kind": "pg_int4"},
        "nullable": True,
        "domain": {"kind": "int_range", "min": "-2147483648", "max": "2147483647"},
    }
    narrowed = {**item, "contract": probe.encoded(contract).decode()}
    assert _refusal(_build(narrowed)) == [
        ("PIE-B1003", "full_join_equality_outside_reviewed_int_domain")
    ]


# -- G5: physical row domains and G6: structural LIMIT --------------------------


@pytest.mark.parametrize("target", TARGETS)
def test_row_domain_witnesses_scan_their_declared_relations_without_only(target):
    for variant in ("inherited_parent", "view_rows", "partitioned_root"):
        item = probe.fixture(target, "G_scan_row_domains", variant)
        sql = _sql(_build(item))
        relation = probe.ROW_DOMAIN_RELATIONS[target, variant]
        quote = '"' if target == "postgres" else "`"
        assert f"{quote}{relation}{quote} AS " in sql
        assert "ONLY" not in sql
    statements = [sql for sql, _ in cases.row_domain_setup(target)]
    joined = "\n".join(statements)
    if target == "postgres":
        assert 'INHERITS ("phase66 parent")' in joined
        assert "PARTITION OF" in joined and "CREATE VIEW" in joined
    else:
        assert "INHERITS" not in joined
        assert "UNION ALL" in joined and "PARTITION BY LIST" in joined


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("value", (False, None))
def test_a_false_or_missing_row_domain_declaration_blocks(target, value):
    item = probe.fixture(target, "G_scan_row_domains", "view_rows")
    contract = json.loads(item["contract"])
    premises = contract["sources"][0]["premises"]
    contract["sources"][0]["premises"] = [
        {**premise, "value": value}
        if premise["key"] == "row_domain_matches"
        else premise
        for premise in premises
        if value is not None or premise["key"] != "row_domain_matches"
    ]
    outcome = _build({**item, "contract": probe.encoded(contract).decode()})
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert _refusal(outcome) == [
        ("PIE-B1001", "row_domain_matches_declaration_required")
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_bind_safe_binds_the_data_literal_and_never_the_structural_limit(target):
    item = probe.fixture(target, "G_scan_row_domains", "inherited_parent")
    assert item["policy"] == "bind_safe_literals"
    outcome = _build(item)
    sql = _sql(outcome)
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert document["fixed_values"] == [
        {**document["fixed_values"][0], "tag": "Int", "value": "0"}
    ]
    assert len(document["parameter_uses"]) == 1
    marker = "$1" if target == "postgres" else "?"
    assert sql.count(marker) == 1 and sql.endswith(" LIMIT 5")
    assert "LIMIT " + marker not in sql
    kinds = [item["kind"] for item in document["requirements"]]
    assert "static_limit" in kinds and "parameter" in kinds
    preserved = _build({**item, "policy": "preserve_literals"})
    assert preserved.artifact.rendered.sql.decode().endswith(" LIMIT 5")
    assert json.loads(serialize_project_sql_emission(preserved))["fixed_values"] == []


# -- G7 / P / B: window value result representation -----------------------------
#
# Expected widths are the reviewed rules written out by hand: PostgreSQL keeps
# the value's type except that an anycompatible lag/lead integer default joins
# with its own literal type (int4, int8 beyond signed32); MySQL's is INT below
# ten display characters (SMALLINT 6, INT 11, BIGINT 20, a d-digit default
# d + 1) and BIGINT from ten. A non-null default encloses the interval.

WIDTHS_HEADER = (
    "shape Wide:\n    rid: Int not null\n    s: Int nullable\n    i: Int nullable\n"
    "    b: Int nullable\n"
    'source rows: Wide is {target}.table("widths.locator.not.sql")\n'
)
WIDTH_KINDS = {
    ("postgres", 16): "pg_int2",
    ("postgres", 32): "pg_int4",
    ("postgres", 64): "pg_int8",
    ("mysql", 16): "my_smallint",
    ("mysql", 32): "my_int",
    ("mysql", 64): "my_bigint",
}
# name, width, nullable, declared interval
WIDTH_FIELDS = (
    ("rid", 64, False, (1, 5)),
    ("s", 16, True, (3, 7)),
    ("i", 32, True, (10, 20)),
    ("b", 64, True, (-9, 9)),
)
ROWS1 = "rows between 1 preceding and current row"
I32_MAX = (1 << 31) - 1


def _widths_item(target: str, body: str) -> dict:
    contract = json.loads(
        probe.aggregate_fixture(target, "X_aggregate_global", "bag")["contract"]
    )
    contract["sources"] = [
        probe._declared_source(
            target,
            "rows",
            "phase66 widths",
            [
                {
                    "name": name,
                    "column": name,
                    "representation": {
                        "storage": {"kind": WIDTH_KINDS[target, width]},
                        "nullable": nullable,
                        "domain": {
                            "kind": "int_range",
                            "min": str(low),
                            "max": str(high),
                        },
                    },
                }
                for name, width, nullable, (low, high) in WIDTH_FIELDS
            ],
        )
    ]
    return {
        "source": WIDTHS_HEADER.format(target=target) + body,
        "contract": probe.encoded(contract).decode(),
        "policy": "preserve_literals",
    }


def _windows_body(calls) -> str:
    lines = ["query result:", "    from rows", "    select:", "        record_id = rid"]
    for label, call, frame in calls:
        lines += [f"        {label} = {call} window:", "            order by:"]
        lines += ["                rid"] + ([f"            {frame}"] if frame else [])
    return "\n".join(lines) + "\n"


# label, call, frame, (PostgreSQL storage, MySQL storage), enclosed interval
MATRIX = (
    *(
        (
            f"{prefix}{name}",
            call.format(name),
            frame,
            {"s": ("pg_int2", "my_int"), "i": ("pg_int4", "my_bigint")}.get(
                name, ("pg_int8", "my_bigint")
            ),
            dict((n, r) for n, _, _, r in WIDTH_FIELDS)[name],
        )
        for name in ("s", "i", "b")
        for prefix, call, frame in (
            ("f", "first_value({})", ROWS1),
            ("l", "last_value({})", ROWS1),
            ("n", "nth_value({}, 2)", ROWS1),
            ("g", "lag({})", ""),
            ("d", "lead({})", ""),
        )
    ),
    ("s_null", "lag(s, 1, null)", "", ("pg_int2", "my_int"), (3, 7)),
    ("s_zero", "lag(s, 1, 0)", "", ("pg_int4", "my_int"), (0, 7)),
    ("s_six", "lead(s, 1, 100000)", "", ("pg_int4", "my_int"), (3, 100000)),
    ("s_eight", "lag(s, 1, 99999999)", "", ("pg_int4", "my_int"), (3, 99999999)),
    ("s_nine", "lag(s, 1, 999999999)", "", ("pg_int4", "my_bigint"), (3, 999999999)),
    ("s_ten", "lag(s, 1, 1000000000)", "", ("pg_int4", "my_bigint"), (3, 10**9)),
    ("s_big", "lag(s, 1, 10000000000)", "", ("pg_int8", "my_bigint"), (3, 10**10)),
    ("i_zero", "lag(i, 1, 0)", "", ("pg_int4", "my_bigint"), (0, 20)),
    ("i_max", "lag(i, 1, 2147483647)", "", ("pg_int4", "my_bigint"), (10, I32_MAX)),
    ("i_over", "lead(i, 1, 2147483648)", "", ("pg_int8", "my_bigint"), (10, 1 << 31)),
    ("b_zero", "lag(b, 1, 0)", "", ("pg_int8", "my_bigint"), (-9, 9)),
)


def _representations(outcome: Any) -> dict[str, dict]:
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    return {c["label"]: c["representation"] for c in document["columns"]}


def _int_representation(kind: str, low: int, high: int, nullable=True) -> dict:
    return {
        "storage": {"kind": kind},
        "nullable": nullable,
        "domain": {"kind": "int_range", "min": str(low), "max": str(high)},
    }


# Over the non-null rid, a NULL default is itself returned while an integer
# default never is, so only the first result may be NULL.
NULLABILITY = (
    ("r_null", "lag(rid, 1, null)", True),
    ("r_zero", "lag(rid, 1, 0)", False),
)


@pytest.mark.parametrize("target", TARGETS)
def test_the_value_window_width_matrix_is_each_target_reviewed_rule(target):
    calls = [(a, b, c) for a, b, c, *_ in MATRIX]
    calls += [(label, call, "") for label, call, _ in NULLABILITY]
    outcome = _build(_widths_item(target, _windows_body(calls)))
    published = _representations(outcome)
    side = TARGETS.index(target)
    for label, _call, _frame, kinds, (low, high) in MATRIX:
        assert published[label] == _int_representation(kinds[side], low, high), label
    wide = WIDTH_KINDS[target, 64]
    assert published["record_id"]["storage"] == {"kind": wide}
    assert published["r_null"] == _int_representation(wide, 1, 5, nullable=True)
    assert published["r_zero"] == _int_representation(wide, 0, 5, nullable=False)
    assert _pure(_observation(outcome.artifact))[0] is pure.Status.OK


CARRIED = """table first:
    from rows
    select:
        record_id = rid
        v = lag(s) window:
            order by:
                rid
query result:
    from first
    select:
        record_id
        v
"""
TWO_STAGE = """table first:
    from rows
    select:
        record_id = rid
        v = first_value(s) window:
            order by:
                rid
query result:
    from first
    select:
        record_id
        w = first_value(v) window:
            order by:
                record_id
"""
# A carry repeats no computation; a second window re-evaluates the carried
# result, which MySQL materialized as INT (display 11), so it becomes BIGINT.
PROPAGATION = {
    ("postgres", "carried"): ("v", "pg_int2"),
    ("mysql", "carried"): ("v", "my_int"),
    ("postgres", "two_stage"): ("w", "pg_int2"),
    ("mysql", "two_stage"): ("w", "my_bigint"),
}


def _public(outcome: Any) -> dict:
    return json.loads(serialize_project_sql_emission(outcome))


def _decodes(document: dict) -> str | None:
    try:
        probe.decode_public(probe.encoded(document))
    except ValueError as error:
        return str(error)
    return None


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("shape", ("carried", "two_stage"))
def test_carried_and_rewindowed_results_decode_in_every_consumer(target, shape):
    outcome = _build(_widths_item(target, CARRIED if shape == "carried" else TWO_STAGE))
    label, kind = PROPAGATION[target, shape]
    assert _representations(outcome)[label] == _int_representation(kind, 3, 7)
    assert _pure(_observation(outcome.artifact))[0] is pure.Status.OK
    document = _public(outcome)
    assert _decodes(document) is None
    column = document["columns"][1]
    stale = {"pg_int2": "pg_int4", "my_int": "my_smallint", "my_bigint": "my_int"}
    wrong_width = json.loads(json.dumps(document))
    wrong_width["columns"][1]["representation"]["storage"] = {"kind": stale[kind]}
    forged = [wrong_width]
    if shape == "carried":
        transport = column["correspondence"]["window_transport"]
        assert transport["function"] == "lag"
        wrong_producer = json.loads(json.dumps(document))
        wrong_producer["columns"][1]["correspondence"]["window_transport"][
            "function"
        ] = "lead"
        missing = json.loads(json.dumps(document))
        del missing["columns"][1]["correspondence"]["window_transport"]
        forged += [wrong_producer, missing]
    else:
        # The outer window's projection numbers after the named body's own.
        projection = column["correspondence"]["projection"]
        assert projection["kind"] == "window_projection"
        assert projection["position"] == 1
        wrong_port = json.loads(json.dumps(document))
        wrong_port["columns"][1]["correspondence"]["projection"]["position"] = 0
        forged.append(wrong_port)
    for item in forged:
        assert _decodes(item) is not None


@pytest.mark.parametrize("target", TARGETS)
def test_the_smallint_wide_offset_witness_publishes_each_target_rule(target):
    item = probe.fixture(target, "G_scan_row_domains", "partitioned_root")
    published = _representations(_build(item))
    if target == "postgres":
        expected = ("pg_int2", "pg_int2", "pg_int4")
    else:
        expected = ("my_smallint", "my_int", "my_bigint")
    assert published == {
        "id": _int_representation(expected[0], 0, 99, nullable=False),
        "low": _int_representation(expected[1], 0, 99),
        # A non-null value with an integer default is never NULL.
        "high": _int_representation(expected[2], 0, 999999999, nullable=False),
    }
    # The target oracle's physical types are the published storages' own codes.
    protocol = {
        "pg_int2": 21,
        "pg_int4": 23,
        "my_smallint": 2,
        "my_int": 3,
        "my_bigint": 8,
    }
    rows_, labels, physical, _ = cases.row_domain_expectation(
        target, "partitioned_root"
    )
    assert labels == ("id", "low", "high")
    assert physical == [protocol[kind] for kind in expected]
    assert sorted(row[2]["value"] for row in rows_) == ["1", "1", "999999999"]


def _with_window_result(artifact: Any, function: str, change) -> Any:
    def body_change(body):
        columns = []
        for column in body.columns:
            if type(column) is windowing.WindowColumn and column.function == function:
                image = column.column
                image = replace(image, realization=change(image.realization))
                column = replace(column, column=image)
            columns.append(column)
        return replace(
            body,
            columns=tuple(columns),
            window=replace(
                body.window,
                columns=tuple(c for c in columns if type(c) is windowing.WindowColumn),
            ),
        )

    return _with_stage(artifact, body_change)


@pytest.mark.parametrize("target", TARGETS)
def test_stale_or_false_window_result_claims_meet_the_independent_walk(target):
    artifact = _build(
        probe.fixture(target, "G_scan_row_domains", "partitioned_root")
    ).artifact
    small, medium, large = (
        ("pg_int2", "pg_int4", "pg_int8")
        if target == "postgres"
        else ("my_smallint", "my_int", "my_bigint")
    )
    low_kind = small if target == "postgres" else medium
    # `low` is first_value (value width), `high` is lag with its wide default.
    changes = (
        ("first_value", lambda r: replace(r, storage={"kind": large})),
        (
            "first_value",
            lambda r: replace(r, storage={"kind": low_kind, "unsigned": True}),
        ),
        ("lag", lambda r: replace(r, storage={"kind": small})),
        (
            "lag",
            lambda r: replace(
                r, storage={"kind": medium if target == "mysql" else large}
            ),
        ),
        (
            "lag",
            lambda r: replace(r, domain={"kind": "int_range", "min": "0", "max": "99"}),
        ),
        (
            "lag",
            lambda r: replace(
                r,
                domain={"kind": "int_range", "min": str(I64_MIN), "max": str(I64_MAX)},
            ),
        ),
    )
    if target == "mysql":
        changes += (("first_value", lambda r: replace(r, storage={"kind": small})),)
    for function, change in changes:
        drifted = _with_window_result(artifact, function, change)
        checked = verification.verify_project_sql_emission(drifted, artifact.request)
        assert "plan_ast_correspondence" in checked.issues, function


def _realization_record(document: dict, function: str) -> dict:
    """The serialized realization record of one window column's own result."""
    by_ref = {tuple(record["ref"]): record for record in document["records"]}
    column = next(
        r
        for r in document["records"]
        if r["ref"][0] == "window_column" and r["fields"]["function"] == function
    )
    image = by_ref[tuple(column["fields"]["column"])]
    return by_ref[tuple(image["fields"]["realization"])]


@pytest.mark.parametrize("target", TARGETS)
def test_stale_window_widths_are_refused_by_the_data_only_consumers(target):
    outcome = _build(probe.fixture(target, "G_scan_row_domains", "partitioned_root"))
    public = _public(outcome)
    assert _decodes(public) is None
    stale = {"pg_int4": "pg_int2", "my_bigint": "my_int"}
    high = public["columns"][2]["representation"]
    forged_public = json.loads(json.dumps(public))
    forged_public["columns"][2]["representation"]["storage"] = {
        "kind": stale[high["storage"]["kind"]]
    }
    assert _decodes(forged_public) == "window output published"
    document = _observation(outcome.artifact)
    for field, value in (
        ("storage", {"kind": stale[high["storage"]["kind"]]}),
        ("domain", {"kind": "int_range", "min": "0", "max": "99"}),
    ):
        forged = json.loads(json.dumps(document))
        _realization_record(forged, "lag")["fields"][field] = value
        status, detail = _pure(forged)
        assert status is not pure.Status.OK and detail is not None


# -- P: PostgreSQL navigation defaults and out-of-signed64 defaults ---------------


def _read(kind: str, low: int, high: int, **origin) -> Any:
    realization = rows.Realization(
        "Int",
        {"kind": kind},
        True,
        {"kind": "int_range", "min": str(low), "max": str(high)},
    )
    return rows.StageColumn(0, "c0", None, realization, **origin)


FIELD = {"field": object()}
WINDOW = {"window": object()}


@pytest.mark.parametrize(
    "family,kind,default,expected",
    (
        ("postgres", "pg_int2", None, "pg_int2"),
        ("postgres", "pg_int2", "NULL", "pg_int2"),
        ("postgres", "pg_int2", "0", "pg_int4"),
        ("postgres", "pg_int2", "100000", "pg_int4"),
        ("postgres", "pg_int4", "2147483647", "pg_int4"),
        ("postgres", "pg_int4", "2147483648", "pg_int8"),
        ("postgres", "pg_int8", "0", "pg_int8"),
        ("mysql", "my_smallint", "99999999", "my_int"),
        ("mysql", "my_smallint", "999999999", "my_bigint"),
        ("mysql", "my_int", None, "my_bigint"),
    ),
)
def test_the_owner_and_the_walk_agree_on_hand_derived_widths(
    family, kind, default, expected
):
    read = _read(kind, 3, 7, **FIELD)
    produced, problem = windowing.integer_value_result(family, read, default)
    assert problem is None and produced is not None
    derived = verification._window_integer_result(family, read, default)
    number = None if default in (None, "NULL") else int(default)
    low, high = (3, 7) if number is None else (min(3, number), max(7, number))
    enclosure = {"kind": "int_range", "min": str(low), "max": str(high)}
    assert produced == derived == ({"kind": expected}, enclosure)


@pytest.mark.parametrize("family", TARGETS)
@pytest.mark.parametrize("default", (str(I64_MAX + 1), str(I64_MIN - 1)))
def test_a_default_outside_signed64_is_refused_by_owner_and_walk(family, default):
    kind = "pg_int8" if family == "postgres" else "my_bigint"
    read = _read(kind, 3, 7, **FIELD)
    assert windowing.integer_value_result(family, read, default) == (
        None,
        ("PIE-B1002", "window_default_integer_out_of_signed64_range"),
    )
    with pytest.raises(ValueError):
        verification._window_integer_result(family, read, default)


# -- C3 and B1: MySQL carriers without a reviewed representation ------------------

# Generated carriers reach a later window only through a named table stage,
# whose MySQL CTE may be merged into an expression with its own display length.
COMPUTED = """table t:
    from rows
    select:
        record_id = rid
        bumped = rid + 1
query result:
    from t
    select:
        record_id
        w = first_value(bumped) window:
            order by:
                record_id
"""
LITERAL = """table t:
    from rows
    select:
        record_id = rid
        one = 1
query result:
    from t
    select:
        record_id
        w = lag(one) window:
            order by:
                record_id
"""
GROUPED = """table g:
    from rows
    group by:
        rid
    select:
        rid
        m = max(s)
query result:
    from g
    select:
        record_id = rid
        w = first_value(m) window:
            order by:
                rid
"""
ORIGIN_BLOCKED = (
    "PIE-B1002",
    "mysql_window_integer_result_origin_not_supported_in_phase66",
)


@pytest.mark.parametrize("body", (LITERAL, GROUPED))
def test_mysql_int_carriers_outside_the_reviewed_classes_are_blocked(body):
    blocked = _build(_widths_item("mysql", body))
    assert blocked.status == "BLOCKED" and blocked.artifact is None
    assert _refusal(blocked) == [ORIGIN_BLOCKED]
    assert _build(_widths_item("postgres", body)).status == "VERIFIED"


@pytest.mark.parametrize("target", TARGETS)
def test_an_arithmetic_window_value_stays_refused_before_emission(target):
    # The earlier semantic refusal is kept; no width rule is reached or needed.
    assert _refusal(_build(_widths_item(target, COMPUTED))) == [
        ("PIE-B1003", "semantic_result_unsuccessful"),
        ("PIE-B1003", "active_output_unavailable"),
    ]


def test_the_walk_refuses_an_unreviewed_mysql_carrier_class():
    for origin in (
        {},
        {"aggregate": object()},
        {"literal": object()},
        {**FIELD, **WINDOW},
    ):
        read = _read("my_int", 3, 7, **origin)
        assert windowing.integer_value_result("mysql", read, None) == (
            None,
            ORIGIN_BLOCKED,
        )
        with pytest.raises(ValueError):
            verification._window_integer_result("mysql", read, None)
    for origin in (FIELD, WINDOW):
        read = _read("my_signed_int", 3, 7, **origin)
        assert windowing.integer_value_result("mysql", read, None) == (
            None,
            ORIGIN_BLOCKED,
        )


BOOL_BLOCKED = (
    "PIE-B1002",
    "mysql_bool_window_result_representation_not_supported_in_phase66",
)
BOOL_CALLS = (
    ("first_value(flag)", ROWS1),
    ("last_value(flag)", ROWS1),
    ("nth_value(flag, 2)", ROWS1),
    ("lag(flag)", ""),
    ("lead(flag, 1, null)", ""),
)
CARRIED_BOOL = """table first:
    from rows
    select:
        record_id = id
        kept = flag
query result:
    from first
    select:
        record_id
        w = first_value(kept) window:
            order by:
                record_id
"""


@pytest.mark.parametrize("call,frame", BOOL_CALLS)
def test_mysql_bool_window_values_are_an_explicit_boundary(call, frame):
    blocked = _build(_item("mysql", _window(call, frame)))
    assert blocked.status == "BLOCKED" and blocked.artifact is None
    assert _refusal(blocked) == [BOOL_BLOCKED]
    assert _public(blocked)["status"] == "BLOCKED"
    assert _build(_item("postgres", _window(call, frame))).status == "VERIFIED"


def test_the_bool_boundary_follows_the_logical_type_not_the_source_spelling():
    blocked = _build(_item("mysql", CARRIED_BOOL))
    assert _refusal(blocked) == [BOOL_BLOCKED]
    # Neighbouring MySQL controls stay published: an Int window value and an
    # ordinary Bool column.
    assert (
        _build(_item("mysql", _window("first_value(id)", ROWS1))).status == "VERIFIED"
    )
    assert _build(probe.fixture("mysql")).status == "VERIFIED"


def _carrier_copy(family, function, arguments, retained):
    """The pre-G7 producer: every value result copied its carrier verbatim."""
    read = next(item.read for item in arguments if item.read is not None)
    carrier = read.realization
    return (
        rows.Realization(
            carrier.tag, carrier.storage, bool(retained[1]), carrier.domain
        ),
        None,
    )


@pytest.mark.parametrize("call,frame", BOOL_CALLS[:1] + BOOL_CALLS[3:4])
def test_a_forged_mysql_bool_window_success_is_refused_everywhere(
    call, frame, monkeypatch
):
    item = _item("mysql", _window(call, frame))
    monkeypatch.setattr(windowing, "result_realization", _carrier_copy)
    refused = _build(item)
    assert _refusal(refused) == [("PIE-B1008", "plan_ast_correspondence")]
    assert _public(refused)["status"] == "BLOCKED"
    # Fault injection in both producer checks yields a forged success, which
    # each independent data-only consumer still refuses.
    monkeypatch.setattr(
        verification,
        "_window_result_realization",
        lambda family, function, arguments, retained: _carrier_copy(
            family, function, arguments, retained
        )[0],
    )
    forged = _build(item)
    assert forged.status == "VERIFIED"
    assert _decodes(_public(forged)) == (
        "MySQL publishes no Bool window value result in Phase66"
    )
    observed = portable.export_emission_observation(
        forged.artifact, forged.artifact.request
    )
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert _pure(json.loads(observed.canonical_bytes)) == (
        pure.Status.INVALID_RELATION,
        "window value result representation",
    )
    correspondence = portable.verify_emission_observation(
        observed.canonical_bytes, forged.artifact, forged.artifact.request
    )
    assert correspondence.issues == ("document_invalid_relation",)


# -- denominator and the corrective contract ------------------------------------


def test_the_corrective_denominator_is_exact():
    assert len(cases.CASE_IDS) == 63
    for target, expected in (
        ("postgres", {"VERIFIED": 158, "INPUT_REJECTED": 3, "BLOCKED": 28}),
        ("mysql", {"VERIFIED": 154, "INPUT_REJECTED": 3, "BLOCKED": 32}),
    ):
        inputs = probe.generation_inputs(target)
        assert len(inputs) == 189
        statuses = Counter(
            probe.expected_status(item["id"], item["variant"], target)
            for item in inputs
        )
        assert statuses == expected


def test_the_corrective_contract_records_its_decisions_and_lifecycle():
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for phrase in (
        "R15-INT-OFFSET-V1",
        "window_frame_offset_out_of_signed64_range",
        "window_range_arithmetic_evidence_missing",
        "window_range_key_domain_out_of_storage_range",
        "window_range_boundary_out_of_signed64_range",
        "window_frame_offset_domain",
        "window_range_arithmetic",
        "R14-PG-NAVIGATION-RESULT-V1",
        "R15-MYSQL-WINDOW-RESULT-V1",
        "mysql_bool_window_result_representation_not_supported_in_phase66",
        "mysql_window_integer_result_origin_not_supported_in_phase66",
        "window_default_integer_out_of_signed64_range",
        "window_value_domain_out_of_storage_range",
        "It is a new support decision",
        "63 cases / 195 public documents per target",
        "PostgreSQL 162 VERIFIED / 4 INPUT_REJECTED / 29 BLOCKED",
        "MySQL 158 VERIFIED / 4 INPUT_REJECTED / 33 BLOCKED",
        "33 MiB = 34,603,008 bytes",
        "Phase66 remains `ACTIVE`",
        "Slice16 remains `NEXT / NOT IMPLEMENTED`",
        "not a numbered Slice",
    ):
        assert phrase in document, phrase
