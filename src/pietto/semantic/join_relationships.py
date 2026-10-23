"""Relationship resolution for single-file JOINs.

Private: nothing here is exported. It reads only the AST, diagnostics and
semantic facts, never project code.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from pietto.ast_nodes import (
    AuthoredJoinKind,
    BinaryExpr,
    ComparisonExpr,
    Definition,
    DottedNameExpr,
    Expression,
    JoinClause,
    JoinTraversalStep,
    Node,
    QueryDef,
    RelationshipMetadata,
    Script,
    SourceDef,
    TableDef,
    TypeExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.model import (
    RelationshipSemanticInfo,
    ResolvedType,
    RowSchema,
)
from pietto.semantic.relationship_metadata import (
    _admits,
    _expanded_type,
    _type_identity,
    check_relationship_conditions,
)

__all__ = ()

_DECLARATION_ERRORS = "its declaration has errors"
_NO_ON = "it has no `on`"
_NOT_EQUALITIES = "its `on` is not only field equalities that a JOIN can use"


@dataclass(frozen=True, slots=True)
class JoinRelationshipContext:
    """The script facts relationship resolution reads, built once per script."""

    relationships: tuple[RelationshipMetadata, ...]  # script.relationships
    admitted: tuple[RelationshipSemanticInfo, ...]  # check_relationship_metadata facts
    relation_symbols: Mapping[str, Definition]
    source_row_schemas: Mapping[SourceDef, RowSchema]
    type_expansions: Mapping[TypeExpr, ResolvedType]
    # Every relationship as a JOIN reads it, classified at the first JOIN.
    _classified: list[tuple[_Relationship, ...]] = field(
        default_factory=list, init=False, repr=False, compare=False
    )


@dataclass(frozen=True, slots=True)
class JoinBindingView:
    """One visible earlier binding of a JOIN."""

    ordinal: int
    name: str
    relation: SourceDef | TableDef | QueryDef


@dataclass(frozen=True, slots=True)
class ResolvedJoinRelationship:
    """The relationship direction a JOIN uses and its oriented equality pairs."""

    source: JoinBindingView
    source_inferred: bool
    relationship: str
    step: JoinTraversalStep | None
    source_role: str
    target_role: str
    # (source field, target field, conjunct, source operand, target operand)
    pairs: tuple[tuple[str, str, ComparisonExpr, DottedNameExpr, DottedNameExpr], ...]


def resolve_join_relationship(
    clause: JoinClause,
    *,
    target: SourceDef | TableDef | QueryDef,
    visible: tuple[JoinBindingView, ...],  # visible earlier bindings, input order
    written_source: JoinBindingView | None,  # None when `from` is omitted
    context: JoinRelationshipContext,
) -> ResolvedJoinRelationship | tuple[Diagnostic, ...]:
    """Resolve the relationship of one M1, M2 or M4 JOIN (one step).

    The result is the resolution, or its diagnostics at the JOIN or the step.
    An empty tuple means: stop silently, because a relationship with its own
    declaration diagnostic decided the JOIN (no structure, nothing reported).
    """

    steps = clause.traversal_steps
    if (
        clause.kind is AuthoredJoinKind.CROSS
        or len(steps) > 1
        or (clause.on_clause is not None and not steps)
        or not visible
    ):
        raise ValueError(
            "relationship resolution needs an M1, M2 or M4 JOIN with at most "
            "one VIA step and its visible earlier bindings"
        )
    relationships = _relationships(context)
    if steps:
        return _through_step(clause, steps[0], visible, written_source, relationships)
    if written_source is not None:
        return _direct(clause, target, written_source, relationships, inferred=False)
    # Every visible earlier binding with any declared relationship to the
    # target is a candidate, usable or not; none is preferred.
    candidates = tuple(
        binding
        for binding in visible
        if any(
            relationship.relates(binding.relation.name, clause.target_relation_name)
            for relationship in relationships
        )
    )
    if len(candidates) == 1:
        return _direct(clause, target, candidates[0], relationships, inferred=True)
    if candidates:
        return (_several_sources(clause, candidates, relationships),)
    return (
        _error(
            clause,
            f"JOIN {clause.target_binding_name}: no relationship joins "
            f"{_or_list(tuple(binding.name for binding in visible))} to "
            f"{clause.target_relation_name}; declare one, or write `from` and `on`",
        ),
    )


@dataclass(frozen=True, slots=True)
class _Relationship:
    """One declared relationship as a JOIN reads it."""

    metadata: RelationshipMetadata
    admitted: bool
    declaration_error: bool  # not admitted, or a PIE-S2604 of its two sources
    derived: str | None  # the first endpoint relation that is a table or query
    reason: str | None  # why a JOIN cannot use it; None when it can
    # Its endpoint relation names, when both name a relation.
    ends: tuple[str, str] | None

    def relates(self, first: str, second: str) -> bool:
        """Whether its two endpoint relations are exactly these, in either order."""

        return self.ends is not None and sorted(self.ends) == sorted((first, second))

    def directions(self, source: str, target: str) -> tuple[tuple[str, str], ...]:
        """The (source role, target role) of each direction from `source` to
        `target`, endpoint 1 to endpoint 2 first."""

        if self.ends is None:
            return ()
        first, second = self.metadata.endpoints
        return tuple(
            (start.local_name, end.local_name)
            for start, end in ((first, second), (second, first))
            if (start.relation_name, end.relation_name) == (source, target)
        )

    def pairs(
        self, source_role: str
    ) -> tuple[tuple[str, str, ComparisonExpr, DottedNameExpr, DottedNameExpr], ...]:
        """The equality pairs of a usable relationship, oriented source then
        target, in declared conjunct order."""

        assert self.metadata.base_match is not None
        pairs: list[
            tuple[str, str, ComparisonExpr, DottedNameExpr, DottedNameExpr]
        ] = []
        for conjunct in _conjuncts(self.metadata.base_match.expression):
            equality = _field_equality(conjunct)
            assert equality is not None
            comparison, source, target = equality
            if source.parts[0] != source_role:
                source, target = target, source
            pairs.append((source.parts[1], target.parts[1], comparison, source, target))
        return tuple(pairs)


def _relationships(context: JoinRelationshipContext) -> tuple[_Relationship, ...]:
    """Every declared relationship in declaration order, with its usability;
    classified once per context."""

    if not context._classified:
        context._classified.append(_classify(context))
    return context._classified[0]


def _classify(context: JoinRelationshipContext) -> tuple[_Relationship, ...]:
    result: list[_Relationship] = []
    position = 0
    for metadata in context.relationships:
        # The admitted facts follow declaration order and skip invalid ones.
        admitted = None
        if position < len(context.admitted) and _admits(
            context.admitted[position], metadata
        ):
            admitted = context.admitted[position]
            position += 1
        relations = tuple(
            context.relation_symbols.get(endpoint.relation_name)
            for endpoint in metadata.endpoints
        )
        first, second = metadata.endpoints
        ends = (
            (first.relation_name, second.relation_name)
            if all(
                isinstance(relation, (SourceDef, TableDef, QueryDef))
                for relation in relations
            )
            else None
        )
        derived = next(
            (
                endpoint.relation_name
                for endpoint, relation in zip(metadata.endpoints, relations)
                if isinstance(relation, (TableDef, QueryDef))
            ),
            None,
        )
        if derived is not None:
            # Tables and queries have no schema before the fixpoint, so a JOIN
            # never types such a relationship; a list names it with this
            # reason even when its declaration has errors.
            reason = f"a relationship JOIN cannot read {derived}"
            error = admitted is None
        elif admitted is None or _condition_has_errors(metadata, admitted, context):
            reason, error = _DECLARATION_ERRORS, True
        elif metadata.base_match is None:
            reason, error = _NO_ON, False
        elif not _usable_condition(metadata, relations, context):
            reason, error = _NOT_EQUALITIES, False
        else:
            reason, error = None, False
        result.append(
            _Relationship(
                metadata=metadata,
                admitted=admitted is not None,
                declaration_error=error,
                derived=derived,
                reason=reason,
                ends=ends,
            )
        )
    return tuple(result)


def _condition_has_errors(
    metadata: RelationshipMetadata,
    admitted: RelationshipSemanticInfo,
    context: JoinRelationshipContext,
) -> bool:
    """Whether the condition of a relationship between two sources has a
    PIE-S2604, checked exactly as the declaration check does."""

    return bool(
        check_relationship_conditions(
            Script(
                span=metadata.span,
                header=None,
                definitions=(),
                relationships=(metadata,),
            ),
            (admitted,),
            source_row_schemas=context.source_row_schemas,
            relation_row_schemas={},
            type_expansions=context.type_expansions,
        )
    )


def _usable_condition(
    metadata: RelationshipMetadata,
    relations: tuple[Definition | None, ...],
    context: JoinRelationshipContext,
) -> bool:
    """Whether every top-level `and` conjunct is `==` between fields of the two
    different endpoints whose types have an exact identity: not Decimal, Json,
    Any or Bytes, a shape or an unknown type, also through a type alias."""

    assert metadata.base_match is not None
    roles = {
        endpoint.local_name: relation
        for endpoint, relation in zip(metadata.endpoints, relations)
    }
    for conjunct in _conjuncts(metadata.base_match.expression):
        equality = _field_equality(conjunct)
        if equality is None:
            return False
        _, left, right = equality
        if left.parts[0] == right.parts[0] or not all(
            operand.parts[0] in roles for operand in (left, right)
        ):
            return False
        for operand in (left, right):
            relation = roles[operand.parts[0]]
            schema = (
                context.source_row_schemas.get(relation)
                if isinstance(relation, SourceDef)
                else None
            )
            row_field = None if schema is None else schema.fields.get(operand.parts[1])
            if (
                row_field is None
                or _type_identity(_expanded_type(row_field, context.type_expansions))
                is None
            ):
                return False
    return True


def _direct(
    clause: JoinClause,
    target: SourceDef | TableDef | QueryDef,
    source: JoinBindingView,
    relationships: tuple[_Relationship, ...],
    *,
    inferred: bool,
) -> ResolvedJoinRelationship | tuple[Diagnostic, ...]:
    """A JOIN without VIA from one source binding."""

    derived = next(
        (
            relation.name
            for relation in (source.relation, target)
            if isinstance(relation, (TableDef, QueryDef))
        ),
        None,
    )
    if derived is not None:
        return (_derived_relation(clause, derived),)
    related = tuple(
        relationship
        for relationship in relationships
        if relationship.relates(source.relation.name, clause.target_relation_name)
    )
    usable = tuple(
        (relationship, direction)
        for relationship in related
        if relationship.reason is None
        for direction in relationship.directions(
            source.relation.name, clause.target_relation_name
        )
    )
    join = f"JOIN {clause.target_binding_name}"
    if len(usable) == 1:
        relationship, (source_role, target_role) = usable[0]
        return ResolvedJoinRelationship(
            source=source,
            source_inferred=inferred,
            relationship=relationship.metadata.name,
            step=None,
            source_role=source_role,
            target_role=target_role,
            pairs=relationship.pairs(source_role),
        )
    if usable:
        return (
            _error(
                clause,
                f"{join} matches {len(usable)} relationship directions from "
                f"{source.name}: "
                + _and_list(
                    tuple(
                        _via(relationship, direction)
                        for relationship, direction in usable
                    )
                )
                + "; write one of them",
            ),
        )
    if related:
        if all(relationship.declaration_error for relationship in related):
            # A JOIN diagnostic is never caused by declaration errors alone.
            return ()
        return (
            _error(
                clause,
                f"{join}: no relationship from {source.name} to "
                f"{clause.target_relation_name} can be used: "
                + _and_list(
                    tuple(
                        f"{relationship.metadata.name} ({relationship.reason})"
                        for relationship in related
                    )
                ),
            ),
        )
    return (
        _error(
            clause,
            f"{join}: no relationship joins {source.name} to "
            f"{clause.target_relation_name}; declare one, or write `on`",
        ),
    )


def _several_sources(
    clause: JoinClause,
    candidates: tuple[JoinBindingView, ...],
    relationships: tuple[_Relationship, ...],
) -> Diagnostic:
    """Name every candidate binding with each usable direction, then each
    relationship it cannot use."""

    items: list[str] = []
    several = False
    for binding in candidates:
        related = tuple(
            relationship
            for relationship in relationships
            if relationship.relates(binding.relation.name, clause.target_relation_name)
        )
        directions = tuple(
            (relationship, direction)
            for relationship in related
            if relationship.reason is None
            for direction in relationship.directions(
                binding.relation.name, clause.target_relation_name
            )
        )
        several = several or len(directions) > 1
        items.extend(
            f"{binding.name} {_via(relationship, direction)}"
            for relationship, direction in directions
        )
        items.extend(
            f"{binding.name} relationship {relationship.metadata.name} "
            f"(cannot be used: {relationship.reason})"
            for relationship in related
            if relationship.reason is not None
        )
    return _error(
        clause,
        f"JOIN {clause.target_binding_name} matches relationships from "
        f"{len(candidates)} earlier bindings: {_and_list(tuple(items))}; write "
        "`from <binding>`" + (" and `via`" if several else ""),
    )


def _through_step(
    clause: JoinClause,
    step: JoinTraversalStep,
    visible: tuple[JoinBindingView, ...],
    written_source: JoinBindingView | None,
    relationships: tuple[_Relationship, ...],
) -> ResolvedJoinRelationship | tuple[Diagnostic, ...]:
    """A JOIN with one VIA step: the step and its path, then the source binding
    and whether the JOIN can use the relationship.

    A JOIN that omits its `from` or the step's roles names its cause at the
    JOIN, with the text an EXPLICIT_MODULES project gives; a JOIN that writes
    both keeps the single-file messages at the step and the JOIN.
    """

    name = step.relationship_name
    join = f"JOIN {clause.target_binding_name}"
    source_role, target_role = step.source_endpoint_role, step.target_endpoint_role
    inferred = written_source is None or source_role is None or target_role is None
    named = tuple(
        relationship
        for relationship in relationships
        if relationship.metadata.name == name
    )
    if len(named) > 1:
        # PIE-S2602 already reports the second declaration of the name.
        return ()
    if not named:
        if inferred:
            return (
                _error(
                    clause, f"{join}: `via {name}` names no relationship of this module"
                ),
            )
        return (_error(step, f"Unknown relationship in JOIN VIA: {name}"),)
    (relationship,) = named
    first, second = relationship.metadata.endpoints
    if source_role is not None and target_role is not None:
        if not relationship.admitted:
            # PIE-S2601 or PIE-S2603 already reports this relationship.
            return ()
        relations = {
            first.local_name: first.relation_name,
            second.local_name: second.relation_name,
        }
        unknown = [role for role in (source_role, target_role) if role not in relations]
        if unknown and inferred:
            missing = tuple(dict.fromkeys(unknown))
            return (
                _error(
                    clause,
                    f"{join}: relationship {name} has no endpoint "
                    f"role{'s' if len(missing) > 1 else ''} {_and_list(missing)}; "
                    f"its roles are {first.local_name} and {second.local_name}",
                ),
            )
        if unknown:
            return tuple(
                _error(step, f"Unknown endpoint role in JOIN VIA {name}: {role}")
                for role in unknown
            )
        if source_role == target_role and inferred:
            return (
                _error(
                    clause,
                    f"{join}: `via {name}: {source_role} -> {target_role}` names "
                    "one role as both source and target",
                ),
            )
        if source_role == target_role:
            return (
                _error(
                    step,
                    f"JOIN VIA {name} uses one endpoint role as both source and "
                    f"target: {source_role}",
                ),
            )
        start, end = relations[source_role], relations[target_role]
        problems: list[Diagnostic] = []
        if written_source is not None and start != written_source.relation.name:
            problems.append(
                _error(
                    clause,
                    f"JOIN VIA path starts at {start}, not at source binding "
                    f"{written_source.name} ({written_source.relation.name})",
                )
            )
        if end != clause.target_relation_name:
            ends_at = f"at {end}, not at the JOIN target {clause.target_relation_name}"
            problems.append(
                _error(
                    clause,
                    f"{join}: its VIA path ends {ends_at}"
                    if inferred
                    else f"JOIN VIA path ends {ends_at}",
                )
            )
        if problems:
            return tuple(problems)
    else:
        # The one direction of the relationship that ends at the target.
        ends = tuple(
            (head, tail)
            for head, tail in ((first, second), (second, first))
            if tail.relation_name == clause.target_relation_name
        )
        if len(ends) > 1:
            return (
                _error(
                    clause,
                    f"{join}: relationship {name} joins {first.relation_name} to "
                    f"itself; write `via {name}: {first.local_name} -> "
                    f"{second.local_name}` or `via {name}: {second.local_name} -> "
                    f"{first.local_name}`",
                ),
            )
        if not ends:
            joined = (
                f"{first.relation_name} to itself"
                if first.relation_name == second.relation_name
                else f"{first.relation_name} and {second.relation_name}"
            )
            return (
                _error(
                    clause,
                    f"{join}: `via {name}` joins {joined}, not "
                    f"{clause.target_relation_name}",
                ),
            )
        if not relationship.admitted:
            # PIE-S2601 or PIE-S2603 already reports this relationship.
            return ()
        ((head, tail),) = ends
        start = head.relation_name
        source_role, target_role = head.local_name, tail.local_name
    if relationship.declaration_error:
        # Its own PIE-S2604 already fails the file.
        return ()
    if relationship.derived is not None:
        return (_derived_relation(clause, relationship.derived),)
    if written_source is None:
        readers = tuple(
            binding for binding in visible if binding.relation.name == start
        )
        if not readers:
            return (
                _error(
                    clause,
                    f"{join}: `via {name}` starts at {start}, which no earlier "
                    "binding reads",
                ),
            )
        if len(readers) != 1:
            return (
                _error(
                    clause,
                    f"{join}: `via {name}` starts at {start}, which {len(readers)} "
                    "earlier bindings read: "
                    f"{_and_list(tuple(binding.name for binding in readers))}; "
                    "write `from <binding>`",
                ),
            )
        source, source_inferred = readers[0], True
    elif start != written_source.relation.name:
        # Only without roles: written roles had their path start checked above.
        return (
            _error(
                clause,
                f"{join}: its VIA path starts at {start}, not at its source binding "
                f"{written_source.name} ({written_source.relation.name})",
            ),
        )
    else:
        source, source_inferred = written_source, False
    if relationship.reason is not None:
        return (
            _error(
                clause,
                f"{join}: relationship {name} cannot be used: {relationship.reason}",
            ),
        )
    return ResolvedJoinRelationship(
        source=source,
        source_inferred=source_inferred,
        relationship=name,
        step=step,
        source_role=source_role,
        target_role=target_role,
        pairs=relationship.pairs(source_role),
    )


def _derived_relation(clause: JoinClause, relation: str) -> Diagnostic:
    """A relationship JOIN reads only sources in single files."""

    return _error(
        clause,
        "A relationship JOIN through a table or query is not available in single "
        f"files yet: JOIN {clause.target_binding_name} reads {relation}; write "
        "`from` and `on` instead.",
        code="PIE-S2334",
    )


def _via(relationship: _Relationship, direction: tuple[str, str]) -> str:
    """The `via` that writes one direction of a relationship."""

    return f"`via {relationship.metadata.name}: {direction[0]} -> {direction[1]}`"


def _conjuncts(expression: Expression) -> tuple[Expression, ...]:
    """The top-level `and` conjuncts in source order, without recursion."""

    conjuncts: list[Expression] = []
    pending = [expression]
    while pending:
        current = pending.pop()
        if type(current) is BinaryExpr and current.operator == "and":
            pending.extend((current.right, current.left))
        else:
            conjuncts.append(current)
    return tuple(conjuncts)


def _field_equality(
    expression: Expression,
) -> tuple[ComparisonExpr, DottedNameExpr, DottedNameExpr] | None:
    """An `a.x == b.y` conjunct and its two operands as written."""

    if type(expression) is not ComparisonExpr or expression.operator != "==":
        return None
    left, right = expression.left, expression.right
    if (
        type(left) is not DottedNameExpr
        or len(left.parts) != 2
        or type(right) is not DottedNameExpr
        or len(right.parts) != 2
    ):
        return None
    return expression, left, right


def _and_list(items: tuple[str, ...]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _or_list(items: tuple[str, ...]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} or {items[-1]}"


def _error(node: Node, message: str, *, code: str = "PIE-S2335") -> Diagnostic:
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
