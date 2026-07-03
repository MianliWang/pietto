from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE41_PLAN_PATH = REPO_ROOT / "docs/plan/phase-41-decimal-precision-scale-mvp.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
DECIMAL_CONTRACT_PATH = REPO_ROOT / "docs/spec/decimal-precision-scale-contract-v1.md"
READINESS_SPEC_PATH = (
    REPO_ROOT / "docs/spec/decimal-precision-scale-metadata-carrier-readiness-v1.md"
)
CARRIER_DECISION_SPEC_PATH = (
    REPO_ROOT / "docs/spec/decimal-precision-scale-carrier-mvp-decision-v1.md"
)
PHASE36_MATRIX_PATH = REPO_ROOT / "docs/spec/phase36-core-type-resolution-matrix-v1.md"
PHASE38_MATRIX_PATH = (
    REPO_ROOT / "docs/spec/phase38-type-capability-matrix-contract-v1.md"
)
SCALAR_MATRIX_PATH = REPO_ROOT / "docs/spec/expanded-scalar-operator-matrix-v1.md"
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
PHASE35_VALIDATION_TEST_PATH = (
    REPO_ROOT / "tests/test_phase35_validation_delivery_workflow_polish.py"
)


def test_slice7_plan_status_records_completed_slices_without_completion_claim() -> None:
    plan = _normalized(PHASE41_PLAN_PATH)

    for required in (
        "Phase 41 Slice 7 is Docs, Deferred Register, And Package Smoke Readiness",
        "Slices 2 through 6 are complete",
        "Slice 7 is docs/static-audit/readiness work only",
        "Slice 8 remains the completion audit/status lock",
        "Phase 41 is not complete in Slice 7",
        "Slice 2 implemented Decimal precision-scale semantic validation and `PIE-S2004`",
        "Slice 3 implemented the private internal `DecimalPrecisionScale` carrier",
        "`SemanticModel.decimal_precision_scales`",
        "`decimal_precision_scale_for`",
        "safe alias-chain internal fact propagation",
        "Slice 4 proved IR compatibility",
        "Slice 5 proved aggregate/numeric boundaries remain stable",
        "Slice 6 proved CLI JSON v1, Project JSON v2, explain text/JSON, and Semantic Metadata Artifact v1 compatibility",
    ):
        assert required in plan, required

    for forbidden in (
        "Phase 41 is complete in Slice 7",
        "Slice 7 completes Phase 41",
        "Slice 7 changes production compiler behavior",
        "Slice 7 updates `README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md`",
    ):
        assert forbidden not in plan, forbidden


def test_deferred_register_splits_phase41_internal_mvp_from_remaining_work() -> None:
    register = _normalized(DEFERRED_REGISTER_PATH)
    row = next(
        line
        for line in _read(DEFERRED_REGISTER_PATH).splitlines()
        if line.startswith("| Decimal precision/scale |")
    )

    for required in (
        "Phase 41 implemented `Decimal(p,s)` semantic validation",
        "`PIE-S2004`",
        "private internal `DecimalPrecisionScale` type-expression carrier",
        "`SemanticModel.decimal_precision_scales`",
        "`decimal_precision_scale_for(type_expr)`",
        "safe alias-chain internal fact propagation",
        "Phase 30 Decimal precision/scale contract and Phase 31 Decimal boundary tests are superseded for the internal MVP",
        "implemented by Phase 41 for semantic validation and private carrier only",
    ):
        assert required in register, required

    for required in (
        "Phase 42 numeric/literal work",
        "future aggregate/type propagation phase",
        "native SQL type/DDL/dialect contract",
        "native DB metadata prerequisite",
        "schema-versioned public output contract",
        "Artifact v2/display contract",
        "cast syntax/design prerequisite",
        "future type-argument policy phase",
    ):
        assert required in row, required

    assert "Current type facts have no precision/scale carrier" not in row


