"""The DuckDB adapter's own SQL AST and renderer (AD78.03).

One B1 statement: a projection of the registered capture's columns, with at
most one comparison of a column with the query's one parameter. Every
identifier is Pietto-owned except the quoted result labels, so the SQL never
holds the caller's key or column names (docs/spec/duckdb-arrow-route-v1.md).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__: tuple[str, ...] = ()

RELATION = "pietto_arrow_0"
OPERATORS = {"==": "=", "!=": "<>", "<": "<", "<=": "<=", ">": ">", ">=": ">="}


@dataclass(frozen=True, slots=True)
class DuckDBColumn:
    """Result column `"c<field>" AS "<label>"`; `field` is the source field's
    position in shape order."""

    field: int
    label: str


@dataclass(frozen=True, slots=True)
class DuckDBComparison:
    """`"c<field>" <operator> CAST($<placeholder> AS BIGINT)`."""

    field: int
    operator: str
    placeholder: int


@dataclass(frozen=True, slots=True)
class DuckDBSelect:
    relation: str
    columns: tuple[DuckDBColumn, ...]
    where: DuckDBComparison | None

    @property
    def nodes(self) -> int:
        return node_count(len(self.columns), self.where is not None)


def node_count(columns: int, filtered: bool) -> int:
    """The statement, its relation, a read and a label per column, and a
    comparison with its read and placeholder."""
    return 2 + 2 * columns + (3 if filtered else 0)


@dataclass(frozen=True, slots=True)
class Token:
    """One rendered byte range; `subject` names its plan owner symbolically:
    ("statement",), ("projection", i), ("export", i), ("source",),
    ("filter",), ("left",), ("predicate",) or ("read",)."""

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

    emit("SELECT ", "syntax", "select", "statement")
    for position, column in enumerate(ast.columns):
        if position:
            emit(", ", "syntax", "separator", "statement")
        emit(
            _quoted(f"c{column.field}"), "identifier", "column", "projection", position
        )
        emit(" AS ", "syntax", "alias", "projection", position)
        emit(_quoted(column.label), "identifier", "label", "export", position)
    emit(" FROM temp.main.", "syntax", "from", "statement")
    emit(_quoted(ast.relation), "identifier", "relation", "source")
    if ast.where is not None:
        where = ast.where
        emit(" WHERE ", "syntax", "where", "filter")
        emit(_quoted(f"c{where.field}"), "identifier", "column", "left")
        emit(f" {where.operator} ", "syntax", "operator", "predicate")
        emit("CAST(", "syntax", "anchor_open", "read")
        emit(f"${where.placeholder}", "parameter", "parameter", "read")
        emit(" AS BIGINT)", "syntax", "anchor_close", "read")
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
    reads = [c.field for c in ast.columns]
    where = ast.where
    if where is not None:
        if (
            type(where) is not DuckDBComparison
            or where.operator not in OPERATORS.values()
            or where.placeholder != 1
        ):
            return False
        reads.append(where.field)
    return all(type(k) is int and 0 <= k < fields for k in reads)
