"""S12 captured result chunks, fenced checkpoints and retention references.

A capture consumes checked batches from one real S10 owner of one open S11
attempt. Each chunk file is durable before its metadata is published under the
publisher fence, and each publication creates an immutable checkpoint whose
contiguous frontier is recomputed from its complete member set. Committed is
not complete: source, transaction, delivery, cleanup and remote use stay the
attempt's own layers. Nothing here is consumer recovery, extraction resume, an
ACK, generation publication, expiry or garbage collection.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import json
import os
from typing import Any

from pietto._project import project_job_chunks as chunks
from pietto._project.project_job_store import (
    _FENCE,
    _FENCE_CONTROL,
    AttemptHandle,
    OperationResult,
    Publisher,
    _advance,
    _description,
    _fence,
    _identity_request,
    _json,
    _limit,
    _operate,
    _pairs,
)
from pietto._project.project_job_workspace import (
    CHUNKS,
    STAGING,
    JobStoreError,
    Workspace,
    new_identity,
    read,
    supports,
    valid_identity,
)

__all__: tuple[str, ...] = ()

MAX_CHUNKS_PER_GENERATION = 256
MAX_STAGED = 8
MAX_SCOPE_BYTES = 4096
NOT_IMPLEMENTED = "NOT_IMPLEMENTED_BY_S12"
LAYERS = (
    "source",
    "transaction",
    "delivery",
    "cancel",
    "cleanup",
    "remote_source_use_end",
)


def _capturing(workspace: Workspace) -> None:
    """Capture-capable formats (v2, v3) by exact feature; v1 is never upgraded."""
    if not supports(workspace, "result-chunks"):
        raise JobStoreError("WORKSPACE_CAPTURE_FORMAT")


def contract_digest(output) -> str:
    """The output-contract identity that the original IPC owner puts in each frame."""
    from pietto._project.project_result_ipc import contract_digest as identity

    return identity(output.contract).hex()


def coordinate_scheme(refinement) -> str:
    """Choice, ordering, structural keys and public erasure of a refined capture."""
    if refinement is None:
        return _json(None)
    unit = refinement.units[-1]
    return _json(
        {
            "choice": refinement.policy.choice,
            "coordinates": [
                [c.tag, dict(c.storage)["kind"]]
                for c in unit.order_coordinates + unit.coordinates
            ],
            "directions": list(unit.directions) + ["asc"] * len(unit.key_names),
            "erasure": [position for position, _ in refinement.erasure],
            "keys": list(unit.key_names),
            "order": list(unit.order_names),
            "prefix": refinement.prefix,
            "rule": unit.rule,
            "version": chunks.COORDINATES,
        }
    )


def frontier(ranges) -> int:
    """Maximal contiguous committed prefix from position 0 (never max(stop))."""
    position = 0
    for start, stop in sorted(ranges):
        if start != position:
            break
        position = stop
    return position


def holes(ranges, end=None) -> tuple[tuple[int, int], ...]:
    missing, position = [], 0
    for start, stop in sorted(ranges):
        if start > position:
            missing.append((position, start))
        position = max(position, stop)
    if end is not None and end > position:
        missing.append((position, end))
    return tuple(missing)


@dataclass(frozen=True, slots=True, eq=False)
class StagedChunk:
    """A durable but unpublished file of one live session; never a receipt."""

    session: Any = field(repr=False)
    identity: str
    start: int
    stop: int
    batches: int
    name: str
    size: int
    digest: str = field(repr=False)
    descriptor: str = field(repr=False)
    device: int = field(repr=False)
    inode: int = field(repr=False)
    changed: int = field(repr=False)


class CaptureSession:
    """Process-local consumer of one owner; never passed to another process."""

    __slots__ = (
        "publisher",
        "attempt",
        "owner",
        "record",
        "kind",
        "contract",
        "_binding",
        "_observed",
        "_batches",
        "_checked",
        "_staged",
        "_terminal",
        "_failed",
        "_ended",
        "_pid",
    )

    def __init__(self, publisher, attempt, owner, record, kind, contract):
        self.publisher = publisher
        self.attempt = attempt
        self.owner = owner
        self.record = record
        self.kind = kind
        self.contract = contract
        self._binding = None
        self._observed = self._batches = 0
        self._checked = None
        self._staged: dict[str, StagedChunk] = {}
        self._terminal = None
        self._failed = False
        self._ended = False
        self._pid = os.getpid()

    def __repr__(self) -> str:
        return f"CaptureSession(generation={self.attempt.generation!r})"

    @property
    def observed(self) -> int:
        """Rows received from the owner's checked stream (positions [0, observed))."""
        return self._observed

    @property
    def terminal(self) -> str | None:
        return self._terminal

    @property
    def staged(self) -> tuple[StagedChunk, ...]:
        return tuple(self._staged.values())

    def _use(self) -> Workspace:
        if self._pid != os.getpid():
            raise JobStoreError("CAPTURE_FOREIGN_PROCESS")
        return self.publisher.use()

    def stage(self) -> StagedChunk | None:
        """Consume the owner's next checked batch into one durable unpublished file."""
        from pietto._project.project_arrow_interop import ManagedBatch

        workspace = self._use()
        if self._ended:
            raise JobStoreError("CAPTURE_ENDED")
        if self._terminal is not None:
            return None
        if self._failed:
            raise JobStoreError("CAPTURE_FAILED")
        if len(self._staged) >= MAX_STAGED:
            raise JobStoreError("CAPTURE_STAGED_LIMIT")
        owner = self.owner
        payloads = owner._payloads
        current = (0, 0) if payloads is None else (payloads.rows, payloads.batches)
        if current != (self._observed, self._batches):
            raise JobStoreError("CAPTURE_LINEAGE")
        try:
            batch = next(owner)
        except StopIteration:
            self._terminal = self._owner_terminal()
            if self._observed == 0 and self._batches == 0 and self._terminal == "EOF":
                # An empty native result keeps its exact schema; nothing advances.
                if owner._payloads is None:
                    raise JobStoreError("CAPTURE_SCHEMA_UNAVAILABLE") from None
                self._binding = owner._payloads.binding
                return self._checked_step(workspace, None, 0, None, "EOF")
            return None
        except BaseException:
            self._terminal = self._owner_terminal()
            raise
        try:
            payloads = owner._payloads
            if (
                type(batch) is not ManagedBatch
                or payloads is None
                or batch._captured[0] is not payloads.binding
                or (self._binding is not None and payloads.binding is not self._binding)
            ):
                raise JobStoreError("CAPTURE_LINEAGE")
            from pietto._project.project_arrow_result import _arrow

            array = _arrow().record_batch(batch)
            rows = array.num_rows
            if not 0 < rows <= chunks.MAX_ROWS or (payloads.rows, payloads.batches) != (
                self._observed + rows,
                self._batches + 1,
            ):
                raise JobStoreError("CAPTURE_LINEAGE")
            coordinates = None
            if self.kind == "REFINED":
                coordinates = self._coordinates(rows)
            self._binding = payloads.binding
            return self._checked_step(workspace, array, rows, coordinates, None)
        finally:
            batch.close()

    def _checked_step(self, workspace, array, rows, coordinates, terminal):
        # Positions follow the received stream even if this file then fails;
        # a failed materialization ends staging and leaves an honest hole.
        start, batches = self._observed, 0 if array is None else 1
        self._observed += rows
        self._batches += batches
        try:
            return self._materialize(
                workspace,
                self._encode(array, rows),
                start,
                rows,
                batches,
                coordinates,
                terminal,
            )
        except BaseException:
            self._failed = True
            raise

    def _owner_terminal(self) -> str:
        from pietto._project.project_execution import compiled_attempt_outcome

        if self.owner._closed is not True:
            return "UNKNOWN"
        try:
            return compiled_attempt_outcome(self.owner).source
        except ValueError:
            return "UNKNOWN"

    def _coordinates(self, rows: int) -> list:
        from pietto._project.project_refinement_enumeration import CheckedPage

        enumeration = self.owner.enumeration
        checked = enumeration.last_committed
        if (
            type(checked) is not CheckedPage
            or checked is self._checked
            or checked.request.owner is not enumeration
            or len(checked.rows) != rows
            or len(checked.coordinates) != rows
            or enumeration.progress[0] != self._observed + rows
        ):
            raise JobStoreError("CAPTURE_LINEAGE")
        self._checked = checked
        return [[chunks.coordinate_wire(v) for v in key] for key in checked.coordinates]

    def _encode(self, array, rows) -> bytes:
        """The unchanged S10 IPC writer over exactly this checked extent."""
        from pietto._project.project_arrow_result import _arrow
        from pietto._project.project_result_ipc import IPCLimits, encode_ipc

        binding = self._binding
        if binding is None:
            raise JobStoreError("CAPTURE_LINEAGE")
        source = _arrow().RecordBatchReader.from_batches(
            binding.schema, [] if array is None else [array]
        )
        return encode_ipc(
            binding,
            source,
            expected_rows=rows,
            ipc_limits=IPCLimits(chunks.MAX_FRAME_BYTES),
        )

    def _materialize(
        self, workspace, frame, start, rows, batches, coordinates, terminal
    ):
        """Descriptor + frame -> durable unpublished file; Arrow-free storage step."""
        identity = new_identity("chk")
        text, data = chunks.encode_chunk(
            {
                "attempt": self.attempt.identity,
                "batches": batches,
                "binding": self.record,
                "chunk": identity,
                "contract": self.contract,
                "coordinates": coordinates,
                "generation": self.attempt.generation,
                "job": self.publisher.job,
                "kind": self.kind,
                "rows": rows,
                "start": start,
                "stop": start + rows,
                "terminal": terminal,
                "workspace": workspace.identity,
            },
            frame,
        )
        facts = chunks.write_chunk(workspace, identity, data)
        staged = StagedChunk(
            self,
            identity,
            start,
            start + rows,
            batches,
            facts.name,
            facts.size,
            facts.digest,
            text,
            facts.device,
            facts.inode,
            facts.changed,
        )
        self._staged[identity] = staged
        return staged

    def publish(self, staged: StagedChunk, *, operation: str) -> OperationResult:
        """One fenced transaction: chunk reference, new checkpoint and members."""
        workspace = self._use()
        if (
            type(staged) is not StagedChunk
            or staged.session is not self
            or self._staged.get(staged.identity) is not staged
        ):
            raise JobStoreError("CAPTURE_STAGED_FOREIGN")
        publisher, attempt = self.publisher, self.attempt
        request = _identity_request(
            publisher,
            generation=attempt.generation,
            attempt=attempt.identity,
            chunk=staged.identity,
            start=staged.start,
            stop=staged.stop,
            batches=staged.batches,
            file=staged.name,
            bytes=staged.size,
            digest=staged.digest,
            descriptor=staged.descriptor,
        )

        def effect(c):
            revision = _fence(c, publisher, _FENCE)
            _open_capture(c, publisher, attempt)
            ended = c.execute(
                "SELECT observed FROM capture_end WHERE generation = ?",
                (attempt.generation,),
            ).fetchone()
            if ended is not None and staged.stop > ended[0]:
                raise JobStoreError("CAPTURE_EXTENT")
            ranges = c.execute(
                "SELECT start, stop FROM chunk WHERE generation = ?",
                (attempt.generation,),
            ).fetchall()
            # A schema-only [0, 0) chunk stands alone; other extents never overlap.
            if (staged.start == staged.stop and (staged.start or ranges)) or any(
                start == stop or (start < staged.stop and staged.start < stop)
                for start, stop in ranges
            ):
                raise JobStoreError("CAPTURE_OVERLAP")
            if len(ranges) >= MAX_CHUNKS_PER_GENERATION:
                raise JobStoreError("STORE_LIMIT")
            _limit(c, "chunk")
            # The commit boundary rechecks the final object; nothing is read.
            directory = workspace.directory(CHUNKS)
            try:
                chunks.file_identity(directory, staged)
            finally:
                os.close(directory)
            c.execute(
                "INSERT INTO chunk(identity, job, generation, attempt, start, stop,"
                " batches, file, bytes, digest, descriptor, publisher_epoch,"
                " publisher_instance) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    staged.identity,
                    publisher.job,
                    attempt.generation,
                    attempt.identity,
                    staged.start,
                    staged.stop,
                    staged.batches,
                    staged.name,
                    staged.size,
                    staged.digest,
                    staged.descriptor,
                    publisher.epoch,
                    publisher.instance,
                ),
            )
            previous = c.execute(
                "SELECT identity, ordinal FROM checkpoint WHERE generation = ?"
                " ORDER BY ordinal DESC LIMIT 1",
                (attempt.generation,),
            ).fetchone()
            members = [staged.identity]
            ordinal = 1
            if previous is not None:
                ordinal = previous[1] + 1
                members += [
                    r[0]
                    for r in c.execute(
                        "SELECT chunk FROM checkpoint_member WHERE checkpoint = ?",
                        (previous[0],),
                    )
                ]
            extents = ranges + [(staged.start, staged.stop)]
            identity = new_identity("ckp")
            reached = frontier(extents)
            c.execute(
                "INSERT INTO checkpoint(identity, job, generation, ordinal, frontier,"
                " members, rows, publisher_epoch) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    identity,
                    publisher.job,
                    attempt.generation,
                    ordinal,
                    reached,
                    len(members),
                    sum(stop - start for start, stop in extents),
                    publisher.epoch,
                ),
            )
            c.executemany(
                "INSERT INTO checkpoint_member(checkpoint, chunk, generation)"
                " VALUES (?, ?, ?)",
                [(identity, m, attempt.generation) for m in sorted(members)],
            )
            return publisher.job, {
                "checkpoint": identity,
                "chunk": staged.identity,
                "frontier": reached,
                "members": len(members),
                "ordinal": ordinal,
                "revision": revision,
            }

        result = _advance(
            publisher,
            _operate(
                workspace,
                operation,
                "publish_chunk",
                request,
                effect,
                payload=len(staged.descriptor),
            ),
        )
        del self._staged[staged.identity]
        return result

    def end(self, *, operation: str) -> OperationResult:
        """Record the observed extent and the owner's own terminal after it closed."""
        workspace = self._use()
        if self._ended:
            raise JobStoreError("CAPTURE_ENDED")
        if self.owner._closed is not True:
            raise JobStoreError("CAPTURE_OWNER_OPEN")
        source = self._terminal or self._owner_terminal()
        publisher, attempt = self.publisher, self.attempt
        request = _identity_request(
            publisher,
            generation=attempt.generation,
            observed=self._observed,
            source=source,
            staged=len(self._staged),
        )

        def effect(c):
            revision = _fence(c, publisher, _FENCE_CONTROL)
            row = c.execute(
                "SELECT attempt, publisher_epoch, publisher_instance FROM capture"
                " WHERE generation = ? AND job = ?",
                (attempt.generation, publisher.job),
            ).fetchone()
            if row != (attempt.identity, publisher.epoch, publisher.instance):
                raise JobStoreError("CAPTURE_PUBLISHER")
            if c.execute(
                "SELECT 1 FROM capture_end WHERE generation = ?", (attempt.generation,)
            ).fetchone():
                raise JobStoreError("CAPTURE_ENDED")
            c.execute(
                "INSERT INTO capture_end(generation, observed, source, staged,"
                " publisher_epoch) VALUES (?, ?, ?, ?, ?)",
                (
                    attempt.generation,
                    self._observed,
                    source,
                    len(self._staged),
                    publisher.epoch,
                ),
            )
            return publisher.job, {
                "generation": attempt.generation,
                "observed": self._observed,
                "revision": revision,
            }

        result = _advance(
            publisher,
            _operate(
                workspace, operation, "end_capture", request, effect, control=True
            ),
        )
        self._ended = True
        return result


