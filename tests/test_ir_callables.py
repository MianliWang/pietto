from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from pathlib import Path
from typing import Callable

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import DeriveDef, Script
from pietto.errors import Severity
from pietto.ir import (
    CallIR,
    ConstraintIR,
    DeriveIR,
    FieldId,
    FieldRefIR,
    IrResult,
    ParameterIR,
    SymbolId,
    SymbolNamespace,
    TypeIR,
    TypeKindIR,
    build_ir,
)
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import SemanticModel, analyze

CALLABLE_SOURCE = (
    "type Email = Text not null\n"
    "type Predicate = Bool not null\n"
    "constraint valid_email(email: Email not null) -> Predicate not null:\n"
    '    matches(email, ".+@.+")\n'
    "derive normalized_email(prefix: Text not null, email: Email not null) "
    "-> Email not null:\n"
    "    trim(email)\n"
)


def test_constraint_and_derive_lower_in_source_order() -> None:
    result, _, _ = _build(CALLABLE_SOURCE)

    assert result.ir is not None
    assert [
        (type(definition), definition.name) for definition in result.ir.definitions
    ] == [
        (TypeIR, "Email"),
        (TypeIR, "Predicate"),
        (ConstraintIR, "valid_email"),
        (DeriveIR, "normalized_email"),
    ]


def test_constraint_ir_preserves_signature_and_expression_body() -> None:
    result, _, _ = _build(CALLABLE_SOURCE)
    constraint = _callable(result, ConstraintIR)

    assert constraint.symbol == SymbolId(
        SymbolNamespace.CALLABLE,
        "valid_email",
    )
    assert [parameter.name for parameter in constraint.parameters] == ["email"]
    parameter = constraint.parameters[0]
    assert parameter.type_ref.symbol == SymbolId(SymbolNamespace.TYPE, "Email")
    assert parameter.type_ref.canonical_symbol == SymbolId(
        SymbolNamespace.TYPE,
        "Text",
    )
    assert parameter.type_ref.kind is TypeKindIR.TYPE_ALIAS
    assert parameter.type_ref.canonical_kind is TypeKindIR.BUILTIN
    assert constraint.return_type.symbol == SymbolId(
        SymbolNamespace.TYPE,
        "Predicate",
    )
    assert constraint.return_type.canonical_name == "Bool"
    assert isinstance(constraint.body, CallIR)
    assert constraint.body.callee == "matches"


def test_derive_parameters_preserve_order_types_spans_and_body_references() -> None:
    result, _, _ = _build(CALLABLE_SOURCE, path="callables-ir.pie")
    derive = _callable(result, DeriveIR)

    assert [parameter.name for parameter in derive.parameters] == [
        "prefix",
        "email",
    ]
    assert all(isinstance(parameter, ParameterIR) for parameter in derive.parameters)
    assert derive.parameters[0].type_ref.canonical_name == "Text"
    assert derive.parameters[1].type_ref.symbol == SymbolId(
        SymbolNamespace.TYPE,
        "Email",
    )
    assert derive.parameters[1].type_ref.canonical_name == "Text"
    assert derive.parameters[0].span.path == "callables-ir.pie"
    assert derive.return_type.symbol == SymbolId(SymbolNamespace.TYPE, "Email")
    assert derive.return_type.canonical_name == "Text"

    assert isinstance(derive.body, CallIR)
    argument = derive.body.arguments[0]
    assert isinstance(argument, FieldRefIR)
    assert argument.field == FieldId(owner=derive.symbol, name="email")


@pytest.mark.parametrize(
    ("model_field", "target", "expected_fact"),
    [
        ("type_resolutions", "parameter", "type resolution"),
        ("type_expansions", "return", "canonical type expansion"),
        ("expression_value_types", "body", "expression value type"),
    ],
)
def test_missing_callable_semantic_fact_reports_pie_i1000(
    model_field: str,
    target: str,
    expected_fact: str,
) -> None:
    _, script, model = _build(
        "derive identity(value: Text not null) -> Text not null:\n    value\n"
    )
    derive = next(
        definition
        for definition in script.definitions
        if isinstance(definition, DeriveDef)
    )
    key = {
        "parameter": derive.parameters[0].type,
        "return": derive.return_type,
        "body": derive.body,
    }[target]
    values = dict(getattr(model, model_field))
    values.pop(key)
    incomplete_model = replace(model, **{model_field: values})

    result = build_ir(script, incomplete_model)

    assert result.ir is None
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-I1000",
            Severity.ERROR,
            f"Missing semantic fact required for IR lowering: {expected_fact}",
        )
    ]


def test_callable_ir_is_frozen_and_frontend_independent() -> None:
    result, _, _ = _build(CALLABLE_SOURCE)
    constraint = _callable(result, ConstraintIR)
    derive = _callable(result, DeriveIR)

    _assert_no_parser_or_antlr_objects((constraint, derive))
    for value in (
        constraint,
        constraint.parameters[0],
        constraint.body,
        derive,
        derive.parameters[0],
        derive.body,
    ):
        field = fields(value)[0]
        with pytest.raises(FrozenInstanceError):
            setattr(value, field.name, getattr(value, field.name))


def test_callable_lowering_does_not_mutate_inputs() -> None:
    _, script, model = _build(CALLABLE_SOURCE)
    original_script = deepcopy(script)
    original_model = _semantic_snapshot(model)

    build_ir(script, model)

    assert script == original_script
    assert _semantic_snapshot(model) == original_model


@pytest.mark.parametrize(
    "path",
    [
        Path("examples/constraints/valid_email.pie"),
        Path("examples/derives/normalized_email.pie"),
    ],
    ids=str,
)
def test_callable_examples_build_without_ir_errors(path: Path) -> None:
    parse_result = parse_file(path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )

    result = build_ir(parse_result.ast, semantic_result.model)

    assert result.diagnostics == ()
    assert result.ir is not None
    expected_type = ConstraintIR if "constraints" in path.parts else DeriveIR
    assert any(
        isinstance(definition, expected_type) for definition in result.ir.definitions
    )


def _build(
    source: str,
    *,
    path: str | None = None,
) -> tuple[IrResult, Script, SemanticModel]:
    parse_result = parse_source(source, path=path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    result = build_ir(parse_result.ast, semantic_result.model)
    assert result.diagnostics == ()
    assert result.ir is not None
    return result, parse_result.ast, semantic_result.model


def _callable(
    result: IrResult,
    definition_type: type[ConstraintIR] | type[DeriveIR],
) -> ConstraintIR | DeriveIR:
    assert result.ir is not None
    return next(
        definition
        for definition in result.ir.definitions
        if isinstance(definition, definition_type)
    )


def _semantic_snapshot(model: SemanticModel) -> tuple[tuple[str, object], ...]:
    snapshot: list[tuple[str, object]] = []
    for field in fields(model):
        value = getattr(model, field.name)
        if isinstance(value, Mapping):
            value = tuple(value.items())
        snapshot.append((field.name, value))
    return tuple(snapshot)


def _assert_no_parser_or_antlr_objects(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    assert not type(value).__module__.startswith("pietto.ast_nodes")
    _walk_public_values(value, _assert_no_parser_or_antlr_objects)


def _walk_public_values(
    value: object,
    assertion: Callable[[object], None],
) -> None:
    if is_dataclass(value):
        for field in fields(value):
            assertion(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            assertion(key)
            assertion(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            assertion(item)
