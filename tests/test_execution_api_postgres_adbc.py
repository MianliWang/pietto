"""Public PostgreSQL ADBC route checks that need no PostgreSQL service."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

import _pietto_execution_api as api
import pietto.execution as execution
from pietto._project import project_execution as ex
from pietto._project import project_public_execution as composition
from pietto.execution import _errors as errors
from pietto.execution import _handle


PASSWORD = "pw-adbc-never-shown"
ACCESS = execution.PostgresAccess("127.0.0.1", 5432, "app", "reader", PASSWORD)
PREMISE = execution.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))


@pytest.fixture(scope="module")
def query(tmp_path_factory):
    return execution.compile_query(
        api.write_example(tmp_path_factory.mktemp("execution-adbc-public")),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


def test_adbc_route_dispatches_one_private_owner_with_fresh_public_inputs(
    query, monkeypatch
):
    captured = {}
    owner = SimpleNamespace(attempt="adbc-attempt")

    def prepare(template, access, **options):
        captured.update(template=template, access=access, options=options)
        return owner

    monkeypatch.setattr(composition, "prepare_postgres_adbc_attempt", prepare)
    handle = execution.execute(
        query,
        route="postgres_adbc",
        access=ACCESS,
        premise=PREMISE,
        values=(7,),
    )
    assert handle.route == "postgres_adbc" and handle.attempt == "adbc-attempt"
    assert type(captured["access"]) is ex.PostgresAccess
    assert captured["access"] == ex.PostgresAccess(
        "127.0.0.1", 5432, "app", "reader", PASSWORD, "require"
    )
    assert captured["options"] == {
        "schemas": ("fixture", "pg_catalog"),
        "limits": ex.ExecutionLimits(),
        "isolation": "stable",
        "values": (7,),
    }


def test_adbc_requires_the_existing_postgres_public_access_and_premise(query):
    with pytest.raises(execution.RequestRejected) as access:
        execution.execute(
            query,
            route="postgres_adbc",
            access=execution.MySQLAccess(
                "db", 3306, "app", "reader", PASSWORD, "/ca.pem", "reader"
            ),
            premise=PREMISE,
        )
    with pytest.raises(execution.RequestRejected) as premise:
        execution.execute(
            query,
            route="postgres_adbc",
            access=ACCESS,
            premise=execution.MySQLDeploymentPremise(schemas=("fixture",)),
        )
    assert (access.value.code, access.value.detail) == (
        "PIE-R1002",
        "PUBLIC_ACCESS_TYPE",
    )
    assert (premise.value.code, premise.value.detail) == (
        "PIE-R1002",
        "PUBLIC_PREMISE_TYPE",
    )


def test_adbc_bridge_binds_the_exact_private_premise_without_driver_io(query):
    selected = {
        "adbc_driver_manager",
        "adbc_driver_postgresql",
        "pyarrow",
    }
    before = {module.partition(".")[0] for module in sys.modules}
    handle = execution.execute(
        query, route="postgres_adbc", access=ACCESS, premise=PREMISE
    )
    request = handle._owner.request
    private = request.postgres_adbc_deployment
    assert private is not None
    assert (
        request.route,
        request.postgres_deployment,
        request.mysql_deployment,
        private.access is request.access,
        private.sources is request.binding.artifact.request.sources,
        private.schemas,
        private.route,
        private.basis,
    ) == (
        "postgres_adbc",
        None,
        None,
        True,
        True,
        ("fixture", "pg_catalog"),
        "postgres_adbc",
        "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE",
    )
    after = {module.partition(".")[0] for module in sys.modules}
    assert not (after - before) & selected


def test_adbc_bridge_does_not_reimport_after_a_legitimate_arrow_consumer(query):
    pyarrow = pytest.importorskip("pyarrow")

    assert pyarrow.__name__ == "pyarrow"
    before = set(sys.modules)
    execution.execute(query, route="postgres_adbc", access=ACCESS, premise=PREMISE)
    assert not {
        name
        for name in set(sys.modules) - before
        if name.partition(".")[0]
        in {"adbc_driver_manager", "adbc_driver_postgresql", "pyarrow"}
    }


def test_adbc_ambient_refusal_precedes_private_owner_import(monkeypatch):
    calls = []

    def refuse(prefixes):
        calls.append(prefixes)
        raise ex.ExecutionError("EXECUTION_AMBIENT_CONNECTION_PROFILE")

    monkeypatch.setattr(ex, "refuse_ambient", refuse)
    with pytest.raises(ex.ExecutionError, match="EXECUTION_AMBIENT_CONNECTION_PROFILE"):
        composition.prepare_postgres_adbc_attempt(
            object(),
            object(),
            schemas=("fixture",),
            limits=object(),
            isolation="stable",
        )
    assert calls == [("PG",)]


@pytest.mark.parametrize(
    "word",
    ("POSTGRES_ADBC_DRIVER_PROFILE", "POSTGRES_ADBC_DRIVER_LIBRARY"),
)
def test_adbc_driver_refusals_reuse_the_pinned_driver_profile_code(word):
    refusal = errors.attempt_failure(
        ex.ExecutionError(word), phase="open", deadline=False, connected=False
    )
    assert (refusal.code, refusal.detail) == ("PIE-R2002", word)


def test_adbc_retryable_cleanup_failure_is_publicly_failed_before_closed():
    owner = SimpleNamespace(cleanup="FAILED_REMOTE_UNOBSERVED", delivery="FAILED")
    assert _handle._end(
        False, False, None, errors.failure("PIE-R3003"), owner, False
    ) == ("FAILED_REMOTE_UNOBSERVED")


def test_adbc_cleanup_timeout_is_publicly_terminal_until_explicit_retry(query):
    handle = execution.execute(
        query, route="postgres_adbc", access=ACCESS, premise=PREMISE
    )
    owner = handle._owner
    calls = []
    live = [True]
    owner._timer = SimpleNamespace(
        cancel=lambda: None, join=lambda **kwargs: None, is_alive=lambda: live[0]
    )
    owner._owned_connection = SimpleNamespace(close=lambda: calls.append("connection"))
    owner._owned_database = SimpleNamespace(close=lambda: calls.append("database"))
    owner._transaction = "OPEN"
    owner._primary = ex.ExecutionFailure("original_failure", "ValueError")

    handle.close()
    assert not handle.closed and owner._retired
    assert handle.outcome.end == "FAILED_REMOTE_UNOBSERVED"
    primary = handle.outcome.primary
    assert primary is not None
    assert (primary.code, primary.phase) == (
        "PIE-R3999",
        "original_failure",
    )
    with pytest.raises(execution.HandleMisuse, match="PIE-R4001"):
        next(handle)
    with pytest.raises(execution.HandleMisuse, match="PIE-R4001"):
        handle.__enter__()

    live[0] = False
    handle.close()
    assert handle.closed and calls == ["connection", "database"]
    assert handle.outcome.transaction == "UNKNOWN"
    primary = handle.outcome.primary
    assert primary is not None
    assert (primary.code, primary.phase) == (
        "PIE-R3999",
        "original_failure",
    )
