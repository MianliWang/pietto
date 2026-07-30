from __future__ import annotations

from pathlib import Path
import subprocess

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-47-direct-row-schema-mvp.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase47-direct-row-schema-scope-lock-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE47_TEST_PATHS = (
    "tests/test_phase47_direct_row_schema_scope_lock.py",
    "tests/test_phase47_private_row_schema_scaffold.py",
    "tests/test_phase47_source_row_schema_propagation.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_qualified_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase47_unknown_direct_field_diagnostics.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase47_project_json_privacy_hardening.py",
    "tests/test_phase47_completion_audit.py",
)

ALLOWED_SLICE11_GATE2_PATHS = {
    "docs/plan/phase-47-direct-row-schema-mvp.md",
    "docs/spec/phase47-direct-row-schema-scope-lock-v1.md",
    "tests/test_phase47_completion_audit.py",
    "tests/test_phase47_direct_row_schema_scope_lock.py",
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


def _phase47_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_phase47_route_is_complete_and_all_slices_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    for relative_path in PHASE47_TEST_PATHS:
        assert (REPO_ROOT / relative_path).is_file(), relative_path

    docs = _phase47_docs()
    for required in (
        "Phase 47 Direct Row Schema MVP is complete after Slice 11",
        "Slice 11 is docs/tests/static-audit/status-lock work only",
        "final Gate 3 natural CI proof",
        "1. Candidate/scope lock only - complete",
        "2. Route expansion and downstream readiness lock - complete",
        "3. Private row schema carrier scaffold - complete",
        "4. Source shape fields to source row schema - complete",
        "5. Direct bare field projections from direct source inputs - complete",
        "6. Qualified direct field projections: `source.field` - complete",
        "7. Direct field rename projections: `alias = field` - complete",
        "8. Unknown direct field diagnostics and deterministic ordering - complete",
        "9. Downstream readiness hardening for Phase 48-50 - complete",
        "10. Project JSON/private-fact privacy and compatibility hardening - complete",
        "11. Completion audit/status lock - complete",
    ):
        assert required in docs, required


def test_phase47_delivered_private_row_schema_inventory_is_locked() -> None:
    docs = _phase47_docs()

    for required in (
        "project-private direct row schema facts only",
        "`ProjectRowFieldNullability`",
        "`ProjectRowFieldProvenanceKind`",
        "`ProjectRowFieldProvenance`",
        "`ProjectRowField`",
        "`ProjectRowSchema`",
        "`ProjectSemanticModel.source_row_schemas`",
        "`ProjectSemanticModel.relation_row_schemas`",
        "private carrier inventory",
    ):
        assert required in docs, required


def test_phase47_direct_source_schema_behavior_matrix_is_locked() -> None:
    docs = _phase47_docs()

    for required in (
        "Source row schema propagation is complete for resolved source shape fields",
        "source field order",
        "resolved project type facts",
        "project-private nullability",
        "original `FieldDef`",
        "Direct-source ungrouped relation row schemas are complete",
        "bare direct fields such as `id`",
        "qualified direct fields such as `users.id`",
        "renamed bare fields such as `user_id = id`",
        "renamed qualified fields such as `user_id = users.id`",
        "Mixed direct field select order is preserved",
        "preserve type, nullability, and `FieldDef` facts",
        "`SOURCE_FIELD` and `DIRECT_PROJECTION` provenance",
    ):
        assert required in docs, required


def test_phase47_unknown_direct_field_and_duplicate_boundary_is_locked() -> None:
    docs = _phase47_docs()

    for required in (
        "Unknown direct field references use existing semantic diagnostics flow",
        "`PIE-S2102`",
        "Duplicate output names remain private unknown schemas without diagnostics",
        "Grouped relations skip direct relation row schema population",
        "preserve Phase 50 aggregate/grouped output-schema deferral",
    ):
        assert required in docs, required


def test_phase47_json_privacy_and_public_surface_boundary_is_locked() -> None:
    docs = _phase47_docs()

    for required in (
        "Project JSON v2 privacy and compatibility are locked",
        "Project JSON v2 key order and shape remain unchanged",
        "private row schema facts remain un-serialized",
        "private relation graph and cycle facts remain un-serialized",
        "existing top-level `diagnostics[]`",
        "public project semantic API",
        "Project JSON v2 shape change",
        "private semantic fact serialization",
    ):
        assert required in docs, required


def test_phase47_phase48_50_deferred_boundaries_are_locked() -> None:
    docs = _phase47_docs()

    for required in (
        "Phase 48 query-to-query row schema propagation",
        "Phase 49 computed alias schema",
        "Phase 49 `let` schema",
        "Phase 50 aggregate/grouped output schema",
        "query-to-query row schema propagation",
        "computed aliases",
        "`let` schema",
        "aggregate output schema",
        "grouped result schema",
    ):
        assert required in docs, required


def test_phase47_forbidden_runtime_parser_sql_join_release_surfaces_remain_locked() -> (
    None
):
    docs = _phase47_docs()
    lowered_docs = docs.lower()

    for required in (
        "project IR",
        "project SQL emit",
        "project `emit-sql`",
        "project `explain`",
        "parser/grammar/generated changes",
        "single-file behavior changes",
        "JOIN/relationship behavior",
        "runtime/database execution",
        "package version, tag, release, publish, upload, signing, or attestation",
        "`src/**`",
        "`grammar/**`",
        "generated parser files",
        "`fixtures/**`",
        "`goldens/**`",
        "`scripts/**`",
        "`.github/**`",
        "`pyproject.toml`",
        "`uv.lock`",
    ):
        assert required in docs, required

    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered_docs, forbidden


def test_phase47_completion_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert (_git_diff_name_only(FORBIDDEN_DIFF_PATHS) == "") or _slice5_gate2()
    assert (
        _git_status_paths().issubset(ALLOWED_SLICE11_GATE2_PATHS)
    ) or _slice5_gate2()


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
