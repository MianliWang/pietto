"""S17 explicit unpublished-generation retirement and concurrent safe collection.

Collection never decides from age, a file listing, an expired lease or a PID.
A candidate is either a committed chunk of an explicitly RETIRED unpublished
generation outside every unreleased retention, or an ABANDONED claimed file (a
v7 claim with no chunk row whose attempt has a terminal or whose publisher epoch
was superseded). Under the generation's EXCLUSIVE lease (never waited for) the
collector observes the exact objects, then one short transaction fenced by the
current runtime incarnation recomputes every root and pins a tombstone per
member. Only then are those exact objects unlinked through checked directory
descriptors; after the directories are synchronized a removal is recorded, and
only a removal returns its bytes to the accounting. A tombstoned subject is
refused by every later reader, retainer and publisher. History rows (chunks,
checkpoints, attempts, operations) are never deleted or edited. Published
generations, sink data, the database, its journals, envelopes and lock files
are never collected.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import stat
from typing import Any

from pietto._project import project_job_chunks as chunks
from pietto._project.project_job_store import (
    _FENCE_CONTROL,
    LIMITS,
    OperationResult,
    Publisher,
    _advance,
    _fence,
    _identity_request,
    _json,
    _operate,
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
    write,
)

__all__: tuple[str, ...] = ()

MAX_MEMBERS = 64
MAX_BYTES = 1024 * 1024 * 1024
MAX_GENERATIONS = 16


def _collecting(workspace: Workspace) -> None:
    if not supports(workspace, "concurrent-gc"):
        raise JobStoreError("WORKSPACE_COLLECTION_FORMAT")


def retire_generation(
    publisher: Publisher, generation: str, *, operation: str
) -> OperationResult:
    """Explicitly remove one unpublished generation's implicit latest-checkpoint
    root and forbid its further production, references and publication. Not a
    cancellation, expiry or unpublication; every other root stays effective."""
    workspace = publisher.use()
    _collecting(workspace)
    if not valid_identity(generation, "gen"):
        raise JobStoreError("GENERATION_UNKNOWN")

    def effect(c):
        revision = _fence(c, publisher, _FENCE_CONTROL)
        if not c.execute(
            "SELECT 1 FROM generation WHERE identity = ? AND job = ?",
            (generation, publisher.job),
        ).fetchone():
            raise JobStoreError("GENERATION_UNKNOWN")
        if c.execute(
            "SELECT 1 FROM publication WHERE generation = ?", (generation,)
        ).fetchone():
            raise JobStoreError("GENERATION_PUBLISHED")
        if c.execute(
            "SELECT 1 FROM generation_retirement WHERE generation = ?", (generation,)
        ).fetchone():
            raise JobStoreError("GENERATION_RETIRED")
        if c.execute(
            "SELECT 1 FROM attempt a WHERE a.generation = ? AND NOT EXISTS"
            " (SELECT 1 FROM attempt_terminal t WHERE t.attempt = a.identity)",
            (generation,),
        ).fetchone():
            raise JobStoreError("ATTEMPT_OPEN")
        c.execute(
            "INSERT INTO generation_retirement(generation, job, publisher_epoch,"
            " publisher_instance) VALUES (?, ?, ?, ?)",
            (generation, publisher.job, publisher.epoch, publisher.instance),
        )
        return publisher.job, {"generation": generation, "revision": revision}

    return _advance(
        publisher,
        _operate(
            workspace,
            operation,
            "retire_generation",
            _identity_request(publisher, generation=generation),
            effect,
            control=True,
        ),
    )


def _reason(c, retention, scope) -> str:
    """The original owner of one unreleased retention (inspection only)."""
    if c.execute(
        "SELECT 1 FROM publication WHERE retention = ?", (retention,)
    ).fetchone():
        return "PUBLICATION"
    if c.execute(
        "SELECT 1 FROM stream_window WHERE retention = ?", (retention,)
    ).fetchone():
        return "WINDOW"
    if c.execute("SELECT 1 FROM consumer WHERE retention = ?", (retention,)).fetchone():
        return "CONSUMER"
    if json.loads(scope).get("purpose") == "publication-preparation":
        return "PREPARATION"
    return "EXPLICIT"


def _roots(c, job, generation) -> tuple[tuple, frozenset]:
    """Every independently applicable metadata root of one generation (reason,
    subject, checkpoint) and the union of the members they protect."""
    roots: list[tuple] = []
    retired = bool(
        c.execute(
            "SELECT 1 FROM generation_retirement WHERE generation = ?", (generation,)
        ).fetchone()
    )
    latest = c.execute(
        "SELECT identity FROM checkpoint WHERE generation = ? ORDER BY ordinal DESC"
        " LIMIT 1",
        (generation,),
    ).fetchone()
    if latest is not None and not retired:
        roots.append(("LATEST", None, latest[0]))
    for retention, checkpoint, scope in c.execute(
        "SELECT identity, checkpoint, scope FROM retention WHERE generation = ?"
        " AND identity NOT IN (SELECT retention FROM retention_release)"
        " ORDER BY identity",
        (generation,),
    ).fetchall():
        roots.append((_reason(c, retention, scope), retention, checkpoint))
    for (stream,) in c.execute(
        "SELECT DISTINCT i.stream FROM stream_issuance i JOIN stream s"
        " ON s.identity = i.stream WHERE s.generation = ? AND"
        " (SELECT count(*) FROM sink_observation o WHERE o.stream = i.stream"
        " AND o.position >= i.start AND o.position < i.stop) < i.stop - i.start",
        (generation,),
    ).fetchall():
        roots.append(("UNRESOLVED_WINDOW", stream, None))
    protected = frozenset(
        r[0]
        for r in c.execute(
            "SELECT m.chunk FROM checkpoint_member m WHERE m.checkpoint IN ("
            + ", ".join("?" * len([x for x in roots if x[2] is not None]))
            + ")",
            tuple(x[2] for x in roots if x[2] is not None),
        )
    )
    return tuple(roots), protected


@dataclass(frozen=True, slots=True)
class GenerationProtection:
    """One generation's current roots and collection facts (inspection)."""

    generation: str
    retired: bool
    published: bool
    roots: tuple[tuple, ...]
    protected: frozenset[str]
    decided: frozenset[str]
    removed: frozenset[str]


