from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-23-count-field-aggregate-mvp.md"


def _read() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized() -> str:
    return " ".join(_read().split())


def test_phase23_slice1_plan_exists_and_names_count_field_mvp() -> None:
    assert PLAN_PATH.is_file()

    plan = _normalized()
    for required in (
        "Phase 23 Slice 1 is complete as candidate decision and contract work only",
        "Phase 23 selects **`count(field)` Aggregate MVP** as the next core language direction",
        "`count(field)` aggregate MVP",
        "Implementation-ready after this Slice 1 contract",
    ):
        assert required in plan


def test_slice1_is_contract_only_without_behavior_changes() -> None:
    plan = _normalized()

    for required in (
        "It does not implement semantic behavior, Semantic IR behavior, SQL renderer behavior, CLI behavior, JSON behavior, runtime behavior, database behavior, fixtures, or goldens",
        "Slice 1 changes no grammar, generated ANTLR, AST, semantic production code, Semantic IR production code, SQL renderer, CLI behavior, JSON schema, fixture, golden, `scripts/check_goldens.py` inventory, dependency, lockfile, package metadata, CI, backend registry behavior, runtime/database behavior, UI, LSP, policy/security DSL, or relationship query behavior",
        "This decision does not implement `count(field)`",
        "It records the future implementation contract so later slices can remain narrow and auditable",
    ):
        assert required in plan


def test_count_star_semantics_are_preserved() -> None:
    plan = _normalized()

    for required in (
        "`count()` remains valid",
        "`count()` means SQL `COUNT(*)`",
        "`count()` counts all input rows",
        "`count()` result type remains `Int not null`",
        "`count() -> Int not null`",
        "PostgreSQL continues rendering `count()` as `COUNT(*)`",
        "MySQL continues rendering `count()` as `COUNT(*)`",
    ):
        assert required in plan


def test_count_field_non_null_counting_contract_is_locked() -> None:
    plan = _normalized()

    for required in (
        "`count(field)` means SQL `COUNT(field)`",
        "`count(field)` counts non-null field values",
        "`count(field)` result type is `Int not null`",
        "`count(field) -> Int not null`",
        "`count(source.field) -> Int not null`",
        "SQL `COUNT(field)` counts non-null field values",
        "The `count(field)` result is non-null because SQL `COUNT(expr)` returns `0` when no input expression value is counted",
    ):
        assert required in plan


def test_accepted_projection_shapes_and_contexts_are_locked() -> None:
    plan = _normalized()

    for required in (
        "direct aliased aggregate projections only",
        "`alias = count(field)`",
        "`alias = count(source.field)`",
        "no-GROUP aggregate `select:` projections",
        "grouped aggregate `select:` projections",
        "bare field arguments such as `count(amount)`",
        "existing single-input qualified field arguments such as `count(orders.amount)`",
        "zero arguments remain valid only for existing `count()`",
    ):
        assert required in plan


def test_argument_policy_allows_concrete_types_and_excludes_any_unknown_unresolved() -> (
    None
):
    plan = _normalized()

    for required in (
        "the direct field policy matches the existing `sum`/`avg`/`min`/`max` aggregate policy",
        "all concrete bound field types are allowed except `Any`",
        "`Any` is rejected",
        "`Unknown` is rejected",
        "unresolved fields are rejected",
        "projection aliases are not accepted as aggregate arguments",
    ):
        assert required in plan


def test_existing_aggregate_diagnostics_are_reused_without_new_expected_code() -> None:
    plan = _normalized()

    for required in (
        "no new diagnostic code is expected for Slice 1",
        "`PIE-S2308` for invalid aggregate context",
        "`PIE-S2309` for wrong arity",
        "`PIE-S2310` for aggregate composition",
        "`PIE-S2311` for nested aggregate",
        "`PIE-S2312` for mixed no-GROUP aggregate and non-aggregate projections",
        "`PIE-S2313` for unaliased aggregate projections",
        "`PIE-S2314` for unsupported direct field argument type",
        "`PIE-S2315` for expression arguments",
        "add no new diagnostic code unless a later implementation slice proves a concrete diagnostic gap",
        "preserve unknown-child cascade suppression",
    ):
        assert required in plan


def test_deferred_boundaries_cover_required_non_goals() -> None:
    plan = _normalized()

    for required in (
        "`count_distinct(field)`",
        "distinct aggregates or `DISTINCT` syntax",
        "filtered aggregates",
        "aggregate expression arguments such as `count(a + b)` or `count(lower(name))`",
        "nested aggregates",
        "composed aggregate expressions",
        "unnamed aggregate projections",
        "result predicates, `satisfying`, post-select `where`, `such that`, SQL `HAVING`, or any HAVING-like user syntax",
        "grouped `ORDER BY`",
        "JOIN behavior",
        "relationship behavior",
        "relationship-driven query behavior",
        "SQL execution",
        "database connections",
        "runtime behavior",
        "public API expansion",
        "JSON schema changes",
        "CLI option changes",
    ):
        assert required in plan


def test_future_slice_sequence_keeps_implementation_out_of_slice1() -> None:
    plan = _normalized()

    for required in (
        "Slice 1: Count(Field) Candidate Decision And Contract**: complete as docs/static-audit only",
        "Slice 2: Count(Field) Semantic Validation And Row Schema**: future implementation slice",
        "Slice 3: Count(Field) IR Lowering**: future implementation slice",
        "Slice 4: PostgreSQL/MySQL SQL Rendering And Goldens**: future implementation slice",
        "Slice 5: CLI/JSON/Output Hardening**: future tests/audit slice",
        "Slice 6: Completion Audit And Status Lock**: future audit-only slice",
    ):
        assert required in plan


def test_slice1_does_not_claim_count_field_is_implemented() -> None:
    plan = _normalized()

    for forbidden in (
        "count(field) is implemented",
        "implements count(field)",
        "count(field) implementation is complete",
        "Phase 23 implements count(field)",
        "renders COUNT(field) today",
        "semantic validation is complete",
        "IR lowering is complete",
        "SQL rendering is complete",
        "CLI behavior is complete",
        "runtime behavior is complete",
    ):
        assert forbidden not in plan
