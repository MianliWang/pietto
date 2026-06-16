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
CONTRACT_PATH = "docs/spec/relationship-name-ownership-contract-v1.md"
PLAN_PATH = "docs/plan/phase-15-relationship-metadata-semantics.md"

LOCKED_GROUP_HASHES = {
    "examples": (
        10,
        "230369f90130d7c4b722b75ef2ec264d98e0d6f34ad3b1b5fd7d5fbf04d45a97",
    ),
    "fixtures": (
        32,
        "1f5845f1d08066947e5fa2a60b3ca0802cb8e74ca69f39f4fcf7b9a5f352138c",
    ),
    "goldens": (
        19,
        "539a980e24fc41be1e645b4527b3114d6046e0014f7c8d347e150bd1721ef728",
    ),
}


def test_contract_exists_with_contract_and_audit_only_status() -> None:
    contract_path = REPO_ROOT / CONTRACT_PATH
    contract = contract_path.read_text(encoding="utf-8")
    normalized = " ".join(contract.split())

    assert contract_path.is_file()
    assert "# Relationship Name Ownership And Ambiguity Contract v1" in contract
    assert (
        "**Phase 15 Slice 3: Relationship Name Ownership And Ambiguity Contract "
        "is complete as contract and audit work only.**"
    ) in normalized
    assert "changes no runtime semantic behavior" in normalized
    assert "authorizes no relation composition implementation" in normalized


def test_relationship_namespace_ownership_is_explicit() -> None:
    normalized = " ".join(_read(CONTRACT_PATH).split())

    for required in (
        "Relationship names live in a relationship metadata namespace",
        "must be unique among relationship declarations",
        "separate from the relation, type, and callable namespaces",
        "may overlap with a relation, type, or callable name",
        "Such overlap is not a current ambiguity",
        "`SemanticModel.relation_symbols`",
        "`SemanticModel.type_symbols`",
        "`SemanticModel.callable_symbols`",
    ):
        assert required in normalized


def test_endpoint_local_names_are_relationship_local_only() -> None:
    normalized = " ".join(_read(CONTRACT_PATH).split())

    for required in (
        "scoped only inside its owning relationship",
        "unique within that relationship",
        "different relationships may reuse the same endpoint local names",
        "do not enter relation, type, callable, or query field namespaces",
        "do not qualify fields",
        "do not alter current query field lookup",
    ):
        assert required in normalized


def test_from_resolution_uses_only_relation_namespace_and_existing_diagnostic() -> None:
    contract = " ".join(_read(CONTRACT_PATH).split())
    relations = _read("src/pietto/semantic/relations.py")

    assert "`from relationship_name`" in contract
    assert "resolved using only the existing relation namespace" in contract
    assert "existing `PIE-S2301` unknown relation diagnostic" in contract
    assert "Relationship metadata is never a fallback relation candidate" in contract
    assert "target = relation_symbols.get(from_clause.source_name)" in relations
    assert 'code="PIE-S2301"' in relations
    assert 'message=f"Unknown relation: {from_clause.source_name}"' in relations
    assert "relationship" not in relations.lower()


def test_semantic_relationships_remain_readonly_metadata_outside_ir() -> None:
    contract = " ".join(_read(CONTRACT_PATH).split())
    semantic_model = _read("src/pietto/semantic/model.py")
    ir_runtime = _runtime_text("src/pietto/ir")
    sql_runtime = _runtime_text("src/pietto/sql")

    assert "`SemanticModel.relationships` is immutable, read-only metadata" in contract
    assert "is not Semantic IR" in contract
    assert "class RelationshipSemanticInfo:" in semantic_model
    assert "relationships: tuple[RelationshipSemanticInfo, ...] = ()" in semantic_model
    assert "@dataclass(frozen=True, slots=True)" in semantic_model
    assert "RelationshipSemanticInfo" not in ir_runtime
    assert "RelationshipSemanticInfo" not in sql_runtime
    assert "relationship" not in ir_runtime.lower()
    assert "relationship" not in sql_runtime.lower()


def test_composition_resolution_and_future_ambiguity_remain_deferred() -> None:
    contract = " ".join(_read(CONTRACT_PATH).split())
    runtime = "\n".join(
        (
            _runtime_text("src/pietto/semantic"),
            _runtime_text("src/pietto/ir"),
            _runtime_text("src/pietto/sql"),
            _read("src/pietto/cli.py"),
            _read("src/pietto/cli_json.py"),
        )
    ).lower()

    for required in (
        "ambiguity diagnostics for actual queries are explicitly deferred",
        "defines no composition resolver",
        "endpoint-qualified field lookup",
        "multi-input query semantics",
        "JOIN behavior",
        "reserves no diagnostic code",
    ):
        assert required in contract

    for marker in (
        "composition_resolver",
        "resolve_composition",
        "relationshipir",
        "endpoint_qualified",
        "multi_input",
        "relationship lowering",
        "join lowering",
    ):
        assert marker not in runtime


def test_public_sql_mysql_json_and_dependency_boundaries_remain_unchanged() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    sql_source = _read("src/pietto/sql/__init__.py")
    mysql_source = _read("src/pietto/sql/mysql.py")
    all_block = re.search(r"(?s)__all__ = \[(?P<body>.*?)\]", sql_source)

    assert all_block is not None
    assert tuple(re.findall(r'"([^"]+)"', all_block.group("body"))) == (
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    )
    assert tuple(inspect.signature(sql_api.emit_postgres_sql).parameters) == (
        "script_ir",
    )
    assert "emit_mysql_sql" not in sql_source
    assert "def emit_mysql_sql(" in mysql_source
    assert "def emit_sql(" not in sql_source
    assert cli_json._SCHEMA_VERSION == 1
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]


def test_examples_fixtures_and_goldens_are_byte_locked() -> None:
    groups = {
        "examples": _all_files("examples"),
        "fixtures": _all_files("tests/fixtures"),
        "goldens": _all_files("tests/fixtures/golden"),
    }

    for name, paths in groups.items():
        expected_count, expected_hash = LOCKED_GROUP_HASHES[name]
        assert len(paths) == expected_count
        assert _aggregate_files(paths) == expected_hash


def test_plan_and_status_docs_record_slice3_without_runtime_authorization() -> None:
    documents = {
        PLAN_PATH: _read(PLAN_PATH),
        "README.md": _read("README.md"),
        "AGENTS.md": _read("AGENTS.md"),
        "docs/spec/pietto-v0.9.md": _read("docs/spec/pietto-v0.9.md"),
    }

    for document in documents.values():
        normalized = " ".join(document.split())
        assert CONTRACT_PATH in document
        assert "Phase 15 Slice 3" in normalized
        assert "contract" in normalized.lower()
        assert "no runtime" in normalized.lower()

    combined = " ".join("\n".join(documents.values()).split())
    for boundary in (
        "relation composition",
        "JOIN",
        "SQL lowering",
        "endpoint-qualified field lookup",
        "multi-input query semantics",
        "ambiguity diagnostics",
        "separately authorized",
    ):
        assert boundary in combined


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _runtime_text(root: str) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / root).glob("*.py"))
    )


def _all_files(root: str) -> tuple[Path, ...]:
    return tuple(
        path for path in sorted((REPO_ROOT / root).rglob("*")) if path.is_file()
    )


def _aggregate_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
