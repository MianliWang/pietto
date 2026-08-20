from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from _static_audit_helpers import (
    normalized_text as _normalized,
    read_text as _read,
)

from pietto._metadata.model import SemanticMetadataType
from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    analyze,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/expanded-scalar-operator-matrix-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
SEMANTIC_AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
METADATA_MODEL_PATH = REPO_ROOT / "src/pietto/_metadata/model.py"
METADATA_BUILDER_PATH = REPO_ROOT / "src/pietto/_metadata/builder.py"
METADATA_SERIALIZER_PATH = REPO_ROOT / "src/pietto/_metadata/serializer.py"
METADATA_TEXT_PATH = REPO_ROOT / "src/pietto/_metadata/text.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"


def _phase36_slice9_docs() -> str:
    return f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"


def test_slice9_selects_option_b_without_behavior_change() -> None:
    combined = _phase36_slice9_docs()

    for required in (
        "Phase 36 Slice 9 selects Option B: tests-only hardening",
        "Expanded Scalar / Operator Matrix",
        "without changing compiler behavior",
        "The expanded matrix is documentation and test hardening, not new implementation",
        "Slice 9 makes no behavior change",
        "not stable type-specific compatibility guarantees",
        "Slice 9 keeps the broader 12-slice Phase 36 plan intact",
    ):
        assert required in combined, required


def test_scalar_posture_inventory_is_documented_and_grounded() -> None:
    combined = _phase36_slice9_docs()
    catalog = _read(CATALOG_PATH)
    metadata_builder = _read(METADATA_BUILDER_PATH)

    for type_name in (
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    ):
        assert f'"{type_name}"' in catalog

    for required in (
        "`Bool` | current builtin",
        "`Int` | current builtin numeric",
        "`Float` | current builtin numeric",
        "`Decimal` | current logical exact numeric builtin",
        "`Text` | current builtin",
        "`Date` | current builtin temporal",
        "`Timestamp` | current builtin temporal",
        "`UUID` | `limited_frozen` builtin",
        "Enum | `metadata_only` semantic/IR kind",
        "`DateTime` / `Time` / `Interval` | unsupported/deferred",
        "`Any` | current builtin top/deferred boundary",
        "`Bytes` / `Json` | `deferred_builtin` behavior surfaces",
        "Type aliases | current alias behavior",
        "Currency/Money | deferred",
        "native DB metadata | deferred",
    ):
        assert required in combined, required

    assert '_DEFERRED_BUILTINS = frozenset({"Bytes", "Json"})' in metadata_builder
    assert '_LIMITED_FROZEN_BUILTINS = frozenset({"UUID"})' in metadata_builder
    assert '"Enum"' not in catalog
    assert '"DateTime"' not in catalog
    assert '"Time"' not in catalog
    assert '"Interval"' not in catalog
    assert '"Currency"' not in catalog
    assert '"Money"' not in catalog


def test_arithmetic_and_decimal_boundaries_remain_current() -> None:
    combined = _phase36_slice9_docs()
    expressions = _read(SEMANTIC_EXPRESSIONS_PATH)

    for required in (
        "division `/` remains deferred/unknown",
        "`Decimal + Decimal` and `Decimal - Decimal` remain the current accepted Decimal behavior",
        "Decimal multiplication remains rejected with `PIE-S2105`",
        "Mixed Decimal promotion remains closed/deferred",
        "Phase 41 Decimal precision-scale validation and private `DecimalPrecisionScale` facts do not change this arithmetic matrix",
        "No new arithmetic behavior is authorized",
    ):
        assert required in combined, required

    for required in (
        'if expression.operator == "/":',
        "return _UNKNOWN_VALUE_TYPE",
        'if expression.operator == "%":',
        'operator in {"+", "-", "*"}',
        'operator in {"+", "-"}',
        '_is_builtin(left_type, "Decimal")',
        '_is_builtin(right_type, "Decimal")',
        'return _is_builtin(value_type, "Int") or _is_builtin(value_type, "Float")',
    ):
        assert required in expressions, required

    decimal_multiply = analyze(_parse(_scalar_source("value = price * discount")))
    decimal_divide = analyze(_parse(_scalar_source("value = price / discount")))
    mixed_decimal = analyze(_parse(_scalar_source("value = price + amount")))
    decimal_add = analyze(_parse(_scalar_source("value = price + discount")))

    assert _error_codes(decimal_multiply) == ["PIE-S2105"]
    assert _output_type_kind(decimal_multiply, "value") is TypeKind.UNKNOWN

    assert _error_codes(decimal_divide) == []
    assert _output_type_kind(decimal_divide, "value") is TypeKind.UNKNOWN

    assert _error_codes(mixed_decimal) == []
    _assert_output_type(mixed_decimal, "value", "Decimal", EffectiveNullability.UNKNOWN)

    assert _error_codes(decimal_add) == []
    _assert_output_type(decimal_add, "value", "Decimal", EffectiveNullability.UNKNOWN)