def _open_capture(c, publisher, attempt) -> None:
    row = c.execute(
        "SELECT c.attempt, c.publisher_epoch, c.publisher_instance,"
        " (SELECT count(*) FROM attempt_terminal t WHERE t.attempt = c.attempt)"
        " FROM capture c WHERE c.generation = ? AND c.job = ?",
        (attempt.generation, publisher.job),
    ).fetchone()
    if row is None:
        raise JobStoreError("CAPTURE_UNKNOWN")
    if row[:3] != (attempt.identity, publisher.epoch, publisher.instance):
        raise JobStoreError("CAPTURE_PUBLISHER")
    if row[3]:
        raise JobStoreError("ATTEMPT_TERMINAL")


def begin_capture(
    publisher: Publisher, attempt: AttemptHandle, owner, *, operation: str
) -> CaptureSession:
    """Bind one capture to this publisher, open attempt, fresh binding and owner."""
    from pietto._project.project_execution import (
        compiled_attempt_outcome,
        verify_compiled_owner,
    )

    workspace = publisher.use()
    _capturing(workspace)
    if type(attempt) is not AttemptHandle or attempt.publisher is not publisher:
        raise JobStoreError("ATTEMPT_PUBLISHER")
    verify_compiled_owner(owner)
    request = owner.request
    if (
        request.binding is not attempt.binding
        or request.isolation != attempt.isolation
        or request.route != attempt.route
    ):
        raise JobStoreError("ATTEMPT_OWNER")
    compiled_attempt_outcome(owner)
    outcome = owner.outcome
    if owner._closed or outcome.rows or outcome.batches:
        raise JobStoreError("CAPTURE_OWNER_STATE")
    row = read(
        workspace,
        lambda c: c.execute(
            "SELECT binding, description FROM generation WHERE identity = ? AND job = ?",
            (attempt.generation, publisher.job),
        ).fetchone(),
    )
    if row is None:
        raise JobStoreError("GENERATION_UNKNOWN")
    if _description(attempt.binding, attempt.route) != row[1]:
        raise JobStoreError("GENERATION_DESCRIPTION")
    refined = owner.refined_request
    kind = "ORDINARY" if refined is None else "REFINED"
    scheme = coordinate_scheme(None if refined is None else refined.refinement)
    contract = contract_digest(request.output)
    document = _identity_request(
        publisher,
        generation=attempt.generation,
        attempt=attempt.identity,
        kind=kind,
        contract=contract,
        scheme=scheme,
    )

    def effect(c):
        revision = _fence(c, publisher, _FENCE)
        found = c.execute(
            "SELECT generation, publisher_epoch, publisher_instance,"
            " (SELECT count(*) FROM attempt_terminal WHERE attempt = identity)"
            " FROM attempt WHERE identity = ? AND job = ?",
            (attempt.identity, publisher.job),
        ).fetchone()
        if found is None:
            raise JobStoreError("ATTEMPT_UNKNOWN")
        if found[3]:
            raise JobStoreError("ATTEMPT_TERMINAL")
        if found[:3] != (attempt.generation, publisher.epoch, publisher.instance):
            raise JobStoreError("ATTEMPT_PUBLISHER")
        # One original capture attempt per generation; later attempts cannot append.
        if c.execute(
            "SELECT 1 FROM capture WHERE generation = ?", (attempt.generation,)
        ).fetchone():
            raise JobStoreError("CAPTURE_EXISTS")
        c.execute(
            "INSERT INTO capture(generation, job, attempt, kind, contract, scheme,"
            " publisher_epoch, publisher_instance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                attempt.generation,
                publisher.job,
                attempt.identity,
                kind,
                contract,
                scheme,
                publisher.epoch,
                publisher.instance,
            ),
        )
        return publisher.job, {"capture": attempt.generation, "revision": revision}

    result = _advance(
        publisher, _operate(workspace, operation, "begin_capture", document, effect)
    )
    if result.observation != "COMMITTED_THIS_CALL":
        raise JobStoreError("CAPTURE_REPLAYED")
    return CaptureSession(publisher, attempt, owner, row[0], kind, contract)


