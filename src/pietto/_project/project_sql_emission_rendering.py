"""Typed rendering events with ranges captured in the final UTF-8 stream."""

from dataclasses import dataclass
from pietto._project.project_sql_emission_contract import emission_origin_subjects

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
    CompiledSQLQuery,
    inline_body,
    resource_limits,
)
from pietto._project.project_sql_emission_aggregation import (
    AggregateKeyColumn,
    AggregateProjectionColumn,
    AggregateValueColumn,
)
from pietto._project import project_sql_emission_windows as windowing
from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_sets as setting
from pietto._project import project_sql_emission_values as valuing
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
    subjects = emission_origin_subjects(request)

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
        self.subjects = emission_origin_subjects(request)

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

    def parameter_read(self, value):
        """CAST(<placeholder> AS <carrier>): the same anchor a bound literal uses."""
        start = self.offset
        reference = value.original.ref
        self.emit("CAST(", "syntax", "anchor_open", reference)
        self.emit(
            "$" + str(value.use.server_index)
            if self.request.family == "postgres"
            else "?",
            "parameter",
            value.original.parameter.tag,
            reference,
        )
        self.emit(
            parameters.anchor_suffix(value.physical_type),
            "syntax",
            "anchor_close",
            reference,
        )
        self.enclose("anchor", reference, start)

    def block_read(self, value, alias):
        """``EXISTS (SELECT 1 FROM <producer> AS <alias>)`` or, for a scalar
        read, ``(SELECT <alias>.<column> FROM <producer> AS <alias>)``."""
        if value.kind in ("in", "not_in"):
            self.block_membership(value, alias)
            return
        start = self.offset
        reference = value.original.ref
        target = value.target
        kind = value.kind
        if kind == "scalar":
            read = rows.block_column(target, value.column)
            assert read is not None
            self.emit("(", "syntax", "scalar_open", reference)
            self.emit("SELECT ", "syntax", "scalar_select", reference)
            self.identifier(target.symbol.name, "scalar_scope", target.use.ref)
            self.emit(".", "syntax", "scalar_column_qualifier", reference)
            self.identifier(read[0], "scalar_column", reference)
        else:
            self.emit("EXISTS (", "syntax", "exists_open", reference)
            self.emit("SELECT ", "syntax", "exists_select", reference)
            self.emit(SENTINEL, "literal", "exists_sentinel", reference)
        self.emit(" FROM ", "syntax", f"{kind}_from", reference)
        if target.source is not None:
            relation = target.source.ref
            self.identifier(target.producer.namespace, f"{kind}_namespace", relation)
            self.emit(".", "syntax", f"{kind}_qualifier", relation)
            self.identifier(target.producer.name, f"{kind}_relation", relation)
        elif inline_body(target.producer):
            # A capturing let is the derived relation of its own read.
            producer = target.producer.block.ref
            self.emit("(", "syntax", "inline_open", producer)
            _unit_select(self, target.producer)
            self.emit(")", "syntax", "inline_close", producer)
        else:
            producer = target.producer.block.ref
            self.identifier(target.producer.symbol.name, f"{kind}_reference", producer)
        self.emit(" AS ", "syntax", f"{kind}_alias", target.use.ref)
        self.identifier(target.symbol.name, f"{kind}_scope", target.use.ref)
        self.emit(")", "syntax", f"{kind}_close", reference)
        self.enclose(kind, reference, start)

    def block_membership(self, value, alias):
        """``(<v> [NOT] IN (SELECT <e>.<c> FROM <producer> AS <e>))``.

        The producer is a top-level CTE, a qualified source or a capturing
        let's inline chain; a LIMIT stays inside that CTE or derived table.
        """
        start = self.offset
        reference = value.original.ref
        target = value.target
        column = rows.block_read_column(target)
        if column is None or len(value.operands) != 1:
            raise ValueError("unrenderable membership read")
        self.emit("(", "syntax", "in_open", reference)
        self.scalar(value.operands[0], alias)
        self.emit(
            " NOT IN (" if value.kind == "not_in" else " IN (",
            "syntax",
            "in_operator",
            reference,
        )
        self.emit("SELECT ", "syntax", "in_select", reference)
        self.identifier(target.symbol.name, "in_column_scope", target.use.ref)
        self.emit(".", "syntax", "in_column_qualifier", target.use.ref)
        if target.source is not None:
            relation = target.source.ref
            self.identifier(column[0], "in_source_column", relation)
            self.emit(" FROM ", "syntax", "in_from", reference)
            self.identifier(target.producer.namespace, "in_namespace", relation)
            self.emit(".", "syntax", "in_qualifier", relation)
            self.identifier(target.producer.name, "in_relation", relation)
        elif inline_body(target.producer):
            # A capturing let is the derived relation of its own read.
            producer = target.producer
            self.identifier(column[0], "in_column", producer.columns[0].column.terminal)
            self.emit(" FROM ", "syntax", "in_from", reference)
            self.emit("(", "syntax", "inline_open", producer.block.ref)
            _unit_select(self, producer)
            self.emit(")", "syntax", "inline_close", producer.block.ref)
        else:
            producer = target.producer
            self.identifier(column[0], "in_column", producer.cte_columns[0].binding)
            self.emit(" FROM ", "syntax", "in_from", reference)
            self.identifier(producer.symbol.name, "in_reference", producer.block.ref)
        self.emit(" AS ", "syntax", "in_alias", target.use.ref)
        self.identifier(target.symbol.name, "in_scope", target.use.ref)
        self.emit("))", "syntax", "in_close", reference)
        self.enclose("relation_membership", reference, start)

    def scalar(self, value, alias):
        """One admitted tree; a reference with its own scope reads that relation."""
        start = self.offset
        if type(value) is rows.SQLBlockRead:
            self.block_read(value, alias)
            return
        if type(value) is rows.SQLCapturedReference:
            reference = value.original.ref
            self.identifier(value.scope.name, "capture_scope", value.capture.ref)
            self.emit(".", "syntax", "capture_qualifier", reference)
            self.identifier(value.column.name, "capture_column", value.column.terminal)
            self.enclose("capture", reference, start)
            return
        if type(value) is rows.SQLStageReference:
            reference = value.original.ref
            scope = alias if value.scope is None else value.scope.name
            self.identifier(scope, "value_scope", value.port)
            self.emit(".", "syntax", "value_qualifier", reference)
            self.identifier(value.column.name, "value_column", value.column.terminal)
            self.enclose("reference", reference, start)
            return
        if type(value) is rows.SQLParameterRead:
            self.parameter_read(value)
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
        if value.kind == "not":
            self.emit("(NOT ", "syntax", "not_open", reference)
            self.scalar(value.operands[0], alias)
            self.emit(")", "syntax", "not_close", reference)
            self.enclose("not", reference, start)
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
        if value.kind == "between":
            self.emit("(", "syntax", "between_open", reference)
            self.scalar(value.operands[0], alias)
            self.emit(" BETWEEN ", "syntax", "between_operator", reference)
            self.scalar(value.operands[1], alias)
            self.emit(" AND ", "syntax", "between_separator", reference)
            self.scalar(value.operands[2], alias)
            self.emit(")", "syntax", "between_close", reference)
            self.enclose("between", reference, start)
            return
        if value.kind == "scalar_call":
            name = value.original.callee_symbol.name
            spelling = {
                "postgres": {
                    "lower": "lower",
                    "upper": "upper",
                    "trim": "trim",
                    "len": "length",
                    "replace": "replace",
                    "abs": "abs",
                    "nullif": "NULLIF",
                    "coalesce": "COALESCE",
                },
                "mysql": {
                    "lower": "LOWER",
                    "upper": "UPPER",
                    "trim": "TRIM",
                    "len": "CHAR_LENGTH",
                    "replace": "REPLACE",
                    "abs": "ABS",
                    "nullif": "NULLIF",
                    "coalesce": "COALESCE",
                },
            }[self.request.family].get(name)
            if name == "substr":
                self.emit(
                    "substring(" if self.request.family == "postgres" else "SUBSTRING(",
                    "syntax",
                    "scalar_call_open",
                    reference,
                )
                self.scalar(value.operands[0], alias)
                self.emit(
                    " FROM " if self.request.family == "postgres" else ", ",
                    "syntax",
                    "scalar_call_separator",
                    reference,
                )
                if self.request.family == "postgres":
                    self.emit(
                        "CAST(",
                        "syntax",
                        "scalar_call_index_cast_open",
                        reference,
                    )
                self.scalar(value.operands[1], alias)
                if self.request.family == "postgres":
                    self.emit(
                        " AS pg_catalog.int4)",
                        "syntax",
                        "scalar_call_index_cast_close",
                        reference,
                    )
                self.emit(
                    " FOR " if self.request.family == "postgres" else ", ",
                    "syntax",
                    "scalar_call_separator",
                    reference,
                )
                if self.request.family == "postgres":
                    self.emit(
                        "CAST(",
                        "syntax",
                        "scalar_call_index_cast_open",
                        reference,
                    )
                self.scalar(value.operands[2], alias)
                if self.request.family == "postgres":
                    self.emit(
                        " AS pg_catalog.int4)",
                        "syntax",
                        "scalar_call_index_cast_close",
                        reference,
                    )
                self.emit(")", "syntax", "scalar_call_close", reference)
                self.enclose("scalar_call", reference, start)
                return
            if name == "len":
                assert spelling is not None
                self.emit(
                    "CAST(" + spelling + "(",
                    "syntax",
                    "scalar_call_open",
                    reference,
                )
                self.scalar(value.operands[0], alias)
                self.emit(
                    ") AS "
                    + (
                        "pg_catalog.int8"
                        if self.request.family == "postgres"
                        else "SIGNED"
                    )
                    + ")",
                    "syntax",
                    "scalar_call_close",
                    reference,
                )
                self.enclose("scalar_call", reference, start)
                return
            if name == "date_of":
                if self.request.family == "postgres":
                    self.emit("CAST(", "syntax", "scalar_call_open", reference)
                    self.scalar(value.operands[0], alias)
                    self.emit(" AS date)", "syntax", "scalar_call_close", reference)
                else:
                    self.emit("DATE(", "syntax", "scalar_call_open", reference)
                    self.scalar(value.operands[0], alias)
                    self.emit(")", "syntax", "scalar_call_close", reference)
                self.enclose("scalar_call", reference, start)
                return
            if name in {"contains", "starts_with", "ends_with"}:
                if len(value.operands) != 2:
                    raise ValueError("unrenderable scalar call")
                if name == "contains":
                    self.emit(
                        "(strpos(" if self.request.family == "postgres" else "(INSTR(",
                        "syntax",
                        "scalar_call_open",
                        reference,
                    )
                    self.scalar(value.operands[0], alias)
                    self.emit(
                        ", ",
                        "syntax",
                        "scalar_call_separator",
                        reference,
                    )
                    self.scalar(value.operands[1], alias)
                    self.emit(") > 0)", "syntax", "scalar_call_close", reference)
                else:
                    function = {"starts_with": "left", "ends_with": "right"}[name]
                    if self.request.family == "mysql":
                        function = function.upper()
                    self.emit(
                        "(" + function + "(", "syntax", "scalar_call_open", reference
                    )
                    self.scalar(value.operands[0], alias)
                    self.emit(", ", "syntax", "scalar_call_separator", reference)
                    self.emit(
                        "length("
                        if self.request.family == "postgres"
                        else "CHAR_LENGTH(",
                        "syntax",
                        "scalar_call_nested_open",
                        reference,
                    )
                    self.scalar(value.operands[1], alias)
                    self.emit(")", "syntax", "scalar_call_nested_close", reference)
                    self.emit(" ) = ", "syntax", "scalar_call_operator", reference)
                    self.scalar(value.operands[1], alias)
                    self.emit(")", "syntax", "scalar_call_close", reference)
                self.enclose("scalar_call", reference, start)
                return
            if name in {"sign", "year", "month", "day", "hour", "minute"}:
                function = name.upper() if self.request.family == "mysql" else name
                if self.request.family == "postgres" and name in {
                    "year",
                    "month",
                    "day",
                    "hour",
                    "minute",
                }:
                    self.emit(
                        "CAST(EXTRACT(" + name.upper() + " FROM ",
                        "syntax",
                        "scalar_call_open",
                        reference,
                    )
                    self.scalar(value.operands[0], alias)
                    self.emit(
                        ") AS pg_catalog.int8)",
                        "syntax",
                        "scalar_call_close",
                        reference,
                    )
                else:
                    cast_type = (
                        "pg_catalog.int8"
                        if self.request.family == "postgres"
                        else "SIGNED"
                    )
                    self.emit(
                        "CAST(" + function + "(",
                        "syntax",
                        "scalar_call_open",
                        reference,
                    )
                    self.scalar(value.operands[0], alias)
                    self.emit(
                        ") AS " + cast_type + ")",
                        "syntax",
                        "scalar_call_close",
                        reference,
                    )
                self.enclose("scalar_call", reference, start)
                return
            if spelling is None or not value.operands:
                raise ValueError("unrenderable scalar call")
            self.emit(spelling + "(", "syntax", "scalar_call_open", reference)
            for position, operand in enumerate(value.operands):
                if position:
                    self.emit(", ", "syntax", "scalar_call_separator", reference)
                self.scalar(operand, alias)
            self.emit(")", "syntax", "scalar_call_close", reference)
            self.enclose("scalar_call", reference, start)
            return
        if value.kind == "conditional":
            self.emit("(CASE WHEN ", "syntax", "conditional_open", reference)
            self.scalar(value.operands[1], alias)
            self.emit(" THEN ", "syntax", "conditional_then", reference)
            self.scalar(value.operands[0], alias)
            self.emit(" ELSE ", "syntax", "conditional_else", reference)
            self.scalar(value.operands[2], alias)
            self.emit(" END)", "syntax", "conditional_close", reference)
            self.enclose("conditional", reference, start)
            return
        if value.kind == "membership":
            if len(value.operands) == 1:
                self.emit(
                    "TRUE" if value.original.expression.negated else "FALSE",
                    "syntax",
                    "membership_constant",
                    reference,
                )
            else:
                self.emit("(", "syntax", "membership_open", reference)
                self.scalar(value.operands[0], alias)
                self.emit(
                    " NOT IN (" if value.original.expression.negated else " IN (",
                    "syntax",
                    "membership_operator",
                    reference,
                )
                for position, operand in enumerate(value.operands[1:]):
                    if position:
                        self.emit(", ", "syntax", "membership_separator", reference)
                    self.scalar(operand, alias)
                self.emit("))", "syntax", "membership_close", reference)
            self.enclose("membership", reference, start)
            return
        if value.kind == "cast":
            physical = (
                "pg_catalog.float8" if self.request.family == "postgres" else "DOUBLE"
            )
            self.emit("CAST(", "syntax", "cast_open", reference)
            self.scalar(value.operands[0], alias)
            self.emit(" AS " + physical + ")", "syntax", "cast_close", reference)
            self.enclose("cast", reference, start)
            return
        if value.kind == "comparison" and value.original.expression.operator in {
            "like",
            "not like",
        }:
            self.emit("(", "syntax", "comparison_open", reference)
            self.scalar(value.operands[0], alias)
            self.emit(operator_token(value), "syntax", "comparison_operator", reference)
            self.scalar(value.operands[1], alias)
            self.emit(" ESCAPE '!'", "syntax", "comparison_escape", reference)
            self.emit(")", "syntax", "comparison_close", reference)
            self.enclose("comparison", reference, start)
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


