"""Private direct-field binding for structural window partition tuples."""

from __future__ import annotations

from pietto.ast_nodes import DottedNameExpr, Expression, NameExpr
from pietto.errors import Diagnostic
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import RowSchema, TypeKind, ValueType, ValueTypeKind
from pietto.semantic.window_semantics import WindowPartitionFieldBinding

__all__: tuple[str, ...] = ()


def bind_window_partition_fields(
    *,
    partition_expressions: tuple[NameExpr | DottedNameExpr, ...],
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
) -> tuple[WindowPartitionFieldBinding, ...] | None:
    """Resolve direct partition fields once each and preserve source order."""

    if type(partition_expressions) is not tuple:
        raise TypeError("partition_expressions must be an exact tuple")
    if any(
        type(expression) not in {NameExpr, DottedNameExpr}
        for expression in partition_expressions
    ):
        raise TypeError(
            "partition_expressions must contain exact NameExpr or DottedNameExpr"
        )
    if type(input_schema) is not RowSchema:
        raise TypeError("input_schema must be an exact RowSchema")
    if type(field_qualifier) is not str:
        raise TypeError("field_qualifier must be an exact string")
    if type(value_types) is not dict:
        raise TypeError("value_types must be an exact dict")
    if type(diagnostics) is not list:
        raise TypeError("diagnostics must be an exact list")

    bindings: list[WindowPartitionFieldBinding] = []
    for expression in partition_expressions:
        value_type = infer_row_expression(
            expression,
            input_schema,
            value_types,
            diagnostics,
            report_unknown_name=True,
            field_qualifier=field_qualifier,
        )
        if (
            value_type.kind is ValueTypeKind.UNKNOWN
            or value_type.resolved_type.kind is TypeKind.UNKNOWN
        ):
            return None
        bindings.append(
            WindowPartitionFieldBinding(
                expression=expression,
                value_type=value_type,
            )
        )
    return tuple(bindings)
