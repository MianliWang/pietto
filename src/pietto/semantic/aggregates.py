"""Semantic helpers for no-GROUP aggregate entry slices."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import cast

from pietto import ast_nodes as ast
from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CastExpr,
    CallExpr,
    ConditionalExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    ParameterRefExpr,
    UnaryExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

COUNT_AGGREGATE_NAME = "count"
COUNT_DISTINCT_AGGREGATE_NAME = "count_distinct"
SUM_AGGREGATE_NAME = "sum"
AVG_AGGREGATE_NAME = "avg"
STRING_AGGREGATE_NAME = "string_agg"
# Keep this IR-facing aggregate set limited to the already lowered aggregate
# vocabulary. Later semantic-only slices may run ahead of IR lowering.
AGGREGATE_NAMES = frozenset(
    {
        COUNT_AGGREGATE_NAME,
        SUM_AGGREGATE_NAME,
        AVG_AGGREGATE_NAME,
        STRING_AGGREGATE_NAME,
        STRING_AGGREGATE_NAME,
    }
)
MIN_AGGREGATE_NAME = "min"
MAX_AGGREGATE_NAME = "max"
# The sample standard deviation (Python `statistics.stdev`) of an Int or Float
# direct field; its result is a nullable Float.
STDDEV_AGGREGATE_NAME = "stddev"
# The sample variance, the population variance and the population standard
# deviation (Python `statistics.variance`, `pvariance` and `pstdev`), typed as
# `stddev`.
VARIANCE_AGGREGATE_NAME = "variance"
PVARIANCE_AGGREGATE_NAME = "pvariance"
PSTDEV_AGGREGATE_NAME = "pstdev"
# The interpolated median and quantile (pandas `Series.median` and
# `Series.quantile`) of an Int or Float direct field, whose values are taken as
# Float; `quantile` also takes a Float literal fraction from 0.0 to 1.0. Their
# result is a nullable Float.
MEDIAN_AGGREGATE_NAME = "median"
QUANTILE_AGGREGATE_NAME = "quantile"
# The aggregates of an Int or Float direct field with a nullable Float result.
FLOAT_STATISTIC_AGGREGATE_NAMES = frozenset(
    {
        STDDEV_AGGREGATE_NAME,
        VARIANCE_AGGREGATE_NAME,
        PVARIANCE_AGGREGATE_NAME,
        PSTDEV_AGGREGATE_NAME,
        MEDIAN_AGGREGATE_NAME,
        QUANTILE_AGGREGATE_NAME,
    }
)
# The test of a group, `any(TEST for o in group)` and `all(TEST for o in
# group)`: an aggregate only as a call with a generator, a Bool never None.
GROUP_TEST_AGGREGATE_NAMES = frozenset({"any", "all"})
SEMANTIC_AGGREGATE_NAMES = AGGREGATE_NAMES | frozenset(
    {
        COUNT_DISTINCT_AGGREGATE_NAME,
        MIN_AGGREGATE_NAME,
        MAX_AGGREGATE_NAME,
        *FLOAT_STATISTIC_AGGREGATE_NAMES,
    }
)
LET_EXPANDABLE_AGGREGATE_ARGUMENT_NAMES = frozenset(
    {
        COUNT_AGGREGATE_NAME,
        COUNT_DISTINCT_AGGREGATE_NAME,
        SUM_AGGREGATE_NAME,
        AVG_AGGREGATE_NAME,
        STRING_AGGREGATE_NAME,
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
BOOL_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Bool", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NON_NULL,
)
FLOAT_NULLABLE_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Float", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NULLABLE,
)
DECIMAL_NULLABLE_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Decimal", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NULLABLE,
)
_TEXT_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="Text", kind=TypeKind.BUILTIN),
    nullability=EffectiveNullability.NULLABLE,
)


_KNOWN_EXPRESSIONS = frozenset(
    {
        ast.LiteralExpr,
        ast.NameExpr,
        ast.DottedNameExpr,
        ast.CallExpr,
        ast.UnaryExpr,
        ast.ConditionalExpr,
        ast.MembershipExpr,
        ast.RelationExistsExpr,
        ast.AnyExpr,
        ast.GeneratorExpr,
        ast.RelationScalarExpr,
        ast.RelationMembershipExpr,
        ast.CastExpr,
        ast.BinaryExpr,
        ast.ComparisonExpr,
        ast.BetweenExpr,
        ast.IsNullExpr,
        ast.WindowExpr,
        ast.ParameterRefExpr,
        ast.CapturedFieldExpr,
    }
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
        and list_generator_of(expression) is None
    ):
        return expression.callee.name
    return None


def semantic_aggregate_call_name(expression: Expression) -> str | None:
    """Return the semantic aggregate function name for one recognized call."""

    if (
        isinstance(expression, CallExpr)
        and isinstance(expression.callee, NameExpr)
        and list_generator_of(expression) is None
    ):
        name = expression.callee.name
        if name in SEMANTIC_AGGREGATE_NAMES or (
            name in GROUP_TEST_AGGREGATE_NAMES
            and _generator_argument(expression) is not None
        ):
            return name
    return None


def list_generator_of(expression: Expression) -> ast.GeneratorExpr | None:
    """The generator of a `sum` or `any` call over a row's collected field
    (``c.xs``), a list operation of one row and no aggregate; else None."""

    if not (
        isinstance(expression, CallExpr)
        and isinstance(expression.callee, NameExpr)
        and expression.callee.name in {SUM_AGGREGATE_NAME, "any"}
    ):
        return None
    generator = _generator_argument(expression)
    if generator is None or generator.source_read is None:
        return None
    return generator


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
        return (*expression.arguments, *aggregate_order_expressions(expression))
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, ConditionalExpr):
        return (expression.when_true, expression.condition, expression.when_false)
    if isinstance(expression, MembershipExpr):
        return (expression.value, *expression.options)
    if isinstance(expression, ast.RelationMembershipExpr):
        return (expression.value,)
    if isinstance(expression, CastExpr):
        return (expression.value,)
    if isinstance(expression, BinaryExpr):
        return (expression.left, expression.right)
    if isinstance(expression, ComparisonExpr):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    if isinstance(expression, ast.GeneratorExpr):
        # A list generator's body and test read its element, not the row:
        # its one row read is the collected field.
        if expression.source_read is not None:
            return (expression.source_read,)
        return expression.operands
    if isinstance(
        expression,
        (
            LiteralExpr,
            NameExpr,
            DottedNameExpr,
            WindowExpr,
            ParameterRefExpr,
            ast.RelationExistsExpr,
            ast.CollectRelationExpr,
            ast.AnyExpr,
            ast.RelationScalarExpr,
            ast.CapturedFieldExpr,
        ),
    ):
        return ()
    raise AssertionError(f"Unsupported expression: {type(expression).__name__}")


def expected_aggregate_arity(function_name: str) -> int:
    """Return the approved argument count for one aggregate function."""

    if function_name == COUNT_AGGREGATE_NAME:
        return 0
    if function_name in {SUM_AGGREGATE_NAME, AVG_AGGREGATE_NAME}:
        return 1
    raise AssertionError(f"Unsupported aggregate function: {function_name}")


def expected_semantic_aggregate_arity(function_name: str) -> int:
    """Return the semantic argument count for one aggregate function."""

    if function_name in {STRING_AGGREGATE_NAME, QUANTILE_AGGREGATE_NAME}:
        return 2
    if function_name in AGGREGATE_NAMES:
        return expected_aggregate_arity(function_name)
    if function_name in {
        COUNT_DISTINCT_AGGREGATE_NAME,
        MIN_AGGREGATE_NAME,
        MAX_AGGREGATE_NAME,
        STDDEV_AGGREGATE_NAME,
        VARIANCE_AGGREGATE_NAME,
        PVARIANCE_AGGREGATE_NAME,
        PSTDEV_AGGREGATE_NAME,
        MEDIAN_AGGREGATE_NAME,
        *GROUP_TEST_AGGREGATE_NAMES,
    }:
        return 1
    raise AssertionError(f"Unsupported aggregate function: {function_name}")


def expected_semantic_aggregate_arities(function_name: str) -> tuple[int, ...]:
    """Return all semantic argument counts accepted for one aggregate."""

    if function_name == COUNT_AGGREGATE_NAME:
        return (0, 1)
    return (expected_semantic_aggregate_arity(function_name),)


def aggregate_order_expressions(expression: CallExpr) -> tuple[Expression, ...]:
    """Return ordered keys only for the aggregate that owns that syntax."""

    if semantic_aggregate_call_name(expression) != STRING_AGGREGATE_NAME:
        return ()
    return tuple(item.expression for item in expression.aggregate_order_by)


def is_supported_semantic_aggregate_arity(
    function_name: str,
    arity: int,
) -> bool:
    """Return whether one aggregate arity is accepted semantically; a
    `count_distinct` of several arguments counts their distinct tuples."""

    if function_name == COUNT_DISTINCT_AGGREGATE_NAME:
        return arity >= 1
    return arity in expected_semantic_aggregate_arities(function_name)


def is_count_distinct_tuple(expression: Expression) -> bool:
    """Whether a call is `count_distinct(a, b, ...)`: the number of distinct
    tuples of its arguments over the rows in which none of them is None."""

    return (
        semantic_aggregate_call_name(expression) == COUNT_DISTINCT_AGGREGATE_NAME
        and len(cast(CallExpr, expression).arguments) > 1
    )


def count_distinct_tuple_diagnostic(
    expression: CallExpr,
    argument_types: tuple[ValueType | None, ...],
    *,
    let_expansions: Mapping[str, Expression] | None,
) -> Diagnostic | None:
    """The first refused argument of `count_distinct(a, b, ...)`, at that
    argument: PIE-S2315 for one that is not a direct field (or a `let:` name
    of one), PIE-S2104 for a field written again and PIE-S2314 for a known
    type that `count_distinct(x)` refuses. ``argument_types`` are the
    arguments' canonical types, None where not typed; an unknown one is its
    own error's."""

    written: list[tuple[tuple[str, ...], bool]] = []
    for argument, argument_type in zip(
        expression.arguments, argument_types, strict=True
    ):
        field = effective_semantic_aggregate_argument_expression(
            COUNT_DISTINCT_AGGREGATE_NAME, argument, let_expansions=let_expansions
        )
        if not is_direct_field_argument(field):
            return _diagnostic(
                argument,
                code="PIE-S2315",
                message="Aggregate function count_distinct of several columns "
                "requires a direct field for each argument; expression arguments "
                "are not supported",
            )
        parts = (
            (field.name,)
            if type(field) is NameExpr
            else cast(DottedNameExpr, field).parts
        )
        # A bare name that reads a field reads the one input field so named,
        # which a read qualified by its binding (`sales.pot` beside `pot`)
        # names too; an unknown or ambiguous read is its own error alone.
        read = argument_type is None or argument_type.kind is ValueTypeKind.KNOWN
        first = next(
            (
                key
                for key, key_read in written
                if key == parts
                or read
                and key_read
                and {len(key), len(parts)} == {1, 2}
                and key[-1] == parts[-1]
            ),
            None,
        )
        if first is not None:
            return _diagnostic(
                argument,
                code="PIE-S2104",
                message="Invalid arguments for aggregate count_distinct: "
                f"{'.'.join(first)} is written twice",
                hint=f"write `count_distinct({'.'.join(first)})`"
                if len(expression.arguments) == 2
                else "write each column once",
            )
        written.append((parts, read))
    for argument, argument_type in zip(
        expression.arguments, argument_types, strict=True
    ):
        if (
            argument_type is not None
            and argument_type.kind is ValueTypeKind.KNOWN
            and not is_supported_count_distinct_argument(argument_type)
        ):
            return _diagnostic(
                argument,
                code="PIE-S2314",
                message="Aggregate function count_distinct expects Bool, Int, "
                "Float, Decimal, Text, Date, Timestamp, or UUID field argument, "
                f"got {argument_type.resolved_type.name}",
            )
    return None


