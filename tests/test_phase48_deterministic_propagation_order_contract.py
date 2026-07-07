from __future__ import annotations

from pathlib import Path
import subprocess

from _static_audit_helpers import git_diff_name_only
from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-48-query-to-query-row-schema.md"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase48-deterministic-propagation-order-cycle-blocking-contract-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE2_GATE2_PATHS = {
    "docs/plan/phase-48-query-to-query-row-schema.md",
    "docs/spec/phase48-deterministic-propagation-order-cycle-blocking-contract-v1.md",
    "tests/test_phase48_deterministic_propagation_order_contract.py",
}

FORBIDDEN_DIFF_PATHS = (
    "src",
    "grammar",
    "fixtures",
    "goldens",
    "tests/fixtures",
    "tests/golden",
    "scripts",
    ".github",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
    "docs/spec/pietto-roadmap-phase45-60-v1.md",
)


def _docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_slice2_contract_document_exists_and_is_linked_from_plan() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _docs()
    for required in (
        "Phase 48 Slice 2",
        "Deterministic propagation order and cycle-blocking contract",
        "`docs/spec/phase48-deterministic-propagation-order-cycle-blocking-contract-v1.md`",
        "Slice 2 adds no public Project JSON v2 keys",
        "actual private carrier implementation belongs to Slice 3",
        "No other file is approved in Slice 2 Gate 2",
    ):
        assert required in docs, required


def test_deterministic_ordering_contract_is_locked() -> None:
    docs = _docs()

    for required in (
        "Canonical relation order is the parsed project input order followed by definition order",
        "definition order within each parsed input",
        "dependency-first for acyclic `TableDef | QueryDef` relations",
        "Source-backed direct-source relations are propagation seeds",
        "Multi-hop propagation must preserve upstream-before-downstream ordering",
        "canonical relation order is the tie-breaker",
        "private relation fact ordering",
        "deterministic diagnostics",
        "must not rely on incidental dictionary order",
    ):
        assert required in docs, required


def test_graph_edge_direction_requires_explicit_propagation_handling() -> None:
    docs = _docs()

    for required in (
        "dependent relation -> dependency relation",
        "Future propagation must invert that direction or account for it explicitly",
        "not itself a ready-to-use propagation order",
    ):
        assert required in docs, required


def test_cycle_and_unresolved_relations_are_blocked_without_new_diagnostics() -> None:
    docs = _docs()

    for required in (
        "existing `PIE-S2301`",
        "existing `PIE-S2302`",
        "Existing unresolved relation diagnostics remain authoritative",
        "Existing cycle diagnostics remain authoritative",
        "future private `BLOCKED`",
        "cycle members as blocked before attempting to propagate concrete schemas",
        "Concrete schemas must not be propagated for cycle members",
        "Slice 2 adds no new diagnostic code",
        "adds no new diagnostics",
    ):
        assert required in docs, required


def test_private_availability_vocabulary_remains_planned_only() -> None:
    docs = _docs()

    for required in (
        "`CONCRETE`",
        "`UNKNOWN`",
        "`DEFERRED`",
        "`BLOCKED`",
        "`ProjectRelationRowSchemaState`",
        "status: CONCRETE | UNKNOWN | DEFERRED | BLOCKED",
        "schema: ProjectRowSchema | None",
        "reason: private enum/string",
        "planned private vocabulary only",
        "actual private carrier implementation belongs to Slice 3",
    ):
        assert required in docs, required


def test_public_surface_and_deferred_behavior_boundaries_are_locked() -> None:
    docs = _docs()

    for required in (
        "Project JSON v2 top-level shape remains unchanged",
        "adds no public Project JSON v2 keys",
        "Private row schema facts",
        "private schema availability facts",
        "must not be serialized",
        "no parser, grammar, generated parser artifact",
        "no project IR",
        "no project SQL emit",
        "no project `emit-sql`",
        "no project `explain`",
        "no public project semantic API",
        "no JOIN/relationship behavior",
        "computed alias schema",
        "`let` schema",
        "aggregate/grouped schema",
    ):
        assert required in docs, required


def test_downstream_readiness_labels_are_tentative_not_roadmap_edits() -> None:
    docs = _docs()

    for required in (
        "The numbered readiness labels below are tentative Phase 48-local planning labels",
        "They do not amend the older global Phase 45-60 roadmap",
        "do not authorize the named downstream behaviors",
    ):
        assert required in docs, required


def test_phase48_slice2_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS) == ""
    assert _git_status_paths().issubset(ALLOWED_SLICE2_GATE2_PATHS)


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
