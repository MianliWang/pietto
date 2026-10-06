"""S16 atomic complete-generation publication over an explicit v6 job workspace.

A publication is the one immutable complete local result of a generation: a
reference to its exact covering checkpoint, made visible by one fenced metadata
transaction. It needs a fresh caller acceptance, the recorded closing
observation of a normally ended, committed, cleanly closed and qualified closing
attempt (the original capture, or an S14 continuation that re-enumerated
[0, N)), exact gap-free coverage [0, N) and every member file read and checked
again. The preparation retention becomes the publication's own protection in
that transaction. A publication is not evidence about older attempts, a sink
effect, an R1 acknowledgement, a notification or current file integrity.
Nothing here retries, schedules, unpublishes, expires or deletes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
import time
from typing import Any
import weakref

from pietto._project import project_job_chunks as chunks
from pietto._project.project_job_capture import (
    SnapshotReader,
    _snapshot,
    arrow_output,
    contract_digest,
    coordinate_scheme,
    known_extent,
    release_retention,
    retain_checkpoint,
    stored_binding,
)
from pietto._project.project_job_store import (
    _FENCE,
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
    CHUNKS,
    JobStoreError,
    Workspace,
    read,
    supports,
    valid_identity,
)

__all__: tuple[str, ...] = ()

FORMAT = "pietto.publication.v1"
MAX_ACCEPTANCE_SECONDS = 86400
MAX_PURPOSE_BYTES = 256
# Each route's own normal cleanup term. LOCAL_CLOSED_REMOTE_UNOBSERVED is local
# closure without a remote observation; the COMMIT_ACK is the transaction fact.
CLEAN = {
    "postgres_rows": "CLOSED",
    "postgres_adbc": "LOCAL_CLOSED_REMOTE_UNOBSERVED",
    "mysql_rows": "LOCAL_CLOSED_REMOTE_UNOBSERVED",
}
GUARDS = ("STATIC", "FULFILLED")
# The trusted host clocks. Tests inject explicit boundaries; callers cannot.
_wall = time.time
_monotonic = time.monotonic
_ACCEPTED: weakref.WeakSet = weakref.WeakSet()
_PREPARED: weakref.WeakSet = weakref.WeakSet()


def _publishing(workspace: Workspace) -> None:
    if not supports(workspace, "complete-publication"):
        raise JobStoreError("WORKSPACE_PUBLICATION_FORMAT")


def covers(ranges, extent) -> bool:
    """Exactly [0, extent): contiguous non-empty members, or the one [0, 0) member."""
    if type(extent) is not int or extent < 0:
        return False
    if extent == 0:
        return list(ranges) == [(0, 0)]
    position = 0
    for start, stop in sorted(ranges):
        if start != position or stop <= start:
            return False
        position = stop
    return position == extent


def _basis(facts) -> bool:
    end = facts["end"]
    if end is None or end[1] != "EOF":
        return False
    closing, members = facts["closing"], facts["members"]
    if facts["basis"] == "CAPTURE":
        return all(m[3] == closing for m in members)
    if facts["basis"] != "CONTINUATION":
        return False
    previous = facts["predecessor"]
    # Old members kept, every new member this attempt's own, at its own end.
    return (
        facts["reconciled"]
        and facts["end_checkpoint"] == facts["checkpoint"]
        and previous <= {m[0] for m in members}
        and all(m[3] == closing for m in members if m[0] not in previous)
    )


def eligibility(facts) -> tuple[str, ...]:
    """Every refusal of the complete-result truth table over raw facts (see
    `_facts`); an empty tuple is eligible. Cancel flags alone never refuse."""
    outcome = facts["outcome"] or {}
    observation = facts["observation"]
    extent = facts["extent"]
    states = outcome.get("guard_states")
    checks = (
        (
            "PUBLICATION_CLOSING_UNOBSERVED",
            facts["terminal"] == "OUTCOME" and observation is not None,
        ),
        ("PUBLICATION_SOURCE", outcome.get("source") == "EOF"),
        (
            "PUBLICATION_TRANSACTION",
            outcome.get("transaction") == "COMMIT_ACK"
            and outcome.get("remote_source_use_end") == "TRANSACTION_ACK",
        ),
        ("PUBLICATION_DELIVERY", outcome.get("delivery") == "COMPLETE"),
        (
            "PUBLICATION_CLEANUP",
            outcome.get("cleanup") == CLEAN.get(facts["route"])
            and observation is not None
            and observation["cleanup"] == [],
        ),
        (
            "PUBLICATION_PRIMARY",
            observation is not None and observation["failure"] is None,
        ),
        (
            "PUBLICATION_QUALIFICATION",
            outcome.get("source_qualification") == "QUALIFIED"
            and outcome.get("transaction_opened") is True,
        ),
        (
            "PUBLICATION_GUARDS",
            type(states) is list and all(s in GUARDS for s in states),
        ),
        (
            "PUBLICATION_OUTCOME",
            outcome.get("structure") == "ACCEPTED"
            and outcome.get("deployment_acceptance")
            == "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
            and outcome.get("route") == facts["route"]
            and outcome.get("binding_reference") == facts["binding_reference"],
        ),
        ("PUBLICATION_BASIS", _basis(facts)),
        (
            "PUBLICATION_EXTENT",
            extent is not None
            and facts["known"] == extent
            and observation is not None
            and observation["rows"] == extent,
        ),
        (
            "PUBLICATION_COVERAGE",
            facts["latest"] == facts["checkpoint"] and covers(facts["ranges"], extent),
        ),
        ("PUBLICATION_ATTEMPT_OPEN", facts["open"] == 0),
        ("GENERATION_PUBLISHED", not facts["published"]),
    )
    return tuple(code for code, ok in checks if not ok)


def _facts(c, workspace, job, generation, checkpoint, closing) -> dict:
    """The raw closing, end, membership and history facts of one transaction."""
    head = c.execute(
        "SELECT g.route, g.binding, p.attempt, p.kind FROM generation g"
        " JOIN capture p ON p.generation = g.identity AND p.job = g.job"
        " WHERE g.identity = ? AND g.job = ?",
        (generation, job),
    ).fetchone()
    if head is None:
        raise JobStoreError("CAPTURE_UNKNOWN")
    route, binding, captured, kind = head
    attempt = c.execute(
        "SELECT binding_reference FROM attempt WHERE identity = ? AND generation = ?"
        " AND job = ?",
        (closing, generation, job),
    ).fetchone()
    if attempt is None:
        raise JobStoreError("PUBLICATION_BASIS")
    terminal = c.execute(
        "SELECT kind, outcome FROM attempt_terminal WHERE attempt = ?", (closing,)
    ).fetchone()
    observed = c.execute(
        "SELECT closed, rows, failure, cleanup FROM closing_observation"
        " WHERE attempt = ? AND generation = ?",
        (closing, generation),
    ).fetchone()
    basis, end, reconciled, end_checkpoint = None, None, False, None
    predecessor: frozenset = frozenset()
    if closing == captured:
        basis = "CAPTURE"
        end = c.execute(
            "SELECT observed, source FROM capture_end WHERE generation = ?",
            (generation,),
        ).fetchone()
    else:
        found = c.execute(
            "SELECT n.predecessor,"
            " (SELECT count(*) FROM reconciliation r WHERE r.attempt = n.attempt),"
            " e.observed, e.source, e.checkpoint FROM continuation n"
            " LEFT JOIN continuation_end e ON e.attempt = n.attempt"
            " WHERE n.attempt = ? AND n.generation = ? AND n.job = ?",
            (closing, generation, job),
        ).fetchone()
        if found is not None:
            basis, reconciled, end_checkpoint = "CONTINUATION", bool(found[1]), found[4]
            end = None if found[3] is None else (found[2], found[3])
            if found[0] is not None:
                predecessor = frozenset(
                    r[0]
                    for r in c.execute(
                        "SELECT chunk FROM checkpoint_member WHERE checkpoint = ?",
                        (found[0],),
                    )
                )
    snapshot = _snapshot(c, workspace, job, generation, checkpoint)
    latest = c.execute(
        "SELECT identity FROM checkpoint WHERE generation = ?"
        " ORDER BY ordinal DESC LIMIT 1",
        (generation,),
    ).fetchone()
    return {
        "route": route,
        "binding": binding,
        "kind": kind,
        "checkpoint": checkpoint,
        "closing": closing,
        "binding_reference": attempt[0],
        "terminal": None if terminal is None else terminal[0],
        "outcome": None if terminal is None else json.loads(terminal[1]),
        "observation": None
        if observed is None
        else {
            "closed": bool(observed[0]),
            "rows": observed[1],
            "failure": None if observed[2] is None else json.loads(observed[2]),
            "cleanup": json.loads(observed[3]),
        },
        "basis": basis,
        "end": None if end is None else tuple(end),
        "reconciled": reconciled,
        "end_checkpoint": end_checkpoint,
        "predecessor": predecessor,
        "members": tuple(
            (m.chunk, m.start, m.stop, m.attempt) for m in snapshot.members
        ),
        "ranges": tuple((m.start, m.stop) for m in snapshot.members),
        "latest": None if latest is None else latest[0],
        "known": known_extent(c, workspace, generation),
        "extent": end[0] if end is not None and end[1] == "EOF" else None,
        "open": c.execute(
            "SELECT count(*) FROM attempt a WHERE a.generation = ? AND NOT EXISTS"
            " (SELECT 1 FROM attempt_terminal t WHERE t.attempt = a.identity)",
            (generation,),
        ).fetchone()[0],
        "published": c.execute(
            "SELECT 1 FROM publication WHERE generation = ?", (generation,)
        ).fetchone()
        is not None,
        "snapshot": snapshot,
    }


@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class PublicationAcceptance:
    """A process-local caller acceptance to publish one generation; never stored.

    It names the exact checkpoint and closing attempt. No stored row, receipt,
    publication or copy mints one; identities authenticate nobody.
    """

    workspace: str
    job: str
    generation: str
    checkpoint: str
    closing: str
    purpose: str
    route: str
    isolation: str
    binding: str
    contract: str
    scheme: str = field(repr=False)
    seconds: int
    accepted_at: float
    _output: Any = field(repr=False)
    _refinement: Any = field(repr=False)
    _deadline: float = field(repr=False)
    _pid: int = field(repr=False)

    def __reduce_ex__(self, protocol):
        raise JobStoreError("ACCEPTANCE_COPY")


def _accepted(acceptance) -> PublicationAcceptance:
    """Issued here, by this process, and within both validity bounds now."""
    if type(acceptance) is not PublicationAcceptance or acceptance not in _ACCEPTED:
        raise JobStoreError("ACCEPTANCE_UNKNOWN")
    if acceptance._pid != os.getpid():
        raise JobStoreError("ACCEPTANCE_FOREIGN_PROCESS")
    if not (
        _monotonic() < acceptance._deadline
        and _wall() < acceptance.accepted_at + acceptance.seconds
    ):
        raise JobStoreError("ACCEPTANCE_EXPIRED")
    return acceptance


def accept_publication(
    workspace: Workspace,
    job: str,
    generation: str,
    *,
    checkpoint: str,
    closing: str,
    purpose: str,
    route: str,
    isolation: str,
    values,
    expected_pin: str,
    accepted_producer: str,
    accepted_compatibility: tuple,
    seconds: int,
) -> PublicationAcceptance:
    """Fresh trust, exact typed values, route/isolation, output/scheme and (R2)
    the extraction specification; no source, guard or database credential."""
    from pietto._project.project_execution import compiled_output
    from pietto._project.project_execution_template import bind_values
    from pietto._project.project_job_extraction import specification

    _publishing(workspace)
    if not valid_identity(checkpoint, "ckp"):
        raise JobStoreError("CHECKPOINT_UNKNOWN")
    if not valid_identity(closing, "att"):
        raise JobStoreError("PUBLICATION_BASIS")
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
            "SELECT g.binding, g.isolation, p.contract, p.scheme,"
            " (SELECT specification FROM extraction x WHERE x.generation = p.generation)"
            " FROM generation g JOIN capture p ON p.generation = g.identity"
            " AND p.job = g.job WHERE g.identity = ? AND g.job = ?",
            (generation, job),
        ).fetchone()
        if row is None:
            raise JobStoreError("CAPTURE_UNKNOWN")
        _snapshot(c, workspace, job, generation, checkpoint)
        return row

    record, stored_isolation, contract, scheme, text = read(workspace, body)
    if isolation != stored_isolation:
        raise JobStoreError("ACCEPTANCE_ISOLATION")
    if (contract, scheme) != (contract_digest(output), coordinate_scheme(refinement)):
        raise JobStoreError("READER_SNAPSHOT")
    if text is not None and (
        refinement is None
        or specification(refinement, output, route, isolation) != text
    ):
        raise JobStoreError("EXTRACTION_SPECIFICATION")
    acceptance = PublicationAcceptance(
        workspace.identity,
        job,
        generation,
        checkpoint,
        closing,
        purpose,
        route,
        isolation,
        record,
        contract,
        scheme,
        seconds,
        accepted_at,
        output,
        refinement,
        deadline,
        os.getpid(),
    )
    _ACCEPTED.add(acceptance)
    return _accepted(acceptance)


def _object(directory: int, member) -> chunks.FileFacts:
    """One member's file object (no content), for `chunks.file_identity`."""
    try:
        state = os.stat(member.file, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        raise JobStoreError("CHUNK_MISSING") from None
    return chunks.FileFacts(
        member.file,
        state.st_size,
        member.digest,
        state.st_dev,
        state.st_ino,
        state.st_ctime_ns,
    )


def _verify(workspace, acceptance, snapshot) -> tuple[chunks.FileFacts, ...]:
    """Every member, one bounded chunk at a time, with every S12 reader check
    against freshly reconstructed requirements; the object read is the one
    observed before and after. No decoded table is kept."""
    stored = arrow_output(
        acceptance.job,
        acceptance.generation,
        acceptance._output,
        acceptance._refinement,
        acceptance.route,
    )
    files = []
    directory = workspace.directory(CHUNKS)
    try:
        with SnapshotReader(workspace, snapshot, stored) as reader:
            for index, member in enumerate(snapshot.members):
                before = _object(directory, member)
                reader.read(index)
                if _object(directory, member) != before:
                    raise JobStoreError("CHUNK_OBJECT")
                files.append(before)
    finally:
        os.close(directory)
    return tuple(files)


class PreparedPublication:
    """A process-local, single-subject prepared publication; never a permit.

    It holds the preparation retention, the verified membership and its file
    objects. It cannot be copied, serialized or rebuilt from a digest.
    """

    __slots__ = (
        "acceptance",
        "publisher",
        "generation",
        "checkpoint",
        "closing",
        "extent",
        "members",
        "files",
        "retention",
        "descriptor",
        "binding",
        "contract",
        "scheme",
        "state",
        "_pid",
        "__weakref__",
    )

    def __init__(self, acceptance, publisher, facts, files, retention, descriptor):
        self.acceptance, self.publisher = acceptance, publisher
        self.generation, self.checkpoint = acceptance.generation, acceptance.checkpoint
        self.closing, self.extent = acceptance.closing, facts["extent"]
        self.members, self.files = facts["members"], files
        self.retention, self.descriptor = retention, descriptor
        self.binding, self.contract, self.scheme = (
            facts["binding"],
            acceptance.contract,
            acceptance.scheme,
        )
        # PREPARED, then PUBLISHED, REFUSED or UNKNOWN after the first publish call.
        self.state = "PREPARED"
        self._pid = os.getpid()

    def __reduce_ex__(self, protocol):
        raise JobStoreError("PREPARED_COPY")


def _release(publisher, retention, primary) -> None:
    """Known nonpublication: release only this preparation's protection; keep
    it (conservatively) when even that is uncertain."""
    try:
        release_retention(publisher, retention, operation=new_operation())
    except JobStoreError as error:
        primary.add_note("preparation protection kept: " + str(error))


def _refuse(facts) -> None:
    refused = eligibility(facts)
    if refused:
        raise JobStoreError(refused[0])


def prepare_publication(
    publisher: Publisher, acceptance: PublicationAcceptance, *, operation: str
) -> PreparedPublication:
    """Protect the named checkpoint, then check every structured fact and every
    member file outside any write transaction; no source access."""
    workspace = publisher.use()
    _publishing(workspace)
    acceptance = _accepted(acceptance)
    if (acceptance.workspace, acceptance.job) != (workspace.identity, publisher.job):
        raise JobStoreError("ACCEPTANCE_SUBJECT")
    snapshot = retain_checkpoint(
        publisher,
        acceptance.generation,
        scope={
            "closing": acceptance.closing,
            "purpose": "publication-preparation",
            "subject": acceptance.purpose,
        },
        operation=operation,
        checkpoint=acceptance.checkpoint,
    )
    retention = snapshot.retention
    try:
        facts = read(
            workspace,
            lambda c: _facts(
                c,
                workspace,
                publisher.job,
                acceptance.generation,
                acceptance.checkpoint,
                acceptance.closing,
            ),
        )
        _refuse(facts)
        files = _verify(workspace, acceptance, facts["snapshot"])
        # Expensive work is over: the acceptance and the job must still allow it.
        _accepted(acceptance)
        if (
            read(
                workspace,
                lambda c: c.execute(
                    "SELECT state FROM job WHERE identity = ?", (publisher.job,)
                ).fetchone()[0],
            )
            != "ACTIVE"
        ):
            raise JobStoreError("JOB_STATE")
    except BaseException as primary:
        _release(publisher, retention, primary)
        raise
    descriptor = _json(
        {
            "basis": facts["basis"],
            "chunk": chunks.FORMAT,
            "coordinates": chunks.COORDINATES if facts["kind"] == "REFINED" else None,
            "format": FORMAT,
            "kind": facts["kind"],
            "workspace": workspace.format,
        }
    )
    prepared = PreparedPublication(
        acceptance, publisher, facts, files, retention, descriptor
    )
    _PREPARED.add(prepared)
    return prepared


def publish_generation(
    publisher: Publisher, prepared: PreparedPublication, *, operation: str
) -> OperationResult:
    """The one visibility point: recheck everything under the ACTIVE fence and
    insert the immutable publication with its own protection in one transaction.

    COMMITTED_THIS_CALL only after an observed COMMIT; an uncertain COMMIT is
    STORE_COMMIT_UNKNOWN with everything kept (query the original operation).
    """
    workspace = publisher.use()
    _publishing(workspace)
    if (
        type(prepared) is not PreparedPublication
        or prepared not in _PREPARED
        or prepared._pid != os.getpid()
        or prepared.publisher is not publisher
    ):
        raise JobStoreError("PREPARED_UNKNOWN")
    if prepared.state == "REFUSED":
        raise JobStoreError("PREPARED_USED")
    request = _identity_request(
        publisher,
        generation=prepared.generation,
        checkpoint=prepared.checkpoint,
        closing=prepared.closing,
        extent=prepared.extent,
        members=len(prepared.members),
        retention=prepared.retention,
        descriptor=prepared.descriptor,
    )

    def effect(c):
        revision = _fence(c, publisher, _FENCE)
        # Validity is judged at the visibility point itself (an expired
        # acceptance after slow preparation refuses here, and is released).
        _accepted(prepared.acceptance)
        facts = _facts(
            c,
            workspace,
            publisher.job,
            prepared.generation,
            prepared.checkpoint,
            prepared.closing,
        )
        _refuse(facts)
        if (facts["members"], facts["extent"]) != (prepared.members, prepared.extent):
            raise JobStoreError("PUBLICATION_MEMBERSHIP")
        held = c.execute(
            "SELECT generation, checkpoint, (SELECT count(*) FROM retention_release r"
            " WHERE r.retention = identity) FROM retention WHERE identity = ?"
            " AND job = ?",
            (prepared.retention, publisher.job),
        ).fetchone()
        if held is None or held[:2] != (prepared.generation, prepared.checkpoint):
            raise JobStoreError("RETENTION_UNKNOWN")
        if held[2]:
            raise JobStoreError("RETENTION_RELEASED")
        # The commit boundary rechecks each file object; nothing is read.
        directory = workspace.directory(CHUNKS)
        try:
            for item in prepared.files:
                chunks.file_identity(directory, item)
        finally:
            os.close(directory)
        c.execute(
            "INSERT INTO publication(generation, job, binding, checkpoint, extent,"
            " members, contract, scheme, closing, retention, descriptor, operation,"
            " publisher_epoch, publisher_instance)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                prepared.generation,
                publisher.job,
                prepared.binding,
                prepared.checkpoint,
                prepared.extent,
                len(prepared.members),
                prepared.contract,
                prepared.scheme,
                prepared.closing,
                prepared.retention,
                prepared.descriptor,
                operation,
                publisher.epoch,
                publisher.instance,
            ),
        )
        return publisher.job, {
            "checkpoint": prepared.checkpoint,
            "closing": prepared.closing,
            "extent": prepared.extent,
            "generation": prepared.generation,
            "retention": prepared.retention,
            "revision": revision,
        }

    first = prepared.state == "PREPARED"
    try:
        result = _advance(
            publisher,
            _operate(
                workspace,
                operation,
                "publish_generation",
                request,
                effect,
                payload=len(prepared.descriptor),
            ),
        )
    except JobStoreError as primary:
        if str(primary) == "STORE_COMMIT_UNKNOWN":
            prepared.state = "UNKNOWN"
        elif first:
            prepared.state = "REFUSED"
            _release(publisher, prepared.retention, primary)
        raise
    prepared.state = "PUBLISHED"
    return result


