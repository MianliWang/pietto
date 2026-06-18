from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-25-result-predicate-satisfying-mvp.md"


def _read() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized() -> str:
    return " ".join(_read().split())


def test_phase25_slice1_plan_exists_and_records_baseline() -> None:
    assert PLAN_PATH.is_file()

    plan = _normalized()
    for required in (
        "Phase 25 Result Predicate / satisfying Contract-First MVP",
        "Phase 25 Slice 1 is complete as candidate decision and exact contract work only",
        "HEAD: `64c0bbebfaa428338ff31e78261e17aebafd9310`",
        "Phase 24 Aggregate Function Expansion II is complete",
        "aggregate expression arguments remain deferred through `PIE-S2315`",
    ):
        assert required in plan


def test_slice1_is_contract_only_without_behavior_changes() -> None:
    plan = _normalized()

    for required in (
        "It does not implement `satisfying`, parse `satisfying:`, lower HAVING, or change compiler behavior",
        "Slice 1 changes no grammar, generated ANTLR, AST, AST builder, semantic analysis, Semantic IR, SQL backend, CLI behavior, JSON schema, JSON output behavior, fixture, golden, script, dependency, lockfile, package metadata, CI, Makefile, project config, runtime/database behavior, schema introspection, project/multi-file behavior, UI, LSP, public MySQL API, or relationship/JOIN behavior",
        "This Slice 1 decision does not implement `satisfying`",
        "It records the future implementation contract so later slices can remain narrow and auditable",
    ):
        assert required in plan


def test_candidate_comparison_selects_contract_first_satisfying_mvp() -> None:
    plan = _normalized()

    for required in (
        "Contract-first GROUP BY-only `satisfying` MVP",
        "Docs/static-audit-only readiness phase",
        "Aggregate expression arguments first",
        "Direct SQL `having` source syntax",
        "JOIN/relationship-aware result predicates",
        "Chosen for Phase 25",
        "Phase 25 selects **Result Predicate / `satisfying` Contract-First MVP** as the next core language direction",
    ):
        assert required in plan


def test_satisfying_source_order_and_group_by_only_contract_are_locked() -> None:
    plan = _normalized()

    for required in (
        "`satisfying:` is a colon-plus-indentation relation clause containing one predicate expression",
        "Pietto does not expose a source-level `having` keyword or `HAVING:` clause",
        "from where group by select satisfying order by limit",
        "`satisfying:` appears only after `select:` and before `order by:` / `limit`",
        "The MVP is GROUP BY-only",
        "A relation with `satisfying:` and no `group by:` remains deferred",
    ):
        assert required in plan


def test_satisfying_scope_is_select_output_names_only() -> None:
    plan = _normalized()

    for required in (
        "The MVP satisfying scope is select output names only",
        "group-key projection output names",
        "direct aggregate projection output names",
        "`r = region` makes `r` visible to `satisfying`, not `region`",
        "input row fields that are not select outputs",
        "row-level non-group fields",
        "dotted field references such as `orders.region`",
        "projection aliases that name computed scalar expressions",
    ):
        assert required in plan


def test_predicate_subset_and_deferred_expression_forms_are_locked() -> None:
    plan = _normalized()

    for required in (
        "select output names, scalar literals, parentheses, comparisons, `between`, `is null`, `is not null`, and existing Boolean `and` / `or` composition",
        "direct aggregate calls",
        "scalar calls",
        "arithmetic",
        "unary operators",
        "`like`",
        "standalone `not`",
        "aggregate composition",
        "projection alias composition",
        "The satisfying predicate must type as Bool when known",
    ):
        assert required in plan


def test_ir_and_sql_contract_avoids_premature_name_and_format_locking() -> None:
    plan = _normalized()

    for required in (
        "A possible name is `RelationIR.result_filter`, but Slice 1 deliberately does not hard-lock a concrete class or field name",
        "Final naming belongs to the IR implementation slice",
        "selected SQL backends render the result predicate after `GROUP BY` and before `ORDER BY` / `LIMIT`",
        "SQL lowering must not rely on SELECT aliases being portable in HAVING",
        "Slice 1 does not hard-lock exact SQL formatting, line breaks, or indentation",
    ):
        assert required in plan


def test_diagnostics_recommendation_preserves_existing_aggregate_codes() -> None:
    plan = _normalized()

    for required in (
        "Slice 1 does not implement or reserve final diagnostics",
        "direct aggregate calls inside `satisfying:` should reuse `PIE-S2308`",
        "existing aggregate projection diagnostics `PIE-S2309` through `PIE-S2315` should remain unchanged",
        "known non-Bool satisfying predicates should reuse `PIE-S2202`",
        "New satisfying diagnostics should be reserved for scope and predicate-shape errors",
    ):
        assert required in plan


def test_required_non_goals_remain_explicitly_deferred() -> None:
    plan = _normalized()

    for required in (
        "no-GROUP satisfying",
        "direct aggregate calls inside `satisfying`",
        "aggregate expression arguments",
        "generic SQL `HAVING` source syntax",
        "dotted field references inside satisfying",
        "row-level non-group field references inside satisfying",
        "nested aggregates",
        "JOIN or relationship traversal",
        "runtime/database execution",
        "schema introspection",
        "project or multi-file implementation",
        "public MySQL API expansion",
        "JSON schema changes",
    ):
        assert required in plan


def test_future_slice_sequence_is_recorded_without_implementing_slice2() -> None:
    plan = _normalized()

    for required in (
        "Slice 1: Candidate Decision And Exact Contract",
        "Slice 2: Parser And AST",
        "Slice 3: Semantic Validation",
        "Slice 4: IR Representation And Alias Normalization",
        "Slice 5: PostgreSQL And Private MySQL SQL Lowering",
        "Slice 6: CLI / JSON / Output Hardening",
        "Slice 7: Completion Audit And Status Lock",
        "future implementation slice",
    ):
        assert required in plan


def test_slice1_does_not_claim_satisfying_is_implemented() -> None:
    plan = _normalized()

    for forbidden in (
        "satisfying is implemented",
        "implements satisfying",
        "satisfying implementation is complete",
        "Phase 25 implements satisfying",
        "HAVING lowering is implemented",
        "implements HAVING lowering",
        "JSON schema is changed",
    ):
        assert forbidden not in plan
