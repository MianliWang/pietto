"""The SQLite adapter's own SQL AST and renderer (AD78.03, PL.47).

One `SELECT` over one `STRICT` table of the `main` schema, aliased `s0`, with
the clauses of the SQL rules of docs/spec/sqlite-project-v1.md; a window is
written inline as `OVER (...)` in its result field (S15). Every node
keeps the plan object it renders as its `subject`, so the document can name
the plan owner of each byte range.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

__all__: tuple[str, ...] = ()

ALIAS = "s0"
OPERATORS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
LOGICAL = {"and": "AND", "or": "OR"}
ARITHMETIC = ("+", "-", "*")
# Each admitted aggregate by its Pietto name, with the SQL function it calls.
FUNCTIONS = {
    "count": "COUNT",
    "count_distinct": "COUNT",
    "min": "MIN",
    "max": "MAX",
    "avg": "AVG",
    "sum": "SUM",
}
MAX_INT = 2**63 - 1
# Each admitted window function by its Pietto name, with the SQL it calls
# (S15); a ranking function takes no argument and no frame.
WINDOWS = {
    "row_number": "ROW_NUMBER",
    "rank": "RANK",
    "dense_rank": "DENSE_RANK",
    "count": "COUNT",
    "min": "MIN",
    "max": "MAX",
    "sum": "SUM",
}
RANKING = frozenset({"row_number", "rank", "dense_rank"})
UNITS = {"rows": "ROWS", "range": "RANGE", "groups": "GROUPS"}
BOUNDS = {
    "unbounded_preceding": "UNBOUNDED PRECEDING",
    "offset_preceding": "PRECEDING",
    "current_row": "CURRENT ROW",
    "offset_following": "FOLLOWING",
    "unbounded_following": "UNBOUNDED FOLLOWING",
}


@dataclass(frozen=True, slots=True)
class SQLiteColumn:
    """`` `s0`.`<column>` ``; `field` is the source field's shape position."""

    field: int
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteLiteral:
    value: bool | int | float | str
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteParameter:
    """`?<number>`, numbered from 1 by first read in the SQL."""

    number: int
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteComparison:
    """`<left> [COLLATE BINARY] <operator> <right>`."""

    operator: str
    left: SQLiteExpression
    right: SQLiteExpression
    collate: bool
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteLogical:
    operator: str
    left: SQLiteExpression
    right: SQLiteExpression
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteNot:
    operand: SQLiteExpression
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteIsNull:
    operand: SQLiteExpression
    negated: bool
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteArithmetic:
    """`<left> <operator> <right>` of `Int` values; `operator` is in ARITHMETIC."""

    operator: str
    left: SQLiteExpression
    right: SQLiteExpression
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteNegative:
    """`-<operand>`; a literal operand makes one signed literal."""

    operand: SQLiteExpression
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteAbs:
    operand: SQLiteExpression
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteAggregate:
    """`COUNT(*)`, `COUNT(x)`, `COUNT(DISTINCT x [COLLATE BINARY])`, `MIN(x)`,
    `MAX(x)`, `AVG(CAST(x AS REAL))` or `SUM(x)`; `function` is the Pietto
    name, a key of FUNCTIONS. The argument of `avg` and `sum` may be
    arithmetic, every other one is a column."""

    function: str
    argument: SQLiteExpression | None
    collate: bool
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteFrame:
    """`<unit> BETWEEN <start> AND <end>`, with no EXCLUDE: each bound is a
    key of BOUNDS and its offset, None unless the bound is an offset."""

    unit: str
    start: tuple[str, int | None]
    end: tuple[str, int | None]
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteWindow:
    """`<FUNCTION>(* | x) OVER ([PARTITION BY ...] [ORDER BY ...] [frame])`;
    `function` is a key of WINDOWS, `partition_by` holds keys with
    `descending` None."""

    function: str
    argument: SQLiteColumn | None
    partition_by: tuple[SQLiteKey, ...]
    order_by: tuple[SQLiteKey, ...]
    frame: SQLiteFrame | None
    subject: object


