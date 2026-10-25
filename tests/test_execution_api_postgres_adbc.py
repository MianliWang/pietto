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
        "parameters": None,
    }


SINCE = """
query since(low: Int, note: Text | None):
    from items
    where id > low and (note is None or label != note)
    select:
        id
        tag = note
        next = low + 1
"""


@pytest.fixture(scope="module")
def since(tmp_path_factory):
    project = api.write_example(tmp_path_factory.mktemp("execution-adbc-parameters"))
    main = project / "main.pietto"
    main.write_text(main.read_text(encoding="utf-8") + SINCE, encoding="utf-8")
    return execution.compile_query(
        project,
        module="main.pietto",
        kind="query",
        name="since",
        dialect="postgres",
        emission_contract="contract.json",
        literal_policy="bind-safe",
    )


def test_adbc_binds_parameters_by_name_before_any_driver_import(since):
    """The ADBC route binds the same unbound template as the rows route: one
    native argument per parameter and slot, the template's exact SQL."""
    before = {module.partition(".")[0] for module in sys.modules}
    template = since._template.artifact.rendered.sql
    for parameters, arguments in (
        ({"note": "x", "low": 5}, (5, "x", 1)),
        ({"low": -5, "note": None}, (-5, None, 1)),
    ):
        handle = execution.execute(
            since,
            route="postgres_adbc",
            access=ACCESS,
            premise=PREMISE,
            parameters=parameters,
        )
        request = handle._owner.request
        assert request.route == "postgres_adbc"
        assert request.binding.arguments == arguments
        assert request.artifact.rendered.sql == template
        handle.close()
    after = {module.partition(".")[0] for module in sys.modules}
    assert not (after - before) & {"adbc_driver_manager", "adbc_driver_postgresql"}


class Submitted(Exception):
    """Stops a statement at the driver's execute call."""


def test_adbc_submits_each_parameter_with_its_type_at_the_driver(since, monkeypatch):
    """The ADBC reader prepares the template SQL and binds one typed Arrow
    column per `$n`, up to the driver's execute: a header parameter carries
    its declared type, also as a NULL, and a bind-safe slot its own."""
    from pietto._project import project_execution_postgres_adbc as adbc

    monkeypatch.setattr(adbc, "read_control", lambda *args, **kwargs: None)
    submitted = []

    class Statement:
        def __init__(self, connection):
            self.sql = self.bound = None

        def set_options(self, **options):
            pass

        def set_sql_query(self, sql):
            self.sql = sql

        def prepare(self):
            pass

        def bind(self, batch):
            self.bound = batch

        def execute_query(self):
            submitted.append((self.sql, self.bound))
            raise Submitted

        def close(self):
            pass

    arrow = SimpleNamespace(
        int64=lambda: "int64",
        bool_=lambda: "bool",
        float64=lambda: "double",
        string=lambda: "string",
        array=lambda values, type: (*values, type),
        record_batch=lambda columns, names: SimpleNamespace(
            num_rows=1, columns=tuple(columns), names=tuple(names)
        ),
    )
    template = since._template.artifact.rendered.sql.decode()
    for parameters, columns in (
        ({"low": 5, "note": "x"}, ((5, "int64"), ("x", "string"), (1, "int64"))),
        ({"low": -5, "note": None}, ((-5, "int64"), (None, "string"), (1, "int64"))),
    ):
        handle = execution.execute(
            since,
            route="postgres_adbc",
            access=ACCESS,
            premise=PREMISE,
            parameters=parameters,
        )
        owner = handle._owner
        owner._manager = SimpleNamespace(AdbcStatement=Statement)
        owner._arrow = arrow
        with pytest.raises(Submitted):
            owner._submit("query", 1)
        sql, batch = submitted.pop()
        assert (sql, batch.columns, batch.names) == (
            template,
            columns,
            ("p1", "p2", "p3"),
        )
        handle.close()


@pytest.mark.parametrize(
    "parameters,code,detail",
    (
        (None, "PIE-R1006", "BINDING_PARAMETERS"),
        ({"low": 5, "note": "x", "high": 1}, "PIE-R1006", "BINDING_PARAMETERS"),
        ({"low": 5.0, "note": "x"}, "PIE-R1006", "BINDING_PARAMETER:0:Int"),
        ({"low": None, "note": "x"}, "PIE-R1006", "BINDING_PARAMETER:0:Int"),
        ({"low": 5, "note": b"x"}, "PIE-R1006", "BINDING_PARAMETER:1:Text"),
        ([("low", 5)], "PIE-R1002", "PUBLIC_PARAMETERS_TYPE"),
        ({"low": 2**63 - 1, "note": None}, "PIE-R1004", "BINDING_INVALID"),
    ),
    ids=("missing", "extra", "float", "null", "bytes", "pairs", "overflow"),
)
def test_adbc_refuses_each_parameter_input_before_the_bridge_opens(
    since, monkeypatch, parameters, code, detail
):
    from pietto._project import project_execution_postgres_adbc as adbc

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused request reached the ADBC owner")

    monkeypatch.setattr(adbc.PostgresADBCExecution, "__init__", forbidden)
    with pytest.raises(execution.RequestRejected) as refused:
        execution.execute(
            since,
            route="postgres_adbc",
            access=ACCESS,
            premise=PREMISE,
            parameters=parameters,
        )
    assert (refused.value.code, refused.value.detail) == (code, detail)
    assert refused.value.__cause__ is None and refused.value.__context__ is None


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


