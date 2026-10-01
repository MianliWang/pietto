"""Closed native syntax for the explicit private refinement path.

These nodes are syntax, not authority. The correspondence verifier checks them
against the original emission before either rendering or native submission.
"""

from dataclasses import dataclass, field, fields
from typing import Any

from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_sql_emission_rendering import _Writer
from pietto._project.project_sql_emission_windows import SPELLING

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Expr:
    kind: str
    args: tuple


@dataclass(frozen=True, slots=True)
class Order:
    value: Expr
    direction: str = "asc"


@dataclass(frozen=True, slots=True)
class Relation:
    name: tuple[str, ...]
    alias: str


@dataclass(frozen=True, slots=True)
class Join:
    left: Any
    right: Any
    kind: str
    condition: Expr | None = None


@dataclass(frozen=True, slots=True)
class Select:
    columns: tuple[tuple[str, Expr], ...]
    source: Any
    where: Expr | None = None
    groups: tuple[Expr, ...] = ()
    orders: tuple[Order, ...] = ()
    limit: int | Expr | None = None
    offset: int | Expr = 0
    distinct: bool = False


@dataclass(frozen=True, slots=True)
class SetQuery:
    left: Any
    right: Any
    kind: str
    quantifier: str


@dataclass(frozen=True, slots=True)
class CTE:
    name: str
    columns: tuple[str, ...]
    query: Select | SetQuery


@dataclass(frozen=True, slots=True)
class Statement:
    ctes: tuple[CTE, ...]
    query: Select
    recursive: bool = False


