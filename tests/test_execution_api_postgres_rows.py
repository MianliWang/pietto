"""Public execution alpha on the PostgreSQL rows route, without a database.

Compiling, request checks and refusals use the real public layer and private
owners. Connection-level laws drive the pinned psycopg/libpq against a
loopback protocol stub and observe file opens with inotify; each has a
control that shows the observation would see the unpinned behavior. The
lifecycle wrapper runs over a duck-typed owner. The real-database and
installed-consumer witnesses are tests/_pietto_execution_api_probe.py.
"""

from __future__ import annotations

import ast
import copy
import gc
import json
import os
from pathlib import Path
import pickle
import socket
import subprocess
import sys
import threading
from types import ModuleType, SimpleNamespace
from typing import Any, cast
import warnings

import pytest

import _pietto_execution_api as api
import pietto.execution as execution
from pietto._project import project_arrow_result
from pietto._project import project_execution as ex
from pietto._project import project_execution_postgres as pg
from pietto._project import project_public_execution as composition
from pietto._project.project_result_contract import ResultError
from pietto.execution import _handle
from pietto._project.project_sql_emission_cli import run_project_emit_sql

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "pw-5f1c9e-never-shown"
HOST_MARKER = "db-7d24-host.invalid"
PREMISE = execution.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog"))
REFUSED = ("SSLKEYLOGFILE", "OPENSSL_CONF", "OPENSSL_MODULES")
# The 36 PG* names the bundled libpq 18 reads before it connects (Phase69 S01
# measurement); the route refuses every PG* name, these are the ones that act.
LIBPQ_ENVIRONMENT = (
    "PGAPPNAME",
    "PGCHANNELBINDING",
    "PGCLIENTENCODING",
    "PGCONNECT_TIMEOUT",
    "PGDATABASE",
    "PGGSSDELEGATION",
    "PGGSSENCMODE",
    "PGGSSLIB",
    "PGHOST",
    "PGHOSTADDR",
    "PGKRBSRVNAME",
    "PGLOADBALANCEHOSTS",
    "PGMAXPROTOCOLVERSION",
    "PGMINPROTOCOLVERSION",
    "PGOPTIONS",
    "PGPASSFILE",
    "PGPASSWORD",
    "PGPORT",
    "PGREQUIREAUTH",
    "PGREQUIREPEER",
    "PGREQUIRESSL",
    "PGSERVICE",
    "PGSSLCERT",
    "PGSSLCERTMODE",
    "PGSSLCOMPRESSION",
    "PGSSLCRL",
    "PGSSLCRLDIR",
    "PGSSLKEY",
    "PGSSLMAXPROTOCOLVERSION",
    "PGSSLMINPROTOCOLVERSION",
    "PGSSLMODE",
    "PGSSLNEGOTIATION",
    "PGSSLROOTCERT",
    "PGSSLSNI",
    "PGTARGETSESSIONATTRS",
    "PGUSER",
)


def access(
    port: Any = 5432,
    *,
    host: str = "127.0.0.1",
    sslmode: str = "disable",
    user: str = "reader",
    password: str = PASSWORD,
) -> execution.PostgresAccess:
    return execution.PostgresAccess(host, port, "app", user, password, sslmode)


def child_environment(**extra: str) -> dict[str, str]:
    """This process's environment without any variable the route refuses or
    that selects the psycopg implementation."""
    kept = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("PG") and k not in (*ex.AMBIENT_TLS, "PSYCOPG_IMPL")
    }
    return kept | extra


def ended(error: execution.ExecutionError) -> execution.Outcome:
    """The final outcome an attempt failure carries."""
    assert error.outcome is not None
    return error.outcome


@pytest.fixture(scope="module")
def example(tmp_path_factory):
    return api.write_example(tmp_path_factory.mktemp("execution-example"))


@pytest.fixture(scope="module")
def query(example):
    return execution.compile_query(
        example,
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )


@pytest.fixture
def clean(monkeypatch):
    """No ambient connection input and no PSYCOPG_IMPL; PyArrow (absent from
    the core profile) is replaced only where a test reaches the connection."""
    for name in tuple(os.environ):
        if name.startswith("PG") or name in (*REFUSED, "PSYCOPG_IMPL"):
            monkeypatch.delenv(name)
    return monkeypatch


@pytest.fixture
def sentinel():
    """A loopback port that records whether anything connected to it."""
    listener = socket.create_server(("127.0.0.1", 0))
    listener.setblocking(False)

    def connected():
        try:
            listener.accept()[0].close()
        except BlockingIOError:
            return False
        return True

    yield SimpleNamespace(port=listener.getsockname()[1], connected=connected)
    listener.close()


def emit(example, policy="preserve", *, contract="contract.json", text=False):
    result = run_project_emit_sql(
        [
            "--project",
            str(example),
            "--module",
            "main.pietto",
            "--kind",
            "table",
            "--name",
            "active_items",
            "--dialect",
            "postgres",
            "--emission-contract",
            contract,
            "--literal-policy",
            policy,
            *(["--format", "text"] if text else []),
        ]
    )
    assert not isinstance(result, int)
    return result


def compiled(example, **overrides):
    arguments: dict[str, Any] = dict(
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    arguments.update(overrides)
    return execution.compile_query(example, **arguments)


IMPORT_CHILD = r"""
import json, pydoc, sys
sys.path.insert(0, sys.argv[1])
events = []
sys.addaudithook(
    lambda name, args: events.append(name)
    if name in ("socket.connect", "socket.getaddrinfo", "subprocess.Popen")
    else None
)
DRIVERS = ("psycopg", "psycopg_binary", "pyarrow")
def loaded():
    return sorted({m.split(".")[0] for m in sys.modules} & set(DRIVERS))
import pietto.execution as pe
from pietto._project import project_execution as private_execution
from pietto._project import project_execution_postgres as postgres
from pietto._project import project_job_store as job_store
from pietto._project import project_job_workspace as workspace
def forbidden(*args, **kwargs):
    raise AssertionError("an unopened query had a side effect")
postgres._connect = forbidden
postgres.drivers = forbidden
private_execution.refuse_ambient = forbidden
workspace.create_workspace = forbidden
workspace.open_workspace = forbidden
job_store.register_job = forbidden
job_store.claim_publisher = forbidden
after_import = loaded()
query = pe.compile_query(sys.argv[2], module="main.pietto", kind="table",
    name="active_items", dialect="postgres", emission_contract="contract.json")
access = pe.PostgresAccess("127.0.0.1", int(sys.argv[3]), "app", "reader",
    "pw-never-sent", "disable")
handle = pe.execute(query, route="postgres_rows", access=access,
    premise=pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog")))
texts = [repr(query), repr(access), str(access), repr(handle), repr(handle.outcome),
    pydoc.render_doc(pe, renderer=pydoc.plaintext),
    pydoc.render_doc(query, renderer=pydoc.plaintext),
    pydoc.render_doc(handle, renderer=pydoc.plaintext)]
print(json.dumps({"after_import": after_import, "loaded": loaded(), "events": events,
    "end": handle.outcome.end, "shown": any("pw-never-sent" in t for t in texts),
}))
"""


def test_import_compile_and_unopened_execute_load_no_driver_and_connect_nowhere(
    example, sentinel
):
    """G01: compiling, inspecting and an unopened execute() make no connection
    and read no connection setting: even with PGHOST/PGPORT naming a live
    loopback listener, nothing connects and no driver or PyArrow is loaded."""
    environment = {
        k: v for k, v in os.environ.items() if not k.startswith(("PG", "PYTHON"))
    }
    environment.update(PGHOST="127.0.0.1", PGPORT=str(sentinel.port), PGUSER="x")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            IMPORT_CHILD,
            str(ROOT / "src"),
            str(example),
            str(sentinel.port),
        ],
        capture_output=True,
        text=True,
        env=environment,
        cwd=example.parent,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    facts = json.loads(result.stdout)
    assert facts == {
        "after_import": [],
        "loaded": [],
        "events": [],
        "end": "NOT_STARTED",
        "shown": False,
    }
    assert not sentinel.connected()


@pytest.mark.parametrize(
    "blocks",
    (api.example_blocks, api.bundle_blocks),
    ids=("run_query", "bundle_query"),
)
def test_the_documented_script_uses_only_public_imports(blocks):
    """The external user's scripts need no checkout or test helper: they
    import the standard library, PyArrow and `pietto.execution` only."""
    tree = ast.parse(blocks()["python"])
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert imported == {"sys", "pyarrow", "pietto.execution"}
    names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert names <= set(execution.__all__)


@pytest.mark.parametrize("policy", ("preserve", "bind-safe"))
def test_compile_query_produces_the_project_command_artifact(example, policy):
    """G13 and the shared orchestration: the Python compile and the CLI reach
    the same artifact bytes for the same arguments."""
    query = compiled(example, literal_policy=policy)
    command = emit(example, policy)
    assert command.exit_code == 0 and query.emission == command.stdout
    document = json.loads(query.emission or b"")
    assert document["status"] == "VERIFIED"
    assert ("$1" in document["sql"]) is (policy == "bind-safe")
    assert (query.module, query.kind, query.name, query.dialect) == (
        "main.pietto",
        "table",
        "active_items",
        "postgres",
    )
    assert (query.release, query.literal_policy) == ("18.6", policy)
    assert repr(query) == (
        "CompiledQuery(module='main.pietto', kind='table', name='active_items',"
        f" dialect='postgres', release='18.6', literal_policy='{policy}',"
        " origin='live')"
    )


def test_compile_refusals_are_the_project_command_documents(tmp_path):
    """A BLOCKED and an INPUT_REJECTED compile carry the command's own JSON
    document byte for byte, and str() is its text report."""
    project = api.write_example(tmp_path)
    contract = project / "contract.json"
    contract.write_text(
        contract.read_text().replace('"release": "18.6"', '"release": "18.5"')
    )
    for name, status in (
        ("contract.json", "BLOCKED"),
        ("absent.json", "INPUT_REJECTED"),
    ):
        with pytest.raises(execution.CompileRejected) as refused:
            compiled(project, emission_contract=name)
        json_command = emit(project, contract=name)
        text_command = emit(project, contract=name, text=True)
        assert refused.value.status == status
        assert refused.value.emission == json_command.stdout
        assert str(refused.value) == text_command.stderr.rstrip("\n")
        assert json.loads(refused.value.emission)["status"] == status


def test_compile_stops_at_an_unadmitted_relation_let_without_internal_error(
    tmp_path,
):
    """A relation let whose VALUES body is not yet admitted, anywhere in the
    project, blocks compilation with the command's own BLOCKED document, never
    an internal PIE-R1999 refusal."""
    project = api.write_example(tmp_path)
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + "\nquery gated:\n    let l:\n        values(id: Int not null):\n"
        "            1\n    from l\n    select:\n        id\n"
    )
    with pytest.raises(execution.CompileRejected) as refused:
        compiled(project)
    assert refused.value.status == "BLOCKED"
    assert refused.value.emission == emit(project).stdout
    document = json.loads(refused.value.emission)
    assert [d["code"] for d in document["diagnostics"]] == ["PIE-S2347"]


