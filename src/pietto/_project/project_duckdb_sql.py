"""The DuckDB adapter's own SQL AST and renderer (AD78.03).

One statement over the registered capture: its columns, or with `group by`
and aggregates their grouped values, filtered in `where` and `having` by
comparisons of a read with a literal or a parameter, null tests and `AND`,
`OR` and `NOT` of these, then its order keys and its static limit. Every
identifier is Pietto-owned except the quoted result labels, so the SQL never
holds the caller's key or column names (docs/spec/duckdb-arrow-route-v1.md).
"""

from __future__ import annotations

from dataclasses import dataclass
import math

__all__: tuple[str, ...] = ()

RELATION = "pietto_arrow_0"
OPERATORS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
# The type each parameter's placeholder is cast to: DuckDB types a bound
# Python value by its value.
CASTS = {"Int": "BIGINT", "Float": "DOUBLE", "Text": "VARCHAR", "Bool": "BOOLEAN"}
LOGIC = ("AND", "OR", "NOT")
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


@dataclass(frozen=True, slots=True)
class DuckDBColumn:
    """Result column `<value> AS "<label>"`: `"c<field>"`, or the aggregate
    `function` of it; `field` is the source field's position in shape order,
    None only in `count(*)`."""

    field: int | None
    label: str
    function: str | None = None


@dataclass(frozen=True, slots=True)
class DuckDBRead:
    """A read in a predicate: in `where` the source field `"c<field>"`; in
    `having` a selected value restated with qualified names, a group key's
    `field` or the aggregate `function` of it."""

    field: int | None
    function: str | None = None


@dataclass(frozen=True, slots=True)
class DuckDBLiteral:
    """An `Int`, `Float`, `Text` or `Bool` literal, with its sign."""

    value: int | float | str | bool


@dataclass(frozen=True, slots=True)
class DuckDBParameter:
    """`CAST($<placeholder> AS <type>)`, the type of the parameter's `tag`."""

    placeholder: int
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
class DuckDBSelect:
    relation: str
    columns: tuple[DuckDBColumn, ...]
    where: Predicate | None
    group_by: tuple[int, ...] = ()
    having: Predicate | None = None
    order_by: tuple[DuckDBOrderKey, ...] = ()
    limit: int | None = None

    @property
    def nodes(self) -> int:
        return node_count(
            len(self.columns),
            sum(c.function is not None and c.field is not None for c in self.columns),
            len(self.group_by),
            sum(_size(p) for p in (self.where, self.having) if p is not None),
            len(self.order_by),
            self.limit is not None,
        )


def _size(node: Predicate) -> int:
    if type(node) is DuckDBLogic:
        return 1 + sum(_size(operand) for operand in node.operands)
    return 2 if type(node) is DuckDBNullTest else 3


def node_count(
    columns: int, arguments: int, keys: int, predicates: int, orders: int, limits: int
) -> int:
    """The statement and its relation; a value and a label per column, and the
    read of each column's aggregate that has one; a read per group key; the
    `predicates` nodes of `where` and `having`, one per logical operator,
    comparison, null test, read, literal and placeholder; a key and the value
    it reads per order key; and the limit's value."""
    return 2 + 2 * columns + arguments + keys + predicates + 2 * orders + limits


@dataclass(frozen=True, slots=True)
class Token:
    """One rendered byte range; `subject` names its plan owner symbolically:
    ("statement",), ("projection", i), ("export", i), ("aggregate", i),
    ("argument", i), ("source",), ("filter",), ("aggregation",),
    ("group_key", i), ("having",), ("order",), ("order_key", i), ("limit",),
    or ("predicate", *path) and ("having_predicate", *path), the node of the
    `where` or `having` predicate at that path of operand positions."""

    start: int
    end: int
    kind: str
    role: str
    subject: tuple[object, ...]


