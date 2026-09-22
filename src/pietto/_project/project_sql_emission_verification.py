"""Independent correspondence checks; no construction, rendering or type inference."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import math
import re
from typing import Any

from pietto._project import project_sql_plan as plans
from pietto._project.project_query_block_ir import ProjectIRReusedEffectiveOutput
from pietto._project import project_sql_plan_expressions as row
from pietto._project.project_sql_plan_verification import verify_project_sql_plan
from pietto._project.project_sql_plan_requirements import (
    verify_project_sql_requirement_report,
)
from pietto._project.project_sql_plan_source_maps import verify_project_sql_source_map
from pietto._project.project_sql_plan_target_assessment import (
    verify_project_sql_target_assessment,
)
from pietto._project.project_sql_emission_contract import BoundSource, PreparedEmission
from pietto._project.project_sql_emission_scopes import verify_emission_layout
from pietto._project.project_sql_emission_ast import (
    RowBody,
    RowScan,
    RowNamedUse,
    RowStageUse,
    RowJoinUse,
    RowCarryColumn,
    RowValueColumn,
    SQLRowQuery,
    SQLJoinQuery,
    node_premises,
    row_parameter_leaves,
    admitted_row_shape,
    definition_blocks,
    SQLSelect,
    SQLScan,
    SQLColumn,
    SQLLiteralColumn,
    SQLSymbol,
    SQLCTE,
    SQLNamedUse,
    OriginalRequirement,
    GeneratedRequirement,
    projection_chain_shape,
    identifier_valid,
    applicable_premises,
    resource_limits,
    emission_blockers,
)
from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_rows as rows
from pietto._project import project_sql_emission_joins as joining
from pietto._project import project_sql_emission_aggregation as grouping
from pietto._project import project_sql_emission_windows as windowing
from pietto._project import project_sql_emission_results as resulting
from pietto._project import project_sql_emission_sets as setting
from pietto._project import project_sql_plan_windows as plan_windows
from pietto._project import project_sql_plan_aggregation as plan_aggregation
from pietto._project import project_sql_emission_ast as ast
from pietto._project.project_sql_plan_joins import ProjectSQLJoinPortKind
from pietto.ast_nodes import AuthoredJoinKind
from pietto._project.project_sql_emission_rendering import (
    OPERATORS,
    RenderedSQL,
    RenderingEvent,
    operator_token,
)

__all__: tuple[str, ...] = ()


def _same(actual, expected):
    return (
        type(actual) is tuple
        and len(actual) == len(expected)
        and all(a is b for a, b in zip(actual, expected, strict=True))
    )


def prepared_current(request):
    if type(request) is not PreparedEmission:
        return False
    names = (
        "verification",
        "accepted_bytes",
        "normalized_bytes",
        "family",
        "release",
        "sources",
        "premises",
        "target_request",
        "report",
        "source_map",
        "assessment",
        "layout",
        "input_blockers",
    )
    if not _same(tuple(getattr(request, n) for n in names), request._accepted):
        return False
    checked = request.verification
    if (
        type(checked.plan) is not plans.ProjectSQLPlan
        or not verify_project_sql_plan(
            checked.plan,
            checked.completed,
            checked.analysis_bundle,
            checked.selected_owner,
            literal_policy=checked.literal_policy,
            envelope=checked.envelope,
        ).verified
    ):
        return False
    if (
        not verify_project_sql_requirement_report(
            request.report.report, checked
        ).verified
        or request.report.source_verification is not checked
    ):
        return False
    if (
        not verify_project_sql_source_map(
            request.source_map.source_map, checked
        ).verified
        or request.source_map.source_verification is not checked
    ):
        return False
    if (
        not verify_project_sql_target_assessment(
            request.assessment.assessment, checked, request.target_request
        ).verified
        or request.assessment.source_verification is not checked
    ):
        return False
    if not verify_emission_layout(request.layout, checked):
        return False
    # Binding was done once. Check retained occurrence/ordinal correspondence,
    # without running a selector resolver or the construction-time Decimal rule.
    document = json.loads(request.normalized_bytes)
    if len(document["sources"]) != len(request.sources):
        return False
    for source, description in zip(request.sources, document["sources"], strict=True):
        if (
            source.selector
            != json.dumps(
                description["selector"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
            or (source.namespace, source.name)
            != (description["relation"]["namespace"], description["relation"]["name"])
            or len(source.fields) != len(description["fields"])
        ):
            return False
        entries = checked.analysis_bundle.root.find_owner(source.owner)
        if (
            len(entries) != 1
            or type(entries[0]) is not ProjectIRReusedEffectiveOutput
            or not any(
                source.owner is owner for owner in checked.analysis_bundle.root.owners
            )
        ):
            return False
        fields = entries[0].active_properties.relational.fields
        for field, field_description in zip(
            source.fields, description["fields"], strict=True
        ):
            if (field.ordinal, field.name, field.column) != (
                field_description["ordinal"],
                field_description["name"],
                field_description["column"],
            ) or json.loads(field.representation) != field_description[
                "representation"
            ]:
                return False
            if (
                type(field.ordinal) is not int
                or not 0 <= field.ordinal < len(fields)
                or field.field is not fields[field.ordinal]
                or field.name != field.field.evidence.name
            ):
                return False
            if field.resolution is not None:
                types = checked.completed.semantic_result.module_type_source_resolutions
                if types is None or not any(
                    field.resolution is value
                    for env in types.environments
                    for value in env.type_resolutions
                ):
                    return False
            if field.decimal is not None:
                # This is correspondence to the retained checked argument values,
                # not creation/validation of a Pietto Decimal semantic fact.
                expression = field.decimal_expression
                if (
                    expression is None
                    or len(expression.arguments) != 2
                    or tuple(
                        getattr(a.value, "value", None) for a in expression.arguments
                    )
                    != (field.decimal.precision, field.decimal.scale)
                ):
                    return False
    return True


def verify_sql_ast(request, ast):
    try:
        if (
            not prepared_current(request)
            or type(ast) is not SQLSelect
            or ast.request is not request
        ):
            return False
        plan = request.plan
        if not projection_chain_shape(plan) or emission_blockers(request):
            return False
        sources = {s.ref: s for s in plan.sources}
        definitions = tuple(
            d for d in request.layout.definitions if d.original.ref not in sources
        )
        if (
            type(ast.ctes) is not tuple
            or len(ast.ctes) != len(definitions) - 1
            or ast.definition is not definitions[-1]
            or definitions[-1].original.entry.owner is not plan.scope.selected_owner
        ):
            return False
        available = {}
        provenance = {}
        expressions_seen = []
        symbols = []
        nodes = []
        bodies = (*[cte.body for cte in ast.ctes], ast)
        for index, (definition, body) in enumerate(
            zip(definitions, bodies, strict=True)
        ):
            final = body is ast
            if (
                type(body) is not SQLSelect
                or body.request is not request
                or body.definition is not definition
                or (not final and body.ctes != ())
            ):
                return False
            matches = tuple(u for u in request.layout.uses if u.consumer is definition)
            if len(matches) != 1:
                return False
            binding = matches[0]
            use = binding.original
            scan = body.scan
            if use.producer in sources:
                if (
                    type(scan) is not SQLScan
                    or scan.source is not sources[use.producer]
                    or not any(scan.realization is s for s in request.sources)
                    or scan.realization.owner is not scan.source.source.owner
                ):
                    return False
            elif type(scan) is not SQLNamedUse or scan.cte is not available.get(
                use.producer
            ):
                return False
            if (
                scan.use is not use
                or scan.binding is not binding
                or type(scan.symbol) is not SQLSymbol
                or type(scan.symbol.position) is not int
                or scan.symbol.position != 0
                or scan.symbol.binding is not use.ref
                or scan.symbol.name != f"s{use.ref.position}"
            ):
                return False
            symbols.append(scan.symbol)
            nodes.extend((body, scan))
            blocks = tuple(
                b for b in plan.blocks if b.definition is definition.original.ref
            )
            if len(blocks) != 1:
                return False
            projections = tuple(p for p in plan.projections if p.block is blocks[0].ref)
            exports = definition.original.exports
            if (
                type(body.columns) is not tuple
                or len(body.columns) != len(exports)
                or len(projections) != len(exports)
            ):
                return False
            for position, (column, projection, export) in enumerate(
                zip(body.columns, projections, exports, strict=True)
            ):
                if (
                    type(column) not in {SQLColumn, SQLLiteralColumn}
                    or type(column.ordinal) is not int
                    or column.ordinal != position
                    or column.scan is not scan
                    or column.projection is not projection
                    or column.export is not export
                    or column.label
                    != (export.identity.name if final else f"c{position}")
                ):
                    return False
                expression = plan.expressions[projection.expression.position]
                if (
                    expression.ref is not projection.expression
                    or projection.export is not export.ref
                    or projection.input_use is not use.ref
                ):
                    return False
                if type(column) is SQLLiteralColumn and column.value is not None:
                    origin = column.origin
                    if (
                        type(origin) is not parameters.LiteralOrigin
                        or origin.value is not column.value
                        or origin.export is not export
                        or origin.terminal is not definition.terminals[position]
                        or projection.source_port is not None
                        or projection.input_port is not None
                        or column.producer is not None
                        or column.symbol.binding is not export.ref
                        or column.symbol.name != column.label
                        or not _verify_value(
                            request, column.value, expression, expressions_seen, nodes
                        )
                    ):
                        return False
                    if not _literal_ports(origin, (export,)):
                        return False
                    if (
                        type(column.symbol) is not SQLSymbol
                        or type(column.symbol.position) is not int
                        or column.symbol.position != position + 1
                        or not identifier_valid(
                            column.label, request.family, label=final
                        )
                    ):
                        return False
                    symbols.append(column.symbol)
                    nodes.extend((column, origin))
                    provenance[export.ref] = origin
                    continue
                pairs = tuple(
                    (i, b)
                    for i, b in enumerate(binding.bindings)
                    if b.input_port.ref is projection.input_port
                )
                if len(pairs) != 1:
                    return False
                input_position, link = pairs[0]
                if (
                    column.producer is not link
                    or (
                        type(column) is SQLColumn
                        and column.input_port is not link.input_port
                    )
                    or projection.source_port is not link.canonical.ref
                    or projection.export is not export.ref
                    or projection.input_use is not use.ref
                ):
                    return False
                if type(expression) is not row.ProjectSQLReference:
                    return False
                expressions_seen.append(expression)
                if type(column) is SQLLiteralColumn:
                    if (
                        type(scan) is not SQLNamedUse
                        or column.value is not None
                        or column.origin is not provenance.get(link.canonical.ref)
                        or not _literal_ports(
                            column.origin, (link.canonical, link.input_port, export)
                        )
                    ):
                        return False
                    name = scan.cte.columns[input_position].name
                    symbol = column.symbol
                    if (
                        type(symbol) is not SQLSymbol
                        or type(symbol.position) is not int
                        or symbol.position != position + 1
                        or symbol.binding is not link.input_port.ref
                        or symbol.name != name
                        or not identifier_valid(name, request.family)
                        or not identifier_valid(
                            column.label, request.family, label=final
                        )
                    ):
                        return False
                    symbols.append(symbol)
                    nodes.append(column)
                    provenance[export.ref] = column.origin
                    continue
                assert isinstance(column, SQLColumn)
                if type(scan) is SQLScan:
                    physical = link.canonical
                    fields = tuple(
                        f for f in scan.realization.fields if f.field is physical.field
                    )
                    if len(fields) != 1 or not any(
                        physical is p for p in plan.source_ports
                    ):
                        return False
                    field, origin = fields[0], scan
                    name = field.column
                else:
                    if type(scan) is not SQLNamedUse:
                        return False
                    physical, field, origin = provenance[link.canonical.ref]
                    name = scan.cte.columns[input_position].name
                    if (
                        scan.cte.columns[input_position].binding
                        is not link.terminal.ref
                    ):
                        return False
                if (
                    column.source_port is not physical
                    or column.source_field is not field
                    or column.origin is not origin
                ):
                    return False
                for port in (link.canonical, link.input_port, export):
                    logical, original_type = (
                        port.field.evidence.resolved_type,
                        field.field.evidence.resolved_type,
                    )
                    if (
                        logical.kind is not original_type.kind
                        or logical.name != original_type.name
                        or port.field.effective_nullability
                        is not field.field.effective_nullability
                    ):
                        return False
                expressions = tuple(
                    e for e in plan.expressions if e.ref is projection.expression
                )
                if (
                    len(expressions) != 1
                    or type(expressions[0]) is not row.ProjectSQLReference
                ):
                    return False
                symbol = column.symbol
                if (
                    type(symbol) is not SQLSymbol
                    or type(symbol.position) is not int
                    or symbol.position != position + 1
                    or symbol.binding is not link.input_port.ref
                    or symbol.name != name
                    or not identifier_valid(name, request.family)
                    or not identifier_valid(column.label, request.family, label=final)
                ):
                    return False
                symbols.append(symbol)
                nodes.append(column)
                provenance[export.ref] = (physical, field, origin)
            if not final:
                cte = ast.ctes[index]
                if (
                    type(cte) is not SQLCTE
                    or cte.definition is not definition
                    or type(cte.symbol) is not SQLSymbol
                    or type(cte.symbol.position) is not int
                    or cte.symbol.position != index
                    or cte.symbol.binding is not definition.original.ref
                    or cte.symbol.name != f"p{index}"
                    or type(cte.columns) is not tuple
                    or len(cte.columns) != len(exports)
                ):
                    return False
                for i, (symbol, terminal) in enumerate(
                    zip(cte.columns, definition.terminals, strict=True)
                ):
                    if (
                        type(symbol) is not SQLSymbol
                        or type(symbol.position) is not int
                        or symbol.position != i
                        or symbol.binding is not terminal.ref
                        or symbol.name != f"c{i}"
                    ):
                        return False
                symbols.extend((cte.symbol, *cte.columns))
                nodes.append(cte)
                available[definition.original.ref] = cte
        if (
            len({id(s) for s in symbols}) != len(symbols)
            or len(nodes) + len(symbols) > resource_limits(request)["nodes"]
        ):
            return False
        if (
            len(expressions_seen) != len(plan.expressions)
            or {id(e) for e in expressions_seen} != {id(e) for e in plan.expressions}
            or request.verification.envelope is not plan.fixed_envelope
            or request.verification.literal_policy is not plan.literal_policy
        ):
            return False
        return True
    except (AttributeError, TypeError, ValueError, IndexError, KeyError):
        return False


def _literal_ports(origin, ports):
    tag = parameters.tag_of(origin.value.original)
    return all(
        port.field.evidence.resolved_type.kind.value == "builtin"
        and port.field.evidence.resolved_type.name == tag
        and port.field.effective_nullability.value == "non_null"
        for port in ports
    )


def _verify_value(request, value, original, expressions_seen, nodes):
    """Walk the supplied SQL nodes against original refs; never build expectations."""
    plan = request.plan
    seen = set()
    while type(original) is row.ProjectSQLUnary:
        if (
            type(value) is not parameters.SQLUnary
            or id(value) in seen
            or value.original is not original
            or original.expression.operator not in {"+", "-"}
        ):
            return False
        seen.add(id(value))
        expressions_seen.append(original)
        nodes.append(value)
        original = plan.expressions[original.operand.position]
        if value.original.operand is not original.ref:
            return False
        value = value.operand
    tag = parameters.tag_of(original)
    if (
        type(value) is not parameters.SQLAnchor
        or value.original is not original
        or tag is None
        or value.physical_type != parameters.PHYSICAL[request.family].get(tag)
    ):
        return False
    nodes.append(value)
    leaf = value.operand
    if (
        type(leaf) not in {parameters.SQLLiteral, parameters.SQLParameter}
        or leaf.original is not original
        or not any(leaf.site is site for site in plan.literal_sites)
        or leaf.site.position.expression is not original.ref
        or leaf.site.position.literal is not original.expression
        or leaf.site.position.role.value
        not in {"select", "let", "where", "on", "satisfying", "qualify"}
    ):
        return False
    expressions_seen.append(original)
    nodes.append(leaf)
    if type(leaf) is parameters.SQLLiteral:
        # A literal stays a literal under PRESERVE, and under BIND_SAFE only in a
        # specialized position the extraction rule never admits as a slot. That
        # eligibility is re-derived from the retained role, never from the builder.
        return (
            type(original) is row.ProjectSQLLiteral
            and parameters.same_value(leaf.value, original.expression.value)
            and leaf.site.disposition.value == "preserved_with_reason"
            and (
                (
                    leaf.site.reason.value == "preserve_policy"
                    and request.verification.literal_policy.value == "preserve_literals"
                )
                or (
                    leaf.site.reason.value == "specialized_or_structural_context"
                    and request.verification.literal_policy.value
                    == "bind_safe_literals"
                    and leaf.site.position.role.value
                    not in {"select", "let", "where", "on", "unknown"}
                )
            )
        )
    assert isinstance(leaf, parameters.SQLParameter)
    return (
        type(original) is row.ProjectSQLBoundLiteral
        and type(leaf.use) is parameters.NativeUse
        and leaf.use.original is original
        and leaf.use.slot is original.use.slot
        and leaf.use.slot.site is leaf.site
        and leaf.use.physical_type == value.physical_type
        and any(leaf.fixed is fixed for fixed in plan.fixed_envelope.values)
        and leaf.fixed.slot is original.use.slot
        and leaf.fixed.tag is original.use.slot.tag
        and parameters.same_value(leaf.fixed.value, original.expression.value)
        and request.verification.literal_policy.value == "bind_safe_literals"
    )


def verify_sql_bytes(ast, rendered):
    try:
        if (
            type(rendered) is not RenderedSQL
            or rendered.ast is not ast
            or type(rendered.sql) is not bytes
            or type(rendered.events) is not tuple
        ):
            return False
        data = rendered.sql
        data.decode("utf-8")
        if len(data) > resource_limits(ast.request)["sql_bytes"]:
            return False
        events = iter(rendered.events)
        semantic_ranges = []
        offset = 0
        subjects = ast.request.source_map.source_map.indexes.subjects
        quote = '"' if ast.request.family == "postgres" else "`"

        def take(kind, role, subject, expected, *, identifier=False):
            nonlocal offset
            event = next(events)
            if (
                type(event) is not RenderingEvent
                or event.kind != kind
                or event.role != role
                or event.subject is not subject
                or type(event.start) is not int
                or type(event.end) is not int
                or event.start != offset
                or not event.start < event.end <= len(data)
            ):
                raise ValueError("token range or ownership")
            if not _same(event.origins, getattr(subjects.get(subject), "origins", ())):
                raise ValueError("source map correspondence")
            token = data[event.start : event.end].decode("utf-8")
            if identifier:
                if not token.startswith(quote) or not token.endswith(quote):
                    raise ValueError("quoting")
                inner = token[1:-1]
                i, decoded = 0, []
                while i < len(inner):
                    char = inner[i]
                    if char == quote:
                        if i + 1 >= len(inner) or inner[i + 1] != quote:
                            raise ValueError("undoubled identifier quote")
                        i += 1
                    decoded.append(char)
                    i += 1
                if "".join(decoded) != expected:
                    raise ValueError("identifier binding")
            elif expected is not None and token != expected:
                raise ValueError("SQL token")
            offset = event.end
            return token, event.start, event.end

        plan = ast.request.plan

        def scalar(value):
            nodes = parameters.value_nodes(value)
            opened = []
            for node in nodes[:-1]:
                opened.append((node, offset))
                if type(node) is parameters.SQLUnary:
                    take(
                        "syntax",
                        "unary_open",
                        node.original.ref,
                        "(" + node.original.expression.operator,
                    )
                else:
                    take("syntax", "anchor_open", node.original.ref, "CAST(")
            leaf = nodes[-1]
            tag = parameters.tag_of(leaf.original)
            family = ast.request.family
            if type(leaf) is parameters.SQLParameter:
                take(
                    "parameter",
                    tag,
                    leaf.site.ref,
                    "$" + str(leaf.use.server_index) if family == "postgres" else "?",
                )
            else:
                assert isinstance(leaf, parameters.SQLLiteral)
                token, _, _ = take("literal", tag, leaf.site.ref, None)
                if tag == "Bool":
                    if token not in {"TRUE", "FALSE"}:
                        raise ValueError("Boolean literal token")
                    decoded = token == "TRUE"
                elif tag == "Int":
                    if re.fullmatch(r"-?(0|[1-9][0-9]*)", token) is None:
                        raise ValueError("integer literal token")
                    decoded = int(token)
                    if str(decoded) != token:
                        raise ValueError("noncanonical integer literal")
                elif tag == "Float":
                    if family == "postgres":
                        if not token.startswith("'") or not token.endswith("'"):
                            raise ValueError("double input must be a string token")
                        spelling = token[1:-1]
                    else:
                        if "e" not in token:
                            raise ValueError(
                                "double requires approximate numeric spelling"
                            )
                        spelling = token[:-2] if token.endswith("e0") else token
                    decoded = float(spelling)
                    if not math.isfinite(decoded) or repr(decoded) != spelling:
                        raise ValueError("noncanonical binary64 spelling")
                elif family == "postgres":
                    if re.fullmatch(r"E'(?:\\[0-3][0-7]{2})*'", token) is None:
                        raise ValueError("explicit UTF8 string escape")
                    decoded = bytes(
                        int(token[i + 1 : i + 4], 8)
                        for i in range(2, len(token) - 1, 4)
                    ).decode("utf-8")
                else:
                    if re.fullmatch(r"X'(?:[0-9a-f]{2})*'", token) is None:
                        raise ValueError("UTF8 hexadecimal string")
                    decoded = bytes.fromhex(token[2:-1]).decode("utf-8")
                if not parameters.same_value(decoded, leaf.value):
                    raise ValueError("literal payload mismatch")
            for node, start in reversed(opened):
                if type(node) is parameters.SQLUnary:
                    role, close = "unary", ")"
                else:
                    role = "anchor"
                    close = " AS " + parameters.SQL_TYPES[node.physical_type] + ")"
                    if node.physical_type == "pg_text":
                        close += ' COLLATE "C"'
                    elif node.physical_type == "my_utf8mb4_text":
                        close += " COLLATE utf8mb4_0900_bin"
                take("syntax", role + "_close", node.original.ref, close)
                semantic_ranges.append((role, node.original.ref, start, offset))

        def select(body, owner):
            scan = body.scan
            take("syntax", "select", owner, "SELECT ")
            for position, column in enumerate(body.columns):
                if position:
                    take("syntax", "separator", column.projection.ref, ", ")
                if type(column) is SQLLiteralColumn and column.value is not None:
                    scalar(column.value)
                else:
                    if type(column) is SQLLiteralColumn:
                        if column.producer is None:
                            raise ValueError("literal terminal link missing")
                        input_port, port = (
                            column.producer.input_port,
                            column.producer.terminal,
                        )
                    else:
                        assert isinstance(column, SQLColumn)
                        input_port = column.input_port
                        port = (
                            column.source_port
                            if type(scan) is SQLScan
                            else column.producer.terminal
                        )
                    take(
                        "identifier",
                        "column_scope",
                        input_port.ref,
                        scan.symbol.name,
                        identifier=True,
                    )
                    take("syntax", "qualifier", column.projection.ref, ".")
                    take(
                        "identifier",
                        "column",
                        port.ref,
                        column.symbol.name,
                        identifier=True,
                    )
                take("syntax", "alias", column.projection.ref, " AS ")
                take(
                    "identifier",
                    "label",
                    column.export.ref,
                    column.label,
                    identifier=True,
                )
            if type(scan) is SQLScan:
                ref = scan.source.ref
                take("syntax", "from", ref, " FROM ")
                take(
                    "identifier",
                    "namespace",
                    ref,
                    scan.realization.namespace,
                    identifier=True,
                )
                take("syntax", "qualifier", ref, ".")
                take(
                    "identifier",
                    "relation",
                    ref,
                    scan.realization.name,
                    identifier=True,
                )
            else:
                if type(scan) is not SQLNamedUse:
                    raise ValueError("unknown SQL relation")
                ref = scan.cte.definition.original.ref
                take("syntax", "from", ref, " FROM ")
                take(
                    "identifier",
                    "cte_reference",
                    ref,
                    scan.cte.symbol.name,
                    identifier=True,
                )
            take("syntax", "alias", scan.use.ref, " AS ")
            take(
                "identifier",
                "relation_scope",
                scan.use.ref,
                scan.symbol.name,
                identifier=True,
            )

        if ast.ctes:
            take("syntax", "with", plan.scope, "WITH ")
            for i, cte in enumerate(ast.ctes):
                ref = cte.definition.original.ref
                if i:
                    take("syntax", "cte_separator", ref, ", ")
                take("identifier", "cte_name", ref, cte.symbol.name, identifier=True)
                take("syntax", "cte_columns_open", ref, " (")
                for j, symbol in enumerate(cte.columns):
                    if j:
                        take("syntax", "terminal_separator", symbol.binding, ", ")
                    take(
                        "identifier",
                        "terminal_column",
                        symbol.binding,
                        symbol.name,
                        identifier=True,
                    )
                take("syntax", "cte_body_open", ref, ") AS (")
                select(cte.body, ref)
                take("syntax", "cte_body_close", ref, ")")
            take("syntax", "with_body", ast.definition.original.ref, " ")
        select(ast, plan.scope)
        if (
            next(events, None) is not None
            or offset != len(data)
            or type(rendered.expression_ranges) is not tuple
            or len(rendered.expression_ranges) != len(semantic_ranges)
        ):
            return False
        for event, (role, subject, start, end) in zip(
            rendered.expression_ranges, semantic_ranges, strict=True
        ):
            if (
                type(event) is not RenderingEvent
                or event.kind != "expression_range"
                or event.role != role
                or event.subject is not subject
                or type(event.start) is not int
                or type(event.end) is not int
                or (event.start, event.end) != (start, end)
                or not _same(
                    event.origins, getattr(subjects.get(subject), "origins", ())
                )
            ):
                return False
        return True
    except (
        AttributeError,
        TypeError,
        ValueError,
        IndexError,
        KeyError,
        StopIteration,
        UnicodeError,
    ):
        return False


def verify_requirements(request, ast, original, generated):
    plan = request.plan
    entries = request.report.report.entries
    if (
        type(original) is not tuple
        or len(original) != len(plan.demands)
        or len(entries) != len(plan.demands)
    ):
        return False
    for item, entry, demand in zip(original, entries, plan.demands, strict=True):
        rule = (
            "R04"
            if entry.family.value == "fixed_literal_transport"
            or (
                entry.family.value == "expression"
                and type(plan.expressions[entry.subject.position])
                is not row.ProjectSQLReference
            )
            else "R03"
            if ast.ctes and entry.family.value == "scope"
            else "R01"
            if entry.family.value in {"source_realization", "expression", "scope"}
            else "R02"
        )
        if (
            type(item) is not OriginalRequirement
            or item.entry is not entry
            or entry.demand is not demand
            or item.rule != rule
        ):
            return False
    if type(generated) is not tuple:
        return False
    # The denominator comes from every actual definition/header/reference/body,
    # not from the supplied requirement list or a construction success tag.
    expected = []
    naming = tuple(
        p
        for p in request.premises
        if p.key == "identifier_case" and p.scope == "statement"
    )
    for cte in ast.ctes:
        expected.append(("cte_definition", cte.definition.original.ref, "R03", naming))
        for column in cte.columns:
            expected.append(("terminal_column", column.binding, "R03", naming))
    for body in (*[cte.body for cte in ast.ctes], ast):
        scan = body.scan
        if type(scan) is SQLScan:
            expected.append(
                (
                    "qualified_scan",
                    scan,
                    "R01",
                    applicable_premises(request, scan.realization.owner),
                )
            )
            for field in scan.realization.fields:
                expected.append(
                    (
                        "source_representation",
                        field,
                        "R02",
                        applicable_premises(request, scan.realization.owner, field),
                    )
                )
        else:
            expected.append(("named_use", scan.use.ref, "R03", naming))
            for symbol in scan.cte.columns:
                expected.append(("immediate_terminal", symbol.binding, "R03", naming))
        for column in body.columns:
            if type(column) is SQLLiteralColumn:
                expected.append(("value_projection", column.projection.ref, "R04", ()))
                if column.value is not None:
                    for node in parameters.value_nodes(column.value):
                        kind = (
                            "unary"
                            if type(node) is parameters.SQLUnary
                            else "type_anchor"
                            if type(node) is parameters.SQLAnchor
                            else "parameter"
                            if type(node) is parameters.SQLParameter
                            else "literal"
                        )
                        keys = {"operator_environment"}
                        if parameters.tag_of(node.original) == "Text":
                            keys.add("client_encoding")
                        if kind == "parameter":
                            keys.add("parameter_protocol")
                        used = tuple(
                            p
                            for p in request.premises
                            if p.scope == "statement" and p.key in keys
                        )
                        expected.append((kind, node.original.ref, "R04", used))
                continue
            expected.append(
                (
                    "field_projection",
                    column,
                    "R02",
                    applicable_premises(
                        request, column.origin.realization.owner, column.source_field
                    ),
                )
            )
        expected.append(("read_only_select_bytes", body, "R23", ()))
    if ast.ctes:
        expected.append(("nonrecursive_with_bytes", ast, "R23", ()))
    if len(expected) != len(generated):
        return False
    for requirement, (kind, subject, rule, premises) in zip(
        generated, expected, strict=True
    ):
        if (
            type(requirement) is not GeneratedRequirement
            or requirement.subject is not subject
            or (requirement.kind, requirement.rule) != (kind, rule)
            or not _same(requirement.premises, premises)
        ):
            return False
    return True


@dataclass(frozen=True, slots=True)
class EmissionVerification:
    issues: tuple[str, ...]

    @property
    def verified(self):
        return not self.issues


def verify_project_sql_emission(artifact, request):
    from pietto._project.project_sql_emission import EmissionArtifact

    issues = []
    try:
        rows_query = type(artifact) is EmissionArtifact and (
            type(artifact.ast) in {SQLRowQuery, SQLJoinQuery}
        )
        if (
            type(artifact) is not EmissionArtifact
            or artifact.request is not request
            or not (
                verify_row_query(request, artifact.ast)
                if rows_query
                else verify_sql_ast(request, artifact.ast)
            )
        ):
            issues.append("plan_ast_correspondence")
        if not (
            verify_row_bytes(artifact.ast, artifact.rendered)
            if rows_query
            else verify_sql_bytes(artifact.ast, artifact.rendered)
        ):
            issues.append("sql_bytes_or_ranges")
        if not (
            verify_row_requirements(
                request,
                artifact.ast,
                artifact.original_requirements,
                artifact.generated_requirements,
            )
            if rows_query
            else verify_requirements(
                request,
                artifact.ast,
                artifact.original_requirements,
                artifact.generated_requirements,
            )
        ):
            issues.append("requirement_denominators")
        if not (
            verify_row_parameters(artifact)
            if rows_query
            else verify_parameters(artifact)
        ):
            issues.append("fixed_value_or_parameter_correspondence")
        # Accepted bytes are retained, not reopened; semantic target changes
        # invalidate this product even when a query's spelling is unchanged.
        document = json.loads(request.normalized_bytes)
        if document["target"] != {"family": request.family, "release": request.release}:
            issues.append("target_input_binding")
    except (AttributeError, TypeError, ValueError, IndexError, KeyError):
        issues.append("artifact_structure")
    return EmissionVerification(tuple(issues))


def verify_parameters(artifact):
    plan, ast = artifact.request.plan, artifact.ast
    if not _same(artifact.fixed_values, plan.fixed_envelope.values):
        return False
    leaves = [
        node
        for body in (*[cte.body for cte in ast.ctes], ast)
        for column in body.columns
        if type(column) is SQLLiteralColumn and column.value is not None
        for node in parameters.value_nodes(column.value)
        if type(node) is parameters.SQLParameter
    ]
    tokens = [event for event in artifact.rendered.events if event.kind == "parameter"]
    if (
        type(artifact.parameter_uses) is not tuple
        or len(artifact.parameter_uses) != len(leaves)
        or len(tokens) != len(leaves)
        or len(leaves) > resource_limits(artifact.request)["parameters"]
    ):
        return False
    seen = {}
    for ordinal, (use, leaf, token) in enumerate(
        zip(artifact.parameter_uses, leaves, tokens, strict=True)
    ):
        slot = leaf.original.use.slot
        if slot not in seen:
            seen[slot] = (len(seen) + 1, use.physical_type)
        index, physical = seen[slot]
        if (
            type(use) is not parameters.NativeUse
            or use is not leaf.use
            or use.original is not leaf.original
            or use.slot is not slot
            or type(use.ordinal) is not int
            or use.ordinal != ordinal
            or type(use.server_index) is not int
            or use.server_index
            != (ordinal + 1 if artifact.request.family == "mysql" else index)
            or use.physical_type != physical
            or token.subject is not leaf.site.ref
        ):
            return False
    return len(seen) == len(plan.literal_slots) and all(
        slot in seen for slot in plan.literal_slots
    )


def _operand_children(plan):
    """Independent child order from the retained operand links, not node fields."""
    children: dict[object, list[tuple[int, object]]] = {}
    for operand in plan.operands:
        children.setdefault(operand.parent, []).append(
            (operand.position, operand.child)
        )
    result = {}
    for parent, items in children.items():
        ordered = sorted(items)
        if [position for position, _ in ordered] != list(range(len(ordered))):
            raise ValueError("operand positions")
        result[parent] = tuple(child for _, child in ordered)
    return result


def _row_realization(request, expression, operands):
    """Recompute one node's checked tag, storage, NULL posture and exact interval."""
    family = request.family
    tag, nullable = rows.value_tag(expression), rows.value_nullable(expression)
    if tag is None or nullable is None:
        raise ValueError("logical type evidence")
    if type(expression) is row.ProjectSQLIsNull:
        if tag != "Bool" or nullable is not False:
            raise ValueError("null test result")
        return rows.Realization(
            "Bool", {"kind": rows.BOOL_RESULT[family]}, nullable, {"kind": "bool01"}
        )
    if type(expression) is row.ProjectSQLComparison:
        left, right = operands
        if (
            expression.expression.operator not in rows.COMPARISONS
            or tag != "Bool"
            or left.tag not in rows.COMPARABLE
            or left.tag != right.tag
        ):
            raise ValueError("comparison domain")
        if left.tag == "Text" and tuple(
            left.domain.get(k) for k in ("encoding", "collation", "padding")
        ) != tuple(right.domain.get(k) for k in ("encoding", "collation", "padding")):
            raise ValueError("text comparison domain")
        if left.tag == "Decimal" and (
            left.storage != right.storage
            or tuple(left.domain.get(k) for k in ("precision", "scale"))
            != tuple(right.domain.get(k) for k in ("precision", "scale"))
        ):
            raise ValueError("decimal comparison parameters")
        return rows.Realization(
            "Bool", {"kind": rows.BOOL_RESULT[family]}, nullable, {"kind": "bool01"}
        )
    operator = expression.expression.operator
    if type(expression) is row.ProjectSQLBinary and operator in rows.LOGICAL:
        if tag != "Bool" or any(
            item.tag != "Bool" or item.domain.get("kind") != "bool01"
            for item in operands
        ):
            raise ValueError("logical domain")
        return rows.Realization(
            "Bool", {"kind": rows.BOOL_RESULT[family]}, nullable, {"kind": "bool01"}
        )
    if tag != "Int" or any(item.tag != "Int" for item in operands):
        raise ValueError("arithmetic domain")
    bounds = []
    for item in operands:
        interval = rows.int_bounds(item)
        if interval is None:
            raise ValueError("int range evidence")
        bounds.append(interval)
    if type(expression) is row.ProjectSQLUnary:
        if operator not in {"+", "-"}:
            raise ValueError("unary operator")
        low, high = (-bounds[0][1], -bounds[0][0]) if operator == "-" else bounds[0]
        storage = rows._arithmetic_storage(family, operands[0], operands[0])
    else:
        if operator not in rows.ARITHMETIC:
            raise ValueError("arithmetic operator")
        if operator == "+":
            low, high = bounds[0][0] + bounds[1][0], bounds[0][1] + bounds[1][1]
        elif operator == "-":
            low, high = bounds[0][0] - bounds[1][1], bounds[0][1] - bounds[1][0]
        else:
            products = [a * b for a in bounds[0] for b in bounds[1]]
            low, high = min(products), max(products)
        storage = rows._arithmetic_storage(family, operands[0], operands[1])
    if storage is None:
        raise ValueError("integer result has no physical type")
    limits = rows.signed_range(storage)
    if limits is None or low < limits[0] or high > limits[1]:
        raise ValueError("integer result outside its physical range")
    return rows.Realization(
        "Int",
        storage,
        nullable,
        {"kind": "int_range", "min": str(low), "max": str(high)},
    )


