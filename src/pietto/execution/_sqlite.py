"""The ``sqlite_file`` route (docs/spec/sqlite-project-v1.md, "Execution";
PL.47): its request checks after execute()'s shared ones, and one attempt
that opens the caller's SQLite file read-only behind the eleven defences,
checks its source in the attempt's one read transaction and runs the
compiled statement there.

Importing this module loads no sqlite3 and no PyArrow. execute() imports
sqlite3 to read the linked build from a ``:memory:`` database; only an
opening attempt checks the pinned PyArrow and opens the file. The attempt
depends only downward: it runs the adapter's verified statement and never
reads source syntax or reselects a target.
"""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
import stat
import sys
import threading
import time
from typing import Any
import uuid

from pietto._project import project_execution as ex
from pietto._project import project_sqlite_emission as adapter
from pietto._project import project_sqlite_result as results
from pietto._project.project_compiled_loading import supported_compatibility
from pietto._project.project_duckdb_result import DuckDBBatches
from pietto._project.project_execution_template import BindingError
from pietto._project.project_result_contract import ResultError
from pietto._project.project_sql_emission_parameters import parameter_valid
from pietto._project.project_sqlite_sql import FUNCTIONS, WINDOWS, quoted
from pietto.execution._errors import failure, request_failure

__all__: tuple[str, ...] = ()

# PL.47: at most 1,048,576 rows per source table, and a file of at most
# 128 MiB with its -wal file: S12 measured the check of a 253 MiB file of
# randomly keyed indexes past the 20 s deadline, so the cap went down from
# 256 MiB and the deadline stayed.
MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_SOURCE_ROWS = 1_048_576
# Virtual machine steps between two deadline and cancel checks.
PROGRESS_STEPS = 10_000
# Rows the text check and the result read fetch at a time.
FETCH_ROWS = 4096
# The STRICT column types each logical type is read from.
DECLARED = {
    "Int": ("INT", "INTEGER"),
    "Bool": ("INT", "INTEGER"),
    "Float": ("REAL",),
    "Text": ("TEXT",),
}
# The functions the compiled statement and the value check call; a window
# function arrives under its lower-case name too.
CALLS = frozenset(
    {
        *(name.lower() for name in (*FUNCTIONS.values(), *WINDOWS.values())),
        "typeof",
        "abs",
    }
)
# The PRAGMA statements of the source check: whether each names the source.
# `index_xinfo` names one of the source's indexes instead.
PRAGMAS = {
    "schema_version": False,
    "encoding": False,
    "table_list": True,
    "index_list": True,
    "table_xinfo": True,
    "integrity_check": True,
}
_TAGS = {kind: tag for tag, kind in adapter.STORAGES.items()}


@dataclass(frozen=True, slots=True, eq=False)
class SQLiteTemplate:
    """The live query of a VERIFIED SQLite document and the installed code
    identity it was compiled with; the ``sqlite_file`` route executes it."""

    emission: Any
    compatibility: tuple[Any, ...]

    def __repr__(self) -> str:
        return "SQLiteTemplate(emission=...)"

    def facts(self) -> tuple[Any, ...]:
        """Module, kind, name, family, release, literal policy, slot tags and
        header parameters, as `query_facts` gives them on the other targets."""
        checked = self.emission.checked
        owner = checked.selected_owner
        return (
            checked.completed.semantic_result.modules[owner.module_position].path,
            owner.identity.declaration_kind.value,
            owner.definition.name,
            adapter.FAMILY,
            self.emission.contract.release,
            "preserve",
            (),
            tuple(
                (
                    p.declaration.name,
                    p.tag,
                    p.value_type.nullability.value == "nullable",
                )
                for p in checked.plan.parameters
            ),
        )


def prepare_sqlite_live_template(outcome: Any) -> SQLiteTemplate | None:
    """The live template of a VERIFIED outcome whose artifact verifies afresh;
    None for any other status (the command's failure document)."""
    if outcome.status != "VERIFIED" or outcome.artifact is None:
        return None
    if type(outcome) is not adapter.SQLiteEmission or not adapter.verify_artifact(
        outcome.artifact
    ):
        raise ValueError("BINDING_ARTIFACT")
    return SQLiteTemplate(outcome.artifact, supported_compatibility())


