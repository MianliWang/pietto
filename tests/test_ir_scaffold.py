from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass
from typing import Callable

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

import pietto.ir as ir_api
from pietto.ast_nodes import Script
from pietto.ir import IrResult, ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import SemanticModel, analyze


def test_build_ir_returns_ir_result() -> None:
    script, semantic_model = _analyzed_script()

    result = build_ir(script, semantic_model)

    assert isinstance(result, IrResult)


def test_build_ir_returns_script_ir_without_diagnostics() -> None:
    script, semantic_model = _analyzed_script()

    result = build_ir(script, semantic_model)

    assert isinstance(result.ir, ScriptIR)
    assert isinstance(result.ir.definitions, tuple)
    assert result.diagnostics == ()
    assert isinstance(result.diagnostics, tuple)


def test_ir_result_is_frozen() -> None:
    script, semantic_model = _analyzed_script()
    result = build_ir(script, semantic_model)

    with pytest.raises(FrozenInstanceError):
        result.diagnostics = ()  # type: ignore[misc]


def test_script_ir_is_frozen() -> None:
    script, semantic_model = _analyzed_script()
    result = build_ir(script, semantic_model)
    assert result.ir is not None

    with pytest.raises(FrozenInstanceError):
        result.ir.definitions = ()  # type: ignore[misc]


def test_build_ir_does_not_mutate_parser_ast() -> None:
    script, semantic_model = _analyzed_script()
    original = deepcopy(script)

    build_ir(script, semantic_model)

    assert script == original


def test_build_ir_does_not_mutate_semantic_model() -> None:
    script, semantic_model = _analyzed_script()
    original = _semantic_snapshot(semantic_model)

    build_ir(script, semantic_model)

    assert _semantic_snapshot(semantic_model) == original


def test_ir_public_objects_do_not_expose_antlr_nodes() -> None:
    script, semantic_model = _analyzed_script()

    _assert_no_antlr_nodes(build_ir(script, semantic_model))


def test_ir_public_objects_do_not_store_parser_ast_nodes() -> None:
    script, semantic_model = _analyzed_script()

    _assert_no_parser_ast_nodes(build_ir(script, semantic_model))


def test_compile_to_ir_is_not_exported() -> None:
    assert not hasattr(ir_api, "compile_to_ir")
    assert "compile_to_ir" not in ir_api.__all__


def test_ir_public_exports_are_explicit() -> None:
    assert ir_api.__all__ == [
        "BetweenIR",
        "BinaryIR",
        "CallIR",
        "ComparisonIR",
        "ConnectorIR",
        "ConstraintIR",
        "DefinitionIR",
        "DeriveIR",
        "EnumIR",
        "ExpressionIR",
        "ExpressionLoweringResult",
        "FieldId",
        "FieldRefIR",
        "FilterIR",
        "IrResult",
        "IsNullIR",
        "LiteralIR",
        "NullabilityIR",
        "ParameterIR",
        "ProjectionIR",
        "RelationIR",
        "RelationKindIR",
        "RelationSourceIR",
        "RowFieldIR",
        "RowSchemaIR",
        "ScriptIR",
        "ShapeFieldIR",
        "ShapeIR",
        "SourceIR",
        "SourceSpan",
        "SymbolId",
        "SymbolNamespace",
        "TypeIR",
        "TypeKindIR",
        "TypeRefIR",
        "UnaryIR",
        "build_ir",
    ]


def _analyzed_script() -> tuple[Script, SemanticModel]:
    parse_result = parse_source("shape User:\n    id: UUID not null\n")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert semantic_result.diagnostics == ()
    return parse_result.ast, semantic_result.model


def _semantic_snapshot(model: SemanticModel) -> tuple[tuple[str, object], ...]:
    snapshot: list[tuple[str, object]] = []
    for field in fields(model):
        value = getattr(model, field.name)
        if isinstance(value, Mapping):
            value = tuple(value.items())
        snapshot.append((field.name, value))
    return tuple(snapshot)


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    _walk_public_values(value, _assert_no_antlr_nodes)


def _assert_no_parser_ast_nodes(value: object) -> None:
    assert not type(value).__module__.startswith("pietto.ast_nodes")
    _walk_public_values(value, _assert_no_parser_ast_nodes)


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
