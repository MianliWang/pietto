"""Typed rendering events with ranges captured in the final UTF-8 stream."""

from dataclasses import dataclass

from pietto._project.project_sql_emission_ast import (
    SQLJoinQuery,
    SQLSelect,
    SQLColumn,
    SQLScan,
    SQLNamedUse,
    SQLLiteralColumn,
    RowScan,
    RowNamedUse,
    RowStageUse,
    RowJoinUse,
    RowCarryColumn,
    SQLRowQuery,
    resource_limits,
)
from pietto._project.project_sql_emission_contract import BoundSource
from pietto._project.project_sql_emission_joins import (
    JoinBody,
    NATIVE_KINDS,
    SENTINEL,
)
from pietto.ast_nodes import AuthoredJoinKind
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
    ast: SQLSelect | SQLRowQuery | SQLJoinQuery
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


class _Writer:
    """One shared byte/event writer for the row and joined renderers."""

    __slots__ = (
        "request",
        "quote",
        "chunks",
        "events",
        "expression_ranges",
        "offset",
        "limit",
        "subjects",
    )

    def __init__(self, request) -> None:
        self.request = request
        self.quote = '"' if request.family == "postgres" else "`"
        self.chunks: list[bytes] = []
        self.events: list[RenderingEvent] = []
        self.expression_ranges: list[RenderingEvent] = []
        self.offset = 0
        self.limit = resource_limits(request)["sql_bytes"]
        self.subjects = request.source_map.source_map.indexes.subjects

    def emit(self, text, kind, role, subject):
        chunk = text.encode("utf-8")
        if self.offset + len(chunk) > self.limit:
            raise SQLSizeLimit("SQL byte limit exceeded.")
        self.chunks.append(chunk)
        self.events.append(
            RenderingEvent(
                kind,
                role,
                subject,
                self.offset,
                self.offset + len(chunk),
                getattr(self.subjects.get(subject), "origins", ()),
            )
        )
        self.offset += len(chunk)

    def identifier(self, value, role, subject):
        quote = self.quote
        self.emit(
            quote + value.replace(quote, quote * 2) + quote, "identifier", role, subject
        )

    def enclose(self, role, subject, start):
        self.expression_ranges.append(
            RenderingEvent(
                "expression_range",
                role,
                subject,
                start,
                self.offset,
                getattr(self.subjects.get(subject), "origins", ()),
            )
        )

    def constant(self, value):
        nodes = parameters.value_nodes(value)
        opened = []
        for node in nodes[:-1]:
            opened.append((node, self.offset))
            if type(node) is parameters.SQLUnary:
                self.emit(
                    "(" + node.original.expression.operator,
                    "syntax",
                    "unary_open",
                    node.original.ref,
                )
            else:
                self.emit("CAST(", "syntax", "anchor_open", node.original.ref)
        leaf = nodes[-1]
        tag = parameters.tag_of(leaf.original)
        if type(leaf) is parameters.SQLParameter:
            self.emit(
                "$" + str(leaf.use.server_index)
                if self.request.family == "postgres"
                else "?",
                "parameter",
                tag,
                leaf.site.ref,
            )
        else:
            self.emit(
                parameters.literal_token(leaf, self.request.family),
                "literal",
                tag,
                leaf.site.ref,
            )
        for node, start in reversed(opened):
            unary = type(node) is parameters.SQLUnary
            self.emit(
                ")" if unary else parameters.anchor_suffix(node.physical_type),
                "syntax",
                "unary_close" if unary else "anchor_close",
                node.original.ref,
            )
            self.enclose("unary" if unary else "anchor", node.original.ref, start)

    def scalar(self, value, alias):
        """One admitted tree; a reference with its own scope reads that relation."""
        start = self.offset
        if type(value) is rows.SQLStageReference:
            reference = value.original.ref
            scope = alias if value.scope is None else value.scope.name
            self.identifier(scope, "value_scope", value.port)
            self.emit(".", "syntax", "value_qualifier", reference)
            self.identifier(value.column.name, "value_column", value.column.terminal)
            self.enclose("reference", reference, start)
            return
        if type(value) is not rows.SQLOperation:
            self.constant(value)
            return
        reference = value.original.ref
        if value.kind == "sign":
            self.emit(
                "(" + value.original.expression.operator,
                "syntax",
                "unary_open",
                reference,
            )
            self.scalar(value.operands[0], alias)
            self.emit(")", "syntax", "unary_close", reference)
            self.enclose("unary", reference, start)
            return
        if value.kind == "null_test":
            self.emit("(", "syntax", "is_null_open", reference)
            self.scalar(value.operands[0], alias)
            self.emit(
                " IS NOT NULL" if value.original.expression.negated else " IS NULL",
                "syntax",
                "is_null_test",
                reference,
            )
            self.emit(")", "syntax", "is_null_close", reference)
            self.enclose("is_null", reference, start)
            return
        opening, operator, closing, role = OPERATORS[value.kind]
        self.emit("(", "syntax", opening, reference)
        self.scalar(value.operands[0], alias)
        self.emit(operator_token(value), "syntax", operator, reference)
        self.scalar(value.operands[1], alias)
        self.emit(")", "syntax", closing, reference)
        self.enclose(role, reference, start)

    def rendered(self, ast):
        return RenderedSQL(
            ast,
            b"".join(self.chunks),
            tuple(self.events),
            tuple(self.expression_ranges),
        )


