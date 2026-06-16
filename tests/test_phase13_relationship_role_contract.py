from __future__ import annotations

import inspect
import re
import tomllib
from pathlib import Path

import pietto.cli_json as cli_json
import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "docs/spec/relationship-relation-role-contract-v1.md"
PLAN_PATH = "docs/plan/phase-13-relation-composition-planning.md"


def test_contract_exists_with_planning_only_status() -> None:
    contract_path = REPO_ROOT / CONTRACT_PATH
    contract = contract_path.read_text(encoding="utf-8")
    normalized = " ".join(contract.split())

    assert contract_path.is_file()
    assert "# Relationship And Relation Role Contract v1" in contract
    assert (
        "**Phase 13 Slice 2: Relationship / Relation Role Contract is complete.**"
        in contract
    )
    assert "planning and contract work only" in normalized
    assert "defines no currently accepted Pietto syntax" in normalized
    assert "adds no grammar, parser, AST, semantic, IR, SQL backend" in normalized


def test_contract_defines_required_conceptual_vocabulary() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split()).lower()

    for concept in (
        "relationship declaration",
        "relationship endpoint",
        "endpoint role",
        "relation role",
        "authority",
        "purpose",
        "query context",
        "relation-as-gateway",
        "relation-as-checkpoint",
        "cardinality",
        "fanout",
        "semantic authorization",
        "runtime authorization",
        "sql-lowerable invariant",
        "fail closed",
    ):
        assert concept in normalized

    assert (
        "endpoint role and relation role are distinct planning concepts" in normalized
    )
    assert "neither concept is implemented" in normalized
    assert "not accepted source syntax" in normalized
    assert "not a pietto keyword, reserved word, declaration form" in normalized


def test_contract_draws_conservative_security_boundary() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split()).lower()

    for required in (
        "compiler semantic checks are not database enforcement",
        "this model is not user authorization",
        "future compiler planning only",
        "not runtime security",
        "does not prevent direct database access outside pietto",
        "does not currently provide access control",
        "pietto currently enforces none of the runtime or database concerns",
        "any future safety claim requires its own threat model",
    ):
        assert required in normalized

    for current_claim in (
        "pietto enforces access control",
        "pietto enforces privacy",
        "pietto provides runtime authorization",
        "pietto provides safe data sharing",
    ):
        assert current_claim not in normalized


def test_contract_uses_only_canonical_diagnostic_families() -> None:
    contract = _read(CONTRACT_PATH)

    for family in ("PIE-Pxxxx", "PIE-Sxxxx", "PIE-Ixxxx", "PIE-Bxxxx"):
        assert family in contract

    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", contract) is None


def test_contract_contains_no_future_syntax_shaped_examples() -> None:
    contract = _read(CONTRACT_PATH)
    lowered = contract.lower()

    assert "```" not in lowered
    assert "relationship foo:" not in lowered
    assert "relationship user" not in lowered
    assert "role admin" not in lowered
    assert "join_one" not in lowered
    assert "join_many" not in lowered
    assert "capability token" not in lowered
    assert "authority token" not in lowered
    assert (
        re.search(r"(?m)^\s*(relationship|role|authority|purpose)\s+\w+\s*:", lowered)
        is None
    )


def test_status_documents_link_contract_without_claiming_implementation() -> None:
    documents = {
        "README.md": _read("README.md"),
        "AGENTS.md": _read("AGENTS.md"),
        "docs/spec/pietto-v0.9.md": _read("docs/spec/pietto-v0.9.md"),
    }

    for document in documents.values():
        normalized = " ".join(document.split())
        assert CONTRACT_PATH in document
        assert "Slice 2" in normalized
        assert "complete" in normalized
        assert "Slices 3 through 6" in normalized

    combined = " ".join("\n".join(documents.values()).split())
    for boundary in (
        "relationship declarations",
        "relation roles",
        "permission gates",
        "runtime security",
        "JOIN",
        "SQL execution",
        "not implemented",
    ):
        assert boundary in combined


def test_master_plan_records_slice2_completion_and_remaining_status() -> None:
    plan = _read(PLAN_PATH)
    normalized = " ".join(plan.split())

    assert "**Slice 1: Master Plan And Baseline Audit is complete.**" in plan
    assert "**Slice 2: Relationship / Relation Role Contract is complete.**" in plan
    assert "Slices 3 through 6 are planned only" in normalized
    assert CONTRACT_PATH in plan
    assert "defines no currently accepted Pietto syntax" in normalized


def test_runtime_has_no_relationship_or_authorization_implementation() -> None:
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
    ).lower()

    for marker in (
        "relationship gate",
        "relation gate",
        "capability token",
        "authority token",
        "join_one",
        "join_many",
        "relation-as-gateway",
        "semantic authorization",
    ):
        assert marker not in runtime_text


def test_public_api_json_dependencies_and_goldens_remain_unchanged() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
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
    assert cli_json._SCHEMA_VERSION == 1
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert "sqlglot" not in _read("uv.lock").lower()
    assert (
        len(
            tuple(
                path
                for path in (REPO_ROOT / "tests/fixtures/golden").iterdir()
                if path.is_file()
            )
        )
        == 21
    )


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
