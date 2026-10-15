"""Public ordinary-save request and opaque workspace behavior."""

from __future__ import annotations

import json
import threading
from typing import Any

import pytest

import _pietto_execution_api as api
import _pietto_jobs_public_cases as public_cases
import _pietto_execution_jobs_probe as workspace_probe
import pietto.execution as execution
from pietto._project import project_job_store as store
from pietto._project import project_job_workspace as private_workspace


@pytest.fixture(scope="module")
def query(tmp_path_factory):
    return execution.compile_query(
        api.write_example(tmp_path_factory.mktemp("execution-save")),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


def test_save_refuses_wrong_values_before_any_workspace_control_write(
    query, monkeypatch
):
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "0" * 32)

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused save wrote workspace control state")

    monkeypatch.setattr(store, "register_job", forbidden)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.save(
            workspace,
            query,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
            premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
            values=("wrong",),
        )
    assert (refused.value.code, refused.value.detail) == ("PIE-R1006", "BINDING_SLOTS")


SINCE = (
    "\nquery since(low: Int not null, note: Text nullable):\n    from items\n"
    "    where id > low and (note is null or label != note)\n    select:\n"
    "        id\n        next = low + 1\n"
)


@pytest.fixture(scope="module")
def since(tmp_path_factory):
    project = api.write_example(tmp_path_factory.mktemp("execution-save-parameters"))
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + SINCE, encoding="utf-8")
    return execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="since",
        dialect="postgres",
        emission_contract="contract.json",
    )


@pytest.mark.parametrize(
    "parameters,code,detail",
    (
        ([("low", 5)], "PIE-R1002", "PUBLIC_PARAMETERS_TYPE"),
        (None, "PIE-R1006", "BINDING_PARAMETERS"),
        ({"low": 5}, "PIE-R1006", "BINDING_PARAMETERS"),
        ({"low": True, "note": None}, "PIE-R1006", "BINDING_PARAMETER:0:Int"),
        ({"low": None, "note": None}, "PIE-R1006", "BINDING_PARAMETER:0:Int"),
        ({"low": 5, "note": 5}, "PIE-R1006", "BINDING_PARAMETER:1:Text"),
        ({"low": 2**63 - 1, "note": None}, "PIE-R1004", "BINDING_INVALID"),
    ),
    ids=("pairs", "missing", "absent", "bool", "null", "int_text", "overflow"),
)
@pytest.mark.parametrize("operation", ("save", "save_recoverable", "relay_live"))
def test_saved_operations_bind_parameters_before_the_workspace(
    since, monkeypatch, operation, parameters, code, detail
):
    """Every entry that starts a generation binds the caller's parameters like
    execute() and refuses a missing, extra, mistyped, illegal NULL or
    out-of-range value before it opens the workspace or connects (recover
    restates a saved binding instead: tests/test_execution_recovery.py)."""
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "3" * 32)

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused request opened the workspace")

    monkeypatch.setattr(private_workspace, "open_workspace", forbidden)
    arguments: dict = dict(
        operation=execution.new_operation(),
        route="postgres_rows",
        access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
        premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
        parameters=parameters,
    )
    if operation == "save_recoverable":
        arguments.update(source_requirements=(), limits=execution.ExecutionLimits())
    if operation == "relay_live":
        arguments.update(
            sink_root="/not-opened",
            expected_sink_identity="sink-" + "0" * 32,
            sink_namespace="n",
            sink_epoch=1,
            sink_retention="r",
            sink_budget_bytes=1,
        )
    with pytest.raises(execution.RequestRejected) as refused:
        getattr(execution, operation)(workspace, since, **arguments)
    assert (refused.value.code, refused.value.detail) == (code, detail)


def test_save_checks_isolation_before_opening_workspace(query, monkeypatch):
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "2" * 32)

    def forbidden(*arguments, **keywords):
        raise AssertionError("an invalid request opened the workspace")

    monkeypatch.setattr(store, "register_job", forbidden)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.save(
            workspace,
            query,
            operation=execution.new_operation(),
            route="postgres_rows",
            access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
            premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
            isolation="not-an-isolation",
        )
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1002",
        "EXECUTION_ISOLATION",
    )


