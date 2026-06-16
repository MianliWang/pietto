from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "docs/spec/composition-sql-shape-contract-v1.md"
ROLE_CONTRACT_PATH = "docs/spec/relationship-relation-role-contract-v1.md"
SCOPE_CONTRACT_PATH = "docs/spec/composition-scope-name-resolution-contract-v1.md"
PLAN_PATH = "docs/plan/phase-13-relation-composition-planning.md"


def test_contract_exists_with_planning_only_status() -> None:
    contract_path = REPO_ROOT / CONTRACT_PATH
    contract = contract_path.read_text(encoding="utf-8")
    normalized = " ".join(contract.split())

    assert contract_path.is_file()
    assert "# Composition SQL Shape Contract v1" in contract
    assert (
        "**Phase 13 Slice 4: Join / Composition SQL Shape Contract is complete.**"
        in contract
    )
    assert "planning and contract work only" in normalized
    assert "defines no currently accepted Pietto syntax" in normalized
    assert "does not authorize implementation" in normalized
    assert ROLE_CONTRACT_PATH in contract
    assert SCOPE_CONTRACT_PATH in contract


def test_contract_defines_required_sql_shape_planning_vocabulary() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split()).lower()

    for term in (
        "composition sql shape",
        "composition input",
        "join-like lowering",
        "join predicate",
        "join kind",
        "join side",
        "cardinality-preserving shape",
        "fanout-producing shape",
        "qualification preservation",
        "selected-dialect lowering",
        "backend capability boundary",
        "fail-closed lowering",
        "deterministic artifact shape",
        "semantic-to-backend handoff",
    ):
        assert term in normalized

    for shape_family in (
        "direct selected-dialect join-like shape",
        "cte-backed shape",
        "nested relation expansion shape",
        "backend-rejected unsupported shape",
        "explicitly forbidden hidden runtime fallback",
    ):
        assert shape_family in normalized

    assert "does not select one as the implementation strategy" in normalized


def test_dialect_parity_and_fail_closed_backend_boundary_are_explicit() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "PostgreSQL and MySQL supported semantics must remain aligned",
        "fail closed for that dialect",
        "must not silently omit a predicate",
        "No backend may infer support",
        "selected backend cannot lower it faithfully",
        "`PIE-Bxxxx` backend family",
    ):
        assert required in normalized


def test_qualification_cardinality_and_fanout_are_preserved() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "preserve the semantic name-resolution and ownership decisions",
        "must not re-resolve ambiguous names",
        "chooses no final alias syntax",
        "Fanout can change row counts",
        "ordering meaning, limit meaning, aggregate meaning",
        "whether cardinality metadata is asserted, proven, trusted under explicit "
        "assumptions, or rejected",
        "adds no runtime cardinality validation",
    ):
        assert required in normalized


def test_order_by_and_limit_baselines_remain_unchanged() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "Current `ORDER BY` remains input-scope",
        "Projection aliases do not enter its scope",
        "Current static `LIMIT` remains unchanged",
        "Expression-valued limits",
        "whether ordering is evaluated before or after the composition boundary",
        "No such decision changes current ordering or limit behavior",
    ):
        assert required in normalized


def test_contract_contains_no_examples_or_future_syntax_shapes() -> None:
    contract = _read(CONTRACT_PATH)
    lowered = contract.lower()

    assert "```" not in contract
    assert "join_one" not in lowered
    assert "join_many" not in lowered
    assert "join users" not in lowered
    assert "from users join" not in lowered
    assert "with joined as" not in lowered
    assert "select users.id from" not in lowered
    assert "relationship foo:" not in lowered
    assert "role admin:" not in lowered
    assert "select:" not in lowered
    assert "order by:" not in lowered
    assert (
        re.search(
            r"(?m)^\s*(relationship|role|source|query|table|shape)\s+\w+\s*:",
            lowered,
        )
        is None
    )


def test_diagnostics_use_only_canonical_families_without_new_codes() -> None:
    contract = _read(CONTRACT_PATH)

    for family in ("PIE-Pxxxx", "PIE-Sxxxx", "PIE-Ixxxx", "PIE-Bxxxx"):
        assert family in contract

    assert "This slice introduces no diagnostic code" in contract
    assert "source-span ownership, deterministic ordering, and cascade behavior" in (
        " ".join(contract.split())
    )
    assert re.search(r"\bPIE-[PSIB]\d{4}\b", contract) is None
    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", contract) is None


def test_security_and_runtime_fallback_boundaries_are_explicit() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "not authorization",
        "provides no access control, privacy enforcement, database grants, "
        "row-level security, masking, policy isolation, or safe data sharing",
        "must not be represented as proof that a caller may access data",
        "No in-memory JOIN fallback",
        "connector execution",
        "hidden runtime post-processing",
        "implicit authorization service",
        "database introspection",
        "Unsupported, ambiguous, or unsafe lowering must fail closed",
    ):
        assert required in normalized


def test_api_json_dependency_golden_and_source_boundaries_are_unchanged() -> None:
    contract = _read(CONTRACT_PATH)
    project = tomllib.loads(_read("pyproject.toml"))
    sql_api = _read("src/pietto/sql/__init__.py")
    cli_json = _read("src/pietto/cli_json.py")

    for non_goal in (
        "parser, AST, semantic, IR, or SQL backend implementation",
        "JOIN, relation composition, CTE, subquery, or nested expansion behavior",
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
    assert len(tuple((REPO_ROOT / "tests/fixtures/golden").iterdir())) == 21


def test_runtime_has_no_composition_sql_shape_implementation_markers() -> None:
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
    ).lower()

    for marker in (
        "join lowering",
        "composition lowering",
        "cte lowering",
        "relation composition",
        "cardinality enforcement",
        "permission gate",
        "authorization token",
        "capability token",
        "join_one",
        "join_many",
    ):
        assert marker not in runtime_text


def test_plan_and_status_documents_link_slice4_without_implementation_claims() -> None:
    documents = {
        PLAN_PATH: _read(PLAN_PATH),
        "README.md": _read("README.md"),
        "AGENTS.md": _read("AGENTS.md"),
        "docs/spec/pietto-v0.9.md": _read("docs/spec/pietto-v0.9.md"),
    }

    for document in documents.values():
        normalized = " ".join(document.split())
        assert CONTRACT_PATH in document
        assert "Slice 4" in normalized
        assert "Slices 5 through 6" in normalized
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
