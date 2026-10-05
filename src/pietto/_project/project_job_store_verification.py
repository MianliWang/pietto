"""Independent complete-relation checks over raw job-store rows.

The checker replays the operation history from raw rows and S10's own scalar and
content codecs. It does not call the store's mutation or query functions, so a
coordinated re-encoding must still satisfy the fencing and identity laws.
"""

from __future__ import annotations

import json
from typing import Any, NoReturn

from pietto._project.project_job_workspace import (
    JobStoreError,
    Workspace,
    read,
    supports,
    valid_identity,
)

__all__: tuple[str, ...] = ()

KINDS = (
    "register_job",
    "claim",
    "register_binding",
    "register_generation",
    "open_attempt",
    "attempt_terminal",
    "cancel_job",
)
CAPTURE_KINDS = (
    "begin_capture",
    "publish_chunk",
    "end_capture",
    "retain_checkpoint",
    "release_retention",
)
CAPTURE_TABLES = (
    "capture",
    "chunk",
    "checkpoint",
    "checkpoint_member",
    "capture_end",
    "retention",
    "retention_release",
)
REPLAY_KINDS = (
    "register_consumer",
    "open_replay",
    "issue_delivery",
    "acknowledge_delivery",
)
REPLAY_TABLES = ("consumer", "replay_session", "issuance", "acknowledgement")
DESCRIPTOR = (
    "attempt",
    "batches",
    "binding",
    "chunk",
    "contract",
    "coordinates",
    "format",
    "frame_bytes",
    "frame_sha256",
    "generation",
    "job",
    "kind",
    "rows",
    "start",
    "stop",
    "terminal",
    "workspace",
)
INTERRUPTED = {
    "basis": "PUBLISHER_EPOCH_ENDED_WITHOUT_TERMINAL",
    "cleanup": "UNKNOWN",
    "delivery": "UNKNOWN",
    "remote_source_use_end": "UNKNOWN",
    "source": "UNKNOWN",
    "transaction": "UNKNOWN",
}
OUTCOME_FIELDS = (
    "binding_reference",
    "cancel",
    "cleanup",
    "delivery",
    "deployment_acceptance",
    "guard_states",
    "local_durable_result",
    "native_definition_lifetime_exclusion",
    "premise_compliance",
    "remote_source_use_end",
    "route",
    "source",
    "source_qualification",
    "structure",
    "transaction",
    "transaction_opened",
)


def _fail(code: str) -> NoReturn:
    raise JobStoreError("STORE_INVARIANT_" + code)


