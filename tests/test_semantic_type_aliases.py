from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import ConstraintDef, Script, ShapeDef, TypeDef
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, TypeKind, analyze


def test_direct_alias_expands_to_builtin_target() -> None:
    result = analyze(
        _parse(
            "type EmailText = Text not null\n"
            "shape User:\n"
            "    email: EmailText not null\n"
        )
    )
    field_type = _shape(result, "User").fields[0].type_expr

    assert result.model.type_resolutions[field_type].kind is TypeKind.TYPE_ALIAS
    assert result.model.type_expansions[field_type].kind is TypeKind.BUILTIN
    assert result.model.type_expansions[field_type].name == "Text"
    assert result.diagnostics == ()


def test_alias_chain_expands_to_final_builtin_target() -> None:
    result = analyze(
        _parse(
            "type Email = Text not null\n"
            "type WorkEmail = Email not null\n"
            "shape User:\n"
            "    email: WorkEmail not null\n"
        )
    )
    field_type = _shape(result, "User").fields[0].type_expr
    work_email = _type_def(result, "WorkEmail")

    assert result.model.type_expansions[work_email.base].name == "Text"
    assert result.model.type_expansions[field_type].name == "Text"
    assert result.model.type_expansions[field_type].kind is TypeKind.BUILTIN


def test_alias_identity_remains_preserved_in_direct_resolution() -> None:
    result = analyze(
        _parse("type Email = Text not null\nshape User:\n    email: Email not null\n")
    )
    field_type = _shape(result, "User").fields[0].type_expr
    alias = _type_def(result, "Email")
    resolved = result.model.type_resolutions[field_type]

    assert resolved.name == "Email"
    assert resolved.kind is TypeKind.TYPE_ALIAS
    assert resolved.definition is alias
    assert result.model.type_expansions[field_type].name == "Text"


@pytest.mark.parametrize(
    ("source", "alias_name", "expected_kind", "target_name"),
    [
        (
            "enum Status:\n    active\ntype StatusAlias = Status not null\n",
            "StatusAlias",
            TypeKind.ENUM,
            "Status",
        ),
        (
            "shape User:\n    id: UUID not null\ntype UserAlias = User not null\n",
            "UserAlias",
            TypeKind.SHAPE,
            "User",
        ),
    ],
)
def test_alias_expands_to_user_type_kind(
    source: str,
    alias_name: str,
    expected_kind: TypeKind,
    target_name: str,
) -> None:
    result = analyze(_parse(source))
    alias = _type_def(result, alias_name)
    expansion = result.model.type_expansions[alias.base]

    assert expansion.kind is expected_kind
    assert expansion.name == target_name
    assert expansion.definition is result.model.type_symbols[target_name]


def test_direct_alias_cycle_reports_pie_s2003() -> None:
    result = analyze(_parse("type A = A not null\n"))
    alias = _type_def(result, "A")

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2003", "Type alias cycle involving A")]
    assert result.model.type_expansions[alias.base].kind is TypeKind.UNKNOWN


def test_indirect_alias_cycle_reports_one_pie_s2003() -> None:
    result = analyze(_parse("type A = B not null\ntype B = A not null\n"))

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2003", "Type alias cycle involving A")]
    assert (
        result.model.type_expansions[_type_def(result, "A").base].kind
        is TypeKind.UNKNOWN
    )
    assert (
        result.model.type_expansions[_type_def(result, "B").base].kind
        is TypeKind.UNKNOWN
    )


def test_multiple_alias_cycles_follow_source_order() -> None:
    result = analyze(
        _parse("type A = B not null\ntype B = A not null\ntype C = C not null\n")
    )

    assert [
        (diagnostic.location.line, diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (1, "PIE-S2003", "Type alias cycle involving A"),
        (3, "PIE-S2003", "Type alias cycle involving C"),
    ]


def test_unknown_alias_target_reports_only_pie_s2002() -> None:
    result = analyze(_parse("type A = Missing not null\ntype B = A not null\n"))

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2002"]
    assert (
        result.model.type_expansions[_type_def(result, "A").base].kind
        is TypeKind.UNKNOWN
    )
    assert (
        result.model.type_expansions[_type_def(result, "B").base].kind
        is TypeKind.UNKNOWN
    )


def test_constraint_returning_bool_alias_is_accepted() -> None:
    result = analyze(
        _parse(
            "type Predicate = Bool not null\n"
            "constraint valid() -> Predicate not null:\n"
            "    true\n"
        )
    )
    constraint = result.model.callable_symbols["valid"]
    assert isinstance(constraint, ConstraintDef)

    assert (
        result.model.type_resolutions[constraint.return_type].kind
        is TypeKind.TYPE_ALIAS
    )
    assert result.model.type_expansions[constraint.return_type].name == "Bool"
    assert result.diagnostics == ()


def test_constraint_returning_text_alias_reports_pie_s2401() -> None:
    result = analyze(
        _parse(
            "type Label = Text not null\n"
            "constraint label() -> Label not null:\n"
            '    "value"\n'
        )
    )

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2401"]


def test_type_expansions_mapping_is_readonly() -> None:
    result = analyze(_parse("type Email = Text not null\n"))
    type_expr = _type_def(result, "Email").base

    with pytest.raises(TypeError):
        result.model.type_expansions[type_expr] = (  # type: ignore[index]
            result.model.type_expansions[type_expr]
        )


def test_type_alias_expansion_does_not_mutate_input_ast() -> None:
    script = _parse("type Email = Text not null\ntype WorkEmail = Email not null\n")
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_type_alias_semantic_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse("type Email = Text not null\ntype WorkEmail = Email not null\n")
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _type_def(result: SemanticResult, name: str) -> TypeDef:
    definition = result.model.type_symbols[name]
    assert isinstance(definition, TypeDef)
    return definition


def _shape(result: SemanticResult, name: str) -> ShapeDef:
    definition = result.model.type_symbols[name]
    assert isinstance(definition, ShapeDef)
    return definition


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)
