"""The `duckdb_arrow` execution route: its request checks, the owned capture,
the session and the attempt's lifecycle (docs/spec/duckdb-arrow-route-v1.md;
D79.03, D79.04, D79.06 and AD79.01). Cells that need PyArrow, or PyArrow and
the pinned duckdb, skip with a reason where those are not installed."""

from __future__ import annotations

import copy
import dataclasses
import json
import math
import operator
import pickle
import subprocess
import sys
import threading
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import _pietto_execution_api as api
from _pietto_execution_duckdb import (
    CUSTOMERS,
    ROWS,
    bag,
    compiled,
    customers,
    events,
    joined,
    orders,
    projection,
    run,
)
from _pietto_sql_duckdb import (
    GROUPED,
    JOINED,
    JOINED_GROUPED,
    JOINED_HEADER,
    KEYED_HEADER,
    ORDERED,
    PREDICATED,
    PROJECTION,
    SELF_GROUPED,
    SELF_JOINED,
    TWIN_JOINED,
    TYPED_FIELDS,
    TYPED_HEADER,
    contract,
    filtered,
    joined_contract,
    narrowed,
    source_entry,
    write,
)

from pietto import execution
from pietto._project import project_duckdb_emission as adapter
from pietto._project import project_duckdb_contract as duckdb_contract
from pietto._project import project_duckdb_result as results
from pietto._project import project_execution_reader as reader
from pietto._project import project_result_binding as binding
from pietto._project.project_result_contract import ResultError
from pietto.execution import _duckdb as route

ROOT = Path(__file__).resolve().parents[1]
# The statement reads pietto_running, an endless Arrow stream that a test
# registers on the attempt's own connection; the engine pulls each batch from
# its generator, so the test sees the statement running inside the engine
# with no Python UDF (DuckDB's needs NumPy, which the execute-duckdb closure
# lacks). Only an interrupt stops it, or the watchdog WATCHDOG_SECONDS after
# its first batch.
SLOW = 'SELECT count(*) AS "id", NULL AS "note" FROM pietto_running'
WATCHDOG_SECONDS = 30.0
# The spec's session table ("Session and attempt", D79.06 and PL.47) in its
# order: the setting, the value set and the value read back.
SESSION_TABLE = (
    ("allow_community_extensions", "false", "false"),
    ("allow_extension_repositories", "'forbidden'", "forbidden"),
    ("allow_persistent_secrets", "false", "false"),
    ("allow_unsigned_extensions", "false", "false"),
    ("arrow_large_buffer_size", "false", "false"),
    ("arrow_lossless_conversion", "false", "false"),
    ("arrow_output_list_view", "false", "false"),
    ("arrow_output_version", "'1.0'", "1.0"),
    ("autoinstall_known_extensions", "false", "false"),
    ("autoload_known_extensions", "false", "false"),
    ("enable_progress_bar", "false", "false"),
    ("enable_progress_bar_print", "false", "false"),
    ("max_temp_directory_size", "'0B'", "0 bytes"),
    ("memory_limit", "'1GiB'", "1.0 GiB"),
    ("python_enable_replacements", "false", "false"),
    ("python_scan_all_frames", "false", "false"),
    ("temp_directory", "''", ""),
    ("threads", "1", "1"),
    ("enable_external_access", "false", "false"),
    ("lock_configuration", "true", "true"),
)
# The values the spec reads back unchanged at 2.0.0, in its order, then the
# aliases of threads and memory_limit.
SESSION_UNCHANGED = (
    ("allowed_configs", "[]"),
    ("allowed_directories", "[]"),
    ("allowed_paths", "[]"),
    ("extension_directories", "[]"),
    ("custom_extension_repository", ""),
    ("autoinstall_extension_repository", ""),
    ("log_query_path", ""),
    ("profiling_output", ""),
    ("disabled_filesystems", ""),
    ("enable_profiling", None),
    ("enable_logging", "0"),
    ("logging_storage", "memory"),
    ("access_mode", "automatic"),
    ("default_collation", ""),
    ("worker_threads", "1"),
    ("max_memory", "1.0 GiB"),
)
OPENED = [("connect", ":memory:"), ("register", "pietto_arrow_0")]
ENDED = [("unregister", "pietto_arrow_0"), ("close",)]
OPERATORS = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def _pyarrow() -> Any:
    return pytest.importorskip("pyarrow", reason="the capture needs PyArrow")


def _engine() -> Any:
    pa = _pyarrow()
    pytest.importorskip("duckdb", reason="the session needs the pinned duckdb")
    return pa


# One compile of each B1 query per module for the cells that only read it; a
# cell that changes its query or needs its own project compiles afresh.
@pytest.fixture(scope="module")
def filtered_query(tmp_path_factory: pytest.TempPathFactory) -> execution.CompiledQuery:
    return compiled(tmp_path_factory.mktemp("filtered") / "p")


@pytest.fixture(scope="module")
def projection_query(
    tmp_path_factory: pytest.TempPathFactory,
) -> execution.CompiledQuery:
    return projection(tmp_path_factory.mktemp("projection") / "p")


@pytest.fixture(scope="module")
def joined_query(tmp_path_factory: pytest.TempPathFactory) -> execution.CompiledQuery:
    return joined(tmp_path_factory.mktemp("joined") / "p", JOINED)


def _refusal(query: Any, **arguments: Any) -> tuple[str, str | None]:
    arguments = {"route": "duckdb_arrow", "premise": None, **arguments}
    with pytest.raises(execution.RequestRejected) as refused:
        execution.execute(query, **arguments)
    assert refused.value.__cause__ is None and refused.value.__context__ is None
    return refused.value.code, refused.value.detail


def _failed(handle: Any) -> Any:
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle as result:
            list(result)
    return failed.value


def _handle(pa: Any, query: Any, table: Any = None, **arguments: Any) -> Any:
    return execution.execute(
        query,
        route="duckdb_arrow",
        access=execution.DuckDBArrowInput(
            "orders", orders(pa) if table is None else table
        ),
        premise=None,
        **arguments,
    )


class _Connection:
    """The attempt's real connection, recording what the route asks of it."""

    def __init__(
        self, connection: Any, calls: list[tuple[str, ...]], hooks: dict[str, Any]
    ) -> None:
        self._connection, self._calls, self._hooks = connection, calls, hooks
        self._registered = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)

    def sql(self, query: str, **arguments: Any) -> Any:
        if self._registered and "statement" in self._hooks:
            self._hooks["statement"]()
        return self._connection.sql(query, **arguments)

    def register(self, name: str, table: Any) -> Any:
        self._calls.append(("register", name))
        if "register" in self._hooks:
            self._hooks["register"](self._connection)
        result = self._connection.register(name, table)
        self._registered = True
        return result

    def interrupt(self) -> Any:
        self._calls.append(("interrupt",))
        return self._connection.interrupt()

    def unregister(self, name: str) -> Any:
        self._calls.append(("unregister", name))
        return self._connection.unregister(name)

    def close(self) -> Any:
        self._calls.append(("close",))
        return self._connection.close()


class _Driver:
    """The pinned duckdb module, whose connections record their calls."""

    def __init__(
        self, driver: Any, calls: list[tuple[str, ...]], hooks: dict[str, Any]
    ) -> None:
        self._driver, self._calls, self._hooks = driver, calls, hooks

    def __getattr__(self, name: str) -> Any:
        return getattr(self._driver, name)

    def connect(self, database: str) -> _Connection:
        self._calls.append(("connect", database))
        connection = self._driver.connect(database)
        return _Connection(connection, self._calls, self._hooks)


def _recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[tuple[str, ...]], dict[str, Any]]:
    """The connection calls of every attempt, behind the real driver check,
    and the hooks a test may set: `register` runs with the real connection
    when the capture is registered (an exception fails the registration),
    `statement` before each statement after the registration."""
    calls: list[tuple[str, ...]] = []
    hooks: dict[str, Any] = {}
    driver = route._driver
    monkeypatch.setattr(route, "_driver", lambda: _Driver(driver(), calls, hooks))
    return calls, hooks


def test_the_input_is_a_frozen_value_that_refuses_pickle_and_copy() -> None:
    table = object()
    value = execution.DuckDBArrowInput("orders", table)
    assert repr(value) == "DuckDBArrowInput(name='orders', table=<object>)"
    assert value.table is table and "DuckDBArrowInput" in execution.__all__
    with pytest.raises(dataclasses.FrozenInstanceError):
        value.name = "other"  # type: ignore[misc]
    for attempt in (pickle.dumps, copy.copy, copy.deepcopy):
        with pytest.raises(TypeError, match="caller-owned table; it cannot be pickled"):
            attempt(value)


CHECKS_CHILD = r"""
import json, sys
sys.path[:0] = json.loads(sys.argv[1])
from pietto import execution
from pietto.execution import DuckDBArrowInput as Input, ExecutionLimits as Limits
query = execution.compile_query(sys.argv[2], module="main.pietto", kind="query",
    name="result", dialect="duckdb", emission_contract="contract.json")
pg = execution.PostgresAccess("127.0.0.1", 5432, "d", "u", "p")
ok = dict(route="duckdb_arrow", access=Input("orders", object()), premise=None,
    parameters={"min_amount": 1})
cases = [
    (None, {}), ("SELECT 1", {}), (query, {"route": None}), (query, {"route": 1}),
    (query, {"route": "postgres_rows"}), (query, {"route": "duckdb"}),
    (query, {"access": None}), (query, {"access": pg}),
    (query, {"premise": execution.PostgresDeploymentPremise(("pg_catalog",))}),
    (query, {"limits": None}), (query, {"limits": 1}), (query, {"isolation": None}),
    (query, {"values": []}), (query, {"parameters": {1: 2}}),
    (query, {"values": (1,)}), (query, {"parameters": {}}),
    (query, {"parameters": {"min_amount": 1, "x": 2}}),
    (query, {"parameters": {"min_amount": True}}),
    (query, {"parameters": {"min_amount": 2 ** 63}}),
    (query, {"parameters": {"min_amount": None}}),
    (query, {}), (query, {"access": Input("", object())}),
    (query, {"access": Input(b"orders", object())}),
    # Earlier checks win: 6 over 7, 7 over 8.
    (query, {"values": [], "parameters": {}}),
    (query, {"values": (1,), "access": Input("", object())}),
]
seen = []
for value, change in cases:
    try:
        execution.execute(value, **{**ok, **change})
    except execution.RequestRejected as error:
        seen.append([error.code, error.detail])
loaded = sorted(n for n in sys.modules if n.partition(".")[0] in ("pyarrow", "duckdb", "_duckdb"))
print(json.dumps({"seen": seen, "loaded": loaded}))
"""


def test_checks_one_to_eight_refuse_in_order_and_import_nothing(
    tmp_path: Path,
) -> None:
    """Checks 1-8 of the spec's execute API, first failure first; none of
    them imports PyArrow or DuckDB (check 8 reads a loaded `pyarrow.lib`)."""
    root = write(tmp_path / "p", filtered(">="), contract())
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            CHECKS_CHILD,
            json.dumps(sys.path),
            str(root),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    facts = json.loads(result.stdout)
    assert facts["loaded"] == []
    assert facts["seen"] == [
        ["PIE-R1001", "PUBLIC_QUERY_REQUIRED"],
        ["PIE-R1002", "PUBLIC_QUERY_TYPE"],
        ["PIE-R1001", "PUBLIC_ROUTE_REQUIRED"],
        ["PIE-R1002", "PUBLIC_ROUTE_TYPE"],
        ["PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE"],
        ["PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE"],
        ["PIE-R1001", "PUBLIC_ACCESS_REQUIRED"],
        ["PIE-R1002", "PUBLIC_ACCESS_TYPE"],
        ["PIE-R1002", "PUBLIC_PREMISE_TYPE"],
        ["PIE-R1001", "PUBLIC_LIMITS_REQUIRED"],
        ["PIE-R1002", "PUBLIC_LIMITS_TYPE"],
        ["PIE-R1001", "PUBLIC_ISOLATION_REQUIRED"],
        ["PIE-R1002", "PUBLIC_VALUES_TYPE"],
        ["PIE-R1002", "PUBLIC_PARAMETERS_TYPE"],
        ["PIE-R1006", "BINDING_SLOTS"],
        ["PIE-R1006", "BINDING_PARAMETERS"],
        ["PIE-R1006", "BINDING_PARAMETERS"],
        ["PIE-R1006", "BINDING_PARAMETER:0:Int"],
        ["PIE-R1006", "BINDING_PARAMETER:0:Int"],
        ["PIE-R1006", "BINDING_PARAMETER:0:Int"],
        ["PIE-R1002", "EXECUTION_ACCESS"],
        ["PIE-R1002", "EXECUTION_ACCESS"],
        ["PIE-R1002", "EXECUTION_ACCESS"],
        ["PIE-R1002", "PUBLIC_VALUES_TYPE"],
        ["PIE-R1006", "BINDING_SLOTS"],
    ]


def test_check_seven_refuses_a_forged_template_and_another_code_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The template binds afresh only while its artifact verifies (PIE-R1004)
    and the installed code is the code it was compiled with (PIE-R1005)."""
    query = compiled(tmp_path / "p")
    access = execution.DuckDBArrowInput("orders", object())
    arguments: dict[str, Any] = {"access": access, "parameters": {"min_amount": 1}}
    template = query._template
    assert type(template) is adapter.DuckDBTemplate
    forged = dataclasses.replace(
        template.emission, sql=template.emission.sql.replace(b">=", b"<=")
    )
    object.__setattr__(
        query, "_template", dataclasses.replace(template, emission=forged)
    )
    assert _refusal(query, **arguments) == ("PIE-R1004", "BINDING_ARTIFACT")
    object.__setattr__(query, "_template", template)
    monkeypatch.setattr(route, "supported_compatibility", lambda: ("another",))
    assert _refusal(query, **arguments) == ("PIE-R1005", "COMPILED_COMPATIBILITY")


CAPTURE_CHILD = r"""
import json, sys
sys.path[:0] = json.loads(sys.argv[1])
import pyarrow as pa
from pietto import execution
from pietto.execution import DuckDBArrowInput as Input, ExecutionLimits as Limits
query = execution.compile_query(sys.argv[2], module="main.pietto", kind="query",
    name="result", dialect="duckdb", emission_contract="contract.json")
