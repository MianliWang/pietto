from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import ConstraintDef, DeriveDef, Script
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import TypeKind, analyze


def test_constraint_returning_bool_has_no_signature_diagnostic() -> None:
    result = analyze(
        _parse(
            "constraint valid(email: Text not null) -> Bool not null:\n"
            '    matches(email, ".+@.+")\n'
        )
    )

    assert result.diagnostics == ()


def test_constraint_returning_text_reports_pie_s2401() -> None:
    result = analyze(
        _parse("constraint label(email: Text not null) -> Text not null:\n    true\n")
    )

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2401",
            Severity.ERROR,
            "Constraint label must return Bool",
        )
    ]


def test_constraint_bool_alias_uses_canonical_expansion() -> None:
    result = analyze(
        _parse(
            "type Predicate = Bool not null\n"
            "constraint valid() -> Predicate not null:\n"
            "    true\n"
        )
    )
    constraint = _constraint(result.model.callable_symbols["valid"])

    assert (
        result.model.type_resolutions[constraint.return_type].kind
        is TypeKind.TYPE_ALIAS
    )
    assert result.model.type_expansions[constraint.return_type].name == "Bool"
    assert result.diagnostics == ()


def test_unknown_constraint_return_type_suppresses_pie_s2401() -> None:
    result = analyze(_parse("constraint valid() -> Missing not null:\n    true\n"))
    constraint = _constraint(result.model.callable_symbols["valid"])

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2002"]
    assert (
        result.model.type_resolutions[constraint.return_type].kind is TypeKind.UNKNOWN
    )


def test_valid_derive_signature_has_no_callable_diagnostic() -> None:
    result = analyze(
        _parse("derive normalize(value: Text not null) -> Text not null:\n    value\n")
    )

    assert result.diagnostics == ()


def test_derive_unknown_return_type_relies_on_pie_s2002() -> None:
    result = analyze(
        _parse(
            "derive normalize(value: Text not null) -> Missing not null:\n    value\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2002"]


def test_duplicate_constraint_parameter_reports_pie_s2001() -> None:
    result = analyze(
        _parse(
            "constraint equal(value: Text not null, value: Text not null) "
            "-> Bool not null:\n"
            "    true\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2001",
            "Duplicate parameter name in constraint equal: value",
        )
    ]


def test_duplicate_derive_parameter_reports_pie_s2001() -> None:
    result = analyze(
        _parse(
            "derive choose(value: Text not null, value: Text not null) "
            "-> Text not null:\n"
            "    value\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2001",
            "Duplicate parameter name in derive choose: value",
        )
    ]


def test_duplicate_parameter_diagnostic_uses_later_parameter_span() -> None:
    script = _parse(
        "derive choose(value: Text not null, value: Text not null) "
        "-> Text not null:\n"
        "    value\n",
        path="callables.pietto",
    )
    derive = _derive(script.definitions[0])
    duplicate = derive.parameters[1]

    diagnostic = analyze(script).diagnostics[0]

    assert diagnostic.code == "PIE-S2001"
    assert diagnostic.location.path == duplicate.span.path == "callables.pietto"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (
        duplicate.span.line,
        duplicate.span.column,
        duplicate.span.end_line,
        duplicate.span.end_column,
    )


def test_multiple_callable_diagnostics_follow_source_order() -> None:
    result = analyze(
        _parse(
            "constraint first() -> Text not null:\n"
            "    true\n"
            "derive second(value: Text not null, value: Text not null) "
            "-> Text not null:\n"
            "    value\n"
            "constraint third() -> Int not null:\n"
            "    true\n"
        )
    )

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (1, "PIE-S2401", "Constraint first must return Bool"),
        (3, "PIE-S2001", "Duplicate parameter name in derive second: value"),
        (5, "PIE-S2401", "Constraint third must return Bool"),
    ]


def test_user_defined_callable_calls_remain_unsupported() -> None:
    result = analyze(
        _parse(
            "constraint valid(value: Text not null) -> Bool not null:\n"
            "    unknown_constraint(value)\n"
            "derive normalize(value: Text not null) -> Text not null:\n"
            "    unknown_derive(value)\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [
        ("PIE-S2103", "Unknown function: unknown_constraint"),
        ("PIE-S2103", "Unknown function: unknown_derive"),
    ]
    assert len(result.model.expression_value_types) == 4


def test_callable_signature_validation_does_not_mutate_input_ast() -> None:
    script = _parse(
        "constraint label(value: Text not null) -> Text not null:\n    value\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_callable_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse("constraint label(value: Text not null) -> Text not null:\n    value\n")
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _constraint(value: object) -> ConstraintDef:
    assert isinstance(value, ConstraintDef)
    return value


def _derive(value: object) -> DeriveDef:
    assert isinstance(value, DeriveDef)
    return value


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