@dataclass(frozen=True, slots=True)
class Publication:
    """A RECORDED complete-result reference; reading its rows needs a fresh
    saved-read acceptance, and current file integrity is a separate check."""

    job: str
    generation: str
    binding: str
    checkpoint: str
    extent: int
    members: int
    contract: str
    scheme: str = field(repr=False)
    closing: str
    retention: str
    descriptor: str = field(repr=False)
    operation: str
    publisher_epoch: int
    publisher_instance: str
    integrity: str = "RECORDED"


_COLUMNS = (
    "p.job, p.generation, p.binding, p.checkpoint, p.extent, p.members, p.contract,"
    " p.scheme, p.closing, p.retention, p.descriptor, p.operation,"
    " p.publisher_epoch, p.publisher_instance"
)


def publication(workspace: Workspace, job: str, generation: str) -> Publication | None:
    """The exact generation's publication, None when it is known NOT published;
    IO, corruption or an unknown generation raise (never absence)."""
    _publishing(workspace)
    if not valid_identity(job, "job") or not valid_identity(generation, "gen"):
        raise JobStoreError("GENERATION_UNKNOWN")

    def body(c):
        if not c.execute(
            "SELECT 1 FROM generation WHERE identity = ? AND job = ?", (generation, job)
        ).fetchone():
            raise JobStoreError("GENERATION_UNKNOWN")
        return c.execute(
            "SELECT " + _COLUMNS + " FROM publication p WHERE p.generation = ?"
            " AND p.job = ?",
            (generation, job),
        ).fetchone()

    row = read(workspace, body)
    return None if row is None else Publication(*row)


def publications(workspace: Workspace, job: str) -> tuple[Publication, ...]:
    """Every publication of one job in commit order, from one read snapshot
    (bounded by the generation limit)."""
    _publishing(workspace)
    if not valid_identity(job, "job"):
        raise JobStoreError("JOB_UNKNOWN")
    rows = read(
        workspace,
        lambda c: c.execute(
            "SELECT " + _COLUMNS + " FROM publication p JOIN operation o"
            " ON o.identity = p.operation WHERE p.job = ? ORDER BY o.sequence",
            (job,),
        ).fetchall(),
    )
    return tuple(Publication(*row) for row in rows)
