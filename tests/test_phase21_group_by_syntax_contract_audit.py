from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-21-group-by-contract-planning.md"


def _read() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized() -> str:
    return " ".join(_read().split())


def test_phase21_slice2_contract_status_is_documented() -> None:
    plan = _normalized()

    for required in (
        "Phase 21 Slice 2 is complete as GROUP BY syntax and clause-scope contract work only",
        "These slices are docs/audit only",
        "They do not implement GROUP BY or any compiler behavior",
        "Slice 2: Syntax And Clause-Scope Contract**: complete as docs/audit only",
    ):
        assert required in plan


def test_group_by_block_is_locked_as_future_syntax() -> None:
    plan = _normalized()

    for required in (
        "Slice 2 selects **Option A: `group by:`** as the future syntax direction",
        "group by:",
        "after `where` and before `select`",
        "from where group by select order by limit",
        "A future `group by:` block must be non-empty",
    ):
        assert required in plan


def test_rejected_syntax_options_are_recorded() -> None:
    plan = _normalized()

    for required in (
        "Option B: `group:` block",
        "Option C: select-driven inferred grouping",
        "Option D: Malloy-style separated `group_by` / `aggregate` blocks",
        "Rejected",
        "drifts away from Pietto's current `select:` projection model",
    ):
        assert required in plan


def test_group_key_allowed_and_disallowed_forms_are_locked() -> None:
    plan = _normalized()

    for required in (
        "V1 group keys allow only input-scope fields",
        "direct field, such as `status`",
        "existing single-input qualified field, such as `orders.region`",
        "literals",
        "arbitrary expressions",
        "scalar calls",
        "aggregate calls",
        "projection aliases",
        "relationship fields or relationship metadata names",
        "multi-input references",
        "future relation-role references",
    ):
        assert required in plan


def test_select_where_order_by_and_limit_scope_rules_are_locked() -> None:
    plan = _normalized()

    for required in (
        "group key projections are allowed",
        "aggregate projections are allowed",
        "aggregate projections still require explicit aliases",
        "mixed group key and aggregate projections are allowed",
        "non-grouped plain fields are rejected",
        "pure grouping or distinct-style output without any aggregate remains deferred",
        "`where` remains an input row-level predicate before grouping",
        "aggregates remain invalid in `where`",
        "grouped `order by` is deferred in v1",
        "existing non-grouped `order by` remains input-scope and unchanged",
        "`limit` remains after the grouped result",
    ):
        assert required in plan


def test_future_valid_examples_are_documented() -> None:
    text = _read()

    for required in (
        "table order_counts:",
        "    group by:\n        status",
        "        total = count()",
        "table revenue_by_region:",
        "    group by:\n        orders.region",
        "        region = orders.region",
        "        revenue = sum(amount)",
    ):
        assert required in text


def test_future_invalid_examples_are_documented() -> None:
    text = _read()

    for required in (
        "lower(status)",
        "Diagnostic category: unsupported group key expression.",
        "Diagnostic category: unsupported group key literal.",
        "group by:\n        count()",
        "Diagnostic category: aggregate call in group key.",
        "customer_id",
        "Diagnostic category: selected field is neither a group key nor an aggregate.",
        "Diagnostic category: aggregate projection requires an explicit alias.",
        "where count() > 0",
        "Diagnostic category: aggregate in input row-level predicate.",
        "Diagnostic category: grouped `order by` is deferred for v1.",
    ):
        assert required in text


def test_diagnostic_categories_are_descriptive_only() -> None:
    plan = _normalized()

    for required in (
        "Slice 2 reserves no new diagnostic codes",
        "Future implementation should define codes only when semantic behavior is authorized",
        "invalid group key form",
        "unknown group field",
        "duplicate group key",
        "unknown-child cascade suppression",
    ):
        assert required in plan


def test_future_implementation_touchpoints_are_named_without_edits() -> None:
    plan = _normalized()

    for required in (
        "Future implementation is not part of Slice 2",
        "grammar, parser, generated ANTLR files, AST nodes, and AST building",
        "semantic relation schema propagation and aggregate validation",
        "Semantic IR relation model and lowering",
        "PostgreSQL and MySQL SQL relation renderers",
        "CLI integration, SQL goldens, fixture inventory, and focused tests",
    ):
        assert required in plan


def test_slice2_hard_non_goals_remain_locked() -> None:
    plan = _normalized()

    for required in (
        "GROUP BY implementation",
        "grammar or source syntax changes",
        "generated ANTLR changes",
        "parser or AST changes",
        "semantic model changes",
        "Semantic IR model, export, builder, or lowering changes",
        "PostgreSQL or MySQL SQL renderer changes",
        "CLI, JSON, or public API changes",
        "fixture, SQL golden, or `scripts/check_goldens.py` changes",
        "new diagnostic codes",
        "SQL HAVING user syntax",
        "`satisfying`, `filter`, post-select `where`, or `such that` implementation",
        "relationship-driven query behavior",
        "aggregate expression argument implementation",
        "Decimal aggregate semantics",
        "rollup, cube, or grouping sets",
        "window functions",
        "nested results",
        "runtime or database execution",
    ):
        assert required in plan
