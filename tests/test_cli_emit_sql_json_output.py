from __future__ import annotations

import json
import os
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import IrResult
from pietto.sql import SqlArtifact, SqlArtifactKind, SqlResult

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
)
RELATION = (
    SOURCE + "table active_users:\n"
    "    from users\n"
    "    where active == true\n"
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
        'source users: User is postgres.table("users")\n'
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
            "shape User:\n    email: MissingType not null\n",
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


def test_emit_sql_json_missing_parent_reports_output_write_with_artifacts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pietto", RELATION)
    output = tmp_path / "missing" / "out.sql"

    assert _emit_json_output(path, output) == 2
    result = _read_json_document(capsys)

    assert result["output"] == {"path": str(output), "written": False}
    assert cast(list[dict[str, object]], result["cli_errors"])[0]["kind"] == (
        "output_write"
    )
    assert cast(list[object], result["artifacts"])
    assert not output.exists()


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
    assert cast(list[dict[str, object]], result["cli_errors"])[0]["kind"] == (
        "output_write"
    )
    assert cast(list[object], result["artifacts"])
    assert output.read_text(encoding="utf-8") == "original SQL\n"
    assert not tuple(tmp_path.glob(".out.sql.*.tmp"))


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
