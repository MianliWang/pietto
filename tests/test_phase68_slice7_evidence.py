"""Synthetic data-only corruption tests; none are claimed as native evidence."""

from copy import deepcopy
import json

import pytest

from _pietto_phase68_slice7_cases import manifest, case_preparation
from _pietto_phase68_slice7_probe import native_record, encoded
from _pietto_phase68_slice7_check import check_attempt
from pietto._project.project_guard_program import prepare_program, statement_for
from pietto._project.project_guard_rendering import render_guard


def synthetic(tmp_path, *, violated=False):
    case = next(
        c
        for c in manifest()
        if c["name"] == ("bag_two_equal_null" if violated else "bag_one")
    )
    program = prepare_program(case_preparation(tmp_path, "postgres", case))
    native = render_guard(statement_for(program, "combined"))
    columns = [
        program.prefix + "channel",
        program.prefix + "g0",
        "left_id",
        "right_key",
    ]
    wire = ((0, 1 if violated else 0, None, None),) + (
        () if violated else ((1, 0, 1, None), (1, 0, 1, None))
    )
    record = dict(
        synthetic=True,
        case=case["name"],
        route="postgres_rows",
        session=123,
        role="synthetic-observer",
        environment=[
            program.preparation.artifact.request.release,
            "repeatable read",
            True,
            "UTF8",
        ],
        rows=encoded(case["rows"]),
        guard_states=list(case["states"]),
        guard_native=native_record(native),
        cursors=[dict(ordinal=0, session=123, statements=[0], closed=True)],
        statements=[
            dict(
                ordinal=0,
                cursor=0,
                sql=native.sql.decode(),
                arguments=encoded((native.arguments,))[0],
                closed=True,
                execute_returned=True,
                native_status=2,
                native_rows=len(wire),
                metadata=[[name, 20, None, None, None, None, None] for name in columns],
                fetches=[dict(method="fetchall", rows=encoded(wire), normal=True)],
            )
        ],
        control_joined=True,
        session_gone=True,
        outcome=dict(
            cleanup="CLOSED",
            cleanup_failures=[],
            transaction="ROLLBACK_ACK" if violated else "COMMIT_ACK",
            source="FAILED" if violated else "EOF",
        ),
    )
    if violated:
        record["failure"] = dict(category="SINGLE_MATCH_VIOLATED")
    return json.loads(json.dumps(record)), case, program


@pytest.mark.parametrize("violated", (False, True))
def test_data_only_success_and_violation_are_distinct(tmp_path, violated):
    record, case, program = synthetic(tmp_path, violated=violated)
    check_attempt(record, case, program)


@pytest.mark.parametrize(
    "damage",
    (
        "sql",
        "control_owner",
        "arguments",
        "missing_statement",
        "missing_cursor",
        "open_cursor",
        "session",
        "terminal",
        "public_value",
        "metadata",
        "receipt",
        "empty_success",
    ),
)
def test_complete_synthetic_record_damage_is_rejected(tmp_path, damage):
    record, case, program = synthetic(tmp_path)
    broken = deepcopy(record)
    if damage == "sql":
        broken["guard_native"]["sql"] += " WHERE TRUE"
        broken["statements"][0]["sql"] = broken["guard_native"]["sql"]
    elif damage == "control_owner":
        broken["guard_native"]["uses"][0]["control"] = 1
    elif damage == "arguments":
        broken["guard_native"]["arguments"][0] = dict(kind="int", value="0")
        broken["statements"][0]["arguments"] = broken["guard_native"]["arguments"]
    elif damage == "missing_statement":
        broken["statements"] = []
    elif damage == "missing_cursor":
        broken["cursors"] = []
    elif damage == "open_cursor":
        broken["cursors"][0]["closed"] = False
    elif damage == "session":
        broken["session_gone"] = False
    elif damage == "terminal":
        broken["statements"][0]["execute_returned"] = False
    elif damage == "public_value":
        broken["rows"][0][0] = dict(kind="int", value="2")
    elif damage == "metadata":
        broken["statements"][0]["metadata"][2][0] = "foreign_field"
    elif damage == "receipt":
        broken["guard_states"] = ["VIOLATED"]
    else:
        broken["rows"] = []
        broken["statements"][0]["fetches"][0]["rows"] = broken["statements"][0][
            "fetches"
        ][0]["rows"][:1]
        broken["statements"][0]["native_rows"] = 1
    with pytest.raises((ValueError, KeyError, IndexError, TypeError)):
        check_attempt(broken, case, program)


