from __future__ import annotations

import inspect
import tomllib
from importlib.util import find_spec
from pathlib import Path

import pytest

import pietto
import pietto.cli as cli
import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.sql as sql_api


def test_cli_and_package_can_be_imported() -> None:
    assert pietto.__doc__ == "Pietto compiler package."
    assert callable(cli.main)


def test_no_arguments_prints_help_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main([]) == 0

    captured = capsys.readouterr()
    assert "Pietto semantic SQL authoring tools." in captured.out
    assert "usage: pietto" in captured.out
    assert captured.err == ""


def test_help_returns_success_and_writes_only_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["--help"]) == 0

    captured = capsys.readouterr()
    assert "usage: pietto" in captured.out
    assert "--version" in captured.out
    assert captured.err == ""


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


def test_version_uses_package_metadata(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "version", lambda package: f"{package}-test")

    assert cli.main(["--version"]) == 0

    captured = capsys.readouterr()
    assert captured.out == "pietto pietto-test\n"
    assert captured.err == ""


def test_version_falls_back_when_package_metadata_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def missing_version(package: str) -> str:
        raise cli.PackageNotFoundError(package)

    monkeypatch.setattr(cli, "version", missing_version)

    assert cli.main(["--version"]) == 0

    captured = capsys.readouterr()
    # The fallback literal must follow the declared package version.
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert captured.out == f"pietto {project['project']['version']}\n"
    assert captured.err == ""


@pytest.mark.parametrize("arguments", [["--unknown"]])
def test_unimplemented_or_unknown_arguments_return_usage_error(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(arguments) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: pietto" in captured.err
    assert "error:" in captured.err


def test_cli_usage_and_file_errors_return_two(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    example = Path("examples/tables/active_users.pietto")
    assert cli.main(["emit-sql", str(example), "--dialect", "sqlite"]) == 2
    dialect_output = capsys.readouterr()
    assert dialect_output.out == ""
    assert "invalid choice: 'sqlite'" in dialect_output.err

    missing = tmp_path / "missing.pietto"
    assert cli.main(["check", str(missing)]) == 2
    file_output = capsys.readouterr()
    assert file_output.out == ""
    assert str(missing) in file_output.err


def test_console_script_targets_cli_main() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["scripts"] == {"pietto": "pietto.cli:main"}


def test_help_and_version_do_not_invoke_compiler_stages(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("help and version must not invoke compiler stages")

    monkeypatch.setattr(parser_api, "parse_source", unexpected_call)
    monkeypatch.setattr(parser_api, "parse_file", unexpected_call)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["--help"]) == 0
    assert cli.main(["--version"]) == 0
    capsys.readouterr()


def test_cli_has_no_runtime_execution_or_convenience_compiler_wrappers() -> None:
    source = inspect.getsource(cli)

    assert find_spec("pietto.cli") is not None
    assert not hasattr(cli, "compile_to_ir")
    assert not hasattr(cli, "compile_to_sql")
    assert not hasattr(cli.ir_api, "compile_to_ir")
    assert not hasattr(ir_api, "compile_to_ir")
    for forbidden in (
        "sqlglot",
        "psycopg",
        "sqlalchemy",
        ".connect(",
        ".execute(",
        "schema introspection",
    ):
        assert forbidden not in source.lower()