@dataclass(frozen=True, slots=True)
class Member:
    chunk: str
    start: int
    stop: int
    batches: int
    file: str
    bytes: int
    digest: str = field(repr=False)
    descriptor: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class CheckpointSnapshot:
    """An immutable RECORDED member snapshot; VERIFIED only after reading files."""

    workspace: str
    job: str
    generation: str
    binding: str
    attempt: str
    kind: str
    contract: str
    scheme: str = field(repr=False)
    checkpoint: str | None
    ordinal: int
    frontier: int
    members: tuple[Member, ...] = field(repr=False)
    committed: tuple[tuple[int, int], ...]
    holes: tuple[tuple[int, int], ...]
    observed_end: int | None
    session_source: str | None
    layers: tuple[tuple[str, Any], ...]
    retention: str | None = None
    integrity: str = "RECORDED"


def _snapshot(c, workspace, job, generation, checkpoint, retention=None):
    capture = c.execute(
        "SELECT c.attempt, c.kind, c.contract, c.scheme, g.binding FROM capture c"
        " JOIN generation g ON g.identity = c.generation AND g.job = c.job"
        " WHERE c.generation = ? AND c.job = ?",
        (generation, job),
    ).fetchone()
    if capture is None:
        raise JobStoreError("CAPTURE_UNKNOWN")
    if checkpoint is None:
        head = c.execute(
            "SELECT identity, ordinal, frontier, members, rows FROM checkpoint"
            " WHERE generation = ? ORDER BY ordinal DESC LIMIT 1",
            (generation,),
        ).fetchone()
    else:
        if not valid_identity(checkpoint, "ckp"):
            raise JobStoreError("CHECKPOINT_UNKNOWN")
        head = c.execute(
            "SELECT identity, ordinal, frontier, members, rows FROM checkpoint"
            " WHERE identity = ? AND generation = ? AND job = ?",
            (checkpoint, generation, job),
        ).fetchone()
        if head is None:
            raise JobStoreError("CHECKPOINT_UNKNOWN")
    members: tuple[Member, ...] = ()
    if head is not None:
        members = tuple(
            Member(*r)
            for r in c.execute(
                "SELECT k.identity, k.start, k.stop, k.batches, k.file, k.bytes,"
                " k.digest, k.descriptor FROM checkpoint_member m JOIN chunk k"
                " ON k.identity = m.chunk AND k.generation = m.generation"
                " WHERE m.checkpoint = ? AND k.job = ? AND k.attempt = ?"
                " ORDER BY k.start, k.stop",
                (head[0], job, capture[0]),
            )
        )
    end = c.execute(
        "SELECT observed, source FROM capture_end WHERE generation = ?", (generation,)
    ).fetchone()
    terminal = c.execute(
        "SELECT kind, outcome FROM attempt_terminal WHERE attempt = ?", (capture[0],)
    ).fetchone()
    ranges = tuple((m.start, m.stop) for m in members)
    reached = frontier(ranges)
    # A cached frontier/count is accepted only if it equals the recomputation.
    if head is not None and (
        len(members) != head[3]
        or reached != head[2]
        or sum(b - a for a, b in ranges) != head[4]
        or any(a[1] > b[0] or a == b for a, b in zip(ranges, ranges[1:]))
        or any(a == b and len(ranges) > 1 for a, b in ranges)
    ):
        raise JobStoreError("CHECKPOINT_MEMBERS")
    outcome = {} if terminal is None else dict(_pairs(terminal[1]))
    layers = (
        ("attempt_terminal", None if terminal is None else terminal[0]),
        *((name, outcome.get(name, "UNKNOWN")) for name in LAYERS),
        ("publication", NOT_IMPLEMENTED),
        ("consumer_ack", NOT_IMPLEMENTED),
    )
    return CheckpointSnapshot(
        workspace.identity,
        job,
        generation,
        capture[4],
        capture[0],
        capture[1],
        capture[2],
        capture[3],
        None if head is None else head[0],
        0 if head is None else head[1],
        reached,
        members,
        ranges,
        holes(ranges, None if end is None else end[0]),
        None if end is None else end[0],
        None if end is None else end[1],
        layers,
        retention,
    )


