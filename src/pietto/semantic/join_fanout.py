"""The conservative fan-out rule for aggregates over single-file JOIN rows.

Private: nothing here is exported. It reads only the AST, diagnostics and
semantic facts, never project code.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pietto.ast_nodes import (
    AuthoredJoinKind,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    Definition,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    NameExpr,
    QueryDef,
    SelectItem,
    ShapeDef,
    SourceDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    AVG_AGGREGATE_NAME,
    COUNT_AGGREGATE_NAME,
    COUNT_DISTINCT_AGGREGATE_NAME,
    MAX_AGGREGATE_NAME,
    MIN_AGGREGATE_NAME,
    STDDEV_AGGREGATE_NAME,
    SUM_AGGREGATE_NAME,
    child_expressions,
    semantic_aggregate_call_name,
)
from pietto.semantic.relationship_predicates import mandatory_field_equalities
from pietto.semantic.model import (
    EffectiveNullability,
    JoinFieldRef,
    JoinInfo,
    RelationJoinsInfo,
    RelationshipCallInfo,
    RowSchema,
)

__all__ = ()

_NOT_FACTORS = (AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI)

# The aggregates whose value is a function of the set of non-NULL argument
# values of a group: a JOIN that repeats a row only repeats a value already in
# that set, so they never read rows a JOIN repeats in a way that matters.
_SET_INSENSITIVE = frozenset(
    (MIN_AGGREGATE_NAME, MAX_AGGREGATE_NAME, COUNT_DISTINCT_AGGREGATE_NAME)
)
# The aggregates that skip every row whose argument is NULL (`count` with an
# argument, `sum`, `avg`, `stddev`): they read no row in which their direct
# field argument's input is NULL-extended.
_NULL_SKIPPING = frozenset(
    (
        COUNT_AGGREGATE_NAME,
        SUM_AGGREGATE_NAME,
        AVG_AGGREGATE_NAME,
        STDDEV_AGGREGATE_NAME,
    )
)


@dataclass(frozen=True, slots=True)
class _KeyDependency:
    """Each key field needs one reached determinant; alternatives stay complete.

    ``nulls`` holds the inputs that are NULL-extended in the only rows where
    the dependency fails; it then holds for an aggregate that reads none of
    those rows. An empty ``nulls`` holds on every row.
    """

    determinants: tuple[frozenset[int], ...]
    target: int
    nulls: frozenset[int] = frozenset()

    def ready(self, reached: set[int] | frozenset[int]) -> bool:
        return all(candidates & reached for candidates in self.determinants)


def join_fanout_diagnostics(
    definition: TableDef | QueryDef,
    info: RelationJoinsInfo,
    *,
    type_symbols: Mapping[str, Definition],  # shapes of sources (keys)
    source_row_schemas: Mapping[SourceDef, RowSchema],  # NOT NULL of key fields
    let_expressions: Mapping[str, Expression],  # admitted `let:` values
    relationship_calls: Sequence[RelationshipCallInfo] = (),
) -> tuple[Diagnostic, ...]:
    """One PIE-S2381 per refused aggregate call, in select order."""

    # Factors: the FROM input and every JOIN target other than SEMI and ANTI.
    factors = frozenset({0}).union(
        join.target_input for join in info.joins if join.kind not in _NOT_FACTORS
    )
    keys = tuple(_declared_keys(item.relation, type_symbols) for item in info.inputs)
    on_pairs = _on_pairs(info)
    anti_joins = _anti_join_dependencies(definition, info, source_row_schemas)
    key_dependencies = (
        *_predicate_key_dependencies(
            definition, info, keys, on_pairs, relationship_calls
        ),
        *anti_joins,
    )
    # The inputs NULL-extended on every row WHERE keeps (`_null_followers` of
    # the anti-joined ones): their JOINs repeat no row and match nothing.
    nulled = _null_followers(
        frozenset(dependency.target for dependency in anti_joins), info, on_pairs
    )
    protected = _group_protection(
        definition, info, keys, factors, source_row_schemas, let_expressions
    )
    diagnostics: list[Diagnostic] = []
    for item in definition.select_items:
        call = item.expression
        name = semantic_aggregate_call_name(call)
        if name is None or item.alias is None or not isinstance(call, CallExpr):
            continue
        if name == COUNT_AGGREGATE_NAME and not call.arguments:
            # count() counts JOIN rows by definition.
            continue
        if name in _SET_INSENSITIVE:
            continue
        seed = _argument_inputs(call, info, let_expressions) | protected
        # The direct field argument of an aggregate that skips NULL arguments.
        read = (
            _renamed_field(call.arguments[0], info, let_expressions)
            if name in _NULL_SKIPPING and call.arguments
            else None
        )
        usable = _usable_dependencies(read, info, on_pairs, key_dependencies)
        if factors <= _closure(seed, usable):
            continue
        span = call.span
        diagnostics.append(
            Diagnostic(
                code="PIE-S2381",
                severity=Severity.ERROR,
                message=_message(
                    info, factors, seed, usable, keys, on_pairs, read, nulled
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
    return tuple(diagnostics)


def _declared_keys(
    relation: SourceDef | TableDef | QueryDef,
    type_symbols: Mapping[str, Definition],
) -> tuple[tuple[str, ...], ...]:
    """The field sets of a source shape's `unique` items in declaration order,
    or the output keys of a grouped table or query (`_grouped_keys`); other
    tables and queries carry no keys."""

    if not isinstance(relation, SourceDef):
        return _grouped_keys(relation)
    if relation.shape_name is None:
        return ()
    shape = type_symbols.get(relation.shape_name)
    if not isinstance(shape, ShapeDef):
        return ()
    return tuple(unique.field_names for unique in shape.uniques)


def _grouped_keys(relation: TableDef | QueryDef) -> tuple[tuple[str, ...], ...]:
    """The output names of every GROUP BY key of a grouped relation, each key
    selected as its plain read (`k` or `alias = k`, as written in GROUP BY).

    GROUP BY yields one row per distinct key tuple (one NULL group per NULL
    key, which no `==` matches), so these outputs are a unique key of its rows:
    an `on` that matches them all matches at most one of its rows. A key that
    is not selected leaves no such key; a key selected under several names
    puts every one of them in the key, so none is preferred, as in the key a
    project gives a grouped relation."""

    clause = relation.group_by_clause
    if clause is None:
        return ()
    names: dict[str, None] = {}
    for group in clause.items:
        written = _field_text(group.key)
        selected = tuple(
            name
            for item in relation.select_items
            if isinstance(item.expression, (NameExpr, DottedNameExpr))
            and _field_text(item.expression) == written
            and (name := _output_name(item)) is not None
        )
        if not selected:
            return ()
        names.update(dict.fromkeys(selected))
    return (tuple(names),)


def _field_text(expression: NameExpr | DottedNameExpr) -> str:
    if isinstance(expression, NameExpr):
        return expression.name
    return ".".join(expression.parts)


def _output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    if isinstance(item.expression, NameExpr):
        return item.expression.name
    if isinstance(item.expression, DottedNameExpr):
        return item.expression.parts[-1]
    return None


def _on_pairs(
    info: RelationJoinsInfo,
) -> dict[int, list[tuple[JoinFieldRef, JoinFieldRef]]]:
    """Per JOIN ordinal, the top-level `==` conjuncts of its `on` between two
    field reads of different inputs, bare or qualified."""

    pairs: dict[int, list[tuple[JoinFieldRef, JoinFieldRef]]] = {}
    for join in info.joins:
        clause = join.clause.on_clause
        if clause is None:
            continue
        found = pairs.setdefault(join.ordinal, [])
        for node in _and_tree(clause.expression):
            if type(node) is not ComparisonExpr or node.operator != "==":
                continue
            left = info.field_reads.get(node.left)
            right = info.field_reads.get(node.right)
            if left is not None and right is not None and left.input != right.input:
                found.append((left, right))
    return pairs


def _key_determinants(
    pairs: Sequence[tuple[JoinFieldRef, JoinFieldRef]],
    target: int,
    key: tuple[str, ...],
) -> tuple[frozenset[int], ...] | None:
    """For each field of ``key`` of input ``target``, the other inputs whose
    fields ``pairs`` equate with it; None when a field has none."""

    determinants: list[frozenset[int]] = []
    for field in key:
        candidates = frozenset(
            other.input
            for left, right in pairs
            for own, other in ((left, right), (right, left))
            if own.input == target and own.field == field
        )
        if not candidates:
            return None
        determinants.append(candidates)
    return tuple(determinants) or None


def _predicate_key_dependencies(
    definition: TableDef | QueryDef,
    info: RelationJoinsInfo,
    keys: tuple[tuple[tuple[str, ...], ...], ...],
    on_pairs: Mapping[int, Sequence[tuple[JoinFieldRef, JoinFieldRef]]],
    calls: Sequence[RelationshipCallInfo],
) -> tuple[_KeyDependency, ...]:
    """Key proofs from required positive equalities.

    In ON they are its top-level `==` conjuncts between two field reads of
    different inputs, bare or qualified, written by hand or in the body of a
    relationship call; in WHERE only those of actual required calls. ON proves
    only dependencies its JOIN preserves; WHERE proves dependencies of the
    final filtered rows. Neither proves coverage or a matching row exists.

    An INNER `on` holds on every row it keeps. A LEFT `on` holds on its
    matched rows; on a row it NULL-extends its target is NULL and its earlier
    inputs are one row, so its target is determined everywhere, and an earlier
    input whose key it matches only where its target is not NULL-extended. A
    RIGHT `on` likewise determines its target only where its earlier inputs
    are not NULL-extended: an unmatched target row stands beside one NULL left
    part, which several unmatched target rows share.
    """

    occurrences = {
        id(definition.from_clause if item.ordinal == 0 else item.clause): item.ordinal
        for item in info.inputs
    }
    on_joins: dict[int, JoinInfo] = {
        id(join.clause.on_clause): join
        for join in info.joins
        if join.clause.on_clause is not None
    }
    scopes: dict[int, list[tuple[JoinFieldRef, JoinFieldRef]]] = {
        id(join.clause.on_clause): list(on_pairs[join.ordinal])
        for join in on_joins.values()
    }
    present: dict[int, set[int]] = {}
    for call in calls:
        if (
            call.owner is not definition
            or not call.mandatory_equalities
            or call.context is not definition.where_clause
        ):
            continue
        context_id = id(call.context)
        assert definition.where_clause is not None
        expression = definition.where_clause.expression
        arguments: set[int] = set()
        for argument in call.arguments:
            ordinal = occurrences.get(id(argument.occurrence))
            if (
                ordinal is None
                or argument.relation is not info.inputs[ordinal].relation
            ):
                break
            arguments.add(ordinal)
        else:
            if context_id not in present:
                present[context_id] = {id(node) for node in _and_tree(expression)}
            if id(call.expanded) not in present[context_id]:
                continue
            required = {id(item) for item in mandatory_field_equalities(call.expanded)}
            pairs = scopes.setdefault(context_id, [])
            for equality in call.mandatory_equalities:
                left = info.field_reads.get(equality.left)
                right = info.field_reads.get(equality.right)
                if (
                    id(equality) in required
                    and left is not None
                    and right is not None
                    and left.input in arguments
                    and right.input in arguments
                    and left.input != right.input
                ):
                    pairs.append((left, right))
    dependencies: list[_KeyDependency] = []
    for context_id, pairs in scopes.items():
        targets: tuple[tuple[int, frozenset[int]], ...]
        if context_id == id(definition.where_clause):
            targets = tuple(
                (item.ordinal, frozenset()) for item in info.inputs if item.visible
            )
        else:
            join = on_joins[context_id]
            if join.kind is AuthoredJoinKind.INNER:
                targets = tuple(
                    (item.ordinal, frozenset())
                    for item in info.inputs
                    if item.visible and item.ordinal <= join.target_input
                )
            elif join.kind is AuthoredJoinKind.LEFT:
                targets = (
                    (join.target_input, frozenset()),
                    *(
                        (item.ordinal, frozenset((join.target_input,)))
                        for item in info.inputs
                        if item.visible and item.ordinal < join.target_input
                    ),
                )
            elif join.kind is AuthoredJoinKind.RIGHT:
                targets = ((join.target_input, frozenset(join.null_extends)),)
            else:
                continue
        for target, nulls in targets:
            for key in keys[target]:
                determinants = _key_determinants(pairs, target, key)
                if determinants is not None:
                    dependencies.append(_KeyDependency(determinants, target, nulls))
    for join in info.joins:
        if join.latest is not None:
            # An asof JOIN keeps at most one target row per earlier row: the
            # earlier inputs its `on` reads determine it.
            dependencies.append(
                _KeyDependency(
                    tuple(frozenset({item}) for item in _earlier_reads(info, join)),
                    join.target_input,
                )
            )
    return tuple(dependencies)


def _earlier_reads(info: RelationJoinsInfo, join: JoinInfo) -> tuple[int, ...]:
    """The earlier inputs a JOIN's `on` reads, ascending."""

    read: set[int] = set()
    pending = [] if join.condition is None else [join.condition]
    while pending:
        node = pending.pop()
        ref = (
            info.field_reads.get(node)
            if isinstance(node, (NameExpr, DottedNameExpr))
            else None
        )
        if ref is not None and ref.input < join.target_input:
            read.add(ref.input)
        pending.extend(child_expressions(node))
    return tuple(sorted(read))




def _anti_join_dependencies(
    definition: TableDef | QueryDef,
    info: RelationJoinsInfo,
    source_row_schemas: Mapping[SourceDef, RowSchema],
) -> tuple[_KeyDependency, ...]:
    """Inputs that WHERE keeps NULL-extended on every row it keeps.

    A top-level `and` operand `x.f is None`, where `x` is a LEFT JOIN's input
    and `f` is a field that its source shape declares never None, is true
    only on a row in which `x` is NULL-extended: there `x` is one all-NULL
    row, which every other input determines. Under `or` or `not`, or of a
    field that may be None, it proves nothing.
    """

    if definition.where_clause is None:
        return ()
    left_targets = {
        join.target_input for join in info.joins if join.kind is AuthoredJoinKind.LEFT
    }
    targets: dict[int, None] = {}
    for node in _and_tree(definition.where_clause.expression):
        if type(node) is not IsNullExpr or node.negated:
            continue
        read = info.field_reads.get(node.value)
        if read is None or read.input not in left_targets:
            continue
        relation = info.inputs[read.input].relation
        schema = (
            source_row_schemas.get(relation)
            if isinstance(relation, SourceDef)
            else None
        )
        field = None if schema is None else schema.fields.get(read.field)
        if field is not None and field.nullability is EffectiveNullability.NON_NULL:
            targets[read.input] = None
    return tuple(_KeyDependency((), target) for target in targets)