table = pa.table({"id": pa.array([1], pa.int64()), "amount": pa.array([5], pa.int64()),
    "note": pa.array([None], pa.string()), "ok": [True], "price": [1.0]})
ok = dict(route="duckdb_arrow", access=Input("orders", table), premise=None,
    parameters={"min_amount": 1})
cases = [
    {"access": Input("Orders", table)}, {"access": Input("orders ", table)},
    {"isolation": "serializable"}, {"isolation": 1},
    {"limits": Limits(batch_rows=0)}, {"limits": Limits(seconds=float("nan"))},
    {"access": Input("orders", table.drop_columns(["ok"]))},
    # Earlier checks win: 9 over 10, 10 over 11, 11 over 13.
    {"access": Input("other", table), "isolation": "serializable"},
    {"isolation": "x", "limits": Limits(batch_rows=0)},
    {"limits": Limits(batch_rows=0), "access": Input("orders", table.drop_columns(["ok"]))},
]
seen = []
for change in cases:
    try:
        execution.execute(query, **{**ok, **change})
    except execution.RequestRejected as error:
        seen.append([error.code, error.detail])
handle = execution.execute(query, **ok)
loaded = sorted(n for n in sys.modules if n.partition(".")[0] in ("duckdb", "_duckdb"))
print(json.dumps({"seen": seen, "loaded": loaded, "end": handle.outcome.end}))
handle.close()
"""


def test_checks_nine_to_thirteen_refuse_in_order_and_import_no_duckdb(
    tmp_path: Path,
) -> None:
    """The name is used exactly (no case folding or trimming); the handle
    exists only after the capture, and nothing before the attempt opens
    imports DuckDB."""
    _pyarrow()
    root = write(tmp_path / "p", filtered(">="), contract())
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            CAPTURE_CHILD,
            json.dumps(sys.path),
            str(root),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "seen": [
            ["PIE-R1002", "DUCKDB_ARROW_SCHEMA"],
            ["PIE-R1002", "DUCKDB_ARROW_SCHEMA"],
            ["PIE-R1002", "EXECUTION_ISOLATION"],
            ["PIE-R1002", "EXECUTION_ISOLATION"],
            ["PIE-R1002", "EXECUTION_LIMITS"],
            ["PIE-R1002", "EXECUTION_LIMITS"],
            ["PIE-R1002", "DUCKDB_ARROW_SCHEMA"],
            ["PIE-R1002", "DUCKDB_ARROW_SCHEMA"],
            ["PIE-R1002", "EXECUTION_ISOLATION"],
            ["PIE-R1002", "EXECUTION_LIMITS"],
        ],
        "loaded": [],
        "end": "NOT_STARTED",
    }


def test_check_twelve_refuses_a_pyarrow_that_is_not_the_pinned_distribution(
    filtered_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The other Arrow routes' codes, raised from `execute()` as
    RequestRejected before the capture: PIE-R2001 when the distribution is
    not installed, PIE-R2002 for another version, files it does not own or
    a PyArrow that cannot be loaded."""
    pa = _pyarrow()
    query = filtered_query
    arguments: dict[str, Any] = {
        "access": execution.DuckDBArrowInput("orders", orders(pa)),
        "parameters": {"min_amount": 1},
    }

    def unloadable(name: str) -> Any:
        raise ImportError(name)

    missing = ("PIE-R2001", "ARROW_DEPENDENCY_MISSING")
    other = ("PIE-R2002", "ARROW_DEPENDENCY_VERSION")
    monkeypatch.setattr(route, "capture", lambda *_: pytest.fail("captured"))
    for name, value, expected in (
        ("PYARROW", ("pietto-no-such-arrow", "26.0.1", "pyarrow"), missing),
        ("PYARROW", ("pyarrow", "0.0.1", "pyarrow"), other),
        ("owner_versions", lambda *_: frozenset(), other),
        ("_owned", unloadable, other),
    ):
        with monkeypatch.context() as patch:
            patch.setattr(route, name, value)
            assert _refusal(query, **arguments) == expected, name


class _Sharing:
    """The pinned PyArrow, except that concatenating returns the first chunk
    itself instead of a copy."""

    def __init__(self, pa: Any) -> None:
        self._pa = pa

    def __getattr__(self, name: str) -> Any:
        return getattr(self._pa, name)

    def concat_arrays(self, chunks: list[Any]) -> Any:
        return chunks[0]


