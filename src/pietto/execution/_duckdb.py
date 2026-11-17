"""The ``duckdb_arrow`` route (docs/spec/duckdb-arrow-route-v1.md; D79.03,
D79.04 as PL.47 and D79.19 revise it, D79.06, D79.24 and AD79.01): request
checks 7 to 13 of execute(), the owned
capture of the caller's tables, and one attempt's private in-memory
session.

Importing this module loads no DuckDB and no PyArrow. Checks 7 to 11 import
nothing; check 12 verifies the PyArrow the caller already loaded (and the
``pyarrow.compute`` of that distribution, which the capture uses); only an
opening attempt imports the pinned duckdb. The attempt depends only
downward: it runs the adapter's verified statement and never reads source
syntax, reselects a target or infers a schema.
"""

from __future__ import annotations

import importlib
import sys
import threading
import time
import uuid
from typing import Any

from pietto._project import project_duckdb_emission as adapter
from pietto._project import project_duckdb_result as results
from pietto._project import project_execution as ex
from pietto._project.project_compiled_loading import (
    owner_versions,
    supported_compatibility,
)
from pietto._project.project_duckdb_sql import relation
from pietto._project.project_execution_template import BindingError
from pietto._project.project_result_contract import ResultError
from pietto._project.project_sql_emission_parameters import (
    parameter_text,
    parameter_valid,
)
from pietto.execution._errors import failure, request_failure

__all__: tuple[str, ...] = ()

PYARROW = ("pyarrow", "26.0.1", "pyarrow")
DRIVER = ("duckdb", "2.0.0", "duckdb")
ENGINE = [("v2.0.0", "d54cbbe3df")]
# Of each input (D79.19).
MAX_ROWS = 1_048_576
# The civil interval of a `Date` in days and of a `Timestamp` in microseconds
# from the Unix epoch (1000-01-01 to 9999-12-31 23:59:59.499999).
CIVIL_DAYS = (-354_285, 2_932_896)
CIVIL_MICROSECONDS = (-30_610_224_000_000_000, 253_402_300_799_499_999)
# Of the selected columns of all inputs together (PL.47, D79.19).
MAX_BYTES = 256 * 1024 * 1024
# DuckDB drops an interrupt that reaches the connection before its statement
# starts, so a sent cancellation is sent again at this interval until the
# statement ends.
RESEND_SECONDS = 0.05

# Check 12 (the owner's choice of 2026-11-11): the codes of the other Arrow
# routes, with this route's own details, raised from execute() as
# RequestRejected. A PyArrow whose distribution is not installed is
# PIE-R2001; one of another version, not that distribution's own files or
# that cannot be loaded is PIE-R2002.
PYARROW_REFUSALS = {
    "EXECUTION_DEPENDENCY_MISSING": ("PIE-R2001", "ARROW_DEPENDENCY_MISSING"),
    "ARROW_DEPENDENCY_VERSION": ("PIE-R2002", "ARROW_DEPENDENCY_VERSION"),
}