def _row_select(w: _Writer, body) -> None:
    """One stage body: its columns, its scan and its optional filter."""
    scan = body.scan
    alias = scan.symbol.name
    w.emit("SELECT ", "syntax", "select", body.block.ref)
    for position, column in enumerate(body.columns):
        if position:
            w.emit(", ", "syntax", "separator", column.export.ref)
        if type(column) is RowCarryColumn:
            w.identifier(alias, "carry_scope", column.input_port)
            w.emit(".", "syntax", "carry_qualifier", column.export.ref)
            w.identifier(column.read.name, "carry_column", column.read.terminal)
        else:
            w.scalar(column.value, alias)
        w.emit(" AS ", "syntax", "alias", column.export.ref)
        w.identifier(column.label, "label", column.export.ref)
    if type(scan) is RowScan:
        w.emit(" FROM ", "syntax", "from", scan.source.ref)
        w.identifier(scan.realization.namespace, "namespace", scan.source.ref)
        w.emit(".", "syntax", "qualifier", scan.source.ref)
        w.identifier(scan.realization.name, "relation", scan.source.ref)
        w.emit(" AS ", "syntax", "alias", scan.use.ref)
        w.identifier(alias, "relation_scope", scan.use.ref)
    elif type(scan) is RowNamedUse:
        reference = scan.body.block.ref
        w.emit(" FROM ", "syntax", "from", reference)
        w.identifier(scan.body.symbol.name, "cte_reference", reference)
        w.emit(" AS ", "syntax", "alias", scan.use.ref)
        w.identifier(alias, "relation_scope", scan.use.ref)
    elif type(scan) is RowJoinUse:
        reference = scan.body.join.ref
        w.emit(" FROM ", "syntax", "from", reference)
        w.identifier(scan.body.symbol.name, "join_reference", reference)
        w.emit(" AS ", "syntax", "alias", scan.tail.ref)
        w.identifier(alias, "join_scope", scan.tail.ref)
    else:
        assert type(scan) is RowStageUse
        reference = scan.body.block.ref
        w.emit(" FROM ", "syntax", "from", reference)
        w.identifier(scan.body.symbol.name, "stage_reference", reference)
        w.emit(" AS ", "syntax", "alias", scan.block.ref)
        w.identifier(alias, "stage_scope", scan.block.ref)
    if body.predicate is not None:
        w.emit(" WHERE ", "syntax", "where", body.predicate.original.ref)
        w.scalar(body.predicate.value, alias)


def render_row_sql(query: SQLRowQuery) -> RenderedSQL:
    """Render ordered stage bodies; every range is a final UTF-8 byte interval."""
    w = _Writer(query.request)
    *cte_bodies, final_body = query.bodies
    if cte_bodies:
        w.emit("WITH ", "syntax", "with", query.request.plan.scope)
        for index, body in enumerate(cte_bodies):
            reference = body.block.ref
            if index:
                w.emit(", ", "syntax", "cte_separator", reference)
            assert body.symbol is not None
            w.identifier(body.symbol.name, "cte_name", reference)
            w.emit(" (", "syntax", "cte_columns_open", reference)
            for position, symbol in enumerate(body.cte_columns):
                if position:
                    w.emit(", ", "syntax", "terminal_separator", symbol.binding)
                w.identifier(symbol.name, "terminal_column", symbol.binding)
            w.emit(") AS (", "syntax", "cte_body_open", reference)
            _row_select(w, body)
            w.emit(")", "syntax", "cte_body_close", reference)
        w.emit(" ", "syntax", "with_body", final_body.block.ref)
    _row_select(w, final_body)
    return w.rendered(query)


