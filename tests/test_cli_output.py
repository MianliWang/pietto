from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

import pietto.cli as cli
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.sql import SqlArtifact, SqlArtifactKind, SqlResult

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
)
_OUTPUT_ENCODING_ERROR = b"pietto: error: terminal output could not be encoded\n"


def test_emit_sql_default_output_remains_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.out == _expected_sql()
    assert captured.err == ""


def test_emit_sql_output_file_receives_sql_and_stdout_stays_empty(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)
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

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert output.read_text(encoding="utf-8") == _expected_sql()


def test_emit_sql_output_file_is_overwritten(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)
    output = tmp_path / "out.sql"
    output.write_text("stale SQL\n", encoding="utf-8")

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

    assert output.read_text(encoding="utf-8") == _expected_sql()
    assert capsys.readouterr().out == ""


def test_emit_sql_output_file_preserves_multiple_artifact_formatting(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "relations.pietto",
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query active_user_emails:\n"
        "    from active_users\n"
        "    select:\n"
        "        email\n",
    )
    output = tmp_path / "relations.sql"

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

    assert output.read_text(encoding="utf-8") == (
        'SELECT\n    "email" AS "email"\nFROM "users"\n'
        "\n"
        'SELECT\n    "email" AS "email"\nFROM "active_users"\n'
    )
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_emit_sql_output_keeps_warnings_on_stderr(
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

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2005 warning:" in captured.err
    assert output.read_text(encoding="utf-8").startswith("SELECT\n")


def test_emit_sql_missing_output_parent_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)
    output = tmp_path / "missing" / "out.sql"

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
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{output}: error:" in captured.err
    assert not output.exists()


def test_emit_sql_backend_error_does_not_create_output_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "backend-error.pietto", SOURCE)
    output = tmp_path / "backend-error.sql"
    artifact = SqlArtifact(
        name="partial",
        kind=SqlArtifactKind.RELATION,
        sql='SELECT "id" AS "id"\nFROM "users"',
    )
    diagnostic = Diagnostic(
        code="PIE-B1000",
        severity=Severity.ERROR,
        message="unsupported backend case",
        location=SourceLocation(path=str(path), line=1, column=1),
    )
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(
            artifacts=(artifact,),
            diagnostics=(diagnostic,),
        ),
    )

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
    assert "PIE-B1000 error:" in captured.err
    assert not output.exists()


@pytest.mark.parametrize(
    ("name", "source", "expected_code"),
    [
        ("syntax.pietto", "shape User {\n", "PIE-P1005"),
        (
            "semantic.pietto",
            "shape User:\n    email: MissingType not null\n",
            "PIE-S2002",
        ),
    ],
)
def test_emit_sql_frontend_error_does_not_create_output_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    name: str,
    source: str,
    expected_code: str,
) -> None:
    path = _write(tmp_path, name, source)
    output = tmp_path / f"{name}.sql"

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
    assert expected_code in captured.err
    assert not output.exists()


def test_emit_sql_unsupported_dialect_still_returns_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _relation_file(tmp_path)
    output = tmp_path / "out.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "sqlite",
                "--output",
                str(output),
            ]
        )
        == 2
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice: 'sqlite'" in captured.err
    assert not output.exists()


def test_check_behavior_remains_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "valid-check.pietto", SOURCE)

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must not build IR or emit SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


def test_terminal_encoding_failure_returns_safe_output_error(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path,
        "emoji.pietto",
        "shape User:\n"
        "    id: UUID not null\n"
        'source users: User is postgres.table("secret😀")\n'
        "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        id\n",
    )

    normal = _run_cli(["emit-sql", str(path), "--dialect", "postgres"])
    assert normal.returncode == 0
    assert normal.stderr == b""
    assert normal.stdout == _expected_emoji_sql().encode("utf-8")
    for encoding in ("gbk", "cp1252", "ascii"):
        failed = _run_cli(
            ["emit-sql", str(path), "--dialect", "postgres"],
            encoding=encoding,
        )
        assert failed.returncode == 2
        assert failed.stdout == b""
        assert failed.stderr == _OUTPUT_ENCODING_ERROR
        assert b"secret" not in failed.stderr
        assert b"Traceback" not in failed.stderr

        output = tmp_path / f"{encoding}.sql"
        json_result = _run_cli(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(output),
            ],
            encoding=encoding,
        )
        assert json_result.returncode == 0
        assert json_result.stderr == b""
        assert json_result.stdout.isascii()
        assert json.loads(json_result.stdout)["artifacts"][0]["sql"] == (
            _expected_emoji_sql().rstrip("\n")
        )
        assert output.read_bytes() == _expected_emoji_sql().encode("utf-8")

        diagnostic = _run_cli(
            ["check", str(tmp_path / "missing😀.pietto")],
            encoding=encoding,
            strict_stderr=True,
        )
        assert diagnostic.returncode == 2
        assert diagnostic.stdout == b""
        assert diagnostic.stderr == _OUTPUT_ENCODING_ERROR
        assert b"Traceback" not in diagnostic.stderr


def _relation_file(tmp_path: Path) -> Path:
    return _write(
        tmp_path,
        "active_users.pietto",
        SOURCE + "table active_users:\n"
        "    from users\n"
        "    where active == true\n"
        "    select:\n"
        "        id\n"
        "        email\n",
    )


def _expected_sql() -> str:
    return (
        "SELECT\n"
        '    "id" AS "id",\n'
        '    "email" AS "email"\n'
        'FROM "users"\n'
        'WHERE "active" = TRUE\n'
    )


def _expected_emoji_sql() -> str:
    return 'SELECT\n    "id" AS "id"\nFROM "secret😀"\n'


def _run_cli(
    arguments: list[str],
    *,
    encoding: str | None = None,
    strict_stderr: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    environment = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1] / "src")}
    if encoding is None:
        environment.pop("PYTHONIOENCODING", None)
    else:
        environment["PYTHONIOENCODING"] = encoding
    program = "from pietto.cli import main; raise SystemExit(main())"
    if strict_stderr:
        program = (
            "import os, sys; sys.stderr = os.fdopen("
            "sys.stderr.fileno(), 'w', encoding=sys.stderr.encoding, "
            "errors='strict', closefd=False); " + program
        )
    return subprocess.run(
        [
            sys.executable,
            "-c",
            program,
            *arguments,
        ],
        capture_output=True,
        check=False,
        env=environment,
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
