from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from typing import Callable

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.ir import (
    CallIR,
    FieldId,
    FieldRefIR,
    FilterIR,
    IrResult,
    IsNullIR,
    ProjectionIR,
    RelationIR,
    RelationKindIR,
    RelationSourceIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, SemanticModel, analyze

SOURCE = (
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text nullable\n"
    "    deleted_at: Timestamp nullable\n"
    'source users: User is postgres.table("public.users")\n'
)


def test_build_ir_lowers_minimal_table() -> None:
    result, _, _ = _build(
        SOURCE + "table projected:\n    from users\n    select:\n        email\n"
    )

    table = _relation_ir(result, "projected")
    assert table.kind is RelationKindIR.TABLE
    assert table.symbol == SymbolId(SymbolNamespace.RELATION, "projected")
    assert table.filter is None
    assert [projection.name for projection in table.projections] == ["email"]


def test_build_ir_lowers_minimal_query() -> None:
    result, _, _ = _build(
        SOURCE + "query output:\n    from users\n    select:\n        id\n"
    )

    query = _relation_ir(result, "output")
    assert query.kind is RelationKindIR.QUERY
    assert query.symbol == SymbolId(SymbolNamespace.RELATION, "output")


def test_relation_source_uses_resolved_symbol_and_span() -> None:
    result, _, _ = _build(
        SOURCE + "table projected:\n    from users\n    select:\n        email\n",
        path="relations.pie",
    )

    relation = _relation_ir(result, "projected")
    assert relation.source == RelationSourceIR(
        target=SymbolId(SymbolNamespace.RELATION, "users"),
        name="users",
        span=relation.source.span,
    )
    assert relation.source.span.path == "relations.pie"
    assert relation.source.span.line == 7


def test_where_lowers_to_filter_with_resolved_field_reference() -> None:
    result, _, _ = _build(
        SOURCE + "table active:\n"
        "    from users\n"
        "    where deleted_at is null\n"
        "    select:\n"
        "        email\n"
    )

    relation = _relation_ir(result, "active")
    assert isinstance(relation.filter, FilterIR)
    assert isinstance(relation.filter.expression, IsNullIR)
    field = relation.filter.expression.value
    assert isinstance(field, FieldRefIR)
    assert field.field == FieldId(
        owner=SymbolId(SymbolNamespace.RELATION, "users"),
        name="deleted_at",
    )


def test_bare_and_aliased_projections_preserve_names_and_order() -> None:
    result, _, _ = _build(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "        email_norm = lower(email)\n"
        "        email\n"
    )

    relation = _relation_ir(result, "projected")
    assert [projection.name for projection in relation.projections] == [
        "id",
        "email_norm",
        "email",
    ]
    bare = relation.projections[0]
    aliased = relation.projections[1]
    assert isinstance(bare, ProjectionIR)
    assert isinstance(bare.expression, FieldRefIR)
    assert bare.expression.field == FieldId(
        owner=SymbolId(SymbolNamespace.RELATION, "users"),
        name="id",
    )
    assert bare.type_ref is not None
    assert bare.type_ref.canonical_name == "UUID"
    assert isinstance(aliased.expression, CallIR)
    assert aliased.expression.callee == "lower"
    assert aliased.type_ref is not None
    assert aliased.type_ref.kind is TypeKindIR.UNKNOWN


def test_relation_row_schema_preserves_semantic_field_order() -> None:
    result, script, model = _build(
        SOURCE + "query output:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "        id\n"
    )
    query_ast = _relation_ast(script, "output")
    query_ir = _relation_ir(result, "output")

    assert list(model.relation_row_schemas[query_ast].fields) == ["email", "id"]
    assert [field.name for field in query_ir.row_schema.fields] == ["email", "id"]


def test_source_table_query_chain_lowers_in_top_level_order() -> None:
    result, _, _ = _build(
        SOURCE + "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query output:\n"
        "    from projected\n"
        "    select:\n"
        "        email\n"
    )

    assert result.ir is not None
    assert [
        (type(definition), definition.name)
        for definition in result.ir.definitions
        if isinstance(definition, (SourceIR, RelationIR))
    ] == [
        (SourceIR, "users"),
        (RelationIR, "projected"),
        (RelationIR, "output"),
    ]
    query = _relation_ir(result, "output")
    assert query.source.target == SymbolId(
        SymbolNamespace.RELATION,
        "projected",
    )
    projection = query.projections[0]
    assert isinstance(projection.expression, FieldRefIR)
    assert projection.expression.field == FieldId(
        owner=query.source.target,
        name="email",
    )


def test_unknown_schema_and_expression_lower_safely() -> None:
    result, _, _ = _build(
        'source raw is postgres.table("raw")\n'
        "table projected:\n"
        "    from raw\n"
        "    select:\n"
        "        missing\n",
        mode=CheckMode.LOOSE,
    )

    relation = _relation_ir(result, "projected")
    assert relation.row_schema.is_unknown is True
    expression = relation.projections[0].expression
    assert isinstance(expression, FieldRefIR)
    assert expression.field is None
    assert expression.value_type.kind is TypeKindIR.UNKNOWN


@pytest.mark.parametrize(
    ("field_name", "expected_fact"),
    [
        ("from_resolutions", "resolved relation input"),
        ("relation_row_schemas", "relation row schema"),
        ("expression_value_types", "expression value type"),
    ],
)
def test_missing_relation_semantic_fact_returns_pie_i1000(
    field_name: str,
    expected_fact: str,
) -> None:
    _, script, model = _build(
        SOURCE + "table projected:\n    from users\n    select:\n        email\n"
    )
    incomplete_model = replace(model, **{field_name: {}})

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


def test_relation_ir_is_frozen_and_frontend_independent() -> None:
    result, _, _ = _build(
        SOURCE + "table active:\n"
        "    from users\n"
        "    where deleted_at is null\n"
        "    select:\n"
        "        email\n"
    )
    relation = _relation_ir(result, "active")
    _assert_no_parser_or_antlr_objects(relation)

    values = [
        relation,
        relation.source,
        relation.filter,
        relation.projections[0],
        relation.row_schema,
    ]
    for value in values:
        assert value is not None
        field = fields(value)[0]
        with pytest.raises(FrozenInstanceError):
            setattr(value, field.name, getattr(value, field.name))


def test_relation_lowering_does_not_mutate_inputs() -> None:
    _, script, model = _build(
        SOURCE + "table projected:\n    from users\n    select:\n        email\n"
    )
    original_script = deepcopy(script)
    original_model = _semantic_snapshot(model)

    build_ir(script, model)

    assert script == original_script
    assert _semantic_snapshot(model) == original_model


def _build(
    source: str,
    *,
    path: str | None = None,
    mode: CheckMode | None = None,
) -> tuple[IrResult, Script, SemanticModel]:
    parse_result = parse_source(source, path=path)
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast, mode_override=mode)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    result = build_ir(parse_result.ast, semantic_result.model)
    assert result.diagnostics == ()
    assert result.ir is not None
    return result, parse_result.ast, semantic_result.model


def _relation_ir(result: IrResult, name: str) -> RelationIR:
    assert result.ir is not None
    return next(
        definition
        for definition in result.ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _relation_ast(script: Script, name: str) -> TableDef | QueryDef:
    return next(
        definition
        for definition in script.definitions
        if isinstance(definition, (TableDef, QueryDef)) and definition.name == name
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
