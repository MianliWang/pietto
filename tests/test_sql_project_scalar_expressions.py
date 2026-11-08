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
from pietto._project import project_sql_emission_windows as windowing
from pietto._project.project_sql_emission import (
    emit_project_sql,
    serialize_project_sql_emission,
)
from pietto._project.project_sql_emission_ast import RowValueColumn, SQLRowQuery
from pietto._project.project_sql_emission_verification import (
    verify_project_sql_emission,
)


TARGETS = ("postgres", "mysql")


def test_text_window_default_tokens_accept_only_ascii_octal_utf8() -> None:
    carrier = {
        "tag": "Text",
        "storage": {"kind": "pg_text"},
        "domain": {
            "kind": "text",
            "max_characters": 1,
            "encoding": "UTF8",
            "collation": "C",
            "padding": "NO PAD",
        },
    }
    valid = "E'\\351\\233\\252'"
    assert windowing.text_default_width(valid) == 1
    assert windowing._text_literal("a\x00b", "postgres") is None
    assert windowing._text_literal("\ud800", "postgres") is None
    assert all(
        windowing.text_default_width(token) is None
        and pure._window_value_representation("postgres", {}, carrier, token, {})
        is None
        for token in (
            "E'\\000'",
            "E'\\400'",
            "E'\\777'",
            "E'\\١٢٣'",
            "E'\\351\\233'",
            "'snow'",
        )
    )


def graft(value, **changes):
    result = copy(value)
    for name, changed in changes.items():
        object.__setattr__(result, name, changed)
    return result


def row_query(artifact):
    query = artifact.ast
    assert isinstance(query, SQLRowQuery)
    return query


def emit(tmp_path, target, body, policy="preserve_literals", *, imported=None):
    """Run one ordinary selected relation through the installed project path;
    ``imported`` moves the source beside it into module `a.pietto`."""
    item = probe.parameterized_fixture(
        target, body, policy, protocol=policy == "bind_safe_literals"
    )
    source: str | dict[str, str] = item["source"]
    if imported is not None:
        source = {
            "a.pietto": item["source"].removesuffix(body) + imported,
            "main.pietto": body,
        }
        contract = json.loads(item["contract"])
        contract["sources"][0]["selector"]["module"] = "a.pietto"
        item["contract"] = probe.encoded(contract).decode()
    return probe.build_case(tmp_path, source, item["contract"], policy)


def emit_temporal(directory, target, body):
    """One body over the published temporal source, with exact identifier case."""
    source = temporal_probe.temporal_source(target).split("table result:", 1)[0]
    checked = temporal_probe.build_neutral(directory, {"main.pietto": source + body})
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
    return emit_project_sql(checked, json.dumps(contract).encode())


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


S05_POSTGRES_BODY = """table result:
    from rows
    let plus_id = money + id
    let left_literal = 1 + money
    select:
        plus_id
        left_literal
"""


S05_SUM_BODY = """table result:
    from rows
    select:
        total = sum(money)
"""


def test_postgres_decimal_carriers_emit_exact_addition(tmp_path):
    checked, outcome = emit(tmp_path, "postgres", S05_POSTGRES_BODY)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    document = json.loads(serialize_project_sql_emission(outcome).decode())
    assert "pg_catalog.numeric(22, 2)" in document["sql"]
    assert "pg_catalog.numeric(10, 2)" in document["sql"]
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
    assert emit_compiled(loaded, ()).request.family == "postgres"


def test_postgres_decimal_sum_emits_checked_result_carrier(tmp_path):
    checked, outcome = emit(tmp_path, "postgres", S05_SUM_BODY)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    document = json.loads(serialize_project_sql_emission(outcome).decode())
    assert "CAST(SUM(" in document["sql"]
    assert "AS pg_catalog.numeric(28, 2))" in document["sql"]


def test_mysql_decimal_int_stays_refused(tmp_path):
    checked, outcome = emit(tmp_path, "mysql", S05_POSTGRES_BODY)
    assert checked.verified and outcome.status == "BLOCKED"


def test_mysql_decimal_sum_stays_refused(tmp_path):
    checked, outcome = emit(tmp_path, "mysql", S05_SUM_BODY)
    assert checked.verified and outcome.status == "BLOCKED"


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
    item = probe.parameterized_fixture(
        "postgres",
        """table result:
    from rows
    select:
        default = round(money)
        explicit_zero = round(money, 0)
        retained_scale = round(money, 30)
""",
        protocol=False,
    )
    contract = json.loads(item["contract"])
    representation = contract["sources"][0]["fields"][3]["representation"]
    representation["storage"].update(precision=65, scale=30)
    representation["domain"].update(precision=65, scale=30)

    _, outcome = probe.build_case(
        tmp_path,
        item["source"].replace("money: Decimal(9, 2)", "money: Decimal(65, 30)"),
        probe.encoded(contract).decode(),
        item["policy"],
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
    outcome = emit_temporal(
        tmp_path / "project",
        "postgres",
        """table result:
    from rows
    let unit = "month"
    let month_stamp = date_trunc(unit, stamp)
    select:
        month_stamp
""",
    )
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
    outcome = emit_temporal(
        tmp_path / "project",
        "postgres",
        """table result:
    from rows
    let day = date_of(stamp)
    select:
        date_year = date_trunc("year", day)
        date_month = date_trunc("month", day)
        date_day = date_trunc("day", day)
""",
    )
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
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
    )

    built = build_compiled(artifact)
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert template.artifact.rendered.sql == artifact.rendered.sql

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


DECIMAL_FLOAT_ARITHMETIC_BODY = """table result:
    from rows
    where ratio < 1.5 * 2.0
    select:
        doubled = money + money
        nothing = money - money
        constant = 1.5 + 2.25
"""


@pytest.mark.parametrize("target", TARGETS)
def test_decimal_and_float_arithmetic_pass_the_private_observation(tmp_path, target):
    """Only an Int result rests on the target's checked signed 64-bit
    operation: Decimal and Float literal arithmetic carry no such evidence, and
    the independent observation rebuilds that on both targets."""
    checked, outcome = emit(tmp_path, target, DECIMAL_FLOAT_ARITHMETIC_BODY)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
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
    assert [c["logical_type"]["name"] for c in document["columns"]] == [
        "Decimal",
        "Decimal",
        "Float",
    ]
    assert not any(
        "target_checked_signed64_narrowing" in r["evidence"]
        for r in document["requirements"]
    )


FLOAT_FIELD_ARITHMETIC_BODY = """query result:
    from rows
    where ratio * 2.0 > 1.0
    select:
        id
        doubled = ratio * 2.0
        summed = ratio + ratio
        negated = -ratio
        nested = ratio - ratio * ratio
        folded = 1.5 + 2.25
"""

FLOAT_REMAINDER_BODY = """query result:
    from rows
    select:
        id
        remainder = ratio % 0.1
"""

TEXT_WINDOW_DEFAULT_BODY = """query result:
    from rows
    select:
        id
        previous = lag(text, 1, "雪") window(order by id)
        following = lead(text, 1, "a'b") window(order by id)
"""


@pytest.mark.parametrize("target", TARGETS)
def test_postgres_text_window_defaults_are_escaped_and_widen_the_result(
    tmp_path, target
):
    """E7 opens only static Text literals beside Text lag/lead values."""
    checked, outcome = emit(tmp_path, target, TEXT_WINDOW_DEFAULT_BODY)
    assert checked.verified
    if target == "mysql":
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        assert [(blocker.code, blocker.detail) for blocker in outcome.blockers] == [
            ("PIE-B1003", "window_default_literal_kind_not_realized_yet"),
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    sql = artifact.rendered.sql.decode("utf-8")
    assert "E'\\351\\233\\252'" in sql
    assert "E'\\141\\047\\142'" in sql
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    defaults = [
        column["representation"]["domain"]["max_characters"]
        for column in document["columns"]
        if column["label"] in {"previous", "following"}
    ]
    assert len(defaults) == 2 and min(defaults) >= 3
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
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
    )

    built = build_compiled(artifact)
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert template.artifact.rendered.sql == artifact.rendered.sql


