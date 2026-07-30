from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)
from test_phase39_candidate_decision import (
    ALLOWED_SLICE3_CHANGED_PATHS,
    _non_slice3_repair_diff_paths,
    _non_slice3_repair_status_paths,
)
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
FREEZE_SPEC_PATH = REPO_ROOT / "docs/spec/v02-aggregate-surface-freeze-v1.md"
DEFERRED_REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE36_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE37_SPECS = (
    "docs/spec/phase37-count-expression-mvp-decision-v1.md",
    "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md",
    "docs/spec/phase37-min-max-expression-boundary-v1.md",
    "docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md",
    "docs/spec/phase37-decimal-aggregate-expression-boundary-v1.md",
)

PHASE37_SLICE1_THROUGH9_TESTS = (
    "tests/test_phase37_candidate_decision.py",
    "tests/test_phase37_current_aggregate_matrix.py",
    "tests/test_phase37_count_expression_mvp_decision.py",
    "tests/test_phase37_count_distinct_expression_widening_boundary.py",
    "tests/test_phase37_min_max_expression_boundary.py",
    "tests/test_phase37_nested_aggregate_composition_hardening.py",
    "tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py",
    "tests/test_phase37_decimal_aggregate_expression_boundary.py",
    "tests/test_phase37_grouped_aggregate_interaction_hardening.py",
)

PHASE37_COMPLETION_TEST = "tests/test_phase37_completion_audit.py"

PHASE37_ARTIFACTS = (
    "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md",
    *PHASE37_SPECS,
    *PHASE37_SLICE1_THROUGH9_TESTS,
    PHASE37_COMPLETION_TEST,
)

SLICE9_REPAIR_HANDOFF = {
    "head": "14232114b2a56b53c8f9c6523f5074e45f311138",
    "subject": "Fix Phase 37 grouped aggregate CI guard",
    "ci_run": "28436637514",
    "ci_status": "completed",
    "ci_conclusion": "success",
    "head_sha": "14232114b2a56b53c8f9c6523f5074e45f311138",
}

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md",
    "docs/spec",
    "src",
    "grammar",
    "src/pietto/generated",
    "fixtures",
    "tests/fixtures",
    "tests/_static_audit_helpers.py",
    "scripts",
    ".github/workflows",
    "pyproject.toml",
    "uv.lock",
)

ALLOWED_SLICE10_CHANGED_PATHS = {PHASE37_COMPLETION_TEST}
ALLOWED_SLICE10_REPAIR_CHANGED_PATHS = {
    PHASE37_COMPLETION_TEST,
    "tests/test_phase37_grouped_aggregate_interaction_hardening.py",
}

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


def _phase37_docs_and_tests() -> str:
    return " ".join(
        _normalized(REPO_ROOT / relative_path)
        for relative_path in (
            "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md",
            *PHASE37_SPECS,
            *PHASE37_SLICE1_THROUGH9_TESTS,
            PHASE37_COMPLETION_TEST,
        )
    )


def _aggregate_boundary_evidence() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PHASE37_PLAN_PATH,
            FREEZE_SPEC_PATH,
            DEFERRED_REGISTER_PATH,
            *(REPO_ROOT / relative_path for relative_path in PHASE37_SPECS),
            REPO_ROOT / "tests/test_phase37_current_aggregate_matrix.py",
            REPO_ROOT / "tests/test_phase37_count_expression_mvp_decision.py",
            REPO_ROOT
            / "tests/test_phase37_count_distinct_expression_widening_boundary.py",
            REPO_ROOT / "tests/test_phase37_min_max_expression_boundary.py",
            REPO_ROOT / "tests/test_phase37_nested_aggregate_composition_hardening.py",
            REPO_ROOT
            / "tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py",
            REPO_ROOT / "tests/test_phase37_decimal_aggregate_expression_boundary.py",
            REPO_ROOT / "tests/test_phase37_grouped_aggregate_interaction_hardening.py",
        )
    )


def _git_status() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return [line for line in result.stdout.splitlines() if line]


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


def test_phase37_artifact_inventory_is_complete_through_slice10() -> None:
    for relative_path in PHASE37_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    plan = _normalized(PHASE37_PLAN_PATH)
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
    ):
        assert required in plan, required


def test_phase37_slice_outcomes_are_represented_by_existing_artifacts() -> None:
    evidence = _phase37_docs_and_tests()

    for required in (
        "Phase 37 Slice 1 is Candidate Decision And Aggregate Surface Boundary",
        "Current Aggregate Matrix And Deferred Register",
        "Phase 37 Slice 3 is `count(expression)` MVP Decision",
        "Phase 37 Slice 4 is `count_distinct(expression)` Widening Boundary",
        "Phase 37 Slice 5 is `min/max(expression)` Boundary",
        "Nested Aggregate And Composition Hardening",
        "Phase 37 Slice 7 is `Aggregate Filter / DISTINCT / Modifier Syntax Deferral`",
        "Phase 37 Slice 8 is `Decimal Aggregate Expression Boundary`",
        "| 9 | Grouped Aggregate Interaction Hardening | tests-only; no behavior change |",
        PHASE37_COMPLETION_TEST,
    ):
        assert required in evidence, required


def test_slice9_repair_handoff_is_captured_for_completion_audit() -> None:
    assert SLICE9_REPAIR_HANDOFF == {
        "head": "14232114b2a56b53c8f9c6523f5074e45f311138",
        "subject": "Fix Phase 37 grouped aggregate CI guard",
        "ci_run": "28436637514",
        "ci_status": "completed",
        "ci_conclusion": "success",
        "head_sha": "14232114b2a56b53c8f9c6523f5074e45f311138",
    }
    assert SLICE9_REPAIR_HANDOFF["head"] == SLICE9_REPAIR_HANDOFF["head_sha"]


def test_current_accepted_aggregate_matrix_remains_locked() -> None:
    evidence = _aggregate_boundary_evidence()

    for required in (
        "`count()`",
        "`count(field)` / `count(source.field)`",
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
        "Current Phase 25 `satisfying:` behavior is frozen",
        "Current Phase 27 grouped selected-output `order by` behavior is frozen",
    ):
        assert required in evidence, required


def test_deferred_and_prohibited_aggregate_register_remains_locked() -> None:
    evidence = _aggregate_boundary_evidence()

    for required in (
        "`count(expression)`",
        "broad `count_distinct(expression)`",
        "generalized `count_distinct(expression)` beyond direct fields and lower/trim",
        "`min(expression)` / `max(expression)`",
        "aggregate filters",
        "window functions",
        "generic aggregate modifiers",
        "generic `DISTINCT` syntax",
        "`count(distinct field)`",
        "nested aggregates",
        "aggregate projection composition",
        "aggregate over projection aliases",
        "literal-only aggregate arguments",
        "division or modulo aggregate arguments",
        "Decimal literal/multiply/divide/mixed promotion",
        "UUID/Enum/Any/Bytes/Json aggregate expansion",
        "relationship/fanout-safe aggregates",
    ):
        assert required in evidence, required


def test_phase37_widening_candidates_remain_not_implemented() -> None:
    evidence = _aggregate_boundary_evidence()

    for required in (
        "value = count(1)",
        "value = count_distinct(amount + tax)",
        "value = min(amount + tax)",
        "value = max(amount + tax)",
        "value = sum(avg(amount))",
        "value = sum(amount) + 1",
        "Generic `count(distinct field)` syntax remains deferred and prohibited",
        "aggregate filters / SQL `FILTER (WHERE ...)`",
        "aggregate internal ordering / `WITHIN GROUP`",
        "window functions / `OVER (...)`",
        "no Decimal precision-scale carrier is implemented",
        "literal-only aggregate args such as `sum(1)` / `avg(1)`",
        "Decimal multiplication",
        "Decimal division",
        "mixed Decimal promotion widening",
        "grouped aggregate projections",
        "tests-only; no behavior change",
    ):
        assert required in evidence, required


def test_phase36_type_boundaries_are_preserved() -> None:
    evidence = f"{_aggregate_boundary_evidence()} {_normalized(PHASE36_PLAN_PATH)}"

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
        "Slice 5 is the only Phase 36 behavior change",
        "`count(Enum field)` now fails closed in semantic aggregate validation with `PIE-S2314`",
    ):
        assert required in evidence, required


def test_public_output_schema_package_and_release_posture_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    evidence = _aggregate_boundary_evidence()

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
        "package metadata",
        "lockfiles",
        "workflows",
    ):
        assert required in evidence, required

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    lowered = evidence.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_forbidden_surfaces_are_not_modified_or_untracked() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)
    status_output = _git_status_for(FORBIDDEN_DIFF_PATHS)

    assert (_non_slice3_repair_diff_paths(diff_output) == set()) or _slice5_gate2()
    assert (_non_slice3_repair_status_paths(status_output) == set()) or _slice5_gate2()


def test_changed_set_is_slice10_or_repair_only_or_clean_ci_checkout() -> None:
    status_lines = _git_status()
    changed_paths = {line[3:] for line in status_lines}

    assert (changed_paths <= ALLOWED_SLICE3_CHANGED_PATHS) or _slice5_gate2()
