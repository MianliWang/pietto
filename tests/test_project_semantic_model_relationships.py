from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from pietto.ast_nodes import QueryDef, Script, SourceDef, TableDef
from pietto.parser_api import parse_source
from pietto.semantic import analyze

RELATIONS = (
    "shape Row:\n"
    "    id: Int not null\n"
    'source users: Row is postgres.table("public.users")\n'
    "table groups:\n"
    "    from users\n"
    "    select:\n"
    "        id\n"
    "query accounts:\n"
    "    from groups\n"
    "    select:\n"
    "        id\n"
)


def test_valid_relationship_is_stored_in_semantic_model() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship membership:\n"
            "    endpoint member: users\n"
            "    endpoint group: groups\n"
        )
    )

    assert result.diagnostics == ()
    assert [relationship.name for relationship in result.model.relationships] == [
        "membership"
    ]
    assert [
        (endpoint.local_name, endpoint.relation_name)
        for endpoint in result.model.relationships[0].endpoints
    ] == [("member", "users"), ("group", "groups")]


def test_relationship_and_endpoint_source_order_are_preserved() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship membership:\n"
            "    endpoint member: users\n"
            "    endpoint group: groups\n"
            "relationship ownership:\n"
            "    endpoint resource: accounts\n"
            "    endpoint owner: users\n"
        )
    )

    assert [relationship.name for relationship in result.model.relationships] == [
        "membership",
        "ownership",
    ]
    assert [
        endpoint.local_name
        for relationship in result.model.relationships
        for endpoint in relationship.endpoints
    ] == ["member", "group", "resource", "owner"]


def test_endpoints_resolve_to_existing_source_table_and_query_symbols() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship source_table:\n"
            "    endpoint source_side: users\n"
            "    endpoint table_side: groups\n"
            "relationship table_query:\n"
            "    endpoint table_side: groups\n"
            "    endpoint query_side: accounts\n"
        )
    )

    source_table, table_query = result.model.relationships
    assert isinstance(source_table.endpoints[0].relation, SourceDef)
    assert isinstance(source_table.endpoints[1].relation, TableDef)
    assert isinstance(table_query.endpoints[1].relation, QueryDef)
    for relationship in result.model.relationships:
        for endpoint in relationship.endpoints:
            assert (
                endpoint.relation
                is result.model.relation_symbols[endpoint.relation_name]
            )


def test_self_relationship_resolves_both_endpoints_to_same_relation() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship referral:\n"
            "    endpoint referrer: users\n"
            "    endpoint referred: users\n"
        )
    )

    first, second = result.model.relationships[0].endpoints
    assert first.local_name == "referrer"
    assert second.local_name == "referred"
    assert first.relation is second.relation
    assert first.relation is result.model.relation_symbols["users"]


def test_multiple_relationships_may_share_resolved_relations() -> None:
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

    membership, ownership = result.model.relationships
    assert membership.endpoints[0].relation is ownership.endpoints[0].relation
    assert membership.endpoints[1].relation is ownership.endpoints[1].relation


def test_relationship_semantic_facts_are_immutable() -> None:
    result = analyze(
        _parse(
            RELATIONS + "relationship membership:\n"
            "    endpoint member: users\n"
            "    endpoint group: groups\n"
        )
    )
    relationship = result.model.relationships[0]

    with pytest.raises(FrozenInstanceError):
        relationship.name = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        relationship.endpoints[0].local_name = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("relationship_source", "expected_code"),
    [
        (
            "relationship invalid:\n"
            "    endpoint known: users\n"
            "    endpoint missing: missing\n",
            "PIE-S2601",
        ),
        (
            "relationship duplicate:\n"
            "    endpoint first: users\n"
            "    endpoint second: groups\n"
            "relationship duplicate:\n"
            "    endpoint third: users\n"
            "    endpoint fourth: groups\n",
            "PIE-S2602",
        ),
        (
            "relationship invalid:\n"
            "    endpoint repeated: users\n"
            "    endpoint repeated: groups\n",
            "PIE-S2603",
        ),
    ],
)
def test_invalid_relationships_are_not_stored(
    relationship_source: str,
    expected_code: str,
) -> None:
    result = analyze(_parse(RELATIONS + relationship_source))

    assert [diagnostic.code for diagnostic in result.diagnostics] == [expected_code]
    if expected_code == "PIE-S2602":
        assert [relationship.name for relationship in result.model.relationships] == [
            "duplicate"
        ]
    else:
        assert result.model.relationships == ()


def test_program_without_relationship_metadata_has_empty_semantic_tuple() -> None:
    result = analyze(_parse(RELATIONS))

    assert result.diagnostics == ()
    assert result.model.relationships == ()


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast
