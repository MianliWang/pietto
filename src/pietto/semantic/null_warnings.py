"""Single-file warnings at tests whose SQL None handling a Python reader
does not expect.

Private: nothing here is exported. PIE-S2383 is a WHERE test after a LEFT
JOIN that is never True where the JOIN found no match; PIE-S2384 is a
`not in` whose left value may be None. Both are WARNINGs in every check mode
and change no SQL. They are kept precise: a test rejects None only through
a comparison, `in`/`not in` or an inclusive chain over field reads and
arithmetic, so `is None`, `or`, `coalesce`, other built-in calls and
conditionals never count; PIE-S2384 counts a field only when its input's row
type is `| None`, not when only a JOIN of the same relation fills it with
None, and not where a WHERE conjunct `is not None` already drops its None
rows. A warning whose test holds an ERROR is not reported.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pietto.ast_nodes import (
    AuthoredJoinKind,
    BetweenExpr,
    BinaryExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    QueryDef,
    Script,
    SourceDef,
    TableDef,
    UnaryExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.joins import _conjuncts, _expression_nodes, _location, _text
from pietto.semantic.model import (
    EffectiveNullability,
    JoinFieldRef,
    JoinInfo,
    RelationJoinsInfo,
    RowSchema,
    ValueType,
    ValueTypeKind,
)

__all__ = ()

_ARITHMETIC = frozenset({"+", "-", "*", "/", "%"})
# A later JOIN of these kinds whose match reads an input already drops that
# input's unmatched rows itself.
_MATCH_REQUIRING = frozenset({AuthoredJoinKind.INNER, AuthoredJoinKind.SEMI})


def null_warnings(
    script: Script,
    joins: Mapping[TableDef | QueryDef, RelationJoinsInfo],
    *,
    expression_value_types: Mapping[Expression, ValueType],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[TableDef | QueryDef, RowSchema],
    reported: Sequence[Diagnostic],
) -> list[Diagnostic]:
    """PIE-S2383 and PIE-S2384 of each table and query without JOIN errors,
    except at a test that holds an ERROR among ``reported``."""

    found: list[Diagnostic] = []
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        info = joins.get(definition)
        if info is None and definition.join_clauses:
            continue
        if info is not None:
            found.extend(_left_join_where(definition, info))
        found.extend(
            _nullable_not_in(
                definition,
                info,
                expression_value_types,
                source_row_schemas,
                relation_row_schemas,
            )
        )
    errors = [item.location for item in reported if item.severity is Severity.ERROR]
    return [
        item
        for item in found
        if not any(_holds(item.location, error) for error in errors)
    ]


def _holds(outer: SourceLocation, inner: SourceLocation) -> bool:
    """Whether ``inner`` lies inside ``outer``'s range."""

    start = (outer.line, outer.column)
    if inner.path != outer.path or (inner.line, inner.column) < start:
        return False
    if outer.end_line is None or outer.end_column is None:
        return True
    end = (inner.end_line or inner.line, inner.end_column or inner.column)
    return end <= (outer.end_line, outer.end_column)


def _strict_leaves(expression: Expression) -> list[NameExpr | DottedNameExpr]:
    """The name reads that make ``expression`` None when one is None, in
    source order: the expression itself or operands of arithmetic and signs."""

    leaves: list[NameExpr | DottedNameExpr] = []
    pending = [expression]
    while pending:
        node = pending.pop()
        if isinstance(node, (NameExpr, DottedNameExpr)):
            leaves.append(node)
        elif type(node) is BinaryExpr and node.operator in _ARITHMETIC:
            pending.extend((node.right, node.left))
        elif type(node) is UnaryExpr and node.operator in {"-", "+"}:
            pending.append(node.operand)
    return leaves


def _tested_values(test: Expression) -> tuple[Expression, ...]:
    """The values that make a test never True when one of them is None."""

    if type(test) is ComparisonExpr:
        return (test.left, test.right)
    if type(test) is MembershipExpr:
        return (test.value,)
    if type(test) is BetweenExpr:
        return (test.value, test.lower, test.upper)
    return ()


def _match_reads(join: JoinInfo, info: RelationJoinsInfo) -> set[int]:
    """The inputs a JOIN's match condition reads."""

    reads = {item.left.input for item in join.equalities}
    reads.update(item.right.input for item in join.equalities)
    if join.clause.on_clause is not None:
        for node in _expression_nodes(join.clause.on_clause.expression):
            read = (
                info.field_reads.get(node)
                if isinstance(node, (NameExpr, DottedNameExpr))
                else None
            )
            if read is not None:
                reads.add(read.input)
    return reads


def _left_join_where(
    definition: TableDef | QueryDef, info: RelationJoinsInfo
) -> list[Diagnostic]:
    """PIE-S2383 once per LEFT JOIN target that a WHERE test rejects, at the
    first such test in source order."""

    if definition.where_clause is None:
        return []
    unmatched: set[int] = set()
    for join in info.joins:
        if join.kind is AuthoredJoinKind.LEFT:
            unmatched.add(join.target_input)
        elif join.kind in _MATCH_REQUIRING:
            unmatched -= _match_reads(join, info)
    first: dict[int, tuple[Expression, NameExpr | DottedNameExpr]] = {}
    for test in _conjuncts(definition.where_clause.expression):
        for value in _tested_values(test):
            for leaf in _strict_leaves(value):
                read = info.field_reads.get(leaf)
                if read is not None and read.input in unmatched:
                    first.setdefault(read.input, (test, leaf))
    found: list[Diagnostic] = []
    for target in sorted(first):
        test, leaf = first[target]
        binding = info.inputs[target].binding
        found.append(
            Diagnostic(
                code="PIE-S2383",
                severity=Severity.WARNING,
                message=(
                    f"`{_text(leaf)}` is None where `left join {binding}` finds "
                    "no match, so this WHERE test is never True on those rows "
                    f"and drops them, as `inner join {binding}` would; to keep "
                    "them, move the test into the JOIN's `on`, or write "
                    f"`inner join {binding}` if only matched rows are wanted"
                ),
                location=_location(test.span),
            )
        )
    return found


