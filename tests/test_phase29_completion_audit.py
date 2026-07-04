from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType

import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-29-v02-stabilization-boundary.md"
STABILIZATION_SPEC_PATH = REPO_ROOT / "docs/spec/v02-stabilization-boundary-v1.md"
REGISTER_SPEC_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
AGGREGATE_FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
TYPE_GAP_SPEC_PATH = REPO_ROOT / "docs/spec/v02-core-type-system-gap-matrix-v1.md"
EXIT_CRITERIA_SPEC_PATH = (
    REPO_ROOT / "docs/spec/v02-exit-criteria-validation-strategy-v1.md"
)
CLI_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/cli-json-v1.md"
DIAGNOSTICS_SPEC_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"

PHASE29_ARTIFACTS = (
    "docs/plan/phase-29-v02-stabilization-boundary.md",
    "docs/spec/v02-stabilization-boundary-v1.md",
    "docs/spec/v02-deferred-feature-register-v1.md",
    "docs/spec/v02-aggregate-surface-freeze-v1.md",
    "docs/spec/v02-core-type-system-gap-matrix-v1.md",
    "docs/spec/v02-exit-criteria-validation-strategy-v1.md",
    "tests/test_phase29_v02_stabilization_candidate_decision.py",
    "tests/test_phase29_v02_deferred_feature_register.py",
    "tests/test_phase29_v02_aggregate_surface_freeze.py",
    "tests/test_phase29_v02_core_type_system_gap_matrix.py",
    "tests/test_phase29_v02_exit_criteria_validation_strategy.py",
    "tests/test_phase29_completion_audit.py",
)

REQUIRED_VALIDATION_COMMANDS = (
    "uv run pytest tests/test_phase29_completion_audit.py",
    "uv run pytest tests/test_phase29_v02_exit_criteria_validation_strategy.py",
    "uv run pytest tests/test_phase29_v02_core_type_system_gap_matrix.py",
    "uv run pytest tests/test_phase29_v02_aggregate_surface_freeze.py",
    "uv run pytest tests/test_phase29_v02_deferred_feature_register.py",
    "uv run pytest tests/test_phase29_v02_stabilization_candidate_decision.py",
    "uv run python scripts/check_generated.py",
    "uv run python scripts/check_goldens.py",
    "uv run python scripts/package_smoke.py",
    "uv run python scripts/validate.py",
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
        21,
        "eb04af25b547ebc30aa700a8956be1880eab8426dd80e99278b2c0a668603b91",
    ),
    "ir": (
        "src/pietto/ir",
        5,
        "526e4bf82d1b8aa9d8c563021c7efc3092d9479eedb0ea7ca36a0cce0dd18c01",
    ),
    "sql": (
        "src/pietto/sql",
        10,
        "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b",
    ),
    "cli": (
        "src/pietto/cli.py",
        1,
        "63e99f989500f83686963fba853fed27d76bc5e0c0ac2e58827fb336b2bb044a",
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
        "ce4141c38f03e5975d32d75307e42a89a9d9c9cc7bdd36d7f7fa9b6960676b2c",
    ),
    "pyproject": (
        "pyproject.toml",
        1,
        "cf5894a9cb7ef0399126a7d424da4e3958fc92d8e6bed295939a6e6bac469099",
    ),
    "uv_lock": (
        "uv.lock",
        1,
        "b48bb27656ff3344a95ba92347f45173904801cd8bdccfd2b55106549c445ac0",
    ),
    "github": (
        ".github",
        1,
        "129f96212b5025e66254b2485195977770cf7765bd8977215c6dfaefd9e6e5ae",
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
        "140af85301e560bcf13481c589e99c039e734a47d0ebc9d2787b7062d948031d",
    ),
    "pietto_v09": (
        "docs/spec/pietto-v0.9.md",
        1,
        "8c5f7ae8e5f6bbcbe7c004e681ba4bf8e417efb62240137f83ccd6d5a8472b39",
    ),
    "phase29_plan": (
        "docs/plan/phase-29-v02-stabilization-boundary.md",
        1,
        "b5625d16c7e995c9f023953edc56caa61c4276d03d8f0602ff4988589abc695e",
    ),
    "phase29_boundary_spec": (
        "docs/spec/v02-stabilization-boundary-v1.md",
        1,
        "66826da2df9a6a8b37bf0ba77972b2ad1abae337bc677b4000fbff77e60701de",
    ),
    "phase29_deferred_register": (
        "docs/spec/v02-deferred-feature-register-v1.md",
        1,
        "b884a09a1e0a5fc8c7f68479a6dfe70ed4da8717766310bcd42849fce5e760d8",
    ),
    "phase29_aggregate_freeze": (
        "docs/spec/v02-aggregate-surface-freeze-v1.md",
        1,
        "cebb1fb8360c1c72a1ec6ba59a75962c04a25cecd8a874bf038fe336021b8ccc",
    ),
    "phase29_type_gap_matrix": (
        "docs/spec/v02-core-type-system-gap-matrix-v1.md",
        1,
        "c417a76567e1c4f007768eb064cc586318f42283b65657f72b4bf15fc7f676be",
    ),
    "phase29_exit_criteria": (
        "docs/spec/v02-exit-criteria-validation-strategy-v1.md",
        1,
        "76aea935b950042af804eb94f0c25d10ea68ee31d065efd420610150d6f5b5e1",
    ),
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_phase29_status_and_artifact_inventory_are_complete() -> None:
    for relative_path in PHASE29_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file()

    plan = _normalized(PLAN_PATH)
    for required in (
        "Phase 29 Slice 1 is complete as candidate decision, v0.2 boundary "
        "contract, and static audit work only",
        "Phase 29 Slice 2 is complete as deferred-feature register contract "
        "and static audit work only",
        "Phase 29 Slice 3 is complete as aggregate-surface freeze contract "
        "and static audit work only",
        "Phase 29 Slice 4 is complete as core type-system gap matrix contract "
        "and static audit work only",
        "Phase 29 Slice 5 is complete as v0.2 exit criteria and validation "
        "strategy contract and static audit work only",
        "Phase 29 Slice 6 is complete as completion audit and status lock work only",
        "Phase 29 v0.2 Stabilization Boundary is complete as "
        "docs/spec/static-audit and status work only",
        "Status: complete as completion audit and status lock work only",
        "Complete Phase 29 v0.2 stabilization audit",
        "Historical Slice 5 checkpoint retained for static-audit compatibility",
        "### Slice 6: Completion Audit And Status Lock Status: planned only",
    ):
        assert required in plan


