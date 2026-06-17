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
SPEC_PATH = "docs/spec/language-direction-v1.md"
PLAN_PATH = "docs/plan/phase-16-language-direction-safety-mode.md"
STATUS_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
)

LOCKED_FILE_HASHES = {
    SPEC_PATH: "6fb738d3ec275f92762b83a2a9f469bcf66be204a7ac762ee5aa8e2780ea307c",
    PLAN_PATH: "adfb0d99075299049c790f465fab7453e0ed73b985e9cff19c6aeb38f94c7f5a",
    "grammar/Pietto.g4": (
        "aa9b7fe9e35ff64269fa64e8db9555897f6c16f70f293b6cb4a071a1ef25e7c1"
    ),
    "src/pietto/__init__.py": (
        "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d"
    ),
    "src/pietto/ast_nodes.py": (
        "1a08986999697940b6c4f778508b83c9c123dcb7de62f9de26511e2a4d36bc94"
    ),
    "src/pietto/ast_builder.py": (
        "cb01ad879fb95833bf250e8502ca22757ffdbd1c6a9ebb3632d0ea100fe21cdc"
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
    "docs/spec/diagnostics.md": (
        "ceed55f6c3f18ce928d4faaf8cae75368d5f8a1f11281a3839ed5929bcb65d39"
    ),
    "pyproject.toml": (
        "021682ef880fe748f1655d4d70fcc549db4336ac39db2b29a835762ab1723d50"
    ),
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
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
        "ead48cc705797cddb75e672db2fd6f49070de544c5f06bdd350b40bfce57e22d"
    ),
    "scripts/package_smoke.py": (
        "61de7eec8f26476e39d05305642ecde0a55d1030513ce91f627cac45517c1131"
    ),
}

LOCKED_GROUP_HASHES = {
    "generated": (
        8,
        "655bfa5fd1bbc263f24f188a3526ab18657a1e1ab24c4ee18804416613166913",
    ),
    "semantic": (
        19,
        "35d3e741814070f0a8ef04a0133fd68e476a0e44b07b45b1482f9767eae9c785",
    ),
    "ir": (
        5,
        "b8867c8f4c2396936f607c616a81184c0f46071ba5d2db60b70a217db9719808",
    ),
    "sql": (
        10,
        "2fd6e7a45db95619a228150e26e2f78dfdcd1f24e72499780955c911c82221a2",
    ),
    "examples": (
        10,
        "230369f90130d7c4b722b75ef2ec264d98e0d6f34ad3b1b5fd7d5fbf04d45a97",
    ),
    "fixtures": (
        44,
        "d27e4dad84810a67c25250c52a034356e809f5c7ee1f4819a4475a944c7365d5",
    ),
    "goldens": (
        25,
        "626188783ed0e9cf20f1d6a38ef5009ada08812a2cd2cffa2cc6d0daf8a3f6e2",
    ),
}


def test_phase16_documents_and_four_slice_status_are_exact() -> None:
    spec = _read(SPEC_PATH)
    plan = _read(PLAN_PATH)
    normalized = " ".join(plan.split())

    assert (REPO_ROOT / SPEC_PATH).is_file()
    assert (REPO_ROOT / PLAN_PATH).is_file()
    assert (
        "**Phase 16 Slice 1: Language Direction and Syntax Philosophy is "
        "complete as design, specification, and audit work only.**" in normalized
    )
    for required in (
        "**Phase 16 Slice 2: Safety Surface Deferral and SQL Portability "
        "Contract is complete as design, specification, and audit work only.**",
        "**Phase 16 Slice 3: Current Syntax Surface Audit is complete as "
        "syntax-surface audit only.**",
        "**Phase 16 Slice 4: Phase 16 Completion Audit is complete as final "
        "audit and status work only.**",
        "**Phase 16 Language Direction And Safety Mode is complete as design, "
        "specification, and audit work only.**",
        "Phase 16 introduced no accepted syntax changes",
        "Phase 16 introduced no compiler, runtime, or database behavior changes",
        "Phase 16 completion does not authorize Phase 17 or any production "
        "implementation automatically",
    ):
        assert required in normalized

    assert SPEC_PATH in plan
    assert "defines no new accepted Pietto syntax" in spec