@pytest.mark.parametrize("target", TARGETS)
def test_postgres_float_remainder_uses_the_exact_binary64_lowering(tmp_path, target):
    """E5 admits same-type Float `%` only through the PostgreSQL exact path."""
    checked, outcome = emit(tmp_path, target, FLOAT_REMAINDER_BODY)
    assert checked.verified
    if target == "mysql":
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        assert [(blocker.code, blocker.detail) for blocker in outcome.blockers] == [
            ("PIE-B1003", "float_remainder_exact_binary64_not_realized")
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    sql = artifact.rendered.sql.decode("utf-8")
    assert 'WITH "__pietto_s04_operands" AS MATERIALIZED (SELECT ' in sql
    assert "pg_catalog.float8send" in sql
    assert "pg_catalog.mod" in sql
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
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
    )

    built = build_compiled(artifact)
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert template.artifact.rendered.sql == artifact.rendered.sql


@pytest.mark.parametrize("target", TARGETS)
def test_postgres_float_field_arithmetic_rests_on_the_checked_float8_operator(
    tmp_path, target
):
    """E4: PostgreSQL emits Float `+`, `-`, `*` over a field uncast, each with
    the R05 evidence that its checked float8 operator refuses a non-finite
    result (SQLSTATE 22003), and a sign, which never fails, without it; a
    literal fold stays statically checked. The observation, the independent
    public consumer and the compiled template agree. MySQL keeps it refused."""
    checked, outcome = emit(tmp_path, target, FLOAT_FIELD_ARITHMETIC_BODY)
    assert checked.verified
    if target == "mysql":
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        assert [(b.code, b.detail) for b in outcome.blockers] == [
            ("PIE-B1003", "float_literal_operands_required")
        ]
        return
    assert outcome.status == "VERIFIED", outcome.blockers
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    sql = document["sql"]
    ratio = '"t1"."c4"'
    for spelling in (
        f"({ratio} * CAST('2.0' AS pg_catalog.float8)) AS \"doubled\"",
        f'({ratio} + {ratio}) AS "summed"',
        f'(-{ratio}) AS "negated"',
        f'({ratio} - ({ratio} * {ratio})) AS "nested"',
        "(CAST('1.5' AS pg_catalog.float8) + CAST('2.25' AS pg_catalog.float8))",
    ):
        assert spelling in sql
    checked_token = {"overflow": "target_checked_binary64_overflow"}
    assert [
        r["evidence"] for r in document["requirements"] if r["kind"] == "arithmetic"
    ] == [
        [{"operator": "*"}, checked_token],
        [{"operator": "*"}, checked_token],
        [{"operator": "+"}, checked_token],
        [{"operator": "-"}],
        [{"operator": "-"}, checked_token],
        [{"operator": "*"}, checked_token],
        [{"operator": "+"}],
    ]
    assert all(
        c["representation"]["storage"] == {"kind": "pg_float8"}
        and c["representation"]["domain"]
        == {"kind": "finite_float", "format": "binary64"}
        for c in document["columns"][1:]
    )
    artifact = outcome.artifact
    assert artifact is not None
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
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_execution_template import (
        prepare_compiled_template,
    )

    built = build_compiled(artifact)
    template = prepare_compiled_template(
        load_compiled(
            built.payload,
            expected_pin=built.pin,
            accepted_producer=built.producer,
            accepted_compatibility=built.compatibility,
        )
    )
    assert template.artifact.rendered.sql == artifact.rendered.sql


@pytest.mark.parametrize("value", ("None - 2.5", "ratio * None", "-(None + ratio)"))
def test_postgres_float_arithmetic_keeps_typed_none_refused(tmp_path, value):
    """D-12: a Float with an always-null operand stays refused on PostgreSQL;
    E4 opens only finite Float carriers."""
    checked, outcome = emit(
        tmp_path,
        "postgres",
        f"query result:\n    from rows\n    select:\n        id\n        v = {value}\n",
    )
    assert outcome.status == "BLOCKED" and outcome.artifact is None


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


_NOW_SQL = "(statement_timestamp() AT TIME ZONE 'UTC')"


@pytest.mark.parametrize("target", TARGETS)
def test_now_is_one_utc_statement_snapshot_evaluated_at_execution(tmp_path, target):
    """Project PostgreSQL emits `now()` as the statement's UTC start, a
    never-None microsecond Timestamp, in SELECT items and WHERE; the compiled
    bundle and the live template keep the expression, never a value. A MySQL
    project refuses it until a run of the project's own SQL."""
    outcome = emit_temporal(
        tmp_path / target,
        target,
        """table result:
    from rows
    where stamp <= now()
    select:
        stamp
        seen = now()
        day = date_of(now())
""",
    )

    if target == "mysql":
        assert outcome.status == "BLOCKED" and outcome.artifact is None
        assert [
            (blocker["code"], blocker["subject"]["detail"])
            for blocker in probe.decode_public(serialize_project_sql_emission(outcome))[
                "blockers"
            ]
        ] == [("PIE-B1003", "scalar_call_signature_not_admitted")]
        return
    assert outcome.status == "VERIFIED" and outcome.artifact is not None
    artifact = outcome.artifact
    assert verify_project_sql_emission(artifact, artifact.request).verified
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    sql = artifact.rendered.sql.decode()
    assert sql.count(_NOW_SQL) == 3
    assert f'WHERE ("s0"."stamp" <= {_NOW_SQL})' in sql
    assert f'{_NOW_SQL} AS "seen", CAST({_NOW_SQL} AS date) AS "day"' in sql
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    columns = {column["label"]: column for column in document["columns"]}
    assert (columns["seen"]["logical_type"]["name"], columns["seen"]["nullable"]) == (
        "Timestamp",
        False,
    )

    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_execution_template import prepare_live_template

    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).request.family == "postgres"
    template = prepare_live_template(artifact)
    assert template.artifact.rendered.sql.decode() == sql
    assert template.slots == ()


@pytest.mark.parametrize("target", TARGETS)
def test_date_of_derives_the_date_result_carrier_and_civil_parts(tmp_path, target):
    outcome = emit_temporal(
        tmp_path / target,
        target,
        """table result:
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
""",
    )

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


FLOAT_ZERO_BODY = """table result:
    from rows
    let zero_member = ratio in (-0.0, 1.5)
    let zero_excluded = ratio not in (0.0)
    let inside = -0.0 <= ratio <= 1.5
    let unless_zero = nullif(ratio, 0.0)
    let unless_negative_zero = nullif(ratio, -0.0)
    select:
        zero_member
        zero_excluded
        inside
        unless_zero
        unless_negative_zero
"""


@pytest.mark.parametrize("target", TARGETS)
def test_float_zero_literals_keep_their_carriers_in_every_equality(tmp_path, target):
    """F2/F6: `in`, a chain and `nullif` compare by Float equality; each `-0.0`
    keeps its own typed carrier, so the target sees a real -0."""
    checked, outcome = emit(tmp_path, target, FLOAT_ZERO_BODY)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    sql = probe.decode_public(serialize_project_sql_emission(outcome))["sql"]
    zero, neg, one = (
        (
            "CAST('0.0' AS pg_catalog.float8)",
            "(-CAST('0.0' AS pg_catalog.float8))",
            "CAST('1.5' AS pg_catalog.float8)",
        )
        if target == "postgres"
        else (
            "CAST(0.0e0 AS DOUBLE)",
            "(-CAST(0.0e0 AS DOUBLE))",
            "CAST(1.5e0 AS DOUBLE)",
        )
    )
    for spelling in (
        f" IN ({neg}, {one}))",
        f" NOT IN ({zero}))",
        f" BETWEEN {neg} AND {one})",
        f", {zero}) AS ",
        f", {neg}) AS ",
    ):
        assert sql.count(spelling) == 1, (spelling, sql)
    assert sql.count("NULLIF(") == 2


@pytest.mark.parametrize("target", TARGETS)
def test_bound_float_zeros_differ_in_identity_not_in_value(tmp_path, target):
    """F6/F8: under bind-safe literals `-0.0` binds 0.0 under its own unary
    minus, so the target computes a real -0; `== 0.0` binds the same value
    without it. The SQL differs (bits witness); one Float equality (value)."""
    documents = {}
    for name, literal in (("negative", "-0.0"), ("positive", "0.0")):
        checked, outcome = emit(
            tmp_path / name,
            target,
            f"table result:\n    from rows\n    select:\n        z = ratio == {literal}\n",
            policy="bind_safe_literals",
        )
        assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
        documents[name] = probe.decode_public(serialize_project_sql_emission(outcome))
    negative, positive = documents["negative"], documents["positive"]
    assert [v["value"] for v in negative["fixed_values"]] == ["0x0.0p+0"]
    assert [v["value"] for v in positive["fixed_values"]] == ["0x0.0p+0"]
    anchor = (
        "CAST($1 AS pg_catalog.float8)" if target == "postgres" else "CAST(? AS DOUBLE)"
    )
    assert f"= (-{anchor}))" in negative["sql"]
    assert f"= {anchor})" in positive["sql"] and "(-CAST(" not in positive["sql"]


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


@pytest.mark.parametrize("mutation", ("operands", "callee", "rendered_sql"))
@pytest.mark.parametrize(
    ("target", "callee"),
    (("postgres", "lower"), ("mysql", "lower"), ("postgres", "concat")),
)
def test_q1_scalar_ast_and_bytes_tampering_are_rejected(
    tmp_path, target, mutation, callee
):
    body = Q1_BODY if callee == "lower" else POSTGRES_TEXT_GROWTH_BODY
    _, outcome = emit(tmp_path, target, body)
    artifact = outcome.artifact
    assert artifact is not None
    body_index, lower = next(
        (index, column)
        for index, body in enumerate(row_query(artifact).bodies)
        for column in body.columns
        if type(column) is RowValueColumn
        and type(column.value) is rows.SQLOperation
        and column.value.kind == "scalar_call"
        and column.value.original.callee_symbol.name == callee
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
        before, after = {
            ("lower", "postgres"): (b"lower(", b"upper("),
            ("lower", "mysql"): (b"LOWER(", b"UPPER("),
            ("concat", "postgres"): (b" || ", b", "),
        }[callee, target]
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
# PostgreSQL project SQL also joins Text; MySQL project SQL refuses `concat`
# (test_mysql_project_sql_refuses_concat).
POSTGRES_TEXT_GROWTH_BODY = """table result:
    from rows
    let joined = concat(text, "雪é", text)
    select:
        growing = replace(text, text, text)
        reverse_coalesced = coalesce("x", text)
        joined
        nulled = concat(text, None)
"""
# PostgreSQL concat() skips NULL; `||` is NULL when any argument is. The same
# bytes for both literal policies: a call argument stays a literal.
POSTGRES_TEXT_GROWTH_SQL = (
    'WITH "p0" ("c0", "c1", "c2", "c3", "c4", "c5") AS (SELECT '
    '"s0"."order.id" AS "c0", "s0"."flag value" AS "c1", '
    '"s0"."text `""é" AS "c2", "s0"."amount value" AS "c3", '
    '"s0"."ratio value" AS "c4", ("s0"."text `""é" || '
    "CAST(E'\\351\\233\\252\\303\\251' AS pg_catalog.text) COLLATE \"C\" || "
    '"s0"."text `""é") AS "c5" FROM "public"."phase66 source é" AS "s0") '
    'SELECT replace("t1"."c2", "t1"."c2", "t1"."c2") AS "growing", '
    'COALESCE(CAST(E\'\\170\' AS pg_catalog.text) COLLATE "C", "t1"."c2") '
    'AS "reverse_coalesced", "t1"."c5" AS "joined", ("t1"."c2" || NULL) '
    'AS "nulled" FROM "p0" AS "t1"'
)


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
    body = POSTGRES_TEXT_GROWTH_BODY if target == "postgres" else TEXT_GROWTH_BODY
    checked, outcome = emit(tmp_path, target, body, policy)
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified

    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds

    document = probe.decode_public(serialize_project_sql_emission(outcome))
    columns = {column["label"]: column for column in document["columns"]}
    widths = {"growing": 4096, "reverse_coalesced": 64}
    if target == "postgres":
        assert document["sql"] == POSTGRES_TEXT_GROWTH_SQL
        # A concat is as wide as all its arguments; a None adds nothing.
        widths.update(joined=130, nulled=64)
        assert [columns[label]["nullable"] for label in ("joined", "nulled")] == [
            False,
            True,
        ]
    for label, width in widths.items():
        representation = columns[label]["representation"]
        assert representation["domain"]["max_characters"] == width
        if target == "mysql":
            assert representation["storage"] == {"kind": "my_varchar", "length": width}

    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    from pietto._project.project_result_output import prepare_output

    replayed = emit_compiled(loaded, ())
    assert replayed.rendered.sql == artifact.rendered.sql
    assert [
        (column.label, column.realization.nullable, column.realization.domain)
        for column in prepare_output(replayed).columns
    ] == [
        (column.label, column.realization.nullable, column.realization.domain)
        for column in prepare_output(artifact).columns
    ]


def test_concat_of_only_none_stays_fail_closed(tmp_path):
    checked, outcome = emit(
        tmp_path,
        "postgres",
        "table result:\n    from rows\n    select:\n"
        "        unknown = concat(None, None)\n",
    )
    assert checked.verified
    assert outcome.status == "BLOCKED" and outcome.artifact is None
    assert [(blocker.code, blocker.detail) for blocker in outcome.blockers] == [
        ("PIE-B1003", "scalar_call_signature_not_admitted")
    ]


@pytest.mark.parametrize(
    ("body", "location"),
    (
        # At the first refused statement part: the let, before `nulled`.
        (POSTGRES_TEXT_GROWTH_BODY, (10, 5)),
        (
            'table result:\n    from rows\n    where concat(text, "-") == "x"\n'
            "    select:\n        id\n",
            (10, 5),
        ),
        # At the select item whose inlined def body calls it.
        (
            'def tag(x: Text) -> Text: return concat(x, "-")\n'
            "table result:\n    from rows\n    select:\n        tagged = tag(text)\n",
            (12, 9),
        ),
    ),
    ids=("let_and_select", "where", "def_body"),
)
def test_mysql_project_sql_refuses_concat(tmp_path, body, location):
    """MySQL types a CONCAT from its arguments' storage lengths and counts a
    literal's UTF-8 bytes, not from the declared widths, so MySQL project SQL
    refuses `concat`, as it refuses `round` and `date_trunc`; single-file
    MySQL SQL renders CONCAT."""
    checked, outcome = emit(tmp_path, "mysql", body)
    assert checked.verified
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
    ] == [("PIE-B1003", "scalar_call_signature_not_admitted", *location)]


