from __future__ import annotations

import os
from pathlib import Path

import pytest

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
    path = _write(tmp_path, "same-file.pie", SOURCE)
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
    path = _write(tmp_path, "input.pie", SOURCE)
    output = tmp_path / "hard-link.pie"
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
    path = _write(tmp_path, "input.pie", SOURCE)
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
    path = _write(tmp_path, "input.pie", SOURCE)
    output = _write(tmp_path, "output.sql", "stale SQL\n")

    assert _emit(path, output) == 0

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert output.read_text(encoding="utf-8") == (
        'SELECT\n    "email" AS "email"\nFROM "users"\n'
    )
    assert not tuple(tmp_path.glob(".output.sql.*.tmp"))


def test_atomic_replace_failure_preserves_existing_output_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pie", SOURCE)
    output = _write(tmp_path, "output.sql", "original SQL\n")

    def fail_replace(source: Path, destination: Path) -> None:
        del source, destination
        raise PermissionError("replacement denied")

    monkeypatch.setattr(cli.os, "replace", fail_replace)

    assert _emit(path, output) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "replacement denied" in captured.err
    assert output.read_text(encoding="utf-8") == "original SQL\n"
    assert not tuple(tmp_path.glob(".output.sql.*.tmp"))


def test_backend_error_does_not_truncate_existing_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pie", SOURCE)
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
    path = _write(tmp_path, "forged\nPIE-S9999 error.pie", "type = Int\n")

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
    path = tmp_path / "missing\nforged-error.pie"

    assert cli.main(["check", str(path)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "\\nforged-error.pie" in captured.err
    assert "\nforged-error.pie" not in captured.err
    assert len(captured.err.splitlines()) == 1


def test_escape_in_path_is_not_emitted_as_raw_ansi(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "color\x1b[31m.pie", "shape User {\n")

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
            path="bad\npath\x1b.pie",
            line=1,
            column=2,
        ),
    )

    cli._render_diagnostics((diagnostic,), fallback_path=Path("fallback.pie"))

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "bad\\npath\\x1b.pie:1:2 PIE-P1000 error: first\\nsecond\\r\\t\\x1b\\x00\\x7f\n"
    )


def test_success_path_with_newline_is_escaped_on_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid\nname.pie", "shape User:\n    id: UUID not null\n")

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {str(path).replace(chr(10), r'\n')}\n"
    assert len(captured.out.splitlines()) == 1
    assert captured.err == ""


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
