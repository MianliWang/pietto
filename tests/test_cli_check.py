from __future__ import annotations

import errno
import json
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
        "valid.pietto",
        'shape User:\n    email: Text\nsource users: User = postgres.table("users")\n',
    )

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert captured.err == ""


def test_check_missing_file_returns_file_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "missing.pietto"

    assert cli.main(["check", str(path)]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{path}: error: No such file or directory (errno 2)\n"


@pytest.mark.parametrize(
    "command",
    [["check"], ["emit-sql", "--dialect", "postgres"], ["explain"]],
)
def test_directory_input_reported_as_permission_error_is_a_directory(
    command: list[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory = tmp_path / "models"
    directory.mkdir()

    def windows_open(path: Path) -> object:
        # The Windows C runtime reports opening a directory as EACCES.
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(cli.parser_api, "parse_file", windows_open)

    assert cli.main([command[0], str(directory), *command[1:]]) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"{directory}: error: Is a directory (errno 13)\n"


@pytest.mark.parametrize(
    ("command", "schema", "other", "arguments"),
    [
        (["check"], 2, 4, ""),
        (
            ["emit-sql", "--dialect", "postgres"],
            2,
            1,
            " --module FILE --kind KIND --name NAME --dialect DIALECT"
            " --emission-contract FILE",
        ),
        (["explain"], 4, 2, ""),
    ],
)
def test_a_project_directory_given_as_the_file_hints_at_project_mode(
    command: list[str],
    schema: int,
    other: int,
    arguments: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    directory = tmp_path / "project"
    directory.mkdir()

    assert cli.main([command[0], str(directory), *command[1:]]) == 2
    without_config = capsys.readouterr()

    (directory / "pietto.toml").write_text(f"schema_version = {schema}\n")
    assert cli.main([command[0], str(directory), *command[1:]]) == 2
    with_config = capsys.readouterr()

    assert without_config.out == with_config.out == ""
    assert with_config.err == (
        f"{without_config.err}hint: for a project use pietto {command[0]} --project"
        f" {directory}{arguments}\n"
    )
    # A schema version that this command's --project does not read gets no
    # hint, which would lead to its refusal.
    (directory / "pietto.toml").write_text(f"schema_version = {other}\n")
    assert cli.main([command[0], str(directory), *command[1:]]) == 2
    assert capsys.readouterr().err == without_config.err
    assert without_config.err.startswith(f"{directory}: error: Is a directory")
    # A configuration nested too deeply for tomllib is one that does not say
    # its version, which --project reports; it never raises.
    (directory / "pietto.toml").write_text(
        f"schema_version = {other}\na = {'[' * 2000}{']' * 2000}\n"
    )
    assert cli.main([command[0], str(directory), *command[1:]]) == 2
    assert capsys.readouterr().err == with_config.err
    # So is one with an integer too long for tomllib's int().
    (directory / "pietto.toml").write_text(
        f"schema_version = {other}\na = {'9' * 5000}\n"
    )
    assert cli.main([command[0], str(directory), *command[1:]]) == 2
    assert capsys.readouterr().err == with_config.err
    # JSON keeps the v1 error unchanged.
    assert cli.main(["check", str(directory), "--format", "json"]) == 2
    document = json.loads(capsys.readouterr().out)
    assert [error["kind"] for error in document["cli_errors"]] == ["file_read"]


def test_check_parser_error_returns_diagnostic_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "syntax.pietto", "shape User {\n")

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert (
        f"{path}:1:12 PIE-P1005 error: "
        "Braces are not supported as Pietto block delimiters."
    ) in captured.err


def test_check_overly_long_integer_returns_parser_error_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "huge-integer.pietto",
        "type Huge = Int(max = " + "9" * 5000 + ")\n",
    )

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{path}:1:23 PIE-P1000 error:" in captured.err
    assert "maximum supported length" in captured.err
    assert "Traceback" not in captured.err
    assert "ValueError" not in captured.err


def test_check_deep_unary_returns_parser_error_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "deep-unary.pietto",
        "derive deep() -> Int:\n    return " + "+" * 1500 + "1\n",
    )

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    # Located at the start of the declaration that ran out of depth.
    assert f"{path}:1:1 PIE-P1000 error:" in captured.err
    assert "recursion limit" in captured.err
    assert "Traceback" not in captured.err
    assert "RecursionError" not in captured.err


def test_check_semantic_error_returns_diagnostic_error(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "semantic.pietto",
        "shape User:\n    email: MissingType\n",
    )

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{path}:2:12 PIE-S2002 error: Unknown type: MissingType" in captured.err


@pytest.mark.parametrize(
    "endings",
    [("\n",), ("\r\n",), ("\r",), ("\r", "\r\n", "\n")],
    ids=["lf", "crlf", "cr", "mixed"],
)
def test_check_reports_one_line_per_lf_crlf_or_lone_cr(
    endings: tuple[str, ...],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    lines = [
        "shape User:",
        "    id: UUID",
        "    deleted_at: Timestamp | None",
        "",
        'source users: User = postgres.table("public.users")',
        "",
        "query q:",
        "    from users",
        "    where missing_field is None",
        "    select:",
        "        id",
    ]
    path = tmp_path / "line-ends.pietto"
    path.write_bytes(
        "".join(
            line + endings[index % len(endings)] for index, line in enumerate(lines)
        ).encode("utf-8")
    )

    assert cli.main(["check", str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        f"{path}:9:11 PIE-S2102 error: Unknown field: missing_field\n"
    )

    assert cli.main(["check", "--format", "json", str(path)]) == 1
    document = json.loads(capsys.readouterr().out)
    assert [item["location"] for item in document["diagnostics"]] == [
        {"path": str(path), "line": 9, "column": 11, "end_line": 9, "end_column": 24}
    ]


def test_check_deep_alias_chain_returns_semantic_error_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    aliases = [f"type Alias{index} = Alias{index + 1}\n" for index in range(1399)]
    aliases.append("type Alias1399 = Int\n")
    path = _write(tmp_path, "deep-aliases.pietto", "".join(aliases))

    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"{path}:1:1 PIE-S2006 error:" in captured.err
    assert "recursion limit" in captured.err
    assert "Traceback" not in captured.err
    assert "RecursionError" not in captured.err


def test_check_warnings_do_not_fail(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "warning.pietto",
        'shape User:\n    email: Text\nsource raw = postgres.table("raw")\n',
    )

    assert cli.main(["check", str(path)]) == 0

    captured = capsys.readouterr()
    assert captured.out == f"OK: {path}\n"
    assert f"{path}:3:1 PIE-S2303 warning:" in captured.err


def test_emission_warning_keeps_the_check_command_successful(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(
        tmp_path,
        "warning.pietto",
        """shape Row:
    id: Int
    value: Int | None
    text: Text | None
    label: Text | None
source rows: Row = postgres.table("rows")
query q:
    from rows
    select first = first_value(value) window(order by id range 2 preceding)
""",
    )

    assert cli.main(["check", str(path)]) == 0
    assert "PIE-S2385 warning" in capsys.readouterr().err


def test_warning_message_does_not_claim_a_check_with_an_error_succeeds(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = _write(
        tmp_path,
        "error.pietto",
        """shape Row:
    id: Int
    value: Int | None
    text: Text | None
    label: Text | None
source rows: Row = postgres.table("rows")
table produced:
    from rows
    select:
        value = None
        bad = missing
query reader:
    from produced
    select value
""",
    )

    assert cli.main(["check", str(path)]) == 1
    stderr = capsys.readouterr().err
    assert "does not change check's exit status" in stderr
    assert "check remains successful" not in stderr


def test_check_stops_before_semantic_analysis_after_parser_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write(tmp_path, "syntax.pietto", "shape User {\n")

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
        "valid.pietto",
        "shape User:\n    email: Text\n",
    )

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must stop after semantic analysis")

    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(sql_api, "emit_postgres_sql", unexpected_call)

    assert cli.main(["check", str(path)]) == 0
    assert capsys.readouterr().out == f"OK: {path}\n"


def test_check_requires_exactly_one_file(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = _write(tmp_path, "first.pietto", "")
    second = _write(tmp_path, "second.pietto", "")

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
