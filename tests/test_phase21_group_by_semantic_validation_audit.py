from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-21-group-by-contract-planning.md"
DIAGNOSTICS_PATH = REPO_ROOT / "docs/spec/diagnostics.md"
SEMANTIC_GROUP_BY_PATH = REPO_ROOT / "src/pietto/semantic/group_by.py"


def _read_plan() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized_plan() -> str:
    return " ".join(_read_plan().split())


def test_phase21_slice5_status_and_scope_are_documented() -> None:
    plan = _normalized_plan()

    for required in (
        "Phase 21 Slice 5 is complete as grouped semantic validation and grouped output schema work with the same unconditional fail-closed lowering gate",
        "It resolves group keys, validates grouped projections, computes grouped row schemas, and keeps `PIE-S2316` as an error",
        "Slice 5 changes only semantic validation, grouped row-schema propagation, diagnostic documentation, and focused tests",
        "It adds no grammar, generated ANTLR, parser, AST, IR, SQL, CLI, fixture, golden, `scripts/check_goldens.py`, dependency, lockfile, CI, runtime, database, UI, LSP, or policy DSL behavior",
    ):
        assert required in plan


def test_group_key_resolution_contract_is_documented() -> None:
    plan = _normalized_plan()

    for required in (
        "bare input fields resolve against the grouped relation input row schema",
        "single-input qualified fields resolve only when the qualifier matches the relation `from` source name",
        "`status` and `orders.status` are equivalent when both resolve to the same input field",
        "accepted unique keys preserve first source order",
        "later duplicate resolved keys emit `PIE-S2317`",
        "unknown group keys reuse `PIE-S2102`",
        "dependent grouped projection cascades from an unknown group key are suppressed",
    ):
        assert required in plan


def test_grouped_select_and_output_schema_contract_are_documented() -> None:
    plan = _normalized_plan()

    for required in (
        "direct group key projections are allowed",
        "aliased group key projections are allowed",
        "direct aggregate projections in the Phase 20 aggregate surface are allowed for schema computation",
        "aggregate projections still require explicit aliases and reuse `PIE-S2313`",
        "non-grouped plain fields emit `PIE-S2318`",
        "scalar grouped projection expressions emit `PIE-S2319`",
        "pure grouping or distinct-style output without an aggregate emits `PIE-S2320`",
        "grouped `order by` emits `PIE-S2321` and remains deferred",
        "group key projections preserve input field type and nullability",
        "`count() -> Int not null`",
        "`sum(Int) -> Int nullable`",
        "`sum(Float) -> Float nullable`",
        "`avg(Int) -> Float nullable`",
        "`avg(Float) -> Float nullable`",
        "invalid named projections publish unknown fields where stable output names exist",
        "invalid unaliased projections suppress output fields",
    ):
        assert required in plan


def test_fail_closed_lowering_gate_is_documented() -> None:
    plan = _normalized_plan()

    for required in (
        "semantic analysis still emits one `PIE-S2316` error per table or query relation containing `group by:`",
        "`GROUP BY is semantically validated but IR/SQL lowering is deferred`",
        "`pietto check` still fails for every grouped relation",
        "`pietto emit-sql --format json` still fails before IR/SQL output and produces no artifacts",
        "downstream relations cannot produce SQL success while any grouped relation emits `PIE-S2316`",
    ):
        assert required in plan


def test_slice5_non_goals_remain_locked() -> None:
    plan = _normalized_plan()

    for required in (
        "Slice 5 explicitly does not implement Semantic IR `group_keys`, SQL `GROUP BY` lowering, SQL goldens, grouped `emit-sql` success",
        "grouped `order by`",
        "HAVING user syntax",
        "`satisfying`, `filter`",
        "JOIN",
        "relationship-driven query behavior",
        "aggregate expression arguments",
        "Decimal aggregate semantics",
        "casts",
        "runtime/database execution",
    ):
        assert required in plan


def test_slice5_diagnostics_are_registered() -> None:
    diagnostics = DIAGNOSTICS_PATH.read_text(encoding="utf-8")

    for required in (
        "| `PIE-S2316` | GROUP BY IR/SQL lowering is deferred |",
        "| `PIE-S2317` | Duplicate GROUP BY key |",
        "| `PIE-S2318` | Non-grouped projection in grouped relation |",
        "| `PIE-S2319` | Grouped scalar projection is deferred |",
        "| `PIE-S2320` | Pure grouped output without an aggregate is deferred |",
        "| `PIE-S2321` | Grouped ORDER BY is deferred |",
    ):
        assert required in diagnostics


def test_semantic_gate_message_and_codes_are_owned_by_group_by_helper() -> None:
    source = SEMANTIC_GROUP_BY_PATH.read_text(encoding="utf-8")

    for required in (
        'GROUP_BY_DEFERRED_CODE = "PIE-S2316"',
        "GROUP BY is semantically validated but IR/SQL lowering is deferred",
        'code="PIE-S2317"',
        'code="PIE-S2318"',
        'code="PIE-S2319"',
        'code="PIE-S2320"',
        'code="PIE-S2321"',
    ):
        assert required in source


def test_plan_does_not_claim_group_by_lowering_or_emit_sql_success() -> None:
    plan = _normalized_plan()

    forbidden_claims = (
        "SQL GROUP BY lowering is complete",
        "grouped emit-sql success is implemented",
        "grouped `emit-sql` success path is implemented",
        "Semantic IR `group_keys` is implemented",
        "GROUP BY implementation is complete",
    )
    for forbidden in forbidden_claims:
        assert forbidden not in plan