def protection(workspace: Workspace, job: str) -> tuple[GenerationProtection, ...]:
    """The union of roots per generation of one job in ONE read snapshot. Live
    file users hold leases; they are not metadata and are reported as BUSY by
    the collector instead."""
    _collecting(workspace)
    if not valid_identity(job, "job"):
        raise JobStoreError("JOB_UNKNOWN")

    def body(c):
        result = []
        for (generation,) in c.execute(
            "SELECT identity FROM generation WHERE job = ? ORDER BY identity", (job,)
        ).fetchall():
            roots, protected = _roots(c, job, generation)
            result.append(
                GenerationProtection(
                    generation,
                    bool(
                        c.execute(
                            "SELECT 1 FROM generation_retirement WHERE generation = ?",
                            (generation,),
                        ).fetchone()
                    ),
                    bool(
                        c.execute(
                            "SELECT 1 FROM publication WHERE generation = ?",
                            (generation,),
                        ).fetchone()
                    ),
                    roots,
                    protected,
                    frozenset(
                        r[0]
                        for r in c.execute(
                            "SELECT chunk FROM tombstone WHERE generation = ?",
                            (generation,),
                        )
                    ),
                    frozenset(
                        r[0]
                        for r in c.execute(
                            "SELECT r.chunk FROM removal r JOIN tombstone t"
                            " ON t.chunk = r.chunk WHERE t.generation = ?",
                            (generation,),
                        )
                    ),
                )
            )
        return tuple(result)

    return read(workspace, body)


