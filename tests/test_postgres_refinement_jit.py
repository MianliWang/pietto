"""Generated refinement pages on the two new PostgreSQL routes turn JIT off for
the rest of their transaction and read the setting back before each page."""

import threading
from types import SimpleNamespace

import pytest

from pietto._project import project_execution_postgres as rows
from pietto._project import project_execution_postgres_adbc as adbc
from pietto._project.project_execution import ExecutionError
from pietto._project.project_execution_postgres import PostgresExecution
from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution
from pietto._project.project_execution_postgres_adbc_native import JIT_OFF_SQL

TIMEOUT = "SELECT pg_catalog.set_config('statement_timeout',$1,true)"
PAGE = "WITH page SELECT 1"
QUERY = "SELECT query"
GUARD = "SELECT guard"


class Submitted(Exception):
    """Stops an attempt once its statement reached the native cursor."""


class Cursor:
    def __init__(self, log, readback):
        self.log, self.readback, self.sql = log, readback, None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None, prepare=None):
        self.sql = sql
        self.log.append(sql)
        if sql in (PAGE, QUERY, GUARD):
            raise Submitted

    def fetchall(self):
        assert self.sql == JIT_OFF_SQL
        return [(self.readback,)]


def rows_owner(route, readback, log):
    """A Psycopg owner reduced to the state its refined page path reads."""
    owner = object.__new__(PostgresExecution)
    page = SimpleNamespace(native=SimpleNamespace(sql=PAGE.encode(), arguments=(1,)))
    vars(owner).update(
        request=SimpleNamespace(route=route),
        enumeration=SimpleNamespace(
            progress=(0, 0, False), request_page=lambda: page, fail=lambda: None
        ),
        _connection=SimpleNamespace(cursor=lambda: Cursor(log, readback)),
        _cancel=threading.Event(),
        _verify=lambda: None,
        _remaining=lambda: 5.0,
        _finish=lambda commit: log.append(("finish", commit)),
        _primary=None,
        _source="NOT_STARTED",
        _submitted=False,
    )
    return owner


@pytest.mark.parametrize(
    ("route", "controls"),
    [("postgres_rows", [TIMEOUT, JIT_OFF_SQL]), ("", [TIMEOUT])],
)
def test_psycopg_every_page_follows_its_controls(route, controls):
    log = []
    owner = rows_owner(route, "off", log)
    with pytest.raises(Submitted):
        owner._next_refined_page()
    # The state a committed first page leaves before the next page is requested.
    vars(owner).update(_submitted=True)
    vars(owner)["enumeration"].progress = (2, 1, False)
    with pytest.raises(Submitted):
        owner._next_refined_page()
    assert log == [*controls, PAGE, ("finish", False)] * 2


def test_psycopg_query_and_separate_guard_keep_the_server_jit(monkeypatch):
    monkeypatch.setattr(rows, "execution_arguments", lambda request: ())
    log = []
    query = rows_owner("postgres_rows", "off", log)
    vars(query).update(
        refined_request=None,
        guards=None,
        _submitted=False,
        _closed=False,
        request=SimpleNamespace(
            route="postgres_rows",
            artifact=SimpleNamespace(rendered=SimpleNamespace(sql=QUERY.encode())),
        ),
    )
    with pytest.raises(Submitted):
        next(query)
    guard = rows_owner("postgres_rows", "off", log)
    vars(guard).update(
        guards=SimpleNamespace(
            context=SimpleNamespace(separate_allowed=True),
            states=("DYNAMIC",),
            prepare_submission=lambda owner: SimpleNamespace(
                sql=GUARD.encode(), arguments=()
            ),
        ),
        guard_events=[],
        attempt="attempt",
    )
    with pytest.raises(Submitted):
        guard._fulfill_separate_guards()
    assert log == [TIMEOUT, QUERY, ("finish", False), GUARD]


def test_psycopg_page_is_never_submitted_without_jit_off():
    log = []
    with pytest.raises(ExecutionError, match="^EXECUTION_CONTEXT$"):
        rows_owner("postgres_rows", "on", log)._next_refined_page()
    assert log == [TIMEOUT, JIT_OFF_SQL, ("finish", False)]


def adbc_owner(monkeypatch, readback, log):
    """An ADBC owner reduced to the state its shared submission reads."""

    def read(owner, sql, arguments=(), tags=(), *, maximum=1024, finalizing=False):
        log.append(sql)
        return (), ((readback,),) if sql == JIT_OFF_SQL else (("10s",),), None

    class Statement:
        def __init__(self, owner, sql, arguments, tags, purpose, *, copy):
            log.append(sql)

        def execute(self, maximum):
            return ()

    monkeypatch.setattr(adbc, "read_control", read)
    monkeypatch.setattr(adbc, "NativeStatement", Statement)
    owner = object.__new__(PostgresADBCExecution)
    vars(owner).update(
        _verify=lambda: None,
        _remaining=lambda: 5.0,
        _refresh=lambda: None,
        _parameters=lambda purpose: (purpose.upper(), (), ()),
    )
    return owner


@pytest.mark.parametrize(
    ("purpose", "controls"),
    [("page", [TIMEOUT, JIT_OFF_SQL]), ("guard", [TIMEOUT]), ("query", [TIMEOUT])],
)
def test_adbc_only_pages_turn_jit_off(monkeypatch, purpose, controls):
    log = []
    owner = adbc_owner(monkeypatch, "off", log)
    owner._submit(purpose, 1)
    owner._submit(purpose, 1)
    assert log == [*controls, purpose.upper()] * 2


def test_adbc_page_is_never_submitted_without_jit_off(monkeypatch):
    log = []
    owner = adbc_owner(monkeypatch, "on", log)
    with pytest.raises(ExecutionError, match="^POSTGRES_ADBC_NATIVE_CONTEXT$"):
        owner._submit("page", 1)
    assert log == [TIMEOUT, JIT_OFF_SQL]
