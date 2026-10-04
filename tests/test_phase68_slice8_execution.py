"""Offline MySQL request/owner/protocol boundaries; no database acquisition."""

from dataclasses import replace

import pytest

from _pietto_phase68_slice7_cases import manifest, case_preparation
from test_phase68_slice6_refinement import capabilities, refined
from pietto._project.project_execution import (
    MySQLAccess,
    PostgresAccess,
    ExecutionError,
    prepare_execution,
)
from pietto._project.project_execution_mysql import MySQLExecution
from pietto._project.project_execution_postgres import PostgresExecution
from pietto._project.project_guard_preparation import prepare_guarded_output
from pietto._project.project_guard_runtime import (
    prepare_guarded_execution,
    ObservedGuardRequest,
)
from pietto._project.project_refinement import prepare_refinement, TieRefinement
from pietto._project.project_refinement_enumeration import prepare_refined_execution


def access():
    return MySQLAccess(
        "127.0.0.1",
        3306,
        "phase66",
        "pietto_query",
        "not-a-live-secret",
        "/explicit/ca.pem",
        "pietto_query@%",
        verify_identity=False,
        loopback_tls_exception=True,
    )


@pytest.mark.parametrize(
    "name",
    (
        "no_request",
        "bag_one",
        "right_limit_0",
        "right_limit_1",
        "path_whole_positive",
        "refined_pages",
        "refined_violation_outside_page",
    ),
)
def test_exact_mysql_product_entry_shapes(tmp_path, name):
    case = next(c for c in manifest() if c["name"] == name)
    preparation = case_preparation(tmp_path, "mysql", case)
    query = None
    if case["options"].get("refined"):
        query = prepare_refinement(
            preparation.artifact,
            capabilities(preparation.artifact),
            policy=TieRefinement(),
            output=prepare_guarded_output(preparation),
        )
    request = prepare_guarded_execution(preparation, access(), refinement=query)
    owner = MySQLExecution(request)
    assert owner.request is request.execution
    assert owner._connection is None and owner._controller is None
    assert owner.guarded_request is request
    assert (owner.refined_request is None) == (query is None)
    with pytest.raises(ExecutionError, match="EXECUTION_TARGET"):
        PostgresExecution(request)
    with pytest.raises(ValueError):
        MySQLExecution(ObservedGuardRequest(request.program))
    assert "not-a-live-secret" not in repr(request)


def test_ordinary_and_unguarded_refinement_keep_mysql_authority(tmp_path):
    q = refined(tmp_path, "mysql", "G_emission_table_bag", "bag")
    for request in (
        prepare_execution(q.original, access()),
        prepare_refined_execution(q, access()),
    ):
        owner = MySQLExecution(request)
        assert owner.request.artifact is q.original
        assert owner.guarded_request is None
        with pytest.raises(ExecutionError, match="EXECUTION_TARGET"):
            PostgresExecution(request)
    with pytest.raises(ExecutionError, match="EXECUTION_TARGET"):
        prepare_execution(
            q.original,
            PostgresAccess("127.0.0.1", 5432, "lab", "reader", "not-live", "disable"),
        )


def test_access_and_value_mutation_precede_any_connection(tmp_path):
    q = refined(tmp_path, "mysql", "G_emission_table_bag", "bag")
    for a in (
        replace(access(), host="example.invalid"),
        replace(access(), loopback_tls_exception=False),
        replace(access(), transaction_observation="caller_assertion"),
        replace(access(), ca_file=""),
        replace(access(), port=True),
    ):
        with pytest.raises(ExecutionError):
            prepare_execution(q.original, a)
    request = prepare_execution(q.original, access())
    owner = MySQLExecution(request)
    object.__setattr__(request.access, "roles", "foreign")
    with pytest.raises(ExecutionError, match="EXECUTION_RESOURCE_IDENTITY"):
        owner.open()
    assert owner._connections == [] and owner.control_joined


def test_native_statement_rejects_foreign_owner():
    from pietto._project.project_execution_mysql_native import NativeStatement

    with pytest.raises(ExecutionError, match="MYSQL_STATEMENT_OWNER"):
        NativeStatement(object(), b"SELECT 1", (), "query")