def is_direct_field_argument(expression: Expression) -> bool:
    """Return whether an aggregate argument is one direct field reference."""

    return isinstance(expression, (NameExpr, DottedNameExpr))


def is_supported_semantic_aggregate_argument_expression(
    function_name: str,
    expression: Expression,
    value_type: ValueType,
    *,
    let_expansions: Mapping[str, Expression] | None = None,
    form_only: bool = False,
) -> bool:
    """Return whether an aggregate accepts this argument expression; with
    ``form_only``, whether it accepts its form (`accepts_argument_form`)."""

    expression = effective_semantic_aggregate_argument_expression(
        function_name,
        expression,
        let_expansions=let_expansions,
    )
    if is_direct_field_argument(expression):
        return is_supported_semantic_aggregate_argument(function_name, value_type)
    if type(expression) is ast.GeneratorExpr:
        # The conditional count and sum of a group add Int values (D73.04);
        # the test of a group reads a Bool.
        return (
            generator_aggregate_result_value_type(function_name, value_type) is not None
        )
    if function_name == COUNT_AGGREGATE_NAME:
        return _is_supported_count_expression_shape(
            expression, value_type, null_operands=form_only
        )
    if function_name == COUNT_DISTINCT_AGGREGATE_NAME:
        return _is_builtin(value_type, "Text") and _is_lower_trim_text_transform_chain(
            expression
        )
    if function_name == STRING_AGGREGATE_NAME:
        return _is_builtin(value_type, "Text")
    if function_name not in {SUM_AGGREGATE_NAME, AVG_AGGREGATE_NAME}:
        return False
    return _is_supported_sum_avg_numeric_expression_shape(
        expression,
        value_type,
    )


