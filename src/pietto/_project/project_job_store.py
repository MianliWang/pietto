"""Durable job metadata and one exclusive publisher per job over a workspace.

A stored job is protected specification and history, never execution
authority: loading needs fresh caller trust inputs, S10 rederives every
binding, and each attempt needs new access, premise, qualification and guards.
This module stores no result rows; S12 chunks and checkpoints belong to
project_job_capture. No effects, ACKs or completed generations are stored. A
local COMMIT is not a remote transaction ACK or result completion.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
import fcntl
import json
import os
import sqlite3
import stat
from typing import Any

from pietto._project.project_job_workspace import (
    JobStoreError,
    Workspace,
    admit,
    new_identity,
    read,
    valid_identity,
    write,
)

__all__: tuple[str, ...] = ()

MAX_VECTOR_BYTES = 4 * 1024 * 1024
MAX_DESCRIPTION_BYTES = 4 * 1024 * 1024
MAX_OUTCOME_BYTES = 64 * 1024
LIMITS = {
    "job": 1024,
    "binding": 16384,
    "generation": 16384,
    "attempt": 65536,
    "operation": 262144,
    "chunk": 65536,
    "retention": 16384,
}
MAX_ATTEMPT_ORDINAL = 1024
ROUTES = ("postgres_rows", "postgres_adbc", "mysql_rows")
ISOLATIONS = ("stable", "serializable")
INTERRUPTED = {
    "basis": "PUBLISHER_EPOCH_ENDED_WITHOUT_TERMINAL",
    "source": "UNKNOWN",
    "transaction": "UNKNOWN",
    "delivery": "UNKNOWN",
    "cleanup": "UNKNOWN",
    "remote_source_use_end": "UNKNOWN",
}
_FENCE = (
    "UPDATE job SET revision = revision + 1 WHERE identity = ?"
    " AND publisher_epoch = ? AND publisher_instance = ? AND revision = ?"
    " AND state = 'ACTIVE'"
)
_FENCE_CONTROL = (
    "UPDATE job SET revision = revision + 1 WHERE identity = ?"
    " AND publisher_epoch = ? AND publisher_instance = ? AND revision = ?"
    " AND state IN ('ACTIVE', 'CANCELLED')"
)
_FENCE_CANCEL = (
    "UPDATE job SET revision = revision + 1, state = 'CANCELLED' WHERE identity = ?"
    " AND publisher_epoch = ? AND publisher_instance = ? AND revision = ?"
    " AND state = 'ACTIVE'"
)


def _json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def new_operation() -> str:
    """A caller keeps this before calling, so a lost reply can be queried."""
    return new_identity("op")


@dataclass(frozen=True, slots=True)
class OperationResult:
    """COMMITTED_THIS_CALL, PREVIOUSLY_COMMITTED (replay) or QUERIED; never an ACK."""

    operation: str
    kind: str
    job: str
    sequence: int
    result: tuple[tuple[str, Any], ...]
    observation: str

    def get(self, name: str) -> Any:
        return dict(self.result)[name]


class Publisher:
    """Process-local exclusive writer of one job; never passed to another process."""

    __slots__ = (
        "workspace",
        "job",
        "epoch",
        "instance",
        "revision",
        "_fd",
        "_pid",
        "_closed",
    )

    def __init__(self, workspace, job, epoch, instance, revision, fd):
        self.workspace = workspace
        self.job = job
        self.epoch = epoch
        self.instance = instance
        self.revision = revision
        self._fd = fd
        self._pid = os.getpid()
        self._closed = False

    def __repr__(self) -> str:
        return f"Publisher(job={self.job!r}, epoch={self.epoch!r})"

    def use(self) -> Workspace:
        if self._pid != os.getpid():
            raise JobStoreError("PUBLISHER_FOREIGN_PROCESS")
        if self._closed:
            raise JobStoreError("PUBLISHER_CLOSED")
        return self.workspace

    def close(self) -> None:
        """Close this descriptor once; inherited descriptions may still hold the lock."""
        if self._closed:
            return
        if self._pid != os.getpid():
            raise JobStoreError("PUBLISHER_FOREIGN_PROCESS")
        self._closed = True
        os.close(self._fd)


@dataclass(frozen=True, slots=True, eq=False)
class AttemptHandle:
    publisher: Publisher = field(repr=False)
    identity: str
    generation: str
    ordinal: int
    route: str
    isolation: str
    binding: Any = field(repr=False)


@dataclass(frozen=True, slots=True)
class GenerationRecord:
    identity: str
    binding: str
    route: str
    isolation: str


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    identity: str
    generation: str
    ordinal: int
    publisher_epoch: int
    publisher_instance: str
    terminal: str | None
    terminal_epoch: int | None
    outcome: tuple[tuple[str, Any], ...] | None


@dataclass(frozen=True, slots=True)
class JobRecord:
    identity: str
    state: str
    publisher_epoch: int
    publisher_instance: str | None
    revision: int
    pin: str
    producer: str
    compatibility: tuple
    bundle_bytes: int
    bindings: tuple[str, ...]
    generations: tuple[GenerationRecord, ...]
    attempts: tuple[AttemptRecord, ...]
    operations: tuple[OperationResult, ...]


def _pairs(document: str) -> tuple[tuple[str, Any], ...]:
    value = json.loads(document)
    return tuple(
        (k, tuple(v) if type(v) is list else v) for k, v in sorted(value.items())
    )


def _limit(connection: sqlite3.Connection, table: str) -> None:
    if (
        connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        >= LIMITS[table]
    ):
        raise JobStoreError("STORE_LIMIT")


def _operate(workspace, operation, kind, request, effect, *, payload=0, control=False):
    """Replay check, conditional effect and operation record in ONE transaction."""
    if not valid_identity(operation, "op"):
        raise JobStoreError("OPERATION_IDENTITY")
    text = _json(request)
    admit(workspace, payload + len(text.encode("utf-8")), control=control)

    def body(connection):
        row = connection.execute(
            "SELECT sequence, kind, request, job, result FROM operation"
            " WHERE identity = ?",
            (operation,),
        ).fetchone()
        if row is not None:
            if (row[1], row[2]) != (kind, text):
                raise JobStoreError("OPERATION_CONFLICT")
            return OperationResult(
                operation, kind, row[3], row[0], _pairs(row[4]), "PREVIOUSLY_COMMITTED"
            )
        _limit(connection, "operation")
        subject, result = effect(connection)
        cursor = connection.execute(
            "INSERT INTO operation(identity, kind, job, request, result)"
            " VALUES (?, ?, ?, ?, ?)",
            (operation, kind, subject, text, _json(result)),
        )
        if cursor.lastrowid is None:
            raise JobStoreError("STORE_CONSTRAINT")
        return OperationResult(
            operation,
            kind,
            subject,
            cursor.lastrowid,
            _pairs(_json(result)),
            "COMMITTED_THIS_CALL",
        )

    return write(workspace, body)


def _fence(connection, publisher, statement=_FENCE) -> int:
    """The write-side check: workspace job, current publisher, revision and state."""
    cursor = connection.execute(
        statement,
        (publisher.job, publisher.epoch, publisher.instance, publisher.revision),
    )
    if cursor.rowcount == 1:
        return publisher.revision + 1
    row = connection.execute(
        "SELECT publisher_epoch, publisher_instance, revision FROM job"
        " WHERE identity = ?",
        (publisher.job,),
    ).fetchone()
    if row is None:
        raise JobStoreError("JOB_UNKNOWN")
    if (row[0], row[1]) != (publisher.epoch, publisher.instance):
        raise JobStoreError("PUBLISHER_STALE")
    if row[2] != publisher.revision:
        raise JobStoreError("PUBLISHER_REVISION")
    raise JobStoreError("JOB_STATE")


def _advance(publisher: Publisher, result: OperationResult) -> OperationResult:
    if result.observation == "COMMITTED_THIS_CALL":
        publisher.revision = result.get("revision")
    return result


def _template_root(template):
    from pietto._project.project_execution_binding_verification import verify_template
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    verify_template(template)
    request = template.artifact.request
    if type(request) is not CompiledPreparedEmission:
        raise JobStoreError("JOB_TEMPLATE")
    root = request.verification.completed.root
    root.verify()
    return root


def _binding_root(binding):
    from pietto._project.project_execution_binding_verification import verify_binding
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    verify_binding(binding)
    request = binding.artifact.request
    if type(request) is not CompiledPreparedEmission:
        raise JobStoreError("BINDING_ROOT")
    return request.verification.completed.root


def _slots(root) -> str:
    from pietto._project.project_compiled_schema import _wire

    return _json(
        _wire(
            tuple(
                (r.address, r.get("tag"), r.get("site"), r.get("literal"))
                for r in root.description.records
                if r.address.kind == "slot"
            )
        )
    )


def _vector(binding) -> str:
    """Canonical typed vector (S10 scalar wire): Bool/Int/±0/Float bits/Text kept."""
    from pietto._project.project_compiled_schema import Scalar, scalar_wire

    text = _json(
        [
            scalar_wire(Scalar(slot.tag, value))
            for slot, value in zip(binding.template.slots, binding.values, strict=True)
        ]
    )
    if len(text.encode("utf-8")) > MAX_VECTOR_BYTES:
        raise JobStoreError("BINDING_VECTOR")
    return text


def _description(binding, route) -> str:
    from pietto._project.project_compiled_schema import CompiledError, _wire
    from pietto._project.project_execution_template import describe_compiled_binding

    value = describe_compiled_binding(binding, route=route)
    try:
        text = _json(
            [
                [f.name, _wire(getattr(value, f.name))]
                for f in fields(value)
                if f.name != "binding_reference"
            ]
        )
    except CompiledError:
        raise JobStoreError("GENERATION_DESCRIPTION") from None
    if len(text.encode("utf-8")) > MAX_DESCRIPTION_BYTES:
        raise JobStoreError("GENERATION_DESCRIPTION")
    return text


def _job_row(workspace, job):
    if not valid_identity(job, "job"):
        raise JobStoreError("JOB_UNKNOWN")
    row = read(
        workspace,
        lambda c: c.execute(
            "SELECT pin, producer, compatibility, state FROM job WHERE identity = ?",
            (job,),
        ).fetchone(),
    )
    if row is None:
        raise JobStoreError("JOB_UNKNOWN")
    return row


def register_job(workspace: Workspace, template, *, operation: str) -> OperationResult:
    """Persist this live or loaded template's exact pinned bundle bytes."""
    from pietto._project.project_compiled_schema import (
        MAX_BYTES,
        _wire,
        content_pin,
        encode,
    )

    root = _template_root(template)
    raw = encode(root.description)
    if len(raw) > MAX_BYTES or content_pin(raw) != root.expected_pin:
        raise JobStoreError("JOB_BUNDLE")
    compatibility = _wire(root.accepted_compatibility)
    request = {
        "bytes": len(raw),
        "compatibility": compatibility,
        "pin": root.expected_pin,
        "producer": root.accepted_producer,
    }

    def effect(connection):
        _limit(connection, "job")
        job = new_identity("job")
        connection.execute(
            "INSERT INTO job(identity, bundle, pin, producer, compatibility, state,"
            " publisher_epoch, publisher_instance, revision)"
            " VALUES (?, ?, ?, ?, ?, 'ACTIVE', 0, NULL, 1)",
            (job, raw, root.expected_pin, root.accepted_producer, _json(compatibility)),
        )
        return job, {"job": job, "revision": 1}

    return _operate(
        workspace, operation, "register_job", request, effect, payload=len(raw)
    )