def test_comparison_bool_and_risky_shared_paths_are_documented() -> None:
    combined = _phase36_slice9_docs()
    expressions = _read(SEMANTIC_EXPRESSIONS_PATH)

    for required in (
        "Bool predicate and `where` behavior remain current",
        "Generic known-child comparison behavior remains current",
        "not a pair-specific compatibility guarantee",
        "UUID / Enum / Any / Bytes / Json comparison and ordering are risky generic shared paths",
        "No new comparison, ordering, or Bool predicate behavior is authorized",
        "comparison/order/group/satisfying for `UUID`",
        "comparison/order/group/satisfying for Enum",
        "comparison/order/group/satisfying for `Any` / `Bytes` / `Json`",
    ):
        assert required in combined, required

    for required in (
        'expression.operator in {"and", "or"}',
        '_is_builtin(left_type, "Bool")',
        '_is_builtin(right_type, "Bool")',
        "isinstance(expression, ComparisonExpr)",
        "isinstance(expression, BetweenExpr)",
        '_builtin_value_type("Bool", EffectiveNullability.UNKNOWN)',
    ):
        assert required in expressions, required

    uuid_compare = analyze(
        _parse(_typed_projection_source("UUID", "same = value == other"))
    )
    bytes_order = analyze(_parse(_order_by_source("Bytes")))
    json_group = analyze(_parse(_group_by_source("Json")))

    assert _error_codes(uuid_compare) == []
    _assert_output_type(uuid_compare, "same", "Bool", EffectiveNullability.UNKNOWN)
    assert _error_codes(bytes_order) == []
    assert _error_codes(json_group) == []


def test_aggregate_matrix_boundaries_remain_current() -> None:
    combined = _phase36_slice9_docs()
    aggregates = _read(SEMANTIC_AGGREGATES_PATH)

    for required in (
        "`count()` remains current `Int NON_NULL` behavior",
        "`count(Enum field)` remains semantic `PIE-S2314`",
        "`count(Any field)` remains semantic `PIE-S2314`",
        "`Bytes` / `Json` direct `count(field)` remains current accepted behavior",
        "`count_distinct` supported direct-field rows remain current for `Bool`, `Int`, `Float`, `Decimal`, `Text`, `Date`, `Timestamp`, and `UUID`",
        "`min` / `max` supported direct-field rows remain current for `Int`, `Float`, `Decimal`, `Date`, and `Timestamp`",
        "`sum` / `avg` supported rows remain current for `Int`, `Float`, and `Decimal`",
        "Unsupported aggregate arguments remain semantic `PIE-S2314`",
        "No new aggregate behavior is authorized",
    ):
        assert required in combined, required

    for required in (
        "COUNT_VALUE_TYPE",
        "TypeKind.ENUM",
        '_is_builtin(value_type, "Any")',
        '"Bool"',
        '"UUID"',
        '"Date"',
        '"Timestamp"',
        '"Decimal"',
        "PIE-S2314",
    ):
        assert required in aggregates, required

    for projection in (
        "total = count()",
        "value = count(raw)",
        "value = count(payload)",
        "value = count(uuid_value)",
    ):
        result = analyze(_parse(_aggregate_source(projection)))
        assert _error_codes(result) == []

    for projection in (
        "value = count(anything)",
        "value = count(status)",
        "value = count_distinct(anything)",
        "value = count_distinct(raw)",
        "value = count_distinct(payload)",
        "value = count_distinct(status)",
        "value = min(raw)",
        "value = max(payload)",
        "value = sum(payload)",
        "value = avg(raw)",
    ):
        result = analyze(_parse(_aggregate_source(projection)))
        assert _error_codes(result) == ["PIE-S2314"], projection
        assert _output_type_kind(result, "value") is TypeKind.UNKNOWN


