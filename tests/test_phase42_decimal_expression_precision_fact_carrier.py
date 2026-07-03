from __future__ import annotations

import json
from dataclasses import fields
from types import MappingProxyType

import pietto.semantic as semantic_api
from pietto import cli_json
from pietto._metadata.builder import build_semantic_metadata_artifact
from pietto._metadata.model import SemanticMetadataType
from pietto._metadata.serializer import semantic_metadata_artifact_to_json_dict
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import ProjectConfigPath, ProjectDiscoveryResult, ProjectRoot
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    DottedNameExpr,
    Expression,
    NameExpr,
    Script,
)
from pietto.ast_nodes import QueryDef, TableDef
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    TypeRefIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    SemanticResult,
    ValueType,
    ValueTypeKind,
    analyze,
)
from pietto.semantic.model import DecimalPrecisionScale
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

BASE_SOURCE = (
    "type Money = Decimal(12, 2) not null\n"
    "shape Order:\n"
    "    price: Decimal(12, 2) not null\n"
    "    tax: Decimal(10, 4) not null\n"
    "    amount: Int not null\n"
    "    score: Float not null\n"
    "    money: Money not null\n"
    "    status: Text not null\n"
    'source orders: Order is postgres.table("orders")\n'
)

RelationAst = TableDef | QueryDef


def test_private_expression_fact_carrier_records_direct_decimal_field_refs() -> None:
    script, semantic, _ = _compile(
        BASE_SOURCE + "table projected:\n"
        "    from orders\n"
        "    select:\n"
        "        price\n"
        "        qualified_tax = orders.tax\n"
        "query downstream:\n"
        "    from projected\n"
        "    select:\n"
        "        price\n"
        "        qualified_tax\n"
    )
    model = semantic.model

    assert isinstance(model.decimal_expression_precision_scales, MappingProxyType)
    assert not hasattr(semantic_api, "DecimalPrecisionScale")

    projected = _relation_ast(script, "projected")
    projected_price = _select_expression(projected, "price")
    projected_tax = _select_expression(projected, "qualified_tax")
    downstream = _relation_ast(script, "downstream")
    downstream_price = _select_expression(downstream, "price")
    downstream_tax = _select_expression(downstream, "qualified_tax")

    assert isinstance(projected_price, NameExpr)
    assert isinstance(projected_tax, DottedNameExpr)
    assert isinstance(downstream_price, NameExpr)
    assert isinstance(downstream_tax, NameExpr)

    for expression in (projected_price, downstream_price):
        assert model.decimal_expression_precision_scale_for(expression) == (
            DecimalPrecisionScale(12, 2)
        )
    for expression in (projected_tax, downstream_tax):
        assert model.decimal_expression_precision_scale_for(expression) == (
            DecimalPrecisionScale(10, 4)
        )


def test_expression_facts_do_not_cover_computed_let_alias_or_type_alias_refs() -> None:
    script, semantic, _ = _compile(
        BASE_SOURCE + "query computed:\n"
        "    from orders\n"
        "    let:\n"
        "        gross = price\n"
        "    select:\n"
        "        let_value = gross\n"
        "        decimal_total = price + tax\n"
        "        decimal_int = price + amount\n"
        "        alias_money = money\n"
    )
    relation = _relation_ast(script, "computed")
    let_value = _select_expression(relation, "let_value")
    decimal_total = _select_expression(relation, "decimal_total")
    decimal_int = _select_expression(relation, "decimal_int")
    alias_money = _select_expression(relation, "alias_money")

    assert isinstance(let_value, NameExpr)
    assert isinstance(decimal_total, BinaryExpr)
    assert isinstance(decimal_int, BinaryExpr)
    assert isinstance(alias_money, NameExpr)

    for expression in (let_value, decimal_total, decimal_int, alias_money):
        assert semantic.model.decimal_expression_precision_scale_for(expression) is None

    alias_script = _parse(
        BASE_SOURCE + "table alias_scope:\n"
        "    from orders\n"
        "    select:\n"
        "        subtotal = price\n"
        "        alias_leaf = subtotal\n"
    )
    alias_result = analyze(alias_script)
    alias_relation = _relation_ast(alias_script, "alias_scope")
    alias_leaf = _select_expression(alias_relation, "alias_leaf")

    assert _error_codes(alias_result) == []
    assert isinstance(alias_leaf, NameExpr)
    assert alias_result.model.decimal_expression_precision_scale_for(alias_leaf) is None


