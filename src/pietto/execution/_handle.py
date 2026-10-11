"""execute(): one explicit attempt on the PostgreSQL rows route, its result
handle, its batches and its terminal outcome."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import warnings
import weakref

from pietto._project import project_execution as ex
from pietto._project import project_public_execution as composition
from pietto.execution._access import (
    ExecutionLimits,
    PostgresAccess,
    PostgresDeploymentPremise,
)
from pietto.execution._errors import (
    AttemptFailed,
    Failure,
    HandleMisuse,
    RequestRejected,
    attempt_failure,
    batch_failure,
    failure,
    record_failure,
    request_failure,
    schema_failure,
)
from pietto.execution._query import CompiledQuery

__all__ = [
    "Outcome",
    "ResultBatch",
    "ResultHandle",
    "UnclosedHandleWarning",
    "execute",
]

ROUTES = ("postgres_rows",)


@dataclass(frozen=True, slots=True)
class Outcome:
    """A snapshot of one attempt's terminal state.

    ``end`` is NOT_STARTED, OPEN, COMPLETE (read to the end and committed),
    STOPPED_EARLY (closed before the end), DEADLINE, FAILED or, in an
    UnclosedHandleWarning only, DROPPED. ``source``, ``transaction``,
    ``delivery`` and ``cleanup`` are the owner's layered states; the
    transaction is COMMIT_ACK or ROLLBACK_ACK only after the server
    acknowledged it, and UNKNOWN stays UNKNOWN. ``remote_source_use_end`` is
    TRANSACTION_ACK only then, otherwise REMOTE_QUIESCENCE_UNCONFIRMED.
    ``primary`` is the failure that ended the attempt and ``cleanup_failures``
    the cleanup steps that failed after it. Once the attempt is closed, its
    outcome no longer changes.
    """

    attempt: str
    route: str
    end: str
    source: str
    transaction: str
    delivery: str
    cleanup: str
    remote_source_use_end: str
    rows: int
    batches: int
    bytes: int
    deadline_expired: bool
    primary: Failure | None
    cleanup_failures: tuple[Failure, ...]
    premise_compliance: str = "NOT_INDEPENDENTLY_VERIFIED"
    native_definition_lifetime_exclusion: str = "NOT_DEMONSTRATED"


class UnclosedHandleWarning(ResourceWarning):
    """PIE-R5002: an open result handle was garbage-collected, or was still
    open at interpreter exit. ``outcome`` is its snapshot with ``end``
    DROPPED. Pietto does no I/O for it: the server session and its read-only
    transaction stay open until the attempt's resources are garbage-collected
    after its deadline timer ran, or until the process exits; the deadline
    only cancels a statement that is still running. Python hides
    ResourceWarning by default (``-W default::ResourceWarning`` shows it)."""

    def __init__(self, outcome):
        notice = failure("PIE-R5002")
        super().__init__(str(notice) + " (attempt=" + outcome.attempt + ")")
        self.code = notice.code
        self.outcome = outcome


def _end(closed, deadline, primary, outcome, dropped):
    if dropped:
        return "DROPPED"
    if not closed:
        # Delivery opens only when the attempt opened successfully.
        return "NOT_STARTED" if outcome.delivery == "NOT_STARTED" else "OPEN"
    if (
        primary is None
        and outcome.source == "EOF"
        and outcome.delivery == "COMPLETE"
        and outcome.transaction == "COMMIT_ACK"
    ):
        return "COMPLETE"
    if deadline:
        return "DEADLINE"
    if primary is not None:
        return "FAILED"
    if outcome.transaction == "NOT_STARTED":
        return "NOT_STARTED"
    if outcome.source == "EARLY_CLOSE":
        return "STOPPED_EARLY"
    return "FAILED"


def _primary(record, recorded):
    if record is None:
        return None
    if recorded is not None:
        return recorded
    code = {"consumer": "PIE-R3007", "transaction": "PIE-R3006"}.get(
        record.phase, "PIE-R3999"
    )
    return record_failure(record, code)


def _outcome(owner, route, recorded, *, dropped=False):
    closed, deadline, _connected, outcome = composition.attempt_facts(owner)
    primary = _primary(outcome.primary, recorded)
    # A check that found the deadline passed before the timer fired ended the
    # attempt at that same deadline.
    deadline = deadline or (primary is not None and primary.code == "PIE-R3001")
    return Outcome(
        outcome.attempt,
        route,
        _end(closed, deadline, primary, outcome, dropped),
        outcome.source,
        outcome.transaction,
        outcome.delivery,
        outcome.cleanup,
        ex.remote_source_use_end(outcome.transaction),
        outcome.rows,
        outcome.batches,
        outcome.bytes,
        deadline,
        primary,
        tuple(record_failure(r, "PIE-R5001") for r in outcome.cleanup_failures),
    )


def _dropped(owner, route):
    # A garbage-collection callback: no I/O and no lock, only a snapshot.
    warnings.warn(UnclosedHandleWarning(_outcome(owner, route, None, dropped=True)))


class ResultBatch:
    """One checked batch of result rows, owned by the caller.

    Export it through the Arrow PyCapsule interface, for example with
    ``pyarrow.record_batch(batch)``; the imported Arrow batch shares its
    buffers and stays valid after the batch is closed. Close it (or use it as
    a context manager) when done.
    """

    __slots__ = ("_managed", "_rows", "_closed")
    _managed: Any
    _rows: int
    _closed: bool

    def __init__(self, *arguments, **keywords):
        raise TypeError("ResultBatch objects are returned by a ResultHandle")

    @property
    def num_rows(self) -> int:
        return self._rows

    @property
    def closed(self) -> bool:
        return self._closed

    def _export(self, method, *arguments):
        if self._closed:
            raise HandleMisuse(failure("PIE-R4002", "PUBLIC_BATCH_CLOSED"))
        try:
            return method(*arguments)
        except Exception as caught:
            refusal = batch_failure(caught)
        raise HandleMisuse(refusal)

    def __arrow_c_schema__(self):
        return self._export(self._managed.__arrow_c_schema__)

    def __arrow_c_array__(self, requested_schema=None):
        return self._export(self._managed.__arrow_c_array__, requested_schema)

    def close(self) -> None:
        if not self._closed:
            self._closed = True
            self._managed.close()

    def __enter__(self):
        return self

    def __exit__(self, kind, error, traceback):
        self.close()
        return False

    def __repr__(self) -> str:
        state = ", closed=True" if self._closed else ""
        return f"ResultBatch(num_rows={self._rows}{state})"


def _batch(managed):
    batch = object.__new__(ResultBatch)
    batch._managed = managed
    batch._rows = composition.batch_rows(managed)
    batch._closed = False
    return batch


class ResultHandle:
    """One attempt of one compiled query on one route; execute() creates it
    unopened. Use it as a context manager (``with``) or iterate it: entering,
    or the first ``next()``, connects; each ``next()`` returns a ResultBatch;
    the end of the result commits and closes. close() before the end stops
    early and rolls back. ``pyarrow.schema(handle)`` returns the schema of its
    batches without opening or consuming the attempt. Use it from one thread.
    """

    __slots__ = ("_owner", "_route", "_finalizer", "_recorded", "__weakref__")
    _owner: Any
    _route: str
    _finalizer: weakref.finalize | None
    _recorded: Failure | None

    def __init__(self, *arguments, **keywords):
        raise TypeError("ResultHandle objects are created by execute()")

    def __reduce_ex__(self, protocol):
        raise TypeError("ResultHandle cannot be pickled or copied")

    @property
    def attempt(self) -> str:
        return self._owner.attempt

    @property
    def route(self) -> str:
        return self._route

    @property
    def closed(self) -> bool:
        return composition.attempt_facts(self._owner)[0]

    @property
    def outcome(self) -> Outcome:
        return _outcome(self._owner, self._route, self._recorded)

    def __arrow_c_schema__(self):
        """The Arrow schema of this attempt's batches, without I/O."""
        try:
            return composition.result_schema(self._owner).__arrow_c_schema__()
        except Exception as caught:
            refusal = schema_failure(caught)
        raise HandleMisuse(refusal, attempt=self._owner.attempt)

    def _arm(self):
        # Only an opening attempt holds a connection that a drop would strand.
        if self._finalizer is None and not self.closed:
            self._finalizer = weakref.finalize(self, _dropped, self._owner, self._route)

    def _settle(self):
        if self._finalizer is not None and self.closed:
            self._finalizer.detach()
            self._finalizer = None

    def _run(self, step):
        owner = self._owner
        try:
            return step()
        except StopIteration:
            self._settle()
            raise
        except Exception as caught:
            _closed, deadline, connected, outcome = composition.attempt_facts(owner)
            primary = outcome.primary
            refusal = attempt_failure(
                caught,
                phase=None if primary is None else primary.phase,
                deadline=deadline,
                connected=connected,
                driver=composition.driver_error(caught),
            )
            if refusal.code == "PIE-R3006" and primary is not None:
                # The owner raises one wrapper when its end-of-result commit or
                # cleanup failed; the failure it recorded keeps the phase,
                # SQLSTATE and exception class, exactly as close() reports it.
                refusal = record_failure(primary, "PIE-R3006")
        except BaseException as caught:
            if self._recorded is None:
                self._recorded = failure(
                    "PIE-R3008", phase="interrupt", cause=type(caught).__name__
                )
            self._settle()
            raise
        # Raised here, outside the handler: no private exception is chained.
        if refusal.code.startswith("PIE-R4"):
            raise HandleMisuse(refusal, attempt=owner.attempt)
        if self._recorded is None:
            self._recorded = refusal
        self._settle()
        raise AttemptFailed(refusal, attempt=owner.attempt, outcome=self.outcome)

    def __enter__(self):
        self._arm()
        self._run(self._owner.open)
        return self

    def __iter__(self):
        return self

    def __next__(self) -> ResultBatch:
        self._arm()
        return _batch(self._run(self._owner.__next__))

    def close(self) -> None:
        """Close the attempt; idempotent. Before the end this stops early."""
        self._owner.close()
        self._settle()

    def __exit__(self, kind, error, traceback):
        closed, _deadline, _connected, outcome = composition.attempt_facts(self._owner)
        # After the attempt ended, an exception in the with block passes
        # through and changes nothing: the terminal outcome stays as reached.
        if not closed:
            if error is not None and self._recorded is None and outcome.primary is None:
                self._recorded = failure(
                    "PIE-R3007" if isinstance(error, Exception) else "PIE-R3008",
                    phase="consumer",
                    cause=type(error).__name__,
                )
            self._owner.__exit__(kind, error, traceback)
        self._settle()
        return False

    def __repr__(self) -> str:
        return (
            f"ResultHandle(route={self._route!r}, attempt={self.attempt!r},"
            f" end={self.outcome.end!r})"
        )


