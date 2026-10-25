from __future__ import annotations

import errno
import json
import os
import sys
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import IrResult
from pietto.sql import SqlArtifact, SqlArtifactKind, SqlResult

SOURCE = (
    "shape User:\n"
    "    id: UUID\n"
    "    email: Text\n"
    "    active: Bool\n"
    'source users: User = postgres.table("users")\n'
)
RELATION = (
    SOURCE + "table active_users:\n"
    "    from users\n"
    "    where active == True\n"
    "    select:\n"
    "        id\n"
    "        email\n"
)
EXPECTED_SQL = (
    "SELECT\n"
    '    "id" AS "id",\n'
    '    "email" AS "email"\n'
    'FROM "users"\n'
    'WHERE "active" = TRUE\n'
)


@pytest.mark.parametrize(
    "tail",
    [
        ["--format", "json", "--output"],
        ["--format=json", "--output"],
        ["--output", "--format", "json"],
    ],
)
def test_emit_sql_json_output_success_writes_raw_sql_and_keeps_artifacts(
    tail: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "active_users.pietto", RELATION)
    output = tmp_path / "out.sql"
    output.write_text("stale SQL\n", encoding="utf-8")
    arguments = ["emit-sql", str(path), "--dialect", "postgres"]
    if tail[0] == "--output":
        arguments.extend(["--output", str(output), "--format", "json"])
    else:
        arguments.extend([*tail, str(output)])

    assert cli.main(arguments) == 0
    captured = capsys.readouterr()
    result = _parse_json_document(captured.out, captured.err)

    assert result["ok"] is True
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output), "written": True}
    assert "version" not in result
    artifacts = cast(list[dict[str, object]], result["artifacts"])
    assert artifacts[0]["name"] == "active_users"
    assert artifacts[0]["sql"] == EXPECTED_SQL.removesuffix("\n")
    assert output.read_text(encoding="utf-8") == EXPECTED_SQL
    assert "\\n" in captured.out
    assert "SELECT\n" not in captured.out


def test_emit_sql_json_warning_writes_output_and_stays_ok(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "warning.pietto",
        "shape User:\n"
        "    email: Text\n"
        'source users: User = postgres.table("users")\n'
        # A source without a shape is a PIE-S2303 warning in the default mode.
        'source raw = postgres.table("raw")\n'
        "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n",
    )
    output = tmp_path / "warning.sql"

    assert _emit_json_output(path, output) == 0
    result = _read_json_document(capsys)

    assert result["ok"] is True
    assert result["output"] == {"path": str(output), "written": True}
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert [diagnostic["severity"] for diagnostic in diagnostics] == ["warning"]
    assert output.read_text(encoding="utf-8").startswith("SELECT\n")


@pytest.mark.parametrize(
    ("name", "source", "expected_code"),
    [
        ("parser.pietto", "shape User {\n", "PIE-P1005"),
        (
            "semantic.pietto",
            "shape User:\n    email: MissingType\n",
            "PIE-S2002",
        ),
    ],
)
def test_emit_sql_json_frontend_error_does_not_write_output(
    name: str,
    source: str,
    expected_code: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)
    output = _write(tmp_path, f"{name}.sql", "original SQL\n")

    assert _emit_json_output(path, output) == 1
    result = _read_json_document(capsys)

    assert result["ok"] is False
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output), "written": False}
    assert expected_code in [
        diagnostic["code"]
        for diagnostic in cast(list[dict[str, object]], result["diagnostics"])
    ]
    assert output.read_text(encoding="utf-8") == "original SQL\n"


def test_emit_sql_json_ir_error_does_not_write_or_call_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "ir-error.pietto", SOURCE)
    output = tmp_path / "ir-error.sql"
    diagnostic = _diagnostic(path, "PIE-I1000", "missing semantic fact")
    monkeypatch.setattr(
        cli.ir_api,
        "build_ir",
        lambda script, model: IrResult(ir=None, diagnostics=(diagnostic,)),
    )

    def unexpected_emit(script_ir: object) -> object:
        del script_ir
        raise AssertionError("SQL backend must not run after IR errors")

    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_emit)

    assert _emit_json_output(path, output) == 1
    result = _read_json_document(capsys)

    assert result["output"] == {"path": str(output), "written": False}
    assert cast(list[dict[str, object]], result["diagnostics"])[0]["code"] == (
        "PIE-I1000"
    )
    assert not output.exists()


