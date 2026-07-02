from __future__ import annotations

import hashlib
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = "docs/plan/phase-13-relation-composition-planning.md"
CONTRACT_PATHS = (
    "docs/spec/relationship-relation-role-contract-v1.md",
    "docs/spec/composition-scope-name-resolution-contract-v1.md",
    "docs/spec/composition-sql-shape-contract-v1.md",
    "docs/spec/composition-security-diagnostics-contract-v1.md",
)
STATUS_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    PLAN_PATH,
)

FILE_HASHES = {
    "pyproject.toml": "021682ef880fe748f1655d4d70fcc549db4336ac39db2b29a835762ab1723d50",
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
    "grammar/Pietto.g4": (
        "54484b73f76ae051e0e4f27cc47bc99a0687da7c0e4f40ab4da06a640a54369a"
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
        "5640b45133915b03bc6457f9eb2429832d547b1118f25f972e82a97d34ec5535"
    ),
}

GROUP_HASHES = {
    "frontend": "7ecd994ab99d95af792ea628de9de236940c1c46ced49599ea482cffab49ee4f",
    "semantic": "18392ababb9f0382c31e821bbd82a5347a804ada0de8d56fa79a035a7dc07fa2",
    "ir": "45efae911ce554b9484b6a8f9e63abf30c0c72d6be239e218cfa360de92d92b7",
    "sql": "f23a79dd0b5620f04ad3329abcd7ad368c1b223ded90fed0f52f1f35b9de18d3",
    "generated": "7ac3aea913b1453a972456be0171a2c292991e71bde3e94a4056b4bf537b5c4e",
    "cli": "bab5a160ac57ad45045836f2f4396e7383baf03c20bb8a18d51e9fd2476a716f",
}

CONTRACT_HASHES = {
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
}

GOLDENS_HASH = "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004"


def test_all_phase13_slices_and_documents_are_complete() -> None:
    plan = _read(PLAN_PATH)
    slice_names = (
        "Master Plan And Baseline Audit",
        "Relationship / Relation Role Contract",
        "Composition Scope And Name Resolution Contract",
        "Join / Composition SQL Shape Contract",
        "Security Boundary And Diagnostics Contract",
        "Completion Audit And Documentation",
    )

    assert (
        "**Phase 13 Relation Composition And Relationship Planning is complete.**"
        in (plan)
    )
    for number, name in enumerate(slice_names, start=1):
        assert f"**Slice {number}: {name} is complete.**" in plan

    for path in (PLAN_PATH, *CONTRACT_PATHS):
        assert (REPO_ROOT / path).is_file()


def test_phase13_contracts_remain_planning_only_and_byte_locked() -> None:
    for path in CONTRACT_PATHS:
        contract = _read(path)
        normalized = " ".join(contract.split())

        assert _sha256(REPO_ROOT / path) == CONTRACT_HASHES[path]
        assert "planning and contract work only" in normalized
        assert "defines no currently accepted Pietto syntax" in normalized
        assert "No future slice receives implementation authorization" in normalized
        assert "adds or authorizes none of the following" in normalized
        for boundary in (
            "grammar",
            "parser",
            "AST",
            "semantic",
            "IR",
            "SQL backend",
            "CLI",
            "JSON",
            "runtime",
            "public API",
        ):
            assert boundary in normalized

    combined = _normalized_paths(CONTRACT_PATHS)
    for boundary in (
        "dependency",
        "package",
        "version",
        "CI",
        "golden",
        "SQLGlot",
    ):
        assert boundary in combined


def test_production_compiler_and_phase13_implementation_markers_are_absent() -> None:
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


def test_grammar_records_only_the_later_approved_metadata_boundary() -> None:
    grammar = _read("grammar/Pietto.g4")

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

    phase13_text = _phase13_text()
    legacy_suffix_pattern = re.compile(re.escape("." + "pie") + r"\b")
    assert legacy_suffix_pattern.search(phase13_text) is None
    assert ".pietto" in _read(PLAN_PATH)


def test_public_api_dependency_package_and_sqlglot_boundaries_are_locked() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    sql_api = _read("src/pietto/sql/__init__.py")
    mysql_backend = _read("src/pietto/sql/mysql.py")
    all_block = re.search(r"(?s)__all__ = \[(?P<body>.*?)\]", sql_api)

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
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["requires-python"] == ">=3.12"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert "sqlglot" not in _read("uv.lock").lower()