def test_mysql_failure_preserves_vendor_code_without_changing_pg_record():
    from dataclasses import asdict
    from pietto._project.project_execution_mysql_native import failure
    from pietto._project.project_execution import ExecutionFailure

    class NativeError(Exception):
        errno = 1317
        sqlstate = "70100"

    assert asdict(failure(NativeError(), "read")) == {
        "phase": "read",
        "kind": "NativeError",
        "sqlstate": "70100",
        "vendor_code": 1317,
    }
    assert set(asdict(ExecutionFailure("read", "Error"))) == {
        "phase",
        "kind",
        "sqlstate",
    }


@pytest.mark.parametrize(
    "explain,diagnostic,accepted",
    (
        (True, ("Note", 1003, "rewritten plan"), True),
        (False, ("Note", 1003, "rewritten plan"), False),
        (True, ("Warning", 3135, "mode warning"), False),
        (True, ("Note", 9999, "unknown"), False),
    ),
)
def test_only_explain_plan_note_has_a_purpose_bound_exception(
    explain, diagnostic, accepted
):
    from types import SimpleNamespace
    from pietto._project.project_execution_mysql_native import read_control
    from pietto._project.project_execution import ExecutionLimits

    class Cursor:
        description = ()
        warning_count = 1

        def execute(self, sql, arguments=()):
            pass

        def fetchmany(self, count):
            return [diagnostic]

        def fetchone(self):
            return None

        def close(self):
            pass

    connection = SimpleNamespace(unread_result=False, cursor=lambda **options: Cursor())
    owner = SimpleNamespace(
        _connection=connection,
        _checkpoint=lambda: None,
        _charge_internal=lambda rows: None,
        _controls=[],
        _cleanup_errors=[],
        control_events=[],
        request=SimpleNamespace(limits=ExecutionLimits()),
    )
    if accepted:
        assert read_control(owner, "EXPLAIN SELECT * FROM `v`", explain=explain) == (
            (),
            (),
        )
        assert owner.control_events == [("explain_notes", (("Note", 1003),))]
    else:
        with pytest.raises(ExecutionError, match="MYSQL_CONTROL_WARNING"):
            read_control(owner, "EXPLAIN SELECT * FROM `v`", explain=explain)
    assert owner._controls == []


@pytest.mark.parametrize("damage", ("sql", "purpose", "arguments", "foreign_statement"))
def test_native_submission_is_bound_to_original_authority(tmp_path, damage):
    from pietto._project.project_execution_mysql_native import NativeStatement

    q = refined(tmp_path, "mysql", "G_emission_table_bag", "bag")
    owner = MySQLExecution(prepare_execution(q.original, access()))
    statement = NativeStatement(owner, q.original.rendered.sql, (), "query")
    owner._statement = statement
    owner._verify_submission(statement)
    if damage == "sql":
        statement.sql += b"; SELECT 1"
    elif damage == "purpose":
        statement.purpose = "page"
    elif damage == "arguments":
        statement.arguments = (1,)
    else:
        statement = NativeStatement(owner, q.original.rendered.sql, (), "query")
    with pytest.raises(ValueError):
        owner._verify_submission(statement)
    assert owner._connections == []


def test_unstarted_control_thread_can_be_cleaned_without_a_join_error():
    from types import SimpleNamespace
    from pietto._project.project_execution_mysql_control import MySQLControl

    owner = SimpleNamespace(attempt="offline", control_events=[])
    control = MySQLControl(owner)
    control.join()
    assert control.thread.ident is None and not control.thread.is_alive()


@pytest.mark.parametrize(
    "changed", ("server", "account", "role", "database", "epoch_shape")
)
def test_native_epoch_requires_same_server_and_explicit_control_context(
    monkeypatch, changed
):
    from types import SimpleNamespace
    from pietto._project import project_execution_mysql_context as context

    row = [
        7,
        11,
        "ACTIVE",
        "READ ONLY",
        "REPEATABLE READ",
        "NO",
        "server-a",
        "pietto_query@%",
        "NONE",
        "phase66",
    ]
    owner = SimpleNamespace(
        _connection=object(),
        _control_connection=object(),
        session_id=3,
        request=SimpleNamespace(access=access(), isolation="stable"),
        context=(None,) * 14 + ("server-a",),
    )
    monkeypatch.setattr(
        context, "read_control", lambda *args, **kwargs: ((), (tuple(row),))
    )
    assert context.native_epoch(owner, control=True) == tuple(row)
    if changed == "epoch_shape":
        row.pop()
    else:
        row[{"server": 6, "account": 7, "role": 8, "database": 9}[changed]] = "foreign"
    with pytest.raises(ExecutionError, match="MYSQL_TRANSACTION_OBSERVATION_REQUIRED"):
        context.native_epoch(owner, control=True)


