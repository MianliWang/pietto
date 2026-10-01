"""Discriminating private evidence refusals; no native acquisition in pytest."""

from copy import deepcopy
from typing import Any

import pytest

from _pietto_phase68_slice8_check import native_statements, require


def test_record_boolean_is_not_a_terminal_or_source_grant():
    with pytest.raises(ValueError, match="S08_RECORD_SOURCE"):
        require(False, "SOURCE")
    # An asserted successful statement with no actual native calls is rejected.
    for statement in ({}, {"terminal": {"status_flag": 8193}}):
        with pytest.raises(ValueError, match="STATEMENT_DENOMINATOR"):
            native_statements({"events": [], "statements": [statement]})


def test_native_statement_inventory_never_ignores_unowned_or_foreign_events():
    base = {
        "events": [
            {
                "connection": "data",
                "session": 1,
                "event": "cmd_stmt_execute.call",
                "value": {},
            }
        ],
        "session": 1,
        "statements": [],
    }
    with pytest.raises(ValueError, match="UNOWNED_NATIVE_EVENT"):
        native_statements(base)
    foreign = deepcopy(base)
    foreign["events"][0]["session"] = 2
    with pytest.raises(ValueError, match="NATIVE_SESSION"):
        native_statements(foreign)


@pytest.mark.parametrize("exit_code", (0, 7))
def test_worker_registration_gate_and_reaping_use_real_pipe(tmp_path, exit_code):
    import json
    import os
    import sys
    from _pietto_phase68_slice8_probe import worker_process

    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps(dict(limits={}, used={}, events=[])))
    code = "import json,sys;assert sys.stdin.read(1)=='1';assert json.load(open(sys.argv[1]))['events'][-1]['kind']=='registered_worker';sys.exit(int(sys.argv[2]))"
    with (tmp_path / "worker.log").open("w") as log:
        actual = worker_process(
            [sys.executable, "-c", code, str(ledger), str(exit_code)],
            dict(os.environ),
            ledger,
            log,
            origin="offline",
            group="gate",
            directory=tmp_path,
            seconds=10,
        )
    events = json.loads(ledger.read_text())["events"]
    assert actual == exit_code
    assert [e["kind"] for e in events] == ["registered_worker", "worker_reaped"]
    assert events[0]["pid"] == events[1]["pid"] and events[1]["returncode"] == exit_code


def test_registered_worker_timeout_is_reaped(tmp_path):
    import json
    import os
    import subprocess
    import sys
    from _pietto_phase68_slice8_probe import worker_process

    ledger = tmp_path / "ledger.json"
    ledger.write_text(json.dumps(dict(limits={}, used={}, events=[])))
    code = "import sys,threading;sys.stdin.read(1);threading.Event().wait(10)"
    with (tmp_path / "worker.log").open("w") as log:
        with pytest.raises(subprocess.TimeoutExpired):
            worker_process(
                [sys.executable, "-c", code],
                dict(os.environ),
                ledger,
                log,
                origin="offline",
                group="timeout",
                directory=tmp_path,
                seconds=0.1,
            )
    events = json.loads(ledger.read_text())["events"]
    assert [e["kind"] for e in events] == ["registered_worker", "worker_reaped"]
    assert events[-1]["returncode"] is not None


def test_component_builder_stages_nested_fixture_parent(tmp_path):
    from _pietto_phase68_slice8_probe import component_artifact

    artifact = component_artifact(tmp_path / "not-created" / "component")
    assert artifact is not None and artifact.request.family == "mysql"
    assert artifact.request.sources[0].name == "p68s3_input"


