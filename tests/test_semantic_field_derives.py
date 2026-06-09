from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import CallExpr, FieldDef, Script, ShapeDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, TypeKind, ValueTypeKind, analyze


def test_valid_field_derive_uses_same_shape_fields_and_builtins() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    email_norm: Text not null derive lower(trim(email))\n"
        )
    )
    expression = _field(result, "email_norm").derive_expression
    assert isinstance(expression, CallExpr)
    inner = expression.arguments[0]
    assert isinstance(inner, CallExpr)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Text"
    assert result.model.expression_value_types[inner].resolved_type.name == "Text"


def test_field_derive_can_reference_later_field() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email_norm: Text not null derive lower(email)\n"
            "    email: Text not null\n"
        )
    )

    assert result.diagnostics == ()


def test_field_derive_type_mismatch_reports_pie_s2402_at_expression() -> None:
    script = _parse(
        "shape User:\n"
        "    email: Text not null\n"
        "    is_valid: Bool not null derive lower(email)\n",
        path="field-derives.pie",
    )
    shape = script.definitions[0]
    assert isinstance(shape, ShapeDef)
    expression = shape.fields[1].derive_expression
    assert expression is not None

    result = analyze(script)

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2402",
            Severity.ERROR,
            "Field derive body type does not match field type: is_valid",
        )
    ]
    diagnostic = result.diagnostics[0]
    assert diagnostic.location.path == expression.span.path == "field-derives.pie"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (
        expression.span.line,
        expression.span.column,
        expression.span.end_line,
        expression.span.end_column,
    )


def test_unknown_field_derive_function_suppresses_pie_s2402() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    email_norm: Text not null derive normalize(email)\n"
        )
    )
    expression = _field(result, "email_norm").derive_expression
    assert expression is not None

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2103"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_unknown_field_reference_reports_pie_s2102_without_mismatch() -> None:
    result = analyze(
        _parse("shape User:\n    email_norm: Text not null derive lower(missing)\n")
    )
    expression = _field(result, "email_norm").derive_expression
    assert isinstance(expression, CallExpr)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_unknown_declared_field_type_suppresses_pie_s2402() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    email_norm: Missing not null derive lower(email)\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2002"]


def test_field_derive_aliases_use_canonical_types() -> None:
    result = analyze(
        _parse(
            "type Email = Text not null\n"
            "type NormalizedEmail = Email not null\n"
            "shape User:\n"
            "    email: Email not null\n"
            "    email_norm: NormalizedEmail not null derive lower(trim(email))\n"
        )
    )
    field = _field(result, "email_norm")
    expression = field.derive_expression
    assert expression is not None

    assert result.diagnostics == ()
    assert result.model.type_expansions[field.type_expr].kind is TypeKind.BUILTIN
    assert result.model.type_expansions[field.type_expr].name == "Text"
    assert result.model.expression_value_types[expression].resolved_type.name == "Text"


def test_multiple_field_derive_mismatches_follow_source_order() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    is_valid: Bool not null derive lower(email)\n"
            "    email_length: Int not null derive lower(email)\n"
        )
    )

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            3,
            "PIE-S2402",
            "Field derive body type does not match field type: is_valid",
        ),
        (
            4,
            "PIE-S2402",
            "Field derive body type does not match field type: email_length",
        ),
    ]


def test_field_derive_validation_does_not_mutate_input_ast() -> None:
    script = _parse(
        "shape User:\n"
        "    email: Text not null\n"
        "    email_norm: Text not null derive lower(trim(email))\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_field_derive_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    email_norm: Text not null derive lower(trim(email))\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _field(result: SemanticResult, name: str) -> FieldDef:
    definition = result.model.type_symbols["User"]
    assert isinstance(definition, ShapeDef)
    field = next(field for field in definition.fields if field.name == name)
    return field


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)
