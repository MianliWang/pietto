"""The temporary file through which both emit-sql writers replace an output file.

Each writer fills the file returned by ``open_replacement`` and installs it
with one ``os.replace``, so the output path only ever holds the old or the new
complete content.
"""

from __future__ import annotations

import contextlib
import os
import secrets
import stat
import sys
from pathlib import Path
from typing import BinaryIO

# O_EXCL never reuses an existing name, so a collision is a reported failure;
# O_BINARY keeps the written bytes, LF line endings included, on Windows.
_CREATE = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)


def is_read_only(output: Path) -> bool:
    """Whether output is an existing regular file the user may not write.

    ``os.access`` asks what an ordinary ``open(output, "w")`` would face: the
    mode bits, ACLs and root on POSIX, the read-only attribute on Windows.
    """

    return _replaced_mode(output) is not None and not os.access(output, os.W_OK)


def open_replacement(output: Path) -> tuple[BinaryIO, Path]:
    """Create the hidden same-directory temporary file that will replace output.

    The short ``.pietto-*.tmp`` name keeps every output name the file system
    accepts writable. A new output gets the mode ``open(output, "w")`` gives:
    the operating system applies the process umask to 0o666, so the umask is
    never read or changed. A replaced regular file keeps its read, write and
    execute bits: the temporary file is created with them, which the umask can
    only narrow, so it is never more open than the file it replaces, and then
    receives them exactly where the file system stores them. Ownership and the
    set-id and sticky bits are not copied. Windows keeps only a read-only
    attribute, which a writable target never has, so there both files are
    ordinary writable files.
    """

    mode = _replaced_mode(output)
    temporary = output.parent / f".pietto-{secrets.token_hex(4)}.tmp"
    handle = open(os.open(temporary, _CREATE, 0o666 if mode is None else mode), "wb")
    if mode is not None and sys.platform != "win32":
        # A file system without permission bits (FAT, some shares) refuses;
        # the umask-narrowed mode then stands.
        with contextlib.suppress(OSError):
            os.fchmod(handle.fileno(), mode)
    return handle, temporary


def _replaced_mode(output: Path) -> int | None:
    """The permission bits of an existing regular output, else None."""

    try:
        state = os.stat(output)
    except OSError:
        return None
    if not stat.S_ISREG(state.st_mode):
        return None
    return stat.S_IMODE(state.st_mode) & 0o777
