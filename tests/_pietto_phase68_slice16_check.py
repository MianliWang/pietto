"""Independent S16 publication checker over static SQLite backups, chunk bytes
and literal oracles.

From raw relations alone it recomputes the closing attempt's eligibility, the
exact membership and extent of the published checkpoint, the R2 continuation
lineage, the publication / protection / operation correspondence, the
cancellation order and the unchanged older history; every referenced chunk is
decoded with pyarrow itself (the S12 checker's frame parser). It never calls
the production publication, eligibility, snapshot, reader or verifier.
"""

from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any

from _pietto_phase68_slice12_check import (
    CHUNK,
    CHUNK_MAGIC,
    FRAME,
    decode_frame,
    parse_chunk,
)

STORE_TABLES = (
    "job",
    "generation",
    "attempt",
    "attempt_terminal",
    "operation",
    "capture",
    "capture_end",
    "chunk",
    "checkpoint",
    "checkpoint_member",
    "retention",
    "retention_release",
    "extraction",
    "continuation",
    "reconciliation",
    "continuation_end",
    "closing_observation",
    "publication",
)
CLEAN = {
    "postgres_rows": "CLOSED",
    "postgres_adbc": "LOCAL_CLOSED_REMOTE_UNOBSERVED",
    "mysql_rows": "LOCAL_CLOSED_REMOTE_UNOBSERVED",
}
GUARDS = ("STATIC", "FULFILLED")
# An interrupted attempt's remote layers are unobserved by definition (S11).
INTERRUPTED = {
    "basis": "PUBLISHER_EPOCH_ENDED_WITHOUT_TERMINAL",
    "source": "UNKNOWN",
    "transaction": "UNKNOWN",
    "delivery": "UNKNOWN",
    "cleanup": "UNKNOWN",
    "remote_source_use_end": "UNKNOWN",
}


def need(condition, code):
    if not condition:
        raise ValueError("S16_CHECK_" + code)


def load(backup) -> dict[str, Any]:
    """A static backup copy only; never a live workspace database."""
    with closing(
        sqlite3.connect("file:" + str(backup) + "?mode=ro&immutable=1", uri=True)
    ) as c:
        store: dict[str, Any] = {
            t: [tuple(r) for r in c.execute(f"SELECT * FROM {t}")] for t in STORE_TABLES
        }
        store["user_version"] = c.execute("PRAGMA user_version").fetchone()[0]
    return store


def _covers(ranges, extent) -> bool:
    if extent == 0:
        return sorted(ranges) == [(0, 0)]
    position = 0
    for start, stop in sorted(ranges):
        if start != position or stop <= start:
            return False
        position = stop
    return position == extent


def _terminal_requests(store) -> dict[str, tuple[int, dict]]:
    """attempt -> (sequence, request) of the operation that wrote its terminal."""
    found = {}
    for sequence, _identity, kind, _job, request, _result in store["operation"]:
        if kind == "attempt_terminal":
            value = json.loads(request)
            found[value["attempt"]] = (sequence, value)
    return found


def check_history(store) -> dict:
    """Every terminal and closing observation equals the request of its own
    operation: an erased UNKNOWN or relabelled outcome cannot pass."""
    requests = _terminal_requests(store)
    closings = {r[0]: r for r in store["closing_observation"]}
    unknown = 0
    for attempt, kind, _epoch, outcome in store["attempt_terminal"]:
        need(attempt in requests, "TERMINAL_OPERATION")
        request = requests[attempt][1]
        need(
            request["kind"] == kind and request["outcome"] == json.loads(outcome),
            "TERMINAL_HISTORY",
        )
        if kind == "INTERRUPTED":
            need(json.loads(outcome) == INTERRUPTED, "INTERRUPTED_OUTCOME")
        observation = request.get("observation")
        row = closings.get(attempt)
        if kind == "OUTCOME" and store["user_version"] >= 6:
            need(row is not None and observation is not None, "CLOSING_HISTORY")
            assert row is not None and observation is not None
            need(
                (
                    row[3],
                    row[4],
                    None if row[5] is None else json.loads(row[5]),
                    json.loads(row[6]),
                )
                == (
                    1,
                    observation["rows"],
                    observation["failure"],
                    observation["cleanup"],
                ),
                "CLOSING_HISTORY",
            )
        else:
            need(row is None and observation is None, "CLOSING_HISTORY")
        unknown += json.loads(outcome).get("transaction") == "UNKNOWN"
    return {"terminals": len(store["attempt_terminal"]), "unknown": unknown}


