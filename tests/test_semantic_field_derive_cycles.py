from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import FieldDef, Script, ShapeDef
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze


def test_derived_field_depending_on_base_field_is_acyclic() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    email_norm: Text not null derive lower(trim(email))\n"
        )
    )

    assert result.diagnostics == ()


def test_derived_field_can_depend_on_earlier_derived_field() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    email: Text not null\n"
            "    email_norm: Text not null derive lower(email)\n"
            "    display_email: Text not null derive lower(email_norm)\n"
        )
    )

    assert result.diagnostics == ()


def test_derived_field_can_depend_on_later_derived_field() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    display_email: Text not null derive lower(email_norm)\n"
            "    email_norm: Text not null derive lower(email)\n"
            "    email: Text not null\n"
        )
    )

    assert result.diagnostics == ()


def test_direct_field_derive_cycle_reports_pie_s2504() -> None:
    result = analyze(_parse("shape User:\n    a: Text not null derive a\n"))

    assert _diagnostics(result.diagnostics) == [
        ("PIE-S2504", Severity.ERROR, "Derived field cycle involving a")
    ]


def test_two_field_derive_cycle_reports_once_at_earliest_field() -> None:
    script = _parse(
        "shape User:\n    a: Text not null derive b\n    b: Text not null derive a\n",
        path="field-cycles.pietto",
    )
    shape = script.definitions[0]
    assert isinstance(shape, ShapeDef)

    diagnostic = analyze(script).diagnostics[0]

    assert _diagnostics((diagnostic,)) == [
        ("PIE-S2504", Severity.ERROR, "Derived field cycle involving a")
    ]
    _assert_location_matches(diagnostic, shape.fields[0])


def test_three_field_derive_cycle_reports_once() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    a: Text not null derive b\n"
            "    b: Text not null derive c\n"
            "    c: Text not null derive a\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2504"]
    assert result.diagnostics[0].message == "Derived field cycle involving a"


def test_nested_builtin_call_dependency_participates_in_cycle() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    a: Text not null derive lower(trim(b))\n"
            "    b: Text not null derive lower(trim(a))\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2504"]


def test_comparison_dependencies_participate_in_cycle() -> None:
    result = analyze(
        _parse(
            "shape Flags:\n"
            "    a: Bool not null derive b == true\n"
            "    b: Bool not null derive a == true\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2504"]


def test_is_null_dependencies_participate_in_cycle() -> None:
    result = analyze(
        _parse(
            "shape Flags:\n"
            "    a: Bool not null derive b is null\n"
            "    b: Bool not null derive a is not null\n"
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2504"]


def test_unknown_field_does_not_create_fake_cycle() -> None:
    result = analyze(
        _parse("shape User:\n    a: Text not null derive lower(missing)\n")
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]


def test_shapes_are_checked_independently() -> None:
    result = analyze(
        _parse(
            "shape First:\n"
            "    a: Text not null derive a\n"
            "shape Second:\n"
            "    a: Text not null derive b\n"
            "    b: Text not null derive a\n"
        )
    )

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (2, "PIE-S2504", "Derived field cycle involving a"),
        (4, "PIE-S2504", "Derived field cycle involving a"),
    ]


def test_disjoint_cycles_are_reported_in_source_order() -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    first: Text not null derive second\n"
            "    second: Text not null derive first\n"
            "    third: Text not null derive fourth\n"
            "    fourth: Text not null derive third\n"
        )
    )

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (2, "PIE-S2504", "Derived field cycle involving first"),
        (4, "PIE-S2504", "Derived field cycle involving third"),
    ]


def test_field_derive_cycle_analysis_does_not_mutate_input_ast() -> None:
    script = _parse(
        "shape User:\n    a: Text not null derive b\n    b: Text not null derive a\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_field_derive_cycle_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            "shape User:\n"
            "    a: Text not null derive b\n"
            "    b: Text not null derive a\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _diagnostics(
    diagnostics: tuple[Diagnostic, ...],
) -> list[tuple[str, Severity, str]]:
    return [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in diagnostics
    ]


def _assert_location_matches(diagnostic: Diagnostic, field: FieldDef) -> None:
    span = field.span
    assert diagnostic.location.path == span.path == "field-cycles.pietto"
    assert diagnostic.location.line == span.line
    assert diagnostic.location.column == span.column
    assert diagnostic.location.end_line == span.end_line
    assert diagnostic.location.end_column == span.end_column


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