def checkpoint_snapshot(
    workspace: Workspace, job: str, generation: str, *, checkpoint: str | None = None
) -> CheckpointSnapshot:
    """One read transaction; no protection record and no file is opened."""
    _capturing(workspace)
    if not valid_identity(job, "job") or not valid_identity(generation, "gen"):
        raise JobStoreError("CAPTURE_UNKNOWN")
    return read(
        workspace, lambda c: _snapshot(c, workspace, job, generation, checkpoint)
    )


def _scope(scope) -> str:
    try:
        text = _json(scope)
    except (TypeError, ValueError):
        raise JobStoreError("RETENTION_SCOPE") from None
    if (
        type(scope) is not dict
        or not scope
        or any(type(k) is not str for k in scope)
        or any(type(v) not in (str, int, bool) for v in scope.values())
        or len(text.encode("utf-8")) > MAX_SCOPE_BYTES
    ):
        raise JobStoreError("RETENTION_SCOPE")
    return text


def _retain(c, workspace, publisher, generation, checkpoint, text):
    """Transaction-local retention insert; the caller owns fence and operation."""
    _limit(c, "retention")
    identity = new_identity("ret")
    snapshot = _snapshot(c, workspace, publisher.job, generation, checkpoint)
    if snapshot.checkpoint is None:
        raise JobStoreError("CHECKPOINT_UNKNOWN")
    c.execute(
        "INSERT INTO retention(identity, job, generation, checkpoint, scope,"
        " publisher_epoch, publisher_instance) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            identity,
            publisher.job,
            generation,
            snapshot.checkpoint,
            text,
            publisher.epoch,
            publisher.instance,
        ),
    )
    return identity, snapshot