def accepts_argument_form(
    function_name: str,
    expression: Expression,
    *,
    let_expansions: Mapping[str, Expression] | None = None,
) -> bool:
    """Return whether an aggregate accepts this argument expression for some
    argument type: a `Text` one for ``count_distinct`` and an `Int` one for
    every other aggregate, which each form it accepts takes."""

    return is_supported_semantic_aggregate_argument_expression(
        function_name,
        expression,
        _TEXT_VALUE_TYPE
        if function_name == COUNT_DISTINCT_AGGREGATE_NAME
        else INT_NULLABLE_VALUE_TYPE,
        let_expansions=let_expansions,
        form_only=True,
    )


def effective_semantic_aggregate_argument_expression(
    function_name: str,
    expression: Expression,
    *,
    let_expansions: Mapping[str, Expression] | None,
) -> Expression:
    """Return the expression shape used for approved aggregate argument checks."""

    if function_name not in LET_EXPANDABLE_AGGREGATE_ARGUMENT_NAMES:
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
        function_name in LET_EXPANDABLE_AGGREGATE_ARGUMENT_NAMES
        and isinstance(expression, NameExpr)
        and let_expansions is not None
        and expression.name in let_expansions
    )


def extremum_reads_let(
    function_name: str,
    expression: Expression,
    let_expansions: Mapping[str, Expression] | None,
    input_schema: RowSchema,
) -> bool:
    """Whether a `min` or `max` argument reads a `let:` name over an input row
    of known shape: a single file keeps their direct-field surface, so the
    name is no direct field there and the argument is otherwise checked with
    the name's binding type. Over an unknown input row, unread `let:` names
    are checked separately."""

    if function_name not in {
        MIN_AGGREGATE_NAME,
        MAX_AGGREGATE_NAME,
        *FLOAT_STATISTIC_AGGREGATE_NAMES,
    }:
        return False
    if not let_expansions or input_schema.is_unknown:
        return False
    pending = [expression]
    while pending:
        node = pending.pop()
        if isinstance(node, NameExpr) and node.name in let_expansions:
            return True
        pending.extend(child_expressions(node))
    return False


