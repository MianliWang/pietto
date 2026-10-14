"""S17 independent checker and pure transition models; import acquires nothing.

The checker reads only raw evidence: SQLite backups (supported backup API),
chunk/staging file inventories, the runtime's own event logs, kill/cut
observations and literal oracles. It recomputes admission inequalities,
once-only settlement, claims, retirement order, protection roots, tombstones,
removals and event order itself; it never calls the product coordinator,
collector, classifier, availability or query functions, so a product defect
or a coordinated damage meets a recomputation, not a cached success field.

The models are small exhaustive state machines of the selected protocols,
independent of the implementation: the admission/settlement envelope and the
reader/collector lifetime exclusion. They are design checks, not proofs about
the code.
"""

from __future__ import annotations

from collections import deque
import json
import sqlite3

TABLES = (
    "job",
    "generation",
    "attempt",
    "attempt_terminal",
    "operation",
    "chunk",
    "checkpoint",
    "checkpoint_member",
    "capture",
    "capture_end",
    "retention",
    "retention_release",
    "consumer",
    "issuance",
    "acknowledgement",
    "stream",
    "stream_window",
    "stream_issuance",
    "sink_observation",
    "publication",
    "runtime_owner",
    "admission",
    "admission_settlement",
    "chunk_claim",
    "generation_retirement",
    "collection",
    "tombstone",
    "removal",
)
FIELDS = ("connections", "workers", "memory", "durable", "operations")


class CheckError(AssertionError):
    """One named law failed; the name is the designated rejecting control."""


def need(ok, law: str) -> None:
    if not ok:
        raise CheckError(law)


def load(path) -> dict:
    """Every relevant table of one closed store backup (read-only)."""
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return {
            name: [tuple(r) for r in connection.execute(f"SELECT * FROM {name}")]
            for name in TABLES
        }
    finally:
        connection.close()


def _ops(data):
    """Operation rows in commit order with decoded request/result."""
    return [
        (row[0], row[2], row[3], json.loads(row[4]), json.loads(row[5]))
        for row in sorted(data["operation"])
    ]


