from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import pietto.cli as cli
import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE10_PLAN = "docs/plan/phase-10-mysql-sql-generation-mvp.md"


def test_phase10_master_plan_exists_and_records_nine_ordered_slices() -> None:
    plan = _read(PHASE10_PLAN)

    assert "**Phase 10 MySQL SQL Generation MVP is complete.**" in plan
    assert "**Slice 1: Phase 10 Master Plan And Readiness Audit is complete.**" in (
        plan
    )
    slice_names = (
        "Phase 10 Master Plan And Readiness Audit",
        "SQLGlot Evaluation And Isolated Adapter Spike",
        "Dialect Dispatch Design",
        "MySQL Backend Skeleton",
        "MySQL Connector Semantic Surface",
        "MySQL Expression And Relation Rendering MVP",
        "MySQL Golden Corpus And PostgreSQL Regression Lock",
        "CLI Enablement For `--dialect mysql`",
        "Completion Audit",
    )
    for number, name in enumerate(slice_names, start=1):
        assert f"{number}. **{name}**" in plan


def test_phase10_is_generation_only_and_preserves_json_boundary() -> None:
    plan = _read(PHASE10_PLAN)
    normalized = " ".join(plan.split())

    for required in (
        "Phase 10 is SQL generation only.",
        "JSON schema version 1 remains the only runtime CLI JSON schema in Phase 10.",
        "JSON schema version 2 remains reserved for future explicit project "
        "and multi-file mode.",
        "SQL execution",
        "database driver",
        "connector execution",
        "schema introspection",
        "project mode",
        "watch mode",
        "LSP/editor integration",
        "Web UI",
    ):
        assert " ".join(required.split()) in normalized


def test_phase10_preserves_postgres_and_sqlglot_isolation_contracts() -> None:
    plan = _read(PHASE10_PLAN)

    for required in (
        "`emit_postgres_sql(ScriptIR) -> SqlResult`",
        "handwritten PostgreSQL backend as the byte-exact reference",
        "PostgreSQL-to-MySQL transpilation",
        "SQLGlot must never become:",
        "the Pietto parser or semantic analyzer",
        "a PostgreSQL backend replacement",
        "an optimizer or executor",
    ):
        assert required in plan


def test_phase10_documents_production_test_and_generated_typing_gates() -> None:
    plan = _read(PHASE10_PLAN)
    production = _jsonc("pyrightconfig.json")
    tests = json.loads(_read("pyrightconfig.tests.json"))
    vscode = json.loads(_read(".vscode/settings.json"))

    assert "uvx pyright" in plan
    assert "uvx pyright --project pyrightconfig.tests.json" in plan
    assert production["include"] == ["src/pietto"]
    assert production["exclude"] == ["src/pietto/generated"]
    assert production["ignore"] == ["src/pietto/generated"]
    assert tests == {
        "extends": "./pyrightconfig.json",
        "include": ["tests"],
    }
    assert vscode == {
        "python.analysis.exclude": ["src/pietto/generated/**"],
        "python.analysis.ignore": ["src/pietto/generated/**"],
    }


def test_phase10_keeps_mysql_skeleton_private_and_sqlglot_absent() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "pietto").rglob("*.py")
        if "generated" not in path.parts
    ).lower()

    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert 'name = "sqlglot"' not in _read("uv.lock")
    for forbidden in (
        "def emit_sql(",
        "sqlglot",
        "schema_version = 2",
        '"schema_version": 2',
    ):
        assert forbidden not in runtime_text
    assert "mysql.table" in runtime_text
    assert "def emit_mysql_sql(" in runtime_text
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert '_ENABLED_SQL_DIALECTS = ("postgres", "mysql")' in _read("src/pietto/cli.py")
    assert cli.main(["emit-sql", "missing.pietto", "--dialect", "sqlite"]) == 2


def test_phase10_status_documents_describe_private_mysql_rendering() -> None:
    combined = "\n".join(
        (
            _read("README.md"),
            _read("AGENTS.md"),
            _read("docs/spec/pietto-v0.9.md"),
        )
    )
    normalized = " ".join(combined.split())

    assert "Phase 10 MySQL SQL Generation MVP" in normalized
    assert "private MySQL backend" in normalized
    assert "closed renderer" in normalized


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _jsonc(path: str) -> dict[str, object]:
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", _read(path)))
