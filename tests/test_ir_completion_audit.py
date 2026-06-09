from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
from enum import StrEnum
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

import pietto.ir as ir_api
import pietto.ir.model as ir_model
from pietto.ast_nodes import (
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
)
from pietto.errors import Diagnostic, Severity
from pietto.ir import (
    ConstraintIR,
    DefinitionIR,
    DeriveIR,
    EnumIR,
    IrResult,
    RelationIR,
    RelationKindIR,
    ScriptIR,
    ShapeIR,
    SourceIR,
    TypeIR,
    build_ir,
)
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import SemanticModel, analyze

EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pie")))
assert EXAMPLE_PATHS, "Expected committed Pietto examples."

ALL_DEFINITIONS_SOURCE = (
    "type Email = Text not null\n"
    "enum Status:\n"
    "    active\n"
    "    archived\n"
    "constraint valid_email(email: Text not null) -> Bool not null:\n"
    '    matches(email, ".+@.+")\n'
    "derive normalize_email(email: Text not null) -> Text not null:\n"
    "    lower(trim(email))\n"
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text nullable\n"
    "    email_norm: Text nullable derive lower(trim(email))\n"
    "    check has_id:\n"
    "        id is not null\n"
    "    unique user_email on email\n"
    "    index active_email_idx on email when email is not null\n"
    'source users: User is postgres.table("public.users")\n'
    "table active_users:\n"
    "    from users\n"
    "    where email is not null\n"
    "    select:\n"
    "        id\n"
    "        email\n"
    "        email_norm\n"
    "query active_user_emails:\n"
    "    from active_users\n"
    "    select:\n"
    "        email\n"
    "        email_norm\n"
)


def test_all_public_ir_model_types_are_exported_without_internal_helpers() -> None:
    model_types = {
        name
        for name, value in vars(ir_model).items()
        if _is_public_model_type(name, value)
    }

    assert set(ir_api.__all__) == model_types | {"ShapeItemIR", "build_ir"}
    assert all(hasattr(ir_api, name) for name in ir_api.__all__)
    for helper in ("lower_expr", "lower_row_schema", "lower_type_ref"):
        assert not hasattr(ir_api, helper)
        assert helper not in ir_api.__all__
    assert not hasattr(ir_api, "compile_to_ir")


def test_every_supported_top_level_definition_lowers_in_source_order() -> None:
    result, _, _ = _build(ALL_DEFINITIONS_SOURCE)

    assert isinstance(result.ir, ScriptIR)
    assert [
        (
            type(definition),
            definition.name,
            definition.kind if isinstance(definition, RelationIR) else None,
        )
        for definition in result.ir.definitions
    ] == [
        (TypeIR, "Email", None),
        (EnumIR, "Status", None),
        (ConstraintIR, "valid_email", None),
        (DeriveIR, "normalize_email", None),
        (ShapeIR, "User", None),
        (SourceIR, "users", None),
        (RelationIR, "active_users", RelationKindIR.TABLE),
        (RelationIR, "active_user_emails", RelationKindIR.QUERY),
    ]


def test_complete_public_ir_graph_is_immutable_and_frontend_independent() -> None:
    result, _, _ = _build(ALL_DEFINITIONS_SOURCE)

    _assert_frontend_independent(result)
    _assert_tuple_collections(result)
    for value in _dataclass_values(result):
        dataclass_fields = fields(value)
        if not dataclass_fields:
            continue
        field = dataclass_fields[0]
        with pytest.raises(FrozenInstanceError):
            setattr(value, field.name, getattr(value, field.name))


def test_parser_only_contract_metadata_remains_explicitly_deferred() -> None:
    result, _, _ = _build(
        "type Percent = Float not null ensure self between 0 and 1\n"
        "shape User:\n"
        "    age: Int nullable @sensitive "
        "ensure self is null or self between 0 and 130\n"
    )
    assert result.ir is not None
    type_ir = next(
        definition
        for definition in result.ir.definitions
        if isinstance(definition, TypeIR)
    )
    shape_ir = next(
        definition
        for definition in result.ir.definitions
        if isinstance(definition, ShapeIR)
    )

    assert not hasattr(type_ir, "ensures")
    assert not hasattr(shape_ir.fields[0], "annotations")
    assert not hasattr(shape_ir.fields[0], "ensure_clauses")


