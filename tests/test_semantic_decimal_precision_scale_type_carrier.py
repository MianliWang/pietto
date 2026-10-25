from __future__ import annotations

from types import MappingProxyType

import pytest

import pietto.semantic as semantic_api
from pietto.ast_nodes import (
    ConstraintDef,
    DeriveDef,
    FieldDef,
    Script,
    ShapeDef,
    TypeDef,
)
from pietto.ir import SourceIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import TypeKind, analyze
from pietto.semantic.model import DecimalPrecisionScale
from pietto.sql import emit_postgres_sql


def test_decimal_precision_scale_facts_are_stored_for_supported_type_sites() -> None:
    script = _parse(
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
    script = _parse(
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
    script = _parse(
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
    script = _parse(
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
    script = _parse(source)
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


def _parse(source: str) -> Script:
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
    script = _parse(
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
