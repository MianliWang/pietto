"""Internal MySQL rendering for the approved Semantic IR expressions."""

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
from pietto.sql.mysql_render import (
    MySqlRenderError,
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
    "lower": "LOWER",
    "trim": "TRIM",
    "len": "CHAR_LENGTH",
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


def render_mysql_expression(expression: ExpressionIR) -> str:
    """Render one supported Semantic IR expression as MySQL SQL."""

    return _render_mysql_expression(expression, nested=False)


def _render_mysql_expression(expression: ExpressionIR, *, nested: bool) -> str:
    if isinstance(expression, LiteralIR):
        return render_literal(expression.value)
    if isinstance(expression, FieldRefIR):
        if expression.qualifier:
            return quote_qualified_identifier((*expression.qualifier, expression.name))
        return quote_identifier(expression.name, context="column identifier")
    if isinstance(expression, AggregateCallIR):
        return _render_aggregate_call(expression)
    if isinstance(expression, WindowCallIR):
        if nested:
            raise MySqlRenderError(
                "MySQL window calls are supported only as direct projections"
            )
        return render_mysql_window_call(expression)
    if isinstance(expression, CallIR):
        return _render_call(expression)
    if isinstance(expression, ComparisonIR):
        operator = _supported_operator(
            _COMPARISON_OPERATORS,
            expression.operator,
            "comparison",
        )
        sql = (
            f"{_render_mysql_expression(expression.left, nested=True)} {operator} "
            f"{_render_mysql_expression(expression.right, nested=True)}"
        )
    elif isinstance(expression, IsNullIR):
        operator = "IS NOT NULL" if expression.negated else "IS NULL"
        sql = f"{_render_mysql_expression(expression.value, nested=True)} {operator}"
    elif isinstance(expression, BetweenIR):
        sql = (
            f"{_render_mysql_expression(expression.value, nested=True)} BETWEEN "
            f"{_render_mysql_expression(expression.lower, nested=True)} AND "
            f"{_render_mysql_expression(expression.upper, nested=True)}"
        )
    elif isinstance(expression, UnaryIR):
        operator = _supported_operator(
            _UNARY_OPERATORS,
            expression.operator,
            "unary",
        )
        sql = f"{operator}{_render_mysql_expression(expression.operand, nested=True)}"
    elif isinstance(expression, BinaryIR):
        operator = _supported_operator(
            _BINARY_OPERATORS,
            expression.operator,
            "binary",
        )
        sql = (
            f"{_render_mysql_expression(expression.left, nested=True)} {operator} "
            f"{_render_mysql_expression(expression.right, nested=True)}"
        )
    else:
        raise MySqlRenderError(
            f"Unsupported MySQL expression IR node: {type(expression).__name__}"
        )

    return f"({sql})" if nested else sql


def render_mysql_window_call(
    expression: WindowCallIR,
    *,
    over_sql: str | None = None,
) -> str:
    """Render one independently validated private-MySQL window call."""

    if type(getattr(expression, "span", None)) is not SourceSpan:
        raise MySqlRenderError("MySQL window call requires an exact source span")
    if type(getattr(expression, "value_type", None)) is not TypeRefIR:
        raise MySqlRenderError("MySQL window call requires an exact value type")
    identity = getattr(expression, "identity", None)
    if type(identity) is not WindowFunctionIdentityIR:
        raise MySqlRenderError("MySQL window call requires an exact identity")
    namespace = getattr(identity, "namespace", None)
    name = getattr(identity, "name", None)
    role = getattr(identity, "role", None)
    if type(namespace) is not tuple or namespace != ():
        raise MySqlRenderError("MySQL window identity requires an empty namespace")
    if type(name) is not str or name not in _WINDOW_FUNCTION_NAMES:
        raise MySqlRenderError("MySQL window identity is unsupported")
    if role is not WindowFunctionRoleIR.WINDOW_FUNCTION:
        raise MySqlRenderError("MySQL window identity requires the window role")

    arguments = getattr(expression, "arguments", None)
    if type(arguments) is not tuple:
        raise MySqlRenderError("MySQL window arguments require an exact tuple")
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
        raise MySqlRenderError(f"MySQL window function {name} has invalid arity")
    if any(
        not isinstance(argument, ExpressionIR) or isinstance(argument, WindowCallIR)
        for argument in arguments
    ):
        raise MySqlRenderError("MySQL window arguments contain an invalid expression")

    spec = getattr(expression, "spec", None)
    if type(spec) is not WindowSpecIR:
        raise MySqlRenderError("MySQL window call requires an exact specification")
    if type(getattr(spec, "span", None)) is not SourceSpan:
        raise MySqlRenderError("MySQL window specification requires an exact span")
    partition_by = getattr(spec, "partition_by", None)
    order_by = getattr(spec, "order_by", None)
    if type(partition_by) is not tuple or type(order_by) is not tuple:
        raise MySqlRenderError("MySQL window specification requires exact tuples")
    if not order_by:
        raise MySqlRenderError("MySQL window specification requires local ORDER BY")
    if any(
        not isinstance(partition, ExpressionIR) or isinstance(partition, WindowCallIR)
        for partition in partition_by
    ):
        raise MySqlRenderError("MySQL window partition contains an invalid expression")
    _validate_mysql_window_order_items(order_by)
    decision = decide_inline_window_target(expression, WindowTargetDialect.MYSQL)
    if not decision.supported:
        raise MySqlRenderError(decision.failure_reason)
    null_treatment = getattr(expression, "null_treatment", None)
    nth_direction = getattr(expression, "nth_direction", None)
    if name in {"lag", "lead", "first_value", "last_value", "nth_value"}:
        if type(null_treatment) is not WindowNullTreatmentIR:
            raise MySqlRenderError("MySQL value window requires NULL treatment")
    elif null_treatment is not None:
        raise MySqlRenderError("MySQL function forbids NULL treatment")
    if name == "nth_value":
        if type(nth_direction) is not WindowNthDirectionIR:
            raise MySqlRenderError("MySQL nth_value requires a direction")
    elif nth_direction is not None:
        raise MySqlRenderError("MySQL non-nth function forbids FROM direction")

    argument_sql = ", ".join(
        _render_mysql_expression(argument, nested=True) for argument in arguments
    )
    if over_sql is None:
        components = render_mysql_window_components(
            partition_by,
            order_by,
            getattr(spec, "frame", None),
        )
        over_sql = f"({' '.join(components)})"
    if type(over_sql) is not str or not over_sql:
        raise MySqlRenderError("MySQL window OVER SQL must be nonempty")
    modifiers: list[str] = []
    if name == "nth_value" and expression.nth_direction_is_explicit:
        modifiers.append("FROM FIRST")
    if null_treatment is not None and expression.null_treatment_is_explicit:
        modifiers.append("RESPECT NULLS")
    suffix = "" if not modifiers else " " + " ".join(modifiers)
    return f"{_WINDOW_FUNCTION_NAMES[name]}({argument_sql}){suffix} OVER {over_sql}"


def render_mysql_window_components(
    partition_by: tuple[ExpressionIR, ...],
    order_by: tuple[WindowOrderItemIR, ...],
    frame: WindowFrameIR | None,
) -> tuple[str, ...]:
    if type(partition_by) is not tuple or any(
        not isinstance(item, ExpressionIR) for item in partition_by
    ):
        raise MySqlRenderError("MySQL window partition requires exact expressions")
    if type(order_by) is not tuple:
        raise MySqlRenderError("MySQL window order requires an exact tuple")
    _validate_mysql_window_order_items(order_by)
    clauses: list[str] = []
    if partition_by:
        clauses.append(
            "PARTITION BY "
            + ", ".join(
                _render_mysql_expression(partition, nested=True)
                for partition in partition_by
            )
        )
    if order_by:
        clauses.append(
            "ORDER BY "
            + ", ".join(_render_mysql_window_order_item(item) for item in order_by)
        )
    if frame is not None:
        clauses.append(_render_mysql_window_frame(frame))
    return tuple(clauses)


def _render_mysql_window_frame(frame: WindowFrameIR) -> str:
    if type(frame) is not WindowFrameIR:
        raise MySqlRenderError("MySQL window frame must be exact")
    if type(frame.unit) is not WindowFrameUnitIR:
        raise MySqlRenderError("MySQL window frame unit must be exact")
    if frame.unit is WindowFrameUnitIR.GROUPS:
        raise MySqlRenderError("MySQL does not support GROUPS frames")
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
        raise MySqlRenderError("MySQL RANGE offsets require Phase 64 evidence")
    if any(
        type(bound.offset) is not LiteralIR
        or type(bound.offset.value) is not int
        or bound.offset.value < 0
        for bound in offset_bounds
    ):
        raise MySqlRenderError("MySQL frame offsets require nonnegative Int literals")
    if (
        frame.exclusion is not WindowFrameExclusionIR.NO_OTHERS
        or frame.exclusion_is_explicit
    ):
        raise MySqlRenderError("MySQL does not support authored EXCLUDE frames")
    start = _render_mysql_window_frame_bound(frame.start)
    end = _render_mysql_window_frame_bound(frame.end)
    if frame.frame_is_explicit and not frame.end_is_explicit:
        return f"{frame.unit.value} {start}"
    return f"{frame.unit.value} BETWEEN {start} AND {end}"


def _render_mysql_window_frame_bound(bound: WindowFrameBoundIR) -> str:
    if type(bound) is not WindowFrameBoundIR:
        raise MySqlRenderError("MySQL window frame bound must be exact")
    if bound.kind is WindowFrameBoundKindIR.OFFSET_PRECEDING:
        assert bound.offset is not None
        return f"{_render_mysql_expression(bound.offset, nested=True)} PRECEDING"
    if bound.kind is WindowFrameBoundKindIR.OFFSET_FOLLOWING:
        assert bound.offset is not None
        return f"{_render_mysql_expression(bound.offset, nested=True)} FOLLOWING"
    return bound.kind.value


def _validate_mysql_window_order_items(
    order_by: tuple[WindowOrderItemIR, ...],
) -> None:
    for item in order_by:
        if type(item) is not WindowOrderItemIR:
            raise MySqlRenderError("MySQL window order requires exact items")
        if type(getattr(item, "span", None)) is not SourceSpan:
            raise MySqlRenderError("MySQL window order item requires an exact span")
        order_expression = getattr(item, "expression", None)
        if not isinstance(order_expression, ExpressionIR) or isinstance(
            order_expression, WindowCallIR
        ):
            raise MySqlRenderError("MySQL window order contains an invalid expression")
        direction = getattr(item, "direction", None)
        if type(direction) is not OrderDirectionIR:
            raise MySqlRenderError("MySQL window order direction is invalid")
        direction_is_explicit = getattr(item, "direction_is_explicit", None)
        if type(direction_is_explicit) is not bool:
            raise MySqlRenderError(
                "MySQL window order explicitness requires an exact bool"
            )
        if not direction_is_explicit and direction is not OrderDirectionIR.ASC:
            raise MySqlRenderError(
                "MySQL omitted window order direction must resolve to ASC"
            )


def _render_mysql_window_order_item(item: WindowOrderItemIR) -> str:
    return (
        f"{_render_mysql_expression(item.expression, nested=True)} "
        f"{item.direction.value}"
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
        raise MySqlRenderError(
            f"Unsupported MySQL aggregate call: {expression.function}"
        )
    return _render_numeric_aggregate(expression, function_name=function_name)


def _render_count_aggregate(expression: AggregateCallIR) -> str:
    if not _has_builtin_type(expression, "Int", NullabilityIR.NON_NULL):
        raise MySqlRenderError("MySQL aggregate count expects Int non-null result")
    if not expression.arguments:
        return "COUNT(*)"
    if len(expression.arguments) != 1:
        raise MySqlRenderError("MySQL aggregate count expects 0 or 1 argument(s)")
    argument = expression.arguments[0]
    if (
        isinstance(argument, FieldRefIR)
        and argument.field is not None
        and not (
            argument.value_type.canonical_kind is TypeKindIR.BUILTIN
            and argument.value_type.canonical_name != "Any"
        )
    ):
        raise MySqlRenderError(
            "MySQL aggregate count supports only concrete non-Any field arguments"
        )
    if not _is_count_argument_expression(argument):
        raise MySqlRenderError(
            "MySQL aggregate count expects a direct field argument or approved "
            "field-bearing expression argument"
        )
    return f"COUNT({_render_mysql_expression(argument, nested=True)})"


def _render_count_distinct_aggregate(expression: AggregateCallIR) -> str:
    if not _has_builtin_type(expression, "Int", NullabilityIR.NON_NULL):
        raise MySqlRenderError(
            "MySQL aggregate count_distinct expects Int non-null result"
        )
    if len(expression.arguments) != 1:
        raise MySqlRenderError("MySQL aggregate count_distinct expects 1 argument(s)")
    argument = expression.arguments[0]

    if isinstance(argument, FieldRefIR):
        if argument.field is None:
            raise MySqlRenderError(
                "MySQL aggregate count_distinct expects a resolved field argument"
            )
        argument_type = argument.value_type.canonical_name
        if (
            argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
            or argument_type not in _SUPPORTED_COUNT_DISTINCT_ARGUMENT_TYPES
        ):
            raise MySqlRenderError(
                "MySQL aggregate count_distinct supports only Bool, Int, Float, "
                "Decimal, Text, Date, Timestamp, or UUID field arguments"
            )
    elif not _is_count_distinct_text_transform_argument(argument):
        raise MySqlRenderError(
            "MySQL aggregate count_distinct expects a direct field or lower/trim "
            "Text transform argument"
        )

    return f"COUNT(DISTINCT {_render_mysql_expression(argument, nested=True)})"


def _render_numeric_aggregate(
    expression: AggregateCallIR,
    *,
    function_name: str,
) -> str:
    if len(expression.arguments) != 1:
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    argument_type = _numeric_aggregate_argument_type(argument)
    if argument_type is None:
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects a field-only Int, "
            "Float, or Decimal expression argument"
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
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} result type does not match "
            "approved logical shape"
        )
    return f"{function_name}({_render_mysql_expression(argument, nested=True)})"


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
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    if not isinstance(argument, FieldRefIR) or argument.field is None:
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects a direct field argument"
        )
    argument_type = argument.value_type.canonical_name
    if (
        argument.value_type.canonical_kind is not TypeKindIR.BUILTIN
        or argument_type not in _SUPPORTED_EXTREMA_AGGREGATE_ARGUMENT_TYPES
    ):
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} supports only Int, Float, "
            "Decimal, Date, or Timestamp field arguments"
        )

    if not _has_builtin_type(expression, argument_type, NullabilityIR.NULLABLE):
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} result type does not match "
            "approved logical shape"
        )
    return f"{function_name}({_render_mysql_expression(argument, nested=True)})"


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
    if expression.callee == "matches":
        raise MySqlRenderError("Unsupported MySQL function call: matches")
    function_name = _FUNCTION_NAMES.get(expression.callee)
    if function_name is None:
        raise MySqlRenderError(f"Unsupported MySQL function call: {expression.callee}")
    expected_symbol = SymbolId(SymbolNamespace.CALLABLE, expression.callee)
    if expression.callee_symbol != expected_symbol:
        raise MySqlRenderError(
            f"Unsupported MySQL function identity: {expression.callee}"
        )
    if len(expression.arguments) != 1:
        raise MySqlRenderError(
            f"MySQL function {expression.callee} expects 1 argument(s)"
        )
    argument = _render_mysql_expression(expression.arguments[0], nested=True)
    return f"{function_name}({argument})"


def _supported_operator(
    supported: dict[str, str],
    operator: str,
    kind: str,
) -> str:
    try:
        return supported[operator]
    except KeyError as error:
        raise MySqlRenderError(
            f"Unsupported MySQL {kind} operator: {operator}"
        ) from error