@dataclass(frozen=True, slots=True)
class SQLiteSourceField:
    """One source field in shape order: its column, logical type, compiled
    nullability and declared domain (`int_range` of an `Int`,
    `max_characters` of a `Text`)."""

    column: str
    tag: str
    nullable: bool
    bounds: tuple[int, int] | None
    max_characters: int | None


@dataclass(frozen=True, slots=True)
class SQLiteExecutionFacts:
    """What the route reads of one verified artifact: the source table's
    name, the statement, the source fields, each result column as (label,
    storage kind, nullable), the parameter read by each of ``?1``, ``?2``,
    ... and the header parameters as (name, tag, nullable)."""

    name: str
    sql: str
    fields: tuple[SQLiteSourceField, ...]
    result: tuple[tuple[str, str, bool], ...]
    uses: tuple[int, ...]
    parameters: tuple[tuple[str, str, bool], ...]


def execution_facts(template: object) -> SQLiteExecutionFacts:
    """The facts of a live template whose artifact verifies afresh; any other
    value is BINDING_ARTIFACT."""
    if type(template) is not SQLiteTemplate or not adapter.verify_artifact(
        template.emission
    ):
        raise ValueError("BINDING_ARTIFACT")
    artifact = template.emission
    document = json.loads(artifact.document)
    (source,) = artifact.checked.plan.sources
    (entry,) = (s for s in artifact.contract.sources if s.owner is source.source.owner)
    fields = []
    for field in sorted(entry.fields, key=lambda f: f.ordinal):
        representation = field.representation
        tag = _TAGS[representation["storage"]["kind"]]
        domain = representation["domain"]
        fields.append(
            SQLiteSourceField(
                field.column,
                tag,
                representation["nullable"],
                (int(domain["min"]), int(domain["max"])) if tag == "Int" else None,
                domain["max_characters"] if tag == "Text" else None,
            )
        )
    servers: dict[int, int] = {}
    for use in document["parameter_uses"]:
        parameter = use["owner"]["parameter"]
        if servers.setdefault(use["server_index"], parameter) != parameter:
            raise ValueError("BINDING_ARTIFACT")
    if sorted(servers) != list(range(1, len(servers) + 1)):
        raise ValueError("BINDING_ARTIFACT")
    return SQLiteExecutionFacts(
        entry.name,
        artifact.sql.decode("utf-8"),
        tuple(fields),
        tuple(
            (c["label"], c["representation"]["storage"]["kind"], c["nullable"])
            for c in document["columns"]
        ),
        tuple(servers[k] for k in sorted(servers)),
        template.facts()[7],
    )


def _bound(facts, values, parameters):
    """The binding: no value slots, and exactly the declared header
    parameters, each of its exact type and without NUL in a `Text`
    (BINDING_* words, PIE-R1006); the values of ``?1``, ``?2``, ..."""
    if values is not None and len(values) != 0:
        raise BindingError("BINDING_SLOTS")
    supplied = {} if parameters is None else parameters
    if set(supplied) != {name for name, _tag, _nullable in facts.parameters}:
        raise BindingError("BINDING_PARAMETERS")
    arguments = []
    for ordinal, (name, tag, nullable) in enumerate(facts.parameters):
        value = supplied[name]
        if value is None:
            valid = nullable
        else:
            valid = parameter_valid(tag, value, adapter.FAMILY) and not (
                tag == "Text" and "\0" in value
            )
        if not valid:
            raise BindingError(f"BINDING_PARAMETER:{ordinal}:{tag}")
        arguments.append(int(value) if tag == "Bool" and value is not None else value)
    return tuple(arguments[k] for k in facts.uses)


def _path(value):
    """The caller's path as a non-empty `str` without NUL, joined to the
    working directory of this call when relative (no file is read), or None.
    It is not normalized: a `..` after a symbolic link is resolved with the
    file, as the operating system would."""
    try:
        path = os.fspath(value)
        if type(path) is not str or not path or "\0" in path:
            return None
        return path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
    except Exception:
        return None


