from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

import pietto.cli as cli

EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pie")))
assert len(EXAMPLE_PATHS) == 10

SQL_EXAMPLES = (
    (Path("examples/tables/active_users.pie"), 1),
    (Path("examples/queries/active_user_emails.pie"), 2),
)


def test_public_cli_main_help_and_version_are_available(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert callable(cli.main)

    assert cli.main(["--help"]) == 0
    help_output = capsys.readouterr()
    assert "usage: pietto" in help_output.out
    assert "check" in help_output.out
    assert "emit-sql" in help_output.out
    assert help_output.err == ""

    assert cli.main(["--version"]) == 0
    version_output = capsys.readouterr()
    assert version_output.out.startswith("pietto ")
    assert version_output.err == ""


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=str)
def test_all_committed_examples_pass_cli_check(
    path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert " error:" not in captured.err


def test_cli_check_reports_parser_and_semantic_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    parser_error = _write(tmp_path, "parser-error.pie", "shape User {\n")
    assert cli.main(["check", str(parser_error)]) == 1
    parser_output = capsys.readouterr()
    assert parser_output.out == ""
    assert "PIE-P1005 error:" in parser_output.err

    semantic_error = _write(
        tmp_path,
        "semantic-error.pie",
        "shape User:\n    email: MissingType not null\n",
    )
    assert cli.main(["check", str(semantic_error)]) == 1
    semantic_output = capsys.readouterr()
    assert semantic_output.out == ""
    assert "PIE-S2002 error:" in semantic_output.err


@pytest.mark.parametrize(("path", "select_count"), SQL_EXAMPLES, ids=str)
def test_supported_committed_examples_emit_sql_to_stdout(
    path: Path,
    select_count: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0

    captured = capsys.readouterr()
    assert captured.out.count("SELECT\n") == select_count
    assert captured.out.endswith("\n")
    assert captured.err == ""


def test_committed_query_example_emits_ordered_sql_to_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = Path("examples/queries/active_user_emails.pie")
    output = tmp_path / "active_user_emails.sql"

    assert (
        cli.main(
            [
                "emit-sql",
                str(source),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    captured = capsys.readouterr()
    sql = output.read_text(encoding="utf-8")
    assert captured.out == ""
    assert captured.err == ""
    assert sql.count("SELECT\n") == 2
    assert sql.index('FROM "public.users"') < sql.index('FROM "active_users"')
    assert "\n\nSELECT\n" in sql


def test_cli_usage_and_file_errors_return_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    example = Path("examples/tables/active_users.pie")
    assert cli.main(["emit-sql", str(example), "--dialect", "mysql"]) == 2
    dialect_output = capsys.readouterr()
    assert dialect_output.out == ""
    assert "invalid choice: 'mysql'" in dialect_output.err

    missing = tmp_path / "missing.pie"
    assert cli.main(["check", str(missing)]) == 2
    file_output = capsys.readouterr()
    assert file_output.out == ""
    assert str(missing) in file_output.err


def test_check_remains_isolated_from_ir_and_sql(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must stop after semantic analysis")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)

    path = Path("examples/sources/users.pie")
    assert cli.main(["check", str(path)]) == 0
    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert "PIE-S2303 warning:" in captured.err
    assert " error:" not in captured.err


def test_exit_codes_and_cli_boundaries_are_documented() -> None:
    plan = Path("docs/plan/phase-5-cli-tooling.md").read_text(encoding="utf-8")

    assert "**Phase 5 CLI MVP: Complete.**" in plan
    assert "returns `0`" in plan
    assert "return `1`" in plan
    assert "return `2`" in plan
    for command in (
        "pietto --help",
        "pietto --version",
        "pietto check file.pie",
        "pietto emit-sql file.pie --dialect postgres",
        "pietto emit-sql file.pie --dialect postgres --output out.sql",
    ):
        assert command in plan


def test_cli_has_no_runtime_execution_or_convenience_compiler_wrappers() -> None:
    source = inspect.getsource(cli)

    assert not hasattr(cli, "compile_to_ir")
    assert not hasattr(cli, "compile_to_sql")
    assert not hasattr(cli.ir_api, "compile_to_ir")
    for forbidden in (
        "sqlglot",
        "psycopg",
        "sqlalchemy",
        ".connect(",
        ".execute(",
        "schema introspection",
    ):
        assert forbidden not in source.lower()


def test_repository_contains_no_legacy_diagnostic_codes() -> None:
    roots = (
        Path("src"),
        Path("tests"),
        Path("docs"),
        Path("README.md"),
        Path("AGENTS.md"),
    )
    legacy_codes: list[tuple[Path, str]] = []

    for root in roots:
        paths = root.rglob("*") if root.is_dir() else (root,)
        for path in paths:
            if not path.is_file() or path.suffix not in {".md", ".pie", ".py", ".txt"}:
                continue
            for match in re.finditer(
                r"(?<!PIE-)\bP[0-9]{4}\b",
                path.read_text(encoding="utf-8"),
            ):
                legacy_codes.append((path, match.group()))

    assert legacy_codes == []


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