def _aggregate_value(w: _Writer, column, alias) -> None:
    """One aggregate occurrence: its own spelling over its own exact argument."""
    reference = column.aggregate.ref
    start = w.offset
    w.emit(column.spelling + "(", "syntax", "aggregate_open", reference)
    if column.argument is None:
        # count() consumes the complete input BAG, so COUNT(*) is the whole row
        # count, never SELECT * and never a column count.
        w.emit("*", "syntax", "aggregate_row_count", reference)
    else:
        if column.distinct:
            w.emit("DISTINCT ", "syntax", "aggregate_distinct", reference)
        if column.argument_cast is not None:
            w.emit("CAST(", "syntax", "aggregate_argument_cast_open", reference)
        w.scalar(column.argument, alias)
        if column.argument_cast is not None:
            w.emit(
                " AS " + column.argument_cast + ")",
                "syntax",
                "aggregate_argument_cast_close",
                reference,
            )
    w.emit(")", "syntax", "aggregate_close", reference)
    w.enclose("aggregate", reference, start)


def _window_specification(w: _Writer, specification, reference, alias) -> None:
    """The exact OVER body, shared by an inline use and a WINDOW definition."""

    if specification.partitions:
        w.emit("PARTITION BY ", "syntax", "window_partition", reference)
        for position, (_binding, read) in enumerate(specification.partitions):
            if position:
                w.emit(", ", "syntax", "window_partition_separator", reference)
            w.identifier(alias, "window_partition_scope", read.terminal)
            w.emit(".", "syntax", "window_partition_qualifier", reference)
            w.identifier(read.name, "window_partition_column", read.terminal)
    if specification.orders:
        if specification.partitions:
            w.emit(" ", "syntax", "window_spec_separator", reference)
        w.emit("ORDER BY ", "syntax", "window_order", reference)
        for item in specification.orders:
            if item.position:
                w.emit(", ", "syntax", "window_order_separator", reference)
            w.identifier(alias, "window_order_scope", item.read.terminal)
            w.emit(".", "syntax", "window_order_qualifier", reference)
            w.identifier(item.read.name, "window_order_column", item.read.terminal)
            w.emit(
                " ASC" if item.direction == "asc" else " DESC",
                "syntax",
                "window_order_direction",
                reference,
            )
    frame = specification.frame
    if frame is not None:
        if specification.partitions or specification.orders:
            w.emit(" ", "syntax", "window_frame_separator", reference)
        w.emit(
            windowing.UNIT_SPELLING[frame.unit] + " BETWEEN ",
            "syntax",
            "window_frame_unit",
            reference,
        )
        w.emit(frame.start[1], "syntax", "window_frame_start", reference)
        w.emit(" AND ", "syntax", "window_frame_and", reference)
        w.emit(frame.end[1], "syntax", "window_frame_end", reference)
        spelling = windowing.EXCLUSION_SPELLING.get(frame.exclusion)
        if spelling is not None:
            w.emit(" " + spelling, "syntax", "window_frame_exclusion", reference)


