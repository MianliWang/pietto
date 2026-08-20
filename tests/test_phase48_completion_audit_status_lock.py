from __future__ import annotations

from pathlib import Path
import tomllib

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-48-query-to-query-row-schema.md"
SPEC_PATH = REPO_ROOT / "docs/spec/phase48-completion-audit-status-lock-v1.md"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
ROADMAP_PATH = REPO_ROOT / "docs/spec/pietto-roadmap-phase45-60-v1.md"
PIETTO_V09_PATH = REPO_ROOT / "docs/spec/pietto-v0.9.md"
PROJECT_MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"

PHASE48_SLICE_NAMES = (
    "Candidate/scope lock and route plan",
    "Deterministic propagation order and cycle-blocking contract",
    "Private schema availability state carrier and propagation readiness",
    "Table-to-table / table-to-query propagation",
    "Query-to-query and multi-hop propagation",
    "Propagated field provenance / lineage hardening",
    "Upstream unknown / absent / deferred / blocked schema propagation",
    "Downstream diagnostics and deterministic ordering hardening",
    "Project JSON/private-fact privacy plus future explain/bridge readiness",
    "Completion audit/status lock",
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

PRECLAIMED_GATE3_SUCCESS = (
    "Slice 10 Gate 3 natural CI succeeded",
    "Slice 10 commit has been pushed",
    "Phase 48 is complete after Slice 10 Gate 2",
    "Gate 3 natural CI has already succeeded",
)


def _phase48_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_completion_spec_exists_and_is_linked_from_plan() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 48 Slice 10 is Completion audit/status lock",
        "`docs/spec/phase48-completion-audit-status-lock-v1.md`",
        "docs/spec/tests-only",
        "No other file is approved in Slice 10 Gate 2",
    ):
        assert required in f"{plan} {spec}", required


def test_phase48_ten_slice_inventory_is_locked() -> None:
    docs = _phase48_docs()

    assert "Phase 48 is Query-to-query Row Schema Propagation" in docs
    assert "Phase 48 is a full ten-slice phase" in docs
    for slice_name in PHASE48_SLICE_NAMES:
        assert slice_name in docs, slice_name

    assert "Phase 48 is complete only after Slice 10 Gate 3" in docs
    assert "natural CI success" in docs


def test_phase48_delivered_private_row_schema_inventory_is_locked() -> None:
    docs = _phase48_docs()
    model_source = _read(PROJECT_MODEL_PATH)

    for required in (
        "ProjectRelationRowSchemaStatus",
        "ProjectRelationRowSchemaReason",
        "ProjectRelationRowSchemaState",
        "relation_row_schema_states",
        "concrete relation-to-relation row schema propagation",
        "table-to-table",
        "table-to-query",
        "query-to-query",
        "table-from-query",
        "mixed acyclic multi-hop",
        "`id`",
        "`upstream.id`",
        "`alias = id`",
        "`alias = upstream.id`",
        "`UNKNOWN`",
        "`DEFERRED`",
        "`BLOCKED`",
        "provenance / lineage hardening",
        "Project JSON/private-fact privacy",
    ):
        assert required in docs, required

    for required in (
        "class ProjectRelationRowSchemaStatus",
        "class ProjectRelationRowSchemaReason",
        "class ProjectRelationRowSchemaState",
        "relation_row_schema_states: Mapping",
        "def _build_project_relation_row_schemas",
    ):
        assert required in model_source, required


def test_flat_schema_diagnostics_and_json_privacy_boundaries_are_locked() -> None:
    docs = _phase48_docs()

    for required in (
        "flat relation schema model",
        "only the immediate upstream qualifier is valid",
        "original source lineage and lineage-path selectors remain invalid",
        "`PIE-S2102`",
        "`PIE-S2301`",
        "`PIE-S2302`",
        "adds no new diagnostics",
        "changes no diagnostic wording",
        "Project JSON v2 top-level shape remains unchanged",
        "no public row schema/state JSON",
        "No private Phase 48 row schema fact is serialized into Project JSON v2",
        "private status values",
        "private reason values",
        "provenance facts",
        "relation graph facts",
        "cycle facts",
        "deterministic private ordering facts",
    ):
        assert required in docs, required


def test_phase48_deferred_boundaries_are_locked() -> None:
    docs = _phase48_docs()

    for required in (
        "computed alias schema",
        "`let` expression schema",
        "aggregate/grouped output schema",
        "project IR",
        "project SQL emit",
        "project `emit-sql`",
        "project `explain`",
        "public project semantic API",
        "Project JSON v2 row schema output",
        "private fact serialization",
        "parser/grammar/generated changes",
        "JOIN/relationship behavior",
        "runtime/database execution",
        "Phase 49 computed alias / `let` schema remains a candidate next phase",
        "Phase 50 aggregate/grouped output row schema remains a candidate future phase",
        "Phase 51-55 readiness labels remain tentative",
        "Phase 52 remains Project Explain / Project Semantic Metadata Readiness",
        "distinct from existing single-file `pietto explain`",
    ):
        assert required in docs, required


def test_package_release_and_gate3_preclaim_boundaries_are_locked() -> None:
    docs = _phase48_docs()
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    assert project["version"] == "0.1.0"
    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)
    assert "Package version remains `0.1.0`" in docs
    assert "performs no package version change, tag, release, publish, upload" in docs

    lowered_docs = docs.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered_docs, forbidden
    for forbidden in PRECLAIMED_GATE3_SUCCESS:
        assert forbidden not in docs, forbidden
