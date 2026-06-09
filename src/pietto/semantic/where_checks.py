"""Boolean consumer validation for table and query where clauses."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import ValueType, ValueTypeKind


def check_where_clauses(
    script: Script,
    expression_value_types: Mapping[Expression, ValueType],
) -> list[Diagnostic]:
    """Require known table and query where expressions to have type Bool."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        where_clause = definition.where_clause
        if where_clause is None:
            continue

        value_type = expression_value_types.get(where_clause.expression)
        if value_type is None or value_type.kind is ValueTypeKind.UNKNOWN:
            continue
        if value_type.resolved_type.name == "Bool":
            continue

        diagnostics.append(_non_bool_where_diagnostic(where_clause.expression))

    return diagnostics


def _non_bool_where_diagnostic(expression: Expression) -> Diagnostic:
    """Report a known non-Bool where expression at its expression span."""

    span = expression.span
    return Diagnostic(
        code="PIE-S2202",
        severity=Severity.ERROR,
        message="Expected Bool expression in where clause",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
