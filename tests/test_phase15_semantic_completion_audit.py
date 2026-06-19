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
SPEC_PATH = "docs/spec/relationship-metadata-semantic-validation-v1.md"
PLAN_PATH = "docs/plan/phase-15-relationship-metadata-semantics.md"
SEMANTIC_TEST_PATH = "tests/test_phase15_relationship_metadata_semantics.py"
MODEL_TEST_PATH = "tests/test_phase15_semantic_model_relationships.py"
OWNERSHIP_CONTRACT_PATH = "docs/spec/relationship-name-ownership-contract-v1.md"
OWNERSHIP_TEST_PATH = "tests/test_phase15_relationship_name_ownership_contract.py"
RELATIONSHIP_MODULE = "src/pietto/semantic/relationship_metadata.py"

LOCKED_FILE_HASHES = {
    "grammar/Pietto.g4": (
        "d75052cfc4c5de426388cc9d8a34eef607e8023a5e1789f2e497979ea2dde9f6"
    ),
    "src/pietto/ast_nodes.py": (
        "2ea40611346889186ed87c4235e6987fa41e9e4832fdceb58748eee2720fb058"
    ),
    "src/pietto/ast_builder.py": (
        "e28f084e3b7862c3e47a0f9478cc92539f4f1e113438060f0d0c4927b928ccae"
    ),
    "src/pietto/parser_api.py": (
        "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b"
    ),
    "src/pietto/errors.py": (
        "7aa9622bde3eb07bb64bb5c932dc69e48d635e89790b26e8090b9309c5cf62f6"
    ),
    "src/pietto/cli.py": (
        "94f826375f3208f0e98aa374baf54efec2b555327589aefb748c28ec5ad1ae3f"
    ),
    "src/pietto/cli_json.py": (
        "ccee00529ee36b123f70d418105609dbb4906f2ccc1c1f5653527b1168fb6d91"
    ),
    "src/pietto/sql/__init__.py": (
        "e40bd3eee7f76bc68313adb8237a7a6c5d84286197261f70c827a4219c9e3418"
    ),
    "pyproject.toml": (
        "021682ef880fe748f1655d4d70fcc549db4336ac39db2b29a835762ab1723d50"
    ),
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
    ".github/workflows/ci.yml": (
        "c2ba73d04dab3331ca19577f2cf4250274671aa37ec4f84f293429e118b6c4c5"
    ),
}

LOCKED_GROUP_HASHES = {
    "generated": (
        8,
        "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1",
    ),
    "unchanged_semantic": (
        17,
        "fb41cc6953f9744c52f0d37bed1b738c105c08324824cbe0e6079d7ec1919efe",
    ),
    "ir": (
        5,
        "8c2c3648740d898137c402c20596db28d3ac13734cdbdb6ddd6ce82c5b3577cd",
    ),
    "sql": (
        10,
        "112bb96372e442aba03ff953b45a5c5850a946e29d0f6358c3cffa281bf29b92",
    ),
    "examples": (
        10,
        "230369f90130d7c4b722b75ef2ec264d98e0d6f34ad3b1b5fd7d5fbf04d45a97",
    ),
    "fixtures": (
        68,
        "dbd457dd7e79f41d0e1740187818478941861cabf9ae9f3b06f908bdc81cd11c",
    ),
    "goldens": (
        37,
        "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004",
    ),
}

STATUS_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/relationship-endpoint-metadata-syntax-v1.md",
)


def test_phase15_slice1_status_and_semantic_contract_are_explicit() -> None:
    spec = _read(SPEC_PATH)
    plan = _read(PLAN_PATH)
    normalized = " ".join(f"{spec}\n{plan}".split())

    assert "# Relationship Metadata Semantic Validation Version 1" in spec
    assert (
        "**Phase 15 Slice 1: Relationship Metadata Semantic Validation is complete.**"
        in plan
    )
    assert (
        "**Phase 15 Slice 2: Relationship Semantic Model Storage is complete.**" in plan
    )
    assert (
        "**Phase 15 Slice 3: Relationship Name Ownership And Ambiguity Contract "
        "is complete as contract and audit work only.**"
    ) in normalized
    for required in (
        "semantic-validation-only",
        "Every endpoint `relation_name` must name an existing source, table, or query",
        "relationship declaration name must be unique",
        "endpoint `local_name` values within one relationship must be distinct",
        "self-relationship",
        "not added to the type, callable, or relation namespace",
        "Semantic IR | Unchanged",
        "PostgreSQL and MySQL SQL | Unchanged",
        "JSON version 1",
        "No additional diagnostic code is reserved",
        "`SemanticModel.relationships`",
        "`RelationshipSemanticInfo`",
        "`RelationshipSemanticEndpointInfo`",
        "resolved existing source, table, or query definition",
        OWNERSHIP_CONTRACT_PATH,
    ):
        assert required in normalized


