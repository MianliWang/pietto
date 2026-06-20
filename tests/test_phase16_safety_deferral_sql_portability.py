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
SPEC_PATH = "docs/spec/safety-deferral-and-sql-portability-v1.md"
LANGUAGE_SPEC_PATH = "docs/spec/language-direction-v1.md"
PLAN_PATH = "docs/plan/phase-16-language-direction-safety-mode.md"
STATUS_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
)

LOCKED_FILE_HASHES = {
    SPEC_PATH: "cc37df490ed1adf646883d166bc85055552e1a2bf664d65ff5e29c3978bc8570",
    LANGUAGE_SPEC_PATH: (
        "6fb738d3ec275f92762b83a2a9f469bcf66be204a7ac762ee5aa8e2780ea307c"
    ),
    PLAN_PATH: "adfb0d99075299049c790f465fab7453e0ed73b985e9cff19c6aeb38f94c7f5a",
    "grammar/Pietto.g4": (
        "d75052cfc4c5de426388cc9d8a34eef607e8023a5e1789f2e497979ea2dde9f6"
    ),
    "src/pietto/__init__.py": (
        "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d"
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
    "docs/spec/diagnostics.md": (
        "20dddffb5f2feb34736f0726e91f3b459f69668a845571a38ed3db74b42beed3"
    ),
    "pyproject.toml": (
        "021682ef880fe748f1655d4d70fcc549db4336ac39db2b29a835762ab1723d50"
    ),
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
    ".github/workflows/ci.yml": (
        "c2ba73d04dab3331ca19577f2cf4250274671aa37ec4f84f293429e118b6c4c5"
    ),
}

LOCKED_GROUP_HASHES = {
    "generated": (
        8,
        "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1",
    ),
    "semantic": (
        20,
        "dfa4af8c0dd699431ac068f1ee007e3a744d9384fe1b602aa5ab682a1f42579b",
    ),
    "ir": (
        5,
        "7438c72875751eeadf8b12b3aad1825499061f3f4e0dd73d8c1a339c614ae884",
    ),
    "sql": (
        10,
        "67aeafa622d3147b08930cebcf18862322eec692d547d328b18966afa81f3530",
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


def test_slice2_spec_and_plan_status_are_exact() -> None:
    spec = _normalized(SPEC_PATH)
    plan = _normalized(PLAN_PATH)

    assert (REPO_ROOT / SPEC_PATH).is_file()
    assert (
        "Phase 16 Slice 2 is complete as design, specification, and audit work only"
        in spec
    )
    assert (
        "Phase 16 Slice 2: Safety Surface Deferral and SQL Portability Contract "
        "is complete as design, specification, and audit work only"
    ) in plan
    assert (
        "Phase 16 Slice 3: Current Syntax Surface Audit is complete as "
        "syntax-surface audit only"
    ) in plan
    assert (
        "Phase 16 Slice 4: Phase 16 Completion Audit is complete as final audit "
        "and status work only"
    ) in plan
    assert (
        "Phase 16 Language Direction And Safety Mode is complete as design, "
        "specification, and audit work only"
    ) in plan
    assert SPEC_PATH in plan


def test_sql_portability_and_lossless_lowering_contract_is_explicit() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "supported features lower deterministically and semantically to mainstream "
        "SQL dialects",
        "prioritize SQL portability, explicit dialect contracts, deterministic "
        "SQL lowering, and fail-closed diagnostics",
        "deterministic lowering within the documented supported subset",
        "explicit contracts for each enabled SQL dialect",
        "reviewed golden tests for emitted SQL",
        "no silent semantic approximation when dialects differ",
        "fail-closed diagnostics when a requested feature is unsupported",
        "does not silently substitute a weaker, broader, narrower, or otherwise "
        "different operation",
        "Unsupported or dialect-specific behavior must fail closed",
    ):
        assert required in spec


def test_speculative_safety_and_policy_syntax_is_deferred() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Default Pietto syntax should remain small and easy to learn",
        "Source, table, and query declarations do not require safety, permission, "
        "exposure, purpose, authority, or capability metadata",
        "no `exposure` syntax",
        "no `purpose` syntax",
        "no permission, authority, or capability-token syntax",
        "no Rust-like `impl` or evidence syntax",
        "no new safety/policy strict-mode syntax or implementation",
        "These concepts are not planned source syntax",
        "The existing header and semantic checking vocabulary that includes "
        "`mode strict` remains unchanged",
        "does not reinterpret that compile-time checking policy as a safety mode, "
        "permission mode, policy mode, or runtime security guarantee",
    ):
        assert required in spec


def test_relationship_metadata_freeze_is_explicit() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Relationship metadata remains frozen as secondary read-only metadata",
        "not implicit query behavior",
        "relationship composition",
        "JOIN lowering",
        "endpoint-qualified lookup",
        "relation-role or endpoint-role enforcement",
        "a runtime or compile-time security model",
        "Relationship metadata remains outside Semantic IR and SQL lowering",
    ):
        assert required in spec


