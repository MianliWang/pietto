from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import Callable

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.errors import Diagnostic, Severity
from pietto.ir import (
    EnumIR,
    IrResult,
    NullabilityIR,
    RelationIR,
    ScriptIR,
    ShapeIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    TypeIR,
    build_ir,
)
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze

EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pie")))
assert EXAMPLE_PATHS, "Expected at least one committed Pietto example."


@pytest.mark.parametrize(
    ("source", "expected_type"),
    [
        ("type Email = Text not null\n", TypeIR),
        ("enum Status:\n    pending\n    active\n", EnumIR),
        ("shape User:\n    email: Text not null\n", ShapeIR),
        (
            "shape User:\n"
            "    email: Text not null\n"
            'source users: User is postgres.table("public.users")\n',
            SourceIR,
        ),
    ],
)
def test_public_pipeline_lowers_each_foundation_declaration(
    source: str,
    expected_type: type[object],
) -> None:
    result = _compile_foundation(source)

    assert result.diagnostics == ()
    assert result.ir is not None
    assert any(
        isinstance(definition, expected_type) for definition in result.ir.definitions
    )


def test_public_pipeline_preserves_supported_definition_and_field_order() -> None:
    result = _compile_foundation(
        "type Email = Text not null\n"
        "enum Status:\n"
        "    pending\n"
        "    active\n"
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Email nullable\n"
        'source users: User is postgres.table("public.users")\n'
    )

    assert result.ir is not None
    assert [type(definition) for definition in result.ir.definitions] == [
        TypeIR,
        EnumIR,
        ShapeIR,
        SourceIR,
    ]
    shape = _definition(result.ir, ShapeIR)
    assert [field.name for field in shape.fields] == ["id", "email"]


def test_alias_and_canonical_type_survive_type_shape_and_source_pipeline() -> None:
    result = _compile_foundation(
        "type Email = Text not null\n"
        "shape User:\n"
        "    id: UUID not null\n"
        "    email: Email nullable\n"
        'source users: User is postgres.table("public.users")\n'
    )

    assert result.ir is not None
    type_ir = _definition(result.ir, TypeIR)
    shape_ir = _definition(result.ir, ShapeIR)
    source_ir = _definition(result.ir, SourceIR)
    shape_email = shape_ir.fields[1]
    source_email = source_ir.row_schema.fields[1]

    assert type_ir.symbol == SymbolId(SymbolNamespace.TYPE, "Email")
    assert type_ir.canonical_type.canonical_name == "Text"
    assert shape_email.type_ref.symbol == type_ir.symbol
    assert shape_email.type_ref.canonical_name == "Text"
    assert shape_email.nullability is NullabilityIR.NULLABLE
    assert source_email.type_ref.symbol == type_ir.symbol
    assert source_email.type_ref.canonical_name == "Text"
    assert source_email.nullability is NullabilityIR.NULLABLE
    assert [field.name for field in source_ir.row_schema.fields] == [
        "id",
        "email",
    ]


def test_source_connector_is_static_metadata_only() -> None:
    result = _compile_foundation(
        "shape User:\n"
        "    id: UUID not null\n"
        'source users: User is postgres.table("public.users")\n'
    )

    assert result.ir is not None
    source = _definition(result.ir, SourceIR)
    assert source.connector.name == "postgres.table"
    assert source.connector.arguments == ("public.users",)
    assert all(
        isinstance(argument, (str, int, float, bool)) or argument is None
        for argument in source.connector.arguments
    )
    assert not hasattr(source.connector, "execute")
    assert not hasattr(source.connector, "connection")


def test_constraint_and_derive_definitions_are_skipped_deterministically() -> None:
    source = (
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

    first = _compile_foundation(source)
    second = _compile_foundation(source)

    assert first == second
    assert first.ir is not None
    assert [type(definition) for definition in first.ir.definitions] == [
        ShapeIR,
        SourceIR,
        RelationIR,
        RelationIR,
    ]


def test_foundation_ir_is_deeply_frozen_and_frontend_independent() -> None:
    result = _compile_foundation(
        "type Email = Text not null\n"
        "enum Status:\n"
        "    active\n"
        "shape User:\n"
        "    email: Email nullable\n"
        'source users: User is postgres.table("public.users")\n'
    )

    assert result.ir is not None
    _assert_no_parser_or_antlr_objects(result)

    mutable_targets = [
        result,
        result.ir,
        *result.ir.definitions,
        _definition(result.ir, ShapeIR).fields[0],
        _definition(result.ir, SourceIR).row_schema.fields[0],
        _definition(result.ir, SourceIR).connector,
    ]
    for value in mutable_targets:
        field = fields(value)[0]
        with pytest.raises(FrozenInstanceError):
            setattr(value, field.name, getattr(value, field.name))


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=str)
def test_committed_example_completes_foundation_ir_pipeline(path: Path) -> None:
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


def test_implemented_ir_diagnostic_codes_are_documented() -> None:
    implemented = _diagnostic_codes_in(Path("src/pietto/ir"))
    documented = set(
        re.findall(
            r"`(PIE-I[0-9]{4})`",
            Path("docs/spec/diagnostics.md").read_text(encoding="utf-8"),
        )
    )

    assert implemented == {"PIE-I1000"}
    assert documented == implemented


def _compile_foundation(source: str) -> IrResult:
    parse_result = parse_source(source, path="integration.pie")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    return build_ir(parse_result.ast, semantic_result.model)


def _definition(
    script_ir: ScriptIR,
    definition_type: type[TypeIR] | type[ShapeIR] | type[SourceIR],
) -> TypeIR | ShapeIR | SourceIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, definition_type)
    )


def _diagnostic_codes_in(root: Path) -> set[str]:
    codes: set[str] = set()
    for path in root.rglob("*.py"):
        codes.update(
            re.findall(
                r'["\'](PIE-I[0-9]{4})["\']',
                path.read_text(encoding="utf-8"),
            )
        )
    return codes


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
