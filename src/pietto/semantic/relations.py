"""Relation input resolution for table and query definitions."""

from __future__ import annotations

from pietto import ast_nodes as ast
from pietto.ast_nodes import SetRelationDef
from pietto._flat_relational_admission import (
    _EXPLICIT_MODULES,
    availability_diagnostic,
)

from collections.abc import Mapping

from pietto.ast_nodes import (
    AuthoredJoinKind,
    Definition,
    FromClause,
    JoinClause,
    Node,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

RelationDefinition = SourceDef | TableDef | QueryDef
_ENDPOINT_RELATIONS = (SourceDef, TableDef, QueryDef)
# A SEMI or ANTI JOIN binding is visible only to its own `on`.
_HIDING_KINDS = frozenset({AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI})


_KNOWN_DEFINITIONS = frozenset(
    {
        ast.TypeDef,
        ast.EnumDef,
        ast.ShapeDef,
        ast.ConstraintDef,
        ast.DeriveDef,
        ast.SourceDef,
        ast.TableDef,
        ast.QueryDef,
        ast.SetRelationDef,
    }
)


def resolve_relation_inputs(
    script: Script,
    relation_symbols: Mapping[str, Definition],
) -> tuple[dict[FromClause, RelationDefinition], list[Diagnostic]]:
    """Resolve table and query from clauses against collected relations."""

    resolutions: dict[FromClause, RelationDefinition] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        if type(definition) not in _KNOWN_DEFINITIONS:
            # syntax_diagnostics reports the one availability diagnostic.
            continue
        if not isinstance(definition, (TableDef, QueryDef)):
            continue

        from_clause = definition.from_clause
        target = relation_symbols.get(from_clause.source_name)
        if isinstance(target, (SourceDef, TableDef, QueryDef)):
            resolutions[from_clause] = target
        elif isinstance(target, SetRelationDef):
            diagnostics.append(_set_operation_input_diagnostic(from_clause, target))
        else:
            diagnostics.append(_unknown_relation_diagnostic(from_clause))

    return resolutions, diagnostics


def join_target(
    clause: JoinClause,
    relation_symbols: Mapping[str, Definition],
) -> RelationDefinition | Diagnostic:
    """Return the relation a JOIN reads, or why it reads none, at the JOIN.

    A name that is no relation is PIE-S2301 and a set operation keeps the
    availability diagnostic of a FROM input that names one.
    """

    target = relation_symbols.get(clause.target_relation_name)
    if isinstance(target, _ENDPOINT_RELATIONS):
        return target
    if isinstance(target, SetRelationDef):
        return _set_operation_input_diagnostic(clause, target)
    return _join_diagnostic(
        clause, "PIE-S2301", f"Unknown relation: {clause.target_relation_name}"
    )


def _set_operation_input_diagnostic(node: Node, target: SetRelationDef) -> Diagnostic:
    return availability_diagnostic(
        node.span,
        "Set-operation inputs are available only when "
        f"{_EXPLICIT_MODULES} completes them: {target.name}",
    )


def _join_diagnostic(node: Node, code: str, message: str) -> Diagnostic:
    span = node.span
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _unknown_relation_diagnostic(from_clause: FromClause) -> Diagnostic:
    """Report an unresolved relation at the complete from-clause span."""

    span = from_clause.span
    return Diagnostic(
        code="PIE-S2301",
        severity=Severity.ERROR,
        message=f"Unknown relation: {from_clause.source_name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