def test_unsupported_temporal_and_deferred_surfaces_remain_closed() -> None:
    combined = _phase36_slice9_docs()

    for required in (
        "Decimal precision/scale carrier",
        "DateTime / Time / Interval behavior",
        "UUID stable/native behavior",
        "Enum SQL scalar semantics",
        "Any dynamic typing",
        "Bytes binary literals, encoding, functions, operators, native storage, or native metadata",
        "Json path operators, structural typing, object/array schema validation",
        "domain refinement",
        "Currency/Money",
        "native DB metadata",
        "DDL/storage/runtime execution",
        "schema introspection/db pull",
    ):
        assert required in combined, required

    for type_name in ("DateTime", "Time", "Interval"):
        result = analyze(
            _parse(
                "shape Event:\n"
                f"    value: {type_name} not null\n"
                'source events: Event is postgres.table("events")\n'
                "table projected:\n"
                "    from events\n"
                "    select:\n"
                "        value\n"
            )
        )
        assert _error_codes(result) == ["PIE-S2002"]


def test_no_matrix_specific_public_output_schema_was_added() -> None:
    combined = _phase36_slice9_docs()

    assert "CLI JSON v1 unchanged" in combined
    assert "Project JSON v2 unchanged" in combined
    assert "Semantic Metadata Artifact v1 schema/output unchanged" in combined

    assert {field.name for field in fields(SemanticMetadataType)} == {
        "status",
        "name",
        "kind",
        "canonical_name",
        "canonical_kind",
        "nullability",
        "support_posture",
    }

    for source in (
        _read(METADATA_MODEL_PATH),
        _read(METADATA_SERIALIZER_PATH),
        _read(METADATA_TEXT_PATH),
        _read(CLI_JSON_PATH),
    ):
        lowered = source.lower()
        for forbidden in (
            "operator_matrix",
            "comparison_matrix",
            "aggregate_matrix",
            "scalar_matrix",
            "ordering_policy",
            "group_key_policy",
            "domain_constraints",
            "precision_scale",
            "native_type_metadata",
            "uuid_native",
            "enum_sql",
            "json_structure",
            "bytes_encoding",
        ):
            assert forbidden not in lowered, forbidden


def _scalar_source(projection: str) -> str:
    return (
        "shape Order:\n"
        "    amount: Int not null\n"
        "    price: Decimal not null\n"
        "    discount: Decimal nullable\n"
        'source orders: Order is postgres.table("orders")\n'
        "table projected:\n"
        "    from orders\n"
        "    select:\n"
        f"        {projection}\n"
    )


def _typed_projection_source(type_name: str, projection: str) -> str:
    prefix = ""
    if type_name == "Status":
        prefix = "enum Status:\n    active\n    paused\n"
    return (
        prefix + "shape Flexible:\n"
        f"    value: {type_name} not null\n"
        f"    other: {type_name} nullable\n"
        'source events: Flexible is postgres.table("events")\n'
        "table projected:\n"
        "    from events\n"
        "    select:\n"
        f"        {projection}\n"
    )


def _order_by_source(type_name: str) -> str:
    return (
        "shape Flexible:\n"
        f"    value: {type_name} not null\n"
        'source events: Flexible is postgres.table("events")\n'
        "table ordered:\n"
        "    from events\n"
        "    select:\n"
        "        value\n"
        "    order by:\n"
        "        value\n"
    )


def _group_by_source(type_name: str) -> str:
    return (
        "shape Flexible:\n"
        f"    value: {type_name} not null\n"
        'source events: Flexible is postgres.table("events")\n'
        "table grouped:\n"
        "    from events\n"
        "    group by:\n"
        "        value\n"
        "    select:\n"
        "        value\n"
        "        rows = count()\n"
    )


def _aggregate_source(projection: str) -> str:
    return (
        "enum Status:\n"
        "    active\n"
        "    paused\n"
        "shape Flexible:\n"
        "    anything: Any nullable\n"
        "    raw: Bytes not null\n"
        "    payload: Json not null\n"
        "    uuid_value: UUID not null\n"
        "    status: Status not null\n"
        'source events: Flexible is postgres.table("events")\n'
        "table aggregated:\n"
        "    from events\n"
        "    select:\n"
        f"        {projection}\n"
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(result: SemanticResult) -> TableDef | QueryDef:
    relation = next(iter(result.model.relation_row_schemas))
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _output_type_kind(result: SemanticResult, name: str) -> TypeKind:
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields[name]
    return field.resolved_type.kind


def _assert_output_type(
    result: SemanticResult,
    name: str,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    relation = _relation(result)
    field = result.model.relation_row_schemas[relation].fields[name]

    assert field.resolved_type.kind is TypeKind.BUILTIN
    assert field.resolved_type.name == expected_type
    assert field.nullability is expected_nullability


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
