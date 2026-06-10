from __future__ import annotations

import ast
import json
import re
import tomllib
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_ROOT = REPO_ROOT / "tests" / "fixtures" / "golden"
CHECK_KEYS = {
    "schema_version",
    "command",
    "ok",
    "path",
    "diagnostics",
    "cli_errors",
}
EMIT_KEYS = CHECK_KEYS | {"dialect", "artifacts", "output"}


def test_phase7_documentation_records_complete_single_file_scope() -> None:
    phase7 = _read("docs/plan/phase-7-developer-workflow-stability.md")
    phase8 = _read("docs/plan/phase-8-project-model-configuration-planning.md")
    readme = _read("README.md")
    agents = _read("AGENTS.md")
    json_spec = _read("docs/spec/cli-json-v1.md")
    resource_design = _read("docs/plan/phase-7-resource-depth-budget-design.md")
    workflow_design = _read("docs/plan/phase-7-future-workflow-design.md")

    assert "Phase 7 Developer Workflow & Stability Foundation: Complete." in phase7
    for slice_number in range(1, 8):
        assert f"{slice_number}. **" in phase7
    assert "**Phase 7 Developer Workflow & Stability Foundation: complete**" in readme
    assert (
        "Current phase: Phase 8 Project Model & Configuration Planning complete."
        in agents
    )
    assert "**Phase 8 planning/specification is complete.**" in phase8
    assert "Every Phase 8 slice is documentation, specification" in phase8
    for slice_name in (
        "Readiness And Decision Frame",
        "Configuration Contract",
        "Root And Path Semantics",
        "Multi-file Semantics",
        "CLI And JSON Design",
        "Project Resource Model",
        "Completion Audit",
    ):
        assert slice_name in phase8
    assert "schema version 1" in json_spec
    assert "complete denial-of-service protection" in resource_design
    assert "no global UTF-8 source byte limit" not in resource_design
    assert "no lexer token-count limit" not in resource_design
    assert "no workflow capability is implemented" in workflow_design

    combined = "\n".join((phase7, phase8, readme, agents, json_spec, workflow_design))
    for deferred in (
        "SQL execution",
        "database connection",
        "schema introspection",
        "multi-file",
        "watch mode",
        "LSP",
    ):
        assert deferred.lower() in combined.lower()