LPAD_BODY = """table result:
    from rows
    select:
        padded = lpad(text, 5, "0")
        widened = lpad(text, 100, " ")
"""
ADD_MONTHS_BODY = """    from rows
    select:
        later = add_months(d, 1)
        moved = add_months(d2, id)
        stamped = add_months(date_of(ts), -1)
"""


def test_postgres_lpad_and_add_months_project_forms_are_verified(tmp_path):
    """`lpad` is as wide as its text or its width, as it never truncates;
    `add_months` keeps the Date carrier. Both pass the portable boundary."""
    checked, padded = emit(tmp_path / "pad", "postgres", LPAD_BODY)
    dated_checked, dated = probe.temporal_case(
        tmp_path / "date", "postgres", ADD_MONTHS_BODY
    )
    for plan, outcome in ((checked, padded), (dated_checked, dated)):
        assert plan.verified and outcome.status == "VERIFIED", outcome.blockers
        assert outcome.artifact is not None
        observed = portable.export_emission_observation(
            outcome.artifact, outcome.artifact.request
        )
        assert observed.canonical_bytes is not None
        assert (
            pure.parse_emission_observation(observed.canonical_bytes).status
            is pure.Status.OK
        )
    assert padded.artifact is not None and dated.artifact is not None
    sql = padded.artifact.rendered.sql.decode()
    assert sql.count("(CASE WHEN length(") == 2
    assert sql.count(" AS pg_catalog.int4), CAST(") == 2
    widths = [
        column.value.realization.domain["max_characters"]
        for body in row_query(padded.artifact).bodies
        for column in body.columns
        if type(column) is RowValueColumn
    ]
    assert widths == [64, 100]
    sql = dated.artifact.rendered.sql.decode()
    assert sql.count(" + make_interval(months => CAST(") == 3
    assert sql.count(" AS pg_catalog.int4))) AS date)") == 3


def test_postgres_lpad_refuses_a_width_outside_int4(tmp_path):
    checked, outcome = emit(
        tmp_path,
        "postgres",
        'table result:\n    from rows\n    select:\n        p = lpad(text, id, "0")\n',
    )
    assert checked.verified and outcome.status == "BLOCKED"
    assert [blocker.detail for blocker in outcome.blockers] == [
        "lpad_width_outside_physical_range"
    ]


def test_mysql_project_sql_refuses_lpad_and_add_months(tmp_path):
    """MySQL project SQL refuses both until the two-database differential
    admits them; single-file MySQL SQL renders LPAD and DATE_ADD."""
    checked, padded = emit(tmp_path / "pad", "mysql", LPAD_BODY)
    dated_checked, dated = probe.temporal_case(
        tmp_path / "date", "mysql", ADD_MONTHS_BODY
    )
    for plan, outcome, lines in (
        (checked, padded, (11, 12)),
        (dated_checked, dated, (12, 13, 14)),
    ):
        assert plan.verified
        assert public_blockers(outcome) == [
            ("PIE-B1003", "scalar_call_signature_not_admitted", line, 9)
            for line in lines
        ]


@pytest.mark.parametrize("target", TARGETS)
def test_concat_reads_an_imported_text_alias_field_as_text(tmp_path, target):
    item = probe.parameterized_fixture(
        target,
        'table result:\n    from rows\n    select:\n        joined = concat(text, "-")\n',
        protocol=False,
    )
    assert "    text: Text\n" in item["source"]
    _, outcome = probe.build_case(
        tmp_path,
        {
            "types.pietto": "type Label = Text\nexport type Label\n",
            "main.pietto": 'from "types.pietto" import type Label\n'
            + item["source"].replace("    text: Text\n", "    text: Label\n"),
        },
        item["contract"],
        item["policy"],
    )
    document = json.loads(serialize_project_sql_emission(outcome))
    if target == "mysql":
        assert document["status"] == "BLOCKED" and document["diagnostics"] == []
        assert [
            (
                b["code"],
                b["subject"]["detail"],
                b["location"]["path"],
                b["location"]["line"],
                b["location"]["column"],
            )
            for b in document["blockers"]
        ] == [("PIE-B1003", "scalar_call_signature_not_admitted", "main.pietto", 12, 9)]
        return
    assert document["status"] == "VERIFIED", document
    assert document["sql"] == (
        'SELECT ("s0"."text `""é" || CAST(E\'\\055\' AS pg_catalog.text) '
        'COLLATE "C") AS "joined" FROM "public"."phase66 source é" AS "s0"'
    )


SAME_VALUE_BODY = """table result:
    from rows
    where same_value(nullif(id, 0), id)
    select:
        id
        both_null = same_value(nullif(id, id), nullif(id, id))
        texts = same_value(text, nullif(text, "x"))
        amounts = same_value(money, money)
        typed = same_value(id + None, id)
        floats = same_value(ratio, 1.5)
"""
SAME_VALUE_SQL = {
    "postgres": (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4") AS (SELECT "s0"."order.id" AS "c0", '
        '"s0"."flag value" AS "c1", "s0"."text `""é" AS "c2", '
        '"s0"."amount value" AS "c3", "s0"."ratio value" AS "c4" '
        'FROM "public"."phase66 source é" AS "s0" '
        'WHERE (NULLIF("s0"."order.id", CAST(0 AS pg_catalog.int8)) '
        'IS NOT DISTINCT FROM "s0"."order.id")) '
        'SELECT "t1"."c0" AS "id", (NULLIF("t1"."c0", "t1"."c0") '
        'IS NOT DISTINCT FROM NULLIF("t1"."c0", "t1"."c0")) AS "both_null", '
        '("t1"."c2" IS NOT DISTINCT FROM NULLIF("t1"."c2", '
        'CAST(E\'\\170\' AS pg_catalog.text) COLLATE "C")) AS "texts", '
        '("t1"."c3" IS NOT DISTINCT FROM "t1"."c3") AS "amounts", '
        '(("t1"."c0" + CAST(NULL AS pg_catalog.int8)) IS NOT DISTINCT FROM "t1"."c0") '
        'AS "typed", ("t1"."c4" IS NOT DISTINCT FROM CAST(\'1.5\' AS pg_catalog.float8)) '
        'AS "floats" FROM "p0" AS "t1"'
    ),
    "mysql": (
        "WITH `p0` (`c0`, `c1`, `c2`, `c3`, `c4`) AS (SELECT `s0`.`order.id` AS `c0`, "
        '`s0`.`flag value` AS `c1`, `s0`.`text ``"é` AS `c2`, '
        "`s0`.`amount value` AS `c3`, `s0`.`ratio value` AS `c4` "
        "FROM `phase66`.`phase66 source é` AS `s0` "
        "WHERE (NULLIF(`s0`.`order.id`, CAST(0 AS SIGNED)) <=> `s0`.`order.id`)) "
        "SELECT `t1`.`c0` AS `id`, (NULLIF(`t1`.`c0`, `t1`.`c0`) "
        "<=> NULLIF(`t1`.`c0`, `t1`.`c0`)) AS `both_null`, "
        "(`t1`.`c2` <=> NULLIF(`t1`.`c2`, CAST(X'78' AS CHAR CHARACTER SET utf8mb4) "
        "COLLATE utf8mb4_0900_bin)) AS `texts`, "
        "(`t1`.`c3` <=> `t1`.`c3`) AS `amounts`, "
        "((`t1`.`c0` + CAST(NULL AS SIGNED)) <=> `t1`.`c0`) AS `typed`, "
        "(`t1`.`c4` <=> CAST(1.5e0 AS DOUBLE)) AS `floats` FROM `p0` AS `t1`"
    ),
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_same_value_is_a_null_safe_never_null_bool(tmp_path, target, policy):
    checked, outcome = emit(tmp_path, target, SAME_VALUE_BODY, policy)
    assert checked.verified and outcome.status == "VERIFIED"
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds

    document = probe.decode_public(serialize_project_sql_emission(outcome))
    columns = {column["label"]: column for column in document["columns"]}
    for label in ("both_null", "texts", "amounts", "typed", "floats"):
        assert columns[label]["logical_type"]["name"] == "Bool"
        assert columns[label]["nullable"] is False
    # Both policies keep these literals, so the SQL is the same.
    assert document["sql"] == SAME_VALUE_SQL[target]

    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, ()).request.family == target


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(
    "operands",
    (
        ("ratio", "ratio"),
        ("ratio", "1.5"),
        ("1.5", "ratio"),
        ("flag", "flag"),
        ("money", "id"),
    ),
)
def test_same_value_emission_admits_exactly_what_equality_admits(
    tmp_path, target, operands
):
    def blockers(name, value):
        _, outcome = emit(
            tmp_path / name,
            target,
            f"table result:\n    from rows\n    select:\n        value = {value}\n",
        )
        return outcome.status, [blocker.detail for blocker in outcome.blockers]

    left, right = operands
    same = blockers("call", f"same_value({left}, {right})")
    assert same == blockers("equality", f"{left} == {right}")
    # Float: PostgreSQL everywhere; MySQL only beside a row-free operand, as
    # its `==` (MySQL semijoin plans duplicated rows for row-row Float keys).
    if "ratio" in operands and (target == "postgres" or "1.5" in operands):
        assert same == ("VERIFIED", [])
    else:
        assert same[0] == "BLOCKED"


