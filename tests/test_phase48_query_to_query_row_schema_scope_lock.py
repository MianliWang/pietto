from __future__ import annotations

from pathlib import Path
import subprocess

from _static_audit_helpers import git_diff_name_only
from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-48-query-to-query-row-schema.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase48-query-to-query-row-schema-scope-lock-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE1_GATE2_PATHS = {
    "docs/plan/phase-48-query-to-query-row-schema.md",
    "docs/spec/phase48-query-to-query-row-schema-scope-lock-v1.md",
    "docs/spec/phase48-query-to-query-multi-hop-propagation-v1.md",
    "tests/test_phase48_query_to_query_row_schema_scope_lock.py",
    "src/pietto/_project/model.py",
    "tests/test_phase48_query_to_query_multi_hop_propagation.py",
    "tests/test_phase48_table_upstream_row_schema_propagation.py",
    "tests/test_phase48_schema_availability_state_carrier.py",
    "tests/test_phase47_downstream_readiness_hardening.py",
    "tests/test_phase47_qualified_field_row_schema.py",
    "tests/test_phase47_unknown_direct_field_diagnostics.py",
    "tests/test_phase47_direct_bare_field_row_schema.py",
    "tests/test_phase47_direct_field_rename_row_schema.py",
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
}

FORBIDDEN_DIFF_PATHS = (
    "src/pietto/_project/check.py",
    "src/pietto/_project/json_v2.py",
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
)


def _docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_phase48_identity_scope_and_route_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _docs()
    for required in (
        "Query-to-query Row Schema Propagation",
        "Phase 46 relation dependency graph and cycle diagnostics",
        "Phase 47 direct row schema carrier, source row schemas, and direct relation row schemas",
        "`ProjectSemanticModel.source_row_schemas`",
        "`ProjectSemanticModel.relation_row_schemas`",
        "`relation_resolutions`",
        "`relation_dependency_graph`",
        "existing `PIE-S2301`, `PIE-S2302`, and `PIE-S2102` diagnostics",
        "1. Candidate/scope lock and route plan",
        "2. Deterministic propagation order and cycle-blocking contract",
        "3. Private schema availability state carrier and propagation readiness",
        "4. Table-to-table / table-to-query propagation",
        "5. Query-to-query and multi-hop propagation",
        "6. Propagated field provenance / lineage hardening",
        "7. Upstream unknown / absent / deferred / blocked schema propagation",
        "8. Downstream diagnostics and deterministic ordering hardening",
        "9. Project JSON/private-fact privacy plus future explain/bridge readiness",
        "10. Completion audit/status lock",
        "The older five- or six-slice",
        "Future Pietto phases should default to eight to twelve slices",
    ):
        assert required in docs, required


def test_phase48_schema_availability_state_design_is_locked() -> None:
    docs = _docs()

    for required in (
        "schema availability design B",
        "`ProjectRelationRowSchemaState`",
        "status: CONCRETE | UNKNOWN | DEFERRED | BLOCKED",
        "schema: ProjectRowSchema | None",
        "reason: private enum/string",
        "`CONCRETE`",
        "`UNKNOWN`",
        "`DEFERRED`",
        "`BLOCKED`",
        "private target design only",
        "not Project JSON v2 output",
        "not public project semantic API",
        "does not implement the carrier",
    ):
        assert required in docs, required


def test_phase48_flat_relation_schema_and_qualifier_policy_are_locked() -> None:
    docs = _docs()

    for required in (
        "flat output schema",
        "immediate upstream relation name",
        "`id`",
        "`staged.id`",
        "`users.id` is invalid when `from staged`",
        "`staged.users.id` is unsupported",
        "not downstream query paths",
        "not be used to solve ambiguity",
    ):
        assert required in docs, required


