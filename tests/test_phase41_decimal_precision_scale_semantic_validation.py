from __future__ import annotations

import pytest

from pietto.ast_nodes import Script, ShapeDef, TypeDef, TypeExpr
from pietto.errors import Diagnostic, Severity
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import TypeKind, analyze
from pietto.sql import emit_postgres_sql


def test_valid_decimal_precision_scale_type_arguments_remain_plain_decimal() -> None:
    script = _parse(
        "type Money = Decimal(12, 2) not null\n"
        "constraint valid(amount: Decimal(38, 38) not null) -> Bool not null:\n"
        "    true\n"
        "derive keep(amount: Decimal(1, 0) nullable) -> Decimal(10, 2) nullable:\n"
        "    amount\n"
        "shape Product:\n"
        "    price: Decimal(12, 2) not null\n"
        "    money: Money not null\n"
        "    plain: Decimal not null\n"
        "    empty: Decimal() not null\n"
        "    label: Text(max = 255) not null\n"
    )

    semantic_result = analyze(script)

    assert semantic_result.diagnostics == ()

    decimal_type_expressions = _decimal_type_expressions(script)
    assert decimal_type_expressions
    for type_expr in decimal_type_expressions:
        resolved_type = semantic_result.model.type_resolutions[type_expr]
        assert resolved_type.name == "Decimal"
        assert resolved_type.kind is TypeKind.BUILTIN
        assert not hasattr(resolved_type, "precision")
        assert not hasattr(resolved_type, "scale")


@pytest.mark.parametrize(
    ("type_expr", "message"),
    [
        (
            "Decimal(10)",
            "Decimal precision-scale requires exactly two positional integer literal arguments",
        ),
        (
            "Decimal(10, 2, 0)",
            "Decimal precision-scale requires exactly two positional integer literal arguments",
        ),
        (
            "Decimal(precision = 10, scale = 2)",
            "Decimal precision-scale requires exactly two positional integer literal arguments",
        ),
        ("Decimal(10.5, 2)", "Decimal precision and scale must be integer literals"),
        ('Decimal("10", 2)', "Decimal precision and scale must be integer literals"),
        ("Decimal(true, 2)", "Decimal precision and scale must be integer literals"),
        ("Decimal(null, 2)", "Decimal precision and scale must be integer literals"),
        ("Decimal(max, 2)", "Decimal precision and scale must be integer literals"),
        (
            "Decimal(schema.max, 2)",
            "Decimal precision and scale must be integer literals",
        ),
        ("Decimal(max(10), 2)", "Decimal precision and scale must be integer literals"),
        ("Decimal(10 + 1, 2)", "Decimal precision and scale must be integer literals"),
        ("Decimal(-10, 2)", "Decimal precision and scale must be integer literals"),
        ("Decimal(+10, 2)", "Decimal precision and scale must be integer literals"),
        (
            "Decimal(0, 0)",
            "Decimal precision must be an integer from 1 to 38",
        ),
        (
            "Decimal(39, 0)",
            "Decimal precision must be an integer from 1 to 38",
        ),
        (
            "Decimal(10, 11)",
            "Decimal scale must be an integer from 0 to precision",
        ),
    ],
)
def test_invalid_decimal_precision_scale_type_arguments_fail_closed(
    type_expr: str,
    message: str,
) -> None:
    script = _parse(f"shape Product:\n    price: {type_expr} not null\n")

    semantic_result = analyze(script)

    assert _error_diagnostics(semantic_result.diagnostics) == [
        ("PIE-S2004", Severity.ERROR, message)
    ]


def test_invalid_decimal_argument_diagnostic_uses_type_expression_span() -> None:
    script = _parse("shape Product:\n    price: Decimal(0, 0) not null\n")

    diagnostic = analyze(script).diagnostics[0]

    assert diagnostic.code == "PIE-S2004"
    location = diagnostic.location
    assert location is not None
    assert location.end_column is not None
    assert location.line == 2
    assert location.column == 12
    assert location.end_line == 2
    assert location.end_column > location.column


def test_empty_decimal_arguments_preserve_plain_decimal_compatibility() -> None:
    script = _parse("shape Product:\n    amount: Decimal() not null\n")
    shape = _shape(script)
    type_expr = shape.fields[0].type_expr

    semantic_result = analyze(script)

    assert type_expr.arguments == ()
    assert semantic_result.diagnostics == ()
    resolved_type = semantic_result.model.type_resolutions[type_expr]
    assert resolved_type.name == "Decimal"
    assert resolved_type.kind is TypeKind.BUILTIN


def test_non_decimal_type_arguments_remain_compatibility_surface() -> None:
    script = _parse(
        "type Label = Text(max = 32, encoding = utf8) not null\n"
        "shape Product:\n"
        "    count: Int(max = 5000) not null\n"
        "    label: Label not null\n"
    )

    assert analyze(script).diagnostics == ()


def test_decimal_precision_scale_validation_adds_no_carrier_or_sql_output() -> None:
    source = (
        "shape Product:\n"
        "    price: Decimal(12, 2) not null\n"
        'source products: Product is postgres.table("products")\n'
        "table projected:\n"
        "    from products\n"
        "    select:\n"
        "        price\n"
    )
    script = _parse(source)
    semantic_result = analyze(script)
    assert semantic_result.diagnostics == ()

    script_ir = build_ir(script, semantic_result.model)

    assert script_ir.diagnostics == ()
    assert script_ir.ir is not None
    sql_result = emit_postgres_sql(script_ir.ir)
    combined_sql = "\n".join(artifact.sql for artifact in sql_result.artifacts)

    assert sql_result.diagnostics == ()
    assert "DECIMAL(" not in combined_sql
    assert "NUMERIC(" not in combined_sql
    assert "precision" not in combined_sql
    assert "scale" not in combined_sql


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _shape(script: Script) -> ShapeDef:
    return next(
        definition
        for definition in script.definitions
        if isinstance(definition, ShapeDef)
    )


def _decimal_type_expressions(script: Script) -> list[TypeExpr]:
    type_expressions: list[TypeExpr] = []
    for definition in script.definitions:
        if isinstance(definition, TypeDef) and definition.base.name == "Decimal":
            type_expressions.append(definition.base)
        if isinstance(definition, ShapeDef):
            type_expressions.extend(
                field.type_expr
                for field in definition.fields
                if field.type_expr.name == "Decimal"
            )
    return type_expressions


def _error_diagnostics(
    diagnostics: tuple[Diagnostic, ...],
) -> list[tuple[str, Severity, str]]:
    return [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
