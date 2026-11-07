"""Resolve unshadowed scalar constructor spellings to existing cast nodes,
and two-argument `max` and `min` calls to the conditionals they mean."""

from __future__ import annotations

import itertools
from collections.abc import Callable
from dataclasses import replace
from typing import cast

from pietto import ast_nodes as ast
from pietto._builtin_shadows import (
    builtin_shadows as builtin_shadows,
    in_concat_file as in_concat_file,
    shadowed_builtin_names as shadowed_builtin_names,
)
from pietto.errors import Diagnostic
from pietto.semantic.aggregates import INTERNAL_ORDER_ONLY

__all__: tuple[str, ...] = ()

# `max(a, b)` is `(b if a < b else a) if b is not None else b`, and `min(a, b)`
# the same with `>`: Python's larger or smaller of two values, the first on a
# tie, and None when either is None, which PostgreSQL GREATEST and LEAST are
# not. Without the test of `b`, a None `b` would give `a`. The test is left out
# when `b` is a literal other than None.
_EXTREMA = {"max": "<", "min": ">"}


def normalize_float_calls(
    script: ast.Script,
    *,
    occurrence_observer: Callable[[object, object], None] | None = None,
) -> tuple[ast.Script, tuple[Diagnostic, ...]]:
    """Preserve authored callable meanings before recognizing a constructor."""

    from pietto.semantic.inline_functions import (
        _MAX_EXPANSION_DEPTH,
        _MAX_EXPANSION_NODES,
        _diagnostic,
        _last_occurrence,
        _measure,
        _ordered,
        _rebuild,
        _size_diagnostic,
        _tree_nodes,
    )

    constructors = frozenset({"Float", "Text"})
    shadowed = shadowed_builtin_names(script)
    diagnostics: list[Diagnostic] = []
    # A window's or a table function's own call stays a call, whose reader
    # checks its name: `Float(x) window(...)` is an unknown window function,
    # as `Int(x) window(...)` is.
    calls = frozenset(
        id(node.call)
        for node in _tree_nodes(script)
        if isinstance(node, (ast.WindowExpr, ast.TableFunctionFromClause))
    )

    # Above every occurrence the script holds, so each copy is a new node.
    occurrences = itertools.count(1 + _last_occurrence(script))

    def copy(node: ast.Expression) -> ast.Expression:
        """``node`` again, as the same text written out once more."""

        def copied(original: object, rebuilt: object) -> object:
            if not isinstance(rebuilt, ast.Node):
                return rebuilt
            return replace(
                rebuilt, span=replace(rebuilt.span, occurrence=next(occurrences))
            )

        return cast(
            ast.Expression,
            _rebuild(node, copied, occurrence_observer=occurrence_observer),
        )

    def extremum(call: ast.CallExpr, operator: str) -> ast.ConditionalExpr:
        # The nodes no text is written for are at the called name, outside
        # the arguments' text (`written_extremum`).
        def at() -> ast.Span:
            return replace(call.callee.span, occurrence=next(occurrences))

        first, second = call.arguments
        chosen = ast.ConditionalExpr(
            span=at(),
            when_true=second,
            condition=ast.ComparisonExpr(
                span=at(), left=first, operator=operator, right=copy(second)
            ),
            when_false=copy(first),
        )
        if type(second) is ast.LiteralExpr and second.value is not None:
            return replace(chosen, span=call.span)
        return ast.ConditionalExpr(
            span=call.span,
            when_true=chosen,
            condition=ast.IsNullExpr(span=at(), value=copy(second), negated=True),
            when_false=copy(second),
        )

    def normalize(original: object, rebuilt: object) -> object:
        if (
            id(original) not in calls
            and type(rebuilt) is ast.CallExpr
            and type(rebuilt.callee) is ast.NameExpr
            and rebuilt.callee.name in _EXTREMA.keys() - shadowed
            and len(rebuilt.arguments) == 2
            and not rebuilt.aggregate_order_by
        ):
            name = rebuilt.callee.name
            written = extremum(rebuilt, _EXTREMA[name])
            # Each call writes its arguments out again, a nested call too, so
            # a nest is bounded as a def's expansion is.
            size = _measure(written)
            if size.nodes > _MAX_EXPANSION_NODES or size.depth > _MAX_EXPANSION_DEPTH:
                diagnostics.append(
                    _size_diagnostic(name, size.nodes, size.depth, rebuilt.span)
                )
                return original
            rebuilt = written
        elif (
            id(original) not in calls
            and type(rebuilt) is ast.CallExpr
            and type(rebuilt.callee) is ast.NameExpr
            and rebuilt.callee.name in constructors - shadowed
        ):
            if rebuilt.aggregate_order_by:
                diagnostics.append(
                    _diagnostic(
                        "PIE-S2104",
                        INTERNAL_ORDER_ONLY,
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


def written_extremum(
    expression: ast.ConditionalExpr,
) -> tuple[str, ast.Expression, ast.Expression, tuple[ast.Expression, ...]] | None:
    """The name and the two arguments of the `max` or `min` call that
    ``expression`` is written for (`normalize_float_calls`), and its nodes that
    no text is written for, None for any other conditional: only such a call's
    conditionals test a value at a location outside that value's text. A def
    expansion keeps those nodes at the called def's name (`_substitution`)."""

    chosen = expression
    test = expression.condition
    parts: tuple[ast.Expression, ...] = ()
    if type(test) is ast.IsNullExpr:
        if type(expression.when_true) is not ast.ConditionalExpr or _within(
            test.value.span, test.span
        ):
            return None
        chosen = expression.when_true
        parts = (test, chosen)
    comparison = chosen.condition
    if (
        type(comparison) is not ast.ComparisonExpr
        or comparison.operator not in _EXTREMA.values()
        or _within(comparison.left.span, comparison.span)
        or not _within(comparison.left.span, expression.span)
    ):
        return None
    name = "max" if comparison.operator == "<" else "min"
    return name, comparison.left, chosen.when_true, (*parts, comparison)


def _within(inner: ast.Span, outer: ast.Span) -> bool:
    return (
        inner.path == outer.path
        and (outer.line, outer.column) <= (inner.line, inner.column)
        and (inner.end_line, inner.end_column) <= (outer.end_line, outer.end_column)
    )