def _candidates(c, generation, limit) -> tuple[tuple, tuple]:
    """(candidates, blocked reasons) of one generation now, in a stable order.
    A candidate is (chunk, basis, bytes, job)."""
    head = c.execute(
        "SELECT g.job, EXISTS (SELECT 1 FROM generation_retirement r"
        " WHERE r.generation = g.identity),"
        " EXISTS (SELECT 1 FROM publication p WHERE p.generation = g.identity),"
        " j.publisher_epoch FROM generation g JOIN job j ON j.identity = g.job"
        " WHERE g.identity = ?",
        (generation,),
    ).fetchone()
    if head is None:
        raise JobStoreError("GENERATION_UNKNOWN")
    job, retired, published, epoch = head
    roots, protected = _roots(c, job, generation)
    found: list[tuple] = []
    blocked: list[tuple] = []
    if retired and not published:
        for chunk, size in c.execute(
            "SELECT k.chunk, k.bytes FROM chunk_claim k JOIN chunk h"
            " ON h.identity = k.chunk WHERE k.generation = ? AND NOT EXISTS"
            " (SELECT 1 FROM tombstone t WHERE t.chunk = k.chunk) ORDER BY k.chunk",
            (generation,),
        ).fetchall():
            if chunk in protected:
                blocked.append((chunk, "PROTECTED"))
            else:
                found.append((chunk, "RETIRED", size, job))
    for chunk, size, terminal, claimed in c.execute(
        "SELECT k.chunk, k.bytes, EXISTS (SELECT 1 FROM attempt_terminal t"
        " WHERE t.attempt = k.attempt), k.publisher_epoch FROM chunk_claim k"
        " WHERE k.generation = ? AND NOT EXISTS (SELECT 1 FROM chunk h"
        " WHERE h.identity = k.chunk) AND NOT EXISTS (SELECT 1 FROM tombstone t"
        " WHERE t.chunk = k.chunk) ORDER BY k.chunk",
        (generation,),
    ).fetchall():
        if terminal or claimed < epoch:
            found.append((chunk, "ABANDONED", size, job))
        else:
            blocked.append((chunk, "OWNER_LIVE"))
    if not retired and not found:
        blocked.append((None, "NOT_RETIRED"))
    if published:
        blocked.append((None, "PUBLISHED"))
    return tuple(found[:limit]), tuple(blocked) + tuple(
        ("ROOT", r[0], r[1]) for r in roots
    )


def _objects(workspace, chunk) -> list:
    """Every present alias of one claimed subject: [directory, name, device,
    inode, ctime, size]. A symlink, directory or foreign object refuses."""
    found = []
    for directory, name in (
        (CHUNKS, chunk + chunks.SUFFIX),
        (STAGING, chunk + chunks.STAGED),
    ):
        fd = workspace.directory(directory)
        try:
            try:
                state = os.stat(name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
        finally:
            os.close(fd)
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_uid != os.geteuid()
            or state.st_mode & 0o077
        ):
            raise JobStoreError("COLLECTION_OBJECT")
        found.append(
            [
                directory,
                name,
                state.st_dev,
                state.st_ino,
                state.st_ctime_ns,
                state.st_size,
            ]
        )
    if len({(o[2], o[3]) for o in found}) > 1:
        raise JobStoreError("COLLECTION_OBJECT")
    return found