def test_phase15_slice3_contract_and_audit_completion_are_recorded() -> None:
    contract = _read(OWNERSHIP_CONTRACT_PATH)
    normalized = " ".join(contract.split())
    audit = _read(OWNERSHIP_TEST_PATH)

    assert "# Relationship Name Ownership And Ambiguity Contract v1" in contract
    assert "Relationship names live in a relationship metadata namespace" in normalized
    assert "scoped only inside its owning relationship" in normalized
    assert (
        "ambiguity diagnostics for actual queries are explicitly deferred" in normalized
    )
    assert "changes no runtime semantic behavior" in normalized
    assert (
        "test_relationship_namespace_ownership_is_explicit" in audit
        and "test_endpoint_local_names_are_relationship_local_only" in audit
    )
    assert "test_composition_resolution_and_future_ambiguity_remain_deferred" in audit


def test_relationship_checker_uses_only_three_canonical_semantic_diagnostics() -> None:
    source = _read(RELATIONSHIP_MODULE)
    registry = _read("docs/spec/diagnostics.md")
    implemented = set(re.findall(r'"(PIE-S[0-9]{4})"', source))
    documented = set(re.findall(r"`(PIE-S26[0-9]{2})`", registry))

    assert implemented == documented == {"PIE-S2601", "PIE-S2602", "PIE-S2603"}
    assert "Unknown relationship endpoint relation" in source
    assert "Duplicate relationship metadata name" in source
    assert "Duplicate endpoint local name in relationship" in source
    assert "Severity.ERROR" in source
    assert "SourceLocation(" in source


def test_semantic_integration_stores_only_readonly_validated_facts() -> None:
    analyzer = _read("src/pietto/semantic/analyzer.py")
    module = _read(RELATIONSHIP_MODULE)
    semantic_api = _read("src/pietto/semantic/__init__.py")
    semantic_model = _read("src/pietto/semantic/model.py")

    assert (
        "from pietto.semantic.relationship_metadata import check_relationship_metadata"
    ) in analyzer
    assert (
        "relationships, relationship_diagnostics = check_relationship_metadata("
        in analyzer
    )
    assert "relationships=relationships" in analyzer
    assert "def check_relationship_metadata(" in module
    assert "relation_symbols: Mapping[str, Definition]" in module
    assert "check_relationship_metadata" not in semantic_api
    assert "class RelationshipSemanticEndpointInfo:" in semantic_model
    assert "class RelationshipSemanticInfo:" in semantic_model
    assert "relationships: tuple[RelationshipSemanticInfo, ...] = ()" in semantic_model
    assert "@dataclass(frozen=True, slots=True)" in semantic_model


def test_frontend_ir_sql_cli_json_dependency_and_ci_boundaries_are_locked() -> None:
    for path, expected_hash in LOCKED_FILE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    groups = {
        "generated": tuple(
            path
            for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
            if path.is_file()
        ),
        "unchanged_semantic": tuple(
            path
            for path in _all_files("src/pietto/semantic")
            if path.suffix == ".py"
            and path.relative_to(REPO_ROOT).as_posix()
            not in {
                "src/pietto/semantic/analyzer.py",
                "src/pietto/semantic/model.py",
                RELATIONSHIP_MODULE,
            }
        ),
        "ir": _python_files("src/pietto/ir"),
        "sql": _python_files("src/pietto/sql"),
        "examples": _all_files("examples"),
        "fixtures": _all_files("tests/fixtures"),
        "goldens": _all_files("tests/fixtures/golden"),
    }
    for name, paths in groups.items():
        expected_count, expected_hash = LOCKED_GROUP_HASHES[name]
        assert len(paths) == expected_count
        assert _aggregate_files(paths) == expected_hash

    project = tomllib.loads(_read("pyproject.toml"))
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert project["project"]["scripts"] == {"pietto": "pietto.cli:main"}
    assert cli_json._SCHEMA_VERSION == 1


def test_public_sql_api_remains_postgres_only_and_mysql_private() -> None:
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