def _join_relation(w: _Writer, item) -> None:
    """One JOIN input relation reference, then its generated capture-free alias."""
    reference = item.original.ref
    producer = item.producer
    if type(producer) is BoundSource:
        relation = item.source
        w.identifier(producer.namespace, "join_namespace", relation)
        w.emit(".", "syntax", "join_qualifier", relation)
        w.identifier(producer.name, "join_relation", relation)
    else:
        w.identifier(producer.symbol.name, "join_reference", reference)
    w.emit(" AS ", "syntax", "join_alias", reference)
    w.identifier(item.symbol.name, "join_scope", reference)


def _join_condition(w: _Writer, unit) -> None:
    """Every effective condition component, each in its own role."""
    written = 0
    for item in unit.equalities:
        reference = item.original.ref
        if written:
            w.emit(" AND ", "syntax", "equality_separator", reference)
        start = w.offset
        w.emit("(", "syntax", "equality_open", reference)
        w.identifier(item.left_scope.name, "equality_scope", item.left_port)
        w.emit(".", "syntax", "equality_qualifier", reference)
        w.identifier(item.left.name, "equality_column", item.left.terminal)
        w.emit(" = ", "syntax", "equality_operator", reference)
        w.identifier(item.right_scope.name, "equality_scope", item.right_port)
        w.emit(".", "syntax", "equality_qualifier", reference)
        w.identifier(item.right.name, "equality_column", item.right.terminal)
        w.emit(")", "syntax", "equality_close", reference)
        w.enclose("relationship_equality", reference, start)
        written += 1
    if unit.predicate is not None:
        if written:
            w.emit(" AND ", "syntax", "condition_separator", unit.join.on)
        w.scalar(unit.predicate, "")
        written += 1
    if not written:
        raise ValueError("A rendered JOIN condition requires one component.")


def _join_select(w: _Writer, unit) -> None:
    """One JOIN occurrence's own SELECT: explicit ordered published ports."""
    reference = unit.join.ref
    left, right = unit.inputs
    w.emit("SELECT ", "syntax", "select", reference)
    for position, column in enumerate(unit.columns):
        if position:
            w.emit(", ", "syntax", "separator", column.port.ref)
        w.identifier(column.scope.name, "join_column_scope", column.match.ref)
        w.emit(".", "syntax", "join_column_qualifier", column.port.ref)
        w.identifier(column.read.name, "join_column", column.read.terminal)
        w.emit(" AS ", "syntax", "alias", column.port.ref)
        w.identifier(column.label, "label", column.port.ref)
    w.emit(" FROM ", "syntax", "from", reference)
    _join_relation(w, left)
    if unit.membership is None:
        w.emit(
            " " + NATIVE_KINDS[unit.join.kind] + " ", "syntax", "join_kind", reference
        )
        _join_relation(w, right)
        if unit.join.kind is not AuthoredJoinKind.CROSS:
            w.emit(" ON ", "syntax", "join_on", reference)
            _join_condition(w, unit)
        return
    w.emit(
        " WHERE EXISTS (" if unit.membership == "exists" else " WHERE NOT EXISTS (",
        "syntax",
        "membership_open",
        reference,
    )
    w.emit("SELECT ", "syntax", "membership_select", reference)
    w.emit(SENTINEL, "literal", "membership_sentinel", reference)
    w.emit(" FROM ", "syntax", "membership_from", reference)
    _join_relation(w, right)
    w.emit(" WHERE ", "syntax", "correlation", reference)
    _join_condition(w, unit)
    w.emit(")", "syntax", "membership_close", reference)


def render_join_sql(query) -> RenderedSQL:
    """Render ordered JOIN units and their row stages as one closed statement."""
    w = _Writer(query.request)
    *cte_units, final_body = query.units
    if cte_units:
        w.emit("WITH ", "syntax", "with", query.request.plan.scope)
        for index, unit in enumerate(cte_units):
            reference = unit.join.ref if type(unit) is JoinBody else unit.block.ref
            if index:
                w.emit(", ", "syntax", "cte_separator", reference)
            assert unit.symbol is not None
            w.identifier(unit.symbol.name, "cte_name", reference)
            w.emit(" (", "syntax", "cte_columns_open", reference)
            for position, symbol in enumerate(unit.cte_columns):
                if position:
                    w.emit(", ", "syntax", "terminal_separator", symbol.binding)
                w.identifier(symbol.name, "terminal_column", symbol.binding)
            w.emit(") AS (", "syntax", "cte_body_open", reference)
            if type(unit) is JoinBody:
                _join_select(w, unit)
            else:
                _row_select(w, unit)
            w.emit(")", "syntax", "cte_body_close", reference)
        w.emit(" ", "syntax", "with_body", final_body.block.ref)
    _row_select(w, final_body)
    return w.rendered(query)
