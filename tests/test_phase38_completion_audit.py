from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE38_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE38_SPEC_PATHS = (
    "docs/spec/phase38-count-family-semantics-contract-v1.md",
    "docs/spec/phase38-type-capability-matrix-contract-v1.md",
    "docs/spec/phase38-boundary-types-capability-contract-v1.md",
    "docs/spec/phase38-distinct-collation-ordering-readiness-v1.md",
    "docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md",
)

PHASE38_TEST_PATHS = (
    "tests/test_phase38_candidate_decision.py",
    "tests/test_phase38_count_family_semantics_contract.py",
    "tests/test_phase38_type_capability_matrix_contract.py",
    "tests/test_phase38_boundary_types_capability_contract.py",
    "tests/test_phase38_distinct_collation_ordering_readiness.py",
    "tests/test_phase38_binding_filter_post_aggregate_roadmap.py",
    "tests/test_phase38_completion_audit.py",
)

PHASE38_ARTIFACTS = (
    "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md",
    *PHASE38_SPEC_PATHS,
    *PHASE38_TEST_PATHS,
)

ALLOWED_SLICE7_CHANGED_PATHS = {
    "docs/plan/phase-38-aggregate-semantics-and-type-capability-consolidation.md",
    "tests/test_phase38_completion_audit.py",
}

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
    return _normalized(PHASE38_PLAN_PATH)


def _phase38_evidence() -> str:
    return " ".join(
        _normalized(REPO_ROOT / relative_path) for relative_path in PHASE38_ARTIFACTS
    )


def _phase38_release_evidence() -> str:
    return " ".join(
        _normalized(REPO_ROOT / relative_path)
        for relative_path in PHASE38_ARTIFACTS
        if relative_path != "tests/test_phase38_completion_audit.py"
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


def _status_path(line: str) -> str:
    return line[3:]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_phase38_artifact_inventory_is_complete_through_slice7() -> None:
    for relative_path in PHASE38_ARTIFACTS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    plan = _plan()
    for required in (
        "| 1 | Candidate Decision And Scope Inventory |",
        "| 2 | Count Family Semantics Contract |",
        "| 3 | Type Capability Matrix Contract |",
        "| 4 | Any / Json / Bytes / Enum / UUID Capability Boundary |",
        "| 5 | Distinct / Collation / Ordering Readiness |",
        "| 6 | Binding / Aggregate Filter / Post-Aggregate Roadmap |",
        "| 7 | Completion Audit And Public Surface Lock |",
    ):
        assert required in plan, required


def test_phase38_completion_status_is_locked_in_plan() -> None:
    plan = _plan()

    for required in (
        "Phase 38 Slice 7 is Completion Audit And Public Surface Lock",
        "docs/plan/static-audit/tests-only",
        "authorizes no behavior change",
        "Slice 7 closes Phase 38 as an aggregate semantics and type capability consolidation phase",
        "Phase 38 is complete as docs/plan/spec/static-audit and tests-only work",
        "Gate 2 must not guess the final Gate 3 commit SHA",
        "Gate 3 remains responsible for final staging, commit, push, and natural CI `headSha` verification",
    ):
        assert required in plan, required


def test_slice1_through_slice6_outcomes_remain_represented() -> None:
    evidence = _phase38_evidence()

    for required in (
        "Slice 1 recorded the candidate decision and scope inventory",
        "Slice 2 recorded the count-family semantics contract",
        "Slice 3 recorded the type capability matrix contract",
        "Slice 4 recorded the Any / Json / Bytes / Enum / UUID capability boundary",
        "Slice 5 recorded distinct, collation, and ordering readiness",
        "Slice 6 recorded the binding, aggregate-filter, and post-aggregate roadmap",
        "Phase 38 Slice 2 is Count Family Semantics Contract",
        "Phase 38 Slice 3 is Type Capability Matrix Contract",
        "Phase 38 Slice 4 is Any / Json / Bytes / Enum / UUID Capability Boundary",
        "Phase 38 Slice 5 is Distinct / Collation / Ordering Readiness",
        "Phase 38 Slice 6 is Binding / Aggregate Filter / Post-Aggregate Roadmap",
    ):
        assert required in evidence, required


def test_slice6_ci_repair_guard_is_clean_checkout_compatible() -> None:
    evidence = _phase38_evidence()

    for required in (
        "Slice 6 CI repair is part of the trusted completion posture",
        "23ad6264281bb5e4ed20db546f4f51cf30a21066",
        "compatible with both a clean CI checkout and a dirty Gate 2 or repair working tree",
        "allowed-path subset guard",
        "Accept both clean CI checkout and dirty Gate 2/repair states",
        "assert status_paths <= ALLOWED_SLICE6_CHANGED_PATHS",
    ):
        assert required in evidence, required


def test_phase38_remains_static_audit_only_without_behavior_changes() -> None:
    plan = _plan()

    for required in (
        "source/compiler behavior unchanged",
        "grammar and generated parser inventory unchanged",
        "parser and AST behavior unchanged",
        "semantic behavior unchanged",
        "IR behavior unchanged",
        "SQL behavior unchanged",
        "CLI text output unchanged",
        "CLI JSON v1 unchanged",
        "Project JSON v2 unchanged",
        "Semantic Metadata Artifact v1 unchanged",
        "diagnostic envelope unchanged",
        "SQL golden bytes unchanged",
        "fixtures/goldens unchanged",
        "scripts/workflows unchanged",
        "package metadata unchanged",
    ):
        assert required in plan, required


def test_aggregate_and_type_system_boundaries_remain_deferred() -> None:
    evidence = _phase38_evidence()

    for required in (
        "`count(expression)`, `count(constant)`, `count(1)`, and `count_if(predicate)`",
        "broad `count_distinct(expression)`",
        "`min/max(expression)`",
        "broad `sum/avg(expression)`",
        "`count_distinct(Json/Bytes/Any/Enum)`",
        "`min/max(Text|UUID|Enum|Json|Bytes|Any)`",
        "SQL-style aggregate modifiers, aggregate filters, `WITHIN GROUP`, and window functions",
        "explicit `let:` / `with:` binding syntax",
        "post-aggregate expression composition, relation-layer IR, subquery lowering",
        "Decimal precision-scale carrier",
        "Float NaN/signed-zero policy",
        "Text collation/normalization policy",
        "UUID ordering metadata",
        "Enum ordering metadata",
        "relationship-aware aggregate rewrites",
        "fanout warnings",
        "grain inference",
        "endpoint-qualified lookup",
        "relation composition",
        "JOIN behavior",
        "runtime/database execution",
        "schema introspection",
        "db pull",
        "native database metadata",
        "raw SQL escape hatches",
        "public MySQL API expansion",
    ):
        assert required in evidence, required


def test_public_surface_package_and_release_lock_is_preserved() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    evidence = _phase38_evidence()

    for required in (
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation",
        "package version change, tag, release, publish/upload, signing, or attestation",
        "package release, publication, upload, signing, and attestation",
    ):
        assert required in evidence, required

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    lowered = _phase38_release_evidence().lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_forbidden_surfaces_are_unchanged_or_untracked() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)
    status_output = _git_status_for(FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""
    assert status_output == ""


def test_changed_set_is_slice7_allowlist_or_clean_ci_checkout() -> None:
    status_paths = {_status_path(line) for line in _git_status()}

    # Accept both clean CI checkout and dirty Gate 2 working trees.
    assert status_paths <= ALLOWED_SLICE7_CHANGED_PATHS

    for path in status_paths:
        assert path in ALLOWED_SLICE7_CHANGED_PATHS, path

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert not any(_path_matches(path, forbidden) for path in status_paths)
