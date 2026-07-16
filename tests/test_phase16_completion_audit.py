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
PLAN_PATH = "docs/plan/phase-16-language-direction-safety-mode.md"
LANGUAGE_SPEC_PATH = "docs/spec/language-direction-v1.md"
PORTABILITY_SPEC_PATH = "docs/spec/safety-deferral-and-sql-portability-v1.md"
SYNTAX_SPEC_PATH = "docs/spec/current-syntax-surface-audit-v1.md"
SLICE1_AUDIT_PATH = "tests/test_phase16_language_direction_audit.py"
SLICE2_AUDIT_PATH = "tests/test_phase16_safety_deferral_sql_portability.py"
SLICE3_AUDIT_PATH = "tests/test_phase16_current_syntax_surface_audit.py"
STATUS_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    PLAN_PATH,
)

PHASE16_ARTIFACT_HASHES = {
    LANGUAGE_SPEC_PATH: (
        "6fb738d3ec275f92762b83a2a9f469bcf66be204a7ac762ee5aa8e2780ea307c"
    ),
    PORTABILITY_SPEC_PATH: (
        "cc37df490ed1adf646883d166bc85055552e1a2bf664d65ff5e29c3978bc8570"
    ),
    SYNTAX_SPEC_PATH: (
        "580ebcfcc78102d902110d864eb80c7f1a57ffcb6b4b33e1160c9abd17ba07a6"
    ),
    SLICE1_AUDIT_PATH: (
        "21c74ec3628930db13cdff30d490216094fe73789a8b1159bf8cb9fd68cf3253"
    ),
    SLICE2_AUDIT_PATH: (
        "013ea777b23084d4ab24247932be6f4bed7fac3c226601b46ecc4e56a9c6e980"
    ),
    SLICE3_AUDIT_PATH: (
        "3f65484bb61037902571230e66fd353684dbbdd9c80bf36cce79c9edcbc26ef7"
    ),
    PLAN_PATH: "adfb0d99075299049c790f465fab7453e0ed73b985e9cff19c6aeb38f94c7f5a",
}

