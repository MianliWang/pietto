"""SET-body SQL construction: six native forms over complete operand terminals.

A SET definition is one generated unit whose operands are wrapper SELECTs over
their producers' complete terminals (a physical scan or the producer CTE), joined
by the spelled `<KIND> <QUANTIFIER>` operator with explicit left-fold grouping.
A nested SET producer is a CTE, never inlined, so SQL precedence can never
re-associate the authored nesting. Output identities belong to the SET owner.

This module owns the SET-specific construction only. The renderer turns the
returned nodes into bytes and the independent verifier re-derives them from the
retained plan, so no SQL text is authority here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from pietto.ast_nodes import SetOperationKind, SetOperationQuantifier
from pietto._project import project_sql_emission_rows as rows
from pietto._project.model import ProjectRowFieldNullability

__all__: tuple[str, ...] = ()

KIND_SPELLING = {
    SetOperationKind.UNION: "UNION",
    SetOperationKind.INTERSECT: "INTERSECT",
    SetOperationKind.EXCEPT: "EXCEPT",
}
QUANTIFIER_SPELLING = {
    SetOperationQuantifier.ALL: "ALL",
    SetOperationQuantifier.DISTINCT: "DISTINCT",
}
# R22: the five equality forms compare V01-V04; UNION ALL additionally transports
# finite Float (V06) without any equality requirement.
EQUIVALENCE_TAGS = frozenset({"Int", "Bool", "Text", "Decimal"})
TRANSPORT_TAGS = EQUIVALENCE_TAGS | {"Float"}
NULLABILITY = {
    ProjectRowFieldNullability.NON_NULL: False,
    ProjectRowFieldNullability.NULLABLE: True,
    ProjectRowFieldNullability.UNKNOWN: "unknown",
}
DEMAND_RULE = "R22"


def _scalar(value: Any) -> Any:
    return value if type(value) in {int, str, bool, type(None)} else "..."


def _count(value: Any) -> int | str:
    return len(value) if type(value) is tuple else "?"


@dataclass(frozen=True, slots=True, eq=False)
class SetOperandBody:
    """One operand: a wrapper SELECT over its producer's complete terminal."""

    position: int
    operand: Any
    use: Any
    producer: Any
    source: Any
    symbol: Any
    columns: tuple[rows.StageColumn, ...]
    inputs: tuple[Any, ...]

    def __repr__(self) -> str:
        return (
            f"SetOperandBody(position={_scalar(self.position)}, "
            f"alias={_scalar(self.symbol.name)}, columns=<{_count(self.columns)}>, "
            "producer=..., operand=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class SetColumn:
    """One SET-owned positional output over every operand's same-position input."""

    ordinal: int
    source: Any
    export: Any
    output: Any
    inputs: tuple[rows.StageColumn, ...]
    realization: rows.Realization
    symbol: Any
    label: str
    column: rows.StageColumn

    def __repr__(self) -> str:
        return (
            f"SetColumn(ordinal={_scalar(self.ordinal)}, label={_scalar(self.label)}, "
            f"inputs=<{_count(self.inputs)}>, source=..., column=...)"
        )


@dataclass(frozen=True, slots=True, eq=False)
class SetBody:
    """One generated SET unit realizing exactly one authored SET body."""

    definition: Any
    body: Any
    index: int
    kind: SetOperationKind
    quantifier: SetOperationQuantifier
    operands: tuple[SetOperandBody, ...]
    columns: tuple[SetColumn, ...]
    terminals: tuple[Any, ...]
    final: bool
    symbol: Any
    cte_columns: tuple[Any, ...]
    predicate: None = None
    aggregation: None = None
    window: None = None

    @property
    def block(self) -> Any:
        """The plan SET body names this unit wherever a stage block would."""

        return self.body

    def __repr__(self) -> str:
        return (
            f"SetBody(index={_scalar(self.index)}, final={_scalar(self.final)}, "
            f"kind={_scalar(self.kind.value)}, "
            f"quantifier={_scalar(self.quantifier.value)}, "
            f"operands=<{_count(self.operands)}>, columns=<{_count(self.columns)}>)"
        )


def operator_spelling(kind, quantifier) -> str:
    return f"{KIND_SPELLING[kind]} {QUANTIFIER_SPELLING[quantifier]}"


def demand_rule(entry) -> str | None:
    """Every retained SET demand belongs to R22."""

    return DEMAND_RULE if entry.family.value == "set" else None


def bodies_by_definition(plan) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for body in plan.set_bodies:
        if body.definition in result:
            return {}
        result[body.definition] = body
    return result


def bodies_admitted(plan) -> bool:
    """Whether every SET body has the closed explicit shape this owner emits."""

    if not plan.set_bodies:
        return True
    operands = {o.ref: o for o in plan.set_operands}
    columns = {c.ref: c for c in plan.set_columns}
    if len(bodies_by_definition(plan)) != len(plan.set_bodies):
        return False
    for body in plan.set_bodies:
        if (
            body.fold != "source_order_left_fold"
            or body.kind not in KIND_SPELLING
            or body.quantifier not in QUANTIFIER_SPELLING
            or len(body.operands) < 2
            or not body.columns
            or any(ref not in operands for ref in body.operands)
            or any(ref not in columns for ref in body.columns)
            or [operands[ref].position for ref in body.operands]
            != list(range(len(body.operands)))
        ):
            return False
    return True


def node_count(unit: SetBody) -> int:
    """The bounded node contribution of one SET unit."""

    return 3 + len(unit.operands) * (2 + len(unit.columns))


def nullability(kind, states):
    """The published operation-specific nullability rule over operand states."""

    if kind is SetOperationKind.EXCEPT:
        return states[0]
    if kind is SetOperationKind.INTERSECT and False in states:
        return False
    if all(state is False for state in states):
        return False
    if "unknown" in states:
        return "unknown"
    return True


def column_realization(kind, quantifier, column, inputs, evidence):
    """One SET output's independently checked physical realization.

    Corresponding operands must carry the same logical tag and the same
    physical representation: an Int of equal width whose exact ranges merge, an
    identical Bool/Text/Decimal/Float storage, identical Text encoding /
    collation / padding premises and identical validated Decimal(p, s). No common
    type is inferred and no cast conceals a mismatch.
    """

    first = inputs[0].realization
    tag = first.tag
    if any(item.realization.tag != tag for item in inputs):
        return None, ("PIE-B1002", "set_column_logical_type_drift")
    allowed = (
        TRANSPORT_TAGS
        if (kind, quantifier) == (SetOperationKind.UNION, SetOperationQuantifier.ALL)
        else EQUIVALENCE_TAGS
    )
    if tag not in allowed:
        return None, ("PIE-B1003", "set_row_equivalence_domain_unsupported")
    storage = first.storage
    domain: dict[str, Any] = dict(first.domain)
    if tag == "Int":
        widths = {
            rows.INT_WIDTHS.get(item.realization.storage["kind"]) for item in inputs
        }
        bounds = [rows.int_bounds(item.realization) for item in inputs]
        if None in widths or len(widths) != 1 or any(b is None for b in bounds):
            return None, ("PIE-B1002", "set_column_physical_representation_mismatch")
        domain = {
            "kind": "int_range",
            "min": str(min(b[0] for b in bounds if b is not None)),
            "max": str(max(b[1] for b in bounds if b is not None)),
        }
    else:
        if any(item.realization.storage != storage for item in inputs):
            return None, ("PIE-B1002", "set_column_physical_representation_mismatch")
        if tag == "Text":
            keys = ("encoding", "collation", "padding")
            if any(
                tuple(item.realization.domain.get(k) for k in keys)
                != tuple(first.domain.get(k) for k in keys)
                for item in inputs
            ):
                return None, ("PIE-B1005", "set_column_text_domain_mismatch")
            domain["max_characters"] = max(
                int(item.realization.domain.get("max_characters", 0)) for item in inputs
            )
        elif tag == "Decimal":
            if any(
                (
                    item.realization.domain.get("precision"),
                    item.realization.domain.get("scale"),
                )
                != (first.domain.get("precision"), first.domain.get("scale"))
                for item in inputs
            ):
                return None, ("PIE-B1005", "set_column_decimal_parameter_mismatch")
        elif any(item.realization.domain != first.domain for item in inputs):
            return None, ("PIE-B1002", "set_column_physical_representation_mismatch")
    physical = nullability(kind, tuple(item.realization.nullable for item in inputs))
    if physical != NULLABILITY[column.source.nullability]:
        return None, ("PIE-B1002", "set_column_nullability_drift")
    if (
        quantifier is SetOperationQuantifier.DISTINCT
        or kind is not SetOperationKind.UNION
    ):
        if any(item.reason is not None for item in evidence):
            return None, ("PIE-B1003", "set_row_equivalence_domain_unsupported")
    return rows.Realization(tag, storage, physical, domain), None


def build_set_unit(
    request,
    definition,
    body,
    *,
    uses_by_ref,
    source_refs,
    by_definition,
    index,
    final,
    symbol,
):
    """Realize one SET definition as its own closed unit."""

    plan = request.plan
    exports = definition.original.exports
    operands = sorted(
        (o for o in plan.set_operands if o.body is body.ref), key=lambda o: o.position
    )
    inputs = {i.ref: i for i in plan.set_inputs}
    columns = sorted(
        (c for c in plan.set_columns if c.body is body.ref), key=lambda c: c.position
    )

    def problem(code, detail, subject, location=None):
        return None, (code, detail, subject, location)

    if tuple(o.ref for o in operands) != tuple(body.operands) or tuple(
        c.ref for c in columns
    ) != tuple(body.columns):
        return problem("PIE-B1001", "set_inventory_drift", body.ref)
    realized_operands = []
    for operand in operands:
        use = uses_by_ref.get(operand.use.ref)
        if (
            use is None
            or use.original is not operand.use
            or use.original.consumer is not (definition.original.ref)
        ):
            return problem("PIE-B1001", "set_operand_use_not_bound", operand.ref)
        fields = [inputs.get(ref) for ref in operand.fields]
        if any(f is None for f in fields) or len(fields) != len(use.bindings):
            return problem("PIE-B1001", "set_operand_inventory_drift", operand.ref)
        alias = symbol(0, operand.ref, f"o{operand.ref.position}")
        reads: list[rows.StageColumn] = []
        source = None
        if use.original.producer in source_refs:
            source = source_refs[use.original.producer]
            matches = tuple(
                item for item in request.sources if item.owner is source.source.owner
            )
            if len(matches) != 1:
                return problem("PIE-B1001", "source_mapping_missing", source.ref)
            producer: Any = matches[0]
            for position, (field, link) in enumerate(
                zip(fields, use.bindings, strict=True)
            ):
                assert field is not None
                bound = tuple(
                    item
                    for item in producer.fields
                    if item.field is link.canonical.field
                )
                if (
                    len(bound) != 1
                    or link.terminal is not link.canonical
                    or field.terminal is not link.terminal
                    or field.binding is not link.input_port
                ):
                    return problem(
                        "PIE-B1001", "set_operand_terminal_not_bound", field.ref
                    )
                realization = rows.field_realization(bound[0])
                if realization is None:
                    return problem(
                        "PIE-B1004",
                        "set_operand_field_representation_missing",
                        field.ref,
                    )
                reads.append(
                    rows.StageColumn(
                        position,
                        bound[0].column,
                        link.canonical.ref,
                        realization,
                        field=bound[0],
                        source_port=link.canonical.ref,
                    )
                )
        else:
            producer = by_definition.get(use.original.producer)
            if producer is None:
                return problem("PIE-B1001", "named_producer_not_realized", operand.ref)
            for position, (field, link) in enumerate(
                zip(fields, use.bindings, strict=True)
            ):
                assert field is not None
                column = producer.columns[position].column
                if (
                    column.terminal is not link.terminal.ref
                    or field.terminal is not link.terminal
                    or field.binding is not link.input_port
                ):
                    return problem(
                        "PIE-B1001", "set_operand_terminal_not_bound", field.ref
                    )
                reads.append(replace(column, position=position, name=f"c{position}"))
        realized_operands.append(
            SetOperandBody(
                operand.position,
                operand,
                use,
                producer,
                source,
                alias,
                tuple(reads),
                tuple(f for f in fields if f is not None),
            )
        )
    if len(columns) != len(exports) or len(exports) != len(definition.terminals):
        return problem("PIE-B1001", "set_terminal_denominator", body.ref)
    realized_columns = []
    for ordinal, (column, export, terminal) in enumerate(
        zip(columns, exports, definition.terminals, strict=True)
    ):
        if (
            column.output is not terminal.ref
            or getattr(terminal, "canonical", None) is not export
            or len(column.inputs) != len(realized_operands)
            or any(
                ref is not operand.inputs[ordinal].ref
                for ref, operand in zip(column.inputs, realized_operands, strict=True)
            )
            or any(
                len(operand.columns) != len(columns) for operand in realized_operands
            )
        ):
            return problem("PIE-B1001", "set_column_inventory_drift", column.ref)
        positional = tuple(operand.columns[ordinal] for operand in realized_operands)
        realization, failure = column_realization(
            body.kind,
            body.quantifier,
            column,
            positional,
            tuple(operand.inputs[ordinal].evidence for operand in realized_operands),
        )
        if realization is None:
            assert failure is not None
            location = getattr(body.operation.owner.definition.body, "span", None)
            return problem(*failure, column.ref, location)
        label = export.identity.name if final else f"c{ordinal}"
        realized_columns.append(
            SetColumn(
                ordinal,
                column,
                export,
                terminal,
                positional,
                realization,
                symbol(ordinal + 1, export.ref, label),
                label,
                rows.StageColumn(ordinal, label, terminal.ref, realization),
            )
        )
    unit = SetBody(
        definition,
        body,
        index,
        body.kind,
        body.quantifier,
        tuple(realized_operands),
        tuple(realized_columns),
        tuple(definition.terminals),
        final,
        None if final else symbol(index, body.ref, f"p{index}"),
        ()
        if final
        else tuple(
            symbol(i, t.ref, f"c{i}") for i, t in enumerate(definition.terminals)
        ),
    )
    return unit, None


def requirements(request, unit: SetBody, naming, requirement):
    """Every requirement this SET unit's own generated structures introduce."""

    from pietto._project.project_sql_emission_ast import scan_requirements

    encoding = tuple(
        p
        for p in request.premises
        if p.scope == "statement" and p.key == "client_encoding"
    )
    result = [requirement("set_operation", unit.body.ref, DEMAND_RULE, naming)]
    for operand in unit.operands:
        result.append(
            requirement("set_operand", operand.operand.ref, DEMAND_RULE, naming)
        )
        if operand.source is not None:
            result.extend(scan_requirements(request, operand.producer))
    for column in unit.columns:
        result.append(
            requirement(
                "set_column",
                column.source.ref,
                DEMAND_RULE,
                encoding if column.realization.tag == "Text" else (),
            )
        )
    if unit.body.requires_equivalence:
        result.append(
            requirement("set_row_equivalence", unit.body.ref, DEMAND_RULE, ())
        )
    return tuple(result)


def requirement_evidence(query, item) -> list[dict[str, Any]]:
    """Public evidence for one generated SET requirement, from its AST node."""

    for unit in getattr(query, "units", ()):
        if type(unit) is not SetBody:
            continue
        if (
            item.kind in {"set_operation", "set_row_equivalence"}
            and unit.body.ref is item.subject
        ):
            return [
                {
                    "kind": unit.kind.value,
                    "quantifier": unit.quantifier.value,
                    "operands": len(unit.operands),
                    "fold": unit.body.fold,
                }
            ]
        if item.kind == "set_column":
            for column in unit.columns:
                if column.source.ref is item.subject:
                    return [
                        {
                            "position": column.ordinal,
                            "tag": column.realization.tag,
                            "nullable": column.realization.nullable,
                        }
                    ]
    return []
