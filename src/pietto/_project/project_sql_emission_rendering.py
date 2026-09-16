"""Typed rendering events with ranges captured in the final UTF-8 stream."""

from dataclasses import dataclass

from pietto._project.project_sql_emission_ast import SQLSelect, resource_limits

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
    emit("SELECT ", "syntax", "select", plan.scope)
    for i, column in enumerate(ast.columns):
        if i:
            emit(", ", "syntax", "separator", column.projection.ref)
        identifier(ast.scan.symbol.name, "column_scope", column.input_port.ref)
        emit(".", "syntax", "qualifier", column.projection.ref)
        identifier(column.source_field.column, "column", column.source_port.ref)
        emit(" AS ", "syntax", "alias", column.projection.ref)
        identifier(column.label, "label", column.export.ref)
    emit(" FROM ", "syntax", "from", ast.scan.source.ref)
    identifier(ast.scan.realization.namespace, "namespace", ast.scan.source.ref)
    emit(".", "syntax", "qualifier", ast.scan.source.ref)
    identifier(ast.scan.realization.name, "relation", ast.scan.source.ref)
    emit(" AS ", "syntax", "alias", ast.scan.use.ref)
    identifier(ast.scan.symbol.name, "relation_scope", ast.scan.use.ref)
    return RenderedSQL(ast, b"".join(chunks), tuple(events))