@pytest.mark.parametrize(
    "clauses",
    (
        "    where id > low\n    select:\n        id\n",
        # Unread parameters still make a parameterized template.
        "    select:\n        id\n",
    ),
    ids=("read", "unread"),
)
def test_compile_of_a_parameterized_query_stops_at_the_compiled_boundary(
    tmp_path, clauses
):
    """The command emits the unbound template; until compiled records carry a
    parameter read, compiling it refuses deterministically before any binding."""
    project = api.write_example(tmp_path)
    main = project / "main.pietto"
    main.write_text(
        main.read_text(encoding="utf-8")
        + "\nquery since(low: Int not null):\n    from items\n"
        + clauses
    )
    with pytest.raises(execution.RequestRejected) as refused:
        compiled(project, kind="query", name="since")
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "COMPILED_EXPORT_SCALAR",
    )
    assert compiled(project).literal_policy == "preserve"


@pytest.mark.parametrize(
    "change,code",
    (
        ({"module": None}, "PIE-R1001"),
        ({"kind": "view"}, "PIE-R1002"),
        ({"dialect": "sqlite"}, "PIE-R1002"),
        ({"literal_policy": "bind_safe"}, "PIE-R1002"),
        ({"literal_policy": None}, "PIE-R1001"),
        ({"emission_contract": Path("contract.json")}, "PIE-R1002"),
        ({"name": 7}, "PIE-R1002"),
    ),
)
def test_compile_arguments_are_checked_before_the_project_is_read(
    tmp_path, change, code
):
    with pytest.raises(execution.RequestRejected) as refused:
        compiled(tmp_path / "absent", **change)
    assert (refused.value.code, refused.value.detail) == (
        code,
        "PUBLIC_COMPILE_ARGUMENT",
    )
    with pytest.raises(execution.RequestRejected, match="PIE-R1001"):
        execution.compile_query(
            None,  # type: ignore[arg-type]
            module="m",
            kind="table",
            name="n",
            dialect="postgres",
            emission_contract="c",
        )


def test_compiled_query_is_created_only_by_compile_query_or_load_bundle(query):
    with pytest.raises(TypeError, match=r"compile_query\(\) or load_bundle\(\)"):
        execution.CompiledQuery()
    with pytest.raises(AttributeError):
        query.dialect = "mysql"  # type: ignore[misc]
    for duplicate in (pickle.dumps, copy.copy, copy.deepcopy):
        with pytest.raises(TypeError):
            duplicate(query)


def _forged(query, dialect):
    forged = object.__new__(execution.CompiledQuery)
    for slot in execution.CompiledQuery.__slots__:
        object.__setattr__(forged, slot, getattr(query, slot))
    object.__setattr__(forged, "_dialect", dialect)
    return forged


REQUEST_CASES: dict[str, tuple[dict[str, Any], str, str]] = {
    "query_none": (dict(query=None), "PIE-R1001", "PUBLIC_QUERY_REQUIRED"),
    "sql_text": (
        dict(query="SELECT * FROM fixture.items"),
        "PIE-R1002",
        "PUBLIC_QUERY_TYPE",
    ),
    "route_none": (dict(route=None), "PIE-R1001", "PUBLIC_ROUTE_REQUIRED"),
    "route_type": (dict(route=5), "PIE-R1002", "PUBLIC_ROUTE_TYPE"),
    "route_unknown": (
        dict(route="postgres_other"),
        "PIE-R1003",
        "PUBLIC_ROUTE_UNAVAILABLE",
    ),
    "route_mysql": (dict(route="mysql_rows"), "PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE"),
    "query_mysql": (dict(dialect="mysql"), "PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE"),
    "access_none": (dict(access=None), "PIE-R1001", "PUBLIC_ACCESS_REQUIRED"),
    "access_private": (
        dict(access=ex.PostgresAccess("127.0.0.1", 5432, "app", "u", "p", "disable")),
        "PIE-R1002",
        "PUBLIC_ACCESS_TYPE",
    ),
    "premise_none": (dict(premise=None), "PIE-R1001", "PUBLIC_PREMISE_REQUIRED"),
    "premise_tuple": (
        dict(premise=("fixture", "pg_catalog")),
        "PIE-R1002",
        "PUBLIC_PREMISE_TYPE",
    ),
    "limits_none": (dict(limits=None), "PIE-R1001", "PUBLIC_LIMITS_REQUIRED"),
    "limits_dict": (dict(limits={"seconds": 1}), "PIE-R1002", "PUBLIC_LIMITS_TYPE"),
    "isolation_none": (dict(isolation=None), "PIE-R1001", "PUBLIC_ISOLATION_REQUIRED"),
    "isolation_value": (
        dict(isolation="read committed"),
        "PIE-R1002",
        "EXECUTION_ISOLATION",
    ),
    # With require, only the host-form clause can refuse these hosts.
    "socket_directory": (
        dict(access=access(host="/var/run/postgresql", sslmode="require")),
        "PIE-R1002",
        "EXECUTION_ACCESS_PROFILE",
    ),
    "abstract_socket": (
        dict(access=access(host="@pietto", sslmode="require")),
        "PIE-R1002",
        "EXECUTION_ACCESS_PROFILE",
    ),
    "host_list": (
        dict(access=access(host="127.0.0.1,127.0.0.2", sslmode="require")),
        "PIE-R1002",
        "EXECUTION_ACCESS_PROFILE",
    ),
    "disable_off_loopback": (
        dict(access=access(host="localhost")),
        "PIE-R1002",
        "EXECUTION_ACCESS_PROFILE",
    ),
    "verify_full": (
        dict(access=access(sslmode="verify-full")),
        "PIE-R1002",
        "EXECUTION_ACCESS_PROFILE",
    ),
    "port_text": (dict(access=access(port="5432")), "PIE-R1002", "EXECUTION_ACCESS"),
    "empty_password": (
        dict(access=access(password="")),
        "PIE-R1002",
        "EXECUTION_ACCESS",
    ),
    # None inside a value object is an invalid value, not a missing argument.
    "password_none": (
        dict(access=access(password=None)),  # type: ignore[arg-type]
        "PIE-R1002",
        "EXECUTION_ACCESS",
    ),
    "schemas_none": (
        dict(premise=execution.PostgresDeploymentPremise(schemas=None)),  # type: ignore[arg-type]
        "PIE-R1002",
        "POSTGRES_DEPLOYMENT_PREMISE_SCOPE",
    ),
    "schemas_uncovered": (
        dict(premise=execution.PostgresDeploymentPremise(schemas=("public",))),
        "PIE-R1002",
        "POSTGRES_DEPLOYMENT_PREMISE_SCOPE",
    ),
    "schemas_missing_catalog": (
        dict(premise=execution.PostgresDeploymentPremise(schemas=("fixture",))),
        "PIE-R1002",
        "POSTGRES_DEPLOYMENT_PREMISE_SCOPE",
    ),
    "schemas_list": (
        dict(premise=execution.PostgresDeploymentPremise(schemas=["fixture"])),  # type: ignore[arg-type]
        "PIE-R1002",
        "POSTGRES_DEPLOYMENT_PREMISE_SCOPE",
    ),
    "schemas_catalog": (
        dict(
            premise=execution.PostgresDeploymentPremise(
                schemas=("fixture", "information_schema")
            )
        ),
        "PIE-R1002",
        "POSTGRES_DEPLOYMENT_PREMISE_SCOPE",
    ),
    "batch_rows": (
        dict(limits=execution.ExecutionLimits(batch_rows=5000)),
        "PIE-R1002",
        "EXECUTION_LIMITS",
    ),
}


