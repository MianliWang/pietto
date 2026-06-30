from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase36-core-type-resolution-matrix-v1.md"

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/_metadata",
    "tests/fixtures",
    "pyproject.toml",
    "uv.lock",
    ".github",
    "scripts",
    "examples",
)


def _phase36_slice2_docs() -> str:
    return f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"


def test_phase36_is_broader_core_type_resolution_not_decimal_only() -> None:
    combined = _phase36_slice2_docs()

    for required in (
        "Phase 36 is now a broader core type resolution phase, not Decimal-only",
        "Post-v0.2 Core Type System Expansion / Candidate Resolution",
        "Slice 2 rescopes the phase",
        "without changing behavior",
    ):
        assert required in combined, required


def test_twelve_slice_plan_is_documented() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "| 1 | Candidate Decision And Type Expansion Boundary |",
        "| 2 | Rescope And Candidate Resolution Matrix |",
        "| 3 | Decimal Precision-scale Carrier MVP Decision |",
        "| 4 | UUID Support Completion |",
        "| 5 | Enum Support Resolution |",
        "| 6 | DateTime / Time / Interval Boundary |",
        "| 7 | Any / Bytes / Json Support Posture |",
        "| 8 | Type Alias / Domain Refinement Boundary |",
        "| 9 | Expanded Scalar / Operator Matrix |",
        "| 10 | Public Surface Stability Hardening |",
        "| 11 | Phase 36 Status Housekeeping |",
        "| 12 | Completion Audit And Status Lock |",
    ):
        assert required in plan, required


def test_resolution_modes_are_explicitly_defined() -> None:
    combined = _phase36_slice2_docs()

    for required in (
        "resolve means one of",
        "safe implementation",
        "fail-closed contract",
        "readiness/spec",
        "defer with exact prerequisites",
        "Resolve does not mean blindly implementing every candidate",
    ):
        assert required in combined, required


def test_currency_money_and_native_db_metadata_are_deferred() -> None:
    combined = _phase36_slice2_docs()

    for required in (
        "Currency/Money is deferred",
        "Native DB metadata is deferred",
        "| Currency/Money |",
        "| native DB metadata |",
        "Currency/Money remains deferred until all of the following are separately approved",
        "Native DB metadata remains deferred until all of the following are separately approved",
        "Currency primitive",
        "Money primitive",
        "native type annotations",
        "schema introspection",
    ):
        assert required in combined, required


def test_candidate_matrix_covers_required_candidates() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "| Decimal precision-scale metadata carrier |",
        "| UUID |",
        "| Enum |",
        "| DateTime |",
        "| Time |",
        "| Interval |",
        "| Any |",
        "| Bytes |",
        "| Json |",
        "| type alias / domain refinement |",
        "| scalar/operator/comparison/aggregate matrix |",
        "| Currency/Money |",
        "| native DB metadata |",
    ):
        assert required in spec, required


def test_slice2_authorizes_no_implementation_behavior() -> None:
    combined = _phase36_slice2_docs()

    for required in (
        "Slice 2 authorizes no implementation behavior",
        "does not implement type behavior",
        "does not change source/compiler behavior",
        "does not change Semantic Metadata Artifact v1 schema or output",
        "No source/compiler behavior is authorized by Slice 2",
        "no forbidden surface is opened by this spec",
    ):
        assert required in combined, required

    for forbidden in (
        "Slice 2 implements",
        "Slice 2 changes semantic behavior",
        "Slice 2 changes IR behavior",
        "Slice 2 changes SQL behavior",
        "Slice 2 changes CLI behavior",
        "Slice 2 changes JSON v1",
        "Slice 2 changes Semantic Metadata Artifact v1",
    ):
        assert forbidden not in combined, forbidden


def test_forbidden_surfaces_are_not_modified_by_slice2() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""
