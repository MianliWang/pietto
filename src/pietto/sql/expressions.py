"""Internal PostgreSQL rendering for the supported Semantic IR expressions."""

from __future__ import annotations

from pietto.ir.model import (
    AggregateCallIR,
    BetweenIR,
    BinaryIR,
    CallIR,
    ComparisonIR,
    ExpressionIR,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    NullabilityIR,
    OrderDirectionIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeKindIR,
    TypeRefIR,
    UnaryIR,
    WindowCallIR,
    WindowFrameBoundIR,
    WindowFrameBoundKindIR,
    WindowFrameExclusionIR,
    WindowFrameIR,
    WindowFrameUnitIR,
    WindowFunctionIdentityIR,
    WindowFunctionRoleIR,
    WindowOrderItemIR,
    WindowNthDirectionIR,
    WindowNullTreatmentIR,
    WindowSpecIR,
)
from pietto.sql.render import (
    quote_identifier,
    quote_qualified_identifier,
    render_literal,
)
from pietto.sql.window_strategy import (
    WindowTargetDialect,
    decide_inline_window_target,
)

_COMPARISON_OPERATORS = {
    "==": "=",
    "!=": "<>",
    "<": "<",
    "<=": "<=",
    ">": ">",
    ">=": ">=",
}
_BINARY_OPERATORS = {
    "and": "AND",
    "or": "OR",
    "+": "+",
    "-": "-",
    "*": "*",
    "/": "/",
    "%": "%",
}
_UNARY_OPERATORS = {
    "+": "+",
    "-": "-",
}
_FUNCTION_NAMES = {
    "lower": "lower",
    "trim": "trim",
    "len": "length",
}
_FUNCTION_ARITIES = {
    "lower": 1,
    "trim": 1,
    "len": 1,
    "matches": 2,
}
_NUMERIC_AGGREGATE_NAMES = {
    "sum": "SUM",
    "avg": "AVG",
}
_SUPPORTED_NUMERIC_AGGREGATE_ARGUMENT_TYPES = frozenset({"Int", "Float", "Decimal"})
_EXTREMA_AGGREGATE_NAMES = {
    "min": "MIN",
    "max": "MAX",
}
_SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES = frozenset(
    {"Int", "Float", "Decimal", "Date", "Timestamp"}
)
_SUPPORTED_COUNT_DISTINCT_ARGUMENT_TYPES = frozenset(
    {"Bool", "Int", "Float", "Decimal", "Text", "Date", "Timestamp", "UUID"}
)
_COUNT_DISTINCT_TRANSFORM_NAMES = frozenset({"lower", "trim"})
_COUNT_EXPRESSION_CALL_NAMES = frozenset({"lower", "trim", "len"})
_WINDOW_FUNCTION_NAMES = {
    "row_number": "ROW_NUMBER",
    "rank": "RANK",
    "dense_rank": "DENSE_RANK",
    "percent_rank": "PERCENT_RANK",
    "cume_dist": "CUME_DIST",
    "ntile": "NTILE",
    "lag": "LAG",
    "lead": "LEAD",
    "first_value": "FIRST_VALUE",
    "last_value": "LAST_VALUE",
    "nth_value": "NTH_VALUE",
}
_ZERO_ARGUMENT_WINDOW_FUNCTIONS = frozenset(
    {"row_number", "rank", "dense_rank", "percent_rank", "cume_dist"}
)


def render_expression_sql(expression: ExpressionIR) -> str:
    """Render one supported Semantic IR expression as PostgreSQL SQL."""

    return _render_expression_sql(expression, nested=False)


