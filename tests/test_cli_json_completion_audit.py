from __future__ import annotations

import inspect
import json
import re
import tomllib
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.ir as ir_api
import pietto.sql as sql_api
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import IrResult
from pietto.sql import SqlArtifact, SqlArtifactKind, SqlResult

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text not null\n"
    'source users: User is postgres.table("users")\n'
)
RELATION = (
    SOURCE + "table user_emails:\n"
    "    from users\n"
    "    select:\n"
    "        id\n"
    "        email\n"
)
CHECK_KEYS = {
    "schema_version",
    "command",
    "ok",
    "path",
    "diagnostics",
    "cli_errors",
}
EMIT_KEYS = CHECK_KEYS | {"dialect", "artifacts", "output"}
DIAGNOSTIC_KEYS = {"code", "severity", "message", "location", "suggestion"}
LOCATION_KEYS = {"path", "line", "column", "end_line", "end_column"}
CLI_ERROR_KEYS = {"kind", "message", "path"}
ARTIFACT_KEYS = {"kind", "name", "sql"}
OUTPUT_KEYS = {"path", "written"}


def test_phase_6_check_json_schema_and_document_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "warning.pie", "shape User:\n    email: Text\n")

    assert cli.main(["check", str(path), "--format=json"]) == 0
    result = _read_json_document(capsys, command="check")

    assert set(result) == CHECK_KEYS
    assert result["ok"] is True
    assert result["cli_errors"] == []
    diagnostic = cast(list[dict[str, object]], result["diagnostics"])[0]
    assert set(diagnostic) == DIAGNOSTIC_KEYS
    assert diagnostic["severity"] == "warning"
    location = cast(dict[str, object], diagnostic["location"])
    assert set(location) == LOCATION_KEYS
    assert location["path"] == str(path)


def test_phase_6_emit_json_schema_artifact_and_output_contract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "relation.pie", RELATION)
    output = tmp_path / "relation.sql"

    assert _emit_json(path, output=output) == 0
    result = _read_json_document(capsys, command="emit-sql")

    assert set(result) == EMIT_KEYS
    assert result["ok"] is True
    assert result["dialect"] == "postgres"
    assert result["cli_errors"] == []
    artifact = cast(list[dict[str, object]], result["artifacts"])[0]
    assert set(artifact) == ARTIFACT_KEYS
    assert artifact["name"] == "user_emails"
    output_status = cast(dict[str, object], result["output"])
    assert set(output_status) == OUTPUT_KEYS
    assert output_status == {"path": str(output), "written": True}
    assert output.read_text(encoding="utf-8") == f"{artifact['sql']}\n"


def test_phase_6_cli_error_schema_is_stable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing.pie"

    assert cli.main(["check", str(missing), "--format=json"]) == 2
    result = _read_json_document(capsys, command="check")

    assert result["ok"] is False
    error = cast(list[dict[str, object]], result["cli_errors"])[0]
    assert set(error) == CLI_ERROR_KEYS
    assert error["kind"] == "file_read"
    assert error["path"] == str(missing)


@pytest.mark.parametrize(
    ("name", "source", "expected_exit", "expected_ok", "expected_code"),
    [
        ("valid.pie", "", 0, True, None),
        (
            "warning.pie",
            "shape User:\n    email: Text\n",
            0,
            True,
            "PIE-S2005",
        ),
        ("parser.pie", "shape User {\n", 1, False, "PIE-P1005"),
        (
            "semantic.pie",
            "shape User:\n    email: MissingType not null\n",
            1,
            False,
            "PIE-S2002",
        ),
    ],
)
def test_phase_6_check_json_exit_matrix(
    name: str,
    source: str,
    expected_exit: int,
    expected_ok: bool,
    expected_code: str | None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)

    assert cli.main(["check", str(path), "--format=json"]) == expected_exit
    result = _read_json_document(capsys, command="check")

    assert result["ok"] is expected_ok
    codes = [
        diagnostic["code"]
        for diagnostic in cast(list[dict[str, object]], result["diagnostics"])
    ]
    if expected_code is None:
        assert codes == []
    else:
        assert expected_code in codes


