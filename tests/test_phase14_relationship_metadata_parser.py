from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from pietto.ast_nodes import (
    RelationshipEndpoint,
    RelationshipMetadata,
    Script,
    ShapeDef,
    SourceDef,
    Span,
    TableDef,
)
from pietto.errors import Severity
from pietto.ir import ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql


def test_minimal_relationship_metadata_preserves_names_order_and_spans() -> None:
    path = Path("metadata/relationships.pietto")
    result = parse_source(
        "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: groups\n",
        path=path,
    )

    assert result.diagnostics == ()
    assert isinstance(result.ast, Script)
    assert result.ast.definitions == ()
    assert len(result.ast.relationships) == 1

    relationship = result.ast.relationships[0]
    assert relationship == RelationshipMetadata(
        span=Span(
            path=str(path),
            line=1,
            column=1,
            end_line=3,
            end_column=27,
        ),
        name="membership",
        endpoints=(
            RelationshipEndpoint(
                span=Span(
                    path=str(path),
                    line=2,
                    column=5,
                    end_line=2,
                    end_column=27,
                ),
                local_name="member",
                relation_name="users",
            ),
            RelationshipEndpoint(
                span=Span(
                    path=str(path),
                    line=3,
                    column=5,
                    end_line=3,
                    end_column=27,
                ),
                local_name="group",
                relation_name="groups",
            ),
        ),
    )


def test_multiple_relationship_declarations_preserve_source_order() -> None:
    result = parse_source(
        "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: groups\n"
        "\n"
        "relationship ownership:\n"
        "    endpoint owner: users\n"
        "    endpoint resource: accounts\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [relationship.name for relationship in result.ast.relationships] == [
        "membership",
        "ownership",
    ]
    assert [
        endpoint.local_name
        for relationship in result.ast.relationships
        for endpoint in relationship.endpoints
    ] == ["member", "group", "owner", "resource"]


def test_relationship_and_endpoint_are_contextual_identifiers() -> None:
    result = parse_source(
        "type relationship = Int\n"
        "shape endpoint:\n"
        "    relationship: relationship\n"
        'source endpoint: endpoint is postgres.table("endpoint")\n'
        "relationship endpoint:\n"
        "    endpoint relationship: endpoint\n"
        "    endpoint endpoint: relationship\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert [definition.name for definition in result.ast.definitions] == [
        "relationship",
        "endpoint",
        "endpoint",
    ]
    relationship = result.ast.relationships[0]
    assert relationship.name == "endpoint"
    assert [
        (endpoint.local_name, endpoint.relation_name)
        for endpoint in relationship.endpoints
    ] == [
        ("relationship", "endpoint"),
        ("endpoint", "relationship"),
    ]


def test_script_without_relationship_metadata_keeps_empty_collection() -> None:
    result = parse_source(
        "shape User:\n"
        "    id: Int not null\n"
        'source users: User is postgres.table("public.users")\n'
        "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
    )

    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.relationships == ()
    assert [type(definition) for definition in result.ast.definitions] == [
        ShapeDef,
        SourceDef,
        TableDef,
    ]


@pytest.mark.parametrize(
    "source",
    [
        "relationship missing:\n",
        "relationship one:\n    endpoint only: users\n",
        (
            "relationship three:\n"
            "    endpoint first: users\n"
            "    endpoint second: groups\n"
            "    endpoint third: accounts\n"
        ),
        "endpoint stray: users\n",
        (
            "relationship missing_name:\n"
            "    endpoint : users\n"
            "    endpoint second: groups\n"
        ),
        (
            "relationship missing_relation:\n"
            "    endpoint first:\n"
            "    endpoint second: groups\n"
        ),
        (
            "relationship missing_colon\n"
            "    endpoint first: users\n"
            "    endpoint second: groups\n"
        ),
        (
            "relationship braces {\n"
            "    endpoint first: users\n"
            "    endpoint second: groups\n"
            "}\n"
        ),
    ],
)
def test_malformed_relationship_metadata_uses_existing_parser_failure(
    source: str,
) -> None:
    result = parse_source(source, path="malformed.pietto")

    assert result.ast is None
    assert result.diagnostics
    assert all(
        diagnostic.code in {"PIE-P1000", "PIE-P1005"}
        and diagnostic.severity is Severity.ERROR
        and diagnostic.location.path == "malformed.pietto"
        for diagnostic in result.diagnostics
    )


def test_relationship_metadata_is_immutable() -> None:
    result = parse_source(
        "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: groups\n"
    )

    assert result.ast is not None
    relationship = result.ast.relationships[0]
    with pytest.raises(FrozenInstanceError):
        relationship.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        relationship.endpoints[0].local_name = "changed"  # type: ignore[misc]


def test_relationship_metadata_does_not_change_semantic_ir_or_sql() -> None:
    program = (
        "shape User:\n"
        "    id: Int not null\n"
        'source users: User is postgres.table("public.users")\n'
        "table selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
    )
    metadata = (
        "relationship membership:\n"
        "    endpoint member: users\n"
        "    endpoint group: users\n"
    )

    baseline_parse = parse_source(program)
    metadata_parse = parse_source(program + metadata)
    assert baseline_parse.diagnostics == metadata_parse.diagnostics == ()
    assert baseline_parse.ast is not None
    assert metadata_parse.ast is not None
    assert baseline_parse.ast.definitions == metadata_parse.ast.definitions
    assert metadata_parse.ast.relationships

    baseline_semantic = analyze(baseline_parse.ast)
    metadata_semantic = analyze(metadata_parse.ast)
    assert baseline_semantic == metadata_semantic
    assert "membership" not in metadata_semantic.model.type_symbols
    assert "membership" not in metadata_semantic.model.callable_symbols
    assert "membership" not in metadata_semantic.model.relation_symbols

    baseline_ir = build_ir(baseline_parse.ast, baseline_semantic.model)
    metadata_ir = build_ir(metadata_parse.ast, metadata_semantic.model)
    assert baseline_ir == metadata_ir
    assert isinstance(baseline_ir.ir, ScriptIR)
    assert isinstance(metadata_ir.ir, ScriptIR)
    assert emit_postgres_sql(baseline_ir.ir) == emit_postgres_sql(metadata_ir.ir)
    assert emit_mysql_sql(baseline_ir.ir) == emit_mysql_sql(metadata_ir.ir)
