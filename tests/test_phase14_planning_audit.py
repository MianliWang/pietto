from __future__ import annotations

import hashlib
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = "docs/plan/phase-14-relation-composition-implementation-readiness.md"
DECISION_PATH = "docs/plan/phase-14-first-implementation-candidate-decision.md"
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

PHASE13_HASHES = {
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
        "65c38ddda4a97c7ef79a534d3c8b5081eef99a0e0e321743e638685ae24f3db9"
    ),
}

FILE_HASHES = {
    "pyproject.toml": "021682ef880fe748f1655d4d70fcc549db4336ac39db2b29a835762ab1723d50",
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
    "grammar/Pietto.g4": (
        "6a5f6bc45d4f66011a7898fe783b6600beaf73f3b984d6539f975cf0cd7f3110"
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
        "f25c22282e443e0ade67fab3eebef0606137f6aacb4918b0fd0c7847bf160ec2"
    ),
    "scripts/package_smoke.py": (
        "61de7eec8f26476e39d05305642ecde0a55d1030513ce91f627cac45517c1131"
    ),
}

GROUP_HASHES = {
    "frontend": "4af1382a5d1e4464f492f0c267d500fbeb667bff819dcbcad11b346f33d87e8b",
    "semantic": "6ebe460bd8a7603d9b1e34df4bf398ff36400d3499fabb81f1ed07253087ea80",
    "ir": "b29ccb7bf6df2a168059698446631664b02393a5e99382c9c109cdb022fbd846",
    "sql": "87b3f0a6baee9990f22fa01ff18a545274525006bc1c95ed5f37ccfdcf3e0c5c",
    "generated": "44dad9dc2fced336b8e102a558be94786fb7618fd860a3ef6f6d56e49fdebf1f",
    "cli": "235d4e50c3474306253dfc6b118e2518b3e300e90f7fbe9903263a39cbdc42a0",
}

GOLDENS_HASH = "66190fd279c318c33bc85fbe877a73fefc05791c922c64a4ca7b733b4e53c502"


def test_phase14_plan_records_final_transition_status_and_slice_order() -> None:
    plan = _read(PLAN_PATH)
    slice_names = (
        "Final Transition Readiness Gate",
        "First Implementation Candidate Decision",
        "Explicitly Authorized Minimal Vertical Slice",
        "Backend Compatibility And Completion Audit",
    )

    assert "# Phase 14: Relation Composition Implementation Readiness" in plan
    assert "**Phase 14 Slice 1: Final Transition Readiness Gate is complete.**" in plan
    assert (
        "**Phase 14 Slice 2: First Implementation Candidate Decision is complete.**"
        in plan
    )
    assert (
        "**Phase 14 Slice 3: Relationship Metadata Syntax Contract And Parse-Only "
        "AST\nImplementation is complete.**" in plan
    )
    assert (
        "**Phase 14 implementation has started only at the parser and AST "
        "boundary.**" in plan
    )
    assert "**Slice 4 requires separate explicit authorization.**" in plan
    assert "Slice 1 is planning-only" in plan
    assert "Phase 14 must not become another broad planning phase" in plan
    assert DECISION_PATH in plan

    offsets = [
        plan.index(f"{number}. **{name}**")
        for number, name in enumerate(slice_names, start=1)
    ]
    assert offsets == sorted(offsets)


def test_phase13_inputs_are_referenced_and_byte_locked() -> None:
    plan = _read(PLAN_PATH)

    for path in PHASE13_INPUTS:
        assert path in plan
        assert (REPO_ROOT / path).is_file()
        assert _sha256(REPO_ROOT / path) == PHASE13_HASHES[path]

    normalized = " ".join(plan.split())
    assert "Phase 13 remains complete as planning, contract, and audit work only" in (
        normalized
    )
    assert "not accepted syntax" in normalized


def test_two_candidates_and_concrete_slice2_decision_are_recorded() -> None:
    plan = _read(PLAN_PATH)
    normalized = " ".join(plan.split())

    for candidate in (
        "Relationship and endpoint metadata syntax foundation",
        "Ambiguity and name-ownership foundation",
    ):
        assert candidate in plan

    for dimension in ("Value", "Risk", "Surface area", "Testability"):
        assert dimension in plan

    assert "Slice 1 did not choose between these candidates" in normalized
    assert (
        "Slice 2 chose the relationship and endpoint metadata syntax foundation"
        in normalized
    )
    assert "deferred the ambiguity and name-ownership foundation" in normalized
    assert "not a continuation of general planning" in normalized
    assert "did not implement either candidate" in normalized

    for decision in (
        "First real implementation candidate",
        "Files to touch",
        "Files to keep untouched",
        "Grammar impact",
        "AST impact",
        "Semantic impact",
        "IR impact",
        "SQL impact",
        "CLI and JSON impact",
        "Deferred behavior",
    ):
        assert decision in plan