@pytest.mark.parametrize(
    ("name", "source", "expected_exit", "expected_ok", "expected_code"),
    [
        ("valid.pie", RELATION, 0, True, None),
        ("parser.pie", "shape User {\n", 1, False, "PIE-P1005"),
        (
            "semantic.pie",
            "shape User:\n    email: MissingType not null\n",
            1,
            False,
            "PIE-S2002",
        ),
    ],
)
def test_phase_6_emit_json_exit_matrix(
    name: str,
    source: str,
    expected_exit: int,
    expected_ok: bool,
    expected_code: str | None,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)

    assert _emit_json(path) == expected_exit
    result = _read_json_document(capsys, command="emit-sql")

    assert result["ok"] is expected_ok
    codes = [
        diagnostic["code"]
        for diagnostic in cast(list[dict[str, object]], result["diagnostics"])
    ]
    if expected_code is None:
        assert codes == []
        assert cast(list[object], result["artifacts"])
    else:
        assert expected_code in codes


def test_phase_6_emit_json_backend_and_usage_exit_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "backend.pie", SOURCE)
    output = tmp_path / "backend.sql"
    diagnostic = _diagnostic(path, "PIE-B1000", "unsupported backend case")
    artifact = _artifact("partial", "SELECT 1")
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(
            artifacts=(artifact,),
            diagnostics=(diagnostic,),
        ),
    )

    assert _emit_json(path, output=output) == 1
    backend = _read_json_document(capsys, command="emit-sql")
    assert backend["ok"] is False
    assert backend["cli_errors"] == []
    assert cast(list[dict[str, object]], backend["artifacts"])[0]["sql"] == "SELECT 1"
    assert backend["output"] == {"path": str(output), "written": False}
    assert not output.exists()

    missing = tmp_path / "missing.pie"
    assert _emit_json(missing) == 2
    file_error = _read_json_document(capsys, command="emit-sql")
    assert cast(list[dict[str, object]], file_error["cli_errors"])[0]["kind"] == (
        "file_read"
    )

    assert (
        cli.main(
            [
                "emit-sql",
                str(path),
                "--dialect",
                "mysql",
                "--format=json",
            ]
        )
        == 2
    )
    dialect_error = _read_json_document(capsys, command="emit-sql")
    assert dialect_error["dialect"] == "mysql"
    assert (
        cast(list[dict[str, object]], dialect_error["cli_errors"])[0]["kind"]
        == "unsupported_dialect"
    )


def test_phase_6_json_output_failure_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "input.pie", RELATION)
    same_bytes = path.read_bytes()

    assert _emit_json(path, output=path) == 2
    rejected = _read_json_document(capsys, command="emit-sql")
    assert rejected["output"] == {"path": str(path), "written": False}
    assert cast(list[dict[str, object]], rejected["cli_errors"])[0]["kind"] == (
        "output_path"
    )
    assert path.read_bytes() == same_bytes

    output = _write(tmp_path, "out.sql", "original SQL\n")

    def fail_replace(source: Path, destination: Path) -> None:
        del source, destination
        raise PermissionError("replacement denied")

    monkeypatch.setattr(cli.os, "replace", fail_replace)
    assert _emit_json(path, output=output) == 2
    write_error = _read_json_document(capsys, command="emit-sql")
    assert write_error["output"] == {"path": str(output), "written": False}
    assert cast(list[dict[str, object]], write_error["cli_errors"])[0]["kind"] == (
        "output_write"
    )
    assert cast(list[object], write_error["artifacts"])
    assert output.read_text(encoding="utf-8") == "original SQL\n"
    assert not tuple(tmp_path.glob(".out.sql.*.tmp"))


