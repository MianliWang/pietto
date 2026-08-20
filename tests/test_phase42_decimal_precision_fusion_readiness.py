from __future__ import annotations

import json
from dataclasses import fields
from types import MappingProxyType

import pytest

from pietto import cli_json
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.model import SemanticMetadataType
from pietto._metadata.serializer import semantic_metadata_artifact_to_json_dict
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import ProjectConfigPath, ProjectDiscoveryResult, ProjectRoot
from pietto.ast_nodes import BinaryExpr, FieldDef, NameExpr, Script, ShapeDef, TableDef
from pietto.errors import Severity
from pietto.ir import AggregateCallIR, NullabilityIR, RelationIR, ScriptIR, TypeRefIR
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    SemanticResult,
    ValueType,
    ValueTypeKind,
    analyze,
)
from pietto.semantic.model import DecimalPrecisionScale, SemanticModel
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


BASE_SHAPE = (
    "shape Order:\n"
    "    price: Decimal(12, 2) not null\n"
    "    tax: Decimal(10, 4) not null\n"
    "    amount: Int not null\n"
    "    score: Float not null\n"
)


def test_decimal_precision_carriers_remain_private_and_non_public() -> None:
    script, semantic, _ = _compile(
        _source(
            "postgres.table",
            "table projected:\n    from orders\n    select:\n        price\n",
        )
    )
    fields_by_name = _shape_fields(script, "Order")
    relation = _relation_ast(script)
    price_expression = relation.select_items[0].expression
    assert isinstance(price_expression, NameExpr)

    assert DecimalPrecisionScale(12, 2) == semantic.model.decimal_precision_scale_for(
        fields_by_name["price"].type_expr
    )
    assert DecimalPrecisionScale(10, 4) == semantic.model.decimal_precision_scale_for(
        fields_by_name["tax"].type_expr
    )
    assert all(
        hasattr(type_expr, "name")
        for type_expr in semantic.model.decimal_precision_scales
    )
    assert isinstance(
        semantic.model.decimal_expression_precision_scales,
        MappingProxyType,
    )
    assert semantic.model.decimal_expression_precision_scale_for(
        price_expression
    ) == DecimalPrecisionScale(12, 2)

    assert "decimal_precision_scales" in {field.name for field in fields(SemanticModel)}
    assert "decimal_precision_scale_for" in dir(SemanticModel)
    assert "decimal_expression_precision_scales" in {
        field.name for field in fields(SemanticModel)
    }
    assert "decimal_expression_precision_scale_for" in dir(SemanticModel)


def test_direct_field_type_expr_facts_are_recoverable_but_computed_outputs_are_not() -> (
    None
):
    script, semantic, _ = _compile(
        _source(
            "postgres.table",
            "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        price\n"
            "        decimal_total = price + tax\n"
            "        decimal_int = price + amount\n",
        )
    )
    source_schema = next(iter(semantic.model.source_row_schemas.values()))
    source_price = source_schema.fields["price"]
    assert source_price.definition is not None
    assert semantic.model.decimal_precision_scale_for(
        source_price.definition.type_expr
    ) == DecimalPrecisionScale(12, 2)

    relation = _relation_ast(script)
    relation_fields = semantic.model.relation_row_schemas[relation].fields
    projected_price = relation_fields["price"]
    assert projected_price.definition is not None
    assert semantic.model.decimal_precision_scale_for(
        projected_price.definition.type_expr
    ) == DecimalPrecisionScale(12, 2)

    for output_name in ("decimal_total", "decimal_int"):
        computed = relation_fields[output_name]
        assert computed.definition is None
        assert computed.resolved_type.name == "Decimal"
        assert not hasattr(computed, "precision")
        assert not hasattr(computed, "scale")


def test_decimal_int_and_decimal_decimal_expressions_stay_logical_without_precision_fact() -> (
    None
):
    script, semantic, _ = _compile(
        _source(
            "postgres.table",
            "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        decimal_total = price + tax\n"
            "        decimal_int = price + amount\n"
            "        int_decimal = amount + price\n"
            "        decimal_minus_int = price - amount\n",
        )
    )
    relation = _relation_ast(script)

    for alias in (
        "decimal_total",
        "decimal_int",
        "int_decimal",
        "decimal_minus_int",
    ):
        expression = _select_expression(relation, alias)
        value_type = semantic.model.expression_value_types[expression]
        _assert_value_type(value_type, "Decimal", EffectiveNullability.UNKNOWN)
        assert not hasattr(value_type, "precision")
        assert not hasattr(value_type, "scale")

    for alias in (
        "decimal_total",
        "decimal_int",
        "int_decimal",
        "decimal_minus_int",
    ):
        expression = _select_expression(relation, alias)
        assert semantic.model.decimal_expression_precision_scale_for(expression) is None


@pytest.mark.parametrize(
    ("projection", "expected_codes"),
    [
        ("value = price * tax", ["PIE-S2105"]),
        ("value = price * amount", ["PIE-S2105"]),
        ("value = price % amount", ["PIE-S2105"]),
        ("value = price + score", ["PIE-S2105"]),
        ("value = score + price", ["PIE-S2105"]),
    ],
)
def test_deferred_decimal_operator_boundaries_stay_fail_closed(
    projection: str,
    expected_codes: list[str],
) -> None:
    semantic = analyze(
        _parse(
            _source(
                "postgres.table",
                "table projected:\n"
                "    from orders\n"
                "    select:\n"
                f"        {projection}\n",
            )
        )
    )

    assert _error_codes(semantic) == expected_codes


def test_decimal_division_remains_unknown_without_precision_fact() -> None:
    script = _parse(
        _source(
            "postgres.table",
            "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = price / amount\n",
        )
    )
    semantic = analyze(script)
    relation = _relation_ast(script)
    expression = _select_expression(relation, "value")

    assert semantic.diagnostics == ()
    value_type = semantic.model.expression_value_types[expression]
    assert value_type.kind is ValueTypeKind.UNKNOWN
    assert not hasattr(value_type, "precision")
    assert not hasattr(value_type, "scale")


def test_decimal_aggregate_results_and_public_outputs_remain_precision_scale_free() -> (
    None
):
    for connector, emitter in (
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ):
        script, semantic, script_ir = _compile(
            _source(
                connector,
                "table decimal_stats:\n"
                "    from orders\n"
                "    select:\n"
                "        total = sum(price)\n"
                "        average = avg(price - tax)\n"
                "        decimal_int_total = sum(price + amount)\n"
                "        known_decimal_expr = count(price + tax)\n",
            )
        )
        relation = _relation_ast(script)
        semantic_fields = semantic.model.relation_row_schemas[relation].fields

        for alias in ("total", "average", "decimal_int_total"):
            _assert_value_type(
                semantic_fields[alias],
                "Decimal",
                EffectiveNullability.NULLABLE,
            )
        _assert_value_type(
            semantic_fields["known_decimal_expr"],
            "Int",
            EffectiveNullability.NON_NULL,
        )

        relation_ir = _relation_ir(script_ir)
        ir_fields = {field.name: field for field in relation_ir.row_schema.fields}
        for alias in ("total", "average", "decimal_int_total"):
            assert ir_fields[alias].type_ref.canonical_name == "Decimal"
            assert ir_fields[alias].type_ref.nullability is NullabilityIR.NULLABLE
        assert ir_fields["known_decimal_expr"].type_ref.canonical_name == "Int"
        assert ir_fields["known_decimal_expr"].type_ref.nullability is (
            NullabilityIR.NON_NULL
        )

        for projection in relation_ir.projections:
            if projection.name == "price":
                continue
            assert isinstance(projection.expression, AggregateCallIR)
            assert not hasattr(projection.expression.value_type, "precision")
            assert not hasattr(projection.expression.value_type, "scale")

        sql_result = emitter(script_ir)
        assert sql_result.diagnostics == ()
        _assert_public_text_has_no_precision_scale(_sql_text(sql_result))

        public_json_documents = [
            cli_json.check_result_to_json_dict(
                path="phase42_decimal_fusion.pietto",
                diagnostics=semantic.diagnostics,
            ),
            cli_json.emit_sql_result_to_json_dict(
                path="phase42_decimal_fusion.pietto",
                dialect="postgresql" if connector == "postgres.table" else "mysql",
                diagnostics=sql_result.diagnostics,
                artifacts=sql_result.artifacts,
            ),
            project_check_result_to_json_dict(
                ProjectDiscoveryResult(
                    root=ProjectRoot(path="."),
                    config_path=ProjectConfigPath(path="pietto.toml"),
                    inputs=(),
                    errors=(),
                )
            ),
            semantic_metadata_artifact_to_json_dict(
                build_semantic_metadata_artifact(
                    path="phase42_decimal_fusion.pietto",
                    script=script,
                    semantic_result=semantic,
                    ir=script_ir,
                )
            ),
        ]
        for document in public_json_documents:
            _assert_public_text_has_no_precision_scale(
                json.dumps(document, ensure_ascii=True)
            )


def test_public_type_surfaces_have_no_precision_scale_fields() -> None:
    for type_surface in (ResolvedType, ValueType, TypeRefIR, SemanticMetadataType):
        assert {"precision", "scale"}.isdisjoint(
            {field.name for field in fields(type_surface)}
        )


def _source(connector: str, relation: str) -> str:
    return BASE_SHAPE + f'source orders: Order is {connector}("orders")\n' + relation


def _parse(source: str) -> Script:
    result = parse_source(source, path="phase42_decimal_fusion.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    script = _parse(source)
    semantic = analyze(script)
    assert _error_codes(semantic) == []
    ir_result = build_ir(script, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return script, semantic, ir_result.ir


def _relation_ast(script: Script) -> TableDef:
    relation = script.definitions[-1]
    assert isinstance(relation, TableDef)
    return relation


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _shape_fields(script: Script, name: str) -> dict[str, FieldDef]:
    shape = next(
        definition
        for definition in script.definitions
        if isinstance(definition, ShapeDef) and definition.name == name
    )
    return {field.name: field for field in shape.fields}


def _select_expression(relation: TableDef, alias: str) -> BinaryExpr:
    for item in relation.select_items:
        if item.alias == alias:
            expression = item.expression
            assert isinstance(expression, BinaryExpr)
            return expression
    raise AssertionError(f"Missing select alias: {alias}")


def _assert_value_type(
    value_type: object,
    expected_name: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert getattr(value_type, "resolved_type").name == expected_name
    assert getattr(value_type, "nullability") is expected_nullability


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _sql_text(result: SqlResult) -> str:
    return "\n".join(artifact.sql for artifact in result.artifacts)


def _assert_public_text_has_no_precision_scale(text: str) -> None:
    for forbidden in ("DECIMAL(", "NUMERIC(", "precision", "scale"):
        assert forbidden not in text