class ArrowInvalid(ValueError):
    """PyArrow's error for a failed stream read: it carries no SQLSTATE."""


class ProgrammingError(Exception):
    """The driver manager's error for a server error: it carries the SQLSTATE."""

    def __init__(self, sqlstate):
        super().__init__("[libpq] more than one row returned by a subquery")
        self.sqlstate = sqlstate


@pytest.mark.parametrize(
    ("error", "sqlstate"),
    ((ProgrammingError("21000"), "21000"), (ArrowInvalid("stream failed"), None)),
    ids=("server_error", "arrow_error"),
)
def test_adbc_error_raised_while_the_result_stream_is_read_keeps_its_sqlstate(
    query, monkeypatch, error, sqlstate
):
    """The route reads each result stream through the pinned manager's reader,
    which raises a server error found mid-stream (a multi-row scalar read:
    21000) as the driver's error with its SQLSTATE; an error without one is
    classified as before. The attempt then sends nothing more and closes."""
    import time

    handle = execution.execute(
        query, route="postgres_adbc", access=ACCESS, premise=PREMISE
    )
    owner = handle._owner
    submitted, streams, closed = [], [], []

    class Stream:
        schema = ()

        def __init__(self, failure):
            self.failure = failure

        def read_next_batch(self):
            if self.failure is None:
                raise StopIteration
            raise self.failure

        def close(self):
            closed.append("reader")

    class Statement:
        def __init__(self, connection):
            self.sql = ""

        def set_options(self, **options):
            pass

        def set_sql_query(self, sql):
            self.sql = sql
            submitted.append(sql)

        def prepare(self):
            pass

        def bind(self, batch):
            pass

        def execute_query(self):
            # The statement-timeout control read ends normally; the query fails.
            control = self.sql.startswith("SELECT pg_catalog.set_config(")
            streams.append(Stream(None if control else error))
            return SimpleNamespace(address=len(streams) - 1, is_valid=False), -1

        def close(self):
            closed.append("statement")

    class Reader:
        @staticmethod
        def _import_from_c(address):
            return streams[address]

    owner._started = time.monotonic()
    owner._transaction = owner._delivery = "OPEN"
    owner.session_id = 4242
    owner._manager = SimpleNamespace(AdbcStatement=Statement)
    # Arrow only types the bound values; it has no stream reader to fall back to.
    owner._arrow = SimpleNamespace(
        int64=str,
        bool_=str,
        float64=str,
        string=str,
        array=lambda values, **_: values,
        record_batch=lambda columns, **_: SimpleNamespace(num_rows=1),
    )
    owner._stream_reader = Reader
    owner._connection = owner._owned_connection = SimpleNamespace(
        close=lambda: closed.append("connection")
    )
    owner._owned_database = SimpleNamespace(close=lambda: closed.append("database"))
    monkeypatch.setattr(owner, "_verify", lambda: None)

    with pytest.raises(execution.AttemptFailed) as failed:
        next(handle)
    expected = errors.failure(
        "PIE-R3003", phase="query", sqlstate=sqlstate, cause=type(error).__name__
    )
    assert failed.value.failure == expected
    outcome = handle.outcome
    assert handle.closed and outcome.primary == expected
    assert (
        outcome.end,
        outcome.source,
        outcome.transaction,
        outcome.delivery,
        outcome.cleanup,
        outcome.cleanup_failures,
        outcome.cancel_observed,
    ) == (
        "FAILED",
        "FAILED",
        "UNKNOWN",
        "FAILED",
        "LOCAL_CLOSED_REMOTE_UNOBSERVED",
        (),
        False,
    )
    # No ROLLBACK or other command follows the server error on that connection.
    assert len(submitted) == 2 and submitted[0].startswith(
        "SELECT pg_catalog.set_config('statement_timeout'"
    )
    assert closed == [
        "reader",
        "statement",
        "reader",
        "statement",
        "connection",
        "database",
    ]


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
