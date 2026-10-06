"""S17 bounded same-host job runtime over an explicit v7 job workspace.

One caller-created `Runtime` per workspace and process owns aggregate admission:
a nonblocking lock on the stable `locks/runtime.lock` plus a new durable
`runtime_owner` epoch. It is not a daemon, scheduler service, credential queue
or arbitrary-code job service; product units and coding writers are unrelated.

A unit is one typed use of the original owners (CAPTURE, RELAY, RECOVER, REPLAY,
PUBLISH). Its resource vector is reserved all-or-none in memory under the
coordinator mutex and durably as an `admission` row in one BEGIN IMMEDIATE
transaction that checks committed accounting plus every outstanding reservation;
it is settled exactly once. Each admitted unit runs in its own bounded worker
thread that opens its own workspace handle, claims its own per-job publisher and
builds its own native owner from explicit typed host inputs; no connection,
publisher, owner or acceptance is pickled or crosses a process boundary.

The next checked batch is pulled only after the previous one is durable (and,
for RELAY, delivered and confirmed): a blocked sink or consumer stops the source
at a fixed high-water mark while other units continue. Control is a separate
lane: `cancel` is accepted in O(1), the owner's own native cancel is signalled at
once, and the unit's worker (the Publisher/SQLite owner) records the durable job
cancellation. Requested, sent, observed and durable outcomes stay distinct; a
flag is never a durable CANCELLED. Scheduler success, reclaimed credit and
settlement never rewrite source, transaction, delivery, sink or publication facts.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import fcntl
import os
import stat
import threading
import time
from typing import Any
import weakref

from pietto._project import project_job_chunks as chunks
from pietto._project.project_job_store import (
    CONTROL_OPERATIONS,
    LIMITS,
    _json,
    charge,
    new_operation,
)
from pietto._project.project_job_workspace import (
    CONTROL_RESERVE,
    JobStoreError,
    Workspace,
    new_identity,
    open_workspace,
    read,
    supports,
    valid_identity,
    write,
)

__all__: tuple[str, ...] = ()

MODES = ("CAPTURE", "RELAY", "RECOVER", "REPLAY", "PUBLISH")
LOCK = "runtime.lock"
MIB = 1024 * 1024
MAX_UNIT_SECONDS = 86400
MAX_EVENTS = 64
# Bounded re-check interval of a parked worker or the control thread; waking is
# by notification, this only bounds a missed-notification delay.
PARK_SECONDS = 0.05
# Conservative per-owner memory: one checked native batch and its Arrow form, one
# IPC frame and one chunk image; REPLAY holds up to three decoded members.
FRAME = chunks.MAX_FILE_BYTES
_ADMITTED: weakref.WeakSet = weakref.WeakSet()
_OWNERS: weakref.WeakSet = weakref.WeakSet()


@dataclass(frozen=True, slots=True)
class Policy:
    """The aggregate envelope of one runtime incarnation (frozen, recorded)."""

    connections: int = 3
    workers: int = 3
    queue: int = 8
    memory: int = 512 * MIB
    durable: int = 64 * MIB
    operations: int = 65536
    overtakes: int = 4


@dataclass(frozen=True, slots=True)
class Vector:
    """One unit's reserved resources; memory and durable bytes are conservative."""

    connections: int
    workers: int
    memory: int
    durable: int
    operations: int


_FIELDS = ("connections", "workers", "memory", "durable", "operations")


def _total(vectors) -> Vector:
    return Vector(*(sum(getattr(v, f) for v in vectors) for f in _FIELDS))


def _fits(used: Vector, add: Vector, policy: Policy) -> str | None:
    """The first exceeded aggregate bound (the limiting resource), if any."""
    for name in _FIELDS:
        if getattr(used, name) + getattr(add, name) > getattr(policy, name):
            return name
    return None


def _policy_text(policy, workspace) -> str:
    if type(policy) is not Policy or any(
        type(getattr(policy, f)) is not int for f in Policy.__slots__
    ):
        raise JobStoreError("RUNTIME_POLICY")
    if not (
        1 <= policy.connections <= 8
        and 1 <= policy.workers <= 8
        and 0 <= policy.queue <= 64
        and 64 * MIB <= policy.memory <= 4096 * MIB
        and 0 <= policy.durable <= workspace.budget - CONTROL_RESERVE
        and 0 <= policy.operations <= LIMITS["operation"] - CONTROL_OPERATIONS
        and 0 <= policy.overtakes <= 16
    ):
        raise JobStoreError("RUNTIME_POLICY")
    return _json({f: getattr(policy, f) for f in Policy.__slots__})


class RuntimeOwner:
    """Process-local proof that this process holds a workspace's runtime lock as
    one exact incarnation; never copied, serialized or passed to a process."""

    __slots__ = (
        "root",
        "workspace",
        "epoch",
        "instance",
        "policy",
        "_fd",
        "_pid",
        "__weakref__",
    )

    def __init__(self, root, workspace, epoch, instance, policy, fd):
        self.root, self.workspace = root, workspace
        self.epoch, self.instance, self.policy = epoch, instance, policy
        self._fd, self._pid = fd, os.getpid()

    def __repr__(self) -> str:
        return f"RuntimeOwner(epoch={self.epoch!r})"

    def __reduce_ex__(self, protocol):
        raise JobStoreError("RUNTIME_OWNER_COPY")

    def release(self) -> None:
        if self._fd >= 0 and self._pid == os.getpid():
            fd, self._fd = self._fd, -1
            os.close(fd)


def owning(owner, workspace: Workspace) -> RuntimeOwner:
    if (
        type(owner) is not RuntimeOwner
        or owner not in _OWNERS
        or owner._pid != os.getpid()
        or owner._fd < 0
        or owner.workspace != workspace.identity
    ):
        raise JobStoreError("RUNTIME_OWNER")
    return owner


def fence(c, owner: RuntimeOwner) -> None:
    """The current incarnation is still the latest one (in the caller's txn)."""
    if c.execute(
        "SELECT epoch, instance FROM runtime_owner ORDER BY epoch DESC LIMIT 1"
    ).fetchone() != (owner.epoch, owner.instance):
        raise JobStoreError("RUNTIME_STALE")