type SQLiteExpression = (
    SQLiteColumn
    | SQLiteLiteral
    | SQLiteParameter
    | SQLiteComparison
    | SQLiteLogical
    | SQLiteNot
    | SQLiteIsNull
    | SQLiteArithmetic
    | SQLiteNegative
    | SQLiteAbs
    | SQLiteAggregate
    | SQLiteWindow
)
_ATOMS = (
    SQLiteColumn,
    SQLiteLiteral,
    SQLiteParameter,
    SQLiteAbs,
    SQLiteAggregate,
    SQLiteWindow,
)


@dataclass(frozen=True, slots=True)
class SQLiteResult:
    """`<value> AS `<label>``; `subject` is the projection, `export` the label's."""

    value: SQLiteExpression
    label: str
    subject: object
    export: object


@dataclass(frozen=True, slots=True)
class SQLiteKey:
    """A `GROUP BY` key (`descending` None) or an `ORDER BY` key."""

    value: SQLiteColumn | SQLiteAggregate
    collate: bool
    descending: bool | None
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteLimit:
    value: int
    subject: object


@dataclass(frozen=True, slots=True)
class SQLiteSelect:
    """`columns` are the contract columns of the source fields, in shape order."""

    table: str
    columns: tuple[str, ...]
    results: tuple[SQLiteResult, ...]
    where: SQLiteExpression | None
    group_by: tuple[SQLiteKey, ...]
    having: SQLiteExpression | None
    order_by: tuple[SQLiteKey, ...]
    limit: SQLiteLimit | None
    subject: object
    source: object


def _children(node: object) -> tuple[object, ...]:
    if type(node) in (SQLiteComparison, SQLiteLogical, SQLiteArithmetic):
        return (node.left, node.right)  # type: ignore[attr-defined]
    if type(node) in (SQLiteNot, SQLiteIsNull, SQLiteNegative, SQLiteAbs):
        return (node.operand,)  # type: ignore[attr-defined]
    if type(node) is SQLiteAggregate and node.argument is not None:
        return (node.argument,)
    if type(node) is SQLiteWindow:
        argument = () if node.argument is None else (node.argument,)
        return (*argument, *(k.value for k in (*node.partition_by, *node.order_by)))
    return ()


def size(ast: SQLiteSelect) -> tuple[int, int]:
    """The node count of the statement and the depth of its deepest expression:
    the statement, its table, each result, key and limit, and each expression
    node."""
    roots = [
        *(r.value for r in ast.results),
        *(() if ast.where is None else (ast.where,)),
        *(() if ast.having is None else (ast.having,)),
        *(k.value for k in (*ast.group_by, *ast.order_by)),
    ]
    nodes = 2 + len(ast.results) + len(ast.group_by) + len(ast.order_by)
    nodes += ast.limit is not None
    depth = 0
    pending = [(root, 1) for root in roots]
    while pending:
        node, level = pending.pop()
        nodes += 1
        depth = max(depth, level)
        pending.extend((child, level + 1) for child in _children(node))
    return nodes, depth


@dataclass(frozen=True, slots=True)
class Token:
    """One rendered byte range and the plan object it renders."""

    start: int
    end: int
    kind: str
    role: str
    subject: object


def quoted(name: str) -> str:
    return "`" + name.replace("`", "``") + "`"


def literal_text(value: object, negated: bool = False) -> str | None:
    """A literal as the SQL writes it, `negated` when a unary `-` precedes it,
    or None when the SQL has no form for it."""
    if type(value) is bool:
        # SQLite reads TRUE and FALSE as a column or result alias so named.
        return "1" if value else "0"
    if type(value) is int:
        # Only right after a `-` does SQLite read 9223372036854775808 as the
        # INTEGER minimum; anywhere else it reads a REAL.
        return str(value) if 0 <= value <= MAX_INT + negated else None
    if type(value) is float:
        if not math.isfinite(value) or math.copysign(1.0, value) < 0:
            return None
        return repr(value)
    if type(value) is str and "\x00" not in value:
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            return None
        return "'" + value.replace("'", "''") + "'"
    return None


