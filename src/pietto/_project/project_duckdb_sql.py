"""The DuckDB adapter's own SQL AST and renderer (AD78.03).

One statement over the registered captures, the first input joined to each
later one by `INNER JOIN` or `LEFT JOIN` on equalities of fields: its
columns, or with `group by` and aggregates their grouped values, and `Int`
and `Float` arithmetic over them in the final projection, filtered in
`where` and `having` by comparisons of a read with a literal or a parameter,
null tests and `AND`, `OR` and `NOT` of these, then its order keys and its
static limit. Every identifier is Pietto-owned except the quoted result
labels, so the SQL never holds the caller's key or column names
(docs/spec/duckdb-arrow-route-v1.md). Fields are numbered across the inputs
in their order, so each capture column's name `"c<k>"` is unique.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import math

__all__: tuple[str, ...] = ()

RELATION = "pietto_arrow_0"
JOINS = ("INNER", "LEFT")
OPERATORS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
# The type each parameter's placeholder is cast to: DuckDB types a bound
# Python value by its value.
CASTS = {
    "Int": "BIGINT",
    "Float": "DOUBLE",
    "Text": "VARCHAR",
    "Bool": "BOOLEAN",
    "Date": "DATE",
    "Timestamp": "TIMESTAMP",
    "Decimal": "DECIMAL",
}
# The digits of a DuckDB DECIMAL, and the civil interval of a `Date` and of
# a `Timestamp` (language.md, "Timestamp and UUID source meaning").
MAX_PRECISION = 38
CIVIL = (datetime(1000, 1, 1), datetime(9999, 12, 31, 23, 59, 59, 499999))
LOGIC = ("AND", "OR", "NOT")
# The Python value type of an arithmetic literal of each type.
_VALUE = {"Int": int, "Float": float}
# NULL sorts as the PostgreSQL emitter's SQL puts it (PL.47); DuckDB's own
# default puts NULL last in both directions.
DIRECTIONS = {False: " ASC NULLS LAST", True: " DESC NULLS FIRST"}
# DuckDB refuses a larger LIMIT; the language's static limit stays within it.
MAX_LIMIT = 2**63 - 1
# The text of each aggregate before and after its column; `count(*)` has none.
AGGREGATES = {
    "count": ("count(", ")"),
    "sum": ("CAST(sum(", ") AS BIGINT)"),
    "min": ("min(", ")"),
    "max": ("max(", ")"),
}
# The text of the error each checked `Float` operation raises: DuckDB
# returns an infinity on overflow and 0 on underflow, which PostgreSQL refuses.
FLOAT_OVERFLOW = "Pietto Float overflow: the result is outside binary64"
FLOAT_UNDERFLOW = (
    "Pietto Float underflow: a product of two non-zero Float values rounded"
    " to 0; use Int or scale the values"
)
SIGNED64 = (-(2**63), 2**63 - 1)


@dataclass(frozen=True, slots=True)
class DuckDBColumn:
    """Result column `<value> AS "<label>"`: `"c<field>"`, the aggregate
    `function` of it, or the arithmetic `value`; `field` is the source
    field's position in shape order, None in `count(*)` and arithmetic."""

    field: int | None
    label: str
    function: str | None = None
    value: DuckDBArithmetic | None = None


@dataclass(frozen=True, slots=True)
class DuckDBRead:
    """A read in a predicate: in `where` the source field `"c<field>"`; in
    `having` a selected value restated with qualified names, a group key's
    `field` or the aggregate `function` of it."""

    field: int | None
    function: str | None = None


@dataclass(frozen=True, slots=True)
class DuckDBLiteral:
    """An `Int`, `Float`, `Text` or `Bool` literal, with its sign; a `Date`
    or `Timestamp` that a `Text` literal spells; or the exact `Decimal` that
    a number literal writes."""

    value: int | float | str | bool | date | datetime | Decimal


