from __future__ import annotations

import os
import stat
import sys
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
    # Windows shows only the read-only attribute, which the replacement lacks.
    assert stat.S_IMODE(written.st_mode) == (
        0o666 if sys.platform == "win32" else 0o640
    )
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
        (["--project"], "pietto fmt: error: argument --project: expected one argument"),
        (
            ["--project", "."],
            "pietto fmt: error: argument --project: not allowed with argument path",
        ),
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


@pytest.mark.parametrize("kind", ["missing", "directory", "invalid_utf8", "-"])
def test_fmt_file_errors_are_usage_failures_as_migrate_reports_them(
    kind: str,
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

    for mode in ([], ["--check"], ["--write"]):
        assert cli.main(["fmt", *mode, str(path)]) == 2, mode

        assert capsys.readouterr() == expected, mode
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


CONFIG = 'schema_version = 2\n[sources]\ninclude = ["*.pietto", "sub/*.pietto"]\n'


def _project(tmp_path: Path, modules: dict[str, bytes]) -> Path:
    root = tmp_path / "project"
    (root / "sub").mkdir(parents=True)
    (root / "pietto.toml").write_text(CONFIG + 'exclude = ["skip.pietto"]\n')
    for name, data in modules.items():
        (root / name).write_bytes(data)
    return root


def _contents(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_fmt_project_checks_and_rewrites_every_module_in_module_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(
        tmp_path,
        {
            "sub/c.pietto": MESSY,
            "b.pietto": MESSY,
            "a.pietto": FORMATTED,
            "skip.pietto": MESSY,
            "notes.txt": MESSY,
        },
    )
    before = _contents(root)
    untouched = os.stat(root / "a.pietto")

    assert cli.main(["fmt", "--project", str(root), "--check"]) == 1
    assert capsys.readouterr() == (
        "",
        "would reformat: b.pietto\nwould reformat: sub/c.pietto\n",
    )
    assert _contents(root) == before

    assert cli.main(["fmt", "--write", "--project", str(root)]) == 0
    assert capsys.readouterr() == ("", "")
    assert _contents(root) == {
        **before,
        "b.pietto": FORMATTED,
        "sub/c.pietto": FORMATTED,
    }
    assert (
        os.stat(root / "a.pietto").st_ino,
        os.stat(root / "a.pietto").st_mtime_ns,
    ) == (
        untouched.st_ino,
        untouched.st_mtime_ns,
    )

    assert cli.main(["fmt", "--check", "--project", str(root)]) == 0
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("mode", ["--check", "--write"])
def test_fmt_project_refuses_the_whole_project_as_check_reports_its_parser_errors(
    mode: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(
        tmp_path,
        {
            "a.pietto": MESSY,
            "b.pietto": b"shape A:\n    id: Int\n  name: Text\n",
            "sub/c.pietto": WARNED,
            "sub/d.pietto": b"shape A:\n\tid: Int\n",
        },
    )
    before = _contents(root)
    assert cli.main(["check", "--project", str(root)]) == 1
    expected = capsys.readouterr().err

    assert cli.main(["fmt", mode, "--project", str(root)]) == 1

    assert capsys.readouterr() == ("", expected)
    assert "PIE-P1009" in expected and _contents(root) == before


@pytest.mark.parametrize("mode", ["--check", "--write"])
def test_fmt_project_refuses_the_whole_project_when_one_module_cannot_be_formatted(
    mode: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(
        tmp_path,
        {"a.pietto": MESSY, "b.pietto": b"#" * (1024 * 1024 + 1), "c.pietto": MESSY},
    )
    before = _contents(root)
    monkeypatch.setattr(source_format, "_render", lambda lines, newline: "")

    assert cli.main(["fmt", mode, "--project", str(root)]) == 1

    refused = (
        ": error: formatting would not keep the source's tokens, comments and "
        "blocks; nothing was printed or written\n"
    )
    assert capsys.readouterr() == (
        "",
        f"a.pietto{refused}"
        "b.pietto:1:1 PIE-P1006 error: Source exceeds the maximum supported size "
        "of 1048576 UTF-8 bytes.\n"
        f"c.pietto{refused}",
    )
    assert _contents(root) == before


@pytest.mark.parametrize(
    ("data", "check_err"),
    [
        (MESSY, "would reformat: a.pietto\nwould reformat: link.pietto\n"),
        (FORMATTED, "would reformat: a.pietto\n"),
        (
            b"#" * 1_048_577,
            "link.pietto:1:1 PIE-P1006 error: Source exceeds the maximum supported "
            "size of 1048576 UTF-8 bytes.\n",
        ),
    ],
    ids=["messy", "formatted", "oversize"],
)
def test_fmt_project_write_refuses_a_symbolic_link_module(
    data: bytes, check_err: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(tmp_path, {"a.pietto": MESSY, "sub/target.txt": data})
    (root / "link.pietto").symlink_to(root / "sub" / "target.txt")
    before = _contents(root)

    assert cli.main(["fmt", "--write", "--project", str(root)]) == 2

    assert capsys.readouterr() == (
        "",
        "link.pietto: error: source file must not be a symbolic link\n",
    )
    assert _contents(root) == before and (root / "link.pietto").is_symlink()

    assert cli.main(["fmt", "--check", "--project", str(root)]) == 1
    assert capsys.readouterr().err == check_err


@pytest.mark.skipif(
    not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root writes any file"
)
@pytest.mark.parametrize(
    ("read_only", "refusal"),
    [
        ("b.pietto", "b.pietto: error: source file is read-only"),
        ("sub", "sub/c.pietto: error: source file directory is not writable"),
    ],
    ids=["file", "directory"],
)
def test_fmt_project_write_writes_no_module_when_one_cannot_be_replaced(
    read_only: str, refusal: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = _project(
        tmp_path,
        {
            "a.pietto": MESSY,
            "b.pietto": MESSY,
            "c.pietto": FORMATTED,
            "sub/c.pietto": MESSY,
        },
    )
    (root / "c.pietto").chmod(0o444)
    (root / read_only).chmod(0o555)
    before = _contents(root)
    try:
        assert cli.main(["fmt", "--write", "--project", str(root)]) == 2
    finally:
        (root / "sub").chmod(0o755)

    assert capsys.readouterr() == (
        "",
        f"{refusal}; the source file was not changed\n",
    )
    assert _contents(root) == before


def test_fmt_project_write_refuses_a_module_changed_after_it_was_read(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _project(tmp_path, {"a.pietto": MESSY, "b.pietto": MESSY})
    original = cli.format_source

    def format_then_change(source: str, *, path: str) -> Any:
        result = original(source, path=path)
        if path == "b.pietto":
            (root / path).write_bytes(MESSY + b"# new\n")
        return result

    monkeypatch.setattr(cli, "format_source", format_then_change)

    assert cli.main(["fmt", "--write", "--project", str(root)]) == 2

    # Each module is replaced whole, in module order, up to the first refusal.
    assert capsys.readouterr() == (
        "",
        "b.pietto: error: source file changed while it was formatted; "
        "the source file was not changed\n",
    )
    assert _contents(root)["a.pietto"] == FORMATTED
    assert _contents(root)["b.pietto"] == MESSY + b"# new\n"


@pytest.mark.parametrize(
    ("config", "modules"),
    [
        (None, {}),
        ('schema_version = 2\n[sources]\ninclude = ["none/*.pietto"]\n', {}),
        ("x", {}),
        (CONFIG, {"b.pietto": b"\xff\n", "c.pietto": b"#" * (1024 * 1024 + 1)}),
    ],
    ids=["no_config", "no_match", "invalid", "unreadable_and_oversize"],
)
@pytest.mark.parametrize("mode", ["--check", "--write"])
def test_fmt_project_reports_project_errors_as_check_does(
    config: str | None,
    modules: dict[str, bytes],
    mode: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path, {"a.pietto": MESSY, **modules})
    if config is None:
        (root / "pietto.toml").unlink()
    else:
        (root / "pietto.toml").write_text(config)
    before = _contents(root)
    assert cli.main(["check", "--project", str(root)]) == 2
    expected = capsys.readouterr()

    assert cli.main(["fmt", mode, "--project", str(root)]) == 2

    assert capsys.readouterr() == expected
    assert expected.err.startswith("project error: ")
    assert ("PIE-P1006" in expected.err) == bool(modules)
    assert _contents(root) == before


PACKAGE_ROOT = (
    '[package]\npath = "pkg"\nnamespace = "example"\nname = "shop"\n'
    f'version = "1.0.0"\nsha256 = "{"0" * 64}"\n'
)


@pytest.mark.parametrize(
    ("config", "version", "hint"),
    [
        (
            CONFIG.replace("2", "1"),
            1,
            "Set schema_version = 2 and declare the names a file uses from "
            "another file with import and export.",
        ),
        *(
            (
                f"schema_version = {version}\n{PACKAGE_ROOT}{tables}",
                version,
                "Select the package's modules with a schema_version = 2 "
                "pietto.toml in the package directory.",
            )
            for version, tables in ((3, ""), (4, "[capability_environment]\n"))
        ),
    ],
    ids=["v1", "v3", "v4"],
)
@pytest.mark.parametrize("mode", ["--check", "--write"])
def test_fmt_project_refuses_another_schema_version_with_a_hint(
    config: str,
    version: int,
    hint: str,
    mode: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path, {"a.pietto": MESSY})
    (root / "pietto.toml").write_text(config)

    assert cli.main(["fmt", mode, "--project", str(root)]) == 2

    assert capsys.readouterr() == (
        "",
        "project error: config_schema: fmt --project needs schema_version = 2 "
        f"(explicit modules); this project uses schema_version {version}. {hint} "
        "(path: pietto.toml)\n",
    )
    assert (root / "a.pietto").read_bytes() == MESSY


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        ([], "--project needs --check or --write"),
        (["--format=json", "--check"], "unrecognized arguments: --format=json"),
        (
            ["a.pietto", "--check"],
            "argument path: not allowed with argument --project",
        ),
    ],
)
def test_fmt_project_usage_errors(
    arguments: list[str],
    message: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _project(tmp_path, {"a.pietto": MESSY})

    assert cli.main(["fmt", "--project", str(root), *arguments]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines()[-1].endswith(f" error: {message}")
    assert (root / "a.pietto").read_bytes() == MESSY


def test_fmt_needs_a_path_or_a_project(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["fmt"]) == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        "pietto fmt: error: one of the arguments path --project is required"
    )
    assert cli.main(["fmt", "--project", ""]) == 2
    assert capsys.readouterr().err.splitlines()[-1] == (
        "pietto fmt: error: argument --project: Project root must be a non-empty path."
    )
