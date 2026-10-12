"""Data-only oracle for the separately dispatched public MySQL witness."""

from __future__ import annotations

import copy
import subprocess
import sys

import pytest

import _pietto_execution_api_mysql_native as native


@pytest.fixture
def report():
    origin = "a" * 64
    return {
        "format": native.FORMAT,
        "status": "PASS",
        "wheel_sha256": origin,
        "otel_wheels": {name: origin for name in native.OTEL_WHEELS},
        "otel_unselected": native.CP312_WRAPT,
        "identity": {
            "interpreter": ["CPython", "3.13.13", "Linux"],
            "server": "8.4.12",
            "wheel_sha256": origin,
            "origins": {"pietto": origin, "mysql.connector.connection": origin},
            "drivers": {
                "mysql-connector-python": "26.7.0",
                "pyarrow": "25.0.1",
            },
        },
        "telemetry": {
            "versions": {
                "opentelemetry-api": "1.33.1",
                "opentelemetry-sdk": "1.33.1",
                "wrapt": "2.5.0",
            },
            "recording": True,
            "exporters": [],
            "selected_wheel": "wrapt-2.5.0-cp313-example.whl",
        },
        "profile": {
            "host": "localhost",
            "identity_verified": True,
            "tls": "TLSv1.3",
            "certificate": {
                "reload": "ALTER INSTANCE RELOAD TLS",
                "sans": ["DNS:localhost", "IP Address:127.0.0.1"],
                "service": [
                    {
                        "host": "127.0.0.1",
                        "identity_verified": True,
                        "tls": "TLSv1.3",
                        "fresh_leaf": True,
                    },
                    {
                        "host": "localhost",
                        "identity_verified": True,
                        "tls": "TLSv1.3",
                        "fresh_leaf": True,
                    },
                ],
            },
            "attrs_oracle": {
                "enabled": True,
                "size": 512,
                "positive": [["pietto_s06_marker", "present"]],
            },
            "sessions": [
                {
                    "kind": "data",
                    "attrs": [],
                    "connect_args": False,
                    "otel": False,
                    "traceparent": False,
                    "tls": "TLSv1.3",
                    "auth": "caching_sha2_password",
                },
                {
                    "kind": "control",
                    "attrs": [],
                    "connect_args": False,
                    "otel": False,
                    "traceparent": False,
                    "tls": "TLSv1.3",
                    "auth": "caching_sha2_password",
                },
            ],
            "packets": {
                "handshake": [
                    {
                        "client_flags": 1,
                        "connect_args": False,
                        "attribute_encoding": False,
                        "traceparent": False,
                    },
                    {
                        "client_flags": 1,
                        "connect_args": False,
                        "attribute_encoding": False,
                        "traceparent": False,
                    },
                ],
                "query": [{"traceparent": False}],
                "query_attrs": [[]],
                "prepare": True,
                "execute": True,
                "control": True,
            },
        },
        "cases": {
            "rows": {"rows": native.ROWS, "end": "COMPLETE"},
            "bundle": {"rows": native.ROWS, "end": "COMPLETE"},
            "empty": {"rows": [], "end": "COMPLETE"},
            "schema": {
                "schema": [["left_id", "int64", False], ["right_key", "int64", True]]
            },
            "cancel": {
                "end": "CANCELLED",
                "cleanup": "LOCAL_CLOSED_REMOTE_UNOBSERVED",
                "source": "INCOMPLETE",
                "delivery": "FAILED",
                "deadline_expired": False,
                "transaction": "UNKNOWN",
                "remote": "REMOTE_QUIESCENCE_UNCONFIRMED",
                "cancel": {"requested": True, "sent": True, "observed": False},
                "primary": ["PIE-R3009", None, None],
                "error": {"code": "PIE-R3009", "receipt": None},
                "control_kill": True,
                "consumer_thread_joined": True,
                "late_unchanged": True,
                "batches": 0,
                "rows": 0,
                "blocked": {
                    "session": 1,
                    "event": "statement/sql/select",
                    "sql_sha256": "b" * 64,
                    "native_statement": "NativeStatement",
                    "purpose": "query",
                    "server": {
                        "current_rows": 1,
                        "statement_event": "statement/com/Execute",
                        "end_event_id": None,
                        "process_state": "executing",
                        "process_command": "Execute",
                    },
                },
            },
            "deadline": {
                "end": "DEADLINE",
                "cleanup": "LOCAL_CLOSED_REMOTE_UNOBSERVED",
                "source": "INCOMPLETE",
                "delivery": "FAILED",
                "deadline_expired": True,
                "transaction": "ROLLBACK_ACK",
                "remote": "TRANSACTION_ACK",
                "cancel": {"requested": True, "sent": True, "observed": True},
                "primary": ["PIE-R3001", "EXECUTION_DEADLINE", "query"],
                "error": {"code": "PIE-R3001"},
                "control_kill": True,
                "consumer_thread_joined": True,
                "late_unchanged": True,
                "batches": 0,
                "rows": 0,
                "blocked": {
                    "session": 2,
                    "event": "statement/sql/select",
                    "sql_sha256": "b" * 64,
                    "native_statement": "NativeStatement",
                    "purpose": "query",
                    "server": {
                        "current_rows": 1,
                        "statement_event": "statement/com/Execute",
                        "end_event_id": None,
                        "process_state": "executing",
                        "process_command": "Execute",
                    },
                },
            },
        },
        "factory": {
            "origin": "live",
            "module": "main.pietto",
            "kind": "table",
            "name": "result",
            "dialect": "mysql",
        },
        "cleanup": "PASS",
    }