@dataclass(frozen=True, slots=True, eq=False)
class ParameterUse:
    domain: str
    owner: Any = field(repr=False)
    index: int
    value: Any = field(repr=False)
    original: Any = field(default=None, repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class NativeStatement:
    statement: Statement = field(repr=False)
    sql: bytes = field(repr=False)
    uses: tuple[ParameterUse, ...] = field(repr=False)
    arguments: tuple = field(repr=False)


def syntax_work(root, limit):
    """Bound expanded native syntax, including repeated shared expression uses."""
    pending, total = [root], 0
    syntax = (Expr, Order, Relation, Join, Select, SetQuery, CTE, Statement)
    while pending:
        node = pending.pop()
        if type(node) in syntax:
            total += 1
            if total > limit:
                raise ValueError("REFINEMENT_RESOURCE_LIMIT")
            pending.extend(getattr(node, f.name) for f in fields(node))
        elif type(node) is tuple:
            if len(node) > limit or len(pending) + len(node) > 4 * limit:
                raise ValueError("REFINEMENT_RESOURCE_LIMIT")
            pending.extend(node)
    return total


def ref(alias, name):
    return Expr("ref", (alias, name))


def integer(value):
    return Expr("integer", (value,))


def conjunction(*items):
    kept = tuple(item for item in items if item is not None)
    return kept[0] if len(kept) == 1 else Expr("and", kept)


def disjunction(*items):
    return items[0] if len(items) == 1 else Expr("or", tuple(items))


def null_equal(left, right):
    return disjunction(
        conjunction(
            Expr("is_not_null", (left,)),
            Expr("is_not_null", (right,)),
            Expr("=", (left, right)),
        ),
        conjunction(Expr("is_null", (left,)), Expr("is_null", (right,))),
    )


def _parameters(value):
    if type(value) is rows.SQLOperation:
        return tuple(p for child in value.operands for p in _parameters(child))
    if type(value) is rows.SQLStageReference:
        return ()
    return tuple(
        node
        for node in parameters.value_nodes(value)
        if type(node) is parameters.SQLParameter
    )


def render(statement, artifact, page_values=(), *, _guards=None):
    """Render checked syntax with distinct original-slot and page-use domains."""
    request = artifact.request
    family = request.family
    w = _Writer(request)
    subject = request.plan.scope
    uses = []
    from pietto._project.project_execution_binding_verification import native_arguments

    original_arguments = native_arguments(
        artifact,
        tuple(s.site.position.literal.value for s in request.plan.literal_slots),
    )
    original_indices = tuple(u.server_index for u in artifact.parameter_uses)
    page_base = max(original_indices, default=0)

    def emit(text):
        w.emit(text, "syntax", "refinement", subject)

    def ident(value):
        w.identifier(value, "refinement", subject)

    def separated(items, fn, separator=", "):
        for i, item in enumerate(items):
            if i:
                emit(separator)
            fn(item)

    def order(item):
        expression(item.value)
        if item.direction not in ("asc", "desc"):
            raise ValueError("REFINEMENT_ORDER_DIRECTION")
        emit(" ASC" if item.direction == "asc" else " DESC")

    def expression(value):
        if type(value) is not Expr:
            raise ValueError("REFINEMENT_EXPRESSION")
        k, a = value.kind, value.args
        if k == "ref":
            ident(a[0])
            emit(".")
            ident(a[1])
        elif k == "integer":
            if type(a[0]) is not int or not -(1 << 63) <= a[0] < 1 << 63:
                raise ValueError("REFINEMENT_INTEGER")
            emit(str(a[0]))
        elif k == "null":
            emit("NULL")
        elif k in ("and", "or"):
            emit("(")
            if not a:
                emit("TRUE" if k == "and" else "FALSE")
            else:
                separated(a, expression, " AND " if k == "and" else " OR ")
            emit(")")
        elif k in ("=", "<>", "<", ">", "<=", ">=", "+", "-"):
            emit("(")
            expression(a[0])
            emit(" " + k + " ")
            expression(a[1])
            emit(")")
        elif k in ("is_null", "is_not_null", "not"):
            emit("(")
            if k == "not":
                emit("NOT ")
            expression(a[0])
            if k != "not":
                emit(" IS NULL" if k == "is_null" else " IS NOT NULL")
            emit(")")
        elif k == "cast_integer":
            emit("CAST(")
            expression(a[0])
            emit(" AS BIGINT)" if family == "postgres" else " AS SIGNED)")
        elif k == "case":
            emit("CASE WHEN ")
            expression(a[0])
            emit(" THEN ")
            expression(a[1])
            emit(" ELSE ")
            expression(a[2])
            emit(" END")
        elif k in ("scalar_query", "exists"):
            emit("(" if k == "scalar_query" else "EXISTS (")
            query(a[0])
            emit(")")
        elif k == "original_scalar":
            original, alias = a
            w.scalar(original, alias)
            for parameter in _parameters(original):
                use = parameter.use
                uses.append(
                    ParameterUse(
                        "original",
                        use.slot,
                        use.server_index if family == "postgres" else len(uses) + 1,
                        original_arguments[use.server_index - 1],
                        use,
                    )
                )
        elif k == "original_aggregate":
            from pietto._project.project_sql_emission_rendering import _aggregate_value

            _aggregate_value(w, a[0], a[1])
            if a[0].argument is not None:
                for p in _parameters(a[0].argument):
                    uses.append(
                        ParameterUse(
                            "original",
                            p.use.slot,
                            p.use.server_index
                            if family == "postgres"
                            else len(uses) + 1,
                            original_arguments[p.use.server_index - 1],
                            p.use,
                        )
                    )
        elif k == "window":
            original, alias, partitions, orders, whole_frame = a
            emit(SPELLING[original.function] + "(")
            for i, arg in enumerate(original.arguments):
                if i:
                    emit(", ")
                if arg.read is not None:
                    expression(ref(alias, arg.read.name))
                else:
                    emit(arg.literal)
            emit(") OVER (")
            if partitions:
                emit("PARTITION BY ")
                separated(partitions, expression)
            if orders:
                if partitions:
                    emit(" ")
                emit("ORDER BY ")
                separated(orders, order)
            if whole_frame:
                emit(" ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING")
            emit(")")
        elif k == "guard_control":
            from pietto._project.project_guard_program import GuardStatement

            if type(_guards) is not GuardStatement or len(a) != 1:
                raise ValueError("GUARD_CONTROL_CONTEXT")
            control = a[0]
            positions = tuple(i for i, c in enumerate(_guards.controls) if c is control)
            if len(positions) != 1:
                raise ValueError("GUARD_CONTROL_IDENTITY")
            index = (
                page_base + positions[0] + 1 if family == "postgres" else len(uses) + 1
            )
            emit("CAST($" + str(index) + " AS BIGINT)" if family == "postgres" else "?")
            uses.append(ParameterUse("guard", control, index, control.value))
        elif k in ("page", "page_limit"):
            index, tag, precision, scale = a
            raw = page_values[index]
            wire = (
                str(raw)
                if tag == "Decimal" and raw is not None
                else int(raw)
                if family == "mysql" and tag == "Bool" and raw is not None
                else raw
            )
            server_index = (
                page_base + index + 1 if family == "postgres" else len(uses) + 1
            )
            # Explicit casts type NULL and Decimal controls; original binding
            # sites and their domains remain owned by S04.
            names = (
                {
                    "Int": "BIGINT",
                    "Bool": "BOOLEAN",
                    "Text": "TEXT",
                    "Decimal": "NUMERIC",
                }
                if family == "postgres"
                else {
                    "Int": "SIGNED",
                    "Bool": "SIGNED",
                    "Text": "CHAR CHARACTER SET utf8mb4",
                }
            )
            cast = names.get(tag)
            if tag == "Decimal" and family == "mysql":
                if (
                    type(precision) is not int
                    or type(scale) is not int
                    or not 1 <= precision <= 65
                    or not 0 <= scale <= min(30, precision)
                ):
                    raise ValueError("REFINEMENT_PAGE_TYPE")
                cast = f"DECIMAL({precision},{scale})"
            if cast is None:
                raise ValueError("REFINEMENT_PAGE_TYPE")
            if k == "page_limit" and family == "mysql":
                emit("?")
            else:
                emit("CAST(")
                emit("$" + str(server_index) if family == "postgres" else "?")
                emit(" AS " + cast + ")")
            uses.append(ParameterUse("page", index, server_index, wire))
        else:
            raise ValueError("REFINEMENT_EXPRESSION_KIND")

    def source(value):
        if type(value) is Relation:
            separated(value.name, ident, ".")
            emit(" AS ")
            ident(value.alias)
        elif type(value) is Join:
            if value.kind not in ("INNER", "CROSS", "LEFT", "RIGHT", "FULL"):
                raise ValueError("REFINEMENT_JOIN_KIND")
            emit("(")
            source(value.left)
            emit(" " + value.kind + " JOIN ")
            source(value.right)
            if value.kind != "CROSS":
                emit(" ON ")
                expression(value.condition)
            emit(")")
        else:
            raise ValueError("REFINEMENT_RELATION")

    def column(item):
        expression(item[1])
        emit(" AS ")
        ident(item[0])

    def query(value):
        if type(value) is SetQuery:
            if value.kind not in (
                "UNION",
                "INTERSECT",
                "EXCEPT",
            ) or value.quantifier not in ("ALL", "DISTINCT"):
                raise ValueError("REFINEMENT_SET_KIND")
            emit("(")
            query(value.left)
            emit(") " + value.kind + " " + value.quantifier + " (")
            query(value.right)
            emit(")")
            return
        if type(value) is not Select:
            raise ValueError("REFINEMENT_SELECT")
        emit("SELECT DISTINCT " if value.distinct else "SELECT ")
        separated(value.columns, column)
        if value.source is not None or _guards is None:
            emit(" FROM ")
            source(value.source)
        if value.where is not None:
            emit(" WHERE ")
            expression(value.where)
        if value.groups:
            emit(" GROUP BY ")
            separated(value.groups, expression)
        if value.orders:
            emit(" ORDER BY ")
            separated(value.orders, order)
        if value.limit is not None:
            emit(" LIMIT ")
            expression(
                value.limit if type(value.limit) is Expr else integer(value.limit)
            )
        if value.offset:
            emit(" OFFSET ")
            expression(
                value.offset
                if type(value.offset) is Expr and _guards is not None
                else integer(value.offset)
            )

    if statement.ctes:
        emit("WITH RECURSIVE " if statement.recursive else "WITH ")
        for i, cte in enumerate(statement.ctes):
            if i:
                emit(", ")
            ident(cte.name)
            emit(" (")
            separated(cte.columns, ident)
            emit(") AS (")
            query(cte.query)
            emit(")")
        emit(" ")
    query(statement.query)
    if family == "postgres":
        by_index = {}
        for use in uses:
            previous = by_index.setdefault(use.index, use)
            if (
                previous.domain != use.domain
                or previous.owner is not use.owner
                and previous.owner != use.owner
            ):
                raise ValueError("REFINEMENT_PARAMETER_COLLISION")
        if sorted(by_index) != list(range(1, max(by_index, default=0) + 1)):
            raise ValueError("REFINEMENT_PARAMETER_GAP")
        arguments = tuple(by_index[i].value for i in sorted(by_index))
    else:
        arguments = tuple(use.value for use in uses)
    return NativeStatement(statement, b"".join(w.chunks), tuple(uses), arguments)
