"""Named header parameters in project SQL: placeholders, numbering, obligations.

A header parameter is a native placeholder under every literal policy. One
occurrence stream in rendering order is shared with bind-safe literal slots:
PostgreSQL reuses one ``$n`` per owner, MySQL writes one ``?`` per occurrence.
The unbound template keeps declared carriers and lists the checks that wait
for a binding; nothing in the SQL text depends on a value.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

import _pietto_sql_emission as probe
from _pietto_sql_query_parameters import PROTOCOL
from _pietto_sql_query_parameters import parameterized_case as _case
import _pietto_target_conformance_cases as conformance
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_ast import resource_limits
from pietto._project.project_sql_emission_cli import _render_verified
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project.project_sql_plan_expressions import ProjectSQLParameterRead
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
    outcome = _case(tmp_path, target, body, policy, protocol=False)[1]
    document = _document(outcome)
    if placeholders:
        assert document["status"] == "BLOCKED"
        assert [(b["code"], b["subject"]["detail"]) for b in document["blockers"]] == [
            ("PIE-B1004", "parameter_protocol_declaration_missing")
        ]
    else:
        # The independent consumer accepts the protocol-less template too.
        decoded = probe.decode_public(serialize_project_sql_emission(outcome))
        assert (decoded["format"], decoded["status"]) == (
            "pietto.sql-emission.v2",
            "VERIFIED",
        )
        assert decoded["sql"] == declared["sql"]


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


def _mutated(document: dict[str, Any], change) -> bytes:
    copy = json.loads(json.dumps(document))
    change(copy)
    return probe.encoded(copy)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_the_public_decoder_reads_a_v2_template_as_data(
    tmp_path: Path, target: str
) -> None:
    item = probe.fixture(target, "Q_query_parameters", "bind")
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    data = serialize_project_sql_emission(outcome)
    document = probe.decode_public(data)
    assert document["format"] == probe.PARAMETERIZED_FORMAT
    values = probe.bindings("Q_query_parameters", "bind")
    assert values is not None
    arguments = probe.decoded_arguments(document, values)
    assert values["low"] in arguments and None in arguments
    with pytest.raises(ValueError):
        probe.decoded_arguments(document)  # a template has no values of its own
    with pytest.raises(ValueError):
        probe.decoded_arguments(document, {**values, "low": True})

    def owner(d):
        d["parameter_uses"][0]["owner"] = {"kind": "parameter", "parameter": 1}

    def index(d):
        d["parameter_uses"][-1]["server_index"] += 1

    def unread(d):
        d["parameters"][0]["reads"].pop()

    def obligation(d):
        d["binding_obligations"][0]["kind"] = "unregistered_check"

    def requirement(d):
        d["requirements"] = [
            r for r in d["requirements"] if r["kind"] != "query_parameter"
        ]

    def blocked(d):
        d["status"] = "BLOCKED"

    def version(d):
        d["format"] = "pietto.sql-emission.v1"

    for change in (owner, index, unread, obligation, requirement, blocked, version):
        with pytest.raises(ValueError):
            probe.decode_public(_mutated(document, change))


UNREAD = """query result(low: Int not null, note: Text nullable):
    from rows
    where id > low
    select:
        display_text = text
