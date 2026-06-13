"""Semantic validation for relationship metadata."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import Definition, Node, Script
from pietto.errors import Diagnostic, Severity, SourceLocation


def check_relationship_metadata(
    script: Script,
    relation_symbols: Mapping[str, Definition],
) -> tuple[Diagnostic, ...]:
    """Validate relationship names, endpoints, and referenced relations."""

    diagnostics: list[Diagnostic] = []
    relationship_names: set[str] = set()

    for relationship in script.relationships:
        if relationship.name in relationship_names:
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
        for endpoint in relationship.endpoints:
            if endpoint.local_name in endpoint_names:
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

            if endpoint.relation_name not in relation_symbols:
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

    return tuple(diagnostics)


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