def _window_clause(w: _Writer, stage, alias) -> None:
    """One generated WINDOW clause listing every named definition in order."""

    if stage is None or not stage.definitions:
        return
    w.emit(" WINDOW ", "syntax", "window_clause", stage.ref)
    for definition in stage.definitions:
        if definition.index:
            w.emit(", ", "syntax", "window_clause_separator", stage.ref)
        reference = definition.symbol.binding
        w.identifier(definition.symbol.name, "window_definition", reference)
        w.emit(" AS ", "syntax", "window_definition_as", reference)
        start = w.offset
        w.emit("(", "syntax", "window_spec_open", reference)
        _window_specification(w, definition.specification, reference, alias)
        w.emit(")", "syntax", "window_spec_close", reference)
        w.enclose("window_specification", reference, start)


def _window_value(w: _Writer, column, alias) -> None:
    """One window occurrence: its spelling, then its exact OVER specification."""

    reference = column.window.ref
    start = w.offset
    w.emit(
        windowing.SPELLING[column.function] + "(", "syntax", "window_open", reference
    )
    for argument in column.arguments:
        if argument.position:
            w.emit(", ", "syntax", "window_argument_separator", reference)
        if argument.read is not None:
            w.identifier(alias, "window_argument_scope", argument.read.terminal)
            w.emit(".", "syntax", "window_argument_qualifier", reference)
            w.identifier(
                argument.read.name, "window_argument_column", argument.read.terminal
            )
        elif argument.parameter is None:
            assert argument.literal is not None
            w.emit(argument.literal, "literal", "window_argument_literal", reference)
        elif argument.role not in windowing.COUNT_ROLES:
            w.parameter_read(argument.parameter)
        elif w.request.family == "postgres":
            # PostgreSQL's structural count is int4; the int8 anchor is cast.
            w.emit("CAST(", "syntax", "window_count_open", reference)
            w.parameter_read(argument.parameter)
            w.emit(" AS pg_catalog.int4)", "syntax", "window_count_close", reference)
        else:
            # MySQL refuses CAST(? AS SIGNED) as a LAG/LEAD offset or NTILE
            # count; every MySQL count is a bare placeholder.
            w.emit("?", "parameter", "Int", argument.parameter.original.ref)
    w.emit(")", "syntax", "window_close", reference)
    w.emit(" OVER ", "syntax", "window_over", reference)
    specification = column.specification
    if specification.symbol is not None:
        w.identifier(specification.symbol.name, "window_reference", reference)
        w.enclose("window", reference, start)
        return
    inner = w.offset
    w.emit("(", "syntax", "window_spec_open", reference)
    _window_specification(w, specification, reference, alias)
    w.emit(")", "syntax", "window_spec_close", reference)
    w.enclose("window_specification", reference, inner)
    w.enclose("window", reference, start)


