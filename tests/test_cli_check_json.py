from __future__ import annotations

import json
from pathlib import Path

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
        "valid.pie",
        "shape User:\n    email: Text not null\n",
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
    path = _write(tmp_path, "valid.pie", "")

    assert cli.main(["check", str(path), "--format=json"]) == 0

    result = json.loads(capsys.readouterr().out)
    assert result["ok"] is True


def test_check_json_warning_is_successful_and_structured(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "warning.pie", "shape User:\n    email: Text\n")

    assert cli.main(["check", str(path), "--format", "json"]) == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert captured.err == ""
    assert result["ok"] is True
    assert [item["severity"] for item in result["diagnostics"]] == ["warning"]
    assert result["diagnostics"][0]["location"]["path"] == str(path)


@pytest.mark.parametrize(
    ("name", "source", "expected_code"),
    [
        ("parser.pie", "shape User {\n", "PIE-P1005"),
        (
            "semantic.pie",
            "shape User:\n    email: MissingType not null\n",
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
    path = tmp_path / "missing.pie"

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
    assert "No such file or directory" in error["message"]


@pytest.mark.parametrize(
    "arguments",
    [
        ["check", "--format", "json"],
        ["check", "first.pie", "second.pie", "--format=json"],
        ["check", "input.pie", "--unknown", "--format", "json"],
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
    path = _write(tmp_path, "valid.pie", "")

    assert cli.main(["check", str(path), "--format", "yaml"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice: 'yaml'" in captured.err


def test_unidentified_top_level_error_remains_plain_argparse_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["--unknown", "--format", "json"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: pietto" in captured.err


def test_emit_sql_json_is_not_implemented_in_this_slice(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pie", "")

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "unrecognized arguments: --format json" in captured.err


def test_check_json_uses_raw_fields_and_json_encoding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "line\nesc\x1bdel\x7fsnow雪.pie"
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
            "huge-integer.pie",
            "type Huge = Int(max = " + "9" * 5000 + ") not null\n",
            "maximum supported length",
        ),
        (
            "deep-unary.pie",
            "derive deep() -> Int not null:\n    " + "+" * 1500 + "1\n",
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
    aliases = [
        f"type Alias{index} = Alias{index + 1} not null\n" for index in range(1399)
    ]
    aliases.append("type Alias1399 = Int not null\n")
    path = _write(tmp_path, "deep-aliases.pie", "".join(aliases))

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
    path = _write(tmp_path, "valid.pie", "")

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
    path = _write(tmp_path, "ordered.pie", "")
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
        lambda script: SemanticResult(
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
    path = _write(tmp_path, "valid.pie", "")

    assert cli.main(["check", str(path), "--format", "text"]) == 0
    explicit = capsys.readouterr()
    assert explicit.out == f"OK: {path}\n"
    assert explicit.err == ""

    assert cli.main(["check", str(path)]) == 0
    default = capsys.readouterr()
    assert default.out == f"OK: {path}\n"
    assert default.err == ""


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
