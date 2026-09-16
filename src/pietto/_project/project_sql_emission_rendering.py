"""Typed rendering events with ranges captured in the final UTF-8 stream."""

from dataclasses import dataclass

from pietto._project.project_sql_emission_ast import (
    SQLSelect,
    SQLScan,
    SQLNamedUse,
    resource_limits,
)

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
    ast: SQLSelect
    sql: bytes
    events: tuple[RenderingEvent, ...]


class SQLSizeLimit(ValueError):
    pass


def render_sql(ast: SQLSelect) -> RenderedSQL:
    request = ast.request
    quote = '"' if request.family == "postgres" else "`"
    chunks: list[bytes] = []
    events = []
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

    def select(body, subject):
        scan = body.scan
        emit("SELECT ", "syntax", "select", subject)
        for i, column in enumerate(body.columns):
            if i:
                emit(", ", "syntax", "separator", column.projection.ref)
            identifier(scan.symbol.name, "column_scope", column.input_port.ref)
            emit(".", "syntax", "qualifier", column.projection.ref)
            port = (
                column.source_port
                if type(scan) is SQLScan
                else column.producer.terminal
            )
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
    return RenderedSQL(ast, b"".join(chunks), tuple(events))
