from __future__ import annotations

import subprocess
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

AGENTS_PATH = REPO_ROOT / "AGENTS.md"
ROADMAP_SPEC_PATH = REPO_ROOT / "docs/spec/pietto-roadmap-phase45-60-v1.md"
AGENT_POLICY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/agent-workflow-and-skills-adoption-v1.md"
)
EXTERNAL_SKILLS_SPEC_PATH = (
    REPO_ROOT / "docs/spec/external-skills-evaluation-matrix-v1.md"
)
PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE2_GATE2_PATHS = {
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
    "docs/spec/agent-workflow-and-skills-adoption-v1.md",
    "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md",
    "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
}

ALLOWED_MAINTENANCE_PHASE2_DIRTY_PATHS = ALLOWED_SLICE2_GATE2_PATHS | {
    "docs/spec/pietto-code-audit-and-security-review-v1.md",
    "tests/test_maintenance_phase2_code_audit_security_review.py",
}

ALLOWED_SLICE4_GATE2_PATHS = {
    "AGENTS.md",
    "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md",
    "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
    "tests/test_maintenance_phase2_code_audit_security_review.py",
}

ALLOWED_SLICE5_GATE2_PATHS = {
    "docs/spec/external-skills-evaluation-matrix-v1.md",
    "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md",
    "tests/test_maintenance_phase2_external_skills_evaluation.py",
    "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
    "tests/test_maintenance_phase2_code_audit_security_review.py",
}

ALLOWED_CURRENT_MAINTENANCE_PHASE2_GATE2_PATHS = (
    ALLOWED_MAINTENANCE_PHASE2_DIRTY_PATHS
    | ALLOWED_SLICE4_GATE2_PATHS
    | ALLOWED_SLICE5_GATE2_PATHS
)

FORBIDDEN_DIFF_PATHS = (
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
            ROADMAP_SPEC_PATH,
            AGENT_POLICY_SPEC_PATH,
            EXTERNAL_SKILLS_SPEC_PATH,
            PLAN_PATH,
        )
    )


def test_maintenance_phase2_slice2_artifacts_exist_and_are_non_behavioral() -> None:
    assert ROADMAP_SPEC_PATH.is_file()
    assert AGENT_POLICY_SPEC_PATH.is_file()
    assert PLAN_PATH.is_file()

    docs = _docs()
    for required in (
        "Maintenance Phase 2 Slice 2",
        "docs/spec/plan/static-audit work only",
        "implements no source/compiler behavior change",
        "authorizes no source/compiler behavior",
        "Package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation",
    ):
        assert required in docs, required


def test_agent_workflow_and_external_skills_policy_is_locked() -> None:
    docs = _docs()
    for required in (
        "Pietto must not install external skills or plugins by default",
        "Pietto must not execute external repository scripts by default",
        "Pietto must not copy external code, hooks, MCP configs, plugin manifests",
        "External repositories may be inspected as text-only references",
        "does not mean running commands from those repositories",
        "obra/superpowers",
        "EveryInc/compound-engineering-plugin",
        "trailofbits/skills",
        "trailofbits/skills-curated",
        "trailofbits/claude-code-config",
        "Pietto-specific workflow docs and checklists should be written locally",
        "Trail of Bits-style code audit practices are valuable",
        "External code, scripts, hooks, MCP configs, plugins, and command bundles",
        "Gate 1 is read-only planning",
        "Gate 2 is bounded implementation and focused validation",
        "Gate 3 is publish work only when separately approved",
        "`AGENTS.md` remains unchanged by default",
        "requires a separate approval after this docs/spec policy is locked",
        "Maintenance Phase 2 Slice 4 is AGENTS.md Adoption Pointer",
    ):
        assert required in docs, required


def test_slice3_code_audit_policy_extension_is_locked() -> None:
    docs = _docs()
    for required in (
        "Maintenance Phase 2 Slice 3 records the local Pietto checklist",
        "docs/spec/pietto-code-audit-and-security-review-v1.md",
        "not an imported external skill, plugin, scanner, hook, MCP config, or script bundle",
        "reviewers must trace concrete Pietto data flow",
        "distinguish confirmed issues from false positives",
        "robustness issues, and deferred design risks",
        "preserve the Gate 1 / Gate 2 / Gate 3 workflow",
        "Maintenance Phase 2 Slice 2 and Slice 3 perform no release operation",
    ):
        assert required in docs, required