"""


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_the_public_decoder_binds_an_unread_parameter_by_its_family_domain(
    tmp_path: Path, target: str
) -> None:
    checked, outcome = _case(tmp_path, target, UNREAD, "preserve_literals")
    assert checked.verified and outcome.status == "VERIFIED"
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [(p["name"], len(p["reads"])) for p in document["parameters"]] == [
        ("low", 1),
        ("note", 0),
    ]
    assert probe.decoded_arguments(document, {"low": 1, "note": None}) == (1,)
    # An unread parameter is still bound by its declared type.
    with pytest.raises(ValueError):
        probe.decoded_arguments(document, {"low": 1, "note": 5})
    # PostgreSQL text cannot hold NUL; MySQL text can.
    nul = {"low": 1, "note": "a\0b"}
    if target == "mysql":
        assert probe.decoded_arguments(document, nul) == (1,)
    else:
        with pytest.raises(ValueError):
            probe.decoded_arguments(document, nul)


# Result and post-aggregation positions. The bodies are the conformance bodies,
# so the native oracles and these exact bytes describe one template.
POSITIONS = probe.PARAMETER_POSITION_BODIES
POSITION_SQL = {
    ("grouped", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "s0"."order.id" AS "c0", "s0"."flag value" AS "c1", "s0"."text `""é" AS "c2", "s0"."amount value" AS "c3", "s0"."ratio value" AS "c4", ("s0"."order.id" * CAST($1 AS pg_catalog.int8)) AS "c5" FROM "public"."phase66 source é" AS "s0"), '
        '"p1" ("c0", "c1", "c2", "c3", "c4", "c5", "c6") AS (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c2" AS "c2", "t1"."c3" AS "c3", "t1"."c4" AS "c4", "t1"."c5" AS "c5", ("t1"."c0" + CAST($2 AS pg_catalog.int8)) AS "c6" FROM "p0" AS "t1"), '
        '"p2" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "t2"."c5" AS "c0", COUNT(*) AS "c1", COUNT("t2"."c6") AS "c2", AVG(CAST("t2"."c6" AS pg_catalog.float8)) AS "c3", MAX("t2"."c6") AS "c4" FROM "p1" AS "t2" GROUP BY "t2"."c5"), '
        '"p3" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "t3"."c0" AS "c0", "t3"."c1" AS "c1", "t3"."c2" AS "c2", "t3"."c3" AS "c3", "t3"."c4" AS "c4" FROM "p2" AS "t3" WHERE ("t3"."c1" > CAST($1 AS pg_catalog.int8))), '
        '"p4" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "t4"."c0" AS "c0", "t4"."c1" AS "c1", "t4"."c2" AS "c2", "t4"."c3" AS "c3", "t4"."c4" AS "c4", "t4"."c2" AS "c5" FROM "p3" AS "t4") '
        'SELECT "t0"."c0" AS "k", "t0"."c1" AS "c", "t0"."c2" AS "n", "t0"."c3" AS "a", "t0"."c4" AS "m" FROM "p4" AS "t0" ORDER BY "t0"."c5" DESC'
    ),
    ("grouped", "mysql"): (
        'WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `s0`.`order.id` AS `c0`, `s0`.`flag value` AS `c1`, `s0`.`text ``"é` AS `c2`, `s0`.`amount value` AS `c3`, `s0`.`ratio value` AS `c4`, (`s0`.`order.id` * CAST(? AS SIGNED)) AS `c5` FROM `phase66`.`phase66 source é` AS `s0`), '
        "`p1` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`) AS (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1`, `t1`.`c2` AS `c2`, `t1`.`c3` AS `c3`, `t1`.`c4` AS `c4`, `t1`.`c5` AS `c5`, (`t1`.`c0` + CAST(? AS SIGNED)) AS `c6` FROM `p0` AS `t1`), "
        "`p2` (`c0`, `c1`, `c2`, `c3`, `c4`) AS (SELECT `t2`.`c5` AS `c0`, COUNT(*) AS `c1`, COUNT(`t2`.`c6`) AS `c2`, AVG(CAST(`t2`.`c6` AS DOUBLE)) AS `c3`, MAX(`t2`.`c6`) AS `c4` FROM `p1` AS `t2` GROUP BY `t2`.`c5`), "
        "`p3` (`c0`, `c1`, `c2`, `c3`, `c4`) AS (SELECT `t3`.`c0` AS `c0`, `t3`.`c1` AS `c1`, `t3`.`c2` AS `c2`, `t3`.`c3` AS `c3`, `t3`.`c4` AS `c4` FROM `p2` AS `t3` WHERE (`t3`.`c1` > CAST(? AS SIGNED))), "
        "`p4` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `t4`.`c0` AS `c0`, `t4`.`c1` AS `c1`, `t4`.`c2` AS `c2`, `t4`.`c3` AS `c3`, `t4`.`c4` AS `c4`, `t4`.`c2` AS `c5` FROM `p3` AS `t4`) "
        "SELECT `t0`.`c0` AS `k`, `t0`.`c1` AS `c`, `t0`.`c2` AS `n`, `t0`.`c3` AS `a`, `t0`.`c4` AS `m` FROM `p4` AS `t0` ORDER BY `t0`.`c5` DESC"
    ),
    ("result", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "s0"."order.id" AS "c0", "s0"."flag value" AS "c1", "s0"."text `""é" AS "c2", "s0"."amount value" AS "c3", "s0"."ratio value" AS "c4" FROM "public"."phase66 source é" AS "s0" WHERE (strpos("s0"."text `""é", CAST($1 AS pg_catalog.text) COLLATE "C") > 0)), '
        '"p1" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c2" AS "c2", "t1"."c3" AS "c3", "t1"."c4" AS "c4", ROW_NUMBER() OVER (ORDER BY "t1"."c0" ASC) AS "c5" FROM "p0" AS "t1"), '
        '"p2" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "t2"."c0" AS "c0", "t2"."c1" AS "c1", "t2"."c2" AS "c2", "t2"."c3" AS "c3", "t2"."c4" AS "c4", "t2"."c5" AS "c5" FROM "p1" AS "t2" WHERE ("t2"."c5" <= (CAST($2 AS pg_catalog.int8) + CAST(1 AS pg_catalog.int8)))), '
        '"p3" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "t3"."c0" AS "c0", ("t3"."c0" * CAST($2 AS pg_catalog.int8)) AS "c1", lower(CAST($1 AS pg_catalog.text) COLLATE "C") AS "c2", "t3"."c5" AS "c3", "t3"."c0" AS "c4" FROM "p2" AS "t3") '
        'SELECT "t0"."c0" AS "id", "t0"."c1" AS "s", "t0"."c2" AS "u", "t0"."c3" AS "r" FROM "p3" AS "t0" ORDER BY "t0"."c1" ASC'
    ),
    ("result", "mysql"): (
        'WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`) AS (SELECT `s0`.`order.id` AS `c0`, `s0`.`flag value` AS `c1`, `s0`.`text ``"é` AS `c2`, `s0`.`amount value` AS `c3`, `s0`.`ratio value` AS `c4` FROM `phase66`.`phase66 source é` AS `s0` WHERE (INSTR(`s0`.`text ``"é`, CAST(? AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin) > 0)), '
        "`p1` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1`, `t1`.`c2` AS `c2`, `t1`.`c3` AS `c3`, `t1`.`c4` AS `c4`, ROW_NUMBER() OVER (ORDER BY `t1`.`c0` ASC) AS `c5` FROM `p0` AS `t1`), "
        "`p2` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `t2`.`c0` AS `c0`, `t2`.`c1` AS `c1`, `t2`.`c2` AS `c2`, `t2`.`c3` AS `c3`, `t2`.`c4` AS `c4`, `t2`.`c5` AS `c5` FROM `p1` AS `t2` WHERE (`t2`.`c5` <= (CAST(? AS SIGNED) + CAST(1 AS SIGNED)))), "
        "`p3` (`c0`, `c1`, `c2`, `c3`, `c4`) AS (SELECT `t3`.`c0` AS `c0`, (`t3`.`c0` * CAST(? AS SIGNED)) AS `c1`, LOWER(CAST(? AS CHAR CHARACTER SET utf8mb4) COLLATE utf8mb4_0900_bin) AS `c2`, `t3`.`c5` AS `c3`, `t3`.`c0` AS `c4` FROM `p2` AS `t3`) "
        "SELECT `t0`.`c0` AS `id`, `t0`.`c1` AS `s`, `t0`.`c2` AS `u`, `t0`.`c3` AS `r` FROM `p3` AS `t0` ORDER BY `t0`.`c1` ASC"
    ),
}
# (owner parameter per native use, obligations as (kind, parameters)).
POSITION_USES = {
    # k = id * low (LET), s = id + high (LET), then SATISFYING c > low.
    "grouped": (
        [0, 1, 0],
        [("int_range_representable", [0]), ("int_range_representable", [1])],
    ),
    # WHERE contains(text, label), QUALIFY r <= low + 1, s = id * low,
    # u = lower(label); the ORDER key id * low only matches s.
    "result": (
        [1, 0, 0, 1],
        [
            ("int_range_representable", [0]),
            ("int_range_representable", [0]),
            ("text_result_width", [1]),
        ],
    ),
}


@pytest.mark.parametrize("name", tuple(POSITIONS))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_result_and_aggregate_positions_emit_exact_sql(
    tmp_path: Path, target: str, name: str
) -> None:
    _, outcome = _case(tmp_path, target, POSITIONS[name], "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    assert document["format"] == "pietto.sql-emission.v2"
    assert document["sql"] == "".join(POSITION_SQL[name, target])
    owners, obligations = POSITION_USES[name]
    uses = document["parameter_uses"]
    assert [u["owner"] for u in uses] == [
        {"kind": "parameter", "parameter": owner} for owner in owners
    ]
    if target == "mysql":
        assert [u["server_index"] for u in uses] == list(range(1, len(owners) + 1))
    else:
        first: dict[int, int] = {}
        assert [u["server_index"] for u in uses] == [
            first.setdefault(owner, len(first) + 1) for owner in owners
        ]
    assert [
        (o["kind"], o["parameters"]) for o in document["binding_obligations"]
    ] == obligations
    # A read in an ORDER tree is matching only: no use, listed read or R04.
    assert not any(token in document["sql"].split("ORDER BY")[-1] for token in "$?")
    assert sum(len(p["reads"]) for p in document["parameters"]) == len(owners)
    assert [
        r["evidence"]
        for r in document["requirements"]
        if r["kind"] == "query_parameter"
    ] == [[{"parameter": owner}] for owner in owners]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_distinct_order_key_treats_a_read_as_a_constant_leaf(
    tmp_path: Path, target: str
) -> None:
    body = (
        "query result(low: Int not null):\n"
        "    from rows\n"
        "    select distinct:\n"
        "        id\n"
        "        s = id + low\n"
        "    order by:\n"
        "        id + low\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    head, tail = document["sql"].split(" ORDER BY ")
    assert head.count("$1" if target == "postgres" else "?") == 1
    assert tail == ('"t0"."c1" ASC' if target == "postgres" else "`t0`.`c1` ASC")
    assert len(document["parameter_uses"]) == 1


@pytest.mark.parametrize(
    ("key", "detail"),
    (
        ("id + high", "order_expression_requires_established_port"),
        # Outside a grouped query an output name is no ORDER key, as without
        # parameters.
        ("s", "order"),
    ),
    ids=("other_parameter", "output_name"),
)
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_an_order_key_matches_only_the_same_restated_parameter(
    tmp_path: Path, target: str, key: str, detail: str
) -> None:
    body = (
        "query result(low: Int not null, high: Int not null):\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        s = id + low\n"
        "    order by:\n"
        f"        {key}\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert document["status"] == "BLOCKED"
    assert [
        (b["code"], b["reason"], b["subject"]["detail"]) for b in document["blockers"]
    ] == [("PIE-B1003", "UNSUPPORTED_RULE", detail)]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_closed_builtin_value_arguments_take_parameters(
    tmp_path: Path, target: str
) -> None:
    body = (
        "query result(low: Int not null, label: Text nullable):\n"
        "    from rows\n"
        "    where contains(label, text) and starts_with(label, text)"
        " and ends_with(label, text)\n"
        "    select:\n"
        "        id\n"
        "        a = lower(label)\n"
        "        b = upper(label)\n"
        "        c = trim(label)\n"
        "        d = coalesce(label, text)\n"
        "        e = nullif(label, text)\n"
        "        f = nullif(text, label)\n"
        "        g = coalesce(low, id)\n"
        "        h = sign(low - id)\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    # Width follows the parameter except for nullif(text, label), whose result
    # is bounded by its first argument; only low - id needs an Int range.
    assert Counter(o["kind"] for o in document["binding_obligations"]) == Counter(
        {"text_result_width": 5, "int_range_representable": 1}
    )
    columns = {c["label"]: c["representation"]["domain"] for c in document["columns"]}
    assert columns["f"]["max_characters"] == 64
    assert columns["h"] == {"kind": "int_range", "min": "-1", "max": "1"}


@pytest.mark.parametrize("variant", tuple(probe.PARAMETER_POSITION_VARIANTS))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_conformance_bindings_cover_every_use_of_the_position_witness(
    tmp_path: Path, target: str, variant: str
) -> None:
    """Each registered witness binds every header parameter, and its native
    oracle has the template's width; the product binder accepts the same
    values (tests/test_execution_binding.py)."""
    item = probe.fixture(target, "Q_query_parameters", variant)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    binding = probe.bindings("Q_query_parameters", variant)
    assert binding is not None
    assert [p["name"] for p in document["parameters"]] == list(binding)
    records = conformance.parameter_records(document, binding)
    indices = {u["server_index"] for u in document["parameter_uses"]}
    assert len(records) == len(indices)
    first = {
        u["server_index"]: u["owner"]["parameter"] for u in document["parameter_uses"]
    }
    names = [document["parameters"][first[i]]["name"] for i in sorted(indices)]
    # The wire spelling of an Int or Text value is its decimal or exact text.
    assert [
        None if record == conformance.NULL else record["value"] for record in records
    ] == [None if binding[name] is None else str(binding[name]) for name in names]
    rows, labels, _ = conformance.parameter_expectation(target, variant)
    assert [c["label"] for c in document["columns"]] == list(labels)
    assert all(len(row) == len(labels) for row in rows)


WINDOWS = """query result(k: Int not null, d: Int not null, v: Int not null):
    from rows
    select:
        id
        a = lag(id, k, d) window:
            order by:
                id
        b = ntile(k) window:
            order by:
                id
        c = nth_value(id, k) window:
            order by:
                id
            rows between unbounded preceding and unbounded following
        e = lag(v) window:
            order by:
                id
