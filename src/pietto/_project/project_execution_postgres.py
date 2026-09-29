"""Explicit private PostgreSQL attempt. Imports do not load a driver or Arrow."""

from __future__ import annotations

import importlib
import math
import os
import threading
import time
import uuid
from typing import Any

from pietto._project.project_execution import (
    ExecutionError,
    ExecutionFailure,
    ExecutionOutcome,
    request_state,
    execution_arguments,
    verify_execution_request,
)
from pietto._project.project_execution_reader import ExecutionPayloads
from pietto._project.project_execution_source import admit_postgres_source

__all__: tuple[str, ...] = ()


def _connect(request):
    if any(name.startswith("PG") or name == "SSLKEYLOGFILE" for name in os.environ):
        raise ExecutionError("EXECUTION_AMBIENT_CONNECTION_PROFILE")
    pg = importlib.import_module("psycopg")
    a = request.access
    return pg.connect(
        host=a.host,
        port=a.port,
        dbname=a.database,
        user=a.user,
        password=a.password,
        sslmode=a.sslmode,
        gssencmode="disable",
        sslcertmode="disable",
        passfile="/dev/null",
        connect_timeout=max(2, min(10, math.ceil(request.limits.seconds))),
        options=f"-c statement_timeout={max(1, min(10000, math.ceil(request.limits.seconds * 1000)))} -c client_encoding=UTF8 -c search_path=pg_catalog",
        application_name="pietto_private_execution",
        autocommit=True,
        cursor_factory=pg.RawCursor,
    )


def failure(error, phase):
    # Keep structured failure identity; credentials/SQL/values never enter text.
    return ExecutionFailure(
        phase, type(error).__name__, getattr(error, "sqlstate", None)
    )


