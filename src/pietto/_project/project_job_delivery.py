"""S15 provisional durable delivery to an independent cooperative reference sink.

A stream is the one durable delivery registration of one generation to one sink
namespace incarnation. It discloses only committed, contiguous, checked saved
occurrences of explicitly adopted immutable checkpoint windows, or the actual
S13 deliveries of a fixed R1 consumer. A bounded local issuance is committed
under the S11 fence before any sink contact; sink decisions come back as data
and become local observations only through a fenced confirmation. The effect
identity is the destination incarnation plus (workspace, generation, position),
never an attempt, checkpoint, chunk, batch, session, consumer or operation.

The local sink-confirmed frontier is derived from observations. A sink COMMIT,
a received reply, a local observation, an S13 acknowledgement, source EOF,
complete capture and generation publication stay distinct. Delivered effects
are provisional: a later source or transaction failure does not undo them.
Nothing here publishes a generation, schedules work, retries without an explicit
call, deletes files or compensates an external effect.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import os
import time
from typing import Any
import weakref

from pietto._project import project_job_chunks as chunks
from pietto._project import project_job_replay as replay
from pietto._project.project_job_capture import (
    CaptureSession,
    SnapshotReader,
    _retain,
    _scope,
    _snapshot,
    arrow_output,
    contract_digest,
    coordinate_scheme,
    stored_binding,
)
from pietto._project.project_job_sink import (
    LAYOUT,
    Sink,
    SinkEffect,
    SinkReply,
    check_effect,
    effect_digest,
)
from pietto._project.project_job_store import (
    _FENCE,
    _FENCE_CONTROL,
    OperationResult,
    Publisher,
    _advance,
    _fence,
    _identity_request,
    _json,
    _operate,
    _vector,
    new_operation,
)
from pietto._project.project_job_workspace import (
    JobStoreError,
    Workspace,
    new_identity,
    read,
    supports,
    valid_identity,
)

__all__: tuple[str, ...] = ()

WAITING = "WAITING_FOR_COMMITTED_CHECKPOINT"
MAX_ACCEPTANCE_SECONDS = 86400
MAX_PURPOSE_BYTES = 256
MAX_BATCH_BYTES = 16 * 1024 * 1024
LIMITS = {
    "stream": 1024,
    "stream_window": 16384,
    "stream_session": 65536,
    "stream_issuance": 262144,
    "sink_observation": 1048576,
}
CONFIRMED = ("COMMITTED", "DUPLICATE", "PRESENT_MATCHING")
CONFLICTED = ("CONFLICT", "PRESENT_CONFLICT")
UNAVAILABLE = ("UNAVAILABLE", "UNAVAILABLE_OR_UNKNOWN", "RETENTION_EXPIRED")
# The trusted host clocks. Tests inject explicit boundaries; callers cannot.
_wall = time.time
_monotonic = time.monotonic
_ACCEPTED: weakref.WeakSet = weakref.WeakSet()


def _delivering(workspace: Workspace) -> None:
    if not supports(workspace, "cooperative-delivery"):
        raise JobStoreError("WORKSPACE_DELIVERY_FORMAT")


def _purpose(purpose) -> None:
    if (
        type(purpose) is not str
        or not purpose
        or not purpose.isprintable()
        or len(purpose.encode("utf-8")) > MAX_PURPOSE_BYTES
    ):
        raise JobStoreError("ACCEPTANCE_PURPOSE")


def _seconds(seconds) -> None:
    if type(seconds) is not int or not 1 <= seconds <= MAX_ACCEPTANCE_SECONDS:
        raise JobStoreError("ACCEPTANCE_BOUND")


def _bound(c, table: str) -> None:
    if c.execute(f"SELECT count(*) FROM {table}").fetchone()[0] >= LIMITS[table]:
        raise JobStoreError("STORE_LIMIT")


def layout(output, refinement) -> str:
    """The exact typed row shape of one compiled output (Arrow-free)."""
    from pietto._project.project_scalar_meaning import TimestampMeaning

    contract = output.contract
    fields = []
    for leaf in contract.shape.fields:
        law = None if leaf.meaning is None else leaf.meaning.law
        fields.append(
            [
                leaf.ordinal,
                leaf.label,
                leaf.shape.canonical.kind.value,
                leaf.shape.canonical.name,
                leaf.nullability.value,
                None
                if law is None
                else [
                    "timestamp",
                    law.calendar,
                    law.resolution,
                    law.timezone,
                    list(law.lower),
                    list(law.upper),
                ]
                if type(law) is TimestampMeaning
                else ["uuid", law.byte_order, law.byte_width],
            ]
        )
    return _json(
        {
            "contract": contract_digest(output),
            "fields": fields,
            "format": LAYOUT,
            "multiplicity": contract.multiplicity.value,
            "scheme": None if refinement is None else coordinate_scheme(refinement),
        }
    )


def _payloads(batch, coordinates) -> tuple[str, ...]:
    """One canonical exact typed row per occurrence of one checked batch.

    Values are the S06 atoms (S12 wire) of the checked Arrow values; batch
    layout, offsets, native carriers and IPC batch counts never enter a row.
    """
    from pietto._project.project_arrow_result import _arrow

    data = _arrow().record_batch(batch)
    columns = [data.column(i).to_pylist() for i in range(data.num_columns)]
    return tuple(
        _json(
            {
                "coordinates": None
                if coordinates is None
                else [chunks.coordinate_wire(v) for v in coordinates[j]],
                "values": [chunks.coordinate_wire(column[j]) for column in columns],
            }
        )
        for j in range(data.num_rows)
    )


@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class WindowAcceptance:
    """A process-local caller acceptance to read one saved checkpoint of one
    generation for delivery (or, without a checkpoint, only to register its
    stream). Never stored or copied; no record, receipt or sink reply mints one.
    """

    workspace: str
    job: str
    generation: str
    checkpoint: str | None
    purpose: str
    route: str
    binding: str
    contract: str
    scheme: str = field(repr=False)
    layout: str = field(repr=False)
    batch_rows: int
    seconds: int
    accepted_at: float
    _output: Any = field(repr=False)
    _refinement: Any = field(repr=False)
    _deadline: float = field(repr=False)
    _pid: int = field(repr=False)

    def __reduce_ex__(self, protocol):
        raise JobStoreError("ACCEPTANCE_COPY")


@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class SinkAcceptance:
    """A process-local caller acceptance to submit to and query one sink
    incarnation, distinct from any read permission. It never outlives the sink's
    retention contract; renewing it is not renewing that contract.
    """

    sink: str
    namespace: str
    epoch: int
    retention: str = field(repr=False)
    retained_until: int
    purpose: str
    seconds: int
    accepted_at: float
    _handle: Any = field(repr=False)
    _deadline: float = field(repr=False)
    _pid: int = field(repr=False)

    def __reduce_ex__(self, protocol):
        raise JobStoreError("ACCEPTANCE_COPY")


def _accepted(acceptance, kind):
    """Issued here, by this process, and within every validity bound now."""
    if type(acceptance) is not kind or acceptance not in _ACCEPTED:
        raise JobStoreError("ACCEPTANCE_UNKNOWN")
    if acceptance._pid != os.getpid():
        raise JobStoreError("ACCEPTANCE_FOREIGN_PROCESS")
    now = _wall()
    if not (
        _monotonic() < acceptance._deadline
        and now < acceptance.accepted_at + acceptance.seconds
    ):
        raise JobStoreError("ACCEPTANCE_EXPIRED")
    if kind is SinkAcceptance and now >= acceptance.retained_until:
        raise JobStoreError("RETENTION_EXPIRED")
    return acceptance


def accept_window(
    workspace: Workspace,
    job: str,
    generation: str,
    *,
    checkpoint: str | None,
    purpose: str,
    route: str,
    values,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: tuple,
    seconds: int,
    batch_rows: int,
) -> WindowAcceptance:
    """Fresh trust, exact typed values, output/scheme correspondence, frontier."""
    from pietto._project.project_execution import compiled_output
    from pietto._project.project_execution_template import bind_values

    _delivering(workspace)
    if checkpoint is not None and not valid_identity(checkpoint, "ckp"):
        raise JobStoreError("CHECKPOINT_UNKNOWN")
    _purpose(purpose)
    _seconds(seconds)
    if type(batch_rows) is not int or not 1 <= batch_rows <= chunks.MAX_ROWS:
        raise JobStoreError("ACCEPTANCE_BOUND")
    accepted_at, deadline = _wall(), _monotonic() + seconds
    template, binding, stored_route = stored_binding(
        workspace,
        job,
        generation,
        expected_pin=expected_pin,
        accepted_producer=accepted_producer,
        accepted_compatibility=accepted_compatibility,
    )
    if route != stored_route:
        raise JobStoreError("ACCEPTANCE_ROUTE")
    try:
        stated = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    except (ValueError, TypeError):
        raise JobStoreError("BINDING_VECTOR") from None
    # The typed wire keeps True != 1, -0.0 != 0.0 and exact Text distinct.
    if _vector(stated) != _vector(binding):
        raise JobStoreError("BINDING_VECTOR")
    output, refinement, _program = compiled_output(binding)

    def body(c):
        row = c.execute(
            "SELECT g.binding, c.contract, c.scheme FROM capture c JOIN generation g"
            " ON g.identity = c.generation AND g.job = c.job"
            " WHERE c.generation = ? AND c.job = ?",
            (generation, job),
        ).fetchone()
        if row is None:
            raise JobStoreError("CAPTURE_UNKNOWN")
        if checkpoint is not None:
            _snapshot(c, workspace, job, generation, checkpoint)
        return row

    record, contract, scheme = read(workspace, body)
    if (contract, scheme) != (contract_digest(output), coordinate_scheme(refinement)):
        raise JobStoreError("READER_SNAPSHOT")
    acceptance = WindowAcceptance(
        workspace.identity,
        job,
        generation,
        checkpoint,
        purpose,
        route,
        record,
        contract,
        scheme,
        layout(output, refinement),
        batch_rows,
        seconds,
        accepted_at,
        output,
        refinement,
        deadline,
        os.getpid(),
    )
    _ACCEPTED.add(acceptance)
    return _accepted(acceptance, WindowAcceptance)


def accept_sink(
    sink: Sink,
    *,
    instance: str,
    namespace: str,
    epoch: int,
    retention: str,
    purpose: str,
    seconds: int,
) -> SinkAcceptance:
    """Compare the sink owner's own current description with the caller's
    independent expectations; a colocated claim or old reply never suffices."""
    if type(sink) is not Sink:
        raise JobStoreError("SINK_UNKNOWN")
    _purpose(purpose)
    _seconds(seconds)
    accepted_at, deadline = _wall(), _monotonic() + seconds
    actual = sink.describe()
    if (actual.identity, actual.namespace, actual.epoch, actual.retention) != (
        instance,
        namespace,
        epoch,
        retention,
    ):
        raise JobStoreError("SINK_DESTINATION")
    acceptance = SinkAcceptance(
        actual.identity,
        actual.namespace,
        actual.epoch,
        actual.retention,
        actual.retained_until,
        purpose,
        seconds,
        accepted_at,
        sink,
        deadline,
        os.getpid(),
    )
    _ACCEPTED.add(acceptance)
    return _accepted(acceptance, SinkAcceptance)


@dataclass(frozen=True, slots=True)
class StreamFacts:
    """The registered destination and output of one stream (recorded facts)."""

    identity: str
    workspace: str
    job: str
    generation: str
    binding: str
    route: str
    contract: str
    scheme: str = field(repr=False)
    layout: str = field(repr=False)
    sink: str
    namespace: str
    epoch: int
    retention: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class WindowFacts:
    ordinal: int
    checkpoint: str
    retention: str
    start: int
    stop: int


def _stream(c, workspace, job, stream) -> StreamFacts:
    row = c.execute(
        "SELECT generation, binding, route, contract, scheme, layout, sink, namespace,"
        " epoch, retention,"
        " (SELECT count(*) FROM stream_retirement r WHERE r.stream = s.identity)"
        " FROM stream s WHERE identity = ? AND job = ?",
        (stream, job),
    ).fetchone()
    if row is None:
        raise JobStoreError("STREAM_UNKNOWN")
    if row[10]:
        raise JobStoreError("STREAM_RETIRED")
    return StreamFacts(stream, workspace.identity, job, *row[:10])


def _latest_window(c, stream) -> WindowFacts | None:
    row = c.execute(
        "SELECT ordinal, checkpoint, retention, start, stop FROM stream_window"
        " WHERE stream = ? ORDER BY ordinal DESC LIMIT 1",
        (stream,),
    ).fetchone()
    return None if row is None else WindowFacts(*row)


def _released(c, retention) -> bool:
    return bool(
        c.execute(
            "SELECT count(*) FROM retention_release WHERE retention = ?", (retention,)
        ).fetchone()[0]
    )


def _frontier(c, stream) -> int:
    """The derived local sink-confirmed frontier (maximal contiguous prefix)."""
    position = 0
    for (observed,) in c.execute(
        "SELECT position FROM sink_observation WHERE stream = ? ORDER BY position",
        (stream,),
    ):
        if observed != position:
            break
        position += 1
    return position


def _ranges(positions) -> tuple[tuple[int, int], ...]:
    result: list[list[int]] = []
    for p in sorted(positions):
        if result and result[-1][1] == p:
            result[-1][1] = p + 1
        else:
            result.append([p, p + 1])
    return tuple((a, b) for a, b in result)


def _unresolved(c, stream) -> set[int]:
    """Issued positions without a local observation (sink outcome not known here)."""
    issued: set[int] = set()
    for start, stop in c.execute(
        "SELECT start, stop FROM stream_issuance WHERE stream = ?", (stream,)
    ):
        issued.update(range(start, stop))
    return issued - {
        p
        for (p,) in c.execute(
            "SELECT position FROM sink_observation WHERE stream = ?", (stream,)
        )
    }


def _destination(facts, sink) -> None:
    if (facts.sink, facts.namespace, facts.epoch, facts.retention) != (
        sink.sink,
        sink.namespace,
        sink.epoch,
        sink.retention,
    ):
        raise JobStoreError("SINK_DESTINATION")


def _correspond(facts, acceptance) -> None:
    if (
        acceptance.workspace,
        acceptance.job,
        acceptance.generation,
        acceptance.binding,
        acceptance.route,
        acceptance.contract,
        acceptance.scheme,
        acceptance.layout,
    ) != (
        facts.workspace,
        facts.job,
        facts.generation,
        facts.binding,
        facts.route,
        facts.contract,
        facts.scheme,
        facts.layout,
    ):
        raise JobStoreError("ACCEPTANCE_SUBJECT")


def register_stream(
    publisher: Publisher,
    window: WindowAcceptance,
    sink: SinkAcceptance,
    *,
    operation: str,
) -> OperationResult:
    """The one delivery registration of a generation to one sink incarnation."""
    workspace = publisher.use()
    _delivering(workspace)
    read_acceptance = _accepted(window, WindowAcceptance)
    sink_acceptance = _accepted(sink, SinkAcceptance)
    if (read_acceptance.workspace, read_acceptance.job) != (
        workspace.identity,
        publisher.job,
    ):
        raise JobStoreError("ACCEPTANCE_SUBJECT")
    a = read_acceptance
    request = _identity_request(
        publisher,
        generation=a.generation,
        binding=a.binding,
        route=a.route,
        contract=a.contract,
        scheme=a.scheme,
        layout=a.layout,
        sink=sink_acceptance.sink,
        namespace=sink_acceptance.namespace,
        epoch=sink_acceptance.epoch,
        retention=sink_acceptance.retention,
        purpose=a.purpose,
    )

    def effect(c):
        revision = _fence(c, publisher, _FENCE)
        _accepted(read_acceptance, WindowAcceptance)
        _accepted(sink_acceptance, SinkAcceptance)
        _bound(c, "stream")
        if c.execute(
            "SELECT 1 FROM stream WHERE generation = ? AND sink = ? AND namespace = ?"
            " AND epoch = ?",
            (
                a.generation,
                sink_acceptance.sink,
                sink_acceptance.namespace,
                sink_acceptance.epoch,
            ),
        ).fetchone():
            raise JobStoreError("STREAM_EXISTS")
        row = c.execute(
            "SELECT g.binding, g.route, c.contract, c.scheme FROM generation g"
            " JOIN capture c ON c.generation = g.identity AND c.job = g.job"
            " WHERE g.identity = ? AND g.job = ?",
            (a.generation, publisher.job),
        ).fetchone()
        if row != (a.binding, a.route, a.contract, a.scheme):
            raise JobStoreError("ACCEPTANCE_SUBJECT")
        identity = new_identity("stm")
        c.execute(
            "INSERT INTO stream(identity, job, generation, binding, route, contract,"
            " scheme, layout, sink, namespace, epoch, retention, purpose,"
            " publisher_epoch, publisher_instance)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                identity,
                publisher.job,
                a.generation,
                a.binding,
                a.route,
                a.contract,
                a.scheme,
                a.layout,
                sink_acceptance.sink,
                sink_acceptance.namespace,
                sink_acceptance.epoch,
                sink_acceptance.retention,
                a.purpose,
                publisher.epoch,
                publisher.instance,
            ),
        )
        return publisher.job, {"revision": revision, "stream": identity}

    return _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "register_stream",
            request,
            effect,
            payload=len(a.layout),
        ),
    )


def find_stream(
    workspace: Workspace,
    job: str,
    generation: str,
    *,
    sink: str,
    namespace: str,
    epoch: int,
) -> str | None:
    """The registered stream of this destination incarnation, if any (read-only)."""
    _delivering(workspace)
    row = read(
        workspace,
        lambda c: c.execute(
            "SELECT identity FROM stream WHERE job = ? AND generation = ? AND sink = ?"
            " AND namespace = ? AND epoch = ?",
            (job, generation, sink, namespace, epoch),
        ).fetchone(),
    )
    return None if row is None else row[0]


@dataclass(frozen=True, slots=True)
class Waiting:
    """WAITING_FOR_COMMITTED_CHECKPOINT: every adopted window is delivered up to
    its committed contiguous frontier. It is not source EOF, completion or
    publication; observed_end, holes and complete row coverage are recorded
    facts, and `schema` is the verified schema member of an empty result."""

    terminal: str
    window: int | None
    position: int
    checkpoint: str | None
    observed_end: int | None
    holes: tuple[tuple[int, int], ...]
    complete_coverage: bool
    schema: Any = field(repr=False)


class Issued:
    """One locally issued contiguous extent and its process-local sink outcomes.

    An outcome is data from the sink owner; only a fenced confirmation makes it
    local progress. A lost or unknown outcome stays unknown in this object.
    """

    __slots__ = (
        "session",
        "identity",
        "window",
        "delivery",
        "start",
        "stop",
        "effects",
        "prior",
        "_digests",
        "_done",
        "_outcomes",
        "_source",
    )

    def __init__(
        self,
        session,
        identity,
        window,
        delivery,
        start,
        stop,
        effects,
        prior,
        done,
        source,
    ):
        self.session = session
        self.identity = identity
        self.window = window
        self.delivery = delivery
        self.start = start
        self.stop = stop
        self.effects: tuple[SinkEffect, ...] = effects
        self.prior: frozenset[int] = prior
        self._digests = {
            e.position: effect_digest(e.layout, e.payload) for e in effects
        }
        self._done: set[int] = set(done)
        self._outcomes: dict[int, tuple[str, Any]] = {}
        self._source = source

    def __repr__(self) -> str:
        return (
            f"Issued(identity={self.identity!r}, start={self.start}, stop={self.stop})"
        )

    @property
    def confirmed(self) -> frozenset[int]:
        """Positions with a durable local observation known to this process."""
        return frozenset(self._done)

    @property
    def resolved(self) -> bool:
        return len(self._done) == self.stop - self.start

    def outcome(self, position: int) -> tuple[str, Any] | None:
        return self._outcomes.get(position)


@dataclass(frozen=True, slots=True)
class StreamState:
    """A read-only observation of one stream's obligations; never authority.

    `position` is the local sink-confirmed frontier; `unresolved` are issued
    occurrences without a local observation (their sink outcome is unknown
    here); `windows` carry each protected checkpoint and its release state.
    """

    stream: str
    job: str
    generation: str
    sink: str
    namespace: str
    epoch: int
    retention: str = field(repr=False)
    retired: bool
    position: int
    observed: tuple[tuple[int, int], ...]
    unresolved: tuple[tuple[int, int], ...]
    windows: tuple[tuple[int, str, str, int, int, bool], ...]
    sessions: tuple[tuple[str, int, int], ...]
    issuances: tuple[tuple[str, str, int | None, str | None, int, int], ...]


def stream_state(workspace: Workspace, stream: str) -> StreamState:
    """Registered facts, derived frontier and the complete delivery history."""
    _delivering(workspace)
    if not valid_identity(stream, "stm"):
        raise JobStoreError("STREAM_UNKNOWN")

    def body(c):
        row = c.execute(
            "SELECT job, generation, sink, namespace, epoch, retention,"
            " (SELECT count(*) FROM stream_retirement r WHERE r.stream = s.identity)"
            " FROM stream s WHERE identity = ?",
            (stream,),
        ).fetchone()
        if row is None:
            raise JobStoreError("STREAM_UNKNOWN")
        return (
            row,
            _frontier(c, stream),
            [
                p
                for (p,) in c.execute(
                    "SELECT position FROM sink_observation WHERE stream = ?", (stream,)
                )
            ],
            _unresolved(c, stream),
            c.execute(
                "SELECT w.ordinal, w.checkpoint, w.retention, w.start, w.stop,"
                " EXISTS (SELECT 1 FROM retention_release x WHERE x.retention = w.retention)"
                " FROM stream_window w WHERE w.stream = ? ORDER BY w.ordinal",
                (stream,),
            ).fetchall(),
            c.execute(
                "SELECT identity, ordinal, position FROM stream_session"
                " WHERE stream = ? ORDER BY ordinal",
                (stream,),
            ).fetchall(),
            c.execute(
                "SELECT i.identity, i.session, i.window_ordinal, i.delivery, i.start,"
                " i.stop FROM stream_issuance i JOIN stream_session s"
                " ON s.identity = i.session WHERE i.stream = ?"
                " ORDER BY s.ordinal, i.ordinal",
                (stream,),
            ).fetchall(),
        )

    row, position, observed, unresolved, windows, sessions, issuances = read(
        workspace, body
    )
    return StreamState(
        stream,
        row[0],
        row[1],
        row[2],
        row[3],
        row[4],
        row[5],
        bool(row[6]),
        position,
        _ranges(observed),
        _ranges(unresolved),
        tuple((w[0], w[1], w[2], w[3], w[4], bool(w[5])) for w in windows),
        tuple(sessions),
        tuple(issuances),
    )


def open_stream(
    publisher: Publisher,
    stream: str,
    sink: SinkAcceptance,
    *,
    window: WindowAcceptance | None = None,
    operation: str,
) -> StreamSession:
    """A new durable session at the derived frontier; older sessions are superseded.

    `window` (read permission) must name the latest adopted window's checkpoint;
    without it the session can adopt windows or bridge S13 deliveries only.
    """
    workspace = publisher.use()
    _delivering(workspace)
    sink_acceptance = _accepted(sink, SinkAcceptance)
    read_acceptance = None if window is None else _accepted(window, WindowAcceptance)
    if not valid_identity(stream, "stm"):
        raise JobStoreError("STREAM_UNKNOWN")
    request = _identity_request(
        publisher,
        stream=stream,
        accepted_at=int(sink_acceptance.accepted_at),
        seconds=sink_acceptance.seconds,
        purpose=sink_acceptance.purpose,
        checkpoint=None if read_acceptance is None else read_acceptance.checkpoint,
        batch_rows=None if read_acceptance is None else read_acceptance.batch_rows,
    )
    taken = []

    def effect(c):
        revision = _fence(c, publisher, _FENCE)
        _accepted(sink_acceptance, SinkAcceptance)
        _bound(c, "stream_session")
        facts = _stream(c, workspace, publisher.job, stream)
        _destination(facts, sink_acceptance)
        latest = _latest_window(c, stream)
        snapshot = None
        if read_acceptance is not None:
            _accepted(read_acceptance, WindowAcceptance)
            _correspond(facts, read_acceptance)
            if latest is not None and read_acceptance.checkpoint != latest.checkpoint:
                raise JobStoreError("STREAM_WINDOW")
        if latest is not None:
            if _released(c, latest.retention):
                raise JobStoreError("STREAM_RELEASED")
            snapshot = _snapshot(
                c, workspace, publisher.job, facts.generation, latest.checkpoint
            )
        position = _frontier(c, stream)
        ordinal = c.execute(
            "SELECT coalesce(max(ordinal), 0) + 1 FROM stream_session WHERE stream = ?",
            (stream,),
        ).fetchone()[0]
        identity = new_identity("sts")
        c.execute(
            "INSERT INTO stream_session(identity, stream, ordinal, position,"
            " accepted_at, seconds, batch_rows, purpose, publisher_epoch,"
            " publisher_instance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                identity,
                stream,
                ordinal,
                position,
                int(sink_acceptance.accepted_at),
                sink_acceptance.seconds,
                None if read_acceptance is None else read_acceptance.batch_rows,
                sink_acceptance.purpose,
                publisher.epoch,
                publisher.instance,
            ),
        )
        taken.append((facts, latest, snapshot))
        return publisher.job, {
            "ordinal": ordinal,
            "position": position,
            "revision": revision,
            "session": identity,
        }

    result = _advance(
        publisher, _operate(workspace, operation, "open_stream", request, effect)
    )
    if result.observation != "COMMITTED_THIS_CALL":
        raise JobStoreError("STREAM_SESSION_REPLAYED")
    facts, latest, snapshot = taken[0]
    return StreamSession(
        publisher,
        sink_acceptance,
        read_acceptance,
        result.get("session"),
        result.get("ordinal"),
        result.get("position"),
        facts,
        latest,
        snapshot,
    )


class StreamSession:
    """One process-local delivery session of one stream; never passed to another
    process. It holds at most one pending issued batch and one decoded member."""

    __slots__ = (
        "publisher",
        "sink",
        "window_acceptance",
        "identity",
        "ordinal",
        "facts",
        "window",
        "snapshot",
        "_position",
        "_pending",
        "_reader",
        "_held",
        "_pid",
        "_closed",
    )

    def __init__(
        self,
        publisher,
        sink,
        window_acceptance,
        identity,
        ordinal,
        position,
        facts,
        window,
        snapshot,
    ):
        self.publisher = publisher
        self.sink = sink
        self.window_acceptance = window_acceptance
        self.identity = identity
        self.ordinal = ordinal
        self.facts = facts
        self.window = window
        self.snapshot = snapshot
        self._position = position
        self._pending: Issued | None = None
        self._reader: SnapshotReader | None = None
        self._held: tuple[int, Any] | None = None
        self._pid = os.getpid()
        self._closed = False

    def __repr__(self) -> str:
        return f"StreamSession(identity={self.identity!r})"

    @property
    def position(self) -> int:
        """The local sink-confirmed frontier known to this session."""
        return self._position

    @property
    def pending(self) -> Issued | None:
        """The issued batch whose occurrences are not all confirmed yet."""
        return self._pending

    def _use(self) -> Workspace:
        if self._pid != os.getpid():
            raise JobStoreError("STREAM_FOREIGN_PROCESS")
        if self._closed:
            raise JobStoreError("STREAM_CLOSED")
        return self.publisher.use()

    def _own(self, issued) -> None:
        if type(issued) is not Issued or issued.session is not self:
            raise JobStoreError("ISSUANCE_FOREIGN")

    # Duck-typed S13 reader seam: `replay._rebatch` reads checked member
    # slices of `self.snapshot` through these two methods.
    def _open_reader(self) -> SnapshotReader:
        if self._reader is None:
            a, facts = self.window_acceptance, self.facts
            output = arrow_output(
                facts.job, facts.generation, a._output, a._refinement, facts.route
            )
            self._reader = SnapshotReader(self.publisher.use(), self.snapshot, output)
        return self._reader

    def _chunk(self, index):
        if self._held is None or self._held[0] != index:
            self._held = None
            self._held = (index, self._open_reader().read(index))
        return self._held[1]

    def _current(self, c) -> None:
        """The newest session of its stream, by this publisher, not retired."""
        row = c.execute(
            "SELECT s.ordinal, s.publisher_epoch, s.publisher_instance,"
            " (SELECT max(ordinal) FROM stream_session WHERE stream = s.stream),"
            " (SELECT count(*) FROM stream_retirement WHERE stream = s.stream)"
            " FROM stream_session s WHERE s.identity = ? AND s.stream = ?",
            (self.identity, self.facts.identity),
        ).fetchone()
        if row is None:
            raise JobStoreError("STREAM_SESSION_UNKNOWN")
        if row[0] != row[3] or (row[1], row[2]) != (
            self.publisher.epoch,
            self.publisher.instance,
        ):
            raise JobStoreError("STREAM_SESSION_STALE")
        if row[4]:
            raise JobStoreError("STREAM_RETIRED")

    def _authority(self, source=None) -> None:
        _accepted(self.sink, SinkAcceptance)
        if source is None:
            if self.window_acceptance is None:
                raise JobStoreError("STREAM_READ_REQUIRED")
            _accepted(self.window_acceptance, WindowAcceptance)
        else:
            replay._accepted(source)

    def _live(self, issued=None) -> None:
        """Authority, ACTIVE job, current publisher/session and protection now."""
        source = None
        if issued is not None and issued._source is not None:
            source = issued._source.replay.acceptance
        self._authority(source)
        publisher = self.publisher

        def body(c):
            row = c.execute(
                "SELECT state, publisher_epoch, publisher_instance FROM job"
                " WHERE identity = ?",
                (publisher.job,),
            ).fetchone()
            if (row[1], row[2]) != (publisher.epoch, publisher.instance):
                raise JobStoreError("PUBLISHER_STALE")
            if row[0] != "ACTIVE":
                raise JobStoreError("JOB_STATE")
            self._current(c)
            self._protected(c, issued)

        read(self.publisher.use(), body)

    def _protected(self, c, issued) -> None:
        """The saved occurrences are still protected: the issued window's (or
        the bridged S13 consumer's) retention is not released."""
        if issued is None or issued.window is not None:
            window = self.window if issued is None else issued.window
            if window is not None and _released(c, window.retention):
                raise JobStoreError("STREAM_RELEASED")
            return
        found = c.execute(
            "SELECT (SELECT count(*) FROM retention_release x"
            " WHERE x.retention = k.retention) FROM issuance i"
            " JOIN consumer k ON k.identity = i.consumer WHERE i.identity = ?",
            (issued.delivery,),
        ).fetchone()
        if found is None or found[0]:
            raise JobStoreError("CONSUMER_RELEASED")

    def _waiting(self, workspace) -> Waiting:
        window = self.window
        if window is None:
            return Waiting(
                WAITING,
                None,
                self._position,
                None,
                None,
                (),
                False,
                None,
            )
        facts = self.facts
        snapshot = read(
            workspace,
            lambda c: _snapshot(
                c, workspace, facts.job, facts.generation, window.checkpoint
            ),
        )
        complete = (
            snapshot.session_source == "EOF"
            and snapshot.observed_end == window.stop
            and not snapshot.holes
            and bool(snapshot.members)
        )
        schema = None
        if window.stop == 0 and any(m.start == m.stop for m in snapshot.members):
            # An empty result keeps its exact schema in one checked [0, 0) member.
            schema = replay._rebatch(self, 0, 0)[3]
        return Waiting(
            WAITING,
            window.ordinal,
            self._position,
            window.checkpoint,
            snapshot.observed_end,
            snapshot.holes,
            complete,
            schema,
        )

    def _effects(self, start, payloads) -> tuple[SinkEffect, ...]:
        facts, total, effects = self.facts, 0, []
        for offset, payload in enumerate(payloads):
            # Bounded canonical exact typed rows, checked before any effect.
            check_effect(facts.layout, payload)
            total += len(payload.encode("utf-8"))
            if total > MAX_BATCH_BYTES:
                raise JobStoreError("STREAM_BATCH_LIMIT")
            effects.append(
                SinkEffect(
                    facts.sink,
                    facts.namespace,
                    facts.epoch,
                    facts.retention,
                    facts.workspace,
                    facts.generation,
                    start + offset,
                    facts.layout,
                    payload,
                )
            )
        return tuple(effects)

    def _issue(self, effects, start, stop, window, delivery, source, operation):
        """The local intention, committed before any sink contact."""
        workspace, publisher, facts = self.publisher.use(), self.publisher, self.facts
        digest = hashlib.sha256(
            _json([effect_digest(e.layout, e.payload) for e in effects]).encode("utf-8")
        ).hexdigest()
        request = _identity_request(
            publisher,
            stream=facts.identity,
            session=self.identity,
            window=None if window is None else window.ordinal,
            delivery=delivery,
            start=start,
            stop=stop,
            digest=digest,
        )
        taken = []

        def effect(c):
            revision = _fence(c, publisher, _FENCE)
            self._authority(None if source is None else source.replay.acceptance)
            self._current(c)
            _bound(c, "stream_issuance")
            last = c.execute(
                "SELECT start, stop FROM stream_issuance WHERE session = ?"
                " ORDER BY ordinal DESC LIMIT 1",
                (self.identity,),
            ).fetchone()
            if (
                last is not None
                and c.execute(
                    "SELECT count(*) FROM sink_observation WHERE stream = ?"
                    " AND position >= ? AND position < ?",
                    (facts.identity, last[0], last[1]),
                ).fetchone()[0]
                != last[1] - last[0]
            ):
                raise JobStoreError("DELIVERY_PENDING")
            if window is not None:
                if _latest_window(c, facts.identity) != window:
                    raise JobStoreError("STREAM_WINDOW")
                if _released(c, window.retention):
                    raise JobStoreError("STREAM_RELEASED")
                if _frontier(c, facts.identity) != start:
                    raise JobStoreError("STREAM_PROGRESS")
            else:
                found = c.execute(
                    "SELECT i.start, i.stop, k.generation,"
                    " (SELECT count(*) FROM acknowledgement a WHERE a.issuance = i.identity),"
                    " (SELECT count(*) FROM retention_release x"
                    " WHERE x.retention = k.retention)"
                    " FROM issuance i JOIN consumer k ON k.identity = i.consumer"
                    " WHERE i.identity = ? AND k.job = ?",
                    (delivery, publisher.job),
                ).fetchone()
                if found is None or found[:3] != (start, stop, facts.generation):
                    raise JobStoreError("DELIVERY_FOREIGN")
                if found[3]:
                    raise JobStoreError("DELIVERY_ACKNOWLEDGED")
                if found[4]:
                    raise JobStoreError("CONSUMER_RELEASED")
            confirmed = {
                p
                for (p,) in c.execute(
                    "SELECT position FROM sink_observation WHERE stream = ?"
                    " AND position >= ? AND position < ?",
                    (facts.identity, start, stop),
                )
            }
            prior: set[int] = set()
            for a, b in c.execute(
                "SELECT start, stop FROM stream_issuance WHERE stream = ?"
                " AND stop > ? AND start < ?",
                (facts.identity, start, stop),
            ):
                prior.update(range(max(a, start), min(b, stop)))
            ordinal = c.execute(
                "SELECT count(*) + 1 FROM stream_issuance WHERE session = ?",
                (self.identity,),
            ).fetchone()[0]
            identity = new_identity("sti")
            c.execute(
                "INSERT INTO stream_issuance(identity, stream, session, ordinal,"
                " window_ordinal, delivery, start, stop, digest, publisher_epoch)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    identity,
                    facts.identity,
                    self.identity,
                    ordinal,
                    None if window is None else window.ordinal,
                    delivery,
                    start,
                    stop,
                    digest,
                    publisher.epoch,
                ),
            )
            taken.append((frozenset(prior - confirmed), confirmed))
            return publisher.job, {
                "issuance": identity,
                "ordinal": ordinal,
                "revision": revision,
                "start": start,
                "stop": stop,
            }

        result = _advance(
            publisher, _operate(workspace, operation, "issue_stream", request, effect)
        )
        if result.observation != "COMMITTED_THIS_CALL":
            raise JobStoreError("STREAM_ISSUANCE_REPLAYED")
        prior, confirmed = taken[0]
        issued = Issued(
            self,
            result.get("issuance"),
            window,
            delivery,
            start,
            stop,
            effects,
            prior,
            confirmed,
            source,
        )
        self._pending = None if issued.resolved else issued
        return issued

    def next(self, rows: int, *, operation: str) -> Issued | Waiting:
        """Read, check and locally issue the next committed contiguous occurrences
        of the latest adopted window, or report WAITING_FOR_COMMITTED_CHECKPOINT."""
        workspace = self._use()
        if self._pending is not None:
            raise JobStoreError("DELIVERY_PENDING")
        self._authority()
        window, start = self.window, self._position
        if window is None or start >= window.stop:
            return self._waiting(workspace)
        acceptance = self.window_acceptance
        assert acceptance is not None
        if type(rows) is not int or not 1 <= rows <= acceptance.batch_rows:
            raise JobStoreError("STREAM_ROWS")
        stop = min(start + rows, window.stop)
        self._live()
        batch, coordinates, _held, _schema = replay._rebatch(self, start, stop)
        try:
            self._authority()
            payloads = _payloads(batch, coordinates)
        finally:
            batch.close()
        return self._issue(
            self._effects(start, payloads), start, stop, window, None, None, operation
        )

    def bridge(self, delivery, *, operation: str) -> Issued:
        """Locally issue the occurrences of one actual pending S13 Delivery."""
        self._use()
        if self._pending is not None:
            raise JobStoreError("DELIVERY_PENDING")
        if (
            type(delivery) is not replay.Delivery
            or delivery.replay._pid != os.getpid()
            or delivery.replay._pending is not delivery
        ):
            raise JobStoreError("DELIVERY_FOREIGN")
        source = replay._accepted(delivery.replay.acceptance)
        facts = self.facts
        if (
            source.workspace,
            source.job,
            source.generation,
            source.route,
            layout(source._output, source._refinement),
        ) != (facts.workspace, facts.job, facts.generation, facts.route, facts.layout):
            raise JobStoreError("ACCEPTANCE_SUBJECT")
        _accepted(self.sink, SinkAcceptance)
        payloads = _payloads(delivery.batch, delivery.coordinates)
        if len(payloads) != delivery.stop - delivery.start:
            raise JobStoreError("DELIVERY_FOREIGN")
        return self._issue(
            self._effects(delivery.start, payloads),
            delivery.start,
            delivery.stop,
            None,
            delivery.identity,
            delivery,
            operation,
        )

    def _validated(self, issued, effect, reply, kind) -> tuple[str, Any]:
        """A sink reply is data: exact destination, key, row digest and record."""
        if (
            type(reply) is not SinkReply
            or reply.kind != kind
            or (reply.sink, reply.namespace, reply.epoch, reply.retention)
            != (effect.sink, effect.namespace, effect.epoch, effect.retention)
            or (reply.workspace, reply.generation, reply.position)
            != (effect.workspace, effect.generation, effect.position)
        ):
            return ("UNKNOWN", "SINK_REPLY_FOREIGN")
        if reply.status in CONFLICTED:
            return ("CONFLICT", reply)
        if reply.status in UNAVAILABLE:
            return ("UNAVAILABLE", reply)
        if reply.status == "ACTIVE_NOT_FOUND" and kind == "query":
            return ("ABSENT", reply)
        if (
            reply.status not in CONFIRMED
            or (reply.status == "PRESENT_MATCHING") != (kind == "query")
            or reply.digest != issued._digests[effect.position]
            or not valid_identity(reply.commit, "skc")
            or type(reply.sequence) is not int
            or reply.sequence < 1
        ):
            return ("UNKNOWN", "SINK_REPLY_INVALID")
        return (reply.status, reply)

    def _submit(self, issued, effect) -> tuple[str, Any]:
        try:
            reply = self.sink._handle.submit(effect)
        except JobStoreError as error:
            return ("UNKNOWN", str(error))
        return self._validated(issued, effect, reply, "submit")

    def _reconcile(self, issued, effect) -> tuple[str, Any]:
        """One query; only if the exact incarnation reports the key absent, one
        resubmission of the same key and payload under current authority."""
        try:
            reply = self.sink._handle.query(effect)
        except JobStoreError as error:
            return ("UNKNOWN", str(error))
        outcome = self._validated(issued, effect, reply, "query")
        if outcome[0] != "ABSENT":
            return outcome
        try:
            self._live(issued)
        except JobStoreError as error:
            return ("NOT_SENT", str(error))
        return self._submit(issued, effect)

    def send(self, issued: Issued) -> dict[int, str]:
        """One action per unconfirmed occurrence, outside any job-store
        transaction and after a live recheck each: an original submission, or for
        an occurrence issued before with an unknown outcome, reconciliation."""
        self._use()
        self._own(issued)
        for effect in issued.effects:
            position = effect.position
            if position in issued._done or position in issued._outcomes:
                continue
            try:
                self._live(issued)
            except JobStoreError as error:
                issued._outcomes[position] = ("NOT_SENT", str(error))
                break
            if position in issued.prior:
                issued._outcomes[position] = self._reconcile(issued, effect)
            else:
                issued._outcomes[position] = self._submit(issued, effect)
        return {p: o[0] for p, o in issued._outcomes.items()}

    def reconcile(self, issued: Issued) -> dict[int, str]:
        """For each occurrence whose outcome is unknown here: one query and at most
        one same-identity resubmission. Still unknown stays unresolved."""
        self._use()
        self._own(issued)
        for effect in issued.effects:
            position = effect.position
            current = issued._outcomes.get(position)
            if position in issued._done or (
                current is not None and current[0] not in ("UNKNOWN", "NOT_SENT")
            ):
                continue
            try:
                self._live(issued)
            except JobStoreError as error:
                issued._outcomes[position] = ("NOT_SENT", str(error))
                break
            issued._outcomes[position] = self._reconcile(issued, effect)
        return {p: o[0] for p, o in issued._outcomes.items()}

    def confirm(self, issued: Issued, *, operation: str) -> OperationResult:
        """Append the validated sink observations of this issuance under the fence."""
        workspace = self._use()
        self._own(issued)
        observations = []
        for position, (status, reply) in sorted(issued._outcomes.items()):
            if status in CONFIRMED and position not in issued._done:
                observations.append(
                    [
                        position,
                        "QUERY" if status == "PRESENT_MATCHING" else "REPLY",
                        status,
                        reply.commit,
                        reply.sequence,
                        reply.digest,
                    ]
                )
        if not observations:
            raise JobStoreError("STREAM_NOTHING_TO_CONFIRM")
        publisher, facts = self.publisher, self.facts
        request = _identity_request(
            publisher,
            stream=facts.identity,
            session=self.identity,
            issuance=issued.identity,
            observations=observations,
        )

        def effect(c):
            revision = _fence(c, publisher, _FENCE)
            _accepted(self.sink, SinkAcceptance)
            self._current(c)
            self._protected(c, issued)
            row = c.execute(
                "SELECT start, stop FROM stream_issuance WHERE identity = ?"
                " AND session = ? AND stream = ?",
                (issued.identity, self.identity, facts.identity),
            ).fetchone()
            if row is None:
                raise JobStoreError("ISSUANCE_FOREIGN")
            _bound(c, "sink_observation")
            added = 0
            for position, basis, status, commit, sequence, digest in observations:
                if not row[0] <= position < row[1]:
                    raise JobStoreError("SINK_OBSERVATION_FOREIGN")
                existing = c.execute(
                    "SELECT commit_identity, digest FROM sink_observation"
                    " WHERE stream = ? AND position = ?",
                    (facts.identity, position),
                ).fetchone()
                if existing is not None:
                    # A matching repeated observation never counts twice.
                    if existing != (commit, digest):
                        raise JobStoreError("SINK_OBSERVATION_CONFLICT")
                    continue
                if c.execute(
                    "SELECT 1 FROM sink_observation WHERE stream = ?"
                    " AND commit_identity = ?",
                    (facts.identity, commit),
                ).fetchone():
                    raise JobStoreError("SINK_OBSERVATION_CONFLICT")
                c.execute(
                    "INSERT INTO sink_observation(stream, position, issuance, session,"
                    " basis, status, commit_identity, commit_sequence, digest,"
                    " publisher_epoch) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        facts.identity,
                        position,
                        issued.identity,
                        self.identity,
                        basis,
                        status,
                        commit,
                        sequence,
                        digest,
                        publisher.epoch,
                    ),
                )
                added += 1
            return publisher.job, {
                "confirmed": added,
                "issuance": issued.identity,
                "position": _frontier(c, facts.identity),
                "revision": revision,
            }

        result = _advance(
            publisher, _operate(workspace, operation, "confirm_sink", request, effect)
        )
        issued._done.update(o[0] for o in observations)
        self._position = result.get("position")
        if self._pending is issued and issued.resolved:
            self._pending = None
        return result

    def acknowledge(self, issued: Issued, *, operation: str) -> OperationResult:
        """The original explicit S13 acknowledgement, only after every occurrence
        of that Delivery is durably confirmed by this sink."""
        workspace = self._use()
        self._own(issued)
        delivery = issued._source
        if delivery is None:
            raise JobStoreError("STREAM_NOT_BRIDGED")
        count = read(
            workspace,
            lambda c: c.execute(
                "SELECT count(*) FROM sink_observation WHERE stream = ?"
                " AND position >= ? AND position < ?",
                (self.facts.identity, issued.start, issued.stop),
            ).fetchone()[0],
        )
        if count != issued.stop - issued.start:
            raise JobStoreError("STREAM_UNCONFIRMED")
        return delivery.replay.acknowledge(delivery, operation=operation)

    def adopt(self, window: WindowAcceptance, *, operation: str) -> OperationResult:
        """Protect one more checkpoint as the next window of this stream.

        The first window starts at 0; a later one must be a verified extension of
        the latest (its members kept, a later ordinal, frontier not smaller) and
        is admitted only once every occurrence below the latest stop is
        confirmed. A replayed operation returns its historical fact only.
        """
        workspace = self._use()
        acceptance = _accepted(window, WindowAcceptance)
        if acceptance.checkpoint is None:
            raise JobStoreError("CHECKPOINT_UNKNOWN")
        facts, publisher = self.facts, self.publisher
        _correspond(facts, acceptance)
        _accepted(self.sink, SinkAcceptance)
        scope = _scope({"purpose": acceptance.purpose, "stream": facts.identity})
        request = _identity_request(
            publisher,
            stream=facts.identity,
            session=self.identity,
            checkpoint=acceptance.checkpoint,
            scope=scope,
        )
        taken = []

        def effect(c):
            revision = _fence(c, publisher, _FENCE)
            _accepted(acceptance, WindowAcceptance)
            _accepted(self.sink, SinkAcceptance)
            self._current(c)
            _bound(c, "stream_window")
            latest = _latest_window(c, facts.identity)
            new = _snapshot(
                c, workspace, facts.job, facts.generation, acceptance.checkpoint
            )
            if latest is not None:
                if latest.checkpoint == acceptance.checkpoint:
                    raise JobStoreError("STREAM_WINDOW_CURRENT")
                if _frontier(c, facts.identity) < latest.stop:
                    raise JobStoreError("STREAM_WINDOW_UNCONFIRMED")
                old = _snapshot(
                    c, workspace, facts.job, facts.generation, latest.checkpoint
                )
                if (
                    new.ordinal <= old.ordinal
                    or not {m.chunk for m in old.members}
                    <= {m.chunk for m in new.members}
                    or new.frontier < latest.stop
                ):
                    raise JobStoreError("STREAM_WINDOW_EXTENSION")
            retention, snapshot = _retain(
                c, workspace, publisher, facts.generation, acceptance.checkpoint, scope
            )
            ordinal = 1 if latest is None else latest.ordinal + 1
            start = 0 if latest is None else latest.stop
            c.execute(
                "INSERT INTO stream_window(stream, ordinal, previous, generation,"
                " checkpoint, retention, start, stop, publisher_epoch)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    facts.identity,
                    ordinal,
                    None if latest is None else latest.ordinal,
                    facts.generation,
                    snapshot.checkpoint,
                    retention,
                    start,
                    snapshot.frontier,
                    publisher.epoch,
                ),
            )
            taken.append(replace(snapshot, retention=retention))
            return publisher.job, {
                "checkpoint": snapshot.checkpoint,
                "ordinal": ordinal,
                "retention": retention,
                "revision": revision,
                "start": start,
                "stop": snapshot.frontier,
            }

        result = _advance(
            publisher,
            _operate(
                workspace,
                operation,
                "adopt_window",
                request,
                effect,
                payload=len(scope),
            ),
        )
        if taken:
            snapshot = taken[0]
            if self._reader is not None:
                self._reader.close()
            self._reader, self._held = None, None
            self.window_acceptance, self.snapshot = acceptance, snapshot
            self.window = WindowFacts(
                result.get("ordinal"),
                result.get("checkpoint"),
                result.get("retention"),
                result.get("start"),
                result.get("stop"),
            )
        return result

    def close(self) -> None:
        """Release local resources only: never a confirmation, ACK or release."""
        if self._closed or self._pid != os.getpid():
            return
        self._closed = True
        self._held = self._pending = None
        if self._reader is not None:
            self._reader.close()


def retire_stream(
    publisher: Publisher, stream: str, *, operation: str
) -> OperationResult:
    """Release every window's protection (metadata only) once no issued occurrence
    is unresolved; otherwise keep protecting and refuse. Nothing is deleted."""
    workspace = publisher.use()
    _delivering(workspace)
    if not valid_identity(stream, "stm"):
        raise JobStoreError("STREAM_UNKNOWN")

    def effect(c):
        revision = _fence(c, publisher, _FENCE_CONTROL)
        _stream(c, workspace, publisher.job, stream)
        if _unresolved(c, stream):
            raise JobStoreError("STREAM_OBLIGATION_UNRESOLVED")
        position = _frontier(c, stream)
        c.execute(
            "INSERT INTO stream_retirement(stream, position, publisher_epoch,"
            " publisher_instance) VALUES (?, ?, ?, ?)",
            (stream, position, publisher.epoch, publisher.instance),
        )
        released = 0
        for (retention,) in c.execute(
            "SELECT retention FROM stream_window WHERE stream = ? ORDER BY ordinal",
            (stream,),
        ).fetchall():
            if not _released(c, retention):
                c.execute(
                    "INSERT INTO retention_release(retention, publisher_epoch,"
                    " publisher_instance) VALUES (?, ?, ?)",
                    (retention, publisher.epoch, publisher.instance),
                )
                released += 1
        return publisher.job, {
            "position": position,
            "released": released,
            "revision": revision,
            "stream": stream,
        }

    return _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "retire_stream",
            _identity_request(publisher, stream=stream),
            effect,
            control=True,
        ),
    )


