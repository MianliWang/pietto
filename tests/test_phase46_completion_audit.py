from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-46-project-semantic-continuation.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase46-project-semantic-continuation-scope-lock-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PROJECT_MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
PROJECT_CHECK_PATH = REPO_ROOT / "src/pietto/_project/check.py"
PROJECT_JSON_V2_PATH = REPO_ROOT / "src/pietto/_project/json_v2.py"
CLI_PATH = REPO_ROOT / "src/pietto/cli.py"

PHASE46_TEST_PATHS = (
    "tests/test_phase46_project_semantic_continuation_scope_lock.py",
    "tests/test_phase46_project_relation_dependency_graph_scaffold.py",
    "tests/test_phase46_project_relation_dependency_edge_collection.py",
    "tests/test_phase46_project_relation_cycle_detection.py",
    "tests/test_phase46_project_relation_cycle_diagnostics.py",
    "tests/test_phase46_project_json_v2_relation_cycle_diagnostics.py",
    "tests/test_phase46_project_compatibility_hardening.py",
    "tests/test_phase46_completion_audit.py",
)

PRIVATE_GRAPH_FACT_MARKERS = (
    "ProjectRelationDependencyGraph",
    "ProjectRelationDependencyNode",
    "ProjectRelationDependencyEdge",
    "ProjectRelationDependencySource",
    "ProjectRelationDependencyCycle",
    "relation_dependency_graph",
    "dependency_source",
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


def _phase46_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_phase46_slice_inventory_and_completion_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    for relative_path in PHASE46_TEST_PATHS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    docs = _phase46_docs()
    for required in (
        "Phase 46 Slice 8 is `Completion audit and status lock`",
        "Slice 8 is docs/tests/static-audit/status-lock only",
        "Phase 46 is complete after Slice 8 as `Project Semantic Continuation`",
        "Gate 3 commit, push, and natural CI proof handled outside this Gate 2",
        "1. Candidate decision and scope lock",
        "2. Private relation dependency graph scaffold",
        "3. Relation edge collection from existing table/query `from` dependencies",
        "4. Deterministic cycle detection MVP",
        "5. Text-mode project semantic diagnostics",
        "6. JSON v2 diagnostics through existing `diagnostics[]`",
        "7. Compatibility hardening",
        "8. Completion audit/status lock",
    ):
        assert required in docs, required


def test_phase46_delivered_behavior_boundary_is_locked() -> None:
    docs = _phase46_docs()

    for required in (
        "candidate decision and scope lock",
        "private relation dependency graph scaffold",
        "relation edge collection from existing table/query `from` dependencies",
        "deterministic private relation cycle facts",
        "project relation cycle diagnostics through `PIE-S2302`",
        "Project JSON v2 relation cycle diagnostics compatibility through existing",
        "project compatibility hardening",
        "completion audit and status lock",
        "private-first and conservative",
        "Phase 45's private project semantic model boundary",
    ):
        assert required in docs, required


def test_private_relation_dependency_graph_boundary_remains_private() -> None:
    model_source = _read(PROJECT_MODEL_PATH)
    public_project_sources = "\n".join(
        _read(path) for path in (PROJECT_JSON_V2_PATH, PROJECT_CHECK_PATH, CLI_PATH)
    )
    docs = _phase46_docs()

    for required in (
        "class ProjectRelationDependencyNode",
        "class ProjectRelationDependencyEdge",
        "class ProjectRelationDependencySource",
        "class ProjectRelationDependencyCycle",
        "class ProjectRelationDependencyGraph",
        "relation_dependency_graph: ProjectRelationDependencyGraph",
        "def _build_project_relation_dependency_graph",
        "def _detect_project_relation_dependency_cycles",
        "def _build_project_relation_cycle_diagnostics",
        'code="PIE-S2302"',
    ):
        assert required in model_source, required

    for private_fact in PRIVATE_GRAPH_FACT_MARKERS:
        assert private_fact not in public_project_sources, private_fact

    for required in (
        "Private graph and cycle facts remain private and un-serialized",
        "Project JSON v2 does not expose `ProjectRelationDependencyGraph`",
        "`ProjectRelationDependencyCycle`",
        "`relation_dependency_graph`",
        "`cycles`",
        "graph nodes",
        "graph edges",
        "dependency sources",
    ):
        assert required in docs, required


def test_project_json_v2_and_diagnostics_completion_boundary_is_locked() -> None:
    docs = _phase46_docs()
    json_v2_source = _read(PROJECT_JSON_V2_PATH)
    slice6_source = _read(
        REPO_ROOT / "tests/test_phase46_project_json_v2_relation_cycle_diagnostics.py"
    )
    slice7_source = _read(
        REPO_ROOT / "tests/test_phase46_project_compatibility_hardening.py"
    )

    for required in (
        "Semantic diagnostics remain top-level `diagnostics[]`",
        "`cli_errors[]` remains project/config/source-selection/source-read only",
        "`inputs[]` and `result.check` remain read/parse based",
        "no semantic input statuses or semantic file counters are introduced",
        "Project JSON v2 shape",
    ):
        assert required in docs, required

    for required in (
        "semantic_diagnostics",
        '"ok": result.ok and not _has_error_diagnostics(semantic_diagnostics)',
        "diagnostics.extend(semantic_diagnostics)",
        '"cli_errors": [_cli_error_to_json_dict(error) for error in result.errors]',
        '"inputs": inputs',
        '"check": counters',
    ):
        assert required in json_v2_source, required

    for required in (
        "PROJECT_JSON_TOP_LEVEL_KEYS",
        '("PIE-S2302", "Relation cycle detected: first -> second -> first")',
        '"severity"',
        '"related_locations"',
        '"files_total": 1',
        'assert document["cli_errors"] == []',
        "assert tuple(document) == PROJECT_JSON_TOP_LEVEL_KEYS",
    ):
        assert required in f"{slice6_source}\n{slice7_source}", required


def test_project_and_single_file_output_boundaries_are_locked() -> None:
    docs = _phase46_docs()
    cli_source = _read(CLI_PATH)
    slice7_source = _read(
        REPO_ROOT / "tests/test_phase46_project_compatibility_hardening.py"
    )

    for required in (
        "Single-file `check`, CLI JSON v1, `emit-sql`, and `explain` remain separate and",
        "Project `emit-sql` and project `explain` remain unsupported or",
        "Slice 8 has no IR, SQL, project `emit-sql`, or project `explain` path",
    ):
        assert required in docs, required

    for required in (
        "def _run_check",
        "def _run_project_check",
        "def _run_emit_sql",
        "def _run_explain",
        "build_empty_project_semantic_result(parse_result)",
        "semantic_diagnostics=semantic_result.diagnostics",
    ):
        assert required in cli_source, required

    for required in (
        "test_single_file_surfaces_remain_separate_from_project_cycle_semantics",
        "test_project_emit_sql_and_explain_remain_rejected_without_cycle_leakage",
        "single-file surfaces must not build project semantics",
        "PIE-S2302",
    ):
        assert required in slice7_source, required


def test_phase46_non_goals_future_boundary_and_release_surfaces_are_locked() -> None:
    docs = _phase46_docs()
    pyproject = _read(PYPROJECT_PATH)
    lowered_docs = docs.lower()

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject

    for required in (
        "Slice 8 changes no row schema behavior",
        "projection/body validation",
        "query-to-query schema propagation",
        "computed alias schema",
        "`let` schema",
        "aggregate output schema",
        "project IR",
        "project SQL",
        "project `emit-sql`",
        "project `explain`",
        "public project semantic API",
        "private semantic fact serialization",
        "parser public API",
        "grammar",
        "generated parser artifact",
        "single-file behavior",
        "JOIN behavior",
        "relationship-driven query behavior",
        "runtime/database behavior",
        "fixture",
        "golden",
        "package version",
        "workflow",
        "dependency file",
        "tag, release, publish, upload, signing, or attestation behavior",
        "Phase 47 entry direction is direct row schema MVP candidate work only",
        "Phase 48 through Phase 50",
    ):
        assert required in docs, required

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered_docs, forbidden
