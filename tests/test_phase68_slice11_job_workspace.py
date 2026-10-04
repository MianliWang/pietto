"""S11 qualified workspace: profile, exclusive create, exact open, settings, bounds."""

from pathlib import Path
from typing import Any
import json
import os
import sqlite3
import stat

import pytest

import _pietto_phase68_slice11_probe as probe
from pietto._project import project_job_workspace as w
from pietto._project.project_job_workspace import JobStoreError


@pytest.fixture
def qualified(tmp_path):
    return probe.qualified(tmp_path)


def snapshot(root: Path):
    return {
        p.name: (p.read_bytes(), p.stat().st_mtime_ns, stat.S_IMODE(p.lstat().st_mode))
        for p in sorted(root.iterdir())
        if p.is_file()
    }


def test_profile_binds_the_actual_measured_build_and_filesystem(tmp_path, qualified):
    if not qualified:
        return
    profile = w.storage_profile(str(tmp_path))
    probe = sqlite3.connect(":memory:")
    try:
        actual = (
            sqlite3.sqlite_version,
            probe.execute("SELECT sqlite_source_id()").fetchone()[0],
            tuple(r[0] for r in probe.execute("PRAGMA compile_options")),
        )
    finally:
        probe.close()
    assert actual in w.QUALIFIED_SQLITE and len(w.QUALIFIED_SQLITE) == 1
    assert (profile.sqlite_version, profile.sqlite_source_id) == actual[:2]
    assert profile.filesystem == "ext4" and "rw" in profile.super_options.split(",")
    assert profile.device_sync == "EXTERNAL_PREMISE_NOT_VERIFIED"


@pytest.mark.parametrize(
    "change,category",
    [
        ("platform", "WORKSPACE_PROFILE_PLATFORM"),
        ("engine", "WORKSPACE_PROFILE_SQLITE"),
        ("build", "WORKSPACE_PROFILE_SQLITE"),
        ("filesystem", "WORKSPACE_PROFILE_FILESYSTEM"),
        ("tmpfs", "WORKSPACE_PROFILE_FILESYSTEM"),
    ],
)
def test_unsupported_profile_refuses_before_any_file(
    tmp_path, monkeypatch, change, category
):
    root = tmp_path / "workspace"
    if change == "platform":
        monkeypatch.setattr(w.sys, "platform", "darwin")
    elif change == "engine":
        monkeypatch.setattr(w, "QUALIFIED_SQLITE", frozenset())
    elif change == "build":
        monkeypatch.setattr(
            w,
            "QUALIFIED_SQLITE",
            frozenset((v, s, o + ("OMIT_WAL",)) for v, s, o in w.QUALIFIED_SQLITE),
        )
    elif change == "filesystem":
        monkeypatch.setattr(w, "QUALIFIED_FILESYSTEMS", frozenset({"xfs"}))
    else:
        # A private owned directory on the real tmpfs; removed after the check.
        private = Path(os.path.realpath("/dev/shm")) / (
            "pietto-s11-refused-" + os.urandom(8).hex()
        )
        private.mkdir(mode=0o700)
        root = private / "workspace"
    probe = sqlite3.connect(":memory:")
    try:
        qualified_engine = (
            sqlite3.sqlite_version,
            probe.execute("SELECT sqlite_source_id()").fetchone()[0],
            tuple(r[0] for r in probe.execute("PRAGMA compile_options")),
        ) in w.QUALIFIED_SQLITE
    finally:
        probe.close()
    # The engine is checked before the filesystem, so an unqualified engine
    # reports itself first on every non-platform change.
    expected = (
        category
        if change == "platform" or qualified_engine
        else "WORKSPACE_PROFILE_SQLITE"
    )
    try:
        with pytest.raises(JobStoreError, match=expected):
            w.create_workspace(str(root))
        assert not root.exists()
    finally:
        if change == "tmpfs":
            root.parent.rmdir()


def test_exclusive_private_creation_and_exact_reopen(tmp_path, qualified):
    if not qualified:
        return
    root = tmp_path / "workspace"
    workspace = w.create_workspace(str(root), budget_bytes=w.MIN_BUDGET)
    assert repr(workspace) == f"Workspace(identity={workspace.identity!r})"
    workspace.close()
    workspace.close()
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE((root / "locks").stat().st_mode) == 0o700
    assert sorted(p.name for p in root.iterdir()) == [
        "locks",
        "store.sqlite",
        "workspace.json",
    ]
    for name in ("store.sqlite", "workspace.json"):
        assert stat.S_IMODE((root / name).stat().st_mode) == 0o600
    envelope = (root / "workspace.json").read_bytes()
    assert envelope == w.envelope_bytes(workspace.identity, w.MIN_BUDGET)
    assert json.loads(envelope) == {
        "budget": w.MIN_BUDGET,
        "database": "store.sqlite",
        "features": [],
        "format": "pietto.job-workspace.v1",
        "identity": workspace.identity,
    }
    before = snapshot(root)
    with pytest.raises(JobStoreError, match="WORKSPACE_EXISTS"):
        w.create_workspace(str(root))
    assert snapshot(root) == before
    again = w.open_workspace(str(root), expected_identity=workspace.identity)
    try:
        assert (again.identity, again.budget) == (workspace.identity, w.MIN_BUDGET)
    finally:
        again.close()
    with pytest.raises(JobStoreError, match="WORKSPACE_IDENTITY"):
        w.open_workspace(str(root), expected_identity=w.new_identity("ws"))
    with pytest.raises(JobStoreError, match="WORKSPACE_IDENTITY"):
        w.open_workspace(str(root), expected_identity="job-" + "0" * 32)


@pytest.mark.parametrize("damage", ["creating", "no_envelope", "no_database"])
def test_incomplete_workspace_is_never_an_empty_store(tmp_path, qualified, damage):
    if not qualified:
        return
    root = tmp_path / "workspace"
    workspace = w.create_workspace(str(root))
    workspace.close()
    if damage == "creating":
        (root / "CREATING").write_bytes(b"x")
        (root / "CREATING").chmod(0o600)
    elif damage == "no_envelope":
        (root / "workspace.json").unlink()
    else:
        (root / "store.sqlite").unlink()
    before = snapshot(root)
    with pytest.raises(JobStoreError, match="WORKSPACE_INCOMPLETE"):
        w.open_workspace(str(root), expected_identity=workspace.identity)
    assert snapshot(root) == before


@pytest.mark.parametrize(
    "rewrite",
    [
        lambda d: {**d, "format": "pietto.job-workspace.v2"},
        lambda d: {**d, "features": ["future-feature"]},
        lambda d: {**d, "database": "other.sqlite"},
        lambda d: {**d, "budget": w.MAX_BUDGET + 1},
        lambda d: {**d, "extra": 1},
        "noncanonical",
        "duplicate",
        "oversized",
        "binary",
    ],
)
def test_foreign_or_future_envelope_refuses_with_no_sqlite_open(
    tmp_path, qualified, monkeypatch, rewrite
):
    if not qualified:
        return
    root = tmp_path / "workspace"
    workspace = w.create_workspace(str(root))
    workspace.close()
    path = root / "workspace.json"
    document = json.loads(path.read_bytes())
    if rewrite == "noncanonical":
        raw = json.dumps(document, indent=1).encode()
    elif rewrite == "duplicate":
        raw = path.read_bytes().replace(b'{"budget"', b'{"budget":1,"budget"')
    elif rewrite == "oversized":
        raw = path.read_bytes() + b" " * w.MAX_ENVELOPE_BYTES
    elif rewrite == "binary":
        raw = b"\xff\xfe"
    else:
        raw = (
            json.dumps(rewrite(document), sort_keys=True, separators=(",", ":")) + "\n"
        ).encode()
    path.write_bytes(raw)
    before = snapshot(root)

    def forbidden(*args, **kwargs):
        raise AssertionError("SQLite opened before the envelope was accepted")

    monkeypatch.setattr(w, "_connect", forbidden)
    with pytest.raises(JobStoreError, match="WORKSPACE_FORMAT"):
        w.open_workspace(str(root), expected_identity=workspace.identity)
    assert snapshot(root) == before


@pytest.mark.parametrize(
    "tamper",
    [
        "PRAGMA application_id = 7",
        "PRAGMA user_version = 2",
        "CREATE TABLE extra(x INTEGER)",
        "CREATE VIEW v AS SELECT 1",
        "CREATE TRIGGER t AFTER INSERT ON job BEGIN SELECT 1; END",
        "UPDATE workspace SET identity = 'ws-00000000000000000000000000000000'",
        "PRAGMA journal_mode = DELETE",
        "not-a-database",
    ],
)
def test_known_envelope_with_foreign_database_refuses_without_application_write(
    tmp_path, qualified, tamper
):
    if not qualified:
        return
    root = tmp_path / "workspace"
    workspace = w.create_workspace(str(root))
    workspace.close()
    database = root / "store.sqlite"
    if tamper == "not-a-database":
        database.write_bytes(b"SQLite format 2\0" + b"\0" * 4080)
    else:
        raw = sqlite3.connect(database, isolation_level=None)
        try:
            raw.execute(tamper)
        finally:
            raw.close()
    main = database.read_bytes()
    with pytest.raises(JobStoreError, match="WORKSPACE_SCHEMA"):
        w.open_workspace(str(root), expected_identity=workspace.identity)
    # SQLite-managed -wal/-shm bookkeeping may appear for a known profile; the
    # main database bytes, journal mode and schema are not converted or repaired.
    assert database.read_bytes() == main
    if tamper == "PRAGMA journal_mode = DELETE":
        raw = sqlite3.connect(database, isolation_level=None)
        try:
            assert raw.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        finally:
            raw.close()


