from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-26-aggregate-expression-arguments-numeric-foundation.md"
)


def _read(path: Path = PLAN_PATH) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path = PLAN_PATH) -> str:
    return " ".join(_read(path).split())


def test_phase26_slice1_plan_exists_and_records_trusted_baseline() -> None:
    assert PLAN_PATH.is_file()

    plan = _normalized()
    for required in (
        "Phase 26 Aggregate Expression Arguments + Numeric Expression Foundation",
        "Phase 26 Slice 1 is complete as candidate decision, exact contract, "
        "and static audit work only",
        "HEAD: `38c696d0aadc1c5f6b9e41b71e2a441f32c20198`",
        "Phase 25 Result Predicate / `satisfying` MVP is complete",
        "aggregate expression arguments remain deferred through `PIE-S2315`",
    ):
        assert required in plan


def test_slice1_is_contract_only_without_behavior_changes() -> None:
    plan = _normalized()

    for required in (
        "It does not implement numeric expression behavior, aggregate "
        "expression arguments, Semantic IR behavior, SQL renderer behavior, "
        "CLI behavior, JSON behavior, runtime behavior, database behavior, "
        "fixtures, or goldens",
        "Slice 1 changes no grammar, generated ANTLR, AST, AST builder, "
        "semantic implementation, Semantic IR implementation, SQL backend, "
        "CLI implementation, JSON schema, JSON serializer, fixture, golden, "
        "script, dependency, lockfile, package metadata, CI, Makefile/config",
        "This Slice 1 decision does not implement numeric expression behavior, "
        "aggregate expression arguments, IR lowering, SQL lowering, CLI "
        "behavior, JSON behavior, fixtures, or goldens",
    ):
        assert required in plan


def test_candidate_comparison_selects_combined_mvp() -> None:
    plan = _normalized()

    for required in (
        "A. Numeric scalar expression foundation first, no aggregate "
        "expression args yet",
        "B. Aggregate expression arguments first, only for already-typed expressions",
        "C. Combined MVP: numeric expression foundation + aggregate expression args",
        "D. Defer aggregate expression args and do data science scalar functions first",
        "Chosen for Phase 26",
        "Phase 26 selects **Aggregate Expression Arguments + Numeric "
        "Expression Foundation** using the **Combined MVP** scope",
        "Implementation-ready after this Slice 1 contract",
    ):
        assert required in plan


def test_numeric_scalar_contract_and_projection_boundary_are_locked() -> None:
    plan = _normalized()

    for required in (
        "Phase 26 numeric scalar expression work is allowed to affect ordinary "
        "scalar expressions and computed projections",
        "It is not limited to aggregate arguments",
        "Aggregate expression arguments then reuse typed scalar expressions "
        "through a separate aggregate-argument shape gate",
        "`Int + Int -> Int`",
        "`Int - Int -> Int`",
        "`Int * Int -> Int`",
        "`Float + Float -> Float`",
        "`Float - Float -> Float`",
        "`Float * Float -> Float`",
        "`Int + Float -> Float`",
        "`Float + Int -> Float`",
        "`Int * Float -> Float`",
        "`Float * Int -> Float`",
        "Phase 26 does not authorize modulo inside aggregate expression arguments",
    ):
        assert required in plan


def test_decimal_contract_and_deferrals_are_locked() -> None:
    plan = _normalized()

    for required in (
        "`Decimal + Decimal -> Decimal`",
        "`Decimal - Decimal -> Decimal`",
        "`Decimal * Decimal`",
        "`Decimal * Int`",
        "`Int * Decimal`",
        "`Float + Decimal`",
        "`Decimal + Float`",
        "`Decimal / Decimal`",
        "Decimal precision/scale modeling",
        "Pietto currently has a logical `Decimal` type but no precision or "
        "scale carrier in `ResolvedType`",
        "Multiplication, mixed Decimal promotion, and division would imply "
        "scale, rounding, or dialect precision semantics",
    ):
        assert required in plan


def test_aggregate_expression_argument_mvp_and_deferrals_are_locked() -> None:
    plan = _normalized()

    for required in (
        "`sum(numeric_expression)`",
        "`avg(numeric_expression)`",
        "`count_distinct(text_transform_expression)`",
        "The aggregate expression argument must contain at least one direct "
        "input field reference",
        "must not be a standalone literal argument such as `avg(1)`",
        "Projection aliases are not aggregate argument leaves",
        "`count(expression)`",
        "`min(expression)`",
        "`max(expression)`",
        "`count(distinct field)` syntax",
        "generic `DISTINCT` syntax",
        "aggregate modifiers",
        "nested aggregates",
        "aggregate composition",
        "all division inside aggregate arguments",
    ):
        assert required in plan


def test_count_distinct_text_transform_contract_uses_existing_renderer_evidence() -> (
    None
):
    plan = _normalized()
    semantic_functions = _read(REPO_ROOT / "tests/test_semantic_functions.py")
    postgres_expressions = _read(REPO_ROOT / "tests/test_sql_postgres_expressions.py")
    mysql_expressions = _read(REPO_ROOT / "tests/test_sql_mysql_expressions.py")

    for required in (
        "`lower(text_field)`",
        "`trim(text_field)`",
        "`lower(trim(text_field))`",
        "equivalent nested chains composed only of `lower` and `trim`",
        "The nested `lower` / `trim` chain is included because current semantic "
        "tests and both SQL expression renderer tests already cover recursive "
        "`lower(trim(field))` support for PostgreSQL and private MySQL",
        "`len(...)` or `matches(...)` inside `count_distinct` expression arguments",
    ):
        assert required in plan

    assert "test_nested_lower_trim_returns_text_and_records_inner_call" in (
        semantic_functions
    )
    assert "test_lower_and_trim_calls_render_recursively" in postgres_expressions
    assert "test_approved_function_mappings_are_uppercase_and_recursive" in (
        mysql_expressions
    )


def test_satisfying_interaction_and_diagnostic_precedence_are_locked() -> None:
    plan = _normalized()

    for required in (
        "This should become accepted once the `sum(amount + tax)` select "
        "projection is accepted by later Phase 26 slices",
        "`satisfying:` clause continues to resolve `total` as a select output name",
        "preserving the Phase 25 rule that HAVING does not rely on SELECT alias "
        "portability",
        "Direct aggregate calls inside `satisfying:` remain rejected",
        "The primary diagnostic for that shape remains `PIE-S2308`",
    ):
        assert required in plan


def test_diagnostics_transition_preserves_existing_aggregate_codes() -> None:
    plan = _normalized()

    for required in (
        "`PIE-S2315` is retired only for allowed aggregate expression arguments",
        "`PIE-S2315` remains for unsupported aggregate expression arguments",
        "`PIE-S2311` remains the nested aggregate diagnostic",
        "`PIE-S2310` remains the aggregate composition diagnostic",
        "`PIE-S2314` remains the aggregate argument type mismatch diagnostic",
        "`PIE-S2308` remains the diagnostic for direct aggregate calls inside "
        "`satisfying:`",
        "`sum(amount / tax)` remains deferred through `PIE-S2315`",
        "`sum(lower(status))` reports `PIE-S2314`",
        "`sum(avg(amount))` reports `PIE-S2311`",
        "`sum(amount) + 1` reports `PIE-S2310`",
        "`satisfying: sum(amount + tax) > 1000` reports `PIE-S2308`",
        "Unknown children continue to suppress aggregate cascade diagnostics",
    ):
        assert required in plan