def test_saved_surface_exports_only_opaque_public_carriers():
    assert {
        "WorkspaceRef",
        "OperationReply",
        "SaveCloseHandle",
        "SaveReply",
        "create_workspace",
        "open_workspace",
        "new_operation",
        "operation_result",
        "save",
    } <= set(execution.__all__)
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/private-root")
    object.__setattr__(workspace, "identity", "ws-" + "1" * 32)
    assert "connection" not in repr(workspace)


def test_pending_save_cleanup_is_retained_until_the_explicit_close():
    class Pending:
        def __init__(self):
            self.calls = 0

        def close(self):
            self.calls += 1

    pending = Pending()
    handle = execution.SaveCloseHandle(pending)
    assert handle.closed is False
    handle.close()
    handle.close()
    assert handle.closed is True and pending.calls == 1


def test_pending_save_cleanup_projects_a_close_failure_and_allows_retry():
    class Pending:
        def __init__(self):
            self.calls = 0

        def close(self):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("save-close-secret")

    pending = Pending()
    handle = execution.SaveCloseHandle(pending)
    with pytest.raises(execution.RequestRejected) as refused:
        handle.close()
    assert (
        "save-close-secret" not in str(refused.value)
        and refused.value.__cause__ is None
        and refused.value.__context__ is None
        and handle.closed is False
    )
    handle.close()
    assert handle.closed is True and pending.calls == 2


def test_public_runtime_capacity_preserves_the_control_operation_reserve(tmp_path):
    from pietto._project import project_job_runtime as runtime
    from pietto._project import project_public_jobs as jobs

    if not workspace_probe.qualified(tmp_path):
        pytest.skip("runtime capacity requires a qualified workspace")
    reference = execution.create_workspace(
        tmp_path / "workspace", budget_bytes=private_workspace.MIN_BUDGET
    )
    budget, operations = jobs.runtime_capacity(reference)
    policy = jobs.policy_for(budget, operations)
    assert (budget, operations, policy.operations, policy.durable) == (
        private_workspace.MIN_BUDGET,
        65536 - store.CONTROL_OPERATIONS,
        65536 - store.CONTROL_OPERATIONS,
        min(
            64 * runtime.MIB,
            (private_workspace.MIN_BUDGET - private_workspace.CONTROL_RESERVE) // 2,
        ),
    )


def test_capture_uses_verified_budget_and_a_policy_compatible_real_runtime(
    tmp_path, monkeypatch
):
    saved = public_cases.completed_saved_result(tmp_path, monkeypatch)
    if saved is None:
        return
    try:
        assert (
            saved.state.terminal,
            saved.state.settlement,
            dict(saved.state.counters)["rows"],
        ) == (
            "COMPLETED",
            "RELEASED",
            3,
        )
    finally:
        saved.close()


def test_public_save_runs_the_real_runtime_capture_path(tmp_path, monkeypatch):
    if not workspace_probe.qualified(tmp_path):
        return
    from pietto._project import project_arrow_result as arrow
    from pietto._project import project_execution as private_execution

    try:
        arrow.pinned()
    except private_execution.ExecutionError:
        pytest.skip("public save payload requires pinned PyArrow")
    public_cases._controlled_postgres_source(monkeypatch, (((2, 3), (2, 3)), ((3, 4),)))
    from pietto._project.project_execution_postgres import PostgresExecution

    controlled_open = PostgresExecution.open

    def open(owner):
        result = controlled_open(owner)
        owner._qualification = "CONTROLLED_SOURCE_QUALIFICATION"
        owner.context = ("CONTROLLED_SOURCE_CONTEXT",)
        return result

    monkeypatch.setattr(PostgresExecution, "open", open)
    template, _built = workspace_probe.compiled_template(tmp_path / "compiled")
    from pietto.execution._query import _query

    query = _query(template, "live", None)
    workspace = execution.create_workspace(
        tmp_path / "public-workspace", budget_bytes=private_workspace.MIN_BUDGET
    )
    try:
        operation = execution.new_operation()
        reply = execution.save(
            workspace,
            query,
            operation=operation,
            route="postgres_rows",
            access=execution.PostgresAccess("127.0.0.1", 9, "db", "u", "pw", "disable"),
            premise=execution.PostgresDeploymentPremise(("public", "pg_catalog")),
        )
        assert (reply.terminal, reply.settlement, reply.cleanup) == (
            "COMPLETED",
            "RELEASED",
            None,
        )
        recorded = execution.operation_result(workspace, operation)
        assert recorded is not None and recorded.job == reply.job
    finally:
        private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        ).close()


