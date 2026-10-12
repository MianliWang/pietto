"""PIE-R error surface of the public execution alpha: the documented code set,
the deterministic classification of private refusals and driver exceptions,
fixed-vocabulary text without credentials, and no exception chaining."""

from __future__ import annotations

import copy
import os
from pathlib import Path
import pickle
import re
import socket
import traceback

import pytest

import _pietto_execution_api as api
import pietto.execution as execution
from pietto._project import project_arrow_result
from pietto._project import project_execution as ex
from pietto._project.project_compiled_schema import CompiledError
from pietto._project.project_execution_template import BindingError
from pietto._project.project_result_contract import ResultError
from pietto.execution import _errors as errors

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "pw-3a9d71-never-shown"
HOST = "host-51b0.invalid"


class DriverError(Exception):
    """A foreign driver exception whose message must never be read."""

    def __init__(self, message, sqlstate=None):
        super().__init__(message)
        self.sqlstate = sqlstate


def test_documented_runtime_codes_are_exactly_the_implemented_codes():
    document = (ROOT / "docs/spec/diagnostics.md").read_text(encoding="utf-8")
    section = document.split("## Runtime Diagnostics", 1)[1]
    rows = re.findall(r"^\| `(PIE-R[0-9]{4})` \| ([A-Z_]+): ", section, re.M)
    assert dict(rows) == {
        code: category for code, (category, _) in errors.CODES.items()
    }
    assert len(rows) == len(set(code for code, _ in rows))
    assert set(re.findall(r"`(PIE-R[0-9]{4})`", document)) == set(errors.CODES)
    assert len({category for category, _ in errors.CODES.values()}) == len(errors.CODES)


@pytest.mark.parametrize(
    "error,code",
    (
        (ex.ExecutionError("POSTGRES_DEPLOYMENT_PREMISE_REQUIRED"), "PIE-R1001"),
        (ex.ExecutionError("EXECUTION_ACCESS_PROFILE"), "PIE-R1002"),
        (ex.ExecutionError("POSTGRES_DEPLOYMENT_PREMISE_SCOPE"), "PIE-R1002"),
        (ex.ExecutionError("COMPILED_FRESH_PROFILE_REQUIRED"), "PIE-R1003"),
        (ex.ExecutionError("UNFULFILLED_RUNTIME_OBLIGATION"), "PIE-R1004"),
        (BindingError("BINDING_VALUE:0:Int"), "PIE-R1006"),
        (BindingError("BINDING_VALUE:1:Text"), "PIE-R1006"),
        (BindingError("BINDING_SLOTS"), "PIE-R1006"),
        (BindingError("BINDING_INVALID"), "PIE-R1004"),
        (CompiledError("COMPILED_EXPORT_SHAPE"), "PIE-R1004"),
        (ResultError("PRODUCER_UNSUPPORTED"), "PIE-R1004"),
        (ex.ExecutionError("COMPILED_COMPATIBILITY"), "PIE-R1005"),
        (CompiledError("COMPILED_CODE_ORIGIN"), "PIE-R1005"),
        (ex.ExecutionError("SOMETHING_NEW"), "PIE-R1999"),
        (DriverError("x"), "PIE-R1999"),
        (ValueError("lower case is no category"), "PIE-R1999"),
    ),
)
def test_request_refusals_are_classified_by_their_category_word(error, code):
    refusal = errors.request_failure(error)
    assert refusal.code == code
    assert refusal.category == errors.CODES[code][0]


