from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.sql as sql_api
from pietto.ir import ScriptIR
from pietto.sql import SqlResult

REPO_ROOT = Path(__file__).resolve().parents[1]
MYSQL_SOURCE = REPO_ROOT / (
    "tests/fixtures/mysql/compatibility_ordering_metadata.pietto"
)
MYSQL_FAILURES = REPO_ROOT / "tests/fixtures/mysql/compatibility_failures.pietto"
MYSQL_SQL_GOLDEN = REPO_ROOT / (
    "tests/fixtures/golden/emit_mysql_compatibility_ordering_metadata.sql"
)
MYSQL_JSON_GOLDEN = REPO_ROOT / (
    "tests/fixtures/golden/emit_mysql_compatibility_ordering_metadata.json"
)


def test_mysql_text_cli_matches_reviewed_golden(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["emit-sql", str(MYSQL_SOURCE), "--dialect", "mysql"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.encode("utf-8") == MYSQL_SQL_GOLDEN.read_bytes()


def test_mysql_json_cli_matches_structural_v1_golden(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert (
        cli.main(
            [
                "emit-sql",
                MYSQL_SOURCE.relative_to(REPO_ROOT).as_posix(),
                "--dialect",
                "mysql",
                "--format=json",
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.err == ""
    document = json.loads(captured.out)
    assert document == json.loads(MYSQL_JSON_GOLDEN.read_text(encoding="utf-8"))
    assert document["schema_version"] == 1
    assert document["dialect"] == "mysql"


def test_mysql_backend_diagnostics_use_exit_one_and_preserve_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["emit-sql", str(MYSQL_FAILURES), "--dialect", "mysql"]) == 1

    captured = capsys.readouterr()
    assert captured.out.count("SELECT\n") == 2
    assert captured.out.index("FROM `users`") < captured.out.index("FROM `first_ok`")
    assert [
        line.split(": ", maxsplit=1)[1].split(".", maxsplit=1)[0]
        for line in captured.err.splitlines()
    ] == [
        "MySQL SQL emission is not implemented for RelationIR: first_bad",
        "MySQL SQL emission is not implemented for RelationIR: second_bad",
    ]
    assert captured.err.count("PIE-B1000 error:") == 2


def test_mysql_json_backend_failure_preserves_artifacts_and_diagnostics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        cli.main(
            [
                "emit-sql",
                str(MYSQL_FAILURES),
                "--dialect",
                "mysql",
                "--format=json",
            ]
        )
        == 1
    )

    document = _read_json(capsys)
    assert document["schema_version"] == 1
    assert document["dialect"] == "mysql"
    assert document["ok"] is False
    artifacts = cast(list[dict[str, object]], document["artifacts"])
    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [artifact["name"] for artifact in artifacts] == ["first_ok", "second_ok"]
    assert [diagnostic["code"] for diagnostic in diagnostics] == [
        "PIE-B1000",
        "PIE-B1000",
    ]


def test_mysql_output_file_success_is_atomic(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "mysql.sql"
    output.write_text("stale SQL\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "emit-sql",
                str(MYSQL_SOURCE),
                "--dialect",
                "mysql",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert output.read_bytes() == MYSQL_SQL_GOLDEN.read_bytes()
    assert not tuple(tmp_path.glob(".mysql.sql.*.tmp"))


def test_mysql_json_output_file_uses_existing_v1_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "mysql-json.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(MYSQL_SOURCE),
                "--dialect",
                "mysql",
                "--format=json",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    document = _read_json(capsys)
    assert document["schema_version"] == 1
    assert document["dialect"] == "mysql"
    assert document["ok"] is True
    assert document["output"] == {
        "path": str(output),
        "written": True,
    }
    assert output.read_bytes() == MYSQL_SQL_GOLDEN.read_bytes()
    assert not tuple(tmp_path.glob(".mysql-json.sql.*.tmp"))


def test_mysql_backend_failure_does_not_replace_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "mysql.sql"
    output.write_text("original SQL\n", encoding="utf-8")

    assert (
        cli.main(
            [
                "emit-sql",
                str(MYSQL_FAILURES),
                "--dialect",
                "mysql",
                "--output",
                str(output),
            ]
        )
        == 1
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.count("PIE-B1000 error:") == 2
    assert output.read_text(encoding="utf-8") == "original SQL\n"
    assert not tuple(tmp_path.glob(".mysql.sql.*.tmp"))


def test_unknown_text_and_json_dialects_still_exit_two_before_parsing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_parse(path: Path) -> object:
        del path
        raise AssertionError("unknown dialect must stop before parsing")

    monkeypatch.setattr(cli.parser_api, "parse_file", unexpected_parse)

    assert cli.main(["emit-sql", "missing.pietto", "--dialect", "sqlite"]) == 2
    text = capsys.readouterr()
    assert text.out == ""
    assert "invalid choice: 'sqlite'" in text.err

    assert (
        cli.main(
            [
                "emit-sql",
                "missing.pietto",
                "--dialect",
                "sqlite",
                "--format=json",
            ]
        )
        == 2
    )
    document = _read_json(capsys)
    assert document["dialect"] == "sqlite"
    error = cast(list[dict[str, object]], document["cli_errors"])[0]
    assert error["kind"] == "unsupported_dialect"


def test_explicit_dialect_does_not_infer_from_header_connector_or_suffix(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mysql_path = tmp_path / "input.sql"
    mysql_path.write_text(
        "pietto 0.9\n"
        "mode checked\n"
        "dialect postgres\n"
        "encoding utf8\n"
        "shape User:\n"
        "    email: Text not null\n"
        'source users: User is mysql.table("users")\n'
        "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n",
        encoding="utf-8",
    )

    assert cli.main(["emit-sql", str(mysql_path), "--dialect", "mysql"]) == 0
    selected = capsys.readouterr()
    assert selected.out.endswith("FROM `users`\n")
    assert selected.err == ""

    assert cli.main(["emit-sql", str(mysql_path), "--dialect", "postgres"]) == 1
    mismatched = capsys.readouterr()
    assert mismatched.out == ""
    assert "PIE-B1000 error:" in mismatched.err
    assert "postgres.table(Text)" in mismatched.err


def test_closed_dispatch_passes_only_script_ir_to_selected_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "metadata.pietto"
    path.write_text("type Age = Int not null\n", encoding="utf-8")
    received: list[ScriptIR] = []

    def emit(script_ir: ScriptIR) -> SqlResult:
        received.append(script_ir)
        return SqlResult(artifacts=(), diagnostics=())

    monkeypatch.setattr(cli.mysql_backend, "emit_mysql_sql", emit)

    assert cli.main(["emit-sql", str(path), "--dialect", "mysql"]) == 0
    assert len(received) == 1
    assert isinstance(received[0], ScriptIR)
    assert capsys.readouterr().out == ""


def test_mysql_remains_private_and_check_is_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert "emit_mysql_sql" not in sql_api.__all__
    assert not hasattr(sql_api, "emit_sql")

    path = tmp_path / "check.pietto"
    path.write_text("type Age = Int not null\n", encoding="utf-8")

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must not build IR or emit SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
    monkeypatch.setattr(cli.mysql_backend, "emit_mysql_sql", unexpected_call)

    assert cli.main(["check", str(path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


def _read_json(
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    document = json.loads(captured.out)
    assert isinstance(document, dict)
    return cast(dict[str, object], document)
