"""Cycle diagnostics for table and query relation dependencies."""

from __future__ import annotations

from collections.abc import Mapping

from pietto.ast_nodes import FromClause, QueryDef, Script, SourceDef, TableDef
from pietto.errors import Diagnostic, Severity, SourceLocation

RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef


def check_relation_cycles(
    script: Script,
    from_resolutions: Mapping[FromClause, RelationDefinition],
) -> tuple[set[DerivedRelation], list[Diagnostic]]:
    """Find table/query dependency cycles in deterministic source order."""

    state: dict[DerivedRelation, int] = {}
    stack: list[DerivedRelation] = []
    stack_indexes: dict[DerivedRelation, int] = {}
    cyclic_relations: set[DerivedRelation] = set()
    diagnostics: list[Diagnostic] = []

    def visit(definition: DerivedRelation) -> None:
        state[definition] = 1
        stack_indexes[definition] = len(stack)
        stack.append(definition)

        target = from_resolutions.get(definition.from_clause)
        if isinstance(target, (TableDef, QueryDef)):
            target_state = state.get(target, 0)
            if target_state == 0:
                visit(target)
            elif target_state == 1:
                cycle = stack[stack_indexes[target] :]
                cyclic_relations.update(cycle)
                diagnostics.append(_cycle_diagnostic(definition, cycle))

        stack.pop()
        stack_indexes.pop(definition)
        state[definition] = 2

    for definition in script.definitions:
        if (
            isinstance(definition, (TableDef, QueryDef))
            and state.get(definition, 0) == 0
        ):
            visit(definition)

    return cyclic_relations, diagnostics


def _cycle_diagnostic(
    closing_definition: DerivedRelation,
    cycle: list[DerivedRelation],
) -> Diagnostic:
    """Report one cycle at the dependency edge that closes it."""

    span = closing_definition.from_clause.span
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
