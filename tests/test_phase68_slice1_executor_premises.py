"""Offline report damages; synthetic records are never native support evidence."""

from contextlib import contextmanager
import io
import json
import os
import subprocess
from copy import deepcopy
from functools import cache
import tempfile
import importlib.util
from pathlib import Path
import sys
from typing import Any, cast

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pietto_phase68_executor_premise", ROOT / "scripts/phase68_executor_premise.py"
)
assert SPEC is not None and SPEC.loader is not None
PROBE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)
p = cast(Any, PROBE)
c = p.helper("_pietto_phase68_executor_cases")


RUNTIME = {
    "python": "3.13.13 synthetic",
    "executable": "/synthetic/python",
    "versions": dict(c.PINS),
    "origins": {name: "/synthetic/site-packages" for name in c.PINS},
    "libraries": {"synthetic": "not-native-evidence"},
    "modules": {
        name: "/synthetic/" + name
        for name in (
            "psycopg",
            "mysql.connector",
            "adbc_driver_manager",
            "adbc_driver_postgresql",
            "pyarrow",
        )
    },
}


@cache
def fixed_artifact(target):
    emission = p.helper("_pietto_phase66_sql_emission_probe")
    from pietto._project.project_sql_emission import serialize_project_sql_emission

    with tempfile.TemporaryDirectory(
        prefix="pietto-phase68-slice01-unit-"
    ) as temporary:
        fixture = emission.fixed_fixture(target, "R_fixed_direct", "bind")
        _, outcome = emission.build_case(
            Path(temporary), fixture["source"], fixture["contract"], fixture["policy"]
        )
        data = serialize_project_sql_emission(outcome)
    return data.decode(), emission.decode_public(data)


def submission(sql, values, route):
    if route == "mysql_rows":
        return [
            {"method": "cmd_stmt_prepare", "sql": sql, "values": []},
            {"method": "execute", "sql": None, "values": deepcopy(values)},
            {"method": "cmd_stmt_execute", "sql": None, "values": deepcopy(values)},
        ]
    return [{"method": "execute", "sql": sql, "values": deepcopy(values)}]


