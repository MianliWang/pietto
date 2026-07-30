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
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
)

LOCKED_FILE_HASHES = {
    SPEC_PATH: "6fb738d3ec275f92762b83a2a9f469bcf66be204a7ac762ee5aa8e2780ea307c",
    PLAN_PATH: "adfb0d99075299049c790f465fab7453e0ed73b985e9cff19c6aeb38f94c7f5a",
    "grammar/Pietto.g4": (
        "661f00037b4ade8f8b5bef0cb3e070e4379decdd11cd19021d68e960e69d2724"
    ),
    "src/pietto/__init__.py": (
        "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d"
    ),
    "src/pietto/ast_nodes.py": (
        "bbfd121446d62d33c7990b80d17579d3f8b55763ce1b5f93ee17247cbd2ce0c2"
    ),
    "src/pietto/ast_builder.py": (
        "918dc9f6d7705376b604e69fb80c45cf4c3673c8909a58537770d114d96252cb"
    ),
    "src/pietto/parser_api.py": (
        "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b"
    ),
    "src/pietto/errors.py": (
        "7aa9622bde3eb07bb64bb5c932dc69e48d635e89790b26e8090b9309c5cf62f6"
    ),
    "src/pietto/cli.py": (
        "e9d90d40293db543c4b6c0da829e8b6a122fd2f8b29fcafdc23d4d54b1c42e09"
    ),
    "src/pietto/cli_json.py": (
        "ccee00529ee36b123f70d418105609dbb4906f2ccc1c1f5653527b1168fb6d91"
    ),
    "src/pietto/sql/__init__.py": (
        "e40bd3eee7f76bc68313adb8237a7a6c5d84286197261f70c827a4219c9e3418"
    ),
    "docs/spec/diagnostics.md": (
        "d70d62c76ddb25a8c2000a7cd1cb2f8071e90d3ed62fb6b8cf3b8c0655ff7c98"
    ),
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
    "scripts/validate.py": (
        "567c9ea1836c39d4e2037012e2b6e7795ceb3a9f54e9e3f7d951ae39155a5987"
    ),
    "scripts/check_generated.py": (
        "b126059cd0aebe9535fceb9b0a1b1c09ee1ba22af13f70d276d7e013c49c60e7"
    ),
    "scripts/check_goldens.py": (
        "23e271e0138e6b7ac189e27f33c557e04300301adff8f49747999e0c4b50c2e9"
    ),
    "scripts/package_smoke.py": (
        "aa6ab2ddf8ed8e889e8d75de224467565b7e6034cf068b44d602807fdd554924"
    ),
}

LOCKED_GROUP_HASHES = {
    "generated": (
        8,
        "9a84d108062bdbd87f5cd1d6e237e66f8bbb39d1d9d7674312eab6eb156cbad1",
    ),
    "semantic": (
        36,
        "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70",
    ),
    "ir": (
        5,
        "04cb667ff3c9cdf0189d9fd0caa5dc0f9db74ca78dd86e965f020b4523f543e9",
    ),
    "sql": (
        10,
        "72a23f954c49337192effe005c9b3331359b132cc06f494fd4922b9718d1c026",
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
    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["project"]["dependencies"]
    ] == ["antlr4-python3-runtime"]
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


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
