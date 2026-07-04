from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-43-let-binding-aggregate-and-grouped-query-integration-mvp.md"
)
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase43-let-binding-aggregate-grouped-integration-scope-lock-v1.md"
)
REGISTER_PATH = REPO_ROOT / "docs/spec/v02-deferred-feature-register-v1.md"
PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
PHASE40_PLAN_PATH = REPO_ROOT / "docs/plan/phase-40-let-binding-model-candidate.md"
PHASE40_AGG_SPEC_PATH = (
    REPO_ROOT / "docs/spec/phase40-let-binding-aggregate-interaction-boundary-v1.md"
)
PHASE42_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-42-aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock.md"
)
PHASE42_SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock-v1.md"
)
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

IR_PATHS = (
    REPO_ROOT / "src/pietto/ir/model.py",
    REPO_ROOT / "src/pietto/ir/builder.py",
    REPO_ROOT / "src/pietto/ir/lowering.py",
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


def _phase43_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def test_phase43_slice1_artifacts_and_trusted_handoff_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert REGISTER_PATH.is_file()

    docs = _phase43_docs()
    for required in (
        "Phase 43 Slice 1 is Identity, Scope Lock, And Static Audit",
        "docs/spec/deferred-register/static-audit work only and implements no behavior change",
        "baseline HEAD: `2e9bb45623a7bf98ed430b9b9ab76404402b9a5e`",
        "baseline branch: `main`",
        "baseline commit: `Complete Phase 42 aggregate scope lock audit`",
        "latest completed phase: Phase 42 Aggregate Function Typeclasses And Decimal Arithmetic Scope Lock",
        "final Phase 42 CI run: `28671500608`",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation is authorized by Slice 1",
        "Phase 43 Slice 2 is `sum(row_let)` / `avg(row_let)` Inline Aggregate Arguments",
        "Slice 2 is a production behavior slice",
    ):
        assert required in docs, required


def test_phase43_identity_supersedes_old_phase37_future_label() -> None:
    phase37 = _normalized(PHASE37_PLAN_PATH)
    docs = _phase43_docs()

    for required in (
        "The following roadmap note is planning-only",
        "Phase 43: LSP Diagnostics MVP",
        "Phase 44: Arrow / PyArrow Schema Bridge MVP",
        "Phase 45+: Semantic Graph / JOIN Readiness II",
    ):
        assert required in phase37, required

    for required in (
        "Let Binding Aggregate And Grouped Query Integration MVP",
        "supersedes the old Phase 37 planning-only future label",
        "`Phase 43: LSP Diagnostics MVP`",
        "historical, non-authoritative context",
        "LSP/editor behavior, Arrow/PyArrow integration",
        "relationship/JOIN-driven query behavior",
        "runtime/database execution",
        "project/multi-file semantic expansion",
    ):
        assert required in docs, required


def test_phase40_and_phase42_boundaries_are_carried_forward() -> None:
    docs = _phase43_docs()
    source_docs = " ".join(
        _normalized(path)
        for path in (
            PHASE40_PLAN_PATH,
            PHASE40_AGG_SPEC_PATH,
            PHASE42_PLAN_PATH,
            PHASE42_SPEC_PATH,
        )
    )

    for required in (
        "row-level `where` may reference let names",
        "grouped pre-aggregate `where` may reference let names",
        "no-GROUP non-aggregate `select` may reference let names",
        "no-GROUP input-scope `order by` may reference let names",
        "supported let references are IR inline-expanded",
        "no-GROUP aggregate select projections may use `sum(row_let)` and",
        "grouped aggregate select projections may use the same `sum(row_let)` and",
        "`count(gross)`",
        "`count_distinct(gross)`",
        "`group by gross` remains deferred/fail-closed",
        "`satisfying: gross > 0` remains deferred/fail-closed",
        "grouped `order by gross` remains deferred/fail-closed",
        "`limit gross` remains deferred/fail-closed",
        "qualified let references such as `orders.gross` remain rejected",
        "Projection aliases remain output names only",
    ):
        assert required in docs, required

    for required in (
        "aggregate-let remains deferred",
        "`sum(gross)`",
        "`avg(gross)`",
        "`count(gross)`",
        "`count_distinct(gross)`",
        "`group by gross` remains deferred/fail-closed",
        "`satisfying: gross > 0` remains deferred/fail-closed",
        "grouped `order by gross` remains deferred/fail-closed",
        "`limit gross` remains deferred/fail-closed",
        "qualified let references such as `orders.gross` remain rejected",
        "Projection aliases remain output names only",
    ):
        assert required in source_docs, required

    for required in (
        "Historical Phase 42 evidence confirmed that aggregate arguments did not see let names before Slice 2",
        "type_relation_expressions",
        "passes no let scope into direct aggregate projection argument typing",
        "IR lowering passes empty `let_expansions` while lowering aggregate arguments",
    ):
        assert required in docs, required

    for required in (
        "Aggregate arguments do not see let names",
        "type_relation_expressions",
        "passes no let scope into direct aggregate projection argument typing",
        "IR lowering passes empty `let_expansions` while lowering aggregate arguments",
    ):
        assert required in source_docs, required


def test_phase43_slice_sequence_and_inline_policy_are_locked() -> None:
    docs = _phase43_docs()

    for required in (
        "| 1 | Identity, Scope Lock, And Static Audit |",
        "| 2 | `sum(row_let)` / `avg(row_let)` Inline Aggregate Arguments |",
        "| 3 | `count(row_let)` / `count_distinct(row_let)` Inline Aggregate Arguments |",
        "| 4 | `group by row_let` Inline Group Key MVP |",
        "| 5 | Grouped `order by row_let` Safe Subset |",
        "| 6 | `satisfying` Boundary For Aggregate-Wrapped Let |",
        "| 7 | CLI / JSON / Metadata / SQL Compatibility Hardening |",
        "| 8 | Completion Audit And Status Lock |",
        "Future Phase 43 behavior slices must prefer inline expansion through existing semantic validation",
        "Phase 43 must not invent special aggregate-only let semantics",
        "`satisfying: row_let > 0` must remain rejected unless",
        "`limit row_let` must continue to reject",
        "qualified let references must continue to reject",
    ):
        assert required in docs, required


def test_gate2_allowlist_forbidden_surfaces_and_stop_conditions_are_locked() -> None:
    docs = _phase43_docs()

    for required in (
        "Phase 43 Slice 1 Gate 2 is limited to:",
        "docs/plan/phase-43-let-binding-aggregate-and-grouped-query-integration-mvp.md",
        "docs/spec/phase43-let-binding-aggregate-grouped-integration-scope-lock-v1.md",
        "docs/spec/v02-deferred-feature-register-v1.md",
        "tests/test_phase43_let_binding_aggregate_grouped_scope_lock.py",
        "No other file is approved",
        "production source changes",
        "grammar or generated ANTLR changes",
        "IR model or lowering behavior changes",
        "PostgreSQL or private MySQL SQL renderer behavior changes",
        "CLI JSON v1, Project JSON v2, explain, or Semantic Metadata Artifact v1",
        "`README.md`, `AGENTS.md`, or `docs/spec/pietto-v0.9.md` changes",
        "literal-only aggregate behavior",
        "Decimal precision fusion",
        "aggregate typeclass implementation",
        "runtime/database execution",
        "UI/LSP",
        "Arrow/PyArrow integration",
        "project/multi-file execution",
        "relationship/JOIN-driven query behavior",
        "broader validation, hash-lock refresh, package/build work, generators, full pytest, `scripts/validate.py`, package smoke, or CI operations",
    ):
        assert required in docs, required


def test_deferred_register_records_phase43_scope_lock() -> None:
    register = _normalized(REGISTER_PATH)

    for required in (
        "Phase 43 Slice 1 scope-lock selects let-binding aggregate/grouped integration as the active Phase 43 identity",
        "old Phase 37 LSP/Arrow/JOIN labels are historical planning-only context",
        "Phase 43 Slice 2 implements only direct `sum(let_name)` / `avg(let_name)` inline aggregate arguments",
        "No `count(let_name)`, `count_distinct(let_name)`, `group by let_name`, grouped `order by let_name`, or raw `satisfying` let-name behavior unfreezes until its later Phase 43 implementation slice is explicitly approved",
        "hidden relation layer, CTE, subquery, JOIN, relationship traversal, public schema change, LSP, Arrow/PyArrow, runtime/database, or project/multi-file behavior",
    ):
        assert required in register, required

    for forbidden in (
        "count over let names is implemented",
        "count_distinct over let names is implemented",
        "grouped let support is implemented",
        "Phase 43 implements LSP",
        "Arrow/PyArrow integration is implemented",
        "JOIN readiness is implemented",
    ):
        assert forbidden not in register, forbidden


def test_ir_package_and_release_boundaries_remain_locked() -> None:
    docs = _phase43_docs()

    assert 'version = "0.1.0"' in _read(PYPROJECT_PATH)
    assert 'version = "0.2.0"' not in _read(PYPROJECT_PATH)

    ir_text = " ".join(_read(path) for path in IR_PATHS)
    assert "LetBindingIR" not in ir_text
    assert "RelationLayerIR" not in ir_text

    for required in (
        "no `LetBindingIR`",
        "no `RelationLayerIR`",
        "no hidden CTE insertion",
        "no hidden subquery insertion",
        "no public `let_scopes` metadata key",
        "No compiler behavior is implemented by this slice",
    ):
        assert required in docs, required

    lowered_docs = docs.lower()
    for forbidden in POSITIVE_RELEASE_CLAIMS:
        assert forbidden not in lowered_docs, forbidden