def test_json_cli_golden_audits_and_ci_remain_unchanged() -> None:
    cli = _read("src/pietto/cli.py")
    cli_json = _read("src/pietto/cli_json.py")
    workflow = _read(".github/workflows/ci.yml")
    golden_root = REPO_ROOT / "tests/fixtures/golden"
    goldens = tuple(path for path in golden_root.iterdir() if path.is_file())

    assert "_SCHEMA_VERSION = 1" in cli_json
    assert "_SCHEMA_VERSION = 2" not in cli_json
    assert re.findall(r'subparsers\.add_parser\(\n        "([^"]+)"', cli) == [
        "check",
        "emit-sql",
        "explain",
    ]
    for marker in (
        '"project"',
        '"watch"',
        "--watch",
        "playground",
        "lsp",
        "web ui",
    ):
        assert marker not in cli.lower()

    assert '"--project"' in cli
    assert "def _run_project_check(" in cli
    assert "discover_project_inputs(root)" in cli
    assert "compile_project" not in cli.lower()
    assert "load_project_config" not in cli.lower()
    assert "project_loader" not in cli.lower()

    assert len(goldens) == 37
    assert _aggregate_files(goldens) == GOLDENS_HASH
    assert "CLASSIFIED_FIXTURES" in _read("scripts/check_goldens.py")
    assert "_compare_generated_files" in _read("scripts/check_generated.py")
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)
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


def test_phase13_diagnostics_remain_family_only_and_stage_owned() -> None:
    contracts = {path: _read(path) for path in CONTRACT_PATHS}

    for contract in contracts.values():
        for family in ("PIE-Pxxxx", "PIE-Sxxxx", "PIE-Ixxxx", "PIE-Bxxxx"):
            assert family in contract
        assert "introduces no diagnostic code" in contract

    concrete_pattern = re.compile(r"\bPIE-[PSIB]\d{4}\b")
    concrete_references = {
        path: concrete_pattern.findall(contract)
        for path, contract in contracts.items()
        if concrete_pattern.search(contract)
    }
    established_unknown_field_code = "PIE-" + "S" + "2102"
    assert concrete_references == {
        "docs/spec/composition-scope-name-resolution-contract-v1.md": [
            established_unknown_field_code
        ]
    }
    scope_contract = contracts[
        "docs/spec/composition-scope-name-resolution-contract-v1.md"
    ]
    normalized_scope_contract = " ".join(scope_contract.split())
    assert "existing unknown-field behavior" in normalized_scope_contract
    assert "is not changed by this planning contract" in normalized_scope_contract
    security_contract = " ".join(
        contracts["docs/spec/composition-security-diagnostics-contract-v1.md"].split()
    )
    assert "reserves no concrete diagnostic code" in security_contract


def test_security_non_claims_and_threat_model_absence_are_explicit() -> None:
    contract = _read("docs/spec/composition-security-diagnostics-contract-v1.md")
    normalized = " ".join(contract.split()).lower()

    for non_claim in (
        "access control",
        "privacy enforcement",
        "runtime authorization",
        "authentication",
        "database permissions or grants",
        "row-level security",
        "masking",
        "policy isolation",
        "safe data sharing",
        "secure execution",
        "protection from direct database access outside pietto",
    ):
        assert non_claim in normalized

    assert (
        "a successful pietto check or sql emission must not be represented as proof "
        "that a caller may access data"
    ) in normalized
    assert "this slice does not define a threat model" in normalized
    assert "compiler metadata alone is not an enforcement mechanism" in normalized


def test_status_documents_record_planning_only_completion_and_non_goals() -> None:
    documents = {path: _read(path) for path in STATUS_PATHS}

    for path, document in documents.items():
        normalized = " ".join(document.split())
        if path != PLAN_PATH:
            assert PLAN_PATH in document
        assert "Phase 13" in normalized
        assert "Slices 1 through 6 are complete" in normalized
        assert "planning, contract, and audit work only" in normalized
        assert "Future implementation work requires a new explicit phase" in normalized

    combined = " ".join("\n".join(documents.values()).split())
    for boundary in (
        "relation composition",
        "JOIN",
        "SQL shape implementation",
        "relationship syntax",
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


def _phase13_text() -> str:
    paths = (
        REPO_ROOT / PLAN_PATH,
        *(REPO_ROOT / path for path in CONTRACT_PATHS),
        *sorted((REPO_ROOT / "tests").glob("test_phase13_*.py")),
    )
    return "\n".join(path.read_text(encoding="utf-8") for path in paths)


def _normalized_paths(paths: tuple[str, ...]) -> str:
    return " ".join("\n".join(_read(path) for path in paths).split())
