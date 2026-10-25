"""Cycle diagnostics for table and query relation dependencies."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import (
    AnyExpr,
    FromClause,
    JoinClause,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef


def check_relation_cycles(
    script: Script,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    *,
    join_resolutions: Mapping[JoinClause, RelationDefinition] | None = None,
    any_dependencies: tuple[
        tuple[DerivedRelation, AnyExpr, RelationDefinition | None], ...
    ] = (),
) -> tuple[set[DerivedRelation], list[Diagnostic]]:
    """Find table/query dependency cycles in deterministic source order.

    A relation reads its FROM input and, with ``join_resolutions`` (single
    files), each JOIN target in JOIN order. The walk follows those reads depth
    first from each relation in source order, and each FROM or JOIN clause
    that closes a cycle on its path reports that cycle. Every relation on a
    cycle is returned, also one that no reported cycle names.
    """

    # Tarjan's strongly connected components over the same walk: a relation's
    # discovery index becomes `closed`, above every index, once its component
    # is complete.
    closed = len(script.definitions)
    discovery: dict[DerivedRelation, int] = {}
    stack: list[DerivedRelation] = []
    stack_indexes: dict[DerivedRelation, int] = {}
    component_stack: list[DerivedRelation] = []
    cyclic_relations: set[DerivedRelation] = set()
    diagnostics: list[Diagnostic] = []

    def visit(definition: DerivedRelation) -> int:
        """Return the lowest discovery index ``definition`` reaches in an open
        component; it is its own exactly when its component is complete."""

        low = discovery[definition] = len(discovery)
        stack_indexes[definition] = len(stack)
        stack.append(definition)
        component_start = len(component_stack)
        component_stack.append(definition)

        edges: list[
            tuple[FromClause | JoinClause | AnyExpr, RelationDefinition | None]
        ] = [(definition.from_clause, from_resolutions.get(definition.from_clause))]
        if join_resolutions is not None:
            edges.extend(
                (clause, join_resolutions.get(clause))
                for clause in definition.join_clauses
            )
        edges.extend(
            (expression, target)
            for owner, expression, target in any_dependencies
            if owner is definition
        )
        for edge, target in edges:
            if not isinstance(target, (TableDef, QueryDef)):
                continue
            if target not in discovery:
                low = min(low, visit(target))
                continue
            if target in stack_indexes:
                cycle = stack[stack_indexes[target] :]
                cyclic_relations.update(cycle)
                diagnostics.append(_cycle_diagnostic(edge, cycle))
            low = min(low, discovery[target])

        stack.pop()
        stack_indexes.pop(definition)
        if low == discovery[definition]:
            component = component_stack[component_start:]
            del component_stack[component_start:]
            for member in component:
                discovery[member] = closed
            if len(component) > 1:
                cyclic_relations.update(component)
        return low

    for definition in script.definitions:
        if isinstance(definition, (TableDef, QueryDef)) and definition not in discovery:
            visit(definition)

    return cyclic_relations, diagnostics


def _cycle_diagnostic(
    closing_edge: FromClause | JoinClause | AnyExpr,
    cycle: list[DerivedRelation],
) -> Diagnostic:
    """Report one cycle at the dependency edge that closes it."""

    span = closing_edge.span
    names = [definition.name for definition in cycle]
    cycle_path = " -> ".join([*names, names[0]])
    return Diagnostic(
        code="PIE-S2302",
        severity=Severity.ERROR,
        message=f"Relation cycle detected: {cycle_path}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
