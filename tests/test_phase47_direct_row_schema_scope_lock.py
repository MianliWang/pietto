from __future__ import annotations

import subprocess
from pathlib import Path

from _static_audit_helpers import git_diff_name_only
from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-47-direct-row-schema-mvp.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase47-direct-row-schema-scope-lock-v1.md"
PHASE46_PLAN_PATH = REPO_ROOT / "docs/plan/phase-46-project-semantic-continuation.md"
PHASE46_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase46-project-semantic-continuation-scope-lock-v1.md"
)
ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-roadmap-phase45-60-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_PHASE47_ROUTE_LOCK_GATE2_PATHS = {
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


def test_phase47_identity_selected_candidate_and_slice1_scope_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _docs()
    for required in (
        "Phase 47",
        "Direct Row Schema MVP",
        "Direct Row Schema MVP candidate/scope lock only",
        "A. Phase 47 Slice 1 candidate/scope lock only",
        "Slice 1 is docs/spec/static-audit",
        "implements no source behavior",
        "no private row schema carrier scaffold",
        "no source row schema propagation",
        "no table/query output schema propagation",
        "no projection/body validation",
        "no CLI behavior",
        "no Project JSON v2 behavior",
        "no IR, no SQL",
        "Package version remains `0.1.0`",
    ):
        assert required in docs, required

    for rejected in (
        "B. Phase 47 Slice 1 candidate/scope lock",
        "+ private row schema carrier scaffold",
        "C. Phase 47 Slice 1 direct row schema MVP implementation",
        "behavior belongs to later bounded slices",
    ):
        assert rejected in docs, rejected


def test_phase47_slice2_route_expansion_scope_is_locked() -> None:
    docs = _docs()

    for required in (
        "Phase 47 Slice 2 is Route Expansion And Downstream Readiness Lock",
        "Slice 2 is docs/spec/static-audit",
        "additive route update",
        "B. Add Phase 47 Slice 2 Gate 2 route expansion/static-audit update",
        "expands Phase 47 to an eleven-slice route",
        "without implementing behavior",
        "without amending, rebasing, resetting, or rewriting Slice 1 history",
        "no private row schema carrier scaffold",
        "no source row schema propagation",
        "no table/query output schema propagation",
        "no unknown field diagnostics implementation",
        "no query-to-query propagation",
        "no computed aliases",
        "no `let` schema",
        "no aggregate output schema",
        "no CLI behavior",
        "no Project JSON v2 behavior",
        "no IR, no SQL",
        "no project `emit-sql`",
        "no project `explain`",
    ):
        assert required in docs, required


def test_phase47_predecessor_evidence_and_roadmap_supersession_are_locked() -> None:
    docs = _docs()
    phase46_docs = " ".join(
        _normalized(path) for path in (PHASE46_PLAN_PATH, PHASE46_SPEC_PATH)
    )
    roadmap = _read(ROADMAP_PATH)

    for required in (
        "Direct row schema propagation is deferred to Phase 47",
        "Row schema propagation is deferred to Phase 47",
        "Phase 47 entry direction is direct row schema MVP candidate work only",
    ):
        assert required in phase46_docs, required

    assert "47 | Project Semantic Metadata Artifact" in roadmap

    for required in (
        "Phase 46 is the authoritative current predecessor for Phase 47",
        "older `docs/spec/pietto-roadmap-phase45-60-v1.md` row",
        "`Project Semantic Metadata Artifact`",
        "superseded",
        "Direct Row Schema scope lock",
        "This Slice 1 does not edit that older roadmap document",
    ):
        assert required in docs, required


def test_future_private_row_schema_boundary_is_locked() -> None:
    docs = _docs()

    for required in (
        "project-private row schema facts only",
        "private to `src/pietto/_project/model.py`",
        "frozen, slots-based",
        "independent from the single-file `pietto.semantic` row schema classes",
        "`ProjectEffectiveNullability`",
        "`ProjectRowField.name`",
        "`ProjectRowField.resolved_type`",
        "`ProjectRowField.nullability`",
        "`ProjectRowField.field_def`",
        "`ProjectRowField.provenance` or an equivalent private origin slot",
        "`ProjectRowSchema.fields`",
        "`ProjectRowSchema.is_unknown`",
        "`ProjectSemanticModel.source_row_schemas`",
        "`ProjectSemanticModel.relation_row_schemas`",
        "must not reuse single-file `pietto.semantic.RowSchema`",
        "project checks do not call the single-file semantic analyzer",
        "planned private carrier concepts, not Slice 2 implementation",
        "private provenance or origin structure",
    ):
        assert required in docs, required


def test_source_and_direct_projection_scope_decisions_are_locked() -> None:
    docs = _docs()

    for required in (
        "Source definitions should get row schemas from resolved source shape fields",
        "source order from the referenced `ShapeDef.fields`",
        "resolved project type fact",
        "explicit nullability as project-private nullability",
        "original `FieldDef` owner",
        "bare `field`",
        "`source.field` when the qualifier matches",
        "separate bounded behavior slice",
        "qualifier matches the table/query",
        "direct source inputs",
        "Unknown direct field references",
        "`PIE-S2102` as the preferred existing diagnostic candidate",
        "final diagnostic code, message, and location policy must be confirmed",
        "behavior slice Gate 1 before implementation",
        "`ProjectSemanticResult.diagnostics`",
        "existing top-level semantic diagnostics path",
        "Project JSON v2 shape must not change",
    ):
        assert required in docs, required


def test_phase47_alias_direct_rename_boundary_is_locked() -> None:
    docs = _docs()

    for required in (
        "`alias = field` is a direct field rename",
        "user_id = id",
        "preserves the input field type",
        "nullability",
        "provenance",
        "differs from bare `field`",
        "differs from a computed alias such as `total = price + tax`",
        "late bounded slice after bare and qualified direct fields",
        "`alias = source.field` may be considered",
        "after qualified direct fields are complete",
        "computed aliases remain deferred",
    ):
        assert required in docs, required


def test_phase47_downstream_readiness_without_behavior_is_locked() -> None:
    docs = _docs()

    for required in (
        "Phase 47 may include readiness for Phase 48 query-to-query row schema",
        "must not implement query-to-query propagation behavior",
        "future downstream relation schemas can be stored without refactor",
        "relation row schema mappings should be deterministic",
        "Phase 48 remains the behavior phase",
        "Phase 47 may include readiness for Phase 49 computed alias schema",
        "let-bound expression schema",
        "must not implement computed aliases or `let` schema behavior",
        "future expression-derived fields",
        "No expression type inference is authorized in Phase 47",
        "Phase 47 may include readiness for Phase 50 aggregate output schema",
        "grouped result schema",
        "must not implement aggregate or grouped output schema behavior",
        "Row schema, nullability, and type vocabulary should not block",
        "Aggregate output schema remains Phase 50 or later",
        "No aggregate schema behavior is authorized in Phase 47",
    ):
        assert required in docs, required


def test_phase47_explicit_deferrals_and_future_route_are_locked() -> None:
    docs = _docs()

    for required in (
        "`alias = field` before its late bounded Phase 47 direct rename slice",
        "computed aliases",
        "expression typing for project relation bodies",
        "same-`select` alias reuse",
        "projection aliases as reusable bindings",
        "`let` schema",
        "aggregate output schema",
        "grouped result schema",
        "`where`, `order by`, `limit`, or `satisfying` body validation",
        "Query-to-query row schema propagation behavior should be Phase 48",
        "project IR",
        "project SQL",
        "project `emit-sql`",
        "project `explain`",
        "relationship-driven query behavior",
        "1. Candidate/scope lock only",
        "2. Route expansion and downstream readiness lock",
        "3. Private row schema carrier scaffold",
        "4. Source shape fields to source row schema",
        "5. Direct bare field projections from direct source inputs",
        "6. Qualified direct field projections: `source.field`",
        "7. Direct field rename projections: `alias = field`",
        "8. Unknown direct field diagnostics and deterministic ordering",
        "9. Downstream readiness hardening for Phase 48-50",
        "10. Project JSON/private-fact privacy and compatibility hardening",
        "11. Completion audit/status lock",
        "Phase 47 Direct Row Schema MVP is complete after Slice 11",
        "Slice 11 is docs/tests/static-audit/status-lock work only",
        "final Gate 3 natural CI proof",
    ):
        assert required in docs, required


def test_phase47_json_public_surface_and_validation_contract_are_locked() -> None:
    docs = _docs()

    for required in (
        "Future private row schema facts must not be serialized into Project JSON v2",
        "CLI JSON v1",
        "Semantic Metadata Artifact v1",
        "public Python APIs",
        "Project JSON v2 shape must remain unchanged",
        "existing top-level `diagnostics[]` field",
        "`cli_errors[]` remains project/config/source-selection/source-read only",
        "`inputs[]` and `result.check` remain read/parse based",
        "git diff --check",
        "git diff --no-index --check -- /dev/null tests/test_phase47_completion_audit.py || true",
        "uv run ruff format --check tests/test_phase47_completion_audit.py tests/test_phase47_direct_row_schema_scope_lock.py",
        "uv run ruff check tests/test_phase47_completion_audit.py tests/test_phase47_direct_row_schema_scope_lock.py",
        "uv run pyright --project pyrightconfig.tests.json",
        "uv run pytest tests/test_phase47_completion_audit.py tests/test_phase47_direct_row_schema_scope_lock.py",
    ):
        assert required in docs, required


def test_phase47_forbidden_surfaces_package_and_dirty_paths_are_locked() -> None:
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
        "`docs/spec/pietto-v0.9.md`",
        "`docs/spec/pietto-roadmap-phase45-60-v1.md`",
        "`src/pietto/cli.py`",
        "`src/pietto/_project/json_v2.py`",
        "`src/pietto/_project/model.py`",
        "`src/pietto/_project/check.py`",
        "Gate 2 must not implement any source/compiler behavior",
        "tag, release, publish, upload, signing, or attestation behavior",
    ):
        assert required in docs, required

    assert (
        git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS) == ""
    ) or _slice5_gate2()
    assert (
        _git_status_paths().issubset(ALLOWED_PHASE47_ROUTE_LOCK_GATE2_PATHS)
    ) or _slice5_gate2()


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
