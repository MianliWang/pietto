"""Closed project-SQL witnesses for the adopted scalar expression surface."""

from copy import copy
from dataclasses import replace
import json

import pytest

import _pietto_sql_emission as probe
import _pietto_results_product as temporal_probe
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_portable as portable
from pietto._project import project_sql_emission_pure_boundary as pure
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_sql_emission import (
    emit_project_sql,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_ast import RowValueColumn, SQLRowQuery
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)


TARGETS = ("postgres", "mysql")


def graft(value, **changes):
    result = copy(value)
    for name, changed in changes.items():
        object.__setattr__(result, name, changed)
    return result


def row_query(artifact):
    query = artifact.ast
    assert isinstance(query, SQLRowQuery)
    return query


def emit(tmp_path, target, body, policy="preserve_literals"):
    """Run one ordinary selected relation through the installed project path."""
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
    return probe.build_case(
        tmp_path,
        header + body,
        probe.encoded(contract).decode(),
        policy,
    )


Q1_BODY = """table result:
    from rows
    let lowered = lower(text)
    let uppered = upper(text)
    let trimmed = trim(text)
    let sized = len(text)
    let piece = substr(text, 1, 2)
    let replaced = replace(text, text, text)
    let contained = contains(text, text)
    let prefixed = starts_with(text, text)
    let suffixed = ends_with(text, text)
    let selected = id in (id, id)
    let text_membership = text in (text)
    let decimal_membership = money in (money)
    let float_membership = ratio in (ratio)
    let empty_selected = flag in ()
    let empty_excluded = flag not in ()
    let unknown_excluded = flag not in (flag)
    let fallback = coalesce(nullif(text, text), text)
    let null_fallback = coalesce(None, text)
    let null_checked = nullif(text, None)
    let nullable_membership = id in (id, None)
    let branch = text if flag else text
    let negated = not flag
    let widened = Float(id)
    let magnitude = abs(money)
    let direction = sign(money)
    let ranged = id <= id <= id
    let matched = text like text
    let unmatched = text not like text
    select:
        lowered
        uppered
        trimmed
        sized
        piece
        replaced
        contained
        prefixed
        suffixed
        selected
        text_membership
        decimal_membership
        float_membership
        empty_selected
        empty_excluded
        unknown_excluded
        fallback
        null_fallback
        null_checked
        nullable_membership
        branch
        negated
        widened
        magnitude
        direction
        ranged
        matched
        unmatched
"""


C5_POSTGRES_SCALAR_BODY = """table result:
    from rows
    let whole_money = round(money, 0)
    let whole_ratio = round(ratio)
    let decimal_id = Text(id)
    select:
        whole_money
        whole_ratio
        decimal_id
"""


C5_POSTGRES_LET_SCALE_BODY = """table result:
    from rows
    let scale = -1
    let rounded = round(money, scale)
    select:
        rounded
"""


def test_postgres_scalar_project_forms_are_verified(tmp_path):
    checked, outcome = emit(tmp_path, "postgres", C5_POSTGRES_SCALAR_BODY)
    assert checked.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None
    document = json.loads(serialize_project_sql_emission(outcome).decode())
    sql = document["sql"]
    assert "round(" in sql and " AS pg_catalog.int4))" in sql and "trunc(" in sql
    assert 'COLLATE "C"' in sql
    assert (
        probe.decode_public(serialize_project_sql_emission(outcome))["status"]
        == "VERIFIED"
    )
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    )
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )

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
    replayed = emit_compiled(loaded, ())
    assert replayed.request.family == "postgres"


def test_postgres_high_precision_decimal_rounds_emit(tmp_path):
    base = probe.fixture("postgres")
    source = base["source"].replace("money: Decimal(9, 2)", "money: Decimal(65, 30)")
    header = source.split("table result:", 1)[0]
    contract = json.loads(base["contract"])
    representation = contract["sources"][0]["fields"][3]["representation"]
    representation["storage"].update(precision=65, scale=30)
    representation["domain"].update(precision=65, scale=30)
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact",
        }
    )
    source = (
        header
        + """table result:
    from rows
    select:
        default = round(money)
        explicit_zero = round(money, 0)
        retained_scale = round(money, 30)
"""
    )

    _, outcome = probe.build_case(
        tmp_path,
        source,
        probe.encoded(contract).decode(),
        "preserve_literals",
    )
    assert outcome.status == "VERIFIED" and outcome.artifact is not None


def test_postgres_literal_let_scale_survives_compiled_replay(tmp_path):
    checked, outcome = emit(tmp_path, "postgres", C5_POSTGRES_LET_SCALE_BODY)
    assert checked.verified and outcome.status == "VERIFIED"
    assert outcome.artifact is not None

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


def test_postgres_literal_let_date_unit_survives_compiled_replay(tmp_path):
    source = (
        temporal_probe.temporal_source("postgres").split("table result:", 1)[0]
        + """table result:
    from rows
    let unit = "month"
    let month_stamp = date_trunc(unit, stamp)
    select:
        month_stamp
"""
    )
    checked = temporal_probe.build_neutral(
        tmp_path / "project", {"main.pietto": source}
    )
    contract = json.loads(temporal_probe.temporal_input("postgres"))
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact",
        }
    )
    outcome = emit_project_sql(checked, json.dumps(contract).encode())
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    assert (
        probe.decode_public(serialize_project_sql_emission(outcome))["status"]
        == "VERIFIED"
    )

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


def test_postgres_date_trunc_date_units_preserve_date_carrier(tmp_path):
    source = (
        temporal_probe.temporal_source("postgres").split("table result:", 1)[0]
        + """table result:
    from rows
    let day = date_of(stamp)
    select:
        date_year = date_trunc("year", day)
        date_month = date_trunc("month", day)
        date_day = date_trunc("day", day)
"""
    )
    checked = temporal_probe.build_neutral(
        tmp_path / "project", {"main.pietto": source}
    )
    contract = json.loads(temporal_probe.temporal_input("postgres"))
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact",
        }
    )
    outcome = emit_project_sql(checked, json.dumps(contract).encode())
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    sql = json.loads(serialize_project_sql_emission(outcome))["sql"]
    assert sql.count(" AS timestamp)) AS date)") == 3
    assert verify_project_sql_emission(
        outcome.artifact, outcome.artifact.request
    ).verified
    assert (
        probe.decode_public(serialize_project_sql_emission(outcome))["status"]
        == "VERIFIED"
    )

    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    )
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, outcome.artifact, outcome.artifact.request
    ).corresponds

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


