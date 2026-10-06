"""Independent S15 delivery checker over static SQLite backups, chunk bytes and
literal oracles.

It decodes chunks with pyarrow itself (the S12 checker's frame parser), decodes
every sink row's typed wires with its own closed decoder and recomputes digests,
keys and frontiers from raw rows. It never calls the production delivery, sink,
snapshot, reader or codec, so production code cannot generate its own expected
values, keys, positions or history.
"""

from __future__ import annotations

from contextlib import closing
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any
from uuid import UUID, uuid4

from _pietto_phase68_slice12_check import _atom, decode_frame, frontier, parse_chunk

STORE_TABLES = (
    "generation",
    "capture",
    "capture_end",
    "chunk",
    "checkpoint",
    "checkpoint_member",
    "stream",
    "stream_window",
    "stream_session",
    "stream_issuance",
    "sink_observation",
    "stream_retirement",
    "operation",
)
SINK_TABLES = ("sink", "effect")
SINK_FORMAT = "pietto.reference-sink.v1"
LAYOUT_FORMAT = "pietto.sink-layout.v1"
SEVEN_FIELDS = [
    ["occurred_at", "Timestamp"],
    ["maybe_time", "Timestamp"],
    ["key_value", "UUID"],
    ["maybe_key", "UUID"],
    ["number", "Int"],
    ["flag", "Bool"],
    ["ratio", "Float"],
    ["label", "Text"],
    ["amount", "Decimal"],
]


def need(condition, code):
    if not condition:
        raise ValueError("S15_CHECK_" + code)


def load(backup, tables) -> dict[str, Any]:
    """A static backup copy only; never a live store or sink database."""
    with closing(
        sqlite3.connect("file:" + str(backup) + "?mode=ro&immutable=1", uri=True)
    ) as c:
        return {t: [tuple(r) for r in c.execute(f"SELECT * FROM {t}")] for t in tables}


