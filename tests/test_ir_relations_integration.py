from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Diagnostic, Severity
from pietto.ir import (
    ConstraintIR,
    DeriveIR,
    FieldRefIR,
    FilterIR,
    IrResult,
    IsNullIR,
    RelationIR,
    RelationKindIR,
    ShapeIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    TypeIR,
    build_ir,
)
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import CheckMode, SemanticModel, analyze

PIPELINE_SOURCE = (
    "type Email = Text not null\n"
    "constraint valid_flag(x: Bool not null) -> Bool not null:\n"
    "    x\n"
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text nullable\n"
    "    deleted_at: Timestamp nullable\n"
    "derive copy_email(x: Text not null) -> Text not null:\n"
    "    x\n"
    'source users: User is postgres.table("public.users")\n'
    "table active_users:\n"
    "    from users\n"
    "    where deleted_at is null\n"
    "    select:\n"
    "        email\n"
    "        email_norm = lower(trim(email))\n"
    "        id\n"
    "query active_user_emails:\n"
    "    from active_users\n"
    "    select:\n"
    "        id\n"
    "        email_norm\n"
    "        email\n"
)

EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pietto")))
RELATION_EXAMPLE_PATHS = tuple(
    path
    for path in EXAMPLE_PATHS
    if re.search(r"^(?:table|query)\s", path.read_text(encoding="utf-8"), re.MULTILINE)
)
assert RELATION_EXAMPLE_PATHS, "Expected committed relation examples."


def test_relation_pipeline_preserves_order_dependencies_and_schemas() -> None:
    result, _, _ = _compile(PIPELINE_SOURCE)

    assert result.ir is not None
    assert [
        (type(definition), _definition_name(definition))
        for definition in result.ir.definitions
    ] == [
        (TypeIR, "Email"),
        (ConstraintIR, "valid_flag"),
        (ShapeIR, "User"),
        (DeriveIR, "copy_email"),
        (SourceIR, "users"),
        (RelationIR, "active_users"),
        (RelationIR, "active_user_emails"),
    ]

    source = _definition(result, SourceIR, "users")
    table = _relation(result, "active_users")
    query = _relation(result, "active_user_emails")

    assert table.kind is RelationKindIR.TABLE
    assert table.source.target == SymbolId(SymbolNamespace.RELATION, source.name)
    assert query.kind is RelationKindIR.QUERY
    assert query.source.target == table.symbol
    assert [field.name for field in source.row_schema.fields] == [
        "id",
        "email",
        "deleted_at",
    ]
    assert [field.name for field in table.row_schema.fields] == [
        "email",
        "email_norm",
        "id",
    ]
    assert [field.name for field in query.row_schema.fields] == [
        "id",
        "email_norm",
        "email",
    ]
    assert [projection.name for projection in table.projections] == [
        "email",
        "email_norm",
        "id",
    ]
    assert [projection.name for projection in query.projections] == [
        "id",
        "email_norm",
        "email",
    ]


def test_relation_filter_and_public_graph_are_frontend_independent_and_frozen() -> None:
    result, _, _ = _compile(PIPELINE_SOURCE)
    table = _relation(result, "active_users")

    assert isinstance(table.filter, FilterIR)
    assert isinstance(table.filter.expression, IsNullIR)
    assert isinstance(table.filter.expression.value, FieldRefIR)
    _assert_frontend_independent(table)
    _assert_deeply_frozen(table)


def test_unknown_relation_schema_propagates_without_ir_failure() -> None:
    result, _, _ = _compile(
        'source raw is postgres.table("raw")\n'
        "table projected:\n"
        "    from raw\n"
        "    select:\n"
        "        missing\n"
        "query output:\n"
        "    from projected\n"
        "    select:\n"
        "        missing\n",
        mode=CheckMode.LOOSE,
    )

    assert result.diagnostics == ()
    assert _relation(result, "projected").row_schema.is_unknown is True
    assert _relation(result, "output").row_schema.is_unknown is True