def test_emit_sql_json_backend_error_preserves_artifacts_and_old_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "backend-error.pietto", SOURCE)
    output = _write(tmp_path, "backend-error.sql", "original SQL\n")
    artifact = _artifact("partial", "SELECT 1")
    diagnostic = _diagnostic(path, "PIE-B1000", "unsupported backend case")
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(
            artifacts=(artifact,),
            diagnostics=(diagnostic,),
        ),
    )

    assert _emit_json_output(path, output) == 1
    result = _read_json_document(capsys)

    assert result["ok"] is False
    assert result["cli_errors"] == []
    assert result["output"] == {"path": str(output), "written": False}
    assert cast(list[dict[str, object]], result["artifacts"])[0]["sql"] == "SELECT 1"
    assert output.read_text(encoding="utf-8") == "original SQL\n"


def test_emit_sql_json_file_read_error_reports_unwritten_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "missing.pietto"
    output = tmp_path / "out.sql"

    assert _emit_json_output(path, output) == 2
    result = _read_json_document(capsys)

    assert result["output"] == {"path": str(output), "written": False}
    error = cast(list[dict[str, object]], result["cli_errors"])[0]
    assert error["kind"] == "file_read"
    assert error["message"] == "No such file or directory (errno 2)"
    assert not output.exists()


def test_emit_sql_json_unsupported_dialect_reports_unwritten_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pietto", SOURCE)
    output = tmp_path / "out.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "sqlite",
                "--format=json",
                "--output",
                str(output),
            ]
        )
        == 2
    )
    result = _read_json_document(capsys)

    assert result["dialect"] == "sqlite"
    assert result["output"] == {"path": str(output), "written": False}
    error = cast(list[dict[str, object]], result["cli_errors"])[0]
    assert error["kind"] == "unsupported_dialect"
    assert not output.exists()


def test_emit_sql_json_usage_error_reports_unwritten_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pietto", SOURCE)
    output = tmp_path / "out.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--format=json",
                "--output",
                str(output),
            ]
        )
        == 2
    )
    result = _read_json_document(capsys)

    assert result["output"] == {"path": str(output), "written": False}
    assert cast(list[dict[str, object]], result["cli_errors"])[0]["kind"] == ("usage")
    assert not output.exists()


def test_emit_sql_json_same_input_output_is_rejected_before_compilation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", RELATION)
    original = path.read_bytes()

    def unexpected_parse(checked_path: Path) -> object:
        del checked_path
        raise AssertionError("invalid output path must stop before compilation")

    monkeypatch.setattr(cli.parser_api, "parse_file", unexpected_parse)

    assert _emit_json_output(path, path) == 2
    result = _read_json_document(capsys)

    assert result["output"] == {"path": str(path), "written": False}
    assert cast(list[dict[str, object]], result["cli_errors"])[0]["kind"] == (
        "output_path"
    )
    assert path.read_bytes() == original


def test_emit_sql_json_hardlink_output_is_rejected_without_truncation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", RELATION)
    output = tmp_path / "hardlink.sql"
    os.link(path, output)
    original = path.read_bytes()

    assert _emit_json_output(path, output) == 2
    result = _read_json_document(capsys)

    assert result["output"] == {"path": str(output), "written": False}
    assert cast(list[dict[str, object]], result["cli_errors"])[0]["kind"] == (
        "output_path"
    )
    assert path.read_bytes() == original
    assert output.read_bytes() == original


def test_emit_sql_json_symlink_output_is_rejected_and_target_is_unchanged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", RELATION)
    target = _write(tmp_path, "target.sql", "original SQL\n")
    output = tmp_path / "output.sql"
    output.symlink_to(target)

    assert _emit_json_output(path, output) == 2
    result = _read_json_document(capsys)

    assert result["output"] == {"path": str(output), "written": False}
    assert cast(list[dict[str, object]], result["cli_errors"])[0]["kind"] == (
        "output_path"
    )
    assert output.is_symlink()
    assert target.read_text(encoding="utf-8") == "original SQL\n"