def _row_select(w: _Writer, body) -> None:
    """One stage body: its columns, its scan, its grouping and its filter."""
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
        elif type(column) is AggregateKeyColumn:
            w.identifier(alias, "group_key_scope", column.input_port)
            w.emit(".", "syntax", "group_key_qualifier", column.export.ref)
            w.identifier(column.read.name, "group_key_column", column.read.terminal)
        elif type(column) is AggregateProjectionColumn:
            w.identifier(alias, "result_scope", column.input_port)
            w.emit(".", "syntax", "result_qualifier", column.export.ref)
            w.identifier(column.read.name, "result_column", column.read.terminal)
        elif type(column) is AggregateValueColumn:
            _aggregate_value(w, column, alias)
        elif type(column) is windowing.WindowColumn:
            _window_value(w, column, alias)
        elif type(column) is windowing.WindowProjectionColumn:
            w.identifier(alias, "window_result_scope", column.input_port)
            w.emit(".", "syntax", "window_result_qualifier", column.export.ref)
            w.identifier(column.read.name, "window_result_column", column.read.terminal)
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
        if inline_body(scan.body):
            w.emit("(", "syntax", "inline_open", reference)
            _row_select(w, scan.body)
            w.emit(")", "syntax", "inline_close", reference)
        else:
            w.identifier(scan.body.symbol.name, "stage_reference", reference)
        w.emit(" AS ", "syntax", "alias", scan.block.ref)
        w.identifier(alias, "stage_scope", scan.block.ref)
    stage = body.aggregation
    if stage is not None and stage.keys:
        # GROUP BY binds the actual input expressions, never an output alias or
        # an ordinal: a constant-valued key groups by its established value.
        w.emit(" GROUP BY ", "syntax", "group_by", stage.aggregation.ref)
        for position, column in enumerate(stage.keys):
            if position:
                w.emit(", ", "syntax", "group_separator", column.key.ref)
            start = w.offset
            w.identifier(alias, "grouping_scope", column.input_port)
            w.emit(".", "syntax", "grouping_qualifier", column.key.ref)
            w.identifier(column.read.name, "grouping_column", column.read.terminal)
            w.enclose("grouping", column.key.ref, start)
    _window_clause(w, body.window, alias)
    if body.predicate is not None:
        satisfying = body.block.kind.value == "satisfying"
        w.emit(
            " WHERE ",
            "syntax",
            "satisfying" if satisfying else "where",
            body.predicate.original.ref,
        )
        w.scalar(body.predicate.value, alias)