def report():
    rows = []
    for route, group, case in c.DENOMINATOR:
        target = "mysql" if route == "mysql_rows" else "postgres"
        observation = {
            "source_terminal": "synthetic EOF",
            "statement_cleanup": "close_returned",
            "actual": [],
        }
        if case == "identity":
            observation = {
                "distributions": dict(c.PINS),
                "python": "3.13.13 synthetic",
                "native_libraries": {"synthetic": "not-native-evidence"},
                "session": {"actual": [[{"kind": "text", "value": "pietto_query"}]]},
            }
        elif group in ("P02", "P03") or case in (
            "multi_pull",
            "empty_eof",
            "compiled_nonempty",
            "compiled_empty",
        ):
            observation["actual"] = deepcopy(c.expected_rows(case, route))
            if group == "P02":
                values = [
                    p.scalar(v)
                    for v in c.parameters(target, c.CASES[group].index(case))
                ]
                observation.update(
                    sql=c.PARAMETER_SQL[target],
                    parameters=values,
                    api_calls=[
                        {
                            "method": "execute",
                            "sql": c.PARAMETER_SQL[target],
                            "values": deepcopy(values),
                        }
                    ],
                )
            if group == "P03":
                observation["metadata"] = [[label] for label in c.LABELS]
            if group == "P07":
                observation.update(
                    plan_verified=True, producer_fields=2, artifact_retained=True
                )
        elif case == "stable_view":
            values = [[{"kind": "int", "value": "10"}]]
            observation.update(
                before={"actual": values},
                after={"actual": deepcopy(values)},
                transaction_terminal="COMMIT_returned",
            )
        elif case == "serializable_readonly":
            observation["transaction_terminal"] = "COMMIT_returned"
        elif case == "late_error":
            observation["error"] = {"type": "DivisionByZero", "sqlstate": "22012"}
        elif case == "early_close":
            observation["delivery_complete"] = False
        elif case == "cleanup_injection":
            observation["injected_cleanup"] = {"type": "RuntimeError", "natural": False}
        elif case == "cancel_blocking_read":
            observation.update(
                cancellation={"request": {"execution_observed": True}},
                control_joined=True,
                error={"type": "QueryCanceled", "sqlstate": "57014"},
            )
        elif case == "fixed_emission_values":
            expected = p.helper("_pietto_target_conformance_cases").fixed_rows(target)
            observation.update(
                original_typed_rows=deepcopy(expected),
                expected_original_rows=expected,
                plan_verified=True,
            )
        elif case == "family_inventory":
            observation.update(families=dict(c.FAMILIES), production_changed=False)
        if case == "identity":
            observation.update(
                executable=RUNTIME["executable"], origins=deepcopy(RUNTIME["origins"])
            )
            modules = {
                "postgres_rows": ("psycopg",),
                "mysql_rows": ("mysql.connector",),
                "postgres_adbc": (
                    "adbc_driver_manager",
                    "adbc_driver_postgresql",
                    "pyarrow",
                ),
            }[route]
            observation["module_paths"] = {
                name: RUNTIME["modules"][name] for name in modules
            }
        if group == "P02":
            observation["api_calls"] = submission(
                observation["sql"], observation["parameters"], route
            )
        if group == "P03":
            observation["domain_valid"] = True
        if case in ("stable_view", "serializable_readonly"):
            isolation = "repeatable read" if case == "stable_view" else "serializable"
            isolation = (
                isolation
                if target == "postgres"
                else isolation.upper().replace(" ", "-")
            )
            observation["session"] = {
                "actual": [
                    [
                        {"kind": "text", "value": "pietto_query"},
                        {"kind": "text", "value": "phase66"},
                        {"kind": "int", "value": "123"},
                        {"kind": "text", "value": isolation},
                        {"kind": "text", "value": "on"}
                        if target == "postgres"
                        else {"kind": "int", "value": "1"},
                        {"kind": "text", "value": "synthetic server"},
                    ]
                ]
            }
            observation["controls"] = [{"sql": "COMMIT", "returned": True}]
            observation["mutation"] = {
                "manager_actual": [[{"kind": "int", "value": "11"}]]
            }
            observation["read"] = {"actual": [[{"kind": "int", "value": "11"}]]}
        if case == "cancel_blocking_read":
            observation["owned_session_id"] = 123
            observation["cancellation"]["request"].update(
                session_id=123, signal_sent=target == "mysql"
            )
            observation["cancellation"]["signal"] = (
                "owned manager KILL QUERY returned" if target == "mysql" else "returned"
            )
            if target == "mysql":
                observation.pop("error")
                observation["actual"] = [[{"kind": "int", "value": "1"}]]
                observation["source_terminal"] = "native_rowset_eof"
        if case == "fixed_emission_values":
            data, document = fixed_artifact(target)
            values = [
                p.scalar(v)
                for v in p.helper(
                    "_pietto_phase66_sql_emission_probe"
                ).decoded_arguments(document)
            ]
            observation.update(
                artifact_bytes=data,
                sql=document["sql"],
                parameters=values,
                api_calls=submission(document["sql"], values, route),
            )
            observation.pop("expected_original_rows", None)
        rows.append(
            dict(
                route=route,
                target=target,
                group=group,
                case=case,
                status="OBSERVED_SUPPORTED",
                observation=observation,
            )
        )
    return {
        "format": p.FORMAT,
        "input_identity": {"synthetic-fixture": "separate expected context"},
        "location": "local",
        "records": rows,
        "resources": [
            {"target": target, "cleanup": {"status": "success"}}
            for target in ("postgres", "mysql")
        ],
        "assessment": "READY_FOR_SLICE02_EXPERIMENT",
    }


def validate(value):
    p.verify_report(value, {"synthetic-fixture": "separate expected context"}, RUNTIME)


def test_offline_complete_denominator_and_optional_import_boundary():
    validate(report())
    assert len(c.DENOMINATOR) == 57
    assert len(set(c.DENOMINATOR)) == 57
    assert "adbc_driver_postgresql" not in sys.modules


