from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-24-aggregate-function-expansion-ii.md"


def _read() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized() -> str:
    return " ".join(_read().split())


def test_phase24_slice1_plan_exists_and_names_aggregate_expansion_ii() -> None:
    assert PLAN_PATH.is_file()

    plan = _normalized()
    for required in (
        "Phase 24 Aggregate Function Expansion II",
        "Phase 24 Slice 1 is complete as candidate decision and contract work only",
        "Phase 24 selects **Aggregate Function Expansion II** as the next core language direction",
        "using the **Balanced** scope",
        "Implementation-ready after this Slice 1 contract",
    ):
        assert required in plan


def test_slice1_is_contract_only_without_behavior_changes() -> None:
    plan = _normalized()

    for required in (
        "It does not implement semantic behavior, Semantic IR behavior, SQL renderer behavior, CLI behavior, JSON behavior, runtime behavior, database behavior, fixtures, or goldens",
        "Slice 1 changes no grammar, generated ANTLR, AST, semantic production code, Semantic IR production code, SQL renderer, CLI behavior, JSON schema, fixture, golden, `scripts/check_goldens.py` inventory, dependency, lockfile, package metadata, CI, backend registry behavior, runtime/database behavior, UI, LSP, policy/security DSL, or relationship query behavior",
        "This decision does not implement `count_distinct(field)`, Decimal aggregate support, or aggregate expression arguments",
        "It records the future implementation contract so later slices can remain narrow and auditable",
    ):
        assert required in plan


def test_balanced_scope_is_selected_with_three_subtracks() -> None:
    plan = _normalized()

    for required in (
        "Balanced: implement `count_distinct(field)` MVP, implement logical Decimal direct-field aggregate support if the approved contract remains precise, and keep aggregate expression arguments readiness/contract-only",
        "Chosen for Phase 24",
        "implement `count_distinct(field)` MVP",
        "implement logical Decimal direct-field aggregate support if the approved contract remains precise",
        "keep aggregate expression arguments readiness/contract-only in Phase 24",
    ):
        assert required in plan


def test_count_distinct_accepted_shapes_contexts_and_sql_are_locked() -> None:
    plan = _normalized()

    for required in (
        "direct aliased aggregate projections only",
        "`alias = count_distinct(field)`",
        "`alias = count_distinct(source.field)`",
        "no-GROUP aggregate `select:` projections",
        "grouped aggregate `select:` projections",
        "bare field arguments such as `count_distinct(customer_id)`",
        "existing single-input qualified field arguments such as `count_distinct(orders.customer_id)`",
        "PostgreSQL should render `count_distinct(field)` as `COUNT(DISTINCT field)`",
        "MySQL should render `count_distinct(field)` as `COUNT(DISTINCT field)`",
        "`count_distinct(field)` counts unique non-null field values",
    ):
        assert required in plan


def test_count_distinct_result_and_type_allowlist_are_locked() -> None:
    plan = _normalized()

    for required in (
        "`count_distinct(field) -> Int not null`",
        "`count_distinct(source.field) -> Int not null`",
        "the result is non-null because SQL `COUNT(DISTINCT expr)` returns `0`",
        "`Bool`",
        "`Int`",
        "`Float`",
        "`Decimal`",
        "`Text`",
        "`Date`",
        "`Timestamp`",
        "`UUID`",
    ):
        assert required in plan


def test_count_distinct_rejects_and_defers_unsupported_arguments() -> None:
    plan = _normalized()

    for required in (
        "`Any`",
        "`Unknown`",
        "unresolved or missing fields",
        "`Bytes`",
        "`Json`",
        "projection aliases",
        "expression arguments",
        "nested aggregates",
        "`count_distinct` remains an aggregate name only, not a scalar builtin",
        "It must not be added to the scalar `BUILTIN_FUNCTIONS` catalog",
    ):
        assert required in plan


def test_decimal_direct_field_aggregate_contract_is_locked() -> None:
    plan = _normalized()

    for required in (
        "Future Decimal aggregate support is limited to direct field arguments only",
        "`sum(Decimal)`",
        "`avg(Decimal)`",
        "`min(Decimal)`",
        "`max(Decimal)`",
        "`sum(Decimal) -> Decimal nullable`",
        "`avg(Decimal) -> Decimal nullable`",
        "`min(Decimal) -> Decimal nullable`",
        "`max(Decimal) -> Decimal nullable`",
        "render `sum(Decimal)` with `SUM(field)`",
        "render `avg(Decimal)` with `AVG(field)`",
        "render `min(Decimal)` with `MIN(field)`",
        "render `max(Decimal)` with `MAX(field)`",
    ):
        assert required in plan