@dataclass(frozen=True, slots=True)
class DuckDBParameter:
    """`CAST($<placeholder> AS <type>)`, the type of the parameter's `tag`,
    `DECIMAL(p,s)` with the `decimal` (precision, scale) of a `Decimal`."""

    placeholder: int
    tag: str
    decimal: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class DuckDBArithmetic:
    """`<left> <operator> <right>` of two operands, `+`, `-` or `*`, or a
    `Float` sign `-<operand>` or `+<operand>`, which is the operand itself;
    each operand is a read of a field or group key, a literal or a parameter
    of the result's `tag`, `Int` or `Float`, and one at least is a read. A
    `Float` `+`, `-` or `*` is checked: it fails with FLOAT_OVERFLOW where
    DuckDB gives an infinity, and a `*` also with FLOAT_UNDERFLOW where two
    non-zero operands give 0."""

    operator: str
    operands: tuple[DuckDBRead | DuckDBLiteral | DuckDBParameter, ...]
    tag: str


@dataclass(frozen=True, slots=True)
class DuckDBComparison:
    """`<left> <operator> <right>`: a read and a literal or a parameter."""

    left: DuckDBRead | DuckDBLiteral | DuckDBParameter
    operator: str
    right: DuckDBRead | DuckDBLiteral | DuckDBParameter


@dataclass(frozen=True, slots=True)
class DuckDBNullTest:
    """`<read> IS NULL`, or `IS NOT NULL` when `negated`."""

    read: DuckDBRead
    negated: bool


@dataclass(frozen=True, slots=True)
class DuckDBLogic:
    """`AND` or `OR` of two operands, or `NOT` of one; an operand that is
    itself a `DuckDBLogic` is parenthesized."""

    operator: str
    operands: tuple[DuckDBComparison | DuckDBNullTest | DuckDBLogic, ...]


Predicate = DuckDBComparison | DuckDBNullTest | DuckDBLogic


@dataclass(frozen=True, slots=True)
class DuckDBOrderKey:
    """`<value> ASC NULLS LAST`, or `DESC NULLS FIRST` when `descending`, the
    value restated with qualified names as a `having` read is."""

    field: int | None
    function: str | None
    descending: bool


@dataclass(frozen=True, slots=True)
class DuckDBJoin:
    """`<kind> JOIN temp.main."pietto_arrow_<k>"` of the next input, whose
    fields are `"c<start>"` onward, `ON` the `AND` of `<a> = <b>` for each
    pair of fields in `on`, one of this input and one of an earlier one."""

    kind: str
    start: int
    on: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class DuckDBSelect:
    relation: str
    columns: tuple[DuckDBColumn, ...]
    where: Predicate | None
    group_by: tuple[int, ...] = ()
    having: Predicate | None = None
    order_by: tuple[DuckDBOrderKey, ...] = ()
    limit: int | None = None
    joins: tuple[DuckDBJoin, ...] = ()

    @property
    def nodes(self) -> int:
        return node_count(
            len(self.columns),
            sum(c.function is not None and c.field is not None for c in self.columns)
            + sum(len(c.value.operands) for c in self.columns if c.value is not None),
            len(self.group_by),
            sum(_size(p) for p in (self.where, self.having) if p is not None),
            len(self.order_by),
            self.limit is not None,
            sum(1 + 4 * len(j.on) for j in self.joins),
        )


def _size(node: Predicate) -> int:
    if type(node) is DuckDBLogic:
        return 1 + sum(_size(operand) for operand in node.operands)
    return 2 if type(node) is DuckDBNullTest else 3


def node_count(
    columns: int,
    arguments: int,
    keys: int,
    predicates: int,
    orders: int,
    limits: int,
    joins: int = 0,
) -> int:
    """The statement and its relation; a value and a label per column, and the
    read of each column's aggregate that has one or each operand of its
    arithmetic (both `arguments`); a read per group key; the
    `predicates` nodes of `where` and `having`, one per logical operator,
    comparison, null test, read, literal and placeholder; a key and the value
    it reads per order key; the limit's value; and the `joins` nodes, per
    JOIN itself, its relation and, as a predicate, its `ON`."""
    return 2 + 2 * columns + arguments + keys + predicates + 2 * orders + limits + joins


@dataclass(frozen=True, slots=True)
class Token:
    """One rendered byte range; `subject` names its plan owner symbolically:
    ("statement",), ("projection", i), ("export", i), ("aggregate", i),
    ("argument", i), ("computed", i), ("computed", i, k) for the k-th operand
    of an arithmetic column, ("source",), ("filter",), ("aggregation",),
    ("group_key", i), ("having",), ("order",), ("order_key", i), ("limit",),
    ("predicate", *path) and ("having_predicate", *path), the node of the
    `where` or `having` predicate at that path of operand positions, or of
    JOIN j: ("join", j), its input ("join_source", j), its equality p
    ("join_on", j, p) and that equality's side s ("join_on", j, p, s)."""

    start: int
    end: int
    kind: str
    role: str
    subject: tuple[object, ...]


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def relation(position: int) -> str:
    """The registered name of input `position`, in FROM and JOIN order."""
    return f"pietto_arrow_{position}"


