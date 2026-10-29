"""Offline S09 constructor and sibling authority boundaries."""

from dataclasses import replace
import pytest

from _pietto_execution_rows_cases import build
from _pietto_execution_guard_cases import manifest, case_preparation
from _pietto_execution_refinement import capabilities
from _pietto_sql_query_parameters import parameterized_case
from pietto._project.project_execution import (
    AMBIENT_TLS,
    ExecutionRequest,
    PostgresAccess,
    PostgresADBCDeploymentPremise,
    ExecutionError,
    ExecutionFailure,
    PostgresDeploymentPremise,
    prepare_compiled_execution,
    prepare_execution,
    request_state,
)
from pietto._project.project_execution_postgres import PostgresExecution
from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
from pietto._project.project_guard_runtime import (
    prepare_guarded_execution,
    ObservedGuardRequest,
)
from pietto._project.project_guard_preparation import prepare_guarded_output
from pietto._project.project_refinement import prepare_refinement, TieRefinement
from pietto._project.project_refinement_enumeration import prepare_refined_execution


def access():
    return PostgresAccess(
        "127.0.0.1", 5432, "phase66", "pietto_query", "not-a-live-secret", "disable"
    )


@pytest.fixture(scope="module")
def artifact(tmp_path_factory):
    return build(
        tmp_path_factory.mktemp("s09-ordinary"),
        "postgres",
        "G_emission_table_bag",
        "bag",
    ).artifact


def test_explicit_route_and_premise_preserve_rows(artifact):
    a = access()
    from pietto._project.project_result_output import prepare_output

    old = prepare_execution(artifact, a, output=prepare_output(artifact))
    assert PostgresExecution(old).request is old
    with pytest.raises(ExecutionError, match="EXECUTION_TARGET"):
        PostgresADBCExecution(old)
    with pytest.raises(ExecutionError, match="PREMISE_REQUIRED"):
        prepare_execution(artifact, a, route="postgres_adbc")
    premise = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    request = prepare_execution(
        artifact, a, route="postgres_adbc", postgres_adbc_deployment=premise
    )
    owner = PostgresADBCExecution(request)
    assert (
        owner.request is request
        and owner._connection is None
        and owner._database is None
    )
    with pytest.raises(ExecutionError, match="EXECUTION_TARGET"):
        PostgresExecution(request)
    assert "not-a-live-secret" not in repr(request)


def test_a_parameterized_template_is_refused_before_any_connection(tmp_path):
    body = "query result(low: Int):\n    from rows\n    where id > low\n"
    body += "    select:\n        display_text = text\n"
    _, outcome = parameterized_case(tmp_path, "postgres", body)
    assert outcome.status == "VERIFIED"
    a = access()
    premise = PostgresADBCDeploymentPremise(
        a, outcome.artifact.request.sources, ("public", "pg_catalog")
    )
    # No live binder exists for a header parameter yet.
    with pytest.raises(ExecutionError, match="EXECUTION_PRODUCER_NOT_DELIVERED"):
        prepare_execution(
            outcome.artifact, a, route="postgres_adbc", postgres_adbc_deployment=premise
        )


def test_compiled_adbc_uses_its_fresh_route_bound_premise(artifact):
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
    )

    root = build_compiled(artifact).root
    template = prepare_compiled_template(root)
    values = tuple(slot.original.site.position.literal.value for slot in template.slots)
    binding = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    a = access()
    premise = PostgresADBCDeploymentPremise(
        a, binding.artifact.request.sources, ("public", "pg_catalog")
    )
    request = prepare_compiled_execution(
        binding,
        a,
        route="postgres_adbc",
        postgres_adbc_deployment=premise,
    )
    assert type(request) is ExecutionRequest
    assert request.route == "postgres_adbc"
    assert request.postgres_adbc_deployment is premise
    assert request.postgres_deployment is None
    with pytest.raises(
        ExecutionError, match="POSTGRES_ADBC_DEPLOYMENT_PREMISE_REQUIRED"
    ):
        prepare_compiled_execution(binding, a, route="postgres_adbc")

    rows = PostgresDeploymentPremise(
        a, binding.artifact.request.sources, ("public", "pg_catalog"), "postgres_rows"
    )
    row_request = prepare_compiled_execution(
        binding, a, route="postgres_rows", postgres_deployment=rows
    )
    assert type(row_request) is ExecutionRequest
    assert row_request.postgres_deployment is rows