def expression_uses_qualified_field(expression: ExpressionIR) -> bool:
    """Return whether an expression contains a qualified field reference."""

    if isinstance(expression, FieldRefIR):
        return bool(expression.qualifier)
    if isinstance(expression, WindowCallIR):
        arguments = getattr(expression, "arguments", ())
        if type(arguments) is tuple and any(
            expression_uses_qualified_field(argument)
            for argument in arguments
            if isinstance(argument, ExpressionIR)
        ):
            return True
        spec = getattr(expression, "spec", None)
        if type(spec) is not WindowSpecIR:
            return False
        partition_by = getattr(spec, "partition_by", ())
        if type(partition_by) is tuple and any(
            expression_uses_qualified_field(partition)
            for partition in partition_by
            if isinstance(partition, ExpressionIR)
        ):
            return True
        order_by = getattr(spec, "order_by", ())
        if type(order_by) is not tuple:
            return False
        return any(
            expression_uses_qualified_field(order_expression)
            for item in order_by
            if type(item) is WindowOrderItemIR
            for order_expression in (getattr(item, "expression", None),)
            if isinstance(order_expression, ExpressionIR)
        )
    if isinstance(expression, AggregateCallIR):
        return any(
            expression_uses_qualified_field(argument)
            for argument in expression.arguments
        )
    if isinstance(expression, CallIR):
        return any(
            expression_uses_qualified_field(argument)
            for argument in expression.arguments
        )
    if isinstance(expression, (ComparisonIR, BinaryIR)):
        return expression_uses_qualified_field(
            expression.left
        ) or expression_uses_qualified_field(expression.right)
    if isinstance(expression, IsNullIR):
        return expression_uses_qualified_field(expression.value)
    if isinstance(expression, BetweenIR):
        return (
            expression_uses_qualified_field(expression.value)
            or expression_uses_qualified_field(expression.lower)
            or expression_uses_qualified_field(expression.upper)
        )
    if isinstance(expression, UnaryIR):
        return expression_uses_qualified_field(expression.operand)
    return False


def _render_expression_sql(expression: ExpressionIR, *, nested: bool) -> str:
    if isinstance(expression, LiteralIR):
        return render_literal(expression.value)
    if isinstance(expression, FieldRefIR):
        if expression.qualifier:
            return quote_qualified_identifier((*expression.qualifier, expression.name))
        return quote_identifier(expression.name)
    if isinstance(expression, AggregateCallIR):
        return _render_aggregate_call(expression)
    if isinstance(expression, WindowCallIR):
        if nested:
            raise ValueError(
                "PostgreSQL window calls are supported only as direct projections"
            )
        return render_window_call_sql(expression)
    if isinstance(expression, CallIR):
        sql = _render_call(expression)
        return f"({sql})" if nested and expression.callee == "matches" else sql
    if isinstance(expression, ComparisonIR):
        operator = _supported_operator(
            _COMPARISON_OPERATORS,
            expression.operator,
            "comparison",
        )
        sql = (
            f"{_render_expression_sql(expression.left, nested=True)} {operator} "
            f"{_render_expression_sql(expression.right, nested=True)}"
        )
    elif isinstance(expression, IsNullIR):
        operator = "IS NOT NULL" if expression.negated else "IS NULL"
        sql = f"{_render_expression_sql(expression.value, nested=True)} {operator}"
    elif isinstance(expression, BetweenIR):
        sql = (
            f"{_render_expression_sql(expression.value, nested=True)} BETWEEN "
            f"{_render_expression_sql(expression.lower, nested=True)} AND "
            f"{_render_expression_sql(expression.upper, nested=True)}"
        )
    elif isinstance(expression, UnaryIR):
        operator = _supported_operator(
            _UNARY_OPERATORS,
            expression.operator,
            "unary",
        )
        sql = f"{operator}{_render_expression_sql(expression.operand, nested=True)}"
    elif isinstance(expression, BinaryIR):
        operator = _supported_operator(
            _BINARY_OPERATORS,
            expression.operator,
            "binary",
        )
        sql = (
            f"{_render_expression_sql(expression.left, nested=True)} {operator} "
            f"{_render_expression_sql(expression.right, nested=True)}"
        )
    else:
        raise ValueError(
            f"Unsupported PostgreSQL expression IR node: {type(expression).__name__}"
        )

    return f"({sql})" if nested else sql


def render_window_call_sql(
    expression: WindowCallIR,
    *,
    over_sql: str | None = None,
) -> str:
    """Render one independently validated PostgreSQL window call."""

    if type(getattr(expression, "span", None)) is not SourceSpan:
        raise ValueError("PostgreSQL window call requires an exact source span")
    if type(getattr(expression, "value_type", None)) is not TypeRefIR:
        raise ValueError("PostgreSQL window call requires an exact value type")
    identity = getattr(expression, "identity", None)
    if type(identity) is not WindowFunctionIdentityIR:
        raise ValueError("PostgreSQL window call requires an exact identity")
    namespace = getattr(identity, "namespace", None)
    name = getattr(identity, "name", None)
    role = getattr(identity, "role", None)
    if type(namespace) is not tuple or namespace != ():
        raise ValueError("PostgreSQL window identity requires an empty namespace")
    if type(name) is not str or name not in _WINDOW_FUNCTION_NAMES:
        raise ValueError("PostgreSQL window identity is unsupported")
    if role is not WindowFunctionRoleIR.WINDOW_FUNCTION:
        raise ValueError("PostgreSQL window identity requires the window role")

    arguments = getattr(expression, "arguments", None)
    if type(arguments) is not tuple:
        raise ValueError("PostgreSQL window arguments require an exact tuple")
    if name in _ZERO_ARGUMENT_WINDOW_FUNCTIONS:
        valid_arity = len(arguments) == 0
    elif name == "ntile":
        valid_arity = len(arguments) == 1
    elif name in {"first_value", "last_value"}:
        valid_arity = len(arguments) == 1
    elif name == "nth_value":
        valid_arity = len(arguments) == 2
    else:
        valid_arity = len(arguments) in {1, 2, 3}
    if not valid_arity:
        raise ValueError(f"PostgreSQL window function {name} has invalid arity")
    if any(
        not isinstance(argument, ExpressionIR) or isinstance(argument, WindowCallIR)
        for argument in arguments
    ):
        raise ValueError("PostgreSQL window arguments contain an invalid expression")

    spec = getattr(expression, "spec", None)
    if type(spec) is not WindowSpecIR:
        raise ValueError("PostgreSQL window call requires an exact specification")
    if type(getattr(spec, "span", None)) is not SourceSpan:
        raise ValueError("PostgreSQL window specification requires an exact span")
    partition_by = getattr(spec, "partition_by", None)
    order_by = getattr(spec, "order_by", None)
    if type(partition_by) is not tuple or type(order_by) is not tuple:
        raise ValueError("PostgreSQL window specification requires exact tuples")
    if not order_by:
        raise ValueError("PostgreSQL window specification requires local ORDER BY")
    if any(
        not isinstance(partition, ExpressionIR) or isinstance(partition, WindowCallIR)
        for partition in partition_by
    ):
        raise ValueError("PostgreSQL window partition contains an invalid expression")
    _validate_window_order_items(order_by)
    decision = decide_inline_window_target(
        expression,
        WindowTargetDialect.POSTGRESQL,
    )
    if not decision.supported:
        raise ValueError(decision.failure_reason)
    null_treatment = getattr(expression, "null_treatment", None)
    nth_direction = getattr(expression, "nth_direction", None)
    if name in {"lag", "lead", "first_value", "last_value", "nth_value"}:
        if type(null_treatment) is not WindowNullTreatmentIR:
            raise ValueError("PostgreSQL value window requires NULL treatment")
    elif null_treatment is not None:
        raise ValueError("PostgreSQL function forbids NULL treatment")
    if name == "nth_value":
        if type(nth_direction) is not WindowNthDirectionIR:
            raise ValueError("PostgreSQL nth_value requires a direction")
    elif nth_direction is not None:
        raise ValueError("PostgreSQL non-nth function forbids FROM direction")

    argument_sql = ", ".join(
        _render_expression_sql(argument, nested=True) for argument in arguments
    )
    if over_sql is None:
        components = render_window_components_sql(
            partition_by,
            order_by,
            getattr(spec, "frame", None),
        )
        over_sql = f"({' '.join(components)})"
    if type(over_sql) is not str or not over_sql:
        raise ValueError("PostgreSQL window OVER SQL must be nonempty")
    return f"{_WINDOW_FUNCTION_NAMES[name]}({argument_sql}) OVER {over_sql}"