@pytest.mark.parametrize(
    "case,category",
    [
        ("relative", "WORKSPACE_PATH"),
        ("normalized", "WORKSPACE_PATH"),
        ("symlink_root", "WORKSPACE_OBJECT"),
        ("symlink_parent", "WORKSPACE_PATH"),
        ("open_parent", "WORKSPACE_PARENT"),
        ("root_mode", "WORKSPACE_OBJECT"),
        ("database_symlink", "WORKSPACE_OBJECT"),
        ("database_hardlink", "WORKSPACE_OBJECT"),
        ("database_mode", "WORKSPACE_OBJECT"),
        ("special_file", "WORKSPACE_OBJECT"),
        ("unknown_file", "WORKSPACE_OBJECT"),
        ("locks_symlink", "WORKSPACE_OBJECT"),
    ],
)
def test_path_object_and_permission_substitutions_refuse_without_repair(
    tmp_path, qualified, case, category
):
    if not qualified:
        return
    root = tmp_path / "workspace"
    workspace = w.create_workspace(str(root))
    workspace.close()
    target = str(root)
    if case == "relative":
        target = os.path.relpath(root)
    elif case == "normalized":
        target = str(root) + "/."
    elif case == "symlink_root":
        (tmp_path / "alias").symlink_to(root)
        target = str(tmp_path / "alias")
    elif case == "symlink_parent":
        (tmp_path / "parent-alias").symlink_to(tmp_path)
        target = str(tmp_path / "parent-alias" / "workspace")
    elif case == "open_parent":
        tmp_path.chmod(0o777)
    elif case == "root_mode":
        root.chmod(0o755)
    elif case == "database_symlink":
        (root / "store.sqlite").rename(tmp_path / "moved.sqlite")
        (root / "store.sqlite").symlink_to(tmp_path / "moved.sqlite")
    elif case == "database_hardlink":
        os.link(root / "store.sqlite", tmp_path / "second-name")
    elif case == "database_mode":
        (root / "store.sqlite").chmod(0o644)
    elif case == "special_file":
        os.mkfifo(root / "store.sqlite-wal", 0o600)
    elif case == "unknown_file":
        (root / "unexpected").write_bytes(b"")
        (root / "unexpected").chmod(0o600)
    else:
        (root / "locks").rename(tmp_path / "locks")
        (root / "locks").symlink_to(tmp_path / "locks")
    modes = {p.name: stat.S_IMODE(p.lstat().st_mode) for p in root.iterdir()}
    try:
        with pytest.raises(JobStoreError, match=category):
            w.open_workspace(target, expected_identity=workspace.identity)
        assert {
            p.name: stat.S_IMODE(p.lstat().st_mode) for p in root.iterdir()
        } == modes
    finally:
        tmp_path.chmod(0o700)


def test_every_connection_setting_is_read_back(tmp_path, qualified):
    if not qualified:
        return
    workspace = w.create_workspace(str(tmp_path / "workspace"), busy_seconds=0.5)
    try:
        connection = workspace.use()
        for name, value in w._SAFE_CONFIG:
            assert (
                connection.getconfig(getattr(sqlite3, "SQLITE_DBCONFIG_" + name))
                is value
            )
        observed = {
            p: connection.execute(f"PRAGMA {p}").fetchone()[0]
            for p in (
                "journal_mode",
                "synchronous",
                "foreign_keys",
                "temp_store",
                "busy_timeout",
                "max_page_count",
                "journal_size_limit",
                "cell_size_check",
                "application_id",
                "user_version",
            )
        }
        assert observed == {
            "journal_mode": "wal",
            "synchronous": 2,
            "foreign_keys": 1,
            "temp_store": 2,
            "busy_timeout": 500,
            "max_page_count": w.DEFAULT_BUDGET // w.PAGE_SIZE,
            "journal_size_limit": w.JOURNAL_SIZE_LIMIT,
            "cell_size_check": 1,
            "application_id": w.APPLICATION_ID,
            "user_version": w.SCHEMA_VERSION,
        }
        with pytest.raises(sqlite3.OperationalError, match="too many attached"):
            connection.execute("ATTACH ':memory:' AS other")
        assert (
            tuple(
                connection.execute(
                    "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
                )
            )
            == w.expected_schema()
        )
    finally:
        workspace.close()
    bad_busy: tuple[Any, ...] = (0, -1, 31, True, "5", float("nan"))
    for bad in bad_busy:
        with pytest.raises(JobStoreError, match="WORKSPACE_BUSY_BOUND"):
            w.create_workspace(str(tmp_path / "other"), busy_seconds=bad)
    bad_budget: tuple[Any, ...] = (w.MIN_BUDGET - 1, w.MAX_BUDGET + 1, True, 1.0)
    for bad in bad_budget:
        with pytest.raises(JobStoreError, match="WORKSPACE_BUDGET"):
            w.create_workspace(str(tmp_path / "other"), budget_bytes=bad)
    assert not (tmp_path / "other").exists()


