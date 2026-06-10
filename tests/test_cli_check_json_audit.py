from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.parser_api import ParseResult

_CHECK_KEYS = {
    "schema_version",
    "command",
    "ok",
    "path",
    "diagnostics",
    "cli_errors",
}
_DIAGNOSTIC_KEYS = {
    "code",
    "severity",
    "message",
    "location",
    "suggestion",
}
_LOCATION_KEYS = {
    "path",
    "line",
    "column",
    "end_line",
    "end_column",
}
_CLI_ERROR_KEYS = {"kind", "message", "path"}


@pytest.mark.parametrize(
    ("name", "source", "expected_exit", "expected_ok", "expected_code"),
    [
        ("valid.pie", "", 0, True, None),
        (
            "warning.pie",
            "shape User:\n    email: Text\n",
            0,
            True,
            "PIE-S2005",
        ),
        ("parser.pie", "shape User {\n", 1, False, "PIE-P1005"),
        (
            "semantic.pie",
            "shape User:\n    email: MissingType not null\n",
            1,
            False,
            "PIE-S2002",
        ),
    ],
)
def test_check_json_audit_document_schema_exit_and_ok(
    name: str,
    source: str,
    expected_exit: int,
    expected_ok: bool,
    expected_code: str | None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)

    exit_code = cli.main(["check", str(path), "--format", "json"])
    result = _read_json_document(capsys)

    assert exit_code == expected_exit
    assert set(result) == _CHECK_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "check"
    assert result["ok"] is expected_ok
    assert result["path"] == str(path)
    assert result["cli_errors"] == []
    assert "version" not in result
    assert "package_version" not in result

    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    if expected_code is None:
        assert diagnostics == []
        return

    diagnostic = next(item for item in diagnostics if item["code"] == expected_code)
    assert set(diagnostic) == _DIAGNOSTIC_KEYS
    assert diagnostic["severity"] in {"error", "warning", "info"}
    assert diagnostic["severity"] == str(diagnostic["severity"]).lower()
    assert diagnostic["suggestion"] is None or isinstance(diagnostic["suggestion"], str)
    location = cast(dict[str, object], diagnostic["location"])
    assert set(location) == _LOCATION_KEYS
    assert location["path"] == str(path)


@pytest.mark.parametrize("case", ["file_read", "usage"])
def test_check_json_audit_cli_errors_are_structured(
    case: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if case == "file_read":
        path = tmp_path / "missing.pie"
        arguments = ["check", str(path), "--format=json"]
        expected_path: str | None = str(path)
    else:
        arguments = ["check", "--format", "json"]
        expected_path = None

    assert cli.main(arguments) == 2
    result = _read_json_document(capsys)

    assert set(result) == _CHECK_KEYS
    assert result["ok"] is False
    assert result["diagnostics"] == []
    errors = cast(list[dict[str, object]], result["cli_errors"])
    assert len(errors) == 1
    assert set(errors[0]) == _CLI_ERROR_KEYS
    assert errors[0]["kind"] == case
    assert errors[0]["path"] == expected_path


def test_check_json_audit_location_can_be_null(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "location-null.pie"
    diagnostic = Diagnostic(
        code="PIE-P1000",
        severity=Severity.ERROR,
        message="location unavailable",
        location=cast(SourceLocation, None),
    )
    monkeypatch.setattr(
        cli.parser_api,
        "parse_file",
        lambda checked: ParseResult(ast=None, diagnostics=(diagnostic,)),
    )

    assert cli.main(["check", str(path), "--format=json"]) == 1
    result = _read_json_document(capsys)

    serialized = cast(list[dict[str, object]], result["diagnostics"])[0]
    assert set(serialized) == _DIAGNOSTIC_KEYS
    assert serialized["location"] is None


def test_check_json_audit_controls_and_unicode_round_trip_as_raw_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    unsafe = 'line\nquote"slash\\esc\x1bnul\x00del\x7funicode雪'
    path_text = str(tmp_path / unsafe)
    diagnostic = Diagnostic(
        code="PIE-P1000",
        severity=Severity.ERROR,
        message=unsafe,
        location=SourceLocation(path=None, line=1, column=1),
    )
    monkeypatch.setattr(
        cli.parser_api,
        "parse_file",
        lambda checked: ParseResult(ast=None, diagnostics=(diagnostic,)),
    )

    assert cli.main(["check", path_text, "--format=json"]) == 1
    captured = capsys.readouterr()
    result = _parse_json_document(captured.out, captured.err)

    assert "\x1b" not in captured.out
    assert "\x00" not in captured.out
    assert "\x7f" not in captured.out
    assert "雪" not in captured.out
    assert result["path"] == path_text
    serialized = cast(list[dict[str, object]], result["diagnostics"])[0]
    assert serialized["message"] == unsafe
    assert serialized["message"] != cli._escape_cli_text(unsafe)
    assert serialized["suggestion"] is None
    location = cast(dict[str, object], serialized["location"])
    assert location["path"] == path_text
    assert location["end_line"] is None
    assert location["end_column"] is None


@pytest.mark.parametrize(
    ("name", "source", "expected_code"),
    [
        (
            "huge-integer.pie",
            "type Huge = Int(max = " + "9" * 5000 + ") not null\n",
            "PIE-P1000",
        ),
        (
            "deep-parser.pie",
            "derive deep() -> Int not null:\n    " + "+" * 1500 + "1\n",
            "PIE-P1000",
        ),
        (
            "deep-semantic.pie",
            "".join(
                [
                    *(
                        f"type Alias{index} = Alias{index + 1} not null\n"
                        for index in range(1399)
                    ),
                    "type Alias1399 = Int not null\n",
                ]
            ),
            "PIE-S2006",
        ),
    ],
)
def test_check_json_audit_phase_5_5_failures_remain_structured(
    name: str,
    source: str,
    expected_code: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)

    assert cli.main(["check", str(path), "--format=json"]) == 1
    captured = capsys.readouterr()
    result = _parse_json_document(captured.out, captured.err)

    assert "Traceback" not in captured.out
    assert "RecursionError" not in captured.out
    assert "ValueError" not in captured.out
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert diagnostics[0]["code"] == expected_code


def test_check_json_audit_parser_error_short_circuits_later_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "parser-error.pie", "shape User {\n")

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("parser errors must stop later compiler stages")

    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path), "--format=json"]) == 1
    assert _read_json_document(capsys)["ok"] is False


def test_check_json_audit_semantic_error_never_enters_ir_or_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "semantic-error.pie",
        "shape User:\n    email: MissingType not null\n",
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must stop after semantic analysis")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path), "--format=json"]) == 1
    assert _read_json_document(capsys)["ok"] is False


def test_check_json_audit_text_modes_keep_plain_text_escaping(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid\nname.pie", "")
    escaped_path = str(path).replace("\n", r"\n")

    assert cli.main(["check", str(path)]) == 0
    default = capsys.readouterr()
    assert default.out == f"OK: {escaped_path}\n"
    assert default.err == ""

    assert cli.main(["check", str(path), "--format", "text"]) == 0
    explicit = capsys.readouterr()
    assert explicit.out == f"OK: {escaped_path}\n"
    assert explicit.err == ""

    assert cli.main(["check", str(path), "--format", "yaml"]) == 2
    invalid = capsys.readouterr()
    assert invalid.out == ""
    assert "invalid choice: 'yaml'" in invalid.err


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
    assert "OK:" not in stdout
    result = json.loads(stdout)
    assert isinstance(result, dict)
    return cast(dict[str, object], result)


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
