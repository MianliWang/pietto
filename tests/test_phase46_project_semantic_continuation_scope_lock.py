from __future__ import annotations

import subprocess
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-46-project-semantic-continuation.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase46-project-semantic-continuation-scope-lock-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE1_GATE2_PATHS = {
    "docs/plan/phase-46-project-semantic-continuation.md",
    "docs/spec/phase46-project-semantic-continuation-scope-lock-v1.md",
    "tests/test_phase46_project_semantic_continuation_scope_lock.py",
}

FORBIDDEN_DIFF_PATHS = (
    "src",
    "grammar",
    "fixtures",
    "goldens",
    "scripts",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "AGENTS.md",
)


def _docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_phase46_identity_selected_direction_and_slice1_scope_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _docs()
    for required in (
        "Phase 46",
        "Project Semantic Continuation",
        "Candidate/scope lock + private relation dependency graph scaffold + very narrow relation cycle detection MVP",
        "C. Candidate/scope lock + dependency graph scaffold",
        "narrow A. Cycle detection MVP",
        "continues the private project semantic model built in Phase 45",
        "Slice 1 is docs/spec/static-audit",
        "does not implement the dependency graph scaffold",
        "does not collect relation dependency edges",
        "does not select a cycle diagnostic code",
        "does not detect cycles",
        "Package version remains `0.1.0`",
    ):
        assert required in docs, required


def test_phase46_private_graph_vocabulary_and_edge_boundary_are_locked() -> None:
    docs = _docs()
    for required in (
        "private relation dependency graph",
        "A relation node is a stable project relation definition",
        "A relation edge is a private dependency",
        "A dependency source is the syntax site",
        "A cycle candidate is a deterministic relation-node path",
        "A cycle diagnostic is a project semantic diagnostic",
        "table/query relation symbols",
        "existing table/query `from` relation dependencies",
        "no JOIN edges",
        "no relationship metadata edges",
        "no inferred/schema edges",
        "no row-schema propagation edges",
        "no projection/body field-reference edges",
        "does not authorize CTE expansion",
        "project IR",
        "project SQL",
    ):
        assert required in docs, required


def test_phase46_determinism_cycle_mvp_and_deferrals_are_locked() -> None:
    docs = _docs()
    for required in (
        "selected project input order remains stable and project-relative",
        "relation symbol ordering remains stable",
        "relation edge ordering remains stable",
        "cycle candidate ordering remains stable",
        "diagnostic ordering remains deterministic",
        "diagnostic locations remain project-relative",
        "detecting relation cycles among table/query `from` dependencies",
        "block later row schema propagation",
        "Phase 46 does not compute row schemas",
        "Row schema propagation is deferred to Phase 47",
        "row schema propagation deferred to Phase 47",
        "projection/body validation deferred",
        "query-to-query row schema propagation deferred",
        "computed aliases deferred",
        "`let` schema deferred",
        "aggregate output schema deferred",
        "project explain/metadata deferred",
        "relationship/JOIN deferred",
        "parser/grammar/generated changes forbidden",
    ):
        assert required in docs, required


def test_phase46_json_private_fact_and_public_surface_rules_are_locked() -> None:
    docs = _docs()
    for required in (
        "must not change Project JSON v2 shape",
        "existing top-level `diagnostics[]` field",
        "Private graph state",
        "private relation nodes",
        "private relation edges",
        "must not be serialized into Project JSON v2",
        "adds no public project semantic API",
        "does not expose graph nodes",
        "Semantic Metadata Artifact v1",
        "public Python APIs",
        "fixtures",
        "goldens",
        "single-file behavior changes",
        "runtime/database execution behavior",
    ):
        assert required in docs, required


def test_phase46_slice_route_allowlist_and_validation_are_locked() -> None:
    docs = _docs()
    for required in (
        "1. Candidate decision and scope lock",
        "2. Private relation dependency graph scaffold",
        "3. Relation edge collection from existing table/query `from` dependencies",
        "4. Deterministic cycle detection MVP",
        "5. Text-mode project semantic diagnostics",
        "6. JSON v2 diagnostics through existing `diagnostics[]`",
        "7. Compatibility hardening",
        "8. Completion audit/status lock",
        "Phase 46 Slice 1 Gate 2 is limited to:",
        "docs/plan/phase-46-project-semantic-continuation.md",
        "docs/spec/phase46-project-semantic-continuation-scope-lock-v1.md",
        "tests/test_phase46_project_semantic_continuation_scope_lock.py",
        "No other file is approved in this Gate 2",
        "git diff --check",
        "uv run ruff format --check tests/test_phase46_project_semantic_continuation_scope_lock.py",
        "uv run ruff check tests/test_phase46_project_semantic_continuation_scope_lock.py",
        "uv run pyright --project pyrightconfig.tests.json",
        "uv run pytest tests/test_phase46_project_semantic_continuation_scope_lock.py",
    ):
        assert required in docs, required

    assert _git_status_paths().issubset(ALLOWED_SLICE1_GATE2_PATHS)


def test_phase46_forbidden_surfaces_package_and_release_boundaries_are_locked() -> None:
    docs = _docs()
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject

    for required in (
        "`src/**`",
        "`grammar/**`",
        "generated parser files",
        "`fixtures/**`",
        "`goldens/**`",
        "`scripts/**`",
        "`.github/**`",
        "`pyproject.toml`",
        "`uv.lock`",
        "`README*`",
        "`AGENTS*`",
        "`src/pietto/cli.py`",
        "`src/pietto/_project/json_v2.py`",
        "`src/pietto/_project/model.py`",
        "`src/pietto/_project/check.py`",
        "relation cycle detection implementation",
        "dependency graph implementation",
        "row schema implementation",
        "private semantic facts serialized into JSON",
        "Project JSON v2 shape change",
        "package version changes",
        "tag, release, publish, upload, signing, or attestation behavior",
    ):
        assert required in docs, required

    assert _git_diff_name_only(FORBIDDEN_DIFF_PATHS) == ""
    assert _git_status_paths().issubset(ALLOWED_SLICE1_GATE2_PATHS)


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
        ["git", "status", "--short"],
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
