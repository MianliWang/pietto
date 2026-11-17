"""Named header parameters in project SQL: placeholders, numbering, obligations.

A header parameter is a native placeholder under every literal policy. One
occurrence stream in rendering order is shared with bind-safe literal slots:
PostgreSQL reuses one ``$n`` per owner, MySQL writes one ``?`` per occurrence.
The unbound template keeps declared carriers and lists the checks that wait
for a binding; nothing in the SQL text depends on a value.
"""

from __future__ import annotations

import contextlib
import errno
import io
import itertools
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, NamedTuple

import pytest

from _pietto_plan_profiles import _database, _profile
import _pietto_sql_emission as probe
from _pietto_sql_query_parameters import PROTOCOL
from _pietto_sql_query_parameters import parameterized_case as _case
from _pietto_sql_query_parameters import (
    MYSQL_TYPED_OPEN,
    MYSQL_TYPED_REFUSED,
    typed_case,
)
import _pietto_target_conformance_cases as conformance
from pietto import _batch_output as batch_output
from pietto import cli
from pietto._project import project_sql_emission_cli as emission_cli
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_sql_emission import serialize_project_sql_emission
from pietto._project.project_sql_emission_ast import resource_limits
from pietto._project.project_sql_emission_cli import _render_verified
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project.project_sql_plan_expressions import ProjectSQLParameterRead
from pietto._project.project_sql_plan_target_assessment import (
    prepare_project_sql_target_request,
)
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerificationIssue,
    verify_project_sql_plan,
)
from pietto.compiler import compile_all_sql, compile_sql

INT_MIN, INT_MAX = str(-(1 << 63)), str((1 << 63) - 1)
PLACEHOLDER = {"postgres": "pg_int8", "mysql": "my_signed_int"}


def _document(outcome) -> dict[str, Any]:
    return json.loads(serialize_project_sql_emission(outcome))


REUSE = """query result(low: Int, flag2: Bool | None):
    from rows
    let next = low + 1
    where id > low and id != 7 and id >= low and flag2 is None
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
        "query result(low: Int, label: Text):\n"
        "    from rows\n"
        + "".join(f"    let {binding}\n" for binding in let.split("\n        "))
        + "    select:\n"
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
        "query result(low: Int, high: Int):\n"
        "    from rows\n"
        "    let a = low\n"
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
    body = "query result(low: Int):\n    from rows\n    select:\n"
    body += "        record_id = id\n"
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    assert document["format"] == "pietto.sql-emission.v2"
    assert [(p["name"], p["reads"]) for p in document["parameters"]] == [("low", [])]
    assert document["parameter_uses"] == document["binding_obligations"] == []
    assert _render_verified(document).startswith("pietto.sql-emission.v2 VERIFIED")


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_an_unread_parameter_keeps_the_template_outside_the_observation(
    tmp_path: Path, target: str
) -> None:
    """The private observation has no parameter; it never drops an unread one."""
    import _pietto_sql_emission_portable as portable

    clauses = "    from rows\n    select:\n        record_id = id\n"
    template = _case(
        tmp_path / "template", target, "query result(low: Int):\n" + clauses
    )[1].artifact
    twin = _case(tmp_path / "twin", target, "query result:\n" + clauses)[1].artifact
    assert template is not None and twin is not None
    assert template.request.plan.parameters and not twin.request.plan.parameters
    assert template.rendered.sql == twin.rendered.sql
    observed = portable.export_emission_observation(template, template.request)
    assert observed == portable.EmissionObservation(
        portable.ObservationStatus.OUTSIDE_SCHEMA
    )
    # The parameter-free twin's coherent document never stands in for it.
    document = portable.export_emission_observation(twin, twin.request)
    assert document.status is portable.ObservationStatus.OK
    assert (
        portable.verify_emission_observation(
            document.canonical_bytes, twin, twin.request
        ).issues
        == ()
    )
    assert portable.verify_emission_observation(
        document.canonical_bytes, template, template.request
    ).issues == ("outside_schema",)


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_text_parameters_compare_and_project_with_unbound_widths(
    tmp_path: Path, target: str
) -> None:
    body = (
        "query result(label: Text | None):\n"
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
def test_a_float_parameter_compares_as_a_constant_on_both_targets(
    tmp_path: Path, target: str
) -> None:
    """A header parameter reads no row, so even a MySQL Float `==` against it
    cannot become a join or semijoin key; every bound -0.0 keeps its own bits."""
    body = (
        "query result(p: Float):\n"
        "    from rows\n"
        "    where ratio == p and ratio <= p\n"
        "    select:\n"
        "        r = ratio\n"
    )
    _, outcome = _case(tmp_path, target, body, "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    anchor = (
        "CAST($1 AS pg_catalog.float8)" if target == "postgres" else "CAST(? AS DOUBLE)"
    )
    assert document["sql"].count(anchor) == 2
    for value in (-0.0, 0.0):
        assert parameters.value_valid("Float", value, target)
    # F8: binding identity is bitwise while the comparison law is value equality.
    assert not parameters.same_value(-0.0, 0.0) and -0.0 == 0.0


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


ROW_LET = "    let k = 1\n    select:\n        record_id = id\n        k\n"


@pytest.mark.parametrize("target", ("postgres", "mysql"))
@pytest.mark.parametrize(
    ("clauses", "policy", "placeholders"),
    (
        ("    select:\n        record_id = id\n", "preserve_literals", False),
        (ROW_LET, "preserve_literals", False),
        (ROW_LET, "bind_safe_literals", True),
        (
            "    let n = low + 1\n    select:\n        record_id = id\n",
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
    body = "query result(low: Int):\n    from rows\n" + clauses
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


UNREAD = """query result(low: Int, note: Text | None):
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
        "`p1` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1`, `t1`.`c2` AS `c2`, `t1`.`c3` AS `c3`, `t1`.`c4` AS `c4`, CAST(ROW_NUMBER() OVER (ORDER BY `t1`.`c0` ASC) AS SIGNED) AS `c5` FROM `p0` AS `t1`), "
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
        "query result(low: Int):\n"
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
        "query result(low: Int, high: Int):\n"
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
        "query result(low: Int, label: Text | None):\n"
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


WINDOWS = """query result(k: Int, d: Int, v: Int):
    from rows
    select:
        id
        a = lag(id, k, d) window(order by id)
        b = ntile(k) window(order by id)
        c = nth_value(id, k) window(order by id rows between unbounded preceding and unbounded following)
        e = lag(v) window(order by id)
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
    "ASC) AS `c5`, CAST(NTILE(?) OVER (ORDER BY `s0`.`order.id` ASC) AS SIGNED) AS `c6`, "
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
        "query result(k: Int):\n"
        "    from rows\n"
        "    where id > k\n"
        "    select:\n"
        "        id\n"
        "        z = lag(id, k, 0) window(order by id)\n"
        "        o = lag(id, 0) window(order by id)\n"
        "        n = lead(id, k) window(order by id)\n"
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
        "label: Text",
        "lag(label)",
        ("PIE-B1003", "window_parameter_value_kind_not_realized_yet"),
    ),
    "bool_value": (
        "flag2: Bool",
        "lag(flag2)",
        ("PIE-B1003", "window_parameter_value_kind_not_realized_yet"),
    ),
    "text_default": (
        "label: Text",
        "lag(text, 1, label)",
        ("PIE-B1003", "window_default_literal_kind_not_realized_yet"),
    ),
    "float_value": ("r: Float", "lag(r)", None),
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
        f"        w = {call} window(order by id)\n"
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
    import _pietto_sql_emission_portable as portable
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

    # A lost plan read, and a read naming another non-null `Int` parameter.
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


JOINED = """query result(k: Int):
    from lhs
    let r = rhs
    inner join r on lhs.id == r.id
    select:
        a = lhs.id
        w = lag(lhs.id, k, k) window(order by lhs.id)
"""
NAMED = """query result(k: Int):
    from rows
    let composed = window base
    let base = window(order by id desc)
    select:
        id
        w = ntile(k) window composed
        x = lag(id, k) window composed
"""
SHAPES = {
    ("joined", "postgres"): 'LAG("t0"."c0", CAST(CAST($1 AS pg_catalog.int8) AS '
    'pg_catalog.int4), CAST($1 AS pg_catalog.int8)) OVER (ORDER BY "t0"."c0" ASC)',
    ("joined", "mysql"): "LAG(`t0`.`c0`, ?, CAST(? AS SIGNED)) OVER "
    "(ORDER BY `t0`.`c0` ASC)",
    ("named", "postgres"): "NTILE(CAST(CAST($1 AS pg_catalog.int8) AS "
    'pg_catalog.int4)) OVER "w0" AS "c5", LAG("s0"."order.id", CAST(CAST($1 AS '
    'pg_catalog.int8) AS pg_catalog.int4)) OVER "w0" AS "c6"',
    ("named", "mysql"): "CAST(NTILE(?) OVER `w0` AS SIGNED) AS `c5`, "
    "LAG(`s0`.`order.id`, ?) OVER `w0` AS `c6`",
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
        "query result(low: Int, high: Int):\n"
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


LET_COLUMN = """query result(low: Int):
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


LET_WINDOW = """query result(low: Int, step: Int):
    let a:
        from rows
        where id > low
        select:
            id
            b = lag(id, step) window(order by id)
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


LET_READS = """query result(low: Int, high: Int):
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