def _eligible(outcome, row, route, reference, extent) -> bool:
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
        and outcome.get("route") == route
        and outcome.get("binding_reference") == reference
        and row[3] == 1
        and row[4] == extent
        and row[5] is None
        and json.loads(row[6]) == []
    )


def check_publication(store, generation) -> dict:
    """Re-derive the one publication of `generation` from raw relations."""
    found = [p for p in store["publication"] if p[0] == generation]
    need(len(found) == 1, "PUBLICATION")
    (
        _g,
        job,
        binding,
        checkpoint,
        extent,
        members,
        contract,
        scheme,
        closing_attempt,
        retention,
        descriptor,
        operation,
        epoch,
        instance,
    ) = found[0]
    operations = {o[1]: o for o in store["operation"]}
    record = operations.get(operation)
    need(record is not None and record[2] == "publish_generation", "OPERATION")
    assert record is not None
    sequence, request, result = record[0], json.loads(record[4]), json.loads(record[5])
    need(
        request
        == {
            "checkpoint": checkpoint,
            "closing": closing_attempt,
            "descriptor": descriptor,
            "extent": extent,
            "generation": generation,
            "job": job,
            "members": members,
            "publisher": [epoch, instance],
            "retention": retention,
        },
        "OPERATION_REQUEST",
    )
    need(
        result
        == {
            "checkpoint": checkpoint,
            "closing": closing_attempt,
            "extent": extent,
            "generation": generation,
            "retention": retention,
            "revision": result.get("revision"),
        },
        "OPERATION_RESULT",
    )
    # Cancellation, if any, came after the publication's own transaction.
    need(
        all(
            o[0] > sequence
            for o in store["operation"]
            if o[2] == "cancel_job" and o[3] == job
        ),
        "CANCEL_ORDER",
    )
    generation_row = next((g for g in store["generation"] if g[0] == generation), None)
    capture = next((c for c in store["capture"] if c[0] == generation), None)
    need(generation_row is not None and capture is not None, "GENERATION")
    assert generation_row is not None and capture is not None
    route = generation_row[3]
    need(
        (binding, contract, scheme) == (generation_row[2], capture[4], capture[5]),
        "IDENTITY",
    )
    # The closing attempt: its terminal before the publication, eligible facts.
    attempt = next((a for a in store["attempt"] if a[0] == closing_attempt), None)
    need(attempt is not None and attempt[1:3] == (generation, job), "CLOSING_ATTEMPT")
    assert attempt is not None
    terminal = next(
        (t for t in store["attempt_terminal"] if t[0] == closing_attempt), None
    )
    observed = next(
        (r for r in store["closing_observation"] if r[0] == closing_attempt), None
    )
    requests = _terminal_requests(store)
    need(
        terminal is not None
        and terminal[1] == "OUTCOME"
        and observed is not None
        and requests.get(closing_attempt, (sequence,))[0] < sequence,
        "CLOSING_TERMINAL",
    )
    assert terminal is not None and observed is not None
    need(
        _eligible(json.loads(terminal[3]), observed, route, attempt[6], extent),
        "CLOSING_ELIGIBILITY",
    )
    # Exact membership of the named (and latest) checkpoint.
    chunks = {r[0]: r for r in store["chunk"] if r[2] == generation}
    member_ids = {m[1] for m in store["checkpoint_member"] if m[0] == checkpoint}
    need(member_ids <= set(chunks) and len(member_ids) == members, "MEMBERS")
    ranges = [(chunks[m][4], chunks[m][5]) for m in member_ids]
    need(_covers(ranges, extent), "COVERAGE")
    latest = max(
        (r for r in store["checkpoint"] if r[2] == generation), key=lambda r: r[3]
    )
    need(latest[0] == checkpoint, "LATEST")
    # Basis: the original capture, or a reconciled continuation with its own end.
    reconciled = {r[0] for r in store["reconciliation"]}
    producers = {capture[2]} | {
        n[0] for n in store["continuation"] if n[2] == generation and n[0] in reconciled
    }
    need(all(chunks[m][3] in producers for m in member_ids), "PRODUCERS")
    if closing_attempt == capture[2]:
        basis = "CAPTURE"
        end = next((e for e in store["capture_end"] if e[0] == generation), None)
        need(
            end is not None
            and (end[1], end[2]) == (extent, "EOF")
            and all(chunks[m][3] == closing_attempt for m in member_ids),
            "BASIS",
        )
    else:
        basis = "CONTINUATION"
        frozen = next(
            (n for n in store["continuation"] if n[0] == closing_attempt), None
        )
        done = next(
            (e for e in store["continuation_end"] if e[0] == closing_attempt), None
        )
        need(frozen is not None and done is not None, "BASIS")
        assert frozen is not None and done is not None
        previous = {m[1] for m in store["checkpoint_member"] if m[0] == frozen[3]}
        need(
            frozen[2] == generation
            and closing_attempt in reconciled
            and (done[2], done[3], done[5]) == (extent, "EOF", checkpoint)
            and previous <= member_ids
            and all(chunks[m][3] == closing_attempt for m in member_ids - previous),
            "BASIS",
        )
    need(json.loads(descriptor).get("basis") == basis, "DESCRIPTOR")
    # Publication-owned protection: its own exact checkpoint, never released.
    protection = next((r for r in store["retention"] if r[0] == retention), None)
    need(
        protection is not None
        and protection[1:4] == (job, generation, checkpoint)
        and not [r for r in store["retention_release"] if r[0] == retention],
        "PROTECTION",
    )
    # Nothing of the generation was opened or written after the publication.
    for _seq, _identity, kind, _job, text, _result in store["operation"]:
        value = json.loads(text)
        if _seq > sequence and value.get("generation") == generation:
            need(
                kind
                in (
                    "retain_checkpoint",
                    "release_retention",
                    "register_consumer",
                    "open_replay",
                    "register_stream",
                    "adopt_window",
                ),
                "AFTER_PUBLICATION",
            )
    attempts = [a for a in store["attempt"] if a[1] == generation]
    need(
        all(requests.get(a[0], (sequence,))[0] < sequence for a in attempts),
        "ATTEMPT_OPEN",
    )
    return {
        "generation": generation,
        "extent": extent,
        "members": members,
        "basis": basis,
        "closing": closing_attempt,
        "sequence": sequence,
    }


def published_rows(store, workspace_root, generation) -> list[tuple]:
    """Every member of the published checkpoint, decoded from its chunk bytes."""
    publication = next(p for p in store["publication"] if p[0] == generation)
    chunks = {r[0]: r for r in store["chunk"] if r[2] == generation}
    capture = next(r for r in store["capture"] if r[0] == generation)
    members = sorted(
        (chunks[m] for k, m, _g in store["checkpoint_member"] if k == publication[3]),
        key=lambda r: (r[4], r[5]),
    )
    rows: list[tuple] = []
    for chunk in members:
        data = (Path(workspace_root) / "chunks" / chunk[7]).read_bytes()
        need(hashlib.sha256(data).hexdigest() == chunk[9], "CHUNK_DIGEST")
        _text, descriptor, frame = parse_chunk(data)
        need(
            (descriptor["chunk"], descriptor["start"], descriptor["stop"])
            == (chunk[0], chunk[4], chunk[5]),
            "CHUNK_DESCRIPTOR",
        )
        _batches, table = decode_frame(frame, chunk[5] - chunk[4], capture[4])
        rows.extend(
            tuple(table.column(i)[j].as_py() for i in range(table.num_columns))
            for j in range(table.num_rows)
        )
    need(len(rows) == publication[4], "ROW_COUNT")
    return rows