def render(ast: SQLiteSelect) -> tuple[bytes, tuple[Token, ...]]:
    chunks: list[bytes] = []
    tokens: list[Token] = []
    offset = 0

    def emit(text: str, kind: str, role: str, subject: object) -> None:
        nonlocal offset
        chunk = text.encode("utf-8")
        chunks.append(chunk)
        tokens.append(Token(offset, offset + len(chunk), kind, role, subject))
        offset += len(chunk)

    def column(node: SQLiteColumn, name: str) -> None:
        emit(quoted(ALIAS) + ".", "identifier", "alias", node.subject)
        emit(quoted(name), "identifier", "column", node.subject)

    def value(node: object, nested: bool = False) -> None:
        if nested and type(node) not in _ATOMS:
            emit("(", "syntax", "open", node.subject)  # type: ignore[attr-defined]
            value(node)
            emit(")", "syntax", "close", node.subject)  # type: ignore[attr-defined]
        elif type(node) is SQLiteColumn:
            column(node, ast.columns[node.field])
        elif type(node) is SQLiteLiteral:
            text = literal_text(node.value)
            assert text is not None
            emit(text, "literal", "literal", node.subject)
        elif type(node) is SQLiteParameter:
            emit(f"?{node.number}", "parameter", "parameter", node.subject)
        elif type(node) is SQLiteComparison:
            value(node.left, True)
            if node.collate:
                emit(" COLLATE BINARY", "syntax", "collate", node.subject)
            emit(f" {node.operator} ", "syntax", "operator", node.subject)
            value(node.right, True)
        elif type(node) is SQLiteLogical:
            value(node.left, True)
            emit(f" {node.operator} ", "syntax", "operator", node.subject)
            value(node.right, True)
        elif type(node) is SQLiteNot:
            emit("NOT ", "syntax", "operator", node.subject)
            value(node.operand, True)
        elif type(node) is SQLiteIsNull:
            value(node.operand, True)
            text = " IS NOT NULL" if node.negated else " IS NULL"
            emit(text, "syntax", "operator", node.subject)
        elif type(node) is SQLiteArithmetic:
            value(node.left, True)
            emit(f" {node.operator} ", "syntax", "operator", node.subject)
            value(node.right, True)
        elif type(node) is SQLiteNegative:
            emit("-", "syntax", "operator", node.subject)
            operand = node.operand
            if type(operand) is SQLiteLiteral:
                # One signed literal; any other operand that is no column or
                # call is in parentheses, so no `--` starts a comment.
                text = literal_text(operand.value, True)
                assert text is not None
                emit(text, "literal", "literal", operand.subject)
            else:
                value(operand, True)
        elif type(node) is SQLiteAbs:
            emit("ABS(", "syntax", "function", node.subject)
            value(node.operand)
            emit(")", "syntax", "close", node.subject)
        elif type(node) is SQLiteAggregate:
            function = node.function
            emit(FUNCTIONS[function] + "(", "syntax", "function", node.subject)
            if node.argument is None:
                emit("*", "syntax", "star", node.subject)
            else:
                if function == "count_distinct":
                    emit("DISTINCT ", "syntax", "distinct", node.subject)
                elif function == "avg":
                    # The language casts an Int to the target's binary64 first.
                    emit("CAST(", "syntax", "cast", node.subject)
                value(node.argument)
                if node.collate:
                    emit(" COLLATE BINARY", "syntax", "collate", node.subject)
                if function == "avg":
                    emit(" AS REAL)", "syntax", "cast", node.subject)
            emit(")", "syntax", "close", node.subject)
        elif type(node) is SQLiteWindow:
            emit(WINDOWS[node.function] + "(", "syntax", "function", node.subject)
            if node.argument is None:
                if node.function not in RANKING:
                    emit("*", "syntax", "star", node.subject)
            else:
                value(node.argument)
            emit(") OVER (", "syntax", "over", node.subject)
            keys("PARTITION BY", node.partition_by, node.subject, "")
            lead = " " if node.partition_by else ""
            keys("ORDER BY", node.order_by, node.subject, lead)
            lead = " " if node.partition_by or node.order_by else ""
            frame = node.frame
            if frame is not None:
                bounds = [
                    BOUNDS[kind] if offset is None else f"{offset} {BOUNDS[kind]}"
                    for kind, offset in (frame.start, frame.end)
                ]
                text = f"{lead}{UNITS[frame.unit]} BETWEEN {bounds[0]} AND {bounds[1]}"
                emit(text, "syntax", "frame", frame.subject)
            emit(")", "syntax", "close", node.subject)
        else:
            raise TypeError(type(node).__name__)

    def keys(
        clause: str, items: tuple[SQLiteKey, ...], owner: object, lead: str = " "
    ) -> None:
        for position, key in enumerate(items):
            emit(
                f"{lead}{clause} " if position == 0 else ", ",
                "syntax",
                "clause" if position == 0 else "separator",
                owner if position == 0 else key.subject,
            )
            value(key.value)
            if key.collate:
                emit(" COLLATE BINARY", "syntax", "collate", key.subject)
            if key.descending is not None:
                text = " DESC NULLS FIRST" if key.descending else " ASC NULLS LAST"
                emit(text, "syntax", "direction", key.subject)

    emit("SELECT ", "syntax", "clause", ast.subject)
    for position, result in enumerate(ast.results):
        if position:
            emit(", ", "syntax", "separator", ast.subject)
        value(result.value)
        emit(" AS ", "syntax", "alias", result.subject)
        emit(quoted(result.label), "identifier", "label", result.export)
    emit(" FROM ", "syntax", "clause", ast.subject)
    emit(quoted("main") + ".", "identifier", "schema", ast.source)
    emit(quoted(ast.table), "identifier", "table", ast.source)
    emit(" AS ", "syntax", "alias", ast.source)
    emit(quoted(ALIAS), "identifier", "alias", ast.source)
    if ast.where is not None:
        emit(" WHERE ", "syntax", "clause", ast.subject)
        value(ast.where)
    keys("GROUP BY", ast.group_by, ast.subject)
    if ast.having is not None:
        emit(" HAVING ", "syntax", "clause", ast.subject)
        value(ast.having)
    keys("ORDER BY", ast.order_by, ast.subject)
    if ast.limit is not None:
        emit(" LIMIT ", "syntax", "clause", ast.limit.subject)
        emit(str(ast.limit.value), "literal", "limit", ast.limit.subject)
    return b"".join(chunks), tuple(tokens)


