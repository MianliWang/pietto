"""The DuckDB adapter's own SQL AST and renderer (AD78.03).

One statement over the registered capture: its columns, or with `group by`
and aggregates their grouped values, with at most one comparison of a column
with the query's one parameter in `where` and at most one of a selected value
with it in `having`, then its order keys and its static limit. Every
identifier is Pietto-owned except the quoted result labels, so the SQL never
holds the caller's key or column names (docs/spec/duckdb-arrow-route-v1.md).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__: tuple[str, ...] = ()

RELATION = "pietto_arrow_0"
OPERATORS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
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
class DuckDBComparison:
    """`"c<field>" <operator> CAST($<placeholder> AS BIGINT)`."""

    field: int
    operator: str
    placeholder: int


@dataclass(frozen=True, slots=True)
class DuckDBHaving:
    """`<value> <operator> CAST($<placeholder> AS BIGINT)`, the selected value
    restated with qualified names: a group key's `field`, or the aggregate
    `function` of it."""

    field: int | None
    function: str | None
    operator: str
    placeholder: int


@dataclass(frozen=True, slots=True)
class DuckDBOrderKey:
    """`<value> ASC NULLS LAST`, or `DESC NULLS FIRST` when `descending`, the
    value restated with qualified names as in `DuckDBHaving`."""

    field: int | None
    function: str | None
    descending: bool


@dataclass(frozen=True, slots=True)
class DuckDBSelect:
    relation: str
    columns: tuple[DuckDBColumn, ...]
    where: DuckDBComparison | None
    group_by: tuple[int, ...] = ()
    having: DuckDBHaving | None = None
    order_by: tuple[DuckDBOrderKey, ...] = ()
    limit: int | None = None

    @property
    def nodes(self) -> int:
        return node_count(
            len(self.columns),
            sum(c.function is not None and c.field is not None for c in self.columns),
            len(self.group_by),
            (self.where is not None) + (self.having is not None),
            len(self.order_by),
            self.limit is not None,
        )


def node_count(
    columns: int, arguments: int, keys: int, filters: int, orders: int, limits: int
) -> int:
    """The statement and its relation; a value and a label per column, and the
    read of each column's aggregate that has one; a read per group key; a
    comparison, the value it reads and its placeholder per filter; a key and
    the value it reads per order key; and the limit's value."""
    return 2 + 2 * columns + arguments + keys + 3 * filters + 2 * orders + limits


@dataclass(frozen=True, slots=True)
class Token:
    """One rendered byte range; `subject` names its plan owner symbolically:
    ("statement",), ("projection", i), ("export", i), ("aggregate", i),
    ("argument", i), ("source",), ("filter",), ("left",), ("predicate",),
    ("read",), ("aggregation",), ("group_key", i), ("having",),
    ("having_left",), ("having_predicate",), ("having_read",), ("order",),
    ("order_key", i) or ("limit",)."""

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

    def compare(operator: str, placeholder: int, predicate: str, read: str) -> None:
        emit(f" {operator} ", "syntax", "operator", predicate)
        emit("CAST(", "syntax", "anchor_open", read)
        emit(f"${placeholder}", "parameter", "parameter", read)
        emit(" AS BIGINT)", "syntax", "anchor_close", read)

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
        where = ast.where
        emit(" WHERE ", "syntax", "where", "filter")
        emit(_quoted(f"c{where.field}"), "identifier", "column", "left")
        compare(where.operator, where.placeholder, "predicate", "read")
    if ast.group_by:
        emit(" GROUP BY ", "syntax", "group_by", "aggregation")
        for position, field in enumerate(ast.group_by):
            if position:
                emit(", ", "syntax", "separator", "aggregation")
            value(field, None, qualified, (), ("group_key", position))
    if ast.having is not None:
        having = ast.having
        emit(" HAVING ", "syntax", "having", "having")
        left = ("having_left",)
        value(having.field, having.function, qualified, left, left)
        compare(having.operator, having.placeholder, "having_predicate", "having_read")
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
    where, having = ast.where, ast.having
    if where is not None:
        if (
            type(where) is not DuckDBComparison
            or where.operator not in OPERATORS.values()
            or where.placeholder != 1
        ):
            return False
        reads.append(where.field)
    if having is not None:
        if (
            type(having) is not DuckDBHaving
            or not grouped
            or having.operator not in OPERATORS.values()
            or having.placeholder != 1
        ):
            return False
        values.append((having.field, having.function))
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