@pytest.mark.parametrize("case", sorted(REQUEST_CASES))
def test_execute_refuses_each_invalid_input_before_any_io(query, monkeypatch, case):
    """G03: every refusal comes from execute() itself; nothing connects, no
    default is substituted and SQL text is never a query."""
    change, code, detail = REQUEST_CASES[case]

    def forbidden(*arguments, **keywords):
        raise AssertionError("a refused request reached the driver")

    monkeypatch.setattr(pg, "_connect", forbidden)
    monkeypatch.setattr(pg, "drivers", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    arguments: dict[str, Any] = dict(
        query=query, route="postgres_rows", access=access(), premise=PREMISE
    )
    change = dict(change)
    if "dialect" in change:
        arguments["query"] = _forged(query, change.pop("dialect"))
    arguments.update(change)
    target = arguments.pop("query")
    with pytest.raises(execution.RequestRejected) as refused:
        execution.execute(target, **arguments)
    assert (refused.value.code, refused.value.detail) == (code, detail)
    assert refused.value.attempt is None and refused.value.outcome is None
    assert refused.value.__cause__ is None and refused.value.__context__ is None


def test_execute_reports_the_first_refusal_in_the_documented_order(query):
    order = (
        ("query", "SELECT 1", "PUBLIC_QUERY_TYPE"),
        ("route", "postgres_other", "PUBLIC_ROUTE_UNAVAILABLE"),
        ("access", None, "PUBLIC_ACCESS_REQUIRED"),
        ("premise", None, "PUBLIC_PREMISE_REQUIRED"),
        ("limits", None, "PUBLIC_LIMITS_REQUIRED"),
        ("isolation", "read committed", "EXECUTION_ISOLATION"),
    )
    for position, (name, _value, detail) in enumerate(order):
        arguments: dict[str, Any] = dict(
            query=query, route="postgres_rows", access=access(), premise=PREMISE
        )
        arguments.update({n: v for n, v, _d in order[position:]})
        target = arguments.pop("query")
        with pytest.raises(execution.RequestRejected) as refused:
            execution.execute(target, **arguments)
        assert refused.value.detail == detail, name


def test_values_are_checked_after_every_type_in_the_documented_order(query):
    """After all presence and type checks (the route's availability right
    after its type), the values of premise, access, isolation (its type
    included) and limits are checked in that order."""
    uncovered = execution.PostgresDeploymentPremise(schemas=("public",))
    socket_host = access(host="/var/run/postgresql")
    wide = execution.ExecutionLimits(batch_rows=5000)
    pairs = (
        (dict(route="mysql_rows", access=None), "PUBLIC_ROUTE_UNAVAILABLE"),
        (dict(premise=uncovered, limits={"seconds": 1}), "PUBLIC_LIMITS_TYPE"),
        (dict(premise=uncovered, isolation=None), "PUBLIC_ISOLATION_REQUIRED"),
        (dict(access=socket_host, isolation=5), "EXECUTION_ACCESS_PROFILE"),
        (dict(isolation=5, limits=wide), "EXECUTION_ISOLATION"),
        (
            dict(access=socket_host, premise=uncovered),
            "POSTGRES_DEPLOYMENT_PREMISE_SCOPE",
        ),
        (
            dict(access=socket_host, isolation="read committed"),
            "EXECUTION_ACCESS_PROFILE",
        ),
        (dict(isolation="read committed", limits=wide), "EXECUTION_ISOLATION"),
        (dict(limits=wide), "EXECUTION_LIMITS"),
    )
    for changes, detail in pairs:
        arguments: dict[str, Any] = dict(
            route="postgres_rows", access=access(), premise=PREMISE
        )
        arguments.update(changes)
        with pytest.raises(execution.RequestRejected) as refused:
            execution.execute(query, **arguments)
        assert refused.value.detail == detail, changes


def test_omitted_route_access_or_premise_is_a_type_error(query):
    for missing in ("route", "access", "premise"):
        arguments: dict[str, Any] = dict(
            route="postgres_rows", access=access(), premise=PREMISE
        )
        del arguments[missing]
        with pytest.raises(TypeError, match=missing):
            execution.execute(query, **arguments)  # type: ignore[call-arg]


def test_each_execute_is_a_fresh_unopened_attempt(query):
    first = execution.execute(
        query, route="postgres_rows", access=access(), premise=PREMISE
    )
    second = execution.execute(
        query, route="postgres_rows", access=access(), premise=PREMISE
    )
    assert first.attempt != second.attempt and first.route == "postgres_rows"
    assert (first.outcome.end, first.closed) == ("NOT_STARTED", False)
    assert repr(first) == (
        f"ResultHandle(route='postgres_rows', attempt='{first.attempt}',"
        " end='NOT_STARTED')"
    )
    with pytest.raises(TypeError):
        execution.ResultHandle()
    with pytest.raises(TypeError):
        pickle.dumps(first)
    first.close()
    outcome = first.outcome
    assert (outcome.end, outcome.transaction, outcome.cleanup) == (
        "NOT_STARTED",
        "NOT_STARTED",
        "CLOSED",
    )
    assert outcome.remote_source_use_end == "REMOTE_QUIESCENCE_UNCONFIRMED"
    with pytest.raises(execution.HandleMisuse) as misuse:
        first.__enter__()
    assert misuse.value.code == "PIE-R4001"
    assert first.outcome == outcome


@pytest.mark.parametrize("name", (*LIBPQ_ENVIRONMENT, *REFUSED))
def test_refused_environment_is_named_before_the_driver_loads(query, clean, name):
    def forbidden():
        raise AssertionError("the driver loaded despite a refused variable")

    clean.setattr(pg, "drivers", forbidden)
    clean.setenv(name, "value-never-read")
    handle = execution.execute(
        query, route="postgres_rows", access=access(), premise=PREMISE
    )
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle:
            pass
    error = failed.value
    assert (error.code, error.detail) == (
        "PIE-R2003",
        "EXECUTION_AMBIENT_CONNECTION_PROFILE",
    )
    assert "value-never-read" not in str(error)
    outcome = ended(error)
    assert (outcome.end, outcome.transaction, outcome.cleanup) == (
        "FAILED",
        "NOT_STARTED",
        "CLOSED",
    )
    assert outcome.primary == error.failure and handle.closed


def test_selecting_the_psycopg_wait_function_is_accepted(query, clean):
    """PSYCOPG_WAIT_FUNC only selects psycopg's I/O wait implementation; the
    attempt goes on to load the pinned driver."""
    reached = []

    def driver():
        reached.append(True)
        raise ex.ExecutionError("EXECUTION_DEPENDENCY_MISSING")

    clean.setattr(pg, "drivers", driver)
    clean.setenv("PSYCOPG_WAIT_FUNC", "wait_select")
    with pytest.raises(execution.AttemptFailed, match="PIE-R2001"):
        with execution.execute(
            query, route="postgres_rows", access=access(), premise=PREMISE
        ):
            pass
    assert reached == [True]


def test_missing_arrow_is_refused_before_the_query_reaches_the_server(
    query, clean, sentinel
):
    """A3: with psycopg importable but PyArrow absent, the attempt is refused
    before it connects instead of after the server ran the statement."""
    clean.setitem(sys.modules, "pyarrow", None)
    handle = execution.execute(
        query, route="postgres_rows", access=access(sentinel.port), premise=PREMISE
    )
    with pytest.raises(execution.AttemptFailed) as failed:
        handle.__enter__()
    assert (failed.value.code, failed.value.detail) == (
        "PIE-R2001",
        "EXECUTION_DEPENDENCY_MISSING",
    )
    assert ended(failed.value).transaction == "NOT_STARTED"
    assert not sentinel.connected()


@pytest.mark.parametrize(
    "word,code",
    (
        ("EXECUTION_DEPENDENCY_MISSING", "PIE-R2001"),
        ("EXECUTION_DRIVER_VERSION", "PIE-R2002"),
        ("POSTGRES_DRIVER_LIBRARY", "PIE-R2002"),
    ),
)
def test_a_missing_or_unpinned_driver_is_refused_without_fallback(
    query, clean, word, code
):
    def refuse():
        raise ex.ExecutionError(word)

    clean.setattr(pg, "drivers", refuse)
    with pytest.raises(execution.AttemptFailed) as failed:
        with execution.execute(
            query, route="postgres_rows", access=access(), premise=PREMISE
        ):
            pass
    assert (failed.value.code, failed.value.detail) == (code, word)


SHADOW_CHILD = r"""
import json, sys
sys.path[:0] = [sys.argv[1], sys.argv[2]]
import pietto.execution as pe
query = pe.compile_query(sys.argv[3], module="main.pietto", kind="table",
    name="active_items", dialect="postgres", emission_contract="contract.json")
handle = pe.execute(query, route="postgres_rows",
    access=pe.PostgresAccess("127.0.0.1", 9, "app", "reader", "pw-shadow", "disable"),
    premise=pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog")))
try:
    with handle:
        pass
except pe.AttemptFailed as error:
    print(json.dumps([error.code, error.detail, sys.modules["psycopg"].__file__]))
"""
SHADOW = """
import pathlib
pathlib.Path(__file__).with_name("imported").write_text("yes")
class pq:
    __impl__ = "binary"
def connect(**fields):
    pathlib.Path(__file__).with_name("connected").write_text(str(sorted(fields)))
    raise RuntimeError("shadow")
"""

BINARY_SHADOW_CHILD = r"""
import json, sys
sys.path[:0] = [sys.argv[1], sys.argv[2]]
import pietto.execution as pe
query = pe.compile_query(sys.argv[3], module="main.pietto", kind="table",
    name="active_items", dialect="postgres", emission_contract="contract.json")
handle = pe.execute(query, route="postgres_rows",
    access=pe.PostgresAccess("127.0.0.1", 9, "app", "reader", "pw-shadow", "disable"),
    premise=pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog")))
try:
    with handle:
        pass
except pe.AttemptFailed as error:
    print(json.dumps([error.code, error.detail, "psycopg_binary" in sys.modules,
        "psycopg" in sys.modules]))
"""
BINARY_SHADOW = """
import pathlib
pathlib.Path(__file__).with_name("imported").write_text("yes")
"""


def test_a_shadowing_driver_copy_never_receives_the_connection(example, tmp_path):
    """Trust item 4: a psycopg copy ahead of the installed one on sys.path
    passes the metadata version pin, but its file is not recorded by the
    pinned distribution, so it is refused before any connection value."""
    if subprocess.run(
        [sys.executable, "-I", "-B", "-c", "import psycopg"], capture_output=True
    ).returncode:
        pytest.fail("the core profile is expected to provide psycopg[binary]")
    fake = tmp_path / "shadow" / "psycopg"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text(SHADOW)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            SHADOW_CHILD,
            str(ROOT / "src"),
            str(fake.parent),
            str(example),
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        env=child_environment(),
    )
    assert result.returncode == 0, result.stderr
    code, detail, origin = json.loads(result.stdout)
    assert (code, detail) == ("PIE-R2002", "EXECUTION_DRIVER_VERSION")
    assert Path(origin) == fake / "__init__.py"
    assert (fake / "imported").exists() and not (fake / "connected").exists()


def test_a_shadowing_binary_copy_is_refused_before_psycopg_imports_it(
    example, tmp_path
):
    """The binary distribution's module needs the same origin check before
    importing psycopg, which otherwise imports it as its selected implementation."""
    fake = tmp_path / "shadow" / "psycopg_binary"
    fake.mkdir(parents=True)
    (fake / "__init__.py").write_text(BINARY_SHADOW)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            BINARY_SHADOW_CHILD,
            str(ROOT / "src"),
            str(fake.parent),
            str(example),
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        env=child_environment(),
    )
    assert result.returncode == 0, result.stderr
    code, detail, binary_imported, psycopg_imported = json.loads(result.stdout)
    assert (code, detail) == ("PIE-R2002", "EXECUTION_DRIVER_VERSION")
    assert binary_imported is False and psycopg_imported is False
    assert not (fake / "imported").exists()


IMPL_CHILD = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import pietto.execution as pe
query = pe.compile_query(sys.argv[2], module="main.pietto", kind="table",
    name="active_items", dialect="postgres", emission_contract="contract.json")