def test_adbc_save_cleanup_is_retained_until_explicit_retry(tmp_path, monkeypatch):
    if not workspace_probe.qualified(tmp_path):
        return
    pytest.importorskip("pyarrow")
    pytest.importorskip("adbc_driver_postgresql")
    pytest.importorskip("adbc_driver_manager")
    from pietto._project import project_execution_reader as reader
    from pietto._project import project_job_runtime as runtime
    from pietto._project.project_execution import ExecutionFailure
    from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution

    release = threading.Event()
    original_owner = runtime._owner

    def owner(binding, source):
        result = original_owner(binding, source)
        assert type(result) is PostgresADBCExecution
        assert result.request.postgres_adbc_deployment is not None
        return result

    def open(owner):
        from pietto._project.project_execution_reader import bind_stored_output

        owner._payloads = reader.ExecutionPayloads(
            owner.request,
            (),
            producer=bind_stored_output(owner.request.output, owner.request.route),
        )
        owner._fixture_rows = iter((((2, 3),),))
        owner._source, owner._transaction, owner._delivery = "READING", "OPEN", "OPEN"
        owner._qualification, owner.context = "CONTROLLED", ("CONTROLLED",)
        return owner

    def next_(owner):
        try:
            return owner._payloads.accept(next(owner._fixture_rows))
        except StopIteration:
            owner._terminal = "COMPLETE"
            owner._source, owner._delivery = "EOF", "COMPLETE"
            raise

    def close(owner):
        if not getattr(owner, "_fixture_pending", False):
            owner._fixture_pending = True
            owner._retired = True
            owner._transaction, owner._cleanup = "UNKNOWN", "FAILED_REMOTE_UNOBSERVED"
            owner._primary = ExecutionFailure("cleanup", "TimeoutError")
            return
        assert release.wait(2)
        owner._closed, owner._cleanup = True, "CLOSED"

    monkeypatch.setattr(runtime, "_owner", owner)
    monkeypatch.setattr(PostgresADBCExecution, "open", open)
    monkeypatch.setattr(PostgresADBCExecution, "__next__", next_)
    monkeypatch.setattr(PostgresADBCExecution, "close", close)
    template, _built = workspace_probe.compiled_template(tmp_path / "compiled")
    from pietto.execution._query import _query

    workspace = execution.create_workspace(
        tmp_path / "workspace", budget_bytes=private_workspace.MIN_BUDGET
    )
    try:
        reply = execution.save(
            workspace,
            _query(template, "live", None),
            operation=execution.new_operation(),
            route="postgres_adbc",
            access=execution.PostgresAccess("127.0.0.1", 9, "db", "u", "pw", "disable"),
            premise=execution.PostgresDeploymentPremise(("public", "pg_catalog")),
        )
        assert reply.terminal == "FAILED_REMOTE_UNOBSERVED"
        assert reply.cleanup is not None and not reply.cleanup.closed
        release.set()
        reply.cleanup.close()
        assert reply.cleanup.closed
        assert reply.job is not None
        opened = private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        )
        try:
            attempt = store.job_record(opened, reply.job).attempts[0]
        finally:
            opened.close()
        assert attempt.terminal == "OUTCOME"
        assert attempt.outcome is not None
        assert dict(attempt.outcome)["transaction"] == "UNKNOWN"
    finally:
        private_workspace.open_workspace(
            workspace.root, expected_identity=workspace.identity
        ).close()


