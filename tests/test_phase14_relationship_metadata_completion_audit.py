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

UNCHANGED_FILE_HASHES = {
    "src/pietto/parser_api.py": (
        "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b"
    ),
    "src/pietto/errors.py": (
        "7aa9622bde3eb07bb64bb5c932dc69e48d635e89790b26e8090b9309c5cf62f6"
    ),
    "src/pietto/generated/__init__.py": (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
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

UNCHANGED_GROUP_HASHES = {
    "semantic": "3c1bb49ad1b22d05747a8246c882982318048e3e0a195e6bcfe9da09847b231c",
    "ir": "a7af3fe9b002bb3e1a781f4962b44349b93f1baa098771c38b08bba44e3bcc7b",
    "sql": "ea79bb45960afbfcfb28a16cbe5c8ee8a80e3af0f6087236a6acaf10b11729c9",
}

GOLDENS_HASH = "539a980e24fc41be1e645b4527b3114d6046e0014f7c8d347e150bd1721ef728"


def test_slice3_contract_and_status_are_parse_only_and_ast_only() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    assert "# Relationship Endpoint Metadata Syntax Version 1" in contract
    assert "Phase 14 Slice 3 as a parse-only and AST-only" in normalized
    assert "Relationship declarations are accepted only as source metadata" in (
        normalized
    )
    for required in (
        "exactly two endpoint lines",
        "contextual language words",
        "`RelationshipEndpoint`",
        "`RelationshipMetadata`",
        "`Script.relationships`",
        "Relationship metadata is intentionally not part of `Script.definitions`",
        "Semantic analysis | Unchanged and unaware",
        "Semantic IR | Unchanged",
        "PostgreSQL and MySQL SQL | Unchanged",
        "JSON schema version 1",
    ):
        assert required in contract

    for path in (
        DECISION_PATH,
        READINESS_PATH,
        "README.md",
        "AGENTS.md",
        "docs/spec/pietto-v0.9.md",
    ):
        document = _read(path)
        assert CONTRACT_PATH in document
        assert "Phase 14 Slice 3" in document


def test_grammar_and_ast_define_only_the_metadata_surface() -> None:
    grammar = _read("grammar/Pietto.g4")
    ast_nodes = _read("src/pietto/ast_nodes.py")
    ast_builder = _read("src/pietto/ast_builder.py")

    for syntax in (
        "relationshipDefinition",
        "relationshipEndpoint",
        "RELATIONSHIP: 'relationship';",
        "ENDPOINT: 'endpoint';",
    ):
        assert syntax in grammar
    assert "relationshipBody" in grammar
    assert "relationshipEndpoint NEWLINE* relationshipEndpoint" in grammar
    assert "| RELATIONSHIP" in grammar
    assert "| ENDPOINT" in grammar

    assert "class RelationshipEndpoint(Node):" in ast_nodes
    assert "class RelationshipMetadata(Node):" in ast_nodes
    assert "endpoints: tuple[RelationshipEndpoint, RelationshipEndpoint]" in ast_nodes
    assert "relationships: tuple[RelationshipMetadata, ...] = ()" in ast_nodes
    assert "relationships=relationships" in ast_builder

    lowered_grammar = grammar.lower()
    for forbidden in (
        "joinClause",
        "join:",
        "relationRole",
        "cardinality",
        "fanout",
        "permission gate",
    ):
        assert forbidden.lower() not in lowered_grammar


def test_generated_inventory_and_provenance_are_exact() -> None:
    expected = (
        "Pietto.interp",
        "Pietto.tokens",
        "PiettoLexer.interp",
        "PiettoLexer.py",
        "PiettoLexer.tokens",
        "PiettoParser.py",
        "PiettoVisitor.py",
        "__init__.py",
    )
    generated_root = REPO_ROOT / "src/pietto/generated"

    assert (
        tuple(path.name for path in sorted(generated_root.iterdir()) if path.is_file())
        == expected
    )
    assert (generated_root / "__init__.py").read_bytes() == b""
    assert "relationshipDefinition" in _read("src/pietto/generated/PiettoParser.py")
    assert "visitRelationshipDefinition" in _read(
        "src/pietto/generated/PiettoVisitor.py"
    )
    assert "RELATIONSHIP" in _read("src/pietto/generated/PiettoLexer.py")
    assert "java -jar $(ANTLR_JAR)" in _read("Makefile")
    assert "-visitor -no-listener -Xexact-output-dir" in _read("Makefile")


def test_forbidden_compiler_layers_and_repository_surfaces_are_byte_locked() -> None:
    for path, expected_hash in UNCHANGED_FILE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    groups = {
        "semantic": _module_paths("src/pietto/semantic"),
        "ir": _module_paths("src/pietto/ir"),
        "sql": _module_paths("src/pietto/sql"),
    }
    for name, paths in groups.items():
        assert _aggregate_sha256(paths) == UNCHANGED_GROUP_HASHES[name]

    project = tomllib.loads(_read("pyproject.toml"))
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert project["project"]["scripts"] == {"pietto": "pietto.cli:main"}
    assert (
        _aggregate_files(
            path
            for path in (REPO_ROOT / "tests/fixtures/golden").iterdir()
            if path.is_file()
        )
        == GOLDENS_HASH
    )
    assert len(tuple((REPO_ROOT / "tests/fixtures/golden").iterdir())) == 19


def test_public_sql_api_json_v1_and_private_mysql_boundary_are_unchanged() -> None:
    sql_api_source = _read("src/pietto/sql/__init__.py")
    mysql_source = _read("src/pietto/sql/mysql.py")
    all_block = re.search(r"(?s)__all__ = \[(?P<body>.*?)\]", sql_api_source)

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
    assert cli_json._SCHEMA_VERSION == 1


def test_no_semantic_sql_runtime_security_or_diagnostic_surface_was_added() -> None:
    forbidden_runtime = "\n".join(
        _read(path)
        for path in (
            *_module_paths("src/pietto/semantic"),
            *_module_paths("src/pietto/ir"),
            *_module_paths("src/pietto/sql"),
            "src/pietto/parser_api.py",
            "src/pietto/errors.py",
            "src/pietto/cli.py",
            "src/pietto/cli_json.py",
        )
    ).lower()

    for marker in (
        "relationshipmetadata",
        "relationshipendpoint",
        "relationship syntax",
        "relation composition",
        "join lowering",
        "composition lowering",
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
        assert marker not in forbidden_runtime

    changed_surface = "\n".join(
        _read(path)
        for path in (
            CONTRACT_PATH,
            "grammar/Pietto.g4",
            "src/pietto/ast_nodes.py",
            "src/pietto/ast_builder.py",
            "tests/test_phase14_relationship_metadata_parser.py",
        )
    )
    concrete_code = re.compile(r"(?<!PIE-)\b[PSIB][0-9]{4}\b")
    assert concrete_code.search(changed_surface) is None
    assert re.search(r"\." + "pie" + r"\b", changed_surface) is None


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_paths(root: str) -> tuple[str, ...]:
    return tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in sorted((REPO_ROOT / root).glob("*.py"))
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