@pytest.mark.parametrize(
    "error,code",
    (
        (CompiledError("PUBLIC_BUNDLE_CODE_IDENTITY"), "PIE-R1005"),
        (CompiledError("COMPILED_CODE_ORIGIN"), "PIE-R1005"),
        (CompiledError("COMPILED_HANDOFF"), "PIE-R1008"),
        (CompiledError("PUBLIC_BUNDLE_SIZE"), "PIE-R1002"),
        (CompiledError("COMPILED_BYTE_LIMIT"), "PIE-R1008"),
        (CompiledError("COMPILED_CONTENT_PIN"), "PIE-R1007"),
        (CompiledError("PUBLIC_BUNDLE_UNSUPPORTED"), "PIE-R1004"),
        (CompiledError("COMPILED_COMPATIBILITY"), "PIE-R1008"),
        (CompiledError("COMPILED_JSON"), "PIE-R1008"),
        (CompiledError("COMPILED_DEPTH_LIMIT"), "PIE-R1008"),
        (CompiledError("COMPILED_CANONICAL"), "PIE-R1008"),
        (BindingError("COMPILED_COMPATIBILITY"), "PIE-R1999"),
        (ValueError("COMPILED_JSON"), "PIE-R1999"),
        (CompiledError("lower case is no category"), "PIE-R1999"),
        (DriverError("x"), "PIE-R1999"),
    ),
)
def test_bundle_refusals_are_classified_by_their_category_word(error, code):
    """load_bundle's acceptance stage: the code identity, the payload's size,
    the pin, then any other loader refusal of the bytes."""
    refusal = errors.bundle_failure(error)
    assert (refusal.code, refusal.category) == (code, errors.CODES[code][0])
    assert refusal.cause == type(error).__name__


def test_value_and_bundle_refusal_text_is_fixed_vocabulary():
    for refusal, text in (
        (
            errors.request_failure(BindingError("BINDING_VALUE:0:Int")),
            "PIE-R1006 VALUE_REFUSED: the values do not fit the query's slots:"
            " their number differs, or a value's exact type or range is not its"
            " slot's (detail=BINDING_VALUE:0:Int, cause=BindingError)",
        ),
        (
            errors.bundle_failure(CompiledError("COMPILED_CONTENT_PIN")),
            "PIE-R1007 BUNDLE_CONTENT: the bundle bytes are not the bytes the"
            " expected pin names (detail=COMPILED_CONTENT_PIN, cause=CompiledError)",
        ),
    ):
        assert str(refusal) == text


@pytest.mark.parametrize(
    "error,facts,code",
    (
        (ex.ExecutionError("EXECUTION_DEPENDENCY_MISSING"), {}, "PIE-R2001"),
        (ResultError("ARROW_DEPENDENCY_MISSING"), {}, "PIE-R2001"),
        (ex.ExecutionError("EXECUTION_DRIVER_VERSION"), {}, "PIE-R2002"),
        (ex.ExecutionError("POSTGRES_DRIVER_LIBRARY"), {}, "PIE-R2002"),
        (ImportError("libpq.so.5: cannot open shared object file"), {}, "PIE-R2002"),
        (ex.ExecutionError("EXECUTION_AMBIENT_CONNECTION_PROFILE"), {}, "PIE-R2003"),
        (
            DriverError("connection refused", None),
            {"connected": False, "driver": True},
            "PIE-R2004",
        ),
        (DriverError("connection refused", None), {"connected": False}, "PIE-R3999"),
        (OSError("refused before the driver"), {"connected": False}, "PIE-R3999"),
        (RuntimeError("can't start new thread"), {"connected": False}, "PIE-R3999"),
        (ex.ExecutionError("EXECUTION_TARGET_VERSION"), {}, "PIE-R2005"),
        (ex.ExecutionError("EXECUTION_CONTEXT"), {}, "PIE-R2006"),
        (ex.ExecutionError("POSTGRES_TRANSACTION_CHANGED"), {}, "PIE-R2006"),
        (ex.ExecutionError("POSTGRES_SOURCE_NATIVE_CONTEXT"), {}, "PIE-R2006"),
        (ex.ExecutionError("POSTGRES_SOURCE_RLS_NOT_QUALIFIED"), {}, "PIE-R2007"),
        (ex.ExecutionError("POSTGRES_ADBC_DEPLOYMENT_PREMISE_SCOPE"), {}, "PIE-R2007"),
        (TimeoutError("EXECUTION_DEADLINE"), {}, "PIE-R3001"),
        (DriverError("canceled", "57014"), {"deadline": True}, "PIE-R3001"),
        (ex.ExecutionError("EXECUTION_CANCELED"), {"deadline": True}, "PIE-R3001"),
        (DriverError("statement timeout", "57014"), {}, "PIE-R3002"),
        (DriverError("relation missing", "42P01"), {}, "PIE-R3003"),
        (DriverError("server closed the connection", None), {}, "PIE-R3003"),
        (ResultError("EXECUTION_RESOURCE_LIMIT"), {}, "PIE-R3004"),
        (ex.ExecutionError("POSTGRES_SOURCE_RESOURCE_LIMIT"), {}, "PIE-R3004"),
        (ResultError("VALUE_DOMAIN"), {}, "PIE-R3005"),
        (ResultError("EXECUTION_METADATA"), {}, "PIE-R3005"),
        (ex.ExecutionError("EXECUTION_FINALIZATION"), {}, "PIE-R3006"),
        (ex.ExecutionError("EXECUTION_REQUEST_CHANGED"), {}, "PIE-R3999"),
        (ex.ExecutionError("EXECUTION_REUSE"), {"deadline": True}, "PIE-R4001"),
    ),
)
def test_attempt_failures_are_classified_deterministically(error, facts, code):
    """A deadline wins over the cancellation it caused, a driver exception
    before the session exists is a connection failure (any other exception
    there is unclassified), and the message of a foreign exception is never
    read; reuse stays misuse after a deadline."""
    arguments = {"phase": "read", "deadline": False, "connected": True} | facts
    refusal = errors.attempt_failure(error, **arguments)
    assert refusal.code == code
    assert refusal.phase == "read"
    assert refusal.cause == type(error).__name__