# Cross-feature templates: a computed parameter key under a window over the
# grouped output and a QUALIFY, and one parameter read as a LET value, a window
# count and a QUALIFY operand under an ORDER key through a LET and a LIMIT.
CROSS = {
    "grouped_window": """query result(low: Int):
    from rows
    let k = id * low
    group by:
        k
    select:
        k
        n = count()
        r = row_number() window(order by n desc)
    qualify:
        r <= low
""",
    "window_count_qualify": """query result(step: Int, fill: Int | None):
    from rows
    let s = id * step
    select:
        id
        a = lag(id, step, fill) window(order by id)
    qualify:
        a > step
    order by:
        s desc
    limit 3
""",
}
CROSS_SQL = {
    ("grouped_window", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "s0"."order.id" AS "c0", "s0"."flag value" AS "c1", "s0"."text `""é" AS "c2", "s0"."amount value" AS "c3", "s0"."ratio value" AS "c4", ("s0"."order.id" * CAST($1 AS pg_catalog.int8)) AS "c5" FROM "public"."phase66 source é" AS "s0"), '
        '"p1" ("c0", "c1") AS (SELECT "t1"."c5" AS "c0", COUNT(*) AS "c1" FROM "p0" AS "t1" GROUP BY "t1"."c5"), '
        '"p2" ("c0", "c1", "c2") AS (SELECT "t2"."c0" AS "c0", "t2"."c1" AS "c1", ROW_NUMBER() OVER (ORDER BY "t2"."c1" DESC) AS "c2" FROM "p1" AS "t2"), '
        '"p3" ("c0", "c1", "c2") AS (SELECT "t3"."c0" AS "c0", "t3"."c1" AS "c1", "t3"."c2" AS "c2" FROM "p2" AS "t3" WHERE ("t3"."c2" <= CAST($1 AS pg_catalog.int8))) '
        'SELECT "t4"."c0" AS "k", "t4"."c1" AS "n", "t4"."c2" AS "r" FROM "p3" AS "t4"'
    ),
    ("grouped_window", "mysql"): (
        'WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `s0`.`order.id` AS `c0`, `s0`.`flag value` AS `c1`, `s0`.`text ``"é` AS `c2`, `s0`.`amount value` AS `c3`, `s0`.`ratio value` AS `c4`, (`s0`.`order.id` * CAST(? AS SIGNED)) AS `c5` FROM `phase66`.`phase66 source é` AS `s0`), '
        "`p1` (`c0`, `c1`) AS (SELECT `t1`.`c5` AS `c0`, COUNT(*) AS `c1` FROM `p0` AS `t1` GROUP BY `t1`.`c5`), "
        "`p2` (`c0`, `c1`, `c2`) AS (SELECT `t2`.`c0` AS `c0`, `t2`.`c1` AS `c1`, CAST(ROW_NUMBER() OVER (ORDER BY `t2`.`c1` DESC) AS SIGNED) AS `c2` FROM `p1` AS `t2`), "
        "`p3` (`c0`, `c1`, `c2`) AS (SELECT `t3`.`c0` AS `c0`, `t3`.`c1` AS `c1`, `t3`.`c2` AS `c2` FROM `p2` AS `t3` WHERE (`t3`.`c2` <= CAST(? AS SIGNED))) "
        "SELECT `t4`.`c0` AS `k`, `t4`.`c1` AS `n`, `t4`.`c2` AS `r` FROM `p3` AS `t4`"
    ),
    ("window_count_qualify", "postgres"): (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT "s0"."order.id" AS "c0", "s0"."flag value" AS "c1", "s0"."text `""é" AS "c2", "s0"."amount value" AS "c3", "s0"."ratio value" AS "c4", ("s0"."order.id" * CAST($1 AS pg_catalog.int8)) AS "c5" FROM "public"."phase66 source é" AS "s0"), '
        '"p1" ("c0", "c1", "c2", "c3", "c4", "c5", "c6") AS (SELECT "t1"."c0" AS "c0", "t1"."c1" AS "c1", "t1"."c2" AS "c2", "t1"."c3" AS "c3", "t1"."c4" AS "c4", "t1"."c5" AS "c5", LAG("t1"."c0", CAST(CAST($1 AS pg_catalog.int8) AS pg_catalog.int4), CAST($2 AS pg_catalog.int8)) OVER (ORDER BY "t1"."c0" ASC) AS "c6" FROM "p0" AS "t1"), '
        '"p2" ("c0", "c1", "c2", "c3", "c4", "c5", "c6") AS (SELECT "t2"."c0" AS "c0", "t2"."c1" AS "c1", "t2"."c2" AS "c2", "t2"."c3" AS "c3", "t2"."c4" AS "c4", "t2"."c5" AS "c5", "t2"."c6" AS "c6" FROM "p1" AS "t2" WHERE ("t2"."c6" > CAST($1 AS pg_catalog.int8))), '
        '"p3" ("c0", "c1", "c2") AS (SELECT "t3"."c0" AS "c0", "t3"."c6" AS "c1", "t3"."c5" AS "c2" FROM "p2" AS "t3") '
        'SELECT "t0"."c0" AS "id", "t0"."c1" AS "a" FROM "p3" AS "t0" ORDER BY "t0"."c2" DESC LIMIT 3'
    ),
    ("window_count_qualify", "mysql"): (
        'WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`) AS (SELECT `s0`.`order.id` AS `c0`, `s0`.`flag value` AS `c1`, `s0`.`text ``"é` AS `c2`, `s0`.`amount value` AS `c3`, `s0`.`ratio value` AS `c4`, (`s0`.`order.id` * CAST(? AS SIGNED)) AS `c5` FROM `phase66`.`phase66 source é` AS `s0`), '
        "`p1` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`) AS (SELECT `t1`.`c0` AS `c0`, `t1`.`c1` AS `c1`, `t1`.`c2` AS `c2`, `t1`.`c3` AS `c3`, `t1`.`c4` AS `c4`, `t1`.`c5` AS `c5`, LAG(`t1`.`c0`, ?, CAST(? AS SIGNED)) OVER (ORDER BY `t1`.`c0` ASC) AS `c6` FROM `p0` AS `t1`), "
        "`p2` (`c0`, `c1`, `c2`, `c3`, `c4`, `c5`, `c6`) AS (SELECT `t2`.`c0` AS `c0`, `t2`.`c1` AS `c1`, `t2`.`c2` AS `c2`, `t2`.`c3` AS `c3`, `t2`.`c4` AS `c4`, `t2`.`c5` AS `c5`, `t2`.`c6` AS `c6` FROM `p1` AS `t2` WHERE (`t2`.`c6` > CAST(? AS SIGNED))), "
        "`p3` (`c0`, `c1`, `c2`) AS (SELECT `t3`.`c0` AS `c0`, `t3`.`c6` AS `c1`, `t3`.`c5` AS `c2` FROM `p2` AS `t3`) "
        "SELECT `t0`.`c0` AS `id`, `t0`.`c1` AS `a` FROM `p3` AS `t0` ORDER BY `t0`.`c2` DESC LIMIT 3"
    ),
}
# (owner parameter per native use, obligations as (kind, parameters)).
CROSS_USES = {
    "grouped_window": ([0, 0], [("int_range_representable", [0])]),
    "window_count_qualify": (
        [0, 0, 1, 0],
        [("int_range_representable", [0]), ("structural_count_interval", [0])],
    ),
}


@pytest.mark.parametrize("name", tuple(CROSS))
@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_cross_feature_templates_emit_exact_sql(
    tmp_path: Path, target: str, name: str
) -> None:
    _, outcome = _case(tmp_path, target, CROSS[name], "preserve_literals")
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    assert document["sql"] == "".join(CROSS_SQL[name, target])
    owners, obligations = CROSS_USES[name]
    uses = document["parameter_uses"]
    assert [u["owner"] for u in uses] == [
        {"kind": "parameter", "parameter": owner} for owner in owners
    ]
    first: dict[int, int] = {}
    assert [u["server_index"] for u in uses] == (
        list(range(1, len(owners) + 1))
        if target == "mysql"
        else [first.setdefault(owner, len(first) + 1) for owner in owners]
    )
    assert [
        (o["kind"], o["parameters"]) for o in document["binding_obligations"]
    ] == obligations


@pytest.mark.parametrize("target", ("postgres", "mysql"))
def test_a_narrow_operation_over_a_parameter_read_is_proved_statically(
    tmp_path: Path, target: str
) -> None:
    """`nullif(id, low)` keeps an int4 id's carrier and range, so PostgreSQL
    computes its negation and its sum with id in bigint, proved without a
    binding; `id + low` is already bigint and still waits for one. MySQL
    computes all three as signed 64-bit, as before."""
    body = (
        "query result(low: Int):\n"
        "    from rows\n"
        "    select:\n"
        "        display_text = text\n"
        "        negated = -nullif(id, low)\n"
        "        summed = nullif(id, low) + id\n"
        "        bound = id + low\n"
    )
    item = probe.parameterized_fixture(target, body, "preserve_literals")
    contract = json.loads(item["contract"])
    contract["sources"][0]["fields"][0]["representation"]["storage"] = {
        "kind": "pg_int4" if target == "postgres" else "my_int"
    }
    contract["sources"][0]["fields"][0]["representation"]["domain"] = {
        "kind": "int_range",
        "min": "0",
        "max": "5",
    }
    _, outcome = probe.build_case(
        tmp_path, item["source"], probe.encoded(contract).decode()
    )
    document = _document(outcome)
    assert outcome.status == "VERIFIED", document
    columns = {c["label"]: c["representation"] for c in document["columns"]}
    assert [columns[name]["storage"] for name in ("negated", "summed", "bound")] == [
        {"kind": "pg_int8" if target == "postgres" else "my_signed_int"}
    ] * 3
    assert [
        (columns[name]["domain"]["min"], columns[name]["domain"]["max"])
        for name in ("negated", "summed")
    ] == [("-2147483647", "2147483648"), ("-4294967296", "4294967294")]
    # Only `bound` (expression 10) keeps a per-binding range proof.
    assert [
        (o["kind"], o["parameters"], o["subject"])
        for o in document["binding_obligations"]
    ] == [("int_range_representable", [0], {"kind": "expression", "position": 10})]
    if target == "mysql":
        assert "(-NULLIF(`s0`.`order.id`, CAST(? AS SIGNED)))" in document["sql"]
        return
    assert (
        '(-CAST(NULLIF("s0"."order.id", CAST($1 AS pg_catalog.int8))'
        ' AS pg_catalog.int8)) AS "negated", '
        '(CAST(NULLIF("s0"."order.id", CAST($1 AS pg_catalog.int8))'
        ' AS pg_catalog.int8) + "s0"."order.id") AS "summed"'
    ) in document["sql"]


def test_concat_of_a_binding_width_text_has_no_result_bound(tmp_path: Path) -> None:
    """`concat` is as wide as all its arguments together, so a Text whose
    width each binding fixes leaves it unbounded, as for `replace` (PostgreSQL:
    MySQL project SQL refuses every `concat`)."""
    body = (
        "query result(label: Text):\n"
        "    let kept:\n"
        "        from rows\n"
        "        select:\n"
        "            id\n"
        "            echo = label\n"
        "    from kept\n"
        "    select:\n"
        '        joined = concat(echo, "x")\n'
    )
    _, outcome = _case(tmp_path, "postgres", body)
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [(b.code, b.detail) for b in outcome.blockers] == [
        ("PIE-B1004", "text_concat_result_bound_missing")
    ]


TYPED_WHERE = (
    ' WHERE (((("s0"."ts" >= CAST($1 AS pg_catalog.timestamp))'
    ' AND ("s0"."d2" = CAST($2 AS pg_catalog.date)))'
    ' AND ("s0"."u" = CAST($3 AS pg_catalog.uuid)))'
    ' AND ("s0"."money" >= CAST($4 AS pg_catalog.numeric(9,2))))'
)
TYPED_REFUSAL = (
    "Keep this declaration in check/plan or select an artifact using the forms "
    "reviewed for the requested target. Do not relabel the target or source "
    "carrier to bypass this refusal."
)


def test_typed_parameters_cast_to_their_source_carrier_on_postgresql(
    tmp_path: Path,
) -> None:
    """A Decimal(p, s), Date, Timestamp or UUID read is a
    placeholder in the compared column's own carrier, a Decimal one with its
    declared precision and scale; it has no binding obligation."""
    checked, outcome = typed_case(tmp_path, "postgres")
    assert checked.verified and outcome.status == "VERIFIED"
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert document["format"] == "pietto.sql-emission.v2"
    assert TYPED_WHERE in document["sql"]
    assert [
        (p["name"], p["tag"], p["nullable"], len(p["reads"]))
        for p in document["parameters"]
    ] == [
        ("since", "Timestamp", False, 1),
        ("day", "Date", True, 1),
        ("key", "UUID", False, 1),
        ("floor", "Decimal", False, 1),
    ]
    assert [u["physical_type"] for u in document["parameter_uses"]] == [
        "pg_timestamp",
        "pg_date",
        "pg_uuid",
        "pg_numeric",
    ]
    assert document["binding_obligations"] == []
    artifact = outcome.artifact
    assert artifact is not None
    reads = [
        e
        for e in artifact.request.plan.expressions
        if type(e) is ProjectSQLParameterRead
    ]
    assert [(r.parameter.tag, r.parameter.decimal) for r in reads] == [
        ("Timestamp", None),
        ("Date", None),
        ("UUID", None),
        ("Decimal", (9, 2)),
    ]


