from __future__ import annotations

from pathlib import Path

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation


def test_parser_diagnostic_uses_stable_plain_text_format(
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = _diagnostic(
        code="PIE-P1000",
        severity=Severity.ERROR,
        message="unexpected token",
        path="parser.pie",
        line=3,
        column=7,
    )

    cli._render_diagnostics((diagnostic,), fallback_path=Path("fallback.pie"))

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "parser.pie:3:7 PIE-P1000 error: unexpected token\n"


def test_semantic_diagnostic_uses_stable_plain_text_format(
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = _diagnostic(
        code="PIE-S2002",
        severity=Severity.ERROR,
        message="Unknown type: Missing",
        path="semantic.pie",
        line=5,
        column=12,
    )

    cli._render_diagnostics((diagnostic,), fallback_path=Path("fallback.pie"))

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "semantic.pie:5:12 PIE-S2002 error: Unknown type: Missing\n"


def test_diagnostic_without_path_uses_checked_file_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = _diagnostic(
        code="PIE-S2005",
        severity=Severity.WARNING,
        message="Implicit nullability",
        path=None,
        line=2,
        column=9,
    )

    cli._render_diagnostics((diagnostic,), fallback_path=Path("checked.pie"))

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ("checked.pie:2:9 PIE-S2005 warning: Implicit nullability\n")


def test_multiple_diagnostics_preserve_input_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostics = (
        _diagnostic(
            code="PIE-S2005",
            severity=Severity.WARNING,
            message="first",
            path="ordered.pie",
            line=8,
            column=4,
        ),
        _diagnostic(
            code="PIE-S2002",
            severity=Severity.ERROR,
            message="second",
            path="ordered.pie",
            line=2,
            column=1,
        ),
        _diagnostic(
            code="PIE-S2501",
            severity=Severity.ERROR,
            message="third",
            path="ordered.pie",
            line=5,
            column=3,
        ),
    )

    cli._render_diagnostics(diagnostics, fallback_path=Path("fallback.pie"))

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.splitlines() == [
        "ordered.pie:8:4 PIE-S2005 warning: first",
        "ordered.pie:2:1 PIE-S2002 error: second",
        "ordered.pie:5:3 PIE-S2501 error: third",
    ]


def test_warning_only_check_writes_diagnostic_to_stderr_and_succeeds(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "warning.pie", "shape User:\n    email: Text\n")

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err.startswith(f"{path}:2:12 PIE-S2005 warning:")


def test_multiple_check_diagnostics_remain_ordered_and_off_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "multiple.pie",
        "shape User:\n"
        "    first: MissingOne not null\n"
        "    second: MissingTwo not null\n",
    )

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    lines = captured.err.splitlines()
    assert [line.split()[1] for line in lines] == ["PIE-S2002", "PIE-S2002"]
    assert "Unknown type: MissingOne" in lines[0]
    assert "Unknown type: MissingTwo" in lines[1]


def test_valid_check_keeps_stderr_empty(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "valid.pie",
        "shape User:\n    email: Text not null\n",
    )

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


def test_usage_and_file_errors_keep_exit_code_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["check"]) == 2
    assert "the following arguments are required: path" in capsys.readouterr().err

    missing = tmp_path / "missing.pie"
    assert cli.main(["check", str(missing)]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(missing) in captured.err


def _diagnostic(
    *,
    code: str,
    severity: Severity,
    message: str,
    path: str | None,
    line: int,
    column: int,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        location=SourceLocation(
            path=path,
            line=line,
            column=column,
        ),
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