def _result_select(w: _Writer, body) -> None:
    """One result body: DISTINCT, the carried visible tuple, ORDER BY and LIMIT.

    The scan is the definition's own closed projection stage. Every ORDER key is
    an exact carried column of that stage read through the stage alias, so a
    constant key is a value column and never an ordinal, and no NULLS spelling is
    generated because the retained policy requires no posture.
    """
    scan = body.scan
    alias = scan.symbol.name
    reference = body.block.ref
    w.emit("SELECT ", "syntax", "select", reference)
    if body.distinct is not None:
        w.emit("DISTINCT ", "syntax", "distinct", body.distinct.distinct.ref)
    for position, column in enumerate(body.columns):
        if position:
            w.emit(", ", "syntax", "separator", column.export.ref)
        w.identifier(alias, "result_carry_scope", column.projection_port.ref)
        w.emit(".", "syntax", "result_carry_qualifier", column.export.ref)
        w.identifier(column.read.name, "result_carry_column", column.read.terminal)
        w.emit(" AS ", "syntax", "alias", column.export.ref)
        w.identifier(column.label, "label", column.export.ref)
    reference = scan.body.block.ref
    w.emit(" FROM ", "syntax", "from", reference)
    if inline_body(scan.body):
        # A capturing let's projection is the derived relation it orders.
        w.emit("(", "syntax", "inline_open", reference)
        _row_select(w, scan.body)
        w.emit(")", "syntax", "inline_close", reference)
    else:
        w.identifier(scan.body.symbol.name, "stage_reference", reference)
    w.emit(" AS ", "syntax", "alias", scan.boundary.ref)
    w.identifier(alias, "result_scope", scan.boundary.ref)
    order = body.order
    if order is not None:
        w.emit(" ORDER BY ", "syntax", "order_by", order.order.ref)
        for item in order.items:
            reference = item.item.ref
            if item.position:
                w.emit(", ", "syntax", "order_separator", reference)
            start = w.offset
            w.identifier(alias, "order_scope", item.port.ref)
            w.emit(".", "syntax", "order_qualifier", reference)
            w.identifier(item.read.name, "order_column", item.read.terminal)
            w.emit(
                " " + resulting.DIRECTIONS[item.direction],
                "syntax",
                "order_direction",
                reference,
            )
            w.enclose("order_item", reference, start)
    if body.limit is not None:
        reference = body.limit.limit.ref
        w.emit(" LIMIT ", "syntax", "limit", reference)
        w.emit(str(body.limit.value), "literal", "limit_value", reference)


