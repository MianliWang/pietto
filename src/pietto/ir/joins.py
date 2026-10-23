"""Lowering of single-file JOIN facts into relation IR.

Private: nothing here is exported. The IR builder calls it for tables and
queries with JOIN clauses; join-free relations never reach it.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass

from pietto.ast_nodes import (
    AuthoredJoinKind,
    DottedNameExpr,
    Expression,
    NameExpr,
    Node,
    QueryDef,
    TableDef,
    WindowExpr,
)
from pietto.ir.lowering import lower_span, lower_value_type
from pietto.ir.model import (
    ExpressionIR,
    FieldId,
    FieldRefIR,
    JoinEqualityIR,
    JoinHopIR,
    JoinIR,
    JoinKindIR,
    RelationInputIR,
    RelationInputRoleIR,
    SourceSpan,
    SymbolId,
    SymbolNamespace,
    TypeRefIR,
)
from pietto.semantic import RowSchema, SemanticModel, ValueType
from pietto.semantic.model import (
    JoinEqualityInfo,
    JoinFieldRef,
    JoinInfo,
    RelationJoinsInfo,
)

__all__ = ()


class JoinLoweringError(Exception):
    """A JOIN fact that IR lowering cannot use; reported as PIE-I1000 at ``node``."""

    def __init__(self, node: Node, message: str) -> None:
        super().__init__(message)
        self.node = node
        self.message = message


def join_relation_facts(
    definition: TableDef | QueryDef,
    semantic_model: SemanticModel,
) -> RelationJoinsInfo | None:
    """The JOIN facts ``definition`` lowers from; None without JOIN clauses.

    Windows fail before the facts are looked up, because a relation that
    failed check for them has none. Then facts that are missing, or that do
    not describe the relation's JOIN clauses, fail at the first JOIN.
    """

    if not definition.join_clauses:
        return None
    window = _first_window(definition)
    if window is not None:
        raise JoinLoweringError(window, "window over JOIN rows")
    info = semantic_model.relation_joins.get(definition)
    if info is None or not _facts_describe(definition, info):
        raise JoinLoweringError(definition.join_clauses[0], "resolved JOIN facts")
    return info


def lower_join_inputs(
    definition: TableDef | QueryDef,
    info: RelationJoinsInfo,
) -> tuple[RelationInputIR, ...]:
    """The FROM input, at the FROM clause like ``RelationIR.source``, then each
    JOIN target at its JOIN clause."""

    return tuple(
        RelationInputIR(
            ordinal=item.ordinal,
            role=(
                RelationInputRoleIR.FROM
                if item.clause is None
                else RelationInputRoleIR.TARGET
            ),
            target=SymbolId(SymbolNamespace.RELATION, item.relation.name),
            binding=item.binding,
            visible=item.visible,
            span=lower_span(
                definition.from_clause.span if item.clause is None else item.clause.span
            ),
        )
        for item in info.inputs
    )


@dataclass(frozen=True, slots=True)
class JoinReads:
    """The resolved field reads of one JOIN relation and the inputs they name."""

    inputs: tuple[RelationInputIR, ...]
    field_reads: Mapping[Expression, JoinFieldRef]

    def field_ref(
        self,
        expression: NameExpr | DottedNameExpr,
        *,
        span: SourceSpan,
        value_type: TypeRefIR,
    ) -> FieldRefIR:
        """The read ``expression`` as its input's field, qualified by the
        input's binding; a read without a resolution fails at the read."""

        reference = self.field_reads.get(expression)
        if reference is None:
            raise JoinLoweringError(expression, "resolved JOIN field read")
        return _field_ref(self.inputs, reference, span=span, value_type=value_type)

    def field_id(self, expression: NameExpr | DottedNameExpr) -> FieldId:
        """Resolve a field occurrence without losing its input identity."""

        reference = self.field_reads.get(expression)
        if reference is None:
            raise JoinLoweringError(expression, "resolved JOIN field read")
        return FieldId(
            owner=self.inputs[reference.input].target,
            name=reference.field,
            input=reference.input,
        )

    def group_key_ref(
        self,
        expression: NameExpr | DottedNameExpr,
        semantic_model: SemanticModel,
        *,
        row_schema: RowSchema,
    ) -> FieldRefIR:
        """Lower a resolved group key using the joined tail row's type."""

        identity = self.field_id(expression)
        assert identity.input is not None
        binding = self.inputs[identity.input].binding
        field = row_schema.fields.get(f"{binding}.{identity.name}")
        if field is None:
            raise JoinLoweringError(expression, "resolved JOIN field read")
        return self.field_ref(
            expression,
            span=lower_span(expression.span),
            value_type=lower_value_type(
                ValueType(
                    resolved_type=field.resolved_type, nullability=field.nullability
                ),
                semantic_model,
            ),
        )


