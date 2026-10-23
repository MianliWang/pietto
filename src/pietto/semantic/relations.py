"""Relation input resolution for table and query definitions."""

from __future__ import annotations

from pietto import ast_nodes as ast
from pietto.ast_nodes import SetRelationDef
from pietto._flat_relational_admission import (
    _EXPLICIT_MODULES,
    availability_diagnostic,
    unsupported_join,
)

from collections.abc import Mapping

from pietto.ast_nodes import (
    AuthoredJoinKind,
    Definition,
    FromClause,
    JoinClause,
    Node,
    QueryDef,
    RelationshipMetadata,
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
    matches = [0] if definition.from_clause.source_name == name else []
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


def check_join_references(
    script: Script,
    relation_symbols: Mapping[str, Definition],
) -> list[Diagnostic]:
    """Check the names that a single-file INNER or LEFT JOIN reads.

    The JOIN target must name a relation (PIE-S2301). Its `from` must name
    exactly one visible earlier binding: the FROM input or an earlier JOIN
    binding other than SEMI and ANTI. Each VIA step must name a declared
    relationship and two different endpoint roles of it, and the steps must
    lead from that binding's relation to the JOIN target (PIE-S2335). Other
    JOIN forms keep their availability diagnostic only, and a relationship
    with a declaration diagnostic of its own is not checked again.
    """

    relationships: dict[str, list[RelationshipMetadata]] = {}
    for relationship in script.relationships:
        relationships.setdefault(relationship.name, []).append(relationship)

    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        for position, clause in enumerate(definition.join_clauses):
            if unsupported_join(clause):
                continue
            if clause.target_relation_name not in relation_symbols:
                diagnostics.append(
                    _join_diagnostic(
                        clause,
                        "PIE-S2301",
                        f"Unknown relation: {clause.target_relation_name}",
                    )
                )
            if clause.source_binding_name is None:
                # Single-file checks do not infer an omitted JOIN source.
                diagnostics.extend(
                    _via_diagnostics(
                        clause, relationships, relation_symbols, source_relation=None
                    )
                )
                continue
            source = written_join_source(definition, position)
            if isinstance(source, Diagnostic):
                diagnostics.append(source)
                source_relation = None
            elif source == 0:
                source_relation = definition.from_clause.source_name
            else:
                source_relation = definition.join_clauses[
                    source - 1
                ].target_relation_name
            diagnostics.extend(
                _via_diagnostics(
                    clause,
                    relationships,
                    relation_symbols,
                    source_relation=(
                        source_relation if source_relation in relation_symbols else None
                    ),
                )
            )
    return diagnostics


def _via_diagnostics(
    clause: JoinClause,
    relationships: Mapping[str, list[RelationshipMetadata]],
    relation_symbols: Mapping[str, Definition],
    *,
    source_relation: str | None,
) -> list[Diagnostic]:
    """Check each VIA step, then the path that valid steps form."""

    diagnostics: list[Diagnostic] = []
    hops: list[tuple[str, str]] = []
    reported_elsewhere = False
    roles_omitted = False
    for step in clause.traversal_steps:
        candidates = relationships.get(step.relationship_name, [])
        if not candidates:
            diagnostics.append(
                _join_diagnostic(
                    step,
                    "PIE-S2335",
                    f"Unknown relationship in JOIN VIA: {step.relationship_name}",
                )
            )
            continue
        endpoints = {
            endpoint.local_name: endpoint.relation_name
            for endpoint in candidates[0].endpoints
        }
        if (
            len(candidates) > 1
            or len(endpoints) != len(candidates[0].endpoints)
            or any(
                not isinstance(relation_symbols.get(relation), _ENDPOINT_RELATIONS)
                for relation in endpoints.values()
            )
        ):
            # PIE-S2601..PIE-S2603 already report this relationship.
            reported_elsewhere = True
            continue
        if step.source_endpoint_role is None or step.target_endpoint_role is None:
            # Single-file checks do not infer omitted VIA roles, so the path
            # that the steps form is not checked either.
            roles_omitted = True
            continue
        roles = (step.source_endpoint_role, step.target_endpoint_role)
        unknown = [role for role in roles if role not in endpoints]
        diagnostics.extend(
            _join_diagnostic(
                step,
                "PIE-S2335",
                f"Unknown endpoint role in JOIN VIA {step.relationship_name}: {role}",
            )
            for role in unknown
        )
        if not unknown and roles[0] == roles[1]:
            diagnostics.append(
                _join_diagnostic(
                    step,
                    "PIE-S2335",
                    f"JOIN VIA {step.relationship_name} uses one endpoint role as "
                    f"both source and target: {roles[0]}",
                )
            )
        hops.append((endpoints.get(roles[0], ""), endpoints.get(roles[1], "")))
    if not hops or diagnostics or reported_elsewhere or roles_omitted:
        return diagnostics
    for (_, end), (start, _) in zip(hops, hops[1:]):
        if end != start:
            return [
                _join_diagnostic(
                    clause,
                    "PIE-S2335",
                    f"JOIN VIA steps do not connect: a step ends at {end} and the "
                    f"next starts at {start}",
                )
            ]
    if source_relation is not None and hops[0][0] != source_relation:
        diagnostics.append(
            _join_diagnostic(
                clause,
                "PIE-S2335",
                f"JOIN VIA path starts at {hops[0][0]}, not at source binding "
                f"{clause.source_binding_name} ({source_relation})",
            )
        )
    if (
        clause.target_relation_name in relation_symbols
        and hops[-1][1] != clause.target_relation_name
    ):
        diagnostics.append(
            _join_diagnostic(
                clause,
                "PIE-S2335",
                f"JOIN VIA path ends at {hops[-1][1]}, not at the JOIN target "
                f"{clause.target_relation_name}",
            )
        )
    return diagnostics


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
