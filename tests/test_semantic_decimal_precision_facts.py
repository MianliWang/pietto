from __future__ import annotations

import json
from dataclasses import fields
from types import MappingProxyType

import pytest

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
    ConstraintDef,
    DeriveDef,
    DottedNameExpr,
    Expression,
    FieldDef,
    NameExpr,
    QueryDef,
    Script,
    ShapeDef,
    TableDef,
    TypeDef,
)
from pietto.errors import Severity
from pietto.ir import (
    AggregateCallIR,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    SourceIR,
    TypeRefIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    SemanticResult,
    TypeKind,
    ValueType,
    ValueTypeKind,
    analyze,
)
from pietto.semantic.model import DecimalPrecisionScale, SemanticModel
from pietto.sql import SqlResult, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


def test_decimal_precision_scale_facts_are_stored_for_supported_type_sites() -> None:
    script = _parse_script(
        "type Money = Decimal(12, 2)\n"
        "constraint valid(amount: Decimal(38, 38)) -> Bool:\n"
        "    return True\n"
        "derive keep(amount: Decimal(1, 0) | None) -> Decimal(10, 2) | None:\n"
        "    return amount\n"
        "shape Product:\n"
        "    price: Decimal(12, 2)\n"
        "    plain: Decimal\n"
        "    empty: Decimal()\n"
    )

    result = analyze(script)

    assert result.diagnostics == ()
    assert isinstance(result.model.decimal_precision_scales, MappingProxyType)
    money = _type_def(script, "Money")
    constraint = _constraint(script, "valid")
    derive = _derive(script, "keep")
    fields = _shape_fields(script, "Product")

    expected = {
        money.base: DecimalPrecisionScale(12, 2),
        constraint.parameters[0].type: DecimalPrecisionScale(38, 38),
        derive.parameters[0].type: DecimalPrecisionScale(1, 0),
        derive.return_type: DecimalPrecisionScale(10, 2),
        fields["price"].type_expr: DecimalPrecisionScale(12, 2),
    }
    for type_expr, fact in expected.items():
        assert result.model.decimal_precision_scale_for(type_expr) == fact
        resolved_type = result.model.type_resolutions[type_expr]
        assert resolved_type.name == "Decimal"
        assert resolved_type.kind is TypeKind.BUILTIN
        assert not hasattr(resolved_type, "precision")
        assert not hasattr(resolved_type, "scale")

    assert result.model.decimal_precision_scale_for(fields["plain"].type_expr) is None
    assert result.model.decimal_precision_scale_for(fields["empty"].type_expr) is None


def test_decimal_precision_scale_facts_propagate_through_safe_alias_chains() -> None:
    script = _parse_script(
        "type Money = Decimal(12, 2)\n"
        "type Price = Money\n"
        "type OptionalPrice = Price\n"
        "type Label = Text(max = 255)\n"
        "shape Product:\n"
        "    direct: Decimal(12, 2) | None\n"
        "    money: Money\n"
        "    price: Price\n"
        "    optional: OptionalPrice | None\n"
        "    label: Label\n"
    )

    result = analyze(script)

    assert result.diagnostics == ()
    money = _type_def(script, "Money")
    price = _type_def(script, "Price")
    optional_price = _type_def(script, "OptionalPrice")
    label = _type_def(script, "Label")
    fields = _shape_fields(script, "Product")
    fact = DecimalPrecisionScale(12, 2)

    for type_expr in (
        money.base,
        price.base,
        optional_price.base,
        fields["direct"].type_expr,
        fields["money"].type_expr,
        fields["price"].type_expr,
        fields["optional"].type_expr,
    ):
        assert result.model.decimal_precision_scale_for(type_expr) == fact

    assert result.model.decimal_precision_scale_for(label.base) is None
    assert result.model.decimal_precision_scale_for(fields["label"].type_expr) is None


def test_decimal_precision_scale_facts_skip_invalid_plain_empty_and_non_decimal() -> (
    None
):
    script = _parse_script(
        "type Label = Text(max = 32)\n"
        "shape Product:\n"
        "    invalid: Decimal(0, 0)\n"
        "    plain: Decimal\n"
        "    empty: Decimal()\n"
        "    label: Label\n"
    )

    result = analyze(script)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2004"]
    label = _type_def(script, "Label")
    fields = _shape_fields(script, "Product")
    for type_expr in (
        fields["invalid"].type_expr,
        fields["plain"].type_expr,
        fields["empty"].type_expr,
        fields["label"].type_expr,
        label.base,
    ):
        assert result.model.decimal_precision_scale_for(type_expr) is None


