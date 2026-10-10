"""Explicit pinned ADBC handles and bounded Arrow storage; no ambient driver lookup."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import math
import os
import stat
from pathlib import Path
from urllib.parse import urlencode, quote

from pietto._project.project_execution import (
    ExecutionError,
    ExecutionFailure,
    pinned_modules,
)

__all__: tuple[str, ...] = ()
# The pinned driver closure of `pietto[execute-postgres-adbc]`.
DRIVERS = (
    ("adbc-driver-postgresql", "1.12.0", "adbc_driver_postgresql"),
    ("adbc-driver-manager", "1.12.0", "adbc_driver_manager"),
    ("pyarrow", "25.0.1", "pyarrow"),
)
CONTEXT_SQL = "SELECT current_setting('server_version_num')::integer,current_database()::text,current_user::text,session_user::text,(SELECT oid::bigint FROM pg_catalog.pg_roles WHERE rolname=current_user),(SELECT oid::bigint FROM pg_catalog.pg_database WHERE datname=current_database()),pg_backend_pid(),pg_current_xact_id()::text,current_setting('transaction_isolation'),current_setting('transaction_read_only'),current_setting('client_encoding'),current_setting('search_path'),current_setting('TimeZone'),current_setting('standard_conforming_strings'),inet_server_addr()::text,inet_server_port(),pg_postmaster_start_time()::text"
# Generated refinement pages run with JIT off for the rest of their transaction.
JIT_OFF_SQL = "SELECT pg_catalog.set_config('jit','off',true)"


def failure(error, phase):
    state = getattr(error, "sqlstate", None)
    return ExecutionFailure(
        phase, type(error).__name__, state if type(state) is str else None
    )


def drivers():
    """The pinned driver, manager and Arrow modules and the driver's own library."""
    driver, manager, pa = pinned_modules(DRIVERS, "POSTGRES_ADBC_DRIVER_PROFILE")
    filename = driver.__file__
    if type(filename) is not str:
        raise ExecutionError("POSTGRES_ADBC_DRIVER_LIBRARY")
    library = Path(filename).resolve().parent / "libadbc_driver_postgresql.so"
    if not library.is_file() or library.resolve().parent != library.parent:
        raise ExecutionError("POSTGRES_ADBC_DRIVER_LIBRARY")
    return manager, pa, library


def connect(owner):
    if any(k.startswith("PG") or k == "SSLKEYLOGFILE" for k in os.environ):
        raise ExecutionError("EXECUTION_AMBIENT_CONNECTION_PROFILE")
    manager, pa, library = drivers()
    a = owner.request.access
    # The pinned Linux driver supports require (encryption) or explicit loopback
    # disable. A child of the null character device cannot name a CA/CRL/key,
    # unlike an empty option, which re-enables libpq's home-directory defaults.
    if not stat.S_ISCHR(Path("/dev/null").stat().st_mode):
        raise ExecutionError("EXECUTION_AMBIENT_CONNECTION_PROFILE")
    settings = dict(
        host=a.host,
        port=str(a.port),
        dbname=a.database,
        user=a.user,
        password=a.password,
        sslmode=a.sslmode,
        gssencmode="disable",
        sslcertmode="disable",
        sslrootcert="/dev/null/pietto-ca",
        sslcrl="/dev/null/pietto-crl",
        sslcert="/dev/null/pietto-cert",
        sslkey="/dev/null/pietto-key",
        passfile="/dev/null",
        connect_timeout=str(max(2, min(10, math.ceil(owner._remaining())))),
        application_name="pietto_postgres_adbc",
        options="-c statement_timeout=10000 -c client_encoding=UTF8 -c search_path=pg_catalog -c timezone=UTC -c standard_conforming_strings=on",
    )
    uri = "postgresql:///?" + urlencode(settings, quote_via=quote)
    owner._checkpoint()
    database = manager.AdbcDatabase(driver=str(library), uri=uri)
    owner._database = owner._owned_database = database
    owner.control_events.append(("database_registered", owner.attempt))
    owner._checkpoint()
    connection = manager.AdbcConnection(database)
    owner._connection = owner._owned_connection = connection
    owner._manager = manager
    owner._arrow = pa
    owner.control_events.append(("connection_registered", owner.attempt))
    status = connection.get_option("adbc.postgresql.transaction_status")
    owner.control_events.append(("initial_transaction_status", status))
    if status != "idle":
        raise ExecutionError("POSTGRES_ADBC_INITIAL_TRANSACTION")
    owner._checkpoint()
    return connection


