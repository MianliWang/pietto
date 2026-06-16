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
CONTRACT_PATH = "docs/spec/relationship-endpoint-metadata-syntax-v1.md"
DECISION_PATH = "docs/plan/phase-14-first-implementation-candidate-decision.md"
READINESS_PATH = "docs/plan/phase-14-relation-composition-implementation-readiness.md"
SLICE3_AUDIT_PATH = "tests/test_phase14_relationship_metadata_completion_audit.py"
PARSER_TEST_PATH = "tests/test_phase14_relationship_metadata_parser.py"

STATUS_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    READINESS_PATH,
    DECISION_PATH,
    CONTRACT_PATH,
)

LOCKED_FILE_HASHES = {
    "grammar/Pietto.g4": (
        "aa9b7fe9e35ff64269fa64e8db9555897f6c16f70f293b6cb4a071a1ef25e7c1"
    ),
    "src/pietto/ast_nodes.py": (
        "1a08986999697940b6c4f778508b83c9c123dcb7de62f9de26511e2a4d36bc94"
    ),
    "src/pietto/ast_builder.py": (
        "cb01ad879fb95833bf250e8502ca22757ffdbd1c6a9ebb3632d0ea100fe21cdc"
    ),
    PARSER_TEST_PATH: (
        "805550f071d971fb6b37fb0f1ab8280c185d888f2f1a15eb806173022477840c"
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
        "655bfa5fd1bbc263f24f188a3526ab18657a1e1ab24c4ee18804416613166913",
    ),
    "semantic": (
        19,
        "3c1bb49ad1b22d05747a8246c882982318048e3e0a195e6bcfe9da09847b231c",
    ),
    "ir": (
        5,
        "1a00971a164e25214814c865154423c0b6e0ec7d02d651b2afdd32d091a5a92a",
    ),
    "sql": (
        10,
        "03cc50bf10a49b7a1d617b57d056f839e98046f09726eb717da9e004c900bdb0",
    ),
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


def test_phase14_four_slice_sequence_and_completion_status_are_explicit() -> None:
    readiness = _read(READINESS_PATH)
    normalized = " ".join(readiness.split())

    slices = (
        "1. **Final Transition Readiness Gate**",
        "2. **First Implementation Candidate Decision**",
        "3. **Explicitly Authorized Minimal Vertical Slice**",
        "4. **Backend Compatibility And Completion Audit**",
    )
    positions = tuple(readiness.index(slice_name) for slice_name in slices)
    assert positions == tuple(sorted(positions))
    assert all(f"{slice_name}: complete" in readiness for slice_name in slices)

    for required in (
        "Phase 14 is complete",
        "readiness planning",
        "candidate decision",
        "parse-only and AST-only relationship metadata",
        "backend compatibility and completion audit",
        "Slice 4 adds only static audit and status documentation",
        "Phase 15 has not started and remains unauthorized",
    ):
        assert required in normalized


def test_contract_grammar_ast_and_generated_surface_are_exact() -> None:
    contract = _read(CONTRACT_PATH)
    normalized_contract = " ".join(contract.split())
    grammar = _read("grammar/Pietto.g4")
    ast_nodes = _read("src/pietto/ast_nodes.py")
    ast_builder = _read("src/pietto/ast_builder.py")

    assert "# Relationship Endpoint Metadata Syntax Version 1" in contract
    assert "parse-only and AST-only language surface" in normalized_contract
    assert (
        "Relationship metadata is intentionally not part of `Script.definitions`"
        in (contract)
    )

    for rule in (
        "relationshipDefinition",
        "relationshipBody",
        "relationshipEndpoint",
        "RELATIONSHIP: 'relationship';",
        "ENDPOINT: 'endpoint';",
    ):
        assert rule in grammar
    assert (
        ": NEWLINE* relationshipEndpoint NEWLINE* relationshipEndpoint NEWLINE*"
        in grammar
    )
    assert "((definition | relationshipDefinition) NEWLINE*)*" in grammar

    for forbidden in (
        "join",
        "relation composition",
        "sql shape",
        "relationrole",
        "endpointrole",
        "cardinality",
        "fanout",
        "permission gate",
        "runtime security",
        "database connection",
        "schema introspection",
        "execute sql",
    ):
        assert forbidden not in grammar.lower()

    assert "class RelationshipEndpoint(Node):" in ast_nodes
    assert "class RelationshipMetadata(Node):" in ast_nodes
    assert "endpoints: tuple[RelationshipEndpoint, RelationshipEndpoint]" in ast_nodes
    assert "relationships: tuple[RelationshipMetadata, ...] = ()" in ast_nodes
    assert "definitions = tuple(self.visit(item) for item in ctx.definition())" in (
        ast_builder
    )
    assert "relationships=relationships" in ast_builder

    for path in (
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
    ):
        assert _sha256(REPO_ROOT / path) == LOCKED_FILE_HASHES[path]

    generated_paths = _generated_paths()
    expected_count, expected_hash = LOCKED_GROUP_HASHES["generated"]
    assert len(generated_paths) == expected_count
    assert _aggregate_files(generated_paths) == expected_hash


def test_parser_coverage_and_slice3_audit_remain_present_and_byte_locked() -> None:
    parser_test = _read(PARSER_TEST_PATH)
    test_names = set(re.findall(r"^def (test_[a-z0-9_]+)", parser_test, re.MULTILINE))

    assert {
        "test_minimal_relationship_metadata_preserves_names_order_and_spans",
        "test_multiple_relationship_declarations_preserve_source_order",
        "test_relationship_and_endpoint_are_contextual_identifiers",
        "test_script_without_relationship_metadata_keeps_empty_collection",
        "test_malformed_relationship_metadata_uses_existing_parser_failure",
        "test_relationship_metadata_is_immutable",
        "test_relationship_metadata_does_not_change_semantic_ir_or_sql",
    } <= test_names
    for required in (
        "len(result.ast.relationships) == 1",
        "relationship one:",
        "relationship three:",
        "Span(",
        "result.ast.relationships == ()",
        "baseline_parse.ast.definitions == metadata_parse.ast.definitions",
        "baseline_semantic == metadata_semantic",
        "baseline_ir == metadata_ir",
        "emit_postgres_sql(baseline_ir.ir) == emit_postgres_sql(metadata_ir.ir)",
        "emit_mysql_sql(baseline_ir.ir) == emit_mysql_sql(metadata_ir.ir)",
    ):
        assert required in parser_test

    assert (REPO_ROOT / SLICE3_AUDIT_PATH).is_file()
    assert "test_forbidden_compiler_layers_and_repository_surfaces_are_byte_locked" in (
        _read(SLICE3_AUDIT_PATH)
    )
    assert _sha256(REPO_ROOT / PARSER_TEST_PATH) == LOCKED_FILE_HASHES[PARSER_TEST_PATH]


def test_unchanged_compiler_repository_and_golden_surfaces_are_byte_locked() -> None:
    for path, expected_hash in LOCKED_FILE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    groups = {
        "generated": _generated_paths(),
        "semantic": _python_paths("src/pietto/semantic"),
        "ir": _python_paths("src/pietto/ir"),
        "sql": _python_paths("src/pietto/sql"),
        "examples": _all_files("examples"),
        "fixtures": _all_files("tests/fixtures"),
        "goldens": _all_files("tests/fixtures/golden"),
    }
    for name, paths in groups.items():
        expected_count, expected_hash = LOCKED_GROUP_HASHES[name]
        assert len(paths) == expected_count
        assert _aggregate_files(paths) == expected_hash


def test_json_api_dependency_version_suffix_and_diagnostic_boundaries_hold() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    lockfile = _read("uv.lock")
    sql_api_source = _read("src/pietto/sql/__init__.py")
    mysql_source = _read("src/pietto/sql/mysql.py")
    all_block = re.search(r"(?s)__all__ = \[(?P<body>.*?)\]", sql_api_source)

    assert cli_json._SCHEMA_VERSION == 1
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("pyproject.toml").lower()
    assert "sqlglot" not in lockfile.lower()

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
    assert "emit_mysql_sql" not in sql_api_source
    assert "def emit_mysql_sql(" in mysql_source
    assert "def emit_sql(" not in sql_api_source

    source_paths = (*_all_files("examples"), *_source_fixture_paths())
    assert source_paths
    assert all(path.suffix == ".pietto" for path in source_paths)

    legacy_suffix = re.compile(r"\." + "pie" + r"\b")
    assert legacy_suffix.search("\n".join(_read(path) for path in STATUS_PATHS)) is None

    phase14_surface = "\n".join(
        _read(path) for path in (READINESS_PATH, DECISION_PATH, CONTRACT_PATH)
    )
    assert re.search(r"PIE-[PSIB][0-9]{4}", phase14_surface) is None
    assert "reserves no diagnostic code" in _read(CONTRACT_PATH)

    parser_codes = set(re.findall(r"PIE-[PSIB][0-9]{4}", _read(PARSER_TEST_PATH)))
    assert parser_codes == {"PIE-P1000", "PIE-P1005"}


def test_status_docs_lock_phase14_completion_and_phase15_authorization_gate() -> None:
    for path in STATUS_PATHS:
        normalized = " ".join(_read(path).split()).lower()
        assert "phase 14" in normalized
        assert "complete" in normalized
        assert "slice 4" in normalized
        assert "parse-only" in normalized
        assert "ast-only" in normalized
        assert "phase 15" in normalized
        assert "not started" in normalized
        assert "unauthorized" in normalized
        assert "runtime" in normalized
        assert "database" in normalized

    combined = "\n".join(_read(path).lower() for path in STATUS_PATHS)
    for deferred in (
        "join",
        "relation composition",
        "sql lowering",
        "semantic validation",
        "relation-role semantics",
        "endpoint-role enforcement",
        "cardinality",
        "fanout",
        "permission gate",
        "runtime security",
        "diagnostic code",
        "json v2",
        "sqlglot",
        "project mode",
        "database connection",
        "schema introspection",
        "release",
        "publish",
        "signing",
        "upload",
        "attestation",
    ):
        assert deferred in combined

    workflow = _read(".github/workflows/ci.yml").lower()
    assert "permissions:\n  contents: read" in workflow
    assert '- "3.12"' in workflow
    assert '- "3.13"' in workflow
    for forbidden in (
        "contents: write",
        "write-all",
        "id-token:",
        "pull_request_target",
        "workflow_run",
        "upload-artifact",
        "release",
        "publish",
        "deploy",
        "attestation",
    ):
        assert forbidden not in workflow


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _generated_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
        if path.is_file()
    )


def _python_paths(root: str) -> tuple[Path, ...]:
    return tuple(sorted((REPO_ROOT / root).glob("*.py")))


def _all_files(root: str) -> tuple[Path, ...]:
    return tuple(
        path for path in sorted((REPO_ROOT / root).rglob("*")) if path.is_file()
    )


def _source_fixture_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in _all_files("tests/fixtures")
        if "golden" not in path.relative_to(REPO_ROOT).parts
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
