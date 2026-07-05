from __future__ import annotations

import hashlib
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DECISION_PATH = "docs/plan/phase-14-first-implementation-candidate-decision.md"
READINESS_PATH = "docs/plan/phase-14-relation-composition-implementation-readiness.md"
PHASE13_INPUTS = (
    "docs/plan/phase-13-relation-composition-planning.md",
    "docs/spec/relationship-relation-role-contract-v1.md",
    "docs/spec/composition-scope-name-resolution-contract-v1.md",
    "docs/spec/composition-sql-shape-contract-v1.md",
    "docs/spec/composition-security-diagnostics-contract-v1.md",
    "tests/test_phase13_completion_audit.py",
)
STATUS_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
)

INPUT_HASHES = {
    READINESS_PATH: (
        "b47cf0ccaaaf19960bc9c31c5f57d0952c47a2abef0dc42abdedf19f8dcd8fb9"
    ),
    "docs/plan/phase-13-relation-composition-planning.md": (
        "fe2518aa3837fa99b942fc3bf7bf05bfccdc8e2e3e66de9a12ce99d66949ead6"
    ),
    "docs/spec/relationship-relation-role-contract-v1.md": (
        "fa3d881856a89368645f3a71d9f1ffa6129d758f5960b697bbca1eae8737cf66"
    ),
    "docs/spec/composition-scope-name-resolution-contract-v1.md": (
        "e37a3da9700ac4f8cb01c01240b064588bdf87fc6facbbcf6ba25883742608fb"
    ),
    "docs/spec/composition-sql-shape-contract-v1.md": (
        "2cd2044ccf9c6100a9bcde1767f09f8c25f7565135bc7d4043abdb61548ae56a"
    ),
    "docs/spec/composition-security-diagnostics-contract-v1.md": (
        "2383731c2b9d78f8cf73da8e9d47f973b6eef93eb20e0f03d8f045307b788534"
    ),
    "tests/test_phase13_completion_audit.py": (
        "e375d58a320dd053412cb2888aad8acb89cf450f9ade40fa5900752345357383"
    ),
}

FILE_HASHES = {
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
    "grammar/Pietto.g4": (
        "54484b73f76ae051e0e4f27cc47bc99a0687da7c0e4f40ab4da06a640a54369a"
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
        "aa6ab2ddf8ed8e889e8d75de224467565b7e6034cf068b44d602807fdd554924"
    ),
}

GROUP_HASHES = {
    "frontend": "7ecd994ab99d95af792ea628de9de236940c1c46ced49599ea482cffab49ee4f",
    "semantic": "de7bc94d972739411d98458a89d293aecd5cea4326a9cf51a8b065c2cf8846cd",
    "ir": "57097f43ba5e0ffa8d531b827b7029c9104b85ab3dc0657889cccd28caec5249",
    "sql": "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b",
    "generated": "7ac3aea913b1453a972456be0171a2c292991e71bde3e94a4056b4bf537b5c4e",
    "cli": "31d91f9a6f7d0705398add8c8516cf3b9b81c09cb3a7fb9141b6f96470f0216b",
}

GOLDENS_HASH = "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004"


def test_slice2_status_inputs_and_single_candidate_decision() -> None:
    decision = _read(DECISION_PATH)

    assert "# Phase 14 Slice 2: First Implementation Candidate Decision" in decision
    assert "**Phase 14 Slice 2 is complete as a candidate decision only.**" in decision
    assert (
        "**Phase 14 Slice 3: Relationship Metadata Syntax Contract And Parse-Only "
        "AST\nImplementation is complete.**" in decision
    )
    assert (
        "**Phase 14 implementation has started only at the parser and AST boundary.**"
        in decision
    )
    assert (
        "**Slice 4 remains unauthorized until separately reviewed and approved.**"
        in decision
    )

    for path in (
        READINESS_PATH,
        *PHASE13_INPUTS,
        "tests/test_phase14_planning_audit.py",
    ):
        assert path in decision
        assert (REPO_ROOT / path).is_file()

    for path, expected_hash in INPUT_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    chosen = re.findall(r"\*\*Chosen candidate: ([^.]+)\.\*\*", decision)
    deferred = re.findall(r"\*\*Deferred candidate: ([^.]+)\.\*\*", decision)
    assert chosen == ["Relationship and endpoint metadata syntax foundation"]
    assert deferred == ["Ambiguity and name-ownership foundation"]
    assert chosen[0] != deferred[0]