def claim_runtime(workspace: Workspace, policy: Policy) -> RuntimeOwner:
    """Nonblocking same-host ownership, then a durable higher epoch; no steal."""
    if not supports(workspace, "bounded-job-runtime"):
        raise JobStoreError("WORKSPACE_RUNTIME_FORMAT")
    text = _policy_text(policy, workspace)
    locks = workspace.locks_fd()
    fd = os.open(
        LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=locks
    )
    try:
        state = os.fstat(fd)
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_uid != os.geteuid()
            or state.st_mode & 0o077
            or state.st_nlink != 1
        ):
            raise JobStoreError("RUNTIME_LOCK_OBJECT")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise JobStoreError("RUNTIME_BUSY") from None
        current = os.stat(LOCK, dir_fd=locks, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (state.st_dev, state.st_ino):
            raise JobStoreError("RUNTIME_LOCK_OBJECT")
        instance = new_identity("run")

        def body(c):
            epoch = (
                c.execute(
                    "SELECT coalesce(max(epoch), 0) FROM runtime_owner"
                ).fetchone()[0]
                + 1
            )
            c.execute(
                "INSERT INTO runtime_owner(epoch, instance, policy) VALUES (?, ?, ?)",
                (epoch, instance, text),
            )
            return epoch

        epoch = write(workspace, body)
        owner = RuntimeOwner(
            workspace.root, workspace.identity, epoch, instance, policy, fd
        )
        _OWNERS.add(owner)
        fd = -1
        return owner
    finally:
        if fd >= 0:
            os.close(fd)


@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class Admission:
    """A process-local admitted unit allowance of one runtime incarnation; the
    only authority a v7 capture has to claim chunk files. Never copied."""

    identity: str
    workspace: str
    job: str
    runtime: int
    mode: str
    durable: int
    _pid: int = field(repr=False)

    def __reduce_ex__(self, protocol):
        raise JobStoreError("RUNTIME_ADMISSION_COPY")


def admitted(admission, workspace: Workspace, job: str) -> Admission:
    """A live admission of this process, workspace and job (else refusal)."""
    if (
        type(admission) is not Admission
        or admission not in _ADMITTED
        or admission._pid != os.getpid()
        or (admission.workspace, admission.job) != (workspace.identity, job)
    ):
        raise JobStoreError("RUNTIME_ADMISSION_REQUIRED")
    return admission


def _insert_admission(c, workspace, owner, identity, job, mode, vector) -> None:
    """Durable all-or-none reservation against committed accounting and every
    outstanding reservation, under the writer lock."""
    fence(c, owner)
    if not c.execute("SELECT 1 FROM job WHERE identity = ?", (job,)).fetchone():
        raise JobStoreError("JOB_UNKNOWN")
    if c.execute("SELECT count(*) FROM admission").fetchone()[0] >= LIMITS["admission"]:
        raise JobStoreError("STORE_LIMIT")
    charge(c, workspace, vector.durable)
    reserved = c.execute(
        "SELECT coalesce(sum(a.operations), 0) FROM admission a WHERE NOT EXISTS"
        " (SELECT 1 FROM admission_settlement s WHERE s.admission = a.identity)"
    ).fetchone()[0]
    if (
        c.execute("SELECT count(*) FROM operation").fetchone()[0]
        + reserved
        + vector.operations
        + CONTROL_OPERATIONS
        > LIMITS["operation"]
    ):
        raise JobStoreError("STORE_LIMIT")
    c.execute(
        "INSERT INTO admission(identity, job, runtime, mode, vector, durable,"
        " operations) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            identity,
            job,
            owner.epoch,
            mode,
            _json({f: getattr(vector, f) for f in _FIELDS}),
            vector.durable,
            vector.operations,
        ),
    )


@dataclass(frozen=True, slots=True)
class AdmissionFact:
    """The durable admission and its settlement as recorded (query result)."""

    identity: str
    job: str
    runtime: int
    mode: str
    vector: str
    durable: int
    operations: int
    claimed: int
    settlement: tuple[int, str, int] | None


def admission_fact(workspace: Workspace, identity: str) -> AdmissionFact | None:
    """None only when the admission is known absent (never on IO failure)."""
    if not valid_identity(identity, "adm"):
        raise JobStoreError("RUNTIME_ADMISSION_UNKNOWN")

    def body(c):
        row = c.execute(
            "SELECT identity, job, runtime, mode, vector, durable, operations,"
            " (SELECT coalesce(sum(bytes), 0) FROM chunk_claim k"
            " WHERE k.admission = a.identity) FROM admission a WHERE identity = ?",
            (identity,),
        ).fetchone()
        settled = c.execute(
            "SELECT runtime, kind, claimed FROM admission_settlement WHERE admission = ?",
            (identity,),
        ).fetchone()
        return row, settled

    row, settled = read(workspace, body)
    if row is None:
        return None
    return AdmissionFact(
        row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], settled
    )


def settle(workspace: Workspace, owner: RuntimeOwner, identity: str) -> AdmissionFact:
    """Exactly once per admission: RELEASED by its own incarnation, RECONCILED by
    a later one (after real ownership exclusion). A repeat returns the original."""
    owner = owning(owner, workspace)
    if not valid_identity(identity, "adm"):
        raise JobStoreError("RUNTIME_ADMISSION_UNKNOWN")

    def body(c):
        fence(c, owner)
        row = c.execute(
            "SELECT runtime, (SELECT coalesce(sum(bytes), 0) FROM chunk_claim k"
            " WHERE k.admission = a.identity) FROM admission a WHERE identity = ?",
            (identity,),
        ).fetchone()
        if row is None:
            raise JobStoreError("RUNTIME_ADMISSION_UNKNOWN")
        if c.execute(
            "SELECT 1 FROM admission_settlement WHERE admission = ?", (identity,)
        ).fetchone():
            return
        kind = "RELEASED" if row[0] == owner.epoch else "RECONCILED"
        c.execute(
            "INSERT INTO admission_settlement(admission, runtime, kind, claimed)"
            " VALUES (?, ?, ?, ?)",
            (identity, owner.epoch, kind, row[1]),
        )

    write(workspace, body)
    fact = admission_fact(workspace, identity)
    assert fact is not None
    return fact


def reconcile(workspace: Workspace, owner: RuntimeOwner, *, limit: int = 256) -> tuple:
    """Settle (RECONCILED) every open admission of an EARLIER incarnation. The
    runtime lock proves that incarnation's process holds no worker; its claims
    stay charged until collected and its open attempts stay open until a
    publisher interrupts them. Nothing is restarted."""
    owner = owning(owner, workspace)
    if type(limit) is not int or not 1 <= limit <= 4096:
        raise JobStoreError("RUNTIME_BOUND")

    def body(c):
        fence(c, owner)
        rows = c.execute(
            "SELECT a.identity, (SELECT coalesce(sum(bytes), 0) FROM chunk_claim k"
            " WHERE k.admission = a.identity) FROM admission a WHERE a.runtime < ?"
            " AND NOT EXISTS (SELECT 1 FROM admission_settlement s"
            " WHERE s.admission = a.identity) ORDER BY a.identity LIMIT ?",
            (owner.epoch, limit),
        ).fetchall()
        c.executemany(
            "INSERT INTO admission_settlement(admission, runtime, kind, claimed)"
            " VALUES (?, ?, 'RECONCILED', ?)",
            [(r[0], owner.epoch, r[1]) for r in rows],
        )
        return tuple(rows)

    return write(workspace, body)