def render_window_components_sql(
    partition_by: tuple[ExpressionIR, ...],
    order_by: tuple[WindowOrderItemIR, ...],
    frame: WindowFrameIR | None,
) -> tuple[str, ...]:
    """Render exact target-neutral window components without an OVER wrapper."""

    if type(partition_by) is not tuple or any(
        not isinstance(item, ExpressionIR) for item in partition_by
    ):
        raise ValueError("PostgreSQL window partition requires exact expressions")
    if type(order_by) is not tuple:
        raise ValueError("PostgreSQL window order requires an exact tuple")
    _validate_window_order_items(order_by)
    clauses: list[str] = []
    if partition_by:
        clauses.append(
            "PARTITION BY "
            + ", ".join(
                _render_expression_sql(partition, nested=True)
                for partition in partition_by
            )
        )
    if order_by:
        clauses.append(
            "ORDER BY "
            + ", ".join(_render_window_order_item(item) for item in order_by)
        )
    if frame is not None:
        clauses.append(_render_window_frame(frame))
    return tuple(clauses)


def _render_window_frame(frame: WindowFrameIR) -> str:
    if type(frame) is not WindowFrameIR:
        raise ValueError("PostgreSQL window frame must be exact")
    if type(frame.unit) is not WindowFrameUnitIR:
        raise ValueError("PostgreSQL window frame unit must be exact")
    offset_bounds = tuple(
        bound
        for bound in (frame.start, frame.end)
        if bound.kind
        in {
            WindowFrameBoundKindIR.OFFSET_PRECEDING,
            WindowFrameBoundKindIR.OFFSET_FOLLOWING,
        }
    )
    if frame.unit is WindowFrameUnitIR.RANGE and offset_bounds:
        raise ValueError("PostgreSQL RANGE offsets require Phase 64 evidence")
    if any(
        type(bound.offset) is not LiteralIR
        or type(bound.offset.value) is not int
        or bound.offset.value < 0
        for bound in offset_bounds
    ):
        raise ValueError("PostgreSQL frame offsets require nonnegative Int literals")
    start = _render_window_frame_bound(frame.start)
    end = _render_window_frame_bound(frame.end)
    if frame.frame_is_explicit and not frame.end_is_explicit:
        result = f"{frame.unit.value} {start}"
    else:
        result = f"{frame.unit.value} BETWEEN {start} AND {end}"
    if type(frame.exclusion) is not WindowFrameExclusionIR:
        raise ValueError("PostgreSQL window exclusion must be exact")
    return f"{result} EXCLUDE {frame.exclusion.value}"


def _render_window_frame_bound(bound: WindowFrameBoundIR) -> str:
    if type(bound) is not WindowFrameBoundIR:
        raise ValueError("PostgreSQL window frame bound must be exact")
    if bound.kind is WindowFrameBoundKindIR.OFFSET_PRECEDING:
        assert bound.offset is not None
        return f"{_render_expression_sql(bound.offset, nested=True)} PRECEDING"
    if bound.kind is WindowFrameBoundKindIR.OFFSET_FOLLOWING:
        assert bound.offset is not None
        return f"{_render_expression_sql(bound.offset, nested=True)} FOLLOWING"
    return bound.kind.value