def test_cancelled_deadline_and_server_timeout_have_distinct_runtime_codes():
    """Manual control, elapsed local deadline and server timeout are separate."""
    cancelled = errors.failure("PIE-R3009")
    deadline = errors.attempt_failure(
        TimeoutError("EXECUTION_DEADLINE"),
        phase="read",
        deadline=False,
        connected=True,
    )
    server_timeout = errors.attempt_failure(
        DriverError("statement timeout", "57014"),
        phase="read",
        deadline=False,
        connected=True,
    )
    assert [
        (item.code, item.category) for item in (cancelled, deadline, server_timeout)
    ] == [
        ("PIE-R3009", "CANCELLED"),
        ("PIE-R3001", "DEADLINE"),
        ("PIE-R3002", "STATEMENT_TIMEOUT"),
    ]


def test_batch_export_refusals_name_closed_and_transfer():
    assert errors.batch_failure(ResultError("INTEROP_CLOSED")).code == "PIE-R4002"
    assert errors.batch_failure(ResultError("INTEROP_SPENT")).code == "PIE-R4003"
    assert errors.batch_failure(DriverError("pyarrow said no")).code == "PIE-R4003"


def test_failure_text_is_fixed_vocabulary():
    leaking = DriverError(
        f'connection to server at "{HOST}" failed: password "{PASSWORD}"', "28P01"
    )
    refusal = errors.attempt_failure(
        leaking, phase="admission", deadline=False, connected=False, driver=True
    )
    text = str(refusal)
    assert text == (
        "PIE-R2004 CONNECTION_FAILED: "
        + errors.CODES["PIE-R2004"][1]
        + " (phase=admission, sqlstate=28P01, cause=DriverError)"
    )
    assert HOST not in text and PASSWORD not in text
    assert errors.sqlstate(DriverError("x", "not a state")) is None
    error = execution.AttemptFailed(refusal, attempt="a1")
    assert str(error) == text and (error.code, error.category) == (
        "PIE-R2004",
        "CONNECTION_FAILED",
    )
    assert error.detail is None and error.attempt == "a1"
    assert issubclass(execution.RequestRejected, execution.ExecutionError)
    assert issubclass(execution.HandleMisuse, execution.ExecutionError)
    assert not issubclass(execution.CompileRejected, execution.ExecutionError)


def test_access_never_shows_or_duplicates_the_password():
    access = execution.PostgresAccess(HOST, 5432, "app", "reader", PASSWORD)
    for text in (repr(access), str(access), format(access)):
        assert PASSWORD not in text and "password=<redacted>" in text
    assert access.sslmode == "require"
    premise = execution.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
    for value in (access, premise):
        for duplicate in (pickle.dumps, copy.copy, copy.deepcopy):
            with pytest.raises(TypeError):
                duplicate(value)
    # Round-trips only the value object built here; limits hold no credential.
    limits = execution.ExecutionLimits(seconds=5)
    assert pickle.loads(pickle.dumps(limits)) == limits