@pytest.mark.parametrize(
    "damage",
    (
        "missing_route",
        "missing_case",
        "dependency",
        "source",
        "input",
        "actual",
        "target",
        "terminal",
        "unsupported_promoted",
        "false_ready",
        "duplicate",
        "same_domain_signed_zero",
        "lost_duplicate",
        "swapped_columns",
        "cleanup",
        "role",
        "cancel",
        "families",
        "native_library",
        "submitted_sql",
        "domain_claim",
        "isolation",
        "fixed_argument",
    ),
)
def test_damaged_reports_are_rejected(damage):
    value = report()
    records = value["records"]
    parameter = records[1]["observation"]
    if damage == "missing_route":
        value["records"] = [r for r in records if r["route"] != "postgres_adbc"]
    elif damage == "missing_case":
        records.pop()
    elif damage == "dependency":
        records[0]["observation"]["distributions"]["psycopg"] = "0.0.0"
    elif damage == "source":
        value["input_identity"] = {"synthetic-fixture": "foreign"}
    elif damage == "input":
        parameter["parameters"][0]["value"] = "1"
    elif damage == "actual":
        parameter["actual"][0][0]["value"] = "9007199254740992"
    elif damage == "target":
        records[1]["target"] = "mysql"
    elif damage == "terminal":
        parameter["source_terminal"] = "not_observed"
    elif damage == "unsupported_promoted":
        parameter["error"] = {"type": "NotSupportedError"}
    elif damage == "false_ready":
        records[1]["status"] = "OBSERVED_UNSUPPORTED"
        parameter["error"] = {"type": "NotSupportedError"}
    elif damage == "duplicate":
        records[-1] = deepcopy(records[-2])
    elif damage in ("same_domain_signed_zero", "lost_duplicate", "swapped_columns"):
        actual = next(
            r["observation"]["actual"]
            for r in records
            if r["case"] == "carriers_populated"
        )
        if damage == "same_domain_signed_zero":
            actual[0][2]["bits"] = "0000000000000000"
        elif damage == "lost_duplicate":
            actual.pop()
        else:
            actual[0][0], actual[0][1] = actual[0][1], actual[0][0]
    elif damage == "cleanup":
        value["resources"][0]["cleanup"]["status"] = "failed"
    elif damage == "role":
        records[0]["observation"]["session"]["actual"][0][0]["value"] = "pietto_manager"
    elif damage == "cancel":
        next(r["observation"] for r in records if r["case"] == "cancel_blocking_read")[
            "control_joined"
        ] = False
    elif damage == "families":
        next(r["observation"] for r in records if r["case"] == "family_inventory")[
            "families"
        ].pop("JOIN")
    elif damage == "native_library":
        records[0]["observation"]["native_libraries"]["synthetic"] = "foreign"
    elif damage == "submitted_sql":
        parameter["api_calls"][0]["sql"] = "SELECT 0"
    elif damage == "domain_claim":
        next(r["observation"] for r in records if r["case"] == "carriers_populated")[
            "domain_valid"
        ] = False
    elif damage == "isolation":
        next(r["observation"] for r in records if r["case"] == "stable_view")[
            "session"
        ]["actual"][0][3]["value"] = "read committed"
    elif damage == "fixed_argument":
        next(r["observation"] for r in records if r["case"] == "fixed_emission_values")[
            "parameters"
        ].pop()
    with pytest.raises(ValueError):
        validate(value)


def test_honest_unsupported_blocks_product_gate_and_environment_holds():
    value = report()
    value["records"][1]["status"] = "OBSERVED_UNSUPPORTED"
    value["records"][1]["observation"]["error"] = {"type": "NotSupportedError"}
    value["assessment"] = "PRODUCT_GATE_BLOCKED_REPLAN"
    validate(value)
    value["records"][1]["status"] = "INCONCLUSIVE_ENVIRONMENT"
    value["assessment"] = "HOLD"
    validate(value)


def test_source_oracle_keeps_duplicates_null_and_float_bits():
    expected = c.expected_rows("carriers_populated", "postgres_rows")
    assert len(expected) == 2 and expected[0] == expected[1]
    changed = deepcopy(expected)
    changed[0][2]["bits"] = "0000000000000000"
    assert not p.check_values(
        {"actual": changed}, "carriers_populated", "postgres_rows"
    )
    assert p.scalar(-0.0) != p.scalar(0.0)


# These exercise the exact pump used by run_child, with owned real OS pipes.


def wire(message):
    return json.dumps(message, ensure_ascii=False).encode("utf-8") + b"\n"


@contextmanager
def owned_control_child(code, *, pass_fds=()):
    child = subprocess.Popen(
        [sys.executable, "-I", "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        pass_fds=pass_fds,
    )
    try:
        yield child
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=2)
        for stream in (child.stdin, child.stdout, child.stderr):
            assert stream is not None
            stream.close()


def coalesced_child():
    together = wire({"event": "observation", "record": {"ordinal": 1}}) + wire(
        {"event": "empty_rows"}
    )
    terminal = wire({"event": "result", "records": []})
    return (
        "import os,sys,json\n"
        f"os.write(1, {together!r})\n"
        "assert json.loads(sys.stdin.buffer.readline()) == {'ack': 'empty_rows'}\n"
        "os.write(2, b'bounded diagnostic')\n"
        f"os.write(1, {terminal!r})\n"
    )