@pytest.mark.parametrize("target", TARGETS)
def test_same_value_is_not_yet_a_project_join_match_condition(tmp_path, target):
    # A JOIN `on` admits no built-in call yet; a joined SELECT does.
    item = probe.join_witness(
        target,
        "query result:\n    from lhs\n    let r = rhs\n"
        "    left join r on same_value(lhs.id, r.id)\n"
        "    select:\n        a = lhs.id\n",
    )
    _, outcome = probe.build_case(
        tmp_path, item["source"], item["contract"], item["policy"]
    )
    assert outcome.status == "BLOCKED"
    assert "match_condition_not_in_row_domain" in [
        blocker.detail for blocker in outcome.blockers
    ]


NAMED_T0 = "table t0:\n    from rows\n    select:\n        id\n        e = {value}\n"
GROUP_T0 = (
    "table result:\n    from t0\n    group by e\n"
    "    select:\n        e\n        n = count()\n"
)
GROUPED_OR_DISTINCT = {
    "group_key": "table result:\n    from rows\n"
    "    let k = {value}\n    group by k\n"
    "    select:\n        k\n        n = count()\n",
    "group_named": NAMED_T0 + GROUP_T0,
    "group_module": 'from "a.pietto" import table t0\n' + GROUP_T0,
    "distinct_column": "table result:\n    from rows\n"
    "    select distinct:\n        id\n        e = {value}\n",
    "distinct_let": "table result:\n    from rows\n    let k = {value}\n"
    "    select distinct:\n        id\n        e = k\n",
    "distinct_after_union": "table t0:\n    from rows\n    select:\n"
    "        e = {value}\n"
    "table t1:\n    from rows\n    select:\n        e = {value}\n"
    "query u:\n    union all t0, t1\n"
    "table result:\n    from u\n    select distinct:\n        e\n",
}


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("form", tuple(GROUPED_OR_DISTINCT))
def test_project_same_value_groups_and_deduplicates_as_equality_does(
    tmp_path, target, form
):
    # A computed Bool GROUP BY key or DISTINCT column, `==` as well, arrives on
    # MySQL as a 4-byte INT (LONG) that the reader accepts (DB campaign 6).
    def document_of(name, value):
        checked, outcome = emit(
            tmp_path / name,
            target,
            GROUPED_OR_DISTINCT[form].format(value=value),
            imported=NAMED_T0.format(value=value) + "export table t0\n"
            if form == "group_module"
            else None,
        )
        assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
        data = serialize_project_sql_emission(outcome)
        # The independent decoder expects nullable true for this `==` union
        # column, which the document publishes as "unknown"; that predates
        # `same_value`.
        if (form, name) == ("distinct_after_union", "equal"):
            return json.loads(data)
        return probe.decode_public(data)

    same = document_of("same", "same_value(nullif(id, 0), id)")
    equal = document_of("equal", "nullif(id, 0) == id")
    assert " = " in equal["sql"]
    assert same["sql"] == equal["sql"].replace(
        " = ", " <=> " if target == "mysql" else " IS NOT DISTINCT FROM "
    )
    storage = [c["representation"]["storage"] for c in same["columns"]]
    assert storage == [c["representation"]["storage"] for c in equal["columns"]]
    assert {"kind": "my_signed_bool" if target == "mysql" else "pg_bool"} in storage


def public_blockers(outcome):
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    return [
        (
            item["code"],
            item["subject"]["detail"],
            item["location"]["line"],
            item["location"]["column"],
        )
        for item in document["blockers"]
    ]


ABS_DEFS = (
    "def fa(x: Float | None) -> Float | None: return abs(x)\n"
    "def fi(x: Int | None) -> Int | None: return abs(x)\n"
)
RESULT = "table result:\n    from rows\n"
SELECT_O = RESULT + "    select:\n        id\n        o = {}\n"
T0 = "table t0:\n    from rows\n    select:\n        id\n        x = abs(None)\n"
FROM_T0 = T0 + "table result:\n    from t0\n"
POLICIES = ("preserve_literals", "bind_safe_literals")


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize(
    "body,line",
    (
        (SELECT_O.format("abs(None)"), 14),
        (SELECT_O.format("fa(None)"), 14),
        (SELECT_O.format("fi(None)"), 14),
        (SELECT_O.format("abs(abs(None))"), 14),
        (SELECT_O.format("abs(None)") + "    order by id\n", 14),
        (SELECT_O.format("abs(None)") + "    limit 3\n", 14),
        (RESULT + "    let x = abs(None)\n    select:\n        id\n        x\n", 15),
        (RESULT + "    let y = fa(None)\n    select:\n        id\n        o = y\n", 15),
        (FROM_T0 + "    select:\n        id\n        x\n", 19),
        (
            FROM_T0
            + "    select:\n        id\n        o = lag(x) window(order by id)\n",
            19,
        ),
        (
            FROM_T0
            + "    select:\n        id\n        o = first_value(x) window(order by id)\n",
            19,
        ),
    ),
)
def test_a_typed_null_decimal_output_refuses_instead_of_crashing(
    tmp_path, target, policy, body, line
):
    # Each visible output needs a Decimal precision that the typed NULL lacks;
    # every form here raised KeyError in 0.1.7.
    checked, outcome = emit(tmp_path, target, ABS_DEFS + body, policy)
    assert checked.verified and outcome.status == "BLOCKED"
    assert public_blockers(outcome) == [
        ("PIE-B1003", "scalar_call_signature_not_admitted", line, 9)
    ]


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize("policy", POLICIES)
@pytest.mark.parametrize(
    "body",
    (
        SELECT_O.format("abs(None) is None"),
        SELECT_O.format("abs(None) is not None"),
        SELECT_O.format("fa(None) is None"),
        SELECT_O.format("fi(None) is None"),
        SELECT_O.format("coalesce(abs(None), money)"),
        SELECT_O.format("coalesce(abs(None), abs(money))"),
        SELECT_O.format("sign(abs(None))"),
        SELECT_O.format("abs(None) if flag else money"),
        SELECT_O.format("abs(None) is None") + "    order by id\n",
        RESULT + "    where abs(None) is None\n    select:\n        id\n",
        RESULT
        + "    let x = abs(None)\n    where x is None\n    select:\n        id\n",
        RESULT
        + "    let x = abs(None)\n    select:\n        id\n        o = x is None\n",
        RESULT + "    let y = fa(None)\n    where y is None\n    select:\n        id\n",
        FROM_T0 + "    where x is None\n    select:\n        id\n",
    ),
)
def test_readers_of_a_typed_null_decimal_abs_stay_verified(
    tmp_path, target, policy, body
):
    # Each form is VERIFIED in 0.1.7 too.
    checked, outcome = emit(tmp_path, target, ABS_DEFS + body, policy)
    assert checked.verified and outcome.status == "VERIFIED"


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
    outcome = emit_temporal(
        tmp_path / "project",
        "postgres",
        """table result:
    from rows
    let unit = "month"
    select:
        month_stamp = date_trunc(unit, stamp)
""",
    )
    assert outcome.status == "VERIFIED"
    assert json.loads(serialize_project_sql_emission(outcome))["sql"] == (
        'WITH "p0" ("c0", "c1", "c2", "c3", "c4") AS (SELECT '
        '"s0"."stamp" AS "c0", "s0"."optional_stamp" AS "c1", '
        '"s0"."identifier" AS "c2", "s0"."optional_identifier" AS "c3", '
        "CAST(E'\\155\\157\\156\\164\\150' AS pg_catalog.text) COLLATE \"C\" "
        'AS "c4" FROM "public"."rows" AS "s0") '
        'SELECT date_trunc("t1"."c4", "t1"."c0") AS "month_stamp" FROM "p0" AS "t1"'
    )