ORDER_BODY = """query result:
    from rows
    select:
        text
        label = lower(text)
    order by:
        lower(text) desc
"""


HIDDEN_ORDER_BODY = """query result:
    from rows
    select:
        label = lower(text)
    order by:
        lower(text) desc
"""


NULL_BIND_BODY = """table result:
    from rows
    select:
        nullable_membership = id in (1, None)
"""


ALL_NULL_BODY = """table result:
    from rows
    select:
        unknown = coalesce(None, None)
"""


NESTED_BOOL_CALL_BODY = """table result:
    from rows
    select:
        matched = contains(text, text) in (starts_with(text, text), ends_with(text, text))
"""


POSTGRES_WIDE_SUBSTRING_INDEX_BODY = """table result:
    from rows
    select:
        piece = substr(text, 2147483648, 1)
"""


@pytest.mark.parametrize("target", TARGETS)
def test_q1_scalar_surface_is_verified_through_both_project_targets(tmp_path, target):
    checked, outcome = emit(tmp_path, target, Q1_BODY)
    assert checked.verified
    assert outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds

    document = probe.decode_public(serialize_project_sql_emission(outcome))
    labels = [column["label"] for column in document["columns"]]
    assert labels == [
        "lowered",
        "uppered",
        "trimmed",
        "sized",
        "piece",
        "replaced",
        "contained",
        "prefixed",
        "suffixed",
        "selected",
        "text_membership",
        "decimal_membership",
        "float_membership",
        "empty_selected",
        "empty_excluded",
        "unknown_excluded",
        "fallback",
        "null_fallback",
        "null_checked",
        "nullable_membership",
        "branch",
        "negated",
        "widened",
        "magnitude",
        "direction",
        "ranged",
        "matched",
        "unmatched",
    ]
    logical = {column["label"]: column for column in document["columns"]}
    assert logical["widened"]["logical_type"]["name"] == "Float"
    assert logical["magnitude"]["logical_type"]["name"] == "Decimal"
    assert logical["direction"]["logical_type"]["name"] == "Int"
    for label in (
        "contained",
        "prefixed",
        "suffixed",
        "selected",
        "text_membership",
        "decimal_membership",
        "float_membership",
        "empty_selected",
        "empty_excluded",
        "unknown_excluded",
        "nullable_membership",
        "negated",
        "ranged",
        "matched",
        "unmatched",
    ):
        assert logical[label]["logical_type"]["name"] == "Bool"

    # Empty membership has its adopted constant truth value even for nullable
    # lhs; ordinary NOT IN and NOT retain the three-valued Bool carrier.
    assert logical["empty_selected"]["nullable"] is False
    assert logical["empty_excluded"]["nullable"] is False
    assert logical["unknown_excluded"]["nullable"] is not False
    assert logical["nullable_membership"]["nullable"] is not False
    assert logical["negated"]["nullable"] is not False
    sql = document["sql"]
    assert "CASE WHEN " in sql and " ESCAPE '!'" in sql
    assert " IS TRUE" not in sql and " IS FALSE" not in sql
    assert "TRUE" in sql and "NOT IN" in sql and "NOT " in sql
    if target == "postgres":
        assert "CAST(length(" in sql
        assert sql.count(" AS pg_catalog.int4)") == 2
    else:
        assert "CAST(CHAR_LENGTH(" in sql

    values = [
        column.value
        for body in row_query(artifact).bodies
        for column in body.columns
        if type(column) is RowValueColumn and type(column.value) is rows.SQLOperation
    ]
    branch = next(value for value in values if value.kind == "conditional")
    empty_selected = next(
        value
        for value in values
        if value.kind == "membership"
        and not value.original.expression.negated
        and len(value.operands) == 1
    )
    selected = next(
        value
        for value in values
        if value.kind == "membership"
        and not value.original.expression.negated
        and len(value.operands) == 3
        and not any(type(operand) is parameters.SQLNull for operand in value.operands)
    )
    lowered = next(
        value
        for value in values
        if value.kind == "scalar_call" and value.original.callee_symbol.name == "lower"
    )
    assert branch.original.expression is not None and len(branch.operands) == 3
    assert type(empty_selected.operands[0]) is rows.SQLStageReference
    assert len(selected.operands) == 3
    assert (
        len(
            [
                value
                for value in values
                if any(
                    type(operand) is parameters.SQLNull for operand in value.operands
                )
            ]
        )
        == 3
    )
    assert lowered.original.callee_symbol.name == "lower"
    assert "CAST(NULL" not in sql


@pytest.mark.parametrize("target", TARGETS)
def test_q1_nested_boolean_calls_are_closed_sql_expressions(tmp_path, target):
    checked, outcome = emit(tmp_path, target, NESTED_BOOL_CALL_BODY)
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    sql = probe.decode_public(serialize_project_sql_emission(outcome))["sql"]
    if target == "postgres":
        assert "(strpos(" in sql and ") > 0)" in sql
        assert "(left(" in sql and "(right(" in sql
    else:
        assert "(INSTR(" in sql and ") > 0)" in sql
        assert "(LEFT(" in sql and "(RIGHT(" in sql


def test_q1_postgres_substring_refuses_an_index_outside_int4(tmp_path):
    checked, outcome = emit(tmp_path, "postgres", POSTGRES_WIDE_SUBSTRING_INDEX_BODY)
    assert checked.verified
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [blocker.detail for blocker in outcome.blockers] == [
        "substring_index_outside_physical_range"
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_q1_timestamp_civil_parts_preserve_the_exact_timestamp6_carrier(
    tmp_path, target
):
    source = (
        temporal_probe.temporal_source(target).split("table result:", 1)[0]
        + """table result:
    from rows
    select:
        year_part = year(stamp)
        month_part = month(stamp)
        day_part = day(stamp)
        hour_part = hour(stamp)
        minute_part = minute(stamp)
"""
    )
    checked = temporal_probe.build_neutral(tmp_path / target, {"main.pietto": source})
    outcome = emit_project_sql(checked, temporal_probe.temporal_input(target))

    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    assert verify_project_sql_emission(
        outcome.artifact, outcome.artifact.request
    ).verified
    observed = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    )
    assert observed.status is portable.ObservationStatus.OK
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, outcome.artifact, outcome.artifact.request
    ).corresponds
    values = [
        column.value
        for body in row_query(outcome.artifact).bodies
        for column in body.columns
        if type(column) is RowValueColumn
    ]
    bounds = {
        "year": (1000, 9999),
        "month": (1, 12),
        "day": (1, 31),
        "hour": (0, 23),
        "minute": (0, 59),
    }
    for value in values:
        assert value.kind == "scalar_call"
        name = value.original.callee_symbol.name
        assert value.realization.tag == "Int"
        assert (value.realization.domain["min"], value.realization.domain["max"]) == (
            str(bounds[name][0]),
            str(bounds[name][1]),
        )

    sql = outcome.artifact.rendered.sql.decode()
    if target == "postgres":
        assert "CAST(EXTRACT(YEAR FROM" in sql
        assert "AS pg_catalog.int8)" in sql
    else:
        assert "CAST(YEAR(" in sql
        assert "AS SIGNED)" in sql


