from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import Any

import pytest

from pietto import cli, source_format

MESSY = b"shape A:\r\n  id: Int   \r\n"
FORMATTED = b"shape A:\r\n    id: Int\r\n"


def _source(tmp_path: Path, data: bytes = MESSY) -> Path:
    path = tmp_path / "a.pietto"
    path.write_bytes(data)
    return path


@pytest.mark.parametrize(
    ("messy", "formatted"),
    [
        pytest.param(MESSY, FORMATTED, id="crlf"),
        pytest.param(
            b"shape A:\r  id: Int  # a \r", b"shape A:\r    id: Int  # a\r", id="cr"
        ),
        pytest.param(
            b"\xef\xbb\xbfshape A:\n  id: Int\n",
            b"\xef\xbb\xbfshape A:\n    id: Int\n",
            id="bom",
        ),
    ],
)
def test_fmt_writes_the_formatted_source_to_stdout_or_the_file(
    messy: bytes,
    formatted: bytes,
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    path = _source(tmp_path, messy)

    assert cli.main(["fmt", str(path)]) == 0

    captured = capsysbinary.readouterr()
    assert (captured.out, captured.err) == (formatted, b"")
    assert path.read_bytes() == messy

    assert cli.main(["fmt", "--write", str(path)]) == 0
    assert capsysbinary.readouterr() == (b"", b"")
    assert path.read_bytes() == formatted


def test_fmt_check_reports_an_unformatted_file_and_never_writes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _source(tmp_path)

    assert cli.main(["fmt", "--check", str(path)]) == 1
    assert capsys.readouterr() == ("", f"would reformat: {path}\n")
    assert path.read_bytes() == MESSY

    path.write_bytes(FORMATTED)
    assert cli.main(["fmt", "--check", str(path)]) == 0
    assert capsys.readouterr() == ("", "")


def test_fmt_write_replaces_only_an_unformatted_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _source(tmp_path)
    path.chmod(0o640)
    read = os.stat(path)

    assert cli.main(["fmt", "--write", str(path)]) == 0
    assert capsys.readouterr() == ("", "")
    assert path.read_bytes() == FORMATTED
    written = os.stat(path)
    assert stat.S_IMODE(written.st_mode) == 0o640
    assert written.st_ino != read.st_ino  # replaced, not written in place

    assert cli.main(["fmt", "--write", str(path)]) == 0
    assert capsys.readouterr() == ("", "")
    assert os.stat(path).st_ino == written.st_ino
    assert os.stat(path).st_mtime_ns == written.st_mtime_ns
    assert sorted(item.name for item in tmp_path.iterdir()) == ["a.pietto"]


def test_fmt_write_leaves_the_file_whole_when_the_replace_fails(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _source(tmp_path)

    def refuse(source: object, target: object) -> None:
        raise PermissionError(13, "denied")

    monkeypatch.setattr(cli.os, "replace", refuse)

    assert cli.main(["fmt", "--write", str(path)]) == 2

    assert capsys.readouterr() == (
        "",
        f"{path}: error: Permission denied (errno 13)\n",
    )
    assert path.read_bytes() == MESSY
    assert sorted(item.name for item in tmp_path.iterdir()) == ["a.pietto"]


@pytest.mark.parametrize("when", ["after_formatting", "after_the_temporary_file"])
def test_fmt_write_refuses_a_file_changed_after_it_was_read(
    when: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _source(tmp_path)
    name = "format_file" if when == "after_formatting" else "open_replacement"
    original = getattr(cli, name)

    def call_then_change(target: Path) -> Any:
        result = original(target)
        target.write_bytes(MESSY + b"# new\n")
        return result

    monkeypatch.setattr(cli, name, call_then_change)

    assert cli.main(["fmt", "--write", str(path)]) == 2
    assert sorted(item.name for item in tmp_path.iterdir()) == ["a.pietto"]

    assert capsys.readouterr() == (
        "",
        f"{path}: error: source file changed while it was formatted; "
        "the source file was not changed\n",
    )
    assert path.read_bytes() == MESSY + b"# new\n"


@pytest.mark.skipif(not Path("/dev/null").exists(), reason="needs /dev/null")
def test_fmt_write_refuses_a_file_that_is_not_regular(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["fmt", "--write", "/dev/null"]) == 2

    assert capsys.readouterr() == (
        "",
        "/dev/null: error: source file must be a regular file\n",
    )


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs os.mkfifo")
def test_fmt_write_refuses_a_fifo_before_reading_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "a.pietto"
    os.mkfifo(path)

    # Reading a FIFO without a writer would block this call.
    assert cli.main(["fmt", "--write", str(path)]) == 2

    assert capsys.readouterr() == (
        "",
        f"{path}: error: source file must be a regular file\n",
    )
    assert stat.S_ISFIFO(path.lstat().st_mode)


@pytest.mark.parametrize(
    "source",
    [
        b"shape A:\n    id: Int\n  name: Text\n",
        b"\xef\xbb\xbfshape A:\n    id: Int\n  name: Text\n",
        b"\xef\xbb\xbfshape A\n    id: Int\n",
        b"shape A:\r\n    id: Int\r\n  name: Text\r\n",
        b"shape A:\r    id: Int\r  name: Text\r",
        b"shape A:\n\tid: Int\n",
        b'source a = postgres.table("a"\n',
        b"#" * (1024 * 1024 + 1),
    ],
    ids=[
        "PIE-P1003",
        "PIE-P1003-bom",
        "line-1-bom",
        "PIE-P1003-crlf",
        "PIE-P1003-cr",
        "PIE-P1004",
        "PIE-P1008",
        "PIE-P1006",
    ],
)
@pytest.mark.parametrize("mode", [[], ["--check"], ["--write"]])
def test_fmt_refuses_a_source_with_parser_errors_as_check_reports_them(
    source: bytes,
    mode: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _source(tmp_path, source)
    assert cli.main(["check", str(path)]) == 1
    expected = capsys.readouterr().err

    assert cli.main(["fmt", *mode, str(path)]) == 1

    assert capsys.readouterr() == ("", expected)
    assert path.read_bytes() == source


WARNED = b"query q:\n  from a\n  where 1 -- 2 > 0\n  select x\n"
WARNED_FORMATTED = b"query q:\n    from a\n    where 1 -- 2 > 0\n    select x\n"


@pytest.mark.parametrize(
    ("mode", "data", "out", "written"),
    [
        ([], WARNED, WARNED_FORMATTED, WARNED),
        (["--check"], WARNED_FORMATTED, b"", WARNED_FORMATTED),
        (["--write"], WARNED, b"", WARNED_FORMATTED),
    ],
    ids=["stdout", "check", "write"],
)
def test_fmt_reports_parser_warnings_and_still_formats(
    mode: list[str],
    data: bytes,
    out: bytes,
    written: bytes,
    tmp_path: Path,
    capsysbinary: pytest.CaptureFixture[bytes],
) -> None:
    path = _source(tmp_path, data)
    cli.main(["check", str(path)])
    warnings = [
        line
        for line in capsysbinary.readouterr().err.splitlines(keepends=True)
        if b"PIE-P1009" in line
    ]
    assert len(warnings) == 1

    assert cli.main(["fmt", *mode, str(path)]) == 0

    # Positions refer to the file as it was read.
    assert capsysbinary.readouterr() == (out, warnings[0])
    assert warnings[0].startswith(f"{path}:3:".encode())
    assert path.read_bytes() == written


@pytest.mark.parametrize("mode", [[], ["--check"], ["--write"]])
def test_fmt_fails_closed_when_the_result_would_not_keep_the_source(
    mode: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(source_format, "_render", lambda lines, newline: "")
    path = _source(tmp_path)

    assert cli.main(["fmt", *mode, str(path)]) == 1

    assert capsys.readouterr() == (
        "",
        f"{path}: error: formatting would not keep the source's tokens, comments "
        "and blocks; nothing was printed or written\n",
    )
    assert path.read_bytes() == MESSY


@pytest.mark.parametrize("mode", [[], ["--check"], ["--write"]])
def test_fmt_fails_closed_when_the_result_would_exceed_the_size_limit(
    mode: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = b"shape A:\n  id: Int\n"
    monkeypatch.setattr(
        source_format.parser_api,
        "_source_exceeds_utf8_budget",
        lambda text: len(text) > len(data),
    )
    path = _source(tmp_path, data)

    assert cli.main(["fmt", *mode, str(path)]) == 1

    assert capsys.readouterr() == (
        "",
        f"{path}: error: the formatted source would exceed the maximum supported "
        "size of 1048576 UTF-8 bytes; nothing was printed or written\n",
    )
    assert path.read_bytes() == data


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (
            ["--check", "--write"],
            "pietto fmt: error: argument --write: not allowed with argument --check",
        ),
        (["--project"], "pietto: error: unrecognized arguments: --project"),
        (
            ["--format", "json"],
            "pietto: error: unrecognized arguments: --format json",
        ),
        (["a.pietto"], "pietto: error: unrecognized arguments: a.pietto"),
    ],
)
def test_fmt_usage_errors(
    arguments: list[str],
    message: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _source(tmp_path)

    assert cli.main(["fmt", str(path), *arguments]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines()[-1] == message
    assert path.read_bytes() == MESSY


def test_migrate_has_no_json_mode_either(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _source(tmp_path)

    assert cli.main(["migrate", str(path), "--format", "json"]) == 2

    assert capsys.readouterr().err.splitlines()[-1] == (
        "pietto: error: unrecognized arguments: --format json"
    )


@pytest.mark.parametrize("kind", ["missing", "directory", "invalid_utf8", "-"])
@pytest.mark.parametrize("mode", [[], ["--check"], ["--write"]])
def test_fmt_file_errors_are_usage_failures_as_migrate_reports_them(
    kind: str,
    mode: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)  # "-" names a file, as it does for migrate
    path = Path(kind) if kind == "-" else tmp_path / kind
    if kind == "directory":
        path.mkdir()
    elif kind == "invalid_utf8":
        path.write_bytes(b"\xff")
    assert cli.main(["migrate", str(path)]) == 2
    expected = capsys.readouterr()
    assert expected.out == "" and expected.err.startswith(f"{path}: error:")

    assert cli.main(["fmt", *mode, str(path)]) == 2

    assert capsys.readouterr() == expected
    if kind == "invalid_utf8":
        assert path.read_bytes() == b"\xff"


@pytest.mark.parametrize("data", [MESSY, FORMATTED], ids=["messy", "formatted"])
def test_fmt_write_refuses_a_symbolic_link(
    data: bytes, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = _source(tmp_path, data)
    link = tmp_path / "link.pietto"
    link.symlink_to(target)

    assert cli.main(["fmt", "--write", str(link)]) == 2

    assert capsys.readouterr() == (
        "",
        f"{link}: error: source file must not be a symbolic link\n",
    )
    assert link.is_symlink() and target.read_bytes() == data


@pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root writes any file"
)
def test_fmt_write_refuses_a_read_only_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _source(tmp_path)
    path.chmod(0o444)

    assert cli.main(["fmt", "--write", str(path)]) == 2

    assert capsys.readouterr() == (
        "",
        f"{path}: error: source file is read-only; the source file was not changed\n",
    )
    assert path.read_bytes() == MESSY


def test_fmt_write_leaves_a_formatted_read_only_file_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _source(tmp_path, FORMATTED)
    path.chmod(0o444)
    read = os.stat(path)

    assert cli.main(["fmt", "--write", str(path)]) == 0

    assert capsys.readouterr() == ("", "")
    assert path.read_bytes() == FORMATTED
    assert (os.stat(path).st_ino, os.stat(path).st_mtime_ns) == (
        read.st_ino,
        read.st_mtime_ns,
    )
