"""Semantic helpers for no-GROUP aggregate entry slices."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    LiteralExpr,
    NameExpr,
    UnaryExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

COUNT_AGGREGATE_NAME = "count"
COUNT_DISTINCT_AGGREGATE_NAME = "count_distinct"
SUM_AGGREGATE_NAME = "sum"
AVG_AGGREGATE_NAME = "avg"
# Keep this IR-facing aggregate set limited to the already lowered aggregate
# vocabulary. Later semantic-only slices may run ahead of IR lowering.
AGGREGATE_NAMES = frozenset(
    {
        COUNT_AGGREGATE_NAME,
        SUM_AGGREGATE_NAME,
        AVG_AGGREGATE_NAME,
    }
)
MIN_AGGREGATE_NAME = "min"
MAX_AGGREGATE_NAME = "max"
SEMANTIC_AGGREGATE_NAMES = AGGREGATE_NAMES | frozenset(
    {
        COUNT_DISTINCT_AGGREGATE_NAME,
        MIN_AGGREGATE_NAME,
        MAX_AGGREGATE_NAME,
    }
)

COUNT_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NON_NULL,
)
INT_NULLABLE_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Int", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NULLABLE,
)
FLOAT_NULLABLE_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Float", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NULLABLE,
)
DECIMAL_NULLABLE_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Decimal", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NULLABLE,
)


def callee_name(expression: CallExpr) -> str:
    """Return a source-level name for a simple or dotted call target."""

    if isinstance(expression.callee, NameExpr):
        return expression.callee.name
    return ".".join(expression.callee.parts)


def is_count_aggregate_call(expression: Expression) -> bool:
    """Return whether an expression is the approved count aggregate call."""

    return aggregate_call_name(expression) == COUNT_AGGREGATE_NAME


def aggregate_call_name(expression: Expression) -> str | None:
    """Return the aggregate function name for one recognized aggregate call."""

    if (
        isinstance(expression, CallExpr)
        and isinstance(expression.callee, NameExpr)
        and expression.callee.name in AGGREGATE_NAMES
    ):
        return expression.callee.name
    return None


def semantic_aggregate_call_name(expression: Expression) -> str | None:
    """Return the semantic aggregate function name for one recognized call."""

    if (
        isinstance(expression, CallExpr)
        and isinstance(expression.callee, NameExpr)
        and expression.callee.name in SEMANTIC_AGGREGATE_NAMES
    ):
        return expression.callee.name
    return None


def is_aggregate_call(expression: Expression) -> bool:
    """Return whether an expression is a recognized aggregate call."""

    return aggregate_call_name(expression) is not None


def is_semantic_aggregate_call(expression: Expression) -> bool:
    """Return whether an expression is recognized by semantic aggregate checks."""

    return semantic_aggregate_call_name(expression) is not None


def contains_aggregate(expression: Expression) -> bool:
    """Return whether any subtree contains a recognized aggregate name."""

    if is_aggregate_call(expression):
        return True
    return any(contains_aggregate(child) for child in child_expressions(expression))


def contains_semantic_aggregate(expression: Expression) -> bool:
    """Return whether any subtree contains a semantic aggregate name."""

    if is_semantic_aggregate_call(expression):
        return True
    return any(
        contains_semantic_aggregate(child) for child in child_expressions(expression)
    )


def first_aggregate_call(expression: Expression) -> CallExpr | None:
    """Return the first aggregate call in source traversal order."""

    if is_aggregate_call(expression):
        assert isinstance(expression, CallExpr)
        return expression
    for child in child_expressions(expression):
        found = first_aggregate_call(child)
        if found is not None:
            return found
    return None


def first_semantic_aggregate_call(expression: Expression) -> CallExpr | None:
    """Return the first semantic aggregate call in source traversal order."""

    if is_semantic_aggregate_call(expression):
        assert isinstance(expression, CallExpr)
        return expression
    for child in child_expressions(expression):
        found = first_semantic_aggregate_call(child)
        if found is not None:
            return found
    return None


def nested_aggregate(expression: Expression) -> CallExpr | None:
    """Return the first aggregate nested inside another aggregate, if any."""

    return _nested_aggregate(expression, inside_aggregate=False)


def _nested_aggregate(
    expression: Expression,
    *,
    inside_aggregate: bool,
) -> CallExpr | None:
    is_aggregate = is_aggregate_call(expression)
    if is_aggregate and inside_aggregate:
        assert isinstance(expression, CallExpr)
        return expression
    for child in child_expressions(expression):
        nested = _nested_aggregate(
            child,
            inside_aggregate=inside_aggregate or is_aggregate,
        )
        if nested is not None:
            return nested
    return None


def nested_semantic_aggregate(expression: Expression) -> CallExpr | None:
    """Return the first semantic aggregate nested inside another aggregate."""

    return _nested_semantic_aggregate(expression, inside_aggregate=False)


def _nested_semantic_aggregate(
    expression: Expression,
    *,
    inside_aggregate: bool,
) -> CallExpr | None:
    is_aggregate = is_semantic_aggregate_call(expression)
    if is_aggregate and inside_aggregate:
        assert isinstance(expression, CallExpr)
        return expression
    for child in child_expressions(expression):
        nested = _nested_semantic_aggregate(
            child,
            inside_aggregate=inside_aggregate or is_aggregate,
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


def expected_aggregate_arity(function_name: str) -> int:
    """Return the approved argument count for one aggregate function."""

    if function_name == COUNT_AGGREGATE_NAME:
        return 0
    if function_name in {SUM_AGGREGATE_NAME, AVG_AGGREGATE_NAME}:
        return 1
    raise AssertionError(f"Unsupported aggregate function: {function_name}")


def expected_semantic_aggregate_arity(function_name: str) -> int:
    """Return the semantic argument count for one aggregate function."""

    if function_name in AGGREGATE_NAMES:
        return expected_aggregate_arity(function_name)
    if function_name in {
        COUNT_DISTINCT_AGGREGATE_NAME,
        MIN_AGGREGATE_NAME,
        MAX_AGGREGATE_NAME,
    }:
        return 1
    raise AssertionError(f"Unsupported aggregate function: {function_name}")


def expected_semantic_aggregate_arities(function_name: str) -> tuple[int, ...]:
    """Return all semantic argument counts accepted for one aggregate."""

    if function_name == COUNT_AGGREGATE_NAME:
        return (0, 1)
    return (expected_semantic_aggregate_arity(function_name),)


def is_supported_semantic_aggregate_arity(
    function_name: str,
    arity: int,
) -> bool:
    """Return whether one aggregate arity is accepted semantically."""

    return arity in expected_semantic_aggregate_arities(function_name)


def is_direct_field_argument(expression: Expression) -> bool:
    """Return whether an aggregate argument is one direct field reference."""

    return isinstance(expression, (NameExpr, DottedNameExpr))


def is_supported_semantic_aggregate_argument_expression(
    function_name: str,
    expression: Expression,
    value_type: ValueType,
    *,
    let_expansions: Mapping[str, Expression] | None = None,
) -> bool:
    """Return whether an aggregate accepts this argument expression."""

    expression = effective_semantic_aggregate_argument_expression(
        function_name,
        expression,
        let_expansions=let_expansions,
    )
    if is_direct_field_argument(expression):
        return is_supported_semantic_aggregate_argument(function_name, value_type)
    if function_name == COUNT_AGGREGATE_NAME:
        return _is_supported_count_expression_shape(expression, value_type)
    if function_name == COUNT_DISTINCT_AGGREGATE_NAME:
        return _is_builtin(value_type, "Text") and _is_lower_trim_text_transform_chain(
            expression
        )
    if function_name not in {SUM_AGGREGATE_NAME, AVG_AGGREGATE_NAME}:
        return False
    return _is_supported_sum_avg_numeric_expression_shape(
        expression,
        value_type,
    )


def effective_semantic_aggregate_argument_expression(
    function_name: str,
    expression: Expression,
    *,
    let_expansions: Mapping[str, Expression] | None,
) -> Expression:
    """Return the expression shape used for approved aggregate argument checks."""

    if function_name not in {SUM_AGGREGATE_NAME, AVG_AGGREGATE_NAME}:
        return expression
    if not isinstance(expression, NameExpr):
        return expression
    if let_expansions is None or expression.name not in let_expansions:
        return expression
    return _expand_let_references(
        let_expansions[expression.name],
        let_expansions=let_expansions,
        let_stack=frozenset((expression.name,)),
    )


def aggregate_argument_can_use_let_scope(
    function_name: str,
    expression: Expression,
    let_expansions: Mapping[str, Expression] | None,
) -> bool:
    """Return whether this aggregate argument is the approved direct let form."""

    return (
        function_name in {SUM_AGGREGATE_NAME, AVG_AGGREGATE_NAME}
        and isinstance(expression, NameExpr)
        and let_expansions is not None
        and expression.name in let_expansions
    )


def _expand_let_references(
    expression: Expression,
    *,
    let_expansions: Mapping[str, Expression],
    let_stack: frozenset[str],
) -> Expression:
    if isinstance(expression, NameExpr) and expression.name in let_expansions:
        if expression.name in let_stack:
            return expression
        return _expand_let_references(
            let_expansions[expression.name],
            let_expansions=let_expansions,
            let_stack=let_stack | frozenset((expression.name,)),
        )
    if isinstance(expression, UnaryExpr):
        return UnaryExpr(
            operator=expression.operator,
            operand=_expand_let_references(
                expression.operand,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            span=expression.span,
        )
    if isinstance(expression, BinaryExpr):
        return BinaryExpr(
            left=_expand_let_references(
                expression.left,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            operator=expression.operator,
            right=_expand_let_references(
                expression.right,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            span=expression.span,
        )
    if isinstance(expression, CallExpr):
        return CallExpr(
            callee=expression.callee,
            arguments=tuple(
                _expand_let_references(
                    argument,
                    let_expansions=let_expansions,
                    let_stack=let_stack,
                )
                for argument in expression.arguments
            ),
            span=expression.span,
        )
    if isinstance(expression, ComparisonExpr):
        return ComparisonExpr(
            left=_expand_let_references(
                expression.left,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            operator=expression.operator,
            right=_expand_let_references(
                expression.right,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            span=expression.span,
        )
    if isinstance(expression, BetweenExpr):
        return BetweenExpr(
            value=_expand_let_references(
                expression.value,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            lower=_expand_let_references(
                expression.lower,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            upper=_expand_let_references(
                expression.upper,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            span=expression.span,
        )
    if isinstance(expression, IsNullExpr):
        return IsNullExpr(
            value=_expand_let_references(
                expression.value,
                let_expansions=let_expansions,
                let_stack=let_stack,
            ),
            negated=expression.negated,
            span=expression.span,
        )
    return expression


def has_unknown_field_reference(
    expression: Expression,
    expression_value_types: Mapping[Expression, ValueType] | None,
) -> bool:
    """Return whether a field leaf in this expression is semantically unknown."""

    if expression_value_types is None:
        return False
    if isinstance(expression, (NameExpr, DottedNameExpr)):
        value_type = expression_value_types.get(expression)
        return value_type is None or value_type.kind is ValueTypeKind.UNKNOWN
    return any(
        has_unknown_field_reference(child, expression_value_types)
        for child in child_expressions(expression)
    )


def is_supported_numeric_argument(value_type: ValueType) -> bool:
    """Return whether an aggregate argument is an approved numeric field type."""

    return any(_is_builtin(value_type, name) for name in ("Int", "Float", "Decimal"))


def is_supported_extrema_argument(value_type: ValueType) -> bool:
    """Return whether min/max may use this direct field type."""

    return any(
        _is_builtin(value_type, name)
        for name in ("Int", "Float", "Decimal", "Date", "Timestamp")
    )


def is_supported_count_argument(value_type: ValueType) -> bool:
    """Return whether count(field) may use this direct field type."""

    return value_type.resolved_type.kind not in {
        TypeKind.ENUM,
        TypeKind.UNKNOWN,
    } and not _is_builtin(value_type, "Any")


def is_supported_count_distinct_argument(value_type: ValueType) -> bool:
    """Return whether count_distinct(field) may use this direct field type."""

    return any(
        _is_builtin(value_type, name)
        for name in (
            "Bool",
            "Int",
            "Float",
            "Decimal",
            "Text",
            "Date",
            "Timestamp",
            "UUID",
        )
    )


def _is_supported_count_expression_shape(
    expression: Expression,
    value_type: ValueType,
) -> bool:
    if not is_supported_count_argument(value_type):
        return False

    is_valid, has_field = _count_expression_shape(expression)
    return is_valid and has_field


def _count_expression_shape(expression: Expression) -> tuple[bool, bool]:
    """Return (valid shape, has direct field leaf) for count expressions."""

    if isinstance(expression, (NameExpr, DottedNameExpr)):
        return True, True
    if isinstance(expression, LiteralExpr):
        return True, False
    if isinstance(expression, UnaryExpr):
        if expression.operator not in {"+", "-"}:
            return False, False
        return _count_expression_shape(expression.operand)
    if isinstance(expression, BinaryExpr):
        if expression.operator not in {"+", "-", "*", "%", "and", "or"}:
            return False, False
        left_valid, left_has_field = _count_expression_shape(expression.left)
        right_valid, right_has_field = _count_expression_shape(expression.right)
        return left_valid and right_valid, left_has_field or right_has_field
    if isinstance(expression, CallExpr):
        if not isinstance(expression.callee, NameExpr):
            return False, False
        if expression.callee.name not in {"lower", "trim", "len"}:
            return False, False
        if len(expression.arguments) != 1:
            return False, False
        return _count_expression_shape(expression.arguments[0])
    return False, False


def _is_field_only_numeric_shape(expression: Expression) -> bool:
    if isinstance(expression, (NameExpr, DottedNameExpr)):
        return True
    if isinstance(expression, UnaryExpr):
        return expression.operator in {"+", "-"} and _is_field_only_numeric_shape(
            expression.operand
        )
    if isinstance(expression, BinaryExpr):
        return (
            expression.operator in {"+", "-", "*"}
            and _is_field_only_numeric_shape(expression.left)
            and _is_field_only_numeric_shape(expression.right)
        )
    return False


def _is_supported_sum_avg_numeric_expression_shape(
    expression: Expression,
    value_type: ValueType,
) -> bool:
    if _is_field_only_numeric_shape(expression):
        return is_supported_numeric_argument(value_type)

    is_valid, has_field, has_literal = _numeric_literal_argument_shape(expression)
    return (
        is_valid
        and has_field
        and has_literal
        and (_is_builtin(value_type, "Int") or _is_builtin(value_type, "Float"))
    )


def _numeric_literal_argument_shape(
    expression: Expression,
) -> tuple[bool, bool, bool]:
    """Return (valid, has direct field leaf, has Int/Float literal leaf)."""

    if isinstance(expression, (NameExpr, DottedNameExpr)):
        return True, True, False
    if isinstance(expression, LiteralExpr):
        return type(expression.value) in {int, float}, False, True
    if isinstance(expression, UnaryExpr):
        if expression.operator not in {"+", "-"}:
            return False, False, False
        return _numeric_literal_argument_shape(expression.operand)
    if isinstance(expression, BinaryExpr):
        if expression.operator not in {"+", "-", "*"}:
            return False, False, False
        left_valid, left_has_field, left_has_literal = _numeric_literal_argument_shape(
            expression.left
        )
        (
            right_valid,
            right_has_field,
            right_has_literal,
        ) = _numeric_literal_argument_shape(
            expression.right,
        )
        return (
            left_valid and right_valid,
            left_has_field or right_has_field,
            left_has_literal or right_has_literal,
        )
    return False, False, False


def _is_lower_trim_text_transform_chain(expression: Expression) -> bool:
    if isinstance(expression, (NameExpr, DottedNameExpr)):
        return True
    if not isinstance(expression, CallExpr):
        return False
    if not isinstance(expression.callee, NameExpr):
        return False
    if expression.callee.name not in {"lower", "trim"}:
        return False
    if len(expression.arguments) != 1:
        return False
    return _is_lower_trim_text_transform_chain(expression.arguments[0])


def is_supported_semantic_aggregate_argument(
    function_name: str,
    value_type: ValueType,
) -> bool:
    """Return whether an aggregate accepts this direct field argument type."""

    if function_name == COUNT_AGGREGATE_NAME:
        return is_supported_count_argument(value_type)
    if function_name == COUNT_DISTINCT_AGGREGATE_NAME:
        return is_supported_count_distinct_argument(value_type)
    if function_name in {SUM_AGGREGATE_NAME, AVG_AGGREGATE_NAME}:
        return is_supported_numeric_argument(value_type)
    if function_name in {MIN_AGGREGATE_NAME, MAX_AGGREGATE_NAME}:
        return is_supported_extrema_argument(value_type)
    return False


def aggregate_result_value_type(
    function_name: str,
    argument_type: ValueType | None = None,
) -> ValueType | None:
    """Return the logical no-GROUP aggregate result type when supported."""

    if function_name == COUNT_AGGREGATE_NAME:
        if argument_type is None:
            return COUNT_VALUE_TYPE
        return COUNT_VALUE_TYPE if is_supported_count_argument(argument_type) else None
    if argument_type is None or not is_supported_numeric_argument(argument_type):
        return None
    if function_name == SUM_AGGREGATE_NAME:
        if _is_builtin(argument_type, "Int"):
            return INT_NULLABLE_VALUE_TYPE
        if _is_builtin(argument_type, "Decimal"):
            return DECIMAL_NULLABLE_VALUE_TYPE
        return FLOAT_NULLABLE_VALUE_TYPE
    if function_name == AVG_AGGREGATE_NAME:
        if _is_builtin(argument_type, "Decimal"):
            return DECIMAL_NULLABLE_VALUE_TYPE
        return FLOAT_NULLABLE_VALUE_TYPE
    return None


def semantic_aggregate_result_value_type(
    function_name: str,
    argument_type: ValueType | None = None,
) -> ValueType | None:
    """Return the semantic aggregate result type when supported."""

    if function_name in AGGREGATE_NAMES:
        return aggregate_result_value_type(function_name, argument_type)
    if function_name == COUNT_DISTINCT_AGGREGATE_NAME:
        if argument_type is None:
            return None
        return (
            COUNT_VALUE_TYPE
            if is_supported_count_distinct_argument(argument_type)
            else None
        )
    if function_name not in {MIN_AGGREGATE_NAME, MAX_AGGREGATE_NAME}:
        return None
    if argument_type is None or not is_supported_extrema_argument(argument_type):
        return None
    return ValueType(
        resolved_type=argument_type.resolved_type,
        nullability=EffectiveNullability.NULLABLE,
    )


def semantic_projection_aggregate_result_value_type(
    function_name: str,
    argument_type: ValueType | None = None,
) -> ValueType | None:
    """Return semantic projection result types ahead of IR lowering."""

    return semantic_aggregate_result_value_type(function_name, argument_type)


def invalid_context_diagnostic(
    expression: Expression,
    *,
    context: str,
) -> Diagnostic:
    """Report an aggregate used outside direct aliased select projection."""

    aggregate = first_semantic_aggregate_call(expression)
    name = COUNT_AGGREGATE_NAME if aggregate is None else callee_name(aggregate)

    return _diagnostic(
        expression,
        code="PIE-S2308",
        message=(
            f"Aggregate {name}() is not allowed in "
            f"{context}; use it only as a direct aliased select projection"
        ),
    )


def wrong_arity_diagnostic(expression: CallExpr) -> Diagnostic:
    """Report aggregate arity outside the approved no-GROUP shape."""

    name = callee_name(expression)
    expected = _expected_arity_text(name)

    return _diagnostic(
        expression,
        code="PIE-S2309",
        message=(
            f"Aggregate function {name} expects {expected} arguments, "
            f"got {len(expression.arguments)}"
        ),
    )


def deferred_composition_diagnostic(expression: Expression) -> Diagnostic:
    """Report a composed aggregate projection deferred beyond direct calls."""

    aggregate = first_semantic_aggregate_call(expression)
    name = COUNT_AGGREGATE_NAME if aggregate is None else callee_name(aggregate)

    return _diagnostic(
        expression,
        code="PIE-S2310",
        message=(
            "Aggregate projection must be a direct aggregate call; "
            f"composition around {name}() is deferred"
        ),
    )


def nested_aggregate_diagnostic(expression: CallExpr) -> Diagnostic:
    """Report a nested aggregate call."""

    name = callee_name(expression)

    return _diagnostic(
        expression,
        code="PIE-S2311",
        message=f"Nested aggregate {name}() is not supported",
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
    """Report an unaliased aggregate projection."""

    name = callee_name(expression)

    return _diagnostic(
        expression,
        code="PIE-S2313",
        message=f"Aggregate {name}() projection requires an explicit alias",
    )


def wrong_argument_type_diagnostic(
    expression: CallExpr,
    *,
    actual_name: str,
) -> Diagnostic:
    """Report a direct aggregate field argument with an unsupported type."""

    name = callee_name(expression)
    expected = (
        "concrete non-Any"
        if name == COUNT_AGGREGATE_NAME
        else (
            "Bool, Int, Float, Decimal, Text, Date, Timestamp, or UUID"
            if name == COUNT_DISTINCT_AGGREGATE_NAME
            else (
                "Int, Float, Decimal, Date, or Timestamp"
                if name in {MIN_AGGREGATE_NAME, MAX_AGGREGATE_NAME}
                else "Int, Float, or Decimal"
            )
        )
    )

    return _diagnostic(
        expression,
        code="PIE-S2314",
        message=(
            f"Aggregate function {name} expects {expected} field argument, "
            f"got {actual_name}"
        ),
    )


def deferred_argument_expression_diagnostic(expression: CallExpr) -> Diagnostic:
    """Report an aggregate argument expression deferred beyond the MVP."""

    name = callee_name(expression)

    return _diagnostic(
        expression,
        code="PIE-S2315",
        message=(
            f"Aggregate function {name} requires a direct field argument; "
            "expression arguments are deferred"
        ),
    )


def _is_builtin(value_type: ValueType, name: str) -> bool:
    return (
        value_type.resolved_type.kind is TypeKind.BUILTIN
        and value_type.resolved_type.name == name
    )


def _expected_arity_text(function_name: str) -> str:
    arities = expected_semantic_aggregate_arities(function_name)
    if len(arities) == 1:
        return str(arities[0])
    return " or ".join(str(arity) for arity in arities)


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
