from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass
from typing import Callable

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import Script, ShapeDef, SourceDef, TableDef
from pietto.ir import (
    NullabilityIR,
    RowFieldIR,
    RowSchemaIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
)
from pietto.ir.lowering import lower_row_schema, lower_type_ref
from pietto.parser_api import parse_source
from pietto.semantic import SemanticModel, analyze


@pytest.mark.parametrize(
    "value",
    [
        SymbolId(SymbolNamespace.TYPE, "Text"),
        TypeRefIR(
            symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
            canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
            declared_name="Text",
            canonical_name="Text",
            kind=TypeKindIR.BUILTIN,
            canonical_kind=TypeKindIR.BUILTIN,
            nullability=NullabilityIR.NON_NULL,
        ),
        RowFieldIR(
            name="email",
            type_ref=TypeRefIR(
                symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
                canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
                declared_name="Text",
                canonical_name="Text",
                kind=TypeKindIR.BUILTIN,
                canonical_kind=TypeKindIR.BUILTIN,
                nullability=NullabilityIR.NULLABLE,
            ),
            nullability=NullabilityIR.NULLABLE,
            span=None,
        ),
        RowSchemaIR(fields=()),
    ],
)
def test_ir_metadata_models_are_frozen(value: object) -> None:
    assert is_dataclass(value)
    field = fields(value)[0]

    with pytest.raises(FrozenInstanceError):
        setattr(value, field.name, getattr(value, field.name))


def test_builtin_type_lowers_with_declared_and_canonical_identity() -> None:
    script, model = _analyzed("shape User:\n    email: Text not null\n")
    type_expr = _shape(script).fields[0].type_expr

    type_ref = lower_type_ref(type_expr, model)

    assert type_ref == TypeRefIR(
        symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
        canonical_symbol=SymbolId(SymbolNamespace.TYPE, "Text"),
        declared_name="Text",
        canonical_name="Text",
        kind=TypeKindIR.BUILTIN,
        canonical_kind=TypeKindIR.BUILTIN,
        nullability=NullabilityIR.NON_NULL,
    )


def test_type_alias_lowers_with_alias_and_canonical_target() -> None:
    script, model = _analyzed(
        "type Email = Text not null\nshape User:\n    email: Email nullable\n"
    )
    type_expr = _shape(script).fields[0].type_expr

    type_ref = lower_type_ref(type_expr, model)

    assert type_ref.symbol == SymbolId(SymbolNamespace.TYPE, "Email")
    assert type_ref.canonical_symbol == SymbolId(SymbolNamespace.TYPE, "Text")
    assert type_ref.declared_name == "Email"
    assert type_ref.canonical_name == "Text"
    assert type_ref.kind is TypeKindIR.TYPE_ALIAS
    assert type_ref.canonical_kind is TypeKindIR.BUILTIN
    assert type_ref.nullability is NullabilityIR.NULLABLE


def test_source_row_schema_lowers_in_field_order_with_copied_spans() -> None:
    script, model = _analyzed(
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Text nullable\n"
        'source users: User is postgres.table("public.users")\n',
        path="metadata.pietto",
    )
    source = _definition(script, SourceDef, "users")

    schema = lower_row_schema(model.source_row_schemas[source], model)

    assert [field.name for field in schema.fields] == ["id", "email"]
    assert [field.nullability for field in schema.fields] == [
        NullabilityIR.NON_NULL,
        NullabilityIR.NULLABLE,
    ]
    assert schema.is_unknown is False
    assert schema.fields[0].span == SourceSpan(
        path="metadata.pietto",
        line=2,
        column=5,
        end_line=2,
        end_column=22,
    )


def test_relation_row_schema_lowers_in_projection_order() -> None:
    script, model = _analyzed(
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Text nullable\n"
        'source users: User is postgres.table("public.users")\n'
        "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "        id\n"
    )
    table = _definition(script, TableDef, "projected")

    schema = lower_row_schema(model.relation_row_schemas[table], model)

    assert [field.name for field in schema.fields] == ["email", "id"]
    assert [field.type_ref.canonical_name for field in schema.fields] == [
        "Text",
        "UUID",
    ]


def test_unknown_row_schema_lowers_without_crashing() -> None:
    script, model = _analyzed('source raw_events is postgres.table("public.events")\n')
    source = _definition(script, SourceDef, "raw_events")

    schema = lower_row_schema(model.source_row_schemas[source], model)

    assert schema == RowSchemaIR(fields=(), is_unknown=True)


def test_lowered_metadata_exposes_neither_parser_ast_nor_antlr_objects() -> None:
    script, model = _analyzed(
        "type Email = Text not null\n"
        "shape User:\n"
        "    email: Email nullable\n"
        'source users: User is postgres.table("public.users")\n'
    )
    shape = _shape(script)
    source = _definition(script, SourceDef, "users")
    metadata = (
        lower_type_ref(shape.fields[0].type_expr, model),
        lower_row_schema(model.source_row_schemas[source], model),
    )

    _assert_no_parser_or_antlr_objects(metadata)


def test_metadata_lowering_does_not_mutate_inputs() -> None:
    script, model = _analyzed(
        "shape User:\n"
        "    id: UUID not null\n"
        'source users: User is postgres.table("public.users")\n'
    )
    source = _definition(script, SourceDef, "users")
    original_script = deepcopy(script)
    original_model = _semantic_snapshot(model)

    lower_type_ref(_shape(script).fields[0].type_expr, model)
    lower_row_schema(model.source_row_schemas[source], model)

    assert script == original_script
    assert _semantic_snapshot(model) == original_model


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
        diagnostic.severity.value != "error"
        for diagnostic in semantic_result.diagnostics
    )
    return parse_result.ast, semantic_result.model


def _shape(script: Script) -> ShapeDef:
    return _definition(script, ShapeDef, "User")


def _definition[DefinitionT: (ShapeDef, SourceDef, TableDef)](
    script: Script,
    definition_type: type[DefinitionT],
    name: str,
) -> DefinitionT:
    return next(
        definition
        for definition in script.definitions
        if isinstance(definition, definition_type) and definition.name == name
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
