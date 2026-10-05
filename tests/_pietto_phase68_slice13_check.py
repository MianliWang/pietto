"""Independent S13 replay checker over raw replay records, static SQLite backups
and chunk bytes.

It decodes chunks with pyarrow itself and compares S12's literal oracles; it
never calls the production replay, cursor, snapshot, reader or decoder, so
production code cannot generate its own expected values, positions or history.
"""

from __future__ import annotations

from contextlib import closing
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Any

from _pietto_phase68_slice12_check import _atom, decode_frame, parse_chunk

TABLES = (
    "generation",
    "attempt",
    "capture",
    "chunk",
    "checkpoint",
    "checkpoint_member",
    "capture_end",
    "retention",
    "retention_release",
    "consumer",
    "replay_session",
    "issuance",
    "acknowledgement",
    "operation",
)
SOURCE_KINDS = ("open_attempt", "begin_capture", "publish_chunk", "end_capture")
REPLAY_KINDS = (
    "register_consumer",
    "open_replay",
    "issue_delivery",
    "acknowledge_delivery",
)
CORRUPT = {
    "damage-missing": "CHUNK_MISSING",
    "damage-truncated": "CHUNK_SIZE",
    "damage-byte": "CHUNK_DIGEST",
    "damage-swapped": "CHUNK_SIZE",
    "damage-coordinated": "CHUNK_DESCRIPTOR",
}
REFUSALS = {
    "refuse": {
        "complete_on_hole": "CONSUMER_SCOPE",
        "beyond_frontier": "ACCEPTANCE_EXTENT",
        "wrong_pin": "JOB_TRUST_INPUT",
        "wrong_producer": "JOB_TRUST_INPUT",
        "wrong_route": "ACCEPTANCE_ROUTE",
        "wrong_value": "BINDING_VECTOR",
        "purpose_change": "ACCEPTANCE_SUBJECT",
    },
    "late-complete": {"complete": "CONSUMER_SCOPE"},
}


def need(condition, code):
    if not condition:
        raise ValueError("S13_CHECK_" + code)


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


def literal(name) -> list:
    """S12's literal rows in captured position order (the checked stream order)."""
    import _pietto_phase68_slice12_probe as s12
    from _pietto_phase68_slice13_probe import CASES

    precision, spec, _order = CASES[name]
    source = s12.SEVEN65_ROWS if precision == 65 else s12.SEVEN_ROWS
    rows: list = []
    for batch in spec:
        if batch == "LATE":
            break
        rows += [source[i] for i in batch]
    return rows


def decoded(store, workspace, checkpoint):
    """One checkpoint's members decoded independently: rows by position."""
    chunks = {r[0]: r for r in store["chunk"]}
    contract = {r[0]: r[4] for r in store["capture"]}
    members = sorted(
        (chunks[m[1]] for m in store["checkpoint_member"] if m[0] == checkpoint),
        key=lambda r: (r[4], r[5]),
    )
    rows, schema, coordinates, ranges = {}, None, {}, []
    for row in members:
        raw = (Path(workspace) / "chunks" / row[7]).read_bytes()
        need(len(raw) == row[8] and hashlib.sha256(raw).hexdigest() == row[9], "FILE")
        text, descriptor, frame = parse_chunk(raw)
        need(text == row[10] and descriptor["chunk"] == row[0], "DESCRIPTOR")
        _batches, table = decode_frame(frame, row[5] - row[4], contract[row[2]])
        if schema is None:
            schema = [[f.name, str(f.type), f.nullable] for f in table.schema]
        for j in range(table.num_rows):
            rows[row[4] + j] = tuple(
                table.column(i)[j].as_py() for i in range(table.num_columns)
            )
            if descriptor["coordinates"] is not None:
                coordinates[row[4] + j] = descriptor["coordinates"][j]
        ranges.append((row[4], row[5]))
    return rows, schema, coordinates, ranges