def encoded(rows) -> list:
    """S01's independent scalar encoding (the native literal oracles' form)."""
    from _pietto_phase68_slice4_probe import s01

    return [[s01.scalar(v) for v in row] for row in rows]


def same_rows(found, oracle, *, ordered) -> bool:
    """Decoded values against an S01-encoded literal oracle: ordered or a bag."""
    from collections import Counter

    left = encoded(found)
    if ordered:
        return left == oracle

    def bag(items):
        return Counter(json.dumps(row, sort_keys=True) for row in items)

    return bag(left) == bag(oracle)


def check_store(backup, workspace_root, generation, oracle, *, ordered) -> dict:
    """History, publication and decoded values of one published generation."""
    store = load(backup)
    need(store["user_version"] == 6, "VERSION")
    history = check_history(store)
    publication = check_publication(store, generation)
    rows = published_rows(store, workspace_root, generation)
    need(same_rows(rows, oracle, ordered=ordered), "VALUES")
    return {**publication, **history, "rows": len(rows)}


# --- coordinated damages over real records ----------------------------------------


def _rewrite(root, store_path, chunk, frame):
    """Re-encode one chunk file coherently and update its row (sizes/digests agree)."""
    path = Path(root) / "chunks" / (chunk + ".chunk")
    _text, descriptor, _old = parse_chunk(path.read_bytes())
    descriptor = dict(descriptor)
    descriptor["frame_bytes"] = len(frame)
    descriptor["frame_sha256"] = hashlib.sha256(frame).hexdigest()
    raw = json.dumps(
        descriptor, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    body = raw + frame
    data = CHUNK.pack(CHUNK_MAGIC, len(raw), len(frame), hashlib.sha256(body).digest())
    data += body
    path.write_bytes(data)
    with closing(sqlite3.connect(store_path)) as c:
        c.execute(
            "UPDATE chunk SET bytes = ?, digest = ?, descriptor = ? WHERE identity = ?",
            (len(data), hashlib.sha256(data).hexdigest(), raw.decode(), chunk),
        )
        c.commit()


def _altered_value(root, store_path, store, generation):
    """A coherent same-type rewrite of the first row's Int column (valid IPC)."""
    import importlib

    pa: Any = importlib.import_module("pyarrow")
    chunk = min(
        (r for r in store["chunk"] if r[2] == generation and r[5] > r[4]),
        key=lambda r: r[4],
    )
    capture = next(r for r in store["capture"] if r[0] == generation)
    _text, _descriptor, frame = parse_chunk(
        (Path(root) / "chunks" / chunk[7]).read_bytes()
    )
    _batches, table = decode_frame(frame, chunk[5] - chunk[4], capture[4])
    index = next(
        i for i, f in enumerate(table.schema) if str(f.type) in ("int64", "int32")
    )
    column = table.column(index).to_pylist()
    column[0] = 123456789 if column[0] != 123456789 else 987654321
    changed = table.set_column(
        index,
        table.schema.field(index),
        pa.array(column, table.schema.field(index).type),
    )
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, changed.schema) as writer:
        for batch in changed.to_batches():
            writer.write_batch(batch)
    payload = sink.getvalue().to_pybytes()
    header = FRAME.unpack_from(frame)
    _rewrite(
        root,
        store_path,
        chunk[0],
        FRAME.pack(
            header[0],
            header[1],
            header[2],
            len(payload),
            header[4],
            hashlib.sha256(payload).digest(),
        )
        + payload,
    )