def claim_publisher(workspace: Workspace, job: str, *, operation: str) -> Publisher:
    """Nonblocking per-job OS lock, then a durable higher epoch; no steal or retry."""
    _job_row(workspace, job)
    if not valid_identity(operation, "op"):
        raise JobStoreError("OPERATION_IDENTITY")
    locks = workspace.locks_fd()
    name = job + ".lock"
    fd = os.open(
        name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=locks
    )
    try:
        state = os.fstat(fd)
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_uid != os.geteuid()
            or state.st_mode & 0o077
            or state.st_nlink != 1
        ):
            raise JobStoreError("PUBLISHER_LOCK_OBJECT")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise JobStoreError("PUBLISHER_BUSY") from None
        current = os.stat(name, dir_fd=locks, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (state.st_dev, state.st_ino):
            raise JobStoreError("PUBLISHER_LOCK_OBJECT")
        instance = new_identity("pub")

        def effect(connection):
            row = connection.execute(
                "SELECT publisher_epoch, revision FROM job WHERE identity = ?", (job,)
            ).fetchone()
            if row is None:
                raise JobStoreError("JOB_UNKNOWN")
            epoch, revision = row[0] + 1, row[1] + 1
            cursor = connection.execute(
                "UPDATE job SET publisher_epoch = ?, publisher_instance = ?,"
                " revision = ? WHERE identity = ? AND publisher_epoch = ?"
                " AND revision = ?",
                (epoch, instance, revision, job, row[0], row[1]),
            )
            actual = connection.execute(
                "SELECT publisher_epoch, publisher_instance, revision FROM job"
                " WHERE identity = ?",
                (job,),
            ).fetchone()
            if cursor.rowcount != 1 or actual != (epoch, instance, revision):
                raise JobStoreError("STORE_CONSTRAINT")
            return job, {"epoch": epoch, "instance": instance, "revision": revision}

        result = _operate(
            workspace, operation, "claim", {"job": job}, effect, control=True
        )
        if result.observation != "COMMITTED_THIS_CALL":
            raise JobStoreError("PUBLISHER_CLAIM_REPLAYED")
        publisher = Publisher(
            workspace,
            job,
            result.get("epoch"),
            result.get("instance"),
            result.get("revision"),
            fd,
        )
        fd = -1
        return publisher
    finally:
        if fd >= 0:
            os.close(fd)


def _identity_request(publisher: Publisher, **values) -> dict:
    return {
        "job": publisher.job,
        "publisher": [publisher.epoch, publisher.instance],
        **values,
    }


def register_binding(
    publisher: Publisher, binding, *, operation: str
) -> OperationResult:
    """A distinct durable binding record holding the exact protected typed vector."""
    workspace = publisher.use()
    root = _binding_root(binding)
    if _job_row(workspace, publisher.job)[0] != root.expected_pin:
        raise JobStoreError("BINDING_ROOT")
    slots, vector = _slots(root), _vector(binding)
    request = _identity_request(publisher, slots=slots, vector=vector)

    def effect(connection):
        revision = _fence(connection, publisher)
        _limit(connection, "binding")
        identity = new_identity("bind")
        connection.execute(
            "INSERT INTO binding(identity, job, slots, vector) VALUES (?, ?, ?, ?)",
            (identity, publisher.job, slots, vector),
        )
        return publisher.job, {"binding": identity, "revision": revision}

    return _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "register_binding",
            request,
            effect,
            payload=len(slots) + len(vector),
        ),
    )


