from __future__ import annotations

import hashlib
import inspect
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

import pietto.cli_json as cli_json
import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE13_PLAN = "docs/plan/phase-13-relation-composition-planning.md"

FILE_HASHES = {
    "pyproject.toml": "021682ef880fe748f1655d4d70fcc549db4336ac39db2b29a835762ab1723d50",
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
    "grammar/Pietto.g4": (
        "d75052cfc4c5de426388cc9d8a34eef607e8023a5e1789f2e497979ea2dde9f6"
    ),
    ".github/workflows/ci.yml": (
        "c2ba73d04dab3331ca19577f2cf4250274671aa37ec4f84f293429e118b6c4c5"
    ),
    "scripts/validate.py": (
        "6a52494385d5c010101e2304b554ff76afcd9bb44d101783c43b205af688e6a4"
    ),
    "scripts/check_generated.py": (
        "b126059cd0aebe9535fceb9b0a1b1c09ee1ba22af13f70d276d7e013c49c60e7"
    ),
    "scripts/check_goldens.py": (
        "23e271e0138e6b7ac189e27f33c557e04300301adff8f49747999e0c4b50c2e9"
    ),
    "scripts/package_smoke.py": (
        "61de7eec8f26476e39d05305642ecde0a55d1030513ce91f627cac45517c1131"
    ),
}

GROUP_HASHES = {
    "frontend": "06ff1d647427b4e937321ed525866059266ddc2bc292c050a458647365d95123",
    "semantic": "dfa4af8c0dd699431ac068f1ee007e3a744d9384fe1b602aa5ab682a1f42579b",
    "ir": "7438c72875751eeadf8b12b3aad1825499061f3f4e0dd73d8c1a339c614ae884",
    "sql": "67aeafa622d3147b08930cebcf18862322eec692d547d328b18966afa81f3530",
    "generated": "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1",
    "cli": "235d4e50c3474306253dfc6b118e2518b3e300e90f7fbe9903263a39cbdc42a0",
}

GOLDENS_HASH = "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004"


def test_phase13_master_plan_records_planning_status_and_slice_order() -> None:
    plan = _read(PHASE13_PLAN)
    slice_names = (
        "Master Plan And Baseline Audit",
        "Relationship / Relation Role Contract",
        "Composition Scope And Name Resolution Contract",
        "Join / Composition SQL Shape Contract",
        "Security Boundary And Diagnostics Contract",
        "Completion Audit And Documentation",
    )

    assert "# Phase 13: Relation Composition And Relationship Planning" in plan
    assert (
        "**Phase 13 Relation Composition And Relationship Planning is complete.**"
        in (plan)
    )
    assert "**Slice 1: Master Plan And Baseline Audit is complete.**" in plan
    assert "**Slice 2: Relationship / Relation Role Contract is complete.**" in plan
    assert (
        "**Slice 3: Composition Scope And Name Resolution Contract is complete.**"
        in plan
    )
    assert "**Slice 4: Join / Composition SQL Shape Contract is complete.**" in plan
    assert (
        "**Slice 5: Security Boundary And Diagnostics Contract is complete.**" in plan
    )
    assert "**Slice 6: Completion Audit And Documentation is complete.**" in plan
    assert "Slices 1 through 6 are complete" in plan
    assert "planning, contract, and audit work only" in " ".join(plan.split())
    assert "Phase 12 SQL Feature Expansion I is complete" in plan

    offsets = [
        plan.index(f"{number}. **{name}**")
        for number, name in enumerate(slice_names, start=1)
    ]
    assert offsets == sorted(offsets)


def test_phase13_plan_defines_required_concepts_and_hard_boundaries() -> None:
    plan = _read(PHASE13_PLAN)
    normalized = " ".join(plan.split())

    for required in (
        "planning-only throughout all six slices",
        "Future implementation work requires a new explicit phase",
        "generic SQL builder",
        "relation-as-gateway",
        "relation-as-checkpoint",
        "Query context matching",
        "Input relation versus output relation",
        "Cardinality",
        "one-to-many",
        "many-to-one",
        "Semantic versus runtime permission",
        "SQL-lowerable invariant",
        "Fail-closed backend behavior",
        "explicit SQL artifacts",
        "hidden runtime post-processing",
        "PostgreSQL/MySQL supported-feature parity",
        "MySQL emitter remains private",
        "15 reviewed golden files",
    ):
        assert required in normalized

    for prohibited in (
        "change `grammar/Pietto.g4` or generated ANTLR files",
        "change parser, AST, semantic, IR, SQL backend, CLI, JSON, scripts, CI",
        "implement JOIN",
        "implement GROUP BY, aggregate functions, HAVING",
        "implement runtime database permissions",
        "execute SQL",
        "connect to a database or connector",
        "introspect schemas",
        "implement project mode",
        "implement JSON v2",
        "add SQLGlot or any other dependency",
        "expose the MySQL emitter publicly",
        "add a generic public `emit_sql(...)`",
        "capability tokens",
    ):
        assert prohibited in normalized