def test_phase7_json_v1_commands_keep_one_document_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(REPO_ROOT)

    assert cli.main(["check", "examples/basic/types.pie", "--format=json"]) == 0
    checked = _read_json_document(capsys)
    assert set(checked) == CHECK_KEYS
    assert checked["schema_version"] == 1
    assert checked["command"] == "check"
    assert checked["ok"] is True
    assert "version" not in checked

    output = tmp_path / "active-users.sql"
    assert (
        cli.main(
            [
                "emit-sql",
                "examples/tables/active_users.pie",
                "--dialect",
                "postgres",
                "--format",
                "json",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    emitted = _read_json_document(capsys)
    assert set(emitted) == EMIT_KEYS
    assert emitted["schema_version"] == 1
    assert emitted["command"] == "emit-sql"
    assert emitted["ok"] is True
    assert emitted["output"] == {"path": str(output), "written": True}
    assert "version" not in emitted

    artifacts = cast(list[dict[str, object]], emitted["artifacts"])
    assert len(artifacts) == 1
    assert output.read_text(encoding="utf-8") == f"{artifacts[0]['sql']}\n"


def test_phase7_golden_output_strategy_remains_focused_and_dependency_free() -> None:
    assert {path.name for path in GOLDEN_ROOT.iterdir() if path.is_file()} == {
        "check_sources_users_warning.json",
        "check_types.json",
        "emit_sql_active_user_emails.sql",
        "emit_sql_active_users.json",
        "emit_sql_active_users.sql",
    }

    golden_tests = _read("tests/test_cli_golden_outputs.py")
    assert "examples/" in golden_tests
    assert "json.loads(" in golden_tests
    assert ".read_bytes()" in golden_tests
    assert "tmp_path" not in golden_tests
    assert "update" not in golden_tests.lower()

    dependencies = _production_dependencies()
    assert not any("snapshot" in dependency.lower() for dependency in dependencies)


def test_phase7_resource_budget_contract_and_diagnostics_are_stable() -> None:
    assert parser_api._MAX_SOURCE_UTF8_BYTES == 1_048_576
    assert parser_api._MAX_NON_EOF_TOKENS == 200_000

    oversized = parser_api.parse_source(
        "#" + "a" * parser_api._MAX_SOURCE_UTF8_BYTES,
        path="oversized.pie",
    )
    too_many_tokens = parser_api.parse_source(
        "+" * (parser_api._MAX_NON_EOF_TOKENS + 1),
        path="too-many-tokens.pie",
    )

    assert oversized.ast is None
    assert [diagnostic.code for diagnostic in oversized.diagnostics] == ["PIE-P1006"]
    assert too_many_tokens.ast is None
    assert [diagnostic.code for diagnostic in too_many_tokens.diagnostics] == [
        "PIE-P1007"
    ]

    diagnostics = _read("docs/spec/diagnostics.md")
    assert "`PIE-P1006` | UTF-8 source byte budget exceeded" in diagnostics
    assert "`PIE-P1007` | Raw non-EOF lexer token budget exceeded" in diagnostics


def test_phase7_prohibited_capabilities_and_dependencies_remain_absent() -> None:
    dependencies = _production_dependencies()
    assert dependencies == ["antlr4-python3-runtime>=4.13.2"]
    for forbidden in (
        "click",
        "pydantic",
        "pygls",
        "rich",
        "sqlglot",
        "tomli",
        "typer",
        "watchdog",
    ):
        assert not any(
            dependency.lower().startswith(forbidden) for dependency in dependencies
        )

    assert not hasattr(cli, "compile_to_ir")
    assert not hasattr(cli, "compile_to_sql")
    assert not hasattr(ir_api, "compile_to_ir")
    assert not hasattr(sql_api, "compile_to_sql")
    assert not (REPO_ROOT / "pietto.toml").exists()

    runtime_sources = tuple(
        path
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )
    source_text = "\n".join(
        path.read_text(encoding="utf-8") for path in runtime_sources
    )
    assert "pietto.toml" not in source_text
    for forbidden_name in (
        "discover_project_root",
        "load_project_config",
        "compile_to_ir",
        "compile_to_sql",
    ):
        assert forbidden_name not in source_text

    forbidden_imports = {
        "click",
        "fastapi",
        "flask",
        "http",
        "pydantic",
        "pygls",
        "requests",
        "rich",
        "socket",
        "sqlalchemy",
        "sqlglot",
        "tomli",
        "tomllib",
        "typer",
        "urllib",
        "watchdog",
    }
    assert _runtime_import_roots(runtime_sources).isdisjoint(forbidden_imports)


def test_phase7_diagnostic_codes_use_canonical_prefix() -> None:
    legacy_pattern = re.compile(r"(?<!PIE-)\bP[0-9]{4}\b")
    legacy_codes: list[tuple[Path, str]] = []

    for root_name in ("src", "tests", "docs"):
        for path in (REPO_ROOT / root_name).rglob("*"):
            if path.is_file() and path.suffix in {".md", ".pie", ".py", ".txt"}:
                legacy_codes.extend(
                    (path.relative_to(REPO_ROOT), match.group())
                    for match in legacy_pattern.finditer(
                        path.read_text(encoding="utf-8")
                    )
                )
    for name in ("README.md", "AGENTS.md"):
        path = REPO_ROOT / name
        legacy_codes.extend(
            (path.relative_to(REPO_ROOT), match.group())
            for match in legacy_pattern.finditer(path.read_text(encoding="utf-8"))
        )

    assert legacy_codes == []


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _read_json_document(
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _production_dependencies() -> list[str]:
    project = tomllib.loads(_read("pyproject.toml"))
    return cast(list[str], project["project"]["dependencies"])


def _runtime_import_roots(paths: tuple[Path, ...]) -> set[str]:
    imports: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.add(node.module.partition(".")[0])
    return imports