def _clause_roots(definition: TableDef | QueryDef) -> list[Expression]:
    """The row and result expressions of a relation's clauses."""

    roots: list[Expression] = []
    if definition.let_clause is not None:
        roots.extend(binding.expression for binding in definition.let_clause.bindings)
    roots.extend(
        clause.on_clause.expression
        for clause in definition.join_clauses
        if clause.on_clause is not None
    )
    if definition.where_clause is not None:
        roots.append(definition.where_clause.expression)
    roots.extend(item.expression for item in definition.select_items)
    if definition.order_by_clause is not None:
        roots.extend(item.expression for item in definition.order_by_clause.items)
    return roots


def _nullable_not_in(
    definition: TableDef | QueryDef,
    info: RelationJoinsInfo | None,
    value_types: Mapping[Expression, ValueType],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[TableDef | QueryDef, RowSchema],
) -> list[Diagnostic]:
    """PIE-S2384 at each `not in` without a `None` option whose left value
    may be None because a field it reads has an input row type `| None`,
    unless its clause tests that field with `is None` or `is not None`, or a
    top-level `and` conjunct of the WHERE, also through a `let` name, tests
    it with `is not None`."""

    lets = (
        {}
        if definition.let_clause is None
        else {item.name: item.expression for item in definition.let_clause.bindings}
    )

    def declared_nullable(leaf: NameExpr | DottedNameExpr) -> bool:
        if info is None:
            value_type = value_types.get(leaf)
            return (
                value_type is not None
                and value_type.nullability is EffectiveNullability.NULLABLE
            )
        read = info.field_reads.get(leaf)
        if read is None:
            return False
        relation = info.inputs[read.input].relation
        schema = (
            source_row_schemas.get(relation)
            if isinstance(relation, SourceDef)
            else relation_row_schemas.get(relation)
        )
        field = None if schema is None else schema.fields.get(read.field)
        return field is not None and field.nullability is EffectiveNullability.NULLABLE

    def identity(leaf: NameExpr | DottedNameExpr) -> JoinFieldRef | str:
        """The field a read names, through `let` names bound to a read."""

        seen: set[Expression] = set()
        while True:
            read = None if info is None else info.field_reads.get(leaf)
            if read is not None:
                return read
            value = lets.get(leaf.name) if isinstance(leaf, NameExpr) else None
            if not isinstance(value, (NameExpr, DottedNameExpr)) or value in seen:
                return _text(leaf).rsplit(".", 1)[-1]
            seen.add(value)
            leaf = value

    guarded: set[JoinFieldRef | str] = set()
    pending = (
        [] if definition.where_clause is None else [definition.where_clause.expression]
    )
    named: set[str] = set()
    while pending:
        for test in _conjuncts(pending.pop()):
            if type(test) is IsNullExpr and test.negated:
                if isinstance(test.value, (NameExpr, DottedNameExpr)):
                    guarded.add(identity(test.value))
            elif (
                type(test) is NameExpr and test.name in lets and test.name not in named
            ):
                named.add(test.name)
                pending.append(lets[test.name])

    found: list[Diagnostic] = []
    for root in _clause_roots(definition):
        nodes = tuple(_expression_nodes(root))
        tested = guarded | {
            identity(leaf)
            for node in nodes
            if type(node) is IsNullExpr
            for leaf in _expression_nodes(node.value)
            if isinstance(leaf, (NameExpr, DottedNameExpr))
        }
        for node in nodes:
            # A `None` option makes the test never True for any value.
            if (
                type(node) is not MembershipExpr
                or not node.negated
                or any(
                    type(option) is LiteralExpr and option.value is None
                    for option in node.options
                )
            ):
                continue
            value_type = value_types.get(node.value)
            if (
                value_type is None
                or value_type.kind is not ValueTypeKind.KNOWN
                or value_type.nullability is EffectiveNullability.NON_NULL
            ):
                continue
            leaves = [
                leaf for leaf in _strict_leaves(node.value) if declared_nullable(leaf)
            ]
            if not leaves or any(identity(leaf) in tested for leaf in leaves):
                continue
            found.append(_not_in_warning(node, leaves))
    return found


def _not_in_warning(
    node: MembershipExpr, leaves: Sequence[NameExpr | DottedNameExpr]
) -> Diagnostic:
    names = tuple(dict.fromkeys(_text(leaf) for leaf in leaves))
    which = " or ".join(f"`{name}`" for name in names)
    keep = " or ".join(f"{name} is None" for name in names)
    drop = " and ".join(f"{name} is not None" for name in names)
    return Diagnostic(
        code="PIE-S2384",
        severity=Severity.WARNING,
        message=(
            f"`not in` is never True when {which} is None: SQL compares None as "
            "unknown, unlike Python, where `None not in (...)` is True; write "
            f"`... or {keep}` to accept None, or `{drop} and ...` to reject it"
        ),
        location=_location(node.span),
    )
