"""Offline S09 constructor and sibling authority boundaries."""

from dataclasses import replace
import pytest

from _pietto_phase68_slice5_cases import build
from _pietto_phase68_slice7_cases import manifest, case_preparation
from test_phase68_slice6_refinement import capabilities
from pietto._project.project_execution import (
    PostgresAccess,
    PostgresADBCDeploymentPremise,
    ExecutionError,
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
    }
    monkeypatch.setattr(importlib, "import_module", modules.__getitem__)
    monkeypatch.setattr(
        importlib.metadata,
        "version",
        lambda name: "25.0.1" if name == "pyarrow" else "1.12.0",
    )
    for key in tuple(os.environ):
        if key.startswith("PG") or key == "SSLKEYLOGFILE":
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
    options = parse_qs(urlparse(captured[0]["uri"]).query)
    assert options["sslmode"] == [sslmode] and options["sslcertmode"] == ["disable"]
    for key in ("sslrootcert", "sslcrl", "sslcert", "sslkey"):
        path = options[key][0]
        assert path.startswith("/dev/null/")
        with pytest.raises(NotADirectoryError):
            Path(path).stat()
    assert os.environ == before


def test_supplementary_oracle_checks_whole_values_not_just_count(artifact):
    import json
    import copy
    from _pietto_phase68_slice9_check import check_fixture_values
    from _pietto_phase68_slice5_cases import expected
    from _pietto_phase68_slice5_probe import oracle_values
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
    from test_phase68_slice9_postgres_source_assurance import catalog
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
    from test_phase68_slice9_postgres_source_assurance import catalog
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