def _binding_row(workspace, job, identity):
    if not valid_identity(identity, "bind"):
        raise JobStoreError("BINDING_UNKNOWN")
    row = read(
        workspace,
        lambda c: c.execute(
            "SELECT slots, vector FROM binding WHERE identity = ? AND job = ?",
            (identity, job),
        ).fetchone(),
    )
    if row is None:
        raise JobStoreError("BINDING_UNKNOWN")
    return row


def _same_binding(workspace, job, record, binding) -> None:
    root = _binding_root(binding)
    slots, vector = _binding_row(workspace, job, record)
    if (
        _job_row(workspace, job)[0] != root.expected_pin
        or _slots(root) != slots
        or _vector(binding) != vector
    ):
        raise JobStoreError("BINDING_VECTOR")


def register_generation(
    publisher: Publisher,
    record: str,
    binding,
    *,
    route: str,
    isolation: str,
    operation: str,
) -> OperationResult:
    """Immutable logical result namespace; registration is not completion."""
    workspace = publisher.use()
    if route not in ROUTES or isolation not in ISOLATIONS:
        raise JobStoreError("GENERATION_DESCRIPTION")
    _same_binding(workspace, publisher.job, record, binding)
    description = _description(binding, route)
    request = _identity_request(
        publisher,
        binding=record,
        route=route,
        isolation=isolation,
        description=description,
    )

    def effect(connection):
        revision = _fence(connection, publisher)
        _limit(connection, "generation")
        identity = new_identity("gen")
        connection.execute(
            "INSERT INTO generation(identity, job, binding, route, isolation,"
            " description) VALUES (?, ?, ?, ?, ?, ?)",
            (identity, publisher.job, record, route, isolation, description),
        )
        return publisher.job, {"generation": identity, "revision": revision}

    return _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "register_generation",
            request,
            effect,
            payload=len(description),
        ),
    )