def check_store(data) -> dict:
    """Recompute every S17 relation from raw rows (laws named per failure)."""
    claims = {r[0]: r for r in data["chunk_claim"]}
    admissions = {r[0]: r for r in data["admission"]}
    settlements = {r[0]: r for r in data["admission_settlement"]}
    chunks = {r[0]: r for r in data["chunk"]}
    jobs = {r[0]: r for r in data["job"]}
    terminals = {r[0]: r for r in data["attempt_terminal"]}
    retired = {r[0] for r in data["generation_retirement"]}
    published = {r[0] for r in data["publication"]}
    released = {r[0] for r in data["retention_release"]}
    members: dict[str, set] = {}
    for checkpoint, chunk, _generation in data["checkpoint_member"]:
        members.setdefault(checkpoint, set()).add(chunk)
    claimed: dict[str, int] = {}
    for row in claims.values():
        claimed[row[4]] = claimed.get(row[4], 0) + row[5]
    # Allowance and once-only settlement.
    for identity, row in admissions.items():
        vector = json.loads(row[4])
        need(set(vector) == set(FIELDS), "ADMISSION_VECTOR")
        need(vector["durable"] == row[5], "ADMISSION_VECTOR")
        need(claimed.get(identity, 0) <= row[5], "ALLOWANCE")
    for identity, row in settlements.items():
        need(identity in admissions, "SETTLEMENT")
        need(row[3] == claimed.get(identity, 0), "SETTLEMENT")
        need(
            row[2]
            == ("RELEASED" if row[1] == admissions[identity][2] else "RECONCILED"),
            "SETTLEMENT",
        )
    # Every committed chunk was claimed first by its own attempt, exact size.
    for identity, row in chunks.items():
        held = claims.get(identity)
        if held is None:
            raise CheckError("CLAIM")
        need((held[2], held[3], held[5]) == (row[2], row[3], row[8]), "CLAIM")
    # Replayed order: claims before chunks, nothing after a retirement.
    sequence: dict = {}
    for seq, kind, _job, request, result in _ops(data):
        if kind == "claim_chunk":
            sequence[("claim", request["chunk"])] = seq
        elif kind == "publish_chunk":
            need(sequence.get(("claim", request["chunk"]), seq) < seq, "CLAIM_ORDER")
            need(("retired", request["generation"]) not in sequence, "RETIREMENT")
        elif kind == "retire_generation":
            generation = request["generation"]
            need(("published", generation) not in sequence, "RETIREMENT")
            sequence[("retired", generation)] = seq
        elif kind == "publish_generation":
            need(("retired", request["generation"]) not in sequence, "RETIREMENT")
            sequence[("published", request["generation"])] = seq
        elif kind in ("retain_checkpoint", "register_consumer", "adopt_window"):
            generation = request.get("generation") or _stream_generation(
                data, request.get("stream")
            )
            need(("retired", generation) not in sequence, "RETIREMENT")
        elif kind == "open_attempt":
            need(("retired", request["generation"]) not in sequence, "RETIREMENT")
        elif kind == "release_retention":
            _released_root(data, request["retention"], seq)
    need(not (retired & published), "RETIREMENT")
    # Roots now: latest checkpoint of non-retired generations, every unreleased
    # retention's checkpoint (consumer, window, preparation, publication, explicit).
    latest: dict[str, tuple[int, str]] = {}
    for row in data["checkpoint"]:
        if row[2] not in latest or row[3] > latest[row[2]][0]:
            latest[row[2]] = (row[3], row[0])
    protected = set()
    for generation, (_ordinal, checkpoint) in latest.items():
        if generation not in retired:
            protected |= members.get(checkpoint, set())
    for row in data["retention"]:
        if row[0] not in released:
            protected |= members.get(row[3], set())
    collections = {r[0]: r for r in data["collection"]}
    removals = {r[0]: r for r in data["removal"]}
    for chunk, row in {r[0]: r for r in data["tombstone"]}.items():
        need(row[1] in collections, "DECISION")
        held = claims.get(chunk)
        if held is None or held[2] != row[2]:
            raise CheckError("DECISION")
        if row[3] == "RETIRED":
            need(chunk in chunks, "ROOTS")
            need(row[2] in retired and row[2] not in published, "ROOTS")
            need(chunk not in protected, "ROOTS")
        else:
            need(chunk not in chunks, "ROOTS")
            need(
                held[3] in terminals or held[6] < jobs[held[1]][6],
                "ROOTS",
            )
    for chunk in removals:
        need(chunk in {r[0] for r in data["tombstone"]}, "DECISION")
    return {
        "admissions": len(admissions),
        "settlements": len(settlements),
        "claims": len(claims),
        "chunks": len(chunks),
        "retired": len(retired),
        "published": len(published),
        "tombstones": len(data["tombstone"]),
        "removals": len(removals),
        "protected": len(protected),
    }


def _stream_generation(data, stream):
    for row in data["stream"]:
        if row[0] == stream:
            return row[2]
    return None


def _released_root(data, retention, seq):
    """A publication's own protection is never released; an S15 window with an
    unresolved issuance at that point is not released by a generic release."""
    need(retention not in {r[9] for r in data["publication"]}, "PUBLICATION_ROOT")


def check_events(units: dict, policy: dict) -> dict:
    """The runtime's own event logs, per runtime incarnation (one envelope each;
    incarnations never overlap in time): every admitted interval's vector summed
    over time never exceeds the recorded envelope. A unit of a killed process
    has no terminal; its interval closes at that incarnation's last event."""
    groups: dict = {}
    for unit in units.values():
        groups.setdefault(unit.get("runtime"), []).append(unit)
    peak = dict.fromkeys(FIELDS, 0)
    for members in groups.values():
        last = max(ns for unit in members for ns, _kind in unit["events"])
        points = []
        for unit in members:
            events = {kind: ns for ns, kind in unit["events"]}
            if "ADMITTED" not in events:
                continue
            ends = [ns for ns, kind in unit["events"] if kind.startswith("TERMINAL:")]
            end = max(ends) if ends else last
            need(events["ADMITTED"] <= end, "EVENT_ORDER")
            points.append((events["ADMITTED"], 1, unit["vector"]))
            points.append((end, 0, unit["vector"]))
        used = dict.fromkeys(FIELDS, 0)
        for _ns, start, vector in sorted(points, key=lambda p: (p[0], p[1])):
            for name in FIELDS:
                used[name] += vector[name] if start else -vector[name]
                need(used[name] >= 0, "AGGREGATE")
                need(used[name] <= policy[name], "AGGREGATE")
                peak[name] = max(peak[name], used[name])
    return peak


