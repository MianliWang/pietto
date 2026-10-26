from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pietto.ast_nodes import Script, ShapeDef
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import SemanticResult, analyze

RELATIONS = (
    "shape Row:\n"
    "    id: Int\n"
    'source users: Row = postgres.table("public.users")\n'
    "table groups:\n"
    "    from users\n"
    "    select:\n"
    "        id\n"
    "query accounts:\n"
    "    from groups\n"
    "    select:\n"
    "        id\n"
)
# A second shape for relationship parameters; relationships start on line 15.
MEMBER = "shape Member:\n    id: Int\n    group_id: Int\n"


def test_valid_relationship_is_stored_in_semantic_model() -> None:
    result = analyze(
        _parse(
            RELATIONS + MEMBER + "relationship membership(member: Member, group: Row): "
            "member.group_id == group.id\n"
        )
    )

    assert _graded(result) == []
    assert [
        template.declaration.name for template in result.model.relationship_templates
    ] == ["membership"]
    assert [
        (parameter.name, parameter.shape_name)
        for parameter in result.model.relationship_templates[0].declaration.parameters
    ] == [("member", "Member"), ("group", "Row")]
    # A shape-typed relationship is no source-bound relationship metadata.
    assert result.model.relationships == ()


def test_relationship_and_parameter_source_order_are_preserved() -> None:
    result = analyze(
        _parse(
            RELATIONS + MEMBER + "relationship membership(member: Member, group: Row): "
            "member.group_id == group.id\n"
            "relationship ownership(resource: Row, owner: Member): "
            "resource.id == owner.id\n"
        )
    )

    assert _graded(result) == []
    assert [
        template.declaration.name for template in result.model.relationship_templates
    ] == ["membership", "ownership"]
    assert [
        parameter.name
        for template in result.model.relationship_templates
        for parameter in template.declaration.parameters
    ] == ["member", "group", "resource", "owner"]


def test_parameters_resolve_to_their_declared_shape_symbols() -> None:
    result = analyze(
        _parse(
            RELATIONS + MEMBER + "relationship membership(member: Member, group: Row): "
            "member.group_id == group.id\n"
            "relationship ownership(resource: Row, owner: Member): "
            "resource.id == owner.id\n"
        )
    )

    membership, ownership = result.model.relationship_templates
    member, row = result.model.type_symbols["Member"], result.model.type_symbols["Row"]
    assert isinstance(member, ShapeDef) and isinstance(row, ShapeDef)
    assert membership.parameter_shapes[0] is member
    assert membership.parameter_shapes[1] is row
    assert ownership.parameter_shapes[0] is row
    assert ownership.parameter_shapes[1] is member


def test_self_relationship_resolves_both_parameters_to_same_shape() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship referral(referrer: Row, referred: Row): "
            "referrer.id == referred.id\n"
        )
    )

    (template,) = result.model.relationship_templates
    first, second = template.declaration.parameters
    assert first.name == "referrer"
    assert second.name == "referred"
    assert template.parameter_shapes[0] is template.parameter_shapes[1]
    assert template.parameter_shapes[0] is result.model.type_symbols["Row"]


def test_multiple_relationships_may_share_resolved_shapes() -> None:
    result = analyze(
        _parse(
            RELATIONS + MEMBER + "relationship membership(member: Member, group: Row): "
            "member.group_id == group.id\n"
            "relationship ownership(owner: Member, resource: Row): "
            "owner.id == resource.id\n"
        )
    )

    membership, ownership = result.model.relationship_templates
    assert membership.parameter_shapes[0] is ownership.parameter_shapes[0]
    assert membership.parameter_shapes[1] is ownership.parameter_shapes[1]


def test_relationship_semantic_facts_are_immutable() -> None:
    result = analyze(
        _parse(
            RELATIONS + MEMBER + "relationship membership(member: Member, group: Row): "
            "member.group_id == group.id\n"
        )
    )
    template = result.model.relationship_templates[0]

    with pytest.raises(FrozenInstanceError):
        template.declaration = template.declaration  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        template.declaration.parameters[0].name = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("relationship_source", "expected"),
    [
        (
            "relationship invalid(known: Row, missing: Missing): "
            "known.id == missing.id\n",
            [("Unknown relationship parameter shape: Missing", 15, 34)],
        ),
        (
            "relationship duplicate(first: Row, second: Row): first.id == second.id\n"
            "relationship duplicate(third: Row, fourth: Row): third.id == fourth.id\n",
            # Neither declaration wins: each one is ambiguous.
            [
                ("Ambiguous relationship predicate name: duplicate", 15, 1),
                ("Ambiguous relationship predicate name: duplicate", 16, 1),
            ],
        ),
        (
            "relationship invalid(repeated: Row, repeated: Row): "
            "repeated.id == repeated.id\n",
            [("Duplicate relationship parameter: repeated", 15, 37)],
        ),
    ],
)
def test_invalid_relationships_are_not_stored(
    relationship_source: str,
    expected: list[tuple[str, int, int]],
) -> None:
    result = analyze(_parse(RELATIONS + MEMBER + relationship_source))

    assert _graded(result) == [
        ("PIE-S2604", Severity.ERROR, message, line, column)
        for message, line, column in expected
    ]
    assert result.model.relationship_templates == ()
    assert result.model.relationships == ()


def test_program_without_relationship_metadata_has_empty_semantic_tuple() -> None:
    result = analyze(_parse(RELATIONS))

    assert _graded(result) == []
    assert result.model.relationships == ()
    assert result.model.relationship_templates == ()


def _graded(result: SemanticResult) -> list[tuple[str, Severity, str, int, int]]:
    diagnostics: tuple[Diagnostic, ...] = result.diagnostics
    return [
        (
            diagnostic.code,
            diagnostic.severity,
            diagnostic.message,
            diagnostic.location.line,
            diagnostic.location.column,
        )
        for diagnostic in diagnostics
    ]


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast
