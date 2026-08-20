from __future__ import annotations

from pathlib import Path
import tomllib

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-49-row-level-computed-let-schema-lineage.md"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase49-row-level-computed-let-schema-lineage-scope-lock-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

PHASE49_SLICE_NAMES = (
    "Candidate decision / scope lock",
    "Project row expression schema helper contract",
    "Type/nullability adapter for legal row expressions",
    "Computed alias project row schema MVP",
    "Computed alias origin/provenance privacy",
    "Project let scope/value facts",
    "Selected let-derived output schema",
    "Let visibility/order/shadowing hardening",
    "Private row-level dependency graph scaffold",
    "Minimal private lineage carrier for source/direct/rename",
    "Lineage for computed/let/multi-hop fields",
    "Unknown/deferred/diagnostic ordering hardening",
    "Compatibility/privacy/hash-lock readiness",
    "Completion audit/status lock",
)


def _docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_phase49_scope_lock_artifacts_exist() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()


def test_route_c_and_fourteen_slice_count_are_locked() -> None:
    docs = _docs()

    for required in (
        "Phase 49 selects Route C with exactly fourteen slices",
        "Fourteen slices is within the user-approved maximum of sixteen",
        "If future work exceeds sixteen slices",
        "Row-level Computed Alias, Let Schema, Origin, Dependency, and Lineage",
    ):
        assert required in docs, required

    for slice_name in PHASE49_SLICE_NAMES:
        assert slice_name in docs, slice_name


def test_route_c_gate1b_repo_fact_justification_is_locked() -> None:
    docs = _docs()

    for required in (
        "`ValueType(resolved_type, nullability)`",
        "Computed aliases already have single-file type/nullability",
        "Single-file computed row fields already carry computed expression",
        "Project row schema currently defers non-direct projections",
        "`LetScopeSemanticInfo.value_types`",
        "Let self references and forward references fail closed",
        "Row-level dependency cycles are not expressible",
        "Row-level cycle diagnostics remain readiness-only in Phase 49",
        "Private dependency graph and private lineage carrier",
    ):
        assert required in docs, required


def test_expression_coverage_and_non_expansion_are_locked() -> None:
    docs = _docs()

    for required in (
        "supports all existing legal row-level typed expressions for schema",
        "does not expand the expression language",
        "Field references and qualified field references are safe",
        "Int, Float, Text, and Bool literals are typed and non-null",
        "Null literal remains unknown/deferred",
        "Unary numeric expressions reuse existing rules",
        "Supported binary `+`, `-`, `*`, and `%` expressions reuse existing rules",
        "Binary `/` remains unsupported/unknown",
        "Comparisons, Bool `and` / `or`, `between`, and `is null` / `is not null`",
        "`lower`, `trim`, `len`, and `matches`",
        "Decimal support is limited to existing legal expression rules",
        "Date/Timestamp support remains limited",
        "Let references reuse existing `LetScopeSemanticInfo.value_types`",
        "Aggregate expressions and grouped output schema remain deferred",
    ):
        assert required in docs, required


def test_field_def_source_native_and_derived_origin_decision_is_locked() -> None:
    docs = _docs()

    for required in (
        "`field_def` remains source-native only",
        "original shape/source `FieldDef`",
        "direct, renamed, or multi-hop projections may preserve",
        "Computed expression fields and `let`-derived fields should use",
        "source-native `field_def=None`",
        "explicit private origin/provenance/lineage metadata",
        "must not use a synthetic derived `FieldDef`",
        "Derived fields must not look source-native",
    ):
        assert required in docs, required


def test_private_origin_provenance_lineage_and_privacy_are_locked() -> None:
    docs = _docs()

    for required in (
        "`SOURCE_FIELD`",
        "`DIRECT_PROJECTION`",
        "`RENAMED_PROJECTION`",
        "`DERIVED_EXPRESSION`",
        "`LET_DERIVED`",
        "`AGGREGATE`",
        "`UNKNOWN`",
        "source-native fields, renamed projections, computed expression fields",
        "`let`-derived fields are different origin categories",
        "minimal private full lineage carrier",
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
        "Multi-input expressions preserve multiple dependencies",
        "Multi-hop propagation preserves lineage chains",
        "Lineage remains private",
        "must not serialize to Project JSON v2",
    ):
        assert required in docs, required


def test_dependency_graph_boundary_is_locked() -> None:
    docs = _docs()

    for required in (
        "Relation dependency cycles remain separate",
        "`PIE-S2302`",
        "Expression and `let` dependency facts are row-level facts",
        "Current `let` source order rules reject self references and forward references",
        "Select aliases are not fed back into the same relation expression scope",
        "Phase 49 may add a minimal private row-level dependency graph",
        "must not add row-level cycle diagnostics in Slice 1",
    ):
        assert required in docs, required


def test_explicit_non_goals_and_package_release_boundary_are_locked() -> None:
    docs = _docs()
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]

    assert project["version"] == "0.1.0"
    assert "Package version remains `0.1.0`" in docs

    for required in (
        "no production code",
        "no source/compiler behavior",
        "no Project JSON v2 shape change",
        "no private fact serialization",
        "no project IR",
        "no project SQL emit",
        "no project `emit-sql`",
        "no project `explain`",
        "no public project semantic API",
        "no selector syntax expansion",
        "no parser/grammar/generated change",
        "no aggregate/grouped output schema",
        "no JOIN/relationship behavior",
        "no runtime/database execution",
        "no package version change",
        "no tag, release, publish, upload, signing, or attestation",
    ):
        assert required in docs, required


def test_phase50_60_readiness_boundaries_are_locked() -> None:
    docs = _docs()

    for required in (
        "Phase 50 aggregate/grouped output schema",
        "Phase 51 relationship/grain/fanout readiness",
        "Phase 52 Project Explain / Semantic Metadata Readiness",
        "Phase 53 import/export and multi-file ergonomics",
        "Phase 54 JOIN readiness",
        "Phase 55 bridge/export/RAG/Arrow readiness",
        "Phases 56-60 remain later roadmap territory",
        "no aggregate/grouped output schema is implemented in Phase 49",
        "no relationship, grain, or fanout behavior is implemented in Phase 49",
        "no project explain or public metadata output is implemented in Phase 49",
        "JOIN behavior remains deferred",
        "bridge, export, RAG, Arrow, and PyArrow behavior remain deferred",
    ):
        assert required in docs, required