def check_admitted_rows(units: dict, data) -> None:
    """Every unit the runtime admitted has its durable admission and, once
    terminal, its settlement (an erased reservation is visible here)."""
    admissions = {r[0] for r in data["admission"]}
    settled = {r[0] for r in data["admission_settlement"]}
    for handle, unit in units.items():
        kinds = [k for _ns, k in unit["events"]]
        if "ADMITTED" in kinds:
            need(handle in admissions, "ADMISSION_ROWS")
            if unit["settlement"] in ("RELEASED", "RECONCILED"):
                need(handle in settled, "ADMISSION_ROWS")


def check_cancel(units: dict, data) -> None:
    """A unit whose cancel was signalled before its end has a durable cancel
    (when recorded COMMITTED) and its attempt is never a clean success."""
    jobs = {r[0]: r for r in data["job"]}
    terminals = {r[0]: json.loads(r[3]) for r in data["attempt_terminal"]}
    attempts = {r[0]: r for r in data["attempt"]}
    for unit in units.values():
        kinds = [k for _ns, k in unit["events"]]
        if "CANCEL_SIGNALLED" not in kinds or unit.get("durable_cancel") != "COMMITTED":
            continue
        need(jobs[unit["job"]][5] == "CANCELLED", "CANCEL_ORDER")
        for identity, row in attempts.items():
            outcome = terminals.get(identity)
            if (
                row[1] == unit["generation"]
                and outcome is not None
                and "cancel" in outcome
            ):
                need(
                    not (
                        outcome["source"] == "EOF"
                        and outcome["transaction"] == "COMMIT_ACK"
                        and not outcome["cancel"][0]
                    ),
                    "CANCEL_ORDER",
                )


def check_interrupted(data, killed: list) -> None:
    """An attempt whose process was SIGKILLed before its terminal is recorded
    INTERRUPTED with every remote layer UNKNOWN (never promoted)."""
    terminals = {r[0]: r for r in data["attempt_terminal"]}
    for attempt in killed:
        row = terminals.get(attempt)
        if row is None or row[1] != "INTERRUPTED":
            raise CheckError("INTERRUPTED_OUTCOME")
        outcome = json.loads(row[3])
        need(
            all(
                outcome[k] == "UNKNOWN"
                for k in ("source", "transaction", "delivery", "cleanup")
            ),
            "INTERRUPTED_OUTCOME",
        )


def check_removal_basis(data, cut: str, epoch: int, chunks) -> None:
    """A collector that died after its unlink and before its observation: the
    later observation of those exact chunks is ABSENT by a later incarnation,
    never a claimed UNLINKED; after the observation COMMIT it stays its own."""
    for row in data["removal"]:
        if row[0] not in chunks:
            continue
        if cut in ("K3_unlinked_before_sync", "K4_synced_before_observation"):
            need(row[2] == "ABSENT" and row[1] > epoch, "REMOVAL_BASIS")
        if cut == "K5_observed_before_reply":
            need(row[2] == "UNLINKED" and row[1] == epoch, "REMOVAL_BASIS")


def check_inventory(data, files: dict) -> None:
    """Files against decisions: a committed or claimed name absent without a
    tombstone is corruption; a removed name present again, or a present name
    whose object differs from its pinned tombstone object, is refused."""
    tombstones = {r[0]: r for r in data["tombstone"]}
    removed = {r[0] for r in data["removal"]}
    for chunk in {r[0] for r in data["chunk"]}:
        name = "chunks/" + chunk + ".chunk"
        if name not in files:
            need(chunk in tombstones, "INVENTORY")
    for chunk in removed:
        need(
            "chunks/" + chunk + ".chunk" not in files
            and "staging/" + chunk + ".staging" not in files,
            "INVENTORY",
        )
    for chunk, row in tombstones.items():
        if chunk in removed:
            continue
        for directory, name, device, inode, _changed, size in json.loads(row[4]):
            found = files.get(directory + "/" + name)
            if found is not None:
                need((found[0], found[1], found[3]) == (device, inode, size), "OBJECT")


def check_acks(data, acked: set) -> None:
    """Every durable acknowledgement is one the consumer explicitly requested."""
    for row in data["acknowledgement"]:
        need(row[0] in acked, "ACK")


def inventory(root) -> dict:
    """{dir/name: (device, inode, ctime_ns, size)} of chunk and staging names."""
    import os

    result = {}
    for directory in ("chunks", "staging"):
        for name in os.listdir(os.path.join(root, directory)):
            state = os.lstat(os.path.join(root, directory, name))
            result[directory + "/" + name] = (
                state.st_dev,
                state.st_ino,
                state.st_ctime_ns,
                state.st_size,
            )
    return result


# --- pure transition models ------------------------------------------------------


def admission_model(envelope=2, units=3, durable=3, allowance=2) -> int:
    """Exhaustive interleavings of admit / claim / settle / crash+reconcile for
    `units` units over a connection envelope and a durable byte envelope.
    Laws: the in-flight connections never exceed the envelope; open allowances
    plus claimed bytes never exceed the durable envelope; every admission is
    settled at most once; no claim after settlement or beyond allowance; a
    crash never frees claimed bytes. Returns the number of explored states."""
    # state: (incarnation, per-unit (status, claimed, owner)), claimed occupancy
    start = (1, tuple(("idle", 0, 0) for _ in range(units)), 0)
    seen = {start}
    queue = deque([start])
    while queue:
        incarnation, per, occupied = queue.popleft()
        connections = sum(1 for s, _c, _o in per if s == "open")
        reserved = sum(allowance - c for s, c, _o in per if s == "open")
        need(connections <= envelope, "MODEL_AGGREGATE")
        need(occupied + reserved <= durable, "MODEL_DURABLE")
        successors = []
        for i, (status, claimed, owner) in enumerate(per):
            if (
                status == "idle"
                and connections < envelope
                and occupied + reserved + allowance <= durable
            ):
                successors.append(
                    (incarnation, _set(per, i, ("open", 0, incarnation)), occupied)
                )
            if status == "open" and owner == incarnation and claimed < allowance:
                successors.append(
                    (
                        incarnation,
                        _set(per, i, ("open", claimed + 1, owner)),
                        occupied + 1,
                    )
                )
            if status == "open" and owner == incarnation:
                successors.append(
                    (incarnation, _set(per, i, ("settled", claimed, owner)), occupied)
                )
            if status == "open" and owner < incarnation:
                # Reconciliation by a later incarnation: claimed bytes stay.
                successors.append(
                    (
                        incarnation,
                        _set(per, i, ("reconciled", claimed, owner)),
                        occupied,
                    )
                )
            if status == "settled" and claimed:
                # Collection of that unit's bytes (after a removal) frees them.
                successors.append(
                    (
                        incarnation,
                        _set(per, i, ("settled", 0, owner)),
                        occupied - claimed,
                    )
                )
        if incarnation < 2:
            successors.append((incarnation + 1, per, occupied))
        for state in successors:
            if state not in seen:
                seen.add(state)
                queue.append(state)
    return len(seen)


def _set(items, index, value):
    return items[:index] + (value,) + items[index + 1 :]


def lifetime_model(readers=2) -> int:
    """Exhaustive interleavings of `readers` readers (acquire shared lease, fresh
    tombstone check, read, release), one root release and one collector (try
    exclusive, decide only without roots, unlink only after a decision,
    release). Laws: no read of an unlinked file, no decision while a root is
    held, no reader past its check after a decision while the collector held
    exclusion. Returns the number of explored states."""
    # reader: idle | holding | refused | done ; collector: idle|excl|decided|unlinked|done
    start = (tuple("idle" for _ in range(readers)), "idle", True, False, False)
    seen = {start}
    queue = deque([start])
    while queue:
        rs, collector, root, decided, unlinked = queue.popleft()
        holding = sum(1 for r in rs if r == "holding")
        need(not (unlinked and holding), "MODEL_READ_AFTER_UNLINK")
        need(not (decided and root), "MODEL_DECIDED_WITH_ROOT")
        successors = []
        for i, r in enumerate(rs):
            if r == "idle" and collector not in ("excl", "decided"):
                successors.append(
                    (
                        _set(rs, i, "refused" if decided else "holding"),
                        collector,
                        root,
                        decided,
                        unlinked,
                    )
                )
            if r == "holding":
                successors.append(
                    (_set(rs, i, "done"), collector, root, decided, unlinked)
                )
        if root:
            successors.append((rs, collector, False, decided, unlinked))
        if collector == "idle" and holding == 0:
            successors.append((rs, "excl", root, decided, unlinked))
        if collector == "excl" and not root:
            successors.append((rs, "decided", root, True, unlinked))
        if collector == "excl" and root:
            successors.append((rs, "done", root, decided, unlinked))
        if collector == "decided":
            successors.append((rs, "unlinked", root, decided, True))
        if collector == "unlinked":
            successors.append((rs, "done", root, decided, unlinked))
        for state in successors:
            if state not in seen:
                seen.add(state)
                queue.append(state)
    return len(seen)


def check_reads(reads: list, decisions: list) -> None:
    """Reader/collector order from the processes' own observations: a read of a
    subject happened before that subject's decision, or the reader refused."""
    decided = {generation: ns for generation, ns in decisions}
    for generation, ns, outcome in reads:
        if outcome == "READ" and generation in decided:
            need(ns < decided[generation], "READ_AFTER_DECISION")


def check_unique_settlement(data) -> None:
    keys = [r[0] for r in data["admission_settlement"]]
    need(len(keys) == len(set(keys)), "SETTLEMENT")


def check_all(evidence: dict) -> dict:
    """Every law over one evidence bundle (store rows, events, files, cuts)."""
    data = evidence["data"]
    check_unique_settlement(data)
    facts = check_store(data)
    units = evidence.get("units", {})
    if units:
        facts["peak"] = check_events(units, evidence["policy"])
        check_admitted_rows(units, data)
        check_cancel(units, data)
    check_interrupted(data, evidence.get("killed", []))
    if evidence.get("cut"):
        check_removal_basis(data, *evidence["cut"])
    if "files" in evidence:
        check_inventory(data, evidence["files"])
    if "acked" in evidence:
        check_acks(data, evidence["acked"])
    check_reads(evidence.get("reads", []), evidence.get("decisions", []))
    return facts


def _copy(evidence):
    import copy

    return copy.deepcopy(evidence)


def damage(kind: str, evidence: dict) -> tuple[dict, str]:
    """One coordinated damage of real evidence (every redundant copy rewritten)
    and the law that must reject it."""
    e = _copy(evidence)
    data = e["data"]
    if kind == "D01_aggregate_oversubscription":
        # Each unit's own vector stays plausible; their intervals now overlap
        # beyond the recorded envelope.
        groups: dict = {}
        for h, u in e["units"].items():
            kinds = [k for _n, k in u["events"]]
            if (
                u["vector"]["connections"]
                and "ADMITTED" in kinds
                and any(k.startswith("TERMINAL:") for k in kinds)
            ):
                groups.setdefault(u.get("runtime"), []).append(h)
        handles = sorted(
            next(g for g in groups.values() if len(g) >= 2),
            key=lambda h: e["units"][h]["events"][0][0],
        )
        first, second = e["units"][handles[0]], e["units"][handles[1]]
        start = min(ns for ns, k in first["events"] if k == "ADMITTED")
        second["events"] = [
            (start + 1 if k == "ADMITTED" else ns, k) for ns, k in second["events"]
        ]
        e["policy"] = {**e["policy"], "connections": 1}
        end = max(ns for ns, k in first["events"] if k.startswith("TERMINAL:"))
        second["events"] = [
            (max(ns, end + 1) if k.startswith("TERMINAL:") else ns, k)
            for ns, k in second["events"]
        ]
        return e, "AGGREGATE"
    if kind == "D02_double_settlement":
        data["admission_settlement"].append(data["admission_settlement"][0])
        return e, "SETTLEMENT"
    if kind == "D03_erased_reservation":
        claimed = {r[4] for r in data["chunk_claim"]}
        victim = next(
            h
            for h, u in e["units"].items()
            if h not in claimed and any(k == "ADMITTED" for _n, k in u["events"])
        )
        data["admission"] = [r for r in data["admission"] if r[0] != victim]
        data["admission_settlement"] = [
            r for r in data["admission_settlement"] if r[0] != victim
        ]
        return e, "ADMISSION_ROWS"
    if kind == "D04_cancel_recorded_success":
        unit = next(
            u
            for u in e["units"].values()
            if u.get("durable_cancel") == "COMMITTED"
            and any(k == "CANCEL_SIGNALLED" for _n, k in u["events"])
        )
        attempts = {r[0] for r in data["attempt"] if r[1] == unit["generation"]}
        rewritten = []
        for row in data["attempt_terminal"]:
            if row[0] in attempts:
                outcome = json.loads(row[3])
                outcome.update(
                    source="EOF", transaction="COMMIT_ACK", delivery="COMPLETE"
                )
                outcome["cancel"] = [False, False, False]
                row = (row[0], "OUTCOME", row[2], json.dumps(outcome, sort_keys=True))
            rewritten.append(row)
        data["attempt_terminal"] = rewritten
        return e, "CANCEL_ORDER"
    if kind == "D05_protected_tombstone":
        tombstoned = {r[0] for r in data["tombstone"]}
        retired = {r[0] for r in data["generation_retirement"]}
        chunk = next(
            r for r in data["chunk"] if r[0] not in tombstoned and r[2] not in retired
        )
        collection = ("gcd-" + "d" * 32, chunk[1], chunk[2], 1, 1)
        data["collection"].append(collection)
        data["tombstone"].append(
            (chunk[0], collection[0], chunk[2], "RETIRED", "[]", chunk[8])
        )
        return e, "ROOTS"
    if kind == "D06_publication_root_released":
        retention = data["publication"][0][9]
        data["retention_release"].append((retention, 1, "pub-" + "0" * 32))
        sequence = max(r[0] for r in data["operation"]) + 1
        job = data["publication"][0][1]
        data["operation"].append(
            (
                sequence,
                "op-" + "e" * 32,
                "release_retention",
                job,
                json.dumps({"job": job, "retention": retention}),
                json.dumps({"retention": retention}),
            )
        )
        return e, "PUBLICATION_ROOT"
    if kind == "D07_stale_snapshot_read":
        generation, decided = e["decisions"][0]
        e["reads"].append((generation, decided + 1, "READ"))
        return e, "READ_AFTER_DECISION"
    if kind == "D08_retire_published":
        publication = data["publication"][0]
        data["generation_retirement"].append(
            (publication[0], publication[1], 1, "pub-" + "0" * 32)
        )
        sequence = max(r[0] for r in data["operation"]) + 1
        data["operation"].append(
            (
                sequence,
                "op-" + "f" * 32,
                "retire_generation",
                publication[1],
                json.dumps({"generation": publication[0], "job": publication[1]}),
                json.dumps({"generation": publication[0]}),
            )
        )
        return e, "RETIREMENT"
    if kind == "D09_collection_without_decision":
        removed = {r[0] for r in data["removal"]}
        chunk = next(
            r[0] for r in data["tombstone"] if r[0] in removed and r[3] == "RETIRED"
        )
        data["tombstone"] = [r for r in data["tombstone"] if r[0] != chunk]
        data["removal"] = [r for r in data["removal"] if r[0] != chunk]
        return e, "INVENTORY"
    if kind == "D10_replacement_object":
        # A decided, not yet removed subject whose pinned object is replaced.
        removed = {r[0] for r in data["removal"]}
        tombstone = next(
            r for r in data["tombstone"] if r[0] not in removed and json.loads(r[4])
        )
        directory, name = json.loads(tombstone[4])[0][:2]
        device, inode, changed, size = e["files"][directory + "/" + name]
        e["files"][directory + "/" + name] = (device, inode + 1, changed, size)
        return e, "OBJECT"
    if kind == "D11_credited_not_removed":
        tombstone = next(
            r for r in data["tombstone"] if r[0] not in {x[0] for x in data["removal"]}
        )
        data["removal"].append((tombstone[0], 9, "UNLINKED"))
        return e, "INVENTORY"
    if kind == "D13_erased_unknown":
        attempt = e["killed"][0]
        data["attempt_terminal"] = [
            (
                r[0],
                "OUTCOME",
                r[2],
                json.dumps(
                    {
                        **json.loads(r[3]),
                        "source": "EOF",
                        "transaction": "COMMIT_ACK",
                        "delivery": "COMPLETE",
                        "cleanup": "CLOSED",
                    },
                    sort_keys=True,
                ),
            )
            if r[0] == attempt
            else r
            for r in data["attempt_terminal"]
        ]
        return e, "INTERRUPTED_OUTCOME"
    if kind == "D14_promoted_unlink":
        _cut, epoch, chunks = e["cut"]
        data["removal"] = [
            (r[0], epoch, "UNLINKED") if r[0] in chunks else r for r in data["removal"]
        ]
        return e, "REMOVAL_BASIS"
    raise KeyError(kind)


DAMAGES = (
    "D01_aggregate_oversubscription",
    "D02_double_settlement",
    "D03_erased_reservation",
    "D04_cancel_recorded_success",
    "D05_protected_tombstone",
    "D06_publication_root_released",
    "D07_stale_snapshot_read",
    "D08_retire_published",
    "D09_collection_without_decision",
    "D10_replacement_object",
    "D11_credited_not_removed",
    "D13_erased_unknown",
    "D14_promoted_unlink",
)


def rejects(kind: str, evidence: dict) -> str:
    """Apply one damage and return the law that rejected it (must be designated)."""
    damaged, law = damage(kind, evidence)
    try:
        check_all(damaged)
    except CheckError as error:
        need(str(error) == law, "DAMAGE_WRONG_CONTROL:" + kind + ":" + str(error))
        return law
    raise CheckError("DAMAGE_ACCEPTED:" + kind)