def retain_checkpoint(
    publisher: Publisher,
    generation: str,
    *,
    scope: dict,
    operation: str,
    checkpoint: str | None = None,
) -> CheckpointSnapshot:
    """Atomically protect one immutable checkpoint and return its member snapshot."""
    workspace = publisher.use()
    _capturing(workspace)
    if not valid_identity(generation, "gen"):
        raise JobStoreError("CAPTURE_UNKNOWN")
    text = _scope(scope)
    request = _identity_request(
        publisher, generation=generation, checkpoint=checkpoint, scope=text
    )
    taken = []

    def effect(c):
        revision = _fence(c, publisher, _FENCE_CONTROL)
        identity, snapshot = _retain(
            c, workspace, publisher, generation, checkpoint, text
        )
        taken.append(snapshot)
        return publisher.job, {
            "checkpoint": snapshot.checkpoint,
            "retention": identity,
            "revision": revision,
        }

    result = _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "retain_checkpoint",
            request,
            effect,
            control=True,
        ),
    )
    if taken:
        snapshot = taken[0]
    else:
        # A replay names an immutable checkpoint; its members cannot have changed.
        snapshot = checkpoint_snapshot(
            workspace, publisher.job, generation, checkpoint=result.get("checkpoint")
        )
    return replace(snapshot, retention=result.get("retention"))