def _same_read(actual, expected):
    """Independent field-by-field image of one scan column; identity is not reused."""
    return (
        type(actual) is rows.StageColumn
        and type(expected) is rows.StageColumn
        and (actual.position, actual.name) == (expected.position, expected.name)
        and actual.terminal is expected.terminal
        and actual.field is expected.field
        and actual.source_port is expected.source_port
        and actual.literal is expected.literal
        and _same_origin(actual.aggregate, expected.aggregate)
        and _same_realization(actual.realization, expected.realization)
    )


def _same_origin(actual, expected):
    """One transported value's aggregate provenance, compared structurally."""
    if actual is None or expected is None:
        return actual is expected
    return (
        type(actual) is grouping.AggregateOrigin
        and type(expected) is grouping.AggregateOrigin
        and actual.kind == expected.kind
        and actual.aggregation is expected.aggregation
        and actual.result is expected.result
        and _same(actual.inputs, expected.inputs)
        and actual.key is expected.key
        and actual.aggregate is expected.aggregate
        and actual.function == expected.function
    )


def _window_result_realization(family, function, arguments, retained):
    """Independently re-derive one window result's own physical realization."""
    tag, nullable = retained
    if function in windowing.RANKING or function == "ntile":
        if tag != "Int" or nullable is not False:
            raise ValueError("window rank result domain")
        storage, bound = (
            windowing.BUCKET_REALIZATION[family]
            if function == "ntile"
            else (windowing.RANK_STORAGE[family], windowing.RANK_MAX)
        )
        return rows.Realization(
            "Int",
            {"kind": storage},
            False,
            {"kind": "int_range", "min": "0", "max": str(bound)},
        )
    if function in windowing.DISTRIBUTION:
        if tag != "Float":
            raise ValueError("window distribution result domain")
        return rows.Realization(
            "Float",
            {"kind": windowing.FLOAT_STORAGE[family]},
            bool(nullable),
            {"kind": "float64"},
        )
    values = [item for item in arguments if item.read is not None]
    if len(values) != 1:
        raise ValueError("window value result argument")
    carrier = values[0].read.realization
    if tag != carrier.tag:
        raise ValueError("window value result logical type")
    return rows.Realization(
        carrier.tag, carrier.storage, bool(nullable), carrier.domain
    )