def _usable_dependencies(
    read: JoinFieldRef | None,
    info: RelationJoinsInfo,
    on_pairs: Mapping[int, Sequence[tuple[JoinFieldRef, JoinFieldRef]]],
    dependencies: tuple[_KeyDependency, ...],
) -> tuple[_KeyDependency, ...]:
    """The dependencies that hold on the rows this aggregate reads: those
    that hold everywhere, and those whose failing rows it skips because its
    argument (``read``, of a NULL-skipping aggregate) is a field, or a `let`
    name of one, of an input NULL-extended there (`_null_followers`)."""

    return tuple(
        dependency
        for dependency in dependencies
        if not dependency.nulls
        or (
            read is not None
            and read.input in _null_followers(dependency.nulls, info, on_pairs)
        )
    )


def _null_followers(
    nulls: frozenset[int],
    info: RelationJoinsInfo,
    on_pairs: Mapping[int, Sequence[tuple[JoinFieldRef, JoinFieldRef]]],
    *,
    full: bool = False,
) -> frozenset[int]:
    """``nulls`` and each input NULL-extended on every row where one of them
    is: an INNER or LEFT JOIN whose `on` equates a field of its own input with
    a field of such an input finds no match where that field is NULL, so it
    drops the row or NULL-extends its input there, and a later RIGHT or FULL
    JOIN adds only rows in which every earlier input is NULL-extended.

    With ``full``, also such a FULL JOIN's input, which is NULL-extended on
    every row that comes from one of those rows but not on the rows it adds
    without a match: what a remedy about those rows asks, not a proof."""

    kinds = (AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT)
    if full:
        kinds += (AuthoredJoinKind.FULL,)
    followers = set(nulls)
    for join in info.joins:
        if (
            join.kind in kinds
            and join.target_input not in followers
            and any(
                own.input == join.target_input and other.input in followers
                for left, right in on_pairs.get(join.ordinal, ())
                for own, other in ((left, right), (right, left))
            )
        ):
            followers.add(join.target_input)
    return frozenset(followers)