def test_native_view_prepare_denial_is_specific_not_arbitrary_error():
    from _pietto_phase68_slice8_check import check_controls

    record: dict[str, Any] = dict(
        kind="prepare_error",
        rows=[],
        failure=dict(errno=1356, sqlstate="HY000"),
        control_joined=True,
        sessions_gone={"1": [0], "2": [0]},
        outcome=dict(
            cleanup="LOCAL_CLOSED_REMOTE_UNOBSERVED",
            delivery="FAILED",
            primary=dict(phase="query"),
        ),
    )
    check_controls([record], ["prepare_error"])
    damaged = deepcopy(record)
    damaged["failure"]["errno"] = 9999
    with pytest.raises(ValueError, match="NATIVE_PREPARE_ERROR"):
        check_controls([damaged], ["prepare_error"])


def context_record():
    from _pietto_phase68_slice6_probe import s01
    from pietto._project.project_execution_mysql_context import CONTEXT_SQL, EPOCH_SQL

    context = [
        "8.4.12",
        "reader@%",
        "NONE",
        7,
        "phase66",
        "REPEATABLE-READ",
        "utf8mb4",
        "utf8mb4",
        "utf8mb4",
        "utf8mb4_0900_bin",
        "ONLY_FULL_GROUP_BY,STRICT_ALL_TABLES,NO_ENGINE_SUBSTITUTION",
        "+00:00",
        0,
        1000,
        "server-a",
    ]
    epoch = [
        11,
        13,
        "ACTIVE",
        "READ ONLY",
        "REPEATABLE READ",
        "NO",
        "server-a",
        "reader@%",
        "NONE",
        "phase66",
    ]
    record: dict[str, Any] = dict(
        context=context, epoch=epoch, role="reader@%", session=7, events=[]
    )
    for connection, session, sql, row in (
        ("data", 7, CONTEXT_SQL, context),
        (
            "data",
            7,
            EPOCH_SQL.replace("%s", "7", 1).replace("%s", "'reader'", 1),
            epoch,
        ),
        (
            "control",
            8,
            EPOCH_SQL.replace("%s", "7", 1).replace("%s", "'reader'", 1),
            epoch,
        ),
    ):
        for name, value in (
            ("cmd_query.call", sql),
            ("cmd_query.return", dict(rowset=False, warnings=None)),
            ("get_rows.call", dict(binary=False, count=1, columns=[])),
            (
                "get_rows.return",
                dict(
                    rows=[[s01.scalar(v) for v in row]],
                    eof=dict(
                        warning_count=0, status_flag=8193 if connection == "data" else 2
                    ),
                ),
            ),
        ):
            record["events"].append(
                dict(connection=connection, session=session, event=name, value=value)
            )
    return record


@pytest.mark.parametrize(
    "damage",
    (
        "server",
        "account",
        "epoch",
        "missing_context",
        "missing_control",
        "missing_eof",
        "session",
        "missing_reply",
    ),
)
def test_copied_context_requires_actual_native_reply_and_terminal(damage):
    from _pietto_phase68_slice8_check import native_context_records

    record = context_record()
    native_context_records(record)
    if damage == "server":
        record["context"][14] = record["epoch"][6] = "foreign"
    elif damage == "account":
        record["context"][1] = record["epoch"][7] = record["role"] = "foreign@%"
    elif damage == "epoch":
        record["epoch"][1] += 1
    elif damage == "missing_context":
        record["events"] = record["events"][4:]
    elif damage == "missing_control":
        record["events"] = record["events"][:-4]
    elif damage == "missing_eof":
        record["events"][3]["value"]["eof"] = None
    elif damage == "session":
        record["events"][-1]["session"] = 99
    else:
        record["events"].pop(1)
    with pytest.raises(ValueError, match="S08_RECORD_"):
        native_context_records(record)


def test_owned_schema_replacement_restores_manager_database_before_setup(monkeypatch):
    from _pietto_phase68_slice8_probe import reset_fixture_database
    import _pietto_phase68_slice8_probe as probe

    calls = []
    monkeypatch.setattr(probe, "manager", lambda resource, sql: calls.append(sql))
    reset_fixture_database(object())
    assert calls[:3] == [
        "DROP DATABASE phase66",
        "CREATE DATABASE phase66 CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin",
        "USE phase66",
    ]
    assert calls[3].startswith("DROP USER IF EXISTS ")