def render(ast: DuckDBSelect) -> tuple[bytes, tuple[Token, ...]]:
    chunks: list[bytes] = []
    tokens: list[Token] = []
    offset = 0

    def emit(text: str, kind: str, role: str, *subject: object) -> None:
        nonlocal offset
        chunk = text.encode("utf-8")
        chunks.append(chunk)
        tokens.append(Token(offset, offset + len(chunk), kind, role, subject))
        offset += len(chunk)

    def qualifier(field: int) -> str:
        position = sum(join.start <= field for join in ast.joins)
        return _quoted(relation(position)) + "."

    def value(
        field: int | None,
        function: str | None,
        qualified: bool,
        outer: tuple[object, ...],
        inner: tuple[object, ...],
    ) -> None:
        column = (
            None
            if field is None
            else (qualifier(field) if qualified else "") + _quoted(f"c{field}")
        )
        if column is None:
            emit("count(*)", "syntax", "aggregate", *outer)
        elif function is None:
            emit(column, "identifier", "column", *inner)
        else:
            before, after = AGGREGATES[function]
            emit(before, "syntax", "aggregate_open", *outer)
            emit(column, "identifier", "column", *inner)
            emit(after, "syntax", "aggregate_close", *outer)

    def term(node: object, qualified: bool, subject: tuple[object, ...]) -> None:
        if type(node) is DuckDBRead:
            value(node.field, node.function, qualified, subject, subject)
        elif type(node) is DuckDBParameter:
            emit("CAST(", "syntax", "anchor_open", *subject)
            emit(f"${node.placeholder}", "parameter", "parameter", *subject)
            cast = CASTS[node.tag] + (
                "" if node.decimal is None else _pair(node.decimal)
            )
            emit(f" AS {cast})", "syntax", "anchor_close", *subject)
        elif type(node) is DuckDBLiteral:
            before, text, after = _literal(node.value)
            if before:
                emit(before, "syntax", "anchor_open", *subject)
            emit(text, "literal", "literal", *subject)
            if after:
                emit(after, "syntax", "anchor_close", *subject)

    def arithmetic(node: DuckDBArithmetic, subject: tuple[object, ...]) -> None:
        def operation() -> None:
            if len(node.operands) == 1:
                if node.operator == "-":
                    emit("-", "syntax", "operator", *subject)
                term(node.operands[0], False, (*subject, 0))
                return
            term(node.operands[0], False, (*subject, 0))
            emit(f" {node.operator} ", "syntax", "operator", *subject)
            term(node.operands[1], False, (*subject, 1))

        if node.tag != "Float" or len(node.operands) == 1:
            operation()
            return
        emit("CASE WHEN isinf(", "syntax", "guard", *subject)
        operation()
        emit(f") THEN error({_text(FLOAT_OVERFLOW)})", "syntax", "guard", *subject)
        if node.operator == "*":
            emit(" WHEN (", "syntax", "guard", *subject)
            operation()
            emit(") = 0 AND ", "syntax", "guard", *subject)
            term(node.operands[0], False, (*subject, 0))
            emit(" <> 0 AND ", "syntax", "guard", *subject)
            term(node.operands[1], False, (*subject, 1))
            text = f" <> 0 THEN error({_text(FLOAT_UNDERFLOW)})"
            emit(text, "syntax", "guard", *subject)
        emit(" ELSE (", "syntax", "guard", *subject)
        operation()
        emit(") END", "syntax", "guard", *subject)

    def predicate(
        node: Predicate, qualified: bool, subject: tuple[object, ...]
    ) -> None:
        if type(node) is DuckDBLogic:
            for position, operand in enumerate(node.operands):
                if node.operator == "NOT":
                    emit("NOT ", "syntax", "not", *subject)
                elif position:
                    emit(f" {node.operator} ", "syntax", "logical_operator", *subject)
                inner = (*subject, position)
                grouped = type(operand) is DuckDBLogic
                if grouped:
                    emit("(", "syntax", "group_open", *inner)
                predicate(operand, qualified, inner)
                if grouped:
                    emit(")", "syntax", "group_close", *inner)
        elif type(node) is DuckDBNullTest:
            term(node.read, qualified, (*subject, 0))
            test = " IS NOT NULL" if node.negated else " IS NULL"
            emit(test, "syntax", "null_test", *subject)
        elif type(node) is DuckDBComparison:
            term(node.left, qualified, (*subject, 0))
            emit(f" {node.operator} ", "syntax", "operator", *subject)
            term(node.right, qualified, (*subject, 1))

    emit("SELECT ", "syntax", "select", "statement")
    for position, column in enumerate(ast.columns):
        if position:
            emit(", ", "syntax", "separator", "statement")
        if column.value is not None:
            arithmetic(column.value, ("computed", position))
        else:
            read = ("projection" if column.function is None else "argument", position)
            value(column.field, column.function, False, ("aggregate", position), read)
        emit(" AS ", "syntax", "alias", "projection", position)
        emit(_quoted(column.label), "identifier", "label", "export", position)
    emit(" FROM temp.main.", "syntax", "from", "statement")
    emit(_quoted(ast.relation), "identifier", "relation", "source")
    for position, join in enumerate(ast.joins):
        emit(f" {join.kind} JOIN temp.main.", "syntax", "join", "join", position)
        emit(
            _quoted(relation(position + 1)),
            "identifier",
            "relation",
            "join_source",
            position,
        )
        emit(" ON ", "syntax", "on", "join", position)
        for pair, sides in enumerate(join.on):
            equality = ("join_on", position, pair)
            if pair:
                emit(" AND ", "syntax", "logical_operator", "join", position)
            for side, field in enumerate(sides):
                if side:
                    emit(" = ", "syntax", "operator", *equality)
                value(field, None, False, (), (*equality, side))
    if ast.where is not None:
        emit(" WHERE ", "syntax", "where", "filter")
        predicate(ast.where, False, ("predicate",))
    if ast.group_by:
        emit(" GROUP BY ", "syntax", "group_by", "aggregation")
        for position, field in enumerate(ast.group_by):
            if position:
                emit(", ", "syntax", "separator", "aggregation")
            value(field, None, True, (), ("group_key", position))
    if ast.having is not None:
        emit(" HAVING ", "syntax", "having", "having")
        predicate(ast.having, True, ("having_predicate",))
    if ast.order_by:
        emit(" ORDER BY ", "syntax", "order_by", "order")
        for position, key in enumerate(ast.order_by):
            item = ("order_key", position)
            if position:
                emit(", ", "syntax", "order_separator", *item)
            value(key.field, key.function, True, item, item)
            emit(DIRECTIONS[key.descending], "syntax", "order_direction", *item)
    if ast.limit is not None:
        emit(" LIMIT ", "syntax", "limit", "limit")
        emit(str(ast.limit), "literal", "limit_value", "limit")
    return b"".join(chunks), tuple(tokens)