def test_unknown_non_decimal_and_cyclic_aliases_do_not_create_decimal_facts() -> None:
    script = _parse_script(
        "type Label = Text(max = 32)\n"
        "type Loop = Loop\n"
        "shape Product:\n"
        "    label: Label\n"
        "    missing: Missing\n"
        "    looped: Loop\n"
    )

    result = analyze(script)

    assert {diagnostic.code for diagnostic in result.diagnostics} == {
        "PIE-S2002",
        "PIE-S2003",
    }
    label = _type_def(script, "Label")
    loop = _type_def(script, "Loop")
    fields = _shape_fields(script, "Product")
    for type_expr in (
        label.base,
        loop.base,
        fields["label"].type_expr,
        fields["missing"].type_expr,
        fields["looped"].type_expr,
    ):
        assert result.model.decimal_precision_scale_for(type_expr) is None


def test_decimal_precision_scale_carrier_does_not_expand_public_output_surfaces() -> (
    None
):
    source = (
        "shape Product:\n"
        "    price: Decimal(12, 2)\n"
        'source products: Product = postgres.table("products")\n'
        "table projected:\n"
        "    from products\n"
        "    select:\n"
        "        price\n"
    )
    script = _parse_script(source)
    field_type = _shape_fields(script, "Product")["price"].type_expr
    semantic_result = analyze(script)

    assert semantic_result.diagnostics == ()
    assert semantic_result.model.decimal_precision_scale_for(field_type) == (
        DecimalPrecisionScale(12, 2)
    )

    script_ir = build_ir(script, semantic_result.model)

    assert script_ir.diagnostics == ()
    assert script_ir.ir is not None
    source_ir = next(
        definition
        for definition in script_ir.ir.definitions
        if isinstance(definition, SourceIR)
    )
    ir_field = source_ir.row_schema.fields[0]
    assert ir_field.type_ref.canonical_name == "Decimal"
    assert not hasattr(ir_field.type_ref, "precision")
    assert not hasattr(ir_field.type_ref, "scale")
    sql_result = emit_postgres_sql(script_ir.ir)
    combined_sql = "\n".join(artifact.sql for artifact in sql_result.artifacts)

    assert sql_result.diagnostics == ()
    assert "DECIMAL(" not in combined_sql
    assert "NUMERIC(" not in combined_sql
    assert "precision" not in combined_sql
    assert "scale" not in combined_sql


def test_decimal_precision_scale_carrier_is_not_exported_from_semantic_api() -> None:
    assert not hasattr(semantic_api, "DecimalPrecisionScale")


