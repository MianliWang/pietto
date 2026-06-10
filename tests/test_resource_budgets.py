from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Severity
from pietto.parser_api import parse_file, parse_source

_SOURCE_LIMIT = 1_048_576
_TOKEN_LIMIT = 200_000
_CHECK_KEYS = {
    "schema_version",
    "command",
    "ok",
    "path",
    "diagnostics",
    "cli_errors",
}
_EMIT_KEYS = _CHECK_KEYS | {"dialect", "artifacts", "output"}


def test_parse_source_accepts_exact_utf8_byte_budget() -> None:
    source = "#" + "a" * (_SOURCE_LIMIT - 2) + "\n"

    result = parse_source(source)

    assert result.ast is not None
    assert result.diagnostics == ()


def test_parse_source_rejects_utf8_bytes_over_budget() -> None:
    source = "#" + "雪" * (_SOURCE_LIMIT // 3 + 1)

    result = parse_source(source, path="oversized-unicode.pie")

    assert result.ast is None
    assert len(source) < _SOURCE_LIMIT
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-P1006"
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.location.path == "oversized-unicode.pie"
    assert (diagnostic.location.line, diagnostic.location.column) == (1, 1)


def test_parse_file_rejects_oversized_source_as_parser_diagnostic(
    tmp_path: Path,
) -> None:
    path = tmp_path / "oversized.pie"
    path.write_bytes(b"#" + b"a" * _SOURCE_LIMIT)

    result = parse_file(path)

    assert result.ast is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-P1006"]
    assert result.diagnostics[0].location.path == str(path)


def test_token_budget_stops_at_first_excess_non_eof_token() -> None:
    result = parse_source(
        "+" * (_TOKEN_LIMIT + 1),
        path="too-many-tokens.pie",
    )

    assert result.ast is None
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-P1007"
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.location.path == "too-many-tokens.pie"
    assert (diagnostic.location.line, diagnostic.location.column) == (
        1,
        _TOKEN_LIMIT + 1,
    )


def test_check_text_source_budget_is_diagnostic_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_oversized_source(tmp_path)

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-P1006 error:" in captured.err
    assert "Traceback" not in captured.err


def test_check_json_source_budget_preserves_v1_schema(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_oversized_source(tmp_path)

    assert cli.main(["check", str(path), "--format=json"]) == 1

    result = _read_json_document(capsys)
    assert set(result) == _CHECK_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "check"
    assert result["ok"] is False
    assert result["cli_errors"] == []
    diagnostic = cast(list[dict[str, object]], result["diagnostics"])[0]
    assert diagnostic["code"] == "PIE-P1006"
    assert diagnostic["severity"] == "error"


def test_emit_sql_source_budget_stops_before_later_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_oversized_source(tmp_path)
    _forbid_later_stages(monkeypatch)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-P1006 error:" in captured.err
    assert "Traceback" not in captured.err


def test_emit_sql_output_source_budget_preserves_existing_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_oversized_source(tmp_path)
    output = tmp_path / "out.sql"
    output.write_bytes(b"original SQL\n")

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
    assert "PIE-P1006 error:" in captured.err
    assert output.read_bytes() == b"original SQL\n"


def test_emit_sql_json_source_budget_preserves_v1_and_does_not_create_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write_oversized_source(tmp_path)
    output = tmp_path / "out.sql"
    _forbid_later_stages(monkeypatch)

    assert (
        cli.main(
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
        == 1
    )

    result = _read_json_document(capsys)
    assert set(result) == _EMIT_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is False
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output), "written": False}
    diagnostic = cast(list[dict[str, object]], result["diagnostics"])[0]
    assert diagnostic["code"] == "PIE-P1006"
    assert diagnostic["severity"] == "error"
    assert not output.exists()


def test_emit_sql_json_token_budget_preserves_v1_and_output_safety(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "too-many-tokens.pie"
    path.write_text("+" * (_TOKEN_LIMIT + 1), encoding="utf-8")
    output = tmp_path / "out.sql"
    _forbid_later_stages(monkeypatch)

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(output),
            ]
        )
        == 1
    )

    result = _read_json_document(capsys)
    assert set(result) == _EMIT_KEYS
    assert result["schema_version"] == 1
    assert result["command"] == "emit-sql"
    assert result["ok"] is False
    assert result["cli_errors"] == []
    assert result["artifacts"] == []
    assert result["output"] == {"path": str(output), "written": False}
    diagnostic = cast(list[dict[str, object]], result["diagnostics"])[0]
    assert diagnostic["code"] == "PIE-P1007"
    assert diagnostic["severity"] == "error"
    assert not output.exists()


def _write_oversized_source(tmp_path: Path) -> Path:
    path = tmp_path / "oversized.pie"
    path.write_bytes(b"#" + b"a" * _SOURCE_LIMIT)
    return path


def _forbid_later_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("budget failure must stop later compiler stages")

    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)


def _read_json_document(
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    assert "Traceback" not in captured.out
    return cast(dict[str, object], json.loads(captured.out))
