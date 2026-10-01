"""Owned pending/fulfilled guards and checked status-before-data consumption."""

from dataclasses import dataclass, field
from typing import Any

from pietto._project.project_execution import (
    ExecutionRequest,
    ExecutionLimits,
    _verify_execution_structure,
)
from pietto._project.project_guard_program import (
    GuardProgram,
    prepare_program,
    statement_for,
    pure_static_proofs,
)
from pietto._project.project_guard_rendering import render_guard
from pietto._project.project_guard_verification import (
    verify_program,
    verify_native_guard,
)
from pietto._project.project_execution_reader import check_native_column
from pietto._project.project_sql_emission_rows import Realization

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class GuardedExecutionRequest:
    execution: ExecutionRequest = field(repr=False)
    program: GuardProgram = field(repr=False)
    allow_guard_sql: bool = True


@dataclass(frozen=True, slots=True, eq=False)
class ObservedGuardRequest:
    """No native access or PG product authority; only explicit test transport."""

    program: GuardProgram = field(repr=False)
    limits: ExecutionLimits = ExecutionLimits()
    isolation: str = "repeatable read"
    allow_guard_sql: bool = True

    @property
    def execution(self):
        return self


@dataclass(frozen=True, slots=True, eq=False)
class GuardReceipt:
    owner: Any = field(repr=False)
    context: Any = field(repr=False)
    statement: Any = field(repr=False)
    states: tuple[str, ...]
    terminal: str


def prepare_guarded_execution(
    preparation,
    access,
    *,
    limits=ExecutionLimits(),
    isolation="stable",
    binding=None,
    refinement=None,
    allow_guard_sql=True,
):
    program = prepare_program(preparation, binding=binding, refinement=refinement)
    output = program.output
    base = ExecutionRequest(
        preparation.artifact,
        output.contract,
        access,
        limits,
        isolation,
        binding=binding,
        output=output,
    )
    request = GuardedExecutionRequest(base, program, allow_guard_sql)
    verify_guarded_execution(request)
    return request


def verify_guarded_execution(request):
    if type(request) is ObservedGuardRequest:
        from pietto._project.project_execution import verify_execution_limits

        verify_program(request.program)
        verify_execution_limits(request.limits)
        if type(request.allow_guard_sql) is not bool or request.isolation not in (
            "repeatable read",
            "serializable",
        ):
            raise ValueError("GUARD_OBSERVED_REQUEST")
        return
    if (
        type(request) is not GuardedExecutionRequest
        or type(request.allow_guard_sql) is not bool
    ):
        raise ValueError("GUARD_EXECUTION_REQUEST")
    verify_program(request.program)
    p = request.program
    if (
        request.execution.artifact is not p.preparation.artifact
        or request.execution.output is not p.output
    ):
        raise ValueError("GUARD_EXECUTION_ROOT")
    _verify_execution_structure(request.execution, guarded=p.preparation)


class GuardRun:
    """A receipt belongs only to this object's actual still-live transaction."""

    def __init__(self, request, context):
        from pietto._project.project_guard_context import (
            GuardContext,
            ObservedGuardContext,
        )

        verify_guarded_execution(request)
        expected = (
            GuardContext
            if type(request) is GuardedExecutionRequest
            else ObservedGuardContext
        )
        if type(context) is not expected:
            raise ValueError("GUARD_CONTEXT_OWNER")
        context.verify_owned(context.owner)
        self.request, self.context = request, context
        self._roots = (request, context, request.program, request.allow_guard_sql)
        self._context_state = self._context_snapshot()
        self.states = tuple(
            "STATIC" if pure_static_proofs(request.program, subject) else "PENDING"
            for subject in request.program.subjects
        )
        self.receipt = None
        self.native = None
        self._native_state = None
        self._receipt = None
        self._receipt_state = None
        self._states = self.states
        self._width = None
        self.failed = False

    def _context_snapshot(self):
        c = self.context
        return (
            c,
            c.program,
            c.route,
            c.session_id,
            c.role,
            c.environment,
            c.sources,
            c.owner,
            c.transaction,
            getattr(c, "native_transaction", None),
        )

    def verify(self, owner):
        if self._context_state != self._context_snapshot():
            raise ValueError("GUARD_CONTEXT_CHANGED")
        if self.failed or self._roots != (
            self.request,
            self.context,
            self.request.program,
            self.request.allow_guard_sql,
        ):
            raise ValueError("GUARD_ATTEMPT_CHANGED")
        if self.states is not self._states or self.receipt is not self._receipt:
            raise ValueError("GUARD_STATE_CHANGED")
        if self.native is not None and self._native_state != self._native_snapshot():
            raise ValueError("GUARD_STATEMENT_CHANGED")
        if self.receipt is not None and self._receipt_state != (
            self.receipt.owner,
            self.receipt.context,
            self.receipt.statement,
            self.receipt.states,
            self.receipt.terminal,
        ):
            raise ValueError("GUARD_RECEIPT_CHANGED")
        verify_guarded_execution(self.request)
        self.context.verify_owned(owner)
        if self.context.program is not self.request.program:
            raise ValueError("GUARD_CONTEXT_ROOT")

    def _native_snapshot(self):
        from pietto._project.project_refinement_enumeration import atom

        native = self.native
        if native is None:
            return None
        return (
            native,
            native.statement,
            native.statement.program,
            native.statement.kind,
            native.statement.subjects,
            tuple((c, c.kind, atom(c.value)) for c in native.statement.controls),
            native.sql,
            tuple(
                (u, u.domain, u.owner, u.index, atom(u.value), u.original)
                for u in native.uses
            ),
            tuple(atom(v) for v in native.arguments),
        )

    def prepare_submission(self, owner):
        self.verify(owner)
        if self.native is not None:
            raise ValueError("GUARD_SUBMISSION_REUSE")
        pending = any(s == "PENDING" for s in self.states)
        if pending and not self.request.allow_guard_sql:
            raise ValueError("GUARD_SQL_FORBIDDEN_UNFULFILLED")
        kind = (
            ("guard" if self.context.separate_allowed else "combined")
            if pending
            else "data"
        )
        return self._capture_submission(
            owner, render_guard(statement_for(self.request.program, kind))
        )

    def consume_observed_submission(self, owner, native):
        """Data-only recorded transport input; it cannot belong to a PG owner."""
        if type(self.request) is not ObservedGuardRequest:
            raise ValueError("GUARD_OBSERVED_ONLY")
        self.verify(owner)
        if (
            self.native is not None
            or native.statement.program is not self.request.program
        ):
            raise ValueError("GUARD_OBSERVED_SUBMISSION")
        pending = any(s == "PENDING" for s in self.states)
        if pending and not self.request.allow_guard_sql:
            raise ValueError("GUARD_SQL_FORBIDDEN_UNFULFILLED")
        expected = (
            ("guard" if self.context.separate_allowed else "combined")
            if pending
            else "data"
        )
        if native.statement.kind != expected:
            raise ValueError("GUARD_OBSERVED_PURPOSE")
        verify_native_guard(native)
        return self._capture_submission(owner, native)

    def _capture_submission(self, owner, native):
        self.native = native
        self._native_state = self._native_snapshot()
        from pietto._project.project_refinement_enumeration import _size

        if (
            len(self.native.sql)
            + sum(
                _size(v, self.request.execution.limits.max_bytes)
                for v in self.native.arguments
            )
            > self.request.execution.limits.max_bytes
        ):
            raise ValueError("GUARD_RESOURCE_LIMIT")
        from pietto._project.project_guard_context import charge_guard

        charge_guard(
            owner,
            len(self.native.sql)
            + sum(
                _size(v, self.request.execution.limits.max_bytes)
                for v in self.native.arguments
            ),
        )
        self.states = tuple("RUNNING" if s == "PENDING" else s for s in self.states)
        self._states = self.states
        return self.native

    def _accept_status(self, owner, values, terminal):
        if self.native is None:
            raise ValueError("GUARD_SUBMISSION_MISSING")
        owner._remaining()
        if owner._cancel.is_set():
            raise ValueError("EXECUTION_CANCELED")
        if len(values) != len(self.native.statement.subjects) or any(
            type(v) is not int or v not in (0, 1) for v in values
        ):
            raise ValueError("GUARD_STATUS_ROW")
        from pietto._project.project_guard_context import charge_guard

        charge_guard(owner, 8 * len(values))
        statuses = iter(values)
        self.states = tuple(
            "STATIC" if s == "STATIC" else "VIOLATED" if next(statuses) else "FULFILLED"
            for s in self.states
        )
        self._states = self.states
        self.receipt = GuardReceipt(
            self, self.context, self.native, self.states, terminal
        )
        self._receipt = self.receipt
        self._receipt_state = (self, self.context, self.native, self.states, terminal)
        if "VIOLATED" in self.states:
            raise ValueError("SINGLE_MATCH_VIOLATED")

    def require_fulfilled(self, owner, *, refinement=None):
        self.verify(owner)
        if refinement is not None and self.request.program.refinement is not refinement:
            raise ValueError("GUARD_REFINEMENT_IDENTITY")
        if any(s not in ("STATIC", "FULFILLED") for s in self.states) or (
            any(s == "FULFILLED" for s in self.states) and self.receipt is None
        ):
            raise ValueError("GUARD_FULFILLMENT_REQUIRED")
        owner._remaining()
        if owner._cancel.is_set():
            raise ValueError("EXECUTION_CANCELED")

    def accept_guard_result(self, owner, metadata, rows, *, terminal):
        self.verify(owner)
        if self.native is None or self.native.statement.kind != "guard":
            raise ValueError("GUARD_SUBMISSION_KIND")
        verify_native_guard(self.native)
        if (
            terminal != "NORMAL"
            or type(rows) is not tuple
            or len(rows) != 1
            or len(metadata) != len(self.native.statement.subjects)
        ):
            raise ValueError("GUARD_NATIVE_TERMINAL")
        for i, meta in enumerate(metadata):
            check_native_column(
                Realization(
                    "Int",
                    {
                        "kind": "my_signed_int"
                        if self.context.route == "mysql_rows"
                        else "pg_int8"
                    },
                    False,
                    {"kind": "int_range", "min": "0", "max": "1"},
                ),
                self.context.route,
                meta,
                label=self.request.program.prefix + "g" + str(i),
                ordinal=i,
                source_field=None,
            )
        self._accept_status(owner, rows[0], terminal)

    def accept_header(self, owner, metadata, row) -> tuple[Any, ...]:
        if type(metadata) is not tuple:
            raise ValueError("GUARD_METADATA")
        self.verify(owner)
        if self.native is None:
            raise ValueError("GUARD_SUBMISSION_MISSING")
        verify_native_guard(self.native)
        if self.native.statement.kind == "guard":
            raise ValueError("GUARD_REFINED_ENUMERATION_REQUIRED")
        if self.native.statement.kind == "data":
            self.require_fulfilled(owner)
            return metadata
        count = len(self.native.statement.subjects)
        public = len(self.request.program.output.columns)
        from pietto._project.project_guard_lowering import terminal_order

        extra, _ordering = terminal_order(self.request.program)
        self._width = 1 + count + public + len(extra)
        if row is None or len(row) != len(metadata) or len(row) != self._width:
            raise ValueError("GUARD_STATUS_ARITY")
        for i, name in enumerate(
            (self.request.program.prefix + "channel",)
            + tuple(self.request.program.prefix + "g" + str(j) for j in range(count))
        ):
            check_native_column(
                Realization(
                    "Int",
                    {
                        "kind": "my_signed_int"
                        if self.context.route == "mysql_rows"
                        else "pg_int8"
                    },
                    False,
                    {"kind": "int_range", "min": "0", "max": "1"},
                ),
                self.context.route,
                metadata[i],
                label=name,
                ordinal=i,
                source_field=None,
            )
        if (
            type(row[0]) is not int
            or row[0] != 0
            or any(type(v) is not int or v not in (0, 1) for v in row[1 : count + 1])
            or any(v is not None for v in row[count + 1 :])
        ):
            raise ValueError("GUARD_STATUS_ROW")
        from pietto._project.project_guard_context import charge_guard

        charge_guard(owner, 8 * (1 + public + len(extra)))
        self._accept_status(owner, row[1 : count + 1], "STATUS_ROW")
        selected = tuple(metadata[count + 1 : count + 1 + public])
        if self.context.route == "postgres_adbc":
            if any(
                type(meta) is not dict
                or type(meta.get("ordinal")) is not int
                or meta["ordinal"] != count + 1 + i
                for i, meta in enumerate(selected)
            ):
                raise ValueError("GUARD_METADATA_ERASURE")
            selected = tuple(dict(meta, ordinal=i) for i, meta in enumerate(selected))
        return selected

    def public_rows(self, owner, rows):
        self.verify(owner)
        if self.native is None:
            raise ValueError("GUARD_SUBMISSION_MISSING")
        if self.native.statement.kind == "guard":
            raise ValueError("GUARD_REFINED_ENUMERATION_REQUIRED")
        if self.native.statement.kind == "data":
            self.require_fulfilled(owner)
            return rows
        if (
            self.receipt is None
            or self.receipt.owner is not self
            or self.receipt.context is not self.context
            or self.receipt.states != self.states
            or any(s not in ("STATIC", "FULFILLED") for s in self.states)
        ):
            raise ValueError("GUARD_FULFILLMENT_REQUIRED")
        width = len(self.native.statement.subjects)
        public = len(self.request.program.output.columns)
        result = []
        for row in rows:
            from pietto._project.project_guard_context import charge_guard
            from pietto._project.project_refinement_enumeration import _size

            charge_guard(
                owner,
                sum(
                    _size(v, owner.request.limits.max_bytes) + 8
                    for v in row[: width + 1] + row[width + 1 + public :]
                ),
            )
            if (
                len(row) != self._width
                or type(row[0]) is not int
                or row[0] != 1
                or any(type(v) is not int or v != 0 for v in row[1 : width + 1])
            ):
                raise ValueError("GUARD_DATA_CHANNEL")
            result.append(tuple(row[width + 1 : width + 1 + public]))
        return tuple(result)

    def close(self):
        self.states = tuple(
            "UNKNOWN" if s in ("PENDING", "RUNNING") else s for s in self.states
        )
        self._states = self.states
        self.failed = True
