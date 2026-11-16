"""The `sqlite_file` execution route: its request checks, the defences of
its read-only open of the caller's file, the source check in the attempt's
read transaction, and the attempt's lifecycle (docs/spec/sqlite-project-v1.md,
"Execution"; PL.47). Cells that open a file run only on Linux x86-64 with
the measured SQLite build and need PyArrow (lesson 80-2); the request checks
run everywhere."""

from __future__ import annotations

import copy
import dataclasses
import os
import pickle
import platform
import sqlite3
import sys
import threading
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
MAX = 2**63 - 1


def _measured() -> bool:
    if sys.platform != "linux" or platform.machine() != "x86_64":
        return False
    with closing(sqlite3.connect(":memory:")) as connection:
        release, source = connection.execute(
            "SELECT sqlite_version(), sqlite_source_id()"
        ).fetchone()
        options = tuple(row[0] for row in connection.execute("PRAGMA compile_options"))
    build = QUALIFIED_SQLITE_BUILD
    return (release, source, options) == (
        build.release,
        build.source_id,
        build.compile_options,
    )


NATIVE = pytest.mark.skipif(
    not _measured(),
    reason="the sqlite_file route opens files only on Linux x86-64 with the"
    " measured SQLite build",
)


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
    # A relative path once the working directory is gone.
    gone = tmp_path / "gone"
    gone.mkdir()
    monkeypatch.chdir(gone)
    gone.rmdir()
    relative = good | {"access": execution.SQLiteFileInput("x.db")}
    assert _refusal(query, **relative) == ("PIE-R1002", "EXECUTION_ACCESS")


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


def test_other_entry_points_refuse_a_sqlite_query(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    """No bundle, saved result, recovery, relay or job: each refuses before
    it builds or opens anything (the workspace below does not exist)."""
    query = filtered_query
    with pytest.raises(execution.RequestRejected) as refused:
        execution.export_bundle(query)
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "SQLITE_BUNDLE_ENTRY",
    )
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
        (pragma, "schema_version", None, None, None),
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
        (function, None, "sqlite_version", None, None),
        (pragma, "integrity_check", None, None, None),
        (pragma, "table_list", "other", None, None),
        (pragma, "writable_schema", "1", None, None),
        (sqlite3.SQLITE_ATTACH, "x.db", None, None, None),
        (sqlite3.SQLITE_INSERT, "orders", None, "main", None),
        (sqlite3.SQLITE_TRANSACTION, "SAVEPOINT", None, None, None),
    ]
    assert [attempt._authorize(*c) for c in allowed] == [ok] * len(allowed)
    assert [attempt._authorize(*c) for c in denied] == [deny] * len(denied)
    # Once the statement runs, no PRAGMA is allowed.
    attempt._checking = False
    assert attempt._authorize(pragma, "encoding", None, None, None) == deny


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
    table = _table(pa, handle)
    assert table.to_pylist() == [{"id": 1, "note": "a", "ok": True, "price": 1.5}]
    outcome = handle.outcome
    assert (outcome.end, outcome.transaction, outcome.cleanup, outcome.rows) == (
        "COMPLETE",
        "COMMIT_ACK",
        "CLOSED",
        1,
    )
    assert outcome.primary is None and outcome.cleanup_failures == ()
    word = _handle(filtered_query, path, parameters={"low": 0, "word": None})
    assert _table(pa, word).num_rows == 0
    # A relative path names the file of the working directory at execute().
    monkeypatch.chdir(tmp_path)
    relative = _handle(filtered_query, "orders.db")
    monkeypatch.chdir(tmp_path.parent)
    assert _table(pa, relative).num_rows == 1
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["orders.db"]


@NATIVE
def test_the_aggregates_run_in_one_snapshot_of_a_wal_file(tmp_path: Path) -> None:
    """A WAL file whose -wal holds the rows: the size counts it, and SQLite
    leaves the -wal and -shm files beside it, as the effects table states."""
    pa = _pyarrow()
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
        table = _table(pa, _handle(query, path, parameters=arguments))
        assert table.to_pylist() == [
            {"ok": False, "n": 1, "d": 0, "a": 7.0, "s": 2, "low": 2.5},
            {"ok": True, "n": 2, "d": 2, "a": 7.0, "s": 4, "low": -1.0},
        ]
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
    assert _table(pa, _handle(query, path, parameters=arguments)).num_rows == 2
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
    pa = _pyarrow()
    (tmp_path / "elsewhere" / "deep").mkdir(parents=True)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "link").symlink_to(tmp_path / "elsewhere" / "deep")
    _database(tmp_path / "elsewhere" / "orders.db")
    _database(tmp_path / "sub" / "orders.db", _row(id=2))
    named = tmp_path / "sub" / "link" / ".." / "orders.db"
    assert _table(pa, _handle(filtered_query, named)).column("id").to_pylist() == [1]


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


def _swap(column: str, declared: str) -> str:
    return SCHEMA.replace(column, declared, 1)


def _row(**change: object) -> tuple[tuple[object, ...], ...]:
    names = ("id", "amount", "note", "ok", "price")
    first = dict(zip(names, ROWS[0], strict=True)) | change
    return (tuple(first.values()), *ROWS[1:])


R2004, R2007, R3004 = "PIE-R2004", "PIE-R2007", "PIE-R3004"
DEFENCES: dict[str, tuple[Any, tuple[str, str]]] = {
    "missing": (lambda p: None, (R2004, "SQLITE_FILE_TYPE")),
    "directory": (lambda p: p.mkdir(), (R2004, "SQLITE_FILE_TYPE")),
    "fifo": (lambda p: os.mkfifo(p), (R2004, "SQLITE_FILE_TYPE")),
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
    "index fault": (_index_fault, (R2007, "SQLITE_SOURCE_INTEGRITY")),
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
    options = (
        sqlite3.SQLITE_DBCONFIG_DEFENSIVE,
        sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA,
        sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION,
    )

    class Recording(sqlite3.Connection):
        def close(self) -> None:
            seen.append(tuple(self.getconfig(o) for o in options))
            super().close()

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
        "BEGIN",
        "PRAGMA schema_version",
        "PRAGMA encoding",
        "PRAGMA table_list(`orders`)",
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
    # The name's `?` and `#` are percent-encoded: no file `o` was opened or made.
    assert sorted(p.name for p in tmp_path.iterdir()) == [path.name]


@NATIVE
def test_a_sum_overflow_is_named_by_its_code_and_message(tmp_path: Path) -> None:
    _pyarrow()
    query = _compiled(tmp_path / "p", SUM, _contract(id=(0, MAX)))
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