# --- units -------------------------------------------------------------------


@dataclass(frozen=True, slots=True, eq=False)
class NativeSource:
    """Explicit in-process host inputs of one native attempt; never stored or
    pickled. The premise is rebuilt over the worker's own fresh binding."""

    route: str
    access: Any = field(repr=False)
    schemas: tuple[str, ...]
    limits: Any
    isolation: str = "stable"

    def __reduce_ex__(self, protocol):
        raise JobStoreError("RUNTIME_SOURCE_COPY")


@dataclass(frozen=True, slots=True, eq=False)
class SinkTarget:
    """The caller's independent expectations of one reference sink incarnation."""

    root: str
    identity: str
    namespace: str
    epoch: int
    retention: str
    busy_seconds: float = 5.0


@dataclass(frozen=True, slots=True, eq=False)
class Unit:
    """One typed unit request. `trust` is the caller's fresh (pin, producer,
    compatibility); `values` the caller's typed statement of the binding."""

    mode: str
    root: str = field(repr=False)
    workspace: str
    job: str
    generation: str
    trust: tuple = field(repr=False)
    seconds: int = 3600
    values: tuple = field(default=(), repr=False)
    source: NativeSource | None = field(default=None, repr=False)
    durable: int = 0
    operations: int = 4096
    extraction: bool = False
    interrupt: bool = False
    sink: SinkTarget | None = field(default=None, repr=False)
    rows: int = 4096
    checkpoint: str | None = None
    closing: str | None = None
    consumer: str | None = None
    register: bool = True
    scope: str = "complete_capture"
    extent: int = 0
    purpose: str = "s17-runtime"
    batch_rows: int = 4096
    # A live in-process template (the live entry); None loads the stored bundle
    # with the fresh `trust` inputs. Either way the stored binding must match.
    template: Any = field(default=None, repr=False)

    def __reduce_ex__(self, protocol):
        raise JobStoreError("RUNTIME_UNIT_COPY")


def vector(unit: Unit) -> Vector:
    """The unit's bounded resource vector (a conservative reservation)."""
    if unit.mode not in MODES:
        raise JobStoreError("RUNTIME_UNIT")
    if type(unit.operations) is not int or not 0 < unit.operations <= 65536:
        raise JobStoreError("RUNTIME_UNIT_BOUND")
    if unit.mode in ("CAPTURE", "RELAY", "RECOVER"):
        source = unit.source
        if type(source) is not NativeSource:
            raise JobStoreError("RUNTIME_UNIT")
        batch = source.limits.batch_bytes
        if type(batch) is not int or batch <= 0:
            raise JobStoreError("RUNTIME_UNIT_BOUND")
        if type(unit.durable) is not int or unit.durable < 0:
            raise JobStoreError("RUNTIME_UNIT_BOUND")
        held = 2 if unit.mode == "CAPTURE" else 3
        return Vector(1, 1, 2 * batch + held * FRAME, unit.durable, unit.operations)
    if unit.durable != 0:
        raise JobStoreError("RUNTIME_UNIT_BOUND")
    if unit.mode == "REPLAY":
        return Vector(0, 1, 3 * FRAME, 0, unit.operations)
    return Vector(0, 1, 2 * FRAME, 0, unit.operations)


@dataclass(frozen=True, slots=True)
class UnitState:
    """A bounded read-only observation; never authority, never a durable fact
    by itself (durable facts are the store's own queries)."""

    handle: str
    mode: str
    job: str
    generation: str
    state: str
    activity: str | None
    limiting: str | None
    terminal: str | None
    failure: str | None
    cancel: tuple
    durable_cancel: str
    settlement: str
    counters: tuple[tuple[str, int], ...]
    events: tuple[tuple[int, str], ...]


class _Stop(Exception):
    """Internal: a requested cancel/stop observed at a worker checkpoint."""


class _Record:
    """Coordinator bookkeeping of one unit; every field is guarded by the mutex."""

    __slots__ = (
        "unit",
        "handle",
        "vector",
        "state",
        "activity",
        "limiting",
        "terminal",
        "failure",
        "cancel_requested",
        "stop",
        "signal",
        "durable_cancel",
        "settlement",
        "owner",
        "overtaken",
        "deadline",
        "thread",
        "released",
        "resume",
        "outbox",
        "acks",
        "counters",
        "events",
    )

    def __init__(self, unit, handle, vector, deadline):
        self.unit, self.handle, self.vector = unit, handle, vector
        self.state = "QUEUED"
        self.activity: str | None = None
        self.limiting: str | None = None
        self.terminal: str | None = None
        self.failure: str | None = None
        self.cancel_requested = self.stop = False
        self.signal = None
        self.durable_cancel = "NOT_REQUESTED"
        self.settlement = "NONE"
        self.owner: Any = None
        self.overtaken = 0
        self.deadline = deadline
        self.thread: threading.Thread | None = None
        self.released = False
        self.resume = 0
        self.outbox: Any = None
        self.acks: deque = deque(maxlen=1)
        self.counters: dict[str, int] = {}
        self.events: deque = deque(maxlen=MAX_EVENTS)


def open_runtime(
    root: str,
    *,
    expected_identity: str,
    policy: Policy = Policy(),
    busy_seconds: float = 5.0,
) -> Runtime:
    """Open the one coordinating incarnation of a v7 workspace in this process."""
    workspace = open_workspace(root, expected_identity=expected_identity)
    try:
        owner = claim_runtime(workspace, policy)
    finally:
        workspace.close()
    try:
        return Runtime(root, expected_identity, owner, busy_seconds)
    except BaseException:
        owner.release()
        raise