def test_phase13_security_diagnostics_and_backend_planning_are_explicit() -> None:
    plan = _read(PHASE13_PLAN)
    normalized = " ".join(plan.split())

    for diagnostic_family in (
        "PIE-Pxxxx",
        "PIE-Sxxxx",
        "PIE-Ixxxx",
        "PIE-Bxxxx",
    ):
        assert diagnostic_family in plan

    for required in (
        "Compiler planning is not database enforcement",
        "runtime authorization is not implemented",
        "row-level security",
        "safe views",
        "masking",
        "security barriers",
        "capability tokens",
        "must not claim financial-grade safety",
        "CI/CD controls",
        "database-level enforcement",
        "PostgreSQL remains the public reference backend",
        "SQLGlot",
    ):
        assert required in normalized

    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", plan) is None


def test_phase13_status_documents_are_scope_aware() -> None:
    documents = {
        "README.md": _read("README.md"),
        "AGENTS.md": _read("AGENTS.md"),
        "docs/spec/pietto-v0.9.md": _read("docs/spec/pietto-v0.9.md"),
    }

    for document in documents.values():
        normalized = " ".join(document.split())
        assert "Phase 12 SQL Feature Expansion I" in normalized
        assert "Phase 13" in normalized
        assert "relation composition" in normalized.lower()
        assert PHASE13_PLAN in document
        assert "Slice 1" in normalized
        assert "Slice 2" in normalized
        assert "Slice 3" in normalized
        assert "Slice 4" in normalized
        assert "Slice 5" in normalized
        assert "Slice 6" in normalized
        assert "docs/spec/composition-scope-name-resolution-contract-v1.md" in (
            document
        )
        assert "docs/spec/composition-sql-shape-contract-v1.md" in document
        assert "docs/spec/composition-security-diagnostics-contract-v1.md" in (document)

    combined = " ".join("\n".join(documents.values()).split())
    assert "Phase 12 SQL Feature Expansion I is complete" in combined
    assert "Phase 13 is complete" in combined
    assert "Slices 1 through 6 are complete" in combined
    assert "planning, contract, and audit work only" in combined
    assert "JOIN" in combined
    assert "relation roles" in combined
    assert "runtime security" in combined
    assert "not implemented" in combined


def test_slice1_locks_compiler_workflow_and_golden_boundaries() -> None:
    for path, expected_hash in FILE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    groups = {
        "frontend": (
            "src/pietto/__init__.py",
            "src/pietto/ast_nodes.py",
            "src/pietto/ast_builder.py",
            "src/pietto/errors.py",
            "src/pietto/indentation.py",
            "src/pietto/parser_api.py",
        ),
        "semantic": _module_paths("src/pietto/semantic"),
        "ir": _module_paths("src/pietto/ir"),
        "sql": _module_paths("src/pietto/sql"),
        "generated": tuple(
            path.relative_to(REPO_ROOT).as_posix()
            for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
            if path.is_file()
        ),
        "cli": (
            "src/pietto/cli.py",
            "src/pietto/cli_json.py",
        ),
    }
    for name, paths in groups.items():
        assert _aggregate_sha256(paths) == GROUP_HASHES[name]

    golden_root = REPO_ROOT / "tests/fixtures/golden"
    inventory = tuple(path for path in golden_root.iterdir() if path.is_file())
    assert len(inventory) == 37
    assert _aggregate_files(inventory) == GOLDENS_HASH


def test_public_api_json_dependency_and_package_boundaries_are_unchanged() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    runtime_text = _runtime_text()
    signature = inspect.signature(sql_api.emit_postgres_sql)

    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["requires-python"] == ">=3.12"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
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
    assert "def emit_mysql_sql(" in runtime_text
    assert "def emit_sql(" not in runtime_text
    assert cli_json._SCHEMA_VERSION == 1
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert "sqlglot" not in _read("uv.lock").lower()


def test_runtime_has_no_relationship_gate_or_composition_implementation() -> None:
    runtime_text = _runtime_text()
    normalized_runtime = runtime_text.lower()

    for marker in (
        "relationship gate",
        "capability token",
        "join_one",
        "join_many",
        "relation-as-gateway",
    ):
        assert marker not in normalized_runtime

    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", _new_phase13_text()) is None


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_paths(directory: str) -> tuple[str, ...]:
    root = REPO_ROOT / directory
    return tuple(
        path.relative_to(REPO_ROOT).as_posix() for path in sorted(root.glob("*.py"))
    )


def _aggregate_sha256(paths: tuple[str, ...]) -> str:
    return _aggregate_files(REPO_ROOT / path for path in paths)


def _aggregate_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _runtime_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
    )


def _new_phase13_text() -> str:
    paths = (
        PHASE13_PLAN,
        "docs/spec/composition-scope-name-resolution-contract-v1.md",
        "docs/spec/composition-sql-shape-contract-v1.md",
        "docs/spec/composition-security-diagnostics-contract-v1.md",
        "tests/test_phase13_planning_audit.py",
        "tests/test_phase13_composition_scope_contract.py",
        "tests/test_phase13_composition_sql_shape_contract.py",
        "tests/test_phase13_security_diagnostics_contract.py",
        "tests/test_phase13_completion_audit.py",
        "README.md",
        "AGENTS.md",
        "docs/spec/pietto-v0.9.md",
    )
    return "\n".join(_read(path) for path in paths)
