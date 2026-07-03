from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-42-aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock.md"
)
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock-v1.md"
)
REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE42_TEST_PATHS = (
    "tests/test_phase42_aggregate_typeclasses_decimal_scope_lock.py",
    "tests/test_phase42_aggregate_typeclasses_matrix_lock.py",
    "tests/test_phase42_decimal_int_exact_arithmetic.py",
    "tests/test_phase42_decimal_precision_fusion_readiness.py",
    "tests/test_phase42_decimal_expression_precision_fact_carrier.py",
    "tests/test_phase42_literal_only_aggregate_candidate_readiness.py",
    "tests/test_phase42_completion_audit.py",
)

POSITIVE_RELEASE_CLAIMS = (
    "tag created",
    "release created",
    "package release occurred",
    "published package",
    "uploaded package",
    "signing completed",
    "attestation completed",
    "release operation occurred",
)


def _plan() -> str:
    return _normalized(PLAN_PATH)


def _phase42_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH, REGISTER_PATH))


def test_phase42_artifact_inventory_is_complete_through_slice7() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert REGISTER_PATH.is_file()
    for relative_path in PHASE42_TEST_PATHS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    plan = _plan()
    for required in (
        "| 1 | Aggregate Function Typeclasses And Decimal Arithmetic Scope Lock |",
        "| 2 | Aggregate Typeclass Vocabulary Or Tests-First Matrix |",
        "| 3 | Exact Decimal/Int Arithmetic Candidate |",
        "| 4 | Decimal Precision Fusion Readiness Lock |",
        "| 5 | Private Decimal Expression Precision Fact Carrier Scaffold |",
        "| 6 | Literal-only Aggregate Argument Candidate |",
        "| 7 | Completion Audit And Status Lock |",
        "Phase 42 has reached its completion-audit/status-lock slice",
    ):
        assert required in plan, required


def test_phase42_slice7_status_lock_is_no_behavior_work() -> None:
    plan = _plan()

    for required in (
        "Phase 42 Slice 7 is Completion Audit And Status Lock",
        "docs/plan status-lock and tests/static-audit completion work only",
        "It adds no compiler behavior",
        "does not start a later phase",
        "does not claim Gate 3 natural CI success before Gate 3",
        "Final trusted completion requires the later Gate 3 commit, push, and natural CI `headSha` verification",
        "updates this Phase 42 plan/status artifact and adds `tests/test_phase42_completion_audit.py`",
        "Package version remains `0.1.0`",
        "No tag/release/publish/upload/signing or attestation is authorized by Slice 7",
    ):
        assert required in plan, required

    for forbidden in (
        "Gate 3 natural CI succeeded",
        "Gate 3 natural CI has succeeded",
        "natural CI success is complete",
        "Phase 43 has started",
    ):
        assert forbidden not in plan, forbidden


def test_slice1_through_slice6_outcomes_are_recorded() -> None:
    plan = _plan()

    for required in (
        "Phase 42 Slice 1 Scope Lock / Static Audit is complete",
        "aggregate validation, numeric expression typing, Decimal carrier",
        "Phase 42 Slice 2 Aggregate Typeclass Matrix / Readiness Lock is complete",
        "aggregate typeclass matrix and current accepted/fail-closed aggregate behavior",
        "Phase 42 Slice 3 Exact Decimal/Int Arithmetic MVP is complete",
        "only `Decimal + Int`, `Int + Decimal`, `Decimal - Int`, and `Int - Decimal`",
        "without precision/scale propagation",
        "Phase 42 Slice 4 Decimal Precision Fusion Readiness Lock is complete",
        "Decimal precision fusion remains deferred",
        "Phase 42 Slice 5 Private Decimal Expression Precision Fact Carrier Scaffold is complete",
        "private direct-field expression precision facts",
        "no computed expression fusion, aggregate precision propagation, or public precision/scale output",
        "Phase 42 Slice 6 Literal-only Aggregate Candidate Readiness Lock is complete",
        "Literal-only aggregate behavior remains unimplemented",
        "semantic, IR, PostgreSQL, and private MySQL guard changes together",
    ):
        assert required in plan, required


def test_phase42_forbidden_behavior_and_public_surfaces_remain_locked() -> None:
    docs = _phase42_docs()

    for required in (
        "no literal-only aggregate behavior",
        "no Decimal precision fusion",
        "no aggregate typeclass behavior",
        "no Decimal literal or cast syntax",
        "no Decimal multiplication/division/modulo or Float/Decimal widening",
        "no aggregate precision propagation",
        "no SQL, IR, CLI JSON, Project JSON, explain, or Semantic Metadata Artifact public-surface change",
        "no production source, grammar/generated, fixture/golden/example, package/workflow/CI/release, diagnostic, warning/lint, runtime/database, project/multi-file, public MySQL API, or relationship/JOIN behavior change",
        "literal-only aggregate behavior unfreezes only when a later implementation slice is explicitly approved",
        "Decimal fusion, Decimal multiplication, literal-only aggregate arguments, and Decimal literal syntax each require separate approval",
    ):
        assert required in docs, required

    for forbidden in (
        "literal-only aggregates are implemented",
        "Decimal precision fusion is implemented",
        "aggregate typeclasses are implemented",
        "Decimal literals are implemented",
        "cast syntax is implemented",
        "SQL precision output is implemented",
    ):
        assert forbidden not in docs, forbidden


def test_package_version_and_release_boundary_remain_locked() -> None:
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    lowered_docs = _phase42_docs().lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered_docs, forbidden
