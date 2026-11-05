from __future__ import annotations

from typing import cast

from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.serializer import semantic_metadata_artifact_to_json_dict
from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import AggregateCallIR, EnumIR, RelationIR, ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)

ENUM_SOURCE_HEADER = (
    "enum Status:\n"
    "    active\n"
    "    paused\n"
    "shape EnumOrder:\n"
    "    status: Status\n"
    "    optional_status: Status | None\n"
    "    amount: Int\n"
)


def test_count_enum_field_fails_semantic_validation_with_pie_s2314() -> None:
    for connector in ("postgres.table", "mysql.table"):
        script = _parse(_source(connector, "known_statuses = count(status)"))
        semantic_result = analyze(script)
        relation = _relation(semantic_result)
        field = semantic_result.model.relation_row_schemas[relation].fields[
            "known_statuses"
        ]

        assert _error_codes(semantic_result) == ["PIE-S2314"]
        assert field.resolved_type.kind is TypeKind.UNKNOWN
        assert field.nullability is EffectiveNullability.UNKNOWN


def test_count_enum_field_no_longer_reaches_backend_pie_b1000_path() -> None:
    for connector in ("postgres.table", "mysql.table"):
        script = _parse(_source(connector, "known_statuses = count(status)"))
        semantic_result = analyze(script)
        ir_result = build_ir(script, semantic_result.model)

        assert _error_codes(semantic_result) == ["PIE-S2314"]
        assert ir_result.ir is not None
        projection = _relation_ir(ir_result.ir).projections[0]
        assert not isinstance(projection.expression, AggregateCallIR)


def test_other_enum_aggregate_boundaries_remain_rejected() -> None:
    for projection in (
        "value = count_distinct(status)",
        "value = min(status)",
        "value = max(status)",
        "value = sum(status)",
        "value = avg(status)",
    ):
        result = analyze(_parse(_source("postgres.table", projection)))
        relation = _relation(result)
        field = result.model.relation_row_schemas[relation].fields["value"]

        assert _error_codes(result) == ["PIE-S2314"]
        assert field.resolved_type.kind is TypeKind.UNKNOWN
        assert field.nullability is EffectiveNullability.UNKNOWN


def test_enum_metadata_readiness_remains_intact() -> None:
    script = _parse(_source("postgres.table", "status\n        optional_status"))
    semantic_result = analyze(script)
    relation = _relation(semantic_result)
    schema = semantic_result.model.relation_row_schemas[relation]

    assert _error_codes(semantic_result) == []
    assert schema.fields["status"].resolved_type.kind is TypeKind.ENUM
    assert schema.fields["status"].resolved_type.name == "Status"
    assert schema.fields["optional_status"].resolved_type.kind is TypeKind.ENUM
    assert schema.fields["optional_status"].nullability is (
        EffectiveNullability.NULLABLE
    )

    ir_result = build_ir(script, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    assert any(
        isinstance(definition, EnumIR) for definition in ir_result.ir.definitions
    )

    artifact = build_semantic_metadata_artifact(
        path="phase36-slice5-enum.pietto",
        script=script,
        semantic_result=semantic_result,
        ir=ir_result.ir,
    )
    enum_type = next(
        type_ref
        for type_ref in artifact.metadata.types
        if type_ref.kind == "enum" and type_ref.name == "Status"
    )
    assert enum_type.canonical_kind == "enum"
    assert enum_type.support_posture == "metadata_only"


def test_enum_literal_cast_native_runtime_surfaces_remain_absent() -> None:
    for projection, expected_code in (
        ("value = active", None),
        ("value = Status.active", "PIE-S2102"),
        ('value = Status("active")', "PIE-S2103"),
        ("value = cast(status)", "PIE-S2103"),
    ):
        result = analyze(_parse(_source("postgres.table", projection)))
        relation = _relation(result)
        expression = _select_expression(relation, "value")

        if expected_code is not None:
            assert expected_code in _error_codes(result)
        assert result.model.expression_value_types[expression].kind is (
            ValueTypeKind.UNKNOWN
        )


def test_json_metadata_schema_expansion_is_not_authorized() -> None:
    script = _parse(_source("postgres.table", "status"))
    semantic_result = analyze(script)
    ir_result = build_ir(script, semantic_result.model)
    assert ir_result.ir is not None
    document = semantic_metadata_artifact_to_json_dict(
        build_semantic_metadata_artifact(
            path="enum.pietto",
            script=script,
            semantic_result=semantic_result,
            ir=ir_result.ir,
        )
    )
    metadata = cast(dict[str, list[dict[str, object]]], document["metadata"])
    enum_type = next(
        type_ref for type_ref in metadata["types"] if type_ref["name"] == "Status"
    )

    assert set(enum_type) == {
        "status",
        "name",
        "kind",
        "canonical_name",
        "canonical_kind",
        "nullability",
        "support_posture",
    }


def _source(connector: str, projections: str) -> str:
    return (
        ENUM_SOURCE_HEADER
        + f'source orders: EnumOrder = {connector}("orders")\n'
        + "table status_counts:\n"
        + "    from orders\n"
        + "    select:\n"
        + f"        {projections}\n"
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


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _select_expression(relation: TableDef | QueryDef, alias: str) -> Expression:
    for item in relation.select_items:
        if item.alias == alias:
            return item.expression
    raise AssertionError(f"Missing select item: {alias}")


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