def test_replayed_save_operation_is_read_only_before_claim_or_generation(
    tmp_path, query
):
    if not workspace_probe.qualified(tmp_path):
        return
    workspace = private_workspace.create_workspace(
        str(tmp_path / "workspace"), format=private_workspace.FORMAT_V7
    )
    operation = execution.new_operation()
    try:
        original = store.register_job(workspace, query._template, operation=operation)
        before = store.job_record(workspace, original.job)
        reference = execution.WorkspaceRef(workspace.root, workspace.identity)
        reply = execution.save(
            reference,
            query,
            operation=operation,
            route="postgres_rows",
            access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
            premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
        )
        after = store.job_record(workspace, original.job)
        assert reply.terminal == "REPLY_LOST_OR_PARTIAL"
        assert (
            reply.operation is not None
            and reply.operation.sequence == original.sequence
        )
        assert (
            after.publisher_epoch,
            after.bindings,
            after.generations,
            after.operations,
        ) == (
            before.publisher_epoch,
            before.bindings,
            before.generations,
            before.operations,
        )
        other = execution.compile_query(
            api.write_example(tmp_path / "other-query", relation="other_items"),
            module="main.pietto",
            kind="table",
            name="active_items",
            dialect="postgres",
            emission_contract="contract.json",
        )
        with pytest.raises(execution.RequestRejected) as conflict:
            execution.save(
                reference,
                other,
                operation=operation,
                route="postgres_rows",
                access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
                premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
            )
        assert conflict.value.code == "PIE-R1010"
        assert store.job_record(workspace, original.job) == after

        values = tuple(
            slot.original.site.position.literal.value for slot in query._template.slots
        )
        from pietto._project.project_execution_template import bind_values

        publisher = store.claim_publisher(
            workspace, original.job, operation=execution.new_operation()
        )
        try:
            binding = store.register_binding(
                publisher,
                bind_values(query._template, tuple(zip(query._template.slots, values))),
                operation=execution.new_operation(),
            )
        finally:
            publisher.close()
        before = store.job_record(workspace, original.job)
        reply = execution.save(
            reference,
            query,
            operation=binding.operation,
            route="postgres_rows",
            access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
            premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
            job=original.job,
        )
        assert reply.terminal == "REPLY_LOST_OR_PARTIAL"
        assert (
            reply.operation is not None and reply.operation.sequence == binding.sequence
        )
        assert store.job_record(workspace, original.job) == before
    finally:
        workspace.close()


VALUES_JOIN = """
query tagged:
    let tags:
        values(tid: Int not null, tag: Text not null):
            1, "one"
            2, "two"
    from items
    inner join tags as t:
        from items
        on items.id == t.tid
    select:
        id
        tag = t.tag
"""
VALUES_ONLY = """
query tagged:
    values(tid: Int not null, tag: Text not null):
        1, "one"
"""
MYSQL_VALUES_JOIN = """query tagged:
    let tags:
        values(tid: Int not null, tag: Text not null):
            1, "one"
    from lhs
    inner join tags as t:
        from lhs
        on lhs.id == t.tid
    select:
        id = lhs.id
        tag = t.tag
"""


def values_query(directory, case):
    """A VALUES join beside a physical source on either target, or a
    PostgreSQL query whose only input is a VALUES body."""
    if case == "mysql_join":
        project = api.write_join_witness(
            directory / "mysql", "mysql", MYSQL_VALUES_JOIN
        )
    else:
        project = api.write_example(directory)
        main = project / "main.pietto"
        body = VALUES_JOIN if case == "postgres_join" else VALUES_ONLY
        main.write_text(main.read_text(encoding="utf-8") + body, encoding="utf-8")
        if case == "postgres_only":
            contract = json.loads(
                (project / "contract.json").read_text(encoding="utf-8")
            )
            contract["sources"] = []
            (project / "contract.json").write_text(
                json.dumps(contract), encoding="utf-8"
            )
    return execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="tagged",
        dialect="mysql" if case == "mysql_join" else "postgres",
        emission_contract="contract.json",
    )


HEADER_SINCE = """
query since(low: Int not null):
    from items
    where id > low and id < low + low
    select:
        id
"""


