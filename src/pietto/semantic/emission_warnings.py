"""Single-file warnings for completed facts that cannot emit."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pietto.ast_nodes import (
    AuthoredJoinKind,
    CallExpr,
    ComparisonExpr,
    ConditionalExpr,
    Expression,
    FromClause,
    LetBinding,
    LiteralExpr,
    NameExpr,
    QueryDef,
    Script,
    Span,
    TableDef,
    TypeExpr,
    WindowFrameUnit,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import child_expressions
from pietto.semantic.expressions import (
    _canonical_resolved_type,
    _relation_projection_output_name,
)
from pietto.semantic.joins import _conjuncts
from pietto.semantic.model import (
    LetScopeSemanticInfo,
    RelationJoinsInfo,
    ResolvedType,
    TypeKind,
    ValueType,
)
from pietto.semantic.window_semantics import (
    AggregateWindowAnalysis,
    ValidatedFrame,
    WindowExpressionAnalysis,
    WindowNthDirection,
    WindowNullTreatment,
)

__all__ = ()


def emission_warnings(
    script: Script,
    *,
    window_expression_analyses: Mapping[WindowExpr, WindowExpressionAnalysis],
    aggregate_window_analyses: Mapping[WindowExpr, AggregateWindowAnalysis],
    relation_joins: Mapping[TableDef | QueryDef, RelationJoinsInfo],
    let_scopes: Mapping[TableDef | QueryDef, LetScopeSemanticInfo],
    type_expansions: Mapping[TypeExpr, ResolvedType],
    expression_value_types: Mapping[Expression, ValueType],
    from_resolutions: Mapping[FromClause, object],
    reported: Sequence[Diagnostic],
) -> list[Diagnostic]:
    """Return PIE-S2385 from complete semantic window and JOIN facts only."""

    errors = tuple(
        item.location for item in reported if item.severity is Severity.ERROR
    )
    found: list[Diagnostic] = []
    for analysis in (
        *window_expression_analyses.values(),
        *aggregate_window_analyses.values(),
    ):
        warning = _range_offset_warning(analysis, errors)
        if warning is not None:
            found.append(warning)
    for analysis in window_expression_analyses.values():
        expression = analysis.semantic_fact.expression
        modifiers = (
            analysis.navigation_fact.modifiers
            if analysis.navigation_fact is not None
            else analysis.frame_value_fact.modifiers
            if analysis.frame_value_fact is not None
            else None
        )
        if (
            modifiers is not None
            and modifiers.null_treatment is WindowNullTreatment.IGNORE_NULLS
        ):
            found.append(_warning(expression, "this window uses IGNORE NULLS"))
        if (
            modifiers is not None
            and modifiers.nth_direction is WindowNthDirection.FROM_LAST
        ):
            found.append(_warning(expression, "this window uses FROM LAST"))
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        info = relation_joins.get(definition)
        if info is None:
            continue
        for join in info.joins:
            if join.kind is not AuthoredJoinKind.FULL:
                continue
            equality_ids = {id(item.comparison) for item in join.equalities}
            for equality in join.equalities:
                if not (
                    _canonical_int(equality.left_type, type_expansions)
                    and _canonical_int(equality.right_type, type_expansions)
                ):
                    found.append(
                        _warning(
                            equality.comparison,
                            "this FULL JOIN equality is not between canonical Int fields",
                        )
                    )
            for condition in _conjuncts(join.condition) if join.condition else ():
                if (
                    id(condition) in equality_ids
                    or type(condition) is not ComparisonExpr
                    or condition.operator != "=="
                ):
                    continue
                left = info.field_reads.get(condition.left)
                right = info.field_reads.get(condition.right)
                if (
                    left is not None
                    and right is not None
                    and left.input != right.input
                    and not (
                        _canonical_int(
                            expression_value_types.get(condition.left), type_expansions
                        )
                        and _canonical_int(
                            expression_value_types.get(condition.right), type_expansions
                        )
                    )
                ):
                    found.append(
                        _warning(
                            condition,
                            "this FULL JOIN equality is not between canonical Int fields",
                        )
                    )
    found.extend(
        _all_null_relation_reads(
            script,
            relation_joins,
            let_scopes,
            from_resolutions,
            reported,
        )
    )
    return found


def _range_offset_warning(
    analysis: WindowExpressionAnalysis | AggregateWindowAnalysis,
    errors: Sequence[SourceLocation],
) -> Diagnostic | None:
    expression = analysis.semantic_fact.expression
    if any(_holds(expression, error) for error in errors):
        return None
    frame = analysis.validated_specification.frame
    start = frame.resolved.start if type(frame) is ValidatedFrame else None
    end = frame.resolved.end if type(frame) is ValidatedFrame else None
    if (
        type(frame) is ValidatedFrame
        and frame.resolved.unit is WindowFrameUnit.RANGE
        and (
            (start is not None and start.offset is not None)
            or (end is not None and end.offset is not None)
        )
    ):
        return _warning(
            expression,
            "this RANGE window frame has an offset",
        )
    return None


def _all_null_relation_reads(
    script: Script,
    relation_joins: Mapping[TableDef | QueryDef, RelationJoinsInfo],
    let_scopes: Mapping[TableDef | QueryDef, LetScopeSemanticInfo],
    from_resolutions: Mapping[FromClause, object],
    reported: Sequence[Diagnostic],
) -> list[Diagnostic]:
    """Warn when an untyped all-NULL output has any downstream relation reader."""

    errors = [item.location for item in reported if item.severity is Severity.ERROR]
    outputs = tuple(
        (definition, name, item.expression)
        for definition in script.definitions
        if isinstance(definition, (TableDef, QueryDef))
        for item in definition.select_items
        if (name := _relation_projection_output_name(item)) is not None
        and _untyped_all_null_output(
            item.expression,
            _let_values(let_scopes.get(definition)),
            errors,
        )
    )
    found: list[Diagnostic] = []
    readers: list[object] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        from_relation = from_resolutions.get(definition.from_clause)
        if from_relation is not None:
            readers.append(from_relation)
        info = relation_joins.get(definition)
        if info is not None:
            readers.extend(item.relation for item in info.inputs)
    for relation, name, expression in outputs:
        if not any(reader is relation for reader in readers):
            continue
        if any(_holds(expression, error) for error in errors):
            continue
        found.append(
            _warning(
                expression,
                f"`{name}` is an untyped all-None output that another relation reads",
            )
        )
    return found


def _untyped_all_null_output(
    expression: Expression,
    lets: Mapping[str, LetBinding],
    errors: Sequence[SourceLocation],
) -> bool:
    """Whether the complete semantic value is one PostgreSQL leaves untyped."""

    if _has_error_dependency(expression, lets, errors):
        return False
    pending = [(expression, frozenset[str]())]
    while pending:
        node, active = pending.pop()
        if type(node) is LiteralExpr:
            if node.value is not None:
                return False
        elif type(node) is ConditionalExpr:
            pending.extend(((node.when_true, active), (node.when_false, active)))
        elif (
            type(node) is CallExpr
            and type(node.callee) is NameExpr
            and node.callee.name in {"coalesce", "nullif"}
            and node.arguments
        ):
            pending.extend((argument, active) for argument in node.arguments)
        elif type(node) is NameExpr and node.name in lets and node.name not in active:
            pending.append((lets[node.name].expression, active | {node.name}))
        else:
            return False
    return True


def _let_values(scope: LetScopeSemanticInfo | None) -> Mapping[str, LetBinding]:
    if scope is None:
        return {}
    return {
        binding.name: binding
        for binding in scope.bindings
        if binding.name in scope.value_types
    }


def _has_error_dependency(
    expression: Expression,
    lets: Mapping[str, LetBinding],
    errors: Sequence[SourceLocation],
) -> bool:
    pending = [(expression, frozenset[str]())]
    while pending:
        node, active = pending.pop()
        if any(_holds(node, error) for error in errors):
            return True
        if type(node) is NameExpr and node.name in lets:
            if node.name in active:
                continue
            binding = lets[node.name]
            if any(_holds_span(binding.span, error) for error in errors):
                return True
            pending.append((binding.expression, active | {node.name}))
            continue
        pending.extend((child, active) for child in child_expressions(node))
    return False


def _holds(expression: Expression, location: SourceLocation) -> bool:
    return _holds_span(expression.span, location)


def _holds_span(span: Span, location: SourceLocation) -> bool:
    if location.path != span.path or (location.line, location.column) < (
        span.line,
        span.column,
    ):
        return False
    return (
        span.end_line is None
        or span.end_column is None
        or (
            (location.end_line or location.line, location.end_column or location.column)
            <= (span.end_line, span.end_column)
        )
    )


def _canonical_int(
    value: ValueType | None,
    type_expansions: Mapping[TypeExpr, ResolvedType],
) -> bool:
    resolved = (
        None if value is None else _canonical_resolved_type(value, type_expansions)
    )
    return (
        resolved is not None
        and resolved.kind is TypeKind.BUILTIN
        and resolved.name == "Int"
    )


def _warning(expression: Expression, detail: str) -> Diagnostic:
    span = expression.span
    return Diagnostic(
        code="PIE-S2385",
        severity=Severity.WARNING,
        message=(
            f"Single-file SQL emission is unavailable because {detail}; "
            "this warning does not change check's exit status, but emit-sql will "
            "refuse this relation."
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