def release_retention(
    publisher: Publisher, retention: str, *, operation: str
) -> OperationResult:
    """A metadata release by the current publisher; no file is deleted."""
    workspace = publisher.use()
    _capturing(workspace)
    if not valid_identity(retention, "ret"):
        raise JobStoreError("RETENTION_UNKNOWN")

    def effect(c):
        revision = _fence(c, publisher, _FENCE_CONTROL)
        if not c.execute(
            "SELECT 1 FROM retention WHERE identity = ? AND job = ?",
            (retention, publisher.job),
        ).fetchone():
            raise JobStoreError("RETENTION_UNKNOWN")
        if c.execute(
            "SELECT 1 FROM retention_release WHERE retention = ?", (retention,)
        ).fetchone():
            raise JobStoreError("RETENTION_RELEASED")
        c.execute(
            "INSERT INTO retention_release(retention, publisher_epoch,"
            " publisher_instance) VALUES (?, ?, ?)",
            (retention, publisher.epoch, publisher.instance),
        )
        return publisher.job, {"retention": retention, "revision": revision}

    return _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "release_retention",
            _identity_request(publisher, retention=retention),
            effect,
            control=True,
        ),
    )


def protected_chunks(workspace: Workspace, job: str) -> frozenset[str]:
    """Latest checkpoint members per generation plus unreleased retained snapshots."""
    _capturing(workspace)
    return frozenset(
        r[0]
        for r in read(
            workspace,
            lambda c: c.execute(
                "SELECT m.chunk FROM checkpoint_member m JOIN checkpoint k"
                " ON k.identity = m.checkpoint WHERE k.job = ? AND (k.ordinal ="
                " (SELECT max(ordinal) FROM checkpoint WHERE generation = k.generation)"
                " OR k.identity IN (SELECT r.checkpoint FROM retention r WHERE"
                " r.job = k.job AND r.identity NOT IN"
                " (SELECT retention FROM retention_release)))",
                (job,),
            ).fetchall(),
        )
    )


