from __future__ import annotations

from pathlib import Path

from pietto.ast_nodes import QueryDef, Script, ShapeDef, SourceDef, TableDef
from pietto.errors import Severity
from pietto.ir import build_ir
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, analyze
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

RELATIONS = (
    "shape User:\n"
    "    id: Int\n"
    'source users: User = postgres.table("public.users")\n'
    'source groups: User = postgres.table("public.groups")\n'
)


def test_valid_relationship_references_existing_relations() -> None:
    result = analyze(
        _parse(
            "relationship membership(member: User, group: User):\n"
            "    member.id == group.id\n" + RELATIONS
        )
    )

    assert result.diagnostics == ()
    assert list(result.model.relation_symbols) == ["users", "groups"]
    assert [item.declaration.name for item in result.model.relationship_templates] == [
        "membership"
    ]


def test_unknown_parameter_shape_reports_s2604_at_parameter_span() -> None:
    path = Path("metadata/unknown-shape.pietto")
    script = _parse(
        RELATIONS + "relationship membership(member: User, group: Missing):\n"
        "    member.id == group.id\n",
        path=path,
    )
    parameter = script.relationship_templates[0].parameters[1]

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in analyze(script).diagnostics
    ] == [
        (
            "PIE-S2604",
            Severity.ERROR,
            "Unknown relationship parameter shape: Missing",
        )
    ]
    diagnostic = analyze(script).diagnostics[0]
    assert diagnostic.location.path == parameter.span.path
    assert diagnostic.location.line == parameter.span.line
    assert diagnostic.location.column == parameter.span.column
    assert diagnostic.location.end_line == parameter.span.end_line
    assert diagnostic.location.end_column == parameter.span.end_column


def test_duplicate_relationship_name_reports_s2604_at_every_declaration() -> None:
    """Neither declaration wins: each one is reported as ambiguous."""
    script = _parse(
        RELATIONS + "relationship membership(member: User, group: User):\n"
        "    member.id == group.id\n"
        "relationship membership(owner: User, resource: User):\n"
        "    owner.id == resource.id\n"
    )
    declarations = script.relationship_templates

    diagnostics = analyze(script).diagnostics

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in diagnostics
    ] == [
        (
            "PIE-S2604",
            Severity.ERROR,
            "Ambiguous relationship predicate name: membership",
        )
    ] * 2
    for diagnostic, declaration in zip(diagnostics, declarations, strict=True):
        assert diagnostic.location.line == declaration.span.line
        assert diagnostic.location.column == declaration.span.column
        assert diagnostic.location.end_line == declaration.span.end_line
        assert diagnostic.location.end_column == declaration.span.end_column


def test_duplicate_parameter_name_reports_s2604_at_later_parameter() -> None:
    script = _parse(
        RELATIONS + "relationship membership(member: User, member: User):\n"
        "    member.id == member.id\n"
    )
    duplicate = script.relationship_templates[0].parameters[1]

    (diagnostic,) = analyze(script).diagnostics

    assert (
        diagnostic.code,
        diagnostic.severity,
        diagnostic.message,
    ) == (
        "PIE-S2604",
        Severity.ERROR,
        "Duplicate relationship parameter: member",
    )
    assert diagnostic.location.line == duplicate.span.line
    assert diagnostic.location.column == duplicate.span.column
    assert diagnostic.location.end_line == duplicate.span.end_line
    assert diagnostic.location.end_column == duplicate.span.end_column


def test_self_relationship_is_allowed_with_distinct_local_names() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship referral(referrer: User, referred: User):\n"
            "    referrer.id == referred.id\n"
        )
    )

    assert result.diagnostics == ()


def test_relationship_and_parameter_names_do_not_share_existing_namespaces() -> None:
    result = analyze(
        _parse(
            "shape shared:\n"
            "    id: Int\n"
            "derive shared(value: Int) -> Int:\n"
            "    return value\n"
            'source shared: shared = postgres.table("public.shared")\n'
            "relationship shared(shared: shared, other: shared):\n"
            "    shared.id == other.id\n"
        )
    )

    assert result.diagnostics == ()
    assert list(result.model.type_symbols) == ["shared"]
    assert list(result.model.callable_symbols) == ["shared"]
    assert list(result.model.relation_symbols) == ["shared"]


def test_relationship_metadata_stays_outside_definitions_and_relation_symbols() -> None:
    script = _parse(
        RELATIONS + "relationship membership(member: User, group: User):\n"
        "    member.id == group.id\n"
    )
    result = analyze(script)

    assert [type(definition) for definition in script.definitions] == [
        ShapeDef,
        SourceDef,
        SourceDef,
    ]
    assert [definition.name for definition in script.definitions] == [
        "User",
        "users",
        "groups",
    ]
    assert [relationship.name for relationship in script.relationship_templates] == [
        "membership"
    ]
    assert "membership" not in result.model.relation_symbols


def test_relationship_metadata_cannot_be_used_as_relation_input() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship membership(member: User, group: User):\n"
            "    member.id == group.id\n"
            "query invalid:\n"
            "    from membership\n"
            "    select:\n"
            "        id\n"
        )
    )

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2301", "Unknown relation: membership")]
    assert "membership" not in result.model.relation_symbols


def test_valid_relationship_metadata_does_not_change_semantic_ir_or_sql() -> None:
    program = (
        RELATIONS + "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query output:\n"
        "    from selected\n"
        "    select:\n"
        "        id\n"
    )
    metadata = (
        "relationship membership(member: User, group: User):\n"
        "    member.id == group.id\n"
    )
    baseline_script = _parse(program)
    metadata_script = _parse(program + metadata)
    baseline_semantic = analyze(baseline_script)
    metadata_semantic = analyze(metadata_script)

    assert baseline_semantic.diagnostics == metadata_semantic.diagnostics == ()
    assert baseline_semantic.model.type_symbols == metadata_semantic.model.type_symbols
    assert (
        baseline_semantic.model.callable_symbols
        == metadata_semantic.model.callable_symbols
    )
    assert (
        baseline_semantic.model.relation_symbols
        == metadata_semantic.model.relation_symbols
    )
    assert baseline_semantic.model.relationship_templates == ()
    assert len(metadata_semantic.model.relationship_templates) == 1
    assert isinstance(metadata_semantic.model.relation_symbols["users"], SourceDef)
    assert isinstance(metadata_semantic.model.relation_symbols["selected"], TableDef)
    assert isinstance(metadata_semantic.model.relation_symbols["output"], QueryDef)

    baseline_ir = build_ir(baseline_script, baseline_semantic.model)
    metadata_ir = build_ir(metadata_script, metadata_semantic.model)
    assert baseline_ir == metadata_ir
    assert baseline_ir.ir is not None
    assert metadata_ir.ir is not None
    assert emit_postgres_sql(baseline_ir.ir) == emit_postgres_sql(metadata_ir.ir)
    assert emit_mysql_sql(baseline_ir.ir) == emit_mysql_sql(metadata_ir.ir)


def test_program_without_relationship_metadata_keeps_semantic_behavior() -> None:
    script = _parse(
        RELATIONS + "table selected:\n    from users\n    select:\n        id\n"
    )

    checked = analyze(script)
    loose = analyze(script, mode_override=CheckMode.LOOSE)

    assert script.relationships == script.relationship_templates == ()
    assert checked.model.relationship_templates == ()
    assert loose.model.relationship_templates == ()
    assert checked.diagnostics == loose.diagnostics == ()
    assert checked.model.relation_symbols == loose.model.relation_symbols


def test_multiple_valid_relationships_may_reference_the_same_relations() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship membership(member: User, group: User):\n"
            "    member.id == group.id\n"
            "relationship ownership(owner: User, resource: User):\n"
            "    owner.id == resource.id\n"
        )
    )

    assert result.diagnostics == ()
    assert [item.declaration.name for item in result.model.relationship_templates] == [
        "membership",
        "ownership",
    ]


def _parse(source: str, *, path: Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast
