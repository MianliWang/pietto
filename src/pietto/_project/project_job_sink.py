"""Independent local reference cooperative sink over its own private SQLite store.

One sink instance is one namespace incarnation (namespace, epoch) with one
immutable finite retention contract, all fixed at creation and compared on every
open. An effect is the insertion of one exact typed row into the append-only
`effect` table, in the sink's own transaction, together with its commit record.
The primary key (workspace, generation, position) is the occurrence identity
inside this incarnation, so a repeated or concurrent submission of one key can
never insert twice; a different payload for an existing key is an explicit
conflict. Effects and their deduplication decisions share one lifetime: the
retention contract. Beyond it the sink reports RETENTION_EXPIRED, never absence.

This qualifies the supplied reference destination only, not arbitrary external
systems: no network service, plugin registry, callback inside a transaction or
exactly-once claim beyond this database and its retention contract. Its
directory, connection and transactions are never shared with a job store. The
private OS-user boundary and device synchronization honesty stay external
premises, as for the job workspace.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
import hashlib
import json
import os
import re
import sqlite3
import stat
import time
from urllib.parse import quote

from pietto._project.project_job_workspace import (
    CONTROL_RESERVE,
    DEFAULT_BUDGET,
    MAX_BUDGET,
    MIN_BUDGET,
    PAGE_SIZE,
    JobStoreError,
    StorageProfile,
    _abandon_creation,
    _busy,
    _canonical_root,
    _configure,
    _private,
    category,
    new_identity,
    storage_profile,
    valid_identity,
)

__all__: tuple[str, ...] = ()

FORMAT = "pietto.reference-sink.v1"
RETENTION = "pietto.sink-retention.v1"
LAYOUT = "pietto.sink-layout.v1"
ENVELOPE = "sink.json"
DATABASE = "sink.sqlite"
CREATING = "CREATING"
APPLICATION_ID = 0x5054534B
SCHEMA_VERSION = 1
MAX_ENVELOPE_BYTES = 4096
MAX_EFFECT_BYTES = 8 * 1024 * 1024
MAX_RETENTION_SECONDS = 400 * 86400
NAMESPACE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
# Canonical scalar name -> the S06 atom kind of its checked logical value.
KINDS = {
    "Int": "int",
    "Bool": "bool",
    "Text": "str",
    "Float": "float",
    "Decimal": "decimal",
    "Timestamp": "datetime",
    "UUID": "uuid",
}
SCHEMA = (
    "CREATE TABLE sink(singleton INTEGER PRIMARY KEY CHECK (singleton = 1),"
    " identity TEXT NOT NULL, format TEXT NOT NULL, namespace TEXT NOT NULL,"
    " epoch INTEGER NOT NULL CHECK (epoch >= 1), retention TEXT NOT NULL) STRICT",
    "CREATE TABLE effect(workspace TEXT NOT NULL, generation TEXT NOT NULL,"
    " position INTEGER NOT NULL CHECK (position >= 0), layout TEXT NOT NULL,"
    " payload TEXT NOT NULL, digest TEXT NOT NULL,"
    " commit_identity TEXT NOT NULL UNIQUE,"
    " sequence INTEGER NOT NULL UNIQUE CHECK (sequence >= 1),"
    " committed_at INTEGER NOT NULL,"
    " PRIMARY KEY (workspace, generation, position)) STRICT, WITHOUT ROWID",
)
# The trusted host wall clock. Tests inject explicit boundaries; callers cannot.
_wall = time.time


def _json(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def effect_digest(layout: str, payload: str) -> str:
    """Correspondence digest only; exact texts are what the sink compares."""
    return hashlib.sha256(_json([layout, payload]).encode("utf-8")).hexdigest()


def retention_descriptor(seconds: int, until: int) -> str:
    return _json({"format": RETENTION, "retained_until": until, "seconds": seconds})


def _unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise JobStoreError("SINK_FORMAT")
        result[key] = value
    return result


def _retention(value) -> tuple[str, int]:
    if (
        type(value) is not dict
        or set(value) != {"format", "retained_until", "seconds"}
        or value["format"] != RETENTION
        or type(value["seconds"]) is not int
        or not 1 <= value["seconds"] <= MAX_RETENTION_SECONDS
        or type(value["retained_until"]) is not int
        or value["retained_until"] <= value["seconds"]
    ):
        raise JobStoreError("SINK_FORMAT")
    return (
        retention_descriptor(value["seconds"], value["retained_until"]),
        value["retained_until"],
    )


def envelope_bytes(identity, budget, namespace, epoch, retention) -> bytes:
    document = {
        "budget": budget,
        "database": DATABASE,
        "epoch": epoch,
        "format": FORMAT,
        "identity": identity,
        "namespace": namespace,
        "retention": json.loads(retention),
    }
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "ascii"
    )


def read_envelope(raw: bytes) -> tuple[str, int, str, int, str, int]:
    """Bounded immutable identity, checked before any SQLite open."""
    try:
        if len(raw) > MAX_ENVELOPE_BYTES:
            raise JobStoreError("SINK_FORMAT")
        value = json.loads(raw.decode("ascii"), object_pairs_hook=_unique)
        if (
            type(value) is not dict
            or set(value)
            != {
                "budget",
                "database",
                "epoch",
                "format",
                "identity",
                "namespace",
                "retention",
            }
            or value["format"] != FORMAT
            or value["database"] != DATABASE
        ):
            raise JobStoreError("SINK_FORMAT")
        identity, budget = value["identity"], value["budget"]
        namespace, epoch = value["namespace"], value["epoch"]
        retention, until = _retention(value["retention"])
        if (
            not valid_identity(identity, "snk")
            or type(budget) is not int
            or not MIN_BUDGET <= budget <= MAX_BUDGET
            or type(namespace) is not str
            or NAMESPACE.fullmatch(namespace) is None
            or type(epoch) is not int
            or epoch < 1
            or envelope_bytes(identity, budget, namespace, epoch, retention) != raw
        ):
            raise JobStoreError("SINK_FORMAT")
        return identity, budget, namespace, epoch, retention, until
    except (ValueError, UnicodeError, RecursionError) as error:
        if type(error) is JobStoreError:
            raise
        raise JobStoreError("SINK_FORMAT") from None


@cache
def expected_schema() -> tuple:
    memory = sqlite3.connect(":memory:", isolation_level=None)
    try:
        for statement in SCHEMA:
            memory.execute(statement)
        return tuple(
            memory.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
            )
        )
    finally:
        memory.close()


def commit(connection: sqlite3.Connection) -> None:
    connection.execute("COMMIT")


def _connect(root: str, busy: float) -> sqlite3.Connection:
    uri = "file:" + quote(os.path.join(root, DATABASE)) + "?mode=rw"
    return sqlite3.connect(
        uri, uri=True, timeout=busy, isolation_level=None, check_same_thread=True
    )


def _verify_database(connection, identity, namespace, epoch, retention) -> None:
    if (
        connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal"
        or connection.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
        or connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION
        or tuple(
            connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
            )
        )
        != expected_schema()
        or tuple(
            connection.execute(
                "SELECT singleton, identity, format, namespace, epoch, retention FROM sink"
            )
        )
        != ((1, identity, FORMAT, namespace, epoch, retention),)
    ):
        raise JobStoreError("SINK_SCHEMA")


def _parsed(text, keys):
    """A bounded canonical JSON object with exactly `keys`, or SINK_EFFECT."""
    try:
        value = json.loads(text, object_pairs_hook=_unique)
    except (ValueError, RecursionError):
        raise JobStoreError("SINK_EFFECT") from None
    if type(value) is not dict or set(value) != keys or _json(value) != text:
        raise JobStoreError("SINK_EFFECT")
    return value


def _atom_kind(wire) -> str:
    from pietto._project.project_job_chunks import read_coordinate

    try:
        read_coordinate(wire)
    except JobStoreError:
        raise JobStoreError("SINK_EFFECT") from None
    return wire[0]


def check_effect(layout: str, payload: str) -> None:
    """Bound, canonical form and the exact typed shape of one materialized row."""
    if (
        type(layout) is not str
        or type(payload) is not str
        or len(layout.encode("utf-8")) + len(payload.encode("utf-8")) > MAX_EFFECT_BYTES
    ):
        raise JobStoreError("SINK_EFFECT")
    shape = _parsed(layout, {"contract", "fields", "format", "multiplicity", "scheme"})
    row = _parsed(payload, {"coordinates", "values"})
    fields, values = shape["fields"], row["values"]
    if (
        shape["format"] != LAYOUT
        or type(fields) is not list
        or type(values) is not list
        or len(values) != len(fields)
    ):
        raise JobStoreError("SINK_EFFECT")
    for item, wire in zip(fields, values, strict=True):
        if type(item) is not list or len(item) != 6 or item[3] not in KINDS:
            raise JobStoreError("SINK_EFFECT")
        kind = _atom_kind(wire)
        if kind != KINDS[item[3]] and (kind != "NoneType" or item[4] == "non_null"):
            raise JobStoreError("SINK_EFFECT")
    scheme, coordinates = shape["scheme"], row["coordinates"]
    if (scheme is None) != (coordinates is None):
        raise JobStoreError("SINK_EFFECT")
    if coordinates is not None:
        width = len(json.loads(scheme)["coordinates"])
        if type(coordinates) is not list or len(coordinates) != width:
            raise JobStoreError("SINK_EFFECT")
        for wire in coordinates:
            _atom_kind(wire)


@dataclass(frozen=True, slots=True)
class SinkDescription:
    """The sink owner's own current identity, read from its database."""

    identity: str
    namespace: str
    epoch: int
    retention: str
    retained_until: int


@dataclass(frozen=True, slots=True)
class SinkEffect:
    """One effect request: the destination it expects and one exact typed row."""

    sink: str
    namespace: str
    epoch: int
    retention: str
    workspace: str
    generation: str
    position: int
    layout: str = field(repr=False)
    payload: str = field(repr=False)

    @property
    def key(self) -> tuple:
        return (
            self.sink,
            self.namespace,
            self.epoch,
            self.workspace,
            self.generation,
            self.position,
        )


@dataclass(frozen=True, slots=True)
class SinkReply:
    """Data from the cooperating sink owner; never authority or a local receipt.

    submit: COMMITTED (inserted by this call), DUPLICATE (existing equal effect,
    nothing inserted), CONFLICT, RETENTION_EXPIRED or UNAVAILABLE (another
    instance, namespace, epoch or retention contract). query: PRESENT_MATCHING,
    PRESENT_CONFLICT, ACTIVE_NOT_FOUND, RETENTION_EXPIRED or
    UNAVAILABLE_OR_UNKNOWN. The commit record names the stored effect.
    """

    kind: str
    status: str
    sink: str
    namespace: str
    epoch: int
    retention: str
    workspace: str
    generation: str
    position: int
    digest: str | None = None
    commit: str | None = None
    sequence: int | None = None
    committed_at: int | None = None


def _request(effect) -> None:
    if (
        type(effect) is not SinkEffect
        or type(effect.sink) is not str
        or type(effect.namespace) is not str
        or type(effect.epoch) is not int
        or type(effect.retention) is not str
        or not valid_identity(effect.workspace, "ws")
        or not valid_identity(effect.generation, "gen")
        or type(effect.position) is not int
        or effect.position < 0
    ):
        raise JobStoreError("SINK_REQUEST")


class Sink:
    """One open process-local sink handle; never passed to another process."""

    __slots__ = (
        "root",
        "identity",
        "namespace",
        "epoch",
        "retention",
        "retained_until",
        "budget",
        "profile",
        "_connection",
        "_root_fd",
        "_root_state",
        "_pid",
        "_closed",
        "_retired",
    )

    def __init__(
        self,
        root,
        identity,
        budget,
        namespace,
        epoch,
        retention,
        until,
        profile,
        connection,
        root_fd,
    ):
        self.root = root
        self.identity = identity
        self.namespace = namespace
        self.epoch = epoch
        self.retention = retention
        self.retained_until = until
        self.budget = budget
        self.profile: StorageProfile = profile
        self._connection = connection
        self._root_fd = root_fd
        self._root_state = os.fstat(root_fd)
        self._pid = os.getpid()
        self._closed = False
        self._retired = False

    def __repr__(self) -> str:
        return f"Sink(identity={self.identity!r})"

    def use(self) -> sqlite3.Connection:
        if self._pid != os.getpid():
            raise JobStoreError("SINK_FOREIGN_PROCESS")
        if self._closed:
            raise JobStoreError("SINK_CLOSED")
        if self._retired:
            raise JobStoreError("SINK_RETIRED")
        current = os.lstat(self.root)
        if (current.st_dev, current.st_ino) != (
            self._root_state.st_dev,
            self._root_state.st_ino,
        ) or not stat.S_ISDIR(current.st_mode):
            raise JobStoreError("SINK_OBJECT")
        return self._connection

    def retire(self) -> None:
        """Abandon uncertain connection state; later calls need a fresh open."""
        self._retired = True
        try:
            self._connection.close()
        except sqlite3.Error:
            pass

    def close(self) -> None:
        if self._closed:
            return
        if self._pid != os.getpid():
            raise JobStoreError("SINK_FOREIGN_PROCESS")
        self._closed = True
        failure = None
        try:
            self._connection.close()
        except sqlite3.Error:
            failure = "SINK_CLOSE"
        finally:
            os.close(self._root_fd)
        if failure is not None:
            raise JobStoreError(failure)

    def _read(self, body):
        connection = self.use()
        try:
            connection.execute("BEGIN")
            try:
                result = body(connection)
            except BaseException:
                try:
                    connection.execute("ROLLBACK")
                except sqlite3.Error:
                    self.retire()
                raise
            connection.execute("COMMIT")
            return result
        except sqlite3.Error as error:
            raise JobStoreError(category(error)) from None

    def describe(self) -> SinkDescription:
        """The owner's identity as its database records it now."""
        row = self._read(
            lambda c: c.execute(
                "SELECT identity, format, namespace, epoch, retention FROM sink"
            ).fetchone()
        )
        if row != (self.identity, FORMAT, self.namespace, self.epoch, self.retention):
            raise JobStoreError("SINK_SCHEMA")
        return SinkDescription(row[0], row[2], row[3], row[4], self.retained_until)

    def _reply(self, kind, status, effect, row=None) -> SinkReply:
        return SinkReply(
            kind,
            status,
            self.identity,
            self.namespace,
            self.epoch,
            self.retention,
            effect.workspace,
            effect.generation,
            effect.position,
            *(row or ()),
        )

    def _context(self, effect) -> bool:
        return (effect.sink, effect.namespace, effect.epoch, effect.retention) == (
            self.identity,
            self.namespace,
            self.epoch,
            self.retention,
        )

    def _admit(self, payload: int) -> None:
        total = 0
        for name in (DATABASE, DATABASE + "-wal", DATABASE + "-shm", ENVELOPE):
            try:
                total += os.stat(
                    name, dir_fd=self._root_fd, follow_symlinks=False
                ).st_size
            except FileNotFoundError:
                pass
        need = 3 * payload + CONTROL_RESERVE
        if total + need > self.budget:
            raise JobStoreError("SINK_BUDGET")
        space = os.statvfs(self._root_fd)
        if space.f_bavail * space.f_frsize < need + CONTROL_RESERVE:
            raise JobStoreError("SINK_SPACE")

    def submit(self, effect: SinkEffect) -> SinkReply:
        """Insert this exact typed row once, or report the existing decision."""
        connection = self.use()
        _request(effect)
        if not self._context(effect):
            return self._reply("submit", "UNAVAILABLE", effect)
        check_effect(effect.layout, effect.payload)
        if _wall() >= self.retained_until:
            return self._reply("submit", "RETENTION_EXPIRED", effect)
        digest = effect_digest(effect.layout, effect.payload)
        self._admit(
            len(effect.layout.encode("utf-8")) + len(effect.payload.encode("utf-8"))
        )
        key = (effect.workspace, effect.generation, effect.position)
        try:
            connection.execute("BEGIN IMMEDIATE")
        except sqlite3.Error as error:
            raise JobStoreError(category(error)) from None
        try:
            # The sink's own validity is checked again at its effect commit.
            now = _wall()
            if now >= self.retained_until:
                connection.execute("ROLLBACK")
                return self._reply("submit", "RETENTION_EXPIRED", effect)
            identity = new_identity("skc")
            sequence = connection.execute(
                "SELECT coalesce(max(sequence), 0) + 1 FROM effect"
            ).fetchone()[0]
            try:
                # The primary key decides; nothing is ignored or overwritten.
                connection.execute(
                    "INSERT INTO effect(workspace, generation, position, layout, payload,"
                    " digest, commit_identity, sequence, committed_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        *key,
                        effect.layout,
                        effect.payload,
                        digest,
                        identity,
                        sequence,
                        int(now),
                    ),
                )
            except sqlite3.IntegrityError as error:
                if (
                    getattr(error, "sqlite_errorname", "")
                    != "SQLITE_CONSTRAINT_PRIMARYKEY"
                ):
                    raise
                row = connection.execute(
                    "SELECT layout, payload, digest, commit_identity, sequence, committed_at"
                    " FROM effect WHERE workspace = ? AND generation = ? AND position = ?",
                    key,
                ).fetchone()
                connection.execute("ROLLBACK")
                status = (
                    "DUPLICATE"
                    if (row[0], row[1]) == (effect.layout, effect.payload)
                    else "CONFLICT"
                )
                return self._reply("submit", status, effect, row[2:])
        except BaseException as primary:
            try:
                connection.execute("ROLLBACK")
            except BaseException:
                self.retire()
                primary.add_note("rollback failed; sink retired")
            if isinstance(primary, sqlite3.Error):
                raise JobStoreError(category(primary)) from None
            raise
        try:
            commit(connection)
        except BaseException:
            self.retire()
            raise JobStoreError("SINK_COMMIT_UNKNOWN") from None
        return self._reply(
            "submit", "COMMITTED", effect, (digest, identity, sequence, int(now))
        )

    def query(self, effect: SinkEffect) -> SinkReply:
        """Compare the stored effect of this exact key with the expected row."""
        self.use()
        _request(effect)
        if not self._context(effect):
            return self._reply("query", "UNAVAILABLE_OR_UNKNOWN", effect)
        if (
            type(effect.layout) is not str
            or type(effect.payload) is not str
            or len(effect.layout.encode("utf-8")) + len(effect.payload.encode("utf-8"))
            > MAX_EFFECT_BYTES
        ):
            raise JobStoreError("SINK_EFFECT")

        def body(c):
            if _wall() >= self.retained_until:
                return None
            return (
                c.execute(
                    "SELECT layout, payload, digest, commit_identity, sequence,"
                    " committed_at FROM effect WHERE workspace = ? AND generation = ?"
                    " AND position = ?",
                    (effect.workspace, effect.generation, effect.position),
                ).fetchone(),
            )

        found = self._read(body)
        if found is None:
            return self._reply("query", "RETENTION_EXPIRED", effect)
        row = found[0]
        if row is None:
            return self._reply("query", "ACTIVE_NOT_FOUND", effect)
        status = (
            "PRESENT_MATCHING"
            if (row[0], row[1]) == (effect.layout, effect.payload)
            else "PRESENT_CONFLICT"
        )
        return self._reply("query", status, effect, row[2:])


