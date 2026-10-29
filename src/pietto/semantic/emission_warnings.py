"""Single-file warnings for completed facts that cannot emit."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import fields, is_dataclass

from pietto.ast_nodes import (
    AnyExpr,
    AuthoredJoinKind,
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    CastExpr,
    ComparisonExpr,
    ConditionalExpr,
    DottedNameExpr,
    Expression,
    FromClause,
    LetBinding,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    Node,
    QueryDef,
    Script,
    SourceDef,
    Span,
    TableDef,
    TypeExpr,
    UnaryExpr,
    WindowFrameUnit,
    WindowExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import child_expressions, has_unknown_field_reference
from pietto.semantic.expressions import (
    _canonical_resolved_type,
    _relation_projection_output_name,
)
from pietto.semantic.joins import _conjuncts
from pietto.semantic.model import (
    LetScopeSemanticInfo,
    RelationJoinsInfo,
    RelationshipCallInfo,
    ResolvedType,
    TypeKind,
    ValueType,
)
from pietto.semantic.window_semantics import (
    AggregateWindowAnalysis,
    ValidatedFrame,
    WindowExpressionAnalysis,
    WindowNthDirection,
    WindowNullTreatment,
)

__all__ = ()


def emission_warnings(
    script: Script,
    *,
    window_expression_analyses: Mapping[WindowExpr, WindowExpressionAnalysis],
    aggregate_window_analyses: Mapping[WindowExpr, AggregateWindowAnalysis],
    relation_joins: Mapping[TableDef | QueryDef, RelationJoinsInfo],
    let_scopes: Mapping[TableDef | QueryDef, LetScopeSemanticInfo],
    type_expansions: Mapping[TypeExpr, ResolvedType],
    expression_value_types: Mapping[Expression, ValueType],
    from_resolutions: Mapping[FromClause, object],
    relationship_calls: Sequence[RelationshipCallInfo],
    reported: Sequence[Diagnostic],
) -> list[Diagnostic]:
    """Return PIE-S2385 from complete semantic window, JOIN and expression
    facts only."""

    errors = tuple(
        item.location for item in reported if item.severity is Severity.ERROR
    )
    found: list[Diagnostic] = []
    for analysis in (
        *window_expression_analyses.values(),
        *aggregate_window_analyses.values(),
    ):
        warning = _range_offset_warning(analysis, errors)
        if warning is not None:
            found.append(warning)
    for analysis in window_expression_analyses.values():
        expression = analysis.semantic_fact.expression
        modifiers = (
            analysis.navigation_fact.modifiers
            if analysis.navigation_fact is not None
            else analysis.frame_value_fact.modifiers
            if analysis.frame_value_fact is not None
            else None
        )
        if (
            modifiers is not None
            and modifiers.null_treatment is WindowNullTreatment.IGNORE_NULLS
        ):
            found.append(_warning(expression, "this window uses IGNORE NULLS"))
        if (
            modifiers is not None
            and modifiers.nth_direction is WindowNthDirection.FROM_LAST
        ):
            found.append(_warning(expression, "this window uses FROM LAST"))
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        info = relation_joins.get(definition)
        if info is None:
            continue
        found.extend(
            _full_join_warnings(
                info, relationship_calls, type_expansions, expression_value_types
            )
        )
    mysql = _mysql_readers(script, from_resolutions)
    found.extend(
        _all_null_relation_reads(
            script,
            relation_joins,
            let_scopes,
            from_resolutions,
            mysql,
            reported,
        )
    )
    found.extend(
        _expression_warnings(
            script,
            let_scopes,
            mysql,
            expression_value_types,
            type_expansions,
            errors,
        )
    )
    found.extend(
        _hidden_table_warnings(
            script, relation_joins, let_scopes, from_resolutions, mysql, errors
        )
    )
    return found


def _full_join_warnings(
    info: RelationJoinsInfo,
    relationship_calls: Sequence[RelationshipCallInfo],
    type_expansions: Mapping[TypeExpr, ResolvedType],
    expression_value_types: Mapping[Expression, ValueType],
) -> list[Diagnostic]:
    """Mirror PostgreSQL's FULL JOIN rule (sql/joins.py): no `where [not]
    any(...)` filter may be pending before it, and each `and` conjunct of its
    `on`, a relationship call read as its body, must equate an Int field of
    the target with an Int field of an earlier input."""

    expanded = {id(call.call): call.expanded for call in relationship_calls}
    found: list[Diagnostic] = []
    pending = False
    for join in info.joins:
        if join.kind in {AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI}:
            # A `where [not] any(...)` before a later JOIN; a RIGHT JOIN takes
            # it into its ON, a FULL JOIN cannot.
            pending = True
            continue
        if join.kind is AuthoredJoinKind.RIGHT:
            pending = False
        if join.kind is not AuthoredJoinKind.FULL:
            continue
        if pending:
            found.append(
                _warning(
                    join.clause,
                    "a `where any(...)` or `where not any(...)` filter comes "
                    "before this FULL JOIN",
                )
            )
        equality_ids = {id(item.comparison) for item in join.equalities}
        for equality in join.equalities:
            if not (
                _canonical_int(equality.left_type, type_expansions)
                and _canonical_int(equality.right_type, type_expansions)
            ):
                found.append(_warning(equality.comparison, _FULL_TYPES))
        for condition in _conjuncts(join.condition) if join.condition else ():
            if id(condition) in equality_ids:
                continue
            details = [
                _full_conjunct_detail(
                    part,
                    join.target_input,
                    info,
                    type_expansions,
                    expression_value_types,
                )
                for part in (
                    _conjuncts(expanded[id(condition)])
                    if id(condition) in expanded
                    else (condition,)
                )
            ]
            detail = next((item for item in details if item is not None), None)
            if detail is not None:
                found.append(_warning(condition, detail))
    return found


_FULL_TYPES = "this FULL JOIN equality is not between canonical Int fields"
_FULL_FORM = (
    "this FULL JOIN condition is not an equality between Int fields of its two sides"
)


def _full_conjunct_detail(
    condition: Expression,
    target: int,
    info: RelationJoinsInfo,
    type_expansions: Mapping[TypeExpr, ResolvedType],
    expression_value_types: Mapping[Expression, ValueType],
) -> str | None:
    if type(condition) is not ComparisonExpr or condition.operator != "==":
        return _FULL_FORM
    left = info.field_reads.get(condition.left)
    right = info.field_reads.get(condition.right)
    if left is None or right is None or [left.input, right.input].count(target) != 1:
        return _FULL_FORM
    if not (
        _canonical_int(expression_value_types.get(condition.left), type_expansions)
        and _canonical_int(expression_value_types.get(condition.right), type_expansions)
    ):
        return _FULL_TYPES
    return None


# PostgreSQL types a CASE, COALESCE or NULLIF of only NULL values as text.
_TEXT_NULL = "PostgreSQL types a CASE, coalesce or nullif of only None values as text"
# Functions whose PostgreSQL forms take no text (sql/expressions.py).
_NON_TEXT_FUNCTIONS = frozenset(
    {"abs", "sign", "year", "month", "day", "hour", "minute"}
)
_INT32 = range(-(1 << 31), 1 << 31)


def _expression_warnings(
    script: Script,
    let_scopes: Mapping[TableDef | QueryDef, LetScopeSemanticInfo],
    mysql: set[int],
    expression_value_types: Mapping[Expression, ValueType],
    type_expansions: Mapping[TypeExpr, ResolvedType],
    errors: Sequence[SourceLocation],
) -> list[Diagnostic]:
    """Mirror the PostgreSQL expression refusals (sql/expressions.py) on each
    expression a relation's SQL renders, a `let:` name read as its value: an
    operator over None only, a CASE, coalesce or nullif of only None values
    where text cannot stand, a cast of a value not known to be Int, a count
    of a field typed by a shape, and an integer literal outside the 32-bit
    range. A relation that reads a MySQL table is left to that target."""

    found: list[Diagnostic] = []
    seen: set[int] = set()
    for definition in script.definitions:
        # A relation with an error emits nothing; it gets no warning either.
        if (
            not isinstance(definition, (TableDef, QueryDef))
            or id(definition) in mysql
            or any(_holds(definition, item) for item in errors)
        ):
            continue
        lets = _let_values(let_scopes.get(definition))
        all_null: dict[int, bool] = {}

        def value(node: Expression) -> Expression:
            active: set[str] = set()
            while (
                type(node) is NameExpr and node.name in lets and node.name not in active
            ):
                active.add(node.name)
                node = lets[node.name].expression
            return node

        def null(node: Expression) -> bool:
            node = value(node)
            return type(node) is LiteralExpr and node.value is None

        def text_null(node: Expression) -> bool:
            """A CASE, coalesce or nullif of only None values (is_untyped_null
            in sql/expressions.py), which PostgreSQL types as text."""

            node = value(node)
            if type(node) is LiteralExpr:
                return False
            visiting: set[int] = set()
            pending = [node]
            while pending:
                item = pending[-1]
                if id(item) in all_null:
                    pending.pop()
                    continue
                if type(item) is ConditionalExpr:
                    children: tuple[Expression, ...] = (item.when_true, item.when_false)
                elif (
                    type(item) is CallExpr
                    and type(item.callee) is NameExpr
                    and item.callee.name in {"coalesce", "nullif"}
                    and item.arguments
                ):
                    children = item.arguments
                else:
                    all_null[id(item)] = (
                        type(item) is LiteralExpr and item.value is None
                    )
                    pending.pop()
                    continue
                values = [value(child) for child in children]
                waiting = [
                    child
                    for child in values
                    if id(child) not in all_null and id(child) not in visiting
                ]
                if waiting and id(item) not in visiting:
                    visiting.add(id(item))
                    pending.extend(waiting)
                    continue
                all_null[id(item)] = all(
                    all_null.get(id(child), False) for child in values
                )
                visiting.discard(id(item))
                pending.pop()
            return all_null[id(node)]

        def typed(node: Expression) -> str | None:
            """The type name of an operand PostgreSQL cannot read as text."""

            if null(node):
                return None
            value_type = expression_value_types.get(
                value(node)
            ) or expression_value_types.get(node)
            resolved = (
                None
                if value_type is None
                else _canonical_resolved_type(value_type, type_expansions)
            )
            if resolved is None or resolved.kind in {TypeKind.ENUM, TypeKind.UNKNOWN}:
                return None
            if resolved.kind is TypeKind.BUILTIN and resolved.name in {"Text", "Any"}:
                return None
            return resolved.name

        def beside_typed(
            node: Expression, construct: str, *operands: Expression
        ) -> None:
            if any(text_null(item) for item in operands):
                name = next(
                    (name for item in operands if (name := typed(item)) is not None),
                    None,
                )
                if name is not None:
                    report(
                        node,
                        f"{_TEXT_NULL}, and {construct} has no common type for "
                        f"text and {name}",
                    )

        def report(node: Node, detail: str) -> None:
            # Not beside an error of the node or of an expression around it.
            if id(node) not in seen and not any(
                _holds(node, item) or _inside(node.span, item) for item in errors
            ):
                seen.add(id(node))
                found.append(_warning(node, detail))

        for node in _rendered_nodes(definition, lets):
            if type(node) is UnaryExpr:
                if node.operator == "-" and null(node.operand):
                    report(
                        node,
                        "PostgreSQL cannot type operator - when every operand is None",
                    )
                elif text_null(node.operand):
                    report(
                        node,
                        f"{_TEXT_NULL}, which operator {node.operator} does not take",
                    )
            elif type(node) is BinaryExpr:
                if (
                    node.operator not in {"and", "or"}
                    and null(node.left)
                    and null(node.right)
                ):
                    report(
                        node,
                        f"PostgreSQL cannot type operator {node.operator} when "
                        "every operand is None",
                    )
                elif text_null(node.left) or text_null(node.right):
                    report(
                        node,
                        f"{_TEXT_NULL}, which operator {node.operator} does not take",
                    )
            elif type(node) is ComparisonExpr:
                if node.operator not in {"like", "not like"}:
                    beside_typed(
                        node, f"operator {node.operator}", node.left, node.right
                    )
            elif type(node) is BetweenExpr:
                beside_typed(
                    node, "operator between", node.value, node.lower, node.upper
                )
            elif type(node) is MembershipExpr:
                if node.options:
                    beside_typed(
                        node,
                        "operator not in" if node.negated else "operator in",
                        node.value,
                        *node.options,
                    )
            elif type(node) is ConditionalExpr:
                if text_null(node.condition):
                    report(node, f"{_TEXT_NULL}, which a condition does not take")
                else:
                    beside_typed(node, "a conditional", node.when_true, node.when_false)
            elif type(node) is CallExpr and type(node.callee) is NameExpr:
                name = node.callee.name
                if name in {"coalesce", "nullif"}:
                    beside_typed(node, name, *node.arguments)
                elif name == "count" and len(node.arguments) == 1:
                    argument = node.arguments[0]
                    counted = expression_value_types.get(
                        value(argument)
                    ) or expression_value_types.get(argument)
                    resolved = (
                        None
                        if counted is None
                        else _canonical_resolved_type(counted, type_expansions)
                    )
                    if resolved is not None and resolved.kind is TypeKind.SHAPE:
                        report(
                            node,
                            "PostgreSQL emission counts only a field of a built-in "
                            "type, not one of a shape",
                        )
                elif name in _NON_TEXT_FUNCTIONS and any(
                    text_null(item) for item in node.arguments
                ):
                    report(node, f"{_TEXT_NULL}, which function {name} does not take")
                elif name == "substr" and any(
                    _int_literal_outside(item, _INT32) for item in node.arguments[1:]
                ):
                    report(
                        node,
                        "this substr index is outside PostgreSQL's 32-bit integer range",
                    )
            elif type(node) is CastExpr:
                # A field of unknown type is left to gradual typing.
                if not _canonical_int(
                    expression_value_types.get(value(node.value))
                    or expression_value_types.get(node.value),
                    type_expansions,
                ) and not has_unknown_field_reference(
                    node.value, expression_value_types
                ):
                    report(
                        node,
                        "PostgreSQL emission converts only a value known to be Int "
                        "to Float or Text",
                    )
            elif type(node) is WindowExpr:
                name = node.identity.name
                position = 0 if name == "ntile" else 1
                arguments = node.call.arguments
                if (
                    name in {"ntile", "lag", "lead", "nth_value"}
                    and position < len(arguments)
                    and _int_literal_outside(arguments[position], range(1 << 31))
                ):
                    report(
                        node,
                        f"this {name} integer argument is outside PostgreSQL's "
                        "32-bit integer range",
                    )
        for clause in (
            definition.where_clause,
            *(item.on_clause for item in definition.join_clauses),
            definition.qualify_clause,
        ):
            if clause is not None and text_null(clause.expression):
                report(
                    clause.expression, f"{_TEXT_NULL}, which a condition does not take"
                )
        if definition.qualify_clause is None:
            continue
        # QUALIFY reads the SELECT outputs through a derived table, whose NULL
        # outputs PostgreSQL types as text, as it does a CTE's.
        read: set[str] = set()
        pending: list[Expression] = [definition.qualify_clause.expression]
        while pending:
            node = pending.pop()
            if type(node) is NameExpr:
                read.add(node.name)
            elif type(node) not in {AnyExpr, WindowExpr}:
                pending.extend(child_expressions(node))
        for item in definition.select_items:
            name = _relation_projection_output_name(item)
            if (
                name in read
                and name not in lets
                and _untyped_all_null_output(item.expression, lets, errors)
            ):
                report(
                    item.expression,
                    f"`{name}` is an untyped all-None output that its QUALIFY "
                    "stage reads",
                )
    return sorted(found, key=lambda item: (item.location.line, item.location.column))


def _hidden_table_warnings(
    script: Script,
    relation_joins: Mapping[TableDef | QueryDef, RelationJoinsInfo],
    let_scopes: Mapping[TableDef | QueryDef, LetScopeSemanticInfo],
    from_resolutions: Mapping[FromClause, object],
    mysql: set[int],
    errors: Sequence[SourceLocation],
) -> list[Diagnostic]:
    """Mirror the PostgreSQL CTE rule (sql/relations.py): a statement defines
    each table and query of the file it reads, and each one those read, as a
    CTE after the ones it reads, and a CTE takes the place of a table named
    without a schema in the CTEs after it and in the main SELECT. A relation
    with an error emits nothing; it gets no warning either."""

    named = {
        item.name: item
        for item in script.definitions
        if isinstance(item, (SourceDef, TableDef, QueryDef))
    }
    # Only a relation named as a table a source names without a schema can
    # hide it; most files have none, and need no walk of each statement.
    if not any(
        isinstance(item, SourceDef)
        and isinstance(named.get(_table_name(item)), (TableDef, QueryDef))
        for item in script.definitions
    ):
        return []

    cached: dict[int, list[object]] = {}

    def reads(relation: TableDef | QueryDef) -> list[object]:
        """What the relation reads, in order: FROM, each JOIN input, each ANY."""

        if id(relation) not in cached:
            cached[id(relation)] = _reads(relation)
        return cached[id(relation)]

    def _reads(relation: TableDef | QueryDef) -> list[object]:
        lets = _let_values(let_scopes.get(relation))
        info = relation_joins.get(relation)
        found = [
            from_resolutions.get(relation.from_clause),
            *(() if info is None else (item.relation for item in info.inputs[1:])),
        ]
        for node in _rendered_nodes(relation, lets):
            if type(node) is AnyExpr:
                target = node.relation_name
                value = lets[target].expression if target in lets else None
                found.append(
                    named.get(value.name if type(value) is NameExpr else target)
                )
        return found

    found: list[Diagnostic] = []
    for relation in script.definitions:
        if (
            not isinstance(relation, (TableDef, QueryDef))
            or id(relation) in mysql
            or any(_holds(relation, item) for item in errors)
        ):
            continue
        order: list[TableDef | QueryDef] = []
        active = {id(relation)}
        stack = [iter(reads(relation))]
        parents: list[TableDef | QueryDef] = []
        while stack:
            for child in stack[-1]:
                if isinstance(child, (TableDef, QueryDef)) and id(child) not in active:
                    # Each relation is defined once, after the ones it reads.
                    active.add(id(child))
                    parents.append(child)
                    stack.append(iter(reads(child)))
                    break
            else:
                stack.pop()
                if parents:
                    order.append(parents.pop())
        # The first CTE of each name, by its place in the statement.
        first: dict[str, int] = {}
        for index, item in enumerate(order):
            first.setdefault(item.name, index)
        hidden = next(
            (
                (table, table)
                for index, reader in enumerate((*order, relation))
                for target in reads(reader)
                if isinstance(target, SourceDef)
                and "." not in (table := _table_name(target))
                and first.get(table, index) < index
            ),
            None,
        )
        if hidden is not None:
            found.append(
                _warning(
                    relation,
                    f"its SQL defines relation {hidden[0]} as a CTE, which would hide "
                    f"table {hidden[1]} read in the same SQL",
                )
            )
    return found


def _table_name(source: SourceDef) -> str:
    connector = source.connector
    if (
        type(connector) is CallExpr
        and connector.arguments
        and type(connector.arguments[0]) is LiteralExpr
        and type(connector.arguments[0].value) is str
    ):
        return connector.arguments[0].value
    return "."


def _int_literal_outside(expression: Expression, allowed: range) -> bool:
    return (
        type(expression) is LiteralExpr
        and type(expression.value) is int
        and expression.value not in allowed
    )


def _rendered_nodes(
    definition: TableDef | QueryDef, lets: Mapping[str, LetBinding]
) -> Iterator[Expression]:
    """Each expression node the relation's SQL renders, in source order:
    every clause but the `let:` clause, whose names stand for their values
    where they are read. A value's nodes are the same at each read, so a
    `let:` name is followed at its first read only."""

    pending: list[object] = [
        getattr(definition, item.name)
        for item in reversed(fields(definition))
        if item.name not in {"let_clause", "naming_declarations", "span"}
    ]
    expanded: set[str] = set()
    while pending:
        node = pending.pop()
        if type(node) is tuple:
            pending.extend(reversed(node))
            continue
        if not is_dataclass(node) or isinstance(node, (Span, TypeExpr)):
            continue
        if isinstance(node, Expression):
            yield node
            if type(node) is NameExpr and node.name in lets:
                if node.name not in expanded:
                    expanded.add(node.name)
                    pending.append(lets[node.name].expression)
                continue
        pending.extend(
            getattr(node, item.name)
            for item in reversed(fields(node))
            if item.name != "span"
        )


def _mysql_readers(
    script: Script, from_resolutions: Mapping[FromClause, object]
) -> set[int]:
    """Each relation whose FROM chain ends at a `mysql.table` source, by id;
    each chain is walked once, so a long chain of relations stays linear."""

    found: dict[int, bool] = {}
    for definition in script.definitions:
        chain: list[int] = []
        relation: object = definition
        while (
            isinstance(relation, (TableDef, QueryDef))
            and id(relation) not in found
            and id(relation) not in chain
        ):
            chain.append(id(relation))
            relation = from_resolutions.get(relation.from_clause)
        mysql = found.get(id(relation), False) or (
            isinstance(relation, SourceDef)
            and type(relation.connector) is CallExpr
            and type(relation.connector.callee) is DottedNameExpr
            and relation.connector.callee.parts[0] == "mysql"
        )
        found.update(dict.fromkeys(chain, mysql))
    return {key for key, mysql in found.items() if mysql}


def _range_offset_warning(
    analysis: WindowExpressionAnalysis | AggregateWindowAnalysis,
    errors: Sequence[SourceLocation],
) -> Diagnostic | None:
    expression = analysis.semantic_fact.expression
    if any(_holds(expression, error) for error in errors):
        return None
    frame = analysis.validated_specification.frame
    start = frame.resolved.start if type(frame) is ValidatedFrame else None
    end = frame.resolved.end if type(frame) is ValidatedFrame else None
    if (
        type(frame) is ValidatedFrame
        and frame.resolved.unit is WindowFrameUnit.RANGE
        and (
            (start is not None and start.offset is not None)
            or (end is not None and end.offset is not None)
        )
    ):
        return _warning(
            expression,
            "this RANGE window frame has an offset",
        )
    return None


def _all_null_relation_reads(
    script: Script,
    relation_joins: Mapping[TableDef | QueryDef, RelationJoinsInfo],
    let_scopes: Mapping[TableDef | QueryDef, LetScopeSemanticInfo],
    from_resolutions: Mapping[FromClause, object],
    mysql: set[int],
    reported: Sequence[Diagnostic],
) -> list[Diagnostic]:
    """Warn when an untyped all-NULL output has any downstream relation reader.

    PostgreSQL emission refuses such a read; MySQL emission refuses it only
    after a FULL JOIN, which this does not see, so a relation that reads a
    MySQL table is left to that target.
    """

    errors = [item.location for item in reported if item.severity is Severity.ERROR]
    outputs = tuple(
        (definition, name, item.expression)
        for definition in script.definitions
        if isinstance(definition, (TableDef, QueryDef)) and id(definition) not in mysql
        for item in definition.select_items
        if (name := _relation_projection_output_name(item)) is not None
        and _untyped_all_null_output(
            item.expression,
            _let_values(let_scopes.get(definition)),
            errors,
        )
    )
    found: list[Diagnostic] = []
    readers: list[object] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        from_relation = from_resolutions.get(definition.from_clause)
        if from_relation is not None:
            readers.append(from_relation)
        info = relation_joins.get(definition)
        if info is not None:
            readers.extend(item.relation for item in info.inputs)
    for relation, name, expression in outputs:
        if not any(reader is relation for reader in readers):
            continue
        if any(_holds(expression, error) for error in errors):
            continue
        found.append(
            _warning(
                expression,
                f"`{name}` is an untyped all-None output that another relation reads",
            )
        )
    return found


def _untyped_all_null_output(
    expression: Expression,
    lets: Mapping[str, LetBinding],
    errors: Sequence[SourceLocation],
) -> bool:
    """Whether the complete semantic value is one PostgreSQL leaves untyped."""

    if _has_error_dependency(expression, lets, errors):
        return False
    pending = [(expression, frozenset[str]())]
    while pending:
        node, active = pending.pop()
        if type(node) is LiteralExpr:
            if node.value is not None:
                return False
        elif type(node) is ConditionalExpr:
            pending.extend(((node.when_true, active), (node.when_false, active)))
        elif (
            type(node) is CallExpr
            and type(node.callee) is NameExpr
            and node.callee.name in {"coalesce", "nullif"}
            and node.arguments
        ):
            pending.extend((argument, active) for argument in node.arguments)
        elif type(node) is NameExpr and node.name in lets and node.name not in active:
            pending.append((lets[node.name].expression, active | {node.name}))
        else:
            return False
    return True


def _let_values(scope: LetScopeSemanticInfo | None) -> Mapping[str, LetBinding]:
    if scope is None:
        return {}
    return {
        binding.name: binding
        for binding in scope.bindings
        if binding.name in scope.value_types
    }


def _has_error_dependency(
    expression: Expression,
    lets: Mapping[str, LetBinding],
    errors: Sequence[SourceLocation],
) -> bool:
    pending = [(expression, frozenset[str]())]
    while pending:
        node, active = pending.pop()
        if any(_holds(node, error) for error in errors):
            return True
        if type(node) is NameExpr and node.name in lets:
            if node.name in active:
                continue
            binding = lets[node.name]
            if any(_holds_span(binding.span, error) for error in errors):
                return True
            pending.append((binding.expression, active | {node.name}))
            continue
        pending.extend((child, active) for child in child_expressions(node))
    return False


def _holds(node: Node, location: SourceLocation) -> bool:
    return _holds_span(node.span, location)


def _inside(span: Span, location: SourceLocation) -> bool:
    """Whether ``span`` lies in the located expression."""

    return (
        location.path == span.path
        and (location.line, location.column) <= (span.line, span.column)
        and location.end_line is not None
        and location.end_column is not None
        and span.end_line is not None
        and span.end_column is not None
        and (span.end_line, span.end_column) <= (location.end_line, location.end_column)
    )


def _holds_span(span: Span, location: SourceLocation) -> bool:
    if location.path != span.path or (location.line, location.column) < (
        span.line,
        span.column,
    ):
        return False
    return (
        span.end_line is None
        or span.end_column is None
        or (
            (location.end_line or location.line, location.end_column or location.column)
            <= (span.end_line, span.end_column)
        )
    )


def _canonical_int(
    value: ValueType | None,
    type_expansions: Mapping[TypeExpr, ResolvedType],
) -> bool:
    resolved = (
        None if value is None else _canonical_resolved_type(value, type_expansions)
    )
    return (
        resolved is not None
        and resolved.kind is TypeKind.BUILTIN
        and resolved.name == "Int"
    )


def _warning(node: Node, detail: str) -> Diagnostic:
    span = node.span
    return Diagnostic(
        code="PIE-S2385",
        severity=Severity.WARNING,
        message=(
            f"Single-file SQL emission is unavailable because {detail}; "
            "this warning does not change check's exit status, but emit-sql will "
            "refuse this relation."
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
