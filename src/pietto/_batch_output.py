"""Batch directory publication that never replaces an existing name.

Linux pins every directory by descriptor. Windows writes by path into new
owner-only directories that it holds open without delete sharing, so they
cannot be renamed or removed while it writes; their ancestors are resolved by
path.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
import ctypes
import errno
import os
from pathlib import Path
import secrets
import stat
import struct
import sys

__all__: tuple[str, ...] = ()


class UnsupportedPlatform(OSError):
    pass


def supported() -> bool:
    # From 3.12.4 os.mkdir(path, 0o700) gives a Windows directory an owner-only
    # protected DACL; before it the directory inherits its parent's.
    windows = sys.platform == "win32" and sys.version_info >= (3, 12, 4)
    return windows or _descriptors_supported()


def _descriptors_supported() -> bool:
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
    if sys.platform == "win32":
        # os.rename raises FileExistsError on Windows instead of replacing.
        _publish_by_path(
            output,
            artifacts,
            manifest,
            inputs_current,
            _pin_directory,
            os.rename,
            _remove_directory,
        )
        return
    if not _descriptors_supported():
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


if sys.platform == "win32":
    import msvcrt

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _kernel32.CreateFileW.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    _kernel32.CreateFileW.restype = ctypes.c_void_p
    _kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    _kernel32.SetFileInformationByHandle.argtypes = (
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_uint32,
    )
    _kernel32.SetFileInformationByHandle.restype = ctypes.c_int

    def _open_directory(path: Path, access: int) -> int:
        """A descriptor of path itself, never of a reparse point's target.

        The handle shares reading and writing but not deletion, so while it
        is open nobody can rename or remove the directory. Its file or delete
        access right makes it take part in that sharing check.
        """

        handle = _kernel32.CreateFileW(
            os.fspath(path),
            access | 0x0080,  # FILE_READ_ATTRIBUTES
            0x0001 | 0x0002,  # FILE_SHARE_READ | FILE_SHARE_WRITE
            None,
            3,  # OPEN_EXISTING
            0x0200_0000 | 0x0020_0000,  # BACKUP_SEMANTICS | OPEN_REPARSE_POINT
            None,
        )
        if handle is None or handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return msvcrt.open_osfhandle(handle, os.O_RDONLY)
        except BaseException:
            _kernel32.CloseHandle(handle)
            raise

    def _pin_directory(path: Path) -> int:
        return _open_directory(path, 0x0001)  # FILE_LIST_DIRECTORY

    def _remove_directory(path: Path, identity: tuple[int, int]) -> None:
        """Remove the empty directory at path only while it is ``identity``.

        The removal goes through the handle whose identity was checked, so a
        directory put in its place is never removed.
        """

        descriptor = _open_directory(path, 0x0001_0000)  # DELETE
        try:
            state = os.fstat(descriptor)
            if not _plain_directory(state) or _identity(state) != identity:
                raise OSError("batch directory changed")
            remove = ctypes.c_ubyte(1)  # FILE_DISPOSITION_INFO: removed on close
            if not _kernel32.SetFileInformationByHandle(
                msvcrt.get_osfhandle(descriptor), 4, ctypes.byref(remove), 1
            ):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            _close(descriptor)


def _plain_directory(state: os.stat_result) -> bool:
    attributes = getattr(state, "st_file_attributes", 0)
    return stat.S_ISDIR(state.st_mode) and not (
        attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def _path_file_identity(state: os.stat_result) -> tuple[int, int, int, int]:
    # Windows ctime differs between path and descriptor stat, and a written
    # file's modification time can change when it is closed: take it by path.
    return state.st_dev, state.st_ino, state.st_size, state.st_mtime_ns


def _installed_file(path: Path) -> tuple[int, int, int, int]:
    state = os.lstat(path)
    if not stat.S_ISREG(state.st_mode) or state.st_nlink != 1:
        raise OSError("batch file identity changed")
    return _path_file_identity(state)


def _matches_path(path: Path, identity: tuple[int, int, int, int], data: bytes) -> bool:
    if _installed_file(path) != identity:
        return False
    with open(path, "rb") as handle:
        if (
            _identity(os.fstat(handle.fileno())) != identity[:2]
            or handle.read(len(data) + 1) != data
        ):
            return False
    return _installed_file(path) == identity


def _publish_by_path(
    output: Path,
    artifacts: Iterable[bytes],
    manifest: bytes,
    inputs_current: Callable[[], bool],
    pin: Callable[[Path], int],
    rename: Callable[[Path, Path], None],
    remove: Callable[[Path, tuple[int, int]], None],
) -> None:
    """Publish by path; ``rename`` must refuse an existing target.

    Each new owner-only directory is held by ``pin`` and checked against its
    path before every step. Each file is created exclusively under a
    temporary name, checked again, renamed into place and checked there; the
    manifest is renamed last. On failure only paths whose identity is still
    ours are removed, a directory by ``remove`` once its handle is closed.
    """

    parent = _identity(os.stat(output.parent))
    held: list[tuple[Path, int, tuple[int, int] | None]] = []
    temporary: list[tuple[Path, tuple[int, int]]] = []
    created: list[tuple[Path, tuple[int, int, int, int], bytes]] = []
    published = False

    def new_directory(path: Path) -> None:
        os.mkdir(path, 0o700)
        descriptor = pin(path)
        held.append((path, descriptor, None))
        state, named = os.fstat(descriptor), os.lstat(path)
        if (
            not _plain_directory(state)
            or not _plain_directory(named)
            or _identity(named) != _identity(state)
        ):
            raise OSError("created directory identity changed")
        held[-1] = (path, descriptor, _identity(state))

    def namespace_current() -> None:
        if _identity(os.stat(output.parent)) != parent:
            raise OSError("batch directory parent changed")
        for path, _descriptor, identity in held:
            state = os.lstat(path)
            if not _plain_directory(state) or _identity(state) != identity:
                raise OSError("batch directory namespace changed")

    def write_new(
        path: Path, data: bytes, before_install: Callable[[], None]
    ) -> tuple[int, int, int, int]:
        staged = path.parent / f".pietto-{secrets.token_hex(4)}.tmp"
        with open(staged, "xb") as handle:
            opened = _identity(os.fstat(handle.fileno()))
            temporary.append((staged, opened))
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        identity = _installed_file(staged)
        if identity[:3] != (*opened, len(data)):
            raise OSError("batch file identity changed")
        before_install()
        if not _matches_path(staged, identity, data):
            raise OSError("batch file changed")
        rename(staged, path)
        temporary.pop()
        if _installed_file(path) != identity:
            raise OSError("installed batch file changed")  # a foreign name stays
        return identity

    try:
        new_directory(output)
        new_directory(output / "artifacts")
        for index, data in enumerate(artifacts):
            namespace_current()
            path = output / "artifacts" / f"{index:06d}.json"
            created.append((path, write_new(path, data, namespace_current), data))

        def before_manifest() -> None:
            namespace_current()
            if not inputs_current():
                raise OSError("project inputs changed")
            for path, identity, data in created:
                if not _matches_path(path, identity, data):
                    raise OSError("published artifact changed")

        # The installed and checked manifest is the completion point.
        write_new(output / "manifest.json", manifest, before_manifest)
        published = True
    finally:
        keep = published
        if not keep:
            try:
                for path, opened in temporary:
                    if _identity(os.lstat(path)) == opened:
                        os.unlink(path)
                for path, identity, data in reversed(created):
                    if _matches_path(path, identity, data):
                        os.unlink(path)
            except OSError:
                keep = True  # an ambiguous name keeps every directory
        while held:
            path, descriptor, identity = held.pop()
            _close(descriptor)  # our handle shares no deletion
            if not keep and identity is not None:
                try:
                    remove(path, identity)
                    continue
                except OSError:
                    pass
            keep = True  # a directory left behind keeps its parents
