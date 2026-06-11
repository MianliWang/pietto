from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import Expression, Script, ShapeDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, ValueTypeKind, analyze


@pytest.mark.parametrize(
    "body",
    [
        "enabled",
        "amount >= 0",
        "label is not null",
        "true",
    ],
)
def test_known_bool_shape_check_passes(body: str) -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    enabled: Bool not null\n"
            "    amount: Int not null\n"
            "    label: Text nullable\n"
            "    check valid:\n"
            f"        {body}\n"
        )
    )
    expression = _shape(result).checks[0].expression

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"


def test_known_non_bool_shape_check_reports_pie_s2202() -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    label: Text not null\n"
            "    check valid_label:\n"
            "        label\n"
        )
    )
    expression = _shape(result).checks[0].expression

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2202",
            Severity.ERROR,
            "Expected Bool expression in shape check",
        )
    ]
    assert result.model.expression_value_types[expression].resolved_type.name == "Text"


def test_known_bool_index_predicate_passes() -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    label: Text nullable\n"
            "    index active_label on label when label is not null\n"
        )
    )
    expression = _index_predicate(result)

    assert result.diagnostics == ()
    assert result.model.expression_value_types[expression].resolved_type.name == "Bool"


def test_known_non_bool_index_predicate_reports_pie_s2202() -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    label: Text not null\n"
            "    index active_label on label when label\n"
        )
    )
    expression = _index_predicate(result)

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2202",
            Severity.ERROR,
            "Expected Bool expression in index predicate",
        )
    ]
    assert result.model.expression_value_types[expression].resolved_type.name == "Text"


@pytest.mark.parametrize("item_kind", ["check", "index"])
def test_shape_predicate_diagnostic_uses_expression_span(item_kind: str) -> None:
    if item_kind == "check":
        item = "    check valid_label:\n        label\n"
    else:
        item = "    index active_label on label when label\n"
    result = analyze(
        _parse(
            f"shape Record:\n    label: Text not null\n{item}",
            path="shape-predicate.pietto",
        )
    )
    shape = _shape(result)
    expression = (
        shape.checks[0].expression if item_kind == "check" else _index_predicate(result)
    )
    diagnostic = result.diagnostics[0]

    assert diagnostic.code == "PIE-S2202"
    assert diagnostic.location.path == expression.span.path == "shape-predicate.pietto"
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


def test_unknown_shape_field_suppresses_bool_cascade() -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    label: Text not null\n"
            "    check valid_label:\n"
            "        missing\n"
        )
    )
    expression = _shape(result).checks[0].expression

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_unknown_field_type_suppresses_bool_cascade() -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    value: Missing not null\n"
            "    check valid_value:\n"
            "        value\n"
        )
    )
    expression = _shape(result).checks[0].expression

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2002"]
    assert result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN


def test_unknown_shape_functions_do_not_cascade_to_bool_diagnostic() -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    label: Text not null\n"
            "    check valid_label:\n"
            "        unknown_check(label)\n"
            "    index active_label on label when unknown_index(label)\n"
        )
    )
    shape = _shape(result)
    expressions = (shape.checks[0].expression, _index_predicate(result))

    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "PIE-S2103",
        "PIE-S2103",
    ]
    assert all(
        result.model.expression_value_types[expression].kind is ValueTypeKind.UNKNOWN
        for expression in expressions
    )


def test_shape_predicate_diagnostics_follow_source_order() -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    label: Text not null\n"
            "    amount: Int not null\n"
            "    check valid_label:\n"
            "        label\n"
            "    index positive_amount on amount when amount\n"
        )
    )

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (5, "PIE-S2202", "Expected Bool expression in shape check"),
        (6, "PIE-S2202", "Expected Bool expression in index predicate"),
    ]


def test_index_without_predicate_adds_no_expression_type() -> None:
    result = analyze(
        _parse(
            "shape Record:\n    label: Text not null\n    index label_idx on label\n"
        )
    )

    assert result.diagnostics == ()
    assert result.model.expression_value_types == {}


def test_shape_predicate_validation_does_not_mutate_input_ast() -> None:
    script = _parse(
        "shape Record:\n"
        "    label: Text not null\n"
        "    check valid_label:\n"
        "        label\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_shape_predicate_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(
            "shape Record:\n"
            "    label: Text not null\n"
            "    index active_label on label when label\n"
        )
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _shape(result: SemanticResult) -> ShapeDef:
    definition = result.model.type_symbols["Record"]
    assert isinstance(definition, ShapeDef)
    return definition


def _index_predicate(result: SemanticResult) -> Expression:
    predicate = _shape(result).indexes[0].predicate
    assert predicate is not None
    return predicate


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
