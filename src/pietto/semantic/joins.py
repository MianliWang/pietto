"""Single-file JOIN analysis: inputs, joined rows, reads and JOIN-local ON.

Private: nothing here is exported. It reads only the AST, diagnostics and
semantic facts, never project code.

`build_join_structures` checks the written parts of every JOIN and resolves
the inputs of each table or query with JOINs before relation typing. A
relation it admits has a structure, and its clauses read the joined row
that `join_input_row` builds from the rows of its inputs; `join_rows` also
gives each `on` its row. After typing, `check_join_semantics` resolves
every field read, types each JOIN-local `on` and builds the facts of each
relation without a JOIN error, and `join_post_pass` leaves one diagnostic
at each read that fails.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass

from pietto._flat_relational_admission import (
    _EXPLICIT_MODULES,
    availability_diagnostic,
)
from pietto.ast_nodes import (
    AuthoredJoinKind,
    BinaryExpr,
    ComparisonExpr,
    Definition,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    JoinClause,
    NameExpr,
    QueryDef,
    Script,
    SourceDef,
    Span,
    TableDef,
    TypeExpr,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    child_expressions,
    contains_semantic_aggregate,
    first_semantic_aggregate_call,
)
from pietto.semantic.expressions import _UNKNOWN_VALUE_TYPE, infer_row_expression
from pietto.semantic.join_relationships import (
    JoinBindingView,
    JoinRelationshipContext,
    ResolvedJoinRelationship,
    resolve_join_relationship,
)
from pietto.semantic.model import (
    EffectiveNullability,
    JoinEqualityInfo,
    JoinFieldRef,
    JoinInfo,
    JoinInputInfo,
    RelationJoinsInfo,
    RelationshipSemanticInfo,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.predicate_checks import _check_bool_expression
from pietto.semantic.relations import (
    _HIDING_KINDS,
    join_target,
    written_join_source,
)

__all__ = ()

RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef

# The modes whose JOIN reads a relationship.
_RELATIONSHIP_MODES = frozenset({"M1", "M2", "M4"})


@dataclass(frozen=True, slots=True)
class StructuredJoin:
    """One JOIN of a structured relation, as its written parts resolved."""

    ordinal: int  # 1-based, source order; also its target's input ordinal
    clause: JoinClause
    mode: str  # "M1" | "M2" | "M3" | "M4" | "M5"
    source_input: int
    source_inferred: bool
    relationship: ResolvedJoinRelationship | None  # M1, M2 and M4


@dataclass(frozen=True, slots=True)
class JoinStructure:
    """The resolved inputs and JOINs of one table or query, before typing."""

    inputs: tuple[JoinInputInfo, ...]
    joins: tuple[StructuredJoin, ...]


@dataclass(frozen=True, slots=True)
class JoinRows:
    """The joined rows a structured relation reads.

    ``tail`` is the row of its other clauses: the bindings visible after its
    last JOIN with their final nullability. ``on[k - 1]`` is the row of the
    `on` of JOIN k: the bindings visible before it, nullable as the JOINs
    before it leave them, then its target as its own row has it.
    """

    tail: RowSchema
    on: tuple[RowSchema, ...]


@dataclass(frozen=True, slots=True)
class JoinChecks:
    """What `check_join_semantics` found, for the model and `join_post_pass`.

    ``facts`` are those of the relations without a JOIN error;
    ``diagnostics`` are those of typing each JOIN-local `on`; ``reads`` give
    each failed read's one diagnostic, first per location; PIE-S2102 and
    PIE-S2380 inside each span of ``unanalysed`` go; and each ``unexplained``
    diagnostic is reported unless an ERROR lies inside one of its spans.
    """

    facts: Mapping[DerivedRelation, RelationJoinsInfo]
    diagnostics: tuple[Diagnostic, ...]
    reads: tuple[Diagnostic, ...]
    unanalysed: tuple[Span, ...]
    unexplained: tuple[tuple[Diagnostic, tuple[Span, ...]], ...]


def build_join_structures(
    script: Script,
    *,
    relation_symbols: Mapping[str, Definition],
    relationships: tuple[RelationshipSemanticInfo, ...],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    type_expansions: Mapping[TypeExpr, ResolvedType],
) -> tuple[
    dict[DerivedRelation, JoinStructure],
    dict[JoinClause, RelationDefinition],
    list[Diagnostic],
]:
    """Check every JOIN's written parts and resolve each JOIN relation.

    Each JOIN, in source order: its target; an input whose fields are not
    known; its binding name; its combination of kind, `via` and `on`; its
    written `from`; then the relationship it reads. Then the relation's
    windows and ORDER BY after an ungrouped aggregate. A relation gets a structure unless
    one of these reports an error, its FROM input names no relation (an
    error of its own) or the declaration errors of the relationship a JOIN
    would read decide that JOIN without a diagnostic of its own.

    The middle result maps every JOIN whose target is a source, table or
    query to it, in every relation, with a structure or not: the edges the
    relation cycles follow beside FROM.
    """

    context = JoinRelationshipContext(
        relationships=script.relationships,
        admitted=relationships,
        relation_symbols=relation_symbols,
        source_row_schemas=source_row_schemas,
        type_expansions=type_expansions,
    )
    structures: dict[DerivedRelation, JoinStructure] = {}
    targets: dict[JoinClause, RelationDefinition] = {}
    diagnostics: list[Diagnostic] = []
    for definition in script.definitions:
        if (
            not isinstance(definition, (TableDef, QueryDef))
            or not definition.join_clauses
        ):
            continue
        found: list[Diagnostic] = []
        structure = _structure(definition, relation_symbols, context, found, targets)
        found.extend(_window_diagnostics(definition))
        found.extend(_grouping_diagnostics(definition))
        diagnostics.extend(found)
        if structure is not None and not found:
            structures[definition] = structure
    return structures, targets, diagnostics


def _structure(
    definition: DerivedRelation,
    relation_symbols: Mapping[str, Definition],
    context: JoinRelationshipContext,
    found: list[Diagnostic],
    targets: dict[JoinClause, RelationDefinition],
) -> JoinStructure | None:
    """Check each JOIN of one relation into ``found`` and each target it
    resolves into ``targets``; its structure when every JOIN resolved."""

    from_name = definition.from_clause.source_name
    from_relation = relation_symbols.get(from_name)
    # A FROM input that names no relation already has its own error.
    inputs: list[JoinInputInfo | None] = [
        JoinInputInfo(
            ordinal=0,
            binding=from_name,
            relation=from_relation,
            clause=None,
            visible=True,
        )
        if isinstance(from_relation, (SourceDef, TableDef, QueryDef))
        else None
    ]
    joins: list[StructuredJoin] = []
    for ordinal, clause in enumerate(definition.join_clauses, start=1):
        target = join_target(clause, relation_symbols)
        opened: list[Diagnostic | None] = []
        if isinstance(target, Diagnostic):
            found.append(target)
            inputs.append(None)
        else:
            targets[clause] = target
            inputs.append(
                JoinInputInfo(
                    ordinal=ordinal,
                    binding=clause.target_binding_name,
                    relation=target,
                    clause=clause,
                    visible=clause.kind not in _HIDING_KINDS,
                )
            )
            first = inputs[0]
            if ordinal == 1 and first is not None:
                opened.append(
                    _unknown_fields_diagnostic(
                        clause, first.relation, from_name, relation_symbols
                    )
                )
            opened.append(
                _unknown_fields_diagnostic(
                    clause, target, clause.target_relation_name, relation_symbols
                )
            )
            # A self-join of a source without a shape says so for each input.
            found.extend(item for item in opened if item is not None)
        named = _binding_name_diagnostic(definition, ordinal)
        combined = _combination_diagnostic(clause)
        found.extend(item for item in (named, combined) if item is not None)
        if isinstance(target, Diagnostic):
            continue
        written = (
            None
            if clause.source_binding_name is None
            else written_join_source(definition, ordinal - 1, hidden_bindings=True)
        )
        if isinstance(written, Diagnostic):
            found.append(written)
        if any(opened) or combined is not None or isinstance(written, Diagnostic):
            continue
        mode = _join_mode(clause)
        if mode not in _RELATIONSHIP_MODES:
            # `on` and CROSS require a written `from` before analysis.
            if written is not None:
                joins.append(
                    StructuredJoin(
                        ordinal=ordinal,
                        clause=clause,
                        mode=mode,
                        source_input=written,
                        source_inferred=False,
                        relationship=None,
                    )
                )
            continue
        earlier = [inputs[index] for index in _visible_before(definition, ordinal)]
        views = tuple(
            JoinBindingView(
                ordinal=item.ordinal, name=item.binding, relation=item.relation
            )
            for item in earlier
            if item is not None
        )
        if written is None:
            written_view = None
            unresolved = len(views) < len(earlier)
        else:
            written_view = next(
                (view for view in views if view.ordinal == written), None
            )
            unresolved = written_view is None
        if unresolved:
            # The binding the JOIN starts from, or without `from` one it may
            # start from, reads no relation: an earlier error fails the
            # relation already.
            continue
        resolved = resolve_join_relationship(
            clause,
            target=target,
            visible=views,
            written_source=written_view,
            context=context,
        )
        if isinstance(resolved, tuple):
            # An empty result: a relationship's own declaration errors decide
            # the JOIN, and they fail the file already.
            found.extend(resolved)
            continue
        joins.append(
            StructuredJoin(
                ordinal=ordinal,
                clause=clause,
                mode=mode,
                source_input=resolved.source.ordinal,
                source_inferred=resolved.source_inferred,
                relationship=resolved,
            )
        )
    complete = tuple(item for item in inputs if item is not None)
    if len(joins) != len(definition.join_clauses) or len(complete) != len(inputs):
        return None
    return JoinStructure(inputs=complete, joins=tuple(joins))


def _visible_before(definition: DerivedRelation, ordinal: int) -> tuple[int, ...]:
    """The inputs JOIN ``ordinal`` sees: the FROM input and every earlier JOIN
    target but a SEMI or ANTI one."""

    return (0,) + tuple(
        index
        for index, clause in enumerate(definition.join_clauses[: ordinal - 1], start=1)
        if clause.kind not in _HIDING_KINDS
    )


def _join_mode(clause: JoinClause) -> str:
    """Classify a JOIN by its written parts: CROSS is M5; otherwise `on` with
    a `via` step is M4 and `on` alone M3, a `via` step alone M2, neither M1."""

    if clause.kind is AuthoredJoinKind.CROSS:
        return "M5"
    if clause.on_clause is not None:
        return "M4" if clause.traversal_steps else "M3"
    return "M2" if clause.traversal_steps else "M1"


def _unknown_fields_diagnostic(
    clause: JoinClause,
    relation: RelationDefinition,
    name: str,
    relation_symbols: Mapping[str, Definition],
) -> Diagnostic | None:
    """Refuse a JOIN input whose fields are not known: a source without a
    shape, or a table or query that reads one."""

    root = next(
        (
            item
            for item in _reads(relation, relation_symbols)
            if isinstance(item, SourceDef) and item.shape_name is None
        ),
        None,
    )
    if root is None:
        return None
    return availability_diagnostic(
        clause.span,
        f"A JOIN over {name}, whose fields are not known, is not available "
        f"in single files yet; give source {root.name} a shape.",
    )


def _reads(
    relation: RelationDefinition,
    relation_symbols: Mapping[str, Definition],
) -> Iterator[RelationDefinition]:
    """``relation``, then every relation it reads through FROM inputs and JOIN
    targets, transitively, depth first in source order."""

    pending = [relation]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        if isinstance(current, SourceDef):
            continue
        names = (
            current.from_clause.source_name,
            *(clause.target_relation_name for clause in current.join_clauses),
        )
        reads = [relation_symbols.get(name) for name in reversed(names)]
        pending.extend(
            item for item in reads if isinstance(item, (SourceDef, TableDef, QueryDef))
        )


def _binding_name_diagnostic(
    definition: DerivedRelation, ordinal: int
) -> Diagnostic | None:
    """Refuse a JOIN binding named like the FROM input or an earlier JOIN
    binding, SEMI and ANTI ones included, at its `as` name."""

    clause = definition.join_clauses[ordinal - 1]
    name = clause.target_binding_name
    if name == definition.from_clause.source_name:
        message = f"JOIN binding cannot have the FROM input's name: {name}"
    elif any(
        item.target_binding_name == name
        for item in definition.join_clauses[: ordinal - 1]
    ):
        message = f"Duplicate JOIN binding name: {name}"
    else:
        return None
    return _diagnostic(clause.target_binding_span or clause.span, "PIE-S2335", message)


def _combination_diagnostic(clause: JoinClause) -> Diagnostic | None:
    """Refuse a JOIN kind with `on` or `via` steps it cannot have
    (PIE-S2336), then any other JOIN with more than one `via` step."""

    steps = clause.traversal_steps
    if clause.kind is AuthoredJoinKind.CROSS and (
        clause.on_clause is not None or steps
    ):
        message = "CROSS JOIN cannot have ON or VIA."
    elif len(steps) <= 1:
        return None
    elif clause.on_clause is not None:
        message = "JOIN-local ON refinement requires exactly one VIA step."
    elif clause.kind not in {AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT}:
        message = "This JOIN kind requires a direct binary input."
    else:
        return availability_diagnostic(
            clause.span,
            "A JOIN with more than one `via` step is available only when "
            f"{_EXPLICIT_MODULES} completes it.",
        )
    return _diagnostic(clause.span, "PIE-S2336", message)


def _window_diagnostics(definition: DerivedRelation) -> tuple[Diagnostic, ...]:
    """Refuse each window call that is a whole `select` item and each named
    window of a relation with JOINs."""

    message = (
        "Window functions over JOIN rows are available only when "
        f"{_EXPLICIT_MODULES} completes them."
    )
    return tuple(
        availability_diagnostic(span, message)
        for span in (
            *(
                item.expression.span
                for item in definition.select_items
                if type(item.expression) is WindowExpr
            ),
            *(declaration.span for declaration in definition.named_windows),
        )
    )


def _grouping_diagnostics(definition: DerivedRelation) -> tuple[Diagnostic, ...]:
    """Refuse ORDER BY after an ungrouped aggregate over JOIN rows."""

    if (
        definition.group_by_clause is not None
        or definition.order_by_clause is None
        or not any(
            first_semantic_aggregate_call(item.expression) is not None
            for item in definition.select_items
        )
    ):
        return ()
    return (
        availability_diagnostic(
            definition.order_by_clause.span,
            "ORDER BY is not available after an ungrouped aggregate over JOIN rows: "
            "the result has one row; remove `order by`.",
        ),
    )


def join_rows(
    structure: JoinStructure,
    schema_of: Callable[[RelationDefinition], RowSchema],
) -> JoinRows | None:
    """Build the joined rows of a structured relation from the row each of
    its inputs has; None when one of those rows is unknown.

    Keys are ``"<binding>.<field>"`` in input order, then field order. A
    LEFT JOIN makes its target nullable, a RIGHT JOIN every earlier input
    the rows read, a FULL JOIN both, and nothing clears that. An INNER JOIN
    makes non-null each field its relationship equalities read and each
    field that a top-level `and` conjunct of its `on` reads as itself, as an
    operand of a comparison or in `is not null`, where the field read has
    exactly one binding in its `on` row.
    """

    schemas = _input_schemas(structure, schema_of)
    return None if schemas is None else _joined_rows(structure, schemas, on=True)


def join_input_row(
    structure: JoinStructure,
    schema_of: Callable[[RelationDefinition], RowSchema],
) -> RowSchema:
    """The row a structured relation's clauses other than `on` read: its
    joined tail row, or an unknown row when an input's row is unknown.

    It builds no `on` row, so its cost follows the size of this relation.
    """

    schemas = _input_schemas(structure, schema_of)
    if schemas is None:
        return RowSchema(is_unknown=True)
    return _joined_rows(structure, schemas, on=False).tail


def joined_input_rows(
    definitions: Iterable[Definition],
    structures: Mapping[DerivedRelation, JoinStructure],
    *,
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
) -> dict[DerivedRelation, RowSchema]:
    """The input row of each table or query with JOINs among ``definitions``:
    its joined row when it has a structure, else an unknown row.

    Only the given definitions are built, so a caller that types one
    relation passes that relation alone.
    """

    def schema_of(relation: RelationDefinition) -> RowSchema:
        if isinstance(relation, SourceDef):
            return source_row_schemas[relation]
        return relation_row_schemas[relation]

    return {
        definition: (
            join_input_row(structures[definition], schema_of)
            if definition in structures
            else RowSchema(is_unknown=True)
        )
        for definition in definitions
        if isinstance(definition, (TableDef, QueryDef)) and definition.join_clauses
    }


def _input_schemas(
    structure: JoinStructure,
    schema_of: Callable[[RelationDefinition], RowSchema],
) -> tuple[RowSchema, ...] | None:
    """The row of each input, in input order; None when one is unknown."""

    schemas = tuple(schema_of(item.relation) for item in structure.inputs)
    return None if any(schema.is_unknown for schema in schemas) else schemas


def _joined_rows(
    structure: JoinStructure, schemas: tuple[RowSchema, ...], *, on: bool
) -> JoinRows:
    """The tail row, and with ``on`` each JOIN's `on` row.

    One walk over the JOINs keeps what they did so far: the inputs they
    null-extended and the fields INNER JOINs proved. A field is nullable
    when its input is null-extended, else non-null when it is proved, else
    as its input's row has it. Rows are built only where they are returned,
    so the walk costs no more than the rows themselves.
    """

    inputs = _Inputs.of(structure, schemas)
    extended: set[int] = set()
    proven: set[tuple[int, str]] = set()
    scope = [0]
    on_rows: list[RowSchema] = []

    def row(ordinals: Iterable[int]) -> RowSchema:
        fields: dict[str, RowField] = {}
        for ordinal in ordinals:
            binding = structure.inputs[ordinal].binding
            for name, field in schemas[ordinal].fields.items():
                key = f"{binding}.{name}"
                fields[key] = RowField(
                    name=key,
                    resolved_type=field.resolved_type,
                    nullability=(
                        EffectiveNullability.NULLABLE
                        if ordinal in extended
                        else EffectiveNullability.NON_NULL
                        if (ordinal, name) in proven
                        else field.nullability
                    ),
                    definition=field.definition,
                )
        return RowSchema(fields=fields, joined=True)

    for join in structure.joins:
        target = join.ordinal
        kind = join.clause.kind
        if on:
            on_rows.append(row((*scope, target)))
        extended.update(_null_extends(kind, target, scope))
        if kind is AuthoredJoinKind.INNER:
            proven.update(_null_proofs(join, inputs))
        if kind not in _HIDING_KINDS:
            scope.append(target)
    return JoinRows(tail=row(scope), on=tuple(on_rows))


@dataclass(frozen=True, slots=True)
class _Inputs:
    """The inputs of one structured relation, found by binding and by field."""

    infos: tuple[JoinInputInfo, ...]
    schemas: tuple[RowSchema, ...]
    ordinals: Mapping[str, int]  # binding -> input; bindings are unique
    owners: Mapping[str, tuple[int, ...]]  # field -> the inputs with it, in order

    @classmethod
    def of(cls, structure: JoinStructure, schemas: tuple[RowSchema, ...]) -> _Inputs:
        owners: dict[str, list[int]] = {}
        for ordinal, schema in enumerate(schemas):
            for name in schema.fields:
                owners.setdefault(name, []).append(ordinal)
        return cls(
            infos=structure.inputs,
            schemas=schemas,
            ordinals={item.binding: item.ordinal for item in structure.inputs},
            owners={name: tuple(found) for name, found in owners.items()},
        )

    def readable(self, ordinal: int, join: int | None) -> bool:
        """Whether a read sees input ``ordinal``: in the `on` of JOIN
        ``join``, a visible input before it or its own target; elsewhere
        (``join`` None), a visible input."""

        if ordinal == join:
            return True
        visible = self.infos[ordinal].visible
        return visible if join is None else visible and ordinal < join


def _null_extends(
    kind: AuthoredJoinKind, target: int, earlier: Sequence[int]
) -> tuple[int, ...]:
    """The inputs a JOIN makes nullable, ascending: ``earlier`` are the inputs
    the rows read before it."""

    if kind is AuthoredJoinKind.LEFT:
        return (target,)
    if kind is AuthoredJoinKind.RIGHT:
        return tuple(earlier)
    if kind is AuthoredJoinKind.FULL:
        return (*earlier, target)
    return ()


def _null_proofs(join: StructuredJoin, inputs: _Inputs) -> set[tuple[int, str]]:
    """The fields an INNER JOIN's matched rows hold non-null values for."""

    proven: set[tuple[int, str]] = set()
    if join.relationship is not None:
        for source_field, target_field, *_ in join.relationship.pairs:
            proven.add((join.source_input, source_field))
            proven.add((join.ordinal, target_field))
    if join.clause.on_clause is not None:
        for conjunct in _conjuncts(join.clause.on_clause.expression):
            if type(conjunct) is ComparisonExpr:
                operands: tuple[Expression, ...] = (conjunct.left, conjunct.right)
            elif type(conjunct) is IsNullExpr and conjunct.negated:
                operands = (conjunct.value,)
            else:
                operands = (conjunct,)
            for operand in operands:
                if isinstance(operand, (NameExpr, DottedNameExpr)):
                    read = _read(operand, inputs, join.ordinal)
                    if isinstance(read, JoinFieldRef):
                        proven.add((read.input, read.field))
    return proven


