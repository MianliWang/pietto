"""Result-boundary SQL construction: visible DISTINCT, relation ORDER, static LIMIT.

A definition whose plan carries result boundaries ends in one further generated
SELECT, the result body. It reads the definition's own visible projection as a
closed stage and realizes DISTINCT, ORDER BY and LIMIT in that one SELECT, whose
SQL evaluation order (DISTINCT, then ORDER, then LIMIT) is the retained plan order
`visible projection -> DISTINCT -> relation ORDER -> LIMIT -> terminal`. The
result body is the definition's terminal: a named use, a JOIN input or a
SEMI/ANTI right side binds its post-LIMIT output ports, never the projection.

This module owns the result-specific construction only. The renderer turns the
returned nodes into bytes and the independent verifier re-derives them from the
retained plan, so no SQL text is authority here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from pietto._project import project_sql_plan_results as plan_results
from pietto._project import project_sql_emission_rows as rows
from pietto._project.project_final_outputs import ProjectRelationOrdering
from pietto._project.project_ir_properties import ProjectIRProvidedRelationOrdering
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRReboundExistingOutput,
    ProjectIRReusedEffectiveOutput,
)

__all__: tuple[str, ...] = ()

# The retained ORDER carrier routes of R03/R19: each keeps its own input image.
ORDINARY = "ordinary"
REBOUND = "rebound"
COMPLETED = "completed"
CARRIERS = frozenset({ORDINARY, REBOUND, COMPLETED})
DIRECTIONS = {"asc": "ASC", "desc": "DESC"}
# The language authors no NULLS FIRST/LAST and the retained policy requires no
# posture, so every emitted key keeps the target's own native NULL order. No
# spelling and no discriminator helper is generated for it.
NULL_POSTURE = "target_defined"
# R19 orders the same exact comparison domain the window stage admits; a Float
# key stays outside relation ORDER exactly as it stays outside window ORDER.
ORDER_TAGS = frozenset({"Int", "Bool", "Text", "Decimal"})
# The published rule each retained result-boundary demand belongs to, by
# subject kind. A projection-role result port and a canonical result export
# exist for every definition and keep their prior generic attribution.
DEMAND_RULES = {
    "result_boundary": "R03",
    "distinct": "R18",
    "quotient_field": "R18",
    "relation_order": "R19",
    "order_item": "R19",
    "order_expression": "R19",
    "order_use": "R19",
    "hidden_order_requirement": "R20",
    "result_limit": "R21",
}
KINDS = plan_results.ProjectSQLResultKind
ROLES = plan_results.ProjectSQLResultPortRole


def _scalar(value: Any) -> Any:
    return value if type(value) in {int, str, bool, type(None)} else "..."


def _count(value: Any) -> int | str:
    return len(value) if type(value) is tuple else "?"


@dataclass(frozen=True, slots=True, eq=False)
class RowResultUse:
    """The result body's scan: this definition's own closed projection stage."""

    body: Any
    boundary: Any
    symbol: Any

    def __repr__(self) -> str:
        return (
            f"RowResultUse(symbol={_scalar(self.symbol.name)}, body=..., boundary=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class ResultStage:
    """One boundary's exact input and output image of one visible column."""

    boundary: Any
    input_port: Any
    output_port: Any
    quotient_field: Any = None