def test_phase15_behavioral_coverage_and_phase14_fixture_repair_are_locked() -> None:
    tests = _read(SEMANTIC_TEST_PATH)
    model_tests = _read(MODEL_TEST_PATH)
    phase14_test = _read("tests/test_phase14_relationship_metadata_parser.py")
    test_names = set(re.findall(r"^def (test_[a-z0-9_]+)", tests, re.MULTILINE))
    model_test_names = set(
        re.findall(r"^def (test_[a-z0-9_]+)", model_tests, re.MULTILINE)
    )

    assert {
        "test_valid_relationship_references_existing_relations",
        "test_unknown_endpoint_relation_reports_s2601_at_endpoint_span",
        "test_duplicate_relationship_name_reports_s2602_at_later_declaration",
        "test_duplicate_endpoint_local_name_reports_s2603_at_later_endpoint",
        "test_self_relationship_is_allowed_with_distinct_local_names",
        "test_relationship_and_endpoint_names_do_not_share_existing_namespaces",
        "test_relationship_metadata_stays_outside_definitions_and_relation_symbols",
        "test_relationship_metadata_cannot_be_used_as_relation_input",
        "test_valid_relationship_metadata_does_not_change_semantic_ir_or_sql",
        "test_program_without_relationship_metadata_keeps_semantic_behavior",
        "test_multiple_valid_relationships_may_reference_the_same_relations",
    } <= test_names
    assert {
        "test_valid_relationship_is_stored_in_semantic_model",
        "test_relationship_and_endpoint_source_order_are_preserved",
        "test_endpoints_resolve_to_existing_source_table_and_query_symbols",
        "test_self_relationship_resolves_both_endpoints_to_same_relation",
        "test_multiple_relationships_may_share_resolved_relations",
        "test_relationship_semantic_facts_are_immutable",
        "test_invalid_relationships_are_not_stored",
        "test_program_without_relationship_metadata_has_empty_semantic_tuple",
    } <= model_test_names

    compatibility_test = phase14_test[
        phase14_test.index(
            "def test_relationship_metadata_does_not_change_semantic_ir_or_sql"
        ) :
    ]
    assert "endpoint group: users" in compatibility_test
    assert (
        "Phase 15 Slice 2 replaces baseline_semantic == metadata_semantic"
        in compatibility_test
    )
    assert (
        "baseline_semantic.diagnostics == metadata_semantic.diagnostics == ()"
        in compatibility_test
    )
    assert "baseline_semantic.model.type_symbols" in compatibility_test
    assert "baseline_semantic.model.callable_symbols" in compatibility_test
    assert "baseline_semantic.model.relation_symbols" in compatibility_test
    assert "baseline_ir == metadata_ir" in compatibility_test
    assert "emit_postgres_sql(baseline_ir.ir)" in compatibility_test
    assert "emit_mysql_sql(baseline_ir.ir)" in compatibility_test


def test_status_docs_record_current_slice_and_preserve_phase14_history() -> None:
    for path in STATUS_PATHS:
        normalized = " ".join(_read(path).split())
        assert "Phase 14" in normalized
        assert "Phase 15 has not started and remains unauthorized" in normalized
        assert "Phase 15 Slice 1" in normalized
        assert "semantic validation" in normalized.lower()
        assert "Semantic IR" in normalized
        assert "runtime" in normalized.lower()
        assert "database" in normalized.lower()


def test_forbidden_capabilities_remain_absent_from_runtime() -> None:
    runtime = "\n".join(
        _read(path)
        for path in (
            *_python_paths("src/pietto/semantic"),
            *_python_paths("src/pietto/ir"),
            *_python_paths("src/pietto/sql"),
            "src/pietto/parser_api.py",
            "src/pietto/cli.py",
            "src/pietto/cli_json.py",
        )
    ).lower()

    for marker in (
        "join lowering",
        "composition lowering",
        "relation-role semantics",
        "permission gate",
        "runtime authorization",
        "runtime security",
        "threat model",
        "database connection",
        "schema introspection",
        "execute sql",
        "json v2",
        "sqlglot",
        "compile_to_sql",
    ):
        assert marker not in runtime


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _python_paths(root: str) -> tuple[str, ...]:
    return tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted((REPO_ROOT / root).glob("*.py"))
    )


def _python_files(root: str) -> tuple[Path, ...]:
    return tuple(sorted((REPO_ROOT / root).glob("*.py")))


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
