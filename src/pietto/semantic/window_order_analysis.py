"""Private direct-field binding for structural window-local order tuples."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    NameExpr,
    OrderItem,
)
from pietto.errors import Diagnostic
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import RowSchema, TypeKind, ValueType, ValueTypeKind
from pietto.semantic.window_semantics import WindowOrderFieldBinding

__all__: tuple[str, ...] = ()


def bind_window_order_fields(
    *,
    order_items: tuple[OrderItem, ...],
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    diagnostics: list[Diagnostic],
    bare_value_types: Mapping[str, ValueType] | None = None,
    allow_qualified_fields: bool = True,
) -> tuple[WindowOrderFieldBinding, ...] | None:
    """Resolve all direct order fields before validating their directions."""

    if type(order_items) is not tuple:
        raise TypeError("order_items must be an exact tuple")
    if not order_items:
        raise ValueError("order_items must be nonempty")
    if any(type(item) is not OrderItem for item in order_items):
        raise TypeError("order_items must contain exact OrderItem instances")
    if any(
        type(item.expression) not in {NameExpr, DottedNameExpr} for item in order_items
    ):
        raise TypeError(
            "order item expressions must be exact NameExpr or DottedNameExpr"
        )
    if type(input_schema) is not RowSchema:
        raise TypeError("input_schema must be an exact RowSchema")
    if type(field_qualifier) is not str:
        raise TypeError("field_qualifier must be an exact string")
    if type(value_types) is not dict:
        raise TypeError("value_types must be an exact dict")
    if type(diagnostics) is not list:
        raise TypeError("diagnostics must be an exact list")

    resolved: list[tuple[OrderItem, ValueType]] = []
    for item in order_items:
        value_type = infer_row_expression(
            item.expression,
            input_schema,
            value_types,
            diagnostics,
            report_unknown_name=True,
            field_qualifier=field_qualifier if allow_qualified_fields else "",
            bare_value_types=bare_value_types,
        )
        if (
            value_type.kind is ValueTypeKind.UNKNOWN
            or value_type.resolved_type.kind is TypeKind.UNKNOWN
        ):
            return None
        resolved.append((item, value_type))

    for item, _ in resolved:
        direction = item.direction
        if direction is not None and (
            type(direction) is not str or direction not in ("asc", "desc")
        ):
            return None

    return tuple(
        WindowOrderFieldBinding(
            order_item=item,
            value_type=value_type,
            effective_direction="asc" if item.direction is None else item.direction,
        )
        for item, value_type in resolved
    )