def ast_rules_hold(
    ast: SQLiteSelect,
    labels: tuple[str, ...],
    text_fields: frozenset[int],
    text_parameters: frozenset[int],
) -> bool:
    """The SQL rules of the specification that the AST alone decides, over the
    statement's result `labels`, its `Text` source fields and the numbers of its
    `Text` parameters."""
    if type(ast) is not SQLiteSelect or type(ast.table) is not str:
        return False
    if tuple(type(r) for r in ast.results) != (SQLiteResult,) * len(ast.results):
        return False
    if not ast.results or tuple(r.label for r in ast.results) != labels:
        return False
    keys = (*ast.group_by, *ast.order_by)
    if tuple(type(k) for k in keys) != (SQLiteKey,) * len(keys):
        return False
    if any(k.descending is not None for k in ast.group_by) or any(
        type(k.descending) is not bool for k in ast.order_by
    ):
        return False
    if ast.having is not None and not ast.group_by:
        return False  # SQLite runs a HAVING with no GROUP BY; Pietto has none
    if ast.limit is not None and not (
        type(ast.limit) is SQLiteLimit
        and type(ast.limit.value) is int
        and 0 <= ast.limit.value <= MAX_INT
    ):
        return False

    def text(node: object) -> bool:
        if type(node) is SQLiteColumn:
            return node.field in text_fields
        if type(node) is SQLiteParameter:
            return node.number in text_parameters
        return type(node) is SQLiteLiteral and type(node.value) is str

    # HAVING reads only GROUP BY keys and aggregates, never an output alias or
    # a column outside the keys, which SQLite would read from any row, and no
    # NOT or null test, which `check` refuses there.
    grouped = {k.value.field for k in ast.group_by if type(k.value) is SQLiteColumn}
    having: list[object] = [] if ast.having is None else [ast.having]
    while having:
        node = having.pop()
        if type(node) is SQLiteColumn and node.field not in grouped:
            return False
        if type(node) in (SQLiteNot, SQLiteIsNull):
            return False
        if type(node) is not SQLiteAggregate:
            having.extend(_children(node))
    # A window is a whole result field of a statement with no GROUP BY,
    # HAVING or aggregate (S15).
    windows = {id(r.value) for r in ast.results if type(r.value) is SQLiteWindow}
    aggregated = bool(ast.group_by) or ast.having is not None
    numbers: list[int] = []
    pending: list[Any] = [
        *(r.value for r in ast.results),
        *(() if ast.where is None else (ast.where,)),
        *(() if ast.having is None else (ast.having,)),
        *(k.value for k in keys),
    ]
    pending.reverse()
    while pending:  # in rendering order
        node = pending.pop()
        kind = type(node)
        if kind is SQLiteColumn:
            if not (type(node.field) is int and 0 <= node.field < len(ast.columns)):
                return False
        elif kind is SQLiteLiteral:
            if literal_text(node.value) is None:
                return False
        elif kind is SQLiteParameter:
            numbers.append(node.number)
        elif kind is SQLiteComparison:
            if node.operator not in OPERATORS.values() or node.collate is not text(
                node.left
            ):
                return False
        elif kind is SQLiteLogical:
            if node.operator not in LOGICAL.values():
                return False
        elif kind is SQLiteIsNull:
            if type(node.negated) is not bool:
                return False
        elif kind is SQLiteArithmetic:
            if node.operator not in ARITHMETIC:
                return False
        elif kind is SQLiteNegative and type(node.operand) is SQLiteLiteral:
            if literal_text(node.operand.value, True) is None:
                return False
            continue
        elif kind is SQLiteWindow:
            if id(node) not in windows or aggregated or not _window_holds(node, text):
                return False
        elif kind is SQLiteAggregate:
            aggregated = True
            if (
                node.function not in FUNCTIONS
                or (node.argument is None and node.function != "count")
                or (
                    node.argument is not None
                    and node.function not in ("avg", "sum")
                    and type(node.argument) is not SQLiteColumn
                )
                or node.collate
                is not (node.function == "count_distinct" and text(node.argument))
            ):
                return False
        elif kind not in (SQLiteNot, SQLiteNegative, SQLiteAbs):
            return False
        pending.extend(reversed(_children(node)))
    first = list(dict.fromkeys(numbers))
    if first != list(range(1, len(first) + 1)) or (windows and aggregated):
        return False
    return all(k.collate is text(k.value) for k in keys)