def consumer_store(store, consumer):
    """Sessions, issuances and the acknowledgement chain of one consumer."""
    rows = [r for r in store["consumer"] if r[0] == consumer]
    need(len(rows) == 1, "CONSUMER_ROW")
    row = rows[0]
    sessions = sorted(
        (r for r in store["replay_session"] if r[1] == consumer), key=lambda r: r[2]
    )
    need([s[2] for s in sessions] == list(range(1, len(sessions) + 1)), "ORDINALS")
    issued = {r[0]: r for r in store["issuance"] if r[1] == consumer}
    acks = {r[0]: r for r in store["acknowledgement"] if r[1] == consumer}
    chain, position = sorted((a[3], a[4]) for a in acks.values()), 0
    for start, stop in chain:
        need(start == position and stop > start, "ACK_CHAIN")
        position = stop
    for identity, ack in acks.items():
        need(
            identity in issued
            and issued[identity][2:3] + issued[identity][4:6]
            == (ack[2], ack[3], ack[4]),
            "ACK_ISSUANCE",
        )
    retention = [r for r in store["retention"] if r[0] == row[5]]
    need(
        len(retention) == 1
        and retention[0][2:4] == (row[2], row[3])
        and json.loads(retention[0][4]) == {"consumer": consumer, "purpose": row[8]},
        "RETENTION",
    )
    return row, sessions, issued, acks, position


def encoded(rows):
    from _pietto_phase68_slice4_probe import s01

    return [[s01.scalar(v) for v in row] for row in rows]


def walk(
    history,
    items,
    start,
    rows_bound,
    sequence,
    schema,
    generation,
    tally,
    *,
    coordinates=None,
):
    """Contiguous, bounded, exact-value deliveries; returns (position, pending)."""
    position, pending = start, None
    for item in items:
        if "terminal" in item:
            break
        need(pending is None, "ONE_PENDING:" + history)
        need(
            item["start"] == position
            and position < item["stop"] <= len(sequence)
            and item["stop"] - item["start"] <= rows_bound,
            "EXTENT:" + history,
        )
        need(
            item["values"] == encoded(sequence[item["start"] : item["stop"]]),
            "VALUES:" + history,
        )
        need(item["schema"] == schema and item["held"] > 0, "SCHEMA:" + history)
        need(
            item["occurrences"]
            == [[generation, p] for p in range(item["start"], item["stop"])],
            "OCCURRENCES:" + history,
        )
        need(
            item["coordinates"]
            == (
                None
                if coordinates is None
                else coordinates[item["start"] : item["stop"]]
            ),
            "COORDINATES:" + history,
        )
        tally["deliveries"] += 1
        tally["rows"] += item["stop"] - item["start"]
        if item.get("acknowledged"):
            position = item["stop"]
        else:
            pending = item
    return position, pending


def ended(history, item, extent, verified, scope):
    need(
        item["terminal"] == "SAVED_SCOPE_EXHAUSTED"
        and (item["extent"], item["acknowledged"], item["scope"])
        == (extent, extent, scope)
        and item["verified"] == verified,
        "TERMINAL:" + history,
    )


def issuances_match(history, items, issued, acks):
    raw = {item["delivery"]: item for item in items if "delivery" in item}
    need(
        set(raw) == set(issued)
        and all(
            (issued[d][2], issued[d][4], issued[d][5])
            == (item["session"], item["start"], item["stop"])
            for d, item in raw.items()
        ),
        "ISSUANCES:" + history,
    )
    need(
        {d for d, item in raw.items() if item.get("acknowledged")} <= set(acks),
        "ACKNOWLEDGED:" + history,
    )


def source_free(data):
    for name, worker in data.items():
        need(
            worker.get("connections") == []
            and worker.get("forbidden_calls", []) == []
            and worker.get("installed_drivers", []) == []
            and worker.get("loaded_drivers", []) == [],
            "SOURCE_FREE:" + name,
        )


def no_source_attempts(stores, attempts):
    """R1 never reaches a source: after the first saved-read registration no
    attempt, capture or chunk operation exists; attempts stay as captured."""
    for name, store in stores.items():
        kinds = [o[2] for o in sorted(store["operation"])]
        if "register_consumer" in kinds:
            first = kinds.index("register_consumer")
            need(not set(kinds[first:]) & set(SOURCE_KINDS), "SOURCE_ATTEMPT:" + name)
        need(len(store["attempt"]) == attempts, "ATTEMPTS:" + name)