def open_attempt(
    publisher: Publisher, generation: str, binding, *, operation: str
) -> AttemptHandle:
    """A new attempt of an exact generation with a freshly rederived binding."""
    workspace = publisher.use()
    if not valid_identity(generation, "gen"):
        raise JobStoreError("GENERATION_UNKNOWN")
    row = read(
        workspace,
        lambda c: c.execute(
            "SELECT binding, route, isolation, description FROM generation"
            " WHERE identity = ? AND job = ?",
            (generation, publisher.job),
        ).fetchone(),
    )
    if row is None:
        raise JobStoreError("GENERATION_UNKNOWN")
    record, route, isolation, description = row
    _same_binding(workspace, publisher.job, record, binding)
    if _description(binding, route) != description:
        raise JobStoreError("GENERATION_DESCRIPTION")
    request = _identity_request(
        publisher, generation=generation, binding_reference=binding.instance_reference
    )

    def effect(connection):
        revision = _fence(connection, publisher)
        if connection.execute(
            "SELECT 1 FROM attempt a WHERE a.job = ? AND NOT EXISTS"
            " (SELECT 1 FROM attempt_terminal t WHERE t.attempt = a.identity)",
            (publisher.job,),
        ).fetchone():
            raise JobStoreError("ATTEMPT_OPEN")
        _limit(connection, "attempt")
        ordinal = (
            connection.execute(
                "SELECT coalesce(max(ordinal), 0) FROM attempt WHERE generation = ?",
                (generation,),
            ).fetchone()[0]
            + 1
        )
        if ordinal > MAX_ATTEMPT_ORDINAL:
            raise JobStoreError("STORE_LIMIT")
        identity = new_identity("att")
        connection.execute(
            "INSERT INTO attempt(identity, generation, job, ordinal, publisher_epoch,"
            " publisher_instance, binding_reference) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                identity,
                generation,
                publisher.job,
                ordinal,
                publisher.epoch,
                publisher.instance,
                binding.instance_reference,
            ),
        )
        return publisher.job, {
            "attempt": identity,
            "ordinal": ordinal,
            "revision": revision,
        }

    result = _advance(
        publisher,
        _operate(workspace, operation, "open_attempt", request, effect),
    )
    return AttemptHandle(
        publisher,
        result.get("attempt"),
        generation,
        result.get("ordinal"),
        route,
        isolation,
        binding,
    )


