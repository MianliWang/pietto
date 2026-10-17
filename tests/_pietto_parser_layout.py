"""Compare parsed programs apart from their source positions."""

from __future__ import annotations

from dataclasses import fields, is_dataclass

from pietto.ast_nodes import Span


def layout_free(value: object) -> object:
    """An AST value as nested tuples with every source span removed.

    Two layouts of one program give equal results exactly when they build the
    same AST apart from where its nodes sit in the source.
    """

    if type(value) is Span:
        return None
    if type(value) is tuple:
        return tuple(layout_free(item) for item in value)
    if is_dataclass(value) and not isinstance(value, type):
        return (
            type(value).__name__,
            tuple(
                (item.name, layout_free(getattr(value, item.name)))
                for item in fields(value)
            ),
        )
    return value