def test_the_capture_refuses_a_copy_that_shares_the_callers_buffers(
    filtered_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Step 4's own check, a defensive invariant: a copy whose buffers
    overlap the caller's is refused before any handle exists."""
    pa = _pyarrow()
    query = filtered_query
    verified = route._pyarrow

    def sharing() -> Any:
        modules, refused = verified()
        assert modules is not None and refused is None
        return (_Sharing(modules[0]), modules[1]), None

    monkeypatch.setattr(route, "_pyarrow", sharing)
    access = execution.DuckDBArrowInput("orders", orders(pa))
    assert _refusal(query, access=access, parameters={"min_amount": 1}) == (
        "PIE-R1999",
        "DUCKDB_ARROW_CAPTURE_COPY",
    )


def _invalid_utf8(pa: Any) -> Any:
    offsets = pa.py_buffer(bytes([0, 0, 0, 0, 2, 0, 0, 0]))
    return pa.Array.from_buffers(
        pa.string(), 1, [None, offsets, pa.py_buffer(b"\xff\xfe")]
    )


def _forged(pa: Any) -> dict[str, Any]:
    """Tables that differ from the compiled source in one way each."""
    one = ((1, 5, "a", True, 1.5),)
    base = orders(pa, one)

    class Tagged(pa.ExtensionType):
        def __init__(self) -> None:
            super().__init__(pa.int64(), "pietto.test.tagged")

        def __arrow_ext_serialize__(self) -> bytes:
            return b""

        @classmethod
        def __arrow_ext_deserialize__(cls, storage_type: Any, serialized: bytes) -> Any:
            return cls()

    return {
        "missing column": base.drop_columns(["amount"]),
        "duplicate column": base.append_column("id", pa.array([2], pa.int64())),
        "case-folded column": base.rename_columns(
            ["ID", "amount", "note", "ok", "price"]
        ),
        "int32": orders(pa, one, id=pa.array([1], pa.int32())),
        "extension": orders(
            pa,
            one,
            id=pa.ExtensionArray.from_storage(Tagged(), pa.array([1], pa.int64())),
        ),
        "large_string": orders(pa, one, note=pa.array(["a"], pa.large_string())),
        "string_view": orders(pa, one, note=pa.array(["a"], pa.string_view())),
        "dictionary": orders(pa, one, note=pa.array(["a"]).dictionary_encode()),
        "null type": orders(pa, one, note=pa.array([None], pa.null())),
        "float32": orders(pa, one, price=pa.array([1.5], pa.float32())),
        "null in a non-null field": orders(pa, one, id=pa.array([None], pa.int64())),
        "NaN": orders(pa, one, price=pa.array([math.nan])),
        "+Inf": orders(pa, one, price=pa.array([math.inf])),
        "-Inf": orders(pa, one, price=pa.array([-math.inf])),
        "invalid UTF-8": orders(pa, one, note=_invalid_utf8(pa)),
        "too many characters": orders(pa, one, note=pa.array(["x" * 101])),
        "too many characters, each a NUL": orders(pa, one, note=pa.array(["\0" * 101])),
    }


def test_the_capture_refuses_every_forged_table_before_any_session(
    filtered_query: execution.CompiledQuery,
) -> None:
    pa = _pyarrow()
    query = filtered_query
    for name, table in _forged(pa).items():
        refused = _refusal(
            query,
            access=execution.DuckDBArrowInput("orders", table),
            parameters={"min_amount": 1},
        )
        assert refused == ("PIE-R1002", "DUCKDB_ARROW_SCHEMA"), name
    admitted = orders(pa, ((1, 5, "é" * 100, True, -0.0),))
    _handle(pa, query, admitted, parameters={"min_amount": 1}).close()


def test_an_int_outside_the_declared_range_is_refused(tmp_path: Path) -> None:
    pa = _pyarrow()
    document = contract()
    domain = document["sources"][0]["fields"][1]["representation"]["domain"]
    domain.update(min="-100", max="100")
    root = write(tmp_path / "p", filtered(">="), document)
    query = execution.compile_query(
        root,
        module="main.pietto",
        kind="query",
        name="result",
        dialect="duckdb",
        emission_contract="contract.json",
    )
    for amount, admitted in ((100, True), (-100, True), (101, False), (-101, False)):
        table = orders(pa, ((1, amount, None, True, 0.0),))
        arguments: dict[str, Any] = {"parameters": {"min_amount": 1}}
        if admitted:
            _handle(pa, query, table, **arguments).close()
        else:
            access = execution.DuckDBArrowInput("orders", table)
            assert _refusal(query, access=access, **arguments) == (
                "PIE-R1002",
                "DUCKDB_ARROW_SCHEMA",
            )


def test_the_limits_count_rows_first_and_then_only_the_selected_columns(
    filtered_query: execution.CompiledQuery,
) -> None:
    """PL.47: 1,048,576 rows are admitted and one more is refused before the
    schema; after the schema, the selected columns may measure 256 MiB of
    `nbytes` together and one byte more is refused before their values; a
    column that no source field names never counts."""
    pa = _pyarrow()
    query = filtered_query
    arguments: dict[str, Any] = {"parameters": {"min_amount": 1}}
    limit = ("PIE-R1002", "DUCKDB_ARROW_CAPTURE_LIMIT")
    schema = ("PIE-R1002", "DUCKDB_ARROW_SCHEMA")
    assert (route.MAX_ROWS, route.MAX_BYTES) == (1_048_576, 268_435_456)
    rows = ((1, 5, None, True, 0.0),) * route.MAX_ROWS
    _handle(pa, query, orders(pa, rows), **arguments).close()
    over = orders(pa, rows + rows[:1]).drop_columns(["ok"])
    access = execution.DuckDBArrowInput("orders", over)
    assert _refusal(query, access=access, **arguments) == limit
    # One row with a NULL in the non-null `id`, refused at its values when it
    # passes the byte limit, so nothing is copied; each `note` references a
    # prefix of one zero-filled buffer.
    null_id = ((None, 5, "", True, 0.0),)
    data = pa.py_buffer(bytearray(route.MAX_BYTES - orders(pa, null_id).nbytes + 1))

    def note(size: int) -> Any:
        offsets = pa.array([0, size], pa.int32()).buffers()[1]
        return pa.StringArray.from_buffers(1, offsets, data)

    exact = orders(pa, null_id, note=note(data.size - 1))
    above = orders(pa, null_id, note=note(data.size))
    assert exact.nbytes == route.MAX_BYTES and above.nbytes == route.MAX_BYTES + 1
    unselected = exact.append_column("pad", note(data.size))
    for table, refused in (
        (exact, schema),
        (unselected, schema),
        (above, limit),
        (above.drop_columns(["ok"]), schema),
    ):
        access = execution.DuckDBArrowInput("orders", table)
        assert _refusal(query, access=access, **arguments) == refused
    admitted = orders(pa, rows[:1]).append_column("pad", note(data.size))
    _handle(pa, query, admitted, **arguments).close()


def test_the_capture_is_an_owned_copy_of_the_selected_columns(
    filtered_query: execution.CompiledQuery,
) -> None:
    """Named c0..c4 in shape order, without the unselected column or rows,
    in buffers disjoint from the caller's, so a later change of the caller's
    buffer does not reach it."""
    pa = _pyarrow()
    query = filtered_query
    memory = bytearray((7).to_bytes(8, "little") * 4)
    ids = pa.Array.from_buffers(pa.int64(), 4, [None, pa.py_buffer(memory)])
    rows = ((0, 5, "a", True, 1.0),) * 4
    table = orders(pa, rows, id=ids).append_column("extra", pa.array([1, 2, 3, 4]))
    table = table.slice(1, 2)
    handle = _handle(pa, query, table, parameters={"min_amount": 1})
    (owned,) = handle._owner._capture
    assert owned.column_names == ["c0", "c1", "c2", "c3", "c4"]
    assert owned.num_rows == 2 and owned.column(0).to_pylist() == [7, 7]
    caller = route._ranges(
        [chunk for column in table.columns for chunk in column.chunks]
    )
    for column in owned.columns:
        for start, end in route._ranges(column.chunks):
            assert all(end <= lo or hi <= start for lo, hi in caller)
    assert owned.column(0).chunks[0].buffers()[1].size == 16
    memory[8:16] = (9).to_bytes(8, "little")
    assert table.column(0).to_pylist() == [9, 7] and owned.column(0).to_pylist() == [
        7,
        7,
    ]
    handle.close()


def _inputs(pa: Any, *names: str, **tables: Any) -> tuple[Any, ...]:
    """DuckDBArrowInput values of the named tables, `orders` and
    `customers` by default."""
    built = {"orders": orders(pa), "customers": customers(pa)} | tables
    return tuple(execution.DuckDBArrowInput(name, built[name]) for name in names)


def _joined_oracle(least: int) -> list[tuple[Any, ...]]:
    """JOINED computed in Python: orders whose amount and note match a
    customer's id and name, left-joined to the customer whose id is the
    order's id."""
    found = []
    for o_id, amount, note, _ok, _price in ROWS:
        if amount < least:
            continue
        for c_id, name, _rate in CUSTOMERS:
            if amount == c_id and note is not None and name == note:
                buyers = [b for b in CUSTOMERS if b[0] == o_id] or [(None, None, None)]
                for b_id, _name, rate in buyers:
                    found.append(
                        (("id", o_id), ("name", name), ("rate", rate), ("buyer", b_id))
                    )
    return sorted(found, key=repr)


def test_joined_inputs_are_matched_by_name_and_captured_once(
    joined_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D79.19: `access` is a tuple of inputs in any order, one for each
    relation name; `buyers` reads the `customers` input, captured once and
    registered for each source, in FROM and JOIN order."""
    pa = _engine()
    query = joined_query
    calls, _hooks = _recorded(monkeypatch)
    for names in (("orders", "customers"), ("customers", "orders")):
        calls.clear()
        handle = execution.execute(
            query,
            route="duckdb_arrow",
            access=_inputs(pa, *names),
            premise=None,
            parameters={"least": 0},
        )
        owned = handle._owner._capture
        assert [table.column_names for table in owned] == [
            ["c0", "c1", "c2", "c3", "c4"],
            ["c5", "c6", "c7"],
            ["c8", "c9", "c10"],
        ]
        for left, right in zip(owned[1].columns, owned[2].columns, strict=True):
            assert left.chunks[0].buffers()[1].address == (
                right.chunks[0].buffers()[1].address
            )
        with handle as result:
            rows = [r for batch in result for r in pa.record_batch(batch).to_pylist()]
        assert bag(rows) == _joined_oracle(0) and len(rows) == 2
        registered = [("register", f"pietto_arrow_{k}") for k in range(3)]
        assert calls == [
            ("connect", ":memory:"),
            *registered,
            *[("unregister", name) for _step, name in registered],
            ("close",),
        ]


def test_a_float_join_key_matches_minus_zero_and_zero(tmp_path: Path) -> None:
    """Pietto's `==` on the JOIN key: -0.0 matches 0.0, and each value keeps
    its sign."""
    pa = _engine()
    body = (
        "table result:\n    from orders\n"
        "    inner join customers on orders.price == customers.rate\n"
        "    select:\n        id = orders.id\n        price = orders.price\n"
        "        rate = customers.rate\n"
    )
    query = joined(tmp_path / "p", body)
    handle = execution.execute(
        query,
        route="duckdb_arrow",
        access=_inputs(pa, "orders", "customers"),
        premise=None,
    )
    with handle as result:
        rows = [r for batch in result for r in pa.record_batch(batch).to_pylist()]
    found = sorted(
        (r["id"], math.copysign(1, r["price"]), math.copysign(1, r["rate"]))
        for r in rows
    )
    assert found == [(2, -1, -1), (3, 1, 1), (5, 1, -1)]


def test_arithmetic_and_typed_keys_run_over_join_rows(tmp_path: Path) -> None:
    """Arithmetic over LEFT JOIN rows is NULL where the joined side has no
    match or a NULL operand, and a `Date` key joins equal days."""
    pa = _engine()
    document = narrowed(joined_contract())
    body = (
        "table result:\n    from orders\n"
        "    left join customers on orders.amount == customers.id\n"
        "    select:\n        id = orders.id\n        s = orders.amount + customers.id\n"
        "        r = customers.rate * orders.price\n"
    )
    query = joined(tmp_path / "arith", body, document=document)
    rows = ((1, 5, "a", True, 1.5), (2, 10, None, False, -0.0), (3, 7, "z", True, 2.0))
    access = _inputs(pa, "orders", "customers", orders=orders(pa, rows))
    handle = execution.execute(query, route="duckdb_arrow", access=access, premise=None)
    with handle as result:
        got = [r for batch in result for r in pa.record_batch(batch).to_pylist()]
    assert sorted(got, key=lambda r: r["id"]) == [
        {"id": 1, "s": 10, "r": 0.75},
        {"id": 2, "s": 20, "r": None},
        {"id": 3, "s": None, "r": None},
    ]
    header = TYPED_HEADER + 'source later: Event = duckdb.arrow("later")\n'
    document = contract(
        source_entry(fields=TYPED_FIELDS), source_entry("later", TYPED_FIELDS)
    )
    body = (
        "table result:\n    from orders\n"
        "    inner join later on orders.day == later.day\n"
        "    select:\n        id = orders.id\n        other = later.id\n"
    )
    query = joined(tmp_path / "day", body, header, document)
    at, cost, big = datetime(2024, 1, 1), Decimal("1.00"), Decimal("0")
    days = (date(2024, 1, 1), date(2024, 2, 29), None)
    left = events(pa, tuple((k, day, at, cost, big) for k, day in enumerate(days)))
    right = events(
        pa, tuple((10 + k, day, at, cost, big) for k, day in enumerate(days))
    )
    access = (
        execution.DuckDBArrowInput("orders", left),
        execution.DuckDBArrowInput("later", right),
    )
    handle = execution.execute(query, route="duckdb_arrow", access=access, premise=None)
    with handle as result:
        got = [r for batch in result for r in pa.record_batch(batch).to_pylist()]
    assert sorted((r["id"], r["other"]) for r in got) == [(0, 10), (1, 11)]


def test_arithmetic_over_a_chain_of_joins_is_null_on_its_left_joined_read(
    tmp_path: Path,
) -> None:
    """Each JOIN's kind decides the nullability of arithmetic over its own
    read: NULL rows come only from a LEFT JOIN's read, before or after an
    INNER JOIN, and the result check finds each column as documented."""
    pa = _engine()
    body = (
        "table result:\n    from orders\n"
        "    {0} join customers on customers.id == orders.amount\n"
        "    {1} join buyers on buyers.id == orders.id\n"
        "    select:\n        id = orders.id\n"
        "        c = customers.id + orders.id\n        b = buyers.id + orders.id\n"
    )
    rows = ((1, 5, "a", True, 1.5), (2, 10, None, False, 0.0))
    rows += ((3, 7, "z", True, 2.0), (5, 7, "y", False, 1.0))
    access = _inputs(pa, "orders", "customers", orders=orders(pa, rows))
    for kinds, expected in (
        (("inner", "left"), [(1, 6, 2), (2, 12, None)]),
        (("left", "inner"), [(1, 6, 2), (5, None, 10)]),
    ):
        root = tmp_path / "_".join(kinds)
        query = joined(root, body.format(*kinds), document=narrowed(joined_contract()))
        handle = execution.execute(
            query, route="duckdb_arrow", access=access, premise=None
        )
        with handle as result:
            got = [r for batch in result for r in pa.record_batch(batch).to_pylist()]
        assert sorted((r["id"], r["c"], r["b"]) for r in got) == expected, kinds


def test_the_inputs_must_name_each_relation_once(
    joined_query: execution.CompiledQuery,
    projection_query: execution.CompiledQuery,
) -> None:
    """Check 3 takes one input or a tuple of inputs; check 8 each input's
    name and table; check 9 the names, which must be exactly the relation
    names that the query reads, each once."""
    pa = _pyarrow()
    query = joined_query
    arguments: dict[str, Any] = {"parameters": {"least": 0}}
    schema = ("PIE-R1002", "DUCKDB_ARROW_SCHEMA")
    for access, refused in (
        (_inputs(pa, "orders", "customers", "orders"), schema),
        (_inputs(pa, "orders"), schema),
        (_inputs(pa, "orders")[0], schema),
        ((), schema),
        (_inputs(pa, "orders", "customers", "more", more=orders(pa)), schema),
        (list(_inputs(pa, "orders", "customers")), ("PIE-R1002", "PUBLIC_ACCESS_TYPE")),
        (
            (*_inputs(pa, "orders"), ("customers", customers(pa))),
            ("PIE-R1002", "PUBLIC_ACCESS_TYPE"),
        ),
        (
            (*_inputs(pa, "orders"), execution.DuckDBArrowInput("", customers(pa))),
            ("PIE-R1002", "EXECUTION_ACCESS"),
        ),
        (
            (*_inputs(pa, "orders"), execution.DuckDBArrowInput("customers", object())),
            ("PIE-R1002", "EXECUTION_ACCESS"),
        ),
    ):
        assert _refusal(query, access=access, **arguments) == refused, access
    single = projection_query
    rows, _handle_ = run(pa, single, orders(pa))
    handle = execution.execute(
        single, route="duckdb_arrow", access=_inputs(pa, "orders"), premise=None
    )
    with handle as result:
        assert [r for b in result for r in pa.record_batch(b).to_pylist()] == rows


def test_the_capture_limits_count_rows_per_input_and_bytes_once_in_all(
    joined_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D79.19 (ii): rows are counted for each input and the selected columns'
    bytes over all inputs together, an input that two sources read once."""
    pa = _pyarrow()
    query = joined_query
    arguments: dict[str, Any] = {"parameters": {"least": 0}}
    limit = ("PIE-R1002", "DUCKDB_ARROW_CAPTURE_LIMIT")
    tables = {"orders": orders(pa), "customers": customers(pa)}
    selected = sum(table.nbytes for table in tables.values())
    monkeypatch.setattr(route, "MAX_ROWS", len(ROWS))
    monkeypatch.setattr(route, "MAX_BYTES", selected)
    access = _inputs(pa, "orders", "customers")
    execution.execute(
        query, route="duckdb_arrow", access=access, premise=None, **arguments
    ).close()
    monkeypatch.setattr(route, "MAX_BYTES", selected - 1)
    assert _refusal(query, access=access, **arguments) == limit
    monkeypatch.setattr(route, "MAX_BYTES", 2**40)
    six = customers(pa, CUSTOMERS + ((20, "y", 1.0), (25, "z", 1.0)))
    access = _inputs(pa, "orders", "customers", customers=six)
    assert _refusal(query, access=access, **arguments) == limit


def test_the_capture_checks_each_later_input_as_it_checks_the_first(
    tmp_path: Path,
) -> None:
    """Steps 3 and 4 of the capture check every input against its read, not
    only the first: a later input of another Arrow type, an `Int` outside
    the `int_range` that rule 7c's proof reads, a NULL in a non-null field,
    a `Float` that is not finite, a `Text` beyond its characters, or a
    `Date`, `Timestamp` or `Decimal` outside its interval, is refused before
    any session (DUCKDB_ARROW_SCHEMA)."""
    pa = _engine()
    schema = ("PIE-R1002", "DUCKDB_ARROW_SCHEMA")
    body = (
        "table result:\n    from orders\n"
        "    inner join customers on customers.name == orders.note\n"
        "    select:\n        id = orders.id\n        s = orders.amount + customers.id\n"
    )
    query = joined(tmp_path / "p", body, document=narrowed(joined_contract()))
    first = orders(pa, ((1, 5, "a", True, 1.5),))
    later = customers(pa, ((7, "a", 0.5),))
    columns = {"id": 0, "name": 1, "rate": 2}
    forged = {
        "int32": ("id", pa.array([7], pa.int32())),
        "large_string": ("name", pa.array(["a"], pa.large_string())),
        "float32": ("rate", pa.array([0.5], pa.float32())),
        "beyond the int_range": ("id", pa.array([5000], pa.int64())),
        "below the int_range": ("id", pa.array([-1001], pa.int64())),
        "null in a non-null field": ("name", pa.array([None], pa.string())),
        "NaN": ("rate", pa.array([math.nan])),
        "-Inf": ("rate", pa.array([-math.inf])),
        "too many characters": ("name", pa.array(["a" * 101])),
    }
    for name, (column, array) in forged.items():
        table = later.set_column(columns[column], column, array)
        access = (
            execution.DuckDBArrowInput("orders", first),
            execution.DuckDBArrowInput("customers", table),
        )
        assert _refusal(query, access=access) == schema, name
    access = (
        execution.DuckDBArrowInput("orders", first),
        execution.DuckDBArrowInput("customers", later),
    )
    handle = execution.execute(query, route="duckdb_arrow", access=access, premise=None)
    with handle as result:
        rows = [r for batch in result for r in pa.record_batch(batch).to_pylist()]
    assert rows == [{"id": 1, "s": 12}]
    header = TYPED_HEADER + 'source later: Event = duckdb.arrow("later")\n'
    document = contract(
        source_entry(fields=TYPED_FIELDS), source_entry("later", TYPED_FIELDS)
    )
    body = (
        "table result:\n    from orders\n"
        "    inner join later on orders.id == later.id\n"
        "    select:\n        id = orders.id\n        day = later.day\n"
        "        at = later.at\n        cost = later.cost\n"
    )
    query = joined(tmp_path / "typed", body, header, document)
    one = TYPED_ROWS[:1]
    at = pa.array([datetime(2024, 1, 1)])
    forged = {
        "timestamp_ns": ("at", at.cast(pa.timestamp("ns"))),
        "decimal_scale": ("cost", pa.array([Decimal("1")], pa.decimal128(12, 3))),
        "date_before_1000": ("day", pa.array([date(999, 12, 31)], pa.date32())),
        "timestamp_past_the_civil_end": (
            "at",
            pa.array([datetime(9999, 12, 31, 23, 59, 59, 500000)], pa.timestamp("us")),
        ),
        "decimal_beyond_its_precision": (
            "cost",
            _over(pa, 10**12, pa.decimal128(12, 2)),
        ),
    }
    for name, (column, array) in forged.items():
        access = (
            execution.DuckDBArrowInput("orders", events(pa, one)),
            execution.DuckDBArrowInput("later", events(pa, one, **{column: array})),
        )
        assert _refusal(query, access=access) == schema, name
    access = (
        execution.DuckDBArrowInput("orders", events(pa, one)),
        execution.DuckDBArrowInput("later", events(pa, one)),
    )
    handle = execution.execute(query, route="duckdb_arrow", access=access, premise=None)
    with handle as result:
        rows = [r for batch in result for r in pa.record_batch(batch).to_pylist()]
    assert [r["id"] for r in rows] == [1]


def test_aggregates_over_join_rows_check_every_declared_key(
    tmp_path: Path, joined_query: execution.CompiledQuery
) -> None:
    """D79.24: with an aggregate over JOIN rows, an input that breaks a
    declared `unique(...)` key is refused before any session; without an
    aggregate it is not checked."""
    pa = _engine()
    grouped = joined(tmp_path / "grouped", JOINED_GROUPED)
    rows = [
        r
        for batch in _joined_result(pa, grouped, _inputs(pa, "orders", "customers"))
        for r in pa.record_batch(batch).to_pylist()
    ]
    assert [(r["name"], r["n"], r["total"]) for r in rows] == [
        ("c", 1, 15),
        ("x", 1, 10),
    ]
    assert math.copysign(1, rows[1]["top"]) == -1
    twice = customers(pa, CUSTOMERS + ((5, "b", None),))
    access = _inputs(pa, "orders", "customers", customers=twice)
    assert _refusal(grouped, access=access, parameters={"least": 6}) == (
        "PIE-R1002",
        "DUCKDB_ARROW_SCHEMA",
    )
    execution.execute(
        joined_query,
        route="duckdb_arrow",
        access=access,
        premise=None,
        parameters={"least": 0},
    ).close()
    # Every declared key, not only the one a proof used: a second key on
    # `name` breaks where the first, on `id`, holds.
    header = JOINED_HEADER.replace(
        "    key = unique(id)\n", "    key = unique(id)\n    other = unique(name)\n"
    )
    keyed = joined(tmp_path / "keyed", JOINED_GROUPED, header)
    named = customers(pa, CUSTOMERS + ((99, "a", None),))
    access = _inputs(pa, "orders", "customers", customers=named)
    assert _joined_result(pa, grouped, access)
    assert _refusal(keyed, access=access, parameters={"least": 6}) == (
        "PIE-R1002",
        "DUCKDB_ARROW_SCHEMA",
    )
    handle = execution.execute(
        keyed,
        route="duckdb_arrow",
        access=_inputs(pa, "orders", "customers"),
        premise=None,
        parameters={"least": 6},
    )
    assert [s.unique for s in handle._owner.facts.sources] == [(), ((0,), (1,))]
    handle.close()


def _joined_result(pa: Any, query: Any, access: Any) -> list[Any]:
    handle = execution.execute(
        query,
        route="duckdb_arrow",
        access=access,
        premise=None,
        parameters={"least": 6},
    )
    with handle as result:
        return list(result)


def test_a_key_is_unique_under_piettos_equality() -> None:
    """D79.24's check: -0.0 equals 0.0, Text compares by code point, a row
    with a NULL in the key is left out, and a key of two fields repeats only
    when both repeat."""
    pa = _pyarrow()
    pc = pytest.importorskip("pyarrow.compute")

    def holds(*columns: Any) -> bool:
        fields = [
            SimpleNamespace(tag="Float" if c.type == pa.float64() else "")
            for c in columns
        ]
        return route._unique(pa, pc, list(columns), fields)

    floats = pa.array([0.0, -0.0])
    assert not holds(floats) and holds(pa.array([0.0, 1.0, None, None]))
    assert holds(pa.array(["\u00e9", "e\u0301"])) and not holds(pa.array(["a", "a"]))
    ids, names = pa.array([1, 1, 2]), pa.array(["a", "b", "a"])
    assert holds(ids, names) and not holds(pa.array([1, 1]), pa.array(["a", "a"]))
    assert holds(pa.array([1, 1]), pa.array(["a", None]))
    assert holds(pa.array([], pa.int64()))


def test_a_join_that_repeats_rows_stops_at_the_limit(tmp_path: Path) -> None:
    """D79.20: a JOIN of 1,000 by 1,000 rows on one value reads only the
    batches up to max_rows, then refuses the next one."""
    pa = _engine()
    body = (
        "table result:\n    from orders\n"
        "    inner join customers on orders.note == customers.name\n"
        "    select:\n        id = orders.id\n        other = customers.id\n"
    )
    query = joined(tmp_path / "p", body)
    many = orders(pa, ((1, 5, "a", True, 1.0),) * 1000)
    names = customers(pa, tuple((k, "a", None) for k in range(1000)))
    handle = execution.execute(
        query,
        route="duckdb_arrow",
        access=_inputs(pa, "orders", "customers", orders=many, customers=names),
        premise=None,
        limits=execution.ExecutionLimits(batch_rows=1000, max_rows=3000),
    )
    failure = _failed(handle)
    outcome = handle.outcome
    assert (failure.code, outcome.rows, outcome.batches) == ("PIE-R3004", 3000, 3)
    assert outcome.transaction == "UNKNOWN"


# Orders within -1000 to 1000: each order's parent is the order whose id is
# its amount; orders 1 and 4 share a parent, and order 3 has none.
PARENTED = (
    (1, 2, "a", True, 1.5),
    (2, 3, None, False, -0.0),
    (3, 9, "c", True, 2.0),
    (4, 2, None, True, 4.0),
)


def _rows(handle: Any) -> list[dict[str, Any]]:
    pa = _pyarrow()
    with handle as result:
        return [r for batch in result for r in pa.record_batch(batch).to_pylist()]


def test_a_source_read_twice_is_captured_once_and_registered_for_each_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SELF_JOINED over one `orders` input: one copy of its columns under two
    captures, registered as pietto_arrow_0 and pietto_arrow_1; the LEFT JOIN
    rows and their arithmetic are the oracle's, NULL without a parent; the
    input's rows count once and its bytes once."""
    pa = _engine()
    query = joined(tmp_path / "p", SELF_JOINED, document=narrowed(joined_contract()))
    table = orders(pa, PARENTED)
    access = execution.DuckDBArrowInput("orders", table)
    calls, _hooks = _recorded(monkeypatch)
    handle = execution.execute(query, route="duckdb_arrow", access=access, premise=None)
    owned = handle._owner._capture
    assert [t.column_names for t in owned] == [
        ["c0", "c1", "c2", "c3", "c4"],
        ["c5", "c6", "c7", "c8", "c9"],
    ]
    for left, right in zip(owned[0].columns, owned[1].columns, strict=True):
        assert left.chunks[0].buffers()[1].address == (
            right.chunks[0].buffers()[1].address
        )
    parents = {row[0]: row for row in PARENTED}
    expected = []
    for o_id, amount, _note, _ok, price in PARENTED:
        parent = parents.get(amount)
        expected.append(
            {"id": o_id, "up": None, "s": None, "r": None}
            if parent is None
            else {
                "id": o_id,
                "up": parent[0],
                "s": amount + parent[1],
                "r": parent[4] + price,
            }
        )
    assert bag(_rows(handle)) == bag(expected)
    registered = [("register", f"pietto_arrow_{k}") for k in range(2)]
    assert calls == [
        ("connect", ":memory:"),
        *registered,
        *[("unregister", name) for _step, name in registered],
        ("close",),
    ]
    limit = ("PIE-R1002", "DUCKDB_ARROW_CAPTURE_LIMIT")
    monkeypatch.setattr(route, "MAX_ROWS", len(PARENTED))
    monkeypatch.setattr(route, "MAX_BYTES", table.nbytes)
    execution.execute(query, route="duckdb_arrow", access=access, premise=None).close()
    monkeypatch.setattr(route, "MAX_BYTES", table.nbytes - 1)
    assert _refusal(query, access=access) == limit
    monkeypatch.setattr(route, "MAX_BYTES", table.nbytes)
    monkeypatch.setattr(route, "MAX_ROWS", len(PARENTED) - 1)
    assert _refusal(query, access=access) == limit


def test_a_self_join_on_a_nullable_key_matches_no_null(tmp_path: Path) -> None:
    """TWIN_JOINED's INNER JOIN on `note`: each order whose note is not None
    matches itself, filtered by the second read's price, and order 2, whose
    note is None and whose price -0.0 passes that filter, matches nothing,
    not even itself."""
    pa = _engine()
    query = joined(tmp_path / "p", TWIN_JOINED)
    handle = execution.execute(
        query,
        route="duckdb_arrow",
        access=execution.DuckDBArrowInput("orders", orders(pa)),
        premise=None,
    )
    expected = sorted(
        (a[0], b[0])
        for a in ROWS
        for b in ROWS
        if a[2] is not None and a[2] == b[2] and b[4] >= 0.0
    )
    assert sorted((r["id"], r["other"]) for r in _rows(handle)) == expected
    assert expected == [(1, 1), (3, 3), (5, 5)]


def test_a_self_join_that_aggregates_checks_the_key_of_each_read(
    tmp_path: Path,
) -> None:
    """D79.24 over both reads of one input: SELF_GROUPED's groups are the
    oracle's; an input that repeats a declared id is refused before any
    session, and the same input runs a self-join without an aggregate."""
    pa = _engine()
    grouped = joined(tmp_path / "grouped", SELF_GROUPED, KEYED_HEADER)
    access = execution.DuckDBArrowInput("orders", orders(pa, PARENTED))
    arguments: dict[str, Any] = {"parameters": {"least": 0}}
    handle = execution.execute(
        grouped, route="duckdb_arrow", access=access, premise=None, **arguments
    )
    rows = _rows(handle)
    # Parents: 1 and 4 have order 2 (not ok), 2 has order 3 (ok), 3 none.
    assert [(r["ok"], r["n"], r["total"], r["top"]) for r in rows] == [
        (None, 1, 9, None),
        (False, 2, 4, -0.0),
        (True, 1, 3, 2.0),
    ]
    assert math.copysign(1, rows[1]["top"]) == -1
    assert [s.unique for s in handle._owner.facts.sources] == [((0,),)] * 2
    repeated = orders(pa, (*PARENTED, (4, 1, "d", True, 0.5)))
    access = execution.DuckDBArrowInput("orders", repeated)
    assert _refusal(grouped, access=access, **arguments) == (
        "PIE-R1002",
        "DUCKDB_ARROW_SCHEMA",
    )
    plain = joined(
        tmp_path / "plain", SELF_JOINED, KEYED_HEADER, narrowed(joined_contract())
    )
    handle = execution.execute(plain, route="duckdb_arrow", access=access, premise=None)
    assert len(_rows(handle)) == len(PARENTED) + 1


def test_each_operator_returns_the_oracle_bag_and_keeps_its_values(
    tmp_path: Path,
) -> None:
    """The oracle is computed in Python from the input before each run; an
    input-row permutation gives the same bag, and -0.0 keeps its sign bit."""
    pa = _engine()
    for position, (spelling, compare) in enumerate(OPERATORS.items()):
        query = compiled(tmp_path / str(position), filtered(spelling))
        for parameter in (-(2**63), 0, 10, 2**63 - 1):
            expected = bag(
                [{"id": r[0], "price": r[4]} for r in ROWS if compare(r[1], parameter)]
            )
            arguments = {"parameters": {"min_amount": parameter}}
            rows, handle = run(pa, query, orders(pa), **arguments)
            assert bag(rows) == expected, (spelling, parameter)
            assert handle.outcome.end == "COMPLETE"
            reversed_rows, _ = run(pa, query, orders(pa, ROWS[::-1]), **arguments)
            assert bag(reversed_rows) == expected
    rows, _ = run(
        pa,
        compiled(tmp_path / "eq", filtered("==")),
        orders(pa),
        parameters={"min_amount": 10},
    )
    assert (
        rows == [{"id": 2, "price": -0.0}] and math.copysign(1.0, rows[0]["price"]) < 0
    )
    rows, _ = run(pa, projection(tmp_path / "projection"), orders(pa))
    assert bag(rows) == bag([{"id": r[0], "note": r[2]} for r in ROWS])


def _and(a: bool | None, b: bool | None) -> bool | None:
    return False if a is False or b is False else None if None in (a, b) else True


def _or(a: bool | None, b: bool | None) -> bool | None:
    return True if a is True or b is True else None if None in (a, b) else False


def _not(a: bool | None) -> bool | None:
    return None if a is None else not a


def _eq(a: Any, b: Any) -> bool | None:
    return None if a is None or b is None else a == b


def _predicated(row: tuple[Any, ...], p: dict[str, Any]) -> bool:
    """PREDICATED's `where` over one row in three-valued logic."""
    id_, amount, note, ok, price = row
    first = _and(p["low"] <= amount, _not(_eq(note, p["label"])))
    second = _and(ok == p["flag"], price < p["cap"])
    third = _and(_and(amount != p["low"], note is None), id_ > -3)
    return _or(_or(first, second), third) is True


PREDICATED_PARAMETERS = (
    {"label": "a", "low": 10, "flag": True, "cap": 0.0},
    {"label": "", "low": -(2**63), "flag": False, "cap": -0.5},
    {"label": "é", "low": 2**63 - 1, "flag": True, "cap": 2.5},
    {"label": "c", "low": 5, "flag": False, "cap": -1.0},
)


def test_parameters_bind_by_their_types_in_placeholder_order(tmp_path: Path) -> None:
    """Each value is checked against its parameter's type before anything
    reaches DuckDB, whose cast would take 1.5 as the BIGINT 2; the values
    then go to the placeholders in the order of their first reads."""
    query = compiled(tmp_path / "p", PREDICATED)
    assert query.parameters == (
        ("label", "Text", False),
        ("low", "Int", False),
        ("flag", "Bool", False),
        ("cap", "Float", False),
    )
    facts = adapter.execution_facts(query._template)
    assert facts.placeholders == (1, 0, 2, 3)
    good = PREDICATED_PARAMETERS[0]
    assert route._bound(facts, None, good) == (10, "a", True, 0.0)
    access = execution.DuckDBArrowInput("orders", object())
    for name, value, refusal in (
        ("label", b"a", "0:Text"),
        ("label", None, "0:Text"),
        ("low", 1.5, "1:Int"),
        ("low", True, "1:Int"),
        ("flag", 1, "2:Bool"),
        ("cap", 1, "3:Float"),
        ("cap", math.inf, "3:Float"),
        ("cap", math.nan, "3:Float"),
    ):
        assert _refusal(query, access=access, parameters={**good, name: value}) == (
            "PIE-R1006",
            f"BINDING_PARAMETER:{refusal}",
        )


def test_predicates_return_the_three_valued_oracle_bag(tmp_path: Path) -> None:
    """PREDICATED over ROWS for each parameter set, against its oracle in
    three-valued logic computed before the run, for both input orders."""
    pa = _engine()
    query = compiled(tmp_path / "p", PREDICATED)
    for parameters in PREDICATED_PARAMETERS:
        expected = bag(
            [{"id": r[0], "note": r[2]} for r in ROWS if _predicated(r, parameters)]
        )
        for rows in (ROWS, ROWS[::-1]):
            delivered, handle = run(pa, query, orders(pa, rows), parameters=parameters)
            assert bag(delivered) == expected, parameters
            assert handle.outcome.end == "COMPLETE"


# Quotes, a backslash and multibyte text, both Int extremes, a negative zero
# and floats whose shortest decimal has an exponent, each written as a literal.
LITERAL_ROWS = (
    (1, 5, "it's", True, 1.5),
    (2, -(2**63), "a\\b", False, -0.0),
    (3, 2**63 - 1, "é€", True, 0.0),
    (4, 0, None, False, 0.000001),
    (5, 7, 'say "hi"', True, 0.1),
)
LITERAL_CELLS = (
    ("amount == -9223372036854775808", lambda r: r[1] == -(2**63)),
    ("amount == 9223372036854775807", lambda r: r[1] == 2**63 - 1),
    ("amount > -5 and amount < 6", lambda r: -5 < r[1] < 6),
    ("price == -0.0", lambda r: r[4] == 0.0),
    ("price == 0.000001 or price == 0.1", lambda r: r[4] in (0.000001, 0.1)),
    (r'''note == "it's" or note == "a\\b"''', lambda r: r[2] in ("it's", "a\\b")),
    ("note == 'say \"hi\"'", lambda r: r[2] == 'say "hi"'),
    ('note > "z"', lambda r: r[2] is not None and r[2] > "z"),
    ('not (note == "it\\\'s")', lambda r: r[2] is not None and r[2] != "it's"),
    ("note is None or ok == False", lambda r: r[2] is None or not r[3]),
    ("not (note is None) and amount > 0", lambda r: r[2] is not None and r[1] > 0),
    ("ok != True and not (price > 0.05)", lambda r: not r[3] and not r[4] > 0.05),
)


def test_literals_return_the_oracle_bag(tmp_path: Path) -> None:
    pa = _engine()
    for position, (where, keep) in enumerate(LITERAL_CELLS):
        body = PROJECTION.replace("    select:", f"    where {where}\n    select:")
        query = compiled(tmp_path / str(position), body)
        expected = bag([{"id": r[0], "note": r[2]} for r in LITERAL_ROWS if keep(r)])
        for rows in (LITERAL_ROWS, LITERAL_ROWS[::-1]):
            delivered, _ = run(pa, query, orders(pa, rows))
            assert bag(delivered) == expected, where


GROUPED_ROWS = (
    (1, 5, "a", True, 1.5),
    (2, 10, None, False, -0.0),
    (3, 15, "a", True, 0.0),
    (4, -7, None, False, -1.0),
    (5, 20, "a", False, 2.5),
    (6, 1, "a\x00", True, 3.0),
)


def test_a_grouped_query_returns_the_oracle_bag(tmp_path: Path) -> None:
    """GROUPED's groups, aggregates and having against a Python oracle
    computed before each run, NULL keys forming one group and `'a'` and
    `'a\\0'` two; a sum outside signed 64 bits fails the statement, and an
    aggregate without group by gives one row over no rows."""
    pa = _engine()
    query = compiled(tmp_path / "grouped", GROUPED)
    groups: dict[tuple[Any, Any], list[tuple[Any, ...]]] = {}
    for row in GROUPED_ROWS:
        groups.setdefault((row[2], row[3]), []).append(row)
    for minimum in (-(2**63), 15, 2**63 - 1):
        expected = bag(
            [
                {
                    "note": note,
                    "ok": ok,
                    "n": len(rows),
                    "filled": sum(r[2] is not None for r in rows),
                    "c1": sum(r[1] for r in rows),
                    "low": min(r[4] for r in rows),
                    "high": max(r[0] for r in rows),
                }
                for (note, ok), rows in groups.items()
                if sum(r[1] for r in rows) >= minimum
            ]
        )
        table = orders(pa, GROUPED_ROWS)
        rows, handle = run(pa, query, table, parameters={"min_total": minimum})
        assert bag(rows) == expected and handle.outcome.end == "COMPLETE"
    overflow = ((1, 2**63 - 1, "a", True, 0.0), (2, 1, "a", True, 0.0))
    handle = _handle(pa, query, orders(pa, overflow), parameters={"min_total": 0})
    failure = _failed(handle)
    assert (failure.code, failure.failure.phase) == ("PIE-R3003", "query")
    body = "table result:\n    from orders\n    select:\n        n = count()\n"
    rows, _ = run(pa, compiled(tmp_path / "global", body), orders(pa, ()))
    assert rows == [{"n": 0}]


# Order keys over ROWS, the rows' ids in the order PostgreSQL gives: NULL
# last ascending and first descending, Text by its bytes, -0.0 and 0.0 tied
# (broken by id), false before true, and the first rows within a limit.
ORDER_CELLS = (
    ("note desc\n        id", None, [2, 5, 3, 1, 4]),
    ("note\n        id", 3, [4, 1, 3]),
    ("price\n        id desc", None, [4, 5, 2, 1, 3]),
    ("ok\n        id desc", None, [4, 2, 5, 3, 1]),
    ("id", 0, []),
)


def test_ordered_queries_return_the_oracle_order(tmp_path: Path) -> None:
    """Each cell's ids in its order for both input orders, and ORDERED's
    groups in the oracle's order, sorted in Python before the run, cut to
    the first four of five."""
    pa = _engine()
    for position, (keys, limit, ids) in enumerate(ORDER_CELLS):
        body = PROJECTION + f"    order by:\n        {keys}\n"
        body += "" if limit is None else f"    limit {limit}\n"
        query = compiled(tmp_path / str(position), body)
        for rows in (ROWS, ROWS[::-1]):
            delivered, handle = run(pa, query, orders(pa, rows))
            assert [r["id"] for r in delivered] == ids, keys
            assert handle.outcome.end == "COMPLETE"
    rows = (*GROUPED_ROWS, (7, 2, "b", True, 4.0))
    groups: dict[tuple[Any, Any], list[tuple[Any, ...]]] = {}
    for row in rows:
        groups.setdefault((row[2], row[3]), []).append(row)
    expected = sorted(
        (
            {
                "note": note,
                "ok": ok,
                "n": len(members),
                "filled": sum(r[2] is not None for r in members),
                "c1": sum(r[1] for r in members),
                "low": min(r[4] for r in members),
                "high": max(r[0] for r in members),
            }
            for (note, ok), members in groups.items()
        ),
        key=lambda r: (-r["c1"], r["low"], r["note"] is None, r["note"] or ""),
    )
    query = compiled(tmp_path / "ordered", ORDERED)
    delivered, _ = run(pa, query, orders(pa, rows), parameters={"min_total": 0})
    assert len(expected) == 5 and delivered == expected[:4]


# A NUL at the start, in the middle and at the end, values of only NUL (the
# last at max_characters), values longer than DuckDB's 12 inline bytes, and
# the prefixes that a cut at the first NUL would collapse into.
NUL_NOTES = (
    "\0a",
    "a\0b",
    "a\0",
    "\0",
    "\0\0\0",
    "\0" * 100,
    "a",
    "",
    "é\0é",
    "abcdefghijkl\0mnopq",
    "abcdefghijk\0",
    None,
)


def test_a_nul_in_text_reaches_duckdb_and_the_caller_unchanged(
    projection_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    """The capture admits a NUL anywhere in a Text value, copies it as is,
    and the projection and the filtered query deliver every value byte for
    byte, each value distinct from its prefixes."""
    pa = _engine()
    rows = tuple((k, k % 3, note, True, 1.0) for k, note in enumerate(NUL_NOTES))
    table = orders(pa, rows)
    query = projection_query
    handle = _handle(pa, query, table)
    assert handle._owner._capture[0].column(2).to_pylist() == list(NUL_NOTES)
    handle.close()
    delivered, handle = run(pa, query, table)
    assert handle.outcome.end == "COMPLETE"
    assert bag(delivered) == bag([{"id": r[0], "note": r[2]} for r in rows])
    body = filtered("!=").replace("        price\n", "        note\n")
    delivered, handle = run(
        pa, compiled(tmp_path / "q", body), table, parameters={"min_amount": 1}
    )
    assert handle.outcome.end == "COMPLETE"
    assert bag(delivered) == bag(
        [{"id": r[0], "note": r[2]} for r in rows if r[1] != 1]
    )


def test_batches_have_the_compiled_schema_and_follow_the_limits(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reader marks every field nullable; the route restores the compiled
    nullability, and `pyarrow.schema(handle)` needs no I/O. Success and a
    refused batch each unregister the capture and close the session; a
    refused batch ends a statement that has not ended, so its transaction is
    UNKNOWN, and the batches delivered before it stay delivered."""
    pa = _engine()
    query = projection_query
    calls, _hooks = _recorded(monkeypatch)
    handle = _handle(pa, query, limits=execution.ExecutionLimits(batch_rows=2))
    schema = pa.schema(handle)
    assert [(f.name, str(f.type), f.nullable) for f in schema] == [
        ("id", "int64", False),
        ("note", "string", True),
    ]
    assert handle.outcome.end == "NOT_STARTED" and calls == []
    with handle as result:
        batches = [pa.record_batch(batch) for batch in result]
    assert calls == [*OPENED, *ENDED]
    assert [b.num_rows for b in batches] == [2, 2, 1]
    assert all(b.schema.equals(schema) for b in batches)
    outcome = handle.outcome
    assert (outcome.end, outcome.source, outcome.transaction, outcome.delivery) == (
        "COMPLETE",
        "EOF",
        "COMMIT_ACK",
        "COMPLETE",
    )
    assert (outcome.cleanup, outcome.rows, outcome.batches, outcome.primary) == (
        "LOCAL_CLOSED_REMOTE_UNOBSERVED",
        5,
        3,
        None,
    )
    assert outcome.bytes == sum(b.nbytes for b in batches)
    for limits in (
        execution.ExecutionLimits(max_rows=4),
        execution.ExecutionLimits(batch_bytes=8),
        execution.ExecutionLimits(batch_rows=2, max_bytes=40),
    ):
        calls.clear()
        failure = _failed(_handle(pa, query, limits=limits))
        assert (failure.code, failure.detail) == (
            "PIE-R3004",
            "EXECUTION_RESOURCE_LIMIT",
        )
        assert failure.outcome is not None and failure.outcome.end == "FAILED"
        assert failure.outcome.transaction == "UNKNOWN"
        assert calls == [*OPENED, *ENDED]
    # max_bytes 40 refuses the second batch of two rows, after the first.
    assert (failure.outcome.batches, failure.outcome.rows) == (1, 2)


def test_a_result_far_beyond_the_limits_stops_at_its_first_batch_beyond_them(
    projection_query: execution.CompiledQuery,
) -> None:
    """The reader reads one batch at a time: a statement of 10^12 rows stops
    at the third batch of two rows under max_rows 4, after two delivered."""
    pa = _engine()
    limits = execution.ExecutionLimits(batch_rows=2, max_rows=4)
    handle = _handle(pa, projection_query, limits=limits)
    handle._owner._sql = (
        'SELECT CAST(range AS BIGINT) AS "id", CAST(NULL AS VARCHAR) AS "note"'
        " FROM range(1000000000000)"
    )
    delivered = []
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle as result:
            for batch in result:
                delivered.append(pa.record_batch(batch).column(0).to_pylist())
    outcome = handle.outcome
    assert (failed.value.code, delivered) == ("PIE-R3004", [[0, 1], [2, 3]])
    assert (outcome.rows, outcome.batches, outcome.transaction) == (4, 2, "UNKNOWN")
    assert outcome.cleanup == "LOCAL_CLOSED_REMOTE_UNOBSERVED"


def test_close_and_cancel_before_and_after_the_session_opens(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before the session opens, neither connects; after, an early close and
    a consumer's exception each close the reader before its end, so the
    transaction is UNKNOWN, unregister the capture and close."""
    pa = _engine()
    query = projection_query
    calls, _hooks = _recorded(monkeypatch)
    handle = _handle(pa, query)
    handle.close()
    assert (handle.outcome.end, handle.outcome.transaction) == (
        "NOT_STARTED",
        "NOT_STARTED",
    )
    assert calls == []
    handle = _handle(pa, query)
    with handle:
        pass
    outcome = handle.outcome
    assert (outcome.end, outcome.source, outcome.delivery, outcome.cleanup) == (
        "STOPPED_EARLY",
        "EARLY_CLOSE",
        "INCOMPLETE",
        "LOCAL_CLOSED_REMOTE_UNOBSERVED",
    )
    assert outcome.transaction == "UNKNOWN"
    assert handle._owner._connection is None and handle._owner._capture is None
    assert handle._owner._reader is None
    assert calls == [*OPENED, *ENDED]
    with pytest.raises(execution.HandleMisuse) as misuse:
        handle.__enter__()
    assert misuse.value.code == "PIE-R4001"
    calls.clear()
    handle = _handle(pa, query)
    handle.cancel()
    failure = _failed(handle)
    assert failure.code == "PIE-R3009" and handle.outcome.end == "CANCELLED"
    assert handle.outcome.cancel_requested and not handle.outcome.cancel_sent
    # The first check of the opening attempt: no driver, no connection.
    assert handle._owner._primary.phase == "driver" and calls == []
    handle = _handle(pa, query)
    with pytest.raises(LookupError):
        with handle as result:
            next(result)
            raise LookupError("consumer")
    primary = handle.outcome.primary
    assert primary is not None and (primary.code, primary.phase) == (
        "PIE-R3007",
        "consumer",
    )
    assert calls == [*OPENED, *ENDED]


def _slow(handle: Any) -> Any:
    owner = handle._owner
    owner._sql = SLOW
    return handle


def _running(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[tuple[str, ...]], dict[str, Any], threading.Event, threading.Event]:
    """The recorded calls and hooks, an event that `pietto_running` sets from
    inside the engine, and the watchdog's: WATCHDOG_SECONDS after its first
    batch, `pietto_running` sets it and fails the statement, so an interrupt
    that never stops the statement fails the test in bounded time instead
    of hanging it."""
    pa = _pyarrow()
    calls, hooks = _recorded(monkeypatch)
    running, tripped = threading.Event(), threading.Event()
    limit: list[float] = []
    batch = pa.record_batch([pa.array([0], pa.int64())], names=["i"])

    def batches() -> Any:
        while True:
            if not limit:
                limit.append(time.monotonic() + WATCHDOG_SECONDS)
            elif time.monotonic() > limit[0]:
                tripped.set()
                raise TimeoutError("watchdog")
            running.set()
            yield batch

    hooks["register"] = lambda connection: connection.register(
        "pietto_running", pa.RecordBatchReader.from_batches(batch.schema, batches())
    )
    return calls, hooks, running, tripped


def _interrupted(calls: list[tuple[str, ...]]) -> None:
    """The calls of an interrupted attempt: the route sends its interrupt
    again until the statement ends, so one or more lie between the opening
    and the end."""
    sent = calls.count(("interrupt",))
    assert sent >= 1 and calls == [*OPENED, *[("interrupt",)] * sent, *ENDED]


class _Threads:
    """The route's `threading`, recording each thread it creates with its
    target, so that a test can join the resend thread a cancel starts."""

    def __init__(self) -> None:
        self.created: list[tuple[Any, threading.Thread]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(threading, name)

    def Thread(self, *args: Any, **kwargs: Any) -> threading.Thread:
        thread = threading.Thread(*args, **kwargs)
        self.created.append((kwargs.get("target"), thread))
        return thread


def _resends(monkeypatch: pytest.MonkeyPatch) -> _Threads:
    threads = _Threads()
    monkeypatch.setattr(route, "threading", threads)
    return threads


def _stopped(owner: Any, threads: _Threads, calls: list[tuple[str, ...]]) -> None:
    """An interrupted attempt's calls, and its one resend thread stopped with
    the statement: joined for at most WATCHDOG_SECONDS, it is no longer
    alive, and no interrupt follows the attempt's end."""
    assert owner._ended.is_set()
    resends = [t for target, t in threads.created if target == owner._resend]
    assert len(resends) == 1
    resends[0].join(WATCHDOG_SECONDS)
    assert not resends[0].is_alive()
    _interrupted(calls)


def test_cancel_and_the_deadline_interrupt_a_running_statement(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each acts once the statement runs inside the engine, however long the
    session setup took: a cancel, then the deadline timer that the attempt
    armed when it opened, fired at that point instead of waited for. Each
    attempt's resend thread stops with its statement."""
    pa = _engine()
    query = projection_query
    calls, _hooks, running, tripped = _running(monkeypatch)
    threads = _resends(monkeypatch)
    handle = _slow(_handle(pa, query))
    canceller = threading.Thread(target=lambda: running.wait(60) and handle.cancel())
    canceller.start()
    failure = _failed(handle)
    canceller.join()
    outcome = handle.outcome
    assert not tripped.is_set()
    assert (failure.code, outcome.end, outcome.transaction) == (
        "PIE-R3009",
        "CANCELLED",
        "UNKNOWN",
    )
    assert outcome.cancel_requested and outcome.cancel_sent and outcome.cancel_observed
    _stopped(handle._owner, threads, calls)
    assert outcome.cleanup_failures == ()
    calls.clear()
    running.clear()
    seconds = 600.0
    handle = _slow(
        _handle(pa, query, limits=execution.ExecutionLimits(seconds=seconds))
    )
    owner = handle._owner
    armed: list[Any] = []

    def expire() -> None:
        if running.wait(60):
            timer = owner._timer
            armed.append((timer, timer.is_alive(), timer.function == owner.cancel))
            timer.function(*timer.args, **timer.kwargs)

    expirer = threading.Thread(target=expire)
    expirer.start()
    failure = _failed(handle)
    expirer.join()
    outcome = handle.outcome
    assert not tripped.is_set()
    assert (
        failure.code,
        outcome.end,
        outcome.deadline_expired,
        outcome.transaction,
    ) == ("PIE-R3001", "DEADLINE", True, "UNKNOWN")
    assert outcome.cancel_sent and outcome.cancel_observed
    _stopped(owner, threads, calls)
    assert outcome.cleanup_failures == ()
    assert owner._connection is None
    ((timer, alive, cancels),) = armed
    assert alive and cancels and timer.kwargs == {"deadline": True}
    assert 0 < timer.interval <= seconds
    timer.join(60)
    assert not timer.is_alive()


@pytest.mark.parametrize("deadline", [False, True], ids=["cancel", "deadline"])
def test_an_interrupt_sent_before_the_statement_starts_still_stops_it(
    projection_query: execution.CompiledQuery,
    monkeypatch: pytest.MonkeyPatch,
    deadline: bool,
) -> None:
    """A cancel, or the deadline timer's callback, that reaches the connection
    after the attempt marked its statement running but before the engine
    started it: DuckDB drops that interrupt, and the route sends it again
    until the statement ends, so the statement is still interrupted; the
    resend thread then stops."""
    pa = _engine()
    calls, hooks, running, tripped = _running(monkeypatch)
    threads = _resends(monkeypatch)
    handle = _slow(
        _handle(
            pa,
            projection_query,
            limits=execution.ExecutionLimits(seconds=600.0),
        )
    )
    owner = handle._owner
    early: list[tuple[bool, bool]] = []

    def before_the_statement() -> None:
        early.append((owner._running, running.is_set()))
        if deadline:
            owner._timer.function(*owner._timer.args, **owner._timer.kwargs)
        else:
            handle.cancel()

    hooks["statement"] = before_the_statement
    failure = _failed(handle)
    outcome = handle.outcome
    assert not tripped.is_set() and early == [(True, False)]
    assert (failure.code, outcome.end, outcome.deadline_expired) == (
        ("PIE-R3001", "DEADLINE", True)
        if deadline
        else ("PIE-R3009", "CANCELLED", False)
    )
    assert outcome.cancel_requested and outcome.cancel_sent and outcome.cancel_observed
    _stopped(owner, threads, calls)
    assert outcome.cleanup_failures == () and owner._connection is None


def test_a_deadline_that_passes_during_the_statement_stops_before_the_result(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check after the statement: the deadline passed while it ran, before
    the timer fired (the route's clock moves on there), so the attempt ends
    in its query step with no batch; the reader is open and the statement
    has not ended, so the route interrupts it, unobserved, and its
    transaction is UNKNOWN."""
    pa = _engine()
    clock = [0.0]
    monkeypatch.setattr(route, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    calls, hooks = _recorded(monkeypatch)
    hooks["statement"] = lambda: clock.__setitem__(0, 3600.0)
    handle = _handle(pa, projection_query)
    failure = _failed(handle)
    assert (
        failure.code,
        failure.failure.phase,
        handle.outcome.end,
        handle.outcome.transaction,
    ) == ("PIE-R3001", "query", "DEADLINE", "UNKNOWN")
    assert handle.outcome.cancel_sent and not handle.outcome.cancel_observed
    assert handle._owner._batches is None
    assert calls[:2] == OPENED and calls[-2:] == ENDED
    assert set(calls[2:-2]) == {("interrupt",)}


def test_a_cancel_after_the_reader_ended_stops_before_the_end(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cancel that arrives at the check after the reader's end, once the
    statement has ended: nothing is interrupted, the attempt ends CANCELLED,
    as any cancellation with no phase, rather than COMPLETE; the batch
    delivered before stays delivered, and the transaction is COMMIT_ACK."""
    pa = _engine()
    calls, _hooks = _recorded(monkeypatch)
    handle = _handle(pa, projection_query)
    owner = handle._owner
    check = owner._checkpoint
    seen: list[tuple[bool, bool]] = []

    def late() -> None:
        if owner._ended.is_set() and not seen:
            seen.append((owner._running, owner._ended.is_set()))
            handle.cancel()
        check()

    owner._checkpoint = late
    failure = _failed(handle)
    outcome = handle.outcome
    assert seen == [(False, True)]
    assert (
        failure.code,
        failure.failure.phase,
        outcome.end,
        outcome.transaction,
        outcome.cleanup,
    ) == (
        "PIE-R3009",
        None,
        "CANCELLED",
        "COMMIT_ACK",
        "LOCAL_CLOSED_REMOTE_UNOBSERVED",
    )
    assert outcome.cancel_requested and not outcome.cancel_sent
    assert outcome.batches == 1 and calls == [*OPENED, *ENDED]


def test_a_cancel_during_a_batch_read_is_observed_through_its_oserror(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A batch read raises DuckDB's interrupt as OSError: a cancel sent while
    the second batch of a streamed projection is read stops the statement,
    observed, and leaves the transaction UNKNOWN after one batch."""
    pa = _engine()
    calls, _hooks = _recorded(monkeypatch)
    limits = execution.ExecutionLimits(batch_rows=2)
    handle = _handle(pa, projection_query, limits=limits)
    owner = handle._owner
    owner._sql = (
        'SELECT CAST(range AS BIGINT) AS "id", CAST(NULL AS VARCHAR) AS "note"'
        " FROM range(1000000000000)"
    )
    reads: list[None] = []

    class _Cancelling:
        def __init__(self, reader: Any) -> None:
            self._reader = reader

        def __getattr__(self, name: str) -> Any:
            return getattr(self._reader, name)

        def read_next_batch(self) -> Any:
            reads.append(None)
            if len(reads) == 2:
                handle.cancel()
            return self._reader.read_next_batch()

    with pytest.raises(execution.AttemptFailed) as failed:
        with handle as result:
            owner._reader = _Cancelling(owner._reader)
            list(result)
    outcome = handle.outcome
    assert (failed.value.code, outcome.end, outcome.transaction) == (
        "PIE-R3009",
        "CANCELLED",
        "UNKNOWN",
    )
    assert (owner._primary.phase, owner._primary.kind) == ("query", "OSError")
    assert outcome.cancel_sent and outcome.cancel_observed
    assert outcome.batches == 1 and len(reads) == 2
    assert calls[:2] == OPENED and calls[-2:] == ENDED


def test_setup_failures_refuse_the_route_before_its_statement(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A driver that is absent or another release, an engine of another
    profile, a setting that fails or reads back otherwise, a registration
    that fails: the statement never runs, and a session that was opened is
    closed (AD79.01; the spec's session steps 1, 2 and 5)."""
    pa = _engine()
    query = projection_query
    calls, hooks = _recorded(monkeypatch)
    closed = [("connect", ":memory:"), ("close",)]

    def refuse(_connection: Any) -> None:
        raise RuntimeError("registration failed")

    cases: list[tuple[str, Any, str, str, list[tuple[str, ...]]]] = [
        (
            "DRIVER",
            ("pietto-no-such-duckdb", "2.0.0", "duckdb"),
            "PIE-R2001",
            "EXECUTION_DEPENDENCY_MISSING",
            [],
        ),
        (
            "DRIVER",
            ("duckdb", "1.0.0", "duckdb"),
            "PIE-R2002",
            "EXECUTION_DRIVER_VERSION",
            [],
        ),
        (
            "ENGINE",
            [("v2.0.0", "0000000000")],
            "PIE-R2002",
            "DUCKDB_DRIVER_PROFILE",
            closed,
        ),
        (
            "SETTINGS",
            (*route.SETTINGS[:-1], ("pietto_no_such_setting", "1", "1")),
            "PIE-R2006",
            "DUCKDB_SESSION_CONTEXT",
            closed,
        ),
        (
            "READ_BACK",
            (*route.READ_BACK, ("threads", "2")),
            "PIE-R2006",
            "DUCKDB_SESSION_CONTEXT",
            closed,
        ),
        (
            "register",
            refuse,
            "PIE-R2006",
            "DUCKDB_SESSION_CONTEXT",
            [*OPENED, ("close",)],
        ),
    ]
    for name, value, code, detail, expected in cases:
        calls.clear()
        with monkeypatch.context() as patch:
            if name == "register":
                patch.setitem(hooks, name, value)
            else:
                patch.setattr(route, name, value)
            handle = _handle(pa, query)
            handle._owner._sql = "SELECT pietto_never_runs()"
            failure = _failed(handle)
        assert (failure.code, failure.detail, failure.failure.sqlstate) == (
            code,
            detail,
            None,
        )
        assert handle.outcome.transaction == "NOT_STARTED"
        assert handle.outcome.end == "FAILED" and handle._owner._connection is None
        assert calls == expected, name


def test_statement_and_result_failures_are_attempt_failures(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A DuckDB error is PIE-R3003 with its class name and no SQLSTATE; a
    result that does not fit the compiled one is PIE-R3005. Each leaves the
    statement unended, its transaction UNKNOWN, and unregisters the capture
    and closes the session. An error that a batch read raises reaches the
    route as OSError, whatever DuckDB's own class."""
    pa = _engine()
    query = projection_query
    calls, _hooks = _recorded(monkeypatch)
    relation = 'FROM temp.main."pietto_arrow_0"'
    cases = [
        (
            f'SELECT CAST(9223372036854775807 AS BIGINT) + "c0" AS "id", "c2" AS "note" {relation}',
            "PIE-R3003",
            "OutOfRangeException",
            "query",
        ),
        (
            f'SELECT "c0" AS "ID", "c2" AS "note" {relation}',
            "PIE-R3005",
            "ResultError",
            "result",
        ),
        (
            f'SELECT "c2" AS "id", "c2" AS "note" {relation}',
            "PIE-R3005",
            "ResultError",
            "result",
        ),
        (
            f'SELECT CAST(NULL AS BIGINT) AS "id", "c2" AS "note" {relation}',
            "PIE-R3005",
            "ResultError",
            "result",
        ),
    ]
    # The first batch of 2,048 rows reads, the next overflows while read.
    overflow = (
        "SELECT CAST(9223372036854775807 AS BIGINT) - 2048 + CAST(range AS BIGINT)"
        ' AS "id", NULL AS "note" FROM range(4096)'
    )
    cases.append((overflow, "PIE-R3003", "OSError", "query"))
    for sql, code, cause, phase in cases:
        calls.clear()
        handle = _handle(pa, query)
        handle._owner._sql = sql
        failure = _failed(handle)
        assert (failure.code, failure.failure.cause, failure.failure.sqlstate) == (
            code,
            cause,
            None,
        )
        assert failure.failure.phase == phase and handle.outcome.end == "FAILED"
        assert handle.outcome.transaction == "UNKNOWN"
        assert calls == [*OPENED, *ENDED]


# Arithmetic over optional operands whose Int range proves every product (3037000499 is
# the largest square root below 2^63), arithmetic and signs of both types.
PAIR = (
    ("id", "Int", False),
    ("a", "Int", True),
    ("b", "Int", True),
    ("x", "Float", True),
    ("y", "Float", True),
)
PAIR_HEADER = """shape Pair:
    id: Int
    a: Int | None
    b: Int | None
    x: Float | None
    y: Float | None

source orders: Pair = duckdb.arrow("orders")
"""
PAIR_BODY = """table result:
    from orders
    select:
        id
        s = a + b
        d = a - b
        m = a * b
        fs = x + y
        fd = x - y
        fm = x * y
        n = -x
        p = +x
"""
ROOT_63 = 3037000499
PAIR_ROWS = (
    (1, ROOT_63, ROOT_63, 1.5, 2.25),
    (2, -ROOT_63, ROOT_63, -0.0, 0.0),
    (3, None, 5, None, 1.0),
    (4, 0, -ROOT_63, 5e-324, 0.75),
    (5, 7, None, 2.2250738585072014e-308, 0.5),
    (6, -1, 1, 0.0, 1e-200),
    (7, 1, -1, 0.1, 0.2),
    (8, 2, 3, -0.0, -0.0),
)


def _pair(pa: Any, tmp_path: Path, body: str = PAIR_BODY) -> tuple[Any, Any]:
    entry = source_entry(fields=PAIR)
    for field in entry["fields"][1:3]:
        field["representation"]["domain"].update(min=str(-ROOT_63), max=str(ROOT_63))
    root = write(tmp_path / "p", body, contract(entry), PAIR_HEADER)
    query = execution.compile_query(
        root,
        module="main.pietto",
        kind="table",
        name="result",
        dialect="duckdb",
        emission_contract="contract.json",
    )
    types = (pa.int64(), pa.int64(), pa.int64(), pa.float64(), pa.float64())

    def table(rows: tuple[tuple[Any, ...], ...]) -> Any:
        return pa.table(
            {
                name: pa.array([row[k] for row in rows], type=types[k])
                for k, (name, _, _) in enumerate(PAIR)
            }
        )

    return query, table


def _bits(value: Any) -> Any:
    return value.hex() if type(value) is float else value


def test_arithmetic_returns_the_oracle_values(tmp_path: Path) -> None:
    """Python's exact Int and binary64 results, the sign of every zero,
    subnormal products and NULL operands included, for both input orders."""
    pa = _engine()
    query, table = _pair(pa, tmp_path)

    def oracle(row: tuple[Any, ...]) -> dict[str, Any]:
        id_, a, b, x, y = row

        def both(f: Any, u: Any, v: Any) -> Any:
            return None if u is None or v is None else f(u, v)

        return {
            "id": id_,
            "s": both(operator.add, a, b),
            "d": both(operator.sub, a, b),
            "m": both(operator.mul, a, b),
            "fs": both(operator.add, x, y),
            "fd": both(operator.sub, x, y),
            "fm": both(operator.mul, x, y),
            "n": None if x is None else -x,
            "p": x,
        }

    expected = bag([{k: _bits(v) for k, v in oracle(r).items()} for r in PAIR_ROWS])
    for rows in (PAIR_ROWS, PAIR_ROWS[::-1]):
        delivered, _ = run(pa, query, table(rows))
        got = [{k: _bits(v) for k, v in row.items()} for row in delivered]
        assert bag(got) == expected


def test_a_float_result_outside_binary64_fails_the_statement(tmp_path: Path) -> None:
    """An infinity or a zero product of non-zero operands is never returned:
    the statement fails with PIE-R3003 and its own detail, and its text
    carries no hint, which only the documentation gives."""
    pa = _engine()
    query, table = _pair(pa, tmp_path)
    big, tiny = sys.float_info.max, 1e-200
    for x, y, detail in (
        (big, big, "DUCKDB_FLOAT_OVERFLOW"),
        (-big, big, "DUCKDB_FLOAT_OVERFLOW"),
        (1e200, 1e200, "DUCKDB_FLOAT_OVERFLOW"),
        (tiny, tiny, "DUCKDB_FLOAT_UNDERFLOW"),
        (-tiny, tiny, "DUCKDB_FLOAT_UNDERFLOW"),
        (5e-324, 0.5, "DUCKDB_FLOAT_UNDERFLOW"),
    ):
        handle = _handle(pa, query, table(((1, 0, 0, x, y),)))
        failure = _failed(handle).failure
        assert (failure.code, failure.detail, failure.phase, failure.cause) == (
            "PIE-R3003",
            detail,
            "query",
            "InvalidInputException",
        )
        assert str(failure).endswith(", cause=InvalidInputException)")
        assert handle.outcome.end == "FAILED"
    # The first 2,048 rows read; the next row fails while its batch is read,
    # which raises the check's error as OSError, still named by its word.
    rows = tuple((k, 0, 0, 1.0, 1.0) for k in range(2048))
    handle = _handle(pa, query, table((*rows, (2048, 0, 0, big, big))))
    failure = _failed(handle).failure
    assert (failure.code, failure.detail, failure.phase, failure.cause) == (
        "PIE-R3003",
        "DUCKDB_FLOAT_OVERFLOW",
        "query",
        "OSError",
    )
    # A + or a - alone, with no product beside it to fail the same rows.
    for value, x in (("fs = x + y", big), ("fd = x - y", -big)):
        body = f"table result:\n    from orders\n    select:\n        {value}\n"
        query, table = _pair(pa, tmp_path / value[:2], body)
        failure = _failed(_handle(pa, query, table(((1, 0, 0, x, big),)))).failure
        assert (failure.code, failure.detail) == ("PIE-R3003", "DUCKDB_FLOAT_OVERFLOW")


# Arithmetic over group keys: a NULL group, a -0.0 group and an Int square
# at the edge of its proved range; each group's key value is unambiguous.
GROUPED_PAIR = """table result:
    from orders
    group by a, x
    select:
        a
        x
        t = a * a
        f = x * x
        g = -x
        n = count()
"""
GROUPED_PAIR_ROWS = (
    (None, 1.5),
    (None, 1.5),
    (2, -0.0),
    (2, -0.0),
    (3, 0.0),
    (ROOT_63, None),
    (-ROOT_63, 2.5),
    (None, None),
)


def test_grouped_arithmetic_returns_the_oracle_values(tmp_path: Path) -> None:
    """Each group's keys, their Int and Float arithmetic and its count, the
    sign of every zero included; a key whose square underflows fails."""
    pa = _engine()
    query, table = _pair(pa, tmp_path, GROUPED_PAIR)
    counts: dict[tuple[Any, Any], int] = {}
    for key in GROUPED_PAIR_ROWS:
        counts[key] = counts.get(key, 0) + 1
    expected = bag(
        [
            {
                "a": _bits(a),
                "x": _bits(x),
                "t": None if a is None else a * a,
                "f": None if x is None else _bits(x * x),
                "g": None if x is None else _bits(-x),
                "n": n,
            }
            for (a, x), n in counts.items()
        ]
    )
    rows = tuple((k, a, 0, x, 0.0) for k, (a, x) in enumerate(GROUPED_PAIR_ROWS))
    delivered, _ = run(pa, query, table(rows))
    assert bag([{k: _bits(v) for k, v in row.items()} for row in delivered]) == expected
    handle = _handle(pa, query, table(((1, 1, 0, 1e-200, 0.0),)))
    failure = _failed(handle).failure
    assert (failure.code, failure.detail) == ("PIE-R3003", "DUCKDB_FLOAT_UNDERFLOW")


def test_the_result_binding_refuses_a_value_that_fails_full_validation(
    projection_query: execution.CompiledQuery,
) -> None:
    """Step 4's defensive check: a result whose labels, types and nulls fit
    the compiled one but whose text is not valid UTF-8 is refused
    (DUCKDB_RESULT_CHECK, PIE-R3005 on the route); with valid text it binds."""
    pa = _pyarrow()
    facts = adapter.execution_facts(projection_query._template)
    ids = pa.array([1], pa.int64())
    valid = pa.record_batch({"id": ids, "note": pa.array(["a"], pa.string())})
    bound = reader.bind_duckdb_result(pa, valid, facts)
    assert bound.schema.equals(results.result_schema(pa, facts))
    assert type(bound) is pa.RecordBatch
    with pytest.raises(ResultError):
        reader.bind_duckdb_result(pa, pa.Table.from_batches([valid]), facts)
    invalid = pa.record_batch({"id": ids, "note": _invalid_utf8(pa)})
    with pytest.raises(ResultError) as refused:
        reader.bind_duckdb_result(pa, invalid, facts)
    assert refused.value.category == "DUCKDB_RESULT_CHECK"


def test_the_shared_binding_closes_the_duckdb_storage_kinds() -> None:
    """D77.32's wiring: the shared result binding holds one storage kind per
    admitted type, the contract's own spellings, and each has its Arrow
    type; PostgreSQL and MySQL keep theirs."""
    pa = _pyarrow()
    kinds = binding._storages("duckdb", False)
    assert binding._storages("duckdb", True) == kinds
    tags = ("Int", "Bool", "Text", "Float", "Date", "Timestamp", "Decimal")
    assert {tag: kind for tag, (kind,) in kinds.items()} == dict(
        zip(tags, duckdb_contract.STORAGES, strict=True)
    )
    decimal = {"Decimal": (12, 2)}
    assert [results.arrow_type(pa, tag, decimal.get(tag)) for tag in kinds] == [
        pa.int64(),
        pa.bool_(),
        pa.float64(),
        pa.string(),
        pa.decimal128(12, 2),
        pa.date32(),
        pa.timestamp("us"),
    ]
    assert not {kind for (kind,) in kinds.values()} & {
        kind
        for family in ("postgres", "mysql")
        for spelled in binding._storages(family, True).values()
        for kind in spelled
    }


# Each tier 2 type at both ends of its interval, NULL where the field admits
# it, and Decimals that differ in their last digit.
BIG = Decimal("9999999999999999999999999999.9999999999")
TYPED_ROWS = (
    (
        1,
        date(1000, 1, 1),
        datetime(1000, 1, 1),
        Decimal("-9999999999.99"),
        BIG.copy_negate(),
    ),
    (
        2,
        date(9999, 12, 31),
        datetime(9999, 12, 31, 23, 59, 59, 499999),
        Decimal("9999999999.99"),
        BIG,
    ),
    (
        3,
        None,
        datetime(2024, 1, 1, 10, 0, 0, 500000),
        Decimal("0.12"),
        Decimal("1E-10"),
    ),
    (4, date(2024, 1, 1), datetime(2024, 1, 1), None, Decimal("0E-10")),
    (
        5,
        date(2023, 12, 31),
        datetime(2023, 12, 31, 23, 59, 59, 999999),
        Decimal("0.13"),
        Decimal("-1E-10"),
    ),
)
TYPED_NAMES = ("id", "day", "at", "cost", "big")


def _typed_rows(selected: tuple[str, ...] = TYPED_NAMES) -> list[dict[str, Any]]:
    return [
        {name: row[TYPED_NAMES.index(name)] for name in selected} for row in TYPED_ROWS
    ]


def test_typed_fields_round_trip_their_civil_and_decimal_extremes(
    tmp_path: Path,
) -> None:
    """Each value reaches the caller unchanged, as date32, timestamp[us]
    without a time zone and decimal128(p, s), with its compiled nullability."""
    pa = _engine()
    body = "table result:\n    from orders\n    select:\n" + "".join(
        f"        {name}\n" for name in TYPED_NAMES
    )
    query = compiled(tmp_path / "p", body, typed=True)
    rows, handle = run(pa, query, events(pa, TYPED_ROWS))
    assert bag(rows) == bag(_typed_rows())
    assert pa.schema(handle) == pa.schema(
        [
            pa.field("id", pa.int64(), nullable=False),
            pa.field("day", pa.date32()),
            pa.field("at", pa.timestamp("us"), nullable=False),
            pa.field("cost", pa.decimal128(12, 2)),
            pa.field("big", pa.decimal128(38, 10), nullable=False),
        ]
    )


def _lt(a: Any, b: Any) -> bool:
    return a is not None and a < b


# Each `where` of one comparison or test and its oracle over a row's values;
# a NULL operand makes a comparison unknown, which keeps no row.
TYPED_WHERES = (
    (
        'day >= "2024-01-01"',
        lambda r: r["day"] is not None and r["day"] >= date(2024, 1, 1),
    ),
    ('"1000-01-01" == day', lambda r: r["day"] == date(1000, 1, 1)),
    (
        'at < "2024-01-01 10:00:00.5"',
        lambda r: r["at"] < datetime(2024, 1, 1, 10, 0, 0, 500000),
    ),
    (
        'at == "9999-12-31 23:59:59.499999"',
        lambda r: r["at"] == datetime(9999, 12, 31, 23, 59, 59, 499999),
    ),
    ("cost > 0.125", lambda r: r["cost"] is not None and r["cost"] > Decimal("0.125")),
    ("cost == 0.120", lambda r: r["cost"] == Decimal("0.12")),
    ("cost != 0.13", lambda r: r["cost"] is not None and r["cost"] != Decimal("0.13")),
    ("cost <= -9999999999.99", lambda r: _lt(r["cost"], Decimal("-9999999999.98"))),
    ("big > 0.0000000001", lambda r: r["big"] > Decimal("1E-10")),
    ("big >= 0.0000000001", lambda r: r["big"] >= Decimal("1E-10")),
    ("big < 9999999999999999999999999999.9999999999", lambda r: r["big"] < BIG),
    ("big > -1", lambda r: r["big"] > -1),
    ("day is None", lambda r: r["day"] is None),
    ("cost is not None", lambda r: r["cost"] is not None),
)


def test_typed_comparisons_with_literals_return_the_oracle_bag(
    tmp_path: Path,
) -> None:
    """A Date or Timestamp beside a Text literal of its civil spelling, and a
    Decimal beside the exact decimal that a number literal writes."""
    pa = _engine()
    table = events(pa, TYPED_ROWS)
    for position, (where, oracle) in enumerate(TYPED_WHERES):
        body = (
            f"table result:\n    from orders\n    where {where}\n"
            "    select:\n        id\n"
        )
        query = compiled(tmp_path / str(position), body, typed=True)
        rows, _ = run(pa, query, table)
        expected = [{"id": r["id"]} for r in _typed_rows() if oracle(r)]
        assert bag(rows) == bag(expected), where


def test_typed_groups_and_order_return_the_oracle(tmp_path: Path) -> None:
    """`count`, `min` and `max` of each type per `Date` group, NULL first in
    descending order as on the PostgreSQL emitter, and `min` and `max` of a
    `Date` and a `Timestamp` over all rows as date32 and timestamp[us]."""
    pa = _engine()
    body = (
        "table result:\n    from orders\n    group by day\n    select:\n"
        "        day\n        first = min(at)\n        low = min(cost)\n"
        "        top = max(big)\n        n = count(cost)\n"
        "    order by:\n        day desc\n"
    )
    query = compiled(tmp_path / "p", body, typed=True)
    rows, _ = run(pa, query, events(pa, TYPED_ROWS + TYPED_ROWS[2:3]))
    days = sorted(_typed_rows(), key=lambda r: (r["day"] is not None, r["day"]))
    assert [r["day"] for r in rows] == [None, *(r["day"] for r in days[::-1][:-1])]
    assert rows[0] == {
        "day": None,
        "first": datetime(2024, 1, 1, 10, 0, 0, 500000),
        "low": Decimal("0.12"),
        "top": Decimal("1E-10"),
        "n": 2,
    }
    assert rows[2] == {
        "day": date(2024, 1, 1),
        "first": datetime(2024, 1, 1),
        "low": None,
        "top": Decimal("0E-10"),
        "n": 0,
    }
    body = (
        "table result:\n    from orders\n    select:\n"
        "        lo = min(day)\n        hi = max(day)\n        last = max(at)\n"
    )
    query = compiled(tmp_path / "extremes", body, typed=True)
    rows, handle = run(pa, query, events(pa, TYPED_ROWS))
    days = [r["day"] for r in _typed_rows() if r["day"] is not None]
    last = max(r["at"] for r in _typed_rows())
    assert rows == [{"lo": min(days), "hi": max(days), "last": last}]
    assert pa.schema(handle) == pa.schema(
        [("lo", pa.date32()), ("hi", pa.date32()), ("last", pa.timestamp("us"))]
    )


def test_typed_parameters_bind_their_exact_values(tmp_path: Path) -> None:
    """A Date, Timestamp or Decimal(p, s) value of exactly its Python type
    and domain binds; a Decimal goes to DuckDB as its canonical text, so one
    of more than 38 digits (trailing zeros) still compares exactly."""
    pa = _engine()
    body = (
        "query result(since: Timestamp, on: Date, floor: Decimal(38, 10)):\n"
        "    from orders\n    where at >= since or day == on or big >= floor\n"
        "    select:\n        id\n"
    )
    query = compiled(tmp_path / "p", body, typed=True)
    edge = Decimal("9999999999999999999999999999.99999999990000")
    good = {"since": datetime(9999, 12, 31), "on": date(1000, 1, 1), "floor": edge}
    facts = adapter.execution_facts(query._template)
    assert route._bound(facts, None, good) == (
        datetime(9999, 12, 31),
        date(1000, 1, 1),
        str(BIG),
    )
    rows, _ = run(pa, query, events(pa, TYPED_ROWS), parameters=good)
    assert bag(rows) == bag([{"id": 1}, {"id": 2}])
    access = execution.DuckDBArrowInput("orders", object())
    for name, value, refusal in (
        ("since", date(2024, 1, 1), "0:Timestamp"),
        ("since", datetime(2024, 1, 1, tzinfo=timezone.utc), "0:Timestamp"),
        ("since", datetime(9999, 12, 31, 23, 59, 59, 500000), "0:Timestamp"),
        ("since", "2024-01-01 00:00:00", "0:Timestamp"),
        ("on", datetime(2024, 1, 1), "1:Date"),
        ("on", date(999, 12, 31), "1:Date"),
        ("floor", Decimal("0.00000000001"), "2:Decimal"),
        ("floor", Decimal("NaN"), "2:Decimal"),
        ("floor", 1.5, "2:Decimal"),
        ("floor", Decimal("99999999999999999999999999999.999999999"), "2:Decimal"),
    ):
        assert _refusal(query, access=access, parameters={**good, name: value}) == (
            "PIE-R1006",
            f"BINDING_PARAMETER:{refusal}",
        ), (name, value)


def _over(pa: Any, value: int, kind: Any) -> Any:
    """One decimal128 value of `kind` whose unscaled integer is `value`,
    which may have more digits than `kind`'s precision."""
    data = pa.py_buffer(value.to_bytes(16, "little", signed=True))
    return pa.Array.from_buffers(kind, 1, [None, data])


def test_the_capture_refuses_typed_columns_beyond_their_type_or_interval(
    tmp_path: Path,
) -> None:
    """Only date32, timestamp[us] without a time zone and decimal128 of the
    declared (p, s) are admitted, each inside its interval; every other type
    or value is refused before any session (DUCKDB_ARROW_SCHEMA)."""
    pa = _pyarrow()
    body = "table result:\n    from orders\n    select:\n        id\n"
    query = compiled(tmp_path / "p", body, typed=True)
    one = TYPED_ROWS[:1]
    day, at = pa.array([date(2024, 1, 1)]), pa.array([datetime(2024, 1, 1)])
    forged = {
        "timestamp_ns": {"at": at.cast(pa.timestamp("ns"))},
        "timestamp_ms": {"at": at.cast(pa.timestamp("ms"))},
        "timestamp_utc": {"at": at.cast(pa.timestamp("us", tz="UTC"))},
        "timestamp_null": {"at": pa.array([None], pa.timestamp("us"))},
        "date64": {"day": day.cast(pa.date64())},
        "date_text": {"day": pa.array(["2024-01-01"])},
        "decimal_precision": {"cost": pa.array([Decimal("1")], pa.decimal128(13, 2))},
        "decimal_scale": {"cost": pa.array([Decimal("1")], pa.decimal128(12, 3))},
        "decimal256": {"cost": pa.array([Decimal("1")], pa.decimal256(12, 2))},
        "decimal_float": {"cost": pa.array([1.0])},
        "date_before_1000": {"day": pa.array([date(999, 12, 31)], pa.date32())},
        "date_beyond_9999": {
            "day": pa.array([2_932_897], pa.int32()).cast(pa.date32())
        },
        "timestamp_past_the_civil_end": {
            "at": pa.array(
                [datetime(9999, 12, 31, 23, 59, 59, 500000)], pa.timestamp("us")
            )
        },
        "timestamp_before_1000": {
            "at": pa.array(
                [datetime(999, 12, 31, 23, 59, 59, 999999)], pa.timestamp("us")
            )
        },
        "decimal_beyond_its_precision": {
            "cost": _over(pa, 10**12, pa.decimal128(12, 2))
        },
        "decimal_below_its_precision": {
            "big": _over(pa, -(10**38), pa.decimal128(38, 10))
        },
    }
    for name, columns in forged.items():
        access = execution.DuckDBArrowInput("orders", events(pa, one, **columns))
        assert _refusal(query, access=access) == ("PIE-R1002", "DUCKDB_ARROW_SCHEMA"), (
            name
        )
    edges = {
        "cost": _over(pa, 10**12 - 1, pa.decimal128(12, 2)),
        "big": _over(pa, -(10**38) + 1, pa.decimal128(38, 10)),
    }
    _handle(pa, query, events(pa, one, **edges)).close()


def test_the_session_settings_are_the_spec_table_in_its_order() -> None:
    """D79.06: the route sets the spec's rows in table order (external access
    after `temp_directory`, the lock last) and reads back both lists."""
    assert route.SETTINGS == SESSION_TABLE
    assert route.UNCHANGED == SESSION_UNCHANGED
    assert route.READ_BACK == (
        *((name, value) for name, _set, value in SESSION_TABLE),
        *SESSION_UNCHANGED,
    )


def test_the_session_holds_every_spec_value_once_it_is_set_up(
    projection_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Read from the attempt's own connection after its setup: every row of
    both lists has the spec's value, the lock refuses a change, and a local
    file that a default connection reads cannot be read."""
    pa = _engine()
    duckdb = sys.modules["duckdb"]
    data = tmp_path / "data.csv"
    data.write_text("a\n1\n", encoding="utf-8")
    assert "'" not in str(data)
    read = f"SELECT a FROM read_csv('{data}')"
    default = duckdb.connect(":memory:")
    try:
        assert default.sql(read).fetchall() == [(1,)]
    finally:
        default.close()
    expected: dict[str, str | None] = {n: v for n, _set, v in SESSION_TABLE}
    expected.update(SESSION_UNCHANGED)
    _calls, hooks = _recorded(monkeypatch)
    handle = _handle(pa, projection_query)
    checked: list[bool] = []

    def check() -> None:
        # Before the statement: once its reader is open, the connection
        # takes no other query until the reader ends.
        connection = handle._owner._connection._connection
        settings = connection.sql("SELECT name, value FROM duckdb_settings()")
        observed = dict(settings.fetchall())
        assert {name: observed.get(name, "<absent>") for name in expected} == expected
        with pytest.raises(duckdb.InvalidInputException, match="locked"):
            connection.execute("SET threads = 2")
        with pytest.raises(duckdb.PermissionException):
            connection.sql(read).fetchall()
        checked.append(True)

    hooks["statement"] = check
    with handle as result:
        assert sum(pa.record_batch(batch).num_rows for batch in result) == len(ROWS)
    assert checked == [True]


SHADOW_CHILD = r"""
import json, sys
sys.path[:0] = json.loads(sys.argv[1])
import pyarrow as pa
from pietto import execution
query = execution.compile_query(sys.argv[2], module="main.pietto", kind="table",
    name="result", dialect="duckdb", emission_contract="contract.json")
table = pa.table({"id": pa.array([1], pa.int64()), "amount": pa.array([5], pa.int64()),
    "note": pa.array([None], pa.string()), "ok": [True], "price": [1.0]})
handle = execution.execute(query, route="duckdb_arrow",
    access=execution.DuckDBArrowInput("orders", table), premise=None)
seen = None
try:
    with handle as result:
        list(result)
except execution.AttemptFailed as error:
    seen = [error.code, error.detail]
loaded = sorted(n for n in sys.modules if n.partition(".")[0] in ("duckdb", "_duckdb"))
print(json.dumps({"seen": seen, "loaded": loaded}))
"""


def test_a_shadowed_or_unowned_duckdb_module_is_refused_before_any_session(
    projection_query: execution.CompiledQuery,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Step 1's origin checks of `_duckdb`: a copy that shadows it on the
    path is refused before anything is imported (in a fresh interpreter,
    where it is not loaded yet), and a loaded one that the pinned
    distribution does not own is refused before any connection."""
    pa = _engine()
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    (shadow / "_duckdb.py").write_text(
        'raise RuntimeError("the shadow ran")\n', encoding="utf-8"
    )
    root = write(tmp_path / "p", PROJECTION, contract())
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            SHADOW_CHILD,
            json.dumps([str(shadow), *sys.path]),
            str(root),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "seen": ["PIE-R2002", "EXECUTION_DRIVER_VERSION"],
        "loaded": [],
    }
    calls, _hooks = _recorded(monkeypatch)
    owners = route.owner_versions

    def unowned(distribution: str, module: Any) -> frozenset[str]:
        if getattr(module, "__name__", None) == "_duckdb":
            return frozenset()
        return owners(distribution, module)

    monkeypatch.setattr(route, "owner_versions", unowned)
    failure = _failed(_handle(pa, projection_query))
    assert (failure.code, failure.detail) == ("PIE-R2002", "EXECUTION_DRIVER_VERSION")
    assert calls == []


class _FailingClose:
    """A connection or reader whose close closes it, then raises."""

    def __init__(self, wrapped: Any) -> None:
        self._wrapped = wrapped

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)

    def close(self) -> None:
        self._wrapped.close()
        raise RuntimeError("close failed")


@pytest.mark.parametrize("step", ["close", "reader"])
def test_a_failed_close_is_a_finalization_failure(
    projection_query: execution.CompiledQuery,
    monkeypatch: pytest.MonkeyPatch,
    step: str,
) -> None:
    """A failed close of the connection, or of the reader, which step 5
    closes first, is PIE-R3006 with its step; the later steps still run."""
    pa = _engine()
    calls, _hooks = _recorded(monkeypatch)
    handle = _handle(pa, projection_query)
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle as result:
            owner = handle._owner
            if step == "reader":
                owner._reader = _FailingClose(owner._reader)
            else:
                owner._connection = _FailingClose(owner._connection)
            list(result)
    failure = failed.value
    outcome = handle.outcome
    assert (failure.code, outcome.end, outcome.cleanup) == (
        "PIE-R3006",
        "FAILED",
        "FAILED",
    )
    assert [(f.code, f.phase, f.cause) for f in outcome.cleanup_failures] == [
        ("PIE-R5001", step, "RuntimeError")
    ]
    assert calls == [*OPENED, *ENDED]


def test_other_entry_points_refuse_a_duckdb_query(
    filtered_query: execution.CompiledQuery, tmp_path: Path
) -> None:
    """No bundle, saved result, recovery, relay or job: each refuses before it
    builds or opens anything (the workspace below does not exist)."""
    query = filtered_query
    with pytest.raises(execution.RequestRejected) as refused:
        execution.export_bundle(query)
    assert (refused.value.code, refused.value.detail) == (
        "PIE-R1004",
        "DUCKDB_BUNDLE_ENTRY",
    )
    workspace = execution.WorkspaceRef(str(tmp_path / "absent"), "ws-" + "0" * 32)
    common: dict[str, Any] = {
        "operation": execution.new_operation(),
        "access": execution.DuckDBArrowInput("orders", object()),
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
        for selected in ("duckdb_arrow", "postgres_rows"):
            with pytest.raises(execution.RequestRejected) as refused:
                call(route=selected, **common)
            assert (refused.value.code, refused.value.detail) == (
                "PIE-R1003",
                "PUBLIC_ROUTE_UNAVAILABLE",
            ), (name, selected)
    assert not (tmp_path / "absent").exists() and not (tmp_path / "sink").exists()


def test_the_existing_routes_keep_their_premises_and_refusals(tmp_path: Path) -> None:
    """`premise=None` is accepted on `duckdb_arrow` only."""
    query = execution.compile_query(
        api.write_example(tmp_path / "example"),
        module="main.pietto",
        kind="table",
        name="active_items",
        dialect="postgres",
        emission_contract="contract.json",
    )
    pg = execution.PostgresAccess("127.0.0.1", 5432, "d", "u", "p")
    duck = execution.DuckDBArrowInput("items", object())
    for selected, access, premise, expected in (
        ("postgres_rows", pg, None, ("PIE-R1001", "PUBLIC_PREMISE_REQUIRED")),
        ("postgres_adbc", pg, None, ("PIE-R1001", "PUBLIC_PREMISE_REQUIRED")),
        ("postgres_rows", duck, None, ("PIE-R1002", "PUBLIC_ACCESS_TYPE")),
        ("duckdb_arrow", duck, None, ("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE")),
        ("mysql_rows", duck, None, ("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE")),
    ):
        assert (
            _refusal(query, route=selected, access=access, premise=premise) == expected
        )