def _and_tree(expression: Expression) -> tuple[Expression, ...]:
    """Every node of the top-level `and` chain, its `and` nodes included."""

    nodes: list[Expression] = []
    pending = [expression]
    while pending:
        node = pending.pop()
        nodes.append(node)
        if isinstance(node, BinaryExpr) and node.operator == "and":
            pending.extend((node.right, node.left))
    return tuple(nodes)


def _group_protection(
    definition: TableDef | QueryDef,
    info: RelationJoinsInfo,
    keys: tuple[tuple[tuple[str, ...], ...], ...],
    factors: frozenset[int],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    let_expressions: Mapping[str, Expression],
) -> frozenset[int]:
    """Every factor with a strict key whose fields are all GROUP BY keys."""

    grouped: set[tuple[int, str]] = set()
    if definition.group_by_clause is not None:
        for item in definition.group_by_clause.items:
            read = _renamed_field(item.key, info, let_expressions)
            if read is not None:
                grouped.add((read.input, read.field))
    protected: set[int] = set()
    for position in factors:
        relation = info.inputs[position].relation
        schema = (
            source_row_schemas.get(relation)
            if isinstance(relation, SourceDef)
            else None
        )
        if schema is None:
            continue
        for key in keys[position]:
            fields = tuple(schema.fields.get(name) for name in key)
            if all((position, name) in grouped for name in key) and all(
                field is not None and field.nullability is EffectiveNullability.NON_NULL
                for field in fields
            ):
                protected.add(position)
                break
    return frozenset(protected)


