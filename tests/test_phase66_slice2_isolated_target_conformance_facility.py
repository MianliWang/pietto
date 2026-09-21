"""Offline fixture/observer/receipt controls; these tests never run a database."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import _pietto_target_conformance as facility
import _pietto_target_conformance_cases as cases
import _pietto_target_conformance_observation as observation
import _pietto_target_conformance_resources as resources
from _pietto_repository_facts import REPOSITORY_FACTS
from test_phase66_slice5_mysql_native_prepared_transport import native_data


class InjectedServerError(Exception):
    sqlstate = "22012"
    errno = None


class FakeCursor:
    def __init__(self, connection: Any, fault: str = ""):
        self.connection, self.fault = connection, fault
        self.description: Any = [("id", 20, None, 8, None, None, None)]
        self.remaining = [[(1,)]]
        self.fetches = 0
        self.calls: list[tuple[str, Any]] = []

    def execute(self, sql: str, parameters: Any = None) -> None:
        self.calls.append((sql, parameters))
        if sql == "BEGIN":
            self.connection.info.transaction_status = 2
            self.description = None
        elif sql == "SELECT 1/0":
            self.connection.info.transaction_status = 3
            raise InjectedServerError("division by zero")
        elif sql == "SELECT 2 AS v":
            self.remaining = [[(2,)]]
        if self.fault == "metadata":
            self.description = None
        if self.fault == "timeout":
            raise TimeoutError("injected deadline")

    def fetchmany(self, size: int) -> list[tuple[int]]:
        self.fetches += 1
        if self.fault == "late_fetch" and self.fetches == 2:
            raise RuntimeError("injected late fetch")
        return self.remaining.pop(0) if self.remaining else []

    def close(self) -> None:
        if self.fault in {"close", "primary_close"}:
            raise RuntimeError("injected close")


class FakeConnection:
    def __init__(self, fault: str = ""):
        self.fault = fault
        self.info = SimpleNamespace(backend_pid=41, transaction_status=0)
        self.last: FakeCursor | None = None

    def add_notice_handler(self, callback: Any) -> None:
        self.callback = callback

    def cursor(self, **kwargs: Any) -> FakeCursor:
        self.last = FakeCursor(self, self.fault)
        return self.last

    def rollback(self) -> None:
        if self.fault == "recovery":
            raise RuntimeError("injected rollback failure")
        self.info.transaction_status = 0

    def close(self) -> None:
        if self.fault == "connection_close":
            raise RuntimeError("injected connection close")


def test_observer_captures_exact_call_values_and_unavailable_nullability() -> None:
    connection = FakeConnection()
    view = observation.Observer("postgres", connection, "query")
    sql, params = cases.control("postgres", "C_parameters")
    result = view.capture(sql, params)
    cases.check_complete(result)
    assert connection.last is not None and connection.last.calls == [(sql, params)]
    assert result["parameters"] == [
        {"kind": "int", "value": "9007199254740993"},
        {"kind": "text", "value": cases.TEXT},
    ]
    assert result["metadata"][0][6] is None
    assert result["buffering"] == "client_complete"
    assert observation.scalar(True) != observation.scalar(1)
    assert observation.scalar(0.0) != observation.scalar(-0.0)
    with pytest.raises(observation.ObserverFailure, match="UNSUPPORTED_VALUE_TYPE"):
        observation.scalar(float("nan"))


@pytest.mark.parametrize(
    "fault,stage",
    [
        ("late_fetch", "fetch"),
        ("metadata", "fetch"),
        ("timeout", "execute"),
        ("close", "close"),
    ],
)
def test_injected_observer_failures_never_publish_complete_rows(
    fault: str, stage: str
) -> None:
    view = observation.Observer("postgres", FakeConnection(fault), "query")
    result = view.capture("SELECT id FROM phase66_rows")
    assert result["status"] == "failed"
    assert any(failure["stage"] == stage for failure in result["failures"])
    if fault == "late_fetch":
        assert result["rows"] == [[{"kind": "int", "value": "1"}]]
    with pytest.raises(ValueError, match="incomplete observation"):
        cases.check_complete(result)


def test_primary_and_close_failures_are_both_preserved() -> None:
    view = observation.Observer("postgres", FakeConnection("primary_close"), "query")
    result = view.capture("SELECT 1/0")
    assert [(error["stage"], error["kind"]) for error in result["failures"]] == [
        ("execute", "InjectedServerError"),
        ("close", "RuntimeError"),
    ]
    assert result["status"] == "failed"


def test_notice_objects_are_copied_and_loss_is_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    view = observation.Observer("postgres", connection, "manager")
    diagnostic = SimpleNamespace(
        severity_nonlocalized="NOTICE",
        sqlstate="42P07",
        message_primary="already exists",
    )
    connection.callback(diagnostic)
    diagnostic.message_primary = "expired storage"
    assert view.diagnostics()["details"][0]["message"] == "already exists"
    assert view.diagnostics()["total"] is None
    monkeypatch.setattr(observation, "MAX_DIAGNOSTICS", 0)
    connection.callback(diagnostic)
    assert view.diagnostics()["complete"] is False
    monkeypatch.setattr(
        view,
        "diagnostics",
        lambda: {
            "protocol": "postgres_notices",
            "total": None,
            "details": [],
            "complete": False,
        },
    )
    result = view.capture("SELECT 1 AS v")
    assert result["status"] == "failed"
    assert result["failures"][0]["kind"] == "DIAGNOSTICS_INCOMPLETE"


def test_mysql_diagnostic_total_details_and_close_failure_are_separate() -> None:
    class DiagnosticCursor:
        sql = ""
        calls: list[str] = []

        def execute(self, sql: str) -> None:
            self.sql = sql
            self.calls.append(sql)

        def fetchall(self) -> list[tuple[Any, ...]]:
            return (
                [(2,)]
                if self.sql == "SHOW COUNT(*) WARNINGS"
                else [("Warning", 1265, "truncated")]
            )

        def close(self) -> None:
            raise RuntimeError("injected diagnostic close")

    cursor = DiagnosticCursor()
    view = observation.Observer(
        "mysql", SimpleNamespace(cursor=lambda **kwargs: cursor), "manager"
    )
    result = view.diagnostics()
    assert cursor.calls == ["SHOW COUNT(*) WARNINGS", "SHOW WARNINGS"]
    assert result["total"] == 2 and len(result["details"]) == 1
    assert result["details"][0]["sqlstate"] is None
    assert result["complete"] is False
    assert view.diagnostic_failures[0]["stage"] == "diagnostics.close"


def test_injected_recovery_uses_one_session_and_retains_failed_prefix() -> None:
    connection = FakeConnection()
    view = observation.Observer("postgres", connection, "query")
    result: dict[str, Any] = {"id": "E_recovery", "observations": []}
    facility.execute_case("E_recovery", "postgres", view, view, {}, result)
    # Injected recovery behavior is not actual-driver identity evidence.
    with pytest.raises(ValueError, match="cursor route identity"):
        cases.check_case(result, "postgres")
    assert result["recovery"] == "success"
    assert result["session_before"] == result["session_after"] == 41
    assert [result["observations"][i]["rows"] for i in (0, 2)] == [
        [[{"kind": "int", "value": "1"}]],
        [[{"kind": "int", "value": "2"}]],
    ]
    assert result["session_before"] == result["session_after"] == 41
    assert (result["state_after_failure"], result["state_after_recovery"]) == (3, 0)
    connection.fault = "recovery"
    failed: dict[str, Any] = {"id": "E_recovery", "observations": []}
    with pytest.raises(RuntimeError, match="rollback"):
        facility.execute_case("E_recovery", "postgres", view, view, {}, failed)
    assert failed["recovery"] == "failed"
    assert failed["observations"][1]["failures"][0]["sqlstate"] == "22012"


class FakeResources(resources.Resources):
    fail_stop = False
    foreign = False

    def __init__(self, target: str, pin: dict[str, Any], directory: Path):
        super().__init__(target, pin, directory)
        self.container_id, self.network_id = "a" * 64, "b" * 64
        self.runtime_image_id = pin["platform_digest"]
        self.live = {"container": True, "network": True}
        self.commands: list[tuple[str, ...]] = []
        self.event("network_acquired", id=self.network_id)
        self.event("container_acquired", id=self.container_id)

    def inspect_resource(
        self, kind: str, reference: str, *, timeout: float = 30
    ) -> dict[str, Any]:
        return {
            "id": reference,
            "name": self.name if kind == "container" else self.network_name,
            "image": self.runtime_image_id,
            "labels": {
                "pietto.phase66.invocation": "foreign" if self.foreign else self.nonce
            },
        }

    def docker(
        self, *args: str, timeout: float = 30, extra_env: dict[str, str] | None = None
    ) -> str:
        self.commands.append(args)
        if args[:2] == ("container", "stop") and self.fail_stop:
            raise RuntimeError("injected stop failure")
        if args[1] == "rm":
            self.live[args[0]] = False
        if args[1] == "ls":
            return ""
        return "owned"

    def acquire(self) -> None:
        raise RuntimeError("injected setup failure after acquisition")


def test_owned_cleanup_retains_failures_and_never_deletes_foreign_resources(
    tmp_path: Path,
) -> None:
    pins, _ = facility.load_pins(facility.PINS)
    resource = FakeResources("postgres", pins["targets"]["postgres"], tmp_path)
    resource.fail_stop = True
    resource.manager = FakeConnection("connection_close")
    cleanup = resource.cleanup()
    assert cleanup["status"] == "failed" and cleanup["absent"] == {
        "container": True,
        "network": True,
    }
    assert {failure["stage"] for failure in cleanup["failures"]} == {
        "manager.close",
        "container.stop",
    }
    other = tmp_path / "other"
    other.mkdir()
    foreign = FakeResources("postgres", pins["targets"]["postgres"], other)
    foreign.foreign = True
    assert foreign.cleanup()["status"] == "failed"
    assert not any(command[1] in {"stop", "rm"} for command in foreign.commands)


def test_setup_failure_still_cleans_acquired_resources_and_writes_failure_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pins, pins_digest = facility.load_pins(facility.PINS)
    monkeypatch.setattr(facility, "Resources", FakeResources)
    monkeypatch.setattr(facility, "installed_generation", lambda *args: {})
    monkeypatch.setattr(facility, "driver_info", lambda *args: {})
    monkeypatch.setattr(
        facility,
        "sys",
        SimpleNamespace(
            implementation=SimpleNamespace(name="cpython"), version_info=(3, 13)
        ),
    )
    args = argparse.Namespace(
        target="postgres",
        evidence_dir=tmp_path / "run",
        case=None,
        expected_commit=None,
        run_id="injected",
        run_attempt=1,
    )
    assert facility.run_target(args, pins, pins_digest) == 1
    receipt, _ = facility.read_json(
        args.evidence_dir / "phase66-postgres-injected-1.json"
    )
    assert receipt["status"] == "failed" and receipt["cleanup"]["status"] == "success"
    assert receipt["failures"][0]["category"] == "INFRASTRUCTURE_FAILURE"
    assert receipt["cleanup"]["absent"] == {"container": True, "network": True}


def _observation(
    target: str,
    sql: str,
    rows: list[Any],
    names: list[str],
    types: list[int],
    params: list[Any] | None = None,
    *,
    identity: str = "query",
) -> dict[str, Any]:
    return {
        "sql": sql,
        "sql_sha256": facility.digest(sql.encode()),
        "parameters": params or [],
        "identity": identity,
        "prepared": target == "postgres" or bool(params),
        "buffering": "client_complete" if target == "postgres" else "unbuffered",
        "status": "success",
        "execute": "success",
        "fetch": "success" if names else "not_applicable",
        "close": "success",
        "metadata": [
            [name, kind, None, None, None, None, None]
            for name, kind in zip(names, types, strict=True)
        ]
        if names
        else None,
        "rows": rows,
        "diagnostics": {
            "protocol": "postgres_notices"
            if target == "postgres"
            else "mysql_warnings",
            "total": None if target == "postgres" else 0,
            "details": [],
            "complete": True,
        },
        "failures": [],
        "cursor_type": "psycopg.RawCursor"
        if target == "postgres"
        else "mysql.connector.cursor.MySQLCursorPrepared"
        if params
        else "mysql.connector.cursor.MySQLCursor",
        "api": "psycopg.RawCursor"
        if target == "postgres"
        else "mysql.connector.cursor.MySQLCursorPrepared"
        if params
        else "mysql.connector.cursor.MySQLCursor",
        "native": None,
    }


def _native_control_data(target):
    first = _observation(
        target, "SELECT 1 AS v", [[{"kind": "int", "value": "1"}]], ["v"], [23]
    )
    bad = _observation(
        target,
        "SELECT CAST($1 AS integer)"
        if target == "postgres"
        else "DO JSON_EXTRACT(?, '$')",
        [],
        [],
        [],
        [{"kind": "text", "value": "{"}],
    )
    bad.update(
        status="failed",
        execute="failed",
        fetch="not_started",
        failures=[
            {
                "stage": "execute",
                "kind": "ServerError",
                "sqlstate": "22P02" if target == "postgres" else "22032",
                "vendor_code": None if target == "postgres" else 3141,
            }
        ],
    )
    if target == "mysql":
        bad["diagnostics"].update(
            total=1,
            details=[
                {
                    "severity": "Error",
                    "vendor_code": 3141,
                    "sqlstate": None,
                    "message": "synthetic invalid JSON",
                }
            ],
        )
    second = _observation(
        target, "SELECT 2 AS v", [[{"kind": "int", "value": "2"}]], ["v"], [23]
    )
    warning = _observation(
        target,
        "CREATE TABLE IF NOT EXISTS phase66_rows (id BIGINT NOT NULL)"
        if target == "postgres"
        else "INSERT IGNORE INTO phase66_diagnostic_rows VALUES ('abcdef')",
        [],
        [],
        [],
        identity="fixture_manager",
    )
    warning["diagnostics"].update(
        total=None if target == "postgres" else 1,
        details=[
            {
                "severity": "NOTICE" if target == "postgres" else "Warning",
                "sqlstate": "42P07" if target == "postgres" else None,
                "vendor_code": None if target == "postgres" else 1265,
                "message": "synthetic warning",
            }
        ],
    )
    empty = _observation(
        target,
        "SELECT id FROM phase66_rows WHERE 1=0",
        [],
        ["id"],
        [20 if target == "postgres" else 8],
    )
    observations = [first, bad, second, warning, empty]
    if target == "mysql":
        native_data(warning, session=40)
        mismatch = _observation(target, "SELECT ? AS v", [], [], [])
        mismatch.update(
            status="failed",
            execute="not_started",
            fetch="not_started",
            failures=[{"stage": "parameter_count", "kind": "NATIVE_PARAMETER_COUNT"}],
        )
        observations.append(mismatch)
        late = _observation(
            target,
            "SELECT JSON_EXTRACT(?, '$')",
            [],
            ["JSON_EXTRACT(?, '$')"],
            [245],
            [{"kind": "text", "value": "{"}],
        )
        late.update(
            status="failed",
            execute="success",
            fetch="failed",
            failures=[
                {
                    "stage": "fetch",
                    "kind": "DataError",
                    "sqlstate": "22032",
                    "vendor_code": 3141,
                }
            ],
            diagnostics=deepcopy(bad["diagnostics"]),
        )
        observations.append(late)
        observations.append(
            _observation(
                target, "SELECT 3 AS v", [[{"kind": "int", "value": "3"}]], ["v"], [23]
            )
        )
    return {
        "id": "Q_native_lifecycle",
        "observations": observations,
        "session_before": 41,
        "session_after": 41,
        "recovery": "success",
    }


@pytest.fixture(scope="module")
def valid_receipts(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[dict[str, Any], str, dict[str, Any], dict[str, dict[str, Any]]]:
    pins, pins_digest = facility.load_pins(facility.PINS)
    expected = facility.inputs()
    result = {}
    for target in cases.TARGETS:
        legacy = {
            "schema_version": 1,
            "command": "emit-sql",
            "ok": True,
            "path": "legacy.pietto",
            "dialect": target,
            "diagnostics": [],
            "cli_errors": [],
            "artifacts": [
                {
                    "kind": "relation",
                    "name": "legacy_rows",
                    "sql": cases.legacy_sql(target),
                }
            ],
            "output": None,
        }
        stdout = json.dumps(legacy) + "\n"
        members = expected["package_members"]
        generation = {
            "exit_code": 0,
            "stdout": stdout,
            "stderr": "",
            "origins": {
                "pietto": {
                    "member": "pietto/__init__.py",
                    "sha256": members["pietto/__init__.py"],
                },
                "pietto.cli": {
                    "member": "pietto/cli.py",
                    "sha256": members["pietto/cli.py"],
                },
                "pietto.sql." + target: {
                    "member": "pietto/sql/" + target + ".py",
                    "sha256": members["pietto/sql/" + target + ".py"],
                },
            },
            "console_sha256": "c" * 64,
            "isolated": 1,
            "version": "0.1.0",
            "runtime_version": "4.13.2",
            "wheel_sha256": "d" * 64,
            "wheel_members": members,
            "source_sha256": facility.digest(cases.legacy_source(target).encode()),
            "stdout_sha256": facility.digest(stdout.encode()),
        }
        from pietto._project.project_sql_emission import serialize_project_sql_emission

        probe = facility.emission
        emission_records = []
        for item in probe.generation_inputs(target):
            _, outcome = probe.build_case(
                tmp_path_factory.mktemp("synthetic-emission"),
                item["source"],
                item["contract"],
                item["policy"],
            )
            public = serialize_project_sql_emission(outcome)
            emission_records.append(
                {
                    "id": item["id"],
                    "variant": item["variant"],
                    "source_sha256": facility.digest(
                        probe.source_bytes(item["source"])
                    ),
                    "contract_sha256": facility.digest(item["contract"].encode()),
                    "public": public.decode(),
                    "public_sha256": facility.digest(public),
                }
            )
        generation["emission"] = {
            "records": emission_records,
            "isolated": 1,
            "origins": {
                "pietto._project.project_sql_emission" + suffix: {
                    "member": "pietto/_project/project_sql_emission" + suffix + ".py",
                    "sha256": members[
                        "pietto/_project/project_sql_emission" + suffix + ".py"
                    ],
                }
                for suffix in (
                    "",
                    "_contract",
                    "_ast",
                    "_rendering",
                    "_verification",
                    "_scopes",
                    "_parameters",
                )
            },
            "probe_sha256": expected["harness"][
                facility.EMISSION_PROBE.relative_to(facility.ROOT).as_posix()
            ],
            "config_sha256": facility.digest(probe.CONFIG.encode()),
        }
        case_rows = []
        for case_id in cases.CASE_IDS[:3]:
            sql = (
                cases.legacy_sql(target)
                if case_id == "A_legacy"
                else cases.control(target, case_id)[0]
            )
            names = {
                "A_legacy": ["id"],
                "B_result": ["id", "note"],
                "C_parameters": ["a", "txt", "again"],
            }[case_id]
            types = {
                "postgres": {
                    "A_legacy": [20],
                    "B_result": [20, 1043],
                    "C_parameters": [20, 25, 20],
                },
                "mysql": {
                    "A_legacy": [8],
                    "B_result": [8, 253],
                    "C_parameters": [8, 253, 8],
                },
            }[target][case_id]
            params = (
                []
                if case_id != "C_parameters"
                else [
                    {"kind": "int", "value": "9007199254740993"},
                    {"kind": "text", "value": cases.TEXT},
                ]
                + (
                    [{"kind": "int", "value": "9007199254740993"}]
                    if target == "mysql"
                    else []
                )
            )
            case_rows.append(
                {
                    "id": case_id,
                    "observations": [
                        _observation(
                            target,
                            sql,
                            cases.expected_rows(case_id),
                            names,
                            types,
                            params,
                        )
                    ],
                }
            )
        d_sql = (
            "CREATE TABLE IF NOT EXISTS phase66_rows (id BIGINT NOT NULL)"
            if target == "postgres"
            else "INSERT IGNORE INTO phase66_diagnostic_rows VALUES ('abcdef')"
        )
        notice = _observation(target, d_sql, [], [], [], identity="fixture_manager")
        notice["diagnostics"]["details"] = (
            [{"severity": "NOTICE", "sqlstate": "42P07", "message": "already exists"}]
            if target == "postgres"
            else [
                {
                    "severity": "Warning",
                    "vendor_code": 1265,
                    "sqlstate": None,
                    "message": "truncated",
                }
            ]
        )
        if target == "mysql":
            notice["diagnostics"]["total"] = 1
        d = {
            "id": "D_diagnostics",
            "observations": [
                notice,
                _observation(
                    target,
                    "SELECT 1 AS v",
                    [[{"kind": "int", "value": "1"}]],
                    ["v"],
                    [23 if target == "postgres" else 3],
                ),
            ],
        }
        if target == "mysql":
            truncated = deepcopy(notice)
            truncated.update(
                status="failed",
                failures=[{"kind": "DIAGNOSTICS_INCOMPLETE", "stage": "diagnostics"}],
            )
            truncated["diagnostics"] = {
                "protocol": "mysql_warnings",
                "total": 1,
                "details": [],
                "complete": False,
            }
            d["observations"].append(truncated)
            d["settings"] = [
                _observation(target, sql, [], [], [], identity="fixture_manager")
                for sql in (
                    "SET SESSION max_error_count=0",
                    "SET SESSION max_error_count=64",
                )
            ]
        case_rows.append(d)
        for case_id in cases.SLICE2_CASE_IDS[4:]:
            privilege = case_id == "F_privilege_cleanup"
            bad_sql = (
                (
                    "CREATE TABLE public.phase66_denied (id BIGINT)"
                    if target == "postgres"
                    else "CREATE DATABASE phase66_denied"
                )
                if privilege
                else (
                    "SELECT 1/0"
                    if target == "postgres"
                    else "SELECT missing_column FROM phase66_rows"
                )
            )
            code = (
                ("42501" if privilege else "22012")
                if target == "postgres"
                else ("42000" if privilege else "42S22")
            )
            vendor = None if target == "postgres" else (1044 if privilege else 1054)
            bad = _observation(target, bad_sql, [], [], [])
            bad.update(
                status="failed",
                execute="failed",
                fetch="not_started",
                failures=[
                    {
                        "stage": "execute",
                        "kind": "ServerError",
                        "sqlstate": code,
                        "vendor_code": vendor,
                    }
                ],
            )
            if target == "mysql":
                bad["diagnostics"] = {
                    "protocol": "mysql_warnings",
                    "total": 1,
                    "details": [
                        {
                            "severity": "Error",
                            "vendor_code": vendor,
                            "message": "denied",
                            "sqlstate": None,
                        }
                    ],
                    "complete": True,
                }
            case: dict[str, Any] = {
                "id": case_id,
                "observations": [
                    _observation(
                        target,
                        "SELECT 1 AS v",
                        [[{"kind": "int", "value": "1"}]],
                        ["v"],
                        [23],
                    ),
                    bad,
                    _observation(
                        target,
                        "SELECT 2 AS v",
                        [[{"kind": "int", "value": "2"}]],
                        ["v"],
                        [23],
                    ),
                ],
                "recovery": "success",
                "session_before": 41,
                "session_after": 41,
            }
            if privilege:
                case["privileges_verified"] = True
                if target == "postgres":
                    flags = [
                        True,
                        False,
                        False,
                        True,
                        False,
                        True,
                        False,
                        False,
                        False,
                        False,
                        False,
                        False,
                        False,
                        False,
                    ]
                    case["privilege_observations"] = [
                        _observation(
                            target,
                            facility.PG_PRIVILEGES,
                            [
                                [
                                    {"kind": "text", "value": "pietto_query"},
                                    *(
                                        {"kind": "bool", "value": value}
                                        for value in flags
                                    ),
                                ]
                            ],
                            ["role", *("flag" + str(index) for index in range(14))],
                            [19, *([16] * 14)],
                        )
                    ]
                else:
                    case["privilege_observations"] = [
                        _observation(
                            target,
                            "SELECT CURRENT_USER(), CURRENT_ROLE()",
                            [
                                [
                                    {"kind": "text", "value": "pietto_query@%"},
                                    {"kind": "text", "value": "NONE"},
                                ]
                            ],
                            ["user", "role"],
                            [253, 253],
                        ),
                        _observation(
                            target,
                            "SHOW GRANTS FOR CURRENT_USER",
                            [
                                [
                                    {
                                        "kind": "text",
                                        "value": "GRANT USAGE ON *.* TO `pietto_query`@`%`",
                                    }
                                ],
                                [
                                    {
                                        "kind": "text",
                                        "value": "GRANT SELECT ON `phase66`.* TO `pietto_query`@`%`",
                                    }
                                ],
                            ],
                            ["grants"],
                            [253],
                        ),
                    ]
            else:
                case.update(
                    begin=_observation(target, "BEGIN", [], [], []),
                    state_after_failure=3 if target == "postgres" else True,
                    state_after_recovery=0 if target == "postgres" else False,
                )
            case_rows.append(case)
        values = (
            [
                "18.6 (Debian 18.6-1.pgdg12+2)",
                "180006",
                "PostgreSQL 18.6 (Debian 18.6-1.pgdg12+2)",
                "UTF8",
                "UTF8",
                "UTC",
                "10s",
                "pietto_manager",
                "63",
            ]
            if target == "postgres"
            else [
                "8.4.12",
                "MySQL Community Server - GPL",
                "x86_64",
                "Linux",
                "utf8mb4",
                "utf8mb4_0900_bin",
                resources.MYSQL_MODE,
                "10000",
                "root@%",
                "0",
            ]
        )
        env = {
            "query": _observation(
                target,
                facility.ENVIRONMENT_QUERIES[target],
                [
                    [
                        {
                            "kind": "int"
                            if target == "mysql" and index in {7, 9}
                            else "text",
                            "value": value,
                        }
                        for index, value in enumerate(values)
                    ]
                ],
                ["v" + str(index) for index in range(len(values))],
                [25] * len(values),
                identity="fixture_manager",
            ),
            "values": values,
            "image_config": pins["targets"][target]["config_digest"],
            "platform": "linux/amd64",
            "transport": {"mode": "loopback_plaintext"},
        }
        if target == "mysql":
            env["transport"] = {
                "mode": "owned_ca_tls",
                "ca": {
                    "container_id": "a" * 64,
                    "image_config": pins["targets"][target]["config_digest"],
                    "sha256": "e" * 64,
                },
                "verify_certificate": True,
                "verify_hostname": False,
                "allowed_versions": ["TLSv1.2", "TLSv1.3"],
                "certificate_policy": "ca_chain",
                "sessions": [
                    {
                        "identity": identity,
                        "session_id": session_id,
                        "observation": _observation(
                            target,
                            facility.MYSQL_TLS_QUERY,
                            [
                                [
                                    {"kind": "text", "value": "Ssl_cipher"},
                                    {"kind": "text", "value": "TLS_AES_256_GCM_SHA384"},
                                ],
                                [
                                    {"kind": "text", "value": "Ssl_version"},
                                    {"kind": "text", "value": "TLSv1.3"},
                                ],
                            ],
                            ["Variable_name", "Value"],
                            [253, 253],
                            identity=identity,
                        ),
                    }
                    for identity, session_id in (("fixture_manager", 40), ("query", 41))
                ],
            }
        cleanup = {
            "status": "success",
            "absent": {"container": True, "network": True},
            "failures": [],
            "elapsed_seconds": 1.0,
            "container_id": "a" * 64,
            "network_id": "b" * 64,
            "image_cache_retained": pins["targets"][target]["repository"]
            + "@"
            + pins["targets"][target]["platform_digest"],
        }
        events = [
            {
                "event": "image_verified",
                "reference": pins["targets"][target]["repository"]
                + "@"
                + pins["targets"][target]["platform_digest"],
                "contract": "descriptor",
                "runtime_image_id": pins["targets"][target]["platform_digest"],
                "descriptor_digest": pins["targets"][target]["platform_digest"],
                "os": "linux",
                "architecture": "amd64",
            },
            {"event": "network_acquired", "id": "b" * 64},
            {
                "event": "network_observed",
                "observation": {
                    "id": "b" * 64,
                    "driver": "bridge",
                    "internal": False,
                    "options": {"com.docker.network.bridge.gateway_mode_ipv4": "nat"},
                },
            },
            {"event": "container_acquired", "id": "a" * 64},
            {
                "event": "container_start_observed",
                "id": "a" * 64,
                "image": pins["targets"][target]["platform_digest"],
                "running": True,
                "ports": {
                    ("5432/tcp" if target == "postgres" else "3306/tcp"): [
                        {"HostIp": "127.0.0.1", "HostPort": "12345"}
                    ]
                },
            },
            {"event": "container_removed", "id": "a" * 64},
            {"event": "network_removed", "id": "b" * 64},
            {"event": "cleanup_complete", "result": cleanup},
        ]
        if target == "mysql":
            events.insert(
                3, {"event": "ca_extracted", "identity": env["transport"]["ca"]}
            )
        submissions = 20
        for case_id, variants in probe.VARIANTS.items():
            row = {"id": case_id, "observations": [], "variants": []}
            for record in [r for r in emission_records if r["id"] == case_id]:
                before = submissions
                document = probe.decode_public(record["public"].encode())
                if document["status"] == "VERIFIED":
                    named = case_id in {
                        "M_named_chain",
                        "N_imported_chain",
                        "O_named_later",
                    }
                    types = (
                        [25, 20, 16, 1700, 701]
                        if target == "postgres"
                        else [253, 8, 1, 246, 5]
                    )
                    if named:
                        types.append(20 if target == "postgres" else 8)
                    rows = (cases.chain_rows if named else cases.emission_rows)(
                        target, empty=record["variant"] == "empty"
                    )
                    if (case_id, record["variant"]) in cases.FILTERED_VARIANTS:
                        rows = cases.positive_id_rows(rows)
                    names: list[str] = [
                        str(label)
                        for label in (probe.CHAIN_LABELS if named else probe.LABELS)
                    ]
                    if case_id in {"T_row_direct", "U_row_named"}:
                        rows = cases.row_result_rows(
                            target, empty=record["variant"].startswith("empty")
                        )
                        names = [str(label) for label in probe.ROW_LABELS]
                        types = cases.row_result_metadata(target)
                    if record["variant"] == "truth_table":
                        rows = cases.truth_rows(target)
                        names = [str(label) for label in probe.TRUTH_LABELS]
                        types = [16 if target == "postgres" else 8] * len(names)
                    if case_id in {
                        "W_join_shapes",
                        "W_join_values",
                        "V_join_full",
                    }:
                        rows = cases.join_rows(record["variant"])
                        names = [
                            str(label) for label in probe.JOIN_LABELS[record["variant"]]
                        ]
                        types = cases.join_metadata(target, record["variant"])
                    elif case_id in probe.WINDOW_CASES:
                        key = cases.window_key(case_id, record["variant"])
                        rows = cases.WINDOW_EXPECTATIONS[key]
                        names = [str(label) for label in cases.WINDOW_LABELS[key]]
                        types = cases.window_metadata(target, key)
                    elif case_id in probe.AGGREGATE_CASES:
                        rows = cases.aggregate_rows(target, case_id, record["variant"])
                        names = [
                            str(label)
                            for label in probe.aggregate_labels(
                                probe.AGGREGATE_LABELS, case_id, record["variant"]
                            )
                        ]
                        types = cases.aggregate_types(
                            target, case_id, record["variant"]
                        )
                    elif (case_id, record["variant"]) in cases.MIGRATED_JOIN_ROWS:
                        rows = cases.MIGRATED_JOIN_ROWS[case_id, record["variant"]]
                        names = [
                            str(label)
                            for label in cases.MIGRATED_JOIN_LABELS[
                                case_id, record["variant"]
                            ]
                        ]
                        types = [20 if target == "postgres" else 8] * len(names)
                    observation = _observation(
                        target,
                        document["sql"],
                        rows,
                        names,
                        types,
                        cases.parameter_records(document),
                    )
                    observation["prepared"] = True
                    observation["cursor_type"] = (
                        "psycopg.RawCursor"
                        if target == "postgres"
                        else "mysql.connector.cursor.MySQLCursorPrepared"
                    )
                    if case_id == "P_native_identifiers":
                        number = "7" if record["variant"].startswith("plain") else "11"
                        observation = _observation(
                            target,
                            document["sql"],
                            []
                            if record["variant"].startswith("empty")
                            else [[{"kind": "int", "value": number}]] * 2,
                            ["id"],
                            [20 if target == "postgres" else 8],
                        )
                        observation["prepared"] = True
                    elif case_id in {"R_fixed_direct", "S_fixed_named"}:
                        is_named = case_id == "S_fixed_named"
                        labels = (
                            probe.FIXED_NAMED_LABELS if is_named else probe.FIXED_LABELS
                        )
                        tags = probe.FIXED_NAMED_TAGS if is_named else probe.FIXED_TAGS
                        observation = _observation(
                            target,
                            document["sql"],
                            cases.fixed_rows(
                                target,
                                named=is_named,
                                empty=record["variant"].startswith("empty"),
                            ),
                            list(labels),
                            cases.fixed_metadata(target, named=is_named),
                            cases.parameter_records(document),
                        )
                        observation["prepared"] = True
                        if target == "mysql":
                            for metadata, tag in zip(
                                observation["metadata"], tags, strict=True
                            ):
                                metadata.extend((0, 309 if tag == "Text" else 63))
                    if target == "postgres":
                        observation["api"] = observation["cursor_type"]
                    row["observations"].append(observation)
                    submissions += 1
                row["variants"].append(
                    {
                        "variant": record["variant"],
                        "public": record["public"],
                        "public_sha256": record["public_sha256"],
                        "submission_before": before,
                        "submission_after": submissions,
                    }
                )
            case_rows.append(row)
        case_rows.append(_native_control_data(target))
        case_rows.sort(key=lambda case: cases.CASE_IDS.index(case["id"]))
        events[4:4] = [
            {"event": "connection_closed", "identity": "query", "session_id": 41},
            {"event": "connection_closed", "identity": "manager", "session_id": 40},
        ]
        result[target] = {
            "format": facility.FORMAT,
            "target": target,
            "commit": "1" * 40,
            "run_id": "synthetic",
            "run_attempt": 1,
            "inputs": expected,
            "pins_sha256": pins_digest,
            "pin": pins["targets"][target],
            "case_ids": list(cases.CASE_IDS),
            "full_manifest": True,
            "status": "success",
            "drivers": {
                "versions": pins["drivers"],
                "postgres_implementation": "binary",
                "mysql_implementation": "pure",
                "libpq_version": 180006,
                "libpq_build_version": 180006,
                "python": "3.13.13",
            },
            "generation": generation,
            "environment": env,
            "setup": [
                _observation(target, sql, [], [], [], identity="fixture_manager")
                for sql in [
                    *(sql for sql, _ in cases.setup(target)),
                    *(
                        [
                            "CREDENTIAL_MANAGEMENT",
                            "REVOKE ALL ON DATABASE phase66 FROM PUBLIC",
                            "GRANT CONNECT ON DATABASE phase66 TO pietto_query",
                            "REVOKE CREATE ON SCHEMA public FROM PUBLIC",
                            "GRANT USAGE ON SCHEMA public TO pietto_query",
                            "GRANT SELECT ON ALL TABLES IN SCHEMA public TO pietto_query",
                        ]
                        if target == "postgres"
                        else [
                            "CREDENTIAL_MANAGEMENT",
                            "GRANT SELECT ON phase66.* TO 'pietto_query'@'%'",
                        ]
                    ),
                ]
            ],
            "cases": case_rows,
            "resources": events,
            "cleanup": cleanup,
            "failures": [],
        }
        for index, params in (
            (
                3,
                [
                    {"kind": "int", "value": "1"},
                    {"kind": "int", "value": "7"},
                    {"kind": "null"},
                ],
            ),
            (
                4,
                [
                    {"kind": "int", "value": "2"},
                    {"kind": "int", "value": "7"},
                    {"kind": "null"},
                ],
            ),
            (
                5,
                [
                    {"kind": "int", "value": "3"},
                    {"kind": "int", "value": "9007199254740993"},
                    {"kind": "text", "value": cases.TEXT},
                ],
            ),
        ):
            result[target]["setup"][index]["parameters"] = params
            result[target]["setup"][index]["prepared"] = True
        loading = [
            *cases.emission_setup_parameters(target),
            *cases.aggregate_setup_parameters(target),
        ]
        for index, params in enumerate(loading, 7):
            result[target]["setup"][index]["parameters"] = params
            result[target]["setup"][index]["prepared"] = target == "postgres" or bool(
                params
            )
        if target == "mysql":

            def migrate(value, *, transaction_control=False):
                if type(value) is list:
                    for child in value:
                        migrate(child)
                elif type(value) is dict:
                    if "sql_sha256" in value:
                        if value["identity"] == "query" and not transaction_control:
                            # Only the missing column is resolved at prepare;
                            # the denied CREATE DATABASE still fails at execute.
                            if any(
                                f.get("vendor_code") == 1054 for f in value["failures"]
                            ):
                                value["execute"] = "not_started"
                                value["failures"][0]["stage"] = "prepare"
                            native_data(value, session=41)
                        elif value["native"] is None and value["prepared"]:
                            value["api"] = value["cursor_type"] = (
                                "mysql.connector.cursor.MySQLCursorPrepared"
                            )
                        return
                    for key, child in value.items():
                        migrate(child, transaction_control=key == "begin")

            migrate(result[target])
    return pins, pins_digest, expected, result


@pytest.mark.parametrize("target", cases.TARGETS)
def test_data_only_receipt_controls_have_nonempty_positive_denominators(
    valid_receipts: Any, target: str
) -> None:
    pins, pins_digest, expected, receipts = valid_receipts
    facility.verify_receipt(
        receipts[target], target, pins, pins_digest, expected, "1" * 40, "synthetic", 1
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "empty",
        "missing",
        "duplicate",
        "stale",
        "pins",
        "build",
        "sql",
        "parameters",
        "fixture_parameters",
        "begin",
        "identity",
        "metadata",
        "origin",
        "cleanup",
        "cleanup_journal",
        "network",
        "ports",
        "recovery",
        "privileges",
        "extra",
        "image_contract",
        "image_binding",
    ],
)
@pytest.mark.parametrize("target", cases.TARGETS)
def test_receipt_corruption_is_rejected_without_any_resource(
    valid_receipts: Any, target: str, mutation: str
) -> None:
    pins, pins_digest, expected, receipts = valid_receipts
    receipt = deepcopy(receipts[target])
    if mutation == "empty":
        receipt["case_ids"] = []
    elif mutation == "missing":
        receipt["cases"].pop()
    elif mutation == "duplicate":
        receipt["cases"][1] = deepcopy(receipt["cases"][0])
    elif mutation == "stale":
        receipt["commit"] = "2" * 40
    elif mutation == "pins":
        receipt["pin"]["platform_digest"] = "sha256:" + "0" * 64
    elif mutation == "build":
        receipt["environment"]["values"][0] = "unreviewed"
    elif mutation == "sql":
        receipt["cases"][2]["observations"][0]["sql"] += " -- substituted"
    elif mutation == "parameters":
        receipt["cases"][2]["observations"][0]["parameters"][0] = {
            "kind": "float",
            "value": "0x1p53",
        }
    elif mutation == "fixture_parameters":
        receipt["setup"][5]["parameters"][1]["value"] = "9007199254740992"
    elif mutation == "begin":
        del receipt["cases"][4]["begin"]
    elif mutation == "identity":
        receipt["cases"][0]["observations"][0]["identity"] = "fixture_manager"
    elif mutation == "metadata":
        receipt["cases"][1]["observations"][0]["metadata"] = None
    elif mutation == "origin":
        receipt["generation"]["origins"]["pietto.cli"]["member"] = (
            "checkout/src/pietto/cli.py"
        )
    elif mutation == "cleanup":
        receipt["cleanup"]["status"] = "unknown"
    elif mutation == "image_contract":
        # Renaming the contract without its own exposed digest is not evidence.
        image = next(
            event
            for event in receipt["resources"]
            if event["event"] == "image_verified"
        )
        image["contract"] = "classic"
        image["descriptor_digest"] = None
    elif mutation == "image_binding":
        started = next(
            event
            for event in receipt["resources"]
            if event["event"] == "container_start_observed"
        )
        started["image"] = pins["targets"][target]["config_digest"]
    elif mutation == "cleanup_journal":
        receipt["resources"] = []
    elif mutation == "network":
        next(
            event
            for event in receipt["resources"]
            if event["event"] == "network_observed"
        )["observation"]["internal"] = True
    elif mutation == "ports":
        next(
            event
            for event in receipt["resources"]
            if event["event"] == "container_start_observed"
        )["ports"] = {}
    elif mutation == "recovery":
        receipt["cases"][4]["session_after"] = 42
    elif mutation == "privileges":
        receipt["cases"][5]["privilege_observations"][0]["rows"] = []
    else:
        receipt["unexpected"] = True
    with pytest.raises(ValueError, match="invalid target receipt"):
        facility.verify_receipt(
            receipt, target, pins, pins_digest, expected, "1" * 40, "synthetic", 1
        )


@pytest.mark.parametrize("status", ["failure", "cancelled", "skipped", "", None])
@pytest.mark.parametrize("job", ["compiler_status", "target_status"])
def test_aggregate_rejects_unsuccessful_required_jobs(
    tmp_path: Path, status: Any, job: str
) -> None:
    pins, pins_digest = facility.load_pins(facility.PINS)
    args = argparse.Namespace(
        target=None,
        compiler_status="success",
        target_status="success",
        evidence_dir=tmp_path,
    )
    setattr(args, job, status)
    with pytest.raises(ValueError, match="required job"):
        facility.verify_directory(args, pins, pins_digest)


def test_pins_and_raw_receipts_are_strict_data(tmp_path: Path) -> None:
    pins, _ = facility.load_pins(facility.PINS)
    assert set(pins["targets"]) == {"postgres", "mysql"}
    other = tmp_path / "pins.json"
    other.write_bytes(facility.PINS.read_bytes())
    with pytest.raises(ValueError, match="checked-in"):
        facility.load_pins(other)
    other.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError, match="duplicate"):
        facility.read_json(other)
    other.write_text('{"number":NaN}')
    with pytest.raises(ValueError, match="invalid JSON"):
        facility.read_json(other)


def test_receipt_reader_rejects_replacement_at_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "receipt.json"
    path.write_text('{"old":1}')
    replacement = tmp_path / "replacement.json"
    replacement.write_text('{"new":2}')
    original = facility.os.open

    def replace_before_open(name: Any, flags: int) -> int:
        replacement.replace(path)
        return original(name, flags)

    monkeypatch.setattr(facility.os, "open", replace_before_open)
    with pytest.raises(ValueError, match="replaced"):
        facility.read_json(path)


def test_aggregate_cli_requires_observed_prerequisites(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        facility.main(
            [
                "verify-receipts",
                "--pins",
                str(facility.PINS),
                "--evidence-dir",
                str(tmp_path),
                "--expected-commit",
                "1" * 40,
                "--run-id",
                "synthetic",
                "--run-attempt",
                "1",
            ]
        )
        == 1
    )
    assert "required job" in capsys.readouterr().err


@pytest.mark.parametrize(
    "corruption", ["cipher", "version", "ca", "session", "settings"]
)
def test_mysql_transport_and_diagnostic_control_corruption_rejected(
    valid_receipts: Any, corruption: str
) -> None:
    pins, pins_digest, expected, receipts = valid_receipts
    receipt = deepcopy(receipts["mysql"])
    transport = receipt["environment"]["transport"]
    if corruption in {"cipher", "version"}:
        transport["sessions"][1]["observation"]["rows"][int(corruption == "version")][
            1
        ]["value"] = ""
    elif corruption == "ca":
        transport["ca"]["container_id"] = "f" * 64
    elif corruption == "session":
        transport["sessions"][1]["session_id"] = 42
    else:
        receipt["cases"][3]["settings"] = []
    with pytest.raises(ValueError, match="invalid target receipt"):
        facility.verify_receipt(
            receipt, "mysql", pins, pins_digest, expected, "1" * 40, "synthetic", 1
        )


def test_directory_and_native_upload_boundary(
    valid_receipts: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pins, pins_digest, expected, receipts = valid_receipts
    monkeypatch.setattr(facility, "inputs", lambda: expected)
    args = argparse.Namespace(
        target=None,
        compiler_status="success",
        target_status="success",
        evidence_dir=tmp_path,
        expected_commit="1" * 40,
        run_id="synthetic",
        run_attempt=1,
    )
    for target, receipt in receipts.items():
        (tmp_path / f"phase66-{target}-synthetic-1.json").write_bytes(
            facility.canonical(receipt)
        )
    facility.verify_directory(args, pins, pins_digest)
    mysql = tmp_path / "phase66-mysql-synthetic-1.json"
    duplicate = tmp_path / "duplicate"
    duplicate.mkdir()
    extra = duplicate / mysql.name
    extra.write_bytes(mysql.read_bytes())
    with pytest.raises(ValueError, match="duplicated"):
        facility.verify_directory(args, pins, pins_digest)
    extra.unlink()
    mysql.unlink()
    with pytest.raises(ValueError, match="missing"):
        facility.verify_directory(args, pins, pins_digest)
    args.target = "postgres"
    args.compiler_status = args.target_status = None
    args.artifact_id = "123"
    args.artifact_digest = facility.digest(
        (tmp_path / "phase66-postgres-synthetic-1.json").read_bytes()
    )
    facility.verify_directory(args, pins, pins_digest)
    args.artifact_digest = "0" * 64
    with pytest.raises(ValueError, match="digest mismatch"):
        facility.verify_directory(args, pins, pins_digest)


def test_helpers_stay_test_only_and_do_not_extend_product_or_history() -> None:
    for path in facility.HELPERS:
        facts = REPOSITORY_FACTS.python(path)
        assert not any(
            module.startswith("pietto._project") for module in facts.imported_modules
        )
    assert cases.SLICE2_CASE_IDS == (
        "A_legacy",
        "B_result",
        "C_parameters",
        "D_diagnostics",
        "E_recovery",
        "F_privilege_cleanup",
    )
    assert cases.CASE_IDS == (
        *cases.SLICE2_CASE_IDS,
        "A_window_distribution",
        "A_window_frame",
        "A_window_groups",
        "A_window_named",
        "A_window_navigation",
        "A_window_qualify",
        "A_window_ranking",
        "G_emission_table_bag",
        "H_emission_query_bag",
        "I_emission_table_empty",
        "J_emission_query_empty",
        "K_emission_rejected",
        "L_emission_blocked",
        "M_named_chain",
        "N_imported_chain",
        "O_named_later",
        "P_native_identifiers",
        "Q_native_lifecycle",
        "R_fixed_direct",
        "S_fixed_named",
        "T_row_direct",
        "U_row_named",
        "V_aggregate_blocked",
        "V_join_full",
        "V_row_blocked",
        "V_window_blocked",
        "W_join_shapes",
        "W_join_values",
        "X_aggregate_global",
        "X_aggregate_grouped",
        "Y_aggregate_constant",
        "Y_aggregate_domains",
        "Y_aggregate_satisfying",
        "Z_aggregate_composition",
        "Z_aggregate_joined",
        "Z_aggregate_membership",
        "Z_aggregate_transport",
    )
    assert resources.ENDPOINT == "unix:///var/run/docker.sock"
    assert resources.STARTUP_SECONDS == 120 and resources.MAX_CONNECT_ATTEMPTS == 3
    assert len(resources.CONNECT_CHECKPOINTS) == 2
    assert (
        resources.QUERY_SECONDS,
        resources.READ_SECONDS,
        resources.CLEANUP_SECONDS,
    ) == (10, 20, 30)


def test_ci_uses_strict_raw_same_run_receipt_transport() -> None:
    workflow = (facility.ROOT / ".github/workflows/ci.yml").read_text()
    assert workflow.count("digest-mismatch: error") == 2
    assert workflow.count("archive: false") == 1
    assert (
        "path: ${{ runner.temp }}/phase66-target/${{ matrix.target }}/phase66-${{ matrix.target }}-${{ github.run_id }}-${{ github.run_attempt }}.json"
        in workflow
    )
    assert (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
    )
    assert (
        "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c" in workflow
    )
    assert "    outputs:" not in workflow
    for target in cases.TARGETS:
        assert (
            f"name: phase66-{target}-${{{{ github.run_id }}}}-${{{{ github.run_attempt }}}}.json"
            in workflow
        )
    assert (
        '--compiler-status "$COMPILER_STATUS" --target-status "$TARGET_STATUS"'
        in workflow
    )
    assert (
        '--artifact-digest "$ARTIFACT_DIGEST" --artifact-id "$ARTIFACT_ID"' in workflow
    )


def test_test_dependency_group_preserves_runtime_metadata() -> None:
    import tomllib

    project = tomllib.loads((facility.ROOT / "pyproject.toml").read_text())
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert project["dependency-groups"]["target-conformance"] == [
        "psycopg[binary]==3.3.5",
        "mysql-connector-python==26.7.0",
    ]
    assert (
        project["dependency-groups"]["dev"].count(
            {"include-group": "target-conformance"}
        )
        == 1
    )


def test_database_environment_is_not_ambient(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "PGHOST",
        "PGSERVICE",
        "PGPASSFILE",
        "PGOPTIONS",
        "DATABASE_URL",
        "MYSQL_PWD",
        "MYSQL_HOME",
        "DOCKER_CONTEXT",
        "DOCKER_HOST",
        "SSLKEYLOGFILE",
    ):
        monkeypatch.setenv(key, "unrelated")
    environment = resources.clean_environment()
    assert not any(key.startswith("PG") for key in environment)
    assert (
        not {"DATABASE_URL", "MYSQL_PWD", "MYSQL_HOME", "DOCKER_CONTEXT", "DOCKER_HOST"}
        & environment.keys()
    )
    assert environment["PSYCOPG_IMPL"] == "binary"
    assert "SSLKEYLOGFILE" not in environment


@pytest.mark.parametrize(
    "bad",
    [
        None,
        [],
        [{"HostIp": "0.0.0.0", "HostPort": "12345"}],
        [{"HostIp": "127.0.0.1", "HostPort": ""}],
        [{"HostIp": "127.0.0.1", "HostPort": "65536"}],
        [{"HostIp": "127.0.0.1", "HostPort": "12345"}] * 2,
    ],
)
def test_actual_port_binding_is_required_and_exclusive(bad: Any) -> None:
    good = {"HostIp": "127.0.0.1", "HostPort": "12345"}
    assert (
        resources.loopback_port({"3306/tcp": [good], "33060/tcp": None}, "3306")
        == 12345
    )
    with pytest.raises(ValueError, match="port binding"):
        resources.loopback_port({"3306/tcp": bad}, "3306")
    with pytest.raises(ValueError, match="port binding"):
        resources.loopback_port({"3306/tcp": [good], "33060/tcp": [good]}, "3306")


def test_mysql_connection_keeps_ca_verification_and_explicit_modern_tls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import mysql.connector
    import time

    arguments: dict[str, Any] = {}
    sentinel = mysql.connector.MySQLConnection()

    def connect(**kwargs: Any) -> object:
        arguments.update(kwargs)
        return sentinel

    monkeypatch.setattr(mysql.connector, "connect", connect)
    pins, _ = facility.load_pins(facility.PINS)
    resource = resources.Resources("mysql", pins["targets"]["mysql"], tmp_path)
    resource.startup_started = time.monotonic()
    monkeypatch.setenv("SSLKEYLOGFILE", str(tmp_path / "unrelated-keys"))
    assert resource.connect(query=False) is sentinel
    assert arguments["ssl_ca"] == str(resource.ca_path)
    assert arguments["ssl_verify_cert"] is True
    assert arguments["ssl_verify_identity"] is False
    assert arguments["tls_versions"] == ["TLSv1.2", "TLSv1.3"]
    assert arguments["use_pure"] is True
    assert "SSLKEYLOGFILE" not in resources.os.environ
    message = "native SSL failure " + resource._passwords[0]
    resource.event(
        "connect_failed", failure={"message": resource.without_secrets(message)}
    )
    assert resource.events[-1]["failure"]["message"] == "native SSL failure [REDACTED]"


@pytest.mark.parametrize(
    "mutation",
    (
        "emission_origin",
        "source_hash",
        "contract_hash",
        "probe_hash",
        "public_sha",
        "public_sql",
        "public_range",
        "case_record_swap",
        "negative_submission",
        "missing_new_case",
        "missing_variant",
        "wrong_rejection_path",
    ),
)
@pytest.mark.parametrize("target", cases.TARGETS)
def test_new_installed_public_chain_corruptions_are_rejected(
    valid_receipts, mutation, target
):
    pins, pins_digest, expected, receipts = valid_receipts
    receipt = deepcopy(receipts[target])
    emission = receipt["generation"]["emission"]
    record = emission["records"][0]
    if mutation == "emission_origin":
        emission["origins"]["pietto._project.project_sql_emission"]["member"] = (
            "checkout/project_sql_emission.py"
        )
    elif mutation == "source_hash":
        record["source_sha256"] = "0" * 64
    elif mutation == "contract_hash":
        record["contract_sha256"] = "0" * 64
    elif mutation == "probe_hash":
        emission["probe_sha256"] = "0" * 64
    elif mutation == "public_sha":
        record["public_sha256"] = "0" * 64
    elif mutation in {"public_sql", "public_range", "wrong_rejection_path"}:
        if mutation == "wrong_rejection_path":
            record = next(
                r for r in emission["records"] if r["id"] == "K_emission_rejected"
            )
        document = json.loads(record["public"])
        if mutation == "public_sql":
            document["sql"] = document["sql"].replace("SELECT", "DELETE", 1)
        elif mutation == "public_range":
            document["ranges"][-1]["end"] -= 1
        else:
            document["cli_errors"][0]["path"] = "different/selector"
        record["public"] = facility.emission.encoded(document).decode()
        record["public_sha256"] = facility.digest(record["public"].encode())
        for case in receipt["cases"]:
            if case["id"] == record["id"]:
                for variant in case["variants"]:
                    if variant["variant"] == record["variant"]:
                        variant["public"], variant["public_sha256"] = (
                            record["public"],
                            record["public_sha256"],
                        )
    elif mutation == "case_record_swap":
        receipt["cases"][6]["variants"][0]["public"] = emission["records"][1]["public"]
        receipt["cases"][6]["variants"][0]["public_sha256"] = emission["records"][1][
            "public_sha256"
        ]
    elif mutation == "negative_submission":
        receipt["cases"][10]["variants"][0]["submission_after"] += 1
    elif mutation == "missing_new_case":
        receipt["cases"].pop()
    elif mutation == "missing_variant":
        emission["records"].pop()
    with pytest.raises(ValueError):
        facility.verify_receipt(
            receipt, target, pins, pins_digest, expected, "1" * 40, "synthetic", 1
        )


def server_error_observation(*, privilege: bool, native: bool = True) -> dict[str, Any]:
    """Data-only: the exact layers observed against the pinned MySQL 8.4.12."""
    from _pietto_mysql_native_prepared import API

    at_prepare = native and not privilege
    return {
        "api": API if native else "mysql.connector.cursor.MySQLCursorPrepared",
        "status": "failed",
        "execute": "not_started" if at_prepare else "failed",
        "close": "success",
        "diagnostics": {
            "protocol": "mysql_warnings",
            "total": 1,
            "details": [
                {"severity": "Error", "vendor_code": 1044 if privilege else 1054}
            ],
            "complete": True,
        },
        "failures": [
            {
                "stage": "prepare" if at_prepare else "execute",
                "sqlstate": "42000" if privilege else "42S22",
                "vendor_code": 1044 if privilege else 1054,
            }
        ],
    }


def test_native_server_errors_keep_their_own_reported_layer() -> None:
    # MySQL resolves a missing column while preparing, but checks the CREATE
    # DATABASE privilege only at execution; one uniform layer would be wrong.
    cases.check_server_error(server_error_observation(privilege=False), "mysql")
    cases.check_server_error(
        server_error_observation(privilege=True), "mysql", privilege=True
    )
    swapped = server_error_observation(privilege=True)
    swapped["execute"] = "not_started"
    swapped["failures"][0]["stage"] = "prepare"
    with pytest.raises(ValueError, match="wrong failure layer"):
        cases.check_server_error(swapped, "mysql", privilege=True)
    moved = server_error_observation(privilege=False)
    moved["execute"] = "failed"
    moved["failures"][0]["stage"] = "execute"
    with pytest.raises(ValueError, match="wrong failure layer"):
        cases.check_server_error(moved, "mysql")
    # An ordinary cursor has no prepare step, and PostgreSQL never goes native.
    cases.check_server_error(
        server_error_observation(privilege=False, native=False), "mysql"
    )
    postgres = server_error_observation(privilege=False, native=False)
    postgres["api"] = "psycopg.RawCursor"
    postgres["failures"][0]["sqlstate"] = "22012"
    with pytest.raises(ValueError, match="wrong failure layer"):
        cases.check_server_error(dict(postgres, execute="not_started"), "postgres")
    cases.check_server_error(postgres, "postgres")


# The exact result column this pinned MySQL 8.4.12 reported for empty_text in
# every R_fixed_direct variant, PRESERVE and BIND alike, recorded in
# claude-mysql-focused-6. Written out here so the observed side of these
# regressions never comes from the oracle under test.
OBSERVED_EMPTY_TEXT = ["empty_text", 253, None, None, None, None, 1, 128, 309]
EMPTY_TEXT = cases.emission.FIXED_LABELS.index("empty_text")


def fixed_case(receipt: dict[str, Any], case_id: str = "R_fixed_direct") -> Any:
    return next(case for case in receipt["cases"] if case["id"] == case_id)


def substitute_result_column(record: Any, position: int, column: list[Any]) -> int:
    """Replace one result column everywhere this observation records it."""
    replaced = 0

    def walk(node: Any) -> None:
        nonlocal replaced
        if type(node) is list:
            if (
                len(node) > position
                and type(node[position]) is list
                and node[position][:1] == column[:1]
            ):
                node[position] = list(column)
                replaced += 1
                return
            for child in node:
                walk(child)
        elif type(node) is dict:
            for child in node.values():
                walk(child)

    walk(record)
    if not replaced:
        raise AssertionError("no recorded result column matched")
    return replaced


def replace_everywhere(record: Any, column: list[Any], replacement: list[Any]) -> int:
    """Replace one recorded result column by value, wherever the receipt holds it."""
    replaced = 0

    def walk(node: Any) -> None:
        nonlocal replaced
        if type(node) is list:
            for index, child in enumerate(node):
                if child == column:
                    node[index] = list(replacement)
                    replaced += 1
                else:
                    walk(child)
        elif type(node) is dict:
            for child in node.values():
                walk(child)

    walk(record)
    if not replaced:
        raise AssertionError("no recorded result column matched")
    return replaced


def observed_mysql_receipt(receipts: Any, case_id: str = "R_fixed_direct") -> Any:
    receipt = deepcopy(receipts["mysql"])
    for record in fixed_case(receipt, case_id)["observations"]:
        substitute_result_column(record, EMPTY_TEXT, OBSERVED_EMPTY_TEXT)
    return receipt


def accept_receipt(receipt: Any, valid: Any, target: str = "mysql") -> None:
    pins, pins_digest, expected, _ = valid
    facility.verify_receipt(
        receipt, target, pins, pins_digest, expected, "1" * 40, "synthetic", 1
    )


def reject_receipt(receipt: Any, valid: Any, target: str = "mysql") -> None:
    with pytest.raises(ValueError, match="invalid target receipt"):
        accept_receipt(receipt, valid, target)


def test_empty_text_anchor_requires_the_observed_var_string_type(
    valid_receipts: Any,
) -> None:
    accept_receipt(observed_mysql_receipt(valid_receipts[3]), valid_receipts)
    # The oracle states 253 explicitly; it is not optional and not a set.
    assert cases.fixed_metadata("mysql", named=False)[EMPTY_TEXT] == 253
    assert cases.fixed_metadata("postgres", named=False)[EMPTY_TEXT] == 25
    variants = [
        v["variant"] for v in fixed_case(valid_receipts[3]["mysql"])["variants"]
    ]
    preserve = [i for i, v in enumerate(variants) if not v.endswith("bind")]
    bind = [i for i, v in enumerate(variants) if v.endswith("bind")]
    assert len(preserve) == 3 and len(bind) == 3
    for code in (254, 252, 15, 8):
        for selected in (preserve, bind, range(len(variants))):
            receipt = observed_mysql_receipt(valid_receipts[3])
            observations = fixed_case(receipt)["observations"]
            for index in selected:
                substitute_result_column(
                    observations[index],
                    EMPTY_TEXT,
                    [OBSERVED_EMPTY_TEXT[0], code, *OBSERVED_EMPTY_TEXT[2:]],
                )
            reject_receipt(receipt, valid_receipts)


@pytest.mark.parametrize(
    "change",
    (
        "other_column_type",
        "label",
        "collation",
        "arity",
        "position_swap",
        "value_kind",
        "null_value",
        "multiplicity",
        "parameters",
        "empty_result_metadata",
        "named_case_type",
    ),
)
def test_fixed_value_receipt_keeps_every_other_expectation(
    valid_receipts: Any, change: str
) -> None:
    receipt = observed_mysql_receipt(valid_receipts[3])
    case = fixed_case(receipt)
    first = case["observations"][0]
    if change == "other_column_type":
        substitute_result_column(
            first, 16, ["trailing_text", 254, None, None, None, None, 1, 128, 309]
        )
    elif change == "label":
        replace_everywhere(
            first, OBSERVED_EMPTY_TEXT, ["renamed", *OBSERVED_EMPTY_TEXT[1:]]
        )
    elif change == "collation":
        replace_everywhere(first, OBSERVED_EMPTY_TEXT, [*OBSERVED_EMPTY_TEXT[:8], 255])
    elif change == "arity":
        first["metadata"].pop()
    elif change == "position_swap":
        # Move the Text anchor onto the leading Int column's position.
        other = list(first["metadata"][0])
        sentinel = ["__swapped__", *OBSERVED_EMPTY_TEXT[1:]]
        replace_everywhere(first, OBSERVED_EMPTY_TEXT, sentinel)
        replace_everywhere(first, other, OBSERVED_EMPTY_TEXT)
        replace_everywhere(first, sentinel, other)
    elif change == "value_kind":
        first["rows"][0][EMPTY_TEXT] = {
            "kind": "bytes",
            "value": "",
        }
    elif change == "null_value":
        first["rows"][0][EMPTY_TEXT] = {"kind": "null"}
    elif change == "multiplicity":
        first["rows"].pop()
    elif change == "parameters":
        bound = case["observations"][1]
        bound["parameters"] = bound["parameters"][:-1]
    elif change == "empty_result_metadata":
        empty = case["observations"][4]
        assert empty["rows"] == []
        empty["metadata"] = None
    else:
        named = fixed_case(receipt, "S_fixed_named")["observations"][0]
        named["metadata"][-1][1] = 254
    reject_receipt(receipt, valid_receipts)