handle = pe.execute(query, route="postgres_rows",
    access=pe.PostgresAccess("127.0.0.1", 9, "app", "reader", "pw-impl", "disable"),
    premise=pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog")))
try:
    with handle:
        pass
except pe.AttemptFailed as error:
    print(json.dumps([error.code, error.detail, "psycopg" in sys.modules]))
"""


@pytest.mark.parametrize("impl", ("python", "c"))
def test_a_non_binary_psycopg_implementation_is_refused_before_the_import(
    example, tmp_path, impl
):
    """S01 inventory S2-f: psycopg reads PSYCOPG_IMPL when it is imported, and
    any implementation but binary would load a system libpq (the pure Python
    one searches for it with ldconfig); the attempt is refused first."""
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", IMPL_CHILD, str(ROOT / "src"), str(example)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        env=child_environment(PSYCOPG_IMPL=impl),
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["PIE-R2002", "POSTGRES_DRIVER_LIBRARY", False]


SELECTION_CHILD = r"""
import ctypes.util, glob, json, os, sys
src, copy, project, scenario, client, port, password = sys.argv[1:]
sys.path[:0] = [copy, src]
if scenario == "fallback":
    # psycopg-binary cannot be loaded, so psycopg falls back to its ctypes
    # implementation; psycopg-binary's own libpq stands in for the system
    # library that implementation searches for.
    import importlib.util
    package = os.path.dirname(importlib.util.find_spec("psycopg_binary").origin)
    (libpq,) = glob.glob(package + ".libs/libpq-*")
    search = ctypes.util.find_library
    ctypes.util.find_library = lambda name: libpq if name == "pq" else search(name)
    sys.modules["psycopg_binary.pq"] = None
elif scenario == "imported":
    import psycopg  # selects its implementation before PSYCOPG_IMPL is set
    os.environ["PSYCOPG_IMPL"] = "binary"
if client == "psycopg":
    import psycopg
    try:
        psycopg.connect(host="127.0.0.1", port=int(port), dbname="app",
            user="reader", password=password, sslmode="disable",
            gssencmode="disable", connect_timeout=5)
    except psycopg.OperationalError as error:
        result = type(error).__name__
else:
    import pietto.execution as pe
    from pietto._project import project_arrow_result
    project_arrow_result.pinned = lambda: None  # no PyArrow in the core profile
    query = pe.compile_query(project, module="main.pietto", kind="table",
        name="active_items", dialect="postgres", emission_contract="contract.json")
    handle = pe.execute(query, route="postgres_rows",
        access=pe.PostgresAccess("127.0.0.1", int(port), "app", "reader",
            password, "disable"),
        premise=pe.PostgresDeploymentPremise(schemas=("fixture", "pg_catalog")))
    try:
        with handle:
            pass
    except pe.AttemptFailed as error:
        result = [error.code, error.detail]
pq = sys.modules.get("psycopg.pq")
print(json.dumps([result, pq and [pq.__impl__, pq.PGconn.__module__]]))
"""


def _select(example, tmp_path, scenario, client, port, *, copy, impl=None):
    """One fresh interpreter: psycopg's implementation selection in
    `scenario`, then an attempt of the route (`client` "pietto") or a plain
    psycopg.connect. Returns the attempt's code and detail (or the driver
    error), the implementation psycopg selected (None if never imported) and
    the directory of the psycopg_c copy (written first on the path if `copy`)."""
    package = tmp_path / "copy" / "psycopg_c"
    if copy:
        api.write_psycopg_c(package.parent)
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            SELECTION_CHILD,
            str(ROOT / "src"),
            str(package.parent),
            str(example),
            scenario,
            client,
            str(port),
            PASSWORD,
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        timeout=120,
        env=child_environment(**({} if impl is None else {"PSYCOPG_IMPL": impl})),
    )
    assert result.returncode == 0, result.stderr
    return (*json.loads(result.stdout), package)


@pytest.mark.parametrize("impl", (None, "binary"))
def test_the_binary_implementation_reaches_the_server(example, tmp_path, impl):
    """With PSYCOPG_IMPL unset psycopg selects psycopg-binary's own module, and
    PSYCOPG_IMPL=binary ignores a psycopg_c copy on the path (the remedy for an
    installed psycopg-c); the attempt reaches the server under the route's
    rules."""
    with api.PostgresStub(auth="password") as stub:
        outcome, selected, package = _select(
            example, tmp_path, "binary", "pietto", stub.port, copy=bool(impl), impl=impl
        )
    assert outcome == ["PIE-R2004", None]
    assert selected == ["binary", "psycopg_binary.pq"]
    assert stub.events[0] == ("startup", "reader", "app") and not stub.replied
    assert not (package / "imported").exists()


# Whether a psycopg_c copy is first on the path, and the implementation
# psycopg selects there.
REFUSED_SELECTIONS = {
    "copy": (True, ["binary", "psycopg_c"]),
    "imported": (True, ["binary", "psycopg_c"]),
    "fallback": (False, ["python", "psycopg.pq.pq_ctypes"]),
}


@pytest.mark.parametrize("scenario", sorted(REFUSED_SELECTIONS))
def test_no_other_psycopg_implementation_receives_the_connection(
    example, tmp_path, sentinel, scenario
):
    """Trust item 4: with PSYCOPG_IMPL unset psycopg imports a findable
    psycopg_c first, so a copy that calls itself binary is refused before
    psycopg is imported. Whatever it claims, the implementation psycopg
    selected must be psycopg-binary's own module: the copy selected by an
    import before PSYCOPG_IMPL=binary was set, or the ctypes fallback of a
    binary that cannot be loaded, is refused before any connection value."""
    copy, selected = REFUSED_SELECTIONS[scenario]
    outcome, found, package = _select(
        example, tmp_path, scenario, "pietto", sentinel.port, copy=copy
    )
    assert outcome == ["PIE-R2002", "POSTGRES_DRIVER_LIBRARY"]
    assert found == (None if scenario == "copy" else selected)
    assert (package / "imported").exists() is (scenario == "imported")
    assert not (package / "received").exists() and not sentinel.connected()


@pytest.mark.parametrize("scenario", sorted(REFUSED_SELECTIONS))
def test_psycopg_itself_hands_those_implementations_the_password(
    example, tmp_path, scenario
):
    """Control: in the same state a plain psycopg.connect gives the password
    to the copy, or to the server through the ctypes implementation."""
    copy, selected = REFUSED_SELECTIONS[scenario]
    with api.PostgresStub(auth="password") as stub:
        outcome, found, package = _select(
            example, tmp_path, scenario, "psycopg", stub.port, copy=copy
        )
    assert (outcome, found) == ("OperationalError", selected) and stub.replied
    if copy:
        assert PASSWORD.encode() in (package / "received").read_bytes()


def test_a_loaded_psycopg_c_without_a_spec_has_the_driver_refusal(
    query, clean, sentinel
):
    clean.setitem(sys.modules, "psycopg_c", ModuleType("psycopg_c"))
    error = _attempt(query, access(sentinel.port))
    assert (error.code, error.detail) == ("PIE-R2002", "POSTGRES_DRIVER_LIBRARY")
    assert ended(error).transaction == "NOT_STARTED"
    assert PASSWORD not in str(error) and not sentinel.connected()


def _connecting(monkeypatch):
    """The real `_connect` and pinned psycopg; only PyArrow's import is
    replaced, since the core profile has no PyArrow."""
    monkeypatch.setattr(project_arrow_result, "pinned", lambda: None)


def _attempt(query, connection):
    handle = execution.execute(
        query, route="postgres_rows", access=connection, premise=PREMISE
    )
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle:
            pass
    return failed.value


@pytest.mark.parametrize("method", ("trust", "password", "md5", "gss", "sspi"))
def test_only_scram_reaches_authentication_and_no_password_is_sent(
    query, clean, method
):
    """Trust item 1b: whatever method the server asks for other than
    SCRAM-SHA-256, libpq gives up before answering, so no password, hash or
    token leaves the client, and the error explains how to create a SCRAM
    password role over TCP."""
    _connecting(clean)
    with api.PostgresStub(auth=method) as stub:
        error = _attempt(query, access(stub.port))
    assert stub.events[0] == ("startup", "reader", "app")
    assert not stub.replied, stub.events
    assert ("gssenc_request",) not in stub.events
    assert (error.code, error.failure.cause) == ("PIE-R2004", "OperationalError")
    assert "SCRAM-SHA-256" in str(error) and "pg_hba.conf" in str(error)
    assert PASSWORD not in str(error) and str(stub.port) not in str(error)
    assert ended(error).transaction == "NOT_STARTED"
    # The attempt's deadline timer was joined when it ended.
    timer = "pietto-deadline-" + str(error.attempt)
    assert not any(t.name == timer for t in threading.enumerate())


@pytest.mark.parametrize(
    "database",
    (
        "app options='-c search_path=evil' host=/tmp",
        "postgresql://elsewhere.invalid/other",
        "app' host='/tmp",
    ),
)
def test_connection_text_in_a_field_stays_one_literal_value(query, clean, database):
    """S01 inventory: libpq can read a database name as a connection string.
    The route's fields reach the server as literal values, so text such as
    options=, host= or a URI changes neither the host, the options nor the
    authentication rules."""
    _connecting(clean)
    with api.PostgresStub(auth="password") as stub:
        error = _attempt(
            query,
            execution.PostgresAccess(
                "127.0.0.1", stub.port, database, "reader", PASSWORD, "disable"
            ),
        )
    assert stub.events[0] == ("startup", "reader", database)
    assert stub.startup[b"options"].startswith(b"-c statement_timeout=")
    assert b"evil" not in stub.startup[b"options"] and not stub.replied
    assert error.code == "PIE-R2004"


def test_the_stub_sees_a_password_that_an_unpinned_client_sends():
    """Control: without require_auth the same stub receives the password."""
    import psycopg

    with api.PostgresStub(auth="password") as stub:
        with pytest.raises(psycopg.OperationalError):
            psycopg.connect(
                host="127.0.0.1",
                port=stub.port,
                dbname="app",
                user="reader",
                password=PASSWORD,
                sslmode="disable",
                gssencmode="disable",
                connect_timeout=5,
            )
    assert stub.replied


HOME_FILES = ("root.crt", "root.crl", "postgresql.crt", "postgresql.key")


def test_require_encrypts_without_reading_home_certificates(query, clean, tmp_path):
    """Trust item 1: `require` asks for TLS but names no CA, CRL, certificate
    or key, so libpq never opens ~/.postgresql even when the files exist; the
    unpinned control does open root.crt."""
    import psycopg

    _connecting(clean)
    home = tmp_path / "home"
    (home / ".postgresql").mkdir(parents=True)
    for name in HOME_FILES:
        (home / ".postgresql" / name).write_text("not a certificate\n")
    clean.setenv("HOME", str(home))
    with api.OpenWatch(home / ".postgresql") as watch:
        with api.PostgresStub(ssl=b"S") as stub:
            error = _attempt(query, access(stub.port, sslmode="require"))
        assert stub.events[:2] == [("ssl_request",), ("tls_hello", True)]
        assert error.code == "PIE-R2004"
        assert watch.opened() == []
        with api.PostgresStub(ssl=b"S") as control:
            with pytest.raises(psycopg.OperationalError):
                psycopg.connect(
                    host="127.0.0.1",
                    port=control.port,
                    dbname="app",
                    user="reader",
                    password=PASSWORD,
                    sslmode="require",
                    gssencmode="disable",
                    connect_timeout=5,
                )
        assert "root.crt" in watch.opened()


def test_require_never_continues_without_tls(query, clean):
    _connecting(clean)
    with api.PostgresStub(ssl=b"N") as stub:
        error = _attempt(query, access(stub.port, sslmode="require"))
    assert stub.events[0] == ("ssl_request",)
    assert not any(event[0] == "startup" for event in stub.events)
    assert error.code == "PIE-R2004"


def test_a_gssapi_request_reads_no_kerberos_input(query, clean, tmp_path):
    """Trust item 1b: asked for GSSAPI, the pinned client opens neither the
    Kerberos configuration nor the credential cache; the unpinned control
    opens both."""
    import psycopg

    _connecting(clean)
    kerberos = tmp_path / "kerberos"
    kerberos.mkdir()
    (kerberos / "krb5.conf").write_text("[libdefaults]\n default_realm = TEST\n")
    (kerberos / "ccache").write_bytes(b"\x05\x04")
    clean.setenv("KRB5_CONFIG", str(kerberos / "krb5.conf"))
    clean.setenv("KRB5CCNAME", "FILE:" + str(kerberos / "ccache"))
    with api.OpenWatch(kerberos) as watch:
        with api.PostgresStub(auth="gss") as stub:
            error = _attempt(query, access(stub.port))
        assert error.code == "PIE-R2004" and not stub.replied
        assert watch.opened() == []
        with api.PostgresStub(auth="gss") as control:
            with pytest.raises(psycopg.OperationalError):
                psycopg.connect(
                    host="127.0.0.1",
                    port=control.port,
                    dbname="app",
                    user="reader",
                    password=PASSWORD,
                    sslmode="disable",
                    gssencmode="disable",
                    connect_timeout=5,
                )
        assert {"krb5.conf", "ccache"} <= set(watch.opened())


def _profile(query, clean, connection_access, limits=None):
    """The attempt failure and the keyword arguments the route hands to
    psycopg.connect for one attempt; the fake driver refuses to connect."""
    import psycopg

    _connecting(clean)
    seen: dict[str, Any] = {}

    def connect(**fields):
        seen.update(fields)
        raise psycopg.OperationalError("refused by the test")

    clean.setattr(
        pg,
        "drivers",
        lambda: (SimpleNamespace(connect=connect, RawCursor="raw-cursor"),),
    )
    handle = execution.execute(
        query,
        route="postgres_rows",
        access=connection_access,
        premise=PREMISE,
        limits=execution.ExecutionLimits() if limits is None else limits,
    )
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle:
            pass
    return failed.value, seen


SESSION = (
    "-c client_encoding=UTF8 -c search_path=pg_catalog -c timezone=UTC"
    " -c standard_conforming_strings=on"
)


def test_the_connection_carries_the_explicit_profile_only(query, clean):
    """The exact options handed to libpq: the caller's access, TLS files under
    the null device, SCRAM-SHA-256 only and bound to the TLS channel, no GSS
    encryption, no client certificate and no password file; on the loopback
    `disable` exception nothing can be bound and the binding is off."""
    error, seen = _profile(
        query, clean, access(6543, host=HOST_MARKER, sslmode="require")
    )
    assert error.code == "PIE-R2004" and HOST_MARKER not in str(error)
    assert seen == {
        "host": HOST_MARKER,
        "port": 6543,
        "dbname": "app",
        "user": "reader",
        "password": PASSWORD,
        "sslmode": "require",
        "channel_binding": "require",
        "sslrootcert": "/dev/null/pietto-ca",
        "sslcrl": "/dev/null/pietto-crl",
        "sslcrldir": "/dev/null/pietto-crl-directory",
        "sslcert": "/dev/null/pietto-cert",
        "sslkey": "/dev/null/pietto-key",
        "require_auth": "scram-sha-256",
        "gssencmode": "disable",
        "sslcertmode": "disable",
        "passfile": "/dev/null",
        "connect_timeout": 10,
        "options": "-c statement_timeout=10000 " + SESSION,
        "application_name": "pietto_private_execution",
        "autocommit": True,
        "cursor_factory": "raw-cursor",
    }
    _error, loopback = _profile(query, clean, access(6543, sslmode="disable"))
    assert loopback == seen | {
        "host": "127.0.0.1",
        "sslmode": "disable",
        "channel_binding": "disable",
    }


def test_a_driver_error_alone_is_a_connection_failure(query, clean):
    """Before a session exists only the driver's own exception is PIE-R2004;
    any other exception there is unclassified (PIE-R3999), never advice about
    SCRAM or pg_hba.conf."""
    import psycopg

    assert pg.driver_error(psycopg.OperationalError("refused"))
    assert pg.driver_error(psycopg.errors.lookup("28P01")("invalid password"))
    assert not pg.driver_error(OSError("refused"))
    assert not pg.driver_error(RuntimeError("can't start new thread"))
    _connecting(clean)

    def refuse(**fields):
        raise OSError("not a driver failure")

    clean.setattr(
        pg, "drivers", lambda: (SimpleNamespace(connect=refuse, RawCursor=None),)
    )
    error = _attempt(query, access())
    assert (error.code, error.failure.cause) == ("PIE-R3999", "OSError")
    assert "pg_hba.conf" not in str(error)
    assert ended(error).transaction == "NOT_STARTED"


@pytest.mark.parametrize("missing", (False, True))
def test_a_null_device_that_is_not_one_is_refused_before_connecting(
    query, clean, missing
):
    """The TLS file options name children of /dev/null; if that is not the
    null character device, the attempt is refused before connecting under a
    detail that names it, not the refused-variable advice of PIE-R2003."""
    import stat as modes

    _connecting(clean)
    attempts: list[dict[str, Any]] = []

    def connect(**fields):
        attempts.append(fields)

    class Device:
        def __init__(self, path):
            assert path == "/dev/null"

        def stat(self):
            if missing:
                raise FileNotFoundError("/dev/null")
            return SimpleNamespace(st_mode=modes.S_IFREG | 0o644)

    clean.setattr(
        pg, "drivers", lambda: (SimpleNamespace(connect=connect, RawCursor=None),)
    )
    clean.setattr(pg, "Path", Device)
    error = _attempt(query, access())
    assert (error.code, error.detail) == ("PIE-R3999", "EXECUTION_NULL_DEVICE")
    assert attempts == [] and ended(error).transaction == "NOT_STARTED"


QUERY_SQL = "SELECT query"
PAGE_SQL = "WITH page SELECT 1"
STATEMENT_TIMEOUT = "SELECT pg_catalog.set_config('statement_timeout',$1,true)"


class Submitted(Exception):
    """Stops a reduced owner once its statement reached the native cursor."""


class LoggingCursor:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None, prepare=None):
        self.log.append((sql, params))
        if sql in (QUERY_SQL, PAGE_SQL):
            raise Submitted

    def fetchall(self):
        return [("off",)]  # a refined page reads JIT back before it runs


def _reduced_owner(remaining, log, *, refined):
    """A PostgreSQL rows owner reduced to the state its first statement reads,
    as in tests/test_postgres_refinement_jit.py."""
    owner = object.__new__(pg.PostgresExecution)
    page = SimpleNamespace(
        native=SimpleNamespace(sql=PAGE_SQL.encode(), arguments=(1,))
    )
    vars(owner).update(
        request=SimpleNamespace(
            route="postgres_rows",
            artifact=SimpleNamespace(rendered=SimpleNamespace(sql=QUERY_SQL.encode())),
        ),
        refined_request=object() if refined else None,
        enumeration=SimpleNamespace(
            progress=(0, 0, False), request_page=lambda: page, fail=lambda: None
        ),
        guards=None,
        _connection=SimpleNamespace(cursor=lambda: LoggingCursor(log)),
        _cancel=threading.Event(),
        _verify=lambda: None,
        _remaining=lambda: remaining,
        _finish=lambda commit: None,
        _primary=None,
        _source="NOT_STARTED",
        _submitted=False,
        _closed=False,
        _finalizing=False,
        _terminal=None,
        _lock=threading.Lock(),
        deadline_expired=False,
    )
    return owner


class CleanupInterrupt(BaseException):
    pass


class _CleanupStep:
    def __init__(self, log, name, error=None):
        self.log = log
        self.name = name
        self.error = error

    def close(self):
        self.log.append(self.name)
        if self.error is not None:
            raise self.error


class _CleanupControl:
    def __init__(self, log, error=None):
        self.log = log
        self.error = error

    def __enter__(self):
        return self

    def __exit__(self, *arguments):
        return False

    def execute(self, statement):
        self.log.append(statement)
        if self.error is not None:
            raise self.error


class _CleanupConnection:
    def __init__(
        self, log, *, transaction_error=None, close_error=None, discard_error=None
    ):
        self.log = log
        self.transaction_error = transaction_error
        self.close_error = close_error
        self.pgconn = SimpleNamespace(finish=self.finish)
        self.discard_error = discard_error

    def cursor(self):
        return _CleanupControl(self.log, self.transaction_error)

    def close(self):
        self.log.append("connection_close")
        if self.close_error is not None:
            raise self.close_error

    def finish(self):
        self.log.append("connection_discard")
        if self.discard_error is not None:
            raise self.discard_error


class _BlockingCancelConnection(_CleanupConnection):
    def __init__(self, log, entered, released):
        super().__init__(log)
        self.entered = entered
        self.released = released
        self.cancel_calls = 0

    def cancel_safe(self, *, timeout):
        self.cancel_calls += 1
        self.log.append(("cancel_safe", timeout))
        self.entered.set()
        assert self.released.wait(2)


class _CleanupTimer:
    def __init__(self, log, error=None):
        self.log = log
        self.error = error

    def cancel(self):
        self.log.append("timer_cancel")

    def join(self, timeout):
        self.log.append("timer_join")
        if self.error is not None:
            raise self.error

    def is_alive(self):
        return False


def _terminal_owner(*, cursor=None, connection=None, guard=None, timer=None):
    """A real rows owner at its existing finalization boundary."""
    owner = object.__new__(pg.PostgresExecution)
    vars(owner).update(
        attempt="terminal-attempt",
        request=SimpleNamespace(route=""),
        _lock=threading.Lock(),
        _closed=False,
        _finalizing=False,
        _terminal=None,
        _manual_cancel=False,
        _cancel=threading.Event(),
        _cancel_sent=False,
        _cancel_observed=False,
        _source="EXECUTING",
        _transaction="OPEN",
        _delivery="OPEN",
        _cleanup="OPEN",
        _primary=None,
        _cleanup_errors=[],
        deadline_expired=False,
        _owned_cursor=cursor,
        _cursor=cursor,
        _owned_connection=connection,
        _connection=connection,
        refined_request=None,
        _guard_control=None,
        guards=guard,
        enumeration=None,
        _timer=timer,
        _payloads=None,
        session_id=7,
    )
    return owner


def _private_outcome(owner):
    return _handle._outcome(owner, "postgres_rows", None)


@pytest.mark.parametrize("seconds,limit", ((60, 10000), (20, 10000), (4, 4000)))
def test_each_statement_is_limited_to_exactly_10_seconds(query, clean, seconds, limit):
    """The 10 second statement limit is Pietto's own: the session starts with
    statement_timeout 10000 ms, and the statement of a query or of a refined
    page sets it again right before it is submitted, never above 10000 ms and
    never above what is left of a shorter deadline."""
    _error, seen = _profile(
        query, clean, access(), execution.ExecutionLimits(seconds=seconds)
    )
    assert seen["options"] == f"-c statement_timeout={limit} " + SESSION
    clean.setattr(pg, "execution_arguments", lambda request: ())
    for refined, submitted in ((False, QUERY_SQL), (True, PAGE_SQL)):
        log: list[tuple[str, Any]] = []
        with pytest.raises(Submitted):
            next(_reduced_owner(float(seconds), log, refined=refined))
        assert log[0] == (STATEMENT_TIMEOUT, (str(limit),))
        assert log[-1][0] == submitted


@pytest.mark.parametrize(
    "commit,stage,expected_transaction",
    (
        (False, "guard_close", "ROLLBACK_ACK"),
        (False, "statement_close", "ROLLBACK_ACK"),
        (True, "transaction", "UNKNOWN"),
        (False, "connection_close", "ROLLBACK_ACK"),
        (False, "connection_discard", "ROLLBACK_ACK"),
        (False, "control_join", "ROLLBACK_ACK"),
    ),
)
def test_finalization_records_each_interrupt_then_reraises_it(
    commit, stage, expected_transaction
):
    """T1: bounded cleanup finishes before the same BaseException escapes."""
    log: list[str] = []
    interrupt = CleanupInterrupt(stage)
    cursor = _CleanupStep(
        log, "statement_close", interrupt if stage == "statement_close" else None
    )
    guard = _CleanupStep(
        log, "guard_close", interrupt if stage == "guard_close" else None
    )
    connection = _CleanupConnection(
        log,
        transaction_error=interrupt if stage == "transaction" else None,
        close_error=(
            interrupt
            if stage == "connection_close"
            else OSError("close")
            if stage == "connection_discard"
            else None
        ),
        discard_error=interrupt if stage == "connection_discard" else None,
    )
    timer = _CleanupTimer(log, interrupt if stage == "control_join" else None)
    owner = _terminal_owner(
        cursor=cursor, connection=connection, guard=guard, timer=timer
    )

    with pytest.raises(CleanupInterrupt) as raised:
        owner._finish(commit)

    assert raised.value is interrupt
    outcome = _private_outcome(owner)
    assert (owner._closed, outcome.transaction, outcome.cleanup) == (
        True,
        expected_transaction,
        "CLOSED" if stage == "transaction" else "FAILED",
    )
    expected_cleanup = {
        "transaction": [],
        "connection_discard": [
            ("connection_close", "OSError"),
            ("connection_discard", "CleanupInterrupt"),
        ],
    }.get(stage, [(stage, "CleanupInterrupt")])
    assert [
        (failure.phase, failure.cause) for failure in outcome.cleanup_failures
    ] == expected_cleanup
    if stage == "transaction":
        assert outcome.primary == execution.Failure(
            "PIE-R3006", "FINALIZATION", None, "transaction", None, "CleanupInterrupt"
        )
    assert log[-2:] == ["timer_cancel", "timer_join"]


def test_consumer_interrupt_survives_all_interrupting_cleanup_steps():
    """A cleanup interrupt is recorded but cannot replace the caller's KBI."""
    log: list[str] = []
    cleanup = CleanupInterrupt("cleanup")
    owner = _terminal_owner(
        cursor=_CleanupStep(log, "statement_close", cleanup),
        connection=_CleanupConnection(
            log, transaction_error=cleanup, close_error=cleanup, discard_error=cleanup
        ),
        guard=_CleanupStep(log, "guard_close", cleanup),
        timer=_CleanupTimer(log, cleanup),
    )
    original = KeyboardInterrupt("consumer")

    with pytest.raises(KeyboardInterrupt) as raised:
        try:
            raise original
        except KeyboardInterrupt as active:
            owner.__exit__(type(active), active, active.__traceback__)
            raise

    assert raised.value is original
    recorded = execution.Failure(
        "PIE-R3008", "INTERRUPTED", None, "consumer", None, "KeyboardInterrupt"
    )
    outcome = _handle._outcome(owner, "postgres_rows", recorded)
    assert outcome.primary == execution.Failure(
        "PIE-R3008", "INTERRUPTED", None, "consumer", None, "KeyboardInterrupt"
    )
    assert outcome.transaction == "UNKNOWN" and outcome.cleanup == "FAILED"
    assert [failure.phase for failure in outcome.cleanup_failures] == [
        "guard_close",
        "statement_close",
        "transaction",
        "connection_close",
        "connection_discard",
        "control_join",
    ]
    settled = outcome
    assert _handle._outcome(owner, "postgres_rows", recorded) == settled


def test_cancel_owns_the_active_statement_until_bounded_driver_cancel_returns():
    """The sole cross-thread operation cannot overlap statement teardown."""
    log: list[str] = []
    cancel_entered = threading.Event()
    cancel_release = threading.Event()
    cursor_closed = threading.Event()

    class Cursor(_CleanupStep):
        def close(self):
            super().close()
            cursor_closed.set()

    connection = _BlockingCancelConnection(log, cancel_entered, cancel_release)
    owner = _terminal_owner(
        cursor=Cursor(log, "statement_close"), connection=connection
    )
    canceller = threading.Thread(target=owner.cancel)
    canceller.start()
    assert cancel_entered.wait(2)

    finish_called = threading.Event()

    def finish():
        finish_called.set()
        owner._finish(False)

    finalizer = threading.Thread(target=finish)
    finalizer.start()
    assert finish_called.wait(2)
    assert not cursor_closed.is_set()
    cancel_release.set()
    canceller.join(2)
    finalizer.join(2)
    assert not canceller.is_alive() and not finalizer.is_alive()
    outcome = _private_outcome(owner)
    assert connection.cancel_calls == 1
    assert (
        outcome.end,
        outcome.cancel_requested,
        outcome.cancel_sent,
        outcome.cancel_observed,
    ) == (
        "CANCELLED",
        True,
        True,
        False,
    )
    assert (outcome.transaction, outcome.cleanup) == ("ROLLBACK_ACK", "CLOSED")