def _renamed_field(
    expression: Expression,
    info: RelationJoinsInfo,
    let_expressions: Mapping[str, Expression],
) -> JoinFieldRef | None:
    """The field a GROUP BY key reads, following `let:` names that rename one."""

    followed: set[str] = set()
    while isinstance(expression, (NameExpr, DottedNameExpr)):
        read = info.field_reads.get(expression)
        if read is not None:
            return read
        if (
            not isinstance(expression, NameExpr)
            or expression.name in followed
            or expression.name not in let_expressions
        ):
            return None
        followed.add(expression.name)
        expression = let_expressions[expression.name]
    return None


def _argument_inputs(
    call: CallExpr,
    info: RelationJoinsInfo,
    let_expressions: Mapping[str, Expression],
) -> frozenset[int]:
    """The inputs whose fields the arguments read, through `let:` names."""

    inputs: set[int] = set()
    followed: set[str] = set()
    pending: list[Expression] = [
        *call.arguments,
        *(item.expression for item in call.aggregate_order_by),
    ]
    while pending:
        node = pending.pop()
        if not isinstance(node, (NameExpr, DottedNameExpr)):
            pending.extend(child_expressions(node))
            continue
        read = info.field_reads.get(node)
        if read is not None:
            inputs.add(read.input)
        elif (
            isinstance(node, NameExpr)
            and node.name in let_expressions
            and node.name not in followed
        ):
            followed.add(node.name)
            pending.append(let_expressions[node.name])
    return frozenset(inputs)


def _closure(
    seed: frozenset[int], key_dependencies: tuple[_KeyDependency, ...]
) -> frozenset[int]:
    closed = set(seed)
    grown = True
    while grown:
        grown = False
        for dependency in key_dependencies:
            if dependency.target not in closed and dependency.ready(closed):
                closed.add(dependency.target)
                grown = True
    return frozenset(closed)