# D79.06, set with SET in this order, then read back: (name, value, read back).
SETTINGS = (
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
# Read back too, at their 2.0.0 values, which no setting above may change.
UNCHANGED = (
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
    # Text compares in code point order under it; the SQL writes no COLLATE.
    ("default_collation", ""),
    ("worker_threads", "1"),
    ("max_memory", "1.0 GiB"),
)
READ_BACK = (*((name, value) for name, _set, value in SETTINGS), *UNCHANGED)
_ABSENT = object()


def _bound(facts, values, parameters):
    """Check 7's binding: no value slots, and exactly the declared header
    parameters, each of its exact type (BINDING_* words, PIE-R1006), before
    any reaches DuckDB, whose cast would take ``1.5`` as the BIGINT 2. The
    arguments come in placeholder order, a `Decimal` as its canonical text,
    which DuckDB casts exactly, where it reads a `decimal.Decimal` of more
    than 38 digits as a DOUBLE."""
    if values is not None and len(values) != 0:
        raise BindingError("BINDING_SLOTS")
    supplied = {} if parameters is None else parameters
    if set(supplied) != {parameter[0] for parameter in facts.parameters}:
        raise BindingError("BINDING_PARAMETERS")
    arguments = []
    for ordinal, (name, tag, nullable, decimal) in enumerate(facts.parameters):
        value = supplied[name]
        if not (
            nullable
            if value is None
            else parameter_valid(tag, value, adapter.FAMILY, decimal)
        ):
            raise BindingError(f"BINDING_PARAMETER:{ordinal}:{tag}")
        arguments.append(
            parameter_text(tag, value)
            if tag == "Decimal" and value is not None
            else value
        )
    return tuple(arguments[k] for k in facts.placeholders)


def _owned(name):
    """A loaded module of the pinned PyArrow distribution, or the version
    refusal; ``name`` is imported only when it is not loaded yet."""
    module = sys.modules.get(name)
    if module is None:
        module = importlib.import_module(name)
    if owner_versions(PYARROW[0], module) != {PYARROW[1]}:
        raise ex.ExecutionError("ARROW_DEPENDENCY_VERSION")
    return module


def _pyarrow():
    """Check 12: the (pyarrow, pyarrow.compute) modules of the pinned
    distribution, or the (code, detail) of its refusal."""
    try:
        (pa,) = ex.pinned_modules((PYARROW,), "ARROW_DEPENDENCY_VERSION")
        for name in ("pyarrow.lib", "pyarrow.compute", "pyarrow._compute"):
            _owned(name)
        return (pa, sys.modules["pyarrow.compute"]), None
    except ex.ExecutionError as error:
        word = error.args[0] if error.args else ""
    except Exception:
        # A PyArrow that cannot be loaded is not the pinned one either.
        word = ""
    return None, PYARROW_REFUSALS.get(
        word, PYARROW_REFUSALS["ARROW_DEPENDENCY_VERSION"]
    )


def _admitted(pa, pc, field, column):
    """Step 4 of the capture over one selected column."""
    try:
        column.validate(full=True)
    except Exception:
        return False
    if not field.nullable and column.null_count:
        return False
    if field.tag == "Int":
        low, high = field.bounds
        extremes = pc.min_max(column).as_py()
        return (
            extremes["min"] is None or low <= extremes["min"] <= extremes["max"] <= high
        )
    if field.tag == "Float":
        return pc.any(pc.invert(pc.is_finite(column))).as_py() is not True
    if field.tag == "Text":
        # A NUL is one code point like any other: it reaches DuckDB and the
        # caller unchanged (the owner's choice of 2026-11-11).
        longest = pc.max(pc.utf8_length(column)).as_py()
        return longest is None or longest <= field.max_characters
    if field.tag in ("Date", "Timestamp"):
        low, high = CIVIL_DAYS if field.tag == "Date" else CIVIL_MICROSECONDS
        width = pa.int32() if field.tag == "Date" else pa.int64()
        extremes = pc.min_max(column.cast(width)).as_py()
        return (
            extremes["min"] is None or low <= extremes["min"] <= extremes["max"] <= high
        )
    # A Decimal's digits beyond its precision fail the full validation above.
    return True


def _ranges(arrays):
    return [
        (buffer.address, buffer.address + buffer.size)
        for array in arrays
        for buffer in array.buffers()
        if buffer is not None and buffer.size
    ]


def _copy(pa, column):
    """Step 5 for one column: a new array of its referenced values only,
    whose buffers are disjoint from the caller's."""
    chunks = column.chunks
    copy = pa.concat_arrays(chunks) if chunks else pa.array([], type=column.type)
    caller = _ranges(chunks)
    if any(
        lo < end and start < hi for start, end in _ranges([copy]) for lo, hi in caller
    ):
        raise ex.ExecutionError("DUCKDB_ARROW_CAPTURE_COPY")
    return copy


def _unique(pa, pc, columns, fields):
    """D79.24 over the owned copies of one declared key's columns: no two
    rows are equal under Pietto's ``==``, where a ``Float`` ``-0.0`` equals
    ``0.0`` and ``Text`` compares by code point; a row with a NULL in the
    key is left out (NULLS_DISTINCT)."""
    arrays = [
        pc.if_else(pc.equal(column, 0.0), 0.0, column)
        if field.tag == "Float"
        else column
        for column, field in zip(columns, fields, strict=True)
    ]
    names = [f"k{k}" for k in range(len(arrays))]
    table = pa.Table.from_arrays(arrays, names=names).drop_null()
    if table.num_rows < 2:
        return True
    table = table.take(pc.sort_indices(table, [(name, "ascending") for name in names]))
    same = None
    for column in table.columns:
        equal = pc.equal(column.slice(1), column.slice(0, table.num_rows - 1))
        same = equal if same is None else pc.and_(same, equal)
    return pc.any(same).as_py() is not True


def capture(pa, pc, tables, sources):
    """Check 13 (the spec's "Capture"): each source's owned copy of its
    selected columns, in FROM and JOIN order, named on from c0 across the
    sources, or the refusal's detail. ``tables`` maps each input's name to
    its table; sources that share a name share its input, whose columns are
    checked against each and copied once."""
    if any(table.num_rows > MAX_ROWS for table in tables.values()):
        return None, "DUCKDB_ARROW_CAPTURE_LIMIT"
    selected = {}
    for source in sources:
        schema = tables[source.key].schema
        for field in source.fields:
            found = schema.get_all_field_indices(field.column)
            expected = results.arrow_type(pa, field.tag, field.decimal)
            if len(found) != 1:
                return None, "DUCKDB_ARROW_SCHEMA"
            actual = schema.field(found[0]).type
            if type(actual) is not type(expected) or not actual.equals(expected):
                return None, "DUCKDB_ARROW_SCHEMA"
            place = (source.key, field.column)
            selected.setdefault(place, tables[source.key].column(found[0]))
    if sum(column.nbytes for column in selected.values()) > MAX_BYTES:
        return None, "DUCKDB_ARROW_CAPTURE_LIMIT"
    for source in sources:
        for field in source.fields:
            if not _admitted(pa, pc, field, selected[source.key, field.column]):
                return None, "DUCKDB_ARROW_SCHEMA"
    copies = {place: _copy(pa, column) for place, column in selected.items()}
    owned = []
    for source in sources:
        columns = [copies[source.key, field.column] for field in source.fields]
        for key in source.unique:
            keyed = [columns[k] for k in key]
            if not _unique(pa, pc, keyed, [source.fields[k] for k in key]):
                return None, "DUCKDB_ARROW_SCHEMA"
        start = sum(len(item.fields) for item in sources[: len(owned)])
        names = [f"c{start + k}" for k in range(len(columns))]
        owned.append(pa.Table.from_arrays(columns, names=names))
    return tuple(owned), None


def prepare(template, access, *, limits, isolation, values, parameters):
    """Checks 7 to 13, in order, after execute()'s shared checks 1 to 6:
    (an unopened attempt, None) or (None, the first refusal's Failure).
    ``access`` is one DuckDBArrowInput or a tuple of them."""
    try:
        facts = adapter.execution_facts(template)
        arguments = _bound(facts, values, parameters)
        if template.compatibility != supported_compatibility():
            raise BindingError("COMPILED_COMPATIBILITY")
    except Exception as caught:
        return None, request_failure(caught, preparing=True)
    lib = sys.modules.get("pyarrow.lib")
    inputs = access if type(access) is tuple else (access,)
    if any(
        type(item.name) is not str
        or not item.name
        or lib is None
        or type(item.table) is not getattr(lib, "Table", None)
        for item in inputs
    ):
        return None, failure("PIE-R1002", "EXECUTION_ACCESS")
    # One input per relation name that the statement reads, matched by name.
    names = [item.name for item in inputs]
    if len(set(names)) != len(names) or set(names) != {
        source.key for source in facts.sources
    }:
        return None, failure("PIE-R1002", "DUCKDB_ARROW_SCHEMA")
    if type(isolation) is not str or isolation != "stable":
        return None, failure("PIE-R1002", "EXECUTION_ISOLATION")
    try:
        ex.verify_execution_limits(limits)
    except Exception as caught:
        return None, request_failure(caught, preparing=True)
    modules, refused = _pyarrow()
    if refused is not None or modules is None:
        code, detail = refused or PYARROW_REFUSALS["ARROW_DEPENDENCY_VERSION"]
        return None, failure(code, detail)
    pa, pc = modules
    try:
        tables = {item.name: item.table for item in inputs}
        owned, detail = capture(pa, pc, tables, facts.sources)
    except Exception as caught:
        return None, request_failure(caught, preparing=True)
    if detail is not None:
        return None, failure("PIE-R1002", detail)
    return DuckDBAttempt(pa, facts, owned, arguments, limits), None


def _driver():
    """Step 1's distribution check: the installed duckdb 2.0.0 owns the
    imported duckdb and _duckdb modules (PIE-R2001, PIE-R2002)."""
    pins = (DRIVER,)
    origins = (("duckdb", DRIVER[1], "_duckdb"),)
    (duckdb,) = ex.pinned_modules(
        pins, "EXECUTION_DRIVER_VERSION", required_origins=origins
    )
    if owner_versions(DRIVER[0], sys.modules.get("_duckdb")) != {DRIVER[1]}:
        raise ex.ExecutionError("EXECUTION_DRIVER_VERSION")
    return duckdb


class DuckDBAttempt:
    """One attempt: its own ``:memory:`` session, opened when the handle is
    first entered, running the one compiled statement over the capture. It
    has the private owner surface ResultHandle reads; nothing is pooled,
    cached or reused."""

    def __init__(self, pa, facts, capture, arguments, limits):
        self._pa = pa
        self.facts = facts
        self._capture = capture
        self._arguments = arguments
        self.limits = limits
        self._sql = facts.sql
        self.attempt = uuid.uuid4().hex
        self._gate = threading.RLock()
        self._driver: Any = None
        self._connection: Any = None
        self._registered = 0
        self._running = False
        self._ended = threading.Event()
        self._timer: Any = None
        self._reader: Any = None
        self._batches: Any = None
        self._started: Any = None
        self._closed = self._finalizing = False
        self._source = self._transaction = self._delivery = self._cleanup = (
            "NOT_STARTED"
        )
        self._primary: Any = None
        self._cleanup_errors: list[Any] = []
        self._terminal: Any = None
        self.deadline_expired = False
        self._cancel_requested = self._cancel_sent = self._cancel_observed = False
        self.session_id: Any = None

    def schema(self):
        """The schema of every batch, from the compiled result; no I/O."""
        from pietto._project import project_arrow_result as arrow

        return results.result_schema(arrow.pinned(), self.facts)

    def _claim_terminal(self, terminal):
        with self._gate:
            if self._terminal is not None or self._closed or self._finalizing:
                return False
            self._terminal = terminal
            return True

    def _checkpoint(self):
        if self._cancel_requested and not self.deadline_expired:
            raise ex.ExecutionError("EXECUTION_CANCELED")
        if (
            self.deadline_expired
            or time.monotonic() - self._started >= self.limits.seconds
        ):
            self.cancel(deadline=True)
            self.deadline_expired = True
            raise TimeoutError("EXECUTION_DEADLINE")

    def _session(self, duckdb):
        """Steps 1 (the engine's own profile) and 2, then the registration of
        each source's capture: any failure is DUCKDB_DRIVER_PROFILE or
        DUCKDB_SESSION_CONTEXT."""
        try:
            connection = duckdb.connect(":memory:")
        except Exception:
            raise ex.ExecutionError("DUCKDB_SESSION_CONTEXT") from None
        with self._gate:
            self._connection = connection
        try:
            profile = connection.sql(
                "SELECT library_version, source_id FROM pragma_version()"
            ).fetchall()
        except Exception:
            raise ex.ExecutionError("DUCKDB_SESSION_CONTEXT") from None
        if profile != ENGINE:
            raise ex.ExecutionError("DUCKDB_DRIVER_PROFILE")
        try:
            for name, value, _read in SETTINGS:
                connection.execute(f"SET {name} = {value}")
            observed = dict(
                connection.sql("SELECT name, value FROM duckdb_settings()").fetchall()
            )
        except Exception:
            raise ex.ExecutionError("DUCKDB_SESSION_CONTEXT") from None
        if any(observed.get(name, _ABSENT) != value for name, value in READ_BACK):
            raise ex.ExecutionError("DUCKDB_SESSION_CONTEXT")
        for position, table in enumerate(self._capture or ()):
            try:
                connection.register(relation(position), table)
            except Exception:
                raise ex.ExecutionError("DUCKDB_SESSION_CONTEXT") from None
            self._registered += 1

    def open(self):
        if self._started is not None or self._closed:
            raise ex.ExecutionError("EXECUTION_REUSE")
        self._started = time.monotonic()
        phase = "driver"
        try:
            self._checkpoint()
            self._driver = _driver()
            phase = "session"
            timer = threading.Timer(
                max(0.0, self.limits.seconds - (time.monotonic() - self._started)),
                self.cancel,
                kwargs={"deadline": True},
            )
            timer.daemon = True
            with self._gate:
                self._timer = timer
            timer.start()
            self._session(self._driver)
            self.session_id = self.attempt
            phase = "query"
            with self._gate:
                self._checkpoint()
                self._running = True
                self._transaction = "UNKNOWN"
            relation = (
                self._connection.sql(self._sql, params=list(self._arguments))
                if self._arguments
                else self._connection.sql(self._sql)
            )
            # The statement runs until its reader ends or is closed. A sort or
            # a grouping consumes its input here and a JOIN builds its hash
            # table; the probe and the projection run as batches are read.
            reader = relation.to_arrow_reader(self.limits.batch_rows)
            with self._gate:
                self._reader = reader
            self._checkpoint()
            self._batches = results.DuckDBBatches(self._pa, None, self.limits)
            self._delivery = "OPEN"
            return self
        except BaseException as error:
            self._failed(error, phase)
            raise

    def _read(self):
        """The reader's next batch that has rows, or None at its end, when
        the statement's auto-commit transaction has ended."""
        while True:
            try:
                batch = self._reader.read_next_batch()
            except StopIteration:
                with self._gate:
                    self._running = False
                    self._ended.set()
                self._transaction = "COMMIT_ACK"
                return None
            if batch.num_rows:
                return batch

    def __enter__(self):
        return self.open()

    def __iter__(self):
        return self

    def __next__(self):
        if self._closed:
            raise StopIteration
        if self._started is None:
            self.open()
        phase = "query"
        try:
            self._checkpoint()
            batch = self._read()
            if batch is not None:
                phase = "result"
                from pietto._project import project_execution_reader as reader

                if batch.num_rows > self.limits.batch_rows:
                    raise ResultError("DUCKDB_RESULT_CHECK")
                bound = reader.bind_duckdb_result(self._pa, batch, self.facts)
                phase = "delivery"
                return self._batches.deliver(bound)
            self._checkpoint()
            if not self._claim_terminal("COMPLETE"):
                raise ex.ExecutionError("EXECUTION_CANCELED")
            self._source, self._delivery = "EOF", "COMPLETE"
            phase = "finalization"
            self._finish()
            if self._primary is not None or self._cleanup_errors:
                raise ex.ExecutionError("EXECUTION_FINALIZATION")
            raise StopIteration
        except StopIteration:
            raise
        except BaseException as error:
            self._failed(error, phase)
            raise

    def _failed(self, error, phase):
        self._claim_terminal("FAILED")
        if self._primary is None:
            self._primary = ex.ExecutionFailure(phase, type(error).__name__)
        interrupted = getattr(self._driver, "InterruptException", None)
        # A batch read raises every DuckDB error as OSError, an interrupt too.
        if self._cancel_sent and (
            (isinstance(interrupted, type) and isinstance(error, interrupted))
            or (type(error) is OSError and phase == "query")
        ):
            self._cancel_observed = True
        if self._source != "EOF":
            self._source = "INCOMPLETE"
        self._delivery = "FAILED"
        self._finish()

    def cancel(self, *, deadline=False):
        with self._gate:
            if self._terminal is not None or self._closed or self._finalizing:
                return {
                    "requested": False,
                    "sent": False,
                    "observed": False,
                    "late": True,
                }
            self._terminal = "DEADLINE" if deadline else "CANCELLED"
            self.deadline_expired = deadline
            self._cancel_requested = True
            if self._running and self._connection is not None:
                # Stops the running statement (InterruptException on 2.0.0).
                self._connection.interrupt()
                self._cancel_sent = True
                threading.Thread(target=self._resend, daemon=True).start()
            return {
                "requested": True,
                "sent": self._cancel_sent,
                "observed": self._cancel_observed,
                "late": False,
            }

    def _resend(self):
        """The sent interrupt again, every RESEND_SECONDS while the statement
        runs and the attempt is not finalizing, so one that reached the
        connection before the statement started is not lost; it stops when
        the statement ends."""
        while not self._ended.wait(RESEND_SECONDS):
            with self._gate:
                if not self._running or self._finalizing or self._closed:
                    return
                self._connection.interrupt()

    def _finish(self):
        """Step 5: close an open reader, unregister each registered capture,
        then close, whatever ended the attempt; a reader outlives its
        connection."""
        with self._gate:
            if self._closed or self._finalizing:
                return
            self._finalizing = True
            self._running = False
            self._ended.set()
            timer, connection, reader = self._timer, self._connection, self._reader
        if timer is not None:
            timer.cancel()
        if reader is not None:
            try:
                reader.close()
            except BaseException as error:
                self._cleanup_errors.append(
                    ex.ExecutionFailure("reader", type(error).__name__)
                )
        if connection is not None:
            for position in range(self._registered):
                try:
                    connection.unregister(relation(position))
                except BaseException as error:
                    self._cleanup_errors.append(
                        ex.ExecutionFailure("unregister", type(error).__name__)
                    )
            try:
                connection.close()
            except BaseException as error:
                self._cleanup_errors.append(
                    ex.ExecutionFailure("close", type(error).__name__)
                )
        with self._gate:
            self._connection = self._capture = self._reader = None
            self._registered = 0
            self._closed = True
            self._finalizing = False
            self._cleanup = (
                "FAILED" if self._cleanup_errors else "LOCAL_CLOSED_REMOTE_UNOBSERVED"
            )

    def close(self):
        if not self._closed:
            won = self._claim_terminal("STOPPED_EARLY")
            if not won and self._terminal != "STOPPED_EARLY":
                self._finish()
                return
            if self._source != "EOF":
                self._source = "EARLY_CLOSE"
            if self._delivery not in ("FAILED", "COMPLETE"):
                self._delivery = "INCOMPLETE"
            self._finish()

    def __exit__(self, kind, error, traceback):
        if error is not None and self._primary is None:
            self._primary = ex.ExecutionFailure("consumer", type(error).__name__)
            self._delivery = "FAILED"
        self.close()
        return False

    @property
    def outcome(self):
        batches = self._batches
        return ex.ExecutionOutcome(
            self.attempt,
            self._source,
            self._transaction,
            self._delivery,
            self._cleanup,
            0 if batches is None else batches.rows,
            0 if batches is None else batches.batches,
            0 if batches is None else batches.bytes,
            self._primary,
            tuple(self._cleanup_errors),
            self._cancel_requested,
            self._cancel_sent,
            self._cancel_observed,
        )
