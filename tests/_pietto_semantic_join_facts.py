"""Single-file JOIN facts for semantic tests of relationship resolution and
the fan-out rule.

They are built from one analyzed file the way the analyzer's JOIN phases read
it: the relationship context, each JOIN's visible earlier bindings and written
`from`, and a relation's resolved inputs, JOINs and field reads.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from pietto.ast_nodes import (
    AuthoredJoinKind,
    DottedNameExpr,
    Expression,
    JoinClause,
    NameExpr,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic
from pietto.parser_api import parse_source
from pietto.semantic import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    TypeKind,
    ValueType,
    analyze,
)
from pietto.semantic.aggregates import child_expressions
from pietto.semantic.join_fanout import join_fanout_diagnostics
from pietto.semantic.join_relationships import (
    JoinBindingView,
    JoinRelationshipContext,
    ResolvedJoinRelationship,
    resolve_join_relationship,
)
from pietto.semantic.model import (
    JoinEqualityInfo,
    JoinFieldRef,
    JoinInfo,
    JoinInputInfo,
    RelationJoinsInfo,
)

_HIDDEN = (AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI)
_UNKNOWN = ValueType(
    resolved_type=ResolvedType(name="Unknown", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
)


def join_mode(clause: JoinClause) -> str:
    """M1..M5 from the written parts of a JOIN: CROSS is M5; otherwise `on`
    with a `via` step is M4 and `on` alone M3, a `via` step alone M2, neither
    M1."""

    if clause.kind is AuthoredJoinKind.CROSS:
        return "M5"
    if clause.on_clause is not None:
        return "M4" if clause.traversal_steps else "M3"
    return "M2" if clause.traversal_steps else "M1"


@dataclass(frozen=True, slots=True)
class JoinScript:
    """One analyzed single file and its relationship context."""

    script: Script
    model: SemanticModel
    context: JoinRelationshipContext

    def relation(self, name: str) -> TableDef | QueryDef:
        definition = self.model.relation_symbols[name]
        assert isinstance(definition, (TableDef, QueryDef))
        return definition

    def visible(self, query: str, ordinal: int) -> tuple[JoinBindingView, ...]:
        """The bindings JOIN `ordinal` (1-based) can read its source from:
        FROM and the earlier targets other than SEMI and ANTI."""

        definition = self.relation(query)
        symbols = self.model.relation_symbols
        source = definition.from_clause.source_name
        views = [
            JoinBindingView(ordinal=0, name=source, relation=_row(symbols[source]))
        ]
        for position, clause in enumerate(definition.join_clauses[: ordinal - 1], 1):
            if clause.kind not in _HIDDEN:
                views.append(
                    JoinBindingView(
                        ordinal=position,
                        name=clause.target_binding_name,
                        relation=_row(symbols[clause.target_relation_name]),
                    )
                )
        return tuple(views)

    def resolve(
        self, query: str, ordinal: int
    ) -> ResolvedJoinRelationship | tuple[Diagnostic, ...]:
        """Resolve the relationship of JOIN `ordinal` with its written `from`."""

        clause = self.relation(query).join_clauses[ordinal - 1]
        visible = self.visible(query, ordinal)
        written = None
        if clause.source_binding_name is not None:
            (written,) = (
                view for view in visible if view.name == clause.source_binding_name
            )
        return resolve_join_relationship(
            clause,
            target=_row(self.model.relation_symbols[clause.target_relation_name]),
            visible=visible,
            written_source=written,
            context=self.context,
        )

    def joins_info(self, query: str) -> RelationJoinsInfo:
        """The resolved JOIN facts of a relation whose JOINs all resolve."""

        definition = self.relation(query)
        symbols = self.model.relation_symbols
        clauses = definition.join_clauses
        source = definition.from_clause.source_name
        inputs = (
            JoinInputInfo(
                ordinal=0,
                binding=source,
                relation=_row(symbols[source]),
                clause=None,
                visible=True,
            ),
            *(
                JoinInputInfo(
                    ordinal=position,
                    binding=clause.target_binding_name,
                    relation=_row(symbols[clause.target_relation_name]),
                    clause=clause,
                    visible=clause.kind not in _HIDDEN,
                )
                for position, clause in enumerate(clauses, 1)
            ),
        )
        joins: list[JoinInfo] = []
        for position, clause in enumerate(clauses, 1):
            mode = join_mode(clause)
            relationship = step = None
            equalities: tuple[JoinEqualityInfo, ...] = ()
            inferred = False
            if mode in ("M1", "M2", "M4"):
                resolved = self.resolve(query, position)
                assert isinstance(resolved, ResolvedJoinRelationship), resolved
                start = resolved.source.ordinal
                inferred = resolved.source_inferred
                relationship, step = resolved.relationship, resolved.step
                equalities = tuple(
                    JoinEqualityInfo(
                        left=JoinFieldRef(input=start, field=left),
                        right=JoinFieldRef(input=position, field=right),
                        left_type=self._field_type(inputs[start], left),
                        right_type=self._field_type(inputs[position], right),
                        comparison=comparison,
                        left_operand=left_operand,
                        right_operand=right_operand,
                    )
                    for left, right, comparison, left_operand, right_operand in (
                        resolved.pairs
                    )
                )
            else:
                (view,) = (
                    view
                    for view in self.visible(query, position)
                    if view.name == clause.source_binding_name
                )
                start = view.ordinal
            joins.append(
                JoinInfo(
                    ordinal=position,
                    clause=clause,
                    kind=clause.kind,
                    mode=mode,
                    source_input=start,
                    source_inferred=inferred,
                    target_input=position,
                    relationship=relationship,
                    step=step,
                    equalities=equalities,
                    condition=(
                        None
                        if clause.on_clause is None
                        else clause.on_clause.expression
                    ),
                    null_extends=_null_extends(clauses, position),
                )
            )
        tail = [item for item in inputs if item.visible]
        reads: dict[Expression, JoinFieldRef] = {}
        tail_expressions: list[Expression] = [
            item.expression for item in definition.select_items
        ]
        if definition.let_clause is not None:
            tail_expressions.extend(
                binding.expression for binding in definition.let_clause.bindings
            )
        if definition.where_clause is not None:
            tail_expressions.append(definition.where_clause.expression)
        if definition.group_by_clause is not None:
            tail_expressions.extend(
                item.key for item in definition.group_by_clause.items
            )
        if (
            definition.order_by_clause is not None
            and definition.group_by_clause is None
        ):
            tail_expressions.extend(
                item.expression for item in definition.order_by_clause.items
            )
        for expression in tail_expressions:
            self._read(expression, tail, reads)
        for position, clause in enumerate(clauses, 1):
            if clause.on_clause is not None:
                scope = [item for item in inputs[:position] if item.visible]
                self._read(
                    clause.on_clause.expression, [*scope, inputs[position]], reads
                )
        fields = {
            f"{item.binding}.{name}": RowField(
                name=f"{item.binding}.{name}",
                resolved_type=field.resolved_type,
                nullability=field.nullability,
                definition=field.definition,
            )
            for item in tail
            for name, field in self._schema(item).fields.items()
        }
        return RelationJoinsInfo(
            inputs=inputs,
            joins=tuple(joins),
            row_schema=RowSchema(fields=fields, joined=True),
            field_reads=reads,
        )

    def fanout(self, query: str) -> tuple[Diagnostic, ...]:
        """Run the fan-out rule over a relation's resolved JOIN facts."""

        definition = self.relation(query)
        lets: Mapping[str, Expression] = (
            {}
            if definition.let_clause is None
            else {
                binding.name: binding.expression
                for binding in definition.let_clause.bindings
            }
        )
        return join_fanout_diagnostics(
            definition,
            self.joins_info(query),
            type_symbols=self.model.type_symbols,
            source_row_schemas=self.model.source_row_schemas,
            let_expressions=lets,
        )

    def _schema(self, item: JoinInputInfo) -> RowSchema:
        relation = item.relation
        if isinstance(relation, SourceDef):
            return self.model.source_row_schemas[relation]
        return self.model.relation_row_schemas.get(relation, RowSchema(is_unknown=True))

    def _field_type(self, item: JoinInputInfo, name: str) -> ValueType:
        field = self._schema(item).fields.get(name)
        if field is None:
            return _UNKNOWN
        return ValueType(
            resolved_type=field.resolved_type, nullability=field.nullability
        )

    def _read(
        self,
        expression: Expression,
        scope: list[JoinInputInfo],
        reads: dict[Expression, JoinFieldRef],
    ) -> None:
        """Record each field leaf that names exactly one field of the scope."""

        pending = [expression]
        while pending:
            node = pending.pop()
            if isinstance(node, DottedNameExpr) and len(node.parts) == 2:
                binding, name = node.parts
                found = [
                    item
                    for item in scope
                    if item.binding == binding and name in self._schema(item).fields
                ]
            elif isinstance(node, NameExpr):
                name = node.name
                found = [item for item in scope if name in self._schema(item).fields]
            else:
                pending.extend(child_expressions(node))
                continue
            if len(found) == 1:
                reads[node] = JoinFieldRef(input=found[0].ordinal, field=name)


