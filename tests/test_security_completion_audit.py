from __future__ import annotations

import inspect
import os
import re
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

import pietto.cli as cli
import pietto.ir as ir_api
import pietto.sql as sql_api
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.ir import ScriptIR, SourceIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlArtifact, SqlArtifactKind, SqlResult, emit_postgres_sql
from pietto.sql.render import quote_identifier, render_literal

SOURCE = (
    "shape User:\n"
    "    email: Text not null\n"
    'source users: User is postgres.table("users")\n'
    "table user_emails:\n"
    "    from users\n"
    "    select:\n"
    "        email\n"
)


def test_psec_001_long_numeric_literal_is_diagnosed_without_cli_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = "type Huge = Int(max = " + "9" * 5000 + ") not null\n"

    result = parse_source(source, path="huge-integer.pie")

    assert result.ast is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-P1000"]
    assert "maximum supported length" in result.diagnostics[0].message

    path = _write(tmp_path, "huge-integer.pie", source)
    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-P1000 error:" in captured.err
    assert "Traceback" not in captured.err
    assert "ValueError" not in captured.err


def test_psec_002_deep_parser_input_is_diagnosed_without_cli_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = "derive deep() -> Int not null:\n    " + "+" * 1500 + "1\n"

    result = parse_source(source, path="deep-parser.pie")

    assert result.ast is None
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-P1000"]
    assert "recursion limit" in result.diagnostics[0].message

    path = _write(tmp_path, "deep-parser.pie", source)
    assert cli.main(["check", str(path)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-P1000 error:" in captured.err
    assert "Traceback" not in captured.err
    assert "RecursionError" not in captured.err


def test_psec_002_semantic_recursion_stops_emit_sql_before_ir_and_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expression = " + ".join(["1"] * 1200)
    source = f"derive total() -> Int not null:\n    {expression}\n"
    parse_result = parse_source(source, path="deep-semantic.pie")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)

    assert [diagnostic.code for diagnostic in semantic_result.diagnostics] == [
        "PIE-S2006"
    ]
    assert "recursion limit" in semantic_result.diagnostics[0].message

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("IR and SQL must not run after semantic recursion")

    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
    path = _write(tmp_path, "deep-semantic.pie", source)

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-S2006 error:" in captured.err
    assert "Traceback" not in captured.err
    assert "RecursionError" not in captured.err


def test_psec_003_backslash_and_quote_payload_stays_in_one_sql_literal() -> None:
    assert render_literal("path\\to\\file") == "E'path\\\\to\\\\file'"

    rendered = render_literal("\\'; DROP TABLE users; --")

    assert rendered == "E'\\\\''; DROP TABLE users; --'"
    assert rendered.count("E'") == 1


def test_psec_004_nul_is_rejected_and_public_backend_reports_pie_b1000() -> None:
    with pytest.raises(ValueError, match="identifiers must not contain NUL"):
        quote_identifier("bad\x00name")
    with pytest.raises(ValueError, match="string literals must not contain NUL"):
        render_literal("bad\x00value")

    script_ir = _compile_ir(SOURCE)
    source = next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, SourceIR)
    )
    bad_source = replace(
        source,
        connector=replace(source.connector, arguments=("bad\x00table",)),
    )
    result = emit_postgres_sql(
        ScriptIR(
            definitions=tuple(
                bad_source if definition is source else definition
                for definition in script_ir.definitions
            )
        )
    )

    assert result.artifacts == ()
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-B1000"]
    assert "\x00" not in result.diagnostics[0].message