def test_candidate_comparison_covers_required_dimensions_and_rationale() -> None:
    decision = _read(DECISION_PATH)
    normalized = " ".join(decision.split())

    for candidate in (
        "Relationship and endpoint metadata syntax foundation",
        "Ambiguity and name-ownership foundation",
    ):
        assert candidate in decision

    for dimension in (
        "User-visible value",
        "Implementation risk",
        "Grammar risk",
        "AST risk",
        "Semantic risk",
        "IR risk",
        "SQL and backend risk",
        "CLI and JSON risk",
        "Testability",
        "Future query composition usefulness",
        "Future nested semantics usefulness",
        "Future semantic query core usefulness",
    ):
        assert dimension in decision

    for rationale in (
        "small, observable language-surface foundation",
        "direct parser and AST tests",
        "no production multi-input scope to resolve",
        "risk creating an internal abstraction",
        "parse-only and AST-only",
    ):
        assert rationale in normalized


def test_slice3_exact_allowlist_and_untouched_boundaries_are_complete() -> None:
    decision = _read(DECISION_PATH)

    required_allowed_paths = (
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/generated/Pietto.interp",
        "src/pietto/generated/Pietto.tokens",
        "src/pietto/generated/PiettoLexer.interp",
        "src/pietto/generated/PiettoLexer.py",
        "src/pietto/generated/PiettoLexer.tokens",
        "src/pietto/generated/PiettoParser.py",
        "src/pietto/generated/PiettoVisitor.py",
        "tests/test_phase14_relationship_metadata_parser.py",
        "tests/test_phase14_relationship_metadata_completion_audit.py",
        "docs/spec/relationship-endpoint-metadata-syntax-v1.md",
    )
    for path in required_allowed_paths:
        assert f"`{path}`" in decision

    for untouched in (
        "src/pietto/generated/__init__.py",
        "src/pietto/parser_api.py",
        "src/pietto/errors.py",
        "src/pietto/semantic/**",
        "src/pietto/ir/**",
        "src/pietto/sql/**",
        "src/pietto/cli.py",
        "src/pietto/cli_json.py",
        ".github/workflows/ci.yml",
        "pyproject.toml",
        "uv.lock",
    ):
        assert f"`{untouched}`" in decision

    assert "every Phase 13 contract" not in decision
    assert "any Phase 13 contract" in decision
    assert "work must stop and request explicit scope expansion" in decision


def test_slice3_stage_impacts_are_decision_complete() -> None:
    decision = _read(DECISION_PATH)
    normalized = " ".join(decision.split())

    for required in (
        "| Grammar | Yes.",
        "| Generated ANTLR | Yes.",
        "| Parser and AST builder | AST builder only.",
        "| AST | Yes.",
        "| Parser API | No change.",
        "| Semantic analysis | No change.",
        "| IR | No change.",
        "| PostgreSQL and MySQL SQL | No change.",
        "| CLI | No command, option, exit-code, or presentation change.",
        "| JSON | No schema or serialization change",
        "| Runtime and database | No execution, connection, introspection",
    ):
        assert required in decision

    for expected in (
        "preserve one declaration name",
        "preserve exactly two source-ordered endpoints",
        "preserve each endpoint's local metadata name and referenced relation name",
        "preserve the full declaration span and each endpoint span",
        "separately from the existing semantic definition stream",
        "empty default for scripts that contain no relationship metadata",
        "exact accepted syntax is fixed in "
        "`docs/spec/relationship-endpoint-metadata-syntax-v1.md`",
    ):
        assert expected in normalized


def test_readiness_gates_tests_and_hard_non_goals_are_explicit() -> None:
    decision = _read(DECISION_PATH)
    normalized = " ".join(decision.split())

    for gate in (
        "normative exact syntax contract",
        "keyword, contextual-token, and reserved-word impact",
        "ANTLR generation and provenance expectations",
        "immutable AST node names, fields, tuple ordering, and defaults",
        "declaration and endpoint source-span ownership",
        "separation from the semantic definition stream",
        "explicit semantic non-impact",
        "explicit IR non-impact",
        "explicit PostgreSQL/MySQL and artifact-byte non-impact",
        "JSON v1, CLI, and public API compatibility",
        "positive parser and AST tests",
        "negative malformed-form tests",
        "unchanged examples, fixtures, and all 15 goldens",
        "necessary fixed-hash updates with an explanation for each",
        "complete actual diff review before commit",
    ):
        assert gate in normalized

    for boundary in (
        "JOIN or relation composition",
        "CTEs, or subqueries",
        "SQL shape implementation",
        "relationship semantic validation",
        "relation-role semantics",
        "endpoint-role enforcement",
        "cardinality or fanout behavior",
        "measures, dimensions, aggregates",
        "nested table semantics",
        "ambiguity or name-ownership resolution",
        "permission gates",
        "runtime security",
        "threat model",
        "new diagnostic code",
        "database connection",
        "schema introspection",
        "JSON v2",
        "project mode",
        "LSP",
        "Web UI",
        "playground",
        "SQLGlot",
        "release",
        "publish",
        "signing",
        "upload",
        "attestation",
    ):
        assert boundary in normalized


