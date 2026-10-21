"""Boolean consumer validation for supported predicate contexts."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import Expression, TypeExpr
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.expressions import (
    _canonical_value_type,
    condition_value_type,
    is_unknown_number,
)
from pietto.semantic.model import ResolvedType, RowSchema, ValueType, ValueTypeKind


def _check_bool_expression(
    expression: Expression,
    *,
    context: str,
    expression_value_types: Mapping[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType] | None = None,
    explained: bool = True,
    row_schema: RowSchema | None = None,
    lets: Mapping[str, Expression] | None = None,
) -> Diagnostic | None:
    """Return a diagnostic when a predicate has a known non-Bool type, or,
    where no error explains its unknown type (``explained``, see
    `unknown_explained`), when it is a built-in call whose signature fixes a
    type that is not Bool (`condition_value_type`), also as the value of a
    `let:` name of ``lets``, or a number of unknown type such as a quotient
    with a `Decimal` operand (`is_unknown_number`)."""

    value_type = expression_value_types.get(expression)
    if value_type is None:
        return None
    if not explained:
        value_type = condition_value_type(expression, value_type, row_schema, lets)
    if value_type.kind is ValueTypeKind.UNKNOWN:
        if explained or not is_unknown_number(value_type):
            return None
    elif (
        _canonical_value_type(value_type, type_expansions).resolved_type.name == "Bool"
    ):
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