def test_language_identity_slogan_and_syntax_philosophy_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Pietto is a typed SQL authoring DSL",
        "readable, indentation-based source with colon-delimited blocks",
        "small core language",
        "diagnostic-first failure reporting",
        "explicit syntax at dangerous or ambiguous boundaries",
        "familiar and concise path for normal single-relation queries",
        "compile-time guarantees and runtime/database security",
        "Simple by default, explicit when dangerous, fail closed on ambiguity.",
        "Use colon plus indentation for blocks",
        "Do not introduce braces as block delimiters",
        "Keep the keyword and punctuation vocabulary small",
        "Reject ambiguity with source-located diagnostics instead of guessing",
        "Add syntax only through a separately reviewed contract",
    ):
        assert required in spec


def test_relationship_metadata_position_and_security_boundary_are_explicit() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Relationship metadata is secondary descriptive metadata",
        "It is not the center of ordinary Pietto query authoring",
        "Pietto is not a relationship-graph language first",
        "remains outside Semantic IR and SQL generation",
        "does not create a JOIN or relation-composition operation",
        "does not authorize endpoint-qualified lookup or multi-input queries",
        "does not perform SQL lowering",
        "does not enforce runtime authorization, access control, privacy, or "
        "database security",
        "Existing metadata must not be treated as implicit query behavior",
        "database authentication or authorization",
        "row-level security, masking, privacy, or policy isolation",
        "connector or database execution",
        "schema introspection or validation against a live database",
        "Pietto must not claim runtime security or privacy guarantees unless "
        "separately implemented",
    ):
        assert required in spec


def test_future_candidates_and_explicit_non_goals_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())
    candidates = (
        "core SQL authoring improvements",
        "aggregates and measures planning",
        "relationship-aware querying",
        "strict mode design",
        "project workflow",
    )

    assert "The following are equal candidates for later planning" in spec
    assert "Their order does not express priority" in spec
    assert "none is an automatic next step or implementation authorization" in spec
    assert [spec.index(candidate) for candidate in candidates] == sorted(
        spec.index(candidate) for candidate in candidates
    )

    for non_goal in (
        "not a runtime database framework",
        "not an access-control system",
        "not a relationship graph language first",
        "not a Malloy clone",
        "not a security-policy DSL",
        "makes no runtime authorization, access-control, privacy, isolation, "
        "database-execution, or safe-sharing guarantee",
    ):
        assert non_goal in spec

    docs = _read(SPEC_PATH) + _read(PLAN_PATH)
    assert re.findall(r"\bPIE-[PSIBR]\d{4}\b", docs) == []
    assert "reserves no diagnostic code" in spec


def test_compiler_repository_and_document_contracts_are_byte_locked() -> None:
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


def test_public_sql_json_dependency_package_and_ci_boundaries_are_locked() -> None:
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
    assert project["project"]["requires-python"] == ">=3.12"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert "sqlglot" not in _read("uv.lock").lower()
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)


def test_deferred_runtime_composition_and_security_capabilities_are_absent() -> None:
    semantic = _runtime_text("src/pietto/semantic")
    ir = _runtime_text("src/pietto/ir")
    sql = _runtime_text("src/pietto/sql")
    runtime = "\n".join(
        (
            semantic,
            ir,
            sql,
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
        "permission gate",
        "runtime authorization",
        "runtime security",
        "database connection",
        "schema introspection",
        "execute sql",
        "json v2",
        "sqlglot",
        "compile_to_sql",
    ):
        assert marker not in runtime

    for marker in (
        "RelationshipSemanticInfo",
        "RelationshipSemanticEndpointInfo",
        "RelationshipMetadata",
        "RelationshipIR",
    ):
        assert marker not in ir
        assert marker not in sql
    assert '"JOIN "' not in sql


def test_status_docs_record_slice1_without_implementation_authorization() -> None:
    for path in STATUS_PATHS:
        normalized = " ".join(_read(path).split())
        assert "Phase 16" in normalized
        assert "Slice 1" in normalized
        assert "design, specification, and audit work only" in normalized
        assert "Phase 16 is complete" in normalized
        assert "Future work requires separate explicit authorization" in normalized
        assert SPEC_PATH in normalized
        assert PLAN_PATH in normalized


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
