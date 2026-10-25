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


def same_file_relation_reads(
    script: Script,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    relation_symbols: Mapping[str, Definition],
    generated: Mapping[int, ast.AnyExpr],
) -> list[Diagnostic]:
    """PIE-S2382 at each single-file read of a table or query of the file.

    Single-file SQL reads such a relation by its name, so the SQL runs only
    where the database already has that relation. A read is reported where
    PIE-S2301 reports an unknown name: at the FROM clause or the JOIN;
    ``generated`` maps the id of each JOIN that an inter-JOIN ANY filter
    became to that ANY, reported at its relation. Any other ANY is no such
    read: its reader's SQL defines the relation it reads as a CTE.
    """

    reads: list[tuple[ast.Span, Definition | None]] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        reads.append(
            (definition.from_clause.span, from_resolutions.get(definition.from_clause))
        )
        for clause in definition.join_clauses:
            any_expr = generated.get(id(clause))
            reads.append(
                (
                    clause.span if any_expr is None else any_expr.relation_span,
                    relation_symbols.get(clause.target_relation_name),
                )
            )
    found: list[Diagnostic] = []
    for span, target in reads:
        if not isinstance(target, (TableDef, QueryDef)):
            continue
        kind = "table" if isinstance(target, TableDef) else "query"
        found.append(
            Diagnostic(
                code="PIE-S2382",
                severity=Severity.WARNING,
                message=(
                    f"`{target.name}` is a {kind} of this file; single-file SQL "
                    "reads it by name, so the SQL runs only where the database "
                    f"already has a relation named {target.name} (an "
                    "EXPLICIT_MODULES project emits it as a CTE)"
                ),
                location=SourceLocation(
                    path=span.path,
                    line=span.line,
                    column=span.column,
                    end_line=span.end_line,
                    end_column=span.end_column,
                ),
            )
        )
    return found


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


def written_join_source(
    definition: TableDef | QueryDef,
    position: int,
    *,
    hidden_bindings: bool = False,
) -> int | Diagnostic:
    """Find the binding that the written `from` of JOIN ``position`` names.

    The result is the input ordinal of the one visible earlier binding with
    that name (0 for the FROM input, k for the target of JOIN k), or the
    PIE-S2335 at the JOIN when the name is ambiguous, is the binding this
    JOIN introduces, is bound only by a later JOIN or is unknown. A SEMI or
    ANTI binding is not visible to later JOINs; with ``hidden_bindings`` a
    name that only such an earlier binding has says so instead.
    """

    clause = definition.join_clauses[position]
    name = clause.source_binding_name
    earlier = definition.join_clauses[:position]
    matches = (
        [0]
        if (definition.from_clause.binding_name or definition.from_clause.source_name)
        == name
        else []
    )
    matches += [
        ordinal
        for ordinal, item in enumerate(earlier, start=1)
        if item.target_binding_name == name and item.kind not in _HIDING_KINDS
    ]
    hidden = [
        item.kind
        for item in earlier
        if item.target_binding_name == name and item.kind in _HIDING_KINDS
    ]
    if len(matches) == 1:
        return matches[0]
    if matches:
        message = f"Ambiguous JOIN source binding: {name}"
    elif hidden_bindings and hidden:
        kind = "a SEMI" if hidden[0] is AuthoredJoinKind.SEMI else "an ANTI"
        message = (
            f"JOIN source binding is {kind} JOIN binding, which later JOINs "
            f"cannot read: {name}"
        )
    elif name == clause.target_binding_name:
        message = f"JOIN source binding is the binding this JOIN introduces: {name}"
    elif any(
        item.target_binding_name == name
        for item in definition.join_clauses[position + 1 :]
    ):
        message = f"JOIN source binding is bound only by a later JOIN: {name}"
    else:
        message = f"Unknown JOIN source binding: {name}"
    return _join_diagnostic(clause, "PIE-S2335", message)


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