def _set_operand_select(w: _Writer, unit, operand) -> None:
    """One operand: a wrapper SELECT over its producer's complete terminal.

    Every operand labels its positional columns with the SET-owned output labels,
    so the result set carries the SET's names on both targets.
    """
    reference = operand.operand.ref
    alias = operand.symbol.name
    w.emit("(", "syntax", "set_operand_open", reference)
    w.emit("SELECT ", "syntax", "select", reference)
    for position, column in enumerate(operand.columns):
        subject = operand.inputs[position].ref
        if position:
            w.emit(", ", "syntax", "separator", subject)
        w.identifier(alias, "set_input_scope", subject)
        w.emit(".", "syntax", "set_input_qualifier", subject)
        w.identifier(column.name, "set_input_column", column.terminal)
        w.emit(" AS ", "syntax", "alias", subject)
        w.identifier(
            unit.columns[position].label, "label", unit.columns[position].export.ref
        )
    w.emit(" FROM ", "syntax", "from", reference)
    producer = operand.producer
    if type(producer) is BoundSource:
        relation = operand.source.ref
        w.identifier(producer.namespace, "set_namespace", relation)
        w.emit(".", "syntax", "set_qualifier", relation)
        w.identifier(producer.name, "set_relation", relation)
    else:
        w.identifier(producer.symbol.name, "set_reference", producer.block.ref)
    w.emit(" AS ", "syntax", "set_alias", reference)
    w.identifier(alias, "set_scope", reference)
    w.emit(")", "syntax", "set_operand_close", reference)


