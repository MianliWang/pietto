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
    ALLOWED_SLICE3_CHANGED_PATHS as PHASE40_SLICE3_REPAIR_CHANGED_PATHS,
)
from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PHASE39_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-39-count-family-implementation-candidate.md"
)
PHASE39_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/phase39-count-expression-mvp-contract-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE39_TEST_PATHS = (
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase39_count_expression_mvp_contract.py",
    "tests/test_phase39_count_expression_semantics.py",
    "tests/test_phase39_count_expression_ir.py",
    "tests/test_phase39_count_expression_sql.py",
    "tests/test_phase39_count_expression_cli_json_output.py",
    "tests/test_phase39_count_family_boundary_regression_matrix.py",
    "tests/test_phase39_completion_audit.py",
)

PHASE39_IMPLEMENTATION_PATHS = (
    "src/pietto/semantic/aggregates.py",
    "src/pietto/sql/expressions.py",
    "src/pietto/sql/mysql_expressions.py",
)

PHASE39_ARTIFACTS = (
    "docs/plan/phase-39-count-family-implementation-candidate.md",
    "docs/spec/phase39-count-expression-mvp-contract-v1.md",
    *PHASE39_TEST_PATHS,
)

SLICE7_REPAIR_HANDOFF = {
    "failed_commit": "2de5a0791e3b7ca84605bffa98d11c54fffac6fa",
    "failed_ci_run": "28508292364",
    "failed_ci_status": "completed",
    "failed_ci_conclusion": "failure",
    "repair_commit": "7f299a227f9656bc8151cd738d9f9207a98e34ce",
    "repair_ci_run": "28508625025",
    "repair_ci_status": "completed",
    "repair_ci_conclusion": "success",
    "final_trusted_head": "7f299a227f9656bc8151cd738d9f9207a98e34ce",
}

ALLOWED_SLICE8_CHANGED_PATHS = {
    "docs/plan/phase-39-count-family-implementation-candidate.md",
    "tests/test_phase39_candidate_decision.py",
    "tests/test_phase39_completion_audit.py",
}
ALLOWED_PHASE40_SLICE3_REPAIR_CHANGED_PATHS = (
    ALLOWED_SLICE8_CHANGED_PATHS | PHASE40_SLICE3_REPAIR_CHANGED_PATHS
)

FORBIDDEN_DIFF_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/phase39-count-expression-mvp-contract-v1.md",
    "grammar",
    "src",
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
    return _normalized(PHASE39_PLAN_PATH)


def _phase39_evidence() -> str:
    return " ".join(
        _normalized(REPO_ROOT / relative_path)
        for relative_path in (*PHASE39_ARTIFACTS, *PHASE39_IMPLEMENTATION_PATHS)
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
    if len(line) > 2 and line[2] == " ":
        return line[3:]
    return line.split(maxsplit=1)[1]


def _path_matches(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def test_phase39_artifact_inventory_is_complete_through_slice8() -> None:
    for relative_path in (*PHASE39_ARTIFACTS, *PHASE39_IMPLEMENTATION_PATHS):
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    plan = _plan()
    for required in (
        "| 1 | Candidate Decision And Implementation Readiness Scope |",
        "| 2 | Count Expression MVP Contract |",
        "| 3 | Count Expression Semantic MVP |",
        "| 4 | Count Expression IR Lowering MVP |",
        "| 5 | Count Expression SQL Lowering MVP |",
        "| 6 | Count Expression CLI / JSON / Golden Compatibility |",
        "| 7 | Count Family Boundary Regression Matrix |",
        "| 8 | Completion Audit And Status Lock |",
        "define an eight-slice Phase 39 roadmap",
    ):
        assert required in plan, required


def test_phase39_completion_status_and_ci_repair_handoff_are_locked() -> None:
    plan = _plan()

    for required in (
        "Phase 39 Slice 8 is Completion Audit And Status Lock",
        "docs/plan/static-audit/tests-only completion work",
        "Phase 39 is complete as an implementation-oriented 8-slice phase",
        "Slice 7 count-family boundary regression matrix is complete after CI repair",
        "Gate 3 remains responsible for final staging, commit, push, and natural CI `headSha` verification",
    ):
        assert required in plan, required

    for value in SLICE7_REPAIR_HANDOFF.values():
        assert value in plan, value
    assert (
        SLICE7_REPAIR_HANDOFF["repair_commit"]
        == SLICE7_REPAIR_HANDOFF["final_trusted_head"]
    )


def test_slice1_through_slice8_outcomes_remain_represented() -> None:
    evidence = _phase39_evidence()

    for required in (
        "Slice 1 candidate/readiness is complete",
        "Slice 2 `count(expression)` MVP contract is complete",
        "Slice 3 semantic MVP is complete",
        "Slice 4 IR lowering proof is complete",
        "Slice 5 PostgreSQL/private MySQL SQL lowering MVP is complete",
        "Slice 6 CLI/JSON/output compatibility is complete without fixture/golden additions",
        "Slice 7 count-family boundary regression matrix is complete after CI repair",
        "Slice 8 completion audit/status lock is complete once Gate 3 records",
    ):
        assert required in evidence, required


def test_completed_count_family_acceptance_matrix_is_locked() -> None:
    evidence = _phase39_evidence()

    for required in (
        "`count()`",
        "`count(field)` and `count(source.field)`",
        "supported direct `count(Json/Bytes/UUID field)`",
        "narrow field-bearing `count(expression)`",
        "Bool expression count as SQL non-`NULL` expression-result count, not",
        "`count_if(predicate)`",
        "existing `count_distinct(field)`",
        "existing `count_distinct(lower/trim Text chain)`",
        "amount_tax = count(amount + tax)",
        "lowered = count(lower(status))",
        "active_expr = count(active and true)",
        "optional_active_expr = count(active or optional_active)",
        "unique_normalized = count_distinct(lower(trim(status)))",
        'COUNT(("amount" + "tax")) AS "amount_tax"',
        "COUNT((`active` AND TRUE)) AS `active_expr`",
    ):
        assert required in evidence, required


def test_rejected_and_deferred_count_family_boundaries_remain_locked() -> None:
    evidence = _phase39_evidence()

    for required in (
        "`count(1)`, `count(constant)`, and literal-only count expressions",
        "`count_if(predicate)`",
        "`count(Enum field)`",
        "`count(Any field)`",
        "broad `count_distinct(expression)`",
        "`min/max(expression)`",
        "aggregate filters",
        "post-aggregate expressions",
        "`RelationLayerIR`",
        "JOIN/fanout-aware semantics",
        "runtime/database execution",
        "public MySQL API expansion",
        "value = count(1)",
        "value = count(anything)",
        "value = count(enum_status)",
        "value = count_distinct(amount + tax)",
        "value = count(distinct id)",
        "value = count(amount) filter where amount > 0",
    ):
        assert required in evidence, required


def test_slice8_preserves_public_surfaces_package_and_release_boundaries() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    plan = _plan()

    for required in (
        "no source/compiler behavior change in Slice 8",
        "no semantic, IR, SQL, CLI, or JSON implementation change in Slice 8",
        "no grammar/generated change in Slice 8",
        "no fixtures/goldens change in Slice 8",
        "`scripts/check_goldens.py` remains green",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation",
        "no release workflow",
        "no manual workflow run and no `gh workflow run`",
    ):
        assert required in plan, required

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    lowered = plan.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered, forbidden


def test_forbidden_surfaces_are_unchanged_or_untracked_in_slice8() -> None:
    diff_paths = set(
        filter(
            None,
            _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS).splitlines(),
        )
    )
    status_paths = {
        _status_path(line)
        for line in _git_status_for(FORBIDDEN_DIFF_PATHS).splitlines()
        if line
    }

    assert (
        diff_paths <= ALLOWED_PHASE40_SLICE3_REPAIR_CHANGED_PATHS
    ) or _phase54_active_gate2_is_active()
    assert (
        status_paths <= ALLOWED_PHASE40_SLICE3_REPAIR_CHANGED_PATHS
    ) or _phase54_active_gate2_is_active()


def test_changed_set_is_slice8_allowlist_or_clean_ci_checkout() -> None:
    status_paths = {_status_path(line) for line in _git_status()}

    assert (
        status_paths <= ALLOWED_PHASE40_SLICE3_REPAIR_CHANGED_PATHS
    ) or _phase54_active_gate2_is_active()

    for forbidden in FORBIDDEN_DIFF_PATHS:
        assert (
            not any(
                _path_matches(path, forbidden)
                and path not in ALLOWED_PHASE40_SLICE3_REPAIR_CHANGED_PATHS
                for path in status_paths
            )
        ) or _phase54_active_gate2_is_active()