def test_guard_and_page_statements_send_each_parameter_with_its_type(tmp_path):
    """Each `$n` of a guard statement and of a refinement page of a query with
    parameters has its declared type, also for a NULL; controls are Int."""
    from types import SimpleNamespace

    from _pietto_execution_guard_cases import DIRECT, planned
    from pietto._project.project_compiled_build import build_compiled
    from pietto._project.project_execution import ExecutionLimits
    from pietto._project.project_execution_template import (
        bind_values,
        prepare_compiled_template,
    )
    from pietto._project.project_guard_preparation import prepare_guarded
    from pietto._project.project_guard_program import prepare_program, statement_for
    from pietto._project.project_guard_rendering import render_guard
    from pietto._project.project_refinement import prepare_compiled_refinement
    from pietto._project.project_refinement_enumeration import Enumeration

    body = DIRECT.replace(
        "query result:", "query result(low: Int, label: Text | None):"
    ).replace(
        "on lhs.id == r.id", "on lhs.id == r.id and lhs.id > low and r.key != label"
    )
    prepared = prepare_guarded(
        *planned(tmp_path, body=body, policy="bind_safe_literals", wide_text=True)
    )
    refined = prepare_refinement(
        prepared.artifact,
        capabilities(prepared.artifact),
        policy=TieRefinement(),
        output=prepare_guarded_output(prepared),
    )
    template = prepare_compiled_template(
        build_compiled(prepared.artifact, guarded=prepared, refinement=refined).root
    )
    bound = bind_values(template, (), tuple(zip(template.parameters, (3, None))))
    refinement = prepare_compiled_refinement(
        bound.artifact, binding=bound, guarded=bound.guarded
    )
    owner = object.__new__(PostgresADBCExecution)
    for program in (
        prepare_program(bound.guarded, binding=bound),
        prepare_program(bound.guarded, binding=bound, refinement=refinement),
    ):
        native = render_guard(statement_for(program, "guard"))
        vars(owner).update(refined_request=None, guards=SimpleNamespace(native=native))
        assert owner._parameters("guard") == (
            native.sql,
            (3, None, 1, 1),
            ("Int", "Text", "Int", "Int"),
        )
    # The first page: its row limit (the default 256) is the last `$n`.
    enumeration = object.__new__(Enumeration)
    vars(enumeration).update(
        verify=lambda: None,
        query=refinement,
        limits=ExecutionLimits(),
        _frontier=None,
        _pending=None,
        _complete=False,
        _pages=0,
    )
    page = enumeration.request_page()
    vars(owner).update(
        refined_request=SimpleNamespace(refinement=refinement), last_page=page
    )
    assert owner._parameters("page") == (
        page.native.sql,
        (3, None, 256),
        ("Int", "Text", "Int"),
    )


@pytest.mark.parametrize(
    "change", ("access", "roots", "schemas", "route", "basis", "mutable")
)
def test_premise_is_exact_not_ambient(artifact, change):
    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    edits = {
        "access": {"access": access()},
        "roots": {"sources": ()},
        "schemas": {"schemas": ("elsewhere",)},
        "route": {"route": "postgres_rows"},
        "basis": {"basis": "VERIFIED"},
        "mutable": {"schemas": ["public", "pg_catalog"]},
    }
    p = replace(p, **edits[change])
    with pytest.raises(ExecutionError, match="PREMISE_SCOPE"):
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )


def test_premise_mutation_after_acceptance(artifact):
    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    r = prepare_execution(
        artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
    )
    owner = PostgresADBCExecution(r)
    before = request_state(r)
    object.__setattr__(p, "schemas", ("public", "other", "pg_catalog"))
    assert request_state(r) != before
    with pytest.raises(ExecutionError, match="REQUEST_CHANGED"):
        owner._verify()


