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
PLAN_PATH = "docs/plan/phase-15-relationship-metadata-semantics.md"
SEMANTIC_SPEC_PATH = "docs/spec/relationship-metadata-semantic-validation-v1.md"
OWNERSHIP_CONTRACT_PATH = "docs/spec/relationship-name-ownership-contract-v1.md"
SLICE1_TEST_PATH = "tests/test_phase15_relationship_metadata_semantics.py"
SLICE2_TEST_PATH = "tests/test_phase15_semantic_model_relationships.py"
SLICE3_TEST_PATH = "tests/test_phase15_relationship_name_ownership_contract.py"
PRIOR_AUDIT_PATH = "tests/test_phase15_semantic_completion_audit.py"

PHASE15_ARTIFACT_HASHES = {
    SEMANTIC_SPEC_PATH: (
        "4c7b270c20dcf944e98ccf57f49f17c9f964263f32e79941215a8f72bb0f25c2"
    ),
    OWNERSHIP_CONTRACT_PATH: (
        "55ed7f196187bbd978c9431f9077089786b4d61f595b8f56a00b979f4160719a"
    ),
    SLICE1_TEST_PATH: (
        "772e01b3ec353735b57f29c5434dac5bfc36dcb3cab41907d8541827523b298f"
    ),
    SLICE2_TEST_PATH: (
        "227e5989affa152dcbeb4f8775f0705bc8a14d9dcd269e8f4409d32e71714218"
    ),
    SLICE3_TEST_PATH: (
        "e2a4219d2e0a0b7cc2d739475e39022df931c58171a87f96436286008a4be3b3"
    ),
    PRIOR_AUDIT_PATH: (
        "ba8f3afe9d6765a56a7881f4b1a116cabb7983fd4badb2cbebec47847b7da742"
    ),
}

LOCKED_FILE_HASHES = {
    "grammar/Pietto.g4": (
        "54484b73f76ae051e0e4f27cc47bc99a0687da7c0e4f40ab4da06a640a54369a"
    ),
    "src/pietto/ast_nodes.py": (
        "0464445d598b676bfd65ebb0cc59db8cc5f51acea919704c918473bb63be7d0a"
    ),
    "src/pietto/ast_builder.py": (
        "358de38055709b343237ccdde18b3964aacba285a5f0f5d68cdc38530fb95c22"
    ),
    "src/pietto/parser_api.py": (
        "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b"
    ),
    "src/pietto/errors.py": (
        "7aa9622bde3eb07bb64bb5c932dc69e48d635e89790b26e8090b9309c5cf62f6"
    ),
    "src/pietto/cli.py": (
        "cdf08c85afbfc0d1d8bfb12bcd6332e33d2a94c6a5dc79da0e28383418bc2a2e"
    ),
    "src/pietto/cli_json.py": (
        "ccee00529ee36b123f70d418105609dbb4906f2ccc1c1f5653527b1168fb6d91"
    ),
    "src/pietto/sql/__init__.py": (
        "e40bd3eee7f76bc68313adb8237a7a6c5d84286197261f70c827a4219c9e3418"
    ),
    "pyproject.toml": (
        "bc17aff5ff3c3e4db0e954d9c42297c00256ce27d2061abe779a76fa3f4ce7ef"
    ),
    "uv.lock": "7582351d1319c6f34087178ce629bac889c2806353b30195317268bd3b23cd51",
    ".github/workflows/ci.yml": (
        "d0b8023d05232673e2e3f05b27e34e5d4a53249633f48371a17fc07fdb406605"
    ),
}

