"""Typed rendering events with ranges captured in the final UTF-8 stream."""

from dataclasses import dataclass

from pietto._project.project_sql_emission_ast import (
    SQLSelect,
    SQLColumn,
    SQLScan,
    SQLNamedUse,
    SQLLiteralColumn,
    RowScan,
    RowNamedUse,
    RowStageUse,
    RowCarryColumn,
    SQLRowQuery,
    resource_limits,
)
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_rows as rows

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class RenderingEvent:
    kind: str
    role: str
    subject: object
    start: int
    end: int
    origins: tuple[object, ...]


@dataclass(frozen=True, slots=True, eq=False)
class RenderedSQL:
    ast: SQLSelect | SQLRowQuery
    sql: bytes
    events: tuple[RenderingEvent, ...]
    expression_ranges: tuple[RenderingEvent, ...] = ()


class SQLSizeLimit(ValueError):
    pass


def render_sql(ast: SQLSelect) -> RenderedSQL:
    request = ast.request
    quote = '"' if request.family == "postgres" else "`"
    chunks: list[bytes] = []
    events = []
    expression_ranges = []
    offset = 0
    limit = resource_limits(request)["sql_bytes"]
    subjects = request.source_map.source_map.indexes.subjects

    def emit(text, kind, role, subject):
        nonlocal offset
        chunk = text.encode("utf-8")
        if offset + len(chunk) > limit:
            raise SQLSizeLimit("SQL byte limit exceeded.")
        chunks.append(chunk)
        events.append(
            RenderingEvent(
                kind,
                role,
                subject,
                offset,
                offset + len(chunk),
                getattr(subjects.get(subject), "origins", ()),
            )
        )
        offset += len(chunk)

    def identifier(value, role, subject):
        emit(
            quote + value.replace(quote, quote * 2) + quote, "identifier", role, subject
        )

    plan = request.plan

    def scalar(value):
        nodes = parameters.value_nodes(value)
        opened = []
        for node in nodes[:-1]:
            opened.append((node, offset))
            if type(node) is parameters.SQLUnary:
                emit(
                    "(" + node.original.expression.operator,
                    "syntax",
                    "unary_open",
                    node.original.ref,
                )
            else:
                emit("CAST(", "syntax", "anchor_open", node.original.ref)
        leaf = nodes[-1]
        tag = parameters.tag_of(leaf.original)
        if type(leaf) is parameters.SQLParameter:
            emit(
                "$" + str(leaf.use.server_index)
                if request.family == "postgres"
                else "?",
                "parameter",
                tag,
                leaf.site.ref,
            )
        else:
            emit(
                parameters.literal_token(leaf, request.family),
                "literal",
                tag,
                leaf.site.ref,
            )
        for node, start in reversed(opened):
            unary = type(node) is parameters.SQLUnary
            emit(
                ")" if unary else parameters.anchor_suffix(node.physical_type),
                "syntax",
                "unary_close" if unary else "anchor_close",
                node.original.ref,
            )
            expression_ranges.append(
                RenderingEvent(
                    "expression_range",
                    "unary" if unary else "anchor",
                    node.original.ref,
                    start,
                    offset,
                    getattr(subjects.get(node.original.ref), "origins", ()),
                )
            )

    def select(body, subject):
        scan = body.scan
        emit("SELECT ", "syntax", "select", subject)
        for i, column in enumerate(body.columns):
            if i:
                emit(", ", "syntax", "separator", column.projection.ref)
            if type(column) is SQLLiteralColumn and column.value is not None:
                scalar(column.value)
            else:
                if type(column) is SQLLiteralColumn:
                    assert column.producer is not None
                    input_port = column.producer.input_port
                    port = column.producer.terminal
                else:
                    assert isinstance(column, SQLColumn)
                    input_port = column.input_port
                    port = (
                        column.source_port
                        if type(scan) is SQLScan
                        else column.producer.terminal
                    )
                identifier(scan.symbol.name, "column_scope", input_port.ref)
                emit(".", "syntax", "qualifier", column.projection.ref)
                identifier(column.symbol.name, "column", port.ref)
            emit(" AS ", "syntax", "alias", column.projection.ref)
            identifier(column.label, "label", column.export.ref)
        if type(scan) is SQLScan:
            emit(" FROM ", "syntax", "from", scan.source.ref)
            identifier(scan.realization.namespace, "namespace", scan.source.ref)
            emit(".", "syntax", "qualifier", scan.source.ref)
            identifier(scan.realization.name, "relation", scan.source.ref)
        else:
            assert type(scan) is SQLNamedUse
            ref = scan.cte.definition.original.ref
            emit(" FROM ", "syntax", "from", ref)
            identifier(scan.cte.symbol.name, "cte_reference", ref)
        emit(" AS ", "syntax", "alias", scan.use.ref)
        identifier(scan.symbol.name, "relation_scope", scan.use.ref)

    if ast.ctes:
        emit("WITH ", "syntax", "with", plan.scope)
        for i, cte in enumerate(ast.ctes):
            ref = cte.definition.original.ref
            if i:
                emit(", ", "syntax", "cte_separator", ref)
            identifier(cte.symbol.name, "cte_name", ref)
            emit(" (", "syntax", "cte_columns_open", ref)
            for j, symbol in enumerate(cte.columns):
                if j:
                    emit(", ", "syntax", "terminal_separator", symbol.binding)
                identifier(symbol.name, "terminal_column", symbol.binding)
            emit(") AS (", "syntax", "cte_body_open", ref)
            select(cte.body, ref)
            emit(")", "syntax", "cte_body_close", ref)
        emit(" ", "syntax", "with_body", ast.definition.original.ref)
    select(ast, plan.scope)
    return RenderedSQL(ast, b"".join(chunks), tuple(events), tuple(expression_ranges))


