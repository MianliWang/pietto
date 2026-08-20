from __future__ import annotations

import tomllib
from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-50-semantic-readiness-consolidation.md"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase50-aggregate-grouped-project-output-schema-readiness-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

SLICE3_TITLE = (
    "# Phase 50 Slice 3 Aggregate / Grouped Project Output-Schema Readiness v1"
)
REPAIR_SHA = "5c66b00d20200d943f0b6e1d0c02813fba18904b"
ORIGINAL_SLICE2_SHA = "d35ed9a58d3fc4b81febbea8fa3540707cbcfde0"
REPAIR_SUBJECT = "Repair Phase 50 Slice 2 CI compatibility locks"

REQUIRED_SPEC_SECTIONS = (
    "Purpose And Authority",
    "Trusted Baseline",
    "Completed Foundations",
    "Current Aggregate / Grouped Language Surface",
    "Current Project Row-Schema Boundary",
    "Relation Forms In Scope",
    "Output-Field Identity Contract",
    "Group-Key Result Readiness",
    "Aggregate Result Readiness",
    "Type And Nullability Matrix",
    "Schema Availability-State Matrix",
    "Duplicate Output-Name Posture",
    "Origin And Provenance Readiness",
    "Dependency And Lineage Readiness",
    "Satisfying / Order / Limit Interaction",
    "Downstream Propagation And Qualification",
    "Phase 51 Bounded Handoff",
    "Explicit Deferrals",
    "Public And Runtime Non-goals",
    "Version And Release Boundary",
)

SCHEMA_STATES = ("CONCRETE", "UNKNOWN", "DEFERRED", "BLOCKED")


def _section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    remainder = text[start + len(f"## {heading}") :]
    next_offset = remainder.find("\n## ")
    return remainder if next_offset == -1 else remainder[:next_offset]


def test_slice3_artifacts_identity_baseline_and_current_status_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _read(SPEC_PATH)
    combined = f"{plan} {_normalized(SPEC_PATH)}"

    assert SLICE3_TITLE in spec
    for required in (
        REPAIR_SHA,
        ORIGINAL_SLICE2_SHA,
        REPAIR_SUBJECT,
        "29072890119",
        "CI / push",
        "completed / success",
        "5317 passed",
    ):
        assert required in combined, required

    for required in (
        "Phase 50 Slice 1 **Roadmap Reconciliation And Strategic Scope Lock** completed",
        "Phase 50 Slice 2 **Post-v0.2 Deferred Inventory And Phase 50-60 Replan** completed",
        "Phase 50 Slice 3 **Aggregate / Grouped Project Output-Schema Readiness** completed",
        "7bd50022859a5e3d202c26d67bed1a723388048a",
        "29082580976",
        "Phase 50 Slice 4 **Type-System Gap And Capability Readiness** completed",
        "aaf30fcd2ec4b19f6d0c23783067c369a11cd27b",
        "29097916311",
        "Phase 50 Slice 5 **Window-Function Readiness** completed",
        "d79c5c422cb7f54ae5e5587694e49389536419cb",
        "29115612846",
        "Phase 50 Slice 6 **Import / Module / Export Readiness** completed",
        "7c7f6976dd67ccc4628757f2d857b593f71f5e0f",
        "29139545163",
        "Phase 50 Slice 7 **Semantic Package Model Readiness** completed",
        "a5bc07855a0994343475ba546504e64b16fc7e63",
        "29141663534",
        "Phase 50 Slice 8 **PostgreSQL Extension Capability Readiness** completed",
        "9e2c0f0ddcc2047e35985e6b97daa8bf29979914",
        "29157374991",
        "Slice 8 completed",
        "Phase 50 Slice 9 **Multi-dialect Capability Ecosystem Readiness** completed",
        "f886589ac2f64eeb3770c914e7c049e2da105daa",
        "29170827348",
        "Slice 9 completed",
        "Phase 50 Slice 10 **Explain / Public Metadata / Package Integration Boundary** completed",
        "9bc6ed82f3741e3c242981bb88edfb50c73fc586",
        "29179160024",
        "Phase 50 Slice 11 **Completion Audit And Status Lock** is the current",
        "Slice 11 is not complete in Gate 2",
        "Phase 50 remains in progress through Gate 2",
        "Phases 51 through 60 remain unstarted and separately authorized",
        "Phase 53 remains `READINESS_CONTRACT_ONLY`",
        "Phase 54 remains readiness-only and unstarted",
        "Phase 55 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 56 remains unstarted",
        "Phase 57 remains `READINESS_CONTRACT_ONLY`, readiness-only, and unstarted",
        "Phase 58 remains readiness-only and unstarted",
        "Phase 60 remains readiness-only and unstarted",
    ):
        assert required in plan, required


def test_spec_section_order_and_no_behavior_authority_are_locked() -> None:
    spec = _read(SPEC_PATH)
    offsets = [spec.index(f"## {section}") for section in REQUIRED_SPEC_SECTIONS]

    assert offsets == sorted(offsets)
    assert "Slice 3 implements no compiler or runtime behavior." in spec
    for required in (
        "readiness work",
        "not complete in Gate 2",
        "Phase 51 Aggregate / Grouped Project Output-Schema Foundation has not started",
        "Every future implementation remains separately authorized",
        "designs no public schema, public metadata, or public API",
    ):
        assert required in _normalized(SPEC_PATH), required


