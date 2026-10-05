"""S12 chunk frame, coordinate atoms, coverage law, v1/v2 split and file protocol."""

from datetime import datetime
from decimal import Decimal
import errno
import hashlib
import json
import os
import sqlite3
import stat
from typing import Any
from uuid import UUID

import pytest

import _pietto_phase68_slice12_probe as probe
from _pietto_phase68_slice11_probe import compiled_template, qualified
from pietto._project import project_job_capture as c
from pietto._project import project_job_chunks as k
from pietto._project import project_job_store as s
from pietto._project import project_job_workspace as w
from pietto._project.project_job_store_verification import verify_store
from pietto._project.project_job_workspace import JobStoreError

DESCRIPTOR: dict[str, Any] = {
    "attempt": "att-" + "1" * 32,
    "batches": 1,
    "binding": "bind-" + "2" * 32,
    "chunk": "chk-" + "3" * 32,
    "contract": "ab" * 32,
    "coordinates": None,
    "generation": "gen-" + "4" * 32,
    "job": "job-" + "5" * 32,
    "kind": "ORDINARY",
    "rows": 2,
    "start": 4,
    "stop": 6,
    "terminal": None,
    "workspace": "ws-" + "6" * 32,
}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("s12-templates")
    return {
        "small": compiled_template(root / "small", entry="bundle"),
        "small_live": compiled_template(root / "small-live"),
        "seven": probe.seven_template(root / "seven"),
    }


def test_descriptor_frame_round_trip_and_closed_fields():
    frame = probe.synthetic_frame(2)
    text, data = k.encode_chunk(DESCRIPTOR, frame)
    assert data[:16] == k.MAGIC and len(data) == k.HEADER.size + len(text) + len(frame)
    decoded_text, descriptor, decoded_frame = k.decode_chunk(data)
    assert (decoded_text, decoded_frame) == (text, frame)
    assert descriptor == {
        **DESCRIPTOR,
        "format": "pietto.result-chunk.v1",
        "frame_bytes": len(frame),
        "frame_sha256": hashlib.sha256(frame).hexdigest(),
    }
    assert text == k.canonical(descriptor) and text.isascii()
    for missing in ("terminal", "coordinates"):
        partial = {n: v for n, v in DESCRIPTOR.items() if n != missing}
        with pytest.raises(JobStoreError, match="CHUNK_FORMAT"):
            k.encode_chunk(partial, frame)
    with pytest.raises(JobStoreError, match="CHUNK_FORMAT"):
        k.encode_chunk({**DESCRIPTOR, "extra": 1}, frame)


def _reframe(raw_descriptor: bytes, frame: bytes) -> bytes:
    body = raw_descriptor + frame
    return (
        k.HEADER.pack(
            k.MAGIC, len(raw_descriptor), len(frame), hashlib.sha256(body).digest()
        )
        + body
    )