def join_script(source: str, *, path: str = "joins.pietto") -> JoinScript:
    """Parse and analyze `source` and build its relationship context."""

    parsed = parse_source(source, path=path)
    assert parsed.ast is not None, parsed.diagnostics
    semantic = analyze(parsed.ast)
    script = semantic.script
    assert script is not None
    model = semantic.model
    return JoinScript(
        script=script,
        model=model,
        context=JoinRelationshipContext(
            relationships=script.relationships,
            admitted=model.relationships,
            relation_symbols=model.relation_symbols,
            source_row_schemas=model.source_row_schemas,
            type_expansions=model.type_expansions,
        ),
    )


def located(
    diagnostics: tuple[Diagnostic, ...],
) -> list[tuple[str, str, int, int]]:
    return [
        (item.code, item.message, item.location.line, item.location.column)
        for item in diagnostics
    ]


def _row(definition: object) -> SourceDef | TableDef | QueryDef:
    assert isinstance(definition, (SourceDef, TableDef, QueryDef))
    return definition


def _null_extends(clauses: tuple[JoinClause, ...], position: int) -> tuple[int, ...]:
    """The inputs a JOIN NULL-extends: LEFT its target, RIGHT the row inputs
    before it, FULL both."""

    kind = clauses[position - 1].kind
    earlier = tuple(
        ordinal
        for ordinal in range(position)
        if ordinal == 0 or clauses[ordinal - 1].kind not in _HIDDEN
    )
    if kind is AuthoredJoinKind.LEFT:
        return (position,)
    if kind is AuthoredJoinKind.RIGHT:
        return earlier
    if kind is AuthoredJoinKind.FULL:
        return (*earlier, position)
    return ()