def _pair(decimal: tuple[int, int]) -> str:
    return f"({decimal[0]},{decimal[1]})"


def literal_decimal(value: Decimal) -> tuple[int, int]:
    """The (precision, scale) of the digits that a `Decimal` literal writes."""
    _sign, digits, exponent = value.as_tuple()
    scale = -exponent if type(exponent) is int and exponent < 0 else 0
    return max(len(digits), scale), scale


def _literal(value: object) -> tuple[str, str, str]:
    """The text before, of and after a literal: an `Int` cast to `BIGINT`, a
    `Float` its shortest round-trip decimal cast from text to `DOUBLE`, so
    `-0.0` keeps its sign (a bare `1.5` is a `DECIMAL`), a quoted `Text` with
    each `'` doubled, `TRUE` or `FALSE`, a `Date` or `Timestamp` its civil
    text cast to `DATE` or `TIMESTAMP`, and a `Decimal` its digits cast to a
    `DECIMAL` of their own precision and scale."""
    if type(value) is bool:
        return "", "TRUE" if value else "FALSE", ""
    if type(value) is int:
        return "CAST(", str(value), " AS BIGINT)"
    if type(value) is float:
        return "CAST(", f"'{value!r}'", " AS DOUBLE)"
    if type(value) is datetime:
        text = value.isoformat(sep=" ", timespec="microseconds")
        return "CAST(", f"'{text}'", " AS TIMESTAMP)"
    if type(value) is date:
        return "CAST(", f"'{value.isoformat()}'", " AS DATE)"
    if type(value) is Decimal:
        pair = _pair(literal_decimal(value))
        return "CAST(", f"'{format(value, 'f')}'", f" AS DECIMAL{pair})"
    return "", "'" + str(value).replace("'", "''") + "'", ""


