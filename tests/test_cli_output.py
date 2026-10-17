from __future__ import annotations

import contextlib
import errno
import io
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.sql import SqlArtifact, SqlArtifactKind, SqlResult

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
)
_OUTPUT_ENCODING_ERROR = b"pietto: error: terminal output could not be encoded\n"
_STDOUT_NO_SPACE = (
    "pietto: error: standard output could not be written: "
    f"No space left on device (errno {errno.ENOSPC})\n"
)
_STDOUT_CLOSED = "pietto: error: standard output is closed\n"


def test_emit_sql_default_output_remains_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.out == _expected_sql()
    assert captured.err == ""


def test_emit_sql_output_file_receives_sql_and_stdout_stays_empty(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)
    output = tmp_path / "out.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert output.read_text(encoding="utf-8") == _expected_sql()


def test_emit_sql_output_file_is_overwritten(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)
    output = tmp_path / "out.sql"
    output.write_text("stale SQL\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    assert output.read_text(encoding="utf-8") == _expected_sql()
    assert capsys.readouterr().out == ""


def test_emit_sql_output_file_preserves_multiple_artifact_formatting(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "relations.pietto",
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    select:\n"
        "        email\n",
    )
    output = tmp_path / "relations.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    assert output.read_text(encoding="utf-8") == (
        'SELECT\n    "email" AS "email"\nFROM "users"\n'
        "\n"
        'SELECT\n    "email" AS "email"\nFROM "active_users"\n'
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_emit_sql_output_keeps_warnings_on_stderr(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "warning.pietto",
        "shape User:\n"
        "    email: Text\n"
        'source users: User is postgres.table("users")\n'
        "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n",
    )
    output = tmp_path / "warning.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2005 warning:" in captured.err
    assert output.read_text(encoding="utf-8").startswith("SELECT\n")


@pytest.mark.parametrize(
    ("destination", "reason"),
    [
        ("missing/out.sql", "No such file or directory"),
        ("existing-directory", "Is a directory"),
        # The parent is a regular file: compilation runs, then the write fails.
        (
            "plain-file/out.sql",
            "No such file or directory"
            if sys.platform == "win32"
            else "Not a directory",
        ),
    ],
)
def test_emit_sql_output_write_error_reports_only_the_user_path(
    destination: str,
    reason: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)
    (tmp_path / "existing-directory").mkdir()
    _write(tmp_path, "plain-file", "plain\n")
    monkeypatch.chdir(tmp_path)

    assert (
        cli.main(
            [
                "emit-sql",
                path.name,
                "--dialect",
                "postgres",
                "--output",
                destination,
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith(f"{Path(destination)}: error: {reason} (errno ")
    assert ".tmp" not in captured.err
    assert str(tmp_path) not in captured.err
    assert not (tmp_path / "missing").exists()
    assert (tmp_path / "existing-directory").is_dir()
    assert (tmp_path / "plain-file").read_text(encoding="utf-8") == "plain\n"
    assert not tuple(tmp_path.rglob("*.tmp"))


def test_emit_sql_regular_file_parent_fails_after_compilation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        tmp_path,
        "warning.pietto",
        "shape User:\n"
        "    email: Text\n"
        'source users: User is postgres.table("users")\n'
        "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n",
    )
    _write(tmp_path, "plain-file", "plain\n")
    monkeypatch.chdir(tmp_path)
    reason = (
        "No such file or directory (errno 2)"
        if sys.platform == "win32"
        else "Not a directory (errno 20)"
    )

    assert (
        cli.main(
            [
                "emit-sql",
                "warning.pietto",
                "--dialect",
                "postgres",
                "--output",
                "plain-file/out.sql",
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    # The compiler warning precedes the write error, so compilation ran first.
    warning, write_error = captured.err.splitlines()
    assert "PIE-S2005 warning:" in warning
    assert write_error == f"{Path('plain-file/out.sql')}: error: {reason}"


@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
@pytest.mark.parametrize("existing", [False, True])
def test_emit_sql_zero_artifacts_refuse_the_output_file(
    dialect: str,
    existing: bool,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "shapes.pietto", SOURCE)
    output = tmp_path / "out.sql"
    if existing:
        output.write_text("original SQL\n", encoding="utf-8")

    assert (
        cli.main(["emit-sql", str(path), "--dialect", dialect, "--output", str(output)])
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"{output}: error: no SQL artifacts to write; the output file was not changed\n"
    )
    if existing:
        assert output.read_text(encoding="utf-8") == "original SQL\n"
    else:
        assert not output.exists()
    assert not tuple(tmp_path.glob("*.tmp"))


def test_emit_sql_output_file_uses_lf_on_every_platform(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The file receives encoded bytes through a binary (O_BINARY) descriptor,
    # so no text layer can turn "\n" into "\r\n" on Windows.
    path = _relation_file(tmp_path)
    output = tmp_path / "out.sql"

    assert (
        cli.main(
            ["emit-sql", str(path), "--dialect", "postgres", "--output", str(output)]
        )
        == 0
    )

    assert capsys.readouterr() == ("", "")
    assert output.read_bytes() == _expected_sql().encode("utf-8")
    assert b"\r" not in output.read_bytes()


def test_emit_sql_backend_error_does_not_create_output_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "backend-error.pietto", SOURCE)
    output = tmp_path / "backend-error.sql"
    artifact = SqlArtifact(
        name="partial",
        kind=SqlArtifactKind.RELATION,
        sql='SELECT "id" AS "id"\nFROM "users"',
    )
    diagnostic = Diagnostic(
        code="PIE-B1000",
        severity=Severity.ERROR,
        message="unsupported backend case",
        location=SourceLocation(path=str(path), line=1, column=1),
    )
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(
            artifacts=(artifact,),
            diagnostics=(diagnostic,),
        ),
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-B1000 error:" in captured.err
    assert not output.exists()


@pytest.mark.parametrize(
    ("name", "source", "expected_code"),
    [
        ("syntax.pietto", "shape User {\n", "PIE-P1005"),
        (
            "semantic.pietto",
            "shape User:\n    email: MissingType not null\n",
            "PIE-S2002",
        ),
    ],
)
def test_emit_sql_frontend_error_does_not_create_output_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    name: str,
    source: str,
    expected_code: str,
) -> None:
    path = _write(tmp_path, name, source)
    output = tmp_path / f"{name}.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert expected_code in captured.err
    assert not output.exists()


def test_emit_sql_unsupported_dialect_still_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)
    output = tmp_path / "out.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "sqlite",
                "--output",
                str(output),
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice: 'sqlite'" in captured.err
    assert not output.exists()


def test_check_behavior_remains_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid-check.pietto", SOURCE)

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must not build IR or emit SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


def test_terminal_encoding_failure_returns_safe_output_error(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        "emoji.pietto",
        "shape User:\n"
        "    id: UUID not null\n"
        'source users: User is postgres.table("secret😀")\n'
        "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        id\n",
    )

    normal = _run_cli(["emit-sql", str(path), "--dialect", "postgres"])
    assert normal.returncode == 0
    assert normal.stderr == b""
    assert normal.stdout == _expected_emoji_sql().encode("utf-8")
    for encoding in ("gbk", "cp1252", "ascii"):
        failed = _run_cli(
            ["emit-sql", str(path), "--dialect", "postgres"],
            encoding=encoding,
        )
        assert failed.returncode == 2
        assert failed.stdout == b""
        assert failed.stderr == _OUTPUT_ENCODING_ERROR
        assert b"secret" not in failed.stderr
        assert b"Traceback" not in failed.stderr

        output = tmp_path / f"{encoding}.sql"
        json_result = _run_cli(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(output),
            ],
            encoding=encoding,
        )
        assert json_result.returncode == 0
        assert json_result.stderr == b""
        assert json_result.stdout.isascii()
        assert json.loads(json_result.stdout)["artifacts"][0]["sql"] == (
            _expected_emoji_sql().rstrip("\n")
        )
        assert output.read_bytes() == _expected_emoji_sql().encode("utf-8")

        diagnostic = _run_cli(
            ["check", str(tmp_path / "missing😀.pietto")],
            encoding=encoding,
            strict_stderr=True,
        )
        assert diagnostic.returncode == 2
        assert diagnostic.stdout == b""
        assert diagnostic.stderr == _OUTPUT_ENCODING_ERROR
        assert b"Traceback" not in diagnostic.stderr


class _FailingStdout:
    """Stubbed stream fault: stdout whose write or flush fails like a descriptor."""

    encoding = "utf-8"

    def __init__(self, error: OSError, failing: str) -> None:
        self._error = error
        self._failing = failing

    def write(self, text: str) -> int:
        if self._failing == "write":
            raise self._error
        return len(text)

    def flush(self) -> None:
        if self._failing == "flush":
            raise self._error


@pytest.mark.parametrize(
    ("failure", "expected_stderr"),
    [
        # The reader closed the pipe and wants no more output.
        ("broken-pipe", ""),
        ("no-space", _STDOUT_NO_SPACE),
        # Python sets sys.stdout to None when descriptor 1 is closed.
        ("closed", _STDOUT_CLOSED),
    ],
)
@pytest.mark.parametrize(
    "command",
    [
        ["check", "{file}"],
        ["check", "{file}", "--format", "json"],
        ["explain", "{file}"],
        ["explain", "{file}", "--format", "json"],
        ["emit-sql", "{file}", "--dialect", "postgres"],
        ["emit-sql", "{file}", "--dialect", "postgres", "--format", "json"],
        ["check", "--project", "{project}"],
        ["check", "--project", "{project}", "--format", "json"],
        ["explain", "--project", "{project}", "--format", "json"],
        # Help and --version are command output on stdout too.
        [],
        ["--help"],
        ["--version"],
        ["check", "--help"],
        ["emit-sql", "{file}", "--format", "json", "--help"],
    ],
)
def test_stdout_failure_is_a_handled_cli_error_in_every_command(
    command: list[str],
    failure: str,
    expected_stderr: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _relation_file(tmp_path)
    project = tmp_path / "project"
    project.mkdir()
    (project / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    _write(project, "main.pietto", SOURCE)
    stdout = {
        "broken-pipe": _FailingStdout(BrokenPipeError(errno.EPIPE, "x"), "write"),
        "no-space": _FailingStdout(OSError(errno.ENOSPC, "localized"), "flush"),
        "closed": None,
    }[failure]
    monkeypatch.setattr(sys, "stdout", stdout)
    stderr = io.StringIO()

    with contextlib.redirect_stderr(stderr):
        code = cli.main([part.format(file=path, project=project) for part in command])

    assert (code, stderr.getvalue()) == (2, expected_stderr)


@pytest.mark.parametrize(
    ("platform", "expected_stderr"),
    [
        # Windows reports a pipe whose reader has gone as EINVAL, not EPIPE.
        ("win32", ""),
        (
            "linux",
            "pietto: error: standard output could not be written: "
            f"Operating system error (errno {errno.EINVAL})\n",
        ),
    ],
)
def test_einval_is_a_closed_pipe_reader_only_on_windows(
    platform: str,
    expected_stderr: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _relation_file(tmp_path)
    failing = _FailingStdout(OSError(errno.EINVAL, "Invalid argument"), "write")
    monkeypatch.setattr(sys, "stdout", failing)
    monkeypatch.setattr(sys, "platform", platform)
    stderr = io.StringIO()

    with contextlib.redirect_stderr(stderr):
        code = cli.main(["check", str(path)])

    assert (code, stderr.getvalue()) == (2, expected_stderr)


@pytest.mark.parametrize(
    ("command", "expected_code"),
    [
        (["check", "{bad}"], 1),  # compiler diagnostics
        (["check", "{missing}"], 2),  # CLI error
        (["check", "{bad}", "--project", "{project}"], 2),  # usage error
        (["check", "--project", "{missing}"], 2),  # project discovery error
        (["explain", "--project", "{project}"], 2),  # project explain failure text
        (["check", "--bogus"], 2),  # argparse usage errors
        (["emit-sql", "{bad}"], 2),
        (["check", "{bad}", "--format", "yaml"], 2),
    ],
)
def test_closed_stderr_drops_notices_instead_of_writing_them_to_stdout(
    command: list[str],
    expected_code: int,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bad = _write(tmp_path, "bad.pietto", "shape User:\n    id: Intx not null\n")
    project = tmp_path / "project"
    project.mkdir()
    (project / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    _write(project, "main.pietto", SOURCE)
    arguments = [
        part.format(bad=bad, missing=tmp_path / "missing", project=project)
        for part in command
    ]
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    # Python sets sys.stderr to None when descriptor 2 is closed.
    monkeypatch.setattr(sys, "stderr", None)

    assert cli.main(arguments) == expected_code

    assert stdout.getvalue() == ""


def test_argparse_stderr_text_never_reaches_stdout_when_stderr_is_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", None)
    parser = cli._build_parser()

    with pytest.raises(SystemExit) as exit_info:
        parser.exit(2, "pietto: error: boom\n")

    assert (exit_info.value.code, stdout.getvalue()) == (2, "")
    parser.print_help()  # stdout-bound text still reaches the open stdout
    assert stdout.getvalue().startswith("usage: pietto ")


_NEEDS_DEV_FULL = pytest.mark.skipif(
    not os.path.exists("/dev/full"), reason="needs /dev/full"
)


def _failing_sink(sink: str | None) -> int | None:
    if sink == "full":
        return os.open("/dev/full", os.O_WRONLY)
    if sink == "broken-pipe":
        read_end, write_end = os.pipe()
        os.close(read_end)
        return write_end
    return None


def _large_source(tmp_path: Path) -> Path:
    return _write(
        tmp_path,
        "large.pietto",
        "".join(
            f"shape S{index}:\n    id: UUID not null\n"
            f'source s{index}: S{index} is postgres.table("t{index}")\n'
            f"table r{index}:\n    from s{index}\n    select:\n        id\n"
            for index in range(40)
        ),
    )


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX pipes and sh")
@pytest.mark.parametrize("unbuffered", [False, True])
@pytest.mark.parametrize(
    ("sink", "command", "expected_stderr"),
    [
        # Output larger than the stdout buffer fails inside write().
        ("broken-pipe", ["explain", "{large}"], ""),
        # Small output fails only when it is flushed before exit.
        ("broken-pipe", ["check", "{file}", "--format", "json"], ""),
        pytest.param(
            "full",
            ["emit-sql", "{large}", "--dialect", "postgres"],
            _STDOUT_NO_SPACE,
            marks=_NEEDS_DEV_FULL,
        ),
        pytest.param("full", ["--version"], _STDOUT_NO_SPACE, marks=_NEEDS_DEV_FULL),
        ("closed", ["emit-sql", "{file}", "--dialect", "postgres"], _STDOUT_CLOSED),
        ("closed", ["--version"], _STDOUT_CLOSED),
    ],
)
def test_real_stdout_failure_exits_two_without_traceback(
    sink: str,
    command: list[str],
    expected_stderr: str,
    unbuffered: bool,
    tmp_path: Path,
) -> None:
    path = _relation_file(tmp_path)
    large = _large_source(tmp_path)
    arguments = [part.format(file=path, large=large) for part in command]
    descriptor = _failing_sink(sink)
    try:
        completed = _run_cli(
            arguments,
            stdout=descriptor,
            close_stdout=sink == "closed",
            unbuffered=unbuffered,
        )
    finally:
        if descriptor is not None:
            os.close(descriptor)

    assert (completed.returncode, completed.stderr) == (
        2,
        expected_stderr.encode("ascii"),
    )


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX pipes")
@pytest.mark.parametrize(
    "stderr_sink", [pytest.param("full", marks=_NEEDS_DEV_FULL), "broken-pipe"]
)
@pytest.mark.parametrize(
    ("stdout_sink", "command", "expected_code"),
    [
        # A stdout failure exits 2 even when its notice cannot be written.
        pytest.param("full", ["check", "{file}"], 2, marks=_NEEDS_DEV_FULL),
        pytest.param(
            "full",
            ["emit-sql", "{large}", "--dialect", "postgres", "--format", "json"],
            2,
            marks=_NEEDS_DEV_FULL,
        ),
        # With a working stdout, the lost warning leaves the result intact.
        (None, ["check", "{warning}"], 0),
        (None, ["emit-sql", "{warning}", "--dialect", "postgres"], 0),
    ],
)
def test_failing_stderr_keeps_the_command_result(
    stdout_sink: str | None,
    command: list[str],
    expected_code: int,
    stderr_sink: str,
    tmp_path: Path,
) -> None:
    path = _relation_file(tmp_path)
    large = _large_source(tmp_path)
    warning = _write(
        tmp_path,
        "warning.pietto",
        "shape User:\n"
        "    email: Text\n"
        'source users: User is postgres.table("users")\n'
        "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n",
    )
    arguments = [
        part.format(file=path, large=large, warning=warning) for part in command
    ]
    stdout = _failing_sink(stdout_sink)
    stderr = _failing_sink(stderr_sink)
    try:
        completed = _run_cli(arguments, stdout=stdout, stderr=stderr)
    finally:
        for descriptor in (stdout, stderr):
            if descriptor is not None:
                os.close(descriptor)

    assert completed.returncode == expected_code
    if stdout_sink is None and command[0] == "check":
        assert completed.stdout == f"OK: {warning}\n".encode()
    elif stdout_sink is None:
        assert completed.stdout.startswith(b'SELECT\n    "email" AS "email"\n')


@pytest.mark.skipif(sys.platform == "win32", reason="needs POSIX descriptors")
def test_stdout_descriptor_closed_after_startup_exits_two(tmp_path: Path) -> None:
    path = _relation_file(tmp_path)

    # The null device opened to discard stdout lands on the freed descriptor 1.
    completed = _run_cli(["check", str(path)], before_main="import os; os.close(1); ")

    assert (completed.returncode, completed.stderr) == (
        2,
        (
            "pietto: error: standard output could not be written: "
            f"Operating system error (errno {errno.EBADF})\n"
        ).encode("ascii"),
    )


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows limits the whole path, not one name"
)
def test_emit_sql_output_accepts_the_longest_file_name_the_os_accepts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)
    longest = os.pathconf(tmp_path, "PC_NAME_MAX")
    output = tmp_path / f"{'a' * (longest - len('.sql'))}.sql"

    assert (
        cli.main(
            ["emit-sql", str(path), "--dialect", "postgres", "--output", str(output)]
        )
        == 0
    )

    assert capsys.readouterr() == ("", "")
    assert output.read_text(encoding="utf-8") == _expected_sql()
    assert not tuple(tmp_path.glob("*.tmp"))


def _relation_file(tmp_path: Path) -> Path:
    return _write(
        tmp_path,
        "active_users.pietto",
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    where active == true\n"
        "    select:\n"
        "        id\n"
        "        email\n",
    )


def _expected_sql() -> str:
    return (
        "SELECT\n"
        '    "id" AS "id",\n'
        '    "email" AS "email"\n'
        'FROM "users"\n'
        'WHERE "active" = TRUE\n'
    )


def _expected_emoji_sql() -> str:
    return 'SELECT\n    "id" AS "id"\nFROM "secret😀"\n'


def _run_cli(
    arguments: list[str],
    *,
    encoding: str | None = None,
    strict_stderr: bool = False,
    stdout: int | None = None,
    stderr: int | None = None,
    close_stdout: bool = False,
    unbuffered: bool = False,
    before_main: str = "",
) -> subprocess.CompletedProcess[bytes]:
    environment = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    if encoding is None:
        environment.pop("PYTHONIOENCODING", None)
    else:
        environment["PYTHONIOENCODING"] = encoding
    # Buffering decides when a write fails, so it is pinned, not inherited.
    environment.pop("PYTHONUNBUFFERED", None)
    if unbuffered:
        environment["PYTHONUNBUFFERED"] = "1"
    program = f"from pietto.cli import main; {before_main}raise SystemExit(main())"
    if strict_stderr:
        program = (
            "import os, sys; sys.stderr = os.fdopen("
            "sys.stderr.fileno(), 'w', encoding=sys.stderr.encoding, "
            "errors='strict', closefd=False); " + program
        )
    command = [sys.executable, "-c", program, *arguments]
    if close_stdout:
        command = ["sh", "-c", 'exec "$@" >&-', "sh", *command]
    return subprocess.run(
        command,
        stdout=subprocess.PIPE if stdout is None else stdout,
        stderr=subprocess.PIPE if stderr is None else stderr,
        check=False,
        env=environment,
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