@pytest.fixture(scope="module")
def query(tmp_path_factory):
    return execution.compile_query(
        api.write_example(tmp_path_factory.mktemp("execution-errors")),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


def test_public_errors_carry_no_credential_or_chained_driver_exception(
    query, monkeypatch
):
    """G13: a request refusal from a private check and an attempt failure from
    a real driver exception carry neither the password nor the driver's
    message, and no private exception is reachable as cause or context."""
    for name in tuple(os.environ):
        if name.startswith("PG") or name in (*ex.AMBIENT_TLS, "PSYCOPG_IMPL"):
            monkeypatch.delenv(name)
    premise = execution.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
    socket_access = execution.PostgresAccess(
        "/var/run/postgresql", 5432, "app", "reader", PASSWORD
    )
    with pytest.raises(execution.RequestRejected) as refused:
        execution.execute(
            query, route="postgres_rows", access=socket_access, premise=premise
        )
    listener = socket.create_server(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    monkeypatch.setattr(project_arrow_result, "pinned", lambda: None)
    handle = execution.execute(
        query,
        route="postgres_rows",
        access=execution.PostgresAccess(
            "127.0.0.1", port, "app", "reader", PASSWORD, "disable"
        ),
        premise=premise,
    )
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle:
            pass
    assert failed.value.failure.cause == "OperationalError"
    for error in (refused.value, failed.value):
        assert error.__cause__ is None and error.__context__ is None
        rendered = "".join(traceback.format_exception(error)) + repr(error)
        assert PASSWORD not in rendered and str(port) not in str(error)
        assert "/var/run/postgresql" not in str(error)
    outcome = failed.value.outcome
    assert outcome is not None and PASSWORD not in repr(outcome)
    assert outcome.primary == failed.value.failure
    assert PASSWORD not in repr(handle) and PASSWORD not in repr(query)


def test_public_surface_is_exactly_the_alpha_names():
    """The supported exports; no private owner, coordinator, runtime or
    collect entry is part of them."""
    assert execution.__all__ == sorted(execution.__all__)
    assert set(execution.__all__) == {
        "AttemptFailed",
        "CompileRejected",
        "CompiledQuery",
        "ExecutionError",
        "ExecutionLimits",
        "Failure",
        "GenerationObservation",
        "HandleMisuse",
        "JobObservation",
        "MySQLAccess",
        "MySQLDeploymentPremise",
        "OperationReply",
        "Outcome",
        "PostgresAccess",
        "PostgresDeploymentPremise",
        "QueryBundle",
        "RequestRejected",
        "ResultBatch",
        "ResultHandle",
        "SaveCloseHandle",
        "SaveReply",
        "SavedBatch",
        "SavedRead",
        "SavedReadEnd",
        "UnclosedHandleWarning",
        "VerifiedExport",
        "WorkspaceRef",
        "compile_query",
        "create_workspace",
        "execute",
        "export_bundle",
        "inspect_job",
        "load_bundle",
        "new_consumer_identity",
        "new_operation",
        "open_saved_read",
        "open_workspace",
        "operation_result",
        "release_saved_read",
        "retire_generation",
        "save",
        "verified_export",
    }
    for name in execution.__all__:
        assert getattr(execution, name).__module__.startswith("pietto.execution.")
    runtime = (ROOT / "docs/spec/diagnostics.md").read_text(encoding="utf-8")
    runtime = runtime.split("## Runtime Diagnostics", 1)[1]
    for declaration in (
        "Managed operator compliance: NOT_INDEPENDENTLY_VERIFIED",
        "Native all-definition lifetime exclusion: NOT_DEMONSTRATED / NOT CLAIMED",
    ):
        assert declaration in (execution.__doc__ or "")
        assert declaration in (ROOT / "docs/execution.md").read_text(encoding="utf-8")
        assert declaration in runtime