def _set_select(w: _Writer, unit) -> None:
    """One SET unit: explicit left-fold grouping of operand SELECTs.

    `(o0) OP (o1)` for two operands and `((o0) OP (o1)) OP (o2)` beyond, so the
    authored source-order left fold is spelled rather than left to precedence.
    """
    reference = unit.body.ref
    operator = " " + setting.operator_spelling(unit.kind, unit.quantifier) + " "
    count = len(unit.operands)
    for _ in range(count - 2):
        w.emit("(", "syntax", "set_fold_open", reference)
    _set_operand_select(w, unit, unit.operands[0])
    for position, operand in enumerate(unit.operands[1:], start=1):
        w.emit(operator, "syntax", "set_operator", reference)
        _set_operand_select(w, unit, operand)
        if position < count - 1:
            w.emit(")", "syntax", "set_fold_close", reference)


def _values_select(w: _Writer, unit) -> None:
    """One VALUES unit: typed rows, or a typed empty SELECT for zero rows.

    A CTE body is the bare ``VALUES`` list, its aliases written by the CTE column
    list; the selected statement labels the derived table's columns instead.
    """
    reference = unit.body.ref
    family = w.request.family
    if not unit.rows or unit.final:
        w.emit("SELECT ", "syntax", "select", reference)
        for position, column in enumerate(unit.columns):
            subject = column.source.ref
            if position:
                w.emit(", ", "syntax", "separator", subject)
            if unit.rows:
                w.identifier(unit.scope.name, "values_scope", subject)
                w.emit(".", "syntax", "values_qualifier", subject)
                w.identifier(f"c{position}", "values_column", subject)
            else:
                w.emit("CAST(", "syntax", "anchor_open", subject)
                w.emit("NULL", "literal", column.realization.tag, subject)
                w.emit(
                    parameters.anchor_suffix(column.physical),
                    "syntax",
                    "anchor_close",
                    subject,
                )
            w.emit(" AS ", "syntax", "alias", subject)
            w.identifier(column.label, "label", column.export.ref)
        if not unit.rows:
            w.emit(" WHERE FALSE", "syntax", "values_empty", reference)
            return
        w.emit(" FROM (", "syntax", "values_open", reference)
    w.emit("VALUES ", "syntax", "values", reference)
    for index, row in enumerate(unit.rows):
        if index:
            w.emit(", ", "syntax", "values_row_separator", reference)
        w.emit(
            "(" if family == "postgres" else "ROW(",
            "syntax",
            "values_row_open",
            reference,
        )
        for position, (column, value) in enumerate(zip(unit.columns, row, strict=True)):
            subject = column.source.ref
            if position:
                w.emit(", ", "syntax", "separator", subject)
            w.emit("CAST(", "syntax", "anchor_open", subject)
            w.emit(
                valuing.cell_token(column.realization.tag, value, family),
                "literal",
                column.realization.tag,
                subject,
            )
            w.emit(
                parameters.anchor_suffix(column.physical),
                "syntax",
                "anchor_close",
                subject,
            )
        w.emit(")", "syntax", "values_row_close", reference)
    if unit.final:
        w.emit(") AS ", "syntax", "values_close", reference)
        w.identifier(unit.scope.name, "values_alias", reference)
        w.emit(" (", "syntax", "values_columns_open", reference)
        for position, column in enumerate(unit.columns):
            if position:
                w.emit(", ", "syntax", "separator", column.source.ref)
            w.identifier(f"c{position}", "values_column_alias", column.source.ref)
        w.emit(")", "syntax", "values_columns_close", reference)