def canonical(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(layout: str, payload: str) -> str:
    return hashlib.sha256(canonical([layout, payload]).encode("utf-8")).hexdigest()


def decode_wire(value) -> Any:
    """Closed independent decoder of one typed wire."""
    need(type(value) is list and value, "WIRE")
    wire: Any = value
    kind = wire[0]
    if kind == "NoneType":
        need(wire == ["NoneType", None], "WIRE")
        return None
    if kind in ("int", "bool", "str"):
        need(len(wire) == 2 and type(wire[1]).__name__ == kind, "WIRE")
        return wire[1]
    if kind == "float":
        need(len(wire) == 2 and type(wire[1]) is str, "WIRE")
        return float.fromhex(wire[1])
    if kind == "decimal":
        need(len(wire) == 4 and wire[1] in (0, 1), "WIRE")
        return Decimal((wire[1], tuple(wire[2]), wire[3]))
    if kind == "datetime":
        need(len(wire) == 3 and wire[2] in (0, 1), "WIRE")
        return datetime.fromisoformat(wire[1]).replace(fold=wire[2])
    if kind == "uuid":
        need(len(wire) == 2, "WIRE")
        return UUID(bytes=bytes.fromhex(wire[1]))
    raise ValueError("S15_CHECK_WIRE")


def literal_rows(precision, spec) -> list[tuple]:
    """The S12 literal fixture rows a case delivered (outside every worker)."""
    import _pietto_phase68_slice12_probe as s12

    source = s12.SEVEN65_ROWS if precision == 65 else s12.SEVEN_ROWS
    return [source[i] for batch in spec if batch != "LATE" for i in batch]


def chunk_rows(store, workspace_root, generation) -> list[tuple]:
    """The latest checkpoint's contiguous prefix, decoded from chunk bytes."""
    chunks = {r[0]: r for r in store["chunk"] if r[2] == generation}
    capture = next(r for r in store["capture"] if r[0] == generation)
    latest = max(
        (r for r in store["checkpoint"] if r[2] == generation), key=lambda r: r[3]
    )
    members = sorted(
        (chunks[m] for k, m, _g in store["checkpoint_member"] if k == latest[0]),
        key=lambda r: (r[4], r[5]),
    )
    rows: list[tuple] = []
    for chunk in members:
        if chunk[4] != len(rows) or chunk[4] == chunk[5]:
            break
        data = (Path(workspace_root) / "chunks" / chunk[7]).read_bytes()
        need(hashlib.sha256(data).hexdigest() == chunk[9], "CHUNK_DIGEST")
        _text, _descriptor, frame = parse_chunk(data)
        _batches, table = decode_frame(frame, chunk[5] - chunk[4], capture[4])
        rows.extend(
            tuple(table.column(i)[j].as_py() for i in range(table.num_columns))
            for j in range(table.num_rows)
        )
    return rows


def atoms(row) -> list:
    return [_atom(v) for v in row]


def check_sink(store, sink, stream, rows, workspace, generation, encode=None) -> dict:
    """One stream's sink rows against its registration, observations and rows.

    `rows` are the expected rows in the encoding `encode` gives decoded values
    (default: the S12 checker's exact atoms)."""
    encode = atoms if encode is None else encode
    found = [r for r in store["stream"] if r[0] == stream]
    need(len(found) == 1, "STREAM")
    registered = found[0]
    need(len(sink["sink"]) == 1, "SINK_IDENTITY")
    singleton = sink["sink"][0]
    need(singleton[2] == SINK_FORMAT, "SINK_FORMAT")
    need(
        (singleton[1], singleton[3], singleton[4], singleton[5])
        == (registered[8], registered[9], registered[10], registered[11]),
        "DESTINATION",
    )
    layout = registered[7]
    shape = json.loads(layout)
    need(canonical(shape) == layout and shape["format"] == LAYOUT_FORMAT, "LAYOUT")
    capture = next(r for r in store["capture"] if r[0] == generation)
    need(shape["contract"] == capture[4] == registered[5], "LAYOUT_CONTRACT")
    effects = sorted(sink["effect"], key=lambda r: r[2])
    need([e[2] for e in effects] == list(range(len(rows))), "EFFECT_POSITIONS")
    need(all((e[0], e[1]) == (workspace, generation) for e in effects), "EFFECT_KEY")
    need(
        len({e[6] for e in effects}) == len({e[7] for e in effects}) == len(effects),
        "EFFECT_COMMIT",
    )
    for effect, expected in zip(effects, rows, strict=True):
        need(effect[3] == layout, "EFFECT_LAYOUT")
        need(effect[5] == digest(effect[3], effect[4]), "EFFECT_DIGEST")
        payload = json.loads(effect[4])
        need(canonical(payload) == effect[4], "PAYLOAD_CANONICAL")
        values = [decode_wire(w) for w in payload["values"]]
        need(
            encode(values) == (atoms(expected) if encode is atoms else expected),
            "EFFECT_VALUE",
        )
    observations = sorted(r for r in store["sink_observation"] if r[0] == stream)
    by_position = {e[2]: e for e in effects}
    need([o[1] for o in observations] == list(range(len(rows))), "OBSERVATIONS")
    for o in observations:
        effect = by_position.get(o[1])
        need(
            effect is not None
            and (o[6], o[7], o[8]) == (effect[6], effect[7], effect[5]),
            "OBSERVATION_EFFECT",
        )
    reached = frontier([(o[1], o[1] + 1) for o in observations])
    confirmed = [
        json.loads(r[5])
        for r in sorted(store["operation"])
        if r[2] == "confirm_sink" and json.loads(r[4]).get("stream") == stream
    ]
    need(not confirmed or confirmed[-1]["position"] == reached, "FRONTIER")
    need(reached == len(rows), "FRONTIER")
    return {
        "effects": len(effects),
        "frontier": reached,
        "payloads": [e[4] for e in effects],
        "sequences": [e[7] for e in effects],
    }


def check_case(name, spec, relay, deliver, backup) -> dict:
    """All sinks of one case: literal values, one effect per key, equal rows."""
    precision, plan = spec
    expected = literal_rows(precision, plan)
    store = load(backup["store"], STORE_TABLES)
    workspace, generation = relay["identity"], relay["generation"]
    decoded = chunk_rows(store, relay["workspace"], generation)
    need([atoms(r) for r in decoded] == [atoms(r) for r in expected], "CHUNK_VALUES")
    for registered in store["stream"]:
        shape = json.loads(registered[7])
        need(
            [[f[1], f[3]] for f in shape["fields"]] == SEVEN_FIELDS
            and shape["multiplicity"] == ["bag"]
            and shape["scheme"] is None,
            "LAYOUT_FIELDS",
        )
    results = {
        "relay": check_sink(
            store,
            load(backup["sinks"]["relay"], SINK_TABLES),
            relay["stream"],
            expected,
            workspace,
            generation,
        )
    }
    for rows, item in deliver["batches"].items():
        results["batch" + rows] = check_sink(
            store,
            load(backup["sinks"]["batch" + rows], SINK_TABLES),
            item["stream"],
            expected,
            workspace,
            generation,
        )
        extents = [list(x[:2]) for x in item["issued"]]
        size = int(rows)
        need(
            extents
            == [
                [a, min(a + size, len(expected))] for a in range(0, len(expected), size)
            ],
            "BATCH_EXTENTS",
        )
        need(
            all(x[2] == ["COMMITTED"] * (x[1] - x[0]) for x in item["issued"]), "STATUS"
        )
    bridge = deliver["bridge"]
    results["bridge"] = check_sink(
        store,
        load(backup["sinks"]["bridge"], SINK_TABLES),
        bridge["stream"],
        expected,
        workspace,
        generation,
    )
    need(bridge["end"][1:] == [len(expected), len(expected)], "BRIDGE_END")
    payloads = {key: value["payloads"] for key, value in results.items()}
    # Batch layout, sessions, bridge or relay never change an occurrence's row.
    need(len({json.dumps(p) for p in payloads.values()}) == 1, "PAYLOAD_STABILITY")
    rows = payloads["relay"]
    equal = [
        (p, q)
        for p in range(len(rows))
        for q in range(p + 1, len(rows))
        if rows[p] == rows[q]
    ]
    need(
        equal
        == [
            (p, q)
            for p in range(len(expected))
            for q in range(p + 1, len(expected))
            if atoms(expected[p]) == atoms(expected[q])
        ],
        "EQUAL_VALUES",
    )
    first = relay["first"]
    if expected:
        # A sink effect committed while the source had not ended.
        need(
            isinstance(first, dict)
            and first["source"] == "READING"
            and first["terminal"] is None
            and first["sink_rows"][0][3] == 1,
            "BEFORE_EOF",
        )
    else:
        need(first is None and deliver["batches"]["1"]["waiting"]["complete"], "EMPTY")
        schema = deliver["batches"]["1"]["waiting"]["schema"]
        need([f[0] for f in schema] == [f[0] for f in SEVEN_FIELDS], "EMPTY_SCHEMA")
    if relay["failure"] is not None:
        need(relay["end"]["observed"] >= len(expected), "LATE")
        need(
            not any(r[2] == "EOF" for r in store["capture_end"] if r[0] == generation),
            "LATE",
        )
    need(
        deliver["refusal"] == "STREAM_EXISTS"
        and deliver["redelivered"] == len(expected),
        "RELAY_REOPEN",
    )
    return {
        "rows": len(expected),
        "equal_pairs": equal,
        "sinks": {k: v["effects"] for k, v in results.items()},
    }


def check_suite(cases, relay, deliver, backups) -> dict:
    report = {}
    for name, spec in cases.items():
        report[name] = check_case(
            name, spec, relay["cases"][name], deliver["cases"][name], backups[name]
        )
    return report


DAMAGES = {
    # name -> (target backup, statement, expected check code)
    "payload": ("sink", None, "EFFECT_VALUE"),
    "receipt": ("store", None, "OBSERVATION_EFFECT"),
    "epoch": ("sink", "UPDATE sink SET epoch = epoch + 1", "DESTINATION"),
    "retention": (
        "sink",
        "UPDATE sink SET retention = retention || ' '",
        "DESTINATION",
    ),
    "frontier": (
        "store",
        "DELETE FROM sink_observation WHERE position = 1",
        "OBSERVATIONS",
    ),
    "omitted": ("sink", "DELETE FROM effect WHERE position = 2", "EFFECT_POSITIONS"),
    "identity": (
        "sink",
        "UPDATE effect SET generation = 'gen-' || hex(randomblob(16))"
        " WHERE position = 0",
        "EFFECT_KEY",
    ),
}


def damages(name, spec, relay, deliver, backup, scratch) -> dict:
    """Coordinated damages of real records with valid digests must be refused."""
    outcome = {}
    for label, (target, statement, code) in DAMAGES.items():
        copy = scratch / (name + "-" + label + "-" + target + ".sqlite")
        source = backup["sinks"]["relay"] if target == "sink" else backup["store"]
        shutil.copyfile(source, copy)
        with closing(sqlite3.connect(copy)) as c:
            if label == "payload":
                row = c.execute(
                    "SELECT layout, payload FROM effect WHERE position = 1"
                ).fetchone()
                payload = json.loads(row[1])
                wire = payload["values"][5]
                payload["values"][5] = (
                    ["bool", not wire[1]] if wire[0] == "bool" else ["bool", True]
                )
                text = canonical(payload)
                # The digest is recomputed: the damage is coordinated and valid.
                c.execute(
                    "UPDATE effect SET payload = ?, digest = ? WHERE position = 1",
                    (text, digest(row[0], text)),
                )
            elif label == "receipt":
                # A well-formed receipt naming a commit the sink never made.
                c.execute(
                    "UPDATE sink_observation SET commit_identity = ? WHERE position = 1",
                    ("skc-" + uuid4().hex,),
                )
            else:
                c.execute(statement)
            c.commit()
        damaged = dict(backup, sinks=dict(backup["sinks"]))
        if target == "sink":
            damaged["sinks"]["relay"] = copy
        else:
            damaged["store"] = copy
        try:
            check_case(name, spec, relay, deliver, damaged)
        except ValueError as error:
            outcome[label] = str(error)
        else:
            outcome[label] = "ACCEPTED"
        need(outcome[label] == "S15_CHECK_" + code, "DAMAGE_" + label.upper())
    return outcome


def check_native(record, store_facts, store_backup, sinks, oracle) -> dict:
    """One joined native history: relay before the source ended, preserved
    pre-crash effects, the recovered window without repeated effects, the
    driver-free R1 bridge, literal values and refined coordinates."""
    from _pietto_phase68_slice4_probe import s01

    def encode(values):
        return [s01.scalar(v) for v in values]

    from collections import Counter

    def bag(items):
        return Counter(json.dumps(row, sort_keys=True) for row in items)

    store = load(store_backup, STORE_TABLES)
    relay, recover = record["relay"], record["recover"]
    adopt, bridge = record["adopt"], record["bridge"]
    workspace, generation = store_facts["identity"], store_facts["generation"]
    # Position order is the refined order of the saved chunks, decoded here from
    # their bytes; the literal oracle is a bag unless it says it is ordered.
    rows = [encode(r) for r in chunk_rows(store, store_facts["workspace"], generation)]
    count = len(rows)
    need(count > 4, "ORACLE")
    need(
        rows == oracle["rows"]
        if oracle["ordered"]
        else bag(rows) == bag(oracle["rows"]),
        "CHUNK_ORACLE",
    )
    # Effects committed while the source had not ended, then the extractor died.
    need(relay["session_gone"][-1] == 0, "RELAY_SESSION")
    need(
        relay["first"] is not None
        and relay["first"]["terminal"] is None
        and relay["first"]["closed"] is False,
        "BEFORE_EOF",
    )
    need([s[0] for s in relay["steps"]].count("DELIVERED") == 2, "RELAY_STEPS")
    need(
        relay["position"] == 4 and [r[0] for r in relay["sink_rows"]] == [0, 1, 2, 3],
        "RELAY_PREFIX",
    )
    original = relay["attempt"]
    need(all(m[2] == original for m in relay["members"]), "RELAY_MEMBERS")
    # S14 recovery kept the old members and completed the result.
    need(recover["status"] == "COMPLETE" and recover["session_gone"][-1] == 0, "R2")
    need(recover["frontier"] == recover["known"] == count and recover["coverage"], "R2")
    need(
        {tuple(m) for m in relay["members"]} <= {tuple(m) for m in recover["members"]},
        "R2_MEMBERS",
    )
    attempts = {m[2] for m in recover["members"]}
    need(attempts == {original, recover["attempt"]}, "R2_ATTEMPTS")
    # The new window starts at the confirmed prefix; nothing old is resent.
    need(adopt["start"] == 4 and adopt["adopted"]["start"] == 4, "ADOPT")
    need(adopt["adopted"]["stop"] == count and adopt["position"] == count, "ADOPT")
    need(
        [i[:2] for i in adopt["issued"]]
        == [[a, min(a + 3, count)] for a in range(4, count, 3)]
        and all(set(i[2]) == {"COMMITTED"} for i in adopt["issued"]),
        "ADOPT_ISSUED",
    )
    need(adopt["waiting"][1:] == [count, count, True], "ADOPT_WAITING")
    first = check_sink(
        store,
        load(sinks["a"], SINK_TABLES),
        store_facts["stream"],
        rows,
        workspace,
        generation,
        encode,
    )
    # Pre-crash effects keep their original commits: positions 0-3 first.
    need(first["sequences"] == list(range(1, count + 1)), "PRESERVED_EFFECTS")
    need(
        [r[2] for r in relay["sink_rows"]]
        == [
            r[6]
            for r in sorted(load(sinks["a"], SINK_TABLES)["effect"], key=lambda r: r[2])
        ][:4],
        "PRESERVED_EFFECTS",
    )
    fresh = bridge["fresh"]
    second = check_sink(
        store,
        load(sinks["b"], SINK_TABLES),
        fresh["stream"],
        rows,
        workspace,
        generation,
        encode,
    )
    need(first["payloads"] == second["payloads"], "PAYLOAD_STABILITY")
    need(
        all(set(s[2]) == {"COMMITTED"} for s in fresh["steps"])
        and fresh["end"][1:] == [count, count],
        "BRIDGE_FRESH",
    )
    again = bridge["again"]
    need(
        all(s[2] == [] for s in again["steps"])
        and again["end"][1:] == [count, count]
        and len(again["rows"]) == count,
        "BRIDGE_AGAIN",
    )
    # Refined coordinates: each row carries its chunk's own coordinate wires.
    chunks = {r[0]: r for r in store["chunk"] if r[2] == generation}
    latest = max(
        (r for r in store["checkpoint"] if r[2] == generation), key=lambda r: r[3]
    )
    members = sorted(
        (chunks[m] for k, m, _g in store["checkpoint_member"] if k == latest[0]),
        key=lambda r: r[4],
    )
    wires = [key for member in members for key in json.loads(member[10])["coordinates"]]
    payloads = [json.loads(p) for p in first["payloads"]]
    need(
        len(wires) == count and [p["coordinates"] for p in payloads] == wires,
        "COORDINATES",
    )
    return {
        "rows": count,
        "sink_a": first["effects"],
        "sink_b": second["effects"],
        "attempts": len(attempts),
    }