def test_decimal_precision_scale_and_float_collapse_are_explicitly_excluded() -> None:
    plan = _normalized()

    for required in (
        "there is no Decimal precision/scale promise in Phase 24",
        "there are no Decimal type-argument semantics in Phase 24",
        "there is no silent collapse from Decimal to Float",
        "the target SQL engine handles exact precision behavior",
        "no SQL casts are introduced by the Phase 24 Decimal aggregate contract",
    ):
        assert required in plan


def test_expression_argument_readiness_keeps_implementation_deferred() -> None:
    plan = _normalized()

    for required in (
        "Aggregate expression arguments remain readiness/contract-only in Phase 24",
        "`sum(amount + tax)`",
        "`avg(score * weight)`",
        "`count(lower(email))`",
        "`count_distinct(lower(email))`",
        "does not implement aggregate expression arguments",
        "does not broadly retire `PIE-S2315`",
        "Expression argument implementation likely requires Phase 25 implementation authorization",
    ):
        assert required in plan


def test_existing_aggregate_diagnostics_and_backend_failure_are_reused() -> None:
    plan = _normalized()

    for required in (
        "No new diagnostic code is expected in Slice 1",
        "`PIE-S2308` for invalid aggregate context",
        "`PIE-S2309` for wrong arity",
        "`PIE-S2310` for aggregate composition",
        "`PIE-S2311` for nested aggregate",
        "`PIE-S2312` for mixed no-GROUP aggregate and non-aggregate projections",
        "`PIE-S2313` for unaliased aggregate projections",
        "`PIE-S2314` for unsupported direct field argument type",
        "`PIE-S2315` for expression arguments",
        "`PIE-S2308` through `PIE-S2315` aggregate diagnostic family",
        "Malformed backend IR remains fail-closed through existing `PIE-B1000`",
        "Malformed hand-built `AggregateCallIR` shapes must continue to fail closed in SQL backends",
    ):
        assert required in plan


def test_required_phase24_non_goals_are_explicitly_deferred() -> None:
    plan = _normalized()

    for required in (
        "generic `DISTINCT` keyword syntax",
        "`count(distinct field)`",
        "aggregate modifier system",
        "`sum_distinct`",
        "`avg_distinct`",
        "`min_distinct`",
        "`max_distinct`",
        "filtered aggregates",
        "aggregate expression argument implementation",
        "retiring `PIE-S2315`",
        "HAVING",
        "`satisfying`",
        "grouped `ORDER BY`",
        "JOIN behavior",
        "relationship behavior",
        "runtime/database execution",
        "connector execution",
        "schema introspection",
        "JSON schema changes",
        "CLI option changes",
        "public API expansion",
        "dependency/config/CI/package changes",
    ):
        assert required in plan


def test_proposed_phase24_slice_sequence_is_recorded() -> None:
    plan = _normalized()

    for required in (
        "Slice 1: Aggregate Function Expansion II Candidate Decision And Contract**: complete as docs/static-audit only",
        "Slice 2: `count_distinct(field)` Semantic Validation And Row Schema**: complete as semantic validation and row-schema work",
        "Slice 3: `count_distinct(field)` IR Lowering**: future implementation slice",
        "Slice 4: `count_distinct(field)` SQL Rendering And Goldens**: future implementation slice",
        "Slice 5: Decimal Aggregate Semantic/Type Contract**: future contract slice",
        "Slice 6: Decimal Aggregate Implementation, SQL Rendering, And Goldens If Approved**: future implementation slice",
        "Slice 7: Aggregate Expression Arguments Readiness Audit**: future docs/static-audit slice",
        "Slice 8: CLI/JSON/Output Hardening**: future tests/audit slice",
        "Slice 9: Completion Audit And Status Lock**: future audit/status slice",
    ):
        assert required in plan


def test_slice1_does_not_claim_later_behavior_is_implemented() -> None:
    plan = _normalized()

    for forbidden in (
        "Slice 1 implements semantic behavior",
        "Slice 1 implements Semantic IR behavior",
        "Slice 1 implements SQL renderer behavior",
        "Slice 1 implements CLI behavior",
        "Slice 1 implements JSON behavior",
        "Slice 1 implements runtime behavior",
        "Slice 1 implements database behavior",
        "Slice 1 adds fixtures",
        "Slice 1 adds goldens",
        "Slice 1 implements `count_distinct(field)`",
        "Slice 1 implements Decimal aggregate support",
        "Slice 1 implements aggregate expression arguments",
    ):
        assert forbidden not in plan
