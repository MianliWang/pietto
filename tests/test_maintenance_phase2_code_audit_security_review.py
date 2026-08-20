from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

AGENTS_PATH = REPO_ROOT / "AGENTS.md"
CHECKLIST_SPEC_PATH = (
    REPO_ROOT / "docs/spec/pietto-code-audit-and-security-review-v1.md"
)
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
            CHECKLIST_SPEC_PATH,
            AGENT_POLICY_SPEC_PATH,
            EXTERNAL_SKILLS_SPEC_PATH,
            PLAN_PATH,
        )
    )


def test_slice3_artifacts_exist_and_remain_non_behavioral() -> None:
    assert CHECKLIST_SPEC_PATH.is_file()
    assert AGENT_POLICY_SPEC_PATH.is_file()
    assert PLAN_PATH.is_file()

    docs = _docs()
    for required in (
        "Maintenance Phase 2 Slice 3",
        "Code Audit And Security Review Checklist",
        "docs/spec/static-audit work only",
        "implements no behavior change",
        "implements no source/compiler behavior change",
        "does not install external plugins",
        "run external scripts",
        "copy external code",
        "run scanners",
        "modify `AGENTS.md`",
        "Package version remains `0.1.0`",
    ):
        assert required in docs, required


def test_review_posture_and_finding_discipline_are_locked() -> None:
    docs = _docs()
    for required in (
        "evidence-first",
        "exact claim",
        "trust boundary",
        "source-to-sink data flow",
        "validation points",
        "sink",
        "expected impact",
        "confirmed issue",
        "false positive",
        "robustness issue",
        "deferred design risk",
        "report only claims supported by concrete evidence",
        "A dangerous-looking operation is not a confirmed issue",
        "False-positive handling should document the reason for rejection",
        "missing attacker control",
        "existing validation",
        "fail-closed diagnostics",
        "future-only design status",
    ):
        assert required in docs, required


def test_pietto_security_audit_surface_matrix_is_complete() -> None:
    docs = _docs()
    for required in (
        "Path traversal / root containment",
        "Source selection / glob policy",
        "TOML config parsing",
        "UTF-8 / source-read boundaries",
        "Parser diagnostics and location paths",
        "Project JSON v2 schema stability",
        "CLI JSON v1 separation",
        "Semantic Metadata Artifact v1 separation",
        "Semantic / IR / SQL boundaries",
        "Generated / golden / fixture changes",
        "Dependency / workflow / lockfile / package metadata changes",
        "Release / tag / publish / signing / attestation boundaries",
        "External plugin / script prohibition",
        "symlinks, hard links, aliases",
        "unsupported glob forms rejected rather than ignored",
        "unknown keys, duplicate TOML keys/tables",
        "source-read and UTF-8 failures",
        "normalized project-relative paths",
        "without adding SQL, metadata, graph, runtime, database, or release data",
        "single-file `check` and `emit-sql` remain in CLI JSON v1",
        "single-file `explain` remain Semantic Metadata Artifact v1",
        "faithful selected-dialect SQL lowering",
    ):
        assert required in docs, required


def test_external_audit_practices_remain_text_only_and_local() -> None:
    docs = _docs()
    for required in (
        "Trail of Bits-style review practices are useful as text-only process",
        "Compound Engineering-style security review personas are useful as text-only",
        "`obra/superpowers` planning and review habits are useful only as local process ideas",
        "None of these sources are trusted automation for Pietto by default",
        "External code, scripts, hooks, MCP configs, package manifests, scanner rules",
        "must not be imported, installed, or executed",
        "local Pietto checklist",
        "not an imported external skill, plugin, scanner, hook, MCP config, or script bundle",
    ):
        assert required in docs, required


def test_slice4_agents_pointer_preserves_code_audit_policy() -> None:
    docs = _docs()
    agents = _agents()

    for required in (
        "Maintenance Phase 2 Slice 4 is AGENTS.md Adoption Pointer",
        "Slice 4 adopts the already-locked local policies into `AGENTS.md`",
        "`docs/spec/pietto-code-audit-and-security-review-v1.md`",
        "Slice 4 does not copy external framework instructions into `AGENTS.md`",
        "mention external installation commands",
        "add external script/hook/MCP setup instructions",
        "broaden agent authority",
        "No other file is approved in this Gate 2",
    ):
        assert required in docs, required

    for required in (
        "For Pietto-specific agent workflow, external skills adoption, roadmap, and code-audit policy, follow:",
        "docs/spec/pietto-code-audit-and-security-review-v1.md",
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


def test_slice5_external_skills_matrix_preserves_code_audit_policy() -> None:
    assert EXTERNAL_SKILLS_SPEC_PATH.is_file()

    docs = _docs()
    agents = _agents()

    for required in (
        "Maintenance Phase 2 Slice 5 is External Skills Detailed Evaluation Matrix",
        "docs/spec/external-skills-evaluation-matrix-v1.md",
        "Trail of Bits-style code-audit practices worth translating locally",
        "threat-model-lite before expanding behavior",
        "source-to-sink evidence before security claims",
        "false-positive discipline",
        "scanner humility: zero findings from tools or review are inconclusive",
        "supply-chain and dependency review as a policy surface",
        "without running dependency scanners by default",
        "path/config/source-read/resource review",
        "external scanner execution",
        "does not install external plugins",
        "execute external repo scripts",
        "copy external code",
        "import hooks",
        "import MCP configs",
        "change `AGENTS.md`",
    ):
        assert required in docs, required

    assert "docs/spec/external-skills-evaluation-matrix-v1.md" not in agents


def test_slice6_completion_audit_preserves_code_audit_policy() -> None:
    docs = _docs()
    agents = _agents()

    for required in (
        "Maintenance Phase 2 Slice 6 is Completion Audit And Status Lock",
        "tests/test_maintenance_phase2_completion_audit.py",
        "Slice 6 records that Maintenance Phase 2 is complete",
        "Slice 3 code-audit/security checklist was docs/spec/plan/static-audit",
        "no external scripts or scanners were run",
        "no external code was copied",
        "external repositories remain text-only references only",
        "no production source/compiler behavior changed",
        "Slice 6 did not modify `AGENTS.md`",
        "Phase 45 remains not started by Maintenance Phase 2",
    ):
        assert required in docs, required

    assert "docs/spec/external-skills-evaluation-matrix-v1.md" not in agents


def test_forbidden_surfaces_package_release_and_ci_boundaries_are_locked() -> None:
    docs = _docs()
    lowered_docs = docs.lower()
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject

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
        "external repo files under `/tmp/pietto_maintenance_phase2_external_repos/**`",
        "trigger CI",
        "release, tag, publish, upload, signing, or attestation",
        "AGENTS.md` changed only as the approved local-policy pointer",
    ):
        assert required in docs, required

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered_docs, forbidden