@pytest.mark.parametrize(
    "name",
    (
        "no_request",
        "bag_one",
        "right_limit_0",
        "path_whole_positive",
        "refined_pages",
        "refined_violation_outside_page",
    ),
)
def test_original_guarded_entry_shapes_need_same_explicit_premise(tmp_path, name):
    case = next(c for c in manifest() if c["name"] == name)
    preparation = case_preparation(tmp_path, "postgres", case)
    a = access()
    p = PostgresADBCDeploymentPremise(
        a, preparation.artifact.request.sources, ("public", "pg_catalog")
    )
    q = None
    if case["options"].get("refined"):
        q = prepare_refinement(
            preparation.artifact,
            capabilities(preparation.artifact),
            policy=TieRefinement(),
            output=prepare_guarded_output(preparation),
        )
    with pytest.raises(ExecutionError, match="PREMISE_REQUIRED"):
        prepare_guarded_execution(
            preparation,
            a,
            refinement=q,
            route="postgres_adbc",
            allow_guard_sql=False,
            isolation="serializable",
        )
    r = prepare_guarded_execution(
        preparation, a, refinement=q, route="postgres_adbc", postgres_adbc_deployment=p
    )
    owner = PostgresADBCExecution(r)
    assert owner.guarded_request is r and owner._connection is None
    with pytest.raises(ValueError):
        PostgresADBCExecution(ObservedGuardRequest(r.program))


def test_unguarded_refinement_uses_same_access(artifact):
    from pietto._project.project_result_output import prepare_output

    output = prepare_output(artifact)
    q = prepare_refinement(
        artifact, capabilities(artifact), policy=TieRefinement(), output=output
    )
    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    r = prepare_refined_execution(
        q, a, route="postgres_adbc", postgres_adbc_deployment=p
    )
    assert PostgresADBCExecution(r).refined_request is r


def test_native_statement_retains_only_live_handles():
    from types import SimpleNamespace
    from threading import RLock
    from pietto._project.project_execution_postgres_adbc_native import NativeStatement

    calls = []
    owner = SimpleNamespace(_statements=[], _gate=RLock(), _active=None)
    statement = NativeStatement(owner, b"SELECT 1", (), (), "control", copy=False)
    statement.native = SimpleNamespace(close=lambda: calls.append("close"))
    assert owner._statements == [statement]
    statement.close()
    statement.close()
    assert calls == ["close"] and owner._statements == []


def test_unknown_transaction_is_not_rolled_back_as_original(artifact):
    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    r = prepare_execution(
        artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
    )
    owner = PostgresADBCExecution(r)
    owner._transaction = "OPEN"
    owner._failed(ExecutionError("POSTGRES_ADBC_TRANSACTION_CHANGED"), "context")
    assert owner.outcome.transaction == "UNKNOWN"


def test_canceled_preparation_never_opens_native_connection(artifact, monkeypatch):
    from pietto._project import project_execution_postgres_adbc as product

    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    request = prepare_execution(
        artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
    )
    owner = PostgresADBCExecution(request)
    original = product.verify_execution_request

    def verify(value):
        original(value)
        owner.cancel()

    monkeypatch.setattr(product, "verify_execution_request", verify)
    with pytest.raises(ExecutionError, match="EXECUTION_CANCELED"):
        owner.open()
    assert (
        owner._connection is None and owner._database is None and owner.control_joined
    )


def test_copy_checkpoint_is_consumed_before_context_and_rechecks_status(
    artifact, monkeypatch
):
    from pietto._project import project_execution_postgres_adbc as product

    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    owner = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )
    )
    pending = object()
    owner._copy_checkpoint = pending
    owner.context = ("original",)
    checks = []

    def status(*, completed_copy=None):
        checks.append(completed_copy)
        assert owner._copy_checkpoint is None
        return "active" if completed_copy is pending else "intrans"

    monkeypatch.setattr(owner, "_check_connection", status)
    monkeypatch.setattr(product, "native_context", lambda o: (("original",), object()))
    owner._refresh()
    assert checks == [pending, None] and owner._copy_status == ("active", "intrans")
    owner._refresh()
    assert checks[-2:] == [None, None]


