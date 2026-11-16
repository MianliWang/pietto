"""The ``duckdb_arrow`` route (docs/spec/duckdb-arrow-route-v1.md; D79.03,
D79.04 as PL.47 revises it, D79.06 and AD79.01): request checks 7 to 13 of
execute(), the owned capture of the caller's table, and one attempt's
private in-memory session.

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
from pietto._project.project_duckdb_sql import RELATION
from pietto._project.project_execution_template import BindingError
from pietto._project.project_sql_emission_parameters import parameter_valid
from pietto.execution._errors import failure, request_failure

__all__: tuple[str, ...] = ()

PYARROW = ("pyarrow", "26.0.1", "pyarrow")
DRIVER = ("duckdb", "2.0.0", "duckdb")
ENGINE = [("v2.0.0", "d54cbbe3df")]
MAX_ROWS = 1_048_576
# Of the selected columns only (PL.47).
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
    arguments come in placeholder order."""
    if values is not None and len(values) != 0:
        raise BindingError("BINDING_SLOTS")
    supplied = {} if parameters is None else parameters
    if set(supplied) != {name for name, _tag, _nullable in facts.parameters}:
        raise BindingError("BINDING_PARAMETERS")
    arguments = []
    for ordinal, (name, tag, nullable) in enumerate(facts.parameters):
        value = supplied[name]
        if not (
            nullable if value is None else parameter_valid(tag, value, adapter.FAMILY)
        ):
            raise BindingError(f"BINDING_PARAMETER:{ordinal}:{tag}")
        arguments.append(value)
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


def _admitted(pc, field, column):
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


def capture(pa, pc, table, fields):
    """Check 13 (the spec's "Capture"): the owned copy of the selected
    columns named c0, c1, ... in shape order, or the refusal's detail."""
    if table.num_rows > MAX_ROWS:
        return None, "DUCKDB_ARROW_CAPTURE_LIMIT"
    schema = table.schema
    selected = []
    for field in fields:
        found = schema.get_all_field_indices(field.column)
        expected = results.arrow_type(pa, field.tag)
        if len(found) != 1:
            return None, "DUCKDB_ARROW_SCHEMA"
        actual = schema.field(found[0]).type
        if type(actual) is not type(expected) or not actual.equals(expected):
            return None, "DUCKDB_ARROW_SCHEMA"
        selected.append(table.column(found[0]))
    if sum(column.nbytes for column in selected) > MAX_BYTES:
        return None, "DUCKDB_ARROW_CAPTURE_LIMIT"
    for field, column in zip(fields, selected, strict=True):
        if not _admitted(pc, field, column):
            return None, "DUCKDB_ARROW_SCHEMA"
    copies = [_copy(pa, column) for column in selected]
    names = [f"c{k}" for k in range(len(copies))]
    return pa.Table.from_arrays(copies, names=names), None


def prepare(template, access, *, limits, isolation, values, parameters):
    """Checks 7 to 13, in order, after execute()'s shared checks 1 to 6:
    (an unopened attempt, None) or (None, the first refusal's Failure)."""
    try:
        facts = adapter.execution_facts(template)
        arguments = _bound(facts, values, parameters)
        if template.compatibility != supported_compatibility():
            raise BindingError("COMPILED_COMPATIBILITY")
    except Exception as caught:
        return None, request_failure(caught, preparing=True)
    lib = sys.modules.get("pyarrow.lib")
    if (
        type(access.name) is not str
        or not access.name
        or lib is None
        or type(access.table) is not getattr(lib, "Table", None)
    ):
        return None, failure("PIE-R1002", "EXECUTION_ACCESS")
    if access.name != facts.key:
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
        owned, detail = capture(pa, pc, access.table, facts.fields)
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
        self._registered = self._running = False
        self._ended = threading.Event()
        self._timer: Any = None
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
        """Steps 1 (the engine's own profile) and 2, then the registration:
        any failure is DUCKDB_DRIVER_PROFILE or DUCKDB_SESSION_CONTEXT."""
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
        try:
            connection.register(RELATION, self._capture)
        except Exception:
            raise ex.ExecutionError("DUCKDB_SESSION_CONTEXT") from None
        self._registered = True

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
            try:
                relation = (
                    self._connection.sql(self._sql, params=list(self._arguments))
                    if self._arguments
                    else self._connection.sql(self._sql)
                )
                table = relation.to_arrow_table()
            finally:
                with self._gate:
                    self._running = False
                    self._ended.set()
            # The statement ran in its own auto-commit transaction, which
            # ended when the whole result was materialized.
            self._transaction = "COMMIT_ACK"
            self._checkpoint()
            phase = "result"
            from pietto._project import project_execution_reader as reader

            self._batches = results.DuckDBBatches(
                self._pa,
                reader.bind_duckdb_result(self._pa, table, self.facts),
                self.limits,
            )
            self._delivery = "OPEN"
            return self
        except BaseException as error:
            self._failed(error, phase)
            raise

    def __enter__(self):
        return self.open()

    def __iter__(self):
        return self

    def __next__(self):
        if self._closed:
            raise StopIteration
        if self._started is None:
            self.open()
        phase = "delivery"
        try:
            self._checkpoint()
            batch = self._batches.next()
            if batch is not None:
                return batch
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
        if (
            self._cancel_sent
            and isinstance(interrupted, type)
            and isinstance(error, interrupted)
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
        """Step 5: unregister a registered capture, then close, whatever
        ended the attempt."""
        with self._gate:
            if self._closed or self._finalizing:
                return
            self._finalizing = True
            timer, connection = self._timer, self._connection
        if timer is not None:
            timer.cancel()
        if connection is not None:
            if self._registered:
                try:
                    connection.unregister(RELATION)
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
            self._connection = self._capture = None
            self._registered = False
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