def _message(
    info: RelationJoinsInfo,
    factors: frozenset[int],
    seed: frozenset[int],
    key_dependencies: tuple[_KeyDependency, ...],
    keys: tuple[tuple[tuple[str, ...], ...], ...],
    on_pairs: Mapping[int, Sequence[tuple[JoinFieldRef, JoinFieldRef]]],
    read: JoinFieldRef | None,
    nulled: frozenset[int],
) -> str:
    """Why the aggregate may read repeated rows, then the inputs whose
    grouping would close the rule. ``read`` is the direct field argument of a
    NULL-skipping aggregate; ``nulled`` the inputs NULL-extended on every row
    WHERE keeps, whose JOINs repeat no row and match no key there."""

    def binding(position: int) -> str:
        return info.inputs[position].binding

    reached = _closure(seed, key_dependencies)
    repeating = tuple(
        join
        for join in info.joins
        if join.kind not in _NOT_FACTORS
        and join.target_input not in nulled
        and _repeats(info, join, factors, reached)
    )
    repeated = tuple(
        dict.fromkeys(f"JOIN {binding(join.target_input)}" for join in repeating)
    )

    # Group keys: the source factors, each dropped when the rest still close.
    picked = tuple(
        position
        for position, item in enumerate(info.inputs)
        if position in factors and isinstance(item.relation, SourceDef)
    )

    def grouped(inputs: tuple[int, ...]) -> bool:
        return factors <= _closure(seed | frozenset(inputs), key_dependencies)

    if grouped(picked):
        for position in tuple(picked):
            rest = tuple(other for other in picked if other != position)
            if grouped(rest):
                picked = rest
    else:
        picked = ()

    cause = (
        f"An aggregate may read rows repeated by {_and_list(repeated)}"
        if repeated
        else "An aggregate may read rows that a JOIN repeats"
    )
    if repeating and all(join.latest is not None for join in repeating):
        # An asof JOIN already matches its keys in `on`.
        return (
            f"{cause}; use `any(...)` for an input that only filters rows, or "
            "aggregate in a separate query first"
        )
    if not picked:
        return cause

    # A picked input whose key an `on` already matches needs no new match.
    # Where that JOIN NULL-extends the other side of the match (LEFT for an
    # earlier input, RIGHT for its own input), the match holds only on rows
    # the JOIN matched: the aggregate reads the rows it keeps without a match.
    # Where it already reads none of them, what is missing is a proof that a
    # single file does not make, as for a FULL JOIN's match or a RIGHT JOIN's
    # match of an earlier input's key: such an input is not named. The `on`
    # of a JOIN whose input is NULL-extended on every row WHERE keeps (as by
    # `where x.id is None`) matches nothing there and proves no key.
    def skipped(join: JoinInfo) -> bool:
        nulls = (
            frozenset((join.target_input,))
            if join.kind is AuthoredJoinKind.LEFT
            else frozenset(join.null_extends)
        )
        return read is not None and read.input in _null_followers(
            nulls, info, on_pairs, full=True
        )

    to_match: list[int] = []
    unmatched: set[int] = set()
    for position in picked:
        joins = tuple(
            join
            for join in info.joins
            if join.ordinal in on_pairs
            and join.target_input not in nulled
            and position <= join.target_input
            and any(
                _key_determinants(on_pairs[join.ordinal], position, key) is not None
                for key in keys[position]
            )
        )
        outer = tuple(
            join
            for join in joins
            if (join.kind is AuthoredJoinKind.LEFT and position != join.target_input)
            or (join.kind is AuthoredJoinKind.RIGHT and position == join.target_input)
        )
        if outer:
            unmatched.update(join.ordinal for join in outer if not skipped(join))
        elif not joins or not all(
            join.kind is AuthoredJoinKind.FULL
            or (join.kind is AuthoredJoinKind.RIGHT and position < join.target_input)
            for join in joins
        ):
            to_match.append(position)
    remedies: list[str] = []
    if to_match:
        # Grouping by such a key would pass too, but would change the
        # result's grain, so the remedy keeps the authored GROUP BY.
        noun = "a unique key" if len(to_match) == 1 else "unique keys"
        remedies.append(
            f"match {noun} of {_and_list(tuple(binding(item) for item in to_match))}"
            " in `on`"
        )
    if unmatched:
        joins_text = tuple(
            f"JOIN {binding(join.target_input)}"
            for join in info.joins
            if join.ordinal in unmatched
        )
        verb = "keeps" if len(joins_text) == 1 else "keep"
        remedies.append(
            f"read no row that {_and_list(joins_text)} {verb} without a match"
        )
    remedies.append(
        "use `any(...)` for an input that only filters rows, or aggregate in a "
        "separate query first"
    )
    return f"{cause}; {', '.join(remedies)}"


def _repeats(
    info: RelationJoinsInfo,
    join: JoinInfo,
    factors: frozenset[int],
    reached: frozenset[int],
) -> bool:
    """Whether this JOIN may repeat rows whose inputs ``reached`` determines."""

    target = join.target_input in reached
    read: set[int] = set()
    pending = [] if join.condition is None else [join.condition]
    while pending:
        node = pending.pop()
        ref = (
            info.field_reads.get(node)
            if isinstance(node, (NameExpr, DottedNameExpr))
            else None
        )
        if ref is not None and ref.input < join.target_input:
            read.add(ref.input)
        pending.extend(child_expressions(node))
    if read:
        return any((source in reached) != target for source in read)
    return (
        any(item in reached for item in factors if item < join.target_input) != target
    )


def _and_list(items: tuple[str, ...]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"
