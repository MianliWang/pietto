"""Semantic validation for relationship metadata."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    Definition,
    Node,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import (
    RelationshipSemanticEndpointInfo,
    RelationshipSemanticInfo,
)


def check_relationship_metadata(
    script: Script,
    relation_symbols: Mapping[str, Definition],
) -> tuple[tuple[RelationshipSemanticInfo, ...], tuple[Diagnostic, ...]]:
    """Validate relationship metadata and build readonly semantic facts."""

    relationships: list[RelationshipSemanticInfo] = []
    diagnostics: list[Diagnostic] = []
    relationship_names: set[str] = set()

    for relationship in script.relationships:
        is_valid = True
        if relationship.name in relationship_names:
            is_valid = False
            diagnostics.append(
                _diagnostic(
                    relationship,
                    code="PIE-S2602",
                    message=(
                        f"Duplicate relationship metadata name: {relationship.name}"
                    ),
                )
            )
        else:
            relationship_names.add(relationship.name)

        endpoint_names: set[str] = set()
        endpoints: list[RelationshipSemanticEndpointInfo] = []
        for endpoint in relationship.endpoints:
            if endpoint.local_name in endpoint_names:
                is_valid = False
                diagnostics.append(
                    _diagnostic(
                        endpoint,
                        code="PIE-S2603",
                        message=(
                            "Duplicate endpoint local name in relationship "
                            f"{relationship.name}: {endpoint.local_name}"
                        ),
                    )
                )
            else:
                endpoint_names.add(endpoint.local_name)

            relation = relation_symbols.get(endpoint.relation_name)
            if not isinstance(relation, (SourceDef, TableDef, QueryDef)):
                is_valid = False
                diagnostics.append(
                    _diagnostic(
                        endpoint,
                        code="PIE-S2601",
                        message=(
                            "Unknown relationship endpoint relation: "
                            f"{endpoint.relation_name}"
                        ),
                    )
                )
                continue
            endpoints.append(
                RelationshipSemanticEndpointInfo(
                    local_name=endpoint.local_name,
                    relation_name=endpoint.relation_name,
                    relation=relation,
                )
            )

        if is_valid:
            assert len(endpoints) == 2
            relationships.append(
                RelationshipSemanticInfo(
                    name=relationship.name,
                    endpoints=(endpoints[0], endpoints[1]),
                )
            )

    return tuple(relationships), tuple(diagnostics)


def _diagnostic(node: Node, *, code: str, message: str) -> Diagnostic:
    """Create an error diagnostic at a complete metadata node span."""

    span = node.span
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