def test_historical_decimal_specs_have_phase41_supersession_notes() -> None:
    combined = " ".join(
        _normalized(path)
        for path in (
            DECIMAL_CONTRACT_PATH,
            READINESS_SPEC_PATH,
            CARRIER_DECISION_SPEC_PATH,
            PHASE36_MATRIX_PATH,
        )
    )

    for required in (
        "Phase 41 Supersession Note",
        "Phase 41 Update",
        "`Decimal(p,s)` semantic validation is implemented",
        "`DecimalPrecisionScale` is implemented as a private semantic-model fact",
        "`SemanticModel.decimal_precision_scales` stores facts keyed by `TypeExpr`",
        "`decimal_precision_scale_for(type_expr)` provides internal lookup",
        "safe alias-chain internal fact propagation",
        "`Decimal()` remains compatible because the current AST cannot distinguish it from no-argument `Decimal`",
        "non-Decimal type arguments remain the current compatibility surface",
    ):
        assert required in combined, required


def test_phase38_and_scalar_matrices_reflect_internal_carrier_only() -> None:
    combined = f"{_normalized(PHASE38_MATRIX_PATH)} {_normalized(SCALAR_MATRIX_PATH)}"

    for required in (
        "internal precision-scale carrier implemented by Phase 41",
        "`Decimal(12, 2)` now validates as a logical Decimal type form",
        "internal `DecimalPrecisionScale` facts",
        "Phase 41 Decimal precision-scale validation and private `DecimalPrecisionScale` facts do not change this arithmetic matrix",
        "Decimal literal typing remains owned by Phase 42 numeric/literal work",
        "Int/Float/Decimal promotion matrix and Float/Decimal mixing remain owned by Phase 42 numeric promotion decisions",
        "Decimal multiplication/division remains owned by Phase 42 or later numeric operator matrix work",
        "aggregate precision propagation remains owned by a future aggregate/type propagation phase",
        "SQL `DECIMAL(p,s)` / `NUMERIC(p,s)` output remains owned by native SQL type/DDL/dialect contracts",
        "public JSON precision-scale fields remain owned by schema-versioned public output contracts",
        "metadata/explain precision-scale display remains owned by Artifact v2/display contracts",
    ):
        assert required in combined, required


def test_package_smoke_readiness_is_documented_without_script_or_package_changes() -> (
    None
):
    plan = _normalized(PHASE41_PLAN_PATH)
    package_smoke = _read(PACKAGE_SMOKE_PATH)
    phase35_validation = _read(PHASE35_VALIDATION_TEST_PATH)

    for required in (
        "Package smoke readiness remains covered by the standard validation stack and `scripts/package_smoke.py`",
        "Slice 7 changes no script, package metadata, version, workflow, release, upload, signing, or attestation behavior",
        "Sandbox DNS/PyPI failures remain evidence-only infrastructure notes",
    ):
        assert required in plan, required

    for required in (
        "Build, inspect, install, and smoke test Pietto release artifacts.",
        "installed CLI version",
        "installed CLI help",
        "installed CLI check",
        "installed CLI project check JSON v2",
        "installed CLI explain JSON",
        "installed PostgreSQL text",
        "installed MySQL JSON v1",
        "packaging and installed CLI smoke passed",
    ):
        assert required in package_smoke, required

    for required in (
        "Sandbox DNS/PyPI failures in `scripts/package_smoke.py` are ",
        "environment/network failures",
        "record the raw failure and rerun only `scripts/package_smoke.py` with ",
        "network access if available",
        "Do not change repository files to fix sandbox cache, DNS, or PyPI ",
        "environment failures",
    ):
        assert required in phase35_validation, required

    lowered = package_smoke.lower()
    for forbidden in (
        "twine",
        "publish",
        "upload",
        "sigstore",
        "attestation",
        "trusted publishing",
    ):
        assert forbidden not in lowered, forbidden