def classify_files(workspace: Workspace) -> dict:
    """Referenced, orphan, staging and foreign names; nothing is adopted or removed."""
    _capturing(workspace)
    referenced = {
        r[0]
        for r in read(
            workspace, lambda c: c.execute("SELECT file FROM chunk").fetchall()
        )
    }
    finals = chunks.list_names(workspace, CHUNKS)
    staging = chunks.list_names(workspace, STAGING)
    return {
        "referenced": tuple(n for n, k in finals if n in referenced and k == "file"),
        "missing": tuple(sorted(referenced - {n for n, _k in finals})),
        "orphans": tuple(n for n, k in finals if n not in referenced and k == "file"),
        "staging": tuple(n for n, k in staging if k == "file"),
        "foreign": tuple(n for n, k in finals + staging if k != "file"),
    }


@dataclass(frozen=True, slots=True, eq=False)
class StoredOutput:
    """Freshly reconstructed reader requirements; never a former live producer."""

    job: str
    generation: str
    contract: str
    scheme: str = field(repr=False)
    binding: Any = field(repr=False)


def stored_binding(
    workspace: Workspace,
    job: str,
    generation: str,
    *,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: tuple,
):
    """Fresh caller trust -> S10 template and stored-vector binding; Arrow-free."""
    from pietto._project.project_job_store import bind_record, load_job

    _capturing(workspace)
    template = load_job(
        workspace,
        job,
        expected_pin=expected_pin,
        accepted_producer=accepted_producer,
        accepted_compatibility=accepted_compatibility,
    )
    if not valid_identity(generation, "gen"):
        raise JobStoreError("GENERATION_UNKNOWN")
    row = read(
        workspace,
        lambda c: c.execute(
            "SELECT binding, route, description FROM generation"
            " WHERE identity = ? AND job = ?",
            (generation, job),
        ).fetchone(),
    )
    if row is None:
        raise JobStoreError("GENERATION_UNKNOWN")
    binding = bind_record(workspace, job, template, row[0])
    if _description(binding, row[1]) != row[2]:
        raise JobStoreError("GENERATION_DESCRIPTION")
    return template, binding, row[1]


def arrow_output(job, generation, output, refinement, route) -> StoredOutput:
    """The stored-chunk producer of a freshly rederived compiled output."""
    from pietto._project.project_arrow_result import bind_arrow
    from pietto._project.project_execution_reader import bind_stored_output

    return StoredOutput(
        job,
        generation,
        contract_digest(output),
        coordinate_scheme(refinement),
        bind_arrow(bind_stored_output(output, route)),
    )


