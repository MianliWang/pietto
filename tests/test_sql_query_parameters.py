"""Named header parameters in project SQL: placeholders, numbering, obligations.

A header parameter is a native placeholder under every literal policy. One
occurrence stream in rendering order is shared with bind-safe literal slots:
PostgreSQL reuses one ``$n`` per owner, MySQL writes one ``?`` per occurrence.
The unbound template keeps declared carriers and lists the checks that wait
for a binding; nothing in the SQL text depends on a value.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from _pietto_sql_query_parameters import parameterized_case as _case
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_cli import _render_verified
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerificationIssue,
    verify_project_sql_plan,
)

INT_MIN, INT_MAX = str(-(1 << 63)), str((1 << 63) - 1)
PLACEHOLDER = {"postgres": "pg_int8", "mysql": "my_signed_int"}


def _document(outcome) -> dict[str, Any]:
    return json.loads(serialize_project_sql_emission(outcome))


REUSE = """query result(low: Int not null, flag2: Bool nullable):
    from rows
    let:
        next = low + 1
    where id > low and id != 7 and id >= low and flag2 is null
    select:
        display_text = text
        again = low
"""


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_one_native_stream_reuses_dollar_n_and_repeats_question_marks(
    tmp_path: Path, target: str, policy: str
) -> None:
    checked, outcome = _case(tmp_path, target, REUSE, policy)
    assert checked.verified and outcome.status == "VERIFIED"
    document = _document(outcome)
    bound = policy == "bind_safe_literals"
    # Rendering order: low, [1], low, [7], low, flag2, low.
    owners = [
        ("parameter", 0),
        *([("slot", 0)] if bound else []),
        ("parameter", 0),
        *([("slot", 1)] if bound else []),
        ("parameter", 0),
        ("parameter", 1),
        ("parameter", 0),
    ]
    uses = document["parameter_uses"]
    assert [
        (u["owner"]["kind"], u["owner"][u["owner"]["kind"]]) for u in uses
    ] == owners
    indices = [u["server_index"] for u in uses]
    if target == "mysql":
        assert indices == list(range(1, len(owners) + 1))
        assert document["sql"].count("?") == len(owners)
    else:
        first: dict[tuple[str, int], int] = {}
        for owner in owners:
            first.setdefault(owner, len(first) + 1)
        assert indices == [first[owner] for owner in owners]
        assert sorted(set(indices)) == list(range(1, len(first) + 1))
    sql = document["sql"].encode()  # ranges are UTF-8 byte offsets
    for use in uses:
        token = sql[use["range"]["start"] : use["range"]["end"]].decode()
        assert token == ("?" if target == "mysql" else f"${use['server_index']}")
    assert [u["physical_type"] for u in uses if u["owner"].get("parameter") == 0] == [
        PLACEHOLDER[target]
    ] * 4
    assert len(document["fixed_values"]) == (2 if bound else 0)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_v2_document_describes_the_unbound_template(
    tmp_path: Path, target: str
) -> None:
    _, outcome = _case(tmp_path, target, REUSE, "preserve_literals")
    document = _document(outcome)
    assert document["format"] == "pietto.sql-emission.v2"
    parameters = document["parameters"]
    assert [
        (p["parameter"], p["name"], p["tag"], p["nullable"], len(p["reads"]))
        for p in parameters
    ] == [(0, "low", "Int", False, 4), (1, "flag2", "Bool", True, 1)]
    assert all(read["kind"] == "expression" for p in parameters for read in p["reads"])
    assert [(o["kind"], o["parameters"]) for o in document["binding_obligations"]] == [
        ("int_range_representable", [0])
    ]
    columns = {c["label"]: c for c in document["columns"]}
    assert columns["again"]["representation"]["domain"] == {
        "kind": "int_range",
        "min": INT_MIN,
        "max": INT_MAX,
    }
    requirements = [
        r for r in document["requirements"] if r["kind"] == "query_parameter"
    ]
    assert len(requirements) == len(document["parameter_uses"])
    assert {r["rule"] for r in requirements} == {"R04"}
    text = _render_verified(document)
    assert "\nparameters (2):\n" in text and "\nbinding_obligations (1):\n" in text


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_unparameterized_queries_keep_the_v1_document(
    tmp_path: Path, target: str
) -> None:
    body = "query result:\n    from rows\n    where id > 1\n    select:\n        id\n"
    _, outcome = _case(tmp_path, target, body, "bind_safe_literals")
    document = _document(outcome)
    assert document["format"] == "pietto.sql-emission.v1"
    assert "parameters" not in document and "binding_obligations" not in document
    assert [sorted(use) for use in document["parameter_uses"]] == [
        ["physical_type", "range", "server_index", "slot", "use"]
    ]


FULL = (INT_MIN, INT_MAX)
# let bindings, obligations (kind, parameters), and the Int domain of `next`
# (None for Text, whose width a binding fixes).
OBLIGATIONS = {
    "sum": ("next = low + 1", [("int_range_representable", [0])], FULL),
    "negation": ("next = -low", [("int_range_representable", [0])], FULL),
    "zero_product": ("next = low * 0", [], ("0", "0")),
    "int_conditional": ("next = low if flag else 4", [], FULL),
    "text_conditional": (
        "next = label if flag else text",
        [("text_result_width", [1])],
        None,
    ),
    # A let reaches a later let as a stage column; its obligation still names
    # the parameter it depends on.
    "sum_through_let": (
        "a = low * 2\n        next = a + 1",
        [("int_range_representable", [0])] * 2,
        FULL,
    ),
    "text_through_let": (
        "a = label\n        next = a if flag else text",
        [("text_result_width", [1])],
        None,
    ),
}


@pytest.mark.parametrize(
    ("let", "expected", "domain"), OBLIGATIONS.values(), ids=tuple(OBLIGATIONS)
)
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_value_sensitive_checks_wait_for_a_binding(
    tmp_path: Path,
    target: str,
    let: str,
    expected: list[tuple[str, list[int]]],
    domain: tuple[str, str] | None,
) -> None:
    body = (
        "query result(low: Int not null, label: Text not null):\n"
        "    from rows\n"
        f"    let:\n        {let}\n"
        "    select:\n"
        "        display_text = text\n"
        "        next\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    assert [
        (o["kind"], o["parameters"]) for o in document["binding_obligations"]
    ] == expected
    column = {c["label"]: c for c in document["columns"]}["next"]
    actual = column["representation"]["domain"]
    if domain is None:
        # The width is fixed by each binding, never by a placeholder value.
        assert actual["max_characters"] is None
    else:
        # Only a range a binding can move keeps the full carrier.
        assert (actual["min"], actual["max"]) == domain


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_an_obligation_names_every_parameter_it_depends_on(
    tmp_path: Path, target: str
) -> None:
    body = (
        "query result(low: Int not null, high: Int not null):\n"
        "    from rows\n"
        "    let:\n        a = low\n"
        "    select:\n"
        "        display_text = text\n"
        "        z = a + high\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    assert [(o["kind"], o["parameters"]) for o in document["binding_obligations"]] == [
        ("int_range_representable", [0, 1])
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_unread_parameters_still_emit_the_v2_template(
    tmp_path: Path, target: str
) -> None:
    body = "query result(low: Int not null):\n    from rows\n    select:\n"
    body += "        record_id = id\n"
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    assert document["format"] == "pietto.sql-emission.v2"
    assert [(p["name"], p["reads"]) for p in document["parameters"]] == [("low", [])]
    assert document["parameter_uses"] == document["binding_obligations"] == []
    assert _render_verified(document).startswith("pietto.sql-emission.v2 VERIFIED")


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_text_parameters_compare_and_project_with_unbound_widths(
    tmp_path: Path, target: str
) -> None:
    body = (
        "query result(label: Text nullable):\n"
        "    from rows\n"
        '    where text == label and text like label and text in (label, "x")\n'
        "    select:\n"
        "        display_text = text\n"
        "        copy = label\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    copy = {c["label"]: c for c in document["columns"]}["copy"]
    assert copy["nullable"] is True
    assert copy["representation"]["domain"]["max_characters"] is None
    assert document["binding_obligations"] == []
    anchor = (
        'CAST($1 AS pg_catalog.text) COLLATE "C"'
        if target == "postgres"
        else "CAST(? AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin"
    )
    assert document["sql"].count(anchor) == 4


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_parameter_needs_the_declared_parameter_protocol(
    tmp_path: Path, target: str
) -> None:
    _, outcome = _case(tmp_path, target, REUSE, "preserve_literals", protocol=False)
    document = _document(outcome)
    assert document["format"] == "pietto.sql-emission.v1"
    assert document["status"] == "BLOCKED"
    assert [(b["code"], b["subject"]["detail"]) for b in document["blockers"]] == [
        ("PIE-B1004", "parameter_protocol_declaration_missing")
    ]


ROW_LET = "    let:\n        k = 1\n    select:\n        record_id = id\n        k\n"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    ("clauses", "policy", "placeholders"),
    (
        ("    select:\n        record_id = id\n", "preserve_literals", False),
        (ROW_LET, "preserve_literals", False),
        (ROW_LET, "bind_safe_literals", True),
        (
            "    let:\n        n = low + 1\n    select:\n        record_id = id\n",
            "preserve_literals",
            True,
        ),
    ),
    ids=("plain", "row_let", "row_let_bound", "let_read"),
)
def test_the_protocol_is_needed_exactly_when_a_placeholder_renders(
    tmp_path: Path, target: str, clauses: str, policy: str, placeholders: bool
) -> None:
    """An unread header renders no placeholder, so it needs no protocol."""
    body = "query result(low: Int not null):\n    from rows\n" + clauses
    declared = _document(_case(tmp_path / "declared", target, body, policy)[1])
    assert declared["status"] == "VERIFIED"
    assert bool(declared["parameter_uses"]) is placeholders
    document = _document(_case(tmp_path, target, body, policy, protocol=False)[1])
    if placeholders:
        assert document["status"] == "BLOCKED"
        assert [(b["code"], b["subject"]["detail"]) for b in document["blockers"]] == [
            ("PIE-B1004", "parameter_protocol_declaration_missing")
        ]
    else:
        assert (document["format"], document["status"]) == (
            "pietto.sql-emission.v2",
            "VERIFIED",
        )
        assert document["sql"] == declared["sql"]


def test_verifiers_reject_a_forged_parameter_image(tmp_path: Path) -> None:
    checked, outcome = _case(tmp_path, "postgres", REUSE, "preserve_literals")
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    reordered = replace(artifact, parameter_uses=artifact.parameter_uses[::-1])
    assert not verify_project_sql_emission(reordered, reordered.request).verified

    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    object.__setattr__(plan, "parameters", plan.parameters[::-1])
    again = verify_project_sql_plan(
        plan,
        checked.completed,
        checked.analysis_bundle,
        checked.selected_owner,
        literal_policy=checked.literal_policy,
    )
    assert again.issues == (ProjectSQLPlanVerificationIssue.QUERY_PARAMETERS,)