@pytest.mark.parametrize("limit", (12, 13))
def test_recoverable_pages_charge_the_parameter_limit_before_any_workspace(
    tmp_path, monkeypatch, limit
):
    """D70.07: the statement reads `low` three times, and its largest R2 page
    binds nine more values (one per coordinate where its predicate reads it,
    and its row count): a `parameters` limit of 12 refuses save_recoverable
    and recover before any workspace is opened; 13 reaches the workspace."""
    project = api.write_example(tmp_path)
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + HEADER_SINCE, encoding="utf-8")
    contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
    contract["environment"].append(
        {"key": "resource_limits", "scope": "statement", "value": {"parameters": limit}}
    )
    (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    query = execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="since",
        dialect="postgres",
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "4" * 32)

    class Opened(Exception):
        pass

    def opened(*arguments, **keywords):
        raise Opened

    monkeypatch.setattr(private_workspace, "open_workspace", opened)
    monkeypatch.setattr(store, "register_job", opened)
    r2: dict[str, Any] = dict(
        query=query,
        source_requirements=tuple(
            execution.R2SourceInput(
                source.namespace,
                source.name,
                "provider",
                "v1",
                "r1",
                source.namespace,
                "registry",
                "SELECT 1",
                ("id",),
                "pietto_query",
                "retained",
            )
            for source in query._template.artifact.request.sources
        ),
        operation=execution.new_operation(),
        route="postgres_rows",
        access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
        premise=execution.PostgresDeploymentPremise(("fixture", "pg_catalog")),
        limits=execution.ExecutionLimits(),
        parameters={"low": 5},
    )
    for call in (
        lambda: execution.save_recoverable(workspace, **r2),
        lambda: execution.recover(
            workspace,
            job="job-" + "5" * 32,
            generation="gen-" + "6" * 32,
            checkpoint=None,
            expected_pin=bundle.pin,
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
            purpose="parameter budget",
            seconds=1,
            **r2,
        ),
    ):
        with pytest.raises(execution.RequestRejected) as refused:
            call()
        if limit == 12:
            assert (refused.value.code, refused.value.detail) == (
                "PIE-R1004",
                "REFINEMENT_RESOURCE_LIMIT",
            )
        else:
            assert refused.value.code == "PIE-R1009"
            assert "cause=Opened" in str(refused.value)


