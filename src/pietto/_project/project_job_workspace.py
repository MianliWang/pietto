"""Explicit private local job workspace over the qualified SQLite/filesystem profile.

Protection is the private OS-user directory and cooperating product owners; it
is not a defense against root, same-user direct file edits, compromised SQLite,
permanent disk loss, rollback to an older image or shared multi-host storage.
OS/device synchronization honesty is an external premise, never verified here.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
import json
import os
import re
import sqlite3
import stat
import sys
from urllib.parse import quote
from uuid import uuid4

__all__: tuple[str, ...] = ()

FORMAT = "pietto.job-workspace.v1"
FEATURES: tuple[str, ...] = ()
# S12's capture-capable, S13's replay-capable and S14's extraction-resume
# revisions are selected only by an explicit create option; nothing is ever
# upgraded in place.
FORMAT_V2 = "pietto.job-workspace.v2"
FORMAT_V3 = "pietto.job-workspace.v3"
FORMAT_V4 = "pietto.job-workspace.v4"
ENVELOPE = "workspace.json"
DATABASE = "store.sqlite"
CREATING = "CREATING"
LOCKS = "locks"
CHUNKS = "chunks"
STAGING = "staging"
APPLICATION_ID = 0x50544A53
SCHEMA_VERSION = 1
PAGE_SIZE = 4096
MAX_ENVELOPE_BYTES = 4096
MIN_BUDGET = 8 * 1024 * 1024
DEFAULT_BUDGET = 256 * 1024 * 1024
MAX_BUDGET = 4 * 1024 * 1024 * 1024
CONTROL_RESERVE = 4 * 1024 * 1024
JOURNAL_SIZE_LIMIT = 4 * 1024 * 1024
MAX_BUSY_SECONDS = 30.0
IDENTITY = re.compile(
    r"(ws|job|bind|gen|att|pub|op|chk|ckp|ret|csm|rps|dlv)-[0-9a-f]{32}"
)

# The one measured build (S11 profile probe). Version, source and compile
# options together identify it; later versions or system libraries are not
# implied. 3.51.3 and later contain the WAL-reset fix; this exact build does.
QUALIFIED_SQLITE = frozenset(
    {
        (
            "3.53.1",
            "2026-05-05 10:34:17 "
            "c88b22011a54b4f6fbd149e9f8e4de77658ce58143a1af0e3785e4e6475127e9",
            (
                "ATOMIC_INTRINSICS=1",
                "COMPILER=clang-22.1.3",
                "DEFAULT_AUTOVACUUM",
                "DEFAULT_CACHE_SIZE=-2000",
                "DEFAULT_FILE_FORMAT=4",
                "DEFAULT_JOURNAL_SIZE_LIMIT=-1",
                "DEFAULT_MMAP_SIZE=0",
                "DEFAULT_PAGE_SIZE=4096",
                "DEFAULT_PCACHE_INITSZ=20",
                "DEFAULT_RECURSIVE_TRIGGERS",
                "DEFAULT_SECTOR_SIZE=4096",
                "DEFAULT_SYNCHRONOUS=2",
                "DEFAULT_WAL_AUTOCHECKPOINT=1000",
                "DEFAULT_WAL_SYNCHRONOUS=2",
                "DEFAULT_WORKER_THREADS=0",
                "DIRECT_OVERFLOW_READ",
                "ENABLE_DBSTAT_VTAB",
                "ENABLE_FTS3",
                "ENABLE_FTS3_PARENTHESIS",
                "ENABLE_FTS4",
                "ENABLE_FTS5",
                "ENABLE_GEOPOLY",
                "ENABLE_MATH_FUNCTIONS",
                "ENABLE_PERCENTILE",
                "ENABLE_RTREE",
                "MALLOC_SOFT_LIMIT=1024",
                "MAX_ATTACHED=10",
                "MAX_COLUMN=2000",
                "MAX_COMPOUND_SELECT=500",
                "MAX_DEFAULT_PAGE_SIZE=8192",
                "MAX_EXPR_DEPTH=1000",
                "MAX_FUNCTION_ARG=1000",
                "MAX_LENGTH=1000000000",
                "MAX_LIKE_PATTERN_LENGTH=50000",
                "MAX_MMAP_SIZE=0x7fff0000",
                "MAX_PAGE_COUNT=0xfffffffe",
                "MAX_PAGE_SIZE=65536",
                "MAX_SQL_LENGTH=1000000000",
                "MAX_TRIGGER_DEPTH=1000",
                "MAX_VARIABLE_NUMBER=32766",
                "MAX_VDBE_OP=250000000",
                "MAX_WORKER_THREADS=8",
                "MUTEX_PTHREADS",
                "SYSTEM_MALLOC",
                "TEMP_STORE=1",
                "THREADSAFE=1",
            ),
        )
    }
)
QUALIFIED_FILESYSTEMS = frozenset({"ext4"})

# Closed schema. Only job rows are ever updated; all other rows are insert-only.
SCHEMA = (
    "CREATE TABLE workspace(singleton INTEGER PRIMARY KEY CHECK (singleton = 1),"
    " identity TEXT NOT NULL, format TEXT NOT NULL) STRICT",
    "CREATE TABLE job(identity TEXT PRIMARY KEY, bundle BLOB NOT NULL,"
    " pin TEXT NOT NULL, producer TEXT NOT NULL, compatibility TEXT NOT NULL,"
    " state TEXT NOT NULL CHECK (state IN ('ACTIVE', 'CANCELLED')),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 0),"
    " publisher_instance TEXT, revision INTEGER NOT NULL CHECK (revision >= 1))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE binding(identity TEXT PRIMARY KEY,"
    " job TEXT NOT NULL REFERENCES job(identity), slots TEXT NOT NULL,"
    " vector TEXT NOT NULL, UNIQUE (identity, job)) STRICT, WITHOUT ROWID",
    "CREATE TABLE generation(identity TEXT PRIMARY KEY,"
    " job TEXT NOT NULL REFERENCES job(identity), binding TEXT NOT NULL,"
    " route TEXT NOT NULL, isolation TEXT NOT NULL, description TEXT NOT NULL,"
    " UNIQUE (identity, job), FOREIGN KEY (binding, job)"
    " REFERENCES binding(identity, job)) STRICT, WITHOUT ROWID",
    "CREATE TABLE attempt(identity TEXT PRIMARY KEY, generation TEXT NOT NULL,"
    " job TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK (ordinal >= 1),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " publisher_instance TEXT NOT NULL, binding_reference TEXT NOT NULL,"
    " UNIQUE (generation, ordinal), FOREIGN KEY (generation, job)"
    " REFERENCES generation(identity, job)) STRICT, WITHOUT ROWID",
    "CREATE INDEX attempt_job ON attempt(job)",
    "CREATE TABLE attempt_terminal(attempt TEXT PRIMARY KEY"
    " REFERENCES attempt(identity), kind TEXT NOT NULL"
    " CHECK (kind IN ('OUTCOME', 'NOT_EXECUTED', 'INTERRUPTED')),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " outcome TEXT NOT NULL) STRICT, WITHOUT ROWID",
    "CREATE TABLE operation(sequence INTEGER PRIMARY KEY,"
    " identity TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,"
    " job TEXT NOT NULL REFERENCES job(identity), request TEXT NOT NULL,"
    " result TEXT NOT NULL) STRICT",
    "CREATE INDEX operation_job ON operation(job)",
)
# Closed S12 tables (v2 only). Rows are insert-only; extents are half-open
# [start, stop). A checkpoint is an immutable full member set of committed chunks.
CAPTURE_SCHEMA = (
    "CREATE TABLE capture(generation TEXT PRIMARY KEY, job TEXT NOT NULL,"
    " attempt TEXT NOT NULL UNIQUE REFERENCES attempt(identity),"
    " kind TEXT NOT NULL CHECK (kind IN ('ORDINARY', 'REFINED')),"
    " contract TEXT NOT NULL, scheme TEXT NOT NULL,"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " publisher_instance TEXT NOT NULL, UNIQUE (generation, job),"
    " FOREIGN KEY (generation, job) REFERENCES generation(identity, job))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE chunk(identity TEXT PRIMARY KEY, job TEXT NOT NULL,"
    " generation TEXT NOT NULL, attempt TEXT NOT NULL,"
    " start INTEGER NOT NULL CHECK (start >= 0),"
    " stop INTEGER NOT NULL CHECK (stop >= start),"
    " batches INTEGER NOT NULL CHECK (batches IN (0, 1)),"
    " file TEXT NOT NULL UNIQUE, bytes INTEGER NOT NULL CHECK (bytes > 0),"
    " digest TEXT NOT NULL, descriptor TEXT NOT NULL,"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " publisher_instance TEXT NOT NULL, UNIQUE (generation, start),"
    " UNIQUE (identity, generation),"
    " FOREIGN KEY (generation, job) REFERENCES capture(generation, job))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE checkpoint(identity TEXT PRIMARY KEY, job TEXT NOT NULL,"
    " generation TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK (ordinal >= 1),"
    " frontier INTEGER NOT NULL CHECK (frontier >= 0),"
    " members INTEGER NOT NULL CHECK (members >= 1),"
    " rows INTEGER NOT NULL CHECK (rows >= 0),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " UNIQUE (generation, ordinal), UNIQUE (identity, generation),"
    " FOREIGN KEY (generation, job) REFERENCES capture(generation, job))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE checkpoint_member(checkpoint TEXT NOT NULL,"
    " chunk TEXT NOT NULL, generation TEXT NOT NULL,"
    " PRIMARY KEY (checkpoint, chunk),"
    " FOREIGN KEY (checkpoint, generation) REFERENCES checkpoint(identity, generation),"
    " FOREIGN KEY (chunk, generation) REFERENCES chunk(identity, generation))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE capture_end(generation TEXT PRIMARY KEY"
    " REFERENCES capture(generation), observed INTEGER NOT NULL CHECK (observed >= 0),"
    " source TEXT NOT NULL, staged INTEGER NOT NULL CHECK (staged >= 0),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1)) STRICT, WITHOUT ROWID",
    "CREATE TABLE retention(identity TEXT PRIMARY KEY, job TEXT NOT NULL,"
    " generation TEXT NOT NULL, checkpoint TEXT NOT NULL, scope TEXT NOT NULL,"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " publisher_instance TEXT NOT NULL,"
    " FOREIGN KEY (checkpoint, generation) REFERENCES checkpoint(identity, generation))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE retention_release(retention TEXT PRIMARY KEY"
    " REFERENCES retention(identity),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " publisher_instance TEXT NOT NULL) STRICT, WITHOUT ROWID",
)
# Closed S13 tables (v3 only), insert-only. A consumer is bound to one exact
# checkpoint and fixed extent; its progress is derived from acknowledgements,
# whose self-reference makes the acknowledged intervals one gap-free chain
# from position 0. An acknowledgement range must equal its issued range.
REPLAY_SCHEMA = (
    "CREATE TABLE consumer(identity TEXT PRIMARY KEY, job TEXT NOT NULL,"
    " generation TEXT NOT NULL, checkpoint TEXT NOT NULL, binding TEXT NOT NULL,"
    " retention TEXT NOT NULL UNIQUE REFERENCES retention(identity),"
    " scope TEXT NOT NULL CHECK (scope IN ('complete_capture', 'committed_prefix')),"
    " extent INTEGER NOT NULL CHECK (extent >= 0), purpose TEXT NOT NULL,"
    " not_after INTEGER CHECK (not_after IS NULL OR not_after > 0),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " publisher_instance TEXT NOT NULL,"
    " FOREIGN KEY (generation, job) REFERENCES generation(identity, job),"
    " FOREIGN KEY (binding, job) REFERENCES binding(identity, job),"
    " FOREIGN KEY (checkpoint, generation) REFERENCES checkpoint(identity, generation))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE replay_session(identity TEXT PRIMARY KEY,"
    " consumer TEXT NOT NULL REFERENCES consumer(identity),"
    " ordinal INTEGER NOT NULL CHECK (ordinal >= 1),"
    " position INTEGER NOT NULL CHECK (position >= 0),"
    " accepted_at INTEGER NOT NULL, seconds INTEGER NOT NULL CHECK (seconds >= 1),"
    " batch_rows INTEGER NOT NULL CHECK (batch_rows >= 1),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " publisher_instance TEXT NOT NULL, UNIQUE (consumer, ordinal),"
    " UNIQUE (identity, consumer)) STRICT, WITHOUT ROWID",
    "CREATE TABLE issuance(identity TEXT PRIMARY KEY, consumer TEXT NOT NULL,"
    " session TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK (ordinal >= 1),"
    " start INTEGER NOT NULL CHECK (start >= 0),"
    " stop INTEGER NOT NULL CHECK (stop > start),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " UNIQUE (session, ordinal), UNIQUE (identity, session, consumer, start, stop),"
    " FOREIGN KEY (session, consumer) REFERENCES replay_session(identity, consumer))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE acknowledgement(issuance TEXT PRIMARY KEY, consumer TEXT NOT NULL,"
    " session TEXT NOT NULL, start INTEGER NOT NULL CHECK (start >= 0),"
    " stop INTEGER NOT NULL CHECK (stop > start),"
    " previous INTEGER CHECK ((previous IS NULL) = (start = 0)"
    " AND (previous IS NULL OR previous = start)),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " UNIQUE (consumer, start), UNIQUE (consumer, stop),"
    " FOREIGN KEY (issuance, session, consumer, start, stop)"
    " REFERENCES issuance(identity, session, consumer, start, stop),"
    " FOREIGN KEY (consumer, previous) REFERENCES acknowledgement(consumer, stop))"
    " STRICT, WITHOUT ROWID",
)
# Closed S14 tables (v4 only), insert-only. An extraction row is written in the
# same transaction as its capture row, so only a generation registered before
# its first capture can continue. A continuation freezes its predecessor
# checkpoint; its chunks are admitted only after its reconciliation (barrier).
EXTRACTION_SCHEMA = (
    "CREATE TABLE extraction(generation TEXT PRIMARY KEY, job TEXT NOT NULL,"
    " attempt TEXT NOT NULL UNIQUE REFERENCES attempt(identity),"
    " specification TEXT NOT NULL, qualification TEXT NOT NULL,"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " publisher_instance TEXT NOT NULL,"
    " FOREIGN KEY (generation, job) REFERENCES capture(generation, job))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE continuation(attempt TEXT PRIMARY KEY REFERENCES attempt(identity),"
    " job TEXT NOT NULL, generation TEXT NOT NULL REFERENCES extraction(generation),"
    " predecessor TEXT, frontier INTEGER NOT NULL CHECK (frontier >= 0),"
    " reach INTEGER NOT NULL CHECK (reach >= frontier),"
    " members INTEGER NOT NULL CHECK (members >= 0),"
    " rows INTEGER NOT NULL CHECK (rows >= frontier AND rows <= reach),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " publisher_instance TEXT NOT NULL, UNIQUE (attempt, generation),"
    " FOREIGN KEY (predecessor, generation) REFERENCES checkpoint(identity, generation))"
    " STRICT, WITHOUT ROWID",
    "CREATE TABLE reconciliation(attempt TEXT PRIMARY KEY"
    " REFERENCES continuation(attempt), position INTEGER NOT NULL CHECK (position >= 0),"
    " matched INTEGER NOT NULL CHECK (matched >= 0),"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1)) STRICT, WITHOUT ROWID",
    "CREATE TABLE continuation_end(attempt TEXT PRIMARY KEY, generation TEXT NOT NULL,"
    " observed INTEGER NOT NULL CHECK (observed >= 0), source TEXT NOT NULL,"
    " staged INTEGER NOT NULL CHECK (staged >= 0), checkpoint TEXT,"
    " publisher_epoch INTEGER NOT NULL CHECK (publisher_epoch >= 1),"
    " FOREIGN KEY (attempt, generation) REFERENCES continuation(attempt, generation),"
    " FOREIGN KEY (checkpoint, generation) REFERENCES checkpoint(identity, generation))"
    " STRICT, WITHOUT ROWID",
)
# Closed known-version table: envelope (format, features) -> user_version,
# exact schema and private directories. Anything else refuses before SQLite.
VERSIONS = {
    FORMAT: (FEATURES, SCHEMA_VERSION, SCHEMA, ()),
    FORMAT_V2: (("result-chunks",), 2, SCHEMA + CAPTURE_SCHEMA, (CHUNKS, STAGING)),
    FORMAT_V3: (
        ("result-chunks", "saved-replay"),
        3,
        SCHEMA + CAPTURE_SCHEMA + REPLAY_SCHEMA,
        (CHUNKS, STAGING),
    ),
    FORMAT_V4: (
        ("result-chunks", "saved-replay", "extraction-resume"),
        4,
        SCHEMA + CAPTURE_SCHEMA + REPLAY_SCHEMA + EXTRACTION_SCHEMA,
        (CHUNKS, STAGING),
    ),
}
_SAFE_CONFIG = (
    ("DEFENSIVE", True),
    ("TRUSTED_SCHEMA", False),
    ("ENABLE_TRIGGER", False),
    ("ENABLE_VIEW", False),
    ("ENABLE_LOAD_EXTENSION", False),
    ("WRITABLE_SCHEMA", False),
    ("DQS_DDL", False),
    ("DQS_DML", False),
    ("ENABLE_FKEY", True),
)


class JobStoreError(ValueError):
    """A value-free category; no bundle, binding or credential text is included."""


@dataclass(frozen=True, slots=True)
class StorageProfile:
    sqlite_version: str
    sqlite_source_id: str
    filesystem: str
    mount_point: str
    super_options: str
    device_sync: str = "EXTERNAL_PREMISE_NOT_VERIFIED"


def new_identity(kind: str) -> str:
    return kind + "-" + uuid4().hex


def valid_identity(value: object, kind: str) -> bool:
    return (
        type(value) is str
        and IDENTITY.fullmatch(value) is not None
        and value.startswith(kind + "-")
    )


def supports(workspace: Workspace, feature: str) -> bool:
    """An exact capability case of the closed version table, never `version >= n`."""
    return feature in VERSIONS[workspace.format][0]


def _mount(path: str, device: int) -> tuple[str, str, str, str]:
    numbers = f"{os.major(device)}:{os.minor(device)}"
    best: tuple[int, int, str, str, str, str] | None = None
    with open("/proc/self/mountinfo", encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            fields = line.split()
            if len(fields) < 10 or fields[2] != numbers or "-" not in fields[6:]:
                continue
            point = re.sub(
                r"\\([0-7]{3})", lambda m: chr(int(m.group(1), 8)), fields[4]
            )
            if not (path == point or path.startswith(point.rstrip("/") + "/")):
                continue
            separator = fields.index("-", 6)
            key = (
                len(point),
                index,
                point,
                fields[separator + 1],
                fields[5],
                fields[separator + 3],
            )
            if best is None or key[:2] > best[:2]:
                best = key
    if best is None:
        raise JobStoreError("WORKSPACE_PROFILE_FILESYSTEM")
    return best[2], best[3], best[4], best[5]


def storage_profile(path: str) -> StorageProfile:
    """Observe the actual runtime and filesystem; labels are never accepted."""
    if sys.platform != "linux":
        raise JobStoreError("WORKSPACE_PROFILE_PLATFORM")
    probe = sqlite3.connect(":memory:")
    try:
        source = probe.execute("SELECT sqlite_source_id()").fetchone()[0]
        options = tuple(r[0] for r in probe.execute("PRAGMA compile_options"))
    finally:
        probe.close()
    if (sqlite3.sqlite_version, source, options) not in QUALIFIED_SQLITE:
        raise JobStoreError("WORKSPACE_PROFILE_SQLITE")
    point, filesystem, mounted, supers = _mount(path, os.stat(path).st_dev)
    flags = supers.split(",")
    if (
        filesystem not in QUALIFIED_FILESYSTEMS
        or "rw" not in mounted.split(",")
        or "rw" not in flags
        or "nobarrier" in flags
        or "barrier=0" in flags
    ):
        raise JobStoreError("WORKSPACE_PROFILE_FILESYSTEM")
    return StorageProfile(sqlite3.sqlite_version, source, filesystem, point, supers)


def _private(state: os.stat_result, kind: int, *, single: bool = False) -> None:
    if (
        stat.S_IFMT(state.st_mode) != kind
        or state.st_uid != os.geteuid()
        or state.st_mode & 0o077
        or (single and state.st_nlink != 1)
    ):
        raise JobStoreError("WORKSPACE_OBJECT")


def _canonical_root(root: object) -> tuple[str, str, str]:
    if (
        type(root) is not str
        or not root.startswith("/")
        or "\0" in root
        or os.path.normpath(root) != root
        or root == "/"
    ):
        raise JobStoreError("WORKSPACE_PATH")
    parent, name = os.path.split(root)
    if (
        not name
        or len(name.encode("utf-8")) > 255
        or os.path.realpath(parent) != parent
    ):
        raise JobStoreError("WORKSPACE_PATH")
    try:
        state = os.lstat(parent)
    except OSError:
        raise JobStoreError("WORKSPACE_PARENT") from None
    if (
        not stat.S_ISDIR(state.st_mode)
        or state.st_uid != os.geteuid()
        or state.st_mode & 0o022
    ):
        raise JobStoreError("WORKSPACE_PARENT")
    return root, parent, name


def envelope_bytes(identity: str, budget: int, format: str = FORMAT) -> bytes:
    document = {
        "budget": budget,
        "database": DATABASE,
        "features": list(VERSIONS[format][0]),
        "format": format,
        "identity": identity,
    }
    return (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "ascii"
    )


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise JobStoreError("WORKSPACE_FORMAT")
        result[key] = value
    return result


def read_envelope(raw: bytes) -> tuple[str, int, str]:
    """Bounded immutable outer identity, checked before any SQLite open."""
    try:
        if len(raw) > MAX_ENVELOPE_BYTES:
            raise JobStoreError("WORKSPACE_FORMAT")
        value = json.loads(raw.decode("ascii"), object_pairs_hook=_pairs)
        if type(value) is not dict:
            raise JobStoreError("WORKSPACE_FORMAT")
        format = value.get("format")
        if (
            type(format) is not str
            or format not in VERSIONS
            or value.get("features") != list(VERSIONS[format][0])
            or value.get("database") != DATABASE
            or set(value) != {"budget", "database", "features", "format", "identity"}
        ):
            raise JobStoreError("WORKSPACE_FORMAT")
        identity, budget = value["identity"], value["budget"]
        if (
            not valid_identity(identity, "ws")
            or type(budget) is not int
            or not MIN_BUDGET <= budget <= MAX_BUDGET
            or envelope_bytes(identity, budget, format) != raw
        ):
            raise JobStoreError("WORKSPACE_FORMAT")
        return identity, budget, format
    except (ValueError, UnicodeError, RecursionError) as error:
        if type(error) is JobStoreError:
            raise
        raise JobStoreError("WORKSPACE_FORMAT") from None


@cache
def expected_schema(format: str = FORMAT) -> tuple:
    memory = sqlite3.connect(":memory:", isolation_level=None)
    try:
        for statement in VERSIONS[format][2]:
            memory.execute(statement)
        return tuple(
            memory.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
            )
        )
    finally:
        memory.close()


def category(error: sqlite3.Error) -> str:
    name = getattr(error, "sqlite_errorname", "")
    if name.startswith(("SQLITE_BUSY", "SQLITE_LOCKED")):
        return "STORE_BUSY"
    if name.startswith("SQLITE_FULL"):
        return "STORE_FULL"
    if name.startswith("SQLITE_CONSTRAINT"):
        return "STORE_CONSTRAINT"
    return "STORE_IO"


def commit(connection: sqlite3.Connection) -> None:
    connection.execute("COMMIT")


def _configure(connection: sqlite3.Connection, budget: int, busy: float) -> None:
    """Set and read back every connection-specific setting; never trust defaults."""
    for name, value in _SAFE_CONFIG:
        option = getattr(sqlite3, "SQLITE_DBCONFIG_" + name)
        connection.setconfig(option, value)
        if connection.getconfig(option) is not value:
            raise JobStoreError("WORKSPACE_SETTINGS")
    connection.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
    if connection.getlimit(sqlite3.SQLITE_LIMIT_ATTACHED) != 0:
        raise JobStoreError("WORKSPACE_SETTINGS")
    for pragma, value in (
        ("synchronous", 2),
        ("foreign_keys", 1),
        ("temp_store", 2),
        ("busy_timeout", int(busy * 1000)),
        ("max_page_count", budget // PAGE_SIZE),
        ("journal_size_limit", JOURNAL_SIZE_LIMIT),
        ("cell_size_check", 1),
    ):
        connection.execute(f"PRAGMA {pragma} = {value}")
        if connection.execute(f"PRAGMA {pragma}").fetchone()[0] != value:
            raise JobStoreError("WORKSPACE_SETTINGS")


class Workspace:
    """One open process-local workspace handle; never passed to another process."""

    __slots__ = (
        "root",
        "identity",
        "budget",
        "profile",
        "format",
        "_connection",
        "_root_fd",
        "_locks_fd",
        "_root_state",
        "_directories",
        "_pid",
        "_closed",
        "_retired",
    )

    def __init__(
        self,
        root,
        identity,
        budget,
        profile,
        connection,
        root_fd,
        locks_fd,
        format=FORMAT,
        directories=(),
    ):
        self.root = root
        self.identity = identity
        self.budget = budget
        self.profile = profile
        self.format = format
        self._connection = connection
        self._root_fd = root_fd
        self._locks_fd = locks_fd
        self._root_state = os.fstat(root_fd)
        self._directories = dict(directories)
        self._pid = os.getpid()
        self._closed = False
        self._retired = False

    def __repr__(self) -> str:
        return f"Workspace(identity={self.identity!r})"

    def use(self) -> sqlite3.Connection:
        if self._pid != os.getpid():
            raise JobStoreError("WORKSPACE_FOREIGN_PROCESS")
        if self._closed:
            raise JobStoreError("WORKSPACE_CLOSED")
        if self._retired:
            raise JobStoreError("WORKSPACE_RETIRED")
        current = os.lstat(self.root)
        if (current.st_dev, current.st_ino) != (
            self._root_state.st_dev,
            self._root_state.st_ino,
        ) or not stat.S_ISDIR(current.st_mode):
            raise JobStoreError("WORKSPACE_OBJECT")
        return self._connection

    def locks_fd(self) -> int:
        self.use()
        return self._locks_fd

    def directory(self, name: str) -> int:
        """A NEW read-only descriptor of a v2 private directory; caller closes it."""
        self.use()
        if name not in self._directories:
            raise JobStoreError("WORKSPACE_CAPTURE_FORMAT")
        fd = os.open(
            name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=self._root_fd
        )
        try:
            state = os.fstat(fd)
            _private(state, stat.S_IFDIR)
            if (state.st_dev, state.st_ino) != self._directories[name]:
                raise JobStoreError("WORKSPACE_OBJECT")
        except BaseException:
            os.close(fd)
            raise
        return fd

    def retire(self) -> None:
        """Abandon uncertain connection state; later queries need a fresh open."""
        self._retired = True
        try:
            self._connection.close()
        except sqlite3.Error:
            pass

    def close(self) -> None:
        if self._closed:
            return
        if self._pid != os.getpid():
            raise JobStoreError("WORKSPACE_FOREIGN_PROCESS")
        self._closed = True
        failure = None
        try:
            self._connection.close()
        except sqlite3.Error:
            failure = "STORE_CLOSE"
        finally:
            os.close(self._locks_fd)
            os.close(self._root_fd)
        if failure is not None:
            raise JobStoreError(failure)


def write(workspace: Workspace, body):
    """One short write transaction; an uncertain COMMIT is never repeated here."""
    connection = workspace.use()
    try:
        connection.execute("BEGIN IMMEDIATE")
    except sqlite3.Error as error:
        raise JobStoreError(category(error)) from None
    try:
        result = body(connection)
    except BaseException as primary:
        try:
            connection.execute("ROLLBACK")
        except BaseException:
            workspace.retire()
            primary.add_note("rollback failed; workspace retired")
        if isinstance(primary, sqlite3.Error):
            raise JobStoreError(category(primary)) from None
        raise
    try:
        commit(connection)
    except BaseException:
        workspace.retire()
        raise JobStoreError("STORE_COMMIT_UNKNOWN") from None
    return result


def read(workspace: Workspace, body):
    connection = workspace.use()
    try:
        connection.execute("BEGIN")
        try:
            result = body(connection)
        except BaseException:
            try:
                connection.execute("ROLLBACK")
            except sqlite3.Error:
                workspace.retire()
            raise
        connection.execute("COMMIT")
        return result
    except sqlite3.Error as error:
        raise JobStoreError(category(error)) from None


def accounted_bytes(workspace: Workspace) -> int:
    """Database, WAL, SHM, envelope and lock files; not every transient allocation."""
    root = workspace._root_fd
    total = 0
    for name in (DATABASE, DATABASE + "-wal", DATABASE + "-shm", ENVELOPE):
        try:
            total += os.stat(name, dir_fd=root, follow_symlinks=False).st_size
        except FileNotFoundError:
            pass
    with os.scandir(workspace.locks_fd()) as entries:
        for entry in entries:
            total += entry.stat(follow_symlinks=False).st_size
    # Chunk files are charged once per inode: staging and final names share one.
    seen = set()
    for name in workspace._directories:
        fd = workspace.directory(name)
        try:
            with os.scandir(fd) as entries:
                for entry in entries:
                    state = entry.stat(follow_symlinks=False)
                    if (state.st_dev, state.st_ino) not in seen:
                        seen.add((state.st_dev, state.st_ino))
                        total += state.st_size
        finally:
            os.close(fd)
    return total


def admit(workspace: Workspace, payload: int, *, control: bool = False) -> None:
    """Conservative admission; data operations leave the control reserve intact."""
    need = 3 * payload + (0 if control else CONTROL_RESERVE)
    if accounted_bytes(workspace) + need > workspace.budget:
        raise JobStoreError("WORKSPACE_BUDGET")
    space = os.statvfs(workspace._root_fd)
    if space.f_bavail * space.f_frsize < need + CONTROL_RESERVE:
        raise JobStoreError("WORKSPACE_SPACE")


def _connect(root: str, budget: int, busy: float) -> sqlite3.Connection:
    uri = "file:" + quote(os.path.join(root, DATABASE)) + "?mode=rw"
    return sqlite3.connect(
        uri, uri=True, timeout=busy, isolation_level=None, check_same_thread=True
    )


def _busy(busy_seconds: object) -> float:
    if (
        not isinstance(busy_seconds, (int, float))
        or isinstance(busy_seconds, bool)
        or not 0 < busy_seconds <= MAX_BUSY_SECONDS
    ):
        raise JobStoreError("WORKSPACE_BUSY_BOUND")
    return float(busy_seconds)


def create_workspace(
    root: str,
    *,
    budget_bytes: int = DEFAULT_BUDGET,
    busy_seconds: float = 5.0,
    format: str = FORMAT,
) -> Workspace:
    """Exclusively create and atomically initialize a new private workspace."""
    root, parent, name = _canonical_root(root)
    busy = _busy(busy_seconds)
    if type(budget_bytes) is not int or not MIN_BUDGET <= budget_bytes <= MAX_BUDGET:
        raise JobStoreError("WORKSPACE_BUDGET")
    if type(format) is not str or format not in VERSIONS:
        raise JobStoreError("WORKSPACE_FORMAT")
    _features, version, schema, directories = VERSIONS[format]
    profile = storage_profile(parent)
    identity = new_identity("ws")
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    owned: dict[str, tuple[int, int]] = {}
    root_fd = locks_fd = -1
    connection = None
    try:
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            raise JobStoreError("WORKSPACE_EXISTS") from None
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
        os.mkdir(LOCKS, 0o700, dir_fd=root_fd)
        locks_fd = os.open(
            LOCKS, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd
        )
        lock_state = os.fstat(locks_fd)
        owned[LOCKS] = (lock_state.st_dev, lock_state.st_ino)
        _private(lock_state, stat.S_IFDIR)
        for directory in directories:
            os.mkdir(directory, 0o700, dir_fd=root_fd)
            state = os.stat(directory, dir_fd=root_fd, follow_symlinks=False)
            owned[directory] = (state.st_dev, state.st_ino)
            _private(state, stat.S_IFDIR)
        exclusive(DATABASE)
        os.fsync(root_fd)
        connection = _connect(root, budget_bytes, busy)
        connection.execute(f"PRAGMA page_size = {PAGE_SIZE}")
        if connection.execute("PRAGMA journal_mode = WAL").fetchone()[0] != "wal":
            raise JobStoreError("WORKSPACE_SETTINGS")
        _configure(connection, budget_bytes, busy)
        connection.execute("BEGIN IMMEDIATE")
        for statement in schema:
            connection.execute(statement)
        connection.execute(f"PRAGMA application_id = {APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version = {version}")
        connection.execute(
            "INSERT INTO workspace(singleton, identity, format) VALUES (1, ?, ?)",
            (identity, format),
        )
        commit(connection)
        _verify_database(connection, identity, format)
        exclusive(ENVELOPE, envelope_bytes(identity, budget_bytes, format))
        os.fsync(root_fd)
        os.unlink(CREATING, dir_fd=root_fd)
        del owned[CREATING]
        os.fsync(root_fd)
        workspace = Workspace(
            root,
            identity,
            budget_bytes,
            profile,
            connection,
            root_fd,
            locks_fd,
            format,
            {d: owned[d] for d in directories},
        )
        connection = None
        return workspace
    except BaseException:
        _abandon_creation(parent_fd, name, root_fd, locks_fd, connection, owned)
        raise
    finally:
        os.close(parent_fd)


def _abandon_creation(parent_fd, name, root_fd, locks_fd, connection, owned):
    """Remove only resources this call created; anything else stays incomplete."""
    if connection is not None:
        try:
            connection.close()
        except sqlite3.Error:
            pass
    if locks_fd >= 0:
        os.close(locks_fd)
    if root_fd < 0:
        return
    try:
        for child, identity in owned.items():
            try:
                current = os.stat(child, dir_fd=root_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) != identity:
                    continue
                if child in (LOCKS, CHUNKS, STAGING):
                    os.rmdir(child, dir_fd=root_fd)
                else:
                    os.unlink(child, dir_fd=root_fd)
            except OSError:
                pass
        if not os.listdir(root_fd):
            os.rmdir(name, dir_fd=parent_fd)
            os.fsync(parent_fd)
    except OSError:
        pass
    finally:
        os.close(root_fd)


def _verify_database(
    connection: sqlite3.Connection, identity: str, format: str = FORMAT
) -> None:
    if (
        connection.execute("PRAGMA journal_mode").fetchone()[0] != "wal"
        or connection.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID
        or connection.execute("PRAGMA user_version").fetchone()[0]
        != VERSIONS[format][1]
        or tuple(
            connection.execute(
                "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
            )
        )
        != expected_schema(format)
        or tuple(
            connection.execute("SELECT singleton, identity, format FROM workspace")
        )
        != ((1, identity, format),)
    ):
        raise JobStoreError("WORKSPACE_SCHEMA")


def open_workspace(
    root: str, *, expected_identity: str, busy_seconds: float = 5.0
) -> Workspace:
    """Open an existing complete workspace; unknown formats never reach SQLite."""
    root, _parent, _name = _canonical_root(root)
    busy = _busy(busy_seconds)
    if not valid_identity(expected_identity, "ws"):
        raise JobStoreError("WORKSPACE_IDENTITY")
    try:
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        raise JobStoreError("WORKSPACE_OBJECT") from None
    locks_fd = -1
    connection = None
    try:
        _private(os.fstat(root_fd), stat.S_IFDIR)
        profile = storage_profile(root)
        names = set(os.listdir(root_fd))
        if CREATING in names or ENVELOPE not in names or DATABASE not in names:
            raise JobStoreError("WORKSPACE_INCOMPLETE")
        envelope_fd = os.open(ENVELOPE, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=root_fd)
        try:
            _private(os.fstat(envelope_fd), stat.S_IFREG, single=True)
            raw = os.read(envelope_fd, MAX_ENVELOPE_BYTES + 1)
        finally:
            os.close(envelope_fd)
        identity, budget, format = read_envelope(raw)
        if identity != expected_identity:
            raise JobStoreError("WORKSPACE_IDENTITY")
        directories = VERSIONS[format][3]
        if names - {
            ENVELOPE,
            DATABASE,
            DATABASE + "-wal",
            DATABASE + "-shm",
            LOCKS,
            *directories,
        } or not names.issuperset(directories):
            raise JobStoreError("WORKSPACE_OBJECT")
        for child in names - {ENVELOPE, LOCKS, *directories}:
            _private(
                os.stat(child, dir_fd=root_fd, follow_symlinks=False),
                stat.S_IFREG,
                single=True,
            )
        found = {}
        for directory in directories:
            state = os.stat(directory, dir_fd=root_fd, follow_symlinks=False)
            _private(state, stat.S_IFDIR)
            found[directory] = (state.st_dev, state.st_ino)
        locks_fd = os.open(
            LOCKS, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd
        )
        _private(os.fstat(locks_fd), stat.S_IFDIR)
        database = os.stat(DATABASE, dir_fd=root_fd, follow_symlinks=False)
        connection = _connect(root, budget, busy)
        _configure(connection, budget, busy)
        if tuple(r[2] for r in connection.execute("PRAGMA database_list")) != (
            os.path.join(root, DATABASE),
        ):
            raise JobStoreError("WORKSPACE_OBJECT")
        _verify_database(connection, identity, format)
        after = os.stat(DATABASE, dir_fd=root_fd, follow_symlinks=False)
        if (after.st_dev, after.st_ino) != (database.st_dev, database.st_ino):
            raise JobStoreError("WORKSPACE_OBJECT")
        workspace = Workspace(
            root,
            identity,
            budget,
            profile,
            connection,
            root_fd,
            locks_fd,
            format,
            found,
        )
        connection = None
        return workspace
    except sqlite3.Error as error:
        _close_partial(connection, locks_fd, root_fd)
        raise JobStoreError(
            "STORE_BUSY" if category(error) == "STORE_BUSY" else "WORKSPACE_SCHEMA"
        ) from None
    except OSError:
        _close_partial(connection, locks_fd, root_fd)
        raise JobStoreError("WORKSPACE_OBJECT") from None
    except BaseException:
        _close_partial(connection, locks_fd, root_fd)
        raise


def _close_partial(connection, locks_fd, root_fd):
    if connection is not None:
        try:
            connection.close()
        except sqlite3.Error:
            pass
    if locks_fd >= 0:
        os.close(locks_fd)
    os.close(root_fd)
