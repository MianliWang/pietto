from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-34-relationship-grain-narrow-join-mvp.md"
BOUNDARY_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-relationship-grain-narrow-join-boundary-v1.md"
)
GRAIN_SPEC_PATH = REPO_ROOT / "docs/spec/phase-34-relationship-grain-contract-v1.md"
JOIN_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-narrow-join-syntax-semantic-contract-v1.md"
)
READINESS_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-parser-ast-readiness-contract-v1.md"
)
SEMANTIC_SPEC_PATH = REPO_ROOT / "docs/spec/phase-34-semantic-readiness-contract-v1.md"
CANDIDATE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-first-implementation-candidate-decision-v1.md"
)
RESCOPE_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase-34-rescope-completion-candidate-decision-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/ast_nodes.py",
    "src/pietto/ast_builder.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/cli.py",
    "tests/fixtures",
    "tests/goldens",
    "scripts",
    "pyproject.toml",
    "uv.lock",
    ".github",
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


def test_phase34_plan_records_slice7_status_and_scope() -> None:
    plan = _normalized(PLAN_PATH)

    assert PLAN_PATH.is_file()
    for required in (
        "Phase 34 Slice 7 Re-scope / Completion Candidate Decision And Static "
        "Audit is the current docs/spec/static-audit/status-only candidate "
        "decision slice",
        "Proceed with Phase 34 Slice 7 as docs/spec/static-audit/status-only: "
        "re-scope Phase 34 completion language",
        "Slice 7 approved file scope is limited to",
        "`docs/spec/phase-34-rescope-completion-candidate-decision-v1.md`",
        "`tests/test_phase34_rescope_completion_candidate_decision.py`",
        "Slice 7 is the current docs/spec/static-audit/status-only candidate "
        "decision slice",
        "Phase 34 remains in progress and is not complete after Slice 7",
        "Slice 7 does not complete Phase 34 yet",
    ):
        assert required in plan, required


def test_rescope_contract_exists_and_records_completion_candidate() -> None:
    spec = _normalized(RESCOPE_SPEC_PATH)

    assert RESCOPE_SPEC_PATH.is_file()
    for required in (
        "This specification records the Phase 34 Slice 7 re-scope / completion "
        "candidate decision",
        "Slice 7 is docs/spec/static-audit/status-only work",
        "Phase 34 can later complete as a conservative relationship grain and "
        "narrow JOIN readiness/contracts foundation, not as a behavior MVP",
        "Phase 34 should be completed later as a relationship grain and narrow "
        "JOIN readiness/contracts foundation",
        "Phase 34 should not claim implemented JOIN or grain behavior",
        "The original behavior MVP remains future implementation deferred",
        "Slice 7 does not complete Phase 34 yet",
    ):
        assert required in spec, required


def test_slice1_through_slice6_delivery_summary_is_locked() -> None:
    spec = _normalized(RESCOPE_SPEC_PATH)

    for required in (
        "Phase 34 Slice 1 delivered the master plan",
        "Phase 34 Slice 2 delivered the relationship grain contract vocabulary",
        "Phase 34 Slice 3 delivered the narrow JOIN source-shape and semantic contract",
        "Phase 34 Slice 4 delivered parser/AST readiness requirements",
        "Phase 34 Slice 5 delivered semantic readiness requirements",
        "Phase 34 Slice 6 delivered the first implementation candidate decision",
        "Slice 1 through Slice 6 delivered a readiness/contracts foundation, "
        "not implemented JOIN or grain behavior",
    ):
        assert required in spec, required


def test_actual_implementation_surfaces_remain_deferred() -> None:
    spec = _normalized(RESCOPE_SPEC_PATH)

    for required in (
        "Actual relationship grain syntax",
        "JOIN syntax",
        "parser/AST behavior",
        "semantic validation",
        "IR/SQL lowering",
        "CLI/JSON/project behavior",
        "runtime/database behavior",
        "release operations remain deferred",
        "actual narrow JOIN parser/AST implementation is not approved yet",
        "No safe implementation path exists after Slice 6",
    ):
        assert required in spec, required


def test_least_misleading_completion_statement_is_exact() -> None:
    spec = _read(RESCOPE_SPEC_PATH)

    assert (
        "Phase 34 Relationship Grain And Narrow JOIN readiness foundation is "
        "complete as docs/spec/static-audit/status-only work. The original "
        "behavior MVP remains future implementation deferred."
    ) in spec


