from __future__ import annotations

import errno
import json
import os
import stat
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import pietto._output_file as output_file
import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.sql import SqlResult

SOURCE = (
    "shape User:\n"
    "    email: Text not null\n"
    'source users: User is postgres.table("users")\n'
    "table user_emails:\n"
    "    from users\n"
    "    select:\n"
    "        email\n"
)


def test_output_same_as_input_is_rejected_without_truncation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "same-file.pietto", SOURCE)
    original = path.read_bytes()

    assert _emit(path, path) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "output path must differ from the input file" in captured.err
    assert path.read_bytes() == original


def test_hard_link_to_input_is_rejected_without_truncation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = tmp_path / "hard-link.pietto"
    os.link(path, output)
    original = path.read_bytes()

    assert _emit(path, output) == 2

    assert "output path must differ from the input file" in capsys.readouterr().err
    assert path.read_bytes() == original
    assert output.read_bytes() == original


def test_symlink_output_is_rejected_and_target_is_unchanged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    target = _write(tmp_path, "target.sql", "original SQL\n")
    output = tmp_path / "output.sql"
    output.symlink_to(target)

    assert _emit(path, output) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "output path must not be a symbolic link" in captured.err
    assert output.is_symlink()
    assert target.read_text(encoding="utf-8") == "original SQL\n"


def test_successful_output_atomically_overwrites_regular_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "stale SQL\n")

    assert _emit(path, output) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert output.read_text(encoding="utf-8") == (
        'SELECT\n    "email" AS "email"\nFROM "users"\n'
    )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX permission bits")
def test_new_output_file_mode_follows_the_umask(tmp_path: Path) -> None:
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    for umask, expected in ((0o022, 0o644), (0o077, 0o600)):
        output = tmp_path / f"new-{umask:03o}.sql"
        previous = os.umask(umask)
        try:
            assert _emit(path, output) == 0
        finally:
            os.umask(previous)
        assert stat.S_IMODE(output.stat().st_mode) == expected, oct(umask)
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX permission bits")
def test_replaced_output_file_keeps_its_permission_bits(tmp_path: Path) -> None:
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    # Neither narrowed by the umask nor widened to it; elsewhere than on Linux
    # only the owner bits are kept.
    for mode, umask in ((0o664, 0o077), (0o600, 0o022)):
        output = _write(tmp_path, f"kept-{mode:03o}.sql", "stale SQL\n")
        output.chmod(mode)
        previous = os.umask(umask)
        try:
            assert _emit(path, output) == 0
        finally:
            os.umask(previous)
        kept = mode if sys.platform == "linux" else mode & 0o700
        assert stat.S_IMODE(output.stat().st_mode) == kept, oct(mode)
        assert output.read_text(encoding="utf-8") == (
            'SELECT\n    "email" AS "email"\nFROM "users"\n'
        )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX permission bits")
@pytest.mark.parametrize("carrier", ["replaced", "temporary"])
@pytest.mark.parametrize("acl", ["none", "listed", "unlisted", "unlistable", "unknown"])
def test_only_a_pair_shown_free_of_acls_keeps_more_than_the_owner_bits(
    carrier: str, acl: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "stale SQL\n")
    output.chmod(0o764)
    # The replaced file is asked by path, the temporary file by descriptor. A
    # POSIX ACL is listed; a CIFS security descriptor is only read by name.
    probed = Path if carrier == "replaced" else int

    def listxattr(target: Path | int) -> list[str]:
        if isinstance(target, probed) and acl == "unlistable":
            raise OSError(errno.EIO, "attributes could not be listed")
        if isinstance(target, probed) and acl == "listed":
            return ["user.note", "system.posix_acl_access"]
        return ["user.note"]

    def getxattr(target: Path | int, name: str) -> bytes:
        assert name == "system.cifs_acl"
        if isinstance(target, probed) and acl == "unlisted":
            return b"security descriptor"
        if isinstance(target, probed) and acl == "unknown":
            raise OSError(errno.EIO, "attribute could not be read")
        raise OSError(errno.ENODATA, "no such attribute")

    monkeypatch.setattr(os, "listxattr", listxattr, raising=False)
    monkeypatch.setattr(os, "getxattr", getxattr, raising=False)

    assert _emit(path, output) == 0

    kept = 0o764 if acl == "none" and sys.platform == "linux" else 0o700
    assert stat.S_IMODE(output.stat().st_mode) == kept
    assert output.read_text(encoding="utf-8") == (
        'SELECT\n    "email" AS "email"\nFROM "users"\n'
    )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform != "linux", reason="needs Linux POSIX ACL xattrs")
@pytest.mark.parametrize("acl", ["access", "default"])
def test_a_real_posix_acl_never_widens_a_replaced_file(
    acl: str, tmp_path: Path
) -> None:
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    directory = tmp_path / "out"
    directory.mkdir()
    output = _write(directory, "output.sql", "stale SQL\n")
    output.chmod(0o640)
    if acl == "access":
        # The owning group is denied; stat shows the mask as its read bit.
        target, name = output, "system.posix_acl_access"
        entries = [(1, 6, _NO_ID), (4, 0, _NO_ID), (16, 4, _NO_ID)]
    else:
        # New files here would let nobody read and write.
        target, name = directory, "system.posix_acl_default"
        entries = [(1, 6, _NO_ID), (2, 6, _NOBODY), (4, 4, _NO_ID), (16, 6, _NO_ID)]
    try:
        os.setxattr(target, name, _posix_acl([*entries, (32, 0, _NO_ID)]))
    except OSError as error:
        if error.errno in {errno.ENOTSUP, errno.EOPNOTSUPP}:
            pytest.skip("the file system under tmp_path stores no POSIX ACLs")
        if acl == "default" and error.errno == errno.EINVAL:
            # The access case shows the encoding is accepted here, so only the
            # named user is refused: a user namespace that does not map it.
            pytest.skip("this user namespace does not map the user nobody")
        raise
    assert stat.S_IMODE(output.stat().st_mode) == 0o640

    assert _emit(path, output) == 0

    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    # A replacement carries only the ACL its directory hands every new file,
    # and the cleared group bits are its mask: nobody and the group get none.
    assert _posix_acl_entries(output) == (
        None
        if acl == "access"
        else [
            (1, 6, _NO_ID),
            (2, 6, _NOBODY),
            (4, 4, _NO_ID),
            (16, 0, _NO_ID),
            (32, 0, _NO_ID),
        ]
    )
    assert output.read_text(encoding="utf-8") == (
        'SELECT\n    "email" AS "email"\nFROM "users"\n'
    )
    assert not tuple(directory.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX groups")
@pytest.mark.parametrize("changed", ["replaced", "directory"])
def test_a_replacement_in_another_group_keeps_only_the_owner_bits(
    changed: str, tmp_path: Path
) -> None:
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    directory = tmp_path / "out"
    directory.mkdir()
    output = _write(directory, "output.sql", "stale SQL\n")
    output.chmod(0o664)
    new_gid = output.stat().st_gid
    for other_gid in os.getgroups():
        if other_gid == new_gid:
            continue
        try:
            os.chown(output if changed == "replaced" else directory, -1, other_gid)
        except OSError:
            continue  # A group this user namespace does not map, say.
        break
    else:
        pytest.skip("needs membership in a second group the file system accepts")
    if changed == "directory":
        # A set-group-ID directory gives every new file its own group.
        directory.chmod(0o2775)
    assert stat.S_IMODE(output.stat().st_mode) == 0o664

    assert _emit(path, output) == 0

    state = output.stat()
    assert (stat.S_IMODE(state.st_mode), state.st_gid) == (
        0o600,
        new_gid if changed == "replaced" else other_gid,
    )
    assert not tuple(directory.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX permission bits")
def test_a_refused_fchmod_never_leaves_a_replacement_wider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "stale SQL\n")
    output.chmod(0o764)

    def refuse(descriptor: int, mode: int) -> None:
        raise PermissionError(errno.EPERM, "no permission bits here")

    monkeypatch.setattr(os, "fchmod", refuse)
    previous = os.umask(0)
    try:
        assert _emit(path, output) == 0
    finally:
        os.umask(previous)

    # The creation mode, even with no umask, already holds only the owner bits.
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX permission bits")
@pytest.mark.parametrize("refused", ["fstat", "listxattr", "getxattr", "fchmod"])
def test_any_refused_access_step_keeps_only_the_owner_bits(
    refused: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "stale SQL\n")
    output.chmod(0o764)

    def refuse(*arguments: object) -> None:
        # An audit hook may refuse an event with any exception, not only OSError.
        raise RuntimeError(f"os.{refused} refused")

    monkeypatch.setattr(os, refused, refuse, raising=False)
    previous = os.umask(0)
    try:
        assert _emit(path, output) == 0
    finally:
        os.umask(previous)

    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert output.read_text(encoding="utf-8") == (
        'SELECT\n    "email" AS "email"\nFROM "users"\n'
    )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX FIFOs")
@pytest.mark.parametrize("presentation", ["text", "json"])
def test_a_fifo_output_is_refused_before_compilation(
    presentation: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = tmp_path / "output.sql"
    os.mkfifo(output)
    arguments = ["emit-sql", str(path), "--dialect", "postgres"]
    if presentation == "json":
        arguments += ["--format", "json"]

    assert cli.main([*arguments, "--output", str(output)]) == 2

    message = "output path must be a regular file"
    captured = capsys.readouterr()
    if presentation == "json":
        assert captured.err == ""
        document = json.loads(captured.out)
        assert document["cli_errors"] == [
            {"kind": "output_path", "message": message, "path": str(output)}
        ]
        assert document["output"] == {"path": str(output), "written": False}
    else:
        assert captured.out == ""
        assert captured.err == f"{output}: error: {message}\n"
    assert stat.S_ISFIFO(output.lstat().st_mode)
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX FIFOs")
@pytest.mark.parametrize("mode", [0o600, 0o400, 0o777], ids=oct)
def test_a_fifo_appearing_after_validation_bounds_the_replacement(
    mode: int, tmp_path: Path
) -> None:
    # Both callers refuse a FIFO first; should one appear before the write,
    # the replacement keeps at most its owner's read and write bits.
    _without_inherited_acl(tmp_path)
    output = tmp_path / "output.sql"
    os.mkfifo(output)
    output.chmod(mode)
    previous = os.umask(0o022)
    try:
        handle, temporary = output_file.open_replacement(output)
        with handle:
            handle.write(b"SQL\n")
        os.replace(temporary, output)
    finally:
        os.umask(previous)

    state = output.stat()
    assert (stat.S_ISREG(state.st_mode), stat.S_IMODE(state.st_mode)) == (
        True,
        mode & 0o600,
    )
    assert output.read_bytes() == b"SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX permission bits")
def test_an_interruption_after_creation_closes_and_removes_the_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "stale SQL\n")
    descriptors: list[int] = []

    def interrupt(descriptor: int, mode: int) -> None:
        descriptors.append(descriptor)
        raise KeyboardInterrupt

    monkeypatch.setattr(os, "fchmod", interrupt)

    with pytest.raises(KeyboardInterrupt):
        _emit(path, output)

    assert output.read_text(encoding="utf-8") == "stale SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))
    assert len(descriptors) == 1
    with pytest.raises(OSError) as closed:
        os.fstat(descriptors[0])
    assert closed.value.errno == errno.EBADF


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX owners")
@pytest.mark.parametrize("presentation", ["text", "json"])
def test_another_users_output_is_refused_and_left_unchanged(
    presentation: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")
    owner = output.stat().st_uid
    # The command runs as a user who is neither the file's owner nor root.
    monkeypatch.setattr(os, "geteuid", lambda: owner + 1)
    arguments = ["emit-sql", str(path), "--dialect", "postgres"]
    if presentation == "json":
        arguments += ["--format", "json"]

    assert cli.main([*arguments, "--output", str(output)]) == 2

    message = "output file belongs to another user; the output file was not changed"
    captured = capsys.readouterr()
    if presentation == "json":
        assert captured.err == ""
        document = json.loads(captured.out)
        assert document["cli_errors"] == [
            {"kind": "output_write", "message": message, "path": str(output)}
        ]
        assert document["output"] == {"path": str(output), "written": False}
    else:
        assert captured.out == ""
        assert captured.err == f"{output}: error: {message}\n"
    assert output.read_text(encoding="utf-8") == "original SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX owners")