def _aggregate_result_realization(family, function, argument, retained):
    """Independently re-derive one aggregate result's own physical realization."""
    tag, nullable = retained
    if function in grouping.COUNTING_FUNCTIONS:
        if tag != "Int" or nullable is not False:
            raise ValueError("count result domain")
        return rows.Realization(
            "Int",
            {"kind": grouping.COUNT_STORAGE[family]},
            False,
            {"kind": "int_range", "min": "0", "max": str(grouping.COUNT_MAX)},
        )
    if function not in grouping.EXTREMA_FUNCTIONS or argument is None:
        raise ValueError("aggregate function outside the promised domain")
    carrier = argument.realization
    if tag != carrier.tag or nullable is not True:
        raise ValueError("extrema result domain")
    return rows.Realization(carrier.tag, carrier.storage, True, carrier.domain)


def _verify_body_scope(body, position, state):
    """One body's own generated CTE name and ordered terminal column symbols."""
    if body.final:
        if body.symbol is not None or body.cte_columns != ():
            raise ValueError("final body publishes no generated scope")
        return
    if (
        body.symbol is None
        or body.symbol.position != position
        or body.symbol.binding is not body.block.ref
        or body.symbol.name != f"p{position}"  # unit index, not body index
        or len(body.cte_columns) != len(body.terminals)
    ):
        raise ValueError("generated stage scope")
    for index, (symbol, terminal) in enumerate(
        zip(body.cte_columns, body.terminals, strict=True)
    ):
        if (
            symbol.position != index
            or symbol.binding is not terminal.ref
            or symbol.name != f"c{index}"
        ):
            raise ValueError("generated terminal column")
    state["symbols"].extend((body.symbol, *body.cte_columns))


def _verify_aggregate_body(
    request, body, block, stage, keys, values, columns, children, state, reference_type
):
    """Independently rebuild one aggregation stage from its retained products."""
    realized = body.aggregation
    if (
        realized is None
        or type(realized) is not grouping.AggregateStage
        or realized.aggregation is not stage
        or realized.mode != stage.mode.value
        or realized.empty_input != stage.empty_input.value
        or len(body.columns) != len(keys) + len(values)
        or tuple(body.columns[: len(keys)]) != realized.keys
        or tuple(body.columns[len(keys) :]) != realized.values
        or len(block.exports) != len(body.columns)
        or len(keys) != len(stage.authority.keys)
        or len(values) != len(stage.authority.aggregates)
        # An aggregation stage filters nothing: satisfying is its own later stage.
        or body.predicate is not None
        or body.final
    ):
        raise ValueError("aggregate stage inventory")
    ports = {port.ref: port for port in request.plan.stage_ports}
    for index, (key, column) in enumerate(zip(keys, realized.keys, strict=True)):
        export = ports.get(block.exports[index])
        read = columns.get(key.input)
        retained = grouping.key_logical(key.source)
        label = f"c{index}"
        if (
            type(column) is not grouping.AggregateKeyColumn
            or column.ordinal != index
            or column.key is not key
            or column.input_port is not key.input
            or key.source is not stage.authority.keys[index]
            or export is None
            or export.source is not key.ref
            or column.export is not export
            or read is None
            or not _same_read(column.read, read)
            or retained is None
            or (read.realization.tag, read.realization.nullable) != retained
            or grouping.grouping_problem(read.realization) is not None
            or column.label != label
            or column.symbol.position != index + 1
            or column.symbol.binding is not export.ref
            or column.symbol.name != label
            or not identifier_valid(label, request.family)
            or not identifier_valid(read.name, request.family)
            or not _same_read(
                column.column,
                rows.StageColumn(
                    index,
                    label,
                    export.ref,
                    read.realization,
                    field=read.field,
                    source_port=read.source_port,
                    literal=read.literal,
                    aggregate=grouping.AggregateOrigin(
                        "group_key", stage, export.ref, (read.terminal,), key=key
                    ),
                ),
            )
            or column.column.scope is not None
        ):
            raise ValueError("group determinant")
        state["nodes"] += 1
        state["symbols"].append(column.symbol)
    for offset, (value, column) in enumerate(zip(values, realized.values, strict=True)):
        index = len(keys) + offset
        export = ports.get(block.exports[index])
        function = grouping.function_name(value.source)
        label = f"c{index}"
        if function is None or function not in grouping.SPELLING:
            raise ValueError("aggregate function outside the promised domain")
        arguments = plan_aggregation.arguments(value.source)
        if len(arguments) != len(value.arguments) or len(arguments) > 1:
            raise ValueError("aggregate argument signature")
        argument = column.argument
        if value.arguments:
            if argument is None:
                raise ValueError("aggregate argument missing")
            _verify_row_value(
                request,
                argument,
                value.arguments[0],
                columns,
                children,
                state,
                reference_type=reference_type,
            )
            if grouping.argument_problem(function, argument) is not None:
                raise ValueError("aggregate argument outside its admitted domain")
        elif argument is not None or function != "count":
            raise ValueError("row count keeps no scalar argument")
        retained = grouping.result_value(value.source)
        if retained is None:
            raise ValueError("aggregate result logical type evidence")
        expected = _aggregate_result_realization(
            request.family, function, argument, retained
        )
        if (
            type(column) is not grouping.AggregateValueColumn
            or column.ordinal != index
            or column.aggregate is not value
            or value.source is not stage.authority.aggregates[offset]
            or column.function != function
            or column.spelling != grouping.SPELLING[function]
            or column.distinct is not (function in grouping.DISTINCT_FUNCTIONS)
            or export is None
            or export.source is not value.ref
            or column.export is not export
            or column.label != label
            or column.symbol.position != index + 1
            or column.symbol.binding is not export.ref
            or column.symbol.name != label
            or not identifier_valid(label, request.family)
            or not _same_read(
                column.column,
                rows.StageColumn(
                    index,
                    label,
                    export.ref,
                    expected,
                    aggregate=grouping.AggregateOrigin(
                        "aggregate_result",
                        stage,
                        export.ref,
                        (argument.column.terminal,)
                        if argument is not None
                        else tuple(
                            columns[reference].terminal for reference in block.inputs
                        ),
                        aggregate=value,
                        function=function,
                    ),
                ),
            )
        ):
            raise ValueError("aggregate occurrence")
        state["nodes"] += 1
        state["symbols"].append(column.symbol)


def _verify_window_column(request, column, window, export, columns, definitions, state):
    """Re-derive one window result column from the retained plan alone.

    Nothing here calls the construction path: every field is checked against the
    plan's own authority, so a builder that invented a function, a direction, a
    partition or a result port cannot certify itself.
    """

    plan = request.plan
    policies = windowing.window_policies(plan)
    uses = windowing.window_uses(plan)
    arguments = windowing.window_arguments(plan)
    if type(column) is not windowing.WindowColumn or column.window is not window:
        return False
    if export.source is not window.ref:
        return False
    function = windowing.function_identity(window)
    if function is None or function not in windowing.SPELLING:
        return False
    if column.function != function or column.selected is not (
        window.selected is not None
    ):
        return False
    policy = policies.get(window.ref)
    if policy is None:
        return False
    if windowing.unsupported_modifier(policy.modifiers) is not None:
        return False
    items = arguments.get(window.ref, ())
    low, high = windowing.ARITY[function]
    if (
        not low <= len(items) <= high
        or len(items) != len(window.arguments)
        or len(column.arguments) != len(items)
    ):
        return False
    expected, problem = windowing.independent_arguments(
        policy, items, uses.get(window.ref, ()), columns
    )
    if expected is None or problem is not None:
        return False
    for realized, control in zip(column.arguments, expected, strict=True):
        if (
            realized.position != control.position
            or realized.role != control.role
            or realized.literal != control.literal
            or (realized.read is None) is not (control.read is None)
            or (
                realized.read is not None
                and not _same_read(realized.read, control.read)
            )
        ):
            return False
    specification = column.specification
    if specification.parent is not None:
        return False
    named = policy.named_use
    if named is None:
        if specification.symbol is not None:
            return False
    else:
        declaration = named.composed.base.target_declaration
        if declaration is None or specification.symbol is None:
            return False
        if specification.symbol.binding is not window.policy and not any(
            item.symbol is specification.symbol
            and item.named_use.composed.base.target_declaration is declaration
            for item in definitions
        ):
            return False
    partitions = [
        u for u in uses.get(window.ref, ()) if u.role.value == "window_partition"
    ]
    orders = [u for u in uses.get(window.ref, ()) if u.role.value == "window_order"]
    if len(specification.partitions) != len(partitions) or len(
        specification.orders
    ) != len(orders):
        return False
    for (binding, read), use in zip(specification.partitions, partitions, strict=True):
        if (
            binding is not policy.partitions[use.role_position]
            or not _same_read(read, columns[use.input])
            or read.realization.tag not in windowing.ORDER_TAGS
        ):
            return False
    for item, use in zip(specification.orders, orders, strict=True):
        binding = policy.orders[use.role_position]
        if (
            item.binding is not binding
            or item.direction != binding.effective_direction
            or item.direction not in {"asc", "desc"}
            or not _same_read(item.read, columns[use.input])
            or item.read.realization.tag not in windowing.ORDER_TAGS
        ):
            return False
    resolved = getattr(policy.specification.frame, "resolved", None)
    if resolved is None or resolved.unit is None:
        if specification.frame is not None:
            return False
    else:
        frame = specification.frame
        if (
            frame is None
            or frame.unit != resolved.unit.value
            or windowing.frame_problem(frame, request.family) is not None
            or windowing.offset_range_problem(frame, specification.orders) is not None
        ):
            return False
    if column.column.window is None or column.column.terminal is not export.ref:
        return False
    retained = windowing.result_value(window)
    if retained is None:
        return False
    try:
        realization = _window_result_realization(
            request.family, function, column.arguments, retained
        )
    except ValueError:
        return False
    if not _same_realization(column.column.realization, realization):
        return False
    state["nodes"] += windowing.column_nodes(column)
    return True


def _verify_helper_carry(column, ordinal, helper, columns) -> bool:
    """A hidden ORDER helper: an exact carry of one pre-projection stage port.

    It is labelled as the closed projection stage's own column and is never a
    canonical export, so it can be read by ORDER BY without entering the
    visible tuple.
    """
    label = f"c{ordinal}"
    read = columns.get(helper.source)
    return (
        helper.canonical is None
        and read is not None
        and type(column) is RowCarryColumn
        and column.ordinal == ordinal
        and column.export is helper
        and column.input_port is helper.source
        and column.label == label
        and column.symbol.position == ordinal + 1
        and column.symbol.binding is helper.ref
        and column.symbol.name == label
        and _same_read(column.read, read)
        and _same_read(
            column.column,
            replace(read, position=ordinal, name=label, terminal=helper.ref),
        )
    )


def _verify_aggregate_projection(
    request, body, block, stage, projections, columns, state, *, terminals=None
):
    """The exact canonical visible mapping; a hidden determinant stays hidden."""
    exports = body.definition.original.exports
    if terminals is None:
        terminals = body.definition.terminals
    helpers = terminals[len(exports) :]
    if (
        body.aggregation is not None
        or len(body.columns) != len(exports) + len(helpers)
        or len(projections) != len(exports)
        or len(terminals) < len(exports)
        or body.terminals != terminals
    ):
        raise ValueError("aggregate projection denominator")
    for offset, (column, helper) in enumerate(
        zip(body.columns[len(exports) :], helpers, strict=True)
    ):
        if body.final or not _verify_helper_carry(
            column, len(exports) + offset, helper, columns
        ):
            raise ValueError("aggregate projection helper carry")
        state["symbols"].append(column.symbol)
    for position, (column, projection, export, terminal) in enumerate(
        zip(body.columns[: len(exports)], projections, exports, terminals, strict=True)
    ):
        read = columns.get(projection.input)
        label = export.identity.name if body.final else f"c{position}"
        if (
            type(column) is not grouping.AggregateProjectionColumn
            or column.ordinal != position
            or column.projection is not projection
            or projection.block is not block.ref
            or projection.aggregation is not stage.ref
            or projection.export is not export.ref
            or column.export is not export
            or column.input_port is not projection.input
            or read is None
            or not _same_read(column.read, read)
            or column.label != label
            or column.symbol.position != position + 1
            or column.symbol.binding is not export.ref
            or column.symbol.name != label
            or not identifier_valid(label, request.family, label=body.final)
            or not identifier_valid(read.name, request.family)
            or not _same_read(
                column.column,
                rows.StageColumn(
                    position,
                    label,
                    terminal.ref,
                    read.realization,
                    field=read.field,
                    source_port=read.source_port,
                    literal=read.literal,
                    scope=read.scope,
                    aggregate=read.aggregate,
                ),
            )
        ):
            raise ValueError("aggregate result projection")
        state["symbols"].append(column.symbol)