def test_current_behavior_preservation_is_locked() -> None:
    spec = _normalized(RESCOPE_SPEC_PATH)

    for required in (
        "Unsupported join-like syntax remains unsupported",
        "Relationship metadata remains metadata-only",
        "Relationship metadata is not lowered to Semantic IR or SQL",
        "Current single-input relation behavior remains unchanged",
        "`RelationIR` remains single-source",
        "PostgreSQL/MySQL render one `FROM` input",
        "CLI JSON v1 is unchanged",
        "Project JSON v2 is unchanged",
        "Semantic Metadata Artifact v1 is unchanged",
    ):
        assert required in spec, required


def test_phase33_project_json_boundaries_remain_preserved() -> None:
    spec = _normalized(RESCOPE_SPEC_PATH)

    for required in (
        "`pietto check --project ROOT` remains root/config-only",
        "project source selection remains deferred",
        "TOML schema parsing remains deferred",
        "glob expansion remains deferred",
        "project source parsing remains deferred",
        "multi-file semantic analysis remains deferred",
        "project JSON v2 remains check root/config-only",
        "project emit-sql remains rejected",
        "project explain remains rejected",
        "project metadata aggregation remains deferred",
        "single-file `pietto check --format json` remains JSON v1",
        "single-file `pietto emit-sql --format json` remains JSON v1",
        "single-file `pietto explain --format json` remains Semantic Metadata "
        "Artifact v1",
    ):
        assert required in spec, required


def test_completion_audit_housekeeping_is_deferred() -> None:
    spec = _normalized(RESCOPE_SPEC_PATH)
    plan = _normalized(PLAN_PATH)

    for required in (
        "A later completion audit/status lock slice may verify",
        "README, AGENTS, and `docs/spec/pietto-v0.9.md` updates are deferred "
        "unless separately approved",
    ):
        assert required in spec, required
    assert (
        "README, AGENTS, and `docs/spec/pietto-v0.9.md` status updates are "
        "deferred to a later completion audit slice unless separately approved"
    ) in plan


def test_explicit_non_goals_and_implementation_boundary_are_locked() -> None:
    spec = _normalized(RESCOPE_SPEC_PATH)

    for required in (
        "grammar changes",
        "generated parser changes",
        "AST changes",
        "parser behavior changes",
        "semantic model changes",
        "semantic validation",
        "diagnostic code additions",
        "IR changes",
        "SQL backend changes",
        "CLI behavior changes",
        "JSON v1 or JSON v2 behavior changes",
        "Semantic Metadata Artifact v1 changes",
        "fixtures/goldens changes",
        "scripts changes",
        "package metadata/dependency/workflow changes",
        "JOIN implementation",
        "JOIN syntax implementation",
        "grain syntax implementation",
        "grain semantic storage",
        "This spec does not change grammar, generated files, AST, parser "
        "behavior, semantic model, semantic validation, diagnostics, IR, SQL, "
        "CLI, JSON, fixtures, goldens, scripts, package metadata, "
        "dependencies, workflows, public API, project behavior, runtime "
        "behavior, or database behavior",
        "This spec does not define final JOIN syntax, final grain syntax, "
        "final AST fields/classes, diagnostic codes, IR shape, or SQL lowering",
    ):
        assert required in spec, required


def test_forbidden_implementation_surfaces_are_not_modified() -> None:
    diff_output = _git_diff_name_only(FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""


def test_package_version_and_release_boundaries_remain_locked() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    combined = _phase34_docs()

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert "Package version remains `0.1.0`" in combined
    assert "no tag/release/publish/upload/signing/attestation occurred" in combined
    assert "No tag/release/publish/upload/signing/attestation is performed" in combined

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in combined.lower(), forbidden


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _phase34_docs() -> str:
    return " ".join(
        _normalized(path)
        for path in (
            PLAN_PATH,
            BOUNDARY_SPEC_PATH,
            GRAIN_SPEC_PATH,
            JOIN_SPEC_PATH,
            READINESS_SPEC_PATH,
            SEMANTIC_SPEC_PATH,
            CANDIDATE_SPEC_PATH,
            RESCOPE_SPEC_PATH,
        )
    )


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
