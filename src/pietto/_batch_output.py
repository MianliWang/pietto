"""Linux-owned batch directory publication; no replacement of existing names."""

from __future__ import annotations

from collections.abc import Callable, Iterable
import ctypes
import errno
import os
from pathlib import Path
import stat
import struct
import sys

__all__: tuple[str, ...] = ()


class UnsupportedPlatform(OSError):
    pass


def supported() -> bool:
    return (
        sys.platform == "linux"
        and all(
            hasattr(os, name)
            for name in ("O_DIRECTORY", "O_NOFOLLOW", "O_CLOEXEC", "O_TMPFILE")
        )
        and all(
            function in os.supports_dir_fd
            for function in (os.open, os.stat, os.mkdir, os.link, os.unlink, os.rmdir)
        )
        and os.link in os.supports_follow_symlinks
        and Path("/proc/self/fd").is_dir()
    )


def _close(fd: int) -> None:
    if fd >= 0:
        try:
            os.close(fd)
        except OSError:
            # Linux releases a valid descriptor even when close reports an error.
            pass


def _identity(state: os.stat_result) -> tuple[int, int]:
    return state.st_dev, state.st_ino


def _named_identity(parent: int, name: str) -> tuple[int, int]:
    return _identity(os.stat(name, dir_fd=parent, follow_symlinks=False))


def _anonymous(directory: int) -> int:
    try:
        return os.open(
            ".", os.O_WRONLY | os.O_TMPFILE | os.O_CLOEXEC, 0o600, dir_fd=directory
        )
    except OSError as error:
        if error.errno in (errno.EOPNOTSUPP, errno.ENOSYS, errno.EINVAL):
            raise UnsupportedPlatform(
                "anonymous file publication unavailable"
            ) from None
        raise


def _creation_watch(parent: int) -> int:
    # mkdir has no atomic create-and-open form; queued namespace events close
    # the interval before we can pin its resulting directory descriptor.
    library = ctypes.CDLL(None, use_errno=True)
    try:
        initialize, watch = library.inotify_init1, library.inotify_add_watch
    except AttributeError:
        raise UnsupportedPlatform(
            "directory creation observation unavailable"
        ) from None
    initialize.argtypes, initialize.restype = [ctypes.c_int], ctypes.c_int
    watch.argtypes, watch.restype = (
        [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32],
        ctypes.c_int,
    )
    fd = initialize(os.O_NONBLOCK | os.O_CLOEXEC)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "directory observation failed")
    mask = 0x4 | 0x40 | 0x80 | 0x100 | 0x200 | 0x400 | 0x800
    if watch(fd, f"/proc/self/fd/{parent}".encode("ascii"), mask) < 0:
        code = ctypes.get_errno()
        _close(fd)
        raise OSError(code, "directory observation failed")
    return fd


def _verify_creation(watch: int, name: str) -> None:
    created = 0
    wanted = os.fsencode(name)
    for _ in range(16):
        try:
            data = os.read(watch, 65536)
        except BlockingIOError:
            if created != 1:
                raise OSError("directory creation identity unavailable") from None
            return
        offset = 0
        while offset < len(data):
            if len(data) - offset < 16:
                raise OSError("directory event truncated")
            _watch, mask, _cookie, size = struct.unpack_from("iIII", data, offset)
            offset += 16
            if size > len(data) - offset or mask & (0x400 | 0x800 | 0x4000 | 0x8000):
                raise OSError("directory event identity changed")
            entry = data[offset : offset + size].rstrip(b"\0")
            offset += size
            if entry == wanted:
                if mask != 0x100 | 0x40000000:
                    raise OSError("created directory was replaced")
                created += 1
    raise OSError("directory event limit exceeded")


def _new_directory(parent: int, name: str) -> int:
    watch, descriptor = _creation_watch(parent), -1
    try:
        os.mkdir(name, 0o700, dir_fd=parent)
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        descriptor = os.open(
            name,
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=parent,
        )
        observed = os.fstat(descriptor)
        _verify_creation(watch, name)
        if (
            not stat.S_ISDIR(observed.st_mode)
            or observed.st_uid != os.geteuid()
            or observed.st_mode & 0o077
            or _identity(before) != _identity(observed)
            or _named_identity(parent, name) != _identity(observed)
        ):
            raise OSError("created directory identity changed")
        result, descriptor = descriptor, -1
        return result
    finally:
        _close(descriptor)
        _close(watch)


def _file_identity(state: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        state.st_dev,
        state.st_ino,
        state.st_ctime_ns,
        state.st_mtime_ns,
        state.st_size,
    )