OPERATORS = {
    "arithmetic": ("binary_open", "arithmetic_operator", "binary_close", "binary"),
    "logical": ("binary_open", "logical_operator", "binary_close", "binary"),
    "comparison": (
        "comparison_open",
        "comparison_operator",
        "comparison_close",
        "comparison",
    ),
}


def operator_token(node):
    operator = node.original.expression.operator
    if node.kind == "comparison":
        return rows.COMPARISONS[operator]
    return " " + (operator.upper() if node.kind == "logical" else operator) + " "


def render_row_sql(query: SQLRowQuery) -> RenderedSQL:
    """Render ordered stage bodies; every range is a final UTF-8 byte interval."""
    request = query.request
    quote = '"' if request.family == "postgres" else "`"
    chunks: list[bytes] = []
    events: list[RenderingEvent] = []
    expression_ranges: list[RenderingEvent] = []
    offset = 0
    limit = resource_limits(request)["sql_bytes"]
    subjects = request.source_map.source_map.indexes.subjects

    def emit(text, kind, role, subject):
        nonlocal offset
        chunk = text.encode("utf-8")
        if offset + len(chunk) > limit:
            raise SQLSizeLimit("SQL byte limit exceeded.")
        chunks.append(chunk)
        events.append(
            RenderingEvent(
                kind,
                role,
                subject,
                offset,
                offset + len(chunk),
                getattr(subjects.get(subject), "origins", ()),
            )
        )
        offset += len(chunk)

    def identifier(value, role, subject):
        emit(
            quote + value.replace(quote, quote * 2) + quote, "identifier", role, subject
        )

    def enclose(role, subject, start):
        expression_ranges.append(
            RenderingEvent(
                "expression_range",
                role,
                subject,
                start,
                offset,
                getattr(subjects.get(subject), "origins", ()),
            )
        )

    def scalar(value, alias):
        start = offset
        if type(value) is rows.SQLStageReference:
            reference = value.original.ref
            identifier(alias, "value_scope", value.port)
            emit(".", "syntax", "value_qualifier", reference)
            identifier(value.column.name, "value_column", value.column.terminal)
            enclose("reference", reference, start)
            return
        if type(value) is not rows.SQLOperation:
            constant(value)
            return
        reference = value.original.ref
        if value.kind == "sign":
            emit(
                "(" + value.original.expression.operator,
                "syntax",
                "unary_open",
                reference,
            )
            scalar(value.operands[0], alias)
            emit(")", "syntax", "unary_close", reference)
            enclose("unary", reference, start)
            return
        if value.kind == "null_test":
            emit("(", "syntax", "is_null_open", reference)
            scalar(value.operands[0], alias)
            emit(
                " IS NOT NULL" if value.original.expression.negated else " IS NULL",
                "syntax",
                "is_null_test",
                reference,
            )
            emit(")", "syntax", "is_null_close", reference)
            enclose("is_null", reference, start)
            return
        opening, operator, closing, role = OPERATORS[value.kind]
        emit("(", "syntax", opening, reference)
        scalar(value.operands[0], alias)
        emit(operator_token(value), "syntax", operator, reference)
        scalar(value.operands[1], alias)
        emit(")", "syntax", closing, reference)
        enclose(role, reference, start)

    def constant(value):
        nodes = parameters.value_nodes(value)
        opened = []
        for node in nodes[:-1]:
            opened.append((node, offset))
            if type(node) is parameters.SQLUnary:
                emit(
                    "(" + node.original.expression.operator,
                    "syntax",
                    "unary_open",
                    node.original.ref,
                )
            else:
                emit("CAST(", "syntax", "anchor_open", node.original.ref)
        leaf = nodes[-1]
        tag = parameters.tag_of(leaf.original)
        if type(leaf) is parameters.SQLParameter:
            emit(
                "$" + str(leaf.use.server_index)
                if request.family == "postgres"
                else "?",
                "parameter",
                tag,
                leaf.site.ref,
            )
        else:
            emit(
                parameters.literal_token(leaf, request.family),
                "literal",
                tag,
                leaf.site.ref,
            )
        for node, start in reversed(opened):
            unary = type(node) is parameters.SQLUnary
            emit(
                ")" if unary else parameters.anchor_suffix(node.physical_type),
                "syntax",
                "unary_close" if unary else "anchor_close",
                node.original.ref,
            )
            expression_ranges.append(
                RenderingEvent(
                    "expression_range",
                    "unary" if unary else "anchor",
                    node.original.ref,
                    start,
                    offset,
                    getattr(subjects.get(node.original.ref), "origins", ()),
                )
            )

    def select(body):
        scan = body.scan
        alias = scan.symbol.name
        emit("SELECT ", "syntax", "select", body.block.ref)
        for position, column in enumerate(body.columns):
            if position:
                emit(", ", "syntax", "separator", column.export.ref)
            if type(column) is RowCarryColumn:
                identifier(alias, "carry_scope", column.input_port)
                emit(".", "syntax", "carry_qualifier", column.export.ref)
                identifier(column.read.name, "carry_column", column.read.terminal)
            else:
                scalar(column.value, alias)
            emit(" AS ", "syntax", "alias", column.export.ref)
            identifier(column.label, "label", column.export.ref)
        if type(scan) is RowScan:
            emit(" FROM ", "syntax", "from", scan.source.ref)
            identifier(scan.realization.namespace, "namespace", scan.source.ref)
            emit(".", "syntax", "qualifier", scan.source.ref)
            identifier(scan.realization.name, "relation", scan.source.ref)
            emit(" AS ", "syntax", "alias", scan.use.ref)
            identifier(alias, "relation_scope", scan.use.ref)
        elif type(scan) is RowNamedUse:
            reference = scan.body.block.ref
            emit(" FROM ", "syntax", "from", reference)
            identifier(scan.body.symbol.name, "cte_reference", reference)
            emit(" AS ", "syntax", "alias", scan.use.ref)
            identifier(alias, "relation_scope", scan.use.ref)
        else:
            assert type(scan) is RowStageUse
            reference = scan.body.block.ref
            emit(" FROM ", "syntax", "from", reference)
            identifier(scan.body.symbol.name, "stage_reference", reference)
            emit(" AS ", "syntax", "alias", scan.block.ref)
            identifier(alias, "stage_scope", scan.block.ref)
        if body.predicate is not None:
            emit(" WHERE ", "syntax", "where", body.predicate.original.ref)
            scalar(body.predicate.value, alias)

    *cte_bodies, final_body = query.bodies
    if cte_bodies:
        emit("WITH ", "syntax", "with", request.plan.scope)
        for index, body in enumerate(cte_bodies):
            reference = body.block.ref
            if index:
                emit(", ", "syntax", "cte_separator", reference)
            assert body.symbol is not None
            identifier(body.symbol.name, "cte_name", reference)
            emit(" (", "syntax", "cte_columns_open", reference)
            for position, symbol in enumerate(body.cte_columns):
                if position:
                    emit(", ", "syntax", "terminal_separator", symbol.binding)
                identifier(symbol.name, "terminal_column", symbol.binding)
            emit(") AS (", "syntax", "cte_body_open", reference)
            select(body)
            emit(")", "syntax", "cte_body_close", reference)
        emit(" ", "syntax", "with_body", final_body.block.ref)
    select(final_body)
    return RenderedSQL(query, b"".join(chunks), tuple(events), tuple(expression_ranges))