def ack_dispatch(child, received):
    def dispatch(message):
        received.append(message["event"])
        if message["event"] == "empty_rows":
            assert received == ["observation", "empty_rows"]
            p._send_control(child, {"ack": "empty_rows"})

    return dispatch


def test_real_control_pump_drains_coalesced_requests_before_waiting_for_ack():
    received = []
    with owned_control_child(coalesced_child()) as child:
        stderr = p._pump_child(child, ack_dispatch(child, received), seconds=3)
        assert child.returncode == 0
        assert stderr == b"bounded diagnostic"
    assert received == ["observation", "empty_rows", "result"]


def test_old_buffered_policy_fails_the_same_coalesced_ack_protocol(monkeypatch):
    received = []
    with owned_control_child(coalesced_child()) as child:
        assert isinstance(child.stdout, io.FileIO)
        with p.selectors.DefaultSelector() as ready:
            ready.register(child.stdout, p.selectors.EVENT_READ)
            assert ready.select(3), "coalesced write barrier"
        old_reader = io.TextIOWrapper(io.BufferedReader(child.stdout), encoding="utf-8")
        original_read = os.read
        descriptor = child.stdout.fileno()

        def buffered_policy(fd, count):
            return (
                old_reader.readline().encode("utf-8")
                if fd == descriptor
                else original_read(fd, count)
            )

        with monkeypatch.context() as patch:
            patch.setattr(p.os, "read", buffered_policy)
            with pytest.raises(TimeoutError, match="control timeout"):
                p._pump_child(child, ack_dispatch(child, received), seconds=1)
        assert received == ["observation"]
        assert child.poll() is not None
        old_reader.close()


def test_real_control_pump_retains_fragmented_utf8_until_complete(monkeypatch):
    frame = wire({"event": "empty_rows", "note": "雪😀"})
    split = frame.index("雪".encode("utf-8")) + 1
    first, second = frame[:split], frame[split:]
    barrier_read, barrier_write = os.pipe()
    received, partial = [], []
    code = (
        "import os,sys,json\n"
        f"os.write(1, {first!r})\n"
        f"assert os.read({barrier_read}, 1) == b'g'\n"
        f"os.write(1, {second!r})\n"
        "assert json.loads(sys.stdin.buffer.readline()) == {'ack': 'empty_rows'}\n"
        f"os.write(1, {wire({'event': 'result', 'records': []})!r})\n"
    )
    try:
        with owned_control_child(code, pass_fds=(barrier_read,)) as child:
            assert child.stdout is not None
            descriptor = child.stdout.fileno()
            original_read = os.read

            def observe_partial(fd, count):
                data = original_read(fd, count)
                if fd == descriptor and data == first:
                    assert not received
                    partial.append(True)
                    os.write(barrier_write, b"g")
                return data

            def dispatch(message):
                received.append(message)
                if message["event"] == "empty_rows":
                    assert partial == [True]
                    assert message["note"] == "雪😀"
                    p._send_control(child, {"ack": "empty_rows"})

            with monkeypatch.context() as patch:
                patch.setattr(p.os, "read", observe_partial)
                p._pump_child(child, dispatch, seconds=3)
            assert child.returncode == 0
    finally:
        os.close(barrier_read)
        os.close(barrier_write)
    assert [m["event"] for m in received] == ["empty_rows", "result"]


@pytest.mark.parametrize(
    "suffix,error",
    [(b"", "missing terminal"), (b'{"event":', "incomplete control frame")],
)
def test_real_control_eof_drains_frames_but_cannot_invent_completion(suffix, error):
    payload = wire({"event": "observation", "record": {"ordinal": 1}}) + suffix
    received = []
    with owned_control_child(f"import os; os.write(1, {payload!r})") as child:
        with pytest.raises(RuntimeError, match=error):
            p._pump_child(
                child, lambda message: received.append(message["event"]), seconds=3
            )
        assert child.poll() is not None
    assert received == ["observation"]


def test_real_control_timeout_and_broken_peer_reap_without_inventing_ack():
    received = []
    with owned_control_child("import os; os.read(0, 1)") as child:
        with pytest.raises(TimeoutError, match="control timeout"):
            p._pump_child(child, received.append, seconds=0.2)
        assert child.poll() is not None
    assert received == []
    payload = wire({"event": "empty_rows"})
    with owned_control_child(
        f"import os; os.close(0); os.write(1, {payload!r})"
    ) as child:
        with pytest.raises(BrokenPipeError):
            p._pump_child(
                child,
                lambda message: p._send_control(child, {"ack": message["event"]}),
                seconds=3,
            )
        assert child.poll() is not None


