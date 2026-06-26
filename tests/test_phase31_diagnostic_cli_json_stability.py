from __future__ import annotations

import json
import re
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.sql as sql_api
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-31-v02-hardening-and-stable-completion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/v02-hardening-and-stable-completion-v1.md"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CLI_PATH = REPO_ROOT / "src/pietto/cli.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"
SQL_API_PATH = REPO_ROOT / "src/pietto/sql/__init__.py"
POSTGRES_BACKEND_PATH = REPO_ROOT / "src/pietto/sql/postgres.py"
MYSQL_BACKEND_PATH = REPO_ROOT / "src/pietto/sql/mysql.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
SRC_ROOT = REPO_ROOT / "src/pietto"

LIMIT_MESSAGE = "Limit must be a static integer from 0 to 9223372036854775807"
HISTORICAL_DIAGNOSTIC_CODES = frozenset({"PIE-S2316", "PIE-S2322"})


def test_phase31_slice6_plan_and_spec_lock_static_audit_scope() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    combined = f"{plan} {spec}"

    for required in (
        "Phase 31 Slice 6 is complete as Diagnostic / CLI / JSON stability "
        "hardening, tests, static audit, status, and docs work only",
        "Slice 7 is complete. Slice 8 is planned only",
        "Diagnostic inventory audit distinguishes active diagnostics from "
        "historical/retired diagnostics",
        "every currently source-emitted PIE diagnostic code is documented",
        "every documented active diagnostic code corresponds to current behavior",
        "historical/retired/reserved rows may intentionally have no current "
        "source emission",
        "`PIE-S2307` is active and present in the central diagnostics inventory",
        "`PIE-S2322` remains explicitly historical/retired",
        "`PIE-B1000` describes current selected PostgreSQL/private MySQL backend "
        "fail-closed behavior",
        "No diagnostic code, message, severity, ordering, or location behavior changes",
        "No CLI behavior change, JSON v1 schema expansion, new JSON fields, "
        "JSON v2, or public MySQL API expansion",
    ):
        assert required in combined

    for forbidden in (
        "behavior fix",
        "diagnostic behavior change",
        "diagnostic code/message/severity/order/location behavior change",
        "CLI behavior change",
        "JSON v1 schema expansion",
        "new JSON fields",
        "JSON v2",
        "public MySQL API expansion",
        "tooling adoption",
        "`ty` adoption",
        "coverage threshold",
        "v0.2 completion declaration in Slice 6",
        "Phase 32 implementation",
        "Slice 8 work",
    ):
        assert forbidden in combined


def test_diagnostics_inventory_active_and_historical_codes_are_classified() -> None:
    source_codes = _source_diagnostic_codes()
    rows = _diagnostic_inventory_rows()
    documented_codes = set(rows)
    historical_codes = {
        code
        for code, meaning in rows.items()
        if "Historical" in meaning or "retired" in meaning.lower()
    }

    assert "PIE-S2307" in source_codes
    assert rows["PIE-S2307"] == (
        "Static relation LIMIT operand is invalid; emits error message "
        "`Limit must be a static integer from 0 to 9223372036854775807`"
    )
    assert historical_codes == HISTORICAL_DIAGNOSTIC_CODES
    assert "PIE-S2322" in historical_codes
    assert "PIE-S2322" not in source_codes
    assert rows["PIE-S2322"] == (
        "Historical `satisfying` IR/SQL lowering gate, retired after source "
        "pipeline enablement"
    )
    assert source_codes == documented_codes - historical_codes


def test_limit_diagnostic_current_behavior_and_json_shape_are_stable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = _limit_source("postgres.table", "missing")
    parse_result = parse_source(source, path="limit-diagnostic.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    error_diagnostics = [
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in error_diagnostics
    ] == [("PIE-S2307", LIMIT_MESSAGE)]
    assert error_diagnostics[0].severity is Severity.ERROR
    assert error_diagnostics[0].suggestion is None

    input_path = _write(tmp_path / "limit-diagnostic.pietto", source)
    assert cli.main(["check", str(input_path), "--format=json"]) == 1
    document = _read_json(capsys)

    assert set(document) == {
        "schema_version",
        "command",
        "ok",
        "path",
        "diagnostics",
        "cli_errors",
    }
    assert document["schema_version"] == 1
    assert document["command"] == "check"
    assert document["ok"] is False
    assert document["path"] == str(input_path)
    assert document["cli_errors"] == []

    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert set(diagnostic) == {
        "code",
        "severity",
        "message",
        "location",
        "suggestion",
    }
    assert diagnostic["code"] == "PIE-S2307"
    assert diagnostic["severity"] == "error"
    assert diagnostic["message"] == LIMIT_MESSAGE
    assert diagnostic["suggestion"] is None

    location = cast(dict[str, object], diagnostic["location"])
    assert set(location) == {"path", "line", "column", "end_line", "end_column"}
    assert location["path"] == str(input_path)
    assert isinstance(location["line"], int)
    assert isinstance(location["column"], int)