def test_phase_6_json_stage_short_circuiting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    valid = _write(tmp_path, "valid.pie", SOURCE)

    def unexpected_late_stage(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("check must stop before IR and SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_late_stage)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_late_stage)
    assert cli.main(["check", str(valid), "--format=json"]) == 0
    assert _read_json_document(capsys, command="check")["ok"] is True

    parser_error = _write(tmp_path, "parser.pie", "shape User {\n")
    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_late_stage)
    assert _emit_json(parser_error) == 1
    assert _read_json_document(capsys, command="emit-sql")["ok"] is False


def test_phase_6_emit_json_ir_error_stops_backend_and_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, "ir-error.pie", SOURCE)
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

    assert _emit_json(path, output=output) == 1
    result = _read_json_document(capsys, command="emit-sql")
    assert result["output"] == {"path": str(output), "written": False}
    assert not output.exists()


def test_phase_6_emit_json_semantic_error_stops_ir_and_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(
        tmp_path,
        "semantic-error.pie",
        "shape User:\n    email: MissingType not null\n",
    )

    def unexpected_late_stage(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("semantic errors must stop IR and SQL")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_late_stage)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_late_stage)

    assert _emit_json(path) == 1
    result = _read_json_document(capsys, command="emit-sql")
    assert cast(list[dict[str, object]], result["diagnostics"])[0]["code"] == (
        "PIE-S2002"
    )


@pytest.mark.parametrize(
    ("name", "source", "expected_code"),
    [
        (
            "huge-integer.pie",
            "type Huge = Int(max = " + "9" * 5000 + ") not null\n",
            "PIE-P1000",
        ),
        (
            "deep-parser.pie",
            "derive deep() -> Int not null:\n    " + "+" * 1500 + "1\n",
            "PIE-P1000",
        ),
        (
            "deep-semantic.pie",
            "".join(
                [
                    *(
                        f"type Alias{index} = Alias{index + 1} not null\n"
                        for index in range(1399)
                    ),
                    "type Alias1399 = Int not null\n",
                ]
            ),
            "PIE-S2006",
        ),
    ],
)
def test_phase_6_json_security_containment_regressions(
    name: str,
    source: str,
    expected_code: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = _write(tmp_path, name, source)

    assert cli.main(["check", str(path), "--format=json"]) == 1
    captured = capsys.readouterr()
    result = _parse_json_document(captured.out, captured.err, command="check")

    assert "Traceback" not in captured.out
    assert "RecursionError" not in captured.out
    assert "ValueError" not in captured.out
    diagnostics = cast(list[dict[str, object]], result["diagnostics"])
    assert diagnostics[0]["code"] == expected_code


def test_phase_6_json_round_trips_malicious_text_as_structured_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    unsafe = 'line\nquote"slash\\esc\x1bnul\x00del\x7funicode雪'
    path = Path(str(tmp_path / unsafe))
    diagnostic = Diagnostic(
        code="PIE-B1000",
        severity=Severity.ERROR,
        message=unsafe,
        location=SourceLocation(path=None, line=1, column=1),
    )
    artifact = _artifact(unsafe, f"SELECT '{unsafe}'")
    real_parse = cli.parser_api.parse_source(SOURCE)
    assert real_parse.ast is not None
    monkeypatch.setattr(cli.parser_api, "parse_file", lambda checked: real_parse)
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(
            artifacts=(artifact,),
            diagnostics=(diagnostic,),
        ),
    )

    assert _emit_json(path) == 1
    captured = capsys.readouterr()
    result = _parse_json_document(captured.out, captured.err, command="emit-sql")

    assert "\x1b" not in captured.out
    assert "\x00" not in captured.out
    assert "\x7f" not in captured.out
    assert "雪" not in captured.out
    serialized = cast(list[dict[str, object]], result["diagnostics"])[0]
    assert serialized["message"] == unsafe
    assert serialized["message"] != cli._escape_cli_text(unsafe)
    assert cast(list[dict[str, object]], result["artifacts"])[0]["sql"] == artifact.sql


