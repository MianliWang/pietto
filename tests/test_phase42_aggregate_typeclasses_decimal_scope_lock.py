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


def test_phase42_slice1_plan_and_handoff_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 42 Slice 1 is Aggregate Function Typeclasses And Decimal Arithmetic Scope Lock",
        "docs/spec/deferred-register/static-audit work only and implements no behavior change",
        "baseline HEAD: `b6e7651f9bec69caa3d953602dfdb74cc292950e`",
        "baseline branch: `main`",
        "baseline commit: `Complete Phase 41 decimal precision-scale MVP audit`",
        "latest completed phase: Phase 41 Decimal Precision-Scale MVP",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation is authorized by Slice 1",
        "Production semantic work, if approved later, begins in Slice 2 or later",
    ):
        assert required in plan, required

    for forbidden in (
        "Slice 1 implements aggregate typeclasses",
        "Slice 1 implements Decimal arithmetic",
        "Slice 1 implements Decimal literals",
    ):
        assert forbidden not in plan, forbidden


def test_current_maps_and_findings_are_documented() -> None:
    combined = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for required in (
        "`AGGREGATE_NAMES` contains `count`, `sum`, and `avg`",
        "`SEMANTIC_AGGREGATE_NAMES` adds `count_distinct`, `min`, and `max`",
        "`count()` | Accepted; result is `Int NON_NULL`; SQL is `COUNT(*)`",
        "`count(expression)` | Accepted only for approved field-bearing shapes",
        "`sum(expression)` / `avg(expression)` | Accepted only for the current field-bearing numeric expression subset",
        "`count_distinct(field)` | Accepted for `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`",
        "`min(field)` / `max(field)` | Accepted for direct or supported qualified `Int`, `Float`, `Decimal`, `Date`, and `Timestamp` fields",
        "`PIE-S2308`",
        "`PIE-S2315`",
        "dotted numeric literals type as Python `float` and type as `Float`",
        "`Decimal + Decimal` and `Decimal - Decimal` are accepted",
        "`Decimal + Int`, `Int + Decimal`, `Decimal - Int`, and `Int - Decimal`",
        "Decimal multiplication, mixed `Decimal`/`Float`, and mixed `Float`/`Decimal`",
        "`DecimalPrecisionScale`",
        "`SemanticModel.decimal_precision_scales`",
        "`SemanticModel.decimal_precision_scale_for(type_expr)`",
        "private expression-level Decimal precision facts",
        "computed expression precision facts",
        "`LiteralExpr` stores only a parsed Python value, not raw token text",
        "No scalar constant folding",
        "must preserve `SUM(constant)` instead of rewriting to `constant * COUNT(*)`",
        "Projection aliases remain output names only",
        "Aggregate arguments do not see let names",
        "There is no standalone lint framework",
    ):
        assert required in combined, required


def test_future_sequence_forbidden_surfaces_and_stop_conditions_are_locked() -> None:
    combined = f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"

    for required in (
        "| 1 | Aggregate Function Typeclasses And Decimal Arithmetic Scope Lock |",
        "| 2 | Aggregate Typeclass Vocabulary Or Tests-First Matrix |",
        "| 3 | Exact Decimal/Int Arithmetic Candidate |",
        "| 4 | Decimal Precision Fusion Readiness Lock |",
        "| 5 | Private Decimal Expression Precision Fact Carrier Scaffold |",
        "| 6 | Literal-only Aggregate Argument Candidate |",
        "| 7 | Completion Audit And Status Lock |",
        "Slice 2 should not start literal-only `SUM(constant)`",
        "Phase 42 Slice 1 Gate 2 is limited to",
        "No other file is approved",
        "stop and request a Repair Gate 1",
        "production source changes",
        "grammar or generated ANTLR changes",
        "PostgreSQL or private MySQL SQL renderer behavior changes",
        "CLI JSON v1, Project JSON v2, explain, or Semantic Metadata Artifact v1",
        "new diagnostic codes",
        "warning/lint infrastructure",
        "Decimal literal syntax",
        "cast syntax",
        "runtime/database execution",
        "project/multi-file execution",
        "relationship/JOIN-driven query behavior",
    ):
        assert required in combined, required


def test_deferred_register_classifies_phase42_related_future_work_only() -> None:
    register = _normalized(REGISTER_PATH)

    for required in (
        "Phase 42 Slice 1 scope-lock records the current aggregate validation map",
        "Phase 43 Slice 2 implements only direct `sum(let_name)` / `avg(let_name)` inline aggregate arguments",
        "Phase 43 Slice 3 implements only direct `count(let_name)` / `count_distinct(let_name)` inline aggregate arguments",
        "Phase 42 Slice 1 scope-lock records the current numeric expression typing map",
        "Phase 42 Slice 3 implements only exact Decimal/Int `+` and `-` as logical Decimal",
        "Phase 42 Slice 5 adds only a private direct-field expression fact carrier scaffold",
        "Remaining items unfreeze only when their named prerequisite phase or contract is approved",
        "No Decimal literal typing, Int/Float/Decimal promotion matrix",
        "Float/Decimal mixing, Decimal multiplication/division",
        "aggregate precision propagation",
        "SQL `DECIMAL(p,s)` / `NUMERIC(p,s)` output",
        "public JSON precision-scale fields",
        "metadata/explain precision-scale display",
        "non-Decimal type-argument policy",
    ):
        assert required in register, required

    for forbidden in (
        "Phase 42 Slice 1 implements",
        "aggregate typeclasses are implemented",
        "Decimal arithmetic is implemented",
        "Decimal literals are implemented",
        "literal-only aggregates are implemented",
    ):
        assert forbidden not in register, forbidden


def test_slice1_gate2_allowlist_and_forbidden_surfaces_are_documented() -> None:
    plan = _normalized(PLAN_PATH)
    combined = f"{plan} {_normalized(SPEC_PATH)}"

    for required in (
        "Phase 42 Slice 1 Gate 2 is limited to:",
        "docs/plan/phase-42-aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock.md",
        "docs/spec/aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock-v1.md",
        "docs/spec/v02-deferred-feature-register-v1.md",
        "tests/test_phase42_aggregate_typeclasses_decimal_scope_lock.py",
        "No other file is approved",
    ):
        assert required in plan, required

    for required in (
        "production source changes",
        "grammar or generated ANTLR changes",
        "fixtures, goldens, examples",
        "package metadata, package version, lockfile, script, workflow, CI, release",
        "IR model or lowering behavior changes",
        "PostgreSQL or private MySQL SQL renderer behavior changes",
        "CLI JSON v1, Project JSON v2, explain, or Semantic Metadata Artifact v1",
        "runtime/database execution",
        "project/multi-file execution",
        "relationship/JOIN-driven query behavior",
    ):
        assert required in combined, required


def test_package_version_remains_010() -> None:
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)