def _conjuncts(expression: Expression) -> tuple[Expression, ...]:
    """The top-level `and` conjuncts of a condition, in source order."""

    conjuncts: list[Expression] = []
    pending = [expression]
    while pending:
        current = pending.pop()
        if type(current) is BinaryExpr and current.operator == "and":
            pending.extend((current.right, current.left))
        else:
            conjuncts.append(current)
    return tuple(conjuncts)


def _read(
    leaf: NameExpr | DottedNameExpr, inputs: _Inputs, join: int | None
) -> JoinFieldRef | tuple[JoinFieldRef, ...] | None:
    """The field a read names among the bindings it sees (`_Inputs.readable`).

    A bare name gives the one binding field of that name, or every candidate
    in input order when several bindings have it (none when no binding
    does); ``b.f`` gives the field of binding ``b`` when the read sees it,
    else None.
    """

    if isinstance(leaf, NameExpr):
        candidates = tuple(
            JoinFieldRef(input=ordinal, field=leaf.name)
            for ordinal in inputs.owners.get(leaf.name, ())
            if inputs.readable(ordinal, join)
        )
        return candidates[0] if len(candidates) == 1 else candidates
    if len(leaf.parts) == 2:
        binding, name = leaf.parts
        ordinal = inputs.ordinals.get(binding)
        if ordinal is not None and inputs.readable(ordinal, join):
            found = name in inputs.schemas[ordinal].fields
            return JoinFieldRef(input=ordinal, field=name) if found else None
    return None