@pytest.mark.parametrize("target", TARGETS)
def test_date_of_derives_the_date_result_carrier_and_civil_parts(tmp_path, target):
    source = (
        temporal_probe.temporal_source(target).split("table result:", 1)[0]
        + """table result:
    from rows
    let civil_date = date_of(stamp)
    let nullable_date = date_of(optional_stamp)
    let null_date = date_of(None)
    select:
        civil_date
        nullable_date
        null_date
        year_part = year(civil_date)
        month_part = month(civil_date)
        day_part = day(civil_date)
"""
    )
    checked = temporal_probe.build_neutral(tmp_path / target, {"main.pietto": source})
    contract = json.loads(temporal_probe.temporal_input(target))
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    outcome = emit_project_sql(checked, json.dumps(contract).encode())

    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    assert verify_project_sql_emission(
        outcome.artifact, outcome.artifact.request
    ).verified
    values = [
        column.value
        for body in row_query(outcome.artifact).bodies
        for column in body.columns
        if type(column) is RowValueColumn
    ]
    dates = [
        value
        for value in values
        if type(value) is rows.SQLOperation
        and value.kind == "scalar_call"
        and value.original.callee_symbol.name == "date_of"
    ]
    assert [value.realization.tag for value in dates] == ["Date", "Date", "Date"]
    assert [value.realization.nullable for value in dates] == [False, True, True]
    assert all(
        value.realization.storage
        == {"kind": "pg_date" if target == "postgres" else "my_date"}
        and value.realization.domain == {"kind": "date"}
        for value in dates
    )
    parts = [
        value
        for value in values
        if type(value) is rows.SQLOperation
        and value.kind == "scalar_call"
        and value.original.callee_symbol.name in {"year", "month", "day"}
    ]
    assert {
        value.original.callee_symbol.name: (
            value.realization.domain["min"],
            value.realization.domain["max"],
        )
        for value in parts
    } == {"year": ("1000", "9999"), "month": ("1", "12"), "day": ("1", "31")}

    sql = outcome.artifact.rendered.sql.decode()
    if target == "postgres":
        assert 'CAST("s0"."stamp" AS date)' in sql
        assert "EXTRACT(YEAR FROM" in sql
    else:
        assert "DATE(`s0`.`stamp`)" in sql
        assert "YEAR(" in sql
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [column["logical_type"]["name"] for column in document["columns"]][:3] == [
        "Date",
        "Date",
        "Date",
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_a_date_field_is_an_independent_selected_project_source(tmp_path, target):
    source = f"""shape Row:
    event_date: Date | None
source rows: Row = {target}.table("opaque.result.fixture")
table result:
    from rows
    select:
        event_date
"""
    checked = temporal_probe.build_neutral(tmp_path / target, {"main.pietto": source})
    contract = json.loads(temporal_probe.temporal_input(target))
    field = contract["sources"][0]["fields"][0]
    field.update(name="event_date", column="event_date")
    field["representation"] = {
        "storage": {"kind": "pg_date" if target == "postgres" else "my_date"},
        "nullable": True,
        "domain": {"kind": "date"},
    }
    contract["sources"][0]["fields"] = [field]
    contract["environment"].append(
        {
            "key": "identifier_case",
            "scope": "statement",
            "value": "quoted_exact"
            if target == "postgres"
            else "lower_case_table_names=0",
        }
    )
    outcome = emit_project_sql(checked, json.dumps(contract).encode())

    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [c["representation"] for c in document["columns"]] == [
        field["representation"]
    ]
    # The same Date field described as a Timestamp carrier is not its source.
    field["representation"] = {
        "storage": {
            "kind": "pg_timestamp" if target == "postgres" else "my_datetime",
            "fractional_seconds": 6,
        },
        "nullable": True,
        "domain": {"kind": "timestamp"},
    }
    outcome = emit_project_sql(checked, json.dumps(contract).encode())
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [(b.code, b.detail) for b in outcome.blockers] == [
        ("PIE-B1002", "physical_storage_or_domain_mismatch")
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_q1_computed_order_keeps_its_selected_expression_and_direction(
    tmp_path, target
):
    checked, outcome = emit(tmp_path, target, ORDER_BODY)
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [column["label"] for column in document["columns"]] == ["text", "label"]
    sql = document["sql"]
    assert "ORDER BY" in sql and "DESC" in sql
    assert "lower(" in sql if target == "postgres" else "LOWER(" in sql


@pytest.mark.parametrize("target", TARGETS)
def test_q1_computed_order_refuses_hidden_input_reuse(tmp_path, target):
    checked, outcome = emit(tmp_path, target, HIDDEN_ORDER_BODY)
    assert checked.verified
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [blocker.detail for blocker in outcome.blockers] == [
        "order_expression_requires_established_port"
    ]


@pytest.mark.parametrize("target", TARGETS)
def test_contextual_null_is_literal_not_native_parameter(tmp_path, target):
    checked, outcome = emit(
        tmp_path, target, NULL_BIND_BODY, policy="bind_safe_literals"
    )
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert len(document["fixed_values"]) == len(document["parameter_uses"]) == 1
    assert "NULL" in document["sql"]
    if target == "postgres":
        assert "$1" in document["sql"]
    else:
        assert document["sql"].count("?") == 1
    value = next(
        column.value
        for body in row_query(artifact).bodies
        for column in body.columns
        if type(column) is RowValueColumn
    )
    assert value.kind == "membership" and len(value.operands) == 3
    assert type(value.operands[-1]) is parameters.SQLNull


@pytest.mark.parametrize("target", TARGETS)
def test_all_null_q1_call_remains_fail_closed(tmp_path, target):
    checked, outcome = emit(tmp_path, target, ALL_NULL_BODY)
    assert not checked.verified
    assert outcome.status == "BLOCKED" and outcome.artifact is None


@pytest.mark.parametrize("tag", ("Any", "Bytes", "Json"))
def test_q1_membership_refuses_types_without_a_reviewed_sql_equality(tag):
    value = rows.Realization(
        tag,
        {"kind": "unreviewed"},
        False,
        {"kind": "unreviewed"},
    )
    result, problem = rows.resolved_membership_realization(
        "postgres", "Bool", False, (value, value)
    )
    assert result is None
    assert problem == ("PIE-B1003", "membership_type_pair_not_admitted")


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("mutation", ("operands", "callee", "rendered_sql"))
def test_q1_scalar_ast_and_bytes_tampering_are_rejected(tmp_path, target, mutation):
    _, outcome = emit(tmp_path, target, Q1_BODY)
    artifact = outcome.artifact
    assert artifact is not None
    body_index, lower = next(
        (index, column)
        for index, body in enumerate(row_query(artifact).bodies)
        for column in body.columns
        if type(column) is RowValueColumn
        and type(column.value) is rows.SQLOperation
        and column.value.kind == "scalar_call"
        and column.value.original.callee_symbol.name == "lower"
    )
    query = row_query(artifact)
    body = query.bodies[body_index]
    if mutation == "operands":
        changed_value = graft(lower.value, operands=())
        changed = replace(
            artifact,
            ast=replace(
                query,
                bodies=tuple(
                    replace(
                        body,
                        columns=tuple(
                            replace(column, value=changed_value)
                            if column is lower
                            else column
                            for column in body.columns
                        ),
                    )
                    if index == body_index
                    else current
                    for index, current in enumerate(query.bodies)
                ),
            ),
        )
    elif mutation == "callee":
        changed_expression = graft(
            lower.value.original,
            callee_symbol=graft(lower.value.original.callee_symbol, name="upper"),
        )
        changed_value = graft(lower.value, original=changed_expression)
        changed = replace(
            artifact,
            ast=replace(
                query,
                bodies=tuple(
                    replace(
                        body,
                        columns=tuple(
                            replace(column, value=changed_value)
                            if column is lower
                            else column
                            for column in body.columns
                        ),
                    )
                    if index == body_index
                    else current
                    for index, current in enumerate(query.bodies)
                ),
            ),
        )
    else:
        sql = artifact.rendered.sql
        before = b"lower(" if target == "postgres" else b"LOWER("
        after = b"upper(" if target == "postgres" else b"UPPER("
        changed_sql = sql.replace(before, after, 1)
        assert changed_sql != sql
        changed = replace(
            artifact,
            rendered=replace(
                artifact.rendered,
                sql=changed_sql,
            ),
        )
    verified = verify_project_sql_emission(changed, artifact.request).verified
    assert verified is False


TEXT_CARRIER_BODY = """table result:
    from rows
    let coalesced = coalesce(text, "x")
    let null_checked = nullif(text, "x")
    let fallback = coalesce(nullif(trim(text), ""), text, "anonymous")
    let null_fallback = coalesce(None, "x", text)
    let branch = text if flag else "x"
    let nested = "unknown" if flag else ("adult" if flag else "minor")
    let text_member = text in ("x")
    let bool_member = flag in (True)
    select:
        coalesced
        null_checked
        fallback
        null_fallback
        branch
        nested
        text_member
        bool_member
"""


SCALAR_CARRIER_BODY = """table result:
    from rows
    let coalesced = coalesce(id, 1)
    let null_checked = nullif(id, 1)
    let branch = id if flag else 1
    let bool_coalesced = coalesce(flag, True)
    let bool_checked = nullif(flag, True)
    let bool_branch = flag if flag else True
    select:
        coalesced
        null_checked
        branch
        bool_coalesced
        bool_checked
        bool_branch
"""


BIND_SAFE_CALL_BODY = """table result:
    from rows
    select:
        piece = substr(text, 1, 2)
        replaced = replace(text, "x", "y")
        contained = contains(text, "x")
        prefixed = starts_with(text, "x")
        suffixed = ends_with(text, "x")
"""


TEXT_GROWTH_BODY = """table result:
    from rows
    select:
        growing = replace(text, text, text)
        reverse_coalesced = coalesce("x", text)
"""


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_q1_text_carriers_accept_compatible_widths_nulls_and_membership(
    tmp_path, target, policy
):
    checked, outcome = emit(tmp_path, target, TEXT_CARRIER_BODY, policy)
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified

    document = probe.decode_public(serialize_project_sql_emission(outcome))
    columns = {column["label"]: column for column in document["columns"]}
    for label, width in {
        "coalesced": 64,
        "null_checked": 64,
        "fallback": 64,
        "null_fallback": 64,
        "branch": 64,
        "nested": 7,
    }.items():
        representation = columns[label]["representation"]
        assert representation["domain"]["max_characters"] == width
        if target == "mysql":
            assert representation["storage"] == {"kind": "my_varchar", "length": width}
    assert columns["text_member"]["logical_type"]["name"] == "Bool"
    assert columns["bool_member"]["logical_type"]["name"] == "Bool"


@pytest.mark.parametrize("target", TARGETS)
def test_q1_bind_safe_scalar_call_literals_remain_verified_call_arguments(
    tmp_path, target
):
    checked, outcome = emit(
        tmp_path, target, BIND_SAFE_CALL_BODY, policy="bind_safe_literals"
    )
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    assert artifact.fixed_values == () and artifact.parameter_uses == ()
    call_sites = tuple(
        site
        for site in artifact.request.plan.literal_sites
        if any(
            type(parent).__name__ == "CallExpr" for parent, _ in site.position.ancestry
        )
    )
    assert any(
        site.reason is not None and site.reason.value == "call_argument_subtree"
        for site in call_sites
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_q1_text_result_growth_uses_the_derived_bound_not_input_length(
    tmp_path, target, policy
):
    checked, outcome = emit(tmp_path, target, TEXT_GROWTH_BODY, policy)
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified

    document = probe.decode_public(serialize_project_sql_emission(outcome))
    columns = {column["label"]: column for column in document["columns"]}
    for label, width in {"growing": 4096, "reverse_coalesced": 64}.items():
        representation = columns[label]["representation"]
        assert representation["domain"]["max_characters"] == width
        if target == "mysql":
            assert representation["storage"] == {"kind": "my_varchar", "length": width}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_q1_int_and_bool_carriers_accept_compatible_literal_anchors(
    tmp_path, target, policy
):
    checked, outcome = emit(tmp_path, target, SCALAR_CARRIER_BODY, policy)
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified

    document = probe.decode_public(serialize_project_sql_emission(outcome))
    columns = {column["label"]: column for column in document["columns"]}
    for label in ("coalesced", "null_checked", "branch"):
        assert columns[label]["logical_type"]["name"] == "Int"
    for label in ("bool_coalesced", "bool_checked", "bool_branch"):
        assert columns[label]["logical_type"]["name"] == "Bool"
    if target == "mysql":
        assert columns["coalesced"]["representation"]["storage"] == {
            "kind": "my_signed_int"
        }
        assert columns["null_checked"]["representation"]["storage"] == {
            "kind": "my_bigint"
        }


@pytest.mark.parametrize(
    ("family", "storage", "domain"),
    (
        (
            "postgres",
            {"kind": "pg_text"},
            {
                "kind": "text",
                "max_characters": 1,
                "encoding": "UTF8",
                "collation": "bad",
                "padding": "NO PAD",
            },
        ),
        (
            "mysql",
            {"kind": "my_utf8mb4_text"},
            {
                "kind": "text",
                "max_characters": 1,
                "encoding": "utf8mb4",
                "collation": "bad",
                "padding": "NO PAD",
            },
        ),
    ),
)
def test_q1_text_carrier_rejects_collation_tampering(family, storage, domain):
    field = rows.Realization(
        "Text",
        {"kind": "pg_text"}
        if family == "postgres"
        else {"kind": "my_varchar", "length": 64},
        False,
        {
            "kind": "text",
            "max_characters": 64,
            "encoding": "UTF8" if family == "postgres" else "utf8mb4",
            "collation": "C" if family == "postgres" else "utf8mb4_0900_bin",
            "padding": "NO PAD",
        },
    )
    literal = rows.Realization("Text", storage, False, domain)
    result, problem = rows.resolved_membership_realization(
        family, "Bool", False, (field, literal)
    )
    assert result is None
    assert problem == ("PIE-B1003", "membership_type_pair_not_admitted")


COEXISTING_MEMBERSHIP = """query ids:
    from rows
    select:
        id
table result:
    from rows
    where id in (id, 0) and id not in ids
    select:
        listed = id in (1, None)
        read = id in ids
"""
COEXISTING_SQL = {
    "postgres": (
        'WITH "p0" ("c0") AS (SELECT "s0"."order.id" AS "c0" '
        'FROM "public"."phase66 source é" AS "s0"), '
        '"p1" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "s1"."order.id" AS "c0", '
        '"s1"."flag value" AS "c1", "s1"."text `""é" AS "c2", '
        '"s1"."amount value" AS "c3", "s1"."ratio value" AS "c4" '
        'FROM "public"."phase66 source é" AS "s1" '
        'WHERE (("s1"."order.id" IN ("s1"."order.id", CAST(0 AS pg_catalog.int8))) '
        'AND ("s1"."order.id" NOT IN (SELECT "e0"."c0" FROM "p0" AS "e0")))) '
        'SELECT ("t2"."c0" IN (CAST(1 AS pg_catalog.int8), NULL)) AS "listed", '
        '("t2"."c0" IN (SELECT "e1"."c0" FROM "p0" AS "e1")) AS "read" '
        'FROM "p1" AS "t2"'
    ),
    "mysql": (
        "WITH `p0` (`c0`) AS (SELECT `s0`.`order.id` AS `c0` "
        "FROM `phase66`.`phase66 source é` AS `s0`), "
        "`p1` (`c0`, `c1`, `c2`, `c3`, `c4`) AS (SELECT `s1`.`order.id` AS `c0`, "
        '`s1`.`flag value` AS `c1`, `s1`.`text ``"é` AS `c2`, '
        "`s1`.`amount value` AS `c3`, `s1`.`ratio value` AS `c4` "
        "FROM `phase66`.`phase66 source é` AS `s1` "
        "WHERE ((`s1`.`order.id` IN (`s1`.`order.id`, CAST(0 AS SIGNED))) "
        "AND (`s1`.`order.id` NOT IN (SELECT `e0`.`c0` FROM `p0` AS `e0`)))) "
        "SELECT (`t2`.`c0` IN (CAST(1 AS SIGNED), NULL)) AS `listed`, "
        "(`t2`.`c0` IN (SELECT `e1`.`c0` FROM `p0` AS `e1`)) AS `read` "
        "FROM `p1` AS `t2`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
def test_literal_list_and_relation_membership_stay_distinct(tmp_path, target):
    from pietto._project import project_sql_plan_expressions as plan_rows
    from pietto._project.project_sql_plan import ProjectSQLPlan

    checked, outcome = emit(tmp_path, target, COEXISTING_MEMBERSHIP)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == COEXISTING_SQL[target]
    plan = checked.plan
    assert isinstance(plan, ProjectSQLPlan)
    kinds = [
        type(expression).__name__
        for expression in plan.expressions
        if type(expression)
        in {plan_rows.ProjectSQLMembership, plan_rows.ProjectSQLRelationMembership}
    ]
    # Each written form keeps its own node: a relation read is never folded
    # into literal options, and a literal list never reads a relation.
    assert kinds == [
        "ProjectSQLMembership",
        "ProjectSQLRelationMembership",
        "ProjectSQLMembership",
        "ProjectSQLRelationMembership",
    ]
    assert [(c["label"], c["nullable"]) for c in document["columns"]] == [
        ("listed", True),
        ("read", True),
    ]


DECIMAL_INT_READS = """query ids:
    from rows
    select:
        id
query monies:
    from rows
    select:
        money
"""


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("body", "expected"),
    (
        (
            "table result:\n    from rows\n    where money in (1, 2)\n"
            "    select:\n        id\n",
            ("membership_type_pair_not_admitted", 10, 5),
        ),
        (
            "table result:\n    from rows\n    select:\n        id\n"
            "        f = id not in (money, 3)\n",
            ("membership_type_pair_not_admitted", 12, 9),
        ),
        (
            "table result:\n    from rows\n    where money in (1, None)\n"
            "    select:\n        id\n",
            ("membership_type_pair_not_admitted", 10, 5),
        ),
        (
            DECIMAL_INT_READS + "table result:\n    from rows\n"
            "    where money in ids\n    select:\n        id\n",
            ("membership_type_pair_not_admitted", 18, 5),
        ),
        (
            DECIMAL_INT_READS + "table result:\n    from rows\n    select:\n"
            "        id\n        f = id not in monies\n",
            ("membership_type_pair_not_admitted", 20, 9),
        ),
    ),
    ids=("list", "list_not_in", "list_null", "read", "read_not_in"),
)
def test_decimal_int_membership_checks_and_is_refused_like_its_comparison(
    tmp_path, target, body, expected
):
    # `check --project` accepts a Decimal and an Int as it accepts
    # `money == 1`, and project SQL refuses the pair as it refuses that
    # comparison (`comparison_type_pair_not_admitted`).
    _, outcome = emit(tmp_path, target, body)
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "BLOCKED" and document["diagnostics"] == []
    assert [
        (
            b["code"],
            b["subject"]["detail"],
            b["location"]["line"],
            b["location"]["column"],
        )
        for b in document["blockers"]
    ] == [("PIE-B1003", *expected)]


# A project that calls defs, and the same project with each call written out
# by hand: fixture, variant, defs, edits for the calls, edits written out.
ROW_NUMBER = "row_number() window(order by id)\n"
RANK = "rank() window(order by id)\n"
DEF_PROJECTS = {
    "row_body": (
        "T_row_direct",
        "table_preserve",
        "def small(n: Int) -> Bool | None: return n > 0 and n < 1000\n"
        "def both(a: Int, b: Int) -> Bool | None: "
        "return small(a) and small(b)\n"
        "def label(t: Text, f: Bool | None) -> Text: "
        'return "on" if f is None else lower(t)\n'
        "def next_of(n: Int) -> Int | None: return n + 1\n",
        [
            ("bumped = id + 1", "bumped = next_of(id)"),
            ("where id > 0", "where both(id, id) and small(id)"),
            ("positive = id > 0", "positive = label(text, flag) == label(text, flag)"),
        ],
        [
            ("bumped = id + 1", "bumped = (id + 1)"),
            (
                "where id > 0",
                "where ((id > 0 and id < 1000) and (id > 0 and id < 1000)) and "
                "(id > 0 and id < 1000)",
            ),
            (
                "positive = id > 0",
                'positive = ("on" if flag is None else lower(text)) == '
                '("on" if flag is None else lower(text))',
            ),
        ],
    ),
    "parameter_named_like_a_function": (
        "T_row_direct",
        "table_preserve",
        "def f(upper: Text) -> Text: return upper(upper)\n",
        [
            ("doubled = bumped * 2", "doubled = bumped * 2\n    let lower = text"),
            ("same_text = text == text", "same_text = f(lower) == text"),
        ],
        [
            ("doubled = bumped * 2", "doubled = bumped * 2\n    let lower = text"),
            ("same_text = text == text", "same_text = (upper(lower)) == text"),
        ],
    ),
    "reordered_bound_literals": (
        "T_row_direct",
        "query_bind",
        "def btw(lo: Int, hi: Int, n: Int) -> Bool | None: return n < hi and n > lo\n",
        [("where id > 0", "where btw(0, 1000, id) and btw(0, 1000, id)")],
        [
            (
                "where id > 0",
                "where (id < 1000 and id > 0) and (id < 1000 and id > 0)",
            )
        ],
    ),
    "grouped_let_key": (
        "Y_aggregate_computed",
        "let_key",
        "def bucket_of(k: Int | None) -> Int: return 1 if k > 1 else 0\n",
        [("bucket = 1 if key > 1 else 0", "bucket = bucket_of(key)")],
        [("bucket = 1 if key > 1 else 0", "bucket = (1 if key > 1 else 0)")],
    ),
    "satisfying": (
        "Y_aggregate_satisfying",
        "retained",
        "def small(t: Int) -> Bool | None: return t < 2\n",
        [("total < 2 and lo > 5", "small(total) and lo > 5")],
        [("total < 2 and lo > 5", "(total < 2) and lo > 5")],
    ),
    "qualify": (
        "A_window_qualify",
        "selected",
        "def top(n: Int) -> Bool | None: return n <= 2\n",
        [("numbered <= 2", "top(numbered)")],
        [("numbered <= 2", "(numbered <= 2)")],
    ),
    "qualify_window_argument_used_twice": (
        "A_window_qualify",
        "selected",
        "def both(x: Int) -> Bool | None: return x <= 2 and x <= 3\n",
        [("        numbered <= 2\n", "        both(" + ROW_NUMBER + "        )\n")],
        [
            (
                "        numbered <= 2\n",
                "        (("
                + ROW_NUMBER
                + "        ) <= 2 and ("
                + ROW_NUMBER
                + "        ) <= 3)\n",
            )
        ],
    ),
    "qualify_window_arguments_reordered": (
        "A_window_qualify",
        "selected",
        "def swap(a: Int, b: Int) -> Bool | None: return b <= 2 and a <= 3\n",
        [
            (
                "        numbered <= 2\n",
                "        swap(" + ROW_NUMBER + "        , " + RANK + "        )\n",
            )
        ],
        [
            (
                "        numbered <= 2\n",
                "        (("
                + RANK
                + "        ) <= 2 and ("
                + ROW_NUMBER
                + "        ) <= 3)\n",
            )
        ],
    ),
    "join_on": (
        "W_join_values",
        "left_marker",
        "def same(a: Int, b: Int) -> Bool | None: return a == b\n",
        [("on rows.id == r.pid", "on same(rows.id, r.pid)")],
        [("on rows.id == r.pid", "on (rows.id == r.pid)")],
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("case", "variant", "defs", "called", "written"),
    DEF_PROJECTS.values(),
    ids=DEF_PROJECTS,
)
def test_def_calls_emit_the_project_sql_of_the_calls_written_out(
    tmp_path, target, case, variant, defs, called, written
):
    item = probe.fixture(target, case, variant)
    documents = []
    for name, edits, extra in (("called", called, defs), ("written", written, "")):
        source = item["source"]
        for old, new in edits:
            assert source.count(old) == 1
            source = source.replace(old, new)
        _, outcome = probe.build_case(
            tmp_path / name, source + extra, item["contract"], item["policy"]
        )
        documents.append(json.loads(serialize_project_sql_emission(outcome)))
    assert documents[0]["status"] == documents[1]["status"] == "VERIFIED"
    for key in ("sql", "columns", "fixed_values", "parameter_uses", "requirements"):
        assert documents[0][key] == documents[1][key], key


_CHAIN_SELECT = "query result:\n    from lhs\n{join}    select:\n        a = lhs.id\n"
_CHAIN_JOIN = _CHAIN_SELECT.format(join="    cross join rhs\n")
_CHAIN_PLAIN = _CHAIN_SELECT.format(join="")
_CHAIN_QUALIFY = "    qualify:\n        {}\n"
_ROW_NUMBER = "row_number() window(order by lhs.id)"
_CLAMP = "def clamp(v: Int) -> Int | None: return v if v < 10 else 10\n"
CHAIN_PROJECTS = {
    "select": (
        _CHAIN_PLAIN + "        inside = 0 < lhs.id < 10\n",
        _CHAIN_PLAIN + "        inside = 0 < lhs.id and lhs.id < 10\n",
    ),
    "join_select": (
        _CHAIN_JOIN + "        inside = 0 < lhs.id < rhs.id\n",
        _CHAIN_JOIN + "        inside = 0 < lhs.id and lhs.id < rhs.id\n",
    ),
    "join_four_operands": (
        _CHAIN_JOIN + "        inside = 0 < lhs.id < 10 < rhs.id\n",
        _CHAIN_JOIN + "        inside = 0 < lhs.id and lhs.id < 10 and 10 < rhs.id\n",
    ),
    "join_where": (
        _CHAIN_JOIN.replace(
            "    select:", "    where 0 < lhs.id < rhs.id\n    select:"
        ),
        _CHAIN_JOIN.replace(
            "    select:", "    where 0 < lhs.id and lhs.id < rhs.id\n    select:"
        ),
    ),
    "join_on": (
        _CHAIN_SELECT.format(join="    inner join rhs on lhs.id < rhs.id < 10\n"),
        _CHAIN_SELECT.format(
            join="    inner join rhs on lhs.id < rhs.id and rhs.id < 10\n"
        ),
    ),
    "outer_nullable_operand": (
        _CHAIN_SELECT.format(join="    left join rhs on lhs.id == rhs.id\n")
        + "        inside = 0 < rhs.key < lhs.id\n",
        _CHAIN_SELECT.format(join="    left join rhs on lhs.id == rhs.id\n")
        + "        inside = 0 < rhs.key and rhs.key < lhs.id\n",
    ),
    "qualify": (
        _CHAIN_PLAIN + _CHAIN_QUALIFY.format(f"0 < {_ROW_NUMBER} < 3"),
        _CHAIN_PLAIN
        + _CHAIN_QUALIFY.format(f"0 < {_ROW_NUMBER} and {_ROW_NUMBER} < 3"),
    ),
    "join_qualify": (
        _CHAIN_JOIN + _CHAIN_QUALIFY.format(f"0 < {_ROW_NUMBER} < 3"),
        _CHAIN_JOIN + _CHAIN_QUALIFY.format(f"0 < {_ROW_NUMBER} and {_ROW_NUMBER} < 3"),
    ),
    # The body uses its parameter twice in each copy of the operand.
    "def_call_operand": (
        _CLAMP + _CHAIN_PLAIN + "        inside = 0 < clamp(lhs.id) < 5\n",
        _CLAMP
        + _CHAIN_PLAIN
        + "        inside = 0 < clamp(lhs.id) and clamp(lhs.id) < 5\n",
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("chain", "written"), CHAIN_PROJECTS.values(), ids=CHAIN_PROJECTS
)
def test_comparison_chains_emit_the_project_sql_of_their_comparisons_written_out(
    tmp_path, target, chain, written
):
    """``a < b < c`` is ``a < b and b < c``: each comparison reads its own
    occurrence of ``b``, so a chain emits exactly the SQL of that form."""
    documents = []
    for name, body in (("chain", chain), ("written", written)):
        item = probe.join_witness(target, body)
        _, outcome = probe.build_case(
            tmp_path / name, item["source"], item["contract"], item["policy"]
        )
        documents.append(json.loads(serialize_project_sql_emission(outcome)))
    assert documents[0]["status"] == documents[1]["status"] == "VERIFIED"
    for key in ("sql", "columns", "fixed_values", "parameter_uses", "requirements"):
        assert documents[0][key] == documents[1][key], key
    if chain == CHAIN_PROJECTS["select"][0]:
        integer, quote, relation = (
            ("pg_catalog.int8", '"', '"public"."phase66 lhs é"')
            if target == "postgres"
            else ("SIGNED", "`", "`phase66`.`phase66 lhs é`")
        )
        field = f"{quote}s0{quote}.{quote}order.id{quote}"
        assert documents[0]["sql"] == (
            f"SELECT {field} AS {quote}a{quote}, ((CAST(0 AS {integer}) < {field}) "
            f"AND ({field} < CAST(10 AS {integer}))) AS {quote}inside{quote} "
            f"FROM {relation} AS {quote}s0{quote}"
        )


# `let r = lhs` then `from r` reads the input as `r`; the query is the one that
# reads `lhs` directly, so its artifact is that query's.
_FROM_ALIAS_TAILS = {
    "select": "    select:\n        a = {0}.id\n        {0}.key\n",
    "where_order": "    where {0}.id > 1\n    select:\n        a = {0}.id\n"
    "    order by:\n        {0}.id\n",
    "group_having": "    group by:\n        {0}.id\n    select:\n        a = {0}.id\n"
    "        n = count()\n    having:\n        n > 1\n",
    "aggregate": "    select:\n        m = max({0}.key)\n",
    "window": "    select:\n        a = {0}.id\n"
    "        n = row_number() window(order by {0}.id)\n",
    "distinct": "    select distinct:\n        a = {0}.id\n",
}
_LET_BODY = (
    "query result:\n    let b:\n{0}        select:\n            a = {1}.id\n"
    "    from b\n    select:\n        a\n"
)
_CAPTURE = (
    "query result:\n    let recent:\n        capture {0}\n        from rhs\n"
    "        where rhs.key == {0}.id\n        select:\n            id\n"
    "{1}    where exists recent\n    select:\n        a = {0}.id\n"
)
FROM_ALIAS_PROJECTS = {
    **{
        name: (
            "query result:\n    let r = lhs\n    from r\n" + tail.format("r"),
            "query result:\n    from lhs\n" + tail.format("lhs"),
        )
        for name, tail in _FROM_ALIAS_TAILS.items()
    },
    "relation_let_body": (
        _LET_BODY.format("        let r = lhs\n        from r\n", "r"),
        _LET_BODY.format("        from lhs\n", "lhs"),
    ),
    "alias_of_a_relation_let": (
        "query result:\n    let b:\n        from lhs\n        select:\n"
        "            id\n    let r = b\n    from r\n    select:\n        a = r.id\n",
        "query result:\n    let b:\n        from lhs\n        select:\n"
        "            id\n    from b\n    select:\n        a = b.id\n",
    ),
    "capture": (
        _CAPTURE.format("r", "    let r = lhs\n    from r\n"),
        _CAPTURE.format("lhs", "    from lhs\n"),
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("alias", "direct"), FROM_ALIAS_PROJECTS.values(), ids=FROM_ALIAS_PROJECTS
)
def test_a_from_alias_emits_the_project_sql_of_the_relation_read_directly(
    tmp_path, target, alias, direct
):
    documents = []
    for name, body in (("alias", alias), ("direct", direct)):
        item = probe.join_witness(target, body)
        _, outcome = probe.build_case(
            tmp_path / name, item["source"], item["contract"], item["policy"]
        )
        documents.append(json.loads(serialize_project_sql_emission(outcome)))
    assert documents[0]["status"] == documents[1]["status"] == "VERIFIED"
    for key in ("sql", "columns", "fixed_values", "parameter_uses", "requirements"):
        assert documents[0][key] == documents[1][key], key


@pytest.mark.parametrize("target", TARGETS)
def test_a_from_alias_qualify_window_keeps_the_binding_spelling(tmp_path, target):
    bodies = (
        "query result:\n    from lhs\n    select:\n        id\n"
        "    qualify row_number() window(order by lhs.id) <= 3\n",
        "query result:\n    let r = lhs\n    from r\n    select:\n        id\n"
        "    qualify row_number() window(order by r.id) <= 3\n",
    )
    documents = []
    for name, body in zip(("direct", "binding"), bodies, strict=True):
        item = probe.join_witness(target, body)
        _, outcome = probe.build_case(
            tmp_path / name, item["source"], item["contract"], item["policy"]
        )
        documents.append(json.loads(serialize_project_sql_emission(outcome)))
    assert {document["status"] for document in documents} == {"VERIFIED"}
    for key in ("sql", "columns", "fixed_values", "parameter_uses", "requirements"):
        assert all(document[key] == documents[0][key] for document in documents), key


# After `let r = lhs` and `from r` the relation's own name is no input: the
# read is the single file's PIE-S2102 and emission is BLOCKED. 0.1.5 and 0.1.6
# projects emitted it as `r.id`.
@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    ("tail", "column"),
    (
        ("    select:\n        a = lhs.id\n", 13),
        (
            "    select:\n        id\n    qualify row_number() window(order by lhs.id) <= 3\n",
            42,
        ),
    ),
    ids=("select", "qualify"),
)
def test_a_from_alias_source_name_is_blocked_with_the_unknown_field(
    tmp_path, target, tail, column
):
    body = "query result:\n    let r = lhs\n    from r\n" + tail
    item = probe.join_witness(target, body)
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    assert document["status"] == "BLOCKED"
    # The read is on the body's last line, after the five lines of shape and
    # sources that the witness puts first.
    line = body.count("\n") + 5
    assert [
        (
            diagnostic["code"],
            diagnostic["message"],
            diagnostic["location"]["line"],
            diagnostic["location"]["column"],
        )
        for diagnostic in document["diagnostics"]
    ] == [("PIE-S2102", "Unknown field: lhs.id", line, column)]


def test_postgres_select_item_round_reads_a_let_scale(tmp_path):
    # Written directly as a select item, the scale is followed through its
    # `let` as in a single file and in `let rounded = round(money, scale)`.
    body = """table result:
    from rows
    let scale = 2
    select:
        id
        rounded = round(money, scale)
"""
    checked, outcome = emit(tmp_path, "postgres", body)
    assert checked.verified and outcome.status == "VERIFIED"
    assert json.loads(serialize_project_sql_emission(outcome))["sql"] == (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT '
        '"s0"."order.id" AS "c0", "s0"."flag value" AS "c1", '
        '"s0"."text `""é" AS "c2", "s0"."amount value" AS "c3", '
        '"s0"."ratio value" AS "c4", CAST(2 AS pg_catalog.int8) AS "c5" '
        'FROM "public"."phase66 source é" AS "s0") '
        'SELECT "t1"."c0" AS "id", '
        'round("t1"."c3", CAST("t1"."c5" AS pg_catalog.int4)) AS "rounded" '
        'FROM "p0" AS "t1"'
    )


def test_postgres_select_item_date_trunc_reads_a_let_unit(tmp_path):
    source = (
        temporal_probe.temporal_source("postgres").split("table result:", 1)[0]
        + """table result:
    from rows
    let unit = "month"
    select:
        month_stamp = date_trunc(unit, stamp)
"""
    )
    checked = temporal_probe.build_neutral(
        tmp_path / "project", {"main.pietto": source}
    )
    contract = json.loads(temporal_probe.temporal_input("postgres"))
    contract["environment"].append(
        {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"}
    )
    outcome = emit_project_sql(checked, json.dumps(contract).encode())
    assert outcome.status == "VERIFIED"
    assert json.loads(serialize_project_sql_emission(outcome))["sql"] == (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4") AS (SELECT '
        '"s0"."stamp" AS "c0", "s0"."optional_stamp" AS "c1", '
        '"s0"."identifier" AS "c2", "s0"."optional_identifier" AS "c3", '
        "CAST(E'\\155\\157\\156\\164\\150' AS pg_catalog.text) COLLATE \"C\" "
        'AS "c4" FROM "public"."rows" AS "s0") '
        'SELECT date_trunc("t1"."c4", "t1"."c0") AS "month_stamp" FROM "p0" AS "t1"'
    )