def create_sink(
    root: str,
    *,
    namespace: str,
    epoch: int,
    retention_seconds: int,
    budget_bytes: int = DEFAULT_BUDGET,
    busy_seconds: float = 5.0,
) -> Sink:
    """Exclusively create one private sink with its fixed retention contract."""
    root, parent, name = _canonical_root(root)
    busy = _busy(busy_seconds)
    if type(budget_bytes) is not int or not MIN_BUDGET <= budget_bytes <= MAX_BUDGET:
        raise JobStoreError("SINK_BUDGET")
    if (
        type(namespace) is not str
        or NAMESPACE.fullmatch(namespace) is None
        or type(epoch) is not int
        or epoch < 1
        or type(retention_seconds) is not int
        or not 1 <= retention_seconds <= MAX_RETENTION_SECONDS
    ):
        raise JobStoreError("SINK_CONTRACT")
    profile = storage_profile(parent)
    identity = new_identity("snk")
    until = int(_wall()) + retention_seconds
    retention = retention_descriptor(retention_seconds, until)
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    owned: dict[str, tuple[int, int]] = {}
    root_fd = -1
    connection = None
    try:
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            raise JobStoreError("SINK_EXISTS") from None
        root_fd = os.open(
            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd
        )
        _private(os.fstat(root_fd), stat.S_IFDIR)
        os.fsync(parent_fd)

        def exclusive(child, data=b""):
            fd = os.open(
                child,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=root_fd,
            )
            try:
                state = os.fstat(fd)
                owned[child] = (state.st_dev, state.st_ino)
                os.write(fd, data)
                os.fsync(fd)
            finally:
                os.close(fd)

        exclusive(CREATING, identity.encode("ascii") + b"\n")
        exclusive(DATABASE)
        os.fsync(root_fd)
        connection = _connect(root, busy)
        connection.execute(f"PRAGMA page_size = {PAGE_SIZE}")
        if connection.execute("PRAGMA journal_mode = WAL").fetchone()[0] != "wal":
            raise JobStoreError("SINK_SETTINGS")
        _configure(connection, budget_bytes, busy)
        connection.execute("BEGIN IMMEDIATE")
        for statement in SCHEMA:
            connection.execute(statement)
        connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        connection.execute(
            "INSERT INTO sink(singleton, identity, format, namespace, epoch, retention)"
            " VALUES (1, ?, ?, ?, ?, ?)",
            (identity, FORMAT, namespace, epoch, retention),
        )
        commit(connection)
        _verify_database(connection, identity, namespace, epoch, retention)
        exclusive(
            ENVELOPE,
            envelope_bytes(identity, budget_bytes, namespace, epoch, retention),
        )
        os.fsync(root_fd)
        os.unlink(CREATING, dir_fd=root_fd)
        del owned[CREATING]
        os.fsync(root_fd)
        sink = Sink(
            root,
            identity,
            budget_bytes,
            namespace,
            epoch,
            retention,
            until,
            profile,
            connection,
            root_fd,
        )
        connection = None
        return sink
    except BaseException as error:
        _abandon_creation(parent_fd, name, root_fd, -1, connection, owned)
        if isinstance(error, sqlite3.Error):
            raise JobStoreError("SINK_SETTINGS") from None
        raise
    finally:
        os.close(parent_fd)