def test_decision_is_prose_and_tables_without_syntax_or_sql_examples() -> None:
    decision = _read(DECISION_PATH)

    assert "```" not in decision
    assert re.search(re.escape("." + "pie") + r"\b", decision) is None
    assert re.search(r"\bPIE-[PSIB]\d{4}\b", decision) is None
    assert re.search(r"(?<!PIE-)\b[PSIB]\d{4}\b", decision) is None
    pseudo_source_pattern = re.compile(
        r"(?m)^(?:relationship|endpoint|from|select|join)\s+"
        r"[A-Za-z_][A-Za-z0-9_]*(?:\s*[:=]|\s+from\b)",
        re.IGNORECASE,
    )
    sql_example_pattern = re.compile(r"(?m)^\s*(?:SELECT|FROM|JOIN)\s+", re.IGNORECASE)
    assert pseudo_source_pattern.search(decision) is None
    assert sql_example_pattern.search(decision) is None


def test_production_generated_dependency_api_json_golden_and_ci_are_locked() -> None:
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
        "generated": _generated_paths(),
        "cli": (
            "src/pietto/cli.py",
            "src/pietto/cli_json.py",
        ),
    }
    for name, paths in groups.items():
        assert _aggregate_sha256(paths) == GROUP_HASHES[name]

    project = tomllib.loads(_read("pyproject.toml"))
    sql_api = _read("src/pietto/sql/__init__.py")
    mysql_backend = _read("src/pietto/sql/mysql.py")
    cli_json = _read("src/pietto/cli_json.py")
    workflow = _read(".github/workflows/ci.yml")
    all_block = re.search(r"(?s)__all__ = \[(?P<body>.*?)\]", sql_api)
    goldens = tuple(
        path
        for path in (REPO_ROOT / "tests/fixtures/golden").iterdir()
        if path.is_file()
    )

    assert project["project"]["version"] == "0.1.0"
    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["project"]["dependencies"]
    ] == ["antlr4-python3-runtime"]
    assert all_block is not None
    assert tuple(re.findall(r'"([^"]+)"', all_block.group("body"))) == (
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    )
    assert "emit_mysql_sql" not in sql_api
    assert "def emit_mysql_sql(" in mysql_backend
    assert "def emit_sql(" not in _runtime_text()
    assert "_SCHEMA_VERSION = 1" in cli_json
    assert "_SCHEMA_VERSION = 2" not in cli_json
    assert len(goldens) == 37
    assert _aggregate_files(goldens) == GOLDENS_HASH
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
    assert '"3.12"' in workflow
    assert '"3.13"' in workflow


def test_runtime_has_no_phase14_implementation_markers() -> None:
    runtime = _runtime_text().lower()

    for marker in (
        "relation composition",
        "relationship syntax",
        "relation-role syntax",
        "join lowering",
        "composition lowering",
        "join_one",
        "join_many",
        "permission gate",
        "authorization token",
        "capability token",
        "authority token",
        "runtime security",
        "threat model",
        "policy isolation",
        "safe sharing",
        "database connection",
        "schema introspection",
        "execute sql",
        "sqlglot",
    ):
        assert marker not in runtime


def test_status_documents_record_slice3_parse_only_implementation() -> None:
    documents = {path: _read(path) for path in STATUS_PATHS}

    for document in documents.values():
        normalized = " ".join(document.split())
        assert DECISION_PATH in document
        assert "Phase 14 Slice 2" in normalized
        assert "candidate decision" in normalized
        assert "Relationship and endpoint metadata syntax foundation" in normalized
        assert "Ambiguity and name-ownership foundation" in normalized
        assert "Phase 14 Slice 3" in normalized
        assert "parse-only" in normalized
        assert "AST" in normalized
        assert "Slice 4" in normalized
        assert "unauthorized" in normalized
        assert "docs/spec/relationship-endpoint-metadata-syntax-v1.md" in document

    combined = " ".join("\n".join(documents.values()).split())
    for boundary in (
        "relation composition",
        "JOIN",
        "SQL shape implementation",
        "relationship semantic validation",
        "relation-role syntax",
        "permission gate",
        "runtime security",
        "threat model",
        "diagnostic code",
        "database connection",
        "SQL execution",
        "schema introspection",
        "JSON v2",
        "project mode",
        "LSP",
        "Web UI",
        "playground",
        "release",
        "publish",
        "signing",
        "upload",
        "attestation",
        "SQLGlot",
        "not implemented",
    ):
        assert boundary in combined


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_paths(directory: str) -> tuple[str, ...]:
    root = REPO_ROOT / directory
    return tuple(
        path.relative_to(REPO_ROOT).as_posix() for path in sorted(root.glob("*.py"))
    )


def _generated_paths() -> tuple[str, ...]:
    return tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
        if path.is_file()
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