def _quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


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

    def value(
        field: int | None,
        function: str | None,
        qualifier: str,
        outer: tuple[object, ...],
        inner: tuple[object, ...],
    ) -> None:
        column = None if field is None else qualifier + _quoted(f"c{field}")
        if column is None:
            emit("count(*)", "syntax", "aggregate", *outer)
        elif function is None:
            emit(column, "identifier", "column", *inner)
        else:
            before, after = AGGREGATES[function]
            emit(before, "syntax", "aggregate_open", *outer)
            emit(column, "identifier", "column", *inner)
            emit(after, "syntax", "aggregate_close", *outer)

    def term(node: object, qualifier: str, subject: tuple[object, ...]) -> None:
        if type(node) is DuckDBRead:
            value(node.field, node.function, qualifier, subject, subject)
        elif type(node) is DuckDBParameter:
            emit("CAST(", "syntax", "anchor_open", *subject)
            emit(f"${node.placeholder}", "parameter", "parameter", *subject)
            emit(f" AS {CASTS[node.tag]})", "syntax", "anchor_close", *subject)
        elif type(node) is DuckDBLiteral:
            before, text, after = _literal(node.value)
            if before:
                emit(before, "syntax", "anchor_open", *subject)
            emit(text, "literal", "literal", *subject)
            if after:
                emit(after, "syntax", "anchor_close", *subject)

    def predicate(node: Predicate, qualifier: str, subject: tuple[object, ...]) -> None:
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
                predicate(operand, qualifier, inner)
                if grouped:
                    emit(")", "syntax", "group_close", *inner)
        elif type(node) is DuckDBNullTest:
            term(node.read, qualifier, (*subject, 0))
            test = " IS NOT NULL" if node.negated else " IS NULL"
            emit(test, "syntax", "null_test", *subject)
        elif type(node) is DuckDBComparison:
            term(node.left, qualifier, (*subject, 0))
            emit(f" {node.operator} ", "syntax", "operator", *subject)
            term(node.right, qualifier, (*subject, 1))

    qualified = _quoted(ast.relation) + "."
    emit("SELECT ", "syntax", "select", "statement")
    for position, column in enumerate(ast.columns):
        if position:
            emit(", ", "syntax", "separator", "statement")
        read = ("projection" if column.function is None else "argument", position)
        value(column.field, column.function, "", ("aggregate", position), read)
        emit(" AS ", "syntax", "alias", "projection", position)
        emit(_quoted(column.label), "identifier", "label", "export", position)
    emit(" FROM temp.main.", "syntax", "from", "statement")
    emit(_quoted(ast.relation), "identifier", "relation", "source")
    if ast.where is not None:
        emit(" WHERE ", "syntax", "where", "filter")
        predicate(ast.where, "", ("predicate",))
    if ast.group_by:
        emit(" GROUP BY ", "syntax", "group_by", "aggregation")
        for position, field in enumerate(ast.group_by):
            if position:
                emit(", ", "syntax", "separator", "aggregation")
            value(field, None, qualified, (), ("group_key", position))
    if ast.having is not None:
        emit(" HAVING ", "syntax", "having", "having")
        predicate(ast.having, qualified, ("having_predicate",))
    if ast.order_by:
        emit(" ORDER BY ", "syntax", "order_by", "order")
        for position, key in enumerate(ast.order_by):
            item = ("order_key", position)
            if position:
                emit(", ", "syntax", "order_separator", *item)
            value(key.field, key.function, qualified, item, item)
            emit(DIRECTIONS[key.descending], "syntax", "order_direction", *item)
    if ast.limit is not None:
        emit(" LIMIT ", "syntax", "limit", "limit")
        emit(str(ast.limit), "literal", "limit_value", "limit")
    return b"".join(chunks), tuple(tokens)


def _literal(value: object) -> tuple[str, str, str]:
    """The text before, of and after a literal: an `Int` cast to `BIGINT`, a
    `Float` its shortest round-trip decimal cast from text to `DOUBLE`, so
    `-0.0` keeps its sign (a bare `1.5` is a `DECIMAL`), a quoted `Text` with
    each `'` doubled, and `TRUE` or `FALSE`."""
    if type(value) is bool:
        return "", "TRUE" if value else "FALSE", ""
    if type(value) is int:
        return "CAST(", str(value), " AS BIGINT)"
    if type(value) is float:
        return "CAST(", f"'{value!r}'", " AS DOUBLE)"
    return "", "'" + str(value).replace("'", "''") + "'", ""


def literal_holds(value: object) -> bool:
    """A literal in its type's domain, and no NUL written into the SQL text."""
    if type(value) is int:
        return -(2**63) <= value <= MAX_LIMIT
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is str:
        try:
            value.encode("utf-8")
        except UnicodeError:
            return False
        return "\0" not in value
    return type(value) is bool


def ast_rules_hold(ast: DuckDBSelect, fields: int, labels: tuple[str, ...]) -> bool:
    """The SQL rules of the route over a source of `fields` fields and the
    statement's result `labels`."""
    if type(ast) is not DuckDBSelect or ast.relation != RELATION:
        return False
    if type(ast.columns) is not tuple or not ast.columns:
        return False
    if tuple(type(c) for c in ast.columns) != (DuckDBColumn,) * len(ast.columns):
        return False
    if tuple(c.label for c in ast.columns) != labels:
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
    values = [(c.field, c.function) for c in ast.columns]
    grouped = bool(ast.group_by) or any(c.function is not None for c in ast.columns)
    # Each placeholder in SQL order, with the type it is cast to.
    placeholders: list[tuple[object, str]] = []

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
        ):
            placeholders.append((node.placeholder, node.tag))
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

    where, having = ast.where, ast.having
    if where is not None and not holds(where, False):
        return False
    if having is not None and (not grouped or not holds(having, True)):
        return False
    # Placeholders are numbered from 1 in the order of their first use, and
    # each keeps one type.
    numbered: dict[object, str] = {}
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
