"""Fail-closed semantic gate for parsed GROUP BY clauses."""

from __future__ import annotations

from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.errors import Diagnostic, Severity, SourceLocation

GROUP_BY_DEFERRED_CODE = "PIE-S2316"
GROUP_BY_DEFERRED_MESSAGE = "GROUP BY is parsed but semantic implementation is deferred"


def check_group_by_deferred(script: Script) -> list[Diagnostic]:
    """Reject parsed GROUP BY relations until grouped semantics are implemented."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        clause = definition.group_by_clause
        if clause is None:
            continue
        span = clause.span
        diagnostics.append(
            Diagnostic(
                code=GROUP_BY_DEFERRED_CODE,
                severity=Severity.ERROR,
                message=GROUP_BY_DEFERRED_MESSAGE,
                location=SourceLocation(
                    path=span.path,
                    line=span.line,
                    column=span.column,
                    end_line=span.end_line,
                    end_column=span.end_column,
                ),
            )
        )
    return diagnostics