def test_aggregate_outputs_and_public_surfaces_remain_precision_scale_free() -> None:
    for connector, emitter in (
        ("postgres.table", emit_postgres_sql),
        ("mysql.table", emit_mysql_sql),
    ):
        script, semantic, script_ir = _compile(
            _source(
                connector,
                "table stats:\n"
                "    from orders\n"
                "    select:\n"
                "        total = sum(price)\n"
                "        average = avg(price - tax)\n"
                "        decimal_int_total = sum(price + amount)\n"
                "        known = count(price + tax)\n",
            )
        )
        relation = _relation_ast(script, "stats")
        model = semantic.model

        for name in ("total", "average", "decimal_int_total"):
            _assert_value_type(
                model.relation_row_schemas[relation].fields[name],
                "Decimal",
                EffectiveNullability.NULLABLE,
            )
        _assert_value_type(
            model.relation_row_schemas[relation].fields["known"],
            "Int",
            EffectiveNullability.NON_NULL,
        )

        for name in ("total", "average", "decimal_int_total", "known"):
            aggregate = _select_expression(relation, name)
            assert isinstance(aggregate, CallExpr)
            assert model.decimal_expression_precision_scale_for(aggregate) is None
            if aggregate.arguments:
                argument = aggregate.arguments[0]
                if isinstance(argument, BinaryExpr):
                    assert (
                        model.decimal_expression_precision_scale_for(argument) is None
                    )

        relation_ir = _relation_ir(script_ir, "stats")
        ir_fields = {field.name: field for field in relation_ir.row_schema.fields}
        for name in ("total", "average", "decimal_int_total"):
            assert ir_fields[name].type_ref.canonical_name == "Decimal"
            assert ir_fields[name].type_ref.nullability is NullabilityIR.NULLABLE
        assert ir_fields["known"].type_ref.canonical_name == "Int"
        assert ir_fields["known"].type_ref.nullability is NullabilityIR.NON_NULL

        for projection in relation_ir.projections:
            assert isinstance(projection.expression, AggregateCallIR)
            assert not hasattr(projection.expression.value_type, "precision")
            assert not hasattr(projection.expression.value_type, "scale")

        sql_result = emitter(script_ir)
        assert sql_result.diagnostics == ()
        _assert_public_text_has_no_precision_scale(_sql_text(sql_result))

        public_json_documents = [
            cli_json.check_result_to_json_dict(
                path="phase42_expr_fact.pietto",
                diagnostics=semantic.diagnostics,
            ),
            cli_json.emit_sql_result_to_json_dict(
                path="phase42_expr_fact.pietto",
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
                    path="phase42_expr_fact.pietto",
                    script=script,
                    semantic_result=semantic,
                    ir=script_ir,
                )
            ),
        ]
        for document in public_json_documents:
            _assert_public_text_has_no_precision_scale(json.dumps(document))


def test_operator_boundaries_remain_deferred_without_expression_fusion() -> None:
    for projection, expected_codes in (
        ("value = price * tax", ["PIE-S2105"]),
        ("value = price * amount", ["PIE-S2105"]),
        ("value = price % amount", ["PIE-S2105"]),
        ("value = price + score", ["PIE-S2105"]),
        ("value = score + price", ["PIE-S2105"]),
    ):
        result = analyze(
            _parse(
                BASE_SOURCE + "table projected:\n"
                "    from orders\n"
                "    select:\n"
                f"        {projection}\n"
            )
        )
        assert _error_codes(result) == expected_codes

    script = _parse(
        BASE_SOURCE + "table projected:\n"
        "    from orders\n"
        "    select:\n"
        "        value = price / amount\n"
    )
    result = analyze(script)
    relation = _relation_ast(script, "projected")
    expression = _select_expression(relation, "value")

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN
    assert result.model.decimal_expression_precision_scale_for(expression) is None


def test_public_type_surfaces_still_have_no_precision_scale_fields() -> None:
    for type_surface in (ResolvedType, ValueType, TypeRefIR, SemanticMetadataType):
        assert {"precision", "scale"}.isdisjoint(
            {field.name for field in fields(type_surface)}
        )


def _source(connector: str, relation: str) -> str:
    return BASE_SOURCE.replace("postgres.table", connector) + relation


def _parse(source: str) -> Script:
    result = parse_source(source, path="phase42_expr_fact.pietto")
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


def _relation_ast(script: Script, name: str) -> RelationAst:
    relation = next(
        definition for definition in script.definitions if definition.name == name
    )
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _relation_ir(script_ir: ScriptIR, name: str) -> RelationIR:
    relation = next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )
    return relation


def _select_expression(relation: RelationAst, output_name: str) -> Expression:
    for item in relation.select_items:
        if item.alias == output_name:
            return item.expression
        if item.alias is None and isinstance(item.expression, NameExpr):
            if item.expression.name == output_name:
                return item.expression
    raise AssertionError(f"Missing select output: {output_name}")


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
