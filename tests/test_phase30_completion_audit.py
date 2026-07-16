from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-30-core-type-system-stabilization-i.md"
CORE_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/core-type-system-stabilization-contract-v1.md"
)
REGISTRY_CONTRACT_PATH = REPO_ROOT / "docs/spec/canonical-scalar-type-registry-v1.md"
NULLABILITY_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/nullability-propagation-contract-v1.md"
)
BOOL_CONTRACT_PATH = REPO_ROOT / "docs/spec/bool-predicate-semantics-contract-v1.md"
DATE_CONTRACT_PATH = REPO_ROOT / "docs/spec/date-timestamp-formalization-contract-v1.md"
DECIMAL_CONTRACT_PATH = REPO_ROOT / "docs/spec/decimal-precision-scale-contract-v1.md"
OPERATOR_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/operator-comparison-matrix-contract-v1.md"
)

PHASE29_REGISTER_SPEC_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE29_AGGREGATE_FREEZE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
)
PHASE29_TYPE_GAP_SPEC_PATH = (
    REPO_ROOT / "docs/spec/v02-core-type-system-gap-matrix-v1.md"
)
PHASE29_EXIT_CRITERIA_SPEC_PATH = (
    REPO_ROOT / "docs/spec/v02-exit-criteria-validation-strategy-v1.md"
)
CLI_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/cli-json-v1.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"

PHASE30_ARTIFACTS = (
    "docs/plan/phase-30-core-type-system-stabilization-i.md",
    "docs/spec/core-type-system-stabilization-contract-v1.md",
    "docs/spec/canonical-scalar-type-registry-v1.md",
    "docs/spec/nullability-propagation-contract-v1.md",
    "docs/spec/bool-predicate-semantics-contract-v1.md",
    "docs/spec/date-timestamp-formalization-contract-v1.md",
    "docs/spec/decimal-precision-scale-contract-v1.md",
    "docs/spec/operator-comparison-matrix-contract-v1.md",
    "tests/test_phase30_candidate_decision.py",
    "tests/test_phase30_canonical_scalar_type_registry.py",
    "tests/test_phase30_nullability_propagation_contract.py",
    "tests/test_phase30_bool_predicate_semantics_contract.py",
    "tests/test_phase30_date_timestamp_formalization_contract.py",
    "tests/test_phase30_decimal_precision_scale_contract.py",
    "tests/test_phase30_operator_comparison_matrix_contract.py",
    "tests/test_phase30_completion_audit.py",
)

PHASE30_SLICE_STATUS = (
    "Phase 30 Slice 1 is complete as candidate decision, type-system "
    "contract, static audit, and status work only",
    "Phase 30 Slice 2 is complete as canonical scalar type registry "
    "contract, static audit, and status work only",
    "Phase 30 Slice 3 is complete as nullability propagation contract, "
    "static audit, and status work only",
    "Phase 30 Slice 4 is complete as Bool and predicate semantics "
    "contract, static audit, and status work only",
    "Phase 30 Slice 5 is complete as Date / Timestamp formalization "
    "contract, static audit, and status work only",
    "Phase 30 Slice 6 is complete as Decimal precision / scale contract, "
    "static audit, and status work only",
    "Phase 30 Slice 7 is complete as operator and comparison matrix "
    "contract, static audit, and status work only",
    "Phase 30 Slice 8 is complete as completion audit and status lock work only",
)

REQUIRED_VALIDATION_COMMANDS = (
    "uv run pytest tests/test_phase30_completion_audit.py",
    "uv run pytest tests/test_phase30_operator_comparison_matrix_contract.py",
    "uv run pytest tests/test_phase30_decimal_precision_scale_contract.py",
    "uv run pytest tests/test_phase30_date_timestamp_formalization_contract.py",
    "uv run pytest tests/test_phase30_bool_predicate_semantics_contract.py",
    "uv run pytest tests/test_phase30_nullability_propagation_contract.py",
    "uv run pytest tests/test_phase30_canonical_scalar_type_registry.py",
    "uv run pytest tests/test_phase30_candidate_decision.py",
    "uv run pytest tests/test_phase29_completion_audit.py "
    "tests/test_phase29_v02_deferred_feature_register.py "
    "tests/test_phase29_v02_aggregate_surface_freeze.py "
    "tests/test_phase29_v02_exit_criteria_validation_strategy.py",
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
    "uv run python scripts/validate.py",
    "git diff --check",
    "git diff -- src grammar tests/fixtures scripts pyproject.toml uv.lock "
    ".github Makefile",
)

