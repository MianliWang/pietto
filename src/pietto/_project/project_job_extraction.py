"""S14 R2: same-version extraction recovery over an explicit v4 job workspace.

Before its first capture, an R2 generation binds the exact S10 query/binding, S06
choice/coordinates and ordered source-use vector (the specification) and the real
owner's stable source/environment observations (the description). Recovery is an
explicit process-local caller acceptance plus a NEW attempt whose real owner
requalifies the complete vector and guards on a new connection/transaction and
enumerates the complete refined query again from position 0. Its checked stream
is compared with the frozen committed membership; missing ranges and the unseen
suffix become candidate files, published only after every saved occurrence
matched (the barrier). Matching saved rows proves no repeatability or provider
premise; complete coverage is not a transaction ACK, delivery, sink effect or
generation publication. Nothing here retries, schedules, adopts old candidate
files or collects garbage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import time
from typing import Any
import weakref

from pietto._project import project_job_chunks as chunks
from pietto._project.project_job_capture import (
    MAX_STAGED,
    CaptureSession,
    SnapshotReader,
    StagedChunk,
    _begin,
    _snapshot,
    arrow_output,
    contract_digest,
    coordinate_scheme,
    known_extent,
    stored_binding,
)
from pietto._project.project_job_store import (
    _FENCE,
    _FENCE_CONTROL,
    MAX_DESCRIPTION_BYTES,
    AttemptHandle,
    OperationResult,
    Publisher,
    _advance,
    _fence,
    _identity_request,
    _json,
    _operate,
    _vector,
)
from pietto._project.project_job_workspace import (
    JobStoreError,
    Workspace,
    read,
    supports,
    valid_identity,
)

__all__: tuple[str, ...] = ()

SPECIFICATION = "pietto.extraction-spec.v1"
MAX_CANDIDATES = 64
MAX_ACCEPTANCE_SECONDS = 86400
MAX_PURPOSE_BYTES = 256
# The trusted host clocks. Tests inject explicit boundaries; callers cannot.
_wall = time.time
_monotonic = time.monotonic
_ACCEPTED: weakref.WeakSet = weakref.WeakSet()


def _extracting(workspace: Workspace) -> None:
    if not supports(workspace, "extraction-resume"):
        raise JobStoreError("WORKSPACE_EXTRACTION_FORMAT")


def specification(refinement, output, route: str, isolation: str) -> str:
    """The immutable extraction specification of a refined compiled output."""
    return _json(
        {
            "chunk": chunks.FORMAT,
            "contract": contract_digest(output),
            "coordinates": chunks.COORDINATES,
            "isolation": isolation,
            "kind": "REFINED",
            "route": route,
            "scheme": coordinate_scheme(refinement),
            "sources": [
                [
                    r.source.namespace,
                    r.source.name,
                    r.provider,
                    r.version,
                    r.revision,
                    r.registry_namespace,
                    r.registry_name,
                    r.definition,
                    list(r.token_columns),
                    r.role,
                    r.provider_guarantee,
                ]
                for r in refinement.sources
            ],
            "version": SPECIFICATION,
        }
    )


def describe(owner) -> str:
    """Canonical bounded text of an open owner's stable source description."""
    from pietto._project.project_execution import compiled_source_description

    value = compiled_source_description(owner)
    try:
        text = _json(value)
    except (TypeError, ValueError):
        raise JobStoreError("EXTRACTION_DESCRIPTION") from None
    if len(text.encode("utf-8")) > MAX_DESCRIPTION_BYTES:
        raise JobStoreError("EXTRACTION_DESCRIPTION")
    return text


def _fresh(owner) -> None:
    """A newly opened refined owner: enumeration at position 0, nothing delivered."""
    enumeration = getattr(owner, "enumeration", None)
    if (
        getattr(owner, "refined_request", None) is None
        or enumeration is None
        or enumeration.progress != (0, 0, False, False)
        or owner._payloads is not None
        or owner._closed
    ):
        raise JobStoreError("EXTRACTION_OWNER_STATE")


def begin_extraction(
    publisher: Publisher, attempt: AttemptHandle, owner, *, operation: str
) -> CaptureSession:
    """Register this generation R2-capable WITH its first capture, before progress.

    The opened real owner has already qualified the complete source vector; its
    stable description is persisted under the publisher fence. Chunks then flow
    through the unchanged S12 capture session of this original attempt.
    """
    workspace = publisher.use()
    _extracting(workspace)
    _fresh(owner)
    request = owner.request
    text = specification(
        owner.refined_request.refinement,
        request.output,
        request.route,
        request.isolation,
    )
    return _begin(publisher, attempt, owner, operation, (text, describe(owner)))


@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class RecoveryAcceptance:
    """A process-local caller acceptance to recover one R2 extraction; never stored.

    It is not source authority: the new attempt's own owner qualification,
    managed premise and guards are. No stored row, receipt or copy mints one.
    """

    workspace: str
    job: str
    generation: str
    checkpoint: str | None
    purpose: str
    route: str
    isolation: str
    frontier: int
    reach: int
    rows: int
    known: int | None
    seconds: int
    accepted_at: float
    binding: Any = field(repr=False)
    _snapshot: Any = field(repr=False)
    _output: Any = field(repr=False)
    _refinement: Any = field(repr=False)
    _specification: str = field(repr=False)
    _description: str = field(repr=False)
    _deadline: float = field(repr=False)
    _pid: int = field(repr=False)

    def __reduce_ex__(self, protocol):
        raise JobStoreError("ACCEPTANCE_COPY")


def _accepted(acceptance) -> RecoveryAcceptance:
    """Issued here, by this process, and within both validity bounds now."""
    if type(acceptance) is not RecoveryAcceptance or acceptance not in _ACCEPTED:
        raise JobStoreError("ACCEPTANCE_UNKNOWN")
    if acceptance._pid != os.getpid():
        raise JobStoreError("ACCEPTANCE_FOREIGN_PROCESS")
    if not (
        _monotonic() < acceptance._deadline
        and _wall() < acceptance.accepted_at + acceptance.seconds
    ):
        raise JobStoreError("ACCEPTANCE_EXPIRED")
    return acceptance


def _verify_saved(workspace, snapshot, output, refinement, route) -> None:
    """Bounded bytes, descriptor/attempt and full IPC value checks of every member."""
    stored = arrow_output(snapshot.job, snapshot.generation, output, refinement, route)
    with SnapshotReader(workspace, snapshot, stored) as reader:
        reader.verify()


def accept_recovery(
    workspace: Workspace,
    job: str,
    generation: str,
    *,
    checkpoint: str | None,
    purpose: str,
    values,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: tuple,
    seconds: int,
) -> RecoveryAcceptance:
    """Fresh trust, exact values/specification, current checkpoint, verified bytes.

    `checkpoint` must name the generation's current latest checkpoint (None only
    when none exists). Every saved member is checked before any source opens.
    """
    from pietto._project.project_execution import compiled_output
    from pietto._project.project_execution_template import bind_values

    _extracting(workspace)
    if checkpoint is not None and not valid_identity(checkpoint, "ckp"):
        raise JobStoreError("CHECKPOINT_UNKNOWN")
    if (
        type(purpose) is not str
        or not purpose
        or not purpose.isprintable()
        or len(purpose.encode("utf-8")) > MAX_PURPOSE_BYTES
    ):
        raise JobStoreError("ACCEPTANCE_PURPOSE")
    if type(seconds) is not int or not 1 <= seconds <= MAX_ACCEPTANCE_SECONDS:
        raise JobStoreError("ACCEPTANCE_BOUND")
    accepted_at, deadline = _wall(), _monotonic() + seconds
    template, binding, route = stored_binding(
        workspace,
        job,
        generation,
        expected_pin=expected_pin,
        accepted_producer=accepted_producer,
        accepted_compatibility=accepted_compatibility,
    )
    try:
        stated = bind_values(template, tuple(zip(template.slots, values, strict=True)))
    except (ValueError, TypeError):
        raise JobStoreError("BINDING_VECTOR") from None
    if _vector(stated) != _vector(binding):
        raise JobStoreError("BINDING_VECTOR")
    output, refinement, _program = compiled_output(binding)
    if refinement is None:
        raise JobStoreError("EXTRACTION_UNKNOWN")

    def body(c):
        row = c.execute(
            "SELECT x.specification, x.qualification, g.isolation FROM extraction x"
            " JOIN generation g ON g.identity = x.generation AND g.job = x.job"
            " WHERE x.generation = ? AND x.job = ?",
            (generation, job),
        ).fetchone()
        if row is None:
            raise JobStoreError("EXTRACTION_UNKNOWN")
        snapshot = _snapshot(c, workspace, job, generation, None)
        if snapshot.checkpoint != checkpoint:
            raise JobStoreError("CONTINUATION_PREDECESSOR")
        return row, snapshot, known_extent(c, workspace, generation)

    (text, description, isolation), snapshot, known = read(workspace, body)
    if specification(refinement, output, route, isolation) != text:
        raise JobStoreError("EXTRACTION_SPECIFICATION")
    _verify_saved(workspace, snapshot, output, refinement, route)
    if any(m.start == m.stop for m in snapshot.members):
        # A schema-only member is a recorded empty complete result.
        if known not in (None, 0):
            raise JobStoreError("CAPTURE_EXTENT")
        known = 0
    acceptance = RecoveryAcceptance(
        workspace.identity,
        job,
        generation,
        checkpoint,
        purpose,
        route,
        isolation,
        snapshot.frontier,
        max((m.stop for m in snapshot.members), default=0),
        sum(m.stop - m.start for m in snapshot.members),
        known,
        seconds,
        accepted_at,
        binding,
        snapshot,
        output,
        refinement,
        text,
        description,
        deadline,
        os.getpid(),
    )
    _ACCEPTED.add(acceptance)
    return _accepted(acceptance)


