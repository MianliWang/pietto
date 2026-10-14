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
    "    id: Int not null\n"
    'source users: User is postgres.table("public.users")\n'
    'source groups: User is postgres.table("public.groups")\n'
)


def test_valid_relationship_references_existing_relations() -> None:
    result = analyze(
        _parse(
            "relationship membership:\n"
            "    endpoint member: users\n"
            "    endpoint group: groups\n" + RELATIONS
        )
    )

    assert result.diagnostics == ()
    assert list(result.model.relation_symbols) == ["users", "groups"]


def test_unknown_endpoint_relation_reports_s2601_at_endpoint_span() -> None:
    path = Path("metadata/unknown-endpoint.pietto")
    script = _parse(
        RELATIONS + "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: missing\n",
        path=path,
    )
    endpoint = script.relationships[0].endpoints[1]

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in analyze(script).diagnostics
    ] == [
        (
            "PIE-S2601",
            Severity.ERROR,
            "Unknown relationship endpoint relation: missing",
        )
    ]
    diagnostic = analyze(script).diagnostics[0]
    assert diagnostic.location.path == endpoint.span.path
    assert diagnostic.location.line == endpoint.span.line
    assert diagnostic.location.column == endpoint.span.column
    assert diagnostic.location.end_line == endpoint.span.end_line
    assert diagnostic.location.end_column == endpoint.span.end_column


def test_duplicate_relationship_name_reports_s2602_at_later_declaration() -> None:
    script = _parse(
        RELATIONS + "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: groups\n"
        "relationship membership:\n"
        "    endpoint owner: users\n"
        "    endpoint resource: groups\n"
    )
    duplicate = script.relationships[1]

    diagnostic = analyze(script).diagnostics[0]

    assert (
        diagnostic.code,
        diagnostic.severity,
        diagnostic.message,
    ) == (
        "PIE-S2602",
        Severity.ERROR,
        "Duplicate relationship metadata name: membership",
    )
    assert diagnostic.location.line == duplicate.span.line
    assert diagnostic.location.column == duplicate.span.column
    assert diagnostic.location.end_line == duplicate.span.end_line
    assert diagnostic.location.end_column == duplicate.span.end_column


def test_duplicate_endpoint_local_name_reports_s2603_at_later_endpoint() -> None:
    script = _parse(
        RELATIONS + "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint member: groups\n"
    )
    duplicate = script.relationships[0].endpoints[1]

    diagnostic = analyze(script).diagnostics[0]

    assert (
        diagnostic.code,
        diagnostic.severity,
        diagnostic.message,
    ) == (
        "PIE-S2603",
        Severity.ERROR,
        "Duplicate endpoint local name in relationship membership: member",
    )
    assert diagnostic.location.line == duplicate.span.line
    assert diagnostic.location.column == duplicate.span.column
    assert diagnostic.location.end_line == duplicate.span.end_line
    assert diagnostic.location.end_column == duplicate.span.end_column


def test_self_relationship_is_allowed_with_distinct_local_names() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship referral:\n"
            "    endpoint referrer: users\n"
            "    endpoint referred: users\n"
        )
    )

    assert result.diagnostics == ()


def test_relationship_and_endpoint_names_do_not_share_existing_namespaces() -> None:
    result = analyze(
        _parse(
            "shape shared:\n"
            "    id: Int not null\n"
            "derive shared(value: Int not null) -> Int not null:\n"
            "    value\n"
            'source shared: shared is postgres.table("public.shared")\n'
            "relationship shared:\n"
            "    endpoint shared: shared\n"
            "    endpoint other: shared\n"
        )
    )

    assert result.diagnostics == ()
    assert list(result.model.type_symbols) == ["shared"]
    assert list(result.model.callable_symbols) == ["shared"]
    assert list(result.model.relation_symbols) == ["shared"]


def test_relationship_metadata_stays_outside_definitions_and_relation_symbols() -> None:
    script = _parse(
        RELATIONS + "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: groups\n"
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
    assert [relationship.name for relationship in script.relationships] == [
        "membership"
    ]
    assert "membership" not in result.model.relation_symbols


def test_relationship_metadata_cannot_be_used_as_relation_input() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship membership:\n"
            "    endpoint member: users\n"
            "    endpoint group: groups\n"
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
        "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: groups\n"
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
    assert baseline_semantic.model.relationships == ()
    assert len(metadata_semantic.model.relationships) == 1
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

    assert script.relationships == ()
    assert checked.model.relationships == loose.model.relationships == ()
    assert checked.diagnostics == loose.diagnostics == ()
    assert checked.model.relation_symbols == loose.model.relation_symbols


def test_multiple_valid_relationships_may_reference_the_same_relations() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship membership:\n"
            "    endpoint member: users\n"
            "    endpoint group: groups\n"
            "relationship ownership:\n"
            "    endpoint owner: users\n"
            "    endpoint resource: groups\n"
        )
    )

    assert result.diagnostics == ()


def _parse(source: str, *, path: Path | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast
