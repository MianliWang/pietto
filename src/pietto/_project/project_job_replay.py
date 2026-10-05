"""S13 R1 saved-result recovery over one immutable S12 checkpoint.

R1 consumes occurrences that a capture already saved; it never queries,
requalifies or re-evaluates a source. Reading a saved copy needs a fresh
process-local caller acceptance, distinct from any source authority. A consumer
is bound to one exact checkpoint and fixed saved extent [0, extent); its durable
progress is only the contiguous acknowledged prefix. An issued range that was
never acknowledged may be issued again, with the same (generation, position)
occurrence labels. A local acknowledgement is the caller's statement plus a
local COMMIT: never a sink effect, remote ACK, source EOF, whole-query success or
generation publication. Closing releases local resources only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import time
from typing import Any
import weakref

from pietto._project import project_job_chunks as chunks
from pietto._project.project_job_capture import (
    SnapshotReader,
    _retain,
    _scope,
    _snapshot,
    arrow_output,
    checkpoint_snapshot,
    contract_digest,
    coordinate_scheme,
    frontier,
    holes,
    stored_binding,
)
from pietto._project.project_job_store import (
    _FENCE,
    OperationResult,
    Publisher,
    _advance,
    _fence,
    _identity_request,
    _operate,
    _vector,
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

MODES = ("complete_capture", "committed_prefix")
EXHAUSTED = "SAVED_SCOPE_EXHAUSTED"
MAX_ACCEPTANCE_SECONDS = 86400
MAX_PURPOSE_BYTES = 256
# The trusted host clocks. Tests inject explicit boundaries; callers cannot.
_wall = time.time
_monotonic = time.monotonic
_ACCEPTED: weakref.WeakSet = weakref.WeakSet()


def _replaying(workspace: Workspace) -> None:
    if not supports(workspace, "saved-replay"):
        raise JobStoreError("WORKSPACE_REPLAY_FORMAT")


def new_consumer() -> str:
    """Allocate a consumer identity before binding its acceptance."""
    return new_identity("csm")


@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class SavedReadAcceptance:
    """A process-local caller acceptance to read one saved result; never stored.

    It is a read capability inside the private cooperating-user boundary, not
    source authority or proof of any organization's policy. No stored row,
    receipt, copy or recovered record mints one; identities authenticate nobody.
    """

    workspace: str
    job: str
    generation: str
    checkpoint: str
    consumer: str
    scope: str
    extent: int
    purpose: str
    route: str
    batch_rows: int
    seconds: int
    accepted_at: float
    _output: Any = field(repr=False)
    _refinement: Any = field(repr=False)
    _deadline: float = field(repr=False)
    _pid: int = field(repr=False)

    def __reduce_ex__(self, protocol):
        raise JobStoreError("ACCEPTANCE_COPY")


def _accepted(acceptance) -> SavedReadAcceptance:
    """Issued here, by this process, and within both validity bounds now."""
    if type(acceptance) is not SavedReadAcceptance or acceptance not in _ACCEPTED:
        raise JobStoreError("ACCEPTANCE_UNKNOWN")
    if acceptance._pid != os.getpid():
        raise JobStoreError("ACCEPTANCE_FOREIGN_PROCESS")
    # A wall-clock rollback cannot lengthen it: the monotonic deadline also binds.
    if not (
        _monotonic() < acceptance._deadline
        and _wall() < acceptance.accepted_at + acceptance.seconds
    ):
        raise JobStoreError("ACCEPTANCE_EXPIRED")
    return acceptance


def accept_saved_read(
    workspace: Workspace,
    job: str,
    generation: str,
    *,
    checkpoint: str,
    consumer: str,
    scope: str,
    extent: int,
    purpose: str,
    route: str,
    values,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: tuple,
    seconds: int,
    batch_rows: int,
) -> SavedReadAcceptance:
    """Fresh trust, exact binding/output correspondence and bounded validity."""
    from pietto._project.project_execution import compiled_output
    from pietto._project.project_execution_template import bind_values

    _replaying(workspace)
    if not valid_identity(consumer, "csm"):
        raise JobStoreError("CONSUMER_IDENTITY")
    if not valid_identity(checkpoint, "ckp"):
        raise JobStoreError("CHECKPOINT_UNKNOWN")
    if scope not in MODES or type(extent) is not int or extent < 0:
        raise JobStoreError("CONSUMER_SCOPE")
    if (
        type(purpose) is not str
        or not purpose
        or not purpose.isprintable()
        or len(purpose.encode("utf-8")) > MAX_PURPOSE_BYTES
    ):
        raise JobStoreError("ACCEPTANCE_PURPOSE")
    if (
        type(seconds) is not int
        or not 1 <= seconds <= MAX_ACCEPTANCE_SECONDS
        or type(batch_rows) is not int
        or not 1 <= batch_rows <= chunks.MAX_ROWS
    ):
        raise JobStoreError("ACCEPTANCE_BOUND")
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
    snapshot = checkpoint_snapshot(workspace, job, generation, checkpoint=checkpoint)
    if (snapshot.contract, snapshot.scheme) != (
        contract_digest(output),
        coordinate_scheme(refinement),
    ):
        raise JobStoreError("READER_SNAPSHOT")
    _covered(snapshot, scope, extent)
    acceptance = SavedReadAcceptance(
        workspace.identity,
        job,
        generation,
        checkpoint,
        consumer,
        scope,
        extent,
        purpose,
        route,
        batch_rows,
        seconds,
        _wall(),
        output,
        refinement,
        _monotonic() + seconds,
        os.getpid(),
    )
    _ACCEPTED.add(acceptance)
    return acceptance


def _subject(acceptance, workspace, publisher) -> None:
    if (acceptance.workspace, acceptance.job) != (workspace.identity, publisher.job):
        raise JobStoreError("ACCEPTANCE_SUBJECT")


def _covered(snapshot, scope, extent) -> None:
    """The extent is recomputed by the checkpoint rules, never a cursor claim."""
    if snapshot.frontier != extent:
        raise JobStoreError("ACCEPTANCE_EXTENT")
    # Complete capture is row coverage (recorded EOF, known end, no hole and a
    # schema-bearing member when empty); it is not remote transaction success.
    if scope == "complete_capture" and (
        snapshot.session_source != "EOF"
        or snapshot.observed_end != extent
        or snapshot.holes
        or not snapshot.members
    ):
        raise JobStoreError("CONSUMER_SCOPE")


def register_consumer(
    publisher: Publisher,
    acceptance: SavedReadAcceptance,
    *,
    operation: str,
    not_after: int | None = None,
) -> OperationResult:
    """Atomically protect the exact checkpoint and register a fixed-scope consumer."""
    workspace = publisher.use()
    _replaying(workspace)
    acceptance = _accepted(acceptance)
    _subject(acceptance, workspace, publisher)
    if not_after is not None and (
        type(not_after) is not int or not_after <= 0 or not_after <= _wall()
    ):
        raise JobStoreError("CONSUMER_EXPIRED")
    consumer = acceptance.consumer
    scope = _scope({"consumer": consumer, "purpose": acceptance.purpose})
    request = _identity_request(
        publisher,
        consumer=consumer,
        generation=acceptance.generation,
        checkpoint=acceptance.checkpoint,
        scope=acceptance.scope,
        extent=acceptance.extent,
        purpose=acceptance.purpose,
        not_after=not_after,
    )

    def effect(c):
        revision = _fence(c, publisher, _FENCE)
        if c.execute(
            "SELECT 1 FROM consumer WHERE identity = ?", (consumer,)
        ).fetchone():
            raise JobStoreError("CONSUMER_EXISTS")
        retention, snapshot = _retain(
            c, workspace, publisher, acceptance.generation, acceptance.checkpoint, scope
        )
        _covered(snapshot, acceptance.scope, acceptance.extent)
        c.execute(
            "INSERT INTO consumer(identity, job, generation, checkpoint, binding,"
            " retention, scope, extent, purpose, not_after, publisher_epoch,"
            " publisher_instance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                consumer,
                publisher.job,
                acceptance.generation,
                snapshot.checkpoint,
                snapshot.binding,
                retention,
                acceptance.scope,
                acceptance.extent,
                acceptance.purpose,
                not_after,
                publisher.epoch,
                publisher.instance,
            ),
        )
        return publisher.job, {
            "checkpoint": snapshot.checkpoint,
            "consumer": consumer,
            "extent": acceptance.extent,
            "retention": retention,
            "revision": revision,
        }

    return _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "register_consumer",
            request,
            effect,
            payload=len(scope),
        ),
    )


def _progress(ranges, extent=None) -> int:
    """The derived acknowledged frontier; any gap, overlap or excess refuses."""
    reached = frontier(ranges)
    if (
        holes(ranges)
        or sum(b - a for a, b in ranges) != reached
        or (extent is not None and reached > extent)
    ):
        raise JobStoreError("CONSUMER_PROGRESS")
    return reached


def _reached(c, consumer) -> int:
    # Acknowledgements form one chain from 0 (schema foreign key), so max(stop)
    # is the frontier; open_replay and the verifier recheck the whole chain.
    return c.execute(
        "SELECT coalesce(max(stop), 0) FROM acknowledgement WHERE consumer = ?",
        (consumer,),
    ).fetchone()[0]


def _consumer(c, workspace, job, acceptance):
    """The registered facts equal this acceptance; retention and expiry now."""
    row = c.execute(
        "SELECT k.generation, k.checkpoint, k.binding, k.retention, k.scope, k.extent,"
        " k.purpose, k.not_after, r.checkpoint,"
        " (SELECT count(*) FROM retention_release x WHERE x.retention = k.retention)"
        " FROM consumer k JOIN retention r ON r.identity = k.retention"
        " WHERE k.identity = ? AND k.job = ?",
        (acceptance.consumer, job),
    ).fetchone()
    if row is None:
        raise JobStoreError("CONSUMER_UNKNOWN")
    if (row[0], row[1], row[4], row[5], row[6]) != (
        acceptance.generation,
        acceptance.checkpoint,
        acceptance.scope,
        acceptance.extent,
        acceptance.purpose,
    ):
        raise JobStoreError("ACCEPTANCE_SUBJECT")
    if row[9]:
        raise JobStoreError("CONSUMER_RELEASED")
    if row[7] is not None and _wall() >= row[7]:
        raise JobStoreError("CONSUMER_EXPIRED")
    snapshot = _snapshot(c, workspace, job, row[0], row[1], row[3])
    if (snapshot.binding, row[8]) != (row[2], row[1]):
        raise JobStoreError("CONSUMER_SCOPE")
    _covered(snapshot, row[4], row[5])
    return snapshot


def open_replay(
    publisher: Publisher, acceptance: SavedReadAcceptance, *, operation: str
) -> ReplaySession:
    """A new durable session; every older session of the consumer is superseded."""
    workspace = publisher.use()
    _replaying(workspace)
    acceptance = _accepted(acceptance)
    _subject(acceptance, workspace, publisher)
    request = _identity_request(
        publisher,
        consumer=acceptance.consumer,
        accepted_at=int(acceptance.accepted_at),
        seconds=acceptance.seconds,
        batch_rows=acceptance.batch_rows,
    )
    taken = []

    def effect(c):
        revision = _fence(c, publisher, _FENCE)
        snapshot = _consumer(c, workspace, publisher.job, acceptance)
        position = _progress(
            c.execute(
                "SELECT start, stop FROM acknowledgement WHERE consumer = ?",
                (acceptance.consumer,),
            ).fetchall(),
            acceptance.extent,
        )
        ordinal = c.execute(
            "SELECT coalesce(max(ordinal), 0) + 1 FROM replay_session WHERE consumer = ?",
            (acceptance.consumer,),
        ).fetchone()[0]
        identity = new_identity("rps")
        c.execute(
            "INSERT INTO replay_session(identity, consumer, ordinal, position,"
            " accepted_at, seconds, batch_rows, publisher_epoch, publisher_instance)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                identity,
                acceptance.consumer,
                ordinal,
                position,
                int(acceptance.accepted_at),
                acceptance.seconds,
                acceptance.batch_rows,
                publisher.epoch,
                publisher.instance,
            ),
        )
        taken.append(snapshot)
        return publisher.job, {
            "ordinal": ordinal,
            "position": position,
            "revision": revision,
            "session": identity,
        }

    result = _advance(
        publisher, _operate(workspace, operation, "open_replay", request, effect)
    )
    if result.observation != "COMMITTED_THIS_CALL":
        raise JobStoreError("REPLAY_REPLAYED")
    return ReplaySession(
        publisher,
        acceptance,
        result.get("session"),
        result.get("ordinal"),
        result.get("position"),
        taken[0],
    )


def _current(c, replay) -> None:
    """The latest session of its consumer, by this publisher, still eligible now."""
    _accepted(replay.acceptance)
    row = c.execute(
        "SELECT s.ordinal, s.publisher_epoch, s.publisher_instance,"
        " (SELECT max(ordinal) FROM replay_session WHERE consumer = s.consumer),"
        " k.not_after,"
        " (SELECT count(*) FROM retention_release x WHERE x.retention = k.retention)"
        " FROM replay_session s JOIN consumer k ON k.identity = s.consumer"
        " WHERE s.identity = ? AND k.job = ?",
        (replay.identity, replay.publisher.job),
    ).fetchone()
    if row is None:
        raise JobStoreError("REPLAY_SESSION_UNKNOWN")
    if row[0] != row[3] or (row[1], row[2]) != (
        replay.publisher.epoch,
        replay.publisher.instance,
    ):
        raise JobStoreError("REPLAY_SESSION_STALE")
    if row[5]:
        raise JobStoreError("CONSUMER_RELEASED")
    if row[4] is not None and _wall() >= row[4]:
        raise JobStoreError("CONSUMER_EXPIRED")


def plan(members, start, stop) -> tuple[tuple[int, int, int], ...]:
    """(member index, offset, rows) slices covering [start, stop) without a hole."""
    result, position = [], start
    for index, member in enumerate(members):
        if position == stop:
            break
        if member.stop <= position:
            continue
        if member.start > position:
            break
        end = min(member.stop, stop)
        result.append((index, position - member.start, end - position))
        position = end
    if position != stop:
        raise JobStoreError("CHECKPOINT_MEMBERS")
    return tuple(result)


def _rebatch(replay, start, stop) -> tuple[Any, tuple | None, int, Any]:
    """Checked member slices -> one owned output batch; only needed members held.

    Each needed member is fully decoded and value-checked before any of its rows
    is used; an empty extent checks the schema-bearing zero-row member instead.
    Returns (batch, coordinates, held_bytes, schema).
    """
    from pietto._project.project_arrow_interop import manage_batch
    from pietto._project.project_arrow_result import _arrow

    if start == stop:
        return None, None, 0, replay._chunk(0).table.schema
    parts, coordinates = [], []
    for index, offset, rows in plan(replay.snapshot.members, start, stop):
        checked = replay._chunk(index)
        batches = checked.table.to_batches()
        if len(batches) != 1:
            raise JobStoreError("CHUNK_DESCRIPTOR")
        parts.append(batches[0].slice(offset, rows))
        if checked.coordinates is not None:
            coordinates.extend(checked.coordinates[offset : offset + rows])
    joined = parts[0] if len(parts) == 1 else _arrow().concat_batches(parts)
    # A slice may keep its whole parent buffers alive: account what is held.
    held = sum(
        buffer.size
        for column in joined.columns
        for buffer in column.buffers()
        if buffer is not None
    )
    refined = replay.snapshot.kind == "REFINED"
    batch = manage_batch(replay._open_reader().output.binding, joined)
    return batch, tuple(coordinates) if refined else None, held, joined.schema


@dataclass(frozen=True, slots=True, eq=False)
class Delivery:
    """One issued, checked extent. Delivery, session and operation identities may
    differ on recovery; the (generation, position) occurrence labels never do."""

    replay: Any = field(repr=False)
    identity: str
    session: str
    operation: str
    consumer: str
    generation: str
    checkpoint: str
    start: int
    stop: int
    batch: Any = field(repr=False)
    coordinates: tuple | None = field(repr=False)
    held_bytes: int

    @property
    def occurrences(self) -> tuple[tuple[str, int], ...]:
        return tuple((self.generation, p) for p in range(self.start, self.stop))


@dataclass(frozen=True, slots=True)
class SavedScopeEnd:
    """This fixed local scope has no more rows. It is not source EOF, whole-query
    success, a sink effect or generation publication; layers stay as recorded."""

    terminal: str
    consumer: str
    generation: str
    checkpoint: str
    scope: str
    extent: int
    acknowledged: int
    verified: tuple[int, int]
    schema: Any = field(repr=False)
    observed_end: int | None
    holes: tuple[tuple[int, int], ...]
    layers: tuple[tuple[str, Any], ...]


class ReplaySession:
    """One process-local replay of one consumer; never passed to another process."""

    __slots__ = (
        "publisher",
        "acceptance",
        "identity",
        "ordinal",
        "start",
        "snapshot",
        "_position",
        "_pending",
        "_reader",
        "_held",
        "_pid",
        "_closed",
    )

    def __init__(self, publisher, acceptance, identity, ordinal, position, snapshot):
        self.publisher = publisher
        self.acceptance = acceptance
        self.identity = identity
        self.ordinal = ordinal
        self.start = position
        self.snapshot = snapshot
        self._position = position
        self._pending: Delivery | None = None
        self._reader: SnapshotReader | None = None
        self._held: tuple[int, Any] | None = None
        self._pid = os.getpid()
        self._closed = False

    def __repr__(self) -> str:
        return f"ReplaySession(identity={self.identity!r})"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False

    @property
    def position(self) -> int:
        """The acknowledged frontier known to this session (never the issued one)."""
        return self._position

    def _use(self) -> Workspace:
        if self._pid != os.getpid():
            raise JobStoreError("REPLAY_FOREIGN_PROCESS")
        if self._closed:
            raise JobStoreError("REPLAY_CLOSED")
        return self.publisher.use()

    def _open_reader(self) -> SnapshotReader:
        if self._reader is None:
            a = self.acceptance
            output = arrow_output(
                a.job, a.generation, a._output, a._refinement, a.route
            )
            self._reader = SnapshotReader(self.publisher.use(), self.snapshot, output)
        return self._reader

    def _chunk(self, index):
        if self._held is None or self._held[0] != index:
            self._held = None
            self._held = (index, self._open_reader().read(index))
        return self._held[1]

    def next(self, rows: int, *, operation: str) -> Delivery | SavedScopeEnd:
        """Read, check and issue the next extent, or report the saved-scope end."""
        workspace = self._use()
        if self._pending is not None:
            raise JobStoreError("DELIVERY_PENDING")
        acceptance = _accepted(self.acceptance)
        start, extent = self._position, acceptance.extent
        if start == extent:
            return self._end(workspace)
        if type(rows) is not int or not 1 <= rows <= acceptance.batch_rows:
            raise JobStoreError("REPLAY_ROWS")
        stop = min(start + rows, extent)
        batch, coordinates, held, _schema = _rebatch(self, start, stop)
        publisher, consumer = self.publisher, acceptance.consumer
        request = _identity_request(
            publisher, consumer=consumer, session=self.identity, start=start, stop=stop
        )

        def effect(c):
            revision = _fence(c, publisher, _FENCE)
            _current(c, self)
            if c.execute(
                "SELECT 1 FROM issuance i WHERE i.session = ? AND NOT EXISTS"
                " (SELECT 1 FROM acknowledgement a WHERE a.issuance = i.identity)",
                (self.identity,),
            ).fetchone():
                raise JobStoreError("DELIVERY_PENDING")
            if _reached(c, consumer) != start:
                raise JobStoreError("CONSUMER_PROGRESS")
            ordinal = c.execute(
                "SELECT count(*) + 1 FROM issuance WHERE session = ?", (self.identity,)
            ).fetchone()[0]
            identity = new_identity("dlv")
            c.execute(
                "INSERT INTO issuance(identity, consumer, session, ordinal, start, stop,"
                " publisher_epoch) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    identity,
                    consumer,
                    self.identity,
                    ordinal,
                    start,
                    stop,
                    publisher.epoch,
                ),
            )
            return publisher.job, {
                "delivery": identity,
                "ordinal": ordinal,
                "revision": revision,
                "start": start,
                "stop": stop,
            }

        try:
            result = _advance(
                publisher,
                _operate(workspace, operation, "issue_delivery", request, effect),
            )
            if result.observation != "COMMITTED_THIS_CALL":
                raise JobStoreError("DELIVERY_REPLAYED")
        except BaseException:
            # Only a known committed issuance exposes data to the caller.
            batch.close()
            raise
        delivery = Delivery(
            self,
            result.get("delivery"),
            self.identity,
            operation,
            consumer,
            acceptance.generation,
            acceptance.checkpoint,
            start,
            stop,
            batch,
            coordinates,
            held,
        )
        self._pending = delivery
        return delivery

    def acknowledge(self, delivery: Delivery, *, operation: str) -> OperationResult:
        """Commit local progress for exactly this issued extent; no IO inside."""
        workspace = self._use()
        if type(delivery) is not Delivery or delivery.replay is not self:
            raise JobStoreError("DELIVERY_FOREIGN")
        publisher = self.publisher
        consumer, extent = self.acceptance.consumer, self.acceptance.extent
        request = _identity_request(
            publisher,
            consumer=consumer,
            session=self.identity,
            delivery=delivery.identity,
            start=delivery.start,
            stop=delivery.stop,
        )

        def effect(c):
            revision = _fence(c, publisher, _FENCE)
            _current(c, self)
            row = c.execute(
                "SELECT start, stop,"
                " (SELECT count(*) FROM acknowledgement WHERE issuance = identity)"
                " FROM issuance WHERE identity = ? AND session = ? AND consumer = ?",
                (delivery.identity, self.identity, consumer),
            ).fetchone()
            if row is None:
                raise JobStoreError("DELIVERY_FOREIGN")
            if row[2]:
                raise JobStoreError("DELIVERY_ACKNOWLEDGED")
            if (
                (row[0], row[1]) != (delivery.start, delivery.stop)
                or delivery.start != _reached(c, consumer)
                or delivery.stop > extent
            ):
                raise JobStoreError("CONSUMER_PROGRESS")
            c.execute(
                "INSERT INTO acknowledgement(issuance, consumer, session, start, stop,"
                " previous, publisher_epoch) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    delivery.identity,
                    consumer,
                    self.identity,
                    delivery.start,
                    delivery.stop,
                    delivery.start or None,
                    publisher.epoch,
                ),
            )
            return publisher.job, {
                "delivery": delivery.identity,
                "position": delivery.stop,
                "revision": revision,
            }

        result = _advance(
            publisher,
            _operate(workspace, operation, "acknowledge_delivery", request, effect),
        )
        if self._pending is delivery:
            self._pending = None
            self._position = delivery.stop
        return result

    def _end(self, workspace) -> SavedScopeEnd:
        acceptance = self.acceptance
        publisher = self.publisher

        def live(c):
            row = c.execute(
                "SELECT state, publisher_epoch, publisher_instance FROM job"
                " WHERE identity = ?",
                (publisher.job,),
            ).fetchone()
            if (row[1], row[2]) != (publisher.epoch, publisher.instance):
                raise JobStoreError("PUBLISHER_STALE")
            if row[0] != "ACTIVE":
                raise JobStoreError("JOB_STATE")
            _current(c, self)

        read(workspace, live)
        schema = None
        if acceptance.extent == 0 and acceptance.scope == "complete_capture":
            schema = _rebatch(self, 0, 0)[3]
        snapshot = self.snapshot
        return SavedScopeEnd(
            EXHAUSTED,
            acceptance.consumer,
            acceptance.generation,
            acceptance.checkpoint,
            acceptance.scope,
            acceptance.extent,
            self._position,
            (self.start, self._position),
            schema,
            snapshot.observed_end,
            snapshot.holes,
            snapshot.layers,
        )

    def close(self) -> None:
        """Release owned local resources; never an acknowledgement or completion."""
        if self._closed or self._pid != os.getpid():
            return
        self._closed = True
        self._held = self._pending = None
        if self._reader is not None:
            self._reader.close()


@dataclass(frozen=True, slots=True)
class ConsumerState:
    """A read-only observation; it never reopens reading after cancel or expiry."""

    consumer: str
    job: str
    generation: str
    checkpoint: str
    binding: str
    retention: str
    released: bool
    scope: str
    extent: int
    purpose: str
    not_after: int | None
    position: int
    acknowledged: tuple[tuple[int, int], ...]
    sessions: tuple[tuple[str, int, int], ...]
    issued: tuple[tuple[str, str, int, int, bool], ...]


def consumer_state(workspace: Workspace, consumer: str) -> ConsumerState:
    """Registered facts, derived position and complete session/issuance history."""
    _replaying(workspace)
    if not valid_identity(consumer, "csm"):
        raise JobStoreError("CONSUMER_UNKNOWN")

    def body(c):
        row = c.execute(
            "SELECT job, generation, checkpoint, binding, retention,"
            " (SELECT count(*) FROM retention_release x"
            " WHERE x.retention = consumer.retention),"
            " scope, extent, purpose, not_after FROM consumer WHERE identity = ?",
            (consumer,),
        ).fetchone()
        if row is None:
            raise JobStoreError("CONSUMER_UNKNOWN")
        return (
            row,
            c.execute(
                "SELECT start, stop FROM acknowledgement WHERE consumer = ?"
                " ORDER BY start",
                (consumer,),
            ).fetchall(),
            c.execute(
                "SELECT identity, ordinal, position FROM replay_session"
                " WHERE consumer = ? ORDER BY ordinal",
                (consumer,),
            ).fetchall(),
            c.execute(
                "SELECT i.identity, i.session, i.start, i.stop,"
                " EXISTS (SELECT 1 FROM acknowledgement a WHERE a.issuance = i.identity)"
                " FROM issuance i JOIN replay_session s ON s.identity = i.session"
                " WHERE i.consumer = ? ORDER BY s.ordinal, i.ordinal",
                (consumer,),
            ).fetchall(),
        )

    row, acknowledged, sessions, issued = read(workspace, body)
    position = _progress(acknowledged)
    return ConsumerState(
        consumer,
        row[0],
        row[1],
        row[2],
        row[3],
        row[4],
        bool(row[5]),
        row[6],
        row[7],
        row[8],
        row[9],
        position,
        tuple(acknowledged),
        tuple(sessions),
        tuple((i[0], i[1], i[2], i[3], bool(i[4])) for i in issued),
    )