def _remove(workspace, objects) -> bool:
    """Unlink exactly the pinned aliases still present; True if this call
    unlinked something. While every pinned alias is present its ctime must
    match too; after an own alias unlink the inode stays linked, so (device,
    inode, size) identifies the rest. Anything else is refused and preserved."""
    present = []
    for directory, name, device, inode, changed, size in objects:
        fd = workspace.directory(directory)
        try:
            try:
                state = os.stat(name, dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                continue
        finally:
            os.close(fd)
        if not stat.S_ISREG(state.st_mode) or (
            state.st_dev,
            state.st_ino,
            state.st_size,
        ) != (device, inode, size):
            raise JobStoreError("COLLECTION_OBJECT")
        present.append((directory, name, state.st_ctime_ns, changed))
    if len(present) == len(objects) and any(p[2] != p[3] for p in present):
        raise JobStoreError("COLLECTION_OBJECT")
    for directory, name, _now, _then in present:
        fd = workspace.directory(directory)
        try:
            chunks._unlink(name, fd)
        finally:
            os.close(fd)
    return bool(present)


def _synchronize(workspace) -> None:
    """Directory durability of the namespace change (honest-sync premise)."""
    for directory in (CHUNKS, STAGING):
        fd = workspace.directory(directory)
        try:
            chunks._sync(fd)
        finally:
            os.close(fd)


def _record_removals(workspace, owner, removed) -> None:
    from pietto._project.project_job_runtime import fence

    def body(c):
        fence(c, owner)
        for chunk, basis in removed:
            if not c.execute(
                "SELECT 1 FROM removal WHERE chunk = ?", (chunk,)
            ).fetchone():
                c.execute(
                    "INSERT INTO removal(chunk, runtime, basis) VALUES (?, ?, ?)",
                    (chunk, owner.epoch, basis),
                )

    write(workspace, body)


@dataclass(frozen=True, slots=True)
class CollectionReport:
    """What one bounded pass actually did; protected/blocked reasons explicit."""

    decided: tuple[tuple[str, str, int, int], ...]
    removed: tuple[tuple[str, str], ...]
    resumed: tuple[tuple[str, str], ...]
    busy: tuple[str, ...]
    blocked: tuple[tuple[str, tuple], ...]
    refused: tuple[tuple[str, str], ...]
    yielded: bool


def _delete(workspace, owner, pinned, refused) -> list:
    """Unlink each pinned tombstone's objects (a changed object is refused and
    preserved, the others proceed), synchronize the directories, then record
    the removals. UNLINKED only for an unlink this call performed."""
    performed = []
    for chunk, objects in pinned:
        try:
            unlinked = _remove(workspace, objects)
        except JobStoreError as error:
            if str(error) != "COLLECTION_OBJECT":
                raise
            refused.append((chunk, "COLLECTION_OBJECT"))
            continue
        performed.append((chunk, "UNLINKED" if unlinked else "ABSENT"))
    _synchronize(workspace)
    if performed:
        _record_removals(workspace, owner, performed)
    return performed


def collect(
    workspace: Workspace,
    owner,
    *,
    max_members: int = MAX_MEMBERS,
    max_bytes: int = MAX_BYTES,
    max_generations: int = MAX_GENERATIONS,
    yielding: Any = None,
) -> CollectionReport:
    """One bounded pass: first resume decided-but-unremoved tombstones (their
    pinned objects only), then decide and remove new candidates generation by
    generation. A busy generation is skipped; nothing waits for a lease."""
    from pietto._project.project_job_runtime import fence, owning

    _collecting(workspace)
    owner = owning(owner, workspace)
    if (
        type(max_members) is not int
        or not 1 <= max_members <= MAX_MEMBERS
        or type(max_bytes) is not int
        or not 1 <= max_bytes <= MAX_BYTES
        or type(max_generations) is not int
        or not 1 <= max_generations <= MAX_GENERATIONS
    ):
        raise JobStoreError("COLLECTION_BOUND")
    decided: list = []
    removed: list = []
    resumed: list = []
    busy: list = []
    blocked: list = []
    refused: list = []
    yielded = False
    pending = read(
        workspace,
        lambda c: c.execute(
            "SELECT t.generation, t.chunk, t.objects FROM tombstone t WHERE NOT EXISTS"
            " (SELECT 1 FROM removal r WHERE r.chunk = t.chunk)"
            " ORDER BY t.generation, t.chunk LIMIT ?",
            (max_members,),
        ).fetchall(),
    )
    groups: dict[str, list] = {}
    for generation, chunk, objects in pending:
        groups.setdefault(generation, []).append((chunk, json.loads(objects)))
    for generation, pinned in groups.items():
        try:
            lease = chunks.Lease(workspace, generation, exclusive=True)
        except JobStoreError as error:
            if str(error) != "LEASE_BUSY":
                raise
            busy.append(generation)
            continue
        try:
            resumed.extend(_delete(workspace, owner, pinned, refused))
        finally:
            lease.close()
    members, size = len(resumed), 0
    # Only generations that can hold a candidate take decision slots, so a
    # crowd of protected generations never starves a collectable one; the
    # others are reported (with reasons) only when nothing is collectable.
    possible, claimed = read(
        workspace,
        lambda c: (
            c.execute(
                "SELECT DISTINCT k.generation FROM chunk_claim k WHERE NOT EXISTS"
                " (SELECT 1 FROM tombstone t WHERE t.chunk = k.chunk) AND ("
                "(EXISTS (SELECT 1 FROM chunk h WHERE h.identity = k.chunk)"
                " AND EXISTS (SELECT 1 FROM generation_retirement r"
                " WHERE r.generation = k.generation)"
                " AND NOT EXISTS (SELECT 1 FROM publication p"
                " WHERE p.generation = k.generation))"
                " OR (NOT EXISTS (SELECT 1 FROM chunk h WHERE h.identity = k.chunk)"
                " AND (EXISTS (SELECT 1 FROM attempt_terminal a"
                " WHERE a.attempt = k.attempt) OR k.publisher_epoch <"
                " (SELECT publisher_epoch FROM job j WHERE j.identity = k.job))))"
                " ORDER BY k.generation"
            ).fetchall(),
            c.execute(
                "SELECT DISTINCT k.generation FROM chunk_claim k WHERE NOT EXISTS"
                " (SELECT 1 FROM tombstone t WHERE t.chunk = k.chunk)"
                " ORDER BY k.generation LIMIT ?",
                (max_generations,),
            ).fetchall(),
        ),
    )
    candidates = possible or claimed
    for (generation,) in candidates[:max_generations]:
        if members >= max_members or size >= max_bytes:
            break
        if yielding is not None and yielding():
            yielded = True
            break
        try:
            lease = chunks.Lease(workspace, generation, exclusive=True)
        except JobStoreError as error:
            if str(error) != "LEASE_BUSY":
                raise
            busy.append(generation)
            continue
        try:
            found, reasons = read(
                workspace, lambda c: _candidates(c, generation, max_members - members)
            )
            picked, objects = [], {}
            for chunk, basis, nbytes, job in found:
                if size + nbytes > max_bytes and picked:
                    break
                try:
                    objects[chunk] = _objects(workspace, chunk)
                except JobStoreError:
                    refused.append((chunk, "COLLECTION_OBJECT"))
                    continue
                if basis == "RETIRED" and not any(
                    o[0] == CHUNKS for o in objects[chunk]
                ):
                    # A committed file already absent is corruption, never
                    # converted into a collection.
                    refused.append((chunk, "CHUNK_MISSING"))
                    continue
                picked.append((chunk, basis, nbytes, job))
                size += nbytes
            if not picked:
                blocked.append((generation, reasons))
                continue
            identity = new_identity("gcd")

            def body(c):
                fence(c, owner)
                if (
                    c.execute("SELECT count(*) FROM collection").fetchone()[0]
                    >= LIMITS["collection"]
                ):
                    raise JobStoreError("STORE_LIMIT")
                # Recompute under the writer lock: only still-eligible members.
                now = {
                    chunk: basis
                    for chunk, basis, _n, _j in _candidates(c, generation, MAX_MEMBERS)[
                        0
                    ]
                }
                kept = [p for p in picked if now.get(p[0]) == p[1]]
                if not kept:
                    return ()
                c.execute(
                    "INSERT INTO collection(identity, job, generation, runtime, members)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (identity, kept[0][3], generation, owner.epoch, len(kept)),
                )
                c.executemany(
                    "INSERT INTO tombstone(chunk, collection, generation, basis,"
                    " objects, bytes) VALUES (?, ?, ?, ?, ?, ?)",
                    [
                        (chunk, identity, generation, basis, _json(objects[chunk]), n)
                        for chunk, basis, n, _job in kept
                    ],
                )
                return tuple(kept)

            kept = write(workspace, body)
            if not kept:
                blocked.append((generation, reasons))
                continue
            decided.append((identity, generation, len(kept), sum(k[2] for k in kept)))
            members += len(kept)
            removed.extend(
                _delete(
                    workspace, owner, [(k[0], objects[k[0]]) for k in kept], refused
                )
            )
        finally:
            lease.close()
    return CollectionReport(
        tuple(decided),
        tuple(removed),
        tuple(resumed),
        tuple(busy),
        tuple(blocked),
        tuple(refused),
        yielded,
    )


def collection_state(workspace: Workspace, identity: str) -> tuple | None:
    """A lost reply's query: the pinned tombstones and recorded removals of one
    decision, or None when it is known absent (never on IO failure)."""
    _collecting(workspace)
    if not valid_identity(identity, "gcd"):
        raise JobStoreError("COLLECTION_UNKNOWN")

    def body(c):
        head = c.execute(
            "SELECT job, generation, runtime, members FROM collection WHERE identity = ?",
            (identity,),
        ).fetchone()
        if head is None:
            return None
        return head, tuple(
            c.execute(
                "SELECT t.chunk, t.basis, t.bytes, r.basis FROM tombstone t"
                " LEFT JOIN removal r ON r.chunk = t.chunk WHERE t.collection = ?"
                " ORDER BY t.chunk",
                (identity,),
            ).fetchall()
        )

    return read(workspace, body)


def availability(workspace: Workspace, job: str, generation: str) -> tuple:
    """Per claimed chunk of one generation: (chunk, state, present). States:
    AVAILABLE (committed, usable), RETIRED_PROTECTED (retired, a root remains),
    RETIRED_UNPROTECTED (retired, collectable), CLAIMED (unpublished claim),
    COLLECTION_DECIDED (tombstone, no removal), REMOVED_OBSERVED (removal) and
    MISSING (committed or claimed, absent, no decision: an integrity failure)
    or REAPPEARED (removal recorded, a name exists again)."""
    _collecting(workspace)

    def body(c):
        roots, protected = _roots(c, job, generation)
        retired = bool(
            c.execute(
                "SELECT 1 FROM generation_retirement WHERE generation = ?",
                (generation,),
            ).fetchone()
        )
        rows = c.execute(
            "SELECT k.chunk, EXISTS (SELECT 1 FROM chunk h WHERE h.identity = k.chunk),"
            " EXISTS (SELECT 1 FROM tombstone t WHERE t.chunk = k.chunk),"
            " EXISTS (SELECT 1 FROM removal r WHERE r.chunk = k.chunk)"
            " FROM chunk_claim k WHERE k.generation = ? AND k.job = ? ORDER BY k.chunk",
            (generation, job),
        ).fetchall()
        return retired, protected, rows

    retired, protected, rows = read(workspace, body)
    result = []
    for chunk, committed, decided, gone in rows:
        try:
            present = bool(_objects(workspace, chunk))
        except JobStoreError:
            result.append((chunk, "FOREIGN_OBJECT", True))
            continue
        if gone:
            state = "REAPPEARED" if present else "REMOVED_OBSERVED"
        elif decided:
            state = "COLLECTION_DECIDED"
        elif not committed:
            state = "CLAIMED"
        elif retired:
            state = "RETIRED_PROTECTED" if chunk in protected else "RETIRED_UNPROTECTED"
        else:
            state = "AVAILABLE"
        if (
            state in ("AVAILABLE", "RETIRED_PROTECTED", "RETIRED_UNPROTECTED")
            and not present
        ):
            state = "MISSING"
        result.append((chunk, state, present))
    return tuple(result)


def charged(workspace: Workspace) -> dict:
    """The current accounting split (one snapshot): logically unavailable bytes
    still present, observed removed bytes and outstanding allowances."""
    _collecting(workspace)
    return read(
        workspace,
        lambda c: dict(
            zip(
                ("claimed", "decided_unremoved", "removed", "open_allowance"),
                c.execute(
                    "SELECT (SELECT coalesce(sum(bytes), 0) FROM chunk_claim),"
                    " (SELECT coalesce(sum(t.bytes), 0) FROM tombstone t WHERE NOT EXISTS"
                    " (SELECT 1 FROM removal r WHERE r.chunk = t.chunk)),"
                    " (SELECT coalesce(sum(t.bytes), 0) FROM tombstone t JOIN removal r"
                    " ON r.chunk = t.chunk),"
                    " (SELECT coalesce(sum(max(a.durable - (SELECT coalesce(sum(k.bytes), 0)"
                    " FROM chunk_claim k WHERE k.admission = a.identity), 0)), 0)"
                    " FROM admission a WHERE NOT EXISTS (SELECT 1 FROM admission_settlement s"
                    " WHERE s.admission = a.identity))"
                ).fetchone(),
                strict=True,
            )
        ),
    )