LOCKED_FILE_HASHES = {
    "grammar/Pietto.g4": (
        "54484b73f76ae051e0e4f27cc47bc99a0687da7c0e4f40ab4da06a640a54369a"
    ),
    "src/pietto/__init__.py": (
        "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d"
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
        "7ac3aea913b1453a972456be0171a2c292991e71bde3e94a4056b4bf537b5c4e",
    ),
    "semantic": (
        25,
        "88e625ce882c5b84a566ae1a9b64048946986ca2ba6b2de02ec21c45a6f63877",
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


def test_four_slice_sequence_and_phase16_completion_are_explicit() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 16 Slice 1: Language Direction and Syntax Philosophy is complete",
        "Phase 16 Slice 2: Safety Surface Deferral and SQL Portability Contract "
        "is complete",
        "Phase 16 Slice 3: Current Syntax Surface Audit is complete",
        "Phase 16 Slice 4: Phase 16 Completion Audit is complete",
        "Phase 16 Language Direction And Safety Mode is complete as design, "
        "specification, and audit work only",
        "Phase 16 completion does not authorize Phase 17 or any production "
        "implementation automatically",
    ):
        assert required in plan

    assert "planned only" not in plan
    assert "tests/test_phase16_completion_audit.py" in plan


def test_all_phase16_specs_and_focused_audits_are_byte_locked() -> None:
    for path, expected_hash in PHASE16_ARTIFACT_HASHES.items():
        assert (REPO_ROOT / path).is_file()
        assert _sha256(REPO_ROOT / path) == expected_hash

    assert {
        "test_language_identity_slogan_and_syntax_philosophy_are_locked",
        "test_sql_portability_and_lossless_lowering_contract_is_explicit",
        "test_spec_lists_the_current_accepted_syntax_surface",
    } <= (
        _test_names(_read(SLICE1_AUDIT_PATH))
        | _test_names(_read(SLICE2_AUDIT_PATH))
        | _test_names(_read(SLICE3_AUDIT_PATH))
    )


def test_language_portability_and_unchanged_syntax_contracts_remain_exact() -> None:
    language = _normalized(LANGUAGE_SPEC_PATH)
    portability = _normalized(PORTABILITY_SPEC_PATH)
    syntax = _normalized(SYNTAX_SPEC_PATH)

    assert "Pietto is a typed SQL authoring DSL" in language
    assert (
        "Simple by default, explicit when dangerous, fail closed on ambiguity."
        in language
    )
    for required in (
        "prioritize SQL portability, explicit dialect contracts, deterministic "
        "SQL lowering, and fail-closed diagnostics",
        "deterministic lowering within the documented supported subset",
        "no silent semantic approximation when dialects differ",
        "Unsupported or dialect-specific behavior must fail closed",
    ):
        assert required in portability

    for required in (
        "The accepted syntax is unchanged by Phase 16",
        "`source name: Shape is connector`",
        "`source name: Shape = connector` is not accepted syntax",
        "The existing header form `mode strict` remains compile-time checking",
    ):
        assert required in syntax


def test_relationship_metadata_and_speculative_syntax_remain_frozen() -> None:
    language = _normalized(LANGUAGE_SPEC_PATH)
    portability = _normalized(PORTABILITY_SPEC_PATH)
    syntax = _normalized(SYNTAX_SPEC_PATH)
    combined = " ".join((language, portability, syntax))

    for required in (
        "secondary read-only metadata",
        "JOIN lowering",
        "relationship composition",
        "endpoint-qualified lookup",
        "relation-role or endpoint-role enforcement",
        "SQL lowering",
        "security model",
    ):
        assert required in combined

    for required in (
        "`exposure`",
        "`purpose`",
        "`for <purpose>`",
        "Rust-like `impl` or evidence",
        "Permission, authority, or capability-token forms",
        "JOIN forms",
        "Relationship composition forms",
        "Endpoint-qualified lookup forms",
        "Runtime, policy, privacy, or security forms",
        "A new safety/policy strict mode",
    ):
        assert required in syntax


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


def test_public_sql_mysql_json_dependency_package_and_ci_boundaries_are_locked() -> (
    None
):
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
    for marker in (
        "contents: write",
        "id-token:",
        "upload-artifact",
        "release",
        "publish",
        "deploy",
        "attestation",
    ):
        assert marker not in workflow.lower()


def test_no_new_diagnostic_or_deferred_grammar_syntax_exists() -> None:
    docs = "\n".join(
        (
            _read(LANGUAGE_SPEC_PATH),
            _read(PORTABILITY_SPEC_PATH),
            _read(SYNTAX_SPEC_PATH),
            _read(PLAN_PATH),
        )
    )
    grammar = _read("grammar/Pietto.g4")

    assert re.findall(r"\bPIE-[PSIBR]\d{4}\b", docs) == []
    assert docs.count("reserves no diagnostic code") >= 2
    assert "introduces no diagnostic code and reserves no diagnostic code" in docs

    for token_or_rule in (
        "EXPOSURE:",
        "PURPOSE:",
        "FOR:",
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
        "endpointQualified",
    ):
        assert token_or_rule not in grammar


def test_runtime_database_composition_and_policy_behavior_remain_absent() -> None:
    ir = _runtime_text("src/pietto/ir")
    sql = _runtime_text("src/pietto/sql")
    runtime = "\n".join(
        (
            _runtime_text("src/pietto/semantic"),
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
        "permission_gate",
        "authority_token",
        "capability_token",
        "safety_strict_mode",
        "policy_strict_mode",
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


def test_status_docs_record_phase16_completion_without_expanding_scope() -> None:
    for path in STATUS_PATHS:
        normalized = _normalized(path)
        assert "Phase 16" in normalized
        assert "complete" in normalized
        assert "design, specification, and audit work only" in normalized
        assert "introduced no accepted syntax" in normalized
        assert "compiler, runtime, or database behavior" in normalized
        assert "Future work requires separate explicit authorization" in normalized

    combined = " ".join(_normalized(path) for path in STATUS_PATHS)
    for required in (
        "SQL portability",
        "lossless lowering",
        "unchanged accepted",
        "speculative",
        "deferred",
        "Phase 17",
        "does not authorize",
    ):
        assert required in combined


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _normalized(path: str) -> str:
    return " ".join(_read(path).split())


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
