from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase50-explain-public-metadata-package-integration-boundary-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
SLICE10_TITLE = (
    "# Phase 50 Slice 10 Explain / Public Metadata / Package Integration Boundary v1"
)
SLICE9_SHA = "f886589ac2f64eeb3770c914e7c049e2da105daa"
SLICE9_CI_RUN_ID = "29170827348"

SPEC_SECTION_HEADINGS = (
    "Purpose And Slice Identity",
    "Authority And Evidence Hierarchy",
    "Current Public Artifact Inventory",
    "Current Private Fact Inventory",
    "Conceptual Vocabulary",
    "Exposure-route Comparison",
    "Recommended Public Projection Boundary",
    "Artifact Separation And Ownership",
    "Single-file Explain Boundary",
    "Project JSON v2 Boundary",
    "Semantic Metadata Artifact v1 Boundary",
    "Future Project Explain Readiness",
    "Package Identity And Asset Exposure",
    "Package Requirement And Availability Exposure",
    "Capability Profile And Extension Exposure",
    "Portability Report Readiness",
    "Lineage Origin And Provenance Exposure",
    "Package Graph And Dependency Exposure",
    "Public Identity And Reference Rules",
    "Deterministic Ordering",
    "Schema Versioning And Compatibility",
    "Unknown Absent Null And Redaction Posture",
    "Privacy And Trust Boundary",
    "Diagnostic And Fail-closed Matrix",
    "CLI JSON And Artifact Separation",
    "Cross-phase Dependencies",
    "Bounded Phase 58 Handoff",
    "Explicit Deferrals And Non-goals",
    "Package Version And Release Boundary",
    "Separate Authorization And Stop Conditions",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized_section(path: Path, heading: str) -> str:
    text = _read(path)
    marker = f"## {heading}"
    start = text.index(marker)
    end = text.find("\n## ", start + len(marker))
    if end == -1:
        end = len(text)
    return " ".join(text[start:end].split())


def test_slice10_artifacts_status_and_exact_heading_order_are_locked() -> None:
    assert SPEC_PATH.exists()
    spec = _read(SPEC_PATH)
    plan = _read(PLAN_PATH)

    assert spec.startswith(f"{SLICE10_TITLE}\n")
    assert (
        tuple(
            line.removeprefix("## ")
            for line in spec.splitlines()
            if line.startswith("## ")
        )
        == SPEC_SECTION_HEADINGS
    )

    status = _normalized_section(PLAN_PATH, "Status")
    for required in (
        f"Phase 50 Slice 9 **Multi-dialect Capability Ecosystem Readiness** completed at `{SLICE9_SHA}`",
        f"documented natural CI run `{SLICE9_CI_RUN_ID}`",
        "Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary** completed",
        "9bc6ed82f3741e3c242981bb88edfb50c73fc586",
        "29179160024",
        "Phase 50 Slice 11 **Completion Audit And Status Lock** is the current",
        "Slice 11 is not complete in Gate 2",
        "Phase 50 remains in progress through Gate 2",
        "Phases 51 through 60 remain unstarted and separately authorized",
        "Phase 58 remains readiness-only and unstarted",
    ):
        assert required in status, required
    assert "Phase 50 is complete after Slice 11 Gate 2" not in status
    assert "Slice 10 completed" in status
    assert "Slice 11 is complete" not in plan


def test_route_b_artifact_separation_and_no_behavior_boundary_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Slice 10 implements no compiler or runtime behavior.",
        "Route B is explicit independently versioned public projections from private facts.",
        "CLI JSON v1, Semantic Metadata Artifact v1, Project JSON v2 check, future",
        "future package-inspection report remain separate artifact families.",
        "No universal metadata document is selected.",
        "No private fact becomes public by being named as a future input.",
        "Future artifact schemas remain independently versioned.",
        "Phase 58 remains readiness-only, unstarted, and separately authorized.",
    ):
        assert required in spec, required

    for forbidden in (
        "adds a serializer",
        "adds a CLI command",
        "implements project explain",
        "implements a portability report",
        "implements package inspection",
    ):
        assert forbidden not in spec, forbidden


def test_existing_public_artifacts_and_private_carriers_are_separate() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "CLI JSON v1 | IMPLEMENTED_STABLE",
        "Semantic Metadata Artifact v1 | IMPLEMENTED_STABLE",
        "Project JSON v2 check envelope | IMPLEMENTED_LIMITED",
        "Project row schemas, fields, availability states/reasons",
        "origin/provenance, relation dependency graphs, row",
        "Project JSON v2 fields, Semantic Metadata Artifact v1 fields, CLI",
        "Artifact v1 direct single-file field-leaf lineage remains a bounded public artifact fact",
        "Its failure envelope omits metadata rather than serializing a null metadata value.",
        "Project JSON v2 does not gain project explain, package inspection, portability,",
    ):
        assert required in spec, required


def test_package_profile_extension_and_portability_boundaries_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Package/profile/extension/dialect facts are declared readiness facts, not current public or runtime facts.",
        "declared readiness facts. They are not the Python",
        "Declared facts must never be presented as resolved, installed, or runtime-proven facts.",
        "Capability profile, dialect profile, overlay, extension catalog, and extension",
        "SQLite has rejection evidence only. DuckDB, BigQuery, Snowflake,",
        "SUPPORTED_IDENTICALLY",
        "SUPPORTED_WITH_DIALECT_SPECIFIC_LOWERING",
        "SUPPORTED_WITH_SEMANTIC_DIFFERENCES",
        "UNKNOWN_OR_NOT_DECLARED",
        "BLOCKED_BY_MISSING_CAPABILITY",
        "Portability reporting must not imply runtime validation, fallback, degradation, or automatic translation.",
    ):
        assert required in spec, required


def test_public_private_versioning_and_fail_closed_postures_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Package semantic release is an exact SemVer readiness fact.",
        "Extension/profile/",
        "overlay release facts are exact opaque readiness identifiers.",
        "Unknown, absent, null, redacted, private-only, conflicting, unresolved, and",
        "Private-only facts remain omitted.",
        "Conflicting, unresolved, unsupported, and unavailable facts must not become fabricated values, fake nulls, or assumed unknowns.",
        "An unresolved dependency, duplicate/conflicting declaration, missing exact identity, missing capability, missing lowering, ambiguity, or cycle receives no winner.",
        "It must fail closed rather than be inferred, deduplicated, or silently resolved.",
        "Supplied digests, locators, revisions, author text, and curator descriptions",
        "They provide no verification,",
        "Slice 10 assigns no diagnostic code, message, severity, ordering change, CLI",
    ):
        assert required in spec, required


def test_phase_ownership_and_bounded_handoff_are_locked() -> None:
    spec = " ".join(_read(SPEC_PATH).split())

    for required in (
        "Phase 55 owns semantic-package asset schema.",
        "Phase 56 owns capability/dialect/",
        "extension profile schema and declared checking.",
        "Phase 57 owns PostgreSQL",
        "extension signature-catalog readiness.",
        "Phase 58 owns explain, portability, and",
        "public metadata readiness.",
        "Phase 59 owns package graph and lineage/provenance",
        "integration.",
        "Phase 60 is the ecosystem completion checkpoint.",
        "Slice 10 does not begin Slice 11 or Phases 52-60.",
    ):
        assert required in spec, required


def test_package_version_remains_010() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.1.0"
