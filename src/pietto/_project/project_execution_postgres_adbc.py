"""Private PostgreSQL ADBC execution with checked source and exclusive handles."""

from __future__ import annotations

import math
import threading
import time
import uuid
from typing import Any, cast

from pietto._project.project_execution import (
    PostgresAccess,
    ExecutionError,
    ExecutionRequest,
    ExecutionFailure,
    ExecutionOutcome,
    request_state,
    verify_execution_request,
    execution_arguments,
)
from pietto._project.project_execution_postgres_adbc_native import (
    connect,
    read_control,
    NativeStatement,
    CONTEXT_SQL,
    failure,
)
from pietto._project.project_execution_postgres_adbc_context import (
    native_context,
    admit_sources,
    guard_context,
)
from pietto._project.project_postgres_source_assurance import qualify_sources
from pietto._project.project_execution_reader import (
    ExecutionPayloads,
    decode_native_rows,
)
from pietto._project.project_guard_runtime import (
    GuardedExecutionRequest,
    GuardRun,
    verify_guarded_execution,
)
from pietto._project.project_refinement_enumeration import (
    RefinedExecutionRequest,
    Enumeration,
    refinement_state,
    verify_refined_execution,
    atom,
    _size,
)
from pietto._project.project_result_output import source_read_columns

__all__: tuple[str, ...] = ()