@pytest.mark.parametrize(
    "expression,precision",
    [
        ("money * id", 28),
        ("id * money", 28),
        ("money * 2", 28),
        ("-money", 9),
        ("+money", 9),
        ("-(money * id)", 28),
    ],
)
def test_decimal_multiply_and_sign_close_project_readers(
    tmp_path, expression, precision
):
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    body = f"table result:\n    from rows\n    select:\n        result = {expression}\n"
    checked, outcome = emit(tmp_path, "postgres", body)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    storage = document["columns"][0]["representation"]["storage"]
    assert storage == {"kind": "pg_numeric", "precision": precision, "scale": 2}
    observation = portable.export_emission_observation(
        outcome.artifact, outcome.artifact.request
    )
    assert observation.status is portable.ObservationStatus.OK
    assert observation.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observation.canonical_bytes).status
        is pure.Status.OK
    )
    built = build_compiled(outcome.artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(loaded, ())
    assert replay.rendered.sql == outcome.artifact.rendered.sql


@pytest.mark.parametrize("expression", ["money * id", "id * money", "-money", "+money"])
def test_mysql_project_decimal_multiply_and_sign_remain_refused(tmp_path, expression):
    body = f"table result:\n    from rows\n    select:\n        result = {expression}\n"
    checked, outcome = emit(tmp_path, "mysql", body)
    assert checked.verified and outcome.status == "BLOCKED"


@pytest.mark.parametrize("target", TARGETS)
def test_different_scale_decimal_product_preserves_native_sql(tmp_path, target):
    item = probe.parameterized_fixture(
        target,
        "table result:\n    from rows\n    select:\n        product = money * ratio\n",
    )
    source = item["source"].replace("ratio: Float", "ratio: Decimal(8, 3)")
    contract = json.loads(item["contract"])
    representation = contract["sources"][0]["fields"][4]["representation"]
    representation["storage"] = {
        "kind": "pg_numeric" if target == "postgres" else "my_decimal",
        "precision": 8,
        "scale": 3,
    }
    representation["domain"] = {"kind": "decimal", "precision": 8, "scale": 3}
    _, outcome = probe.build_case(
        tmp_path, source, probe.encoded(contract).decode(), "preserve_literals"
    )
    assert outcome.status == "VERIFIED", outcome.blockers
    assert outcome.artifact is not None
    sql = outcome.artifact.rendered.sql
    assert b"CAST(" not in sql
    assert b" * " in sql
    probe.decode_public(serialize_project_sql_emission(outcome))


def emit_aggregate_composition(
    tmp_path, body, *, target="postgres", policy="preserve_literals"
):
    item = probe.aggregate_fixture(target, "X_aggregate_global", "bag")
    source = item["source"].split("query result:", 1)[0] + body
    contract = json.loads(item["contract"])
    contract["environment"].append(
        {
            "key": "parameter_protocol",
            "scope": "statement",
            "value": "postgres_extended" if target == "postgres" else "mysql_prepared",
        }
    )
    return probe.build_case(tmp_path, source, probe.encoded(contract), policy)


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize(
    "grouped,expression,leaf_functions",
    [
        (False, "coalesce(sum(value), 0)", ("sum",)),
        (False, "sum(value) + sum(value)", ("sum", "sum")),
        (False, "sum(value) * 100 / count()", ("sum", "count")),
        (False, "abs(min(value))", ("min",)),
        (False, "abs(avg(value))", ("avg",)),
        pytest.param(False, "avg(value) / 2.0", ("avg",), id="float_division"),
        pytest.param(
            False, "sum(value) % count()", ("sum", "count"), id="int_remainder"
        ),
        (False, "abs(max(amount))", ("max",)),
        (False, "coalesce(min(amount), max(amount))", ("min", "max")),
        (True, "coalesce(sum(value), 0) + coalesce(key, 0)", ("sum",)),
        (True, "coalesce(key, 0) + 1", ()),
        pytest.param(True, "1 + 2", (), id="grouped_constant"),
    ],
)
def test_aggregate_composition_preserves_leaf_ports_and_closes_readers(
    tmp_path, policy, grouped, expression, leaf_functions
):
    from pietto._project import project_sql_emission_aggregation as grouping
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    body = "query result:\n    from agg\n"
    if grouped:
        body += "    group by:\n        key\n"
    body += f"    select:\n        result = {expression}\n        direct = count()\n"
    checked, outcome = emit_aggregate_composition(tmp_path, body, policy=policy)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    assert verify_project_sql_emission(artifact, artifact.request).verified
    aggregate_columns = [
        column
        for stage in row_query(artifact).bodies
        for column in stage.columns
        if type(column) is grouping.AggregateValueColumn
    ]
    assert tuple(column.function for column in aggregate_columns) == (
        *leaf_functions,
        "count",
    )
    assert len(
        {id(column.aggregate.source.call) for column in aggregate_columns}
    ) == len(aggregate_columns)
    for column in aggregate_columns:
        if column.function == "sum":
            assert column.column.realization.nullable is True
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    if expression == "coalesce(sum(value), 0)":
        assert document["columns"][0]["nullable"] is False
    observation = portable.export_emission_observation(artifact, artifact.request)
    assert observation.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observation.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observation.canonical_bytes, artifact, artifact.request
    ).corresponds
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(
        loaded, tuple(value.value for value in artifact.fixed_values)
    )
    assert replay.rendered.sql == artifact.rendered.sql
    from pietto._project.project_result_output import prepare_output

    assert [
        (c.label, c.realization.nullable) for c in prepare_output(replay).columns
    ] == [(c.label, c.realization.nullable) for c in prepare_output(artifact).columns]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_mysql_aggregate_composition_refuses_every_outer_expression(tmp_path, policy):
    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result:\n    from agg\n    select:\n"
        "        first = coalesce(sum(value), 0)\n"
        "        second = abs(min(value))\n"
        "        direct = count()\n",
        target="mysql",
        policy=policy,
    )
    assert checked.verified and outcome.status == "BLOCKED"
    assert [(blocker.code, blocker.detail) for blocker in outcome.blockers] == [
        ("PIE-B1003", "aggregate_composition_not_admitted_on_target"),
        ("PIE-B1003", "aggregate_composition_not_admitted_on_target"),
    ]
    assert outcome.artifact is None


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_aggregate_composition_keeps_legal_repeated_where_parameters(tmp_path, policy):
    from decimal import Decimal
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result(floor: Decimal(9, 2)):\n    from agg\n"
        "    where amount >= floor or amount <= floor\n"
        "    select:\n        result = coalesce(min(amount), max(amount))\n",
        policy=policy,
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [
        (u["owner"]["parameter"], u["server_index"], u["physical_type"])
        for u in document["parameter_uses"]
    ] == [(0, 1, "pg_numeric")] * 2
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.status is portable.ObservationStatus.OUTSIDE_SCHEMA
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(loaded, (), (Decimal("1.25"),))
    assert replay.rendered.sql == artifact.rendered.sql
    assert len(replay.parameter_uses) == 2
    with pytest.raises(CompiledError, match="COMPILED_BINDING_PARAMETERS"):
        emit_compiled(loaded, (), (Decimal("1.234"),))

    from pietto._project.project_compiled_schema import FIELDS, Record
    from pietto._project.project_compiled_verification import verify_description

    records = built.root.records
    projection = next(
        record
        for record in records.values()
        if record.address.kind == "row" and record.get("stage") == "projection"
    )
    operation = records[projection.get("values")[0]]
    parameter = next(address for address in records if address.kind == "parameter_read")
    values = list(operation.values)
    values[FIELDS["operation"].index("operands")] = (
        operation.get("operands")[0],
        parameter,
    )
    forged = Record(operation.address, tuple(values))
    description = replace(
        built.root.description,
        members=tuple(
            (
                name,
                tuple(
                    forged if record.address == forged.address else record
                    for record in members
                ),
            )
            for name, members in built.root.description.members
        ),
    )
    with pytest.raises(CompiledError, match="^COMPILED_AGGREGATE_PARAMETER_POSITION$"):
        verify_description(description)


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("ordering", ("total", "total desc"))
def test_aggregate_composition_having_alias_and_order_close_readers(
    tmp_path, policy, ordering
):
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled
    from pietto._project.project_result_output import prepare_output

    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result:\n    from agg\n    where rid > 0\n"
        "    group by key\n    select:\n"
        "        total = coalesce(sum(value), 0)\n        raw = sum(value)\n"
        "    having total > 0 and total < 10\n"
        f"    order by {ordering}\n",
        policy=policy,
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert [column["nullable"] for column in document["columns"]] == [False, True]
    from pietto._project.project_sql_plan import ProjectSQLPlan

    assert isinstance(checked.plan, ProjectSQLPlan)
    assert len(checked.plan.aggregates) == 2
    assert verify_project_sql_emission(artifact, artifact.request).verified
    observation = portable.export_emission_observation(artifact, artifact.request)
    assert observation.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observation.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observation.canonical_bytes, artifact, artifact.request
    ).corresponds
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    replay = emit_compiled(
        loaded, tuple(value.value for value in artifact.fixed_values)
    )
    assert replay.rendered.sql == artifact.rendered.sql
    assert [
        column.realization.nullable for column in prepare_output(replay).columns
    ] == [False, True]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize("grouped", (False, True))
