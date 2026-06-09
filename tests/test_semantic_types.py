from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import ConstraintDef, DeriveDef, Script, ShapeDef, TypeDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    CheckMode,
    EffectiveNullability,
    SemanticModel,
    TypeKind,
    analyze,
)

BUILTIN_TYPES = (
    "Bool",
    "Text",
    "Int",
    "Float",
    "Decimal",
    "UUID",
    "Timestamp",
    "Date",
    "Json",
    "Bytes",
    "Any",
)


def test_builtin_type_catalog_resolves_supported_names() -> None:
    fields_source = "".join(
        f"    value_{index}: {name} not null\n"
        for index, name in enumerate(BUILTIN_TYPES)
    )
    result = analyze(_parse(f"shape Values:\n{fields_source}"))
    shape = _shape(result.model, "Values")

    assert [
        result.model.type_resolutions[field.type_expr].kind for field in shape.fields
    ] == [TypeKind.BUILTIN] * len(BUILTIN_TYPES)
    assert result.diagnostics == ()


def test_user_type_alias_resolves_with_forward_reference() -> None:
    result = analyze(
        _parse("shape Person:\n    age: Age not null\ntype Age = Int not null\n")
    )
    shape = _shape(result.model, "Person")
    alias = _type_def(result.model, "Age")

    resolved = result.model.type_resolutions[shape.fields[0].type_expr]

    assert resolved.name == "Age"
    assert resolved.kind is TypeKind.TYPE_ALIAS
    assert resolved.definition is alias


def test_enum_type_resolves() -> None:
    result = analyze(
        _parse("enum Status:\n    active\nshape User:\n    status: Status not null\n")
    )
    shape = _shape(result.model, "User")

    resolved = result.model.type_resolutions[shape.fields[0].type_expr]

    assert resolved.kind is TypeKind.ENUM
    assert resolved.definition is result.model.type_symbols["Status"]


def test_shape_type_resolves_in_callable_parameter() -> None:
    result = analyze(
        _parse(
            "constraint valid(user: User not null) -> Bool not null:\n"
            "    true\n"
            "shape User:\n"
            "    id: UUID not null\n"
        )
    )
    constraint = result.model.callable_symbols["valid"]
    assert isinstance(constraint, ConstraintDef)

    resolved = result.model.type_resolutions[constraint.parameters[0].type]

    assert resolved.kind is TypeKind.SHAPE
    assert resolved.definition is result.model.type_symbols["User"]


def test_unknown_type_reports_p2002_and_records_placeholder() -> None:
    result = analyze(_parse("type Value = Missing not null\n"))
    type_expr = _type_def(result.model, "Value").base

    assert [
        (diagnostic.code, diagnostic.severity) for diagnostic in result.diagnostics
    ] == [("P2002", Severity.ERROR)]
    assert result.diagnostics[0].message == "Unknown type: Missing"
    assert result.model.type_resolutions[type_expr].kind is TypeKind.UNKNOWN
    assert result.model.type_resolutions[type_expr].definition is None


def test_unknown_type_diagnostic_uses_type_expression_span() -> None:
    path = Path("examples/semantic/unknown-type.pie")
    script = _parse("type Value = Missing not null\n", path=path)
    definition = script.definitions[0]
    assert isinstance(definition, TypeDef)
    type_expr = definition.base

    diagnostic = analyze(script).diagnostics[0]

    assert diagnostic.location.path == str(path)
    assert diagnostic.location.line == type_expr.span.line
    assert diagnostic.location.column == type_expr.span.column
    assert diagnostic.location.end_line == type_expr.span.end_line
    assert diagnostic.location.end_column == type_expr.span.end_column


