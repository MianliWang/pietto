"""Compare parsed programs apart from their source positions."""

from __future__ import annotations

from dataclasses import fields, is_dataclass, replace

from pietto.ast_nodes import OrderItem, Span


def layout_free(value: object, *, ascending: bool = False) -> object:
    """An AST value as nested tuples with every source span removed.

    Two layouts of one program give equal results exactly when they build the
    same AST apart from where its nodes sit in the source. With ``ascending``,
    an order item's explicit `asc` reads as the omitted direction, which
    `pietto fmt` writes.
    """

    if type(value) is Span:
        return None
    if type(value) is tuple:
        return tuple(layout_free(item, ascending=ascending) for item in value)
    if ascending and type(value) is OrderItem and value.direction == "asc":
        value = replace(value, direction=None)
    if is_dataclass(value) and not isinstance(value, type):
        return (
            type(value).__name__,
            tuple(
                (item.name, layout_free(getattr(value, item.name), ascending=ascending))
                for item in fields(value)
            ),
        )
    return value