def test_slice4_agents_pointer_is_narrow_and_local() -> None:
    docs = _docs()
    agents = _agents()

    for required in (
        "Maintenance Phase 2 Slice 4 is AGENTS.md Adoption Pointer",
        "docs/plan/static-audit plus one tiny `AGENTS.md` local-policy pointer only",
        "Slice 4 adopts the already-locked local policies into `AGENTS.md`",
        "`AGENTS.md` pointer must reference only local Pietto policy documents",
        "Slice 4 does not copy external framework instructions into `AGENTS.md`",
        "mention external installation commands",
        "add external script/hook/MCP setup instructions",
        "broaden agent authority",
        "No other file is approved in this Gate 2",
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

    assert _git_status_paths().issubset(ALLOWED_CURRENT_MAINTENANCE_PHASE2_GATE2_PATHS)


def test_slice5_external_skills_matrix_policy_is_locked() -> None:
    assert EXTERNAL_SKILLS_SPEC_PATH.is_file()

    docs = _docs()
    agents = _agents()
    for required in (
        "Maintenance Phase 2 Slice 5 is External Skills Detailed Evaluation Matrix",
        "docs/spec/plan/static-audit work only",
        "docs/spec/external-skills-evaluation-matrix-v1.md",
        "Slice 5 records the inspected external repo snapshots",
        "direct adoption risks",
        "safe text-only process practices",
        "forbidden adoption surfaces",
        "does not install external plugins",
        "execute external repo scripts",
        "run external scanners",
        "copy external code",
        "change `AGENTS.md`",
        "No other file is approved in this Gate 2",
    ):
        assert required in docs, required

    assert "docs/spec/external-skills-evaluation-matrix-v1.md" not in agents
    assert _git_status_paths().issubset(ALLOWED_CURRENT_MAINTENANCE_PHASE2_GATE2_PATHS)


def test_phase45_60_roadmap_and_phase45_target_are_locked() -> None:
    docs = _docs()
    for required in (
        "# Pietto Roadmap Phase 45-60 v1",
        "Phase 45 is `Project-wide Semantic Model Design And MVP`",
        "A true project-wide semantic model is mandatory, not optional",
        "Phase 45 must not be reduced to per-file semantic aggregation only",
        "| 45 | Project-wide Semantic Model Design And MVP |",
        "| 50 | Import / Module / Export Readiness |",
        "| 60 | Completion Audit And Status Lock |",
        "A phase may use up to 12 slices when needed",
        "one deterministic project catalog over selected top-level definitions",
        "cross-file reference resolution over accepted project symbols",
        "project-level success/failure state that blocks later project IR/SQL",
        "Phase 45 does not by itself authorize project SQL emission",
    ):
        assert required in docs, required


def test_namespace_cross_file_and_ambiguity_preferences_are_locked() -> None:
    docs = _docs()
    for required in (
        "Pietto should use a hybrid namespace preference",
        "The type namespace includes:",
        "`shape`",
        "future type aliases",
        "future domain types",
        "The relation namespace includes:",
        "`source`",
        "`table`",
        "`query`",
        "Cross-file references should allow any selected project top-level symbol",
        "The file/module model is not final",
        "implicit project package model as an MVP stepping stone",
        "Python-like import/export remains a required long-term target",
        "Imports, modules, exports, aliases, visibility rules, and qualified names require readiness work",
        "non-strict mode may report a warning",
        "strict mode should report an error",
        "unqualified ambiguous references must fail closed",
        "Current fail-closed behavior may remain until warning infrastructure",
    ):
        assert required in docs, required


def test_language_precedent_and_malloy_cube_borrowing_policy_is_locked() -> None:
    docs = _docs()
    for required in (
        "Python, Go, Rust, and C++ namespace and module precedents are design context",
        "not implementation authority",
        "Python supports package/module import ergonomics",
        "Go favors explicit package boundaries",
        "Rust separates module visibility and name resolution",
        "C++ demonstrates the risk of complex namespace and lookup rules",
        "Malloy and Cube may be studied for concepts",
        "must not be copied as frameworks or behavior contracts",
        "semantic modeling units",
        "reusable measures and dimensions",
        "relationship and join modeling",
        "Pietto must keep its own Python-style indentation language",
    ):
        assert required in docs, required


def test_gate2_allowlist_validation_and_stop_conditions_are_locked() -> None:
    docs = _docs()
    for required in (
        "docs/spec/pietto-roadmap-phase45-60-v1.md",
        "docs/spec/agent-workflow-and-skills-adoption-v1.md",
        "docs/plan/maintenance-phase-2-agent-workflow-roadmap-and-skills-audit.md",
        "tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
        "No other file is approved in this Gate 2",
        "git diff --check",
        "uv run ruff format --check tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
        "uv run ruff check tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
        "uv run pyright --project pyrightconfig.tests.json",
        "uv run pytest tests/test_maintenance_phase2_agent_workflow_and_roadmap.py",
        "UV_CACHE_DIR=/tmp/pietto_maintenance_phase2_uv_cache uv run ...",
        "any `src/**` change",
        "any `AGENTS.md` change beyond the approved local-policy pointer",
        "external plugin installation",
        "external script execution",
        "copying external framework instructions into `AGENTS.md`",
        "scope expansion beyond docs/spec/plan/static-audit files",
    ):
        assert required in docs, required

    assert _git_status_paths().issubset(ALLOWED_CURRENT_MAINTENANCE_PHASE2_GATE2_PATHS)


def test_forbidden_surfaces_package_release_and_ci_boundaries_are_locked() -> None:
    docs = _docs()
    lowered_docs = docs.lower()
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert _git_diff_name_only(FORBIDDEN_DIFF_PATHS) == ""
    assert _git_status_paths().issubset(ALLOWED_CURRENT_MAINTENANCE_PHASE2_GATE2_PATHS)

    for required in (
        "`AGENTS.md`",
        "`README.md`",
        "`docs/spec/pietto-v0.9.md`",
        "`src/**`",
        "`scripts/**`",
        "`.github/**`",
        "`pyproject.toml`",
        "`uv.lock`",
        "external repo files under `/tmp/pietto_maintenance_phase2_external_repos/**`",
        "trigger CI",
        "implement Phase 45 behavior",
        "AGENTS.md` changed only as the approved local-policy pointer",
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
