from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-18-aggregate-readiness-audit.md"


def _plan_text() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized_plan_text() -> str:
    return " ".join(_plan_text().split())


def test_phase18_plan_exists_and_locks_audit_contract() -> None:
    assert PLAN_PATH.is_file()

    plan = _normalized_plan_text()
    assert "Phase 18 is audit/contract only" in plan
    assert "Phase 18 does not authorize production aggregate implementation" in plan
    assert "reserves no final `PIE-*` diagnostic codes" in plan


def test_current_source_examples_use_accepted_table_syntax() -> None:
    plan = _plan_text()
    normalized = _normalized_plan_text()

    assert "table paid_order_stats:" in plan
    assert "```pietto\nrelation paid_order_stats:" not in plan
    assert "Do not use `relation paid_order_stats:` as a Pietto source" in normalized
    assert (
        'The word "relation" may be used in semantic model prose for existing '
        "relation concepts"
    ) in normalized


def test_aggregate_names_remain_unimplemented_in_phase18() -> None:
    plan = _normalized_plan_text()

    assert "`count`, `sum`, and `avg` are not implemented aggregate functions" in plan
    assert "must remain semantically unknown throughout Phase 18" in plan
    assert (
        "must not add them to the production scalar built-in function catalog" in plan
    )


def test_satisfying_and_result_predicates_remain_deferred() -> None:
    plan = _normalized_plan_text()

    assert "`satisfying` is only a provisional future design direction" in plan
    assert "It is not implemented, not parsed" in plan
    assert "Pietto should not expose SQL HAVING as user syntax" in plan


def test_grammar_generated_and_sql_outputs_are_unchanged_by_slice1() -> None:
    plan = _normalized_plan_text()

    assert "No grammar change, generated ANTLR change" in plan
    assert "No SQL renderer files, SQL golden fixtures" in plan
    assert "Phase 18 Slice 1 does not change production code" in plan
