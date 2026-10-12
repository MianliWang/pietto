"""Public live relay uses a fresh source and an explicit local sink contract."""

from __future__ import annotations

import inspect
import sqlite3

import pytest

import _pietto_execution_api as api
from _pietto_jobs_public_cases import _controlled_postgres_source
from _pietto_phase68_slice11_probe import qualified
import pietto.execution as execution
from pietto._project import project_execution as private_execution
from pietto._project import project_job_runtime as runtime
from pietto._project import project_job_sink as sink_owner
from pietto._project import project_job_workspace as private_workspace


@pytest.fixture
def query(tmp_path):
    return execution.compile_query(
        api.write_example(tmp_path / "project"),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


def _access():
    return execution.PostgresAccess("127.0.0.1", 9, "phase66", "pietto_query", "pw")


def _premise():
    return execution.PostgresDeploymentPremise(("fixture", "pg_catalog"))


def test_relay_requires_a_sink_before_opening_the_workspace(query):
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "0" * 32)

    with pytest.raises(execution.RequestRejected) as refused:
        execution.relay_live(
            workspace,
            query,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=_access(),
            premise=_premise(),
            sink_root=None,
            expected_sink_identity="snk-" + "0" * 32,
            sink_namespace="relay",
            sink_epoch=1,
            sink_retention="retention",
            sink_budget_bytes=private_workspace.DEFAULT_BUDGET,
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1001",
        "REFERENCE_SINK_ROOT",
    )


@pytest.mark.parametrize(
    ("route", "dialect", "access", "premise", "deployment"),
    (
        (
            "postgres_rows",
            "postgres",
            lambda: _access(),
            lambda: _premise(),
            "postgres_deployment",
        ),
        (
            "postgres_adbc",
            "postgres",
            lambda: _access(),
            lambda: _premise(),
            "postgres_adbc_deployment",
        ),
        (
            "mysql_rows",
            "mysql",
            lambda: execution.MySQLAccess(
                "mysql.example.test", 3306, "app", "reader", "pw", "/ca.pem", "reader"
            ),
            lambda: execution.MySQLDeploymentPremise(("fixture",)),
            "mysql_deployment",
        ),
    ),
)
def test_live_relay_pairs_each_public_route_with_its_private_profile_before_source(
    query, monkeypatch, route, dialect, access, premise, deployment
):
    if dialect == "mysql":
        mysql = object.__new__(execution.CompiledQuery)
        for slot in execution.CompiledQuery.__slots__:
            object.__setattr__(mysql, slot, getattr(query, slot))
        object.__setattr__(mysql, "_dialect", "mysql")
        query = mysql
    captured = {}

    def prepare(binding, private_access, **options):
        captured.update(access=private_access, options=options)

    monkeypatch.setattr(private_execution, "prepare_compiled_execution", prepare)
    monkeypatch.setattr(
        runtime,
        "_owner",
        lambda *_args: pytest.fail("sink refusal opened a source owner"),
    )
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "1" * 32)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.relay_live(
            workspace,
            query,
            operation=execution.new_operation(),
            route=route,
            access=access(),
            premise=premise(),
            sink_root=None,
            expected_sink_identity="snk-" + "0" * 32,
            sink_namespace="relay",
            sink_epoch=1,
            sink_retention="retention",
            sink_budget_bytes=private_workspace.DEFAULT_BUDGET,
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1001",
        "REFERENCE_SINK_ROOT",
    )
    assert set(captured["options"]) & {
        "postgres_deployment",
        "postgres_adbc_deployment",
        "mysql_deployment",
    } == {deployment}


def test_live_relay_has_no_saved_reply_recovery_input():
    assert "save_reply" not in inspect.signature(execution.relay_live).parameters


def test_pending_relay_cleanup_projects_a_close_failure_and_allows_retry():
    class Pending:
        def __init__(self):
            self.calls = 0

        def close(self):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("relay-close-secret")

    pending = Pending()
    handle = execution.RelayCloseHandle(pending)
    with pytest.raises(execution.RequestRejected) as refused:
        handle.close()
    assert (
        "relay-close-secret" not in str(refused.value)
        and refused.value.__cause__ is None
        and refused.value.__context__ is None
        and handle.closed is False
    )
    handle.close()
    assert handle.closed is True and pending.calls == 2


def test_create_reference_sink_returns_plain_verified_values(tmp_path):
    if not qualified(tmp_path):
        return
    descriptor = execution.create_reference_sink(
        tmp_path / "sink", namespace="relay", epoch=1, retention_seconds=60
    )
    assert descriptor.root == str(tmp_path / "sink")
    assert not hasattr(descriptor, "close")
    opened = sink_owner.open_sink(
        descriptor.root, expected_identity=descriptor.identity
    )
    try:
        assert (
            opened.namespace,
            opened.epoch,
            opened.retention,
            opened.budget,
        ) == (
            descriptor.namespace,
            descriptor.epoch,
            descriptor.retention,
            descriptor.budget_bytes,
        )
    finally:
        opened.close()


