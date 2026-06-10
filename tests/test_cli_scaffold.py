from __future__ import annotations

import importlib
import tomllib
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
    assert captured.out == "pietto 0.1.0\n"
    assert captured.err == ""


@pytest.mark.parametrize("arguments", [["--unknown"], ["emit-sql"]])
def test_unimplemented_or_unknown_arguments_return_usage_error(
    arguments: list[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(arguments) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: pietto" in captured.err
    assert "error:" in captured.err


def test_console_script_targets_cli_main() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert project["project"]["scripts"] == {"pietto": "pietto.cli:main"}


def test_scaffold_does_not_invoke_compiler_stages(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("CLI scaffold must not invoke compiler stages")

    monkeypatch.setattr(parser_api, "parse_source", unexpected_call)
    monkeypatch.setattr(parser_api, "parse_file", unexpected_call)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["--help"]) == 0
    assert cli.main(["--version"]) == 0
    capsys.readouterr()


def test_scaffold_has_no_compile_to_ir_wrapper() -> None:
    assert not hasattr(cli, "compile_to_ir")
    assert not hasattr(ir_api, "compile_to_ir")
    assert importlib.util.find_spec("pietto.cli") is not None