def _validate_window_order_items(order_by: tuple[WindowOrderItemIR, ...]) -> None:
    for item in order_by:
        if type(item) is not WindowOrderItemIR:
            raise ValueError("PostgreSQL window order requires exact items")
        if type(getattr(item, "span", None)) is not SourceSpan:
            raise ValueError("PostgreSQL window order item requires an exact span")
        order_expression = getattr(item, "expression", None)
        if not isinstance(order_expression, ExpressionIR) or isinstance(
            order_expression, WindowCallIR
        ):
            raise ValueError("PostgreSQL window order contains an invalid expression")
        direction = getattr(item, "direction", None)
        if type(direction) is not OrderDirectionIR:
            raise ValueError("PostgreSQL window order direction is invalid")
        direction_is_explicit = getattr(item, "direction_is_explicit", None)
        if type(direction_is_explicit) is not bool:
            raise ValueError(
                "PostgreSQL window order explicitness requires an exact bool"
            )
        if not direction_is_explicit and direction is not OrderDirectionIR.ASC:
            raise ValueError(
                "PostgreSQL omitted window order direction must resolve to ASC"
            )


def _render_window_order_item(item: WindowOrderItemIR) -> str:
    return (
        f"{_render_expression_sql(item.expression, nested=True)} {item.direction.value}"
    )


def _render_aggregate_call(expression: AggregateCallIR) -> str:
    if expression.function == "count":
        return _render_count_aggregate(expression)
    if expression.function == "count_distinct":
        return _render_count_distinct_aggregate(expression)
    function_name = _EXTREMA_AGGREGATE_NAMES.get(expression.function)
    if function_name is not None:
        return _render_extrema_aggregate(expression, function_name=function_name)
    function_name = _NUMERIC_AGGREGATE_NAMES.get(expression.function)
    if function_name is None:
        raise ValueError(
            f"Unsupported PostgreSQL aggregate call: {expression.function}"
        )
    return _render_numeric_aggregate(expression, function_name=function_name)


def _render_count_aggregate(expression: AggregateCallIR) -> str:
    if not _has_builtin_type(expression, "Int", NullabilityIR.NON_NULL):
        raise ValueError("PostgreSQL aggregate count expects Int non-null result")
    if not expression.arguments:
        return "COUNT(*)"
    if len(expression.arguments) != 1:
        raise ValueError("PostgreSQL aggregate count expects 0 or 1 argument(s)")
    argument = expression.arguments[0]
    if (
        isinstance(argument, FieldRefIR)
        and argument.field is not None
        and not (
            argument.value_type.canonical_kind is TypeKindIR.BUILTIN
            and argument.value_type.canonical_name != "Any"
        )
    ):
        raise ValueError(
            "PostgreSQL aggregate count supports only concrete non-Any field arguments"
        )
    if not _is_count_argument_expression(argument):
        raise ValueError(
            "PostgreSQL aggregate count expects a direct field argument or approved "
            "field-bearing expression argument"
        )
    return f"COUNT({_render_expression_sql(argument, nested=True)})"


def _render_count_distinct_aggregate(expression: AggregateCallIR) -> str:
    if not _has_builtin_type(expression, "Int", NullabilityIR.NON_NULL):
        raise ValueError(
            "PostgreSQL aggregate count_distinct expects Int non-null result"
        )
    if len(expression.arguments) != 1:
        raise ValueError("PostgreSQL aggregate count_distinct expects 1 argument(s)")
    argument = expression.arguments[0]

    if isinstance(argument, FieldRefIR):
        if argument.field is None:
            raise ValueError(
                "PostgreSQL aggregate count_distinct expects a resolved field argument"
            )
        argument_type = argument.value_type.canonical_name
        if (
            argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
            or argument_type not in _SUPPORTED_COUNT_DISTINCT_ARGUMENT_TYPES
        ):
            raise ValueError(
                "PostgreSQL aggregate count_distinct supports only Bool, Int, "
                "Float, Decimal, Text, Date, Timestamp, or UUID field arguments"
            )
    elif not _is_count_distinct_text_transform_argument(argument):
        raise ValueError(
            "PostgreSQL aggregate count_distinct expects a direct field or "
            "lower/trim Text transform argument"
        )

    return f"COUNT(DISTINCT {_render_expression_sql(argument, nested=True)})"


