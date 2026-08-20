from __future__ import annotations

from pathlib import Path
import tomllib

from _static_audit_helpers import normalized_text as _normalized

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-49-row-level-computed-let-schema-lineage.md"
SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase49-project-row-expression-schema-helper-contract-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def _docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_slice2_spec_exists_and_prefers_richer_result_shape() -> None:
    assert SPEC_PATH.is_file()
    docs = _docs()

    for required in (
        "Phase 49 Slice 2 is Project row expression schema helper contract work only",
        "`docs/spec/phase49-project-row-expression-schema-helper-contract-v1.md`",
        "docs/spec/tests-only private helper contract",
        "`ProjectExpressionSchemaResult`-like result",
        "instead of returning only `ProjectRowField` or only `ValueType`",
        "future private project row expression schema helper",
    ):
        assert required in docs, required


def test_slice2_input_contract_is_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "expression AST",
        "output name",
        "input project row schema",
        "relation name / immediate upstream qualifier",
        "current let scope value types",
        "let expression references",
        "`SemanticModel.expression_value_types`",
        "source location / stable fallback reference",
        "availability state of upstream relation row schema",
    ):
        assert required in spec, required


def test_slice2_output_origin_and_field_def_contract_is_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "resolved type",
        "nullability",
        "optional source-native `field_def`",
        "private origin/provenance kind",
        "dependency references",
        "lineage placeholders",
        "schema availability status/reason",
        "`SOURCE_FIELD`",
        "`DIRECT_PROJECTION`",
        "`RENAMED_PROJECTION`",
        "`DERIVED_EXPRESSION`",
        "`LET_DERIVED`",
        "`AGGREGATE`",
        "`UNKNOWN`",
        "`field_def` remains source-native only",
        "Computed aliases and let-derived outputs must use `field_def=None`",
        "must not synthesize derived `FieldDef`",
        "Derived fields must not look source-native",
    ):
        assert required in spec, required


def test_slice2_dependency_lineage_and_cycle_contract_is_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "multiple dependencies for multi-input expressions",
        "source field",
        "relation field",
        "select item",
        "let binding",
        "expression operation",
        "literal",
        "`depends_on`",
        "`projects_from`",
        "`renames_from`",
        "`computes_from`",
        "`let_resolves_to`",
        "Computed alias over propagated field should preserve the upstream lineage chain",
        "Selected let output should link to the let binding",
        "Multi-hop propagation should preserve lineage chains",
        "Relation dependency cycles remain separate",
        "`PIE-S2302`",
        "Row-level dependency cycle diagnostics remain readiness-only in Phase 49",
    ):
        assert required in spec, required


def test_slice2_diagnostics_availability_and_deferrals_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "no new diagnostics in Slice 2 and in the future helper MVP",
        "consume existing semantic facts",
        "preserve existing diagnostics/order",
        "`UNKNOWN`, `DEFERRED`, and `BLOCKED` behavior must remain deterministic",
        "`PIE-S2102`",
        "`PIE-S2301`",
        "`PIE-S2302`",
        "not be replaced or duplicated by helper-specific public diagnostics",
        "Binary expressions and null literal should not become precise",
        "Aggregate and grouped output schema remains deferred to Phase 50 or later",
    ):
        assert required in spec, required


def test_slice2_public_surface_non_goals_and_json_privacy_are_locked() -> None:
    docs = _docs()

    for required in (
        "no production helper behavior",
        "no source/compiler behavior",
        "no Project JSON v2 public output",
        "no public semantic API",
        "no project explain implementation",
        "no project IR",
        "no project SQL",
        "no project `emit-sql`",
        "no JOIN/relationship behavior",
        "no runtime/database execution",
        "no parser/grammar/generated changes",
        "must not be serialized into Project JSON v2",
        "no bridge/export/RAG/Arrow behavior",
        "import/export or module behavior",
    ):
        assert required in docs, required


def test_slice2_reuse_and_location_guidance_is_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "prefer reusing existing `SemanticModel.expression_value_types`",
        "`infer_row_expression` may be considered only if",
        "does not violate existing project path boundaries",
        "avoid full `semantic_api.analyze`",
        "private helper module under `src/pietto/_project/`",
        "Do not default to adding `pietto.semantic` imports into",
        "`src/pietto/_project/model.py`",
        "Minimize duplication and hash-lock churn",
    ):
        assert required in spec, required


def test_slice2_roadmap_readiness_relationships_are_locked() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "Phase 50 aggregate/grouped output row schema depends on the richer helper",
        "Phase 51 relationship/grain/fanout readiness depends on",
        "source-native versus derived field distinction",
        "Phase 52 project explain / semantic metadata readiness depends on private",
        "origin/dependency/lineage facts",
        "Phase 53 import/export and multi-file ergonomics should only be prepared",
        "Phase 54 JOIN readiness may be prepared through origin/lineage metadata",
        "JOIN must not be implemented here",
        "Phase 55 bridge/export/RAG/Arrow readiness may be prepared through private",
        "no bridge/export/PyArrow/runtime behavior is implemented here",
        "Phase 56-60 remain product decisions",
        "Project IR, project SQL, and project `emit-sql` remain future product decisions",
        "not pulled into Slice 2",
    ):
        assert required in spec, required


def test_package_version_remains_010() -> None:
    project = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.1.0"
