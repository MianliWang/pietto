from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import CallExpr, ConstraintDef, DeriveDef, Script
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, TypeKind, ValueTypeKind, analyze


def test_valid_derive_body_uses_parameter_environment() -> None:
    result = analyze(
        _parse(
            "derive normalized_email(email: Text not null) -> Text not null:\n"
            "    lower(trim(email))\n"
        )
    )
    derive = _derive(result, "normalized_email")
    body = derive.body
    assert isinstance(body, CallExpr)
    inner = body.arguments[0]
    assert isinstance(inner, CallExpr)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[body].resolved_type.name == "Text"
    assert result.model.expression_value_types[inner].resolved_type.name == "Text"


def test_derive_body_type_mismatch_reports_pie_s2402() -> None:
    script = _parse(
        "derive normalized_email(email: Text not null) -> Text not null:\n"
        '    matches(email, ".+@.+")\n',
        path="callable-bodies.pietto",
    )
    derive = script.definitions[0]
    assert isinstance(derive, DeriveDef)

    result = analyze(script)

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2402",
            Severity.ERROR,
            "Derive normalized_email body type does not match declared return type",
        )
    ]
    diagnostic = result.diagnostics[0]
    assert diagnostic.location.path == derive.body.span.path == "callable-bodies.pietto"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (
        derive.body.span.line,
        derive.body.span.column,
        derive.body.span.end_line,
        derive.body.span.end_column,
    )


def test_derive_unknown_name_suppresses_body_mismatch() -> None:
    result = analyze(
        _parse(
            "derive normalized_email(email: Text not null) -> Text not null:\n"
            "    missing\n"
        )
    )
    body = _derive(result, "normalized_email").body

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert result.model.expression_value_types[body].kind is ValueTypeKind.UNKNOWN


def test_unknown_parameter_type_suppresses_body_mismatch() -> None:
    result = analyze(
        _parse(
            "derive identity(value: Missing not null) -> Text not null:\n    value\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2002"]


def test_valid_constraint_body_returns_bool() -> None:
    result = analyze(
        _parse(
            "constraint valid_email(email: Text not null) -> Bool not null:\n"
            '    matches(email, ".+@.+")\n'
        )
    )
    body = _constraint(result, "valid_email").body

    assert result.diagnostics == ()
    assert result.model.expression_value_types[body].resolved_type.name == "Bool"


def test_constraint_text_body_reports_pie_s2402() -> None:
    result = analyze(
        _parse(
            "constraint valid_email(email: Text not null) -> Bool not null:\n"
            "    email\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2402",
            "Constraint valid_email body type does not match declared Bool return type",
        )
    ]


def test_constraint_unknown_body_suppresses_pie_s2402() -> None:
    result = analyze(
        _parse(
            "constraint valid_email(email: Text not null) -> Bool not null:\n"
            "    missing\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]


def test_parameter_and_return_aliases_use_canonical_types() -> None:
    result = analyze(
        _parse(
            "type Email = Text not null\n"
            "type NormalizedEmail = Email not null\n"
            "type Predicate = Bool not null\n"
            "derive normalized_email(email: Email not null) "
            "-> NormalizedEmail not null:\n"
            "    lower(trim(email))\n"
            "constraint valid_email(email: Email not null) "
            "-> Predicate not null:\n"
            '    matches(email, ".+@.+")\n'
        )
    )
    derive = _derive(result, "normalized_email")
    constraint = _constraint(result, "valid_email")

    assert result.diagnostics == ()
    assert result.model.type_expansions[derive.return_type].kind is TypeKind.BUILTIN
    assert result.model.type_expansions[derive.return_type].name == "Text"
    assert result.model.expression_value_types[derive.body].resolved_type.name == "Text"
    assert result.model.type_expansions[constraint.return_type].name == "Bool"
    assert (
        result.model.expression_value_types[constraint.body].resolved_type.name
        == "Bool"
    )


def test_wrong_builtin_arguments_suppress_body_mismatch() -> None:
    result = analyze(
        _parse(
            "derive normalized_count(count: Int not null) -> Text not null:\n"
            "    lower(count)\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2104",
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Int",
        )
    ]


def test_duplicate_parameter_diagnostic_still_applies() -> None:
    result = analyze(
        _parse(
            "derive choose(value: Text not null, value: Text not null) "
            "-> Text not null:\n"
            "    value\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2001"]


def test_callable_body_validation_does_not_mutate_input_ast() -> None:
    script = _parse(
        "derive normalized_email(email: Text not null) -> Text not null:\n"
        "    lower(trim(email))\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_callable_body_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            "constraint valid_email(email: Text not null) -> Bool not null:\n"
            '    matches(email, ".+@.+")\n'
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _derive(result: SemanticResult, name: str) -> DeriveDef:
    definition = result.model.callable_symbols[name]
    assert isinstance(definition, DeriveDef)
    return definition


def _constraint(result: SemanticResult, name: str) -> ConstraintDef:
    definition = result.model.callable_symbols[name]
    assert isinstance(definition, ConstraintDef)
    return definition


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