def test_outer_frame_and_descriptor_damage_refuse():
    frame = probe.synthetic_frame(2)
    text, data = k.encode_chunk(DESCRIPTOR, frame)
    for offset in (0, 15, 16, 23, 24, 31, 32, 63, 64, len(data) // 2, len(data) - 1):
        damaged = bytearray(data)
        damaged[offset] ^= 1
        with pytest.raises(JobStoreError, match="CHUNK_FORMAT"):
            k.decode_chunk(bytes(damaged))
    for invalid in (
        data[:-1],
        data + b"\0",
        b"",
        data[: k.HEADER.size],
        bytearray(data),
    ):
        with pytest.raises(JobStoreError, match="CHUNK_FORMAT"):
            k.decode_chunk(invalid)  # type: ignore[arg-type]
    document = json.loads(text)
    # A consistently re-hashed outer frame still needs the exact canonical text,
    # closed keys, unique keys and the frame correspondence.
    rewrites = (
        json.dumps(document, indent=1).encode(),
        text.replace('{"attempt"', '{"attempt":"x","attempt"', 1).encode(),
        k.canonical({**document, "extra": 1}).encode(),
        k.canonical({**document, "frame_bytes": len(frame) + 1}).encode(),
        k.canonical({**document, "frame_sha256": "00" * 32}).encode(),
        k.canonical({**document, "format": "pietto.result-chunk.v2"}).encode(),
        b"\xff",
    )
    for raw in rewrites:
        with pytest.raises(JobStoreError, match="CHUNK_FORMAT"):
            k.decode_chunk(_reframe(raw, frame))


def test_lengths_are_bounded_before_allocation():
    with pytest.raises(JobStoreError, match="CHUNK_LIMIT"):
        k.encode_chunk(DESCRIPTOR, b"\0" * (k.MAX_FRAME_BYTES + 1))
    huge = {**DESCRIPTOR, "coordinates": [["str", "x" * 1024]] * 2048}
    with pytest.raises(JobStoreError, match="CHUNK_LIMIT"):
        k.encode_chunk(huge, b"frame")
    claim = k.HEADER.pack(k.MAGIC, k.MAX_DESCRIPTOR_BYTES + 1, 0, bytes(32))
    with pytest.raises(JobStoreError, match="CHUNK_FORMAT"):
        k.decode_chunk(claim + b"\0" * 8)
    claim = k.HEADER.pack(k.MAGIC, 1, k.MAX_FRAME_BYTES + 1, bytes(32))
    with pytest.raises(JobStoreError, match="CHUNK_FORMAT"):
        k.decode_chunk(claim + b"\0" * 8)
    assert k.MAX_FRAME_BYTES < 96 * 1024 * 1024
    assert (
        k.HEADER.size + k.MAX_DESCRIPTOR_BYTES + k.MAX_FRAME_BYTES == k.MAX_FILE_BYTES
    )


@pytest.mark.parametrize(
    "value,wire",
    [
        (-0.0, ["float", "-0x0.0p+0"]),
        (0.0, ["float", "0x0.0p+0"]),
        (5e-324, ["float", "0x0.0000000000001p-1022"]),
        (Decimal("1.10"), ["decimal", 0, [1, 1, 0], -2]),
        (Decimal("1.1"), ["decimal", 0, [1, 1], -1]),
        (Decimal("-0"), ["decimal", 1, [0], 0]),
        (datetime(2021, 11, 7, 1, 30, fold=1), ["datetime", "2021-11-07T01:30:00", 1]),
        (datetime(2021, 11, 7, 1, 30), ["datetime", "2021-11-07T01:30:00", 0]),
        (
            UUID("00112233-4455-6677-8899-aabbccddeeff"),
            ["uuid", "00112233445566778899aabbccddeeff"],
        ),
        (b"\x00\xff", ["bytes", "00ff"]),
        (True, ["bool", True]),
        (1, ["int", 1]),
        (-(2**63), ["int", -(2**63)]),
        ("雪é😀", ["str", "雪é😀"]),
        (None, ["NoneType", None]),
    ],
)
def test_coordinate_atoms_round_trip_exactly(value, wire):
    assert k.coordinate_wire(value) == wire
    back = k.read_coordinate(json.loads(json.dumps(wire)))
    assert type(back) is type(value) and k.coordinate_wire(back) == wire
    if isinstance(value, datetime):
        assert isinstance(back, datetime) and back.fold == value.fold


@pytest.mark.parametrize(
    "wire",
    [
        ["int", True],
        ["bool", 1],
        ["float", "0x1p0", 1],
        ["decimal", 0, [1, 1, 0], -1, 0],
        ["datetime", "2021-11-07T01:30:00", 2],
        ["uuid", "00"],
        ["NoneType", 0],
        ["object", 1],
        [],
        "int",
        ["str", 1],
    ],
)
def test_coordinate_wire_refuses_non_canonical(wire):
    with pytest.raises(JobStoreError, match="CHUNK_COORDINATE"):
        k.read_coordinate(wire)


def test_frontier_is_the_contiguous_prefix_not_max_stop():
    assert c.frontier([]) == 0
    assert c.frontier([(0, 0)]) == 0
    assert c.frontier([(0, 2), (4, 6)]) == 2
    assert c.frontier([(4, 6), (0, 2), (2, 4)]) == 6
    assert c.frontier([(2, 4), (4, 6)]) == 0
    assert c.holes([(0, 2), (4, 6)]) == ((2, 4),)
    assert c.holes([(0, 2), (4, 6)], 9) == ((2, 4), (6, 9))
    assert c.holes([], 3) == ((0, 3),)
    assert c.holes([(0, 0)], 0) == ()


def test_compiled_contract_identity_is_source_free_and_exact(built):
    from pietto._project.project_compiled_schema import _wire
    from pietto._project.project_execution import compiled_output
    from pietto._project.project_execution_template import (
        bind_values,
        describe_compiled_binding,
    )

    small, built_small = built["small"]
    live, _ = built["small_live"]
    seven, _ = built["seven"]
    digests = {}
    for name, template, value in (
        ("small_a", small, 1),
        ("small_b", small, 5),
        ("live_a", live, 1),
    ):
        binding = bind_values(template, ((template.slots[0], value),))
        output, refinement, program = compiled_output(binding)
        assert refinement is None and program is None
        digests[name] = c.contract_digest(output)
        # Independent recomputation from the stored S11 generation description.
        description = describe_compiled_binding(binding, route="postgres_rows")
        root = template.artifact.request.verification.completed.root
        document = {
            "fields": [
                [o[0], o[1], "builtin", o[3], o[4], None] for o in description.outputs
            ],
            "format": "pietto.compiled-result-contract.v1",
            "multiplicity": output.contract.multiplicity.value,
            "pin": built_small.pin,
            "query": _wire(root.description.query),
        }
        expected = hashlib.sha256(
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        assert digests[name] == expected
    assert digests["small_a"] == digests["small_b"] == digests["live_a"]
    seven_binding = bind_values(seven, ())
    assert c.contract_digest(compiled_output(seven_binding)[0]) != digests["small_a"]


def test_v1_default_and_v2_explicit_layouts(tmp_path):
    if not qualified(tmp_path):
        return
    v1 = w.create_workspace(str(tmp_path / "v1"))
    v2 = w.create_workspace(str(tmp_path / "v2"), format=w.FORMAT_V2)
    try:
        assert (v1.format, v2.format) == (w.FORMAT, w.FORMAT_V2)
        for name in ("chunks", "staging"):
            assert stat.S_IMODE((tmp_path / "v2" / name).stat().st_mode) == 0o700
        assert json.loads((tmp_path / "v2" / "workspace.json").read_bytes()) == {
            "budget": w.DEFAULT_BUDGET,
            "database": "store.sqlite",
            "features": ["result-chunks"],
            "format": "pietto.job-workspace.v2",
            "identity": v2.identity,
        }
        for handle, version, schema in ((v1, 1, w.SCHEMA), (v2, 2, w.SCHEMA)):
            connection = handle.use()
            assert connection.execute("PRAGMA user_version").fetchone()[0] == version
            assert tuple(
                connection.execute(
                    "SELECT type, name, tbl_name, sql FROM sqlite_schema"
                    " ORDER BY type, name"
                )
            ) == w.expected_schema(handle.format)
            assert schema == w.SCHEMA
        assert set(w.expected_schema()) < set(w.expected_schema(w.FORMAT_V2))
    finally:
        v1.close()
        v2.close()
    assert sorted(os.listdir(tmp_path / "v1")) == [
        "locks",
        "store.sqlite",
        "workspace.json",
    ]
    assert sorted(os.listdir(tmp_path / "v2")) == [
        "chunks",
        "locks",
        "staging",
        "store.sqlite",
        "workspace.json",
    ]
    for name, handle in (("v1", v1), ("v2", v2)):
        again = w.open_workspace(
            str(tmp_path / name), expected_identity=handle.identity
        )
        try:
            assert again.format == handle.format
        finally:
            again.close()


@pytest.mark.parametrize(
    "rewrite",
    [
        lambda d: {**d, "features": []},
        lambda d: {**d, "format": "pietto.job-workspace.v1"},
        lambda d: {**d, "format": "pietto.job-workspace.v5"},
        lambda d: {**d, "features": ["result-chunks", "gc"]},
    ],
)
def test_mismatched_or_future_versions_refuse_before_sqlite(
    tmp_path, monkeypatch, rewrite
):
    if not qualified(tmp_path):
        return
    root = tmp_path / "workspace"
    workspace = w.create_workspace(str(root), format=w.FORMAT_V2)
    workspace.close()
    path = root / "workspace.json"
    document = rewrite(json.loads(path.read_bytes()))
    path.write_bytes((k.canonical(document) + "\n").encode())
    before = probe.tree(root)

    def forbidden(*args, **kwargs):
        raise AssertionError("SQLite opened before the envelope was accepted")

    monkeypatch.setattr(w, "_connect", forbidden)
    with pytest.raises(JobStoreError, match="WORKSPACE_FORMAT"):
        w.open_workspace(str(root), expected_identity=workspace.identity)
    assert probe.tree(root) == before
    for bad in ("pietto.job-workspace.v5", None, b"pietto.job-workspace.v2"):
        with pytest.raises(JobStoreError, match="WORKSPACE_FORMAT"):
            w.create_workspace(str(tmp_path / "other"), format=bad)  # type: ignore[arg-type]
    assert not (tmp_path / "other").exists()


@pytest.mark.parametrize(
    "damage", ["v1_database", "missing_chunks", "symlink", "extra"]
)
def test_version_specific_objects_and_schema(tmp_path, damage):
    if not qualified(tmp_path):
        return
    root = tmp_path / "v2"
    v2 = w.create_workspace(str(root), format=w.FORMAT_V2)
    v2.close()
    expected = "WORKSPACE_OBJECT"
    if damage == "v1_database":
        v1 = w.create_workspace(str(tmp_path / "v1"))
        v1.close()
        for name in ("store.sqlite-wal", "store.sqlite-shm"):
            (root / name).unlink(missing_ok=True)
        (root / "store.sqlite").write_bytes(
            (tmp_path / "v1" / "store.sqlite").read_bytes()
        )
        expected = "WORKSPACE_SCHEMA"
    elif damage == "missing_chunks":
        (root / "chunks").rmdir()
    elif damage == "symlink":
        (root / "staging").rmdir()
        (root / "staging").symlink_to(tmp_path)
    else:
        (root / "chunks2").mkdir(mode=0o700)
    with pytest.raises(JobStoreError, match=expected):
        w.open_workspace(str(root), expected_identity=v2.identity)
    # A v1 workspace never accepts S12 directories either.
    v1root = tmp_path / "plain"
    v1 = w.create_workspace(str(v1root))
    v1.close()
    (v1root / "chunks").mkdir(mode=0o700)
    with pytest.raises(JobStoreError, match="WORKSPACE_OBJECT"):
        w.open_workspace(str(v1root), expected_identity=v1.identity)


def test_capture_apis_refuse_v1_without_upgrade(tmp_path, built):
    if not qualified(tmp_path):
        return
    template, _ = built["small"]
    workspace, job, publisher, binding, _record, generation = probe.store(
        tmp_path / "v1", template, (1,), format=w.FORMAT
    )
    try:
        attempt = s.open_attempt(publisher, generation, binding, operation=probe.op())
        before = probe.tree(tmp_path / "v1")
        schema = w.expected_schema()
        for call in (
            lambda: c.begin_capture(
                publisher, attempt, probe.pg_owner(binding), operation=probe.op()
            ),
            lambda: c.checkpoint_snapshot(workspace, job, generation),
            lambda: c.retain_checkpoint(
                publisher, generation, scope={"purpose": "read"}, operation=probe.op()
            ),
            lambda: c.protected_chunks(workspace, job),
            lambda: c.classify_files(workspace),
        ):
            with pytest.raises(JobStoreError, match="WORKSPACE_CAPTURE_FORMAT"):
                call()
        with pytest.raises(JobStoreError, match="WORKSPACE_CAPTURE_FORMAT"):
            workspace.directory("chunks")
        assert probe.tree(tmp_path / "v1") == before
        connection = workspace.use()
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert (
            tuple(
                connection.execute(
                    "SELECT type, name, tbl_name, sql FROM sqlite_schema ORDER BY type, name"
                )
            )
            == schema
        )
        assert verify_store(workspace)["attempts"] == 1
    finally:
        publisher.close()
        workspace.close()


def test_failed_v2_creation_removes_only_owned_objects(tmp_path, monkeypatch):
    if not qualified(tmp_path):
        return

    def fail(*args, **kwargs):
        raise sqlite3.OperationalError("injected")

    monkeypatch.setattr(w, "_configure", fail)
    with pytest.raises(sqlite3.OperationalError):
        w.create_workspace(str(tmp_path / "workspace"), format=w.FORMAT_V2)
    assert not (tmp_path / "workspace").exists()
    monkeypatch.undo()
    (tmp_path / "taken").mkdir(mode=0o700)
    with pytest.raises(JobStoreError, match="WORKSPACE_EXISTS"):
        w.create_workspace(str(tmp_path / "taken"), format=w.FORMAT_V2)
    assert os.listdir(tmp_path / "taken") == []


@pytest.fixture
def v2(tmp_path):
    if not qualified(tmp_path):
        yield None
        return
    handle = w.create_workspace(str(tmp_path / "workspace"), format=w.FORMAT_V2)
    yield handle
    if not handle._closed:
        handle.close()


def names(workspace, directory):
    return sorted(os.listdir(os.path.join(workspace.root, directory)))


def test_durable_publication_of_one_file_is_no_clobber(v2):
    if v2 is None:
        return
    identity = w.new_identity("chk")
    data = b"chunk bytes"
    facts = k.write_chunk(v2, identity, data)
    path = os.path.join(v2.root, "chunks", identity + ".chunk")
    state = os.lstat(path)
    assert facts == k.FileFacts(
        identity + ".chunk",
        len(data),
        hashlib.sha256(data).hexdigest(),
        state.st_dev,
        state.st_ino,
        state.st_ctime_ns,
    )
    assert stat.S_IMODE(state.st_mode) == 0o600 and state.st_nlink == 1
    assert names(v2, "staging") == []
    with pytest.raises(JobStoreError, match="CHUNK_COLLISION"):
        k.write_chunk(v2, identity, b"other bytes")
    assert open(path, "rb").read() == data and names(v2, "staging") == []
    other = w.new_identity("chk")
    os.close(
        os.open(
            os.path.join(v2.root, "staging", other + ".staging"),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    )
    with pytest.raises(JobStoreError, match="CHUNK_COLLISION"):
        k.write_chunk(v2, other, data)
    # Not this call's file: the pre-existing staging name is left alone.
    assert names(v2, "staging") == [other + ".staging"]
    assert names(v2, "chunks") == [identity + ".chunk"]


@pytest.mark.parametrize(
    "fault,code,final",
    [
        ("short_write", "CHUNK_IO", False),
        ("file_fsync", "CHUNK_IO", False),
        ("link", "CHUNK_IO", False),
        ("directory_fsync", "CHUNK_ORPHANED_IO", True),
    ],
)
def test_injected_io_faults_leave_no_reference(v2, monkeypatch, fault, code, final):
    if v2 is None:
        return
    calls = []
    real_sync, real_write = k._sync, os.write

    def sync(fd):
        calls.append(fd)
        if (fault == "file_fsync" and len(calls) == 1) or (
            fault == "directory_fsync" and len(calls) == 2
        ):
            raise OSError(errno.EIO, "injected")
        real_sync(fd)

    def link(*args):
        raise OSError(errno.EIO, "injected")

    if fault == "short_write":
        monkeypatch.setattr(k.os, "write", lambda fd, view: 0)
    monkeypatch.setattr(k, "_sync", sync)
    if fault == "link":
        monkeypatch.setattr(k, "_link", link)
    identity = w.new_identity("chk")
    with pytest.raises(JobStoreError, match=code):
        k.write_chunk(v2, identity, b"x" * 100)
    monkeypatch.setattr(k.os, "write", real_write)
    assert names(v2, "staging") == []
    assert names(v2, "chunks") == ([identity + ".chunk"] if final else [])


def test_bounded_reads_refuse_damaged_or_foreign_objects(v2, tmp_path):
    if v2 is None:
        return
    data = b"\0" * k.HEADER.size + b"payload"
    digest = hashlib.sha256(data).hexdigest()
    root = os.path.join(v2.root, "chunks")

    def make(name, content=data, mode=0o600):
        path = os.path.join(root, name)
        with open(path, "xb") as stream:
            stream.write(content)
        os.chmod(path, mode)
        return path

    make("good.chunk")
    make("short.chunk", data[:-1])
    make("long.chunk", data + b"x")
    make("same.chunk", data[:-1] + b"?")
    make("shared.chunk", mode=0o644)
    os.link(make("linked.chunk"), os.path.join(tmp_path, "outside"))
    os.symlink("good.chunk", os.path.join(root, "symlink.chunk"))
    os.mkfifo(os.path.join(root, "fifo.chunk"), 0o600)
    fd = v2.directory("chunks")
    try:
        assert k.read_chunk_file(fd, "good.chunk", len(data), digest) == data
        for name, size, code in (
            ("missing.chunk", len(data), "CHUNK_MISSING"),
            ("short.chunk", len(data), "CHUNK_SIZE"),
            ("long.chunk", len(data), "CHUNK_SIZE"),
            ("same.chunk", len(data), "CHUNK_DIGEST"),
            ("shared.chunk", len(data), "CHUNK_OBJECT"),
            ("linked.chunk", len(data), "CHUNK_OBJECT"),
            ("symlink.chunk", len(data), "CHUNK_OBJECT"),
            ("fifo.chunk", len(data), "CHUNK_OBJECT"),
            ("../good.chunk", len(data), "CHUNK_OBJECT"),
            ("good.other", len(data), "CHUNK_OBJECT"),
            ("good.chunk", k.MAX_FILE_BYTES + 1, "CHUNK_OBJECT"),
        ):
            with pytest.raises(JobStoreError, match=code):
                k.read_chunk_file(fd, name, size, digest)
    finally:
        os.close(fd)


def test_accounting_charges_each_inode_once_and_admission_creates_nothing(tmp_path):
    if not qualified(tmp_path):
        return
    workspace = w.create_workspace(
        str(tmp_path / "workspace"), budget_bytes=w.MIN_BUDGET, format=w.FORMAT_V2
    )
    try:
        before = w.accounted_bytes(workspace)
        identity = w.new_identity("chk")
        k.write_chunk(workspace, identity, b"y" * 4096)
        assert w.accounted_bytes(workspace) == before + 4096
        os.link(
            os.path.join(workspace.root, "chunks", identity + ".chunk"),
            os.path.join(workspace.root, "staging", "alias.staging"),
        )
        assert w.accounted_bytes(workspace) == before + 4096
        os.unlink(os.path.join(workspace.root, "staging", "alias.staging"))
        room = w.MIN_BUDGET - w.accounted_bytes(workspace) - w.CONTROL_RESERVE
        with pytest.raises(JobStoreError, match="WORKSPACE_BUDGET"):
            k.write_chunk(workspace, w.new_identity("chk"), b"z" * (room // 3 + 1))
        assert names(workspace, "chunks") == [identity + ".chunk"]
        assert names(workspace, "staging") == []
    finally:
        workspace.close()
