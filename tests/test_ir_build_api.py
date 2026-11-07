from __future__ import annotations

import re
from collections.abc import Mapping
from copy import deepcopy
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
    NullabilityIR,
    RelationIR,
    RelationKindIR,
    ScriptIR,
    ShapeIR,
    SourceIR,
    SymbolId,
    SymbolNamespace,
    TypeIR,
    build_ir,
)
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import SemanticModel, analyze

EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pietto")))
assert EXAMPLE_PATHS, "Expected committed Pietto examples."

ALL_DEFINITIONS_SOURCE = (
    "type Email = Text\n"
    "enum Status:\n"
    "    active\n"
    "    archived\n"
    "constraint valid_email(email: Text) -> Bool:\n"
    '    return matches(email, ".+@.+")\n'
    "derive normalize_email(email: Text) -> Text:\n"
    "    return lower(trim(email))\n"
    "shape User:\n"
    "    id: UUID\n"
    "    email: Text | None\n"
    "    email_norm: Text | None derive lower(trim(email))\n"
    "    has_id = check(id is not None)\n"
    "    user_email = unique(email)\n"
    "    active_email_idx = index(email) when email is not None\n"
    'source users: User = postgres.table("public.users")\n'
    "table active_users:\n"
    "    from users\n"
    "    where email is not None\n"
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


def test_ir_public_objects_store_no_antlr_or_parser_ast_nodes() -> None:
    script, semantic_model = _analyzed_script()

    _assert_frontend_independent(build_ir(script, semantic_model))


def test_compile_to_ir_is_not_exported() -> None:
    assert not hasattr(ir_api, "compile_to_ir")
    assert "compile_to_ir" not in ir_api.__all__


def test_ir_public_exports_are_explicit() -> None:
    assert ir_api.__all__ == [
        "AggregateWindowCallIR",
        "AggregateCallIR",
        "AnyFieldIR",
        "ExistsIR",
        "BetweenIR",
        "BinaryIR",
        "CastIR",
        "CallIR",
        "ConditionalIR",
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
        "JoinEqualityIR",
        "JoinHopIR",
        "JoinIR",
        "JoinKindIR",
        "LiteralIR",
        "MembershipIR",
        "NullabilityIR",
        "ParameterIR",
        "ProjectionIR",
        "QualifyIR",
        "RelationIR",
        "RelationInputIR",
        "RelationInputRoleIR",
        "RelationKindIR",
        "RelationSourceIR",
        "ResultPredicateIR",
        "RowFieldIR",
        "RowSchemaIR",
        "ScriptIR",
        "ShapeCheckIR",
        "ShapeFieldDeriveIR",
        "ShapeFieldIR",
        "ShapeIndexIR",
        "ShapeIR",
        "ShapeItemIR",
        "ShapeUniqueIR",
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


def test_all_public_ir_model_types_are_exported_without_internal_helpers() -> None:
    internal_types = (
        "LimitIR",
        "NamedWindowBaseIR",
        "NamedWindowDeclarationIR",
        "NamedWindowLocalSpecIR",
        "NamedWindowOccurrenceIR",
        "NamedWindowUseIR",
        "OrderDirectionIR",
        "OrderItemIR",
        "WindowCallIR",
        "WindowFrameBoundIR",
        "WindowFrameBoundKindIR",
        "WindowFrameExclusionIR",
        "WindowFrameIR",
        "WindowFrameUnitIR",
        "WindowFunctionIdentityIR",
        "WindowFunctionRoleIR",
        "WindowNthDirectionIR",
        "WindowNullTreatmentIR",
        "WindowOrderItemIR",
        "WindowSpecIR",
        "WindowRelationOccurrenceIR",
        "WindowUseKindIR",
        "WindowUseOccurrenceIR",
    )
    model_types = {
        name
        for name, value in vars(ir_model).items()
        if _is_public_model_type(name, value)
    }
    for internal_type in internal_types:
        model_types.remove(internal_type)

    assert set(ir_api.__all__) == model_types | {"ShapeItemIR", "build_ir"}
    assert all(hasattr(ir_api, name) for name in ir_api.__all__)
    for internal_type in internal_types:
        assert not hasattr(ir_api, internal_type)
    for helper in ("lower_expr", "lower_row_schema", "lower_type_ref"):
        assert not hasattr(ir_api, helper)
        assert helper not in ir_api.__all__
    assert not hasattr(ir_api, "compile_to_ir")


@pytest.mark.parametrize(
    ("source", "expected_type"),
    [
        ("type Email = Text\n", TypeIR),
        ("enum Status:\n    pending\n    active\n", EnumIR),
        ("shape User:\n    email: Text\n", ShapeIR),
        (
            "shape User:\n"
            "    email: Text\n"
            'source users: User = postgres.table("public.users")\n',
            SourceIR,
        ),
    ],
)
def test_public_pipeline_lowers_each_foundation_declaration(
    source: str,
    expected_type: type[object],
) -> None:
    result = _compile(source)

    assert result.diagnostics == ()
    assert result.ir is not None
    assert any(
        isinstance(definition, expected_type) for definition in result.ir.definitions
    )


def test_public_pipeline_preserves_supported_definition_and_field_order() -> None:
    result = _compile(
        "type Email = Text\n"
        "enum Status:\n"
        "    pending\n"
        "    active\n"
        "shape User:\n"
        "    id: UUID\n"
        "    email: Email | None\n"
        'source users: User = postgres.table("public.users")\n'
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
    result = _compile(
        "type Email = Text\n"
        "shape User:\n"
        "    id: UUID\n"
        "    email: Email | None\n"
        'source users: User = postgres.table("public.users")\n'
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
    result = _compile(
        "shape User:\n"
        "    id: UUID\n"
        'source users: User = postgres.table("public.users")\n'
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


def test_constraint_and_derive_definitions_lower_deterministically() -> None:
    source = (
        "constraint valid(x: Bool) -> Bool:\n"
        "    return x\n"
        "derive identity(x: Text) -> Text:\n"
        "    return x\n"
        "shape User:\n"
        "    email: Text\n"
        'source users: User = postgres.table("public.users")\n'
        "table projected:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
        "query output:\n"
        "    from projected\n"
        "    select:\n"
        "        email\n"
    )

    first = _compile(source)
    second = _compile(source)

    assert first == second
    assert first.ir is not None
    assert [type(definition) for definition in first.ir.definitions] == [
        ConstraintIR,
        DeriveIR,
        ShapeIR,
        SourceIR,
        RelationIR,
        RelationIR,
    ]


def test_foundation_ir_is_deeply_frozen_and_frontend_independent() -> None:
    result = _compile(
        "type Email = Text\n"
        "enum Status:\n"
        "    active\n"
        "shape User:\n"
        "    email: Email | None\n"
        'source users: User = postgres.table("public.users")\n'
    )

    assert result.ir is not None
    _assert_frontend_independent(result)

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


def test_every_supported_top_level_definition_lowers_in_source_order() -> None:
    result, _, _ = _build(ALL_DEFINITIONS_SOURCE)

    assert isinstance(result.ir, ScriptIR)
    assert [
        (
            type(definition),
            _ir_definition_identity(definition)[1],
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
        assert is_dataclass(value)
        dataclass_fields = fields(value)
        if not dataclass_fields:
            continue
        field = dataclass_fields[0]
        with pytest.raises(FrozenInstanceError):
            setattr(value, field.name, getattr(value, field.name))


def test_parser_only_contract_metadata_remains_explicitly_deferred() -> None:
    result, _, _ = _build(
        "type Percent = Float ensure 0 <= self <= 1\n"
        "shape User:\n"
        "    age: Int | None @sensitive "
        "ensure self is None or 0 <= self <= 130\n"
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


def _analyzed_script() -> tuple[Script, SemanticModel]:
    parse_result = parse_source("shape User:\n    id: UUID\n")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert semantic_result.diagnostics == ()
    return parse_result.ast, semantic_result.model


def _compile(source: str) -> IrResult:
    parse_result = parse_source(source, path="integration.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    return build_ir(parse_result.ast, semantic_result.model)


def _build(source: str) -> tuple[IrResult, Script, SemanticModel]:
    parse_result = parse_source(source, path="ir-build-api.pietto")
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


def _definition[DefinitionT: (TypeIR, ShapeIR, SourceIR)](
    script_ir: ScriptIR,
    definition_type: type[DefinitionT],
) -> DefinitionT:
    return next(
        definition
        for definition in script_ir.definitions
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
    else:  # pragma: no cover - the test fails when a new definition is added.
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