def relay(
    session: StreamSession, capture: CaptureSession, *, rows: int, **window
) -> str:
    """One synchronous step of provisional delivery for one owner and publisher.

    A pending unresolved batch blocks: no further source batch is pulled.
    Committed occurrences of the adopted window are delivered first; only when
    it is drained is exactly one more checked source batch staged, committed and
    adopted as the next window with a fresh window acceptance (`window` holds
    the caller's fresh trust inputs). Returns BLOCKED, DELIVERED,
    COMMITTED_CHUNK or SOURCE_TERMINAL; none of them is EOF or publication.
    """
    if (
        type(capture) is not CaptureSession
        or capture.publisher is not session.publisher
        or capture.attempt.generation != session.facts.generation
    ):
        raise JobStoreError("STREAM_CAPTURE")
    if session.pending is not None:
        return "BLOCKED"
    if session.window is not None:
        # Committed occurrences of the adopted window come first; without read
        # permission for it nothing more is pulled from the source.
        if session.window_acceptance is None:
            raise JobStoreError("STREAM_READ_REQUIRED")
        item = session.next(rows, operation=new_operation())
        if isinstance(item, Issued):
            if any(s in CONFIRMED for s in session.send(item).values()):
                session.confirm(item, operation=new_operation())
            return "DELIVERED" if item.resolved else "BLOCKED"
    if capture.terminal is not None:
        return "SOURCE_TERMINAL"
    staged = capture.stage()
    if staged is None:
        return "SOURCE_TERMINAL"
    result = capture.publish(staged, operation=new_operation())
    facts = session.facts
    acceptance = accept_window(
        session.publisher.use(),
        facts.job,
        facts.generation,
        checkpoint=result.get("checkpoint"),
        **window,
    )
    session.adopt(acceptance, operation=new_operation())
    return "COMMITTED_CHUNK"