def _unit_select(w: _Writer, unit) -> None:
    if type(unit) is JoinBody:
        _join_select(w, unit)
    elif type(unit) is resulting.RowResultBody:
        _result_select(w, unit)
    elif type(unit) is setting.SetBody:
        _set_select(w, unit)
    elif type(unit) is valuing.ValuesBody:
        _values_select(w, unit)
    else:
        _row_select(w, unit)


def render_row_sql(query: SQLRowQuery | CompiledSQLQuery) -> RenderedSQL:
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
            _unit_select(w, body)
            w.emit(")", "syntax", "cte_body_close", reference)
        w.emit(" ", "syntax", "with_body", final_body.block.ref)
    _unit_select(w, final_body)
    return w.rendered(query)


def _join_relation(w: _Writer, item) -> None:
    """One JOIN input relation reference, then its generated capture-free alias;
    a capturing let is its own LATERAL derived relation."""
    reference = item.original.ref
    producer = item.producer
    if type(producer) is BoundSource:
        relation = item.source
        w.identifier(producer.namespace, "join_namespace", relation)
        w.emit(".", "syntax", "join_qualifier", relation)
        w.identifier(producer.name, "join_relation", relation)
    elif inline_body(producer):
        w.emit("LATERAL (", "syntax", "lateral_open", reference)
        _unit_select(w, producer)
        w.emit(")", "syntax", "lateral_close", reference)
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
            _unit_select(w, unit)
            w.emit(")", "syntax", "cte_body_close", reference)
        w.emit(" ", "syntax", "with_body", final_body.block.ref)
    _unit_select(w, final_body)
    return w.rendered(query)
