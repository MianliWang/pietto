"""Typed VALUES SQL construction: one zero-input unit with declared column types.

A VALUES definition is one generated unit. As a named producer it is a CTE whose
column list writes every alias and whose body is ``VALUES`` rows of explicitly
CAST cells (``ROW(...)`` on MySQL); as the selected statement it is a SELECT that
labels the derived ``VALUES`` table's columns. A zero-row body is a typed
``SELECT CAST(NULL AS ...) ... WHERE FALSE``. Every cell, a NULL included, is
written with its column's declared type, so no column name or type is ever left
to the database. Cells are fixed literals: they are never bound parameters.

The renderer turns these nodes into bytes and the independent verifier re-derives
them from the retained plan, so no SQL text is authority here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pietto._project import project_sql_emission_parameters as parameters
from pietto._project import project_sql_emission_rows as rows

__all__: tuple[str, ...] = ()

# Fixed cells are R04 literal transport; each declared column is R02 representation.
ROWS_RULE = "R04"
COLUMN_RULE = "R02"
INT_BOUNDS = (-(1 << 63), (1 << 63) - 1)


def _scalar(value: Any) -> Any:
    return value if type(value) in {int, str, bool, type(None)} else "..."


@dataclass(frozen=True, slots=True, eq=False)
class ValuesOutputColumn:
    """One declared column: its output identity, label and realization."""

    ordinal: int
    source: Any
    export: Any
    output: Any
    realization: rows.Realization
    physical: str
    symbol: Any
    label: str
    column: rows.StageColumn

    def __repr__(self) -> str:
        return (
            f"ValuesOutputColumn(ordinal={_scalar(self.ordinal)}, "
            f"label={_scalar(self.label)}, physical={_scalar(self.physical)})"
        )


@dataclass(frozen=True, slots=True, eq=False)
class ValuesBody:
    """One generated VALUES unit realizing exactly one authored VALUES body."""

    definition: Any
    body: Any
    index: int
    columns: tuple[ValuesOutputColumn, ...]
    rows: tuple[tuple[Any, ...], ...]
    terminals: tuple[Any, ...]
    final: bool
    symbol: Any
    cte_columns: tuple[Any, ...]
    scope: Any
    predicate: None = None
    aggregation: None = None
    window: None = None

    @property
    def block(self) -> Any:
        """The plan VALUES body names this unit wherever a stage block would."""

        return self.body

    def __repr__(self) -> str:
        return (
            f"ValuesBody(index={_scalar(self.index)}, final={_scalar(self.final)}, "
            f"columns=<{len(self.columns)}>, rows=<{len(self.rows)}>)"
        )


def bodies_by_definition(plan) -> dict[Any, Any]:
    result: dict[Any, Any] = {}
    for body in plan.values_bodies:
        if body.definition in result:
            return {}
        result[body.definition] = body
    return result


def bodies_admitted(plan) -> bool:
    """Whether every VALUES body has the closed shape this owner emits."""

    columns = {c.ref: c for c in plan.values_columns}
    if len(bodies_by_definition(plan)) != len(plan.values_bodies):
        return False
    return all(
        body.columns
        and len(body.columns) == len(body.outputs)
        and all(ref in columns for ref in body.columns)
        and [columns[ref].position for ref in body.columns]
        == list(range(len(body.columns)))
        and all(len(row) == len(body.columns) for row in body.rows)
        for body in plan.values_bodies
    )


def node_count(unit: ValuesBody) -> int:
    """The bounded node contribution of one VALUES unit."""

    return 2 + len(unit.columns) * (1 + len(unit.rows))


def column_realization(tag: str, nullable: bool, values: tuple[Any, ...], family):
    """The exact realization of one declared column over its fixed cells.

    Storage is the declared type's target carrier and, as for a source field,
    an Int is proved only within that carrier; the domain describes exactly the
    column's non-NULL cells (an Int range, a Text length) and is the whole
    carrier when it has none.
    """
    present = tuple(value for value in values if value is not None)
    if any(not parameters.value_valid(tag, value, family) for value in present):
        return None
    storage = {"kind": parameters.PHYSICAL[family][tag]}
    if tag == "Bool":
        domain: dict[str, Any] = {"kind": "bool01"}
    elif tag == "Int":
        low, high = (min(present), max(present)) if present else INT_BOUNDS
        domain = {"kind": "int_range", "min": str(low), "max": str(high)}
    elif tag == "Float":
        domain = {"kind": "finite_float", "format": "binary64"}
    else:
        domain = {
            "kind": "text",
            "max_characters": max((len(value) for value in present), default=0),
            "encoding": "UTF8" if family == "postgres" else "utf8mb4",
            "collation": "C" if family == "postgres" else "utf8mb4_0900_bin",
            "padding": "NO PAD",
        }
    return rows.source_realization(rows.Realization(tag, storage, nullable, domain))


def cell_token(tag: str, value: Any, family: str) -> str:
    """One fixed cell spelling inside its declared-type CAST."""

    return "NULL" if value is None else parameters.scalar_token(tag, value, family)


def build_values_unit(request, definition, body, *, index, final, symbol):
    """Realize one VALUES definition as its own closed zero-input unit."""

    plan = request.plan
    family = request.family
    exports = definition.original.exports
    columns = sorted(
        (c for c in plan.values_columns if c.body is body.ref),
        key=lambda c: c.position,
    )

    def problem(code, detail, subject, location=None):
        return None, (code, detail, subject, location)

    if (
        tuple(c.ref for c in columns) != tuple(body.columns)
        or len(columns) != len(exports)
        or len(exports) != len(definition.terminals)
        or any(len(row) != len(columns) for row in body.rows)
    ):
        return problem("PIE-B1001", "values_inventory_drift", body.ref)
    authored = body.relation.definition.body
    realized = []
    for ordinal, (column, export, terminal) in enumerate(
        zip(columns, exports, definition.terminals, strict=True)
    ):
        declared = column.source
        if (
            column.output is not terminal.ref
            or getattr(terminal, "canonical", None) is not export
            or declared.position != ordinal
        ):
            return problem("PIE-B1001", "values_column_inventory_drift", column.ref)
        realization = column_realization(
            declared.logical_type,
            declared.nullable,
            tuple(row[ordinal] for row in body.rows),
            family,
        )
        if realization is None:
            return problem(
                "PIE-B1002",
                "values_cell_representation",
                column.ref,
                authored.columns[ordinal].span,
            )
        label = export.identity.name if final else f"c{ordinal}"
        realized.append(
            ValuesOutputColumn(
                ordinal,
                column,
                export,
                terminal,
                realization,
                parameters.PHYSICAL[family][declared.logical_type],
                symbol(ordinal + 1, export.ref, label),
                label,
                rows.StageColumn(ordinal, label, terminal.ref, realization),
            )
        )
    unit = ValuesBody(
        definition,
        body,
        index,
        tuple(realized),
        body.rows,
        tuple(definition.terminals),
        final,
        None if final else symbol(index, body.ref, f"p{index}"),
        ()
        if final
        else tuple(
            symbol(i, t.ref, f"c{i}") for i, t in enumerate(definition.terminals)
        ),
        symbol(0, body.ref, f"v{body.ref.position}"),
    )
    return unit, None


def requirements(request, unit: ValuesBody, naming, requirement):
    """Every requirement this VALUES unit's own generated structures introduce."""

    encoding = tuple(
        p
        for p in request.premises
        if p.scope == "statement" and p.key == "client_encoding"
    )
    return (
        requirement("values_rows", unit.body.ref, ROWS_RULE, naming),
        *(
            requirement(
                "values_column",
                column.source.ref,
                COLUMN_RULE,
                encoding if column.realization.tag == "Text" else (),
            )
            for column in unit.columns
        ),
    )