def test_current_aggregate_surface_and_type_nullability_matrix_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    type_matrix = _section(_read(SPEC_PATH), "Type And Nullability Matrix")
    normalized_type_matrix = " ".join(type_matrix.split())

    for required in (
        "`count()`",
        "`count(field)`",
        "bounded `count(expression)`",
        "`count_distinct`",
        "`sum` / `avg`",
        "`min` / `max`",
        "`PIE-S2310`",
        "`PIE-S2311`",
        "`PIE-S2312`",
        "`PIE-S2313`",
        "`PIE-S2314`",
        "`PIE-S2315`",
        "`PIE-S2317`",
        "`PIE-S2318`",
        "`PIE-S2319`",
        "`PIE-S2320`",
    ):
        assert required in spec, required

    for required in (
        "| `count()` | no argument | `Int` | `NON_NULL` |",
        "| `count(field)` | current supported direct concrete field | `Int` | `NON_NULL` |",
        "| bounded `count(expression)` | current field-bearing accepted typed expression | `Int` | `NON_NULL` |",
        "| `count_distinct` | approved direct scalar or lower/trim Text chain | `Int` | `NON_NULL` |",
        "| `sum(Int)` | canonical Int | `Int` | `NULLABLE` |",
        "| `sum(Float)` | canonical Float | `Float` | `NULLABLE` |",
        "| `sum(Decimal)` | canonical Decimal | `Decimal` | `NULLABLE` |",
        "| `avg(Int/Float)` | canonical Int or Float | `Float` | `NULLABLE` |",
        "| `avg(Decimal)` | canonical Decimal | `Decimal` | `NULLABLE` |",
        "| `min/max` | direct Int/Float/Decimal/Date/Timestamp | same canonical type | `NULLABLE` |",
    ):
        assert required in type_matrix, required

    assert "no precision propagation" in normalized_type_matrix
    assert (
        "does not infer database runtime empty-input behavior" in normalized_type_matrix
    )


def test_relation_output_identity_origin_and_provenance_are_distinct() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "source-ordered by `select` order",
        "Aggregate expressions have no canonical default name",
        "Output name, source field identity, result role, and provenance are distinct facts",
        "orthogonal private `GROUP_KEY` role",
        "existing private `AGGREGATE` origin vocabulary",
        "`AGGREGATE_FROM_LET`",
        "`AGGREGATE_FROM_EXPRESSION`",
        "An aggregate result must be treated as derived/private result output",
        "never a source-native field",
    ):
        assert required in spec, required

    assert "No synthetic public name is permitted" in spec


def test_exact_four_schema_states_and_duplicate_posture_are_locked() -> None:
    spec = _read(SPEC_PATH)
    state_section = _section(spec, "Schema Availability-State Matrix")
    duplicate_section = _section(spec, "Duplicate Output-Name Posture")
    normalized_duplicate_section = " ".join(duplicate_section.split())

    for state in SCHEMA_STATES:
        assert f"`{state}`" in state_section
    assert "Exactly four states remain authoritative" in state_section
    assert "No fifth schema availability state is allowed" in state_section

    for required in (
        "`UNKNOWN / DUPLICATE_OUTPUT_NAME`",
        "without adding `PIE-S2305`",
        "adds no diagnostic",
        "never makes a duplicate aggregate/grouped schema concrete",
        "Duplicate group keys remain separate existing `PIE-S2317` behavior",
    ):
        assert required in normalized_duplicate_section, required


def test_dependency_lineage_clause_and_qualification_boundaries_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`AGGREGATE_ARGUMENT`",
        "`count()`",
        "no fabricated field lineage leaf",
        "deterministic AST order",
        "Immediate and transitive facts remain distinct",
        "query-clause dependencies, not selected-output lineage",
        "`satisfying:` | none",
        "grouped `order by:` | none",
        "`limit` | none",
        "the bare selected output name",
        "the immediate upstream relation qualifier plus selected output name",
        "are not downstream query paths",
    ):
        assert required in spec, required


def test_phase47_49_carriers_privacy_and_phase51_handoff_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`ProjectRowSchema`",
        "`ProjectRowField`",
        "`ProjectRowFieldProvenance`",
        "`ProjectRelationRowSchemaState`",
        "private row dependency graphs",
        "private row lineages",
        "Project JSON v2",
        "Semantic Metadata Artifact v1",
        "remain private and unserialized",
        "Phase 51 remains unstarted",
        "current canonical aggregate result types and nullability only",
        "bare/immediate-upstream qualification only",
    ):
        assert required in spec, required

    for forbidden in (
        "Phase 51 has started",
        "Phase 51 is complete",
        "public aggregate row schema is implemented",
        "Project JSON v2 exposes aggregate",
    ):
        assert forbidden not in spec, forbidden


def test_explicit_deferrals_and_public_runtime_non_goals_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`count_if`",
        "broad `count_distinct(expression)`",
        "`min/max(expression)`",
        "aggregate filters/internal ordering/generic modifiers/DISTINCT",
        "window functions",
        "pure grouping/rollup/cube/grouping sets",
        "new scalar/type behavior",
        "Decimal aggregate precision",
        "public schema/lineage/project explain",
        "project IR/SQL/emit-sql",
        "JOIN/grain/fanout-aware aggregates",
        "runtime/database/introspection/connections",
        "adds no parser, grammar, generated artifact, AST, semantic analysis",
        "adds no public lineage",
        "adds no diagnostic",
    ):
        assert required in spec, required


def test_package_version_remains_010() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.1.0"