def _terminal(publisher, attempt, kind, outcome, operation):
    workspace = publisher.use()
    text = _json(outcome)
    if len(text.encode("utf-8")) > MAX_OUTCOME_BYTES:
        raise JobStoreError("ATTEMPT_OUTCOME")
    request = _identity_request(publisher, attempt=attempt, kind=kind, outcome=outcome)

    def effect(connection):
        revision = _fence(connection, publisher, _FENCE_CONTROL)
        row = connection.execute(
            "SELECT publisher_epoch, publisher_instance, binding_reference,"
            " (SELECT count(*) FROM attempt_terminal WHERE attempt = identity)"
            " FROM attempt WHERE identity = ? AND job = ?",
            (attempt, publisher.job),
        ).fetchone()
        if row is None:
            raise JobStoreError("ATTEMPT_UNKNOWN")
        if row[3]:
            raise JobStoreError("ATTEMPT_TERMINAL")
        if kind == "INTERRUPTED":
            if row[0] >= publisher.epoch:
                raise JobStoreError("ATTEMPT_PUBLISHER")
        elif (row[0], row[1], row[2]) != (
            publisher.epoch,
            publisher.instance,
            outcome["binding_reference"],
        ):
            raise JobStoreError("ATTEMPT_PUBLISHER")
        connection.execute(
            "INSERT INTO attempt_terminal(attempt, kind, publisher_epoch, outcome)"
            " VALUES (?, ?, ?, ?)",
            (attempt, kind, publisher.epoch, text),
        )
        return publisher.job, {"attempt": attempt, "kind": kind, "revision": revision}

    return _advance(
        publisher,
        _operate(
            workspace, operation, "attempt_terminal", request, effect, control=True
        ),
    )


