"""The written form of an ``asof <kind> join`` and its refusal texts.

Private: shared by single-file semantics and the project front end. It
reads only the AST and names: ``asof_form`` accepts exactly
``EARLIER.k == TARGET.k and ... and EARLIER.t >= TARGET.t`` (zero or more
keys, one final time test) and names the first offending conjunct in source
order otherwise; within one conjunct a forward test outranks a strict one,
and that a reversed one. The type and uniqueness texts take names only.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import cast

from pietto.ast_nodes import (
    AuthoredJoinKind,
    BetweenExpr,
    BinaryExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    JoinClause,
    LiteralExpr,
    NameExpr,
    Span,
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
    parts = conjuncts(clause.on_clause.expression)
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


def time_type_message(earlier: str | None, target: str | None) -> str | None:
    """The refusal of a time test whose canonical types are not one of Date or
    Timestamp on both sides; None when they are. Cross-family is S2105."""

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
) -> str | None:
    """S2386 unless a declared unique lies within the keys and the time;
    ``earlier_fields`` lists each earlier binding with its field names."""

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
        names = [right.parts[1] for _, right in form.keys] + [form.time[1].parts[1]]
        return (
            f"{head} If the data has one row per {_and(names)}, declare "
            f"`{target}_key = unique({', '.join(names)})` in shape {shape}."
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
        and ("value" in sides and _reads_field(node, earlier, target))
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
    """Whether a computed operand of ``node`` reads an input field."""

    pending = [node.left, node.right] if type(node) is ComparisonExpr else [node]
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


def _dotted(node: object) -> str:
    assert type(node) is DottedNameExpr
    return ".".join(node.parts)


def _and(items: Sequence[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"