def test_real_error_record_does_not_require_an_injected_event(tmp_path):
    from _pietto_phase68_slice7_check import check_control

    record, _case, _program = synthetic(tmp_path)
    record.update(
        rows=[],
        guard_states=["UNKNOWN"],
        interventions=[],
        failure=dict(category="division by zero", sqlstate="22012"),
    )
    record["outcome"].update(transaction="ROLLBACK_ACK", source="FAILED")
    raw = record["statements"][0]
    raw.update(
        execute_returned=False,
        error=dict(kind="DivisionByZero", sqlstate="22012"),
        fetches=[],
    )
    check_control(record, "native_guard_error")
    del raw["error"]
    with pytest.raises(ValueError):
        check_control(record, "native_guard_error")


@pytest.mark.parametrize(
    "requested,native",
    (("stable", "REPEATABLE-READ"), ("serializable", "SERIALIZABLE")),
)
def test_bridge_keeps_requested_profile_separate_from_native_observation(
    tmp_path, monkeypatch, requested, native
):
    from types import SimpleNamespace
    import _pietto_phase68_slice7_probe as probe
    from pietto._project import project_guard_context as context

    case = next(c for c in manifest() if c["name"] == "bag_one")
    prepared = case_preparation(tmp_path, "mysql", case)
    captured = []

    class FakeDriver:
        def __init__(self, config):
            self.controls = []

        def control(self, sql):
            self.controls.append(dict(sql=sql, returned=True))

        def query(self, sql, parameters=(), **options):
            rows = (
                [
                    (
                        prepared.artifact.request.release,
                        native,
                        "utf8mb4",
                        "pietto_query@%",
                        123,
                    )
                ]
                if sql.startswith("SELECT VERSION")
                else [("VIEW", None)]
                if "information_schema" in sql
                else []
            )
            return dict(
                sql=sql,
                parameters=[],
                metadata=[],
                actual=[],
                source_terminal="native_rowset_eof",
                statement_cleanup="close_returned",
                native=dict(terminal=dict(packet=dict(status_flag=8195))),
            ), rows

        def close(self):
            pass

    real_import = probe.importlib.import_module
    monkeypatch.setattr(
        probe.importlib,
        "import_module",
        lambda name: SimpleNamespace() if name == "pyarrow" else real_import(name),
    )
    monkeypatch.setattr(probe.s01, "Driver", FakeDriver)
    monkeypatch.setattr(
        context, "verify_guard_source_columns", lambda *args, **kwargs: None
    )

    def owner(request, **kwargs):
        captured.append((request.isolation, kwargs["environment"][1]))
        raise ValueError("test stops after request/native context capture")

    monkeypatch.setattr(context, "ObservedGuardOwner", owner)
    monkeypatch.setattr(probe, "session_gone", lambda *args, **kwargs: [0])
    resource = SimpleNamespace(
        target="mysql",
        port=3306,
        ca_path="synthetic-ca",
        _passwords=("manager", "query"),
    )
    record = probe.bridge_attempt(resource, prepared, "mysql_rows", isolation=requested)
    expected = "repeatable read" if requested == "stable" else "serializable"
    assert captured == [(expected, expected)]
    assert record["guard_states"] == ("NOT_STARTED",)
    assert (
        record["failure"]["category"]
        == "test stops after request/native context capture"
    )


@pytest.mark.parametrize("remaining", ([1, 0], [1] * 20))
def test_native_close_waits_for_actual_session_terminal(monkeypatch, remaining):
    from types import SimpleNamespace
    import _pietto_phase68_slice6_probe as prior
    from _pietto_phase68_slice7_probe import session_gone

    observations = iter(remaining)
    monkeypatch.setattr(prior, "manager", lambda *args: [(next(observations),)])
    monkeypatch.setattr(prior.time, "sleep", lambda seconds: None)
    resource = SimpleNamespace(target="postgres")
    if remaining[-1] == 0:
        assert session_gone(resource, 123) == remaining
    else:
        with pytest.raises(ValueError, match="owned native session did not close"):
            session_gone(resource, 123)


