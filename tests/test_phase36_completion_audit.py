from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    _non_slice3_repair_diff_paths,
)
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PHASE36_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

STATUS_DOCS = (AGENTS_PATH, PIETTO_SPEC_PATH)
STATUS_AND_PLAN_DOCS = (*STATUS_DOCS, PHASE36_PLAN_PATH)

PHASE36_SLICE_ROWS = (
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
)

PHASE36_ARTIFACTS = (
    "docs/plan/phase-36-post-v02-core-type-system-expansion.md",
    "docs/spec/decimal-precision-scale-metadata-carrier-readiness-v1.md",
    "docs/spec/phase36-core-type-resolution-matrix-v1.md",
    "docs/spec/decimal-precision-scale-carrier-mvp-decision-v1.md",
    "docs/spec/uuid-support-completion-v1.md",
    "docs/spec/enum-support-resolution-v1.md",
    "docs/spec/datetime-time-interval-boundary-v1.md",
    "docs/spec/any-bytes-json-support-posture-v1.md",
    "docs/spec/type-alias-domain-refinement-boundary-v1.md",
    "docs/spec/expanded-scalar-operator-matrix-v1.md",
    "docs/spec/public-surface-stability-hardening-v1.md",
    "tests/test_phase36_candidate_decision.py",
    "tests/test_phase36_rescope_candidate_resolution_matrix.py",
    "tests/test_phase36_decimal_precision_scale_carrier_mvp_decision.py",
    "tests/test_phase36_uuid_support_completion.py",
    "tests/test_phase36_enum_support_resolution.py",
    "tests/test_phase36_datetime_time_interval_boundary.py",
    "tests/test_phase36_any_bytes_json_support_posture.py",
    "tests/test_phase36_type_alias_domain_refinement_boundary.py",
    "tests/test_phase36_expanded_scalar_operator_matrix.py",
    "tests/test_phase36_public_surface_stability_hardening.py",
    "tests/test_phase36_status_housekeeping.py",
    "tests/test_phase36_completion_audit.py",
)

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/_metadata",
    "src/pietto/_project",
    "tests/fixtures",
    "pyproject.toml",
    "uv.lock",
    ".github",
    "scripts",
    "examples",
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


def _combined_status() -> str:
    return " ".join(_normalized(path) for path in STATUS_DOCS)


def _combined_status_and_plan() -> str:
    return " ".join(_normalized(path) for path in STATUS_AND_PLAN_DOCS)


def test_phase36_slices_and_artifacts_are_complete() -> None:
    plan = _normalized(PHASE36_PLAN_PATH)

    for required in PHASE36_SLICE_ROWS:
        assert required in plan, required
    for relative_path in PHASE36_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_phase36_final_completion_status_is_documented() -> None:
    for path in STATUS_DOCS:
        status = _normalized(path)

        assert (
            "Phase 36 Post-v0.2 Core Type System Expansion MVP is complete "
            "as of Slice 12 Completion Audit And Status Lock"
        ) in status, str(path)
        assert "Slice 12 is the final completion audit/status lock" in status
        assert "Phase 36 remains in progress" not in status
        assert "Phase 36 Slices 1 through 10 are complete" not in status
        assert "does not claim Phase 36 final completion" not in status


def test_slice12_plan_records_final_status_lock_boundary() -> None:
    plan = _normalized(PHASE36_PLAN_PATH)

    for required in (
        "Phase 36 Slice 12 selects Option B: completion audit plus final status lock",
        "Slice 12 completes Phase 36 Post-v0.2 Core Type System Expansion MVP",
        "docs/spec/static-audit/status-lock work only",
        "Slice 12 is the final completion audit/status lock",
        "Gate 3 remains responsible for final staging, commit, push, and "
        "natural CI `headSha` verification",
    ):
        assert required in plan, required


def test_slice5_is_the_only_phase36_behavior_change() -> None:
    combined = _combined_status_and_plan()

    assert "Slice 5 is the only Phase 36 behavior change" in combined
    assert "`count(Enum field)`" in combined
    assert "`PIE-S2314`" in combined
    assert (
        "`count(Enum field)` now fails closed in semantic aggregate "
        "validation with `PIE-S2314`"
    ) in combined
    assert (
        "Slices 1, 2, 3, 4, 6, 7, 8, 9, 10, 11, and 12 are docs/spec/static-audit"
    ) in combined
    assert "with no behavior change" in combined


def test_phase36_candidate_resolutions_are_locked() -> None:
    combined = _combined_status_and_plan()

    for required in (
        "Decimal precision-scale carrier",
        "deferred with exact prerequisites",
        "UUID remains `limited_frozen` without behavior expansion",
        "Enum remains metadata/readiness except the Slice 5 fail-closed fix",
        "DateTime, Time, and Interval remain unsupported/deferred",
        "Any, Bytes, and Json posture is documented without behavior expansion",
        "type alias behavior remains current",
        "domain refinement is deferred",
        "expanded scalar/operator matrix is documented without behavior change",
        "public surface stability is locked without behavior change",
        "Currency/Money",
        "native DB metadata remain deferred",
    ):
        assert required in combined, required


def test_public_schema_package_and_release_boundaries_are_locked() -> None:
    combined = _combined_status_and_plan()
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    for required in (
        "No public schema/output expansion occurred",
        "CLI JSON v1",
        "Project JSON v2",
        "Semantic Metadata Artifact v1 schema/output",
        "diagnostic envelope",
        "SQL golden bytes",
        "fixtures/goldens",
        "workflows",
        "scripts",
        "lockfiles",
        "package metadata",
        "Package version remains `0.1.0`",
        "No tag/release/publish/upload/signing/attestation occurred",
    ):
        assert required in combined, required

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)
    assert (
        "`docs/spec/pietto-v0.9.md` remains a spec/status document path, "
        "not the package version or a release tag"
    ) in _normalized(PIETTO_SPEC_PATH)

    lowered = combined.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_slice12_adds_no_source_output_or_package_surfaces() -> None:
    plan = _normalized(PHASE36_PLAN_PATH)

    for required in (
        "Slice 12 makes no source/compiler behavior change",
        "It does not change grammar",
        "generated ANTLR files",
        "parser or AST behavior",
        "semantic behavior",
        "IR or SQL behavior",
        "CLI output",
        "CLI JSON v1",
        "Project JSON v2",
        "Semantic Metadata Artifact v1 schema or output",
        "diagnostic envelope shape",
        "SQL golden bytes",
        "fixtures",
        "goldens",
        "validation scripts",
        "workflows",
        "package metadata",
        "package version",
        "lockfiles",
        "tags, release, publish/upload, signing, or attestation",
    ):
        assert required in plan, required


def test_forbidden_implementation_package_and_workflow_surfaces_are_unchanged() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert (
        _non_slice3_repair_diff_paths(diff_output) == set()
    ) or _phase54_active_gate2_is_active()
