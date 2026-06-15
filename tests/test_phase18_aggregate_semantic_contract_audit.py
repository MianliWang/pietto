from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "docs/spec/aggregate-semantic-contract-v1.md"


def _contract_text() -> str:
    return CONTRACT_PATH.read_text(encoding="utf-8")


def _normalized_contract_text() -> str:
    return " ".join(_contract_text().split())


def test_contract_exists_and_locks_docs_only_scope() -> None:
    assert CONTRACT_PATH.is_file()

    contract = _normalized_contract_text()
    assert "Phase 18 Slice 2 is docs/static-audit only" in contract
    assert "implements no aggregate behavior" in contract
    assert "This contract changes no grammar, generated ANTLR files" in contract


def test_source_examples_use_current_table_syntax() -> None:
    contract = _contract_text()
    normalized = _normalized_contract_text()

    assert "table paid_order_stats:" in contract
    assert "```pietto\nrelation paid_order_stats:" not in contract
    assert "Do not use `relation paid_order_stats:` as Pietto source syntax" in (
        normalized
    )


def test_aggregate_recognition_is_semantically_special_not_scalar_builtin() -> None:
    contract = _normalized_contract_text()

    assert "Future aggregate names are semantically special" in contract
    assert "They are not ordinary scalar built-ins" in contract
    assert (
        "must not add `count`, `sum`, or `avg` to production `BUILTIN_FUNCTIONS`"
        in contract
    )
    assert "current semantic behavior remains unknown-function diagnostics" in contract


def test_future_mvp_shape_and_deferred_contexts_are_documented() -> None:
    contract = _normalized_contract_text()

    for required in (
        "Aggregate projections are allowed only inside `select:`",
        "Aggregate projections must be direct named projections",
        "The relation has exactly one input",
        "No GROUP BY",
        "No JOIN",
        "No relationship-driven query behavior",
        "aggregate calls in `where`",
        "aggregate calls in shape `check`",
        "aggregate calls in `derive`",
        "aggregate calls in source metadata",
        "aggregate calls in relationship metadata",
        "aggregate calls as ordinary scalar function arguments",
        "aggregate calls in input-scope `order by`",
        "unaliased aggregate projections",
        "nested aggregate calls",
        "mixed aggregate and non-aggregate field projections",
        "aggregate composition such as `total = count() + 1`",
        "arbitrary scalar expressions inside `sum` and `avg`",
    ):
        assert required in contract


def test_argument_type_and_nullability_contracts_are_documented() -> None:
    contract = _normalized_contract_text()

    for required in (
        "`count()` accepts zero arguments only",
        "`sum(field)` accepts one direct numeric field reference only",
        "`avg(field)` accepts one direct numeric field reference only",
        "Valid single-input qualified fields such as `orders.amount` are allowed",
        "source-level `count(*)`",
        "Decimal aggregate semantics",
        "`count()` | `Int not null`",
        "`sum(Int)` | `Int nullable`",
        "`sum(Float)` | `Float nullable`",
        "`avg(Int)` | `Float nullable`",
        "`avg(Float)` | `Float nullable`",
        "`count()` over empty input returns `0`",
        "`sum` and `avg` over empty input are conservatively nullable",
        "PostgreSQL and MySQL concrete return types may differ",
    ):
        assert required in contract


def test_diagnostics_cascade_and_schema_contracts_are_documented() -> None:
    contract = _normalized_contract_text()

    assert "reserves no final `PIE-*` diagnostic codes" in contract
    for required in (
        "unsupported aggregate function",
        "aggregate in an invalid context",
        "aggregate mixed with a non-aggregate projection",
        "nested aggregate",
        "wrong aggregate arity",
        "wrong aggregate argument type",
        "unknown aggregate argument field",
        "ambiguous aggregate argument field",
        "deferred aggregate composition",
        "Unknown field or function children should suppress noisy follow-on",
        "should not duplicate scalar expression diagnostics",
        "fail closed when aggregate classification is uncertain",
        "aggregate projection aliases become output schema fields",
        "aggregate-output-shaped, not row-preserving",
        "one logical output row",
        "Downstream relations may bind aggregate aliases after schema propagation",
        "Mixed plain field output fails without GROUP BY",
    ):
        assert required in contract


def test_explicit_non_goals_keep_production_boundaries_closed() -> None:
    contract = _normalized_contract_text()

    for required in (
        "aggregate semantics",
        "grammar or generated parser changes",
        "Semantic IR changes",
        "SQL renderer changes",
        "SQL golden fixture changes",
        "final diagnostic code reservations",
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