def test_missing_semantic_fact_returns_documented_pie_i1000() -> None:
    _, script, model = _build(ALL_DEFINITIONS_SOURCE)
    incomplete_model = replace(model, from_resolutions={})

    result = build_ir(script, incomplete_model)

    assert result.ir is None
    assert result.diagnostics
    assert {
        (diagnostic.code, diagnostic.severity) for diagnostic in result.diagnostics
    } == {("PIE-I1000", Severity.ERROR)}
    documented = Path("docs/spec/diagnostics.md").read_text(encoding="utf-8")
    assert "`PIE-I1000`" in documented


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=str)
def test_example_ast_definitions_have_matching_ir_definitions(path: Path) -> None:
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

    assert [
        _ast_definition_identity(definition)
        for definition in parse_result.ast.definitions
    ] == [
        _ir_definition_identity(definition) for definition in ir_result.ir.definitions
    ]


def test_implemented_ir_diagnostics_match_documented_codes() -> None:
    implemented: set[str] = set()
    for path in Path("src/pietto/ir").rglob("*.py"):
        implemented.update(
            re.findall(
                r'["\'](PIE-I[0-9]{4})["\']',
                path.read_text(encoding="utf-8"),
            )
        )
    documented = set(
        re.findall(
            r"`(PIE-I[0-9]{4})`",
            Path("docs/spec/diagnostics.md").read_text(encoding="utf-8"),
        )
    )

    assert implemented == documented == {"PIE-I1000"}


def _build(source: str) -> tuple[IrResult, Script, SemanticModel]:
    parse_result = parse_source(source, path="ir-completion-audit.pie")
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


def _is_public_model_type(name: str, value: object) -> bool:
    if name.startswith("_") or getattr(value, "__module__", None) != ir_model.__name__:
        return False
    if is_dataclass(value):
        return True
    return isinstance(value, type) and issubclass(value, StrEnum)


def _ast_definition_identity(definition: Definition) -> tuple[str, str]:
    kind = {
        TypeDef: "type",
        EnumDef: "enum",
        ConstraintDef: "constraint",
        DeriveDef: "derive",
        ShapeDef: "shape",
        SourceDef: "source",
        TableDef: "table",
        QueryDef: "query",
    }[type(definition)]
    return kind, definition.name


def _ir_definition_identity(definition: DefinitionIR) -> tuple[str, str]:
    if isinstance(definition, TypeIR):
        kind = "type"
    elif isinstance(definition, EnumIR):
        kind = "enum"
    elif isinstance(definition, ConstraintIR):
        kind = "constraint"
    elif isinstance(definition, DeriveIR):
        kind = "derive"
    elif isinstance(definition, ShapeIR):
        kind = "shape"
    elif isinstance(definition, SourceIR):
        kind = "source"
    elif isinstance(definition, RelationIR):
        kind = definition.kind.value
    else:  # pragma: no cover - the audit fails when a new definition is added.
        raise AssertionError(f"Unmapped IR definition: {type(definition).__name__}")
    return kind, definition.name


def _assert_frontend_independent(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    assert not type(value).__module__.startswith("pietto.ast_nodes")
    for child in _children(value):
        _assert_frontend_independent(child)


def _assert_tuple_collections(value: object) -> None:
    assert not isinstance(value, (list, dict, set))
    for child in _children(value):
        _assert_tuple_collections(child)


def _dataclass_values(value: object) -> tuple[object, ...]:
    values: list[object] = []
    if is_dataclass(value):
        values.append(value)
    for child in _children(value):
        values.extend(_dataclass_values(child))
    return tuple(values)


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
