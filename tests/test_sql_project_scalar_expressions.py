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
    let:
        lowered = lower(text)
        uppered = upper(text)
        trimmed = trim(text)
        sized = len(text)
        piece = substr(text, 1, 2)
        replaced = replace(text, text, text)
        contained = contains(text, text)
        prefixed = starts_with(text, text)
        suffixed = ends_with(text, text)
        selected = id in (id, id)
        text_membership = text in (text)
        decimal_membership = money in (money)
        float_membership = ratio in (ratio)
        empty_selected = flag in ()
        empty_excluded = flag not in ()
        unknown_excluded = flag not in (flag)
        fallback = coalesce(nullif(text, text), text)
        null_fallback = coalesce(null, text)
        null_checked = nullif(text, null)
        nullable_membership = id in (id, null)
        branch = text if flag else text
        negated = not flag
        widened = cast(id as Float)
        magnitude = abs(money)
        direction = sign(money)
        ranged = id between id and id
        matched = text like text
        unmatched = text not like text
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
        nullable_membership = id in (1, null)
"""


ALL_NULL_BODY = """table result:
    from rows
    select:
        unknown = coalesce(null, null)
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
    let:
        civil_date = date_of(stamp)
        nullable_date = date_of(optional_stamp)
        null_date = date_of(null)
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
def test_date_has_no_independent_selected_project_source(tmp_path, target):
    source = f"""shape Row:
    event_date: Date nullable
source rows: Row is {target}.table("opaque.result.fixture")
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

    assert outcome.status == "INPUT_REJECTED" and outcome.artifact is None


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
    let:
        coalesced = coalesce(text, "x")
        null_checked = nullif(text, "x")
        fallback = coalesce(nullif(trim(text), ""), text, "anonymous")
        null_fallback = coalesce(null, "x", text)
        branch = text if flag else "x"
        nested = "unknown" if flag else ("adult" if flag else "minor")
        text_member = text in ("x")
        bool_member = flag in (true)
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
    let:
        coalesced = coalesce(id, 1)
        null_checked = nullif(id, 1)
        branch = id if flag else 1
        bool_coalesced = coalesce(flag, true)
        bool_checked = nullif(flag, true)
        bool_branch = flag if flag else true
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
        listed = id in (1, null)
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


# A project that calls defs, and the same project with each call written out
# by hand: fixture, variant, defs, edits for the calls, edits written out.
DEF_PROJECTS = {
    "row_body": (
        "T_row_direct",
        "table_preserve",
        "def small(n: Int not null) -> Bool nullable: return n > 0 and n < 1000\n"
        "def both(a: Int not null, b: Int not null) -> Bool nullable: "
        "return small(a) and small(b)\n"
        "def label(t: Text not null, f: Bool nullable) -> Text not null: "
        'return "on" if f is null else lower(t)\n'
        "def next_of(n: Int not null) -> Int nullable: return n + 1\n",
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
                'positive = ("on" if flag is null else lower(text)) == '
                '("on" if flag is null else lower(text))',
            ),
        ],
    ),
    "parameter_named_like_a_function": (
        "T_row_direct",
        "table_preserve",
        "def f(upper: Text not null) -> Text not null: return upper(upper)\n",
        [
            ("doubled = bumped * 2", "doubled = bumped * 2\n        lower = text"),
            ("same_text = text == text", "same_text = f(lower) == text"),
        ],
        [
            ("doubled = bumped * 2", "doubled = bumped * 2\n        lower = text"),
            ("same_text = text == text", "same_text = (upper(lower)) == text"),
        ],
    ),
    "reordered_bound_literals": (
        "T_row_direct",
        "query_bind",
        "def btw(lo: Int not null, hi: Int not null, n: Int not null) -> "
        "Bool nullable: return n < hi and n > lo\n",
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
        "def bucket_of(k: Int nullable) -> Int not null: return 1 if k > 1 else 0\n",
        [("bucket = 1 if key > 1 else 0", "bucket = bucket_of(key)")],
        [("bucket = 1 if key > 1 else 0", "bucket = (1 if key > 1 else 0)")],
    ),
    "satisfying": (
        "Y_aggregate_satisfying",
        "retained",
        "def small(t: Int not null) -> Bool nullable: return t < 2\n",
        [("total < 2 and lo > 5", "small(total) and lo > 5")],
        [("total < 2 and lo > 5", "(total < 2) and lo > 5")],
    ),
    "qualify": (
        "A_window_qualify",
        "selected",
        "def top(n: Int not null) -> Bool nullable: return n <= 2\n",
        [("numbered <= 2", "top(numbered)")],
        [("numbered <= 2", "(numbered <= 2)")],
    ),
    "join_on": (
        "W_join_values",
        "left_marker",
        "def same(a: Int not null, b: Int not null) -> Bool nullable: return a == b\n",
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
