"""Bounded immutable result chunk files inside a v2 job workspace.

A chunk file is one fixed frame: header, canonical descriptor and the unchanged
private result IPC frame. Its whole-file digest protects a file boundary, never
authenticity against same-user edits. Files are made durable before any
metadata names them; product code never reopens a final file for writing and
deletes one only through the v7 collection protocol (an exclusive lease and a
committed tombstone first). Device/OS synchronization honesty is external.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import errno
import fcntl
import hashlib
import json
import os
import stat
import struct
import time
from typing import Any, cast
from uuid import UUID

from pietto._project.project_job_workspace import (
    CHUNKS,
    STAGING,
    JobStoreError,
    Workspace,
    admit,
)

__all__: tuple[str, ...] = ()

LEASE = ".life"
MAX_LEASE_WAIT = 30.0

FORMAT = "pietto.result-chunk.v1"
COORDINATES = "pietto.coordinate-atoms.v1"
HEADER = struct.Struct(">16sQQ32s")
MAGIC = b"PIETTO-CHUNK1\x00\x00\x00"
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_DESCRIPTOR_BYTES = 2 * 1024 * 1024
MAX_FRAME_BYTES = MAX_FILE_BYTES - HEADER.size - MAX_DESCRIPTOR_BYTES
MAX_ROWS = 4096
SUFFIX = ".chunk"
STAGED = ".staging"
FIELDS = frozenset(
    {
        "attempt",
        "batches",
        "binding",
        "chunk",
        "contract",
        "coordinates",
        "format",
        "frame_bytes",
        "frame_sha256",
        "generation",
        "job",
        "kind",
        "rows",
        "start",
        "stop",
        "terminal",
        "workspace",
    }
)


def canonical(value) -> str:
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _unique(items):
    result = {}
    for key, value in items:
        if key in result:
            raise JobStoreError("CHUNK_FORMAT")
        result[key] = value
    return result


def coordinate_wire(value) -> list:
    """S06 coordinate atoms as JSON: float bits, Decimal tuple, fold, UUID bytes."""
    from pietto._project.project_refinement_enumeration import atom

    try:
        kind, *rest = cast(tuple[Any, ...], atom(value))
    except ValueError:
        raise JobStoreError("CHUNK_COORDINATE") from None
    if kind == "decimal":
        sign, digits, exponent = rest[0]
        return [kind, sign, list(digits), exponent]
    if kind in ("uuid", "bytes"):
        return [kind, rest[0].hex()]
    return [kind, *rest]


def read_coordinate(wire):
    """Closed inverse of `coordinate_wire`; the round trip must be exact."""
    try:
        kind = wire[0]
        if kind == "float" and len(wire) == 2:
            value = float.fromhex(wire[1])
        elif kind == "decimal" and len(wire) == 4:
            value = Decimal((wire[1], tuple(wire[2]), wire[3]))
        elif kind == "datetime" and len(wire) == 3:
            value = datetime.fromisoformat(wire[1]).replace(fold=wire[2])
        elif kind == "uuid" and len(wire) == 2:
            value = UUID(bytes=bytes.fromhex(wire[1]))
        elif kind == "bytes" and len(wire) == 2:
            value = bytes.fromhex(wire[1])
        elif kind == "NoneType" and wire == ["NoneType", None]:
            value = None
        elif kind in ("int", "bool", "str") and len(wire) == 2:
            value = wire[1]
        else:
            raise JobStoreError("CHUNK_COORDINATE")
    except (TypeError, ValueError, IndexError, OverflowError):
        raise JobStoreError("CHUNK_COORDINATE") from None
    if type(wire) is not list or coordinate_wire(value) != wire:
        raise JobStoreError("CHUNK_COORDINATE")
    return value


def encode_chunk(descriptor: dict, frame: bytes) -> tuple[str, bytes]:
    if set(descriptor) != FIELDS - {"format", "frame_bytes", "frame_sha256"}:
        raise JobStoreError("CHUNK_FORMAT")
    if len(frame) > MAX_FRAME_BYTES:
        raise JobStoreError("CHUNK_LIMIT")
    text = canonical(
        {
            **descriptor,
            "format": FORMAT,
            "frame_bytes": len(frame),
            "frame_sha256": hashlib.sha256(frame).hexdigest(),
        }
    )
    raw = text.encode("ascii")
    if len(raw) > MAX_DESCRIPTOR_BYTES:
        raise JobStoreError("CHUNK_LIMIT")
    body = raw + frame
    header = HEADER.pack(MAGIC, len(raw), len(frame), hashlib.sha256(body).digest())
    return text, header + body


def decode_chunk(data: bytes) -> tuple[str, dict, bytes]:
    """Outer frame, canonical descriptor and frame correspondence; no values decoded."""
    if type(data) is not bytes or len(data) < HEADER.size:
        raise JobStoreError("CHUNK_FORMAT")
    magic, size, frame_size, digest = HEADER.unpack_from(data)
    if (
        magic != MAGIC
        or size > MAX_DESCRIPTOR_BYTES
        or frame_size > MAX_FRAME_BYTES
        or HEADER.size + size + frame_size != len(data)
    ):
        raise JobStoreError("CHUNK_FORMAT")
    body = memoryview(data)[HEADER.size :]
    if hashlib.sha256(body).digest() != digest:
        raise JobStoreError("CHUNK_FORMAT")
    try:
        text = bytes(body[:size]).decode("ascii")
        descriptor = json.loads(text, object_pairs_hook=_unique)
    except (UnicodeError, ValueError, RecursionError) as error:
        if type(error) is JobStoreError:
            raise
        raise JobStoreError("CHUNK_FORMAT") from None
    frame = bytes(body[size:])
    if (
        type(descriptor) is not dict
        or set(descriptor) != FIELDS
        or canonical(descriptor) != text
        or descriptor["format"] != FORMAT
        or descriptor["frame_bytes"] != len(frame)
        or descriptor["frame_sha256"] != hashlib.sha256(frame).hexdigest()
    ):
        raise JobStoreError("CHUNK_FORMAT")
    return text, descriptor, frame


@dataclass(frozen=True, slots=True)
class FileFacts:
    name: str
    size: int
    digest: str
    device: int
    inode: int
    # Inode numbers are reused at once after unlink; ctime separates a recreation.
    changed: int


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError(errno.EIO, "short write")
        view = view[written:]


def _sync(fd: int) -> None:
    os.fsync(fd)


def _link(staged: str, final: str, staging: int, chunks: int) -> None:
    # link(2) never replaces an existing name: EEXIST is the no-clobber check.
    os.link(staged, final, src_dir_fd=staging, dst_dir_fd=chunks, follow_symlinks=False)


def _unlink(name: str, directory: int) -> None:
    os.unlink(name, dir_fd=directory)


class Lease:
    """One generation's v7 lifetime lock on its stable `locks/<gen>.life` file:
    SHARED around any chunk file use, EXCLUSIVE (never waiting) around a
    collection decision and its deletions. Each lease is its own open file
    description, so leases conflict even inside one process. Private local
    coordination, never authentication; the lock file is never deleted."""

    __slots__ = ("generation", "exclusive", "_fd", "_pid")

    def __init__(self, workspace, generation, *, exclusive=False, wait=MAX_LEASE_WAIT):
        from pietto._project.project_job_workspace import valid_identity

        if not valid_identity(generation, "gen"):
            raise JobStoreError("GENERATION_UNKNOWN")
        if type(wait) not in (int, float) or not 0 <= wait <= MAX_LEASE_WAIT:
            raise JobStoreError("LEASE_WAIT_BOUND")
        locks = workspace.locks_fd()
        name = generation + LEASE
        fd = os.open(
            name,
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
            dir_fd=locks,
        )
        try:
            state = os.fstat(fd)
            if not _private_file(state) or state.st_nlink != 1:
                raise JobStoreError("LEASE_OBJECT")
            mode = (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB
            deadline = time.monotonic() + (0 if exclusive else wait)
            while True:
                try:
                    fcntl.flock(fd, mode)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise JobStoreError("LEASE_BUSY") from None
                    time.sleep(0.01)
            if not _same(
                os.stat(name, dir_fd=locks, follow_symlinks=False),
                (
                    state.st_dev,
                    state.st_ino,
                ),
            ):
                raise JobStoreError("LEASE_OBJECT")
        except BaseException:
            os.close(fd)
            raise
        self.generation, self.exclusive = generation, exclusive
        self._fd, self._pid = fd, os.getpid()

    def __repr__(self) -> str:
        return f"Lease(generation={self.generation!r}, exclusive={self.exclusive})"

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
        return False

    def close(self) -> None:
        """Close this description once; an inherited copy may still hold it."""
        if self._fd >= 0 and self._pid == os.getpid():
            fd, self._fd = self._fd, -1
            os.close(fd)


def _same(state: os.stat_result, identity: tuple[int, int]) -> bool:
    return (state.st_dev, state.st_ino) == identity


def _private_file(state: os.stat_result) -> bool:
    return (
        stat.S_ISREG(state.st_mode)
        and state.st_uid == os.geteuid()
        and not state.st_mode & 0o077
    )


def write_chunk(workspace: Workspace, identity: str, data: bytes) -> FileFacts:
    """Exclusive staging, fsync, no-clobber link, owned unlink, directory fsync."""
    if len(data) > MAX_FILE_BYTES:
        raise JobStoreError("CHUNK_LIMIT")
    admit(workspace, len(data))
    staged, final = identity + STAGED, identity + SUFFIX
    staging = chunks = -1
    created = None
    linked = False
    try:
        staging = workspace.directory(STAGING)
        chunks = workspace.directory(CHUNKS)
        try:
            fd = os.open(
                staged,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                0o600,
                dir_fd=staging,
            )
        except FileExistsError:
            raise JobStoreError("CHUNK_COLLISION") from None
        try:
            state = os.fstat(fd)
            created = (state.st_dev, state.st_ino)
            if not _private_file(state) or state.st_nlink != 1:
                raise JobStoreError("CHUNK_OBJECT")
            _write_all(fd, data)
            _sync(fd)
        finally:
            os.close(fd)
        try:
            _link(staged, final, staging, chunks)
        except FileExistsError:
            raise JobStoreError("CHUNK_COLLISION") from None
        linked = True
        if _same(os.stat(staged, dir_fd=staging, follow_symlinks=False), created):
            os.unlink(staged, dir_fd=staging)
        state = os.stat(final, dir_fd=chunks, follow_symlinks=False)
        if (
            not _same(state, created)
            or not _private_file(state)
            or state.st_nlink != 1
            or state.st_size != len(data)
        ):
            raise JobStoreError("CHUNK_OBJECT")
        _sync(chunks)
        _sync(staging)
        return FileFacts(
            final,
            len(data),
            hashlib.sha256(data).hexdigest(),
            *created,
            state.st_ctime_ns,
        )
    except BaseException as primary:
        # Only this call's own staging name is removed (inode-checked); a
        # linked final file stays as an unreferenced orphan, never deleted.
        if created is not None and staging >= 0:
            try:
                if _same(
                    os.stat(staged, dir_fd=staging, follow_symlinks=False), created
                ):
                    os.unlink(staged, dir_fd=staging)
            except OSError:
                pass
        if isinstance(primary, OSError):
            raise JobStoreError("CHUNK_ORPHANED_IO" if linked else "CHUNK_IO") from None
        raise
    finally:
        for fd in (staging, chunks):
            if fd >= 0:
                os.close(fd)


def file_identity(chunks: int, facts) -> None:
    """Cheap object check (no content read) of a staged or committed final name."""
    try:
        state = os.stat(facts.name, dir_fd=chunks, follow_symlinks=False)
    except FileNotFoundError:
        raise JobStoreError("CHUNK_MISSING") from None
    if (
        not _same(state, (facts.device, facts.inode))
        or state.st_ctime_ns != facts.changed
        or not _private_file(state)
        or state.st_nlink != 1
        or state.st_size != facts.size
    ):
        raise JobStoreError("CHUNK_OBJECT")


def read_chunk_file(chunks: int, name: str, size: int, digest: str) -> bytes:
    """Bounded before allocation; the exact committed size and digest are required."""
    if (
        type(name) is not str
        or "/" in name
        or not name.endswith(SUFFIX)
        or type(size) is not int
        or not HEADER.size <= size <= MAX_FILE_BYTES
    ):
        raise JobStoreError("CHUNK_OBJECT")
    try:
        fd = os.open(
            name,
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
            dir_fd=chunks,
        )
    except FileNotFoundError:
        raise JobStoreError("CHUNK_MISSING") from None
    except OSError:
        raise JobStoreError("CHUNK_OBJECT") from None
    try:
        state = os.fstat(fd)
        if not _private_file(state) or state.st_nlink != 1:
            raise JobStoreError("CHUNK_OBJECT")
        if state.st_size != size:
            raise JobStoreError("CHUNK_SIZE")
        parts, remaining = [], size
        while remaining:
            part = os.read(fd, min(remaining, 1 << 20))
            if not part:
                raise JobStoreError("CHUNK_SIZE")
            parts.append(part)
            remaining -= len(part)
        if os.read(fd, 1):
            raise JobStoreError("CHUNK_SIZE")
    except OSError:
        raise JobStoreError("CHUNK_IO") from None
    finally:
        os.close(fd)
    data = b"".join(parts)
    if hashlib.sha256(data).hexdigest() != digest:
        raise JobStoreError("CHUNK_DIGEST")
    return data


def list_names(workspace: Workspace, directory: str) -> tuple[tuple[str, str], ...]:
    """Names and object kinds only; nothing is opened, adopted or removed."""
    fd = workspace.directory(directory)
    try:
        with os.scandir(fd) as entries:
            return tuple(
                sorted(
                    (
                        entry.name,
                        "file"
                        if _private_file(entry.stat(follow_symlinks=False))
                        else "foreign",
                    )
                    for entry in entries
                )
            )
    finally:
        os.close(fd)