"""
_CARRIED = {
    "postgres": (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8") AS '
        '(SELECT "s0"."order.id" AS "c0", "s0"."flag value" AS "c1", '
        '"s0"."text `""é" AS "c2", "s0"."amount value" AS "c3", '
        '"s0"."ratio value" AS "c4", '
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`, `c7`, `c8`) AS "
        "(SELECT `s0`.`order.id` AS `c0`, `s0`.`flag value` AS `c1`, "
        '`s0`.`text ``"é` AS `c2`, `s0`.`amount value` AS `c3`, '
        "`s0`.`ratio value` AS `c4`, "
    ),
}
WINDOW_SQL = {
    "postgres": _CARRIED["postgres"]
    + 'LAG("s0"."order.id", CAST(CAST($1 AS pg_catalog.int8) AS pg_catalog.int4), '
    'CAST($2 AS pg_catalog.int8)) OVER (ORDER BY "s0"."order.id" ASC) AS "c5", '
    "NTILE(CAST(CAST($1 AS pg_catalog.int8) AS pg_catalog.int4)) OVER "
    '(ORDER BY "s0"."order.id" ASC) AS "c6", '
    'NTH_VALUE("s0"."order.id", CAST(CAST($1 AS pg_catalog.int8) AS '
    'pg_catalog.int4)) OVER (ORDER BY "s0"."order.id" ASC ROWS BETWEEN UNBOUNDED '
    'PRECEDING AND UNBOUNDED FOLLOWING) AS "c7", '
    'LAG(CAST($3 AS pg_catalog.int8)) OVER (ORDER BY "s0"."order.id" ASC) AS "c8" '
    'FROM "public"."phase66 source é" AS "s0") SELECT "t1"."c0" AS "id", '
    '"t1"."c5" AS "a", "t1"."c6" AS "b", "t1"."c7" AS "c", "t1"."c8" AS "e" '
    'FROM "p0" AS "t1"',
    "mysql": _CARRIED["mysql"]
    + "LAG(`s0`.`order.id`, ?, CAST(? AS SIGNED)) OVER (ORDER BY `s0`.`order.id` "
    "ASC) AS `c5`, NTILE(?) OVER (ORDER BY `s0`.`order.id` ASC) AS `c6`, "
    "NTH_VALUE(`s0`.`order.id`, ?) OVER (ORDER BY `s0`.`order.id` ASC ROWS "
    "BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) AS `c7`, "
    "LAG(CAST(? AS SIGNED)) OVER (ORDER BY `s0`.`order.id` ASC) AS `c8` "
    "FROM `phase66`.`phase66 source é` AS `s0`) SELECT `t1`.`c0` AS `id`, "
    "`t1`.`c5` AS `a`, `t1`.`c6` AS `b`, `t1`.`c7` AS `c`, `t1`.`c8` AS `e` "
    "FROM `p0` AS `t1`",
}
# Native evidence (lanes4/s04w-probe-run): PostgreSQL's counts are int4 and its
# int8 default/value anchors give int8 results; MySQL refuses CAST(? AS SIGNED)
# as LAG/NTILE counts (1064) but returns a SIGNED anchor value as BIGINT.
WINDOW_COLUMNS = {
    "postgres": {
        "a": (False, "pg_int8", INT_MIN, INT_MAX),
        "b": (False, "pg_int4", "0", str((1 << 31) - 1)),
        "c": (True, "pg_int8", "-9007199254740993", "9007199254740993"),
        "e": (True, "pg_int8", INT_MIN, INT_MAX),
    },
    "mysql": {
        "a": (False, "my_bigint", INT_MIN, INT_MAX),
        "b": (False, "my_bigint", "0", INT_MAX),
        "c": (True, "my_bigint", "-9007199254740993", "9007199254740993"),
        "e": (True, "my_bigint", INT_MIN, INT_MAX),
    },
}


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_window_values_defaults_and_counts_are_placeholders(
    tmp_path: Path, target: str, policy: str
) -> None:
    _, outcome = _case(tmp_path, target, WINDOWS, policy)
    assert outcome.status == "VERIFIED", outcome.blockers
    document = _document(outcome)
    assert document["sql"] == WINDOW_SQL[target]
    uses = document["parameter_uses"]
    # Rendering order: k (offset), d (default), k (bucket), k (position), v.
    assert [u["owner"]["parameter"] for u in uses] == [0, 1, 0, 0, 2]
    assert [u["server_index"] for u in uses] == (
        [1, 2, 1, 1, 3] if target == "postgres" else [1, 2, 3, 4, 5]
    )
    assert {u["physical_type"] for u in uses} == {PLACEHOLDER[target]}
    reads = {p["name"]: p["reads"] for p in document["parameters"]}
    assert {name: [r["kind"] for r in refs] for name, refs in reads.items()} == {
        "k": ["window_argument"] * 3,
        "d": ["window_argument"],
        "v": ["window_argument"],
    }
    assert [
        (o["kind"], o["subject"], o["parameters"])
        for o in document["binding_obligations"]
    ] == [("structural_count_interval", ref, [0]) for ref in reads["k"]]
    requirements = [
        r for r in document["requirements"] if r["kind"] == "query_parameter"
    ]
    assert [r["evidence"] for r in requirements] == [
        [{"parameter": u["owner"]["parameter"]}] for u in uses
    ]
    columns = {c["label"]: c for c in document["columns"]}
    for label, (nullable, storage, low, high) in WINDOW_COLUMNS[target].items():
        representation = columns[label]["representation"]
        assert (columns[label]["nullable"], representation["storage"]["kind"]) == (
            nullable,
            storage,
        )
        assert (representation["domain"]["min"], representation["domain"]["max"]) == (
            low,
            high,
        )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_window_reads_count_toward_the_parameter_occurrence_limit(
    tmp_path: Path, target: str
) -> None:
    # WINDOWS renders five parameter occurrences on both targets.
    _, accepted = _case(
        tmp_path / "5", target, WINDOWS, "preserve_literals", limits={"parameters": 5}
    )
    assert accepted.status == "VERIFIED", accepted.blockers
    _, refused = _case(
        tmp_path / "4", target, WINDOWS, "preserve_literals", limits={"parameters": 4}
    )
    assert refused.status == "BLOCKED"
    # As for bind-safe slots, the refused allocation is reported with the limit.
    assert [(b.code, b.detail) for b in refused.blockers] == [
        ("PIE-B1008", "native_occurrence_allocation"),
        ("PIE-B1007", "parameter_occurrence_limit"),
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_the_public_decoder_reads_window_reads_and_count_obligations(
    tmp_path: Path, target: str
) -> None:
    _, outcome = _case(tmp_path, target, WINDOWS, "preserve_literals")
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    values = {"k": 1, "d": -1, "v": 3}
    # Rendering order k (offset), d (default), k (bucket), k (position), v.
    assert probe.decoded_arguments(document, values) == (
        (1, -1, 3) if target == "postgres" else (1, -1, 1, 1, 3)
    )

    def depends(d):
        d["binding_obligations"][0]["parameters"] = [1]

    def subject(d):
        d["binding_obligations"][0]["subject"] = {"kind": "expression", "position": 0}

    def unknown(d):
        d["binding_obligations"][0]["kind"] = "unregistered_check"

    for change in (depends, subject, unknown):
        with pytest.raises(ValueError):
            probe.decode_public(_mutated(document, change))


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_parameter_offset_may_be_null_and_shares_the_where_numbering(
    tmp_path: Path, target: str
) -> None:
    body = (
        "query result(k: Int not null):\n"
        "    from rows\n"
        "    where id > k\n"
        "    select:\n"
        "        id\n"
        "        z = lag(id, k, 0) window:\n"
        "            order by:\n"
        "                id\n"
        "        o = lag(id, 0) window:\n"
        "            order by:\n"
        "                id\n"
        "        n = lead(id, k) window:\n"
        "            order by:\n"
        "                id\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    assert outcome.status == "VERIFIED", outcome.blockers
    document = _document(outcome)
    columns = {c["label"]: c for c in document["columns"]}
    # A parameter offset is never assumed to be 0: only a default keeps non-NULL.
    assert [columns[label]["nullable"] for label in ("z", "o", "n")] == [
        False,
        False,
        True,
    ]
    uses = document["parameter_uses"]
    sql = document["sql"].encode()
    tokens = [sql[u["range"]["start"] : u["range"]["end"]].decode() for u in uses]
    assert len(uses) == 3
    if target == "postgres":
        assert tokens == ["$1"] * 3 and document["sql"].count("$1") == 3
    else:
        assert tokens == ["?"] * 3 and document["sql"].count("?") == 3
        assert [u["server_index"] for u in uses] == [1, 2, 3]
    assert [o["kind"] for o in document["binding_obligations"]] == [
        "structural_count_interval"
    ] * 2
    # Plan order: expression reads, then window argument reads.
    assert [r["kind"] for r in document["parameters"][0]["reads"]] == [
        "expression",
        "window_argument",
        "window_argument",
    ]


WINDOW_REFUSALS = {
    "text_value": (
        "label: Text not null",
        "lag(label)",
        ("PIE-B1003", "window_parameter_value_kind_not_realized_yet"),
    ),
    "bool_value": (
        "flag2: Bool not null",
        "lag(flag2)",
        ("PIE-B1003", "window_parameter_value_kind_not_realized_yet"),
    ),
    "text_default": (
        "label: Text not null",
        "lag(text, 1, label)",
        ("PIE-B1003", "window_default_literal_kind_not_realized_yet"),
    ),
    "float_value": ("r: Float not null", "lag(r)", None),
}


@pytest.mark.parametrize(
    ("header", "call", "expected"), WINDOW_REFUSALS.values(), ids=tuple(WINDOW_REFUSALS)
)
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_unmeasured_window_parameter_kinds_are_refused(
    tmp_path: Path,
    target: str,
    header: str,
    call: str,
    expected: tuple[str, str] | None,
) -> None:
    body = (
        f"query result({header}):\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        f"        w = {call} window:\n"
        "            order by:\n"
        "                id\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    if expected is None:
        assert outcome.status == "VERIFIED", outcome.blockers
        column = {c["label"]: c for c in _document(outcome)["columns"]}["w"]
        assert column["representation"]["storage"]["kind"] == (
            "pg_float8" if target == "postgres" else "my_double"
        )
        return
    assert outcome.status == "BLOCKED"
    assert [(b.code, b.detail) for b in outcome.blockers] == [expected]


# The counts of WINDOWS rendered as value placeholders: consistent bytes.
FORGED_COUNT = {
    "postgres": 'LAG("s0"."order.id", CAST($1 AS pg_catalog.int8), CAST($2',
    "mysql": "LAG(`s0`.`order.id`, CAST(? AS SIGNED), CAST(? AS SIGNED))",
}


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_verifiers_reject_forged_window_parameters(
    tmp_path: Path, target: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pietto._project import project_sql_emission_portable as portable
    from pietto._project import project_sql_emission_windows as windowing
    from pietto._project.project_sql_emission_ast import SQLRowQuery, row_value_roots
    from pietto._project.project_sql_emission_rendering import render_row_sql

    checked, outcome = _case(tmp_path, target, WINDOWS, "preserve_literals")
    artifact = outcome.artifact
    assert artifact is not None
    query = artifact.ast
    assert type(query) is SQLRowQuery
    # The closed observation schema has no parameter read; export refuses it.
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OUTSIDE_SCHEMA

    def refused(owner: Any, name: str, value: Any) -> bool:
        original = getattr(owner, name)
        object.__setattr__(owner, name, value)
        try:
            return not verify_project_sql_emission(artifact, artifact.request).verified
        finally:
            object.__setattr__(owner, name, original)

    # MySQL refuses CAST(? AS SIGNED) as a LAG or NTILE count, and PostgreSQL's
    # count is int4: the verifier re-derives the count tokens on its own.
    assert not refused(artifact, "rendered", render_row_sql(query))
    with monkeypatch.context() as patch:
        patch.setattr(windowing, "COUNT_ROLES", frozenset())
        forged = render_row_sql(query)
    assert FORGED_COUNT[target] in forged.sql.decode()
    assert refused(artifact, "rendered", forged)

    # Each parameter leaf claiming another valid-looking realization.
    leaves = {
        root.role: root.parameter
        for root in row_value_roots(query)
        if type(root) is windowing.WindowArgument and root.parameter is not None
    }
    offset, value = leaves["offset"].realization, leaves["value"].realization
    for leaf, realization in (
        (leaves["offset"], replace(offset, domain=dict(offset.domain, min="-1"))),
        (leaves["default"], leaves["bucket"].realization),
        (
            leaves["value"],
            replace(
                value,
                domain=dict(value.domain, min="0", max="100"),
                proven_int_range=(0, 100),
            ),
        ),
    ):
        assert refused(leaf, "realization", realization)
    assert verify_project_sql_emission(artifact, artifact.request).verified

    # A lost plan read, and a read naming another `Int not null` parameter.
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    roles = {a.role.value: a for a in plan.window_arguments if a.parameter is not None}
    for argument, parameter in (
        (roles["default"], None),
        (roles["offset"], plan.parameters[1]),
    ):
        original = argument.parameter
        object.__setattr__(argument, "parameter", parameter)
        again = verify_project_sql_plan(
            plan,
            checked.completed,
            checked.analysis_bundle,
            checked.selected_owner,
            literal_policy=checked.literal_policy,
        )
        object.__setattr__(argument, "parameter", original)
        assert again.issues == (ProjectSQLPlanVerificationIssue.QUERY_PARAMETERS,)


JOINED = """query result(k: Int not null):
    from lhs
    inner join rhs as r:
        from lhs
        on lhs.id == r.id
    select:
        a = lhs.id
        w = lag(lhs.id, k, k) window:
            order by:
                lhs.id