class PostgresADBCExecution:
    def __init__(self, request):
        if type(request) not in (
            ExecutionRequest,
            GuardedExecutionRequest,
            RefinedExecutionRequest,
        ):
            raise ExecutionError("EXECUTION_REQUEST")
        self.guarded_request = (
            request if type(request) is GuardedExecutionRequest else None
        )
        if self.guarded_request is not None:
            request = request.execution
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
        if self.refined_request is not None:
            request = self.refined_request.execution
        if type(request) is not ExecutionRequest:
            raise ExecutionError("EXECUTION_REQUEST")
        request = cast(ExecutionRequest, request)
        if (
            type(request.access) is not PostgresAccess
            or request.route != "postgres_adbc"
            or request.output is None
        ):
            raise ExecutionError("EXECUTION_TARGET")
        self.request = self._owned_request = request
        self._captured = request_state(request)
        self._owned_guarded_request = self.guarded_request
        self._owned_refined_request = self.refined_request
        self._refined_state = (
            None
            if self.refined_request is None
            else refinement_state(self.refined_request.refinement)
        )
        self.requirements = (
            self.refined_request.refinement.sources
            if self.refined_request is not None
            else ()
            if request.source_requirement is None
            else (request.source_requirement,)
        )
        self.attempt = uuid.uuid4().hex
        self._database: Any = None
        self._owned_database: Any = None
        self._connection: Any = None
        self._owned_connection: Any = None
        self._manager: Any = None
        self._arrow: Any = None
        self._active: Any = None
        self._statement: Any = None
        self._statements: list[Any] = []
        self._gate = threading.RLock()
        self._cancel = threading.Event()
        self._timer: Any = None
        self._started: Any = None
        self._closed = self._submitted = self._finalizing = self._retired = False
        self._unsafe_protocol = False
        self._copy_checkpoint: Any = None
        self._copy_status: Any = None
        self._source = self._transaction = self._delivery = self._cleanup = (
            "NOT_STARTED"
        )
        self._primary: Any = None
        self._cleanup_errors: list[Any] = []
        self._cancel_sent = self._cancel_observed = self.deadline_expired = False
        self.control_events: list[Any] = []
        self.guard_events: list[Any] = []
        self.context: Any = None
        self._initial_context: Any = None
        self._context_native: Any = None
        self.session_id: Any = None
        self.environment: Any = None
        self._qualification: Any = None
        self._owned_qualification: Any = None
        self.source_admissions: Any = None
        self._owned_admissions: Any = None
        self._guard_context: Any = None
        self._guard_transaction: Any = None
        self._guard_sources: Any = None
        self.guards: Any = None
        self._owned_guards: Any = None
        self.enumeration: Any = None
        self._owned_enumeration: Any = None
        self.last_page: Any = None
        self._payloads: Any = None
        self._public_metadata: Any = None
        self.actual_metadata: Any = None
        self._internal_bytes = self._guard_bytes = 0

    def _remaining(self):
        if self._started is None:
            return float(self.request.limits.seconds)
        value = self.request.limits.seconds - (time.monotonic() - self._started)
        if value <= 0:
            self.deadline_expired = True
            self._cancel.set()
            raise ExecutionError("EXECUTION_DEADLINE")
        return value

    def _checkpoint(self):
        if self._finalizing:
            return
        if self._retired:
            raise ExecutionError("EXECUTION_RETIRED")
        if self._cancel.is_set():
            raise ExecutionError("EXECUTION_CANCELED")
        self._remaining()

    def _check_connection(self, *, completed_copy=None):
        from importlib import import_module

        manager = import_module("adbc_driver_manager")
        if (
            type(self._connection) is not manager.AdbcConnection
            or type(self._database) is not manager.AdbcDatabase
            or self._connection is not self._owned_connection
            or self._database is not self._owned_database
            or self._closed
        ):
            raise ExecutionError("POSTGRES_ADBC_CONNECTION_IDENTITY")
        status = self._connection.get_option("adbc.postgresql.transaction_status")
        allowed_active = (
            completed_copy is not None
            and completed_copy is self._statement
            and type(completed_copy) is NativeStatement
            and completed_copy.owner is self
            and completed_copy.copy is True
            and completed_copy.terminal == "NORMAL"
            and completed_copy.reader is None
            and completed_copy.reader_close == "RETURNED"
            and self._active is None
        )
        if status != "intrans" and not (status == "active" and allowed_active):
            raise ExecutionError("POSTGRES_ADBC_TRANSACTION_STATUS")
        return status

    def _charge_internal(self, rows, buffers=0):
        amount = sum(
            sum(_size(v, self.request.limits.max_bytes) + 8 for v in row)
            for row in rows
        )
        self._internal_bytes += max(amount, buffers)
        if self._internal_bytes + self._guard_bytes > self.request.limits.max_bytes:
            raise ExecutionError("EXECUTION_RESOURCE_LIMIT")
        self._checkpoint()

    def _catalog_read(self, sql, arguments):
        tags = tuple("Int" if type(v) is int else "Text" for v in arguments)
        # Arguments originate solely in the fixed catalog protocol (OID/names).
        if any(type(v) not in (int, str) for v in arguments):
            raise ExecutionError("POSTGRES_SOURCE_CATALOG_ARGUMENT")
        return read_control(self, sql, arguments, tags)

    def _refresh(self):
        self._checkpoint()
        pending = self._copy_checkpoint
        self._copy_checkpoint = None
        before = self._check_connection(completed_copy=pending)
        if self._active is not None:
            raise ExecutionError("POSTGRES_ADBC_ACTIVE_READER")
        # PG's COPY reader has already checked CommandComplete. This fixed
        # non-COPY context command completes the remaining ReadyForQuery drain;
        # it never runs with a live Arrow stream or on an error/partial terminal.
        current, reply = native_context(self)
        if current != self.context:
            raise ExecutionError("POSTGRES_ADBC_TRANSACTION_CHANGED")
        after = self._check_connection()
        if pending is not None:
            self._copy_status = (before, after)
        self._context_native = reply
        self._checkpoint()

    def _verify(self):
        if (
            self.request is not self._owned_request
            or request_state(self.request) != self._captured
        ):
            raise ExecutionError("EXECUTION_REQUEST_CHANGED")
        if (
            self.guarded_request is not self._owned_guarded_request
            or self.refined_request is not self._owned_refined_request
        ):
            raise ExecutionError("EXECUTION_REQUEST_CHANGED")
        if self.guarded_request is None:
            verify_execution_request(self.request)
        else:
            verify_guarded_execution(self.guarded_request)
        if self.refined_request is not None:
            verify_refined_execution(
                self.refined_request, _guarded=self.guarded_request
            )
            if refinement_state(self.refined_request.refinement) != self._refined_state:
                raise ExecutionError("REFINEMENT_REQUEST_CHANGED")
        self._checkpoint()
        if self._transaction == "OPEN":
            self._refresh()
            self._qualification.verify(self)
        if (
            self.source_admissions is not self._owned_admissions
            or self.enumeration is not self._owned_enumeration
            or self.guards is not self._owned_guards
        ):
            raise ExecutionError("EXECUTION_OWNER_CHANGED")
        if self.source_admissions is not None:
            self.source_admissions.verify(
                self._connection,
                self.requirements,
                tuple(
                    source_read_columns(self.request.output)[r.source.position]
                    for r in self.requirements
                ),
            )
        if self.guards is not None:
            self.guards.verify(self)
        self._checkpoint()

    def open(self):
        if self._started is not None or self._closed:
            raise ExecutionError("EXECUTION_REUSE")
        self._started = time.monotonic()
        try:
            self._verify()
            self._timer = threading.Timer(self.request.limits.seconds, self._deadline)
            self._timer.name = "pietto-adbc-deadline-" + self.attempt
            self._timer.start()
            self.control_events.append(("thread_registered", self._timer.name))
            connect(self)
            strength = (
                "REPEATABLE READ"
                if self.request.isolation == "stable"
                else "SERIALIZABLE"
            )
            self._transaction = "UNKNOWN"
            read_control(
                self, "BEGIN ISOLATION LEVEL " + strength + " READ ONLY", maximum=0
            )
            self._transaction = "OPEN"
            self.context, self._context_native = native_context(self)
            self._initial_context = self.context
            self.session_id = self.context[6]
            self.environment = (
                self.request.artifact.request.release,
                self.context[8],
                True,
                "UTF8",
            )
            qualify_sources(self)
            if self.requirements:
                self.source_admissions = self._owned_admissions = admit_sources(
                    self, self.requirements
                )
            if self.guarded_request is not None:
                self.guards = self._owned_guards = GuardRun(
                    self.guarded_request, guard_context(self)
                )
                if self._guard_context.separate_allowed:
                    self._fulfill_guards()
            if self.refined_request is not None:
                self.enumeration = self._owned_enumeration = Enumeration(
                    self.refined_request.refinement,
                    self.source_admissions,
                    limits=self.request.limits,
                    _guards=self.guards,
                )
            self._verify()
            self._delivery = "OPEN"
            return self
        except BaseException as error:
            self._failed(error, "admission")
            raise

    def _parameters(self, purpose):
        if purpose == "page":
            if self.refined_request is None:
                raise ExecutionError("REFINEMENT_REQUEST_CHANGED")
            page = self.last_page
            native = page.native
            coordinates = (
                self.refined_request.refinement.units[-1].order_coordinates
                + self.refined_request.refinement.units[-1].coordinates
            )
            kinds = {}
            for use in native.uses:
                kinds[use.index] = (
                    use.owner.tag.value
                    if use.domain == "original"
                    else "Int"
                    if page.frontier is None or use.owner == len(coordinates)
                    else coordinates[use.owner].tag
                )
        elif self.guards is not None:
            native = self.guards.native
            kinds = {}
            for use in native.uses:
                kinds[use.index] = (
                    use.owner.tag.value if use.domain == "original" else "Int"
                )
        else:
            artifact = self.request.artifact
            arguments = execution_arguments(self.request)
            kinds = {u.server_index: u.slot.tag.value for u in artifact.parameter_uses}
            return (
                artifact.rendered.sql,
                arguments,
                tuple(kinds[i + 1] for i in range(len(arguments))),
            )
        return (
            native.sql,
            native.arguments,
            tuple(kinds[i + 1] for i in range(len(native.arguments))),
        )

    def _verify_submission(self, statement):
        if statement is not self._statement:
            raise ExecutionError("POSTGRES_ADBC_STATEMENT_OWNER")
        if statement.purpose == "page":
            self.enumeration._verify_page(self.last_page)
        elif self.guards is not None:
            from pietto._project.project_guard_verification import verify_native_guard

            verify_native_guard(self.guards.native)
        expected = self._parameters(statement.purpose)
        if (
            statement.sql != expected[0]
            or tuple(map(atom, statement.arguments)) != tuple(map(atom, expected[1]))
            or statement.tags != expected[2]
        ):
            raise ExecutionError("POSTGRES_ADBC_SUBMISSION_CORRESPONDENCE")
        self._checkpoint()

    def _submit(self, purpose, maximum):
        self._verify()
        ms = max(1, min(10000, math.ceil(self._remaining() * 1000)))
        read_control(
            self,
            "SELECT pg_catalog.set_config('statement_timeout',$1,true)",
            (str(ms),),
            ("Text",),
            maximum=1,
        )
        sql, arguments, tags = self._parameters(purpose)
        self._statement = NativeStatement(
            self, sql, arguments, tags, purpose, copy=True
        )
        self._source = "EXECUTING"
        metadata = self._statement.execute(maximum)
        self._copy_checkpoint = self._statement
        self._source = "READING"
        self._submitted = True
        self.actual_metadata = metadata
        self._refresh()
        return metadata

    def _fulfill_guards(self):
        if all(s == "STATIC" for s in self.guards.states):
            self.guards.require_fulfilled(self)
            return
        self.guards.prepare_submission(self)
        metadata = self._submit("guard", 1)
        rows = self._statement.fetch(2)
        if not self._statement.exhausted:
            raise ExecutionError("GUARD_NATIVE_TERMINAL")
        self._charge_internal(rows, self._statement.bytes)
        self.guards.accept_guard_result(self, metadata, rows, terminal="NORMAL")
        self._statement.close()
        self._statement = None
        self._submitted = False

    def __enter__(self):
        return self.open()

    def __iter__(self):
        return self

    def __next__(self):
        if self._closed:
            raise StopIteration
        if self._retired:
            raise ExecutionError("EXECUTION_RETIRED")
        if self._started is None:
            self.open()
        batch = None
        try:
            self._verify()
            if self.enumeration is not None:
                return self._next_page()
            if self._statement is None:
                native = (
                    None
                    if self.guards is None
                    else self.guards.prepare_submission(self)
                )
                maximum = self.request.limits.max_rows + (
                    1
                    if native is not None and native.statement.kind == "combined"
                    else 0
                )
                metadata = self._submit("query", maximum)
                statement = cast(NativeStatement, self._statement)
                if self.guards is not None:
                    if native is None:
                        raise ExecutionError("GUARD_SUBMISSION_MISSING")
                    header = None
                    if native.statement.kind == "combined":
                        row = statement.fetch(1)
                        if len(row) != 1:
                            raise ExecutionError("GUARD_STATUS_ARITY")
                        header = row[0]
                    metadata = self.guards.accept_header(self, metadata, header)
                self._public_metadata = metadata
                producer, _ = decode_native_rows(
                    self.request.output, "postgres_adbc", metadata, ()
                )
                self._payloads = ExecutionPayloads(self.request, (), producer=producer)
            statement = self._statement
            if type(statement) is not NativeStatement:
                raise ExecutionError("POSTGRES_ADBC_STATEMENT_OWNER")
            rows = statement.fetch(self.request.limits.batch_rows)
            if self.guards is not None:
                rows = self.guards.public_rows(self, rows)
            if rows:
                _, decoded = decode_native_rows(
                    self.request.output, "postgres_adbc", self._public_metadata, rows
                )
                batch = self._payloads.accept(decoded)
                self._verify()
                self._check_total()
                return batch
            if not statement.exhausted:
                raise ExecutionError("POSTGRES_ADBC_READER_TERMINAL")
            self._source = "EOF"
            self._delivery = "COMPLETE"
            self._finish(True)
            if self._primary is not None or self._cleanup_errors:
                raise ExecutionError("EXECUTION_FINALIZATION")
            raise StopIteration
        except StopIteration:
            raise
        except BaseException as error:
            self._close_failed_batch(batch)
            self._failed(error, "query")
            raise

    def _close_failed_batch(self, batch):
        if batch is not None:
            try:
                batch.close()
            except BaseException as error:
                self._cleanup_errors.append(failure(error, "batch_close"))

    def _check_total(self, raw_bytes=0, statement=None):
        current = self._statement
        if (
            0 if self._payloads is None else self._payloads.bytes
        ) + self._internal_bytes + self._guard_bytes + raw_bytes + (
            0 if current is None or current is statement else current.bytes
        ) > self.request.limits.max_bytes:
            raise ExecutionError("EXECUTION_RESOURCE_LIMIT")
        self._checkpoint()

    def _next_page(self):
        batch = None
        try:
            while not self.enumeration.progress[2]:
                self.last_page = self.enumeration.request_page()
                metadata = self._submit("page", self.last_page.size)
                rows = self._statement.fetch(self.last_page.size + 1)
                if not self._statement.exhausted:
                    raise ExecutionError("REFINEMENT_PAGE_NATIVE_COVERAGE")
                self._charge_internal(rows, self._statement.bytes)
                checked = self.enumeration.check_page(
                    self.last_page, metadata, rows, terminal="NORMAL"
                )
                if self._payloads is None:
                    self._payloads = ExecutionPayloads(
                        self.request, (), producer=checked.producer
                    )
                if checked.rows:
                    batch = self._payloads.accept(checked.rows)
                self._verify()
                self._check_total()
                self._statement.close()
                self._statement = None
                self.enumeration.commit_page(
                    checked,
                    cancel_event=self._cancel,
                    deadline=self._started + self.request.limits.seconds,
                )
                if batch is not None:
                    return batch
            self._source = "EOF"
            self._delivery = "COMPLETE"
            self._finish(True)
            if self._primary is not None or self._cleanup_errors:
                raise ExecutionError("EXECUTION_FINALIZATION")
            raise StopIteration
        except BaseException:
            self._close_failed_batch(batch)
            raise

    def _failed(self, error, phase):
        if (
            self._unsafe_protocol
            or str(error)
            in (
                "POSTGRES_ADBC_TRANSACTION_CHANGED",
                "POSTGRES_ADBC_TRANSACTION_STATUS",
                "POSTGRES_ADBC_CONNECTION_IDENTITY",
            )
        ) and self._transaction == "OPEN":
            self._transaction = "UNKNOWN"
        if self._primary is None:
            self._primary = failure(error, phase)
        self._cancel_observed = self._cancel.is_set() and (
            "canceling statement due to user request" in str(error)
            or (
                self._manager is not None
                and getattr(error, "status_code", None)
                == self._manager.AdbcStatusCode.CANCELLED
            )
        )
        if self._source != "EOF":
            self._source = "FAILED"
        self._delivery = "FAILED"
        if self.enumeration is not None:
            self.enumeration.fail()
        self._finish(False)

    def _deadline(self):
        self.deadline_expired = True
        self.cancel()

    def cancel(self):
        self._cancel.set()
        with self._gate:
            statement = self._active
            if self._closed or statement is None or statement.native is None:
                return {
                    "requested": True,
                    "sent": False,
                    "observed": self._cancel_observed,
                    "late": self._closed,
                }
            try:
                # Pinned adbc.h explicitly permits concurrent StatementCancel;
                # close is serialized by this gate, unlike query/reader calls.
                statement.native.cancel()
                self._cancel_sent = True
                self.control_events.append(
                    ("native_cancel_returned", statement.purpose)
                )
            except BaseException as error:
                self._cleanup_errors.append(failure(error, "cancel"))
        return {
            "requested": True,
            "sent": self._cancel_sent,
            "observed": self._cancel_observed,
            "late": False,
        }

    @property
    def control_joined(self):
        return self._timer is None or not self._timer.is_alive()

    def _finish(self, commit):
        if self._closed:
            return
        self._retired = True
        self._finalizing = True
        try:
            if self._timer is not None:
                self._timer.cancel()
                if threading.current_thread() is not self._timer:
                    self._timer.join(timeout=12)
                if self._timer.is_alive():
                    self._cleanup_errors.append(
                        ExecutionFailure("control_join", "TimeoutError")
                    )
                    self._transaction = "UNKNOWN"
                    self._cleanup = "FAILED_REMOTE_UNOBSERVED"
                    return
            if self.guards is not None:
                self.guards.close()
            if not commit and self.enumeration is not None:
                self.enumeration.fail()
            for statement in tuple(self._statements):
                try:
                    statement.close()
                except BaseException as error:
                    self._cleanup_errors.append(failure(error, "statement_close"))
            if self._owned_connection is not None:
                if self._transaction == "OPEN":
                    try:
                        # Cleanup must identify the original native transaction
                        # even when verification/cancel failed before _refresh.
                        if self._initial_context is None:
                            raise ExecutionError(
                                "POSTGRES_ADBC_TRANSACTION_UNESTABLISHED"
                            )
                        self._check_connection()
                        _, contexts, _ = read_control(
                            self, CONTEXT_SQL, maximum=1, finalizing=True
                        )
                        if (
                            len(contexts) != 1
                            or len(contexts[0]) != 17
                            or tuple(map(atom, contexts[0]))
                            != tuple(map(atom, self._initial_context))
                        ):
                            raise ExecutionError("POSTGRES_ADBC_TRANSACTION_CHANGED")
                        self._check_connection()
                        read_control(
                            self,
                            "COMMIT" if commit else "ROLLBACK",
                            maximum=0,
                            finalizing=True,
                        )
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
            if self._owned_database is not None:
                try:
                    self._owned_database.close()
                except BaseException as error:
                    self._cleanup_errors.append(failure(error, "database_close"))
            self._closed = True
            self._cleanup = (
                "FAILED_REMOTE_UNOBSERVED"
                if self._cleanup_errors
                else "LOCAL_CLOSED_REMOTE_UNOBSERVED"
            )
        finally:
            self._finalizing = False

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
        p = self._payloads
        return ExecutionOutcome(
            self.attempt,
            self._source,
            self._transaction,
            self._delivery,
            self._cleanup,
            0 if p is None else p.rows,
            0 if p is None else p.batches,
            0 if p is None else p.bytes,
            self._primary,
            tuple(self._cleanup_errors),
            self._cancel.is_set(),
            self._cancel_sent,
            self._cancel_observed,
        )
