"""Boolean consumer validation for supported predicate contexts."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    CheckDef,
    Expression,
    IndexDef,
    QueryDef,
    Script,
    ShapeDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import ValueType, ValueTypeKind


def check_predicates(
    script: Script,
    expression_value_types: Mapping[Expression, ValueType],
) -> list[Diagnostic]:
    """Require known where, shape check, and index predicates to be Bool."""

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if isinstance(definition, (TableDef, QueryDef)):
            if definition.where_clause is not None:
                diagnostic = _check_bool_expression(
                    definition.where_clause.expression,
                    context="where clause",
                    expression_value_types=expression_value_types,
                )
                if diagnostic is not None:
                    diagnostics.append(diagnostic)
        elif isinstance(definition, ShapeDef):
            for item in definition.items:
                expression: Expression | None = None
                context = ""
                if isinstance(item, CheckDef):
                    expression = item.expression
                    context = "shape check"
                elif isinstance(item, IndexDef) and item.predicate is not None:
                    expression = item.predicate
                    context = "index predicate"

                if expression is not None:
                    diagnostic = _check_bool_expression(
                        expression,
                        context=context,
                        expression_value_types=expression_value_types,
                    )
                    if diagnostic is not None:
                        diagnostics.append(diagnostic)

    return diagnostics


def _check_bool_expression(
    expression: Expression,
    *,
    context: str,
    expression_value_types: Mapping[Expression, ValueType],
) -> Diagnostic | None:
    """Return a diagnostic when a predicate has a known non-Bool type."""

    value_type = expression_value_types.get(expression)
    if value_type is None or value_type.kind is ValueTypeKind.UNKNOWN:
        return None
    if value_type.resolved_type.name == "Bool":
        return None

    span = expression.span
    return Diagnostic(
        code="PIE-S2202",
        severity=Severity.ERROR,
        message=f"Expected Bool expression in {context}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