def _text(value: str) -> str:
    """A Pietto-owned text, quoted as a `Text` literal is."""
    return "'" + value.replace("'", "''") + "'"


def arithmetic_holds(node: object) -> bool:
    """The shape of an arithmetic value that reads a field or key, as a
    constant result field may not; its operands are checked as reads and
    constants are."""
    if type(node) is not DuckDBArithmetic or type(node.operands) is not tuple:
        return False
    if not any(type(operand) is DuckDBRead for operand in node.operands):
        return False
    if len(node.operands) == 2:
        return node.operator in ("+", "-", "*") and node.tag in ("Int", "Float")
    unary = len(node.operands) == 1 and node.operator in ("-", "+")
    return unary and node.tag == "Float"


def int_bounds(
    node: DuckDBArithmetic, bounds: dict[int, tuple[int, int]]
) -> tuple[int, int] | None:
    """The range of an `Int` arithmetic value that interval arithmetic over
    its operands' ranges gives, each read over its field's `bounds` and each
    parameter over signed 64 bits, or None when that range leaves signed 64
    bits (the range proof of arithmetic). It holds every result, but is wider
    than the results where an operand repeats a read, as in `id - id`."""
    ranges: list[tuple[int, int]] = []
    for operand in node.operands:
        if type(operand) is DuckDBLiteral and type(operand.value) is int:
            ranges.append((operand.value, operand.value))
        elif type(operand) is DuckDBRead and operand.field is not None:
            ranges.append(bounds[operand.field])
        else:
            ranges.append(SIGNED64)
    (a, b), (c, d) = ranges
    if node.operator == "+":
        low, high = a + c, b + d
    elif node.operator == "-":
        low, high = a - d, b - c
    else:
        products = (a * c, a * d, b * c, b * d)
        low, high = min(products), max(products)
    return (low, high) if SIGNED64[0] <= low and high <= SIGNED64[1] else None


def written(node: DuckDBArithmetic) -> int:
    """How often the SQL writes each operand of `node`: once, but twice in
    the checks of a `Float` `+` or `-` and four times in those of a `*`."""
    if node.tag != "Float" or len(node.operands) == 1:
        return 1
    return 4 if node.operator == "*" else 2


def literal_holds(value: object) -> bool:
    """A literal in its type's domain, and no NUL written into the SQL text."""
    if type(value) is int:
        return -(2**63) <= value <= MAX_LIMIT
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is datetime:
        return value.tzinfo is None and CIVIL[0] <= value <= CIVIL[1]
    if type(value) is date:
        return CIVIL[0].date() <= value
    if type(value) is Decimal:
        return value.is_finite() and literal_decimal(value)[0] <= MAX_PRECISION
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError:
            return False
        return "\0" not in value
    return type(value) is bool


def _joins_hold(joins: object, fields: int) -> bool:
    """Each JOIN's input starts after the previous one's and before the last
    field, and each equality pairs one of its fields with an earlier one."""
    if type(joins) is not tuple:
        return False
    if not joins:
        return True
    starts = [0]
    for join in joins:
        if (
            type(join) is not DuckDBJoin
            or join.kind not in JOINS
            or type(join.start) is not int
            or not starts[-1] < join.start < fields
            or type(join.on) is not tuple
            or not join.on
        ):
            return False
        starts.append(join.start)
    for join, end in zip(joins, (*starts[2:], fields), strict=True):
        for pair in join.on:
            if (
                type(pair) is not tuple
                or len(pair) != 2
                or any(type(field) is not int for field in pair)
                or sorted(join.start <= field < end for field in pair) != [False, True]
                or not all(0 <= field < end for field in pair)
            ):
                return False
    return True