def test_aggregate_composition_join_keeps_each_leaf_and_original_input_port(
    tmp_path, policy, grouped
):
    from pietto._project import project_sql_emission_aggregation as grouping
    from pietto._project.project_sql_plan_aggregation import aggregate_call
    from pietto._project.project_sql_emission_ast import SQLJoinQuery
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    body = (
        "query result:\n    from agg\n    let rhs = agg\n"
        "    inner join rhs on agg.rid == rhs.rid\n"
        + ("    group by agg.key\n" if grouped else "")
        + "    select:\n"
        + ("        bucket = coalesce(agg.key, 0)\n" if grouped else "")
        + "        total = coalesce(sum(rhs.value), 0) + coalesce(sum(rhs.value), 0)\n"
        "        raw = sum(agg.value)\n        n = count()\n"
        + (
            "    having total > 0 and total < 100\n    order by total\n"
            if grouped
            else ""
        )
    )
    checked, outcome = emit_aggregate_composition(tmp_path, body, policy=policy)
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None and isinstance(artifact.ast, SQLJoinQuery)
    values = [
        column
        for stage in artifact.ast.bodies
        for column in stage.columns
        if type(column) is grouping.AggregateValueColumn
    ]
    assert tuple(column.function for column in values) == ("sum", "sum", "sum", "count")
    assert len({id(aggregate_call(column.aggregate.source)) for column in values}) == 4
    assert values[0].argument.port is values[1].argument.port
    assert values[0].argument.port is not values[2].argument.port
    assert all(column.column.realization.nullable is True for column in values[:3])
    probe.decode_public(serialize_project_sql_emission(outcome))
    assert verify_project_sql_emission(artifact, artifact.request).verified
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert (
        emit_compiled(
            loaded, tuple(value.value for value in artifact.fixed_values)
        ).rendered.sql
        == artifact.rendered.sql
    )


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
@pytest.mark.parametrize(
    "expression,precision",
    (
        ("min(amount) + 1", 10),
        ("max(amount) - 1", 10),
        ("sum(amount) + 1", 29),
        ("min(amount) * 2", 28),
        ("sum(amount) * 2", 47),
        ("abs(sum(amount)) + 1", 29),
        ("-sum(amount)", 28),
        ("abs(sum(amount))", 28),
    ),
)
def test_decimal_aggregate_result_carriers_close_readers(
    tmp_path, policy, expression, precision
):
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    checked, outcome = emit_aggregate_composition(
        tmp_path,
        f"query result:\n    from agg\n    select:\n        result = {expression}\n",
        policy=policy,
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    document = probe.decode_public(serialize_project_sql_emission(outcome))
    assert document["columns"][0]["representation"]["storage"] == {
        "kind": "pg_numeric",
        "precision": precision,
        "scale": 2,
    }
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    assert portable.verify_emission_observation(
        observed.canonical_bytes, artifact, artifact.request
    ).corresponds
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert (
        emit_compiled(
            loaded, tuple(value.value for value in artifact.fixed_values)
        ).rendered.sql
        == artifact.rendered.sql
    )


@pytest.mark.parametrize(
    "precision,expression,detail",
    (
        (46, "sum(amount) + 1", "decimal_result_outside_physical_range"),
        (65, "min(amount) + 1", "decimal_result_outside_physical_range"),
        (47, "min(amount) * 2", "decimal_result_outside_physical_range"),
        (9, "abs(avg(amount))", "decimal_aggregate_range_proof_missing"),
        (9, "min(amount) / 2", None),
    ),
)
def test_decimal_aggregate_result_keeps_precision_cap_and_refusals(
    tmp_path, precision, expression, detail
):
    item = probe.aggregate_fixture("postgres", "X_aggregate_global", "bag")
    source = (
        item["source"]
        .split("query result:", 1)[0]
        .replace("amount: Decimal(9, 2)", f"amount: Decimal({precision}, 2)")
    )
    source += (
        f"query result:\n    from agg\n    select:\n        result = {expression}\n"
    )
    contract = json.loads(item["contract"])
    representation = contract["sources"][0]["fields"][4]["representation"]
    representation["storage"]["precision"] = precision
    representation["domain"]["precision"] = precision
    checked, outcome = probe.build_case(tmp_path, source, probe.encoded(contract))
    assert outcome.status == "BLOCKED"
    if detail is None:
        assert not checked.verified
        assert [
            d["code"]
            for d in json.loads(serialize_project_sql_emission(outcome))["diagnostics"]
        ] == ["PIE-S2333"]
    else:
        assert checked.verified
        assert [blocker.detail for blocker in outcome.blockers] == [detail]


@pytest.mark.parametrize("policy", ("preserve_literals", "bind_safe_literals"))
def test_composition_having_keeps_one_authored_literal_value(tmp_path, policy):
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_compiled_loading import load_compiled
    from pietto._project.project_compiled_lowering import emit_compiled

    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result:\n    from agg\n    where rid > 0\n    group by key\n"
        "    select:\n        total = sum(value) + 1\n        extra = 1\n"
        "    having total > 0 and total < 100\n    order by total\n",
        policy=policy,
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    artifact = outcome.artifact
    assert artifact is not None
    probe.decode_public(serialize_project_sql_emission(outcome))
    defaults = tuple(value.value for value in artifact.fixed_values)
    assert defaults == ((0, 1) if policy == "bind_safe_literals" else ())
    if policy == "bind_safe_literals":
        from pietto._project.project_sql_emission_verification import (
            _active_specialized_literal,
        )

        plan = artifact.request.plan
        shared = next(
            site.position.literal
            for site in plan.literal_sites
            if site.position.role.value == "select"
            and site.position.literal.value == 1
            and site.reason is not None
            and site.reason.value == "specialized_or_structural_context"
        )
        assert _active_specialized_literal(plan, artifact.request.layout, shared)
        inactive = graft(
            plan,
            filters=tuple(
                item for item in plan.filters if item.site.role.value != "satisfying"
            ),
        )
        assert inactive.literal_sites is plan.literal_sites
        assert not _active_specialized_literal(
            inactive, artifact.request.layout, shared
        )
    observed = portable.export_emission_observation(artifact, artifact.request)
    assert observed.canonical_bytes is not None
    assert (
        pure.parse_emission_observation(observed.canonical_bytes).status
        is pure.Status.OK
    )
    built = build_compiled(artifact)
    loaded = load_compiled(
        built.payload,
        expected_pin=built.pin,
        accepted_producer=built.producer,
        accepted_compatibility=built.compatibility,
    )
    assert emit_compiled(loaded, defaults).rendered.sql == artifact.rendered.sql
    if defaults:
        rebound = emit_compiled(loaded, (0, 7))
        assert rebound.rendered.sql == artifact.rendered.sql
        assert tuple(value.value for value in rebound.fixed_values) == (0, 7)


def test_repeated_bound_leaf_keeps_native_occurrence_identity(tmp_path):
    from pietto._project import project_sql_plan_expressions as scalar
    from pietto._project.project_sql_plan import ProjectSQLPlan

    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result:\n    from agg\n    select:\n        result = count() + 1\n",
        policy="bind_safe_literals",
    )
    assert checked.verified and outcome.status == "VERIFIED"
    assert isinstance(checked.plan, ProjectSQLPlan)
    plan = checked.plan
    leaf = next(
        value
        for value in plan.expressions
        if type(value) is scalar.ProjectSQLBoundLiteral
    )
    chains = rows._constant_chains((leaf, leaf), plan)
    assert [position for position, _, _ in chains] == [0, 1]
    allocated = parameters.allocate_uses(
        "postgres", tuple((item, "pg_int8") for _, _, item in chains), 100
    )
    uses = parameters.occurrence_uses(allocated)
    values = tuple(
        parameters.build_value(plan, chain, "postgres", uses) for _, chain, _ in chains
    )
    observed = []
    for value in values:
        leaf_value = parameters.value_nodes(value)[-1]
        assert isinstance(leaf_value, parameters.SQLParameter)
        observed.append(leaf_value.use)
    assert [use.ordinal for use in observed] == [0, 1]
    assert observed[0] is allocated[0] and observed[1] is allocated[1]
    assert observed[0] is not observed[1]
    assert [use.server_index for use in observed] == [1, 1]