@pytest.mark.parametrize("case", ("postgres_join", "postgres_only", "mysql_join"))
def test_values_rows_save_ordinarily_but_have_no_recovery_coordinates(
    tmp_path, monkeypatch, case
):
    """A VALUES row has no source position or token column: an ordinary save is
    admitted, and save_recoverable and recover are refused before any
    workspace is opened, even beside a physical source."""
    query = values_query(tmp_path, case)
    bundle = execution.export_bundle(query)
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "4" * 32)

    class Opened(Exception):
        pass

    def opened(*arguments, **keywords):
        raise Opened

    monkeypatch.setattr(private_workspace, "open_workspace", opened)
    monkeypatch.setattr(store, "register_job", opened)
    request: dict[str, Any] = (
        dict(
            route="mysql_rows",
            access=execution.MySQLAccess(
                "127.0.0.1", 3306, "phase66", "u", "pw", "/ca.pem", "u"
            ),
            premise=execution.MySQLDeploymentPremise(("phase66",)),
        )
        if case == "mysql_join"
        else dict(
            route="postgres_rows",
            access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
            premise=execution.PostgresDeploymentPremise(
                ("pg_catalog",)
                if case == "postgres_only"
                else ("fixture", "pg_catalog")
            ),
        )
    )
    # The ordinary save passes every request check and reaches the workspace.
    with pytest.raises(execution.RequestRejected) as reached:
        execution.save(workspace, query, operation=execution.new_operation(), **request)
    assert reached.value.code == "PIE-R1009" and "cause=Opened" in str(reached.value)
    inputs = tuple(
        execution.R2SourceInput(
            source.namespace,
            source.name,
            "provider",
            "v1",
            "r1",
            source.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for source in query._template.artifact.request.sources
    )
    assert len(inputs) == (0 if case == "postgres_only" else 1)
    r2: dict[str, Any] = dict(
        query=query,
        source_requirements=inputs,
        operation=execution.new_operation(),
        limits=execution.ExecutionLimits(),
        **request,
    )
    for call in (
        lambda: execution.save_recoverable(workspace, **r2),
        lambda: execution.recover(
            workspace,
            job="job-" + "5" * 32,
            generation="gen-" + "6" * 32,
            checkpoint=None,
            expected_pin=bundle.pin,
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
            purpose="values recovery",
            seconds=1,
            **r2,
        ),
    ):
        with pytest.raises(execution.RequestRejected) as refused:
            call()
        assert (refused.value.code, refused.value.detail) == (
            "PIE-R1004",
            "PUBLIC_R2_VALUES_COORDINATE_BASIS",
        )


SERIES_JOIN = """
query tagged:
    let steps:
        from generate_series(1, 3, 1) as n
        select:
            n
    from items
    inner join steps as s:
        from items
        on items.id == s.n
    select:
        id
        step = s.n
"""
SERIES_ONLY = """
query tagged:
    from generate_series(3, 1, -1) as n
    select:
        n
"""


@pytest.mark.parametrize("case", ("postgres_join", "postgres_only"))
def test_series_rows_save_ordinarily_but_have_no_recovery_coordinates(
    tmp_path, monkeypatch, case
):
    """A generated series row has no source position or token column: an
    ordinary save is admitted, and save_recoverable and recover are refused
    before any workspace is opened, even beside a physical source."""
    project = api.write_example(tmp_path)
    main = project / "main.pietto"
    body = SERIES_JOIN if case == "postgres_join" else SERIES_ONLY
    main.write_text(main.read_text(encoding="utf-8") + body, encoding="utf-8")
    if case == "postgres_only":
        contract = json.loads((project / "contract.json").read_text(encoding="utf-8"))
        contract["sources"] = []
        (project / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
    query = execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="tagged",
        dialect="postgres",
        emission_contract="contract.json",
    )
    bundle = execution.export_bundle(query)
    workspace = object.__new__(execution.WorkspaceRef)
    object.__setattr__(workspace, "root", "/not-opened")
    object.__setattr__(workspace, "identity", "ws-" + "4" * 32)

    class Opened(Exception):
        pass

    def opened(*arguments, **keywords):
        raise Opened

    monkeypatch.setattr(private_workspace, "open_workspace", opened)
    monkeypatch.setattr(store, "register_job", opened)
    request: dict[str, Any] = dict(
        route="postgres_rows",
        access=execution.PostgresAccess("127.0.0.1", 5432, "db", "u", "pw"),
        premise=execution.PostgresDeploymentPremise(
            ("pg_catalog",) if case == "postgres_only" else ("fixture", "pg_catalog")
        ),
    )
    with pytest.raises(execution.RequestRejected) as reached:
        execution.save(workspace, query, operation=execution.new_operation(), **request)
    assert reached.value.code == "PIE-R1009" and "cause=Opened" in str(reached.value)
    inputs = tuple(
        execution.R2SourceInput(
            source.namespace,
            source.name,
            "provider",
            "v1",
            "r1",
            source.namespace,
            "registry",
            "SELECT 1",
            ("id",),
            "pietto_query",
            "retained",
        )
        for source in query._template.artifact.request.sources
    )
    assert len(inputs) == (0 if case == "postgres_only" else 1)
    r2: dict[str, Any] = dict(
        query=query,
        source_requirements=inputs,
        operation=execution.new_operation(),
        limits=execution.ExecutionLimits(),
        **request,
    )
    for call in (
        lambda: execution.save_recoverable(workspace, **r2),
        lambda: execution.recover(
            workspace,
            job="job-" + "5" * 32,
            generation="gen-" + "6" * 32,
            checkpoint=None,
            expected_pin=bundle.pin,
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
            purpose="series recovery",
            seconds=1,
            **r2,
        ),
    ):
        with pytest.raises(execution.RequestRejected) as refused:
            call()
        assert (refused.value.code, refused.value.detail) == (
            "PIE-R1004",
            "PUBLIC_R2_TABLE_FUNCTION_COORDINATE_BASIS",
        )