@pytest.mark.parametrize(
    ("destination", "reason"),
    [
        ("missing/out.sql", "No such file or directory"),
        ("existing-directory", "Is a directory"),
        # A regular-file parent is a write failure after compilation, not an
        # output-path safety failure, on every platform.
        (
            "plain-file/out.sql",
            "No such file or directory"
            if sys.platform == "win32"
            else "Not a directory",
        ),
    ],
)
def test_emit_sql_json_output_write_error_reports_only_the_user_path(
    destination: str,
    reason: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(tmp_path, "input.pietto", RELATION)
    (tmp_path / "existing-directory").mkdir()
    _write(tmp_path, "plain-file", "plain\n")
    monkeypatch.chdir(tmp_path)
    output = Path(destination)

    assert _emit_json_output(Path("input.pietto"), output) == 2
    result = _read_json_document(capsys)

    assert result["output"] == {"path": str(output), "written": False}
    error = cast(list[dict[str, object]], result["cli_errors"])[0]
    assert error["kind"] == "output_write"
    assert error["path"] == str(output)
    assert str(error["message"]).startswith(f"{reason} (errno ")
    document = json.dumps(result)
    assert ".tmp" not in document
    assert json.dumps(str(tmp_path))[1:-1] not in document
    assert cast(list[dict[str, object]], result["artifacts"])[0]["sql"] == (
        EXPECTED_SQL.removesuffix("\n")
    )
    assert not (tmp_path / "missing").exists()
    assert (tmp_path / "existing-directory").is_dir()
    assert (tmp_path / "plain-file").read_text(encoding="utf-8") == "plain\n"
    assert not tuple(tmp_path.rglob("*.tmp"))


@pytest.mark.parametrize("presentation", ["text", "json"])
@pytest.mark.parametrize(
    ("case", "output"),
    [
        ("file-parent", "o.sql"),
        ("unsearchable-parent", "o.sql"),
        # The output inside the same uninspectable directory cannot be
        # inspected either; that does not take precedence over file_read.
        ("unsearchable-parent", "locked/o.sql"),
        ("link-loop", "o.sql"),
    ],
)
def test_uninspectable_input_is_a_file_read_error_with_output(
    case: str,
    presentation: str,
    output: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    locked = tmp_path / "locked"
    if case == "file-parent":
        _write(tmp_path, "plain-file", "plain\n")
        source = Path("plain-file/input.pietto")
        reason = (
            "No such file or directory (errno 2)"
            if sys.platform == "win32"
            else "Not a directory (errno 20)"
        )
    elif case == "unsearchable-parent":
        if sys.platform == "win32" or os.geteuid() == 0:
            pytest.skip("needs POSIX directory permissions that bind the user")
        locked.mkdir()
        _write(locked, "input.pietto", RELATION)
        locked.chmod(0)
        source = Path("locked/input.pietto")
        reason = f"Permission denied (errno {errno.EACCES})"
    else:
        if sys.platform == "win32":
            pytest.skip("symbolic links need extra privileges on Windows")
        (tmp_path / "loop-a").symlink_to("loop-b")
        (tmp_path / "loop-b").symlink_to("loop-a")
        source = Path("loop-a")
        reason = f"Too many levels of symbolic links (errno {errno.ELOOP})"
    arguments = ["emit-sql", str(source), "--dialect", "postgres", "--output", output]
    if presentation == "json":
        arguments.extend(["--format", "json"])

    try:
        assert cli.main(arguments) == 2
    finally:
        if locked.exists():
            locked.chmod(0o700)

    captured = capsys.readouterr()
    if presentation == "json":
        result = _parse_json_document(captured.out, captured.err)
        assert result["cli_errors"] == [
            {"kind": "file_read", "message": reason, "path": str(source)}
        ]
        assert result["output"] == {"path": str(Path(output)), "written": False}
    else:
        assert captured == ("", f"{source}: error: {reason}\n")
    assert not (tmp_path / output).exists()


@pytest.mark.parametrize("case", ["unsearchable-parent", "unwritable-parent"])
def test_unreachable_output_parent_is_an_output_write_error_after_compilation(
    case: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if sys.platform == "win32" or os.geteuid() == 0:
        pytest.skip("needs POSIX directory permissions that bind the user")
    monkeypatch.chdir(tmp_path)
    _write(tmp_path, "input.pietto", RELATION)
    parent = tmp_path / "parent"
    parent.mkdir()
    parent.chmod(0 if case == "unsearchable-parent" else 0o500)
    output = Path("parent/o.sql")

    try:
        assert _emit_json_output(Path("input.pietto"), output) == 2
    finally:
        parent.chmod(0o700)

    result = _read_json_document(capsys)
    assert result["cli_errors"] == [
        {
            "kind": "output_write",
            "message": f"Permission denied (errno {errno.EACCES})",
            "path": str(output),
        }
    ]
    assert result["output"] == {"path": str(output), "written": False}
    assert cast(list[dict[str, object]], result["artifacts"])[0]["sql"] == (
        EXPECTED_SQL.removesuffix("\n")
    )


@pytest.mark.skipif(
    sys.platform == "win32", reason="symbolic links need extra privileges on Windows"
)
@pytest.mark.parametrize("presentation", ["text", "json"])
def test_output_parent_link_loop_is_an_output_write_error_after_compilation(
    presentation: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write(
        tmp_path,
        "input.pietto",
        # The PIE-S2303 warning of a source without a shape shows that
        # compilation ran before the write failed.
        RELATION + 'source raw = postgres.table("raw")\n',
    )
    (tmp_path / "loop-a").symlink_to("loop-b")
    (tmp_path / "loop-b").symlink_to("loop-a")
    monkeypatch.chdir(tmp_path)
    output = Path("loop-a/out.sql")
    reason = f"Too many levels of symbolic links (errno {errno.ELOOP})"
    arguments = ["emit-sql", "input.pietto", "--dialect", "postgres"]
    arguments.extend(["--output", str(output)])
    if presentation == "json":
        arguments.extend(["--format", "json"])

    assert cli.main(arguments) == 2

    captured = capsys.readouterr()
    if presentation == "json":
        result = _parse_json_document(captured.out, captured.err)
        assert result["cli_errors"] == [
            {"kind": "output_write", "message": reason, "path": str(output)}
        ]
        assert [
            diagnostic["code"]
            for diagnostic in cast(list[dict[str, object]], result["diagnostics"])
        ] == ["PIE-S2303"]
        assert cast(list[dict[str, object]], result["artifacts"])[0]["sql"] == (
            EXPECTED_SQL.removesuffix("\n")
        )
        assert result["output"] == {"path": str(output), "written": False}
    else:
        assert captured.out == ""
        warning, write_error = captured.err.splitlines()
        assert "PIE-S2303 warning:" in warning
        assert write_error == f"{output}: error: {reason}"


@pytest.mark.parametrize("dialect", ["postgres", "mysql"])
@pytest.mark.parametrize("existing", [False, True])
def test_emit_sql_json_zero_artifacts_refuse_the_output_file(
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
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                dialect,
                "--format",
                "json",
                "--output",
                str(output),
            ]
        )
        == 2
    )
    result = _read_json_document(capsys)

    assert result == {
        "schema_version": 1,
        "command": "emit-sql",
        "ok": False,
        "path": str(path),
        "dialect": dialect,
        "diagnostics": [],
        "cli_errors": [
            {
                "kind": "output_write",
                "message": (
                    "no SQL artifacts to write; the output file was not changed"
                ),
                "path": str(output),
            }
        ],
        "artifacts": [],
        "output": {"path": str(output), "written": False},
    }
    if existing:
        assert output.read_text(encoding="utf-8") == "original SQL\n"
    else:
        assert not output.exists()
    assert not tuple(tmp_path.glob("*.tmp"))


def test_emit_sql_json_replace_failure_preserves_old_output_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", RELATION)
    output = _write(tmp_path, "out.sql", "original SQL\n")

    def fail_replace(source: Path, destination: Path) -> None:
        del source, destination
        raise PermissionError("replacement denied")

    monkeypatch.setattr(cli.os, "replace", fail_replace)

    assert _emit_json_output(path, output) == 2
    result = _read_json_document(capsys)

    assert result["ok"] is False
    assert result["output"] == {"path": str(output), "written": False}
    assert cast(list[dict[str, object]], result["cli_errors"]) == [
        {"kind": "output_write", "message": "Permission denied", "path": str(output)}
    ]
    assert cast(list[object], result["artifacts"])
    assert output.read_text(encoding="utf-8") == "original SQL\n"
    assert not tuple(tmp_path.glob("*.tmp"))


def test_emit_sql_text_output_and_check_json_remain_unchanged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", RELATION)
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
    text = capsys.readouterr()
    assert text.out == ""
    assert text.err == ""
    assert output.read_text(encoding="utf-8") == EXPECTED_SQL

    assert cli.main(["check", str(path), "--format=json"]) == 0
    checked = _read_json_document(capsys)
    assert checked["command"] == "check"
    assert checked["ok"] is True


def _emit_json_output(path: Path, output: Path) -> int:
    return cli.main(
        [
            "emit-sql",
            str(path),
            "--dialect",
            "postgres",
            "--format=json",
            "--output",
            str(output),
        ]
    )


def _read_json_document(
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    captured = capsys.readouterr()
    return _parse_json_document(captured.out, captured.err)


def _parse_json_document(stdout: str, stderr: str) -> dict[str, object]:
    assert stderr == ""
    assert stdout.startswith("{")
    assert stdout.endswith("}\n")
    assert not stdout.endswith("\n\n")
    result = json.loads(stdout)
    assert isinstance(result, dict)
    return cast(dict[str, object], result)


def _diagnostic(path: Path, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(path=str(path), line=1, column=1),
    )


def _artifact(name: str, sql: str) -> SqlArtifact:
    return SqlArtifact(
        name=name,
        kind=SqlArtifactKind.RELATION,
        sql=sql,
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