def check_suite(capture, data, backups, cases, consumers):
    """Every replay record against independent decoding and the static store."""
    from _pietto_phase67_result_product_probe import TEMPORAL_LABELS
    from _pietto_phase68_slice13_probe import suite_histories

    specs = {spec["name"]: spec for spec in suite_histories()}

    source_free(data)
    stores = {name: load(path) for name, path in backups.items()}
    need(all(s["user_version"] == 3 for s in stores.values()), "VERSION")
    no_source_attempts(stores, 1)
    results = {h["history"]: h for worker in data.values() for h in worker["results"]}
    expectations: dict[tuple, Any] = {}

    def expected(case, checkpoint):
        key = (case, checkpoint)
        if key not in expectations:
            source = case
            if case not in capture["cases"]:
                source = "seven65" if case.startswith("cancel") else "seven39"
            rows, schema, coordinates, ranges = decoded(
                stores[source], cases[source]["workspace"], checkpoint
            )
            lit = literal(source)
            need(
                all(
                    tuple(map(_atom, row)) == tuple(map(_atom, lit[p]))
                    for p, row in rows.items()
                ),
                "LITERAL:" + case,
            )
            reached = frontier(ranges)
            expectations[key] = (
                [rows[p] for p in range(reached)],
                schema,
                [coordinates.get(p) for p in range(reached)],
                reached,
            )
        return expectations[key]

    summary = {"histories": 0, "deliveries": 0, "rows": 0, "redelivered": 0}

    def walk_case(history, items, start, rows_bound, sequence, schema, case):
        generation = cases[case]["generation"]
        return walk(
            history, items, start, rows_bound, sequence, schema, generation, summary
        )

    def consumer_matches(history, h, extent, scope):
        store = stores[h["case"]]
        row, sessions, issued, acks, position = consumer_store(store, h["consumer"])
        generation = cases[h["case"]]["generation"]
        bindings = {g[0]: g[2] for g in store["generation"]}
        need(
            row[1:4] == (cases[h["case"]]["job"], generation, h["checkpoint"])
            and row[4] == bindings[generation]
            and (row[6], row[7], row[8]) == (scope, extent, "s13-suite"),
            "CONSUMER:" + history,
        )
        return sessions, issued, acks, position

    rewritten = ("damage-coordinated", "damage-domain", "damage-semantic")
    for name, h in results.items():
        summary["histories"] += 1
        kind, case = h["kind"], h["case"]
        if "verify_store" in h:
            need(
                h["verify_store"]
                == (
                    "STORE_INVARIANT_CHUNK_HISTORY" if name in rewritten else "ACCEPTED"
                ),
                "VERIFY_STORE:" + name,
            )
        if kind == "refuse":
            need(h["refusals"] == REFUSALS[name], "REFUSALS:" + name)
            continue
        if kind in ("hold_offered", "hold_ack_commit") or name in (
            "required-b",
            "lost-resume",
        ):
            continue  # checked as complete histories below
        sequence, schema, _coordinates, reached = expected(case, h["checkpoint"])
        scope = "complete_capture"
        if name in ("seven39-pinned-hole", "hole0", "late"):
            scope = "committed_prefix"
        need(h["extent"] == reached, "EXTENT_RECOMPUTED:" + name)
        sessions, issued, acks, position = consumer_matches(name, h, reached, scope)
        if kind == "drain":
            rows = specs[name]["rows"]
            at, pending = walk_case(name, h["items"], 0, rows, sequence, schema, case)
            need(pending is None and at == reached == position, "PROGRESS:" + name)
            ended(name, h["items"][-1], reached, [0, reached], scope)
            issuances_match(name, h["items"], issued, acks)
            end = h["items"][-1]
            if name == "empty":
                need(
                    end["schema"] is not None
                    and [f[0] for f in end["schema"]] == list(TEMPORAL_LABELS)
                    and end["schema"] == schema
                    and h["items"][:-1] == [],
                    "EMPTY_SCHEMA",
                )
            elif name == "hole0":
                need(
                    end["schema"] is None
                    and end["holes"] == [[0, 2]]
                    and h["items"][:-1] == [],
                    "HOLE_AT_ZERO",
                )
            elif name == "seven39-pinned-hole":
                latest = capture["cases"]["seven39"]["checkpoints"]["3"][0]
                need(
                    h["checkpoint"] != latest
                    and end["holes"] == [[2, 4]]
                    and end["observed_end"] == 5,
                    "PINNED",
                )
            elif name == "late":
                need(end["layers"]["source"] == "INCOMPLETE", "LATE_LAYERS")
            else:
                need(end["holes"] == [] and end["layers"]["source"] == "EOF", "LAYERS")
        elif kind == "two_sessions":
            at, pending = walk_case(name, h["items"], 0, 3, sequence, schema, case)
            need(pending is not None and at == h["second_start"] == 3, "FIRST:" + name)
            assert pending is not None
            again, none = walk_case(name, h["second"], 3, 2, sequence, schema, case)
            need(none is None and again == reached, "SECOND:" + name)
            redelivered = h["second"][0]
            need(
                redelivered["occurrences"] == pending["occurrences"]
                and redelivered["values"] == pending["values"]
                and redelivered["delivery"] != pending["delivery"]
                and redelivered["session"] != pending["session"],
                "REDELIVERY:" + name,
            )
            summary["redelivered"] += 1
            ended(name, h["second"][-1], reached, [3, reached], scope)
            issuances_match(name, h["items"] + h["second"], issued, acks)
            need([s[3] for s in sessions] == [0, 3], "SESSIONS:" + name)
        elif kind == "corrupt":
            original, *_ = expected("seven39", h["checkpoint"])
            if name == "damage-semantic":
                need("error" not in h, "SEMANTIC_ACCEPTED")
                delivered = [v for item in h["items"][:-1] for v in item["values"]]
                differences = {
                    (p, i)
                    for p, row in enumerate(delivered)
                    for i, cell in enumerate(row)
                    if cell != encoded([original[p]])[0][i]
                }
                need(differences == {(0, 4)}, "SEMANTIC_DETECTED")
                continue
            error = h.get("error")
            need(
                error not in (None, "ACCEPTED") and error == CORRUPT.get(name, error),
                "CORRUPT_CODE:" + name,
            )
            issuances_match(name, h["items"], issued, acks)
            need(
                [(i["start"], i["stop"]) for i in h["items"]] == [(0, 1), (1, 2)]
                and all(i.get("acknowledged") for i in h["items"])
                and [v for i in h["items"] for v in i["values"]]
                == encoded(original[:2])
                and h["after"]["position"] == 2,
                "CORRUPT_PREFIX:" + name,
            )
        elif kind == "late_authority":
            code = "JOB_STATE" if name.startswith("cancel") else "ACCEPTANCE_EXPIRED"
            need(h["error"] == code and h["after"]["position"] == 0, "LATE:" + name)
            if name.endswith("decode"):
                need(
                    h["closed"] is True and h["after"]["issued"] == [], "OFFER:" + name
                )
            else:
                need(
                    h["handed"]["values"] == encoded(sequence[0:2])
                    and [i[2:] for i in h["after"]["issued"]] == [[0, 2, False]],
                    "HANDED:" + name,
                )
        elif kind == "verify":
            need(
                h["verified"]
                == {
                    "integrity": "VERIFIED",
                    "checkpoint": h["checkpoint"],
                    "members": 3,
                    "rows": 5,
                    "frontier": 5,
                },
                "VERIFY",
            )
    # The required example and the lost acknowledgement reply, across real deaths.
    first, resumed = results["required-a"], results["required-b"]
    sequence, schema, _c, reached = expected("seven7", first["checkpoint"])
    need(reached == 7, "SEVEN7")
    at, pending = walk_case(
        "required-a", first["items"], 0, 2, sequence, schema, "seven7"
    )
    need(pending is not None, "REQUIRED_A")
    assert pending is not None
    need(at == 2 and (pending["start"], pending["stop"]) == (2, 4), "REQUIRED_A")
    need(resumed["before"]["position"] == resumed["start"] == 2, "REQUIRED_B_START")
    at, none = walk_case(
        "required-b", resumed["items"], 2, 3, sequence, schema, "seven7"
    )
    need(
        none is None
        and at == 7
        and [(i["start"], i["stop"]) for i in resumed["items"][:-1]]
        == [(2, 5), (5, 7)],
        "REQUIRED_B",
    )
    ended("required-b", resumed["items"][-1], 7, [2, 7], "complete_capture")
    need(
        resumed["items"][0]["values"][:2] == pending["values"]
        and resumed["items"][0]["occurrences"][:2] == pending["occurrences"],
        "REQUIRED_SAME_OCCURRENCES",
    )
    sessions, issued, acks, position = consumer_matches(
        "required", first, 7, "complete_capture"
    )
    need(position == 7 and [s[3] for s in sessions] == [0, 2], "REQUIRED_STORE")
    issuances_match("required", first["items"] + resumed["items"], issued, acks)
    need(
        sorted((a[3], a[4]) for a in acks.values()) == [(0, 2), (2, 5), (5, 7)]
        and pending["delivery"] in issued
        and pending["delivery"] not in acks,
        "REQUIRED_HISTORY",
    )
    lost, after = results["lost-reply"], results["lost-resume"]
    at, pending = walk_case(
        "lost-reply", lost["items"], 0, 2, sequence, schema, "seven7"
    )
    need(pending is not None, "LOST_A")
    assert pending is not None
    need(at == 2 and (pending["start"], pending["stop"]) == (2, 4), "LOST_A")
    need(
        after["query"][:2] == ["acknowledge_delivery", "QUERIED"]
        and after["query"][2]["delivery"] == pending["delivery"]
        and after["query"][2]["position"] == 4
        and after["before"]["position"] == after["start"] == 4,
        "LOST_QUERY",
    )
    at, none = walk_case(
        "lost-resume", after["items"], 4, 3, sequence, schema, "seven7"
    )
    need(none is None and at == 7, "LOST_RESUME")
    ended("lost-resume", after["items"][-1], 7, [4, 7], "complete_capture")
    sessions, issued, acks, position = consumer_matches(
        "lost", lost, 7, "complete_capture"
    )
    need(
        position == 7
        and [s[3] for s in sessions] == [0, 4]
        and sorted((a[3], a[4]) for a in acks.values()) == [(0, 2), (2, 4), (4, 7)]
        and pending["delivery"] in acks,
        "LOST_STORE",
    )
    need(
        consumers == {"required": first["consumer"], "lost": lost["consumer"]},
        "CONSUMER_IDENTITIES",
    )
    return summary