def test_root_replaces_another_users_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")
    monkeypatch.setattr(os, "geteuid", lambda: 0)

    assert _emit(path, output) == 0

    assert output.read_text(encoding="utf-8") == (
        'SELECT\n    "email" AS "email"\nFROM "users"\n'
    )
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform != "linux", reason="needs the Linux overflow ids")
@pytest.mark.parametrize("caller", ["owner", "root"])
def test_an_unreadable_overflow_id_replaces_no_existing_output(
    caller: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The overflow ids need not be their default, and a user namespace that
    # maps only this user may show both this user and an unmapped owner as
    # that id, so when Linux does not tell it no owner can be shown to be the
    # caller, not even the file's own.
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")
    output.chmod(0o664)
    owner = output.stat().st_uid
    _fake_proc(
        monkeypatch,
        {
            "/proc/self/uid_map": f"0 {owner} 1\n",
            "/proc/self/gid_map": f"0 {output.stat().st_gid} 1\n",
            "/proc/sys/kernel/overflowuid": None,
            "/proc/sys/kernel/overflowgid": None,
        },
    )
    monkeypatch.setattr(os, "geteuid", lambda: owner if caller == "owner" else 0)

    assert _emit(path, output) == 2

    assert output.read_text(encoding="utf-8") == "original SQL\n"
    assert stat.S_IMODE(output.stat().st_mode) == 0o664
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform != "linux", reason="needs the Linux overflow ids")
@pytest.mark.parametrize("kind", ["uid", "gid"])
@pytest.mark.parametrize("ids_map", ["full", "partial", "unreadable"])
def test_the_overflow_id_is_unknown_only_where_ids_are_unmapped(
    ids_map: str,
    kind: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # This user's own output, whose owner or group the kernel's overflow id
    # names. A map covering every id, as the initial user namespace has,
    # leaves no id to show so: the overflow id is an ordinary user or group,
    # such as nobody running the command. Elsewhere, and when the map cannot
    # be read, an owner or group shown as it is unknown.
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")
    output.chmod(0o664)
    state = output.stat()
    ids = {"uid": state.st_uid, "gid": state.st_gid}
    full = "         0          0 4294967295\n"
    _fake_proc(
        monkeypatch,
        {
            f"/proc/self/{kind}_map": {
                "full": full,
                "partial": f"0 {ids[kind]} 1\n",
                "unreadable": None,
            }[ids_map],
            f"/proc/self/{'gid' if kind == 'uid' else 'uid'}_map": full,
            f"/proc/sys/kernel/overflow{kind}": f"{ids[kind]}\n",
        },
    )
    replaced = 'SELECT\n    "email" AS "email"\nFROM "users"\n'

    if ids_map == "full" or kind == "gid":
        assert _emit(path, output) == 0
        assert capsys.readouterr() == ("", "")
        assert output.read_text(encoding="utf-8") == replaced
        # Unknown, the group cannot be shown to grant the same access.
        kept = 0o664 if ids_map == "full" else 0o600
        assert stat.S_IMODE(output.stat().st_mode) == kept
    else:
        # Unknown, the owner cannot be shown to be this user.
        assert _emit(path, output) == 2
        message = "output file belongs to another user; the output file was not changed"
        assert capsys.readouterr() == ("", f"{output}: error: {message}\n")
        assert output.read_text(encoding="utf-8") == "original SQL\n"
        assert stat.S_IMODE(output.stat().st_mode) == 0o664
    if kind == "uid":
        # Root replaces an owner it knows, not one shown as the overflow id.
        output.write_text("original SQL\n", encoding="utf-8")
        monkeypatch.setattr(os, "geteuid", lambda: 0)
        assert _emit(path, output) == (0 if ids_map == "full" else 2)
        expected = replaced if ids_map == "full" else "original SQL\n"
        assert output.read_text(encoding="utf-8") == expected
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.skipif(sys.platform != "linux", reason="needs Linux user namespaces")
@pytest.mark.parametrize("mapped", [True, False], ids=["owner-mapped", "none-mapped"])
def test_ids_a_user_namespace_does_not_map_never_count_as_the_same(
    mapped: bool, tmp_path: Path
) -> None:
    _without_inherited_acl(tmp_path)
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")
    output.chmod(0o660)
    # A fresh user namespace that maps at most this user shows every group,
    # and without the map every user, as the one overflow id, whichever group
    # or user owns the file. The group bits then cannot be shown to grant the
    # same access, and an owner shown so cannot be shown to be this user.
    child = (
        "import os, sys\n"
        "user = os.geteuid()\n"
        "try:\n"
        "    os.unshare(os.CLONE_NEWUSER)\n"
        "    if sys.argv[1] == 'mapped':\n"
        "        with open('/proc/self/uid_map', 'w') as uid_map:\n"
        "            uid_map.write(f'0 {user} 1')\n"
        "except OSError:\n"
        "    sys.exit(77)\n"
        "from pietto.cli import main\n"
        "sys.exit(main(sys.argv[2:]))\n"
    )
    arguments = ["mapped" if mapped else "unmapped"]
    arguments += ["emit-sql", str(path), "--dialect", "postgres"]
    arguments += ["--output", str(output)]
    result = subprocess.run(
        [sys.executable, "-c", child, *arguments],
        # The child imports exactly what this process imports.
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 77:
        pytest.skip("unprivileged user namespaces are unavailable here")

    if mapped:
        assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
        assert output.read_text(encoding="utf-8") == (
            'SELECT\n    "email" AS "email"\nFROM "users"\n'
        )
        assert stat.S_IMODE(output.stat().st_mode) == 0o600
    else:
        message = "output file belongs to another user; the output file was not changed"
        assert (result.returncode, result.stdout, result.stderr) == (
            2,
            "",
            f"{output}: error: {message}\n",
        )
        assert output.read_text(encoding="utf-8") == "original SQL\n"
        assert stat.S_IMODE(output.stat().st_mode) == 0o660
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("presentation", ["text", "json"])
def test_an_output_whose_state_cannot_be_read_is_never_replaced(
    presentation: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")
    before = output.stat()
    real_stat = os.stat

    def stat_failing_for_output(
        target: Any, *arguments: Any, **keywords: Any
    ) -> os.stat_result:
        # Only a missing entry shows an output absent; this one is there.
        if str(target) == str(output):
            raise OSError(errno.EIO, "state could not be read")
        return real_stat(target, *arguments, **keywords)

    monkeypatch.setattr(os, "stat", stat_failing_for_output)
    arguments = ["emit-sql", str(path), "--dialect", "postgres"]
    if presentation == "json":
        arguments += ["--format", "json"]

    assert cli.main([*arguments, "--output", str(output)]) == 2

    message = f"Operating system error (errno {errno.EIO})"
    captured = capsys.readouterr()
    if presentation == "json":
        assert captured.err == ""
        document = json.loads(captured.out)
        assert document["cli_errors"] == [
            {"kind": "output_write", "message": message, "path": str(output)}
        ]
        assert document["output"] == {"path": str(output), "written": False}
    else:
        assert captured == ("", f"{output}: error: {message}\n")
    assert output.read_text(encoding="utf-8") == "original SQL\n"
    after = real_stat(output)
    assert (after.st_mode, after.st_ino) == (before.st_mode, before.st_ino)
    assert not tuple(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("presentation", ["text", "json"])
def test_read_only_output_is_refused_and_left_unchanged(
    presentation: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")
    output.chmod(0o444)
    if os.access(output, os.W_OK):
        pytest.skip("this user may write a read-only file")
    before = output.stat()
    arguments = ["emit-sql", str(path), "--dialect", "postgres"]
    if presentation == "json":
        arguments += ["--format", "json"]

    assert cli.main([*arguments, "--output", str(output)]) == 2

    message = "output file is read-only; the output file was not changed"
    captured = capsys.readouterr()
    if presentation == "json":
        assert captured.err == ""
        document = json.loads(captured.out)
        assert document["cli_errors"] == [
            {"kind": "output_write", "message": message, "path": str(output)}
        ]
        assert document["output"] == {"path": str(output), "written": False}
        assert document["artifacts"] == [
            {
                "kind": "relation",
                "name": "user_emails",
                "sql": 'SELECT\n    "email" AS "email"\nFROM "users"',
            }
        ]
    else:
        assert captured == ("", f"{output}: error: {message}\n")
    assert output.read_text(encoding="utf-8") == "original SQL\n"
    after = output.stat()
    assert (after.st_mode, after.st_ino) == (before.st_mode, before.st_ino)
    assert not tuple(tmp_path.glob("*.tmp"))


def test_atomic_replace_failure_preserves_existing_output_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")

    def fail_replace(source: Path, destination: Path) -> None:
        del source, destination
        raise PermissionError("replacement denied")

    monkeypatch.setattr(cli.os, "replace", fail_replace)

    assert _emit(path, output) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{output}: error: Permission denied\n"
    assert output.read_text(encoding="utf-8") == "original SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))


def test_replace_error_omits_os_text_and_temporary_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")

    def localized_replace(source: Path, destination: Path) -> None:
        # Windows FormatMessage text; winerror 5 is kept only on Windows.
        raise PermissionError(
            errno.EACCES, "拒绝访问。", str(source), 5, str(destination)
        )

    monkeypatch.setattr(cli.os, "replace", localized_replace)

    assert _emit(path, output) == 2

    winerror = ", winerror 5" if sys.platform == "win32" else ""
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"{output}: error: Permission denied (errno 13{winerror})\n"
    )
    assert "拒绝访问" not in captured.err
    assert ".tmp" not in captured.err
    assert output.read_text(encoding="utf-8") == "original SQL\n"


@pytest.mark.parametrize(
    ("error_number", "reason"),
    [
        (errno.ENOSPC, "No space left on device"),
        (errno.EROFS, "Read-only file system"),
        (errno.EIO, "Operating system error"),
    ],
)
def test_write_error_reason_is_fixed_english_text_for_errno(
    error_number: int,
    reason: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = tmp_path / "output.sql"

    def failing_replace(source: Path, destination: Path) -> None:
        raise OSError(
            error_number, "localized text", str(source), None, str(destination)
        )

    monkeypatch.setattr(cli.os, "replace", failing_replace)

    assert _emit(path, output) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{output}: error: {reason} (errno {error_number})\n"


def test_backend_error_does_not_truncate_existing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")
    diagnostic = Diagnostic(
        code="PIE-B1000",
        severity=Severity.ERROR,
        message="unsupported backend case",
        location=SourceLocation(path=str(path), line=1, column=1),
    )
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(artifacts=(), diagnostics=(diagnostic,)),
    )

    assert _emit(path, output) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-B1000 error:" in captured.err
    assert output.read_text(encoding="utf-8") == "original SQL\n"


def test_newline_in_path_is_escaped_in_diagnostic_record(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "forged\nPIE-S9999 error.pietto", "type = Int\n")

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "\\nPIE-S9999" in captured.err
    assert "\nPIE-S9999" not in captured.err
    assert len(captured.err.splitlines()) == 1


def test_newline_in_missing_path_is_escaped_in_cli_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "missing\nforged-error.pietto"

    assert cli.main(["check", str(path)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "\\nforged-error.pietto" in captured.err
    assert "\nforged-error.pietto" not in captured.err
    assert len(captured.err.splitlines()) == 1


def test_escape_in_path_is_not_emitted_as_raw_ansi(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "color\x1b[31m.pietto", "shape User {\n")

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "\x1b" not in captured.err
    assert "\\x1b[31m" in captured.err


def test_control_characters_in_diagnostic_text_are_escaped(
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code="PIE-P1000",
        severity=Severity.ERROR,
        message="first\nsecond\r\t\x1b\x00\x7f",
        location=SourceLocation(
            path="bad\npath\x1b.pietto",
            line=1,
            column=2,
        ),
    )

    cli._render_diagnostics((diagnostic,), fallback_path=Path("fallback.pietto"))

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "bad\\npath\\x1b.pietto:1:2 PIE-P1000 error: first\\nsecond\\r\\t\\x1b\\x00\\x7f\n"
    )


_UNICODE_CONTROLS = (
    "\u0080\u0085\u009b\u009f"  # C1, including NEL and CSI
    "\u2028\u2029"  # line and paragraph separators
    "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e"  # bidi
    "\u2066\u2067\u2068\u2069"  # bidi isolates
)


@pytest.mark.parametrize("character", list(_UNICODE_CONTROLS))
def test_unicode_controls_in_diagnostic_text_are_u_escaped(
    character: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code="PIE-P1000",
        severity=Severity.ERROR,
        message=f"input '{character}'",
        location=SourceLocation(path=f"a{character}.pietto", line=1, column=2),
    )

    cli._render_diagnostics((diagnostic,), fallback_path=Path("fallback.pietto"))

    escape = f"\\u{ord(character):04x}"
    assert capsys.readouterr() == (
        "",
        f"a{escape}.pietto:1:2 PIE-P1000 error: input '{escape}'\n",
    )


def test_neighbors_of_escaped_unicode_controls_stay_raw(
    capsys: pytest.CaptureFixture[str],
) -> None:
    text = "~\u00a0\u00e9\u2027\u202f\u2065\u206a"

    cli._print_cli_error(Path(text), text)

    assert capsys.readouterr() == ("", f"{text}: error: {text}\n")


@pytest.mark.parametrize("character", ["\u009b", "\u2028", "\u202e"])
def test_source_unicode_controls_are_escaped_in_text_and_raw_in_json(
    character: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "controls.pietto", f"{SOURCE}{character}\n")
    escape = f"\\u{ord(character):04x}"

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"input '{escape}'" in captured.err
    assert character not in captured.err

    assert cli.main(["check", str(path), "--format", "json"]) == 1
    document = json.loads(capsys.readouterr().out)
    assert f"input '{character}'" in document["diagnostics"][0]["message"]

    valid = _write(tmp_path, f"ok{character}.pietto", SOURCE)
    assert cli.main(["check", str(valid)]) == 0
    assert capsys.readouterr().out == f"OK: {str(valid).replace(character, escape)}\n"


def test_success_path_with_newline_is_escaped_on_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path, "valid\nname.pietto", "shape User:\n    id: UUID not null\n"
    )

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {str(path).replace(chr(10), r'\n')}\n"
    assert len(captured.out.splitlines()) == 1
    assert captured.err == ""


def test_explain_text_path_is_escaped_and_json_path_stays_raw(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "nl\nesc\x1b[31m.pietto", SOURCE)
    escaped = str(path).replace("\n", r"\n").replace("\x1b", r"\x1b")

    assert cli.main(["explain", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out.splitlines()[3] == f"path: {escaped}"
    assert "\x1b" not in captured.out
    assert captured.err == ""

    assert cli.main(["explain", str(path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["path"] == str(path)


def _emit(path: Path, output: Path) -> int:
    return cli.main(
        [
            "emit-sql",
            str(path),
            "--dialect",
            "postgres",
            "--output",
            str(output),
        ]
    )


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _fake_proc(monkeypatch: pytest.MonkeyPatch, files: dict[str, str | None]) -> None:
    """Let reading each of these /proc files give its text; None refuses it."""

    real_read_text = Path.read_text

    def read_text(self: Path, *arguments: Any, **keywords: Any) -> str:
        if str(self) not in files:
            return real_read_text(self, *arguments, **keywords)
        text = files[str(self)]
        if text is None:
            raise PermissionError(errno.EACCES, "Permission denied", str(self))
        return text

    monkeypatch.setattr(Path, "read_text", read_text)


def _without_inherited_acl(directory: Path) -> None:
    """Let new files in directory get exactly their mode less the umask.

    A shared or HPC base directory can pass tmp_path a default POSIX ACL,
    which overrides the umask and masks the group bits of every new file.
    """

    if sys.platform != "linux":
        return
    for name in ("system.posix_acl_default", "system.posix_acl_access"):
        try:
            os.removexattr(directory, name)
        except OSError as error:
            if error.errno not in {errno.ENODATA, errno.ENOTSUP, errno.EOPNOTSUPP}:
                raise


# Linux POSIX ACL xattr: version 2, then little-endian (tag, perm, id) entries;
# tags 1 owner, 2 named user, 4 owning group, 16 mask, 32 other.
_NO_ID = 0xFFFFFFFF
_NOBODY = 65534


def _posix_acl(entries: list[tuple[int, int, int]]) -> bytes:
    return struct.pack("<I", 2) + b"".join(
        struct.pack("<HHI", *entry) for entry in entries
    )


def _posix_acl_entries(path: Path) -> list[tuple[int, int, int]] | None:
    try:
        value = os.getxattr(path, "system.posix_acl_access")
    except OSError as error:
        if error.errno == errno.ENODATA:
            return None
        raise
    return list(struct.iter_unpack("<HHI", value[4:]))