@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "query result(floor: Decimal(10, 2)):\n    from rows\n"
            "    where money >= floor\n    select:\n        id\n",
            [("PIE-B1005", "decimal_comparison_parameter_conflict")],
        ),
        (
            "query result(floor: Decimal(9, 2)):\n    from rows\n"
            "    select:\n        id\n        total = money + floor\n",
            [("PIE-B1003", "decimal_direct_source_operands_required")],
        ),
        (
            "query result(floor: Decimal(9, 2)):\n    from rows\n"
            "    select:\n        id\n        total = money * floor\n",
            [("PIE-B1003", "decimal_direct_source_operands_required")],
        ),
    ),
    ids=("other_precision", "same_shape_arithmetic", "parameter_multiplication"),
)
def test_a_decimal_parameter_keeps_the_existing_decimal_laws(
    tmp_path: Path, body: str, expected: list[tuple[str, str]]
) -> None:
    """A Decimal(p, s) parameter compares only with a Decimal of the same
    (p, s) and, like any non-source Decimal, is no arithmetic operand."""
    _, outcome = typed_case(tmp_path, "postgres", body)
    assert outcome.status == "BLOCKED"
    assert [(b.code, b.detail) for b in outcome.blockers] == expected


@pytest.mark.parametrize(
    ("body", "columns"),
    (
        (
            "query result(since: Timestamp, day: Date | None, key: UUID, "
            "floor: Decimal(9, 2)):\n    from rows\n"
            "    where since <= ts and day == d2 and key == u and floor <= money\n"
            "    select:\n        id\n",
            [14, 32, 50, 61],
        ),
        (
            "query result(low: Int, day: Date | None):\n    from rows\n"
            "    where id > low\n    select:\n        id\n",
            [24],
        ),
    ),
    ids=("read", "unread"),
)
def test_mysql_refuses_each_typed_parameter_at_its_declaration(
    tmp_path: Path, body: str, columns: list[int]
) -> None:
    """Outside its cells (S09), each MySQL Decimal, Date, Timestamp or UUID
    declaration, read or not, is PIE-B1003 at its own span before any
    placeholder is allocated; the other parameters keep theirs."""
    checked, outcome = typed_case(tmp_path, "mysql", body)
    assert checked.verified and outcome.status == "BLOCKED"
    document = _document(outcome)
    assert [
        (
            b["code"],
            b["reason"],
            b["subject"],
            b["suggestion"],
            b["location"]["line"],
            b["location"]["column"],
        )
        for b in document["blockers"]
    ] == [
        (
            "PIE-B1003",
            "UNSUPPORTED_RULE",
            {
                "reference": {"kind": "selected_plan", "position": 0},
                "detail": "query_parameter_type_not_admitted_on_target",
            },
            TYPED_REFUSAL,
            9,
            column,
        )
        for column in columns
    ]


MYSQL_TYPED_WHERE = (
    " WHERE (((`s0`.`ts` >= CAST(? AS DATETIME(6)))"
    " AND (`s0`.`d2` = CAST(? AS DATE)))"
    " AND (`s0`.`money` >= CAST(? AS DECIMAL(9,2))))"
)
MYSQL_ANCHORS = {"Timestamp": "DATETIME(6)", "Date": "DATE", "Decimal": "DECIMAL(9,2)"}


def _mysql_typed(root: Path, body: str, *, main: bool = False) -> Any:
    """The MySQL emission of ``body``, or with ``main`` the one of main, which
    has no MySQL Decimal, Date or Timestamp carrier."""
    if not main:
        return typed_case(root, "mysql", body)[1]
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(parameters.HEADER_PHYSICAL, "mysql", {})
        return typed_case(root, "mysql", body)[1]


def _uses(document: dict[str, Any]) -> list[tuple[str, int, int]]:
    return [
        (u["physical_type"], u["owner"]["parameter"], u["server_index"])
        for u in document["parameter_uses"]
    ]


def test_mysql_typed_parameters_cast_to_their_source_carrier_in_their_cells(
    tmp_path: Path,
) -> None:
    """S09: in a WHERE comparison with a source field of its type, each MySQL
    Decimal(p, s), Date or Timestamp read is one `?` in its source carrier, a
    Decimal one with its declared precision and scale, with no binding
    obligation; main refuses each declaration."""
    outcome = _mysql_typed(tmp_path / "candidate", MYSQL_TYPED_OPEN["where"])
    assert outcome.status == "VERIFIED"
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert MYSQL_TYPED_WHERE in document["sql"]
    assert [(p["name"], p["tag"], p["nullable"]) for p in document["parameters"]] == [
        ("since", "Timestamp", False),
        ("day", "Date", True),
        ("floor", "Decimal", False),
    ]
    assert _uses(document) == [
        ("my_datetime", 0, 1),
        ("my_date", 1, 2),
        ("my_decimal", 2, 3),
    ]
    assert document["binding_obligations"] == []
    main = _mysql_typed(tmp_path / "main", MYSQL_TYPED_OPEN["where"], main=True)
    assert main.status == "BLOCKED"
    assert {b.detail for b in main.blockers} == {
        "query_parameter_type_not_admitted_on_target"
    }


@pytest.mark.parametrize(
    ("operator", "sql"),
    (("==", "="), ("!=", "<>"), ("<", "<"), ("<=", "<="), (">", ">"), (">=", ">=")),
)
def test_each_mysql_typed_comparison_and_select_item_is_a_cell(
    tmp_path: Path, operator: str, sql: str
) -> None:
    """Every comparison operator of a cell, for each type, and each type as
    a whole SELECT item: one `?` per read in SQL order, WHERE before SELECT,
    a header parameter read twice taking two server indexes."""
    body = (
        "query result(since: Timestamp, day: Date, floor: Decimal(9, 2)):\n"
        f"    from rows\n    where ts {operator} since and d {operator} day"
        f" and money {operator} floor\n"
        "    select:\n        id\n        a = since\n        b = day\n"
        "        e = floor\n"
    )
    outcome = _mysql_typed(tmp_path, body)
    assert outcome.status == "VERIFIED", outcome.blockers
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    for field, tag in (("ts", "Timestamp"), ("d", "Date")):
        assert (
            f"(`s0`.`{field}` {sql} CAST(? AS {MYSQL_ANCHORS[tag]}))" in document["sql"]
        )
    assert f"(`s0`.`money` {sql} CAST(? AS DECIMAL(9,2)))" in document["sql"]
    for label, tag in (("a", "Timestamp"), ("b", "Date")):
        assert f"CAST(? AS {MYSQL_ANCHORS[tag]}) AS `{label}`" in document["sql"]
    assert "CAST(? AS DECIMAL(9,2)) AS `e`" in document["sql"]
    assert [owner for _, owner, _ in _uses(document)] == [0, 1, 2] * 2
    assert [index for _, _, index in _uses(document)] == list(range(1, 7))


@pytest.mark.parametrize(
    ("items", "owners"),
    ((("a = day", "b = floor"), [0, 1]), (("a = floor", "b = day"), [1, 0])),
    ids=("ab", "ba"),
)
def test_mysql_typed_reads_follow_the_sql_order_with_mysql_multiplicity(
    tmp_path: Path, items: tuple[str, str], owners: list[int]
) -> None:
    """The native occurrences follow the SQL, also with the reads reversed,
    and one Date read twice in an `or` is two `?`, never one deduplicated
    index."""
    body = (
        "query result(day: Date, floor: Decimal(9, 2)):\n    from rows\n"
        "    select:\n        id\n" + "".join(f"        {i}\n" for i in items)
    )
    outcome = _mysql_typed(tmp_path / "order", body)
    assert outcome.status == "VERIFIED"
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [owner for _, owner, _ in _uses(document)] == owners
    outcome = _mysql_typed(tmp_path / "twice", MYSQL_TYPED_OPEN["twice"])
    assert outcome.status == "VERIFIED"
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert (
        "((`s0`.`d` = CAST(? AS DATE)) OR (`s0`.`d` = CAST(? AS DATE)))"
        in document["sql"]
    )
    assert _uses(document) == [("my_date", 0, 1), ("my_date", 0, 2)]


@pytest.mark.parametrize("shape", sorted(MYSQL_TYPED_OPEN))
def test_mysql_typed_cells_open_only_statements_main_refuses(
    tmp_path: Path, shape: str
) -> None:
    """Each body in its cells emits, where main refuses it at its typed
    declarations."""
    body = MYSQL_TYPED_OPEN[shape]
    assert _mysql_typed(tmp_path / "candidate", body).status == "VERIFIED"
    main = _mysql_typed(tmp_path / "main", body, main=True)
    assert main.status == "BLOCKED"
    assert {b.detail for b in main.blockers} == {
        "query_parameter_type_not_admitted_on_target"
    }


@pytest.mark.parametrize("shape", sorted(MYSQL_TYPED_REFUSED))
def test_a_refused_mysql_typed_statement_reports_mains_document(
    tmp_path: Path, shape: str
) -> None:
    """D77.24, D77.37: a body outside the cells, in them but refused by
    another rule, or declaring a UUID (S09 withdrew its MySQL carrier),
    reports main's whole document, each typed declaration PIE-B1003 in
    header order and nothing else."""
    body = MYSQL_TYPED_REFUSED[shape]
    outcome = _mysql_typed(tmp_path / "candidate", body)
    main = _mysql_typed(tmp_path / "main", body, main=True)
    assert outcome.status == main.status == "BLOCKED"
    assert serialize_project_sql_emission(outcome) == serialize_project_sql_emission(
        main
    )
    (header,) = (line for line in body.splitlines() if line.startswith("query result("))
    typed = re.findall(r": (?:Date|Timestamp|UUID|Decimal)\b", header)
    assert [b.detail for b in outcome.blockers] == [
        "query_parameter_type_not_admitted_on_target"
    ] * len(typed)


# Projection chains: SELECT items that are fields and literals alone, over
# the source or a plain upstream query, which no row realization reads; each
# is (upstream, FROM, SELECT).
_PROJECTION_CHAINS = (
    ("", "    from rows\n", "    select:\n        id\n"),
    ("", "    from rows\n", "    select:\n        id\n        d\n        k = -1\n"),
    (
        "query up:\n    from rows\n    select:\n        id\n        d\n",
        "    from up\n",
        "    select:\n        id\n",
    ),
)


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize(
    ("tag", "field"),
    (
        ("Date", "d"),
        ("Date | None", "d2"),
        ("Timestamp", "ts"),
        ("Decimal(9, 2)", "money"),
        ("UUID", "u"),
    ),
    ids=("date", "nullable_date", "timestamp", "decimal", "uuid"),
)
def test_a_mysql_projection_chain_refuses_each_typed_declaration(
    tmp_path: Path, tag: str, field: str, policy: str
) -> None:
    """A MySQL projection chain that never reads its Decimal, Date, Timestamp
    or UUID declaration reports the document of the same body with a WHERE:
    PIE-B1003 at the declaration. PostgreSQL emits it, and a read in its
    cell still emits on MySQL, except of a UUID."""

    def emitted(name: str, target: str, body: str) -> Any:
        return typed_case(tmp_path / name, target, body, policy)[1]

    header = f"query result(p: {tag}):\n"
    for index, (upstream, source, items) in enumerate(_PROJECTION_CHAINS):
        body = upstream + header + source + items
        chain = emitted(f"chain{index}", "mysql", body)
        where = emitted(
            f"where{index}",
            "mysql",
            upstream + header + source + "    where id > 1\n" + items,
        )
        assert chain.status == where.status == "BLOCKED"
        assert serialize_project_sql_emission(chain) == (
            serialize_project_sql_emission(where)
        )
        assert [
            (b.code, b.detail, b.location.line, b.location.column)
            for b in chain.blockers
        ] == [
            (
                "PIE-B1003",
                "query_parameter_type_not_admitted_on_target",
                9 + upstream.count("\n"),
                14,
            )
        ]
        postgres = emitted(f"postgres{index}", "postgres", body)
        assert postgres.status == "VERIFIED", postgres.blockers
    for index, read in enumerate(
        (
            "    select:\n        id\n        a = p\n",
            f"    where {field} == p\n    select:\n        id\n",
        )
    ):
        outcome = emitted(f"read{index}", "mysql", header + "    from rows\n" + read)
        assert outcome.status == ("BLOCKED" if tag == "UUID" else "VERIFIED")