def test_readiness_gates_and_hard_non_goals_are_explicit() -> None:
    plan = _read(PLAN_PATH)
    normalized = " ".join(plan.split())

    for gate in (
        "one candidate is selected and the other is explicitly deferred",
        "exact Slice 3 file allowlist",
        "grammar impact and generated-file provenance",
        "AST shape and source-span ownership",
        "semantic scope and name-ownership effects",
        "IR inclusion or exclusion",
        "SQL backend non-impact or fail-closed behavior",
        "PostgreSQL/MySQL parity expectations",
        "diagnostic family ownership",
        "fixture and golden policy",
        "JSON v1 and public API compatibility",
        "complete actual diff is reviewed before commit",
    ):
        assert gate in normalized

    for boundary in (
        "JOIN or relation composition",
        "multiple relation inputs",
        "SQL shape implementation",
        "relationship, endpoint, relationship-role, or relation-role syntax",
        "permission gate",
        "runtime authorization",
        "runtime security",
        "threat model",
        "new diagnostic code",
        "SQL execution",
        "database or connector connection",
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


def test_production_grammar_generated_workflow_and_scripts_are_locked() -> None:
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
    ):
        assert marker not in runtime


def test_grammar_adds_only_metadata_syntax_without_diagnostic_code() -> None:
    grammar = _read("grammar/Pietto.g4")
    plan = _read(PLAN_PATH)

    for token_or_rule in (
        "RELATIONSHIP: 'relationship';",
        "ENDPOINT: 'endpoint';",
        "relationshipDefinition",
        "relationshipEndpoint",
    ):
        assert token_or_rule in grammar

    for token_or_rule in (
        "JOIN:",
        "ROLE:",
        "AUTHORITY:",
        "PURPOSE:",
        "GATEWAY:",
        "CHECKPOINT:",
        "PERMISSION:",
        "CAPABILITY:",
        "joinClause",
        "relationshipDeclaration",
        "relationRole",
    ):
        assert token_or_rule not in grammar

    assert "```" not in plan
    assert re.search(re.escape("." + "pie") + r"\b", plan) is None
    assert ".pietto" in plan
    assert re.search(r"\bPIE-[PSIB]\d{4}\b", plan) is None
    assert re.search(r"(?<!PIE-)\b[PSIB]\d{4}\b", plan) is None


def test_api_dependency_package_json_golden_and_ci_boundaries_are_locked() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    sql_api = _read("src/pietto/sql/__init__.py")
    mysql_backend = _read("src/pietto/sql/mysql.py")
    cli_json = _read("src/pietto/cli_json.py")
    workflow = _read(".github/workflows/ci.yml")
    all_block = re.search(r"(?s)__all__ = \[(?P<body>.*?)\]", sql_api)
    golden_root = REPO_ROOT / "tests/fixtures/golden"
    goldens = tuple(path for path in golden_root.iterdir() if path.is_file())

    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["requires-python"] == ">=3.12"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert "sqlglot" not in _read("uv.lock").lower()

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
    assert len(goldens) == 15
    assert _aggregate_files(goldens) == GOLDENS_HASH

    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
    assert '"3.12"' in workflow
    assert '"3.13"' in workflow
    for marker in (
        "contents: write",
        "id-token:",
        "upload-artifact",
        "release",
        "publish",
        "deploy",
        "attestation",
    ):
        assert marker not in workflow.lower()


def test_status_documents_record_phase14_slice3_without_later_implementation() -> None:
    documents = {path: _read(path) for path in STATUS_PATHS}

    for document in documents.values():
        normalized = " ".join(document.split())
        assert PLAN_PATH in document
        assert "Phase 13" in normalized
        assert "planning, contract, and audit work only" in normalized
        assert "Phase 14 Slice 1" in normalized
        assert "Phase 14 Slice 2" in normalized
        assert "Phase 14 Slice 3" in normalized
        assert "planning/readiness work only" in normalized
        assert "parse-only" in normalized
        assert "AST" in normalized
        assert (
            "relationship and endpoint metadata syntax foundation" in normalized.lower()
        )
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
        "CTE",
        "subquery",
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