class Runtime:
    """One caller-created coordinator. Every public method is thread-safe; the
    mutex is a leaf held only for bookkeeping (never across IO or native calls)."""

    def __init__(self, root, identity, owner, busy_seconds):
        self.root, self.identity, self.owner = root, identity, owner
        self.policy: Policy = owner.policy
        self._busy = busy_seconds
        self._mutex = threading.Lock()
        self._cond = threading.Condition(self._mutex)
        self._queue: deque[_Record] = deque()
        self._records: dict[str, _Record] = {}
        self._used = Vector(0, 0, 0, 0, 0)
        self._closing = False
        self._capacity = True
        self._control_failure: str | None = None
        self._pid = os.getpid()
        self._control = threading.Thread(
            target=self._control_loop, name="pietto-runtime-control", daemon=True
        )
        self._control.start()

    def __repr__(self) -> str:
        return f"Runtime(epoch={self.owner.epoch!r})"

    def __reduce_ex__(self, protocol):
        raise JobStoreError("RUNTIME_COPY")

    # --- public API ---------------------------------------------------------

    def submit(self, unit: Unit) -> str:
        """Queue one unit; refused at once when its vector can never fit or the
        finite queue is full. Returns the admission identity (the query handle)."""
        if os.getpid() != self._pid:
            raise JobStoreError("RUNTIME_FOREIGN_PROCESS")
        if type(unit) is not Unit or (unit.root, unit.workspace) != (
            self.root,
            self.identity,
        ):
            raise JobStoreError("RUNTIME_UNIT")
        if not valid_identity(unit.job, "job") or not valid_identity(
            unit.generation, "gen"
        ):
            raise JobStoreError("RUNTIME_UNIT")
        if type(unit.seconds) is not int or not 1 <= unit.seconds <= MAX_UNIT_SECONDS:
            raise JobStoreError("RUNTIME_UNIT_BOUND")
        wanted = vector(unit)
        limiting = _fits(Vector(0, 0, 0, 0, 0), wanted, self.policy)
        if limiting is not None:
            raise JobStoreError("RUNTIME_UNIT_BOUND")
        handle = new_identity("adm")
        record = _Record(unit, handle, wanted, time.monotonic() + unit.seconds)
        with self._cond:
            if self._closing:
                raise JobStoreError("RUNTIME_CLOSED")
            if len(self._queue) >= self.policy.queue:
                raise JobStoreError("RUNTIME_QUEUE_FULL")
            self._records[handle] = record
            self._queue.append(record)
            self._capacity = True
            self._event(record, "QUEUED")
            self._cond.notify_all()
        return handle

    def query(self, handle: str) -> UnitState:
        with self._cond:
            return self._state(self._record(handle))

    def wait(self, handle: str, timeout: float) -> UnitState:
        """Wait (bounded) for the unit's terminal; returns the current state."""
        deadline = time.monotonic() + timeout
        with self._cond:
            record = self._record(handle)
            while record.terminal is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._cond.wait(min(remaining, 1.0))
            return self._state(record)

    def wait_activity(self, handle: str, activity: str, timeout: float) -> UnitState:
        """Wait (bounded) until the unit reports `activity` or ends."""
        deadline = time.monotonic() + timeout
        with self._cond:
            record = self._record(handle)
            while record.activity != activity and record.terminal is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._cond.wait(min(remaining, 1.0))
            return self._state(record)

    def cancel(self, handle: str) -> dict:
        """Control lane: O(1) acceptance (coalesced per unit), the owner's native
        cancel at once, the worker records the durable job cancellation."""
        with self._cond:
            record = self._record(handle)
            if record.terminal is not None:
                return {"requested": record.cancel_requested, "late": True}
            first = not record.cancel_requested
            record.cancel_requested = True
            self._event(record, "CANCEL_REQUESTED")
            owner = record.owner if first else None
            self._cond.notify_all()
        signal = None
        if owner is not None:
            signal = owner.cancel()
            with self._cond:
                record.signal = signal
                self._event(record, "CANCEL_SIGNALLED")
        return {"requested": True, "late": False, "signal": signal}

    def resume(self, handle: str) -> None:
        """Downstream relief for a RELAY unit waiting on its sink."""
        with self._cond:
            self._record(handle).resume += 1
            self._cond.notify_all()

    def take(self, handle: str, timeout: float):
        """The REPLAY unit's one pending Delivery (not an acknowledgement)."""
        deadline = time.monotonic() + timeout
        with self._cond:
            record = self._record(handle)
            while record.outbox is None and record.terminal is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._cond.wait(min(remaining, 1.0))
            return record.outbox

    def ack(self, handle: str, delivery) -> None:
        """The consumer's explicit acknowledgement request of that exact delivery;
        the worker performs the original S13 acknowledge."""
        with self._cond:
            record = self._record(handle)
            if record.outbox is None or record.outbox is not delivery:
                raise JobStoreError("DELIVERY_FOREIGN")
            record.acks.append(delivery)
            self._cond.notify_all()

    def grant(self, job: str, unit: Unit) -> Admission:
        """Admit a unit the caller runs itself (same accounting; no worker)."""
        wanted = vector(unit)
        with self._cond:
            limiting = _fits(self._used, wanted, self.policy)
            if self._closing:
                raise JobStoreError("RUNTIME_CLOSED")
            if limiting is not None:
                raise JobStoreError("RUNTIME_CAPACITY:" + limiting)
            self._used = _total((self._used, wanted))
        identity = new_identity("adm")
        try:
            workspace = open_workspace(self.root, expected_identity=self.identity)
            try:
                write(
                    workspace,
                    lambda c: _insert_admission(
                        c, workspace, self.owner, identity, job, unit.mode, wanted
                    ),
                )
            finally:
                workspace.close()
        except BaseException:
            with self._cond:
                self._used = Vector(
                    *(getattr(self._used, f) - getattr(wanted, f) for f in _FIELDS)
                )
            raise
        admission = Admission(
            identity,
            self.identity,
            job,
            self.owner.epoch,
            unit.mode,
            wanted.durable,
            os.getpid(),
        )
        _ADMITTED.add(admission)
        with self._cond:
            record = _Record(unit, identity, wanted, float("inf"))
            record.state, record.released = "GRANTED", False
            self._records[identity] = record
        return admission

    def release(self, admission: Admission) -> AdmissionFact:
        """Settle a granted admission (once) and return its in-memory capacity."""
        workspace = open_workspace(self.root, expected_identity=self.identity)
        try:
            fact = settle(workspace, self.owner, admission.identity)
        finally:
            workspace.close()
        _ADMITTED.discard(admission)
        with self._cond:
            record = self._records[admission.identity]
            self._release(record)
            record.state, record.terminal, record.settlement = (
                "TERMINAL",
                "RELEASED",
                "RELEASED",
            )
        return fact

    def reconcile(self) -> tuple:
        workspace = open_workspace(self.root, expected_identity=self.identity)
        try:
            rows = reconcile(workspace, self.owner)
        finally:
            workspace.close()
        with self._cond:
            self._capacity = True
            self._cond.notify_all()
        return rows

    def collect(self, **quanta):
        """One bounded collection pass in the calling thread (its own handle);
        it yields when control requests are pending."""
        from pietto._project.project_job_collection import collect

        workspace = open_workspace(self.root, expected_identity=self.identity)
        try:
            report = collect(workspace, self.owner, yielding=self._pending, **quanta)
        finally:
            workspace.close()
        with self._cond:
            self._capacity = True
            self._cond.notify_all()
        return report

    def close(self, timeout: float = 60.0) -> dict:
        """Finite shutdown: no new admissions, queued units stopped, running
        units stopped through their own owners (not a durable job cancel),
        owned threads joined. An unjoined worker keeps the runtime lock."""
        owners = []
        with self._cond:
            self._closing = True
            while self._queue:
                record = self._queue.popleft()
                self._finish(record, "STOPPED_CLOSE", None)
            for record in self._records.values():
                if record.terminal is None and record.state != "GRANTED":
                    record.stop = True
                    if record.owner is not None:
                        owners.append(record.owner)
            self._cond.notify_all()
        for owner in owners:
            try:
                owner.cancel()
            except BaseException:
                pass
        deadline = time.monotonic() + timeout
        # The control thread exits only once every unit is terminal; workers it
        # started meanwhile are then in the list read below.
        self._control.join(max(0.0, deadline - time.monotonic()))
        with self._cond:
            threads = [r.thread for r in self._records.values() if r.thread is not None]
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))
        unjoined = [t.name for t in threads + [self._control] if t.is_alive()]
        if not unjoined:
            self.owner.release()
        with self._cond:
            states = {h: self._state(r) for h, r in self._records.items()}
            failure = self._control_failure
        return {"unjoined": unjoined, "units": states, "control_failure": failure}

    # --- internals ------------------------------------------------------------

    def _record(self, handle) -> _Record:
        record = self._records.get(handle)
        if record is None:
            raise JobStoreError("RUNTIME_UNIT_UNKNOWN")
        return record

    def _event(self, record, kind) -> None:
        record.events.append((time.monotonic_ns(), kind))

    def _count(self, record, name, value=1, *, peak=False) -> None:
        with self._cond:
            current = record.counters.get(name, 0)
            record.counters[name] = max(current, value) if peak else current + value

    def _state(self, record) -> UnitState:
        unit = record.unit
        return UnitState(
            record.handle,
            unit.mode,
            unit.job,
            unit.generation,
            record.state,
            record.activity,
            record.limiting,
            record.terminal,
            record.failure,
            (record.cancel_requested, record.signal),
            record.durable_cancel,
            record.settlement,
            tuple(sorted(record.counters.items())),
            tuple(record.events),
        )

    def _pending(self) -> bool:
        """A control request not yet observed by its worker (GC yields to it)."""
        with self._cond:
            return any(
                r.cancel_requested
                and r.terminal is None
                and r.durable_cancel == "NOT_REQUESTED"
                for r in self._records.values()
            )

    def _release(self, record) -> None:
        """Return reusable in-memory capacity exactly once (caller holds mutex)."""
        if not record.released:
            record.released = True
            self._used = Vector(
                *(getattr(self._used, f) - getattr(record.vector, f) for f in _FIELDS)
            )
            if any(getattr(self._used, f) < 0 for f in _FIELDS):
                raise JobStoreError("RUNTIME_ACCOUNTING")
            self._capacity = True

    def _finish(self, record, terminal, failure) -> None:
        """Caller holds the mutex."""
        record.state, record.activity = "TERMINAL", None
        record.terminal, record.failure = terminal, failure
        self._event(record, "TERMINAL:" + terminal)
        self._cond.notify_all()

    def _choose(self) -> list:
        """FIFO, work-conserving, with bounded overtaking: a later unit that fits
        may pass the oldest blocked unit at most `policy.overtakes` times; then
        nothing passes it until it fits (caller holds the mutex)."""
        chosen = []
        blocked = None
        for record in list(self._queue):
            limiting = _fits(self._used, record.vector, self.policy)
            if limiting is None and (
                blocked is None or blocked.overtaken < self.policy.overtakes
            ):
                self._queue.remove(record)
                self._used = _total((self._used, record.vector))
                record.state, record.limiting = "ADMITTING", None
                if blocked is not None:
                    blocked.overtaken += 1
                    self._event(blocked, "OVERTAKEN")
                chosen.append(record)
            else:
                record.state = "WAITING_FOR_ADMISSION"
                record.limiting = limiting or "OVERTAKING_BOUND"
                if blocked is None:
                    blocked = record
        return chosen

    def _control_loop(self) -> None:
        workspace = None
        try:
            workspace = open_workspace(self.root, expected_identity=self.identity)
            while True:
                with self._cond:
                    if self._closing and all(
                        r.terminal is not None or r.state == "GRANTED"
                        for r in self._records.values()
                    ):
                        return
                    self._cond.wait(PARK_SECONDS)
                    now = time.monotonic()
                    queued, signals = [], []
                    for record in list(self._queue):
                        if record.cancel_requested or now >= record.deadline:
                            self._queue.remove(record)
                            queued.append(record)
                            self._capacity = True
                    for record in self._records.values():
                        if (
                            record.terminal is None
                            and record.thread is not None
                            and now >= record.deadline
                            and not record.stop
                        ):
                            record.stop = True
                            self._event(record, "DEADLINE")
                            if record.owner is not None:
                                signals.append(record.owner)
                            self._cond.notify_all()
                    chosen = []
                    if self._capacity and not self._closing:
                        self._capacity = False
                        chosen = self._choose()
                for owner in signals:
                    owner.cancel()
                for record in queued:
                    workspace = self._cancel_queued(workspace, record)
                for record in chosen:
                    workspace = self._admit(workspace, record)
        except BaseException as error:
            with self._cond:
                self._control_failure = type(error).__name__ + ":" + str(error)
                self._cond.notify_all()
        finally:
            if workspace is not None:
                try:
                    workspace.close()
                except JobStoreError:
                    pass

    def _fresh(self, workspace):
        """A retired control handle is replaced; never reused after uncertainty."""
        if workspace is not None and not workspace._retired:
            return workspace
        if workspace is not None:
            try:
                workspace.close()
            except JobStoreError:
                pass
        return open_workspace(self.root, expected_identity=self.identity)

    def _cancel_queued(self, workspace, record):
        """A never-admitted unit: no worker exists; with a cancel request the
        control lane records the durable job cancellation itself (control
        operations only), else the unit simply stops (deadline)."""
        from pietto._project.project_job_store import cancel_job, claim_publisher

        outcome = "NOT_REQUESTED"
        if record.cancel_requested:
            workspace = self._fresh(workspace)
            try:
                publisher = claim_publisher(
                    workspace, record.unit.job, operation=new_operation()
                )
                try:
                    cancel_job(publisher, operation=new_operation())
                    outcome = "COMMITTED"
                finally:
                    publisher.close()
            except JobStoreError as error:
                outcome = (
                    "UNKNOWN"
                    if str(error) == "STORE_COMMIT_UNKNOWN"
                    else "REFUSED:" + str(error)
                )
        with self._cond:
            record.durable_cancel = outcome
            self._finish(
                record,
                "CANCELLED_QUEUED" if record.cancel_requested else "STOPPED_DEADLINE",
                None,
            )
        return workspace

    def _admit(self, workspace, record):
        """Durable admission of an in-memory reservation (control thread)."""
        unit = record.unit
        try:
            workspace = self._fresh(workspace)
            write(
                workspace,
                lambda c: _insert_admission(
                    c,
                    workspace,
                    self.owner,
                    record.handle,
                    unit.job,
                    unit.mode,
                    record.vector,
                ),
            )
        except JobStoreError as error:
            code = str(error)
            if code == "STORE_COMMIT_UNKNOWN":
                with self._cond:
                    record.state = "ADMISSION_UNKNOWN"
                    self._event(record, "ADMISSION_UNKNOWN")
                # No work after an uncertain admission: a fresh query decides.
                workspace = self._fresh(workspace)
                if admission_fact(workspace, record.handle) is None:
                    with self._cond:
                        self._release(record)
                        self._finish(record, "REFUSED", "ADMISSION_ABSENT")
                    return workspace
            else:
                with self._cond:
                    self._release(record)
                    if (
                        code in ("WORKSPACE_BUDGET", "STORE_LIMIT")
                        and not self._closing
                    ):
                        # Storage is legitimately occupied: wait, keep order.
                        record.state, record.limiting = "WAITING_FOR_ADMISSION", code
                        self._queue.appendleft(record)
                        self._capacity = False
                    else:
                        self._finish(record, "REFUSED", code)
                return workspace
        with self._cond:
            closing = self._closing
        if closing:
            # Admitted while the runtime closes: no worker starts; the durable
            # allowance is settled at once (nothing was claimed).
            fact = settle(workspace, self.owner, record.handle)
            with self._cond:
                record.settlement = (
                    "UNKNOWN" if fact.settlement is None else fact.settlement[1]
                )
                self._release(record)
                self._finish(record, "STOPPED_CLOSE", None)
            return workspace
        admission = Admission(
            record.handle,
            self.identity,
            unit.job,
            self.owner.epoch,
            unit.mode,
            record.vector.durable,
            os.getpid(),
        )
        _ADMITTED.add(admission)
        with self._cond:
            record.state, record.settlement = "RUNNING", "OPEN"
            self._event(record, "ADMITTED")
            record.thread = threading.Thread(
                target=self._work,
                args=(record, admission),
                name="pietto-runtime-" + unit.mode.lower() + "-" + record.handle[4:12],
                daemon=True,
            )
            record.thread.start()
        return workspace

    # --- worker side ------------------------------------------------------------

    def _activity(self, record, activity) -> None:
        with self._cond:
            record.activity = activity
            self._event(record, activity)
            self._cond.notify_all()

    def _check(self, record) -> None:
        with self._cond:
            if record.cancel_requested or record.stop:
                raise _Stop

    def _park(self, record, ready) -> None:
        """Wait for `ready()` (evaluated under the mutex), a cancel or a stop."""
        with self._cond:
            while not ready():
                if record.cancel_requested or record.stop:
                    raise _Stop
                self._cond.wait(PARK_SECONDS)

    def _bind_owner(self, record, owner) -> None:
        """Publish the native owner to the control lane; a cancel that arrived
        before it existed is delivered now (no lost signal)."""
        with self._cond:
            record.owner = owner
            late = record.cancel_requested or record.stop
        if late:
            signal = owner.cancel()
            with self._cond:
                record.signal = signal
                self._event(record, "CANCEL_SIGNALLED")

    def _work(self, record, admission) -> None:
        from pietto._project.project_job_store import claim_publisher

        unit = record.unit
        workspace = publisher = None
        terminal, failure = "COMPLETED", None
        context: dict = {"closers": [], "unit": unit}
        try:
            workspace = open_workspace(
                self.root, expected_identity=self.identity, busy_seconds=self._busy
            )
            publisher = claim_publisher(workspace, unit.job, operation=new_operation())
            context.update(workspace=workspace, publisher=publisher)
            if unit.interrupt:
                self._interrupt(workspace, publisher)
            getattr(self, "_" + unit.mode.lower())(record, admission, context)
        except _Stop:
            terminal = "CANCELLED" if record.cancel_requested else "STOPPED"
        except BaseException as error:
            # A native call woken by the control lane ends as that control's
            # terminal; the owner's own failure category is kept beside it.
            failure = type(error).__name__ + ":" + str(error)[:200]
            terminal = (
                "CANCELLED"
                if record.cancel_requested
                else "STOPPED"
                if record.stop
                else "FAILED"
            )
        finally:
            # The durable cancellation first (forbid new work), by this thread,
            # which owns the publisher and its SQLite connection.
            if record.cancel_requested:
                self._durable_cancel(record, publisher)
            for step in context["closers"][::-1] + self._closure(context):
                try:
                    step()
                except BaseException as error:
                    with self._cond:
                        self._event(record, "CLOSURE_FAILED:" + type(error).__name__)
                    if failure is None:
                        failure = (
                            "CLOSURE:" + type(error).__name__ + ":" + str(error)[:100]
                        )
            settlement = "UNKNOWN"
            if workspace is not None:
                try:
                    if workspace._retired:
                        workspace.close()
                        workspace = open_workspace(
                            self.root, expected_identity=self.identity
                        )
                    fact = settle(workspace, self.owner, admission.identity)
                    settlement = None if fact.settlement is None else fact.settlement[1]
                except BaseException:
                    settlement = "UNKNOWN"
            _ADMITTED.discard(admission)
            for item in (publisher, workspace):
                if item is not None:
                    try:
                        item.close()
                    except BaseException:
                        pass
            with self._cond:
                record.settlement = settlement or "UNKNOWN"
                record.owner = None
                record.outbox = None
                self._release(record)
                self._finish(record, terminal, failure)

    def _durable_cancel(self, record, publisher) -> None:
        """The Publisher/SQLite owner records the durable job cancellation."""
        from pietto._project.project_job_store import cancel_job

        if publisher is None:
            outcome = "UNAVAILABLE:NO_PUBLISHER"
        else:
            try:
                cancel_job(publisher, operation=new_operation())
                outcome = "COMMITTED"
            except JobStoreError as error:
                outcome = (
                    "UNKNOWN"
                    if str(error) == "STORE_COMMIT_UNKNOWN"
                    else "REFUSED:" + str(error)
                )
        with self._cond:
            record.durable_cancel = outcome
            self._event(record, "DURABLE_CANCEL:" + outcome)

    def _closure(self, context) -> list:
        """The original closure of an opened attempt after a normal end, failure,
        cancel or stop: owner closed, capture/continuation end, and the attempt's
        own terminal (its real outcome, or NOT_EXECUTED without an owner)."""
        from pietto._project.project_job_store import (
            record_attempt,
            record_not_executed,
        )

        attempt = context.get("attempt")
        if attempt is None:
            return []
        publisher, owner = context["publisher"], context.get("owner")
        session = context.get("session")
        steps = []
        if owner is not None:
            steps.append(owner.close)
        if session is not None:
            steps.append(lambda: session.end(operation=new_operation()))
        if owner is None:
            steps.append(
                lambda: record_not_executed(
                    publisher, attempt, operation=new_operation()
                )
            )
        else:
            steps.append(
                lambda: record_attempt(
                    publisher, attempt, owner, operation=new_operation()
                )
            )
        return steps

    def _interrupt(self, workspace, publisher) -> None:
        """S11 publisher replacement: an earlier epoch's open attempts become
        INTERRUPTED with every remote layer UNKNOWN (never a success)."""
        from pietto._project.project_job_store import interrupt_attempt, job_record

        for item in job_record(workspace, publisher.job).attempts:
            if item.terminal is None and item.publisher_epoch < publisher.epoch:
                interrupt_attempt(publisher, item.identity, operation=new_operation())

    def _binding(self, workspace, unit):
        from pietto._project.project_job_capture import stored_binding

        if unit.template is not None:
            from pietto._project.project_execution_template import bind_values

            template = unit.template
            binding = bind_values(
                template, tuple(zip(template.slots, unit.values, strict=True))
            )
            route = read(
                workspace,
                lambda c: c.execute(
                    "SELECT route FROM generation WHERE identity = ? AND job = ?",
                    (unit.generation, unit.job),
                ).fetchone(),
            )
            if route is None:
                raise JobStoreError("GENERATION_UNKNOWN")
            return template, binding, route[0]
        pin, producer, compatibility = unit.trust
        return stored_binding(
            workspace,
            unit.job,
            unit.generation,
            expected_pin=pin,
            accepted_producer=producer,
            accepted_compatibility=compatibility,
        )

    def _native(self, record, context, binding, route):
        """Open the attempt's own native owner in this worker thread."""
        source = record.unit.source
        if source.route != route:
            raise JobStoreError("RUNTIME_ROUTE")
        owner = _owner(binding, source)
        context["owner"] = owner
        self._bind_owner(record, owner)
        self._activity(record, "WAITING_FOR_NATIVE")
        owner.open()
        return owner

    def _attempt(self, context, binding):
        from pietto._project.project_job_store import open_attempt

        unit = context["unit"]
        context["attempt"] = open_attempt(
            context["publisher"], unit.generation, binding, operation=new_operation()
        )
        return context["attempt"]

    def _capture_session(self, record, admission, context, owner, attempt):
        from pietto._project.project_job_capture import begin_capture
        from pietto._project.project_job_extraction import begin_extraction

        unit, publisher = record.unit, context["publisher"]
        begin = begin_extraction if unit.extraction else begin_capture
        session = begin(publisher, attempt, owner, operation=new_operation())
        session.admission = admission
        context["session"] = session
        return session

    def _capture(self, record, admission, context) -> None:
        unit, workspace = record.unit, context["workspace"]
        _template, binding, route = self._binding(workspace, unit)
        attempt = self._attempt(context, binding)
        owner = self._native(record, context, binding, route)
        session = self._capture_session(record, admission, context, owner, attempt)
        while True:
            self._check(record)
            self._activity(record, "WAITING_FOR_NATIVE")
            staged = session.stage()
            if staged is None:
                break
            self._activity(record, "STEPPING")
            session.publish(staged, operation=new_operation())
            self._count(record, "chunks")
            self._count(record, "rows", staged.stop - staged.start)
            self._count(record, "staged_peak", len(session.staged) + 1, peak=True)

    def _relay(self, record, admission, context) -> None:
        from pietto._project import project_job_delivery as d
        from pietto._project.project_job_sink import open_sink

        unit, workspace = record.unit, context["workspace"]
        publisher = context["publisher"]
        _template, binding, route = self._binding(workspace, unit)
        target = unit.sink
        if type(target) is not SinkTarget:
            raise JobStoreError("RUNTIME_UNIT")
        sink = open_sink(
            target.root,
            expected_identity=target.identity,
            busy_seconds=target.busy_seconds,
        )
        context["closers"].append(sink.close)
        accepted = d.accept_sink(
            sink,
            instance=target.identity,
            namespace=target.namespace,
            epoch=target.epoch,
            retention=target.retention,
            purpose=unit.purpose,
            seconds=unit.seconds,
        )
        pin, producer, compatibility = unit.trust
        window = dict(
            purpose=unit.purpose,
            route=route,
            values=unit.values,
            seconds=unit.seconds,
            batch_rows=unit.batch_rows,
            expected_pin=pin,
            accepted_producer=producer,
            accepted_compatibility=compatibility,
        )
        # The stream names the generation's capture: it exists only after begin.
        attempt = self._attempt(context, binding)
        owner = self._native(record, context, binding, route)
        capture = self._capture_session(record, admission, context, owner, attempt)
        stream = d.find_stream(
            workspace,
            unit.job,
            unit.generation,
            sink=target.identity,
            namespace=target.namespace,
            epoch=target.epoch,
        )
        if stream is None:
            stream = d.register_stream(
                publisher,
                d.accept_window(
                    workspace, unit.job, unit.generation, checkpoint=None, **window
                ),
                accepted,
                operation=new_operation(),
            ).get("stream")
        session = d.open_stream(publisher, stream, accepted, operation=new_operation())
        context["closers"].append(session.close)
        while True:
            self._check(record)
            self._activity(record, "STEPPING")
            step = d.relay(session, capture, rows=unit.rows, **window)
            self._count(record, "relay_" + step.lower())
            self._count(record, "delivered_position", session.position, peak=True)
            self._count(record, "observed_peak", capture.observed, peak=True)
            if step == "SOURCE_TERMINAL":
                return
            if step == "BLOCKED":
                with self._cond:
                    seen = record.resume
                self._activity(record, "WAITING_FOR_DOWNSTREAM")
                self._count(record, "downstream_waits")
                self._park(record, lambda: record.resume != seen)
                pending = session.pending
                if pending is not None:
                    self._activity(record, "STEPPING")
                    outcomes = session.reconcile(pending)
                    if any(s in d.CONFIRMED for s in outcomes.values()):
                        session.confirm(pending, operation=new_operation())

    def _recover(self, record, admission, context) -> None:
        from pietto._project import project_job_extraction as x

        unit, workspace = record.unit, context["workspace"]
        publisher = context["publisher"]
        pin, producer, compatibility = unit.trust
        acceptance = x.accept_recovery(
            workspace,
            unit.job,
            unit.generation,
            checkpoint=unit.checkpoint,
            purpose=unit.purpose,
            values=unit.values,
            seconds=unit.seconds,
            expected_pin=pin,
            accepted_producer=producer,
            accepted_compatibility=compatibility,
        )
        attempt = self._attempt(context, acceptance.binding)
        owner = self._native(record, context, acceptance.binding, acceptance.route)
        session = x.begin_continuation(
            publisher, acceptance, attempt, owner, operation=new_operation()
        )
        session.admission = admission
        context["session"] = session
        context["closers"].append(session.close)

        def barrier():
            if session.ready and not session.reconciled:
                session.reconcile(operation=new_operation())
                with self._cond:
                    self._event(record, "RECONCILED")
                for item in list(session.staged):
                    session.publish(item, operation=new_operation())
                    self._count(record, "chunks")

        while True:
            self._check(record)
            barrier()
            self._activity(record, "WAITING_FOR_NATIVE")
            items = session.stage()
            if items is None:
                break
            self._activity(record, "STEPPING")
            self._count(record, "pages")
            if session.reconciled:
                for item in items:
                    session.publish(item, operation=new_operation())
                    self._count(record, "chunks")
        barrier()

    def _replay(self, record, admission, context) -> None:
        from pietto._project import project_job_replay as r

        unit, workspace = record.unit, context["workspace"]
        publisher = context["publisher"]
        pin, producer, compatibility = unit.trust
        _template, _binding, route = self._binding(workspace, unit)
        consumer = unit.consumer or r.new_consumer()
        acceptance = r.accept_saved_read(
            workspace,
            unit.job,
            unit.generation,
            checkpoint=unit.checkpoint,
            consumer=consumer,
            scope=unit.scope,
            extent=unit.extent,
            purpose=unit.purpose,
            route=route,
            values=unit.values,
            expected_pin=pin,
            accepted_producer=producer,
            accepted_compatibility=compatibility,
            seconds=unit.seconds,
            batch_rows=unit.batch_rows,
        )
        if unit.register:
            r.register_consumer(publisher, acceptance, operation=new_operation())
        with self._cond:
            record.counters["consumer_registered"] = int(unit.register)
        replay = r.open_replay(publisher, acceptance, operation=new_operation())
        context["closers"].append(replay.close)
        while True:
            self._check(record)
            self._activity(record, "STEPPING")
            item = replay.next(unit.rows, operation=new_operation())
            if isinstance(item, r.SavedScopeEnd):
                self._count(record, "saved_scope_end")
                return
            # The batch may keep whole parent buffers alive: the measured held
            # bytes must stay within this unit's memory reservation.
            self._count(record, "held_bytes_peak", item.held_bytes, peak=True)
            if item.held_bytes > record.vector.memory:
                item.batch.close()
                raise JobStoreError("RUNTIME_MEMORY")
            with self._cond:
                record.outbox = item
                self._cond.notify_all()
            self._count(record, "issued")
            self._activity(record, "WAITING_FOR_DOWNSTREAM")
            self._park(record, lambda: bool(record.acks))
            with self._cond:
                acked = record.acks.popleft()
                record.outbox = None
            if acked is not item:
                raise JobStoreError("DELIVERY_FOREIGN")
            self._activity(record, "STEPPING")
            replay.acknowledge(item, operation=new_operation())
            self._count(record, "acknowledged", item.stop - item.start)

    def _publish(self, record, admission, context) -> None:
        from pietto._project import project_job_publication as p

        unit, workspace = record.unit, context["workspace"]
        publisher = context["publisher"]
        pin, producer, compatibility = unit.trust
        _template, _binding, route = self._binding(workspace, unit)
        isolation = read(
            workspace,
            lambda c: c.execute(
                "SELECT isolation FROM generation WHERE identity = ?",
                (unit.generation,),
            ).fetchone()[0],
        )
        acceptance = p.accept_publication(
            workspace,
            unit.job,
            unit.generation,
            checkpoint=unit.checkpoint,
            closing=unit.closing,
            purpose=unit.purpose,
            route=route,
            isolation=isolation,
            values=unit.values,
            expected_pin=pin,
            accepted_producer=producer,
            accepted_compatibility=compatibility,
            seconds=unit.seconds,
        )
        self._activity(record, "STEPPING")
        prepared = p.prepare_publication(
            publisher, acceptance, operation=new_operation()
        )
        self._count(record, "prepared")
        try:
            self._check(record)
        except _Stop as stop:
            # Known nonpublication: only this preparation's protection goes.
            p._release(publisher, prepared.retention, stop)
            raise
        p.publish_generation(publisher, prepared, operation=new_operation())
        self._count(record, "published")


def _owner(binding, source: NativeSource):
    """The route's own native owner over the original compiled request; the
    managed premise is built over this binding's own sources."""
    from pietto._project import project_execution as ex
    from pietto._project.project_execution_mysql import MySQLExecution
    from pietto._project.project_execution_postgres import PostgresExecution
    from pietto._project.project_execution_postgres_adbc import PostgresADBCExecution

    sources = binding.artifact.request.sources
    if source.route == "mysql_rows":
        premise: dict = {
            "mysql_deployment": ex.MySQLDeploymentPremise(
                source.access, sources, source.schemas
            )
        }
    else:
        premise = {
            "postgres_deployment": ex.PostgresDeploymentPremise(
                source.access, sources, source.schemas, source.route
            )
        }
    request = ex.prepare_compiled_execution(
        binding,
        source.access,
        route=source.route,
        limits=source.limits,
        isolation=source.isolation,
        **premise,
    )
    owners = {
        "postgres_rows": PostgresExecution,
        "postgres_adbc": PostgresADBCExecution,
        "mysql_rows": MySQLExecution,
    }
    return owners[source.route](request)