def _listed(outcome: Any) -> list[tuple[Any, ...]]:
    """Each blocker of ``outcome`` as (code, detail, line, column), without
    the position when it has no location."""
    return [
        (
            b.code,
            b.detail,
            *((b.location.line, b.location.column) if b.location else ()),
        )
        for b in outcome.blockers
    ]


def _built(
    monkeypatch: pytest.MonkeyPatch,
    contract: Callable[[dict[str, Any]], object] | None = None,
    source: Callable[[str], str] | None = None,
    target_request: Any = None,
) -> None:
    """Build each case that ``typed_case`` builds with ``contract`` editing
    its contract in place, ``source`` rewriting its main module and
    ``target_request`` as its target request."""
    real = probe.build_case

    def build_case(
        directory: Path, files: dict[str, str], document: str, policy: str
    ) -> Any:
        edited = json.loads(document)
        if contract is not None:
            contract(edited)
        if source is not None:
            files = {**files, "main.pietto": source(files["main.pietto"])}
        return real(
            directory,
            files,
            probe.encoded(edited).decode(),
            policy,
            target_request=target_request,
        )

    monkeypatch.setattr(probe, "build_case", build_case)


def _premise(
    key: str, value: Any = None, *, source: bool = False
) -> Callable[[dict[str, Any]], None]:
    """An edit that drops each premise ``key`` of a contract's environment,
    or of its source with ``source``, or gives each one ``value``."""

    def edit(contract: dict[str, Any]) -> None:
        holder, name = (
            (contract["sources"][0], "premises")
            if source
            else (contract, "environment")
        )
        holder[name] = [
            p if p["key"] != key else {**p, "value": value}
            for p in holder[name]
            if p["key"] != key or value is not None
        ]

    return edit


def _limits(*limits: dict[str, int]) -> Callable[[dict[str, Any]], None]:
    """An edit that adds each of ``limits`` as a contract's resource limits."""
    return lambda contract: contract["environment"].extend(
        {"key": "resource_limits", "scope": "statement", "value": value}
        for value in limits
    )


@dataclass(frozen=True)
class _Beside:
    """A refusal beside a refused MySQL projection chain's typed declarations:
    the blockers listed before and after them; the list of the same chain
    without a header, when it is not those (a refusal that the declarations
    replace); the edits that make the chain meet it (``_built``'s, the last
    SELECT item, the literal policy and an upstream query read in place of
    the source); and whether a body with a WHERE lists the same document."""

    before: tuple[tuple[Any, ...], ...] = ()
    after: tuple[tuple[Any, ...], ...] = ()
    plain: tuple[tuple[Any, ...], ...] | None = None
    contract: Callable[[dict[str, Any]], object] | None = None
    source: Callable[[str], str] | None = None
    target_request: Callable[[], Any] | None = None
    item: str = "k = -1"
    policy: str = "preserve_literals"
    upstream: bool = False
    twin: bool = True


def _mysql(name: str = "declared", base: Any = None) -> Any:
    """A MySQL 8.4.12 profile, an overlay of ``base`` when it is given."""
    return _profile(_database("mysql", "8.4.12"), name=name, base=base)


# Each refusal that emission lists beside a MySQL projection chain's typed
# declarations, in the order it checks them: a row for each detail that a
# premise conflict, _emission_blockers or a helper it calls can list for a
# chain, and one for each of the two returns of
# representation_not_in_initial_domain. The other details need a statement
# that is not a chain (the refusals of _REFUSED_BEFORE_THE_BODY, a body
# without a source, a pending enforcement, a Float membership) or PostgreSQL
# (a table function's binding), or no source program reaches them:
# scalar_meaning_correspondence (inconsistent prepared inputs, listed
# alone), logical_type_evidence_missing (every alias, enum and Decimal field
# keeps its type evidence) and each literal-sign detail but
# literal_leaf_representation (a chain item is a field or a literal under
# signs, a sign applies only to an Int or a Float of its own type, and no
# leaf is negative). Last, a row for each refusal that emission checks only
# once _emission_blockers lists nothing, the contract's SQL and artifact byte
# limits, which the declarations replace. Its other checks there recheck its
# own output (plan_ast_correspondence and the other PIE-B1008 issues of
# verify_project_sql_emission, and serialization's artifact_correspondence),
# and _emission_blockers refuses first a chain over the node or parameter
# limit they count; the checks that a public entry runs on an emitted query,
# project_path among them, are in _ONCE_A_QUERY_EMITS. The body with a WHERE
# stops at its typed declarations before its literal checks, and its
# structure limit refuses it before it is assessed, without them.
_BESIDE_A_CHAIN: dict[str, _Beside] = {
    "premise_conflict": _Beside(
        before=(("PIE-B1005", "inconsistent_declared_scope"),),
        contract=_limits({"nodes": 900}, {"nodes": 901}),
    ),
    "release": _Beside(
        before=(("PIE-B1003", "target_release_not_reviewed"),),
        contract=lambda c: c["target"].update(release="8.4.11"),
    ),
    # A target request with a profile, which no public entry passes.
    "profile_target": _Beside(
        after=(("PIE-B1005", "target_evidence_scope_conflict"),),
        target_request=lambda: prepare_project_sql_target_request(
            _database("mysql", "8.4.12"), base=_profile(_database("mysql", "8.4.11"))
        ),
    ),
    "profile_composition": _Beside(
        after=(("PIE-B1006", "original_profile_composition_unresolved"),),
        target_request=lambda: prepare_project_sql_target_request(
            _database("mysql", "8.4.12"),
            base=_mysql(),
            overlays=(_mysql("overlay", _mysql("other")),),
        ),
    ),
    "literal_sign": _Beside(
        after=(("PIE-B1002", "literal_leaf_representation", 14, 9),),
        item="k = 9223372036854775808",
        twin=False,
    ),
    "operator_missing": _Beside(
        after=(("PIE-B1004", "operator_environment_declaration_missing"),),
        contract=_premise("operator_environment"),
    ),
    "operator_mismatch": _Beside(
        after=(("PIE-B1005", "operator_environment_declaration_mismatch"),),
        contract=_premise("operator_environment", "user_defined"),
    ),
    "protocol_missing": _Beside(
        after=(("PIE-B1004", "parameter_protocol_declaration_missing"),),
        contract=_premise("parameter_protocol"),
        policy="bind_safe_literals",
    ),
    "protocol_mismatch": _Beside(
        after=(("PIE-B1005", "parameter_protocol_declaration_mismatch"),),
        contract=_premise("parameter_protocol", "postgres_extended"),
        policy="bind_safe_literals",
    ),
    "occurrence_limit": _Beside(
        after=(("PIE-B1007", "parameter_occurrence_limit"),),
        contract=_limits({"parameters": 0}),
        policy="bind_safe_literals",
    ),
    "structure_limit": _Beside(
        after=(("PIE-B1007", "generated_structure_limit"),),
        contract=_limits({"nodes": 9}),
        twin=False,
    ),
    "naming_missing": _Beside(
        after=(("PIE-B1004", "identifier_case_declaration_missing"),),
        contract=_premise("identifier_case"),
        upstream=True,
    ),
    "naming_mismatch": _Beside(
        after=(("PIE-B1005", "identifier_case_declaration_mismatch"),),
        contract=_premise("identifier_case", "lower_case_table_names=1"),
        upstream=True,
    ),
    "target_evidence": _Beside(
        after=(
            ("PIE-B1006", "negative_original_target_evidence"),
            ("PIE-B1001", "source_family_mismatch", 8, 1),
        ),
        source=lambda s: s.replace("mysql.table", "postgres.table"),
    ),
    "source_mapping": _Beside(
        after=(("PIE-B1001", "source_mapping_missing", 8, 1),),
        contract=lambda c: c["sources"].clear(),
    ),
    "source_schema": _Beside(
        after=(("PIE-B1001", "complete_ordered_source_schema_required", 8, 1),),
        contract=lambda c: c["sources"][0]["fields"].reverse(),
    ),
    "source_identifier": _Beside(
        after=(("PIE-B1001", "source_identifier_unrepresentable"),),
        contract=lambda c: c["sources"][0]["relation"].update(name="r" * 80),
    ),
    "row_domain": _Beside(
        after=(("PIE-B1001", "row_domain_matches_declaration_required"),),
        contract=_premise("row_domain_matches", source=True),
    ),
    "read_only": _Beside(
        after=(("PIE-B1001", "read_only_object_declaration_required"),),
        contract=_premise("read_only_object", source=True),
    ),
    "encoding_missing": _Beside(
        after=(("PIE-B1004", "client_encoding_declaration_missing"),),
        contract=_premise("client_encoding"),
    ),
    "encoding_mismatch": _Beside(
        after=(("PIE-B1005", "client_encoding_mismatch"),),
        contract=_premise("client_encoding", "latin1"),
    ),
    "column": _Beside(
        after=(("PIE-B1001", "column_identifier_unrepresentable_or_colliding"),),
        contract=lambda c: c["sources"][0]["fields"][1].update(column="ID"),
    ),
    "enum_field": _Beside(
        after=(("PIE-B1003", "representation_not_in_initial_domain", 7, 5),),
        source=lambda s: (
            s.replace("    money: Decimal(9, 2)\n", "    money: Status\n")
            + "enum Status:\n    active\n    closed\n"
        ),
    ),
    "temporal_alias": _Beside(
        after=(
            ("PIE-B1004", "logical_temporal_or_uuid_meaning_missing", 3, 5),
            ("PIE-B1004", "logical_temporal_or_uuid_meaning_missing", 6, 5),
        ),
        source=lambda s: (
            s.replace("    ts: Timestamp\n", "    ts: Stamp\n")
            + "type Stamp = Timestamp\n"
        ),
    ),
    "nullability": _Beside(
        after=(("PIE-B1002", "nullability_mismatch", 4, 5),),
        contract=lambda c: c["sources"][0]["fields"][2]["representation"].update(
            nullable=True
        ),
    ),
    "plain_decimal": _Beside(
        after=(("PIE-B1004", "validated_decimal_parameters_missing", 7, 5),),
        source=lambda s: s.replace(
            "    money: Decimal(9, 2)\n", "    money: Decimal\n"
        ),
    ),
    # A built-in type outside the initial domain: the second return.
    "bytes_field": _Beside(
        after=(("PIE-B1003", "representation_not_in_initial_domain", 7, 5),),
        source=lambda s: s.replace("    money: Decimal(9, 2)\n", "    money: Bytes\n"),
    ),
    "storage": _Beside(
        after=(("PIE-B1002", "physical_storage_or_domain_mismatch", 3, 5),),
        contract=lambda c: c["sources"][0]["fields"][1]["representation"].update(
            storage={"kind": "my_date"}
        ),
    ),
    "field_premise": _Beside(
        after=(("PIE-B1005", "field_domain_premise_mismatch"),),
        contract=lambda c: c["environment"].append(
            {
                "key": "value_domain",
                "scope": {
                    "kind": "expression",
                    "source": {
                        "module": "main.pietto",
                        "kind": "source",
                        "name": "rows",
                    },
                    "site": {"kind": "expression_site", "position": 0},
                    "context": {"kind": "select_block", "position": 0},
                },
                "value": {"kind": "bool01"},
            }
        ),
    ),
    "label": _Beside(
        after=(("PIE-B1002", "output_label_unrepresentable"),),
        item="l" * 300 + " = -1",
    ),
    "sql_bytes": _Beside(
        plain=(("PIE-B1007", "sql_byte_limit"),),
        contract=_limits({"sql_bytes": 20}),
    ),
    "artifact_bytes": _Beside(
        plain=(("PIE-B1007", "public_artifact_byte_limit"),),
        contract=_limits({"artifact_bytes": 200}),
    ),
}