def qualified_build() -> bool:
    """Defence 9: Linux x86-64 and the measured SQLite build, read from a
    ``:memory:`` database before any file opens."""
    if sys.platform != "linux" or platform.machine() != "x86_64":
        return False
    try:
        import sqlite3

        from pietto.sql.sqlite import QUALIFIED_SQLITE_BUILD as build

        probe = sqlite3.connect(":memory:")
        try:
            release, source = probe.execute(
                "SELECT sqlite_version(), sqlite_source_id()"
            ).fetchone()
            options = tuple(row[0] for row in probe.execute("PRAGMA compile_options"))
        finally:
            probe.close()
    except Exception:
        return False
    return (release, source, options) == (
        build.release,
        build.source_id,
        build.compile_options,
    )


def prepare(template, access, *, limits, isolation, values, parameters):
    """The route's request checks after execute()'s shared ones, in order:
    (an unopened attempt, None) or (None, the first refusal's Failure)."""
    try:
        facts = execution_facts(template)
        arguments = _bound(facts, values, parameters)
        if template.compatibility != supported_compatibility():
            raise BindingError("COMPILED_COMPATIBILITY")
    except Exception as caught:
        return None, request_failure(caught, preparing=True)
    path = _path(access.path)
    if path is None:
        return None, failure("PIE-R1002", "EXECUTION_ACCESS")
    if type(isolation) is not str or isolation != "stable":
        return None, failure("PIE-R1002", "EXECUTION_ISOLATION")
    try:
        ex.verify_execution_limits(limits)
    except Exception as caught:
        return None, request_failure(caught, preparing=True)
    if not qualified_build():
        return None, failure("PIE-R2002", "SQLITE_BUILD")
    return SQLiteAttempt(facts, path, arguments, limits), None


def _file(name):
    """Defences 1, 6 and the file limit of 8: the resolved path of a
    non-empty regular file whose -wal, -journal and -shm files, where they
    exist, are regular files too, and that holds at most MAX_FILE_BYTES
    with its -wal file."""
    try:
        # The caller's string first: resolve() drops a trailing / or /. and,
        # before 3.13, reads f.db/../g.db where the system reports ENOTDIR.
        given = os.stat(name)
        path = Path(name).resolve(strict=True)
        status = os.stat(path)
    except (OSError, RuntimeError, ValueError):
        raise ex.ExecutionError("SQLITE_FILE_TYPE") from None
    # SQLite deletes the -wal file beside a 0-byte database.
    if (
        not os.path.samestat(given, status)
        or not stat.S_ISREG(status.st_mode)
        or status.st_size == 0
    ):
        raise ex.ExecutionError("SQLITE_FILE_TYPE")
    size = status.st_size
    # SQLite opens each of these itself: a FIFO would block it beyond the
    # deadline, and it truncates an -shm file, through any other link too.
    for suffix in ("-wal", "-journal", "-shm"):
        try:
            companion = os.stat(str(path) + suffix)
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            raise ex.ExecutionError("SQLITE_FILE_TYPE") from None
        if not stat.S_ISREG(companion.st_mode) or (
            suffix == "-shm" and companion.st_nlink != 1
        ):
            raise ex.ExecutionError("SQLITE_FILE_TYPE")
        if suffix == "-wal":
            size += companion.st_size
    if size > MAX_FILE_BYTES:
        raise ex.ExecutionError("SQLITE_FILE_LIMIT")
    return path