def _window_holds(node: SQLiteWindow, text: Any) -> bool:
    """The rules of one window: its function and argument, its keys over
    columns, and its frame; a `sum` frame starts at UNBOUNDED PRECEDING and
    ends at CURRENT ROW or UNBOUNDED FOLLOWING."""
    function, frame = node.function, node.frame
    if function not in WINDOWS:
        return False
    if function in RANKING and node.argument is not None:
        return False
    if function not in RANKING | {"count"} and node.argument is None:
        return False
    if node.argument is not None and type(node.argument) is not SQLiteColumn:
        return False
    for key in (*node.partition_by, *node.order_by):
        if type(key) is not SQLiteKey or type(key.value) is not SQLiteColumn:
            return False
        if key.collate is not text(key.value):
            return False
    if any(k.descending is not None for k in node.partition_by) or any(
        type(k.descending) is not bool for k in node.order_by
    ):
        return False
    if function in RANKING:
        return frame is None
    if type(frame) is not SQLiteFrame or frame.unit not in UNITS:
        return False
    for kind, offset in (frame.start, frame.end):
        if kind not in BOUNDS or (offset is None) is kind.startswith("offset_"):
            return False
        if offset is not None and not (
            type(offset) is int and 0 <= offset <= MAX_INT and frame.unit != "range"
        ):
            return False
    return function != "sum" or (
        frame.start[0] == "unbounded_preceding"
        and frame.end[0] in ("current_row", "unbounded_following")
    )