@pytest.mark.parametrize("beside", tuple(_BESIDE_A_CHAIN))
def test_a_refused_mysql_projection_chain_places_its_typed_declarations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, beside: str
) -> None:
    """A MySQL projection chain that another rule also refuses lists PIE-B1003
    at each Decimal, Date, Timestamp and UUID declaration in header order,
    after its premise conflicts and an unreviewed release and before every
    other refusal, its own literal-sign ones included. Those refusals are the
    list of the same chain without a header, but for a refusal that emission
    checks only once nothing else refuses a query, the contract's SQL or
    artifact byte limit, which the declarations replace. That is where a body
    with a WHERE lists them, and it reports the chain's document unless it
    stops at its declarations before a literal check or is refused before it
    is assessed."""
    row = _BESIDE_A_CHAIN[beside]
    _built(
        monkeypatch,
        row.contract,
        row.source,
        None if row.target_request is None else row.target_request(),
    )
    header = (
        "query result(since: Timestamp, n: Int, key: UUID, day: Date, "
        "floor: Decimal(9, 2)):\n"
    )
    # An upstream query declared after the chain keeps the header's line.
    read, upstream = (
        (
            "    from up\n",
            "query up:\n    from rows\n    select:\n        id\n        d\n",
        )
        if row.upstream
        else ("    from rows\n", "")
    )
    items = f"    select:\n        id\n        d\n        {row.item}\n"

    def emitted(name: str, entry: str, where: str = "") -> Any:
        body = entry + read + where + items + upstream
        return typed_case(tmp_path / name, "mysql", body, row.policy)[1]

    chain = emitted("chain", header)
    typed = [
        ("PIE-B1003", "query_parameter_type_not_admitted_on_target", 9, column)
        for column in (14, 40, 51, 62)
    ]
    assert _listed(chain) == [*row.before, *typed, *row.after]
    assert _listed(emitted("plain", "query result:\n")) == list(
        (*row.before, *row.after) if row.plain is None else row.plain
    )
    if row.twin:
        where = emitted("where", header, "    where id > 1\n")
        assert serialize_project_sql_emission(chain) == (
            serialize_project_sql_emission(where)
        )


class _Run(NamedTuple):
    """An entry's outcome: its exit code, standard output and standard error,
    and whether it wrote its --output."""

    code: int
    stdout: bytes
    stderr: str
    written: bool


def _arguments(root: Path, *options: str) -> list[str]:
    """``emit-sql --project`` of the MySQL query ``result`` at ``root``, in
    ``main.pietto`` unless the options give a module, or with ``--all`` its
    batch, in JSON unless the options give a format."""
    module = any(option.startswith("--module=") for option in options)
    selected = (
        ("--all",)
        if "--all" in options
        else (
            *(() if module else ("--module=main.pietto",)),
            "--kind=query",
            "--name=result",
        )
    )
    shown = any(option.startswith("--format=") for option in options)
    return [
        f"--project={root}",
        *selected,
        "--dialect=mysql",
        "--emission-contract=contract.json",
        *(() if shown else ("--format=json",)),
        *(option for option in options if option != "--all"),
    ]


def _emitted_by(root: Path, *options: str) -> _Run:
    """The run of these arguments through ``run_project_emit_sql``."""
    result = emission_cli.run_project_emit_sql(_arguments(root, *options))
    return _Run(result.exit_code, result.stdout, result.stderr, result.written)


def _to_file(root: Path, output: Path) -> _Run:
    return _emitted_by(root, f"--output={output}")


def _to_directory(root: Path, output: Path) -> _Run:
    return _emitted_by(root, "--all", f"--output={output}")


class _FullStdout:
    """A standard output on a full device: each write fails, on its binary
    buffer too."""

    @property
    def buffer(self) -> _FullStdout:
        return self

    def write(self, data: object) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")

    def flush(self) -> None:
        return None


class _UnencodableStdout:
    """A standard output installed without a binary buffer, whose encoding
    cannot hold the text."""

    def write(self, text: str) -> int:
        raise UnicodeEncodeError("ascii", text, 0, 1, "ordinal not in range(128)")

    def flush(self) -> None:
        return None


def _printed_by(stdout: Any, root: Path, output: Path, *options: str) -> _Run:
    """The run of these arguments through ``pietto.cli.main`` with ``stdout``
    as its standard output, which keeps nothing; whether ``output`` exists
    stands for whether the run wrote it."""
    error = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(error):
        code = cli.main(["emit-sql", *_arguments(root, *options)])
    return _Run(code, b"", error.getvalue(), output.exists())


def _batch_of(root: Path, _: Path) -> _Run:
    """``compile_all_sql`` of the MySQL project at ``root``, as a run."""
    emission = compile_all_sql(root, dialect="mysql", emission_contract="contract.json")
    return _Run(emission_cli.EXITS[emission.status], emission.document, "", False)


def _refusal(run: _Run) -> tuple[int, str | None]:
    """The exit code and the last refusal of a run: the kind and message of
    its last CLI error, the error pietto.cli writes for its standard output
    (after a refused rendering, if any), or None."""
    note = re.search(r"(?:\A|\n)pietto(?: emit-sql)?: error: (.*)\n\Z", run.stderr)
    if note is not None:
        return run.code, note[1]
    if not run.stdout.startswith(b"{"):
        return run.code, None
    document = json.loads(run.stdout)
    errors = (document.get("failure", document) or {}).get("cli_errors", [])
    if not errors:
        return run.code, None
    return run.code, f"{errors[-1]['kind']}: {errors[-1]['message']}"


def _renderings(stdout: bytes) -> list[bytes]:
    """The first line of each text rendering on a standard output: its
    format and status."""
    return [
        line for line in stdout.splitlines() if line.startswith(b"pietto.sql-emission.")
    ]


