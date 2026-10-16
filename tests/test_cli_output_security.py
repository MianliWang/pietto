from __future__ import annotations

import errno
import json
import os
import sys
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
def test_source_unicode_controls_are_escaped_in_text_and_parser_messages(
    character: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "controls.pietto", f"{SOURCE}{character}\n")
    escape = f"\\u{ord(character):04x}"

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"Unexpected '{escape}'" in captured.err
    assert character not in captured.err

    # The parser message itself spells the character as an escape, so the
    # JSON message carries that spelling and never the raw control.
    assert cli.main(["check", str(path), "--format", "json"]) == 1
    message = json.loads(capsys.readouterr().out)["diagnostics"][0]["message"]
    assert f"Unexpected '{escape}'" in message and character not in message

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
