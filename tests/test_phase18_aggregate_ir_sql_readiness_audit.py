from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "docs/spec/aggregate-ir-sql-readiness-contract-v1.md"


def _contract_text() -> str:
    return CONTRACT_PATH.read_text(encoding="utf-8")


def _normalized_contract_text() -> str:
    return " ".join(_contract_text().split())


def test_contract_exists_and_locks_docs_only_scope() -> None:
    assert CONTRACT_PATH.is_file()

    contract = _normalized_contract_text()
    assert "Phase 18 Slice 3 is docs/static-audit only" in contract
    assert "No aggregate IR or SQL behavior is implemented" in contract
    assert "No production compiler code changes are part of Slice 3" in contract


def test_source_examples_use_current_table_syntax() -> None:
    contract = _contract_text()
    normalized = _normalized_contract_text()

    assert "table paid_order_stats:" in contract
    assert "```pietto\nrelation paid_order_stats:" not in contract
    assert "Do not use `relation paid_order_stats:` as Pietto source syntax" in (
        normalized
    )


def test_current_ir_facts_are_documented_without_implementation() -> None:
    contract = _normalized_contract_text()

    for required in (
        "generic call-shaped expression representation such as `CallIR`",
        "`CallIR` is currently ordinary call-shaped IR with no aggregate semantics",
        "row-shaped relation representation such as `RelationIR`",
        "row schema representation such as `RowSchemaIR`",
        "There is no aggregate-specific IR node today",
        "There is no aggregate mode/cardinality marker today",
        "There is no no-GROUP one-row aggregate relation contract encoded in IR",
        "Current aggregate names are not lowered specially",
    ):
        assert required in contract


def test_future_ir_shapes_are_provisional_not_chosen() -> None:
    contract = _normalized_contract_text()

    for required in (
        "an aggregate expression node such as `AggregateCallIR`",
        "aggregate-specific projection representation",
        "relation-level aggregate/no-GROUP mode",
        "explicit one-logical-row cardinality metadata",
        "output schema derived from aggregate projection aliases",
        "Slice 3 does not choose a final implementation design",
        "A later approved implementation slice must choose the concrete IR shape",
    ):
        assert required in contract


def test_cardinality_and_schema_contract_are_documented() -> None:
    contract = _normalized_contract_text()

    for required in (
        "Future no-GROUP aggregate output is one logical row",
        "not row-preserving output from the input relation",
        "output schema comes from aggregate projection aliases",
        "Downstream relations may bind aggregate aliases after schema propagation",
        "Mixed plain input fields and aggregate projections fail without GROUP BY",
        "IR row schema consistency must remain stable and diagnostic-first",
    ):
        assert required in contract


def test_sql_backend_readiness_boundaries_are_documented() -> None:
    contract = _normalized_contract_text()

    for required in (
        "SQL `AS` is backend SQL syntax only",
        "Pietto source syntax still has no source-level `as` or `AS`",
        "No SQL renderer changes are made in Slice 3",
        "No SQL golden changes are made in Slice 3",
        "The no-GROUP MVP has no GROUP BY",
        "user-facing SQL HAVING syntax",
        "`where` remains input row-level filtering and lowers to SQL `WHERE`",
        "Result-level predicate design remains deferred",
        "`satisfying` remains provisional, unparsed, and unimplemented",
    ):
        assert required in contract


def test_dialect_and_future_test_readiness_are_documented() -> None:
    contract = _normalized_contract_text()

    for required in (
        "Future `count()` should likely lower to backend `COUNT(*)`",
        "Stable alias rendering and quoting rules must remain byte-stable",
        "PostgreSQL and MySQL physical return types for `SUM` and `AVG` may differ",
        "dialect-specific casts are needed to preserve Pietto logical types",
        "Decimal aggregate semantics are out of the future no-GROUP MVP",
        "Future golden tests must prove no unrelated SQL output changes",
        "IR representation of aggregate projections",
        "relation row schema propagation for aggregate output aliases",
        "downstream binding of aggregate aliases",
        "PostgreSQL no-GROUP aggregate SQL output",
        "MySQL no-GROUP aggregate SQL output",
        "invalid aggregate contexts",
        "mixed aggregate and non-aggregate projections",
        "nested aggregate calls",
        "wrong aggregate arity",
        "wrong aggregate argument type",
        "unchanged unrelated SQL goldens",
    ):
        assert required in contract
    assert "Pietto currently has no Decimal type" not in contract


def test_diagnostics_and_non_goals_keep_boundaries_closed() -> None:
    contract = _normalized_contract_text()

    assert "reserves no final `PIE-*` diagnostic codes" in contract
    for required in (
        "aggregate implementation",
        "aggregate semantics",
        "`AggregateCallIR` implementation",
        "IR model, IR lowering, or IR builder changes",
        "SQL renderer changes",
        "SQL golden fixture changes",
        "grammar changes",
        "generated ANTLR updates",
        "`count`, `sum`, or `avg` scalar built-ins",
        "final aggregate diagnostic code reservations",
        "`satisfying` implementation",
        "GROUP BY",
        "SQL HAVING user syntax",
        "`filter`",
        "post-select `where`",
        "JOIN",
        "relationship-driven query behavior",
        "source connector syntax changes",
        "Pietto source-level `as` or `AS`",
        "runtime behavior",
        "database execution",
    ):
        assert required in contract
