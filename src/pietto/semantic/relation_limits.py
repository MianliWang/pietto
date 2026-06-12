"""Semantic validation for static relation limits."""

from __future__ import annotations

from pietto.ast_nodes import LiteralExpr, QueryDef, Script, TableDef
from pietto.errors import Diagnostic, Severity, SourceLocation

MAX_RELATION_LIMIT = 9_223_372_036_854_775_807
_INVALID_LIMIT_MESSAGE = "Limit must be a static integer from 0 to 9223372036854775807"


def check_relation_limits(script: Script) -> tuple[Diagnostic, ...]:
    """Validate limit operands without invoking general expression resolution."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        clause = definition.limit_clause
        if clause is None or _is_valid_limit(clause.expression):
            continue
        span = clause.expression.span
        diagnostics.append(
            Diagnostic(
                code="PIE-S2307",
                severity=Severity.ERROR,
                message=_INVALID_LIMIT_MESSAGE,
                location=SourceLocation(
                    path=span.path,
                    line=span.line,
                    column=span.column,
                    end_line=span.end_line,
                    end_column=span.end_column,
                ),
            )
        )
    return tuple(diagnostics)


def _is_valid_limit(expression: object) -> bool:
    if not isinstance(expression, LiteralExpr):
        return False
    value = expression.value
    return type(value) is int and 0 <= value <= MAX_RELATION_LIMIT