def test_cancel_wins_before_a_blocked_read_can_publish_eof_completion():
    """A read already at EOF cannot turn an earlier manual winner into COMPLETE."""
    log: list[str] = []
    entered = threading.Event()
    release = threading.Event()

    class Cursor(_CleanupStep):
        def fetchmany(self, count):
            assert count == 1
            entered.set()
            assert release.wait(2)
            return []

    connection = _BlockingCancelConnection(log, threading.Event(), threading.Event())
    owner = _terminal_owner(
        cursor=Cursor(log, "statement_close"), connection=connection
    )
    # This reduced owner reaches only route and batch_rows before the cursor boundary.
    owner.request = cast(
        ex.ExecutionRequest,
        SimpleNamespace(route="", limits=SimpleNamespace(batch_rows=1)),
    )
    owner._verify = lambda: None
    owner._remaining = lambda: 1
    owner._submitted = True
    owner._source = "READING"
    received: list[BaseException] = []

    def consume():
        try:
            next(owner)
        except BaseException as error:
            received.append(error)

    consumer = threading.Thread(target=consume)
    consumer.start()
    assert entered.wait(2)
    assert owner.cancel() == {
        "requested": True,
        "sent": False,
        "observed": False,
        "late": False,
    }
    release.set()
    consumer.join(2)
    assert not consumer.is_alive()
    assert len(received) == 1 and isinstance(received[0], ex.ExecutionError)
    outcome = _private_outcome(owner)
    assert (outcome.end, outcome.transaction, connection.cancel_calls) == (
        "CANCELLED",
        "ROLLBACK_ACK",
        0,
    )


def test_cancel_after_empty_fetch_before_eof_claim_never_commits():
    """The terminal winner is checked again after an empty read becomes known."""
    log: list[str] = []
    entered = threading.Event()
    release = threading.Event()

    class EmptyRows(list):
        def __bool__(self):
            entered.set()
            assert release.wait(2)
            return False

    class Cursor(_CleanupStep):
        def fetchmany(self, count):
            assert count == 1
            return EmptyRows()

    owner = _terminal_owner(
        cursor=Cursor(log, "statement_close"), connection=_CleanupConnection(log)
    )
    owner.request = cast(
        ex.ExecutionRequest,
        SimpleNamespace(route="", limits=SimpleNamespace(batch_rows=1)),
    )
    owner._verify = lambda: None
    owner._remaining = lambda: 1
    owner._submitted = True
    owner._source = "READING"
    handle = object.__new__(execution.ResultHandle)
    handle._owner = owner
    handle._route = "postgres_rows"
    handle._finalizer = None
    handle._recorded = None
    received: list[BaseException] = []

    def consume():
        try:
            next(handle)
        except BaseException as error:
            received.append(error)

    consumer = threading.Thread(target=consume)
    consumer.start()
    assert entered.wait(2)
    assert handle.cancel() is None
    release.set()
    consumer.join(2)
    assert not consumer.is_alive()
    assert len(received) == 1 and isinstance(received[0], execution.AttemptFailed)
    assert received[0].code == "PIE-R3009"
    assert handle.outcome.end == "CANCELLED"
    assert "COMMIT" not in log


def test_primary_failure_claim_blocks_a_late_deadline_during_its_cleanup():
    """The first primary claim survives a timer that reaches blocked cleanup."""
    log: list[str] = []
    entered = threading.Event()
    release = threading.Event()

    class Guard(_CleanupStep):
        def close(self):
            entered.set()
            assert release.wait(2)
            super().close()

    class Cursor(_CleanupStep):
        def fetchmany(self, count):
            raise ValueError("read failure")

    owner = _terminal_owner(
        cursor=Cursor(log, "statement_close"),
        connection=_CleanupConnection(log),
        guard=Guard(log, "guard_close"),
    )
    owner.request = cast(
        ex.ExecutionRequest,
        SimpleNamespace(route="", limits=SimpleNamespace(batch_rows=1)),
    )
    owner._verify = lambda: None
    owner._remaining = lambda: 1
    owner._submitted = True
    owner._source = "READING"
    received: list[BaseException] = []

    def consume():
        try:
            next(owner)
        except BaseException as error:
            received.append(error)

    consumer = threading.Thread(target=consume)
    consumer.start()
    assert entered.wait(2)
    owner._deadline()
    release.set()
    consumer.join(2)
    assert not consumer.is_alive()
    assert len(received) == 1 and isinstance(received[0], ValueError)
    outcome = _private_outcome(owner)
    assert outcome.primary is not None
    assert (outcome.end, outcome.deadline_expired, outcome.primary.cause) == (
        "FAILED",
        False,
        "ValueError",
    )


def test_locally_elapsed_deadline_claims_deadline_without_requesting_cancel(
    monkeypatch,
):
    """Clock expiry is a deadline terminal even when no timer ever requested I/O."""
    log: list[str] = []
    owner = _terminal_owner(
        cursor=_CleanupStep(log, "statement_close"), connection=_CleanupConnection(log)
    )
    owner.request = cast(
        ex.ExecutionRequest,
        SimpleNamespace(route="", limits=SimpleNamespace(seconds=1, batch_rows=1)),
    )
    owner._verify = lambda: None
    owner._started = 0
    owner._submitted = True
    owner._source = "READING"
    monkeypatch.setattr(pg.time, "monotonic", lambda: 1)
    handle = object.__new__(execution.ResultHandle)
    handle._owner = owner
    handle._route = "postgres_rows"
    handle._finalizer = None
    handle._recorded = None

    with pytest.raises(execution.AttemptFailed) as expired:
        next(handle)

    outcome = handle.outcome
    assert owner.deadline_expired is False
    assert (expired.value.code, outcome.end, outcome.deadline_expired) == (
        "PIE-R3001",
        "DEADLINE",
        True,
    )
    assert (outcome.cancel_requested, outcome.cancel_sent, outcome.cancel_observed) == (
        False,
        False,
        False,
    )
    assert outcome.transaction == "ROLLBACK_ACK"


def test_execution_interrupt_survives_an_interrupting_cleanup_step():
    """An executing KeyboardInterrupt remains the object the caller receives."""
    log: list[str] = []
    original = KeyboardInterrupt("statement")
    cleanup = CleanupInterrupt("statement close")

    class Cursor(_CleanupStep):
        def fetchmany(self, count):
            raise original

    owner = _terminal_owner(
        cursor=Cursor(log, "statement_close", cleanup),
        connection=_CleanupConnection(log),
    )
    owner.request = cast(
        ex.ExecutionRequest,
        SimpleNamespace(route="", limits=SimpleNamespace(batch_rows=1)),
    )
    owner._verify = lambda: None
    owner._remaining = lambda: 1
    owner._submitted = True
    owner._source = "READING"
    received: list[BaseException] = []

    def consume():
        try:
            next(owner)
        except BaseException as error:
            received.append(error)

    consumer = threading.Thread(target=consume)
    consumer.start()
    consumer.join(2)
    assert not consumer.is_alive() and received[0] is original
    outcome = _handle._outcome(
        owner,
        "postgres_rows",
        execution.Failure(
            "PIE-R3008", "INTERRUPTED", None, "interrupt", None, "KeyboardInterrupt"
        ),
    )
    assert outcome.primary is not None
    assert outcome.primary.cause == "KeyboardInterrupt"
    assert [(failure.phase, failure.cause) for failure in outcome.cleanup_failures] == [
        ("statement_close", "CleanupInterrupt")
    ]