def stored_output(
    workspace: Workspace,
    job: str,
    generation: str,
    *,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: tuple,
) -> StoredOutput:
    """Fresh caller trust -> S10 template/binding/output -> stored-chunk producer."""
    from pietto._project.project_execution import compiled_output

    _template, binding, route = stored_binding(
        workspace,
        job,
        generation,
        expected_pin=expected_pin,
        accepted_producer=accepted_producer,
        accepted_compatibility=accepted_compatibility,
    )
    output, refinement, _program = compiled_output(binding)
    return arrow_output(job, generation, output, refinement, route)


@dataclass(frozen=True, slots=True, eq=False)
class CheckedChunk:
    """A fully decoded, value-checked stored chunk; not an R1 delivery."""

    chunk: str
    start: int
    stop: int
    terminal: str | None
    table: Any = field(repr=False)
    coordinates: tuple | None = field(repr=False)


class SnapshotReader:
    """Holds a member snapshot and its own read-only directory descriptor only."""

    __slots__ = ("snapshot", "output", "_directory", "_pid", "_closed")

    def __init__(self, workspace: Workspace, snapshot, output):
        _capturing(workspace)
        if (
            type(snapshot) is not CheckpointSnapshot
            or type(output) is not StoredOutput
            or snapshot.workspace != workspace.identity
            or (snapshot.job, snapshot.generation) != (output.job, output.generation)
            or snapshot.contract != output.contract
            or snapshot.scheme != output.scheme
        ):
            raise JobStoreError("READER_SNAPSHOT")
        self.snapshot, self.output = snapshot, output
        self._directory = workspace.directory(CHUNKS)
        self._pid = os.getpid()
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False

    def close(self) -> None:
        if not self._closed and self._pid == os.getpid():
            self._closed = True
            os.close(self._directory)

    def read(self, index: int) -> CheckedChunk:
        """Bounded file, exact descriptor correspondence, full IPC value checks."""
        from pietto._project.project_arrow_result import _arrow
        from pietto._project.project_result_ipc import (
            IPCLimits,
            open_ipc,
            verify_ipc_completion,
        )

        if self._pid != os.getpid() or self._closed:
            raise JobStoreError("READER_CLOSED")
        snapshot, member = self.snapshot, self.snapshot.members[index]
        data = chunks.read_chunk_file(
            self._directory, member.file, member.bytes, member.digest
        )
        text, descriptor, frame = chunks.decode_chunk(data)
        rows = member.stop - member.start
        # Every descriptor field that names this member must equal the snapshot.
        if text != member.descriptor or descriptor != {
            **descriptor,
            "attempt": snapshot.attempt,
            "batches": member.batches,
            "binding": snapshot.binding,
            "chunk": member.chunk,
            "contract": snapshot.contract,
            "generation": snapshot.generation,
            "job": snapshot.job,
            "kind": snapshot.kind,
            "rows": rows,
            "start": member.start,
            "stop": member.stop,
            "workspace": snapshot.workspace,
        }:
            raise JobStoreError("CHUNK_DESCRIPTOR")
        terminal = descriptor["terminal"]
        if (terminal is not None or member.batches == 0) and (
            terminal != "EOF" or rows or member.batches or len(snapshot.members) != 1
        ):
            raise JobStoreError("CHUNK_DESCRIPTOR")
        coordinates = None
        if snapshot.kind == "REFINED":
            wire = descriptor["coordinates"]
            if type(wire) is not list or len(wire) != rows:
                raise JobStoreError("CHUNK_COORDINATE")
            width = len(json.loads(snapshot.scheme)["coordinates"])
            if any(type(key) is not list or len(key) != width for key in wire):
                raise JobStoreError("CHUNK_COORDINATE")
            coordinates = tuple(
                tuple(chunks.read_coordinate(v) for v in key) for key in wire
            )
        elif descriptor["coordinates"] is not None:
            raise JobStoreError("CHUNK_COORDINATE")
        session = open_ipc(
            self.output.binding,
            frame,
            expected_rows=rows,
            ipc_limits=IPCLimits(chunks.MAX_FRAME_BYTES),
        )
        with session:
            table = _arrow().RecordBatchReader.from_stream(session).read_all()
        verify_ipc_completion(session)
        if table.num_rows != rows:
            raise JobStoreError("CHUNK_DESCRIPTOR")
        return CheckedChunk(
            member.chunk, member.start, member.stop, terminal, table, coordinates
        )

    def verify(self) -> dict:
        """Read and check every member one at a time; only then VERIFIED (not cached)."""
        rows = 0
        for index in range(len(self.snapshot.members)):
            checked = self.read(index)
            rows += checked.stop - checked.start
        return {
            "integrity": "VERIFIED",
            "checkpoint": self.snapshot.checkpoint,
            "members": len(self.snapshot.members),
            "rows": rows,
            "frontier": self.snapshot.frontier,
        }
