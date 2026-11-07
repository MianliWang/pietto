"""The order proof of each `first` and `last` of an EXPLICIT_MODULES project.

The rule is the single file's (`semantic.ordered_values`): each key is a
direct field of the input that is never None, and the keys with the field
GROUP BY keys that are never None cover one `unique(...)` of the FROM source's
shape (D73.05). A source field names its shape by the identity of its
declaration, as a Collect read's order proof reads it. As in a single file, a
call with an error already reported inside it is not checked again, so it
reports once.
"""

from __future__ import annotations

from collections.abc import Sequence

from pietto._project.model import (
    ProjectRowFieldNullability,
    ProjectSemanticResult,
)
from pietto.ast_nodes import (
    CallExpr,
    NameExpr,
    QueryDef,
    ShapeDef,
    SourceDef,
    TableDef,
    UniqueDef,
)
from pietto.errors import Diagnostic
from pietto.semantic.aggregates import (
    ORDERED_VALUE_AGGREGATE_NAMES,
    semantic_aggregate_call_name,
)
from pietto.semantic.model import ValueTypeKind
from pietto.semantic.ordered_values import (
    ordered_value_join_diagnostic,
    ordered_value_order_diagnostic,
    ordered_value_reported,
)

__all__ = ("ordered_value_project_diagnostics",)


def ordered_value_project_diagnostics(
    semantic_result: ProjectSemanticResult,
    reported: Sequence[Diagnostic],
) -> tuple[Diagnostic, ...]:
    """PIE-S2334 at a `first` or `last` over JOIN rows and PIE-S2104 at the
    first key of its order that fails the proof, in module and source order,
    for each call with no error in ``reported``."""

    facts = semantic_result.module_semantic_facts
    if facts is None:
        return ()
    shapes = {
        id(item): definition
        for module in semantic_result.modules
        if module.parsed_input is not None
        for definition in module.parsed_input.script.definitions
        if type(definition) is ShapeDef
        for item in definition.items
    }
    found: list[Diagnostic] = []
    for environment in facts.environments:
        for relation in environment.relation_facts:
            definition = relation.owner.definition
            if not isinstance(definition, (TableDef, QueryDef)):
                continue
            calls = tuple(
                item.expression
                for item in definition.select_items
                if type(item.expression) is CallExpr
                and semantic_aggregate_call_name(item.expression)
                in ORDERED_VALUE_AGGREGATE_NAMES
                and not ordered_value_reported(item.expression, reported)
            )
            if definition.join_clauses or definition.join_filters:
                found.extend(ordered_value_join_diagnostic(call) for call in calls)
                continue
            if not calls:
                continue
            state = relation.input_state
            schema = None if state is None else state.schema
            if schema is None or schema.is_unknown or definition.from_clause is None:
                continue
            source = (
                relation.resolution is not None
                and type(relation.resolution.target_symbol.target_occurrence.definition)
                is SourceDef
            )
            owners = {
                id(shape): shape
                for row_field in schema.fields.values()
                if (shape := shapes.get(id(row_field.field_def))) is not None
            }
            uniques = (
                tuple(
                    item.field_names
                    for item in next(iter(owners.values())).items
                    if type(item) is UniqueDef
                )
                if source and len(owners) == 1
                else ()
            )
            lets = (
                {}
                if relation.let_scope_facts is None
                else dict(relation.let_scope_facts.binding_expressions)
            )
            known = {
                name
                for name, value_type in (
                    {}
                    if relation.let_scope_facts is None
                    else relation.let_scope_facts.binding_value_types
                ).items()
                if value_type.kind is ValueTypeKind.KNOWN
            }
            for call in calls:
                assert type(call) is CallExpr
                value = call.arguments[0] if call.arguments else None
                if (
                    type(value) is NameExpr
                    and value.name in lets
                    and value.name not in known
                ):
                    # A single file proves a call only once its type is known:
                    # a `let:` name that is refused, has an error of its own or
                    # reads one has none, and that error stands alone.
                    continue
                problem = ordered_value_order_diagnostic(
                    call,
                    fields={
                        name: row_field.nullability
                        is not ProjectRowFieldNullability.NON_NULL
                        for name, row_field in schema.fields.items()
                    },
                    qualifier=definition.from_clause.binding_name
                    or definition.from_clause.source_name,
                    lets=lets,
                    where=definition,
                    group_keys=()
                    if definition.group_by_clause is None
                    else tuple(group.key for group in definition.group_by_clause.items),
                    unique_keys=uniques,
                    source_keys=source,
                )
                if problem is not None:
                    found.append(problem)
    return tuple(found)