def test_phase29_status_docs_lock_v02_completion_after_phase31_slice8() -> None:
    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 29 v0.2 Stabilization Boundary",
            "complete as docs/spec/static-audit",
            "stable single-file typed SQL authoring compiler",
            "deferred feature register",
            "aggregate surface",
            "core type-system gap matrix",
            "v0.2 exit criteria",
            "completion audit/status lock",
            "Phase 30 Core Type System Stabilization I is complete",
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
            "package version",
            "release",
            "JSON v2",
            "public MySQL API",
            "relationship/JOIN",
        ):
            assert required in status_doc
        assert "Phase 32 remains post-v0.2 and has not started" not in status_doc
        for forbidden in (
            "Pietto 0.2.0 released",
            "v0.2 package published",
            "v0.2 Git tag created",
            "Phase 30 implementation",
            "Phase 31 implementation is complete",
            "Phase 31 implementation has started",
            "Phase 32 is complete",
            "Phase 29 implements JSON v2",
            "Phase 29 changes public `emit_mysql_sql`",
            "public `emit_mysql_sql`",
            "Phase 29 implements relationship/JOIN",
        ):
            assert forbidden not in status_doc


def test_phase29_spec_suite_preserves_contract_boundaries() -> None:
    stabilization = _normalized(STABILIZATION_SPEC_PATH)
    register = _normalized(REGISTER_SPEC_PATH)
    aggregate_freeze = _normalized(AGGREGATE_FREEZE_SPEC_PATH)
    type_gap = _normalized(TYPE_GAP_SPEC_PATH)
    exit_criteria = _normalized(EXIT_CRITERIA_SPEC_PATH)

    for required in (
        "v0.2 is defined as a stable single-file typed SQL authoring compiler boundary",
        "JSON v1 remains the single-file machine-readable contract",
        "The public Python SQL API remains PostgreSQL-only",
        "The MySQL emitter remains private to explicit CLI dispatch",
    ):
        assert required in stabilization

    for required in (
        "It does not authorize implementation",
        "| Feature | Why deferred | Blocking prerequisites | Unfreeze condition "
        "| Target | Allowed before v0.2 | Explicit non-goals |",
        "Aggregate expansion",
        "Runtime/database execution",
        "Arrow/dataframe integration",
    ):
        assert required in register

    for required in (
        "For v0.2, the Phase 19 through Phase 28 aggregate surface is frozen "
        "except for bug fixes and audit-only clarifications",
        "current bounded `count_distinct(...)` Text transform subset",
        "chains composed only of `lower(...)` and `trim(...)` over exactly one "
        "Text field leaf",
        "current direct-field Decimal aggregate surface",
        "Rejected v0.2 Aggregate Expansions",
    ):
        assert required in aggregate_freeze

    for required in (
        "Phase 29 Slice 4 is complete as a core type-system gap matrix "
        "contract and static audit slice only",
        "Canonical scalar type registry",
        "Nullability propagation",
        "Predicate semantics / SQL three-valued logic boundary",
        "Decimal precision/scale",
    ):
        assert required in type_gap

    for required in (
        "It does not declare v0.2 complete",
        "Phase 30 Core Type System Stabilization I",
        "Phase 31 Core Type System Stabilization II And Dialect Matrix Hardening",
        "Phase 32 v0.2 Single-file Stable Completion Audit",
        "remain required before the v0.2 stable completion status can be locked",
        "Phase 32 remains the actual v0.2 single-file stable completion audit",
        "package version changes",
        "release tags",
        "publication",
        "JSON v2",
        "public MySQL API expansion",
    ):
        assert required in exit_criteria


def test_phase29_validation_stack_and_phase30_handoff_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    exit_criteria = _normalized(EXIT_CRITERIA_SPEC_PATH)

    for command in REQUIRED_VALIDATION_COMMANDS:
        assert command in plan
        assert command in exit_criteria or command == (
            "uv run pytest tests/test_phase29_completion_audit.py"
        )

    for required in (
        "Phase 30 Core Type System Stabilization I is the next mainline",
        "Phase 30, Phase 31, and Phase 32 remain required before v0.2 stable "
        "completion",
        "Phase 29 prepares this mainline but does not implement it",
        "Candidate Decision And Type-System Contract",
        "Canonical Scalar Type Registry",
        "Nullability Propagation Contract",
        "Bool And Predicate Semantics",
        "Date / Timestamp Formalization",
        "Decimal Precision / Scale Contract",
        "Operator And Comparison Matrix",
        "Completion Audit",
    ):
        assert required in plan

    for forbidden in (
        "Phase 30 is complete",
        "Phase 30 implementation is authorized",
        "v0.2 is complete",
    ):
        assert forbidden not in plan


def test_phase29_public_api_cli_json_release_and_package_boundaries_are_locked() -> (
    None
):
    cli_json = _normalized(CLI_JSON_SPEC_PATH)
    diagnostics = _normalized(DIAGNOSTICS_SPEC_PATH)
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
    assert "adding top-level or nested fields must be treated conservatively" in (
        cli_json
    )
    assert "PIE-<PHASE><NUMBER>" in diagnostics
    assert "Diagnostic severity is stored separately" in diagnostics
    assert 'version = "0.1.0"' in pyproject
    assert 'requires-python = ">=3.12"' in pyproject

    for command in (
        "uv run python scripts/validate.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert command in ci


def test_phase29_golden_fixture_inventory_remains_unchanged() -> None:
    check_goldens = _check_goldens_module()

    assert len(check_goldens.SQL_FIXTURES) == 32
    assert len(check_goldens.JSON_FIXTURES) == 5
    assert len(check_goldens.CLASSIFIED_FIXTURES) == 37
    assert check_goldens.audit(REPO_ROOT) == ()


def test_phase29_locked_boundary_surface_hashes_are_unchanged() -> None:
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
