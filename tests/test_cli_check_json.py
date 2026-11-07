from __future__ import annotations

import errno
import json
import sys
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.parser_api import ParseResult
from pietto.semantic import CheckMode, SemanticModel, SemanticResult


def test_check_json_valid_file_returns_one_document(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "valid.pietto",
        "shape User:\n    email: Text\n",
    )

    assert cli.main(["check", str(path), "--format", "json"]) == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    assert captured.err == ""
    assert "OK:" not in captured.out
    assert result == {
        "schema_version": 1,
        "command": "check",
        "ok": True,
        "path": str(path),
        "diagnostics": [],
        "cli_errors": [],
    }
    assert "version" not in result


def test_check_json_equals_form_is_supported(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pietto", "")

    assert cli.main(["check", str(path), "--format=json"]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is True


def test_check_json_warning_is_successful_and_structured(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "warning.pietto",
        'shape User:\n    email: Text\nsource raw = postgres.table("raw")\n',
    )

    assert cli.main(["check", str(path), "--format", "json"]) == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.err == ""
    assert result["ok"] is True
    assert [(item["code"], item["severity"]) for item in result["diagnostics"]] == [
        ("PIE-S2303", "warning")
    ]
    assert result["diagnostics"][0]["location"]["path"] == str(path)


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
def test_check_json_compiler_errors_return_one(
    name: str,
    source: str,
    expected_code: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)

    assert cli.main(["check", str(path), "--format", "json"]) == 1

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.err == ""
    assert result["ok"] is False
    assert expected_code in [item["code"] for item in result["diagnostics"]]
    assert result["cli_errors"] == []


def test_check_json_file_read_error_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "missing.pietto"

    assert cli.main(["check", str(path), "--format", "json"]) == 2

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.err == ""
    assert result["ok"] is False
    assert result["diagnostics"] == []
    assert len(result["cli_errors"]) == 1
    error = result["cli_errors"][0]
    assert error["kind"] == "file_read"
    assert error["path"] == str(path)
    assert error["message"] == "No such file or directory (errno 2)"


def test_check_json_directory_input_reported_as_permission_error_is_a_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory = tmp_path / "models"
    directory.mkdir()

    def windows_open(path: Path) -> object:
        # The Windows C runtime reports opening a directory as EACCES.
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(cli.parser_api, "parse_file", windows_open)

    assert cli.main(["check", str(directory), "--format", "json"]) == 2

    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out)["cli_errors"] == [
        {
            "kind": "file_read",
            "message": "Is a directory (errno 13)",
            "path": str(directory),
        }
    ]


@pytest.mark.parametrize(
    "arguments",
    [
        ["check", "--format", "json"],
        ["check", "first.pietto", "second.pietto", "--format=json"],
        ["check", "input.pietto", "--unknown", "--format", "json"],
    ],
)
def test_check_json_command_usage_errors_are_structured(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(arguments) == 2

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.err == ""
    assert result["ok"] is False
    assert result["path"] is None
    assert result["diagnostics"] == []
    assert result["cli_errors"][0]["kind"] == "usage"
    assert result["cli_errors"][0]["path"] is None


def test_invalid_format_remains_plain_argparse_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pietto", "")

    assert cli.main(["check", str(path), "--format", "yaml"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice: 'yaml'" in captured.err


@pytest.mark.parametrize("command", ["check", "explain"])
@pytest.mark.parametrize(
    ("formats", "selected"),
    [
        (["--format", "json", "--format", "text"], "text"),
        (["--format=json", "--format=text"], "text"),
        (["--format", "text", "--format", "json"], "json"),
        (["--format", "json", "--format", "yaml"], None),
        (["--format", "yaml", "--format", "json"], None),
        (["--form", "json"], "json"),
        (["--form=json"], "json"),
        (["--format", "json", "--form", "text"], "text"),
        (["--format", "json", "--form", "yaml"], None),
    ],
)
def test_check_and_explain_last_valid_format_wins(
    command: str,
    formats: list[str],
    selected: str | None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pietto", "shape User:\n    email: Text\n")

    exit_code = cli.main([command, str(path), *formats])

    captured = capsys.readouterr()
    if selected is None:
        assert (exit_code, captured.out) == (2, "")
        assert "invalid choice: 'yaml'" in captured.err
    elif selected == "json":
        assert (exit_code, captured.err) == (0, "")
        assert json.loads(captured.out)["command"] == command
    else:
        assert (exit_code, captured.err) == (0, "")
        assert captured.out.startswith(
            f"OK: {path}\n" if command == "check" else "Semantic Metadata Artifact v1\n"
        )


@pytest.mark.parametrize(
    ("formats", "plain_error"),
    [
        (["--form", "json", "--bogus"], None),
        (["--fo=json", "--check-mode", "bogus"], None),
        (["--format", "json", "--form", "text", "--bogus"], "unrecognized arguments"),
        (["--format", "json", "--format"], "expected one argument"),
    ],
)
def test_check_usage_errors_follow_the_resolved_format(
    formats: list[str],
    plain_error: str | None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pietto", "")

    assert cli.main(["check", str(path), *formats]) == 2

    captured = capsys.readouterr()
    if plain_error is None:
        assert captured.err == ""
        assert json.loads(captured.out)["cli_errors"][0]["kind"] == "usage"
    else:
        assert captured.out == ""
        assert plain_error in captured.err


def test_double_dash_bounds_check_format_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pietto", "")
    monkeypatch.chdir(tmp_path)

    assert cli.main(["--", "check", path.name, "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True

    assert cli.main(["check", "--", "--format=json"]) == 2
    assert capsys.readouterr() == (
        "",
        "--format=json: error: No such file or directory (errno 2)\n",
    )


def test_unidentified_top_level_error_remains_plain_argparse_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["--unknown", "--format", "json"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: pietto" in captured.err


def test_check_json_uses_raw_fields_and_json_encoding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "line\nesc\x1bdel\x7fsnow雪.pietto"
    diagnostic = Diagnostic(
        code="PIE-S2002",
        severity=Severity.ERROR,
        message='quote" slash\\ line\nesc\x1bnul\x00del\x7fsnow雪',
        location=SourceLocation(path=None, line=1, column=2),
    )
    parse_result = ParseResult(
        ast=None,
        diagnostics=(diagnostic,),
    )
    monkeypatch.setattr(cli.parser_api, "parse_file", lambda checked: parse_result)

    assert cli.main(["check", str(path), "--format", "json"]) == 1

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.err == ""
    assert "\x1b" not in captured.out
    assert "\x00" not in captured.out
    assert "\x7f" not in captured.out
    assert "雪" not in captured.out
    assert result["path"] == str(path)
    assert result["diagnostics"][0]["message"] == diagnostic.message
    assert result["diagnostics"][0]["location"]["path"] == str(path)


@pytest.mark.parametrize(
    ("name", "source", "message_fragment"),
    [
        (
            "huge-integer.pietto",
            "type Huge = Int(max = " + "9" * 5000 + ")\n",
            "maximum supported length",
        ),
        (
            "deep-unary.pietto",
            "derive deep() -> Int:\n    " + "+" * 1500 + "1\n",
            "recursion limit",
        ),
    ],
)
def test_check_json_parser_containment_has_no_traceback(
    name: str,
    source: str,
    message_fragment: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)

    assert cli.main(["check", str(path), "--format", "json"]) == 1

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.err == ""
    assert "Traceback" not in captured.out
    assert message_fragment in result["diagnostics"][0]["message"]


def test_check_json_semantic_recursion_has_no_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    aliases = [f"type Alias{index} = Alias{index + 1}\n" for index in range(1399)]
    aliases.append("type Alias1399 = Int\n")
    path = _write(tmp_path, "deep-aliases.pietto", "".join(aliases))

    assert cli.main(["check", str(path), "--format", "json"]) == 1

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.err == ""
    assert "Traceback" not in captured.out
    assert result["diagnostics"][0]["code"] == "PIE-S2006"


def test_check_json_stops_before_ir_and_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pietto", "")

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must stop after semantic analysis")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True


def test_check_json_preserves_parser_then_semantic_diagnostic_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "ordered.pietto", "")
    parser_warning = Diagnostic(
        code="PIE-P1000",
        severity=Severity.WARNING,
        message="parser warning",
        location=SourceLocation(path=None, line=1, column=1),
    )
    semantic_warning = Diagnostic(
        code="PIE-S2005",
        severity=Severity.WARNING,
        message="semantic warning",
        location=SourceLocation(path=None, line=2, column=1),
    )
    real_parse = cli.parser_api.parse_file(path)
    assert real_parse.ast is not None
    monkeypatch.setattr(
        cli.parser_api,
        "parse_file",
        lambda checked: ParseResult(
            ast=real_parse.ast,
            diagnostics=(parser_warning,),
        ),
    )
    monkeypatch.setattr(
        cli.semantic_api,
        "analyze",
        lambda script, mode_override: SemanticResult(
            model=SemanticModel(mode=CheckMode.CHECKED),
            diagnostics=(semantic_warning,),
        ),
    )

    assert cli.main(["check", str(path), "--format", "json"]) == 0

    result = json.loads(capsys.readouterr().out)
    assert [item["code"] for item in result["diagnostics"]] == [
        "PIE-P1000",
        "PIE-S2005",
    ]


def test_explicit_text_and_default_check_behavior_are_unchanged(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pietto", "")

    assert cli.main(["check", str(path), "--format", "text"]) == 0
    explicit = capsys.readouterr()
    assert explicit.out == f"OK: {path}\n"
    assert explicit.err == ""

    assert cli.main(["check", str(path)]) == 0
    default = capsys.readouterr()
    assert default.out == f"OK: {path}\n"
    assert default.err == ""


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
        ("valid.pietto", "", 0, True, None),
        (
            "warning.pietto",
            'source raw = postgres.table("raw")\n',
            0,
            True,
            "PIE-S2303",
        ),
        ("parser.pietto", "shape User {\n", 1, False, "PIE-P1005"),
        (
            "semantic.pietto",
            "shape User:\n    email: MissingType\n",
            1,
            False,
            "PIE-S2002",
        ),
    ],
)
def test_check_json_document_schema_exit_and_ok(
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
def test_check_json_cli_errors_are_structured(
    case: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if case == "file_read":
        path = tmp_path / "missing.pietto"
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


def test_check_json_location_can_be_null(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "location-null.pietto"
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


def test_check_json_controls_and_unicode_round_trip_as_raw_values(
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
            "huge-integer.pietto",
            "type Huge = Int(max = " + "9" * 5000 + ")\n",
            "PIE-P1000",
        ),
        (
            "deep-parser.pietto",
            "derive deep() -> Int:\n    " + "+" * 1500 + "1\n",
            "PIE-P1000",
        ),
        (
            "deep-semantic.pietto",
            "".join(
                [
                    *(
                        f"type Alias{index} = Alias{index + 1}\n"
                        for index in range(1399)
                    ),
                    "type Alias1399 = Int\n",
                ]
            ),
            "PIE-S2006",
        ),
    ],
)
def test_check_json_resource_failures_remain_structured(
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


def test_check_json_parser_error_short_circuits_later_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "parser-error.pietto", "shape User {\n")

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("parser errors must stop later compiler stages")

    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path), "--format=json"]) == 1
    assert _read_json_document(capsys)["ok"] is False


def test_check_json_semantic_error_never_enters_ir_or_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "semantic-error.pietto",
        "shape User:\n    email: MissingType\n",
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must stop after semantic analysis")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path), "--format=json"]) == 1
    assert _read_json_document(capsys)["ok"] is False


@pytest.mark.skipif(sys.platform == "win32", reason="needs control characters in names")
def test_check_json_text_modes_keep_plain_text_escaping(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid\nname.pietto", "")
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