def ast_rules_hold(ast: DuckDBSelect, fields: int, labels: tuple[str, ...]) -> bool:
    """The SQL rules of the route over inputs of `fields` fields in all and
    the statement's result `labels`."""
    if type(ast) is not DuckDBSelect or ast.relation != RELATION:
        return False
    if not _joins_hold(ast.joins, fields):
        return False
    if type(ast.columns) is not tuple or not ast.columns:
        return False
    if tuple(type(c) for c in ast.columns) != (DuckDBColumn,) * len(ast.columns):
        return False
    if tuple(c.label for c in ast.columns) != labels:
        return False
    computed = tuple(c.value for c in ast.columns if c.value is not None)
    if any(
        not arithmetic_holds(c.value) or (c.field, c.function) != (None, None)
        for c in ast.columns
        if c.value is not None
    ):
        return False
    if type(ast.group_by) is not tuple or type(ast.order_by) is not tuple:
        return False
    if any(
        type(k) is not DuckDBOrderKey or type(k.descending) is not bool
        for k in ast.order_by
    ):
        return False
    if ast.limit is not None and not (
        type(ast.limit) is int and 0 <= ast.limit <= MAX_LIMIT
    ):
        return False
    reads: list[object] = list(ast.group_by)
    values = [(c.field, c.function) for c in ast.columns if c.value is None]
    grouped = bool(ast.group_by) or any(c.function is not None for c in ast.columns)
    # Each placeholder in SQL order, with the type it is cast to.
    placeholders: list[tuple[object, object]] = []

    def term(node: object, having: bool) -> str | None:
        """One comparison side: "read", "constant", or None for no term."""
        if type(node) is DuckDBRead:
            if having:
                values.append((node.field, node.function))
            elif node.function is not None:
                return None
            else:
                reads.append(node.field)
            return "read"
        if (
            type(node) is DuckDBParameter
            and type(node.placeholder) is int
            and node.tag in CASTS
            and (
                node.decimal is None
                if node.tag != "Decimal"
                else type(node.decimal) is tuple
                and len(node.decimal) == 2
                and all(type(k) is int for k in node.decimal)
                and 0 <= node.decimal[1] <= node.decimal[0] <= MAX_PRECISION
                and node.decimal[0] >= 1
            )
        ):
            placeholders.append((node.placeholder, (node.tag, node.decimal)))
            return "constant"
        if type(node) is DuckDBLiteral and literal_holds(node.value):
            return "constant"
        return None

    def holds(node: object, having: bool) -> bool:
        if type(node) is DuckDBLogic:
            arity = 1 if node.operator == "NOT" else 2
            return (
                node.operator in LOGIC
                and type(node.operands) is tuple
                and len(node.operands) == arity
                and all(holds(operand, having) for operand in node.operands)
            )
        if type(node) is DuckDBNullTest:
            return type(node.negated) is bool and term(node.read, having) == "read"
        if type(node) is DuckDBComparison and node.operator in OPERATORS.values():
            sides = [term(node.left, having), term(node.right, having)]
            return sorted(sides, key=str) == ["constant", "read"]
        return False

    for node in computed:
        for operand in node.operands:
            if type(operand) is DuckDBRead:
                if operand.function is not None:
                    return False
                values.append((operand.field, None))
            elif type(operand) is DuckDBLiteral:
                if type(operand.value) is not _VALUE[node.tag]:
                    return False
                if not literal_holds(operand.value):
                    return False
            elif type(operand) is not DuckDBParameter or operand.tag != node.tag:
                return False
            elif type(operand.placeholder) is not int:
                return False
            else:
                placeholders.append(
                    (operand.placeholder, (operand.tag, operand.decimal))
                )
    where, having = ast.where, ast.having
    if where is not None and not holds(where, False):
        return False
    if having is not None and (not grouped or not holds(having, True)):
        return False
    # Placeholders are numbered from 1 in the order of their first use, and
    # each keeps one type.
    numbered: dict[object, object] = {}
    for number, tag in placeholders:
        if number not in numbered and number != len(numbered) + 1:
            return False
        if numbered.setdefault(number, tag) != tag:
            return False
    values.extend((k.field, k.function) for k in ast.order_by)
    for field, function in values:
        if function is None:
            # A grouped statement reads a field only through its group key.
            if grouped and field not in ast.group_by:
                return False
            reads.append(field)
        elif function not in AGGREGATES or not grouped:
            return False
        elif field is not None or function != "count":
            reads.append(field)
    return all(type(k) is int and 0 <= k < fields for k in reads)
