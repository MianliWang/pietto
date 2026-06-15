from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = REPO_ROOT / "docs/plan/phase-18-aggregate-readiness-audit.md"
SEMANTIC_CONTRACT_PATH = REPO_ROOT / "docs/spec/aggregate-semantic-contract-v1.md"
IR_SQL_CONTRACT_PATH = REPO_ROOT / "docs/spec/aggregate-ir-sql-readiness-contract-v1.md"

PHASE18_AUDIT_TESTS = (
    REPO_ROOT / "tests/test_phase18_aggregate_readiness_audit.py",
    REPO_ROOT / "tests/test_phase18_aggregate_semantic_contract_audit.py",
    REPO_ROOT / "tests/test_phase18_aggregate_ir_sql_readiness_audit.py",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def _combined_docs() -> str:
    return " ".join(
        (
            _normalized(PLAN_PATH),
            _normalized(SEMANTIC_CONTRACT_PATH),
            _normalized(IR_SQL_CONTRACT_PATH),
        )
    )


def test_phase18_docs_and_static_audit_tests_exist() -> None:
    for path in (
        PLAN_PATH,
        SEMANTIC_CONTRACT_PATH,
        IR_SQL_CONTRACT_PATH,
        *PHASE18_AUDIT_TESTS,
    ):
        assert path.is_file()


def test_phase18_completion_status_is_documented() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Phase 18 Slice 4 is complete as result-predicate deferral and completion audit",
        "Phase 18 is complete as audit/contract-only aggregate readiness work",
        "aggregate readiness master plan",
        "aggregate semantic contract",
        "aggregate IR and SQL readiness contract",
        "focused static audit tests",
    ):
        assert required in plan


def test_phase18_remains_audit_contract_only() -> None:
    docs = _combined_docs()

    for required in (
        "Phase 18 is audit/contract only",
        "implements no aggregate behavior",
        "No aggregate IR or SQL behavior is implemented",
        "does not authorize production aggregate implementation",
        "adds no aggregate behavior",
    ):
        assert required in docs


def test_source_examples_keep_current_table_syntax() -> None:
    docs_text = "\n".join(
        (_read(PLAN_PATH), _read(SEMANTIC_CONTRACT_PATH), _read(IR_SQL_CONTRACT_PATH))
    )
    docs = _combined_docs()

    assert "table paid_order_stats:" in docs_text
    assert "```pietto\nrelation paid_order_stats:" not in docs_text
    assert "Do not use `relation paid_order_stats:` as Pietto source syntax" in docs


def test_decimal_and_diagnostic_code_boundaries_are_preserved() -> None:
    docs = _combined_docs()

    assert "Pietto currently has no Decimal type" not in docs
    assert "Decimal exists in Pietto's built-in type catalog" in docs
    assert "reserves no final `PIE-*` diagnostic codes" in docs
    assert "final aggregate diagnostic code reservations" in docs


def test_sql_source_syntax_and_renderer_boundaries_are_preserved() -> None:
    docs = _combined_docs()

    for required in (
        "SQL `AS` is backend SQL syntax only",
        "Pietto source syntax still has no source-level `as` or `AS`",
        "No SQL renderer changes",
        "No SQL golden changes",
        "No SQL renderer files, SQL golden fixtures",
    ):
        assert required in docs


def test_result_predicates_remain_deferred() -> None:
    docs = _combined_docs()

    for required in (
        "`satisfying` remains provisional, unparsed, unimplemented",
        "outside any Phase 19 no-GROUP aggregate MVP unless separately approved",
        "`where` remains input row-level filtering",
        "Result-level predicate design remains open",
        "Pietto should not expose SQL HAVING as user syntax",
        "`satisfying`, post-select `where`, `such that`, and `filter` remain future design discussion only",
        "`filter` should not be introduced casually because it is too dataframe-like",
    ):
        assert required in docs


def test_deferred_behavior_and_relationship_boundaries_are_preserved() -> None:
    docs = _combined_docs()

    for required in (
        "No GROUP BY",
        "No SQL HAVING user syntax",
        "post-select `where`",
        "`filter`",
        "No JOIN",
        "relationship-driven query behavior",
        "Relationship metadata remains read-only metadata",
        "runtime behavior",
        "database execution",
    ):
        assert required in docs


def test_phase19_handoff_is_conservative() -> None:
    plan = _normalized(PLAN_PATH)

    for required in (
        "Future aggregate implementation should start with no-GROUP `count()` first",
        "`sum` and `avg` may follow in later slices",
        "after the aggregate framework is stable",
        "GROUP BY, result predicates, JOIN, relationship-driven behavior",
        "remain deferred unless separately approved",
    ):
        assert required in plan