def test_live_relay_captures_and_delivers_real_checked_arrow_rows(
    tmp_path, query, monkeypatch
):
    pytest.importorskip("pyarrow")
    if not qualified(tmp_path):
        return
    _controlled_postgres_source(
        monkeypatch, (((2, "two"), (2, "two")), ((3, "three"),))
    )
    workspace = execution.create_workspace(
        tmp_path / "workspace", budget_bytes=private_workspace.DEFAULT_BUDGET
    )
    sink = execution.create_reference_sink(
        str(tmp_path / "sink"), namespace="relay", epoch=1, retention_seconds=60
    )
    reply = execution.relay_live(
        workspace,
        query,
        operation=execution.new_operation(),
        route="postgres_rows",
        access=_access(),
        premise=_premise(),
        sink_root=sink.root,
        expected_sink_identity=sink.identity,
        sink_namespace=sink.namespace,
        sink_epoch=sink.epoch,
        sink_retention=sink.retention,
        sink_budget_bytes=sink.budget_bytes,
        sink_busy_seconds=sink.busy_seconds,
        limits=execution.ExecutionLimits(batch_rows=2, seconds=60),
    )
    assert (reply.terminal, reply.settlement, reply.cleanup) == (
        "COMPLETED",
        "RELEASED",
        None,
    )
    opened = sink_owner.open_sink(sink.root, expected_identity=sink.identity)
    try:
        rows = (
            opened.use()
            .execute("SELECT position FROM effect ORDER BY position")
            .fetchall()
        )
    finally:
        opened.close()
    assert rows == [(0,), (1,), (2,)]


def test_pending_relay_keeps_its_runtime_until_explicit_cleanup(
    tmp_path, query, monkeypatch
):
    pytest.importorskip("pyarrow")
    if not qualified(tmp_path):
        return
    _controlled_postgres_source(monkeypatch, (((2, "two"),),))
    workspace = execution.create_workspace(
        tmp_path / "workspace", budget_bytes=private_workspace.DEFAULT_BUDGET
    )
    sink = execution.create_reference_sink(
        str(tmp_path / "sink"), namespace="relay", epoch=1, retention_seconds=60
    )
    lock = sqlite3.connect(sink.root + "/sink.sqlite", isolation_level=None, timeout=5)
    lock.execute("BEGIN IMMEDIATE")
    try:
        reply = execution.relay_live(
            workspace,
            query,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=_access(),
            premise=_premise(),
            sink_root=sink.root,
            expected_sink_identity=sink.identity,
            sink_namespace=sink.namespace,
            sink_epoch=sink.epoch,
            sink_retention=sink.retention,
            sink_budget_bytes=sink.budget_bytes,
            sink_busy_seconds=0.01,
            limits=execution.ExecutionLimits(batch_rows=1, seconds=60),
        )
        assert reply.terminal is None and reply.cleanup is not None
    finally:
        lock.execute("ROLLBACK")
        lock.close()
    reply.cleanup.close()
    assert reply.cleanup.closed is True


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("expected_sink_identity", "snk-" + "0" * 32),
        ("sink_namespace", "other"),
        ("sink_epoch", 2),
        ("sink_retention", "wrong"),
        ("sink_budget_bytes", private_workspace.DEFAULT_BUDGET + 1),
        ("sink_busy_seconds", 0),
        ("sink_busy_seconds", object()),
    ),
)
def test_sink_mismatches_fail_before_live_source_work(
    tmp_path, query, monkeypatch, field, value
):
    if not qualified(tmp_path):
        return
    workspace = execution.create_workspace(
        tmp_path / "workspace", budget_bytes=private_workspace.DEFAULT_BUDGET
    )
    sink = execution.create_reference_sink(
        str(tmp_path / "sink"), namespace="relay", epoch=1, retention_seconds=60
    )
    calls = []

    def forbidden(*arguments):
        calls.append(arguments)
        raise AssertionError("sink mismatch opened a live source")

    monkeypatch.setattr(runtime, "_owner", forbidden)
    options = dict(
        sink_root=sink.root,
        expected_sink_identity=sink.identity,
        sink_namespace=sink.namespace,
        sink_epoch=sink.epoch,
        sink_retention=sink.retention,
        sink_budget_bytes=sink.budget_bytes,
        sink_busy_seconds=sink.busy_seconds,
    )
    options[field] = value
    with pytest.raises(execution.RequestRejected) as refused:
        execution.relay_live(
            workspace,
            query,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=_access(),
            premise=_premise(),
            limits=execution.ExecutionLimits(batch_rows=2, seconds=60),
            **options,  # type: ignore[reportArgumentType]
        )
    assert refused.value.code == "PIE-R1002"
    assert calls == []
