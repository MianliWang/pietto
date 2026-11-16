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
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import _pietto_execution_api as api
from _pietto_execution_duckdb import (
    ROWS,
    bag,
    compiled,
    orders,
    projection,
    run,
)
from _pietto_sql_duckdb import GROUPED, ORDERED, PROJECTION, contract, filtered, write

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
# The spec's session table ("Session and attempt", D79.06) in its order: the
# setting, the value set and the value read back.
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
    ("memory_limit", "'256MiB'", "256.0 MiB"),
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
    ("worker_threads", "1"),
    ("max_memory", "256.0 MiB"),
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


def test_the_limits_count_the_whole_table_before_the_schema(
    filtered_query: execution.CompiledQuery,
) -> None:
    """65,536 rows and 16 MiB of `Table.nbytes` are admitted, one more of
    either is not; an unselected column counts but is never examined."""
    pa = _pyarrow()
    query = filtered_query
    rows = ((1, 5, None, True, 0.0),) * route.MAX_ROWS
    full = orders(pa, rows)
    _handle(pa, query, full, parameters={"min_amount": 1}).close()
    over = orders(pa, rows + rows[:1]).drop_columns(["ok"])
    access = execution.DuckDBArrowInput("orders", over)
    limit = ("PIE-R1002", "DUCKDB_ARROW_CAPTURE_LIMIT")
    assert _refusal(query, access=access, parameters={"min_amount": 1}) == limit
    small = orders(pa, rows[:1])
    empty = small.append_column("pad", pa.array([b""], pa.binary()))
    pad = route.MAX_BYTES - empty.nbytes
    exact = small.append_column("pad", pa.array([b"x" * pad], pa.binary()))
    assert exact.nbytes == route.MAX_BYTES
    _handle(pa, query, exact, parameters={"min_amount": 1}).close()
    above = small.append_column("pad", pa.array([b"x" * (pad + 1)], pa.binary()))
    access = execution.DuckDBArrowInput("orders", above)
    assert _refusal(query, access=access, parameters={"min_amount": 1}) == limit


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
    owned = handle._owner._capture
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
    assert handle._owner._capture.column(2).to_pylist() == list(NUL_NOTES)
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
    """`to_arrow_table()` marks every field nullable; the route restores the
    compiled nullability, and `pyarrow.schema(handle)` needs no I/O. Success
    and a refused batch each unregister the capture and close the session."""
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
        assert calls == [*OPENED, *ENDED]


def test_close_and_cancel_before_and_after_the_session_opens(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before the session opens, neither connects; after, an early close and
    a consumer's exception each unregister the capture and close."""
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
    assert handle._owner._connection is None and handle._owner._capture is None
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
    in its query step with no batch and no interrupt; the whole result was
    already read, so its transaction is COMMIT_ACK."""
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
    ) == ("PIE-R3001", "query", "DEADLINE", "COMMIT_ACK")
    assert not handle.outcome.cancel_sent and handle._owner._batches is None
    assert calls == [*OPENED, *ENDED]


def test_a_cancel_after_the_result_was_read_stops_before_the_result(
    projection_query: execution.CompiledQuery, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cancel that arrives at the check after the statement, once the
    statement has ended: nothing is interrupted, the attempt ends with no
    batch and, as any cancellation, no phase; the whole result was already
    read, so its transaction is COMMIT_ACK."""
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
    assert owner._batches is None and calls == [*OPENED, *ENDED]


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
    result that does not fit the compiled one is PIE-R3005. Each unregisters
    the capture and closes the session."""
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
        assert handle.outcome.transaction == (
            "UNKNOWN" if phase == "query" else "COMMIT_ACK"
        )
        assert calls == [*OPENED, *ENDED]


def test_the_result_binding_refuses_a_value_that_fails_full_validation(
    projection_query: execution.CompiledQuery,
) -> None:
    """Step 4's defensive check: a result whose labels, types and nulls fit
    the compiled one but whose text is not valid UTF-8 is refused
    (DUCKDB_RESULT_CHECK, PIE-R3005 on the route); with valid text it binds."""
    pa = _pyarrow()
    facts = adapter.execution_facts(projection_query._template)
    ids = pa.array([1], pa.int64())
    valid = pa.table({"id": ids, "note": pa.array(["a"], pa.string())})
    bound = reader.bind_duckdb_result(pa, valid, facts)
    assert bound.schema.equals(results.result_schema(pa, facts))
    invalid = pa.table({"id": ids, "note": _invalid_utf8(pa)})
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
    assert {tag: kind for tag, (kind,) in kinds.items()} == dict(
        zip(("Int", "Bool", "Text", "Float"), duckdb_contract.STORAGES, strict=True)
    )
    assert [results.arrow_type(pa, tag) for tag in kinds] == [
        pa.int64(),
        pa.bool_(),
        pa.float64(),
        pa.string(),
    ]
    assert not {kind for (kind,) in kinds.values()} & {
        kind
        for family in ("postgres", "mysql")
        for spelled in binding._storages(family, True).values()
        for kind in spelled
    }


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
    projection_query: execution.CompiledQuery, tmp_path: Path
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
    handle = _handle(pa, projection_query)
    with handle as result:
        connection = handle._owner._connection
        settings = connection.sql("SELECT name, value FROM duckdb_settings()")
        observed = dict(settings.fetchall())
        assert {name: observed.get(name, "<absent>") for name in expected} == expected
        with pytest.raises(duckdb.InvalidInputException, match="locked"):
            connection.execute("SET threads = 2")
        with pytest.raises(duckdb.PermissionException):
            connection.sql(read).fetchall()
        assert sum(pa.record_batch(batch).num_rows for batch in result) == len(ROWS)


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
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def unregister(self, name: str) -> None:
        self._connection.unregister(name)

    def close(self) -> None:
        self._connection.close()
        raise RuntimeError("close failed")


def test_a_failed_close_is_a_finalization_failure(
    projection_query: execution.CompiledQuery,
) -> None:
    pa = _engine()
    query = projection_query
    handle = _handle(pa, query)
    with pytest.raises(execution.AttemptFailed) as failed:
        with handle as result:
            owner = handle._owner
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
        ("PIE-R5001", "close", "RuntimeError")
    ]


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