def check_join_semantics(
    script: Script,
    structures: Mapping[DerivedRelation, JoinStructure],
    *,
    relation_symbols: Mapping[str, Definition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
    expression_value_types: dict[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType],
) -> JoinChecks:
    """Resolve the reads and type the `on` of each JOIN relation.

    The reads of `let:` values, `where`, `group by`, `select` and an ungrouped `order by`
    resolve against the relation's tail row, and those of each JOIN's `on`
    against its `on` row. Each `on` is typed once, into
    ``expression_value_types``. A relation without a structure, or whose
    joined row is unknown, is not analysed here.
    """

    def schema_of(relation: RelationDefinition) -> RowSchema:
        if isinstance(relation, SourceDef):
            return source_row_schemas[relation]
        return relation_row_schemas[relation]

    rows = {
        definition: join_rows(structure, schema_of)
        for definition, structure in structures.items()
    }
    facts: dict[DerivedRelation, RelationJoinsInfo] = {}
    diagnostics: list[Diagnostic] = []
    reads: dict[SourceLocation, Diagnostic] = {}
    unanalysed: list[Span] = []
    unexplained: list[tuple[Diagnostic, tuple[Span, ...]]] = []
    for definition in script.definitions:
        if (
            not isinstance(definition, (TableDef, QueryDef))
            or not definition.join_clauses
        ):
            continue
        structure = structures.get(definition)
        joined = rows.get(definition)
        if structure is None or joined is None:
            unanalysed.append(definition.span)
            if structure is not None:
                upstream = tuple(_reads(definition, relation_symbols))[1:]
                # A structured upstream relation whose row is unknown either
                # is explained the same way or reports this itself.
                if not any(
                    relation in structures and rows[relation] is None
                    for relation in upstream
                    if not isinstance(relation, SourceDef)
                ):
                    unexplained.append(
                        (
                            _unknown_row_diagnostic(definition, structure, schema_of),
                            tuple(relation.span for relation in upstream),
                        )
                    )
            continue
        info = _relation_joins(
            definition,
            structure,
            joined,
            schema_of=schema_of,
            expression_value_types=expression_value_types,
            type_expansions=type_expansions,
            diagnostics=diagnostics,
            reads=reads,
        )
        if info is not None:
            facts[definition] = info
    return JoinChecks(
        facts=facts,
        diagnostics=tuple(diagnostics),
        reads=tuple(reads.values()),
        unanalysed=tuple(unanalysed),
        unexplained=tuple(unexplained),
    )


def _relation_joins(
    definition: DerivedRelation,
    structure: JoinStructure,
    rows: JoinRows,
    *,
    schema_of: Callable[[RelationDefinition], RowSchema],
    expression_value_types: dict[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType],
    diagnostics: list[Diagnostic],
    reads: dict[SourceLocation, Diagnostic],
) -> RelationJoinsInfo | None:
    """Resolve one structured relation's reads and type its `on` conditions;
    its facts when no read fails and no `on` has an error."""

    inputs = structure.inputs
    found_inputs = _Inputs.of(
        structure, tuple(schema_of(item.relation) for item in inputs)
    )
    field_reads: dict[Expression, JoinFieldRef] = {}
    clean = True

    def fail(leaf: NameExpr | DottedNameExpr, code: str, message: str) -> None:
        nonlocal clean
        clean = False
        location = _location(leaf.span)
        reads.setdefault(
            location,
            Diagnostic(
                code=code, severity=Severity.ERROR, message=message, location=location
            ),
        )

    for leaf in _leaves(_tail_expressions(definition)):
        read = _read(leaf, found_inputs, None)
        if isinstance(read, JoinFieldRef):
            field_reads[leaf] = read
        elif read:
            fail(
                leaf,
                "PIE-S2335",
                f"Ambiguous field: {_text(leaf)}; write {_or_list(read, inputs)}",
            )
        elif isinstance(leaf, DottedNameExpr):
            message = f"Unknown field: {_text(leaf)}"
            qualifier, field = leaf.parts if len(leaf.parts) == 2 else ("", "")
            bound = next((item for item in inputs if item.binding == qualifier), None)
            if bound is not None and not bound.visible:
                assert bound.clause is not None
                message += (
                    f"; {qualifier} is a {bound.clause.kind.value.upper()} JOIN binding, "
                    "which only its own `on` can read"
                )
            elif bound is None:
                candidates = tuple(
                    JoinFieldRef(input=item.ordinal, field=field)
                    for item in inputs
                    if item.visible and item.relation.name == qualifier
                )
                if candidates:
                    message += (
                        f"; {qualifier} names a relation, not a binding: "
                        f"write {_or_list(candidates, inputs)}"
                    )
            fail(leaf, "PIE-S2102", message)
    joins: list[JoinInfo] = []
    for join, on_row in zip(structure.joins, rows.on, strict=True):
        on_clause = join.clause.on_clause
        if on_clause is not None:
            on_reads: dict[Expression, str] = {}
            failed = False
            for leaf in _leaves((on_clause.expression,)):
                read = _read(leaf, found_inputs, join.ordinal)
                if isinstance(read, JoinFieldRef):
                    field_reads[leaf] = read
                    on_reads[leaf] = _key(inputs, read)
                    continue
                failed = True
                if read:
                    message = (
                        f"JOIN ON reference is ambiguous: {_text(leaf)}; "
                        f"write {_or_list(read, inputs)}"
                    )
                elif (
                    type(leaf) is DottedNameExpr
                    and found_inputs.ordinals.get(leaf.parts[0], 0) > join.ordinal
                ):
                    message = f"JOIN ON reference is forward: {_text(leaf)}"
                else:
                    message = f"JOIN ON reference is unknown: {_text(leaf)}"
                fail(leaf, "PIE-S2335", message)
            found = _type_join_on(
                on_clause.expression,
                on_row=on_row,
                read_keys=on_reads,
                failed=failed,
                field_qualifier=inputs[0].binding,
                expression_value_types=expression_value_types,
                type_expansions=type_expansions,
            )
            diagnostics.extend(found)
            clean = clean and not any(
                diagnostic.severity is Severity.ERROR for diagnostic in found
            )
        info = _join_info(
            join, inputs, on_row, _visible_before(definition, join.ordinal)
        )
        if info is None:
            clean = False
        else:
            joins.append(info)
    if not clean:
        return None
    return RelationJoinsInfo(
        inputs=inputs,
        joins=tuple(joins),
        row_schema=rows.tail,
        field_reads=field_reads,
    )


def _type_join_on(
    expression: Expression,
    *,
    on_row: RowSchema,
    read_keys: Mapping[Expression, str],
    failed: bool,
    field_qualifier: str,
    expression_value_types: dict[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType],
) -> list[Diagnostic]:
    """Type one JOIN-local `on` against its `on` row; its diagnostics.

    ``read_keys`` key each resolved field read to its `on` row field, and
    ``failed`` says that a read failed, which the read reports itself. An
    `on` of unknown type, or one that reads a field of unknown type, is
    refused when nothing else inside it is reported: its matches could not
    be checked.
    """

    if contains_semantic_aggregate(expression):
        return [
            _diagnostic(
                expression.span,
                "PIE-S2335",
                "Aggregate expressions are unavailable in JOIN ON.",
            )
        ]
    # Each read is typed as the binding field it resolved to.
    reads_unknown = False
    for leaf, key in read_keys.items():
        read_type = _field_value_type(on_row.fields[key])
        expression_value_types[leaf] = read_type
        reads_unknown = reads_unknown or read_type.kind is ValueTypeKind.UNKNOWN
    found: list[Diagnostic] = []
    value_type = infer_row_expression(
        expression,
        on_row,
        expression_value_types,
        found,
        report_unknown_name=False,
        field_qualifier=field_qualifier,
        type_expansions=type_expansions,
    )
    not_bool = _check_bool_expression(
        expression,
        context="JOIN ON",
        expression_value_types=expression_value_types,
        type_expansions=type_expansions,
        explained=value_type.kind is ValueTypeKind.KNOWN
        or failed
        or any(diagnostic.severity is Severity.ERROR for diagnostic in found),
        row_schema=on_row,
    )
    if not_bool is not None:
        found.append(not_bool)
    elif (value_type.kind is ValueTypeKind.UNKNOWN or reads_unknown) and not (
        found or failed
    ):
        found.append(
            _diagnostic(
                expression.span,
                "PIE-S2202",
                "JOIN ON expression type is unavailable; the fields it reads "
                "need known types.",
            )
        )
    return found


def _join_info(
    join: StructuredJoin,
    inputs: tuple[JoinInputInfo, ...],
    on_row: RowSchema,
    earlier: tuple[int, ...],
) -> JoinInfo | None:
    """One JOIN's facts; its relationship equalities read their types from
    the JOIN's `on` row.

    None when a relationship pair names a field that row lacks, which the
    relationship resolution never gives: the relation then gets no facts,
    so IR refuses it instead of lowering a guessed equality.
    """

    clause = join.clause
    resolution = join.relationship
    source = inputs[join.source_input].binding
    target = inputs[join.ordinal].binding
    equalities: list[JoinEqualityInfo] = []
    for source_field, target_field, comparison, source_operand, target_operand in (
        () if resolution is None else resolution.pairs
    ):
        left = on_row.fields.get(f"{source}.{source_field}")
        right = on_row.fields.get(f"{target}.{target_field}")
        if left is None or right is None:
            return None
        equalities.append(
            JoinEqualityInfo(
                left=JoinFieldRef(input=join.source_input, field=source_field),
                right=JoinFieldRef(input=join.ordinal, field=target_field),
                left_type=_field_value_type(left),
                right_type=_field_value_type(right),
                comparison=comparison,
                left_operand=source_operand,
                right_operand=target_operand,
            )
        )
    return JoinInfo(
        ordinal=join.ordinal,
        clause=clause,
        kind=clause.kind,
        mode=join.mode,
        source_input=join.source_input,
        source_inferred=join.source_inferred,
        target_input=join.ordinal,
        relationship=None if resolution is None else resolution.relationship,
        step=clause.traversal_steps[0] if join.mode in {"M2", "M4"} else None,
        equalities=tuple(equalities),
        condition=None if clause.on_clause is None else clause.on_clause.expression,
        null_extends=_null_extends(clause.kind, join.ordinal, earlier),
    )


def _key(inputs: tuple[JoinInputInfo, ...], read: JoinFieldRef) -> str:
    return f"{inputs[read.input].binding}.{read.field}"


def _field_value_type(field: RowField) -> ValueType:
    """A field read's type, as the typing kernel gives a row field."""

    if field.resolved_type.kind is TypeKind.UNKNOWN:
        return _UNKNOWN_VALUE_TYPE
    return ValueType(resolved_type=field.resolved_type, nullability=field.nullability)


def _tail_expressions(definition: DerivedRelation) -> tuple[Expression, ...]:
    """The expressions that read a relation's tail row as fields: `let:`
    values, `where`, `group by`, `select` items and an ungrouped `order by`."""

    order = definition.order_by_clause
    return (
        *(
            ()
            if definition.let_clause is None
            else (binding.expression for binding in definition.let_clause.bindings)
        ),
        *(
            ()
            if definition.where_clause is None
            else (definition.where_clause.expression,)
        ),
        *(
            ()
            if definition.group_by_clause is None
            else (item.key for item in definition.group_by_clause.items)
        ),
        *(item.expression for item in definition.select_items),
        *(
            ()
            if order is None or definition.group_by_clause is not None
            else (item.expression for item in order.items)
        ),
    )


def _leaves(roots: Sequence[Expression]) -> Iterator[NameExpr | DottedNameExpr]:
    """The name and dotted name reads below ``roots``, in source order; a
    call's callee is no read and a window is not entered."""

    pending = list(reversed(roots))
    while pending:
        node = pending.pop()
        if isinstance(node, (NameExpr, DottedNameExpr)):
            yield node
        else:
            pending.extend(reversed(child_expressions(node)))


def _unknown_row_diagnostic(
    definition: DerivedRelation,
    structure: JoinStructure,
    schema_of: Callable[[RelationDefinition], RowSchema],
) -> Diagnostic:
    """Refuse a JOIN relation whose input row is unknown for no reported
    reason, at the first JOIN whose input row is unknown."""

    item = next(
        item for item in structure.inputs if schema_of(item.relation).is_unknown
    )
    clause = definition.join_clauses[max(item.ordinal, 1) - 1]
    name = clause.target_relation_name if item.ordinal else item.binding
    return availability_diagnostic(
        clause.span,
        f"A JOIN over {name}, whose fields are not known, is not available in "
        "single files yet.",
    )


def join_post_pass(
    diagnostics: Sequence[Diagnostic], checks: JoinChecks
) -> list[Diagnostic]:
    """Leave one diagnostic at each read of a JOIN relation that failed.

    A relation that was not analysed as a JOIN relation adds no PIE-S2102 or
    PIE-S2380; each failed read keeps exactly its resolver diagnostic, which
    for an unknown field is the typing kernel's own PIE-S2102; and a relation
    whose input row is unknown says so unless an ERROR inside a relation it
    reads explains that. Diagnostics of other codes are kept as they are.
    """

    failed = {read.location for read in checks.reads}
    kept = [
        diagnostic
        for diagnostic in diagnostics
        if not (
            diagnostic.code in {"PIE-S2102", "PIE-S2380"}
            and any(_inside(diagnostic.location, span) for span in checks.unanalysed)
        )
        and not (diagnostic.code == "PIE-S2102" and diagnostic.location in failed)
    ]
    kept.extend(checks.reads)
    errors = [
        diagnostic.location
        for diagnostic in kept
        if diagnostic.severity is Severity.ERROR
    ]
    kept.extend(
        diagnostic
        for diagnostic, spans in checks.unexplained
        if not any(_inside(location, span) for location in errors for span in spans)
    )
    return kept


def _inside(location: SourceLocation, span: Span) -> bool:
    return location.path == span.path and (span.line, span.column) <= (
        location.line,
        location.column,
    ) < (span.end_line, span.end_column)


def _text(leaf: NameExpr | DottedNameExpr) -> str:
    return ".".join(leaf.parts) if isinstance(leaf, DottedNameExpr) else leaf.name


def _or_list(
    candidates: tuple[JoinFieldRef, ...], inputs: tuple[JoinInputInfo, ...]
) -> str:
    """``b.f`` of each candidate, in input order, as `x`, `x or y` or `x, y or z`."""

    names = [_key(inputs, candidate) for candidate in candidates]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} or {names[-1]}"


def _location(span: Span) -> SourceLocation:
    return SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _diagnostic(span: Span, code: str, message: str) -> Diagnostic:
    return Diagnostic(
        code=code, severity=Severity.ERROR, message=message, location=_location(span)
    )