def test_observed_source_eof_does_not_complete_early_consumer_delivery(tmp_path):
    q = refined(tmp_path, "mysql", "G_emission_table_bag", "bag")
    owner = MySQLExecution(prepare_execution(q.original, access()))
    owner._source = "EOF"
    owner._delivery = "OPEN"
    owner.close()
    assert owner.outcome.source == "EOF"
    assert owner.outcome.delivery == "INCOMPLETE"
    assert owner.outcome.transaction == "NOT_STARTED"


@pytest.mark.parametrize(
    "damage", ("false", "string", "access", "sources", "scope", "basis")
)
def test_explicit_deployment_declares_exact_access_and_source_scope(tmp_path, damage):
    from pietto._project.project_execution import MySQLDeploymentPremise

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    a = access()
    premise = MySQLDeploymentPremise(a, artifact.request.sources, ("phase66",))
    bad = {
        "false": False,
        "string": "accepted",
        "access": replace(premise, access=access()),
        "sources": replace(premise, sources=()),
        "scope": replace(premise, schemas=("elsewhere",)),
        "basis": replace(premise, basis="NATIVE_LOCKED"),
    }[damage]
    with pytest.raises(ExecutionError, match="MYSQL_DEPLOYMENT_PREMISE"):
        prepare_execution(artifact, a, mysql_deployment=bad)
    owner = MySQLExecution(prepare_execution(artifact, a, mysql_deployment=premise))
    object.__setattr__(premise, "schemas", ("elsewhere",))
    with pytest.raises(ExecutionError, match="EXECUTION_RESOURCE_IDENTITY"):
        owner.open()
    assert owner._connections == []


def test_explicit_premise_reaches_metadata_but_does_not_replace_qualification(
    tmp_path, monkeypatch
):
    from pietto._project.project_execution import MySQLDeploymentPremise
    from pietto._project import project_execution_mysql_context as context

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    a = access()
    owner = MySQLExecution(
        prepare_execution(
            artifact,
            a,
            mysql_deployment=MySQLDeploymentPremise(
                a, artifact.request.sources, ("phase66",)
            ),
        )
    )
    monkeypatch.setattr(owner, "_refresh", lambda: None)
    calls = []

    def metadata(_, sql, args=()):
        calls.append(sql)
        return (), ((1,),) if sql == "SELECT @@sql_quote_show_create" else ()

    monkeypatch.setattr(context, "read_control", metadata)
    with pytest.raises(ExecutionError, match="MYSQL_SOURCE_METADATA_REQUIRED"):
        context.qualify_sources(owner)
    assert len(calls) == 2 and "information_schema.TABLES" in calls[-1]
    assert owner._qualification is None
    assert owner.assurance["native_lifetime_protection"] == "NOT_DEMONSTRATED"
    assert owner.assurance["premise_compliance"] == "NOT_INDEPENDENTLY_VERIFIED"


def test_data_only_qualification_and_cross_attempt_grafts_never_create_live_authority(
    tmp_path,
):
    from pietto._project.project_execution_mysql_context import MySQLSourceQualification

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    first = MySQLExecution(prepare_execution(artifact, access()))
    second = MySQLExecution(prepare_execution(artifact, access()))
    data = MySQLSourceQualification(
        first, first.request, None, (), (), (), (), (), ((), (), ())
    )
    first._qualification = first._owned_qualification = data
    with pytest.raises(ExecutionError, match="MYSQL_SOURCE_QUALIFICATION_IDENTITY"):
        data.verify(first)
    second._qualification = second._owned_qualification = data
    with pytest.raises(ExecutionError, match="MYSQL_SOURCE_QUALIFICATION_IDENTITY"):
        data.verify(second)