def _render_numeric_aggregate(
    expression: AggregateCallIR,
    *,
    function_name: str,
) -> str:
    if len(expression.arguments) != 1:
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    argument_type = _numeric_aggregate_argument_type(argument)
    if argument_type is None:
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} expects a field-only "
            "Int, Float, or Decimal expression argument"
        )

    if argument_type == "Decimal":
        expected_result_type = "Decimal"
    elif expression.function == "sum" and argument_type == "Int":
        expected_result_type = "Int"
    else:
        expected_result_type = "Float"
    if not _has_builtin_type(
        expression,
        expected_result_type,
        NullabilityIR.NULLABLE,
    ):
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} result type does not "
            "match approved logical shape"
        )
    return f"{function_name}({_render_expression_sql(argument, nested=True)})"


def _numeric_aggregate_argument_type(expression: ExpressionIR) -> str | None:
    expression_type, has_field, has_literal = _numeric_aggregate_argument_shape(
        expression
    )
    if expression_type is None:
        return None
    if has_literal and (not has_field or expression_type not in {"Int", "Float"}):
        return None
    return expression_type


def _numeric_aggregate_argument_shape(
    expression: ExpressionIR,
) -> tuple[str | None, bool, bool]:
    """Return (builtin type, has resolved field, has Int/Float literal)."""

    expression_type = _builtin_type_name(expression)
    if expression_type not in _SUPPORTED_NUMERIC_AGGREGATE_ARGUMENT_TYPES:
        return None, False, False

    if isinstance(expression, FieldRefIR):
        if expression.field is None:
            return None, False, False
        return expression_type, True, False

    if isinstance(expression, LiteralIR):
        if type(expression.value) is int and expression_type == "Int":
            return expression_type, False, True
        if type(expression.value) is float and expression_type == "Float":
            return expression_type, False, True
        return None, False, False

    if isinstance(expression, UnaryIR):
        if expression.operator not in _UNARY_OPERATORS:
            return None, False, False
        (
            operand_type,
            operand_has_field,
            operand_has_literal,
        ) = _numeric_aggregate_argument_shape(expression.operand)
        if operand_type != expression_type:
            return None, False, False
        return expression_type, operand_has_field, operand_has_literal

    if isinstance(expression, BinaryIR):
        if expression.operator not in {"+", "-", "*"}:
            return None, False, False
        left_type, left_has_field, left_has_literal = _numeric_aggregate_argument_shape(
            expression.left
        )
        right_type, right_has_field, right_has_literal = (
            _numeric_aggregate_argument_shape(expression.right)
        )
        if left_type is None or right_type is None:
            return None, False, False
        if expression_type == "Decimal":
            if expression.operator == "*":
                return None, False, False
            if {left_type, right_type} - {"Decimal", "Int"}:
                return None, False, False
            if "Decimal" not in {left_type, right_type}:
                return None, False, False
            return (
                expression_type,
                left_has_field or right_has_field,
                left_has_literal or right_has_literal,
            )
        if expression_type == "Int":
            if left_type == "Int" and right_type == "Int":
                return (
                    expression_type,
                    left_has_field or right_has_field,
                    left_has_literal or right_has_literal,
                )
            return None, False, False
        if expression_type == "Float" and {left_type, right_type} <= {"Int", "Float"}:
            return (
                expression_type,
                left_has_field or right_has_field,
                left_has_literal or right_has_literal,
            )

    return None, False, False


def _is_count_distinct_text_transform_argument(expression: ExpressionIR) -> bool:
    if not isinstance(expression, CallIR):
        return False
    if _builtin_type_name(expression) != "Text":
        return False
    if expression.callee not in _COUNT_DISTINCT_TRANSFORM_NAMES:
        return False
    expected_symbol = SymbolId(SymbolNamespace.CALLABLE, expression.callee)
    if expression.callee_symbol != expected_symbol:
        return False
    if len(expression.arguments) != 1:
        return False
    argument = expression.arguments[0]
    if isinstance(argument, FieldRefIR):
        return argument.field is not None and _builtin_type_name(argument) == "Text"
    return _is_count_distinct_text_transform_argument(argument)


