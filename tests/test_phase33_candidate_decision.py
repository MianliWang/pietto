from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-33-json-v2-and-project-multifile.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase-33-json-v2-project-multifile-boundary-v1.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PIETTO_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
CLI_JSON_V1_SPEC_PATH = REPO_ROOT / "docs/spec/cli-json-v1.md"
ARTIFACT_V1_SPEC_PATH = REPO_ROOT / "docs/spec/semantic-metadata-artifact-v1.md"

STATUS_DOCS = (AGENTS_PATH, PIETTO_SPEC_PATH)

PHASE_ROADMAP = (
    "Phase 33: JSON v2 And Project / Multi-file MVP",
    "Phase 34: Relationship Grain And Narrow JOIN MVP",
    "Phase 35: Developer Experience And Delivery Pipeline MVP",
    "Phase 36: Post-v0.2 Core Type System Expansion MVP",
    "Phase 37: Post-v0.2 Aggregate Surface Expansion MVP",
    "Semantic Graph / ERD / AI Metadata Export remains a post-Phase-37 "
    "deferred candidate without an assigned phase number",
)

SLICE_BREAKDOWN = (
    "1. Candidate Decision, Scope, Boundary, And Phase 32 Handoff Audit.",
    "2. JSON v2 Project Result Envelope Contract.",
    "3. Project Root, Config, Path, And Discovery Contract Reconciliation.",
    "4. Private Project Discovery Model MVP.",
    "5. Project Check CLI MVP.",
    "6. JSON v2 Serializer MVP.",
    "7. Project Explain/Metadata Aggregation Contract Or MVP.",
    "8. CLI, Package Smoke, Docs, And Compatibility Hardening.",
    "9. Completion Audit And Status Lock.",
)

FORBIDDEN_IMPLEMENTATION_PATHS = (
    "src/pietto/project.py",
    "src/pietto/project",
    "src/pietto/json_v2.py",
    "src/pietto/json_v2",
    "src/pietto/_json_v2.py",
    "src/pietto/_project.py",
    "src/pietto/database.py",
    "src/pietto/runtime.py",
    "src/pietto/schema_introspection.py",
)

FORBIDDEN_SOURCE_NAME_FRAGMENTS = (
    "json_v2",
    "project_loader",
    "multi_file",
    "schema_introspection",
    "graph_runtime",
)

APPROVED_SLICE6_SOURCE_PATHS = {
    "src/pietto/_project/json_v2.py",
}


def test_phase33_slice1_artifacts_and_status_are_static_audit_only() -> None:
    combined = _phase33_docs()
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert project["version"] == "0.1.0"

    for required in (
        "Phase 33 Slice 1 Candidate Decision, Scope, Boundary, And Phase 32 "
        "Handoff Audit is complete as docs/spec/static-audit/status-only work",
        "Phase 33 Slice 9 Completion Audit And Status Lock is complete",
        "Phase 33 JSON v2 And Project / Multi-file MVP is complete",
        "baseline HEAD: `045e08bfb15f88b526e856aee7ca585f1998071e`",
        "Phase 32 Semantic Explain And Metadata Output MVP is complete",
        "`pietto explain <file> [--format text|json]` is available",
        "Semantic Metadata Artifact v1 JSON is available through `pietto explain "
        "--format json`",
        "package version remains `0.1.0`",
        "no release tag, package release, publishing, upload, signing, or "
        "attestation operation is part of this slice",
        "Slice 1 adds no source implementation, no JSON v2 implementation, no "
        "project mode implementation, no multi-file discovery implementation",
        "no grammar changes, no generated changes, no fixture or golden changes",
        "no script changes, no package metadata changes, no dependency changes, "
        "no workflow changes",
    ):
        assert required in combined, required


def test_phase33_roadmap_titles_and_graph_deferral_are_locked() -> None:
    combined = _phase33_docs()
    current_status = " ".join(_normalized(path) for path in STATUS_DOCS)

    for required in PHASE_ROADMAP:
        assert required in combined, required
        assert required in current_status, required

    for stale in (
        "Phase 33: Project And Multi-file MVP",
        "Phase 34: Semantic Graph / ERD / AI Metadata Export MVP",
        "Phase 35: Relationship Grain And Narrow JOIN MVP",
        "Semantic Graph / ERD / AI Metadata Export: Phase",
    ):
        assert stale not in combined, stale

    for required in (
        "Phase 34, Phase 35, Phase 36, and Phase 37 are not started",
        "Phase 34, Phase 35, Phase 36, and Phase 37 are not started by this boundary",
    ):
        assert required in combined, required


def test_json_v2_boundary_does_not_mutate_existing_json_surfaces() -> None:
    combined = _phase33_docs()
    cli_json_v1_spec = _normalized(CLI_JSON_V1_SPEC_PATH)
    artifact_v1_spec = _normalized(ARTIFACT_V1_SPEC_PATH)

    for required in (
        "JSON v2 is a new project-mode machine-readable output surface",
        "It is not a mutation of CLI JSON v1",
        "not a mutation of Semantic Metadata Artifact v1",
        "`schema_version: 2`",
        '`mode: "project"`',
        "explicit project identity",
        "ordered project inputs",
        "diagnostics",
        "CLI errors",
        "command-specific payloads",
        "not Semantic Metadata Artifact v1 aggregation by default",
        "mutating JSON v1",
        "mutating Artifact v1",
        "embedding Artifact v1 by default",
        "project emit-sql artifacts",
        "dependency graph beyond contract",
        "runtime/database/schema-introspection behavior",
        "JOIN/relationship behavior",
    ):
        assert required in combined, required

    assert "JSON schema version 1 remains exclusively single-file" in cli_json_v1_spec
    assert "separate from existing single-file CLI JSON v1" in artifact_v1_spec


def test_project_multifile_and_cli_candidate_boundaries_are_locked() -> None:
    combined = _phase33_docs()

    for required in (
        "explicit `--project ROOT`",
        "required `pietto.toml`",
        "deterministic file discovery/reporting",
        "no implicit parent search",
        "no configless project mode",
        "no hidden global config",
        "normalized project-relative paths",
        "containment checks",
        "duplicate physical identity rejection",
        "deterministic sorting",
        "stable reporting order",
        "language-level imports/includes",
        "cross-file semantic references",
        "grammar changes",
        "database/schema introspection",
        "runtime",
        "db pull",
        "project framework expansion",
        "pietto check --project ROOT [--format json]",
        "pietto check --format json",
        "pietto emit-sql --format json",
        "pietto explain --format json",
        "Single-file JSON output remains JSON v1",
        "Project mode with JSON should be JSON v2",
        "This document does not implement the CLI",
        "`pietto project ...`",
        "`pietto inspect ...`",
        "`pietto report ...`",
        "hidden root discovery",
        "`emit-sql --project`",
        "`explain --project`",
    ):
        assert required in combined, required


def test_failure_policy_and_phase32_handoff_are_locked() -> None:
    combined = _phase33_docs()

    for required in (
        "root/config/path errors: exit `2`, stop before parse",
        "source-read/parser errors: aggregate/report, but block project semantic "
        "analysis",
        "semantic errors: exit `1`, block project IR",
        "IR errors: exit `1`, block SQL",
        "no partial SQL output",
        "no partial metadata output by default",
        "existing diagnostic codes/fields remain stable",
        "JSON v2 may define v2-only `related_locations`",
        "Semantic Metadata Artifact v1 remains stable",
        "Phase 33 must not silently mutate Artifact v1",
        "Phase 33 must not silently aggregate Artifact v1 across files by default",
        "Phase 33 may only define project JSON v2 boundaries in this slice",
    ):
        assert required in combined, required


def test_future_slice_breakdown_is_conservative() -> None:
    combined = _phase33_docs()

    for required in SLICE_BREAKDOWN:
        assert required in combined, required


def test_slice1_does_not_add_forbidden_implementation_surfaces() -> None:
    combined = _phase33_docs()

    for relative_path in FORBIDDEN_IMPLEMENTATION_PATHS:
        assert not (REPO_ROOT / relative_path).exists(), relative_path

    src_paths = tuple(
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "src" / "pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )
    for relative_path in src_paths:
        for fragment in FORBIDDEN_SOURCE_NAME_FRAGMENTS:
            if fragment == "json_v2" and relative_path in APPROVED_SLICE6_SOURCE_PATHS:
                continue
            assert fragment not in relative_path, relative_path

    for required in (
        "no source/grammar/generated/fixture/golden/script/package/workflow "
        "implementation is part of Slice 1",
        "This Gate 2 slice does not require hash-lock replacement",
    ):
        assert required in combined, required


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _phase33_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))
