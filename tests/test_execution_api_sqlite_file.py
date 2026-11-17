"""The `sqlite_file` execution route: its request checks, the defences of
its read-only open of the caller's file, the source check in the attempt's
read transaction, and the attempt's lifecycle (docs/spec/sqlite-project-v1.md,
"Execution"; PL.47). Native cells open test-owned files on Linux x86-64 with
the measured SQLite build, under the SQLite class of the `native` fixture
(lesson 80-2), and need PyArrow; each control cell shows the harm that its
defence prevents, and a result is judged by its types as well as its values.
The request checks run everywhere, Windows CI included, where the two cells
that need POSIX skip themselves."""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import math
import os
import pickle
import platform
import sqlite3
import sys
import threading
import time
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from typing import Any

import pytest

import _pietto_execution_api as api
import _pietto_sql_sqlite as files

from pietto import execution
from pietto._project import project_sqlite_result as results
from pietto._project.project_result_contract import ResultError
from pietto.execution import _sqlite as route
from pietto.sql.sqlite import QUALIFIED_SQLITE_BUILD

SCHEMA = (
    "CREATE TABLE orders (id INTEGER NOT NULL, amount INTEGER NOT NULL,"
    " note TEXT, ok INTEGER NOT NULL, price REAL NOT NULL) STRICT"
)
ROWS = ((1, 5, "a", 1, 1.5), (2, 7, None, 0, 2.5), (3, 9, "b", 1, -1.0))
FILTERED = """query q(low: Int, word: Text | None):
    from orders
    where amount > low and note == word
    select:
        id
        note
        ok
        price
"""
GROUPED = """query result(v: Int, t: Text):
    from orders
    where amount > v
    group by:
        ok
    select:
        ok
        n = count()
        d = count_distinct(note)
        a = avg(amount)
        s = sum(id)
        low = min(price)
    having n > 0 or t == "x"
    order by:
        ok
"""
SUM = "query result:\n    from orders\n    select:\n        s = sum(id)\n"
WINDOW_SUM = SUM.replace("sum(id)", "sum(id) window(order by id)")
WINDOWS = """query result:
    from orders
    select:
        id
        r = rank() window(partition by ok order by amount desc)
        n = row_number() window(order by id)
        d = dense_rank() window(order by note)
        c = count(price) window(partition by ok)
        s = sum(id) window(order by id)
"""
FLOAT = "query f(x: Float):\n    from orders\n    where price > x\n    select:\n        id\n"
MAX = 2**63 - 1
# The result columns of FILTERED and GROUPED: name, Arrow type, nullable.
COLUMNS = (
    ("id", "int64", False),
    ("note", "string", True),
    ("ok", "bool", False),
    ("price", "double", False),
)
GROUPED_COLUMNS = (
    ("ok", "bool", False),
    ("n", "int64", False),
    ("d", "int64", False),
    ("a", "double", True),
    ("s", "int64", True),
    ("low", "double", True),
)
FIRST = (1, "a", True, 1.5)
GROUPS = [(False, 1, 0, 7.0, 2, 2.5), (True, 2, 2, 7.0, 4, -1.0)]
# Applied to each native cell: see the `native` fixture.
NATIVE = pytest.mark.usefixtures("native")


def _pyarrow() -> Any:
    return pytest.importorskip("pyarrow", reason="results are Arrow batches")


def _contract(**ranges: tuple[int, int]) -> dict[str, Any]:
    """The helper's contract, with an `int_range` for each named Int field."""
    document = files.contract()
    for field in document["sources"][0]["fields"]:
        if field["name"] in ranges:
            low, high = ranges[field["name"]]
            field["representation"]["domain"].update(min=str(low), max=str(high))
    return document


def _compiled(
    root: Path, body: str = FILTERED, document: dict[str, Any] | None = None
) -> execution.CompiledQuery:
    kind = "query" if body.startswith("query") else "table"
    name = body.split("(")[0].split(":")[0].split()[-1]
    files.write(root, body, _contract() if document is None else document)
    return execution.compile_query(
        root,
        module="main.pietto",
        kind=kind,
        name=name,
        dialect="sqlite",
        emission_contract="contract.json",
    )


@pytest.fixture(scope="module")
def filtered_query(tmp_path_factory: pytest.TempPathFactory) -> execution.CompiledQuery:
    return _compiled(tmp_path_factory.mktemp("filtered") / "p")


def _database(
    path: Path,
    rows: tuple[tuple[object, ...], ...] = ROWS,
    schema: str = SCHEMA,
    *setup: str,
) -> Path:
    with closing(sqlite3.connect(path)) as connection:
        for statement in setup:
            connection.execute(statement)
        connection.execute(schema)
        if rows:
            marks = ", ".join("?" * len(rows[0]))
            connection.executemany(f"INSERT INTO orders VALUES ({marks})", rows)
        connection.commit()
    return path


ARGUMENTS = {"low": 4, "word": "a"}


def _handle(query: Any, path: Any, **arguments: Any) -> Any:
    arguments = {"parameters": ARGUMENTS, **arguments}
    return execution.execute(
        query,
        route="sqlite_file",
        access=execution.SQLiteFileInput(path),
        premise=None,
        **arguments,
    )


def _refusal(query: Any, **arguments: Any) -> tuple[str, str | None]:
    arguments = {"route": "sqlite_file", "premise": None, **arguments}
    with pytest.raises(execution.RequestRejected) as refused:
        execution.execute(query, **arguments)
    assert refused.value.__cause__ is None and refused.value.__context__ is None
    return refused.value.code, refused.value.detail


def _failed(handle: Any) -> Any:
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle as result:
            list(result)
    assert failed.value.__cause__ is None and failed.value.__context__ is None
    return failed.value


def _table(pa: Any, handle: Any) -> Any:
    with handle as result:
        batches = [pa.record_batch(batch) for batch in result]
    return pa.Table.from_batches(batches, schema=pa.schema(handle))


def _judged(
    handle: Any,
    rows: Sequence[tuple[object, ...]],
    columns: tuple[tuple[str, str, bool], ...] = COLUMNS,
    *,
    ordered: bool = True,
) -> None:
    """Deliver the whole result and judge it against rows written before the
    run."""
    table = _table(_pyarrow(), handle)
    files.judge(*files.result_facts(table), columns, rows, ordered=ordered)


