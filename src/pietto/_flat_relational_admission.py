"""Private syntax availability shared by existing compiler entrypoints."""

from __future__ import annotations

from pietto.ast_nodes import (
    AuthoredJoinKind,
    Definition,
    JoinClause,
    QueryDef,
    SetRelationDef,
    Span,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()


def unsupported_join(clause: JoinClause) -> bool:
    return clause.on_clause is not None or clause.kind not in {
        AuthoredJoinKind.INNER,
        AuthoredJoinKind.LEFT,
    }


def availability_diagnostic(span: Span, message: str) -> Diagnostic:
    return Diagnostic(
        code="PIE-S2334",
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


def syntax_diagnostics(definition: Definition) -> tuple[Diagnostic, ...]:
    if isinstance(definition, SetRelationDef):
        return (
            availability_diagnostic(
                definition.body.operator_span,
                "Set-operation semantics are not implemented.",
            ),
        )
    if not isinstance(definition, (TableDef, QueryDef)):
        return ()
    diagnostics = []
    for clause in definition.join_clauses:
        if clause.kind not in {AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT}:
            diagnostics.append(
                availability_diagnostic(
                    clause.span,
                    f"{clause.kind.value.upper()} JOIN semantics are not implemented.",
                )
            )
        if clause.on_clause is not None:
            diagnostics.append(
                availability_diagnostic(
                    clause.on_clause.span,
                    "JOIN-local ON semantics are not implemented.",
                )
            )
    return tuple(diagnostics)