def test_finalization_timeout_retires_delivery_but_allows_cleanup_retry(artifact):
    from types import SimpleNamespace

    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    owner = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )
    )
    live = [True]
    calls = []
    owner._timer = SimpleNamespace(
        cancel=lambda: None, join=lambda **kw: None, is_alive=lambda: live[0]
    )
    owner._owned_connection = SimpleNamespace(close=lambda: calls.append("connection"))
    owner._owned_database = SimpleNamespace(close=lambda: calls.append("database"))
    owner._transaction = "OPEN"
    owner.close()
    assert not owner._closed and not owner._finalizing and owner._retired
    assert calls == [] and owner.outcome.transaction == "UNKNOWN"
    with pytest.raises(ExecutionError, match="EXECUTION_RETIRED"):
        next(owner)
    with pytest.raises(ExecutionError, match="EXECUTION_RETIRED"):
        owner._checkpoint()
    live[0] = False
    owner.close()
    assert calls == ["connection", "database"] and owner._closed
    assert owner.outcome.transaction == "UNKNOWN"


def test_adbc_terminal_winner_and_late_cancel_are_fixed(artifact):
    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    owner = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )
    )
    assert owner.cancel() == {
        "requested": True,
        "sent": False,
        "observed": False,
        "late": False,
    }
    owner._failed(ExecutionError("EXECUTION_CANCELED"), "query")
    assert owner._closed and owner._terminal == "CANCELLED"
    assert owner.outcome.cancel_requested is True
    assert owner.cancel() == {
        "requested": False,
        "sent": False,
        "observed": False,
        "late": True,
    }

    other = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )
    )
    assert other._claim_terminal("FAILED")
    other._deadline()
    assert other._terminal == "FAILED" and other.deadline_expired is False

    deadline = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )
    )
    assert deadline._deadline() is None
    assert deadline._terminal == "DEADLINE" and deadline.deadline_expired is True
    assert deadline.outcome.cancel_requested is True


def test_adbc_finalization_records_and_reraises_keyboard_interrupt(artifact):
    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )

    class InterruptingGuards:
        def close(self):
            raise KeyboardInterrupt()

    owner = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )
    )
    owner.guards = InterruptingGuards()
    with pytest.raises(KeyboardInterrupt):
        owner.close()
    assert owner._closed
    assert [(e.phase, e.kind) for e in owner._cleanup_errors] == [
        ("guard_close", "KeyboardInterrupt")
    ]

    primary = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )
    )
    primary._primary = ExecutionFailure("query", "KeyboardInterrupt")
    primary.guards = InterruptingGuards()
    try:
        raise KeyboardInterrupt()
    except KeyboardInterrupt:
        primary._finish(False)
    assert primary._closed
    assert [(e.phase, e.kind) for e in primary._cleanup_errors] == [
        ("guard_close", "KeyboardInterrupt")
    ]


def test_page_primary_survives_failed_batch_close(artifact, monkeypatch):
    from types import SimpleNamespace

    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    owner = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )
    )
    primary = ValueError("injected page verification failure")

    def close():
        raise OSError("injected batch close failure")

    def verify():
        raise primary

    owner.enumeration = SimpleNamespace(
        progress=(0, 0, False),
        request_page=lambda: SimpleNamespace(size=2),
        check_page=lambda *a, **kw: SimpleNamespace(rows=((1,),)),
    )
    owner._payloads = SimpleNamespace(accept=lambda rows: SimpleNamespace(close=close))
    owner._statement = SimpleNamespace(
        fetch=lambda size: ((1,),), exhausted=True, bytes=8
    )
    monkeypatch.setattr(owner, "_submit", lambda *a: ())
    monkeypatch.setattr(owner, "_charge_internal", lambda *a: None)
    monkeypatch.setattr(owner, "_verify", verify)
    with pytest.raises(ValueError) as caught:
        owner._next_page()
    assert caught.value is primary
    assert [(e.phase, e.kind) for e in owner._cleanup_errors] == [
        ("batch_close", "OSError")
    ]


def test_raw_retention_accounts_for_delivery_guards_and_other_statement(artifact):
    from types import SimpleNamespace
    import time

    a = access()
    p = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    owner = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=p
        )
    )
    owner._started = time.monotonic()
    limit = owner.request.limits.max_bytes
    owner._internal_bytes = limit - 60
    owner._guard_bytes = 10
    owner._payloads = SimpleNamespace(bytes=10)
    owner._statement = SimpleNamespace(bytes=20)
    # Data allocation replaces its own previous raw count, but a context command
    # must additionally account for the still-retained data statement.
    owner._check_total(40, owner._statement)
    with pytest.raises(ExecutionError, match="RESOURCE_LIMIT"):
        owner._check_total(41, owner._statement)
    owner._check_total(20, object())
    with pytest.raises(ExecutionError, match="RESOURCE_LIMIT"):
        owner._check_total(21, object())


@pytest.mark.parametrize("sslmode", ("require", "disable"))
def test_explicit_tls_files_cannot_fall_back_to_user_home(
    tmp_path, monkeypatch, sslmode
):
    from types import SimpleNamespace
    from urllib.parse import urlparse, parse_qs
    from pathlib import Path
    from pietto._project import project_compiled_loading as loading
    from pietto._project import project_execution_postgres_adbc_native as native
    import importlib
    import importlib.metadata
    import os

    package = tmp_path / "driver"
    package.mkdir()
    (package / "libadbc_driver_postgresql.so").touch()
    captured = []

    def database(**options):
        captured.append(options)
        return object()

    modules = {
        "adbc_driver_postgresql": SimpleNamespace(
            __file__=str(package / "__init__.py")
        ),
        "adbc_driver_manager": SimpleNamespace(
            AdbcDatabase=database,
            AdbcConnection=lambda database: SimpleNamespace(
                get_option=lambda key: "idle"
            ),
        ),
        "pyarrow": object(),
        "adbc_driver_manager._reader": SimpleNamespace(AdbcRecordBatchReader=object()),
    }

    def version(name):
        return "26.0.0" if name == "pyarrow" else "1.13.0"

    monkeypatch.setattr(importlib, "import_module", modules.__getitem__)
    monkeypatch.setattr(importlib.metadata, "version", version)
    # CONTROLLED as in the S18 decision table: each fake module counts as
    # recorded by its own pinned distribution for the shared owner check.
    monkeypatch.setattr(
        loading,
        "owner_versions",
        lambda distribution, module: frozenset({version(distribution)}),
    )
    for key in tuple(os.environ):
        if key.startswith("PG") or key in AMBIENT_TLS:
            monkeypatch.delenv(key)
    before = dict(os.environ)
    owner = SimpleNamespace(
        request=SimpleNamespace(access=replace(access(), sslmode=sslmode)),
        _remaining=lambda: 10,
        _checkpoint=lambda: None,
        control_events=[],
        attempt="offline",
    )
    native.connect(owner)
    # Result streams are read through the pinned manager's own reader.
    assert (
        owner._stream_reader
        is modules["adbc_driver_manager._reader"].AdbcRecordBatchReader
    )
    options = parse_qs(urlparse(captured[0]["uri"]).query)
    assert options["sslmode"] == [sslmode] and options["sslcertmode"] == ["disable"]
    assert options["require_auth"] == ["scram-sha-256"]
    assert options["channel_binding"] == [
        "require" if sslmode == "require" else "disable"
    ]
    for key in ("sslrootcert", "sslcrl", "sslcert", "sslkey"):
        path = options[key][0]
        assert path.startswith("/dev/null/")
        with pytest.raises(NotADirectoryError):
            Path(path).stat()
    assert os.environ == before


@pytest.mark.parametrize("name", AMBIENT_TLS)
def test_adbc_refuses_shared_tls_ambient_before_driver_loads(monkeypatch, name):
    from types import SimpleNamespace
    from pietto._project import project_execution_postgres_adbc_native as native

    def forbidden():
        raise AssertionError("ADBC driver loaded despite a refused ambient input")

    monkeypatch.setattr(native, "drivers", forbidden)
    monkeypatch.setenv(name, "set")
    owner = SimpleNamespace(request=SimpleNamespace(access=access()))
    with pytest.raises(ExecutionError, match="^EXECUTION_AMBIENT_CONNECTION_PROFILE$"):
        native.connect(owner)


def test_supplementary_oracle_checks_whole_values_not_just_count(artifact):
    import json
    import copy
    from _pietto_execution_adbc_check import check_fixture_values
    from _pietto_execution_rows_cases import expected
    from _pietto_execution_rows_probe import oracle_values
    from pietto._project.project_sql_emission import (
        EmissionOutcome,
        serialize_project_sql_emission,
    )

    public = json.loads(
        serialize_project_sql_emission(EmissionOutcome("VERIFIED", (), artifact))
    )
    raw, _ = expected("postgres", "G_emission_table_bag", "bag")
    record = {"public": public, "rows": oracle_values(raw, public["columns"])}
    check_fixture_values(record)
    changed = copy.deepcopy(record)
    changed["rows"][0][0] = {"kind": "text", "value": "wrong but same row count"}
    with pytest.raises(ValueError, match="FIXTURE_FULL_VALUES"):
        check_fixture_values(changed)
    with pytest.raises(ValueError, match="FIXTURE_FULL_VALUES"):
        check_fixture_values(changed, partial=True)


@pytest.mark.parametrize("commit", (False, True))
def test_finalization_verifies_initial_context_before_transaction_command(
    artifact, monkeypatch, commit
):
    from types import SimpleNamespace
    from _pietto_execution_postgres_source import catalog
    from pietto._project import project_execution_postgres_adbc as product

    a = access()
    premise = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    owner = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=premise
        )
    )
    context, _, _ = catalog()
    owner.context = owner._initial_context = context
    owner._transaction = "OPEN"
    calls = []
    owner._owned_connection = SimpleNamespace(
        close=lambda: calls.append("connection.close")
    )
    monkeypatch.setattr(owner, "_check_connection", lambda: calls.append("status"))

    def read(o, sql, **kwargs):
        assert o is owner and kwargs["finalizing"] is True
        calls.append(sql)
        return (), (context,) if sql == product.CONTEXT_SQL else (), None

    monkeypatch.setattr(product, "read_control", read)
    owner._finish(commit)
    command = "COMMIT" if commit else "ROLLBACK"
    assert calls == [
        "status",
        product.CONTEXT_SQL,
        "status",
        command,
        "connection.close",
    ]
    assert owner._transaction == command + "_ACK" and owner._closed


@pytest.mark.parametrize(
    "reason",
    ("EXECUTION_REQUEST_CHANGED", "EXECUTION_CANCELED", "POSTGRES_ADBC_NATIVE_CONTEXT"),
)
def test_failure_cannot_attribute_foreign_rollback_to_original_attempt(
    artifact, monkeypatch, reason
):
    from types import SimpleNamespace
    from _pietto_execution_postgres_source import catalog
    from pietto._project import project_execution_postgres_adbc as product

    a = access()
    premise = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    owner = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=premise
        )
    )
    original, _, _ = catalog()
    current = original[:7] + ("43",) + original[8:]
    owner._initial_context = original
    owner.context = current  # Coordinated copied state does not replace the anchor.
    owner._transaction = "OPEN"
    calls = []
    owner._owned_connection = SimpleNamespace(
        close=lambda: calls.append("connection.close")
    )
    monkeypatch.setattr(owner, "_check_connection", lambda: None)

    def read(o, sql, **kwargs):
        calls.append(sql)
        return (), (current,), None

    monkeypatch.setattr(product, "read_control", read)
    owner._failed(ExecutionError(reason), "original_failure")
    assert calls == [product.CONTEXT_SQL, "connection.close"]
    assert owner._transaction == "UNKNOWN" and owner._closed
    primary = owner.outcome.primary
    assert primary is not None
    assert primary.phase == "original_failure"
    assert owner.outcome.cleanup_failures[0].phase == "transaction"


def test_finalization_refuses_an_unestablished_transaction_identity(
    artifact, monkeypatch
):
    from types import SimpleNamespace
    from pietto._project import project_execution_postgres_adbc as product

    a = access()
    premise = PostgresADBCDeploymentPremise(
        a, artifact.request.sources, ("public", "pg_catalog")
    )
    owner = PostgresADBCExecution(
        prepare_execution(
            artifact, a, route="postgres_adbc", postgres_adbc_deployment=premise
        )
    )
    owner._transaction = "OPEN"
    calls = []
    owner._owned_connection = SimpleNamespace(
        close=lambda: calls.append("connection.close")
    )
    monkeypatch.setattr(
        product, "read_control", lambda *a, **kw: calls.append("unexpected SQL")
    )
    owner._finish(False)
    assert calls == ["connection.close"] and owner._transaction == "UNKNOWN"