def _same_realization(actual, expected):
    return (
        type(actual) is rows.Realization
        and (actual.tag, actual.nullable) == (expected.tag, expected.nullable)
        and actual.storage == expected.storage
        and actual.domain == expected.domain
    )


def _verify_row_value(
    request,
    value,
    reference,
    columns,
    children,
    state,
    *,
    reference_type: rows.ReferenceNode = row.ProjectSQLReference,
):
    """Walk the supplied tree against retained operand links and stage ports."""
    plan = request.plan
    expression = plan.expressions[reference.position]
    if expression.ref is not reference:
        raise ValueError("expression identity")
    if type(value) is rows.SQLStageReference:
        if (
            type(expression)
            not in {reference_type, plan_windows.ProjectSQLWindowReference}
            or value.original is not expression
            or value.port is not expression.port
            or reference in children
        ):
            raise ValueError("reference node")
        column = columns.get(expression.port)
        if column is None or not _same_read(value.column, column):
            raise ValueError("reference stage column")
        tag, nullable = rows.value_tag(expression), rows.value_nullable(expression)
        if (column.realization.tag, column.realization.nullable) != (tag, nullable):
            raise ValueError("reference type or NULL drift")
        if not _same_realization(value.realization, column.realization):
            raise ValueError("reference realization")
        if value.scope is not getattr(column, "scope", None):
            raise ValueError("reference scope")
        state["expressions"].append(expression)
        state["nodes"] += 1
        return value.realization
    if type(value) is not rows.SQLOperation:
        if not _verify_value(
            request, value, expression, state["expressions"], state["value_nodes"]
        ):
            raise ValueError("constant chain")
        state["nodes"] += len(parameters.value_nodes(value))
        return rows.constant_realization(value, request.family)
    if value.original is not expression:
        raise ValueError("operation identity")
    expected_kind = {
        row.ProjectSQLUnary: "sign",
        row.ProjectSQLIsNull: "null_test",
        row.ProjectSQLComparison: "comparison",
    }.get(type(expression))
    if expected_kind is None:
        if type(expression) is not row.ProjectSQLBinary:
            raise ValueError("operator node")
        expected_kind = (
            "logical"
            if expression.expression.operator in rows.LOGICAL
            else "arithmetic"
        )
    if value.kind != expected_kind:
        raise ValueError("operator kind")
    links = children.get(reference, ())
    if len(links) != len(value.operands):
        raise ValueError("operand denominator")
    state["expressions"].append(expression)
    state["nodes"] += 1
    operands = []
    for link, operand in zip(links, value.operands, strict=True):
        if rows.root_expression(operand).ref is not link:
            raise ValueError("operand order")
        operands.append(
            _verify_row_value(
                request,
                operand,
                link,
                columns,
                children,
                state,
                reference_type=reference_type,
            )
        )
    expected = _row_realization(request, expression, tuple(operands))
    if not _same_realization(value.realization, expected):
        raise ValueError("operator realization")
    return value.realization


def _join_reads(request, original, uses_by_ref, source_refs, produced, by_join, ports):
    """Independently rebuild one JOIN input's pre-match columns and alias."""
    alias = ast.SQLSymbol(0, original.ref, f"m{original.ref.position}")
    reads = []
    producer: Any = None
    source_ref: Any = None
    use = None
    if original.binding_use is not None:
        use = uses_by_ref.get(original.binding_use)
        if use is None:
            raise ValueError("join input use")
        if use.original.producer in source_refs:
            source = source_refs[use.original.producer]
            bound = tuple(
                item for item in request.sources if item.owner is source.source.owner
            )
            if len(bound) != 1:
                raise ValueError("join input source mapping")
            producer = bound[0]
            source_ref = source.ref
            for position, reference in enumerate(original.ports):
                link = use.bindings[position]
                fields = tuple(
                    item
                    for item in producer.fields
                    if item.field is link.canonical.field
                )
                if len(fields) != 1 or link.terminal is not link.canonical:
                    raise ValueError("join input source field")
                realization = rows.field_realization(fields[0])
                if realization is None:
                    raise ValueError("join input representation")
                reads.append(
                    rows.StageColumn(
                        position,
                        fields[0].column,
                        link.canonical.ref,
                        realization,
                        field=fields[0],
                        source_port=link.canonical.ref,
                        scope=alias,
                    )
                )
        else:
            producer = produced.get(use.original.producer)
            if producer is None:
                raise ValueError("join input producer")
            for position, reference in enumerate(original.ports):
                column = producer.columns[position].column
                if column.terminal is not use.bindings[position].terminal.ref:
                    raise ValueError("join input terminal")
                reads.append(
                    replace(column, position=position, name=f"c{position}", scope=alias)
                )
    else:
        producer = by_join.get(original.predecessor)
        if producer is None:
            raise ValueError("join predecessor")
        for position, reference in enumerate(original.ports):
            column = producer.columns[position]
            if column.port.ref is not ports[reference].source:
                raise ValueError("join predecessor port")
            reads.append(
                replace(
                    column.column, position=position, name=column.label, scope=alias
                )
            )
    columns = []
    for position, reference in enumerate(original.ports):
        realization, problem = joining.port_realization(
            ports[reference], reads[position], outer=False
        )
        if realization is None:
            raise ValueError("pre-match realization")
        columns.append(replace(reads[position], realization=realization))
    return alias, producer, use, tuple(columns), source_ref


def _verify_join_unit(request, unit, join, index, context, state):
    """Independent JOIN inventory, scopes, condition and published ports."""
    plan = request.plan
    if (
        type(unit) is not joining.JoinBody
        or unit.join is not join
        or unit.index != index
        or unit.symbol.name != f"p{index}"
        or unit.symbol.binding is not join.ref
        or join.kind not in joining.EXPECTED_ROWS
        or join.rows is not joining.EXPECTED_ROWS[join.kind]
        or unit.membership != joining.MEMBERSHIP.get(join.kind)
        or (unit.sentinel is None) != (unit.membership is None)
        or (unit.sentinel is not None and unit.sentinel is not join.ref)
    ):
        raise ValueError("join unit identity")
    inputs, ports, equalities = (
        context["inputs"],
        context["ports"],
        context["equalities"],
    )
    state["nodes"] += joining_node_count(unit)
    available: dict[Any, Any] = {}
    if len(unit.inputs) != 2 or len(join.inputs) != 2:
        raise ValueError("join arity")
    for ordinal, (reference, item) in enumerate(
        zip(join.inputs, unit.inputs, strict=True)
    ):
        original = inputs[reference]
        if (
            type(item) is not joining.JoinInput
            or item.original is not original
            or item.ordinal != ordinal
            or original.ordinal != ordinal
            or item.ports != tuple(original.ports)
            or (original.producer is None) == (original.predecessor is None)
            or (original.binding_use is None) != (original.producer is None)
        ):
            raise ValueError("join input identity")
        alias, producer, use, columns, source_ref = _join_reads(
            request,
            original,
            context["uses_by_ref"],
            context["source_refs"],
            context["produced"],
            context["by_join"],
            ports,
        )
        if (
            item.symbol.name != alias.name
            or item.symbol.binding is not original.ref
            or item.producer is not producer
            or item.use is not use
            or item.source is not source_ref
            or len(item.columns) != len(columns)
            or any(
                not _same_read(actual, expected)
                for actual, expected in zip(item.columns, columns, strict=True)
            )
            or any(column.scope is not item.symbol for column in item.columns)
        ):
            raise ValueError("join input columns")
        state["symbols"].append(item.symbol)
        for reference_port, column in zip(item.ports, item.columns, strict=True):
            available[reference_port] = column
    left, right = unit.inputs
    if len(unit.equalities) != len(join.equalities):
        raise ValueError("relationship equality denominator")
    for reference, item in zip(join.equalities, unit.equalities, strict=True):
        original = equalities[reference]
        if (
            type(item) is not joining.JoinEquality
            or item.original is not original
            or original.join is not join.ref
            or item.left_port is not original.left
            or item.right_port is not original.right
            or not _same_read(item.left, available[original.left])
            or not _same_read(item.right, available[original.right])
            or item.left_scope is not left.symbol
            or item.right_scope is not right.symbol
        ):
            raise ValueError("relationship equality image")
    if (unit.predicate is None) != (join.on is None):
        raise ValueError("match condition presence")
    if join.on is not None:
        realization = _verify_row_value(
            request,
            unit.predicate,
            join.on,
            available,
            context["children"],
            state,
            reference_type=row.ProjectSQLMatchReference,
        )
        if realization.tag != "Bool" or realization.domain.get("kind") != "bool01":
            raise ValueError("match condition root")
        site = join.site
        if site is None or plan.expressions[join.on.position].site is not site:
            raise ValueError("match condition site")
    if join.kind is AuthoredJoinKind.CROSS and (unit.equalities or unit.predicate):
        raise ValueError("cross join invented a condition")
    if join.kind is not AuthoredJoinKind.CROSS and not (
        unit.equalities or unit.predicate is not None
    ):
        raise ValueError("missing match condition")
    if join.kind is AuthoredJoinKind.FULL and (
        joining.full_admissible(join, unit.equalities, unit.predicate, request.family)
        is not None
    ):
        raise ValueError("full join outside its restricted domain")
    match = tuple(ports[reference] for reference in (*left.ports, *right.ports))
    expected = len(left.ports) if unit.membership is not None else len(match)
    if len(join.outputs) != expected or len(unit.columns) != expected:
        raise ValueError("join output arity")
    carriers = (*left.columns, *right.columns)
    rejected = joining.null_rejected_ports(join, unit.equalities, unit.predicate)
    match_refs = (*left.ports, *right.ports)
    for position, (reference, column) in enumerate(
        zip(join.outputs, unit.columns, strict=True)
    ):
        port = ports[reference]
        realization, problem = joining.port_realization(
            port,
            carriers[position],
            outer=True,
            proved=match_refs[position] in rejected,
        )
        if (
            realization is None
            or type(column) is not joining.JoinColumn
            or column.position != position
            or column.port is not port
            or column.match is not match[position]
            or port.source is not match[position].ref
            or port.kind is not ProjectSQLJoinPortKind.OUTPUT
            or port.block is not join.ref
            or port.position != position
            or column.label != f"c{position}"
            or column.symbol.position != position + 1
            or column.symbol.binding is not port.ref
            or column.symbol.name != column.label
            or not _same_read(column.read, carriers[position])
            or column.scope is not carriers[position].scope
            or not _same_realization(column.column.realization, realization)
            or column.column.terminal is not port.ref
            or column.column.name != column.label
            or tuple(port.nulling) != tuple(port.field.nulling_joins)
        ):
            raise ValueError("join output column")
        state["symbols"].append(column.symbol)
    if len(unit.cte_columns) != len(unit.columns):
        raise ValueError("join cte columns")
    for position, (symbol, column) in enumerate(
        zip(unit.cte_columns, unit.columns, strict=True)
    ):
        if (
            symbol.position != position
            or symbol.binding is not column.port.ref
            or symbol.name != column.label
        ):
            raise ValueError("join cte column symbol")
    state["symbols"].extend((unit.symbol, *unit.cte_columns))


def joining_node_count(unit) -> int:
    """This unit's own structural nodes; its condition is counted by the walk."""
    total = 4 + 3 * len(unit.columns) + 2 * len(unit.equalities)
    if unit.membership is not None:
        total += 3
    return total


def _result_ports(plan):
    grouped: dict[tuple[Any, Any], list[Any]] = {}
    for port in plan.result_ports:
        grouped.setdefault((port.boundary, port.role), []).append(port)

    def ordered(boundary, role):
        items = sorted(grouped.get((boundary, role), ()), key=lambda p: p.position)
        if [p.position for p in items] != list(range(len(items))):
            raise ValueError("result port positions")
        return tuple(items)

    return ordered


def _result_carrier(entry, boundary, order) -> str:
    """Independently classify the ORDER carrier from the entry's own authority."""
    from pietto._project.project_final_outputs import ProjectRelationOrdering
    from pietto._project.project_ir_properties import (
        ProjectIRProvidedRelationOrdering,
    )
    from pietto._project.project_query_block_ir import (
        ProjectIRCompletedQueryBlockOutput,
        ProjectIRReboundExistingOutput,
    )

    source = order.source
    if type(source) is not ProjectRelationOrdering or source.inputs is None:
        raise ValueError("relation ordering authority")
    properties = boundary.properties
    if type(entry) is ProjectIRCompletedQueryBlockOutput:
        if (
            boundary.operator.evidence is not source
            or properties.ordering is not source
        ):
            raise ValueError("completed ORDER carrier")
        return resulting.COMPLETED
    active = entry.active_properties.ordering
    if (
        type(active) is not ProjectIRProvidedRelationOrdering
        or active.output is not entry.active_output
        or active.items is not source.clause.items
    ):
        raise ValueError("active ORDER authority")
    if type(entry) is ProjectIRReusedEffectiveOutput:
        stage = entry.semantic_entry.fragment.property_stage
        provided = [
            p
            for p in stage.provided
            if type(p) is ProjectIRProvidedRelationOrdering
            and p.output.occurrence.producer is boundary.operator.node
        ]
        if (
            properties is not stage
            or len(provided) != 1
            or provided[0].items is not source.clause.items
        ):
            raise ValueError("ordinary ORDER carrier")
        return resulting.ORDINARY
    if type(entry) is ProjectIRReboundExistingOutput:
        provided = properties.ordering
        if (
            type(provided) is not ProjectIRProvidedRelationOrdering
            or provided.items is not source.clause.items
            or provided.output is not properties.relational.output
            or all(properties is not p for p in entry.row_properties)
            or entry.active_output is entry.semantic_entry.output
        ):
            raise ValueError("rebound ORDER carrier")
        return resulting.REBOUND
    raise ValueError("ORDER carrier")