LOCKED_GROUP_HASHES = {
    "generated": (
        8,
        "7ac3aea913b1453a972456be0171a2c292991e71bde3e94a4056b4bf537b5c4e",
    ),
    "semantic": (
        21,
        "de7bc94d972739411d98458a89d293aecd5cea4326a9cf51a8b065c2cf8846cd",
    ),
    "ir": (
        5,
        "57097f43ba5e0ffa8d531b827b7029c9104b85ab3dc0657889cccd28caec5249",
    ),
    "sql": (
        10,
        "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b",
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
    PLAN_PATH,
)


def test_phase15_four_slice_sequence_and_completion_status_are_explicit() -> None:
    plan = _read(PLAN_PATH)
    normalized = " ".join(plan.split())

    for required in (
        "**Phase 15 Slice 1: Relationship Metadata Semantic Validation is complete.**",
        "**Phase 15 Slice 2: Relationship Semantic Model Storage is complete.**",
        "**Phase 15 Slice 3: Relationship Name Ownership And Ambiguity Contract "
        "is complete as contract and audit work only.**",
        "**Phase 15 Slice 4: Relationship Metadata Semantics Completion Audit is "
        "complete.**",
        "**Phase 15 Relationship Metadata Semantics is complete.**",
    ):
        assert required in normalized

    for path in (
        SEMANTIC_SPEC_PATH,
        OWNERSHIP_CONTRACT_PATH,
        SLICE1_TEST_PATH,
        SLICE2_TEST_PATH,
        SLICE3_TEST_PATH,
        PRIOR_AUDIT_PATH,
    ):
        assert path in plan
        assert (REPO_ROOT / path).is_file()


def test_slice1_and_slice2_specs_tests_and_behavior_are_byte_locked() -> None:
    spec = _read(SEMANTIC_SPEC_PATH)
    normalized_spec = " ".join(spec.split())
    slice1_tests = _read(SLICE1_TEST_PATH)
    slice2_tests = _read(SLICE2_TEST_PATH)

    for path in (
        SEMANTIC_SPEC_PATH,
        SLICE1_TEST_PATH,
        SLICE2_TEST_PATH,
        PRIOR_AUDIT_PATH,
    ):
        assert _sha256(REPO_ROOT / path) == PHASE15_ARTIFACT_HASHES[path]

    for required in (
        "Every endpoint `relation_name` must name an existing source, table, or query",
        "Every relationship declaration name must be unique",
        "endpoint `local_name` values within one relationship must be distinct",
        "`SemanticModel.relationships == ()`",
        "`RelationshipSemanticInfo`",
        "`RelationshipSemanticEndpointInfo`",
        "Invalid relationship declarations",
    ):
        assert required in normalized_spec

    assert {
        "test_valid_relationship_references_existing_relations",
        "test_unknown_endpoint_relation_reports_s2601_at_endpoint_span",
        "test_duplicate_relationship_name_reports_s2602_at_later_declaration",
        "test_duplicate_endpoint_local_name_reports_s2603_at_later_endpoint",
        "test_relationship_metadata_stays_outside_definitions_and_relation_symbols",
        "test_relationship_metadata_cannot_be_used_as_relation_input",
        "test_valid_relationship_metadata_does_not_change_semantic_ir_or_sql",
    } <= _test_names(slice1_tests)

    assert {
        "test_valid_relationship_is_stored_in_semantic_model",
        "test_relationship_and_endpoint_source_order_are_preserved",
        "test_endpoints_resolve_to_existing_source_table_and_query_symbols",
        "test_relationship_semantic_facts_are_immutable",
        "test_invalid_relationships_are_not_stored",
        "test_program_without_relationship_metadata_has_empty_semantic_tuple",
    } <= _test_names(slice2_tests)


def test_slice3_contract_and_audit_are_byte_locked() -> None:
    contract = _read(OWNERSHIP_CONTRACT_PATH)
    audit = _read(SLICE3_TEST_PATH)
    normalized = " ".join(contract.split())

    for path in (OWNERSHIP_CONTRACT_PATH, SLICE3_TEST_PATH):
        assert _sha256(REPO_ROOT / path) == PHASE15_ARTIFACT_HASHES[path]

    for required in (
        "Relationship names live in a relationship metadata namespace",
        "separate from the relation, type, and callable namespaces",
        "scoped only inside its owning relationship",
        "resolved using only the existing relation namespace",
        "Relationship metadata is never a fallback relation candidate",
        "`SemanticModel.relationships` is immutable, read-only metadata",
        "ambiguity diagnostics for actual queries are explicitly deferred",
    ):
        assert required in normalized

    assert {
        "test_relationship_namespace_ownership_is_explicit",
        "test_endpoint_local_names_are_relationship_local_only",
        "test_from_resolution_uses_only_relation_namespace_and_existing_diagnostic",
        "test_semantic_relationships_remain_readonly_metadata_outside_ir",
        "test_composition_resolution_and_future_ambiguity_remain_deferred",
    } <= _test_names(audit)


def test_phase15_uses_exactly_three_relationship_semantic_diagnostics() -> None:
    checker = _read("src/pietto/semantic/relationship_metadata.py")
    registry = _read("docs/spec/diagnostics.md")
    spec = _read(SEMANTIC_SPEC_PATH)
    implemented = set(re.findall(r'"(PIE-S26[0-9]{2})"', checker))
    documented = set(re.findall(r"`(PIE-S26[0-9]{2})`", registry))
    specified = set(re.findall(r"`(PIE-S26[0-9]{2})`", spec))

    assert (
        implemented
        == documented
        == specified
        == {
            "PIE-S2601",
            "PIE-S2602",
            "PIE-S2603",
        }
    )
    assert "No additional diagnostic code is reserved by this slice" in spec
    ownership_contract = " ".join(_read(OWNERSHIP_CONTRACT_PATH).split())
    assert "reserves no diagnostic code" in ownership_contract


def test_relationship_metadata_ownership_and_from_boundaries_remain_exact() -> None:
    ast_nodes = _read("src/pietto/ast_nodes.py")
    analyzer = _read("src/pietto/semantic/analyzer.py")
    model = _read("src/pietto/semantic/model.py")
    relations = _read("src/pietto/semantic/relations.py")
    checker = _read("src/pietto/semantic/relationship_metadata.py")

    assert "definitions: tuple[Definition, ...]" in ast_nodes
    assert "relationships: tuple[RelationshipMetadata, ...] = ()" in ast_nodes
    assert "relationships=relationships" in analyzer
    assert "relationship_names: set[str] = set()" in checker
    assert "relation_symbols: Mapping[str, Definition]" in checker
    assert "relationships: tuple[RelationshipSemanticInfo, ...] = ()" in model
    assert "class RelationshipSemanticInfo:" in model
    assert "class RelationshipSemanticEndpointInfo:" in model
    assert model.count("@dataclass(frozen=True, slots=True)") >= 2
    assert "target = relation_symbols.get(from_clause.source_name)" in relations
    assert 'code="PIE-S2301"' in relations
    assert "relationship" not in relations.lower()


def test_frontend_compiler_cli_and_repository_surfaces_are_byte_locked() -> None:
    for path, expected_hash in LOCKED_FILE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    groups = {
        "generated": tuple(
            path
            for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
            if path.is_file()
        ),
        "semantic": _python_files("src/pietto/semantic"),
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


def test_semantic_relationship_facts_never_enter_ir_or_sql() -> None:
    ir = _runtime_text("src/pietto/ir")
    sql = _runtime_text("src/pietto/sql")

    for marker in (
        "RelationshipSemanticInfo",
        "RelationshipSemanticEndpointInfo",
        "RelationshipMetadata",
        "RelationshipIR",
    ):
        assert marker not in ir
        assert marker not in sql
    assert "relationship" not in ir.lower()
    assert "relationship" not in sql.lower()
    assert '"JOIN "' not in sql


def test_public_sql_mysql_json_dependency_and_ci_boundaries_are_locked() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    sql_source = _read("src/pietto/sql/__init__.py")
    mysql_source = _read("src/pietto/sql/mysql.py")
    workflow = _read(".github/workflows/ci.yml")
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
    assert "sqlglot" not in _read("uv.lock").lower()
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)


def test_deferred_capabilities_remain_absent_and_unauthorized() -> None:
    runtime = "\n".join(
        (
            _runtime_text("src/pietto/semantic"),
            _runtime_text("src/pietto/ir"),
            _runtime_text("src/pietto/sql"),
            _read("src/pietto/parser_api.py"),
            _read("src/pietto/cli.py"),
            _read("src/pietto/cli_json.py"),
        )
    ).lower()

    for marker in (
        "composition_resolver",
        "resolve_composition",
        "relationshipir",
        "endpoint_qualified",
        "multi_input",
        "join lowering",
        "relationship lowering",
        "actual-query ambiguity",
        "permission gate",
        "runtime authorization",
        "runtime security",
        "database connection",
        "schema introspection",
        "execute sql",
        "sqlglot",
        "compile_to_sql",
    ):
        assert marker not in runtime

    assert "pietto._project.json_v2" in runtime
    assert "project_check_result_to_json_dict" in runtime
    for marker in (
        "schema_version = 2",
        '"schema_version": 2',
        "compile_project",
        "load_project_config",
        "project_loader",
    ):
        assert marker not in runtime

    combined = " ".join("\n".join(_read(path) for path in STATUS_PATHS).split())
    for boundary in (
        "JOIN",
        "relation composition",
        "SQL lowering",
        "endpoint-qualified field lookup",
        "multi-input query semantics",
        "ambiguity diagnostics",
        "runtime security",
        "database behavior",
        "JSON version 2",
        "public MySQL",
        "generic SQL emitter",
        "release",
        "publication",
    ):
        assert boundary in combined


def test_status_docs_record_phase15_completion_without_expanding_scope() -> None:
    for path in STATUS_PATHS:
        normalized = " ".join(_read(path).split())
        assert "Phase 15" in normalized
        assert "complete" in normalized
        assert "Slice 4" in normalized
        assert "completion audit" in normalized.lower()
        assert "semantic-only" in normalized.lower()
        assert "no runtime" in normalized.lower()


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _test_names(source: str) -> set[str]:
    return set(re.findall(r"^def (test_[a-z0-9_]+)", source, re.MULTILINE))


def _python_files(root: str) -> tuple[Path, ...]:
    return tuple(sorted((REPO_ROOT / root).glob("*.py")))


def _all_files(root: str) -> tuple[Path, ...]:
    return tuple(
        path for path in sorted((REPO_ROOT / root).rglob("*")) if path.is_file()
    )


def _runtime_text(root: str) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in _python_files(root))


def _aggregate_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