LOCKED_BOUNDARY_SURFACES = {
    "grammar": (
        "grammar/Pietto.g4",
        1,
        "03f2eb98ab656dfe4c33bd8088306f3525150c738f42bf09640c02d973d54a2f",
    ),
    "generated": (
        "src/pietto/generated",
        8,
        "7ac3aea913b1453a972456be0171a2c292991e71bde3e94a4056b4bf537b5c4e",
    ),
    "ast_nodes": (
        "src/pietto/ast_nodes.py",
        1,
        "9946bd71566f8c7fd72dfa22b972722922087b7588b435cce59daa1fc25c560d",
    ),
    "ast_builder": (
        "src/pietto/ast_builder.py",
        1,
        "c351d001982ee52274ec21fd6af151baea8b9153caf524415f50bfee17fbcf3d",
    ),
    "parser_api": (
        "src/pietto/parser_api.py",
        1,
        "537178041b413d964bda00aef376f90d745a64d61378ede2dbc6a715b49e7f3f",
    ),
    "semantic": (
        "src/pietto/semantic",
        25,
        "88e625ce882c5b84a566ae1a9b64048946986ca2ba6b2de02ec21c45a6f63877",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "57097f43ba5e0ffa8d531b827b7029c9104b85ab3dc0657889cccd28caec5249",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "310c07a1a5c9ae53f878b143b9d5dc3b092bfdfa072728ee4cae168e361907ec",
    ),
    "cli_json": (
        "src/pietto/cli_json.py",
        1,
        "573fd193b98a746cfd84a6990a22248d2b63a7fc0ed1069f442ffff9c4dd99e7",
    ),
    "diagnostics": (
        "docs/spec/diagnostics.md",
        1,
        "677b1e4f29d16f7bc90335afcfdb36fed42761795814adbf37d657eae267983d",
    ),
    "fixtures": (
        "tests/fixtures",
        68,
        "dbd457dd7e79f41d0e1740187818478941861cabf9ae9f3b06f908bdc81cd11c",
    ),
    "goldens": (
        "tests/fixtures/golden",
        37,
        "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004",
    ),
    "scripts": (
        "scripts",
        4,
        "013844a763f970b8e0f0094f0c68ad114e3056fb1f12858c5c2758c2c57e9887",
    ),
    "makefile": (
        "Makefile",
        1,
        "14c05902d307dbc803c31d522ebe6d2614d36f2c428e4c1eca2d4441661dbe09",
    ),
    "readme": (
        "README.md",
        1,
        "a9012c03259cc7d8cb983f70fcd6481719f06ead73a0decbea7f7a4f76b55ac2",
    ),
    "agents": (
        "AGENTS.md",
        1,
        "27fef9e67bec8917eff21ad2dd41cb22f9feea37e62200ac78864cba2d5aa589",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "8c5f7ae8e5f6bbcbe7c004e681ba4bf8e417efb62240137f83ccd6d5a8472b39",
    ),
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_phase30_artifact_inventory_and_slice_completion_are_locked() -> None:
    for relative_path in PHASE30_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    contracts = " ".join(
        _normalized(path)
        for path in (
            CORE_CONTRACT_PATH,
            REGISTRY_CONTRACT_PATH,
            NULLABILITY_CONTRACT_PATH,
            BOOL_CONTRACT_PATH,
            DATE_CONTRACT_PATH,
            DECIMAL_CONTRACT_PATH,
            OPERATOR_CONTRACT_PATH,
        )
    )

    for required in PHASE30_SLICE_STATUS:
        assert required in plan

    for required in (
        "Phase 30 Core Type System Stabilization I is complete as "
        "docs/spec/static-audit/status work only",
        "v0.2 is not complete yet",
        "Phase 31 Core Type System Stabilization II And Dialect Matrix "
        "Hardening is the next mainline",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
        "Phase 31 is not implemented by Phase 30",
    ):
        assert required in plan

    assert "Slice 8 must not start until separately approved" not in plan
    assert "Slice 8 remains planned only" not in plan
    assert "v0.2 is complete" not in plan

    for required in (
        "Slice 8 is complete as completion audit",
        "Phase 30 is complete as docs/spec/static-audit/status work only",
        "v0.2 is not complete",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in contracts


def test_phase30_status_docs_lock_v02_completion_after_phase31_slice8() -> None:
    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 30 Core Type System Stabilization I",
            "Phase 30 is complete",
            "docs/spec/static-audit/status work only",
            "Slice 8 is complete as completion audit and status lock work only",
            "Phase 31 v0.2 Hardening And Stable Completion is complete",
            "Pietto v0.2 single-file stable complete",
            "Phase 31 complete",
            "Phase 31 Slice 8 complete",
            "Phase 32 has started",
            "Phase 32 Slice 1 Candidate Decision, Roadmap Alignment, And v0.2 "
            "Handoff Audit is complete as docs/spec/static-audit/status-only work",
            "Phase 32 as a whole is not complete",
            "Phase 32: Semantic Explain And Metadata Output MVP",
            "Internal v0.2 completion does not imply a package release",
            "no source implementation",
            "grammar",
            "generated",
            "CLI/JSON/API, IR, SQL, semantic",
            "public MySQL API",
            "type-system behavior",
            "package version",
            "release",
            "publication",
            "JSON v2",
            "Phase 31 implementation",
        ):
            assert required in status_doc
        assert "Phase 32 remains post-v0.2 and has not started" not in status_doc

        for forbidden in (
            "Pietto 0.2.0 released",
            "v0.2 package published",
            "v0.2 Git tag created",
            "Phase 32 is complete",
            "Phase 31 implementation is complete",
            "Phase 30 implements Phase 31",
            "Phase 30 changes JSON v1",
            "Phase 30 implements JSON v2",
            "Phase 30 expands aggregate",
            "Phase 30 changes SQL lowering",
            "Phase 30 changes diagnostics",
            "public `emit_mysql_sql`",
        ):
            assert forbidden not in status_doc


def test_phase30_phase29_handoff_and_frozen_surfaces_remain_preserved() -> None:
    register = _normalized(PHASE29_REGISTER_SPEC_PATH)
    aggregate_freeze = _normalized(PHASE29_AGGREGATE_FREEZE_SPEC_PATH)
    type_gap = _normalized(PHASE29_TYPE_GAP_SPEC_PATH)
    exit_criteria = _normalized(PHASE29_EXIT_CRITERIA_SPEC_PATH)

    for required in (
        "It does not authorize implementation",
        "Aggregate expansion",
        "JSON v2",
        "No SQL execution",
        "No JOIN implementation",
        "Project/multi-file",
        "Runtime/database execution",
    ):
        assert required in register

    for required in (
        "For v0.2, the Phase 19 through Phase 28 aggregate surface is frozen "
        "except for bug fixes and audit-only clarifications",
        "Rejected v0.2 Aggregate Expansions",
        "new aggregate functions",
        "`count(expression)`",
        "`min(expression)` beyond direct fields",
        "`max(expression)` beyond direct fields",
    ):
        assert required in aggregate_freeze

    for required in (
        "Canonical scalar type registry",
        "Nullability propagation",
        "Predicate semantics / SQL three-valued logic boundary",
        "Decimal precision/scale",
        "Operator compatibility matrix",
        "Comparison compatibility matrix",
    ):
        assert required in type_gap

    for required in (
        "It does not declare v0.2 complete",
        "Phase 31 Core Type System Stabilization II And Dialect Matrix Hardening",
        "Phase 32 v0.2 Single-file Stable Completion Audit",
        "remain required before the v0.2 stable completion status can be locked",
        "package version changes",
        "release tags",
        "publication",
        "JSON v2",
        "public MySQL API expansion",
    ):
        assert required in exit_criteria


def test_phase30_public_api_cli_json_package_and_ci_boundaries_are_locked() -> None:
    cli_json = _normalized(CLI_JSON_SPEC_PATH)
    pyproject = _read(REPO_ROOT / "pyproject.toml")
    ci = _read(REPO_ROOT / ".github/workflows/ci.yml")

    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert hasattr(sql_api, "emit_postgres_sql")
    assert not hasattr(sql_api, "emit_mysql_sql")

    assert "JSON schema version 1 remains exclusively single-file" in cli_json
    assert "write exactly one complete JSON document to stdout" in cli_json
    assert 'version = "0.1.0"' in pyproject
    assert 'requires-python = ">=3.12"' in pyproject

    for command in (
        "uv run python scripts/validate.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert command in ci


def test_phase30_validation_stack_is_documented() -> None:
    plan = _normalized(PLAN_PATH)
    for command in REQUIRED_VALIDATION_COMMANDS:
        assert command in plan


def test_phase30_golden_fixture_inventory_remains_unchanged() -> None:
    check_goldens = _check_goldens_module()

    assert len(check_goldens.SQL_FIXTURES) == 32
    assert len(check_goldens.JSON_FIXTURES) == 5
    assert len(check_goldens.CLASSIFIED_FIXTURES) == 37
    assert check_goldens.audit(REPO_ROOT) == ()


def test_phase30_locked_boundary_surface_hashes_are_unchanged() -> None:
    for label, (
        relative_path,
        expected_count,
        expected_hash,
    ) in LOCKED_BOUNDARY_SURFACES.items():
        paths = _paths(REPO_ROOT / relative_path)
        assert len(paths) == expected_count, label
        assert _digest(paths) == expected_hash, label


def _check_goldens_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_goldens", CHECK_GOLDENS_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _paths(path: Path) -> tuple[Path, ...]:
    if path.is_file():
        return (path,)
    return tuple(
        sorted(
            child
            for child in path.rglob("*")
            if (
                child.is_file()
                and "__pycache__" not in child.parts
                and child.suffix != ".pyc"
            )
        )
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