def test_having_round_alias_retains_each_expansion_root(tmp_path):
    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result:\n    from agg\n    group by key\n    select:\n"
        "        mean = round(avg(value))\n"
        "    having mean > 0.0 and mean < 100.0\n    order by mean\n",
    )
    assert checked.verified and outcome.status == "VERIFIED", outcome.blockers
    probe.decode_public(serialize_project_sql_emission(outcome))


@pytest.mark.parametrize("mutation", ("missing", "lost_alias", "foreign_clause"))
def test_public_having_bridge_rejects_lost_or_foreign_alias_source(tmp_path, mutation):
    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result:\n    from agg\n    group by key\n    select:\n"
        "        total = coalesce(sum(value), 0)\n"
        "    having total > 0 and total < 100\n    order by total\n",
    )
    assert checked.verified and outcome.status == "VERIFIED"
    raw = serialize_project_sql_emission(outcome)
    probe.decode_public(raw)
    document = json.loads(raw)
    subject = next(
        item["subject"]
        for item in document["ranges"]
        if item["subject"]["kind"] == "expression"
        and any(
            sum(
                source["kind"] == "normalized_expression"
                for source in origin["sources"]
            )
            == 2
            for origin in item["origins"]
        )
    )
    for item in document["ranges"]:
        if item["subject"] != subject:
            continue
        for origin in item["origins"]:
            sources = origin["sources"]
            aliases = [
                source
                for source in sources
                if source["kind"] == "normalized_expression"
            ]
            if mutation == "missing":
                origin["sources"] = [
                    source
                    for source in sources
                    if source["kind"] != "normalized_expression"
                ]
            elif mutation == "lost_alias":
                origin["sources"] = [
                    source for source in sources if source is not aliases[-1]
                ]
            else:
                cause = next(
                    source for source in sources if source["kind"] == "authored_cause"
                )
                for source in aliases:
                    source["location"] = dict(cause["location"])
    with pytest.raises(ValueError):
        probe.decode_public(json.dumps(document).encode())


@pytest.mark.parametrize(
    "mutation", ("duplicate_first", "reverse_order", "literal_spans")
)
def test_public_having_bridge_pairs_actual_parent_operands(tmp_path, mutation):
    checked, outcome = emit_aggregate_composition(
        tmp_path,
        "query result:\n    from agg\n    group by key\n    select:\n"
        "        total = coalesce(sum(value), 0)\n"
        "    having total > 0 and total < 100\n    order by total\n",
    )
    assert checked.verified and outcome.status == "VERIFIED"
    raw = serialize_project_sql_emission(outcome)
    probe.decode_public(raw)
    document = json.loads(raw)
    clause = next(
        source["location"]
        for item in document["ranges"]
        if item["role"] == "satisfying"
        for origin in item["origins"]
        for source in origin["sources"]
        if source["kind"] == "authored_cause"
    )
    literals = []
    for item in document["ranges"]:
        if item["kind"] != "literal":
            continue
        for origin in item["origins"]:
            for source in origin["sources"]:
                location = source["location"]
                if (
                    source["kind"] == "authored_cause"
                    and location["line"] == clause["line"]
                    and location not in literals
                ):
                    literals.append(location)
    assert len(literals) == 2
    changed = 0
    for item in document["ranges"]:
        for origin in item["origins"]:
            aliases = [
                source
                for source in origin["sources"]
                if source["kind"] == "normalized_expression"
            ]
            if not aliases:
                continue
            assert len(aliases) == 2
            changed += 1
            if mutation == "duplicate_first":
                aliases[1]["location"] = dict(aliases[0]["location"])
            elif mutation == "reverse_order":
                aliases[0]["location"], aliases[1]["location"] = (
                    aliases[1]["location"],
                    aliases[0]["location"],
                )
            else:
                for alias, location in zip(aliases, literals, strict=True):
                    alias["location"] = dict(location)
    assert changed > 0
    with pytest.raises(ValueError):
        probe.decode_public(json.dumps(document).encode())