def _verify_result_body(
    request, body, definition, boundaries, position, previous, last, state
):
    """Independent result-boundary correspondence from the retained plan alone.

    The visible tuple, the DISTINCT quotient, every ORDER key's exact port and
    direction, the static LIMIT and the terminal image are re-derived here from
    the plan collections; the builder's own walk is never reused.
    """
    plan = request.plan
    family = request.family
    entry = definition.original.entry
    exports = definition.original.exports
    authored = entry.owner.definition
    kinds = resulting.KINDS
    roles = resulting.ROLES
    if (
        type(body) is not resulting.RowResultBody
        or body.definition is not definition
        or body.boundaries != tuple(boundaries)
        or body.index != position
        or body.final != last
        or body.final != (entry.owner is plan.scope.selected_owner)
        or type(previous) is not RowBody
        or previous.definition is not definition
        or previous.block.kind.value != "projection"
        or previous.final
        or previous.symbol is None
    ):
        raise ValueError("result body placement")
    scan = body.scan
    first = boundaries[0]
    if (
        type(scan) is not resulting.RowResultUse
        or scan.body is not previous
        or scan.boundary is not first
        or scan.symbol.position != 0
        or scan.symbol.binding is not first.ref
        or scan.symbol.name != f"t{first.ref.position}"
    ):
        raise ValueError("result scan")
    state["symbols"].append(scan.symbol)
    ordered = _result_ports(plan)
    carried = ordered(previous.block.ref, roles.PROJECTION)
    if len(carried) != len(previous.columns) or previous.terminals != carried:
        raise ValueError("result projection inventory")
    reads: dict[Any, tuple[Any, Any]] = {}
    for port, column in zip(carried, previous.columns, strict=True):
        if column.column.terminal is not port.ref or port.definition is not (
            definition.original.ref
        ):
            raise ValueError("result projection port")
        reads[port.ref] = (port, column.column)
    traces: dict[Any, tuple[Any, ...]] = {
        port.ref: () for port in carried if port.canonical is not None
    }
    seen: set[Any] = set()
    predecessor = previous.block.ref
    distinct = order = limit = None
    for index, boundary in enumerate(boundaries):
        if (
            boundary.definition is not definition.original.ref
            or boundary.position != index
            or boundary.predecessor is not predecessor
            or boundary.kind not in set(kinds)
            or boundary.kind in seen
        ):
            raise ValueError("result boundary chain")
        seen.add(boundary.kind)
        inputs = ordered(boundary.ref, roles.INPUT)
        outputs = ordered(boundary.ref, roles.OUTPUT)
        if len(inputs) != len(carried) or any(
            port.source is not previous_port.ref
            or port.canonical is not previous_port.canonical
            or port.key is not previous_port.key
            or port.definition is not definition.original.ref
            for port, previous_port in zip(inputs, carried, strict=True)
        ):
            raise ValueError("result boundary inputs")
        visible = tuple(port for port in inputs if port.canonical is not None)
        if (
            len(outputs) != len(visible)
            or any(
                port.source is not previous_port.ref
                or port.canonical is not previous_port.canonical
                for port, previous_port in zip(outputs, visible, strict=True)
            )
            or tuple(port.canonical for port in visible) != tuple(exports)
        ):
            raise ValueError("result boundary outputs")
        for port, previous_port in zip(inputs, carried, strict=True):
            reads[port.ref] = reads[previous_port.ref]
            if previous_port.ref in traces:
                traces[port.ref] = traces[previous_port.ref]
        fields_by_input: dict[Any, Any] = {}
        if boundary.kind is kinds.DISTINCT:
            (value,) = tuple(d for d in plan.distincts if d.boundary is boundary.ref)
            fields = sorted(
                (f for f in plan.quotient_fields if f.distinct is value.ref),
                key=lambda f: f.position,
            )
            if (
                distinct is not None
                or len(visible) != len(inputs)
                or len(fields) != len(inputs)
                or tuple(f.ref for f in fields) != tuple(value.fields)
                or any(
                    f.position != i
                    or f.input is not inputs[i].ref
                    or f.output is not outputs[i].ref
                    or f.canonical is not exports[i]
                    or f.equivalence.reason is not None
                    or reads[inputs[i].ref][1].realization.tag
                    not in resulting.ORDER_TAGS
                    for i, f in enumerate(fields)
                )
            ):
                raise ValueError("distinct quotient")
            if distinct is not None:
                raise ValueError("distinct image")
            distinct = body.distinct
            if (
                type(distinct) is not resulting.ResultDistinct
                or distinct.distinct is not value
                or distinct.boundary is not boundary
                or distinct.fields != tuple(fields)
            ):
                raise ValueError("distinct image")
            fields_by_input = {
                port.ref: f for port, f in zip(inputs, fields, strict=True)
            }
            state["nodes"] += 1
        elif boundary.kind is kinds.ORDER:
            (value,) = tuple(o for o in plan.orders if o.boundary is boundary.ref)
            carrier = _result_carrier(entry, boundary, value)
            items = sorted(
                (i for i in plan.order_items if i.ordering is value.ref),
                key=lambda i: i.position,
            )
            hidden = {h.item for h in plan.hidden_order_requirements}
            if order is not None or type(body.order) is not resulting.ResultOrder:
                raise ValueError("order image")
            order = body.order
            if (
                order.order is not value
                or order.boundary is not boundary
                or order.carrier != carrier
                or tuple(i.ref for i in items) != tuple(value.items)
                or len(order.items) != len(items)
                or not items
            ):
                raise ValueError("order inventory")
            expressions = {e.ref: e for e in plan.order_expressions}
            uses = {u.ref: u for u in plan.order_uses}
            by_ref = {port.ref: port for port in inputs}
            for position_, (item, realized) in enumerate(
                zip(items, order.items, strict=True)
            ):
                root = expressions.get(item.expression)
                use = None if root is None or root.use is None else uses.get(root.use)
                if (
                    type(realized) is not resulting.ResultOrderItem
                    or realized.item is not item
                    or realized.position != position_
                    or item.position != position_
                    or item.value is not item.expression
                    or item.ref in hidden
                    or root is None
                    or root.item is not item.ref
                    or root.expression is not item.source.expression
                    or root.operands != ()
                    or use is None
                    or use.item is not item.ref
                    or use.scope is not boundary.ref
                    or use.requirement is not None
                    or use.source.expression is not root.expression
                    or realized.expression is not root
                    or realized.use is not use
                    or not use.ports
                    or any(ref not in by_ref for ref in use.ports)
                ):
                    raise ValueError("order item authority")
                port = min((by_ref[ref] for ref in use.ports), key=lambda p: p.position)
                read = reads[port.ref][1]
                direction = item.source.direction.value
                if (
                    realized.port is not port
                    or not _same_read(realized.read, read)
                    or realized.direction != direction
                    or direction not in {"asc", "desc"}
                    or (
                        item.source.item.direction is not None
                        and item.source.item.direction != direction
                    )
                    or realized.nulls is not None
                    or realized.carrier != carrier
                    or read.realization.tag not in resulting.ORDER_TAGS
                    or rows.value_tag(item.source) != read.realization.tag
                ):
                    raise ValueError("order item binding")
                state["nodes"] += 1
        else:
            (value,) = tuple(
                v for v in plan.result_limits if v.boundary is boundary.ref
            )
            if limit is not None:
                raise ValueError("limit image")
            limit = body.limit
            if (
                type(limit) is not resulting.ResultLimit
                or limit.limit is not value
                or limit.boundary is not boundary
                or value.clause is not authored.limit_clause
                or value.literal is not value.clause.expression
                or type(value.value) is not int
                or isinstance(value.value, bool)
                or limit.value != value.value
                or value.value != value.literal.value
                or not 0 <= value.value <= value.maximum
                or value.row_count_upper_bound != value.value
            ):
                raise ValueError("static limit")
            state["nodes"] += 1
        for port, previous_port in zip(outputs, visible, strict=True):
            reads[port.ref] = reads[previous_port.ref]
            traces[port.ref] = (
                *traces[previous_port.ref],
                (boundary, previous_port, port, fields_by_input.get(previous_port.ref)),
            )
        carried = outputs
        predecessor = boundary.ref
    if (body.distinct is None) != (distinct is None) or (
        (body.order is None) != (order is None)
        or (body.limit is None) != (limit is None)
    ):
        raise ValueError("result stage denominator")
    if (
        carried != tuple(definition.terminals)
        or body.terminals != carried
        or len(body.columns) != len(carried)
        or len(carried) != len(exports)
    ):
        raise ValueError("result terminal inventory")
    for ordinal, (column, port, export) in enumerate(
        zip(body.columns, carried, exports, strict=True)
    ):
        projection_port, read = reads[port.ref]
        label = export.identity.name if body.final else f"c{ordinal}"
        trace = traces[port.ref]
        if (
            type(column) is not resulting.ResultColumn
            or column.ordinal != ordinal
            or column.export is not export
            or port.canonical is not export
            or column.projection_port is not projection_port
            or column.output is not port
            or not _same_read(column.read, read)
            or not _same_read(
                column.column,
                replace(read, position=ordinal, name=label, terminal=port.ref),
            )
            or column.label != label
            or column.symbol.position != ordinal + 1
            or column.symbol.binding is not export.ref
            or column.symbol.name != label
            or not identifier_valid(label, family, label=body.final)
            or not identifier_valid(read.name, family)
            or len(column.stages) != len(trace)
            or any(
                type(stage) is not resulting.ResultStage
                or stage.boundary is not expected[0]
                or stage.input_port is not expected[1]
                or stage.output_port is not expected[2]
                or stage.quotient_field is not expected[3]
                for stage, expected in zip(column.stages, trace, strict=True)
            )
        ):
            raise ValueError("result column")
        state["symbols"].append(column.symbol)
    _verify_body_scope(body, position, state)


def _set_column_realization(kind, quantifier, column, reads, evidence):
    """Independently re-derive one SET output's realization from operand reads."""
    from pietto.ast_nodes import SetOperationKind as Kind
    from pietto.ast_nodes import SetOperationQuantifier as Quantifier

    tags = {read.realization.tag for read in reads}
    if len(tags) != 1:
        raise ValueError("set column tags")
    (tag,) = tags
    union_all = (kind, quantifier) == (Kind.UNION, Quantifier.ALL)
    if tag not in {"Int", "Bool", "Text", "Decimal"} and not (
        union_all and tag == "Float"
    ):
        raise ValueError("set comparison domain")
    if not union_all and any(item.reason is not None for item in evidence):
        raise ValueError("set equivalence evidence")
    first = reads[0].realization
    storage = first.storage
    domain = dict(first.domain)
    if tag == "Int":
        widths = {rows.INT_WIDTHS.get(r.realization.storage["kind"]) for r in reads}
        bounds = [rows.int_bounds(r.realization) for r in reads]
        if None in widths or len(widths) != 1 or any(b is None for b in bounds):
            raise ValueError("set int width")
        low = min(b[0] for b in bounds if b is not None)
        high = max(b[1] for b in bounds if b is not None)
        domain = {"kind": "int_range", "min": str(low), "max": str(high)}
    else:
        if any(r.realization.storage != storage for r in reads):
            raise ValueError("set storage")
        if tag == "Text":
            keys = ("encoding", "collation", "padding")
            if (
                len({tuple(r.realization.domain.get(k) for k in keys) for r in reads})
                != 1
            ):
                raise ValueError("set text domain")
            domain["max_characters"] = max(
                int(r.realization.domain.get("max_characters", 0)) for r in reads
            )
        elif tag == "Decimal":
            pairs = {
                (
                    r.realization.domain.get("precision"),
                    r.realization.domain.get("scale"),
                )
                for r in reads
            }
            if len(pairs) != 1 or None in next(iter(pairs)):
                raise ValueError("set decimal parameters")
        elif any(r.realization.domain != first.domain for r in reads):
            raise ValueError("set domain")
    states = tuple(r.realization.nullable for r in reads)
    if kind is Kind.EXCEPT:
        nullable = states[0]
    elif kind is Kind.INTERSECT and False in states:
        nullable = False
    elif all(state is False for state in states):
        nullable = False
    elif "unknown" in states:
        nullable = "unknown"
    else:
        nullable = True
    expected = setting.NULLABILITY[column.source.nullability]
    if nullable != expected:
        raise ValueError("set nullability")
    return rows.Realization(tag, storage, nullable, domain)


def _verify_set_unit(request, unit, definition, body, position, produced, last, state):
    """Independent SET correspondence from the retained plan alone.

    The operand inventory, each operand's complete terminal read, the
    positional column map, every output's realization and the terminal image
    are re-derived here from the plan collections; the builder's walk and the
    renderer are never reused.
    """
    plan = request.plan
    family = request.family
    exports = definition.original.exports
    uses_by_ref = {u.original.ref: u for u in request.layout.uses}
    source_refs = {source.ref: source for source in plan.sources}
    if (
        type(unit) is not setting.SetBody
        or unit.definition is not definition
        or unit.body is not body
        or unit.index != position
        or unit.final != last
        or unit.final != (definition.original.entry.owner is plan.scope.selected_owner)
        or unit.kind is not body.kind
        or unit.quantifier is not body.quantifier
        or body.fold != "source_order_left_fold"
        or unit.predicate is not None
        or unit.aggregation is not None
        or unit.window is not None
    ):
        raise ValueError("set unit placement")
    operands = sorted(
        (o for o in plan.set_operands if o.body is body.ref), key=lambda o: o.position
    )
    inputs = {i.ref: i for i in plan.set_inputs}
    columns = sorted(
        (c for c in plan.set_columns if c.body is body.ref), key=lambda c: c.position
    )
    if (
        tuple(o.ref for o in operands) != tuple(body.operands)
        or tuple(c.ref for c in columns) != tuple(body.columns)
        or len(operands) < 2
        or len(unit.operands) != len(operands)
        or len(unit.columns) != len(columns)
        or len(columns) != len(exports)
    ):
        raise ValueError("set inventory")
    reads_by_operand = []
    for realized, operand in zip(unit.operands, operands, strict=True):
        use = uses_by_ref[operand.use.ref]
        if (
            type(realized) is not setting.SetOperandBody
            or realized.operand is not operand
            or realized.position != operand.position
            or realized.use is not use
            or use.original.consumer is not definition.original.ref
            or realized.symbol.position != 0
            or realized.symbol.binding is not operand.ref
            or realized.symbol.name != f"o{operand.ref.position}"
            or tuple(f.ref for f in realized.inputs) != tuple(operand.fields)
            or len(realized.columns) != len(operand.fields)
            or len(use.bindings) != len(operand.fields)
        ):
            raise ValueError("set operand")
        state["symbols"].append(realized.symbol)
        reads = []
        if use.original.producer in source_refs:
            source = source_refs[use.original.producer]
            bound = tuple(
                item for item in request.sources if item.owner is source.source.owner
            )
            if (
                len(bound) != 1
                or realized.producer is not bound[0]
                or realized.source is not source
            ):
                raise ValueError("set operand source")
            for slot, (ref, link) in enumerate(
                zip(operand.fields, use.bindings, strict=True)
            ):
                field = inputs[ref]
                matches = tuple(
                    item
                    for item in bound[0].fields
                    if item.field is link.canonical.field
                )
                if (
                    len(matches) != 1
                    or link.terminal is not link.canonical
                    or field.terminal is not link.terminal
                    or field.binding is not link.input_port
                    or field.operand is not operand.ref
                    or field.position != slot
                ):
                    raise ValueError("set operand field")
                realization = rows.field_realization(matches[0])
                if realization is None:
                    raise ValueError("set operand representation")
                reads.append(
                    rows.StageColumn(
                        slot,
                        matches[0].column,
                        link.canonical.ref,
                        realization,
                        field=matches[0],
                        source_port=link.canonical.ref,
                    )
                )
        else:
            producer = produced.get(use.original.producer)
            if (
                producer is None
                or realized.producer is not producer
                or realized.source is not None
                or getattr(producer, "final", True)
            ):
                raise ValueError("set operand producer")
            for slot, (ref, link) in enumerate(
                zip(operand.fields, use.bindings, strict=True)
            ):
                field = inputs[ref]
                column = producer.columns[slot].column
                if (
                    column.terminal is not link.terminal.ref
                    or field.terminal is not link.terminal
                    or field.binding is not link.input_port
                    or field.operand is not operand.ref
                    or field.position != slot
                ):
                    raise ValueError("set operand terminal")
                reads.append(replace(column, position=slot, name=f"c{slot}"))
        if any(
            not _same_read(actual, expected)
            for actual, expected in zip(realized.columns, reads, strict=True)
        ):
            raise ValueError("set operand columns")
        reads_by_operand.append(reads)
    for ordinal, (realized, column, export, terminal) in enumerate(
        zip(unit.columns, columns, exports, definition.terminals, strict=True)
    ):
        reads = tuple(item[ordinal] for item in reads_by_operand)
        evidence = tuple(inputs[ref].evidence for ref in column.inputs)
        realization = _set_column_realization(
            body.kind, body.quantifier, column, reads, evidence
        )
        label = export.identity.name if unit.final else f"c{ordinal}"
        if (
            type(realized) is not setting.SetColumn
            or realized.ordinal != ordinal
            or realized.source is not column
            or realized.export is not export
            or realized.output is not terminal
            or column.output is not terminal.ref
            or terminal.canonical is not export
            or column.position != ordinal
            or tuple(column.inputs) != tuple(o.fields[ordinal] for o in operands)
            or any(
                not _same_read(actual, expected)
                for actual, expected in zip(realized.inputs, reads, strict=True)
            )
            or not _same_realization(realized.realization, realization)
            or realized.label != label
            or realized.symbol.position != ordinal + 1
            or realized.symbol.binding is not export.ref
            or realized.symbol.name != label
            or not identifier_valid(label, family, label=unit.final)
            or not _same_read(
                realized.column,
                rows.StageColumn(ordinal, label, terminal.ref, realization),
            )
        ):
            raise ValueError("set column")
        state["symbols"].append(realized.symbol)
    if unit.terminals != tuple(definition.terminals):
        raise ValueError("set terminals")
    _verify_body_scope(unit, position, state)
    state["nodes"] += setting.node_count(unit)