class SQLiteAttempt:
    """One attempt: one read-only connection to the caller's file and one
    read transaction, opened when the handle is first entered, which check
    the source, run the compiled statement, read its whole result, commit
    and close before the first batch. It has the private owner surface
    ResultHandle reads; nothing is pooled, cached or reused."""

    def __init__(self, facts, path, arguments, limits):
        self.facts = facts
        self._path = path
        self._arguments = arguments
        self.limits = limits
        self.attempt = uuid.uuid4().hex
        self._gate = threading.RLock()
        self._connection: Any = None
        self._checking = True
        self._indexes: tuple[str, ...] = ()
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

        return results.result_schema(arrow.pinned(), self.facts.result)

    def _claim_terminal(self, terminal):
        with self._gate:
            if self._terminal is not None or self._closed or self._finalizing:
                return False
            self._terminal = terminal
            return True

    def _expired(self):
        return time.monotonic() - self._started >= self.limits.seconds

    def _checkpoint(self):
        if self._cancel_requested and not self.deadline_expired:
            raise ex.ExecutionError("EXECUTION_CANCELED")
        if self.deadline_expired or self._expired():
            self.cancel(deadline=True)
            self.deadline_expired = True
            raise TimeoutError("EXECUTION_DEADLINE")

    def _progress(self):
        """SQLite's progress handler: a nonzero answer interrupts the
        running statement (SQLITE_INTERRUPT)."""
        if not self._cancel_requested and self._expired():
            self.cancel(deadline=True)
        return 1 if self._cancel_requested else 0

    def _authorize(self, action, first, second, database, inner):
        """Defence 3: allow or SQLITE_DENY, never SQLITE_IGNORE. Reads of the
        source's columns, and of no column (``count(*)``, whose database is
        None unqualified); the statement's and the check's functions; the
        source check's PRAGMA statements, ``index_xinfo`` only of the
        source's indexes, until the statement runs; the read transaction's
        own BEGIN, COMMIT and ROLLBACK."""
        import sqlite3

        name = self.facts.name
        if inner is not None:
            allowed = False
        elif action == sqlite3.SQLITE_READ:
            allowed = first == name and (
                (second == "" and database in ("main", None))
                or (
                    database == "main"
                    and any(second == f.column for f in self.facts.fields)
                )
            )
        elif action == sqlite3.SQLITE_SELECT:
            allowed = first is None and second is None
        elif action == sqlite3.SQLITE_FUNCTION:
            allowed = first is None and second in CALLS
        elif action == sqlite3.SQLITE_PRAGMA:
            allowed = self._checking and (
                second in self._indexes
                if first == "index_xinfo"
                else first in PRAGMAS and second == (name if PRAGMAS[first] else None)
            )
        elif action == sqlite3.SQLITE_TRANSACTION:
            allowed = first in ("BEGIN", "COMMIT", "ROLLBACK")
        else:
            allowed = False
        return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY

    def _session(self, sqlite3, path):
        """Defences 1 to 3 and 7, then the snapshot: the file opened through
        its percent-encoded URI with ``mode=ro``, the hardening set and read
        back (SQLITE_SESSION_CONTEXT), the progress handler, the busy timeout
        within the deadline, the authorizer, BEGIN and the first read."""
        connection = sqlite3.connect(
            path.as_uri() + "?mode=ro",
            uri=True,
            timeout=0,
            isolation_level=None,
            check_same_thread=True,
        )
        with self._gate:
            self._connection = connection
        options = (
            (sqlite3.SQLITE_DBCONFIG_DEFENSIVE, True),
            (sqlite3.SQLITE_DBCONFIG_TRUSTED_SCHEMA, False),
            (sqlite3.SQLITE_DBCONFIG_ENABLE_LOAD_EXTENSION, False),
        )
        for option, value in options:
            connection.setconfig(option, value)
        pragmas = (("cell_size_check", 1), ("mmap_size", 0), ("query_only", 1))
        for pragma, value in pragmas:
            connection.execute(f"PRAGMA {pragma} = {value}")
        if any(connection.getconfig(o) is not v for o, v in options) or any(
            connection.execute(f"PRAGMA {p}").fetchall() != [(v,)] for p, v in pragmas
        ):
            raise ex.ExecutionError("SQLITE_SESSION_CONTEXT")
        connection.set_progress_handler(self._progress, PROGRESS_STEPS)
        self._checkpoint()
        remaining = self.limits.seconds - (time.monotonic() - self._started)
        waited = min(2**31 - 1, max(1, int(remaining * 1000) + 1))
        connection.execute(f"PRAGMA busy_timeout = {waited}")
        connection.set_authorizer(self._authorize)
        connection.execute("BEGIN")
        self._transaction = "UNKNOWN"
        # The first read opens the read transaction, so the checks and the
        # statement below see one snapshot of schema and data.
        connection.execute("PRAGMA schema_version").fetchall()
        self.session_id = self.attempt
        return connection

    def _check(self, connection):
        """Defences 4 and 5, the row limit of 8 and the value check of Q6b
        (i), in the read transaction; the integrity check runs before any
        row of the source is read, and only once no expression of the file
        is left for it to run."""
        name, fields = self.facts.name, self.facts.fields
        table = quoted(name)
        if connection.execute("PRAGMA encoding").fetchall() != [("UTF-8",)]:
            raise ex.ExecutionError("SQLITE_FILE_ENCODING")
        listed = connection.execute(f"PRAGMA table_list({table})").fetchall()
        if len(listed) != 1 or (*listed[0][:3], listed[0][5]) != (
            "main",
            name,
            "table",
            1,
        ):
            raise ex.ExecutionError("SQLITE_SOURCE_OBJECT")
        # The integrity check computes an index's expression keys and WHERE
        # clause and a generated column's value: the file's own code, which
        # the authorizer never sees and one step can run past the deadline.
        indexes = connection.execute(f"PRAGMA index_list({table})").fetchall()
        self._indexes = tuple(row[1] for row in indexes)
        if any(row[4] for row in indexes) or any(
            key[1] == -2
            for index in self._indexes
            for key in connection.execute(
                f"PRAGMA index_xinfo({quoted(index)})"
            ).fetchall()
        ):
            raise ex.ExecutionError("SQLITE_SOURCE_OBJECT")
        columns = connection.execute(f"PRAGMA table_xinfo({table})").fetchall()
        declared = {row[1]: row[2] for row in columns}
        if any(row[6] != 0 for row in columns):
            raise ex.ExecutionError("SQLITE_SOURCE_COLUMNS")
        for field in fields:
            kind = declared.get(field.column)
            if not (
                type(kind) is str
                and kind.isascii()
                and kind.upper() in DECLARED[field.tag]
            ):
                raise ex.ExecutionError("SQLITE_SOURCE_COLUMNS")
        if connection.execute(f"PRAGMA integrity_check({table})").fetchall() != [
            ("ok",)
        ]:
            raise ex.ExecutionError("SQLITE_SOURCE_INTEGRITY")
        self._checkpoint()
        source = "`main`." + table
        (count,) = connection.execute(f"SELECT count(*) FROM {source}").fetchone()
        if count > MAX_SOURCE_ROWS:
            raise ex.ExecutionError("SQLITE_SOURCE_LIMIT")
        tests, arguments = [], []
        for field in fields:
            column = quoted(field.column)
            if field.tag == "Int":
                test = f"typeof({column}) = 'integer' AND {column} BETWEEN ? AND ?"
                arguments.extend(field.bounds or ())
            elif field.tag == "Bool":
                test = f"typeof({column}) = 'integer' AND {column} IN (0, 1)"
            elif field.tag == "Float":
                test = f"typeof({column}) = 'real' AND abs({column}) <= ?"
                arguments.append(sys.float_info.max)
            else:
                test = f"typeof({column}) = 'text'"
            if field.nullable:
                test = f"typeof({column}) = 'null' OR ({test})"
            tests.append(f"({test})")
        # A row whose test is false, or NULL, breaks a domain.
        broken = connection.execute(
            f"SELECT 1 FROM {source} WHERE ({' AND '.join(tests) or '1'}) IS NOT 1"
            " LIMIT 1",
            arguments,
        ).fetchall()
        if broken:
            raise ex.ExecutionError("SQLITE_SOURCE_VALUES")
        texts = [field for field in fields if field.tag == "Text"]
        if not texts:
            return
        # No SQL form finds invalid UTF-8, so each Text value is decoded here.
        # A cursor left running would keep an interrupt alive into ROLLBACK.
        with closing(
            connection.execute(
                "SELECT "
                + ", ".join(f"CAST({quoted(f.column)} AS BLOB)" for f in texts)
                + f" FROM {source}"
            )
        ) as cursor:
            while rows := cursor.fetchmany(FETCH_ROWS):
                self._checkpoint()
                for row in rows:
                    for field, raw in zip(texts, row, strict=True):
                        if raw is not None and not _text_holds(
                            raw, field.max_characters
                        ):
                            raise ex.ExecutionError("SQLITE_SOURCE_VALUES")

    def _query(self, connection):
        """The compiled statement once, read to its end."""
        self._checking = False
        rows: list[Any] = []
        with closing(connection.execute(self.facts.sql, self._arguments)) as cursor:
            labels = tuple(item[0] for item in cursor.description or ())
            if labels != tuple(label for label, _kind, _nullable in self.facts.result):
                raise ResultError("SQLITE_RESULT_CHECK")
            while chunk := cursor.fetchmany(FETCH_ROWS):
                self._checkpoint()
                rows.extend(chunk)
        connection.execute("COMMIT")
        self._transaction = "COMMIT_ACK"
        return rows

    def open(self):
        if self._started is not None or self._closed:
            raise ex.ExecutionError("EXECUTION_REUSE")
        self._started = time.monotonic()
        phase = "driver"
        try:
            self._checkpoint()
            from pietto._project import project_arrow_result as arrow

            pa = arrow.pinned()
            import sqlite3

            phase = "file"
            path = _file(self._path)
            phase = "session"
            connection = self._session(sqlite3, path)
            phase = "source"
            self._check(connection)
            phase = "query"
            rows = self._query(connection)
            phase = "finalization"
            self._disconnect()
            if self._cleanup_errors:
                raise ex.ExecutionError("EXECUTION_FINALIZATION")
            self._checkpoint()
            phase = "result"
            table = results.bind_result(pa, rows, self.facts.result)
            self._batches = DuckDBBatches(pa, table, self.limits)
            self._delivery = "OPEN"
            return self
        except BaseException as error:
            # The busy timeout ends at the deadline, which caused its error.
            code = getattr(error, "sqlite_errorcode", None)
            if type(code) is int and code & 0xFF == 5 and self._expired():
                self.cancel(deadline=True)
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
        if (
            self._cancel_requested
            and getattr(error, "sqlite_errorcode", None) == 9  # SQLITE_INTERRUPT
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
            if self._connection is not None:
                # Stops a running statement; the progress handler and the
                # checkpoints stop one that starts later.
                self._connection.interrupt()
                self._cancel_sent = True
            return {
                "requested": True,
                "sent": self._cancel_sent,
                "observed": self._cancel_observed,
                "late": False,
            }

    def _disconnect(self):
        """Roll back a read transaction still open, then close, whatever
        ended the attempt; each failed step is a cleanup failure."""
        with self._gate:
            connection, self._connection = self._connection, None
        if connection is None:
            return
        try:
            # A cancelled or expired attempt's handler would stop ROLLBACK too.
            connection.set_progress_handler(None, 0)
            if connection.in_transaction:
                connection.execute("ROLLBACK")
                self._transaction = "ROLLBACK_ACK"
        except BaseException as error:
            self._cleanup_errors.append(
                ex.ExecutionFailure("transaction", type(error).__name__)
            )
        try:
            connection.close()
        except BaseException as error:
            self._cleanup_errors.append(
                ex.ExecutionFailure("close", type(error).__name__)
            )

    def _finish(self):
        with self._gate:
            if self._closed or self._finalizing:
                return
            self._finalizing = True
        self._disconnect()
        with self._gate:
            self._closed = True
            self._finalizing = False
            self._cleanup = "FAILED" if self._cleanup_errors else "CLOSED"

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


def _text_holds(raw, longest):
    """A `Text` value's bytes: strict UTF-8 without NUL, of at most
    ``longest`` characters."""
    if type(raw) is not bytes or b"\0" in raw:
        return False
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return type(longest) is int and len(text) <= longest