def test_control_winner_blocks_late_send_before_open_and_after_close_or_eof():
    """Cancellation facts and the terminal winner freeze before any late control."""
    unopened = _terminal_owner()
    assert unopened.cancel() == {
        "requested": True,
        "sent": False,
        "observed": False,
        "late": False,
    }
    unopened._finish(False)
    assert (unopened._connection, _private_outcome(unopened).end) == (None, "CANCELLED")

    log: list[str] = []
    closed_connection = _BlockingCancelConnection(
        log, threading.Event(), threading.Event()
    )
    closed = _terminal_owner(
        cursor=_CleanupStep(log, "statement_close"), connection=closed_connection
    )
    closed.close()
    before_close_cancel = _private_outcome(closed)
    assert closed.cancel() == {
        "requested": False,
        "sent": False,
        "observed": False,
        "late": True,
    }
    assert _private_outcome(closed) == before_close_cancel
    assert (before_close_cancel.end, closed_connection.cancel_calls) == (
        "STOPPED_EARLY",
        0,
    )

    eof_connection = _BlockingCancelConnection(
        log, threading.Event(), threading.Event()
    )
    eof = _terminal_owner(
        cursor=_CleanupStep(log, "statement_close"), connection=eof_connection
    )
    eof._source = "EOF"
    eof._delivery = "COMPLETE"
    eof._terminal = "COMPLETE"
    eof._finish(True)
    before_eof_cancel = _private_outcome(eof)
    assert eof.cancel()["late"] is True
    assert _private_outcome(eof) == before_eof_cancel
    assert (before_eof_cancel.end, eof_connection.cancel_calls) == ("COMPLETE", 0)


def test_failed_driver_cancel_keeps_manual_winner_and_records_its_cleanup():
    log: list[str] = []

    class Connection(_CleanupConnection):
        def cancel_safe(self, *, timeout):
            assert timeout == 2
            raise OSError("cancel transport failed")

    owner = _terminal_owner(connection=Connection(log))
    owner.cancel()
    owner._finish(False)
    outcome = _private_outcome(owner)
    assert (
        outcome.end,
        outcome.cancel_requested,
        outcome.cancel_sent,
        outcome.cancel_observed,
    ) == (
        "CANCELLED",
        True,
        False,
        False,
    )
    assert [(failure.phase, failure.cause) for failure in outcome.cleanup_failures] == [
        ("cancel", "OSError")
    ]


def test_manual_and_deadline_controls_keep_separate_immutable_winners():
    manual = _terminal_owner()
    manual.cancel()
    manual._deadline()
    manual._finish(False)
    manual_outcome = _private_outcome(manual)
    assert (
        manual_outcome.end,
        manual_outcome.deadline_expired,
        manual_outcome.cancel_requested,
    ) == (
        "CANCELLED",
        False,
        True,
    )

    deadline = _terminal_owner()
    deadline._deadline()
    deadline.cancel()
    deadline._finish(False)
    deadline_outcome = _private_outcome(deadline)
    assert (
        deadline_outcome.end,
        deadline_outcome.deadline_expired,
        deadline_outcome.cancel_requested,
    ) == (
        "DEADLINE",
        True,
        True,
    )


def test_a_server_other_than_18_6_is_refused(query, clean):
    closed = []
    connection = SimpleNamespace(
        info=SimpleNamespace(server_version=180005, backend_pid=41),
        close=lambda: closed.append(True),
    )
    clean.setattr(pg, "_connect", lambda request: connection)
    error = _attempt(query, access())
    assert (error.code, error.detail) == ("PIE-R2005", "EXECUTION_TARGET_VERSION")
    outcome = ended(error)
    assert (outcome.end, outcome.transaction, outcome.cleanup) == (
        "FAILED",
        "NOT_STARTED",
        "CLOSED",
    )
    assert closed == [True]


class StubBatch:
    def __init__(self, rows=2, fail=None):
        self._batch = SimpleNamespace(num_rows=rows)
        self.fail = fail
        self.closed = False

    def __arrow_c_schema__(self):
        return "schema-capsule"

    def __arrow_c_array__(self, requested_schema=None):
        if self.fail is not None:
            raise ResultError(self.fail)
        return ("schema-capsule", "array-capsule")

    def close(self):
        self.closed = True


class StubOwner:
    """A duck-typed owner recording states as the PostgreSQL rows owner does.
    `finalization` is the failure its COMMIT or ROLLBACK records and `cleanup`
    the cleanup steps that fail, in order."""

    def __init__(self, steps, *, finalization=None, cleanup=()):
        self.attempt = "stub-attempt"
        self.steps = list(steps)
        self.calls = []
        self._closed = False
        self._terminal = None
        self.deadline_expired = False
        self.session_id = None
        self.source = self.transaction = self.delivery = "NOT_STARTED"
        self.cleanup = "NOT_STARTED"
        self.primary = None
        self.finalization = finalization
        self.failing_steps = tuple(cleanup)
        self.cleanup_failures = []
        self.rows = self.batches = 0
        self.cancel_requested = self.cancel_sent = self.cancel_observed = False

    @property
    def outcome(self):
        return ex.ExecutionOutcome(
            self.attempt,
            self.source,
            self.transaction,
            self.delivery,
            self.cleanup,
            self.rows,
            self.batches,
            0,
            self.primary,
            tuple(self.cleanup_failures),
            self.cancel_requested,
            self.cancel_sent,
            self.cancel_observed,
        )

    def open(self):
        if self._closed or self.transaction != "NOT_STARTED":
            raise ex.ExecutionError("EXECUTION_REUSE")
        self.calls.append("open")
        self.session_id, self.transaction, self.delivery = 7, "OPEN", "OPEN"
        return self

    def __next__(self):
        if self._closed:
            raise StopIteration
        if self.transaction == "NOT_STARTED":
            self.open()
        step = self.steps.pop(0)
        if step == "eof":
            self._terminal = "COMPLETE"
            self.source, self.delivery = "EOF", "COMPLETE"
            self._finish(True)
            if self.primary is not None or self.cleanup_failures:
                # As the owner does: one wrapper says that finalization failed.
                if self.primary is None:
                    self.primary = ex.ExecutionFailure("finalization", "ExecutionError")
                self.delivery = "FAILED"
                raise ex.ExecutionError("EXECUTION_FINALIZATION")
            raise StopIteration
        if isinstance(step, BaseException):
            if step.args == ("deadline",):
                self.deadline_expired = True
                self.cancel_requested = True
                self._terminal = "DEADLINE"
                step = ex.ExecutionError("EXECUTION_CANCELED")
            elif isinstance(step, TimeoutError) and step.args == (
                "EXECUTION_DEADLINE",
            ):
                self._terminal = "DEADLINE"
            elif self._terminal is None:
                self._terminal = "FAILED"
            if self.primary is None:
                self.primary = ex.ExecutionFailure("read", type(step).__name__)
            self.source = self.delivery = "FAILED"
            self._finish(False)
            raise step
        self.source = "READING"
        self.rows += step._batch.num_rows
        self.batches += 1
        return step

    def _finish(self, commit):
        if not self._closed:
            if self.transaction == "OPEN" and self.finalization is not None:
                self.transaction = "UNKNOWN"
                if self.primary is None:
                    self.primary = self.finalization
                else:
                    self.cleanup_failures.append(self.finalization)
            elif self.transaction == "OPEN":
                self.transaction = "COMMIT_ACK" if commit else "ROLLBACK_ACK"
            self.cleanup_failures.extend(
                ex.ExecutionFailure(step, "OSError") for step in self.failing_steps
            )
            self._closed = True
            self.cleanup = "FAILED" if self.cleanup_failures else "CLOSED"
            self.calls.append("finish")

    def close(self):
        if not self._closed:
            if self._terminal is None:
                self._terminal = "STOPPED_EARLY"
            if self.source != "EOF":
                self.source = "EARLY_CLOSE"
                if self.delivery != "FAILED":
                    self.delivery = "INCOMPLETE"
            self._finish(False)

    def cancel(self, *, deadline=False):
        if not self._closed and self._terminal is None:
            self.cancel_requested = True
            self.deadline_expired = deadline
            self._terminal = "DEADLINE" if deadline else "CANCELLED"
            self.source = self.delivery = "FAILED"
            self._finish(False)

    def __exit__(self, kind, error, traceback):
        if error is not None and self.primary is None:
            if self._terminal is None:
                self._terminal = "FAILED"
            self.primary = ex.ExecutionFailure("consumer", type(error).__name__)
            self.delivery = "FAILED"
        self.close()
        return False


def _stubbed(query, monkeypatch, steps, **options):
    owner = StubOwner(steps, **options)
    monkeypatch.setattr(composition, "prepare_attempt", lambda *a, **k: owner)
    handle = execution.execute(
        query, route="postgres_rows", access=access(), premise=PREMISE
    )
    return handle, owner


def test_manual_cancel_is_the_only_cross_thread_handle_control(query, monkeypatch):
    handle, owner = _stubbed(query, monkeypatch, [StubBatch(), "eof"])
    assert handle.cancel() is None
    outcome = handle.outcome
    assert (outcome.end, outcome.cancel_requested, outcome.cancel_sent) == (
        "CANCELLED",
        True,
        False,
    )
    assert handle.cancel() is None and handle.outcome == outcome


def test_reading_to_the_end_commits_and_completes(query, monkeypatch):
    handle, owner = _stubbed(query, monkeypatch, [StubBatch(), StubBatch(3), "eof"])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with handle as result:
            batches = list(result)
        del handle, result
        gc.collect()
    assert [b.num_rows for b in batches] == [2, 3]
    assert repr(batches[0]) == "ResultBatch(num_rows=2)"
    outcome = composition.attempt_facts(owner)[3]
    assert (outcome.source, outcome.transaction) == ("EOF", "COMMIT_ACK")
    assert caught == []


