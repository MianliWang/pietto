from __future__ import annotations

from pathlib import Path

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


def test_emit_sql_valid_file_prints_postgres_sql(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "active_users.pie",
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    where active == true\n"
        "    select:\n"
        "        id\n"
        "        email\n",
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.out == (
        "SELECT\n"
        '    "id" AS "id",\n'
        '    "email" AS "email"\n'
        'FROM "users"\n'
        'WHERE "active" = TRUE\n'
    )
    assert captured.err == ""


def test_emit_sql_preserves_multiple_artifact_order(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "relations.pie",
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    select:\n"
        "        email\n",
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.out == (
        'SELECT\n    "email" AS "email"\nFROM "users"\n'
        "\n"
        'SELECT\n    "email" AS "email"\nFROM "active_users"\n'
    )
    assert captured.err == ""


def test_emit_sql_parser_error_stops_before_later_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "syntax.pie", "shape User {\n")
    _forbid_later_stages(monkeypatch)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-P1005 error:" in captured.err


def test_emit_sql_semantic_error_stops_before_ir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "semantic.pie",
        "shape User:\n    email: MissingType not null\n",
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("IR and SQL must not run after semantic errors")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2002 error: Unknown type: MissingType" in captured.err


def test_emit_sql_ir_error_stops_before_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "ir-error.pie", SOURCE)
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

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{path}:1:1 PIE-I1000 error: missing semantic fact\n" == captured.err


def test_emit_sql_backend_error_returns_one_and_stays_on_stderr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "backend-error.pie", SOURCE)
    diagnostic = _diagnostic(path, "PIE-B1000", "unsupported backend case")
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(artifacts=(), diagnostics=(diagnostic,)),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{path}:1:1 PIE-B1000 error: unsupported backend case\n" == captured.err


def test_emit_sql_can_print_artifacts_and_backend_diagnostics_together(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "mixed-result.pie", SOURCE)
    diagnostic = _diagnostic(path, "PIE-B1000", "one relation unsupported")
    artifact = SqlArtifact(
        name="supported",
        kind=SqlArtifactKind.RELATION,
        sql='SELECT "id" AS "id"\nFROM "users"',
    )
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(
            artifacts=(artifact,),
            diagnostics=(diagnostic,),
        ),
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == 'SELECT "id" AS "id"\nFROM "users"\n'
    assert "PIE-B1000 error: one relation unsupported" in captured.err


def test_emit_sql_warning_does_not_prevent_later_stages(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "warning.pie",
        "shape User:\n"
        "    email: Text\n"
        'source users: User is postgres.table("users")\n'
        "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n",
    )

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert 'SELECT\n    "email" AS "email"\nFROM "users"\n' == captured.out
    assert "PIE-S2005 warning:" in captured.err


def test_emit_sql_unsupported_dialect_is_usage_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pie", SOURCE)

    def unexpected_parse(path: Path) -> object:
        del path
        raise AssertionError("unsupported dialect must stop before parsing")

    monkeypatch.setattr(cli.parser_api, "parse_file", unexpected_parse)

    assert cli.main(["emit-sql", str(path), "--dialect", "mysql"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice: 'mysql'" in captured.err


def test_emit_sql_requires_explicit_dialect(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid.pie", SOURCE)

    assert cli.main(["emit-sql", str(path)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "the following arguments are required: --dialect" in captured.err


def test_emit_sql_missing_file_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "missing.pie"

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(path) in captured.err
    assert "No such file or directory" in captured.err


def test_check_still_does_not_build_ir_or_emit_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid-check.pie", SOURCE)

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must stop after semantic analysis")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


def test_emit_sql_adds_no_convenience_compiler_wrapper() -> None:
    assert not hasattr(cli, "compile_to_ir")
    assert not hasattr(cli, "compile_to_sql")
    assert not hasattr(cli.ir_api, "compile_to_ir")


def _forbid_later_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("later compiler stages must not run")

    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)


def _diagnostic(path: Path, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=str(path),
            line=1,
            column=1,
        ),
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