# Each coordinated damage rewrites every redundant copy it touches (rows, the
# operation request and result) so that only its own named control rejects it.
DAMAGES = {
    "relabelled_failure": "BASIS",
    "member_omission": "CLOSING_ELIGIBILITY",
    "foreign_completion": "CLOSING_TERMINAL",
    "cancelled_publication": "CANCEL_ORDER",
    "protection_removal": "PROTECTION",
    "conflicting_operation": "OPERATION_REQUEST",
    "altered_value": "VALUES",
    "erased_unknown": "INTERRUPTED_OUTCOME",
    "promoted_notification": "OPERATION",
}


def _reoperate(c, identity, change):
    """Coherently rewrite one operation's request and result JSON copies."""
    request, result = c.execute(
        "SELECT request, result FROM operation WHERE identity = ?", (identity,)
    ).fetchone()
    request, result = json.loads(request), json.loads(result)
    change(request, result)
    c.execute(
        "UPDATE operation SET request = ?, result = ? WHERE identity = ?",
        (
            json.dumps(request, sort_keys=True, separators=(",", ":")),
            json.dumps(result, sort_keys=True, separators=(",", ":")),
            identity,
        ),
    )


def damages(backup, workspace_root, generation, oracle, *, ordered, scratch) -> dict:
    """Each coordinated damage of a real published record must be rejected by
    its own named control (DAMAGES), never by an incidental copy mismatch."""
    scratch = Path(scratch)
    scratch.mkdir(mode=0o700)
    base = load(backup)
    publication = next(p for p in base["publication"] if p[0] == generation)
    # Real records with an older (interrupted / UNKNOWN) attempt beside the closing.
    others = [
        a for a in base["attempt"] if a[1] == generation and a[0] != publication[8]
    ]
    need(bool(others), "DAMAGE_BASE")
    older = others[0][0]
    publish = publication[11]
    terminal_operation = {
        value["attempt"]: identity
        for _seq, identity, kind, _job, text, _result in base["operation"]
        if kind == "attempt_terminal"
        for value in (json.loads(text),)
    }

    def reclose(closing):
        def change(request, result):
            request["closing"] = result["closing"] = closing

        return change

    rejected = {}
    for kind, control in DAMAGES.items():
        root = scratch / kind
        root.mkdir(mode=0o700)
        shutil.copytree(Path(workspace_root) / "chunks", root / "chunks")
        store_path = root / "store.sqlite"
        shutil.copyfile(backup, store_path)
        with closing(sqlite3.connect(store_path)) as c:
            c.execute("PRAGMA foreign_keys = OFF")
            if kind == "relabelled_failure":
                # The older interrupted attempt forged into the successful closing
                # in every copy: terminal and its request (the real outcome under
                # its own binding reference), closing observation, publication and
                # the publish request/result. Only its lineage remains to refuse.
                real = next(
                    t for t in base["attempt_terminal"] if t[0] == publication[8]
                )
                outcome = dict(json.loads(real[3]))
                outcome["binding_reference"] = others[0][6]
                text = json.dumps(outcome, sort_keys=True, separators=(",", ":"))
                c.execute(
                    "UPDATE attempt_terminal SET kind = 'OUTCOME', outcome = ?"
                    " WHERE attempt = ?",
                    (text, older),
                )
                observation = json.loads(
                    c.execute(
                        "SELECT request FROM operation WHERE identity = ?",
                        (terminal_operation[publication[8]],),
                    ).fetchone()[0]
                )["observation"]

                def forge(request, result):
                    request.update(kind="OUTCOME", outcome=outcome)
                    request["observation"] = observation
                    result["kind"] = "OUTCOME"

                _reoperate(c, terminal_operation[older], forge)
                c.execute(
                    "INSERT INTO closing_observation SELECT ?, generation, job,"
                    " closed, rows, failure, cleanup, publisher_epoch"
                    " FROM closing_observation WHERE attempt = ?",
                    (older, publication[8]),
                )
                c.execute(
                    "UPDATE publication SET closing = ? WHERE generation = ?",
                    (older, generation),
                )
                _reoperate(c, publish, reclose(older))
            elif kind == "member_omission":
                # The last member removed with every sum recomputed (checkpoint,
                # publication, publish request and result).
                last = max(
                    (
                        r
                        for r in base["chunk"]
                        if r[2] == generation
                        and r[0]
                        in {
                            m[1]
                            for m in base["checkpoint_member"]
                            if m[0] == publication[3]
                        }
                    ),
                    key=lambda r: r[4],
                )
                c.execute(
                    "DELETE FROM checkpoint_member WHERE checkpoint = ? AND chunk = ?",
                    (publication[3], last[0]),
                )
                c.execute(
                    "UPDATE checkpoint SET members = members - 1, rows = rows - ?,"
                    " frontier = ? WHERE identity = ?",
                    (last[5] - last[4], last[4], publication[3]),
                )
                c.execute(
                    "UPDATE publication SET members = members - 1, extent = ?"
                    " WHERE generation = ?",
                    (last[4], generation),
                )

                def shorten(request, result):
                    request["members"] -= 1
                    request["extent"] = result["extent"] = last[4]

                _reoperate(c, publish, shorten)
            elif kind == "foreign_completion":
                # Another attempt named as the closing in every publication copy.
                c.execute(
                    "UPDATE publication SET closing = ? WHERE generation = ?",
                    (older, generation),
                )
                _reoperate(c, publish, reclose(older))
            elif kind == "cancelled_publication":
                # A cancellation ordered before the publication transaction.
                at = next(o[0] for o in base["operation"] if o[1] == publish)
                previous = max(
                    o[0]
                    for o in base["operation"]
                    if o[0] < at and o[2] != "attempt_terminal"
                )
                c.execute(
                    "UPDATE operation SET kind = 'cancel_job' WHERE sequence = ?",
                    (previous,),
                )
            elif kind == "protection_removal":
                c.execute(
                    "INSERT INTO retention_release(retention, publisher_epoch,"
                    " publisher_instance) VALUES (?, ?, ?)",
                    (publication[9], publication[12], publication[13]),
                )
            elif kind == "conflicting_operation":
                c.execute(
                    "UPDATE operation SET request = replace(request, ?, ?)"
                    " WHERE identity = ?",
                    (
                        '"extent":' + str(publication[4]),
                        '"extent":' + str(publication[4] + 1),
                        publish,
                    ),
                )
            elif kind == "erased_unknown":
                # The historical UNKNOWN erased from the terminal and its request.
                for statement in (
                    "UPDATE attempt_terminal SET outcome = replace(outcome,"
                    " 'UNKNOWN', 'COMMIT_ACK') WHERE outcome LIKE '%UNKNOWN%'",
                    "UPDATE operation SET request = replace(request, 'UNKNOWN',"
                    " 'COMMIT_ACK') WHERE kind = 'attempt_terminal'"
                    " AND request LIKE '%UNKNOWN%'",
                ):
                    c.execute(statement)
            elif kind == "promoted_notification":
                # A delivered notification is no commit evidence: a publication
                # row without its own operation is refused.
                c.execute(
                    "UPDATE publication SET operation = ? WHERE generation = ?",
                    ("op-" + "0" * 32, generation),
                )
            c.commit()
        if kind == "altered_value":
            _altered_value(root, store_path, base, generation)
        try:
            check_store(store_path, root, generation, oracle, ordered=ordered)
        except ValueError as error:
            if str(error) != "S16_CHECK_" + control:
                raise ValueError(
                    "S16_DAMAGE_CONTROL:" + kind + ":" + str(error)
                ) from None
            rejected[kind] = str(error)
            continue
        raise ValueError("S16_DAMAGE_ACCEPTED:" + kind)
    shutil.rmtree(scratch)
    return rejected