def segments(members, start: int, stop: int) -> tuple[tuple[str, int, int, Any], ...]:
    """Split [start, stop) by frozen sorted disjoint member extents, in order:
    ("old", a, b, member index) inside a member, ("new", a, b, None) elsewhere."""
    result: list[tuple[str, int, int, Any]] = []
    position = start
    for index, member in enumerate(members):
        if position >= stop or member.start >= stop:
            break
        if member.stop <= position or member.start == member.stop:
            continue
        if member.start > position:
            result.append(("new", position, member.start, None))
            position = member.start
        end = min(member.stop, stop)
        result.append(("old", position, end, index))
        position = end
    if position < stop:
        result.append(("new", position, stop, None))
    return tuple(result)


def begin_continuation(
    publisher: Publisher,
    acceptance: RecoveryAcceptance,
    attempt: AttemptHandle,
    owner,
    *,
    operation: str,
) -> ContinuationSession:
    """Freeze the accepted checkpoint for this new attempt after fresh qualification.

    The new owner's own stable description must equal the one persisted with
    the first capture; the stored text never authorizes anything by itself.
    """
    from pietto._project.project_execution import verify_compiled_owner

    workspace = publisher.use()
    _extracting(workspace)
    acceptance = _accepted(acceptance)
    if (acceptance.workspace, acceptance.job) != (workspace.identity, publisher.job):
        raise JobStoreError("ACCEPTANCE_SUBJECT")
    if type(attempt) is not AttemptHandle or attempt.publisher is not publisher:
        raise JobStoreError("ATTEMPT_PUBLISHER")
    verify_compiled_owner(owner)
    request = owner.request
    if (
        attempt.generation != acceptance.generation
        or attempt.binding is not acceptance.binding
        or request.binding is not attempt.binding
        or (request.route, request.isolation)
        != (acceptance.route, acceptance.isolation)
        or (attempt.route, attempt.isolation)
        != (acceptance.route, acceptance.isolation)
    ):
        raise JobStoreError("ATTEMPT_OWNER")
    _fresh(owner)
    if (
        specification(
            owner.refined_request.refinement,
            request.output,
            request.route,
            request.isolation,
        )
        != acceptance._specification
    ):
        raise JobStoreError("EXTRACTION_SPECIFICATION")
    description = describe(owner)
    if description != acceptance._description:
        raise JobStoreError("EXTRACTION_QUALIFICATION_CHANGED")
    snapshot = acceptance._snapshot
    document = _identity_request(
        publisher,
        generation=acceptance.generation,
        attempt=attempt.identity,
        predecessor=acceptance.checkpoint,
        frontier=acceptance.frontier,
        reach=acceptance.reach,
        members=len(snapshot.members),
        rows=acceptance.rows,
        qualification=description,
    )

    def effect(c):
        revision = _fence(c, publisher, _FENCE)
        _accepted(acceptance)
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
        row = c.execute(
            "SELECT attempt, qualification FROM extraction WHERE generation = ?"
            " AND job = ?",
            (attempt.generation, publisher.job),
        ).fetchone()
        if row is None:
            raise JobStoreError("EXTRACTION_UNKNOWN")
        if row[0] == attempt.identity:
            raise JobStoreError("CONTINUATION_ATTEMPT")
        if row[1] != description:
            raise JobStoreError("EXTRACTION_QUALIFICATION_CHANGED")
        head = c.execute(
            "SELECT identity FROM checkpoint WHERE generation = ?"
            " ORDER BY ordinal DESC LIMIT 1",
            (attempt.generation,),
        ).fetchone()
        if (None if head is None else head[0]) != acceptance.checkpoint:
            raise JobStoreError("CONTINUATION_PREDECESSOR")
        if c.execute(
            "SELECT 1 FROM continuation WHERE attempt = ?", (attempt.identity,)
        ).fetchone():
            raise JobStoreError("CONTINUATION_EXISTS")
        c.execute(
            "INSERT INTO continuation(attempt, job, generation, predecessor, frontier,"
            " reach, members, rows, publisher_epoch, publisher_instance)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                attempt.identity,
                publisher.job,
                attempt.generation,
                acceptance.checkpoint,
                acceptance.frontier,
                acceptance.reach,
                len(snapshot.members),
                acceptance.rows,
                publisher.epoch,
                publisher.instance,
            ),
        )
        return publisher.job, {"continuation": attempt.identity, "revision": revision}

    result = _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "begin_continuation",
            document,
            effect,
            payload=len(description),
        ),
    )
    if result.observation != "COMMITTED_THIS_CALL":
        raise JobStoreError("CONTINUATION_REPLAYED")
    return ContinuationSession(publisher, attempt, owner, acceptance)


class ContinuationSession(CaptureSession):
    """One process-local extraction attempt reconciling one frozen checkpoint."""

    __slots__ = (
        "acceptance",
        "snapshot",
        "materialized",
        "_reader",
        "_held",
        "_matched",
        "_schema",
        "_reconciled",
    )

    def __init__(self, publisher, attempt, owner, acceptance):
        snapshot = acceptance._snapshot
        super().__init__(
            publisher, attempt, owner, snapshot.binding, "REFINED", snapshot.contract
        )
        self.acceptance, self.snapshot = acceptance, snapshot
        # Every new extent this attempt materialized (candidate or not), in order.
        self.materialized: list[tuple[int, int]] = []
        self._reader: SnapshotReader | None = None
        self._held: tuple[int, Any] | None = None
        self._matched = 0
        # A saved schema-only member is matched only by a fresh empty result.
        self._schema = any(m.start == m.stop for m in snapshot.members)
        self._reconciled = False

    def __repr__(self) -> str:
        return f"ContinuationSession(attempt={self.attempt.identity!r})"

    @property
    def matched(self) -> int:
        """Saved occurrences compared equal so far (re-enumerated, not new)."""
        return self._matched

    @property
    def ready(self) -> bool:
        """The barrier: every saved occurrence matched and the stream reached H."""
        a = self.acceptance
        return (
            not self._failed
            and not self._schema
            and self._observed >= a.reach
            and self._matched == a.rows
        )

    @property
    def reconciled(self) -> bool:
        return self._reconciled

    def _control(self) -> None:
        _accepted(self.acceptance)
        if self.owner._cancel.is_set():
            raise JobStoreError("CONTINUATION_CANCELED")

    def _chunk(self, index):
        """One held saved member at a time, read with every S12 reader check."""
        if self._held is None or self._held[0] != index:
            self._held = None
            if self._reader is None:
                a = self.acceptance
                output = arrow_output(
                    a.job, a.generation, a._output, a._refinement, a.route
                )
                self._reader = SnapshotReader(
                    self.publisher.use(), self.snapshot, output
                )
            self._held = (index, self._reader.read(index))
        return self._held[1]

    def stage(self) -> tuple[StagedChunk, ...] | None:  # type: ignore[override]
        """Consume one checked page: compare saved occurrences, stage new ones.

        Returns the new (candidate) files of this page, possibly none, or None
        at the owner's terminal. Before the barrier nothing staged is progress.
        """
        from pietto._project.project_arrow_interop import ManagedBatch

        workspace = self._use()
        if self._ended:
            raise JobStoreError("CAPTURE_ENDED")
        if self._terminal is not None:
            return None
        if self._failed:
            raise JobStoreError("CAPTURE_FAILED")
        self._control()
        if self.ready and not self._reconciled:
            raise JobStoreError("RECONCILIATION_PENDING")
        if len(self._staged) >= (MAX_STAGED if self._reconciled else MAX_CANDIDATES):
            raise JobStoreError(
                "CAPTURE_STAGED_LIMIT"
                if self._reconciled
                else "RECONCILIATION_CANDIDATE_LIMIT"
            )
        owner = self.owner
        payloads = owner._payloads
        current = (0, 0) if payloads is None else (payloads.rows, payloads.batches)
        if current != (self._observed, self._batches):
            raise JobStoreError("CAPTURE_LINEAGE")
        try:
            batch = next(owner)
        except StopIteration:
            self._terminal = self._owner_terminal()
            return self._close_stream(workspace)
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
            wires = self._coordinates(rows)
            self._binding = payloads.binding
            return self._step(workspace, array, rows, wires)
        finally:
            batch.close()

    def _step(self, workspace, array, rows, wires):
        start = self._observed
        self._observed += rows
        self._batches += 1
        staged = []
        try:
            known = self.acceptance.known
            if known is not None and self._observed > known:
                raise JobStoreError("RECONCILIATION_EXTENT")
            for kind, a, b, index in segments(
                self.snapshot.members, start, start + rows
            ):
                if kind == "old":
                    self._compare(
                        index,
                        a,
                        b,
                        array.slice(a - start, b - a),
                        wires[a - start : b - start],
                    )
                    self._matched += b - a
                else:
                    staged.append(
                        self._piece(
                            workspace,
                            array.slice(a - start, b - a),
                            a,
                            b - a,
                            wires[a - start : b - start],
                            None,
                        )
                    )
            return tuple(staged)
        except BaseException:
            self._failed = True
            raise

    def _compare(self, index, a, b, fresh, wires) -> None:
        """Exact occurrence correspondence at every saved position of [a, b)."""
        from pietto._project.project_refinement_enumeration import atom

        member = self.snapshot.members[index]
        checked = self._chunk(index)
        offset, rows = a - member.start, b - a
        saved = checked.table.slice(offset, rows)
        if (
            not saved.schema.equals(fresh.schema, check_metadata=True)
            or checked.coordinates is None
            or [
                [chunks.coordinate_wire(v) for v in key]
                for key in checked.coordinates[offset : offset + rows]
            ]
            != wires
            or any(
                [atom(v) for v in saved.column(i).to_pylist()]
                != [atom(v) for v in fresh.column(i).to_pylist()]
                for i in range(fresh.num_columns)
            )
        ):
            raise JobStoreError("RECONCILIATION_MISMATCH")

    def _piece(self, workspace, array, start, rows, coordinates, terminal):
        staged = self._materialize(
            workspace,
            self._encode(array, rows),
            start,
            rows,
            0 if array is None else 1,
            coordinates,
            terminal,
        )
        self.materialized.append((start, start + rows))
        return staged

    def _close_stream(self, workspace) -> tuple[StagedChunk, ...] | None:
        """The owner's terminal: a normal end must cover H and any known extent."""
        if self._terminal != "EOF":
            return None
        a, position = self.acceptance, self._observed
        try:
            if position < a.reach:
                raise JobStoreError("RECONCILIATION_PREMATURE_END")
            if a.known is not None and position != a.known:
                raise JobStoreError("RECONCILIATION_EXTENT")
            if position:
                return ()
            payloads = self.owner._payloads
            if payloads is None:
                raise JobStoreError("CAPTURE_SCHEMA_UNAVAILABLE")
            self._binding = payloads.binding
            if not self._schema:
                # An empty result keeps its exact schema in one [0, 0) member.
                return (self._piece(workspace, None, 0, 0, [], "EOF"),)
            if not self._chunk(0).table.schema.equals(
                self._binding.schema, check_metadata=True
            ):
                raise JobStoreError("RECONCILIATION_MISMATCH")
            self._schema = False
            return ()
        except BaseException:
            self._failed = True
            raise

    def reconcile(self, *, operation: str) -> OperationResult:
        """Record the barrier; only after it may this attempt publish anything."""
        workspace = self._use()
        self._control()
        if self._reconciled:
            raise JobStoreError("RECONCILIATION_RECORDED")
        if not self.ready or self.owner._primary is not None:
            raise JobStoreError("RECONCILIATION_INCOMPLETE")
        publisher, attempt, acceptance = self.publisher, self.attempt, self.acceptance
        request = _identity_request(
            publisher,
            generation=attempt.generation,
            attempt=attempt.identity,
            predecessor=acceptance.checkpoint,
            position=self._observed,
            matched=self._matched,
        )

        def effect(c):
            revision = _fence(c, publisher, _FENCE)
            _accepted(acceptance)
            row = c.execute(
                "SELECT predecessor, publisher_epoch, publisher_instance,"
                " (SELECT count(*) FROM attempt_terminal t WHERE t.attempt = ?1),"
                " (SELECT count(*) FROM reconciliation r WHERE r.attempt = ?1)"
                " FROM continuation WHERE attempt = ?1 AND generation = ?2 AND job = ?3",
                (attempt.identity, attempt.generation, publisher.job),
            ).fetchone()
            if row is None or row[1:3] != (publisher.epoch, publisher.instance):
                raise JobStoreError("CAPTURE_PUBLISHER")
            if row[3]:
                raise JobStoreError("ATTEMPT_TERMINAL")
            if row[4]:
                raise JobStoreError("RECONCILIATION_RECORDED")
            head = c.execute(
                "SELECT identity FROM checkpoint WHERE generation = ?"
                " ORDER BY ordinal DESC LIMIT 1",
                (attempt.generation,),
            ).fetchone()
            if (None if head is None else head[0]) != row[0]:
                raise JobStoreError("CONTINUATION_PREDECESSOR")
            c.execute(
                "INSERT INTO reconciliation(attempt, position, matched,"
                " publisher_epoch) VALUES (?, ?, ?, ?)",
                (attempt.identity, self._observed, self._matched, publisher.epoch),
            )
            return publisher.job, {
                "position": self._observed,
                "reconciliation": attempt.identity,
                "revision": revision,
            }

        result = _advance(
            publisher,
            _operate(workspace, operation, "reconcile_extraction", request, effect),
        )
        self._reconciled = True
        return result

    def publish(self, staged: StagedChunk, *, operation: str) -> OperationResult:
        """The S12 fenced publication, after the barrier and a live acceptance."""
        self._control()
        if not self._reconciled:
            raise JobStoreError("RECONCILIATION_REQUIRED")
        return super().publish(staged, operation=operation)

    def end(self, *, operation: str) -> OperationResult:
        """Record this attempt's own end; a normal end needs gap-free coverage."""
        workspace = self._use()
        if self._ended:
            raise JobStoreError("CAPTURE_ENDED")
        if self.owner._closed is not True:
            raise JobStoreError("CAPTURE_OWNER_OPEN")
        source = self._terminal or self._owner_terminal()
        publisher, attempt, observed = self.publisher, self.attempt, self._observed
        request = _identity_request(
            publisher,
            generation=attempt.generation,
            attempt=attempt.identity,
            observed=observed,
            source=source,
            staged=len(self._staged),
        )

        def effect(c):
            revision = _fence(c, publisher, _FENCE_CONTROL)
            row = c.execute(
                "SELECT publisher_epoch, publisher_instance,"
                " (SELECT count(*) FROM reconciliation r WHERE r.attempt = ?1),"
                " (SELECT count(*) FROM continuation_end e WHERE e.attempt = ?1)"
                " FROM continuation WHERE attempt = ?1 AND generation = ?2 AND job = ?3",
                (attempt.identity, attempt.generation, publisher.job),
            ).fetchone()
            if row is None or row[:2] != (publisher.epoch, publisher.instance):
                raise JobStoreError("CAPTURE_PUBLISHER")
            if row[3]:
                raise JobStoreError("CAPTURE_ENDED")
            checkpoint = None
            if source == "EOF":
                if not row[2]:
                    raise JobStoreError("RECONCILIATION_INCOMPLETE")
                head = c.execute(
                    "SELECT identity, frontier, rows FROM checkpoint"
                    " WHERE generation = ? ORDER BY ordinal DESC LIMIT 1",
                    (attempt.generation,),
                ).fetchone()
                # frontier == rows == observed: one gap-free member set [0, N).
                if head is None or head[1:] != (observed, observed):
                    raise JobStoreError("CONTINUATION_COVERAGE")
                if known_extent(c, workspace, attempt.generation) not in (
                    None,
                    observed,
                ):
                    raise JobStoreError("CAPTURE_EXTENT")
                checkpoint = head[0]
            c.execute(
                "INSERT INTO continuation_end(attempt, generation, observed, source,"
                " staged, checkpoint, publisher_epoch) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    attempt.identity,
                    attempt.generation,
                    observed,
                    source,
                    len(self._staged),
                    checkpoint,
                    publisher.epoch,
                ),
            )
            return publisher.job, {
                "checkpoint": checkpoint,
                "observed": observed,
                "revision": revision,
            }

        result = _advance(
            publisher,
            _operate(
                workspace, operation, "end_continuation", request, effect, control=True
            ),
        )
        self._ended = True
        return result

    def close(self) -> None:
        """Release the held saved member and reader; never progress or an end."""
        if self._pid == os.getpid():
            self._held = None
            if self._reader is not None:
                self._reader.close()
                self._reader = None


@dataclass(frozen=True, slots=True)
class ExtractionState:
    """A read-only observation of one R2 generation's extraction history.

    Complete coverage is row coverage only: not a transaction ACK, delivery,
    consumer or sink acknowledgement, or generation publication.
    """

    job: str
    generation: str
    attempt: str
    checkpoint: str | None
    frontier: int
    committed: tuple[tuple[int, int], ...]
    holes: tuple[tuple[int, int], ...]
    known: int | None
    complete_coverage: bool
    continuations: tuple[tuple, ...]


def extraction_state(
    workspace: Workspace, job: str, generation: str
) -> ExtractionState:
    """Original attempt, every continuation (frozen bounds, barrier, end) and
    the latest checkpoint's recomputed coverage, in one read transaction."""
    _extracting(workspace)
    if not valid_identity(job, "job") or not valid_identity(generation, "gen"):
        raise JobStoreError("EXTRACTION_UNKNOWN")

    def body(c):
        row = c.execute(
            "SELECT attempt FROM extraction WHERE generation = ? AND job = ?",
            (generation, job),
        ).fetchone()
        if row is None:
            raise JobStoreError("EXTRACTION_UNKNOWN")
        continuations = c.execute(
            "SELECT n.attempt, n.predecessor, n.frontier, n.reach, n.members, n.rows,"
            " r.position, r.matched, e.observed, e.source, e.checkpoint,"
            " t.kind FROM continuation n JOIN attempt a ON a.identity = n.attempt"
            " LEFT JOIN reconciliation r ON r.attempt = n.attempt"
            " LEFT JOIN continuation_end e ON e.attempt = n.attempt"
            " LEFT JOIN attempt_terminal t ON t.attempt = n.attempt"
            " WHERE n.generation = ? AND n.job = ? ORDER BY a.ordinal",
            (generation, job),
        ).fetchall()
        snapshot = _snapshot(c, workspace, job, generation, None)
        return (
            row[0],
            tuple(continuations),
            snapshot,
            known_extent(c, workspace, generation),
        )

    attempt, continuations, snapshot, known = read(workspace, body)
    complete = (
        known is not None
        and snapshot.frontier == known
        and not snapshot.holes
        and bool(snapshot.members)
        and sum(b - a for a, b in snapshot.committed) == known
    )
    return ExtractionState(
        job,
        generation,
        attempt,
        snapshot.checkpoint,
        snapshot.frontier,
        snapshot.committed,
        snapshot.holes,
        known,
        complete,
        continuations,
    )