def requirement_evidence(query, item) -> list[dict[str, Any]]:
    """Public evidence for one generated VALUES requirement, from its AST node."""

    for unit in getattr(query, "units", ()):
        if type(unit) is not ValuesBody:
            continue
        if item.kind == "values_rows" and unit.body.ref is item.subject:
            return [{"rows": len(unit.rows), "columns": len(unit.columns)}]
        if item.kind == "values_column":
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


@dataclass(frozen=True, slots=True, eq=False)
class CompiledValuesSubject:
    ref: Any


@dataclass(frozen=True, slots=True, eq=False)
class CompiledValuesColumnSource:
    """A compiled column subject keeps its declared name for the field record."""

    ref: Any
    name: str

    @property
    def source(self) -> Any:
        return self


def build_compiled_unit(plan, record, definition, family):
    """Realize one compiled VALUES record over its fresh typed ports."""
    from pietto._project.project_sql_emission_ast import SQLSymbol

    facts = {f.address: f for f in plan.ir.completed.facts}
    refs = plan.references
    records = plan.ir.completed.root.records
    name, labels, alias, final, index = record.get("layout")
    columns = []
    for ordinal, (field_address, port_address) in enumerate(
        zip(record.get("fields"), record.get("outputs"), strict=True)
    ):
        port = plan.ports[port_address]
        realization = facts[port_address].require_realization()
        label = port.identity.name
        columns.append(
            ValuesOutputColumn(
                ordinal,
                CompiledValuesColumnSource(
                    refs[field_address], records[field_address].get("label")
                ),
                port,
                port,
                realization,
                parameters.PHYSICAL[family][realization.tag],
                SQLSymbol(ordinal + 1, port.ref, label),
                label,
                rows.StageColumn(ordinal, label, port.ref, realization),
            )
        )
    return ValuesBody(
        definition,
        CompiledValuesSubject(refs[record.address]),
        index,
        tuple(columns),
        tuple(
            tuple(None if cell is None else cell.value for cell in row)
            for row in record.get("rows")
        ),
        tuple(c.export for c in columns),
        final,
        None if name is None else SQLSymbol(index, refs[record.address], name),
        tuple(
            SQLSymbol(i, c.export.ref, label)
            for i, (c, label) in enumerate(zip(columns, labels, strict=True))
        )
        if labels
        else (),
        SQLSymbol(0, refs[record.address], alias),
    )