def verify_row_query(request, query):
    """Independent stage schedule, scope, column and expression correspondence."""
    try:
        plan = request.plan
        joined = bool(plan.joins)
        if (
            not prepared_current(request)
            or type(query) not in {SQLRowQuery, SQLJoinQuery}
            or query.request is not request
            or (type(query) is SQLJoinQuery) != bool(plan.joins or plan.set_bodies)
            or (
                joining.admitted_join_shape(plan)
                if joined
                else admitted_row_shape(plan)
            )
            is False
            or (joined and admitted_row_shape(plan))
            or projection_chain_shape(plan)
            or emission_blockers(request)
        ):
            return False
        children = _operand_children(plan)
        lets = {value.site.block: value for value in plan.let_values}
        filters = {item.site.block: item for item in plan.filters}
        projections: dict[object, list[Any]] = {}
        for projection in plan.projections:
            projections.setdefault(projection.block, []).append(projection)
        stages = grouping.aggregated_definitions(plan)
        aggregate_keys: dict[object, list[object]] = {}
        for key in sorted(plan.group_keys, key=lambda item: item.position):
            aggregate_keys.setdefault(key.aggregation, []).append(key)
        aggregate_values: dict[object, list[object]] = {}
        for value in sorted(plan.aggregates, key=lambda item: item.position):
            aggregate_values.setdefault(value.aggregation, []).append(value)
        aggregate_projections: dict[object, list[Any]] = {}
        for projection in plan.aggregate_projections:
            aggregate_projections.setdefault(projection.block, []).append(projection)
        window_projections: dict[object, list[Any]] = {}
        for projection in plan.window_projections:
            window_projections.setdefault(projection.block, []).append(projection)
        window_blocks = windowing.windowed_blocks(plan)
        uses_by_consumer = {u.consumer.original.ref: u for u in request.layout.uses}
        uses_by_ref = {u.original.ref: u for u in request.layout.uses}
        source_refs = {source.ref: source for source in plan.sources}
        join_groups = joining.joined_definitions(plan) if joined else {}
        tails = {tail.definition: tail for tail in plan.join_tails}
        join_context = {
            "inputs": {item.ref: item for item in plan.join_inputs},
            "ports": {port.ref: port for port in plan.join_ports},
            "equalities": {item.ref: item for item in plan.relationship_matches},
            "uses_by_ref": uses_by_ref,
            "source_refs": source_refs,
            "children": children,
        }
        result_groups = resulting.boundaries_by_definition(plan)
        set_groups = setting.bodies_by_definition(plan)
        expected = []
        for definition, blocks in definition_blocks(request):
            set_body = set_groups.get(definition.original.ref)
            if set_body is not None:
                if blocks or join_groups.get(definition.original.ref):
                    return False
                expected.append((definition, set_body, "set"))
                continue
            for join in join_groups.get(definition.original.ref, ()):
                expected.append((definition, join, None))
            for index, block in enumerate(blocks):
                expected.append((definition, block, index))
            boundaries = result_groups.get(definition.original.ref, ())
            if boundaries:
                # The result body follows the visible projection of its own
                # definition and is that definition's terminal producer.
                expected.append((definition, boundaries, "result"))
        units = query.units if type(query) is SQLJoinQuery else query.bodies
        if len(expected) != len(units):
            return False
        state = {"expressions": [], "value_nodes": [], "nodes": 0, "symbols": []}
        symbols = state["symbols"]
        produced: dict[object, object] = {}
        by_join: dict[object, object] = {}
        columns_by_body = {}
        join_context["produced"] = produced
        join_context["by_join"] = by_join
        for position, ((definition, block, index), body) in enumerate(
            zip(expected, units, strict=True)
        ):
            if index is None:
                _verify_join_unit(request, body, block, position, join_context, state)
                by_join[block.ref] = body
                continue
            if index == "set":
                _verify_set_unit(
                    request,
                    body,
                    definition,
                    block,
                    position,
                    produced,
                    position == len(units) - 1,
                    state,
                )
                produced[definition.original.ref] = body
                continue
            if index == "result":
                _verify_result_body(
                    request,
                    body,
                    definition,
                    block,
                    position,
                    units[position - 1],
                    position == len(units) - 1,
                    state,
                )
                produced[definition.original.ref] = body
                continue
            joined_definition = bool(join_groups.get(definition.original.ref, ()))
            result_boundaries = result_groups.get(definition.original.ref, ())
            selected = definition.original.entry.owner is plan.scope.selected_owner
            if (
                type(body.scan) not in {RowScan, RowNamedUse, RowStageUse, RowJoinUse}
                or body.definition is not definition
                or body.block is not block
                or body.index != index
                or body.final != (position == len(units) - 1)
                or body.final
                != (
                    block.kind.value == "projection"
                    and selected
                    and not result_boundaries
                )
            ):
                return False
            binding = uses_by_consumer.get(definition.original.ref)
            scan = body.scan
            if index == 0 and joined_definition:
                tail = tails.get(definition.original.ref)
                joins = join_groups[definition.original.ref]
                if (
                    tail is None
                    or type(scan) is not RowJoinUse
                    or scan.tail is not tail
                    or tail.join is not joins[-1].ref
                    or scan.body is not by_join.get(joins[-1].ref)
                    or scan.symbol.binding is not tail.ref
                    or scan.symbol.name != f"t{tail.ref.position}"
                ):
                    return False
            elif index == 0:
                if binding is None:
                    return False
                use = binding.original
                if (
                    scan.symbol.name != f"s{use.ref.position}"
                    or scan.symbol.binding is not use.ref
                ):
                    return False
                # the producer/source discrimination below is unchanged
                if use.producer in source_refs:
                    if (
                        type(scan) is not RowScan
                        or scan.source is not source_refs[use.producer]
                        or scan.binding is not binding
                        or scan.use is not use
                        or not any(scan.realization is s for s in request.sources)
                        or scan.realization.owner is not scan.source.source.owner
                    ):
                        return False
                elif (
                    type(scan) is not RowNamedUse
                    or scan.binding is not binding
                    or scan.use is not use
                    or scan.body is not produced.get(use.producer)
                ):
                    return False
            elif (
                type(scan) is not RowStageUse
                or scan.block is not block
                or scan.body is not units[position - 1]
                or scan.body.definition is not definition
                or scan.symbol.binding is not block.ref
                or scan.symbol.name != f"t{block.ref.position}"
            ):
                return False
            symbols.append(scan.symbol)
            stage_ports = {port.ref: port for port in plan.stage_ports}
            for slot, reference in enumerate(block.inputs):
                port = stage_ports.get(reference)
                if port is None or port.block is not block.ref:
                    return False
                if index == 0 and joined_definition:
                    if port.source is not tails[definition.original.ref].ports[slot]:
                        return False
                elif index == 0:
                    assert binding is not None
                    if port.source is not binding.bindings[slot].input_port.ref:
                        return False
                elif port.source is not units[position - 1].block.exports[slot]:
                    return False
            columns = dict(
                zip(block.inputs, _row_reads(request, scan, block), strict=True)
            )
            if any(column is None for column in columns.values()):
                return False
            columns_by_body[position] = columns
            kind = block.kind.value
            stage = stages.get(definition.original.ref)
            if (kind == "aggregate") is not (
                stage is not None and block.ref is stage.block
            ):
                return False
            if kind == "aggregate":
                assert stage is not None
                _verify_aggregate_body(
                    request,
                    body,
                    block,
                    stage,
                    tuple(aggregate_keys.get(stage.ref, ())),
                    tuple(aggregate_values.get(stage.ref, ())),
                    columns,
                    children,
                    state,
                    row.ProjectSQLJoinedReference
                    if joined_definition
                    else row.ProjectSQLReference,
                )
                if body.terminals != tuple(
                    stage_ports.get(ref) for ref in block.exports
                ):
                    return False
                _verify_body_scope(body, position, state)
                continue
            if (
                kind == "projection"
                and stage is not None
                and not window_projections.get(block.ref)
            ):
                _verify_aggregate_projection(
                    request,
                    body,
                    block,
                    stage,
                    tuple(aggregate_projections.get(block.ref, ())),
                    columns,
                    state,
                    terminals=(
                        resulting.projection_terminals(plan, block.ref)
                        if result_boundaries
                        else definition.terminals
                    ),
                )
                if body.predicate is not None:
                    return False
                _verify_body_scope(body, position, state)
                produced[definition.original.ref] = body
                continue
            if body.aggregation is not None or (
                aggregate_projections.get(block.ref)
                and not window_projections.get(block.ref)
            ):
                # A mixed visible projection carries both this aggregation's
                # results and this body's window results; only that shape may
                # reach the claim-based path.
                return False
            if kind == "window" and not window_blocks.get(block.ref):
                return False
            carries = 0 if kind == "projection" else len(block.inputs)
            if kind == "projection":
                claims: dict[Any, Any] = {}
                for entry in projections.get(block.ref, ()):
                    claims[entry.export] = entry
                for entry in aggregate_projections.get(block.ref, ()):
                    if entry.export in claims:
                        return False
                    claims[entry.export] = entry
                for entry in window_projections.get(block.ref, ()):
                    if entry.export in claims:
                        return False
                    claims[entry.export] = entry
                ordered_items = tuple(
                    claims.get(export.ref) for export in definition.original.exports
                )
                if any(entry is None for entry in ordered_items):
                    return False
                items: tuple[Any, ...] = ordered_items
            else:
                items = (lets[block.ref],) if kind == "let" else ()
            if kind == "window":
                items = tuple(window_blocks.get(block.ref, ()))
                # Each generated WINDOW definition is its own emitted structure.
                state["nodes"] += (
                    0 if body.window is None else len(body.window.definitions)
                )
            if len(body.columns) != carries + len(items) + (
                len(resulting.projection_terminals(plan, block.ref))
                - len(definition.original.exports)
                if kind == "projection" and result_boundaries
                else 0
            ):
                return False
            block_exports: tuple[Any, ...] = ()
            if kind != "projection":
                resolved_exports = [stage_ports.get(ref) for ref in block.exports]
                if any(port is None for port in resolved_exports):
                    return False
                block_exports = tuple(resolved_exports)
            terminals: tuple[Any, ...] = (
                definition.original.exports if kind == "projection" else block_exports
            )
            helpers: tuple[Any, ...] = ()
            if kind == "projection" and result_boundaries:
                projection_ports = resulting.projection_terminals(plan, block.ref)
                visible_count = len(definition.original.exports)
                if (
                    body.terminals != projection_ports
                    or len(projection_ports) < visible_count
                    or any(
                        port.canonical is not export
                        for port, export in zip(
                            projection_ports[:visible_count],
                            definition.original.exports,
                            strict=True,
                        )
                    )
                    or len(body.columns) != len(projection_ports)
                ):
                    return False
                helpers = projection_ports[visible_count:]
            elif body.terminals != (
                definition.terminals if kind == "projection" else block_exports
            ):
                return False
            for ordinal, column in enumerate(body.columns):
                if ordinal >= len(terminals) and helpers:
                    helper = helpers[ordinal - len(terminals)]
                    if body.final or not _verify_helper_carry(
                        column, ordinal, helper, columns
                    ):
                        return False
                    symbols.append(column.symbol)
                    continue
                export = terminals[ordinal]
                label = export.identity.name if body.final else f"c{ordinal}"
                if (
                    column.ordinal != ordinal
                    or column.export is not export
                    or column.label != label
                    or column.symbol.position != ordinal + 1
                    or column.symbol.binding is not export.ref
                    or column.symbol.name != label
                    or not identifier_valid(label, request.family, label=body.final)
                ):
                    return False
                symbols.append(column.symbol)
                if ordinal < carries:
                    if (
                        type(column) is not RowCarryColumn
                        or column.input_port is not block.inputs[ordinal]
                        or not _same_read(column.read, columns[block.inputs[ordinal]])
                        or export.source is not block.inputs[ordinal]
                        or not identifier_valid(column.read.name, request.family)
                    ):
                        return False
                    continue
                item = items[ordinal - carries]
                if kind == "window":
                    if not _verify_window_column(
                        request,
                        column,
                        item,
                        export,
                        columns,
                        body.window.definitions if body.window is not None else (),
                        state,
                    ):
                        return False
                    continue
                if type(item) is grouping.plan_projection_type():
                    if (
                        type(column) is not grouping.AggregateProjectionColumn
                        or column.projection is not item
                        or column.input_port is not item.input
                        or not _same_read(column.read, columns[item.input])
                        or stage is None
                        or item.aggregation is not stage.ref
                        or item.block is not block.ref
                        or item.export is not export.ref
                    ):
                        return False
                    continue
                if type(item) is windowing.plan_projection_type():
                    if (
                        type(column) is not windowing.WindowProjectionColumn
                        or column.projection is not item
                        or column.input_port is not item.input
                        or not _same_read(column.read, columns[item.input])
                        or column.read.window is None
                        or item.block is not block.ref
                        or item.export is not export.ref
                    ):
                        return False
                    # The window stage already counted this result; carrying it
                    # into the visible projection introduces no new node.
                    continue
                if (
                    type(column) is not RowValueColumn
                    or column.site is not item.site
                    or column.expression is not item.expression
                    or (
                        column.projection is not item
                        if kind == "projection"
                        else column.projection is not None
                    )
                ):
                    return False
                if kind == "let" and export.source is not item.expression:
                    return False
                _verify_row_value(
                    request,
                    column.value,
                    item.expression,
                    columns,
                    children,
                    state,
                    reference_type=row.ProjectSQLJoinedReference
                    if joined_definition
                    else row.ProjectSQLReference,
                )
                state["nodes"] += 1
            if body.predicate is not None:
                if kind not in {"where", "satisfying", "qualify"}:
                    return False
                item = filters[block.ref]
                if (
                    body.predicate.original is not item
                    or body.predicate.expression is not item.predicate
                ):
                    return False
                realization = _verify_row_value(
                    request,
                    body.predicate.value,
                    item.predicate,
                    columns,
                    children,
                    state,
                    reference_type=grouping.ProjectSQLResultReference
                    if kind == "satisfying"
                    else row.ProjectSQLJoinedReference
                    if joined_definition
                    else row.ProjectSQLReference,
                )
                effects = (
                    plan_aggregation.satisfying_effects(
                        stages[definition.original.ref].authority
                    )
                    if kind == "satisfying"
                    else None
                )
                expected_effects = (
                    (("true", True), ("false", False), ("unknown", False))
                    if effects is None
                    else tuple(
                        (effect.truth.value, effect.retain_row) for effect in effects
                    )
                )
                if (
                    realization.tag != "Bool"
                    or tuple(
                        (effect.truth.value, effect.retain_row)
                        for effect in item.retention_effects
                    )
                    != expected_effects
                ):
                    return False
            elif kind in {"where", "satisfying", "qualify"}:
                return False
            _verify_body_scope(body, position, state)
            if kind == "projection":
                produced[definition.original.ref] = body
        if (
            len({id(s) for s in symbols}) != len(symbols)
            or len(state["expressions"]) != len(plan.expressions)
            or {id(e) for e in state["expressions"]}
            != {id(e) for e in plan.expressions}
            or request.verification.envelope is not plan.fixed_envelope
            or request.verification.literal_policy is not plan.literal_policy
        ):
            return False
        limits = resource_limits(request)
        bodies = query.bodies
        nodes = (
            state["nodes"]
            + 3 * len(bodies)
            + 2 * sum(len(b.columns) for b in bodies)
            + sum(2 + len(b.columns) for b in bodies if not b.final)
        )
        return nodes == query.nodes and nodes <= limits["nodes"]
    except (AttributeError, TypeError, ValueError, IndexError, KeyError):
        return False


def _row_reads(request, scan, block):
    """Independently rebuild each scan column; the builder's own walk is not reused."""
    reads = []
    for position in range(len(block.inputs)):
        if type(scan) is RowScan:
            link = scan.binding.bindings[position]
            matches = tuple(
                field
                for field in scan.realization.fields
                if field.field is link.canonical.field
            )
            if len(matches) != 1 or link.terminal is not link.canonical:
                return [None]
            realization = rows.field_realization(matches[0])
            if realization is None:
                return [None]
            reads.append(
                rows.StageColumn(
                    position,
                    matches[0].column,
                    link.canonical.ref,
                    realization,
                    field=matches[0],
                    source_port=link.canonical.ref,
                )
            )
            continue
        if type(scan) is RowNamedUse:
            column = scan.body.columns[position].column
            if column.terminal is not scan.binding.bindings[position].terminal.ref:
                return [None]
            reads.append(replace(column, position=position, name=f"c{position}"))
            continue
        if type(scan) is RowJoinUse:
            reference = scan.tail.ports[position]
            matches = tuple(
                item for item in scan.body.columns if item.port.ref is reference
            )
            if len(matches) != 1:
                return [None]
            reads.append(
                replace(matches[0].column, position=position, name=matches[0].label)
            )
            continue
        assert type(scan) is RowStageUse
        reads.append(
            replace(
                scan.body.columns[position].column,
                position=position,
                name=f"c{position}",
            )
        )
    return reads


