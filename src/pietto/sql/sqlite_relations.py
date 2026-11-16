"""Internal SQLite rendering of one flat single-file relation SELECT.

SQLite single-file SQL covers a flat subset (D78.01, PL.47): a table or query
over one `sqlite.table` source with `where`, `select`, `order by`, `limit`,
`group by`, `having` and the aggregates `count`, `count_distinct`, `min`,
`max` and `avg` of an Int, over Int, Text, Bool and Float values, with no
arithmetic. Each other form raises SqliteRenderError with its reason.

Every field is qualified with the table name: SQLite binds a bare ORDER BY
name to an output first, comparing names without ASCII case, and falls back
to an output for a bare WHERE or GROUP BY name that names no column.
"""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ir.model import (
    AggregateCallIR,
    AggregateWindowCallIR,
    AnyFieldIR,
    BetweenIR,
    BinaryIR,
    CallIR,
    CastIR,
    ComparisonIR,
    ConditionalIR,
    ExistsIR,
    ExpressionIR,
    FieldId,
    FieldRefIR,
    IsNullIR,
    LiteralIR,
    MembershipIR,
    NullabilityIR,
    OrderDirectionIR,
    OrderItemIR,
    ProjectionIR,
    RelationIR,
    SourceIR,
    SymbolId,
    TypeKindIR,
    TypeRefIR,
    UnaryIR,
    WindowCallIR,
)
from pietto.sql.sqlite_render import (
    SqliteRenderError,
    quote_identifier,
    render_literal,
)

_VALUE_TYPES = frozenset({"Int", "Text", "Bool", "Float"})
_EXTREMA_TYPES = frozenset({"Int", "Float"})
_DISTINCT_TYPES = frozenset({"Int", "Text", "Bool"})
_COMPARISONS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
_CONNECTIVES = {"and": "AND", "or": "OR"}
_EXTREMA = {"min": "MIN", "max": "MAX"}
# SQLite puts NULL first in ascending order. Each key states the place of NULL
# that PostgreSQL documents and the PostgreSQL emitter keeps (D78.02).
_DIRECTIONS = {
    OrderDirectionIR.ASC: "ASC NULLS LAST",
    OrderDirectionIR.DESC: "DESC NULLS FIRST",
}
_INT64_MAX = 9_223_372_036_854_775_807
# What each expression outside the subset is called in its refusal.
_FORMS: dict[type[ExpressionIR], str] = {
    AnyFieldIR: "`any(...)` read",
    ExistsIR: "`any(...)` read",
    BetweenIR: "range comparison",
    CastIR: "cast",
    ConditionalIR: "conditional expression",
    MembershipIR: "`in` test",
    WindowCallIR: "window",
    AggregateWindowCallIR: "window",
}


def render_sqlite_relation(
    relation: RelationIR,
    *,
    sources: Mapping[SymbolId, SourceIR],
) -> str:
    """Render one relation of the subset as a SELECT over its source."""

    if relation.inputs or relation.joins:
        raise _unsupported("JOIN")
    source = sources.get(relation.source.target)
    if source is None:
        raise SqliteRenderError(
            "SQLite single-file SQL reads a sqlite.table source directly; "
            "a table or query that reads another is not supported yet"
        )
    statement = _Statement(source, relation.source.name)
    if relation.qualify is not None:
        raise _unsupported("qualify")
    if relation.named_windows:
        raise _unsupported("window")
    if not relation.projections:
        raise SqliteRenderError("SQLite relation emission requires projections")

    group_fields: list[FieldId] = []
    group_sql: list[str] = []
    for key in relation.group_keys:
        if not isinstance(key, FieldRefIR):
            raise SqliteRenderError("SQLite GROUP BY key must be a field")
        group_sql.append(statement.expression(key))
        assert key.field is not None
        if key.field in group_fields:
            raise SqliteRenderError("SQLite GROUP BY keys must be unique")
        group_fields.append(key.field)
    aggregated = bool(group_fields) or any(
        isinstance(projection.expression, AggregateCallIR)
        for projection in relation.projections
    )
    projection_sql = [
        statement.projection(projection, group_fields if aggregated else None)
        for projection in relation.projections
    ]
    lines = [
        "SELECT",
        ",\n".join(f"    {sql}" for sql in projection_sql),
        f"FROM {statement.table}",
    ]
    if relation.filter is not None:
        lines.append(f"WHERE {statement.expression(relation.filter.expression)}")
    if group_sql:
        lines.extend(("GROUP BY", ",\n".join(f"    {sql}" for sql in group_sql)))
    if relation.result_predicate is not None:
        condition = relation.result_predicate.expression
        condition_type = condition.value_type
        if (
            not group_fields
            or condition_type.canonical_kind is not TypeKindIR.BUILTIN
            or condition_type.canonical_name != "Bool"
        ):
            raise _unsupported("having")  # `check` requires GROUP BY and a Bool
        lines.append(f"HAVING {statement.expression(condition, keys=group_fields)}")
    if relation.order_by:
        orderable = (
            tuple(
                projection.expression
                for projection in relation.projections
                if isinstance(projection.expression, (AggregateCallIR, FieldRefIR))
            )
            if aggregated
            else None
        )
        lines.extend(
            (
                "ORDER BY",
                ",\n".join(
                    f"    {statement.order_item(item, orderable)}"
                    for item in relation.order_by
                ),
            )
        )
    if relation.limit is not None:
        value = relation.limit.value
        if type(value) is not int or not 0 <= value <= _INT64_MAX:
            raise SqliteRenderError(
                "SQLite relation limit is outside the supported range"
            )
        lines.append(f"LIMIT {value}")
    return "\n".join(lines)