def test_admission_keeps_a_control_reserve(tmp_path, qualified):
    if not qualified:
        return
    workspace = w.create_workspace(
        str(tmp_path / "workspace"), budget_bytes=w.MIN_BUDGET
    )
    try:
        used = w.accounted_bytes(workspace)
        assert 0 < used < w.MIN_BUDGET - w.CONTROL_RESERVE
        room = w.MIN_BUDGET - used
        w.admit(workspace, (room - w.CONTROL_RESERVE) // 3)
        with pytest.raises(JobStoreError, match="WORKSPACE_BUDGET"):
            w.admit(workspace, (room - w.CONTROL_RESERVE) // 3 + 1)
        # Only control operations may use the reserve.
        w.admit(workspace, room // 3, control=True)
        with pytest.raises(JobStoreError, match="WORKSPACE_BUDGET"):
            w.admit(workspace, room // 3 + 1, control=True)
    finally:
        workspace.close()


def test_busy_wait_is_bounded_and_leaves_no_change(tmp_path, qualified):
    if not qualified:
        return
    import time

    workspace = w.create_workspace(str(tmp_path / "workspace"), busy_seconds=0.2)
    holder = sqlite3.connect(
        tmp_path / "workspace" / "store.sqlite", isolation_level=None
    )
    try:
        holder.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        with pytest.raises(JobStoreError, match="STORE_BUSY"):
            w.write(workspace, lambda c: c.execute("SELECT 1"))
        assert 0.15 < time.monotonic() - started < 5
        holder.execute("ROLLBACK")
        assert w.read(
            workspace, lambda c: c.execute("SELECT count(*) FROM job").fetchone()
        ) == (0,)
    finally:
        holder.close()
        workspace.close()


def test_handle_lifetime_and_foreign_process(tmp_path, qualified):
    if not qualified:
        return
    workspace = w.create_workspace(str(tmp_path / "workspace"))
    workspace.close()
    with pytest.raises(JobStoreError, match="WORKSPACE_CLOSED"):
        workspace.use()
    workspace = w.open_workspace(
        str(tmp_path / "workspace"), expected_identity=workspace.identity
    )
    try:
        replacement = tmp_path / "replacement"
        replacement.mkdir(mode=0o700)
        (tmp_path / "workspace").rename(tmp_path / "moved")
        replacement.rename(tmp_path / "workspace")
        with pytest.raises(JobStoreError, match="WORKSPACE_OBJECT"):
            workspace.use()
        replacement = tmp_path / "workspace"
        replacement.rename(tmp_path / "replacement")
        (tmp_path / "moved").rename(tmp_path / "workspace")
        workspace.use()
        workspace._pid = -1
        with pytest.raises(JobStoreError, match="WORKSPACE_FOREIGN_PROCESS"):
            workspace.use()
        with pytest.raises(JobStoreError, match="WORKSPACE_FOREIGN_PROCESS"):
            workspace.close()
    finally:
        workspace._pid = os.getpid()
        workspace.close()


class _Connection:
    """Explicit labeled fault injection around one real connection."""

    def __init__(self, real, fail):
        self.real, self.fail = real, fail

    def execute(self, sql, *args):
        if sql == self.fail:
            raise sqlite3.OperationalError("injected " + sql)
        return self.real.execute(sql, *args)

    def close(self):
        self.real.close()
        if self.fail == "close":
            raise sqlite3.OperationalError("injected close")


def test_primary_and_cleanup_failures_are_both_reported(tmp_path, qualified):
    if not qualified:
        return
    workspace = w.create_workspace(str(tmp_path / "workspace"))
    real = workspace._connection
    workspace._connection = _Connection(real, "ROLLBACK")  # type: ignore[assignment]

    def primary(connection):
        raise ValueError("primary")

    with pytest.raises(ValueError, match="primary") as raised:
        w.write(workspace, primary)
    assert raised.value.__notes__ == ["rollback failed; workspace retired"]
    with pytest.raises(JobStoreError, match="WORKSPACE_RETIRED"):
        workspace.use()
    workspace.close()
    again = w.open_workspace(
        str(tmp_path / "workspace"), expected_identity=workspace.identity
    )
    again._connection = _Connection(again._connection, "close")  # type: ignore[assignment]
    with pytest.raises(JobStoreError, match="STORE_CLOSE"):
        again.close()
    with pytest.raises(OSError):
        os.fstat(again._root_fd)