def verify_row_bytes(query, rendered):
    """Independently re-derive every token, range and enclosing expression span."""
    try:
        request = query.request
        if (
            type(rendered) is not RenderedSQL
            or rendered.ast is not query
            or type(rendered.sql) is not bytes
            or type(rendered.events) is not tuple
            or type(rendered.expression_ranges) is not tuple
        ):
            return False
        data = rendered.sql
        data.decode("utf-8")
        if len(data) > resource_limits(request)["sql_bytes"]:
            return False
        events = iter(rendered.events)
        subjects = request.source_map.source_map.indexes.subjects
        quote = '"' if request.family == "postgres" else "`"
        spans = []
        offset = 0

        def take(kind, role, subject, expected, *, identifier=False):
            nonlocal offset
            event = next(events)
            if (
                type(event) is not RenderingEvent
                or (event.kind, event.role) != (kind, role)
                or event.subject is not subject
                or type(event.start) is not int
                or type(event.end) is not int
                or event.start != offset
                or not event.start < event.end <= len(data)
                or not _same(
                    event.origins, getattr(subjects.get(subject), "origins", ())
                )
            ):
                raise ValueError("token range or ownership")
            token = data[event.start : event.end].decode("utf-8")
            if identifier:
                if not token.startswith(quote) or not token.endswith(quote):
                    raise ValueError("quoting")
                inner, index, decoded = token[1:-1], 0, []
                while index < len(inner):
                    char = inner[index]
                    if char == quote:
                        if index + 1 >= len(inner) or inner[index + 1] != quote:
                            raise ValueError("undoubled identifier quote")
                        index += 1
                    decoded.append(char)
                    index += 1
                if "".join(decoded) != expected:
                    raise ValueError("identifier binding")
            elif token != expected:
                raise ValueError("SQL token")
            offset = event.end
            return event

        def scalar(value, alias):
            start = offset
            if type(value) is rows.SQLStageReference:
                reference = value.original.ref
                take(
                    "identifier",
                    "value_scope",
                    value.port,
                    alias if value.scope is None else value.scope.name,
                    identifier=True,
                )
                take("syntax", "value_qualifier", reference, ".")
                take(
                    "identifier",
                    "value_column",
                    value.column.terminal,
                    value.column.name,
                    identifier=True,
                )
                spans.append(("reference", reference, start, offset))
                return
            if type(value) is not rows.SQLOperation:
                constant(value)
                return
            reference = value.original.ref
            if value.kind == "sign":
                operator = value.original.expression.operator
                if operator not in {"+", "-"}:
                    raise ValueError("unary operator")
                take("syntax", "unary_open", reference, "(" + operator)
                scalar(value.operands[0], alias)
                take("syntax", "unary_close", reference, ")")
                spans.append(("unary", reference, start, offset))
                return
            if value.kind == "null_test":
                take("syntax", "is_null_open", reference, "(")
                scalar(value.operands[0], alias)
                take(
                    "syntax",
                    "is_null_test",
                    reference,
                    " IS NOT NULL" if value.original.expression.negated else " IS NULL",
                )
                take("syntax", "is_null_close", reference, ")")
                spans.append(("is_null", reference, start, offset))
                return
            opening, operator, closing, role = OPERATORS[value.kind]
            take("syntax", opening, reference, "(")
            scalar(value.operands[0], alias)
            take("syntax", operator, reference, operator_token(value))
            scalar(value.operands[1], alias)
            take("syntax", closing, reference, ")")
            spans.append((role, reference, start, offset))

        def constant(value):
            nodes = parameters.value_nodes(value)
            opened = []
            for node in nodes[:-1]:
                opened.append((node, offset))
                if type(node) is parameters.SQLUnary:
                    take(
                        "syntax",
                        "unary_open",
                        node.original.ref,
                        "(" + node.original.expression.operator,
                    )
                else:
                    take("syntax", "anchor_open", node.original.ref, "CAST(")
            leaf = nodes[-1]
            tag = parameters.tag_of(leaf.original)
            if type(leaf) is parameters.SQLParameter:
                take(
                    "parameter",
                    tag,
                    leaf.site.ref,
                    "$" + str(leaf.use.server_index)
                    if request.family == "postgres"
                    else "?",
                )
            else:
                take(
                    "literal",
                    tag,
                    leaf.site.ref,
                    parameters.literal_token(leaf, request.family),
                )
            for node, start in reversed(opened):
                unary = type(node) is parameters.SQLUnary
                take(
                    "syntax",
                    "unary_close" if unary else "anchor_close",
                    node.original.ref,
                    ")" if unary else parameters.anchor_suffix(node.physical_type),
                )
                spans.append(
                    ("unary" if unary else "anchor", node.original.ref, start, offset)
                )

        def select(body):
            scan = body.scan
            alias = scan.symbol.name
            take("syntax", "select", body.block.ref, "SELECT ")
            for position, column in enumerate(body.columns):
                if position:
                    take("syntax", "separator", column.export.ref, ", ")
                carrier = {
                    RowCarryColumn: ("carry_scope", "carry_qualifier", "carry_column"),
                    grouping.AggregateKeyColumn: (
                        "group_key_scope",
                        "group_key_qualifier",
                        "group_key_column",
                    ),
                    grouping.AggregateProjectionColumn: (
                        "result_scope",
                        "result_qualifier",
                        "result_column",
                    ),
                    windowing.WindowProjectionColumn: (
                        "window_result_scope",
                        "window_result_qualifier",
                        "window_result_column",
                    ),
                }.get(type(column))
                if carrier is not None:
                    take(
                        "identifier",
                        carrier[0],
                        column.input_port,
                        alias,
                        identifier=True,
                    )
                    take("syntax", carrier[1], column.export.ref, ".")
                    take(
                        "identifier",
                        carrier[2],
                        column.read.terminal,
                        column.read.name,
                        identifier=True,
                    )
                elif type(column) is grouping.AggregateValueColumn:
                    aggregate_value(column, alias)
                elif type(column) is windowing.WindowColumn:
                    window_value(column, alias)
                else:
                    scalar(column.value, alias)
                take("syntax", "alias", column.export.ref, " AS ")
                take(
                    "identifier",
                    "label",
                    column.export.ref,
                    column.label,
                    identifier=True,
                )
            if type(scan) is RowScan:
                take("syntax", "from", scan.source.ref, " FROM ")
                take(
                    "identifier",
                    "namespace",
                    scan.source.ref,
                    scan.realization.namespace,
                    identifier=True,
                )
                take("syntax", "qualifier", scan.source.ref, ".")
                take(
                    "identifier",
                    "relation",
                    scan.source.ref,
                    scan.realization.name,
                    identifier=True,
                )
                take("syntax", "alias", scan.use.ref, " AS ")
                take(
                    "identifier", "relation_scope", scan.use.ref, alias, identifier=True
                )
            elif type(scan) is RowNamedUse:
                reference = scan.body.block.ref
                take("syntax", "from", reference, " FROM ")
                take(
                    "identifier",
                    "cte_reference",
                    reference,
                    scan.body.symbol.name,
                    identifier=True,
                )
                take("syntax", "alias", scan.use.ref, " AS ")
                take(
                    "identifier", "relation_scope", scan.use.ref, alias, identifier=True
                )
            elif type(scan) is RowJoinUse:
                reference = scan.body.join.ref
                take("syntax", "from", reference, " FROM ")
                take(
                    "identifier",
                    "join_reference",
                    reference,
                    scan.body.symbol.name,
                    identifier=True,
                )
                take("syntax", "alias", scan.tail.ref, " AS ")
                take("identifier", "join_scope", scan.tail.ref, alias, identifier=True)
            else:
                if type(scan) is not RowStageUse:
                    raise ValueError("unknown SQL relation")
                reference = scan.body.block.ref
                take("syntax", "from", reference, " FROM ")
                take(
                    "identifier",
                    "stage_reference",
                    reference,
                    scan.body.symbol.name,
                    identifier=True,
                )
                take("syntax", "alias", scan.block.ref, " AS ")
                take(
                    "identifier", "stage_scope", scan.block.ref, alias, identifier=True
                )
            stage = body.aggregation
            if stage is not None and stage.keys:
                take("syntax", "group_by", stage.aggregation.ref, " GROUP BY ")
                for position, column in enumerate(stage.keys):
                    if position:
                        take("syntax", "group_separator", column.key.ref, ", ")
                    start = offset
                    take(
                        "identifier",
                        "grouping_scope",
                        column.input_port,
                        alias,
                        identifier=True,
                    )
                    take("syntax", "grouping_qualifier", column.key.ref, ".")
                    take(
                        "identifier",
                        "grouping_column",
                        column.read.terminal,
                        column.read.name,
                        identifier=True,
                    )
                    spans.append(("grouping", column.key.ref, start, offset))
            elif stage is not None and body.block.kind.value != "aggregate":
                raise ValueError("grouping outside its aggregation stage")
            window_clause(body.window, alias)
            if body.predicate is not None:
                satisfying = body.block.kind.value == "satisfying"
                take(
                    "syntax",
                    "satisfying" if satisfying else "where",
                    body.predicate.original.ref,
                    " WHERE ",
                )
                scalar(body.predicate.value, alias)

        def aggregate_value(column, alias):
            reference = column.aggregate.ref
            start = offset
            take("syntax", "aggregate_open", reference, column.spelling + "(")
            if column.argument is None:
                take("syntax", "aggregate_row_count", reference, "*")
            else:
                if column.distinct:
                    take("syntax", "aggregate_distinct", reference, "DISTINCT ")
                scalar(column.argument, alias)
            take("syntax", "aggregate_close", reference, ")")
            spans.append(("aggregate", reference, start, offset))

        def window_specification(specification, reference, alias):
            """The exact OVER body, shared by an inline use and a definition."""
            if specification.partitions:
                take("syntax", "window_partition", reference, "PARTITION BY ")
                for position, (_binding, read) in enumerate(specification.partitions):
                    if position:
                        take("syntax", "window_partition_separator", reference, ", ")
                    take(
                        "identifier",
                        "window_partition_scope",
                        read.terminal,
                        alias,
                        identifier=True,
                    )
                    take("syntax", "window_partition_qualifier", reference, ".")
                    take(
                        "identifier",
                        "window_partition_column",
                        read.terminal,
                        read.name,
                        identifier=True,
                    )
            if specification.orders:
                if specification.partitions:
                    take("syntax", "window_spec_separator", reference, " ")
                take("syntax", "window_order", reference, "ORDER BY ")
                for item in specification.orders:
                    if item.position:
                        take("syntax", "window_order_separator", reference, ", ")
                    take(
                        "identifier",
                        "window_order_scope",
                        item.read.terminal,
                        alias,
                        identifier=True,
                    )
                    take("syntax", "window_order_qualifier", reference, ".")
                    take(
                        "identifier",
                        "window_order_column",
                        item.read.terminal,
                        item.read.name,
                        identifier=True,
                    )
                    take(
                        "syntax",
                        "window_order_direction",
                        reference,
                        " ASC" if item.direction == "asc" else " DESC",
                    )
            frame = specification.frame
            if frame is not None:
                if specification.partitions or specification.orders:
                    take("syntax", "window_frame_separator", reference, " ")
                take(
                    "syntax",
                    "window_frame_unit",
                    reference,
                    windowing.UNIT_SPELLING[frame.unit] + " BETWEEN ",
                )
                take("syntax", "window_frame_start", reference, frame.start[1])
                take("syntax", "window_frame_and", reference, " AND ")
                take("syntax", "window_frame_end", reference, frame.end[1])
                spelling = windowing.EXCLUSION_SPELLING.get(frame.exclusion)
                if spelling is not None:
                    take("syntax", "window_frame_exclusion", reference, " " + spelling)

        def window_clause(stage, alias):
            """Re-derive the generated WINDOW clause, definition by definition."""
            if stage is None or not stage.definitions:
                return
            take("syntax", "window_clause", stage.ref, " WINDOW ")
            for definition in stage.definitions:
                if definition.index:
                    take("syntax", "window_clause_separator", stage.ref, ", ")
                reference = definition.symbol.binding
                take(
                    "identifier",
                    "window_definition",
                    reference,
                    definition.symbol.name,
                    identifier=True,
                )
                take("syntax", "window_definition_as", reference, " AS ")
                start = offset
                take("syntax", "window_spec_open", reference, "(")
                window_specification(definition.specification, reference, alias)
                take("syntax", "window_spec_close", reference, ")")
                spans.append(("window_specification", reference, start, offset))

        def window_value(column, alias):
            """Re-derive one window occurrence's exact bytes from its own plan."""
            reference = column.window.ref
            start = offset
            take(
                "syntax",
                "window_open",
                reference,
                windowing.SPELLING[column.function] + "(",
            )
            for argument in column.arguments:
                if argument.position:
                    take("syntax", "window_argument_separator", reference, ", ")
                if argument.read is not None:
                    take(
                        "identifier",
                        "window_argument_scope",
                        argument.read.terminal,
                        alias,
                        identifier=True,
                    )
                    take("syntax", "window_argument_qualifier", reference, ".")
                    take(
                        "identifier",
                        "window_argument_column",
                        argument.read.terminal,
                        argument.read.name,
                        identifier=True,
                    )
                else:
                    take(
                        "literal",
                        "window_argument_literal",
                        reference,
                        argument.literal,
                    )
            take("syntax", "window_close", reference, ")")
            take("syntax", "window_over", reference, " OVER ")
            specification = column.specification
            if specification.symbol is not None:
                take(
                    "identifier",
                    "window_reference",
                    reference,
                    specification.symbol.name,
                    identifier=True,
                )
                spans.append(("window", reference, start, offset))
                return
            inner = offset
            take("syntax", "window_spec_open", reference, "(")
            window_specification(specification, reference, alias)
            take("syntax", "window_spec_close", reference, ")")
            spans.append(("window_specification", reference, inner, offset))
            spans.append(("window", reference, start, offset))

        def result_select(body):
            scan = body.scan
            alias = scan.symbol.name
            reference = body.block.ref
            take("syntax", "select", reference, "SELECT ")
            if body.distinct is not None:
                take("syntax", "distinct", body.distinct.distinct.ref, "DISTINCT ")
            for position, column in enumerate(body.columns):
                if position:
                    take("syntax", "separator", column.export.ref, ", ")
                take(
                    "identifier",
                    "result_carry_scope",
                    column.projection_port.ref,
                    alias,
                    identifier=True,
                )
                take("syntax", "result_carry_qualifier", column.export.ref, ".")
                take(
                    "identifier",
                    "result_carry_column",
                    column.read.terminal,
                    column.read.name,
                    identifier=True,
                )
                take("syntax", "alias", column.export.ref, " AS ")
                take(
                    "identifier",
                    "label",
                    column.export.ref,
                    column.label,
                    identifier=True,
                )
            take("syntax", "from", scan.body.block.ref, " FROM ")
            take(
                "identifier",
                "stage_reference",
                scan.body.block.ref,
                scan.body.symbol.name,
                identifier=True,
            )
            take("syntax", "alias", scan.boundary.ref, " AS ")
            take(
                "identifier", "result_scope", scan.boundary.ref, alias, identifier=True
            )
            if body.order is not None:
                take("syntax", "order_by", body.order.order.ref, " ORDER BY ")
                for item in body.order.items:
                    reference = item.item.ref
                    if item.position:
                        take("syntax", "order_separator", reference, ", ")
                    start = offset
                    # Every key is a quoted carried column of the stage alias:
                    # a bare ordinal or an output label cannot pass here.
                    take(
                        "identifier",
                        "order_scope",
                        item.port.ref,
                        alias,
                        identifier=True,
                    )
                    take("syntax", "order_qualifier", reference, ".")
                    take(
                        "identifier",
                        "order_column",
                        item.read.terminal,
                        item.read.name,
                        identifier=True,
                    )
                    if item.nulls is not None:
                        raise ValueError("NULL posture spelling")
                    take(
                        "syntax",
                        "order_direction",
                        reference,
                        {"asc": " ASC", "desc": " DESC"}[item.direction],
                    )
                    spans.append(("order_item", reference, start, offset))
            if body.limit is not None:
                reference = body.limit.limit.ref
                take("syntax", "limit", reference, " LIMIT ")
                value = body.limit.limit.value
                if type(value) is not int or isinstance(value, bool) or value < 0:
                    raise ValueError("static limit value")
                event = take("literal", "limit_value", reference, str(value))
                token = data[event.start : event.end].decode("utf-8")
                if (
                    re.fullmatch(r"0|[1-9][0-9]*", token) is None
                    or int(token) != value
                    or body.limit.value != value
                ):
                    raise ValueError("static limit spelling")

        def set_operand_select(unit, operand):
            reference = operand.operand.ref
            alias = operand.symbol.name
            take("syntax", "set_operand_open", reference, "(")
            take("syntax", "select", reference, "SELECT ")
            for position, column in enumerate(operand.columns):
                subject = operand.inputs[position].ref
                if position:
                    take("syntax", "separator", subject, ", ")
                take("identifier", "set_input_scope", subject, alias, identifier=True)
                take("syntax", "set_input_qualifier", subject, ".")
                take(
                    "identifier",
                    "set_input_column",
                    column.terminal,
                    column.name,
                    identifier=True,
                )
                take("syntax", "alias", subject, " AS ")
                take(
                    "identifier",
                    "label",
                    unit.columns[position].export.ref,
                    unit.columns[position].label,
                    identifier=True,
                )
            take("syntax", "from", reference, " FROM ")
            producer = operand.producer
            if type(producer) is BoundSource:
                relation = operand.source.ref
                take(
                    "identifier",
                    "set_namespace",
                    relation,
                    producer.namespace,
                    identifier=True,
                )
                take("syntax", "set_qualifier", relation, ".")
                take(
                    "identifier",
                    "set_relation",
                    relation,
                    producer.name,
                    identifier=True,
                )
            else:
                take(
                    "identifier",
                    "set_reference",
                    producer.block.ref,
                    producer.symbol.name,
                    identifier=True,
                )
            take("syntax", "set_alias", reference, " AS ")
            take("identifier", "set_scope", reference, alias, identifier=True)
            take("syntax", "set_operand_close", reference, ")")

        def set_select(unit):
            reference = unit.body.ref
            operator = (
                " "
                + {"union": "UNION", "intersect": "INTERSECT", "except": "EXCEPT"}[
                    unit.kind.value
                ]
                + " "
                + {"all": "ALL", "distinct": "DISTINCT"}[unit.quantifier.value]
                + " "
            )
            count = len(unit.operands)
            if count < 2:
                raise ValueError("set arity")
            for _ in range(count - 2):
                take("syntax", "set_fold_open", reference, "(")
            set_operand_select(unit, unit.operands[0])
            for position, operand in enumerate(unit.operands[1:], start=1):
                take("syntax", "set_operator", reference, operator)
                set_operand_select(unit, operand)
                if position < count - 1:
                    take("syntax", "set_fold_close", reference, ")")

        def join_relation(item):
            reference = item.original.ref
            producer = item.producer
            if type(producer) is BoundSource:
                relation = item.source
                take(
                    "identifier",
                    "join_namespace",
                    relation,
                    producer.namespace,
                    identifier=True,
                )
                take("syntax", "join_qualifier", relation, ".")
                take(
                    "identifier",
                    "join_relation",
                    relation,
                    producer.name,
                    identifier=True,
                )
            else:
                take(
                    "identifier",
                    "join_reference",
                    reference,
                    producer.symbol.name,
                    identifier=True,
                )
            take("syntax", "join_alias", reference, " AS ")
            take(
                "identifier",
                "join_scope",
                reference,
                item.symbol.name,
                identifier=True,
            )

        def join_condition(unit):
            written = 0
            for item in unit.equalities:
                reference = item.original.ref
                if written:
                    take("syntax", "equality_separator", reference, " AND ")
                start = offset
                take("syntax", "equality_open", reference, "(")
                take(
                    "identifier",
                    "equality_scope",
                    item.left_port,
                    item.left_scope.name,
                    identifier=True,
                )
                take("syntax", "equality_qualifier", reference, ".")
                take(
                    "identifier",
                    "equality_column",
                    item.left.terminal,
                    item.left.name,
                    identifier=True,
                )
                take("syntax", "equality_operator", reference, " = ")
                take(
                    "identifier",
                    "equality_scope",
                    item.right_port,
                    item.right_scope.name,
                    identifier=True,
                )
                take("syntax", "equality_qualifier", reference, ".")
                take(
                    "identifier",
                    "equality_column",
                    item.right.terminal,
                    item.right.name,
                    identifier=True,
                )
                take("syntax", "equality_close", reference, ")")
                spans.append(("relationship_equality", reference, start, offset))
                written += 1
            if unit.predicate is not None:
                if written:
                    take("syntax", "condition_separator", unit.join.on, " AND ")
                scalar(unit.predicate, "")
                written += 1
            if not written:
                raise ValueError("empty rendered JOIN condition")

        def join_select(unit):
            reference = unit.join.ref
            left, right = unit.inputs
            take("syntax", "select", reference, "SELECT ")
            for position, column in enumerate(unit.columns):
                if position:
                    take("syntax", "separator", column.port.ref, ", ")
                take(
                    "identifier",
                    "join_column_scope",
                    column.match.ref,
                    column.scope.name,
                    identifier=True,
                )
                take("syntax", "join_column_qualifier", column.port.ref, ".")
                take(
                    "identifier",
                    "join_column",
                    column.read.terminal,
                    column.read.name,
                    identifier=True,
                )
                take("syntax", "alias", column.port.ref, " AS ")
                take(
                    "identifier",
                    "label",
                    column.port.ref,
                    column.label,
                    identifier=True,
                )
            take("syntax", "from", reference, " FROM ")
            join_relation(left)
            if unit.membership is None:
                take(
                    "syntax",
                    "join_kind",
                    reference,
                    " " + joining.NATIVE_KINDS[unit.join.kind] + " ",
                )
                join_relation(right)
                if unit.join.kind is not AuthoredJoinKind.CROSS:
                    take("syntax", "join_on", reference, " ON ")
                    join_condition(unit)
                return
            take(
                "syntax",
                "membership_open",
                reference,
                " WHERE EXISTS ("
                if unit.membership == "exists"
                else " WHERE NOT EXISTS (",
            )
            take("syntax", "membership_select", reference, "SELECT ")
            take("literal", "membership_sentinel", reference, joining.SENTINEL)
            take("syntax", "membership_from", reference, " FROM ")
            join_relation(right)
            take("syntax", "correlation", reference, " WHERE ")
            join_condition(unit)
            take("syntax", "membership_close", reference, ")")

        units = getattr(query, "units", query.bodies)
        if len(units) > 1:
            take("syntax", "with", request.plan.scope, "WITH ")
            for index, unit in enumerate(units[:-1]):
                is_join = type(unit) is joining.JoinBody
                reference = unit.join.ref if is_join else unit.block.ref
                if index:
                    take("syntax", "cte_separator", reference, ", ")
                take(
                    "identifier",
                    "cte_name",
                    reference,
                    unit.symbol.name,
                    identifier=True,
                )
                take("syntax", "cte_columns_open", reference, " (")
                for position, symbol in enumerate(unit.cte_columns):
                    if position:
                        take("syntax", "terminal_separator", symbol.binding, ", ")
                    take(
                        "identifier",
                        "terminal_column",
                        symbol.binding,
                        symbol.name,
                        identifier=True,
                    )
                take("syntax", "cte_body_open", reference, ") AS (")
                if is_join:
                    join_select(unit)
                elif type(unit) is resulting.RowResultBody:
                    result_select(unit)
                elif type(unit) is setting.SetBody:
                    set_select(unit)
                else:
                    select(unit)
                take("syntax", "cte_body_close", reference, ")")
            take("syntax", "with_body", units[-1].block.ref, " ")
        if type(units[-1]) is resulting.RowResultBody:
            result_select(units[-1])
        elif type(units[-1]) is setting.SetBody:
            set_select(units[-1])
        else:
            select(units[-1])
        if (
            next(events, None) is not None
            or offset != len(data)
            or len(rendered.expression_ranges) != len(spans)
        ):
            return False
        for event, (role, subject, start, end) in zip(
            rendered.expression_ranges, spans, strict=True
        ):
            if (
                type(event) is not RenderingEvent
                or event.kind != "expression_range"
                or event.role != role
                or event.subject is not subject
                or (event.start, event.end) != (start, end)
                or not _same(
                    event.origins, getattr(subjects.get(subject), "origins", ())
                )
            ):
                return False
        return True
    except (
        AttributeError,
        TypeError,
        ValueError,
        IndexError,
        KeyError,
        StopIteration,
        UnicodeError,
    ):
        return False