def record_attempt(
    publisher: Publisher, attempt: AttemptHandle, owner, *, operation: str
) -> OperationResult:
    """Store the exact layered outcome of this attempt's closed native owner."""
    from pietto._project.project_execution import (
        compiled_attempt_outcome,
        verify_compiled_owner,
    )

    publisher.use()
    if type(attempt) is not AttemptHandle or attempt.publisher is not publisher:
        raise JobStoreError("ATTEMPT_PUBLISHER")
    request = owner.request
    if request.binding is not attempt.binding or request.isolation != attempt.isolation:
        raise JobStoreError("ATTEMPT_OWNER")
    verify_compiled_owner(owner)
    outcome = asdict(compiled_attempt_outcome(owner))
    if (
        outcome["binding_reference"] != attempt.binding.instance_reference
        or outcome["route"] != attempt.route
    ):
        raise JobStoreError("ATTEMPT_OWNER")
    # Each route has its own cleanup vocabulary; the owner's state is authority.
    if owner._closed is not True:
        raise JobStoreError("ATTEMPT_OWNER_OPEN")
    return _terminal(publisher, attempt.identity, "OUTCOME", outcome, operation)


def record_not_executed(
    publisher: Publisher, attempt: AttemptHandle, *, operation: str
) -> OperationResult:
    """The publisher reports that no native owner was created for this attempt."""
    publisher.use()
    if type(attempt) is not AttemptHandle or attempt.publisher is not publisher:
        raise JobStoreError("ATTEMPT_PUBLISHER")
    outcome = {
        "basis": "PUBLISHER_REPORTED_NO_NATIVE_OWNER",
        "binding_reference": attempt.binding.instance_reference,
    }
    return _terminal(publisher, attempt.identity, "NOT_EXECUTED", outcome, operation)


def interrupt_attempt(
    publisher: Publisher, attempt: str, *, operation: str
) -> OperationResult:
    """A later epoch closes an earlier epoch's open attempt; remote layers UNKNOWN."""
    if not valid_identity(attempt, "att"):
        raise JobStoreError("ATTEMPT_UNKNOWN")
    return _terminal(publisher, attempt, "INTERRUPTED", INTERRUPTED, operation)


def cancel_job(publisher: Publisher, *, operation: str) -> OperationResult:
    """Forbid new work; this is not evidence that any source stopped."""
    workspace = publisher.use()

    def effect(connection):
        revision = _fence(connection, publisher, _FENCE_CANCEL)
        return publisher.job, {"state": "CANCELLED", "revision": revision}

    return _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "cancel_job",
            _identity_request(publisher),
            effect,
            control=True,
        ),
    )


def query_operation(workspace: Workspace, operation: str) -> OperationResult | None:
    if not valid_identity(operation, "op"):
        raise JobStoreError("OPERATION_IDENTITY")
    row = read(
        workspace,
        lambda c: c.execute(
            "SELECT sequence, kind, job, result FROM operation WHERE identity = ?",
            (operation,),
        ).fetchone(),
    )
    if row is None:
        return None
    return OperationResult(operation, row[1], row[2], row[0], _pairs(row[3]), "QUERIED")


