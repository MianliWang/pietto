"""Resolve unshadowed scalar constructor spellings to existing cast nodes."""

from __future__ import annotations

from collections.abc import Callable
from typing import cast

from pietto import ast_nodes as ast
from pietto.errors import Diagnostic

__all__: tuple[str, ...] = ()


def normalize_float_calls(
    script: ast.Script,
    *,
    occurrence_observer: Callable[[object, object], None] | None = None,
) -> tuple[ast.Script, tuple[Diagnostic, ...]]:
    """Preserve authored callable meanings before recognizing a constructor."""

    from pietto.semantic.inline_functions import (
        _diagnostic,
        _ordered,
        _rebuild,
        _tree_nodes,
    )

    constructors = frozenset({"Float", "Text"})
    shadowed = frozenset(
        item.name
        for item in script.definitions
        if type(item) in (ast.FunctionDef, ast.ConstraintDef, ast.DeriveDef)
        and item.name in constructors
    ) | frozenset(
        item.name for item in script.relationship_templates if item.name in constructors
    )
    diagnostics: list[Diagnostic] = []
    # A window's or a table function's own call stays a call, whose reader
    # checks its name: `Float(x) window(...)` is an unknown window function,
    # as `Int(x) window(...)` is.
    calls = frozenset(
        id(node.call)
        for node in _tree_nodes(script)
        if isinstance(node, (ast.WindowExpr, ast.TableFunctionFromClause))
    )

    def normalize(original: object, rebuilt: object) -> object:
        if (
            id(original) not in calls
            and type(rebuilt) is ast.CallExpr
            and type(rebuilt.callee) is ast.NameExpr
            and rebuilt.callee.name in constructors - shadowed
        ):
            if rebuilt.aggregate_order_by:
                diagnostics.append(
                    _diagnostic(
                        "PIE-S2104",
                        "Internal ORDER BY is only supported by string_agg",
                        rebuilt.span,
                    )
                )
                return rebuilt
            if len(rebuilt.arguments) != 1:
                diagnostics.append(
                    _diagnostic(
                        "PIE-S2104",
                        f"Invalid arguments for constructor {rebuilt.callee.name}: expected 1, "
                        f"got {len(rebuilt.arguments)}",
                        rebuilt.span,
                    )
                )
            else:
                rebuilt = ast.CastExpr(
                    span=rebuilt.span,
                    value=rebuilt.arguments[0],
                    target=ast.TypeExpr(
                        span=rebuilt.callee.span,
                        name=rebuilt.callee.name,
                        arguments=(),
                        nullability=ast.Nullability.IMPLICIT,
                    ),
                )
        if (
            rebuilt is not original
            and isinstance(original, ast.Expression)
            and isinstance(rebuilt, ast.Expression)
        ):
            for slot in ast.inlined_arguments(original):
                rebuilt = ast.with_inlined_argument(rebuilt, slot)
        return rebuilt

    normalized = cast(
        ast.Script, _rebuild(script, normalize, occurrence_observer=occurrence_observer)
    )
    return normalized, _ordered(diagnostics)
