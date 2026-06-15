"""Semantic helpers for the Phase 19 no-GROUP aggregate entry slice."""

from __future__ import annotations

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    Expression,
    IsNullExpr,
    NameExpr,
    UnaryExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
)

COUNT_AGGREGATE_NAME = "count"

COUNT_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NON_NULL,
)


def callee_name(expression: CallExpr) -> str:
    """Return a source-level name for a simple or dotted call target."""

    if isinstance(expression.callee, NameExpr):
        return expression.callee.name
    return ".".join(expression.callee.parts)


def is_count_aggregate_call(expression: Expression) -> bool:
    """Return whether an expression is the approved aggregate call name."""

    return (
        isinstance(expression, CallExpr)
        and isinstance(expression.callee, NameExpr)
        and expression.callee.name == COUNT_AGGREGATE_NAME
    )


def contains_count_aggregate(expression: Expression) -> bool:
    """Return whether any subtree contains the Phase 19 count aggregate name."""

    if is_count_aggregate_call(expression):
        return True
    return any(
        contains_count_aggregate(child) for child in child_expressions(expression)
    )


def nested_count_aggregate(expression: Expression) -> CallExpr | None:
    """Return the first nested count aggregate call, if one exists."""

    return _nested_count_aggregate(expression, inside_count=False)


def _nested_count_aggregate(
    expression: Expression,
    *,
    inside_count: bool,
) -> CallExpr | None:
    is_count = is_count_aggregate_call(expression)
    if is_count and inside_count:
        assert isinstance(expression, CallExpr)
        return expression
    for child in child_expressions(expression):
        nested = _nested_count_aggregate(
            child,
            inside_count=inside_count or is_count,
        )
        if nested is not None:
            return nested
    return None


def child_expressions(expression: Expression) -> tuple[Expression, ...]:
    """Return immediate expression children for supported AST nodes."""

    if isinstance(expression, CallExpr):
        return expression.arguments
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, BinaryExpr):
        return (expression.left, expression.right)
    if isinstance(expression, ComparisonExpr):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    return ()


def invalid_context_diagnostic(
    expression: Expression,
    *,
    context: str,
) -> Diagnostic:
    """Report a count aggregate used outside direct aliased select projection."""

    return _diagnostic(
        expression,
        code="PIE-S2308",
        message=(
            "Aggregate count() is not allowed in "
            f"{context}; use it only as a direct aliased select projection"
        ),
    )


def wrong_arity_diagnostic(expression: CallExpr) -> Diagnostic:
    """Report count aggregate arity outside the approved count() shape."""

    return _diagnostic(
        expression,
        code="PIE-S2309",
        message=(
            "Aggregate function count expects 0 arguments, "
            f"got {len(expression.arguments)}"
        ),
    )


def deferred_composition_diagnostic(expression: Expression) -> Diagnostic:
    """Report a composed aggregate projection deferred beyond Slice 1A."""

    return _diagnostic(
        expression,
        code="PIE-S2310",
        message=(
            "Aggregate projection must be a direct aggregate call; "
            "composition around count() is deferred"
        ),
    )


def nested_aggregate_diagnostic(expression: CallExpr) -> Diagnostic:
    """Report a nested count aggregate call."""

    return _diagnostic(
        expression,
        code="PIE-S2311",
        message="Nested aggregate count() is not supported",
    )


def mixed_projection_diagnostic(expression: Expression) -> Diagnostic:
    """Report a no-GROUP aggregate projection mixed with row projections."""

    return _diagnostic(
        expression,
        code="PIE-S2312",
        message=(
            "Aggregate projections cannot be mixed with non-aggregate "
            "projections without GROUP BY"
        ),
    )


def aggregate_alias_required_diagnostic(expression: CallExpr) -> Diagnostic:
    """Report an unaliased count aggregate projection."""

    return _diagnostic(
        expression,
        code="PIE-S2313",
        message="Aggregate count() projection requires an explicit alias",
    )


def _diagnostic(
    expression: Expression,
    *,
    code: str,
    message: str,
) -> Diagnostic:
    span = expression.span
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