def pilot(capture, data, backups, cases, consumers, scratch):
    """Coordinated damage of real replay records and stores must be rejected."""
    rejected = {}

    def rejects(label, damaged_data, damaged_backups=backups):
        try:
            check_suite(capture, damaged_data, damaged_backups, cases, consumers)
        except ValueError as error:
            rejected[label] = str(error)
            return
        raise AssertionError("S13 checker accepted damage: " + label)

    def edit(label, change):
        damaged = copy.deepcopy(data)
        histories = {h["history"]: h for w in damaged.values() for h in w["results"]}
        change(histories)
        rejects(label, damaged)

    def value(h):
        h["seven7-b2"]["items"][0]["values"][0][4] = {"kind": "int", "value": "-99"}

    def position(h):
        item = h["seven7-b2"]["items"][1]
        item["start"], item["stop"] = item["start"] + 1, item["stop"] + 1

    def session(h):
        items = h["seven39-mid-chunk"]
        items["second"][0]["session"] = items["items"][0]["session"]

    def acknowledgement(h):
        h["required-a"]["items"][1]["acknowledged"] = True

    def ending(h):
        h["seven7-b3"]["items"][-1]["acknowledged"] = 6

    def origin(h):
        h["seven65-b2"]["items"][0]["occurrences"][0][1] = 1

    for label, change in (
        ("data_value", value),
        ("position_shift", position),
        ("session_swap", session),
        ("forged_acknowledgement", acknowledgement),
        ("forged_terminal", ending),
        ("forged_origin", origin),
    ):
        edit(label, change)
    damaged = copy.deepcopy(data)
    damaged["main"]["connections"] = ["socket_connect"]
    rejects("source_contact", damaged)
    store = Path(scratch)
    store.mkdir(mode=0o700)
    forged = store / "seven7-dropped-ack.sqlite"
    shutil.copyfile(backups["seven7"], forged)
    with closing(sqlite3.connect(forged)) as c:
        c.execute("PRAGMA foreign_keys = OFF")
        c.execute(
            "DELETE FROM acknowledgement WHERE consumer = ? AND start = 5",
            (consumers["required"],),
        )
        c.commit()
    rejects("store_dropped_ack", data, {**backups, "seven7": forged})
    return rejected