"""
NAMED = """query result(k: Int not null):
    from rows
    select:
        id
        w = ntile(k) window composed
        x = lag(id, k) window composed
    window composed = base
    window base:
        order by:
            id desc
"""
SHAPES = {
    ("joined", "postgres"): 'LAG("t0"."c0", CAST(CAST($1 AS pg_catalog.int8) AS '
    'pg_catalog.int4), CAST($1 AS pg_catalog.int8)) OVER (ORDER BY "t0"."c0" ASC)',
    ("joined", "mysql"): "LAG(`t0`.`c0`, ?, CAST(? AS SIGNED)) OVER "
    "(ORDER BY `t0`.`c0` ASC)",
    ("named", "postgres"): "NTILE(CAST(CAST($1 AS pg_catalog.int8) AS "
    'pg_catalog.int4)) OVER "w0" AS "c5", LAG("s0"."order.id", CAST(CAST($1 AS '
    'pg_catalog.int8) AS pg_catalog.int4)) OVER "w0" AS "c6"',
    ("named", "mysql"): "NTILE(?) OVER `w0` AS `c5`, LAG(`s0`.`order.id`, ?) "
    "OVER `w0` AS `c6`",
}


@pytest.mark.parametrize("shape", ("joined", "named"))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_window_parameters_over_a_join_and_a_named_window(
    tmp_path: Path, target: str, shape: str
) -> None:
    if shape == "named":
        _, outcome = _case(tmp_path, target, NAMED, "preserve_literals")
    else:
        item = probe.join_witness(target, JOINED, policy="preserve_literals")
        contract = json.loads(item["contract"])
        contract["environment"].append(
            {
                "key": "parameter_protocol",
                "scope": "statement",
                "value": PROTOCOL[target],
            }
        )
        _, outcome = probe.build_case(
            tmp_path / target,
            item["source"],
            probe.encoded(contract).decode(),
            "preserve_literals",
        )
    assert outcome.status == "VERIFIED", outcome.blockers
    document = _document(outcome)
    assert SHAPES[shape, target] in document["sql"]
    # The joined default is a value, not a count: only counts are obligations.
    assert [o["kind"] for o in document["binding_obligations"]] == [
        "structural_count_interval"
    ] * (1 if shape == "joined" else 2)


LET_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1", "c2", "c3") AS (SELECT "s0"."%s""" AS "c0", '
        '"s0"."?""" AS "c1", "s0"."%s" AS "c2", "s0"."neighbor" AS "c3" FROM '
        '"public"."phase66 native" AS "s0" WHERE (("s0"."%s""" > CAST($1 AS '
        'pg_catalog.int8)) AND ("s0"."%s" <> CAST($2 AS pg_catalog.int8)))), '
        '"p1" ("c0", "c1", "c2") AS (SELECT "t1"."c0" AS "c0", CAST($3 AS '
        'pg_catalog.text) COLLATE "C" AS "c1", (CAST($1 AS pg_catalog.int8) + '
        'CAST($4 AS pg_catalog.int8)) AS "c2" FROM "p0" AS "t1"), "p2" ("c0", '
        '"c1", "c2") AS (SELECT "s1"."c0" AS "c0", "s1"."c1" AS "c1", "s1"."c2" '
        'AS "c2" FROM "p1" AS "s1" WHERE ("s1"."c0" > CAST($1 AS '
        'pg_catalog.int8))) SELECT "t3"."c0" AS "id", "t3"."c1" AS "echo", '
        '"t3"."c2" AS "above" FROM "p2" AS "t3"'
    ),
    "mysql": (
        'WITH `p0` (`c0`, `c1`, `c2`, `c3`) AS (SELECT `s0`.`%s"` AS `c0`, '
        '`s0`.`?"` AS `c1`, `s0`.`%s` AS `c2`, `s0`.`neighbor` AS `c3` FROM '
        '`phase66`.`phase66 native` AS `s0` WHERE ((`s0`.`%s"` > CAST(? AS '
        "SIGNED)) AND (`s0`.`%s` <> CAST(? AS SIGNED)))), `p1` (`c0`, `c1`, "
        "`c2`) AS (SELECT `t1`.`c0` AS `c0`, CAST(? AS CHAR CHARACTER SET "
        "utf8mb4) COLLATE utf8mb4_0900_bin AS `c1`, (CAST(? AS SIGNED) + CAST(? "
        "AS SIGNED)) AS `c2` FROM `p0` AS `t1`), `p2` (`c0`, `c1`, `c2`) AS "
        "(SELECT `s1`.`c0` AS `c0`, `s1`.`c1` AS `c1`, `s1`.`c2` AS `c2` FROM "
        "`p1` AS `s1` WHERE (`s1`.`c0` > CAST(? AS SIGNED))) SELECT `t3`.`c0` "
        "AS `id`, `t3`.`c1` AS `echo`, `t3`.`c2` AS `above` FROM `p2` AS `t3`"
    ),
}


