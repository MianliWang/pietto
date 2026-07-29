from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "docs/spec/composition-scope-name-resolution-contract-v1.md"
ROLE_CONTRACT_PATH = "docs/spec/relationship-relation-role-contract-v1.md"
PLAN_PATH = "docs/plan/phase-13-relation-composition-planning.md"


def test_contract_exists_with_planning_only_status() -> None:
    contract_path = REPO_ROOT / CONTRACT_PATH
    contract = contract_path.read_text(encoding="utf-8")
    normalized = " ".join(contract.split())

    assert contract_path.is_file()
    assert "# Composition Scope And Name Resolution Contract v1" in contract
    assert (
        "**Phase 13 Slice 3: Composition Scope And Name Resolution Contract is "
        "complete.**"
    ) in normalized
    assert "planning and contract work only" in normalized
    assert "defines no currently accepted Pietto syntax" in normalized
    assert "Neither contract authorizes implementation" in normalized
    assert ROLE_CONTRACT_PATH in contract


def test_contract_defines_required_planning_vocabulary() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split()).lower()

    for term in (
        "input relation scope",
        "output relation scope",
        "composition boundary",
        "relation qualifier",
        "field qualifier",
        "unqualified field reference",
        "qualified field reference",
        "ambiguous reference",
        "hidden or unavailable field",
        "projection alias boundary",
        "endpoint name",
        "relationship name",
        "relationship endpoint role",
        "relation role",
        "scope owner",
        "clause visibility",
        "output schema ownership",
    ):
        assert term in normalized

    for boundary in (
        "conceptual planning vocabulary only",
        "not pietto keywords, reserved words",
        "not accepted source syntax",
        "does not choose final syntax for qualified references",
    ):
        assert boundary in normalized


def test_input_output_scope_and_clause_visibility_preserve_current_behavior() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "Pietto currently has one input relation scope for a relation body",
        "current `ORDER BY` contract is input-scope only",
        "Projection aliases do not enter ordering scope",
        "Projection aliases should be treated as output fields only after the "
        "projection alias boundary",
        "must not be retroactively reinterpreted as projection-alias or "
        "output-schema scope",
        "must not silently shadow input fields in earlier clauses",
        "must not silently become ordering keys",
        "implementation is forbidden",
    ):
        assert required in normalized


def test_qualification_ambiguity_and_endpoint_planning_fail_closed() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "lookup of an unqualified field reference must remain deterministic",
        "fail closed with a deterministic semantic diagnostic rather than guess",
        "must not accidentally collide with field names",
        "Possible conceptual owners include a relation, endpoint, relationship, "
        "alias, or output schema owner",
        "not runtime principals, database users, or database roles",
        "must not imply database permission, authorization, or security enforcement",
    ):
        assert required in normalized


def test_contract_contains_no_examples_or_future_syntax_shapes() -> None:
    contract = _read(CONTRACT_PATH)
    lowered = contract.lower()

    assert "```" not in contract
    assert "relationship foo:" not in lowered
    assert "role admin:" not in lowered
    assert "join_one" not in lowered
    assert "join_many" not in lowered
    assert "from users" not in lowered
    assert "select:" not in lowered
    assert "order by:" not in lowered
    assert (
        re.search(
            r"(?m)^\s*(relationship|endpoint|role|authority|purpose)\s+\w+\s*:",
            lowered,
        )
        is None
    )


def test_diagnostics_use_canonical_families_without_new_codes() -> None:
    contract = _read(CONTRACT_PATH)

    for family in ("PIE-Pxxxx", "PIE-Sxxxx", "PIE-Ixxxx", "PIE-Bxxxx"):
        assert family in contract

    assert "This slice introduces no diagnostic code" in contract
    assert "source-span ownership, deterministic ordering, and cascade behavior" in (
        " ".join(contract.split())
    )
    concrete_codes = set(re.findall(r"\bPIE-[PSIB]\d{4}\b", contract))
    assert concrete_codes == {"PIE-S2102"}
    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", contract) is None


def test_scope_checks_are_not_runtime_authorization_or_security() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "compiler semantics, not authorization",
        "do not provide access control, privacy enforcement, database grants, "
        "masking, row-level security, policy isolation, or safe data sharing",
        "must not be represented as proof that a caller may access data",
        "no runtime identity, permission gate, authorization service, or "
        "database-policy enforcement",
        "separate threat model, deployment assumptions, and enforcement design",
    ):
        assert required in normalized


def test_contract_preserves_api_json_dependency_golden_and_source_boundaries() -> None:
    contract = _read(CONTRACT_PATH)
    project = tomllib.loads(_read("pyproject.toml"))
    sql_api = _read("src/pietto/sql/__init__.py")
    cli_json = _read("src/pietto/cli_json.py")

    for non_goal in (
        "parser, AST, semantic, IR, or SQL backend implementation",
        "JOIN or any relation-composition behavior",
        "database or connector connection, execution, or schema introspection",
        "CLI behavior, JSON schema, or public API changes",
        "dependencies, SQLGlot, package metadata, version, CI, or golden changes",
    ):
        assert non_goal in " ".join(contract.split())

    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert '"emit_postgres_sql"' in sql_api
    assert '"emit_mysql_sql"' not in sql_api
    assert "emit_sql" not in sql_api
    assert "_SCHEMA_VERSION = 1" in cli_json
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert "sqlglot" not in _read("uv.lock").lower()
    assert len(tuple((REPO_ROOT / "tests/fixtures/golden").iterdir())) == 37


def test_runtime_has_no_composition_scope_or_authorization_implementation() -> None:
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
    ).lower()

    for marker in (
        "composition scope",
        "relationship scope",
        "endpoint scope",
        "qualifier binding",
        "join scope",
        "permission gate",
        "authorization token",
        "capability token",
        "join_one",
        "join_many",
    ):
        assert marker not in runtime_text


def test_plan_and_status_documents_link_slice3_without_authorizing_implementation() -> (
    None
):
    documents = {
        PLAN_PATH: _read(PLAN_PATH),
        "AGENTS.md": _read("AGENTS.md"),
        "docs/spec/pietto-v0.9.md": _read("docs/spec/pietto-v0.9.md"),
    }

    for document in documents.values():
        normalized = " ".join(document.split())
        assert CONTRACT_PATH in document
        assert "Slice 3" in normalized
        assert "Slices 4 through 6" in normalized
        assert "planning-only" in normalized

    combined = " ".join("\n".join(documents.values()).split())
    for boundary in (
        "relation composition",
        "JOIN",
        "relationship syntax",
        "relation-role syntax",
        "permission gate",
        "runtime security",
        "SQL execution",
        "not implemented",
    ):
        assert boundary in combined

    assert "No future slice receives implementation authorization" in _read(
        CONTRACT_PATH
    )


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