@pytest.mark.parametrize("alias_kind", ["same-file", "hard-link", "symlink"])
def test_psec_005_output_aliases_are_rejected_without_modifying_targets(
    alias_kind: str,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = _write(tmp_path, "input.pie", SOURCE)
    input_bytes = input_path.read_bytes()

    if alias_kind == "same-file":
        output_path = input_path
        target_path = input_path
    elif alias_kind == "hard-link":
        output_path = tmp_path / "hard-link.pie"
        os.link(input_path, output_path)
        target_path = input_path
    else:
        target_path = _write(tmp_path, "target.sql", "original SQL\n")
        output_path = tmp_path / "output.sql"
        output_path.symlink_to(target_path)

    assert _emit(input_path, output_path) == 2

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "output path must" in captured.err
    if alias_kind == "symlink":
        assert output_path.is_symlink()
        assert target_path.read_text(encoding="utf-8") == "original SQL\n"
    else:
        assert target_path.read_bytes() == input_bytes
        assert output_path.read_bytes() == input_bytes


def test_psec_005_backend_error_neither_creates_nor_truncates_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = _write(tmp_path, "input.pie", SOURCE)
    existing_output = _write(tmp_path, "existing.sql", "original SQL\n")
    missing_output = tmp_path / "missing.sql"
    diagnostic = Diagnostic(
        code="PIE-B1000",
        severity=Severity.ERROR,
        message="unsupported backend case",
        location=SourceLocation(path=str(input_path), line=1, column=1),
    )
    monkeypatch.setattr(
        cli.sql_api,
        "emit_postgres_sql",
        lambda script_ir: SqlResult(artifacts=(), diagnostics=(diagnostic,)),
    )

    assert _emit(input_path, existing_output) == 1
    capsys.readouterr()
    assert existing_output.read_text(encoding="utf-8") == "original SQL\n"

    assert _emit(input_path, missing_output) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "PIE-B1000 error:" in captured.err
    assert not missing_output.exists()


def test_psec_006_cli_text_is_escaped_but_sql_artifacts_are_unchanged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    diagnostic = Diagnostic(
        code="PIE-P1000",
        severity=Severity.ERROR,
        message="line\nescape\x1bnul\x00delete\x7f",
        location=SourceLocation(path="bad\npath.pie", line=1, column=2),
    )

    cli._render_diagnostics((diagnostic,), fallback_path=Path("fallback.pie"))

    diagnostic_output = capsys.readouterr()
    assert diagnostic_output.out == ""
    assert diagnostic_output.err == (
        "bad\\npath.pie:1:2 PIE-P1000 error: line\\nescape\\x1bnul\\x00delete\\x7f\n"
    )

    sql = "SELECT '\n\x1b\x00\x7f'"
    artifact = SqlArtifact(
        name="raw_controls",
        kind=SqlArtifactKind.RELATION,
        sql=sql,
    )
    cli._print_sql_artifacts((artifact,))

    artifact_output = capsys.readouterr()
    assert artifact_output.out == f"{sql}\n"
    assert artifact_output.err == ""


def test_psec_007_production_dependencies_and_secret_ignores_remain_minimal() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    dependencies = project["project"]["dependencies"]

    assert len(dependencies) == 1
    assert dependencies[0].startswith("antlr4-python3-runtime")
    for removed in ("pydantic", "rich", "sqlglot", "typer"):
        assert not any(requirement.startswith(removed) for requirement in dependencies)

    ignored = set(Path(".gitignore").read_text(encoding="utf-8").splitlines())
    assert {".env", ".env.*"} <= ignored


def test_phase_5_cli_commands_work_without_runtime_or_compiler_wrappers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["--help"]) == 0
    assert "check" in capsys.readouterr().out

    assert cli.main(["--version"]) == 0
    assert capsys.readouterr().out.startswith("pietto ")

    path = _write(tmp_path, "valid.pie", SOURCE)
    assert cli.main(["check", str(path)]) == 0
    assert capsys.readouterr().out == f"OK: {path}\n"

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0
    emitted = capsys.readouterr()
    assert 'SELECT\n    "email" AS "email"\nFROM "users"\n' == emitted.out
    assert emitted.err == ""

    source = inspect.getsource(cli).lower()
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
    ):
        assert forbidden not in source


def test_security_completion_audit_contains_no_legacy_diagnostic_codes() -> None:
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


def _compile_ir(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="security-completion-audit.pie")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _emit(input_path: Path, output_path: Path) -> int:
    return cli.main(
        [
            "emit-sql",
            str(input_path),
            "--dialect",
            "postgres",
            "--output",
            str(output_path),
        ]
    )


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path