class _Statement:
    """The one source a statement reads, and how it renders expressions."""

    def __init__(self, source: SourceIR, binding: str) -> None:
        connector = source.connector
        if (
            connector.name != "sqlite.table"
            or len(connector.arguments) != 1
            or not isinstance(connector.arguments[0], str)
        ):
            raise SqliteRenderError(
                "SQLite relation emission requires sqlite.table(Text)"
            )
        name = connector.arguments[0]
        if "." in name:
            raise SqliteRenderError("SQLite table name must be one bare <table>")
        self.table = quote_identifier(name, context="table identifier")
        self._symbol = source.symbol
        self._binding = binding

    def projection(
        self, projection: ProjectionIR, group_fields: list[FieldId] | None
    ) -> str:
        """One SELECT item; `group_fields` holds the GROUP BY fields of an
        aggregated relation, whose items are keys, aggregates or literals."""

        if projection.name is None:
            raise SqliteRenderError(
                "SQLite single-file SQL needs a name for each output"
            )
        expression = projection.expression
        if group_fields is None:
            sql = self.expression(expression)
        elif isinstance(expression, AggregateCallIR):
            sql = self._aggregate(expression)
        elif isinstance(expression, LiteralIR) or (
            isinstance(expression, FieldRefIR) and expression.field in group_fields
        ):
            sql = self.expression(expression)
        else:
            raise SqliteRenderError(
                "SQLite output of an aggregated relation must be a GROUP BY "
                "key, an aggregate or a literal"
            )
        alias = quote_identifier(projection.name, context="output identifier")
        return f"{sql} AS {alias}"

    def order_item(
        self, item: OrderItemIR, orderable: tuple[ExpressionIR, ...] | None
    ) -> str:
        """One ORDER BY key; `orderable` holds the keys and aggregates an
        aggregated relation selects, which are its only ORDER BY keys."""

        direction = _DIRECTIONS.get(item.direction)
        if direction is None:
            raise SqliteRenderError("SQLite relation order direction is invalid")
        key = item.expression
        if orderable is None:
            if not isinstance(key, FieldRefIR):
                raise SqliteRenderError("SQLite ORDER BY key must be a field")
            sql = self.expression(key)
        elif any(key == expression for expression in orderable):
            sql = (
                self._aggregate(key)
                if isinstance(key, AggregateCallIR)
                else self.expression(key)
            )
        else:
            raise SqliteRenderError(
                "SQLite ORDER BY key of an aggregated relation must be a "
                "selected GROUP BY key or aggregate"
            )
        return f"{sql} {direction}"

    def expression(
        self,
        expression: ExpressionIR,
        *,
        nested: bool = False,
        keys: list[FieldId] | None = None,
    ) -> str:
        """Render one row expression of the subset; `keys` holds the GROUP BY
        fields of a HAVING condition, which reads those fields and aggregates
        and never an output alias or another field."""

        if isinstance(expression, AggregateCallIR) and keys is not None:
            return self._aggregate(expression)
        if isinstance(expression, FieldRefIR):
            field = expression.field
            if (
                field is None
                or field.owner != self._symbol
                or field.input is not None
                or expression.qualifier not in ((), (self._binding,))
            ):
                raise SqliteRenderError(
                    "SQLite single-file SQL reads only fields of its source"
                )
            _value_type(expression.value_type, f"field {field.name}")
            if keys is not None and field not in keys:
                raise SqliteRenderError(
                    "SQLite output of an aggregated relation must be a GROUP BY "
                    "key, an aggregate or a literal"
                )
            column = quote_identifier(field.name, context="column identifier")
            return f"{self.table}.{column}"
        if isinstance(expression, LiteralIR):
            if expression.value is not None:
                _value_type(expression.value_type, "a literal")
            if keys is not None and type(expression.value) is bool:
                # HAVING reads TRUE and FALSE as an output alias so named.
                return "1" if expression.value else "0"
            return render_literal(expression.value)
        if isinstance(expression, ComparisonIR):
            operator = _COMPARISONS.get(expression.operator)
            if operator is None:
                raise _unsupported(f"operator {expression.operator}")
            left = self.expression(expression.left, nested=True, keys=keys)
            right = self.expression(expression.right, nested=True, keys=keys)
            types = (
                expression.left.value_type.canonical_name,
                expression.right.value_type.canonical_name,
            )
            if types[0] != types[1]:
                raise SqliteRenderError(
                    "SQLite single-file SQL compares only values of one type; "
                    f"this comparison has {types[0]} and {types[1]}"
                )
            sql = f"{left} {operator} {right}"
        elif isinstance(expression, BinaryIR):
            operator = _CONNECTIVES.get(expression.operator)
            if operator is None:
                raise _unsupported("arithmetic")
            left = self.expression(expression.left, nested=True, keys=keys)
            right = self.expression(expression.right, nested=True, keys=keys)
            sql = f"{left} {operator} {right}"
        elif isinstance(expression, UnaryIR):
            if expression.operator != "not":
                raise SqliteRenderError(
                    "SQLite single-file SQL has no arithmetic yet; a sign "
                    "before a number is arithmetic too"
                )
            operand = self.expression(expression.operand, nested=True, keys=keys)
            sql = f"NOT {operand}"
        elif isinstance(expression, IsNullIR):
            operator = "IS NOT NULL" if expression.negated else "IS NULL"
            value = self.expression(expression.value, nested=True, keys=keys)
            sql = f"{value} {operator}"
        elif isinstance(expression, AggregateCallIR):
            raise _unsupported("aggregate inside an expression")
        elif isinstance(expression, CallIR):
            raise _unsupported(f"function {expression.callee}")
        else:
            raise _unsupported(_FORMS.get(type(expression), type(expression).__name__))
        return f"({sql})" if nested else sql

    def _aggregate(self, expression: AggregateCallIR) -> str:
        """Render one `count`, `count_distinct`, `min`, `max` or `avg` over a
        field of the source."""

        function = expression.function
        arguments = expression.arguments
        if expression.order_by or (
            function not in ("count", "count_distinct", "avg")
            and function not in _EXTREMA
        ):
            raise _unsupported(f"aggregate {function}")
        if any(not isinstance(argument, FieldRefIR) for argument in arguments):
            raise SqliteRenderError(
                f"SQLite aggregate {function} reads a field of the source directly"
            )
        if function == "count":
            if len(arguments) > 1 or not _is_builtin(
                expression.value_type, "Int", NullabilityIR.NON_NULL
            ):
                raise SqliteRenderError(
                    "SQLite aggregate count violates its IR contract"
                )
            if not arguments:
                return "COUNT(*)"
            return f"COUNT({self.expression(arguments[0])})"
        if len(arguments) != 1:
            raise SqliteRenderError(f"SQLite aggregate {function} expects 1 argument")
        argument = arguments[0]
        argument_sql = self.expression(argument)
        argument_type = argument.value_type.canonical_name
        if function == "count_distinct":
            if argument_type not in _DISTINCT_TYPES:
                raise SqliteRenderError(
                    "SQLite aggregate count_distinct supports only Int, Text and "
                    "Bool fields"
                )
            if not _is_builtin(expression.value_type, "Int", NullabilityIR.NON_NULL):
                raise SqliteRenderError(
                    "SQLite aggregate count_distinct violates its IR contract"
                )
            return f"COUNT(DISTINCT {argument_sql})"
        if function == "avg":
            if argument_type != "Int":
                raise SqliteRenderError("SQLite aggregate avg supports only Int fields")
            if not _is_builtin(expression.value_type, "Float", NullabilityIR.NULLABLE):
                raise SqliteRenderError("SQLite aggregate avg violates its IR contract")
            # The language casts an Int to the target's binary64 before averaging.
            return f"AVG(CAST({argument_sql} AS REAL))"
        if argument_type not in _EXTREMA_TYPES:
            raise SqliteRenderError(
                f"SQLite aggregate {function} supports only Int and Float fields"
            )
        if not _is_builtin(
            expression.value_type, argument_type, NullabilityIR.NULLABLE
        ):
            raise SqliteRenderError(
                f"SQLite aggregate {function} violates its IR contract"
            )
        return f"{_EXTREMA[function]}({argument_sql})"


def _value_type(type_ref: TypeRefIR, subject: str) -> None:
    if (
        type_ref.canonical_kind is not TypeKindIR.BUILTIN
        or type_ref.canonical_name not in _VALUE_TYPES
    ):
        raise SqliteRenderError(
            "SQLite single-file SQL reads only Int, Text, Bool and Float values; "
            f"{subject} has type {type_ref.declared_name}"
        )


def _is_builtin(type_ref: TypeRefIR, name: str, nullability: NullabilityIR) -> bool:
    return (
        type_ref.canonical_kind is TypeKindIR.BUILTIN
        and type_ref.canonical_name == name
        and type_ref.nullability is nullability
    )


def _unsupported(form: str) -> SqliteRenderError:
    return SqliteRenderError(f"SQLite single-file SQL has no {form} yet")