def test_dialect_contract_and_runtime_security_boundaries_are_explicit() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "PostgreSQL, MySQL, SQLite, and other SQL dialect behavior should be "
        "specified through explicit backend contracts",
        "explicitly dialect-specific under a separate reviewed contract",
        "rejected with fail-closed diagnostics",
        "does not add SQLite support",
        "runtime authorization",
        "database permission enforcement",
        "`GRANT` or row-level-security generation",
        "a policy engine",
        "privacy, isolation, authorization, or security guarantees",
        "Runtime and database security belongs to the database, warehouse, or an "
        "external policy system",
    ):
        assert required in spec

    for candidate in (
        "purpose-like intent sugar",
        "Rust-like `impl` or evidence concepts",
        "exposure-like metadata",
    ):
        assert candidate in spec
    assert "Reconsideration does not imply source syntax" in spec


def test_compiler_repository_and_fixture_surfaces_are_byte_locked() -> None:
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


def test_deferred_syntax_runtime_sql_and_security_implementations_are_absent() -> None:
    grammar = _read("grammar/Pietto.g4")
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
    )
    lowered_runtime = runtime.lower()

    for token_or_rule in (
        "EXPOSURE:",
        "PURPOSE:",
        "PERMISSION:",
        "AUTHORITY:",
        "CAPABILITY:",
        "IMPL:",
        "JOIN:",
        "exposureClause",
        "purposeClause",
        "permissionClause",
        "implEvidence",
        "joinClause",
    ):
        assert token_or_rule not in grammar

    assert "STRICT: 'strict';" in grammar
    assert "mode strict" not in lowered_runtime
    for marker in (
        "exposure_clause",
        "purpose_clause",
        "permission_gate",
        "authority_token",
        "capability_token",
        "impl_evidence",
        "safety_strict_mode",
        "policy_strict_mode",
        "composition_resolver",
        "resolve_composition",
        "relationshipir",
        "endpoint_qualified",
        "join lowering",
        "relationship lowering",
        "runtime authorization",
        "runtime security",
        "database connection",
        "schema introspection",
        "execute sql",
        "grant statement",
        "row-level security generation",
        "policy engine",
        "json v2",
    ):
        assert marker not in lowered_runtime

    for marker in (
        "RelationshipSemanticInfo",
        "RelationshipSemanticEndpointInfo",
        "RelationshipMetadata",
        "RelationshipIR",
    ):
        assert marker not in ir
        assert marker not in sql
    assert '"JOIN "' not in sql


def test_status_docs_record_slice2_without_expanding_scope() -> None:
    for path in STATUS_PATHS:
        normalized = _normalized(path)
        assert "Phase 16 Slice 2" in normalized
        assert "design, specification, and audit work only" in normalized
        assert "Phase 16 is complete" in normalized
        assert "Future work requires separate explicit authorization" in normalized
        assert SPEC_PATH in normalized
        assert PLAN_PATH in normalized

    docs = _read(SPEC_PATH) + _read(PLAN_PATH)
    assert re.findall(r"\bPIE-[PSIBR]\d{4}\b", docs) == []
    assert "reserves no diagnostic code" in _normalized(SPEC_PATH)


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _normalized(path: str) -> str:
    return " ".join(_read(path).split())


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