def _parse_script(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _type_def(script: Script, name: str) -> TypeDef:
    return next(
        definition
        for definition in script.definitions
        if isinstance(definition, TypeDef) and definition.name == name
    )


def _constraint(script: Script, name: str) -> ConstraintDef:
    return next(
        definition
        for definition in script.definitions
        if isinstance(definition, ConstraintDef) and definition.name == name
    )


def _derive(script: Script, name: str) -> DeriveDef:
    return next(
        definition
        for definition in script.definitions
        if isinstance(definition, DeriveDef) and definition.name == name
    )


def _shape_fields(script: Script, name: str) -> dict[str, FieldDef]:
    shape = next(
        definition
        for definition in script.definitions
        if isinstance(definition, ShapeDef) and definition.name == name
    )
    return {field.name: field for field in shape.fields}


@pytest.mark.parametrize("precision,scale", ((39, 4), (65, 30), (65, 65)))
def test_extended_facts_at_existing_sites_and_safe_aliases(precision, scale):
    script = _parse_script(
        f"type Money = Decimal({precision}, {scale})\n"
        "type Price = Money\n"
        "type OptionalPrice = Price\n"
        f"constraint valid(amount: Decimal({precision}, {scale})) -> Bool:\n    return True\n"
        f"derive keep(amount: Decimal({precision}, {scale}) | None) -> Decimal({precision}, {scale}) | None:\n    return amount\n"
        f"shape Product:\n    direct: Decimal({precision}, {scale}) | None\n    price: OptionalPrice | None\n    plain: Decimal\n    empty: Decimal()\n"
    )
    result = analyze(script)
    assert result.diagnostics == ()
    fields = _shape_fields(script, "Product")
    constraint, derive = _constraint(script, "valid"), _derive(script, "keep")
    fact = DecimalPrecisionScale(precision, scale)
    sites = (
        _type_def(script, "Money").base,
        _type_def(script, "Price").base,
        _type_def(script, "OptionalPrice").base,
        constraint.parameters[0].type,
        derive.parameters[0].type,
        derive.return_type,
        fields["direct"].type_expr,
        fields["price"].type_expr,
    )
    for site in sites:
        assert result.model.decimal_precision_scale_for(site) == fact
    assert result.model.decimal_precision_scale_for(fields["plain"].type_expr) is None
    assert result.model.decimal_precision_scale_for(fields["empty"].type_expr) is None


BASE_SOURCE = (
    "type Money = Decimal(12, 2)\n"
    "shape Order:\n"
    "    price: Decimal(12, 2)\n"
    "    tax: Decimal(10, 4)\n"
    "    amount: Int\n"
    "    score: Float\n"
    "    money: Money\n"
    "    status: Text\n"
    'source orders: Order = postgres.table("orders")\n'
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
        "    let gross = price\n"
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
        ("value = price * score", ["PIE-S2105"]),
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
    assert semantic.script is not None
    ir_result = build_ir(semantic.script, semantic.model)
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


BASE_SHAPE = (
    "shape Order:\n"
    "    price: Decimal(12, 2)\n"
    "    tax: Decimal(10, 4)\n"
    "    amount: Int\n"
    "    score: Float\n"
)


def test_decimal_precision_carriers_remain_private_and_non_public() -> None:
    script, semantic, _ = _fusion_compile(
        _shape_source(
            "postgres.table",
            "table projected:\n    from orders\n    select:\n        price\n",
        )
    )
    fields_by_name = _shape_fields(script, "Order")
    relation = _only_relation_ast(script)
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
    script, semantic, _ = _fusion_compile(
        _shape_source(
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

    relation = _only_relation_ast(script)
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
    script, semantic, _ = _fusion_compile(
        _shape_source(
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
    relation = _only_relation_ast(script)

    for alias in (
        "decimal_total",
        "decimal_int",
        "int_decimal",
        "decimal_minus_int",
    ):
        expression = _binary_select_expression(relation, alias)
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
        expression = _binary_select_expression(relation, alias)
        assert semantic.model.decimal_expression_precision_scale_for(expression) is None


@pytest.mark.parametrize(
    ("projection", "expected_codes"),
    [
        ("value = price * score", ["PIE-S2105"]),
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
        _fusion_parse(
            _shape_source(
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
    script = _fusion_parse(
        _shape_source(
            "postgres.table",
            "table projected:\n"
            "    from orders\n"
            "    select:\n"
            "        value = price / amount\n",
        )
    )
    semantic = analyze(script)
    relation = _only_relation_ast(script)
    expression = _binary_select_expression(relation, "value")

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
        script, semantic, script_ir = _fusion_compile(
            _shape_source(
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
        relation = _only_relation_ast(script)
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

        relation_ir = _only_relation_ir(script_ir)
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


def _shape_source(connector: str, relation: str) -> str:
    return BASE_SHAPE + f'source orders: Order = {connector}("orders")\n' + relation


def _fusion_parse(source: str) -> Script:
    result = parse_source(source, path="phase42_decimal_fusion.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _fusion_compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    script = _fusion_parse(source)
    semantic = analyze(script)
    assert _error_codes(semantic) == []
    ir_result = build_ir(script, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return script, semantic, ir_result.ir


def _only_relation_ast(script: Script) -> TableDef:
    relation = script.definitions[-1]
    assert isinstance(relation, TableDef)
    return relation


def _only_relation_ir(script_ir: ScriptIR) -> RelationIR:
    relations = [
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert len(relations) == 1
    return relations[0]


def _binary_select_expression(relation: TableDef, alias: str) -> BinaryExpr:
    for item in relation.select_items:
        if item.alias == alias:
            expression = item.expression
            assert isinstance(expression, BinaryExpr)
            return expression
    raise AssertionError(f"Missing select alias: {alias}")


@pytest.mark.parametrize("connector", ["postgres.table", "mysql.table"])
def test_decimal_int_products_and_signs_keep_logical_types_and_precision(
    connector: str,
) -> None:
    source = BASE_SOURCE.replace("postgres.table", connector) + (
        "query projected:\n    from orders\n    select:\n"
        "        product = price * amount\n"
        "        reverse = amount * price\n"
        "        positive = +price\n"
        "        negative = -price\n"
    )
    parsed = _parse(source)
    semantic = analyze(parsed)
    assert _error_codes(semantic) == []
    assert semantic.script is not None
    script = semantic.script or parsed
    relation = _relation_ast(script, "projected")
    fields = semantic.model.relation_row_schemas[relation].fields
    assert semantic.model.decimal_precision_scale_for(
        _shape_fields(script, "Order")["price"].type_expr
    ) == DecimalPrecisionScale(12, 2)
    for name in ("product", "reverse", "positive", "negative"):
        expected_nullability = (
            EffectiveNullability.UNKNOWN
            if name in {"product", "reverse"}
            else EffectiveNullability.NON_NULL
        )
        _assert_value_type(fields[name], "Decimal", expected_nullability)
        _assert_value_type(
            semantic.model.expression_value_types[_select_expression(relation, name)],
            "Decimal",
            expected_nullability,
        )
