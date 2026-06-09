from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from typing import Callable

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import Script
from pietto.errors import Severity
from pietto.ir import (
    ConnectorIR,
    EnumIR,
    NullabilityIR,
    ShapeIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    TypeIR,
    TypeKindIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import SemanticModel, analyze


def test_build_ir_lowers_type_alias_identity_and_canonical_target() -> None:
    script, model = _analyzed(
        "type Email = Text not null\ntype WorkEmail = Email nullable\n"
    )

    result = build_ir(script, model)

    assert result.diagnostics == ()
    assert result.ir is not None
    email, work_email = result.ir.definitions
    assert isinstance(email, TypeIR)
    assert isinstance(work_email, TypeIR)
    assert email.symbol == SymbolId(SymbolNamespace.TYPE, "Email")
    assert email.declared_type.declared_name == "Text"
    assert email.canonical_type.canonical_name == "Text"
    assert work_email.symbol == SymbolId(SymbolNamespace.TYPE, "WorkEmail")
    assert work_email.declared_type.symbol == SymbolId(
        SymbolNamespace.TYPE,
        "Email",
    )
    assert work_email.declared_type.kind is TypeKindIR.TYPE_ALIAS
    assert work_email.canonical_type.symbol == SymbolId(
        SymbolNamespace.TYPE,
        "Text",
    )
    assert work_email.canonical_type.kind is TypeKindIR.BUILTIN
    assert work_email.canonical_type.nullability is NullabilityIR.NULLABLE


def test_build_ir_lowers_enum_members_in_source_order() -> None:
    script, model = _analyzed("enum Status:\n    pending\n    active\n    archived\n")

    result = build_ir(script, model)

    assert result.ir is not None
    enum = result.ir.definitions[0]
    assert isinstance(enum, EnumIR)
    assert enum.symbol == SymbolId(SymbolNamespace.TYPE, "Status")
    assert enum.members == ("pending", "active", "archived")


def test_build_ir_lowers_shape_fields_with_type_nullability_and_spans() -> None:
    script, model = _analyzed(
        "type Email = Text not null\n"
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Email nullable\n",
        path="declarations.pie",
    )

    result = build_ir(script, model)

    assert result.ir is not None
    shape = next(
        definition
        for definition in result.ir.definitions
        if isinstance(definition, ShapeIR)
    )
    assert [field.name for field in shape.fields] == ["id", "email"]
    assert shape.fields[0].type_ref.canonical_name == "UUID"
    assert shape.fields[0].nullability is NullabilityIR.NON_NULL
    assert shape.fields[1].type_ref.symbol == SymbolId(
        SymbolNamespace.TYPE,
        "Email",
    )
    assert shape.fields[1].type_ref.canonical_name == "Text"
    assert shape.fields[1].nullability is NullabilityIR.NULLABLE
    assert shape.fields[0].span.path == "declarations.pie"
    assert (
        shape.fields[0].span.line,
        shape.fields[0].span.column,
        shape.fields[0].span.end_line,
        shape.fields[0].span.end_column,
    ) == (3, 5, 3, 22)
    assert shape.span.line == 2


def test_build_ir_lowers_typed_source_schema_and_static_connector() -> None:
    script, model = _analyzed(
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Text nullable\n"
        'source users: User is postgres.table("public.users")\n'
    )

    result = build_ir(script, model)

    assert result.ir is not None
    source = next(
        definition
        for definition in result.ir.definitions
        if isinstance(definition, SourceIR)
    )
    assert source.symbol == SymbolId(SymbolNamespace.RELATION, "users")
    assert source.shape_symbol == SymbolId(SymbolNamespace.TYPE, "User")
    assert [field.name for field in source.row_schema.fields] == ["id", "email"]
    assert source.connector == ConnectorIR(
        name="postgres.table",
        arguments=("public.users",),
        span=source.connector.span,
    )


def test_build_ir_preserves_supported_top_level_source_order() -> None:
    script, model = _analyzed(
        'source users: User is postgres.table("public.users")\n'
        "enum Status:\n"
        "    active\n"
        "shape User:\n"
        "    email: Text not null\n"
        "type Email = Text not null\n"
    )

    result = build_ir(script, model)

    assert result.ir is not None
    assert [
        (type(definition), definition.name) for definition in result.ir.definitions
    ] == [
        (SourceIR, "users"),
        (EnumIR, "Status"),
        (ShapeIR, "User"),
        (TypeIR, "Email"),
    ]


def test_unsupported_definitions_are_skipped_without_crashing() -> None:
    script, model = _analyzed(
        "constraint valid(x: Bool not null) -> Bool not null:\n"
        "    x\n"
        "derive identity(x: Text not null) -> Text not null:\n"
        "    x\n"
        "shape User:\n"
        "    email: Text not null\n"
        'source users: User is postgres.table("public.users")\n'
        "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query output:\n"
        "    from projected\n"
        "    select:\n"
        "        email\n"
    )

    result = build_ir(script, model)

    assert result.diagnostics == ()
    assert result.ir is not None
    assert [type(definition) for definition in result.ir.definitions] == [
        ShapeIR,
        SourceIR,
    ]


@pytest.mark.parametrize(
    "definition_type",
    [TypeIR, EnumIR, ShapeIR, SourceIR, ConnectorIR],
)
def test_declaration_ir_models_are_frozen(definition_type: type[object]) -> None:
    script, model = _analyzed(
        "type Email = Text not null\n"
        "enum Status:\n"
        "    active\n"
        "shape User:\n"
        "    email: Email not null\n"
        'source users: User is postgres.table("public.users")\n'
    )
    result = build_ir(script, model)
    assert result.ir is not None
    values = (
        *result.ir.definitions,
        next(
            definition.connector
            for definition in result.ir.definitions
            if isinstance(definition, SourceIR)
        ),
    )
    value = next(item for item in values if isinstance(item, definition_type))
    field = fields(value)[0]

    with pytest.raises(FrozenInstanceError):
        setattr(value, field.name, getattr(value, field.name))


def test_public_declaration_ir_exposes_neither_ast_nor_antlr_objects() -> None:
    script, model = _analyzed(
        "type Email = Text not null\n"
        "enum Status:\n"
        "    active\n"
        "shape User:\n"
        "    email: Email not null\n"
        'source users: User is postgres.table("public.users")\n'
    )

    _assert_no_parser_or_antlr_objects(build_ir(script, model))


def test_build_ir_does_not_mutate_script_or_semantic_model() -> None:
    script, model = _analyzed(
        "shape User:\n"
        "    email: Text not null\n"
        'source users: User is postgres.table("public.users")\n'
    )
    original_script = deepcopy(script)
    original_model = _semantic_snapshot(model)

    build_ir(script, model)

    assert script == original_script
    assert _semantic_snapshot(model) == original_model


def test_missing_required_semantic_fact_returns_pie_i1000() -> None:
    script, model = _analyzed("type Email = Text not null\n")
    incomplete_model = replace(model, type_expansions={})

    result = build_ir(script, incomplete_model)

    assert result.ir is None
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-I1000",
            Severity.ERROR,
            "Missing semantic fact required for IR lowering: canonical type expansion",
        )
    ]


def _analyzed(
    source: str,
    *,
    path: str | None = None,
) -> tuple[Script, SemanticModel]:
    parse_result = parse_source(source, path=path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    return parse_result.ast, semantic_result.model


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
