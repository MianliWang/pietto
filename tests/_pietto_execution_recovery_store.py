"""Disposable S02 mechanics; neither a product format nor execution authority."""

from contextlib import contextmanager
import hashlib
import json
import os
import sqlite3


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def connection(path):
    db = sqlite3.connect(path, timeout=2, isolation_level=None)
    try:
        mode = db.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        db.execute("PRAGMA synchronous=FULL")
        assert (mode, db.execute("PRAGMA synchronous").fetchone()[0]) == ("wal", 2)
        with (path.parent / "sqlite-connections.jsonl").open("a") as audit:
            audit.write(
                json.dumps(
                    {"pid": os.getpid(), "database": path.name, "profile": profile(db)}
                )
                + "\n"
            )
        yield db
    finally:
        db.close()


def profile(db):
    return {
        "journal": db.execute("PRAGMA journal_mode").fetchone()[0],
        "synchronous": db.execute("PRAGMA synchronous").fetchone()[0],
        "in_transaction": db.in_transaction,
    }


def initialize(directory, binding):
    directory.mkdir(mode=0o700)
    sync_directory(directory.parent)
    with connection(directory / "job.sqlite") as db:
        db.executescript(
            "CREATE TABLE job(binding TEXT NOT NULL, state TEXT NOT NULL);"
            "CREATE TABLE chunks(first INTEGER PRIMARY KEY, last INTEGER, name TEXT, size INTEGER, digest TEXT);"
            "CREATE TABLE acks(position INTEGER PRIMARY KEY);"
        )
        db.execute("INSERT INTO job VALUES (?, 'active')", (encoded(binding).decode(),))
    sync_directory(directory)


def authorize(db, binding, now=0):
    stored, state = db.execute("SELECT binding,state FROM job").fetchone()
    if (
        stored != encoded(binding).decode()
        or state != "active"
        or now >= binding["expires"]
    ):
        raise ValueError("binding, cancellation or retention mismatch")


def persist(directory, binding, rows, cut="none", barrier=lambda data: None):
    if not rows or len(rows) > 64:
        raise ValueError("bounded nonempty chunk required")
    if any(
        len(row) != 4
        or any(
            type(row[i]) is not int or not -(2**63) <= row[i] < 2**63 for i in (0, 1, 3)
        )
        or not (row[2] is None or type(row[2]) is str)
        for row in rows
    ):
        raise ValueError("invalid checked scalar row")
    first, last = rows[0][0], rows[-1][0]
    if [r[0] for r in rows] != list(range(first, last + 1)):
        raise ValueError("noncontiguous occurrence chunk")
    data = encoded(rows)
    if len(data) > 1024 * 1024:
        raise ValueError("chunk bound")
    name = f"chunk-{first}-{last}.json"
    events = []
    with connection(directory / "job.sqlite") as db:
        authorize(db, binding)
        temp = directory / (name + ".pending")
        with temp.open("xb") as stream:
            stream.write(data[: max(1, len(data) // 2)])
            stream.flush()
            if cut == "partial":
                barrier(
                    {"cut": cut, "events": ["partial_write"], "profile": profile(db)}
                )
            stream.write(data[max(1, len(data) // 2) :])
            stream.flush()
            if cut == "fsync_failure":
                # Explicit application fault injection, not observed device failure.
                raise OSError("injected file fsync failure")
            os.fsync(stream.fileno())
        events.append("file_fsync_returned")
        os.link(temp, directory / name)
        temp.unlink()
        sync_directory(directory)
        events.append("namespace_fsync_returned")
        if cut == "orphan":
            barrier({"cut": cut, "events": events, "profile": profile(db)})
        db.execute("BEGIN IMMEDIATE")
        authorize(db, binding)
        if db.execute(
            "SELECT 1 FROM chunks WHERE first <= ? AND last >= ?", (last, first)
        ).fetchone():
            raise ValueError("overlapping chunk")
        db.execute(
            "INSERT INTO chunks VALUES (?,?,?,?,?)",
            (first, last, name, len(data), hashlib.sha256(data).hexdigest()),
        )
        events.append("metadata_insert_uncommitted")
        if cut == "uncommitted":
            barrier({"cut": cut, "events": events, "profile": profile(db)})
        db.execute("COMMIT")
        events.append("metadata_commit_returned")
        if cut == "committed":
            barrier({"cut": cut, "events": events, "profile": profile(db)})
        events.append("checkpoint_ack")
        return {"events": events, "profile": profile(db), "first": first, "last": last}


def reopen(directory, binding, now=0):
    with connection(directory / "job.sqlite") as db:
        authorize(db, binding, now)
        records = db.execute("SELECT * FROM chunks ORDER BY first").fetchall()
        acks = [r[0] for r in db.execute("SELECT position FROM acks ORDER BY position")]
        observed_profile = profile(db)
    rows, frontier = [], 0
    for first, last, name, size, digest in records:
        if name != f"chunk-{first}-{last}.json" or size > 1024 * 1024:
            raise ValueError("invalid reference")
        data = (directory / name).read_bytes()
        if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
            raise ValueError("changed chunk")
        chunk = json.loads(data)
        if [r[0] for r in chunk] != list(range(first, last + 1)):
            raise ValueError("changed occurrence extent")
        rows.extend(chunk)
        if first == frontier + 1:
            frontier = last
    ack_frontier = 0
    for position in acks:
        if position != ack_frontier + 1:
            break
        ack_frontier = position
    return {
        "rows": rows,
        "frontier": frontier,
        "acks": acks,
        "ack_frontier": ack_frontier,
        "references": [list(r) for r in records],
        "profile": observed_profile,
    }


def sink_initialize(path, binding):
    with connection(path) as db:
        db.executescript(
            "CREATE TABLE promise(namespace TEXT, epoch INTEGER, expires INTEGER);"
            "CREATE TABLE effects(job TEXT, position INTEGER, payload TEXT, PRIMARY KEY(job,position));"
        )
        db.execute(
            "INSERT INTO promise VALUES (?,?,?)",
            (binding["namespace"], binding["epoch"], binding["expires"]),
        )
    sync_directory(path.parent)


def effect(path, binding, row, now=0):
    with connection(path) as db:
        namespace, epoch, expires = db.execute("SELECT * FROM promise").fetchone()
        if (namespace, epoch) != (
            binding["namespace"],
            binding["epoch"],
        ) or now >= expires:
            raise ValueError("sink promise mismatch or expiry")
        payload = encoded(row[1:]).decode()
        db.execute("BEGIN IMMEDIATE")
        old = db.execute(
            "SELECT payload FROM effects WHERE job=? AND position=?",
            (binding["job"], row[0]),
        ).fetchone()
        if old is not None and old[0] != payload:
            raise ValueError("effect payload conflict")
        if old is None:
            db.execute(
                "INSERT INTO effects VALUES (?,?,?)", (binding["job"], row[0], payload)
            )
        db.execute("COMMIT")
        return {
            "position": row[0],
            "reconciled": old is not None,
            "commit": True,
            "profile": profile(db),
        }


def sink_read(path):
    with connection(path) as db:
        return {
            "effects": [
                [p, *json.loads(v)]
                for p, v in db.execute(
                    "SELECT position,payload FROM effects ORDER BY job,position"
                )
            ],
            "profile": profile(db),
        }


def acknowledge(directory, binding, position):
    with connection(directory / "job.sqlite") as db:
        authorize(db, binding)
        db.execute("INSERT OR IGNORE INTO acks VALUES (?)", (position,))
        return profile(db)