def test_unknown_type_does_not_stop_unrelated_resolution() -> None:
    result = analyze(
        _parse(
            "shape Values:\n    missing: Missing not null\n    text: Text not null\n"
        )
    )
    shape = _shape(result.model, "Values")

    assert (
        result.model.type_resolutions[shape.fields[0].type_expr].kind
        is TypeKind.UNKNOWN
    )
    assert (
        result.model.type_resolutions[shape.fields[1].type_expr].kind
        is TypeKind.BUILTIN
    )
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["P2002"]


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (CheckMode.LOOSE, ()),
        (CheckMode.CHECKED, (("P2005", Severity.WARNING),)),
        (CheckMode.STRICT, (("P2005", Severity.ERROR),)),
    ],
)
def test_implicit_nullability_mode_policy(
    mode: CheckMode,
    expected: tuple[tuple[str, Severity], ...],
) -> None:
    result = analyze(_parse("type Age = Int\n"), mode_override=mode)
    type_expr = _type_def(result.model, "Age").base

    assert (
        tuple(
            (diagnostic.code, diagnostic.severity) for diagnostic in result.diagnostics
        )
        == expected
    )
    assert result.model.type_nullability[type_expr] is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize(
    ("syntax", "expected"),
    [
        ("nullable", EffectiveNullability.NULLABLE),
        ("not null", EffectiveNullability.NON_NULL),
    ],
)
def test_explicit_nullability_has_no_p2005(
    syntax: str,
    expected: EffectiveNullability,
) -> None:
    result = analyze(_parse(f"type Age = Int {syntax}\n"))
    type_expr = _type_def(result.model, "Age").base

    assert result.diagnostics == ()
    assert result.model.type_nullability[type_expr] is expected


def test_all_supported_type_expression_locations_are_recorded() -> None:
    result = analyze(
        _parse(
            "type Age = Int not null\n"
            "constraint valid(value: Age nullable) -> Bool not null:\n"
            "    true\n"
            "derive normalize(value: Text not null) -> Text nullable:\n"
            "    value\n"
            "shape User:\n"
            "    age: Age not null\n"
        )
    )
    alias = _type_def(result.model, "Age")
    constraint = result.model.callable_symbols["valid"]
    derive = result.model.callable_symbols["normalize"]
    shape = _shape(result.model, "User")
    assert isinstance(constraint, ConstraintDef)
    assert isinstance(derive, DeriveDef)
    expected = {
        alias.base,
        constraint.parameters[0].type,
        constraint.return_type,
        derive.parameters[0].type,
        derive.return_type,
        shape.fields[0].type_expr,
    }

    assert set(result.model.type_resolutions) == expected
    assert set(result.model.type_nullability) == expected
    assert result.diagnostics == ()


def test_duplicate_symbol_diagnostic_still_works_with_type_resolution() -> None:
    result = analyze(_parse("type Value = Int not null\ntype Value = Text not null\n"))

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["P2001"]


def test_type_and_duplicate_diagnostics_follow_source_order() -> None:
    result = analyze(
        _parse(
            "type First = Missing not null\n"
            "type Value = Int\n"
            "type Value = Text not null\n"
        )
    )

    assert [
        (diagnostic.location.line, diagnostic.code) for diagnostic in result.diagnostics
    ] == [(1, "P2002"), (2, "P2005"), (3, "P2001")]


def test_type_resolution_mappings_are_readonly() -> None:
    model = analyze(_parse("type Age = Int not null\n")).model
    type_expr = _type_def(model, "Age").base

    with pytest.raises(TypeError):
        model.type_resolutions[type_expr] = object()  # type: ignore[index]
    with pytest.raises(TypeError):
        model.type_nullability[type_expr] = object()  # type: ignore[index]


def test_type_resolution_does_not_mutate_input_ast() -> None:
    script = _parse(
        "constraint valid(value: Text nullable) -> Bool not null:\n    true\n"
    )
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_semantic_type_model_does_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse("type Age = Int not null\nshape User:\n    age: Age nullable\n")
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _type_def(model: SemanticModel, name: str) -> TypeDef:
    definition = model.type_symbols[name]
    assert isinstance(definition, TypeDef)
    return definition


def _shape(model: SemanticModel, name: str) -> ShapeDef:
    definition = model.type_symbols[name]
    assert isinstance(definition, ShapeDef)
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