def holes(ranges, end) -> list:
    missing, position = [], 0
    for start, stop in sorted(ranges):
        if start > position:
            missing.append([position, start])
        position = max(position, stop)
    if end is not None and end > position:
        missing.append([position, end])
    return missing


def check_native(data, backups, cases, histories, attempts, *, refined=False):
    """Native-origin saved inputs recovered after the source DB was stopped."""
    source_free(data)
    stores = {name: load(path) for name, path in backups.items()}
    need(all(s["user_version"] == 3 for s in stores.values()), "VERSION")
    for name, store in stores.items():
        no_source_attempts({name: store}, attempts[name])
    results = {h["history"]: h for worker in data.values() for h in worker["results"]}
    tally = {"histories": 0, "deliveries": 0, "rows": 0, "redelivered": 0}
    for spec in histories:
        name, h = spec["name"], results[spec["name"]]
        case = cases[spec["case"]]
        store = stores[case["store"]]
        rows, schema, coordinates, ranges = decoded(
            store, case["workspace"], h["checkpoint"]
        )
        reached = frontier(ranges)
        sequence = [rows[p] for p in range(reached)]
        coords = [coordinates[p] for p in range(reached)] if refined else None
        scope = spec.get("accept", {}).get("scope", "complete_capture")
        need(h["extent"] == reached, "EXTENT_RECOMPUTED:" + name)
        row, sessions, issued, acks, position = consumer_store(store, h["consumer"])
        bindings = {g[0]: g[2] for g in store["generation"]}
        need(
            row[1:4] == (case["job"], case["generation"], h["checkpoint"])
            and row[4] == bindings[case["generation"]]
            and (row[6], row[7], row[8]) == (scope, reached, "s13-suite"),
            "CONSUMER:" + name,
        )
        end_rows = [e for e in store["capture_end"] if e[0] == case["generation"]]
        observed = end_rows[0][1] if end_rows else None
        generation = case["generation"]
        if spec["kind"] == "drain":
            at, pending = walk(
                name,
                h["items"],
                0,
                spec["rows"],
                sequence,
                schema,
                generation,
                tally,
                coordinates=coords,
            )
            need(pending is None and at == reached == position, "PROGRESS:" + name)
            end = h["items"][-1]
            ended(name, end, reached, [0, reached], scope)
            need(end["holes"] == holes(ranges, observed), "HOLES:" + name)
            if reached == 0 and scope == "complete_capture":
                need(end["schema"] == schema is not None, "EMPTY_SCHEMA:" + name)
            issuances_match(name, h["items"], issued, acks)
        else:
            first, second = spec["rows"]
            at, pending = walk(
                name,
                h["items"],
                0,
                first,
                sequence,
                schema,
                generation,
                tally,
                coordinates=coords,
            )
            need(pending is not None and at == h["second_start"], "FIRST:" + name)
            assert pending is not None
            again, none = walk(
                name,
                h["second"],
                at,
                second,
                sequence,
                schema,
                generation,
                tally,
                coordinates=coords,
            )
            need(none is None and again == reached == position, "SECOND:" + name)
            redelivered = h["second"][0]
            overlap = min(pending["stop"], redelivered["stop"]) - pending["start"]
            need(
                redelivered["start"] == pending["start"]
                and redelivered["values"][:overlap] == pending["values"][:overlap]
                and redelivered["delivery"] != pending["delivery"],
                "REDELIVERY:" + name,
            )
            tally["redelivered"] += 1
            ended(name, h["second"][-1], reached, [at, reached], scope)
            issuances_match(name, h["items"] + h["second"], issued, acks)
            need([s[3] for s in sessions] == [0, at], "SESSIONS:" + name)
        tally["histories"] += 1
    return tally
