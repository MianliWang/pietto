"""Independent S12 store/chunk checker over raw SQLite rows and chunk bytes.

It parses both frames itself and decodes IPC payloads with pyarrow directly; it
never calls the production snapshot, reader or decoder, so production decoding
cannot generate its expected values. Literal oracles come from the caller.
"""

from __future__ import annotations

from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import struct
from typing import Any

CHUNK = struct.Struct(">16sQQ32s")
CHUNK_MAGIC = b"PIETTO-CHUNK1\x00\x00\x00"
FRAME = struct.Struct(">12sQQQ32s32s")
FRAME_MAGIC = b"PIETTO-IPC1\x00"
TABLES = (
    "generation",
    "attempt",
    "attempt_terminal",
    "capture",
    "chunk",
    "checkpoint",
    "checkpoint_member",
    "capture_end",
    "retention",
    "retention_release",
    "operation",
)
SMALL_SCHEMA = [["renamed", "int64", False], ["other", "int64", True]]


def need(condition, code):
    if not condition:
        raise ValueError("S12_CHECK_" + code)


def load(backup) -> dict[str, Any]:
    """A static backup copy only; never a live workspace database."""
    with closing(
        sqlite3.connect("file:" + str(backup) + "?mode=ro&immutable=1", uri=True)
    ) as c:
        store: dict[str, Any] = {
            t: [tuple(r) for r in c.execute(f"SELECT * FROM {t}")] for t in TABLES
        }
        store["user_version"] = c.execute("PRAGMA user_version").fetchone()[0]
    return store


def frontier(ranges) -> int:
    position = 0
    for start, stop in sorted(ranges):
        if start != position:
            break
        position = stop
    return position


def _chain(store, generation):
    """Checkpoints 1..n each add exactly one chunk; recomputed frontier/members/rows."""
    chunks = {r[0]: r for r in store["chunk"] if r[2] == generation}
    members: dict[str, set] = {}
    for checkpoint, chunk, member_generation in store["checkpoint_member"]:
        if member_generation == generation:
            need(chunk in chunks, "MEMBER_GENERATION")
            members.setdefault(checkpoint, set()).add(chunk)
    chain = sorted(
        (r for r in store["checkpoint"] if r[2] == generation), key=lambda r: r[3]
    )
    previous: set = set()
    frontiers = []
    for index, checkpoint in enumerate(chain, 1):
        current = members.get(checkpoint[0], set())
        ranges = [(chunks[m][4], chunks[m][5]) for m in current]
        need(checkpoint[3] == index and previous < current, "CHAIN")
        need(len(current - previous) == 1, "CHAIN")
        need(
            (checkpoint[4], checkpoint[5], checkpoint[6])
            == (frontier(ranges), len(current), sum(b - a for a, b in ranges)),
            "FRONTIER",
        )
        frontiers.append(checkpoint[4])
        previous = current
    ordered = sorted(previous, key=lambda m: (chunks[m][4], chunks[m][5]))
    extents = [(chunks[m][4], chunks[m][5]) for m in ordered]
    need(all(a[1] <= b[0] and a != b for a, b in zip(extents, extents[1:])), "OVERLAP")
    return chunks, ordered, extents, frontiers


