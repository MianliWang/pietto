"""Private syntax availability shared by existing compiler entrypoints."""

from __future__ import annotations

from pietto import ast_nodes as ast
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

_KNOWN_DEFINITIONS = frozenset(
    {
        ast.TypeDef,
        ast.EnumDef,
        ast.ShapeDef,
        ast.ConstraintDef,
        ast.DeriveDef,
        ast.SourceDef,
        ast.TableDef,
        ast.QueryDef,
        ast.SetRelationDef,
    }
)


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


def syntax_diagnostics(
    definition: Definition, *, allow_distinct: bool = False
) -> tuple[Diagnostic, ...]:
    if type(definition) not in _KNOWN_DEFINITIONS:
        return (
            availability_diagnostic(
                definition.span, "Definition semantics are not implemented."
            ),
        )
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
    if definition.distinct_clause is not None and not allow_distinct:
        diagnostics.append(
            availability_diagnostic(
                definition.distinct_clause.span,
                "Relational DISTINCT requires explicit-module completed semantics.",
            )
        )
    return tuple(diagnostics)
