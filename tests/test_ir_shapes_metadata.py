from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from pathlib import Path
from typing import Callable

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import IndexDef, Script, ShapeDef
from pietto.errors import Severity
from pietto.ir import (
    CallIR,
    FieldId,
    FieldRefIR,
    IrResult,
    IsNullIR,
    ShapeCheckIR,
    ShapeFieldDeriveIR,
    ShapeFieldIR,
    ShapeIR,
    ShapeIndexIR,
    ShapeUniqueIR,
    SymbolId,
    SymbolNamespace,
    build_ir,
)
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import SemanticModel, analyze

SHAPE_SOURCE = (
    "shape User:\n"
    "    check has_email:\n"
    "        email is not null\n"
    "    email: Text nullable\n"
    "    unique user_email on email\n"
    "    deleted_at: Timestamp nullable\n"
    "    index active_email_idx on email when deleted_at is null\n"
    "    email_norm: Text nullable derive lower(trim(email)) @sensitive\n"
    "    index all_email_idx on email\n"
)


def test_shape_metadata_lowers_in_mixed_source_order_and_preserves_fields() -> None:
    result, _, _ = _build(SHAPE_SOURCE)
    shape = _shape(result)

    assert [type(item) for item in shape.items] == [
        ShapeCheckIR,
        ShapeFieldIR,
        ShapeUniqueIR,
        ShapeFieldIR,
        ShapeIndexIR,
        ShapeFieldIR,
        ShapeIndexIR,
    ]
    assert [item.name for item in shape.items] == [
        "has_email",
        "email",
        "user_email",
        "deleted_at",
        "active_email_idx",
        "email_norm",
        "all_email_idx",
    ]
    assert [field.name for field in shape.fields] == [
        "email",
        "deleted_at",
        "email_norm",
    ]
    assert shape.fields == tuple(
        item for item in shape.items if isinstance(item, ShapeFieldIR)
    )


def test_shape_check_and_index_predicate_lower_with_field_identity() -> None:
    result, _, _ = _build(SHAPE_SOURCE)
    shape = _shape(result)
    owner = SymbolId(SymbolNamespace.TYPE, "User")

    check = next(item for item in shape.items if isinstance(item, ShapeCheckIR))
    assert isinstance(check.expression, IsNullIR)
    assert isinstance(check.expression.value, FieldRefIR)
    assert check.expression.value.field == FieldId(owner=owner, name="email")

    indexes = tuple(item for item in shape.items if isinstance(item, ShapeIndexIR))
    assert indexes[0].fields == ("email",)
    assert isinstance(indexes[0].predicate, IsNullIR)
    assert isinstance(indexes[0].predicate.value, FieldRefIR)
    assert indexes[0].predicate.value.field == FieldId(
        owner=owner,
        name="deleted_at",
    )
    assert indexes[1].predicate is None


def test_unique_and_field_derive_metadata_lower_without_execution() -> None:
    result, _, _ = _build(SHAPE_SOURCE)
    shape = _shape(result)

    unique = next(item for item in shape.items if isinstance(item, ShapeUniqueIR))
    assert unique.name == "user_email"
    assert unique.fields == ("email",)

    derived_field = next(field for field in shape.fields if field.name == "email_norm")
    assert isinstance(derived_field.derive, ShapeFieldDeriveIR)
    assert isinstance(derived_field.derive.expression, CallIR)
    assert derived_field.derive.expression.callee == "lower"
    inner = derived_field.derive.expression.arguments[0]
    assert isinstance(inner, CallIR)
    assert inner.callee == "trim"
    assert not hasattr(derived_field.derive, "execute")


@pytest.mark.parametrize("metadata_kind", ["derive", "check", "index"])
def test_missing_shape_expression_fact_reports_pie_i1000(
    metadata_kind: str,
) -> None:
    _, script, model = _build(SHAPE_SOURCE)
    shape = next(
        definition
        for definition in script.definitions
        if isinstance(definition, ShapeDef)
    )
    if metadata_kind == "derive":
        expression = next(
            field.derive_expression
            for field in shape.fields
            if field.derive_expression is not None
        )
    elif metadata_kind == "check":
        expression = shape.checks[0].expression
    else:
        index = next(
            item
            for item in shape.indexes
            if isinstance(item, IndexDef) and item.predicate is not None
        )
        expression = index.predicate
    assert expression is not None

    value_types = dict(model.expression_value_types)
    value_types.pop(expression)
    incomplete_model = replace(model, expression_value_types=value_types)

    result = build_ir(script, incomplete_model)

    assert result.ir is None
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-I1000",
            Severity.ERROR,
            "Missing semantic fact required for IR lowering: expression value type",
        )
    ]


def test_shape_metadata_is_deeply_frozen_and_frontend_independent() -> None:
    result, _, _ = _build(SHAPE_SOURCE)
    shape = _shape(result)

    _assert_no_parser_or_antlr_objects(shape)
    for value in (
        shape,
        *shape.items,
        next(field.derive for field in shape.fields if field.derive is not None),
    ):
        field = fields(value)[0]
        with pytest.raises(FrozenInstanceError):
            setattr(value, field.name, getattr(value, field.name))


def test_shape_metadata_lowering_does_not_mutate_inputs() -> None:
    _, script, model = _build(SHAPE_SOURCE)
    original_script = deepcopy(script)
    original_model = _semantic_snapshot(model)

    build_ir(script, model)

    assert script == original_script
    assert _semantic_snapshot(model) == original_model


@pytest.mark.parametrize(
    ("path", "expected_type"),
    [
        (Path("examples/shapes/order.pie"), ShapeCheckIR),
        (Path("examples/shapes/user.pie"), ShapeFieldDeriveIR),
        (Path("examples/shapes/user_indexes.pie"), ShapeIndexIR),
        (Path("examples/shapes/user_uniques.pie"), ShapeUniqueIR),
    ],
    ids=lambda value: str(value),
)
def test_shape_metadata_examples_build_without_ir_errors(
    path: Path,
    expected_type: type[object],
) -> None:
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
    shape = _shape(result)
    values: tuple[object, ...] = shape.items + tuple(
        field.derive for field in shape.fields if field.derive is not None
    )
    assert any(isinstance(value, expected_type) for value in values)


def _build(source: str) -> tuple[IrResult, Script, SemanticModel]:
    parse_result = parse_source(source, path="shape-metadata.pie")
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


def _shape(result: IrResult) -> ShapeIR:
    assert result.ir is not None
    return next(
        definition
        for definition in result.ir.definitions
        if isinstance(definition, ShapeIR)
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