def test_control_stderr_is_drained_bounded_and_primary_failure_survives():
    with owned_control_child(
        "import os; os.write(2, b'x' * 8192); os.read(0, 1)"
    ) as child:
        with pytest.raises(RuntimeError, match="stderr limit"):
            p._pump_child(child, lambda message: None, seconds=3)
        assert child.poll() is not None
    payload = wire({"event": "worker_error", "failure": {"type": "controlled"}})
    with owned_control_child(
        f"import os; os.write(1, {payload!r}); os.read(0, 1)"
    ) as child:

        def fail(message):
            raise ValueError("primary marker")

        with pytest.raises(ValueError, match="primary marker"):
            p._pump_child(child, fail, seconds=3)
        assert child.poll() is not None


def test_adbc_type_metadata_is_explicitly_encoded_before_report_byte_limits():
    class ArrowType:
        def __str__(self):
            return "int64"

    class Field:
        name = "value"
        type = ArrowType()
        nullable = True
        metadata = None

    closed = []

    class Reader:
        schema = [Field()]

        def read_next_batch(self):
            raise StopIteration

        def close(self):
            closed.append("reader")

    class Cursor:
        description = [("value", ArrowType(), None, None, None, None, None)]
        rowcount = -1

        def execute(self, operation, parameters=None):
            assert operation == "SELECT typed_empty"
            assert parameters is None

        def fetch_record_batch(self):
            return Reader()

        def close(self):
            closed.append("cursor")

    class Connection:
        def cursor(self, **options):
            assert options["adbc_stmt_kwargs"]["adbc.postgresql.use_copy"] is True
            return Cursor()

    driver = object.__new__(p.Driver)
    driver.route = "postgres_adbc"
    driver.config = {"password": "test-only"}
    driver.connection = Connection()
    record, actual = driver.query("SELECT typed_empty")
    assert record["metadata"] == [["value", "int64", None, None, None, None, None]]
    assert record["rowcount_observed"] == -1
    assert record["source_terminal"] == "arrow_StopIteration"
    assert actual == [] and closed == ["reader", "cursor"]
    assert json.loads(json.dumps(record))["metadata"] == record["metadata"]


@pytest.mark.parametrize(
    "damage", ("two_native_submissions", "missing_helper", "changed_helper_values")
)
def test_mysql_helper_call_is_not_a_second_native_submission(damage):
    value = report()
    validate(value)
    observed = next(
        row["observation"]
        for row in value["records"]
        if row["route"] == "mysql_rows" and row["case"] == "parameterized_nonempty"
    )
    if damage == "two_native_submissions":
        observed["api_calls"].append(deepcopy(observed["api_calls"][-1]))
    elif damage == "missing_helper":
        observed["api_calls"].pop(1)
    else:
        observed["api_calls"][1]["values"][0]["value"] = "2"
    with pytest.raises(ValueError):
        validate(value)


def test_mysql_cancel_premise_uses_native_command_and_standalone_sleep_terminal():
    running = [
        123,
        "pietto_query",
        "127.0.0.1",
        "phase66",
        "Execute",
        0,
        "User sleep",
        "SELECT SLEEP(5)",
    ]
    assert p._mysql_blocking_session([running], 123)
    for index, value in ((0, 124), (4, "Query"), (6, "Sleep"), (7, "SELECT 1")):
        wrong = running[:]
        wrong[index] = value
        assert not p._mysql_blocking_session([wrong], 123)
    assert not p._mysql_blocking_session([running, running], 123)
    assert not p._mysql_blocking_session([], 123)
    record = next(
        row["observation"]
        for row in report()["records"]
        if row["route"] == "mysql_rows" and row["case"] == "cancel_blocking_read"
    )
    assert p._cancellation_matches(record, "mysql")
    for field in ("execution_observed", "signal_sent"):
        wrong = deepcopy(record)
        wrong["cancellation"]["request"][field] = False
        assert not p._cancellation_matches(wrong, "mysql")
    wrong = deepcopy(record)
    wrong["actual"][0][0]["value"] = "0"
    assert not p._cancellation_matches(wrong, "mysql")
    wrong = deepcopy(record)
    wrong["cancellation"]["request"]["session_id"] = 124
    assert not p._cancellation_matches(wrong, "mysql")
