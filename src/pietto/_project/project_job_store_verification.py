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
EXTRACTION_KINDS = (
    "begin_extraction",
    "begin_continuation",
    "reconcile_extraction",
    "end_continuation",
)
EXTRACTION_TABLES = ("extraction", "continuation", "reconciliation", "continuation_end")
DELIVERY_KINDS = (
    "register_stream",
    "adopt_window",
    "open_stream",
    "issue_stream",
    "confirm_sink",
    "retire_stream",
)
DELIVERY_TABLES = (
    "stream",
    "stream_window",
    "stream_session",
    "stream_issuance",
    "sink_observation",
    "stream_retirement",
)
PUBLICATION_KINDS = ("publish_generation",)
PUBLICATION_TABLES = ("closing_observation", "publication")
# Each route's own normal cleanup term and the positive guard states (S16).
CLEAN = {
    "postgres_rows": "CLOSED",
    "postgres_adbc": "LOCAL_CLOSED_REMOTE_UNOBSERVED",
    "mysql_rows": "LOCAL_CLOSED_REMOTE_UNOBSERVED",
}
GUARDS = ("STATIC", "FULFILLED")
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


def _category(value) -> bool:
    """A failure category [phase, kind]; never a message."""
    return (
        type(value) is list and len(value) == 2 and all(type(v) is str for v in value)
    )


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
    extraction = supports(workspace, "extraction-resume")
    delivery = supports(workspace, "cooperative-delivery")
    publication = supports(workspace, "complete-publication")
    kinds = (
        KINDS
        + (CAPTURE_KINDS if capture else ())
        + (REPLAY_KINDS if replay else ())
        + (EXTRACTION_KINDS if extraction else ())
        + (DELIVERY_KINDS if delivery else ())
        + (PUBLICATION_KINDS if publication else ())
    )

    def snapshot(c) -> dict[str, Any]:
        tables: dict[str, Any] = {
            name: tuple(c.execute(f"SELECT * FROM {name}"))
            for name in (CAPTURE_TABLES if capture else ())
            + (REPLAY_TABLES if replay else ())
            + (EXTRACTION_TABLES if extraction else ())
            + (DELIVERY_TABLES if delivery else ())
            + (PUBLICATION_TABLES if publication else ())
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
    closings = {r[0]: r for r in data.get("closing_observation", ())}
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
        elif (
            kind
            in CAPTURE_KINDS
            + REPLAY_KINDS
            + EXTRACTION_KINDS
            + DELIVERY_KINDS
            + PUBLICATION_KINDS
        ):
            # Data progress, saved reads, delivery and publication need an
            # ACTIVE job; ends, retention, releases and stream retirement are
            # control.
            if (
                kind
                in CAPTURE_KINDS[:2]
                + REPLAY_KINDS
                + EXTRACTION_KINDS[:3]
                + DELIVERY_KINDS[:5]
                + PUBLICATION_KINDS
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
            observation = request.get("observation")
            if publication and terminal[1] == "OUTCOME":
                # v6: the owner's closing observation, in the terminal's transaction.
                closing = closings.get(attempt)
                if (
                    closing is None
                    or type(observation) is not dict
                    or tuple(sorted(observation))
                    != ("cleanup", "closed", "failure", "rows")
                    or observation["closed"] is not True
                    or type(observation["rows"]) is not int
                    or not (
                        observation["failure"] is None
                        or _category(observation["failure"])
                    )
                    or type(observation["cleanup"]) is not list
                    or not all(_category(item) for item in observation["cleanup"])
                    or (
                        closing[1:5],
                        None if closing[5] is None else _canonical(closing[5]),
                        _canonical(closing[6]),
                        closing[7],
                    )
                    != (
                        (row[1], job, 1, observation["rows"]),
                        observation["failure"],
                        observation["cleanup"],
                        current["epoch"],
                    )
                ):
                    _fail("CLOSING_HISTORY")
                created[("closing", attempt)] = sequence
            elif observation is not None or attempt in closings:
                _fail("CLOSING_HISTORY")
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
    if any(("closing", a) not in created for a in closings):
        _fail("CLOSING_HISTORY")
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
    extractions = {r[0]: r for r in data.get("extraction", ())}
    continuations = {r[0]: r for r in data.get("continuation", ())}
    reconciliations = {r[0]: r for r in data.get("reconciliation", ())}
    finished = {r[0]: r for r in data.get("continuation_end", ())}
    # Replayed v4 state: each generation's latest checkpoint and the one
    # complete extent of any normal source end recorded so far.
    head: dict[str, str] = {}
    eof: dict[str, int] = {}
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
                or (row[6] == "complete_capture" and eof.get(generation) != row[7])
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

    deliver = _delivery_replay(data, seen, members)
    publish = _publication_replay(data, seen, members, created, head, eof, latest)
    for sequence, kind, job, request, result, epoch, instance in events:
        publisher = [epoch, instance]
        generation = request.get("generation")
        if kind in REPLAY_KINDS:
            replay(sequence, kind, job, request, result, epoch, instance)
            continue
        if kind in DELIVERY_KINDS:
            deliver(sequence, kind, job, request, result, epoch, instance)
            continue
        if kind in PUBLICATION_KINDS:
            publish(sequence, job, request, result, epoch, instance)
            continue
        if kind in ("begin_capture", "begin_extraction"):
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
            if kind == "begin_extraction":
                extraction = extractions.get(generation)
                specification = _canonical(extraction[3]) if extraction else {}
                if (
                    extraction is None
                    or ("extraction", generation) in seen
                    or extraction[1:]
                    != (
                        job,
                        request.get("attempt"),
                        request.get("specification"),
                        request.get("qualification"),
                        epoch,
                        instance,
                    )
                    or _canonical(extraction[4]) is None
                    or row[3] != "REFINED"
                    or (
                        specification.get("kind"),
                        specification.get("contract"),
                        specification.get("scheme"),
                        specification.get("route"),
                        specification.get("isolation"),
                    )
                    != ("REFINED", row[4], row[5], *generations[generation][3:5])
                ):
                    _fail("EXTRACTION_HISTORY")
                seen[("extraction", generation)] = sequence
        elif kind == "begin_continuation":
            attempt = request.get("attempt")
            row = continuations.get(attempt)
            owner = attempts.get(attempt)
            extraction = extractions.get(generation)
            _ordinal, current = latest.get(generation, (0, set()))
            ranges = sorted((chunks[m][4], chunks[m][5]) for m in current)
            if (
                row is None
                or owner is None
                or extraction is None
                or ("continuation", attempt) in seen
                or ("extraction", generation) not in seen
                or extraction[2] == attempt
                or (owner[1], owner[2], [owner[4], owner[5]])
                != (generation, job, publisher)
                or created.get(attempt, sequence) >= sequence
                or created.get(("terminal", attempt), sequence + 1) < sequence
                or row[1:]
                != (
                    job,
                    generation,
                    request.get("predecessor"),
                    request.get("frontier"),
                    request.get("reach"),
                    request.get("members"),
                    request.get("rows"),
                    epoch,
                    instance,
                )
                or row[3] != head.get(generation)
                or row[4:8]
                != (
                    frontier(ranges),
                    max((b for _a, b in ranges), default=0),
                    len(current),
                    sum(b - a for a, b in ranges),
                )
                or request.get("qualification") != extraction[4]
                or result.get("continuation") != attempt
            ):
                _fail("CONTINUATION_HISTORY")
            seen[("continuation", attempt)] = sequence
        elif kind == "reconcile_extraction":
            attempt = request.get("attempt")
            row = reconciliations.get(attempt)
            frozen = continuations.get(attempt)
            if (
                row is None
                or frozen is None
                or ("reconciled", attempt) in seen
                or ("continuation", attempt) not in seen
                or frozen[2] != generation
                or (frozen[8], frozen[9]) != (epoch, instance)
                or created.get(("terminal", attempt), sequence + 1) < sequence
                or head.get(generation) != frozen[3]
                or request.get("predecessor") != frozen[3]
                or row[1:]
                != (
                    request.get("position"),
                    request.get("matched"),
                    epoch,
                )
                or row[1] < frozen[5]
                or row[2] != frozen[7]
                or (result.get("position"), result.get("reconciliation"))
                != (row[1], attempt)
            ):
                _fail("RECONCILIATION_HISTORY")
            seen[("reconciled", attempt)] = sequence
        elif kind == "end_continuation":
            attempt = request.get("attempt")
            row = finished.get(attempt)
            frozen = continuations.get(attempt)
            _ordinal, current = latest.get(generation, (0, set()))
            ranges = sorted((chunks[m][4], chunks[m][5]) for m in current)
            if (
                row is None
                or frozen is None
                or ("finished", attempt) in seen
                or ("continuation", attempt) not in seen
                or frozen[2] != generation
                or (frozen[8], frozen[9]) != (epoch, instance)
                or row[1:]
                != (
                    generation,
                    request.get("observed"),
                    request.get("source"),
                    request.get("staged"),
                    result.get("checkpoint"),
                    epoch,
                )
                or result.get("observed") != row[2]
                or (
                    row[3] == "EOF"
                    and (
                        ("reconciled", attempt) not in seen
                        or row[5] != head.get(generation)
                        or not current
                        or frontier(ranges) != row[2]
                        or sum(b - a for a, b in ranges) != row[2]
                        or eof.get(generation, row[2]) != row[2]
                    )
                )
                or (row[3] != "EOF" and row[5] is not None)
            ):
                _fail("END_HISTORY")
            if row[3] == "EOF":
                eof[generation] = row[2]
            seen[("finished", attempt)] = sequence
        elif kind == "publish_chunk":
            row = chunks.get(request.get("chunk"))
            capture = captures.get(generation)
            # The original capture attempt, or a reconciled continuation whose
            # own publisher adds chunks after its frozen predecessor.
            frozen = continuations.get(row[3]) if row else None
            ordinal, previous = latest.get(generation, (0, set()))
            producer = (
                capture is not None
                and row is not None
                and (
                    (capture[2], capture[6], capture[7]) == (row[3], epoch, instance)
                    or frozen is not None
                    and frozen[2] == generation
                    and ("reconciled", row[3]) in seen
                    and (frozen[8], frozen[9]) == (epoch, instance)
                    and members.get(frozen[3], set()) <= previous
                    and all(
                        chunks[m][3] == row[3]
                        for m in previous - members.get(frozen[3], set())
                    )
                )
            )
            if (
                row is None
                or capture is None
                or not producer
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
            ranges = [(chunks[m][4], chunks[m][5]) for m in previous]
            start, stop = row[4], row[5]
            if (start == stop and (start or ranges)) or any(
                a == b or (a < stop and start < b) for a, b in ranges
            ):
                _fail("CHUNK_OVERLAP")
            end = ends.get(generation)
            if (
                end is not None
                and row[3] == capture[2]
                and seen.get(("end", generation), sequence) < sequence
                and stop > end[1]
            ) or stop > eof.get(generation, stop):
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
            head[generation] = checkpoint[0]
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
                or (row[2] == "EOF" and eof.get(generation, row[1]) != row[1])
            ):
                _fail("END_HISTORY")
            if row[2] == "EOF":
                eof[generation] = row[1]
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
    if (
        any(("extraction", g) not in seen for g in extractions)
        or any(("continuation", a) not in seen for a in continuations)
        or any(("reconciled", a) not in seen for a in reconciliations)
        or any(("finished", a) not in seen for a in finished)
    ):
        _fail("EXTRACTION_ROWS")
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
    if "extraction" in data:
        counts |= {
            "extractions": len(extractions),
            "continuations": len(continuations),
            "reconciliations": len(reconciliations),
            "continuation_ends": len(finished),
        }
    if "stream" in data:
        counts |= deliver(None, "rows", None, None, None, None, None)
    if "publication" in data:
        counts |= publish(None, None, None, None, None, None)
    return counts


def _delivery_replay(data, seen, members):
    """S15 history against raw rows: registration, window chain, sessions,
    issuances, observations and retirement, with the replayed frontier."""
    from pietto._project.project_job_capture import frontier

    streams = {r[0]: r for r in data.get("stream", ())}
    windows = {(r[0], r[1]): r for r in data.get("stream_window", ())}
    sessions = {r[0]: r for r in data.get("stream_session", ())}
    issued = {r[0]: r for r in data.get("stream_issuance", ())}
    observations = {(r[0], r[1]): r for r in data.get("sink_observation", ())}
    retirements = {r[0]: r for r in data.get("stream_retirement", ())}
    checkpoints = {r[0]: r for r in data["checkpoint"]}
    retentions = {r[0]: r for r in data["retention"]}
    releases = {r[0]: r for r in data["retention_release"]}
    consumers = {r[0]: r for r in data.get("consumer", ())}
    deliveries = {r[0]: r for r in data.get("issuance", ())}
    captures = {r[0]: r for r in data["capture"]}
    generations = data["generation"]
    chain: dict[str, list] = {}
    newest: dict[str, str] = {}
    counter: dict[str, int] = {}
    last: dict[str, tuple[int, int]] = {}
    observed: dict[str, set] = {}
    covered: dict[str, set] = {}

    def reached(stream) -> int:
        return frontier([(p, p + 1) for p in observed.get(stream, ())])

    def live(sequence, stream, session, job, epoch, instance):
        row = sessions.get(session)
        if (
            row is None
            or stream not in streams
            or streams[stream][1] != job
            or seen.get(session, sequence) >= sequence
            or row[1] != stream
            or newest.get(stream) != session
            or (row[8], row[9]) != (epoch, instance)
            or ("retired", stream) in seen
        ):
            _fail("STREAM_SESSION_HISTORY")
        return row

    def deliver(sequence, kind, job, request, result, epoch, instance):
        if kind == "rows":
            if (
                any(s not in seen for s in streams)
                or any(("window",) + w not in seen for w in windows)
                or any(s not in seen for s in sessions)
                or any(i not in seen for i in issued)
                or any(("observed",) + o not in seen for o in observations)
                or any(("retired", s) not in seen for s in retirements)
            ):
                _fail("DELIVERY_ROWS")
            return {
                "streams": len(streams),
                "windows": len(windows),
                "stream_sessions": len(sessions),
                "stream_issuances": len(issued),
                "sink_observations": len(observations),
                "retirements": len(retirements),
            }
        if kind == "register_stream":
            row = streams.get(result.get("stream"))
            generation = request.get("generation")
            capture = captures.get(generation)
            shape = _canonical(request.get("layout") or "null") or {}
            if (
                row is None
                or row[0] in seen
                or capture is None
                or seen.get(("capture", generation), sequence) >= sequence
                or ("destination", *row[2:3], *row[8:11]) in seen
                or row[1:]
                != (
                    job,
                    generation,
                    request.get("binding"),
                    request.get("route"),
                    request.get("contract"),
                    request.get("scheme"),
                    request.get("layout"),
                    request.get("sink"),
                    request.get("namespace"),
                    request.get("epoch"),
                    request.get("retention"),
                    request.get("purpose"),
                    epoch,
                    instance,
                )
                or (row[3], row[4]) != generations[generation][2:4]
                or (row[5], row[6]) != (capture[4], capture[5])
                or type(shape) is not dict
                or shape.get("contract") != row[5]
                or shape.get("scheme") != (None if row[6] == "null" else row[6])
            ):
                _fail("STREAM_HISTORY")
            seen[row[0]] = seen[("destination", *row[2:3], *row[8:11])] = sequence
            chain[row[0]] = []
            observed[row[0]] = set()
            covered[row[0]] = set()
            return
        stream = request.get("stream")
        if kind == "retire_stream":
            row = retirements.get(stream)
            windows_of = chain.get(stream, [])
            fresh = [w[5] for w in windows_of if ("release", w[5]) not in seen]
            if (
                row is None
                or stream not in streams
                or streams[stream][1] != job
                or ("retired", stream) in seen
                or covered[stream] - observed[stream]
                or row[1:] != (reached(stream), epoch, instance)
                or result.get("released") != len(fresh)
                or result.get("position") != row[1]
                or any(
                    releases.get(r) is None or releases[r][1:] != (epoch, instance)
                    for r in fresh
                )
            ):
                _fail("RETIREMENT_HISTORY")
            for retention in fresh:
                seen[("release", retention)] = sequence
            seen[("retired", stream)] = sequence
            return
        if kind == "open_stream":
            row = sessions.get(result.get("session"))
            windows_of = chain.get(stream, [])
            latest = windows_of[-1] if windows_of else None
            if (
                row is None
                or row[0] in seen
                or stream not in streams
                or streams[stream][1] != job
                or ("retired", stream) in seen
                or row[1:]
                != (
                    stream,
                    counter.get(stream, 0) + 1,
                    reached(stream),
                    request.get("accepted_at"),
                    request.get("seconds"),
                    request.get("batch_rows"),
                    request.get("purpose"),
                    epoch,
                    instance,
                )
                or (result.get("ordinal"), result.get("position")) != (row[2], row[3])
                or (
                    latest is not None
                    and (
                        ("release", latest[5]) in seen
                        or request.get("checkpoint") not in (None, latest[4])
                    )
                )
            ):
                _fail("STREAM_SESSION_HISTORY")
            seen[row[0]] = sequence
            counter[stream] = row[2]
            newest[stream] = row[0]
            counter[row[0]] = 0
            return
        session = live(sequence, stream, request.get("session"), job, epoch, instance)
        if kind == "adopt_window":
            windows_of = chain[stream]
            latest = windows_of[-1] if windows_of else None
            ordinal = len(windows_of) + 1
            row = windows.get((stream, ordinal))
            checkpoint = checkpoints.get(request.get("checkpoint"))
            retention = retentions.get(result.get("retention"))
            generation = streams[stream][2]
            if (
                row is None
                or checkpoint is None
                or retention is None
                or retention[0] in seen
                or seen.get(checkpoint[0], sequence) >= sequence
                or checkpoint[2] != generation
                or row[1:]
                != (
                    ordinal,
                    None if latest is None else latest[1],
                    generation,
                    checkpoint[0],
                    retention[0],
                    0 if latest is None else latest[7],
                    checkpoint[4],
                    epoch,
                )
                or retention[1:]
                != (
                    job,
                    generation,
                    checkpoint[0],
                    request.get("scope"),
                    epoch,
                    instance,
                )
                or (
                    result.get("checkpoint"),
                    result.get("ordinal"),
                    result.get("start"),
                    result.get("stop"),
                )
                != (checkpoint[0], ordinal, row[6], row[7])
                or (
                    latest is not None
                    and (
                        latest[4] == checkpoint[0]
                        or reached(stream) < latest[7]
                        or checkpoint[3] <= checkpoints[latest[4]][3]
                        or not members.get(latest[4], set())
                        <= members.get(checkpoint[0], set())
                        or row[7] < latest[7]
                    )
                )
            ):
                _fail("WINDOW_HISTORY")
            seen[("window", stream, ordinal)] = seen[retention[0]] = sequence
            windows_of.append(row)
            return
        if kind == "issue_stream":
            row = issued.get(result.get("issuance"))
            previous = last.get(session[0])
            start, stop = request.get("start"), request.get("stop")
            window, delivery = request.get("window"), request.get("delivery")
            windows_of = chain[stream]
            if (
                row is None
                or row[0] in seen
                or row[1:]
                != (
                    stream,
                    session[0],
                    counter[session[0]] + 1,
                    window,
                    delivery,
                    start,
                    stop,
                    request.get("digest"),
                    epoch,
                )
                or (result.get("start"), result.get("stop")) != (start, stop)
                or (
                    previous is not None
                    and not set(range(*previous)) <= observed[stream]
                )
            ):
                _fail("STREAM_ISSUANCE_HISTORY")
            if window is not None:
                latest = windows_of[-1] if windows_of else None
                if (
                    latest is None
                    or latest[1] != window
                    or ("release", latest[5]) in seen
                    or start != reached(stream)
                    or stop > latest[7]
                ):
                    _fail("STREAM_ISSUANCE_HISTORY")
            else:
                found = deliveries.get(delivery)
                consumer = consumers.get(found[1]) if found else None
                if (
                    found is None
                    or consumer is None
                    or found[0] not in seen
                    or ("ack", delivery) in seen
                    or (found[4], found[5]) != (start, stop)
                    or consumer[2] != streams[stream][2]
                    or ("release", consumer[5]) in seen
                ):
                    _fail("STREAM_ISSUANCE_HISTORY")
            seen[row[0]] = sequence
            counter[session[0]] += 1
            last[session[0]] = (start, stop)
            covered[stream].update(range(start, stop))
            return
        row = issued.get(request.get("issuance"))
        added = 0
        if (
            row is None
            or row[0] not in seen
            or (row[1], row[2]) != (stream, session[0])
            or type(request.get("observations")) is not list
        ):
            _fail("OBSERVATION_HISTORY")
        for item in request["observations"]:
            position = item[0] if type(item) is list and len(item) == 6 else None
            stored = observations.get((stream, position))
            if position in observed[stream]:
                if stored is None or (stored[6], stored[8]) != (item[3], item[5]):
                    _fail("OBSERVATION_HISTORY")
                continue
            if (
                stored is None
                or not row[6] <= position < row[7]
                or stored[2:]
                != (
                    row[0],
                    session[0],
                    item[1],
                    item[2],
                    item[3],
                    item[4],
                    item[5],
                    epoch,
                )
            ):
                _fail("OBSERVATION_HISTORY")
            seen[("observed", stream, position)] = sequence
            observed[stream].add(position)
            added += 1
        if (result.get("confirmed"), result.get("position")) != (
            added,
            reached(stream),
        ):
            _fail("OBSERVATION_HISTORY")

    return deliver


def _covers(ranges, extent) -> bool:
    """Exactly [0, extent): contiguous non-empty extents, or the one [0, 0)."""
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


def _closed_well(outcome, closing, route, reference) -> bool:
    """The complete-result truth table over one raw terminal outcome and its
    closing observation row, re-derived here independently of the owner."""
    states = outcome.get("guard_states")
    return (
        outcome.get("source") == "EOF"
        and outcome.get("transaction") == "COMMIT_ACK"
        and outcome.get("remote_source_use_end") == "TRANSACTION_ACK"
        and outcome.get("delivery") == "COMPLETE"
        and outcome.get("cleanup") == CLEAN.get(route)
        and outcome.get("source_qualification") == "QUALIFIED"
        and outcome.get("transaction_opened") is True
        and type(states) is list
        and all(s in GUARDS for s in states)
        and outcome.get("structure") == "ACCEPTED"
        and outcome.get("deployment_acceptance")
        == "EXPLICIT_MANAGED_DEPLOYMENT_PREMISE"
        and outcome.get("route") == route
        and outcome.get("binding_reference") == reference
        and closing[5] is None
        and _canonical(closing[6]) == []
    )


def _publication_replay(data, seen, members, created, head, eof, latest):
    """S16 history against raw rows: each publication re-derived at its own
    point (closing observation, basis, extent, exact coverage, unreleased own
    protection, no open or later attempt) and nothing written to its
    generation afterwards."""
    publications = {r[0]: r for r in data.get("publication", ())}
    closings = {r[0]: r for r in data.get("closing_observation", ())}
    captures = {r[0]: r for r in data["capture"]}
    chunks = {r[0]: r for r in data["chunk"]}
    ends = {r[0]: r for r in data["capture_end"]}
    retentions = {r[0]: r for r in data["retention"]}
    continuations = {r[0]: r for r in data.get("continuation", ())}
    finished = {r[0]: r for r in data.get("continuation_end", ())}
    attempts, terminals = data["attempt"], data["terminal"]
    generations, operations = data["generation"], data["operation"]

    def publish(sequence, job, request, result, epoch, instance):
        if sequence is None:
            for generation, row in publications.items():
                at = seen.get(("publication", generation))
                later = (
                    [seen.get(c[0], 0) for c in chunks.values() if c[2] == generation]
                    + [seen.get(("end", generation), 0)]
                    + [
                        seen.get((name, a), 0)
                        for a, n in continuations.items()
                        if n[2] == generation
                        for name in ("continuation", "reconciled", "finished")
                    ]
                )
                if at is None or ("release", row[9]) in seen or max(later) > at:
                    _fail("PUBLICATION_ROWS")
            return {
                "closing_observations": len(closings),
                "publications": len(publications),
            }
        generation = request.get("generation")
        row = publications.get(generation)
        capture = captures.get(generation)
        closing = request.get("closing")
        attempt = attempts.get(closing)
        terminal = terminals.get(closing)
        observed = closings.get(closing)
        retention = retentions.get(request.get("retention"))
        checkpoint, extent = request.get("checkpoint"), request.get("extent")
        _ordinal, current = latest.get(generation, (0, set()))
        ranges = sorted((chunks[m][4], chunks[m][5]) for m in current)
        if (
            row is None
            or capture is None
            or attempt is None
            or terminal is None
            or observed is None
            or retention is None
        ):
            _fail("PUBLICATION_HISTORY")
        if closing == capture[2]:
            end = ends.get(generation)
            basis = "CAPTURE"
            based = (
                end is not None
                and seen.get(("end", generation), sequence) < sequence
                and (end[1], end[2]) == (extent, "EOF")
                and all(chunks[m][3] == closing for m in current)
            )
        else:
            frozen = continuations.get(closing)
            done = finished.get(closing)
            previous = members.get(frozen[3], set()) if frozen and frozen[3] else set()
            basis = "CONTINUATION"
            based = (
                frozen is not None
                and done is not None
                and frozen[2] == generation
                and seen.get(("reconciled", closing), sequence) < sequence
                and seen.get(("finished", closing), sequence) < sequence
                and (done[2], done[3], done[5]) == (extent, "EOF", checkpoint)
                and previous <= current
                and all(chunks[m][3] == closing for m in current - previous)
            )
        descriptor = {
            "basis": basis,
            "chunk": "pietto.result-chunk.v1",
            "coordinates": "pietto.coordinate-atoms.v1"
            if capture[3] == "REFINED"
            else None,
            "format": "pietto.publication.v1",
            "kind": capture[3],
            "workspace": data["workspace"][0][2],
        }
        if (
            not based
            or ("publication", generation) in seen
            or row[1:]
            != (
                job,
                generations[generation][2],
                checkpoint,
                extent,
                request.get("members"),
                capture[4],
                capture[5],
                closing,
                retention[0],
                request.get("descriptor"),
                operations[sequence - 1][1],
                epoch,
                instance,
            )
            or _canonical(row[10]) != descriptor
            or result
            != {
                "checkpoint": checkpoint,
                "closing": closing,
                "extent": extent,
                "generation": generation,
                "retention": retention[0],
                "revision": result.get("revision"),
            }
            or head.get(generation) != checkpoint
            or members.get(checkpoint) != current
            or len(current) != row[5]
            or not _covers(ranges, extent)
            or (attempt[1], attempt[2]) != (generation, job)
            or terminal[1] != "OUTCOME"
            or created.get(("closing", closing), sequence) >= sequence
            or not _closed_well(
                _canonical(terminal[3]),
                observed,
                generations[generation][3],
                attempt[6],
            )
            or observed[4] != extent
            or eof.get(generation) != extent
            or retention[1:4] != (job, generation, checkpoint)
            or seen.get(retention[0], sequence) >= sequence
            or ("release", retention[0]) in seen
            or any(
                a[1] == generation
                and created.get(("terminal", a[0]), sequence) >= sequence
                for a in attempts.values()
            )
        ):
            _fail("PUBLICATION_HISTORY")
        seen[("publication", generation)] = sequence

    return publish