@pytest.fixture(scope="module")
def native(
    request: pytest.FixtureRequest,
    filtered_query: execution.CompiledQuery,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """The SQLite class of a native cell (docs/development.md, "SQLite target
    validation"): the cell runs on the measured build on Linux x86-64.
    Elsewhere `qualified` fails it and `report` skips it with a counted
    `PIETTO_NOT_RUN sqlite-native` line, while `hosted-refusal` asserts the
    route's own refusal before any file opens and skips the cell, which has
    nothing else to run. PyArrow is an installation premise, not the
    build's: without it `qualified` and `report` skip the cell with the
    counted line `PIETTO_NOT_RUN sqlite-native ARROW`, and Gate 2's
    arrow-ready run of this file qualifies the cells with no skip."""
    declared = files.sqlite_class(
        os.environ, request.config.getoption("--pietto-sqlite-class")
    )
    with closing(sqlite3.connect(":memory:")) as connection:
        category = files.refusal(files.observe(connection))
    if sys.platform != "linux" or platform.machine() != "x86_64":
        category = "SQLITE_PLATFORM"
    if files.decide(category, declared):
        if declared != "hosted-refusal" and importlib.util.find_spec("pyarrow") is None:
            pytest.skip("PIETTO_NOT_RUN sqlite-native ARROW")
        return
    missing = tmp_path_factory.mktemp("refused") / "absent.db"
    good = {"access": execution.SQLiteFileInput(missing), "parameters": ARGUMENTS}
    assert _refusal(filtered_query, **good) == ("PIE-R2002", "SQLITE_BUILD")
    assert not missing.exists()
    pytest.skip(f"the sqlite_file route refuses here: {category}")


def test_the_input_is_a_frozen_value_that_refuses_pickle_and_copy(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "absent.db"
    value = execution.SQLiteFileInput(missing)
    assert value.path is missing and not missing.exists()
    with pytest.raises(AttributeError):
        value.path = "other"  # type: ignore[misc]
    for attempt in (pickle.dumps, copy.copy, copy.deepcopy):
        with pytest.raises(TypeError, match="cannot be pickled or copied"):
            attempt(value)
    assert value != execution.SQLiteFileInput(missing)


def test_compile_query_compiles_a_sqlite_query(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    query = filtered_query
    assert (query.dialect, query.release, query.origin) == ("sqlite", "3.53.1", "live")
    assert (query.kind, query.name, query.literal_policy) == ("query", "q", "preserve")
    assert query.slots == ()
    assert query.parameters == (("low", "Int", False), ("word", "Text", True))
    root = files.write(tmp_path / "again", FILTERED, _contract())
    from pietto.compiler import compile_sql

    document = compile_sql(
        root,
        module="main.pietto",
        kind="query",
        name="q",
        dialect="sqlite",
        emission_contract="contract.json",
    )
    assert query.emission == document.document
    # Not the adapter's own refusal: bind-safe is refused by its rule 3.
    with pytest.raises(execution.CompileRejected):
        execution.compile_query(
            root,
            module="main.pietto",
            kind="query",
            name="q",
            dialect="sqlite",
            emission_contract="contract.json",
            literal_policy="bind-safe",
        )


JOINED = """query joined:
    from orders
    let c = customers
    inner join c on orders.id == c.id
    select:
        orders.id
        c.name
"""


def test_compile_query_compiles_a_join_that_the_route_refuses(tmp_path: Path) -> None:
    # A third source that the query does not read leaves its contract entry.
    header = files.JOINED_HEADER + ('\nsource spare: Order = sqlite.table("spare")\n')
    document = files.joined_contract()
    document["sources"].append(files.source_entry("spare"))
    root = files.write(tmp_path / "p", JOINED, document, header)
    query = execution.compile_query(
        root,
        module="main.pietto",
        kind="query",
        name="joined",
        dialect="sqlite",
        emission_contract="contract.json",
    )
    assert (query.dialect, query.parameters, query.slots) == ("sqlite", (), ())
    assert query.emission is not None
    assert b'"sql":"SELECT `s0`.`id` AS `id`, `s1`.`name` AS `name` FROM' in (
        query.emission
    )
    missing = tmp_path / "absent.db"
    access = execution.SQLiteFileInput(missing)
    assert _refusal(query, access=access, parameters={}) == (
        "PIE-R1003",
        "PUBLIC_ROUTE_UNAVAILABLE",
    )
    assert not missing.exists()


def test_request_checks_refuse_in_order_before_any_file_opens(
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    query = filtered_query
    missing = tmp_path / "absent.db"
    file = execution.SQLiteFileInput(missing)
    pg = execution.PostgresAccess("127.0.0.1", 5432, "d", "u", "p")
    good: dict[str, Any] = {"access": file, "parameters": ARGUMENTS}
    postgres = execution.compile_query(
        api.write_example(tmp_path / "example"),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    cases: list[tuple[dict[str, Any], tuple[str, str]]] = [
        ({"route": None}, ("PIE-R1001", "PUBLIC_ROUTE_REQUIRED")),
        (
            {"route": "postgres_rows", "access": pg},
            ("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE"),
        ),
        ({"route": "duckdb_arrow"}, ("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE")),
        ({"access": None}, ("PIE-R1001", "PUBLIC_ACCESS_REQUIRED")),
        ({"access": pg}, ("PIE-R1002", "PUBLIC_ACCESS_TYPE")),
        ({"access": str(missing)}, ("PIE-R1002", "PUBLIC_ACCESS_TYPE")),
        ({"premise": ()}, ("PIE-R1002", "PUBLIC_PREMISE_TYPE")),
        ({"limits": None}, ("PIE-R1001", "PUBLIC_LIMITS_REQUIRED")),
        ({"isolation": None}, ("PIE-R1001", "PUBLIC_ISOLATION_REQUIRED")),
        ({"values": [1]}, ("PIE-R1002", "PUBLIC_VALUES_TYPE")),
        ({"parameters": {1: 2}}, ("PIE-R1002", "PUBLIC_PARAMETERS_TYPE")),
        ({"values": (1,)}, ("PIE-R1006", "BINDING_SLOTS")),
        ({"parameters": {"low": 4}}, ("PIE-R1006", "BINDING_PARAMETERS")),
        (
            {"parameters": {"low": True, "word": "a"}},
            ("PIE-R1006", "BINDING_PARAMETER:0:Int"),
        ),
        (
            {"parameters": {"low": 4, "word": "a\0"}},
            ("PIE-R1006", "BINDING_PARAMETER:1:Text"),
        ),
        (
            {"access": execution.SQLiteFileInput(b"x.db")},
            ("PIE-R1002", "EXECUTION_ACCESS"),
        ),
        ({"access": execution.SQLiteFileInput("")}, ("PIE-R1002", "EXECUTION_ACCESS")),
        (
            {"access": execution.SQLiteFileInput("a\0.db")},
            ("PIE-R1002", "EXECUTION_ACCESS"),
        ),
        ({"access": execution.SQLiteFileInput(7)}, ("PIE-R1002", "EXECUTION_ACCESS")),
        ({"isolation": "serializable"}, ("PIE-R1002", "EXECUTION_ISOLATION")),
        (
            {"limits": execution.ExecutionLimits(seconds=0)},
            ("PIE-R1002", "EXECUTION_LIMITS"),
        ),
    ]
    for change, expected in cases:
        assert _refusal(query, **(good | change)) == expected, change
    assert _refusal(postgres, **good) == ("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE")
    # Defence 9: another platform or build is refused last, before any file.
    monkeypatch.setattr(route.platform, "machine", lambda: "aarch64")
    assert _refusal(query, **good) == ("PIE-R2002", "SQLITE_BUILD")
    monkeypatch.undo()
    forged = dataclasses.replace(QUALIFIED_SQLITE_BUILD, release="3.53.2")
    monkeypatch.setattr("pietto.sql.sqlite.QUALIFIED_SQLITE_BUILD", forged)
    assert _refusal(query, **good) == ("PIE-R2002", "SQLITE_BUILD")
    assert list(tmp_path.glob("absent*")) == []


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows cannot remove the working directory"
)
def test_a_relative_path_is_refused_once_the_working_directory_is_gone(
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gone = tmp_path / "gone"
    gone.mkdir()
    monkeypatch.chdir(gone)
    gone.rmdir()
    relative = {"access": execution.SQLiteFileInput("x.db"), "parameters": ARGUMENTS}
    assert _refusal(filtered_query, **relative) == ("PIE-R1002", "EXECUTION_ACCESS")


def test_a_float_parameter_is_finite_before_any_file_opens(tmp_path: Path) -> None:
    query = _compiled(tmp_path / "p", FLOAT)
    access = execution.SQLiteFileInput(tmp_path / "absent.db")
    for value in (math.nan, math.inf, -math.inf, 1, True, None):
        refused = _refusal(query, access=access, parameters={"x": value})
        assert refused == ("PIE-R1006", "BINDING_PARAMETER:0:Float"), value
    assert not (tmp_path / "absent.db").exists()


def test_a_forged_template_or_another_code_identity_is_refused(
    filtered_query: execution.CompiledQuery,
) -> None:
    forged = object.__new__(execution.CompiledQuery)
    for slot in execution.CompiledQuery.__slots__:
        object.__setattr__(forged, slot, getattr(filtered_query, slot))
    template = filtered_query._template
    good = {"access": execution.SQLiteFileInput("x.db"), "parameters": ARGUMENTS}
    object.__setattr__(
        forged, "_template", route.SQLiteTemplate(template.emission, ("other",))
    )
    assert _refusal(forged, **good) == ("PIE-R1005", "COMPILED_COMPATIBILITY")
    object.__setattr__(forged, "_template", route.SQLiteTemplate(None, ()))
    assert _refusal(forged, **good) == ("PIE-R1004", "BINDING_ARTIFACT")


def test_a_bundle_refuses_a_sqlite_query(
    filtered_query: execution.CompiledQuery,
) -> None:
    with pytest.raises(execution.RequestRejected) as refused:
        execution.export_bundle(filtered_query)
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "SQLITE_BUNDLE_ENTRY",
    )


@pytest.mark.skipif(
    sys.platform == "win32", reason="the workspace and job modules import fcntl"
)
def test_other_entry_points_refuse_a_sqlite_query(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    """No saved result, recovery, relay or job: each refuses before it
    builds or opens anything (the workspace below does not exist)."""
    query = filtered_query
    workspace = execution.WorkspaceRef(str(tmp_path / "absent"), "ws-" + "0" * 32)
    common: dict[str, Any] = {
        "operation": execution.new_operation(),
        "access": execution.SQLiteFileInput(tmp_path / "x.db"),
        "premise": None,
        "limits": execution.ExecutionLimits(),
    }
    calls = {
        "save": lambda **k: execution.save(workspace, query, **k),
        "save_recoverable": lambda **k: execution.save_recoverable(
            workspace, query, source_requirements=(), **k
        ),
        "recover": lambda **k: execution.recover(
            workspace,
            job="j",
            generation="g",
            checkpoint=None,
            query=query,
            source_requirements=(),
            expected_pin="0" * 64,
            accepted_producer="x",
            accepted_compatibility="x",
            purpose="p",
            seconds=1,
            **k,
        ),
        "relay_live": lambda **k: execution.relay_live(
            workspace,
            query,
            sink_root=str(tmp_path / "sink"),
            expected_sink_identity="x",
            sink_namespace="x",
            sink_epoch=1,
            sink_retention="x",
            sink_budget_bytes=1,
            **k,
        ),
    }
    for name, call in calls.items():
        for selected in ("sqlite_file", "postgres_rows"):
            with pytest.raises(execution.RequestRejected) as refused:
                call(route=selected, **common)
            assert (refused.value.code, refused.value.detail) == (
                "PIE-R1003",
                "PUBLIC_ROUTE_UNAVAILABLE",
            ), (name, selected)
    from pietto._project import project_job_store as store

    assert "sqlite_file" not in store.ROUTES
    assert sorted(p.name for p in tmp_path.iterdir()) == []


def test_the_authorizer_allows_only_the_source_reads_and_the_checks(
    filtered_query: execution.CompiledQuery,
) -> None:
    facts = route.execution_facts(filtered_query._template)
    attempt = route.SQLiteAttempt(facts, "x.db", (), None)
    ok, deny = sqlite3.SQLITE_OK, sqlite3.SQLITE_DENY
    read, function, pragma = (
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_PRAGMA,
    )
    allowed = [
        (read, "orders", "amount", "main", None),
        (read, "orders", "", "main", None),
        (read, "orders", "", None, None),
        (sqlite3.SQLITE_SELECT, None, None, None, None),
        (function, None, "count", None, None),
        (function, None, "typeof", None, None),
        (function, None, "row_number", None, None),
        (function, None, "rank", None, None),
        (function, None, "dense_rank", None, None),
        (pragma, "schema_version", None, None, None),
        (pragma, "index_list", "orders", None, None),
        (pragma, "integrity_check", "orders", None, None),
        (sqlite3.SQLITE_TRANSACTION, "BEGIN", None, None, None),
        (sqlite3.SQLITE_TRANSACTION, "ROLLBACK", None, None, None),
    ]
    denied = [
        (read, "orders", "amount", None, None),
        (read, "orders", "amount", "temp", None),
        (read, "orders", "secret", "main", None),
        (read, "other", "amount", "main", None),
        (read, "orders", "amount", "main", "v"),
        (read, "Orders", "", "main", None),
        (function, None, "load_extension", None, None),
        (function, None, "ntile", None, None),
        (function, None, "lag", None, None),
        (function, None, "sqlite_version", None, None),
        (pragma, "integrity_check", None, None, None),
        (pragma, "table_list", "other", None, None),
        (pragma, "index_xinfo", "orders", None, None),
        (pragma, "writable_schema", "1", None, None),
        (sqlite3.SQLITE_ATTACH, "x.db", None, None, None),
        (sqlite3.SQLITE_INSERT, "orders", None, "main", None),
        (sqlite3.SQLITE_TRANSACTION, "SAVEPOINT", None, None, None),
    ]
    assert [attempt._authorize(*c) for c in allowed] == [ok] * len(allowed)
    assert [attempt._authorize(*c) for c in denied] == [deny] * len(denied)
    # `index_xinfo` reads only an index that `index_list` listed for the source.
    attempt._indexes = ("orders_id",)
    assert attempt._authorize(pragma, "index_xinfo", "orders_id", None, None) == ok
    assert attempt._authorize(pragma, "index_xinfo", "other_id", None, None) == deny
    # Once the statement runs, no PRAGMA is allowed.
    attempt._checking = False
    assert attempt._authorize(pragma, "encoding", None, None, None) == deny
    assert attempt._authorize(pragma, "index_xinfo", "orders_id", None, None) == deny


def test_the_result_binding_checks_each_value_before_pyarrow() -> None:
    pa = _pyarrow()
    columns = (
        ("i", "sqlite_integer", False),
        ("b", "sqlite_bool01", True),
        ("t", "sqlite_text", True),
        ("f", "sqlite_real", False),
    )
    table = results.bind_result(
        pa, [(1, 1, "x", 0.5), (-(2**63), None, None, -0.0)], columns
    )
    assert table.schema == results.result_schema(pa, columns)
    assert table.to_pylist() == [
        {"i": 1, "b": True, "t": "x", "f": 0.5},
        {"i": -(2**63), "b": None, "t": None, "f": -0.0},
    ]
    for row in (
        (None, 1, "x", 0.5),
        (True, 1, "x", 0.5),
        (1.0, 1, "x", 0.5),
        (1, 2, "x", 0.5),
        (1, True, "x", 0.5),
        (1, 1, b"x", 0.5),
        (1, 1, "x", 1),
        (1, 1, "x", float("inf")),
        (1, 1, "x", float("nan")),
        (1, 1, "x"),
        [1, 1, "x", 0.5],
    ):
        with pytest.raises(ResultError, match="SQLITE_RESULT_CHECK"):
            results.bind_result(pa, [row], columns)


@NATIVE
def test_a_filtered_query_returns_its_rows_and_leaves_the_file_unchanged(
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pa = _pyarrow()
    path = _database(tmp_path / "orders.db")
    before = path.read_bytes()
    handle = _handle(filtered_query, path)
    expected = pa.schema(
        [
            pa.field("id", pa.int64(), nullable=False),
            pa.field("note", pa.string()),
            pa.field("ok", pa.bool_(), nullable=False),
            pa.field("price", pa.float64(), nullable=False),
        ]
    )
    assert pa.schema(handle) == expected and handle.outcome.end == "NOT_STARTED"
    _judged(handle, [FIRST])
    outcome = handle.outcome
    assert (outcome.end, outcome.transaction, outcome.cleanup, outcome.rows) == (
        "COMPLETE",
        "COMMIT_ACK",
        "CLOSED",
        1,
    )
    assert outcome.primary is None and outcome.cleanup_failures == ()
    _judged(_handle(filtered_query, path, parameters={"low": 0, "word": None}), [])
    # A relative path names the file of the working directory at execute().
    monkeypatch.chdir(tmp_path)
    relative = _handle(filtered_query, "orders.db")
    monkeypatch.chdir(tmp_path.parent)
    _judged(relative, [FIRST])
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["orders.db"]


@NATIVE
def test_the_aggregates_run_in_one_snapshot_of_a_wal_file(tmp_path: Path) -> None:
    """A WAL file whose -wal holds the rows: the size counts it, and SQLite
    leaves the -wal and -shm files beside it, as the effects table states."""
    _pyarrow()
    query = _compiled(tmp_path / "p", GROUPED, _contract(id=(0, MAX)))
    path = tmp_path / "orders.db"
    writer = sqlite3.connect(path)
    try:
        writer.execute("PRAGMA journal_mode = WAL")
        writer.execute("PRAGMA wal_autocheckpoint = 0")
        writer.execute(SCHEMA)
        writer.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", ROWS)
        writer.commit()
        main = path.stat().st_size
        wal = Path(str(path) + "-wal").stat().st_size
        assert wal > main
        arguments = {"v": 4, "t": "x"}
        _judged(_handle(query, path, parameters=arguments), GROUPS, GROUPED_COLUMNS)
        refused = _handle(query, path, parameters=arguments)
        limit = main + wal - 1
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(route, "MAX_FILE_BYTES", limit)
            failure = _failed(refused).failure
        assert (failure.code, failure.detail) == ("PIE-R3004", "SQLITE_FILE_LIMIT")
    finally:
        writer.close()
    # The last writer checkpointed and removed its -wal and -shm files; a
    # read-only reader of a WAL file creates them again and leaves them.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["orders.db", "p"]
    _judged(_handle(query, path, parameters=arguments), GROUPS, GROUPED_COLUMNS)
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "orders.db",
        "orders.db-shm",
        "orders.db-wal",
        "p",
    ]


@NATIVE
def test_a_symbolic_link_resolves_before_a_parent_step(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    """`sub/link/../orders.db` names the file that the operating system and
    sqlite3.connect open, beside the link's target, not `sub/orders.db`."""
    _pyarrow()
    (tmp_path / "elsewhere" / "deep").mkdir(parents=True)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "link").symlink_to(tmp_path / "elsewhere" / "deep")
    _database(tmp_path / "elsewhere" / "orders.db")
    _database(tmp_path / "sub" / "orders.db", _row(id=2))
    named = tmp_path / "sub" / "link" / ".." / "orders.db"
    _judged(_handle(filtered_query, named), [FIRST])


@NATIVE
@pytest.mark.parametrize("suffix", ["/", "/.", "/../other.db"])
def test_a_path_the_system_does_not_read_as_a_file_is_refused(
    filtered_query: execution.CompiledQuery, tmp_path: Path, suffix: str
) -> None:
    """The operating system reports ENOTDIR for each form, which
    `Path.resolve()` would drop or, before 3.13, step over."""
    _pyarrow()
    _database(tmp_path / "orders.db")
    _database(tmp_path / "other.db")
    failed = _failed(_handle(filtered_query, f"{tmp_path / 'orders.db'}{suffix}"))
    assert (failed.failure.code, failed.failure.detail) == (
        "PIE-R2004",
        "SQLITE_FILE_TYPE",
    )


@NATIVE
@pytest.mark.parametrize("stage", ["source", "query"])
@pytest.mark.parametrize("end", ["DEADLINE", "CANCELLED"])
def test_a_stop_between_fetches_still_rolls_back(
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    end: str,
) -> None:
    """A deadline or cancel() that the Python check finds while the text scan
    or the statement still has rows to fetch: the cursor is closed first, so
    the interrupt cannot stop ROLLBACK."""
    _pyarrow()
    rows = (*ROWS, (4, 9, "a", 0, 0.0), (5, 9, "a", 1, 0.25))
    path = _database(tmp_path / "orders.db", rows)
    handle = _handle(filtered_query, path, parameters={"low": 0, "word": "a"})
    monkeypatch.setattr(route, "FETCH_ROWS", 1)
    real = route.SQLiteAttempt._checkpoint
    seen: list[bool] = []

    def checkpoint(attempt: Any) -> None:
        if attempt.session_id is not None:
            seen.append(attempt._checking)
            # The first check of the source runs before its text scan.
            if seen.count(True) == 2 if stage == "source" else not seen[-1]:
                if end == "CANCELLED":
                    # As if from another thread during the last fetch.
                    handle.cancel()
                else:
                    attempt.deadline_expired = True
        real(attempt)

    monkeypatch.setattr(route.SQLiteAttempt, "_checkpoint", checkpoint)
    failed = _failed(handle)
    assert failed.failure.code == ("PIE-R3001" if end == "DEADLINE" else "PIE-R3009")
    outcome = handle.outcome
    assert (outcome.end, outcome.transaction, outcome.cleanup) == (
        end,
        "ROLLBACK_ACK",
        "CLOSED",
    )
    assert outcome.cleanup_failures == () and outcome.cancel_sent
    assert seen[-1] is (stage == "source")


@NATIVE
def test_a_lock_held_to_the_deadline_ends_at_the_deadline(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    """The busy timeout is the time left, so its error is the deadline's."""
    _pyarrow()
    path = _database(tmp_path / "orders.db")
    limits = execution.ExecutionLimits(seconds=0.5)
    handle = _handle(filtered_query, path, limits=limits)
    with closing(sqlite3.connect(path, isolation_level=None)) as writer:
        writer.execute("BEGIN EXCLUSIVE")
        failed = _failed(handle)
    assert (failed.failure.code, failed.failure.detail) == (
        "PIE-R3001",
        "SQLITE_ERRORCODE_5",
    )
    outcome = handle.outcome
    assert (outcome.end, outcome.transaction, outcome.cleanup) == (
        "DEADLINE",
        "ROLLBACK_ACK",
        "CLOSED",
    )


def _view(path: Path) -> None:
    _database(path, (), SCHEMA.replace("orders", "base"))
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE VIEW orders AS SELECT * FROM base")


def _index_fault(path: Path) -> None:
    _database(path)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE INDEX orders_amount ON orders(amount)")
        connection.execute("PRAGMA writable_schema = ON")
        connection.execute(
            "UPDATE sqlite_schema SET sql = 'CREATE INDEX orders_amount ON orders(id)'"
            " WHERE name = 'orders_amount'"
        )
        connection.commit()


def _invalid_utf8(path: Path) -> None:
    _database(path, ROWS)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            "UPDATE orders SET note = CAST(x'61ff' AS TEXT) WHERE id = 1"
        )
        connection.commit()


def _planted(schema: str, rows: tuple[tuple[object, ...], ...]) -> Any:
    """A file whose rows were written under `schema` and whose table is then
    declared as SCHEMA, as a tampered file can be: SQLite does not check the
    stored rows against the new declaration."""

    def setup(path: Path) -> None:
        _database(path, rows, schema)
        with closing(sqlite3.connect(path)) as connection:
            connection.execute("PRAGMA writable_schema = ON")
            connection.execute(
                "UPDATE sqlite_schema SET sql = ? WHERE name = 'orders'", (SCHEMA,)
            )
            connection.commit()

    return setup


def _cut(size: int) -> Any:
    """The file of ROWS (two pages of 4,096 bytes) cut to its first `size`
    bytes."""

    def setup(path: Path) -> None:
        _database(path)
        path.write_bytes(path.read_bytes()[:size])

    return setup


def _then(*statements: str, rows: tuple[tuple[object, ...], ...] = ROWS) -> Any:
    """A file of `rows` under SCHEMA, then `statements`."""

    def setup(path: Path) -> None:
        _database(path, rows)
        with closing(sqlite3.connect(path)) as connection:
            for statement in statements:
                connection.execute(statement)
            connection.commit()

    return setup


def _swap(column: str, declared: str) -> str:
    return SCHEMA.replace(column, declared, 1)


def _generated(kind: str) -> str:
    """SCHEMA with a sixth column computed from `note`."""
    return SCHEMA.replace(
        ") STRICT", f", shout TEXT GENERATED ALWAYS AS (upper(note)){kind}) STRICT"
    )


def _row(**change: object) -> tuple[tuple[object, ...], ...]:
    names = ("id", "amount", "note", "ok", "price")
    first = dict(zip(names, ROWS[0], strict=True)) | change
    return (tuple(first.values()), *ROWS[1:])


R2004, R2007, R3004 = "PIE-R2004", "PIE-R2007", "PIE-R3004"
INTEGRITY = (R2007, "SQLITE_SOURCE_INTEGRITY")
# SCHEMA without STRICT, so `amount` stores text; SCHEMA with `amount` nullable.
TYPED = SCHEMA.removesuffix(" STRICT")
NULLABLE = _swap("amount INTEGER NOT NULL", "amount INTEGER")
DEFENCES: dict[str, tuple[Any, tuple[str, str]]] = {
    "missing": (lambda p: None, (R2004, "SQLITE_FILE_TYPE")),
    "directory": (lambda p: p.mkdir(), (R2004, "SQLITE_FILE_TYPE")),
    "fifo": (lambda p: os.mkfifo(p), (R2004, "SQLITE_FILE_TYPE")),
    # SQLite would open /dev/null as an empty database.
    "link to /dev/null": (
        lambda p: p.symlink_to(os.devnull),
        (R2004, "SQLITE_FILE_TYPE"),
    ),
    # SQLITE_CORRUPT (11) at the first read.
    "header cut short": (_cut(100), (R2004, "SQLITE_ERRORCODE_11")),
    "pages cut off": (_cut(4096), (R2004, "SQLITE_ERRORCODE_11")),
    "not a database": (
        lambda p: p.write_bytes(b"not a database" * 512),
        (R2004, "SQLITE_ERRORCODE_26"),
    ),
    "empty file": (lambda p: p.write_bytes(b""), (R2004, "SQLITE_FILE_TYPE")),
    # SQLite would delete the -wal file beside a 0-byte database.
    "empty file with a -wal file": (
        lambda p: (p.write_bytes(b""), Path(f"{p}-wal").write_bytes(b"w" * 1200)),
        (R2004, "SQLITE_FILE_TYPE"),
    ),
    "utf-16": (
        lambda p: _database(p, ROWS, SCHEMA, "PRAGMA encoding = 'UTF-16le'"),
        (R2007, "SQLITE_FILE_ENCODING"),
    ),
    "view": (_view, (R2007, "SQLITE_SOURCE_OBJECT")),
    "not strict": (
        lambda p: _database(p, ROWS, SCHEMA.removesuffix(" STRICT")),
        (R2007, "SQLITE_SOURCE_OBJECT"),
    ),
    "virtual": (
        lambda p: _database(
            p, (), "CREATE VIRTUAL TABLE orders USING fts5(id, amount, note, ok, price)"
        ),
        (R2007, "SQLITE_SOURCE_OBJECT"),
    ),
    "other name case": (
        lambda p: _database(p, (), SCHEMA.replace("orders", "Orders")),
        (R2007, "SQLITE_SOURCE_OBJECT"),
    ),
    "any column": (
        lambda p: _database(p, ROWS, _swap("amount INTEGER", "amount ANY")),
        (R2007, "SQLITE_SOURCE_COLUMNS"),
    ),
    "blob column": (
        lambda p: _database(p, (), _swap("note TEXT", "note BLOB")),
        (R2007, "SQLITE_SOURCE_COLUMNS"),
    ),
    "real for an int": (
        lambda p: _database(p, ROWS, _swap("amount INTEGER", "amount REAL")),
        (R2007, "SQLITE_SOURCE_COLUMNS"),
    ),
    "generated column": (
        lambda p: _database(
            p,
            (),
            _swap("price REAL NOT NULL", "price REAL GENERATED ALWAYS AS (1.5)"),
        ),
        (R2007, "SQLITE_SOURCE_COLUMNS"),
    ),
    "missing column": (
        lambda p: _database(p, (), _swap(", price REAL NOT NULL", "")),
        (R2007, "SQLITE_SOURCE_COLUMNS"),
    ),
    "column case": (
        lambda p: _database(p, (), _swap("price", "Price")),
        (R2007, "SQLITE_SOURCE_COLUMNS"),
    ),
    # The integrity check would compute each of these expressions of the file.
    "expression index": (
        _then("CREATE INDEX orders_lower ON orders(amount, lower(note))"),
        (R2007, "SQLITE_SOURCE_OBJECT"),
    ),
    "partial index": (
        _then("CREATE INDEX orders_some ON orders(amount) WHERE ok = 1"),
        (R2007, "SQLITE_SOURCE_OBJECT"),
    ),
    "generated column beside": (
        lambda p: _database(p, ROWS, _generated("")),
        (R2007, "SQLITE_SOURCE_COLUMNS"),
    ),
    "stored generated column beside": (
        lambda p: _database(p, ROWS, _generated(" STORED")),
        (R2007, "SQLITE_SOURCE_COLUMNS"),
    ),
    "index fault": (_index_fault, (R2007, "SQLITE_SOURCE_INTEGRITY")),
    "planted STRICT type error": (_planted(TYPED, _row(amount="x")), INTEGRITY),
    "planted NOT NULL error": (_planted(NULLABLE, _row(amount=None)), INTEGRITY),
    "bool 2": (lambda p: _database(p, _row(ok=2)), (R2007, "SQLITE_SOURCE_VALUES")),
    "null in a non-null field": (
        lambda p: _database(
            p, _row(amount=None), _swap("amount INTEGER NOT NULL", "amount INTEGER")
        ),
        (R2007, "SQLITE_SOURCE_VALUES"),
    ),
    "infinity": (
        lambda p: _database(p, _row(price=float("inf"))),
        (R2007, "SQLITE_SOURCE_VALUES"),
    ),
    "NUL in text": (
        lambda p: _database(p, _row(note="a\0b")),
        (R2007, "SQLITE_SOURCE_VALUES"),
    ),
    "invalid UTF-8": (_invalid_utf8, (R2007, "SQLITE_SOURCE_VALUES")),
    "text too long": (
        lambda p: _database(p, _row(note="x" * 101)),
        (R2007, "SQLITE_SOURCE_VALUES"),
    ),
    "int outside its range": (
        lambda p: _database(p, _row(id=-1)),
        (R2007, "SQLITE_SOURCE_VALUES"),
    ),
}


@NATIVE
@pytest.mark.parametrize("case", DEFENCES, ids=list(DEFENCES))
def test_each_defence_refuses_before_the_statement(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _pyarrow()
    query = _compiled(tmp_path / "p", FILTERED, _contract(id=(0, MAX)))
    setup, expected = DEFENCES[case]
    path = tmp_path / "orders.db"
    setup(path)
    before = _files(tmp_path)
    statements: list[str] = []
    real = sqlite3.connect

    def connect(*arguments: Any, **keywords: Any) -> Any:
        connection = real(*arguments, **keywords)
        connection.set_trace_callback(statements.append)
        return connection

    handle = _handle(query, path)
    monkeypatch.setattr(sqlite3, "connect", connect)
    failed = _failed(handle)
    assert (failed.failure.code, failed.failure.detail) == expected
    assert not any(s.startswith("SELECT `s0`") for s in statements), statements
    assert failed.outcome is not None and failed.outcome.end == "FAILED"
    if expected[0] != R2004:
        assert failed.outcome.transaction == "ROLLBACK_ACK"
        assert statements[-1] == "ROLLBACK"
    assert _files(tmp_path) == before


def _files(directory: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}


@NATIVE
@pytest.mark.parametrize("companion", ["-wal", "-journal", "-shm", "-shm link"])
def test_a_companion_file_that_sqlite_would_block_on_or_rewrite_is_refused(
    filtered_query: execution.CompiledQuery, tmp_path: Path, companion: str
) -> None:
    """SQLite opens the -wal, -journal and -shm files itself: a FIFO would
    block it beyond the deadline, and it truncates an -shm file in place,
    through any other link to it. A timer frees a FIFO that SQLite opened,
    so that a regression fails instead of hanging."""
    _pyarrow()
    path = _database(tmp_path / "orders.db", ROWS, SCHEMA, "PRAGMA journal_mode = WAL")
    beside = Path(str(path) + companion.removesuffix(" link"))
    other = tmp_path / "other"
    if companion.endswith(" link"):
        other.write_bytes(b"x" * 80_000)
        os.link(other, beside)
    else:
        os.mkfifo(beside)
    timer = threading.Timer(
        5, lambda: os.close(os.open(beside, os.O_RDWR | os.O_NONBLOCK))
    )
    timer.start()
    try:
        failed = _failed(_handle(filtered_query, path))
    finally:
        timer.cancel()
    assert (failed.failure.code, failed.failure.detail) == (R2004, "SQLITE_FILE_TYPE")
    assert not other.exists() or other.read_bytes() == b"x" * 80_000


@NATIVE
def test_a_setting_that_does_not_read_back_is_refused(
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defence 2 reads each setting back: a library that ignored the
    request for defensive mode leaves the session unopened."""
    _pyarrow()
    path = _database(tmp_path / "orders.db")

    class Ignoring(sqlite3.Connection):
        def setconfig(self, op: int, enable: bool = True, /) -> bool:
            if op == sqlite3.SQLITE_DBCONFIG_DEFENSIVE:
                return False
            return super().setconfig(op, enable)

    real = sqlite3.connect
    handle = _handle(filtered_query, path)
    monkeypatch.setattr(
        sqlite3, "connect", lambda *a, **k: real(*a, factory=Ignoring, **k)
    )
    failed = _failed(handle)
    assert (failed.failure.code, failed.failure.detail) == (
        "PIE-R2006",
        "SQLITE_SESSION_CONTEXT",
    )
    assert failed.outcome is not None and failed.outcome.cleanup == "CLOSED"


# A fault planted in the file, the read that shows its harm without the route,
# and that read's rows.
PLANTED = {
    # The index holds `amount` under the name of `id`: a row that the table
    # does not hold, which `quick_check` misses.
    "index fault": (
        _index_fault,
        "SELECT id, amount FROM orders WHERE id = 5",
        [(5, 5)],
    ),
    "planted STRICT type error": (
        _planted(TYPED, _row(amount="x")),
        "SELECT typeof(amount) FROM orders WHERE id = 1",
        [("text",)],
    ),
    "planted NOT NULL error": (
        _planted(NULLABLE, _row(amount=None)),
        "SELECT amount FROM orders WHERE id = 1",
        [(None,)],
    ),
}


@NATIVE
@pytest.mark.parametrize("case", PLANTED, ids=list(PLANTED))
def test_a_planted_fault_misleads_a_read_that_the_route_refuses(
    case: str, filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    _pyarrow()
    setup, read, rows = PLANTED[case]
    path = tmp_path / "orders.db"
    setup(path)
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as raw:
        assert raw.execute(read).fetchall() == rows
        quick = raw.execute("PRAGMA quick_check(orders)").fetchall()
    assert (quick == [("ok",)]) is (case == "index fault")
    failure = _failed(_handle(filtered_query, path)).failure
    assert (failure.code, failure.detail) == INTEGRITY


@NATIVE
def test_a_violated_check_constraint_is_no_premise(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    """Row 1 breaks a CHECK planted in the file. A writable connection's
    integrity check reports it; the read-only one checks no CHECK, so the
    route reads the row, whose values hold the contract's domains."""
    _pyarrow()
    path = _database(tmp_path / "orders.db")
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA writable_schema = ON")
        connection.execute(
            "UPDATE sqlite_schema SET sql = ? WHERE name = 'orders'",
            (SCHEMA.replace(") STRICT", ", CHECK (amount > 6)) STRICT"),),
        )
        connection.commit()
    with closing(sqlite3.connect(path)) as writable:
        assert writable.execute("PRAGMA integrity_check(orders)").fetchall() == [
            ("CHECK constraint failed in orders",)
        ]
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as read_only:
        assert read_only.execute("PRAGMA integrity_check(orders)").fetchall() == [
            ("ok",)
        ]
    _judged(_handle(filtered_query, path), [FIRST])


# Files whose source is sound beside schema the route never reads.
SOUND = {
    # Project SQL compares with COLLATE BINARY: "A" is not "a".
    "NOCASE column": lambda p: _database(
        p,
        (*ROWS, (4, 8, "A", 0, 0.5)),
        _swap("note TEXT", "note TEXT COLLATE NOCASE"),
    ),
    "unique and NOCASE indexes": _then(
        "CREATE UNIQUE INDEX orders_id ON orders(id)",
        "CREATE INDEX orders_note ON orders(note COLLATE NOCASE, amount DESC)",
    ),
    "trigger": _then(
        "CREATE TABLE seen (id INTEGER)",
        "CREATE TRIGGER orders_seen AFTER INSERT ON orders"
        " BEGIN INSERT INTO seen VALUES (new.id); END",
    ),
    "broken view elsewhere": _then(
        "CREATE TABLE gone (a INTEGER)",
        "CREATE VIEW broken AS SELECT a FROM gone",
        "DROP TABLE gone",
    ),
    # Only the source's own indexes and columns are refused.
    "expressions elsewhere": _then(
        "CREATE TABLE other (a TEXT, b TEXT GENERATED ALWAYS AS (upper(a)))",
        "CREATE INDEX other_lower ON other(lower(a)) WHERE a > 'a'",
    ),
}


@NATIVE
@pytest.mark.parametrize("case", SOUND, ids=list(SOUND))
def test_a_sound_source_runs_beside_schema_the_route_never_reads(
    case: str, filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    _pyarrow()
    path = tmp_path / "orders.db"
    SOUND[case](path)
    _judged(_handle(filtered_query, path), [FIRST])


@NATIVE
def test_the_integrity_check_would_run_an_index_expression_past_the_defences(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    """An index planted over `note` with an expression of `hex`, `zeroblob`
    and `replace`, none of which the authorizer allows. On a read-only
    connection that denies every function, `PRAGMA integrity_check` computes
    the expression for each row without asking the authorizer, in fewer
    steps than the route lets pass between two deadline checks; the route
    refuses the index first, within a one-second deadline."""
    _pyarrow()
    heavy = "length(replace(hex(zeroblob(4000000)), '0', 'ab'))"
    path = tmp_path / "orders.db"
    _then("CREATE INDEX orders_note ON orders(note)")(path)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA writable_schema = ON")
        connection.execute(
            "UPDATE sqlite_schema SET sql = ? WHERE name = 'orders_note'",
            (f"CREATE INDEX orders_note ON orders({heavy})",),
        )
        connection.commit()
    asked: list[object] = []
    steps = [0]

    def deny(action: int, *arguments: object) -> int:
        if action != sqlite3.SQLITE_FUNCTION:
            return sqlite3.SQLITE_OK
        asked.append(arguments)
        return sqlite3.SQLITE_DENY

    def step() -> int:
        steps[0] += 1
        return 0

    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as raw:
        raw.set_authorizer(deny)
        raw.set_progress_handler(step, 1)
        report = raw.execute("PRAGMA integrity_check(orders)").fetchall()
    assert report == [(f"row {i} missing from index orders_note",) for i in (1, 2, 3)]
    assert asked == [] and steps[0] < route.PROGRESS_STEPS
    started = time.monotonic()
    limits = execution.ExecutionLimits(seconds=1)
    failure = _failed(_handle(filtered_query, path, limits=limits)).failure
    assert (failure.code, failure.detail) == (R2007, "SQLITE_SOURCE_OBJECT")
    assert time.monotonic() - started < 1


@NATIVE
def test_immutable_would_read_old_rows_where_the_route_reads_the_last_commit(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    """Defence 1 never opens with `immutable=1`: on a WAL file whose last
    commit is still in the -wal file, such a reader keeps the old rows."""
    _pyarrow()
    path = _database(tmp_path / "orders.db", ROWS, SCHEMA, "PRAGMA journal_mode = WAL")
    writer = sqlite3.connect(path)
    try:
        writer.execute("PRAGMA wal_autocheckpoint = 0")
        writer.execute("INSERT INTO orders VALUES (4, 8, 'a', 0, 0.5)")
        writer.commit()
        stale = path.as_uri() + "?mode=ro&immutable=1"
        with closing(sqlite3.connect(stale, uri=True)) as old:
            assert old.execute("SELECT count(*) FROM orders").fetchone() == (3,)
        rows = [FIRST, (4, "a", False, 0.5)]
        _judged(_handle(filtered_query, path), rows, ordered=False)
    finally:
        writer.close()


@NATIVE
@pytest.mark.parametrize("mode", ["delete", "wal"])
def test_a_writer_during_the_attempt_changes_nothing_it_reads(
    mode: str,
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defence 7: after the integrity check and before any row is read, a
    writer replaces the source with a table the checks refuse. In
    rollback-journal mode the attempt's read lock fails its commit; in WAL
    mode it commits, and the attempt keeps its snapshot of schema and data,
    which the next attempt no longer sees."""
    _pyarrow()
    path = _database(
        tmp_path / "orders.db", ROWS, SCHEMA, f"PRAGMA journal_mode = {mode}"
    )
    handle = _handle(filtered_query, path)
    real = route.SQLiteAttempt._checkpoint
    writes: list[object] = []

    def checkpoint(attempt: Any) -> None:
        if attempt.session_id is not None and not writes:
            with closing(sqlite3.connect(path, timeout=0)) as writer:
                try:
                    writer.execute("DROP TABLE orders")
                    writer.execute(TYPED)
                    writer.execute("INSERT INTO orders VALUES (1, 'x', 'a', 2, 'y')")
                    writer.commit()
                    writes.append("COMMIT")
                except sqlite3.OperationalError as error:
                    writes.append(error.sqlite_errorcode)
        real(attempt)

    monkeypatch.setattr(route.SQLiteAttempt, "_checkpoint", checkpoint)
    _judged(handle, [FIRST])
    monkeypatch.undo()
    if mode == "delete":
        assert writes == [sqlite3.SQLITE_BUSY]
        _judged(_handle(filtered_query, path), [FIRST])
    else:
        assert writes == ["COMMIT"]
        failure = _failed(_handle(filtered_query, path)).failure
        assert (failure.code, failure.detail) == (R2007, "SQLITE_SOURCE_OBJECT")


@NATIVE
@pytest.mark.parametrize(
    ("limit", "detail"),
    [
        ("MAX_SOURCE_ROWS", "SQLITE_SOURCE_LIMIT"),
        ("MAX_FILE_BYTES", "SQLITE_FILE_LIMIT"),
    ],
)
def test_the_file_and_row_limits_refuse_before_the_statement(
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    limit: str,
    detail: str,
) -> None:
    _pyarrow()
    path = _database(tmp_path / "orders.db")
    bound = {
        "MAX_SOURCE_ROWS": len(ROWS) - 1,
        "MAX_FILE_BYTES": path.stat().st_size - 1,
    }
    monkeypatch.setattr(route, limit, bound[limit])
    failure = _failed(_handle(filtered_query, path)).failure
    assert (failure.code, failure.detail) == ("PIE-R3004", detail)
    monkeypatch.setattr(route, limit, bound[limit] + 1)
    assert _table(_pyarrow(), _handle(filtered_query, path)).num_rows == 1


@NATIVE
def test_the_session_is_hardened_and_checks_before_it_reads(
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The statements in order, and the configuration still in force when the
    attempt closes its connection."""
    _pyarrow()
    path = _database(tmp_path / "o?mode=rwc&immutable=1#x.db")
    seen: list[Any] = []
    installed: list[Any] = []
    options = (
        sqlite3.SQLITE_DBCONFIG_DEFENSIVE,
        sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA,
        sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION,
    )

    class Recording(sqlite3.Connection):
        def close(self) -> None:
            seen.append(tuple(self.getconfig(o) for o in options))
            super().close()

        def set_authorizer(self, authorizer_callback: Any) -> None:
            seen.append("set_authorizer")
            installed.append(authorizer_callback)
            super().set_authorizer(authorizer_callback)

    real = sqlite3.connect

    def connect(*arguments: Any, **keywords: Any) -> Any:
        seen.append((arguments, keywords))
        connection = real(*arguments, factory=Recording, **keywords)
        connection.set_trace_callback(seen.append)
        return connection

    handle = _handle(filtered_query, path)
    monkeypatch.setattr(sqlite3, "connect", connect)
    assert _table(_pyarrow(), handle).num_rows == 1
    (opened, keywords), *statements, config = seen
    assert opened == (path.resolve().as_uri() + "?mode=ro",)
    assert opened[0].endswith("/o%3Fmode%3Drwc%26immutable%3D1%23x.db?mode=ro")
    assert keywords == {
        "uri": True,
        "timeout": 0,
        "isolation_level": None,
        "check_same_thread": True,
    }
    assert config == (True, False, False)
    prefixes = (
        "PRAGMA cell_size_check = 1",
        "PRAGMA mmap_size = 0",
        "PRAGMA query_only = 1",
        "PRAGMA cell_size_check",
        "PRAGMA mmap_size",
        "PRAGMA query_only",
        "PRAGMA busy_timeout = ",
        "set_authorizer",
        "BEGIN",
        "PRAGMA schema_version",
        "PRAGMA encoding",
        "PRAGMA table_list(`orders`)",
        "PRAGMA index_list(`orders`)",
        "PRAGMA table_xinfo(`orders`)",
        "PRAGMA integrity_check(`orders`)",
        "SELECT count(*) FROM `main`.`orders`",
        "SELECT 1 FROM `main`.`orders` WHERE ",
        "SELECT CAST(`note` AS BLOB) FROM `main`.`orders`",
        "SELECT `s0`.`id` AS `id`",
        "COMMIT",
    )
    assert len(statements) == len(prefixes), statements
    for statement, prefix in zip(statements, prefixes, strict=True):
        assert type(statement) is str and statement.startswith(prefix), statement
    timeout = int(str(statements[6]).removeprefix("PRAGMA busy_timeout = "))
    assert 0 < timeout <= 20_001
    # Defence 3 is the attempt's own authorizer, installed once.
    assert installed == [handle._owner._authorize]
    # The name's `?` and `#` are percent-encoded: no file `o` was opened or made.
    assert sorted(p.name for p in tmp_path.iterdir()) == [path.name]


@NATIVE
def test_windows_run_on_the_route(tmp_path: Path) -> None:
    """The ranking functions pass the authorizer, and each window's result
    column is checked as its document describes it."""
    query = _compiled(tmp_path / "p", WINDOWS, _contract(id=(0, MAX)))
    path = _database(tmp_path / "orders.db")
    columns = (
        ("id", "int64", False),
        *((name, "int64", False) for name in ("r", "n", "d", "c")),
        ("s", "int64", True),
    )
    rows = [(1, 2, 1, 1, 2, 1), (2, 1, 2, 3, 1, 3), (3, 1, 3, 2, 2, 6)]
    _judged(_handle(query, path, parameters=None), rows, columns, ordered=False)


@NATIVE
@pytest.mark.parametrize("body", [SUM, WINDOW_SUM], ids=["grouped", "window"])
def test_a_sum_overflow_is_named_by_its_code_and_message(
    tmp_path: Path, body: str
) -> None:
    _pyarrow()
    query = _compiled(tmp_path / "p", body, _contract(id=(0, MAX)))
    path = _database(tmp_path / "orders.db", _row(id=MAX))
    failed = _failed(_handle(query, path, parameters=None))
    failure = failed.failure
    assert (failure.code, failure.detail, failure.phase, failure.cause) == (
        "PIE-R3003",
        "SQLITE_INTEGER_OVERFLOW",
        "query",
        "OperationalError",
    )
    assert "integer overflow" not in str(failed)
    assert failed.outcome is not None
    assert failed.outcome.transaction == "ROLLBACK_ACK"


@NATIVE
def test_a_computed_column_that_check_leaves_unknown_delivers_its_null(
    tmp_path: Path,
) -> None:
    # A comparison of the nullable `note` is NULL for order 2, and so are a
    # `not` of one and `0 OR NULL`. Declared non-null, such a column failed
    # its NULL with PIE-R3005 SQLITE_RESULT_CHECK.
    body = (
        "query result:\n    from orders\n    select:\n        id\n"
        '        m = note == "a"\n        n = not (note == "a")\n'
        '        o = ok or note == "b"\n'
    )
    _judged(
        _handle(
            _compiled(tmp_path / "p", body), _database(tmp_path / "o.db"), parameters={}
        ),
        [(1, True, False, True), (2, None, None, None), (3, False, True, True)],
        (("id", "int64", False), *((name, "bool", True) for name in "mno")),
    )


ARITHMETIC = """query result:
    from orders
    where amount - 1 > 4
    select:
        id
        v = amount * 2 - id
        a = abs(-amount)
"""
SUMMED = "query result:\n    from orders\n    select:\n        s = sum(amount * id)\n"


@NATIVE
def test_range_proved_arithmetic_runs_on_a_file_that_holds_its_ranges(
    tmp_path: Path,
) -> None:
    """S14's arithmetic runs on the route, and its proof rests on the
    contract's `int_range`, which the value check holds the file to: a value
    past it is refused before the statement runs, where SQLite would answer
    a REAL."""
    _pyarrow()
    document = _contract(id=(0, 100), amount=(0, 100))
    query = _compiled(tmp_path / "p", ARITHMETIC, document)
    assert query.emission is not None and b"ABS(-`s0`.`amount`)" in query.emission
    summed = _compiled(tmp_path / "q", SUMMED, document)
    path = _database(tmp_path / "orders.db")
    # `check` leaves a binary operation's nullability unknown, so `v` may be
    # NULL; a unary `-` and `abs` keep their operand's.
    columns = (("id", "int64", False), ("v", "int64", True), ("a", "int64", False))
    _judged(_handle(query, path, parameters=None), [(2, 12, 7), (3, 15, 9)], columns)
    _judged(_handle(summed, path, parameters=None), [(46,)], (("s", "int64", True),))
    past = _database(tmp_path / "past.db", _row(amount=101))
    failure = _failed(_handle(query, past, parameters=None)).failure
    assert (failure.code, failure.detail) == (R2007, "SQLITE_SOURCE_VALUES")


def _armed(monkeypatch: pytest.MonkeyPatch, react: Any) -> None:
    """Every SQLite step calls the progress handler, and `react` runs as the
    deadline check once the session holds its snapshot."""
    monkeypatch.setattr(route, "PROGRESS_STEPS", 1)

    def expired(self: Any) -> bool:
        return self.session_id is not None and react(self)

    monkeypatch.setattr(route.SQLiteAttempt, "_expired", expired)


@NATIVE
def test_the_deadline_interrupts_a_running_statement(
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pyarrow()
    path = _database(tmp_path / "orders.db")
    handle = _handle(filtered_query, path)
    _armed(monkeypatch, lambda attempt: True)
    failed = _failed(handle)
    assert (failed.failure.code, failed.failure.detail) == (
        "PIE-R3001",
        "SQLITE_ERRORCODE_9",
    )
    outcome = handle.outcome
    assert (outcome.end, outcome.transaction, outcome.cleanup) == (
        "DEADLINE",
        "ROLLBACK_ACK",
        "CLOSED",
    )
    assert outcome.deadline_expired and outcome.cancel_sent


@NATIVE
def test_cancel_interrupts_a_running_statement(
    filtered_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _pyarrow()
    path = _database(tmp_path / "orders.db")
    handle = _handle(filtered_query, path)

    def cancel(attempt: Any) -> bool:
        handle.cancel()
        return False

    _armed(monkeypatch, cancel)
    failed = _failed(handle)
    assert failed.failure.code == "PIE-R3009"
    outcome = handle.outcome
    assert outcome.end == "CANCELLED" and not outcome.deadline_expired
    assert outcome.cancel_requested and outcome.cancel_sent and outcome.cancel_observed
    assert outcome.transaction == "ROLLBACK_ACK"


@NATIVE
def test_batches_follow_the_limits_and_close_opens_nothing(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    pa = _pyarrow()
    every = {"low": 0, "word": "a"}
    rows = (*ROWS, (4, 9, "a", 0, 0.0), (5, 9, "a", 1, 0.25))
    path = _database(tmp_path / "more.db", rows)
    small = execution.ExecutionLimits(batch_rows=2)
    with _handle(filtered_query, path, parameters=every, limits=small) as result:
        sizes = [pa.record_batch(batch).num_rows for batch in result]
    assert sizes == [2, 1]
    capped = execution.ExecutionLimits(batch_rows=2, max_rows=2)
    handle = _handle(filtered_query, path, parameters=every, limits=capped)
    delivered = []
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle as result:
            for batch in result:
                delivered.append(pa.record_batch(batch).num_rows)
    assert delivered == [2] and failed.value.failure.code == "PIE-R3004"
    absent = _handle(filtered_query, tmp_path / "absent.db")
    absent.close()
    assert absent.outcome.end == "NOT_STARTED" and not (tmp_path / "absent.db").exists()