def _unnamed(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    try:
        Path(os.fsdecode(os.fsencode(root) + b"/\xff.pietto")).write_bytes(b"")
    except (OSError, UnicodeError):
        pytest.skip("this file system refuses a file name that is not UTF-8")


def _unnamed_module(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The queries move to a module whose name is not UTF-8, beside an empty
    # file whose name, also not UTF-8, comes first.
    main = root / "main.pietto"
    shapes, query, queries = main.read_text().partition("query result")
    try:
        Path(os.fsdecode(os.fsencode(root) + b"/\xff.pietto")).write_text(
            f'from "main.pietto" import source rows\n{query}{queries}'
        )
        Path(os.fsdecode(os.fsencode(root) + b"/\x80.pietto")).write_bytes(b"")
    except (OSError, UnicodeError):
        pytest.skip("this file system refuses a file name that is not UTF-8")
    main.write_text(f"{shapes}export source rows\n")


def _replaced(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    validate, checks = emission_cli._validate_output, []

    def again(path: Path) -> Any:
        # The write checks the destination again; since the check before
        # emission it has become a symbolic link.
        if path == output:
            checks.append(path)
            if len(checks) == 2:
                output.symlink_to(output.with_name("elsewhere"))
        return validate(path)

    monkeypatch.setattr(emission_cli, "_validate_output", again)


def _read_only(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output.write_text("kept")
    output.chmod(0o444)
    if os.access(output, os.W_OK):
        pytest.skip("this user may write a read-only file")


def _another_users(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if sys.platform == "win32":
        pytest.skip("needs POSIX owners")
    output.write_text("kept")
    owner = output.stat().st_uid
    # The command runs as a user who is neither the file's owner nor root.
    monkeypatch.setattr(os, "geteuid", lambda: owner + 1)


def _locked(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output.parent.chmod(0o555)
    if os.access(output.parent, os.W_OK):
        pytest.skip("this user may write a read-only directory")


def _uncleaned(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*arguments: Any, **keywords: Any) -> None:
        raise OSError(errno.EPERM, "Operation not permitted")

    # The temporary file can neither replace the output nor be removed.
    monkeypatch.setattr(emission_cli.os, "replace", refuse)
    monkeypatch.setattr(Path, "unlink", refuse)


def _directory(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not batch_output.supported():
        pytest.skip("Linux or Windows publication required")


def _drift(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _directory(root, output, monkeypatch)
    monkeypatch.setattr(emission_cli, "_protected_current", lambda _: False)


def _locked_directory(
    root: Path, output: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _directory(root, output, monkeypatch)
    _locked(root, output, monkeypatch)


def _no_temporary_files(
    root: Path, output: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Only the Linux descriptor writer probes for anonymous files; the
    # Windows writer never raises UnsupportedPlatform.
    if not batch_output._descriptors_supported():
        pytest.skip("Linux descriptor publication required")

    def refuse(directory: int) -> int:
        # A file system without O_TMPFILE, such as some mounted drives.
        raise batch_output.UnsupportedPlatform("anonymous file publication unavailable")

    monkeypatch.setattr(batch_output, "_anonymous", refuse)


def _unreviewed(root: Path, output: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = root / "contract.json"
    contract = json.loads(path.read_text())
    contract["target"]["release"] = "8.4.11"
    path.write_text(json.dumps(contract))


@dataclass(frozen=True)
class _Emits:
    """A stage after emission that only a VERIFIED document reaches, or the
    batch's output limit: the run of an entry for a project root and a fresh
    output path; what the chain gets there as 0.2.1 emitted it, and what it
    gets (``_refusal``); how many Date declarations it has and whether it
    reads an upstream query; a step on each project before the runs (its
    root, its output path and the test's monkeypatch); and whether the batch
    limit is set midway between the sizes of the chain's batch and the batch
    as 0.2.1 emitted it."""

    run: Callable[[Path, Path], _Run]
    control: tuple[int, str | None]
    typed: tuple[int, str | None] = (1, None)
    declarations: int = 1
    upstream: bool = True
    prepare: Callable[[Path, Path, pytest.MonkeyPatch], object] | None = None
    limit: bool = False


_STDOUT = "standard output could not be written"
_LIMIT = (
    "batch_output_limit: Batch JSON exceeds the 64 MiB output limit; narrow the"
    " exact selectors."
)


# Each stage after emission that only a VERIFIED document reaches, which a
# chain's typed declarations now keep it from, and the batch's output limit,
# which the size of each item's document decides, in the order the entries
# run them. First, the encoding of the document, which names every project
# file: another project file whose name is not UTF-8 is refused as
# project_path. A refused document is checked instead for its own locations:
# a blocker or diagnostic located in such a file refuses it as project_path,
# naming that file, so a chain in such a module names its own module where
# 0.2.1 named the first such file, as the body with a WHERE does.
# Then the 64 MiB limit: a batch fits it once the declarations replace a
# longer document, and passes it where their list is the longer one, with 64
# of them or beside another refusal. Then the write of emit-sql's --output
# file, a row for each of its refusals (the contract as the file, a
# destination that has become a symbolic link since the check before
# emission, a read-only file, a file of another user, a failed write and a
# temporary file that is not removed) and one for the file written; and the
# write of the batch's --output directory, for a VERIFIED batch, a row for
# each of its refusals (project inputs that change, a failed write, a file
# system without safe directory output) and one for the directory written.
# Last, the streams: in --format text, the rendering of a VERIFIED document,
# alone or in a batch, with an --output file or directory or without, on
# standard output, which pietto.cli writes only when it is not empty, so
# that a full standard output, or one that cannot encode the text, is an
# error (a closed pipe or descriptor gives the full one's), and which still
# gets the rendering of another VERIFIED item of the batch; and the ending
# of that error, which says, in either format, that the --output file or
# directory written is kept. Realization's SQL and artifact byte limits are
# rows of _BESIDE_A_CHAIN. compile_query's template stage, whose refusal the
# compiled-bundle test pins, gives way as a whole, and main's re-derivation
# of a VERIFIED MySQL statement for compile_query refuses nothing of its
# own. The handler of a RecursionError, at any stage, needs a sign chain
# deeper than the parser admits.
_ONCE_A_QUERY_EMITS: dict[str, _Emits] = {
    "project_path": _Emits(
        lambda root, _: _emitted_by(root),
        (
            2,
            "project_path: Project source path must be valid UTF-8 to emit SQL:"
            ' "\\udcff.pietto"; rename it.',
        ),
        prepare=_unnamed,
    ),
    "project_path_own_module": _Emits(
        lambda root, _: _emitted_by(root, "--module=\udcff.pietto"),
        (
            2,
            "project_path: Project source path must be valid UTF-8 to emit SQL:"
            ' "\\udc80.pietto"; rename it.',
        ),
        typed=(
            2,
            "project_path: Project source path must be valid UTF-8 to emit SQL:"
            ' "\\udcff.pietto"; rename it.',
        ),
        prepare=_unnamed_module,
    ),
    "batch_limit_fits": _Emits(_batch_of, (2, _LIMIT), limit=True),
    "batch_limit_declarations": _Emits(
        _batch_of,
        (0, None),
        typed=(2, _LIMIT),
        declarations=64,
        upstream=False,
        limit=True,
    ),
    "batch_limit_refused": _Emits(
        _batch_of, (1, None), typed=(2, _LIMIT), prepare=_unreviewed, limit=True
    ),
    "output_path": _Emits(
        lambda root, _: _emitted_by(root, f"--output={root / 'contract.json'}"),
        (
            2,
            "output_path: Output path must differ from the project configuration,"
            " sources and emission contract.",
        ),
    ),
    "output_replaced": _Emits(
        _to_file,
        (2, "output_path: Output path must not be a symbolic link."),
        prepare=_replaced,
    ),
    "output_read_only": _Emits(
        _to_file, (2, "output_write: Output file is read-only."), prepare=_read_only
    ),
    "output_another_users": _Emits(
        _to_file,
        (2, "output_write: Output file belongs to another user."),
        prepare=_another_users,
    ),
    "output_failed": _Emits(
        _to_file,
        (2, "output_write: Output file could not be written."),
        prepare=_locked,
    ),
    "output_uncleaned": _Emits(
        _to_file,
        (2, "output_write: Temporary output file could not be removed."),
        prepare=_uncleaned,
    ),
    "output_file": _Emits(_to_file, (0, None)),
    "batch_drift": _Emits(
        _to_directory,
        (2, "output_write: Project inputs changed before output was written."),
        prepare=_drift,
    ),
    "batch_failed": _Emits(
        _to_directory,
        (2, "output_write: Output directory could not be written."),
        prepare=_locked_directory,
    ),
    "batch_platform": _Emits(
        _to_directory,
        (
            2,
            "batch_output_platform: Safe batch directory output requires Windows"
            " with CPython 3.12.4 or later or a supported Linux filesystem; use"
            " stdout instead.",
        ),
        prepare=_no_temporary_files,
    ),
    "batch_directory": _Emits(_to_directory, (0, None), prepare=_directory),
    "text": _Emits(lambda root, _: _emitted_by(root, "--format=text"), (0, None)),
    "batch_text": _Emits(
        lambda root, _: _emitted_by(root, "--all", "--format=text"),
        (0, None),
        upstream=False,
    ),
    "text_stdout_full": _Emits(
        lambda root, output: _printed_by(_FullStdout(), root, output, "--format=text"),
        (2, _STDOUT),
    ),
    "text_stdout_unencodable": _Emits(
        lambda root, output: _printed_by(
            _UnencodableStdout(), root, output, "--format=text"
        ),
        (2, "terminal output could not be encoded"),
    ),
    "batch_text_stdout_full": _Emits(
        lambda root, output: _printed_by(
            _FullStdout(), root, output, "--all", "--format=text"
        ),
        (2, _STDOUT),
        upstream=False,
    ),
    "text_output_file": _Emits(
        lambda root, output: _emitted_by(root, "--format=text", f"--output={output}"),
        (0, None),
    ),
    "text_stdout_full_output_file": _Emits(
        lambda root, output: _printed_by(
            _FullStdout(), root, output, "--format=text", f"--output={output}"
        ),
        (2, f"{_STDOUT}; the replaced artifact file is kept"),
    ),
    "batch_text_output_directory": _Emits(
        lambda root, output: _emitted_by(
            root, "--all", "--format=text", f"--output={output}"
        ),
        (0, None),
        upstream=False,
        prepare=_directory,
    ),
    "batch_text_beside": _Emits(
        lambda root, _: _emitted_by(root, "--all", "--format=text"), (0, None)
    ),
    "batch_text_beside_stdout_full": _Emits(
        lambda root, output: _printed_by(
            _FullStdout(), root, output, "--all", "--format=text"
        ),
        (2, _STDOUT),
        typed=(2, _STDOUT),
    ),
    "stdout_full_output_file": _Emits(
        lambda root, output: _printed_by(
            _FullStdout(), root, output, f"--output={output}"
        ),
        (2, f"{_STDOUT}; the replaced artifact file is kept"),
        typed=(2, _STDOUT),
    ),
    "stdout_full_output_directory": _Emits(
        lambda root, output: _printed_by(
            _FullStdout(), root, output, "--all", f"--output={output}"
        ),
        (2, f"{_STDOUT}; the replaced artifact file is kept"),
        typed=(2, _STDOUT),
        prepare=_directory,
    ),
}


@pytest.mark.parametrize("entry", tuple(_ONCE_A_QUERY_EMITS))
def test_a_typed_mysql_projection_chain_reaches_no_stage_of_an_emitted_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, entry: str
) -> None:
    """A MySQL projection chain that declares a Date reaches no stage after
    emission that only a VERIFIED document reaches, where the chain as 0.2.1
    emitted it reaches that stage: emit-sql writes no --output file or
    directory and reports none of their refusals, nor project_path for
    another project file whose name is not UTF-8 (in a module whose name is
    not UTF-8, it names that module); in --format text it writes nothing of
    its own to standard output, so a standard output that fails is no error
    unless another VERIFIED item's rendering goes there, and in JSON the
    error of one says no --output is kept; and it lists PIE-B1003 alone, as
    the body with a WHERE does. The batch's output limit counts the chain's
    document: a batch fits that the chain's VERIFIED document took past the
    limit, and one whose list of these blockers is the longer passes it."""
    row = _ONCE_A_QUERY_EMITS[entry]
    read = "    from up\n" if row.upstream else "    from rows\n"
    upstream = (
        "query up:\n    from rows\n    select:\n        id\n        d\n"
        if row.upstream
        else ""
    )
    roots, outputs = {}, {}
    header = ", ".join(f"p{index}: Date" for index in range(row.declarations))
    for name, where in (
        ("typed", ""),
        ("where", "    where id > 1\n"),
        ("control", ""),
    ):
        body = f"query result({header}):\n{read}{where}    select:\n        id\n"
        typed_case(tmp_path / name, "mysql", body + upstream)
        roots[name] = tmp_path / name / "mysql"
        outputs[name] = tmp_path / f"{name}-output" / "artifact"
        outputs[name].parent.mkdir()

    def run(name: str, call: Callable[[Path, Path], Any]) -> Any:
        if name != "control":
            return call(roots[name], outputs[name])
        # The chain as 0.2.1 emitted it: the law of the typed cells forced, so
        # that no Date declaration is refused.
        with monkeypatch.context() as patch:
            patch.setattr(rows, "mysql_typed_cells", lambda plan: True)
            return call(roots[name], outputs[name])

    def size(root: Path, _: Path) -> int:
        return len(
            compile_all_sql(
                root, dialect="mysql", emission_contract="contract.json"
            ).document
        )

    def listed(name: str) -> list[str]:
        return sorted(os.listdir(outputs[name].parent))

    try:
        for name in roots:
            if row.prepare is not None:
                row.prepare(roots[name], outputs[name], monkeypatch)
        if row.limit:
            typed, control = (run(name, size) for name in ("typed", "control"))
            monkeypatch.setattr(emission_cli, "MAX_BATCH_BYTES", (typed + control) // 2)
        existed = {name: output.exists() for name, output in outputs.items()}
        before = listed("typed")
        runs: dict[str, _Run] = {name: run(name, row.run) for name in roots}
        after = listed("typed")
    finally:
        for output in outputs.values():
            output.parent.chmod(0o700)

    def selected(result: _Run) -> tuple[Any, ...]:
        # The query's own document, where the run printed one, and in text
        # the head of each rendering: an upstream query's names its
        # project's files, which differ.
        if not result.stdout.startswith(b"{"):
            return (result.code, _renderings(result.stdout), *result[2:])
        document = json.loads(result.stdout)
        items = document.get("items", [{"document": document}])
        return (
            _refusal(result),
            document["status"],
            items[:1],
            result.stderr,
            result.written,
        )

    chain, control = runs["typed"], runs["control"]
    assert selected(chain) == selected(runs["where"])
    assert _refusal(chain) == row.typed
    assert not chain.written and after == before
    if row.typed == (1, None) and chain.stdout.startswith(b"{"):
        document = json.loads(chain.stdout)
        items = document.get("items", [{"document": document}])
        assert [
            (
                b["code"],
                b["subject"]["detail"],
                b["location"]["line"],
                b["location"]["column"],
            )
            for b in items[0]["document"]["blockers"]
        ] == [("PIE-B1003", "query_parameter_type_not_admitted_on_target", 9, 14)]
        assert [item["document"]["status"] for item in items[1:]] == (
            ["VERIFIED"] * (len(items) - 1)
        )
    elif row.typed == (1, None):
        # In --format text, the BLOCKED document is rendered on standard
        # error alone; standard output gets every other item's rendering, as
        # 0.2.1 wrote it after the chain's.
        assert _renderings(chain.stdout) == _renderings(control.stdout)[1:]
        assert [
            line for line in chain.stderr.splitlines() if line.startswith("blocker ")
        ] == [
            "blocker PIE-B1003 UNSUPPORTED_RULE:"
            " query_parameter_type_not_admitted_on_target (main.pietto:9:14)"
        ]
    assert _refusal(control) == row.control
    assert control.written == (outputs["control"].exists() and not existed["control"])
    if row.control == (0, None):
        assert control.stdout.startswith((b"{", b"pietto.sql-emission.v2 VERIFIED\n"))


class _Cell(NamedTuple):
    """A cell of the cross product: the route, the format, the output, the
    neighbour, and whether the names of the chain's module and of the
    neighbour's file are UTF-8."""

    route: str
    format: str
    output: str
    neighbour: str
    module: str
    beside: str


class _Report(NamedTuple):
    """How a run reports the chain: its exit code; the status, CLI errors,
    blockers and diagnostics of the chain's own document, or of the document
    that refuses the run before the chain's body, or the error pietto.cli
    writes in place of a document (status None); the status of each other
    item of its batch; and whether emission comes to the chain's body, which
    a batch refused before it lists as no item at all."""

    code: int
    status: str | None
    errors: tuple[str, ...] = ()
    blockers: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    others: tuple[str, ...] = ()
    body: bool = True


_IMPORTED = 'from "main.pietto" import source rows\n'
# The neighbour, the block of a query `beside` in a file of its own.
_NEIGHBOURS: dict[str, str | None] = {
    # An empty file.
    "none": None,
    # A query that emits.
    "verified": "    from rows\n    select:\n        id\n",
    # A query refused at its body, by a label MySQL cannot spell.
    "blocked": f"    from rows\n    select:\n        id\n        {'l' * 300} = 1\n",
    # A query refused before its body, at the plan stage.
    "before": "    from rows\n    select:\n        id\n    order by None is None\n",
    # A warning (PIE-S2385) at z, in a query refused before its body too.
    "warning": "    from rows\n    select:\n        id\n        z = None\n",
    # An error, which refuses the project before any query's body.
    "error": "    from rows\n    select:\n        nope\n",
}
# The names of the chain's module and of the neighbour's file.
_NAMED = {
    "module": {"utf8": "ä.pietto".encode(), "unnamed": b"\xff.pietto"},
    "beside": {"utf8": "é.pietto".encode(), "unnamed": b"\x80.pietto"},
}
_TYPED = "PIE-B1003 query_parameter_type_not_admitted_on_target ä.pietto:2:14"
_OWN_FILE = (
    "project_path: Project source path must be valid UTF-8 to emit SQL:"
    ' "\\udcff.pietto"; rename it.'
)
_BESIDE_FILE = (
    "project_path: Project source path must be valid UTF-8 to emit SQL:"
    ' "\\udc80.pietto"; rename it.'
)
_LISTED = _Report(1, "BLOCKED", blockers=(_TYPED,))
_WARNED = _LISTED._replace(diagnostics=("PIE-S2385 é.pietto:6:13",))
_OWN = _Report(2, "INPUT_REJECTED", (_OWN_FILE,))
_BESIDE_LISTED = _Report(2, "INPUT_REJECTED", (_BESIDE_FILE,), (_TYPED,))
_BESIDE = _Report(2, "INPUT_REJECTED", (_BESIDE_FILE,))
_ERRED = _Report(1, "BLOCKED", diagnostics=("PIE-S2102 é.pietto:5:9",), body=False)
_BESIDE_ERRED = _BESIDE._replace(body=False)
_CRASH = _Report(2, None, ("terminal output could not be encoded",), body=False)
_U, _X = "utf8", "unnamed"


# Every cell of the cross product of the axes that decide how a run reports a
# MySQL projection chain that its Date declaration refuses, read from
# run_project_emit_sql, _emit_owner, _normalized_failure, the batch and the
# writes of its output, and pietto.cli: the route (one query, selected by
# --module, --kind and --name; the batch of the chain's module, selected by
# --all and --module; and --all); the format; the output (standard output,
# --output naming an existing file, which one query replaces, and --output
# naming a directory: an existing one for one query, a new one, which the
# batch creates, for a batch); the neighbour (above); and the names of the
# chain's module and of the neighbour's file, in UTF-8 or not. Each cell
# reports what the same header over a WHERE reports and writes nothing. The
# table gives each report on standard output, by route; an --output a route
# refuses before emission (a directory for one query, an existing file for a
# batch) replaces it, and any other --output changes nothing. In JSON the
# report is the document; in text, the chain's rendering is the first on
# standard error, another item's goes to standard error, or to standard
# output when it is VERIFIED. The Python entries (compile_sql and
# compile_query for one query, compile_all_sql for a batch) report what JSON
# on standard output does. Where a selected owner's module name is not UTF-8,
# a batch fails to encode its owner, as 0.2.1 did: pietto.cli reports that
# the terminal output could not be encoded, and compile_all_sql raises. No
# cell is out of reach. A fault of a standard stream acts on these reports
# afterwards, in pietto.cli, as rows of _ONCE_A_QUERY_EMITS pin it.
_CROSSED: dict[tuple[str, str, str], tuple[_Report, _Report, _Report]] = {
    ("none", _U, _U): (_LISTED, _LISTED, _LISTED),
    ("none", _U, _X): (_LISTED, _LISTED, _LISTED),
    ("none", _X, _U): (_OWN, _CRASH, _CRASH),
    ("none", _X, _X): (_OWN, _CRASH, _CRASH),
    ("verified", _U, _U): (
        _LISTED,
        _LISTED,
        _LISTED._replace(others=("VERIFIED",)),
    ),
    ("verified", _U, _X): (_LISTED, _LISTED, _CRASH),
    ("verified", _X, _U): (_OWN, _CRASH, _CRASH),
    ("verified", _X, _X): (_OWN, _CRASH, _CRASH),
    ("blocked", _U, _U): (_LISTED, _LISTED, _LISTED._replace(others=("BLOCKED",))),
    ("blocked", _U, _X): (_LISTED, _LISTED, _CRASH),
    ("blocked", _X, _U): (_OWN, _CRASH, _CRASH),
    ("blocked", _X, _X): (_OWN, _CRASH, _CRASH),
    ("before", _U, _U): (_LISTED, _LISTED, _LISTED._replace(others=("BLOCKED",))),
    ("before", _U, _X): (_LISTED, _LISTED, _CRASH),
    ("before", _X, _U): (_OWN, _CRASH, _CRASH),
    ("before", _X, _X): (_OWN, _CRASH, _CRASH),
    ("warning", _U, _U): (_WARNED, _WARNED, _WARNED._replace(others=("BLOCKED",))),
    ("warning", _U, _X): (_BESIDE_LISTED, _BESIDE_LISTED, _CRASH),
    ("warning", _X, _U): (
        _OWN._replace(diagnostics=_WARNED.diagnostics),
        _CRASH,
        _CRASH,
    ),
    ("warning", _X, _X): (_BESIDE, _CRASH, _CRASH),
    ("error", _U, _U): (_ERRED, _ERRED, _ERRED),
    ("error", _U, _X): (_BESIDE_ERRED, _BESIDE_ERRED, _BESIDE_ERRED),
    ("error", _X, _U): (_ERRED, _ERRED, _ERRED),
    ("error", _X, _X): (_BESIDE_ERRED, _BESIDE_ERRED, _BESIDE_ERRED),
}
_ROUTES = ("single", "batch", "all")
_REFUSED_OUTPUT = {
    ("single", "dir"): _Report(
        2,
        "INPUT_REJECTED",
        ("output_path: Output path must be a regular file.",),
        body=False,
    ),
    **{
        (route, "file"): _Report(
            2,
            "INPUT_REJECTED",
            ("output_path: Output directory must not already exist.",),
            body=False,
        )
        for route in ("batch", "all")
    },
}


@pytest.fixture(scope="module")
def crossed_base(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The configuration, contract and shape of a MySQL typed case."""
    root = tmp_path_factory.mktemp("crossed")
    typed_case(root, "mysql", "query result:\n    from rows\n    select:\n        id\n")
    return root / "mysql"


def _crossed_project(base: Path, root: Path, cell: _Cell, where: str) -> str:
    """Build the cell's project at ``root``: main.pietto declares the source,
    the chain (over ``where``) has the module the cell names and the
    neighbour a file of its own. Return the chain's module path."""
    root.mkdir(parents=True)
    for name in ("pietto.toml", "contract.json"):
        (root / name).write_bytes((base / name).read_bytes())
    shapes = (base / "main.pietto").read_text().partition("query result")[0]
    (root / "main.pietto").write_text(f"{shapes}export source rows\n")
    block = _NEIGHBOURS[cell.neighbour]
    files = {
        _NAMED["module"][cell.module]: f"{_IMPORTED}query result(p0: Date):\n"
        f"    from rows\n{where}    select:\n        id\n",
        _NAMED["beside"][cell.beside]: ""
        if block is None
        else f"{_IMPORTED}query beside:\n{block}",
    }
    for name, text in files.items():
        try:
            path = Path(os.fsdecode(os.fsencode(root) + b"/" + name))
            path.write_text(text, encoding="utf-8")
        except (OSError, UnicodeError):
            pytest.skip("this file system refuses a file name that is not UTF-8")
    return os.fsdecode(_NAMED["module"][cell.module])


def _shown(arguments: list[str]) -> tuple[int, bytes, str]:
    """The exit code, standard output and standard error of ``pietto
    emit-sql`` with these arguments."""
    raw, error = io.BytesIO(), io.StringIO()
    stdout = io.TextIOWrapper(raw, encoding="utf-8", newline="")
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(error):
        code = cli.main(["emit-sql", *arguments])
    stdout.flush()
    return code, raw.getvalue(), error.getvalue()


def _tree(directory: Path) -> list[tuple[str, bytes | None]]:
    """Each path under ``directory``, with a file's bytes."""
    return sorted(
        (
            str(path.relative_to(directory)),
            path.read_bytes() if path.is_file() else None,
        )
        for path in directory.rglob("*")
    )


def _seen(run: _Run, form: str) -> tuple[Any, ...]:
    """A run as its WHERE twin's must match it: the document or rendering of
    a VERIFIED item names its project's sources, which differ, so only its
    status counts."""
    if form == "text":
        return (run.code, _renderings(run.stdout), run.stderr, run.written)
    if not run.stdout.startswith(b"{"):
        return tuple(run)
    document = json.loads(run.stdout)
    for item in document.get("items", ()):
        if item["document"]["status"] == "VERIFIED":
            item["document"] = "VERIFIED"
    return (run.code, document, run.stderr, run.written)


def _located(subject: str, location: dict[str, Any] | None) -> str:
    if location is None or location["path"] is None:
        return subject
    return f"{subject} {location['path']}:{location['line']}:{location['column']}"


def _rendered(stderr: str, stdout: bytes) -> tuple[Any, ...]:
    """The first rendering on standard error, the chain's, as its status,
    CLI errors, blockers and diagnostics, and the status of each other
    rendering, on either stream."""
    renderings: list[list[str]] = []
    for line in stderr.splitlines():
        if line.startswith("pietto.sql-emission."):
            renderings.append([])
        renderings[-1].append(line)
    errors, blockers, diagnostics = [], [], []
    own, *rest = renderings or [[]]
    for line in own[1:]:
        if line.startswith("error "):
            errors.append(line.removeprefix("error "))
        elif blocker := re.fullmatch(r"blocker (\S+) \S+: (\S+)(?: \((.+)\))?", line):
            blockers.append(" ".join(part for part in blocker.groups() if part))
        elif diagnostic := re.match(r"(\S+) (PIE-\w+) \w+: ", line):
            diagnostics.append(f"{diagnostic[2]} {diagnostic[1]}")
    others = [lines[0].split()[1] for lines in rest]
    others += [line.split()[1].decode() for line in _renderings(stdout)]
    return (
        own[0].split()[1] if own else None,
        tuple(errors),
        tuple(blockers),
        tuple(diagnostics),
        tuple(others),
    )


def _reported(run: _Run, form: str) -> tuple[Any, ...]:
    """A run's report of the chain: the fields of a _Report but ``body``."""
    note = re.fullmatch(r"pietto: error: (.*)\n", run.stderr)
    if not run.stdout and note is not None:
        return (run.code, None, (note[1],), (), (), ())
    if form == "text":
        return (run.code, *_rendered(run.stderr, run.stdout))
    assert run.stderr == ""
    document = json.loads(run.stdout)
    items = document.get("items")
    own = document if items is None else document["failure"]
    for item in items or ():
        if item["owner"]["name"] == "result":
            own = item["document"]
    return (
        run.code,
        own["status"],
        tuple(f"{error['kind']}: {error['message']}" for error in own["cli_errors"]),
        tuple(
            _located(
                f"{blocker['code']} {blocker['subject']['detail']}", blocker["location"]
            )
            for blocker in own["blockers"]
        ),
        tuple(
            _located(diagnostic["code"], diagnostic["location"])
            for diagnostic in own["diagnostics"]
        ),
        tuple(
            item["document"]["status"]
            for item in items or ()
            if item["owner"]["name"] != "result"
        ),
    )


@pytest.mark.parametrize(
    "cell",
    [
        _Cell(*axes)
        for axes in itertools.product(
            _ROUTES,
            ("json", "text"),
            ("stdout", "file", "dir"),
            tuple(_NEIGHBOURS),
            (_U, _X),
            (_U, _X),
        )
    ],
    ids="-".join,
)
def test_a_typed_mysql_projection_chain_reports_as_its_where_twin_in_every_cell(
    tmp_path: Path, crossed_base: Path, cell: _Cell
) -> None:
    """In every cell of route, format, output, neighbour and the names of
    the chain's module and of the neighbour's file, a MySQL projection chain
    that declares a Date reports what the same header over a WHERE reports,
    as the table gives it, and writes nothing; the Python entries report it
    as JSON on standard output does."""
    if cell.route != "single" and cell.output != "stdout":
        if not batch_output.supported():
            pytest.skip("Linux or Windows publication required")
    runs, modules = {}, {}
    for name, where in (("chain", ""), ("where", "    where id > 1\n")):
        root = tmp_path / name / "mysql"
        modules[name] = _crossed_project(crossed_base, root, cell, where)
        output = tmp_path / name / "output" / "artifact"
        output.parent.mkdir()
        if cell.output == "file":
            output.write_text("kept")
        elif cell.output == "dir" and cell.route == "single":
            output.mkdir()
        selected = {
            "single": (f"--module={modules[name]}", "--kind=query", "--name=result"),
            "batch": ("--all", f"--module={modules[name]}"),
            "all": ("--all",),
        }[cell.route]
        before = _tree(output.parent)
        code, stdout, stderr = _shown(
            [
                f"--project={root}",
                *selected,
                "--dialect=mysql",
                "--emission-contract=contract.json",
                f"--format={cell.format}",
                *(() if cell.output == "stdout" else (f"--output={output}",)),
            ]
        )
        runs[name] = _Run(code, stdout, stderr, _tree(output.parent) != before)
    chain = runs["chain"]
    report = (
        _REFUSED_OUTPUT.get((cell.route, cell.output))
        or _CROSSED[cell.neighbour, cell.module, cell.beside][_ROUTES.index(cell.route)]
    )
    assert _seen(chain, cell.format) == _seen(runs["where"], cell.format)
    assert _reported(chain, cell.format) == report[:-1]
    assert not chain.written
    if cell.format == "json" and cell.route != "single" and report.status:
        assert bool(json.loads(chain.stdout)["items"]) == report.body
    if cell.format != "json" or cell.output != "stdout":
        return
    root, module = tmp_path / "chain" / "mysql", modules["chain"]
    if cell.route == "single":
        import pietto.execution as execution

        emission = compile_sql(
            root,
            module=module,
            kind="query",
            name="result",
            dialect="mysql",
            emission_contract="contract.json",
        )
        assert (emission_cli.EXITS[emission.status], emission.document) == chain[:2]
        with pytest.raises(execution.CompileRejected) as rejected:
            execution.compile_query(
                root,
                module=module,
                kind="query",
                name="result",
                dialect="mysql",
                emission_contract="contract.json",
            )
        assert (rejected.value.status, rejected.value.emission) == (
            report.status,
            chain.stdout,
        )
        text = _Run(chain.code, b"", f"{rejected.value}\n", False)
        assert _reported(text, "text") == report[:-1]
        return
    selectors = {"module": module} if cell.route == "batch" else {}
    if report is _CRASH:
        with pytest.raises(UnicodeEncodeError):
            compile_all_sql(
                root, dialect="mysql", emission_contract="contract.json", **selectors
            )
        return
    emission = compile_all_sql(
        root, dialect="mysql", emission_contract="contract.json", **selectors
    )
    assert (emission_cli.EXITS[emission.status], emission.document) == chain[:2]


@dataclass(frozen=True)
class _Before:
    """A MySQL query that emission refuses before it comes to write its body:
    its block, the refusals it lists, and the edits that build it (the
    queries and tables declared before it, and ``_built``'s)."""

    block: str
    refusals: tuple[tuple[str, str], ...]
    upstream: str = ""
    contract: Callable[[dict[str, Any]], object] | None = None
    source: Callable[[str], str] | None = None


# Queries that MySQL emission refuses before it comes to write their body as
# a projection, as rows or as a JOIN. Preparation refuses the first three: a
# plan-stage refusal, where two kinds stand for all, since no plan is left to
# read a header from, and the structure limit before assessment. Then a row
# for each detail that such a route of _emission_blockers, or a helper it
# calls there, lists: the nested and scalar meaning refusals, a table-function
# input and each ordered read refused beside it, and each detail of a shape
# emission does not write, its retained ON included. The others have no
# source program: scalar_meaning_correspondence (inconsistent prepared
# inputs), match_comparison_operator_not_admitted (the grammar spells only
# admitted comparisons) and match_reference_outside_pre_match_scope (a port
# of another block); and neither the suite nor a probe reaches
# set_body_shape_not_admitted or non_field_projection_or_later_shape.
_REFUSED_BEFORE_THE_BODY: dict[str, _Before] = {
    "plan_output": _Before(
        "    from rows\n    select:\n        id\n        z = None\n",
        (("PIE-B1003", "expression_evidence_unavailable"),),
    ),
    "plan_order": _Before(
        "    from rows\n    select:\n        id\n    order by None is None\n",
        (("PIE-B1003", "order"),),
    ),
    "structure_limit": _Before(
        "    from rows\n    where id > 1\n    select:\n        id\n",
        (("PIE-B1007", "generated_structure_limit"),),
        contract=_limits({"nodes": 3}),
    ),
    "table_function": _Before(
        "    from up\n    select:\n        n\n",
        (("PIE-B1003", "table_function_not_admitted_on_target"),),
        upstream="query up:\n    from generate_series(1, 3, 1) as n\n    select:\n"
        "        n\n",
    ),
    # A read of a capturing let with ORDER BY and LIMIT beside the series.
    "ordered_read": _Before(
        "    let c:\n        capture rows\n        from other\n"
        "        where other.id == rows.id\n        select:\n            id\n"
        "        order by:\n            id\n        limit 1\n    from rows\n"
        "    where id in c and exists t\n    select:\n        id\n",
        (
            ("PIE-B1003", "table_function_not_admitted_on_target"),
            ("PIE-B1003", "mysql_correlated_order_or_limit_read_not_admitted"),
        ),
        upstream="table t:\n    from generate_series(1, 3, 1) as n\n    select:\n"
        "        n\nquery other:\n    from rows\n    select:\n        id\n",
    ),
    "collect": _Before(
        "    let recent:\n        from rows\n        select:\n            id\n"
        "        order by id\n    from rows\n    select:\n        id\n"
        "        xs = collect recent\n",
        (("PIE-B1003", "collect_not_admitted_on_target"),),
    ),
    "unnest": _Before(
        "    from cw\n    let o = unnest(cw.xs)\n    cross join o\n    select:\n"
        "        id = cw.id\n",
        (
            ("PIE-B1003", "collect_not_admitted_on_target"),
            ("PIE-B1003", "unnest_not_admitted_on_target"),
        ),
        upstream="query cw:\n    let recent:\n        from rows\n        select:\n"
        "            id\n        order by id\n    from rows\n    select:\n"
        "        id\n        xs = collect recent\n",
    ),
    "aggregate_composition": _Before(
        "    from rows\n    group by id\n    select:\n        id\n"
        "        n = count() + 1\n",
        (("PIE-B1003", "aggregate_composition_not_admitted_on_target"),),
    ),
    "scalar_meaning": _Before(
        "    from rows\n    let r = rows\n    cross join r\n"
        "    where r.u == rows.u\n    select:\n        a = rows.id\n",
        (("PIE-B1003", "scalar_meaning_requires_field_projection"),),
    ),
    # A GROUP BY over a LEFT JOIN.
    "operator": _Before(
        "    from rows\n    let r = rows\n"
        "    left join r on coalesce(r.id, rows.id) == rows.id\n"
        "    group by rows.id\n    select:\n        a = rows.id\n        n = count()\n",
        (
            ("PIE-B1003", "operator_not_implemented_in_slice6"),
            ("PIE-B1003", "match_condition_not_in_row_domain"),
            ("PIE-B1003", "join_shape_not_admitted_in_slice7"),
        ),
    ),
    "shape": _Before(
        "    from rows\n    let r = rows\n"
        "    left join r on coalesce(r.id, rows.id) == rows.id\n    select:\n"
        "        a = rows.id\n",
        (
            ("PIE-B1003", "scalar_projection_requires_later_slice"),
            ("PIE-B1003", "match_condition_not_in_row_domain"),
            ("PIE-B1003", "join_shape_not_admitted_in_slice7"),
        ),
    ),
    # Each side of the ON reads an enum field.
    "match_reference_type": _Before(
        "    from rows\n    let r = rows\n    left join r on rows.money == r.money"
        " and coalesce(r.id, rows.id) == rows.id\n    select:\n        a = rows.id\n",
        (
            ("PIE-B1003", "scalar_projection_requires_later_slice"),
            ("PIE-B1004", "match_reference_logical_type_missing"),
            ("PIE-B1004", "match_reference_logical_type_missing"),
            ("PIE-B1003", "match_condition_not_in_row_domain"),
            ("PIE-B1003", "join_shape_not_admitted_in_slice7"),
            ("PIE-B1003", "representation_not_in_initial_domain"),
        ),
        source=lambda s: (
            s.replace("    money: Decimal(9, 2)\n", "    money: Status\n")
            + "enum Status:\n    active\n    closed\n"
        ),
    ),
    "match_binary": _Before(
        "    from rows\n    let r = rows\n"
        "    left join r on rows.id + 1 == coalesce(r.id, rows.id)\n    select:\n"
        "        a = rows.id\n",
        (
            ("PIE-B1003", "scalar_projection_requires_later_slice"),
            ("PIE-B1003", "match_binary_operator_not_admitted"),
            ("PIE-B1003", "match_condition_not_in_row_domain"),
            ("PIE-B1003", "join_shape_not_admitted_in_slice7"),
        ),
    ),
}


@pytest.mark.parametrize("route", tuple(_REFUSED_BEFORE_THE_BODY))
def test_a_mysql_query_refused_before_its_body_lists_no_typed_declaration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, route: str
) -> None:
    """A MySQL query that emission refuses before it comes to write its body
    reports its other refusals without PIE-B1003 at its Date and UUID
    declarations: the list of the same query without a header."""
    row = _REFUSED_BEFORE_THE_BODY[route]
    _built(monkeypatch, row.contract, row.source)
    typed, plain = (
        typed_case(tmp_path / name, "mysql", row.upstream + header + row.block)[1]
        for name, header in (
            ("typed", "query result(day: Date, key: UUID):\n"),
            ("plain", "query result:\n"),
        )
    )
    assert typed.status == "BLOCKED"
    assert [(b.code, b.detail) for b in typed.blockers] == list(row.refusals)
    assert _listed(typed) == _listed(plain)