def _refuse(code, detail):
    return RequestRejected(failure(code, detail))


def execute(
    query: CompiledQuery,
    *,
    route: str,
    access: PostgresAccess,
    premise: PostgresDeploymentPremise,
    limits: ExecutionLimits = ExecutionLimits(),
    isolation: str = "stable",
    values: tuple | None = None,
) -> ResultHandle:
    """Prepare one attempt of ``query`` and return its unopened ResultHandle.

    ``route``, ``access`` and ``premise`` have no default; ``None`` is refused
    (PIE-R1001). ``route`` must be ``postgres_rows`` and the query compiled
    for ``postgres``. ``isolation`` is ``stable`` (REPEATABLE READ READ ONLY)
    or ``serializable``. ``values`` is None, which binds the values the query
    was compiled with, or a tuple with exactly one value of its slot's exact
    type for each of ``query.slots``; nothing is converted. Every request
    check runs here, before any connection: first query, route, access,
    premise and limits are given and of the right type and isolation is
    given, in that order, with the route's availability for the query
    checked right after its type (PIE-R1003); then ``values`` is None or a
    tuple (PIE-R1002); then the query is bound afresh to the values
    (PIE-R1006, PIE-R1004) and the installed code identity is read again
    (PIE-R1005); then the values of premise, access, isolation (its type
    included) and limits, in that order. The first failure is raised as
    RequestRejected. The driver and environment are checked when the attempt
    opens. Each call is a new attempt.
    """
    if query is None:
        raise _refuse("PIE-R1001", "PUBLIC_QUERY_REQUIRED")
    if type(query) is not CompiledQuery:
        raise _refuse("PIE-R1002", "PUBLIC_QUERY_TYPE")
    if route is None:
        raise _refuse("PIE-R1001", "PUBLIC_ROUTE_REQUIRED")
    if type(route) is not str:
        raise _refuse("PIE-R1002", "PUBLIC_ROUTE_TYPE")
    if route not in ROUTES or query.dialect != "postgres":
        raise _refuse("PIE-R1003", "PUBLIC_ROUTE_UNAVAILABLE")
    if access is None:
        raise _refuse("PIE-R1001", "PUBLIC_ACCESS_REQUIRED")
    if type(access) is not PostgresAccess:
        raise _refuse("PIE-R1002", "PUBLIC_ACCESS_TYPE")
    if premise is None:
        raise _refuse("PIE-R1001", "PUBLIC_PREMISE_REQUIRED")
    if type(premise) is not PostgresDeploymentPremise:
        raise _refuse("PIE-R1002", "PUBLIC_PREMISE_TYPE")
    if limits is None:
        raise _refuse("PIE-R1001", "PUBLIC_LIMITS_REQUIRED")
    if type(limits) is not ExecutionLimits:
        raise _refuse("PIE-R1002", "PUBLIC_LIMITS_TYPE")
    if isolation is None:
        raise _refuse("PIE-R1001", "PUBLIC_ISOLATION_REQUIRED")
    if values is not None and type(values) is not tuple:
        raise _refuse("PIE-R1002", "PUBLIC_VALUES_TYPE")
    try:
        owner = composition.prepare_attempt(
            query._template,
            ex.PostgresAccess(
                access.host,
                access.port,
                access.database,
                access.user,
                access.password,
                access.sslmode,
            ),
            route=route,
            schemas=premise.schemas,
            limits=ex.ExecutionLimits(
                limits.batch_rows,
                limits.batch_bytes,
                limits.max_rows,
                limits.max_bytes,
                limits.seconds,
            ),
            isolation=isolation,
            values=values,
        )
    except Exception as caught:
        refusal = request_failure(caught)
    else:
        handle = object.__new__(ResultHandle)
        handle._owner = owner
        handle._route = route
        handle._finalizer = None
        handle._recorded = None
        return handle
    raise RequestRejected(refusal)
