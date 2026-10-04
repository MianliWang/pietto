"""Independent complete-relation checks over raw job-store rows.

The checker replays the operation history from raw rows and S10's own scalar and
content codecs. It does not call the store's mutation or query functions, so a
coordinated re-encoding must still satisfy the fencing and identity laws.
"""

from __future__ import annotations

import json
from typing import NoReturn

from pietto._project.project_job_workspace import (
    FORMAT,
    JobStoreError,
    Workspace,
    read,
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


def _canonical(text: str):
    value = json.loads(text)
    if (
        json.dumps(
            value,
            ensure_ascii=False,
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

    def snapshot(c):
        return {
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
    if data["workspace"] != ((1, workspace.identity, FORMAT),):
        _fail("WORKSPACE")
    jobs, bindings, generations = data["job"], data["binding"], data["generation"]
    attempts, terminals = data["attempt"], data["terminal"]
    created: dict[object, int] = {}
    state: dict[str, dict] = {}
    for position, (sequence, identity, kind, job, request, result) in enumerate(
        data["operation"], 1
    ):
        if sequence != position or not valid_identity(identity, "op"):
            _fail("OPERATION_SEQUENCE")
        if kind not in KINDS or job not in jobs:
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
    return {
        "jobs": len(jobs),
        "bindings": len(bindings),
        "generations": len(generations),
        "attempts": len(attempts),
        "terminals": len(terminals),
        "operations": len(data["operation"]),
    }