def job_record(workspace: Workspace, job: str) -> JobRecord:
    """One consistent read snapshot of a job's metadata and complete history."""
    from pietto._project.project_compiled_schema import _read

    if not valid_identity(job, "job"):
        raise JobStoreError("JOB_UNKNOWN")

    def body(c):
        head = c.execute(
            "SELECT state, publisher_epoch, publisher_instance, revision, pin,"
            " producer, compatibility, length(bundle) FROM job WHERE identity = ?",
            (job,),
        ).fetchone()
        if head is None:
            raise JobStoreError("JOB_UNKNOWN")
        return (
            head,
            c.execute(
                "SELECT identity, binding, route, isolation FROM generation"
                " WHERE job = ?",
                (job,),
            ).fetchall(),
            c.execute(
                "SELECT a.identity, a.generation, a.ordinal, a.publisher_epoch,"
                " a.publisher_instance, t.kind, t.publisher_epoch, t.outcome"
                " FROM attempt a LEFT JOIN attempt_terminal t ON t.attempt = a.identity"
                " WHERE a.job = ?",
                (job,),
            ).fetchall(),
            c.execute(
                "SELECT identity, sequence, kind, result FROM operation WHERE job = ?"
                " ORDER BY sequence",
                (job,),
            ).fetchall(),
        )

    head, generations, attempts, operations = read(workspace, body)
    compatibility = _read(json.loads(head[6]))
    if type(compatibility) is not tuple:
        raise JobStoreError("JOB_COMPATIBILITY")
    history = tuple(
        OperationResult(o[0], o[2], job, o[1], _pairs(o[3]), "QUERIED")
        for o in operations
    )
    created = {
        r.get(name): r.sequence
        for r in history
        for name in ("binding", "generation", "attempt")
        if r.kind in ("register_binding", "register_generation", "open_attempt")
        and name in dict(r.result)
    }
    return JobRecord(
        job,
        head[0],
        head[1],
        head[2],
        head[3],
        head[4],
        head[5],
        compatibility,
        head[7],
        tuple(r.get("binding") for r in history if r.kind == "register_binding"),
        tuple(
            GenerationRecord(*g)
            for g in sorted(generations, key=lambda g: created.get(g[0], -1))
        ),
        tuple(
            AttemptRecord(
                a[0],
                a[1],
                a[2],
                a[3],
                a[4],
                a[5],
                a[6],
                None if a[7] is None else _pairs(a[7]),
            )
            for a in sorted(attempts, key=lambda a: created.get(a[0], -1))
        ),
        history,
    )


def load_job(
    workspace: Workspace,
    job: str,
    *,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: tuple,
):
    """Fresh template from stored bytes and FRESH caller trust inputs only."""
    from pietto._project.project_compiled_loading import (
        load_compiled,
        supported_compatibility,
    )
    from pietto._project.project_compiled_schema import _read
    from pietto._project.project_execution_template import prepare_compiled_template

    if not valid_identity(job, "job"):
        raise JobStoreError("JOB_UNKNOWN")
    row = read(
        workspace,
        lambda c: c.execute(
            "SELECT bundle, pin, producer, compatibility FROM job WHERE identity = ?",
            (job,),
        ).fetchone(),
    )
    if row is None:
        raise JobStoreError("JOB_UNKNOWN")
    stored = _read(json.loads(row[3]))
    if stored != supported_compatibility():
        raise JobStoreError("JOB_COMPATIBILITY")
    if (row[1], row[2], stored) != (
        expected_pin,
        accepted_producer,
        accepted_compatibility,
    ):
        raise JobStoreError("JOB_TRUST_INPUT")
    root = load_compiled(
        row[0],
        expected_pin=expected_pin,
        accepted_producer=accepted_producer,
        accepted_compatibility=accepted_compatibility,
    )
    return prepare_compiled_template(root)


def bind_record(workspace: Workspace, job: str, template, record: str):
    """Rederive a NEW S10 binding from a stored vector; old references never return."""
    from pietto._project.project_compiled_schema import CompiledError, scalar_read
    from pietto._project.project_execution_template import bind_values

    root = _template_root(template)
    slots, vector = _binding_row(workspace, job, record)
    if _job_row(workspace, job)[0] != root.expected_pin or _slots(root) != slots:
        raise JobStoreError("BINDING_ROOT")
    try:
        values = tuple(scalar_read(item) for item in json.loads(vector))
    except (CompiledError, ValueError, TypeError):
        raise JobStoreError("BINDING_VECTOR") from None
    if len(values) != len(template.slots) or any(
        value.tag != slot.tag for value, slot in zip(values, template.slots)
    ):
        raise JobStoreError("BINDING_VECTOR")
    return bind_values(
        template,
        tuple((slot, value.value) for slot, value in zip(template.slots, values)),
    )