def _canonical(text: str, *, ascii: bool = False):
    value = json.loads(text)
    if (
        json.dumps(
            value,
            ensure_ascii=ascii,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        != text
    ):
        _fail("ENCODING")
    return value


def verify_store(workspace: Workspace) -> dict:
    """Check every row and the full ordered history; return complete counts."""
    from pietto._project.project_compiled_schema import (
        CompiledError,
        _read,
        content_pin,
        decode,
        scalar_read,
    )

    capture = supports(workspace, "result-chunks")
    replay = supports(workspace, "saved-replay")
    kinds = (
        KINDS + (CAPTURE_KINDS if capture else ()) + (REPLAY_KINDS if replay else ())
    )

    def snapshot(c) -> dict[str, Any]:
        tables: dict[str, Any] = {
            name: tuple(c.execute(f"SELECT * FROM {name}"))
            for name in (CAPTURE_TABLES if capture else ())
            + (REPLAY_TABLES if replay else ())
        }
        return tables | {
            "integrity": tuple(r[0] for r in c.execute("PRAGMA integrity_check")),
            "foreign": tuple(c.execute("PRAGMA foreign_key_check")),
            "workspace": tuple(c.execute("SELECT * FROM workspace")),
            "job": {r[0]: r for r in c.execute("SELECT * FROM job")},
            "binding": {r[0]: r for r in c.execute("SELECT * FROM binding")},
            "generation": {r[0]: r for r in c.execute("SELECT * FROM generation")},
            "attempt": {r[0]: r for r in c.execute("SELECT * FROM attempt")},
            "terminal": {r[0]: r for r in c.execute("SELECT * FROM attempt_terminal")},
            "operation": tuple(c.execute("SELECT * FROM operation ORDER BY sequence")),
        }

    data = read(workspace, snapshot)
    if data["integrity"] != ("ok",) or data["foreign"]:
        _fail("INTEGRITY")
    if data["workspace"] != ((1, workspace.identity, workspace.format),):
        _fail("WORKSPACE")
    jobs, bindings, generations = data["job"], data["binding"], data["generation"]
    attempts, terminals = data["attempt"], data["terminal"]
    created: dict[object, int] = {}
    state: dict[str, dict] = {}
    events: list[tuple] = []
    for position, (sequence, identity, kind, job, request, result) in enumerate(
        data["operation"], 1
    ):
        if sequence != position or not valid_identity(identity, "op"):
            _fail("OPERATION_SEQUENCE")
        if kind not in kinds or job not in jobs:
            _fail("OPERATION_KIND")
        request, result = _canonical(request), _canonical(result)
        if kind == "register_job":
            if job in state or result != {"job": job, "revision": 1}:
                _fail("JOB_HISTORY")
            state[job] = {
                "revision": 1,
                "epoch": 0,
                "instance": None,
                "state": "ACTIVE",
                "open": None,
            }
            created[job] = sequence
            continue
        current = state.get(job)
        if current is None or request.get("job") != job:
            _fail("JOB_HISTORY")
        current["revision"] += 1
        if result.get("revision") != current["revision"]:
            _fail("REVISION_HISTORY")
        if kind == "claim":
            current["epoch"] += 1
            current["instance"] = result.get("instance")
            if (
                result.get("epoch") != current["epoch"]
                or not valid_identity(current["instance"], "pub")
                or request != {"job": job}
            ):
                _fail("PUBLISHER_HISTORY")
            continue
        # Every other mutation was fenced by the publisher in force at its point.
        if request.get("publisher") != [current["epoch"], current["instance"]]:
            _fail("FENCE_HISTORY")
        if kind == "cancel_job":
            if current["state"] != "ACTIVE" or result.get("state") != "CANCELLED":
                _fail("STATE_HISTORY")
            current["state"] = "CANCELLED"
        elif kind in CAPTURE_KINDS + REPLAY_KINDS:
            # Data progress and saved reads need an ACTIVE job; ends and
            # retention (including a consumer's release) are control.
            if (
                kind in CAPTURE_KINDS[:2] + REPLAY_KINDS
                and current["state"] != "ACTIVE"
            ):
                _fail("STATE_HISTORY")
            events.append(
                (
                    sequence,
                    kind,
                    job,
                    request,
                    result,
                    current["epoch"],
                    current["instance"],
                )
            )
        elif kind in ("register_binding", "register_generation", "open_attempt"):
            if current["state"] != "ACTIVE":
                _fail("STATE_HISTORY")
            name = {
                "register_binding": "binding",
                "register_generation": "generation",
                "open_attempt": "attempt",
            }[kind]
            entity = result.get(name)
            table = {
                "binding": bindings,
                "generation": generations,
                "attempt": attempts,
            }[name]
            if (
                entity in created
                or entity not in table
                or table[entity][2 if name == "attempt" else 1] != job
            ):
                _fail("ENTITY_HISTORY")
            created[entity] = sequence
            if name == "binding":
                if (table[entity][2], table[entity][3]) != (
                    request.get("slots"),
                    request.get("vector"),
                ):
                    _fail("BINDING_HISTORY")
            elif name == "generation":
                row = table[entity]
                if (row[2], row[3], row[4], row[5]) != (
                    request.get("binding"),
                    request.get("route"),
                    request.get("isolation"),
                    request.get("description"),
                ) or created.get(row[2], sequence) >= sequence:
                    _fail("GENERATION_HISTORY")
            else:
                row = table[entity]
                if current["open"] is not None:
                    _fail("ATTEMPT_OPEN_HISTORY")
                if (row[1], row[3], row[4], row[5], row[6]) != (
                    request.get("generation"),
                    result.get("ordinal"),
                    current["epoch"],
                    current["instance"],
                    request.get("binding_reference"),
                ) or created.get(row[1], sequence) >= sequence:
                    _fail("ATTEMPT_HISTORY")
                current["open"] = entity
        else:
            attempt = request.get("attempt")
            terminal = terminals.get(attempt)
            row = attempts.get(attempt)
            if (
                terminal is None
                or row is None
                or row[2] != job
                or created.get(attempt, sequence) >= sequence
                or ("terminal", attempt) in created
                or not terminal[1] == request.get("kind") == result.get("kind")
                or terminal[2] != current["epoch"]
                or _canonical(terminal[3]) != request.get("outcome")
            ):
                _fail("TERMINAL_HISTORY")
            created[("terminal", attempt)] = sequence
            outcome = request["outcome"]
            if terminal[1] == "INTERRUPTED":
                if row[4] >= current["epoch"] or outcome != INTERRUPTED:
                    _fail("TERMINAL_EPOCH")
            elif (row[4], row[5], row[6]) != (
                current["epoch"],
                current["instance"],
                outcome.get("binding_reference"),
            ):
                _fail("TERMINAL_EPOCH")
            if terminal[1] == "OUTCOME" and (
                tuple(sorted(outcome)) != OUTCOME_FIELDS
                or outcome["route"] != generations[row[1]][3]
            ):
                _fail("TERMINAL_OUTCOME")
            if terminal[1] == "NOT_EXECUTED" and outcome != {
                "basis": "PUBLISHER_REPORTED_NO_NATIVE_OWNER",
                "binding_reference": row[6],
            }:
                _fail("TERMINAL_OUTCOME")
            if current["open"] == attempt:
                current["open"] = None
    for job, row in jobs.items():
        current = state.get(job)
        if current is None or (row[5], row[6], row[7], row[8]) != (
            current["state"],
            current["epoch"],
            current["instance"],
            current["revision"],
        ):
            _fail("JOB_STATE")
        try:
            description = decode(row[1])
            compatibility = _read(json.loads(row[4]))
        except CompiledError:
            _fail("JOB_BUNDLE")
            raise
        if (
            content_pin(row[1]) != row[2]
            or description.producer != row[3]
            or description.compatibility != compatibility
        ):
            _fail("JOB_BUNDLE")
    for identity, row in bindings.items():
        slots = _canonical(row[2])
        try:
            values = [scalar_read(item) for item in _canonical(row[3])]
        except CompiledError:
            _fail("BINDING_VECTOR")
            raise
        if (
            identity not in created
            or len(values) != len(slots)
            or any(v.tag != s[1] for v, s in zip(values, slots))
        ):
            _fail("BINDING_VECTOR")
    for identity, row in generations.items():
        description = dict(_canonical(row[5]))
        job = jobs[row[1]]
        if (
            identity not in created
            or description.get("content_pin") != job[2]
            or description.get("producer") != job[3]
            or description.get("compatibility") != _canonical(job[4])
            or description.get("slots") != _canonical(bindings[row[2]][2])
            or description.get("target", [None] * 3)[2] != row[3]
        ):
            _fail("GENERATION_DESCRIPTION")
    ordinals: dict[str, list[int]] = {}
    for identity, row in attempts.items():
        if identity not in created:
            _fail("ATTEMPT_HISTORY")
        ordinals.setdefault(row[1], []).append(row[3])
    if any(sorted(o) != list(range(1, len(o) + 1)) for o in ordinals.values()):
        _fail("ATTEMPT_ORDINAL")
    if any(("terminal", a) not in created for a in terminals):
        _fail("TERMINAL_HISTORY")
    counts = _verify_capture(workspace, data, events, created) if capture else {}
    return counts | {
        "jobs": len(jobs),
        "bindings": len(bindings),
        "generations": len(generations),
        "attempts": len(attempts),
        "terminals": len(terminals),
        "operations": len(data["operation"]),
    }


def _verify_capture(workspace, data, events, created) -> dict:
    """Replay S12 history: one capture attempt, files named before members, frontiers."""
    from pietto._project.project_job_capture import frontier

    captures = {r[0]: r for r in data["capture"]}
    chunks = {r[0]: r for r in data["chunk"]}
    checkpoints = {r[0]: r for r in data["checkpoint"]}
    ends = {r[0]: r for r in data["capture_end"]}
    retentions = {r[0]: r for r in data["retention"]}
    releases = {r[0]: r for r in data["retention_release"]}
    members: dict[str, set] = {}
    for checkpoint, chunk, generation in data["checkpoint_member"]:
        if checkpoints[checkpoint][2] != generation or chunks[chunk][2] != generation:
            _fail("CHECKPOINT_MEMBER")
        members.setdefault(checkpoint, set()).add(chunk)
    attempts, generations = data["attempt"], data["generation"]
    consumers = {r[0]: r for r in data.get("consumer", ())}
    sessions = {r[0]: r for r in data.get("replay_session", ())}
    issuances = {r[0]: r for r in data.get("issuance", ())}
    acknowledgements = {r[0]: r for r in data.get("acknowledgement", ())}
    # Replayed S13 state: acknowledged frontier, latest session and its single
    # outstanding issuance, per-owner ordinals.
    progress: dict[str, int] = {}
    newest: dict[str, str] = {}
    outstanding: dict[str, str | None] = {}
    ordinals: dict[str, int] = {}
    seen: dict[object, int] = {}
    latest: dict[str, tuple[int, set]] = {}

    def replay(sequence, kind, job, request, result, epoch, instance):
        """One S13 operation against raw rows and the replayed consumer state."""
        if kind == "register_consumer":
            row = consumers.get(request.get("consumer"))
            retention = retentions.get(result.get("retention"))
            checkpoint = checkpoints.get(request.get("checkpoint"))
            generation = request.get("generation")
            scope = json.dumps(
                {
                    "consumer": request.get("consumer"),
                    "purpose": request.get("purpose"),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            end = ends.get(generation)
            if (
                row is None
                or retention is None
                or checkpoint is None
                or row[0] in seen
                or retention[0] in seen
                or seen.get(checkpoint[0], sequence) >= sequence
                or generation not in generations
                or row[1:]
                != (
                    job,
                    generation,
                    checkpoint[0],
                    generations[generation][2],
                    retention[0],
                    request.get("scope"),
                    request.get("extent"),
                    request.get("purpose"),
                    request.get("not_after"),
                    epoch,
                    instance,
                )
                or retention[1:]
                != (job, generation, checkpoint[0], scope, epoch, instance)
                or checkpoint[1:3] != (job, generation)
                or row[7] != checkpoint[4]
                or result
                != {
                    "checkpoint": checkpoint[0],
                    "consumer": row[0],
                    "extent": row[7],
                    "retention": retention[0],
                    "revision": result.get("revision"),
                }
                or (
                    row[6] == "complete_capture"
                    and (
                        end is None
                        or seen.get(("end", generation), sequence) >= sequence
                        or (end[1], end[2]) != (row[7], "EOF")
                    )
                )
            ):
                _fail("CONSUMER_HISTORY")
            seen[row[0]] = seen[retention[0]] = sequence
            progress[row[0]] = ordinals[row[0]] = 0
            return
        if kind == "open_replay":
            row = sessions.get(result.get("session"))
            consumer = consumers.get(request.get("consumer"))
            if (
                row is None
                or consumer is None
                or row[0] in seen
                or seen.get(consumer[0], sequence) >= sequence
                or consumer[1] != job
                or ("release", consumer[5]) in seen
                or row[1:]
                != (
                    consumer[0],
                    ordinals[consumer[0]] + 1,
                    progress[consumer[0]],
                    request.get("accepted_at"),
                    request.get("seconds"),
                    request.get("batch_rows"),
                    epoch,
                    instance,
                )
                or (result.get("ordinal"), result.get("position")) != (row[2], row[3])
            ):
                _fail("SESSION_HISTORY")
            seen[row[0]] = sequence
            ordinals[consumer[0]] += 1
            newest[consumer[0]] = row[0]
            outstanding[row[0]] = None
            ordinals[row[0]] = 0
            return
        if kind == "issue_delivery":
            row = issuances.get(result.get("delivery"))
            session = sessions.get(request.get("session"))
            if (
                row is None
                or session is None
                or row[0] in seen
                or session[0] not in seen
                or newest.get(session[1]) != session[0]
                or outstanding.get(session[0]) is not None
                or (session[7], session[8]) != (epoch, instance)
                or ("release", consumers[session[1]][5]) in seen
                or request.get("consumer") != session[1]
                or row[1:]
                != (
                    session[1],
                    session[0],
                    ordinals[session[0]] + 1,
                    request.get("start"),
                    request.get("stop"),
                    epoch,
                )
                or (result.get("ordinal"), result.get("start"), result.get("stop"))
                != (row[3], row[4], row[5])
                or row[4] != progress[session[1]]
                or row[5] > consumers[session[1]][7]
                or row[5] - row[4] > session[6]
            ):
                _fail("ISSUANCE_HISTORY")
            seen[row[0]] = sequence
            ordinals[session[0]] += 1
            outstanding[session[0]] = row[0]
            return
        issued = issuances.get(request.get("delivery"))
        row = acknowledgements.get(request.get("delivery"))
        if (
            row is None
            or issued is None
            or ("ack", row[0]) in seen
            or issued[0] not in seen
            or outstanding.get(issued[2]) != issued[0]
            or newest.get(issued[1]) != issued[2]
            or (sessions[issued[2]][7], sessions[issued[2]][8]) != (epoch, instance)
            or ("release", consumers[issued[1]][5]) in seen
            or row[1:]
            != (issued[1], issued[2], issued[4], issued[5], issued[4] or None, epoch)
            or (
                request.get("consumer"),
                request.get("session"),
                request.get("start"),
                request.get("stop"),
            )
            != (issued[1], issued[2], issued[4], issued[5])
            or issued[4] != progress[issued[1]]
            or (result.get("delivery"), result.get("position"))
            != (issued[0], issued[5])
        ):
            _fail("ACK_HISTORY")
        seen[("ack", row[0])] = sequence
        outstanding[issued[2]] = None
        progress[issued[1]] = issued[5]

    for sequence, kind, job, request, result, epoch, instance in events:
        publisher = [epoch, instance]
        generation = request.get("generation")
        if kind in REPLAY_KINDS:
            replay(sequence, kind, job, request, result, epoch, instance)
            continue
        if kind == "begin_capture":
            row = captures.get(generation)
            attempt = attempts.get(request.get("attempt"))
            if (
                row is None
                or ("capture", generation) in seen
                or attempt is None
                or row[1:]
                != (
                    job,
                    request.get("attempt"),
                    request.get("kind"),
                    request.get("contract"),
                    request.get("scheme"),
                    epoch,
                    instance,
                )
                or (attempt[1], attempt[2], [attempt[4], attempt[5]])
                != (generation, job, publisher)
                or created.get(attempt[0], sequence) >= sequence
                or created.get(("terminal", attempt[0]), sequence + 1) < sequence
                or result.get("capture") != generation
                or generations[generation][1] != job
            ):
                _fail("CAPTURE_HISTORY")
            seen[("capture", generation)] = sequence
        elif kind == "publish_chunk":
            row = chunks.get(request.get("chunk"))
            capture = captures.get(generation)
            if (
                row is None
                or capture is None
                or row[0] in seen
                or seen.get(("capture", generation), sequence) >= sequence
                or row[1:]
                != (
                    job,
                    generation,
                    request.get("attempt"),
                    request.get("start"),
                    request.get("stop"),
                    request.get("batches"),
                    request.get("file"),
                    request.get("bytes"),
                    request.get("digest"),
                    request.get("descriptor"),
                    epoch,
                    instance,
                )
                or (capture[2], capture[6], capture[7]) != (row[3], epoch, instance)
                or created.get(("terminal", row[3]), sequence + 1) < sequence
                or row[7] != row[0] + ".chunk"
            ):
                _fail("CHUNK_HISTORY")
            descriptor = _canonical(row[10], ascii=True)
            if (
                type(descriptor) is not dict
                or tuple(sorted(descriptor)) != DESCRIPTOR
                or descriptor["format"] != "pietto.result-chunk.v1"
                or (
                    descriptor["chunk"],
                    descriptor["generation"],
                    descriptor["job"],
                    descriptor["attempt"],
                    descriptor["start"],
                    descriptor["stop"],
                    descriptor["rows"],
                    descriptor["batches"],
                    descriptor["contract"],
                    descriptor["kind"],
                    descriptor["workspace"],
                    descriptor["binding"],
                )
                != (
                    row[0],
                    generation,
                    job,
                    row[3],
                    row[4],
                    row[5],
                    row[5] - row[4],
                    row[6],
                    capture[4],
                    capture[3],
                    workspace.identity,
                    generations[generation][2],
                )
                or (descriptor["coordinates"] is None) != (capture[3] == "ORDINARY")
                or (row[4] == row[5])
                != (descriptor["terminal"] == "EOF" and row[6] == 0)
                or (descriptor["terminal"] not in (None, "EOF"))
            ):
                _fail("CHUNK_DESCRIPTOR")
            ordinal, previous = latest.get(generation, (0, set()))
            ranges = [(chunks[m][4], chunks[m][5]) for m in previous]
            start, stop = row[4], row[5]
            if (start == stop and (start or ranges)) or any(
                a == b or (a < stop and start < b) for a, b in ranges
            ):
                _fail("CHUNK_OVERLAP")
            end = ends.get(generation)
            if (
                end is not None
                and seen.get(("end", generation), sequence) < sequence
                and stop > end[1]
            ):
                _fail("CHUNK_EXTENT")
            checkpoint = checkpoints.get(result.get("checkpoint"))
            current = previous | {row[0]}
            extents = ranges + [(start, stop)]
            if (
                checkpoint is None
                or checkpoint[0] in seen
                or result.get("chunk") != row[0]
                or checkpoint[1:]
                != (
                    job,
                    generation,
                    ordinal + 1,
                    frontier(extents),
                    len(current),
                    sum(b - a for a, b in extents),
                    epoch,
                )
                or members.get(checkpoint[0]) != current
                or (
                    result.get("ordinal"),
                    result.get("frontier"),
                    result.get("members"),
                )
                != (ordinal + 1, checkpoint[4], len(current))
            ):
                _fail("CHECKPOINT_HISTORY")
            seen[row[0]] = seen[checkpoint[0]] = sequence
            latest[generation] = (ordinal + 1, current)
        elif kind == "end_capture":
            row = ends.get(generation)
            if (
                row is None
                or ("end", generation) in seen
                or seen.get(("capture", generation), sequence) >= sequence
                or row[1:]
                != (
                    request.get("observed"),
                    request.get("source"),
                    request.get("staged"),
                    epoch,
                )
                or (captures[generation][6], captures[generation][7])
                != (epoch, instance)
                or max(
                    (chunks[m][5] for m in latest.get(generation, (0, ()))[1]),
                    default=0,
                )
                > row[1]
            ):
                _fail("END_HISTORY")
            seen[("end", generation)] = sequence
        elif kind == "retain_checkpoint":
            row = retentions.get(result.get("retention"))
            if (
                row is None
                or row[0] in seen
                or row[1:]
                != (
                    job,
                    generation,
                    result.get("checkpoint"),
                    request.get("scope"),
                    epoch,
                    instance,
                )
                or seen.get(row[3], sequence) >= sequence
                or request.get("checkpoint") not in (None, row[3])
            ):
                _fail("RETENTION_HISTORY")
            seen[row[0]] = sequence
        else:
            retention = request.get("retention")
            row = releases.get(retention)
            if (
                row is None
                or ("release", retention) in seen
                or seen.get(retention, sequence) >= sequence
                or retentions[retention][1] != job
                or row[1:] != (epoch, instance)
                or result.get("retention") != retention
            ):
                _fail("RELEASE_HISTORY")
            seen[("release", retention)] = sequence
    if (
        any(("capture", g) not in seen for g in captures)
        or any(c not in seen for c in chunks)
        or any(c not in seen for c in checkpoints)
        or any(("end", g) not in seen for g in ends)
        or any(r not in seen for r in retentions)
        or any(("release", r) not in seen for r in releases)
    ):
        _fail("CAPTURE_ROWS")
    if (
        any(c not in seen for c in consumers)
        or any(s not in seen for s in sessions)
        or any(i not in seen for i in issuances)
        or any(("ack", a) not in seen for a in acknowledgements)
    ):
        _fail("REPLAY_ROWS")
    counts = {
        "captures": len(captures),
        "chunks": len(chunks),
        "checkpoints": len(checkpoints),
        "retentions": len(retentions),
        "releases": len(releases),
    }
    if "consumer" in data:
        counts |= {
            "consumers": len(consumers),
            "sessions": len(sessions),
            "issuances": len(issuances),
            "acknowledgements": len(acknowledgements),
        }
    return counts
