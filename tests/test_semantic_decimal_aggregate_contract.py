from __future__ import annotations

from pathlib import Path

from pietto.semantic import EffectiveNullability, ResolvedType, TypeKind, ValueType
from pietto.semantic.aggregates import semantic_aggregate_result_value_type

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-24-aggregate-function-expansion-ii.md"


def _read() -> str:
    return PLAN_PATH.read_text(encoding="utf-8")


def _normalized() -> str:
    return " ".join(_read().split())


DECIMAL_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Decimal", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NON_NULL,
)


def test_slice5_status_is_contract_only_without_behavior_changes() -> None:
    plan = _normalized()

    for required in (
        "Phase 24 Slice 5 is complete as Decimal aggregate semantic/type contract work only",
        "without enabling production Decimal aggregate behavior",
        "Slice 5 changes no semantic behavior, Semantic IR behavior, IR model, SQL renderer behavior, CLI behavior, JSON schema, fixture, golden, `scripts/check_goldens.py` inventory, grammar, generated ANTLR, dependency, lockfile, package metadata, CI, backend registry behavior, runtime/database behavior",
        "aggregate expression argument implementation, generic DISTINCT syntax, `count(distinct field)`, aggregate modifier behavior",
    ):
        assert required in plan


def test_decimal_aggregate_result_contracts_are_locked() -> None:
    plan = _normalized()

    for required in (
        "`sum(Decimal) -> Decimal nullable`",
        "`avg(Decimal) -> Decimal nullable`",
        "`min(Decimal) -> Decimal nullable`",
        "`max(Decimal) -> Decimal nullable`",
        "PostgreSQL and MySQL should render `sum(Decimal)` with `SUM(field)`",
        "PostgreSQL and MySQL should render `avg(Decimal)` with `AVG(field)`",
        "PostgreSQL and MySQL should render `min(Decimal)` with `MIN(field)`",
        "PostgreSQL and MySQL should render `max(Decimal)` with `MAX(field)`",
    ):
        assert required in plan


def test_decimal_precision_scale_and_portability_non_promises_are_locked() -> None:
    plan = _normalized()

    for required in (
        "`avg(Decimal)` remains logical Pietto `Decimal`, not `Float`",
        "there is no Decimal precision/scale promise in Phase 24",
        "there are no Decimal type-argument semantics in Phase 24",
        "there is no silent collapse from Decimal to Float",
        "there is no schema introspection for Decimal precision or scale",
        "there is no runtime/database execution for Decimal aggregate validation",
        "there is no dialect-specific precision guarantee",
        "no SQL casts are introduced by the Phase 24 Decimal aggregate contract",
    ):
        assert required in plan


def test_slice5_keeps_unsupported_decimal_cases_deferred() -> None:
    plan = _normalized()

    for required in (
        "Unsupported Decimal aggregate cases remain unsupported until a later approved implementation slice",
        "Decimal aggregate expression arguments such as `sum(amount + tax)`",
        "nested aggregates",
        "aggregate composition",
        "unnamed aggregates",
        "invalid aggregate contexts",
        "unresolved fields",
        "`Bytes`, `Json`, `Any`, `Bool`, `Text`, and `UUID` for `sum` and `avg`",
        "`Bytes`, `Json`, `Any`, `Bool`, `Text`, and `UUID` for `min` and `max`",
        "`Text`, `Bool`, and `UUID` extrema remain outside Phase 24",
    ):
        assert required in plan


def test_slice5_does_not_authorize_other_aggregate_expansions() -> None:
    plan = _normalized()

    for required in (
        "Aggregate expression arguments remain readiness/contract-only in Phase 24",
        "does not implement aggregate expression arguments",
        "does not broadly retire `PIE-S2315`",
        "generic `DISTINCT` keyword syntax",
        "`count(distinct field)`",
        "aggregate modifier system",
        "filtered aggregates",
    ):
        assert required in plan


def test_slice6_production_helpers_authorize_decimal_aggregates() -> None:
    for function_name in ("sum", "avg", "min", "max"):
        value_type = semantic_aggregate_result_value_type(
            function_name,
            DECIMAL_VALUE_TYPE,
        )

        assert value_type is not None
        assert value_type.resolved_type.name == "Decimal"
        assert value_type.resolved_type.kind is TypeKind.BUILTIN
        assert value_type.nullability is EffectiveNullability.NULLABLE


def test_count_distinct_decimal_argument_remains_authorized() -> None:
    value_type = semantic_aggregate_result_value_type(
        "count_distinct",
        DECIMAL_VALUE_TYPE,
    )

    assert value_type is not None
    assert value_type.resolved_type.name == "Int"
    assert value_type.resolved_type.kind is TypeKind.BUILTIN
    assert value_type.nullability is EffectiveNullability.NON_NULL