@dataclass(frozen=True, slots=True, eq=False)
class ResultColumn:
    """One visible output carried through every result boundary to its terminal."""

    ordinal: int
    export: Any
    projection_port: Any
    read: rows.StageColumn
    output: Any
    stages: tuple[ResultStage, ...]
    symbol: Any
    label: str
    column: rows.StageColumn

    def __repr__(self) -> str:
        return (
            f"ResultColumn(ordinal={_scalar(self.ordinal)}, "
            f"label={_scalar(self.label)}, stages=<{_count(self.stages)}>, "
            "read=..., column=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class ResultDistinct:
    """The native DISTINCT over exactly the visible positional tuple."""

    distinct: Any
    boundary: Any
    fields: tuple[Any, ...]

    def __repr__(self) -> str:
        return f"ResultDistinct(fields=<{_count(self.fields)}>, distinct=...)"


@dataclass(frozen=True, slots=True, eq=False)
class ResultOrderItem:
    """One relation ORDER key bound to its exact established value port."""

    position: int
    item: Any
    expression: Any
    use: Any
    port: Any
    read: rows.StageColumn
    direction: str
    nulls: str | None
    carrier: str

    def __repr__(self) -> str:
        return (
            f"ResultOrderItem(position={_scalar(self.position)}, "
            f"direction={_scalar(self.direction)}, nulls={_scalar(self.nulls)}, "
            f"carrier={_scalar(self.carrier)}, read=..., port=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class ResultOrder:
    """The final relation ORDER of one definition, from one retained carrier."""

    order: Any
    boundary: Any
    carrier: str
    items: tuple[ResultOrderItem, ...]

    def __repr__(self) -> str:
        return (
            f"ResultOrder(carrier={_scalar(self.carrier)}, "
            f"items=<{_count(self.items)}>, order=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class ResultLimit:
    """The retained static LIMIT at this definition's result boundary."""

    limit: Any
    boundary: Any
    value: int

    def __repr__(self) -> str:
        return f"ResultLimit(value={_scalar(self.value)}, limit=...)"


@dataclass(frozen=True, slots=True, eq=False)
class RowResultBody:
    """One generated SELECT realizing every result boundary of one definition."""

    definition: Any
    boundaries: tuple[Any, ...]
    index: int
    scan: RowResultUse
    columns: tuple[ResultColumn, ...]
    terminals: tuple[Any, ...]
    distinct: ResultDistinct | None
    order: ResultOrder | None
    limit: ResultLimit | None
    final: bool
    symbol: Any
    cte_columns: tuple[Any, ...]
    predicate: None = None
    aggregation: None = None
    window: None = None

    @property
    def block(self) -> Any:
        """The first boundary names this body wherever a stage block would."""

        return self.boundaries[0]

    def __repr__(self) -> str:
        return (
            f"RowResultBody(index={_scalar(self.index)}, final={_scalar(self.final)}, "
            f"boundaries=<{_count(self.boundaries)}>, columns=<{_count(self.columns)}>, "
            f"distinct={'None' if self.distinct is None else '...'}, "
            f"order={'None' if self.order is None else '...'}, "
            f"limit={'None' if self.limit is None else '...'})"
        )


def demand_rule(entry) -> str | None:
    """The published rule one retained result demand belongs to."""

    if entry.family.value != "result":
        return None
    return DEMAND_RULES.get(entry.subject.kind.value)


def boundaries_by_definition(plan) -> dict[Any, tuple[Any, ...]]:
    """Every definition's result boundaries in retained order."""

    grouped: dict[Any, list[Any]] = {}
    for boundary in plan.result_boundaries:
        grouped.setdefault(boundary.definition, []).append(boundary)
    return {
        definition: tuple(sorted(items, key=lambda b: b.position))
        for definition, items in grouped.items()
    }


def ports_by_boundary(plan) -> dict[tuple[Any, Any], tuple[Any, ...]]:
    """Result ports grouped by (boundary, role) in retained position order."""

    grouped: dict[tuple[Any, Any], list[Any]] = {}
    for port in plan.result_ports:
        grouped.setdefault((port.boundary, port.role), []).append(port)
    return {
        key: tuple(sorted(items, key=lambda p: p.position))
        for key, items in grouped.items()
    }


def projection_terminals(plan, block_ref) -> tuple[Any, ...]:
    """The PROJECTION-role result ports one visible projection block publishes."""

    return ports_by_boundary(plan).get((block_ref, ROLES.PROJECTION), ())


def boundaries_admitted(plan) -> bool:
    """Whether every result boundary has the closed chain shape this owner emits."""

    if plan.set_bodies:
        return False
    projections = {
        block.definition: block
        for block in plan.blocks
        if block.kind.value == "projection"
    }
    for definition, boundaries in boundaries_by_definition(plan).items():
        projection = projections.get(definition)
        if projection is None:
            return False
        predecessor = projection.ref
        seen = set()
        for position, boundary in enumerate(boundaries):
            if (
                boundary.position != position
                or boundary.predecessor is not predecessor
                or boundary.kind not in set(KINDS)
                or boundary.kind in seen
            ):
                return False
            seen.add(boundary.kind)
            predecessor = boundary.ref
    return True


def node_count(body: RowResultBody) -> int:
    """The bounded node contribution of one result body's own structures."""

    return (
        (0 if body.distinct is None else 1)
        + (0 if body.order is None else len(body.order.items))
        + (0 if body.limit is None else 1)
    )


def order_carrier(entry, boundary, order) -> str | None:
    """Classify the retained ORDER carrier from the entry's own authority.

    An ordinary existing entry keeps its historical fragment property stage,
    whose single provided relation ordering names the authored clause items and
    the entry's active output. A rebound existing entry keeps one rebuilt result
    property per stage; its provided ordering shares the authored items with the
    active ordering but names the rebuilt stage output rather than the historical
    one. A completed entry carries the ProjectRelationOrdering itself as the
    operator's evidence.
    """

    source = order.source
    if not isinstance(source, ProjectRelationOrdering) or source.inputs is None:
        return None
    properties = boundary.properties
    if isinstance(entry, ProjectIRCompletedQueryBlockOutput):
        if (
            boundary.operator.evidence is source
            and getattr(properties, "ordering", None) is source
        ):
            return COMPLETED
        return None
    active = getattr(entry.active_properties, "ordering", None)
    if (
        type(active) is not ProjectIRProvidedRelationOrdering
        or active.output is not entry.active_output
        or active.items is not source.clause.items
    ):
        return None
    if isinstance(entry, ProjectIRReusedEffectiveOutput):
        if properties is not entry.semantic_entry.fragment.property_stage:
            return None
        # The historical stage provides one ordering per output it orders; the
        # ORDER operator's own output is the carrier this boundary realizes.
        provided = tuple(
            p
            for p in properties.provided
            if type(p) is ProjectIRProvidedRelationOrdering
            and p.output.occurrence.producer is boundary.operator.node
        )
        if len(provided) != 1 or provided[0].items is not source.clause.items:
            return None
        return ORDINARY
    if isinstance(entry, ProjectIRReboundExistingOutput):
        provided = getattr(properties, "ordering", None)
        if (
            type(provided) is not ProjectIRProvidedRelationOrdering
            or provided.items is not source.clause.items
            or provided.output is not properties.relational.output
            or not any(properties is p for p in entry.row_properties)
            or entry.active_output is entry.semantic_entry.output
        ):
            return None
        return REBOUND
    return None


def bound_port(use, inputs):
    """The one input port an ORDER use binds: its lowest-position resolved port.

    Every port a use lists is a value-identical visible copy of the same original
    target, so the first by position is a deterministic choice rather than an
    arbitrary winner. A use without a port is an unrealizable requirement.
    """

    positions = {port.ref: port for port in inputs}
    matches = [positions[ref] for ref in use.ports if ref in positions]
    if len(matches) != len(use.ports) or not matches:
        return None
    return min(matches, key=lambda port: port.position)


def build_result_body(
    request,
    definition,
    boundaries,
    projection,
    *,
    index,
    final,
    symbol,
):
    """Realize one definition's result boundaries as its terminal SELECT."""

    plan = request.plan
    entry = definition.original.entry
    authored = entry.owner.definition
    exports = definition.original.exports
    ports = ports_by_boundary(plan)
    distincts = {d.boundary: d for d in plan.distincts}
    quotient_fields: dict[Any, list[Any]] = {}
    for field in plan.quotient_fields:
        quotient_fields.setdefault(field.distinct, []).append(field)
    orders = {o.boundary: o for o in plan.orders}
    items = {i.ref: i for i in plan.order_items}
    expressions = {e.ref: e for e in plan.order_expressions}
    uses = {u.ref: u for u in plan.order_uses}
    hidden = {h.item: h for h in plan.hidden_order_requirements}
    limits = {value.boundary: value for value in plan.result_limits}
    first = boundaries[0]

    def problem(code, detail, subject, location=None):
        return None, (code, detail, subject, location)

    carried = ports.get((projection.block.ref, ROLES.PROJECTION), ())
    if len(carried) != len(projection.columns) or any(
        column.column.terminal is not port.ref
        for column, port in zip(projection.columns, carried, strict=True)
    ):
        return problem("PIE-B1001", "result_projection_port_drift", first.ref)
    if projection.final or projection.symbol is None:
        return problem("PIE-B1001", "result_projection_not_a_closed_stage", first.ref)
    origin: dict[Any, Any] = {}
    for port, column in zip(carried, projection.columns, strict=True):
        origin[port.ref] = (port, column.column)
    traces: dict[Any, list[ResultStage]] = {
        port.ref: [] for port in carried if port.canonical is not None
    }
    distinct = order = limit = None
    for boundary in boundaries:
        inputs = ports.get((boundary.ref, ROLES.INPUT), ())
        outputs = ports.get((boundary.ref, ROLES.OUTPUT), ())
        if len(inputs) != len(carried) or any(
            port.source is not previous.ref
            or port.canonical is not previous.canonical
            or port.key is not previous.key
            for port, previous in zip(inputs, carried, strict=True)
        ):
            return problem("PIE-B1001", "result_boundary_input_drift", boundary.ref)
        visible = tuple(port for port in inputs if port.canonical is not None)
        if len(outputs) != len(visible) or any(
            port.source is not previous.ref or port.canonical is not previous.canonical
            for port, previous in zip(outputs, visible, strict=True)
        ):
            return problem("PIE-B1001", "result_boundary_output_drift", boundary.ref)
        if tuple(port.canonical for port in visible) != tuple(exports):
            return problem("PIE-B1001", "result_visible_tuple_drift", boundary.ref)
        for port, previous in zip(inputs, carried, strict=True):
            origin[port.ref] = origin[previous.ref]
            if previous.ref in traces:
                traces[port.ref] = traces[previous.ref]
        stage_fields: dict[Any, Any] = {}
        if boundary.kind is KINDS.DISTINCT:
            value = distincts.get(boundary.ref)
            if value is None or distinct is not None:
                return problem(
                    "PIE-B1001", "distinct_boundary_evidence_missing", boundary.ref
                )
            fields = sorted(
                quotient_fields.get(value.ref, ()), key=lambda f: f.position
            )
            if (
                len(visible) != len(inputs)
                or len(fields) != len(inputs)
                or tuple(f.ref for f in fields) != tuple(value.fields)
                or any(
                    f.position != i
                    or f.input is not inputs[i].ref
                    or f.output is not outputs[i].ref
                    or f.canonical is not exports[i]
                    for i, f in enumerate(fields)
                )
            ):
                return problem(
                    "PIE-B1001", "distinct_tuple_includes_hidden_value", boundary.ref
                )
            for field, port in zip(fields, inputs, strict=True):
                location = getattr(field.equivalence.selected.item, "span", None)
                if field.equivalence.reason is not None:
                    return problem(
                        "PIE-B1003",
                        "distinct_field_equivalence_unsupported",
                        field.ref,
                        location,
                    )
                read = origin[port.ref][1]
                if read.realization.tag not in ORDER_TAGS:
                    return problem(
                        "PIE-B1003",
                        "distinct_field_comparison_domain_unsupported",
                        field.ref,
                        location,
                    )
                stage_fields[port.ref] = field
            distinct = ResultDistinct(value, boundary, tuple(fields))
        elif boundary.kind is KINDS.ORDER:
            value = orders.get(boundary.ref)
            if value is None or order is not None:
                return problem(
                    "PIE-B1001", "order_boundary_evidence_missing", boundary.ref
                )
            carrier = order_carrier(entry, boundary, value)
            if carrier is None:
                return problem(
                    "PIE-B1003", "order_carrier_not_recognized", boundary.ref
                )
            realized = []
            for position, item_ref in enumerate(value.items):
                item = items.get(item_ref)
                if (
                    item is None
                    or item.ordering is not value.ref
                    or item.position != position
                ):
                    return problem(
                        "PIE-B1001", "order_item_inventory_drift", boundary.ref
                    )
                location = getattr(item.source.item, "span", None)
                if item.value is not item.expression or item.ref in hidden:
                    return problem(
                        "PIE-B1003",
                        "hidden_strict_fd_order_approved_non_support",
                        item.ref,
                        location,
                    )
                root = expressions.get(item.expression)
                if (
                    root is None
                    or root.item is not item.ref
                    or root.expression is not item.source.expression
                ):
                    return problem(
                        "PIE-B1001",
                        "order_expression_inventory_drift",
                        item.ref,
                        location,
                    )
                if root.use is None or root.operands:
                    return problem(
                        "PIE-B1003",
                        "order_expression_requires_established_port",
                        item.ref,
                        location,
                    )
                use = uses.get(root.use)
                if (
                    use is None
                    or use.item is not item.ref
                    or use.scope is not boundary.ref
                    or use.requirement is not None
                    or use.source.expression is not root.expression
                ):
                    return problem(
                        "PIE-B1001", "order_use_inventory_drift", item.ref, location
                    )
                port = bound_port(use, inputs)
                if port is None:
                    return problem(
                        "PIE-B1001", "order_value_port_missing", item.ref, location
                    )
                read = origin[port.ref][1]
                direction = item.source.direction.value
                if direction not in DIRECTIONS or (
                    item.source.item.direction is not None
                    and item.source.item.direction != direction
                ):
                    return problem(
                        "PIE-B1004",
                        "order_direction_evidence_missing",
                        item.ref,
                        location,
                    )
                if (
                    read.realization.tag not in ORDER_TAGS
                    or rows.value_tag(item.source) != read.realization.tag
                ):
                    return problem(
                        "PIE-B1003",
                        "order_comparison_domain_unsupported",
                        item.ref,
                        location,
                    )
                realized.append(
                    ResultOrderItem(
                        position,
                        item,
                        root,
                        use,
                        port,
                        read,
                        direction,
                        None,
                        carrier,
                    )
                )
            if not realized:
                return problem("PIE-B1001", "order_item_inventory_drift", boundary.ref)
            order = ResultOrder(value, boundary, carrier, tuple(realized))
        else:
            value = limits.get(boundary.ref)
            if value is None or limit is not None:
                return problem(
                    "PIE-B1001", "limit_boundary_evidence_missing", boundary.ref
                )
            if (
                value.clause is not authored.limit_clause
                or value.literal is not value.clause.expression
                or type(value.value) is not int
                or isinstance(value.value, bool)
                or value.value != value.literal.value
                or not 0 <= value.value <= value.maximum
                or value.row_count_upper_bound != value.value
            ):
                return problem(
                    "PIE-B1004", "limit_static_evidence_missing", boundary.ref
                )
            limit = ResultLimit(value, boundary, value.value)
        for port, previous in zip(outputs, visible, strict=True):
            origin[port.ref] = origin[previous.ref]
            trace = traces.get(previous.ref)
            if trace is None:
                return problem("PIE-B1001", "result_visible_tuple_drift", boundary.ref)
            traces[port.ref] = [
                *trace,
                ResultStage(boundary, previous, port, stage_fields.get(previous.ref)),
            ]
        carried = outputs
    if len(carried) != len(exports) or any(
        port.canonical is not export
        for port, export in zip(carried, exports, strict=True)
    ):
        return problem("PIE-B1001", "result_terminal_denominator", first.ref)
    if tuple(carried) != tuple(definition.terminals):
        return problem("PIE-B1001", "result_terminal_drift", first.ref)
    columns = []
    for position, (port, export) in enumerate(zip(carried, exports, strict=True)):
        projection_port, read = origin[port.ref]
        label = export.identity.name if final else f"c{position}"
        columns.append(
            ResultColumn(
                position,
                export,
                projection_port,
                read,
                port,
                tuple(traces[port.ref]),
                symbol(position + 1, export.ref, label),
                label,
                replace(read, position=position, name=label, terminal=port.ref),
            )
        )
    body = RowResultBody(
        definition,
        tuple(boundaries),
        index,
        RowResultUse(projection, first, symbol(0, first.ref, f"t{first.ref.position}")),
        tuple(columns),
        tuple(carried),
        distinct,
        order,
        limit,
        final,
        None if final else symbol(index, first.ref, f"p{index}"),
        ()
        if final
        else tuple(symbol(i, port.ref, f"c{i}") for i, port in enumerate(carried)),
    )
    return body, None


def requirements(request, body: RowResultBody, naming, requirement):
    """Every requirement this result body's own generated structures introduce."""

    encoding = tuple(
        p
        for p in request.premises
        if p.scope == "statement" and p.key == "client_encoding"
    )
    result = []
    if body.distinct is not None:
        result.append(
            requirement("distinct_quotient", body.distinct.distinct.ref, "R18", ())
        )
        for field, column in zip(body.distinct.fields, body.columns, strict=True):
            result.append(
                requirement(
                    "quotient_field_comparison",
                    field.ref,
                    "R18",
                    encoding if column.read.realization.tag == "Text" else (),
                )
            )
    if body.order is not None:
        result.append(requirement("relation_ordering", body.order.order.ref, "R19", ()))
        for item in body.order.items:
            result.append(
                requirement(
                    "order_item",
                    item.item.ref,
                    "R19",
                    encoding if item.read.realization.tag == "Text" else (),
                )
            )
            if item.read.realization.nullable is not False:
                result.append(
                    requirement("order_null_posture", item.item.ref, "R19", ())
                )
    if body.limit is not None:
        result.append(requirement("static_limit", body.limit.limit.ref, "R21", ()))
    if not body.final and (body.order is not None or body.limit is not None):
        result.append(
            requirement("inner_result_boundary", body.block.ref, "R21", naming)
        )
    for column in body.columns:
        result.append(
            requirement("result_terminal_column", column.output.ref, "R03", naming)
        )
    return tuple(result)


def requirement_evidence(query, item) -> list[dict[str, Any]]:
    """Public evidence for one generated result requirement, from its AST node."""

    for body in getattr(query, "units", query.bodies):
        if type(body) is not RowResultBody:
            continue
        if item.kind == "distinct_quotient" and body.distinct is not None:
            if body.distinct.distinct.ref is item.subject:
                return [{"fields": len(body.distinct.fields)}]
        if item.kind in {"order_item", "order_null_posture"} and body.order is not None:
            for entry in body.order.items:
                if entry.item.ref is item.subject:
                    return [
                        {
                            "carrier": entry.carrier,
                            "position": entry.position,
                            "direction": entry.direction,
                            "nulls": NULL_POSTURE,
                            "value_port": {
                                "kind": entry.port.ref.kind.value,
                                "position": entry.port.ref.position,
                            },
                            "expression": {
                                "kind": entry.expression.ref.kind.value,
                                "position": entry.expression.ref.position,
                            },
                        }
                    ]
        if item.kind == "relation_ordering" and body.order is not None:
            if body.order.order.ref is item.subject:
                return [{"carrier": body.order.carrier, "items": len(body.order.items)}]
        if item.kind == "static_limit" and body.limit is not None:
            if body.limit.limit.ref is item.subject:
                return [{"value": body.limit.value}]
    return []
