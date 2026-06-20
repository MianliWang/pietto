from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-29-v02-stabilization-boundary.md"
SPEC_PATH = REPO_ROOT / "docs/spec/v02-exit-criteria-validation-strategy-v1.md"
STABILIZATION_SPEC_PATH = REPO_ROOT / "docs/spec/v02-stabilization-boundary-v1.md"
REGISTER_SPEC_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
AGGREGATE_FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
TYPE_GAP_SPEC_PATH = REPO_ROOT / "docs/spec/v02-core-type-system-gap-matrix-v1.md"
CLI_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/cli-json-v1.md"
DIAGNOSTICS_SPEC_PATH = REPO_ROOT / "docs/spec/diagnostics.md"

SQL_API_PATH = REPO_ROOT / "src/pietto/sql/__init__.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
CI_PATH = REPO_ROOT / ".github/workflows/ci.yml"
VALIDATE_PATH = REPO_ROOT / "scripts/validate.py"
CHECK_GENERATED_PATH = REPO_ROOT / "scripts/check_generated.py"
CHECK_GOLDENS_PATH = REPO_ROOT / "scripts/check_goldens.py"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"

REQUIRED_EXIT_ROWS = (
    "Stable single-file language surface",
    "Aggregate surface freeze",
    "Deferred feature register",
    "Core type-system gap matrix",
    "Phase 30 prerequisites",
    "Phase 31 prerequisites",
    "Phase 32 completion audit",
    "CLI stability",
    "JSON v1 stability",
    "Public API stability",
    "Diagnostics stability",
    "SQL golden stability",
    "Generated-file stability",
    "Package smoke expectations",
    "Docs, examples, and README readiness",
    "CI expectations",
)

REQUIRED_VALIDATION_COMMANDS = (
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


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice5_plan_status_links_and_validation_are_locked() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 29 Slice 5 is complete as v0.2 exit criteria and validation "
        "strategy contract and static audit work only",
        "docs/spec/v02-exit-criteria-validation-strategy-v1.md",
        "tests/test_phase29_v02_exit_criteria_validation_strategy.py",
        "Status: complete as v0.2 exit criteria and validation strategy "
        "contract and static audit work only",
        "without declaring v0.2 complete",
        "Define v0.2 validation strategy",
    ):
        assert required in plan

    for command in REQUIRED_VALIDATION_COMMANDS:
        assert command in plan

    assert "### Slice 6: Completion Audit And Status Lock Status: planned only" in plan


def test_exit_criteria_spec_status_and_non_authorization_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    assert SPEC_PATH.is_file()
    for required in (
        "Phase 29 Slice 5 is complete as a v0.2 exit criteria and validation "
        "strategy contract and static audit slice only",
        "It does not declare v0.2 complete",
        "Phase 30 Core Type System Stabilization I",
        "Phase 31 Core Type System Stabilization II And Dialect Matrix Hardening",
        "Phase 32 v0.2 Single-file Stable Completion Audit",
        "remain required before the v0.2 stable completion status can be locked",
        "Phase 32 remains the actual v0.2 single-file stable completion audit",
        "does not authorize source implementation changes",
        "grammar changes",
        "generated ANTLR changes",
        "public API changes",
        "CLI behavior changes",
        "JSON behavior or schema changes",
        "IR behavior changes",
        "SQL lowering changes",
        "semantic behavior changes",
        "aggregate behavior changes",
        "diagnostic behavior changes",
        "type-system behavior changes",
        "fixture or golden changes",
        "validation script changes",
        "CI workflow changes",
        "package metadata changes",
        "package version changes",
        "release tags",
        "release artifacts",
        "publication",
        "package upload",
        "signing",
        "attestation",
        "JSON v2",
        "public MySQL API expansion",
    ):
        assert required in spec


def test_exit_criteria_matrix_covers_required_surfaces() -> None:
    spec = _normalized(SPEC_PATH)

    assert (
        "| Area | v0.2 exit criterion | Validation evidence | Explicit non-goals |"
    ) in spec
    for row in REQUIRED_EXIT_ROWS:
        assert f"| {row} |" in spec

    for required in (
        "The Phase 19 through Phase 28 aggregate and result-scope surface "
        "remains frozen except for bug fixes",
        "Every deferred feature remains outside v0.2",
        "Phase 30 and Phase 31 must resolve or explicitly carry forward the "
        "core type-system gaps",
        "Phase 32 performs the v0.2 candidate release contract",
        "JSON schema version 1 remains the single-file machine-readable contract",
        "The public SQL API remains PostgreSQL-only through `emit_postgres_sql`",
        "Diagnostic codes keep canonical `PIE-*` format",
        "Generated ANTLR files remain byte-for-byte reproducible",
        "Package smoke builds sdist and wheel in a temporary directory",
        "README, examples, specs, plans, and golden/documentation references",
        "CI continues to orchestrate the accepted local commands on Python 3.12 "
        "and Python 3.13",
    ):
        assert required in spec


def test_validation_stack_is_exact_and_phase32_ci_handoff_is_locked() -> None:
    spec = _normalized(SPEC_PATH)
    plan = _normalized(PLAN_PATH)

    for command in REQUIRED_VALIDATION_COMMANDS:
        assert command in spec
        assert command in plan

    for required in (
        "A later Phase 32 v0.2 completion audit must run the full local "
        "validation stack",
        "verify a successful exact-head CI run for the candidate commit",
        "before locking v0.2 completion status",
    ):
        assert required in spec


def test_current_release_boundary_evidence_is_grounded_in_repo_contracts() -> None:
    spec = _normalized(SPEC_PATH)
    stabilization = _normalized(STABILIZATION_SPEC_PATH)
    register = _normalized(REGISTER_SPEC_PATH)
    aggregate_freeze = _normalized(AGGREGATE_FREEZE_SPEC_PATH)
    type_gap = _normalized(TYPE_GAP_SPEC_PATH)
    cli_json = _normalized(CLI_JSON_SPEC_PATH)
    diagnostics = _normalized(DIAGNOSTICS_SPEC_PATH)
    sql_api = _read(SQL_API_PATH)
    pyproject = _read(PYPROJECT_PATH)
    ci = _read(CI_PATH)

    for required in (
        "v0.2 is defined as a stable single-file typed SQL authoring compiler boundary",
        "JSON v1 remains the single-file machine-readable contract",
    ):
        assert required in stabilization

    assert "It does not authorize implementation" in register
    assert "aggregate surface is frozen except for bug fixes" in aggregate_freeze
    assert "Phase 30 Core Type System Stabilization I" in type_gap

    for required in (
        "JSON schema version 1 remains exclusively single-file",
        "adding top-level or nested fields must be treated conservatively and "
        "must not happen silently",
    ):
        assert required in cli_json
    assert (
        "JSON schema version 1 remains the single-file machine-readable contract"
        in (spec)
    )

    assert "PIE-<PHASE><NUMBER>" in diagnostics
    assert "Diagnostic severity is stored separately" in diagnostics
    assert "Diagnostic codes keep canonical `PIE-*` format" in spec

    assert '"emit_postgres_sql",' in sql_api
    assert "emit_mysql_sql" not in sql_api
    assert "The public SQL API remains PostgreSQL-only" in spec

    assert 'version = "0.1.0"' in pyproject
    assert 'requires-python = ">=3.12"' in pyproject
    assert "package version changes" in spec

    for command in (
        "uv run python scripts/validate.py",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    ):
        assert command in ci
        assert command in spec


def test_validation_script_roles_are_grounded_without_script_changes() -> None:
    spec = _normalized(SPEC_PATH)
    validate = _read(VALIDATE_PATH)
    check_generated = _read(CHECK_GENERATED_PATH)
    check_goldens = _read(CHECK_GOLDENS_PATH)
    package_smoke = _read(PACKAGE_SMOKE_PATH)

    for required in (
        '("lockfile", ("uv", "lock", "--check"))',
        '("format", ("uv", "run", "ruff", "format", "--check", "."))',
        '("lint", ("uv", "run", "ruff", "check", "."))',
        '"production typing"',
        '"test typing"',
        '("tests", ("uv", "run", "pytest"))',
    ):
        assert required in validate

    for required in (
        "ANTLR jar SHA-256",
        "regenerate:",
        "verified {len(tracked_inventory)} tracked files byte-for-byte",
    ):
        assert required in check_generated

    for required in (
        "SQL_FIXTURES",
        "JSON_FIXTURES",
        "CLASSIFIED_FIXTURES",
        "fixture has no reviewed Pietto input",
    ):
        assert required in check_goldens

    for required in (
        "build sdist and wheel",
        "installed CLI version",
        "installed PostgreSQL text output differs from reviewed golden bytes",
        "installed MySQL JSON v1 output differs structurally from reviewed golden",
    ):
        assert required in package_smoke

    assert "validation script changes" in spec
    assert (
        "No package metadata, version, dependency, build backend, release "
        "artifact, upload, signing, publication, or attestation change"
    ) in spec


def test_explicit_v02_non_goals_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "No grammar, generated ANTLR, AST, parser, project, or multi-file change",
        "No aggregate expansion, new diagnostics, fixture/golden change, SQL "
        "lowering change, or aggregate behavior change",
        "No implementation of registered deferred features",
        "No Slice 5 type model, semantic, diagnostic, or SQL behavior change",
        "No Phase 30 implementation in Slice 5",
        "No Phase 31 implementation in Slice 5",
        "Slice 5 does not declare v0.2 complete",
        "No CLI command, option, help, exit-code, output, or behavior change",
        "No JSON v1 change and no JSON v2 implementation",
        "No public MySQL API expansion and no generic public SQL dispatcher",
        "No diagnostic code, severity, wording, presentation, or behavior change",
        "No fixture or golden inventory/content change in Slice 5",
        "No grammar or generated file change in Slice 5",
        "No CI workflow change in Slice 5",
        "package release, release tag, release artifact, publication, package "
        "upload, signing, or attestation",
        "schema introspection, database pull, connector execution, SQL execution",
        "LSP, playground, web UI, Arrow, or dataframe integration",
    ):
        assert required in spec


def test_forbidden_scope_is_not_authorized() -> None:
    plan_and_spec = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for forbidden in (
        "v0.2 is complete",
        "declares v0.2 complete",
        "Slice 5 implements",
        "Slice 5 changes CLI behavior",
        "Slice 5 changes JSON",
        "Slice 5 changes public API",
        "Slice 5 changes SQL lowering",
        "Slice 5 changes semantic behavior",
        "Slice 5 changes aggregate behavior",
        "Slice 5 changes diagnostic behavior",
        "Slice 5 changes type-system behavior",
        "Slice 5 bumps",
        'version = "0.2.0"',
        "release tag is created",
        "publication is authorized",
        "package upload is authorized",
        "signing is authorized",
        "attestation is authorized",
        "JSON v2 is implemented",
        "public `emit_mysql_sql`",
    ):
        assert forbidden not in plan_and_spec
