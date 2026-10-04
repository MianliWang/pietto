"""Private native MySQL execution over verified ordinary/guarded/refined requests."""

from __future__ import annotations

import math
import threading
import time
import uuid
from typing import Any, cast

from pietto._project.project_execution import (
    MySQLAccess,
    ExecutionRequest,
    ExecutionError,
    ExecutionOutcome,
    request_state,
    execution_arguments,
    verify_execution_request,
)
from pietto._project.project_execution_mysql_native import (
    connect,
    read_control,
    NativeStatement,
    failure,
    transport_state,
)
from pietto._project.project_execution_mysql_context import (
    native_context,
    native_epoch,
    qualify_sources,
    admit_sources,
    MySQLGuardContext,
)
from pietto._project.project_execution_mysql_control import MySQLControl
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
    _size,
    atom,
)

__all__: tuple[str, ...] = ()


class MySQLExecution:
    def __init__(self, request):
        from pietto._project.project_sql_emission import CompiledEmissionArtifact
        from pietto._project.project_guard_preparation import CompiledGuardedArtifact
        from pietto._project.project_execution import verify_execution_limits

        base = (
            request.execution
            if type(request) in (GuardedExecutionRequest, RefinedExecutionRequest)
            else request
        )
        if type(base) is not ExecutionRequest:
            raise ExecutionError("EXECUTION_REQUEST")
        compiled = type(base.artifact) in (
            CompiledEmissionArtifact,
            CompiledGuardedArtifact,
        )
        if compiled:
            verify_execution_limits(base.limits)
        self.guarded_request = (
            request if type(request) is GuardedExecutionRequest else None
        )
        if self.guarded_request is not None:
            if not compiled:
                verify_guarded_execution(request)
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
            if not compiled:
                verify_refined_execution(
                    self.refined_request, _guarded=self.guarded_request
                )
            request = self.refined_request.execution
        if self.guarded_request is None and not compiled:
            verify_execution_request(request)
        request = cast(ExecutionRequest, request)
        if type(request.access) is not MySQLAccess or request.output is None:
            raise ExecutionError("EXECUTION_TARGET")
        self.request = self._owned_request = request
        self._captured = request_state(request)
        self._owned_guarded_request, self._owned_refined_request = (
            self.guarded_request,
            self.refined_request,
        )
        self._refined_state = (
            None
            if self.refined_request is None
            else refinement_state(self.refined_request.refinement)
        )
        self.attempt = uuid.uuid4().hex
        self._connection: Any = None
        self._owned_connection: Any = None
        self._control_connection: Any = None
        self._owned_control_connection: Any = None
        self._transport: Any = None
        self._control_transport: Any = None
        self._connections: list[Any] = []
        self._controls: list[Any] = []
        self._statements: list[Any] = []
        self._statement: Any = None
        self._active: Any = None
        self._gate = threading.RLock()
        self._cancel = threading.Event()
        self._controller: Any = None
        self._started: Any = None
        self._closed = self._discarded = self._submitted = False
        self._source = self._transaction = self._delivery = self._cleanup = (
            "NOT_STARTED"
        )
        self._primary: Any = None
        self._cleanup_errors: list[Any] = []
        self.control_events: list[Any] = []
        self.guard_events: list[Any] = []
        self._cancel_sent = self._cancel_observed = self.deadline_expired = False
        self.session_id: Any = None
        self.context: Any = None
        self._epoch: Any = None
        self._initial_epoch: Any = None
        self.environment: Any = None
        self._qualification: Any = None
        self._owned_qualification: Any = None
        self._sources: tuple = ()
        self._source_schema: tuple = ()
        self.source_admissions: Any = None
        self._owned_admissions: Any = None
        self.enumeration: Any = None
        self._owned_enumeration: Any = None
        self.guards: Any = None
        self._owned_guards: Any = None
        self._guard_context: Any = None
        self._guard_transaction: Any = None
        self._guard_bytes = self._internal_bytes = 0
        self._payloads: Any = None
        self._public_metadata: Any = None
        self.actual_metadata: Any = None
        self.last_page: Any = None

    def _remaining(self):
        remaining = (
            self.request.limits.seconds
            if self._started is None
            else self.request.limits.seconds - (time.monotonic() - self._started)
        )
        if remaining <= 0:
            self.deadline_expired = True
            self._cancel.set()
            raise TimeoutError("EXECUTION_DEADLINE")
        return remaining

    def _timeout(self):
        return max(1, min(10, math.ceil(self._remaining())))

    def _checkpoint(self):
        if self._cancel.is_set():
            raise ExecutionError("EXECUTION_CANCELED")
        self._remaining()

    def _charge_internal(self, rows):
        charge = sum(
            _size(v, self.request.limits.max_bytes) + 8 for row in rows for v in row
        )
        with self._gate:
            self._internal_bytes += charge
            if self._internal_bytes + self._guard_bytes > self.request.limits.max_bytes:
                raise ExecutionError("EXECUTION_RESOURCE_LIMIT")

    def _begin_operation(self, statement):
        with self._gate:
            self._checkpoint()
            if self._active is not None or self._closed or self._discarded:
                raise ExecutionError("MYSQL_OPERATION_LIFETIME")
            self._active = statement

    def _end_operation(self, statement):
        with self._gate:
            if self._active is not statement:
                raise ExecutionError("MYSQL_OPERATION_IDENTITY")
            self._active = None

    def _verify_lifetime(self):
        if (
            self._transaction == "OPEN"
            and self._owned_connection is not None
            and (
                not self._owned_connection.in_transaction
                or self._transport != transport_state(self._owned_connection)
            )
        ):
            self._transaction = "UNKNOWN"
            self._discarded = True
        if (
            self._closed
            or self._discarded
            or self._transaction != "OPEN"
            or self._connection is not self._owned_connection
            or self._connection is None
            or not self._connection.in_transaction
            or self._connection.connection_id != self.session_id
            or self._transport != transport_state(self._connection)
            or self._control_connection is not self._owned_control_connection
            or self._control_transport != transport_state(self._control_connection)
        ):
            raise ExecutionError("MYSQL_TRANSACTION_LIFETIME")
        if self._qualification is not None:
            self._qualification.verify(self)

    def _refresh(self):
        self._verify_lifetime()
        with self._gate:
            try:
                epoch = native_epoch(self, control=True)
            except BaseException:
                self._transaction = "UNKNOWN"
                self._discarded = True
                raise
            if epoch != self._epoch:
                self._transaction = "UNKNOWN"
                self._discarded = True
                raise ExecutionError("MYSQL_TRANSACTION_CHANGED")
        if not self._connection.unread_result and native_context(self) != self.context:
            raise ExecutionError("MYSQL_CONTEXT_CHANGED")
        self._checkpoint()

    def _verify(self):
        from pietto._project.project_execution import verify_compiled_owner

        verify_compiled_owner(self)
        if (
            self.request is not self._owned_request
            or request_state(self.request) != self._captured
            or self.guarded_request is not self._owned_guarded_request
            or self.refined_request is not self._owned_refined_request
            or self.source_admissions is not self._owned_admissions
            or self.enumeration is not self._owned_enumeration
            or self.guards is not self._owned_guards
            or self._qualification is not self._owned_qualification
            or self._connection is not self._owned_connection
        ):
            raise ExecutionError("EXECUTION_RESOURCE_IDENTITY")
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
        if self._transaction == "OPEN":
            self._refresh()
        if self.guards is not None:
            self.guards.verify(self)
        self._checkpoint()

    def open(self):
        if self._started is not None or self._closed:
            raise ExecutionError("EXECUTION_REUSE")
        self._started = time.monotonic()
        try:
            self._verify()
            self._controller = MySQLControl(self)
            self._controller.start()
            connection = connect(self)
            self.session_id = connection.connection_id
            self.control_events.append(("data_session", self.session_id))
            control = connect(self, control=True)
            self._transport = transport_state(connection)
            self._control_transport = transport_state(control)
            read_control(self, "SET SESSION time_zone='+00:00'")
            strength = (
                "REPEATABLE READ"
                if self.request.isolation == "stable"
                else "SERIALIZABLE"
            )
            read_control(self, "SET SESSION TRANSACTION ISOLATION LEVEL " + strength)
            self._transaction = "UNKNOWN"
            read_control(
                self,
                "START TRANSACTION "
                + (
                    "WITH CONSISTENT SNAPSHOT, "
                    if self.request.isolation == "stable"
                    else ""
                )
                + "READ ONLY",
            )
            self._transaction = "OPEN"
            self.context = native_context(self)
            self._epoch = native_epoch(self)
            self._initial_epoch = self._epoch
            self.environment = (
                self.context[0],
                strength.lower(),
                True,
                "utf8mb4",
                self.context[13],
                self.context[2],
            )
            self._sources, self._source_schema = qualify_sources(self)
            if self.refined_request is not None:
                self.source_admissions = self._owned_admissions = admit_sources(
                    self, self.refined_request.refinement.sources
                )
            elif self.request.source_requirement is not None:
                if len(self.request.artifact.request.sources) != 1:
                    raise ExecutionError("SOURCE_VECTOR")
                self.source_admissions = self._owned_admissions = admit_sources(
                    self, (self.request.source_requirement,)
                )
            if self.guarded_request is not None:
                self._guard_transaction = object()
                self._guard_context = MySQLGuardContext(
                    self.guarded_request.program,
                    self,
                    connection,
                    self._guard_transaction,
                    self._epoch,
                    self.session_id,
                    cast(MySQLAccess, self.request.access).account,
                    self.environment,
                    self._sources,
                )
                self.guards = self._owned_guards = GuardRun(
                    self.guarded_request, self._guard_context
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

    def _verify_submission(self, statement):
        if statement is not self._statement:
            raise ExecutionError("MYSQL_STATEMENT_OWNER")
        if statement.purpose == "page":
            if self.enumeration is None or self.last_page is None:
                raise ExecutionError("REFINEMENT_PAGE_IDENTITY")
            self.enumeration._verify_page(self.last_page)
            native = self.last_page.native
            sql, arguments = native.sql, native.arguments
        elif self.guards is not None:
            from pietto._project.project_guard_verification import verify_native_guard

            native = self.guards.native
            if native is None:
                raise ExecutionError("GUARD_SUBMISSION_MISSING")
            verify_native_guard(native)
            expected = "guard" if native.statement.kind == "guard" else "query"
            if statement.purpose != expected:
                raise ExecutionError("GUARD_SUBMISSION_KIND")
            sql, arguments = native.sql, native.arguments
        else:
            if statement.purpose != "query":
                raise ExecutionError("MYSQL_STATEMENT_PURPOSE")
            sql, arguments = (
                self.request.artifact.rendered.sql,
                execution_arguments(self.request),
            )
        if statement.sql != sql or tuple(atom(v) for v in statement.arguments) != tuple(
            atom(v) for v in arguments
        ):
            raise ExecutionError("MYSQL_SUBMISSION_CORRESPONDENCE")
        self._checkpoint()

    def _submit(self, sql, arguments, purpose):
        self._verify()
        self._statement = NativeStatement(self, sql, arguments, purpose)
        self._source = "EXECUTING"
        metadata = self._statement.execute()
        self.actual_metadata = metadata
        self._submitted = True
        self._source = "READING"
        return metadata

    def _complete_rows(self, statement, maximum):
        rows = []
        while statement.terminal is None:
            batch = statement.fetch(
                min(self.request.limits.batch_rows, maximum + 1 - len(rows))
            )
            rows.extend(batch)
            self._charge_internal(batch)
            if len(rows) > maximum:
                raise ExecutionError("MYSQL_ROWSET_ARITY")
        return tuple(rows)

    def _fulfill_guards(self):
        if all(s == "STATIC" for s in self.guards.states):
            self.guards.require_fulfilled(self)
            return
        native = self.guards.prepare_submission(self)
        metadata = self._submit(native.sql, native.arguments, "guard")
        rows = self._complete_rows(self._statement, 1)
        self._refresh()
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
                sql = (
                    self.request.artifact.rendered.sql if native is None else native.sql
                )
                arguments = (
                    execution_arguments(self.request)
                    if native is None
                    else native.arguments
                )
                metadata = self._submit(sql, arguments, "query")
                if self.guards is not None:
                    if native is None or type(self._statement) is not NativeStatement:
                        raise ExecutionError("GUARD_SUBMISSION_MISSING")
                    header = None
                    if native.statement.kind == "combined":
                        header_rows = self._statement.fetch(1)
                        if len(header_rows) != 1:
                            raise ExecutionError("GUARD_STATUS_ARITY")
                        header = header_rows[0]
                    metadata = self.guards.accept_header(self, metadata, header)
                self._public_metadata = metadata
                producer, _ = decode_native_rows(
                    self.request.output, "mysql_rows", metadata, ()
                )
                self._payloads = ExecutionPayloads(self.request, (), producer=producer)
            statement = self._statement
            if type(statement) is not NativeStatement:
                raise ExecutionError("MYSQL_STATEMENT_OWNER")
            while statement.terminal is None:
                rows = statement.fetch(self.request.limits.batch_rows)
                self._charge_internal(rows)
                if self.guards is not None:
                    rows = self.guards.public_rows(self, rows)
                if rows:
                    _, decoded = decode_native_rows(
                        self.request.output, "mysql_rows", self._public_metadata, rows
                    )
                    batch = self._payloads.accept(decoded)
                    self._verify()
                    self._check_total()
                    return batch
                self._checkpoint()
            self._refresh()
            self._source, self._delivery = "EOF", "COMPLETE"
            self._finish(True)
            if self._primary is not None or self._cleanup_errors:
                raise ExecutionError("EXECUTION_FINALIZATION")
            raise StopIteration
        except StopIteration:
            raise
        except BaseException as error:
            if batch is not None:
                try:
                    batch.close()
                except BaseException as cleanup:
                    self._cleanup_errors.append(failure(cleanup, "batch_close"))
            self._failed(error, "query")
            raise

    def _check_total(self):
        if (
            self._payloads.bytes + self._guard_bytes + self._internal_bytes
            > self.request.limits.max_bytes
        ):
            raise ExecutionError("EXECUTION_RESOURCE_LIMIT")

    def _next_page(self):
        batch = None
        try:
            while not self.enumeration.progress[2]:
                page = self.enumeration.request_page()
                self.last_page = page
                metadata = self._submit(page.native.sql, page.native.arguments, "page")
                rows = self._complete_rows(self._statement, page.size)
                self._refresh()
                checked = self.enumeration.check_page(
                    page, metadata, rows, terminal="NORMAL"
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
                    self._checkpoint()
                    return batch
            self._source, self._delivery = "EOF", "COMPLETE"
            self._finish(True)
            if self._primary is not None or self._cleanup_errors:
                raise ExecutionError("EXECUTION_FINALIZATION")
            raise StopIteration
        except BaseException:
            if batch is not None:
                batch.close()
            raise

    def _failed(self, error, phase):
        if self._primary is None:
            self._primary = failure(error, phase)
        if self._cancel_sent and getattr(error, "errno", None) == 1317:
            self._cancel_observed = True
        if self._source != "EOF":
            self._source = "INCOMPLETE"
        self._delivery = "FAILED"
        self._finish(False)

    def cancel(self):
        self._cancel.set()
        if self._controller is not None:
            self._controller.wake.set()
        return {
            "requested": True,
            "sent": self._cancel_sent,
            "observed": self._cancel_observed,
            "late": self._closed,
        }

    @property
    def control_joined(self):
        return self._controller is None or not self._controller.thread.is_alive()

    def _finish(self, commit):
        if self._closed:
            return
        if self._controller is not None:
            try:
                self._controller.join()
            except BaseException as error:
                self._cleanup_errors.append(failure(error, "control_join"))
        with self._gate:
            if self.guards is not None:
                self.guards.close()
            if not commit and self.enumeration is not None:
                self.enumeration.fail()
            connection = self._owned_connection
            discard = (
                self._discarded
                or self._active is not None
                or (connection is not None and connection.unread_result)
            )
            for statement in self._statements:
                try:
                    statement.close(discard=discard)
                except BaseException as error:
                    self._cleanup_errors.append(failure(error, "statement_close"))
                    discard = True
            if connection is not None and self._transaction == "OPEN":
                if discard:
                    self._transaction = "UNKNOWN"
                else:
                    try:
                        from pietto._project.project_execution_mysql_context import (
                            EPOCH_SQL,
                        )

                        # Check the originally admitted transaction even after a
                        # prior failure; cleanup must not act on its replacement.
                        if (
                            self._initial_epoch is None
                            or self._epoch != self._initial_epoch
                            or self._connection is not connection
                            or not connection.in_transaction
                            or transport_state(connection) != self._transport
                            or self._owned_control_connection is None
                            or self._control_connection
                            is not self._owned_control_connection
                            or transport_state(self._owned_control_connection)
                            != self._control_transport
                        ):
                            raise ExecutionError("MYSQL_TRANSACTION_CHANGED")
                        _, observed = read_control(
                            self,
                            EPOCH_SQL,
                            (self.session_id, self.request.access.user),
                            connection=self._owned_control_connection,
                            cleanup=True,
                        )
                        if (
                            len(observed) != 1
                            or tuple(map(type, observed[0]))
                            != tuple(map(type, self._initial_epoch))
                            or observed[0] != self._initial_epoch
                        ):
                            raise ExecutionError("MYSQL_TRANSACTION_CHANGED")
                        # Cancellation and commit publication share the same gate.
                        if commit:
                            self._checkpoint()
                        read_control(
                            self, "COMMIT" if commit else "ROLLBACK", cleanup=True
                        )
                        self._transaction = "COMMIT_ACK" if commit else "ROLLBACK_ACK"
                    except BaseException as error:
                        self._transaction = "UNKNOWN"
                        if self._primary is None:
                            self._primary = failure(error, "transaction")
                        else:
                            self._cleanup_errors.append(failure(error, "transaction"))
            if commit and self._transaction == "COMMIT_ACK":
                try:
                    self._checkpoint()
                except BaseException as error:
                    # A real ACK stays an ACK; late completion is separately
                    # refused after the potentially blocking COMMIT call.
                    if self._primary is None:
                        self._primary = failure(error, "completion")
                    self._delivery = "FAILED"
            for cursor in tuple(self._controls):
                try:
                    cursor.close()
                except BaseException as error:
                    self._cleanup_errors.append(failure(error, "control_close"))
            for owned in reversed(self._connections):
                try:
                    owned.shutdown()
                except BaseException as error:
                    self._cleanup_errors.append(failure(error, "connection_shutdown"))
            self._closed = True
            self._cleanup = (
                "FAILED" if self._cleanup_errors else "LOCAL_CLOSED_REMOTE_UNOBSERVED"
            )

    def close(self):
        if not self._closed:
            if self._source != "EOF":
                self._source = "EARLY_CLOSE"
            if self._delivery not in ("FAILED", "COMPLETE"):
                self._delivery = "INCOMPLETE"
            self._finish(False)

    def __exit__(self, kind, error, traceback):
        if error is not None and self._primary is None:
            self._primary = failure(error, "consumer")
            self._delivery = "FAILED"
        self.close()
        return False

    @property
    def assurance(self):
        q = self._qualification
        return {
            "structural_sources": "CHECKED" if q is not None else "NOT_QUALIFIED",
            "native_context": "CAPTURED" if self._epoch is not None else "NOT_OBSERVED",
            "definition_stability": None if q is None else q.definition_stability,
            "native_lifetime_protection": "NOT_DEMONSTRATED",
            "premise_compliance": "NOT_INDEPENDENTLY_VERIFIED",
            "attempt": self.attempt,
            "source_use_end": "TRANSACTION_ACK"
            if self._transaction in ("COMMIT_ACK", "ROLLBACK_ACK")
            else "REMOTE_QUIESCENCE_UNCONFIRMED",
        }

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