def _let_case(directory: Path, target: str, limit: int | None = None) -> Any:
    item = probe.fixture(target, "Q_query_parameters", "let_bind")
    contract = json.loads(item["contract"])
    if limit is not None:
        contract["environment"].append(
            {
                "key": "resource_limits",
                "scope": "statement",
                "value": {"parameters": limit},
            }
        )
    return probe.build_case(
        directory, item["source"], probe.encoded(contract).decode(), item["policy"]
    )


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_reads_across_let_stages_share_one_numbering(
    tmp_path: Path, target: str
) -> None:
    """A relation let and the entry body read the same header: PostgreSQL
    keeps one `$n` per parameter across CTE stages, MySQL one `?` per read."""
    checked, outcome = _let_case(tmp_path, target)
    assert checked.verified and outcome.status == "VERIFIED"
    document = _document(outcome)
    assert document["sql"] == LET_SQL[target]
    owners = [
        ("parameter", 0),
        ("slot", 0),
        ("parameter", 1),
        ("parameter", 0),
        ("slot", 1),
        ("parameter", 0),
    ]
    uses = document["parameter_uses"]
    assert [
        (u["owner"]["kind"], u["owner"][u["owner"]["kind"]]) for u in uses
    ] == owners
    assert [u["server_index"] for u in uses] == (
        [1, 2, 3, 1, 4, 1] if target == "postgres" else [1, 2, 3, 4, 5, 6]
    )
    assert [(p["name"], len(p["reads"])) for p in document["parameters"]] == [
        ("low", 3),
        ("label", 1),
    ]
    # `above = low + 1` is checked by each binding; a let reads both
    # parameters, so the dependence names both (an over-approximation).
    assert [(o["kind"], o["parameters"]) for o in document["binding_obligations"]] == [
        ("int_range_representable", [0, 1])
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_let_column_carries_its_parameters_to_a_later_check(
    tmp_path: Path, target: str
) -> None:
    body = (
        "query result(low: Int not null, high: Int not null):\n"
        "    let a:\n"
        "        from rows\n"
        "        select:\n"
        "            display_text = text\n"
        "            k = low * 2\n"
        "    from a\n"
        "    select:\n"
        "        display_text\n"
        "        z = k + high\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    # `low * 2` in the let reads `low`; `k + high` reads `low` only through
    # the let's stage column.
    assert [(o["kind"], o["parameters"]) for o in document["binding_obligations"]] == [
        ("int_range_representable", [0]),
        ("int_range_representable", [0, 1]),
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_placeholders_of_every_let_stage_count_toward_one_statement_limit(
    tmp_path: Path, target: str
) -> None:
    _, at_limit = _let_case(tmp_path / "six", target, 6)
    assert at_limit.status == "VERIFIED"
    _, over = _let_case(tmp_path / "five", target, 5)
    assert over.status == "BLOCKED"
    assert [(b.code, b.detail) for b in over.blockers] == [
        ("PIE-B1008", "native_occurrence_allocation"),
        ("PIE-B1007", "parameter_occurrence_limit"),
    ]


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_one_statement_admits_at_most_65535_placeholders(
    tmp_path: Path, target: str
) -> None:
    """D70.07: the protocol ceiling of both databases bounds every statement,
    also under a larger declared limit. No statement that large is built: the
    real read is allocated at the request's own limit and one past it."""
    checked, outcome = _let_case(tmp_path, target, 65536)
    assert outcome.status == "VERIFIED"
    limit = resource_limits(outcome.artifact.request)["parameters"]
    assert limit == 65535
    read = next(
        e for e in checked.plan.expressions if type(e) is ProjectSQLParameterRead
    )
    occurrence = (read, parameters.PHYSICAL[target][read.parameter.tag])
    assert len(parameters.allocate_uses(target, (occurrence,) * limit, limit)) == limit
    with pytest.raises(ValueError, match="limit"):
        parameters.allocate_uses(target, (occurrence,) * (limit + 1), limit)


def test_the_plan_verifier_rederives_a_read_inside_a_let(tmp_path: Path) -> None:
    checked, outcome = _let_case(tmp_path, "postgres")
    artifact = outcome.artifact
    assert artifact is not None
    # The emission verifier re-reads every stage's occurrence order.
    swapped = replace(artifact, parameter_uses=artifact.parameter_uses[::-1])
    assert not verify_project_sql_emission(swapped, swapped.request).verified
    plan = checked.plan
    assert type(plan) is ProjectSQLPlan
    selected = checked.selected_owner
    (read,) = [
        e
        for e in plan.expressions
        if type(e) is ProjectSQLParameterRead
        and e.site.owner is not selected
        and e.parameter.ordinal == 1
    ]
    # A well-formed swap to the other header entry of the same query.
    object.__setattr__(read, "parameter", plan.parameters[0])
    again = verify_project_sql_plan(
        plan,
        checked.completed,
        checked.analysis_bundle,
        selected,
        literal_policy=checked.literal_policy,
    )
    assert not again.verified


LET_COLUMN = """query result(low: Int not null):
    let a:
        from rows
        select:
            record_id = id
            k = low * 2
    from a
    group by:
        k
    select:
        k
        n = count()
    order by:
        k
"""


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_let_column_computed_from_a_parameter_is_an_ordinary_column(
    tmp_path: Path, target: str
) -> None:
    """Group and order keys refuse a read of the header, but the entry body
    may group and order by a let column that a parameter computes."""
    checked, outcome = _case(tmp_path, target, LET_COLUMN, "preserve_literals")
    document = _document(outcome)
    assert checked.verified and outcome.status == "VERIFIED", document
    assert [p["name"] for p in document["parameters"]] == ["low"]
    assert len(document["parameter_uses"]) == 1
    assert [(o["kind"], o["parameters"]) for o in document["binding_obligations"]] == [
        ("int_range_representable", [0])
    ]


LET_WINDOW = """query result(low: Int not null, step: Int not null):
    let a:
        from rows
        where id > low
        select:
            id
            b = lag(id, step) window:
                order by:
                    id
    from a
    select:
        id
        b
        z = id + low
"""


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_window_count_inside_a_let_checks_only_its_own_parameter(
    tmp_path: Path, target: str
) -> None:
    """A count read in a relation let names only its own parameter, while an
    operation over a let column names every parameter a let reads."""
    _, outcome = _case(tmp_path, target, LET_WINDOW, "preserve_literals")
    assert outcome.status == "VERIFIED", outcome.blockers
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert [
        (o["kind"], o["subject"]["kind"], o["parameters"])
        for o in document["binding_obligations"]
    ] == [
        ("structural_count_interval", "window_argument", [1]),
        ("int_range_representable", "expression", [0, 1]),
    ]
    assert probe.decoded_arguments(probe.decode_public(raw), {"low": 1, "step": 2}) == (
        (1, 2) if target == "postgres" else (1, 2, 1)
    )


LET_READS = """query result(low: Int not null, high: Int not null):
    let a:
        from rows
        where id > low
        select:
            id
    let b:
        from rows
        where exists a and id < high + low
        select:
            n = count()
    from rows
    where id >= high and id in a and id <= scalar b.n and not exists a
    select:
        record_id = id
"""


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_lets_read_by_exists_scalar_and_in_carry_the_header(
    tmp_path: Path, target: str
) -> None:
    """A let that reads the header and is read only by `exists`, `scalar` or
    `in` keeps its placeholders in the one statement stream, in rendering
    order, and its checks name the parameters it reads."""
    _, outcome = _case(tmp_path, target, LET_READS, "preserve_literals")
    raw = serialize_project_sql_emission(outcome)
    document = json.loads(raw)
    assert outcome.status == "VERIFIED", document
    plain = document["sql"].replace('"', "").replace("`", "")
    assert plain.index("EXISTS (SELECT 1 FROM p1 AS e0)") < plain.index(
        "IN (SELECT e1.c0 FROM p1 AS e1)"
    )
    assert "NOT EXISTS (SELECT 1 FROM p1 AS e3)" in plain
    # Let a reads low, let b reads high then low, the entry body reads high.
    assert [
        (u["owner"]["parameter"], u["server_index"]) for u in document["parameter_uses"]
    ] == (
        [(0, 1), (1, 2), (0, 1), (1, 2)]
        if target == "postgres"
        else [(0, 1), (1, 2), (0, 3), (1, 4)]
    )
    assert [(o["kind"], o["parameters"]) for o in document["binding_obligations"]] == [
        ("int_range_representable", [0, 1])
    ]
    assert probe.decoded_arguments(probe.decode_public(raw), {"low": 1, "high": 5}) == (
        (1, 5) if target == "postgres" else (1, 5, 1, 5)
    )
