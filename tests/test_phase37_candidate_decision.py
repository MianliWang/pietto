from __future__ import annotations

import subprocess
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    _non_slice3_repair_diff_paths,
    _non_slice3_repair_status_paths,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "src",
    "grammar",
    "src/pietto/generated",
    "fixtures",
    "tests/fixtures",
    "scripts",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
)


def _plan() -> str:
    return _normalized(PLAN_PATH)


def _git_status_for(paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all", "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def test_phase37_slice1_plan_exists_and_records_trusted_handoff() -> None:
    assert PLAN_PATH.is_file()
    plan = _plan()

    for required in (
        "Phase 37 Slice 1 is Candidate Decision And Aggregate Surface Boundary",
        "docs/plan/static-audit only",
        "implements no behavior change",
        "baseline HEAD: `09f05d141f165946489c9d272ad52db8139c8a5c`",
        "baseline branch: `main`",
        "baseline commit: `Complete Phase 36 core type system expansion audit`",
        "latest completed phase: Phase 36 Post-v0.2 Core Type System Expansion MVP",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation is authorized by Slice 1",
    ):
        assert required in plan, required


def test_slice1_candidate_decision_sections_are_present() -> None:
    plan = _plan()

    for required in (
        "## Candidate Decision",
        "## Goals",
        "## Non-goals",
        "## Current Accepted Aggregate Surface",
        "## Deferred And Prohibited Aggregate Candidates",
        "## Phase 36 Type Boundary Preservation",
        "## Public Surface Constraints",
        "## Phase 37 Slice Roadmap",
        "## Validation Plan",
        "## Planning-only Future Roadmap",
        "Post-v0.2 Aggregate Surface Expansion / Aggregate Surface Completion",
        "Aggregate surface boundary and candidate decision",
    ):
        assert required in plan, required


def test_current_accepted_aggregate_surface_is_documented() -> None:
    plan = _plan()

    for required in (
        "`count()`",
        "`count(field)` / `count(source.field)`",
        "`count(Enum field)`",
        "`PIE-S2314`",
        "`count_distinct(field)` / `count_distinct(source.field)`",
        "`count_distinct(lower/trim Text chain)`",
        "`sum(field)` / `sum(source.field)`",
        "`avg(field)` / `avg(source.field)`",
        "`sum(...)` / `avg(...)` bounded numeric expressions",
        "Int/Float literal leaves inside `sum` / `avg`",
        "Decimal `+` and `-` expression participation",
        "`min(field)` / `max(field)`",
        "grouped aggregate projections",
        "`satisfying:`",
        "grouped result `order by:`",
        "Current aggregate names remain aggregate names, not scalar builtins",
    ):
        assert required in plan, required


def test_deferred_and_prohibited_aggregate_candidates_are_locked() -> None:
    plan = _plan()

    for required in (
        "`count(expression)`",
        "broad `count_distinct(expression)`",
        "`min(expression)` / `max(expression)`",
        "aggregate filters",
        "window functions",
        "generic aggregate modifiers",
        "generic `DISTINCT` syntax",
        "nested aggregates",
        "aggregate projection composition",
        "aggregate over projection aliases",
        "literal-only aggregate arguments",
        "division or modulo aggregate arguments",
        "Decimal literal/multiply/divide/mixed promotion",
        "UUID/Enum/Any/Bytes/Json aggregate expansion",
        "relationship/fanout-safe aggregates",
    ):
        assert required in plan, required


def test_slice1_authorizes_no_behavior_or_public_surface_expansion() -> None:
    plan = _plan()

    for required in (
        "Slice 1 authorizes no source/compiler behavior change",
        "source implementation",
        "grammar change",
        "generated ANTLR change",
        "parser or AST behavior change",
        "semantic behavior change",
        "IR or SQL behavior change",
        "CLI behavior change",
        "JSON v1 change",
        "Project JSON v2 change",
        "Semantic Metadata Artifact v1 schema or output change",
        "diagnostic envelope change",
        "SQL golden byte change",
        "fixture or golden change",
        "script change",
        "workflow change",
        "package metadata change",
        "lockfile change",
        "package version change",
    ):
        assert required in plan, required

    for forbidden in (
        "Slice 1 implements `count(expression)`",
        "Slice 1 implements broad `count_distinct(expression)`",
        "Slice 1 changes SQL lowering",
        "Slice 1 changes CLI JSON v1",
        "Slice 1 changes Project JSON v2",
        "Slice 1 changes Semantic Metadata Artifact v1",
        "Slice 1 starts CI",
        "Slice 1 publishes",
    ):
        assert forbidden not in plan, forbidden


def test_phase36_type_boundaries_are_preserved() -> None:
    plan = _plan()

    for required in (
        "Decimal precision-scale carrier deferred with exact prerequisites",
        "UUID remains `limited_frozen` with no behavior expansion",
        "Enum remains metadata/readiness except `count(Enum field)` fails closed with `PIE-S2314`",
        "DateTime / Time / Interval remain deferred",
        "Any / Bytes / Json behavior surfaces remain unchanged and deferred",
        "type alias behavior is preserved",
        "domain refinement remains deferred",
        "Currency/Money remain deferred",
        "native DB metadata remains deferred",
    ):
        assert required in plan, required


def test_public_outputs_and_schema_surfaces_remain_unchanged() -> None:
    plan = _plan()

    for required in (
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "package version remains `0.1.0`",
        "no package/workflow/release metadata change",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in plan, required

    assert 'version = "0.1.0"' in _read(REPO_ROOT / "pyproject.toml")


def test_phase37_slice_roadmap_is_aggregate_focused() -> None:
    plan = _plan()

    for required in (
        "| 1 | Candidate Decision And Aggregate Surface Boundary |",
        "| 2 | Current Aggregate Matrix And Deferred Register |",
        "| 3 | `count(expression)` MVP Decision |",
        "| 4 | `count_distinct(expression)` Widening Boundary |",
        "| 5 | `min/max(expression)` Boundary |",
        "| 6 | Nested Aggregate And Composition Hardening |",
        "| 7 | Aggregate Filter / DISTINCT / Modifier Syntax Deferral |",
        "| 8 | Decimal Aggregate Expression Boundary |",
        "| 9 | Grouped Aggregate Interaction Hardening |",
        "| 10 | Completion Audit And Public Surface Lock |",
        "Later slices may recommend implementation, but implementation requires separate",
        "Gate 1 and Gate 2 authorization",
    ):
        assert required in plan, required


def test_future_roadmap_note_is_planning_only() -> None:
    plan = _plan()

    for required in (
        "The following roadmap note is planning-only and authorizes no implementation in",
        "Phase 37 Slice 1",
        "Phase 38: Deferred Feature Readiness And Semantic Surface Consolidation",
        "Phase 39: Public Developer Experience And Example Gallery MVP",
        "Phase 40: Editor Experience MVP / VSCode Extension Readiness",
        "Phase 41: Database Dialect Expansion Matrix",
        "Phase 42: SQLite or DuckDB Backend MVP",
        "Phase 43: LSP Diagnostics MVP",
        "Phase 44: Arrow / PyArrow Schema Bridge MVP",
        "Phase 45+: Semantic Graph / JOIN Readiness II",
        "These future labels do not change current package metadata",
    ):
        assert required in plan, required


def test_forbidden_surfaces_are_not_modified_or_untracked() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)
    status_output = _git_status_for(FORBIDDEN_DIFF_PATHS)

    assert _non_slice3_repair_diff_paths(diff_output) == set()
    assert _non_slice3_repair_status_paths(status_output) == set()
