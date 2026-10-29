"""Internal MySQL rendering for the approved Semantic IR expressions."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import fields, is_dataclass

from pietto.ir.model import (
    AggregateCallIR,
    AggregateWindowCallIR,
    aggregate_call_contract,
    AnyFieldIR,
    ExistsIR,
    BetweenIR,
    BinaryIR,
    CastIR,
    CallIR,
    ConditionalIR,
    ComparisonIR,
    ExpressionIR,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    MembershipIR,
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
    MYSQL_EXCLUDE_REFUSAL,
    MYSQL_GROUPS_OFFSET_REFUSAL,
    WindowTargetDialect,
    decide_inline_window_target,
    range_offset_refusal,
)

_COMPARISON_OPERATORS = {
    "==": "=",
    "!=": "<>",
    "<": "<",
    "<=": "<=",
    ">": ">",
    ">=": ">=",
    "like": "LIKE",
    "not like": "NOT LIKE",
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
    "not": "NOT ",
}
_FUNCTION_NAMES = {
    "lower": "LOWER",
    "upper": "UPPER",
    "trim": "TRIM",
    "len": "CHAR_LENGTH",
    "replace": "REPLACE",
    "abs": "ABS",
    "sign": "SIGN",
}
_FUNCTION_ARITIES = {
    "lower": 1,
    "upper": 1,
    "trim": 1,
    "len": 1,
    "nullif": 2,
    "substr": 3,
    "replace": 3,
    "contains": 2,
    "starts_with": 2,
    "ends_with": 2,
    "abs": 1,
    "sign": 1,
    "date_of": 1,
    "year": 1,
    "month": 1,
    "day": 1,
    "hour": 1,
    "minute": 1,
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
_DATE_PARTS = frozenset({"year", "month", "day", "hour", "minute"})
_COMPOUND_CALLS = frozenset({"contains", "starts_with", "ends_with"})


def render_mysql_expression(expression: ExpressionIR) -> str:
    """Render one supported Semantic IR expression as MySQL SQL."""

    return _render_mysql_expression(expression, nested=False)


def _render_mysql_expression(expression: ExpressionIR, *, nested: bool) -> str:
    if isinstance(expression, AnyFieldIR):
        return quote_qualified_identifier((expression.binding, expression.name))
    if isinstance(expression, ExistsIR):
        if expression.connector is None:
            parts = (expression.target.name,)
        else:
            connector = expression.connector
            if (
                connector.name != "mysql.table"
                or len(connector.arguments) != 1
                or not isinstance(connector.arguments[0], str)
                or not connector.arguments[0]
            ):
                raise MySqlRenderError("Scalar ANY requires mysql.table(Text)")
            parts = tuple(connector.arguments[0].split("."))
            if len(parts) > 2 or not all(parts):
                raise MySqlRenderError(
                    "Scalar ANY table name must be <table> or <schema>.<table>"
                )
        predicate = _render_mysql_expression(expression.predicate, nested=False)
        return f"EXISTS (SELECT 1 FROM {quote_qualified_identifier(parts)} AS {quote_identifier(expression.binding, context='relation identifier')} WHERE {predicate})"
    if isinstance(expression, LiteralIR):
        return render_literal(expression.value)
    if isinstance(expression, FieldRefIR):
        if expression.qualifier:
            return quote_qualified_identifier((*expression.qualifier, expression.name))
        return quote_identifier(expression.name, context="column identifier")
    if isinstance(expression, AggregateCallIR):
        return _render_aggregate_call(expression)
    if isinstance(expression, AggregateWindowCallIR):
        if nested:
            raise MySqlRenderError("MySQL aggregate windows are direct projections")
        return render_mysql_aggregate_window_call(expression)
    if isinstance(expression, WindowCallIR):
        if nested:
            raise MySqlRenderError(
                "MySQL window calls are supported only as direct projections"
            )
        return render_mysql_window_call(expression)
    if isinstance(expression, CallIR):
        sql = _render_call(expression)
        return f"({sql})" if nested and expression.callee in _COMPOUND_CALLS else sql
    if isinstance(expression, ConditionalIR):
        sql = (
            "CASE WHEN "
            f"{_render_mysql_expression(expression.condition, nested=True)} THEN "
            f"{_render_mysql_expression(expression.when_true, nested=True)} ELSE "
            f"{_render_mysql_expression(expression.when_false, nested=True)} END"
        )
    elif isinstance(expression, MembershipIR):
        value_sql = _render_mysql_expression(expression.value, nested=True)
        if not expression.options:
            return "TRUE" if expression.negated else "FALSE"
        operator = "NOT IN" if expression.negated else "IN"
        options = ", ".join(
            _render_mysql_expression(option, nested=True)
            for option in expression.options
        )
        sql = f"{value_sql} {operator} ({options})"
    elif isinstance(expression, CastIR):
        if (
            expression.value.value_type.canonical_kind is TypeKindIR.BUILTIN
            and expression.value.value_type.canonical_name == "Int"
            and expression.target.canonical_kind is TypeKindIR.BUILTIN
            and expression.target.canonical_name == "Float"
        ):
            sql = f"CAST({_render_mysql_expression(expression.value, nested=True)} AS DOUBLE)"
        elif (
            expression.value.value_type.canonical_kind is TypeKindIR.BUILTIN
            and expression.value.value_type.canonical_name == "Int"
            and expression.target.canonical_kind is TypeKindIR.BUILTIN
            and expression.target.canonical_name == "Text"
        ):
            sql = f"CAST({_render_mysql_expression(expression.value, nested=True)} AS CHAR)"
        else:
            raise MySqlRenderError(
                "MySQL supports only explicit Int to Float or Text casts"
            )
    elif isinstance(expression, ComparisonIR):
        operator = _supported_operator(
            _COMPARISON_OPERATORS,
            expression.operator,
            "comparison",
        )
        sql = (
            f"{_render_mysql_expression(expression.left, nested=True)} {operator} "
            f"{_render_mysql_expression(expression.right, nested=True)}"
        )
        if expression.operator in {"like", "not like"}:
            sql += " ESCAPE '!'"
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
        if _is_integer_division(expression):
            # MySQL `/` of integers is DECIMAL; DIV truncates toward zero as
            # PostgreSQL's integer `/` does.
            operator = "DIV"
        sql = (
            f"{_render_mysql_expression(expression.left, nested=True)} {operator} "
            f"{_render_mysql_expression(expression.right, nested=True)}"
        )
    else:
        raise MySqlRenderError(
            f"Unsupported MySQL expression IR node: {type(expression).__name__}"
        )

    return f"({sql})" if nested else sql


def _is_integer_division(expression: BinaryIR) -> bool:
    """Whether `/` divides an Int by an Int into an Int."""

    return expression.operator == "/" and all(
        part.value_type.canonical_kind is TypeKindIR.BUILTIN
        and part.value_type.canonical_name == "Int"
        for part in (expression, expression.left, expression.right)
    )


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


def render_mysql_aggregate_window_call(
    expression: AggregateWindowCallIR,
    *,
    over_sql: str | None = None,
) -> str:
    """Render the five admitted aggregate windows."""

    if type(expression) is not AggregateWindowCallIR:
        raise MySqlRenderError("MySQL aggregate window requires an exact carrier")
    aggregate_sql = _render_aggregate_call(
        AggregateCallIR(
            span=expression.span,
            value_type=expression.value_type,
            function=expression.function,
            arguments=expression.arguments,
        ),
        allow_grouped_aggregate=True,
    )
    if over_sql is None:
        components = render_mysql_window_components(
            expression.spec.partition_by,
            expression.spec.order_by,
            expression.spec.frame,
        )
        over_sql = f"({' '.join(components)})"
    if type(over_sql) is not str or not over_sql:
        raise MySqlRenderError("MySQL aggregate window OVER SQL must be nonempty")
    return f"{aggregate_sql} OVER {over_sql}"


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
    offset_bounds = tuple(
        bound
        for bound in (frame.start, frame.end)
        if bound.kind
        in {
            WindowFrameBoundKindIR.OFFSET_PRECEDING,
            WindowFrameBoundKindIR.OFFSET_FOLLOWING,
        }
    )
    if frame.unit is WindowFrameUnitIR.GROUPS and offset_bounds:
        raise MySqlRenderError(MYSQL_GROUPS_OFFSET_REFUSAL)
    if frame.unit is WindowFrameUnitIR.RANGE and offset_bounds:
        raise MySqlRenderError(range_offset_refusal("MySQL"))
    if any(
        type(bound.offset) is not LiteralIR
        or type(bound.offset.value) is not int
        or bound.offset.value < 0
        for bound in offset_bounds
    ):
        raise MySqlRenderError("MySQL frame offsets require nonnegative Int literals")
    # MySQL frames never exclude a row, which is EXCLUDE NO OTHERS, and MySQL
    # refuses an EXCLUDE clause, so the clause is left out.
    if frame.exclusion is not WindowFrameExclusionIR.NO_OTHERS:
        raise MySqlRenderError(MYSQL_EXCLUDE_REFUSAL)
    start = _render_mysql_window_frame_bound(frame.start)
    end = _render_mysql_window_frame_bound(frame.end)
    # Without an offset a GROUPS bound is the current row's peer group or a
    # partition end, as the same RANGE bound is; MySQL refuses GROUPS.
    unit = "RANGE" if frame.unit is WindowFrameUnitIR.GROUPS else frame.unit.value
    if frame.frame_is_explicit and not frame.end_is_explicit:
        return f"{unit} {start}"
    return f"{unit} BETWEEN {start} AND {end}"


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


def _render_aggregate_call(
    expression: AggregateCallIR,
    *,
    allow_grouped_aggregate: bool = False,
) -> str:
    if expression.function == "string_agg":
        raise MySqlRenderError("MySQL aggregate string_agg is not supported")
    if expression.function == "count":
        sql = _render_count_aggregate(
            expression, allow_grouped_aggregate=allow_grouped_aggregate
        )
    elif expression.function == "count_distinct":
        sql = _render_count_distinct_aggregate(expression)
    elif (
        function_name := _EXTREMA_AGGREGATE_NAMES.get(expression.function)
    ) is not None:
        sql = _render_extrema_aggregate(
            expression,
            function_name=function_name,
            allow_grouped_aggregate=allow_grouped_aggregate,
        )
    else:
        function_name = _NUMERIC_AGGREGATE_NAMES.get(expression.function)
        if function_name is None:
            raise MySqlRenderError(
                f"Unsupported MySQL aggregate call: {expression.function}"
            )
        sql = _render_numeric_aggregate(
            expression,
            function_name=function_name,
            allow_grouped_aggregate=allow_grouped_aggregate,
        )
    if not aggregate_call_contract(
        expression.function,
        expression.arguments,
        expression.value_type,
        order_by=expression.order_by,
        allow_grouped_value=allow_grouped_aggregate,
    ):
        raise MySqlRenderError("MySQL aggregate call violates its IR contract")
    return sql


def _render_count_aggregate(
    expression: AggregateCallIR,
    *,
    allow_grouped_aggregate: bool = False,
) -> str:
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
    if not _is_count_argument_expression(
        argument, allow_grouped_aggregate=allow_grouped_aggregate
    ):
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
    allow_grouped_aggregate: bool = False,
) -> str:
    if len(expression.arguments) != 1:
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    argument_type = _numeric_aggregate_argument_type(
        argument, allow_grouped_aggregate=allow_grouped_aggregate
    )
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
    argument_sql = _render_mysql_expression(argument, nested=True)
    if expression.function == "avg" and argument_type == "Int":
        # MySQL AVG of an integer is an exact decimal; Pietto says Float.
        argument_sql = f"CAST({argument_sql} AS DOUBLE)"
    return f"{function_name}({argument_sql})"


def _numeric_aggregate_argument_type(
    expression: ExpressionIR,
    *,
    allow_grouped_aggregate: bool = False,
) -> str | None:
    expression_type, has_field, has_literal = _numeric_aggregate_argument_shape(
        expression, allow_grouped_aggregate=allow_grouped_aggregate
    )
    if expression_type is None:
        return None
    if has_literal and (not has_field or expression_type not in {"Int", "Float"}):
        return None
    return expression_type


def _numeric_aggregate_argument_shape(
    expression: ExpressionIR,
    *,
    allow_grouped_aggregate: bool = False,
) -> tuple[str | None, bool, bool]:
    """Return (builtin type, has resolved field, has Int/Float literal)."""

    expression_type = _builtin_type_name(expression)
    if expression_type not in _SUPPORTED_NUMERIC_AGGREGATE_ARGUMENT_TYPES:
        return None, False, False

    if isinstance(expression, FieldRefIR):
        if expression.field is None:
            return None, False, False
        return expression_type, True, False

    if isinstance(expression, AggregateCallIR) and allow_grouped_aggregate:
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
        ) = _numeric_aggregate_argument_shape(
            expression.operand, allow_grouped_aggregate=allow_grouped_aggregate
        )
        if operand_type != expression_type:
            return None, False, False
        return expression_type, operand_has_field, operand_has_literal

    if isinstance(expression, BinaryIR):
        if expression.operator not in {"+", "-", "*"}:
            return None, False, False
        left_type, left_has_field, left_has_literal = _numeric_aggregate_argument_shape(
            expression.left, allow_grouped_aggregate=allow_grouped_aggregate
        )
        right_type, right_has_field, right_has_literal = (
            _numeric_aggregate_argument_shape(
                expression.right, allow_grouped_aggregate=allow_grouped_aggregate
            )
        )
        if left_type is None or right_type is None:
            return None, False, False
        if expression_type == "Decimal":
            operand_types = {left_type, right_type}
            # Decimal * Int is refused at check; only Decimal * Decimal is typed.
            allowed = {"Decimal"} if expression.operator == "*" else {"Decimal", "Int"}
            if operand_types - allowed or "Decimal" not in operand_types:
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


def _is_count_argument_expression(
    expression: ExpressionIR,
    *,
    allow_grouped_aggregate: bool = False,
) -> bool:
    is_valid, has_field = _count_argument_expression_shape(
        expression, allow_grouped_aggregate=allow_grouped_aggregate
    )
    return is_valid and has_field


def _count_argument_expression_shape(
    expression: ExpressionIR,
    *,
    allow_grouped_aggregate: bool = False,
) -> tuple[bool, bool]:
    """Return (valid shape, has resolved field leaf) for count expressions."""

    if _builtin_type_name(expression) in {None, "Any"}:
        return False, False

    if isinstance(expression, FieldRefIR):
        return expression.field is not None, expression.field is not None
    if isinstance(expression, AggregateCallIR) and allow_grouped_aggregate:
        return True, True
    if isinstance(expression, LiteralIR):
        return True, False
    if isinstance(expression, UnaryIR):
        if expression.operator not in _UNARY_OPERATORS:
            return False, False
        return _count_argument_expression_shape(
            expression.operand, allow_grouped_aggregate=allow_grouped_aggregate
        )
    if isinstance(expression, BinaryIR):
        if expression.operator not in {"+", "-", "*", "%", "and", "or"}:
            return False, False
        left_valid, left_has_field = _count_argument_expression_shape(
            expression.left, allow_grouped_aggregate=allow_grouped_aggregate
        )
        right_valid, right_has_field = _count_argument_expression_shape(
            expression.right, allow_grouped_aggregate=allow_grouped_aggregate
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
        return _count_argument_expression_shape(
            expression.arguments[0], allow_grouped_aggregate=allow_grouped_aggregate
        )
    return False, False


def _builtin_type_name(expression: ExpressionIR) -> str | None:
    if expression.value_type.canonical_kind is not TypeKindIR.BUILTIN:
        return None
    return expression.value_type.canonical_name


def _render_extrema_aggregate(
    expression: AggregateCallIR,
    *,
    function_name: str,
    allow_grouped_aggregate: bool = False,
) -> str:
    if len(expression.arguments) != 1:
        raise MySqlRenderError(
            f"MySQL aggregate {expression.function} expects 1 argument(s)"
        )
    argument = expression.arguments[0]
    if not (
        isinstance(argument, FieldRefIR)
        and argument.field is not None
        or allow_grouped_aggregate
        and isinstance(argument, AggregateCallIR)
    ):
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
    expected_symbol = SymbolId(SymbolNamespace.CALLABLE, expression.callee)
    if expression.callee_symbol != expected_symbol:
        raise MySqlRenderError(
            f"Unsupported MySQL function identity: {expression.callee}"
        )
    if expression.callee == "coalesce":
        if len(expression.arguments) < 2:
            raise MySqlRenderError(
                "MySQL function coalesce expects at least 2 argument(s)"
            )
        return (
            "COALESCE("
            + ", ".join(
                _render_mysql_expression(argument, nested=True)
                for argument in expression.arguments
            )
            + ")"
        )
    if expression.callee == "round":
        return _render_round_call(expression)
    if expression.callee == "date_trunc":
        return _render_date_trunc_call(expression)
    if expression.callee not in _FUNCTION_ARITIES:
        raise MySqlRenderError(f"Unsupported MySQL function call: {expression.callee}")
    expected_arity = _FUNCTION_ARITIES[expression.callee]
    if len(expression.arguments) != expected_arity:
        raise MySqlRenderError(
            f"MySQL function {expression.callee} expects {expected_arity} argument(s)"
        )
    arguments = tuple(
        _render_mysql_expression(argument, nested=True)
        for argument in expression.arguments
    )
    if expression.callee == "nullif":
        return f"NULLIF({arguments[0]}, {arguments[1]})"
    if expression.callee == "substr":
        return f"SUBSTRING({arguments[0]}, {arguments[1]}, {arguments[2]})"
    if expression.callee == "replace":
        return f"REPLACE({arguments[0]}, {arguments[1]}, {arguments[2]})"
    if expression.callee == "contains":
        return f"INSTR({arguments[0]}, {arguments[1]}) > 0"
    if expression.callee == "starts_with":
        return f"LEFT({arguments[0]}, CHAR_LENGTH({arguments[1]})) = {arguments[1]}"
    if expression.callee == "ends_with":
        return f"RIGHT({arguments[0]}, CHAR_LENGTH({arguments[1]})) = {arguments[1]}"
    if expression.callee == "date_of":
        return f"DATE({arguments[0]})"
    if expression.callee in _DATE_PARTS:
        return f"{expression.callee.upper()}({arguments[0]})"
    return f"{_FUNCTION_NAMES[expression.callee]}({arguments[0]})"


def _render_round_call(expression: CallIR) -> str:
    if len(expression.arguments) not in {1, 2}:
        raise MySqlRenderError("MySQL function round expects 1 or 2 argument(s)")
    value = expression.arguments[0]
    value_kind = _builtin_type_name(value)
    if value_kind not in {"Decimal", "Float"} or not _same_value_type(
        expression, value
    ):
        raise MySqlRenderError("MySQL supports round only for Decimal and Float")
    if value_kind == "Float":
        if len(expression.arguments) != 1:
            raise MySqlRenderError("MySQL function round(Float) expects 1 argument")
        if has_inexact_float_arithmetic(value):
            raise MySqlRenderError(
                "MySQL function round(Float) supports Float arithmetic only "
                "with a DOUBLE operand"
            )
        # MySQL ROUND of a DOUBLE follows the C library, which may round half
        # to even; this is PostgreSQL's half away from zero, on the same value.
        value_sql = _render_mysql_expression(value, nested=True)
        trunc_sql = f"TRUNCATE({value_sql}, 0)"
        return (
            f"CASE WHEN ABS({value_sql} - {trunc_sql}) >= 0.5 THEN {trunc_sql} + "
            f"CASE WHEN {value_sql} < 0 THEN -1.0 ELSE 1.0 END "
            f"ELSE {trunc_sql} END"
        )
    if len(expression.arguments) == 1:
        return f"ROUND({_render_mysql_expression(value, nested=True)})"
    scale = expression.arguments[1]
    if not _approved_round_scale(scale):
        raise MySqlRenderError(
            "MySQL function round scale must be an Int literal from -30 to 30"
        )
    return (
        f"ROUND({_render_mysql_expression(value, nested=True)}, "
        f"{_render_mysql_expression(scale, nested=True)})"
    )


def has_inexact_float_arithmetic(expression: ExpressionIR) -> bool:
    """Whether a Float `+`, `-`, `*` or `/` in an expression has no DOUBLE operand.

    PostgreSQL computes it as an exact `numeric`, such as `amount + 0.5`, and
    MySQL as a DECIMAL, with a smaller division scale, or as a DOUBLE beside an
    exponent literal such as `1e-17`, so the two may differ near a tie that
    round(Float) then decides. Beside a DOUBLE both compute in binary64 from
    the same operand values.
    """

    decided: dict[int, bool] = {}
    return any(
        type(node) is BinaryIR
        and _builtin_type_name(node) == "Float"
        and not (
            _is_mysql_double(node.left, decided)
            or _is_mysql_double(node.right, decided)
        )
        for node in _ir_nodes(expression)
    )


def is_mysql_double(expression: ExpressionIR) -> bool:
    """Whether PostgreSQL and MySQL both hold a Float value as a DOUBLE.

    A Float field counts as a DOUBLE column, which render_mysql_relation
    proves. A DOUBLE beside an exact value, or chosen with one by CASE or
    COALESCE, keeps the result a DOUBLE on both targets.
    """

    return _is_mysql_double(expression, {})


def _is_mysql_double(expression: ExpressionIR, decided: dict[int, bool]) -> bool:
    """is_mysql_double, which records each node it decides in `decided` by id.

    The caller holds every node recorded, so no id is reused. The walk keeps
    an explicit stack, so a deep expression never exhausts the interpreter's
    recursion limit.
    """

    pending = [expression]
    while pending:
        node = pending[-1]
        if id(node) in decided:
            pending.pop()
            continue
        parts = _mysql_double_parts(node)
        if type(parts) is bool:
            decided[id(node)] = parts
            pending.pop()
            continue
        undecided = [part for part in parts if id(part) not in decided]
        if undecided:
            pending.extend(undecided)
            continue
        pending.pop()
        decided[id(node)] = any(decided[id(part)] for part in parts)
    return decided[id(expression)]


def _mysql_double_parts(expression: ExpressionIR) -> bool | tuple[ExpressionIR, ...]:
    """Whether a node is a DOUBLE, or the parts of which any one makes it one."""

    if _builtin_type_name(expression) != "Float":
        return False
    if type(expression) in {FieldRefIR, AnyFieldIR, CastIR}:
        return True
    if type(expression) is UnaryIR:
        return (expression.operand,)
    if type(expression) is BinaryIR:
        return (expression.left, expression.right)
    if type(expression) is ConditionalIR:
        return (expression.when_true, expression.when_false)
    if type(expression) is CallIR and expression.callee in {
        "abs",
        "coalesce",
        "round",
    }:
        return expression.arguments
    if type(expression) is CallIR and expression.callee == "nullif":
        return expression.arguments[:1]
    if isinstance(expression, (AggregateCallIR, AggregateWindowCallIR)):
        # Both targets read the Int of an avg as a DOUBLE.
        if any(_builtin_type_name(part) == "Int" for part in expression.arguments):
            return True
        return expression.arguments
    if type(expression) is WindowCallIR:
        if expression.identity.name in {"percent_rank", "cume_dist"}:
            return True
        return expression.arguments[:1]
    return False


def mysql_rounded_float_fields(value: object) -> Iterator[FieldRefIR | AnyFieldIR]:
    """Yield each Float field that a round(Float) call in an IR value reads."""

    for node in _ir_nodes(value):
        if (
            type(node) is CallIR
            and node.callee == "round"
            and _builtin_type_name(node) == "Float"
            and node.arguments
        ):
            yield from mysql_float_fields(node.arguments[0])


def mysql_float_fields(value: object) -> Iterator[FieldRefIR | AnyFieldIR]:
    """Yield each Float field in an IR value, in pre-order."""

    for node in _ir_nodes(value):
        if (
            isinstance(node, (FieldRefIR, AnyFieldIR))
            and _builtin_type_name(node) == "Float"
        ):
            yield node


def _ir_nodes(value: object) -> Iterator[object]:
    """Yield an IR value and each value inside it, in pre-order."""

    pending = [value]
    while pending:
        item = pending.pop()
        yield item
        if isinstance(item, tuple):
            pending.extend(reversed(item))
        elif is_dataclass(item) and not isinstance(item, type):
            pending.extend(
                getattr(item, field.name) for field in reversed(fields(item))
            )


def _render_date_trunc_call(expression: CallIR) -> str:
    """Truncate a civil Date or Timestamp to the start of its unit.

    MySQL has no date_trunc; each unit rebuilds the value from its parts with
    every lower part zero, as PostgreSQL date_trunc on a timestamp without
    time zone does. Every function used returns NULL for NULL. A year or month
    steps back by days, as MAKEDATE would read a year below 100 as two digits.
    """

    if len(expression.arguments) != 2:
        raise MySqlRenderError("MySQL function date_trunc expects 2 argument(s)")
    unit, value = expression.arguments
    if (
        type(unit) is not LiteralIR
        or type(unit.value) is not str
        or _builtin_type_name(unit) != "Text"
    ):
        raise MySqlRenderError("MySQL function date_trunc unit must be a Text literal")
    value_kind = _builtin_type_name(value)
    if value_kind not in {"Date", "Timestamp"} or not _same_value_type(
        expression, value
    ):
        raise MySqlRenderError("MySQL function date_trunc has an invalid typed shape")
    units = {"year", "month", "day"}
    if value_kind == "Timestamp":
        units |= {"hour", "minute"}
    if unit.value not in units:
        raise MySqlRenderError("MySQL function date_trunc unit is unsupported")
    # Each unit but day repeats the value, so a date_trunc inside it would
    # grow the SQL exponentially with nesting.
    if unit.value != "day" and any(
        type(node) is CallIR and node.callee == "date_trunc"
        for node in _ir_nodes(value)
    ):
        raise MySqlRenderError(
            f"MySQL function date_trunc with unit {unit.value} repeats its "
            "value, which must not hold another date_trunc"
        )
    x = _render_mysql_expression(value, nested=True)
    day = x if value_kind == "Date" else f"DATE({x})"
    date_sql = {
        "year": f"DATE_SUB({day}, INTERVAL (DAYOFYEAR({x}) - 1) DAY)",
        "month": f"DATE_SUB({day}, INTERVAL (DAYOFMONTH({x}) - 1) DAY)",
        "day": day,
        "hour": f"{day}, MAKETIME(HOUR({x}), 0, 0)",
        "minute": f"{day}, MAKETIME(HOUR({x}), MINUTE({x}), 0)",
    }[unit.value]
    return date_sql if value_kind == "Date" else f"TIMESTAMP({date_sql})"


def _approved_round_scale(expression: ExpressionIR) -> bool:
    if (
        type(expression) is LiteralIR
        and type(expression.value) is int
        and _builtin_type_name(expression) == "Int"
    ):
        return -30 <= expression.value <= 30
    return (
        type(expression) is UnaryIR
        and expression.operator == "-"
        and _builtin_type_name(expression) == "Int"
        and type(expression.operand) is LiteralIR
        and type(expression.operand.value) is int
        and _builtin_type_name(expression.operand) == "Int"
        and 0 <= expression.operand.value <= 30
    )


def _same_value_type(left: ExpressionIR, right: ExpressionIR) -> bool:
    return (
        left.value_type.canonical_kind is TypeKindIR.BUILTIN
        and right.value_type.canonical_kind is TypeKindIR.BUILTIN
        and left.value_type.canonical_name == right.value_type.canonical_name
        and left.value_type.nullability is right.value_type.nullability
    )


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