def _is_count_argument_expression(expression: ExpressionIR) -> bool:
    is_valid, has_field = _count_argument_expression_shape(expression)
    return is_valid and has_field


def _count_argument_expression_shape(
    expression: ExpressionIR,
) -> tuple[bool, bool]:
    """Return (valid shape, has resolved field leaf) for count expressions."""

    if _builtin_type_name(expression) in {None, "Any"}:
        return False, False

    if isinstance(expression, FieldRefIR):
        return expression.field is not None, expression.field is not None
    if isinstance(expression, LiteralIR):
        return True, False
    if isinstance(expression, UnaryIR):
        if expression.operator not in _UNARY_OPERATORS:
            return False, False
        return _count_argument_expression_shape(expression.operand)
    if isinstance(expression, BinaryIR):
        if expression.operator not in {"+", "-", "*", "%", "and", "or"}:
            return False, False
        left_valid, left_has_field = _count_argument_expression_shape(expression.left)
        right_valid, right_has_field = _count_argument_expression_shape(
            expression.right
        )
        return left_valid and right_valid, left_has_field or right_has_field
    if isinstance(expression, CallIR):
        if expression.callee not in _COUNT_EXPRESSION_CALL_NAMES:
            return False, False
        expected_symbol = SymbolId(SymbolNamespace.CALLABLE, expression.callee)
        if expression.callee_symbol != expected_symbol:
            return False, False
        if len(expression.arguments) != 1:
            return False, False
        return _count_argument_expression_shape(expression.arguments[0])
    return False, False


def _builtin_type_name(expression: ExpressionIR) -> str | None:
    if expression.value_type.canonical_kind is not TypeKindIR.BUILTIN:
        return None
    return expression.value_type.canonical_name


def _render_extrema_aggregate(
    expression: AggregateCallIR,
    *,
    function_name: str,
) -> str:
    if len(expression.arguments) != 1:
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    if not isinstance(argument, FieldRefIR) or argument.field is None:
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} expects a direct field "
            "argument"
        )
    argument_type = argument.value_type.canonical_name
    if (
        argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
        or argument_type not in _SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES
    ):
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} supports only Int, "
            "Float, Decimal, Date, or Timestamp field arguments"
        )

    if not _has_builtin_type(expression, argument_type, NullabilityIR.NULLABLE):
        raise ValueError(
            f"PostgreSQL aggregate {expression.function} result type does not "
            "match approved logical shape"
        )
    return f"{function_name}({_render_expression_sql(argument, nested=True)})"


def _has_builtin_type(
    expression: ExpressionIR,
    canonical_name: str,
    nullability: NullabilityIR,
) -> bool:
    return (
        expression.value_type.canonical_kind is TypeKindIR.BUILTIN
        and expression.value_type.canonical_name == canonical_name
        and expression.value_type.nullability is nullability
    )


def _render_call(expression: CallIR) -> str:
    if expression.callee not in _FUNCTION_ARITIES:
        raise ValueError(f"Unsupported PostgreSQL function call: {expression.callee}")
    expected_arity = _FUNCTION_ARITIES[expression.callee]
    if len(expression.arguments) != expected_arity:
        raise ValueError(
            f"PostgreSQL function {expression.callee} expects "
            f"{expected_arity} argument(s)"
        )

    arguments = tuple(
        _render_expression_sql(argument, nested=True)
        for argument in expression.arguments
    )
    if expression.callee == "matches":
        return f"{arguments[0]} ~ {arguments[1]}"
    return f"{_FUNCTION_NAMES[expression.callee]}({arguments[0]})"


def _supported_operator(
    supported: dict[str, str],
    operator: str,
    kind: str,
) -> str:
    try:
        return supported[operator]
    except KeyError as error:
        raise ValueError(
            f"Unsupported PostgreSQL {kind} operator: {operator}"
        ) from error