def test_outcomes_name_complete_stopped_failed_and_deadline(query, monkeypatch):
    complete, _ = _stubbed(query, monkeypatch, [StubBatch(), "eof"])
    assert complete.outcome.end == "NOT_STARTED"
    with complete:
        assert complete.outcome.end == "OPEN"
        list(complete)
    outcome = complete.outcome
    assert (outcome.end, outcome.transaction, outcome.remote_source_use_end) == (
        "COMPLETE",
        "COMMIT_ACK",
        "TRANSACTION_ACK",
    )
    assert (outcome.rows, outcome.batches, outcome.primary) == (2, 1, None)
    assert (
        outcome.premise_compliance,
        outcome.native_definition_lifetime_exclusion,
    ) == (
        "NOT_INDEPENDENTLY_VERIFIED",
        "NOT_DEMONSTRATED",
    )

    stopped, _ = _stubbed(query, monkeypatch, [StubBatch(), StubBatch(), "eof"])
    with stopped:
        next(stopped)
    assert (stopped.outcome.end, stopped.outcome.transaction) == (
        "STOPPED_EARLY",
        "ROLLBACK_ACK",
    )

    failing, _ = _stubbed(
        query, monkeypatch, [StubBatch(), ResultError("VALUE_DOMAIN")]
    )
    with pytest.raises(execution.AttemptFailed) as failed:
        with failing:
            list(failing)
    assert (failed.value.code, failed.value.detail) == ("PIE-R3005", "VALUE_DOMAIN")
    assert failed.value.outcome == failing.outcome
    assert (failing.outcome.end, failing.outcome.primary) == (
        "FAILED",
        failed.value.failure,
    )
    assert failed.value.__context__ is None and failed.value.__cause__ is None
    with pytest.raises(StopIteration):
        next(failing)

    late, _ = _stubbed(query, monkeypatch, [StubBatch(), RuntimeError("deadline")])
    with pytest.raises(execution.AttemptFailed) as expired:
        list(late)
    assert (expired.value.code, late.outcome.end) == ("PIE-R3001", "DEADLINE")


def test_caller_exceptions_pass_through_and_are_recorded(query, monkeypatch):
    handle, _ = _stubbed(query, monkeypatch, [StubBatch(), "eof"])
    mine = ValueError("the caller's own error")
    with pytest.raises(ValueError) as raised:
        with handle:
            raise mine
    assert raised.value is mine
    primary = handle.outcome.primary
    assert primary is not None
    assert (primary.code, primary.phase, primary.cause) == (
        "PIE-R3007",
        "consumer",
        "ValueError",
    )
    assert handle.outcome.end == "FAILED"

    interrupted, _ = _stubbed(query, monkeypatch, [KeyboardInterrupt()])
    with pytest.raises(KeyboardInterrupt):
        next(interrupted)
    primary = interrupted.outcome.primary
    assert primary is not None and primary.code == "PIE-R3008"


def test_a_terminal_outcome_does_not_change_after_the_attempt_ended(query, monkeypatch):
    """An exception raised in the with block after the attempt was read to the
    end, or after close(), passes through and leaves the outcome as reached."""
    complete, owner = _stubbed(query, monkeypatch, [StubBatch(), "eof"])
    mine = ValueError("raised after the end")
    seen: list[execution.Outcome] = []
    with pytest.raises(ValueError) as raised:
        with complete:
            list(complete)
            seen.append(complete.outcome)
            raise mine
    assert raised.value is mine
    assert [complete.outcome] == seen
    assert (seen[0].end, seen[0].transaction, seen[0].delivery, seen[0].primary) == (
        "COMPLETE",
        "COMMIT_ACK",
        "COMPLETE",
        None,
    )
    assert owner.primary is None

    stopped, owner = _stubbed(query, monkeypatch, [StubBatch(), StubBatch(), "eof"])
    seen.clear()
    with pytest.raises(ValueError):
        with stopped:
            next(stopped)
            stopped.close()
            seen.append(stopped.outcome)
            raise ValueError("raised after close")
    assert [stopped.outcome] == seen
    assert (seen[0].end, seen[0].transaction, seen[0].primary) == (
        "STOPPED_EARLY",
        "ROLLBACK_ACK",
        None,
    )
    assert owner.primary is None


def test_a_finalization_failure_keeps_the_identity_the_owner_recorded(
    query, monkeypatch
):
    """PIE-R3006: a COMMIT failing at the end of the result and a ROLLBACK
    failing in close() report the same failure, with the phase, SQLSTATE and
    driver class the owner recorded, not the owner's finalization wrapper."""
    record = ex.ExecutionFailure("transaction", "SerializationFailure", "40001")
    expected = execution.Failure(
        "PIE-R3006",
        "FINALIZATION",
        None,
        "transaction",
        "40001",
        "SerializationFailure",
    )
    at_end, _ = _stubbed(query, monkeypatch, [StubBatch(), "eof"], finalization=record)
    with pytest.raises(execution.AttemptFailed) as failed:
        with at_end:
            list(at_end)
    assert failed.value.failure == expected
    assert failed.value.__cause__ is None and failed.value.__context__ is None
    outcome = at_end.outcome
    assert failed.value.outcome == outcome and outcome.primary == expected
    assert (outcome.end, outcome.source, outcome.transaction, outcome.cleanup) == (
        "FAILED",
        "EOF",
        "UNKNOWN",
        "CLOSED",
    )
    assert outcome.remote_source_use_end == "REMOTE_QUIESCENCE_UNCONFIRMED"

    in_close, _ = _stubbed(
        query, monkeypatch, [StubBatch(), "eof"], finalization=record
    )
    with in_close:
        next(in_close)
    outcome = in_close.outcome
    assert outcome.primary == expected
    assert (outcome.end, outcome.source, outcome.transaction) == (
        "FAILED",
        "EARLY_CLOSE",
        "UNKNOWN",
    )


def test_cleanup_failures_follow_the_primary_in_their_order(query, monkeypatch):
    """PIE-R5001: cleanup steps that fail after the primary are listed in the
    order they failed and never replace it. A cleanup failure after the
    result was read to the end and COMMIT acknowledged ends the attempt
    FAILED with PIE-R3006 in phase finalization; in close() before the end
    the same failure leaves STOPPED_EARLY without a primary."""
    steps = ("statement_close", "connection_close")
    failing, _ = _stubbed(
        query,
        monkeypatch,
        [StubBatch(), ResultError("VALUE_DOMAIN")],
        cleanup=steps,
    )
    with pytest.raises(execution.AttemptFailed) as failed:
        with failing:
            list(failing)
    outcome = failing.outcome
    assert (failed.value.code, outcome.primary) == ("PIE-R3005", failed.value.failure)
    assert (outcome.end, outcome.transaction, outcome.cleanup) == (
        "FAILED",
        "ROLLBACK_ACK",
        "FAILED",
    )
    assert outcome.cleanup_failures == tuple(
        execution.Failure("PIE-R5001", "CLEANUP_FAILED", None, step, None, "OSError")
        for step in steps
    )

    closing, _ = _stubbed(
        query, monkeypatch, [StubBatch(), "eof"], cleanup=("connection_close",)
    )
    with pytest.raises(execution.AttemptFailed) as failed:
        with closing:
            list(closing)
    outcome = closing.outcome
    assert failed.value.failure == execution.Failure(
        "PIE-R3006", "FINALIZATION", None, "finalization", None, "ExecutionError"
    )
    assert (
        outcome.end,
        outcome.source,
        outcome.transaction,
        outcome.delivery,
        outcome.cleanup,
    ) == ("FAILED", "EOF", "COMMIT_ACK", "FAILED", "FAILED")
    assert outcome.primary == failed.value.failure
    assert [(f.code, f.phase) for f in outcome.cleanup_failures] == [
        ("PIE-R5001", "connection_close")
    ]

    # The same cleanup failure in close() before the end has no primary.
    stopped, _ = _stubbed(
        query, monkeypatch, [StubBatch(), "eof"], cleanup=("connection_close",)
    )
    with stopped:
        next(stopped)
    outcome = stopped.outcome
    assert (outcome.end, outcome.transaction, outcome.cleanup, outcome.primary) == (
        "STOPPED_EARLY",
        "ROLLBACK_ACK",
        "FAILED",
        None,
    )
    assert [(f.code, f.phase) for f in outcome.cleanup_failures] == [
        ("PIE-R5001", "connection_close")
    ]


def test_a_deadline_found_before_its_timer_fired_ends_as_deadline(query, monkeypatch):
    """A check that finds the deadline passed (PIE-R3001) before the timer set
    the owner's flag still ends the attempt as DEADLINE."""
    handle, owner = _stubbed(query, monkeypatch, [TimeoutError("EXECUTION_DEADLINE")])
    with pytest.raises(execution.AttemptFailed) as expired:
        list(handle)
    outcome = handle.outcome
    assert owner.deadline_expired is False
    assert (expired.value.code, outcome.end, outcome.deadline_expired) == (
        "PIE-R3001",
        "DEADLINE",
        True,
    )


def test_a_handle_runs_its_attempt_once(query, monkeypatch):
    handle, owner = _stubbed(query, monkeypatch, [StubBatch(), "eof"])
    with handle:
        list(handle)
    before = handle.outcome
    for again in (handle.__enter__, lambda: next(handle)):
        try:
            again()
        except execution.HandleMisuse as misuse:
            assert misuse.code == "PIE-R4001"
        except StopIteration:
            pass
    assert handle.outcome == before and owner.calls == ["open", "finish"]


def test_a_dropped_open_handle_warns_and_does_no_io(query, monkeypatch):
    """G05: garbage-collecting an open handle issues PIE-R5002 with the
    DROPPED snapshot and does not close, cancel or contact anything."""
    handle, owner = _stubbed(query, monkeypatch, [StubBatch(), "eof"])
    handle.__enter__()
    attempt = handle.attempt
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        del handle
        gc.collect()
    dropped = [w.message for w in caught if isinstance(w.message, ResourceWarning)]
    assert len(dropped) == 1
    warning = dropped[0]
    assert isinstance(warning, execution.UnclosedHandleWarning)
    assert warning.code == "PIE-R5002" and warning.outcome.end == "DROPPED"
    assert warning.outcome.attempt == attempt and attempt in str(warning)
    assert owner.calls == ["open"]


def test_unopened_and_closed_handles_drop_silently(query, monkeypatch):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        unopened, _ = _stubbed(query, monkeypatch, [StubBatch(), "eof"])
        closed, _ = _stubbed(query, monkeypatch, [StubBatch(), "eof"])
        closed.__enter__()
        closed.close()
        del unopened, closed
        gc.collect()
    assert [w for w in caught if isinstance(w.message, ResourceWarning)] == []


def test_a_batch_is_exported_until_it_is_closed(query, monkeypatch):
    handle, _ = _stubbed(
        query, monkeypatch, [StubBatch(), StubBatch(fail="INTEROP_REQUEST"), "eof"]
    )
    with handle:
        first, second = next(handle), next(handle)
        assert first.__arrow_c_schema__() == "schema-capsule"
        assert first.__arrow_c_array__() == ("schema-capsule", "array-capsule")
        with pytest.raises(execution.HandleMisuse) as transfer:
            second.__arrow_c_array__("requested")
        assert (transfer.value.code, transfer.value.detail) == (
            "PIE-R4003",
            "INTEROP_REQUEST",
        )
        with first:
            pass
        assert first.closed and repr(first) == "ResultBatch(num_rows=2, closed=True)"
        for export in (first.__arrow_c_schema__, first.__arrow_c_array__):
            with pytest.raises(execution.HandleMisuse) as closed:
                export()
            assert closed.value.code == "PIE-R4002"
    with pytest.raises(TypeError):
        execution.ResultBatch()