def test_phase_6_default_text_cli_remains_compatible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    check_path = _write(tmp_path, "check.pie", "")
    relation_path = _write(tmp_path, "relation.pie", RELATION)

    assert cli.main(["check", str(check_path)]) == 0
    default_check = capsys.readouterr()
    assert default_check.out == f"OK: {check_path}\n"
    assert default_check.err == ""

    assert cli.main(["check", str(check_path), "--format", "text"]) == 0
    explicit_check = capsys.readouterr()
    assert explicit_check.out == f"OK: {check_path}\n"
    assert explicit_check.err == ""

    assert cli.main(["emit-sql", str(relation_path), "--dialect", "postgres"]) == 0
    default_emit = capsys.readouterr()
    assert default_emit.out.startswith("SELECT\n")
    assert default_emit.err == ""

    assert (
        cli.main(
            [
                "emit-sql",
                str(relation_path),
                "--dialect",
                "postgres",
                "--format",
                "text",
            ]
        )
        == 0
    )
    explicit_emit = capsys.readouterr()
    assert explicit_emit.out == default_emit.out
    assert explicit_emit.err == ""

    output = tmp_path / "out.sql"
    assert (
        cli.main(
            [
                "emit-sql",
                str(relation_path),
                "--dialect",
                "postgres",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    text_output = capsys.readouterr()
    assert text_output.out == ""
    assert text_output.err == ""
    assert output.read_text(encoding="utf-8") == default_emit.out


def test_phase_6_committed_examples_work_in_json_modes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    check_example = Path("examples/basic/types.pie")
    relation_example = Path("examples/tables/active_users.pie")
    output = tmp_path / "active_users.sql"

    assert cli.main(["check", str(check_example), "--format=json"]) == 0
    checked = _read_json_document(capsys, command="check")
    assert checked["ok"] is True

    assert _emit_json(relation_example) == 0
    emitted = _read_json_document(capsys, command="emit-sql")
    assert emitted["ok"] is True
    assert cast(list[object], emitted["artifacts"])

    assert _emit_json(relation_example, output=output) == 0
    written = _read_json_document(capsys, command="emit-sql")
    assert written["output"] == {"path": str(output), "written": True}
    assert output.read_text(encoding="utf-8").startswith("SELECT\n")


def test_phase_6_boundaries_dependencies_and_diagnostic_codes_remain_clean() -> None:
    source = inspect.getsource(cli).lower()
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]

    assert dependencies == ["antlr4-python3-runtime>=4.13.2"]
    assert not hasattr(cli, "compile_to_ir")
    assert not hasattr(cli, "compile_to_sql")
    assert not hasattr(ir_api, "compile_to_ir")
    assert not hasattr(sql_api, "compile_to_sql")
    for forbidden in (
        "import psycopg",
        "import sqlalchemy",
        "subprocess",
        "socket",
        ".connect(",
        ".execute(",
        "schema introspection",
        "connector execution",
        "watch mode",
        "lsp",
        "web ui",
        "runtime server",
    ):
        assert forbidden not in source

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


def _emit_json(path: Path, *, output: Path | None = None) -> int:
    arguments = [
        "emit-sql",
        str(path),
        "--dialect",
        "postgres",
        "--format=json",
    ]
    if output is not None:
        arguments.extend(["--output", str(output)])
    return cli.main(arguments)


def _read_json_document(
    capsys: pytest.CaptureFixture[str],
    *,
    command: str,
) -> dict[str, object]:
    captured = capsys.readouterr()
    return _parse_json_document(captured.out, captured.err, command=command)


def _parse_json_document(
    stdout: str,
    stderr: str,
    *,
    command: str,
) -> dict[str, object]:
    assert stderr == ""
    assert stdout.startswith("{")
    assert stdout.endswith("}\n")
    assert not stdout.endswith("\n\n")
    assert "OK:" not in stdout
    result = json.loads(stdout)
    assert isinstance(result, dict)
    assert result["schema_version"] == 1
    assert result["command"] == command
    assert "version" not in result
    assert "package_version" not in result
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