def lower_joins(
    info: RelationJoinsInfo,
    reads: JoinReads,
    semantic_model: SemanticModel,
    *,
    lower_condition: Callable[[Expression], ExpressionIR],
) -> tuple[JoinIR, ...]:
    """Each JOIN in source order, with its relationship hop and its ``on``."""

    return tuple(
        _lower_join(join, reads, semantic_model, lower_condition) for join in info.joins
    )


@contextmanager
def report_join_invariants(definition: TableDef | QueryDef) -> Iterator[None]:
    """Turn a ``RelationIR`` invariant that a JOIN relation breaks into a
    lowering error at its first JOIN; other ``ValueError``s pass unchanged."""

    try:
        yield
    except ValueError as error:
        if not definition.join_clauses:
            raise
        raise JoinLoweringError(
            definition.join_clauses[0], f"JOIN invariant: {error}"
        ) from error


def _facts_describe(definition: TableDef | QueryDef, info: RelationJoinsInfo) -> bool:
    """Whether the facts hold one target input and one JOIN per JOIN clause, in
    order, with the clause's target, kind and ``on``, a relationship hop
    exactly for a relationship JOIN, and field references to these inputs only.

    A JOIN, an ``on`` or a hop that the facts left out would otherwise be
    left out of the SQL.
    """

    clauses = definition.join_clauses
    if len(info.joins) != len(clauses) or len(info.inputs) != len(clauses) + 1:
        return False
    for item, join, clause in zip(info.inputs[1:], info.joins, clauses):
        uses_relationship = bool(clause.traversal_steps) or (
            clause.on_clause is None and clause.kind is not AuthoredJoinKind.CROSS
        )
        if (
            item.clause != clause
            or join.clause != clause
            or item.relation.name != clause.target_relation_name
            or item.binding != clause.target_binding_name
            or join.kind != clause.kind
            or join.condition
            != (None if clause.on_clause is None else clause.on_clause.expression)
            or (join.relationship is not None) != uses_relationship
            or bool(join.equalities) != uses_relationship
        ):
            return False
    ordinals = range(len(info.inputs))
    references = (
        *info.field_reads.values(),
        *(
            reference
            for join in info.joins
            for equality in join.equalities
            for reference in (equality.left, equality.right)
        ),
    )
    return all(reference.input in ordinals for reference in references)


def _first_window(definition: TableDef | QueryDef) -> Node | None:
    """The first selected window call, else the first named window."""

    for item in definition.select_items:
        if type(item.expression) is WindowExpr:
            return item.expression
    return definition.named_windows[0] if definition.named_windows else None


def _lower_join(
    join: JoinInfo,
    reads: JoinReads,
    semantic_model: SemanticModel,
    lower_condition: Callable[[Expression], ExpressionIR],
) -> JoinIR:
    hops: tuple[JoinHopIR, ...] = ()
    if join.relationship is not None:
        hops = (
            JoinHopIR(
                relationship=join.relationship,
                left_input=join.source_input,
                right_input=join.target_input,
                equalities=tuple(
                    _lower_equality(equality, reads, semantic_model)
                    for equality in join.equalities
                ),
                span=lower_span((join.clause if join.step is None else join.step).span),
            ),
        )
    return JoinIR(
        ordinal=join.ordinal,
        kind=JoinKindIR(join.kind.value),
        source_input=join.source_input,
        source_inferred=join.source_inferred,
        target_input=join.target_input,
        hops=hops,
        condition=None if join.condition is None else lower_condition(join.condition),
        null_extends=join.null_extends,
        span=lower_span(join.clause.span),
    )


def _lower_equality(
    equality: JoinEqualityInfo,
    reads: JoinReads,
    semantic_model: SemanticModel,
) -> JoinEqualityIR:
    """Source side first: the roles decided which conjunct operand that is,
    so the sides come from the oriented facts, never from the comparison."""

    return JoinEqualityIR(
        left=_field_ref(
            reads.inputs,
            equality.left,
            span=lower_span(equality.left_operand.span),
            value_type=lower_value_type(equality.left_type, semantic_model),
        ),
        right=_field_ref(
            reads.inputs,
            equality.right,
            span=lower_span(equality.right_operand.span),
            value_type=lower_value_type(equality.right_type, semantic_model),
        ),
    )


def _field_ref(
    inputs: tuple[RelationInputIR, ...],
    reference: JoinFieldRef,
    *,
    span: SourceSpan,
    value_type: TypeRefIR,
) -> FieldRefIR:
    item = inputs[reference.input]
    return FieldRefIR(
        span=span,
        value_type=value_type,
        name=reference.field,
        qualifier=(item.binding,),
        field=FieldId(owner=item.target, name=reference.field, input=reference.input),
    )