def test_missing_query_schema_reports_deterministic_pie_i1000() -> None:
    _, script, model = _compile(PIPELINE_SOURCE)
    query = next(
        definition
        for definition in script.definitions
        if isinstance(definition, QueryDef)
    )
    schemas = dict(model.relation_row_schemas)
    schemas.pop(query)
    incomplete_model = replace(model, relation_row_schemas=schemas)

    first = build_ir(script, incomplete_model)
    second = build_ir(script, incomplete_model)

    assert first == second
    assert first.ir is None
    assert [
        (
            diagnostic.code,
            diagnostic.severity,
            diagnostic.location.path,
            diagnostic.location.line,
            diagnostic.message,
        )
        for diagnostic in first.diagnostics
    ] == [
        (
            "PIE-I1000",
            Severity.ERROR,
            "relations-integration.pietto",
            query.span.line,
            "Missing semantic fact required for IR lowering: relation row schema",
        )
    ]


@pytest.mark.parametrize("path", RELATION_EXAMPLE_PATHS, ids=str)
def test_relation_examples_match_ast_definition_count_kind_and_order(
    path: Path,
) -> None:
    parse_result = parse_file(path)
    assert parse_result.diagnostics == (), _format_diagnostics(
        path,
        "parser",
        parse_result.diagnostics,
    )
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    semantic_errors = tuple(
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    assert semantic_errors == (), _format_diagnostics(
        path,
        "semantic",
        semantic_errors,
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    ir_errors = tuple(
        diagnostic
        for diagnostic in ir_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    assert ir_errors == (), _format_diagnostics(path, "IR", ir_errors)
    assert ir_result.ir is not None

    expected = [
        (
            RelationKindIR.TABLE
            if isinstance(definition, TableDef)
            else RelationKindIR.QUERY,
            definition.name,
        )
        for definition in parse_result.ast.definitions
        if isinstance(definition, (TableDef, QueryDef))
    ]
    actual = [
        (definition.kind, definition.name)
        for definition in ir_result.ir.definitions
        if isinstance(definition, RelationIR)
    ]
    assert actual == expected


def _compile(
    source: str,
    *,
    mode: CheckMode | None = None,
) -> tuple[IrResult, Script, SemanticModel]:
    parse_result = parse_source(source, path="relations-integration.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast, mode_override=mode)
    semantic_errors = tuple(
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    assert semantic_errors == ()

    result = build_ir(parse_result.ast, semantic_result.model)
    assert all(
        diagnostic.severity is not Severity.ERROR for diagnostic in result.diagnostics
    )
    assert result.ir is not None
    return result, parse_result.ast, semantic_result.model


def _definition[DefinitionT: (TypeIR, ShapeIR, SourceIR)](
    result: IrResult,
    definition_type: type[DefinitionT],
    name: str,
) -> DefinitionT:
    assert result.ir is not None
    return next(
        definition
        for definition in result.ir.definitions
        if isinstance(definition, definition_type) and definition.name == name
    )


def _relation(result: IrResult, name: str) -> RelationIR:
    assert result.ir is not None
    return next(
        definition
        for definition in result.ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _definition_name(definition: object) -> str:
    assert isinstance(
        definition,
        (TypeIR, ConstraintIR, ShapeIR, DeriveIR, SourceIR, RelationIR),
    )
    return definition.name


def _assert_frontend_independent(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    assert not type(value).__module__.startswith("pietto.ast_nodes")
    for child in _children(value):
        _assert_frontend_independent(child)


def _assert_deeply_frozen(value: object) -> None:
    if is_dataclass(value):
        dataclass_fields = fields(value)
        if dataclass_fields:
            field = dataclass_fields[0]
            with pytest.raises(FrozenInstanceError):
                setattr(value, field.name, getattr(value, field.name))
    for child in _children(value):
        _assert_deeply_frozen(child)


def _children(value: object) -> tuple[object, ...]:
    if is_dataclass(value):
        return tuple(getattr(value, field.name) for field in fields(value))
    if isinstance(value, Mapping):
        return tuple((*value.keys(), *value.values()))
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return ()


def _format_diagnostics(
    path: Path,
    stage: str,
    diagnostics: tuple[Diagnostic, ...],
) -> str:
    details = "\n".join(
        (
            f"{diagnostic.severity.value} {diagnostic.code} "
            f"{diagnostic.location.line}:{diagnostic.location.column} "
            f"{diagnostic.message}"
        )
        for diagnostic in diagnostics
    )
    return f"{path} produced {stage} diagnostics:\n{details}"