def open_sink(root: str, *, expected_identity: str, busy_seconds: float = 5.0) -> Sink:
    """Fresh access to an existing complete sink; unknown formats never reach SQLite."""
    root, _parent, _name = _canonical_root(root)
    busy = _busy(busy_seconds)
    if not valid_identity(expected_identity, "snk"):
        raise JobStoreError("SINK_IDENTITY")
    try:
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        raise JobStoreError("SINK_OBJECT") from None
    connection = None
    try:
        _private(os.fstat(root_fd), stat.S_IFDIR)
        profile = storage_profile(root)
        names = set(os.listdir(root_fd))
        if CREATING in names or ENVELOPE not in names or DATABASE not in names:
            raise JobStoreError("SINK_INCOMPLETE")
        if names - {ENVELOPE, DATABASE, DATABASE + "-wal", DATABASE + "-shm"}:
            raise JobStoreError("SINK_OBJECT")
        for child in names:
            _private(
                os.stat(child, dir_fd=root_fd, follow_symlinks=False),
                stat.S_IFREG,
                single=True,
            )
        envelope_fd = os.open(ENVELOPE, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=root_fd)
        try:
            raw = os.read(envelope_fd, MAX_ENVELOPE_BYTES + 1)
        finally:
            os.close(envelope_fd)
        identity, budget, namespace, epoch, retention, until = read_envelope(raw)
        if identity != expected_identity:
            raise JobStoreError("SINK_IDENTITY")
        database = os.stat(DATABASE, dir_fd=root_fd, follow_symlinks=False)
        connection = _connect(root, busy)
        _configure(connection, budget, busy)
        if tuple(r[2] for r in connection.execute("PRAGMA database_list")) != (
            os.path.join(root, DATABASE),
        ):
            raise JobStoreError("SINK_OBJECT")
        _verify_database(connection, identity, namespace, epoch, retention)
        after = os.stat(DATABASE, dir_fd=root_fd, follow_symlinks=False)
        if (after.st_dev, after.st_ino) != (database.st_dev, database.st_ino):
            raise JobStoreError("SINK_OBJECT")
        sink = Sink(
            root,
            identity,
            budget,
            namespace,
            epoch,
            retention,
            until,
            profile,
            connection,
            root_fd,
        )
        connection = None
        return sink
    except sqlite3.Error as error:
        _close(connection, root_fd)
        raise JobStoreError(
            "STORE_BUSY" if category(error) == "STORE_BUSY" else "SINK_SCHEMA"
        ) from None
    except OSError:
        _close(connection, root_fd)
        raise JobStoreError("SINK_OBJECT") from None
    except BaseException:
        _close(connection, root_fd)
        raise


def _close(connection, root_fd) -> None:
    if connection is not None:
        try:
            connection.close()
        except sqlite3.Error:
            pass
    os.close(root_fd)
