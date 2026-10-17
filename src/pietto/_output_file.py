"""The temporary file through which both emit-sql writers replace an output file.

Each writer fills the file returned by ``open_replacement`` and installs it
with one ``os.replace``, so the output path only ever holds the old or the new
complete content.
"""

from __future__ import annotations

import contextlib
import errno
import os
import secrets
import stat
import sys
from pathlib import Path
from typing import BinaryIO


def is_read_only(output: Path) -> bool:
    """Whether output is an existing regular file the user may not write.

    ``os.access`` asks what an ordinary ``open(output, "w")`` would face: the
    mode bits, ACLs and root on POSIX, the read-only attribute on Windows.
    ``OSError`` when the state of output cannot be read.
    """

    replaced = _replaced(output)
    return (
        replaced is not None
        and stat.S_ISREG(replaced.st_mode)
        and not os.access(output, os.W_OK)
    )


def is_owned_by_another_user(output: Path) -> bool:
    """Whether output exists and is not shown to belong to this process's user.

    The replacement would belong to this process's user, and the owner bits
    it keeps would then grant that user access the original did not, so such
    an output is not replaced. Root may replace any output, since it already
    reads and writes every file, but an owner shown as the overflow id is
    unknown, not root's: root of a user namespace has no power over a file
    whose owner the namespace does not map. When Linux does not tell which id
    that is, root replaces only its own outputs. Windows has no POSIX owner
    to compare. ``OSError`` when the state of output cannot be read.
    """

    if sys.platform == "win32":
        return False
    replaced = _replaced(output)
    if replaced is None:
        return False
    user = os.geteuid()
    overflow = _overflow_id("uid")
    if replaced.st_uid == user:
        return replaced.st_uid == overflow
    return user != 0 or overflow is None or replaced.st_uid == overflow


def open_replacement(output: Path) -> tuple[BinaryIO, Path]:
    """Create the hidden same-directory temporary file that will replace output.

    The short ``.pietto-*.tmp`` name keeps every output name the file system
    accepts writable. Mode ``x`` never reuses an existing name, so a collision
    is a reported failure, and binary mode keeps the written bytes, LF line
    endings included, on Windows. A new output gets the mode
    ``open(output, "w")`` gives (0o666 less the umask, or what a default ACL
    of the directory grants), which the operating system applies, so the
    umask is never read or changed.

    Whatever the output path holds other than a directory (a regular file, a
    FIFO or a socket, which both callers refuse beforehand unless one appears
    in between) is replaced, and its permission bits bound the new
    file's: all of a regular file's read, write and execute bits, but only the
    owner's read and write bits of anything else. The temporary file is
    created with only the owner's share of that bound, which the umask or an
    inherited default ACL can only narrow, so a file system that refuses
    ``fchmod`` leaves it at most that open. It then receives the whole bound
    where ``_same_access`` holds, otherwise the owner's share alone.
    Ownership, the set-id and sticky bits and the replaced object's own ACL
    are not copied: like any new file, the replacement gets only the ACL its
    directory hands every new file. Windows keeps only a read-only attribute,
    which a writable target never has, so there both files are ordinary
    writable files.

    Each ``OSError`` raised here comes before the file exists, so the caller
    reports every failure and owns every removal: an audit hook sees both
    ``open`` events before the file is created. The steps after it can only
    narrow the file, so any exception they raise leaves it at its creation
    mode or the owner bits instead of escaping. Only an interruption between
    creation and return closes and removes the file here.
    """

    replaced = _replaced(output)
    temporary = output.parent / f".pietto-{secrets.token_hex(4)}.tmp"
    bound = 0
    if replaced is not None:
        bound = replaced.st_mode & (0o777 if stat.S_ISREG(replaced.st_mode) else 0o600)
    creation = 0o666 if replaced is None else bound & 0o700
    handle = open(
        temporary, "xb", opener=lambda path, flags: os.open(path, flags, creation)
    )
    try:
        if replaced is not None and sys.platform != "win32":
            descriptor = handle.fileno()
            same = _same_access(replaced, output, descriptor)
            # A file system without permission bits (FAT, some shares) or an
            # audit hook refuses; the owner-only creation mode then stands.
            with contextlib.suppress(Exception):
                os.fchmod(descriptor, bound & (0o777 if same else 0o700))
    except BaseException:
        with contextlib.suppress(OSError):
            handle.close()
        with contextlib.suppress(OSError):
            os.unlink(temporary)
        raise
    return handle, temporary


def _same_access(replaced: os.stat_result, output: Path, descriptor: int) -> bool:
    """Whether the replaced bits grant on the new file exactly what they did.

    Only on Linux, and only when both have the same owner and group and
    neither carries an ACL, under which the group bits are a mask and named
    entries can deny what the bits allow. An owner or group shown as the
    overflow id is unknown: a user namespace shows every id it does not map
    as that one id, and when Linux does not tell which id that is, no owner
    or group is known. Whatever cannot be read, for any reason, counts as
    different.
    """

    if sys.platform != "linux":
        return False
    try:
        created = os.fstat(descriptor)
        overflow_user = _overflow_id("uid")
        overflow_group = _overflow_id("gid")
        return (
            (created.st_uid, created.st_gid) == (replaced.st_uid, replaced.st_gid)
            and overflow_user is not None
            and overflow_group is not None
            and replaced.st_uid != overflow_user
            and replaced.st_gid != overflow_group
            and not _has_acl(output)
            and not _has_acl(descriptor)
        )
    except Exception:
        return False


def _has_acl(target: Path | int) -> bool:
    """Whether target carries an ACL; OSError when that cannot be told.

    Linux lists POSIX and NFSv4 ACLs as ``system.`` attributes. A CIFS client
    lists only the server's own attributes, so its security descriptor is
    asked for by name.
    """

    if any(name.startswith("system.") for name in os.listxattr(target)):
        return True
    try:
        os.getxattr(target, "system.cifs_acl")
    except OSError as error:
        if error.errno in {errno.ENODATA, errno.EOPNOTSUPP}:
            return False
        raise
    return True


def _overflow_id(kind: str) -> int | None:
    """The id Linux shows for a user ("uid") or group ("gid") it cannot map.

    The kernel's own setting; None on Linux when it cannot be read, since the
    setting need not be its default; -1, which no file shows, elsewhere.
    """

    if sys.platform != "linux":
        return -1
    try:
        return int(Path(f"/proc/sys/kernel/overflow{kind}").read_text("ascii"))
    except (OSError, ValueError):
        return None


def _replaced(output: Path) -> os.stat_result | None:
    """The state of what output names, unless it is absent or a directory.

    Only a missing entry or a parent that is not a directory shows output
    absent; any other failure to read its state raises ``OSError``, so an
    output that cannot be inspected is never treated as a new file.
    """

    try:
        state = os.stat(output)
    except (FileNotFoundError, NotADirectoryError):
        return None
    return None if stat.S_ISDIR(state.st_mode) else state