def _expand_let_references(
    expression: Expression,
    *,
    let_expansions: Mapping[str, Expression],
    let_stack: frozenset[str],
    memo: dict[tuple[str, frozenset[str]], Expression] | None = None,
) -> Expression:
    if memo is None:
        memo = {}
    if type(expression) not in _KNOWN_EXPRESSIONS:
        raise AssertionError(
            f"Unsupported aggregate expression: {type(expression).__name__}"
        )
    if isinstance(expression, NameExpr) and expression.name in let_expansions:
        if expression.name in let_stack:
            return expression
        # A let read again on the same path expands to the same value; reuse
        # it, so a chain of lets that each read the last twice stays linear.
        key = (expression.name, let_stack)
        if key not in memo:
            memo[key] = _expand_let_references(
                let_expansions[expression.name],
                let_expansions=let_expansions,
                let_stack=let_stack | frozenset((expression.name,)),
                memo=memo,
            )
        return memo[key]
    if isinstance(expression, UnaryExpr):
        return UnaryExpr(
            operator=expression.operator,
            operand=_expand_let_references(
                expression.operand,
                let_expansions=let_expansions,
                let_stack=let_stack,
                memo=memo,
            ),
            span=expression.span,
        )
    if isinstance(expression, BinaryExpr):
        return BinaryExpr(
            left=_expand_let_references(
                expression.left,
                let_expansions=let_expansions,
                let_stack=let_stack,
                memo=memo,
            ),
            operator=expression.operator,
            right=_expand_let_references(
                expression.right,
                let_expansions=let_expansions,
                let_stack=let_stack,
                memo=memo,
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
                    memo=memo,
                )
                for argument in expression.arguments
            ),
            aggregate_order_by=tuple(
                ast.OrderItem(
                    expression=_expand_let_references(
                        item.expression,
                        let_expansions=let_expansions,
                        let_stack=let_stack,
                        memo=memo,
                    ),
                    direction=item.direction,
                    span=item.span,
                )
                for item in expression.aggregate_order_by
            ),
            span=expression.span,
        )
    if isinstance(expression, ComparisonExpr):
        return ComparisonExpr(
            left=_expand_let_references(
                expression.left,
                let_expansions=let_expansions,
                let_stack=let_stack,
                memo=memo,
            ),
            operator=expression.operator,
            right=_expand_let_references(
                expression.right,
                let_expansions=let_expansions,
                let_stack=let_stack,
                memo=memo,
            ),
            span=expression.span,
        )
    if isinstance(expression, BetweenExpr):
        return BetweenExpr(
            value=_expand_let_references(
                expression.value,
                let_expansions=let_expansions,
                let_stack=let_stack,
                memo=memo,
            ),
            lower=_expand_let_references(
                expression.lower,
                let_expansions=let_expansions,
                let_stack=let_stack,
                memo=memo,
            ),
            upper=_expand_let_references(
                expression.upper,
                let_expansions=let_expansions,
                let_stack=let_stack,
                memo=memo,
            ),
            span=expression.span,
        )
    if isinstance(expression, IsNullExpr):
        return IsNullExpr(
            value=_expand_let_references(
                expression.value,
                let_expansions=let_expansions,
                let_stack=let_stack,
                memo=memo,
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
    # A loop, not recursion: an argument with its let bindings inlined may nest
    # up to the PIE-S2328 limit, deeper than the interpreter's recursion limit.
    pending = [expression]
    while pending:
        current = pending.pop()
        if isinstance(current, (NameExpr, DottedNameExpr)):
            value_type = expression_value_types.get(current)
            if value_type is None or value_type.kind is ValueTypeKind.UNKNOWN:
                return True
        else:
            pending.extend(reversed(child_expressions(current)))
    return False


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
    *,
    null_operands: bool,
) -> bool:
    if not is_supported_count_argument(value_type):
        return False

    is_valid, has_field = _count_expression_shape(
        expression, null_operands=null_operands
    )
    return is_valid and has_field


def _count_expression_shape(
    expression: Expression, *, null_operands: bool
) -> tuple[bool, bool]:
    """Return (valid shape, has direct field leaf) for count expressions.

    Without ``null_operands`` an arithmetic `null` operand (`n + null`) is no
    valid shape: it takes the other operand's type, but emission needs a type
    at every part of the argument."""

    if isinstance(expression, (NameExpr, DottedNameExpr)):
        return True, True
    if isinstance(expression, (LiteralExpr, ParameterRefExpr)):
        return True, False
    if isinstance(expression, UnaryExpr):
        if expression.operator not in {"+", "-"}:
            return False, False
        return _count_expression_shape(expression.operand, null_operands=null_operands)
    if isinstance(expression, BinaryExpr):
        if expression.operator not in {"+", "-", "*", "%", "and", "or"}:
            return False, False
        if (
            not null_operands
            and expression.operator in {"+", "-", "*", "%"}
            and any(
                isinstance(operand, LiteralExpr) and operand.value is None
                for operand in (expression.left, expression.right)
            )
        ):
            return False, False
        left_valid, left_has_field = _count_expression_shape(
            expression.left, null_operands=null_operands
        )
        right_valid, right_has_field = _count_expression_shape(
            expression.right, null_operands=null_operands
        )
        return left_valid and right_valid, left_has_field or right_has_field
    if isinstance(expression, CallExpr):
        if not isinstance(expression.callee, NameExpr):
            return False, False
        if expression.callee.name not in {"lower", "trim", "len"}:
            return False, False
        if len(expression.arguments) != 1:
            return False, False
        return _count_expression_shape(
            expression.arguments[0], null_operands=null_operands
        )
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
    if isinstance(expression, ParameterRefExpr):
        return expression.type_name in {"Int", "Float"}, False, True
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
    if function_name == STRING_AGGREGATE_NAME:
        return _is_builtin(value_type, "Text")
    if function_name in FLOAT_STATISTIC_AGGREGATE_NAMES:
        return is_supported_stddev_argument(value_type)
    if function_name in GROUP_TEST_AGGREGATE_NAMES:
        return _is_builtin(value_type, "Bool")
    return False


def is_supported_stddev_argument(value_type: ValueType) -> bool:
    """Return whether `stddev`, `variance`, `pvariance`, `pstdev`, `median`
    and `quantile` accept this direct field argument type."""

    return _is_builtin(value_type, "Int") or _is_builtin(value_type, "Float")


def quantile_fraction_diagnostic(expression: CallExpr) -> Diagnostic | None:
    """PIE-S2104 at the fraction of a two-argument `quantile` that is not a
    Float literal from 0.0 to 1.0."""

    if (
        semantic_aggregate_call_name(expression) != QUANTILE_AGGREGATE_NAME
        or len(expression.arguments) != 2
    ):
        return None
    fraction = expression.arguments[1]
    if type(fraction) is LiteralExpr and type(fraction.value) is float:
        if 0.0 <= fraction.value <= 1.0:
            return None
        message = (
            f"Invalid arguments for aggregate quantile: q {fraction.value!r} is "
            "outside 0.0 to 1.0; write a fraction such as 0.9 for the 90th "
            "percentile"
        )
    else:
        message = (
            "Invalid arguments for aggregate quantile: q must be a Float literal "
            "from 0.0 to 1.0, written in the call, such as quantile(x, 0.9)"
        )
    return _diagnostic(fraction, code="PIE-S2104", message=message)


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

    if function_name == STRING_AGGREGATE_NAME:
        return (
            _TEXT_VALUE_TYPE
            if argument_type is not None and _is_builtin(argument_type, "Text")
            else None
        )
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
    if function_name in FLOAT_STATISTIC_AGGREGATE_NAMES:
        return (
            FLOAT_NULLABLE_VALUE_TYPE
            if argument_type is not None and is_supported_stddev_argument(argument_type)
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


def generator_aggregate_result_value_type(
    function_name: str, argument_type: ValueType
) -> ValueType | None:
    """The type of ``sum`` of a generator, the conditional count or sum of a
    group: an Int, 0 and never None for no matching row; of ``any`` and
    ``all`` of a Bool test, the test of a group: a Bool, never None."""

    if function_name == SUM_AGGREGATE_NAME and _is_builtin(argument_type, "Int"):
        return COUNT_VALUE_TYPE
    if function_name in GROUP_TEST_AGGREGATE_NAMES and _is_builtin(
        argument_type, "Bool"
    ):
        return BOOL_VALUE_TYPE
    return None


def filtered_aggregate_result_value_type(
    function_name: str, argument_types: Sequence[ValueType]
) -> ValueType | None:
    """The type of the internal identities of the conditional count,
    ``filtered_count`` over its Bool test, and sum, ``filtered_sum`` of an
    Int value over its Bool test: an Int, 0 and never None for no match."""

    if function_name in {"group_any", "group_all"}:
        # The test of a group over its Bool test: a Bool, never None.
        return (
            BOOL_VALUE_TYPE
            if len(argument_types) == 1 and _is_builtin(argument_types[0], "Bool")
            else None
        )
    arity = {"filtered_count": 1, "filtered_sum": 2}.get(function_name)
    if (
        arity is None
        or len(argument_types) != arity
        or not _is_builtin(argument_types[-1], "Bool")
    ):
        return None
    if arity == 1:
        return COUNT_VALUE_TYPE
    return generator_aggregate_result_value_type(SUM_AGGREGATE_NAME, argument_types[0])


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
    if name == COUNT_DISTINCT_AGGREGATE_NAME:
        return _diagnostic(
            expression,
            code="PIE-S2309",
            message="Aggregate function count_distinct expects at least 1 "
            f"argument, got {len(expression.arguments)}",
        )
    expected = _expected_arity_text(name)
    # Two arguments are the larger or smaller of two values, which nest.
    hint = (
        f"; for more values, nest two-argument calls: {name}(a, {name}(b, c))"
        if name in {MIN_AGGREGATE_NAME, MAX_AGGREGATE_NAME}
        and len(expression.arguments) > 2
        else ""
    )

    return _diagnostic(
        expression,
        code="PIE-S2309",
        message=(
            f"Aggregate function {name} expects {expected} arguments, "
            f"got {len(expression.arguments)}{hint}"
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
            f"composition around {name}() is not supported yet"
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
    hint: bool = True,
) -> Diagnostic:
    """Report a direct aggregate field argument with an unsupported type;
    with ``hint``, a `sum` of a Bool field names the conditional count."""

    name = callee_name(expression)
    generator = _generator_argument(expression)
    if generator is not None and name in GROUP_TEST_AGGREGATE_NAMES:
        return replace(
            _diagnostic(
                generator.body,
                code="PIE-S2202",
                message=f"Expected Bool expression in {name.upper()} predicate",
            ),
            suggestion=_group_test_body_hint(generator, actual_name),
        )
    if generator is not None:
        binder = generator.binding_name
        return _diagnostic(
            expression,
            code="PIE-S2314",
            message=f"Aggregate function {name} of a generator adds an Int field of "
            f"{binder}, got {actual_name}",
            hint=f"count with `sum(1 for {binder} in group if {binder}."
            f"{generator.body.name})`"
            if actual_name == "Bool" and type(generator.body) is NameExpr
            else None,
        )
    expected = (
        "concrete non-Any"
        if name == COUNT_AGGREGATE_NAME
        else (
            "Bool, Int, Float, Decimal, Text, Date, Timestamp, or UUID"
            if name == COUNT_DISTINCT_AGGREGATE_NAME
            else (
                "Int, Float, Decimal, Date, or Timestamp"
                if name in {MIN_AGGREGATE_NAME, MAX_AGGREGATE_NAME}
                else (
                    "Int or Float"
                    if name in FLOAT_STATISTIC_AGGREGATE_NAMES
                    else "Int, Float, or Decimal"
                )
            )
        )
    )

    argument = expression.arguments[0] if expression.arguments else None
    # The field a direct argument reads, bare or qualified (`sales.paid`).
    field = (
        argument.name
        if type(argument) is NameExpr
        else argument.parts[-1]
        if type(argument) is DottedNameExpr
        else None
    )
    suggestion = None
    if hint and actual_name == "Bool" and field is not None:
        if name == SUM_AGGREGATE_NAME:
            suggestion = f"count with `sum(1 for o in group if o.{field})`"
        elif name in {MAX_AGGREGATE_NAME, MIN_AGGREGATE_NAME}:
            test = "any" if name == MAX_AGGREGATE_NAME else "all"
            suggestion = (
                f"for a test of the group write `{test}(o.{field} for o in group)`"
            )
    return _diagnostic(
        expression,
        code="PIE-S2314",
        message=(
            f"Aggregate function {name} expects {expected} field argument, "
            f"got {actual_name}"
        ),
        hint=suggestion,
    )


def deferred_argument_expression_diagnostic(
    expression: CallExpr, *, hint: bool = True
) -> Diagnostic:
    """Report an aggregate argument expression deferred beyond the MVP; with
    ``hint``, a conditional `sum` or `count` argument names the generator."""

    name = callee_name(expression)
    generator = _generator_argument(expression)
    if generator is not None and name in GROUP_TEST_AGGREGATE_NAMES:
        return replace(
            _diagnostic(
                generator.body,
                code="PIE-S2202",
                message=f"{name.upper()} predicate requires a known Bool expression.",
            ),
            suggestion=_group_test_body_hint(generator, None),
        )
    if generator is not None:
        return _diagnostic(
            expression,
            code="PIE-S2314",
            message=(
                f"Aggregate function {name} of a generator adds an Int field of "
                f"{generator.binding_name}; a Float or Decimal sum is not "
                "available yet"
            ),
        )

    suggestion = None
    if (
        hint
        and name in {SUM_AGGREGATE_NAME, COUNT_AGGREGATE_NAME}
        and len(expression.arguments) == 1
        and type(expression.arguments[0]) is ConditionalExpr
    ):
        suggestion = (
            "write `sum(1 for o in group if ...)`"
            if name == COUNT_AGGREGATE_NAME
            else "write `sum(o.v for o in group if ...)`"
        )
    return _diagnostic(
        expression,
        code="PIE-S2315",
        message=(
            f"Aggregate function {name} requires a direct field argument; "
            "expression arguments are not supported yet"
        ),
        hint=suggestion,
    )


def unknown_row_generator_diagnostic(expression: CallExpr) -> Diagnostic | None:
    """PIE-S2334 for a generator over an input row whose fields are not
    known, such as a source without a shape: its test and summed field need
    their types."""

    generator = _generator_argument(expression)
    if generator is None:
        return None
    return _diagnostic(
        expression,
        code="PIE-S2334",
        message=(
            f"{callee_name(expression)}(... for {generator.binding_name} in group "
            "...) reads an input whose fields are not known; give its source a shape"
        ),
    )


def _generator_argument(expression: CallExpr) -> ast.GeneratorExpr | None:
    arguments = expression.arguments
    if len(arguments) == 1 and type(arguments[0]) is ast.GeneratorExpr:
        return arguments[0]
    return None


def _group_test_body_hint(generator: ast.GeneratorExpr, actual_name: str | None) -> str:
    """The suggestion of a group test whose body is no Bool (its message keeps
    the relation `any` text): a number field's test, else a comparison."""

    body = generator.body
    if type(body) is NameExpr and actual_name in {"Int", "Float", "Decimal"}:
        return (
            f"write the body as a test, such as `{generator.binding_name}."
            f"{body.name} > 0`"
        )
    return "write the body as a test, such as a comparison"


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
    hint: str | None = None,
) -> Diagnostic:
    """A ``hint`` follows the message after `; ` and is the JSON suggestion."""

    span = expression.span
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message if hint is None else f"{message}; {hint}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
        suggestion=hint,
    )


def internal_order_diagnostic(expression: CallExpr) -> Diagnostic | None:
    """PIE-S2104 for a string_agg without its internal ORDER BY.

    Syntax admission already refuses an internal ORDER BY on any other call.
    """

    if callee_name(expression) != "string_agg" or expression.aggregate_order_by:
        return None
    return _diagnostic(
        expression,
        code="PIE-S2104",
        message="Invalid arguments for aggregate string_agg: expected ORDER BY key",
    )