def parse_chunk(data: bytes):
    need(len(data) >= CHUNK.size, "CHUNK_FRAME")
    magic, size, frame_size, digest = CHUNK.unpack_from(data)
    need(
        magic == CHUNK_MAGIC and CHUNK.size + size + frame_size == len(data),
        "CHUNK_FRAME",
    )
    body = data[CHUNK.size :]
    need(hashlib.sha256(body).digest() == digest, "CHUNK_DIGEST")
    text = body[:size].decode("ascii")
    descriptor = json.loads(text)
    need(
        json.dumps(descriptor, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        == text,
        "DESCRIPTOR_CANONICAL",
    )
    frame = body[size:]
    need(
        descriptor["frame_bytes"] == len(frame)
        and descriptor["frame_sha256"] == hashlib.sha256(frame).hexdigest(),
        "FRAME_CORRESPONDENCE",
    )
    return text, descriptor, frame


def decode_frame(frame: bytes, rows: int, contract: str):
    import importlib

    pa: Any = importlib.import_module("pyarrow")

    need(len(frame) >= FRAME.size, "IPC_FRAME")
    magic, extent, batches, size, digest_of_contract, digest = FRAME.unpack_from(frame)
    payload = frame[FRAME.size :]
    need(
        magic == FRAME_MAGIC
        and extent == rows
        and size == len(payload)
        and digest_of_contract.hex() == contract
        and hashlib.sha256(payload).digest() == digest,
        "IPC_FRAME",
    )
    table = pa.ipc.open_stream(payload).read_all()
    need(table.num_rows == rows, "IPC_ROWS")
    return batches, table


def _plain(cell):
    if cell["kind"] == "null":
        return None
    need(cell["kind"] == "int", "READER_CARRIER")
    return int(cell["value"])


def check_bridge_store(backup, workspace, registration, data, reads, rows, *, target):
    """Store relations, file bytes and values of the base bridge against literals."""
    store = load(backup)
    need(store["user_version"] == 2, "VERSION")
    plan = {
        generation: (route, case, threshold, record)
        for route, group in registration["plan"]
        for case, threshold, record, generation in group
    }
    results = {(r["route"], r["case"]): r for r in data["results"]}
    read_rows = {(r["route"], r["case"]): r for r in reads["reads"]}
    captures = {r[0]: r for r in store["capture"]}
    chunks = {r[0]: r for r in store["chunk"]}
    need(
        all(
            m[1] in chunks and chunks[m[1]][2] == m[2]
            for m in store["checkpoint_member"]
        ),
        "MEMBER_GENERATION",
    )
    ends = {r[0]: r for r in store["capture_end"]}
    terminals = {r[0]: r for r in store["attempt_terminal"]}
    generations = {r[0]: r for r in store["generation"]}
    need(set(captures) == set(plan) == set(generations), "GENERATIONS")
    contracts, total, values_total = set(), 0, 0
    for generation, (route, case, threshold, record) in plan.items():
        result, read = results[(route, case)], read_rows[(route, case)]
        capture = captures[generation]
        need(generations[generation][2] == record, "GENERATION_BINDING")
        need(
            capture[1:4]
            == (registration["job"], result["store"]["attempt"], "ORDINARY")
            and capture[5] == "null",
            "CAPTURE",
        )
        contracts.add(capture[4])
        _chunks, ordered, extents, frontiers = _chain(store, generation)
        values: list[tuple] = []
        for member in ordered:
            row = chunks[member]
            need(
                row[1:4] == (registration["job"], generation, capture[2])
                and row[7] == row[0] + ".chunk",
                "CHUNK_ROW",
            )
            path = Path(workspace) / "chunks" / row[7]
            need(path.is_file() and not path.is_symlink(), "FILE")
            raw = path.read_bytes()
            need(
                len(raw) == row[8] and hashlib.sha256(raw).hexdigest() == row[9],
                "FILE_DIGEST",
            )
            text, descriptor, frame = parse_chunk(raw)
            need(text == row[10], "DESCRIPTOR_ROW")
            need(
                {
                    k: descriptor[k]
                    for k in (
                        "attempt",
                        "batches",
                        "binding",
                        "chunk",
                        "contract",
                        "coordinates",
                        "generation",
                        "job",
                        "kind",
                        "rows",
                        "start",
                        "stop",
                        "workspace",
                    )
                }  # fmt: skip
                == {
                    "attempt": capture[2],
                    "batches": row[6],
                    "binding": record,
                    "chunk": row[0],
                    "contract": capture[4],
                    "coordinates": None,
                    "generation": generation,
                    "job": registration["job"],
                    "kind": "ORDINARY",
                    "rows": row[5] - row[4],
                    "start": row[4],
                    "stop": row[5],
                    "workspace": registration["workspace_identity"],
                },
                "DESCRIPTOR_IDENTITY",
            )
            batches, table = decode_frame(frame, row[5] - row[4], capture[4])
            need(batches == row[6] == (1 if row[5] > row[4] else 0), "BATCHES")
            need(
                [[f.name, str(f.type), f.nullable] for f in table.schema]
                == SMALL_SCHEMA,
                "SCHEMA",
            )
            need(
                (descriptor["terminal"] == "EOF") == (row[4] == row[5]),
                "SCHEMA_ONLY_TERMINAL",
            )
            values += [
                tuple(table.column(i)[j].as_py() for i in range(table.num_columns))
                for j in range(table.num_rows)
            ]
        expected = [tuple(r) for r in rows if r[0] > threshold]
        # Production fresh-reader positions must equal the independent decode.
        need(
            [tuple(_plain(c) for c in r) for r in read["rows"]] == values,
            "READER_POSITIONS",
        )
        need(
            read["frontier"] == frontiers[-1] and read["recorded"] == "RECORDED", "READ"
        )
        end, terminal = ends[generation], terminals[capture[2]]
        outcome = json.loads(terminal[3])
        observed = result["capture"]
        need(terminal[1] == "OUTCOME", "TERMINAL")
        need(max((b for _a, b in extents), default=0) <= end[1], "EXTENT")
        if case == "A_late":
            # A durable prefix, then a cancelled source: no completion claim.
            need(
                len(values) == 2
                and not Counter(values) - Counter(expected)
                and extents == [(0, 2)]
                and end[1:3] == (2, observed["terminal"])
                and observed["terminal"] != "EOF"
                and outcome["source"] != "EOF"
                and outcome["delivery"] == "FAILED"
                and outcome["cancel"][0] is True
                and observed["control"]["requested"] is True,
                "LATE_PREFIX",
            )
        else:
            need(Counter(values) == Counter(expected), "VALUES")
            need(
                end[1:3] == (len(expected), "EOF")
                and frontiers[-1] == len(expected)
                and outcome["source"] == "EOF"
                and outcome["transaction"] == "COMMIT_ACK"
                and outcome["delivery"] == "COMPLETE",
                "TERMINAL_LAYERS",
            )
        need(
            outcome["local_durable_result"] == "NOT_IMPLEMENTED",
            "S10_OUTCOME_UNCHANGED",
        )
        if case == "empty":
            need(extents == [(0, 0)] and frontiers == [0], "EMPTY_SCHEMA_CHUNK")
        elif case == "A":
            published = observed["published"]
            need(
                [p["frontier"] for p in published] == [2, 2, len(expected)]
                and published[1]["committed"] == [[0, 2], [4, len(expected)]]
                and published[1]["holes"] == [[2, 4]],
                "HOLE_HISTORY",
            )
        else:
            need(frontiers == [b for _a, b in extents], "IN_ORDER")
        total += len(ordered)
        values_total += len(values)
    need(len(contracts) == 1, "CONTRACT_IDENTITY")
    need(not store["retention"] and not store["retention_release"], "NO_RETENTION")
    return {"generations": len(plan), "chunks": total, "rows": values_total}


def _rewrite_chunk(workspace, store_path, chunk, descriptor=None, frame=None):
    """Re-encode one file coherently and update its row: counts/checksums agree."""
    path = Path(workspace) / "chunks" / (chunk + ".chunk")
    text, old, old_frame = parse_chunk(path.read_bytes())
    frame = old_frame if frame is None else frame
    descriptor = dict(old if descriptor is None else descriptor)
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
    return descriptor


def check_bridge_damage(
    backup, workspace, registration, data, reads, rows, *, target, scratch
):
    """Coordinated file + descriptor + row + copied-identity changes must refuse."""
    import importlib

    pa: Any = importlib.import_module("pyarrow")

    scratch = Path(scratch)
    scratch.mkdir(mode=0o700)
    plan = {
        (route, case): generation
        for route, group in registration["plan"]
        for case, _t, _r, generation in group
    }
    route = registration["plan"][0][0]
    rejected = []
    for kind in (
        "outer_byte",
        "missing_file",
        "copied_identity",
        "same_type_value",
        "shifted_extent",
        "member_drop",
    ):
        root = scratch / kind
        root.mkdir(mode=0o700)
        shutil.copytree(Path(workspace) / "chunks", root / "chunks")
        store_path = root / "store.sqlite"
        shutil.copyfile(backup, store_path)
        store = load(store_path)
        by_generation: dict[str, list] = {}
        for row in sorted(store["chunk"], key=lambda r: (r[2], r[4])):
            by_generation.setdefault(row[2], []).append(row)
        a = by_generation[plan[(route, "A")]]
        again = by_generation[plan[(route, "A_again")]]
        b = by_generation[plan[(route, "B")]]
        if kind == "outer_byte":
            path = root / "chunks" / a[0][7]
            raw = bytearray(path.read_bytes())
            raw[len(raw) // 2] ^= 1
            path.write_bytes(bytes(raw))
        elif kind == "missing_file":
            (root / "chunks" / a[1][7]).unlink()
        elif kind == "copied_identity":
            # Same values (A and A_again share a threshold), same sizes and a
            # self-consistent digest, but another generation's descriptor.
            shutil.copyfile(root / "chunks" / a[0][7], root / "chunks" / again[0][7])
            copied = (root / "chunks" / again[0][7]).read_bytes()
            with closing(sqlite3.connect(store_path)) as c:
                c.execute(
                    "UPDATE chunk SET bytes = ?, digest = ?, descriptor = ?"
                    " WHERE identity = ?",
                    (
                        len(copied),
                        hashlib.sha256(copied).hexdigest(),
                        parse_chunk(copied)[0],
                        again[0][0],
                    ),
                )
                c.commit()
        elif kind == "same_type_value":
            path = root / "chunks" / a[0][7]
            _text, descriptor, frame = parse_chunk(path.read_bytes())
            table = decode_frame(frame, a[0][5] - a[0][4], descriptor["contract"])[1]
            column = table.column(0).to_pylist()
            column[0] = 123456789
            changed = table.set_column(
                0, table.schema.field(0), pa.array(column, pa.int64())
            )
            sink = pa.BufferOutputStream()
            with pa.ipc.new_stream(sink, changed.schema) as writer:
                for batch in changed.to_batches():
                    writer.write_batch(batch)
            payload = sink.getvalue().to_pybytes()
            header = FRAME.unpack_from(frame)
            frame = (
                FRAME.pack(
                    header[0],
                    header[1],
                    header[2],
                    len(payload),
                    header[4],
                    hashlib.sha256(payload).digest(),
                )
                + payload
            )
            _rewrite_chunk(root, store_path, a[0][0], frame=frame)
        elif kind == "shifted_extent":
            last = b[-1]
            _text, descriptor, _frame = parse_chunk(
                (root / "chunks" / last[7]).read_bytes()
            )
            descriptor = {**descriptor, "start": last[4] + 1, "stop": last[5] + 1}
            _rewrite_chunk(root, store_path, last[0], descriptor=descriptor)
            with closing(sqlite3.connect(store_path)) as c:
                c.execute(
                    "UPDATE chunk SET start = ?, stop = ? WHERE identity = ?",
                    (last[4] + 1, last[5] + 1, last[0]),
                )
                for checkpoint in c.execute(
                    "SELECT checkpoint FROM checkpoint_member WHERE chunk = ?",
                    (last[0],),
                ).fetchall():
                    ranges = c.execute(
                        "SELECT k.start, k.stop FROM checkpoint_member m JOIN chunk k"
                        " ON k.identity = m.chunk WHERE m.checkpoint = ?",
                        checkpoint,
                    ).fetchall()
                    c.execute(
                        "UPDATE checkpoint SET frontier = ? WHERE identity = ?",
                        (frontier(ranges), checkpoint[0]),
                    )
                c.commit()
        else:
            with closing(sqlite3.connect(store_path)) as c:
                final = c.execute(
                    "SELECT identity FROM checkpoint WHERE generation = ?"
                    " ORDER BY ordinal DESC LIMIT 1",
                    (plan[(route, "B")],),
                ).fetchone()[0]
                c.execute(
                    "DELETE FROM checkpoint_member WHERE checkpoint = ? AND chunk = ?",
                    (final, b[-1][0]),
                )
                ranges = c.execute(
                    "SELECT k.start, k.stop FROM checkpoint_member m JOIN chunk k"
                    " ON k.identity = m.chunk WHERE m.checkpoint = ?",
                    (final,),
                ).fetchall()
                c.execute(
                    "UPDATE checkpoint SET members = ?, frontier = ?, rows = ?"
                    " WHERE identity = ?",
                    (
                        len(ranges),
                        frontier(ranges),
                        sum(y - x for x, y in ranges),
                        final,
                    ),
                )
                c.commit()
        try:
            check_bridge_store(
                store_path, root, registration, data, reads, rows, target=target
            )
        except (ValueError, OSError) as error:
            rejected.append([kind, str(error)])
            continue
        raise ValueError("S12_DAMAGE_ACCEPTED:" + kind)
    shutil.rmtree(scratch)
    return rejected


def _atom(value):
    """Exact identity of a decoded value: float bits, Decimal tuple, UUID bytes."""
    from datetime import datetime
    from decimal import Decimal
    from uuid import UUID

    if type(value) is float:
        return ("float", struct.pack(">d", value))
    if type(value) is Decimal:
        return ("decimal", value.as_tuple())
    if type(value) is UUID:
        return ("uuid", value.bytes)
    if type(value) is bytes and len(value) == 16:
        return ("uuid", value)
    if type(value) is datetime:
        return ("datetime", value.isoformat(), value.tzinfo)
    return (type(value).__name__, value)


def check_suite(data, backups):
    """Execution-profile captures against the literal seven-scalar oracles."""
    import _pietto_phase68_slice12_probe as probe
    from _pietto_phase67_result_product_probe import TEMPORAL_LABELS
    from _pietto_phase68_slice4_probe import s01

    oracle = {
        "seven39": (probe.SEVEN_ROWS, [(0, 2), (2, 4), (4, 5)], [2, 2, 5]),
        "seven65": (probe.SEVEN65_ROWS, [(0, 2), (2, 3)], [2, 3]),
        "empty": ((), [(0, 0)], [0]),
        "late": (probe.SEVEN_ROWS[:2], [(0, 2)], [2]),
        "full_last": (probe.SEVEN_ROWS[:4], [(0, 2), (2, 4)], [2, 4]),
    }
    need(set(data["cases"]) == set(oracle), "SUITE_CASES")
    contracts = {}
    summary = {}
    for name, (rows, extents, frontiers) in oracle.items():
        case = data["cases"][name]
        store = load(backups[name])
        need(store["user_version"] == 2, "VERSION")
        (capture,) = store["capture"]
        chunks, ordered, observed, history = _chain(store, capture[0])
        need(history == frontiers, "FRONTIER_HISTORY")
        need(observed == extents, "EXTENTS")
        decoded = []
        for member in ordered:
            row = chunks[member]
            raw = (Path(case["workspace"]) / "chunks" / row[7]).read_bytes()
            need(
                hashlib.sha256(raw).hexdigest() == row[9] and len(raw) == row[8], "FILE"
            )
            text, descriptor, frame = parse_chunk(raw)
            need(text == row[10] and descriptor["chunk"] == row[0], "DESCRIPTOR")
            need(
                (descriptor["terminal"] == "EOF") == (name == "empty")
                and descriptor["coordinates"] is None,
                "DESCRIPTOR_FIELDS",
            )
            batches, table = decode_frame(frame, row[5] - row[4], capture[4])
            need(batches == row[6] == (0 if name == "empty" else 1), "BATCHES")
            need(
                [f.name for f in table.schema] == list(TEMPORAL_LABELS)
                and all(f.nullable for f in table.schema),
                "SCHEMA_FIELDS",
            )
            precision = 65 if name == "seven65" else 39
            need(
                str(table.schema.field(8).type).endswith(
                    f"({precision}, {30 if precision == 65 else 4})"
                ),
                "DECIMAL_SCHEMA",
            )
            need(
                [[f.name, str(f.type), f.nullable] for f in table.schema]
                == case["schemas"][ordered.index(member)],
                "READER_SCHEMA",
            )
            decoded += [
                tuple(table.column(i)[j].as_py() for i in range(table.num_columns))
                for j in range(table.num_rows)
            ]
        need(
            [tuple(map(_atom, r)) for r in decoded]
            == [tuple(map(_atom, r)) for r in rows],
            "VALUES",
        )
        need(
            [[s01.scalar(v) for v in r] for r in rows] == case["values"],
            "READER_VALUES",
        )
        end = store["capture_end"][0]
        outcome = json.loads(store["attempt_terminal"][0][3])
        need(case["layers"]["source"] == outcome["source"], "LAYERS")
        if name == "late":
            need(
                case["failure"] == "ResultError:VALUE_DOMAIN"
                and end[1:3] == (2, "INCOMPLETE")
                and outcome["source"] == "INCOMPLETE"
                and outcome["delivery"] == "FAILED"
                and outcome["transaction"] == "ROLLBACK_ACK",
                "LATE_PREFIX",
            )
        else:
            need(
                case["failure"] is None
                and end[1:3] == (len(rows), "EOF")
                and outcome["source"] == "EOF"
                and case["calls"] == len(extents) + 1,
                "EOF_TERMINAL",
            )
        need(case["summary"]["integrity"] == "VERIFIED", "VERIFIED")
        contracts[name] = capture[4]
        summary[name] = {"rows": len(decoded), "chunks": len(ordered)}
    need(
        len({contracts[n] for n in ("seven39", "empty", "late", "full_last")}) == 1
        and contracts["seven65"] != contracts["seven39"],
        "CONTRACT_IDENTITY",
    )
    need(
        data["cases"]["seven39"]["controls"]["wrong_trust"] == "JOB_TRUST_INPUT",
        "TRUST",
    )
    need(
        data["damages"]
        == {
            "missing": "CHUNK_MISSING",
            "truncated": "CHUNK_SIZE",
            "byte": "CHUNK_DIGEST",
            "coordinated": "CHUNK_DESCRIPTOR",
        },
        "READER_DAMAGE",
    )
    need(
        data["cases"]["seven65"]["controls"]["foreign_output"] == "READER_SNAPSHOT",
        "FOREIGN_OUTPUT",
    )
    return summary


def check_representative_store(backup, facts, record):
    """One capture of a representative attempt: chain, files and position values."""
    from _pietto_phase68_slice4_probe import s01

    store = load(backup)
    need(store["user_version"] == 2, "VERSION")
    captures = [r for r in store["capture"] if r[0] == facts["generation"]]
    need(len(captures) == 1 and captures[0][2] == facts["attempt"], "CAPTURE")
    capture = captures[0]
    refined = capture[3] == "REFINED"
    need(
        refined == (facts["kind"] == "REFINED") and (capture[5] != "null") == refined,
        "KIND",
    )
    scheme = json.loads(capture[5])
    chunks, ordered, extents, _frontiers = _chain(store, capture[0])
    rows, keys = [], []
    for member in ordered:
        row = chunks[member]
        raw = (Path(facts["workspace"]) / "chunks" / row[7]).read_bytes()
        need(hashlib.sha256(raw).hexdigest() == row[9], "FILE_DIGEST")
        text, descriptor, frame = parse_chunk(raw)
        need(
            text == row[10]
            and (descriptor["chunk"], descriptor["start"], descriptor["stop"])
            == (row[0], row[4], row[5])
            and descriptor["contract"] == capture[4],
            "DESCRIPTOR",
        )
        batches, table = decode_frame(frame, row[5] - row[4], capture[4])
        need(batches == row[6], "BATCHES")
        coordinates: Any = descriptor["coordinates"]
        if refined:
            need(
                type(coordinates) is list
                and len(coordinates) == row[5] - row[4]
                and all(len(k) == len(scheme["coordinates"]) for k in coordinates),
                "COORDINATES",
            )
            keys += [json.dumps(k) for k in coordinates]
        else:
            need(coordinates is None, "ORDINARY_COORDINATES")
        rows += [
            [s01.scalar(table.column(i)[j].as_py()) for i in range(table.num_columns)]
            for j in range(table.num_rows)
        ]
    need(len(keys) == len(set(keys)), "COORDINATE_OCCURRENCE")
    # The independent decode equals the S10-checked values in exact positions.
    need(rows == record["rows"], "POSITIONS")
    need(
        [tuple(e[:2]) for e in facts["extents"]] == extents
        and frontier(extents) == facts["frontier"] == len(rows),
        "EXTENTS",
    )
    end = [r for r in store["capture_end"] if r[0] == capture[0]]
    need(len(end) == 1 and end[0][1] == len(rows), "END")
    terminal = [r for r in store["attempt_terminal"] if r[0] == capture[2]]
    outcome = json.loads(terminal[0][3])
    need(outcome["source"] == record["outcome"]["source"] == end[0][2], "TERMINAL")
    if not rows:
        need(extents == [(0, 0)] and outcome["source"] == "EOF", "EMPTY_SCHEMA")
    return {"chunks": len(ordered), "rows": len(rows), "refined": refined}
