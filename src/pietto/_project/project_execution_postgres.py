"""Explicit private PostgreSQL attempt. Imports do not load a driver or Arrow."""

from __future__ import annotations

import importlib
import math
import os
import threading
import time
import uuid
from typing import Any, cast

from pietto._project.project_execution import (
    ExecutionError,
    ExecutionRequest,
    ExecutionFailure,
    ExecutionOutcome,
    PostgresAccess,
    request_state,
    execution_arguments,
    verify_execution_request,
)
from pietto._project.project_execution_reader import ExecutionPayloads
from pietto._project.project_execution_source import (
    admit_postgres_source,
    admit_postgres_sources,
)
from pietto._project.project_refinement_enumeration import (
    RefinedExecutionRequest,
    Enumeration,
    refinement_state,
    verify_refined_execution,
)
from pietto._project.project_result_output import source_read_columns
from pietto._project.project_guard_runtime import (
    GuardedExecutionRequest,
    GuardRun,
    verify_guarded_execution,
)
from pietto._project.project_guard_context import (
    admit_postgres_guard_context,
    refresh_postgres_guard_context,
)

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
        self.guarded_request = (
            request if type(request) is GuardedExecutionRequest else None
        )
        self._owned_guarded_request = self.guarded_request
        if self.guarded_request is not None:
            verify_guarded_execution(self.guarded_request)
            request = self.guarded_request.execution
        self.refined_request = (
            request if type(request) is RefinedExecutionRequest else None
        )
        if (
            self.guarded_request is not None
            and self.guarded_request.program.refinement is not None
        ):
            self.refined_request = RefinedExecutionRequest(
                self.guarded_request.execution, self.guarded_request.program.refinement
            )
        self._owned_refined_request = self.refined_request
        if self.refined_request is not None:
            verify_refined_execution(
                self.refined_request, _guarded=self.guarded_request
            )
            self._refined_state = refinement_state(self.refined_request.refinement)
            request = self.refined_request.execution
        else:
            self._refined_state = None
        if self.guarded_request is None:
            verify_execution_request(request)
        self.request = cast(ExecutionRequest, request)
        if type(self.request.access) is not PostgresAccess:
            raise ExecutionError("EXECUTION_TARGET")
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
        self.source_admissions = None
        self._owned_admissions = None
        self.enumeration = None
        self._owned_enumeration = None
        self.last_page = None
        self.guards = self._owned_guards = None
        self._guard_context: Any = None
        self._guard_transaction: object | None = None
        self.guard_events = []
        self._guard_control: Any = None
        self._guard_bytes = 0

    def _verify(self):
        if self.guarded_request is None:
            verify_execution_request(self.request)
        else:
            if (
                self.guarded_request is not self._owned_guarded_request
                or self.guarded_request.execution is not self.request
                or self.guards is not self._owned_guards
            ):
                raise ExecutionError("GUARD_RESOURCE_IDENTITY")
            verify_guarded_execution(self.guarded_request)
            if self.guards is not None:
                self.guards.verify(self)
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

        if (
            self.refined_request is not self._owned_refined_request
            or self.source_admissions is not self._owned_admissions
            or self.enumeration is not self._owned_enumeration
        ):
            raise ExecutionError("REFINEMENT_RESOURCE_IDENTITY")
        if self.refined_request is not None:
            verify_refined_execution(
                self.refined_request, _guarded=self.guarded_request
            )
            if (
                self.refined_request.execution is not self.request
                or refinement_state(self.refined_request.refinement)
                != self._refined_state
            ):
                raise ExecutionError("REFINEMENT_REQUEST_CHANGED")
            if self.source_admissions is not None:
                self.source_admissions.verify(
                    self._connection,
                    self.refined_request.refinement.sources,
                    source_read_columns(self.refined_request.refinement.output),
                )
        if self.guards is not None:
            refresh_postgres_guard_context(self)

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
            if self.refined_request is not None:
                refined = self.refined_request.refinement
                self.source_admissions = admit_postgres_sources(
                    connection,
                    refined.sources,
                    source_read_columns(refined.output),
                    role=row[0],
                    session_id=self.session_id,
                )
                self._owned_admissions = self.source_admissions
            if self.guarded_request is not None:
                context = admit_postgres_guard_context(
                    self, self.guarded_request.program
                )
                self.guards = GuardRun(self.guarded_request, context)
                self._owned_guards = self.guards
                if context.separate_allowed:
                    self._fulfill_separate_guards()
            if self.refined_request is not None:
                self.enumeration = Enumeration(
                    self.refined_request.refinement,
                    self.source_admissions,
                    limits=self.request.limits,
                    _guards=self.guards,
                )
                self._owned_enumeration = self.enumeration
            self._remaining()
            self._delivery = "OPEN"
            return self
        except BaseException as error:
            if self._primary is None:
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
        if self.refined_request is not None:
            return self._next_refined_page()
        phase = "execute" if not self._submitted else "read"
        try:
            self._verify()
            # Binding checks can take time; apply the existing control checkpoint
            # after them and before submitting the immutable accepted tuple.
            guarded_native = None
            if not self._submitted and self.guards is not None:
                guarded_native = self.guards.prepare_submission(self)
                arguments = guarded_native.arguments
            else:
                arguments = (
                    execution_arguments(self.request) if not self._submitted else ()
                )
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
                self._remaining()
                if self._cancel.is_set():
                    raise ExecutionError("EXECUTION_CANCELED")
                self._cursor.execute(
                    (
                        guarded_native.sql
                        if guarded_native is not None
                        else self.request.artifact.rendered.sql
                    ).decode("utf-8"),
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
                description = self._cursor.description
                if self.guards is not None:
                    if self.guards.native is None:
                        raise ExecutionError("GUARD_SUBMISSION_MISSING")
                    phase = "guard"
                    self._remaining()
                    if self._cancel.is_set():
                        raise ExecutionError("EXECUTION_CANCELED")
                    header = (
                        self._cursor.fetchone()
                        if self.guards.native.statement.kind == "combined"
                        else None
                    )
                    refresh_postgres_guard_context(self)
                    description = self.guards.accept_header(
                        self, tuple(description), header
                    )
                    self.guard_events.append(("status_consumed", self.guards.states))
                self._payloads = ExecutionPayloads(self.request, description)
            self._remaining()
            if self._cancel.is_set():
                raise ExecutionError("EXECUTION_CANCELED")
            phase = "read"
            rows = self._cursor.fetchmany(self.request.limits.batch_rows)
            if self.guards is not None:
                rows = self.guards.public_rows(self, rows)
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
                if (
                    self._payloads.bytes + self._guard_bytes
                    > self.request.limits.max_bytes
                ):
                    raise ExecutionError("GUARD_RESOURCE_LIMIT")
                if self.guards is not None:
                    refresh_postgres_guard_context(self)
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

    def _fulfill_separate_guards(self):
        if self.guards is None or not self.guards.context.separate_allowed:
            raise ExecutionError("GUARD_SEPARATE_CONTEXT")
        if all(s == "STATIC" for s in self.guards.states):
            self.guards.require_fulfilled(self)
            return
        native = self.guards.prepare_submission(self)
        self._remaining()
        if self._cancel.is_set():
            raise ExecutionError("EXECUTION_CANCELED")
        self._cursor = self._owned_cursor = self._connection.cursor()
        self.guard_events.append(("guard_statement_open", self.attempt))
        try:
            self._remaining()
            if self._cancel.is_set():
                raise ExecutionError("EXECUTION_CANCELED")
            self._cursor.execute(
                native.sql.decode("utf-8"), native.arguments, prepare=True
            )
            metadata = tuple(self._cursor.description)
            rows = tuple(tuple(row) for row in self._cursor.fetchmany(2))
            if len(rows) != 1 or self._cursor.fetchone() is not None:
                raise ExecutionError("GUARD_NATIVE_TERMINAL")
            refresh_postgres_guard_context(self)
            self.guards.accept_guard_result(self, metadata, rows, terminal="NORMAL")
            self.guard_events.append(("guard_terminal", self.guards.states))
            self._cursor.close()
            self._cursor = self._owned_cursor = None
        except BaseException as error:
            if self._primary is None:
                self._primary = failure(error, "guard")
            raise
        self._remaining()
        if self._cancel.is_set():
            raise ExecutionError("EXECUTION_CANCELED")

    def _next_refined_page(self):
        phase = "execute"
        batch = None
        try:
            self._verify()
            if self._cancel.is_set():
                raise ExecutionError("EXECUTION_CANCELED")
            self._remaining()
            if self.enumeration is None:
                raise ExecutionError("REFINEMENT_ENUMERATION")
            while True:
                if self.enumeration.progress[2]:
                    self._source = "EOF"
                    self._delivery = "COMPLETE"
                    self._finish(True)
                    if self._primary is not None or self._cleanup_errors:
                        phase = "finalization"
                        raise ExecutionError("EXECUTION_FINALIZATION")
                    raise StopIteration
                page = self.enumeration.request_page()
                self.last_page = page
                # All reconstruction and verification precede this existing
                # cancellation/deadline checkpoint and native submission.
                remaining = self._remaining()
                if self._cancel.is_set():
                    raise ExecutionError("EXECUTION_CANCELED")
                with self._connection.cursor() as control:
                    control.execute(
                        "SELECT pg_catalog.set_config('statement_timeout',$1,true)",
                        (str(max(1, min(10000, math.ceil(remaining * 1000)))),),
                    )
                self._cursor = self._connection.cursor()
                self._owned_cursor = self._cursor
                self._source = "EXECUTING"
                self._remaining()
                if self._cancel.is_set():
                    raise ExecutionError("EXECUTION_CANCELED")
                self._cursor.execute(
                    page.native.sql.decode("utf-8"), page.native.arguments, prepare=True
                )
                self._submitted = True
                self._source = "READING"
                self.native_buffered_rows = getattr(
                    getattr(self._cursor, "pgresult", None), "ntuples", None
                )
                description = tuple(self._cursor.description)
                self.actual_metadata = tuple(
                    (c.name, c.type_code, c.null_ok) for c in description
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
                    for c in description
                )
                phase = "read"
                rows = tuple(tuple(row) for row in self._cursor.fetchall())
                if (
                    type(self.native_buffered_rows) is not int
                    or len(rows) != self.native_buffered_rows
                ):
                    raise ExecutionError("REFINEMENT_PAGE_NATIVE_COVERAGE")
                self._remaining()
                if self._cancel.is_set():
                    raise ExecutionError("EXECUTION_CANCELED")
                phase = "check"
                checked = self.enumeration.check_page(
                    page, description, rows, terminal="NORMAL"
                )
                if self._payloads is None:
                    self._payloads = ExecutionPayloads(
                        self.request, (), producer=checked.producer
                    )
                if checked.rows:
                    batch = self._payloads.accept(checked.rows)
                self._remaining()
                if self._cancel.is_set():
                    raise ExecutionError("EXECUTION_CANCELED")
                if self.guards is not None:
                    refresh_postgres_guard_context(self)
                    if (
                        self._guard_bytes + checked.raw_bytes + self.enumeration._bytes
                        > self.request.limits.max_bytes
                    ):
                        raise ExecutionError("GUARD_RESOURCE_LIMIT")
                phase = "statement_close"
                self._cursor.close()
                self._cursor = self._owned_cursor = None
                self._remaining()
                if self._cancel.is_set():
                    raise ExecutionError("EXECUTION_CANCELED")
                if self._started is None:
                    raise ExecutionError("EXECUTION_DEADLINE")
                self.enumeration.commit_page(
                    checked,
                    cancel_event=self._cancel,
                    deadline=self._started + self.request.limits.seconds,
                )
                if batch is not None:
                    return batch
                # An empty normally terminated page proves completion through
                # the same enumeration law; it is not an empty Arrow batch.
        except StopIteration:
            raise
        except BaseException as error:
            if self.enumeration is not None:
                self.enumeration.fail()
            if batch is not None:
                try:
                    batch.close()
                except BaseException as cleanup:
                    self._cleanup_errors.append(failure(cleanup, "batch_close"))
            if self._primary is None:
                self._primary = failure(error, phase)
            self._cancel_observed = (
                getattr(error, "sqlstate", None) == "57014"
                and self._cancel.is_set()
                and "due to user request"
                in str(getattr(getattr(error, "diag", None), "message_primary", ""))
            )
            if self._source != "EOF":
                self._source = (
                    "INCOMPLETE" if phase in ("check", "statement_close") else "FAILED"
                )
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
        if self._guard_control is not None:
            try:
                self._guard_control.close()
            except BaseException as error:
                self._cleanup_errors.append(failure(error, "guard_control_close"))
            self._guard_control = None
        if self.guards is not None:
            self.guards.close()
        if not commit and self.enumeration is not None:
            self.enumeration.fail()
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