def test_phase48_duplicate_and_ambiguity_policy_is_locked() -> None:
    docs = _docs()

    for required in (
        "Duplicate output names remain private `UNKNOWN` schemas without diagnostics",
        "Multi-source same-name fields must be disambiguated by upstream aliases",
        "`user_id = users.id`",
        "`event_id = events.id`",
        "`staged.user_id`",
        "`staged.event_id`",
        "not `staged.users.id`",
    ):
        assert required in docs, required


def test_phase48_mvp_behavior_matrix_is_locked() -> None:
    docs = _docs()

    for required in (
        "table-to-table propagation",
        "table-to-query propagation",
        "query-to-query propagation",
        "multi-hop propagation",
        "`id`",
        "`staged.id`",
        "`user_id = id`",
        "`user_id = staged.id`",
        "upstream `CONCRETE`",
        "upstream `UNKNOWN`",
        "upstream `DEFERRED`",
        "upstream `BLOCKED`",
    ):
        assert required in docs, required


def test_phase48_relation_graph_ordering_and_cycle_policy_are_locked() -> None:
    docs = _docs()

    for required in (
        "Parsed input order and definition order are canonical relation order",
        "Propagation should be dependency-first",
        "dependent relation -> dependency relation",
        "Topological traversal must use canonical parsed input and definition order",
        "Direct field diagnostics preserve parsed input order, definition order, and select item order",
        "avoid relying on incidental dict order",
        "existing `PIE-S2302`",
        "cycle members do not propagate schemas",
    ):
        assert required in docs, required


def test_phase48_diagnostics_and_unknown_schema_policy_are_locked() -> None:
    docs = _docs()

    for required in (
        "existing `PIE-S2102`",
        "existing `PIE-S2301`",
        "existing `PIE-S2302`",
        "missing downstream field over concrete upstream schema uses existing `PIE-S2102`",
        "downstream propagates `UNKNOWN` without new diagnostics",
        "downstream schema remains absent/deferred without new diagnostics",
        "downstream schema remains absent/blocked",
        "unresolved relation uses existing `PIE-S2301` only",
        "duplicate output names remain private `UNKNOWN` schema without `PIE-S2305`",
    ):
        assert required in docs, required


def test_phase48_downstream_phase51_55_readiness_matrix_is_locked() -> None:
    docs = _docs()

    for required in (
        "Downstream Phase 51-55 Readiness",
        "Phase 51 relationship/grain/fanout readiness",
        "Phase 52 Project Explain / Project Semantic Metadata Readiness",
        "distinct from existing single-file explain",
        "Phase 53 import/export and multi-file ergonomics",
        "Phase 54 JOIN candidate / narrow JOIN readiness",
        "Phase 55 external bridge / metadata export / RAG / Arrow readiness",
        "does not implement relationship behavior",
        "grain/fanout diagnostics",
        "Project explain output",
        "project semantic metadata artifact output",
        "import/export syntax",
        "JOIN behavior",
        "external metadata export",
        "RAG bridge",
        "Arrow/PyArrow bridge",
    ):
        assert required in docs, required


def test_phase48_deferred_boundaries_and_json_privacy_are_locked() -> None:
    docs = _docs()

    for required in (
        "computed alias schema",
        "`let` schema",
        "aggregate/grouped output schema",
        "project IR",
        "project SQL emit",
        "project `emit-sql`",
        "project `explain`",
        "Project JSON v2 row schema output",
        "private fact serialization",
        "Project JSON v2 top-level shape remains unchanged",
        "Private row schema facts",
        "private schema availability facts",
        "private relation graph facts",
        "Diagnostics flow only through existing `diagnostics[]`",
        "CLI/check orchestration remains unchanged",
    ):
        assert required in docs, required


def test_phase48_slice1_package_version_and_dirty_paths_are_locked() -> None:
    pyproject = _read(PYPROJECT_PATH)

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert (
        git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS) == ""
    ) or _slice5_gate2()
    assert (_git_status_paths().issubset(ALLOWED_SLICE1_GATE2_PATHS)) or _slice5_gate2()


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
