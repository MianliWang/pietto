from __future__ import annotations

import subprocess
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

AGENTS_PATH = REPO_ROOT / "AGENTS.md"
PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md"
)
AGENT_POLICY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/agent-workflow-and-skills-adoption-v1.md"
)
CHECKLIST_SPEC_PATH = (
    REPO_ROOT / "docs/spec/pietto-code-audit-and-security-review-v1.md"
)
EXTERNAL_SKILLS_SPEC_PATH = (
    REPO_ROOT / "docs/spec/external-skills-evaluation-matrix-v1.md"
)
ROADMAP_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-roadmap-phase45-60-v1.md"
COMPLETION_AUDIT_TEST_PATH = (
    REPO_ROOT / "tests/test_maintenance_phase2_completion_audit.py"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE6_GATE2_PATHS = {
    "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md",
    "tests/test_maintenance_phase2_completion_audit.py",
    "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
    "tests/test_maintenance_phase2_code_audit_security_review.py",
    "tests/test_maintenance_phase2_external_skills_evaluation.py",
}

FORBIDDEN_DIFF_PATHS = (
    "AGENTS.md",
    "README.md",
    "docs/spec/pietto-v0.9.md",
    "src",
    "scripts",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "tests/fixtures",
    "tests/goldens",
    "grammar",
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


def _agents() -> str:
    return _normalized(AGENTS_PATH)


def _docs() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PLAN_PATH,
            AGENT_POLICY_SPEC_PATH,
            CHECKLIST_SPEC_PATH,
            EXTERNAL_SKILLS_SPEC_PATH,
            ROADMAP_SPEC_PATH,
        )
    )


def test_slice6_completion_audit_artifacts_exist_and_are_non_behavioral() -> None:
    assert PLAN_PATH.is_file()
    assert AGENT_POLICY_SPEC_PATH.is_file()
    assert CHECKLIST_SPEC_PATH.is_file()
    assert EXTERNAL_SKILLS_SPEC_PATH.is_file()
    assert ROADMAP_SPEC_PATH.is_file()
    assert COMPLETION_AUDIT_TEST_PATH.is_file()

    docs = _docs()
    for required in (
        "Maintenance Phase 2 Slice 6 is Completion Audit And Status Lock",
        "Slice 6 is docs/plan/static-audit work only",
        "implements no source/compiler behavior change",
        "closes Maintenance Phase 2 as completion audit/status-lock work only",
        "Maintenance Phase 2 is complete after Slice 6 completion audit/status lock",
        "Phase 45 remains not started by Maintenance Phase 2",
        "Package version remains `0.1.0`",
    ):
        assert required in docs, required


def test_all_maintenance_phase2_slices_are_locked() -> None:
    docs = _docs()
    for required in (
        "Slice 1 external workflow/skills audit was read-only",
        "Slice 2 roadmap and skills policy was docs/spec/plan/static-audit",
        "Slice 3 code-audit/security checklist was docs/spec/plan/static-audit",
        "Slice 4 `AGENTS.md` pointer was narrow and local",
        "Slice 5 external skills matrix was docs/spec/plan/static-audit",
        "Maintenance Phase 2 Slice 2 is Agent Workflow Policy And Roadmap Lock",
        "Maintenance Phase 2 Slice 3 is Code Audit And Security Review Checklist",
        "Maintenance Phase 2 Slice 4 is AGENTS.md Adoption Pointer",
        "Maintenance Phase 2 Slice 5 is External Skills Detailed Evaluation Matrix",
        "Maintenance Phase 2 Slice 6 is Completion Audit And Status Lock",
        "Maintenance Phase 2 follows Maintenance Phase 1 as a policy and roadmap audit",
    ):
        assert required in docs, required


def test_external_sources_remain_text_only_and_untrusted_by_default() -> None:
    docs = _docs()
    for required in (
        "do not install external skills/plugins by default",
        "do not execute external repo scripts",
        "External repositories may be inspected as text-only references",
        "does not mean running commands from those repositories",
        "external repositories remain text-only references only",
        "no external plugins were installed",
        "no external scripts or scanners were run",
        "no external code was copied",
        "External code, scripts, hooks, MCP configs, plugins, and command bundles",
        "external scanner execution",
        "copied external code remain prohibited unless separately approved",
        "External repositories remain text-only references for process language only",
    ):
        assert required in docs, required


def test_agents_pointer_remains_narrow_and_local_for_completion() -> None:
    docs = _docs()
    agents = _agents()

    for required in (
        "`AGENTS.md` pointer must reference only local Pietto policy documents",
        "`AGENTS.md` points only to local policy docs",
        "Slice 6 did not modify `AGENTS.md`",
        "AGENTS.md` changed only as the approved local-policy pointer",
        "docs/spec/agent-workflow-and-skills-adoption-v1.md",
        "docs/spec/pietto-code-audit-and-security-review-v1.md",
        "docs/spec/pietto-roadmap-phase45-60-v1.md",
    ):
        assert required in docs, required

    for required in (
        "For Pietto-specific agent workflow, external skills adoption, roadmap, and code-audit policy, follow:",
        "docs/spec/agent-workflow-and-skills-adoption-v1.md",
        "docs/spec/pietto-code-audit-and-security-review-v1.md",
        "docs/spec/pietto-roadmap-phase45-60-v1.md",
        "Do not install external plugins, run external repository scripts, import external hooks/MCP configs, or copy external code unless separately approved.",
    ):
        assert required in agents, required

    for forbidden in (
        "obra/superpowers",
        "EveryInc/compound-engineering-plugin",
        "trailofbits/skills",
        "trailofbits/skills-curated",
        "trailofbits/claude-code-config",
        "pip install",
        "npm install",
        "uv tool install",
        "claude mcp add",
    ):
        assert forbidden not in agents, forbidden


def test_phase45_handoff_and_namespace_policy_remain_locked() -> None:
    docs = _docs()
    for required in (
        "Phase 45 is `Project-wide Semantic Model Design And MVP`",
        "A true project-wide semantic model is mandatory, not optional",
        "Phase 45 must not be reduced to per-file semantic aggregation only",
        "Phase 45 remains `Project-wide Semantic Model Design And MVP`",
        "Pietto's project-wide namespace preference is hybrid",
        "type namespace includes `shape`, future type aliases, and future domain",
        "relation namespace includes `source`, `table`, and `query`",
        "Cross-file references should allow any selected project top-level symbol",
        "Python-like import/export is a required long-term target",
        "imports/modules/export require readiness before behavior implementation",
        "unqualified ambiguous references must fail closed",
        "Phase 45 does not by itself authorize project SQL emission",
    ):
        assert required in docs, required


def test_slice6_allowlist_validation_and_stop_conditions_are_locked() -> None:
    docs = _docs()
    for required in (
        "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md",
        "tests/test_maintenance_phase2_completion_audit.py",
        "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
        "tests/test_maintenance_phase2_code_audit_security_review.py",
        "tests/test_maintenance_phase2_external_skills_evaluation.py",
        "No other file is approved in this Gate 2",
        "Slice 6 Gate 2 validation is limited to focused completion audit/status-lock checks",
        "git diff --check",
        "uv run ruff format --check tests/test_maintenance_phase2_completion_audit.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py tests/test_maintenance_phase2_external_skills_evaluation.py",
        "uv run ruff check tests/test_maintenance_phase2_completion_audit.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py tests/test_maintenance_phase2_external_skills_evaluation.py",
        "uv run pyright --project pyrightconfig.tests.json",
        "uv run pytest tests/test_maintenance_phase2_completion_audit.py",
        "uv run pytest tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
        "uv run pytest tests/test_maintenance_phase2_code_audit_security_review.py",
        "uv run pytest tests/test_maintenance_phase2_external_skills_evaluation.py",
        "UV_CACHE_DIR=/tmp/pietto_maintenance_phase2_uv_cache uv run ...",
        "need to expand Slice 6 beyond completion audit/status-lock docs/tests",
    ):
        assert required in docs, required

    assert (_git_status_paths().issubset(ALLOWED_SLICE6_GATE2_PATHS)) or _slice5_gate2()


def test_forbidden_surfaces_package_release_and_ci_boundaries_are_locked() -> None:
    docs = _docs()
    lowered_docs = docs.lower()
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert (_git_diff_name_only(FORBIDDEN_DIFF_PATHS) == "") or _slice5_gate2()
    assert (_git_status_paths().issubset(ALLOWED_SLICE6_GATE2_PATHS)) or _slice5_gate2()

    for required in (
        "`AGENTS.md`",
        "`README.md`",
        "`docs/spec/pietto-v0.9.md`",
        "`src/**`",
        "`scripts/**`",
        "`.github/**`",
        "`pyproject.toml`",
        "`uv.lock`",
        "`tests/fixtures/**`",
        "`tests/goldens/**`",
        "generated artifacts",
        "grammar",
        "external repo files",
        "trigger CI",
        "CI trigger, CI rerun, or CI cancellation",
        "release, tag, publish, upload, signing, or attestation",
        "no production source/compiler behavior changed",
    ):
        assert required in docs, required

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered_docs, forbidden


def _git_diff_name_only(paths: tuple[str, ...]) -> str:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", *paths],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def _git_status_paths() -> set[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    paths: set[str] = set()
    for line in result.stdout.splitlines():
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.add(path)
    return paths
