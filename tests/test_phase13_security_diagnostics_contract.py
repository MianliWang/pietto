from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "docs/spec/composition-security-diagnostics-contract-v1.md"
ROLE_CONTRACT_PATH = "docs/spec/relationship-relation-role-contract-v1.md"
SCOPE_CONTRACT_PATH = "docs/spec/composition-scope-name-resolution-contract-v1.md"
SQL_SHAPE_CONTRACT_PATH = "docs/spec/composition-sql-shape-contract-v1.md"
PLAN_PATH = "docs/plan/phase-13-relation-composition-planning.md"


def test_contract_exists_with_planning_only_status() -> None:
    contract_path = REPO_ROOT / CONTRACT_PATH
    contract = contract_path.read_text(encoding="utf-8")
    normalized = " ".join(contract.split())

    assert contract_path.is_file()
    assert "# Composition Security And Diagnostics Contract v1" in contract
    assert (
        "**Phase 13 Slice 5: Security Boundary And Diagnostics Contract is complete.**"
    ) in normalized
    assert "planning and contract work only" in normalized
    assert "defines no currently accepted Pietto syntax" in normalized
    assert "does not authorize" in normalized
    for earlier_contract in (
        ROLE_CONTRACT_PATH,
        SCOPE_CONTRACT_PATH,
        SQL_SHAPE_CONTRACT_PATH,
    ):
        assert earlier_contract in contract


def test_contract_defines_required_security_and_diagnostic_vocabulary() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split()).lower()

    for term in (
        "compiler semantic validation",
        "semantic authorization",
        "runtime authorization",
        "database enforcement",
        "security claim",
        "threat model",
        "deployment assumption",
        "policy isolation",
        "permission gate",
        "capability token",
        "authority token",
        "query context",
        "relation-as-gateway",
        "relation-as-checkpoint",
        "safe sharing claim",
        "diagnostic ownership",
        "cascade suppression",
        "source-span ownership",
    ):
        assert term in normalized

    assert "conceptual planning vocabulary" in normalized
    assert "not an implemented feature or guarantee" in normalized


def test_compiler_checks_are_not_runtime_authorization_or_security() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "must not be confused with runtime authorization",
        "must not be represented as proof that a caller may access data",
        "is not a security boundary",
        "Compiler metadata alone cannot prevent direct access",
        "Runtime permission failure remains outside the current compiler",
        "must not claim runtime security",
    ):
        assert required in normalized


def test_current_security_non_claims_are_complete() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split()).lower()

    for non_claim in (
        "access control",
        "privacy enforcement",
        "runtime authorization",
        "authentication",
        "database permissions or grants",
        "row-level security",
        "masking",
        "security barriers",
        "tenant isolation",
        "policy isolation",
        "safe data sharing",
        "secure execution",
        "protection from direct database access outside pietto",
    ):
        assert non_claim in normalized

    assert "these are current non-claims" in normalized


def test_contract_plans_but_does_not_define_a_threat_model() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "Any future security claim requires a separate, reviewed threat model",
        "deployment assumptions",
        "trust boundaries",
        "identity sources",
        "database controls",
        "runtime controls",
        "CI/CD controls",
        "bypass risks",
        "This slice does not define a threat model",
    ):
        assert required in normalized

    assert "approve a security architecture" in normalized
    assert "make a security guarantee" in normalized


def test_diagnostic_ownership_uses_families_without_concrete_codes() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for family in ("PIE-Pxxxx", "PIE-Sxxxx", "PIE-Ixxxx", "PIE-Bxxxx"):
        assert family in contract

    for responsibility in (
        "Parser, lexer, indentation, and malformed surface syntax",
        "Semantic name, scope, type, relationship contract, relation-role contract, "
        "cardinality, and query-context compatibility",
        "IR construction responsibility",
        "Selected-backend capability and faithful SQL-lowering responsibility",
    ):
        assert responsibility in normalized

    assert "introduces no diagnostic code" in normalized
    assert "reserves no concrete diagnostic code" in normalized
    assert re.search(r"\bPIE-[PSIB]\d{4}\b", contract) is None
    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", contract) is None