@pytest.mark.parametrize("group", ("attempts", "control_attempts"))
def test_worker_denominator_rejects_omitted_case_or_control(group):
    from _pietto_phase68_slice7_check import check_worker_denominator

    record = dict(
        attempts=[dict(case="bag_one")], control_attempts=[dict(control="pre_cancel")]
    )
    check_worker_denominator(record, ["bag_one"], ["pre_cancel"])
    record[group].clear()
    with pytest.raises(ValueError, match="S07_RECORD_WORKER_"):
        check_worker_denominator(record, ["bag_one"], ["pre_cancel"])


@pytest.mark.parametrize("history", ([], [1]))
def test_tie_reference_requires_observed_session_absence(history):
    from _pietto_phase68_slice7_check import check_tie_contrast

    with pytest.raises(ValueError, match="TIE_SESSION_CLOSE"):
        check_tie_contrast(
            dict(closed=True, session_close_observations=history), "postgres_adbc"
        )


def test_mysql_wire_bool_and_public_bool_use_full_typed_reconsumption(tmp_path):
    case = next(c for c in manifest() if c["name"] == "bound_four")
    program = prepare_program(case_preparation(tmp_path, "mysql", case))
    native = render_guard(statement_for(program, "combined"))
    names = (program.prefix + "channel", program.prefix + "g0") + tuple(
        c.label for c in program.output.columns
    )
    metadata = [
        [
            name,
            code,
            None,
            None,
            None,
            None,
            0 if i < 2 else 1,
            144 if i == 6 else 1 if i < 2 else 0,
            309 if i == 6 else 63,
        ]
        for i, (name, code) in enumerate(
            zip(names, (8, 8, 8, 8, 8, 5, 252), strict=True)
        )
    ]
    arguments = encoded((native.arguments,))[0]
    wire = (
        (0, 0, None, None, None, None, None),
        (1, 0, 1, None, 1, 0.0, "v"),
        (1, 0, 1, None, 1, 0.0, "v"),
    )
    raw = dict(
        operation=1,
        sql=native.sql.decode(),
        parameters=arguments,
        metadata=metadata,
        actual=encoded(wire),
        source_terminal="native_rowset_eof",
        statement_cleanup="close_returned",
        api_calls=[
            dict(method="execute", sql=None, values=arguments),
            dict(method="cmd_stmt_prepare", sql=native.sql.decode()),
            dict(method="cmd_stmt_execute", values=arguments),
        ],
    )
    record = dict(
        synthetic=True,
        case=case["name"],
        route="mysql_rows",
        session=123,
        role="pietto_query@%",
        environment=[
            program.preparation.artifact.request.release,
            "repeatable read",
            True,
            "utf8mb4",
        ],
        rows=encoded(case["rows"]),
        guard_states=["FULFILLED"],
        guard_native=native_record(native),
        statements=[raw],
        statement_count=1,
        closed=True,
        session_gone=True,
        transaction="COMMIT_ACK",
        controls=[
            dict(sql="START TRANSACTION READ ONLY", returned=True),
            dict(sql="COMMIT", returned=True),
        ],
        operations=[
            dict(
                ordinal=0,
                kind="control",
                sql="START TRANSACTION READ ONLY",
                state="terminal",
                returned=True,
            ),
            dict(
                ordinal=1,
                kind="query",
                sql=native.sql.decode(),
                arguments=arguments,
                state="terminal",
                closed=True,
            ),
            dict(
                ordinal=2, kind="control", sql="COMMIT", state="terminal", returned=True
            ),
        ],
    )
    record = json.loads(json.dumps(record))
    check_attempt(record, case, program)
    record["statements"][0]["actual"][-1][-1] = dict(kind="text", value="w")
    with pytest.raises(ValueError, match="PUBLIC_RECONSUMPTION"):
        check_attempt(record, case, program)
