"""The written form of an ``asof <kind> join`` and its refusal texts.

Private: shared by single-file semantics and the project front end. It
reads only the AST and names: ``asof_form`` accepts exactly
``EARLIER.k == TARGET.k and ... and EARLIER.t >= TARGET.t`` (zero or more
keys, one final time test) and names the first offending conjunct in source
order otherwise; within one conjunct a forward test outranks a strict one,
and that a reversed one. The type and uniqueness texts take names only.
``lower_latest_rows`` gives a project's admitted asof JOIN its latest-row
test, which project emission renders as an anti-join.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass, replace
from itertools import chain, count
from typing import Any, cast

from pietto._generated_names import generated_name
from pietto.ast_nodes import (
    AnyExpr,
    AuthoredJoinKind,
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    CollectRelationExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    JoinClause,
    LiteralExpr,
    NameExpr,
    Script,
    Span,
    UnaryExpr,
    inlined_arguments,
)

__all__ = ()

ASOF_KINDS = (AuthoredJoinKind.LEFT, AuthoredJoinKind.INNER)
ASOF_KIND_MESSAGE = "ASOF JOIN is `asof left join` or `asof inner join`."
ASOF_SECOND_MESSAGE = (
    "One asof JOIN per query: move the first into its own query and `from` it."
)
ASOF_SOURCE_MESSAGE = (
    "asof JOIN joins only a source: one latest row is proved by the source "
    "shape's unique(...)."
)
_OTHER = (
    "An asof `on` takes only field `==` keys and one time test; filter the "
    "joined rows with a view source, compute values in an earlier query."
)
_FLIPPED = {">=": "<=", ">": "<", "<=": ">=", "<": ">"}
TIME_TYPES = ("Date", "Timestamp")
_LATER = "_pietto_asof_later"


@dataclass(frozen=True, slots=True)
class AsofForm:
    """An admitted asof `on`: its keys in written order, then its time test.

    Each pair is (earlier-input field, joined field)."""

    keys: tuple[tuple[DottedNameExpr, DottedNameExpr], ...]
    time: tuple[DottedNameExpr, DottedNameExpr]


@dataclass(frozen=True, slots=True)
class AsofRefusal:
    """Why an asof `on` is refused, at the conjunct that shows it."""

    span: Span
    message: str


def missing_on_message(earlier: str, target: str) -> str:
    """The asof text of a JOIN without `on`."""

    return (
        f"JOIN {target}: write `on` with the keys, then one time test: "
        f"`on {earlier}.k == {target}.k and {earlier}.t >= {target}.t`"
    )


def conjuncts(expression: Expression) -> tuple[Expression, ...]:
    """The top-level `and` conjuncts, in source order."""

    found: list[Expression] = []
    pending = [expression]
    while pending:
        node = pending.pop()
        if type(node) is BinaryExpr and node.operator == "and":
            pending.extend((node.right, node.left))
        else:
            found.append(node)
    return tuple(found)


def asof_form(
    clause: JoinClause, earlier: Collection[str], first: str
) -> AsofForm | AsofRefusal:
    """The keys and time test of one asof JOIN's `on`, or why it is refused.

    ``earlier`` names the bindings its `on` may read before the joined one;
    ``first`` is the earlier binding the hints name.
    """

    assert clause.on_clause is not None
    target = clause.target_binding_name
    parts = tuple(
        item for item in conjuncts(clause.on_clause.expression) if not _latest(item)
    )
    kinds = [_classify(item, earlier, target) for item in parts]
    times = [index for index, item in enumerate(kinds) if item[0] in {"time", "extra"}]
    keys = [index for index, item in enumerate(kinds) if item[0] == "key"]
    # The time test is the first `>=` one; any other is refused as extra.
    head = next(
        (i for i in times if kinds[i][0] == "time" and kinds[i][2] == ">="),
        times[0] if times else -1,
    )
    seen: set[tuple[str, str]] = set()
    form_keys: list[tuple[DottedNameExpr, DottedNameExpr]] = []
    time: tuple[DottedNameExpr, DottedNameExpr] | None = None
    for index, (part, item) in enumerate(zip(parts, kinds, strict=True)):
        kind = item[0]
        if kind == "bare":
            return AsofRefusal(part.span, "Qualify each field with its input.")
        if kind == "other":
            return AsofRefusal(part.span, _OTHER)
        if kind == "extra" or (kind == "time" and index != head):
            return AsofRefusal(
                part.span,
                _extra_message(clause, part, kinds, head, index, first, earlier),
            )
        if kind == "time":
            _, left, operator, right, reversed_ = item
            if operator in {"<=", "<"}:
                return AsofRefusal(
                    part.span,
                    "asof finds the latest earlier-or-equal row only; the next "
                    "later row is not available.",
                )
            if operator == ">":
                return AsofRefusal(
                    part.span,
                    "Write `>=`: a row at the same moment matches; excluding it "
                    "is not available; for the previous row of one input use "
                    "`lag(...)`.",
                )
            if reversed_:
                return AsofRefusal(
                    part.span,
                    "Write the earlier input first in each test: "
                    f"`{_dotted(left)} >= {_dotted(right)}`.",
                )
            if keys and keys[-1] > index:
                return AsofRefusal(
                    part.span, "Write the keys first and the one time test last."
                )
            time = (cast(DottedNameExpr, left), cast(DottedNameExpr, right))
            continue
        _, left, _, right, reversed_ = item
        if reversed_:
            return AsofRefusal(
                part.span,
                "Write the earlier input first in each test: "
                f"`{_dotted(left)} == {_dotted(right)}`.",
            )
        pair = (_dotted(left), _dotted(right))
        if pair in seen:
            return AsofRefusal(
                part.span,
                f"Match each key once: remove the repeated `{pair[0]} == {pair[1]}`.",
            )
        seen.add(pair)
        form_keys.append((cast(DottedNameExpr, left), cast(DottedNameExpr, right)))
    if time is None:
        return AsofRefusal(
            clause.on_clause.span,
            f"Add one time test last: `and {first}.t >= {target}.t`.",
        )
    return AsofForm(keys=tuple(form_keys), time=time)


def lowered(clause: JoinClause) -> bool:
    """Whether a project gave this asof JOIN its latest-row test."""

    return clause.on_clause is not None and any(
        _latest(item) for item in conjuncts(clause.on_clause.expression)
    )


def lower_latest_rows(script: Script) -> Script:
    """Each asof JOIN whose `on` has the admitted form, with its latest-row test.

    `on K and E.t >= T.t` becomes `on K and E.t >= T.t and not any(K' and
    E.t >= L.t and L.t > T.t for L in R)`: R is the joined relation (through
    the `let` aliases before the JOIN) and K' the keys over L. With the unique
    that semantics proves, at most one T row is left per earlier row, the
    latest; a None key or time matches no row. Every new node is a fresh
    occurrence of the clause's `on` word (``latest_row_ranges``). A JOIN in
    another form, in a relation that collects or unnests, or where existence
    normalization takes no `any(...)` in its `on`, stays as written.
    """

    from pietto.semantic.existence_generators import _any_inventory
    from pietto.semantic.inline_functions import (
        _last_occurrence,
        _rebuild,
        _tree_nodes,
    )

    nodes = _tree_nodes(script)
    if not any(type(node) is JoinClause and node.asof for node in nodes):
        return script
    used = {
        name.casefold()
        for node in nodes
        for name in (
            *(
                getattr(node, attribute, None)
                for attribute in (
                    "name",
                    "binding_name",
                    "source_name",
                    "target_binding_name",
                )
            ),
            *(node.parts[:1] if type(node) is DottedNameExpr else ()),
        )
        if isinstance(name, str)
    }
    occurrences = count(1 + _last_occurrence(script))
    names = frozenset(used)
    # Each authored asof JOIN that is left as written, and each latest-row
    # test made, by the id of its authored JOIN.
    kept: set[int] = set()
    made: dict[int, AnyExpr] = {}

    def fresh(span: Span) -> Span:
        return replace(span, occurrence=next(occurrences))

    def lower(clause: JoinClause, aliases: dict[str, str]) -> JoinClause:
        if not clause.asof or clause.on_clause is None or id(clause) in kept:
            return clause
        target = clause.target_binding_name
        expression = clause.on_clause.expression
        named = {
            node.parts[0]
            for node in _tree_nodes(expression)
            if type(node) is DottedNameExpr and node.parts[0] != target
        }
        form = asof_form(clause, named, target)
        if isinstance(form, AsofRefusal):
            return clause
        relation, seen = clause.target_relation_name, set()
        while relation in aliases and relation not in seen:
            seen.add(relation)
            relation = aliases[relation]
        later = generated_name((f"{_LATER}_{n}" for n in count(1)), used)
        whole = _on_word(clause)

        def field(node: DottedNameExpr, binding: str) -> DottedNameExpr:
            return replace(node, span=fresh(whole), parts=(binding, node.parts[1]))

        def test(left: Expression, operator: str, right: Expression) -> Expression:
            return ComparisonExpr(
                span=fresh(whole), left=left, operator=operator, right=right
            )

        tests = [
            test(field(left, left.parts[0]), "==", field(right, later))
            for left, right in form.keys
        ]
        earlier, joined = form.time
        tests.append(test(field(earlier, earlier.parts[0]), ">=", field(joined, later)))
        tests.append(test(field(joined, later), ">", field(joined, target)))
        predicate = tests[0]
        for item in tests[1:]:
            predicate = BinaryExpr(
                span=fresh(whole), left=predicate, operator="and", right=item
            )
        made[id(clause)] = AnyExpr(
            span=fresh(whole),
            predicate=predicate,
            binding_name=later,
            binding_span=fresh(whole),
            relation_name=relation,
            relation_span=fresh(whole),
        )
        latest = UnaryExpr(span=fresh(whole), operator="not", operand=made[id(clause)])
        on = BinaryExpr(
            span=fresh(whole), left=expression, operator="and", right=latest
        )
        return replace(clause, on_clause=replace(clause.on_clause, expression=on))

    def visit(before: object, after: object) -> object:
        clauses = getattr(after, "join_clauses", None)
        if not clauses or not any(item.asof for item in clauses):
            return after
        if collects_or_unnests(after):
            # Refused for its nested fields before any latest-row test.
            return after
        declared = (
            *getattr(after, "naming_declarations", ()),
            *getattr(getattr(after, "let_clause", None), "bindings", ()),
        )
        # Only a `let NAME = RELATION` before the JOIN names its relation.
        rebuilt = tuple(
            lower(
                item,
                {
                    let.name: let.expression.name
                    for let in declared
                    if type(let.expression) is NameExpr
                    and (let.span.line, let.span.column)
                    < (item.span.line, item.span.column)
                },
            )
            for item in clauses
        )
        if all(new is old for new, old in zip(rebuilt, clauses, strict=True)):
            return after
        return replace(cast(Any, after), join_clauses=rebuilt)

    rebuilt = _rebuild(script, visit)
    # Only where normalization takes an `any(...)` in that JOIN's `on`; any
    # other asof JOIN keeps its own checks and the project refusal.
    taken = {id(item[0]) for item in _any_inventory(cast(Script, rebuilt))}
    kept.update(key for key, test in made.items() if id(test) not in taken)
    if kept:
        used.clear()
        used.update(names)
        rebuilt = _rebuild(script, visit)
    assert type(rebuilt) is Script
    return rebuilt


def latest_row_ranges(script: Script) -> frozenset[tuple[object, ...]]:
    """The source ranges of the latest-row tests in ``script``: a diagnostic
    there restates one of the authored `on`, which semantics also checks."""

    from pietto.semantic.inline_functions import _tree_nodes

    return frozenset(
        _range(_on_word(node))
        for node in _tree_nodes(script)
        if type(node) is JoinClause and node.asof and lowered(node)
    )


def _on_word(clause: JoinClause) -> Span:
    """The range of the word `on`: inside the `on` clause, as an `any(...)`
    value must be, and the range of no authored node."""

    assert clause.on_clause is not None
    start = clause.on_clause.span
    return replace(
        start, end_line=start.line, end_column=start.column + 2, occurrence=0
    )


def _range(span: Span) -> tuple[object, ...]:
    return (span.path, span.line, span.column, span.end_line, span.end_column)


def conjunct_span(test: tuple[DottedNameExpr, DottedNameExpr]) -> Span:
    """The range of an admitted key or time test: its earlier field, written
    first, through its joined field."""

    left, right = test
    return replace(
        left.span, end_line=right.span.end_line, end_column=right.span.end_column
    )


def collects_or_unnests(definition: object) -> bool:
    """Whether a relation body collects a relation or unnests a field."""

    from pietto.semantic.aggregates import child_expressions

    pending: list[object] = [
        *(item.expression for item in getattr(definition, "select_items", ())),
        *(item.expression for item in getattr(definition, "naming_declarations", ())),
    ]
    while pending:
        node = pending.pop()
        if type(node) is CollectRelationExpr:
            return True
        if (
            type(node) is CallExpr
            and type(node.callee) is NameExpr
            and node.callee.name == "unnest"
        ):
            return True
        if isinstance(node, Expression):
            pending.extend(child_expressions(node))
    return False


def time_type_message(earlier: str | None, target: str | None) -> str | None:
    """The refusal of a time test whose canonical types are not one of Date or
    Timestamp on both sides; None when they are. Cross-family is PIE-S2105."""

    if earlier == target and earlier in TIME_TYPES:
        return None
    return (
        "The time test needs Date on both sides or Timestamp on both sides; "
        f"got {earlier or 'an unknown type'} and {target or 'an unknown type'}."
    )


def key_type_message(name: str | None) -> str | None:
    """The refusal of a key of canonical type ``name``; None when it may key."""

    if name == "Float":
        return "An asof key cannot be Float."
    return None


def unique_message(
    form: AsofForm,
    *,
    first: str,
    target: str,
    shape: str,
    uniques: Sequence[tuple[str, tuple[str, ...]]],
    earlier_fields: Sequence[tuple[str, Collection[str]]],
    items: Collection[str],
) -> str | None:
    """PIE-S2386 unless a declared unique lies within the keys and the time;
    ``earlier_fields`` lists each earlier binding with its field names and
    ``items`` the names the shape declares."""

    matched = {right.parts[1] for _, right in form.keys} | {form.time[1].parts[1]}
    if any(set(fields) <= matched for _, fields in uniques):
        return None
    head = (
        f"Several rows of {target} may be the latest for one {first} row; "
        "Pietto does not pick one."
    )
    # Only a unique that `on` already partly matches is near a proof; one such
    # as a surrogate `unique(id)` would name an unrelated match.
    near = [item for item in uniques if set(item[1]) & matched]
    if not near:
        names = list(
            dict.fromkeys(
                [right.parts[1] for _, right in form.keys] + [form.time[1].parts[1]]
            )
        )
        # A name the shape does not declare yet, so the hint can be pasted.
        key = generated_name(
            chain((f"{target}_key",), (f"{target}_key_{n}" for n in count(2))),
            {item.casefold() for item in items},
        )
        return (
            f"{head} If the data has one row per {_and(names)}, declare "
            f"`{key} = unique({', '.join(names)})` in shape {shape}."
        )
    name, fields = min(
        near, key=lambda item: len([f for f in item[1] if f not in matched])
    )
    missing = [field for field in fields if field not in matched]
    tests = []
    for field in missing:
        owners = [binding for binding, names in earlier_fields if field in names]
        tests.append(
            f"{owners[0]}.{field} == {target}.{field}"
            if len(owners) == 1
            else f"match {target}.{field}"
        )
    remedy = " and ".join(
        f"{test} in `on`" if test.startswith("match ") else f"add `{test}`"
        for test in tests
    )
    return (
        f"{head} {shape}.{name} = unique({', '.join(fields)}) has "
        f"{_and(missing)}, which `on` does not match: {remedy}."
    )


def _classify(
    node: Expression, earlier: Collection[str], target: str
) -> tuple[object, ...]:
    """("key"|"time", earlier field, normalized operator, joined field,
    reversed), ("extra",), ("bare",) or ("other",)."""

    if type(node) is BetweenExpr:
        # A `def` argument or a part of a `def` or relationship body is no
        # test written in `on` itself.
        parts = (node, node.lower, node.value, node.upper)
        if any(inlined_arguments(item) or item.span.occurrence for item in parts):
            return ("other",)
        return ("extra",)
    if type(node) is not ComparisonExpr or node.operator not in {
        "==",
        ">=",
        ">",
        "<=",
        "<",
    }:
        return ("other",)
    if node.left.span.occurrence and node.right.span.occurrence:
        # Both operands copied: the body of a relationship call.
        return ("other",)
    if any(inlined_arguments(item) for item in (node, node.left, node.right)):
        # A `def` call: no test written in `on` itself.
        return ("other",)
    if node.left.span.occurrence:
        # The second comparison of a chain such as `a >= b >= c`, by its
        # operands: the `>=` half of `L < T.t <= E.t` is the time test.
        item = _operands(node, earlier, target)
        return item if item[0] == "time" else ("extra",)
    return _operands(node, earlier, target)


def _operands(
    node: ComparisonExpr, earlier: Collection[str], target: str
) -> tuple[object, ...]:
    sides = [_side(item, earlier, target) for item in (node.left, node.right)]
    if "bare" in sides:
        return ("bare",)
    if (
        node.operator != "=="
        and set(sides) & {"earlier", "target"}
        and any(
            side == "value" and _reads_field(item, earlier, target)
            for side, item in zip(sides, (node.left, node.right), strict=True)
        )
    ):
        # Time arithmetic, such as `orders.t >= price.t + 1`.
        return ("extra",)
    if sorted(sides) != ["earlier", "target"]:
        return ("other",)
    reversed_ = sides[0] == "target"
    left, right = (node.right, node.left) if reversed_ else (node.left, node.right)
    assert type(left) is DottedNameExpr and type(right) is DottedNameExpr
    operator = _FLIPPED.get(node.operator, "==") if reversed_ else node.operator
    return ("key" if operator == "==" else "time", left, operator, right, reversed_)


def _side(node: Expression, earlier: Collection[str], target: str) -> str:
    if type(node) is NameExpr:
        return "bare"
    if type(node) is DottedNameExpr and len(node.parts) == 2:
        if node.parts[0] == target:
            return "target"
        if node.parts[0] in earlier:
            return "earlier"
    return "value"


def _reads_field(node: Expression, earlier: Collection[str], target: str) -> bool:
    """Whether ``node``, a computed operand, reads an input field."""

    pending = [node]
    while pending:
        item = pending.pop()
        if type(item) is DottedNameExpr and _side(item, earlier, target) != "value":
            return True
        if type(item) is BinaryExpr:
            pending.extend((item.left, item.right))
    return False


def _extra_message(
    clause: JoinClause,
    part: Expression,
    kinds: Sequence[tuple[object, ...]],
    head_index: int,
    index: int,
    first: str,
    earlier: Collection[str],
) -> str:
    """The text of a second time test, a chain or time arithmetic."""

    target = clause.target_binding_name
    head = kinds[head_index]
    item = kinds[index]
    if (
        index != head_index
        and head[0] == "time"
        and item[0] == "time"
        and item[2] in {"<", "<="}
        and _dotted(item[1]) == _dotted(head[1])
        and _dotted(item[3]) != _dotted(head[3])
    ):
        return f"For a validity range, use `left join {target} on` with both tests."
    keep = ""
    if (
        index != head_index
        and head[0] == "time"
        and head[4]
        and cast(DottedNameExpr, head[3]).span.occurrence
    ):
        # `L < TARGET.t <= EARLIER.t`: its second half is the time test.
        keep = f"keep `{_dotted(head[1])} >= {_dotted(head[3])}` in `on`; "
    if (
        type(part) is BetweenExpr
        and _side(part.value, earlier, target) == "target"
        and _side(part.upper, earlier, target) == "earlier"
    ):
        # `L <= TARGET.t <= EARLIER.t`: its upper half is the time test.
        keep = f"keep `{_render(part.upper)} >= {_render(part.value)}` in `on`; "
        lower, value = _render(part.lower), _render(part.value)
        text = None if lower is None else f"{lower} <= {value}"
    else:
        text = _render(part)
    text = text or "<test>"
    if clause.kind is AuthoredJoinKind.INNER:
        return (
            f"An asof `on` takes one time test; {keep}test the chosen row after "
            f"the JOIN instead: `where {text}`."
        )
    return (
        f"An asof `on` takes one time test; {keep}to keep every {first} row, test "
        f"the chosen row in select instead: `x = {target}.<field> if {text} else None`."
    )


def _render(node: Expression) -> str | None:
    """Simple source text of a test, or None."""

    if type(node) is DottedNameExpr:
        return ".".join(node.parts)
    if type(node) is NameExpr:
        return node.name
    if type(node) is LiteralExpr:
        return (
            None
            if node.value is None or isinstance(node.value, str)
            else (str(node.value))
        )
    if isinstance(node, (ComparisonExpr, BinaryExpr)):
        left, right = _render(node.left), _render(node.right)
        if left is None or right is None:
            return None
        return f"{left} {node.operator} {right}"
    if type(node) is BetweenExpr:
        texts = (_render(node.lower), _render(node.value), _render(node.upper))
        return None if None in texts else f"{texts[0]} <= {texts[1]} <= {texts[2]}"
    return None


def _latest(node: Expression) -> bool:
    """Whether ``node`` is the latest-row test ``lower_latest_rows`` wrote."""

    return (
        type(node) is UnaryExpr
        and node.operator == "not"
        and node.span.occurrence != 0
        and type(node.operand) is AnyExpr
        and node.operand.binding_name.startswith(_LATER)
    )


def _dotted(node: object) -> str:
    assert type(node) is DottedNameExpr
    return ".".join(node.parts)


def _and(items: Sequence[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"