def test_semantic_backend_and_runtime_failures_remain_distinct() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "Unknown or ambiguous field",
        "Semantic name or scope diagnostic",
        "A security denial",
        "Valid Semantic IR unsupported by the selected backend",
        "Backend capability diagnostic",
        "Runtime or database permission failure",
        "Outside the current Pietto compiler",
        "Compile-time contract validation, if separately implemented",
        "Runtime access control",
    ):
        assert required in normalized


def test_source_span_ordering_and_cascade_planning_is_deterministic() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "define source-span ownership before any concrete code is reserved",
        "define deterministic ordering and cascade behavior",
        "should not produce many misleading downstream diagnostics",
        "Locations must not be fabricated",
        "handled explicitly rather than assigned to an unrelated source token",
    ):
        assert required in normalized


def test_fail_closed_and_sql_lowerable_invariants_are_preserved() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "Unsupported, unsafe, ambiguous, contradictory, or unproven semantics "
        "must fail closed",
        "deterministic diagnostics and no approximate SQL",
        "does not mean runtime denial enforcement",
        "Hidden runtime fallback",
        "in-memory row combination",
        "connector execution",
        "database introspection",
        "explicit SQL artifacts",
        "boundary between semantic acceptance and selected-backend capability",
        "No implicit authorization service",
    ):
        assert required in normalized


def test_contract_contains_no_examples_or_implementation_sketches() -> None:
    contract = _read(CONTRACT_PATH)
    lowered = contract.lower()

    assert "```" not in contract
    assert "join users" not in lowered
    assert "from users join" not in lowered
    assert "select users.id from" not in lowered
    assert "relationship foo:" not in lowered
    assert "role admin:" not in lowered
    assert "permission allow:" not in lowered
    assert "token admin:" not in lowered
    assert "select:" not in lowered
    assert "order by:" not in lowered
    assert (
        re.search(
            r"(?m)^\s*(relationship|role|authority|purpose|permission|token)"
            r"\s+\w+\s*:",
            lowered,
        )
        is None
    )


def test_api_json_dependency_golden_ci_version_and_source_boundaries_hold() -> None:
    contract = _read(CONTRACT_PATH)
    project = tomllib.loads(_read("pyproject.toml"))
    sql_api = _read("src/pietto/sql/__init__.py")
    cli_json = _read("src/pietto/cli_json.py")

    for non_goal in (
        "parser, AST, semantic, IR, SQL backend, or diagnostic implementation",
        "JOIN, relation composition, SQL shape, CTE, or subquery implementation",
        "a threat model or security claim",
        "concrete diagnostic codes or diagnostic-code reservations",
        "database or connector connection, execution, or schema introspection",
        "CLI behavior, JSON schema, public API, dependency, package, version, CI, "
        "or golden-fixture changes",
        "SQLGlot or another SQL-generation dependency",
    ):
        assert non_goal in " ".join(contract.split())

    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert '"emit_postgres_sql"' in sql_api
    assert '"emit_mysql_sql"' not in sql_api
    assert '"emit_sql"' not in sql_api
    assert "_SCHEMA_VERSION = 1" in cli_json
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert "sqlglot" not in _read("uv.lock").lower()
    assert len(tuple((REPO_ROOT / "tests/fixtures/golden").iterdir())) == 37


def test_runtime_has_no_security_composition_or_diagnostic_implementation_markers() -> (
    None
):
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
    ).lower()

    for marker in (
        "permission gate",
        "authorization token",
        "capability token",
        "authority token",
        "relation gateway",
        "runtime security",
        "policy isolation",
        "threat model",
        "relation composition",
        "join lowering",
        "join_one",
        "join_many",
    ):
        assert marker not in runtime_text


def test_plan_and_status_documents_link_slice5_without_implementation_claims() -> None:
    documents = {
        PLAN_PATH: _read(PLAN_PATH),
        "AGENTS.md": _read("AGENTS.md"),
        "docs/spec/pietto-v0.9.md": _read("docs/spec/pietto-v0.9.md"),
    }

    for document in documents.values():
        normalized = " ".join(document.split())
        assert CONTRACT_PATH in document
        assert "Slice 5" in normalized
        assert "Slice 6 remains planned only" in normalized
        assert "planning-only" in normalized

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
        "SQLGlot",
        "not implemented",
    ):
        assert boundary in combined

    assert "No future slice receives implementation authorization" in _read(
        CONTRACT_PATH
    )


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
