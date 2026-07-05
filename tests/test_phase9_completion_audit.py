from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
import tomllib
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
import pietto.cli_json as cli_json
import pietto.ir as ir_api
import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECT_CONFIG_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "config.py"
PROJECT_CHECK_SOURCE = REPO_ROOT / "src" / "pietto" / "_project" / "check.py"
PHASE9_PLAN = "docs/plan/phase-9-sql-backend-architecture-dialect-strategy.md"
PHASE9_DOCUMENTS = (
    "docs/spec/sql-dialect-source-contract-v1.md",
    "docs/plan/phase-9-sqlglot-evaluation.md",
    "docs/spec/sql-backend-abstraction-contract-v1.md",
    "docs/spec/mysql-sql-generation-mvp-v1.md",
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
BASELINE_HASHES = {
    "grammar/Pietto.g4": (
        "54484b73f76ae051e0e4f27cc47bc99a0687da7c0e4f40ab4da06a640a54369a"
    ),
    "src/pietto/generated/Pietto.interp": (
        "10dfbb6de46e4fe29a18783edd3dab3c59d302ea1c38897b7f9eb7c64f4162be"
    ),
    "src/pietto/generated/Pietto.tokens": (
        "631f7484827db7e25e28702e87b3438cf61b42391ac154770dfc4478103b684d"
    ),
    "src/pietto/generated/PiettoLexer.interp": (
        "0558f4336baaba062edb5e68b99c03dca59a5217609fee948284f2594e35c82f"
    ),
    "src/pietto/generated/PiettoLexer.py": (
        "e9898f4fad83917395d81a1862fd803f93ef74003174b69cd469e7c20fc1a41a"
    ),
    "src/pietto/generated/PiettoLexer.tokens": (
        "c52d4b019c2a4e9673a81d906793278fac389a684f7dc664e660bac3415c739b"
    ),
    "src/pietto/generated/PiettoParser.py": (
        "c3e2fd3a8f6ccee156f7b828e3135eb298d84c8ec8c2817ed1cb8a9ed142f537"
    ),
    "src/pietto/generated/PiettoVisitor.py": (
        "dc1b11e34ec9123fbaef6c8d65038fa86b82ec4416adc8032fc1310a9becd6e1"
    ),
    "src/pietto/generated/__init__.py": (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ),
}
POSTGRES_GOLDEN_HASHES = {
    "tests/fixtures/golden/emit_sql_active_users.sql": (
        "5a0878c84b208c906d8affe0f54706118f14bee40951ab8e25c70c90e95f43d3"
    ),
    "tests/fixtures/golden/emit_sql_active_user_emails.sql": (
        "d5aaf1e4cc3c334c72c3978858358b4df21ea3572daa0ecdda0fee0ceff74ee0"
    ),
    "tests/fixtures/golden/emit_sql_compatibility_literals_identifiers.sql": (
        "691b04423af4cb4861d5aa56c0ae865181a738abca153f37ae7c69c1a8857477"
    ),
    "tests/fixtures/golden/emit_sql_compatibility_expressions.sql": (
        "943f92d70fd433d803cf5409b02254f9f7801822270eb5ca567d6cdde9387c46"
    ),
    "tests/fixtures/golden/emit_sql_compatibility_ordering_metadata.sql": (
        "b4e2d6a0bfa3ddff91b75892ddc071ec9199d41512e826a2ad81bac76e23752c"
    ),
}


def test_phase9_documents_and_all_seven_slices_are_complete() -> None:
    required_paths = (PHASE9_PLAN, *PHASE9_DOCUMENTS)
    for path in required_paths:
        assert (REPO_ROOT / path).is_file()

    plan = _read(PHASE9_PLAN)
    assert "**Phase 9 SQL Backend Architecture & Dialect Strategy is complete.**" in (
        plan
    )
    assert "All seven slices are complete." in plan

    slice_names = (
        "Readiness And Compatibility Frame",
        "PostgreSQL Compatibility Corpus",
        "Dialect Capability And Source Contract",
        "SQLGlot Evaluation",
        "Backend Abstraction Contract",
        "MySQL MVP Contract",
        "Completion Audit",
    )
    for number, name in enumerate(slice_names, start=1):
        assert f"{number}. **{name}**: complete." in plan

    documents = (
        plan,
        _read("README.md"),
        _read("AGENTS.md"),
        _read("docs/spec/pietto-v0.9.md"),
    )
    for path in required_paths:
        assert any(path in document for document in documents)


def test_phase9_contracts_are_consistent_and_fail_closed() -> None:
    combined = "\n".join(_read(path) for path in PHASE9_DOCUMENTS)

    _assert_contains_all(
        combined,
        (
            "Initial physical connectors are dialect-specific.",
            "`postgres.table(Text)` remains unchanged.",
            "`mysql.table(Text)`",
            "The internal backend boundary remains `ScriptIR -> SqlResult`.",
            "absent capability = unsupported",
            "approved only for a future isolated Phase 10 MySQL-generation spike",
            "PostgreSQL migration is not approved.",
            "emit_mysql_sql(script_ir: ScriptIR) -> SqlResult",
            "`matches/2` is explicitly absent from the MySQL MVP.",
            "It must not map to `LENGTH`",
            "CLI dialect selection remains explicit and closed.",
            "`PIE-B1000`",
        ),
    )

    assert "planning/specification-only and is not implemented" in _read(
        "docs/spec/sql-backend-abstraction-contract-v1.md"
    )


def test_phase9_postgres_compatibility_corpus_is_complete_and_unchanged() -> None:
    for path, expected_hash in POSTGRES_GOLDEN_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    json_fixtures = {
        "tests/fixtures/golden/check_types.json",
        "tests/fixtures/golden/check_sources_users_warning.json",
        "tests/fixtures/golden/emit_sql_active_users.json",
    }
    for path in json_fixtures:
        parsed = json.loads(_read(path))
        assert isinstance(parsed, dict)

    plan = _read(PHASE9_PLAN)
    _assert_contains_all(
        plan,
        (
            "five byte-exact SQL fixtures",
            "two structural `check` JSON fixtures",
            "one structural `emit-sql` JSON fixture",
            "`public.users` is rendered as the single quoted identifier "
            '`"public.users"`',
            "metadata no-op behavior",
            "ordered multiple artifacts",
        ),
    )


def test_phase9_public_postgres_api_cli_and_json_v1_are_unchanged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    signature = inspect.signature(sql_api.emit_postgres_sql)
    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")
    assert not hasattr(ir_api, "compile_to_ir")
    assert not hasattr(sql_api, "compile_to_sql")

    assert cli_json._SCHEMA_VERSION == 1
    assert (
        cli.main(
            [
                "emit-sql",
                "examples/tables/active_users.pietto",
                "--dialect",
                "postgres",
                "--format=json",
            ]
        )
        == 0
    )
    emitted = _read_json_document(capsys)
    assert set(emitted) == EMIT_KEYS
    assert emitted["schema_version"] == 1
    assert emitted["dialect"] == "postgres"

    assert (
        cli.main(
            [
                "emit-sql",
                "examples/tables/active_users.pietto",
                "--dialect",
                "sqlite",
                "--format=json",
            ]
        )
        == 2
    )
    rejected = _read_json_document(capsys)
    assert set(rejected) == EMIT_KEYS
    assert rejected["schema_version"] == 1
    errors = cast(list[dict[str, object]], rejected["cli_errors"])
    assert errors == [
        {
            "kind": "unsupported_dialect",
            "message": "unsupported SQL dialect: sqlite",
            "path": None,
        }
    ]


def test_phase9_prohibited_production_capabilities_remain_absent() -> None:
    runtime_sources = _runtime_sources()
    runtime_sources_without_project_config_or_check = tuple(
        path
        for path in runtime_sources
        if path not in {PROJECT_CONFIG_SOURCE, PROJECT_CHECK_SOURCE}
    )
    source_text = "\n".join(_read_path(path) for path in runtime_sources)
    source_text_without_project_config = "\n".join(
        _read_path(path) for path in runtime_sources_without_project_config_or_check
    )
    lowered_source = source_text.lower()
    lowered_source_without_project_config = source_text_without_project_config.lower()
    cli_source = _read("src/pietto/cli.py")
    sql_exports = _read("src/pietto/sql/__init__.py")

    for forbidden_fragment in (
        "def emit_sql(",
        "class SqlBackend",
        "BackendCapabilities",
        "sqlglot",
        "compile_to_ir",
        "compile_to_sql",
        "schema_version = 2",
        '"schema_version": 2',
    ):
        assert forbidden_fragment.lower() not in lowered_source

    assert '"--project"' in cli_source
    assert "def _run_project_check(" in cli_source
    assert "discover_project_inputs(root)" in cli_source
    assert "compile_project" not in lowered_source
    assert "load_project_config" not in lowered_source_without_project_config
    assert "project_loader" not in lowered_source
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in cli_source
    assert "mysql.table" in source_text
    assert "def emit_mysql_sql(" in source_text
    assert "return mysql_backend.emit_mysql_sql" in cli_source
    assert "emit_mysql_sql" not in sql_exports
    assert '"emit_sql"' not in sql_exports

    forbidden_imports = {
        "click",
        "fastapi",
        "flask",
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
    assert _runtime_import_roots(
        runtime_sources_without_project_config_or_check
    ).isdisjoint(forbidden_imports)
    assert _runtime_call_attributes(runtime_sources).isdisjoint(
        {"connect", "execute", "glob", "rglob", "walk"}
    )


def test_phase9_dependencies_lock_grammar_and_generated_files_match_baseline() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    assert project["project"]["version"] == "0.1.0"
    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["project"]["dependencies"]
    ] == ["antlr4-python3-runtime"]
    assert project["build-system"]["build-backend"] == "uv_build"
    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["build-system"]["requires"]
    ] == ["uv_build"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert 'name = "sqlglot"' not in _read("uv.lock")

    for path, expected_hash in BASELINE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash


def test_phase9_diagnostics_and_runtime_threat_boundary_are_audited() -> None:
    legacy_pattern = re.compile(r"(?<!PIE-)\bP[0-9]{4}\b")
    assert _legacy_diagnostic_codes(legacy_pattern) == []

    plan = _read(PHASE9_PLAN)
    _assert_contains_all(
        plan,
        (
            "requires a separate threat model",
            "credential storage, access, rotation, and redaction",
            "SSRF-like risks",
            "parameterization, least privilege",
            "transactions, cancellation, retries",
            "driver, connector, and plugin supply-chain risk",
            "Phase 9.5 Static Typing And Source Extension Hardening follows Phase 9",
        ),
    )


def _read(path: str) -> str:
    return _read_path(REPO_ROOT / path)


def _read_path(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_contains_all(text: str, expected: tuple[str, ...]) -> None:
    normalized = " ".join(text.split())
    for value in expected:
        assert " ".join(value.split()) in normalized


def _read_json_document(
    capsys: pytest.CaptureFixture[str],
) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    assert not captured.out.endswith("\n\n")
    return cast(dict[str, object], json.loads(captured.out))


def _runtime_sources() -> tuple[Path, ...]:
    return tuple(
        path
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    )


def _runtime_import_roots(paths: tuple[Path, ...]) -> set[str]:
    imports: set[str] = set()
    for path in paths:
        tree = ast.parse(_read_path(path), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.add(node.module.partition(".")[0])
    return imports


def _runtime_call_attributes(paths: tuple[Path, ...]) -> set[str]:
    attributes: set[str] = set()
    for path in paths:
        tree = ast.parse(_read_path(path), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                attributes.add(node.func.attr)
    return attributes


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _legacy_diagnostic_codes(
    pattern: re.Pattern[str],
) -> list[tuple[Path, str]]:
    matches: list[tuple[Path, str]] = []
    roots = (
        REPO_ROOT / "src",
        REPO_ROOT / "tests",
        REPO_ROOT / "docs",
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
    )
    for root in roots:
        paths = root.rglob("*") if root.is_dir() else (root,)
        for path in paths:
            if not path.is_file() or path.suffix not in {
                ".md",
                ".pietto",
                ".py",
                ".txt",
            }:
                continue
            matches.extend(
                (path.relative_to(REPO_ROOT), match.group())
                for match in pattern.finditer(_read_path(path))
            )
    return matches
