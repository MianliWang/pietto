"""Relation input resolution for table and query definitions."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    Definition,
    FromClause,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

RelationDefinition = SourceDef | TableDef | QueryDef


def resolve_relation_inputs(
    script: Script,
    relation_symbols: Mapping[str, Definition],
) -> tuple[dict[FromClause, RelationDefinition], list[Diagnostic]]:
    """Resolve table and query from clauses against collected relations."""

    resolutions: dict[FromClause, RelationDefinition] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue

        from_clause = definition.from_clause
        target = relation_symbols.get(from_clause.source_name)
        if isinstance(target, (SourceDef, TableDef, QueryDef)):
            resolutions[from_clause] = target
        else:
            diagnostics.append(_unknown_relation_diagnostic(from_clause))

    return resolutions, diagnostics


def _unknown_relation_diagnostic(from_clause: FromClause) -> Diagnostic:
    """Report an unresolved relation at the complete from-clause span."""

    span = from_clause.span
    return Diagnostic(
        code="P2301",
        severity=Severity.ERROR,
        message=f"Unknown relation: {from_clause.source_name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