def test_semantic_ir_sql_and_cli_contracts_are_locked() -> None:
    plan = _normalized()

    for required in (
        "`sum(Int expression) -> Int nullable`",
        "`sum(Float expression) -> Float nullable`",
        "`sum(Decimal expression) -> Decimal nullable`",
        "`avg(Int expression) -> Float nullable`",
        "`avg(Float expression) -> Float nullable`",
        "`avg(Decimal expression) -> Decimal nullable`",
        "`count_distinct(Text transform expression) -> Int not null`",
        "`AggregateCallIR.arguments` already stores `tuple[ExpressionIR, ...]`",
        '`sum(amount + tax)` lowers as `AggregateCallIR("sum", (BinaryIR(...),), ...)`',
        "PostgreSQL and private MySQL SQL lowering should reuse the existing "
        "nested expression rendering policy",
        "Phase 26 does not change JSON v1 schema, stdout/stderr separation, "
        "CLI option names, selected dialect values, or output-file safety rules",
    ):
        assert required in plan


def test_fixture_golden_policy_and_slice_plan_are_locked() -> None:
    plan = _normalized()

    for required in (
        "Slice 7 uses focused inline SQL assertions rather than new fixtures or goldens",
        "Existing SQL fixtures and goldens remain unchanged and continue to be "
        "audited by `scripts/check_goldens.py`",
        "adding new golden files requires updating the explicit "
        "`scripts/check_goldens.py` inventory",
        "Slice 1: Candidate Decision, Exact Contract, And Static Audit",
        "Slice 2: Numeric Scalar Expression Semantics",
        "Slice 3: Decimal Arithmetic Subset",
        "Slice 4: `sum` / `avg` Aggregate Expression Semantics",
        "Slice 5: `count_distinct` Text Transform Expression Semantics",
        "Slice 6: Aggregate Expression Argument IR Lowering",
        "Slice 7: PostgreSQL And Private MySQL SQL Lowering",
        "Slice 8: CLI / JSON / Output And `satisfying` Hardening",
        "Slice 9: Completion Audit And Status Lock",
    ):
        assert required in plan


def test_bounded_slice_matrix_and_non_goals_are_locked() -> None:
    plan = _normalized()

    for required in (
        "GREEN files and directories",
        "YELLOW files and directories",
        "RED files and directories",
        "grammar and generated ANTLR files",
        "AST nodes and AST builder",
        "public SQL exports",
        "dependencies, lockfile, package metadata, CI, Makefile/config",
        "runtime/database, connector execution, schema introspection",
        "project/multi-file, LSP, UI, playground",
        "relationship/JOIN implementation",
        "generic DISTINCT, aggregate modifiers, window functions, median, "
        "percentile, Decimal precision/scale, and casts",
        "public MySQL API expansion",
        "public MySQL CLI exposure or new CLI dialect option",
    ):
        assert required in plan


def test_current_phase24_readiness_lock_remains_deferred_until_later_slices() -> None:
    phase24_readiness = _read(
        REPO_ROOT / "tests/test_phase24_aggregate_expression_arguments_readiness.py"
    )

    for required in (
        "`sum(amount + amount)` remains `PIE-S2315`",
        "`avg(amount + amount)` remains `PIE-S2315`",
        '("value = count_distinct(len(status))", "count_distinct")',
        "test_aggregate_expression_arguments_still_fail_with_s2315",
    ):
        assert required in phase24_readiness


def test_slice1_does_not_claim_later_behavior_is_implemented() -> None:
    plan = _normalized()

    for forbidden in (
        "Slice 1 implements numeric expression behavior",
        "Slice 1 implements aggregate expression arguments",
        "Slice 1 implements IR lowering",
        "Slice 1 implements SQL lowering",
        "Slice 1 implements CLI behavior",
        "Slice 1 implements JSON behavior",
        "Slice 1 adds fixtures",
        "Slice 1 adds goldens",
        "Phase 26 implements JOIN",
        "Phase 26 implements runtime/database execution",
        "Phase 26 implements schema introspection",
        "Phase 26 implements generic DISTINCT syntax",
        "Phase 26 implements Decimal precision/scale modeling",
    ):
        assert forbidden not in plan