@dataclass(frozen=True, slots=True, eq=False)
class NativeReply:
    sql: bytes = field(repr=False)
    arguments: tuple = field(repr=False)
    rows: tuple = field(repr=False)
    terminal: str


class NativeStatement:
    """COPY results are retained as bounded Arrow batches before context SQL.

    This avoids concurrent commands on a libpq result stream. The total raw
    referenced buffers are capped before retention; driver prefetch before a
    returned batch is outside this cap. No hard native RSS claim is made.
    """

    def __init__(self, owner, sql, arguments, tags, purpose, *, copy):
        self.owner = owner
        self.sql = sql.encode() if type(sql) is str else sql
        self.arguments = arguments
        self.tags = tags
        self.purpose = purpose
        self.copy = copy
        self.native = None
        self.reader = None
        self.stream_handle = None
        self.schema = ()
        self.batches = deque()
        self.offset = 0
        self.rows = self.bytes = self.delivered = 0
        self.pulls = []
        self.terminal = None
        self.reader_close = "NOT_STARTED"
        self.statement_close = "NOT_STARTED"
        self.closed = False
        owner._statements.append(self)

    def execute(self, maximum):
        try:
            return self._execute(maximum)
        except BaseException:
            if self.native is not None:
                self.owner._unsafe_protocol = True
                if self.terminal is None:
                    self.terminal = "ERROR"
            raise

    def _execute(self, maximum):
        o = self.owner
        o._checkpoint()
        if len(self.arguments) != len(self.tags):
            raise ExecutionError("POSTGRES_ADBC_PARAMETER_TYPES")
        self.native = o._manager.AdbcStatement(o._connection)
        with o._gate:
            o._active = self
        self.native.set_options(
            **{
                "adbc.postgresql.use_copy": self.copy,
                "adbc.postgresql.batch_size_hint_bytes": min(
                    o.request.limits.batch_bytes, 65536
                ),
            }
        )
        self.native.set_sql_query(self.sql.decode())
        if self.purpose in ("query", "guard", "page"):
            o._verify_submission(self)
        o._checkpoint()
        self.native.prepare()
        if self.arguments:
            pa = o._arrow
            types = {
                "Int": pa.int64(),
                "Bool": pa.bool_(),
                "Float": pa.float64(),
                "Text": pa.string(),
                "Decimal": pa.string(),
            }
            if any(t not in types for t in self.tags):
                raise ExecutionError("POSTGRES_ADBC_PARAMETER_TYPES")
            bound = pa.record_batch(
                [
                    pa.array([v], type=types[t])
                    for v, t in zip(self.arguments, self.tags, strict=True)
                ],
                names=["p" + str(i + 1) for i in range(len(self.tags))],
            )
            if bound.num_rows != 1:
                raise ExecutionError("POSTGRES_ADBC_PARAMETER_BATCH")
            self.native.bind(bound)
        o._checkpoint()
        handle, _rowcount = self.native.execute_query()
        self.stream_handle = handle
        self.reader = o._arrow.RecordBatchReader._import_from_c(handle.address)
        if handle.is_valid:
            raise ExecutionError("POSTGRES_ADBC_STREAM_TRANSFER")
        self.schema = tuple(
            {
                "ordinal": i,
                "name": f.name,
                "type": str(f.type),
                "nullable": f.nullable,
                "metadata": {k.hex(): v.hex() for k, v in (f.metadata or {}).items()},
            }
            for i, f in enumerate(self.reader.schema)
        )
        primary = None
        try:
            while True:
                o._checkpoint()
                try:
                    batch = self.reader.read_next_batch()
                except StopIteration:
                    self.terminal = "NORMAL"
                    break
                charge = max(batch.nbytes, batch.get_total_buffer_size(), 32)
                self.pulls.append(
                    (batch.num_rows, batch.nbytes, batch.get_total_buffer_size())
                )
                if self.rows + batch.num_rows > maximum:
                    raise ExecutionError("EXECUTION_RESOURCE_LIMIT")
                o._check_total(self.bytes + charge, self)
                self.rows += batch.num_rows
                self.bytes += charge
                if batch.num_rows:
                    self.batches.append(batch)
                o._checkpoint()
        except BaseException as error:
            primary = error
            raise
        finally:
            self._close_reader(primary)
            with o._gate:
                if o._active is self:
                    o._active = None
        return self.schema

    def _close_reader(self, primary=None):
        reader = self.reader
        self.reader = None
        if reader is None:
            return
        try:
            reader.close()
            self.reader_close = "RETURNED"
        except BaseException as error:
            self.reader_close = "FAILED"
            self.owner._cleanup_errors.append(failure(error, "reader_close"))
            if primary is None:
                raise

    def fetch(self, count):
        self.owner._checkpoint()
        rows = []
        while self.batches and len(rows) < count:
            batch = self.batches[0]
            length = min(count - len(rows), batch.num_rows - self.offset)
            rows.extend(
                tuple(batch.column(i)[j].as_py() for i in range(batch.num_columns))
                for j in range(self.offset, self.offset + length)
            )
            self.offset += length
            self.delivered += length
            if self.offset == batch.num_rows:
                self.batches.popleft()
                self.offset = 0
        self.owner._checkpoint()
        return tuple(rows)

    @property
    def exhausted(self):
        return self.terminal == "NORMAL" and not self.batches

    def close(self):
        if self.closed:
            return
        self.closed = True
        primary = None
        with self.owner._gate:
            try:
                self._close_reader()
            except BaseException as error:
                primary = error
            handle = self.stream_handle
            self.stream_handle = None
            if handle is not None and handle.is_valid:
                try:
                    handle.release()
                except BaseException as error:
                    self.owner._cleanup_errors.append(failure(error, "stream_release"))
                    if primary is None:
                        primary = error
            if self.native is not None:
                try:
                    self.native.close()
                    self.statement_close = "RETURNED"
                except BaseException as error:
                    if primary is None:
                        primary = error
                    else:
                        self.owner._cleanup_errors.append(
                            failure(error, "statement_close")
                        )
            if self.owner._active is self:
                self.owner._active = None
        self.batches.clear()
        if self in self.owner._statements:
            self.owner._statements.remove(self)
        if primary is not None:
            raise primary


def read_control(owner, sql, arguments=(), tags=(), *, maximum=1024, finalizing=False):
    statement = NativeStatement(owner, sql, arguments, tags, "control", copy=False)
    old = owner._finalizing
    owner._finalizing = finalizing
    primary = None
    try:
        schema = statement.execute(maximum)
        rows = statement.fetch(maximum + 1)
        if not statement.exhausted or len(rows) > maximum:
            raise ExecutionError("POSTGRES_ADBC_CONTROL_TERMINAL")
        if not finalizing:
            owner._charge_internal(rows, statement.bytes)
        reply = NativeReply(statement.sql, arguments, rows, "NORMAL")
        return schema, rows, reply
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            statement.close()
        except BaseException as error:
            owner._cleanup_errors.append(failure(error, "statement_close"))
            if primary is None:
                raise
        finally:
            owner._finalizing = old