def _write_new(
    directory: int,
    name: str,
    data: bytes,
    before_install: Callable[[], None],
    *,
    manifest: bool = False,
) -> tuple[int, int, int, int, int]:
    descriptor = _anonymous(directory)
    try:
        remaining = memoryview(data)
        while remaining:
            size = os.write(descriptor, remaining)
            if size <= 0:
                raise OSError(errno.EIO, "short batch file write")
            remaining = remaining[size:]
        os.fsync(descriptor)
        state = os.fstat(descriptor)
        if (
            not stat.S_ISREG(state.st_mode)
            or state.st_nlink != 0
            or state.st_size != len(data)
        ):
            raise OSError("batch file identity changed")
        identity = _file_identity(state)
        before_install()
        # The source is the opened inode, not a replaceable staging pathname.
        # linkat creates the final name atomically and fails on EEXIST.
        os.link(
            f"/proc/self/fd/{descriptor}",
            name,
            dst_dir_fd=directory,
            follow_symlinks=True,
        )
        if not manifest:
            installed = os.fstat(descriptor)
            if (
                _identity(installed) != _identity(state)
                or installed.st_nlink != 1
                or installed.st_uid != os.geteuid()
                or installed.st_mode & 0o077
                or installed.st_size != state.st_size
                or installed.st_mtime_ns != state.st_mtime_ns
                or _named_identity(directory, name) != _identity(state)
            ):
                raise OSError("installed batch file changed")
            identity = _file_identity(installed)
        return identity
    finally:
        _close(descriptor)


def _matches_file(directory, name, identity, data):
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK,
        dir_fd=directory,
    )
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or before.st_mode & 0o077
            or before.st_nlink != 1
            or _file_identity(before) != identity
        ):
            return False
        offset = 0
        view = memoryview(data)
        while offset < len(data):
            chunk = os.read(descriptor, min(65536, len(data) - offset))
            if not chunk or chunk != view[offset : offset + len(chunk)]:
                return False
            offset += len(chunk)
        if os.read(descriptor, 1):
            return False
        after = os.fstat(descriptor)
        return (
            _file_identity(after) == identity
            and (after.st_mode, after.st_uid, after.st_nlink)
            == (before.st_mode, before.st_uid, 1)
            and _named_identity(directory, name) == identity[:2]
        )
    finally:
        _close(descriptor)


def publish(
    output: Path,
    artifacts: Iterable[bytes],
    manifest: bytes,
    inputs_current: Callable[[], bool],
) -> None:
    if not supported():
        raise UnsupportedPlatform("safe batch directory output unavailable")
    parent = root = children = -1
    published = False
    created: list[tuple[str, tuple[int, int, int, int, int], bytes]] = []
    root_id = children_id = None
    try:
        parent = os.open(
            output.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        parent_state = os.fstat(parent)
        # Check filesystem support before creating any named directory.
        probe = _anonymous(parent)
        _close(probe)
        root = _new_directory(parent, output.name)
        root_id = _identity(os.fstat(root))
        children = _new_directory(root, "artifacts")
        children_id = _identity(os.fstat(children))

        def namespace_current() -> None:
            if (
                _identity(os.stat(output.parent)) != _identity(parent_state)
                or _named_identity(parent, output.name) != root_id
                or _named_identity(root, "artifacts") != children_id
            ):
                raise OSError("batch directory namespace changed")

        for index, data in enumerate(artifacts):
            namespace_current()
            name = f"{index:06d}.json"
            created.append(
                (name, _write_new(children, name, data, namespace_current), data)
            )

        def before_manifest() -> None:
            namespace_current()
            if not inputs_current():
                raise OSError("project inputs changed")
            for name, identity, data in created:
                # Filesystems may give successive writes the same timestamp.
                if not _matches_file(children, name, identity, data):
                    raise OSError("published artifact changed")

        _write_new(root, "manifest.json", manifest, before_manifest, manifest=True)
        published = True
    finally:
        if not published and root >= 0:
            try:
                # Ambiguous namespaces are left incomplete; never recurse into a
                # replacement. Root removal also needs an exclusively owned parent.
                if _named_identity(parent, output.name) == root_id:
                    if (
                        children >= 0
                        and _named_identity(root, "artifacts") == children_id
                    ):
                        for name, identity, data in reversed(created):
                            if _matches_file(children, name, identity, data):
                                os.unlink(name, dir_fd=children)
                        os.rmdir("artifacts", dir_fd=root)
                    owner = os.fstat(parent)
                    if owner.st_uid == os.geteuid() and not owner.st_mode & 0o022:
                        if _named_identity(parent, output.name) == root_id:
                            os.rmdir(output.name, dir_fd=parent)
            except OSError:
                pass
        for descriptor in (children, root, parent):
            _close(descriptor)
