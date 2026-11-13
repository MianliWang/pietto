"""Control statements of refinement attempts on the two PostgreSQL routes:
pages turn JIT off for the rest of their transaction and read the setting back
before each page, and an attempt that reads `now()` reads its statement time
once."""

import threading
from types import SimpleNamespace

import pytest

from _pietto_execution_refinement import CLOCK, live_refinement, now_project
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
CLOCK_READ = (
    "SELECT pg_catalog.to_char(pg_catalog.statement_timestamp() AT TIME ZONE"
    " 'UTC', 'YYYY-MM-DD HH24:MI:SS.US')"
)


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
        assert self.sql in (JIT_OFF_SQL, CLOCK_READ)
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
        _lock=threading.Lock(),
        _closed=False,
        _finalizing=False,
        _terminal=None,
        deadline_expired=False,
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
        rows = ((readback,),) if sql in (JIT_OFF_SQL, CLOCK_READ) else (("10s",),)
        return (), rows, None

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


@pytest.fixture(scope="module")
def refinements(tmp_path_factory):
    project = now_project(
        tmp_path_factory.mktemp("clock") / "project",
        "table plain:\n    from items\n    select:\n        id\n"
        "table seen:\n    from items\n    select:\n        id\n"
        "        seen = now()\n",
    )
    return {name: live_refinement(project, name) for name in ("plain", "seen")}


@pytest.mark.parametrize("route", ("postgres_rows", "postgres_adbc"))
def test_an_attempt_reads_its_statement_time_once_where_now_is_read(
    monkeypatch, refinements, route
):
    """No read without `now()` or with a recovery's recorded time; otherwise
    exactly one server read, which must be canonical Timestamp text."""

    def owner(readback, name, clock=None):
        log = []
        if route == "postgres_rows":
            result = rows_owner(route, readback, log)
        else:
            result = adbc_owner(monkeypatch, readback, log)
        vars(result)["refined_request"] = SimpleNamespace(
            refinement=refinements[name], clock=clock
        )
        return result, log

    plain, log = owner(CLOCK, "plain")
    assert plain._statement_clock() is None and log == []
    read, log = owner(CLOCK, "seen")
    assert read._statement_clock() == CLOCK and log == [CLOCK_READ]
    recorded, log = owner("2000-01-01 00:00:00.000000", "seen", CLOCK)
    assert recorded._statement_clock() == CLOCK and log == []
    for text in (
        CLOCK.replace(" ", "T"),
        CLOCK + "\n",
        "infinity",
        CLOCK + "+00:00",
        CLOCK + "Z",
    ):
        bad, log = owner(text, "seen")
        with pytest.raises(ExecutionError, match="^EXECUTION_CONTEXT$"):
            bad._statement_clock()
        assert log == [CLOCK_READ]
    # A canceled or failed read keeps its own code.
    canceled, log = owner(CLOCK, "seen")
    if route == "postgres_rows":
        vars(canceled)["_cancel"].set()
    else:

        def cancel(*args, **kwargs):
            raise ExecutionError("EXECUTION_CANCELED")

        monkeypatch.setattr(adbc, "read_control", cancel)
    with pytest.raises(ExecutionError, match="^EXECUTION_CANCELED$"):
        canceled._statement_clock()
    assert log == []