def test_discovered_dependency_cannot_widen_accepted_scope(tmp_path, monkeypatch):
    from pietto._project.project_execution import MySQLDeploymentPremise
    from pietto._project import project_execution_mysql_context as context

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    a = access()
    owner = MySQLExecution(
        prepare_execution(
            artifact,
            a,
            mysql_deployment=MySQLDeploymentPremise(
                a, artifact.request.sources, ("phase66",)
            ),
        )
    )
    monkeypatch.setattr(owner, "_refresh", lambda: None)
    calls = []
    source = artifact.request.sources[0]

    def read(_, sql, args=()):
        calls.append((sql, args))
        if sql == "SELECT @@sql_quote_show_create":
            return (), ((1,),)
        if "information_schema.TABLES" in sql:
            return (), (("VIEW", None),)
        return (), (
            (
                source.name,
                "CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`%` SQL SECURITY DEFINER VIEW `"
                + source.name
                + "` AS select `t`.`id` AS `id` from `outside`.`t`",
                "utf8mb4",
                "utf8mb4_0900_bin",
            ),
        )

    monkeypatch.setattr(context, "read_control", read)
    with pytest.raises(ExecutionError, match="MYSQL_DEPLOYMENT_PREMISE_SCOPE"):
        context.qualify_sources(owner)
    assert len(calls) == 3 and not any(
        args and args[0] == "outside" for _, args in calls
    )
    assert owner._qualification is None


def test_deadline_after_commit_ack_preserves_commit_but_refuses_completion(
    tmp_path, monkeypatch
):
    import time
    from types import SimpleNamespace
    from pietto._project.project_execution import ExecutionLimits
    from pietto._project import project_execution_mysql as product

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    owner = MySQLExecution(
        prepare_execution(artifact, access(), limits=ExecutionLimits(seconds=1))
    )
    owner._started = time.monotonic()
    owner._transaction = "OPEN"
    owner._source, owner._delivery = "EOF", "COMPLETE"
    connection = SimpleNamespace(
        unread_result=False, in_transaction=True, shutdown=lambda: None
    )
    control = SimpleNamespace()
    owner._connection = owner._owned_connection = connection
    owner._control_connection = owner._owned_control_connection = control
    owner._transport = owner._control_transport = ("fixture-transport",)
    owner._epoch = owner._initial_epoch = (1, 2, "ACTIVE", "READ ONLY")
    owner._connections.append(connection)
    monkeypatch.setattr(product, "transport_state", lambda c: ("fixture-transport",))

    def commit(_, sql, arguments=(), **options):
        from pietto._project.project_execution_mysql_context import EPOCH_SQL

        if sql == EPOCH_SQL:
            assert options["connection"] is control and options["cleanup"] is True
            return (), (owner._initial_epoch,)
        assert sql == "COMMIT"
        owner._started = time.monotonic() - 2
        return (), ()

    monkeypatch.setattr(product, "read_control", commit)
    owner._finish(True)
    assert owner.outcome.transaction == "COMMIT_ACK"
    assert owner.outcome.delivery == "FAILED"
    failure = owner.outcome.primary
    assert failure is not None and failure.kind == "TimeoutError"
    assert owner.deadline_expired and owner.outcome.cancel_requested


def test_catalog_persistent_table_does_not_qualify_temporary_shadow(
    tmp_path, monkeypatch
):
    from pietto._project.project_execution import MySQLDeploymentPremise
    from pietto._project import project_execution_mysql_context as context
    from pietto._project.project_execution_source import identifier

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    a = access()
    owner = MySQLExecution(
        prepare_execution(
            artifact,
            a,
            mysql_deployment=MySQLDeploymentPremise(
                a, artifact.request.sources, ("phase66",)
            ),
        )
    )
    monkeypatch.setattr(owner, "_refresh", lambda: None)
    source = artifact.request.sources[0]

    def read(_, sql, args=()):
        if sql == "SELECT @@sql_quote_show_create":
            return (), ((1,),)
        if "information_schema.TABLES" in sql:
            return (), (("BASE TABLE", "InnoDB"),)
        assert sql.startswith("SHOW CREATE TABLE")
        return (), (
            (
                source.name,
                "CREATE TEMPORARY TABLE "
                + identifier(source.name, family="mysql")
                + " (`id` bigint) ENGINE=MyISAM",
            ),
        )

    monkeypatch.setattr(context, "read_control", read)
    with pytest.raises(ExecutionError, match="MYSQL_SOURCE_PERSISTENT_IDENTITY"):
        context.qualify_sources(owner)
    assert owner._qualification is None


def test_open_verification_is_inside_attempt_deadline_before_connect(
    tmp_path, monkeypatch
):
    from pietto._project.project_execution import ExecutionLimits
    from pietto._project import project_execution_mysql as product

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    owner = MySQLExecution(
        prepare_execution(artifact, access(), limits=ExecutionLimits(seconds=1))
    )
    ticks = iter((10.0, 12.0))
    from types import SimpleNamespace

    monkeypatch.setattr(product, "time", SimpleNamespace(monotonic=lambda: next(ticks)))
    monkeypatch.setattr(product, "verify_execution_request", lambda request: None)
    monkeypatch.setattr(
        product,
        "connect",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("late connection")),
    )
    with pytest.raises(TimeoutError, match="EXECUTION_DEADLINE"):
        owner.open()
    assert owner._connections == [] and owner.control_joined
    assert owner.outcome.delivery == "FAILED" and owner.deadline_expired


@pytest.mark.parametrize(
    "damage", ({"status_flag": 8193 | 8}, {"status_flag": 1}, {"warning_count": 1})
)
def test_native_eof_requires_readonly_epoch_without_warnings_or_more_results(damage):
    from pietto._project.project_execution_mysql_native import NativeStatement

    statement = object.__new__(NativeStatement)
    packet = dict(status_flag=8193, warning_count=0)
    statement._packet(packet)
    with pytest.raises(ExecutionError, match="MYSQL_PROTOCOL_STATUS"):
        statement._packet(dict(packet, **damage))


def test_cancel_after_request_verification_precedes_connection(tmp_path, monkeypatch):
    from pietto._project import project_execution_mysql as product

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    owner = MySQLExecution(prepare_execution(artifact, access()))
    verify = product.verify_execution_request

    def canceled(request):
        verify(request)
        owner.cancel()

    monkeypatch.setattr(product, "verify_execution_request", canceled)
    monkeypatch.setattr(
        product,
        "connect",
        lambda *a, **kw: (_ for _ in ()).throw(AssertionError("canceled connect")),
    )
    with pytest.raises(ExecutionError, match="EXECUTION_CANCELED"):
        owner.open()
    assert owner.outcome.delivery == "FAILED" and owner._connections == []


def test_registered_partial_control_connection_is_closed(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from pietto._project import project_execution_mysql as product

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    owner = MySQLExecution(prepare_execution(artifact, access()))
    closed = []

    def connection(owner_, *, control=False):
        handle = SimpleNamespace(
            connection_id=8 if control else 7,
            unread_result=False,
            shutdown=lambda: closed.append(control),
        )
        owner_._connections.append(handle)
        if control:
            owner_._control_connection = owner_._owned_control_connection = handle
            raise OSError("injected partial control handshake")
        owner_._connection = owner_._owned_connection = handle
        return handle

    monkeypatch.setattr(product, "connect", connection)
    with pytest.raises(OSError, match="partial control"):
        owner.open()
    assert closed == [True, False] and owner.control_joined
    assert owner.outcome.primary is not None and owner.outcome.delivery == "FAILED"


def test_internal_metadata_bytes_cannot_escape_execution_budget(tmp_path):
    from pietto._project.project_execution import ExecutionLimits

    artifact = refined(tmp_path, "mysql", "G_emission_table_bag", "bag").original
    owner = MySQLExecution(
        prepare_execution(artifact, access(), limits=ExecutionLimits(max_bytes=32))
    )
    with pytest.raises(ValueError, match="REFINEMENT_RESOURCE_LIMIT"):
        owner._charge_internal((("x" * 33,),))
    with pytest.raises(ExecutionError, match="EXECUTION_RESOURCE_LIMIT"):
        owner._charge_internal((("x" * 16, "x" * 16),))