def verify_row_requirements(request, query, original, generated):
    """Rebuild both denominators from the actual bodies, nodes and premise domains."""
    plan = request.plan
    entries = request.report.report.entries
    units = getattr(query, "units", query.bodies)
    generated_scopes = len(units) > 1
    if (
        type(original) is not tuple
        or len(original) != len(plan.demands)
        or len(entries) != len(plan.demands)
    ):
        return False
    for item, entry, demand in zip(original, entries, plan.demands, strict=True):
        rule = (
            rows.demand_rule(plan, entry)
            or joining.demand_rule(plan, entry)
            or grouping.demand_rule(entry)
            or windowing.demand_rule(entry)
            or resulting.demand_rule(entry)
            or setting.demand_rule(entry)
        )
        if rule is None:
            rule = (
                "R04"
                if entry.family.value == "fixed_literal_transport"
                or (
                    entry.family.value == "expression"
                    and type(plan.expressions[entry.subject.position])
                    not in {
                        row.ProjectSQLReference,
                        row.ProjectSQLJoinedReference,
                        row.ProjectSQLMatchReference,
                        grouping.ProjectSQLResultReference,
                        plan_windows.ProjectSQLWindowReference,
                    }
                )
                else "R03"
                if generated_scopes and entry.family.value == "scope"
                else "R01"
                if entry.family.value in {"source_realization", "expression", "scope"}
                else "R02"
            )
        if (
            type(item) is not OriginalRequirement
            or item.entry is not entry
            or entry.demand is not demand
            or item.rule != rule
        ):
            return False
    if type(generated) is not tuple:
        return False
    naming = tuple(
        p
        for p in request.premises
        if p.key == "identifier_case" and p.scope == "statement"
    )
    expected = []

    def node_expectations(value):
        for node in rows.value_nodes(value):
            if type(node) in {rows.SQLStageReference, rows.SQLOperation}:
                kind = rows.requirement_kind(node)
                operands = (
                    ()
                    if type(node) is rows.SQLStageReference
                    else tuple(
                        rows.realization_of(o, request.family) for o in node.operands
                    )
                )
                expected.append(
                    (
                        kind,
                        node.original.ref,
                        rows.REQUIREMENT_RULES[kind],
                        node_premises(request, node.realization, operands, kind),
                    )
                )
                continue
            for leaf in parameters.value_nodes(node):
                kind = (
                    "unary"
                    if type(leaf) is parameters.SQLUnary
                    else "type_anchor"
                    if type(leaf) is parameters.SQLAnchor
                    else "parameter"
                    if type(leaf) is parameters.SQLParameter
                    else "literal"
                )
                expected.append(
                    (
                        kind,
                        leaf.original.ref,
                        "R04",
                        parameters.anchor_premises(
                            request, kind, parameters.tag_of(leaf.original)
                        ),
                    )
                )

    def join_expectations(unit):
        """Independently list what this JOIN occurrence's structure introduces."""
        join = unit.join
        expected.append(("join", join.ref, joining.join_rule(join.kind), naming))
        for item in unit.inputs:
            expected.append(("join_input", item.original.ref, "R07", naming))
            if type(item.producer) is BoundSource:
                expected.append(
                    (
                        "qualified_scan",
                        item,
                        "R01",
                        applicable_premises(request, item.producer.owner),
                    )
                )
                for field in item.producer.fields:
                    expected.append(
                        (
                            "source_representation",
                            field,
                            "R02",
                            applicable_premises(request, item.producer.owner, field),
                        )
                    )
        for item in unit.equalities:
            expected.append(("relationship_equality", item.original.ref, "R07", naming))
        if unit.predicate is not None:
            expected.append(
                (
                    "match_condition",
                    join.on,
                    "R07",
                    node_premises(
                        request,
                        rows.realization_of(unit.predicate, request.family),
                        (),
                        "match_condition",
                    ),
                )
            )
            node_expectations(unit.predicate)
        if join.kind is AuthoredJoinKind.FULL:
            expected.append(("full_condition", join.ref, "R09", naming))
        if unit.membership is not None:
            expected.append(("membership", join.ref, "R11", naming))
            expected.append(("correlation", join.ref, "R11", naming))
            expected.append(("sentinel", unit.sentinel, "R11", naming))
            if type(unit.inputs[1].producer) in {
                resulting.RowResultBody,
                setting.SetBody,
            }:
                expected.append(
                    (
                        "complete_right_terminal",
                        unit.inputs[1].original.ref,
                        "R11",
                        naming,
                    )
                )
        for column in unit.columns:
            expected.append(("join_output", column.port.ref, "R07", naming))
            if column.port.nulling:
                expected.append(("null_extension", column.port.ref, "R08", naming))

    for unit in units[:-1]:
        is_join = type(unit) is joining.JoinBody
        expected.append(
            (
                "cte_definition",
                unit.join.ref if is_join else unit.block.ref,
                "R03",
                naming,
            )
        )
        for symbol in unit.cte_columns:
            expected.append(("terminal_column", symbol.binding, "R03", naming))
    encoding = tuple(
        p
        for p in request.premises
        if p.scope == "statement" and p.key == "client_encoding"
    )

    def result_expectations(unit):
        """Independently list what one result body's own structures introduce."""
        expected.append(("stage_use", unit.scan.body.block.ref, "R03", naming))
        for symbol in unit.scan.body.cte_columns:
            expected.append(("stage_terminal", symbol.binding, "R03", naming))
        if unit.distinct is not None:
            expected.append(
                ("distinct_quotient", unit.distinct.distinct.ref, "R18", ())
            )
            for field, column in zip(unit.distinct.fields, unit.columns, strict=True):
                expected.append(
                    (
                        "quotient_field_comparison",
                        field.ref,
                        "R18",
                        encoding if column.read.realization.tag == "Text" else (),
                    )
                )
        if unit.order is not None:
            expected.append(("relation_ordering", unit.order.order.ref, "R19", ()))
            for item in unit.order.items:
                expected.append(
                    (
                        "order_item",
                        item.item.ref,
                        "R19",
                        encoding if item.read.realization.tag == "Text" else (),
                    )
                )
                if item.read.realization.nullable is not False:
                    expected.append(("order_null_posture", item.item.ref, "R19", ()))
        if unit.limit is not None:
            expected.append(("static_limit", unit.limit.limit.ref, "R21", ()))
        if not unit.final and (unit.order is not None or unit.limit is not None):
            expected.append(("inner_result_boundary", unit.block.ref, "R21", naming))
        for column in unit.columns:
            expected.append(
                ("result_terminal_column", column.output.ref, "R03", naming)
            )
        expected.append(("read_only_select_bytes", unit, "R23", ()))

    def set_expectations(unit):
        """Independently list what one SET unit's own structures introduce."""
        expected.append(("set_operation", unit.body.ref, "R22", naming))
        for operand in unit.operands:
            expected.append(("set_operand", operand.operand.ref, "R22", naming))
            if operand.source is not None:
                expected.append(
                    (
                        "qualified_scan",
                        operand.producer,
                        "R01",
                        applicable_premises(request, operand.producer.owner),
                    )
                )
                for field in operand.producer.fields:
                    expected.append(
                        (
                            "source_representation",
                            field,
                            "R02",
                            applicable_premises(request, operand.producer.owner, field),
                        )
                    )
        for column in unit.columns:
            expected.append(
                (
                    "set_column",
                    column.source.ref,
                    "R22",
                    encoding if column.realization.tag == "Text" else (),
                )
            )
        if unit.body.requires_equivalence:
            expected.append(("set_row_equivalence", unit.body.ref, "R22", ()))
        expected.append(("read_only_select_bytes", unit, "R23", ()))

    for unit in units:
        if type(unit) is joining.JoinBody:
            join_expectations(unit)
            continue
        if type(unit) is setting.SetBody:
            set_expectations(unit)
            continue
        if type(unit) is resulting.RowResultBody:
            result_expectations(unit)
            continue
        body = unit
        scan = body.scan
        if type(scan) is RowScan:
            expected.append(
                (
                    "qualified_scan",
                    scan,
                    "R01",
                    applicable_premises(request, scan.realization.owner),
                )
            )
            for field in scan.realization.fields:
                expected.append(
                    (
                        "source_representation",
                        field,
                        "R02",
                        applicable_premises(request, scan.realization.owner, field),
                    )
                )
        elif type(scan) is RowNamedUse:
            expected.append(("named_use", scan.use.ref, "R03", naming))
            for link in scan.binding.bindings:
                expected.append(
                    ("immediate_terminal", link.terminal.ref, "R03", naming)
                )
        elif type(scan) is RowJoinUse:
            expected.append(("join_use", scan.tail.ref, "R07", naming))
            for symbol in scan.body.cte_columns:
                expected.append(("join_terminal", symbol.binding, "R07", naming))
        else:
            expected.append(("stage_use", scan.block.ref, "R03", naming))
            for symbol in scan.body.cte_columns:
                expected.append(("stage_terminal", symbol.binding, "R03", naming))
        operators = tuple(
            p
            for p in request.premises
            if p.scope == "statement" and p.key == "operator_environment"
        )
        if body.aggregation is not None:
            expected.append(
                ("aggregation", body.aggregation.aggregation.ref, "R12", operators)
            )
        for column in body.columns:
            if type(column) is RowCarryColumn:
                expected.append(("carry_projection", column.export.ref, "R05", ()))
                continue
            if type(column) is grouping.AggregateKeyColumn:
                expected.append(("group_key", column.key.ref, "R12", operators))
                continue
            if type(column) is grouping.AggregateValueColumn:
                expected.append(("aggregate", column.aggregate.ref, "R13", operators))
                if column.argument is not None:
                    node_expectations(column.argument)
                continue
            if type(column) is grouping.AggregateProjectionColumn:
                expected.append(("result_projection", column.projection.ref, "R12", ()))
                continue
            if type(column) is windowing.WindowColumn:
                expected.append(
                    ("window_computation", column.window.ref, "R14", operators)
                )
                expected.append(
                    ("window_specification", column.window.policy, "R15", ())
                )
                for _binding, read in column.specification.partitions:
                    expected.append(
                        ("window_partition_comparison", read.terminal, "R14", ())
                    )
                for item in column.specification.orders:
                    expected.append(
                        ("window_order_comparison", item.read.terminal, "R14", ())
                    )
                continue
            if type(column) is windowing.WindowProjectionColumn:
                expected.append(
                    ("window_result_projection", column.projection.ref, "R17", ())
                )
                continue
            expected.append(("computed_projection", column.export.ref, "R05", ()))
            node_expectations(column.value)
        if body.predicate is not None:
            satisfying = body.block.kind.value == "satisfying"
            expected.append(
                (
                    "satisfying_root" if satisfying else "predicate_root",
                    body.predicate.original.ref,
                    "R12" if satisfying else "R06",
                    operators,
                )
            )
            node_expectations(body.predicate.value)
        expected.append(("read_only_select_bytes", body, "R23", ()))
    if generated_scopes:
        expected.append(("nonrecursive_with_bytes", query, "R23", ()))
    if len(expected) != len(generated):
        return False
    for requirement, (kind, subject, rule, premises) in zip(
        generated, expected, strict=True
    ):
        if (
            type(requirement) is not GeneratedRequirement
            or requirement.subject is not subject
            or (requirement.kind, requirement.rule) != (kind, rule)
            or not _same(requirement.premises, premises)
        ):
            return False
    return True


def verify_row_parameters(artifact):
    plan, query = artifact.request.plan, artifact.ast
    if not _same(artifact.fixed_values, plan.fixed_envelope.values):
        return False
    leaves = row_parameter_leaves(query)
    tokens = [event for event in artifact.rendered.events if event.kind == "parameter"]
    if (
        type(artifact.parameter_uses) is not tuple
        or len(artifact.parameter_uses) != len(leaves)
        or len(tokens) != len(leaves)
        or len(leaves) > resource_limits(artifact.request)["parameters"]
    ):
        return False
    seen = {}
    for ordinal, (use, leaf, token) in enumerate(
        zip(artifact.parameter_uses, leaves, tokens, strict=True)
    ):
        slot = leaf.original.use.slot
        if slot not in seen:
            seen[slot] = (len(seen) + 1, use.physical_type)
        index, physical = seen[slot]
        if (
            type(use) is not parameters.NativeUse
            or use is not leaf.use
            or use.original is not leaf.original
            or use.slot is not slot
            or type(use.ordinal) is not int
            or use.ordinal != ordinal
            or type(use.server_index) is not int
            or use.server_index
            != (ordinal + 1 if artifact.request.family == "mysql" else index)
            or use.physical_type != physical
            or token.subject is not leaf.site.ref
        ):
            return False
    return len(seen) == len(plan.literal_slots) and all(
        slot in seen for slot in plan.literal_slots
    )
