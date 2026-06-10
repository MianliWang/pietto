from __future__ import annotations

from pathlib import Path

import pytest

import pietto.cli as cli
import pietto.ir as ir_api
import pietto.sql as sql_api


def test_check_valid_file_returns_success(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "valid.pie",
        "shape User:\n"
        "    email: Text not null\n"
        'source users: User is postgres.table("users")\n',
    )

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


def test_check_missing_file_returns_file_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "missing.pie"

    assert cli.main(["check", str(path)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert str(path) in captured.err
    assert "error:" in captured.err
    assert "No such file or directory" in captured.err


def test_check_parser_error_returns_diagnostic_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "syntax.pie", "shape User {\n")

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (
        f"{path}:1:12 PIE-P1005 error: "
        "Braces are not supported as Pietto block delimiters."
    ) in captured.err


def test_check_semantic_error_returns_diagnostic_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "semantic.pie",
        "shape User:\n    email: MissingType not null\n",
    )

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{path}:2:12 PIE-S2002 error: Unknown type: MissingType" in captured.err


def test_check_warnings_do_not_fail(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "warning.pie",
        "shape User:\n    email: Text\n",
    )

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert f"{path}:2:12 PIE-S2005 warning:" in captured.err


def test_check_stops_before_semantic_analysis_after_parser_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write(tmp_path, "syntax.pie", "shape User {\n")

    def unexpected_analyze(script: object) -> object:
        del script
        raise AssertionError("semantic analysis must not run after parser errors")

    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_analyze)

    assert cli.main(["check", str(path)]) == 1


def test_check_does_not_build_ir_or_emit_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "valid.pie",
        "shape User:\n    email: Text not null\n",
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must stop after semantic analysis")

    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path)]) == 0
    assert capsys.readouterr().out == f"OK: {path}\n"


def test_emit_sql_remains_unimplemented(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["emit-sql", "input.pie"]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "invalid choice" in captured.err
    assert "emit-sql" in captured.err


def test_check_requires_exactly_one_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = _write(tmp_path, "first.pie", "")
    second = _write(tmp_path, "second.pie", "")

    assert cli.main(["check"]) == 2
    missing = capsys.readouterr()
    assert "the following arguments are required: path" in missing.err

    assert cli.main(["check", str(first), str(second)]) == 2
    multiple = capsys.readouterr()
    assert "unrecognized arguments" in multiple.err


def test_no_compile_to_ir_wrapper_was_added() -> None:
    assert not hasattr(cli, "compile_to_ir")
    assert not hasattr(ir_api, "compile_to_ir")


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