class PostgresExecution:
    def __init__(self, request):
        verify_execution_request(request)
        self.request = request
        self._captured = request_state(request)
        self.attempt = uuid.uuid4().hex
        self._connection: Any = None
        self._owned_connection: Any = None
        self._owned_cursor: Any = None
        self._cursor: Any = None
        self._payloads = None
        self._started = None
        self._submitted = False
        self._closed = False
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._source = "NOT_STARTED"
        self._transaction = "NOT_STARTED"
        self._delivery = "NOT_STARTED"
        self._cleanup = "NOT_STARTED"
        self._primary = None
        self._cleanup_errors = []
        self._timer = None
        self.control_events = []
        self.deadline_expired = False
        self._cancel_sent = self._cancel_observed = False
        self.session_id = None
        self.context = None
        self.source_admission = None
        self._owned_admission = None
        self.native_buffered_rows = None
        self.actual_metadata = None
        self.actual_metadata_details = None

    def _verify(self):
        verify_execution_request(self.request)
        if (
            self._connection is not self._owned_connection
            or self._cursor is not self._owned_cursor
            or self.source_admission is not self._owned_admission
        ):
            raise ExecutionError("EXECUTION_RESOURCE_IDENTITY")
        if request_state(self.request) != self._captured:
            raise ExecutionError("EXECUTION_REQUEST_CHANGED")
        if self.source_admission is not None:
            self.source_admission.verify(
                self._connection, self.request.source_requirement
            )

    def _remaining(self):
        if self._started is None:
            return self.request.limits.seconds
        remaining = self.request.limits.seconds - (time.monotonic() - self._started)
        if remaining <= 0:
            raise TimeoutError("EXECUTION_DEADLINE")
        return remaining

    def open(self):
        if self._connection is not None or self._closed:
            raise ExecutionError("EXECUTION_REUSE")
        self._verify()
        self._started = time.monotonic()
        try:
            if self._cancel.is_set():
                raise ExecutionError("EXECUTION_PRE_CANCELED")
            self._timer = threading.Timer(self.request.limits.seconds, self._deadline)
            self._timer.name = "pietto-deadline-" + self.attempt
            self.control_events.append(("thread_registered", self._timer.name))
            self._timer.start()
            self.control_events.append(("connection_open_intent", self.attempt))
            connection = _connect(self.request)
            with self._lock:
                self._connection = connection
                self._owned_connection = connection
                self.session_id = connection.info.backend_pid
                self.control_events.append(("connection_registered", self.session_id))
            family, minor = map(int, self.request.artifact.request.release.split("."))
            if connection.info.server_version != family * 10000 + minor:
                raise ExecutionError("EXECUTION_TARGET_VERSION")
            strength = (
                "REPEATABLE READ"
                if self.request.isolation == "stable"
                else "SERIALIZABLE"
            )
            with connection.cursor() as control:
                self._transaction = "UNKNOWN"
                control.execute("BEGIN ISOLATION LEVEL " + strength + " READ ONLY")
                self._transaction = "OPEN"
                control.execute(
                    "SELECT current_user,current_setting('transaction_isolation'),current_setting('transaction_read_only'),current_setting('client_encoding'),current_setting('search_path'),pg_backend_pid()"
                )
                row = control.fetchone()
                if row[:5] != (
                    self.request.access.user,
                    strength.lower(),
                    "on",
                    "UTF8",
                    "pg_catalog",
                ):
                    raise ExecutionError("EXECUTION_CONTEXT")
                self.context = row[:5]
                self.session_id = row[5]
            if self.request.source_requirement is not None:
                self.source_admission = admit_postgres_source(
                    connection,
                    self.request.source_requirement,
                    role=row[0],
                    session_id=self.session_id,
                )
                self._owned_admission = self.source_admission
            self._remaining()
            self._delivery = "OPEN"
            return self
        except BaseException as error:
            self._primary = failure(error, "admission")
            self._source = "FAILED"
            self._delivery = "FAILED"
            self._finish(False)
            raise

    def __enter__(self):
        return self.open()

    def __iter__(self):
        return self

    def __next__(self):
        if self._closed:
            raise StopIteration
        if self._connection is None:
            self.open()
        phase = "execute" if not self._submitted else "read"
        try:
            self._verify()
            # Binding checks can take time; apply the existing control checkpoint
            # after them and before submitting the immutable accepted tuple.
            arguments = execution_arguments(self.request) if not self._submitted else ()
            if self._cancel.is_set():
                raise ExecutionError("EXECUTION_CANCELED")
            remaining = self._remaining()
            connection = self._connection
            if connection is None:
                raise ExecutionError("EXECUTION_CONNECTION")
            if not self._submitted:
                with connection.cursor() as control:
                    ms = max(1, min(10000, math.ceil(remaining * 1000)))
                    control.execute(
                        "SELECT pg_catalog.set_config('statement_timeout',$1,true)",
                        (str(ms),),
                    )
                self._cursor = connection.cursor()
                self._owned_cursor = self._cursor
                self._source = "EXECUTING"
                self._cursor.execute(
                    self.request.artifact.rendered.sql.decode("utf-8"),
                    arguments,
                    prepare=True,
                )
                self._submitted = True
                self._source = "READING"
                self.native_buffered_rows = getattr(
                    getattr(self._cursor, "pgresult", None), "ntuples", None
                )
                self.actual_metadata = tuple(
                    (c.name, c.type_code, c.null_ok) for c in self._cursor.description
                )
                self.actual_metadata_details = tuple(
                    (
                        c.name,
                        c.type_code,
                        getattr(c, "display_size", None),
                        getattr(c, "internal_size", None),
                        getattr(c, "precision", None),
                        getattr(c, "scale", None),
                        c.null_ok,
                    )
                    for c in self._cursor.description
                )
                self._payloads = ExecutionPayloads(
                    self.request, self._cursor.description
                )
            self._remaining()
            if self._cancel.is_set():
                raise ExecutionError("EXECUTION_CANCELED")
            phase = "read"
            rows = self._cursor.fetchmany(self.request.limits.batch_rows)
            self._remaining()
            if self._cancel.is_set():
                raise ExecutionError("EXECUTION_CANCELED")
            if not rows:
                self._source = "EOF"
                self._delivery = "COMPLETE"
                self._finish(True)
                if self._primary is not None or self._cleanup_errors:
                    phase = "finalization"
                    raise ExecutionError("EXECUTION_FINALIZATION")
                raise StopIteration
            phase = "check"
            if self._payloads is None:
                raise ExecutionError("EXECUTION_METADATA")
            batch = self._payloads.accept(rows)
            try:
                self._remaining()
                if self._cancel.is_set():
                    raise ExecutionError("EXECUTION_CANCELED")
            except BaseException:
                close = getattr(batch, "close", None)
                if close is not None:
                    try:
                        close()
                    except BaseException as cleanup:
                        self._cleanup_errors.append(failure(cleanup, "batch_close"))
                raise
            return batch
        except StopIteration:
            raise
        except BaseException as error:
            if self._primary is None:
                self._primary = failure(error, phase)
            self._cancel_observed = (
                getattr(error, "sqlstate", None) == "57014"
                and self._cancel.is_set()
                and "due to user request"
                in str(getattr(getattr(error, "diag", None), "message_primary", ""))
            )
            if self._source != "EOF":
                self._source = "INCOMPLETE" if phase == "check" else "FAILED"
            self._delivery = "FAILED"
            self._finish(False)
            raise

    def _deadline(self):
        self.deadline_expired = True
        self.cancel()

    @property
    def control_joined(self):
        return self._timer is None or not self._timer.is_alive()

    def cancel(self):
        self._cancel.set()
        with self._lock:
            connection = self._owned_connection
            if self._closed or self._transaction == "COMMIT_ACK" or connection is None:
                return {
                    "requested": True,
                    "sent": False,
                    "observed": False,
                    "late": self._closed,
                }
        try:
            connection.cancel_safe(timeout=2)
            self._cancel_sent = True
            return {
                "requested": True,
                "sent": True,
                "observed": self._cancel_observed,
                "late": False,
            }
        except BaseException as error:
            self._cleanup_errors.append(failure(error, "cancel"))
            return {"requested": True, "sent": False, "observed": False, "late": False}

    def _finish(self, commit):
        if self._closed:
            return
        if self._owned_cursor is not None:
            try:
                self._owned_cursor.close()
            except BaseException as error:
                self._cleanup_errors.append(failure(error, "statement_close"))
        if self._owned_connection is not None:
            if self._transaction == "OPEN":
                try:
                    with self._owned_connection.cursor() as control:
                        control.execute("COMMIT" if commit else "ROLLBACK")
                    self._transaction = "COMMIT_ACK" if commit else "ROLLBACK_ACK"
                except BaseException as error:
                    self._transaction = "UNKNOWN"
                    if self._primary is None:
                        self._primary = failure(error, "transaction")
                    else:
                        self._cleanup_errors.append(failure(error, "transaction"))
            try:
                self._owned_connection.close()
            except BaseException as error:
                self._cleanup_errors.append(failure(error, "connection_close"))
                try:
                    self._owned_connection.pgconn.finish()
                except BaseException as discard:
                    self._cleanup_errors.append(failure(discard, "connection_discard"))
        with self._lock:
            self._closed = True
        if self._timer is not None:
            self._timer.cancel()
            if threading.current_thread() is not self._timer:
                self._timer.join(timeout=3)
                if self._timer.is_alive():
                    self._cleanup_errors.append(
                        ExecutionFailure("control_join", "TimeoutError")
                    )
        self._cleanup = "FAILED" if self._cleanup_errors else "CLOSED"

    def close(self):
        if not self._closed:
            if self._source != "EOF":
                self._source = "EARLY_CLOSE"
                if self._delivery != "FAILED":
                    self._delivery = "INCOMPLETE"
            self._finish(False)

    def __exit__(self, kind, error, traceback):
        if error is not None and self._primary is None:
            self._primary = failure(error, "consumer")
            self._delivery = "FAILED"
        self.close()
        return False

    @property
    def outcome(self):
        payloads = self._payloads
        return ExecutionOutcome(
            self.attempt,
            self._source,
            self._transaction,
            self._delivery,
            self._cleanup,
            0 if payloads is None else payloads.rows,
            0 if payloads is None else payloads.batches,
            0 if payloads is None else payloads.bytes,
            self._primary,
            tuple(self._cleanup_errors),
            self._cancel.is_set(),
            self._cancel_sent,
            self._cancel_observed,
        )