def test_private_mysql_backend_diagnostic_json_shape_is_stable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = _write(
        tmp_path / "enum-count-risk.pietto",
        _enum_count_source("mysql.table"),
    )

    assert (
        cli.main(["emit-sql", str(input_path), "--dialect", "mysql", "--format=json"])
        == 1
    )
    document = _read_json(capsys)

    assert set(document) == {
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    }
    assert document["schema_version"] == 1
    assert document["command"] == "emit-sql"
    assert document["dialect"] == "mysql"
    assert document["ok"] is False
    assert document["path"] == str(input_path)
    assert document["cli_errors"] == []
    assert document["artifacts"] == []
    assert document["output"] is None

    diagnostics = cast(list[dict[str, object]], document["diagnostics"])
    assert [diagnostic["code"] for diagnostic in diagnostics] == ["PIE-B1000"]
    assert [diagnostic["severity"] for diagnostic in diagnostics] == ["error"]
    assert all(
        set(diagnostic)
        == {
            "code",
            "severity",
            "message",
            "location",
            "suggestion",
        }
        for diagnostic in diagnostics
    )


def test_cli_json_v1_success_shape_and_private_mysql_dispatch_are_stable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_path = _write(tmp_path / "valid-mysql.pietto", _valid_source("mysql.table"))

    assert (
        cli.main(["emit-sql", str(input_path), "--dialect", "mysql", "--format=json"])
        == 0
    )
    document = _read_json(capsys)

    assert set(document) == {
        "schema_version",
        "command",
        "ok",
        "path",
        "dialect",
        "diagnostics",
        "cli_errors",
        "artifacts",
        "output",
    }
    assert document["schema_version"] == 1
    assert document["command"] == "emit-sql"
    assert document["ok"] is True
    assert document["path"] == str(input_path)
    assert document["dialect"] == "mysql"
    assert document["diagnostics"] == []
    assert document["cli_errors"] == []
    assert document["output"] is None

    artifacts = cast(list[dict[str, object]], document["artifacts"])
    assert len(artifacts) == 1
    assert set(artifacts[0]) == {"kind", "name", "sql"}
    assert artifacts[0]["kind"] == "relation"
    assert artifacts[0]["name"] == "selected"
    assert "SELECT" in str(artifacts[0]["sql"])


def test_backend_b1000_inventory_matches_selected_backend_posture() -> None:
    diagnostics = _read(DIAGNOSTICS_PATH)
    postgres = _read(POSTGRES_BACKEND_PATH)
    mysql = _read(MYSQL_BACKEND_PATH)

    assert (
        "| `PIE-B1000` | Selected PostgreSQL/private MySQL SQL backend emission "
        "case is unsupported or invalid |" in diagnostics
    )
    assert "currently emitted only by PostgreSQL" not in diagnostics
    for backend_source in (postgres, mysql):
        assert 'code="PIE-B1000"' in backend_source
        assert "severity=Severity.ERROR" in backend_source
    assert "PostgreSQL SQL emission is not implemented for" in postgres
    assert "MySQL SQL emission is not implemented for" in mysql


def test_static_audit_no_cli_json_public_api_or_tooling_surface_was_added() -> None:
    cli_source = _read(CLI_PATH)
    cli_json = _read(CLI_JSON_PATH)
    sql_api_source = _read(SQL_API_PATH)
    pyproject = _read(PYPROJECT_PATH)
    combined_docs = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert "emit_mysql_sql" not in sql_api_source
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli_source
    assert "return mysql_backend.emit_mysql_sql" in cli_source
    assert "schema_version" in cli_json
    assert "_SCHEMA_VERSION = 1" in cli_json
    for forbidden in (
        '"types"',
        '"type_output"',
        '"metadata"',
        "schema_version = 2",
        "json_v2",
        "explain",
    ):
        assert forbidden not in cli_json.lower()
    for forbidden in (
        "ty",
        "coverage",
        "mutation",
        "publish",
        "release",
    ):
        assert forbidden not in pyproject.lower()

    for required in (
        "No diagnostic code, message, severity, ordering, or location behavior changes",
        "No CLI behavior change",
        "JSON v1 schema expansion",
        "new JSON fields",
        "JSON v2",
        "public MySQL API expansion",
        "tooling evaluation",
        "`ty`",
        "coverage addition",
    ):
        assert required in combined_docs


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _source_diagnostic_codes() -> set[str]:
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in SRC_ROOT.rglob("*.py")
    )
    return set(re.findall(r"code\s*=\s*['\"](PIE-[A-Z]\d{4})['\"]", source))


def _diagnostic_inventory_rows() -> dict[str, str]:
    rows: dict[str, str] = {}
    for match in re.finditer(
        r"^\| `(PIE-[A-Z]\d{4})` \| (?P<meaning>.+) \|$",
        _read(DIAGNOSTICS_PATH),
        flags=re.MULTILINE,
    ):
        rows[match.group(1)] = match.group("meaning")
    return rows


def _limit_source(connector: str, limit: str) -> str:
    return (
        "shape User:\n"
        "    id: Int not null\n"
        f'source users: User is {connector}("users")\n'
        "query selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        f"    limit {limit}\n"
    )


def _valid_source(connector: str) -> str:
    return (
        "shape User:\n"
        "    id: Int not null\n"
        f'source users: User is {connector}("users")\n'
        "query selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
    )


def _enum_count_source(connector: str) -> str:
    return (
        "enum Status:\n"
        "    draft\n"
        "shape Event:\n"
        "    status: Status not null\n"
        f'source events: Event is {connector}("events")\n'
        "query selected:\n"
        "    from events\n"
        "    select:\n"
        "        known_statuses = count(status)\n"
    )


def _write(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    document = json.loads(captured.out)
    assert isinstance(document, dict)
    return cast(dict[str, object], document)
