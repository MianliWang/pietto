from __future__ import annotations

import subprocess
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

MATRIX_SPEC_PATH = REPO_ROOT / "docs/spec/external-skills-evaluation-matrix-v1.md"
AGENT_POLICY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/agent-workflow-and-skills-adoption-v1.md"
)
CHECKLIST_SPEC_PATH = (
    REPO_ROOT / "docs/spec/pietto-code-audit-and-security-review-v1.md"
)
PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE5_GATE2_PATHS = {
    "docs/spec/external-skills-evaluation-matrix-v1.md",
    "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md",
    "tests/test_maintenance_phase2_external_skills_evaluation.py",
    "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
    "tests/test_maintenance_phase2_code_audit_security_review.py",
}

ALLOWED_SLICE6_GATE2_PATHS = {
    "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md",
    "tests/test_maintenance_phase2_completion_audit.py",
    "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
    "tests/test_maintenance_phase2_code_audit_security_review.py",
    "tests/test_maintenance_phase2_external_skills_evaluation.py",
}

ALLOWED_CURRENT_MAINTENANCE_PHASE2_GATE2_PATHS = (
    ALLOWED_SLICE5_GATE2_PATHS | ALLOWED_SLICE6_GATE2_PATHS
)

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


def _docs() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            MATRIX_SPEC_PATH,
            AGENT_POLICY_SPEC_PATH,
            CHECKLIST_SPEC_PATH,
            PLAN_PATH,
        )
    )


def test_slice5_artifacts_exist_and_remain_non_behavioral() -> None:
    assert MATRIX_SPEC_PATH.is_file()
    assert AGENT_POLICY_SPEC_PATH.is_file()
    assert CHECKLIST_SPEC_PATH.is_file()
    assert PLAN_PATH.is_file()

    docs = _docs()
    for required in (
        "Maintenance Phase 2 Slice 5",
        "External Skills Detailed Evaluation Matrix",
        "docs/spec/plan/static-audit work only",
        "implements no source/compiler behavior change",
        "does not install external plugins",
        "execute external repo scripts",
        "copy external code",
        "import hooks",
        "import MCP configs",
        "run scanners",
        "modify `AGENTS.md`",
        "Package version remains `0.1.0`",
    ):
        assert required in docs, required


def test_external_repo_snapshot_inventory_is_locked() -> None:
    docs = _docs()
    for required in (
        "`obra/superpowers`",
        "`d884ae0`",
        "| `obra/superpowers` | `d884ae0` | 14 |",
        "Multi-platform plugin manifests",
        "`EveryInc/compound-engineering-plugin`",
        "`d3f3529`",
        "35 local `SKILL.md`; README says 28 shipped skills",
        "autonomous `/lfg`, commit/push/PR/CI flows",
        "`trailofbits/skills`",
        "`cfe5d7b`",
        "| `trailofbits/skills` | `cfe5d7b` | 75 |",
        "static-analysis skills, SARIF workflows, some `.mcp.json` files",
        "`trailofbits/skills-curated`",
        "`022fa09`",
        "| `trailofbits/skills-curated` | `022fa09` | 27 |",
        "`trailofbits/claude-code-config`",
        "`7db11a2`",
        "| `trailofbits/claude-code-config` | `7db11a2` | 0 |",
        "MCP template, package/tool install guidance",
    ):
        assert required in docs, required


def test_external_evaluation_matrix_records_risk_and_text_only_borrowing() -> None:
    docs = _docs()
    for required in (
        "Full coding-agent methodology for Claude, Codex, Cursor, Kimi",
        "High: installs, session hooks, worktrees, subagents",
        "Socratic design refinement, chunked design approval",
        "Plugin install, hooks, worktree automation",
        "Compound Engineering workflow plugin across Claude, Codex",
        "High: `/lfg` commits, pushes, opens PRs, watches/fixes CI",
        "Plan/review loop, structured findings, scoped review personas",
        "`/lfg`, commit/push/PR skills, browser/CI automation",
        "Security-focused Claude marketplace compatible with Codex",
        "false-positive checks, static analysis, supply-chain review",
        "scanner/tool assumptions, Bash/Write/Edit tools",
        "Running Semgrep or CodeQL",
        "Reviewed/approved marketplace with security, development, research",
        "malicious hooks and backdoored skills",
        "Review every hook/script line",
        "converted deployment/GitHub automation, `openai-yeet`",
        "Opinionated Claude Code setup for sandboxing, permissions, hooks, MCP",
        "`--dangerously-skip-permissions`",
        "Treat project MCP as untrusted",
        "Copying settings, hooks, MCP templates",
    ):
        assert required in docs, required


def test_code_audit_security_practices_are_borrowed_as_local_process() -> None:
    docs = _docs()
    for required in (
        "threat-model-lite before expanding behavior",
        "assets, trust boundaries, entry points, attacker capabilities",
        "context building before findings",
        "source-to-sink evidence before security claims",
        "evidence-first findings with explicit verdicts",
        "false-positive discipline",
        "confirmed issue, false positive, robustness issue, and deferred design risk",
        "scanner humility: zero findings from tools or review are inconclusive",
        "supply-chain and dependency review as a policy surface",
        "without running dependency scanners by default",
        "path/config/source-read/resource review",
        "generated, golden, workflow, package metadata, release, tag, publish",
    ):
        assert required in docs, required


def test_pietto_local_adoption_strategy_and_next_slice_are_locked() -> None:
    docs = _docs()
    for required in (
        "Pietto should create and maintain local workflow and audit documents",
        "rather than importing external frameworks",
        "External repositories remain text-only references for process language only",
        "direct adoption risk must be recorded before any future change",
        "forbidden automation, config, code, hook, MCP, dependency, workflow",
        "external plugins, external repo scripts, external scanner execution",
        "`AGENTS.md` remains unchanged by Slice 5",
        "Maintenance Phase 2 should likely use one completion audit/status-lock slice",
        "Phase 45 remains `Project-wide Semantic Model Design And MVP`",
        "Slice 5 does not start Phase 45 behavior",
    ):
        assert required in docs, required


def test_slice6_completion_lock_preserves_external_skills_policy() -> None:
    docs = _docs()
    for required in (
        "Maintenance Phase 2 Slice 6 is Completion Audit And Status Lock",
        "tests/test_maintenance_phase2_completion_audit.py",
        "Slice 6 records that Maintenance Phase 2 is complete",
        "Slice 5 external skills matrix was docs/spec/plan/static-audit",
        "no external plugins were installed",
        "no external scripts or scanners were run",
        "no external code was copied",
        "external repositories remain text-only references only",
        "Phase 45 remains not started by Maintenance Phase 2",
        "Slice 6 did not modify `AGENTS.md`",
    ):
        assert required in docs, required

    assert (
        _git_status_paths().issubset(ALLOWED_CURRENT_MAINTENANCE_PHASE2_GATE2_PATHS)
    ) or _slice5_gate2()


def test_gate2_allowlist_validation_and_stop_conditions_are_locked() -> None:
    docs = _docs()
    for required in (
        "docs/spec/external-skills-evaluation-matrix-v1.md",
        "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md",
        "tests/test_maintenance_phase2_external_skills_evaluation.py",
        "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
        "tests/test_maintenance_phase2_code_audit_security_review.py",
        "No other file is approved in this Gate 2",
        "git diff --check",
        "uv run ruff format --check tests/test_maintenance_phase2_external_skills_evaluation.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py",
        "uv run ruff check tests/test_maintenance_phase2_external_skills_evaluation.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py",
        "uv run pyright --project pyrightconfig.tests.json",
        "uv run pytest tests/test_maintenance_phase2_external_skills_evaluation.py",
        "uv run pytest tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
        "uv run pytest tests/test_maintenance_phase2_code_audit_security_review.py",
        "UV_CACHE_DIR=/tmp/pietto_maintenance_phase2_slice5_uv_cache uv run ...",
        "Slice 6 Gate 2 validation is limited to focused completion audit/status-lock checks",
        "uv run ruff format --check tests/test_maintenance_phase2_completion_audit.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py tests/test_maintenance_phase2_external_skills_evaluation.py",
        "uv run ruff check tests/test_maintenance_phase2_completion_audit.py tests/test_maintenance_phase2_agent_workflow_and_roadmap.py tests/test_maintenance_phase2_code_audit_security_review.py tests/test_maintenance_phase2_external_skills_evaluation.py",
        "uv run pytest tests/test_maintenance_phase2_completion_audit.py",
        "any `src/**` change",
        "external plugin installation",
        "external script execution",
        "external scanner execution",
        "scope expansion beyond docs/spec/plan/static-audit files",
    ):
        assert required in docs, required

    assert (
        _git_status_paths().issubset(ALLOWED_CURRENT_MAINTENANCE_PHASE2_GATE2_PATHS)
    ) or _slice5_gate2()


def test_forbidden_surfaces_release_and_ci_boundaries_are_locked() -> None:
    docs = _docs()
    lowered_docs = docs.lower()
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert (_git_diff_name_only(FORBIDDEN_DIFF_PATHS) == "") or _slice5_gate2()
    assert (
        _git_status_paths().issubset(ALLOWED_CURRENT_MAINTENANCE_PHASE2_GATE2_PATHS)
    ) or _slice5_gate2()

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
        "release, tag, publish, upload, signing, or attestation",
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