def test_checker_accepts_literal_native_facts(report):
    assert native.check(report) == {"family": "mysql-native", "verdict": "ACCEPTED"}


def test_checker_preserves_a_server_statement_timeout(report):
    report["cases"]["deadline"].update(
        end="FAILED",
        deadline_expired=False,
        cancel={"requested": False, "sent": False, "observed": False},
        primary=["PIE-R3002", None, None],
        error={"code": "PIE-R3002"},
        control_kill=False,
    )
    assert native.check(report) == {"family": "mysql-native", "verdict": "ACCEPTED"}


def test_terminal_readiness_has_a_bounded_wait():
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        with pytest.raises(ValueError, match="^TEST_READY_TIMEOUT$"):
            native._worker_line(child, "TEST_READY", seconds=0.01)
    finally:
        child.kill()
        child.wait(timeout=5)


def test_terminal_worker_sends_config_before_readiness():
    class Stdin:
        writes: list[str]
        flushed: bool

        def __init__(self):
            self.writes = []
            self.flushed = False

        def write(self, value: str) -> None:
            self.writes.append(value)

        def flush(self) -> None:
            self.flushed = True

    class Process:
        stdin: Stdin | None

        def __init__(self):
            self.stdin = Stdin()

    process = Process()
    native._send_worker_config(process, {"case": "terminal"})
    assert process.stdin is not None
    assert process.stdin.writes == ['{"case": "terminal"}\n']
    assert process.stdin.flushed is True


def test_preterminal_checker_refuses_a_failed_worker_outcome(report):
    cases = copy.deepcopy(report["cases"])
    cases["rows"]["end"] = "FAILED"
    with pytest.raises(native.Rejected, match="^ROWS$"):
        native._check_nonterminal_cases(cases)


@pytest.mark.parametrize(
    "damage,reason",
    (
        (lambda r: r["profile"].update(identity_verified=False), "TLS_IDENTITY"),
        (
            lambda r: r["profile"]["sessions"][0].update(attrs=[["_pid", "x"]]),
            "CONN_ATTRS",
        ),
        (lambda r: r["profile"]["sessions"][1].update(traceparent=True), "OTEL"),
        (
            lambda r: r["profile"]["attrs_oracle"].update(size=0),
            "ATTRS_ORACLE",
        ),
        (
            lambda r: r["profile"]["packets"].update(execute=False),
            "PACKETS",
        ),
        (
            lambda r: r["profile"]["packets"].update(query_attrs=[["traceparent"]]),
            "PACKETS",
        ),
        (
            lambda r: r["profile"]["certificate"].update(sans=[]),
            "TLS_CERTIFICATE",
        ),
        (
            lambda r: r.update(otel_unselected="wrapt-cp313.whl"),
            "OTEL_WHEELS",
        ),
        (
            lambda r: r["cases"]["cancel"]["cancel"].update(sent=False),
            "CANCEL_FACTS",
        ),
        (
            lambda r: r["cases"]["deadline"].update(late_unchanged=False),
            "DEADLINE_FACTS",
        ),
        (
            lambda r: r["cases"]["deadline"].update(blocked=None),
            "DEADLINE_BLOCKED",
        ),
        (
            lambda r: r["cases"]["cancel"]["blocked"].update(purpose="admission"),
            "CANCEL_BLOCKED",
        ),
        (
            lambda r: r.update(factory={}),
            "PUBLIC_FACTORY",
        ),
        (lambda r: r["cases"]["rows"].update(rows=[]), "ROWS"),
    ),
)
def test_checker_refuses_native_damage(report, damage, reason):
    bad = copy.deepcopy(report)
    damage(bad)
    with pytest.raises(native.Rejected, match="^" + reason + "$"):
        native.check(bad)
